#!/usr/bin/env python3
"""Deterministically package two completed DEV_RUNTIME cases and selected files.

Ordinary stdlib tar/gzip only. This does not import scientific dependencies,
generate values, search, or modify the once-only case outputs.
"""
from __future__ import annotations

import time
PROCESS_STARTED = time.monotonic()

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import resource
import tarfile

ROOT = Path(__file__).resolve().parent.parent


def regular_file(path: Path) -> Path:
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError(f"Symlink source refused: {path}")
    if not path.is_file():
        raise ValueError(f"Explicit regular file required: {path}")
    return path.resolve()


def binding(path: Path) -> dict:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return {"SHA256": h.hexdigest(), "size_bytes": path.stat().st_size}


def checked_case(path: Path, project_root: Path) -> list[tuple[str, Path, dict]]:
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_dir():
        raise ValueError("Case source must be a nonsymlink directory")
    path = path.resolve()
    if path.name not in {"case_000", "case_001"}:
        raise ValueError("Exactly DEV_RUNTIME case_000 and case_001 required")
    marker_path = regular_file(path / "COMMITTED.json")
    marker = json.loads(marker_path.read_text())
    if (marker.get("status") != "COMPLETED_CASE_ONLY" or marker.get("panel") != "DEV_RUNTIME"
            or marker.get("caps_passed") is not True or marker.get("science_unchanged") is not True
            or marker.get("A_remains_FAIL_CLOSED") is not True
            or marker.get("no_retry_or_redraw") is not True):
        raise ValueError("Durable DEV_RUNTIME completion marker required before case reads")
    manifest_path = regular_file(path / "artifact_manifest.json")
    if binding(manifest_path)["SHA256"] != marker["artifact_manifest_SHA256"]:
        raise ValueError("COMMITTED artifact manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text())
    required = {f"scan_{i:02d}_full_map.npz" for i in range(6)} | {
        "admission.json", "case_definition.json", "truth.json", "synthetic_array_hashes.json",
        "geometry_arrays.npz", "geometry.json", "scan_map_metadata.json",
        "all_ON_threshold_carriers.json", "detector_summary.json", "localized_recovery.json",
        "outcome.json", "outcomes.json", "resource_receipt.json", "single_case_status.json"}
    if not required.issubset(manifest):
        raise ValueError("Complete original six-map scientific output set required")
    names = {p.name for p in path.iterdir()}
    if names != set(manifest) | {"COMMITTED.json", "artifact_manifest.json"}:
        raise ValueError("Full case directory differs from committed manifest")
    files = []
    for name in sorted(names):
        if Path(name).name != name:
            raise ValueError("Nested/traversal case filename refused")
        source = regular_file(path / name)
        observed = binding(source)
        if name in manifest and observed != manifest[name]:
            raise ValueError(f"Committed file binding mismatch: {name}")
        files.append((source.relative_to(project_root).as_posix(), source, observed))
    return files


class HashingReader:
    def __init__(self, file):
        self.file = file
        self.sha256 = hashlib.sha256()
        self.size = 0

    def read(self, size=-1):
        block = self.file.read(size)
        self.sha256.update(block)
        self.size += len(block)
        return block


def archive(path: Path, files: list[tuple[str, Path, dict]]) -> dict:
    if len({name for name, _, _ in files}) != len(files):
        raise ValueError("Duplicate tar member names")
    with path.open("xb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=6, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w|", format=tarfile.USTAR_FORMAT) as tar:
                for name, source, expected in sorted(files):
                    regular_file(source)
                    info = tarfile.TarInfo(name)
                    info.size = expected["size_bytes"]
                    info.mtime = 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mode = 0o644
                    info.type = tarfile.REGTYPE
                    with source.open("rb") as f:
                        checked = HashingReader(f)
                        tar.addfile(info, checked)
                    if checked.size != expected["size_bytes"] or checked.sha256.hexdigest() != expected["SHA256"]:
                        raise ValueError(f"Source bytes changed while archiving {name}")
        raw.flush()
        os.fsync(raw.fileno())
    blob = hashlib.sha1()
    blob.update(f"blob {path.stat().st_size}\0".encode("ascii"))
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            blob.update(block)
    return {**binding(path), "git_blob_SHA1": blob.hexdigest(),
            "members": {name: expected for name, _, expected in sorted(files)}}


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive completed DEV_RUNTIME outputs without scientific execution")
    parser.add_argument("--case-directory", type=Path, action="append", required=True,
                        help="Repeat exactly twice, for case_000 and case_001")
    parser.add_argument("--metadata-path", type=Path, action="append", required=True,
                        help="Explicit selected regular file; repeat as needed, no directory crawling")
    parser.add_argument("--output-directory", type=Path, required=True, help="New directory only")
    parser.add_argument("--project-root", type=Path, default=ROOT,
                        help="Root used for full project-relative archive member names")
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    if len(args.case_directory) != 2 or {p.name for p in args.case_directory} != {"case_000", "case_001"}:
        raise ValueError("Both distinct DEV_RUNTIME case directories required")
    cases = {p.name: checked_case(p, project_root) for p in args.case_directory}
    metadata = []
    for path in args.metadata_path:
        source = regular_file(path)
        try:
            name = source.relative_to(project_root).as_posix()
        except ValueError as exc:
            raise ValueError("Selected metadata file must be under this project root") from exc
        metadata.append((name, source, binding(source)))
    if any(p.is_symlink() for p in (args.output_directory, *args.output_directory.parents)):
        raise ValueError("Symlink output path refused")
    args.output_directory.mkdir(parents=True, exist_ok=False)
    result = {"format": "deterministic USTAR/gzip", "gzip_mtime": 0,
              "tar_mtime": 0, "uid": 0, "gid": 0, "uname": "", "gname": "",
              "scientific_values_generated": False, "archives": {}}
    for case_name in sorted(cases):
        name = f"dev_runtime_{case_name}.tar.gz"
        result["archives"][name] = archive(args.output_directory / name, cases[case_name])
    name = "dev_runtime_metadata_logs.tar.gz"
    result["archives"][name] = archive(args.output_directory / name, metadata)
    destination = args.output_directory / "archive_manifest.json"
    with destination.open("x") as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    usage = resource.getrusage(resource.RUSAGE_SELF)
    receipt = {"operation": "deterministic DEV_RUNTIME artifact archives only",
               "wall_s": time.monotonic() - PROCESS_STARTED,
               "cpu_s": float(usage.ru_utime + usage.ru_stime),
               "peak_rss_bytes": int(usage.ru_maxrss * 1024),
               "scope": "process startup through all three archive writes, hashes and manifest flush; excludes this receipt and final stdout",
               "scientific_values_generated": False}
    with (args.output_directory / "archive_resource_receipt.json").open("x") as f:
        json.dump(receipt, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    print(json.dumps({"output_directory": str(args.output_directory.resolve()),
                      "archives": {name: {k: value[k] for k in ("SHA256", "size_bytes", "git_blob_SHA1")}
                                   for name, value in result["archives"].items()}}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
