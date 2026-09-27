"""New attempt-journal risks only; no old backend/codec/science test replay."""
import base64
from copy import deepcopy
from datetime import date
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from seti_repeater import rehearsal_contract_radio as r

ROOT = Path(__file__).resolve().parents[1]
CONFIG = "config/radio_rehearsal_contract_20260927.json"


class Provider:
    kind = "local-rehearsal-call-fixture"

    def __init__(self, action=None):
        self.calls = []
        self.action = action or (lambda: "ok")

    def dispatch(self, operation, request):
        self.calls.append({"operation": operation, "request": deepcopy(request)})
        return self.action()


def persist(path, payload):
    with Path(path).open("xb", buffering=0) as stream:
        stream.write(payload)
        os.fsync(stream.fileno())


def crash_worker(root, cfg, grant, after_side_effect):
    # The independent checkpoint is retained separately from the journal.
    # Both are LOCAL disks: this is not remote/scratch-loss durability evidence.
    def action():
        persist(Path(root)/"intent_checkpoint.txt", journal.journal.head.encode())
        if after_side_effect:
            persist(Path(root)/"simulated_side_effect.txt", b"one fixture write")
        os._exit(75 if after_side_effect else 74)
    journal = r.FixtureAttemptJournal(root, cfg, grant, Provider(action))
    journal.call("create_tree", {"fixture": True}, reserve_reply_bytes=256)


class RehearsalTests(unittest.TestCase):
    evidence = {}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cfg = json.loads((ROOT/CONFIG).read_text())
        self.genesis = json.loads((ROOT/"results_radio_execution_envelope_2026-09-27/resource_ledger_genesis.json").read_text())
        self.sessions, self.providers, self.observations = [], [], {}

    def tearDown(self):
        for session in self.sessions:
            if not session.journal.stream.closed:
                session.journal.close()
        files = {str(p.relative_to(self.root)): base64.b64encode(p.read_bytes()).decode()
                 for p in sorted(self.root.rglob("*")) if p.is_file()}
        self.evidence[self._testMethodName] = {"files_base64": files,
            "fixture_calls": [p.calls for p in self.providers], "observations": self.observations}
        self.temp.cleanup()

    def session(self, phase="initialization", provider=None, clock=None):
        provider = provider or Provider()
        grant = r.fixture_grant(self.cfg, phase, "a"*40, "b"*64)
        kwargs = {"clock": clock} if clock is not None else {}
        session = r.FixtureAttemptJournal(self.root, self.cfg, grant, provider, **kwargs)
        self.sessions.append(session)
        self.providers.append(provider)
        return session

    def replay(self, session):
        result = r.replay(session.journal.path, self.cfg, session.grant, expected_head=session.journal.head)
        self.observations[session.grant["phase"]] = result
        self.assertEqual(result["remaining_dispatch_rights"], 0)
        self.assertFalse(result["telescope_access_authorized"])
        return result

    def assert_stopped(self, session):
        before = len(session.provider.calls)
        with self.assertRaises(r.AttemptStopped):
            session.call("read", {}, reserve_reply_bytes=1)
        self.assertEqual(len(session.provider.calls), before)

    def test_separate_genesis_and_no_activation_even_before_expiry(self):
        prep = r.prepare(self.cfg, self.genesis)
        self.assertNotEqual(prep["model_genesis_sha256"], r.digest(self.genesis))
        self.assertNotEqual(prep["model_genesis"]["source_inventory_sha256"], self.genesis["source_inventory_sha256"])
        self.assertEqual(prep["grant_genesis"]["grants"], [])
        for day, expired in ((date(2026, 9, 27), False), (date(2026, 10, 9), False), (date(2026, 10, 10), True)):
            state = r.activation_state(prep, today=day)
            self.assertEqual(state["status"], "BLOCKED")
            self.assertEqual(state["expired"], expired)
            self.assertFalse(state["live_execution_authorized"])
        self.observations["planned_genesis_sha256"] = prep["model_genesis_sha256"]

    def test_cumulative_caps_and_bool_limits_are_rejected(self):
        for key in r.LIMIT_KEYS:
            with self.subTest(key=key):
                cfg = deepcopy(self.cfg)
                cfg["total_limits"][key] += 1
                with self.assertRaises(ValueError): r.validate_config(cfg)
        for section, key in (("initialization", "max_tool_calls"), ("readonly_recovery", "max_wall_seconds")):
            cfg = deepcopy(self.cfg)
            cfg["phase_limits"][section][key] = True
            with self.assertRaises(ValueError): r.validate_config(cfg)
        cfg = deepcopy(self.cfg)
        cfg["max_attempts_per_mutating_phase"] = True
        with self.assertRaises(ValueError): r.validate_config(cfg)

    def test_closed_demo_or_telescope_paths_cannot_be_substituted(self):
        for path in ("results_radio_acquisition_2026-09-26/published_fixture_ledger.json",
                     "results_radio_hd1461_live_v2/resource_ledger.json", "../model_ledger.json"):
            cfg = deepcopy(self.cfg)
            cfg["location"]["path"] = path
            with self.assertRaises(ValueError): r.validate_config(cfg)
        cfg = deepcopy(self.cfg)
        cfg["namespace_id"] += "-reset"
        with self.assertRaises(ValueError): r.validate_config(cfg)

    def test_preparation_cannot_be_relabelled_ready(self):
        for key in ("live_execution_authorized", "namespace_initialization_authorized", "telescope_access_authorized", "automatic_retry", "refund"):
            cfg = deepcopy(self.cfg)
            cfg[key] = True
            with self.assertRaises(ValueError): r.validate_config(cfg)
        prep = r.prepare(self.cfg, self.genesis)
        prep["activation_gates"] = dict.fromkeys(r.GATES, True)
        with self.assertRaises(ValueError): r.activation_state(prep, today=date(2026, 9, 27))

    def test_live_provider_and_fake_remote_grant_rejected(self):
        provider = Provider()
        provider.kind = "github-live"
        with self.assertRaises(ValueError): self.session(provider=provider)
        grant = r.fixture_grant(self.cfg, "initialization", "a"*40, "b"*64)
        grant["remote_grant_confirmed"] = True
        with self.assertRaises(ValueError):
            r.FixtureAttemptJournal(self.root, self.cfg, grant, Provider())

    def test_intent_is_fsynced_before_dispatch_and_unicode_measured(self):
        def action():
            rows = session.journal.path.read_text().splitlines()
            self.assertEqual(json.loads(rows[-1])["event"]["type"], "call_intent")
            self.assertEqual(session.journal.head, json.loads(rows[-1])["sha256"])
            return "ø🛰"
        session = self.session(provider=Provider(action))
        self.assertEqual(session.call("read", {"scope": "fixture"}, reserve_reply_bytes=100), "ø🛰")
        session.close()
        result = self.replay(session)
        self.assertEqual(result["returned_response_utf8_bytes"], 6)
        self.assertEqual(result["reserved_response_utf8_bytes"], 100)
        self.assertEqual(result["full_phase_charged"], self.cfg["phase_limits"]["initialization"])

    def test_no_unused_response_refund(self):
        session = self.session()
        for _ in range(2): session.call("read", {}, reserve_reply_bytes=2097152)
        with self.assertRaises(r.AttemptStopped): session.call("read", {}, reserve_reply_bytes=1)
        self.assertEqual(len(session.provider.calls), 2)
        result = self.replay(session)
        self.assertEqual(result["reserved_response_utf8_bytes"], 4194304)
        self.assertEqual(result["stop_reason"], "phase allowance exhausted")
        self.assertTrue(result["failed"])
        self.assert_stopped(session)

    def test_call_count_exhaustion_counts_even_tiny_results(self):
        session = self.session()
        for _ in range(12): session.call("read", {}, reserve_reply_bytes=10)
        with self.assertRaises(r.AttemptStopped): session.call("read", {}, reserve_reply_bytes=10)
        self.assertEqual(self.replay(session)["calls_intended"], 12)
        self.assert_stopped(session)

    def test_lost_reply_keeps_intent_charge_and_one_side_effect(self):
        def action():
            persist(self.root/"side_effect", b"one")
            raise TimeoutError("reply missing after simulated write")
        session = self.session(provider=Provider(action))
        with self.assertRaises(TimeoutError): session.call("create_tree", {}, reserve_reply_bytes=512)
        self.assertTrue(self.replay(session)["failed"])
        self.assertEqual(len(session.provider.calls), 1)
        self.assert_stopped(session)

    def test_oversized_reply_retained_and_never_refunded(self):
        session = self.session(provider=Provider(lambda: "x"*101))
        with self.assertRaises(r.AttemptStopped): session.call("read", {}, reserve_reply_bytes=100)
        result = self.replay(session)
        self.assertEqual(result["returned_response_utf8_bytes"], 101)
        self.assertTrue(result["failed"])
        self.assert_stopped(session)

    def test_deadline_before_call_and_late_reply(self):
        now = [0.0]
        session = self.session(clock=lambda: now[0])
        now[0] = 120.0
        with self.assertRaises(r.AttemptStopped): session.call("read", {}, reserve_reply_bytes=100)
        self.assertEqual(session.provider.calls, [])
        now[0] = 0.0
        def late():
            now[0] = 301.0
            return "ok"
        other = self.session("normal_append", Provider(late), clock=lambda: now[0])
        with self.assertRaises(r.AttemptStopped): other.call("read", {}, reserve_reply_bytes=100)
        self.assertTrue(self.replay(other)["failed"])
        self.assert_stopped(other)

    def test_clock_regression_stops_before_second_dispatch(self):
        now = [0.0]
        session = self.session(clock=lambda: now[0])
        now[0] = 10.0
        session.call("read", {}, reserve_reply_bytes=100)
        now[0] = 5.0
        with self.assertRaises(r.AttemptStopped): session.call("read", {}, reserve_reply_bytes=100)
        self.assertEqual(len(session.provider.calls), 1)
        self.assertEqual(self.replay(session)["stop_reason"], "invalid monotonic clock")

    def test_malformed_reply_retains_pending_intent_and_stop_reason(self):
        session = self.session(provider=Provider(lambda: {"incompatible": "decoded object"}))
        with self.assertRaises(r.AttemptStopped): session.call("read", {}, reserve_reply_bytes=100)
        result = self.replay(session)
        self.assertIsNotNone(result["pending_call_id"])
        self.assertTrue(result["failed"])
        self.assertIn("exact tool-visible text", result["stop_reason"])
        self.assert_stopped(session)

    def test_intent_fsync_failure_prevents_dispatch(self):
        session = self.session()
        checkpoint = session.journal.head
        with patch("seti_repeater.acquisition_radio.os.fsync", side_effect=OSError("injected disk fault")):
            with self.assertRaises(OSError): session.call("create_tree", {}, reserve_reply_bytes=100)
        self.assertEqual(session.provider.calls, [])
        self.assert_stopped(session)
        with self.assertRaises(ValueError): r.replay(session.journal.path, self.cfg, session.grant, expected_head=checkpoint)
        self.observations["dispatch_count_after_failed_intent_fsync"] = 0

    def test_result_fsync_failure_leaves_independent_intent_checkpoint(self):
        captured = {}
        original = r.SessionJournal.append
        def failing_append(journal, event):
            if event["type"] == "call_result":
                captured["intent_head"] = journal.head
                raise OSError("result write unavailable")
            return original(journal, event)
        session = self.session()
        with patch.object(r.SessionJournal, "append", failing_append):
            with self.assertRaises(OSError): session.call("create_tree", {}, reserve_reply_bytes=100)
        result = r.replay(session.journal.path, self.cfg, session.grant, expected_head=captured["intent_head"])
        self.observations["read_only_recovery"] = result
        self.assertIsNotNone(result["pending_call_id"])
        self.assertEqual(len(session.provider.calls), 1)
        self.assert_stopped(session)

    def test_existing_phase_cannot_be_reopened_even_with_fresh_attempt_id(self):
        session = self.session()
        session.close()
        with self.assertRaises(FileExistsError): self.session()
        self.assertEqual(len(session.provider.calls), 0)

    def test_readonly_recovery_refuses_mutation(self):
        session = self.session("readonly_recovery")
        with self.assertRaises(r.AttemptStopped): session.call("create_tree", {}, reserve_reply_bytes=100)
        self.assertEqual(session.provider.calls, [])

    def test_one_ordered_mutation_sequence_and_force_false(self):
        session = self.session()
        for op in r.MUTATIONS:
            session.call(op, {"force": False} if op == "update_ref" else {}, reserve_reply_bytes=100)
        with self.assertRaises(r.AttemptStopped): session.call("create_tree", {}, reserve_reply_bytes=100)
        self.assertEqual(len(session.provider.calls), 3)
        self.assertEqual(self.replay(session)["calls_intended"], 3)
        other = self.session("normal_append")
        for op in r.MUTATIONS[:2]: other.call(op, {}, reserve_reply_bytes=100)
        with self.assertRaises(r.AttemptStopped): other.call("update_ref", {"force": True}, reserve_reply_bytes=100)
        self.assertEqual(len(other.provider.calls), 2)

    def test_request_and_single_reply_bounds_prevent_dispatch(self):
        session = self.session()
        with self.assertRaises(r.AttemptStopped): session.call("read", {"x": "a"*262144}, reserve_reply_bytes=1)
        other = self.session("normal_append")
        with self.assertRaises(r.AttemptStopped): other.call("read", {}, reserve_reply_bytes=2097153)
        self.assertEqual(session.provider.calls+other.provider.calls, [])

    def test_torn_tail_changed_hash_and_valid_prefix_truncation_refused(self):
        session = self.session()
        session.call("read", {}, reserve_reply_bytes=100)
        session.close()
        original = session.journal.path.read_bytes()
        variants = (original[:-1], original.replace(b'"read"', b'"reed"'),
                    b"\n".join(original.splitlines()[:-1])+b"\n")
        for index, payload in enumerate(variants):
            path = self.root/f"corruption-{index}.jsonl"
            path.write_bytes(payload)
            with self.assertRaises(ValueError): r.replay(path, self.cfg, session.grant, expected_head=session.journal.head)
        self.replay(session)

    def test_different_grant_and_missing_independent_checkpoint_refused(self):
        session = self.session()
        session.close()
        altered = deepcopy(session.grant)
        altered["expected_head"] = "c"*40
        with self.assertRaises(ValueError): r.replay(session.journal.path, self.cfg, altered, expected_head=session.journal.head)
        with self.assertRaises(ValueError): r.replay(session.journal.path, self.cfg, session.grant, expected_head=None)

    def test_rehashed_invalid_grammar_is_not_accepted(self):
        session = self.session()
        session.call("read", {}, reserve_reply_bytes=100)
        rows = [json.loads(line) for line in session.journal.path.read_text().splitlines()]
        for variant in ("orphan_reply", "bool_ordinal", "false_accept", "reply_then_another_reply"):
            events = [deepcopy(row["event"]) for row in rows]
            if variant == "orphan_reply": events.pop(1)
            if variant == "bool_ordinal": events[1]["ordinal"] = False
            if variant == "false_accept": events[2]["accepted"] = False
            if variant == "reply_then_another_reply": events.append(deepcopy(events[2]))
            head, payload = r.ZERO, b""
            for index, event in enumerate(events):
                row = {"index": index, "previous_sha256": head, "event": event}
                head = r.digest(row)
                row["sha256"] = head
                payload += r.encode(row)+b"\n"
            path = self.root/(variant+".jsonl")
            path.write_bytes(payload)
            with self.assertRaises(ValueError): r.replay(path, self.cfg, session.grant, expected_head=head)

    def test_duplicate_keys_and_nonfinite_json_refused(self):
        for payload in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'):
            with self.assertRaises(ValueError): r.strict_json(payload)

    def crash_case(self, after_side_effect):
        grant = r.fixture_grant(self.cfg, "lost_reply_append", "a"*40, "b"*64)
        process = multiprocessing.get_context("fork").Process(target=crash_worker,
            args=(str(self.root), self.cfg, grant, after_side_effect))
        process.start()
        process.join(10)
        if process.is_alive():
            process.kill()
            process.join()
            self.fail("crash fixture did not terminate")
        self.assertEqual(process.exitcode, 75 if after_side_effect else 74)
        path = self.root/grant["contract_sha256"]/grant["phase"]/"attempts.jsonl"
        checkpoint = (self.root/"intent_checkpoint.txt").read_text()
        result = r.replay(path, self.cfg, grant, expected_head=checkpoint)
        self.assertEqual(result["calls_intended"], 1)
        self.assertIsNotNone(result["pending_call_id"])
        self.assertEqual(result["remaining_dispatch_rights"], 0)
        self.assertEqual((self.root/"simulated_side_effect.txt").exists(), after_side_effect)
        with self.assertRaises(FileExistsError): r.FixtureAttemptJournal(self.root, self.cfg, grant, Provider())
        self.observations.update({"process_exit_code": process.exitcode, "read_only_recovery": result,
            "side_effect_exists": after_side_effect, "restart_dispatches": 0})

    def test_process_exit_after_intent_before_simulated_side_effect(self):
        self.crash_case(False)

    def test_process_exit_after_side_effect_before_reply(self):
        self.crash_case(True)


if __name__ == "__main__":
    unittest.main()
