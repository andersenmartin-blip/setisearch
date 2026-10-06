"""Manufactured filesystem controls; no real target execution or package import."""
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("recovery", Path(__file__).with_name("recovery.py"))
r = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(r)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.source = self.base / "source"; self.source.mkdir()
        self.interpreter = self.base / "python"; self.interpreter.write_bytes(b"not an executable")
        self.sources = {"site_packages": str(self.source), "python": str(self.interpreter)}
        self.root = self.base / "new-copy"

    def tearDown(self): self.temp.cleanup()

    def row(self, name="fixture.bin", raw=b"original bytes", mode=0o644):
        path = self.source / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        return {"path": r.PREFIX + name, "bytes": len(raw), "mode": mode, "sha256": hashlib.sha256(raw).hexdigest()}

    def copy(self, row): return r.recover([row], self.sources, self.root)

    def test_matching_bytes_new_identity(self):
        row = self.row(); result = self.copy(row)
        outcome = result["outcomes"][0]
        self.assertEqual(result["copied_files"], 1)
        self.assertNotEqual(outcome["source_identity"][:2], outcome["candidate_identity"][:2])
        self.assertFalse(result["runtime_qualified"])
        self.assertEqual(r.verify_candidate(self.root, result)["files"], 1)

    def test_same_size_hash_mismatch_retained_nonexecutably(self):
        row = self.row(mode=0o755); (self.source / "fixture.bin").write_bytes(b"different data")
        result = self.copy(row)
        self.assertEqual(result["outcomes"][0]["status"], "SOURCE_HASH_MISMATCH_RETAINED")
        staging = self.root / result["outcomes"][0]["retained_staging"]
        self.assertEqual(staging.read_bytes(), b"different data")
        self.assertEqual(staging.stat().st_mode & 0o777, 0o600)
        self.assertFalse((self.root / "candidate").exists())

    def test_size_mismatch_not_read(self):
        row = self.row(); (self.source / "fixture.bin").write_bytes(b"x")
        result = self.copy(row)
        self.assertEqual(result["read_bytes"], 0)
        self.assertEqual(result["outcomes"][0]["status"], "SOURCE_SIZE_MISMATCH")

    def test_missing_preserved(self):
        row = self.row(); (self.source / "fixture.bin").unlink()
        result = self.copy(row)
        self.assertEqual(result["outcomes"][0]["status"], "MISSING_CURRENT_SOURCE")
        self.assertEqual(result["missing_or_mismatched"], 1)

    def test_no_cfg_reconstruction(self):
        row = self.row(); row["path"] = "venv/pyvenv.cfg"
        self.assertEqual(self.copy(row)["outcomes"][0]["status"], "NO_DECLARED_CURRENT_SOURCE")

    def test_zero_length_ordinary_copy(self):
        self.assertEqual(self.copy(self.row(raw=b""))["copied_files"], 1)

    def test_preserve_original_mode(self):
        result = self.copy(self.row(mode=0o755))
        self.assertEqual((self.root / result["outcomes"][0]["candidate_path"]).stat().st_mode & 0o777, 0o755)

    def test_existing_output_refused(self):
        row = self.row(); self.root.mkdir(); (self.root / "foreign").write_text("retain")
        with self.assertRaises(FileExistsError): self.copy(row)
        self.assertEqual((self.root / "foreign").read_text(), "retain")

    def test_output_parent_symlink_refused(self):
        row = self.row(); link = self.base / "alias"; link.symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(r.Refusal): r.recover([row], self.sources, link / "new")

    def test_source_leaf_symlink_refused_and_failure_retained(self):
        row = self.row(); target = self.source / "fixture.bin"; target.unlink(); target.symlink_to(self.interpreter)
        with self.assertRaises(r.Refusal): self.copy(row)
        self.assertIn(b"failure", (self.root / "COPY.events.jsonl").read_bytes())

    def test_source_parent_symlink_refused(self):
        row = self.row("dir/file"); alias = self.source / "alias"; alias.symlink_to(self.source / "dir", target_is_directory=True)
        row["path"] = r.PREFIX + "alias/file"
        with self.assertRaises(r.Refusal): self.copy(row)

    def test_invalid_path_refused_before_output(self):
        row = self.row(); row["path"] = "venv/../escape"
        with self.assertRaises(r.Refusal): self.copy(row)
        self.assertFalse(self.root.exists())

    def test_duplicate_rows_refused(self):
        row = self.row()
        with self.assertRaises(r.Refusal): r.validate_rows([row, row], 2, row["bytes"] * 2)

    def test_parent_file_collision_refused(self):
        one = self.row("a"); two = dict(one, path=r.PREFIX + "a/b")
        with self.assertRaises(r.Refusal): r.validate_rows([one, two], 2, one["bytes"] * 2)

    def test_boolean_size_refused(self):
        row = self.row(); row["bytes"] = True
        with self.assertRaises(r.Refusal): r.validate_rows([row], 1, 1)

    def test_boolean_count_refused(self):
        with self.assertRaises(r.Refusal): r.validate_rows([], False, 0)

    def test_uppercase_hash_refused(self):
        row = self.row(); row["sha256"] = row["sha256"].upper()
        with self.assertRaises(r.Refusal): self.copy(row)

    def test_duplicate_json_refused(self):
        with self.assertRaises(r.Refusal): r.parse(b'{"x":1,"x":2}')

    def test_nonfinite_json_refused(self):
        with self.assertRaises(r.Refusal): r.parse(b'{"x":NaN}')

    def test_altered_original_manifest_refused(self):
        with self.assertRaises(r.Refusal): r.expected_rows(b'{"inventory":{"entries":[]}}')

    def test_low_read_cap_retains_failed_copy(self):
        row = self.row()
        with patch.dict(r.LIMITS, {"read_bytes": 1}):
            with self.assertRaises(r.Refusal): self.copy(row)
        self.assertTrue((self.root / "COPY.events.jsonl").exists())
        self.assertFalse((self.root / "RESULT.json").exists())

    def test_low_artifact_cap_retains_failure(self):
        row = self.row()
        # Original row admission itself refuses an impossible envelope.
        with patch.dict(r.LIMITS, {"artifact_bytes": 1}):
            with self.assertRaises(r.Refusal): self.copy(row)
        self.assertFalse(self.root.exists())

    def test_wall_refusal(self):
        budget = r.Budget(); budget.started -= 121
        with self.assertRaises(r.Refusal): budget.check()

    def test_source_identity_change_refused(self):
        row = self.row(); real = r.signature; calls = 0
        def shifted(info):
            nonlocal calls
            calls += 1; value = real(info)
            if calls > 2: value[-1] += 1
            return value
        with patch.object(r, "signature", shifted):
            with self.assertRaises(r.Refusal): self.copy(row)
        self.assertTrue((self.root / "retained-staging" / row["path"]).exists())

    def test_candidate_body_change_refused(self):
        result = self.copy(self.row()); candidate = self.root / result["outcomes"][0]["candidate_path"]
        candidate.write_bytes(b"different data")
        with self.assertRaises(r.Refusal): r.verify_candidate(self.root, result)

    def test_candidate_missing_refused(self):
        result = self.copy(self.row()); (self.root / result["outcomes"][0]["candidate_path"]).unlink()
        with self.assertRaises(r.Refusal): r.verify_candidate(self.root, result)

    def test_candidate_extra_entry_refused(self):
        result = self.copy(self.row()); (self.root / "candidate" / "extra").write_bytes(b"extra")
        with self.assertRaises(r.Refusal): r.verify_candidate(self.root, result)

    def test_candidate_hardlink_refused(self):
        result = self.copy(self.row()); candidate = self.root / result["outcomes"][0]["candidate_path"]
        os.link(candidate, self.base / "second-link")
        with self.assertRaises(r.Refusal): r.verify_candidate(self.root, result)

    def test_candidate_mode_change_refused(self):
        result = self.copy(self.row()); os.chmod(self.root / result["outcomes"][0]["candidate_path"], 0o777)
        with self.assertRaises(r.Refusal): r.verify_candidate(self.root, result)

    def test_no_native_dispatch(self):
        with self.assertRaises(r.Refusal): r.native_dispatch("even if all hashes match")


class WrapperRefusals(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.base = Path(self.temp.name)
        spec = importlib.util.spec_from_file_location("driver", Path(__file__).with_name("run_recovery.py"))
        self.driver = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.driver)
        for name in ("recovery.py", "run_recovery.py"):
            (self.base / name).write_bytes(Path(__file__).with_name(name).read_bytes())
        self.freeze = {"status": "ADMINISTRATIVE_COPY_ONLY_NO_NATIVE_AUTHORITY",
                       "authority_commit": r.AUTHORITY, "limits": dict(r.LIMITS), "sources": dict(r.FIXED_SOURCES),
                       "source_files": {name: r.pin((self.base / name).read_bytes())
                                        for name in ("recovery.py", "run_recovery.py")}}
        self.manifest = self.base / "manifest.json"; self.manifest.write_bytes(b"altered")
        self.root = self.base / "no-output"

    def tearDown(self): self.temp.cleanup()

    def invoke(self, expected_hash=None):
        raw = r.canonical(self.freeze); (self.base / "SOURCE_FREEZE.json").write_bytes(raw)
        argv = ["driver", "--manifest", str(self.manifest), "--new-output", str(self.root),
                "--freeze-sha256", expected_hash or r.pin(raw)["sha256"]]
        with patch.object(self.driver, "HERE", self.base), patch.object(sys, "argv", argv):
            self.driver.main()

    def test_wrong_freeze_digest_no_output(self):
        with self.assertRaisesRegex(ValueError, "source freeze"): self.invoke("0" * 64)
        self.assertFalse(self.root.exists())

    def test_changed_executable_source_no_output(self):
        (self.base / "recovery.py").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "source member"): self.invoke()
        self.assertFalse(self.root.exists())

    def test_missing_driver_from_freeze_no_output(self):
        del self.freeze["source_files"]["run_recovery.py"]
        with self.assertRaisesRegex(ValueError, "both executable"): self.invoke()
        self.assertFalse(self.root.exists())

    def test_altered_authority_no_output(self):
        self.freeze["authority_commit"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "exact type/value"): self.invoke()
        self.assertFalse(self.root.exists())

    def test_changed_budget_no_output(self):
        self.freeze["limits"]["wall_seconds"] += 1
        with self.assertRaisesRegex(ValueError, "exact type/value"): self.invoke()
        self.assertFalse(self.root.exists())

    def test_altered_manifest_no_output(self):
        with self.assertRaisesRegex(ValueError, "manifest size"): self.invoke()
        self.assertFalse(self.root.exists())


if __name__ == "__main__": unittest.main(verbosity=2)
