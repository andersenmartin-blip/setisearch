#!/usr/bin/env python3
"""Run the frozen LS1 high-time-resolution follow-up of Stage 1 survivors."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from seti_repeater.light_sail_htr import compare_on_off, evaluate_timeseries
from seti_repeater.search_v0p6 import canonical_json_bytes


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_value(value: Any) -> Any:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def channel_bounds(
    fch1_mhz: float, foff_mhz: float, nchans: int, low_mhz: float, high_mhz: float
) -> tuple[int, int]:
    indices = [
        int(np.ceil((low_mhz - fch1_mhz) / foff_mhz)),
        int(np.floor((high_mhz - fch1_mhz) / foff_mhz)),
    ]
    start, final = sorted(indices)
    start = max(0, start)
    stop = min(nchans - 1, final) + 1
    if stop - start < 2:
        raise RuntimeError("candidate band has fewer than two HTR channels")
    return start, stop


def open_source(path: Path, source: dict):
    import h5py
    import hdf5plugin  # noqa: F401

    if path.stat().st_size != int(source["expected_size_bytes"]):
        raise RuntimeError(f"HTR size changed for {source['label']}")
    handle = h5py.File(path, "r")
    dataset = handle["data"]
    attrs = {
        **{key: json_value(value) for key, value in handle.attrs.items()},
        **{key: json_value(value) for key, value in dataset.attrs.items()},
    }
    if len(dataset.shape) != 3 or dataset.shape[1] != 1:
        handle.close()
        raise RuntimeError("unexpected HTR dataset geometry")
    if str(attrs["source_name"]).casefold() != source["expected_source_name"].casefold():
        handle.close()
        raise RuntimeError(f"HTR source changed for {source['label']}")
    if abs(float(attrs["tstart"]) - float(source["expected_tstart_mjd"])) > 2 / 86_400:
        handle.close()
        raise RuntimeError(f"HTR start time changed for {source['label']}")
    sample_time_s = float(attrs["tsamp"])
    foff_mhz = float(attrs["foff"])
    if not 0.0001 <= sample_time_s <= 0.001:
        handle.close()
        raise RuntimeError("HTR time resolution is outside frozen class")
    if not 0.1 <= abs(foff_mhz) <= 1.0:
        handle.close()
        raise RuntimeError("HTR frequency resolution is outside frozen class")
    return handle, dataset, attrs


def band_timeseries(dataset, attrs: dict, candidate: dict) -> tuple[np.ndarray, dict]:
    padding = float(candidate["frequency_padding_mhz"])
    low = float(candidate["frequency_start_mhz"]) - padding
    high = float(candidate["frequency_stop_mhz"]) + padding
    start, stop = channel_bounds(
        float(attrs["fch1"]), float(attrs["foff"]), int(dataset.shape[-1]), low, high
    )
    values = np.asarray(dataset[:, 0, start:stop], dtype=np.float32)
    return np.nanmean(values, axis=1, dtype=np.float64), {
        "channel_start": start,
        "channel_stop": stop,
        "channel_count": stop - start,
        "requested_frequency_low_mhz": low,
        "requested_frequency_high_mhz": high,
    }


def run(config_path: Path, data_dir: Path) -> dict[str, Any]:
    config_raw = config_path.read_bytes()
    config = json.loads(config_raw)
    stage1_path = Path(config["stage1"]["result_path"])
    if sha256_file(stage1_path) != config["stage1"]["result_file_sha256"]:
        raise RuntimeError("Stage 1 result file identity changed")
    stage1 = json.loads(stage1_path.read_text(encoding="utf-8"))
    if (
        stage1["result_sha256"] != config["stage1"]["result_identity_sha256"]
        or stage1["high_time_resolution_followup_authorized"] is not True
        or stage1["surviving_event_count"] != len(config["candidates"])
    ):
        raise RuntimeError("Stage 1 did not authorize this exact HTR follow-up")
    observed_candidates = [
        {"on_label": item["on_label"], **item["event"]}
        for item in stage1["candidates"]
        if item["survives_adjacent_off_veto"]
    ]
    expected_stage1_candidates = [
        {
            key: value
            for key, value in item.items()
            if key not in {"candidate_id", "off_label", "frequency_padding_mhz"}
        }
        for item in config["candidates"]
    ]
    if observed_candidates != expected_stage1_candidates:
        raise RuntimeError("Stage 1 survivor inventory changed")
    source_by_label = {item["label"]: item for item in config["sources"]}
    opened = {}
    try:
        for label, source in source_by_label.items():
            path = data_dir / f"{label}.8.0001.h5"
            handle, dataset, attrs = open_source(path, source)
            opened[label] = (handle, dataset, attrs, sha256_file(path))
        records = []
        settings = config["analysis"]
        for candidate in config["candidates"]:
            on_handle, on_dataset, on_attrs, on_sha = opened[candidate["on_label"]]
            off_handle, off_dataset, off_attrs, off_sha = opened[candidate["off_label"]]
            del on_handle, off_handle
            on_series, on_band = band_timeseries(on_dataset, on_attrs, candidate)
            off_series, off_band = band_timeseries(off_dataset, off_attrs, candidate)
            common = {
                "envelope_start_s": float(candidate["time_start_s"]),
                "envelope_stop_s": float(candidate["time_stop_s"]),
                "pulse_width_s": settings["pulse_width_s"],
                "reference_guard_s": float(settings["reference_guard_s"]),
                "pulse_score_threshold": float(settings["pulse_score_threshold"]),
            }
            on_metrics = evaluate_timeseries(
                on_series, float(on_attrs["tsamp"]), **common
            )
            off_metrics = evaluate_timeseries(
                off_series, float(off_attrs["tsamp"]), **common
            )
            comparison = compare_on_off(
                on_metrics,
                off_metrics,
                envelope_on_threshold=float(settings["envelope_on_threshold"]),
                envelope_off_veto_threshold=float(
                    settings["envelope_off_veto_threshold"]
                ),
                pulse_score_threshold=float(settings["pulse_score_threshold"]),
                minimum_on_off_pulse_margin=float(
                    settings["minimum_on_off_pulse_margin"]
                ),
                required_subsecond_scales=int(
                    settings["required_subsecond_scales"]
                ),
            )
            records.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "stage1_event": observed_candidates[len(records)],
                    "on_source_sha256": on_sha,
                    "off_source_sha256": off_sha,
                    "on_band": on_band,
                    "off_band": off_band,
                    "on_metrics": on_metrics,
                    "off_metrics": off_metrics,
                    "comparison": comparison,
                }
            )
    finally:
        for handle, _dataset, _attrs, _sha in opened.values():
            handle.close()
    supported = [
        item for item in records if item["comparison"]["diffraction_structure_supported"]
    ]
    result: dict[str, Any] = {
        "artifact_type": "seti_repeater.ls1_htr_followup",
        "schema_version": 1,
        "status": (
            "followup-complete-independent-observation-required"
            if supported
            else "followup-complete-no-diffraction-supported-candidate"
        ),
        "config_sha256": hashlib.sha256(config_raw).hexdigest(),
        "stage1_result_identity_sha256": stage1["result_sha256"],
        "candidate_count": len(records),
        "diffraction_supported_candidate_count": len(supported),
        "candidates": records,
        "spectral_dataset_values_read": True,
        "raw_spectral_payload_published": False,
        "scores_are_calibrated_significances": False,
        "independent_observation_completed": False,
        "technosignature_claimed": False,
    }
    result["result_sha256"] = hashlib.sha256(canonical_json_bytes(result)).hexdigest()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--data-dir", type=Path, default=Path("data_ls1_htr"))
    parser.add_argument(
        "--output", type=Path, default=Path("results_ls1_htr/followup.json")
    )
    args = parser.parse_args()
    result = run(args.config, args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(f".{args.output.name}.tmp-{os.getpid()}")
    temporary.write_bytes(canonical_json_bytes(result))
    os.replace(temporary, args.output)
    print(canonical_json_bytes(result).decode("utf-8"))


if __name__ == "__main__":
    main()
