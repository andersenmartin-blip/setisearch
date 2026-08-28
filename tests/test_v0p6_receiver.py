"""Known-answer tests for production receiver-frame signatures."""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from seti_repeater import native_cache_v0p6 as disk_cache
from seti_repeater.alias_v0p6 import _validate_signatures
import seti_repeater.search_v0p6 as core
from seti_repeater.receiver_v0p6 import (
    M37_MAXIMUM_RECEIVER_SIGNATURE_LOCAL_CHANNEL_VISITS,
    M37_MAXIMUM_RECEIVER_SIGNATURE_QUERIES,
    M37_RECEIVER_SIGNATURE_LOCAL_HALF_WIDTH_HZ,
    M37_RECEIVER_SIGNATURE_PEAK_SNR_FLOOR,
    build_m37_receiver_frame_signatures,
    build_m37_receiver_frame_signatures_streaming,
    build_receiver_frame_signatures,
    build_receiver_frame_signatures_streaming,
    validate_receiver_signature_result,
)


ROOT = Path(__file__).resolve().parents[1]


class ReceiverSignatureTests(unittest.TestCase):
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
        orbital = np.zeros((96, 2), dtype=np.float64)
        for scan_index in (0, 2, 4):
            orbital[scan_index * 16 : (scan_index + 1) * 16, 0] = (
                -0.2 + 0.05 * scan_index
            )
        self.factor_basis = core.make_factor_basis_from_arrays(
            np.arange(96, dtype=np.float64) + 57_470.0,
            labels,
            np.ones(96, dtype=np.float64),
            orbital,
            expected_sha256=None,
        )
        self.template_bank = core.make_line_template_bank()[:2]
        self.factor_table = core.make_template_factor_table(
            self.factor_basis,
            self.template_bank,
            expected_template_bank_sha256=core.template_bank_sha256(
                self.template_bank
            ),
        )
        self.grid = core.make_proxy_carrier_grid(0.0005, 1.0, 10, 200)
        self.geometry = core.NativeFrequencyGeometry(0.0, 1.0, 1000)
        self.widths = (1, 3)
        self.caches = self._make_caches()
        self.records, self.certificate = self._make_retention_product()

    def _make_caches(self):
        caches = {width: {} for width in self.widths}
        on_indices = core.m37_scan_indices_for_kind(
            self.scan_definitions, "on"
        )
        for width in self.widths:
            for epoch, scan_index in enumerate(on_indices):
                definition = self.scan_definitions[scan_index]
                label = str(definition["label"])
                scan_table = core.factor_table_for_scan(
                    self.factor_table, self.factor_basis, label
                )
                plan = core.plan_native_filter_cache(
                    self.geometry,
                    scan_table,
                    self.grid,
                    width,
                    window_id="synthetic",
                    scan_label=label,
                    scan_kind="on",
                    source_sha256=f"{scan_index + 1:064x}",
                    factor_basis_sha256_value=self.factor_basis.basis_sha256,
                    factor_basis_labels_sha256_value=(
                        self.factor_basis.labels_sha256
                    ),
                    scan_inventory_sha256_value=core.scan_inventory_sha256(
                        self.scan_definitions
                    ),
                    factor_scan_selection_sha256_value=(
                        core.factor_scan_selection_sha256(
                            self.factor_basis, self.scan_definitions, label
                        )
                    ),
                    template_bank_sha256_value=(
                        self.factor_table.template_bank_sha256
                    ),
                )
                values = np.zeros(plan.payload_shape, dtype=np.dtype("<f4"))

                def set_channel(raw_index, amplitude):
                    if plan.raw_center_start <= raw_index < plan.raw_center_stop:
                        values[:, raw_index - plan.raw_center_start] = np.float32(
                            amplitude
                        )

                if width == 1 and epoch == 0:
                    # Both inclusive +/-100 Hz boundaries tie.  A much larger
                    # value one channel outside must not enter the query.
                    set_channel(399, 10.0)
                    set_channel(400, 2.0)
                    set_channel(600, 2.0)
                elif width == 1 and epoch == 2:
                    set_channel(499, 1.375)
                    set_channel(501, 1.375)
                elif width == 3 and epoch == 1:
                    set_channel(522, 3.0)
                elif width == 3 and epoch == 2:
                    set_channel(532, 4.0)
                digest = core.float32_array_sha256(values)
                values.setflags(write=False)
                caches[width][label] = core.NativeFilterCache(
                    plan=plan,
                    values=values,
                    payload_sha256=digest,
                )
        return caches

    def _make_retention_product(self):
        shifts = core.make_scramble_shift_table(
            1,
            3,
            self.grid.score_bin_count,
            seed=37_060_801,
            minimum_shift_bins=1,
        )
        bank_sha = core.template_bank_sha256(self.template_bank)
        scan_sha = core.scan_inventory_sha256(self.scan_definitions)
        on_rows_sha = core.factor_row_selection_sha256(
            self.factor_basis, self.scan_definitions, "on"
        )
        subsets = ((0, 2), (1, 2))
        calibration = core.CalibrationAccumulator.create(
            window_id="synthetic",
            score_bin_count=self.grid.score_bin_count,
            template_count=2,
            template_bank_sha256_value=bank_sha,
            factor_basis_sha256_value=self.factor_basis.basis_sha256,
            factor_basis_labels_sha256_value=self.factor_basis.labels_sha256,
            scan_inventory_sha256_value=scan_sha,
            factor_row_selection_sha256_value=on_rows_sha,
            factor_table_sha256_value=self.factor_table.factor_table_sha256,
            spectral_widths=self.widths,
            activity_subsets=subsets,
            minimum_active_epoch_snr=3.0,
            stack_statistic="sum",
            scramble_shifts=shifts,
            minimum_shift_bins=1,
            expected_scramble_sha256=core.scramble_table_sha256(shifts),
        )
        calibration_vectors = np.full(
            (3, self.grid.score_bin_count), 3.0, dtype=np.float32
        )
        for template_index in range(2):
            for width_index in range(2):
                core.update_calibration(
                    calibration,
                    calibration_vectors,
                    template_index=template_index,
                    width_index=width_index,
                    exclusion_mask=None,
                )
        calibration.finalize()
        threshold = core.calibrated_threshold(
            (calibration,),
            expected_window_ids=("synthetic",),
            reference_floor=7.0,
        )
        ledger = core.ExhaustiveRetentionLedger(
            window_id="synthetic",
            scan_kind="on",
            grid=self.grid,
            threshold_certificate=threshold,
            maximum_records=10,
            template_bank=self.template_bank,
            spectral_widths=self.widths,
            activity_subsets=subsets,
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
        for template_index in range(2):
            for width_index, width in enumerate(self.widths):
                for subset in subsets:
                    vectors = np.zeros(
                        (3, self.grid.score_bin_count), dtype=np.float32
                    )
                    if (
                        template_index,
                        width_index,
                        subset,
                    ) == (0, 0, (0, 2)):
                        vectors[0, 10] = 6.0
                        vectors[2, 10] = 6.0
                    elif (
                        template_index,
                        width_index,
                        subset,
                    ) == (1, 1, (1, 2)):
                        vectors[1, 11] = 6.0
                        vectors[2, 11] = 6.0
                    ledger.add_hypothesis(
                        vectors,
                        subset,
                        template=self.template_bank[template_index],
                        width_index=width_index,
                        width_channels=width,
                        exclusion_mask=None,
                    )
        records = ledger.finalize()
        certificate = ledger.certificate()

        # Rehydrate the synthetic product as a provenance-required persisted
        # handoff.  Production M37 retention creates these fields directly.
        for record in records:
            record["epoch_vector_product_sha256"] = hashlib.sha256(
                core.canonical_json_bytes(record["record_key"])
                + b"synthetic epoch product"
            ).hexdigest()
        provenance = {}
        on_indices = core.m37_scan_indices_for_kind(
            self.scan_definitions, "on"
        )
        for width_index, width in enumerate(self.widths):
            selected = [
                self.caches[width][
                    str(self.scan_definitions[index]["label"])
                ]
                for index in on_indices
            ]
            provenance[width_index] = (
                tuple(item.plan.plan_sha256 for item in selected),
                tuple(item.payload_sha256 for item in selected),
            )
        certificate["require_epoch_vector_product"] = True
        certificate["epoch_product_inventory_sha256"] = (
            core._epoch_product_inventory_sha256(
                {
                    (template_index, width_index): hashlib.sha256(
                        f"{template_index}:{width_index}".encode()
                    ).hexdigest()
                    for template_index in range(2)
                    for width_index in range(2)
                }
            )
        )
        certificate["cache_provenance_inventory_sha256"] = (
            core._cache_provenance_inventory_sha256(provenance)
        )
        records.sort(key=core._retention_record_sort_key)
        certificate["canonical_record_bytes"] = sum(
            len(core.canonical_json_bytes(item)) for item in records
        )
        certificate["records_sha256"] = hashlib.sha256(
            core.canonical_json_bytes(records)
        ).hexdigest()
        certificate.pop("retention_certificate_sha256")
        certificate["retention_certificate_sha256"] = hashlib.sha256(
            core.canonical_json_bytes(certificate)
        ).hexdigest()
        return records, certificate

    def _build(self, caches=None, **overrides):
        arguments = {
            "local_half_width_hz": 100.0,
            "local_peak_snr_floor": 5.5,
            "maximum_records": 2,
            "maximum_queries": 4,
            "maximum_local_channel_visits": 1_000,
            "maximum_signature_record_canonical_bytes": 6_144,
            "maximum_evidence_canonical_bytes": 100_000,
            "expected_on_certificate_sha256": self.certificate[
                "retention_certificate_sha256"
            ],
        }
        arguments.update(overrides)
        return build_receiver_frame_signatures(
            self.records,
            self.certificate,
            self.caches if caches is None else caches,
            self.scan_definitions,
            self.factor_basis,
            self.factor_table,
            self.template_bank,
            self.grid,
            **arguments,
        )

    def test_literal_boundary_tie_and_exact_alias_schema(self):
        result = self._build()
        signatures = result["receiver_signatures"]
        first = self.records[0]
        second = self.records[1]
        first_entries = signatures[first["record_id"]]
        second_entries = signatures[second["record_id"]]
        self.assertEqual([item["epoch_zero_based"] for item in first_entries], [0, 2])
        self.assertEqual([item["epoch_zero_based"] for item in second_entries], [1, 2])
        self.assertEqual(first_entries[0]["peak_frequency_mhz"], 400.0 / 1e6)
        self.assertEqual(first_entries[0]["predicted_mid_mhz"] * 1e6, 500.0)
        self.assertEqual(first_entries[0]["peak_frequency_mhz"] * 1e6, 400.0)
        self.assertEqual(
            first_entries[0]["offset_from_prediction_hz"],
            (
                first_entries[0]["peak_frequency_mhz"]
                - first_entries[0]["predicted_mid_mhz"]
            )
            * 1e6,
        )
        self.assertLessEqual(
            abs(first_entries[0]["offset_from_prediction_hz"]), 100.0
        )
        self.assertEqual(first_entries[0]["peak_snr"], 8.0)
        self.assertEqual(first_entries[1]["peak_frequency_mhz"], 499.0 / 1e6)
        self.assertEqual(first_entries[1]["peak_snr"], 5.5)
        expected_second_mid_hz = 0.0
        for item in core.factor_table_for_scan(
            self.factor_table, self.factor_basis, "epoch2_on"
        )[1]:
            expected_second_mid_hz += (
                float(second["proxy_carrier_hz"]) * float(item)
            )
        expected_second_mid = expected_second_mid_hz / 16.0 / 1e6
        self.assertEqual(second_entries[0]["predicted_mid_mhz"], expected_second_mid)
        self.assertNotEqual(
            first_entries[0]["predicted_mid_mhz"],
            second_entries[0]["predicted_mid_mhz"],
        )

        certificate = result["certificate"]
        _, alias_product_sha = _validate_signatures(
            self.records,
            signatures,
            local_half_width_hz=100.0,
        )
        self.assertEqual(
            alias_product_sha,
            certificate["receiver_signature_product_sha256"],
        )
        self.assertEqual(certificate["cache_count"], 6)
        self.assertEqual(certificate["query_count"], 4)
        self.assertEqual(certificate["local_peak_snr_floor"], 5.5)
        receipt = certificate["receiver_signature_certificate_sha256"]
        self.assertEqual(
            validate_receiver_signature_result(
                result, expected_certificate_sha256=receipt
            )["result_sha256"],
            result["result_sha256"],
        )

    def test_exact_capacity_boundaries_and_plus_one_fail_closed(self):
        baseline = self._build()
        certificate = baseline["certificate"]
        visits = certificate["local_channel_visits"]
        evidence_bytes = certificate[
            "receiver_signature_product_canonical_bytes"
        ]
        record_bytes = max(
            len(
                core.canonical_json_bytes(
                    {
                        "record_id": record_id,
                        "receiver_frame_signature": entries,
                    }
                )
            )
            for record_id, entries in baseline["receiver_signatures"].items()
        )
        self._build(
            maximum_local_channel_visits=visits,
            maximum_evidence_canonical_bytes=evidence_bytes,
            maximum_signature_record_canonical_bytes=record_bytes,
        )
        cases = (
            ({"maximum_records": 1}, "record capacity"),
            ({"maximum_queries": 3}, "query capacity"),
            (
                {"maximum_local_channel_visits": visits - 1},
                "local-channel-visit capacity",
            ),
            (
                {"maximum_evidence_canonical_bytes": evidence_bytes - 1},
                "evidence-byte capacity",
            ),
            (
                {"maximum_signature_record_canonical_bytes": record_bytes - 1},
                "record exceeds",
            ),
        )
        for overrides, message in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(core.V0P6CapacityError, message):
                    self._build(**overrides)

    def test_incomplete_duplicate_and_wrong_cache_inventories_are_rejected(self):
        incomplete = dict(self.caches)
        incomplete.pop(3)
        with self.assertRaisesRegex(core.V0P6IncompleteError, "width inventory"):
            self._build(incomplete)

        duplicate_widths = [
            (1, self.caches[1]),
            (1, self.caches[1]),
            (3, self.caches[3]),
        ]
        with self.assertRaisesRegex(core.V0P6IncompleteError, "repeats a width"):
            self._build(duplicate_widths)

        scans = list(self.caches[1].items())
        duplicate_labels = dict(self.caches)
        duplicate_labels[1] = [scans[0], scans[0], *scans[1:]]
        with self.assertRaisesRegex(core.V0P6IncompleteError, "scan label"):
            self._build(duplicate_labels)

        wrong = {width: dict(items) for width, items in self.caches.items()}
        wrong[3]["epoch1_on"] = self.caches[1]["epoch1_on"]
        with self.assertRaisesRegex(core.V0P6ContractError, "identity"):
            self._build(wrong)

    def test_cache_source_payload_and_retention_provenance_mutation_fail(self):
        source_changed = {width: dict(items) for width, items in self.caches.items()}
        original = source_changed[1]["epoch1_on"]
        source_changed[1]["epoch1_on"] = replace(
            original,
            plan=replace(original.plan, source_sha256="f" * 64),
        )
        with self.assertRaises(core.V0P6ContractError):
            self._build(source_changed)

        payload_changed = {width: dict(items) for width, items in self.caches.items()}
        original = payload_changed[1]["epoch1_on"]
        changed_values = original.values.copy()
        changed_values.flat[0] += np.float32(1.0)
        changed_values.setflags(write=False)
        payload_changed[1]["epoch1_on"] = replace(
            original, values=changed_values
        )
        with self.assertRaises(core.V0P6IncompleteError):
            self._build(payload_changed)

        forged_certificate = dict(self.certificate)
        forged_certificate["cache_provenance_inventory_sha256"] = "0" * 64
        forged_certificate.pop("retention_certificate_sha256")
        forged_certificate["retention_certificate_sha256"] = hashlib.sha256(
            core.canonical_json_bytes(forged_certificate)
        ).hexdigest()
        with self.assertRaisesRegex(core.V0P6IncompleteError, "provenance"):
            build_receiver_frame_signatures(
                self.records,
                forged_certificate,
                self.caches,
                self.scan_definitions,
                self.factor_basis,
                self.factor_table,
                self.template_bank,
                self.grid,
                local_half_width_hz=100.0,
                local_peak_snr_floor=5.5,
                maximum_records=2,
                maximum_queries=4,
                maximum_local_channel_visits=1_000,
                maximum_signature_record_canonical_bytes=6_144,
                maximum_evidence_canonical_bytes=100_000,
                expected_on_certificate_sha256=forged_certificate[
                    "retention_certificate_sha256"
                ],
            )

    def test_fake_or_mutated_signatures_lack_a_factory_receipt(self):
        result = self._build()
        mutated = json.loads(core.canonical_json_bytes(result))
        record_id = sorted(mutated["receiver_signatures"])[0]
        mutated["receiver_signatures"][record_id][0]["peak_snr"] += 1.0
        product = [
            {
                "record_id": item_id,
                "receiver_frame_signature": entries,
            }
            for item_id, entries in sorted(
                mutated["receiver_signatures"].items()
            )
        ]
        product_bytes = core.canonical_json_bytes(product)
        mapping_bytes = core.canonical_json_bytes(
            mutated["receiver_signatures"]
        )
        cert = mutated["certificate"]
        cert["receiver_signature_product_canonical_bytes"] = len(product_bytes)
        cert["receiver_signature_product_sha256"] = hashlib.sha256(
            product_bytes
        ).hexdigest()
        cert["receiver_signatures_mapping_canonical_bytes"] = len(mapping_bytes)
        cert["receiver_signatures_mapping_sha256"] = hashlib.sha256(
            mapping_bytes
        ).hexdigest()
        cert.pop("receiver_signature_certificate_sha256")
        cert["receiver_signature_certificate_sha256"] = hashlib.sha256(
            core.canonical_json_bytes(cert)
        ).hexdigest()
        mutated.pop("result_sha256")
        mutated["result_sha256"] = hashlib.sha256(
            core.canonical_json_bytes(
                {
                    "receiver_signatures": mutated["receiver_signatures"],
                    "certificate": cert,
                }
            )
        ).hexdigest()
        with self.assertRaisesRegex(core.V0P6ContractError, "trusted receipt"):
            validate_receiver_signature_result(mutated)

    def test_trusted_numeric_signature_fields_reject_strings_and_bools(self):
        baseline = self._build()
        record_id = sorted(baseline["receiver_signatures"])[0]

        def reseal(mutated):
            product = [
                {
                    "record_id": item_id,
                    "receiver_frame_signature": entries,
                }
                for item_id, entries in sorted(
                    mutated["receiver_signatures"].items()
                )
            ]
            product_bytes = core.canonical_json_bytes(product)
            mapping_bytes = core.canonical_json_bytes(
                mutated["receiver_signatures"]
            )
            cert = mutated["certificate"]
            cert["receiver_signature_product_canonical_bytes"] = len(
                product_bytes
            )
            cert["receiver_signature_product_sha256"] = hashlib.sha256(
                product_bytes
            ).hexdigest()
            cert["receiver_signatures_mapping_canonical_bytes"] = len(
                mapping_bytes
            )
            cert["receiver_signatures_mapping_sha256"] = hashlib.sha256(
                mapping_bytes
            ).hexdigest()
            cert.pop("receiver_signature_certificate_sha256")
            cert["receiver_signature_certificate_sha256"] = hashlib.sha256(
                core.canonical_json_bytes(cert)
            ).hexdigest()
            mutated.pop("result_sha256")
            mutated["result_sha256"] = hashlib.sha256(
                core.canonical_json_bytes(
                    {
                        "receiver_signatures": mutated[
                            "receiver_signatures"
                        ],
                        "certificate": cert,
                    }
                )
            ).hexdigest()
            return cert["receiver_signature_certificate_sha256"]

        cases = (
            ("predicted_mid_mhz", "string"),
            ("peak_frequency_mhz", "string"),
            ("peak_snr", "string"),
            ("offset_from_prediction_hz", "string"),
            ("peak_snr", "bool"),
        )
        for field, kind in cases:
            with self.subTest(field=field, kind=kind):
                mutated = json.loads(core.canonical_json_bytes(baseline))
                entry = mutated["receiver_signatures"][record_id][0]
                entry[field] = str(entry[field]) if kind == "string" else True
                receipt = reseal(mutated)
                with self.assertRaisesRegex(
                    core.V0P6ContractError, "finite JSON number"
                ):
                    validate_receiver_signature_result(
                        mutated, expected_certificate_sha256=receipt
                    )

    def test_disk_and_memory_products_are_bit_identical(self):
        memory = self._build()
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            disk_caches = {width: {} for width in self.widths}
            for width in self.widths:
                for label, cache in self.caches[width].items():
                    path = Path(directory) / f"{width}-{label}.cache"
                    receipt = disk_cache.publish_native_filter_cache(path, cache)
                    handle = disk_cache.open_native_filter_cache(
                        path,
                        expected_plan=cache.plan,
                        expected_plan_sha256=receipt.plan_sha256,
                        expected_manifest_sha256=receipt.manifest_sha256,
                    )
                    disk_caches[width][label] = stack.enter_context(handle)
            disk = self._build(disk_caches)
        self.assertEqual(
            memory["receiver_signatures"], disk["receiver_signatures"]
        )
        self.assertEqual(
            memory["certificate"]["receiver_signature_product_sha256"],
            disk["certificate"]["receiver_signature_product_sha256"],
        )
        self.assertEqual(memory["result_sha256"], disk["result_sha256"])

    def test_width_stream_is_bit_identical_and_closes_each_batch(self):
        baseline = self._build()
        with tempfile.TemporaryDirectory() as directory:
            published = {width: {} for width in self.widths}
            for width in self.widths:
                for label, cache in self.caches[width].items():
                    path = Path(directory) / f"{width}-{label}.cache"
                    receipt = disk_cache.publish_native_filter_cache(path, cache)
                    published[width][label] = (path, cache.plan, receipt)

            completed_widths = []

            @contextmanager
            def open_width(width):
                arena = disk_cache.NativeFilterCacheArena(1_000_000)
                retained_handles = []
                with ExitStack() as stack:
                    opened = {}
                    for label, (path, plan, receipt) in published[width].items():
                        handle = stack.enter_context(
                            disk_cache.open_native_filter_cache(
                                path,
                                expected_plan=plan,
                                expected_plan_sha256=receipt.plan_sha256,
                                expected_manifest_sha256=receipt.manifest_sha256,
                                arena=arena,
                            )
                        )
                        retained_handles.append(handle)
                        opened[label] = handle
                    self.assertEqual(arena.handle_count, 3)
                    yield opened
                self.assertEqual(arena.handle_count, 0)
                self.assertEqual(arena.mapped_bytes, 0)
                self.assertTrue(all(handle.closed for handle in retained_handles))
                arena.close()
                completed_widths.append(width)

            streamed = build_receiver_frame_signatures_streaming(
                self.records,
                self.certificate,
                open_width,
                self.scan_definitions,
                self.factor_basis,
                self.factor_table,
                self.template_bank,
                self.grid,
                local_half_width_hz=100.0,
                local_peak_snr_floor=5.5,
                maximum_records=2,
                maximum_queries=4,
                maximum_local_channel_visits=1_000,
                maximum_signature_record_canonical_bytes=6_144,
                maximum_evidence_canonical_bytes=100_000,
                expected_on_certificate_sha256=self.certificate[
                    "retention_certificate_sha256"
                ],
            )
        self.assertEqual(completed_widths, list(self.widths))
        self.assertEqual(streamed, baseline)

    def test_m37_wrapper_freezes_thresholds_caps_and_minimum_epoch(self):
        grid = core.make_m37_proxy_carrier_grid(core.M37_WINDOW_IDS[0])
        factor_table_sha = "f" * 64
        certificate = {
            "window_id": core.M37_WINDOW_IDS[0],
            "scan_kind": "on",
            "proxy_grid_sha256": core.proxy_carrier_grid_sha256(grid),
            "spectral_widths": list(core.M37_SPECTRAL_WIDTHS),
            "activity_subsets": [list(item) for item in core.M37_ACTIVITY_SUBSETS],
            "epoch_count": 3,
            "expected_hypotheses": 2_976,
            "expected_score_cells": 2_976 * grid.score_bin_count,
            "maximum_records": core.M37_MAXIMUM_RECORDS_PER_WINDOW,
            "maximum_record_canonical_bytes": core.M37_MAXIMUM_RECORD_CANONICAL_BYTES,
            "maximum_evidence_canonical_bytes": core.M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES,
            "require_epoch_vector_product": True,
            "require_mask_product": True,
            "minimum_active_epoch_snr": core.M37_MINIMUM_ACTIVE_EPOCH_SNR,
            "stack_statistic": "minimum_epoch",
            "experiment_contract_sha256": core.M37_EXPERIMENT_CONTRACT_SHA256,
            "factor_basis_sha256": core.M37_FACTOR_BASIS_SHA256,
            "factor_basis_labels_sha256": core.M37_FACTOR_BASIS_LABELS_SHA256,
            "scan_inventory_sha256": core.M37_SCAN_INVENTORY_SHA256,
            "factor_row_selection_sha256": core.M37_FACTOR_ROW_SELECTION_SHA256S["on"],
            "template_bank_sha256": core.M37_BANK_SHA256,
            "factor_table_sha256": factor_table_sha,
        }
        table = SimpleNamespace(
            factor_table_sha256=factor_table_sha,
            factors=np.empty((core.M37_TEMPLATE_COUNT, 96)),
        )
        sentinel = {"accepted": True}
        with (
            patch(
                "seti_repeater.receiver_v0p6.core.validate_retention_certificate",
                return_value=certificate,
            ),
            patch(
                "seti_repeater.receiver_v0p6.core.validate_m37_factor_basis_scan_inventory"
            ),
            patch(
                "seti_repeater.receiver_v0p6.core.validate_template_factor_table"
            ),
            patch(
                "seti_repeater.receiver_v0p6.build_receiver_frame_signatures",
                return_value=sentinel,
            ) as generic,
            patch(
                "seti_repeater.receiver_v0p6."
                "build_receiver_frame_signatures_streaming",
                return_value=sentinel,
            ) as streaming_generic,
        ):
            self.assertIs(
                build_m37_receiver_frame_signatures(
                    [], {}, {}, [], object(), table, grid
                ),
                sentinel,
            )
            kwargs = generic.call_args.kwargs
            self.assertEqual(
                kwargs["local_half_width_hz"],
                M37_RECEIVER_SIGNATURE_LOCAL_HALF_WIDTH_HZ,
            )
            self.assertEqual(
                kwargs["local_peak_snr_floor"],
                M37_RECEIVER_SIGNATURE_PEAK_SNR_FLOOR,
            )
            self.assertEqual(
                kwargs["maximum_queries"],
                M37_MAXIMUM_RECEIVER_SIGNATURE_QUERIES,
            )
            self.assertEqual(
                kwargs["maximum_local_channel_visits"],
                M37_MAXIMUM_RECEIVER_SIGNATURE_LOCAL_CHANNEL_VISITS,
            )
            self.assertIs(
                build_m37_receiver_frame_signatures_streaming(
                    [], {}, lambda _width: None, [], object(), table, grid
                ),
                sentinel,
            )
            self.assertEqual(
                streaming_generic.call_args.kwargs,
                generic.call_args.kwargs,
            )
            certificate["stack_statistic"] = "sum"
            with self.assertRaisesRegex(core.V0P6ContractError, "M37"):
                build_m37_receiver_frame_signatures(
                    [], {}, {}, [], object(), table, grid
                )
            with self.assertRaisesRegex(core.V0P6ContractError, "M37"):
                build_m37_receiver_frame_signatures_streaming(
                    [], {}, lambda _width: None, [], object(), table, grid
                )


if __name__ == "__main__":
    unittest.main()
