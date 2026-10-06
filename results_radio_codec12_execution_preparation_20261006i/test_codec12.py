"""Concrete codec12 source/order/custody regressions; no native execution."""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import contract
import codec12_control as control
import preflight

ROOT = HERE.parent


def fake_rows(handoff=0):
    """Typed metadata stubs only. These hashes describe no actual payload."""
    return [{"row": i, "selected_cells": 65536,
             "compressed_bytes": 1, "compressed_sha256": "4" * 64, "full_decoded_sha256": "5" * 64,
             "native_descending_sha256": hashlib.sha256(f"stub-raw-{handoff}-{i}".encode()).hexdigest(),
             "ascending_raw_sha256": "2" * 64, "normalized_sha256": "3" * 64} for i in range(16)]


class InputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = contract.verify_inputs(ROOT)

    def test_original_bytes_and_all12_context_bindings(self):
        inputs = self.inputs
        contexts = contract.verify_receiver_contexts(inputs)
        self.assertEqual(list(contexts), ["calibration", "validation"])
        self.assertEqual(len(inputs["contents"]), 14)
        self.assertEqual(inputs["authority_bytes"], 632453)
        self.assertEqual(contexts["calibration"]["context_sha256"], "8899f84c7e9721e79627a4ec7166b7c941127a50f6ed5cb2d771f2c8518feb13")
        self.assertEqual(contexts["validation"]["context_sha256"], "304e30cc6eab0f1f88a633021a115e3dd281e223d2549988b64e60918f8b4eb6")

    def test_H_plan_cannot_be_rewritten_ready(self):
        raws = dict(self.inputs["h_raws"])
        plan = copy.deepcopy(self.inputs["plan"])
        plan["execution_enabled"] = True
        raws["PLAN.json"] = contract.canonical(plan)
        with self.assertRaisesRegex(ValueError, "immutable H"):
            contract.inspect_documents(raws)

    def test_H_missing_or_extra_document_denied(self):
        for mutation in (lambda r: r.pop("SELECTED_CODE.json"), lambda r: r.update({"extra": b"x"})):
            raws = dict(self.inputs["h_raws"]); mutation(raws)
            with self.assertRaises(ValueError):
                contract.inspect_documents(raws)

    def test_all_handoff_order_scan_and_boolean_mutations_denied(self):
        for index in range(12):
            for key, value in (("handoff_index", True), ("role", "pilot"), ("scan", "epoch1_on" if index % 6 else "epoch1_off")):
                inputs = copy.deepcopy(self.inputs)
                inputs["plan"]["scope"]["ordered_handoffs"][index][key] = value
                with self.subTest(index=index, key=key), self.assertRaises(ValueError):
                    contract.verify_receiver_contexts(inputs)

    def test_role_context_or_bank_transplant_denied(self):
        for key in ("receiver_context_sha256", "receiver_bank_sha256"):
            inputs = copy.deepcopy(self.inputs)
            inputs["plan"]["scope"]["ordered_handoffs"][6][key] = inputs["plan"]["scope"]["ordered_handoffs"][0][key]
            with self.assertRaises(ValueError):
                contract.verify_receiver_contexts(inputs)

    def test_input_read_path_escape_symlink_and_hardlink_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / "a").write_bytes(b"a")
            (root / "link").symlink_to(root / "a")
            (root / "directory").mkdir(); (root / "directory" / "a").write_bytes(b"a")
            (root / "alias").symlink_to(root / "directory", target_is_directory=True)
            for relative in ("../a", "/a", "directory/../a", "link", "alias/a"):
                with self.subTest(relative=relative), self.assertRaises(ValueError):
                    contract.read(root, relative)
            os.link(root / "a", root / "hardlink")
            with self.assertRaises(ValueError):
                contract.read(root, "a")

    def test_held_file_identity_mutation_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path = root / "a"; path.write_bytes(b"abc")
            real = os.fstat; calls = []
            def modified(fd):
                value = real(fd); calls.append(fd)
                if len(calls) == 2:
                    os.replace(path, root / "old")
                    path.write_bytes(b"abc")
                return value
            with patch.object(contract.os, "fstat", side_effect=modified), self.assertRaises(ValueError):
                contract.read(root, "a")

    def test_memory_module_never_reopens_changed_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.py"; path.write_bytes(b'raise ValueError("disk reopen")\n')
            name = "_codec12_test_memory"
            try:
                module = contract.load_memory(name, b'answer = "authenticated memory"\n', path)
                self.assertEqual(module.answer, "authenticated memory")
                with self.assertRaises(ValueError):
                    contract.load_memory(name, b"answer=0\n", path)
            finally:
                sys.modules.pop(name, None)

    def test_duplicate_nonfinite_and_boolean_external_pin_denied(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            with self.assertRaises(ValueError):
                contract.parse(raw)
        with self.assertRaises(ValueError):
            contract.authenticate(b"1", {"bytes": True, "sha256": contract.sha(b"1")})

    def test_H_laws_integrate_from_memory_without_reopen(self):
        with patch.object(Path, "read_bytes", side_effect=AssertionError("unverified reopen")):
            _, observation = control._metadata_laws(self.inputs)
        self.assertEqual(observation["case_count"], 22)
        self.assertEqual(observation["payload_index_attempts"], 0)

    def test_wrong_expected_law_cannot_tune_to_pass(self):
        inputs = copy.deepcopy(self.inputs)
        inputs["plan"]["case_laws"][4]["expected"] = "accept"
        with self.assertRaises(ValueError):
            control._metadata_laws(inputs)

    def test_public_dispatch_denied_before_any_output_or_native_call(self):
        with patch.object(control, "_run_after_outer_admission", side_effect=AssertionError("native call")):
            for dispatch in (None, {"ready": True}, {"engineering_execution_authorized": True}):
                with self.assertRaisesRegex(ValueError, "BLOCKED"):
                    control.produce(self.inputs, Path("not-created"), dispatch=dispatch)
        self.assertFalse((HERE / "not-created").exists())
        self.assertTrue(all(name not in sys.modules for name in ("numpy", "h5py", "hdf5plugin")))

    def test_preflight_keeps_all_execution_gates_closed(self):
        result = preflight.inspect(ROOT)
        self.assertEqual(result["status"], "BLOCKED_PENDING_OUTER_NATIVE_LIFETIME")
        self.assertEqual(len(result["missing_before_activation"]), 4)
        self.assertFalse(result["source_freeze_is_live_execution_freeze"])
        self.assertEqual(result["control_dispatches"], 0)


class ReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = contract.verify_inputs(ROOT)["plan"]

    def records(self):
        return [{"scope": scope, "rows": fake_rows(i), "handoff": control.handoff_receipt(scope, fake_rows(i)),
                 "encoder_pipeline": [[32008, 1, [0, 4, 4, 0, 2]]], "legacy_pipeline": [[32008, 1, [0, 3, 4, 0, 2]]],
                 "files": [{"name": name, "bytes": 1, "allocated_bytes_snapshot": 4096, "sha256": "6" * 64}
                           for name in ("encoder.h5", "legacy.h5")]}
                for i, scope in enumerate(self.plan["scope"]["ordered_handoffs"])]

    def test_exact12_order_accepted_in_metadata_domain_only(self):
        control.validate_complete_receipts(self.plan, self.records())

    def test_missing_duplicate_or_reordered_handoffs_denied(self):
        records = self.records()
        for mutation in (records[:-1], records + [records[0]], records[::-1], [records[0]] * 12):
            with self.assertRaises(ValueError):
                control.validate_complete_receipts(self.plan, mutation)

    def test_incomplete_reordered_boolean_and_bad_row_hash_denied(self):
        rows = fake_rows()
        for mutation in (rows[:-1], rows[::-1], [{**rows[0], "row": False}] + rows[1:],
                         [{**rows[0], "native_descending_sha256": "not a hash"}] + rows[1:]):
            with self.assertRaises(ValueError):
                control.validate_row_receipts(mutation)

    def test_role_bank_or_raw_hash_receipt_mutation_denied(self):
        for key in ("role", "receiver_bank_sha256", "raw_row_sha256s"):
            records = self.records(); records[6]["handoff"][key] = records[0]["handoff"][key]
            with self.assertRaises(ValueError):
                control.validate_complete_receipts(self.plan, records)

    def test_repeated_controlled_raw_rows_denied(self):
        records = self.records()
        for record in records:
            record["rows"] = fake_rows(0); record["handoff"] = control.handoff_receipt(record["scope"], record["rows"])
        with self.assertRaisesRegex(ValueError, "distinct"):
            control.validate_complete_receipts(self.plan, records)

    def test_normalized_hash_repetition_is_not_scientific_disjointness(self):
        # Additive handoff salt can be removed by centering. Only raw sets must
        # be distinct; no new scientific panel identity is inferred from either.
        records = self.records()
        self.assertEqual(len({tuple(r["handoff"]["normalized_row_sha256s"]) for r in records}), 1)
        control.validate_complete_receipts(self.plan, records)

    def test_file_pipeline_bool_size_and_name_mutations_denied(self):
        for mutate in (lambda r: r.update({"legacy_pipeline": []}),
                       lambda r: r["files"][0].update({"bytes": True}),
                       lambda r: r["files"][0].update({"name": "wrong.h5"}),
                       lambda r: r["files"][0].update({"allocated_bytes_snapshot": 17 * 1024**2}),
                       lambda r: r["rows"][0].update({"compressed_bytes": True})):
            records = self.records(); mutate(records[0])
            with self.assertRaises(ValueError): control.validate_complete_receipts(self.plan, records)

    def success_journal(self, path, records, result):
        journal = control.EventJournal(path)
        journal.append("started", {"engineering_only": True})
        for record in records:
            scope = record["scope"]; journal.append("handoff_started", scope)
            for phase in ("encoded", "transferred", "row_verified"):
                for i, row in enumerate(record["rows"]):
                    value = {"handoff_index": scope["handoff_index"], "row": i}
                    if phase == "row_verified": value.update(row)
                    journal.append(phase, value)
            journal.append("handoff_complete", {"handoff_index": scope["handoff_index"], "receipt_sha256": contract.sha(contract.canonical(record))})
        journal.append("completed", {"receipt_sha256": contract.sha(contract.canonical(result)), "handoffs_observed": 12})
        journal.close()
        return path.read_bytes()

    def test_success_journal_requires_all602_events_and_terminal_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            records = self.records(); result = {"domain": "metadata_stub_only"}
            raw = self.success_journal(Path(tmp) / "journal", records, result)
            self.assertEqual(control.verify_success_journal(raw, self.plan, records, result)["events"], 602)
            prefix = b"\n".join(raw.splitlines()[:-1]) + b"\n"
            self.assertEqual(len(control.verify_journal(prefix)), 601)
            with self.assertRaises(ValueError): control.verify_success_journal(prefix, self.plan, records, result)
            with self.assertRaises(ValueError): control.verify_success_journal(raw, self.plan, records, {"different": True})

    def test_success_journal_rejects_rehashed_phase_substitution(self):
        with tempfile.TemporaryDirectory() as tmp:
            records = self.records(); result = {"domain": "metadata_stub_only"}
            raw = self.success_journal(Path(tmp) / "original", records, result)
            events = control.verify_journal(raw)
            events[3]["phase"] = "row_verified"
            journal = control.EventJournal(Path(tmp) / "changed")
            for event in events: journal.append(event["phase"], event["value"])
            journal.close()
            with self.assertRaises(ValueError): control.verify_success_journal((Path(tmp) / "changed").read_bytes(), self.plan, records, result)


class CustodyTests(unittest.TestCase):
    def test_compressed_size_and_mask_veto_precede_payload_callback(self):
        for size, mask in ((6 * 1024**2, 0), (0, 0), (True, 0), (1, 1), (1, False)):
            calls = []
            fake = SimpleNamespace(get_chunk_info_by_coord=lambda _: SimpleNamespace(size=size, filter_mask=mask),
                                   read_direct_chunk=lambda _: calls.append("payload"))
            with self.subTest(size=size, mask=mask), self.assertRaises(ValueError):
                control.read_filtered_chunk(fake, (0, 0, 159 * 1048576), 5 * 1024**2)
            self.assertEqual(calls, [])

    def test_compressed_expected_length_veto_precedes_payload_callback(self):
        calls = []
        fake = SimpleNamespace(get_chunk_info_by_coord=lambda _: SimpleNamespace(size=2, filter_mask=0),
                               read_direct_chunk=lambda _: calls.append("payload"))
        with self.assertRaises(ValueError):
            control.read_filtered_chunk(fake, (0, 0, 0), 10, {"compressed_bytes": 1, "compressed_sha256": "0" * 64})
        self.assertEqual(calls, [])

    def test_compressed_retained_hash_and_short_body_veto(self):
        fake = SimpleNamespace(get_chunk_info_by_coord=lambda _: SimpleNamespace(size=2, filter_mask=0),
                               read_direct_chunk=lambda _: (0, b"x"))
        with self.assertRaises(ValueError): control.read_filtered_chunk(fake, (0, 0, 0), 10)
        fake.read_direct_chunk = lambda _: (0, b"xx")
        with self.assertRaises(ValueError):
            control.read_filtered_chunk(fake, (0, 0, 0), 10, {"compressed_bytes": 2, "compressed_sha256": "0" * 64})
        self.assertEqual(control.read_filtered_chunk(fake, (0, 0, 0), 10,
                         {"compressed_bytes": 2, "compressed_sha256": contract.sha(b"xx")}), b"xx")

    def test_journal_fsync_chain_and_exclusive_second_use(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "journal"
            journal = control.EventJournal(path)
            journal.append("started", {"engineering_only": True})
            journal.append("transferred", {"row": 0})
            journal.close()
            events = control.verify_journal(path.read_bytes())
            self.assertEqual(len(events), 2)
            with self.assertRaises(FileExistsError):
                control.EventJournal(path)
            with self.assertRaises(ValueError):
                journal.append("replay", {})

    def test_journal_cap_refusal_retains_previous_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "journal"; journal = control.EventJournal(path, cap=500)
            journal.append("one", {})
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                journal.append("too-large", {"x": "x" * 1000})
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(journal.sequence, 1)
            journal.close()

    def test_journal_tamper_truncation_reorder_and_boolean_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "journal"; journal = control.EventJournal(path)
            for i in range(2): journal.append("row", {"row": i})
            journal.close(); raw = path.read_bytes(); lines = raw.splitlines(keepends=True)
            event = json.loads(lines[0]); event["sequence"] = False
            event["event_sha256"] = contract.sha(contract.canonical({k: v for k, v in event.items() if k != "event_sha256"}))
            for mutation in (raw[:-1], b"".join(lines[::-1]), raw.replace(b'"row":0', b'"row":9'), contract.canonical(event)):
                with self.assertRaises(ValueError):
                    control.verify_journal(mutation)

    def test_journal_external_replacement_denied_without_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "journal"; journal = control.EventJournal(path)
            journal.append("one", {}); os.rename(path, Path(tmp) / "retained-original")
            path.write_bytes(b"replacement")
            with self.assertRaises(ValueError):
                journal.append("two", {})
            journal.close()
            self.assertEqual(path.read_bytes(), b"replacement")
            self.assertTrue((Path(tmp) / "retained-original").is_file())

    def test_partial_write_failure_is_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "failure.json"; real_write = os.write; calls = []
            def broken(fd, data):
                calls.append(fd)
                if len(calls) == 1: return real_write(fd, data[:3])
                raise OSError("injected write failure")
            with patch.object(control.os, "write", side_effect=broken), self.assertRaises(OSError):
                control.write_json_new(path, {"value": "retained"})
            self.assertEqual(path.read_bytes(), b'{"v')
            with self.assertRaises(FileExistsError):
                control.write_json_new(path, {"value": "retry"})

    def test_short_writes_are_fully_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "new.json"; real_write = os.write
            with patch.object(control.os, "write", side_effect=lambda fd, data: real_write(fd, data[:3])):
                pin = control.write_json_new(path, {"value": "complete"})
            self.assertEqual(path.read_bytes(), contract.canonical({"value": "complete"}))
            self.assertEqual(pin["sha256"], contract.sha(path.read_bytes()))

    def test_receipt_cap_denied_before_file_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "no-file"
            with self.assertRaises(ValueError):
                control.write_json_new(path, {"too_large": "x" * 100}, maximum=10)
            self.assertFalse(path.exists())

    def test_storage_counts_directories_and_refuses_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); file = root / "a"; file.write_bytes(b"abc")
            with self.assertRaises(ValueError): control.storage_snapshot(root, 3)
            original = control.storage_snapshot(root, 1024**2)
            self.assertGreater(original["logical_bytes"], 3)
            (root / "sym").symlink_to(file)
            with self.assertRaises(ValueError): control.storage_snapshot(root, 1024**2)
            (root / "sym").unlink()  # Test fixture only, never historical evidence.
            os.link(file, root / "alias")
            with self.assertRaises(ValueError): control.storage_snapshot(root, 1024**2)

    def test_output_freshness_inside_source_and_symlink_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / "source"; source.mkdir()
            control._output_path(root / "fresh", source)
            (root / "alias").symlink_to(source, target_is_directory=True)
            for output in (source / "inside", source, root / "alias" / "new", Path("relative")):
                with self.assertRaises(ValueError): control._output_path(output, source)

    def test_output_file_pin_detects_replacement_during_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a"; path.write_bytes(b"original"); real = os.fstat; calls = []
            def changed(fd):
                st = real(fd); calls.append(fd)
                if len(calls) == 2:
                    os.replace(path, Path(tmp) / "original"); path.write_bytes(b"replaced")
                return st
            with patch.object(control.os, "fstat", side_effect=changed), self.assertRaises(ValueError):
                control.file_pin(path, 1024**2)

    def test_native_imports_only_in_uninvoked_private_body(self):
        tree = ast.parse((HERE / "codec12_control.py").read_bytes())
        body = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_run_after_outer_admission")
        names = {a.name for node in ast.walk(body) if isinstance(node, ast.Import) for a in node.names}
        self.assertTrue({"numpy", "h5py", "hdf5plugin"} <= names)
        for node in tree.body:
            if isinstance(node, ast.Import):
                self.assertFalse(any(a.name in ("numpy", "h5py", "hdf5plugin") for a in node.names))
        self.assertTrue(all(name not in sys.modules for name in ("numpy", "h5py", "hdf5plugin")))


if __name__ == "__main__":
    unittest.main()
