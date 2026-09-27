"""Changed-risk checks for codec/direct ancestry and v2 publication transitions."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import numpy as np

from seti_repeater import acquisition_radio as acquisition
from seti_repeater import codec_direct_radio as adapter
from seti_repeater import execution_envelope_radio as envelope
from seti_repeater import factors_radio as direct
from seti_repeater import pipeline_direct_radio as pipeline
from seti_repeater import publication_role_radio as publication
from seti_repeater import search_v0p6 as core
from seti_repeater import source_m43h as rows
from seti_repeater import transport_radio as net
from seti_repeater import transfer_m43g as native
from m43g_reference import sorted_reference, direct_reference
from radio_codec_publication_fixture import ROOT, prepare


class CodecDirectTests(unittest.TestCase):
    evidence = {}
    replay_simulated_calls = 0
    replay_encoded_bytes = 0

    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.fixtures = {name: prepare(Path(cls.temporary.name) / name, name)
                        for name in ("gzip", "bitshuffle_lz4")}

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_codec_receipts_reach_direct_score_store_bit_exact(self):
        for name, f in self.fixtures.items():
            with self.subTest(codec=name):
                with patch.object(net, "open_response", side_effect=AssertionError("network forbidden")) as opened:
                    run = adapter.fixture_run(f["context"], f["binding"], f["directories"])
                    opened.assert_not_called()
                sources = run.sources
                store = run.build_store()
                records = []; normalized_cells = 0; score_cells = 0
                for scan in f["context"].scans:
                    label = scan["label"]
                    reference = sorted_reference(np.ascontiguousarray(f["raw"][label][:, ::-1]))
                    self.assertTrue(np.array_equal(sources[label].values.view("<u4"), reference.view("<u4")))
                    normalized_cells += reference.size
                    self.assertFalse(sources[label].values.flags.writeable)
                    scope = json.loads(sources[label].scope_json)
                    self.assertEqual(scope["codec_receipt_sha256"], f["receipts"][label]["receipt_sha256"])
                    for width in core.M37_SPECTRAL_WIDTHS:
                        expected = direct_reference(reference, f["geometry"],
                            direct.for_scan(f["bank"], label), f["context"].grid,
                            width, 0, f["context"].grid.support_bin_count)
                        actual = np.stack([store.arrays[(scan["kind"], t, width)][scan["epoch"]-1]
                                           for t in range(f["bank"].template_count)])
                        self.assertTrue(np.array_equal(actual.view("<u4"), expected.view("<u4")))
                        score_cells += actual.size
                        records.append({"scan": label, "width": width,
                            "score_sha256": native.array_hash(actual),
                            "oracle_sha256": native.array_hash(expected),
                            "shape": list(actual.shape)})
                self.evidence[name] = {"manifest": f["manifest"],
                    "manifest_sha256": f["binding"].identity,
                    "codec_receipts": f["receipts"], "transports": f["transports"],
                    "direct_bank": {"identity": f["bank"].identity, "record": f["bank"].record()},
                    "source_ids": run.source_ids, "score_provenance": store.provenance,
                    "score_comparisons": records, "normalized_cells_bit_exact": normalized_cells,
                    "score_cells_bit_exact": score_cells, "real_network_requests": 0,
                    "scientific_evaluation": False}

    def test_trusted_manifest_hash_is_not_self_selected(self):
        f = self.fixtures["gzip"]
        with self.assertRaisesRegex(ValueError, "binding changed"):
            adapter.bind(f["manifest"], "0"*64, f["bank"])

    def test_generated_codec_receipts_replay_without_old_scratch_paths(self):
        with tempfile.TemporaryDirectory() as td:
            replay = prepare(Path(td), "gzip")
            original = self.fixtures["gzip"]
            self.assertEqual(replay["binding"].identity, original["binding"].identity)
            self.assertEqual(replay["receipts"], original["receipts"])
            type(self).replay_simulated_calls = sum(len(t["simulated_calls"]) for t in replay["transports"].values())
            type(self).replay_encoded_bytes = sum(t["input_hdf5_bytes"] for t in replay["transports"].values())

    def test_cadence_window_inventory_and_memory_stop_before_native_reads(self):
        f = self.fixtures["gzip"]
        for fault in ("window", "inventory", "memory"):
            context = pipeline.Context(scans=f["context"].scans, factors=f["bank"],
                grid=f["context"].grid,
                window=f["context"].window + ("-changed" if fault == "window" else ""),
                memory_limit_bytes=1 if fault == "memory" else 256*1024**2)
            directories = dict(f["directories"])
            if fault == "inventory": directories.pop("epoch3_off")
            with self.subTest(fault=fault), patch.object(np, "load", side_effect=AssertionError("row opened")) as loaded:
                with self.assertRaises((ValueError, core.V0P6CapacityError)):
                    adapter.fixture_run(context, f["binding"], directories)
                loaded.assert_not_called()

    def test_mixed_codec_cadence_does_not_reach_scoring(self):
        f = self.fixtures["gzip"]; directories = dict(f["directories"])
        directories["epoch2_on"] = self.fixtures["bitshuffle_lz4"]["directories"]["epoch2_on"]
        with patch.object(pipeline.NativeRun, "build_store", side_effect=AssertionError("scoring reached")) as scored:
            with self.assertRaisesRegex(ValueError, "trusted fixture binding"):
                adapter.fixture_run(f["context"], f["binding"], directories)
            scored.assert_not_called()

    def test_telescope_kind_and_real_url_rejected_before_arrays(self):
        f = self.fixtures["gzip"]
        for field in ("kind", "url"):
            with self.subTest(field=field), patch.object(np, "load", side_effect=AssertionError("row opened")) as loaded:
                manifest = copy.deepcopy(f["manifest"])
                scope = manifest["scans"][0]["scope"]
                if field == "kind": scope["kind"] = "telescope-remote"
                else: scope["definition"]["url"] = "https://archive.example/file.h5"
                with self.assertRaisesRegex(ValueError, "local fixture"):
                    adapter.bind(manifest, native.digest(manifest), f["bank"])
                loaded.assert_not_called()

    def test_swapped_scan_or_codec_receipt_rejected_before_arrays(self):
        f = self.fixtures["gzip"]
        for directory in (f["directories"]["epoch1_off"],
                          self.fixtures["bitshuffle_lz4"]["directories"]["epoch1_on"]):
            with self.subTest(directory=str(directory)), patch.object(np, "load", side_effect=AssertionError("row opened")) as loaded:
                with self.assertRaisesRegex(ValueError, "trusted fixture binding"):
                    adapter.adapt_fixture(directory, f["binding"], f["bank"], "epoch1_on")
                loaded.assert_not_called()

    def test_normalization_origin_window_and_manifest_order_cannot_drift(self):
        f = self.fixtures["gzip"]
        for fault in ("origin", "window", "order"):
            with self.subTest(fault=fault):
                m = copy.deepcopy(f["manifest"])
                if fault == "origin": m["scans"][0]["scope"]["archive_interval"][0] += 1
                if fault == "window": m["window"] += "-changed"
                if fault == "order": m["scans"].reverse()
                with self.assertRaises(ValueError):
                    adapter.bind(m, native.digest(m), f["bank"])

    def test_runtime_and_factor_bank_cannot_be_substituted(self):
        f = self.fixtures["gzip"]
        for key in ("runtime", "direct_factor_bank_sha256"):
            m = copy.deepcopy(f["manifest"])
            if key == "runtime": m[key]["h5py"] = "wrong"
            else: m[key] = "0"*64
            with self.subTest(key=key), self.assertRaises(ValueError):
                adapter.bind(m, native.digest(m), f["bank"])

    def test_coherent_new_bank_still_requires_matching_header_clock_and_contract(self):
        f = self.fixtures["gzip"]
        for fault in ("clock", "contract"):
            data = json.loads(f["bank"].inputs_json)
            if fault == "clock":
                for row in data["clock_seconds"][16:]:
                    for j in range(3): row[j] += 1
            else: data["provenance"]["source_contract_sha256"] = "a"*64
            bank = direct.build(**data)
            m = copy.deepcopy(f["manifest"]); m["direct_factor_bank_sha256"] = bank.identity
            with self.subTest(fault=fault), self.assertRaisesRegex(ValueError, "clock differs|different source contract"):
                adapter.bind(m, native.digest(m), bank)

    def test_corrupt_native_row_is_rejected_without_silent_repair(self):
        f = self.fixtures["gzip"]
        path = f["directories"]["epoch1_on"] / "row00.native.npy"
        original = path.read_bytes()
        try:
            path.write_bytes(original[:-4] + b"XXXX")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                adapter.adapt_fixture(path.parent, f["binding"], f["bank"], "epoch1_on")
            self.assertEqual(path.read_bytes(), original[:-4] + b"XXXX")
        finally:
            path.write_bytes(original)

    def test_change_between_rehydrate_and_read_is_rejected(self):
        f = self.fixtures["gzip"]
        path = f["directories"]["epoch1_on"] / "row00.native.npy"
        original = path.read_bytes(); real = rows.rehydrate
        def changed(*args, **kwargs):
            receipt = real(*args, **kwargs)
            value = np.load(path, allow_pickle=False)
            value[0] += np.float32(1)
            np.save(path, value, allow_pickle=False)
            return receipt
        try:
            with patch.object(rows, "rehydrate", side_effect=changed):
                with self.assertRaisesRegex(ValueError, "changed after receipt"):
                    adapter.adapt_fixture(path.parent, f["binding"], f["bank"], "epoch1_on")
        finally:
            path.write_bytes(original)

    def test_transport_claim_cannot_be_promoted_by_resigning_receipt(self):
        f = self.fixtures["gzip"]; label = "epoch1_on"
        path = f["directories"][label] / "source.json"; original = path.read_bytes()
        receipt = json.loads(original); receipt["transport"]["kind"] = "live-identity-bound-http-ranges"
        receipt = rows.seal({k: v for k, v in receipt.items() if k != "receipt_sha256"})
        m = copy.deepcopy(f["manifest"]); m["scans"][0]["receipt_sha256"] = receipt["receipt_sha256"]
        try:
            rows.atomic_json(path, receipt)
            binding = adapter.bind(m, native.digest(m), f["bank"])
            with patch.object(np, "load", side_effect=AssertionError("row opened")) as loaded:
                with self.assertRaisesRegex(ValueError, "transport ancestry"):
                    adapter.adapt_fixture(path.parent, binding, f["bank"], label)
                loaded.assert_not_called()
        finally:
            path.write_bytes(original)


class PublicationTests(unittest.TestCase):
    evidence = {}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        cfg = json.loads((ROOT / "config/radio_execution_envelope_20260927.json").read_text())
        self.resource = envelope.build_resource_contract(cfg)
        self.genesis = self.resource.genesis()
        path = Path(self.temp.name) / "local-ledger.json"
        self.backend = envelope.LocalRoleStore.initialize(path, self.genesis)
        self.location = {"kind": "local-v2-qualification-only", "path": str(path.resolve())}
        self.protocol = publication.bind_local_protocol(self.location, self.resource, self.genesis)
        self.store = publication.BoundRoleStore(self.backend, self.protocol)

    def reserve(self, store=None, revision="0", document=None, role="calibration", index=1):
        return envelope.reserve_role(store or self.store, expected_revision=revision,
            expected_ledger_sha256=envelope.ledger_digest(document or self.genesis), role=role,
            session_id=f"00000000-0000-4000-8000-{index:012d}",
            created_utc="2026-09-27T08:00:00+00:00")

    def test_unguarded_primitive_reset_reproduces_new_boundary_risk(self):
        self.reserve()
        current = self.backend.read()
        self.backend.publish(current.revision, current.sha256, self.genesis)
        self.assertEqual(self.backend.read().document["reservations"], [])
        self.evidence["unguarded_primitive_reset_reproduced_locally"] = True

    def test_guard_refuses_reset_and_preserves_committed_reservation(self):
        self.reserve(); before = self.store.read()
        with self.assertRaisesRegex(ValueError, "append exactly one"):
            self.store.publish(before.revision, before.sha256, self.genesis)
        self.assertEqual(self.store.read(), before)

    def test_guard_refuses_consistent_namespace_rebinding(self):
        changed = copy.deepcopy(self.genesis); changed["resource_contract_sha256"] = "a"*64
        with self.assertRaisesRegex(ValueError, "append exactly one"):
            self.store.publish("0", envelope.ledger_digest(self.genesis), changed)
        self.assertEqual(self.store.read().document, self.genesis)

    def test_guard_refuses_replacing_existing_reservation(self):
        self.reserve(); before = self.store.read(); changed = copy.deepcopy(before.document)
        changed["reservations"][0]["session_id"] = "00000000-0000-4000-8000-000000000099"
        with self.assertRaisesRegex(ValueError, "append exactly one"):
            self.store.publish(before.revision, before.sha256, changed)
        self.assertEqual(self.store.read(), before)

    def test_wrong_store_location_rejected_before_publish(self):
        protocol = publication.bind_local_protocol({**self.location, "path": "/wrong/store.json"},
                                                   self.resource, self.genesis)
        wrong = publication.BoundRoleStore(self.backend, protocol)
        with self.assertRaisesRegex(ValueError, "location/revision"):
            self.reserve(wrong)
        self.assertEqual(self.backend.read().document, self.genesis)

    def test_consistent_wrong_genesis_is_not_accepted(self):
        changed = copy.deepcopy(self.genesis); changed["source_inventory_sha256"] = "b"*64
        with self.assertRaisesRegex(ValueError, "genesis differs"):
            publication.bind_local_protocol(self.location, self.resource, changed)

    def test_primitive_namespace_swap_is_detected_on_read(self):
        changed = copy.deepcopy(self.genesis); changed["source_inventory_sha256"] = "b"*64
        self.backend.publish("0", envelope.ledger_digest(self.genesis), changed)
        with self.assertRaisesRegex(ValueError, "namespace or local revision"):
            self.store.read()

    def test_concurrent_workers_same_parent_have_exactly_one_winner(self):
        barrier = threading.Barrier(2); outcomes = []
        def worker(index):
            try:
                barrier.wait(timeout=5)
                self.reserve(index=index)
                outcomes.append("reserved")
            except ValueError:
                outcomes.append("refused")
        workers = [threading.Thread(target=worker, args=(i,)) for i in (11, 12)]
        for worker in workers: worker.start()
        for worker in workers: worker.join(timeout=10)
        self.assertFalse(any(worker.is_alive() for worker in workers))
        self.assertCountEqual(outcomes, ["reserved", "refused"])
        self.assertEqual(len(self.store.read().document["reservations"]), 1)
        self.evidence["concurrent_same_parent_outcomes"] = sorted(outcomes)

    def test_lost_reply_is_spent_and_stale_retry_is_refused_by_bound_store(self):
        real = self.backend
        class LostReply:
            def read(self): return real.read()
            def publish(self, *args):
                real.publish(*args)
                raise RuntimeError("lost reply after durable CAS")
        store = publication.BoundRoleStore(LostReply(), self.protocol)
        with self.assertRaisesRegex(RuntimeError, "lost reply"):
            self.reserve(store)
        with self.assertRaisesRegex(ValueError, "checkpoint changed"):
            self.reserve(index=2)
        self.assertEqual(len(self.store.read().document["reservations"]), 1)
        self.evidence["lost_reply_remains_spent"] = True

    def test_wrong_confirmation_is_refused_without_refund(self):
        real = self.backend
        class ChangedConfirmation:
            published = False
            def read(self):
                cp = real.read()
                return replace(cp, location={**cp.location, "path": "/changed"}) if self.published else cp
            def publish(self, *args):
                real.publish(*args); self.published = True
        with self.assertRaisesRegex(ValueError, "location/revision"):
            self.reserve(publication.BoundRoleStore(ChangedConfirmation(), self.protocol))
        self.assertEqual(len(self.backend.read().document["reservations"]), 1)

    def test_ordered_three_roles_exhaust_once_with_no_network_budget(self):
        receipts = []
        for index, role in enumerate(envelope.EXPECTED_ROLES):
            before = self.store.read()
            receipts.append(self.reserve(revision=before.revision, document=before.document,
                                         role=role, index=index+1))
        last = self.store.read()
        with self.assertRaisesRegex(ValueError, "role out of order"):
            self.reserve(revision=last.revision, document=last.document, role="pilot", index=4)
        self.assertTrue(all(r["network_budget_issued"] is False for r in receipts))
        self.evidence["simulation_ledger"] = last.document
        self.evidence["simulation_audit"] = envelope.validate_resource_ledger(last.document, last.sha256)
        self.evidence["telescope_namespace_activated"] = False


if __name__ == "__main__":
    unittest.main()
