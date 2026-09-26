"""Actual transport handoff, persistent quota, crash and publication fault checks."""
import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from seti_repeater import acquisition_radio as acquisition
from seti_repeater import transport_radio as transport
from seti_repeater import http_range_v0p6 as ranges
from seti_repeater import source_m43h as rows
from radio_acquisition_fixture import LocalFixtureStore

ROOT = Path(__file__).resolve().parents[1]
TOTAL = {"max_requests": 6, "max_bytes": 200, "max_seconds": 60}
SESSION = {"max_requests": 3, "max_bytes": 100, "max_seconds": 30}
URL = "https://fixture.invalid/synthetic-object.h5"
EVIDENCE = {}


class Response(io.BytesIO):
    def __init__(self, data=b"", *, status=200, headers=None):
        super().__init__(data)
        self.status = status
        self.headers = headers or {"Content-Length": "1000", "ETag": '"fixture"', "Accept-Ranges": "bytes"}
        self.body_reads = 0

    def geturl(self):
        return URL

    def read(self, n=-1):
        self.body_reads += 1
        return super().read(n)


class RadioAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = LocalFixtureStore.create(self.root/"durable-store",
            acquisition.genesis("1"*64, "2"*64, TOTAL))
        self.clock = [100.]

    def tearDown(self):
        self.temp.cleanup()

    def start(self, name="session", *, store=None, session_limits=SESSION):
        store = store or self.store
        checkpoint = store.read()
        budget = acquisition.start_session(store, expected_revision=checkpoint.revision,
            expected_ledger_sha256=checkpoint.sha256, session_limits=session_limits,
            directory=self.root/name, clock=lambda: self.clock[0])
        self.addCleanup(budget.journal.close)
        budget.bind_scope({"scan": "epoch1_on", "window": "engineering", "url": URL})
        return budget

    def evidence(self, name, budget):
        checkpoint = self.store.read()
        replay = acquisition.read_journal(budget.journal.path, expected_head=budget.journal.head,
                                          expected_reservation=budget.reservation)
        EVIDENCE[name] = {"ledger": checkpoint.document, "ledger_sha256": checkpoint.sha256,
            "revision": checkpoint.revision, "budget": budget.record(), "replay": replay,
            "journal_text": budget.journal.path.read_text(), "telescope_requests": 0}
        return replay

    def test_write_ahead_real_transport_and_source_identity_failure(self):
        budget = self.start()
        calls = []
        def head(request, timeout):
            replay = acquisition.read_journal(budget.journal.path, expected_head=budget.journal.head,
                                              expected_reservation=budget.reservation)
            self.assertEqual(replay["reserved_attempts"], 1)
            self.assertEqual(len(self.store.read().document["reservations"]), 1)
            calls.append(request.get_method())
            return Response()
        with patch.object(transport, "open_response", side_effect=head):
            identity = transport.live_identity(URL, budget)
        mirror = transport.RadioMirror(self.root/"mirror", identity, budget)
        headers = {"Content-Range": "bytes 10-13/1000", "ETag": '"fixture"',
                   "Content-Length": "4", "Content-Encoding": "identity"}
        def get(request, timeout):
            replay = acquisition.read_journal(budget.journal.path, expected_head=budget.journal.head,
                                              expected_reservation=budget.reservation)
            self.assertEqual((replay["reserved_attempts"], replay["reserved_bytes"]), (2, 5))
            calls.append(request.get_method())
            return Response(b"abcd", status=206, headers=headers)
        with patch.object(transport, "open_response", side_effect=get):
            self.assertEqual(mirror._request(ranges.ByteRange(10, 14)), b"abcd")
        bad = Response(b"abcd", status=206, headers={**headers, "ETag": '"changed"'})
        with patch.object(transport, "open_response", return_value=bad):
            with self.assertRaisesRegex(ValueError, "mismatch before body"):
                mirror._request(ranges.ByteRange(10, 14))
        self.assertEqual(bad.body_reads, 0)
        mirror.close()
        budget.close("error")
        replay = self.evidence("transport", budget)
        self.assertEqual(calls, ["HEAD", "GET"])
        self.assertEqual((replay["reserved_attempts"], replay["reserved_bytes"], replay["accepted_bytes"]), (3, 10, 4))

    def test_workspace_loss_cannot_restore_quota_or_reopen_old_lease(self):
        first = self.start("workspace-one")
        first.reserve(41)
        old_checkpoint, old_reservation = first.checkpoint, first.reservation
        first.journal.close()  # abrupt process loss: no completion event
        shutil.rmtree(self.root/"workspace-one")
        # The independent durable store survives. A fresh process must debit another whole session.
        restored = LocalFixtureStore(self.root/"durable-store")
        second = self.start("workspace-two", store=restored)
        second.reserve(11)
        second.accepted_bytes += 10
        second.close("completed")
        replay = self.evidence("restart", second)
        state = acquisition.validate_ledger(restored.read().document, restored.read().sha256)
        self.assertEqual(state["charged_limits"], TOTAL)
        self.assertEqual(state["remaining_limits"], {k: 0 for k in TOTAL})
        with self.assertRaisesRegex(ValueError, "cumulative reservation budget exhausted"):
            self.start("third", store=restored)
        with self.assertRaisesRegex(ValueError, "newly published reservation"):
            acquisition.DurableBudget(old_checkpoint, old_reservation, self.root/"reused")
        self.assertTrue(replay["reservation_remains_fully_charged"])

    def test_uncertain_publication_is_charged_and_never_activates(self):
        store = self.store
        real = store.publish
        def uncertain(*args):
            real(*args)
            raise OSError("publication landed but acknowledgment was lost")
        with patch.object(store, "publish", side_effect=uncertain):
            with self.assertRaisesRegex(OSError, "acknowledgment"):
                self.start("never-active")
        self.assertFalse((self.root/"never-active").exists())
        self.assertEqual(len(store.read().document["reservations"]), 1)
        second = self.start("next-process")
        second.close("interrupted")
        self.evidence("uncertain_publication", second)
        with self.assertRaisesRegex(ValueError, "cumulative"):
            self.start("overdrawn")

    def test_conflict_and_false_publication_ack_fail_before_transport(self):
        initial = self.store.read()
        first = self.start("first")
        with self.assertRaisesRegex(ValueError, "revision changed"):
            acquisition.start_session(self.store, expected_revision=initial.revision,
                expected_ledger_sha256=initial.sha256, session_limits=SESSION, directory=self.root/"stale")
        self.assertFalse((self.root/"stale").exists())
        with patch.object(self.store, "publish", return_value=None):
            with self.assertRaisesRegex(ValueError, "publication not confirmed"):
                self.start("false-ack")
        first.close("completed")
        self.evidence("publication_conflict", first)

    def test_journal_corruption_rollback_and_torn_tail_rejected(self):
        budget = self.start()
        budget.reserve(6)
        budget.accepted_bytes += 5
        budget.close("completed")
        original = budget.journal.path.read_bytes()
        variants = [original[:-2], b"\n".join(original.splitlines()[:-1])+b"\n",
                    original.replace(b'"reserved_bytes":6', b'"reserved_bytes":5')]
        for payload in variants:
            budget.journal.path.write_bytes(payload)
            with self.assertRaises((ValueError, json.JSONDecodeError)):
                acquisition.read_journal(budget.journal.path, expected_head=budget.journal.head,
                                         expected_reservation=budget.reservation)
        budget.journal.path.write_bytes(original)
        wrong = copy.deepcopy(budget.reservation)
        wrong["reserved_limits"]["max_bytes"] -= 1
        with self.assertRaisesRegex(ValueError, "reservation changed"):
            acquisition.read_journal(budget.journal.path, expected_head=budget.journal.head, expected_reservation=wrong)
        self.evidence("journal_integrity", budget)

    def test_session_limits_and_failed_write_stop_before_http(self):
        budget = self.start()
        budget.reserve(100)
        with patch.object(transport, "open_response", side_effect=AssertionError("HTTP opened")) as opened:
            mirror = transport.RadioMirror(self.root/"mirror", ranges.RemoteIdentity(URL, 1000, '"fixture"'), budget)
            with self.assertRaisesRegex(ValueError, "request/byte budget"):
                mirror._request(ranges.ByteRange(0, 1))
            mirror.close()
            self.clock[0] += 31
            with self.assertRaisesRegex(ValueError, "time budget"):
                transport.live_identity(URL, budget)
            opened.assert_not_called()
        budget.close("error")
        self.evidence("limits", budget)
        other = self.start("write-fault")
        with patch.object(acquisition.os, "fsync", side_effect=OSError("disk failure")):
            with patch.object(transport, "open_response", side_effect=AssertionError("HTTP opened")) as opened:
                with self.assertRaisesRegex(OSError, "disk failure"):
                    transport.live_identity(URL, other)
                opened.assert_not_called()
        with self.assertRaisesRegex(ValueError, "journal failed"):
            other.reserve(0)

    def test_request_count_and_invalid_acceptance_cannot_be_reset(self):
        budget = self.start()
        budget.reserve(2)
        budget.accepted_bytes += 1
        with self.assertRaisesRegex(ValueError, "reservation"):
            budget.accepted_bytes += 1
        budget.reserve(0)
        with self.assertRaisesRegex(ValueError, "reservation"):
            budget.accepted_bytes += 1
        budget.reserve(0)
        with patch.object(transport, "open_response", side_effect=AssertionError("HTTP opened")) as opened:
            with self.assertRaisesRegex(ValueError, "request/byte budget"):
                transport.live_identity(URL, budget)
            opened.assert_not_called()
        budget.close("completed")
        self.evidence("request_cap", budget)

    def test_ledger_chain_changed_contract_and_invalid_limits_rejected(self):
        budget = self.start()
        checkpoint = self.store.read()
        for field, value in (("contract_sha256", "3"*64), ("source_inventory_sha256", "4"*64)):
            changed = copy.deepcopy(checkpoint.document)
            changed[field] = value
            with self.assertRaisesRegex(ValueError, "independent checkpoint"):
                acquisition.validate_ledger(changed, checkpoint.sha256)
        changed = copy.deepcopy(checkpoint.document)
        changed["reservations"][0]["prior_ledger_sha256"] = "f"*64
        with self.assertRaisesRegex(ValueError, "order, parent or identity"):
            acquisition.validate_ledger(changed, acquisition.digest(changed))
        for value in (float("nan"), float("inf"), True, -1, 0):
            with self.assertRaises(ValueError):
                acquisition.genesis("1"*64, "2"*64, {**TOTAL, "max_seconds": value})
        budget.close("completed")
        self.evidence("ledger_integrity", budget)

    def test_hd1461_hold_before_store_access_or_spectral_access(self):
        path = "config/radio_hd1461_source_preparation_20260926.json"
        with patch.object(self.store, "read", side_effect=AssertionError("store opened")) as read:
            with self.assertRaisesRegex(ValueError, "source contract blocked"):
                acquisition.start_source_session(ROOT, path, rows.file_hash(ROOT/path), self.store,
                    expected_revision="unknown", expected_ledger_sha256="0"*64,
                    directory=self.root/"blocked", spectral_access_authorized=True)
            read.assert_not_called()
        self.assertFalse((self.root/"blocked").exists())


if __name__ == "__main__":
    unittest.main()
