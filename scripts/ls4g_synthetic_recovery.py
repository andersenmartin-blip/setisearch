#!/usr/bin/env python3
"""Frozen LS4G conditional synthetic experiment; detector remains unchanged."""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
import platform
import time

import numpy as np

from seti_repeater.light_sail_residual import residual_metrics, compare_residuals

ROOT = Path(__file__).resolve().parents[1]


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def verify_manifest(path, root=ROOT):
    for line in path.read_text().splitlines():
        expected, relative = line.split("  ", 1)
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f"freeze mismatch: {relative}")


def background_pair(seed, background, config):
    rng = np.random.default_rng(seed)
    n, dt = config["sample_count"], config["sample_time_s"]
    pair = rng.normal(size=(2, n))
    if background == "ar1":
        rho = config["ar1_rho"]
        scale = np.sqrt(1 - rho * rho)
        for series in pair:
            for i in range(1, n):
                series[i] = rho * series[i - 1] + scale * series[i]
    elif background == "on_variance_x4":
        t = (np.arange(n) + .5) * dt
        start, stop = config["envelope_s"]
        pair[0, (t >= start) & (t < stop)] *= 2
    elif background != "white":
        raise ValueError(background)
    # Draw jitter after the same number of innovations in every background.
    times = np.array(config["pulse_times_s"]) + rng.uniform(
        -config["pulse_jitter_s"], config["pulse_jitter_s"], len(config["pulse_times_s"]))
    return pair + 100, times.tolist()


def inject(series, times, width, amplitude, dt):
    """Inject half-open rectangular pulses and return their discrete identities."""
    centers = (np.arange(len(series)) + .5) * dt
    truth = []
    for center in times:
        indices = np.flatnonzero((centers >= center - width / 2) & (centers < center + width / 2))
        if not len(indices):
            raise ValueError("pulse contains no sample centers")
        series[indices] += amplitude
        truth.append({"center_s": float(centers[indices].mean()),
                      "width_s": len(indices) * dt, "samples": len(indices)})
    return truth


def truth_matches(pulses, truth, effective_width, dt):
    """Chronological one-to-one associations; truth cannot increase detections."""
    i = j = 0
    matched = set()
    while i < len(pulses) and j < len(truth):
        delta = pulses[i]["peak_time_s"] - truth[j]["center_s"]
        tolerance = (effective_width + truth[j]["width_s"]) / 2 + dt
        if abs(delta) <= tolerance:
            matched.add(j)
            i += 1
            j += 1
        elif delta < 0:
            i += 1
        else:
            j += 1
    return matched


def evaluate(pair, truth, config, settings):
    dt = config["sample_time_s"]
    on, off = [residual_metrics(x, dt, *config["envelope_s"], settings) for x in pair]
    comparison = compare_residuals(on, off, settings)
    matches = {x["requested_width_s"]: truth_matches(x["inside_pulses"], truth, x["effective_width_s"], dt)
               for x in on["scales"]}
    associated = max((len(matches[x["widths_s"][0]] & matches[x["widths_s"][1]])
                      for x in comparison["supporting_scale_pairs"]), default=0)
    return {
        "passed": comparison["residual_pulse_pattern_pass"],
        "supported": bool(comparison["supporting_scale_pairs"]),
        "recovered": bool(comparison["residual_pulse_pattern_pass"] and
                          associated >= settings["minimum_separated_pulses"]),
        "matched_truth_pulses": associated,
        "off_veto": comparison["off_pulse_veto"],
        "reference_veto": comparison["on_reference_pulse_veto"],
        "inside_counts": [len(x["inside_pulses"]) for x in on["scales"]],
        "reference_counts": [len(x["reference_pulses"]) for x in on["scales"]],
        "off_counts": [len(x["inside_pulses"]) + len(x["reference_pulses"]) for x in off["scales"]],
    }


def cell_specs(config):
    for background in config["backgrounds"]:
        yield {"kind": "null", "background": background, "width_s": 0., "amplitude_sigma": 0.}
        for width, amplitude in itertools.product(config["widths_s"], config["amplitudes_sigma"]):
            yield {"kind": "recovery", "background": background, "width_s": width, "amplitude_sigma": amplitude}
    control = config["control"]
    for location, width, amplitude in itertools.product(control["locations"], control["widths_s"], control["amplitudes_sigma"]):
        yield {"kind": "control", "background": "white", "location": location,
               "width_s": width, "amplitude_sigma": amplitude}


def build_trial(base, times, spec, config):
    pair = base.copy()
    truth, control_truth = [], []
    dt = config["sample_time_s"]
    if spec["kind"] == "recovery":
        truth = inject(pair[0], times, spec["width_s"], spec["amplitude_sigma"], dt)
    elif spec["kind"] == "control":
        control = config["control"]
        truth = inject(pair[0], times, control["on_width_s"], control["on_amplitude_sigma"], dt)
        destination = 1 if spec["location"] == "off" else 0
        control_truth = inject(pair[destination], [control["locations"][spec["location"]]],
                               spec["width_s"], spec["amplitude_sigma"], dt)
    elif spec["kind"] != "null":
        raise ValueError(spec["kind"])
    return pair, truth, control_truth


def main():
    verify_manifest(ROOT / "LS4E_FREEZE.sha256")
    verify_manifest(ROOT / "LS4G_FREEZE.sha256")
    config = json.loads((ROOT / "config/ls4g_synthetic_recovery.json").read_text())
    settings = json.loads((ROOT / config["settings_source"]).read_text())["settings"]
    specs = list(cell_specs(config))
    if len(specs) * len(config["seeds"]) != config["expected_trials"]:
        raise ValueError("unexpected grid size")
    output = ROOT / "results_ls4g_synthetic_recovery"
    output.mkdir(exist_ok=False)
    started = time.monotonic()
    count = 0
    totals = [{**s, **{key: 0 for key in ("trials", "passed", "supported", "recovered", "off_veto", "reference_veto")}}
              for s in specs]
    ledger_path = output / "trials.jsonl"
    try:
        with ledger_path.open("wb") as ledger:
            for seed in config["seeds"]:
                for background in config["backgrounds"]:
                    base, times = background_pair(seed, background, config)
                    for index, spec in enumerate(specs):
                        if spec["background"] != background:
                            continue
                        pair, truth, control_truth = build_trial(base, times, spec, config)
                        row = {"cell": index, "seed": seed, "injected_on": truth, "injected_control": control_truth,
                               **evaluate(pair, truth, config, settings)}
                        ledger.write(encoded(row))
                        totals[index]["trials"] += 1
                        for key in ("passed", "supported", "recovered", "off_veto", "reference_veto"):
                            totals[index][key] += int(row[key])
                        count += 1
                ledger.flush()
                print(f"seed {seed}: {count}/{config['expected_trials']} trials", flush=True)
        if count != config["expected_trials"]:
            raise ValueError("incomplete grid")
        summary = {"artifact_type": "seti_repeater.ls4g_synthetic_recovery_result", "version": 1,
                   "status": "completed", "total_trials": count, "cells": totals,
                   "ledger_sha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
                   "freeze_sha256": hashlib.sha256((ROOT / "LS4G_FREEZE.sha256").read_bytes()).hexdigest(),
                   "python_version": platform.python_version(), "numpy_version": np.__version__,
                   "elapsed_s": time.monotonic() - started,
                   "raw_spectral_values_read": False, "retuned_after_results": False,
                   "end_to_end_completeness": False, "false_alarm_calibrated": False,
                   "technosignature_claimed": False}
        summary["result_sha256"] = hashlib.sha256(encoded(summary)).hexdigest()
        (output / "summary.json").write_bytes(encoded(summary))
        print(json.dumps({"status": summary["status"], "trials": count, "result_sha256": summary["result_sha256"]}))
    except Exception as exc:
        (output / "abort.json").write_bytes(encoded({"status": "aborted", "completed_trials": count,
                                                    "error": str(exc), "elapsed_s": time.monotonic() - started}))
        raise


if __name__ == "__main__":
    main()
