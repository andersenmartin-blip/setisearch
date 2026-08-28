"""Synthetic known-answer tests for the v0.6 receiver-alias stage."""

from __future__ import annotations

import hashlib
import json
import unittest

import numpy as np
import seti_repeater.search_v0p6 as v06

from seti_repeater.alias_v0p6 import (
    match_m37_receiver_frame_aliases,
    match_receiver_frame_aliases,
    validate_receiver_alias_result,
)
from seti_repeater.search_v0p6 import (
    M37_FACTOR_BASIS_LABELS_SHA256,
    M37_FACTOR_BASIS_SHA256,
    M37_FACTOR_ROW_SELECTION_SHA256S,
    M37_SCAN_INVENTORY_SHA256,
    CalibrationAccumulator,
    ExhaustiveRetentionLedger,
    V0P6CapacityError,
    V0P6ContractError,
    V0P6IncompleteError,
    calibrated_threshold,
    canonical_json_bytes,
    make_line_template_bank,
    make_proxy_carrier_grid,
    make_scramble_shift_table,
    scramble_table_sha256,
    template_bank_sha256,
    update_calibration,
)


class ReceiverAliasTests(unittest.TestCase):
    def make_product(
        self,
        *,
        template_count: int,
        amplitudes: tuple[float, ...] | None = None,
        spectral_widths: tuple[int, ...] = (1,),
        activity_subsets: tuple[tuple[int, ...], ...] = ((0, 1),),
    ):
        grid = make_proxy_carrier_grid(0.0001, 1.0, 1, 0)
        source_count = max(3, template_count)
        if source_count % 2 == 0:
            source_count += 1
        bank = make_line_template_bank(
            count=source_count, expected_sha256=None
        )[:template_count]
        bank_digest = template_bank_sha256(bank)
        shifts = make_scramble_shift_table(
            1,
            3,
            grid.score_bin_count,
            seed=370612,
            minimum_shift_bins=1,
        )
        calibration = CalibrationAccumulator.create(
            window_id="synthetic",
            score_bin_count=grid.score_bin_count,
            template_count=template_count,
            template_bank_sha256_value=bank_digest,
            factor_basis_sha256_value=M37_FACTOR_BASIS_SHA256,
            factor_basis_labels_sha256_value=M37_FACTOR_BASIS_LABELS_SHA256,
            scan_inventory_sha256_value=M37_SCAN_INVENTORY_SHA256,
            factor_row_selection_sha256_value=(
                M37_FACTOR_ROW_SELECTION_SHA256S["on"]
            ),
            factor_table_sha256_value="a" * 64,
            spectral_widths=spectral_widths,
            activity_subsets=activity_subsets,
            minimum_active_epoch_snr=None,
            stack_statistic="sum",
            scramble_shifts=shifts,
            minimum_shift_bins=1,
            expected_scramble_sha256=scramble_table_sha256(shifts),
        )
        null_vectors = np.zeros((3, grid.score_bin_count), dtype=np.float32)
        for template_index in range(template_count):
            for width_index in range(len(spectral_widths)):
                update_calibration(
                    calibration,
                    null_vectors,
                    template_index=template_index,
                    width_index=width_index,
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
            grid=grid,
            threshold_certificate=threshold,
            maximum_records=100,
            template_bank=bank,
            spectral_widths=spectral_widths,
            activity_subsets=activity_subsets,
            expected_template_bank_sha256=None,
            factor_basis_sha256=M37_FACTOR_BASIS_SHA256,
            factor_basis_labels_sha256=M37_FACTOR_BASIS_LABELS_SHA256,
            scan_inventory_sha256=M37_SCAN_INVENTORY_SHA256,
            factor_row_selection_sha256=(
                M37_FACTOR_ROW_SELECTION_SHA256S["on"]
            ),
            factor_table_sha256="a" * 64,
            epoch_count=3,
            minimum_active_epoch_snr=None,
            stack_statistic="sum",
        )
        if amplitudes is None:
            amplitudes = tuple(8.0 + index for index in range(template_count))
        center = grid.score_half_bins
        for template_index in range(template_count):
            for width_index, width in enumerate(spectral_widths):
                vectors = np.zeros((3, grid.score_bin_count), dtype=np.float32)
                vectors[:, center] = amplitudes[template_index]
                for subset in activity_subsets:
                    ledger.add_hypothesis(
                        vectors,
                        subset,
                        template=bank[template_index],
                        width_index=width_index,
                        width_channels=width,
                        exclusion_mask=None,
                    )
        records = ledger.finalize()
        certificate = ledger.certificate()
        for record in records:
            record["member_disposition"] = "pending_receiver_alias_evaluation"
        return grid, bank, records, certificate

    @staticmethod
    def signatures(
        records,
        *,
        peak_hz_by_template=None,
        peak_snr_by_template=None,
    ):
        peak_hz_by_template = (
            {} if peak_hz_by_template is None else peak_hz_by_template
        )
        peak_snr_by_template = (
            {} if peak_snr_by_template is None else peak_snr_by_template
        )
        result = {}
        for record in records:
            template_index = int(record["template_index"])
            base_hz = float(peak_hz_by_template.get(template_index, 0.0))
            snr = float(peak_snr_by_template.get(template_index, 8.0))
            entries = []
            for epoch in record["active_epochs_zero_based"]:
                # Whole-MHz epoch separation avoids manufacturing an
                # accidental >20 Hz subtraction at the literal boundary.
                peak_mhz = float(int(epoch)) + base_hz / 1e6
                predicted_mhz = peak_mhz
                entries.append(
                    {
                        "epoch_zero_based": int(epoch),
                        "predicted_mid_mhz": predicted_mhz,
                        "peak_frequency_mhz": peak_mhz,
                        "peak_snr": snr,
                        "offset_from_prediction_hz": float(
                            (peak_mhz - predicted_mhz) * 1e6
                        ),
                    }
                )
            result[str(record["record_id"])] = entries
        return result

    @staticmethod
    def prior_products(records, retention_certificate, *, adjacent_veto_templates=()):
        off_records = json.loads(canonical_json_bytes(list(records)))
        for record in off_records:
            disposition = record["member_disposition"]
            same = disposition == "rfi_veto_matched_off_same_hypothesis"
            local = disposition == "rfi_veto_local_off_track"
            witness = {
                "record_id": "f" * 64,
                "window_id": str(record["window_id"]),
                "snr": 8.0,
                "template_index": int(record["template_index"]),
                "spectral_width_index": int(record["spectral_width_index"]),
                "active_epochs_zero_based": list(
                    record["active_epochs_zero_based"]
                ),
                "proxy_carrier_index": int(record["proxy_carrier_index"]),
                "proxy_carrier_hz": float(record["proxy_carrier_hz"]),
                "maximum_track_distance_hz": 0.0,
            }
            record["off_track_evidence"] = {
                "contract": "max_i(abs(q * F_v_i - r * F_w_i)) <= tolerance_hz",
                "tolerance_hz": 20.0,
                "off_integration_count": 2,
                "off_factor_matrix_sha256": "b" * 64,
                "same_hypothesis": {
                    "matched": same,
                    "matched_off_record_count": int(same),
                    "best_off_witness": witness if same else None,
                },
                "local_track": {
                    "matched": local,
                    "matched_off_record_count": int(local),
                    "best_off_witness": witness if local else None,
                },
            }
        ordered_off = sorted(
            off_records,
            key=lambda item: (
                int(item["template_index"]),
                int(item["spectral_width_index"]),
                tuple(item["active_epochs_zero_based"]),
                int(item["proxy_carrier_index"]),
            ),
        )
        off_counts = {
            "pending_receiver_alias_evaluation": 0,
            "rfi_veto_local_off_track": 0,
            "rfi_veto_matched_off_same_hypothesis": 0,
        }
        for record in ordered_off:
            off_counts[record["member_disposition"]] += 1
        off_certificate = {
            "window_id": retention_certificate["window_id"],
            "contract": "literal maximum OFF-time track distance in Hz",
            "inclusive_comparison": "maximum_track_distance_hz <= tolerance_hz",
            "same_hypothesis_key_fields": [
                "template_index",
                "proxy_carrier_index",
                "spectral_width_index",
                "active_epochs_zero_based",
            ],
            "local_track_comparison_scope": "all retained OFF templates",
            "disposition_precedence": [
                "rfi_veto_matched_off_same_hypothesis",
                "rfi_veto_local_off_track",
                "pending_receiver_alias_evaluation",
            ],
            "best_witness_order": [
                "snr descending",
                "window_order index ascending",
                "template_index ascending",
                "spectral_width_index ascending",
                "activity_subset ordinal ascending",
                "proxy_carrier_index ascending",
                "record_id ascending",
            ],
            "annotated_record_order": [
                "template_index ascending",
                "spectral_width_index ascending",
                "active_epochs_zero_based lexicographic ascending",
                "proxy_carrier_index ascending",
            ],
            "tolerance_hz": 20.0,
            "off_integration_count": 2,
            "off_factor_matrix_sha256": "b" * 64,
            "factor_basis_sha256": retention_certificate[
                "factor_basis_sha256"
            ],
            "factor_basis_labels_sha256": retention_certificate[
                "factor_basis_labels_sha256"
            ],
            "scan_inventory_sha256": retention_certificate[
                "scan_inventory_sha256"
            ],
            "on_factor_row_selection_sha256": retention_certificate[
                "factor_row_selection_sha256"
            ],
            "off_factor_row_selection_sha256": "c" * 64,
            "factor_table_sha256": retention_certificate["factor_table_sha256"],
            "on_retention_certificate_sha256": retention_certificate[
                "retention_certificate_sha256"
            ],
            "off_retention_certificate_sha256": "d" * 64,
            "on_records_sha256": retention_certificate["records_sha256"],
            "off_records_sha256": "e" * 64,
            "on_record_count": len(ordered_off),
            "off_record_count": 1,
            "indexed_bucket_count": 1,
            "maximum_bucket_entries_observed": 1,
            "maximum_bucket_entries": 100,
            "exact_candidate_visits": 0,
            "maximum_exact_candidate_visits": 100,
            "anchor_pruning_roundoff_guard": (
                "4 * spacing(max(abs(on_anchor_hz), tolerance_hz, 1.0))"
            ),
            "maximum_anchor_pruning_roundoff_guard_hz": 0.0,
            "all_on_records_annotated_exactly_once": True,
            "disposition_counts": off_counts,
            "annotated_records_sha256": hashlib.sha256(
                canonical_json_bytes(ordered_off)
            ).hexdigest(),
            "maximum_annotated_record_canonical_bytes": 6_144,
            "maximum_annotated_evidence_canonical_bytes": 96_000_000,
            "annotated_evidence_canonical_bytes": sum(
                len(canonical_json_bytes(item)) for item in ordered_off
            ),
            "truncation_permitted": False,
        }
        off_certificate["off_match_certificate_sha256"] = hashlib.sha256(
            canonical_json_bytes(off_certificate)
        ).hexdigest()

        veto_templates = {int(item) for item in adjacent_veto_templates}
        adjacent_evidence = []
        queries = []
        for record in ordered_off:
            active = [int(epoch) for epoch in record["active_epochs_zero_based"]]
            measurements = []
            matching = []
            for position, epoch in enumerate(active):
                veto = (
                    int(record["template_index"]) in veto_templates
                    and position == 0
                )
                snr = 6.0 if veto else 0.0
                if veto:
                    matching.append(epoch)
                measurements.append(
                    {
                        "epoch_zero_based": epoch,
                        "paired_on_scan_label": f"epoch{epoch + 1}_on",
                        "paired_off_scan_label": f"epoch{epoch + 1}_off",
                        "snr": snr,
                        "meets_single_epoch_floor": veto,
                    }
                )
                queries.append(
                    {
                        "record_id": record["record_id"],
                        "epoch_zero_based": epoch,
                        "paired_off_scan_label": f"epoch{epoch + 1}_off",
                        "template_index": int(record["template_index"]),
                        "spectral_width_index": int(
                            record["spectral_width_index"]
                        ),
                        "proxy_carrier_index": int(
                            record["proxy_carrier_index"]
                        ),
                    }
                )
            adjacent_evidence.append(
                {
                    "record_id": record["record_id"],
                    "template_index": int(record["template_index"]),
                    "spectral_width_index": int(
                        record["spectral_width_index"]
                    ),
                    "spectral_width_channels": int(
                        record["spectral_width_channels"]
                    ),
                    "proxy_carrier_index": int(record["proxy_carrier_index"]),
                    "proxy_carrier_hz": float(record["proxy_carrier_hz"]),
                    "active_epochs_zero_based": active,
                    "single_epoch_snr_floor": 5.5,
                    "comparison": (
                        "native_gathered_snr >= single_epoch_snr_floor"
                    ),
                    "exact_same_q_template_width": True,
                    "exclusion_mask_applied": False,
                    "frequency_neighborhood_hz": 0.0,
                    "paired_adjacent_off_measurements": measurements,
                    "matching_active_epochs_zero_based": matching,
                    "maximum_active_epoch_snr": max(
                        item["snr"] for item in measurements
                    ),
                    "vetoed": bool(matching),
                    "recommended_member_disposition": (
                        "rfi_veto_single_adjacent_off"
                        if matching
                        else "pending_receiver_alias_evaluation"
                    ),
                }
            )
        evidence_bytes = canonical_json_bytes(adjacent_evidence)
        cache_inventory = []
        adjacent_certificate = {
            "window_id": retention_certificate["window_id"],
            "contract": "exact paired adjacent OFF q/template/width native gather",
            "comparison": "any active-epoch S/N >= single_epoch_snr_floor",
            "single_epoch_snr_floor": 5.5,
            "exact_same_q_template_width": True,
            "exclusion_mask_applied": False,
            "frequency_neighborhood_hz": 0.0,
            "on_retention_certificate_sha256": retention_certificate[
                "retention_certificate_sha256"
            ],
            "on_records_sha256": retention_certificate["records_sha256"],
            "proxy_grid_sha256": retention_certificate["proxy_grid_sha256"],
            "template_bank_sha256": retention_certificate["template_bank_sha256"],
            "factor_basis_sha256": retention_certificate["factor_basis_sha256"],
            "factor_basis_labels_sha256": retention_certificate[
                "factor_basis_labels_sha256"
            ],
            "scan_inventory_sha256": retention_certificate[
                "scan_inventory_sha256"
            ],
            "on_factor_row_selection_sha256": retention_certificate[
                "factor_row_selection_sha256"
            ],
            "off_factor_row_selection_sha256": "c" * 64,
            "factor_table_sha256": retention_certificate["factor_table_sha256"],
            "cache_inventory": cache_inventory,
            "cache_inventory_sha256": hashlib.sha256(
                canonical_json_bytes(cache_inventory)
            ).hexdigest(),
            "cache_count": 0,
            "query_inventory_sha256": hashlib.sha256(
                canonical_json_bytes(queries)
            ).hexdigest(),
            "query_count": len(queries),
            "maximum_queries": max(1, len(queries)),
            "input_record_count": len(adjacent_evidence),
            "evidence_record_count": len(adjacent_evidence),
            "maximum_records": 100,
            "maximum_evidence_record_canonical_bytes": 6_144,
            "maximum_evidence_canonical_bytes": 96_000_000,
            "evidence_canonical_bytes": len(evidence_bytes),
            "all_input_records_evaluated_exactly_once": True,
            "all_active_epoch_queries_evaluated_exactly_once": True,
            "truncation_permitted": False,
            "evidence_sha256": hashlib.sha256(evidence_bytes).hexdigest(),
        }
        adjacent_certificate[
            "single_adjacent_off_certificate_sha256"
        ] = hashlib.sha256(canonical_json_bytes(adjacent_certificate)).hexdigest()
        return (
            off_records,
            off_certificate,
            adjacent_evidence,
            adjacent_certificate,
        )

    def run_match(
        self,
        records,
        certificate,
        grid,
        bank,
        factors,
        signatures,
        *,
        maximum_records=100,
        maximum_bucket_entries=100,
        maximum_identity_comparisons=100,
        maximum_visits=100,
        adjacent_veto_templates=(),
        prior_products=None,
        receiver_signature_certificate_sha256=None,
        expected_receiver_signature_product_sha256=None,
    ):
        if prior_products is None:
            prior_products = self.prior_products(
                records,
                certificate,
                adjacent_veto_templates=adjacent_veto_templates,
            )
        (
            off_records,
            off_certificate,
            adjacent_evidence,
            adjacent_certificate,
        ) = prior_products
        return match_receiver_frame_aliases(
            off_records,
            certificate,
            grid,
            np.asarray(factors, dtype=np.float64),
            signatures,
            off_match_certificate=off_certificate,
            single_adjacent_off_evidence=adjacent_evidence,
            single_adjacent_off_certificate=adjacent_certificate,
            expected_off_match_certificate_sha256=off_certificate[
                "off_match_certificate_sha256"
            ],
            expected_single_adjacent_off_certificate_sha256=(
                adjacent_certificate[
                    "single_adjacent_off_certificate_sha256"
                ]
            ),
            window_order=("synthetic",),
            track_tolerance_hz=20.0,
            local_half_width_hz=100.0,
            local_peak_snr_floor=5.5,
            minimum_shared_active_epochs=2,
            maximum_records=maximum_records,
            maximum_bucket_entries=maximum_bucket_entries,
            maximum_identity_track_comparisons=(
                maximum_identity_comparisons
            ),
            maximum_distinct_candidate_visits_per_window=maximum_visits,
            template_bank=bank,
            receiver_signature_certificate_sha256=(
                receiver_signature_certificate_sha256
            ),
            expected_receiver_signature_product_sha256=(
                expected_receiver_signature_product_sha256
            ),
        )

    def test_signature_factory_receipt_is_bound_and_raw_m37_map_is_rejected(self):
        grid, bank, records, certificate = self.make_product(template_count=1)
        signatures = self.signatures(records)
        factors = np.asarray([[1.0] * 3])
        product = [
            {
                "record_id": str(record["record_id"]),
                "receiver_frame_signature": signatures[str(record["record_id"])],
            }
            for record in records
        ]
        product.sort(key=lambda item: item["record_id"])
        signature_product_sha = hashlib.sha256(
            canonical_json_bytes(product)
        ).hexdigest()
        signature_certificate_sha = "9" * 64
        result = self.run_match(
            records,
            certificate,
            grid,
            bank,
            factors,
            signatures,
            receiver_signature_certificate_sha256=signature_certificate_sha,
            expected_receiver_signature_product_sha256=signature_product_sha,
        )
        self.assertEqual(
            result["certificate"]["receiver_signature_certificate_sha256"],
            signature_certificate_sha,
        )
        alias_receipt = result["certificate"][
            "receiver_alias_certificate_sha256"
        ]
        validate_receiver_alias_result(
            result["records"],
            result["certificate"],
            expected_certificate_sha256=alias_receipt,
        )

        with self.assertRaisesRegex(
            V0P6ContractError,
            "receiver-signature result fields",
        ):
            match_m37_receiver_frame_aliases(
                [],
                {},
                None,
                None,
                (),
                signatures,
                off_match_certificate={},
                single_adjacent_off_evidence=(),
                single_adjacent_off_certificate={},
                expected_off_match_certificate_sha256="a" * 64,
                expected_single_adjacent_off_certificate_sha256="b" * 64,
                expected_receiver_signature_certificate_sha256="c" * 64,
            )

    def test_transitive_identity_components_ignore_width_and_subset(self):
        grid, bank, records, certificate = self.make_product(
            template_count=3,
            spectral_widths=(1, 3),
            activity_subsets=((0, 1), (0, 2)),
        )
        signatures = self.signatures(records)
        # At q=100 Hz: tracks are 100, 120 and 140 Hz.  The endpoints
        # are 40 Hz apart but belong to one component through the middle node.
        factors = np.asarray([[1.0] * 4, [1.2] * 4, [1.4] * 4])
        result = self.run_match(
            records,
            certificate,
            grid,
            bank,
            factors,
            signatures,
            maximum_bucket_entries=len(records),
            maximum_visits=len(records) * (len(records) - 1),
        )
        self.assertEqual(
            result["certificate"]["alias_identity_node_count"], 3
        )
        self.assertEqual(
            result["certificate"]["alias_identity_component_count"], 1
        )
        self.assertTrue(
            all(
                not item["receiver_alias_evidence"]["matched"]
                for item in result["records"]
            )
        )
        self.assertTrue(
            all(
                item["member_disposition"]
                == "pending_receiver_alias_evaluation"
                for item in result["records"]
            )
        )

    def test_alias_identity_track_comparison_cap_is_exact(self):
        grid, bank, records, certificate = self.make_product(template_count=3)
        signatures = self.signatures(records)
        factors = np.asarray([[1.0] * 3, [1.1] * 3, [1.2] * 3])
        with self.assertRaisesRegex(
            V0P6CapacityError,
            "identity track-comparison capacity exceeded",
        ):
            self.run_match(
                records,
                certificate,
                grid,
                bank,
                factors,
                signatures,
                maximum_identity_comparisons=2,
            )
        result = self.run_match(
            records,
            certificate,
            grid,
            bank,
            factors,
            signatures,
            maximum_identity_comparisons=3,
        )
        self.assertEqual(
            result["certificate"]["alias_identity_track_comparisons"],
            3,
        )
        self.assertEqual(
            result["certificate"][
                "maximum_alias_identity_track_comparisons"
            ],
            3,
        )
    def test_cross_component_brute_force_best_witness_order_and_precedence(self):
        grid, bank, records, certificate = self.make_product(template_count=3)
        signatures = self.signatures(records)
        factors = np.asarray([[1.0] * 3, [1.1] * 3, [3.0] * 3])
        by_template = {int(item["template_index"]): item for item in records}
        by_template[0]["member_disposition"] = "rfi_veto_local_off_track"
        result = self.run_match(
            records, certificate, grid, bank, factors, signatures
        )
        shuffled = self.run_match(
            list(reversed(records)),
            certificate,
            grid,
            bank,
            factors,
            dict(reversed(list(signatures.items()))),
        )
        self.assertEqual(canonical_json_bytes(result), canonical_json_bytes(shuffled))
        output = {int(item["template_index"]): item for item in result["records"]}
        self.assertEqual(
            output[0]["member_disposition"], "rfi_veto_local_off_track"
        )
        self.assertEqual(
            output[1]["member_disposition"], "rfi_veto_receiver_frame_alias"
        )
        self.assertEqual(
            output[2]["member_disposition"], "rfi_veto_receiver_frame_alias"
        )
        self.assertEqual(
            output[0]["receiver_alias_evidence"][
                "matched_cross_component_record_count"
            ],
            1,
        )
        # Template 2 can witness templates 0 and 1.  Template 1 has the
        # higher retained S/N and is therefore the deterministic witness.
        witness = output[2]["receiver_alias_evidence"][
            "best_receiver_alias_witness"
        ]
        self.assertEqual(witness["template_index"], 1)
        self.assertEqual(len(witness["matched_active_epochs"]), 2)

    def test_bucketed_matches_equal_independent_literal_brute_force(self):
        grid, bank, records, certificate = self.make_product(template_count=5)
        peak_hz = {0: 0.0, 1: 10.0, 2: 15.0, 3: 40.0, 4: 34.0}
        signatures = self.signatures(records, peak_hz_by_template=peak_hz)
        factors = np.asarray(
            [
                [1.00, 1.00, 1.00],
                [1.10, 1.05, 1.15],
                [1.40, 1.40, 1.40],
                [2.50, 2.50, 2.50],
                [4.00, 4.00, 4.00],
            ]
        )
        result = self.run_match(
            records, certificate, grid, bank, factors, signatures
        )
        source = sorted(records, key=lambda item: int(item["template_index"]))
        parent = list(range(len(source)))

        def find(index):
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left, right):
            left = find(left)
            right = find(right)
            if left != right:
                parent[right] = left

        tracks = [
            float(item["proxy_carrier_hz"])
            * factors[int(item["template_index"])]
            for item in source
        ]
        for left in range(len(source)):
            for right in range(left + 1, len(source)):
                if float(np.max(np.abs(tracks[left] - tracks[right]))) <= 20.0:
                    union(left, right)
        output_by_id = {item["record_id"]: item for item in result["records"]}
        for left_index, left in enumerate(source):
            matches = []
            left_signature = signatures[left["record_id"]]
            for right_index, right in enumerate(source):
                if left_index == right_index or find(left_index) == find(right_index):
                    continue
                right_signature = signatures[right["record_id"]]
                literal = [
                    epoch
                    for epoch in range(2)
                    if abs(
                        (
                            right_signature[epoch]["peak_frequency_mhz"]
                            - left_signature[epoch]["peak_frequency_mhz"]
                        )
                        * 1e6
                    )
                    <= 20.0
                ]
                if len(literal) >= 2:
                    matches.append(right)
            matches.sort(
                key=lambda item: (
                    -float(item["snr"]),
                    int(item["template_index"]),
                    int(item["spectral_width_index"]),
                    tuple(item["active_epochs_zero_based"]),
                    int(item["proxy_carrier_index"]),
                    item["record_id"],
                )
            )
            evidence = output_by_id[left["record_id"]]["receiver_alias_evidence"]
            self.assertEqual(
                evidence["matched_cross_component_record_count"], len(matches)
            )
            self.assertEqual(
                None
                if not matches
                else evidence["best_receiver_alias_witness"]["record_id"],
                None if not matches else matches[0]["record_id"],
            )

    def test_exact_capacity_boundaries_and_visits_before_component_rejection(self):
        grid, bank, records, certificate = self.make_product(template_count=3)
        signatures = self.signatures(records)
        factors = np.asarray([[1.0] * 2, [1.1] * 2, [1.2] * 2])
        accepted = self.run_match(
            records,
            certificate,
            grid,
            bank,
            factors,
            signatures,
            maximum_records=3,
            maximum_bucket_entries=3,
            maximum_visits=6,
        )
        self.assertEqual(accepted["certificate"]["bucket_entries"], 3)
        self.assertEqual(
            accepted["certificate"][
                "maximum_distinct_candidate_visits_observed_per_left"
            ],
            2,
        )
        self.assertEqual(
            accepted["certificate"]["total_distinct_candidate_visits"], 6
        )
        self.assertEqual(
            accepted["certificate"][
                "maximum_distinct_candidate_visits_per_window"
            ],
            6,
        )
        self.assertTrue(
            all(
                not item["receiver_alias_evidence"]["matched"]
                for item in accepted["records"]
            )
        )
        with self.assertRaisesRegex(V0P6CapacityError, "input-record"):
            self.run_match(
                records,
                certificate,
                grid,
                bank,
                factors,
                signatures,
                maximum_records=2,
            )
        with self.assertRaisesRegex(V0P6CapacityError, "bucket-entry"):
            self.run_match(
                records,
                certificate,
                grid,
                bank,
                factors,
                signatures,
                maximum_bucket_entries=2,
            )
        with self.assertRaisesRegex(V0P6CapacityError, "candidate-visit"):
            self.run_match(
                records,
                certificate,
                grid,
                bank,
                factors,
                signatures,
                maximum_visits=5,
            )

    def test_trusted_prior_receipts_bind_dispositions_and_precedence(self):
        grid, bank, records, certificate = self.make_product(template_count=3)
        records[0]["member_disposition"] = "rfi_veto_local_off_track"
        signatures = self.signatures(records)
        factors = np.asarray([[1.0] * 2, [1.1] * 2, [3.0] * 2])
        priors = self.prior_products(
            records, certificate, adjacent_veto_templates=(0, 1)
        )
        result = self.run_match(
            records,
            certificate,
            grid,
            bank,
            factors,
            signatures,
            prior_products=priors,
        )
        output = {int(item["template_index"]): item for item in result["records"]}
        self.assertEqual(
            output[0]["member_disposition"], "rfi_veto_local_off_track"
        )
        self.assertEqual(
            output[1]["member_disposition"], "rfi_veto_single_adjacent_off"
        )
        self.assertEqual(
            output[2]["member_disposition"], "rfi_veto_receiver_frame_alias"
        )

        off_records, off_certificate, adjacent, adjacent_certificate = priors
        mutated_off = json.loads(canonical_json_bytes(off_records))
        mutated_off[0]["member_disposition"] = "pending_receiver_alias_evaluation"
        with self.assertRaisesRegex(
            (V0P6IncompleteError, V0P6ContractError),
            "OFF-match.*(changed|precedence|bind)",
        ):
            self.run_match(
                records,
                certificate,
                grid,
                bank,
                factors,
                signatures,
                prior_products=(
                    mutated_off,
                    off_certificate,
                    adjacent,
                    adjacent_certificate,
                ),
            )

        mutated_adjacent = json.loads(canonical_json_bytes(adjacent))
        mutated_adjacent[1]["vetoed"] = False
        with self.assertRaisesRegex(
            (V0P6IncompleteError, V0P6ContractError),
            "single-adjacent-OFF.*(changed|reproduce|inconsistent)",
        ):
            self.run_match(
                records,
                certificate,
                grid,
                bank,
                factors,
                signatures,
                prior_products=(
                    off_records,
                    off_certificate,
                    mutated_adjacent,
                    adjacent_certificate,
                ),
            )

    def test_literal_signature_boundaries_and_complete_coverage(self):
        grid, bank, records, certificate = self.make_product(template_count=2)
        factors = np.asarray([[1.0] * 2, [3.0] * 2])
        signatures = self.signatures(
            records,
            peak_hz_by_template={0: 0.0, 1: 20.0},
            peak_snr_by_template={0: 5.5, 1: 5.5},
        )
        accepted = self.run_match(
            records, certificate, grid, bank, factors, signatures
        )
        self.assertTrue(
            all(
                item["receiver_alias_evidence"]["matched"]
                for item in accepted["records"]
            )
        )
        rounding_boundary = self.signatures(records)
        boundary_peaks = (
            1.9999999999999995e-05,
            3.9999999999999996e-05,
        )
        self.assertEqual(
            (boundary_peaks[1] - boundary_peaks[0]) * 1e6, 20.0
        )
        for record in records:
            peak_mhz = boundary_peaks[int(record["template_index"])]
            for entry in rounding_boundary[record["record_id"]]:
                entry["predicted_mid_mhz"] = peak_mhz
                entry["peak_frequency_mhz"] = peak_mhz
                entry["offset_from_prediction_hz"] = 0.0
        boundary_result = self.run_match(
            records, certificate, grid, bank, factors, rounding_boundary
        )
        self.assertTrue(
            all(
                item["receiver_alias_evidence"]["matched"]
                for item in boundary_result["records"]
            )
        )
        below = self.signatures(
            records,
            peak_hz_by_template={0: 0.0, 1: 20.0},
            peak_snr_by_template={0: 5.5, 1: np.nextafter(5.5, -np.inf)},
        )
        rejected = self.run_match(
            records, certificate, grid, bank, factors, below
        )
        self.assertTrue(
            all(
                not item["receiver_alias_evidence"]["matched"]
                for item in rejected["records"]
            )
        )
        missing = dict(signatures)
        missing.pop(next(iter(missing)))
        with self.assertRaisesRegex(V0P6IncompleteError, "exact.*inventory"):
            self.run_match(records, certificate, grid, bank, factors, missing)

        outside = self.signatures(records)
        entry = outside[str(records[0]["record_id"])][0]
        entry["predicted_mid_mhz"] = 0.0
        entry["peak_frequency_mhz"] = np.nextafter(100.0e-6, np.inf)
        entry["offset_from_prediction_hz"] = float(
            (entry["peak_frequency_mhz"] - entry["predicted_mid_mhz"]) * 1e6
        )
        with self.assertRaisesRegex(V0P6ContractError, "outside.*local window"):
            self.run_match(records, certificate, grid, bank, factors, outside)

    def test_signature_numeric_fields_require_json_numbers(self):
        grid, bank, records, certificate = self.make_product(template_count=2)
        factors = np.asarray([[1.0] * 2, [3.0] * 2])
        record_id = str(records[0]["record_id"])
        cases = (
            ("predicted_mid_mhz", "string"),
            ("peak_frequency_mhz", "string"),
            ("peak_snr", "string"),
            ("offset_from_prediction_hz", "string"),
            ("peak_snr", "bool"),
        )
        for field, kind in cases:
            with self.subTest(field=field, kind=kind):
                signatures = self.signatures(records)
                entry = signatures[record_id][0]
                entry[field] = str(entry[field]) if kind == "string" else True
                with self.assertRaisesRegex(
                    V0P6ContractError, "finite JSON number"
                ):
                    self.run_match(
                        records,
                        certificate,
                        grid,
                        bank,
                        factors,
                        signatures,
                    )

    def test_result_and_per_record_evidence_hashes_detect_mutation(self):
        grid, bank, records, certificate = self.make_product(template_count=2)
        signatures = self.signatures(records)
        factors = np.asarray([[1.0] * 2, [3.0] * 2])
        result = self.run_match(
            records, certificate, grid, bank, factors, signatures
        )
        receipt = result["certificate"]["receiver_alias_certificate_sha256"]
        validated = validate_receiver_alias_result(
            result["records"],
            result["certificate"],
            expected_certificate_sha256=receipt,
        )
        self.assertEqual(validated["receiver_alias_certificate_sha256"], receipt)

        mutated = [dict(item) for item in result["records"]]
        mutated[0] = dict(mutated[0])
        mutated[0]["receiver_alias_evidence"] = dict(
            mutated[0]["receiver_alias_evidence"]
        )
        mutated[0]["receiver_alias_evidence"]["matched"] = False
        with self.assertRaisesRegex(V0P6IncompleteError, "annotated records changed"):
            validate_receiver_alias_result(mutated, result["certificate"])

        rehashed = dict(result["certificate"])
        rehashed["annotated_records_sha256"] = hashlib.sha256(
            canonical_json_bytes(mutated)
        ).hexdigest()
        rehashed.pop("receiver_alias_certificate_sha256")
        rehashed["receiver_alias_certificate_sha256"] = hashlib.sha256(
            canonical_json_bytes(rehashed)
        ).hexdigest()
        with self.assertRaisesRegex(V0P6IncompleteError, "evidence SHA-256"):
            validate_receiver_alias_result(
                mutated,
                rehashed,
                expected_certificate_sha256=rehashed[
                    "receiver_alias_certificate_sha256"
                ],
            )

        forged = dict(result["certificate"])
        forged["maximum_records"] += 1
        forged.pop("receiver_alias_certificate_sha256")
        forged["receiver_alias_certificate_sha256"] = hashlib.sha256(
            canonical_json_bytes(forged)
        ).hexdigest()
        with self.assertRaisesRegex(V0P6ContractError, "differs from receipt"):
            validate_receiver_alias_result(
                result["records"],
                forged,
                expected_certificate_sha256=receipt,
            )

    def test_trusted_alias_witness_numeric_string_is_rejected(self):
        grid, bank, records, certificate = self.make_product(template_count=2)
        result = self.run_match(
            records,
            certificate,
            grid,
            bank,
            np.asarray([[1.0] * 2, [3.0] * 2]),
            self.signatures(records),
        )
        mutated = json.loads(canonical_json_bytes(result["records"]))
        evidence = next(
            item["receiver_alias_evidence"]
            for item in mutated
            if item["receiver_alias_evidence"][
                "best_receiver_alias_witness"
            ]
            is not None
        )
        witness_epoch = evidence["best_receiver_alias_witness"][
            "matched_active_epochs"
        ][0]
        witness_epoch["left_peak_snr"] = str(witness_epoch["left_peak_snr"])
        evidence.pop("receiver_alias_evidence_sha256")
        evidence["receiver_alias_evidence_sha256"] = hashlib.sha256(
            canonical_json_bytes(evidence)
        ).hexdigest()

        rehashed = json.loads(canonical_json_bytes(result["certificate"]))
        rehashed["annotated_records_sha256"] = hashlib.sha256(
            canonical_json_bytes(mutated)
        ).hexdigest()
        rehashed.pop("receiver_alias_certificate_sha256")
        rehashed["receiver_alias_certificate_sha256"] = hashlib.sha256(
            canonical_json_bytes(rehashed)
        ).hexdigest()
        with self.assertRaisesRegex(
            V0P6ContractError, "finite JSON number"
        ):
            validate_receiver_alias_result(
                mutated,
                rehashed,
                expected_certificate_sha256=rehashed[
                    "receiver_alias_certificate_sha256"
                ],
            )

    def test_persisted_retention_receipt_is_forwarded_to_record_validation(self):
        grid, bank, records, certificate = self.make_product(template_count=2)
        (
            off_records,
            off_certificate,
            adjacent_evidence,
            adjacent_certificate,
        ) = self.prior_products(records, certificate)
        digest = certificate["retention_certificate_sha256"]
        attestation = v06._RETENTION_CERTIFICATE_ATTESTATIONS.pop(digest)
        try:
            result = match_receiver_frame_aliases(
                off_records,
                certificate,
                grid,
                np.asarray([[1.0] * 2, [3.0] * 2]),
                self.signatures(records),
                off_match_certificate=off_certificate,
                single_adjacent_off_evidence=adjacent_evidence,
                single_adjacent_off_certificate=adjacent_certificate,
                expected_off_match_certificate_sha256=off_certificate[
                    "off_match_certificate_sha256"
                ],
                expected_single_adjacent_off_certificate_sha256=(
                    adjacent_certificate[
                        "single_adjacent_off_certificate_sha256"
                    ]
                ),
                window_order=("synthetic",),
                track_tolerance_hz=20.0,
                local_half_width_hz=100.0,
                local_peak_snr_floor=5.5,
                minimum_shared_active_epochs=2,
                maximum_records=100,
                maximum_bucket_entries=100,
                maximum_identity_track_comparisons=100,
                maximum_distinct_candidate_visits_per_window=100,
                template_bank=bank,
                expected_on_certificate_sha256=digest,
            )
            self.assertEqual(result["certificate"]["input_record_count"], 2)
        finally:
            v06._RETENTION_CERTIFICATE_ATTESTATIONS[digest] = attestation


if __name__ == "__main__":
    unittest.main()
