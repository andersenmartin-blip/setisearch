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
import shutil
import time
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[2]
TOOLS = "tools/radio_next_bands_20261010"
STAGE = "results/radio_next_bands_20261010"
SCOPE = TOOLS + "/scope.json"
GUIDE = TOOLS + "/RAW_CHECKPOINT_REPRODUCTION_CORRECTED.md"
REPORT = "RADIO_NEXT_BANDS_VERIFIED_SAVED_REPORT_2026-10-10.md"
SUMMARY = STAGE + "/acceptance/summary/VERIFIED_SAVED_SUMMARY.json"
MANIFEST = STAGE + "/acceptance/packaging/PACKAGE_MANIFEST.json"
ARCHIVE_NAME = "SETI_NEXT_BANDS_VERIFIED_SAVED_RESULTS_2026-10-10.zip"
SELECTION_SHA = "d47604f9539486692569e9ecd810775d86574b0547102708d9469c57b1da2fd7"
EXPECTED_SCOPE_SHA = "60ec39a777575ba25352e2eeb0b6db3ec21e3aed84fb92d534b82b5ded3f74b4"
FREEZE_COMMIT = "d1bfe755e205e99b3c93544f4af84cc8d4585938"
RECOVERY_COMMIT = "8f88b722c9508d4e209c3df540407029b80c3203"
SOURCE_AUDIT = STAGE + "/acceptance/review/SOURCE_CELL_QA_RECEIPT.json"
ACCEPTANCE_SCOPE = TOOLS + "/SAVED_OUTPUT_ACCEPTANCE_SCOPE.json"
SOURCE_AUDIT_STATUS = "PASS_36_FIXED_RAW_PATCHES_AUTHENTICATED_BITWISE_TO_SOURCE_WITH_ORIGINAL_TERMINAL_STATUS_PRESERVED"
INPUT_PINS = STAGE + "/acceptance/SUMMARY_INPUT_PINS.json"
SUMMARY_RECEIPT = STAGE + "/acceptance/summary/SUMMARY_EXECUTION_RECEIPT.json"
RAW_MANIFEST_SHA = {153:"79ada8a632117ee9de4db9f5614dfdbabe72b9b54a4b354ffa148569430db453",
                    154:"3f88c7b4baf4b822d7f3d8dbe1ef9d9327d8c5254fa9c3439ff5cd229d231b46"}
CHUNKS = (153,154)
WORKSPACE_CAP = 8*1024**3
PENDING_OUTPUT_RESERVE = 512*1024**2
CPU_CAP, WALL_CAP, MEMORY_CAP = 120, 1800, 4*1024**3
CHUNK = 1024**2
TEXT_SUFFIXES = {".json", ".md", ".py", ".txt", ".log", ".csv", ".sha256", ".svg"}
ALLOWED_SUFFIXES = TEXT_SUFFIXES | {".npz", ".png", ".jpg", ".jpeg", ".pdf", ".gz"}
EXCLUDED_COMPONENTS = {"__pycache__", ".git", ".cache", "cache", "wheels", "deps",
                       "private", "privatework", "library_helpers", "library_helpers_current", "packaging",
                       "archive_parts_10MiB", "archive"}
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


def collect_payload(root, scope, acceptance):
    names = set(scope["pinned_dependency_files"]) | set(acceptance["pinned_dependency_files"])
    names.add(ACCEPTANCE_SCOPE)
    names.update((SCOPE, REPORT, GUIDE, SUMMARY, SUMMARY_RECEIPT, INPUT_PINS, SOURCE_AUDIT,
                  TOOLS+"/RAW_CHECKPOINT_REPRODUCTION.md",
                  TOOLS+"/RAW_CHECKPOINT_REPRODUCTION_ERRATUM.json",
                  STAGE+"/figures/NEXT_BANDS_COVERAGE.png",
                  STAGE+"/figures/NEXT_BANDS_FIXED_PROFILE_MEANS.png"))
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
    for metadata in (scope,acceptance):
        for name, expected in metadata["pinned_dependency_files"].items():
            if digest(root/name) != expected:
                raise ValueError("Scope-pinned imported file differs: " + name)
    return sorted(names)


def required_summary_json_paths(acceptance):
    names={TOOLS+"/ACTIVATION_SCOPE.json",SCOPE,ACCEPTANCE_SCOPE,TOOLS+"/PATH_PREFLIGHT_RECOVERY_SCOPE.json",
           STAGE+"/PATH_PREFLIGHT_PRESERVATION_RECEIPT.json",STAGE+"/review/PATH_PREFLIGHT_PEER_REVIEW.json",SOURCE_AUDIT}
    jobs={(j["source_chunk_id"],j["batch_id"]):j for j in acceptance["job_contracts"]}
    if len(acceptance["job_contracts"])!=4 or set(jobs)!={(c,b) for c in CHUNKS for b in (1,2)}:
        raise ValueError("Acceptance must preserve four exact original numeric families")
    for chunk in CHUNKS:
        names.update((f"{STAGE}/chunk{chunk}/arrays/ACQUISITION_RESULT.json",
                      f"{STAGE}/chunk{chunk}/arrays/ACQUISITION_OUTPUT_QA_RECEIPT.json"))
        for batch in (1,2):
            job=jobs[(chunk,batch)]
            names.update(job["input_file_sha256"])
            names.add(job["original_terminal_receipt"]["path"])
            names.update(job["acceptance_directory"]+"/"+name for name in
                         ("SAVED_OUTPUT_ACCEPTANCE_RECEIPT.json","QA_RECEIPT.json"))
            failed=f"{STAGE}/preflight_failures/chunk{chunk}/batch_{batch:02d}/measurement/"
            names.update(failed+name for name in ("INPUT_PINS.json","FAILURE_RECEIPT.json"))
    if len(names)!=51:
        raise ValueError("Internal fifty-one accepted saved-input contract changed")
    return names


def verify_summary_provenance(root, scope, acceptance, summary, summary_pin, args):
    receipt,receipt_pin=load_json(root,SUMMARY_RECEIPT,args.expected_summary_execution_receipt_sha256)
    pins,pins_pin=load_json(root,INPUT_PINS,receipt["input_pins_sha256"])
    required=required_summary_json_paths(acceptance)
    if (set(pins)!=required or set(receipt["opened_inputs"])!=required
            or receipt["status"]!="PASS_PINNED_JSON_SUMMARIZATION_NOT_DETECTOR_OR_RAW_QA"
            or receipt["mode"]!="VERIFIED_SAVED_OUTPUTS_ONLY" or receipt["HDF5_or_NPZ_opened"] is not False
            or receipt["detector_rerun"] is not False or receipt["global_reranking"] is not False
            or receipt["classification_or_OFF_optimization"] is not False
            or receipt["output_hashes"].get(SUMMARY)!=summary_pin["sha256"]):
        raise ValueError("Package requires exact fifty-one input pins and verified-saved summary receipt")
    for name,expected in pins.items():
        relative_path(root,name)
        _,actual=load_json(root,name,expected)
        if receipt["opened_inputs"][name]!=actual:
            raise ValueError("Summary opened-input SHA or size no longer matches: "+name)
    for name,expected in receipt["output_hashes"].items():
        if name==REPORT:
            continue
        if digest(relative_path(root,name))!=expected:
            raise ValueError("Original summary output changed: "+name)
    if (summary["status"]!="VERIFIED_ALL_FOUR_SAVED_OUTPUT_FAMILIES_ORIGINAL_STATUSES_PRESERVED"
            or summary["summary_mode"]!="VERIFIED_SAVED_OUTPUTS_ONLY"
            or summary["all_four_numeric_executions_complete"] is not False
            or summary["all_four_saved_output_families_verified"] is not True
            or summary["original_numeric_COMPLETE_jobs"]!=1 or summary["original_numeric_resource_failure_jobs"]!=3
            or summary["original_execution_statuses_rewritten"] is not False
            or summary["saved_output_acceptance_scope_sha256"]!=args.expected_acceptance_scope_sha256
            or summary["public_saved_output_acceptance_freeze_commit"]!=args.acceptance_freeze_commit
            or summary["fully_audited_summary_complete"] is not True
            or summary["all_required_local_and_acquisition_QA_pass"] is not True
            or summary["metadata_selection_canonical_SHA256"]!=SELECTION_SHA
            or summary["common_execution_scope_sha256"]!=EXPECTED_SCOPE_SHA
            or summary["public_code_freeze_commit"]!=FREEZE_COMMIT
            or summary["profile_identity_fields"]!=["source_chunk_id","batch_id","track_id"]
            or summary["batch_rankings_separate_no_global_reranking"] is not True
            or summary["expected_scan_tiles"]!=1524 or summary["completed_scan_tiles"]!=1524
            or summary["expected_profile_count"]!=36 or summary["profile_count"]!=36
            or summary["ON_carrier_origin_entries"]!=6242304
            or summary["evaluated_hypothesis_combinations"]!=9525755904):
        raise ValueError("Final audited summary differs from exact four-batch contract")
    source=summary["joint_source_cell_QA"]
    audit,audit_pin=load_json(root,SOURCE_AUDIT,pins[SOURCE_AUDIT])
    counts={"compact_files":12,"decoded_rows":192,"patches":36,"scan_profiles":216,
            "time_rows":3456,"raw_cells_bitwise_checked":445824}
    if (source["status"]!=SOURCE_AUDIT_STATUS
            or audit["status"]!=source["status"] or source["receipt_sha256"]!=audit_pin["sha256"]
            or source["receipt_path"]!=SOURCE_AUDIT or source["counts"]!=counts or audit["counts"]!=counts
            or audit["public_scope_sha256"]!=EXPECTED_SCOPE_SHA
            or audit["public_wrapper_sha256"]!=scope["script_sha256"] or audit["freeze_commit"]!=args.acceptance_freeze_commit
            or audit["acceptance_scope_sha256"]!=args.expected_acceptance_scope_sha256
            or audit["original_scientific_freeze_commit"]!=FREEZE_COMMIT
            or audit["audit_script_sha256"]!=acceptance["pinned_dependency_files"][acceptance["source_audit_script_path"]]
            or audit["original_statuses_preserved"] is not True or audit["original_files_written"]!=0
            or audit["profile_identity_fields"]!=["source_chunk_id","batch_id","track_id"]):
        raise ValueError("Actual joint raw-source audit differs from the summarized pinned PASS receipt")
    preflight=summary["path_preflight_recovery"]
    if (preflight["public_recovery_freeze_commit"]!=RECOVERY_COMMIT
            or preflight["code_invocations_if_complete_per_job"]!=2
            or preflight["actual_source_array_loads_and_searches_if_complete_per_job"]!=1
            or preflight["numerical_retry_after_measurements_start"] is not False
            or preflight["numeric_code_or_selection_changed"] is not False or len(preflight["failures"])!=4):
        raise ValueError("Preserved preflight/code-invocation distinction changed")
    return pins,pins_pin,receipt_pin,receipt,audit


def verify_saved_inventory(root, scope, acceptance, summary, summary_pins, audit, acceptance_freeze):
    pins={}
    identities=set()
    batches={(b["source_chunk_id"],b["batch_id"]):b for b in summary["batches"]}
    summary_profiles={tuple(p["identity"]):p for p in summary["profiles"]}
    audit_checks={(c["source_chunk_id"],c["batch_id"],c["track_id"]):c for c in audit["patch_checks"]}
    if (len(summary["batches"])!=4 or len(batches)!=4 or len(summary["profiles"])!=36
            or len(summary_profiles)!=36 or len(audit["patch_checks"])!=36 or len(audit_checks)!=36):
        raise ValueError("Four batch/36 profile composite identities must be unique")
    jobs={(j["source_chunk_id"],j["batch_id"]):j for j in acceptance["job_contracts"]}
    expected_tiles=0
    for chunk in CHUNKS:
      for batch_id in (1,2):
        prefix=f"{STAGE}/chunk{chunk}/batch_{batch_id:02d}/measurement/"
        checkpoint,_=load_json(root,prefix+"DRIFT_CHECKPOINT.json",summary_pins[prefix+"DRIFT_CHECKPOINT.json"])
        qs=scope["immutable_metadata_selection"]["batch_q"][batch_id-1]
        expected_done={scan:qs for scan in ("epoch1_on","epoch2_on","epoch3_on")}
        if (checkpoint["source_chunk_id"]!=chunk or checkpoint["batch_id"]!=batch_id
                or checkpoint["fixed_batch_q"]!=qs or checkpoint["expected_scan_tiles"]!=381
                or checkpoint["complete"] is not True or checkpoint["completed_scan_tiles"]!=381
                or len(checkpoint["completed_receipts"])!=381 or checkpoint["completed_q_by_ON"]!=expected_done):
            raise ValueError("ALL_COMPLETE archive requires four fixed 381-tile checkpoints")
        completed=set()
        for entry in checkpoint["completed_receipts"]:
            identity=(entry["scan_id"],entry["reference_core_q"])
            if identity in completed or identity[0] not in expected_done or identity[1] not in qs:
                raise ValueError("Duplicate or unexpected ON/core identity")
            completed.add(identity)
            first=chunk*1048576+identity[1]*4096
            if (entry["searched_carriers"]!=4096 or entry["valid_hypotheses_per_carrier"]!=1526
                    or entry["reference_channel_interval_half_open"]!=[first,first+4096]):
                raise ValueError("Saved maximum-map reference-carrier contract changed")
            for key,sha_key,size_key in (("path","sha256","bytes"),
                                        ("normalization_path","normalization_sha256","normalization_bytes")):
                name=prefix+entry[key]
                if name in pins:
                    raise ValueError("Duplicate map/normalization inventory file")
                pins[name]={"sha256":entry[sha_key],"bytes":entry[size_key]}
        expected_tiles+=381
        batch=batches[(chunk,batch_id)]
        job=jobs[(chunk,batch_id)]
        kind="execution" if (chunk,batch_id)==(153,2) else "failure"
        original_status="COMPLETE_127_NEW_NATIVE_CORE_BATCH_EXPLORATORY_ONLY" if kind=="execution" else "INCOMPLETE_RESOURCE_LIMIT_NO_RETRY"
        expected_qa="PASS_COMPLETE_SAVED_NATIVE_BATCH_OUTPUTS" if kind=="execution" else "PASS_COMPLETE_SAVED_OUTPUTS_WITH_ORIGINAL_CPU_CAP_EXCEEDED"
        accepted_status="SAVED_OUTPUT_VERIFIED_ORIGINAL_COMPLETE" if kind=="execution" else "SAVED_OUTPUT_VERIFIED_ORIGINAL_RESOURCE_FAILURE"
        qa_path=job["acceptance_directory"]+"/QA_RECEIPT.json"
        accepted_path=job["acceptance_directory"]+"/SAVED_OUTPUT_ACCEPTANCE_RECEIPT.json"
        qa,qa_pin=load_json(root,qa_path,batch["QA_receipt_sha256"])
        accepted,accepted_pin=load_json(root,accepted_path,batch["saved_output_verification_receipt_sha256"])
        terminal=job["original_terminal_receipt"]
        terminal_public={k:terminal[k] for k in ("path","sha256","bytes")}
        expected_counts={"maps":381,"normalization_files":381,"carrier_maximum_records":1560576,
                         "top20_entries":60,"patches":9,"scan_profiles":54,"time_rows":864,
                         "retained_raw_patch_cells":111456,"binary_and_normalization_hashes":771}
        bindings={"INPUT_PINS_sha256":prefix+"INPUT_PINS.json","checkpoint_sha256":prefix+"DRIFT_CHECKPOINT.json",
                  "top20_sha256":prefix+"DRIFT_TOP20.json","profile_JSON_sha256":prefix+"FIXED_TOP3_PROFILES.json"}
        if (batch["saved_output_verified"] is not True or batch["execution_complete"] is not (kind=="execution")
                or batch["profile_count"]!=9 or batch["original_numeric_job_status"]!=original_status
                or batch["original_terminal_receipt"]!=terminal_public or batch["original_terminal_kind"]!=kind
                or batch["original_resource_caps_satisfied"] is not (kind=="execution")
                or batch["QA_status"]!=expected_qa or qa["status"]!=expected_qa
                or qa["source_chunk_id"]!=chunk or qa["batch_id"]!=batch_id
                or qa_pin["sha256"]!=summary_pins[qa_path] or qa["counts"]!=expected_counts or qa["fixed_batch_q"]!=qs
                or qa["public_scope_sha256"]!=EXPECTED_SCOPE_SHA or qa["public_wrapper_sha256"]!=scope["script_sha256"]
                or qa["freeze_commit"]!=acceptance_freeze or qa["original_scientific_freeze_commit"]!=FREEZE_COMMIT
                or qa["acceptance_scope_sha256"]!=summary_pins[ACCEPTANCE_SCOPE]
                or qa["qa_script_sha256"]!=acceptance["qa_script_sha256"]
                or qa["original_terminal_receipt_sha256"]!=terminal["sha256"]
                or qa["original_terminal_receipt_path"]!=terminal["path"] or qa["original_terminal_kind"]!=kind
                or qa["original_numeric_job_status"]!=original_status or qa["input_json_sha256"]!=job["input_file_sha256"]
                or qa["original_resource_metrics"]!=job["original_measured_resource_use"]
                or qa["original_CPU_cap_s"]!=1500 or qa["original_numeric_resource_compliant"] is not (kind=="execution")
                or any(qa[key]!=summary_pins[name] for key,name in bindings.items())):
            raise ValueError("Actual derivative PASS QA differs from original terminal, summary or pinned saved outputs")
        if (accepted["status"]!=accepted_status or accepted["source_chunk_id"]!=chunk or accepted["batch_id"]!=batch_id
                or accepted["freeze_commit"]!=acceptance_freeze or accepted["original_scientific_freeze_commit"]!=FREEZE_COMMIT
                or accepted["original_numeric_job_status"]!=original_status
                or accepted["original_terminal_receipt"]!=terminal_public
                or accepted["input_json_sha256"]!=job["input_file_sha256"] or accepted["counts"]!=expected_counts
                or accepted["QA_receipt"]!={"path":qa_path,**qa_pin,"status":expected_qa,"passed":True}
                or accepted["acceptance_scope_sha256"]!=summary_pins[ACCEPTANCE_SCOPE]
                or accepted["original_resource_metrics"]!=job["original_measured_resource_use"]
                or accepted["original_numeric_resource_compliant"] is not (kind=="execution")
                or accepted["saved_output_QA_resource_compliant"] is not True
                or accepted["saved_scoring_reexecuted"] is not False or accepted["profiles_remeasured"] is not False
                or accepted_pin["sha256"]!=summary_pins[accepted_path]):
            raise ValueError("Actual saved-output verification receipt differs from derivative QA or preserved identity")
        profiles,_=load_json(root,prefix+"FIXED_TOP3_PROFILES.json",summary_pins[prefix+"FIXED_TOP3_PROFILES.json"])
        if len(profiles)!=9:
            raise ValueError("Complete batch profile family has changed")
        for record in profiles:
            track=record["selected_track"]
            identity=(track["source_chunk_id"],track["batch_id"],track["track_id"])
            if identity[:2]!=(chunk,batch_id) or identity in identities:
                raise ValueError("Duplicate or foreign composite profile identity")
            identities.add(identity)
            if identity not in summary_profiles or identity not in audit_checks:
                raise ValueError("Profile missing from summary/source-audit identities")
            p=summary_profiles[identity];c=audit_checks[identity]
            if (p["patch_provenance"]!=record["patch"] or c["bitwise_identical"] is not True
                    or c["patch_sha256"]!=record["patch"]["sha256"] or c["raw_cells"]!=12384
                    or c["raw_cell_bytes_SHA256"]!=c["independent_source_cell_bytes_SHA256"]
                    or c["original_terminal_receipt_sha256"]!=terminal["sha256"]
                    or c["original_terminal_receipt_path"]!=terminal["path"] or c["original_terminal_kind"]!=kind
                    or c["original_numeric_job_status"]!=original_status
                    or c["source_profiles_JSON_sha256"]!=summary_pins[prefix+"FIXED_TOP3_PROFILES.json"]):
                raise ValueError("Fixed patch provenance differs from actual source-audit PASS")
            name=prefix+record["patch"]["path"]
            if name in pins:
                raise ValueError("Duplicate fixed patch inventory file")
            pins[name]={"sha256":record["patch"]["sha256"],"bytes":record["patch"]["bytes"]}
    if expected_tiles!=1524 or len(identities)!=36 or len(pins)!=1524*2+36:
        raise ValueError("Full map/normalization/36 patch inventory count differs")
    for name,expected in pins.items():
        path=relative_path(root,name)
        if not path.is_file() or path.stat().st_size!=expected["bytes"] or digest(path)!=expected["sha256"]:
            raise ValueError("Saved opaque map/normalization/patch SHA or size differs: "+name)
    return pins,expected_tiles,len(identities)


def external_raw_archives(root, summary):
    archives=[]
    for chunk in CHUNKS:
        name=f"{STAGE}/chunk{chunk}/raw_checkpoint/RAW_CHECKPOINT_ARCHIVE_MANIFEST.json"
        raw,pin=load_json(root,name,RAW_MANIFEST_SHA[chunk])
        archive=raw["archive"]
        if (raw["status"]!="PASS_COMPLETE_OPAQUE_BYTE_COPY_ZIP_SHA_SIZE_ALL_MEMBER_SHA_CRC_READBACK"
                or raw["source_chunk_id"]!=chunk or raw["public_scientific_freeze_commit"]!=FREEZE_COMMIT
                or raw["independent_acquisition_QA_sha256"]!=summary["acquisition_metadata"][str(chunk)]["acquisition_source_QA_receipt_sha256"]
                or archive["filename"]!=f"SETI_NATIVE{chunk}_RAW_2026-10-10.zip"
                or raw["HDF5_or_NPZ_decodes"]!=0 or raw["numerical_measurement_or_profile_runs"]!=0):
            raise ValueError("External RAW ZIP metadata differs from pinned completed input archive")
        archives.append({"source_chunk_id":chunk,**archive,"archive_manifest_path":name,"archive_manifest_sha256":pin["sha256"]})
    return archives


def workspace_bytes(directory):
    total=0
    for current,dirs,files in os.walk(directory,followlinks=False):
        dirs[:]=[name for name in dirs if not (Path(current)/name).is_symlink()]
        for name in files:
            path=Path(current)/name
            if not path.is_symlink():
                total+=path.stat().st_size
    return total

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
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",default=str(ROOT))
    parser.add_argument("--archive",required=True)
    parser.add_argument("--expected-scope-sha256",required=True)
    parser.add_argument("--expected-summary-sha256",required=True)
    parser.add_argument("--expected-acceptance-scope-sha256",required=True)
    parser.add_argument("--acceptance-freeze-commit",required=True)
    parser.add_argument("--expected-summary-execution-receipt-sha256",required=True)
    parser.add_argument("--expected-report-sha256",required=True)
    parser.add_argument("--root-authorized-package-read",action="store_true")
    args=parser.parse_args()
    if not args.root_authorized_package_read:
        raise SystemExit("Explicit root GO is required before any result/payload byte reads")
    started=time.monotonic()
    for key in ("OPENBLAS_NUM_THREADS","OMP_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):
        os.environ[key]="1"
    resource.setrlimit(resource.RLIMIT_CPU,(CPU_CAP,CPU_CAP+1))
    resource.setrlimit(resource.RLIMIT_AS,(MEMORY_CAP,MEMORY_CAP))
    def deadline(signum,frame):
        raise TimeoutError("Packaging CPU/wall cap exceeded")
    signal.signal(signal.SIGALRM,deadline);signal.signal(signal.SIGXCPU,deadline);signal.alarm(WALL_CAP)
    root=Path(args.root).resolve()
    archive_path=Path(args.archive).resolve()
    temporary=archive_path.with_suffix(".zip.tmp")
    output=root/(STAGE+"/acceptance/packaging")
    if args.expected_scope_sha256!=EXPECTED_SCOPE_SHA or archive_path.name!=ARCHIVE_NAME:
        raise ValueError("Use exact declared public scope and result archive name")
    if archive_path.exists() or temporary.exists() or output.exists():
        raise ValueError("Once-only package destination/evidence already exists")
    output.mkdir(parents=True,exist_ok=False)
    (output/"PACKAGE_STARTED.json").write_text(json.dumps({"status":"STARTED_ONCE_ONLY_VERIFIED_SAVED_OUTPUT_BYTE_PACKAGE",
        "script_sha256":digest(Path(__file__)),"CPU_cap_s":CPU_CAP,"wall_cap_s":WALL_CAP,
        "memory_cap_bytes":MEMORY_CAP,"root_GO_required":True},indent=2)+"\n")
    try:
        scope,scope_pin=load_json(root,SCOPE,EXPECTED_SCOPE_SHA)
        acceptance,acceptance_pin=load_json(root,ACCEPTANCE_SCOPE,args.expected_acceptance_scope_sha256)
        if (acceptance["original_scope_sha256"]!=EXPECTED_SCOPE_SHA or acceptance["original_wrapper_sha256"]!=scope["script_sha256"]
                or len(args.acceptance_freeze_commit)!=40 or any(c not in "0123456789abcdef" for c in args.acceptance_freeze_commit)):
            raise ValueError("Exact preserved numeric identity and public acceptance freeze are required")
        summary,summary_pin=load_json(root,SUMMARY,args.expected_summary_sha256)
        if digest(relative_path(root,REPORT))!=args.expected_report_sha256:
            raise ValueError("Final review-approved report pin differs")
        for required in (GUIDE,TOOLS+"/RAW_CHECKPOINT_REPRODUCTION.md",TOOLS+"/RAW_CHECKPOINT_REPRODUCTION_ERRATUM.json"):
            if not relative_path(root,required).is_file():
                raise ValueError("Corrected guide and preserved original/erratum required")
        report_text=(root/REPORT).read_text()
        if any(marker in report_text for marker in ("DRAFT_NOT_RUN","RAPPORTUDKAST","AFVENTER FÆRDIGE")):
            raise ValueError("Result report remains an unexecuted draft")
        summary_pins,pins_pin,summary_receipt_pin,summary_execution_receipt,audit=verify_summary_provenance(root,scope,acceptance,summary,summary_pin,args)
        inventory_pins,map_count,profile_count=verify_saved_inventory(root,scope,acceptance,summary,summary_pins,audit,args.acceptance_freeze_commit)
        raw_archives=external_raw_archives(root,summary)
        payloads=collect_payload(root,scope,acceptance)
        if (set(inventory_pins)-set(payloads) or set(summary_pins)-set(payloads)
                or SUMMARY not in payloads or SOURCE_AUDIT not in payloads):
            raise ValueError("Required opaque scientific result or pinned provenance omitted")
        snapshot_pins={name:{"bytes":(root/name).stat().st_size,"sha256":digest(root/name)} for name in payloads}
        # A fresh snapshot must preserve admitted identities, never replace them.
        admitted={}
        def admit(name,expected_sha,expected_bytes=None):
            value={"sha256":expected_sha}
            if expected_bytes is not None:
                value["bytes"]=expected_bytes
            if name in admitted:
                previous=admitted[name]
                if previous["sha256"]!=expected_sha or ("bytes" in previous and expected_bytes is not None and previous["bytes"]!=expected_bytes):
                    raise ValueError("Conflicting declared payload identity: "+name)
                previous.update(value)
            else:
                admitted[name]=value
        for name,pin in inventory_pins.items():
            admit(name,pin["sha256"],pin["bytes"])
        for name,expected in summary_pins.items():
            admit(name,expected,summary_execution_receipt["opened_inputs"][name]["bytes"])
        for name,expected in scope["pinned_dependency_files"].items():
            admit(name,expected,scope["pinned_dependency_file_bytes"][name])
        for name,expected in acceptance["pinned_dependency_files"].items():
            admit(name,expected)
        for job in acceptance["job_contracts"]:
            for name,expected in job["input_file_sha256"].items():
                admit(name,expected,job["input_file_bytes"][name])
        for name,pin in ((SCOPE,scope_pin),(ACCEPTANCE_SCOPE,acceptance_pin),(SUMMARY,summary_pin),(INPUT_PINS,pins_pin),(SUMMARY_RECEIPT,summary_receipt_pin)):
            admit(name,pin["sha256"],pin["bytes"])
        admit(REPORT,args.expected_report_sha256)
        for name,expected in summary_execution_receipt["output_hashes"].items():
            if name!=REPORT:
                admit(name,expected)
        admit(TOOLS+"/summarize_verified_saved.py",summary_execution_receipt["script_sha256"])
        admit(acceptance["source_audit_script_path"],audit["audit_script_sha256"])
        for chunk in CHUNKS:
            manifest_name=f"{STAGE}/chunk{chunk}/raw_checkpoint/RAW_CHECKPOINT_ARCHIVE_MANIFEST.json"
            raw,raw_pin=load_json(root,manifest_name,RAW_MANIFEST_SHA[chunk])
            admit(manifest_name,raw_pin["sha256"],raw_pin["bytes"])
            for batch_id in (1,2):
                qa_name=f"{STAGE}/acceptance/chunk{chunk}/batch_{batch_id:02d}/QA_RECEIPT.json"
                qa,_=load_json(root,qa_name,summary_pins[qa_name])
                admit(acceptance["qa_script_path"],qa["qa_script_sha256"])
            acq_qa_name=f"{STAGE}/chunk{chunk}/arrays/ACQUISITION_OUTPUT_QA_RECEIPT.json"
            acq_qa,_=load_json(root,acq_qa_name,summary_pins[acq_qa_name])
            admit(STAGE+"/review/qa_completed_acquisition.py",acq_qa["qa_script_sha256"])
        for name,pin in admitted.items():
            if name not in snapshot_pins or any(snapshot_pins[name][key]!=value for key,value in pin.items()):
                raise ValueError("Payload snapshot differs from audited/admitted SHA or size: "+name)
        estimate=sum(e["bytes"] for e in snapshot_pins.values())+8*1024**2
        before_workspace=workspace_bytes(root.parent)
        if before_workspace+estimate+PENDING_OUTPUT_RESERVE>WORKSPACE_CAP:
            raise ValueError("Conservative package/workspace reserve exceeds 8GiB")
        if shutil.disk_usage(root.parent).free<estimate+PENDING_OUTPUT_RESERVE:
            raise ValueError("Insufficient free storage for package/reserve")
        archive_path.parent.mkdir(parents=True,exist_ok=True)
        entries=[]
        with zipfile.ZipFile(temporary,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as archive:
            for name in payloads:
                entry=add_file(archive,root,name)
                if any(entry[k]!=snapshot_pins[name][k] for k in ("bytes","sha256")):
                    raise ValueError("Payload differs from pre-package snapshot: "+name)
                entries.append(entry)
            manifest={"schema":"SETI_TWO_NATIVE_CHUNKS_VERIFIED_SAVED_PUBLIC_RESULT_PACKAGE_V2",
                "archive_filename":ARCHIVE_NAME,"mode":"ALL_VERIFIED_SAVED_OUTPUT_FAMILIES_ONLY","payload_member_count":len(entries),
                "completed_scan_tiles":map_count,"completed_normalization_files":map_count,
                "completed_fixed_profiles":profile_count,"ON_carrier_origin_entries":6242304,
                "evaluated_hypothesis_combinations":9525755904,
                "reference_coverage_per_native_chunk":0.9921875,"reference_coverage_grid_only":True,
                "public_code_freeze_commit":FREEZE_COMMIT,"public_path_recovery_freeze_commit":RECOVERY_COMMIT,
                "common_execution_scope_sha256":scope_pin["sha256"],"summary_sha256":summary_pin["sha256"],
                "saved_output_acceptance_scope_sha256":acceptance_pin["sha256"],
                "public_saved_output_acceptance_freeze_commit":args.acceptance_freeze_commit,
                "original_numeric_COMPLETE_jobs":1,"original_numeric_resource_failure_jobs":3,
                "original_execution_statuses_rewritten":False,
                "original_job_statuses":[{"source_chunk_id":b["source_chunk_id"],"batch_id":b["batch_id"],
                    "original_numeric_job_status":b["original_numeric_job_status"],
                    "original_terminal_receipt":b["original_terminal_receipt"],
                    "saved_output_verification_status":b["saved_output_verification_status"]} for b in summary["batches"]],
                "summary_execution_receipt_sha256":summary_receipt_pin["sha256"],
                "summary_input_pins_sha256":pins_pin["sha256"],"saved_summary_input_count":len(summary_pins),
                "joint_source_audit_sha256":summary_pins[SOURCE_AUDIT],
                "metadata_selection_canonical_SHA256":SELECTION_SHA,"batch_rankings_remain_separate":True,
                "profile_identity_fields":["source_chunk_id","batch_id","track_id"],"members":entries,
                "manifest_excludes_its_own_hash_and_CRC":True,"ZIP_SHA256_recorded_only_in_external_receipt":True,
                "raw_HDF5_files_embedded":False,"runtime_wheels_embedded":False,
                "required_external_input_archives":raw_archives,"one_historical_visit":True,
                "code_invocations_per_original_job":2,"actual_numeric_searches_per_original_job":1,
                "new_telescope_HTTP_requests_during_packaging":0,"new_telescope_BODY_bytes_during_packaging":0,
                "original_full_source_file_MD5_verified":False,
                "NPZ_or_HDF5_numeric_values_decoded_during_packaging":False,
                "public_git_transport_bytepart_max_bytes":10485759,
                "user_delivery_is_one_original_ZIP":True}
            manifest_raw=(json.dumps(manifest,indent=2,ensure_ascii=False,allow_nan=False)+"\n").encode()
            archive.writestr(zip_info(MANIFEST),manifest_raw)
        members={entry["path"]:entry for entry in entries}
        members[MANIFEST]={"bytes":len(manifest_raw),"sha256":hashlib.sha256(manifest_raw).hexdigest(),
                           "member_CRC32_hex":f"{zlib.crc32(manifest_raw)&0xffffffff:08x}"}
        verified=verify_archive(temporary,members)
        for name,expected in snapshot_pins.items():
            if (root/name).stat().st_size!=expected["bytes"] or digest(root/name)!=expected["sha256"]:
                raise ValueError("Original payload changed before final ZIP verification: "+name)
        if digest(root/SCOPE)!=EXPECTED_SCOPE_SHA or digest(root/ACCEPTANCE_SCOPE)!=args.expected_acceptance_scope_sha256:
            raise ValueError("Public scope changed during packaging")
        zip_sha,zip_bytes=digest(temporary),temporary.stat().st_size
        temporary.replace(archive_path)
        (output/"PACKAGE_MANIFEST.json").write_bytes(manifest_raw)
        resources={"process_CPU_seconds_including_imports":time.process_time(),
                   "wall_seconds_including_imports":time.monotonic()-started,
                   "peak_RSS_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
        if resources["process_CPU_seconds_including_imports"]>CPU_CAP or resources["wall_seconds_including_imports"]>WALL_CAP or resources["peak_RSS_bytes"]>MEMORY_CAP:
            raise TimeoutError("Measured package resources exceed declared caps")
        receipt={"status":"PASS_ARCHIVE_SHA256_SIZE_AND_EVERY_MEMBER_CRC_AND_SHA256",
                 "archive_filename":ARCHIVE_NAME,"archive_bytes":zip_bytes,"archive_sha256":zip_sha,
                 "mode":"ALL_VERIFIED_SAVED_OUTPUT_FAMILIES_ONLY","verified_member_count_including_manifest":verified,
                 "payload_member_count":len(entries),"completed_scan_tiles":map_count,
                 "completed_normalization_files":map_count,"completed_fixed_profiles":profile_count,
                 "embedded_manifest_path":MANIFEST,"embedded_manifest_sha256":members[MANIFEST]["sha256"],
                 "script_sha256":digest(Path(__file__)),"CPU_cap_s":CPU_CAP,"wall_cap_s":WALL_CAP,
                 "memory_cap_bytes":MEMORY_CAP,"workspace_cap_bytes":WORKSPACE_CAP,
                 "workspace_bytes_before_archive":before_workspace,"pending_output_reserve_bytes":PENDING_OUTPUT_RESERVE,
                 "raw_HDF5_or_wheels_embedded":False,"private_transfer_helpers_or_native_IDs_embedded":False,
                 "NPZ_or_HDF5_numeric_values_decoded":False,"detector_rerun":False,**resources}
        (output/"PACKAGE_RECEIPT.json").write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n")
        signal.alarm(0);print(json.dumps(receipt,allow_nan=False))
    except BaseException as exc:
        failure={"status":"PACKAGE_FAILED_OR_PARTIAL_NO_RETRY","error_type":type(exc).__name__,"error":str(exc),
                 "retry_authorized":False,"partial_archive_retained":temporary.exists() or archive_path.exists(),
                 "NPZ_or_HDF5_numeric_values_decoded":False,"detector_rerun":False,
                 "process_CPU_seconds_including_imports":time.process_time(),"wall_seconds_including_imports":time.monotonic()-started,
                 "peak_RSS_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
        (output/"PACKAGE_FAILURE_RECEIPT.json").write_text(json.dumps(failure,indent=2,allow_nan=False)+"\n")
        raise

if __name__ == "__main__":
    main()
