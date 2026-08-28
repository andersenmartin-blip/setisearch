"""Known-answer tests for detector-v0.6 global rank-p evidence."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import math
import unittest

import numpy as np

import seti_repeater.search_v0p6 as core
import seti_repeater.significance_v0p6 as significance
from seti_repeater.significance_v0p6 import (
    INCLUSIVE_NULL_COMPARISON,
    evaluate_global_rank_significance,
    evaluate_m37_global_rank_significance,
    validate_global_rank_significance,
)


def _make_product(
    *,
    null_maxima=(1.0, 2.0, 3.0, 4.0),
    retained_scores=(2.0, 4.0),
    scientific_p_ceiling=0.4,
    window_id="synthetic",
):
    grid = core.make_proxy_carrier_grid(0.0001, 1.0, 5, 1)
    bank = [core.make_line_template_bank()[0]]
    bank_sha256 = core.template_bank_sha256(bank)
    null_maxima = np.asarray(null_maxima, dtype=np.float64)
    shifts = core.make_scramble_shift_table(
        len(null_maxima),
        3,
        grid.score_bin_count,
        seed=37_062_121,
        minimum_shift_bins=1,
    )
    calibration = core.CalibrationAccumulator.create(
        window_id=window_id,
        score_bin_count=grid.score_bin_count,
        template_count=1,
        template_bank_sha256_value=bank_sha256,
        factor_basis_sha256_value="1" * 64,
        factor_basis_labels_sha256_value="2" * 64,
        scan_inventory_sha256_value="3" * 64,
        factor_row_selection_sha256_value="4" * 64,
        factor_table_sha256_value="5" * 64,
        spectral_widths=(1,),
        activity_subsets=((0, 1),),
        minimum_active_epoch_snr=None,
        stack_statistic="sum",
        scramble_shifts=shifts,
        minimum_shift_bins=1,
        expected_scramble_sha256=core.scramble_table_sha256(shifts),
    )
    core.update_calibration(
        calibration,
        np.zeros((3, grid.score_bin_count), dtype=np.float32),
        template_index=0,
        width_index=0,
        exclusion_mask=None,
    )
    # The fixture isolates rank-p behavior by supplying a deterministic sealed
    # null vector after exercising the complete calibration inventory.
    calibration.null_maxima[:] = null_maxima
    calibration._checkpoint_state()
    calibration.finalize()
    threshold = core.calibrated_threshold(
        (calibration,),
        expected_window_ids=(window_id,),
        reference_floor=float(np.min(null_maxima)),
        quantile=0.0,
        scientific_p_ceiling=scientific_p_ceiling,
    )
    ledger = core.ExhaustiveRetentionLedger(
        window_id=window_id,
        scan_kind="on",
        grid=grid,
        threshold_certificate=threshold,
        maximum_records=100,
        template_bank=bank,
        spectral_widths=(1,),
        activity_subsets=((0, 1),),
        expected_template_bank_sha256=None,
        factor_basis_sha256="1" * 64,
        factor_basis_labels_sha256="2" * 64,
        scan_inventory_sha256="3" * 64,
        factor_row_selection_sha256="4" * 64,
        factor_table_sha256="5" * 64,
        epoch_count=3,
        minimum_active_epoch_snr=None,
        stack_statistic="sum",
    )
    vectors = np.full((3, grid.score_bin_count), -100.0, dtype=np.float32)
    for index, score in enumerate(retained_scores, start=1):
        vectors[0:2, index] = np.float32(
            float(score) / np.float32(math.sqrt(2.0))
        )
    ledger.add_hypothesis(
        vectors,
        (0, 1),
        template=bank[0],
        width_index=0,
        width_channels=1,
        exclusion_mask=None,
    )
    records = ledger.finalize()
    certificate = ledger.certificate()
    return {
        "grid": grid,
        "bank": bank,
        "null_maxima": calibration.null_maxima.copy(),
        "threshold": threshold,
        "records": records,
        "certificate": certificate,
    }


def _reseal_result(result, *, reset_counts=False):
    """Recompute every public hash after an intentional test mutation."""
    forged = deepcopy(result)
    for item in forged["evidence"]:
        payload = dict(item)
        payload.pop("evidence_sha256", None)
        item["evidence_sha256"] = hashlib.sha256(
            core.canonical_json_bytes(payload)
        ).hexdigest()
    certificate = forged["certificate"]
    if reset_counts:
        certificate["input_record_count"] = len(forged["evidence"])
        certificate["evidence_record_count"] = len(forged["evidence"])
    identifiers = [item["record_id"] for item in forged["evidence"]]
    hashes = [item["evidence_sha256"] for item in forged["evidence"]]
    evidence_bytes = core.canonical_json_bytes(forged["evidence"])
    certificate["record_ids_sha256"] = hashlib.sha256(
        core.canonical_json_bytes(identifiers)
    ).hexdigest()
    certificate["evidence_item_sha256s_sha256"] = hashlib.sha256(
        core.canonical_json_bytes(hashes)
    ).hexdigest()
    certificate["evidence_sha256"] = hashlib.sha256(evidence_bytes).hexdigest()
    certificate["evidence_canonical_bytes"] = len(evidence_bytes)
    certificate_payload = dict(certificate)
    certificate_payload.pop("significance_certificate_sha256", None)
    certificate["significance_certificate_sha256"] = hashlib.sha256(
        core.canonical_json_bytes(certificate_payload)
    ).hexdigest()
    result_payload = {
        "evidence": forged["evidence"],
        "certificate": certificate,
    }
    forged["result_sha256"] = hashlib.sha256(
        core.canonical_json_bytes(result_payload)
    ).hexdigest()
    return forged


class GlobalRankSignificanceTests(unittest.TestCase):
    def _evaluate(self, fixture, records=None):
        return evaluate_global_rank_significance(
            fixture["records"] if records is None else records,
            fixture["certificate"],
            fixture["threshold"],
            fixture["null_maxima"],
            fixture["grid"],
            fixture["bank"],
        )

    def _validate(self, result, fixture, **kwargs):
        return validate_global_rank_significance(
            result,
            fixture["records"],
            fixture["certificate"],
            fixture["threshold"],
            fixture["null_maxima"],
            fixture["grid"],
            fixture["bank"],
            **kwargs,
        )

    def test_inclusive_equality_counts_every_tied_null(self):
        fixture = _make_product(
            null_maxima=(1.0, 2.0, 2.0, 4.0),
            retained_scores=(2.0,),
            scientific_p_ceiling=0.8,
        )
        original_records = deepcopy(fixture["records"])
        result = self._evaluate(fixture)
        item = result["evidence"][0]
        self.assertEqual(item["inclusive_null_comparison"], INCLUSIVE_NULL_COMPARISON)
        self.assertEqual(item["inclusive_null_exceedance_count"], 3)
        self.assertEqual(item["inclusive_global_rank_p"], 4.0 / 5.0)
        self.assertTrue(item["scientifically_eligible"])
        self.assertEqual(fixture["records"], original_records)
        self.assertEqual(self._validate(result, fixture), result)

    def test_rank_p_just_below_and_above_ceiling(self):
        fixture = _make_product(
            null_maxima=(0.0, 0.5, 1.0, 1.5, 1.7, 1.9, 2.0, 8.0, 9.0),
            retained_scores=(8.0, 2.0),
            scientific_p_ceiling=0.35,
        )
        result = self._evaluate(fixture)
        by_score = {
            item["retained_snr"]: item for item in result["evidence"]
        }
        self.assertEqual(by_score[8.0]["inclusive_global_rank_p"], 0.3)
        self.assertTrue(by_score[8.0]["scientifically_eligible"])
        self.assertEqual(by_score[2.0]["inclusive_global_rank_p"], 0.4)
        self.assertFalse(by_score[2.0]["scientifically_eligible"])

    def test_p_equal_to_ceiling_is_scientifically_eligible(self):
        fixture = _make_product(
            null_maxima=(1.0, 2.0, 3.0, 4.0),
            retained_scores=(4.0,),
            scientific_p_ceiling=0.4,
        )
        item = self._evaluate(fixture)["evidence"][0]
        self.assertEqual(item["inclusive_global_rank_p"], 0.4)
        self.assertTrue(item["scientifically_eligible"])

    def test_output_is_order_invariant_and_sorted_by_raw_record_id(self):
        fixture = _make_product(retained_scores=(2.0, 3.0, 4.0))
        forward = self._evaluate(fixture)
        reverse_records = list(reversed(deepcopy(fixture["records"])))
        reverse = self._evaluate(fixture, records=reverse_records)
        self.assertEqual(forward, reverse)
        identifiers = [item["record_id"] for item in forward["evidence"]]
        self.assertEqual(identifiers, sorted(identifiers))
        self.assertEqual(len(identifiers), len(set(identifiers)))

    def test_mutation_with_all_public_hashes_recomputed_is_rejected(self):
        fixture = _make_product()
        result = self._evaluate(fixture)
        forged = deepcopy(result)
        forged["evidence"][0]["retained_snr"] += 0.25
        forged = _reseal_result(forged)
        with self.assertRaisesRegex(core.V0P6ContractError, "attestation"):
            self._validate(forged, fixture)
        with self.assertRaisesRegex(core.V0P6IncompleteError, "reproduce"):
            self._validate(
                forged,
                fixture,
                expected_result_sha256=forged["result_sha256"],
            )

    def test_resealed_numeric_json_type_changes_are_rejected_at_schema_gate(self):
        fixture = _make_product()
        result = self._evaluate(fixture)
        mutations = (
            (
                "evidence numeric string",
                lambda forged: forged["evidence"][0].__setitem__(
                    "retained_snr",
                    str(forged["evidence"][0]["retained_snr"]),
                ),
            ),
            (
                "evidence boolean schema version",
                lambda forged: forged["evidence"][0].__setitem__(
                    "schema_version", True
                ),
            ),
            (
                "certificate numeric string",
                lambda forged: forged["certificate"].__setitem__(
                    "operational_threshold_snr",
                    str(forged["certificate"]["operational_threshold_snr"]),
                ),
            ),
            (
                "certificate boolean schema version",
                lambda forged: forged["certificate"].__setitem__(
                    "schema_version", True
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                forged = deepcopy(result)
                mutate(forged)
                forged = _reseal_result(forged)
                with self.assertRaises(core.V0P6ContractError):
                    self._validate(
                        forged,
                        fixture,
                        expected_result_sha256=forged["result_sha256"],
                    )

    def test_rehashed_threshold_dataclass_mutation_is_rejected(self):
        fixture = _make_product()
        threshold = replace(
            fixture["threshold"],
            scientific_empirical_p_ceiling=0.9,
            certificate_sha256="",
        )
        payload = threshold.as_record()
        payload.pop("certificate_sha256")
        threshold = replace(
            threshold,
            certificate_sha256=hashlib.sha256(
                core.canonical_json_bytes(payload)
            ).hexdigest(),
        )
        with self.assertRaises(core.V0P6ContractError):
            evaluate_global_rank_significance(
                fixture["records"],
                fixture["certificate"],
                threshold,
                fixture["null_maxima"],
                fixture["grid"],
                fixture["bank"],
            )

    def test_wrong_null_hash_count_finiteness_and_dtype_fail_closed(self):
        fixture = _make_product()
        changed = fixture["null_maxima"].copy()
        changed[0] += 0.5
        with self.assertRaisesRegex(core.V0P6IncompleteError, "SHA-256"):
            evaluate_global_rank_significance(
                fixture["records"],
                fixture["certificate"],
                fixture["threshold"],
                changed,
                fixture["grid"],
                fixture["bank"],
            )
        with self.assertRaisesRegex(core.V0P6IncompleteError, "shape/count"):
            evaluate_global_rank_significance(
                fixture["records"],
                fixture["certificate"],
                fixture["threshold"],
                fixture["null_maxima"][:-1],
                fixture["grid"],
                fixture["bank"],
            )
        nonfinite = fixture["null_maxima"].copy()
        nonfinite[0] = np.nan
        with self.assertRaisesRegex(core.V0P6ContractError, "finite"):
            evaluate_global_rank_significance(
                fixture["records"],
                fixture["certificate"],
                fixture["threshold"],
                nonfinite,
                fixture["grid"],
                fixture["bank"],
            )
        with self.assertRaisesRegex(core.V0P6ContractError, "float vector"):
            evaluate_global_rank_significance(
                fixture["records"],
                fixture["certificate"],
                fixture["threshold"],
                np.arange(4),
                fixture["grid"],
                fixture["bank"],
            )

    def test_missing_and_duplicate_evidence_are_rejected_even_if_resealed(self):
        fixture = _make_product(retained_scores=(2.0, 3.0, 4.0))
        result = self._evaluate(fixture)

        missing = deepcopy(result)
        missing["evidence"].pop()
        missing = _reseal_result(missing, reset_counts=True)
        with self.assertRaisesRegex(core.V0P6IncompleteError, "cover every"):
            self._validate(
                missing,
                fixture,
                expected_result_sha256=missing["result_sha256"],
            )

        duplicated = deepcopy(result)
        duplicated["evidence"][1] = deepcopy(duplicated["evidence"][0])
        duplicated = _reseal_result(duplicated)
        with self.assertRaisesRegex(core.V0P6IncompleteError, "duplicated"):
            self._validate(
                duplicated,
                fixture,
                expected_result_sha256=duplicated["result_sha256"],
            )

    def test_cross_process_trusted_retention_threshold_and_result_digests(self):
        fixture = _make_product()
        retention_digest = fixture["certificate"][
            "retention_certificate_sha256"
        ]
        threshold_digest = fixture["threshold"].certificate_sha256
        retention_attestation = core._RETENTION_CERTIFICATE_ATTESTATIONS.pop(
            retention_digest
        )
        threshold_attestation = core._THRESHOLD_CERTIFICATE_REGISTRY.pop(
            id(fixture["threshold"]._receipt)
        )
        result = None
        result_attestation = None
        try:
            with self.assertRaises(core.V0P6ContractError):
                self._evaluate(fixture)
            result = evaluate_global_rank_significance(
                fixture["records"],
                fixture["certificate"],
                fixture["threshold"],
                fixture["null_maxima"],
                fixture["grid"],
                fixture["bank"],
                expected_on_certificate_sha256=retention_digest,
                expected_threshold_certificate_sha256=threshold_digest,
            )
            result_attestation = (
                significance._SIGNIFICANCE_RESULT_ATTESTATIONS.pop(
                    result["result_sha256"]
                )
            )
            validated = validate_global_rank_significance(
                result,
                fixture["records"],
                fixture["certificate"],
                fixture["threshold"],
                fixture["null_maxima"],
                fixture["grid"],
                fixture["bank"],
                expected_on_certificate_sha256=retention_digest,
                expected_threshold_certificate_sha256=threshold_digest,
                expected_result_sha256=result["result_sha256"],
            )
            self.assertEqual(validated, result)
        finally:
            core._RETENTION_CERTIFICATE_ATTESTATIONS[
                retention_digest
            ] = retention_attestation
            core._THRESHOLD_CERTIFICATE_REGISTRY[
                id(fixture["threshold"]._receipt)
            ] = threshold_attestation
            if result is not None and result_attestation is not None:
                significance._SIGNIFICANCE_RESULT_ATTESTATIONS[
                    result["result_sha256"]
                ] = result_attestation

    def test_grid_bank_and_template_count_are_reconstructed(self):
        fixture = _make_product()
        wrong_grid = core.make_proxy_carrier_grid(0.000101, 1.0, 5, 1)
        with self.assertRaises(core.V0P6ContractError):
            evaluate_global_rank_significance(
                fixture["records"],
                fixture["certificate"],
                fixture["threshold"],
                fixture["null_maxima"],
                wrong_grid,
                fixture["bank"],
            )
        wrong_bank = core.make_line_template_bank(
            count=3, expected_sha256=None
        )
        with self.assertRaises(core.V0P6ContractError):
            evaluate_global_rank_significance(
                fixture["records"],
                fixture["certificate"],
                fixture["threshold"],
                fixture["null_maxima"],
                fixture["grid"],
                wrong_bank,
            )

    def test_m37_wrapper_rejects_synthetic_window_and_dimensions(self):
        fixture = _make_product()
        with self.assertRaisesRegex(core.V0P6ContractError, "M37"):
            evaluate_m37_global_rank_significance(
                fixture["records"],
                fixture["certificate"],
                fixture["threshold"],
                fixture["null_maxima"],
                fixture["grid"],
            )

        m37_named = _make_product(window_id=core.M37_WINDOW_IDS[0])
        with self.assertRaisesRegex(core.V0P6ContractError, "exact window q grid"):
            evaluate_m37_global_rank_significance(
                m37_named["records"],
                m37_named["certificate"],
                m37_named["threshold"],
                m37_named["null_maxima"],
                m37_named["grid"],
            )


if __name__ == "__main__":
    unittest.main()
