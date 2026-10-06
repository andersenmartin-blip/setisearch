"""Cold source-freeze validation with metadata stubs; no module execution."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import contract
import run_preflight


class SourceFreezeTests(unittest.TestCase):
    def fixture(self, root):
        files = {}
        for name in sorted(run_preflight.REQUIRED_MODULES):
            raw = b'# metadata-only source stub; never compiled\n'
            (root / name).write_bytes(raw)
            files[name] = contract.raw_pin(raw)
        return {"schema": "codec12-I-source-freeze-v1", "status": "BLOCKED_PENDING_OUTER_NATIVE_LIFETIME",
                "execution_enabled": False, "authority_commit": contract.H_COMMIT, "files": files,
                "total_raw_bytes": sum(row["bytes"] for row in files.values()), "self_hash_excluded": True,
                "original_inputs": {"domain": "metadata_stub_only"}}

    def verify(self, root, freeze):
        raw = contract.canonical(freeze)
        return run_preflight.verify_source_freeze(root, raw, {"bytes": len(raw), "sha256": contract.sha(raw)})

    def test_all_frozen_source_bodies_checked_without_compilation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); freeze = self.fixture(root)
            _, contents = self.verify(root, freeze)
            self.assertEqual(set(contents), run_preflight.REQUIRED_MODULES)
            (root / "contract.py").write_bytes(b"mutated\n")
            with self.assertRaises(ValueError): self.verify(root, freeze)

    def test_external_pin_wrong_or_bool_size_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); freeze = self.fixture(root); raw = contract.canonical(freeze)
            for pin in ({"bytes": len(raw), "sha256": "0" * 64}, {"bytes": True, "sha256": contract.sha(raw)}):
                with self.assertRaises(ValueError): run_preflight.verify_source_freeze(root, raw, pin)

    def test_execution_true_or_self_hash_false_cannot_activate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); original = self.fixture(root)
            for key, value in (("execution_enabled", True), ("self_hash_excluded", False), ("status", "READY")):
                freeze = copy.deepcopy(original); freeze[key] = value
                with self.assertRaises(ValueError): self.verify(root, freeze)

    def test_missing_module_and_self_reference_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); original = self.fixture(root)
            freeze = copy.deepcopy(original); freeze["files"].pop("contract.py")
            with self.assertRaises(ValueError): self.verify(root, freeze)
            freeze = copy.deepcopy(original); freeze["files"]["SOURCE_FREEZE.json"] = contract.raw_pin(b"self")
            with self.assertRaises(ValueError): self.verify(root, freeze)

    def test_escape_symlink_hardlink_and_blob_mismatch_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); original = self.fixture(root)
            freeze = copy.deepcopy(original); freeze["files"]["../escape"] = contract.raw_pin(b"x")
            with self.assertRaises(ValueError): self.verify(root, freeze)
            freeze = copy.deepcopy(original); freeze["files"]["contract.py"]["git_blob_sha1"] = "0" * 40
            with self.assertRaises(ValueError): self.verify(root, freeze)
            source = root / "preflight.py"; source.rename(root / "retained")
            source.symlink_to(root / "retained")
            with self.assertRaises(ValueError): self.verify(root, original)

    def test_total_size_and_pin_field_mutations_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); original = self.fixture(root)
            freeze = copy.deepcopy(original); freeze["total_raw_bytes"] += 1
            with self.assertRaises(ValueError): self.verify(root, freeze)
            freeze = copy.deepcopy(original); freeze["files"]["contract.py"]["extra"] = True
            with self.assertRaises(ValueError): self.verify(root, freeze)

    def test_json_duplicate_and_nonfinite_freeze_denied(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            with self.assertRaises(ValueError): run_preflight.parse(raw)


if __name__ == "__main__":
    unittest.main()
