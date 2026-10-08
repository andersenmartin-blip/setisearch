#!/usr/bin/env python3
"""One explicitly admitted primary pilot after corrected fresh B; preparation is inert.

The complete fresh VAL_B gate, source geometry, reader metadata, every .npy
file hash and the published admission are checked before the first np.load.
Scientific modules are imported only after those checks. No controls, source
downloads, masks, candidate subsets, or scientific parameter changes occur.
The closed failed A record and exactly two successful independent DEV runtime
proofs for the one permitted operational correction are mandatory metadata
prerequisites. A cannot reopen the sky gate and is never rerun by this module.
"""
from __future__ import annotations

import time
PROCESS_STARTED = time.monotonic()

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import sys
import traceback

ROOT = Path(__file__).resolve().parent.parent
PILOT_ID = "primary_HD189733_cadence85030_chunk152_20261008"
FROZEN = {
    "detector": "1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45",
    "dev_helpers": "d64aa962c585f536ea969fb09bcc6e16df4289f6fd4e69f396684b94bd995f49",
    "contract": "44854605dbbe40a2c8aa7805433437e7ef03de31db3c76326d235baa88d7406c",
    "source_manifest": "6a9c166f15de69c378e3346fcd5dac1082790345622b2df3af674f108bf29aec",
    "value_reader": "329b922431a925a08ad48e7315f54f556e1af5f7bccbec0f51d71fb52216ffb0",
    "validation_cases": "93b425038ef9ec178610a1f17856258b0bf726b2e326430db85d4240e48ce46c",
    "failed_validation_a_cases": "1edb1ab43c0ff025662de6ce7f6bd5a00cb3c902e275fa5e38d56794c1b86ad1",
    "summarizer": "6f9153d8c598eb6bb897d0a00dc632906a00ed203c876902fca955b1b7e4b361",
}
CHECKS = {
    "complete_and_integrity", "strong_14_of_14", "operating_at_least_44_of_48",
    "each_activity_at_least_7_of_8", "each_drift_at_least_10_of_12",
    "each_width_at_least_22_of_24", "matched_rfi_no_surviving_cadence",
    "matched_rfi_all_primary_on_detected_before_off", "noise_at_most_one_surviving_cadence",
}
SHA256_RE = re.compile(r"[0-9a-f]{64}")
FAILED_A_IDS = {
    "SETI_RADIO_PILOT_20261008_VAL_A:single_row_transient:010",
    "SETI_RADIO_PILOT_20261008_VAL_A:single_row_transient:011",
}
RUNTIME_IDS = {
    "SETI_RADIO_PILOT_20261008_DEV_RUNTIME:single_row_transient:000",
    "SETI_RADIO_PILOT_20261008_DEV_RUNTIME:single_row_transient:001",
}
RUNTIME_CASE_BANK_SHA256 = "2bef79ec3c17568243672c1ec65c9ca2baeb8066dcc4ab6842039f6d4f2a94d1"


def check_panel_metadata(cases: list[dict], outcomes: list[dict], panel: str) -> tuple[set, set]:
    if (len(cases) != 142 or len(outcomes) != 142
            or any(c["panel"] != panel or f"_{panel}:" not in c["case_id"] for c in cases)
            or len({c["case_id"] for c in cases}) != 142
            or len({c["seed_sha256"] for c in cases}) != 142
            or any(hashlib.sha256(c["case_id"].encode("ascii")).hexdigest() != c["seed_sha256"] for c in cases)
            or any(o.get("panel") != panel for o in outcomes)
            or len({o["case_id"] for o in outcomes}) != 142
            or {o["case_id"] for o in outcomes} != {c["case_id"] for c in cases}):
        raise ValueError(f"All 142 distinct frozen {panel} identities/outcomes required")
    return {c["case_id"] for c in cases}, {c["seed_sha256"] for c in cases}


def check_failed_a(summary: dict, cases: list[dict], outcomes: list[dict], summarizer) -> tuple[set, set]:
    identities = check_panel_metadata(cases, outcomes, "VAL_A")
    recomputed = summarizer.summarize(cases, outcomes, "VAL_A")
    if (summary.get("panel") != "VAL_A" or summary.get("scientific_gate") != "FAIL_CLOSED"
            or summary.get("complete") is not False or summary.get("missing_case_ids") != []
            or set(summary.get("failed_case_ids", [])) != FAILED_A_IDS
            or set(summary.get("checks", {})) != CHECKS
            or summary["checks"]["complete_and_integrity"] is not False
            or any(value is not True for key, value in summary["checks"].items() if key != "complete_and_integrity")
            or any(summary.get(key) != value for key, value in recomputed.items())):
        raise ValueError("Original closed A failure and all its historical checks must remain intact")
    failed = [o for o in outcomes if o["case_id"] in FAILED_A_IDS]
    if (len(failed) != 2 or any(o.get("data_integrity_ok") is not False
            or o.get("family") != "single_row_transient"
            or (o.get("failure") or {}).get("type") != "TimeoutError" for o in failed)):
        raise ValueError("The operational correction applies only to A's two closed diagnostic timeouts")
    return identities


def check_correction_proof(proof: dict, hashes: dict, validation_identities: tuple[set, set],
                           failed_a_identities: tuple[set, set]) -> None:
    if (proof.get("status") != "PASS_OPERATIONAL_DEVELOPMENT_ONLY"
            or proof.get("panel") != "DEV_RUNTIME" or proof.get("complete") is not True
            or proof.get("case_count_expected") != 2 or proof.get("case_count_observed") != 2
            or proof.get("scientific_files_unchanged") is not True
            or proof.get("failed_validation_a_summary_sha256") != hashes["failed_validation_a_summary"]
            or proof.get("failed_validation_a_outcomes_sha256") != hashes["failed_validation_a_outcomes"]
            or proof.get("case_bank_sha256") != RUNTIME_CASE_BANK_SHA256
            or len(proof.get("case_ids", [])) != 2 or set(proof["case_ids"]) != RUNTIME_IDS):
        raise ValueError("Exactly two completed independent DEV runtime correction proofs bound to closed A required")
    for key in ("detector", "dev_helpers", "contract"):
        if proof.get("scientific_sha256", {}).get(key) != FROZEN[key]:
            raise ValueError("Operational DEV proof changed a frozen scientific/shared input")
    records = proof.get("case_results", [])
    if len(records) != 2 or {r.get("case_id") for r in records} != RUNTIME_IDS:
        raise ValueError("Both exact successful DEV runtime committed records required")
    for record in records:
        if (record.get("panel") != "DEV_RUNTIME" or record.get("status") != "COMPLETED_CASE_ONLY"
                or record.get("caps_passed") is not True or record.get("no_retry_or_redraw") is not True
                or not SHA256_RE.fullmatch(record.get("artifact_manifest_SHA256", ""))):
            raise ValueError("DEV runtime record lacks successful committed artifacts/resources")
    runtime_seeds = {hashlib.sha256(identity.encode("ascii")).hexdigest() for identity in RUNTIME_IDS}
    if (validation_identities[0] & failed_a_identities[0]
            or validation_identities[1] & failed_a_identities[1]
            or RUNTIME_IDS & (validation_identities[0] | failed_a_identities[0])
            or runtime_seeds & (validation_identities[1] | failed_a_identities[1])):
        raise ValueError("Fresh B, historical A and operational DEV proof identities/seeds must be disjoint")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for piece in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(piece)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text())


def write_json(path: Path, value) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def cpu_seconds() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return float(usage.ru_utime + usage.ru_stime)


def snapshot() -> dict:
    return {"wall_s": time.monotonic() - PROCESS_STARTED,
            "cpu_s": cpu_seconds(),
            "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)}


def deadline(_signum, _frame):
    raise TimeoutError("Admitted whole-job wall/CPU watchdog reached")


def load_module(path: Path, name: str):
    if name in sys.modules:
        raise ValueError(f"Unexpected previously imported module {name}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot import pinned module {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def check_source_geometry(source: dict, contract: dict) -> None:
    geometry = contract["geometry"]
    band = source["band"]
    cadence = source["cadence_completeness"]
    if (source.get("status") != "METADATA_QUALIFIED_FOR_BOUNDED_PROSPECTIVE_ACQUISITION"
            or source.get("cadence_id") != 85030 or source.get("target") != "HD 189733"
            or source.get("spectral_values_read") is not False
            or source.get("spectral_payload_fetched") is not False):
        raise ValueError("Pinned prospectively qualified primary metadata required")
    if (cadence.get("source_count") != 6 or cadence.get("on_count") != 3
            or cadence.get("off_count") != 3 or cadence.get("independent_visit_count") != 1
            or cadence.get("sequence") != ["ON", "OFF"] * 3):
        raise ValueError("Exactly 3ON/3OFF in one historical visit required")
    if (band["reference_channel_interval_half_open"] != [159905792, 159909888]
            or band["prospective_science_decode_interval_half_open"] != [159903921, 159911759]
            or band["reference_channel_interval_half_open"] != geometry["reference_source_channel_interval"]
            or band["prospective_science_decode_interval_half_open"] != geometry["loaded_source_channel_interval"]
            or band.get("reference_channel_count") != 4096
            or band.get("all_scans_share_exact_channel_grid") is not True):
        raise ValueError("Source/native loaded and reference channel intervals differ")
    sources = source["sources"]
    headers = geometry["scan_metadata"]
    if len(sources) != 6 or len(headers) != 6:
        raise ValueError("Complete six-scan source/contract required")
    for item, header in zip(sources, headers):
        current = item["current_header"]
        attr = current["data_attributes"]
        if (item["label"] != header["scan_id"] or item["role"] != header["role"]
                or current["dataset_shape"] != [16, 1, 264503296]
                or item["dtype_exact"] != "<f4" or header["nrows"] != 16):
            raise ValueError("Source identity/role/complete native row geometry differs")
        for expected, actual in ((header["tstart_mjd"], attr["tstart"]),
                                 (header["tsamp_s"], attr["tsamp"]),
                                 (header["fch1_hz"], attr["fch1"] * 1e6),
                                 (header["df_hz"], attr["foff"] * 1e6)):
            if expected != actual or not math.isfinite(float(actual)):
                raise ValueError("Absolute source fch1/df/time metadata differs from contract")


def check_reader(reader: dict, source: dict, hashes: dict, parent: Path) -> list[dict]:
    if (reader.get("status") != "PASS_BOUNDED_PILOT_VALUES_READ_NO_SEARCH"
            or reader.get("scientific_search_run") is not False
            or reader.get("source_manifest_sha256") != hashes["source_manifest"]
            or reader.get("validation_summary_sha256") != hashes["validation_summary"]
            or reader.get("loaded_source_channel_interval") != [159903921, 159911759]
            or reader.get("spectral_payload_bytes") != 305133821
            or reader.get("selected_application_array_bytes") != 6 * 16 * 7838 * 4):
        raise ValueError("Complete bounded reader result bound to this source and VAL_B required")
    decoded = reader["decoded_files"]
    if len(decoded) != 6 or [d["scan_id"] for d in decoded] != [s["label"] for s in source["sources"]]:
        raise ValueError("Exactly six ordered native reader arrays required")
    for record in decoded:
        if (record["path"] != record["scan_id"] + ".selected.npy"
                or record["shape"] != [16, 7838] or record["dtype"] != "<f4"
                or record["source_channel0"] != 159903921
                or not SHA256_RE.fullmatch(record["decoded_array_sha256"])):
            raise ValueError("Reader array declaration lacks the complete native geometry/hash")
        path = parent / record["path"]
        if path.is_symlink() or path.resolve().parent != parent.resolve() or not path.is_file():
            raise ValueError("Selected arrays must be regular sibling reader outputs")
    requests = reader["value_read_requests"]
    expected = [(s, c) for s in source["sources"] for c in s["chunks"]]
    if len(requests) != 96 or len(expected) != 96:
        raise ValueError("Complete exact 96 source requests required")
    for request, (item, chunk) in zip(requests, expected):
        if (request.get("status") != "EXACT_SOURCE_RANGE_RECEIVED"
                or request["scan_id"] != item["label"] or request["time_row"] != chunk["time_row"]
                or request["request_range"] != chunk["byte_range"]
                or request["body_bytes_received"] != chunk["stored_size"]
                or request["expected_etag"] != item["etag"]
                or not SHA256_RE.fullmatch(request["raw_sha256"])
                or request.get("compact_raw_roundtrip_sha256") != request["raw_sha256"]):
            raise ValueError("Reader source-range/compact-roundtrip receipt differs")
    return decoded


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("admission", "source-manifest", "reader-result", "validation-summary",
                "validation-outcomes", "correction-proof", "failed-validation-a-summary",
                "failed-validation-a-outcomes", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "linux":
        raise ValueError("Linux whole-job RSS/CPU accounting required")
    # Hard maxima cover admission parsing, hashing and imports as well as search.
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGPROF, deadline)
    signal.setitimer(signal.ITIMER_REAL, max(1.0, 1800 - (time.monotonic() - PROCESS_STARTED) - 10))
    signal.setitimer(signal.ITIMER_PROF, max(1.0, 12 * 3600 - cpu_seconds() - 5))
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    admission = read_json(args.admission)
    if (admission.get("status") != "ADMITTED_PRIMARY_PILOT_ONLY"
            or admission.get("pilot_id") != PILOT_ID
            or not re.fullmatch(r"[0-9a-f]{40}", admission.get("public_commit_sha", ""))
            or admission.get("fresh_validation_panel") != "VAL_B"
            or admission.get("fresh_validation_case_count") != 142
            or admission.get("operational_correction_count") != 1):
        raise ValueError("Published primary-only admission after complete fresh VAL_B required")
    budget = admission["budget"]
    if any(not math.isfinite(float(budget[key])) for key in
           ("max_wall_seconds_per_job", "max_rss_bytes", "remaining_cpu_seconds", "exclusive_cpu_allocation_seconds")):
        raise ValueError("Finite explicitly allocated resource budget required")
    max_wall = min(1800.0, float(budget["max_wall_seconds_per_job"]))
    max_rss = min(4 * 1024**3, int(budget["max_rss_bytes"]))
    max_cpu = min(12 * 3600.0, float(budget["remaining_cpu_seconds"]),
                  float(budget["exclusive_cpu_allocation_seconds"]))
    if min(max_wall, max_cpu) <= 10 or max_rss <= 0:
        raise ValueError("Positive bounded root CPU allocation and resource margin required")
    signal.setitimer(signal.ITIMER_REAL, max(1.0, max_wall - (time.monotonic() - PROCESS_STARTED) - 10))
    signal.setitimer(signal.ITIMER_PROF, max(1.0, max_cpu - cpu_seconds() - 5))
    resource.setrlimit(resource.RLIMIT_AS, (max_rss, max_rss))
    paths = {"runner": Path(__file__).resolve(), "waterfall": Path(__file__).with_name("waterfall.py"),
             "detector": ROOT / "pilot_engine_20261008/detector.py",
             "dev_helpers": ROOT / "pilot_engine_20261008/run_dev.py",
             "contract": ROOT / "pilot_controls_20261008/control_contract.json",
             "value_reader": ROOT / "pilot_reader_20261008/value_reader.py",
             "validation_cases": ROOT / "pilot_controls_20261008/validation_b_cases.json",
             "failed_validation_a_cases": ROOT / "pilot_controls_20261008/validation_a_cases.json",
             "summarizer": ROOT / "pilot_controls_20261008/summarize.py",
             "source_manifest": args.source_manifest, "reader_result": args.reader_result,
             "validation_summary": args.validation_summary, "validation_outcomes": args.validation_outcomes,
             "correction_proof": args.correction_proof,
             "failed_validation_a_summary": args.failed_validation_a_summary,
             "failed_validation_a_outcomes": args.failed_validation_a_outcomes}
    observed = {key: digest(path) for key, path in paths.items()}
    for key, value in observed.items():
        if admission["sha256"].get(key) != value or (key in FROZEN and FROZEN[key] != value):
            raise ValueError(f"Published/frozen {key} SHA256 differs; no arrays loaded")
    validation = read_json(args.validation_summary)
    if (validation.get("panel") != "VAL_B" or validation.get("complete") is not True
            or validation.get("case_count_expected") != 142 or validation.get("case_count_observed") != 142
            or validation.get("missing_case_ids") != [] or validation.get("failed_case_ids") != []
            or validation.get("scientific_gate") != "PASS_EXPLORATORY_SCOPE_ONLY"
            or set(validation.get("checks", {})) != CHECKS
            or any(value is not True for value in validation["checks"].values())):
        raise ValueError("Full fresh 142-case VAL_B PASS gate required before any np.load")
    cases = read_json(paths["validation_cases"])
    outcomes = read_json(args.validation_outcomes)
    validation_identities = check_panel_metadata(cases, outcomes, "VAL_B")
    summarizer = load_module(paths["summarizer"], "pilot_metadata_summarizer")
    recomputed = summarizer.summarize(cases, outcomes, "VAL_B")
    if any(validation.get(key) != value for key, value in recomputed.items()):
        raise ValueError("Saved full VAL_B summary differs from complete pinned outcomes")
    failed_a_summary = read_json(args.failed_validation_a_summary)
    failed_a_outcomes = read_json(args.failed_validation_a_outcomes)
    failed_a_cases = read_json(paths["failed_validation_a_cases"])
    failed_a_identities = check_failed_a(failed_a_summary, failed_a_cases, failed_a_outcomes, summarizer)
    correction_proof = read_json(args.correction_proof)
    check_correction_proof(correction_proof, observed, validation_identities, failed_a_identities)
    contract = read_json(paths["contract"])
    source = read_json(args.source_manifest)
    check_source_geometry(source, contract)
    reader = read_json(args.reader_result)
    decoded = check_reader(reader, source, observed, args.reader_result.resolve().parent)
    if set(admission["selected_array_file_sha256"]) != {d["scan_id"] for d in decoded}:
        raise ValueError("Published file SHA256 for all six selected arrays required")
    array_paths = [args.reader_result.resolve().parent / d["path"] for d in decoded]
    array_file_hashes = {d["scan_id"]: digest(p) for d, p in zip(decoded, array_paths)}
    if array_file_hashes != admission["selected_array_file_sha256"]:
        raise ValueError("Published selected-array file SHA256 differs before np.load")
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError("Existing output refused; one primary pilot invocation only")
    if str(args.output.resolve()) != admission["output_directory"]:
        raise ValueError("Output directory differs from admitted invocation")
    claim_path = Path(admission["canonical_claim_path"])
    if not claim_path.is_absolute() or claim_path.name != PILOT_ID + ".json":
        raise ValueError("One canonical named primary pilot claim required")
    measured = snapshot()
    if measured["wall_s"] >= max_wall - 10 or measured["cpu_s"] >= max_cpu - 5 or measured["peak_rss_bytes"] > max_rss:
        raise ValueError("No admitted resource margin before first array load")
    claim_path.parent.mkdir(parents=True, exist_ok=True)
    claim = {"pilot_id": PILOT_ID, "status": "CLAIMED_BEFORE_FIRST_ARRAY_LOAD",
             "first_claim_utc": datetime.now(timezone.utc).isoformat(),
             "admission_sha256": digest(args.admission), "public_commit_sha": admission["public_commit_sha"],
             "output_directory": str(args.output.resolve())}
    with claim_path.open("x") as handle:
        json.dump(claim, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "admission.json", {"admission": admission, "observed_sha256": observed,
               "selected_array_file_sha256": array_file_hashes, "validation_gate": recomputed,
               "closed_failed_validation_a": failed_a_summary, "operational_correction_proof": correction_proof,
               "source_geometry_verified": True, "synthetic": False, "independent_visit_count": 1})
    failed = False
    outcome = {"pilot_id": PILOT_ID, "status": "FAILED_CLOSED", "failure": None,
               "native_source_arrays_retained": True, "masked_or_omitted_samples": 0}
    try:
        # Operational import controls prevent BLAS thread reservations exceeding
        # the same complete-job allocation; detector scientific bytes stay fixed.
        for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            os.environ[variable] = "1"
        import numpy as np
        import scipy
        if np.__version__ != "2.3.5" or scipy.__version__ != "1.17.0":
            raise ValueError("Frozen NumPy 2.3.5 / SciPy 1.17.0 environment required")
        detector = load_module(paths["detector"], "detector")
        helpers = load_module(paths["dev_helpers"], "pilot_frozen_dev_helpers")
        arrays = []
        for record, path in zip(decoded, array_paths):
            power = np.load(path, allow_pickle=False)
            if (power.shape != (16, 7838) or power.dtype != np.dtype("<f4")
                    or not power.flags.c_contiguous or not np.isfinite(power).all()
                    or np.any(power < 0)
                    or hashlib.sha256(power.tobytes(order="C")).hexdigest() != record["decoded_array_sha256"]):
                raise ValueError("Actual native selected array geometry/values/hash differ from reader")
            power.flags.writeable = False
            arrays.append(power)
        write_json(args.output / "input_array_provenance.json", {"reader_decoded_files": decoded,
                   "selected_array_file_sha256": array_file_hashes, "native_shape": [16, 7838],
                   "absolute_source_channel0": 159903921, "masks": None})
        scans, frequencies = detector.control_inputs(arrays, contract)
        if any(s.valid_mask is not None for s in scans):
            raise ValueError("No masks permitted in the frozen primary pilot")
        geometry = detector.cadence_geometry(scans, detector.Config())
        if len(frequencies) != 4096 or len(geometry["drift_grid_hz_s"]) != 5415:
            raise ValueError("All 4096 reference carriers and 5415 frozen drifts required")
        # Fixed, prospectively declared display is retained before the first
        # search/judgment. Its native arrays and display policy stay unchanged.
        plotter = load_module(paths["waterfall"], "pilot_fixed_waterfall")
        display = plotter.render_waterfall(arrays, contract, args.output / "six_scan_waterfall.png")
        write_json(args.output / "waterfall_metadata.json", display)
        if snapshot()["peak_rss_bytes"] > max_rss:
            raise MemoryError("Admitted RSS exceeded before scientific search")
        result = detector.search_cadence(scans, frequencies, detector.Config())
        if len(result["scan_maps"]) != 6 or result["geometry"]["OFF_reference_halo_channels"] != 250:
            raise ValueError("Complete frozen six scan maps/OFF reference halo required")
        for mapping, header in zip(result["scan_maps"], contract["geometry"]["scan_metadata"]):
            expected_carriers = 4096 if header["role"] == "on" else 4596
            if (mapping["scan_id"] != header["scan_id"] or mapping["role"] != header["role"].upper()
                    or len(mapping["maximum_robust_box_track_score"]) != expected_carriers
                    or mapping["total_hypothesis_count_per_carrier"] != 5415 * 4
                    or not np.all(mapping["valid_hypothesis_count"] == 5415 * 4)):
                raise ValueError("A scan map omits a frozen unmasked carrier/hypothesis")
        if any(len(hit["OFF_comparisons"]) != 3 for hit in result["all_ON_threshold_carriers"]):
            raise ValueError("Every raw ON threshold hit requires all three OFF dispositions")
        helpers.save_result(args.output, result)
        helpers.write_json(args.output / "all_OFF_dispositions.json", [
            {"ON_scan_id": hit["scan_id"], "ON_reference_carrier_index": hit["reference_carrier_index"],
             "ON_disposition": hit["disposition"], "OFF_comparison": comparison}
            for hit in result["all_ON_threshold_carriers"] for comparison in hit["OFF_comparisons"]])
        outcome.update(status="COMPLETED_EXPLORATORY_PRIMARY_PILOT",
                       ON_threshold_carrier_count=len(result["all_ON_threshold_carriers"]),
                       surviving_ON_threshold_carrier_count=result["surviving_ON_threshold_carrier_count"],
                       scan_map_count=6, reference_carrier_count=4096, drift_count=5415,
                       numpy=np.__version__, scipy=scipy.__version__, python=sys.version,
                       interpretation="Exploratory only; one historical visit; no calibrated sky significance")
    except BaseException as error:
        failed = True
        outcome["failure"] = {"type": type(error).__name__, "message": str(error)}
        (args.output / "failure_traceback.txt").write_text(traceback.format_exc())
    finally:
        # Finalization stays guarded: a watchdog firing during artifact hashes
        # or receipts must replace any provisional completion with failure.
        caps_passed = False
        try:
            manifest = {p.name: {"SHA256": digest(p), "size_bytes": p.stat().st_size}
                        for p in sorted(args.output.iterdir()) if p.is_file()
                        and p.name not in {"artifact_manifest.json", "resource_receipt.json", "outcome.json"}}
            measured = snapshot()
            caps_passed = measured["wall_s"] <= max_wall and measured["cpu_s"] <= max_cpu and measured["peak_rss_bytes"] <= max_rss
            if not caps_passed:
                raise RuntimeError("Whole-job artifact work exceeded admitted resource cap")
            if failed:
                outcome["status"] = "FAILED_CLOSED"
            outcome.update(measured)
            write_json(args.output / "outcome.json", outcome)
            manifest["outcome.json"] = {"SHA256": digest(args.output / "outcome.json"),
                                        "size_bytes": (args.output / "outcome.json").stat().st_size}
            write_json(args.output / "artifact_manifest.json", manifest)
            measured = snapshot()
            caps_passed = measured["wall_s"] <= max_wall and measured["cpu_s"] <= max_cpu and measured["peak_rss_bytes"] <= max_rss
            if not caps_passed:
                raise RuntimeError("Whole-job manifest work exceeded admitted resource cap")
            claim.update(status=outcome["status"], whole_job_cpu_s=measured["cpu_s"], whole_job_wall_s=measured["wall_s"])
            write_json(claim_path, claim)
            measured = snapshot()
            caps_passed = measured["wall_s"] <= max_wall and measured["cpu_s"] <= max_cpu and measured["peak_rss_bytes"] <= max_rss
            if not caps_passed:
                raise RuntimeError("Whole-job claim finalization exceeded admitted resource cap")
            write_json(args.output / "resource_receipt.json", {**measured, "caps_passed": caps_passed,
                       "accounting": "Whole process: startup, admission, hashes, imports, six loads, full search, plot, artifacts",
                       "caps": {"wall_s": max_wall, "cpu_s_available": max_cpu, "peak_rss_bytes": max_rss},
                       "RLIMIT_AS_bytes": max_rss, "signal_watchdogs": ["ITIMER_REAL", "ITIMER_PROF"],
                       "status": outcome["status"]})
        except BaseException as finalization_error:
            # A triggered deadline already stops work. Disarm both timers only
            # for the reserved failure flush; its CPU/wall/RSS are still measured.
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.setitimer(signal.ITIMER_PROF, 0)
            failed = True
            outcome.update(status="FAILED_CLOSED", finalization_failure={
                "type": type(finalization_error).__name__, "message": str(finalization_error)})
            measured = snapshot()
            outcome.update(measured)
            write_json(args.output / "outcome.json", outcome)
            claim.update(status="FAILED_CLOSED", whole_job_cpu_s=measured["cpu_s"], whole_job_wall_s=measured["wall_s"])
            write_json(claim_path, claim)
            failure_manifest = {p.name: {"SHA256": digest(p), "size_bytes": p.stat().st_size}
                                for p in sorted(args.output.iterdir()) if p.is_file()
                                and p.name not in {"artifact_manifest.json", "resource_receipt.json"}}
            write_json(args.output / "artifact_manifest.json", failure_manifest)
            measured = snapshot()
            caps_passed = measured["wall_s"] <= max_wall and measured["cpu_s"] <= max_cpu and measured["peak_rss_bytes"] <= max_rss
            write_json(args.output / "resource_receipt.json", {**measured, "caps_passed": caps_passed,
                       "caps": {"wall_s": max_wall, "cpu_s_available": max_cpu, "peak_rss_bytes": max_rss},
                       "status": "FAILED_CLOSED", "finalization_failure": outcome["finalization_failure"],
                       "failure_flush_included_in_measurement": True,
                       "RLIMIT_AS_bytes": max_rss, "signal_watchdogs": ["ITIMER_REAL", "ITIMER_PROF"]})
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.setitimer(signal.ITIMER_PROF, 0)
    print(json.dumps(outcome, sort_keys=True), flush=True)
    return 1 if failed or not caps_passed else 0


if __name__ == "__main__":
    raise SystemExit(main())
