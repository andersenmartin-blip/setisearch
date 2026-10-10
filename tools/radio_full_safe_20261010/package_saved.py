#!/usr/bin/env python3
"""Build and verify one result ZIP after root GO; read array files as bytes only.

Inputs are the current phase, exact scope-pinned imported code/metadata, final
report and reproduction tools. Raw HDF5 files, wheels, caches, private transfer
helpers and opaque native IDs are excluded. The embedded manifest lists payload
hashes/sizes/CRCs; the ZIP SHA exists only in the external package receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import time
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[2]
TOOLS = "tools/radio_full_safe_20261010"
STAGE = "results/radio_full_safe_20261010"
SCOPE = TOOLS + "/scope.json"
GUIDE = TOOLS + "/REPRODUCTION.md"
REPORT = "RADIO_FULL_SAFE_REPORT_2026-10-10.md"
SUMMARY = STAGE + "/summary/FULL_SAFE_SUMMARY.json"
MANIFEST = STAGE + "/packaging/PACKAGE_MANIFEST.json"
ARCHIVE_NAME = "SETI_FULL_SAFE_RESULTS_2026-10-10.zip"
SELECTION_SHA = "81bdd9b01d32c5d1fffd54df30d036a2aab29035c8d9e29d21b564e166d67120"
RAW_ARCHIVE_SHA = "6696fe54086e019ce966816dc818969ca5f1682e3ff9211326f1a68d2323ef1d"
CPU_CAP, WALL_CAP, MEMORY_CAP = 60, 1800, 4*1024**3
CHUNK = 1024**2
TEXT_SUFFIXES = {".json", ".md", ".py", ".txt", ".log", ".csv", ".sha256", ".svg"}
ALLOWED_SUFFIXES = TEXT_SUFFIXES | {".npz", ".png", ".jpg", ".jpeg", ".pdf", ".gz"}
EXCLUDED_COMPONENTS = {"__pycache__", ".git", ".cache", "cache", "wheels", "deps",
                       "private", "library_helpers", "library_helpers_current", "packaging"}
PRIVATE_PATTERNS = (
    re.compile(rb"\blibfile_[0-9a-f]{16,}\b"),
    re.compile(rb"\bfile_[0-9a-f]{16,}\b"),
    re.compile(rb"[?&](?:sig|token|access_token|X-Amz-Signature|X-Goog-Signature)=",
               re.IGNORECASE),
    re.compile(rb'"(?:reported_weekly_remaining_percent|reported_resets)"\s*:'),
)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def load_json(root, name, expected=None):
    raw = (root/name).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if expected is not None and actual != expected:
        raise ValueError("Metadata pin differs: " + name)
    return json.loads(raw), {"sha256": actual, "bytes": len(raw)}


def relative_path(root, name):
    relative = Path(name)
    path = root/relative
    if (relative.is_absolute() or ".." in relative.parts or path.is_symlink()
            or not path.resolve().is_relative_to(root)):
        raise ValueError("Non-project path or symlink forbidden: " + name)
    return path


def public_text(path, name):
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return
    raw = path.read_bytes()
    if any(pattern.search(raw) for pattern in PRIVATE_PATTERNS):
        raise ValueError("Private opaque ID, signed credential URL or account counter in public payload: " + name)


def collect_payload(root, scope):
    names = set(scope["pinned_dependency_files"])
    names.update((SCOPE, REPORT, GUIDE))
    for prefix in (TOOLS, STAGE):
        directory = root/prefix
        if not directory.is_dir():
            raise ValueError("Required phase directory missing: " + prefix)
        for path in directory.rglob("*"):
            relative = path.relative_to(root)
            if (any(part in EXCLUDED_COMPONENTS for part in relative.parts)
                    or path.is_dir() or path.suffix.lower() not in ALLOWED_SUFFIXES):
                continue
            names.add(relative.as_posix())
    forbidden = [name for name in names if Path(name).suffix.lower() in {".h5", ".hdf5", ".whl"}
                 or any(part in EXCLUDED_COMPONENTS for part in Path(name).parts)]
    if forbidden:
        raise ValueError("Raw source, dependency or private file entered payload list")
    for name in names:
        path = relative_path(root, name)
        if not path.is_file():
            raise ValueError("Required payload file missing: " + name)
        public_text(path, name)
    for name, expected in scope["pinned_dependency_files"].items():
        if digest(root/name) != expected:
            raise ValueError("Scope-pinned imported file differs: " + name)
    return sorted(names)


def verify_saved_inventory(root, scope, summary, mode):
    if (summary["metadata_selection_canonical_SHA256"] != SELECTION_SHA
            or summary["common_execution_scope_sha256"] != digest(root/SCOPE)
            or summary["expected_scan_tiles"] != 642 or summary["expected_profile_count"] != 18):
        raise ValueError("Final summary differs from frozen phase contract")
    if mode == "COMPLETE" and summary["both_batch_executions_complete"] is not True:
        raise ValueError("COMPLETE packaging needs both complete saved batch executions")
    pins = {}
    expected_tiles, expected_profiles = 0, 0
    for batch_id in (1, 2):
        prefix = f"{STAGE}/batch_{batch_id:02d}/measurement/"
        checkpoint_path = root/(prefix+"DRIFT_CHECKPOINT.json")
        checkpoint = None
        if checkpoint_path.is_file():
            checkpoint, _ = load_json(root, prefix+"DRIFT_CHECKPOINT.json")
            if (checkpoint["batch_id"] != batch_id
                    or checkpoint["fixed_batch_q"] != scope["batch_q"][batch_id-1]
                    or checkpoint["expected_scan_tiles"] != 321
                    or checkpoint["completed_scan_tiles"] != len(checkpoint["completed_receipts"])):
                raise ValueError("Checkpoint batch or count mismatch")
            expected_tiles += checkpoint["completed_scan_tiles"]
            for entry in checkpoint["completed_receipts"]:
                for key, sha_key, bytes_key in (
                    ("path", "sha256", "bytes"),
                    ("normalization_path", "normalization_sha256", "normalization_bytes")):
                    name = prefix+entry[key]
                    if name in pins:
                        raise ValueError("Duplicate inventory member: " + name)
                    pins[name] = {"sha256": entry[sha_key], "bytes": entry[bytes_key]}
            if mode == "COMPLETE" and (checkpoint["complete"] is not True
                                      or checkpoint["completed_scan_tiles"] != 321):
                raise ValueError("COMPLETE archive requires both 321-tile checkpoints")
        elif mode == "COMPLETE":
            raise ValueError("Missing complete batch checkpoint")
        profiles_path = root/(prefix+"FIXED_TOP3_PROFILES.json")
        if profiles_path.is_file():
            profiles, _ = load_json(root, prefix+"FIXED_TOP3_PROFILES.json")
            expected_profiles += len(profiles)
            for record in profiles:
                name = prefix+record["patch"]["path"]
                if name in pins:
                    raise ValueError("Duplicate profile inventory member: " + name)
                pins[name] = {"sha256": record["patch"]["sha256"], "bytes": record["patch"]["bytes"]}
        if mode == "COMPLETE":
            batch = summary["batches"][batch_id-1]
            if (batch["batch_id"] != batch_id or batch["execution_complete"] is not True
                    or batch["profile_count"] != 9 or not batch["QA_status"].startswith("PASS")):
                raise ValueError("COMPLETE archive requires independent PASS QA for each complete batch")
            actual_QA, actual_QA_pin = load_json(root, prefix+"QA_RECEIPT.json",
                                                batch["QA_receipt_sha256"])
            if actual_QA["status"] != batch["QA_status"]:
                raise ValueError("Actual QA annotation differs from the summarized pinned receipt")
            for required in ("EXECUTION_RECEIPT.json", "QA_RECEIPT.json", "DRIFT_TOP20.json",
                             "FIXED_TOP3_PROFILES.json"):
                if not (root/(prefix+required)).is_file():
                    raise ValueError("Required complete batch evidence missing: " + prefix+required)
    if (expected_tiles != summary["completed_scan_tiles"]
            or expected_profiles != summary["profile_count"]
            or (mode == "COMPLETE" and (expected_tiles != 642 or expected_profiles != 18))):
        raise ValueError("Saved inventory and final summary counts differ")
    for name, expected in pins.items():
        path = relative_path(root, name)
        if (not path.is_file() or path.stat().st_size != expected["bytes"]
                or digest(path) != expected["sha256"]):
            raise ValueError("Saved map/normalization/profile hash or size differs: " + name)
    return pins, expected_tiles, expected_profiles


def zip_info(name):
    info = zipfile.ZipInfo(name, date_time=(2026, 10, 10, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info._compresslevel = 1
    info.external_attr = 0o100644 << 16
    return info


def add_file(archive, root, name):
    path = root/name
    before = path.stat()
    h, crc, size = hashlib.sha256(), 0, 0
    with path.open("rb") as source, archive.open(zip_info(name), "w", force_zip64=True) as target:
        for block in iter(lambda: source.read(CHUNK), b""):
            target.write(block)
            h.update(block)
            crc = zlib.crc32(block, crc)
            size += len(block)
    after = path.stat()
    if (size != before.st_size or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns):
        raise ValueError("Payload changed during ZIP creation: " + name)
    return {"path": name, "bytes": size, "sha256": h.hexdigest(), "member_CRC32_hex": f"{crc & 0xffffffff:08x}"}


def verify_archive(path, members):
    with zipfile.ZipFile(path, "r") as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("Duplicate ZIP member")
        if set(archive.namelist()) != set(members):
            raise ValueError("ZIP member list differs from expected public payload")
        for name, expected in members.items():
            info = archive.getinfo(name)
            h, crc, size = hashlib.sha256(), 0, 0
            with archive.open(info, "r") as handle:
                for block in iter(lambda: handle.read(CHUNK), b""):
                    h.update(block)
                    crc = zlib.crc32(block, crc)
                    size += len(block)
            if (size != expected["bytes"] or info.file_size != size
                    or h.hexdigest() != expected["sha256"]
                    or f"{crc & 0xffffffff:08x}" != expected["member_CRC32_hex"]
                    or info.CRC != crc & 0xffffffff):
                raise ValueError("ZIP SHA256, size or member CRC differs: " + name)
    return len(members)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--archive", required=True)
    parser.add_argument("--expected-scope-sha256", required=True)
    parser.add_argument("--mode", choices=("COMPLETE", "PARTIAL"), required=True)
    parser.add_argument("--root-authorized-package-read", action="store_true")
    args = parser.parse_args()
    if not args.root_authorized_package_read:
        raise SystemExit("Explicit root GO is required before reading result payload bytes")
    started = time.monotonic()
    for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[key] = "1"
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP+1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    def deadline(signum, frame):
        raise TimeoutError("Packaging CPU/wall cap exceeded")
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    signal.alarm(WALL_CAP)
    root = Path(args.root).resolve()
    archive_path = Path(args.archive).resolve()
    temporary = archive_path.with_suffix(".zip.tmp")
    output = root/(STAGE+"/packaging")
    if archive_path.name != ARCHIVE_NAME:
        raise ValueError("Use the one declared result archive name")
    if archive_path.exists() or temporary.exists() or output.exists():
        raise ValueError("Package destination or packaging evidence already exists")
    scope, scope_pin = load_json(root, SCOPE, args.expected_scope_sha256)
    summary, summary_pin = load_json(root, SUMMARY)
    if not (root/GUIDE).is_file() or not (root/REPORT).is_file():
        raise ValueError("Final report and existing REPRODUCTION.md are required")
    report_text = (root/REPORT).read_text()
    if "RAPPORTUDKAST" in report_text or "AFVENTER FÆRDIGE" in report_text:
        raise ValueError("Report is still an unexecuted draft")
    inventory_pins, map_count, profile_count = verify_saved_inventory(root, scope, summary, args.mode)
    payloads = collect_payload(root, scope)
    if set(inventory_pins)-set(payloads) or SUMMARY not in payloads:
        raise ValueError("A required saved map or summary was omitted")
    snapshot_pins = {name: {"bytes": (root/name).stat().st_size, "sha256": digest(root/name)} for name in payloads}
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=1, allowZip64=True) as archive:
        for name in payloads:
            entry = add_file(archive, root, name)
            if any(entry[key] != snapshot_pins[name][key] for key in ("bytes", "sha256")):
                raise ValueError("Payload differs from pre-package snapshot: " + name)
            entries.append(entry)
        manifest = {
            "schema": "SETI_FULL_SAFE_PUBLIC_PACKAGE_MANIFEST_V1",
            "archive_filename": ARCHIVE_NAME,
            "mode": args.mode,
            "payload_member_count": len(entries),
            "completed_scan_tiles": map_count,
            "completed_fixed_profiles": profile_count,
            "public_code_freeze_commit": summary["public_code_freeze_commit"],
            "common_execution_scope_sha256": scope_pin["sha256"],
            "summary_sha256": summary_pin["sha256"],
            "metadata_selection_canonical_SHA256": SELECTION_SHA,
            "batch_rankings_remain_separate": True,
            "profile_identity_fields": ["batch_id", "track_id"],
            "members": entries,
            "manifest_excludes_its_own_hash_and_CRC": True,
            "ZIP_SHA256_recorded_only_in_external_receipt": True,
            "raw_HDF5_files_embedded": False,
            "runtime_wheels_embedded": False,
            "required_external_input_archive": {
                "filename": "SETI_FRESH_BAND151_RAW_2026-10-09.zip",
                "bytes": 305428707, "sha256": RAW_ARCHIVE_SHA},
            "one_historical_visit": True,
            "new_telescope_HTTP_requests": 0, "new_telescope_BODY_bytes": 0,
            "original_full_source_file_MD5_verified": False,
            "NPZ_or_HDF5_numeric_values_decoded_during_packaging": False,
        }
        manifest_raw = (json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False)+"\n").encode()
        archive.writestr(zip_info(MANIFEST), manifest_raw)
    members = {entry["path"]: entry for entry in entries}
    members[MANIFEST] = {"bytes": len(manifest_raw), "sha256": hashlib.sha256(manifest_raw).hexdigest(),
                         "member_CRC32_hex": f"{zlib.crc32(manifest_raw) & 0xffffffff:08x}"}
    verified_members = verify_archive(temporary, members)
    for name, expected in snapshot_pins.items():
        if (root/name).stat().st_size != expected["bytes"] or digest(root/name) != expected["sha256"]:
            raise ValueError("Original payload changed before final ZIP verification: " + name)
    if digest(root/SCOPE) != args.expected_scope_sha256:
        raise ValueError("Frozen scope changed during packaging")
    zip_sha, zip_bytes = digest(temporary), temporary.stat().st_size
    resources = {"process_CPU_seconds_including_imports": time.process_time(),
                 "wall_seconds_including_imports": time.monotonic()-started,
                 "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
    if (resources["process_CPU_seconds_including_imports"] > CPU_CAP
            or resources["wall_seconds_including_imports"] > WALL_CAP
            or resources["peak_RSS_bytes"] > MEMORY_CAP):
        raise TimeoutError("Measured packaging resources exceed caps")
    temporary.replace(archive_path)
    output.mkdir(parents=True, exist_ok=False)
    (output/"PACKAGE_MANIFEST.json").write_bytes(manifest_raw)
    receipt = {
        "status": "PASS_ARCHIVE_SHA256_SIZE_AND_EVERY_MEMBER_CRC_AND_SHA256",
        "archive_filename": ARCHIVE_NAME,
        "archive_bytes": zip_bytes, "archive_sha256": zip_sha,
        "mode": args.mode, "verified_member_count_including_manifest": verified_members,
        "payload_member_count": len(entries), "completed_scan_tiles": map_count,
        "completed_fixed_profiles": profile_count,
        "embedded_manifest_path": MANIFEST,
        "embedded_manifest_sha256": members[MANIFEST]["sha256"],
        "script_sha256": digest(Path(__file__)),
        "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP, "memory_cap_bytes": MEMORY_CAP,
        "raw_HDF5_or_wheels_embedded": False,
        "private_transfer_helpers_or_native_IDs_embedded": False,
        "NPZ_or_HDF5_numeric_values_decoded": False,
        "detector_rerun": False, **resources,
    }
    (output/"PACKAGE_RECEIPT.json").write_text(json.dumps(receipt, indent=2, allow_nan=False)+"\n")
    signal.alarm(0)
    print(json.dumps(receipt, allow_nan=False))


if __name__ == "__main__":
    main()
