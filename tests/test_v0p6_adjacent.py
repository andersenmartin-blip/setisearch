"""Known-answer tests for sparse gathers and adjacent-OFF evidence."""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from seti_repeater import native_cache_v0p6 as disk_cache
import seti_repeater.search_v0p6 as core
from seti_repeater.adjacent_v0p6 import (
    disposition_after_single_adjacent_off,
    evaluate_m37_single_adjacent_off_veto,
    evaluate_m37_single_adjacent_off_veto_streaming,
    evaluate_single_adjacent_off_veto,
    evaluate_single_adjacent_off_veto_streaming,
    gather_filtered_native_at_score_indices,
    validate_single_adjacent_off_result,
)
from seti_repeater.search_v0p6 import (
    CalibrationAccumulator,
    ExhaustiveRetentionLedger,
    M37_FACTOR_ROW_SELECTION_SHA256S,
    NativeFrequencyGeometry,
    V0P6CapacityError,
    V0P6ContractError,
    V0P6IncompleteError,
    build_native_filter_cache,
    calibrated_threshold,
    canonical_json_bytes,
    factor_row_selection_sha256,
    factor_scan_selection_sha256,
    factor_table_for_scan,
    gather_filtered_native,
    make_factor_basis_from_arrays,
    make_line_template_bank,
    make_proxy_carrier_grid,
    make_scramble_shift_table,
    make_template_factor_table,
    plan_native_filter_cache,
    scan_inventory_sha256,
    scramble_table_sha256,
    template_bank_sha256,
    update_calibration,
)


ROOT = Path(__file__).resolve().parents[1]


def _sparse_fixture():
    rng = np.random.default_rng(37_060_712)
    frequency_mhz = np.arange(600, dtype=np.float64) / 1e6
    geometry = NativeFrequencyGeometry(0.0, 1.0, 600)
    grid = make_proxy_carrier_grid(0.0003, 1.0, 12, 5)
    factor_table = np.array(
        [[1.01, 1.02], [1.04, 1.03]], dtype=np.float64
    )
    plan = plan_native_filter_cache(
        geometry,
        factor_table,
        grid,
        5,
        window_id="synthetic",
        scan_label="epoch1_off",
        scan_kind="off",
        source_sha256="1" * 64,
        factor_basis_sha256_value="2" * 64,
        factor_basis_labels_sha256_value="3" * 64,
        scan_inventory_sha256_value="4" * 64,
        factor_scan_selection_sha256_value="5" * 64,
        template_bank_sha256_value="6" * 64,
    )
    data = rng.normal(size=(2, 600)).astype(np.float32)
    cache = build_native_filter_cache(data, frequency_mhz, plan)
    return grid, factor_table[0], cache


class SparseGatherTests(unittest.TestCase):
    def test_sparse_is_bit_identical_and_preserves_order_and_duplicates(self):
        grid, factors, cache = _sparse_fixture()
        selected = np.array([24, 0, 7, 7, 12, 1, 23, 0], dtype=np.int64)
        full = gather_filtered_native(cache, factors, grid, chunk_bins=3)
        sparse = gather_filtered_native_at_score_indices(
            cache, factors, grid, selected, chunk_bins=2
        )
        np.testing.assert_array_equal(sparse, full[selected])
        np.testing.assert_array_equal(
            sparse.view(np.uint32), full[selected].view(np.uint32)
        )
        self.assertEqual(sparse.dtype, np.dtype("<f4"))
        self.assertEqual(sparse.shape, selected.shape)
        self.assertEqual(
            gather_filtered_native_at_score_indices(
                cache, factors, grid, np.array([], dtype=np.int64)
            ).shape,
            (0,),
        )

    def test_sparse_supports_validated_disk_cache(self):
        grid, factors, cache = _sparse_fixture()
        selected = np.array([3, 20, 3, 11], dtype=np.int64)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "off.cache"
            receipt = disk_cache.publish_native_filter_cache(path, cache)
            with disk_cache.open_native_filter_cache(
                path,
                expected_plan=cache.plan,
                expected_plan_sha256=receipt.plan_sha256,
                expected_manifest_sha256=receipt.manifest_sha256,
            ) as handle:
                observed = gather_filtered_native_at_score_indices(
                    handle, factors, grid, selected, chunk_bins=1
                )
                expected = gather_filtered_native(
                    handle, factors, grid, chunk_bins=4
                )[selected]
                np.testing.assert_array_equal(
                    observed.view(np.uint32), expected.view(np.uint32)
                )

    def test_sparse_rejects_inexact_indices_and_contract_changes(self):
        grid, factors, cache = _sparse_fixture()
        for invalid in (
            np.array([1.0]),
            np.array([True]),
            [True, 2],
            np.array([-1]),
            np.array([grid.score_bin_count]),
            np.array([[1]], dtype=np.int64),
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(V0P6ContractError):
                    gather_filtered_native_at_score_indices(
                        cache, factors, grid, invalid
                    )
        with self.assertRaisesRegex(V0P6ContractError, "factor row"):
            gather_filtered_native_at_score_indices(
                cache, factors + 0.001, grid, [0]
            )
        changed_grid = make_proxy_carrier_grid(0.000301, 1.0, 12, 5)
        with self.assertRaisesRegex(V0P6ContractError, "proxy-grid"):
            gather_filtered_native_at_score_indices(
                cache, factors, changed_grid, [0]
            )
        forged = replace(cache, payload_sha256="0" * 64)
        with self.assertRaises(V0P6IncompleteError):
            gather_filtered_native_at_score_indices(
                forged, factors, grid, [0]
            )

        noninjective_geometry = NativeFrequencyGeometry(0.0, 2.0, 600)
        noninjective_factors = np.array([[1.01]], dtype=np.float64)
        noninjective_plan = plan_native_filter_cache(
            noninjective_geometry,
            noninjective_factors,
            grid,
            1,
            window_id="synthetic",
            scan_label="epoch1_off",
            scan_kind="off",
            source_sha256="1" * 64,
            factor_basis_sha256_value="2" * 64,
            factor_basis_labels_sha256_value="3" * 64,
            scan_inventory_sha256_value="4" * 64,
            factor_scan_selection_sha256_value="5" * 64,
            template_bank_sha256_value="6" * 64,
        )
        noninjective_cache = build_native_filter_cache(
            np.zeros((1, 600), dtype=np.float32),
            np.arange(600, dtype=np.float64) * 2.0 / 1e6,
            noninjective_plan,
        )
        with self.assertRaisesRegex(V0P6ContractError, "step"):
            gather_filtered_native_at_score_indices(
                noninjective_cache,
                noninjective_factors[0],
                grid,
                [grid.score_half_bins],
            )


class AdjacentOffVetoTests(unittest.TestCase):
    def setUp(self):
        config = json.loads(
            (ROOT / "config" / "hd156668b_m37_preflight.json").read_text()
        )
        self.scan_definitions = config["scans"]
        labels = [
            {
                "scan_index": scan_index,
                "scan_label": scan["label"],
                "integration_index": integration_index,
            }
            for scan_index, scan in enumerate(self.scan_definitions)
            for integration_index in range(16)
        ]
        self.factor_basis = make_factor_basis_from_arrays(
            np.arange(96, dtype=np.float64) + 57_470.0,
            labels,
            np.full(96, 1.01, dtype=np.float64),
            np.zeros((96, 2), dtype=np.float64),
            expected_sha256=None,
        )
        self.template_bank = [make_line_template_bank()[0]]
        self.factor_table = make_template_factor_table(
            self.factor_basis,
            self.template_bank,
            expected_template_bank_sha256=template_bank_sha256(
                self.template_bank
            ),
        )
        self.grid = make_proxy_carrier_grid(0.0005, 1.0, 10, 4)
        self.geometry = NativeFrequencyGeometry(0.0, 1.0, 1000)
        self.frequency_mhz = np.arange(1000, dtype=np.float64) / 1e6
        self.records, self.certificate = self._retained_on_product()

    def _retained_on_product(self):
        shifts = make_scramble_shift_table(
            1,
            3,
            self.grid.score_bin_count,
            seed=37_060_713,
            minimum_shift_bins=1,
        )
        bank_sha = template_bank_sha256(self.template_bank)
        scan_sha = scan_inventory_sha256(self.scan_definitions)
        on_rows_sha = factor_row_selection_sha256(
            self.factor_basis, self.scan_definitions, "on"
        )
        calibration = CalibrationAccumulator.create(
            window_id="synthetic",
            score_bin_count=self.grid.score_bin_count,
            template_count=1,
            template_bank_sha256_value=bank_sha,
            factor_basis_sha256_value=self.factor_basis.basis_sha256,
            factor_basis_labels_sha256_value=self.factor_basis.labels_sha256,
            scan_inventory_sha256_value=scan_sha,
            factor_row_selection_sha256_value=on_rows_sha,
            factor_table_sha256_value=self.factor_table.factor_table_sha256,
            spectral_widths=(1,),
            activity_subsets=((0, 2),),
            minimum_active_epoch_snr=3.0,
            stack_statistic="sum",
            scramble_shifts=shifts,
            minimum_shift_bins=1,
            expected_scramble_sha256=scramble_table_sha256(shifts),
        )
        zeros = np.full(
            (3, self.grid.score_bin_count), 3.0, dtype=np.float32
        )
        update_calibration(
            calibration,
            zeros,
            template_index=0,
            width_index=0,
            exclusion_mask=None,
        )
        calibration.finalize()
        threshold = calibrated_threshold(
            (calibration,),
            expected_window_ids=("synthetic",),
            reference_floor=7.0,
        )
        ledger = ExhaustiveRetentionLedger(
            window_id="synthetic",
            scan_kind="on",
            grid=self.grid,
            threshold_certificate=threshold,
            maximum_records=10,
            template_bank=self.template_bank,
            spectral_widths=(1,),
            activity_subsets=((0, 2),),
            expected_template_bank_sha256=bank_sha,
            factor_basis_sha256=self.factor_basis.basis_sha256,
            factor_basis_labels_sha256=self.factor_basis.labels_sha256,
            scan_inventory_sha256=scan_sha,
            factor_row_selection_sha256=on_rows_sha,
            factor_table_sha256=self.factor_table.factor_table_sha256,
            epoch_count=3,
            minimum_active_epoch_snr=3.0,
            stack_statistic="sum",
        )
        vectors = np.zeros((3, self.grid.score_bin_count), dtype=np.float32)
        vectors[0, 10] = 6.0
        vectors[2, 10] = 6.0
        ledger.add_hypothesis(
            vectors,
            (0, 2),
            template=self.template_bank[0],
            width_index=0,
            width_channels=1,
            exclusion_mask=None,
        )
        return ledger.finalize(), ledger.certificate()

    def _off_caches(self, epoch_data):
        caches = {1: {}}
        for scan_index in (1, 3, 5):
            definition = self.scan_definitions[scan_index]
            label = str(definition["label"])
            scan_table = factor_table_for_scan(
                self.factor_table, self.factor_basis, label
            )
            plan = plan_native_filter_cache(
                self.geometry,
                scan_table,
                self.grid,
                1,
                window_id="synthetic",
                scan_label=label,
                scan_kind="off",
                source_sha256=f"{scan_index + 1:064x}",
                factor_basis_sha256_value=self.factor_basis.basis_sha256,
                factor_basis_labels_sha256_value=self.factor_basis.labels_sha256,
                scan_inventory_sha256_value=scan_inventory_sha256(
                    self.scan_definitions
                ),
                factor_scan_selection_sha256_value=(
                    factor_scan_selection_sha256(
                        self.factor_basis, self.scan_definitions, label
                    )
                ),
                template_bank_sha256_value=(
                    self.factor_table.template_bank_sha256
                ),
            )
            data = epoch_data((scan_index - 1) // 2, scan_table[0])
            caches[1][label] = build_native_filter_cache(
                data, self.frequency_mhz, plan
            )
        return caches

    def _evaluate(self, caches, **overrides):
        arguments = {
            "single_epoch_snr_floor": 5.5,
            "maximum_records": 10,
            "maximum_queries": 2,
            "maximum_evidence_canonical_bytes": 100_000,
            "chunk_bins": 1,
        }
        arguments.update(overrides)
        return evaluate_single_adjacent_off_veto(
            self.records,
            self.certificate,
            caches,
            self.scan_definitions,
            self.factor_basis,
            self.factor_table,
            self.template_bank,
            self.grid,
            **arguments,
        )

    def test_inclusive_exact_track_veto_and_complete_provenance(self):
        def data(epoch, _factors):
            amplitude = (1.375, 9.0, 1.0)[epoch]
            return np.full((16, 1000), amplitude, dtype=np.float32)

        result = self._evaluate(self._off_caches(data))
        item = result["evidence"][0]
        certificate = result["certificate"]
        self.assertTrue(item["vetoed"])
        self.assertEqual(item["matching_active_epochs_zero_based"], [0])
        self.assertEqual(item["maximum_active_epoch_snr"], 5.5)
        self.assertEqual(
            [value["snr"] for value in item["paired_adjacent_off_measurements"]],
            [5.5, 4.0],
        )
        self.assertFalse(item["exclusion_mask_applied"])
        self.assertEqual(item["frequency_neighborhood_hz"], 0.0)
        self.assertEqual(certificate["cache_count"], 3)
        self.assertEqual(certificate["query_count"], 2)
        self.assertEqual(certificate["evidence_record_count"], 1)
        self.assertTrue(certificate["all_active_epoch_queries_evaluated_exactly_once"])
        self.assertEqual(
            item["recommended_member_disposition"],
            "rfi_veto_single_adjacent_off",
        )
        receipt = certificate["single_adjacent_off_certificate_sha256"]
        validated = validate_single_adjacent_off_result(
            result["evidence"],
            certificate,
            expected_certificate_sha256=receipt,
        )
        self.assertEqual(
            validated["single_adjacent_off_certificate_sha256"], receipt
        )

        mutated = json.loads(canonical_json_bytes(result["evidence"]))
        mutated[0]["vetoed"] = False
        with self.assertRaisesRegex(V0P6IncompleteError, "evidence"):
            validate_single_adjacent_off_result(mutated, certificate)
        forged_certificate = dict(certificate)
        forged_evidence_bytes = canonical_json_bytes(mutated)
        forged_certificate["evidence_sha256"] = hashlib.sha256(
            forged_evidence_bytes
        ).hexdigest()
        forged_certificate["evidence_canonical_bytes"] = len(
            forged_evidence_bytes
        )
        forged_certificate.pop("single_adjacent_off_certificate_sha256")
        forged_certificate["single_adjacent_off_certificate_sha256"] = (
            hashlib.sha256(
                canonical_json_bytes(forged_certificate)
            ).hexdigest()
        )
        with self.assertRaisesRegex(V0P6IncompleteError, "does not reproduce"):
            validate_single_adjacent_off_result(
                mutated,
                forged_certificate,
                expected_certificate_sha256=forged_certificate[
                    "single_adjacent_off_certificate_sha256"
                ],
            )

    def test_width_stream_is_bit_identical_and_closes_the_batch(self):
        def data(epoch, _factors):
            amplitude = (1.375, 9.0, 1.0)[epoch]
            return np.full((16, 1000), amplitude, dtype=np.float32)

        caches = self._off_caches(data)
        baseline = self._evaluate(caches)
        with tempfile.TemporaryDirectory() as directory:
            published = {}
            for label, cache in caches[1].items():
                path = Path(directory) / f"1-{label}.cache"
                receipt = disk_cache.publish_native_filter_cache(path, cache)
                published[label] = (path, cache.plan, receipt)

            completed_widths = []

            @contextmanager
            def open_width(width):
                self.assertEqual(width, 1)
                arena = disk_cache.NativeFilterCacheArena(1_000_000)
                retained_handles = []
                with ExitStack() as stack:
                    opened = {}
                    for label, (path, cache_plan, receipt) in published.items():
                        handle = stack.enter_context(
                            disk_cache.open_native_filter_cache(
                                path,
                                expected_plan=cache_plan,
                                expected_plan_sha256=receipt.plan_sha256,
                                expected_manifest_sha256=(
                                    receipt.manifest_sha256
                                ),
                                arena=arena,
                            )
                        )
                        retained_handles.append(handle)
                        opened[label] = handle
                    self.assertEqual(arena.handle_count, 3)
                    yield opened
                self.assertEqual(arena.handle_count, 0)
                self.assertEqual(arena.mapped_bytes, 0)
                self.assertTrue(
                    all(handle.closed for handle in retained_handles)
                )
                arena.close()
                completed_widths.append(width)

            streamed = evaluate_single_adjacent_off_veto_streaming(
                self.records,
                self.certificate,
                open_width,
                self.scan_definitions,
                self.factor_basis,
                self.factor_table,
                self.template_bank,
                self.grid,
                single_epoch_snr_floor=5.5,
                maximum_records=10,
                maximum_queries=2,
                maximum_evidence_canonical_bytes=100_000,
                expected_on_certificate_sha256=self.certificate[
                    "retention_certificate_sha256"
                ],
                chunk_bins=1,
            )
        self.assertEqual(completed_widths, [1])
        self.assertEqual(streamed, baseline)

    def test_trusted_numeric_fields_reject_strings(self):
        def data(epoch, _factors):
            amplitude = (1.375, 9.0, 1.0)[epoch]
            return np.full((16, 1000), amplitude, dtype=np.float32)

        baseline = self._evaluate(self._off_caches(data))

        certificate_string = json.loads(
            canonical_json_bytes(baseline["certificate"])
        )
        certificate_string["single_epoch_snr_floor"] = "5.5"
        certificate_string.pop("single_adjacent_off_certificate_sha256")
        certificate_string["single_adjacent_off_certificate_sha256"] = (
            hashlib.sha256(
                canonical_json_bytes(certificate_string)
            ).hexdigest()
        )
        with self.assertRaisesRegex(V0P6ContractError, "finite JSON number"):
            validate_single_adjacent_off_result(
                baseline["evidence"],
                certificate_string,
                expected_certificate_sha256=certificate_string[
                    "single_adjacent_off_certificate_sha256"
                ],
            )

        evidence_string = json.loads(
            canonical_json_bytes(baseline["evidence"])
        )
        measurement = evidence_string[0][
            "paired_adjacent_off_measurements"
        ][0]
        measurement["snr"] = str(measurement["snr"])
        evidence_bytes = canonical_json_bytes(evidence_string)
        rehashed = json.loads(canonical_json_bytes(baseline["certificate"]))
        rehashed["evidence_sha256"] = hashlib.sha256(evidence_bytes).hexdigest()
        rehashed["evidence_canonical_bytes"] = len(evidence_bytes)
        rehashed.pop("single_adjacent_off_certificate_sha256")
        rehashed["single_adjacent_off_certificate_sha256"] = hashlib.sha256(
            canonical_json_bytes(rehashed)
        ).hexdigest()
        with self.assertRaisesRegex(V0P6ContractError, "finite JSON number"):
            validate_single_adjacent_off_result(
                evidence_string,
                rehashed,
                expected_certificate_sha256=rehashed[
                    "single_adjacent_off_certificate_sha256"
                ],
            )

    def test_strong_neighbor_is_not_an_exact_q_veto(self):
        candidate_index = self.records[0]["proxy_carrier_index"]

        def data(epoch, factors):
            values = np.zeros((16, 1000), dtype=np.float32)
            if epoch == 0:
                neighbor_hz = self.grid.score_hz[candidate_index + 1]
                for integration, factor in enumerate(factors):
                    raw_index = int(np.rint(neighbor_hz * factor))
                    values[integration, raw_index] = 3.0
            return values

        result = self._evaluate(self._off_caches(data))
        item = result["evidence"][0]
        self.assertFalse(item["vetoed"])
        self.assertEqual(item["matching_active_epochs_zero_based"], [])
        self.assertEqual(item["maximum_active_epoch_snr"], 0.0)
        self.assertEqual(
            item["recommended_member_disposition"],
            "pending_receiver_alias_evaluation",
        )

    def test_exact_inventory_and_capacity_fail_closed(self):
        caches = self._off_caches(
            lambda _epoch, _factors: np.zeros(
                (16, 1000), dtype=np.float32
            )
        )
        with self.assertRaisesRegex(V0P6CapacityError, "query capacity"):
            self._evaluate(caches, maximum_queries=1)
        self.assertEqual(self._evaluate(caches, maximum_queries=2)["certificate"]["query_count"], 2)
        with self.assertRaisesRegex(V0P6CapacityError, "record capacity"):
            self._evaluate(caches, maximum_records=0)
        missing = {1: dict(caches[1])}
        missing[1].pop("epoch3_off")
        with self.assertRaisesRegex(V0P6IncompleteError, "inventory"):
            self._evaluate(missing)
        extra = {1: dict(caches[1]), 3: dict(caches[1])}
        with self.assertRaisesRegex(V0P6IncompleteError, "inventory"):
            self._evaluate(extra)

    def test_trusted_retention_digest_supports_cross_process_replay(self):
        caches = self._off_caches(
            lambda _epoch, _factors: np.zeros(
                (16, 1000), dtype=np.float32
            )
        )
        digest = self.certificate["retention_certificate_sha256"]
        attestation = core._RETENTION_CERTIFICATE_ATTESTATIONS.pop(digest)
        try:
            with self.assertRaisesRegex(V0P6ContractError, "attestation"):
                self._evaluate(caches)
            result = self._evaluate(
                caches, expected_on_certificate_sha256=digest
            )
            self.assertEqual(result["certificate"]["input_record_count"], 1)
        finally:
            core._RETENTION_CERTIFICATE_ATTESTATIONS[digest] = attestation

    def test_precedence_helper_preserves_stronger_off_dispositions(self):
        for prior in (
            "rfi_veto_matched_off_same_hypothesis",
            "rfi_veto_local_off_track",
        ):
            self.assertEqual(
                disposition_after_single_adjacent_off(prior, True), prior
            )
        self.assertEqual(
            disposition_after_single_adjacent_off(
                "pending_receiver_alias_evaluation", True
            ),
            "rfi_veto_single_adjacent_off",
        )
        self.assertEqual(
            disposition_after_single_adjacent_off(
                "pending_receiver_alias_evaluation", False
            ),
            "pending_receiver_alias_evaluation",
        )

    def test_m37_wrapper_requires_the_frozen_minimum_epoch_statistic(self):
        grid = core.make_m37_proxy_carrier_grid(core.M37_WINDOW_IDS[0])
        certificate = {
            "window_id": core.M37_WINDOW_IDS[0],
            "spectral_widths": list(core.M37_SPECTRAL_WIDTHS),
            "activity_subsets": [list(item) for item in core.M37_ACTIVITY_SUBSETS],
            "epoch_count": 3,
            "expected_hypotheses": 2_976,
            "hypotheses_replayed": 2_976,
            "expected_score_cells": 2_976 * grid.score_bin_count,
            "score_cells_replayed": 2_976 * grid.score_bin_count,
            "maximum_records": core.M37_MAXIMUM_RECORDS_PER_WINDOW,
            "maximum_record_canonical_bytes": (
                core.M37_MAXIMUM_RECORD_CANONICAL_BYTES
            ),
            "maximum_evidence_canonical_bytes": (
                core.M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES
            ),
            "require_epoch_vector_product": True,
            "require_mask_product": True,
            "minimum_active_epoch_snr": core.M37_MINIMUM_ACTIVE_EPOCH_SNR,
            "stack_statistic": "minimum_epoch",
            "experiment_contract_sha256": core.M37_EXPERIMENT_CONTRACT_SHA256,
            "factor_basis_sha256": core.M37_FACTOR_BASIS_SHA256,
            "factor_basis_labels_sha256": core.M37_FACTOR_BASIS_LABELS_SHA256,
            "scan_inventory_sha256": core.M37_SCAN_INVENTORY_SHA256,
            "factor_row_selection_sha256": (
                core.M37_FACTOR_ROW_SELECTION_SHA256S["on"]
            ),
            "template_bank_sha256": core.M37_BANK_SHA256,
        }
        sentinel = {"accepted": True}
        with (
            patch(
                "seti_repeater.adjacent_v0p6.core.validate_retention_certificate",
                return_value=certificate,
            ),
            patch(
                "seti_repeater.adjacent_v0p6.core.validate_m37_factor_basis_scan_inventory"
            ),
            patch(
                "seti_repeater.adjacent_v0p6.core.validate_template_factor_table"
            ),
            patch(
                "seti_repeater.adjacent_v0p6.evaluate_single_adjacent_off_veto",
                return_value=sentinel,
            ),
            patch(
                "seti_repeater.adjacent_v0p6."
                "evaluate_single_adjacent_off_veto_streaming",
                return_value=sentinel,
            ),
        ):
            self.assertIs(
                evaluate_m37_single_adjacent_off_veto(
                    [], {}, {}, [], object(), object(), grid
                ),
                sentinel,
            )
            self.assertIs(
                evaluate_m37_single_adjacent_off_veto_streaming(
                    [], {}, lambda _width: None, [], object(), object(), grid
                ),
                sentinel,
            )
            certificate["stack_statistic"] = "sum"
            with self.assertRaisesRegex(V0P6IncompleteError, "non-canonical"):
                evaluate_m37_single_adjacent_off_veto(
                    [], {}, {}, [], object(), object(), grid
                )
            with self.assertRaisesRegex(V0P6IncompleteError, "non-canonical"):
                evaluate_m37_single_adjacent_off_veto_streaming(
                    [], {}, lambda _width: None, [], object(), object(), grid
                )


if __name__ == "__main__":
    unittest.main()
