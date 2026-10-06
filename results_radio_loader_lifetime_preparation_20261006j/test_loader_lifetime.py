"""New source-only fixture tests; no kernel collector, target or native import."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("loader_lifetime_J", HERE / "loader_lifetime.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
PROCESS = {"local_pid": 6, "outer_pid": 58364, "starttime_ticks": 8396398,
           "namespace_device": 4, "namespace_inode": 4026532277}
FILES = {"/fixture/python": {"bytes": 100, "sha256": "a" * 64},
         "/fixture/transient.so": {"bytes": 200, "sha256": "b" * 64}}


def event(kind, payload):
    return {"kind": kind, "payload": payload}


def opening(oid, name, resolved):
    return event("object_open", {"object_id": oid, "namespace_id": 0,
                                "loader_name": name, "resolved_path": resolved,
                                "file_pin": copy.deepcopy(FILES[resolved])})


def fixture():
    return [event("handshake", {"source_freeze_sha256": module.SOURCE_FREEZE_SHA256,
                                "loader_interface_version": 2}),
            opening(1, "", "/fixture/python"),
            event("preinit", {"main_object_id": 1}),
            opening(2, "/fixture/transient.so", "/fixture/transient.so"),
            event("object_close", {"object_id": 2}),
            event("collector_end", {"event_loss_count": 0, "exit_code": 0})]


def bodies(events, identity=PROCESS):
    previous = module.ZERO
    raw = []
    for i, value in enumerate(events):
        item = {**value, "sequence": i, "previous_sha256": previous,
                "monotonic_ns": (i + 1) * 10, "process": copy.deepcopy(identity)}
        body = module.canonical(item)
        raw.append(body)
        previous = module.digest(body)
    return raw


def checked(events):
    ledger = module.LoaderLedger(PROCESS, "/fixture/python", FILES)
    for raw in bodies(events):
        ledger.consume(raw)
    return ledger.finish()


class LifetimeTests(unittest.TestCase):
    def rejected(self, events):
        with self.assertRaises(module.Refusal):
            checked(events)

    def test_transient_object_survives_equal_endpoint_snapshots(self):
        value = checked(fixture())
        self.assertEqual(value["live_at_terminal"], [1])
        self.assertEqual(value["transient_generations_retained"], 1)
        row = value["object_generations"][1]
        self.assertEqual((row["opened_event"], row["closed_event"]), (3, 4))
        self.assertEqual((row["opened_ns"], row["closed_ns"]), (40, 50))
        self.assertEqual(row["resolved_path"], "/fixture/transient.so")

    def test_source_check_never_certifies_a_live_runtime(self):
        value = checked(fixture())
        for key in ("collector_authentication", "continuous_file_custody", "full_syscall_or_loader_coverage",
                    "descendant_or_terminal_io_qualification", "runtime_qualified", "codec_certificate_issued",
                    "execution_authorized", "spectra_authorized"):
            self.assertIs(value[key], False)
        with self.assertRaises(module.Refusal):
            module.dispatch()

    def test_all_live_objects_remain_in_terminal_receipt(self):
        events = fixture(); del events[4]
        self.assertEqual(checked(events)["live_at_terminal"], [1, 2])

    def test_same_file_new_generation_retained_after_unload(self):
        events = fixture()
        events[5:5] = [opening(3, "/fixture/transient.so", "/fixture/transient.so")]
        value = checked(events)
        self.assertEqual(len(value["object_generations"]), 3)
        self.assertEqual(value["live_at_terminal"], [1, 3])

    def test_closed_object_id_cannot_be_reused(self):
        events = fixture(); events.insert(5, opening(2, "/fixture/transient.so", "/fixture/transient.so"))
        self.rejected(events)

    def test_empty_main_name_is_unique_and_executable_bound(self):
        for index in (1, 3):
            events = fixture(); events[index]["payload"]["loader_name"] = ""
            if index == 1: events[index]["payload"]["resolved_path"] = "/fixture/transient.so"
            self.rejected(events)

    def test_unknown_and_double_close_refused(self):
        events = fixture(); events[4]["payload"]["object_id"] = 99
        self.rejected(events)
        events = fixture(); events.insert(5, copy.deepcopy(events[4]))
        self.rejected(events)

    def test_startup_order_and_one_preinit_required(self):
        for events in (fixture()[1:], fixture()[:2] + fixture()[3:],
                       fixture()[:3] + [fixture()[2]] + fixture()[3:]):
            self.rejected(events)

    def test_handshake_cannot_repeat_or_change_source(self):
        events = fixture(); events.insert(2, copy.deepcopy(events[0])); self.rejected(events)
        events = fixture(); events[0]["payload"]["source_freeze_sha256"] = "d" * 64; self.rejected(events)

    def test_close_before_preinit_refused(self):
        events = fixture(); events.insert(2, event("object_close", {"object_id": 1})); self.rejected(events)

    def test_unlisted_pin_and_bad_byte_type_refused(self):
        for key, value in (("sha256", "c" * 64), ("bytes", True)):
            events = fixture(); events[3]["payload"]["file_pin"][key] = value; self.rejected(events)
        events = fixture(); events[3]["payload"]["resolved_path"] = "/other.so"; self.rejected(events)

    def test_new_namespace_and_kernel_pseudo_object_refused(self):
        events = fixture(); events[3]["payload"]["namespace_id"] = 1; self.rejected(events)
        events = fixture(); events[3]["payload"]["loader_name"] = "linux-vdso.so.1"; self.rejected(events)

    def test_loader_name_resolution_requires_external_qualification(self):
        for name in ("transient.so", "/symlink/transient.so", None):
            events = fixture(); events[3]["payload"]["loader_name"] = name; self.rejected(events)

    def test_paths_cannot_traverse_or_normalize_silently(self):
        for name in ("/", "/fixture/../transient.so", "/fixture//transient.so", "//fixture/x", "/x\0y"):
            with self.assertRaises(module.Refusal): module.path(name)

    def test_boolean_identifiers_refused(self):
        for index, key in ((0, "loader_interface_version"), (3, "object_id"), (3, "namespace_id"),
                           (2, "main_object_id"), (4, "object_id"), (5, "event_loss_count"), (5, "exit_code")):
            events = fixture(); events[index]["payload"][key] = False; self.rejected(events)

    def test_event_loss_or_nonzero_exit_refused(self):
        for key in ("event_loss_count", "exit_code"):
            events = fixture(); events[-1]["payload"][key] = 1; self.rejected(events)

    def test_incomplete_and_truncated_stream_cannot_finish(self):
        ledger = module.LoaderLedger(PROCESS, "/fixture/python", FILES)
        for raw in bodies(fixture())[:-1]: ledger.consume(raw)
        with self.assertRaises(module.Refusal): ledger.finish()
        with self.assertRaises(module.Refusal): ledger.consume(bodies(fixture())[-1][:-1])
        with self.assertRaises(module.Refusal): ledger.finish()

    def test_no_resumption_after_failure_or_end(self):
        for complete in (False, True):
            ledger = module.LoaderLedger(PROCESS, "/fixture/python", FILES)
            if complete:
                for raw in bodies(fixture()): ledger.consume(raw)
            else:
                with self.assertRaises(module.Refusal): ledger.consume(b"{}\n")
            with self.assertRaises(module.Refusal): ledger.consume(bodies(fixture())[0])

    def test_event_sequence_time_hash_and_process_drift_refused(self):
        for key, value in (("sequence", 0), ("monotonic_ns", 1), ("previous_sha256", "e" * 64),
                           ("process", {**PROCESS, "starttime_ticks": PROCESS["starttime_ticks"] + 1})):
            ledger = module.LoaderLedger(PROCESS, "/fixture/python", FILES)
            raw = bodies(fixture()); ledger.consume(raw[0])
            item = json.loads(raw[1]); item[key] = value
            with self.assertRaises(module.Refusal): ledger.consume(module.canonical(item))

    def test_namespace_starttime_pid_binding_cannot_be_substituted(self):
        for key in PROCESS:
            ledger = module.LoaderLedger(PROCESS, "/fixture/python", FILES)
            item = json.loads(bodies(fixture())[0]); item["process"][key] += 1
            with self.assertRaises(module.Refusal): ledger.consume(module.canonical(item))

    def test_canonical_duplicate_nonfinite_and_unknown_fields_refused(self):
        for raw in (b'{"x":1,"x":2}\n', b'{"x":NaN}\n', b'{ "x": 1 }\n', b'\xff\n'):
            with self.assertRaises(module.Refusal): module.decode(raw)
        events = fixture(); events[0]["payload"]["all_qualified"] = True; self.rejected(events)
        events = fixture(); events[3]["kind"] = "qualified_snapshot"; self.rejected(events)

    def test_record_byte_and_event_caps_charge_failed_attempt(self):
        ledger = module.LoaderLedger(PROCESS, "/fixture/python", FILES)
        raw = b" " * (module.MAX_RECORD + 1)
        with self.assertRaises(module.Refusal): ledger.consume(raw)
        self.assertEqual(ledger.bytes, len(raw))
        ledger = module.LoaderLedger(PROCESS, "/fixture/python", FILES); ledger.bytes = module.MAX_BYTES
        with self.assertRaises(module.Refusal): ledger.consume(bodies(fixture())[0])
        ledger = module.LoaderLedger(PROCESS, "/fixture/python", FILES); ledger.count = module.MAX_EVENTS
        with self.assertRaises(module.Refusal): ledger.consume(bodies(fixture())[0])

    def test_object_cap_and_large_expectations_refused(self):
        events = fixture(); events[3]["payload"]["object_id"] = module.MAX_OBJECTS + 1; self.rejected(events)
        with self.assertRaises(module.Refusal):
            module.LoaderLedger(PROCESS, "/fixture/python", {"/x/" + str(i): FILES["/fixture/python"]
                                                           for i in range(module.MAX_OBJECTS + 1)})

    def test_external_expectations_and_receipt_are_defensive_copies(self):
        process = copy.deepcopy(PROCESS); files = copy.deepcopy(FILES)
        ledger = module.LoaderLedger(process, "/fixture/python", files)
        process["local_pid"] = 777; files["/fixture/python"]["sha256"] = "f" * 64
        for raw in bodies(fixture()): ledger.consume(raw)
        value = ledger.finish(); value["object_generations"][0]["file_pin"]["sha256"] = "f" * 64
        value["process"]["local_pid"] = 778
        self.assertEqual(ledger.finish()["object_generations"][0]["file_pin"], FILES["/fixture/python"])
        self.assertEqual(ledger.finish()["process"], PROCESS)

    def test_chain_and_charge_use_all_original_raw_bytes(self):
        raw = bodies(fixture()); value = checked(fixture())
        self.assertEqual(value["terminal_chain_sha256"], hashlib.sha256(raw[-1]).hexdigest())
        self.assertEqual(value["raw_event_bytes_charged"], sum(map(len, raw)))

    def test_recomputed_chain_can_hide_omission_but_cannot_grant_coverage(self):
        # A trusted live collector remains necessary: a valid chain is not a
        # proof that somebody did not omit a whole open/close pair and rehash.
        events = fixture(); del events[3:5]
        value = checked(events)
        self.assertEqual(value["transient_generations_retained"], 0)
        self.assertIs(value["collector_authentication"], False)
        self.assertIs(value["full_syscall_or_loader_coverage"], False)
        self.assertIs(value["execution_authorized"], False)

    def test_component_import_is_stdlib_only_and_inert(self):
        tree = ast.parse((HERE / "loader_lifetime.py").read_bytes())
        names = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        names |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        self.assertEqual(names, {"hashlib", "json", "pathlib"})
        self.assertTrue(all(name not in sys.modules for name in ("numpy", "h5py", "hdf5plugin")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
