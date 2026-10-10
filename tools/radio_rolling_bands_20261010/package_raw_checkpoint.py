#!/usr/bin/env python3
"""Once-only raw-input ZIP checkpoint after root GO and complete acquisition QA.

This module imports only the Python standard library. Compact HDF5 files are
copied and hashed as opaque bytes; no HDF5/NPZ decoding, source HTTP, detector
search, normalization or profile projection occurs. ZIP_STORED preserves the
already compressed source chunks without a second compression pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import resource
import shutil
import signal
import time
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[2]
TOOLS = "tools/radio_rolling_bands_20261010"
STAGE = "results/radio_rolling_bands_20261010"
COMMON_SCOPE = TOOLS + "/scope.json"
COMMON_SCOPE_SHA = "9670e4c961d349dc3cc320a16b8c2f705928edeb58c543aa5d52166a6c021e7a"
CHUNKS = (155, 157)
QA_COMMON_SCOPE_FIELD = "common_four_batch_scope_sha256"
QA_CODE_SHA = "953fe609e16c095af34618bbf43f0060dfa9715f3707d7b560f3267ab3048494"
EXPECTED_PRIOR_CHUNKS = ()
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
COUNT = 1048576
CPU_CAP, WALL_CAP, MEMORY_CAP = 60, 300, 4 * 1024**3
WORKSPACE_CAP = 8 * 1024**3
PENDING_OUTPUT_RESERVE = 512 * 1024**2
BLOCK = 1024**2
GUIDE = TOOLS + "/RAW_CHECKPOINT_REPRODUCTION.md"
GUIDE_SHA = "bf7e48e9bf22b32ed26eaf06223122aeffea4032a86c1afff84ff8056b18230b"
SCRIPT = TOOLS + "/package_raw_checkpoint.py"
QA_SCRIPT = STAGE + "/review/qa_completed_acquisition.py"
EXTRA_METADATA_PINS = {'results/radio_rolling_bands_20261010/INDEPENDENT_STATIC_REVIEW.json': '27c1b4ade643e0c5258278a1d81094f723ad4d9411c4a814cceaa9a9db5bb3ae', 'results/radio_rolling_bands_20261010/METADATA_QA_RECEIPT.json': '1936d78f524c90f88073e8dd4395f4f74b5f813fe273d9670631f9e5b9219a59', 'results/radio_rolling_bands_20261010/ROOT_METADATA_STATIC_REVIEW.json': 'dbfcdba25916297ac81a20a75367d97474805a7b14a79cb1fccc84c3c2b54f2d'}
PRIVATE_PATTERNS = (
    re.compile(rb"\blibfile_[0-9a-f]{16,}\b"),
    re.compile(rb"\bfile_[0-9a-f]{16,}\b"),
    re.compile(rb"[?&](?:sig|token|access_token|X-Amz-Signature|X-Goog-Signature)=", re.I),
    re.compile(rb'"(?:reported_weekly_remaining_percent|reported_resets)"\s*:'),
)


def check(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(BLOCK), b""):
            value.update(block)
    return value.hexdigest()


def canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def save_new(path, value):
    with path.open("xb") as handle:
        handle.write(canonical(value))


def project_path(name):
    relative = Path(name)
    check(not relative.is_absolute() and ".." not in relative.parts, "Unsafe member path: " + name)
    path = ROOT / relative
    check(path.resolve().is_relative_to(ROOT), "Member escapes project: " + name)
    check(all(not part.is_symlink() for part in (path, *path.parents) if part != ROOT.parent),
          "Symlink input forbidden: " + name)
    check(path.is_file(), "Required input missing: " + name)
    return path


def read_json(name, expected=None):
    raw = project_path(name).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    check(expected is None or actual == expected, "Metadata SHA differs: " + name)
    return json.loads(raw), {"sha256": actual, "bytes": len(raw)}


def workspace_bytes(directory):
    # Directory metadata only; file contents are never opened here.
    return sum(path.stat().st_size for path in directory.rglob("*") if path.is_file() and not path.is_symlink())


def measured(started):
    return {"process_CPU_seconds_including_imports": time.process_time(),
            "wall_seconds": time.monotonic() - started,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def validate_caps(usage):
    check(usage["process_CPU_seconds_including_imports"] <= CPU_CAP
          and usage["wall_seconds"] <= WALL_CAP and usage["peak_RSS_bytes"] <= MEMORY_CAP,
          "Measured raw-checkpoint resource cap exceeded")


def collect_inputs(chunk, expected_qa_sha, freeze_commit):
    common, common_pin = read_json(COMMON_SCOPE, COMMON_SCOPE_SHA)
    check(common["source_chunk_ids"] == list(CHUNKS) and common["old_holdouts_reopened"] is False
          and common["protected_old_native_chunks_not_read"] == [156, 159], "Wrong frozen chunk family")
    context = common["chunk_contracts"][str(chunk)]
    scope_name = context["acquisition_scope_path"]
    scope, scope_pin = read_json(scope_name, context["acquisition_scope_sha256"])
    check(scope["native_chunk_index"] == chunk and scope["attempts"] == 1, "Wrong acquisition scope")
    arrays = scope["output_directory"]
    check(arrays == f"{STAGE}/chunk{chunk}/arrays", "Wrong fixed compact directory")
    result_name, ledger_name = arrays + "/ACQUISITION_RESULT.json", arrays + "/SOURCE_BODY_LEDGER.json"
    qa_name = arrays + "/ACQUISITION_OUTPUT_QA_RECEIPT.json"
    result, result_pin = read_json(result_name)
    ledger, ledger_pin = read_json(ledger_name)
    qa, qa_pin = read_json(qa_name, expected_qa_sha)
    check(result["status"] == "COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY"
          and ledger["complete"] is True, "Partial acquisition cannot be checkpointed as complete")
    check(qa["status"] == "PASS_COMPLETE_SOURCE_BYTES_AND_ALL96_DECODED_ROWS"
          and qa["source_chunk_id"] == chunk and qa["freeze_commit"] == freeze_commit,
          "Independent complete acquisition QA/freeze identity required")
    check(qa["counts"] == {"source_requests": 96, "compact_files": 6, "retained_compressed_chunks": 96,
                           "decoded_rows": 96, "decoded_values_authenticated": 100663296}, "Incomplete QA counts")
    check(qa["acquisition_result_sha256"] == result_pin["sha256"]
          and qa["source_BODY_ledger_sha256"] == ledger_pin["sha256"]
          and qa[QA_COMMON_SCOPE_FIELD] == common_pin["sha256"]
          and qa["acquisition_scope_sha256"] == scope_pin["sha256"], "QA input identities differ")
    check(qa["qa_script_sha256"] == QA_CODE_SHA == digest(project_path(QA_SCRIPT)), "Independent QA code differs")
    check(result["native_chunk_index"] == chunk and result["source_channel0"] == chunk * COUNT
          and result["physical_channel_interval_half_open"] == [chunk * COUNT, (chunk + 1) * COUNT],
          "Acquisition native source interval differs")
    check(result["qualification"] == "FAIL_CLOSED_UNCHANGED" and result["cost_DKK"] == 0
          and result["whole_original_telescope_MD5_verified"] is False
          and result["new_observation_visit"] is False, "Acquisition scientific gate differs")
    check(result["completion_resource_guard"]["status"] == "PASS_BEFORE_COMPLETE"
          and result["end_of_run_pinned_file_readback"] == "PASS_SCOPE_SCRIPT_MANIFEST_HELPER_AND_ALL_OTHER_SCOPE_PINS",
          "Missing acquisition completion guards")
    check(result["scope_sha256"] == scope_pin["sha256"]
          and result["script_sha256"] == context["acquisition_script_sha256"]
          and result["source_manifest_sha256"] == context["source_manifest_sha256"]
          and qa["acquisition_script_sha256"] == context["acquisition_script_sha256"]
          and qa["source_manifest_sha256"] == context["source_manifest_sha256"], "Acquisition provenance differs")
    expected_body = scope["expected_new_spectral_BODY_bytes"]
    check(result["new_spectral_BODY_bytes"] == qa["actual_new_BODY_bytes"] == expected_body
          and result["new_spectral_BODY_charged_upper_bound"] == qa["new_BODY_charged_upper_bound"] == expected_body + 96,
          "Actual/conservative BODY totals differ")
    check(ledger["new_value_requests_attempted"] == 96
          and ledger["source_body_bytes_received"] - ledger["prior_body_bytes"] == expected_body
          and ledger["source_body_bytes_charged_upper_bound"] - ledger["prior_charged_upper_bound_bytes"] == expected_body + 96,
          "Complete acquisition BODY ledger differs")
    pins = dict(common["pinned_dependency_files"])
    pins.update(scope["pinned_files"])
    pins[COMMON_SCOPE] = COMMON_SCOPE_SHA
    pins[TOOLS + "/native_search.py"] = common["script_sha256"]
    pins[TOOLS + "/generate_scope.py"] = common["scope_generator_sha256"]
    pins[result_name], pins[ledger_name], pins[qa_name] = result_pin["sha256"], ledger_pin["sha256"], qa_pin["sha256"]
    pins[QA_SCRIPT] = QA_CODE_SHA
    pins.update(EXTRA_METADATA_PINS)
    pins[GUIDE] = GUIDE_SHA
    pins[SCRIPT] = digest(project_path(SCRIPT))
    # Native158 requires the completed155/157 metadata chain, not their spectra.
    prerequisites = scope.get("prior_verified_acquisitions", [])
    check(tuple(p["native_chunk_index"] for p in prerequisites) == EXPECTED_PRIOR_CHUNKS,
          "Wrong prospective prerequisite acquisition family")
    prior_chain = []
    for prior in prerequisites:
        old_result, old_result_pin = read_json(prior["acquisition_summary_path"])
        old_ledger, old_ledger_pin = read_json(prior["source_BODY_ledger_path"])
        old_qa, old_qa_pin = read_json(prior["QA_receipt_path"])
        check(old_result["status"] == "COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY"
              and old_ledger["complete"] is True
              and old_qa["status"] == "PASS_COMPLETE_SOURCE_BYTES_AND_ALL96_DECODED_ROWS",
              "Complete independently verified prerequisite required")
        check(old_result["native_chunk_index"] == old_qa["source_chunk_id"] == prior["native_chunk_index"]
              and old_qa["qa_script_sha256"] == prior["QA_script_sha256"]
              and old_qa["freeze_commit"] == prior["public_freeze_commit"]
              and old_qa["common_four_batch_scope_sha256"] == prior["common_scope_sha256"],
              "Prerequisite QA and public freeze identity differs")
        check(old_qa["acquisition_result_sha256"] == old_result_pin["sha256"]
              and old_qa["source_BODY_ledger_sha256"] == old_ledger_pin["sha256"],
              "Prerequisite independent QA receipt identity differs")
        for field, key in (("scope", "acquisition_scope_sha256"),
                           ("script", "acquisition_script_sha256"),
                           ("source_manifest", "source_manifest_sha256")):
            check(old_result[field + "_sha256"] == old_qa[key] == prior[key],
                  "Prerequisite source/acquisition provenance differs")
        check(old_result["new_spectral_BODY_bytes"] == old_qa["actual_new_BODY_bytes"] == prior["exact_spectral_BODY_bytes"]
              and old_result["new_spectral_BODY_charged_upper_bound"] == old_qa["new_BODY_charged_upper_bound"] == prior["exact_spectral_BODY_bytes"] + 96
              and old_ledger["source_body_bytes_received"] == prior["expected_final_cadence_BODY_bytes"]
              and old_ledger["source_body_bytes_charged_upper_bound"] == prior["expected_final_cadence_charged_bytes"],
              "Prerequisite actual/conservative BODY accounting differs")
        observed = {"native_chunk_index": prior["native_chunk_index"],
                    "acquisition_summary_sha256": old_result_pin["sha256"],
                    "source_BODY_ledger_sha256": old_ledger_pin["sha256"],
                    "QA_receipt_sha256": old_qa_pin["sha256"]}
        prior_chain.append(observed)
        for path_key, pin in (("acquisition_summary_path", old_result_pin),
                              ("source_BODY_ledger_path", old_ledger_pin), ("QA_receipt_path", old_qa_pin)):
            pins[prior[path_key]] = pin["sha256"]
    if prerequisites:
        check(result["prior_complete_verified_acquisitions"] == qa["prior_complete_verified_acquisitions"] == prior_chain,
              "Completed source/independent QA prerequisite hashes differ")
    for name, expected in pins.items():
        path = project_path(name)
        check(path.suffix in (".py", ".json", ".md"), "Only allowlisted public metadata/code accepted")
        raw = path.read_bytes()
        check(not any(pattern.search(raw) for pattern in PRIVATE_PATTERNS), "Private identity or signed URL in metadata: " + name)
        check(hashlib.sha256(raw).hexdigest() == expected, "Frozen code/metadata differs: " + name)
    records, qa_files = result["decoded_files"], qa["files"]
    check(len(records) == len(qa_files) == 6 and [r["scan_id"] for r in records] == list(SCANS)
          and [r["scan_id"] for r in qa_files] == list(SCANS), "Exactly six ordered compact files required")
    raw_pins = {}
    for record, checked in zip(records, qa_files):
        scan = record["scan_id"]
        name = arrays + f"/{scan}.compact.h5"
        check(record["array_file"] == f"{scan}.compact.h5" and record["source_channel0"] == chunk * COUNT
              and record["shape"] == [16, 1, COUNT] and len(record["decoded_rows"]) == 16,
              "Wrong compact file/shape/origin metadata")
        check(checked["file_sha256"] == record["file_sha256"] and checked["bytes"] == record["bytes"]
              and checked["retained_compressed_chunks_checked"] == checked["decoded_rows_checked"] == 16,
              "Independent QA compact file identity differs")
        path = project_path(name)
        check(path.stat().st_size == record["bytes"], "Compact file size differs: " + name)
        raw_pins[name] = {"sha256": record["file_sha256"], "bytes": record["bytes"]}
    return pins, raw_pins, result, qa


def zip_info(name):
    info = zipfile.ZipInfo(name, date_time=(2026, 10, 10, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o100644 << 16
    return info


def add_file(archive, name, expected_sha, expected_bytes=None):
    path = project_path(name)
    before = path.stat()
    value, crc, size = hashlib.sha256(), 0, 0
    with path.open("rb") as source, archive.open(zip_info(name), "w", force_zip64=True) as target:
        for block in iter(lambda: source.read(BLOCK), b""):
            target.write(block); value.update(block); crc = zlib.crc32(block, crc); size += len(block)
    after = path.stat()
    check((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
          == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), "Source changed during copy: " + name)
    check(size == before.st_size and (expected_bytes is None or size == expected_bytes)
          and value.hexdigest() == expected_sha, "Copied source SHA/size differs: " + name)
    return {"path": name, "bytes": size, "sha256": value.hexdigest(), "member_CRC32_hex": f"{crc & 0xffffffff:08x}"}


def verify_archive(path, members):
    with zipfile.ZipFile(path, "r") as archive:
        check(len(archive.namelist()) == len(set(archive.namelist())) and set(archive.namelist()) == set(members),
              "ZIP member inventory differs")
        for name, expected in members.items():
            info = archive.getinfo(name)
            check(info.compress_type == zipfile.ZIP_STORED, "Unexpected ZIP compression")
            value, crc, size = hashlib.sha256(), 0, 0
            with archive.open(info, "r") as source:
                for block in iter(lambda: source.read(BLOCK), b""):
                    value.update(block); crc = zlib.crc32(block, crc); size += len(block)
            check(size == info.file_size == expected["bytes"] and value.hexdigest() == expected["sha256"]
                  and f"{crc & 0xffffffff:08x}" == expected["member_CRC32_hex"] and info.CRC == crc & 0xffffffff,
                  "ZIP SHA/size/CRC readback differs: " + name)


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunk", type=int, choices=CHUNKS, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--expected-script-sha256", required=True)
    parser.add_argument("--expected-acquisition-qa-sha256", required=True)
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--root-go-after-complete-acquisition-qa", action="store_true", required=True)
    args = parser.parse_args()
    archive_path = args.archive.absolute()
    check(archive_path == ROOT.parent / f"SETI_NATIVE{args.chunk}_RAW_2026-10-10.zip", "Use the exact fixed scratch ZIP path")
    check(re.fullmatch(r"[0-9a-f]{40}", args.freeze_commit), "Exact public freeze commit required")
    check(digest(Path(__file__)) == args.expected_script_sha256, "Packager script differs from reviewed pin")
    checkpoint_dir = ROOT / f"{STAGE}/chunk{args.chunk}/raw_checkpoint"
    check(not archive_path.exists() and not archive_path.is_symlink(), "Refuse existing ZIP/path")
    check(not checkpoint_dir.exists() and not checkpoint_dir.is_symlink(), "Raw checkpoint attempt is once only")

    def deadline(signum, frame):
        raise TimeoutError("Raw checkpoint CPU/wall limit")

    signal.signal(signal.SIGALRM, deadline); signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(WALL_CAP)
    checkpoint_dir.mkdir()
    save_new(checkpoint_dir / "RAW_CHECKPOINT_STARTED.json", {
        "source_chunk_id": args.chunk, "attempts": 1, "retry_or_replace_authorized": False,
        "packager_sha256": args.expected_script_sha256, "acquisition_QA_sha256": args.expected_acquisition_qa_sha256,
        "freeze_commit": args.freeze_commit, "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP, "memory_cap_bytes": MEMORY_CAP,
    })
    try:
        pins, raw_pins, acquisition, qa = collect_inputs(args.chunk, args.expected_acquisition_qa_sha256, args.freeze_commit)
        names = sorted(set(pins) | set(raw_pins))
        estimate = sum(project_path(name).stat().st_size for name in names) + 2 * 1024**2
        current_workspace = workspace_bytes(ROOT.parent)
        check(current_workspace + estimate + PENDING_OUTPUT_RESERVE <= WORKSPACE_CAP, "Conservative workspace reserve exceeds cap")
        check(shutil.disk_usage(ROOT.parent).free > estimate + PENDING_OUTPUT_RESERVE, "Insufficient free disk reserve")
        members = {}
        manifest_name = f"{STAGE}/chunk{args.chunk}/raw_checkpoint/RAW_CHECKPOINT_PAYLOAD_MANIFEST.json"
        with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for name in names:
                expected = raw_pins.get(name)
                members[name] = add_file(archive, name, expected["sha256"] if expected else pins[name],
                                         expected["bytes"] if expected else None)
            manifest = {
                "schema": "SETI_COMPLETE_NATIVE_RAW_CHECKPOINT_PAYLOAD_V1", "source_chunk_id": args.chunk,
                "public_scientific_freeze_commit": args.freeze_commit, "common_analysis_scope_sha256": COMMON_SCOPE_SHA,
                "independent_acquisition_QA_sha256": args.expected_acquisition_qa_sha256,
                "packager_script_sha256": args.expected_script_sha256,
                "compression": "ZIP_STORED_OPAQUE_BYTE_COPY", "compact_HDF5_files": 6,
                "raw_source_BODY_bytes": acquisition["new_spectral_BODY_bytes"],
                "new_source_HTTP_requests_by_packager": 0, "HDF5_or_NPZ_decodes_by_packager": 0,
                "numerical_measurement_or_profile_runs_by_packager": 0,
                "scientific_qualification": "FAIL_CLOSED_UNCHANGED", "whole_original_telescope_MD5_verified": False,
                "independent_observation_visit": False, "cost_DKK": 0,
                "scope": "Six compact retained native-frequency chunks from the same historical ON/OFF visit, with exact frozen manifests/code and independent acquisition receipts. No new origin/significance/sensitivity claim.",
                "members": [members[name] for name in names],
                "self_reference_rule": "The payload manifest omits itself and the full ZIP SHA. Full ZIP SHA and this member SHA appear only in the external archive manifest.",
            }
            manifest_bytes = canonical(manifest)
            save_new(checkpoint_dir / "RAW_CHECKPOINT_PAYLOAD_MANIFEST.json", manifest)
            archive.writestr(zip_info(manifest_name), manifest_bytes)
            members[manifest_name] = {"path": manifest_name, "bytes": len(manifest_bytes),
                                      "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                                      "member_CRC32_hex": f"{zlib.crc32(manifest_bytes) & 0xffffffff:08x}"}
        verify_archive(archive_path, members)
        archive_sha = digest(archive_path)
        for name, expected in pins.items():
            check(digest(project_path(name)) == expected, "Metadata/code changed before COMPLETE: " + name)
        usage = measured(started)
        validate_caps(usage)
        final = {
            "schema": "SETI_COMPLETE_NATIVE_RAW_CHECKPOINT_ARCHIVE_MANIFEST_V1",
            "status": "PASS_COMPLETE_OPAQUE_BYTE_COPY_ZIP_SHA_SIZE_ALL_MEMBER_SHA_CRC_READBACK",
            "source_chunk_id": args.chunk, "public_scientific_freeze_commit": args.freeze_commit,
            "archive": {"filename": archive_path.name, "bytes": archive_path.stat().st_size, "sha256": archive_sha},
            "members": [members[name] for name in sorted(members)], "verified_member_count": len(members),
            "input_metadata_file_sha256": pins, "independent_acquisition_QA_sha256": args.expected_acquisition_qa_sha256,
            "packager_script_sha256": args.expected_script_sha256, "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP,
            "memory_cap_bytes": MEMORY_CAP, "workspace_cap_bytes": WORKSPACE_CAP,
            "workspace_bytes_before_archive": current_workspace, "pending_output_reserve_bytes": PENDING_OUTPUT_RESERVE,
            "completion_resource_guard": "PASS_BEFORE_COMPLETE_EXTERNAL_MANIFEST", **usage,
            "new_source_HTTP_requests": 0, "HDF5_or_NPZ_decodes": 0, "numerical_measurement_or_profile_runs": 0,
            "retry_or_replace_authorized": False, "cost_DKK": 0, "scientific_qualification": "FAIL_CLOSED_UNCHANGED",
        }
        save_new(checkpoint_dir / "RAW_CHECKPOINT_ARCHIVE_MANIFEST.json", final)
        print(json.dumps({key: final[key] for key in ("status", "source_chunk_id", "archive", "verified_member_count", *usage)}, allow_nan=False), flush=True)
    except BaseException as exc:
        save_new(checkpoint_dir / "RAW_CHECKPOINT_FAILURE.json", {
            "status": "RAW_CHECKPOINT_FAILED_OR_PARTIAL_NO_RETRY", "source_chunk_id": args.chunk,
            "error_type": type(exc).__name__, "error": str(exc), "retry_authorized": False,
            "partial_archive_exists": archive_path.exists(), **measured(started),
            "new_source_HTTP_requests": 0, "HDF5_or_NPZ_decodes": 0, "numerical_measurement_runs": 0,
        })
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
