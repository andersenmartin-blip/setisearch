"""Changed-risk tests for the prospective disjoint-window contract."""
import copy
import hashlib
import json
from pathlib import Path
from dataclasses import replace
import unittest

from seti_repeater import calibration_transfer_radio as transfer

ROOT = Path(__file__).resolve().parents[1]


class CrossWindowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design = json.loads((ROOT / "results_radio_motion_2026-09-26" /
                                 "prospective_design.json").read_text())
        cls.contract = transfer.build_contract(cls.design)
        cls.windows = {item.role: item for item in cls.contract.windows}
        cls.source_context = hashlib.sha256(b"calibration-context").hexdigest()
        cls.destination_context = hashlib.sha256(b"validation-context").hexdigest()
        cls.certificate = transfer.ExactContextCertificate(
            cls.windows["calibration"].identity, cls.source_context,
            hashlib.sha256(b"receipt").hexdigest(), "synthetic")

    def test_three_ordered_disjoint_window_identities_are_bound(self):
        self.assertEqual(tuple(self.windows), transfer.ROLES)
        self.assertEqual({x.archive_chunk_index for x in self.contract.windows},
                         {150, 151, 152})
        self.assertEqual(sum(len(x.payload_keys) for x in self.contract.windows), 18)
        self.assertEqual(self.contract.record()["normalization_blocks_native_channels"],
                         [list(x) for x in transfer.BLOCKS])

    def test_contract_is_deterministic_and_detects_identity_tamper(self):
        again = transfer.build_contract(copy.deepcopy(self.design))
        self.assertEqual(again.identity, self.contract.identity)
        with self.assertRaisesRegex(ValueError, "contract changed"):
            replace(self.contract, grid_sha256="0" * 64).validate()

    def test_payload_coordinate_crossing_is_refused(self):
        changed = copy.deepcopy(self.design)
        changed["windows"][1]["payload_keys"][0][
            "chunk_coordinates_time_feed_frequency"][0][2] = 150
        with self.assertRaisesRegex(ValueError, "payload identity changed"):
            transfer.build_contract(changed)

    def test_exact_context_certificate_cannot_be_reused(self):
        self.certificate.validate_for_exact_context(
            self.windows["calibration"].identity, self.source_context)
        with self.assertRaisesRegex(ValueError, "reuse refused"):
            self.certificate.validate_for_exact_context(
                self.windows["validation"].identity, self.destination_context)

    def test_distinct_transfer_request_is_bound_but_never_authorized(self):
        request = transfer.prepare_transfer_request(
            self.contract, self.certificate, source_role="calibration",
            destination_role="validation", source_context_sha256=self.source_context,
            destination_context_sha256=self.destination_context)
        self.assertNotEqual(request["source_window_sha256"],
                            request["destination_window_sha256"])
        self.assertFalse(request["threshold_transfer_authorized"])
        self.assertIn("cross_window_numeric_transfer_not_qualified", request["blockers"])
        self.assertEqual(len(request["blockers"]), 8)

    def test_same_context_and_pilot_shortcut_are_refused(self):
        with self.assertRaisesRegex(ValueError, "contexts must be distinct"):
            transfer.prepare_transfer_request(
                self.contract, self.certificate, source_role="calibration",
                destination_role="validation", source_context_sha256=self.source_context,
                destination_context_sha256=self.source_context)
        with self.assertRaisesRegex(ValueError, "calibration-to-validation"):
            transfer.prepare_transfer_request(
                self.contract, self.certificate, source_role="calibration",
                destination_role="pilot", source_context_sha256=self.source_context,
                destination_context_sha256=self.destination_context)

    def test_missing_evidence_slots_remain_explicit(self):
        self.assertEqual(len(self.contract.required_evidence), 6)
        self.assertTrue(all(value is None for value in
                            self.contract.required_evidence.values()))
        self.assertEqual(self.contract.record()["status"],
                         "IDENTITIES_FROZEN_TRANSFER_NOT_QUALIFIED")

    def test_contract_has_no_telescope_or_candidate_authority(self):
        record = self.contract.record()
        self.assertFalse(record["spectral_access_authorized"])
        self.assertFalse(record["telescope_values_opened"])
        self.assertFalse(record["scientific_candidate_selection_authorized"])
        self.assertFalse(record["roles_are_independent_observations"])


if __name__ == "__main__":
    unittest.main()
