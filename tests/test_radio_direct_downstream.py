"""New risks introduced by the direct-table downstream contract."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import unittest

from seti_repeater import pipeline_direct_radio as pipeline
from seti_repeater import search_v0p6 as core
from seti_repeater import transfer_m43g as native
from radio_direct_downstream_fixture import panel, setup


class DirectDownstreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = panel()

    def test_contract_is_literal_direct_table_not_factor_basis(self):
        contract = self.p["context"].factor_contract
        self.assertNotIsInstance(contract, core.FactorBasis)
        self.assertEqual(contract.record()["factor_provider_kind"],
                         "literal-midpoint-table-not-factor-basis")
        self.assertFalse(contract.record()["old_factor_basis_constructed"])
        self.assertEqual(contract.factors.template_count, 33)

    def test_contract_rejects_tampering_and_scan_reordering(self):
        contract = self.p["context"].factor_contract
        bad = replace(contract, factor_table_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "contract changed"):
            bad.validate()
        cfg, context, _ = setup(); scans = list(reversed(context.scans))
        with self.assertRaises(core.V0P6ContractError):
            pipeline.Context(scans=scans, factors=contract.factors, grid=context.grid,
                             window="bad-order")

    def test_sources_must_bind_scan_and_direct_bank_before_scoring(self):
        context = self.p["context"]
        sources = dict(self.p["calibration_run"].sources)
        original = sources["epoch1_on"]
        scope = json.loads(original.scope_json); scope["direct_factor_bank_sha256"] = "0" * 64
        sources["epoch1_on"] = replace(original, scope_json=core.canonical_json_bytes(scope).decode())
        with self.assertRaisesRegex(ValueError, "identity or payload mismatch|does not belong"):
            pipeline.NativeRun(context, sources)

    def test_calibration_is_bound_to_exact_direct_context(self):
        p = self.p; changed = copy.copy(p["context"])
        changed.window = "another-window"
        with self.assertRaisesRegex(ValueError, "context changed"):
            p["calibration"].validate(changed)
        self.assertFalse(p["calibration"].receipt["cross_window_transfer_qualified"])
        self.assertEqual(p["calibration"].receipt["direct_factor_contract_sha256"],
                         p["context"].factor_contract.identity)

    def test_all_cases_complete_and_partition_every_retained_on_member(self):
        for name, report in self.p["reports"].items():
            retained = {r["record_id"] for r in report["detector"]["retained"]["on"]}
            clustered = [rid for group in report["clusters"] for rid in group["member_ids"]]
            self.assertEqual(set(clustered), retained, name)
            self.assertEqual(len(clustered), len(retained), name)
            self.assertEqual(retained, {d["record_id"] for d in report["detector"]["decisions"]})
            self.assertTrue(report["complete"])
            self.assertFalse(report["scientific_candidate_selection_authorized"])

    def test_signal_and_interference_paths_reach_final_stages(self):
        outcomes = self.p["outcomes"]
        self.assertTrue(outcomes["finite_exposure_signal"]["recovered"])
        self.assertEqual(outcomes["finite_exposure_signal"]["all_final_member_count"], 2246)
        self.assertEqual(outcomes["noise"]["all_final_member_count"], 0)
        self.assertEqual(outcomes["matched_on_off"]["all_final_member_count"], 13)
        self.assertEqual(outcomes["single_paired_off"]["all_final_member_count"], 0)
        matched = {d["physical_disposition"]
                   for d in self.p["reports"]["matched_on_off"]["detector"]["decisions"]}
        adjacent = {d["physical_disposition"]
                    for d in self.p["reports"]["single_paired_off"]["detector"]["decisions"]}
        self.assertIn("rfi_veto_matched_off_same_hypothesis", matched)
        self.assertIn("rfi_veto_single_adjacent_off", adjacent)

    def test_certificates_explicitly_bind_direct_provider_identities(self):
        p = self.p; factor = p["context"].factor_contract
        result = p["reports"]["finite_exposure_signal"]["detector"]
        cert = result["retention_certificates"]["on"]
        self.assertEqual(cert["factor_basis_sha256"], factor.factors.identity)
        self.assertEqual(cert["factor_basis_labels_sha256"], factor.labels_sha256)
        self.assertEqual(result["legacy_certificate_slot_mapping"],
                         factor.record()["legacy_certificate_slot_mapping"])
        self.assertEqual(result["adjacent_off"]["certificate"]["off_factor_row_selection_sha256"],
                         factor.row_selection_sha256("off"))

    def test_no_telescope_entry_point_or_hidden_candidate_authority(self):
        self.assertFalse(hasattr(pipeline.NativeRun, "from_telescope"))
        for report in self.p["reports"].values():
            self.assertTrue(all(not d["scientific_candidate"]
                                for d in report["detector"]["decisions"]))
            self.assertFalse(report["score_provenance"]["telescope_values_opened"])


if __name__ == "__main__":
    unittest.main()
