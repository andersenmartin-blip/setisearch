"""Prospective risks for content-addressed archive batching and grouped readback."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from seti_repeater import event_archive_batch_radio as r
from seti_repeater.empty_null_radio import canonical


class BatchArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", "-b", "m43-support-qualification", self.root], check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.org"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=self.root, check=True)
        (self.root / "README.md").write_bytes(b"untouched\n")
        source = self.root / r.SOURCE_PREFIX
        source.mkdir(parents=True)
        for index in range(67):
            data = (bytes(range(256)) if index % 9 == 0 else canonical({"index": index})) * (index + 1)
            (source / ("part%03d" % index)).write_bytes(data)
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "source"], cwd=self.root, check=True)
        self.parent = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root).decode().strip()

    def tearDown(self):
        self.tmp.cleanup()

    def freeze(self):
        return r.prepare_freeze(self.root, self.parent)

    def publish_locally(self, freeze):
        for target, pin in freeze["files"].items():
            path = self.root / target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(subprocess.check_output(["git", "show", freeze["source_commit"] + ":" + pin["source_path"]], cwd=self.root))
        subprocess.run(["git", "add", r.PREFIX], cwd=self.root, check=True)
        tree = subprocess.check_output(["git", "write-tree"], cwd=self.root).decode().strip()
        self.assertEqual(tree, freeze["expected_tree"])
        subprocess.run(["git", "commit", "-qm", "atomic archive"], cwd=self.root, check=True)
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root).decode().strip()

    def test_exact_blob_reuse_batches_tree_and_grouped_readback(self):
        freeze = self.freeze()
        self.assertEqual(freeze["file_count"], 67)
        self.assertEqual([b["entries"] for b in freeze["batches"]], [32, 32, 3])
        self.assertEqual(freeze["source_cat_file_batch_operations"], 1)
        commit = self.publish_locally(freeze)
        result = r.verify_readback(self.root, commit, freeze)
        self.assertEqual(result["git_cat_file_batch_operations"], 1)
        for target, pin in freeze["files"].items():
            actual = subprocess.check_output(["git", "rev-parse", commit + ":" + target], cwd=self.root).decode().strip()
            self.assertEqual(actual, pin["blob"])

    def test_target_reuse_is_refused(self):
        freeze = self.freeze()
        self.publish_locally(freeze)
        with self.assertRaisesRegex(ValueError, "Fresh immutable"):
            r.prepare_freeze(self.root, "HEAD")

    def test_changed_source_or_limit_is_refused(self):
        freeze = self.freeze()
        bad = copy.deepcopy(freeze)
        path = next(iter(bad["files"]))
        bad["files"][path]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "freeze or source"):
            r.validate_freeze(self.root, bad, require_parent=self.parent)
        bad = copy.deepcopy(freeze)
        bad["limits"]["stored_bytes"] += 1
        with self.assertRaisesRegex(ValueError, "limits changed"):
            r.validate_freeze(self.root, bad)

    def test_parent_conflict_and_existing_target_stop_before_mutation(self):
        freeze = self.freeze()
        with self.assertRaisesRegex(ValueError, "parent conflicts"):
            r.validate_freeze(self.root, freeze, require_parent="a" * 40)
        self.assertFalse((self.root / r.PREFIX).exists())

    def test_corrupt_or_incomplete_readback_fails(self):
        freeze = self.freeze()
        commit = self.publish_locally(freeze)
        bad = copy.deepcopy(freeze)
        path = next(iter(bad["files"]))
        bad["files"][path]["bytes"] += 1
        with self.assertRaisesRegex(ValueError, "readback differs"):
            r.verify_readback(self.root, commit, bad)
        bad = copy.deepcopy(freeze)
        bad["expected_tree"] = "a" * 40
        with self.assertRaisesRegex(ValueError, "tree differs"):
            r.verify_readback(self.root, commit, bad)

    def test_freeze_is_canonical_deterministic_and_non_scientific(self):
        first = self.freeze()
        second = self.freeze()
        self.assertEqual(canonical(first), canonical(second))
        self.assertFalse(first["execution_restart_authorized"])
        self.assertFalse(first["scientific_admission_authorized"])
        self.assertEqual(first["new_random_values"], 0)
        self.assertEqual(first["mutation_commits"], 1)
        self.assertEqual(first["ref_updates"], 1)


if __name__ == "__main__":
    unittest.main()
