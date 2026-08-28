"""Adversarial tests for the receipt-bound detector-v0.6 M37 outcome."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import unittest
from unittest import mock

import seti_repeater.outcome_v0p6 as outcome
import seti_repeater.search_v0p6 as core
import seti_repeater.significance_v0p6 as significance


def _sha(value):
    return hashlib.sha256(core.canonical_json_bytes(value)).hexdigest()


def _stub_alias_validator(records, certificate, *, expected_certificate_sha256=None):
    detached_records = json.loads(core.canonical_json_bytes(list(records)))
    cert = json.loads(core.canonical_json_bytes(dict(certificate)))
    observed = cert.pop("receiver_alias_certificate_sha256")
    if observed != _sha(cert) or observed != expected_certificate_sha256:
        raise core.V0P6IncompleteError("alias receipt mismatch")
    cert["receiver_alias_certificate_sha256"] = observed
    if cert["annotated_records_sha256"] != _sha(detached_records):
        raise core.V0P6IncompleteError("alias records mismatch")
    if cert["input_record_count"] != len(detached_records):
        raise core.V0P6IncompleteError("alias count mismatch")
    return cert


def _base_record(window_id, ordinal, record_ordinal, snr):
    record_id = _sha(
        {
            "window_id": window_id,
            "window_ordinal": ordinal,
            "record_ordinal": record_ordinal,
        }
    )
    return {
        "record_id": record_id,
        "window_id": window_id,
        "snr": float(snr),
        "template_index": 0,
        "spectral_width_index": 0,
        "active_epochs_zero_based": [0, 1],
        "proxy_carrier_index": record_ordinal,
        "member_disposition": "pending_physical_veto_evaluation",
    }


def _significance_result(window_id, bases, exceedances, retention_sha, threshold_sha):
    evidence = []
    for base, exceedance_count in zip(bases, exceedances, strict=True):
        rank_p = float((1 + exceedance_count) / (core.M37_SCRAMBLE_COUNT + 1))
        payload = {
            "schema_version": significance.SIGNIFICANCE_SCHEMA_VERSION,
            "record_id": base["record_id"],
            "retained_record_sha256": _sha(base),
            "retained_snr": base["snr"],
            "global_null_count": core.M37_SCRAMBLE_COUNT,
            "inclusive_null_comparison": significance.INCLUSIVE_NULL_COMPARISON,
            "inclusive_null_exceedance_count": exceedance_count,
            "inclusive_rank_p_definition": significance.INCLUSIVE_RANK_P_DEFINITION,
            "inclusive_global_rank_p": rank_p,
            "scientific_empirical_p_ceiling": core.M37_SCIENTIFIC_P_CEILING,
            "scientific_eligibility_comparison": (
                significance.SCIENTIFIC_ELIGIBILITY_COMPARISON
            ),
            "scientifically_eligible": rank_p <= core.M37_SCIENTIFIC_P_CEILING,
        }
        item = dict(payload)
        item["evidence_sha256"] = _sha(payload)
        evidence.append(item)
    evidence.sort(key=lambda item: item["record_id"])
    ids = [item["record_id"] for item in evidence]
    item_hashes = [item["evidence_sha256"] for item in evidence]
    evidence_bytes = core.canonical_json_bytes(evidence)
    certificate_payload = {
        "artifact_type": significance.SIGNIFICANCE_ARTIFACT_TYPE,
        "schema_version": significance.SIGNIFICANCE_SCHEMA_VERSION,
        "detector_version": core.DETECTOR_VERSION,
        "window_id": window_id,
        "source_scan_kind": "on",
        "evidence_sort_order": significance.EVIDENCE_SORT_ORDER,
        "inclusive_null_comparison": significance.INCLUSIVE_NULL_COMPARISON,
        "inclusive_rank_p_definition": significance.INCLUSIVE_RANK_P_DEFINITION,
        "scientific_eligibility_comparison": (
            significance.SCIENTIFIC_ELIGIBILITY_COMPARISON
        ),
        "scientific_eligibility_requires_retained_operational_threshold": True,
        "retention_certificate_sha256": retention_sha,
        "threshold_certificate_sha256": threshold_sha,
        "source_records_sha256": _sha(bases),
        "proxy_grid_sha256": core.proxy_carrier_grid_sha256(
            core.make_m37_proxy_carrier_grid(window_id)
        ),
        "template_bank_sha256": core.M37_BANK_SHA256,
        "template_count": core.M37_TEMPLATE_COUNT,
        "experiment_contract_sha256": core.M37_EXPERIMENT_CONTRACT_SHA256,
        "analysis_contract_sha256": "1" * 64,
        "factor_basis_sha256": core.M37_FACTOR_BASIS_SHA256,
        "factor_basis_labels_sha256": core.M37_FACTOR_BASIS_LABELS_SHA256,
        "scan_inventory_sha256": core.M37_SCAN_INVENTORY_SHA256,
        "on_factor_row_selection_sha256": (
            core.M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        ),
        "factor_table_sha256": "2" * 64,
        "threshold_window_ids": list(core.M37_WINDOW_IDS),
        "global_null_shape": [core.M37_SCRAMBLE_COUNT],
        "global_null_dtype_encoding": "little-endian float64",
        "global_null_maxima_sha256": "3" * 64,
        "global_null_count": core.M37_SCRAMBLE_COUNT,
        "operational_threshold_snr": 7.0,
        "scientific_empirical_p_ceiling": core.M37_SCIENTIFIC_P_CEILING,
        "input_record_count": len(evidence),
        "evidence_record_count": len(evidence),
        "record_ids_sha256": _sha(ids),
        "evidence_item_sha256s_sha256": _sha(item_hashes),
        "evidence_sha256": hashlib.sha256(evidence_bytes).hexdigest(),
        "evidence_canonical_bytes": len(evidence_bytes),
        "maximum_evidence_canonical_bytes": (
            core.M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES
        ),
        "all_input_records_evaluated_exactly_once": True,
        "truncation_permitted": False,
    }
    certificate = dict(certificate_payload)
    certificate["significance_certificate_sha256"] = _sha(certificate_payload)
    result_payload = {"evidence": evidence, "certificate": certificate}
    result = dict(result_payload)
    result["result_sha256"] = _sha(result_payload)
    return result


def _window_input(window_id, ordinal, specs, threshold_sha):
    retention_sha = _sha({"retention": window_id})
    bases = []
    alias_records = []
    exceedances = []
    for record_ordinal, (physical_disposition, exceedance_count) in enumerate(specs):
        base = _base_record(window_id, ordinal, record_ordinal, 20.0 + record_ordinal)
        alias_record = deepcopy(base)
        alias_record["member_disposition"] = physical_disposition
        alias_record["off_track_evidence"] = {"sealed": True}
        alias_record["single_adjacent_off_evidence"] = {"sealed": True}
        alias_record["receiver_alias_evidence"] = {"sealed": True}
        bases.append(base)
        alias_records.append(alias_record)
        exceedances.append(exceedance_count)
    alias_certificate_payload = {
        "window_id": window_id,
        "window_ordinal": ordinal,
        "input_record_count": len(alias_records),
        "maximum_records": core.M37_MAXIMUM_RECORDS_PER_WINDOW,
        "on_integration_count": 48,
        "track_tolerance_hz": outcome.alias_stage.M37_ALIAS_TRACK_TOLERANCE_HZ,
        "local_receiver_half_width_hz": (
            outcome.alias_stage.M37_RECEIVER_LOCAL_HALF_WIDTH_HZ
        ),
        "local_peak_snr_floor": outcome.alias_stage.M37_RECEIVER_PEAK_SNR_FLOOR,
        "minimum_shared_active_epochs": (
            outcome.alias_stage.M37_RECEIVER_MINIMUM_SHARED_ACTIVE_EPOCHS
        ),
        "maximum_bucket_entries": core.M37_MAXIMUM_ALIAS_BUCKET_ENTRIES,
        "maximum_distinct_candidate_visits_per_window": (
            core.M37_MAXIMUM_ALIAS_NEIGHBOR_VISITS
        ),
        "on_factor_matrix_sha256": "4" * 64,
        "on_retention_certificate_sha256": retention_sha,
        "receiver_signature_certificate_sha256": _sha(
            {"receiver-signature": window_id}
        ),
        "alias_identity_track_comparison_definition": (
            "candidate node pair surviving first-ON-time anchor pruning before "
            "literal all-ON-time track comparison"
        ),
        "alias_identity_track_comparisons": 0,
        "maximum_alias_identity_track_comparisons": (
            outcome.alias_stage.M37_MAXIMUM_ALIAS_IDENTITY_TRACK_COMPARISONS
        ),
        "annotated_records_sha256": _sha(alias_records),
        "all_on_records_annotated_exactly_once": True,
        "truncation_permitted": False,
    }
    alias_certificate = dict(alias_certificate_payload)
    alias_certificate["receiver_alias_certificate_sha256"] = _sha(
        alias_certificate_payload
    )
    alias_result = {
        "records": alias_records,
        "certificate": alias_certificate,
    }
    significance_result = _significance_result(
        window_id, bases, exceedances, retention_sha, threshold_sha
    )
    return {
        "window_id": window_id,
        "alias_result": alias_result,
        "significance_result": significance_result,
        "expected_alias_certificate_sha256": alias_certificate[
            "receiver_alias_certificate_sha256"
        ],
        "expected_significance_result_sha256": significance_result[
            "result_sha256"
        ],
        "expected_retention_certificate_sha256": retention_sha,
    }


def _real_empty_alias_result(window_id, ordinal, retention_sha):
    """Build the exact empty schema accepted by the real alias validator."""
    empty_inventory_sha = _sha([])
    certificate_payload = {
        "window_id": window_id,
        "window_ordinal": ordinal,
        "contract": (
            "cross-component stationary receiver peaks in at least two "
            "common active ON epochs"
        ),
        "identity_partition_contract": (
            "connected components of unique (template_index, proxy_carrier_index) "
            "under literal maximum ON-time track distance"
        ),
        "track_comparison": (
            "max_i(abs(q * F_v_i - r * F_w_i)) <= tolerance_hz"
        ),
        "track_tolerance_hz": outcome.alias_stage.M37_ALIAS_TRACK_TOLERANCE_HZ,
        "on_integration_count": 48,
        "on_factor_matrix_sha256": "4" * 64,
        "local_receiver_half_width_hz": (
            outcome.alias_stage.M37_RECEIVER_LOCAL_HALF_WIDTH_HZ
        ),
        "local_peak_snr_comparison": (
            "peak_snr >= local_peak_snr_floor"
        ),
        "local_peak_snr_floor": outcome.alias_stage.M37_RECEIVER_PEAK_SNR_FLOOR,
        "peak_separation_comparison": (
            "abs(delta_hz) <= track_tolerance_hz"
        ),
        "minimum_shared_active_epochs": (
            outcome.alias_stage.M37_RECEIVER_MINIMUM_SHARED_ACTIVE_EPOCHS
        ),
        "on_retention_certificate_sha256": retention_sha,
        "off_match_certificate_sha256": _sha({"off-match": window_id}),
        "single_adjacent_off_certificate_sha256": _sha(
            {"single-adjacent-off": window_id}
        ),
        "input_off_annotated_records_sha256": empty_inventory_sha,
        "single_adjacent_off_evidence_sha256": empty_inventory_sha,
        "receiver_signature_product_sha256": _sha(
            {"receiver-signature-product": window_id}
        ),
        "receiver_signature_certificate_sha256": _sha(
            {"receiver-signature": window_id}
        ),
        "alias_identity_partition_sha256": empty_inventory_sha,
        "alias_identity_node_count": 0,
        "alias_identity_component_count": 0,
        "alias_identity_edge_count": 0,
        "alias_identity_track_comparison_definition": (
            "candidate node pair surviving first-ON-time anchor pruning before "
            "literal all-ON-time track comparison"
        ),
        "alias_identity_track_comparisons": 0,
        "maximum_alias_identity_track_comparisons": (
            outcome.alias_stage.M37_MAXIMUM_ALIAS_IDENTITY_TRACK_COMPARISONS
        ),
        "alias_identity_anchor_pruning_roundoff_guard": (
            "4 * spacing(max(abs(left_anchor_hz), tolerance_hz, 1.0))"
        ),
        "maximum_alias_identity_anchor_pruning_roundoff_guard_hz": 0.0,
        "input_record_count": 0,
        "maximum_records": core.M37_MAXIMUM_RECORDS_PER_WINDOW,
        "bucket_entry_definition": (
            "sum C(k, 2) over records, where k is the number of active "
            "signature epochs with peak_snr >= local_peak_snr_floor"
        ),
        "bucket_entries": 0,
        "maximum_bucket_entries": core.M37_MAXIMUM_ALIAS_BUCKET_ENTRIES,
        "bucket_neighbor_cell_radius": 2,
        "candidate_visit_definition": (
            "cumulative per-window sum of distinct other records reached for "
            "each left record before identity and literal-match rejection"
        ),
        "total_distinct_candidate_visits": 0,
        "maximum_distinct_candidate_visits_observed_per_left": 0,
        "maximum_distinct_candidate_visits_per_window": (
            core.M37_MAXIMUM_ALIAS_NEIGHBOR_VISITS
        ),
        "all_on_records_annotated_exactly_once": True,
        "disposition_counts": {
            "pending_receiver_alias_evaluation": 0,
            "rfi_veto_local_off_track": 0,
            "rfi_veto_matched_off_same_hypothesis": 0,
            "rfi_veto_receiver_frame_alias": 0,
            "rfi_veto_single_adjacent_off": 0,
        },
        "annotated_records_sha256": empty_inventory_sha,
        "truncation_permitted": False,
    }
    certificate = dict(certificate_payload)
    certificate["receiver_alias_certificate_sha256"] = _sha(
        certificate_payload
    )
    return {"records": [], "certificate": certificate}


def _five_windows(first_specs=(), other_specs=()):
    threshold_sha = "a" * 64
    inputs = [
        _window_input(
            window_id,
            ordinal,
            first_specs if ordinal == 0 else other_specs,
            threshold_sha,
        )
        for ordinal, window_id in enumerate(core.M37_WINDOW_IDS)
    ]
    return inputs, threshold_sha


def _reseal_alias(window_input):
    certificate = window_input["alias_result"]["certificate"]
    certificate["input_record_count"] = len(window_input["alias_result"]["records"])
    certificate["annotated_records_sha256"] = _sha(
        window_input["alias_result"]["records"]
    )
    payload = dict(certificate)
    payload.pop("receiver_alias_certificate_sha256", None)
    certificate["receiver_alias_certificate_sha256"] = _sha(payload)
    window_input["expected_alias_certificate_sha256"] = certificate[
        "receiver_alias_certificate_sha256"
    ]


def _reseal_significance(window_input):
    result = window_input["significance_result"]
    for item in result["evidence"]:
        payload = dict(item)
        payload.pop("evidence_sha256", None)
        item["evidence_sha256"] = _sha(payload)
    certificate = result["certificate"]
    ids = [item["record_id"] for item in result["evidence"]]
    item_hashes = [item["evidence_sha256"] for item in result["evidence"]]
    evidence_bytes = core.canonical_json_bytes(result["evidence"])
    certificate["input_record_count"] = len(result["evidence"])
    certificate["evidence_record_count"] = len(result["evidence"])
    certificate["record_ids_sha256"] = _sha(ids)
    certificate["evidence_item_sha256s_sha256"] = _sha(item_hashes)
    certificate["evidence_sha256"] = hashlib.sha256(evidence_bytes).hexdigest()
    certificate["evidence_canonical_bytes"] = len(evidence_bytes)
    certificate_payload = dict(certificate)
    certificate_payload.pop("significance_certificate_sha256", None)
    certificate["significance_certificate_sha256"] = _sha(certificate_payload)
    result_payload = {
        "evidence": result["evidence"],
        "certificate": certificate,
    }
    result["result_sha256"] = _sha(result_payload)
    window_input["expected_significance_result_sha256"] = result["result_sha256"]


def _reseal_outcome(result):
    forged = deepcopy(result)
    for record in forged["records"]:
        payload = dict(record)
        payload.pop("outcome_record_sha256", None)
        record["outcome_record_sha256"] = _sha(payload)
    certificate = forged["certificate"]
    cursor = 0
    for receipt in certificate["window_receipts"]:
        count = receipt["record_count"]
        window_records = forged["records"][cursor : cursor + count]
        cursor += count
        receipt["outcome_record_sha256s_sha256"] = _sha(
            [item["outcome_record_sha256"] for item in window_records]
        )
    records_bytes = core.canonical_json_bytes(forged["records"])
    certificate["outcome_record_ids_sha256"] = _sha(
        [item["record_id"] for item in forged["records"]]
    )
    certificate["outcome_item_sha256s_sha256"] = _sha(
        [item["outcome_record_sha256"] for item in forged["records"]]
    )
    certificate["outcome_records_sha256"] = hashlib.sha256(records_bytes).hexdigest()
    certificate["outcome_records_canonical_bytes"] = len(records_bytes)
    certificate_payload = dict(certificate)
    certificate_payload.pop("outcome_certificate_sha256", None)
    certificate["outcome_certificate_sha256"] = _sha(certificate_payload)
    result_payload = {
        "records": forged["records"],
        "certificate": certificate,
    }
    forged["result_sha256"] = _sha(result_payload)
    return forged


class M37OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.alias_patch = mock.patch.object(
            outcome.alias_stage,
            "validate_receiver_alias_result",
            side_effect=_stub_alias_validator,
        )
        self.alias_patch.start()

    def tearDown(self):
        self.alias_patch.stop()

    def assemble(self, inputs, threshold_sha):
        return outcome.assemble_m37_outcome(
            inputs,
            expected_threshold_certificate_sha256=threshold_sha,
        )

    def test_exact_id_join_disposition_precedence_and_open_state(self):
        specs = (
            (outcome.UNVETOED_PHYSICAL_DISPOSITION, 0),
            (outcome.UNVETOED_PHYSICAL_DISPOSITION, 2),
            ("rfi_veto_matched_off_same_hypothesis", 0),
            ("rfi_veto_local_off_track", 0),
            ("rfi_veto_single_adjacent_off", 0),
            ("rfi_veto_receiver_frame_alias", 0),
        )
        inputs, threshold_sha = _five_windows(first_specs=specs)
        result = self.assemble(inputs, threshold_sha)
        by_physical = {}
        for record in result["records"]:
            by_physical.setdefault(record["physical_disposition"], []).append(record)
        unvetoed = by_physical[outcome.UNVETOED_PHYSICAL_DISPOSITION]
        self.assertEqual(
            [item["final_disposition"] for item in unvetoed],
            [
                outcome.SCIENTIFIC_CANDIDATE_UNRESOLVED,
                outcome.RETAINED_NOT_SCIENTIFICALLY_ELIGIBLE,
            ],
        )
        for disposition in outcome.PHYSICAL_RFI_DISPOSITIONS:
            item = by_physical[disposition][0]
            self.assertTrue(
                item["global_rank_p_evidence"]["scientifically_eligible"]
            )
            self.assertEqual(item["final_disposition"], disposition)
        certificate = result["certificate"]
        self.assertEqual(certificate["global_search_state"], "open")
        self.assertTrue(certificate["unresolved_scientific_candidates"])
        self.assertEqual(certificate["unresolved_candidate_count"], 1)
        self.assertEqual(outcome.validate_m37_outcome(result), result)

    def test_five_complete_windows_without_candidate_close_cleanly(self):
        inputs, threshold_sha = _five_windows(
            first_specs=((outcome.UNVETOED_PHYSICAL_DISPOSITION, 2),)
        )
        result = self.assemble(inputs, threshold_sha)
        certificate = result["certificate"]
        self.assertEqual(certificate["global_search_state"], "closed")
        self.assertFalse(certificate["unresolved_scientific_candidates"])
        self.assertEqual(
            certificate["global_outcome"], outcome.GLOBAL_CLOSED_NO_UNRESOLVED
        )

    def test_empty_but_complete_five_window_run_is_closed(self):
        inputs, threshold_sha = _five_windows()
        result = self.assemble(inputs, threshold_sha)
        self.assertEqual(result["records"], [])
        self.assertEqual(result["certificate"]["window_count"], 5)
        self.assertEqual(result["certificate"]["global_search_state"], "closed")

    def test_persisted_rehydration_requires_exact_trusted_digest(self):
        inputs, threshold_sha = _five_windows(
            first_specs=((outcome.UNVETOED_PHYSICAL_DISPOSITION, 0),)
        )
        result = self.assemble(inputs, threshold_sha)
        encoded = outcome.canonical_m37_outcome_bytes(result)
        outcome._OUTCOME_RESULT_ATTESTATIONS.clear()
        outcome._outcome_attestation_bytes = 0
        with self.assertRaises(outcome.M37ValidationError):
            outcome.validate_m37_outcome(result)
        with self.assertRaises(outcome.M37ValidationError):
            outcome.rehydrate_m37_outcome(
                encoded, expected_result_sha256="f" * 64
            )
        restored = outcome.rehydrate_m37_outcome(
            encoded, expected_result_sha256=result["result_sha256"]
        )
        self.assertEqual(restored, result)
        with self.assertRaises(outcome.M37ValidationError):
            outcome.rehydrate_m37_outcome(
                encoded.rstrip() + b"\n\n",
                expected_result_sha256=result["result_sha256"],
            )

    def test_missing_or_reordered_windows_fail_closed(self):
        inputs, threshold_sha = _five_windows()
        with self.assertRaises(outcome.M37ValidationError):
            self.assemble(inputs[:-1], threshold_sha)
        reordered = deepcopy(inputs)
        reordered[0], reordered[1] = reordered[1], reordered[0]
        with self.assertRaises(outcome.M37ValidationError):
            self.assemble(reordered, threshold_sha)

    def test_dropped_significance_id_fails_even_with_all_hashes_resealed(self):
        inputs, threshold_sha = _five_windows(
            first_specs=(
                (outcome.UNVETOED_PHYSICAL_DISPOSITION, 0),
                (outcome.UNVETOED_PHYSICAL_DISPOSITION, 2),
            )
        )
        inputs[0]["significance_result"]["evidence"].pop()
        _reseal_significance(inputs[0])
        with self.assertRaises(outcome.M37ValidationError):
            self.assemble(inputs, threshold_sha)

    def test_duplicate_alias_id_fails_even_with_alias_receipt_resealed(self):
        inputs, threshold_sha = _five_windows(
            first_specs=((outcome.UNVETOED_PHYSICAL_DISPOSITION, 0),)
        )
        inputs[0]["alias_result"]["records"].append(
            deepcopy(inputs[0]["alias_result"]["records"][0])
        )
        _reseal_alias(inputs[0])
        with self.assertRaises(outcome.M37ValidationError):
            self.assemble(inputs, threshold_sha)

    def test_reordered_alias_records_fail_even_with_alias_receipt_resealed(self):
        inputs, threshold_sha = _five_windows(
            first_specs=(
                (outcome.UNVETOED_PHYSICAL_DISPOSITION, 0),
                (outcome.UNVETOED_PHYSICAL_DISPOSITION, 2),
            )
        )
        inputs[0]["alias_result"]["records"].reverse()
        _reseal_alias(inputs[0])
        with self.assertRaises(outcome.M37ValidationError):
            self.assemble(inputs, threshold_sha)

    def test_independent_upstream_receipts_are_mandatory_and_exact(self):
        inputs, threshold_sha = _five_windows()
        mutations = (
            ("expected_alias_certificate_sha256", "b" * 64),
            ("expected_significance_result_sha256", "c" * 64),
            ("expected_retention_certificate_sha256", "d" * 64),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                forged = deepcopy(inputs)
                forged[0][field] = value
                with self.assertRaises(outcome.M37ValidationError):
                    self.assemble(forged, threshold_sha)
        with self.assertRaises(outcome.M37ValidationError):
            self.assemble(inputs, "e" * 64)

    def test_receiver_signature_certificate_receipt_is_required(self):
        inputs, threshold_sha = _five_windows()
        certificate = inputs[0]["alias_result"]["certificate"]
        certificate.pop("receiver_signature_certificate_sha256")
        _reseal_alias(inputs[0])
        with self.assertRaises(outcome.M37ValidationError):
            self.assemble(inputs, threshold_sha)

    def test_alias_identity_comparison_cap_is_rechecked_at_join(self):
        inputs, threshold_sha = _five_windows()
        certificate = inputs[0]["alias_result"]["certificate"]
        certificate["alias_identity_track_comparisons"] = (
            outcome.alias_stage.M37_MAXIMUM_ALIAS_IDENTITY_TRACK_COMPARISONS + 1
        )
        _reseal_alias(inputs[0])
        with self.assertRaises(outcome.M37ValidationError):
            self.assemble(inputs, threshold_sha)

    def test_retained_record_hash_prevents_same_id_cross_product_swap(self):
        inputs, threshold_sha = _five_windows(
            first_specs=((outcome.UNVETOED_PHYSICAL_DISPOSITION, 0),)
        )
        inputs[0]["alias_result"]["records"][0]["snr"] += 1.0
        _reseal_alias(inputs[0])
        with self.assertRaises(outcome.M37ValidationError):
            self.assemble(inputs, threshold_sha)

    def test_resealed_final_disposition_forgery_is_still_rejected(self):
        inputs, threshold_sha = _five_windows(
            first_specs=((outcome.UNVETOED_PHYSICAL_DISPOSITION, 0),)
        )
        result = self.assemble(inputs, threshold_sha)
        forged = deepcopy(result)
        forged["records"][0]["final_disposition"] = (
            outcome.RETAINED_NOT_SCIENTIFICALLY_ELIGIBLE
        )
        forged = _reseal_outcome(forged)
        with self.assertRaises(outcome.M37ValidationError):
            outcome.validate_m37_outcome(
                forged, expected_result_sha256=forged["result_sha256"]
            )

    def test_resealed_numeric_json_strings_are_rejected(self):
        inputs, threshold_sha = _five_windows(
            first_specs=((outcome.UNVETOED_PHYSICAL_DISPOSITION, 0),)
        )
        result = self.assemble(inputs, threshold_sha)
        for field in (
            "retained_snr",
            "inclusive_global_rank_p",
            "scientific_empirical_p_ceiling",
        ):
            with self.subTest(field=field):
                forged = deepcopy(result)
                evidence = forged["records"][0]["global_rank_p_evidence"]
                evidence[field] = str(evidence[field])
                forged = _reseal_outcome(forged)
                with self.assertRaisesRegex(
                    outcome.M37ValidationError,
                    "finite number",
                ):
                    outcome.validate_m37_outcome(
                        forged,
                        expected_result_sha256=forged["result_sha256"],
                    )

    def test_capacity_and_upstream_validator_errors_use_one_fail_closed_type(self):
        inputs, threshold_sha = _five_windows(
            first_specs=((outcome.UNVETOED_PHYSICAL_DISPOSITION, 0),)
        )
        with mock.patch.object(outcome, "M37_MAXIMUM_OUTCOME_RECORDS", 0):
            with self.assertRaises(outcome.M37ValidationError):
                self.assemble(inputs, threshold_sha)
        with mock.patch.object(
            outcome.alias_stage,
            "validate_receiver_alias_result",
            side_effect=core.V0P6ContractError("bad alias"),
        ):
            with self.assertRaises(outcome.M37ValidationError):
                self.assemble(inputs, threshold_sha)


class M37OutcomeRealAliasIntegrationTests(unittest.TestCase):
    def test_empty_five_window_join_uses_real_alias_validator(self):
        inputs, threshold_sha = _five_windows()
        for ordinal, item in enumerate(inputs):
            alias_result = _real_empty_alias_result(
                item["window_id"],
                ordinal,
                item["expected_retention_certificate_sha256"],
            )
            item["alias_result"] = alias_result
            item["expected_alias_certificate_sha256"] = alias_result[
                "certificate"
            ]["receiver_alias_certificate_sha256"]

        result = outcome.assemble_m37_outcome(
            inputs,
            expected_threshold_certificate_sha256=threshold_sha,
        )

        self.assertEqual(result["records"], [])
        self.assertEqual(result["certificate"]["window_count"], 5)
        self.assertEqual(result["certificate"]["global_search_state"], "closed")
        self.assertEqual(outcome.validate_m37_outcome(result), result)


if __name__ == "__main__":
    unittest.main()
