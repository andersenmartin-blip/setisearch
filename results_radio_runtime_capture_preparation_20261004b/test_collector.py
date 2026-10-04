"""Tiny disjoint fixtures only; no actual interpreter/runtime capture."""
import copy
import contextlib
import io
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("capture_collector_under_test", HERE / "collector.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
PLAN_RAW = (HERE.parent / "results_radio_runtime_materialization_preparation_20261004a" / "runtime-materialization.plan.json").read_bytes()
PLAN_PIN = hashlib.sha256(PLAN_RAW).hexdigest()

def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

def pin(value):
    return hashlib.sha256(value).hexdigest()

def file_pin(path="/fixture/python", body=b"synthetic ELF", role="runtime"):
    return {"path": path, "role": role, "bytes": len(body), "sha256": pin(body), "mode": "100755" if path == "/fixture/python" else "100644"}

def contract():
    return {"schema": c.SCHEMA, "evidence_domain": "synthetic-test-fixture", "capture_identity": "a" * 64,
            "capture_authorized": True, "externally_bound_publication_required": True,
            "activation_required": True, "plan_sha256": PLAN_PIN,
            "python_path": "/fixture/python", "python_sha256": pin(b"synthetic ELF"),
            "files": [file_pin()], "imports": [], "import_paths": [], "loader_paths": [],
            "distributions": [], "missing_paths": ["/fixture/h5py"],
            "limits": dict(c.MAXIMA)}

def witness(contract_pin):
    return {"schema": "radio-runtime-metadata-capture-publication-readback-v1",
            "prepared_commit": "1" * 40, "prepared_tree": "2" * 40,
            "activation_commit": "3" * 40, "activation_tree": "4" * 40,
            "activation_parent": "1" * 40, "collector_contract_sha256": contract_pin,
            "repository": "andersenmartin-blip/setisearch", "branch": "m43-support-qualification",
            "activation_changed_path": "config/fixture.activate.json", "contract_sha256": "6" * 64,
            "publication_files": [{"sha256": contract_pin}], "capture_identity": "a" * 64,
            "plan_sha256": PLAN_PIN, "provenance": {"synthetic_test_fixture": True},
            "activation_sha256": "5" * 64}

class FakeBackend:
    def __init__(self):
        self.calls = []
        self.import_count = 0
        self.python_version = "3.12.14"
        self.native_modules = {}
        self.package_versions = {"numpy": "2.3.5", "h5py": "3.16.0", "hdf5": "2.0.0", "hdf5plugin": "7.1.0"}
        self.file_round = 0
        self.drift_file = False
        self.availability_round = 0
        self.drift_availability = False
        self.data = {"/fixture/python": b"synthetic ELF"}
    def host(self):
        self.calls.append("host")
        return {"python": self.python_version, "python_full": self.python_version,
                "implementation": "cpython", "cache_tag": "cpython-312", "executable": "/fixture/python",
                "executable_realpath": "/fixture/python", "system": "Linux", "release": "fixture",
                "machine": "x86_64", "endianness": "little", "libc": "glibc 2.28",
                "isolated": True, "no_site": True, "dont_write_bytecode": True, "import_paths": []}
    def maps(self, ledger, limit):
        self.calls.append("maps")
        body = b"1000-2000 r-xp 00000000 01:02 7 /fixture/python\n"
        ledger.charge(len(body), "proc_maps_read_bytes")
        return body
    def file(self, entry, ledger, keep_bytes):
        self.calls.append("file")
        self.file_round += 1
        body = self.data[entry["path"]]
        ledger.charge(len(body), "regular_file_read_bytes")
        if pin(body) != entry["sha256"]:
            raise c.CaptureError("fake file hash mismatch")
        record = dict(entry, device=os.makedev(1, 2), inode=7,
                      mtime_ns=self.file_round if self.drift_file else 1, ctime_ns=2)
        return record, body if keep_bytes else None
    def modules(self):
        self.calls.append("modules")
        return dict(self.native_modules)
    def availability(self, paths):
        self.calls.append("availability")
        self.availability_round += 1
        return [{"path": path, "status": "PRESENT_AT_EXACT_PATH" if self.drift_availability and self.availability_round > 1 else "MISSING_AT_EXACT_PATH"} for path in paths]
    def import_packages(self, packages, paths):
        self.calls.append("imports")
        self.import_count += 1
        return {name: {"status": "OBSERVED", "version": version} for name, version in self.package_versions.items()}, {}

def fake_elf(body, **kwargs):
    return {"needed": [], "interpreter": "/fixture/ld.so", "rpath": None, "runpath": None, "soname": None}

def run_capture(value=None, backend=None):
    value = contract() if value is None else value
    body = raw(value)
    w = raw(witness(pin(body)))
    return c.capture(body, pin(body), PLAN_RAW, PLAN_PIN, admission_witness_raw=w,
                     admission_witness_pin=pin(w), backend=backend or FakeBackend(), elf_parser=fake_elf)

class AdmissionTests(unittest.TestCase):
    def test_default_missing_authority_refuses_before_backend(self):
        b = FakeBackend()
        value = contract(); value["capture_authorized"] = False
        with self.assertRaises(c.CaptureError): run_capture(value, b)
        self.assertEqual(b.calls, [])
    def test_public_scientific_domain_refuses(self):
        value = contract(); value["evidence_domain"] = "public-scientific-evidence"
        with self.assertRaises(c.CaptureError): run_capture(value)
    def test_outer_pins_and_duplicate_json(self):
        body = raw(contract())
        with self.assertRaises(c.CaptureError): c.validate_inputs(body, "0" * 64, PLAN_RAW, PLAN_PIN)
        duplicated = b'{"schema":"x","schema":"y"}'
        with self.assertRaises(c.CaptureError): c.validate_inputs(duplicated, pin(duplicated), PLAN_RAW, PLAN_PIN)
    def test_authority_target_and_schema_semantic_drift(self):
        for mutate in (lambda p: p.update(schema="other"), lambda p: p["authority"].update(runtime_qualified=True),
                       lambda p: p["materialization"]["required_historical_versions"].update(python="3.13.0")):
            plan = json.loads(PLAN_RAW); mutate(plan); plan_raw = raw(plan)
            value = contract(); value["plan_sha256"] = pin(plan_raw); body = raw(value)
            with self.assertRaises(c.CaptureError): c.validate_inputs(body, pin(body), plan_raw, pin(plan_raw))
    def test_zero_length_selected_regular_metadata_is_admissible(self):
        value = contract()
        value["files"].append(file_pin("/fixture/empty/__init__.py", b"", "runtime"))
        body = raw(value)
        admitted, _ = c.validate_inputs(body, pin(body), PLAN_RAW, PLAN_PIN)
        self.assertEqual(admitted["files"][1]["bytes"], 0)
        self.assertEqual(admitted["files"][1]["sha256"], hashlib.sha256(b"").hexdigest())
        b = FakeBackend(); b.data["/fixture/empty/__init__.py"] = b""
        result = run_capture(value, b)
        self.assertEqual(result["selected_files_before"][1]["bytes"], 0)
        self.assertEqual(result["selected_files_before"], result["selected_files_after"])
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "empty.py"; path.write_bytes(b""); path.chmod(0o644)
            entry = file_pin(str(path), b"", "runtime"); ledger = c.ReadLedger(1)
            observation, exact_raw = c.read_selected_file(entry, ledger, keep_bytes=True)
            self.assertEqual(exact_raw, b"")
            self.assertEqual(observation["sha256"], hashlib.sha256(b"").hexdigest())
            self.assertEqual(ledger.read_bytes, 0)
        for invalid in (-1, True):
            value = contract(); value["files"].append(file_pin("/fixture/empty/__init__.py", b"", "runtime"))
            value["files"][1]["bytes"] = invalid
            with self.assertRaises(c.CaptureError): run_capture(value)

    def test_unknown_fields_caps_duplicates_paths(self):
        mutations = [lambda x: x.update(extra=True), lambda x: x["limits"].update(files=True),
                     lambda x: x["limits"].update(read_bytes=1), lambda x: x["files"].append(copy.deepcopy(x["files"][0])),
                     lambda x: x["files"][0].update(path="/fixture/../python")]
        for mutate in mutations:
            value = contract(); mutate(value)
            with self.assertRaises(c.CaptureError): run_capture(value)
    def test_real_domain_native_imports_deferred(self):
        value = contract(); value["evidence_domain"] = "metadata-capture-only"
        value["files"].append(file_pin("/fixture/numpy/__init__.py", b"x", "code"))
        value["imports"] = [{"name": "numpy", "origin": "/fixture/numpy/__init__.py", "version": "2.3.5"}]
        value["import_paths"] = ["/fixture"]
        body = raw(value)
        with self.assertRaises(c.CaptureError): c.validate_inputs(body, pin(body), PLAN_RAW, PLAN_PIN)
    def test_witness_required_and_linked(self):
        body = raw(contract()); b = FakeBackend()
        with self.assertRaises(c.CaptureError): c.capture(body, pin(body), PLAN_RAW, PLAN_PIN, backend=b, elf_parser=fake_elf)
        self.assertEqual(b.calls, [])
        w = witness(pin(body)); w["activation_parent"] = "9" * 40; wb = raw(w)
        with self.assertRaises(c.CaptureError): c.capture(body, pin(body), PLAN_RAW, PLAN_PIN, admission_witness_raw=wb, admission_witness_pin=pin(wb), backend=b, elf_parser=fake_elf)
    def test_fixture_observation_is_detached_pending(self):
        backend = FakeBackend(); value = contract(); result = run_capture(value, backend)
        self.assertEqual(result["status"], "OBSERVED_METADATA_ONLY")
        self.assertEqual(result["admission_status"], "PENDING_MISSING_INPUTS")
        self.assertTrue(all(v is False for v in result["authority"].values()))
        self.assertEqual(len(result["authority"]), 16)
        self.assertEqual(backend.import_count, 0)
        value["files"][0]["sha256"] = "0" * 64
        self.assertEqual(result["selected_files_before"][0]["sha256"], pin(b"synthetic ELF"))
        self.assertEqual(result["maps_raw_before_utf8"].encode(), b"1000-2000 r-xp 00000000 01:02 7 /fixture/python\n")
        self.assertEqual(result["read_ledger"]["regular_file_read_bytes"], 2 * len(b"synthetic ELF"))
    def test_host_mismatch_never_adopts_or_imports(self):
        b = FakeBackend(); b.python_version = "3.13.1"
        value = contract(); value["files"].append(file_pin("/fixture/numpy/__init__.py", b"x", "code")); b.data["/fixture/numpy/__init__.py"] = b"x"
        value["imports"] = [{"name": "numpy", "origin": "/fixture/numpy/__init__.py", "version": "2.3.5"}]; value["import_paths"] = ["/fixture"]
        result = run_capture(value, b)
        self.assertEqual(b.import_count, 0)
        self.assertIn({"identity": "python", "required": "3.12.14", "observed": "3.13.1"}, result["mismatches"])
    def test_package_version_mismatch_observation_remains_pending(self):
        b = FakeBackend(); b.package_versions["numpy"] = "9.9.9"
        value = contract(); value["files"].append(file_pin("/fixture/numpy/__init__.py", b"x", "code")); b.data["/fixture/numpy/__init__.py"] = b"x"
        value["imports"] = [{"name": "numpy", "origin": "/fixture/numpy/__init__.py", "version": "2.3.5"}]; value["import_paths"] = ["/fixture"]
        result = run_capture(value, b)
        self.assertIn({"identity": "numpy", "required": "2.3.5", "observed": "9.9.9"}, result["mismatches"])
        self.assertFalse(result["authority"]["runtime_qualified"])
    def test_inventory_or_availability_drift_closes(self):
        for field in ("drift_file", "drift_availability"):
            b = FakeBackend(); setattr(b, field, True)
            with self.assertRaises(c.CaptureError): run_capture(backend=b)
    def test_ambient_native_modules_refused(self):
        b = FakeBackend(); b.native_modules = {"numpy": "/ambient/numpy.py"}
        with self.assertRaises(c.CaptureError): run_capture(backend=b)
    def test_result_byte_cap(self):
        value = contract(); value["limits"]["result_bytes"] = 8
        with self.assertRaises(c.CaptureError): run_capture(value)

    def test_elf_failure_binds_selected_file_and_never_returns_partial_success(self):
        spec = importlib.util.spec_from_file_location("failure_elf_fixture", HERE / "test_elf_metadata.py")
        fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
        b = FakeBackend(); value = contract()
        body = fixture.changed(fixture.elf_fixture(), 0x300 + 8, "<Q", 0x400800)
        value["files"][0] = file_pin(body=body); value["python_sha256"] = pin(body)
        b.data["/fixture/python"] = body
        for name in ("collector.py", "elf_metadata.py"):
            path = str(HERE / name); source = (HERE / name).read_bytes()
            value["files"].append(file_pin(path, source, "code")); b.data[path] = source
        body_raw = raw(value); w = raw(witness(pin(body_raw)))
        with self.assertRaises(c.ElfCaptureError) as raised:
            c.capture(body_raw, pin(body_raw), PLAN_RAW, PLAN_PIN,
                      admission_witness_raw=w, admission_witness_pin=pin(w), backend=b)
        context = raised.exception.context
        self.assertEqual(context["path"], "/fixture/python")
        self.assertEqual(context["file_bytes"], len(body))
        self.assertEqual(context["file_sha256"], pin(body))
        self.assertEqual(context["parser_context"]["table_address"], 0x400800)
        self.assertEqual(context["parser_source_sha256"], pin((HERE / "elf_metadata.py").read_bytes()))
        self.assertEqual(context["collector_source_sha256"], pin((HERE / "collector.py").read_bytes()))
        self.assertFalse(context["parser_injected_synthetic_only"])
        self.assertEqual(context["status"], "CLOSED_FAILED")
        self.assertFalse(context["observation_adopted"])
        self.assertTrue(all(v is False for v in context["authority"].values()))
        self.assertEqual(b.import_count, 0)
        self.assertNotIn("modules", b.calls)

    def test_elf_failure_cli_writes_structured_stderr_and_no_stdout(self):
        exc = c.ElfCaptureError("selected ELF metadata rejected", {
            "schema": "radio-selected-elf-error-context-v1", "path": "/fixture/python",
            "file_bytes": 12, "file_sha256": "a" * 64, "status": "CLOSED_FAILED"})
        out, err = io.StringIO(), io.StringIO()
        args = ["--contract", "/fixture/c", "--contract-sha256", "a" * 64,
                "--plan", "/fixture/p", "--plan-sha256", "b" * 64,
                "--admission-witness", "/fixture/w", "--admission-witness-sha256", "c" * 64]
        with patch.object(c, "_raw_cli_file", return_value=b"fixture"), \
             patch.object(c, "capture", side_effect=exc), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(c.main(args), 1)
        self.assertEqual(out.getvalue(), "")
        lines = err.getvalue().splitlines()
        self.assertTrue(lines[0].startswith("CLOSED_FAILED ElfCaptureError:"))
        context = json.loads(lines[1].removeprefix("ELF_ERROR_CONTEXT "))
        self.assertEqual(context["path"], "/fixture/python")

    def test_injected_parser_malformed_context_cannot_expand_error_bound(self):
        class SyntheticFailure(ValueError):
            context = {"huge": "x" * 1000000}
        def failing_parser(_body, **_caps):
            raise SyntheticFailure("s" * 1000000)
        value = contract(); b = FakeBackend(); body = raw(value); w = raw(witness(pin(body)))
        with self.assertRaises(c.ElfCaptureError) as raised:
            c.capture(body, pin(body), PLAN_RAW, PLAN_PIN, admission_witness_raw=w,
                      admission_witness_pin=pin(w), backend=b, elf_parser=failing_parser)
        context = raised.exception.context
        self.assertEqual(context["parser_context_status"], "UNAVAILABLE_OR_UNSUPPORTED")
        self.assertLessEqual(len(c._canonical(context)), 65536)
        self.assertLessEqual(len(context["parser_reason"]), 512)
        self.assertFalse(context["observation_adopted"])
        self.assertTrue(context["parser_injected_synthetic_only"])
        self.assertIsNone(context["parser_source_sha256"])

    def test_pinned_helper_exec_works_under_isolated_path(self):
        fixture_spec = importlib.util.spec_from_file_location("synthetic_elf_fixture", HERE / "test_elf_metadata.py")
        fixture_module = importlib.util.module_from_spec(fixture_spec)
        fixture_spec.loader.exec_module(fixture_module)
        b = FakeBackend(); value = contract()
        body = fixture_module.elf_fixture()
        value["files"][0] = file_pin(body=body)
        value["python_sha256"] = pin(body)
        b.data["/fixture/python"] = body
        for name in ("collector.py", "elf_metadata.py"):
            source_path = str(HERE / name); source_raw = (HERE / name).read_bytes()
            value["files"].append(file_pin(source_path, source_raw, "code"))
            b.data[source_path] = source_raw
        contract_raw = raw(value); w = raw(witness(pin(contract_raw)))
        result = c.capture(contract_raw, pin(contract_raw), PLAN_RAW, PLAN_PIN,
            admission_witness_raw=w, admission_witness_pin=pin(w), backend=b,
            initial_cli_read_bytes=123)
        self.assertEqual(result["elf_metadata"]["/fixture/python"]["needed"], ["libfirst.so", "libother.so"])
        self.assertEqual(result["read_ledger"]["cli_input_read_bytes"], 123)
        self.assertTrue(all(edge["status"] == "UNRESOLVED" for edge in result["dependency_observations"]))
        self.assertFalse(result["engineering_capture_authorized"])


class FileReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.path = self.root / "fixture.bin"; self.path.write_bytes(b"disjoint metadata"); self.path.chmod(0o644)
        self.entry = file_pin(str(self.path), self.path.read_bytes(), "input")
    def tearDown(self): self.temp.cleanup()
    def test_bounded_hash_exact_bytes(self):
        ledger = c.ReadLedger(100)
        observed, body = c.read_selected_file(self.entry, ledger, keep_bytes=True)
        self.assertEqual(body, b"disjoint metadata")
        self.assertEqual(observed["sha256"], self.entry["sha256"])
        self.assertEqual(ledger.read_bytes, len(body))
    def test_symlink_hardlink_directory_fifo_refused(self):
        symlink = self.root / "link"; symlink.symlink_to(self.path)
        e = dict(self.entry, path=str(symlink))
        with self.assertRaises(c.CaptureError): c.read_selected_file(e, c.ReadLedger(100))
        hardlink = self.root / "hard"; os.link(self.path, hardlink)
        with self.assertRaises(c.CaptureError): c.read_selected_file(self.entry, c.ReadLedger(100))
        hardlink.unlink()
        directory = self.root / "directory"; directory.mkdir()
        with self.assertRaises(c.CaptureError): c.read_selected_file(dict(self.entry, path=str(directory)), c.ReadLedger(100))
        fifo = self.root / "fifo"; os.mkfifo(fifo)
        with self.assertRaises(c.CaptureError): c.read_selected_file(dict(self.entry, path=str(fifo)), c.ReadLedger(100))
    def test_named_replacement_detected(self):
        def replace(path):
            alternate = self.root / "new"; alternate.write_bytes(b"disjoint metadata"); alternate.chmod(0o644); os.replace(alternate, path)
        with self.assertRaises(c.CaptureError): c.read_selected_file(self.entry, c.ReadLedger(100), after_read=replace)
    def test_hash_size_mode_and_cap_negatives(self):
        for entry in (dict(self.entry, sha256="0" * 64), dict(self.entry, bytes=1), dict(self.entry, mode="100755")):
            with self.assertRaises(c.CaptureError): c.read_selected_file(entry, c.ReadLedger(100))
        ledger = c.ReadLedger(1)
        with self.assertRaises(c.CaptureError): c.read_selected_file(self.entry, ledger)
        self.assertEqual(ledger.read_bytes, 0)
    def test_ancestor_symlink_refused(self):
        alias = self.root / "alias"; alias.symlink_to(self.root)
        with self.assertRaises(c.CaptureError): c.read_selected_file(dict(self.entry, path=str(alias / self.path.name)), c.ReadLedger(100))

class MapsAndDistributionTests(unittest.TestCase):
    def test_maps_truncation_overflow_and_cap(self):
        for body in (b"garbage\n", b"ffffffffffffffff-10000000000000000 r-xp 0 00:00 1 /x\n", b"2000-1000 r-xp 0 00:00 1 /x\n", b"\xff"):
            with self.assertRaises(c.CaptureError): c.parse_maps(body)
        with self.assertRaises(c.CaptureError): c.parse_maps(b"123", max_bytes=2)
    def test_dependency_ambiguity_never_loader_proof(self):
        files = [{"path": "/a/libx.so", "device": os.makedev(1,2), "inode": 1}, {"path": "/b/libx.so", "device": os.makedev(1,2), "inode": 2}]
        maps = [{"path": x["path"], "deleted": False, "device_major": 1, "device_minor": 2, "inode": x["inode"]} for x in files]
        elfs = {"/consumer": {"needed": ["libx.so", "missing.so"], "runpath": "$ORIGIN"}, "/a/libx.so": {"needed": []}, "/b/libx.so": {"needed": []}}
        result = c.resolve_dependencies(elfs, maps, files, ["/a"])
        self.assertEqual(result[0]["status"], "AMBIGUOUS_OBSERVED_CANDIDATES")
        self.assertEqual(result[1]["status"], "UNRESOLVED")
        self.assertTrue(all(x["observed_loader_edge_proven"] is False for x in result))
        maps[1]["deleted"] = True
        self.assertEqual(c.resolve_dependencies(elfs, maps, files, ["/a"])[0]["status"], "UNIQUE_OBSERVED_COMPATIBLE_CANDIDATE")
    def test_static_metadata_is_not_import_or_record_traversal(self):
        d = {"name": "numpy", "metadata_path": "/f/METADATA", "wheel_path": "/f/WHEEL", "record_path": "/f/RECORD", "expected_version": "2.3.5"}
        inputs = {"/f/METADATA": b"Name: numpy\nVersion: 2.3.5\n\nbody", "/f/WHEEL": b"Wheel-Version: 1.0\nTag: cp312-cp312-manylinux_2_28_x86_64\n", "/f/RECORD": b"../../danger,,\n"}
        result = c.observe_distribution(d, inputs)
        self.assertEqual(result["record_rows"], 1)
        self.assertFalse(result["complete_package_custody_proven"])
        self.assertEqual(result["record_member_files_opened"], 0)
        inputs["/f/METADATA"] = b"Name: numpy\nVersion: 9.9\n"
        self.assertFalse(c.observe_distribution(d, inputs)["version_matches_retained_target"])
        inputs["/f/METADATA"] = b"Name: numpy\nVersion: 2.3.5\nVersion: 9.9\n"
        with self.assertRaises(c.CaptureError): c.observe_distribution(d, inputs)

if __name__ == "__main__": unittest.main()
