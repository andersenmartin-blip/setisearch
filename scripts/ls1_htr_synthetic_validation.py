#!/usr/bin/env python3
"""Synthetic validation for the frozen LS1 HTR comparison rules."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from seti_repeater.light_sail_htr import compare_on_off, evaluate_timeseries
from seti_repeater.search_v0p6 import canonical_json_bytes


def run_validation() -> dict:
    generator = np.random.default_rng(21913401)
    sample_time_s = 0.001
    sample_count = 120_000
    on = generator.normal(100.0, 2.0, sample_count)
    off = generator.normal(100.0, 2.0, sample_count)
    start_s, stop_s = 30.0, 70.0
    inside = (np.arange(sample_count) * sample_time_s >= start_s) & (
        np.arange(sample_count) * sample_time_s < stop_s
    )
    on[inside] += 0.25
    for center_s in np.arange(start_s + 0.05, stop_s, 0.1):
        center = int(round(center_s / sample_time_s))
        on[center : center + 5] += 8.0
    kwargs = {
        "sample_time_s": sample_time_s,
        "envelope_start_s": start_s,
        "envelope_stop_s": stop_s,
        "pulse_width_s": [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0],
        "reference_guard_s": 2.0,
        "pulse_score_threshold": 8.0,
    }
    on_metrics = evaluate_timeseries(on, **kwargs)
    off_metrics = evaluate_timeseries(off, **kwargs)
    comparison = compare_on_off(
        on_metrics,
        off_metrics,
        envelope_on_threshold=8.0,
        envelope_off_veto_threshold=6.0,
        pulse_score_threshold=8.0,
        minimum_on_off_pulse_margin=2.0,
        required_subsecond_scales=2,
    )
    if not comparison["diffraction_structure_supported"]:
        raise RuntimeError("synthetic HTR diffraction pattern was not recovered")
    result = {
        "artifact_type": "seti_repeater.ls1_htr_synthetic_validation",
        "schema_version": 1,
        "seed": 21913401,
        "recovered": True,
        "comparison": comparison,
        "spectral_dataset_values_read": False,
        "technosignature_claimed": False,
    }
    result["result_sha256"] = hashlib.sha256(canonical_json_bytes(result)).hexdigest()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results_ls1_htr/synthetic_validation.json"),
    )
    args = parser.parse_args()
    result = run_validation()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(f".{args.output.name}.tmp-{os.getpid()}")
    temporary.write_bytes(canonical_json_bytes(result))
    os.replace(temporary, args.output)
    print(canonical_json_bytes(result).decode("utf-8"))


if __name__ == "__main__":
    main()
