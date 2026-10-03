#!/usr/bin/env python3
"""Small isolated lossless, reproducibility, and hostile-restore regression cases."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

import zstandard

SCRIPT = Path(__file__).with_name("evidence_archive.py").resolve()
RECORDS = []


def run(*args, success=True):
    result = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                            capture_output=True, text=True)
    RECORDS.append({"args": list(map(str, args)), "returncode": result.returncode,
                    "stdout": result.stdout, "stderr": result.stderr,
                    "expected_success": success})
    if success and result.returncode:
        raise AssertionError(result.stderr)
    if not success and result.returncode == 0:
        raise AssertionError("hostile or corrupt operation unexpectedly passed")
    return result


def malformed_bundle(directory, *, path="x.bin", kind=tarfile.REGTYPE,
                     duplicate=False, missing=False):
    """Digest-valid wrapper: restore must reject structure, not only digests."""
    payload = b"preserved evidence bytes"
    digest = hashlib.sha256(payload).hexdigest()
    manifest = {"schema": "seti-lossless-evidence-source-manifest-v1", "files": [
        {"path": path, "bytes": len(payload), "sha256": digest, "mode": 0o644}]}
    manifest_bytes = json.dumps(manifest).encode()
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        info = tarfile.TarInfo("source-manifest.json")
        info.size = len(manifest_bytes)
        tar.addfile(info, io.BytesIO(manifest_bytes))
        if not missing:
            for _ in range(2 if duplicate else 1):
                info = tarfile.TarInfo("blobs/" + digest)
                info.type = kind
                info.size = len(payload) if kind == tarfile.REGTYPE else 0
                info.linkname = "../../escape"
                tar.addfile(info, io.BytesIO(payload) if info.size else None)
    compressed = zstandard.ZstdCompressor(level=1).compress(raw.getvalue())
    directory.mkdir()
    name = "evidence.tar.zst.part0000"
    (directory / name).write_bytes(compressed)
    (directory / "source-manifest.json").write_bytes(manifest_bytes)
    archive = {"schema": "seti-lossless-evidence-archive-v1", "compressed_bytes": len(compressed),
        "compressed_sha256": hashlib.sha256(compressed).hexdigest(),
        "source_manifest_bytes": len(manifest_bytes),
        "source_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "source_logical_bytes": len(payload), "source_file_count": 1,
        "unique_blob_count": 1, "unique_blob_bytes": len(payload),
        "parts": [{"filename": name, "bytes": len(compressed),
                   "sha256": hashlib.sha256(compressed).hexdigest()}]}
    (directory / "archive-manifest.json").write_text(json.dumps(archive))


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="seti-archive-test-")
        self.base = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def source(self):
        root = self.base / "source"
        (root / "acquisition-candidate" / "attempt01").mkdir(parents=True)
        payload = bytes(range(256)) * 100
        (root / "acquisition-candidate" / "attempt01" / "native.npy").write_bytes(payload)
        (root / "acquisition-candidate" / "attempt01" / "normalized.npy").write_bytes(payload)
        (root / "empty.txt").write_bytes(b"")
        (root / "never_execute.py").write_text("raise RuntimeError('EVIDENCE WAS EXECUTED')\n")
        (root / "æøå.json").write_text('{"ok":true}\n')
        for excluded in ("publication", "publishing", ".hidden", "__pycache__"):
            (root / excluded).mkdir()
            (root / excluded / "excluded.bin").write_bytes(b"excluded")
        (root / "handoff-observation-01").mkdir()
        (root / "handoff-observation-01" / "failure.log").write_text("retained failed attempt")
        return root

    def test_roundtrip_dedup_and_stream_verify(self):
        root = self.source()
        archive, restored = self.base / "archive", self.base / "restored"
        run("build", "--root", root, "--output", archive)
        manifest = json.loads((archive / "source-manifest.json").read_bytes())
        self.assertEqual(manifest["source_file_count"], 6)
        self.assertEqual(manifest["unique_blob_count"], 5)
        run("verify", "--archive", archive, "--source-root", root)
        run("restore", "--archive", archive, "--dest", restored)
        for entry in manifest["files"]:
            self.assertEqual((root / entry["path"]).read_bytes(), (restored / entry["path"]).read_bytes())
        a = restored / "acquisition-candidate/attempt01/native.npy"
        b = restored / "acquisition-candidate/attempt01/normalized.npy"
        self.assertNotEqual(a.stat().st_ino, b.stat().st_ino)
        a.write_bytes(b"independent copy")
        self.assertNotEqual(a.read_bytes(), b.read_bytes())

    def test_reproducible_across_output_locations(self):
        root = self.source()
        a, b = self.base / "bundle-a", self.base / "bundle-b"
        run("build", "--root", root, "--output", a)
        run("build", "--root", root, "--output", b)
        self.assertEqual((a / "source-manifest.json").read_bytes(), (b / "source-manifest.json").read_bytes())
        self.assertEqual((a / "archive-manifest.json").read_bytes(), (b / "archive-manifest.json").read_bytes())
        self.assertEqual((a / "evidence.tar.zst.part0000").read_bytes(), (b / "evidence.tar.zst.part0000").read_bytes())

    def test_corruption_and_changed_source_rejected(self):
        root, archive = self.source(), self.base / "bundle"
        run("build", "--root", root, "--output", archive)
        (root / "empty.txt").write_bytes(b"changed")
        run("verify", "--archive", archive, "--source-root", root, success=False)
        part = archive / "evidence.tar.zst.part0000"
        part.write_bytes(part.read_bytes() + b"corrupt")
        dest = self.base / "rejected"
        run("restore", "--archive", archive, "--dest", dest, success=False)
        self.assertFalse(dest.exists())

    def test_traversal_symlink_duplicate_missing_and_pax_rejected(self):
        cases = [dict(path="../escape"), dict(path="/absolute"),
                 dict(path="a/../escape"), dict(kind=tarfile.SYMTYPE),
                 dict(kind=tarfile.LNKTYPE), dict(kind=tarfile.XHDTYPE),
                 dict(duplicate=True), dict(missing=True)]
        for i, kwargs in enumerate(cases):
            with self.subTest(kwargs=kwargs):
                archive, dest = self.base / f"hostile-{i}", self.base / f"restore-{i}"
                malformed_bundle(archive, **kwargs)
                run("restore", "--archive", archive, "--dest", dest, success=False)
                self.assertFalse(dest.exists())
                self.assertFalse((self.base / "escape").exists())

    def test_source_symlink_rejected(self):
        root = self.source()
        (root / "link").symlink_to(root / "empty.txt")
        run("build", "--root", root, "--output", self.base / "bad-source", success=False)
        self.assertFalse((self.base / "bad-source").exists())

    def test_fixed_compressed_cap_rejected_and_partial_bundle_removed(self):
        root = self.source()
        # Incompressible isolated test data, never telescope or candidate evidence.
        (root / "incompressible-test.bin").write_bytes(os.urandom(2 * 1024 * 1024))
        output = self.base / "over-cap"
        run("build", "--root", root, "--output", output,
            "--archive-cap-mib", "1", success=False)
        self.assertFalse(output.exists())
        self.assertFalse(list(self.base.glob(".archive-staging-*")))

    def test_short_write_regression(self):
        spec = importlib.util.spec_from_file_location("owned_archive_support", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class PartialWriter(io.BytesIO):
            def write(self, data):
                return super().write(data[:7])

        payload = bytes(range(256)) * 100
        out = PartialWriter()
        module.write_all(out, payload)
        self.assertEqual(out.getvalue(), payload)

    def test_real_multiple_parts_roundtrip(self):
        root = self.source()
        (root / "multi-part-test.bin").write_bytes(os.urandom(3 * 1024 * 1024))
        output, dest = self.base / "multi-bundle", self.base / "multi-restored"
        run("build", "--root", root, "--output", output)
        manifest = json.loads((output / "archive-manifest.json").read_bytes())
        self.assertEqual(len(manifest["parts"]), 4)
        self.assertTrue(all(part["bytes"] <= 1024 * 1024 for part in manifest["parts"]))
        run("restore", "--archive", output, "--dest", dest)
        self.assertEqual((root / "multi-part-test.bin").read_bytes(), (dest / "multi-part-test.bin").read_bytes())


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ArchiveTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    output = Path(__file__).with_name("test-results.json")
    output.write_text(json.dumps({"schema": "seti-evidence-archive-isolated-tests-v1",
        "tests_run": result.testsRun, "success": result.wasSuccessful(), "subprocesses": RECORDS}, indent=2) + "\n")
    sys.exit(0 if result.wasSuccessful() else 1)
