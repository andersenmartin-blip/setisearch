"""Stdlib-only negative gate and byte custody checks; never calls produce."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("codec16_source_gate_test", ROOT / "run_codec16.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def pin(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


class SourceGateTests(unittest.TestCase):
    def test_authenticated_memory_helper_loaded_without_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "helper.py"
            path.write_bytes(b'raise ValueError("unverified disk reopen")\n')
            name = "_codec16_source_test_memory_helper"
            try:
                module = gate._load(name, path, b'proof = "authenticated memory"\n')
                self.assertEqual(module.proof, "authenticated memory")
                self.assertEqual(module.__file__, str(path))
            finally:
                sys.modules.pop(name, None)

    def test_duplicate_nonfinite_and_wrong_pin_refused(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            with self.assertRaises(ValueError):
                gate.parse(raw)
        with self.assertRaises(ValueError):
            gate._pin(b"{}", {"bytes": 2, "sha256": "0" * 64})
        with self.assertRaises(ValueError):
            gate._pin(b"x", {"bytes": True, "sha256": hashlib.sha256(b"x").hexdigest()})

    def test_bounded_ordinary_file_and_symlink_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ordinary = root / "value"
            ordinary.write_bytes(b"12345")
            with self.assertRaises(ValueError):
                gate.read_regular(ordinary, maximum=4)
            linked = root / "linked"
            linked.symlink_to(ordinary)
            with self.assertRaises(ValueError):
                gate.read_regular(linked)

    def test_complete_inventory_alteration_and_extra_file_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            files = {}
            for relative in gate.REQUIRED:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                raw = b"one immutable artifact\n"
                path.write_bytes(raw)
                files[relative] = pin(raw)
            raw = canonical({"schema": "codec16-G-leaf-artifacts-v1", "files": files,
                             "total_raw_bytes": sum(value["bytes"] for value in files.values()),
                             "self_hash_excluded": True})
            self.assertEqual(set(gate.verify_leaf(root, raw, pin(raw))), gate.REQUIRED)
            (root / "unexpected").write_bytes(b"extra")
            with self.assertRaises(ValueError):
                gate.verify_leaf(root, raw, pin(raw))
            (root / "unexpected").unlink()
            (root / "preparation.py").write_bytes(b"different")
            with self.assertRaises(ValueError):
                gate.verify_leaf(root, raw, pin(raw))

    def test_dispatch_malformed_scope_extra_key_and_false_authorization_refused(self):
        files = {"retained-draft/" + name: (ROOT / "retained-draft" / name).read_bytes()
                 for name in ("PLAN.json", "INPUT_MANIFEST.json", "SELECTED_CODE.json")}
        dispatch = {"schema": "codec16-fresh-engineering-dispatch-v1", "scope_id": "codec16-g-test-only",
                    "plan_sha256": hashlib.sha256(files["retained-draft/PLAN.json"]).hexdigest(),
                    "input_manifest_sha256": hashlib.sha256(files["retained-draft/INPUT_MANIFEST.json"]).hexdigest(),
                    "selection_sha256": hashlib.sha256(files["retained-draft/SELECTED_CODE.json"]).hexdigest(),
                    "runtime_prefix": "/only-a-source-test", "outer_supervisor_scope_sha256": "1" * 64,
                    "engineering_execution_authorized": True}
        raw = canonical(dispatch)
        self.assertEqual(gate.inspect_dispatch(raw, pin(raw), files), dispatch)
        # Accepted schema is inspected only. No effectful producer is called.
        for changed in ({**dispatch, "scope_id": []}, {**dispatch, "extra": 1},
                        {**dispatch, "engineering_execution_authorized": False},
                        {**dispatch, "plan_sha256": "0" * 64}):
            raw = canonical(changed)
            with self.assertRaises(ValueError):
                gate.inspect_dispatch(raw, pin(raw), files)

    def test_output_must_be_new_and_outside_leaf(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            leaf = root / "leaf"
            leaf.mkdir()
            gate.inspect_output(root / "future-output", leaf)
            for output in (leaf / "inside", leaf, Path("relative")):
                with self.assertRaises(ValueError):
                    gate.inspect_output(output, leaf)

    def test_native_imports_and_call_only_deferred(self):
        for name in ("run_codec16.py", "codec16_control.py", "preparation.py"):
            tree = ast.parse((ROOT / name).read_bytes())
            for node in tree.body:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                    self.assertFalse(any(value.split(".")[0] in ("numpy", "h5py", "hdf5plugin") for value in names))
        self.assertTrue(all(name not in sys.modules for name in ("numpy", "h5py", "hdf5plugin", "codec16_control")))

    def test_retained_plan_manifest_and_selected_pins_unchanged(self):
        expected = {"PLAN.json": "8c08a43b6a3b20792585e327b85d98caf04fc523f7ecd153b3165703ece4464f",
                    "INPUT_MANIFEST.json": "f37b59cec67e2fc4bcbf6006b67661ee630505aa7ad0703ec3949cf4d3a71fb0",
                    "SELECTED_CODE.json": "3f66b1724165be840357cb61c1e2dfba9e259f74eb96ddc53c5c2974f0777d55"}
        for name, sha in expected.items():
            self.assertEqual(hashlib.sha256((ROOT / "retained-draft" / name).read_bytes()).hexdigest(), sha)

    def test_entire_retained_draft_matches_original_checkpoint(self):
        retained = ROOT / "retained-draft"
        checkpoint = gate.parse((retained / "CHECKPOINT.json").read_bytes())
        observed = {path.relative_to(retained).as_posix() for path in retained.rglob("*")
                    if path.is_file() and path.name != "CHECKPOINT.json"}
        self.assertEqual(observed, set(checkpoint["files"]))
        self.assertEqual(len(observed), checkpoint["file_count_excluding_checkpoint"])
        for relative, expected in checkpoint["files"].items():
            raw = (retained / relative).read_bytes()
            self.assertEqual(len(raw), expected["bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), expected["sha256"])


if __name__ == "__main__":
    unittest.main()
