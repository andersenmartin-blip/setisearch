#!/usr/bin/env python3
"""Run the frozen LS4C HTR follow-up with sequential raw-file deletion."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
from typing import Any

import numpy as np

from ls1_fetch import fetch
from seti_repeater.light_sail_htr import compare_on_off, evaluate_timeseries
from seti_repeater.search_v0p6 import canonical_json_bytes
from seti_repeater.sigproc import parse_sigproc_header_bytes


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def channel_bounds(
    fch1_mhz: float,
    foff_mhz: float,
    nchans: int,
    low_mhz: float,
    high_mhz: float,
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


def verify_stage1(config: dict) -> list[dict[str, Any]]:
    stage1_path = Path(config["stage1"]["result_path"])
    if sha256_file(stage1_path) != config["stage1"]["result_file_sha256"]:
        raise RuntimeError("LS4B result file identity changed")
    stage1 = json.loads(stage1_path.read_text(encoding="utf-8"))
    if (
        stage1.get("result_sha256") != config["stage1"]["result_identity_sha256"]
        or stage1.get("high_time_resolution_followup_preregistration_required") is not True
        or stage1.get("surviving_event_count") != len(config["candidates"])
        or stage1.get("high_time_resolution_values_read") is not False
    ):
        raise RuntimeError("LS4B did not authorize this exact HTR preregistration")
    observed = [
        {"on_label": item["on_label"], **item["event"]}
        for item in stage1["candidates"]
        if item["survives_adjacent_off_veto"]
    ]
    expected = [
        {
            key: value
            for key, value in item.items()
            if key not in {"candidate_id", "off_label", "frequency_padding_mhz"}
        }
        for item in config["candidates"]
    ]
    if observed != expected:
        raise RuntimeError("LS4B survivor inventory changed")
    return observed


def verify_analysis_inheritance(config: dict, ls1_htr_config_path: Path) -> None:
    ls1 = json.loads(ls1_htr_config_path.read_text(encoding="utf-8"))
    if config["analysis"] != ls1["analysis"]:
        raise RuntimeError("LS4C HTR analysis differs from the frozen LS1 analysis")


def parse_and_validate_header(path: Path, source: dict, config: dict) -> tuple[dict, int]:
    expected_size = int(source["expected_size_bytes"])
    if path.stat().st_size != expected_size:
        raise RuntimeError(f"HTR size changed for {source['label']}")
    with path.open("rb") as handle:
        raw = handle.read(65_536)
    header, data_offset = parse_sigproc_header_bytes(raw)
    expected = config["expected_filterbank_header"]
    for field in ("nchans", "nifs", "nbits"):
        if int(header[field]) != int(expected[field]):
            raise RuntimeError(f"SIGPROC {field} changed for {source['label']}")
    for field, expected_field in {
        "fch1": "fch1_mhz",
        "foff": "foff_mhz",
        "tsamp": "tsamp_s",
    }.items():
        if not math.isclose(
            float(header[field]), float(expected[expected_field]), rel_tol=0.0, abs_tol=1e-9
        ):
            raise RuntimeError(f"SIGPROC {field} changed for {source['label']}")
    if data_offset != int(expected["header_bytes"]):
        raise RuntimeError(f"SIGPROC header length changed for {source['label']}")
    if str(header["source_name"]).casefold() != source["expected_source_name"].casefold():
        raise RuntimeError(f"HTR source changed for {source['label']}")
    if not math.isclose(
        float(header["tstart"]), float(source["expected_tstart_mjd"]), rel_tol=0.0, abs_tol=1e-9
    ):
        raise RuntimeError(f"HTR start epoch changed for {source['label']}")
    payload_bytes = expected_size - data_offset
    expected_payload = (
        int(expected["ntime"])
        * int(expected["nchans"])
        * int(expected["nifs"])
        * int(expected["nbits"])
        // 8
    )
    if payload_bytes != expected_payload:
        raise RuntimeError(f"HTR payload geometry changed for {source['label']}")
    return header, data_offset


def extract_candidate_series(
    path: Path,
    header: dict,
    data_offset: int,
    candidates: list[dict[str, Any]],
    config: dict,
) -> tuple[dict[str, np.ndarray], dict[str, dict[str, Any]]]:
    expected = config["expected_filterbank_header"]
    ntime = int(expected["ntime"])
    nchans = int(expected["nchans"])
    matrix = np.memmap(
        path,
        dtype=np.uint8,
        mode="r",
        offset=data_offset,
        shape=(ntime, nchans),
        order="C",
    )
    bounds: dict[str, tuple[int, int, float, float]] = {}
    series = {
        candidate["candidate_id"]: np.empty(ntime, dtype=np.float64)
        for candidate in candidates
    }
    for candidate in candidates:
        padding = float(candidate["frequency_padding_mhz"])
        low = float(candidate["frequency_start_mhz"]) - padding
        high = float(candidate["frequency_stop_mhz"]) + padding
        start, stop = channel_bounds(
            float(header["fch1"]), float(header["foff"]), nchans, low, high
        )
        bounds[candidate["candidate_id"]] = (start, stop, low, high)
    chunk_rows = int(config["resource_policy"]["chunk_rows"])
    for row_start in range(0, ntime, chunk_rows):
        row_stop = min(ntime, row_start + chunk_rows)
        block = matrix[row_start:row_stop]
        for candidate in candidates:
            candidate_id = candidate["candidate_id"]
            start, stop, _low, _high = bounds[candidate_id]
            series[candidate_id][row_start:row_stop] = np.mean(
                block[:, start:stop], axis=1, dtype=np.float64
            )
    del matrix
    band_records = {}
    for candidate in candidates:
        candidate_id = candidate["candidate_id"]
        start, stop, low, high = bounds[candidate_id]
        first = float(header["fch1"]) + start * float(header["foff"])
        last = float(header["fch1"]) + (stop - 1) * float(header["foff"])
        band_records[candidate_id] = {
            "channel_start": start,
            "channel_stop": stop,
            "channel_count": stop - start,
            "requested_frequency_low_mhz": low,
            "requested_frequency_high_mhz": high,
            "effective_frequency_extent_mhz": sorted((first, last)),
        }
    return series, band_records


def evaluate_source(
    source: dict,
    path: Path,
    source_sha256: str,
    config: dict,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    header, data_offset = parse_and_validate_header(path, source, config)
    relevant = [
        candidate
        for candidate in config["candidates"]
        if source["label"] in {candidate["on_label"], candidate["off_label"]}
    ]
    series, bands = extract_candidate_series(path, header, data_offset, relevant, config)
    settings = config["analysis"]
    metrics = {}
    for candidate in relevant:
        candidate_id = candidate["candidate_id"]
        metrics[candidate_id] = evaluate_timeseries(
            series[candidate_id],
            float(header["tsamp"]),
            float(candidate["time_start_s"]),
            float(candidate["time_stop_s"]),
            settings["pulse_width_s"],
            reference_guard_s=float(settings["reference_guard_s"]),
            pulse_score_threshold=float(settings["pulse_score_threshold"]),
        )
    del series
    receipt = {
        "label": source["label"],
        "role": source["role"],
        "source_name": str(header["source_name"]),
        "tstart_mjd": float(header["tstart"]),
        "sample_time_s": float(header["tsamp"]),
        "source_url": source["url"],
        "source_size_bytes": int(source["expected_size_bytes"]),
        "source_sha256": source_sha256,
        "candidate_series_count": len(relevant),
        "raw_file_deleted_after_evaluation": True,
    }
    return metrics, bands, receipt


def run(
    config_path: Path,
    ls1_htr_config_path: Path,
    data_dir: Path,
) -> tuple[dict[str, Any], list[str]]:
    config_raw = config_path.read_bytes()
    config = json.loads(config_raw)
    if config.get("artifact_type") != "seti_repeater.ls4c_htr_followup_preregistration":
        raise RuntimeError("wrong LS4C configuration artifact")
    if config["freeze_boundary"]["htr_values_read_before_freeze"]:
        raise RuntimeError("LS4C freeze boundary is not prospective")
    observed_candidates = verify_stage1(config)
    verify_analysis_inheritance(config, ls1_htr_config_path)
    total_download = sum(int(source["expected_size_bytes"]) for source in config["sources"])
    if total_download > int(config["resource_policy"]["maximum_total_htr_download_bytes"]):
        raise RuntimeError("selected HTR source inventory exceeds the frozen download cap")
    data_dir.mkdir(parents=True, exist_ok=True)
    metrics_by_candidate: dict[str, dict[str, Any]] = {
        item["candidate_id"]: {} for item in config["candidates"]
    }
    bands_by_candidate: dict[str, dict[str, Any]] = {
        item["candidate_id"]: {} for item in config["candidates"]
    }
    receipts = []
    manifest_lines = []
    for source in config["sources"]:
        destination = data_dir / f"{source['label']}.8.0001.fil"
        expected_size = int(source["expected_size_bytes"])
        required_free = expected_size + int(
            config["resource_policy"]["minimum_free_headroom_bytes_after_download"]
        )
        if shutil.disk_usage(data_dir).free < required_free:
            raise RuntimeError(f"insufficient free disk before {source['label']}")
        fetch_record = {
            "label": source["label"],
            "medium_resolution": {
                "url": source["url"],
                "expected_size_bytes": expected_size,
            },
        }
        try:
            source_sha256 = fetch(fetch_record, destination)
            manifest_lines.append(f"{source_sha256}  {destination.as_posix()}")
            metrics, bands, receipt = evaluate_source(
                source, destination, source_sha256, config
            )
            for candidate_id, value in metrics.items():
                role_key = "on" if source["label"] == next(
                    item["on_label"]
                    for item in config["candidates"]
                    if item["candidate_id"] == candidate_id
                ) else "off"
                metrics_by_candidate[candidate_id][role_key] = value
                bands_by_candidate[candidate_id][role_key] = bands[candidate_id]
            receipts.append(receipt)
            print(f"evaluated HTR source {source['label']}", flush=True)
        finally:
            destination.unlink(missing_ok=True)
            destination.with_suffix(destination.suffix + ".part").unlink(missing_ok=True)
        if destination.exists():
            raise RuntimeError(f"raw HTR file was not deleted after {source['label']}")
    settings = config["analysis"]
    records = []
    receipt_by_label = {item["label"]: item for item in receipts}
    for index, candidate in enumerate(config["candidates"]):
        candidate_id = candidate["candidate_id"]
        metrics = metrics_by_candidate[candidate_id]
        if set(metrics) != {"on", "off"}:
            raise RuntimeError(f"incomplete ON/OFF metrics for {candidate_id}")
        comparison = compare_on_off(
            metrics["on"],
            metrics["off"],
            envelope_on_threshold=float(settings["envelope_on_threshold"]),
            envelope_off_veto_threshold=float(settings["envelope_off_veto_threshold"]),
            pulse_score_threshold=float(settings["pulse_score_threshold"]),
            minimum_on_off_pulse_margin=float(settings["minimum_on_off_pulse_margin"]),
            required_subsecond_scales=int(settings["required_subsecond_scales"]),
        )
        records.append(
            {
                "candidate_id": candidate_id,
                "stage1_event": observed_candidates[index],
                "on_source_sha256": receipt_by_label[candidate["on_label"]]["source_sha256"],
                "off_source_sha256": receipt_by_label[candidate["off_label"]]["source_sha256"],
                "on_band": bands_by_candidate[candidate_id]["on"],
                "off_band": bands_by_candidate[candidate_id]["off"],
                "on_metrics": metrics["on"],
                "off_metrics": metrics["off"],
                "comparison": comparison,
            }
        )
    supported = [
        item for item in records if item["comparison"]["diffraction_structure_supported"]
    ]
    result: dict[str, Any] = {
        "artifact_type": "seti_repeater.ls4c_htr_followup",
        "schema_version": 1,
        "status": (
            "followup-complete-independent-observation-required"
            if supported
            else "followup-complete-no-diffraction-supported-candidate"
        ),
        "config_sha256": hashlib.sha256(config_raw).hexdigest(),
        "stage1_result_identity_sha256": config["stage1"]["result_identity_sha256"],
        "candidate_group_context": config["candidate_group_context"],
        "candidate_count": len(records),
        "diffraction_supported_candidate_count": len(supported),
        "source_receipts": receipts,
        "candidates": records,
        "spectral_dataset_values_read": True,
        "collapsed_timeseries_published": False,
        "raw_files_deleted_after_each_source": True,
        "raw_spectral_payload_published": False,
        "scores_are_calibrated_significances": False,
        "independent_observation_completed": False,
        "technosignature_claimed": False,
    }
    result["result_sha256"] = hashlib.sha256(canonical_json_bytes(result)).hexdigest()
    return result, manifest_lines


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument(
        "--ls1-htr-config", type=Path, default=Path("config/ls1_htr_followup.json")
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data_ls4c_htr"))
    parser.add_argument("--output", type=Path, default=Path("results_ls4c_htr/followup.json"))
    parser.add_argument("--manifest", type=Path, default=Path("DATA_MANIFEST_LS4C_HTR.sha256"))
    args = parser.parse_args()
    result, manifest_lines = run(args.config, args.ls1_htr_config, args.data_dir)
    atomic_write(args.output, canonical_json_bytes(result))
    atomic_write(args.manifest, ("\n".join(manifest_lines) + "\n").encode("utf-8"))
    print(canonical_json_bytes(result).decode("utf-8"))


if __name__ == "__main__":
    main()
