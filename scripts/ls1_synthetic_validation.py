#!/usr/bin/env python3
"""Run the frozen LS1 detector against a deterministic synthetic injection."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from seti_repeater.light_sail import search_broadband_events
from seti_repeater.search_v0p6 import canonical_json_bytes


def overlap(start: float, stop: float, truth_start: float, truth_stop: float) -> float:
    intersection = max(0.0, min(stop, truth_stop) - max(start, truth_start))
    return intersection / min(stop - start, truth_stop - truth_start)


def run_validation() -> dict:
    seed = 219134
    generator = np.random.default_rng(seed)
    ntime, nfrequency = 192, 2048
    sample_time_s = 1.0
    frequency_mhz = np.linspace(1100.0, 1200.0, nfrequency, endpoint=False)
    data = generator.normal(100.0, 3.0, size=(ntime, nfrequency)).astype(np.float32)
    time_start, time_stop = 73, 97
    channel_start, channel_stop = 768, 1024
    data[time_start:time_stop, channel_start:channel_stop] += np.float32(9.0)
    search = search_broadband_events(
        data,
        frequency_mhz,
        sample_time_s,
        base_bin_channels=32,
        spectral_width_bins=(1, 2, 4, 8, 16),
        duration_s=(4.0, 8.0, 16.0, 24.0, 32.0),
        minimum_score=6.0,
        maximum_events=128,
    )
    truth_frequency_start = float(frequency_mhz[channel_start])
    truth_frequency_stop = float(frequency_mhz[channel_stop - 1])
    recovered = [
        event
        for event in search["events"]
        if overlap(
            event["frequency_start_mhz"],
            event["frequency_stop_mhz"],
            truth_frequency_start,
            truth_frequency_stop,
        )
        >= 0.8
        and overlap(
            event["time_start_s"],
            event["time_stop_s"],
            float(time_start),
            float(time_stop),
        )
        >= 0.8
    ]
    result = {
        "artifact_type": "seti_repeater.ls1_synthetic_validation",
        "schema_version": 1,
        "seed": seed,
        "truth": {
            "time_start_s": float(time_start),
            "time_stop_s": float(time_stop),
            "frequency_start_mhz": truth_frequency_start,
            "frequency_stop_mhz": truth_frequency_stop,
            "added_native_channel_amplitude": 9.0,
        },
        "search_summary": {
            key: value for key, value in search.items() if key != "events"
        },
        "recovered": bool(recovered),
        "best_matching_event": recovered[0] if recovered else None,
        "spectral_dataset_values_read": False,
        "technosignature_claimed": False,
    }
    if not recovered:
        raise RuntimeError("frozen synthetic LS1 injection was not recovered")
    result["result_sha256"] = hashlib.sha256(canonical_json_bytes(result)).hexdigest()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("results_ls1/synthetic_validation.json")
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
