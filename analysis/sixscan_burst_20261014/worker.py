#!/usr/bin/env python3
"""Once-only, admitted single-case six-scan burst worker.

Importing this module reads no inputs, imports no numerical package and creates
no random values. All code/definition pins are authenticated before numerical
imports or generation. The parent coordinator alone admits and launches cases.
"""
from __future__ import annotations

import argparse
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
import time
import traceback

STARTED = time.monotonic()
STAGE = Path(__file__).resolve().parent
RAW_INPUT_ROOT = (STAGE.parent / "checkpoints/SETI_NATIVE_SPOR_2026-10-14/SETI_NATIVE_SPOR_2026-10-14").resolve()
CPU_CAP_S = 600
WALL_CAP_S = 1800
MEMORY_CAP_BYTES = 1024 ** 3
ADMISSION_STATUS = "ADMITTED_AFTER_EXACT_PUBLIC_FREEZE_READBACK"


def sha256_file(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def durable_json(path, value, *, exclusive=False):
    path = Path(path)
    target = path if exclusive else path.with_name(path.name + ".tmp")
    with target.open("x" if exclusive else "w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    if not exclusive:
        target.replace(path)
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def set_caps():
    """Apply whole-process limits before importing NumPy, SciPy or generator."""
    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                 "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ[name] = "1"
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP_BYTES, MEMORY_CAP_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP_S, CPU_CAP_S))

    def timeout(signum, frame):
        raise TimeoutError(f"Whole-case resource watchdog (signal {signum}); no retry/redraw")

    signal.signal(signal.SIGALRM, timeout)
    signal.signal(signal.SIGPROF, timeout)
    signal.setitimer(signal.ITIMER_REAL, max(.01, WALL_CAP_S - (time.monotonic() - STARTED)))
    used = resource.getrusage(resource.RUSAGE_SELF)
    # Give exception/receipt handling a small reserve inside the hard CPU cap.
    signal.setitimer(signal.ITIMER_PROF, max(.01, CPU_CAP_S - 1 - used.ru_utime - used.ru_stime))


def resource_snapshot():
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {"wall_s": time.monotonic() - STARTED,
            "cpu_s": usage.ru_utime + usage.ru_stime,
            "peak_rss_bytes": int(usage.ru_maxrss) * 1024,
            "caps": {"cpu_s": CPU_CAP_S, "wall_s": WALL_CAP_S,
                     "address_space_bytes": MEMORY_CAP_BYTES}}


def authenticate_admission():
    """Hash pinned bytes only; never load raw arrays or RNG during admission."""
    go_path, scope_path = STAGE / "GO.json", STAGE / "SCOPE.json"
    go = json.loads(go_path.read_text(encoding="utf-8"))
    if go.get("status") != ADMISSION_STATUS:
        raise ValueError("Exact-public-freeze admission required before generation")
    scope_sha = sha256_file(scope_path)
    if go.get("scope_sha256") != scope_sha:
        raise ValueError("Admission does not authenticate the current SCOPE.json bytes")
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    resources = scope.get("resources", {})
    if resources.get("per_case_CPU_s_cap") != CPU_CAP_S:
        raise ValueError("Public per-case CPU cap differs from the worker hard cap")
    pins = scope.get("code_pins")
    if not isinstance(pins, list) or not pins:
        raise ValueError("Complete source/definition code pins required")
    observed = {}
    for pin in pins:
        if not isinstance(pin, dict) or set(("path", "sha256", "bytes")) - pin.keys():
            raise ValueError("Malformed source/definition pin")
        relative = Path(pin["path"])
        path = (STAGE / relative).resolve()
        if relative.is_absolute() or ".." in relative.parts or path == STAGE or STAGE not in path.parents:
            raise ValueError("Code pin must resolve inside the frozen stage")
        name = relative.as_posix()
        if name in observed:
            raise ValueError("Duplicate source/definition pin: " + name)
        digest, size = sha256_file(path), path.stat().st_size
        if digest != pin["sha256"] or size != pin["bytes"]:
            raise ValueError("Frozen source/definition pin differs: " + name)
        observed[name] = {"sha256": digest, "bytes": size}
    required = {"worker.py", "detector.py", "generator.py", "case_bank.json", "contract.json", "real_baselines.json"}
    if required - observed.keys():
        raise ValueError("Unpinned worker prerequisites: " + repr(sorted(required - observed.keys())))
    return go, scope, {"scope_sha256": scope_sha, "GO_sha256": sha256_file(go_path),
                       "observed_code_pins": observed,
                       "checked_before_numerical_imports_RNG_and_raw_reads": True}


def import_frozen(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("Frozen module cannot be imported: " + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Tee:
    """Keep per-case logs while retaining coordinator stdout/stderr capture."""
    def __init__(self, parent, path):
        self.parent = parent
        self.stream = Path(path).open("x", encoding="utf-8", buffering=1)

    def write(self, text):
        self.parent.write(text)
        return self.stream.write(text)

    def flush(self):
        self.parent.flush()
        self.stream.flush()

    def isatty(self):
        return False

    def close(self):
        self.flush()
        os.fsync(self.stream.fileno())
        self.stream.close()


def array_hash(array):
    # The declared authentication representation is native little-endian,
    # float32, C-order power bytes; validity is checked separately.
    return hashlib.sha256(array.tobytes(order="C")).hexdigest()


def authenticate_arrays(arrays, metadata, geometry, np):
    if len(arrays) != 6 or len(metadata) != 6:
        raise ValueError("Exactly six generated arrays and scan headers required")
    first, stop = geometry["loaded_source_channel_interval"]
    width = int(stop) - int(first)
    hashes = {}
    if len({scan["scan_id"] for scan in metadata}) != 6:
        raise ValueError("Six distinct scan IDs required")
    for array, scan in zip(arrays, metadata):
        if not isinstance(array, np.ndarray) or array.dtype != np.dtype("float32"):
            raise ValueError("Generator must return the frozen six float32 arrays")
        if not array.flags.c_contiguous or array.shape != (scan["nrows"], width):
            raise ValueError("Generated float32 geometry/order differs: " + scan["scan_id"])
        if not np.isfinite(array).all() or (array < 0).any():
            raise ValueError("Nonfinite/negative generated power; no clipping or redraw")
        hashes[scan["scan_id"]] = {"shape": list(array.shape), "dtype": str(array.dtype),
                                   "C_order_bytes_sha256": array_hash(array), "nbytes": int(array.nbytes)}
    return hashes


def json_and_array_store(value, np):
    """Move every numerical array (all maps/inventories included) into NPZ."""
    arrays, descriptors = {}, {}

    def visit(item, path):
        if isinstance(item, np.ndarray):
            stem = re.sub(r"[^A-Za-z0-9_]", "_", "__".join(path)) or "root"
            key = stem
            suffix = 1
            while key in arrays:
                key = stem + "__" + str(suffix)
                suffix += 1
            if item.dtype.hasobject:
                raise ValueError("Object arrays cannot enter durable maps.npz: " + repr(path))
            arrays[key] = item
            descriptor = {"npz_key": key, "shape": list(item.shape), "dtype": str(item.dtype),
                          "C_order_bytes_sha256": array_hash(item), "nbytes": int(item.nbytes),
                          "original_field_path": list(path)}
            descriptors[key] = descriptor
            return {"array_descriptor": descriptor}
        if isinstance(item, np.generic):
            return visit(item.item(), path)
        if isinstance(item, dict):
            return {str(key): visit(child, path + (str(key),)) for key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [visit(child, path + (str(index),)) for index, child in enumerate(item)]
        if isinstance(item, float) and not math.isfinite(item):
            return {"nonfinite_float": "nan" if math.isnan(item) else "+inf" if item > 0 else "-inf"}
        if item is None or isinstance(item, (str, bool, int, float)):
            return item
        raise TypeError("Unexpected result field type at " + repr(path) + ": " + type(item).__name__)

    return visit(value, ()), arrays, descriptors


def save_npz(path, arrays, np):
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("xb") as stream:
        np.savez_compressed(stream, **arrays)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    # Verify every durable input/map array, without creating further case draws.
    with np.load(path, allow_pickle=False) as restored:
        if set(restored.files) != set(arrays):
            raise ValueError("Durable NPZ inventory differs")
        for key, original in arrays.items():
            copy = restored[key]
            if (copy.shape != original.shape or copy.dtype != original.dtype or
                    array_hash(copy) != array_hash(original)):
                raise ValueError("Durable NPZ bytes differ: " + key)


def scan_inputs(arrays, metadata, geometry, detector, np):
    loaded_first, loaded_stop = geometry["loaded_source_channel_interval"]
    core_first, core_stop = geometry["reference_source_channel_interval"]
    if int(core_stop) - int(core_first) != 4096 or not (loaded_first <= core_first < core_stop <= loaded_stop):
        raise ValueError("Complete declared 4096-carrier core and loaded guards required")
    roles = [str(scan["role"]).lower() for scan in metadata]
    if roles != ["on", "off", "on", "off", "on", "off"]:
        raise ValueError("Frozen chronological ON/OFF cadence differs")
    return [detector.Scan(scan_id=scan["scan_id"], role=scan["role"], power=array,
                          tstart_mjd=scan["tstart_mjd"], tsamp_s=scan["tsamp_s"],
                          fch1_hz=scan["fch1_hz"], df_hz=scan["df_hz"],
                          source_channel0=int(loaded_first),
                          normalization_source_channels=np.arange(core_first, core_stop, dtype=np.int64),
                          valid_mask=None, expected_nrows=int(scan["nrows"]))
            for array, scan in zip(arrays, metadata)], int(core_first)


def canonical_truth(truth):
    """Attach the exact frozen endpoint-localization fields, without refitting."""
    truth = dict(truth)
    active = truth["active_ON_scan_ids"]
    if active:
        truth["reference_source_channel_at_tref"] = truth["reference_source_channel"]
        truth["active_window_start_by_scan"] = {
            scan_id: int(truth["flux_by_scan"][scan_id]["truth_window_source_rows"][0]) for scan_id in active}
        truth["oracle_width_by_scan"] = {
            scan_id: int(truth["flux_by_scan"][scan_id]["injection_oracle_width_channels"]) for scan_id in active}
    return truth


def authenticate_exposed_prerequisites(output_root):
    receipts = {}
    for phase in ("PRIMARY_CALIBRATION", "PRIMARY_VALIDATION", "QA"):
        path = STAGE / (phase + "_RUN_STATE.json")
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("status") != "COMPLETE" or state.get("running") or state.get("unsubmitted"):
            raise ValueError("Exposed re-search requires the full primary+QA phase closure: " + phase)
        receipts[path.name] = sha256_file(path)
    summary_path = Path(output_root).resolve() / "SUMMARY.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("integrity_gate") is not True:
        raise ValueError("All 205 primary+QA integrity gate must close before exposed re-search")
    receipts["SUMMARY.json"] = sha256_file(summary_path)
    return {"primary_and_QA_complete": True, "summary_integrity_gate": True,
            "closure_receipt_sha256": receipts,
            "scientific_recovery_gate_is_not_required_for_descriptive_exposed_research": True}


def verify_result_inventory(result, metadata, core_first, np):
    """Require complete persisted payloads, without a second detector traversal."""
    required = {"geometry", "alias_geometry", "scan_maps", "OFF_threshold_inventories",
                "OFF_inventory_certificates", "all_ON_threshold_hypotheses",
                "maximum_pre_OFF_ON_score", "surviving_ON_threshold_hypothesis_count"}
    if required - result.keys():
        raise ValueError("Incomplete detector result fields")
    maps = result["scan_maps"]
    if len(maps) != 6 or [mapping["scan_id"] for mapping in maps] != [scan["scan_id"] for scan in metadata]:
        raise ValueError("Complete six-scan map inventory required")
    geometry = result["geometry"]
    for scan, mapping in zip(metadata, maps):
        interval = [core_first, core_first + 4096] if scan["role"] == "ON" else geometry["OFF_reference_source_channel_interval_half_open"]
        references = np.arange(*interval, dtype=np.int64)
        if (mapping["role"] != scan["role"] or not np.array_equal(mapping["reference_source_channels"], references) or
                mapping["scores"].shape != (len(references), 5) or mapping["native4_centers"].shape != (len(references), 5, 4) or
                "normalization" not in mapping):
            raise ValueError("Full carrier/top5/normalization map payload differs: " + scan["scan_id"])
    off_ids = {scan["scan_id"] for scan in metadata if scan["role"] == "OFF"}
    if set(result["OFF_threshold_inventories"]) != off_ids or set(result["OFF_inventory_certificates"]) != off_ids:
        raise ValueError("All three complete OFF inventories/certificates required")
    inventory_fields = {"reference_carrier_index", "reference_source_channel", "width", "window_start",
                        "representative_drift_index", "alias_first_index", "alias_last_index", "score", "native4_centers"}
    for scan_id in off_ids:
        inventory = result["OFF_threshold_inventories"][scan_id]
        certificate = result["OFF_inventory_certificates"][scan_id]
        if (set(inventory) != inventory_fields or certificate.get("complete") is not True or
                certificate.get("score_threshold") != 8 or
                any(len(array) != certificate["inventory_rows"] for array in inventory.values()) or
                not np.all(np.isfinite(inventory["score"]) & (inventory["score"] >= 8))):
            raise ValueError("OFF >=8 inventory is incomplete/invalid: " + scan_id)
    observed_max = float(max(mapping["scores"].max() for mapping in maps if mapping["role"] == "ON"))
    if not math.isfinite(observed_max) or observed_max != result["maximum_pre_OFF_ON_score"]:
        raise ValueError("Global pre-OFF ON maximum differs from the full maps")
    for hit in result["all_ON_threshold_hypotheses"]:
        if hit["ON_score"] < 10 or {receipt["scan_id"] for receipt in hit["OFF_comparisons"]} != off_ids or len(hit["OFF_comparisons"]) != 3:
            raise ValueError("ON threshold hypothesis lacks all three OFF witness receipts")


def read_exposed_arrays(case, metadata, contract_geometry, np):
    """Authenticate all six source files before decoding any exposed raw crop."""
    geometry = dict(contract_geometry)
    geometry["reference_source_channel_interval"] = case["reference_source_channel_interval"]
    geometry["loaded_source_channel_interval"] = case["loaded_source_channel_interval"]
    core_first, core_stop = geometry["reference_source_channel_interval"]
    loaded_first, loaded_stop = geometry["loaded_source_channel_interval"]
    if len(case["scans"]) != 6 or [scan["scan_id"] for scan in case["scans"]] != [scan["scan_id"] for scan in metadata]:
        raise ValueError("Authentic exposed cadence scan inventory differs")
    sources = []
    for scan in case["scans"]:
        pins = {}
        for field in ("raw_crop", "normalization"):
            pin = scan[field]
            relative = Path(pin["path"])
            path = (RAW_INPUT_ROOT / relative).resolve()
            if relative.is_absolute() or ".." in relative.parts or RAW_INPUT_ROOT not in path.parents:
                raise ValueError("Exposed source must stay inside authenticated checkpoint root")
            digest, size = sha256_file(path), path.stat().st_size
            if digest != pin["sha256"] or size != pin["bytes"]:
                raise ValueError("Authentic exposed source pin differs: " + scan["scan_id"] + ":" + field)
            pins[field] = {"path": str(path), "sha256": digest, "bytes": size}
        sources.append({"scan_id": scan["scan_id"], **pins})
    arrays = []
    for source in sources:
        with np.load(source["raw_crop"]["path"], allow_pickle=False) as raw:
            required = {"raw_power", "source_channel0", "normalization_source_channels", "absolute_time_rows"}
            if set(raw.files) != required:
                raise ValueError("Authentic raw crop NPZ fields differ: " + source["scan_id"])
            channel0, normalization, rows = raw["source_channel0"], raw["normalization_source_channels"], raw["absolute_time_rows"]
            if (channel0.shape != () or channel0.dtype != np.dtype("int64") or int(channel0) != loaded_first or
                    normalization.dtype != np.dtype("int64") or
                    not np.array_equal(normalization, np.arange(core_first, core_stop, dtype=np.int64)) or
                    rows.dtype != np.dtype("int64") or not np.array_equal(rows, np.arange(16, dtype=np.int64))):
                raise ValueError("Authentic raw crop channel/row coordinates differ: " + source["scan_id"])
            array = raw["raw_power"]
            if array.dtype != np.dtype("float32") or array.shape != (16, loaded_stop - loaded_first):
                raise ValueError("Authentic raw crop float32 dimensions differ: " + source["scan_id"])
            arrays.append(np.ascontiguousarray(array))
    truth = {"case_id": case["case_id"], "family": case["family"], "synthetic": False,
             "active_ON_scan_ids": [], "source_files": sources, "RNG_instantiated": False,
             "synthetic_injection": False, "fresh_background": False,
             "new_telescope_bytes": 0, "new_observation": False,
             "interpretation": case["interpretation"]}
    return arrays, truth, geometry


def main():
    set_caps()
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--case-index", type=int)
    mode.add_argument("--exposed-index", type=int)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    go, scope, admission = authenticate_admission()
    exposed = args.exposed_index is not None
    index = args.exposed_index if exposed else args.case_index
    bank_path = STAGE / ("real_baselines.json" if exposed else "case_bank.json")
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    cases = bank if isinstance(bank, list) else bank["cases"]
    if index < 0 or index >= len(cases):
        raise ValueError("Case index outside the frozen bank")
    case = cases[index]
    contract = json.loads((STAGE / "contract.json").read_text(encoding="utf-8"))
    if exposed:
        admission["exposed_prerequisites"] = authenticate_exposed_prerequisites(args.output_root)
    identifier = ("R" if exposed else "C") + f"{index:04d}"
    folder = args.output_root.resolve() / ("exposed" if exposed else "cases") / identifier
    if folder.exists():
        raise FileExistsError("Once-only case output already exists; no retry/redraw")
    claims = STAGE / "claims"
    claims.mkdir(parents=True, exist_ok=True)
    claim_path = claims / (identifier + ".json")
    claim = {"case_index": index, "exposed": exposed, "case_id": case["case_id"],
             "status": "CLAIMED_BEFORE_NUMERICAL_IMPORT_RNG_OR_RAW_READ",
             "output_directory": str(folder), "no_retry_or_redraw": True, **admission}
    durable_json(claim_path, claim, exclusive=True)
    folder.mkdir(parents=True, exist_ok=False)
    stdout, stderr = Tee(sys.stdout, folder / "STDOUT.log"), Tee(sys.stderr, folder / "STDERR.log")
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = stdout, stderr
    failed = True
    try:
        durable_json(folder / "admission.json", admission)
        durable_json(folder / "case_definition.json", case)
        # This is the first point at which numerical packages or RNG-bearing
        # modules may be imported; all required pins and the claim exist.
        import numpy as np
        import scipy
        if (np.__version__ != "2.3.5" or scipy.__version__ != "1.17.0" or
                sys.platform != "linux" or sys.byteorder != "little"):
            raise ValueError("Frozen Linux little-endian NumPy/SciPy environment differs")
        detector = import_frozen(STAGE / "detector.py", "sixscan_frozen_detector")
        generator = import_frozen(STAGE / "generator.py", "sixscan_frozen_generator")
        metadata, geometry = contract["geometry"]["scan_metadata"], contract["geometry"]
        if exposed:
            arrays, truth, geometry = read_exposed_arrays(case, metadata, geometry, np)
        else:
            arrays, truth = generator.generate_case(case, contract)
        if isinstance(arrays, dict):
            if set(arrays) != {scan["scan_id"] for scan in metadata}:
                raise ValueError("Generated scan inventory differs from contract")
            arrays = [arrays[scan["scan_id"]] for scan in metadata]
        hashes = authenticate_arrays(arrays, metadata, geometry, np)
        truth = canonical_truth(truth)
        truth["authenticated_input_arrays"] = hashes
        truth["generated_exactly_once"] = not exposed
        durable_json(folder / "truth.json", truth)
        save_npz(folder / "inputs.npz", {scan["scan_id"]: array for scan, array in zip(metadata, arrays)}, np)
        for array in arrays:
            array.flags.writeable = False
        scans, core_first = scan_inputs(arrays, metadata, geometry, detector, np)
        result = detector.search_cadence(scans, core_first, detector.Config())
        verify_result_inventory(result, metadata, core_first, np)
        if authenticate_arrays(arrays, metadata, geometry, np) != hashes:
            raise ValueError("Raw input array bytes changed during the detector")
        result = dict(result)
        result["calibrationglobal_ON_max"] = result["maximum_pre_OFF_ON_score"]
        if truth["active_ON_scan_ids"]:
            result["recovery"] = detector.recovery(result, truth)
        else:
            result["recovery"] = {"recovery_applicable": False, "active_ON_scan_ids": [],
                                  "reason": "No injected primary ON; full candidate census is preserved"}
        result.update(case_index=index, exposed=exposed, case_id=case["case_id"],
                      input_array_hashes=hashes, no_retry_or_redraw=True,
                      generation_call_count=0 if exposed else 1, admission=admission)
        encoded, maps, descriptors = json_and_array_store(result, np)
        if not maps:
            raise ValueError("Detector returned no complete numerical scan maps")
        save_npz(folder / "maps.npz", maps, np)
        encoded["array_store"] = {"file": "maps.npz", "descriptors": descriptors,
                                  "all_array_fields_preserved": True}
        encoded["resource_receipt"] = resource_snapshot()
        receipt = encoded["resource_receipt"]
        if (receipt["cpu_s"] > CPU_CAP_S or receipt["wall_s"] > WALL_CAP_S or
                receipt["peak_rss_bytes"] > MEMORY_CAP_BYTES):
            raise ValueError("Measured whole-case resource limit exceeded")
        encoded["status"] = "COMPLETED_CASE_ONLY"
        encoded["data_integrity_ok"] = True
        durable_json(folder / "output.json", encoded)
        print(json.dumps({"case_index": index, "exposed": exposed, "case_id": case["case_id"],
                          "status": "COMPLETED_CASE_ONLY", "resources": receipt}, sort_keys=True))
        sys.stdout, sys.stderr = old_stdout, old_stderr
        stdout.close()
        stderr.close()
        manifest = {path.name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
                    for path in sorted(folder.iterdir()) if path.is_file()}
        durable_json(folder / "artifact_manifest.json", manifest)
        claim.update(status="COMPLETED_CASE_ONLY", resources=receipt,
                     artifact_manifest_sha256=sha256_file(folder / "artifact_manifest.json"))
        durable_json(claim_path, claim)
        durable_json(folder / "COMMITTED.json", {"status": "COMPLETED_CASE_ONLY",
                     "case_id": case["case_id"], "case_index": index, "exposed": exposed,
                     "artifact_manifest_sha256": claim["artifact_manifest_sha256"],
                     "no_retry_or_redraw": True, "data_integrity_ok": True})
        failed = False
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.setitimer(signal.ITIMER_PROF, 0)
        (folder / "COMMITTED.json").unlink(missing_ok=True)
        receipt = resource_snapshot()
        failure = {"case_index": index, "exposed": exposed, "case_id": case["case_id"],
                   "status": "FAILED_CLOSED_CASE_ONLY", "data_integrity_ok": False,
                   "no_retry_or_redraw": True, "resource_receipt": receipt,
                   "failure": {"type": type(error).__name__, "message": str(error)}}
        try:
            traceback.print_exc()
            durable_json(folder / "output.json", failure)
            claim.update(status="FAILED_CLOSED_CASE_ONLY", failure=failure["failure"], resources=receipt)
            durable_json(claim_path, claim)
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
            if not stdout.stream.closed:
                stdout.close()
            if not stderr.stream.closed:
                stderr.close()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.setitimer(signal.ITIMER_PROF, 0)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
