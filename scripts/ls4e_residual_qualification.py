#!/usr/bin/env python3
"""Execute every frozen LS4E synthetic case and publish derived diagnostics."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform

import numpy as np

from seti_repeater.light_sail_residual import residual_metrics, compare_residuals
from seti_repeater.search_v0p6 import canonical_json_bytes

ROOT = Path(__file__).resolve().parents[1]


def make_case(name: str, seed: int, validation: dict):
    rng = np.random.default_rng(seed)
    n, dt = validation["sample_count"], validation["sample_time_s"]
    start, stop = validation["envelope_s"]
    t = (np.arange(n) + 0.5) * dt
    on, off = rng.normal(100, 1, n), rng.normal(100, 1, n)
    inside = (t >= start) & (t < stop)
    pulse_times = []

    def add_pulses(series, times):
        for time in times:
            series[np.abs(t - time) < 0.006] += 10.0

    periodic = np.arange(start + 2.15, stop - 2, 2.7)
    if name == "constant_plateau":
        on[inside] += 1.0
    elif name == "smooth_envelope":
        on += 5.0 * np.exp(-0.5 * ((t - 50.0) / 10.0) ** 2)
    elif name == "linear_trend":
        on += 0.25 * t
    elif name == "gain_step":
        on[t >= 50.25] += 8.0
    elif name == "isolated_impulse":
        add_pulses(on, [50.25])
    elif name in {"periodic_pulses", "common_on_off_pulses", "on_reference_pulses"}:
        on[inside] += 0.25
        add_pulses(on, periodic)
        pulse_times = periodic.tolist()
        if name == "common_on_off_pulses":
            # OFF train occurs at other scan-relative times, testing whole-scan veto.
            add_pulses(off, periodic + 15.0)
        if name == "on_reference_pulses":
            add_pulses(on, [10.25, 15.15, 20.75])
    elif name == "irregular_pulses":
        pulse_times = [start + x for x in [2.13, 5.67, 11.12, 18.84, 27.37, 34.42]]
        on[inside] += 0.25
        add_pulses(on, pulse_times)
    elif name != "white_noise":
        raise ValueError(f"unknown synthetic case: {name}")
    return on, off, pulse_times


def evaluate_pair(on, off, dt, envelope, settings):
    on_metrics = residual_metrics(on, dt, *envelope, settings)
    off_metrics = residual_metrics(off, dt, *envelope, settings)
    comparison = compare_residuals(on_metrics, off_metrics, settings)
    return {"comparison": comparison,
            "on_pulse_counts": [len(x["inside_pulses"]) for x in on_metrics["scales"]],
            "on_reference_counts": [len(x["reference_pulses"]) for x in on_metrics["scales"]],
            "off_total_counts": [len(x["inside_pulses"]) + len(x["reference_pulses"]) for x in off_metrics["scales"]]}


def verify_freeze():
    for line in (ROOT / "LS4E_FREEZE.sha256").read_text().splitlines():
        expected, relative = line.split("  ", 1)
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f"LS4E freeze changed: {relative}")


def main():
    verify_freeze()
    config_path = ROOT / "config/ls4e_residual_qualification.json"
    config = json.loads(config_path.read_text())
    validation, settings = config["validation"], config["settings"]
    rows, totals = [], {}
    for name in validation["negative_cases"] + validation["positive_cases"]:
        count = 0
        for seed in validation["seeds"]:
            on, off, pulse_times = make_case(name, seed, validation)
            result = evaluate_pair(on, off, validation["sample_time_s"], validation["envelope_s"], settings)
            count += int(result["comparison"]["residual_pulse_pattern_pass"])
            rows.append({"case": name, "seed": seed, "injected_on_pulse_times_s": pulse_times, **result})
        totals[name] = {"passes": count, "trials": len(validation["seeds"])}
        print(f"{name}: {count}/{len(validation['seeds'])}", flush=True)
    old = json.loads((ROOT / "config/ls4c_lhs1140_x_htr_followup.json").read_text())
    native = old["expected_filterbank_header"]
    candidate = next(x for x in old["candidates"] if x["candidate_id"] == "LS4B-A1-9380")
    native_validation = {"sample_count": native["ntime"], "sample_time_s": native["tsamp_s"],
                         "envelope_s": [candidate["time_start_s"], candidate["time_stop_s"]]}
    on, off, _ = make_case("constant_plateau", validation["native_geometry_plateau_seed"], native_validation)
    native_result = evaluate_pair(on, off, native["tsamp_s"], native_validation["envelope_s"], settings)
    passed = all(totals[n]["passes"] == 0 for n in validation["negative_cases"])
    passed &= all(totals[n]["passes"] >= 22 for n in validation["positive_cases"])
    passed &= not native_result["comparison"]["residual_pulse_pattern_pass"]
    result = {"artifact_type": "seti_repeater.ls4e_synthetic_qualification_result", "schema_version": 1,
              "status": "synthetic-gate-passed" if passed else "synthetic-gate-failed",
              "total_grid_trials": len(rows), "totals": totals, "trials": rows,
              "native_plateau_counterexample": {**native_validation, **native_result},
              "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
              "freeze_sha256": hashlib.sha256((ROOT / "LS4E_FREEZE.sha256").read_bytes()).hexdigest(),
              "python_version": platform.python_version(), "numpy_version": np.__version__,
              "new_radio_spectral_values_read": False, "raw_spectral_access_ready": False,
              "selection_conditioning": "Fixed synthetic envelopes; Stage-1 selection not simulated.",
              "false_alarm_calibrated": False, "technosignature_claimed": False,
              "retuned_after_results": False}
    result["result_sha256"] = hashlib.sha256(canonical_json_bytes(result)).hexdigest()
    directory = ROOT / "results_ls4e_qualification"
    directory.mkdir(exist_ok=True)
    (directory / "qualification.json").write_bytes(canonical_json_bytes(result))
    print(json.dumps({"status": result["status"], "result_sha256": result["result_sha256"]}))


if __name__ == "__main__":
    main()
