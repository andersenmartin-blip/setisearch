#!/usr/bin/env python3
"""Run only explicitly admitted, publicly frozen DEV controls, one or a panel.

No RNG/control arrays are created before admission checks. Never runs VAL or
sky-pilot data. The external freeze receipt binds all inputs and this code.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import resource
import signal
import sys
import time
import traceback

PROCESS_STARTED = time.monotonic()

import numpy as np
import scipy
from detector import Config, control_inputs, recovery_matches, search_cadence


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean_json(value):
    if isinstance(value, np.ndarray):
        return clean_json(value.tolist())
    if isinstance(value, np.generic):
        return clean_json(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    return value


def write_json(path: Path, value) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(clean_json(value), indent=2, sort_keys=True,
                                    allow_nan=False) + "\n")
    temporary.replace(path)


def cpu_seconds() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF)
    return float(r.ru_utime + r.ru_stime)


def peak_rss_bytes() -> int:
    # Linux resource.ru_maxrss is KiB; the admitted environment is Linux.
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load frozen module {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def timeout_handler(_signum, _frame):
    raise TimeoutError("Admitted wall/CPU watchdog reached; no retry or redraw")


def snapshot(wall_start: float, cpu_start: float) -> dict:
    return {"wall_s": time.monotonic()-wall_start,
            "cpu_s": cpu_seconds()-cpu_start, "peak_rss_bytes": peak_rss_bytes()}


def save_result(path: Path, result: dict) -> None:
    maps_metadata = []
    for index, m in enumerate(result["scan_maps"]):
        array_fields = {key: value for key, value in m.items() if isinstance(value, np.ndarray)}
        np.savez_compressed(path / f"scan_{index:02d}_full_map.npz", **array_fields)
        metadata = {key: value for key, value in m.items() if key not in array_fields}
        metadata["array_file"] = f"scan_{index:02d}_full_map.npz"
        maps_metadata.append(metadata)
    write_json(path / "scan_map_metadata.json", maps_metadata)
    np.savez_compressed(path / "geometry_arrays.npz",
                        drift_grid_hz_s=result["geometry"]["drift_grid_hz_s"],
                        **{f"scan_{i:02d}_times_from_tref_s": t for i, t in
                           enumerate(result["geometry"]["times_from_tref_s"])})
    geometry = {key: value for key, value in result["geometry"].items()
                if key not in ("drift_grid_hz_s", "times_from_tref_s")}
    write_json(path / "geometry.json", geometry)
    write_json(path / "all_ON_threshold_carriers.json", result["all_ON_threshold_carriers"])
    write_json(path / "detector_summary.json", {
        "score_definition": result["score_definition"],
        "ON_threshold_carrier_count": len(result["all_ON_threshold_carriers"]),
        "surviving_ON_threshold_carrier_count": result["surviving_ON_threshold_carrier_count"],
        "limitations": result["limitations"]})


def main() -> int:
    parser = argparse.ArgumentParser(description="Run admitted full-family DEV cases only")
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--generator", type=Path, required=True)
    parser.add_argument("--summarizer", type=Path, required=True)
    parser.add_argument("--freeze-receipt", type=Path, required=True)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--case", help="One exact frozen DEV case identity")
    choice.add_argument("--all", action="store_true", help="All admitted DEV cases, in frozen order")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    freeze = json.loads(args.freeze_receipt.read_text())
    if (freeze.get("status") != "ADMITTED_DEV_ONLY" or
            not re.fullmatch(r"[0-9a-f]{40}", freeze.get("public_commit_sha", ""))):
        raise ValueError("Immutable public DEV admission receipt required")
    bound_paths = {"detector": Path(__file__).with_name("detector.py"),
                   "runner": Path(__file__), "generator": args.generator,
                   "contract": args.contract, "cases": args.cases,
                   "summarizer": args.summarizer}
    observed_hashes = {key: digest(path) for key, path in bound_paths.items()}
    for key, value in observed_hashes.items():
        if freeze["sha256"].get(key) != value:
            raise ValueError(f"Frozen {key} SHA256 differs; no controls generated")
    if np.__version__ != "2.3.5" or scipy.__version__ != "1.17.0":
        raise ValueError("Admitted NumPy/SciPy version mismatch")
    if sys.platform != "linux":
        raise ValueError("Admitted Linux resource accounting required")
    cases = json.loads(args.cases.read_text())
    if not cases or any(c["panel"] != "DEV" or "_DEV:" not in c["case_id"] for c in cases):
        raise ValueError("Only the independently frozen DEV identity bank may run")
    if len({c["case_id"] for c in cases}) != len(cases):
        raise ValueError("Duplicate DEV identities")
    selected = cases if args.all else [c for c in cases if c["case_id"] == args.case]
    if not selected:
        raise ValueError("Requested DEV case does not exist")
    allowed = set(freeze["allowed_case_ids"])
    if any(c["case_id"] not in allowed for c in selected):
        raise ValueError("Selected DEV invocation was not admitted")
    contract = json.loads(args.contract.read_text())
    if (contract["geometry"]["reference_source_channel_interval"][1] -
            contract["geometry"]["reference_source_channel_interval"][0]) != 4096:
        raise ValueError("All 4096 declared ON carriers required")
    budget = freeze["budget"]
    max_wall = min(1800.0, float(budget["max_wall_seconds_per_job"]))
    max_rss = min(4*1024**3, int(budget["max_rss_bytes"]))
    cpu_available = min(12*3600.0, float(budget["remaining_cpu_seconds"]))
    if min(max_wall, cpu_available) <= 10 or peak_rss_bytes() > max_rss:
        raise ValueError("No admitted resource margin to start")
    if args.output.exists():
        raise FileExistsError("Output already exists; ambiguous/repeated invocation refused")

    args.output.mkdir(parents=True)
    write_json(args.output / "admission.json", {"freeze_receipt": freeze,
               "observed_SHA256": observed_hashes, "selected_case_ids": [c["case_id"] for c in selected],
               "numpy": np.__version__, "scipy": scipy.__version__, "python": sys.version,
               "synthetic": True, "scientific_gate": "NOT_EVALUATED_DEVELOPMENT_ONLY"})
    generator = load_module(args.generator, "frozen_dev_generator")
    summarizer = load_module(args.summarizer, "frozen_dev_summarizer")
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.signal(signal.SIGPROF, timeout_handler)
    # Reserve 10 wall seconds / 5 CPU seconds for flushing the failure record.
    elapsed_startup = time.monotonic()-PROCESS_STARTED
    signal.setitimer(signal.ITIMER_REAL, max(1.0, max_wall-elapsed_startup-10))
    signal.setitimer(signal.ITIMER_PROF, max(1.0, cpu_available-cpu_seconds()-5))
    wall_start, cpu_start = PROCESS_STARTED, 0.0
    outcomes = []
    failed = False
    try:
        for case_number, case in enumerate(selected):
            if (time.monotonic()-wall_start >= max_wall-10 or
                    cpu_seconds() >= cpu_available-5 or peak_rss_bytes() > max_rss):
                raise TimeoutError("Insufficient admitted margin before next DEV case")
            case_path = args.output / f"case_{case_number:03d}"
            case_path.mkdir()
            write_json(case_path / "case_definition.json", case)
            cwall, ccpu = time.monotonic(), cpu_seconds()
            outcome = {"case_id": case["case_id"], "panel": "DEV", "family": case["family"],
                       "data_integrity_ok": False, "all_active_on_recovered": False,
                       "any_localized_on_recovered": False, "pre_OFF_all_active_recovery": False,
                       "pre_OFF_any_active_recovery": False, "survivor_count": 0, "failure": None}
            try:
                arrays, truth = generator.generate_case(case, contract)
                write_json(case_path / "truth.json", truth)
                array_hashes = [{"scan_id": h["scan_id"], "shape": list(a.shape),
                                 "dtype": str(a.dtype), "C_order_bytes_SHA256":
                                 hashlib.sha256(a.tobytes(order="C")).hexdigest()}
                                for a, h in zip(arrays, contract["geometry"]["scan_metadata"])]
                write_json(case_path / "synthetic_array_hashes.json", array_hashes)
                scans, frequencies = control_inputs(arrays, contract)
                if peak_rss_bytes() > max_rss:
                    raise MemoryError("Admitted peak RSS exceeded before detector")
                result = search_cadence(scans, frequencies, Config())
                save_result(case_path, result)
                if truth["active_ON_scan_ids"]:
                    recovery = recovery_matches(result, truth)
                    write_json(case_path / "localized_recovery.json", recovery)
                    outcome.update(all_active_on_recovered=recovery["final_all_active_recovery"],
                                   any_localized_on_recovered=recovery["final_any_active_recovery"],
                                   pre_OFF_all_active_recovery=recovery["pre_OFF_all_active_recovery"],
                                   pre_OFF_any_active_recovery=recovery["pre_OFF_any_active_recovery"])
                else:
                    write_json(case_path / "localized_recovery.json",
                               {"recovery_applicable": False, "reason": "No active ON signal in frozen truth"})
                if peak_rss_bytes() > max_rss:
                    raise MemoryError("Admitted peak RSS exceeded")
                outcome.update(data_integrity_ok=True,
                               survivor_count=result["surviving_ON_threshold_carrier_count"],
                               ON_threshold_carrier_count=len(result["all_ON_threshold_carriers"]))
            except Exception as exc:
                outcome["failure"] = {"type": type(exc).__name__, "message": str(exc)}
                (case_path / "failure_traceback.txt").write_text(traceback.format_exc())
                failed = True
            finally:
                outcome.update(snapshot(cwall, ccpu))
                write_json(case_path / "outcome.json", outcome)
                manifest = {f.name: {"SHA256": digest(f), "size_bytes": f.stat().st_size}
                            for f in sorted(case_path.iterdir()) if f.is_file()}
                write_json(case_path / "artifact_manifest.json", manifest)
                outcomes.append(outcome)
                write_json(args.output / "outcomes.json", outcomes)
                print(json.dumps({key: outcome.get(key) for key in (
                    "case_id", "data_integrity_ok", "all_active_on_recovered", "survivor_count",
                    "wall_s", "cpu_s", "peak_rss_bytes", "failure")}), flush=True)
            if failed:
                break
            del arrays, scans, result
    except Exception as exc:
        failed = True
        write_json(args.output / "job_failure.json", {"type": type(exc).__name__, "message": str(exc)})
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.setitimer(signal.ITIMER_PROF, 0)
        observed = snapshot(wall_start, cpu_start)
        write_json(args.output / "resource_receipt.json", {**observed, "caps": {
            "wall_s": max_wall, "cpu_s_available": cpu_available, "peak_rss_bytes": max_rss},
            "caps_passed": observed["wall_s"] <= max_wall and observed["cpu_s"] <= cpu_available
                           and observed["peak_rss_bytes"] <= max_rss})
        summary = summarizer.summarize(cases, outcomes, "DEV")
        summary["job_failure"] = failed
        summary["selected_case_count"] = len(selected)
        summary["selected_case_outcomes_recorded"] = len(outcomes)
        summary["selected_cases_completed"] = sum(bool(o["data_integrity_ok"]) and not o["failure"] for o in outcomes)
        write_json(args.output / "development_summary.json", summary)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
