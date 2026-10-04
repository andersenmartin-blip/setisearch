"""Pure capture-b preparation regression tests; no collector or live root use."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("capture_b_contract_builder", HERE / "build_contracts.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


class ContractPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_plan = (HERE.parent / b.PLAN_REL).read_bytes()

    def setUp(self):
        self.repo = Path("/synthetic/capture-b-repository")
        self.root = Path("/synthetic/capture-b-root")
        selected = [
            {"path": "/synthetic/python3.12", "role": "elf", "bytes": 1000,
             "sha256": "d" * 64, "mode": "100755", "filesystem_mode": "0755"},
            {"path": "/synthetic/stdlib.py", "role": "runtime", "bytes": 200,
             "sha256": "e" * 64, "mode": "100644", "filesystem_mode": "0644"}]
        self.preread = {"schema": "radio-runtime-metadata-prospective-preread-pins-v1",
                        "capture_identity": b.IDENTITY, "selected_files": selected,
                        "selected_file_count": 2, "selected_file_bytes": 1200,
                        "python_path": "/synthetic/python3.12", "loader_paths": [],
                        "distributions": [], "missing_paths": []}
        self.artifacts = {}
        for path in b.input_paths(self.repo):
            if str(path).endswith(b.PLAN_REL):
                raw = self.original_plan
            elif path.name == "runtime-preread-pins.json":
                raw = b.canonical(self.preread)
            else:
                raw = b"# synthetic finalized repository preparation input\n"
            self.artifacts[str(path)] = (raw, b.pin_for(path, raw))
        self.validation = {}
        for name in ("capture_gate", "collector", "elf_metadata"):
            testpath = self.repo / b.HERE_REL / ("test_" + name + ".py")
            logpath = self.repo / b.HERE_REL / (name + "-synthetic-final-tests.log")
            testraw = b"# synthetic test\n"
            lograw = b"synthetic preparation fixture\nRan 2 tests in 0.001s\n\nOK\n"
            self.validation[str(testpath)] = (testraw, b.pin_for(testpath, testraw))
            self.validation[str(logpath)] = (lograw, b.pin_for(logpath, lograw))
        self.refresh_ready()

    def refresh_ready(self):
        self.ready = {"schema": "radio-runtime-capture-b-inputs-ready-v1", "capture_identity": b.IDENTITY,
                      "status": "FINAL_FOR_CONTRACT_PREPARATION",
                      "input_pins": sorted([v[1] for v in self.artifacts.values()], key=lambda p: p["path"]),
                      "validation_pins": sorted([v[1] for v in self.validation.values()], key=lambda p: p["path"])}

    def update_preread(self):
        path = str(self.repo / b.HERE_REL / "runtime-preread-pins.json")
        raw = b.canonical(self.preread)
        self.artifacts[path] = (raw, b.pin_for(path, raw))
        self.refresh_ready()

    def assemble(self):
        return b.assemble(self.repo, self.root, self.artifacts, self.ready, self.validation)

    def test_fresh_acyclic_contracts_and_budget_arithmetic(self):
        child_raw, supervisor_raw, headroom_raw = self.assemble()
        child, supervisor, headroom = map(b.parse, (child_raw, supervisor_raw, headroom_raw))
        self.assertEqual(len(child["files"]), 7)
        self.assertEqual(len(supervisor["source_pins"]), 7)
        self.assertEqual(len(supervisor["runtime_pins"]), 2)
        self.assertEqual(child["imports"], [])
        self.assertEqual(child["import_paths"], [])
        self.assertEqual(child["limits"]["result_bytes"] + 1, supervisor["limits"]["stream_bytes"])
        self.assertNotIn(str(self.repo / b.CHILD_REL), {p["path"] for p in child["files"]})
        self.assertNotIn(str(self.repo / b.FREEZE_REL), {p["path"] for p in supervisor["source_pins"]})
        self.assertNotIn(str(self.repo / b.HERE_REL / "runtime-preread-pins.json"), {p["path"] for p in child["files"]})
        self.assertEqual(supervisor["activation_path"], str(self.repo / b.ACTIVATION_REL))
        self.assertEqual(supervisor["output_root_identity"], b.ROOT_IDENTITY)
        self.assertEqual(headroom["parent_explicit_read_allocation_bytes"] + headroom["child_explicit_read_reservation_bytes"], 256 * b.MIB)
        self.assertEqual(headroom["parent_known_explicit_read_upper_bound_bytes"],
                         headroom["parent_inventory_two_pass_bytes"] + headroom["parent_cli_upper_bound_bytes"] + len(child_raw) + headroom["activation_marker_canonical_bytes"] + 1)
        self.assertEqual(headroom["terminal_read_floor_bytes"], headroom["parent_inventory_one_pass_bytes"] + 1 + 16385)
        self.assertFalse(headroom["new_allocation_created"])
        self.assertFalse(headroom["child_reservation_refunded"])
        self.assertEqual(headroom["engineering_subtotal_before_seconds"], 970)
        self.assertEqual(headroom["scientific_fields_pending"], 11)
        self.assertTrue(all(value is False for value in headroom["authority"].values()))

    def test_missing_final_readiness_refused(self):
        self.ready["status"] = "DRAFT"
        with self.assertRaisesRegex(b.PreparationError, "readiness"):
            self.assemble()

    def test_old_identity_is_never_adopted(self):
        self.ready["capture_identity"] = "f" * 64
        with self.assertRaises(b.PreparationError):
            self.assemble()

    def test_post_ready_source_edit_refused(self):
        path = str(self.repo / b.HERE_REL / "capture_gate.py")
        raw = b"# changed after readiness\n"
        self.artifacts[path] = (raw, b.pin_for(path, raw))
        with self.assertRaisesRegex(b.PreparationError, "input drift"):
            self.assemble()

    def test_post_ready_validation_log_edit_refused(self):
        path = next(p for p in self.validation if p.endswith(".log"))
        raw = b"FAILED\n"
        self.validation[path] = (raw, b.pin_for(path, raw))
        with self.assertRaisesRegex(b.PreparationError, "validation-only input drift"):
            self.assemble()

    def test_failed_producer_log_cannot_be_finalized(self):
        path = next(p for p in self.validation if p.endswith(".log"))
        raw = b"synthetic fixture\nRan 2 tests in 0.001s\n\nFAILED (failures=1)\n"
        self.validation[path] = (raw, b.pin_for(path, raw))
        self.refresh_ready()
        with self.assertRaisesRegex(b.PreparationError, "successful final producer test log"):
            self.assemble()

    def test_omitted_input_readiness_pin_refused(self):
        self.ready["input_pins"].pop()
        with self.assertRaises(b.PreparationError):
            self.assemble()

    def test_contract_selfpin_cycle_refused(self):
        path = str(self.repo / b.CHILD_REL)
        self.artifacts[path] = (b"{}\n", b.pin_for(path, b"{}\n"))
        self.refresh_ready()
        with self.assertRaisesRegex(b.PreparationError, "acyclic"):
            self.assemble()

    def test_original_plan_raw_drift_refused(self):
        path = str(self.repo / b.PLAN_REL)
        raw = self.original_plan + b" "
        self.artifacts[path] = (raw, b.pin_for(path, raw))
        self.refresh_ready()
        with self.assertRaisesRegex(b.PreparationError, "original inert plan"):
            self.assemble()

    def test_old_preread_identity_refused(self):
        self.preread["capture_identity"] = "f" * 64
        self.update_preread()
        with self.assertRaisesRegex(b.PreparationError, "fresh completed preread"):
            self.assemble()

    def test_duplicate_runtime_refused(self):
        self.preread["selected_files"].append(copy.deepcopy(self.preread["selected_files"][0]))
        self.preread["selected_file_count"] = 3
        self.preread["selected_file_bytes"] = 2200
        self.update_preread()
        with self.assertRaisesRegex(b.PreparationError, "duplicate"):
            self.assemble()

    def test_preread_byte_totals_drift_refused(self):
        self.preread["selected_file_bytes"] += 1
        self.update_preread()
        with self.assertRaisesRegex(b.PreparationError, "totals"):
            self.assemble()

    def test_preread_mode_mismatch_refused(self):
        self.preread["selected_files"][0]["mode"] = "100644"
        self.update_preread()
        with self.assertRaisesRegex(b.PreparationError, "mode mapping"):
            self.assemble()

    def test_static_distribution_unselected_bytes_refused(self):
        self.preread["distributions"] = [{"name": "numpy", "expected_version": "2.3.5",
            "metadata_path": "/unselected/METADATA", "wheel_path": "/unselected/WHEEL",
            "record_path": "/unselected/RECORD"}]
        self.update_preread()
        with self.assertRaisesRegex(b.PreparationError, "not selected"):
            self.assemble()

    def test_static_distribution_version_drift_refused(self):
        self.preread["distributions"] = [{"name": "numpy", "expected_version": "9.9",
            "metadata_path": "/synthetic/stdlib.py", "wheel_path": "/synthetic/stdlib.py",
            "record_path": "/synthetic/stdlib.py"}]
        self.update_preread()
        with self.assertRaisesRegex(b.PreparationError, "name/version"):
            self.assemble()

    def test_noncanonical_runtime_path_refused(self):
        self.preread["selected_files"][1]["path"] = "/synthetic/../stdlib.py"
        self.update_preread()
        with self.assertRaisesRegex(b.PreparationError, "absolute path"):
            self.assemble()

    def test_missing_path_existing_overlap_refused(self):
        self.preread["missing_paths"] = [self.preread["python_path"]]
        self.update_preread()
        with self.assertRaisesRegex(b.PreparationError, "overlap"):
            self.assemble()

    def test_joined_inventory_cap_refuses_before_output(self):
        self.preread["selected_files"][0]["bytes"] = 60 * b.MIB
        self.preread["selected_file_bytes"] = 60 * b.MIB + 200
        self.update_preread()
        with self.assertRaisesRegex(b.PreparationError, "headroom"):
            self.assemble()

    def test_full_body_manifest_proof_cannot_exceed_child_witness_cap(self):
        self.preread["synthetic_extra_provenance"] = "x" * (2 * b.MIB)
        self.update_preread()
        with self.assertRaisesRegex(b.PreparationError, "witness cap"):
            self.assemble()

    def test_held_collector_bootstrap_cap(self):
        path = str(self.repo / b.HERE_REL / "collector.py")
        raw = b"x" * 65537
        self.artifacts[path] = (raw, b.pin_for(path, raw))
        self.refresh_ready()
        with self.assertRaisesRegex(b.PreparationError, "bootstrap cap"):
            self.assemble()

    def test_duplicate_json_and_nonfinite_rejected(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}'):
            with self.assertRaises(b.PreparationError):
                b.parse(raw)

    def test_preparation_read_rejects_symlink_and_hardlink(self):
        with tempfile.TemporaryDirectory(prefix="capture-b-pure-preparation-") as directory:
            import os
            path = Path(directory) / "source.json"
            path.write_bytes(b"{}\n")
            symlink = Path(directory) / "link.json"
            symlink.symlink_to(path)
            with self.assertRaises(OSError):
                b.read_preparation(symlink)
            hardlink = Path(directory) / "hard.json"
            os.link(path, hardlink)
            with self.assertRaisesRegex(b.PreparationError, "sole-link"):
                b.read_preparation(path)

    def test_preparation_read_exact_bytes_and_cap(self):
        with tempfile.TemporaryDirectory(prefix="capture-b-pure-preparation-") as directory:
            path = Path(directory) / "source.json"
            path.write_bytes(b"{}\n")
            raw, pin = b.read_preparation(path, 3)
            self.assertEqual(raw, b"{}\n")
            self.assertEqual(pin["bytes"], 3)
            with self.assertRaises(b.PreparationError):
                b.read_preparation(path, 2)


if __name__ == "__main__":
    unittest.main()
