#!/usr/bin/env python3
"""Summarize pinned saved JSON after root GO; never open HDF5 or NPZ values.

This reader preserves batch-local ranks and identities (source_chunk_id, batch_id, track_id).
It checks metadata consistency, does not rerun a detector or evaluate an OFF
veto, and does not replace independent raw-output QA. Importing reads no files.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import time

SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]
SHORT = dict(zip(SCANS, ("ON1", "OFF1", "ON2", "OFF2", "ON3", "OFF3")))
ADJACENT = {
    "epoch1_on": (None, "epoch1_off"),
    "epoch2_on": ("epoch1_off", "epoch2_off"),
    "epoch3_on": ("epoch2_off", "epoch3_off"),
}
ACTIVATION = "tools/radio_next_bands_20261010/ACTIVATION_SCOPE.json"
SCOPE = "tools/radio_next_bands_20261010/scope.json"
EXPECTED_SCOPE_SHA = "60ec39a777575ba25352e2eeb0b6db3ec21e3aed84fb92d534b82b5ded3f74b4"
CHUNKS = (153, 154)
RECOVERY_SCOPE = "tools/radio_next_bands_20261010/PATH_PREFLIGHT_RECOVERY_SCOPE.json"
RECOVERY_SCOPE_SHA = "a1a6856f6a27e6f20deaaa894de88a3138e25460686c78cdda949b3e566ee268"
RECOVERY_COMMIT = "8f88b722c9508d4e209c3df540407029b80c3203"
PRESERVATION = "results/radio_next_bands_20261010/PATH_PREFLIGHT_PRESERVATION_RECEIPT.json"
PREFLIGHT_PEER = "results/radio_next_bands_20261010/review/PATH_PREFLIGHT_PEER_REVIEW.json"
STAGE = "results/radio_next_bands_20261010"
COMPLETE_STATUS = "COMPLETE_127_NEW_NATIVE_CORE_BATCH_EXPLORATORY_ONLY"
SELECTION_SHA = "d47604f9539486692569e9ecd810775d86574b0547102708d9469c57b1da2fd7"
FROZEN_CODE_COMMIT = "d1bfe755e205e99b3c93544f4af84cc8d4585938"
ROOT = Path(__file__).resolve().parents[2]
CPU_CAP, WALL_CAP, MEMORY_CAP = 40, 1800, 4 * 1024**3
ACCEPTANCE_SCOPE = "tools/radio_next_bands_20261010/SAVED_OUTPUT_ACCEPTANCE_SCOPE.json"
ACCEPTANCE_STAGE = STAGE + "/acceptance"
ACCEPTANCE_STATUSES = {
    "failure": "SAVED_OUTPUT_VERIFIED_ORIGINAL_RESOURCE_FAILURE",
    "execution": "SAVED_OUTPUT_VERIFIED_ORIGINAL_COMPLETE",
}
QA_STATUSES = {
    "failure": "PASS_COMPLETE_SAVED_OUTPUTS_WITH_ORIGINAL_CPU_CAP_EXCEEDED",
    "execution": "PASS_COMPLETE_SAVED_NATIVE_BATCH_OUTPUTS",
}
SOURCE_AUDIT_STATUS = "PASS_36_FIXED_RAW_PATCHES_AUTHENTICATED_BITWISE_TO_SOURCE_WITH_ORIGINAL_TERMINAL_STATUS_PRESERVED"


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def dump_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    temporary.replace(path)


def integer(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Expected integer: " + label)
    return value


def finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Expected finite scalar: " + label)
    return value


class PinnedJSON:
    def __init__(self, root, pins_path):
        self.root = root.resolve()
        self.pins_path = pins_path.resolve()
        raw = self.pins_path.read_bytes()
        self.pins_sha = sha256(raw)
        self.pins = json.loads(raw)
        self.opened = {}
        if not isinstance(self.pins, dict) or not self.pins:
            raise ValueError("A nonempty root-relative JSON-path to SHA256 map is required")
        for name, expected in self.pins.items():
            relative = Path(name)
            resolved = (self.root / relative).resolve()
            if (relative.is_absolute() or ".." in relative.parts or relative.suffix != ".json"
                    or not resolved.is_relative_to(self.root) or not isinstance(expected, str)
                    or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected)):
                raise ValueError("Invalid pinned JSON path or SHA256: " + name)

    def present(self, name):
        return name in self.pins

    def load(self, name):
        if name not in self.pins:
            raise ValueError("Missing explicit JSON input pin: " + name)
        raw = (self.root / name).read_bytes()
        actual = sha256(raw)
        if actual != self.pins[name]:
            raise ValueError("Pinned JSON differs: " + name)
        self.opened[name] = {"sha256": actual, "bytes": len(raw)}
        return json.loads(raw)

    def unchanged(self):
        if sha256(self.pins_path.read_bytes()) != self.pins_sha:
            raise ValueError("Input pins changed during summarization")
        for name, entry in self.opened.items():
            if sha256((self.root / name).read_bytes()) != entry["sha256"]:
                raise ValueError("Pinned input changed during summarization: " + name)


def geometry(activation, scope):
    selection = scope["immutable_metadata_selection"]
    canonical = (json.dumps(selection, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if (sha256(canonical) != SELECTION_SHA
            or activation["immutable_metadata_selection"] != selection
            or activation["metadata_selection_canonical_SHA256"] != SELECTION_SHA
            or scope["metadata_selection_canonical_SHA256"] != SELECTION_SHA):
        raise ValueError("Immutable prospective four-batch selection changed")
    if (selection["native_chunk_indices"] != list(CHUNKS)
            or selection["physical_chunk_intervals_half_open"] != [[c*1048576,(c+1)*1048576] for c in CHUNKS]
            or selection["full_safe_q_ascending"] != list(range(1,255))
            or selection["batch_q"] != [list(range(1,128)),list(range(128,255))]
            or selection["core_channels"] != 4096 or selection["read_halo_channels"] != 4000
            or selection["scan_order"] != list(SCANS)
            or scope["source_chunk_ids"] != list(CHUNKS)
            or scope["source_chunk_channel_count"] != 1048576
            or scope["safe_q_interval_inclusive"] != [1,254]
            or scope["expected_scan_tiles_per_batch"] != 381
            or scope["valid_hypotheses_per_carrier"] != 1526
            or scope["widths_channels"] != [1,3]
            or scope["drift_grid"] != {"first_hz_s":-4,"last_hz_s":4,"count":763}
            or scope["expected_total_scan_tiles_if_all_four_complete"] != 1524
            or scope["expected_total_ON_carrier_origin_entries_if_all_four_complete"] != 6242304
            or scope["expected_total_hypothesis_entries_if_all_four_complete"] != 9525755904
            or scope["profile_identity_fields"] != ["source_chunk_id","batch_id","track_id"]):
        raise ValueError("Frozen native geometry or evaluated-combination count changed")
    for chunk in CHUNKS:
        context=scope["chunk_contracts"][str(chunk)]
        if context["source_channel_interval_half_open"] != [chunk*1048576,(chunk+1)*1048576]:
            raise ValueError("Native chunk interval changed")
    return selection

def checkpoint_summary(data, batch, qs, source_first, chunk):
    if (data["source_chunk_id"] != chunk or data["batch_id"] != batch or data["fixed_batch_q"] != qs
            or data["expected_scan_tiles"] != 381):
        raise ValueError("Checkpoint batch contract changed")
    entries = data["completed_receipts"]
    if data["completed_scan_tiles"] != len(entries):
        raise ValueError("Checkpoint count differs from completed receipts")
    completed = {scan: set() for scan in ONS}
    for entry in entries:
        scan, q = entry["scan_id"], integer(entry["reference_core_q"], "q")
        if scan not in ONS or q not in qs or q in completed[scan]:
            raise ValueError("Unexpected or duplicate completed scan/core")
        first = source_first + q * 4096
        if (entry["tile_index"] != qs.index(q)
                or entry["core_start_relative_channel"] != q * 4096
                or entry["reference_channel_interval_half_open"] != [first, first + 4096]
                or entry["searched_carriers"] != 4096
                or entry["valid_hypotheses_per_carrier"] != 1526):
            raise ValueError("Completed scan/core has an invalid carrier contract")
        completed[scan].add(q)
    all_tiles = all(completed[s] == set(qs) for s in ONS)
    if data["complete"] is not all_tiles:
        raise ValueError("Checkpoint completeness flag disagrees with actual entries")
    if data["completed_q_by_ON"] != {s: sorted(completed[s]) for s in ONS}:
        raise ValueError("Checkpoint ON-core summary differs")
    return {s: sorted(completed[s]) for s in ONS}, all_tiles


def top20_check(top20, batch, qs, source_first, chunk):
    if set(top20) != set(ONS):
        raise ValueError("Expected all three ON top20 lists")
    expected = []
    for scan in ONS:
        tracks = top20[scan]
        if len(tracks) != 20:
            raise ValueError("Incomplete saved top20 list")
        for rank, track in enumerate(tracks, 1):
            if (track["source_chunk_id"] != chunk or track["batch_id"] != batch or track["originating_scan"] != scan
                    or track["originating_role"] != "ON" or track["display_rank"] != rank
                    or track["reference_core_q"] not in qs or track["width_channels"] not in (1, 3)):
                raise ValueError("Saved batch-local rank geometry changed")
            channel = integer(track["source_reference_channel"], "source_reference_channel")
            q = integer(track["reference_core_q"], "reference_core_q")
            first = source_first + q * 4096
            if not first <= channel < first + 4096:
                raise ValueError("Selected reference channel lies outside its declared core")
            frequency = finite(track["reference_frequency_hz"], "frequency")
            expected_frequency = 1876464843.75 - 2.835503418452676 * channel
            if not math.isclose(frequency, expected_frequency, rel_tol=0, abs_tol=1e-6):
                raise ValueError("Selected scalar frequency differs from the frozen native grid")
            drift = finite(track["drift_hz_s"], "drift")
            finite(track["maximum_robust_box_track_score"], "score")
            if drift < -4 or drift > 4:
                raise ValueError("Saved drift lies outside frozen grid")
        expected.extend(tracks[:3])
    return expected


def profile_summaries(records, expected, batch, batch_complete, chunk):
    if len(records) > 9 or [r["selected_track"] for r in records] != expected[:len(records)]:
        raise ValueError("Profiles differ from fixed batch-local top3 ordering")
    summaries = []
    for record in records:
        track = record["selected_track"]
        if (record["fixed_frequency_shift_channels"] != 0
                or record["classification"] != "UNRESOLVED_EXPLORATORY_PROFILE_NO_SKY_INFERENCE"):
            raise ValueError("Fixed-profile classification or shift changed")
        scans = record["scan_profiles"]
        if [p["scan_id"] for p in scans] != list(SCANS):
            raise ValueError("Missing or reordered six-scan profile")
        measures = {}
        for scan in scans:
            for field in ("mean_center_minus_flank", "median_center_minus_flank",
                          "first_eight_mean_center_minus_flank", "last_eight_mean_center_minus_flank"):
                finite(scan[field], field)
            count = integer(scan["positive_rows"], "positive_rows")
            if count < 0 or count > 16:
                raise ValueError("Invalid positive-row count")
            for field in ("all_16_center_minus_flank_rows", "all_16_raw_width_mean_power",
                          "frozen_source_channel_centers"):
                if len(scan[field]) != 16:
                    raise ValueError("Incomplete sixteen-row profile field")
                for value in scan[field]:
                    finite(value, field)
            measures[scan["scan_id"]] = {k: v for k, v in scan.items() if k != "scan_id"}
        origin = track["originating_scan"]
        before, after = ADJACENT[origin]
        summaries.append({
            "identity": [chunk, batch, track["track_id"]],
            "source_chunk_id": chunk,
            "batch_id": batch,
            "track_id": track["track_id"],
            "originating_scan": origin,
            "display_rank_within_batch_and_ON": track["display_rank"],
            "source_reference_channel": track["source_reference_channel"],
            "reference_core_q": track["reference_core_q"],
            "reference_frequency_hz": track["reference_frequency_hz"],
            "reference_seconds_from_anchor": track["reference_seconds_from_anchor"],
            "drift_hz_s": track["drift_hz_s"],
            "width_channels": track["width_channels"],
            "saved_robust_score": track["maximum_robust_box_track_score"],
            "origin_ON": measures[origin],
            "adjacent_preceding_OFF_scan": before,
            "adjacent_preceding_OFF": measures[before] if before else None,
            "adjacent_following_OFF_scan": after,
            "adjacent_following_OFF": measures[after],
            "all_six_fixed_scan_measures": measures,
            "batch_execution_complete": batch_complete,
            "classification": "UNRESOLVED_EXPLORATORY_PROFILE_NO_SKY_INFERENCE",
            "patch_provenance": record["patch"],
        })
    return summaries


def acquisition_metadata(reader, scope, chunk):
    context=scope["chunk_contracts"][str(chunk)]
    path=context["acquisition_summary_path"]
    if not reader.present(path):
        return {"status":"NOT_PROVIDED"}
    data=reader.load(path)
    source0=chunk*1048576
    if (data["status"] != "COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY"
            or data["source_manifest_sha256"] != context["source_manifest_sha256"]
            or data["script_sha256"] != context["acquisition_script_sha256"]
            or data["scope_sha256"] != context["acquisition_scope_sha256"]
            or data["source_channel0"] != source0
            or data["physical_channel_interval_half_open"] != [source0,source0+1048576]):
        raise ValueError("Acquisition receipt differs from prospective chunk contract")
    decoded=data["decoded_files"]
    if (len(decoded)!=6 or {d["scan_id"] for d in decoded}!=set(SCANS)
            or any(d["shape"]!=[16,1,1048576] or d["source_channel0"]!=source0
                   or [r["time_row"] for r in d["decoded_rows"]]!=list(range(16)) for d in decoded)):
        raise ValueError("Acquisition compact/decoded-row metadata incomplete")
    qa_path=f"{STAGE}/chunk{chunk}/arrays/ACQUISITION_OUTPUT_QA_RECEIPT.json"
    qa_status="NOT_PROVIDED"
    qa_sha=None
    if reader.present(qa_path):
        qa=reader.load(qa_path)
        counts={"source_requests":96,"compact_files":6,"retained_compressed_chunks":96,
                "decoded_rows":96,"decoded_values_authenticated":100663296}
        if (qa["status"]!="PASS_COMPLETE_SOURCE_BYTES_AND_ALL96_DECODED_ROWS"
                or qa["source_chunk_id"]!=chunk or qa["freeze_commit"]!=FROZEN_CODE_COMMIT
                or qa["acquisition_scope_sha256"]!=context["acquisition_scope_sha256"]
                or qa["acquisition_script_sha256"]!=context["acquisition_script_sha256"]
                or qa["source_manifest_sha256"]!=context["source_manifest_sha256"]
                or qa["common_four_batch_scope_sha256"]!=reader.pins[SCOPE]
                or qa["acquisition_result_sha256"]!=reader.pins[path] or qa["counts"]!=counts):
            raise ValueError("Acquisition source QA differs from actual pinned native source receipt")
        checked={f["scan_id"]:f for f in qa["files"]}
        if len(qa["files"])!=6 or set(checked)!=set(SCANS):
            raise ValueError("Acquisition source QA scan inventory changed")
        for d in decoded:
            f=checked[d["scan_id"]]
            if (f["file_sha256"]!=d["file_sha256"] or f["bytes"]!=d["bytes"]
                    or f["retained_compressed_chunks_checked"]!=16 or f["decoded_rows_checked"]!=16):
                raise ValueError("Acquisition source QA compact/row bindings differ")
        qa_status,qa_sha=qa["status"],reader.pins[qa_path]
    return {"status":data["status"],"receipt_sha256":reader.pins[path],"decoded_files":decoded,
            "acquisition_source_QA_status":qa_status,"acquisition_source_QA_receipt_sha256":qa_sha,
            "whole_original_source_MD5_verified":False}


def preflight_metadata(reader, scope, acquisitions):
    recovery=reader.load(RECOVERY_SCOPE)
    preserved=reader.load(PRESERVATION)
    peer=reader.load(PREFLIGHT_PEER)
    if (reader.pins[RECOVERY_SCOPE]!=RECOVERY_SCOPE_SHA
            or recovery["scientific_scope_sha256"]!=reader.pins[SCOPE]
            or recovery["unchanged_script_sha256"]!=scope["script_sha256"]
            or recovery["original_acquisition_and_scientific_freeze_commit"]!=FROZEN_CODE_COMMIT
            or recovery["authorizes_one_corrected_CLI_invocation_per_listed_job"] is not True
            or recovery["code_invocations_if_complete_each"]!=2
            or recovery["source_array_loads_and_numerical_searches_if_complete_each"]!=1
            or recovery["numerical_retry_after_measurements_start"] is not False
            or recovery["partial_numeric_resume"] is not False
            or recovery["changed_numerical_code_selection_grid_width_or_normalization"] is not False
            or recovery["new_source_GETs"]!=0 or recovery["rerun_acquisition"] is not False
            or preserved["status"]!="PASS_ZERO_MEASUREMENT_FAILURES_PRESERVED_BYTE_IDENTICAL"
            or preserved["scope_sha256"]!=reader.pins[RECOVERY_SCOPE]
            or peer["status"]!="PASS_ZERO_NUMERIC_WORK_PRESERVED_AND_FIXED_ABSOLUTE_CLI"
            or peer["path_recovery_scope_sha256"]!=reader.pins[RECOVERY_SCOPE]
            or peer["scientific_scope_sha256"]!=reader.pins[SCOPE]
            or peer["script_sha256"]!=scope["script_sha256"]
            or peer["code_math_grid_width_selection_unchanged"] is not True):
        raise ValueError("Path-only preflight recovery provenance changed")
    records=recovery["failures"]
    identities={(r["source_chunk_id"],r["batch_id"]) for r in records}
    if len(records)!=4 or identities!={(c,b) for c in CHUNKS for b in (1,2)}:
        raise ValueError("Preflight recovery must preserve four exact chunk/batch failures")
    peer_records={(r["source_chunk_id"],r["batch_id"]):r for r in peer["preserved_failures"]}
    if len(peer_records)!=4:
        raise ValueError("Independent preflight review identities changed")
    failures=[]
    for entry in records:
        chunk,batch=entry["source_chunk_id"],entry["batch_id"]
        review=peer_records[(chunk,batch)]
        if (entry["previous_code_invocations"]!=1 or entry["previous_source_array_loads"]!=0
                or entry["previous_detector_searches"]!=0 or entry["previous_profile_measurements"]!=0
                or review["preserved_file_sha256"]!=entry["preserved_file_sha256"]
                or review["source_array_loads"]!=0 or review["completed_scan_tiles"]!=0
                or review["completed_profiles"]!=0 or review["normalization_file_present"] is not False):
            raise ValueError("Preflight failure is not documented before numerical work")
        directory=entry["preserved_directory"]
        for filename,expected in entry["preserved_file_sha256"].items():
            name=directory+"/"+filename
            if reader.pins.get(name)!=expected:
                raise ValueError("Preserved preflight bytes not explicitly pinned")
            data=reader.load(name)
            if data["source_chunk_id"]!=chunk or data["batch_id"]!=batch:
                raise ValueError("Preserved failure/input-pin identity changed")
            if filename=="FAILURE_RECEIPT.json":
                if (data["completed_scan_tiles"]!=0 or data["completed_profiles"]!=0
                        or data["error_type"]!="ValueError"
                        or data["fixed_batch_q"]!=scope["immutable_metadata_selection"]["batch_q"][batch-1]
                        or not math.isclose(data["process_CPU_seconds_including_imports"],entry["failed_process_CPU_s"],rel_tol=0,abs_tol=1e-9)):
                    raise ValueError("Preserved preflight failure contains unexpected numeric work")
            elif filename=="INPUT_PINS.json":
                context=scope["chunk_contracts"][str(chunk)]
                if (data["scope_sha256"]!=reader.pins[SCOPE] or data["script_sha256"]!=scope["script_sha256"]
                        or data["source_manifest_sha256"]!=context["source_manifest_sha256"]
                        or data["acquisition_summary_sha256"]!=acquisitions[str(chunk)]["receipt_sha256"]):
                    raise ValueError("Preserved preflight source pins changed")
            else:
                raise ValueError("Unexpected preserved preflight file")
        failures.append({"source_chunk_id":chunk,"batch_id":batch,"preserved_directory":directory,
                         "preserved_file_sha256":entry["preserved_file_sha256"],
                         "failed_process_CPU_seconds":entry["failed_process_CPU_s"],
                         "previous_code_invocations":1,"previous_source_array_loads":0,
                         "previous_detector_searches":0,"previous_profile_measurements":0})
    cpu=sum(r["failed_process_CPU_seconds"] for r in failures)
    if not math.isclose(cpu,recovery["failed_preflight_CPU_sum_s"],rel_tol=0,abs_tol=1e-9):
        raise ValueError("Preflight CPU sum differs")
    return {"status":"PASS_PRESERVED_ZERO_MEASUREMENT_PREFLIGHTS_AND_PATH_ONLY_RECOVERY",
            "recovery_scope_sha256":reader.pins[RECOVERY_SCOPE],"public_recovery_freeze_commit":RECOVERY_COMMIT,
            "preservation_receipt_sha256":reader.pins[PRESERVATION],"peer_review_sha256":reader.pins[PREFLIGHT_PEER],
            "failed_preflight_CPU_seconds":cpu,"failures":failures,
            "code_invocations_if_complete_per_job":2,"actual_source_array_loads_and_searches_if_complete_per_job":1,
            "numerical_retry_after_measurements_start":False,"numeric_code_or_selection_changed":False}


def acceptance_contract(reader, scope, expected_sha):
    data=reader.load(ACCEPTANCE_SCOPE)
    if (reader.pins[ACCEPTANCE_SCOPE]!=expected_sha
            or data["original_scope_sha256"]!=reader.pins[SCOPE]
            or data["original_wrapper_sha256"]!=scope["script_sha256"]):
        raise ValueError("Saved-output acceptance scope differs from original frozen numeric identity")
    jobs={(j["source_chunk_id"],j["batch_id"]):j for j in data["job_contracts"]}
    if len(data["job_contracts"])!=4 or set(jobs)!={(c,b) for c in CHUNKS for b in (1,2)}:
        raise ValueError("Acceptance must bind exactly four original chunk/batch families")
    for identity,job in jobs.items():
        chunk,batch=identity
        prefix=f"{STAGE}/chunk{chunk}/batch_{batch:02d}/measurement/"
        required={prefix+n for n in ("INPUT_PINS.json","DRIFT_CHECKPOINT.json","DRIFT_TOP20.json",
                                    "FIXED_TOP3_PROFILES.json","NORMALIZATION.json")}
        terminal=job["original_terminal_receipt"]
        required.add(terminal["path"])
        if set(job["input_file_sha256"])!=required or set(job["input_file_bytes"])!=required:
            raise ValueError("Acceptance must bind five saved input JSONs plus the original terminal per job")
        kind=terminal["kind"]
        expected_kind="execution" if identity==(153,2) else "failure"
        if (kind!=expected_kind or terminal["path"]!=prefix+("EXECUTION_RECEIPT.json" if kind=="execution" else "FAILURE_RECEIPT.json")
                or job["acceptance_directory"]!=f"{ACCEPTANCE_STAGE}/chunk{chunk}/batch_{batch:02d}"):
            raise ValueError("Acceptance original terminal kind or derivative directory changed")
        for name,expected in job["input_file_sha256"].items():
            if reader.pins.get(name)!=expected:
                raise ValueError("Acceptance original input must be explicitly pinned: "+name)
        if reader.pins.get(terminal["path"])!=terminal["sha256"]:
            raise ValueError("Original terminal receipt must be explicitly pinned")
    return data,jobs


def required_verified_json_paths(jobs, source_audit_path):
    names={ACTIVATION,SCOPE,ACCEPTANCE_SCOPE,RECOVERY_SCOPE,PRESERVATION,PREFLIGHT_PEER,source_audit_path}
    for chunk in CHUNKS:
        names.update((f"{STAGE}/chunk{chunk}/arrays/ACQUISITION_RESULT.json",
                      f"{STAGE}/chunk{chunk}/arrays/ACQUISITION_OUTPUT_QA_RECEIPT.json"))
        for batch in (1,2):
            job=jobs[(chunk,batch)]
            names.update(job["input_file_sha256"])
            names.add(job["original_terminal_receipt"]["path"])
            names.update(job["acceptance_directory"]+"/"+n for n in
                         ("QA_RECEIPT.json","SAVED_OUTPUT_ACCEPTANCE_RECEIPT.json"))
            failed=f"{STAGE}/preflight_failures/chunk{chunk}/batch_{batch:02d}/measurement/"
            names.update(failed+n for n in ("INPUT_PINS.json","FAILURE_RECEIPT.json"))
    if len(names)!=51:
        raise ValueError("Internal exact fifty-one pinned JSON contract changed")
    return names


def load_verified_batch(reader, scope, acceptance, job, chunk, batch, selection, acquisition, acceptance_freeze):
    prefix=f"{STAGE}/chunk{chunk}/batch_{batch:02d}/measurement/"
    qs=selection["batch_q"][batch-1]
    context=scope["chunk_contracts"][str(chunk)]
    terminal_pin=job["original_terminal_receipt"]
    terminal=reader.load(terminal_pin["path"])
    kind=terminal_pin["kind"]
    original_complete=kind=="execution"
    terminal_status=COMPLETE_STATUS if original_complete else "INCOMPLETE_RESOURCE_LIMIT_NO_RETRY"
    if (reader.opened[terminal_pin["path"]]["bytes"]!=terminal_pin["bytes"]
            or terminal["status"]!=terminal_status or terminal["source_chunk_id"]!=chunk
            or terminal["batch_id"]!=batch or terminal["fixed_batch_q"]!=qs):
        raise ValueError("Original terminal status/identity/bytes changed")
    resources={k:finite(terminal[k],k) for k in
               ("process_CPU_seconds_including_imports","wall_seconds_including_imports","peak_RSS_bytes")}
    if resources!=job["original_measured_resource_use"] or any(v<=0 for v in resources.values()):
        raise ValueError("Original measured resources differ from the frozen saved-output inventory")
    cpu_pass=resources["process_CPU_seconds_including_imports"]<=scope["CPU_cap_s_per_batch"]
    wall_pass=resources["wall_seconds_including_imports"]<=scope["wall_cap_s_per_batch"]
    memory_pass=resources["peak_RSS_bytes"]<=scope["memory_cap_bytes_per_batch"]
    if original_complete:
        if (not cpu_pass or not wall_pass or not memory_pass
                or terminal["scope_sha256"]!=reader.pins[SCOPE]
                or terminal["script_sha256"]!=scope["script_sha256"]
                or terminal["metadata_selection_canonical_SHA256"]!=SELECTION_SHA
                or terminal["source_manifest_sha256"]!=context["source_manifest_sha256"]
                or terminal["acquisition_summary_sha256"]!=acquisition["receipt_sha256"]
                or terminal["CPU_cap_s"]!=scope["CPU_cap_s_per_batch"]
                or terminal["wall_cap_s"]!=scope["wall_cap_s_per_batch"]
                or terminal["memory_cap_bytes"]!=scope["memory_cap_bytes_per_batch"]
                or terminal["search_summary"]["completed_scan_tiles"]!=381
                or terminal["fixed_profile_summary"]["profile_count"]!=9):
            raise ValueError("Original COMPLETE execution fails its immutable contract")
        expected_flags={"one_historical_visit":True,"source_chunk_values_received_after_prospective_freeze":True,
                        "blind_or_independent_validation":False,"OFF_veto_applied":False,"qualified_sky_pilot":False,
                        "old_A_B_failure_statuses_changed":False,"old_holdouts_reopened":False,
                        "calibrated_SNR_FAP_flux_EIRP_or_sensitivity":False,"whole_original_source_MD5_verified":False,
                        "numeric_retry_authorized":False,"completion_of_other_chunk_or_batch_inferred":False}
        if (any(terminal[k] is not v for k,v in expected_flags.items())
                or terminal["new_telescope_HTTP_requests_during_analysis"]!=0
                or terminal["new_telescope_BODY_bytes_during_analysis"]!=0):
            raise ValueError("Original COMPLETE scientific/source flags changed")
    else:
        if (cpu_pass or not wall_pass or not memory_pass or terminal["error_type"]!="ResourceLimitExceeded"
                or terminal["error"]!="Measured use exceeds frozen native-band batch caps"
                or terminal["retry_authorized"] is not False or terminal["partial_outputs_preserved"] is not True
                or terminal["completed_scan_tiles"]!=381 or terminal["completed_profiles"]!=9):
            raise ValueError("Only the frozen terminal CPU overrun with all saved outputs may be accepted")
    inputs={name:reader.load(name) for name in job["input_file_sha256"]}
    for name in inputs:
        if reader.opened[name]["bytes"]!=job["input_file_bytes"][name]:
            raise ValueError("Original saved JSON size differs from acceptance pin")
    pins=inputs[prefix+"INPUT_PINS.json"]
    if (pins["source_chunk_id"]!=chunk or pins["batch_id"]!=batch
            or pins["scope_sha256"]!=reader.pins[SCOPE] or pins["script_sha256"]!=scope["script_sha256"]
            or pins["source_manifest_sha256"]!=context["source_manifest_sha256"]
            or pins["acquisition_summary_sha256"]!=acquisition["receipt_sha256"]
            or pins["compact_files_and_96_decoded_row_pins"]!=acquisition["decoded_files"]):
        raise ValueError("Original input pins differ from authenticated acquisition")
    checkpoint=inputs[prefix+"DRIFT_CHECKPOINT.json"]
    done,all_tiles=checkpoint_summary(checkpoint,batch,qs,chunk*1048576,chunk)
    if not all_tiles or checkpoint["completed_scan_tiles"]!=381:
        raise ValueError("Verification requires complete saved carrier coverage; no completion is inferred")
    if not original_complete and (terminal["checkpoint_sha256"]!=reader.pins[prefix+"DRIFT_CHECKPOINT.json"]
            or terminal["profile_checkpoint_sha256"]!=reader.pins[prefix+"FIXED_TOP3_PROFILES.json"]
            or terminal["completed_q_by_ON"]!=done):
        raise ValueError("Original failed terminal receipt differs from its full saved checkpoint/profile bytes")
    expected=top20_check(inputs[prefix+"DRIFT_TOP20.json"],batch,qs,chunk*1048576,chunk)
    if original_complete and (terminal["saved_normalization_sha256"]!=reader.pins[prefix+"NORMALIZATION.json"]
            or terminal["fixed_profile_summary"]["source_top20_sha256"]!=reader.pins[prefix+"DRIFT_TOP20.json"]):
        raise ValueError("Original COMPLETE normalization/profile provenance changed")
    profiles=profile_summaries(inputs[prefix+"FIXED_TOP3_PROFILES.json"],expected,batch,original_complete,chunk)
    if len(profiles)!=9:
        raise ValueError("Exactly nine unchanged selected profiles are required")
    directory=job["acceptance_directory"]
    qa_path=directory+"/QA_RECEIPT.json"
    accepted_path=directory+"/SAVED_OUTPUT_ACCEPTANCE_RECEIPT.json"
    qa,accepted=reader.load(qa_path),reader.load(accepted_path)
    expected_counts={"maps":381,"normalization_files":381,"carrier_maximum_records":1560576,
                     "top20_entries":60,"patches":9,"scan_profiles":54,"time_rows":864,
                     "retained_raw_patch_cells":111456,"binary_and_normalization_hashes":771}
    bindings={"INPUT_PINS_sha256":prefix+"INPUT_PINS.json","checkpoint_sha256":prefix+"DRIFT_CHECKPOINT.json",
              "top20_sha256":prefix+"DRIFT_TOP20.json","profile_JSON_sha256":prefix+"FIXED_TOP3_PROFILES.json",
              "acquisition_summary_sha256":context["acquisition_summary_path"]}
    terminal_public={k:terminal_pin[k] for k in ("path","sha256","bytes")}
    qa_public={"path":qa_path,**reader.opened[qa_path],"status":QA_STATUSES[kind],"passed":True}
    if (qa["status"]!=QA_STATUSES[kind] or qa["source_chunk_id"]!=chunk or qa["batch_id"]!=batch
            or qa["fixed_batch_q"]!=qs or qa["counts"]!=expected_counts
            or qa["freeze_commit"]!=acceptance_freeze or qa["original_scientific_freeze_commit"]!=FROZEN_CODE_COMMIT
            or qa["public_scope_sha256"]!=reader.pins[SCOPE] or qa["public_wrapper_sha256"]!=scope["script_sha256"]
            or qa["acceptance_scope_sha256"]!=reader.pins[ACCEPTANCE_SCOPE]
            or qa["qa_script_sha256"]!=acceptance["qa_script_sha256"]
            or qa["original_terminal_receipt_sha256"]!=terminal_pin["sha256"]
            or qa["original_terminal_receipt_path"]!=terminal_pin["path"]
            or qa["original_terminal_kind"]!=kind or qa["original_numeric_job_status"]!=terminal_status
            or qa["original_resource_metrics"]!=resources or qa["original_CPU_cap_s"]!=1500
            or qa["original_numeric_resource_compliant"] is not original_complete
            or qa["input_json_sha256"]!=job["input_file_sha256"]
            or any(qa[key]!=reader.pins[path] for key,path in bindings.items())):
        raise ValueError("Derivative QA receipt differs from immutable original outputs/terminal status")
    if (accepted["status"]!=ACCEPTANCE_STATUSES[kind] or accepted["source_chunk_id"]!=chunk or accepted["batch_id"]!=batch
            or accepted["freeze_commit"]!=acceptance_freeze
            or accepted["original_scientific_freeze_commit"]!=FROZEN_CODE_COMMIT
            or accepted["original_numeric_job_status"]!=terminal_status
            or accepted["original_terminal_receipt"]!=terminal_public
            or accepted["input_json_sha256"]!=job["input_file_sha256"]
            or accepted["QA_receipt"]!=qa_public or accepted["counts"]!=expected_counts
            or accepted["acceptance_scope_sha256"]!=reader.pins[ACCEPTANCE_SCOPE]
            or accepted["original_resource_metrics"]!=resources
            or accepted["original_numeric_resource_compliant"] is not original_complete
            or accepted["saved_output_QA_resource_compliant"] is not True
            or accepted["saved_scoring_reexecuted"] is not False or accepted["profiles_remeasured"] is not False):
        raise ValueError("Saved-output verification receipt differs from actual pinned derivative QA")
    for p in profiles:
        p["batch_saved_output_verified"]=True
        p["original_numeric_job_status"]=terminal_status
    return {"source_chunk_id":chunk,"batch_id":batch,"fixed_batch_q":qs,"status":terminal_status,
            "original_numeric_job_status":terminal_status,"execution_complete":original_complete,
            "original_terminal_receipt":terminal_public,"original_terminal_kind":kind,
            "original_resource_caps_satisfied":cpu_pass and wall_pass and memory_pass,
            "original_CPU_cap_satisfied":cpu_pass,"original_wall_cap_satisfied":wall_pass,
            "original_memory_cap_satisfied":memory_pass,"execution_resources":resources,
            "saved_output_verified":True,"saved_output_verification_status":accepted["status"],
            "saved_output_verification_receipt_path":accepted_path,
            "saved_output_verification_receipt_sha256":reader.pins[accepted_path],
            "checkpoint_all_tiles_present":True,"completed_scan_tiles":381,"completed_q_by_ON":done,
            "profile_count":9,"profiles":profiles,"QA_status":qa["status"],"QA_receipt_path":qa_path,
            "QA_receipt_sha256":reader.pins[qa_path],"acquisition_summary_sha256":acquisition["receipt_sha256"],
            "source_manifest_sha256":context["source_manifest_sha256"]}

def number(value, digits=6):
    if value is None:
        return "—"
    return f"{value:.{digits}f}".replace(".", ",")


def joint_source_QA(reader, scope, profiles, path, pass_status, jobs, acceptance_freeze, acceptance):
    if path is None:
        if pass_status is not None:
            raise ValueError("No invented source-cell PASS status without a pinned audit receipt")
        return {"status":"NOT_PROVIDED","raw_source_comparison_inferred_from_local_QA":False}
    if not pass_status or not pass_status.startswith("PASS_"):
        raise ValueError("Root must specify the exact independently authorized audit PASS status")
    if path!=ACCEPTANCE_STAGE+"/review/SOURCE_CELL_QA_RECEIPT.json":
        raise ValueError("Only the fixed isolated acceptance source-audit receipt is admitted")
    qa=reader.load(path)
    expected_counts={"compact_files":12,"decoded_rows":192,"patches":36,
                     "scan_profiles":216,"time_rows":3456,"raw_cells_bitwise_checked":445824}
    if (qa["status"]!=pass_status or qa["public_scope_sha256"]!=reader.pins[SCOPE]
            or qa["public_wrapper_sha256"]!=scope["script_sha256"]
            or qa["freeze_commit"]!=acceptance_freeze or qa["acceptance_scope_sha256"]!=reader.pins[ACCEPTANCE_SCOPE]
            or qa["original_scientific_freeze_commit"]!=FROZEN_CODE_COMMIT
            or qa["audit_script_sha256"]!=acceptance["pinned_dependency_files"][acceptance["source_audit_script_path"]]
            or qa["original_statuses_preserved"] is not True or qa["original_files_written"]!=0
            or qa["profile_identity_fields"]!=["source_chunk_id","batch_id","track_id"]
            or pass_status!=SOURCE_AUDIT_STATUS or qa["counts"]!=expected_counts or len(profiles)!=36):
        raise ValueError("Joint source-cell audit differs from complete four-batch profile family")
    checks={(c["source_chunk_id"],c["batch_id"],c["track_id"]):c for c in qa["patch_checks"]}
    if len(checks)!=36 or set(checks)!={tuple(p["identity"]) for p in profiles}:
        raise ValueError("Joint audit composite identities differ")
    for p in profiles:
        c=checks[tuple(p["identity"])]
        prefix=f'{STAGE}/chunk{p["source_chunk_id"]}/batch_{p["batch_id"]:02d}/measurement/'
        terminal=jobs[(p["source_chunk_id"],p["batch_id"])]["original_terminal_receipt"]
        original_status=COMPLETE_STATUS if terminal["kind"]=="execution" else "INCOMPLETE_RESOURCE_LIMIT_NO_RETRY"
        if (c["bitwise_identical"] is not True or c["raw_cells"]!=12384
                or c["patch_sha256"]!=p["patch_provenance"]["sha256"]
                or c["raw_cell_bytes_SHA256"]!=c["independent_source_cell_bytes_SHA256"]
                or c["original_terminal_receipt_sha256"]!=terminal["sha256"]
                or c["original_terminal_receipt_path"]!=terminal["path"] or c["original_terminal_kind"]!=terminal["kind"]
                or c["original_numeric_job_status"]!=original_status
                or c["source_profiles_JSON_sha256"]!=reader.pins[prefix+"FIXED_TOP3_PROFILES.json"]):
            raise ValueError("Joint audit patch/source provenance differs")
    return {"status":qa["status"],"receipt_path":path,"receipt_sha256":reader.pins[path],
            "counts":qa["counts"],"audit_script_sha256":qa["audit_script_sha256"],
            "original_full_source_file_MD5_verified":False}

def render_report(summary):
    lead="Alle fire oprindelige familier af gemte søgeoutputs er verificeret ved særskilt kontrol. Én numerisk kørsel sluttede COMPLETE; tre sluttede med en CPU-grænsefejl efter lagring af alle felter og profiler. Deres oprindelige fejlstatus og overskridelser er bevaret."

    lines=["# SETI: fast driftsøgning i native udsnit 153 og 154","",
           "**10. oktober 2026.** "+lead,
           f'Der er gemt **{summary["completed_scan_tiles"]} af 1.524 ON-scanningsfelter** og **{summary["profile_count"]} af 36 faste top-3-profiler**. Ranglisterne er separate for hvert udsnit, hver gruppe og hver ON-scanning; profilidentiteten er (native udsnit, gruppe, track-ID).',"",
           "Alle seks scanninger stammer fra ét besøg den 17. marts 2016. Udsnit og fire referencekanallister blev fastlagt før modtagelsen af de nye kildeværdier. Dette er eksplorativ analyse, ikke uafhængig eller blind validering. A/B er fortsat FAIL_CLOSED, den kvalificerede himmelpilot er blokeret, og gamle holdouts er lukkede.","",
           f'De fire første kodeinvokationer stoppede før indlæsning af signalarrays på grund af en relativ filsti. Fejlfilerne og deres {number(summary["path_preflight_recovery"]["failed_preflight_CPU_seconds"],6)} CPU-sekunder er bevaret. En særskilt offentlig fastlåsning ved `{RECOVERY_COMMIT}` tillod korrigerede absolutte CLI-stier med uændret kode, grid og kanalvalg. Hver gruppe har derfor to kodeinvokationer, men én faktisk arrayindlæsning, søgning og profilfamilie; der er ingen numerisk genkørsel.',"",
           "## Dækning og kontrol","",
           "| Native udsnit | Gruppe | Gemte felter / 381 | Profiler / 9 | Oprindelig kørselsstatus | Senere outputverifikation |",
           "| --- | --- | ---: | ---: | --- | --- |"]
    for b in summary["batches"]:
        lines.append(f'| {b["source_chunk_id"]} | {b["batch_id"]} | {b["completed_scan_tiles"]} | {b["profile_count"]} | {b["original_numeric_job_status"]} | {b["saved_output_verification_status"]} |')
    lines += ["","| Native udsnit | ON | Gemte referencekanaler | Andel af dette udsnit |","| --- | --- | ---: | ---: |"]
    for chunk in CHUNKS:
        for scan in ONS:
            c=summary["coverage"]["by_chunk"][str(chunk)]["by_ON"][scan]
            lines.append(f'| {chunk} | {SHORT[scan]} | {c["completed_reference_channels"]:,}'.replace(",",".")+f' | {number(100*c["completed_fraction"],5)} % |')
    lines += ["",(f'**{summary["ON_carrier_origin_entries"]:,} ON-referencekanal/originkombinationer** er evalueret med **1.526 gyldige grid-/breddehypoteser hver**, i alt **{summary["evaluated_hypothesis_combinations"]:,} hypotesekombinationer**. For hver referencekanal gemmes scoremaksimum, vindende drift og bredde samt det verificerede hypoteseantal.').replace(",","."),
              "De fire verificerede checkpointfamilier dækker 254 af 256 referencefelter, **99,21875 % i hvert udsnit**, alene for 763 lineære drifthastigheder fra −4 til +4 Hz/s og bredde 1 og 3. Randfelterne [0,4096) og [1044480,1048576) er usøgte i hvert udsnit. Haloer overlapper; tællingerne er beregningsdækning og ikke uafhængige statistiske forsøg."]
    qa=summary["joint_source_cell_QA"]
    if qa["status"].startswith("PASS"):
        lines += ["", "En særskilt, hashbundet kildecellekontrol matcher **445.824 råcelleforekomster i 36 profiludklip bit for bit** mod de 12 kompakte kildefiler. Den omfatter 192 afkodede kilderækker, 216 scanningsprofiler og 3.456 profilrækkeforekomster. De oprindelige større HDF5-kilders fulde MD5 er fortsat ikke verificeret."]
    else:
        lines += ["", "En særskilt sammenligning af profiludklippenes råceller med kildekompakterne er ikke dokumenteret i denne sammenfatning. QA af gemte outputs er ikke i sig selv en råkildecellesammenligning. De oprindelige større HDF5-kilders fulde MD5 er fortsat ikke verificeret."]
    lines += ["", "## De gemte faste profiler","",
              "Profilerne er udvalgt efter detektorens ON-rangscore inden for deres egne grupper. De er gentagne, muligvis nærliggende og afhængige beskrivelser; antallet af udvalgte spor er ikke antallet af uafhængige fysiske signaler. Frekvensintervallerne nedenfor er kun de udvalgte referencefrekvensers min/max, ikke en målt strukturafgrænsning.","",
              "| Native udsnit | Gruppe | Udvalgte spor | Native q | Referencefrekvensinterval, MHz |","| --- | --- | ---: | --- | ---: |"]
    for b in summary["batches"]:
        p=b["profiles"]
        if p:
            f=[x["reference_frequency_hz"]/1e6 for x in p]
            cores=", ".join(map(str,sorted({x["reference_core_q"] for x in p})))
            lines.append(f'| {b["source_chunk_id"]} | {b["batch_id"]} | {len(p)} | {cores} | {number(min(f))}–{number(max(f))} |')
    lines += ["", "Tallene er gemt normaliseret centereffekt minus rækkens median af bevægelige flankkanaler med absolut offset større end tre inden for ±64. De er ikke kalibreret SNR. Detektorens robuste rangscore og profilens middelresidual er forskellige størrelser. OFF-værdierne følger den valgte, uændrede drift ved de faktiske scanningstider. ON2/ON3 har både forudgående og efterfølgende OFF; ON1 har kun efterfølgende OFF i denne sekvens. Alle seks scanningers faste forløb bevares i sammenfatningen.","",
              "| Native udsnit | Gruppe | ON/rang | Frekvens, MHz | Drift, Hz/s | Bredde | ON-middel | OFF før | OFF efter |",
              "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for p in summary["profiles"]:
        before=p["adjacent_preceding_OFF"]
        lines.append(f'| {p["source_chunk_id"]} | {p["batch_id"]} | {SHORT[p["originating_scan"]]}/{p["display_rank_within_batch_and_ON"]} | {number(p["reference_frequency_hz"]/1e6)} | {number(p["drift_hz_s"])} | {p["width_channels"]} | {number(p["origin_ON"]["mean_center_minus_flank"])} | {number(before["mean_center_minus_flank"] if before else None)} | {number(p["adjacent_following_OFF"]["mean_center_minus_flank"])} |')
    if not summary["profiles"]:
        lines.append("| — | — | Ingen pinnede profiler | — | — | — | — | — | — |")
    lines += ["", "Profilerne forbliver uafklarede. Positive rækker og halvdele er målt efter udvælgelse. En lille middelresidual på et præcist OFF-spor fastslår ikke fravær af nærliggende OFF-struktur. Ingen OFF-forskydning er optimeret; ingen kvalificeret OFF-veto, oprindelsesbestemmelse eller SETI-kandidat er fastslået.","",
              "## Målt kørsel","","| Native udsnit | Gruppe | CPU, sekunder | Vægtid, sekunder | Maksimal RSS, bytes |","| --- | --- | ---: | ---: | ---: |"]
    for b in summary["batches"]:
        r=b.get("execution_resources",b.get("failure_receipt",{}))
        lines.append(f'| {b["source_chunk_id"]} | {b["batch_id"]} | {number(r.get("process_CPU_seconds_including_imports"),3)} | {number(r.get("wall_seconds_including_imports"),3)} | {r.get("peak_RSS_bytes","—")} |')
    lines += ["",f'Den oprindelige numeriske grænse var {summary["numeric_CPU_cap_s_per_batch"]} CPU-sekunder, 1.800 sekunders vægtid og 4 GiB RAM. Tre oprindelige kørsler overskred CPU-grænsen ved afslutningskontrollen; grænsen eller fejlkvitteringerne er ikke ændret. En senere fastlåst kontrol af gemte outputs genkører ingen søgning, score, rangliste eller profil og omklassificerer ikke de numeriske kørsler til COMPLETE. Fasens {summary["stage_CPU_planning_allocation_s"]} CPU-sekunder er arbejdsplanlægning, ikke en abonnementsbalance eller global stopgrænse. Analyserne bruger 0 nye teleskoprequests/bytes; datamodtagelsens særskilte byte- og ressourcekvitteringer skal læses separat. Projektet fortsætter uden betalte ressourcer.',"",
              "## Begrænsninger og reproduktion","",
              f'Den særskilte gemte-outputkontrol blev fastlåst ved `{summary["public_saved_output_acceptance_freeze_commit"]}` med scope-SHA256 `{summary["saved_output_acceptance_scope_sha256"]}`. Verificeret betyder her, at de gemte outputs består de fastlagte integritets- og kildekontroller; det er ikke en kvalificeret SETI-kandidat eller en godkendelse af de oprindelige ressourcegrænser.',
              "Der er ikke beregnet kalibreret SNR, falskalarmrate, flux, EIRP eller følsomhed. Der påstås intet generelt nulresultat eller uafhængighed mellem hypoteser, profiler, udsnit eller scanninger. Ingen barycentrisk korrektion, ikke-lineære spor, andre bredder eller injektionskalibrering er tilføjet. De beskyttede gamle native udsnit 156 og 159 er lukkede.",
              f'Fælles scope og kode blev fastlåst offentligt ved `{summary["public_code_freeze_commit"]}` før de nye kildeværdier. Scope-SHA256: `{summary["common_execution_scope_sha256"]}`. Den prospektive fastlåsning gør ikke denne ene historiske sekvens til en uafhængig besøgsobservation. Kildekompakters lokale hashes og afkodede rækkehashes erstatter ikke originalfilernes fulde MD5.',
              "Sammenfatningen åbner kun eksplicit hashpinnede JSON-filer efter særskilt GO. Den genkører ikke detektoren og åbner hverken HDF5 eller NPZ. Inputhashes, outputhashes og ressourceforbrug findes i sammenfatningskvitteringen.","",
              "[Dækningsfigur](results/radio_next_bands_20261010/figures/NEXT_BANDS_COVERAGE.png) · [Faste profilmidler](results/radio_next_bands_20261010/figures/NEXT_BANDS_FIXED_PROFILE_MEANS.png)",""]
    return "\n".join(lines)

def write_csv(path, profiles):
    columns = ["source_chunk_id", "batch_id", "track_id", "originating_scan", "display_rank", "source_reference_channel",
               "reference_frequency_hz", "reference_seconds_from_anchor", "drift_hz_s", "width_channels",
               "saved_robust_score", *[s+"_mean_center_minus_flank" for s in SCANS],
               "origin_positive_rows", "origin_first_eight_mean", "origin_last_eight_mean",
               "batch_execution_complete", "batch_saved_output_verified", "original_numeric_job_status", "classification"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for p in profiles:
            row = {key: p[key] for key in columns if key in p}
            row.update(display_rank=p["display_rank_within_batch_and_ON"],
                       origin_positive_rows=p["origin_ON"]["positive_rows"],
                       origin_first_eight_mean=p["origin_ON"]["first_eight_mean_center_minus_flank"],
                       origin_last_eight_mean=p["origin_ON"]["last_eight_mean_center_minus_flank"])
            row.update({s+"_mean_center_minus_flank": p["all_six_fixed_scan_measures"][s]["mean_center_minus_flank"] for s in SCANS})
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--pins", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--report-path", default=str(ROOT/"RADIO_NEXT_BANDS_VERIFIED_SAVED_REPORT_2026-10-10.md"))
    parser.add_argument("--expected-acceptance-scope-sha256", required=True)
    parser.add_argument("--acceptance-freeze-commit", required=True)
    parser.add_argument("--joint-source-cell-receipt", required=True)
    parser.add_argument("--joint-source-cell-pass-status", default=SOURCE_AUDIT_STATUS)
    parser.add_argument("--root-authorized-summary-read", action="store_true")
    args = parser.parse_args()
    if not args.root_authorized_summary_read:
        raise SystemExit("Explicit root GO is required before opening any new numerical output")
    started = time.monotonic()
    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP+1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    def timeout(signum, frame):
        raise TimeoutError("Saved summary CPU/wall deadline exceeded")
    signal.signal(signal.SIGALRM, timeout)
    signal.signal(signal.SIGXCPU, timeout)
    signal.alarm(WALL_CAP)
    root = Path(args.root).resolve()
    out, report = Path(args.output_dir).resolve(), Path(args.report_path).resolve()
    if not out.is_relative_to(root) or not report.is_relative_to(root):
        raise ValueError("Summary artifacts must remain inside this project")
    reader = PinnedJSON(root, Path(args.pins))
    activation, scope = reader.load(ACTIVATION), reader.load(SCOPE)
    if reader.pins[SCOPE]!=EXPECTED_SCOPE_SHA:
        raise ValueError("Use exactly the public frozen four-batch scope")
    selection=geometry(activation,scope)
    acquisitions={str(chunk):acquisition_metadata(reader,scope,chunk) for chunk in CHUNKS}
    preflight=preflight_metadata(reader,scope,acquisitions)
    acceptance,jobs=acceptance_contract(reader,scope,args.expected_acceptance_scope_sha256)
    required_inputs=required_verified_json_paths(jobs,args.joint_source_cell_receipt)
    if set(reader.pins)!=required_inputs:
        raise ValueError("Verified-saved summary requires exactly all fifty-one explicit JSON pins")
    if len(args.acceptance_freeze_commit)!=40 or any(c not in "0123456789abcdef" for c in args.acceptance_freeze_commit):
        raise ValueError("Exact public acceptance freeze commit is required")
    batches=[load_verified_batch(reader,scope,acceptance,jobs[(chunk,batch)],chunk,batch,selection,
                                 acquisitions[str(chunk)],args.acceptance_freeze_commit)
             for chunk in CHUNKS for batch in (1,2)]
    complete=all(b["execution_complete"] for b in batches)
    verified=all(b["saved_output_verified"] for b in batches)
    original_complete_count=sum(b["execution_complete"] for b in batches)
    all_required_QA_pass=(verified and all(a.get("acquisition_source_QA_status")=="PASS_COMPLETE_SOURCE_BYTES_AND_ALL96_DECODED_ROWS"
                                        for a in acquisitions.values()))
    audited_complete=verified and all_required_QA_pass
    if not audited_complete or original_complete_count!=1:
        raise ValueError("Saved-output summary requires all four derivative admissions and the unchanged three FAILED/one COMPLETE contract")
    profiles=[p for b in batches for p in b["profiles"]]
    identities=[tuple(p["identity"]) for p in profiles]
    if len(set(identities))!=36 or len(profiles)!=36:
        raise ValueError("All 36 composite identities must be unique")
    source_cell_QA=joint_source_QA(reader,scope,profiles,args.joint_source_cell_receipt,args.joint_source_cell_pass_status,
                                 jobs,args.acceptance_freeze_commit,acceptance)
    if source_cell_QA["status"]!=SOURCE_AUDIT_STATUS:
        raise ValueError("Complete verified-saved summary requires the pinned supplemental raw-source audit")
    if set(reader.opened)!=required_inputs:
        raise ValueError("All required verification metadata must have been opened and bound")
    by_chunk={}
    for chunk in CHUNKS:
        group=[b for b in batches if b["source_chunk_id"]==chunk]
        by_on={}
        for scan in ONS:
            done=set().union(*(set(b["completed_q_by_ON"][scan]) for b in group))
            by_on[scan]={"completed_q":sorted(done),"completed_core_count":len(done),
                         "completed_reference_channels":len(done)*4096,"completed_fraction":len(done)/256}
        by_chunk[str(chunk)]={"by_ON":by_on,"both_original_chunk_executions_complete":all(b["execution_complete"] for b in group),
                              "both_chunk_saved_output_families_verified":all(b["saved_output_verified"] for b in group),
                              "native_chunk_interval_half_open":[chunk*1048576,(chunk+1)*1048576],
                              "previous_core_count":0,"native_chunk_core_count":256}
    tiles=sum(b["completed_scan_tiles"] for b in batches)
    entries=tiles*4096
    summary={"schema":"SETI_PINNED_TWO_NATIVE_CHUNKS_VERIFIED_SAVED_SUMMARY_V2",
             "status":"VERIFIED_ALL_FOUR_SAVED_OUTPUT_FAMILIES_ORIGINAL_STATUSES_PRESERVED",
             "all_four_saved_output_families_verified":verified,"original_numeric_COMPLETE_jobs":original_complete_count,
             "original_numeric_resource_failure_jobs":4-original_complete_count,
             "original_execution_statuses_rewritten":False,
             "saved_output_acceptance_scope_sha256":reader.pins[ACCEPTANCE_SCOPE],
             "public_saved_output_acceptance_freeze_commit":args.acceptance_freeze_commit,
             "all_four_numeric_executions_complete":complete,"fully_audited_summary_complete":audited_complete,
             "all_required_local_and_acquisition_QA_pass":all_required_QA_pass,"summary_mode":"VERIFIED_SAVED_OUTPUTS_ONLY",
             "batch_rankings_separate_no_global_reranking":True,
             "profile_identity_fields":["source_chunk_id","batch_id","track_id"],
             "completed_scan_tiles":tiles,"expected_scan_tiles":1524,
             "profile_count":len(profiles),"expected_profile_count":36,
             "ON_carrier_origin_entries":entries,"evaluated_hypothesis_combinations":entries*1526,
             "expected_ON_carrier_origin_entries_if_complete":6242304,
             "expected_evaluated_hypothesis_combinations_if_complete":9525755904,
             "checkpoint_preserves_maximum_not_each_hypothesis_score":True,
             "coverage":{"by_chunk":by_chunk,"full_safe_reference_core_count_per_chunk_if_complete":254,
                         "full_safe_reference_fraction_per_chunk_if_complete":0.9921875,
                         "unsearched_edge_intervals_relative_half_open":[[0,4096],[1044480,1048576]],
                         "partial_counts_from_checkpoints_not_independent_NPZ_QA":True},
             "batches":batches,"profiles":profiles,"acquisition_metadata":acquisitions,
             "path_preflight_recovery":preflight,
             "numeric_CPU_cap_s_per_batch":scope["CPU_cap_s_per_batch"],
             "joint_source_cell_QA":source_cell_QA,"one_historical_visit":True,"visit_date":"2016-03-17",
             "source_chunk_values_received_after_prospective_freeze":True,"blind_validation":False,
             "A_B":"FAIL_CLOSED_UNCHANGED","qualified_sky_pilot":False,"old_holdouts_reopened":False,
             "OFF_veto":False,"calibrated_SNR_FAP_flux_EIRP_or_sensitivity":False,
             "origin_classification":False,"general_null_result_claim":False,"independent_trials_claim":False,
             "new_telescope_HTTP_requests_during_analysis":0,"new_telescope_BODY_bytes_during_analysis":0,
             "metadata_selection_canonical_SHA256":SELECTION_SHA,
             "public_code_freeze_commit":FROZEN_CODE_COMMIT,"common_execution_scope_sha256":reader.pins[SCOPE],
             "detector_wrapper_sha256":scope["script_sha256"],
             "stage_CPU_planning_allocation_s":scope["stage_CPU_planning_allocation_s"],
             "original_full_source_file_MD5_verified":False}
    if verified and (tiles!=1524 or entries!=6242304 or entries*1526!=9525755904
                     or any(c["completed_core_count"]!=254 for value in by_chunk.values() for c in value["by_ON"].values())):
        raise ValueError("Complete four-batch aggregate counts differ from metadata geometry")
    reader.unchanged()
    out.mkdir(parents=True, exist_ok=False)
    dump_json(out/"VERIFIED_SAVED_SUMMARY.json", summary)
    write_csv(out/"PROFILE_SUMMARY.csv", profiles)
    report.write_text(render_report(summary))
    reader.unchanged()
    resources = {"process_CPU_seconds_including_imports": time.process_time(),
                 "wall_seconds_including_imports": time.monotonic()-started,
                 "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
    if (resources["process_CPU_seconds_including_imports"] > CPU_CAP
            or resources["wall_seconds_including_imports"] > WALL_CAP
            or resources["peak_RSS_bytes"] > MEMORY_CAP):
        raise TimeoutError("Measured saved-summary resources exceed caps")
    receipt = {"status": "PASS_PINNED_JSON_SUMMARIZATION_NOT_DETECTOR_OR_RAW_QA",
               "mode": "VERIFIED_SAVED_OUTPUTS_ONLY", "script_sha256": sha256(Path(__file__).read_bytes()),
               "input_pins_sha256": reader.pins_sha, "opened_inputs": reader.opened,
               "output_hashes": {str(p.relative_to(root)): sha256(p.read_bytes())
                                  for p in (out/"VERIFIED_SAVED_SUMMARY.json", out/"PROFILE_SUMMARY.csv", report)},
               "HDF5_or_NPZ_opened": False, "detector_rerun": False, "global_reranking": False,
               "classification_or_OFF_optimization": False,
               "original_execution_statuses_rewritten":False,"root_GO_required": True, **resources}
    dump_json(out/"SUMMARY_EXECUTION_RECEIPT.json", receipt)
    signal.alarm(0)
    print(json.dumps({"status": receipt["status"], "original_numeric_executions_all_COMPLETE": complete, "saved_output_families_verified": verified,
                      "fully_audited_summary_complete": audited_complete,
                      "completed_tiles": summary["completed_scan_tiles"], "profiles": len(profiles),
                      "evaluated_hypothesis_combinations": entries*1526, **resources}, allow_nan=False))


if __name__ == "__main__":
    main()
