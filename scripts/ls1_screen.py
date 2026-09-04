#!/usr/bin/env python3
"""Execute the frozen LS1 medium-resolution ABACAD broadband screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from seti_repeater.light_sail import apply_abacad_veto, search_broadband_events
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
    if start >= stop:
        raise RuntimeError("frozen science band is outside source coverage")
    return start, stop


def screen_scan(scan: dict, config: dict, path: Path) -> dict[str, Any]:
    import h5py
    import hdf5plugin  # noqa: F401  Register archive compression filters.

    expected_size = int(scan["medium_resolution"]["expected_size_bytes"])
    if path.stat().st_size != expected_size:
        raise RuntimeError(f"source size changed for {scan['label']}")
    source_sha256 = sha256_file(path)
    detector = config["medium_resolution_screen"]
    with h5py.File(path, "r") as handle:
        dataset = handle["data"]
        attrs = {
            **{key: json_value(value) for key, value in handle.attrs.items()},
            **{key: json_value(value) for key, value in dataset.attrs.items()},
        }
        if len(dataset.shape) != 3 or dataset.shape[1] != 1:
            raise RuntimeError("unexpected HDF5 dynamic-spectrum geometry")
        source_name = str(attrs["source_name"])
        if source_name.casefold() != scan["expected_source_name"].casefold():
            raise RuntimeError(f"source identity changed for {scan['label']}")
        tstart_mjd = float(attrs["tstart"])
        if abs(tstart_mjd - float(scan["expected_tstart_mjd"])) > 2.0 / 86_400.0:
            raise RuntimeError(f"start epoch changed for {scan['label']}")
        sample_time_s = float(attrs["tsamp"])
        fch1_mhz = float(attrs["fch1"])
        foff_mhz = float(attrs["foff"])
        if not 0.5 <= sample_time_s <= 2.0:
            raise RuntimeError("medium-resolution time sampling is outside frozen class")
        if not 0.001 <= abs(foff_mhz) <= 0.005:
            raise RuntimeError("medium-resolution channel width is outside frozen class")
        start, stop = channel_bounds(
            fch1_mhz,
            foff_mhz,
            int(dataset.shape[-1]),
            float(detector["science_band_mhz"][0]),
            float(detector["science_band_mhz"][1]),
        )
        data = np.asarray(dataset[:, 0, start:stop], dtype=np.float32)
        indices = np.arange(start, stop, dtype=np.float64)
        frequency_mhz = fch1_mhz + indices * foff_mhz
    search = search_broadband_events(
        data,
        frequency_mhz,
        sample_time_s,
        base_bin_channels=int(detector["base_bin_native_channels"]),
        spectral_width_bins=tuple(detector["spectral_width_base_bins"]),
        duration_s=tuple(detector["duration_s"]),
        minimum_score=float(detector["off_veto_score_threshold"]),
        maximum_events=int(detector["maximum_events_per_scan"]),
        clip_low=float(detector["native_robust_clip"][0]),
        clip_high=float(detector["native_robust_clip"][1]),
        minimum_valid_fraction=float(detector["minimum_valid_fraction"]),
    )
    return {
        "label": scan["label"],
        "role": scan["role"],
        "adjacent_off_labels": scan["adjacent_off_labels"],
        "source_name": source_name,
        "tstart_mjd": tstart_mjd,
        "sample_time_s": sample_time_s,
        "frequency_channel_width_hz": abs(foff_mhz) * 1e6,
        "science_channel_start": start,
        "science_channel_stop": stop,
        "source_url": scan["medium_resolution"]["url"],
        "source_size_bytes": expected_size,
        "source_sha256": source_sha256,
        "search": search,
    }


def run(config_path: Path, data_dir: Path) -> dict[str, Any]:
    config_raw = config_path.read_bytes()
    config = json.loads(config_raw)
    if config["freeze_boundary"]["medium_resolution_values_read_before_freeze"]:
        raise RuntimeError("LS1 freeze boundary is not prospective")
    scans = [
        screen_scan(scan, config, data_dir / f"{scan['label']}.0002.h5")
        for scan in config["selected_sequence"]
    ]
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
        status = "screen-complete-followup-required"
    else:
        status = "screen-complete-no-surviving-events"
    result: dict[str, Any] = {
        "artifact_type": "seti_repeater.ls1_medium_resolution_screen",
        "schema_version": 1,
        "status": status,
        "config_sha256": hashlib.sha256(config_raw).hexdigest(),
        "selected_cadence_id": config["archive_inventory"]["selected_cadence_id"],
        "scans": scans,
        "on_threshold_event_count": len(candidates),
        "surviving_event_count": len(survivors),
        "candidates": candidates,
        "high_time_resolution_followup_authorized": bool(survivors) and not truncated,
        "spectral_dataset_values_read": True,
        "raw_spectral_payload_published": False,
        "score_is_calibrated_significance": False,
        "technosignature_claimed": False,
    }
    result["result_sha256"] = hashlib.sha256(canonical_json_bytes(result)).hexdigest()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--data-dir", type=Path, default=Path("data_ls1"))
    parser.add_argument("--output", type=Path, default=Path("results_ls1/screen.json"))
    args = parser.parse_args()
    result = run(args.config, args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(f".{args.output.name}.tmp-{os.getpid()}")
    temporary.write_bytes(canonical_json_bytes(result))
    os.replace(temporary, args.output)
    print(canonical_json_bytes(result).decode("utf-8"))


if __name__ == "__main__":
    main()
