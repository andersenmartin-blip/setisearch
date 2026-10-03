"""Local-only integration tests of unchanged budget/journal with fresh SQLite CAS."""
import copy
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engineering_session_store as candidate
from engineering_session_store import acquisition

TOTAL = {"max_requests": 100, "max_bytes": 10000, "max_seconds": 100}
SESSION = {"max_requests": 5, "max_bytes": 100, "max_seconds": 10}
SCOPE = {"scan": "engineering-on", "window": "calibration", "url": "https://synthetic.invalid/object.h5",
         "source_definition_sha256": "3"*64, "extraction": [64, 128]}


def appended(before, session_limits=SESSION):
    document = copy.deepcopy(before.document)
    document["reservations"].append({"ordinal": len(document["reservations"]), "session_id": str(uuid.uuid4()),
        "prior_ledger_sha256": before.sha256, "reserved_limits": copy.deepcopy(session_limits),
        "created_utc": "2026-10-03T19:00:00+00:00"})
    return document


def race_worker(path, revision, sha, document, ready, release, output):
    try:
        store = candidate.EngineeringSqliteStore.open(path)
        ready.put("ready")
        if not release.wait(10):
            raise ValueError("race test release unavailable")
        store.publish(revision, sha, document)
        output.put({"outcome": "committed", "session_id": document["reservations"][-1]["session_id"]})
    except BaseException as error:
        output.put({"outcome": "refused", "error": type(error).__name__, "reason": str(error)})


class Clock:
    def __init__(self): self.value = 0.0
    def __call__(self): return self.value


class TestEngineeringSessionStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="engineering-session-test-")
        self.root = Path(self.tmp.name)
        self.genesis = acquisition.genesis("1"*64, "2"*64, TOTAL)
        self.store = candidate.EngineeringSqliteStore.create(self.root/"ledger.sqlite3", self.genesis)

    def tearDown(self): self.tmp.cleanup()

    def start(self, name="session", store=None, clock=None, limits=SESSION):
        store = self.store if store is None else store
        before = store.read()
        return acquisition.start_session(store, expected_revision=before.revision,
            expected_ledger_sha256=before.sha256, session_limits=limits,
            directory=self.root/name, clock=Clock() if clock is None else clock)

    def finished(self, name="session"):
        clock = Clock()
        budget = self.start(name, clock=clock)
        budget.bind_scope(copy.deepcopy(SCOPE))
        budget.reserve(0)
        clock.value = 0.25
        budget.reserve(9)
        budget.accepted_bytes += 8
        clock.value = 0.5
        budget.close("completed")
        return budget

    def replay(self, budget, path=None, head=None, scopes=None, checkpoint=None, reservation=None, require_closed=True):
        return candidate.strict_read_journal(path or budget.journal.path,
            expected_checkpoint=checkpoint or budget.checkpoint,
            expected_reservation=reservation or budget.reservation,
            expected_head=head or budget.journal.head, ordered_scopes=[copy.deepcopy(SCOPE)] if scopes is None else scopes,
            require_closed=require_closed)

    def changed_journal(self, budget, mutator, name="changed.jsonl", noncanonical=False):
        records = [json.loads(line) for line in budget.journal.path.read_bytes().splitlines()]
        mutator(records)
        head = acquisition.ZERO
        output = []
        for index, original in enumerate(records):
            record = {"index": index, "previous_sha256": head, "event": original["event"]}
            # A mutator may intentionally override exact index type.
            if original.get("force_index") is not None:
                record["index"] = original["force_index"]
            record["sha256"] = acquisition.digest(record)
            head = record["sha256"]
            output.append((json.dumps(record).encode() if noncanonical else acquisition.encode(record)) + b"\n")
        path = self.root/name
        path.write_bytes(b"".join(output))
        return path, head

    def test_original_positive_budget_journal_and_read_only_replay(self):
        budget = self.finished()
        report = self.replay(budget)
        original = acquisition.read_journal(budget.journal.path, expected_head=budget.journal.head, expected_reservation=budget.reservation)
        for key in ("reserved_attempts", "reserved_bytes", "accepted_bytes", "closed"):
            self.assertEqual(report[key], original[key])
        self.assertEqual((report["reserved_attempts"], report["reserved_bytes"], report["accepted_bytes"]), (2, 9, 8))
        self.assertTrue(report["reservation_remains_fully_charged"])
        self.assertFalse(report["restored_request_permission"])
        self.assertEqual(self.store.read().document["reservations"], [budget.reservation])

    def test_two_process_compare_and_swap_has_exactly_one_winner(self):
        context = multiprocessing.get_context("spawn")
        before = self.store.read()
        documents = [appended(before), appended(before)]
        ready, output, release = context.Queue(), context.Queue(), context.Event()
        processes = [context.Process(target=race_worker, args=(str(self.store.path), before.revision, before.sha256, document, ready, release, output)) for document in documents]
        for process in processes: process.start()
        try:
            self.assertEqual([ready.get(timeout=10) for _ in processes], ["ready", "ready"])
            release.set()
            results = [output.get(timeout=10) for _ in processes]
            for process in processes:
                process.join(timeout=10)
                self.assertEqual(process.exitcode, 0)
            self.assertEqual(sorted(result["outcome"] for result in results), ["committed", "refused"])
            refusal = next(result for result in results if result["outcome"] == "refused")
            self.assertIn("compare-and-swap", refusal["reason"])
            after = self.store.read()
            self.assertEqual(len(after.document["reservations"]), 1)
            self.assertEqual(after.document["reservations"][0]["session_id"], next(result["session_id"] for result in results if result["outcome"] == "committed"))
        finally:
            release.set()
            for process in processes:
                if process.is_alive(): process.terminate()
                process.join(timeout=5)
            ready.close(); output.close()

    def test_genesis_only_and_no_replace_failed_or_existing_file(self):
        with self.assertRaises(FileExistsError): candidate.EngineeringSqliteStore.create(self.store.path, self.genesis)
        before = self.store.read()
        with self.assertRaisesRegex(ValueError, "fresh engineering genesis"):
            candidate.EngineeringSqliteStore.create(self.root/"nonfresh.sqlite", appended(before))
        empty = self.root/"failed-create.sqlite"
        empty.write_bytes(b"")
        with self.assertRaises(FileExistsError): candidate.EngineeringSqliteStore.create(empty, self.genesis)
        with self.assertRaises(ValueError): candidate.EngineeringSqliteStore.open(empty)

    def test_stale_revision_or_digest_never_publishes(self):
        before = self.store.read()
        for revision, sha in (("engineering-sqlite:99", before.sha256), (before.revision, "f"*64), (True, before.sha256)):
            with self.subTest(revision=revision, sha=sha):
                with self.assertRaises(ValueError): self.store.publish(revision, sha, appended(before))
        self.assertEqual(self.store.read().sha256, before.sha256)

    def test_refund_reorder_ancestry_and_alias_edits_refused(self):
        budget = self.finished()
        before = self.store.read()
        edits = []
        removed = copy.deepcopy(before.document); removed["reservations"] = []; edits.append(removed)
        noappend = copy.deepcopy(before.document); edits.append(noappend)
        reorder = appended(before); reorder["reservations"].reverse(); edits.append(reorder)
        altered = appended(before); altered["contract_sha256"] = "f"*64; edits.append(altered)
        alias = appended(before); alias["reservations"][0]["reserved_limits"]["max_seconds"] = 10.0; edits.append(alias)
        for document in edits:
            with self.subTest(document=document):
                with self.assertRaises(ValueError): self.store.publish(before.revision, before.sha256, document)
        self.assertEqual(self.store.read().sha256, before.sha256)

    def test_publication_uncertainty_remains_fully_charged_without_budget(self):
        real = self.store
        class Uncertain:
            read = real.read
            def publish(self, revision, sha, document):
                real.publish(revision, sha, document)
                raise OSError("publication acknowledgement lost")
        with self.assertRaisesRegex(OSError, "acknowledgement lost"): self.start(store=Uncertain())
        after = real.read()
        self.assertEqual(len(after.document["reservations"]), 1)
        self.assertEqual(acquisition.validate_ledger(after.document, after.sha256)["charged_limits"], SESSION)
        self.assertFalse((self.root/"session").exists())
        fresh = self.start("next-process")
        self.assertEqual(fresh.reservation["ordinal"], 1)
        fresh.close("error")

    def test_directory_fsync_after_commit_uncertainty_keeps_charge(self):
        before = self.store.read()
        with mock.patch.object(candidate, "_sync_directory", side_effect=OSError("directory fsync failed")):
            with self.assertRaisesRegex(OSError, "directory fsync"): self.start()
        after = self.store.read()
        self.assertNotEqual(after.sha256, before.sha256)
        self.assertEqual(len(after.document["reservations"]), 1)
        self.assertFalse((self.root/"session").exists())

    def test_postpublication_readback_ambiguity_has_no_journal_or_budget(self):
        real = self.store
        before = real.read()
        class Ambiguous:
            count = 0
            def read(self):
                self.count += 1
                return before if self.count >= 3 else real.read()
            publish = real.publish
        with self.assertRaisesRegex(ValueError, "publication not confirmed"): self.start(store=Ambiguous())
        self.assertEqual(len(real.read().document["reservations"]), 1)
        self.assertFalse((self.root/"session").exists())

    def test_postpublication_location_change_remains_charged_without_budget(self):
        real = self.store
        class Relocated:
            count = 0
            def read(self):
                self.count += 1
                checkpoint = real.read()
                if self.count >= 3:
                    location = copy.deepcopy(checkpoint.location)
                    location["path"] = str(self.root/"different-ledger.sqlite")
                    return acquisition.Checkpoint(checkpoint.document, checkpoint.revision, location)
                return checkpoint
            publish = real.publish
        # Capture the outer test root without turning it into implicit authority.
        relocated = Relocated(); relocated.root = self.root
        with self.assertRaisesRegex(ValueError, "publication not confirmed"): self.start(store=relocated)
        self.assertEqual(len(real.read().document["reservations"]), 1)
        self.assertFalse((self.root/"session").exists())

    def test_preexisting_session_directory_charges_without_dispatch(self):
        (self.root/"session").mkdir()
        with self.assertRaises(FileExistsError): self.start()
        self.assertEqual(len(self.store.read().document["reservations"]), 1)
        self.assertEqual(list((self.root/"session").iterdir()), [])

    def test_initial_journal_local_failure_keeps_whole_reservation_charged(self):
        with mock.patch.object(acquisition, "_sync_directory", side_effect=OSError("journal directory fsync failed")):
            with self.assertRaisesRegex(OSError, "journal directory fsync failed"): self.start()
        self.assertEqual(len(self.store.read().document["reservations"]), 1)
        path = self.root/"session"/"attempts.jsonl"
        self.assertTrue(path.exists())
        self.assertEqual(path.stat().st_size, 0)

    def test_prepublication_error_never_dispatches_or_charges(self):
        dispatches = []
        before = self.store.read()
        with self.assertRaises(ValueError):
            budget = acquisition.start_session(self.store, expected_revision="stale", expected_ledger_sha256=before.sha256,
                session_limits=SESSION, directory=self.root/"session")
            dispatches.append(budget.reserve(0))
        self.assertEqual(dispatches, [])
        self.assertEqual(self.store.read().sha256, before.sha256)

    def test_existing_checkpoint_cannot_reconstruct_original_budget(self):
        budget = self.finished()
        reopened = candidate.EngineeringSqliteStore.open(self.store.path).read()
        with self.assertRaisesRegex(ValueError, "newly published reservation"):
            acquisition.DurableBudget(reopened, budget.reservation, self.root/"restored")
        with self.assertRaises(ValueError): budget.reserve(0)
        with self.assertRaises(ValueError): budget.bind_scope(SCOPE)
        self.assertFalse((self.root/"restored").exists())

    def test_budget_quota_time_and_accepted_accounting_fail_closed(self):
        clock = Clock(); budget = self.start(clock=clock)
        with self.assertRaises(ValueError): budget.reserve(0)
        budget.bind_scope(copy.deepcopy(SCOPE))
        budget.reserve(9)
        for value in (True, 7, 9):
            with self.assertRaises(ValueError): budget.accepted_bytes = value
        budget.accepted_bytes = 8
        with self.assertRaises(ValueError): budget.accepted_bytes = 16
        with self.assertRaises(ValueError): budget.reserve(101)
        clock.value = 11
        with self.assertRaises(ValueError): budget.reserve(0)
        clock.value = 9.0; budget.close("error")
        self.assertEqual(self.replay(budget)["reserved_attempts"], 1)

    def test_sqlite_connection_failure_before_cas_never_charges(self):
        before = self.store.read()
        with mock.patch.object(candidate.sqlite3, "connect", side_effect=sqlite3.OperationalError("local connection failed")):
            with self.assertRaises(sqlite3.OperationalError): self.store.publish(before.revision, before.sha256, appended(before))
        self.assertEqual(self.store.read().sha256, before.sha256)

    def test_journal_fsync_failure_cannot_dispatch_or_resume(self):
        budget = self.start(); budget.bind_scope(copy.deepcopy(SCOPE))
        with mock.patch.object(acquisition.os, "fsync", side_effect=OSError("journal fsync failed")):
            with self.assertRaisesRegex(OSError, "journal fsync failed"): budget.reserve(9)
        self.assertTrue(budget.journal.broken)
        self.assertEqual(budget.attempts, 0)
        with self.assertRaises(ValueError): budget.reserve(9)
        with self.assertRaises(ValueError): budget.close("error")
        self.assertTrue(budget.closed)
        self.assertEqual(len(self.store.read().document["reservations"]), 1)

    def test_journal_short_write_is_broken_and_torn_without_refund(self):
        budget = self.start(); budget.bind_scope(copy.deepcopy(SCOPE))
        real = budget.journal.stream
        class ShortWrite:
            closed = False
            def write(self, payload): return real.write(payload[:10])
            def fileno(self): return real.fileno()
            def close(self): self.closed = True; real.close()
        budget.journal.stream = ShortWrite()
        with self.assertRaisesRegex(OSError, "short journal write"): budget.reserve(9)
        self.assertTrue(budget.journal.broken)
        self.assertEqual(budget.attempts, 0)
        with self.assertRaises(ValueError): budget.close("error")
        with self.assertRaises(ValueError): self.replay(budget)
        self.assertEqual(len(self.store.read().document["reservations"]), 1)

    def test_cumulative_limits_remain_charged_after_errors(self):
        cap = {"max_requests": 2, "max_bytes": 20, "max_seconds": 10}
        store = candidate.EngineeringSqliteStore.create(self.root/"bounded.sqlite", acquisition.genesis("1"*64, "2"*64, cap))
        first = self.start("bounded-first", store=store, limits=cap); first.close("error")
        with self.assertRaisesRegex(ValueError, "cumulative reservation budget exhausted"):
            self.start("bounded-second", store=store, limits=cap)
        self.assertEqual(len(store.read().document["reservations"]), 1)

    def test_database_symlink_hardlink_fifo_and_oversize_refused(self):
        symlink = self.root/"linked.sqlite"; symlink.symlink_to(self.store.path)
        with self.assertRaises(OSError): candidate.EngineeringSqliteStore.open(symlink)
        hard = self.root/"hard.sqlite"; os.link(self.store.path, hard)
        with self.assertRaises(ValueError): self.store.read()
        hard.unlink()
        fifo = self.root/"fifo.sqlite"; os.mkfifo(fifo)
        with self.assertRaises(ValueError): candidate.EngineeringSqliteStore.open(fifo)
        large = self.root/"large.sqlite"; large.write_bytes(b"x")
        with large.open("r+b") as stream: stream.truncate(candidate.MAX_DB_BYTES+1)
        with self.assertRaises(ValueError): candidate.EngineeringSqliteStore.open(large)

    def test_ledger_and_history_tampering_refused(self):
        before = self.store.read()
        huge = copy.deepcopy(self.genesis); huge["extra"] = "x"*candidate.MAX_LEDGER_BYTES
        with self.assertRaises(ValueError): self.store.publish(before.revision, before.sha256, huge)
        self.finished()
        db = sqlite3.connect(str(self.store.path))
        db.execute("DELETE FROM history WHERE revision=0"); db.commit(); db.close()
        with self.assertRaises(ValueError): self.store.read()

    def test_exact_start_checkpoint_and_ordered_scope_joins(self):
        budget = self.finished()
        wrong_location = copy.deepcopy(budget.checkpoint.location); wrong_location["path"] = str(self.root/"other.sqlite")
        checkpoint = acquisition.Checkpoint(budget.checkpoint.document, budget.checkpoint.revision, wrong_location)
        with self.assertRaises(ValueError): self.replay(budget, checkpoint=checkpoint)
        wrong_scope = copy.deepcopy(SCOPE); wrong_scope["window"] = "pilot"
        with self.assertRaises(ValueError): self.replay(budget, scopes=[wrong_scope])
        with self.assertRaises(ValueError): self.replay(budget, scopes=[SCOPE, SCOPE])
        reservation = copy.deepcopy(budget.reservation); reservation["reserved_limits"]["max_seconds"] = 10.0
        with self.assertRaises(ValueError): self.replay(budget, reservation=reservation)

    def test_recomputed_chain_cannot_hide_types_fields_time_or_scope_edits(self):
        budget = self.finished()
        mutations = {
            "attempt-bool": lambda rs: rs[2]["event"].__setitem__("attempt", True),
            "reserve-float": lambda rs: rs[3]["event"].__setitem__("reserved_bytes", 9.0),
            "accepted-float": lambda rs: rs[4]["event"].__setitem__("bytes", 8.0),
            "extra-reserve": lambda rs: rs[2]["event"].__setitem__("extra", 0),
            "negative-time": lambda rs: rs[2]["event"].__setitem__("elapsed_seconds", -1),
            "bool-time": lambda rs: rs[2]["event"].__setitem__("elapsed_seconds", False),
            "regressed-time": lambda rs: rs[5]["event"].__setitem__("elapsed_seconds", 0.1),
            "overcap-time": lambda rs: rs[5]["event"].__setitem__("elapsed_seconds", 11),
            "forged-start-ledger": lambda rs: rs[0]["event"].__setitem__("ledger_sha256", "f"*64),
            "real-service-scope": lambda rs: rs[1]["event"]["scope"].__setitem__("url", "https://example.com/data.h5"),
            "interval-bool": lambda rs: rs[1]["event"]["scope"].__setitem__("extraction", [True,128]),
            "index-bool": lambda rs: rs[1].__setitem__("force_index", True),
            "repeated-body": lambda rs: rs.insert(5, copy.deepcopy(rs[4])),
            "after-close": lambda rs: rs.append(copy.deepcopy(rs[1])),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name):
                path, head = self.changed_journal(budget, mutation, name+".jsonl")
                with self.assertRaises(ValueError): self.replay(budget, path=path, head=head)

    def test_torn_tampered_rollback_and_unclosed_head_refused(self):
        budget = self.finished()
        payload = budget.journal.path.read_bytes()
        torn = self.root/"torn.jsonl"; torn.write_bytes(payload[:-1])
        with self.assertRaises(ValueError): self.replay(budget, path=torn)
        changed = self.root/"tampered.jsonl"; changed.write_bytes(payload.replace(b'"bytes":8', b'"bytes":7'))
        with self.assertRaises(ValueError): self.replay(budget, path=changed)
        lines = payload.splitlines()
        rollback = self.root/"rollback.jsonl"; rollback.write_bytes(b"\n".join(lines[:-1])+b"\n")
        old_head = json.loads(lines[-2])["sha256"]
        with self.assertRaises(ValueError): self.replay(budget, path=rollback, head=old_head)
        open_report = self.replay(budget, path=rollback, head=old_head, require_closed=False)
        self.assertFalse(open_report["closed"])
        with self.assertRaises(ValueError): self.replay(budget, path=rollback)

    def test_noncanonical_duplicate_json_and_empty_completion_refused(self):
        budget = self.finished()
        path, head = self.changed_journal(budget, lambda rs: None, noncanonical=True)
        with self.assertRaises(ValueError): self.replay(budget, path=path, head=head)
        duplicate = self.root/"duplicate.jsonl"
        duplicate.write_bytes(budget.journal.path.read_bytes().replace(b'"index":0', b'"index":0,"index":0', 1))
        with self.assertRaises(ValueError): self.replay(budget, path=duplicate)
        crlf = self.root/"crlf.jsonl"; crlf.write_bytes(budget.journal.path.read_bytes().replace(b"\n", b"\r\n"))
        with self.assertRaisesRegex(ValueError, "LF record separators"): self.replay(budget, path=crlf)
        empty = self.start("empty"); empty.close("completed")
        with self.assertRaises(ValueError): self.replay(empty, scopes=[])

    def test_completed_unaccepted_get_cannot_hide_behind_next_head_scope_or_get(self):
        budget = self.finished()
        mutations = {
            "missing-final-body": lambda rs: rs.pop(4),
            "head-overwrites-missing-get": lambda rs: rs.insert(2, {"event": {"type": "reserve", "attempt": 1, "reserved_bytes": 7, "elapsed_seconds": 0}}),
            "scope-overwrites-missing-get": lambda rs: rs.insert(1, {"event": {"type": "reserve", "attempt": 1, "reserved_bytes": 7, "elapsed_seconds": 0}}),
        }
        # Missing-body variant is a semantically valid original replay and must
        # fail strict completed-product replay even with an honestly pinned head.
        path, head = self.changed_journal(budget, mutations["missing-final-body"], "missing-final-body.jsonl")
        self.assertTrue(acquisition.read_journal(path, expected_head=head, expected_reservation=budget.reservation)["closed"])
        with self.assertRaisesRegex(ValueError, "full ordered scope inventory|unaccepted GET"):
            self.replay(budget, path=path, head=head)
        # Fresh explicit sequences avoid relying on invalid attempt numbering.
        for name, sequence in (("next-head", ("head",)), ("next-get", ("get",)), ("next-scope", ("scope", "get"))):
            clock = Clock(); fresh = self.start(name, clock=clock)
            fresh.bind_scope(copy.deepcopy(SCOPE)); fresh.reserve(7)
            scopes = [copy.deepcopy(SCOPE)]
            for action in sequence:
                if action == "head": fresh.reserve(0)
                elif action == "get": fresh.reserve(9); fresh.accepted_bytes += 8
                else: fresh.bind_scope(copy.deepcopy(SCOPE)); scopes.append(copy.deepcopy(SCOPE))
            fresh.close("completed")
            with self.assertRaises(ValueError): self.replay(fresh, scopes=scopes)

    def test_error_or_interrupted_keeps_failed_get_charged_and_replayable(self):
        for outcome in ("error", "interrupted"):
            fresh = self.start(outcome)
            fresh.bind_scope(copy.deepcopy(SCOPE)); fresh.reserve(9); fresh.close(outcome)
            report = self.replay(fresh)
            self.assertEqual((report["reserved_attempts"], report["reserved_bytes"], report["accepted_bytes"], report["unaccepted_get_attempts"]), (1,9,0,1))
            self.assertTrue(report["reservation_remains_fully_charged"])

    def test_database_oversized_individual_ledger_refused_before_payload_fetch(self):
        db = sqlite3.connect(str(self.store.path))
        db.execute("UPDATE history SET document=? WHERE revision=0", (b"x"*(candidate.MAX_LEDGER_BYTES+1),))
        db.commit(); db.close()
        with self.assertRaisesRegex(ValueError, "exact bounds"): self.store.read()

    def test_journal_file_and_record_bounds_refused(self):
        budget = self.finished()
        hard = self.root/"hard.jsonl"; os.link(budget.journal.path, hard)
        with self.assertRaises(ValueError): self.replay(budget)
        hard.unlink()
        symlink = self.root/"symlink.jsonl"; symlink.symlink_to(budget.journal.path)
        with self.assertRaises(OSError): self.replay(budget, path=symlink)
        large = self.root/"large.jsonl"; large.write_bytes(b"x")
        with large.open("r+b") as stream: stream.truncate(candidate.MAX_JOURNAL_BYTES+1)
        with self.assertRaises(ValueError): self.replay(budget, path=large)
        longline = self.root/"longline.jsonl"; longline.write_bytes(b"x"*(candidate.MAX_JOURNAL_RECORD_BYTES+1)+b"\n")
        with self.assertRaises(ValueError): self.replay(budget, path=longline)


if __name__ == "__main__":
    unittest.main(verbosity=2)
