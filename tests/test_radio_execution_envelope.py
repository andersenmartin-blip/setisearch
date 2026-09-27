"""Changed-risk tests for the blocked HD 1461 execution envelope."""
import copy
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from seti_repeater import acquisition_radio as acquisition
from seti_repeater import execution_envelope_radio as envelope
from radio_execution_envelope import build

ROOT = Path(__file__).resolve().parents[1]


class ExecutionEnvelopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (cls.cfg, cls.runtime, cls.codec, cls.motion, cls.resource,
         cls.genesis, cls.envelope) = build()

    def test_runtime_and_existing_evidence_are_hash_bound(self):
        record = self.envelope.record()
        self.assertEqual(record["runtime_manifest_sha256"],
                         envelope.digest(self.runtime))
        self.assertEqual(record["codec_evidence_sha256"],
                         envelope.digest(self.codec))
        self.assertTrue(self.codec["local_codec_receipt_path_passed"])
        self.assertFalse(self.codec["telescope_codec_receipt_handoff_passed"])

    def test_all_published_input_evidence_has_independent_pins(self):
        self.assertEqual(set(self.cfg["input_evidence"]),
                         set(self.cfg["expected_input_sha256"]))
        for name, relative in self.cfg["input_evidence"].items():
            import hashlib
            observed = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(observed, self.cfg["expected_input_sha256"][name])

    def test_new_resource_namespace_is_empty_and_not_a_ledger_reset(self):
        record = self.resource.record()
        self.assertEqual(record["status"], "FROZEN_NOT_ACTIVATED")
        self.assertEqual(record["reservations"], 0)
        self.assertEqual(record["prior_synthetic_demonstration"]["status"],
                         "CLOSED_EXHAUSTED_NOT_PARENT_NOT_RESET")
        audit = envelope.validate_resource_ledger(
            self.genesis, envelope.ledger_digest(self.genesis))
        self.assertEqual(audit["sessions"], 0)
        self.assertEqual(audit["remaining_limits"], envelope.TOTAL_LIMITS)

    def test_v1_session_validator_cannot_represent_three_session_total(self):
        with self.assertRaisesRegex(ValueError, "session budget"):
            acquisition.genesis(self.resource.identity,
                                self.resource.source_inventory_sha256,
                                envelope.TOTAL_LIMITS)

    def test_three_role_reservations_exhaust_caps_and_fourth_is_refused(self):
        ledger = copy.deepcopy(self.genesis)
        for ordinal, role in enumerate(envelope.EXPECTED_ROLES):
            reservation = {"ordinal": ordinal,
                "role": role,
                "session_id": f"00000000-0000-4000-8000-{ordinal+1:012d}",
                "prior_ledger_sha256": envelope.ledger_digest(ledger),
                "reserved_limits": envelope.SESSION_LIMITS,
                "created_utc": f"2026-09-27T0{ordinal}:00:00+00:00"}
            ledger["reservations"].append(reservation)
        audit = envelope.validate_resource_ledger(
            ledger, envelope.ledger_digest(ledger))
        self.assertEqual(audit["sessions"], 3)
        self.assertEqual(audit["remaining_limits"],
                         {"max_requests": 0, "max_bytes": 0, "max_seconds": 0})
        extra = copy.deepcopy(ledger)
        extra["reservations"].append({"ordinal": 3,
            "role": "forbidden-fourth-role",
            "session_id": "00000000-0000-4000-8000-000000000004",
            "prior_ledger_sha256": envelope.ledger_digest(extra),
            "reserved_limits": envelope.SESSION_LIMITS,
            "created_utc": datetime.now(timezone.utc).isoformat()})
        with self.assertRaisesRegex(ValueError, "role, order"):
            envelope.validate_resource_ledger(extra, envelope.ledger_digest(extra))

    def test_attempt_budget_forbids_post_freeze_remedy_and_early_pilot(self):
        attempts = self.resource.record()["scientific_attempt_limits"]
        self.assertEqual(attempts["evaluation_runs"], 1)
        self.assertEqual(attempts["post_freeze_remedy_attempts"], 0)
        self.assertEqual(attempts["pilot_runs_before_all_gates_pass"], 0)

    def test_local_durable_controller_reserves_only_next_role(self):
        with tempfile.TemporaryDirectory() as td:
            store = envelope.LocalRoleStore.initialize(
                Path(td) / "ledger.json", self.genesis)
            before = store.read(); before_sha = envelope.ledger_digest(before.document)
            with self.assertRaisesRegex(ValueError, "role out of order"):
                envelope.reserve_role(store, expected_revision=before.revision,
                    expected_ledger_sha256=before_sha, role="validation",
                    session_id="00000000-0000-4000-8000-000000000011",
                    created_utc="2026-09-27T06:00:00+00:00")
            receipt = envelope.reserve_role(store,
                expected_revision=before.revision,
                expected_ledger_sha256=before_sha, role="calibration",
                session_id="00000000-0000-4000-8000-000000000012",
                created_utc="2026-09-27T06:01:00+00:00")
            self.assertEqual(receipt["revision"], "1")
            self.assertFalse(receipt["network_budget_issued"])
            self.assertEqual(store.read().document["reservations"][0]["role"],
                             "calibration")

    def test_local_controller_rejects_stale_checkpoint_without_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            store = envelope.LocalRoleStore.initialize(
                Path(td) / "ledger.json", self.genesis)
            before = store.read(); before_sha = envelope.ledger_digest(before.document)
            envelope.reserve_role(store, expected_revision="0",
                expected_ledger_sha256=before_sha, role="calibration",
                session_id="00000000-0000-4000-8000-000000000021",
                created_utc="2026-09-27T06:02:00+00:00")
            with self.assertRaisesRegex(ValueError, "checkpoint changed"):
                envelope.reserve_role(store, expected_revision="0",
                    expected_ledger_sha256=before_sha, role="calibration",
                    session_id="00000000-0000-4000-8000-000000000022",
                    created_utc="2026-09-27T06:03:00+00:00")
            self.assertEqual(len(store.read().document["reservations"]), 1)

    def test_publication_ambiguity_remains_spent_and_cannot_retry_old_parent(self):
        class AmbiguousStore:
            def __init__(self, real): self.real = real
            def read(self): return self.real.read()
            def publish(self, *args):
                self.real.publish(*args)
                raise RuntimeError("simulated lost publication reply")
        with tempfile.TemporaryDirectory() as td:
            real = envelope.LocalRoleStore.initialize(
                Path(td) / "ledger.json", self.genesis)
            before = real.read(); before_sha = envelope.ledger_digest(before.document)
            with self.assertRaisesRegex(RuntimeError, "lost publication reply"):
                envelope.reserve_role(AmbiguousStore(real),
                    expected_revision="0", expected_ledger_sha256=before_sha,
                    role="calibration",
                    session_id="00000000-0000-4000-8000-000000000031",
                    created_utc="2026-09-27T06:04:00+00:00")
            self.assertEqual(len(real.read().document["reservations"]), 1)
            with self.assertRaisesRegex(ValueError, "checkpoint changed"):
                envelope.reserve_role(real, expected_revision="0",
                    expected_ledger_sha256=before_sha, role="calibration",
                    session_id="00000000-0000-4000-8000-000000000032",
                    created_utc="2026-09-27T06:05:00+00:00")

    def test_envelope_retains_exact_five_blockers(self):
        self.assertEqual(self.envelope.record()["blockers"], [
            "pointing_provenance", "telescope_codec_receipt_handoff",
            "physical_motion_bank", "cross_window_numeric_transfer",
            "recovery_rfi_null_evaluation"])
        self.assertEqual(self.envelope.record()["status"], "BLOCKED")

    def test_arithmetic_is_not_relabelled_physical_motion(self):
        self.assertTrue(self.motion["arithmetic_qualified"])
        self.assertFalse(self.motion["physical_model_qualified"])
        self.assertFalse(self.motion["source_pointing_resolved"])

    def test_gate_or_identity_tampering_is_refused(self):
        evidence = self.envelope.evidence
        evidence["gates"]["pointing_provenance"]["passed"] = True
        changed = replace(self.envelope,
                          evidence_json=envelope.canonical(evidence))
        with self.assertRaisesRegex(ValueError, "claims changed"):
            changed.validate()
        with self.assertRaisesRegex(ValueError, "envelope changed"):
            replace(self.envelope, identity="0" * 64).validate()

    def test_no_spectral_or_candidate_authority(self):
        record = self.envelope.record()
        self.assertFalse(record["spectral_access_authorized"])
        self.assertFalse(record["scientific_candidate_selection_authorized"])
        self.assertFalse(record["telescope_values_opened"])
        self.assertEqual(record["telescope_requests"], 0)


if __name__ == "__main__":
    unittest.main()
