#!/usr/bin/env python3
"""Summarize the three new COMPLETE boundary families from pinned JSON only.

No reviewed scientific array is opened or recomputed by this module. The prior
native scopes, measurements and terminal statuses are never written.
"""
import time
WALL_STARTED = time.monotonic()
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import resource
import signal
RUN_DIRECTORY = None

ROOT = Path(__file__).resolve().parents[2]
TOOLS = "tools/radio_internal_boundaries_20261010"
STAGE = "results/radio_internal_boundaries_20261010"
SCOPE = TOOLS + "/scope.json"
ACTIVATION = TOOLS + "/ACTIVATION_SCOPE.json"
SOURCE_AUDIT = STAGE + "/review/SOURCE_CELL_QA_RECEIPT.json"
REPORT = "RADIO_INTERNAL_BOUNDARIES_REPORT_2026-10-10.md"
SUMMARY = STAGE + "/summary/SAVED_SUMMARY.json"
PINS = STAGE + "/SUMMARY_INPUT_PINS.json"
SUMMARY_RECEIPT = STAGE + "/summary/SUMMARY_EXECUTION_RECEIPT.json"
PAIR_IDS = ("pair153_154", "pair154_155", "pair157_158")
PAIR_CHUNKS = ((153, 154), (154, 155), (157, 158))
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]
SHORT = dict(zip(SCANS, ("ON1", "OFF1", "ON2", "OFF2", "ON3", "OFF3")))
SELECTION_SHA = "3b447a80d662289fef3e5d4574a2f725808c2952db768814462e407bb56bc36b"
COMPLETE = "COMPLETE_TWO_JOINED_BOUNDARY_CORES_EXPLORATORY_ONLY"
QA_PASS = "PASS_COMPLETE_SAVED_JOINED_BOUNDARY_OUTPUTS"
AUDIT_PASS = "PASS_27_FIXED_RAW_PATCHES_AUTHENTICATED_BITWISE_TO_SOURCE"
NORMALIZATION_METHOD = "median of all2097152 joined raw float32 channels in each row, then float64 promotion (NumPy2.3.5)"
MEASUREMENT_JSON = ("INPUT_PINS.json", "DRIFT_CHECKPOINT.json", "DRIFT_TOP20.json",
                    "FIXED_TOP3_PROFILES.json", "NORMALIZATION.json", "EXECUTION_RECEIPT.json")
QA_COUNTS = {"maps": 6, "normalization_files": 6, "carrier_maximum_records": 24576,
             "top20_entries": 60, "patches": 9, "scan_profiles": 54, "time_rows": 864,
             "retained_raw_patch_cells": 111456, "binary_and_normalization_hashes": 21}
CPU_CAP, WALL_CAP, MEMORY_CAP = 20, 1800, 2 * 1024**3


def check(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_pin(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            digest.update(block)
    return {"sha256": digest.hexdigest(), "bytes": path.stat().st_size}


def project_path(root, name):
    relative = Path(name)
    path = root / relative
    check(not relative.is_absolute() and ".." not in relative.parts
          and not path.is_symlink() and path.resolve().is_relative_to(root), "Non-project path forbidden: " + name)
    return path


def finite(value):
    check(not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value), "Finite scalar required")
    return value


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    temporary.replace(path)


class PinnedJSON:
    def __init__(self, root, path):
        self.root, self.path = root, path.resolve()
        raw = self.path.read_bytes()
        self.sha = sha(raw)
        self.input_map_pin = {"sha256": self.sha, "bytes": len(raw)}
        self.pins = json.loads(raw)
        self.opened = {}
        check(isinstance(self.pins, dict) and self.pins, "Explicit nonempty JSON input pins required")
        for name, expected in self.pins.items():
            project_path(root, name)
            check(name.endswith(".json") and isinstance(expected, str) and len(expected) == 64
                  and all(c in "0123456789abcdef" for c in expected), "Invalid JSON input pin")

    def load(self, name):
        check(name in self.pins, "Missing explicit JSON pin: " + name)
        raw = project_path(self.root, name).read_bytes()
        check(sha(raw) == self.pins[name], "Changed JSON input: " + name)
        self.opened[name] = {"sha256": sha(raw), "bytes": len(raw)}
        return json.loads(raw)

    def unchanged(self):
        check(sha(self.path.read_bytes()) == self.sha, "Input pin map changed")
        for name, pin in self.opened.items():
            check(file_pin(project_path(self.root, name)) == pin, "Opened JSON input changed: " + name)


def required_inputs(scope):
    names = {SCOPE, ACTIVATION, SOURCE_AUDIT}
    for pair_id in PAIR_IDS:
        contract = scope["pair_contracts"][pair_id]
        names.update(contract["measurement_directory"] + "/" + n for n in MEASUREMENT_JSON)
        names.add(contract["QA_receipt_path"])
    check(len(names) == 24, "Exactly twenty-four saved JSON inputs required")
    return names


def verify_scope(reader, expected):
    scope, activation = reader.load(SCOPE), reader.load(ACTIVATION)
    check(reader.pins[SCOPE] == expected, "Exact public boundary scope pin required")
    selection = activation["immutable_metadata_selection"]
    canonical = (json.dumps(selection, sort_keys=True, separators=(",", ":")) + "\n").encode()
    check(sha(canonical) == activation["metadata_selection_canonical_SHA256"] == SELECTION_SHA
          and scope["metadata_selection_canonical_SHA256"] == SELECTION_SHA
          and scope["immutable_metadata_selection"] == selection
          and activation["zero_cost_continuation_authorized"] is True, "Fixed boundary selection changed")
    check(selection["pair_ids"] == list(PAIR_IDS) and selection["native_pairs"] == [list(p) for p in PAIR_CHUNKS]
          and selection["joined_reference_core_q"] == [255, 256]
          and selection["joined_channel_count"] == 2097152 and selection["core_channel_count"] == 4096
          and selection["scan_order"] == list(SCANS)
          and selection["drift_grid_hz_s"] == {"first": -4, "last": 4, "count": 763}
          and selection["widths_channels"] == [1, 3], "Boundary geometry/grid changed")
    check(set(scope["pair_contracts"]) == set(PAIR_IDS), "Exactly three pair contracts required")
    check(set(scope["chunk_contracts"]) == {"153", "154", "155", "157", "158"}, "Only five retained native source chunks allowed")
    for field, value in {"schema": "SETI_THREE_JOINED_INTERNAL_BOUNDARY_PAIRS_V1", "joined_reference_core_q": [255, 256],
        "native_channel_count": 1048576, "joined_channel_count": 2097152, "rows_per_scan": 16,
        "scan_order": list(SCANS), "origin_scan_order": list(ONS), "drift_grid": {"first_hz_s": -4, "last_hz_s": 4, "count": 763},
        "widths_channels": [1, 3], "valid_hypotheses_per_carrier": 1526, "CPU_cap_s_per_pair": 120,
        "wall_cap_s_per_pair": 1800, "memory_cap_bytes_per_pair": 4*1024**3, "analysis_attempts_per_pair": 1,
        "numeric_retry_authorized": False, "numeric_pairs_serial": True, "old_holdouts_reopened": False,
        "protected_old_native_chunks_not_read": [156, 159], "original_scopes_terminal_statuses_and_outputs_modified": False,
        "OFF_veto": False, "blind_or_independent_validation": False, "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False,
        "new_HTTP_requests": 0, "new_BODY_bytes": 0, "joined_profile_normalization_method": NORMALIZATION_METHOD}.items():
        check(scope[field] == value, "Frozen scientific/resource contract differs: "+field)
    check(scope["summary_script_path"] == TOOLS+"/summarize_saved.py"
          and scope["package_script_path"] == TOOLS+"/package_saved.py"
          and scope["summary_CPU_cap_s"] == CPU_CAP and scope["summary_wall_cap_s"] == WALL_CAP
          and scope["summary_memory_cap_bytes"] == MEMORY_CAP, "Summary executable or resource contract changed")
    check(Path(__file__).resolve() == project_path(reader.root, scope["summary_script_path"]).resolve()
          and file_pin(Path(__file__))["sha256"] == scope["summary_script_sha256"], "Imported summary differs from frozen project code")
    for field in ("script", "qa_script", "source_audit_script", "summary_script", "package_script"):
        check(scope["pinned_dependency_files"][scope[field+"_path"]]["sha256"] == scope[field+"_sha256"],
              "Executable dependency pin differs: "+field)
    for name, pin in scope["pinned_dependency_files"].items():
        check(file_pin(project_path(reader.root, name)) == pin, "Frozen code/metadata dependency changed: " + name)
    for pair_id, chunks in zip(PAIR_IDS, PAIR_CHUNKS):
        c = scope["pair_contracts"][pair_id]
        check(c["source_chunk_ids"] == list(chunks) and c["source_channel0"] == chunks[0]*1048576
              and c["source_channel_count"] == 2097152 and c["joined_reference_core_q"] == [255, 256]
              and c["measurement_directory"] == f"{STAGE}/{pair_id}/measurement"
              and c["QA_receipt_path"] == f"{STAGE}/{pair_id}/review/QA_RECEIPT.json"
              and c["QA_required_status"] == QA_PASS, "Pair identity/path/geometry changed")
    return scope


def load_pair(reader, scope, pair_id, freeze):
    c = scope["pair_contracts"][pair_id]
    prefix = c["measurement_directory"] + "/"
    check(not project_path(reader.root, prefix+"FAILURE_RECEIPT.json").exists(), "Original boundary FAILED output cannot be admitted")
    data = {n: reader.load(prefix+n) for n in MEASUREMENT_JSON}
    execution, inputs = data["EXECUTION_RECEIPT.json"], data["INPUT_PINS.json"]
    check(execution["status"] == COMPLETE and execution["pair_id"] == inputs["pair_id"] == pair_id
          and execution["scope_sha256"] == inputs["scope_sha256"] == reader.pins[SCOPE]
          and execution["script_sha256"] == inputs["script_sha256"] == scope["script_sha256"], "Original new COMPLETE identity required")
    for value in (execution, inputs):
        check(value["source_chunk_ids"] == c["source_chunk_ids"] and value["source_channel0"] == c["source_channel0"]
              and value["source_channel_count"] == 2097152 and value["public_freeze_commit"] == freeze,
              "Original pair geometry or public freeze differs")
    check(execution["fixed_pair_q"] == [255, 256] and execution["metadata_selection_canonical_SHA256"] == SELECTION_SHA,
          "Original finite selection differs")
    expected_sources = {}
    for chunk in c["source_chunk_ids"]:
        context = scope["chunk_contracts"][str(chunk)]
        expected_sources[str(chunk)] = {"source_manifest_sha256": context["source_manifest_sha256"],
            "acquisition_summary_sha256": context["acquisition_summary_sha256"], "acquisition_QA_sha256": context["acquisition_QA_sha256"],
            "compact_files_and_96_decoded_row_pins": context["compact_files_and_96_decoded_row_pins"]}
        expected_verified = {r["scan_id"]: {"path": r["array_file"], "file_sha256": r["file_sha256"], "bytes": r["bytes"]}
                             for r in context["compact_files_and_96_decoded_row_pins"]}
        check(set(expected_verified) == set(SCANS) and execution["verified_source_inputs"][str(chunk)] == expected_verified,
              "Six original verified compact declarations per native side required")
    check(inputs["source_inputs"] == execution["source_inputs"] == expected_sources
          and set(execution["verified_source_inputs"]) == set(expected_sources), "Exact original source declarations required")
    admission = inputs["runtime_admission_receipts"]
    check(admission == execution["runtime_admission_receipts"], "Original late admission pins differ")
    if pair_id == "pair157_158":
        gate = scope["runtime_158_admission"]
        names = {j[k] for j in gate["jobs"] for k in ("execution_receipt_path", "QA_receipt_path")}
        names.add(gate["source_audit_receipt_path"])
        check(len(gate["jobs"]) == 2 and {j["batch_id"] for j in gate["jobs"]} == {1, 2}
              and len(names) == 5 and set(admission) == names, "Both original158 admissions required")
        for name, pin in admission.items():
            check(file_pin(project_path(reader.root, name)) == pin, "Original runtime admission bytes changed")
    else:
        check(admission == {}, "Unexpected runtime admission")
    for field, value in {"one_historical_visit": True, "blind_or_independent_validation": False,
        "qualified_sky_pilot": False, "OFF_veto_applied": False, "original_scopes_terminal_statuses_and_outputs_modified": False,
        "old_holdouts_reopened": False, "numeric_retry_authorized": False, "whole_original_source_MD5_verified": False,
        "new_HTTP_requests": 0, "new_BODY_bytes": 0, "cost_DKK": 0, "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False}.items():
        check(execution[field] == value, "Original scientific/resource contract differs: "+field)
    resources = {k: finite(execution[k]) for k in ("process_CPU_seconds_including_imports", "wall_seconds_including_imports", "peak_RSS_bytes")}
    check(0 < resources["process_CPU_seconds_including_imports"] <= 120
          and 0 < resources["wall_seconds_including_imports"] <= 1800
          and 0 < resources["peak_RSS_bytes"] <= 4*1024**3
          and execution["CPU_cap_s"] == 120 and execution["wall_cap_s"] == 1800
          and execution["memory_cap_bytes"] == 4*1024**3
          and execution["search_summary"]["completed_scan_tiles"] == 6
          and execution["fixed_profile_summary"]["profile_count"] == 9, "Original numerical resource/completion gate changed")
    checkpoint = data["DRIFT_CHECKPOINT.json"]
    expected = [(scan, q) for q in (255, 256) for scan in ONS]
    check(checkpoint["pair_id"] == pair_id and checkpoint["fixed_pair_q"] == [255, 256]
          and checkpoint["complete"] is True and checkpoint["completed_scan_tiles"] == checkpoint["expected_scan_tiles"] == 6
          and [(e["scan_id"], e["reference_core_q"]) for e in checkpoint["completed_receipts"]] == expected
          and checkpoint["completed_q_by_ON"] == {scan: [255, 256] for scan in ONS}
          and checkpoint["completed_core_count_by_ON"] == {scan: 2 for scan in ONS}, "Complete fixed six-map checkpoint required")
    inventory = {}
    for entry in checkpoint["completed_receipts"]:
        first = c["source_channel0"] + entry["reference_core_q"]*4096
        check(entry["searched_carriers"] == 4096 and entry["valid_hypotheses_per_carrier"] == 1526
              and entry["reference_channel_interval_half_open"] == [first, first+4096], "Saved reference-carrier contract changed")
        for pathkey, hashkey, sizekey in (("path", "sha256", "bytes"), ("normalization_path", "normalization_sha256", "normalization_bytes")):
            name = prefix + entry[pathkey]
            project_path(reader.root, name)
            check(name not in inventory, "Duplicate map/normalization path")
            inventory[name] = {"sha256": entry[hashkey], "bytes": entry[sizekey]}
    norm = data["NORMALIZATION.json"]
    check(norm["method"] == NORMALIZATION_METHOD and norm["source_channel0"] == c["source_channel0"]
          and norm["source_channel_count"] == 2097152 and norm["source_chunk_ids"] == c["source_chunk_ids"]
          and set(norm["row_power_medians"]) == set(SCANS), "Separate joined2N profile normalization required")
    for scan in SCANS:
        medians = norm["row_power_medians"][scan]
        check(len(medians) == 16 and all(finite(v) > 0 for v in medians), "Six positive finite sixteen-row medians required")
    check(execution["saved_normalization_sha256"] == reader.pins[prefix+"NORMALIZATION.json"], "Original profile normalization pin changed")
    top = data["DRIFT_TOP20.json"]
    check(set(top) == set(ONS), "All three separate ON rankings required")
    selected = []
    for scan in ONS:
        check(len(top[scan]) == 20, "Exactly twenty unchanged ranks per ON required")
        for rank, track in enumerate(top[scan], 1):
            q, channel = track["reference_core_q"], track["source_reference_channel"]
            check(track["pair_id"] == pair_id and track["family"] == "internal_boundary_drift"
                  and track["originating_scan"] == scan and track["originating_role"] == "ON"
                  and track["track_id"] == scan+"_gap_drift_rank_%02d" % rank
                  and track["display_rank"] == rank and q in (255, 256)
                  and track["source_chunk_id"] == c["source_chunk_ids"][q-255]
                  and track["source_native_core_q"] == (255 if q == 255 else 0)
                  and track["reference_core_tile"] == q-255 and track["status"] == "EXPLORATORY_RANK_UNCLASSIFIED"
                  and c["source_channel0"]+q*4096 <= channel < c["source_channel0"]+(q+1)*4096
                  and track["width_channels"] in (1, 3) and -4 <= finite(track["drift_hz_s"]) <= 4,
                  "Saved pair-local track identity/geometry changed")
            finite(track["maximum_robust_box_track_score"])
            check(math.isclose(finite(track["reference_frequency_hz"]), 1876464843.75-2.835503418452676*channel, rel_tol=0, abs_tol=1e-6), "Reference frequency differs from fixed grid")
        selected.extend(top[scan][:3])
    records = data["FIXED_TOP3_PROFILES.json"]
    check(len(records) == 9 and [r["selected_track"] for r in records] == selected
          and execution["fixed_profile_summary"]["source_top20_sha256"] == reader.pins[prefix+"DRIFT_TOP20.json"], "Exactly nine unchanged original top3 profiles required")
    profiles = []
    for record in records:
        t = record["selected_track"]
        check(record["fixed_frequency_shift_channels"] == 0 and record["classification"] == "UNRESOLVED_EXPLORATORY_PROFILE_NO_SKY_INFERENCE"
              and [p["scan_id"] for p in record["scan_profiles"]] == list(SCANS), "Fixed six-scan profile contract changed")
        for scan in record["scan_profiles"]:
            finite(scan["mean_center_minus_flank"])
            check(len(scan["all_16_center_minus_flank_rows"]) == 16, "Sixteen saved profile rows required")
            for value in scan["all_16_center_minus_flank_rows"]:
                finite(value)
        name = prefix + record["patch"]["path"]
        project_path(reader.root, name)
        check(name not in inventory, "Duplicate fixed patch path")
        inventory[name] = {"sha256": record["patch"]["sha256"], "bytes": record["patch"]["bytes"]}
        profiles.append({"identity": [pair_id, t["track_id"]], "pair_id": pair_id, "selected_track": t,
                         "scan_profiles": record["scan_profiles"], "patch_provenance": record["patch"],
                         "classification": record["classification"], "profile_normalization": NORMALIZATION_METHOD})
    qa = reader.load(c["QA_receipt_path"])
    check(not project_path(reader.root, str(Path(c["QA_receipt_path"]).with_name("QA_FAILURE_RECEIPT.json"))).exists(),
          "Failed saved QA cannot be admitted")
    hashes = {prefix+n: reader.pins[prefix+n] for n in MEASUREMENT_JSON}
    bindings = {"execution_receipt_sha256": "EXECUTION_RECEIPT.json", "INPUT_PINS_sha256": "INPUT_PINS.json",
                "checkpoint_sha256": "DRIFT_CHECKPOINT.json", "top20_sha256": "DRIFT_TOP20.json",
                "profile_JSON_sha256": "FIXED_TOP3_PROFILES.json", "saved_normalization_sha256": "NORMALIZATION.json"}
    qa_inventory = {p["path"]: {"sha256": p["sha256"], "bytes": p["bytes"]} for p in qa["output_byte_pins"]}
    check(qa["status"] == QA_PASS and qa["pair_id"] == pair_id and qa["freeze_commit"] == freeze
          and qa["public_scope_sha256"] == reader.pins[SCOPE] and qa["public_wrapper_sha256"] == scope["script_sha256"]
          and qa["qa_script_sha256"] == scope["qa_script_sha256"] and qa["counts"] == QA_COUNTS
          and qa["input_json_sha256"] == hashes and all(qa[k] == reader.pins[prefix+n] for k, n in bindings.items())
          and len(qa["output_byte_pins"]) == len(qa_inventory) == len(inventory) == 21 and qa_inventory == inventory,
          "Actual matching saved-output QA and all twenty-one output byte pins required")
    check(qa["source_chunk_ids"] == c["source_chunk_ids"] and qa["source_channel0"] == c["source_channel0"]
          and qa["source_channel_count"] == 2097152 and qa["fixed_pair_q"] == [255, 256]
          and qa["profile_identity_fields"] == ["pair_id", "track_id"]
          and qa["cap_CPU_s_this_QA"] == 20 and qa["cap_wall_s_this_QA"] == 300 and qa["cap_memory_bytes"] == 2*1024**3
          and 0 < finite(qa["process_CPU_seconds_including_imports"]) <= 20
          and 0 < finite(qa["wall_seconds"]) <= 300 and 0 < finite(qa["peak_RSS_bytes"]) <= 2*1024**3,
          "Actual saved QA geometry/resources required")
    opened = {p["path"]: {"sha256": p["sha256"], "bytes": p["bytes"]} for p in qa["opened_json_pins"]}
    check(len(opened) == len(qa["opened_json_pins"]), "Duplicate saved QA JSON pins")
    for name, pin in opened.items():
        check(file_pin(project_path(reader.root, name)) == pin, "Saved QA opened metadata changed")
    return {"pair_id": pair_id, "source_chunk_ids": c["source_chunk_ids"], "original_numeric_status": execution["status"],
            "execution_receipt_path": prefix+"EXECUTION_RECEIPT.json", "execution_receipt_sha256": reader.pins[prefix+"EXECUTION_RECEIPT.json"],
            "execution_resources": resources, "completed_scan_tiles": 6, "fixed_profile_count": 9,
            "QA_receipt_path": c["QA_receipt_path"], "QA_receipt_sha256": reader.pins[c["QA_receipt_path"]],
            "QA_status": qa["status"], "normalization_sha256": reader.pins[prefix+"NORMALIZATION.json"],
            "profiles": profiles, "output_byte_pins": inventory, "runtime_admission_receipts": admission,
            "QA_opened_json_pins": opened}


def source_audit(reader, scope, pairs, freeze):
    audit = reader.load(SOURCE_AUDIT)
    profiles = [p for pair in pairs for p in pair["profiles"]]
    counts = {"compact_files": 30, "decoded_rows": 480, "patches": 27, "scan_profiles": 162,
              "time_rows": 2592, "raw_cells_bitwise_checked": 334368}
    check(audit["status"] == AUDIT_PASS and audit["freeze_commit"] == freeze
          and audit["public_scope_sha256"] == reader.pins[SCOPE] and audit["public_wrapper_sha256"] == scope["script_sha256"]
          and audit["audit_script_sha256"] == scope["source_audit_script_sha256"] and audit["counts"] == counts,
          "Exact separately authorized bitwise source audit required")
    check(audit["profile_identity_fields"] == ["pair_id", "track_id"]
          and audit["compact_file_input_occurrences"] == 36 and audit["decoded_row_input_occurrences"] == 576
          and audit["source_HDF5_files_read_once"] == 30 and audit["source_HDF5_decoded_rows"] == 480
          and audit["CPU_cap_s"] == 60 and audit["wall_cap_s"] == 300 and audit["memory_cap_bytes"] == 4*1024**3
          and 0 < finite(audit["process_CPU_seconds_including_imports"]) <= 60
          and 0 < finite(audit["wall_seconds"]) <= 300 and 0 < finite(audit["peak_RSS_bytes"]) <= 4*1024**3,
          "Exact unique source policy and measured audit resource caps required")
    checks = {(c["pair_id"], c["track_id"]): c for c in audit["patch_checks"]}
    check(len(audit["patch_checks"]) == len(checks) == 27
          and set(checks) == {tuple(p["identity"]) for p in profiles}, "All twenty-seven pair/track identities must match source audit")
    for p in profiles:
        c = checks[tuple(p["identity"])]
        prefix = scope["pair_contracts"][p["pair_id"]]["measurement_directory"] + "/"
        check(c["bitwise_identical"] is True and c["raw_cells"] == 12384
              and c["patch_sha256"] == p["patch_provenance"]["sha256"]
              and c["raw_cell_bytes_SHA256"] == c["independent_source_cell_bytes_SHA256"]
              and c["source_execution_receipt_sha256"] == reader.pins[prefix+"EXECUTION_RECEIPT.json"]
              and c["source_profiles_JSON_sha256"] == reader.pins[prefix+"FIXED_TOP3_PROFILES.json"], "Original pair/patch/source provenance changed")
    return {"status": audit["status"], "receipt_path": SOURCE_AUDIT, "receipt_sha256": reader.pins[SOURCE_AUDIT],
            "counts": counts, "unique_source_file_policy": "Thirty distinct compact files and 480 decoded rows; native 154 reused in two pair provenances"}


def render_report(summary):
    lines = ["# SETI: tre interne båndgrænser", "", "**10. oktober 2026.** De tre nye parfamilier sluttede oprindeligt COMPLETE og består de krævede gemte-output- og kildecellekontroller.", "",
             "Der er gemt 18 ON-feltkort, 180 top20-poster og 27 faste profiler. De 73.728 referencekanal/originposter dækker 112.508.928 evaluerede drift/breddehypotesekombinationer. Tællingerne angiver korrelerede beregninger, ikke uafhængige signaler eller forsøg.", "",
             "Kun de nye sammenføjede q255/q256-felter i 153+154, 154+155 og 157+158 indgår. De gamle referencefelter, scopes og afslutningsstatusser er bevaret. Dette er udforskning af allerede eksponerede data fra ét historisk besøg; to par deler hele native bånd 154.", "",
             "Detektoren beholder sin rå kontekst, robuste aritmetik, 763 drifthastigheder fra −4 til +4 Hz/s og bredder 1/3. De faste profiler bruger en ny nævner: hver rækkes median af alle 2.097.152 sammenføjede rå float32-kanaler, derefter promoveret til float64. Tidligere native medianer genbruges ikke, og profiltal er ikke identiske mål med tidligere native profiler.", "",
             "En særskilt kildekontrol matcher 334.368 råcelleforekomster i 27 profiludklip bit for bit. 30 forskellige kompaktfiler og 480 afkodede rækker kontrolleres; genbrug af bånd 154 skaber 36 fil- og 576 rækkeproveniensforekomster. Rækkemedianerne kontrolleres som gemte nævnere og i profilalgebraen; de genmåles ikke uafhængigt fra hele kildeparret. De store originalfilers fulde MD5 er fortsat ikke verificeret.", "",
             "| Par | Gemte ON-felter | Profiler | Oprindelig status | CPU,s | Vægtid,s |", "| --- | ---: | ---: | --- | ---: | ---: |"]
    for pair in summary["pairs"]:
        r = pair["execution_resources"]
        lines.append(f'| {pair["pair_id"]} |6|9|{pair["original_numeric_status"]}|{r["process_CPU_seconds_including_imports"]:.3f}|{r["wall_seconds_including_imports"]:.3f}|')
    lines += ["", "| Par | ON/rang | Frekvens,MHz | Drift,Hz/s | Bredde | ON1 | OFF1 | ON2 | OFF2 | ON3 | OFF3 |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for p in summary["profiles"]:
        t = p["selected_track"]
        means = "|".join(f'{s["mean_center_minus_flank"]:.6f}' for s in p["scan_profiles"])
        lines.append(f'|{p["pair_id"]}|{SHORT[t["originating_scan"]]}/{t["display_rank"]}|{t["reference_frequency_hz"]/1e6:.6f}|{t["drift_hz_s"]:.6f}|{t["width_channels"]}|{means}|')
    lines += ["", "Alle seks middelresidualer følger det samme uændrede spor. Detektorens rangscore og profilmiddelresidual er forskellige størrelser. ON1 har kun efterfølgende OFF i sekvensen; ON2/ON3 har både forudgående og efterfølgende OFF. En lille værdi langs det præcise OFF-spor udelukker ikke nærliggende OFF-struktur.", "",
              "En union med tidligere 254-referencefelt-dækning kræver særskilt verifikation af den tidligere gemte dækning. Den nye familie udleder ikke dette af sine egne outputs. Kun betinget af sådan verifikation giver unionen 255/256 felter i 153, 155, 157, 158 og 256/256 i 154, alene for det frosne grid og bredder 1/3. Gamle CPU-grænsefejl omklassificeres ikke til COMPLETE.", "",
              "A/B forbliver FAIL_CLOSED; gamle holdouts og beskyttede 156/159 forbliver lukkede. Der fastslås ingen kalibreret SNR, falskalarmrate, flux, EIRP, følsomhed, oprindelse, kvalificeret SETI-kandidat, generelt nulresultat eller uafhængig besøgsvalidering.", "",
              f'Ny kode/scope blev fastlåst ved `{summary["public_freeze_commit"]}` med scope-SHA256 `{summary["scope_sha256"]}`. Opsummeringen læser kun hashpinnet JSON; ingen detektor, rangliste, normalisering eller profil genberegnes. Der er nul nye teleskoprequests/bytes og 0 DKK i denne fase.', ""]
    return "\n".join(lines)


def pair_metadata_unchanged(root, pairs):
    admitted = {}
    for pair in pairs:
        for mapping in (pair["QA_opened_json_pins"], pair["runtime_admission_receipts"]):
            for name, pin in mapping.items():
                check(name not in admitted or admitted[name] == pin, "Conflicting admitted pair metadata: "+name)
                admitted[name] = pin
    for name, pin in admitted.items():
        check(file_pin(project_path(root, name)) == pin, "Admitted pair metadata changed: "+name)


def main():
    global RUN_DIRECTORY
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--pins", required=True)
    parser.add_argument("--expected-scope-sha256", required=True)
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--root-go-after-all-pairs-QA", action="store_true")
    args = parser.parse_args()
    check(args.root_go_after_all_pairs_QA, "Explicit root GO after all three saved QAs and joint source audit required")
    check(len(args.freeze_commit) == 40 and all(c in "0123456789abcdef" for c in args.freeze_commit), "Exact public freeze commit required")
    started = WALL_STARTED
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP+1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    def deadline(signum, frame):
        raise TimeoutError("Saved boundary summary resource deadline exceeded")
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    signal.alarm(WALL_CAP)
    root = Path(args.root).resolve()
    check(Path(args.pins).resolve() == project_path(root, PINS).resolve() and not Path(args.pins).is_symlink(),
          "Use the exact retained summary input pin file")
    out = root / (STAGE+"/summary")
    check(not out.exists() and not (root/REPORT).exists(), "Once-only summary/report destinations must be unused")
    out.mkdir(parents=True, exist_ok=False)
    RUN_DIRECTORY = out
    save(out/"SUMMARY_STARTED.json", {"status": "STARTED_ONCE_ONLY_BOUNDARY_SAVED_JSON_SUMMARY",
         "freeze_commit": args.freeze_commit, "scope_sha256": args.expected_scope_sha256,
         "script_sha256": file_pin(Path(__file__))["sha256"]})
    reader = PinnedJSON(root, Path(args.pins))
    scope = verify_scope(reader, args.expected_scope_sha256)
    check(set(reader.pins) == required_inputs(scope), "Exactly all twenty-four JSON input pins required")
    pairs = [load_pair(reader, scope, pair_id, args.freeze_commit) for pair_id in PAIR_IDS]
    profiles = [p for pair in pairs for p in pair["profiles"]]
    check(len(profiles) == len({tuple(p["identity"]) for p in profiles}) == 27, "Unique complete pair/track identities required")
    audit = source_audit(reader, scope, pairs, args.freeze_commit)
    check(set(reader.opened) == set(reader.pins), "Every required JSON input must be opened and bound")
    summary = {"schema": "SETI_COMPLETE_JOINED_BOUNDARY_SAVED_SUMMARY_V1", "status": "COMPLETE_AUDITED_SAVED_BOUNDARY_FAMILY",
               "original_new_pair_statuses_all_COMPLETE": True, "previous_native_terminal_statuses_rewritten": False,
               "pair_ids": list(PAIR_IDS), "pairs": pairs, "profiles": profiles, "profile_identity_fields": ["pair_id", "track_id"],
               "pair_ON_rankings_separate_no_global_reranking": True, "completed_scan_tiles": 18, "top20_records": 180,
               "profile_count": 27, "scan_profiles": 162, "time_row_occurrences": 2592, "raw_cell_occurrences": 334368,
               "carrier_origin_entries": 73728, "evaluated_hypothesis_combinations": 112508928,
               "scope_sha256": reader.pins[SCOPE], "public_freeze_commit": args.freeze_commit,
               "joint_source_cell_QA": audit, "fixed_profile_normalization": NORMALIZATION_METHOD,
               "original254_coverage_verified_by_this_summary": False, "coverage_union_claims_conditional_on_previous_saved_verification": True,
               "one_historical_visit": True, "visit_date": "2016-03-17", "blind_or_independent_validation": False,
               "A_B": "FAIL_CLOSED_UNCHANGED", "protected_native_chunks_read": [], "old_holdouts_reopened": False,
               "OFF_veto": False, "origin_classification": False, "qualified_sky_pilot": False,
               "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False, "general_null_result_claim": False,
               "independent_trials_claim": False, "whole_original_source_MD5_verified": False,
               "detector_rerun_by_summary": False, "new_HTTP_requests": 0, "new_BODY_bytes": 0, "cost_DKK": 0}
    reader.unchanged()
    pair_metadata_unchanged(root, pairs)
    save(out/"SAVED_SUMMARY.json", summary)
    csv_path = out/"PROFILE_SUMMARY.csv"
    columns = ["pair_id", "track_id", "originating_scan", "display_rank", "reference_frequency_hz", "drift_hz_s", "width_channels"] + [s+"_mean_center_minus_flank" for s in SCANS]
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for p in profiles:
            row = {k: p["selected_track"][k] for k in columns if k in p["selected_track"]}
            row.update(pair_id=p["pair_id"])
            row.update({s["scan_id"]+"_mean_center_minus_flank": s["mean_center_minus_flank"] for s in p["scan_profiles"]})
            writer.writerow(row)
    (root/REPORT).write_text(render_report(summary))
    reader.unchanged()
    pair_metadata_unchanged(root, pairs)
    for name, pin in scope["pinned_dependency_files"].items():
        check(file_pin(project_path(root, name)) == pin, "Frozen dependency changed during summary")
    measured = {"process_CPU_seconds_including_imports": time.process_time(), "wall_seconds_including_imports": time.monotonic()-started,
                "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
    check(measured["process_CPU_seconds_including_imports"] <= CPU_CAP and measured["wall_seconds_including_imports"] <= WALL_CAP
          and measured["peak_RSS_bytes"] <= MEMORY_CAP, "Measured summary caps exceeded")
    receipt = {"status": "PASS_PINNED_COMPLETE_BOUNDARY_JSON_SUMMARY_NO_NUMERIC_RERUN", "script_sha256": file_pin(Path(__file__))["sha256"],
               "scope_sha256": reader.pins[SCOPE], "freeze_commit": args.freeze_commit, "input_pins_sha256": reader.sha,
               "opened_inputs": reader.opened, "output_hashes": {str(p.relative_to(root)): file_pin(p)["sha256"] for p in (out/"SAVED_SUMMARY.json", csv_path, root/REPORT)},
               "HDF5_or_NPZ_opened": False, "detector_rerun": False, "rankings_reselected": False,
               "previous_native_terminal_statuses_rewritten": False, "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP,
               "memory_cap_bytes": MEMORY_CAP, **measured}
    save(out/"SUMMARY_EXECUTION_RECEIPT.json", receipt)
    signal.alarm(0)
    print(json.dumps({"status": receipt["status"], "profiles": 27, "maps": 18, **measured}, allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        if RUN_DIRECTORY is not None:
            save(RUN_DIRECTORY/"SUMMARY_FAILURE_RECEIPT.json", {"status": "INCOMPLETE_BOUNDARY_SUMMARY_NO_RETRY",
                 "error_type": type(error).__name__, "error": str(error), "partial_outputs_preserved": True,
                 "process_CPU_seconds_including_imports": time.process_time(), "wall_seconds_including_imports": time.monotonic()-WALL_STARTED})
        raise
