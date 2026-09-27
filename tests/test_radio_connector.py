"""Tests of changed typed-envelope/admission integration only."""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
import uuid

from seti_repeater import connector_rehearsal_radio as c
from seti_repeater import rehearsal_contract_radio as r
from seti_repeater import execution_envelope_radio as env
from seti_repeater.github_role_radio import PublicationStopped
from radio_connector_fixture import ConnectorGitFixture, IndependentAdmissionFixture, OwnerHandle, bootstrap_counterexample

ROOT = Path(__file__).resolve().parents[1]
PREPARED = "results_radio_rehearsal_contract_2026-09-27/prepared_contract.json"


class SimulatedClientLoss(BaseException):
    """Bypass normal client cleanup; independent fixture authority remains."""


def append_model(before):
    after = deepcopy(before)
    n = len(after["reservations"])
    after["reservations"].append({"ordinal": n, "role": env.EXPECTED_ROLES[n],
        "session_id": str(uuid.uuid4()), "prior_ledger_sha256": env.ledger_digest(before),
        "reserved_limits": dict(env.SESSION_LIMITS), "created_utc": "2026-09-27T14:30:00Z"})
    return after


class ConnectorTests(unittest.TestCase):
    evidence = {}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prepared_bytes = (ROOT/PREPARED).read_bytes()
        self.prepared_sha = hashlib.sha256(self.prepared_bytes).hexdigest()
        self.prepared = json.loads(self.prepared_bytes)
        self.cfg = self.prepared["config"]
        self.services, self.sessions, self.stores, self.authorities = [], [], [], []
        self.observations = {}

    def tearDown(self):
        for session in self.sessions:
            if not session.journal.stream.closed:
                session.journal.close()
        files = {str(p.relative_to(self.root)): base64.b64encode(p.read_bytes()).decode()
                 for p in sorted(self.root.rglob("*")) if p.is_file() and p.name == "attempts.jsonl"}
        self.evidence[self._testMethodName] = {"journal_files_base64": files,
            "services": [s.evidence() for s in self.services],
            "authorities": [a.snapshot() for a in self.authorities],
            "stores": [{"events": s.events, "receipts": s.receipts, "typed_replies": s.typed_replies,
                        "stopped": s.stopped} for s in self.stores], "observations": self.observations}
        self.temp.cleanup()

    def environment(self):
        service = ConnectorGitFixture(self.root/f"git-{len(self.services)}", self.prepared)
        authority = IndependentAdmissionFixture(self.root/f"authority-{len(self.authorities)}.sqlite", self.cfg)
        self.services.append(service)
        self.authorities.append(authority)
        return service, authority

    def previous_assumptions(self, authority, phase, service):
        # Explicit fixture-only preconditions. No claim of live initialization.
        for prior in r.PHASES[:r.PHASES.index(phase)]:
            owner = authority.claim(prior, service.head, r.digest(service.ledger()))
            authority.finish(owner)

    def client(self, service, authority, phase="normal_append", root_name=None):
        owner = authority.claim(phase, service.head, r.digest(service.ledger()))
        provider = c.JournaledConnectorFixture(service, authority, owner)
        session = r.FixtureAttemptJournal(self.root/(root_name or f"client-{len(self.sessions)}"), self.cfg, owner.grant, provider)
        store = c.ConnectorModelStore(session, self.prepared_bytes, self.prepared_sha)
        self.sessions.append(session)
        self.stores.append(store)
        return store, owner

    def setup_normal(self):
        service, authority = self.environment()
        self.previous_assumptions(authority, "normal_append", service)
        store, owner = self.client(service, authority)
        return service, authority, store, owner

    def publish(self, store, service, document=None):
        return store.publish(store.journal.grant["expected_head"], store.journal.grant["expected_model_sha256"],
                             append_model(service.ledger()) if document is None else document)

    def finish(self, authority, store, owner, state="closed"):
        store.journal.close()
        if authority.active.get(owner.token) is owner:
            authority.finish(owner, state)

    def assert_no_retry(self, store, service):
        count = len(service.tool_calls)
        with self.assertRaises(PublicationStopped): store.read()
        self.assertEqual(len(service.tool_calls), count)

    def test_actual_public_commit_tool_envelope_decodes_without_http_inference(self):
        observation = json.loads((ROOT/"results_radio_connector_2026-09-27/observed_commit_tool_result.json").read_text())
        reply = c.decode_reply("read", r.encode(observation["tool_result"]))
        self.assertEqual(reply.value["sha"], "ef0827036b16952808a09a65bad910b3e29577e9")
        self.assertEqual(reply.kind, "git_object")
        self.assertIsNone(reply.http_status)
        self.assertIsNone(reply.api_version)
        self.assertIsNone(reply.internal_attempts)
        self.observations["observed_commit_sha"] = reply.value["sha"]

    def test_minimal_ref_ack_is_not_fabricated_reference_proof(self):
        reply = c.decode_reply("update_ref", r.encode({"isError": False, "structuredContent": {"success": True}}))
        self.assertEqual(reply.kind, "acknowledgement")
        self.assertEqual(reply.value, {"success": True})
        self.assertNotIn("object", reply.value)

    def test_ambiguous_and_text_only_envelopes_fail_closed(self):
        variants = [{"content": [{"text": "success"}]},
                    {"isError": False, "structuredContent": {"success": 1}},
                    {"isError": 0, "structuredContent": {"success": True}},
                    {"isError": True, "structuredContent": {"success": True}}]
        for value in variants:
            with self.subTest(value=value):
                with self.assertRaises(c.ConnectorUncertain): c.decode_reply("update_ref", r.encode(value))

    def test_conflicting_nested_get_content_and_duplicate_json_are_refused(self):
        for data in ({"content": "{}", "structuredContent": {"content": '{"other":1}'}},
                     {"content": '{"sha":"a","sha":"b"}'}, {"content": "[]"}):
            with self.assertRaises((ValueError, c.ConnectorUncertain)):
                c.decode_reply("read", r.encode({"isError": False, "structuredContent": data}))

    def test_two_normal_reads_and_append_share_one_phase_budget(self):
        service, authority, store, owner = self.setup_normal()
        store.read()
        store.read()
        receipt = self.publish(store, service)
        self.assertEqual(len(service.ledger()["reservations"]), 1)
        self.assertEqual(receipt["attempt_id"], owner.grant["attempt_id"])
        self.assertIsNone(receipt["http_status"])
        self.assertLessEqual(store.journal.calls, self.cfg["phase_limits"]["normal_append"]["max_tool_calls"])
        self.assertGreater(store.journal.calls, receipt["tool_calls_in_publish"])
        self.assertEqual(store.journal.calls, len(service.tool_calls))
        self.assertTrue(all(x["http_status"] is None for x in store.typed_replies))
        self.finish(authority, store, owner)
        replay = r.replay(store.journal.journal.path, self.cfg, owner.grant, expected_head=store.journal.journal.head)
        self.assertEqual(replay["remaining_dispatch_rights"], 0)
        self.observations["replay"] = replay

    def test_false_positive_update_ack_does_not_confirm_unlanded_commit(self):
        service, authority, store, owner = self.setup_normal()
        original = service._dispatch
        def unlanded(method, path, body):
            if method == "PATCH":
                return 200, {"ref": service.ref, "object": {"type": "commit", "sha": body["sha"]}}
            return original(method, path, body)
        service._dispatch = unlanded
        with self.assertRaises(PublicationStopped): self.publish(store, service)
        self.assertEqual(service.head, service.initial)
        self.assertEqual(store.receipts, [])
        self.assert_no_retry(store, service)
        self.finish(authority, store, owner, "uncertain")

    def test_unique_attempt_message_must_survive_tool_conversion(self):
        service, authority, store, owner = self.setup_normal()
        original = service.commit
        service.commit = lambda tree, parents, message: original(tree, parents, "dropped unique attempt identity")
        with self.assertRaises(PublicationStopped): self.publish(store, service)
        self.assertFalse(any(x["tool"] == "github_update_ref" for x in service.tool_calls))
        self.assertEqual(service.head, service.initial)
        self.assert_no_retry(store, service)
        self.finish(authority, store, owner, "uncertain")

    def test_error_envelope_after_successful_update_is_uncertain_and_spent(self):
        service, authority, store, owner = self.setup_normal()
        def error_after(tool, args, reply):
            return {"isError": True, "structuredContent": {"error": "reply wrapper failed"}} if tool == "github_update_ref" else reply
        service.tool_after = error_after
        with self.assertRaises(PublicationStopped): self.publish(store, service)
        self.assertEqual(len(service.ledger()["reservations"]), 1)
        self.assertEqual(store.receipts, [])
        self.assert_no_retry(store, service)
        self.finish(authority, store, owner, "uncertain")
        with self.assertRaises(ValueError): authority.claim("normal_append", service.head, r.digest(service.ledger()))

    def test_semantic_veto_revokes_phase_before_rebinding_a_fresh_client(self):
        service, authority, store, owner = self.setup_normal()
        service.tool_after = lambda tool, args, reply: {"isError": True, "structuredContent": {"error": "semantic veto"}}
        with self.assertRaises(PublicationStopped): store.read()
        before = len(service.tool_calls)
        service.tool_after = None
        rebound = c.ConnectorModelStore(store.journal, self.prepared_bytes, self.prepared_sha)
        self.stores.append(rebound)
        with self.assertRaises(PublicationStopped): rebound.read()
        self.assertEqual(len(service.tool_calls), before)
        with self.assertRaises(ValueError): authority.admit(owner, "read", {})
        with self.assertRaises(ValueError): authority.claim("normal_append", service.head, r.digest(service.ledger()))
        self.assertTrue(store.journal.stopped)
        self.observations["phase_veto"] = {"calls_before_rebind": before,
            "calls_after_rebind": len(service.tool_calls), "owner_revoked": True}

    def test_uncertain_write_recovered_readonly_after_client_state_loss(self):
        service, authority, first, normal_owner = self.setup_normal()
        self.publish(first, service)
        self.finish(authority, first, normal_owner)
        lost, lost_owner = self.client(service, authority, "lost_reply_append")
        def lose(tool, args, reply):
            if tool == "github_update_ref": raise SimulatedClientLoss("reply and client lost after simulated Git update")
            return reply
        service.tool_after = lose
        with self.assertRaises(SimulatedClientLoss): self.publish(lost, service)
        self.assertEqual(len(service.ledger()["reservations"]), 2)
        # Retain the old evidence; a fresh client cannot access/reuse its handles.
        lost.journal.close()
        authority.abandon_after_client_loss("lost_reply_append")
        with self.assertRaises(ValueError): authority.claim("lost_reply_append", service.head, r.digest(service.ledger()))
        service.tool_after = None
        fresh_authority = IndependentAdmissionFixture(authority.path, self.cfg)
        self.authorities.append(fresh_authority)
        recovery, owner = self.client(service, fresh_authority, "readonly_recovery", root_name="fresh-client-no-local-checkpoint")
        checkpoint = recovery.read()
        self.assertEqual(len(checkpoint.document["reservations"]), 2)
        self.assertEqual(len(recovery.receipts), 0)
        self.assertTrue(all(x["tool"] == "github_fetch" for x in service.tool_calls[-recovery.journal.calls:]))
        with self.assertRaises(PublicationStopped): self.publish(recovery, service)
        self.assertEqual(len(service.ledger()["reservations"]), 2)
        self.finish(fresh_authority, recovery, owner)
        self.observations["fresh_client_readonly"] = {"reservations_seen": 2, "resend_calls": 0,
            "old_client_journal_used": False, "independent_authority_assumed": True}

    def test_independent_authority_rejects_two_competing_phase_owners(self):
        service, authority = self.environment()
        self.previous_assumptions(authority, "normal_append", service)
        other_authority = IndependentAdmissionFixture(authority.path, self.cfg)
        self.authorities.append(other_authority)
        outcomes, owners = [], []
        barrier = threading.Barrier(2)
        def claim(admission):
            barrier.wait()
            try:
                owners.append((admission, admission.claim("normal_append", service.head, r.digest(service.ledger()))))
                outcomes.append("owned")
            except ValueError:
                outcomes.append("refused")
        threads = [threading.Thread(target=claim, args=(admission,)) for admission in (authority, other_authority)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertCountEqual(outcomes, ["owned", "refused"])
        self.assertEqual(service.tool_calls, [])
        self.observations["owner_race"] = outcomes
        owners[0][0].finish(owners[0][1])

    def test_serialized_grant_does_not_restore_owner_channel(self):
        service, authority, store, owner = self.setup_normal()
        forged = OwnerHandle(deepcopy(owner.grant), object())
        with self.assertRaises(ValueError): authority.admit(forged, "read", {})
        restarted = IndependentAdmissionFixture(authority.path, self.cfg)
        with self.assertRaises(ValueError): restarted.admit(owner, "read", {})
        with self.assertRaises(ValueError): restarted.claim("normal_append", service.head, r.digest(service.ledger()))
        self.assertEqual(service.tool_calls, [])
        self.finish(authority, store, owner)

    def test_all_phase_debits_exhaust_total_without_quota_refund(self):
        service, authority = self.environment()
        for phase in r.PHASES:
            owner = authority.claim(phase, service.head, r.digest(service.ledger()))
            authority.finish(owner)
        snapshot = authority.snapshot()
        self.assertEqual(snapshot["charged_whole_phase_limits"], self.cfg["total_limits"])
        self.assertEqual(snapshot["remaining_whole_phase_limits"], dict.fromkeys(r.LIMIT_KEYS, 0))
        self.assertEqual(service.tool_calls, [])
        with self.assertRaises(ValueError): authority.claim("initialization", service.head, r.digest(service.ledger()))
        self.observations["accounting_scope"] = "all phases charged by supplied authority; no live bootstrap demonstrated"

    def test_independent_admission_occurs_before_connector(self):
        service, authority, store, owner = self.setup_normal()
        def inspect(tool, args, result):
            snapshot = authority.snapshot()
            phase = next(row for row in snapshot["phases"] if row["phase"] == "normal_append")
            self.assertEqual(phase["calls_debited"], len(service.tool_calls))
            return result
        service.tool_after = inspect
        store.read()
        self.finish(authority, store, owner)

    def test_scope_mismatch_and_live_fixture_spoofing_are_refused(self):
        service, authority = self.environment()
        self.previous_assumptions(authority, "normal_append", service)
        owner = authority.claim("normal_append", service.head, r.digest(service.ledger()))
        service.kind = "live-connector"
        with self.assertRaises(ValueError): c.JournaledConnectorFixture(service, authority, owner)
        service.kind = "isolated-connector-envelope-fixture"
        provider = c.JournaledConnectorFixture(service, authority, owner)
        journal = r.FixtureAttemptJournal(self.root/"wrong-pin", self.cfg, owner.grant, provider)
        self.sessions.append(journal)
        with self.assertRaises(ValueError): c.ConnectorModelStore(journal, self.prepared_bytes, "0"*64)
        authority.finish(owner)
        self.assertEqual(service.tool_calls, [])

    def test_phase_budget_is_not_reset_by_repeated_read_operations(self):
        service, authority, store, owner = self.setup_normal()
        with self.assertRaises(PublicationStopped):
            for _ in range(20): store.read()
        self.assertEqual(len(service.tool_calls), 44)
        self.assert_no_retry(store, service)
        self.finish(authority, store, owner, "uncertain")

    def test_wrong_sole_parent_after_connector_conversion_prevents_ref_update(self):
        service, authority, store, owner = self.setup_normal()
        original = service.commit
        service.commit = lambda tree, parents, message: original(tree, [], message)
        with self.assertRaises(PublicationStopped): self.publish(store, service)
        self.assertFalse(any(x["tool"] == "github_update_ref" for x in service.tool_calls))
        self.finish(authority, store, owner, "uncertain")

    def test_single_entry_and_ancestry_guards_survive_typed_conversion(self):
        service, authority, store, owner = self.setup_normal()
        def unrelated_change(tool, args, reply):
            if tool == "github_update_ref":
                service.external_commit(entries=[{"path": "notes/new.txt", "mode": "100644", "content": "unrelated"}])
            return reply
        service.tool_after = unrelated_change
        receipt = self.publish(store, service)
        self.assertEqual(len(receipt["verified_commit_path"]), 2)
        self.assertEqual(service.git("show", receipt["commit"]+":notes/keep.txt").decode(), "Preserve this unrelated file.\n")
        self.finish(authority, store, owner)

    def test_bootstrap_restart_trace_exceeds_initialization_cap_with_no_remote_record(self):
        service, _ = self.environment()
        trace = bootstrap_counterexample(service, self.cfg["phase_limits"]["initialization"]["max_tool_calls"])
        self.assertEqual(trace["counterexample_calls"], 13)
        self.assertEqual(trace["remote_grants_after_trace"], 0)
        self.assertTrue(trace["bound_exceeded"])
        self.assertEqual(service.head, service.initial)
        self.assertEqual(len(service.tool_calls), 13)
        self.observations["counterexample"] = trace

    def test_bootstrap_restart_trace_can_exceed_entire_contract_cap(self):
        service, _ = self.environment()
        trace = bootstrap_counterexample(service, self.cfg["total_limits"]["max_tool_calls"])
        self.assertEqual(trace["counterexample_calls"], 161)
        self.assertEqual(trace["real_connector_calls"], 0)
        self.assertTrue(all(not event["durable_remote_change"] for event in trace["events"]))
        self.assertEqual(service.head, service.initial)
        self.assertEqual(len(service.tool_calls), 161)
        self.observations["counterexample"] = trace


if __name__ == "__main__":
    unittest.main()
