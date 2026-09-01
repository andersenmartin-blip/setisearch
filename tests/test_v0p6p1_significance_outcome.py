"""Capacity-bound regression tests for M37 v0.6.1 adjudication."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest import mock

from seti_repeater import capacity_v0p6p1 as capacity
from seti_repeater import outcome_v0p6 as outcome_v0p6
from seti_repeater import outcome_v0p6p1 as outcome
from seti_repeater import significance_v0p6p1 as significance
from tests import test_v0p6_outcome as fixtures


ROOT = Path(__file__).resolve().parents[1]


def _amended_empty_inputs():
    inputs, threshold_sha256 = fixtures._five_windows()
    for item in inputs:
        alias_certificate = item["alias_result"]["certificate"]
        alias_certificate["maximum_records"] = (
            capacity.M37_V0P6P1_MAXIMUM_RECORDS_PER_WINDOW
        )
        alias_certificate["maximum_bucket_entries"] = (
            capacity.M37_V0P6P1_MAXIMUM_ALIAS_BUCKET_ENTRIES
        )
        alias_certificate["maximum_distinct_candidate_visits_per_window"] = (
            capacity.M37_V0P6P1_MAXIMUM_ALIAS_DISTINCT_CANDIDATE_VISITS
        )
        alias_certificate["maximum_alias_identity_track_comparisons"] = (
            capacity.M37_V0P6P1_MAXIMUM_ALIAS_IDENTITY_TRACK_COMPARISONS
        )
        fixtures._reseal_alias(item)
        significance_certificate = item["significance_result"]["certificate"]
        significance_certificate["maximum_evidence_canonical_bytes"] = (
            capacity.M37_V0P6P1_MAXIMUM_EVIDENCE_CANONICAL_BYTES
        )
        fixtures._reseal_significance(item)
    return inputs, threshold_sha256


class M37V0P6P1SignificanceOutcomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = capacity.open_m37_v0p6p1_capacity_amendment(
            ROOT / "config/hd156668b_m37_v0p6p1_capacity_amendment.json"
        )

    def test_old_outcome_entry_point_rejects_amended_capacity(self):
        inputs, threshold_sha256 = _amended_empty_inputs()
        with mock.patch.object(
            outcome_v0p6.alias_stage,
            "validate_receiver_alias_result",
            side_effect=fixtures._stub_alias_validator,
        ):
            with self.assertRaises(outcome_v0p6.M37ValidationError):
                outcome_v0p6.assemble_m37_outcome(
                    inputs,
                    expected_threshold_certificate_sha256=threshold_sha256,
                )

    def test_amended_outcome_is_closed_and_persistently_reopenable(self):
        inputs, threshold_sha256 = _amended_empty_inputs()
        with mock.patch.object(
            outcome_v0p6.alias_stage,
            "validate_receiver_alias_result",
            side_effect=fixtures._stub_alias_validator,
        ):
            result = outcome.assemble_m37_v0p6p1_outcome(
                self.profile,
                inputs,
                expected_threshold_certificate_sha256=threshold_sha256,
            )
            certificate = result["certificate"]
            self.assertEqual(
                certificate["maximum_records_per_window"], 50_000
            )
            self.assertEqual(
                certificate["maximum_outcome_records"], 250_000
            )
            self.assertEqual(
                certificate["maximum_outcome_canonical_bytes"],
                2_400_000_000,
            )
            self.assertEqual(certificate["global_search_state"], "closed")
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "outcome.json"
                receipt = outcome.publish_m37_v0p6p1_outcome_artifact(
                    path,
                    result,
                    self.profile,
                    expected_result_sha256=result["result_sha256"],
                )
                reopened = outcome.open_m37_v0p6p1_outcome_artifact(
                    path,
                    self.profile,
                    expected_file_sha256=receipt.file_sha256,
                    expected_result_sha256=receipt.result_sha256,
                )
            self.assertEqual(reopened.result, result)

    def test_artifact_caps_are_separate_from_v0p6(self):
        self.assertEqual(
            significance.M37_V0P6P1_SIGNIFICANCE_ARTIFACT_MAXIMUM_BYTES,
            496_777_216,
        )
        self.assertEqual(
            outcome.M37_V0P6P1_OUTCOME_ARTIFACT_MAXIMUM_BYTES,
            2_416_777_216,
        )
        self.assertEqual(outcome_v0p6.M37_MAXIMUM_OUTCOME_RECORDS, 50_000)


if __name__ == "__main__":
    unittest.main()
