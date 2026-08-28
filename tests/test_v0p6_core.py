"""Synthetic known-answer tests for the prospective detector-v0.6 core."""

from __future__ import annotations

from dataclasses import replace
import gc
import hashlib
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
import seti_repeater.search_v0p6 as v06

from seti_repeater.search_v0p6 import (
    DETECTOR_VERSION,
    FILTER_COORDINATE,
    M37_BANK_SHA256,
    M37_FACTOR_BASIS_SHA256,
    M37_FACTOR_BASIS_LABELS_SHA256,
    M37_FACTOR_ROW_SELECTION_SHA256S,
    M37_SCAN_INVENTORY_SHA256,
    M37_EXPERIMENT_CONTRACT_SHA256,
    M37_SCRAMBLE_TABLES_SHA256,
    M37_SCRAMBLE_RESOURCE_NAMES,
    M37_SCRAMBLE_TABLE_SHA256S,
    M37_TEMPLATE_COUNT,
    PROXY_CARRIER_AXIS_LABEL,
    CalibrationAccumulator,
    ExhaustiveRetentionLedger,
    NativeFrequencyGeometry,
    V0P6CapacityError,
    V0P6ContractError,
    V0P6CoverageError,
    V0P6IncompleteError,
    build_epoch_vectors,
    build_epoch_vector_product,
    build_m37_mask_product,
    build_two_pass_template_mask,
    build_native_filter_cache,
    calibrated_threshold,
    canonical_json_bytes,
    empirical_global_pvalue,
    factor_basis_sha256,
    factor_row_selection_sha256,
    factor_scan_selection_sha256,
    factor_table_for_scan,
    float64_vector_sha256,
    gather_filtered_native,
    generate_m37_scramble_tables_for_preregistration,
    make_line_template_bank,
    make_hypothesis_inventory,
    make_m37_calibration,
    make_m37_proxy_carrier_grid,
    make_factor_basis_from_arrays,
    make_template_factor_table,
    make_proxy_carrier_grid,
    make_scramble_shift_table,
    load_m37_scramble_tables,
    match_retained_off_tracks,
    materialized_reference_gather,
    m37_scan_indices_for_kind,
    native_filter_then_q_gather,
    native_geometry_from_extraction,
    nearest_native_indices,
    plan_native_filter_cache,
    scramble_table_sha256,
    scan_inventory_sha256,
    stack_hypothesis,
    template_bank_sha256,
    template_factors_from_basis,
    update_calibration,
    validate_scramble_shift_table,
    validate_factor_basis_scan_inventory,
    validate_epoch_vector_product,
    validate_mask_product,
    validate_template_factor_table,
    validate_m37_scramble_tables,
)
from seti_repeater.spectral import normalized_boxcar


ROOT = Path(__file__).resolve().parents[1]


def native_axis(
    count: int,
    *,
    first_mhz: float = 0.0,
    channel_width_hz: float = 1.0,
    descending: bool = False,
) -> np.ndarray:
    step = channel_width_hz / 1e6
    if descending:
        step = -step
    return first_mhz + np.arange(count, dtype=np.float64) * step


def geometry_for_axis(
    frequency_mhz: np.ndarray,
    channel_width_hz: float,
) -> NativeFrequencyGeometry:
    return NativeFrequencyGeometry(
        raw_zero_hz=float(np.min(frequency_mhz)) * 1e6,
        channel_width_hz=float(channel_width_hz),
        channel_count=frequency_mhz.size,
    )


def literal_raw_filter_oracle(
    data: np.ndarray,
    frequency_mhz: np.ndarray,
    geometry: NativeFrequencyGeometry,
    factors: np.ndarray,
    q_support_mhz: np.ndarray,
    width: int,
) -> np.ndarray:
    """Literal native-row filter then q-track gather oracle."""
    half = width // 2
    result = np.zeros(q_support_mhz.size, dtype=np.float32)
    for integration in range(data.shape[0]):
        requested_hz = q_support_mhz * 1e6 * factors[integration]
        indices = nearest_native_indices(geometry, requested_hz)
        for q_index, raw_index in enumerate(indices):
            lo = int(raw_index) - half
            hi = int(raw_index) + half + 1
            result[q_index] += np.sum(
                data[integration, lo:hi], dtype=np.float32
            ) / np.float32(math.sqrt(width))
    result /= np.float32(math.sqrt(data.shape[0]))
    return result


class V0P6BankAndGridTests(unittest.TestCase):
    def test_sha256_identity_requires_a_json_string(self):
        with self.assertRaisesRegex(V0P6ContractError, "lowercase SHA-256"):
            v06._frozen_sha256(int("1" * 64), "synthetic identity")

    def test_integer_contract_controls_reject_coercion(self):
        with self.assertRaisesRegex(V0P6ContractError, "exact integer"):
            make_proxy_carrier_grid(1.0, 1.0, 2.5, 1)
        with self.assertRaisesRegex(V0P6ContractError, "not boolean"):
            make_proxy_carrier_grid(1.0, 1.0, 2, True)
        with self.assertRaisesRegex(V0P6ContractError, "exact integer"):
            NativeFrequencyGeometry(0.0, 1.0, 10.5)
        with self.assertRaisesRegex(V0P6ContractError, "not boolean"):
            native_geometry_from_extraction(
                fch1_mhz=1.0,
                foff_mhz=1e-6,
                channel_start=False,
                channel_stop=10,
            )
        with self.assertRaisesRegex(V0P6ContractError, "exact integer"):
            make_scramble_shift_table(
                2.5,
                3,
                100,
                seed=1,
                minimum_shift_bins=10,
            )
        with self.assertRaisesRegex(V0P6ContractError, "not boolean"):
            make_scramble_shift_table(
                2,
                3,
                100,
                seed=True,
                minimum_shift_bins=10,
            )

    def test_m37_bank_identity_order_and_namespace(self):
        bank = make_line_template_bank()
        self.assertEqual(DETECTOR_VERSION, "0.6.0-development")
        self.assertEqual(len(bank), M37_TEMPLATE_COUNT)
        self.assertEqual(
            [item["line_index"] for item in bank[:9]],
            [0, 1, -1, 2, -2, 3, -3, 4, -4],
        )
        self.assertEqual([item["line_index"] for item in bank[-2:]], [46, -46])
        self.assertEqual(template_bank_sha256(bank), M37_BANK_SHA256)
        self.assertEqual(
            template_bank_sha256(json.loads(canonical_json_bytes(bank))),
            M37_BANK_SHA256,
        )
        self.assertEqual(FILTER_COORDINATE, "native_raw_channel_axis_before_q_track_gather")
        self.assertEqual(PROXY_CARRIER_AXIS_LABEL, "proxy_carrier_mhz")
        self.assertEqual(
            M37_FACTOR_BASIS_SHA256,
            "492d2fe31d8cbe14968c9ce0296e898f42bf298540310f3f06a74ec8c971c143",
        )

    def test_bank_mutations_fail_hash_gate(self):
        with self.assertRaisesRegex(V0P6ContractError, "SHA-256"):
            make_line_template_bank(direction=(1.0, 0.0), direction_phase_cycles=0.0)
        with self.assertRaisesRegex(V0P6ContractError, "positive and odd"):
            make_line_template_bank(count=92, expected_sha256=None)

    def test_score_grid_is_exact_crop_of_support_grid(self):
        grid = make_proxy_carrier_grid(1400.5, 2.835503418452676, 5, 2)
        self.assertEqual(grid.support_bin_count, 15)
        self.assertEqual(grid.score_bin_count, 11)
        np.testing.assert_array_equal(grid.score_mhz, grid.support_mhz[2:-2])
        self.assertAlmostEqual(grid.score_mhz[5], 1400.5)
        self.assertAlmostEqual(
            (grid.score_mhz[6] - grid.score_mhz[5]) * 1e6,
            2.835503418452676,
            places=7,
        )

    def test_m37_wrapper_dimensions_and_explicit_scramble_identities(self):
        grid = make_m37_proxy_carrier_grid("m37_1400p5")
        self.assertEqual(grid.score_bin_count, 747_665)
        self.assertEqual(grid.support_bin_count, 747_793)
        tables = generate_m37_scramble_tables_for_preregistration()
        sealed = validate_m37_scramble_tables(tables)
        self.assertEqual(
            tuple(scramble_table_sha256(item) for item in sealed),
            M37_SCRAMBLE_TABLE_SHA256S,
        )
        aggregate = np.asarray(
            np.stack(sealed, axis=0), dtype="<i8", order="C"
        )
        import hashlib

        self.assertEqual(
            hashlib.sha256(aggregate.tobytes()).hexdigest(),
            M37_SCRAMBLE_TABLES_SHA256,
        )
        with patch.object(
            v06,
            "make_scramble_shift_table",
            side_effect=AssertionError("production loader invoked the RNG path"),
        ):
            loaded = load_m37_scramble_tables()
        self.assertEqual(len(M37_SCRAMBLE_RESOURCE_NAMES), 5)
        for loaded_table, generated_table in zip(loaded, sealed, strict=True):
            np.testing.assert_array_equal(loaded_table, generated_table)
            self.assertFalse(loaded_table.flags.writeable)
        first_payload = (
            ROOT / "src" / "seti_repeater" / M37_SCRAMBLE_RESOURCE_NAMES[0]
        ).read_bytes()
        corrupted = bytearray(first_payload)
        corrupted[-1] ^= 1
        with self.assertRaisesRegex(V0P6ContractError, "SHA-256 changed"):
            v06._decode_m37_scramble_resource(
                bytes(corrupted),
                expected_sha256=M37_SCRAMBLE_TABLE_SHA256S[0],
                resource_name=M37_SCRAMBLE_RESOURCE_NAMES[0],
            )
        calibration = make_m37_calibration(
            "m37_1400p5",
            sealed[0],
            factor_table_sha256_value="a" * 64,
        )
        self.assertEqual(
            calibration.experiment_contract_sha256,
            M37_EXPERIMENT_CONTRACT_SHA256,
        )
        self.assertEqual(len(calibration.expected_hypothesis_keys), 2_976)


class V0P6FactorBasisTests(unittest.TestCase):
    def test_factor_basis_has_an_independent_endian_layout_oracle(self):
        times = np.array([1.0, 2.0], dtype=np.float64)
        baseline = np.array([3.0, 4.0], dtype=np.float64)
        orbital = np.array([[5.0, 6.0], [7.0, 8.0]], dtype=np.float64)
        expected = "e521e21cbe4bcd4565351f5d355732f72f7d335ee4b22190fe65de4a2d4d791d"
        self.assertEqual(
            factor_basis_sha256(times, baseline, orbital), expected
        )
        self.assertEqual(
            factor_basis_sha256(
                times.astype(">f8"),
                baseline.astype(">f8"),
                np.asfortranarray(orbital.astype(">f8")),
            ),
            expected,
        )
        basis = make_factor_basis_from_arrays(
            times,
            (
                {"scan_index": 0, "scan_label": "epoch1_on", "integration_index": 0},
                {"scan_index": 0, "scan_label": "epoch1_on", "integration_index": 1},
            ),
            baseline,
            orbital,
            expected_sha256=expected,
        )
        self.assertFalse(basis.baseline.flags.writeable)
        template = {
            "coefficient_x": 0.5,
            "coefficient_y": -0.25,
            "projected_scale": 999.0,
            "phase_cycles": np.nan,
        }
        expected_factor = baseline + orbital @ np.array([0.5, -0.25])
        np.testing.assert_array_equal(
            template_factors_from_basis(basis, template), expected_factor
        )
        np.testing.assert_array_equal(
            template_factors_from_basis(
                basis, template, scan_label="epoch1_on"
            ),
            expected_factor,
        )

        bank = make_line_template_bank(count=3, expected_sha256=None)
        table = make_template_factor_table(
            basis,
            bank,
            expected_template_bank_sha256=template_bank_sha256(bank),
        )
        self.assertEqual(table.factors.shape, (3, 2))
        np.testing.assert_array_equal(
            factor_table_for_scan(table, basis, "epoch1_on"),
            table.factors,
        )
        self.assertFalse(table.factors.flags.writeable)
        validate_template_factor_table(
            table,
            basis,
            bank,
            expected_template_bank_sha256=template_bank_sha256(bank),
        )
        forged_factors = table.factors.copy()
        forged_factors[0, 0] = np.nextafter(forged_factors[0, 0], np.inf)
        forged_factors.setflags(write=False)
        import hashlib

        forged = replace(
            table,
            factors=forged_factors,
            factor_table_sha256=hashlib.sha256(
                np.ascontiguousarray(forged_factors, dtype="<f8").tobytes()
            ).hexdigest(),
        )
        with self.assertRaisesRegex(V0P6IncompleteError, "do not reproduce"):
            validate_template_factor_table(
                forged,
                basis,
                bank,
                expected_template_bank_sha256=template_bank_sha256(bank),
            )

    def test_factor_basis_labels_and_m37_roles_are_exact(self):
        config = json.loads(
            (ROOT / "config" / "hd156668b_m37_preflight.json").read_text()
        )
        labels = []
        for scan_index, scan in enumerate(config["scans"]):
            for integration_index in range(16):
                labels.append(
                    {
                        "scan_index": scan_index,
                        "scan_label": scan["label"],
                        "integration_index": integration_index,
                    }
                )
        basis = make_factor_basis_from_arrays(
            np.arange(96, dtype=np.float64) + 57_470.0,
            labels,
            np.ones(96, dtype=np.float64),
            np.zeros((96, 2), dtype=np.float64),
            expected_sha256=None,
        )
        validate_factor_basis_scan_inventory(basis, config["scans"])
        self.assertEqual(
            basis.labels_sha256, M37_FACTOR_BASIS_LABELS_SHA256
        )
        self.assertEqual(
            scan_inventory_sha256(config["scans"]),
            M37_SCAN_INVENTORY_SHA256,
        )
        self.assertNotEqual(
            factor_row_selection_sha256(basis, config["scans"], "on"),
            factor_row_selection_sha256(basis, config["scans"], "off"),
        )
        expected_rows = {
            "on": list(range(0, 16))
            + list(range(32, 48))
            + list(range(64, 80)),
            "off": list(range(16, 32))
            + list(range(48, 64))
            + list(range(80, 96)),
        }
        for kind, row_indices in expected_rows.items():
            payload = {
                "factor_basis_sha256": M37_FACTOR_BASIS_SHA256,
                "factor_basis_labels_sha256": (
                    M37_FACTOR_BASIS_LABELS_SHA256
                ),
                "scan_inventory_sha256": M37_SCAN_INVENTORY_SHA256,
                "scan_kind": kind,
                "factor_row_indices": row_indices,
            }
            self.assertEqual(
                hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
                M37_FACTOR_ROW_SELECTION_SHA256S[kind],
            )
        self.assertEqual(
            m37_scan_indices_for_kind(config["scans"], "on"), (0, 2, 4)
        )
        self.assertEqual(
            m37_scan_indices_for_kind(config["scans"], "off"), (1, 3, 5)
        )
        changed = list(config["scans"])
        changed[0], changed[1] = changed[1], changed[0]
        with self.assertRaisesRegex(V0P6ContractError, "ABABAB"):
            m37_scan_indices_for_kind(changed, "on")
        compensated = json.loads(json.dumps(config["scans"]))
        compensated[0]["expected_header"]["dataset_shape"][0] = 15
        compensated[1]["expected_header"]["dataset_shape"][0] = 17
        with self.assertRaisesRegex(V0P6ContractError, "16 integrations"):
            m37_scan_indices_for_kind(compensated, "on")

    def test_factor_basis_mutations_and_bad_labels_fail_closed(self):
        times = np.array([1.0, 2.0])
        baseline = np.ones(2)
        orbital = np.zeros((2, 2))
        duplicate_groups = (
            {"scan_index": 0, "scan_label": "same", "integration_index": 0},
            {"scan_index": 1, "scan_label": "same", "integration_index": 0},
        )
        with self.assertRaisesRegex(V0P6ContractError, "unique"):
            make_factor_basis_from_arrays(
                times,
                duplicate_groups,
                baseline,
                orbital,
                expected_sha256=None,
            )
        with self.assertRaisesRegex(V0P6ContractError, "SHA-256"):
            make_factor_basis_from_arrays(
                times,
                (
                    {"scan_index": 0, "scan_label": "scan", "integration_index": 0},
                    {"scan_index": 0, "scan_label": "scan", "integration_index": 1},
                ),
                baseline,
                orbital,
                expected_sha256="0" * 64,
            )
        basis = make_factor_basis_from_arrays(
            times,
            (
                {"scan_index": 0, "scan_label": "scan", "integration_index": 0},
                {"scan_index": 0, "scan_label": "scan", "integration_index": 1},
            ),
            baseline,
            orbital,
            expected_sha256=None,
        )
        basis.baseline.setflags(write=True)
        with self.assertRaisesRegex(V0P6IncompleteError, "identity changed"):
            template_factors_from_basis(
                basis, {"coefficient_x": 0.0, "coefficient_y": 0.0}
            )

    def test_production_epoch_builder_uses_sealed_factor_and_filter_tables(self):
        config = json.loads(
            (ROOT / "config" / "hd156668b_m37_preflight.json").read_text()
        )
        labels = [
            {
                "scan_index": scan_index,
                "scan_label": scan["label"],
                "integration_index": integration_index,
            }
            for scan_index, scan in enumerate(config["scans"])
            for integration_index in range(16)
        ]
        basis = make_factor_basis_from_arrays(
            np.arange(96, dtype=np.float64) + 57_470.0,
            labels,
            np.full(96, 1.01, dtype=np.float64),
            np.zeros((96, 2), dtype=np.float64),
            expected_sha256=None,
        )
        bank = [make_line_template_bank()[0]]
        table = make_template_factor_table(
            basis,
            bank,
            expected_template_bank_sha256=template_bank_sha256(bank),
        )
        frequency = native_axis(1000)
        geometry = geometry_for_axis(frequency, 1.0)
        grid = make_proxy_carrier_grid(0.0005, 1.0, 10, 4)
        caches = {}
        for scan_index in (0, 2, 4):
            definition = config["scans"][scan_index]
            label = definition["label"]
            scan_table = factor_table_for_scan(table, basis, label)
            plan = plan_native_filter_cache(
                geometry,
                scan_table,
                grid,
                1,
                window_id="synthetic",
                scan_label=label,
                scan_kind="on",
                source_sha256=f"{scan_index + 1:064x}",
                factor_basis_sha256_value=basis.basis_sha256,
                factor_basis_labels_sha256_value=basis.labels_sha256,
                scan_inventory_sha256_value=scan_inventory_sha256(
                    config["scans"]
                ),
                factor_scan_selection_sha256_value=(
                    factor_scan_selection_sha256(
                        basis, config["scans"], label
                    )
                ),
                template_bank_sha256_value=table.template_bank_sha256,
            )
            data = np.full(
                (16, 1000), scan_index + 1, dtype=np.float32
            )
            caches[label] = build_native_filter_cache(data, frequency, plan)
        with patch(
            "seti_repeater.search_v0p6.normalized_boxcar",
            side_effect=AssertionError("production gather refiltered native data"),
        ):
            vectors = build_epoch_vectors(
                caches,
                config["scans"],
                basis,
                table,
                0,
                grid,
                1,
                window_id="synthetic",
                kind="on",
                chunk_bins=3,
            )
        np.testing.assert_array_equal(
            vectors[:, 0], np.array([4.0, 12.0, 20.0], dtype=np.float32)
        )
        first_label = config["scans"][0]["label"]
        original_cache = caches[first_label]
        forged_plan = replace(
            original_cache.plan,
            factor_scan_selection_sha256="f" * 64,
            plan_sha256="",
        )
        forged_plan = replace(
            forged_plan,
            plan_sha256=hashlib.sha256(
                canonical_json_bytes(
                    v06._native_filter_cache_plan_payload(forged_plan)
                )
            ).hexdigest(),
        )
        forged_caches = dict(caches)
        forged_caches[first_label] = replace(
            original_cache,
            plan=forged_plan,
        )
        with self.assertRaisesRegex(
            V0P6ContractError,
            "cache identity differs",
        ):
            build_epoch_vectors(
                forged_caches,
                config["scans"],
                basis,
                table,
                0,
                grid,
                1,
                window_id="synthetic",
                kind="on",
                chunk_bins=3,
            )
        product = build_epoch_vector_product(
            caches,
            config["scans"],
            basis,
            table,
            bank,
            0,
            grid,
            1,
            window_id="synthetic",
            kind="on",
            expected_template_bank_sha256=template_bank_sha256(bank),
            chunk_bins=3,
        )
        validate_epoch_vector_product(product)
        np.testing.assert_array_equal(product.values, vectors)
        self.assertEqual(
            product.factor_row_selection_sha256,
            factor_row_selection_sha256(basis, config["scans"], "on"),
        )
        with self.assertRaises(ValueError):
            product.values.setflags(write=True)
        changed = product.values.copy()
        changed[0, 0] = np.nextafter(changed[0, 0], np.inf)
        changed = np.frombuffer(changed.tobytes(), dtype="<f4").reshape(
            changed.shape
        )
        forged = replace(product, values=changed)
        with self.assertRaisesRegex(V0P6ContractError, "factory receipt"):
            validate_epoch_vector_product(forged)
        rehashed = replace(
            product,
            values=changed,
            values_sha256=hashlib.sha256(memoryview(changed).cast("B")).hexdigest(),
            product_sha256="",
        )
        rehashed = replace(
            rehashed,
            product_sha256=hashlib.sha256(
                canonical_json_bytes(v06._epoch_vector_product_payload(rehashed))
            ).hexdigest(),
        )
        with self.assertRaisesRegex(V0P6ContractError, "factory receipt"):
            validate_epoch_vector_product(rehashed)
        replacement_values = np.frombuffer(
            np.full(product.values.shape, 999.0, dtype="<f4").tobytes(),
            dtype="<f4",
        ).reshape(product.values.shape)
        object.__setattr__(product, "values", replacement_values)
        with self.assertRaisesRegex(V0P6ContractError, "factory receipt"):
            validate_epoch_vector_product(product, verify_values=False)

    def test_m37_mask_product_is_factory_attested_and_width_complete(self):
        products = {}
        for width in v06.M37_SPECTRAL_WIDTHS:
            values = np.zeros((3, 31), dtype=np.float32)
            if width == 1:
                values[0, 15] = 11.0
            products[width] = v06._seal_epoch_vector_product(
                values,
                window_id="synthetic",
                scan_kind="on",
                template_index=0,
                width_channels=width,
                grid_sha256="b" * 64,
                factor_basis_sha256_value=M37_FACTOR_BASIS_SHA256,
                factor_basis_labels_sha256_value=(
                    M37_FACTOR_BASIS_LABELS_SHA256
                ),
                factor_row_selection_sha256_value=(
                    M37_FACTOR_ROW_SELECTION_SHA256S["on"]
                ),
                template_bank_sha256_value=M37_BANK_SHA256,
                factor_table_sha256_value="a" * 64,
                cache_plan_sha256s=tuple(
                    hashlib.sha256(f"plan-{width}-{index}".encode()).hexdigest()
                    for index in range(3)
                ),
                cache_payload_sha256s=tuple(
                    hashlib.sha256(
                        f"payload-{width}-{index}".encode()
                    ).hexdigest()
                    for index in range(3)
                ),
            )
        mask = build_m37_mask_product(products)
        validate_mask_product(mask)
        self.assertTrue(np.all(mask.values[0, 6:25]))
        self.assertEqual(int(np.count_nonzero(mask.values)), 19)
        changed_values = np.frombuffer(mask.values.tobytes(), dtype=np.bool_).reshape(
            mask.values.shape
        )
        changed_values = np.frombuffer(
            np.logical_not(changed_values).tobytes(), dtype=np.bool_
        ).reshape(mask.values.shape)
        rehashed = replace(
            mask,
            values=changed_values,
            values_sha256=hashlib.sha256(
                memoryview(changed_values).cast("B")
            ).hexdigest(),
            product_sha256="",
        )
        rehashed = replace(
            rehashed,
            product_sha256=hashlib.sha256(
                canonical_json_bytes(v06._mask_product_payload(rehashed))
            ).hexdigest(),
        )
        with self.assertRaisesRegex(V0P6ContractError, "factory receipt"):
            validate_mask_product(rehashed)
        registry_key = id(mask._receipt)
        del mask
        gc.collect()
        self.assertNotIn(registry_key, v06._MASK_PRODUCT_REGISTRY)

    def test_m37_calibration_uses_native_kernel_and_binds_execution_identity(self):
        from seti_repeater.calibration_kernel_v0p6 import (
            m37_null_scramble_maxima,
        )

        grid = make_m37_proxy_carrier_grid("m37_1400p5")
        shifts = load_m37_scramble_tables()[0]
        values = np.full((3, grid.score_bin_count), 4.0, dtype=np.float32)
        values[0, 17] = np.float32(8.0)
        products = {}
        for width in v06.M37_SPECTRAL_WIDTHS:
            products[width] = v06._seal_epoch_vector_product(
                values,
                window_id="m37_1400p5",
                scan_kind="on",
                template_index=0,
                width_channels=width,
                grid_sha256=v06.proxy_carrier_grid_sha256(grid),
                factor_basis_sha256_value=M37_FACTOR_BASIS_SHA256,
                factor_basis_labels_sha256_value=(
                    M37_FACTOR_BASIS_LABELS_SHA256
                ),
                factor_row_selection_sha256_value=(
                    M37_FACTOR_ROW_SELECTION_SHA256S["on"]
                ),
                template_bank_sha256_value=M37_BANK_SHA256,
                factor_table_sha256_value="a" * 64,
                cache_plan_sha256s=tuple(
                    hashlib.sha256(f"plan-{width}-{index}".encode()).hexdigest()
                    for index in range(3)
                ),
                cache_payload_sha256s=tuple(
                    hashlib.sha256(
                        f"payload-{width}-{index}".encode()
                    ).hexdigest()
                    for index in range(3)
                ),
            )
        mask = build_m37_mask_product(products)
        expected = m37_null_scramble_maxima(
            products[1].values,
            mask.values,
            shifts,
            thread_count=v06.M37_CALIBRATION_THREAD_COUNT,
        )
        calibration = make_m37_calibration(
            "m37_1400p5",
            shifts,
            factor_table_sha256_value="a" * 64,
        )
        v06.update_m37_calibration(
            calibration,
            products[1],
            exclusion_mask=mask,
        )
        np.testing.assert_array_equal(
            calibration.null_maxima.view(np.uint64),
            expected.view(np.uint64),
        )
        self.assertEqual(
            calibration.required_execution_engine,
            v06.M37_CALIBRATION_EXECUTION_ENGINE,
        )
        self.assertEqual(len(calibration.execution_engine_identity_sha256), 64)
        self.assertEqual(
            calibration.observed_score_cells,
            len(v06.M37_ACTIVITY_SUBSETS) * grid.score_bin_count,
        )
        self.assertEqual(
            calibration.null_score_cells,
            len(v06.M37_ACTIVITY_SUBSETS)
            * shifts.shape[0]
            * grid.score_bin_count,
        )

        wrong_engine = make_m37_calibration(
            "m37_1400p5",
            shifts,
            factor_table_sha256_value="a" * 64,
        )
        with self.assertRaisesRegex(V0P6IncompleteError, "execution engine"):
            update_calibration(
                wrong_engine,
                products[1].values,
                template_index=0,
                width_index=0,
                exclusion_mask=mask.values,
            )


class V0P6NativeFilterTests(unittest.TestCase):
    def test_direct_gathers_reject_inexact_spectral_widths(self):
        frequency = native_axis(100)
        data = np.zeros((1, 100), dtype=np.float32)
        geometry = geometry_for_axis(frequency, 1.0)
        factors = np.ones(1, dtype=np.float64)
        grid = make_proxy_carrier_grid(0.00005, 1.0, 5, 4)
        for gather in (
            native_filter_then_q_gather,
            materialized_reference_gather,
        ):
            with self.subTest(gather=gather.__name__):
                with self.assertRaisesRegex(V0P6ContractError, "exact integer"):
                    gather(
                        data,
                        frequency,
                        geometry,
                        factors,
                        grid,
                        3.2,
                    )

    def test_mapping_skip_proves_q_boxcar_false_negative(self):
        frequency = np.arange(12, dtype=np.float64)
        data = np.zeros((1, 12), dtype=np.float32)
        data[0, 6] = 1.0
        grid = make_proxy_carrier_grid(4.4, 1e6, 1, 0)
        factors = np.array([1.5], dtype=np.float64)
        geometry = geometry_for_axis(frequency, 1e6)
        mapped = nearest_native_indices(
            geometry, grid.support_hz * factors[0]
        )
        np.testing.assert_array_equal(mapped, [5, 7, 8])

        native_first = native_filter_then_q_gather(
            data, frequency, geometry, factors, grid, 3
        )
        gathered_first = data[0, mapped]
        forbidden_q_boxcar = normalized_boxcar(gathered_first, 3)
        self.assertAlmostEqual(float(native_first[1]), 1.0 / math.sqrt(3.0))
        self.assertEqual(float(forbidden_q_boxcar[1]), 0.0)

    def test_identity_mapping_agrees_on_q_boxcar_interior(self):
        frequency = np.arange(20, dtype=np.float64)
        data = np.arange(20, dtype=np.float32)[None, :]
        grid = make_proxy_carrier_grid(10.0, 1e6, 4, 0)
        factors = np.array([1.0])
        geometry = geometry_for_axis(frequency, 1e6)
        native_first = native_filter_then_q_gather(
            data, frequency, geometry, factors, grid, 3
        )
        mapped = nearest_native_indices(geometry, grid.score_hz)
        forbidden_but_identity = normalized_boxcar(data[0, mapped], 3)
        np.testing.assert_array_equal(native_first[1:-1], forbidden_but_identity[1:-1])

    def test_streaming_matches_materialized_and_literal_all_widths(self):
        rng = np.random.default_rng(3706001)
        frequency = native_axis(1000)
        data = rng.normal(size=(3, 1000)).astype(np.float32)
        factors = np.array([1.02, 1.03, 1.01], dtype=np.float64)
        grid = make_proxy_carrier_grid(0.0005, 1.0, 20, 64)
        geometry = geometry_for_axis(frequency, 1.0)
        for width in (1, 3, 5, 9, 17, 33, 65, 129):
            reference = materialized_reference_gather(
                data,
                frequency,
                geometry,
                factors,
                grid,
                width,
                return_support=True,
            )
            literal = literal_raw_filter_oracle(
                data, frequency, geometry, factors, grid.support_mhz, width
            )
            np.testing.assert_allclose(reference, literal, rtol=0.0, atol=5e-7)
            for chunk_bins in (1, 7, 31, grid.support_bin_count + 1):
                streamed = native_filter_then_q_gather(
                    data,
                    frequency,
                    geometry,
                    factors,
                    grid,
                    width,
                    chunk_bins=chunk_bins,
                    return_support=True,
                )
                np.testing.assert_array_equal(streamed, reference)

    def test_planned_native_cache_reuses_one_filter_bit_for_bit(self):
        rng = np.random.default_rng(3706012)
        frequency = native_axis(1000)
        data = rng.normal(size=(3, 1000)).astype(np.float32)
        factor_table = np.array(
            [[1.02, 1.03, 1.01], [1.01, 1.02, 1.04]], dtype=np.float64
        )
        grid = make_proxy_carrier_grid(0.0005, 1.0, 20, 64)
        geometry = geometry_for_axis(frequency, 1.0)
        for width in (1, 3, 5, 9, 17, 33, 65, 129):
            plan = plan_native_filter_cache(
                geometry,
                factor_table,
                grid,
                width,
                window_id="synthetic",
                scan_label="epoch1_on",
                scan_kind="on",
                source_sha256="1" * 64,
                factor_basis_sha256_value=M37_FACTOR_BASIS_SHA256,
                factor_basis_labels_sha256_value=(
                    M37_FACTOR_BASIS_LABELS_SHA256
                ),
                scan_inventory_sha256_value=M37_SCAN_INVENTORY_SHA256,
                factor_scan_selection_sha256_value=(
                    v06.M37_FACTOR_SCAN_SELECTION_SHA256S["epoch1_on"]
                ),
                template_bank_sha256_value=M37_BANK_SHA256,
            )
            exhaustive = np.concatenate(
                [
                    nearest_native_indices(
                        geometry, grid.support_hz * factor
                    )
                    for factor in factor_table.ravel()
                ]
            )
            self.assertEqual(plan.raw_center_start, int(np.min(exhaustive)))
            self.assertEqual(plan.raw_center_stop, int(np.max(exhaustive)) + 1)
            expected_by_template = [
                native_filter_then_q_gather(
                    data,
                    frequency,
                    geometry,
                    factors,
                    grid,
                    width,
                    return_support=True,
                )
                for factors in factor_table
            ]
            with patch(
                "seti_repeater.search_v0p6.normalized_boxcar",
                wraps=normalized_boxcar,
            ) as filter_spy:
                cache = build_native_filter_cache(data, frequency, plan)
                for factors, expected in zip(
                    factor_table, expected_by_template, strict=True
                ):
                    for chunk_bins in (1, 17, grid.support_bin_count + 1):
                        observed = gather_filtered_native(
                            cache,
                            factors,
                            grid,
                            chunk_bins=chunk_bins,
                            return_support=True,
                        )
                        np.testing.assert_array_equal(observed, expected)
                self.assertEqual(filter_spy.call_count, 1)

    def test_native_cache_identity_and_coverage_fail_closed(self):
        frequency = native_axis(1000)
        data = np.ones((2, 1000), dtype=np.float32)
        geometry = geometry_for_axis(frequency, 1.0)
        grid = make_proxy_carrier_grid(0.0005, 1.0, 10, 4)
        planned_factors = np.array(
            [[1.01, 1.01], [1.04, 1.04]], dtype=np.float64
        )
        plan = plan_native_filter_cache(
            geometry,
            planned_factors,
            grid,
            3,
            window_id="synthetic",
            scan_label="epoch1_on",
            scan_kind="on",
            source_sha256="1" * 64,
            factor_basis_sha256_value=M37_FACTOR_BASIS_SHA256,
            factor_basis_labels_sha256_value=M37_FACTOR_BASIS_LABELS_SHA256,
            scan_inventory_sha256_value=M37_SCAN_INVENTORY_SHA256,
            factor_scan_selection_sha256_value=(
                v06.M37_FACTOR_SCAN_SELECTION_SHA256S["epoch1_on"]
            ),
            template_bank_sha256_value=M37_BANK_SHA256,
        )
        cache = build_native_filter_cache(
            data[:, ::-1], frequency[::-1].copy(), plan
        )
        cache.values.setflags(write=True)
        with self.assertRaisesRegex(V0P6IncompleteError, "cache changed"):
            gather_filtered_native(cache, planned_factors[0], grid)

        fresh = build_native_filter_cache(data, frequency, plan)
        with self.assertRaisesRegex(V0P6ContractError, "absent"):
            gather_filtered_native(fresh, np.full(2, 1.02), grid)
        alternate_partition = make_proxy_carrier_grid(0.0005, 1.0, 12, 2)
        np.testing.assert_array_equal(
            alternate_partition.support_hz, grid.support_hz
        )
        with self.assertRaisesRegex(V0P6ContractError, "grid identities"):
            gather_filtered_native(
                fresh, planned_factors[0], alternate_partition
            )
        corrupted_plan = replace(plan, width_channels=1)
        with self.assertRaisesRegex(V0P6ContractError, "plan SHA-256"):
            build_native_filter_cache(data, frequency, corrupted_plan)

    def test_descending_native_axis_matches_ascending(self):
        rng = np.random.default_rng(3706002)
        ascending_frequency = native_axis(700)
        ascending_data = rng.normal(size=(2, 700)).astype(np.float32)
        descending_frequency = ascending_frequency[::-1].copy()
        descending_data = ascending_data[:, ::-1].copy()
        grid = make_proxy_carrier_grid(0.00035, 1.0, 15, 10)
        factors = np.array([1.01, 1.02])
        geometry = geometry_for_axis(ascending_frequency, 1.0)
        ascending = native_filter_then_q_gather(
            ascending_data,
            ascending_frequency,
            geometry,
            factors,
            grid,
            33,
        )
        descending = native_filter_then_q_gather(
            descending_data,
            descending_frequency,
            geometry,
            factors,
            grid,
            33,
        )
        np.testing.assert_array_equal(ascending, descending)

    def test_width129_support_guard_keeps_normative_edges_responsive(self):
        frequency = native_axis(1000)
        grid = make_proxy_carrier_grid(0.0005, 1.0, 2, 64)
        factor = np.array([1.02])
        geometry = geometry_for_axis(frequency, 1.0)
        score_indices = nearest_native_indices(
            geometry, grid.score_hz * factor[0]
        )
        data = np.zeros((1, 1000), dtype=np.float32)
        data[0, score_indices[0] - 64] = 1.0
        data[0, score_indices[-1] + 64] = 2.0
        score = native_filter_then_q_gather(
            data, frequency, geometry, factor, grid, 129
        )
        support = native_filter_then_q_gather(
            data,
            frequency,
            geometry,
            factor,
            grid,
            129,
            return_support=True,
        )
        self.assertEqual(score.size, 5)
        self.assertEqual(support.size, 133)
        self.assertTrue(np.all(np.isfinite(score)))
        self.assertGreater(float(score[0]), 0.0)
        self.assertGreater(float(score[-1]), float(score[0]))
        np.testing.assert_array_equal(score, support[64:-64])

    def test_noninjective_mapping_and_filter_edge_fail_closed(self):
        frequency = native_axis(100)
        data = np.zeros((1, 100), dtype=np.float32)
        geometry = geometry_for_axis(frequency, 1.0)
        duplicate_grid = make_proxy_carrier_grid(0.00005, 1.0, 5, 0)
        with self.assertRaisesRegex(V0P6ContractError, "not injective"):
            native_filter_then_q_gather(
                data,
                frequency,
                geometry,
                np.array([0.5]),
                duplicate_grid,
                1,
            )
        edge_grid = make_proxy_carrier_grid(0.000005, 1.0, 2, 0)
        with self.assertRaises(V0P6CoverageError):
            native_filter_then_q_gather(
                data,
                frequency,
                geometry,
                np.array([1.0]),
                edge_grid,
                17,
            )

    def test_materialized_reference_has_a_hard_cell_cap(self):
        frequency = native_axis(100)
        data = np.zeros((3, 100), dtype=np.float32)
        grid = make_proxy_carrier_grid(0.00005, 1.0, 10, 0)
        geometry = geometry_for_axis(frequency, 1.0)
        with self.assertRaises(V0P6CapacityError):
            materialized_reference_gather(
                data,
                frequency,
                geometry,
                np.ones(3),
                grid,
                1,
                maximum_mapping_cells=62,
            )

    def test_rint_ties_to_even_with_nextafter_guards(self):
        geometry = NativeFrequencyGeometry(0.0, 1.0, 6)
        half = 0.5
        requested = np.array(
            [
                np.nextafter(half, -np.inf),
                half,
                np.nextafter(half, np.inf),
                1.5,
                2.5,
            ]
        )
        np.testing.assert_array_equal(
            nearest_native_indices(geometry, requested), [0, 0, 1, 2, 2]
        )
        descending_geometry = NativeFrequencyGeometry(0.0, 1.0, 6)
        requested_descending = np.array(
            [
                np.nextafter(4.5, np.inf),
                4.5,
                np.nextafter(4.5, -np.inf),
                3.5,
                2.5,
            ]
        )
        np.testing.assert_array_equal(
            nearest_native_indices(descending_geometry, requested_descending),
            [5, 4, 4, 4, 2],
        )

    def test_published_mapping_skip_witnesses(self):
        config = json.loads(
            (ROOT / "config" / "hd156668b_m37_preflight.json").read_text()
        )
        header = config["scans"][0]["expected_header"]
        start = 167_400_554
        stop = 168_317_500
        raw_frequency = (
            float(header["fch1_mhz"])
            + np.arange(start, stop, dtype=np.float64)
            * float(header["foff_mhz"])
        )
        if raw_frequency[0] > raw_frequency[-1]:
            raw_frequency = raw_frequency[::-1].copy()
        geometry = native_geometry_from_extraction(
            fch1_mhz=float(header["fch1_mhz"]),
            foff_mhz=float(header["foff_mhz"]),
            channel_start=start,
            channel_stop=stop,
        )
        grid = make_proxy_carrier_grid(
            1400.5, 2.835503418452676, 373_832, 64
        )
        for factor, expected_skips in (
            (1.0000629897424504, 48),
            (1.0000519857551609, 38),
        ):
            mapped = nearest_native_indices(geometry, grid.support_hz * factor)
            steps = np.abs(np.diff(mapped))
            self.assertEqual(set(np.unique(steps)), {1, 2})
            self.assertEqual(
                abs(int(mapped[-1]) - int(mapped[0])) + 1 - mapped.size,
                expected_skips,
            )
        frozen = nearest_native_indices(
            geometry, grid.support_hz * 1.0000629897424504
        )
        inferred_df_mhz = float(raw_frequency[1] - raw_frequency[0])
        forbidden_inferred = np.rint(
            (
                grid.support_mhz * 1.0000629897424504
                - float(raw_frequency[0])
            )
            / inferred_df_mhz
        ).astype(np.int64)
        self.assertEqual(np.count_nonzero(frozen != forbidden_inferred), 2_488)


class V0P6MaskCalibrationTests(unittest.TestCase):
    def test_two_pass_mask_rejects_inexact_spectral_widths(self):
        with self.assertRaisesRegex(V0P6ContractError, "exact integer"):
            build_two_pass_template_mask(
                lambda _width: np.zeros((3, 5), dtype=np.float32),
                (1.9,),
                strong_snr=10.0,
                other_epochs_below_snr=3.0,
                guard_bins=2,
            )

    def test_two_pass_width_or_mask_and_clipped_dilation(self):
        vectors = {
            1: np.zeros((3, 15), dtype=np.float32),
            3: np.zeros((3, 15), dtype=np.float32),
        }
        vectors[1][0, 0] = 12.0
        vectors[3][2, 10] = 11.0
        mask = build_two_pass_template_mask(
            lambda width: vectors[width],
            (1, 3),
            strong_snr=10.0,
            other_epochs_below_snr=3.0,
            guard_bins=2,
        )
        self.assertTrue(np.all(mask[0, :3]))
        self.assertFalse(mask[0, -1])
        self.assertTrue(np.all(mask[2, 8:13]))
        self.assertFalse(np.any(mask[1]))

    def test_stack_rejects_nonfinite_masked_and_floor_cells(self):
        vectors = np.zeros((3, 7), dtype=np.float32)
        vectors[0, 1] = np.nan
        vectors[1, 1] = 5.0
        vectors[0:2, 2] = np.inf
        vectors[0, 3] = 4.0
        vectors[1, 3] = 2.0
        vectors[0:2, 4] = 4.0
        mask = np.zeros_like(vectors, dtype=bool)
        mask[0, 4] = True
        score = stack_hypothesis(
            vectors,
            (0, 1),
            minimum_active_epoch_snr=3.0,
            stack_statistic="minimum_epoch",
            exclusion_mask=mask,
        )
        self.assertTrue(np.all(np.isneginf(score[[1, 2, 3, 4]])))
        with self.assertRaisesRegex(V0P6ContractError, "strictly increasing"):
            stack_hypothesis(
                vectors,
                (1, 0),
                minimum_active_epoch_snr=3.0,
                stack_statistic="minimum_epoch",
            )
        with self.assertRaisesRegex(V0P6ContractError, "must be finite"):
            build_two_pass_template_mask(
                lambda width: vectors,
                (1,),
                strong_snr=np.nan,
                other_epochs_below_snr=3.0,
                guard_bins=2,
            )

    def test_streaming_calibration_is_order_invariant_and_counts_all_cells(self):
        rng = np.random.default_rng(3706003)
        left = rng.normal(size=(3, 31)).astype(np.float32)
        right = rng.normal(size=(3, 31)).astype(np.float32)
        mask = np.zeros((3, 31), dtype=bool)
        mask[1, 5:8] = True
        subsets = ((0, 1), (0, 2), (1, 2), (0, 1, 2))
        shifts = make_scramble_shift_table(
            7, 3, 31, seed=370606, minimum_shift_bins=4
        )
        shift_sha = scramble_table_sha256(shifts)
        create_kwargs = {
            "window_id": "synthetic",
            "score_bin_count": 31,
            "template_count": 2,
            "template_bank_sha256_value": M37_BANK_SHA256,
            "factor_basis_sha256_value": M37_FACTOR_BASIS_SHA256,
            "factor_basis_labels_sha256_value": M37_FACTOR_BASIS_LABELS_SHA256,
            "scan_inventory_sha256_value": M37_SCAN_INVENTORY_SHA256,
            "factor_row_selection_sha256_value": M37_FACTOR_ROW_SELECTION_SHA256S["on"],
            "factor_table_sha256_value": "a" * 64,
            "spectral_widths": (1,),
            "activity_subsets": subsets,
            "minimum_active_epoch_snr": 0.0,
            "stack_statistic": "minimum_epoch",
            "scramble_shifts": shifts,
            "minimum_shift_bins": 4,
            "expected_scramble_sha256": shift_sha,
        }
        first = CalibrationAccumulator.create(**create_kwargs)
        second = CalibrationAccumulator.create(**create_kwargs)
        for accumulator, sequence in (
            (first, ((0, left), (1, right))),
            (second, ((1, right), (0, left))),
        ):
            for template_index, vectors in sequence:
                update_calibration(
                    accumulator,
                    vectors,
                    template_index=template_index,
                    width_index=0,
                    exclusion_mask=mask,
                )
            certificate = accumulator.finalize()
            self.assertTrue(certificate["sealed"])
        self.assertEqual(first.observed_maximum, second.observed_maximum)
        np.testing.assert_array_equal(first.null_maxima, second.null_maxima)
        self.assertEqual(first.observed_score_cells, 2 * 4 * 31)
        self.assertEqual(first.null_score_cells, 2 * 7 * 4 * 31)

    def test_calibration_inventory_is_mandatory_and_fail_closed(self):
        subsets = ((0, 1), (0, 2), (1, 2), (0, 1, 2))
        shifts = make_scramble_shift_table(
            3, 3, 19, seed=370608, minimum_shift_bins=3
        )
        kwargs = {
            "window_id": "synthetic",
            "score_bin_count": 19,
            "template_count": 1,
            "template_bank_sha256_value": M37_BANK_SHA256,
            "factor_basis_sha256_value": M37_FACTOR_BASIS_SHA256,
            "factor_basis_labels_sha256_value": M37_FACTOR_BASIS_LABELS_SHA256,
            "scan_inventory_sha256_value": M37_SCAN_INVENTORY_SHA256,
            "factor_row_selection_sha256_value": M37_FACTOR_ROW_SELECTION_SHA256S["on"],
            "factor_table_sha256_value": "a" * 64,
            "spectral_widths": (1,),
            "activity_subsets": subsets,
            "minimum_active_epoch_snr": 0.0,
            "stack_statistic": "minimum_epoch",
            "scramble_shifts": shifts,
            "minimum_shift_bins": 3,
            "expected_scramble_sha256": scramble_table_sha256(shifts),
        }
        vectors = np.ones((3, 19), dtype=np.float32)
        missing = CalibrationAccumulator.create(**kwargs)
        with self.assertRaisesRegex(V0P6IncompleteError, "inventory mismatch"):
            missing.finalize()

        duplicate = CalibrationAccumulator.create(**kwargs)
        update_calibration(
            duplicate,
            vectors,
            template_index=0,
            width_index=0,
            exclusion_mask=None,
        )
        with self.assertRaisesRegex(V0P6IncompleteError, "duplicate"):
            update_calibration(
                duplicate,
                vectors,
                template_index=0,
                width_index=0,
                exclusion_mask=None,
            )
        with self.assertRaises(V0P6IncompleteError):
            duplicate.finalize()

        wrong = CalibrationAccumulator.create(**kwargs)
        with self.assertRaisesRegex(V0P6IncompleteError, "unexpected"):
            update_calibration(
                wrong,
                vectors,
                template_index=99,
                width_index=0,
                exclusion_mask=None,
            )
        self.assertEqual(
            make_hypothesis_inventory(1, (1,), subsets),
            wrong.expected_hypothesis_keys,
        )

        fractional = CalibrationAccumulator.create(**kwargs)
        with self.assertRaisesRegex(V0P6ContractError, "exact integer"):
            update_calibration(
                fractional,
                vectors,
                template_index=0.9,
                width_index=0,
                exclusion_mask=None,
            )

        forged = CalibrationAccumulator.create(**kwargs)
        update_calibration(
            forged,
            vectors,
            template_index=0,
            width_index=0,
            exclusion_mask=None,
        )
        forged.null_maxima[:] = -999.0
        with self.assertRaisesRegex(V0P6IncompleteError, "outside the updater"):
            forged.finalize()

    def test_calibration_rejects_transient_scramble_table_substitution(self):
        first_shifts = make_scramble_shift_table(
            3, 3, 19, seed=370620, minimum_shift_bins=3
        )
        second_shifts = make_scramble_shift_table(
            3, 3, 19, seed=370621, minimum_shift_bins=3
        ).copy()
        second_shifts.setflags(write=False)
        accumulator = CalibrationAccumulator.create(
            window_id="synthetic",
            score_bin_count=19,
            template_count=2,
            template_bank_sha256_value=M37_BANK_SHA256,
            factor_basis_sha256_value=M37_FACTOR_BASIS_SHA256,
            factor_basis_labels_sha256_value=M37_FACTOR_BASIS_LABELS_SHA256,
            scan_inventory_sha256_value=M37_SCAN_INVENTORY_SHA256,
            factor_row_selection_sha256_value=(
                M37_FACTOR_ROW_SELECTION_SHA256S["on"]
            ),
            factor_table_sha256_value="a" * 64,
            spectral_widths=(1,),
            activity_subsets=((0, 1),),
            minimum_active_epoch_snr=None,
            stack_statistic="sum",
            scramble_shifts=first_shifts,
            minimum_shift_bins=3,
            expected_scramble_sha256=scramble_table_sha256(first_shifts),
        )
        vectors = np.ones((3, 19), dtype=np.float32)
        update_calibration(
            accumulator,
            vectors,
            template_index=0,
            width_index=0,
            exclusion_mask=None,
        )
        accumulator.scramble_shifts = second_shifts
        accumulator.scramble_table_sha256 = scramble_table_sha256(
            second_shifts
        )
        with self.assertRaisesRegex(V0P6IncompleteError, "outside the updater"):
            update_calibration(
                accumulator,
                vectors,
                template_index=1,
                width_index=0,
                exclusion_mask=None,
            )

    def test_empty_scrambles_and_mixed_global_contracts_are_rejected(self):
        with self.assertRaisesRegex(V0P6ContractError, "at least one"):
            validate_scramble_shift_table(
                np.empty((0, 3), dtype=np.int64),
                epoch_count=3,
                score_bin_count=11,
                minimum_shift_bins=2,
            )

        def sealed(window_id, score_bin_count, seed):
            shifts = make_scramble_shift_table(
                3, 3, score_bin_count, seed=seed, minimum_shift_bins=2
            )
            accumulator = CalibrationAccumulator.create(
                window_id=window_id,
                score_bin_count=score_bin_count,
                template_count=1,
                template_bank_sha256_value=M37_BANK_SHA256,
                factor_basis_sha256_value=M37_FACTOR_BASIS_SHA256,
                factor_basis_labels_sha256_value=M37_FACTOR_BASIS_LABELS_SHA256,
                scan_inventory_sha256_value=M37_SCAN_INVENTORY_SHA256,
                factor_row_selection_sha256_value=M37_FACTOR_ROW_SELECTION_SHA256S["on"],
                factor_table_sha256_value="a" * 64,
                spectral_widths=(1,),
                activity_subsets=((0, 1),),
                minimum_active_epoch_snr=3.0,
                stack_statistic="minimum_epoch",
                scramble_shifts=shifts,
                minimum_shift_bins=2,
                expected_scramble_sha256=scramble_table_sha256(shifts),
            )
            update_calibration(
                accumulator,
                np.full((3, score_bin_count), 4.0, dtype=np.float32),
                template_index=0,
                width_index=0,
                exclusion_mask=None,
            )
            accumulator.finalize()
            return accumulator

        left = sealed("left", 11, 370610)
        right = sealed("right", 13, 370611)
        self.assertNotEqual(
            left.experiment_contract_sha256,
            right.experiment_contract_sha256,
        )
        with self.assertRaisesRegex(V0P6IncompleteError, "experiment contract"):
            calibrated_threshold(
                (left, right),
                expected_window_ids=("left", "right"),
                reference_floor=7.0,
            )

    def test_scramble_table_and_threshold_are_deterministic(self):
        first = make_scramble_shift_table(
            16, 3, 101, seed=370607, minimum_shift_bins=9
        )
        second = make_scramble_shift_table(
            16, 3, 101, seed=370607, minimum_shift_bins=9
        )
        np.testing.assert_array_equal(first, second)
        self.assertTrue(np.all(first[:, 0] == 0))
        self.assertEqual(scramble_table_sha256(first), scramble_table_sha256(second))
        validate_scramble_shift_table(
            first,
            epoch_count=3,
            score_bin_count=101,
            minimum_shift_bins=9,
            expected_sha256=scramble_table_sha256(first),
        )
        changed = first.copy()
        changed[0, 1] += 1
        self.assertNotEqual(scramble_table_sha256(first), scramble_table_sha256(changed))
        changed[:, 0] = 1
        with self.assertRaisesRegex(V0P6ContractError, "epoch zero"):
            validate_scramble_shift_table(
                changed,
                epoch_count=3,
                score_bin_count=101,
                minimum_shift_bins=9,
            )
        calibration = CalibrationAccumulator.create(
            window_id="synthetic",
            score_bin_count=101,
            template_count=1,
            template_bank_sha256_value=M37_BANK_SHA256,
            factor_basis_sha256_value=M37_FACTOR_BASIS_SHA256,
            factor_basis_labels_sha256_value=M37_FACTOR_BASIS_LABELS_SHA256,
            scan_inventory_sha256_value=M37_SCAN_INVENTORY_SHA256,
            factor_row_selection_sha256_value=M37_FACTOR_ROW_SELECTION_SHA256S["on"],
            factor_table_sha256_value="a" * 64,
            spectral_widths=(1,),
            activity_subsets=((0, 1),),
            minimum_active_epoch_snr=None,
            stack_statistic="minimum_epoch",
            scramble_shifts=first,
            minimum_shift_bins=9,
            expected_scramble_sha256=scramble_table_sha256(first),
        )
        vectors = np.random.default_rng(370609).normal(size=(3, 101)).astype(
            np.float32
        )
        update_calibration(
            calibration,
            vectors,
            template_index=0,
            width_index=0,
            exclusion_mask=None,
        )
        calibration.finalize()
        self.assertEqual(
            calibration.null_maxima_sha256,
            float64_vector_sha256(calibration.null_maxima),
        )
        with self.assertRaises(ValueError):
            calibration.null_maxima[0] = 0.0
        result = calibrated_threshold(
            (calibration,),
            expected_window_ids=("synthetic",),
            reference_floor=-100.0,
            quantile=0.99,
        )
        expected = float(
            np.quantile(calibration.null_maxima, 0.99, method="higher")
        )
        self.assertEqual(result["empirical_higher_quantile_snr"], expected)
        self.assertEqual(result["operational_threshold_snr"], expected)
        self.assertTrue(result["scientific_eligibility_requires_rank_p"])
        self.assertEqual(
            empirical_global_pvalue(
                (calibration,),
                expected_window_ids=("synthetic",),
                score=float(np.max(calibration.null_maxima)) + 1.0,
            ),
            1.0 / 17.0,
        )
        self.assertGreater(result["inclusive_rank_p_at_threshold"], 0.01)


class V0P6RetentionTests(unittest.TestCase):
    def setUp(self):
        self.template = make_line_template_bank()[0]
        self.grid = make_proxy_carrier_grid(1400.5, 1.0, 4, 2)

    def make_ledger(
        self,
        window_id,
        grid,
        threshold,
        maximum_records,
        *,
        template_bank=None,
        spectral_widths=(1,),
        activity_subsets=((0, 1),),
        epoch_count=3,
        minimum_active_epoch_snr=None,
        stack_statistic="sum",
        scan_kind="on",
        **kwargs,
    ):
        bank = [self.template] if template_bank is None else template_bank
        bank_digest = template_bank_sha256(bank)
        shifts = make_scramble_shift_table(
            1,
            epoch_count,
            grid.score_bin_count,
            seed=370612,
            minimum_shift_bins=1,
        )
        calibration = CalibrationAccumulator.create(
            window_id=window_id,
            score_bin_count=grid.score_bin_count,
            template_count=len(bank),
            template_bank_sha256_value=bank_digest,
            factor_basis_sha256_value=M37_FACTOR_BASIS_SHA256,
            factor_basis_labels_sha256_value=M37_FACTOR_BASIS_LABELS_SHA256,
            scan_inventory_sha256_value=M37_SCAN_INVENTORY_SHA256,
            factor_row_selection_sha256_value=M37_FACTOR_ROW_SELECTION_SHA256S["on"],
            factor_table_sha256_value="a" * 64,
            spectral_widths=spectral_widths,
            activity_subsets=activity_subsets,
            minimum_active_epoch_snr=minimum_active_epoch_snr,
            stack_statistic=stack_statistic,
            scramble_shifts=shifts,
            minimum_shift_bins=1,
            expected_scramble_sha256=scramble_table_sha256(shifts),
        )
        null_vectors = np.zeros(
            (epoch_count, grid.score_bin_count), dtype=np.float32
        )
        for template_index in range(len(bank)):
            for width_index in range(len(spectral_widths)):
                update_calibration(
                    calibration,
                    null_vectors,
                    template_index=template_index,
                    width_index=width_index,
                    exclusion_mask=None,
                )
        calibration.finalize()
        threshold_certificate = calibrated_threshold(
            (calibration,),
            expected_window_ids=(window_id,),
            reference_floor=threshold,
        )
        return ExhaustiveRetentionLedger(
            window_id=window_id,
            scan_kind=scan_kind,
            grid=grid,
            threshold_certificate=threshold_certificate,
            maximum_records=maximum_records,
            template_bank=bank,
            spectral_widths=spectral_widths,
            activity_subsets=activity_subsets,
            expected_template_bank_sha256=None,
            factor_basis_sha256=M37_FACTOR_BASIS_SHA256,
            factor_basis_labels_sha256=M37_FACTOR_BASIS_LABELS_SHA256,
            scan_inventory_sha256=M37_SCAN_INVENTORY_SHA256,
            factor_row_selection_sha256=M37_FACTOR_ROW_SELECTION_SHA256S[scan_kind],
            factor_table_sha256="a" * 64,
            epoch_count=epoch_count,
            minimum_active_epoch_snr=minimum_active_epoch_snr,
            stack_statistic=stack_statistic,
            **kwargs,
        )

    def make_sparse_retention_product(
        self,
        *,
        window_id,
        grid,
        bank,
        scan_kind,
        active_by_template,
        threshold=7.0,
    ):
        ledger = self.make_ledger(
            window_id,
            grid,
            threshold,
            100,
            template_bank=bank,
            scan_kind=scan_kind,
        )
        for template_index in range(len(bank)):
            vectors = np.zeros(
                (3, grid.score_bin_count), dtype=np.float32
            )
            for proxy_index, amplitude in active_by_template.get(
                template_index, ()
            ):
                vectors[0:2, proxy_index] = amplitude
            ledger.add_hypothesis(
                vectors,
                (0, 1),
                template=bank[template_index],
                width_index=0,
                width_channels=1,
                exclusion_mask=None,
            )
        return ledger.finalize(), ledger.certificate()

    def test_retention_rejects_record_mutation_before_finalize(self):
        grid = make_proxy_carrier_grid(0.0001, 1.0, 2, 0)
        ledger = self.make_ledger("synthetic", grid, 7.0, 100)
        vectors = np.full((3, grid.score_bin_count), 8.0, dtype=np.float32)
        ledger.add_hypothesis(
            vectors,
            (0, 1),
            template=self.template,
            width_index=0,
            width_channels=1,
            exclusion_mask=None,
        )
        ledger._records[0]["snr"] = 999_999.0
        with self.assertRaisesRegex(V0P6IncompleteError, "record bytes changed"):
            ledger.finalize()

        byte_count_ledger = self.make_ledger("synthetic-bytes", grid, 7.0, 100)
        byte_count_ledger.add_hypothesis(
            vectors,
            (0, 1),
            template=self.template,
            width_index=0,
            width_channels=1,
            exclusion_mask=None,
        )
        byte_count_ledger._canonical_record_bytes += 1
        with self.assertRaisesRegex(V0P6IncompleteError, "outside the updater"):
            byte_count_ledger.finalize()

        map_ledger = self.make_ledger("synthetic-map", grid, 7.0, 100)
        map_ledger.add_hypothesis(
            vectors,
            (0, 1),
            template=self.template,
            width_index=0,
            width_channels=1,
            exclusion_mask=None,
        )
        map_ledger._cache_provenance_by_width[0] = (
            ("1" * 64,) * 3,
            ("2" * 64,) * 3,
        )
        with self.assertRaisesRegex(V0P6IncompleteError, "outside the updater"):
            map_ledger.finalize()

    def test_persisted_retention_certificate_accepts_independent_digest(self):
        grid = make_proxy_carrier_grid(0.0001, 1.0, 2, 0)
        records, certificate = self.make_sparse_retention_product(
            window_id="synthetic",
            grid=grid,
            bank=[self.template],
            scan_kind="on",
            active_by_template={0: ((2, 8.0),)},
        )
        self.assertEqual(len(records), 1)
        digest = certificate["retention_certificate_sha256"]
        attestation = v06._RETENTION_CERTIFICATE_ATTESTATIONS.pop(digest)
        try:
            with self.assertRaisesRegex(V0P6ContractError, "trusted attestation"):
                v06.validate_retention_certificate(certificate)
            validated = v06.validate_retention_certificate(
                certificate,
                expected_certificate_sha256=digest,
            )
            self.assertEqual(validated["retention_certificate_sha256"], digest)
        finally:
            v06._RETENTION_CERTIFICATE_ATTESTATIONS[digest] = attestation

    def test_resealed_retention_json_numeric_type_changes_are_rejected(self):
        grid = make_proxy_carrier_grid(0.0001, 1.0, 2, 0)
        bank = [self.template]
        records, certificate = self.make_sparse_retention_product(
            window_id="synthetic",
            grid=grid,
            bank=bank,
            scan_kind="on",
            active_by_template={0: ((2, 8.0),)},
        )

        forged_certificate = dict(certificate)
        forged_certificate["operational_threshold_snr"] = str(
            forged_certificate["operational_threshold_snr"]
        )
        forged_certificate.pop("retention_certificate_sha256")
        forged_certificate["retention_certificate_sha256"] = hashlib.sha256(
            canonical_json_bytes(forged_certificate)
        ).hexdigest()
        with self.assertRaisesRegex(V0P6ContractError, "JSON num"):
            v06.validate_retention_certificate(
                forged_certificate,
                expected_certificate_sha256=forged_certificate[
                    "retention_certificate_sha256"
                ],
            )

        for label, mutate in (
            (
                "numeric string",
                lambda item: item.__setitem__(
                    "proxy_carrier_hz", str(item["proxy_carrier_hz"])
                ),
            ),
            (
                "boolean record-key integer",
                lambda item: (
                    item["record_key"].__setitem__("q_offset_bin", False),
                    item.__setitem__(
                        "record_id",
                        hashlib.sha256(
                            canonical_json_bytes(item["record_key"])
                        ).hexdigest(),
                    ),
                ),
            ),
        ):
            with self.subTest(label=label):
                forged_records = json.loads(canonical_json_bytes(records))
                mutate(forged_records[0])
                forged_certificate = dict(certificate)
                forged_certificate["records_sha256"] = hashlib.sha256(
                    canonical_json_bytes(forged_records)
                ).hexdigest()
                forged_certificate["canonical_record_bytes"] = sum(
                    len(canonical_json_bytes(item)) for item in forged_records
                )
                forged_certificate.pop("retention_certificate_sha256")
                forged_certificate[
                    "retention_certificate_sha256"
                ] = hashlib.sha256(
                    canonical_json_bytes(forged_certificate)
                ).hexdigest()
                with self.assertRaisesRegex(
                    V0P6ContractError, "JSON numeric types"
                ):
                    v06._validated_retained_records(
                        forged_records,
                        forged_certificate,
                        grid,
                        expected_kind="on",
                        expected_template_count=1,
                        template_bank=bank,
                        expected_certificate_sha256=forged_certificate[
                            "retention_certificate_sha256"
                        ],
                    )

    def test_rehydrated_threshold_rejects_numeric_strings(self):
        ledger = self.make_ledger("synthetic", self.grid, 7.0, 10)
        record = ledger.threshold_certificate.as_record()
        record["reference_floor_snr"] = str(record["reference_floor_snr"])
        record.pop("certificate_sha256")
        record["certificate_sha256"] = hashlib.sha256(
            canonical_json_bytes(record)
        ).hexdigest()
        with self.assertRaisesRegex(V0P6ContractError, "JSON number"):
            v06.threshold_certificate_from_record(
                record,
                expected_certificate_sha256=record["certificate_sha256"],
            )

    def test_persisted_on_off_products_match_with_trusted_digests(self):
        grid = make_proxy_carrier_grid(0.0001, 1.0, 2, 0)
        bank = [self.template]
        on_records, on_certificate = self.make_sparse_retention_product(
            window_id="synthetic",
            grid=grid,
            bank=bank,
            scan_kind="on",
            active_by_template={0: ((2, 8.0),)},
        )
        off_records, off_certificate = self.make_sparse_retention_product(
            window_id="synthetic",
            grid=grid,
            bank=bank,
            scan_kind="off",
            active_by_template={0: ((2, 8.0),)},
        )
        on_digest = on_certificate["retention_certificate_sha256"]
        off_digest = off_certificate["retention_certificate_sha256"]
        attestations = {
            on_digest: v06._RETENTION_CERTIFICATE_ATTESTATIONS.pop(on_digest),
            off_digest: v06._RETENTION_CERTIFICATE_ATTESTATIONS.pop(off_digest),
        }
        try:
            result = match_retained_off_tracks(
                on_records,
                on_certificate,
                off_records,
                off_certificate,
                grid,
                np.ones((1, 3), dtype=np.float64),
                window_order=("synthetic",),
                tolerance_hz=20.0,
                maximum_bucket_entries=1,
                maximum_exact_candidate_visits=1,
                expected_on_certificate_sha256=on_digest,
                expected_off_certificate_sha256=off_digest,
            )
            self.assertEqual(
                result["records"][0]["member_disposition"],
                "rfi_veto_matched_off_same_hypothesis",
            )
        finally:
            v06._RETENTION_CERTIFICATE_ATTESTATIONS.update(attestations)

    def test_threshold_inventory_cannot_be_rehashed_with_dataclass_replace(self):
        ledger = self.make_ledger("synthetic", self.grid, 7.0, 10)
        original = ledger.threshold_certificate
        forged = replace(
            original,
            calibration_epoch_product_inventory_sha256s=("c" * 64,),
            certificate_sha256="",
        )
        forged_record = forged.as_record()
        forged_record.pop("certificate_sha256")
        forged = replace(
            forged,
            certificate_sha256=hashlib.sha256(
                canonical_json_bytes(forged_record)
            ).hexdigest(),
        )
        with self.assertRaisesRegex(V0P6ContractError, "factory receipt"):
            v06.validate_threshold_certificate(forged)

    def test_persisted_threshold_certificate_requires_independent_digest(self):
        ledger = self.make_ledger("synthetic", self.grid, 7.0, 10)
        original = ledger.threshold_certificate
        record = original.as_record()
        digest = original.certificate_sha256
        attestation = v06._THRESHOLD_CERTIFICATE_REGISTRY.pop(
            id(original._receipt)
        )
        try:
            with self.assertRaisesRegex(
                V0P6ContractError, "live or trusted attestation"
            ):
                v06.validate_threshold_certificate(original)
            v06.validate_threshold_certificate(
                original,
                expected_certificate_sha256=digest,
            )
            loaded = v06.threshold_certificate_from_record(
                record,
                expected_certificate_sha256=digest,
            )
            v06.validate_threshold_certificate(loaded)
            self.assertEqual(loaded.as_record(), record)

            forged_record = dict(record)
            forged_record["reference_floor_snr"] = 8.0
            forged_record["operational_threshold_snr"] = max(
                8.0,
                forged_record["empirical_higher_quantile_snr"],
            )
            forged_record.pop("certificate_sha256")
            forged_record["certificate_sha256"] = hashlib.sha256(
                canonical_json_bytes(forged_record)
            ).hexdigest()
            with self.assertRaisesRegex(
                V0P6ContractError, "independently supplied identity"
            ):
                v06.threshold_certificate_from_record(
                    forged_record,
                    expected_certificate_sha256=digest,
                )
        finally:
            v06._THRESHOLD_CERTIFICATE_REGISTRY[
                id(original._receipt)
            ] = attestation

    def test_inclusive_complete_retention_without_frequency_alias(self):
        vectors = np.zeros((3, self.grid.score_bin_count), dtype=np.float32)
        vectors[0:2, 1:5] = 5.0
        exact_score = stack_hypothesis(
            vectors,
            (0, 1),
            minimum_active_epoch_snr=None,
            stack_statistic="sum",
        )
        mask = np.zeros_like(vectors, dtype=bool)
        mask[0, 3] = True
        ledger = self.make_ledger(
            "synthetic",
            self.grid,
            float(exact_score[1]),
            10,
        )
        ledger.add_hypothesis(
            vectors,
            (0, 1),
            template=self.template,
            width_index=0,
            width_channels=1,
            exclusion_mask=mask,
        )
        records = ledger.finalize()
        self.assertEqual([item["proxy_carrier_index"] for item in records], [1, 2, 4])
        self.assertTrue(all(item["snr"] == exact_score[1] for item in records))
        self.assertTrue(all("frequency_mhz" not in item for item in records))
        self.assertTrue(all("proxy_carrier_hz" in item for item in records))
        self.assertTrue(all("proxy_carrier_mhz" in item for item in records))
        self.assertTrue(
            all(
                item["proxy_carrier_hz"]
                == item["proxy_carrier_mhz"] * 1e6
                for item in records
            )
        )
        certificate = ledger.certificate()
        self.assertEqual(certificate["retained_record_count"], 3)
        self.assertFalse(certificate["truncation_permitted"])

    def test_scan_kind_separates_on_and_off_record_identities(self):
        vectors = np.ones((3, self.grid.score_bin_count), dtype=np.float32)
        products = []
        for scan_kind in ("on", "off"):
            ledger = self.make_ledger(
                "synthetic",
                self.grid,
                0.0,
                100,
                scan_kind=scan_kind,
            )
            ledger.add_hypothesis(
                vectors,
                (0, 1),
                template=self.template,
                width_index=0,
                width_channels=1,
                exclusion_mask=None,
            )
            products.append((ledger.finalize(), ledger.certificate()))
        on_records, on_certificate = products[0]
        off_records, off_certificate = products[1]
        self.assertEqual(on_certificate["scan_kind"], "on")
        self.assertEqual(off_certificate["scan_kind"], "off")
        self.assertTrue(
            set(item["record_id"] for item in on_records).isdisjoint(
                item["record_id"] for item in off_records
            )
        )

    def test_indexed_off_matching_equals_brute_force_and_is_order_invariant(self):
        grid = make_proxy_carrier_grid(0.0001, 1.0, 4, 0)
        bank = make_line_template_bank(count=3, expected_sha256=None)[:2]
        on_records, on_certificate = self.make_sparse_retention_product(
            window_id="synthetic",
            grid=grid,
            bank=bank,
            scan_kind="on",
            active_by_template={0: ((1, 8.0), (5, 8.0))},
        )
        off_records, off_certificate = self.make_sparse_retention_product(
            window_id="synthetic",
            grid=grid,
            bank=bank,
            scan_kind="off",
            active_by_template={0: ((1, 8.0),), 1: ((5, 9.0),)},
        )
        factors = np.ones((2, 4), dtype=np.float64)
        result = match_retained_off_tracks(
            on_records,
            on_certificate,
            off_records,
            off_certificate,
            grid,
            factors,
            window_order=("synthetic",),
            tolerance_hz=20.0,
            maximum_bucket_entries=10,
            maximum_exact_candidate_visits=100,
        )
        shuffled = match_retained_off_tracks(
            list(reversed(on_records)),
            on_certificate,
            list(reversed(off_records)),
            off_certificate,
            grid,
            factors,
            window_order=("synthetic",),
            tolerance_hz=20.0,
            maximum_bucket_entries=10,
            maximum_exact_candidate_visits=100,
        )
        self.assertEqual(
            canonical_json_bytes(result), canonical_json_bytes(shuffled)
        )
        forged_certificate = dict(on_certificate)
        for name in (
            "expected_hypotheses",
            "hypotheses_replayed",
            "expected_score_cells",
            "score_cells_replayed",
        ):
            forged_certificate[name] = 1
        forged_certificate.pop("retention_certificate_sha256")
        import hashlib

        forged_certificate["retention_certificate_sha256"] = hashlib.sha256(
            canonical_json_bytes(forged_certificate)
        ).hexdigest()
        with self.assertRaisesRegex(V0P6ContractError, "trusted attestation"):
            match_retained_off_tracks(
                on_records,
                forged_certificate,
                off_records,
                off_certificate,
                grid,
                factors,
                window_order=("synthetic",),
                tolerance_hz=20.0,
                maximum_bucket_entries=10,
                maximum_exact_candidate_visits=100,
            )
        self.assertEqual(
            [item["member_disposition"] for item in result["records"]],
            [
                "rfi_veto_matched_off_same_hypothesis",
                "rfi_veto_local_off_track",
            ],
        )
        certificate = result["certificate"]
        self.assertEqual(
            certificate["same_hypothesis_key_fields"],
            [
                "template_index",
                "proxy_carrier_index",
                "spectral_width_index",
                "active_epochs_zero_based",
            ],
        )
        self.assertEqual(
            certificate["disposition_precedence"],
            [
                "rfi_veto_matched_off_same_hypothesis",
                "rfi_veto_local_off_track",
                "pending_receiver_alias_evaluation",
            ],
        )
        certificate_without_digest = dict(certificate)
        observed_certificate_sha256 = certificate_without_digest.pop(
            "off_match_certificate_sha256"
        )
        self.assertEqual(
            observed_certificate_sha256,
            hashlib.sha256(
                canonical_json_bytes(certificate_without_digest)
            ).hexdigest(),
        )
        validated_off = v06.validate_off_match_result(
            result["records"],
            certificate,
            expected_certificate_sha256=observed_certificate_sha256,
        )
        self.assertEqual(
            validated_off["off_match_certificate_sha256"],
            observed_certificate_sha256,
        )

        def reseal_off_result(records, base_certificate):
            resealed = dict(base_certificate)
            resealed["annotated_records_sha256"] = hashlib.sha256(
                canonical_json_bytes(records)
            ).hexdigest()
            resealed["annotated_evidence_canonical_bytes"] = sum(
                len(canonical_json_bytes(item)) for item in records
            )
            resealed.pop("off_match_certificate_sha256", None)
            resealed["off_match_certificate_sha256"] = hashlib.sha256(
                canonical_json_bytes(resealed)
            ).hexdigest()
            return resealed

        forged_guard_certificate = dict(certificate)
        forged_guard_certificate[
            "maximum_anchor_pruning_roundoff_guard_hz"
        ] = str(
            forged_guard_certificate[
                "maximum_anchor_pruning_roundoff_guard_hz"
            ]
        )
        forged_guard_certificate = reseal_off_result(
            result["records"], forged_guard_certificate
        )
        with self.assertRaisesRegex(V0P6ContractError, "JSON number"):
            v06.validate_off_match_result(
                result["records"],
                forged_guard_certificate,
                expected_certificate_sha256=forged_guard_certificate[
                    "off_match_certificate_sha256"
                ],
            )

        for label, mutate in (
            (
                "annotated retained S/N",
                lambda record: record.__setitem__(
                    "snr", str(record["snr"])
                ),
            ),
            (
                "OFF witness S/N",
                lambda record: record["off_track_evidence"][
                    "same_hypothesis"
                ]["best_off_witness"].__setitem__(
                    "snr",
                    str(
                        record["off_track_evidence"]["same_hypothesis"]
                        ["best_off_witness"]["snr"]
                    ),
                ),
            ),
        ):
            with self.subTest(label=label):
                forged_records = json.loads(
                    canonical_json_bytes(result["records"])
                )
                mutate(forged_records[0])
                forged_certificate = reseal_off_result(
                    forged_records, certificate
                )
                with self.assertRaisesRegex(V0P6ContractError, "JSON num"):
                    v06.validate_off_match_result(
                        forged_records,
                        forged_certificate,
                        expected_certificate_sha256=forged_certificate[
                            "off_match_certificate_sha256"
                        ],
                    )
        mutated_off = json.loads(canonical_json_bytes(result["records"]))
        mutated_off[0]["member_disposition"] = (
            "pending_receiver_alias_evaluation"
        )
        with self.assertRaisesRegex(V0P6IncompleteError, "annotated records"):
            v06.validate_off_match_result(mutated_off, certificate)
        forged_off_certificate = dict(certificate)
        forged_off_certificate["annotated_records_sha256"] = hashlib.sha256(
            canonical_json_bytes(mutated_off)
        ).hexdigest()
        forged_off_certificate["disposition_counts"] = {
            **forged_off_certificate["disposition_counts"],
            "rfi_veto_matched_off_same_hypothesis": 0,
            "pending_receiver_alias_evaluation": 1,
        }
        forged_off_certificate.pop("off_match_certificate_sha256")
        forged_off_certificate["off_match_certificate_sha256"] = hashlib.sha256(
            canonical_json_bytes(forged_off_certificate)
        ).hexdigest()
        with self.assertRaisesRegex(V0P6ContractError, "precedence"):
            v06.validate_off_match_result(
                mutated_off,
                forged_off_certificate,
                expected_certificate_sha256=forged_off_certificate[
                    "off_match_certificate_sha256"
                ],
            )
        for on_record, annotated in zip(
            on_records, result["records"], strict=True
        ):
            on_track = (
                float(on_record["proxy_carrier_hz"])
                * factors[int(on_record["template_index"])]
            )
            brute = []
            for off_record in off_records:
                off_track = (
                    float(off_record["proxy_carrier_hz"])
                    * factors[int(off_record["template_index"])]
                )
                distance = float(np.max(np.abs(on_track - off_track)))
                if distance <= 20.0:
                    brute.append(off_record["record_id"])
            self.assertEqual(
                annotated["off_track_evidence"]["local_track"][
                    "matched_off_record_count"
                ],
                len(brute),
            )

    def test_off_track_literal_twenty_hz_boundary_and_caps(self):
        grid = make_proxy_carrier_grid(0.0001, 1.0, 1, 0)
        bank = make_line_template_bank(count=3, expected_sha256=None)[:2]
        on_records, on_certificate = self.make_sparse_retention_product(
            window_id="synthetic",
            grid=grid,
            bank=bank,
            scan_kind="on",
            active_by_template={0: ((1, 8.0),)},
        )
        off_records, off_certificate = self.make_sparse_retention_product(
            window_id="synthetic",
            grid=grid,
            bank=bank,
            scan_kind="off",
            active_by_template={1: ((1, 8.0),)},
        )
        factors = np.array(
            [[1.0] * 48, [1.2] * 48], dtype=np.float64
        )
        accepted = match_retained_off_tracks(
            on_records,
            on_certificate,
            off_records,
            off_certificate,
            grid,
            factors,
            window_order=("synthetic",),
            tolerance_hz=20.0,
            maximum_bucket_entries=1,
            maximum_exact_candidate_visits=1,
        )
        witness = accepted["records"][0]["off_track_evidence"][
            "local_track"
        ]["best_off_witness"]
        self.assertEqual(witness["maximum_track_distance_hz"], 20.0)
        subtraction_boundary = np.array(
            [[3.403217943645538], [0.3467112949013061]],
            dtype=np.float64,
        )
        subtraction_tolerance = 305.65066487442317
        self.assertEqual(
            abs(
                100.0 * subtraction_boundary[0, 0]
                - 100.0 * subtraction_boundary[1, 0]
            ),
            subtraction_tolerance,
        )
        guarded = match_retained_off_tracks(
            on_records,
            on_certificate,
            off_records,
            off_certificate,
            grid,
            subtraction_boundary,
            window_order=("synthetic",),
            tolerance_hz=subtraction_tolerance,
            maximum_bucket_entries=1,
            maximum_exact_candidate_visits=1,
        )
        self.assertTrue(
            guarded["records"][0]["off_track_evidence"]["local_track"][
                "matched"
            ]
        )
        last_row_outside = factors.copy()
        last_row_outside[1, -1] = np.nextafter(
            last_row_outside[1, -1], np.inf
        )
        late_rejected = match_retained_off_tracks(
            on_records,
            on_certificate,
            off_records,
            off_certificate,
            grid,
            last_row_outside,
            window_order=("synthetic",),
            tolerance_hz=20.0,
            maximum_bucket_entries=1,
            maximum_exact_candidate_visits=1,
        )
        self.assertEqual(
            late_rejected["certificate"]["exact_candidate_visits"], 1
        )
        self.assertFalse(
            late_rejected["records"][0]["off_track_evidence"][
                "local_track"
            ]["matched"]
        )
        outside = factors.copy()
        outside[1] = np.nextafter(outside[1], np.inf)
        rejected = match_retained_off_tracks(
            on_records,
            on_certificate,
            off_records,
            off_certificate,
            grid,
            outside,
            window_order=("synthetic",),
            tolerance_hz=20.0,
            maximum_bucket_entries=1,
            maximum_exact_candidate_visits=1,
        )
        self.assertFalse(
            rejected["records"][0]["off_track_evidence"]["local_track"][
                "matched"
            ]
        )
        dense_off_records, dense_off_certificate = (
            self.make_sparse_retention_product(
                window_id="synthetic",
                grid=grid,
                bank=bank,
                scan_kind="off",
                active_by_template={1: ((0, 8.0), (1, 8.0))},
            )
        )
        with self.assertRaisesRegex(V0P6CapacityError, "bucket-entry"):
            match_retained_off_tracks(
                on_records,
                on_certificate,
                dense_off_records,
                dense_off_certificate,
                grid,
                factors,
                window_order=("synthetic",),
                tolerance_hz=20.0,
                maximum_bucket_entries=1,
                maximum_exact_candidate_visits=100,
            )
        at_visit_cap = match_retained_off_tracks(
            on_records,
            on_certificate,
            dense_off_records,
            dense_off_certificate,
            grid,
            factors,
            window_order=("synthetic",),
            tolerance_hz=20.0,
            maximum_bucket_entries=2,
            maximum_exact_candidate_visits=2,
        )
        self.assertEqual(
            at_visit_cap["certificate"]["exact_candidate_visits"], 2
        )
        with self.assertRaisesRegex(V0P6CapacityError, "candidate-visit"):
            match_retained_off_tracks(
                on_records,
                on_certificate,
                dense_off_records,
                dense_off_certificate,
                grid,
                factors,
                window_order=("synthetic",),
                tolerance_hz=20.0,
                maximum_bucket_entries=2,
                maximum_exact_candidate_visits=1,
            )

    def test_final_order_is_invariant_to_hypothesis_completion_order(self):
        templates = make_line_template_bank(count=3, expected_sha256=None)
        vectors = np.ones((3, self.grid.score_bin_count), dtype=np.float32)

        def run(order):
            ledger = self.make_ledger(
                "synthetic",
                self.grid,
                1.0,
                100,
                template_bank=templates[:2],
            )
            for template_index in order:
                ledger.add_hypothesis(
                    vectors,
                    (0, 1),
                    template=templates[template_index],
                    width_index=0,
                    width_channels=1,
                    exclusion_mask=None,
                )
            records = ledger.finalize()
            return canonical_json_bytes(records), ledger.certificate()["records_sha256"]

        self.assertEqual(run((0, 1)), run((1, 0)))

    def test_missing_or_duplicate_hypothesis_invalidates_without_partial_result(self):
        vectors = np.ones((3, self.grid.score_bin_count), dtype=np.float32)
        missing = self.make_ledger("synthetic", self.grid, 100.0, 10)
        with self.assertRaises(V0P6IncompleteError):
            missing.finalize()

        duplicate = self.make_ledger("synthetic", self.grid, 100.0, 10)
        for attempt in range(2):
            if attempt == 0:
                duplicate.add_hypothesis(
                    vectors,
                    (0, 1),
                    template=self.template,
                    width_index=0,
                    width_channels=1,
                    exclusion_mask=None,
                )
            else:
                with self.assertRaises(V0P6IncompleteError):
                    duplicate.add_hypothesis(
                        vectors,
                        (0, 1),
                        template=self.template,
                        width_index=0,
                        width_channels=1,
                        exclusion_mask=None,
                    )
        with self.assertRaises(V0P6CapacityError):
            duplicate.finalize()

    def test_wrong_equal_size_hypothesis_inventory_is_rejected(self):
        vectors = np.ones((3, self.grid.score_bin_count), dtype=np.float32)
        wrong_template = dict(self.template)
        wrong_template["template_index"] = 999
        template_ledger = self.make_ledger("synthetic", self.grid, 100.0, 10)
        with self.assertRaisesRegex(V0P6IncompleteError, "unexpected"):
            template_ledger.add_hypothesis(
                vectors,
                (0, 1),
                template=wrong_template,
                width_index=0,
                width_channels=1,
                exclusion_mask=None,
            )

        width_ledger = self.make_ledger("synthetic", self.grid, 100.0, 10)
        with self.assertRaisesRegex(V0P6IncompleteError, "width"):
            width_ledger.add_hypothesis(
                vectors,
                (0, 1),
                template=self.template,
                width_index=0,
                width_channels=3,
                exclusion_mask=None,
            )

        subset_ledger = self.make_ledger("synthetic", self.grid, 100.0, 10)
        with self.assertRaisesRegex(V0P6IncompleteError, "malformed"):
            subset_ledger.add_hypothesis(
                vectors,
                (1, 0),
                template=self.template,
                width_index=0,
                width_channels=1,
                exclusion_mask=None,
            )

        fractional_ledger = self.make_ledger(
            "synthetic", self.grid, 100.0, 10
        )
        fractional_template = dict(self.template)
        fractional_template["template_index"] = 0.9
        with self.assertRaisesRegex(V0P6IncompleteError, "malformed"):
            fractional_ledger.add_hypothesis(
                vectors,
                (0, 1),
                template=fractional_template,
                width_index=0,
                width_channels=1,
                exclusion_mask=None,
            )

    def test_retention_contract_is_immutable_and_certificate_is_snapshotted(self):
        templates = make_line_template_bank(count=3, expected_sha256=None)[:2]
        vectors = np.ones((3, self.grid.score_bin_count), dtype=np.float32)
        mutable = self.make_ledger(
            "mutable",
            self.grid,
            100.0,
            20,
            template_bank=templates,
        )
        mutable.add_hypothesis(
            vectors,
            (0, 1),
            template=templates[0],
            width_index=0,
            width_channels=1,
            exclusion_mask=None,
        )
        mutable.threshold = 0.0
        with self.assertRaisesRegex(V0P6IncompleteError, "contract changed"):
            mutable.add_hypothesis(
                vectors,
                (0, 1),
                template=templates[1],
                width_index=0,
                width_channels=1,
                exclusion_mask=None,
            )

        wrong_epochs = self.make_ledger(
            "wrong-epochs", self.grid, 100.0, 20
        )
        with self.assertRaisesRegex(V0P6IncompleteError, "shape changed"):
            wrong_epochs.add_hypothesis(
                np.ones((4, self.grid.score_bin_count), dtype=np.float32),
                (0, 1),
                template=self.template,
                width_index=0,
                width_channels=1,
                exclusion_mask=None,
            )

        mutated_grid = make_proxy_carrier_grid(1400.5, 1.0, 4, 2)
        changed_grid = self.make_ledger(
            "changed-grid", mutated_grid, 100.0, 20
        )
        mutated_grid.support_mhz.setflags(write=True)
        mutated_grid.support_mhz[:] = 42.0
        with self.assertRaisesRegex(V0P6IncompleteError, "contract changed"):
            changed_grid.add_hypothesis(
                vectors,
                (0, 1),
                template=self.template,
                width_index=0,
                width_channels=1,
                exclusion_mask=None,
            )

        sealed = self.make_ledger("sealed", self.grid, 0.0, 20)
        vectors[2, 0] = np.nan
        sealed.add_hypothesis(
            vectors,
            (0, 1),
            template=self.template,
            width_index=0,
            width_channels=1,
            exclusion_mask=None,
        )
        records = sealed.finalize()
        self.assertIsNone(records[0]["epoch_values_at_proxy_carrier"][2])
        self.assertFalse(records[0]["epoch_value_is_finite"][2])
        before = sealed.certificate()
        sealed.threshold = np.nan
        sealed.maximum_records = 0
        self.assertEqual(sealed.certificate(), before)

    def test_exact_ten_thousand_capacity_boundary(self):
        grid = make_proxy_carrier_grid(1400.5, 1.0, 5000, 0)
        vectors = np.ones((2, grid.score_bin_count), dtype=np.float32)
        vectors[:, 0] = -1.0
        passing = self.make_ledger(
            "capacity", grid, 0.0, 10_000, epoch_count=2
        )
        passing.add_hypothesis(
            vectors,
            (0, 1),
            template=self.template,
            width_index=0,
            width_channels=1,
            exclusion_mask=None,
        )
        self.assertEqual(len(passing.finalize()), 10_000)

        vectors[:, 0] = 1.0
        failing = self.make_ledger(
            "capacity", grid, 0.0, 10_000, epoch_count=2
        )
        with self.assertRaisesRegex(V0P6CapacityError, "exceeds"):
            failing.add_hypothesis(
                vectors,
                (0, 1),
                template=self.template,
                width_index=0,
                width_channels=1,
                exclusion_mask=None,
            )
        with self.assertRaises(V0P6CapacityError):
            failing.finalize()

    def test_canonical_record_and_evidence_byte_caps_fail_closed(self):
        vectors = np.ones((2, self.grid.score_bin_count), dtype=np.float32)
        record_cap = self.make_ledger(
            "bytes",
            self.grid,
            0.0,
            100,
            epoch_count=2,
            maximum_record_canonical_bytes=100,
        )
        with self.assertRaisesRegex(V0P6CapacityError, "record exceeds"):
            record_cap.add_hypothesis(
                vectors,
                (0, 1),
                template=self.template,
                width_index=0,
                width_channels=1,
                exclusion_mask=None,
            )
        evidence_cap = self.make_ledger(
            "bytes",
            self.grid,
            0.0,
            100,
            epoch_count=2,
            maximum_evidence_canonical_bytes=100,
        )
        with self.assertRaisesRegex(V0P6CapacityError, "evidence byte cap"):
            evidence_cap.add_hypothesis(
                vectors,
                (0, 1),
                template=self.template,
                width_index=0,
                width_channels=1,
                exclusion_mask=None,
            )


if __name__ == "__main__":
    unittest.main()
