#!/usr/bin/env python3
"""Retrospective LS4C audit using published metrics and synthetic data only.

Run from the repository root with PYTHONPATH=src:scripts. This preserves the
frozen detector and its historical dispositions; it does not read radio data.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from seti_repeater.light_sail_htr import compare_on_off, evaluate_timeseries
from seti_repeater.search_v0p6 import canonical_json_bytes


INPUTS = {
    "results_ls4c_htr/followup.json": "b5269c7223cbe17ac40edc9f2c85d6dd52c64aa0a5e2c735a6a4e5e49bb7996f",
    "config/ls4c_lhs1140_x_htr_followup.json": "8d2b55785c1d6d960390b471d1f0b72842709886619e2f89b4b7d0eb857c5147",
    "src/seti_repeater/light_sail_htr.py": "80c66abdd0db55d935315cd1f090e4172b80955f76b5c57230d2888ef6b0550f",
}
COMPARE_KEYS = (
    "envelope_on_threshold", "envelope_off_veto_threshold",
    "pulse_score_threshold", "minimum_on_off_pulse_margin",
    "required_subsecond_scales",
)


def verified_json(path: Path, expected_sha256: str) -> dict:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError(f"input identity changed: {path}")
    return json.loads(raw)


def center_selected_channels(header: dict, low: float, high: float) -> np.ndarray:
    """Independent frequency-center predicate, not historical rounding code."""
    centers = header["fch1_mhz"] + np.arange(header["nchans"]) * header["foff_mhz"]
    return np.flatnonzero((centers >= low) & (centers <= high))


def level_step_counterexample(config: dict) -> dict:
    """A constructive specificity counterexample, not a false-alarm estimate."""
    header, settings = config["expected_filterbank_header"], config["analysis"]
    candidate = next(x for x in config["candidates"] if x["candidate_id"] == "LS4B-A1-9380")
    rng = np.random.default_rng(114004)
    n, dt = header["ntime"], header["tsamp_s"]
    on, off = rng.normal(100.0, 1.0, n), rng.normal(100.0, 1.0, n)
    centers = (np.arange(n) + 0.5) * dt
    inside = (centers >= candidate["time_start_s"]) & (centers < candidate["time_stop_s"])
    on[inside] += 1.0

    def evaluate(values):
        return evaluate_timeseries(
            values, dt, candidate["time_start_s"], candidate["time_stop_s"],
            settings["pulse_width_s"], reference_guard_s=settings["reference_guard_s"],
            pulse_score_threshold=settings["pulse_score_threshold"],
        )

    on_metrics, off_metrics = evaluate(on), evaluate(off)
    comparison = compare_on_off(on_metrics, off_metrics, **{k: settings[k] for k in COMPARE_KEYS})
    return {
        "seed": 114004, "sample_count": n, "sample_time_s": dt,
        "noise_mean": 100.0, "noise_standard_deviation": 1.0,
        "on_level_step": 1.0, "injected_subsecond_pulses": False,
        "on_envelope_score": on_metrics["envelope_mean_screening_score"],
        "off_envelope_score": off_metrics["envelope_mean_screening_score"],
        "comparison": comparison,
        "interpretation": "A constant plateau plus white noise passes the historical morphology rule. This demonstrates non-specificity, not the cause of the real event or its false-alarm probability.",
    }


def audit(root: Path) -> dict:
    result = verified_json(root / "results_ls4c_htr/followup.json", INPUTS["results_ls4c_htr/followup.json"])
    config = verified_json(root / "config/ls4c_lhs1140_x_htr_followup.json", INPUTS["config/ls4c_lhs1140_x_htr_followup.json"])
    detector_path = "src/seti_repeater/light_sail_htr.py"
    if hashlib.sha256((root / detector_path).read_bytes()).hexdigest() != INPUTS[detector_path]:
        raise ValueError("historical detector changed")
    identity = {k: v for k, v in result.items() if k != "result_sha256"}
    if hashlib.sha256(canonical_json_bytes(identity)).hexdigest() != result["result_sha256"]:
        raise ValueError("historical result identity mismatch")
    rows = []
    settings = config["analysis"]
    for item in result["candidates"]:
        comparison = compare_on_off(item["on_metrics"], item["off_metrics"], **{k: settings[k] for k in COMPARE_KEYS})
        if comparison != item["comparison"]:
            raise ValueError("historical decision does not replay")
        band = item["on_band"]
        selected = center_selected_channels(config["expected_filterbank_header"], band["requested_frequency_low_mhz"], band["requested_frequency_high_mhz"])
        stored = set(range(band["channel_start"], band["channel_stop"]))
        scales = []
        supported = {x["requested_width_s"] for x in comparison["supported_subsecond_scales"]}
        for on, off in zip(item["on_metrics"]["pulse_scales"], item["off_metrics"]["pulse_scales"], strict=True):
            if on["requested_width_s"] >= 1.0:
                continue
            scales.append({
                "width_s": on["requested_width_s"],
                "historically_supported": on["requested_width_s"] in supported,
                "on_maximum_inside_score": on["maximum_inside_score"],
                "on_maximum_reference_score": on["maximum_reference_score"],
                "on_reference_exceeds_inside": on["maximum_reference_score"] > on["maximum_inside_score"],
                "off_maximum_inside_score": off["maximum_inside_score"],
                "off_inside_blocks_at_threshold": off["inside_blocks_at_threshold"],
                "inside_block_count": on["inside_block_count"],
                "reference_block_count": on["reference_block_count"],
            })
        event = item["stage1_event"]
        rows.append({
            "candidate_id": item["candidate_id"], "historical_comparison_replayed": True,
            "historical_disposition": comparison["disposition"],
            "on_off_extraction_bands_equal": band == item["off_band"],
            "stored_htr_channel_count": len(stored),
            "center_selected_channel_count": len(selected),
            "extra_channels_outside_requested_centers": sorted(stored - set(selected.tolist())),
            "center_selected_bounds": [int(selected[0]), int(selected[-1]) + 1],
            "effective_htr_center_extent_mhz": band["effective_frequency_extent_mhz"],
            "stage1_inside_9300_9500_mhz": event["frequency_start_mhz"] >= 9300 and event["frequency_stop_mhz"] <= 9500,
            "pulse_scales": scales,
        })
    events = config["candidates"]
    overlap_start = max(x["time_start_s"] for x in events)
    overlap_stop = min(x["time_stop_s"] for x in events)
    out = {
        "artifact_type": "seti_repeater.ls4d_retrospective_audit", "schema_version": 1,
        "base_commit": "3ba9a2ec0de5c0869793e659920b1af50b3659d3",
        "input_sha256": INPUTS, "historical_result_identity": result["result_sha256"],
        "status": "audit-complete-morphology-evidence-insufficient-origin-unresolved",
        "retrospective": True, "new_radio_spectral_values_read": False,
        "historical_dispositions_modified": False, "technosignature_claimed": False,
        "shared_envelope_interval_s": [overlap_start, overlap_stop],
        "shared_envelope_duration_s": max(0.0, overlap_stop - overlap_start),
        "candidates": rows, "level_step_counterexample": level_step_counterexample(config),
        "numpy_version": np.__version__,
        "limitations": [
            "Reference intervals contain more blocks; comparing maxima is descriptive and is not a calibrated veto.",
            "OFF pulses are in a separate later scan, not simultaneous coincidence evidence.",
            "Summary receipts contain no pulse timestamps, cross-band correlation, fine spectral shapes or clipping statistics.",
            "HTR reprocessing of the same recording is not independent astronomical confirmation.",
            "Band overlap is RFI context, not identification of an emitter at GBT.",
            "The real event was not reprocessed with center-selected channels or a revised detector.",
        ],
    }
    archive_path = root / "results_ls4d_audit/archive_refresh.json"
    archive = json.loads(archive_path.read_text())
    records = archive.get("response", {}).get("data", [])
    archive_ok = archive.get("http_status") == 200 and archive.get("response", {}).get("result") == "success"
    out["archive_inventory"] = {
        "receipt_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        "retrieved_utc": archive["retrieved_utc"], "successful": archive_ok,
        "record_count": len(records),
        "cadence_urls": [x["cadence_url"] for x in records],
        "x_band_cadence_urls": [x["cadence_url"] for x in records if 8000 <= x["center_freq"] <= 12000],
        "scope": "GBT primary-target complete-cadence listings for exact alias LHS1140, limit 3000. Not an exhaustive search of every archive, alias or ungrouped scan.",
    }
    out["result_sha256"] = hashlib.sha256(canonical_json_bytes(out)).hexdigest()
    return out


def main():
    root = Path(__file__).resolve().parents[1]
    result = audit(root)
    directory = root / "results_ls4d_audit"
    directory.mkdir(exist_ok=True)
    (directory / "audit.json").write_bytes(canonical_json_bytes(result))
    print(json.dumps({"status": result["status"], "result_sha256": result["result_sha256"]}))


if __name__ == "__main__":
    main()
