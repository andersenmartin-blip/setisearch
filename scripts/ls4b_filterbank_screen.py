#!/usr/bin/env python3
"""Execute the frozen LS4B X-band filterbank screen one scan at a time."""

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
from seti_repeater.light_sail import apply_abacad_veto, search_broadband_events
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
    if start >= stop:
        raise RuntimeError("frozen science band is outside source coverage")
    return start, stop


def verify_detector_inheritance(config: dict, ls1_config_path: Path) -> None:
    ls1 = json.loads(ls1_config_path.read_text(encoding="utf-8"))
    adapted = config["medium_resolution_screen"]
    inherited = ls1["medium_resolution_screen"]
    allowed_changes = {"implementation", "product_suffix", "science_band_mhz"}
    adapted_core = {key: value for key, value in adapted.items() if key not in allowed_changes}
    inherited_core = {key: value for key, value in inherited.items() if key not in allowed_changes}
    if adapted_core != inherited_core:
        raise RuntimeError("LS4B detector core differs from the frozen LS1 detector")


def verify_header_source(config: dict) -> None:
    source = Path(config["archive_header_result"]["source_path"])
    if sha256_file(source) != config["archive_header_result"]["source_sha256"]:
        raise RuntimeError("LS4A header result no longer matches its frozen digest")
    result = json.loads(source.read_text(encoding="utf-8"))
    if result.get("result_sha256") != config["archive_header_result"]["source_result_identity"]:
        raise RuntimeError("LS4A header-result identity changed")
    if result.get("spectral_values_read") is not False:
        raise RuntimeError("LS4A is not a header-only result")
    selected = result.get("selected_for_preregistration", {})
    if selected.get("band") != "X" or not str(selected.get("cadence_url", "")).endswith("--114966"):
        raise RuntimeError("LS4A selection no longer reproduces the frozen X-band cadence")


def parse_and_validate_header(path: Path, scan: dict, config: dict) -> tuple[dict, int]:
    expected_size = int(scan["medium_resolution"]["expected_size_bytes"])
    if path.stat().st_size != expected_size:
        raise RuntimeError(f"source size changed for {scan['label']}")
    with path.open("rb") as handle:
        raw = handle.read(65_536)
    header, data_offset = parse_sigproc_header_bytes(raw)
    expected = config["expected_filterbank_header"]
    exact_fields = ("nchans", "nifs", "nbits")
    for field in exact_fields:
        if int(header[field]) != int(expected[field]):
            raise RuntimeError(f"SIGPROC {field} changed for {scan['label']}")
    float_fields = {
        "fch1": "fch1_mhz",
        "foff": "foff_mhz",
        "tsamp": "tsamp_s",
    }
    for field, expected_field in float_fields.items():
        if not math.isclose(
            float(header[field]), float(expected[expected_field]), rel_tol=0.0, abs_tol=1e-9
        ):
            raise RuntimeError(f"SIGPROC {field} changed for {scan['label']}")
    if data_offset != int(expected["header_bytes"]):
        raise RuntimeError(f"SIGPROC header length changed for {scan['label']}")
    if str(header["source_name"]).casefold() != scan["expected_source_name"].casefold():
        raise RuntimeError(f"source identity changed for {scan['label']}")
    if not math.isclose(
        float(header["tstart"]), float(scan["expected_tstart_mjd"]), rel_tol=0.0, abs_tol=1e-9
    ):
        raise RuntimeError(f"start epoch changed for {scan['label']}")
    row_bytes = int(expected["nchans"]) * int(expected["nifs"]) * int(expected["nbits"]) // 8
    payload_bytes = expected_size - data_offset
    if payload_bytes != int(expected["ntime"]) * row_bytes:
        raise RuntimeError(f"filterbank payload geometry changed for {scan['label']}")
    return header, data_offset


def screen_scan(scan: dict, config: dict, path: Path, source_sha256: str) -> dict[str, Any]:
    header, data_offset = parse_and_validate_header(path, scan, config)
    detector = config["medium_resolution_screen"]
    nchans = int(header["nchans"])
    ntime = int(config["expected_filterbank_header"]["ntime"])
    start, stop = channel_bounds(
        float(header["fch1"]),
        float(header["foff"]),
        nchans,
        float(detector["science_band_mhz"][0]),
        float(detector["science_band_mhz"][1]),
    )
    science_window_bytes = ntime * (stop - start) * 4
    if science_window_bytes > int(config["resource_policy"]["maximum_science_window_bytes_per_scan"]):
        raise RuntimeError("frozen science window exceeds the memory resource gate")
    matrix = np.memmap(
        path,
        dtype="<f4",
        mode="r",
        offset=data_offset,
        shape=(ntime, nchans),
        order="C",
    )
    data = matrix[:, start:stop]
    indices = np.arange(start, stop, dtype=np.float64)
    frequency_mhz = float(header["fch1"]) + indices * float(header["foff"])
    search = search_broadband_events(
        data,
        frequency_mhz,
        float(header["tsamp"]),
        base_bin_channels=int(detector["base_bin_native_channels"]),
        spectral_width_bins=tuple(detector["spectral_width_base_bins"]),
        duration_s=tuple(detector["duration_s"]),
        minimum_score=float(detector["off_veto_score_threshold"]),
        maximum_events=int(detector["maximum_events_per_scan"]),
        clip_low=float(detector["native_robust_clip"][0]),
        clip_high=float(detector["native_robust_clip"][1]),
        minimum_valid_fraction=float(detector["minimum_valid_fraction"]),
    )
    del data
    del matrix
    effective = sorted((float(frequency_mhz[0]), float(frequency_mhz[-1])))
    return {
        "label": scan["label"],
        "role": scan["role"],
        "adjacent_off_labels": scan["adjacent_off_labels"],
        "source_name": str(header["source_name"]),
        "tstart_mjd": float(header["tstart"]),
        "sample_time_s": float(header["tsamp"]),
        "frequency_channel_width_hz": abs(float(header["foff"])) * 1e6,
        "science_channel_start": start,
        "science_channel_stop": stop,
        "science_channel_count": stop - start,
        "science_window_bytes": science_window_bytes,
        "effective_science_band_mhz": effective,
        "source_url": scan["medium_resolution"]["url"],
        "source_size_bytes": int(scan["medium_resolution"]["expected_size_bytes"]),
        "source_sha256": source_sha256,
        "search": search,
    }


def run(config_path: Path, ls1_config_path: Path, data_dir: Path) -> tuple[dict, list[str]]:
    config_raw = config_path.read_bytes()
    config = json.loads(config_raw)
    if config.get("artifact_type") != "seti_repeater.ls4b_preregistration":
        raise RuntimeError("wrong LS4B configuration artifact")
    if config["freeze_boundary"]["medium_resolution_values_read_before_freeze"]:
        raise RuntimeError("LS4B freeze boundary is not prospective")
    verify_detector_inheritance(config, ls1_config_path)
    verify_header_source(config)
    data_dir.mkdir(parents=True, exist_ok=True)
    scans: list[dict[str, Any]] = []
    manifest_lines: list[str] = []
    for scan in config["selected_sequence"]:
        destination = data_dir / f"{scan['label']}.0002.fil"
        expected_size = int(scan["medium_resolution"]["expected_size_bytes"])
        required_free = expected_size + int(
            config["resource_policy"]["minimum_free_headroom_bytes_after_download"]
        )
        if shutil.disk_usage(data_dir).free < required_free:
            raise RuntimeError(f"insufficient free disk before {scan['label']}")
        try:
            source_sha256 = fetch(scan, destination)
            manifest_lines.append(f"{source_sha256}  {destination.as_posix()}")
            scans.append(screen_scan(scan, config, destination, source_sha256))
            print(
                f"screened {scan['label']} with {len(scans[-1]['search']['events'])} retained events",
                flush=True,
            )
        finally:
            destination.unlink(missing_ok=True)
            destination.with_suffix(destination.suffix + ".part").unlink(missing_ok=True)
        if destination.exists():
            raise RuntimeError(f"raw file was not deleted after {scan['label']}")
    detector = config["medium_resolution_screen"]
    candidates = apply_abacad_veto(
        scans,
        on_threshold=float(detector["on_score_threshold"]),
        off_threshold=float(detector["off_veto_score_threshold"]),
        minimum_frequency_overlap=float(detector["off_veto_frequency_overlap"]),
    )
    survivors = [item for item in candidates if item["survives_adjacent_off_veto"]]
    truncated = any(scan["search"]["retention_truncated"] for scan in scans)
    if truncated:
        status = "invalid-retention-truncated"
    elif survivors:
        status = "screen-complete-followup-preregistration-required"
    else:
        status = "screen-complete-no-surviving-events"
    result: dict[str, Any] = {
        "artifact_type": "seti_repeater.ls4b_medium_resolution_screen",
        "schema_version": 1,
        "status": status,
        "config_sha256": hashlib.sha256(config_raw).hexdigest(),
        "selected_band": "X",
        "selected_cadence_id": "--114966",
        "target": config["target"],
        "geometry": config["geometry"],
        "science_band_mhz": detector["science_band_mhz"],
        "scans": scans,
        "on_threshold_event_count": len(candidates),
        "surviving_event_count": len(survivors),
        "candidates": candidates,
        "high_time_resolution_followup_preregistration_required": bool(survivors) and not truncated,
        "high_time_resolution_values_read": False,
        "spectral_dataset_values_read": True,
        "raw_files_deleted_after_each_scan": True,
        "raw_spectral_payload_published": False,
        "score_is_calibrated_significance": False,
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
        "--ls1-config", type=Path, default=Path("config/ls1_hd219134_light_sail.json")
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data_ls4b"))
    parser.add_argument("--output", type=Path, default=Path("results_ls4b/screen.json"))
    parser.add_argument("--manifest", type=Path, default=Path("DATA_MANIFEST_LS4B.sha256"))
    args = parser.parse_args()
    result, manifest_lines = run(args.config, args.ls1_config, args.data_dir)
    atomic_write(args.output, canonical_json_bytes(result))
    atomic_write(args.manifest, ("\n".join(manifest_lines) + "\n").encode("utf-8"))
    print(canonical_json_bytes(result).decode("utf-8"))


if __name__ == "__main__":
    main()
