"""Pure saved-JSON contracts copied from the audited summary; no values read on import.

Original source SHA78ae0404bfbb0732503416369f3cea66c2a73cc52abb6fe5ccb9f07be8bd10c4.
Stage names/identities are supplied by a separately pinned postprocessing scope.
No preflight recovery semantics or exceptional-output admission are inherited.
"""
import csv, hashlib, json, math
from pathlib import Path
SCANS=("epoch1_on","epoch1_off","epoch2_on","epoch2_off","epoch3_on","epoch3_off")
ONS=SCANS[::2]
SHORT=dict(zip(SCANS,("ON1","OFF1","ON2","OFF2","ON3","OFF3")))
ADJACENT={"epoch1_on":(None,"epoch1_off"),"epoch2_on":("epoch1_off","epoch2_off"),"epoch3_on":("epoch2_off","epoch3_off")}
COMPLETE_STATUS="COMPLETE_127_NEW_NATIVE_CORE_BATCH_EXPLORATORY_ONLY"

def configure(config):
    global STAGE,SCOPE,FROZEN_CODE_COMMIT,SELECTION_SHA,ACQUISITION_SCOPE_BINDING_KEY,ACQUISITION_QA_SCRIPT_SHA
    STAGE=config["results_directory"]
    SCOPE=config["numerical_scope_path"]
    FROZEN_CODE_COMMIT=config["original_scientific_freeze_commit"]
    SELECTION_SHA=config["selection_canonical_sha256"]
    ACQUISITION_SCOPE_BINDING_KEY=config["acquisition_QA_scope_binding_key"]
    ACQUISITION_QA_SCRIPT_SHA=config["acquisition_QA_script_sha256"]


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
                or qa["qa_script_sha256"]!=ACQUISITION_QA_SCRIPT_SHA
                or qa["source_chunk_id"]!=chunk or qa["freeze_commit"]!=FROZEN_CODE_COMMIT
                or qa["acquisition_scope_sha256"]!=context["acquisition_scope_sha256"]
                or qa["acquisition_script_sha256"]!=context["acquisition_script_sha256"]
                or qa["source_manifest_sha256"]!=context["source_manifest_sha256"]
                or qa[ACQUISITION_SCOPE_BINDING_KEY]!=reader.pins[SCOPE]
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

def load_batch(reader, scope, chunk, batch, selection, acquisition):
    prefix=f"{STAGE}/chunk{chunk}/batch_{batch:02d}/measurement/"
    qs=selection["batch_q"][batch-1]
    context=scope["chunk_contracts"][str(chunk)]
    checkpoint_path=prefix+"DRIFT_CHECKPOINT.json"
    result={"source_chunk_id":chunk,"batch_id":batch,"fixed_batch_q":qs,
            "status":"NO_PINNED_RESULT_AVAILABLE","execution_complete":False,
            "checkpoint_all_tiles_present":False,"completed_scan_tiles":0,
            "completed_q_by_ON":{scan:[] for scan in ONS},"profile_count":0,
            "QA_status":"NOT_PROVIDED","profiles":[]}
    failure_path=prefix+"FAILURE_RECEIPT.json"
    if (reader.root/failure_path).exists():
        raise ValueError("Original COMPLETE-only stage cannot admit a numerical failure receipt")
    failure=reader.load(failure_path) if reader.present(failure_path) else None
    if failure is not None:
        if (failure["source_chunk_id"]!=chunk or failure["batch_id"]!=batch or failure["fixed_batch_q"]!=qs):
            raise ValueError("Failure receipt chunk/batch identity changed")
        result.update(status=failure["status"],failure_receipt=failure)
    if not reader.present(checkpoint_path):
        return result
    checkpoint=reader.load(checkpoint_path)
    done,all_tiles=checkpoint_summary(checkpoint,batch,qs,chunk*1048576,chunk)
    result.update(completed_q_by_ON=done,completed_scan_tiles=checkpoint["completed_scan_tiles"],
                  checkpoint_all_tiles_present=all_tiles,status="PARTIAL_PINNED_CHECKPOINT")
    if failure is not None:
        result["status"]=failure["status"]
    execution_path=prefix+"EXECUTION_RECEIPT.json"
    execution=reader.load(execution_path) if reader.present(execution_path) else None
    if execution is not None:
        if (execution["source_chunk_id"]!=chunk or execution["batch_id"]!=batch
                or execution["fixed_batch_q"]!=qs or execution["scope_sha256"]!=reader.pins[SCOPE]
                or execution["script_sha256"]!=scope["script_sha256"]
                or execution["metadata_selection_canonical_SHA256"]!=SELECTION_SHA
                or execution["status"]!=COMPLETE_STATUS
                or execution["source_manifest_sha256"]!=context["source_manifest_sha256"]
                or execution["acquisition_summary_sha256"]!=acquisition.get("receipt_sha256")):
            raise ValueError("Execution receipt differs from frozen native chunk and batch")
        if (execution["one_historical_visit"] is not True
                or execution["source_chunk_values_received_after_prospective_freeze"] is not True
                or execution["blind_or_independent_validation"] is not False
                or execution["OFF_veto_applied"] is not False or execution["qualified_sky_pilot"] is not False
                or execution["old_A_B_failure_statuses_changed"] is not False
                or execution["old_holdouts_reopened"] is not False
                or execution["calibrated_SNR_FAP_flux_EIRP_or_sensitivity"] is not False
                or execution["whole_original_source_MD5_verified"] is not False
                or execution["numeric_retry_authorized"] is not False
                or execution["completion_of_other_chunk_or_batch_inferred"] is not False
                or execution["new_telescope_HTTP_requests_during_analysis"]!=0
                or execution["new_telescope_BODY_bytes_during_analysis"]!=0):
            raise ValueError("Scientific, source or single-attempt contract changed")
        resources={k:finite(execution[k],k) for k in
                   ("process_CPU_seconds_including_imports","wall_seconds_including_imports","peak_RSS_bytes")}
        if (resources["process_CPU_seconds_including_imports"]>scope["CPU_cap_s_per_batch"]
                or resources["wall_seconds_including_imports"]>scope["wall_cap_s_per_batch"] or resources["peak_RSS_bytes"]>4*1024**3
                or execution["CPU_cap_s"]!=scope["CPU_cap_s_per_batch"]
                or execution["wall_cap_s"]!=scope["wall_cap_s_per_batch"]
                or execution["memory_cap_bytes"]!=scope["memory_cap_bytes_per_batch"]
                or execution["search_summary"]["completed_scan_tiles"]!=381
                or execution["fixed_profile_summary"]["profile_count"]!=9 or not all_tiles):
            raise ValueError("COMPLETE native receipt fails resources or completeness")
        pins_path=prefix+"INPUT_PINS.json"
        pins=reader.load(pins_path)
        if (pins["source_chunk_id"]!=chunk or pins["batch_id"]!=batch
                or pins["scope_sha256"]!=reader.pins[SCOPE] or pins["script_sha256"]!=scope["script_sha256"]
                or pins["source_manifest_sha256"]!=context["source_manifest_sha256"]
                or pins["acquisition_summary_sha256"]!=acquisition["receipt_sha256"]
                or pins["compact_files_and_96_decoded_row_pins"]!=acquisition["decoded_files"]):
            raise ValueError("Executed input pins differ from completed acquisition metadata")
        result.update(execution_resources=resources,execution_complete=failure is None,
                      status=execution["status"] if failure is None else failure["status"],
                      acquisition_summary_sha256=acquisition["receipt_sha256"],
                      source_manifest_sha256=context["source_manifest_sha256"])
    top_path,profile_path=prefix+"DRIFT_TOP20.json",prefix+"FIXED_TOP3_PROFILES.json"
    if reader.present(profile_path):
        if not reader.present(top_path) or not all_tiles:
            raise ValueError("Saved profiles require pinned top20 and complete search checkpoint")
        top20=reader.load(top_path)
        expected=top20_check(top20,batch,qs,chunk*1048576,chunk)
        if execution is not None and execution["fixed_profile_summary"]["source_top20_sha256"]!=reader.pins[top_path]:
            raise ValueError("Fixed profiles differ from pinned top20 provenance")
        result["profiles"]=profile_summaries(reader.load(profile_path),expected,batch,result["execution_complete"],chunk)
        result["profile_count"]=len(result["profiles"])
    if result["execution_complete"] and result["profile_count"]!=9:
        raise ValueError("Complete native batch requires nine fixed profiles")
    qa_path=prefix+"QA_RECEIPT.json"
    if reader.present(qa_path):
        qa=reader.load(qa_path)
        expected_counts={"maps":381,"normalization_files":381,"carrier_maximum_records":1560576,
                         "top20_entries":60,"patches":9,"scan_profiles":54,"time_rows":864,
                         "retained_raw_patch_cells":111456,"binary_and_normalization_hashes":771}
        bindings={"execution_receipt_sha256":execution_path,"INPUT_PINS_sha256":prefix+"INPUT_PINS.json",
                  "checkpoint_sha256":checkpoint_path,"top20_sha256":top_path,"profile_JSON_sha256":profile_path,
                  "acquisition_summary_sha256":context["acquisition_summary_path"]}
        if (qa["status"]!="PASS_COMPLETE_SAVED_NATIVE_BATCH_OUTPUTS"
                or qa["source_chunk_id"]!=chunk or qa["batch_id"]!=batch or qa["fixed_batch_q"]!=qs
                or qa["freeze_commit"]!=FROZEN_CODE_COMMIT or qa["public_scope_sha256"]!=reader.pins[SCOPE]
                or qa["public_wrapper_sha256"]!=scope["script_sha256"] or qa["counts"]!=expected_counts
                or any(qa[key]!=reader.pins.get(path) for key,path in bindings.items())):
            raise ValueError("Saved-output QA receipt differs from actual pinned native batch metadata")
        result.update(QA_status=qa["status"],QA_receipt_sha256=reader.pins[qa_path])
    return result

def number(value, digits=6):
    if value is None:
        return "—"
    return f"{value:.{digits}f}".replace(".", ",")

def write_csv(path, profiles):
    columns = ["source_chunk_id", "batch_id", "track_id", "originating_scan", "display_rank", "source_reference_channel",
               "reference_frequency_hz", "reference_seconds_from_anchor", "drift_hz_s", "width_channels",
               "saved_robust_score", *[s+"_mean_center_minus_flank" for s in SCANS],
               "origin_positive_rows", "origin_first_eight_mean", "origin_last_eight_mean",
               "batch_execution_complete", "classification"]
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
