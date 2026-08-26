#!/usr/bin/env python3
"""Prove M36 extraction coverage including the widest spectral template.

This preflight uses only configuration values and previously verified HDF5
header geometry. It never opens a remote file or reads spectral samples.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from astropy.time import Time

from m13_hdf5_extract import channel_bounds
from seti_repeater.orbit import (
    DAY_S,
    celestial_frequency_factor,
    make_location,
    make_target,
)
from seti_repeater.search import make_rest_grid, make_subsets, make_templates
from seti_repeater.spectral import validate_widths


def extraction_geometry(scan: dict, window: dict) -> dict:
    header = scan["expected_header"]
    fch1 = float(header["fch1_mhz"])
    foff = float(header["foff_mhz"])
    nchans = int(header["dataset_shape"][-1])
    start, stop = channel_bounds(
        fch1,
        foff,
        nchans,
        float(window["fmin_mhz"]),
        float(window["fmax_mhz"]),
    )
    first = fch1 + start * foff
    last = fch1 + (stop - 1) * foff
    low, high = sorted((first, last))
    return {
        "channel_start": start,
        "channel_stop": stop,
        "channel_count": stop - start,
        "frequency_low_mhz": low,
        "frequency_high_mhz": high,
        "channel_width_mhz": abs(foff),
    }


def check_config(config: dict) -> dict:
    target = make_target(config["target"])
    location = make_location(config["observatory"])
    templates = make_templates(config)
    widths = validate_widths(config["search"]["spectral_widths_channels"])
    spectral_half_width = max(widths) // 2
    on_scan_count = sum(scan["kind"] == "on" for scan in config["scans"])
    subsets = make_subsets(
        on_scan_count,
        int(config["search"]["minimum_active_epochs"]),
    )
    reporting = config["search"]["candidate_reporting"]
    maximum_hypothesis_peaks = (
        len(templates)
        * len(subsets)
        * len(widths)
        * int(reporting["peaks_per_hypothesis"])
    )
    report_cap = int(reporting["max_report_clusters"])
    report_cap_nontruncating = report_cap >= maximum_hypothesis_peaks
    records = []
    overall_passed = report_cap_nontruncating

    for window in config["windows"]:
        window_records = []
        for scan in config["scans"]:
            header = scan["expected_header"]
            geometry = extraction_geometry(scan, window)
            df_mhz = geometry["channel_width_mhz"]
            frequencies_zero = geometry["frequency_low_mhz"]
            nfreq = geometry["channel_count"]
            rest_grid = make_rest_grid(window, df_mhz)
            times = Time(
                float(header["tstart_mjd"])
                + (np.arange(int(header["dataset_shape"][0])) + 0.5)
                * float(header["tsamp_s"])
                / DAY_S,
                format="mjd",
                scale="utc",
            )
            template_records = []
            for template_index, (scale, phase) in enumerate(templates):
                factor, observer, planet = celestial_frequency_factor(
                    times,
                    scale,
                    phase,
                    target,
                    location,
                    config["orbit"],
                )
                observed_track = float(window["rest_center_mhz"]) * factor
                reference_indices = np.rint(
                    (observed_track - frequencies_zero) / df_mhz
                ).astype(int)
                shifts = reference_indices - reference_indices[0]
                dedoppler_margin = int(np.max(np.abs(shifts)))
                total_margin = dedoppler_margin + spectral_half_width
                observed_needed = rest_grid * factor[0]
                indices = np.rint(
                    (observed_needed - frequencies_zero) / df_mhz
                ).astype(int)
                lower_headroom = int(indices.min() - total_margin)
                upper_headroom = int(nfreq - total_margin - 1 - indices.max())
                passed = lower_headroom >= 0 and upper_headroom >= 0
                overall_passed &= passed
                template_records.append({
                    "template_index": template_index,
                    "projected_scale": scale,
                    "phase_offset_cycles": phase,
                    "passed": bool(passed),
                    "dedoppler_margin_channels": dedoppler_margin,
                    "spectral_half_width_channels": spectral_half_width,
                    "total_margin_channels": total_margin,
                    "lower_headroom_channels": lower_headroom,
                    "upper_headroom_channels": upper_headroom,
                    "observer_start_m_s": float(observer[0]),
                    "planet_start_m_s": float(planet[0]),
                    "frequency_factor_start": float(factor[0]),
                })
            window_records.append({
                "scan_label": scan["label"],
                "source_name": header["source_name"],
                "extraction_geometry": geometry,
                "minimum_lower_headroom_channels": min(
                    item["lower_headroom_channels"] for item in template_records
                ),
                "minimum_upper_headroom_channels": min(
                    item["upper_headroom_channels"] for item in template_records
                ),
                "templates": template_records,
            })
        records.append({
            "window_id": window["id"],
            "passed": all(
                all(item["passed"] for item in scan["templates"])
                for scan in window_records
            ),
            "scans": window_records,
        })

    return {
        "purpose": (
            "M36 metadata-only motion and spectral-width extraction coverage proof"
        ),
        "spectral_payload_inspected": False,
        "remote_files_opened": False,
        "detector_version": config["project"]["detector_version_frozen"],
        "spectral_width_bank_channels": list(widths),
        "spectral_half_width_channels": spectral_half_width,
        "template_count": len(templates),
        "activity_subset_count": len(subsets),
        "peaks_per_hypothesis": int(reporting["peaks_per_hypothesis"]),
        "maximum_hypothesis_peaks_per_window": maximum_hypothesis_peaks,
        "candidate_report_cap": report_cap,
        "candidate_report_cap_nontruncating": report_cap_nontruncating,
        "scan_count": len(config["scans"]),
        "window_count": len(config["windows"]),
        "checks": len(templates) * len(config["scans"]) * len(config["windows"]),
        "passed": bool(overall_passed),
        "windows": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    config = json.loads(args.config.read_text())
    result = check_config(config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "passed": result["passed"],
        "checks": result["checks"],
        "spectral_width_bank_channels": result["spectral_width_bank_channels"],
        "maximum_hypothesis_peaks_per_window": (
            result["maximum_hypothesis_peaks_per_window"]
        ),
        "candidate_report_cap": result["candidate_report_cap"],
        "candidate_report_cap_nontruncating": (
            result["candidate_report_cap_nontruncating"]
        ),
        "windows": [
            {"window_id": item["window_id"], "passed": item["passed"]}
            for item in result["windows"]
        ],
    }, indent=2))
    if not result["passed"]:
        raise SystemExit("Extraction coverage preflight failed")


if __name__ == "__main__":
    main()
