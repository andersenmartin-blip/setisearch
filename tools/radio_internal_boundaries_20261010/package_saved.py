#!/usr/bin/env python3
"""Package the admitted joined-boundary family as unchanged opaque file bytes.

The companion summary module supplies only saved-JSON contract checks. Import
does not read files, import scientific libraries or execute a scientific helper.
"""
import time
WALL_STARTED = time.monotonic()
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import resource
import shutil
import signal
import zlib
import zipfile

import summarize_saved as contracts

CPU_CAP, WALL_CAP, MEMORY_CAP = 40, 1800, 4 * 1024**3
WORKSPACE_CAP = 8 * 1024**3
RESERVE = 512 * 1024**2
ARCHIVE_NAME = "SETI_INTERNAL_BOUNDARIES_RESULTS_2026-10-10.zip"
PACKAGING = contracts.STAGE + "/packaging"
EDITORIAL = contracts.STAGE + "/summary/EDITORIAL_RECEIPT.json"
GENERATED_REPORT = contracts.STAGE + "/summary/GENERATED_REPORT.md"
RUN_DIRECTORY = None
TEXT_SUFFIXES = {".json", ".md", ".py", ".txt", ".log", ".csv", ".sha256"}
OPAQUE_SUFFIXES = {".npz", ".png", ".svg", ".jpg", ".jpeg", ".pdf", ".gz"}
EXCLUDED_PARTS = {"__pycache__", ".git", ".cache", "cache", "wheels", "deps", "private", "privatework",
                  "library_helpers", "library_helpers_current", "packaging", "archive_parts_10MiB", "archive"}
check = contracts.check


def public_text(path):
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return
    raw = path.read_bytes()
    check(len(raw) <= 32*1024**2, "Public text member exceeds explicit bound")
    text = raw.decode("utf-8")
    check(not re.search(r"\b(?:libfile|file)_[0-9a-f]{16,}\b", text, re.I), "Private Library file identifier forbidden")
    check(not re.search(r"https?://[^\s\"<>]+[?&](?:sig|signature|token|se|sp)=", text, re.I), "Signed transfer URL forbidden")
    check(not re.search(r"(?:weekly|ugentlig|quota|reset|nulstilling)[^\n]{0,60}(?:\d+\s*%|\d+\s*(?:extra|ekstra))", text, re.I),
          "Private account usage metrics forbidden")


def snapshot(root, names):
    pins = {}
    for name in sorted(names):
        path = contracts.project_path(root, name)
        check(path.is_file(), "Archive member is not a regular file: "+name)
        check(not set(Path(name).parts) & EXCLUDED_PARTS, "Excluded archive member: "+name)
        check(path.suffix.lower() in TEXT_SUFFIXES | OPAQUE_SUFFIXES, "Unapproved archive member type: "+name)
        public_text(path)
        pins[name] = contracts.file_pin(path)
    return pins


def collect(root, scope, reader, pairs):
    names = set(reader.pins) | set(scope["pinned_dependency_files"])
    names.add(contracts.PINS)
    names.add(contracts.REPORT)
    for directory in (contracts.TOOLS, contracts.STAGE):
        for path in (root/directory).rglob("*"):
            check(not path.is_symlink(), "Symlink found in new evidence tree")
            if path.is_file() and not set(path.relative_to(root).parts) & EXCLUDED_PARTS:
                names.add(path.relative_to(root).as_posix())
    for pair in pairs:
        names.update(pair["output_byte_pins"])
        names.update(pair["runtime_admission_receipts"])
        names.update(pair["QA_opened_json_pins"])
    names.discard(PACKAGING+"/PACKAGE_STARTED.json")
    return names


def workspace_bytes(root):
    total = 0
    for directory, children, files in os.walk(root, followlinks=False):
        children[:] = [name for name in children if name != ".git"]
        for name in children+files:
            check(not (Path(directory)/name).is_symlink(), "Workspace symlink forbidden for resource accounting")
        for name in files:
            total += (Path(directory)/name).stat().st_size
    return total


def zip_info(name):
    info = zipfile.ZipInfo(name, (2026, 10, 10, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def add_file(archive, root, name, pin):
    path = contracts.project_path(root, name)
    before = path.stat()
    digest, size, crc = hashlib.sha256(), 0, 0
    with path.open("rb") as source, archive.open(zip_info(name), "w", force_zip64=True) as destination:
        for block in iter(lambda: source.read(1024**2), b""):
            destination.write(block)
            digest.update(block)
            size += len(block)
            crc = zlib.crc32(block, crc)
    after = path.stat()
    check((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), "Member changed while packaging: "+name)
    check({"sha256": digest.hexdigest(), "bytes": size} == pin, "Snapshot member bytes changed: "+name)
    check(archive.getinfo(name).CRC == crc & 0xffffffff, "Written member CRC differs")
    return crc & 0xffffffff


def verify_archive(path, pins, manifest_bytes):
    expected = set(pins) | {"ARCHIVE_MANIFEST.json"}
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        check(len(names) == len(expected) and len(names) == len(set(names)) and set(names) == expected,
              "Exact ZIP inventory required")
        for name in names:
            info = archive.getinfo(name)
            digest, size, crc = hashlib.sha256(), 0, 0
            with archive.open(info, "r") as stream:
                for block in iter(lambda: stream.read(1024**2), b""):
                    digest.update(block)
                    size += len(block)
                    crc = zlib.crc32(block, crc)
            pin = pins[name] if name != "ARCHIVE_MANIFEST.json" else {
                "sha256": hashlib.sha256(manifest_bytes).hexdigest(), "bytes": len(manifest_bytes)}
            check({"sha256": digest.hexdigest(), "bytes": size} == pin and info.file_size == size
                  and info.CRC == crc & 0xffffffff, "ZIP member SHA/size/CRC verification failed: "+name)


def check_summary(root, reader, scope, pairs, audit, args):
    late_pins = {}
    def read_pinned(name, expected):
        raw = contracts.project_path(root, name).read_bytes()
        pin = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        check(pin["sha256"] == expected, "Exact finished JSON SHA required: "+name)
        late_pins[name] = pin
        return json.loads(raw)
    def pin_output(name, expected):
        pin = contracts.file_pin(contracts.project_path(root, name))
        check(pin["sha256"] == expected, "Exact finished output SHA required: "+name)
        check(name not in late_pins or late_pins[name] == pin, "Conflicting late output declaration: "+name)
        late_pins[name] = pin
    summary = read_pinned(contracts.SUMMARY, args.expected_summary_sha256)
    receipt = read_pinned(contracts.SUMMARY_RECEIPT, args.expected_summary_receipt_sha256)
    pin_output(contracts.REPORT, args.expected_report_sha256)
    profiles = [p for pair in pairs for p in pair["profiles"]]
    check(summary["status"] == "COMPLETE_AUDITED_SAVED_BOUNDARY_FAMILY" and summary["scope_sha256"] == reader.pins[contracts.SCOPE]
          and summary["public_freeze_commit"] == args.freeze_commit and summary["pairs"] == pairs and summary["profiles"] == profiles
          and summary["joint_source_cell_QA"] == audit and summary["pair_ids"] == list(contracts.PAIR_IDS)
          and summary["original_new_pair_statuses_all_COMPLETE"] is True
          and summary["previous_native_terminal_statuses_rewritten"] is False
          and summary["completed_scan_tiles"] == 18 and summary["top20_records"] == 180 and summary["profile_count"] == 27
          and summary["evaluated_hypothesis_combinations"] == 112508928, "Summary differs from admitted original saved JSON")
    check(receipt["status"] == "PASS_PINNED_COMPLETE_BOUNDARY_JSON_SUMMARY_NO_NUMERIC_RERUN"
          and receipt["script_sha256"] == scope["summary_script_sha256"]
          and receipt["scope_sha256"] == reader.pins[contracts.SCOPE] and receipt["freeze_commit"] == args.freeze_commit
          and receipt["input_pins_sha256"] == reader.sha and receipt["opened_inputs"] == reader.opened
          and receipt["CPU_cap_s"] == 20 and receipt["wall_cap_s"] == 1800 and receipt["memory_cap_bytes"] == 2*1024**3
          and 0 < contracts.finite(receipt["process_CPU_seconds_including_imports"]) <= 20
          and 0 < contracts.finite(receipt["wall_seconds_including_imports"]) <= 1800
          and 0 < contracts.finite(receipt["peak_RSS_bytes"]) <= 2*1024**3
          and receipt["HDF5_or_NPZ_opened"] is False and receipt["detector_rerun"] is False
          and receipt["rankings_reselected"] is False and receipt["previous_native_terminal_statuses_rewritten"] is False,
          "Actual matching saved-only summary receipt required")
    expected_outputs = {contracts.SUMMARY, contracts.STAGE+"/summary/PROFILE_SUMMARY.csv", contracts.REPORT}
    check(set(receipt["output_hashes"]) == expected_outputs, "Exactly summary/CSV/report outputs required")
    original_report_sha = receipt["output_hashes"][contracts.REPORT]
    if original_report_sha == args.expected_report_sha256:
        check(args.expected_editorial_receipt_sha256 is None and not (root/EDITORIAL).exists()
              and not (root/GENERATED_REPORT).exists(), "Unchanged report requires no editorial bridge")
    else:
        check(args.expected_editorial_receipt_sha256 is not None, "Changed report requires explicit editorial receipt SHA")
        editorial = read_pinned(EDITORIAL, args.expected_editorial_receipt_sha256)
        pin_output(GENERATED_REPORT, original_report_sha)
        check(editorial["status"] == "PASS_EDITORIAL_REPORT_REVIEW_NO_NUMERIC_RERUN"
              and editorial["scope_sha256"] == reader.pins[contracts.SCOPE] and editorial["freeze_commit"] == args.freeze_commit
              and editorial["original_generated_report_sha256"] == original_report_sha
              and editorial["preserved_generated_report_path"] == GENERATED_REPORT
              and editorial["preserved_generated_report_sha256"] == original_report_sha
              and contracts.file_pin(root/GENERATED_REPORT)["sha256"] == original_report_sha
              and editorial["reviewed_report_sha256"] == args.expected_report_sha256
              and editorial["summary_sha256"] == args.expected_summary_sha256
              and editorial["summary_receipt_sha256"] == args.expected_summary_receipt_sha256
              and editorial["no_numeric_rerun"] is True and editorial["scientific_JSON_changed"] is False,
              "Editorial bridge must preserve generated report and every scientific input")
    for name, digest in receipt["output_hashes"].items():
        if name != contracts.REPORT:
            pin_output(name, digest)
    check(not (root/contracts.STAGE/"summary/SUMMARY_FAILURE_RECEIPT.json").exists(), "Failed summary cannot be packaged as COMPLETE")
    return summary, receipt, late_pins


def main():
    global RUN_DIRECTORY
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(contracts.ROOT))
    parser.add_argument("--archive", required=True)
    for name in ("expected-scope-sha256", "freeze-commit", "expected-summary-sha256", "expected-summary-receipt-sha256", "expected-report-sha256"):
        parser.add_argument("--"+name, required=True)
    parser.add_argument("--root-go-after-all-pairs-QA", action="store_true")
    parser.add_argument("--expected-editorial-receipt-sha256")
    args = parser.parse_args()
    check(args.root_go_after_all_pairs_QA, "Explicit root GO after all three QAs and joint source audit required")
    check(re.fullmatch(r"[0-9a-f]{40}", args.freeze_commit), "Exact public freeze commit required")
    for name in ("expected_scope_sha256", "expected_summary_sha256", "expected_summary_receipt_sha256", "expected_report_sha256"):
        check(re.fullmatch(r"[0-9a-f]{64}", getattr(args, name)), "Exact SHA256 required: "+name)
    check(args.expected_editorial_receipt_sha256 is None or re.fullmatch(r"[0-9a-f]{64}", args.expected_editorial_receipt_sha256),
          "Optional editorial receipt requires an exact SHA256")
    root, target = Path(args.root).resolve(), Path(args.archive).absolute()
    check(target.name == ARCHIVE_NAME and not target.is_symlink() and not target.exists(), "Single new archive destination required")
    check(target.parent.exists() and target.parent.is_dir() and target.parent.resolve() == target.parent,
          "Existing non-symlink archive parent required")
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP+1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    def deadline(signum, frame):
        raise TimeoutError("Boundary opaque package resource deadline exceeded")
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    signal.alarm(WALL_CAP)
    out = root/PACKAGING
    check(not out.exists(), "Boundary packaging is authorized once only")
    out.mkdir(parents=True, exist_ok=False)
    RUN_DIRECTORY = out
    contracts.save(out/"PACKAGE_STARTED.json", {"status": "STARTED_ONCE_ONLY_OPAQUE_BOUNDARY_PACKAGE",
         "freeze_commit": args.freeze_commit, "scope_sha256": args.expected_scope_sha256,
         "script_sha256": contracts.file_pin(Path(__file__))["sha256"], "archive_filename": target.name})
    reader = contracts.PinnedJSON(root, root/contracts.PINS)
    scope = contracts.verify_scope(reader, args.expected_scope_sha256)
    check(Path(__file__).resolve() == contracts.project_path(root, scope["package_script_path"]).resolve()
          and contracts.file_pin(Path(__file__))["sha256"] == scope["package_script_sha256"],
          "Executing package differs from frozen project code")
    check(scope["package_CPU_cap_s"] == CPU_CAP and scope["package_wall_cap_s"] == WALL_CAP
          and scope["package_memory_cap_bytes"] == MEMORY_CAP and scope["package_workspace_cap_bytes"] == WORKSPACE_CAP,
          "Frozen packaging resource contract differs")
    check(set(reader.pins) == contracts.required_inputs(scope), "Exactly twenty-four original saved JSON pins required")
    pairs = [contracts.load_pair(reader, scope, pair_id, args.freeze_commit) for pair_id in contracts.PAIR_IDS]
    audit = contracts.source_audit(reader, scope, pairs, args.freeze_commit)
    check(set(reader.opened) == set(reader.pins), "All required original JSON inputs must be bound")
    summary, receipt, late_pins = check_summary(root, reader, scope, pairs, audit, args)
    admitted = {}
    def admit(name, pin):
        contracts.project_path(root, name)
        check(set(pin) == {"sha256", "bytes"} and re.fullmatch(r"[0-9a-f]{64}", pin["sha256"])
              and isinstance(pin["bytes"], int) and not isinstance(pin["bytes"], bool) and pin["bytes"] > 0,
              "Exact positive SHA/size declaration required: "+name)
        check(name not in admitted or admitted[name] == pin, "Conflicting original admission pin: "+name)
        admitted[name] = pin
    for mapping in (scope["pinned_dependency_files"], reader.opened, {contracts.PINS: reader.input_map_pin}, late_pins):
        for name, pin in mapping.items():
            admit(name, pin)
    for pair in pairs:
        for mapping in (pair["output_byte_pins"], pair["runtime_admission_receipts"], pair["QA_opened_json_pins"]):
            for name, pin in mapping.items():
                admit(name, pin)
    names = collect(root, scope, reader, pairs) | set(admitted)
    pins = snapshot(root, names)
    scientific = {name: pin for pair in pairs for name, pin in pair["output_byte_pins"].items()}
    check(len(scientific) == 63 and sum(name.endswith(".npz") for name in scientific) == 45,
          "Exactly eighteen maps/eighteen tile normalizations/twenty-seven patches required")
    check({name for name in pins if name.endswith(".npz")} == {name for name in scientific if name.endswith(".npz")},
          "Only forty-five admitted scientific NPZ members allowed")
    for name, pin in admitted.items():
        check(pins[name] == pin, "Archived bytes differ from admitted original SHA/size: "+name)
    reader.unchanged()
    estimated = sum(pin["bytes"] for pin in pins.values()) + 8*1024**2
    used = workspace_bytes(root)
    check(used + estimated <= WORKSPACE_CAP, "Workspace plus uncompressed archive estimate exceeds8GiB")
    check(shutil.disk_usage(root).free >= RESERVE + estimated and shutil.disk_usage(target.parent).free >= RESERVE+estimated,
          "Archive must leave512MiB reserve beyond conservative estimate")
    manifest = {"schema": "SETI_COMPLETE_JOINED_BOUNDARY_OPAQUE_ARCHIVE_V1",
                "status": "PINNED_THREE_ORIGINAL_COMPLETE_PAIRS_AND_SAVED_QA_AND_SOURCE_QA",
                "scope_sha256": reader.pins[contracts.SCOPE], "public_freeze_commit": args.freeze_commit,
                "summary_sha256": args.expected_summary_sha256, "summary_receipt_sha256": args.expected_summary_receipt_sha256,
                "reviewed_report_sha256": args.expected_report_sha256, "summary_input_pins_sha256": reader.sha,
                "editorial_receipt_sha256": args.expected_editorial_receipt_sha256,
                "original_pair_statuses": {pair["pair_id"]: pair["original_numeric_status"] for pair in pairs},
                "previous_native_terminal_statuses_rewritten": False, "saved_scientific_file_count": 63,
                "raw_source_HDF5_included": False, "scientific_arrays_interpreted_by_package": False,
                "members": pins, "self_hash_omitted": True, "archive_SHA256_in_external_receipt_only": True}
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False)+"\n").encode()
    (out/"ARCHIVE_MANIFEST.json").write_bytes(manifest_bytes)
    partial = target.with_suffix(".zip.pending")
    check(not partial.exists(), "Existing partial archive prevents retry")
    crcs = {}
    with partial.open("xb") as destination:
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as archive:
            for name, pin in pins.items():
                crcs[name] = add_file(archive, root, name, pin)
            archive.writestr(zip_info("ARCHIVE_MANIFEST.json"), manifest_bytes, compress_type=zipfile.ZIP_DEFLATED, compresslevel=1)
        destination.flush()
        os.fsync(destination.fileno())
    verify_archive(partial, pins, manifest_bytes)
    reader.unchanged()
    check(snapshot(root, names) == pins, "Evidence changed after ZIP verification")
    check(workspace_bytes(root) <= WORKSPACE_CAP and shutil.disk_usage(root).free >= RESERVE
          and shutil.disk_usage(target.parent).free >= RESERVE, "Measured workspace/reserve cap exceeded")
    archive_pin = contracts.file_pin(partial)
    measured = {"process_CPU_seconds_including_imports": time.process_time(), "wall_seconds_including_imports": time.monotonic()-WALL_STARTED,
                "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
    check(0 < measured["process_CPU_seconds_including_imports"] <= CPU_CAP
          and 0 < measured["wall_seconds_including_imports"] <= WALL_CAP and 0 < measured["peak_RSS_bytes"] <= MEMORY_CAP,
          "Measured opaque packaging resource caps exceeded")
    check(not target.exists(), "Archive destination appeared during packaging")
    partial.rename(target)
    check(contracts.file_pin(target) == archive_pin, "Published archive bytes differ")
    measured.update(process_CPU_seconds_including_imports=time.process_time(), wall_seconds_including_imports=time.monotonic()-WALL_STARTED)
    check(measured["process_CPU_seconds_including_imports"] <= CPU_CAP and measured["wall_seconds_including_imports"] <= WALL_CAP,
          "Measured publication resource caps exceeded")
    result = {"status": "COMPLETE_VERIFIED_OPAQUE_JOINED_BOUNDARY_ARCHIVE", "archive_filename": target.name,
              "archive_sha256": archive_pin["sha256"], "archive_bytes": archive_pin["bytes"],
              "script_sha256": contracts.file_pin(Path(__file__))["sha256"], "scope_sha256": reader.pins[contracts.SCOPE],
              "freeze_commit": args.freeze_commit, "input_pins_sha256": reader.sha, "opened_inputs": reader.opened,
              "member_count": len(pins)+1, "all_member_SHA256_sizes_and_CRC_verified": True,
              "member_crc32": crcs, "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
              "original_pair_statuses": manifest["original_pair_statuses"], "previous_native_terminal_statuses_rewritten": False,
              "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP, "memory_cap_bytes": MEMORY_CAP,
              "workspace_cap_bytes": WORKSPACE_CAP, "workspace_bytes_measured": workspace_bytes(root),
              "raw_HDF5_opened": False, "NPZ_arrays_interpreted": False, "detector_rerun": False,
              "rankings_reselected": False, "cost_DKK": 0, "new_HTTP_requests": 0, "new_BODY_bytes": 0, **measured}
    contracts.save(out/"PACKAGING_EXECUTION_RECEIPT.json", result)
    signal.alarm(0)
    print(json.dumps({"status": result["status"], "archive": target.name, "bytes": archive_pin["bytes"], **measured}, allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        if RUN_DIRECTORY is not None:
            contracts.save(RUN_DIRECTORY/"PACKAGING_FAILURE_RECEIPT.json", {"status": "INCOMPLETE_BOUNDARY_ARCHIVE_NO_RETRY",
                 "error_type": type(error).__name__, "error": str(error), "partial_archive_and_evidence_preserved": True,
                 "process_CPU_seconds_including_imports": time.process_time(), "wall_seconds_including_imports": time.monotonic()-WALL_STARTED})
        raise
