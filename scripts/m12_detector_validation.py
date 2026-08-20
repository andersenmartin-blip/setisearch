#!/usr/bin/env python3
"""Run the preregistered v0.5 vetoes on the labelled M11 development set."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from seti_repeater.candidates import (
    annotate_local_off_vetoes,
    annotate_receiver_frame_aliases,
    apply_candidate_flags,
)
from seti_repeater.search import (
    build_bank,
    load_scan,
    make_rest_grid,
    make_subsets,
    make_templates,
)
from seti_repeater.sigproc import extract_frequency_window
from seti_repeater.spectral import make_spectral_bank, validate_widths


DEVELOPMENT_WINDOWS = ("m11_1400p5", "m11_1425p0")
FORMAL_SURVIVOR = "survives_for_followup"
FAMILY_REVIEW = "rfi_family_veto_pending_manual_review"
V0P5_SETTINGS = {
    "local_off_tolerance_hz": 20.0,
    "single_epoch_snr_floor": 5.5,
    "receiver_local_half_width_hz": 100.0,
    "receiver_alias_tolerance_hz": 20.0,
    "receiver_alias_minimum_shared_epochs": 2,
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def extract_development_windows(config: dict, data_dir: Path, workers: int) -> None:
    for window in config["windows"]:
        if window["id"] not in DEVELOPMENT_WINDOWS:
            continue
        for scan in config["scans"]:
            output = data_dir / window["id"] / f"{scan['label']}.npz"
            if output.exists():
                continue
            print(f"extract {window['id']} {scan['label']}", flush=True)
            extract_frequency_window(
                scan["url"], window["fmin_mhz"], window["fmax_mhz"], output,
                workers=workers,
            )


def validate_window(
    window: dict,
    config: dict,
    frozen_summary: dict,
    data_dir: Path,
    operational_threshold: float,
) -> list[dict]:
    window_id = window["id"]
    scans_by_kind = {}
    for kind in ("on", "off"):
        definitions = sorted(
            (scan for scan in config["scans"] if scan["kind"] == kind),
            key=lambda item: item["epoch"],
        )
        scans_by_kind[kind] = [
            load_scan(data_dir / window_id / f"{scan['label']}.npz")
            for scan in definitions
        ]

    templates = make_templates(config)
    subsets = make_subsets(3, config["search"]["minimum_active_epochs"])
    widths = validate_widths(config["search"]["spectral_widths_channels"])
    minimum_active_epoch_snr = config["search"].get("minimum_active_epoch_snr")
    stack_statistic = config["search"].get("stack_statistic", "sum")
    first_scan = scans_by_kind["on"][0]
    channel_width_mhz = abs(float(
        first_scan["frequency_mhz"][1] - first_scan["frequency_mhz"][0]
    ))
    rest_grid = make_rest_grid(window, channel_width_mhz)

    off_bank, _ = build_bank(
        scans_by_kind["off"], rest_grid, window["rest_center_mhz"], templates, config
    )
    off_spectral = make_spectral_bank(off_bank, widths)

    frozen_reduction = frozen_summary["windows"][window_id]["candidate_reduction"]
    frozen_clusters = frozen_reduction["clusters"]
    clusters = copy.deepcopy(frozen_clusters)
    annotate_local_off_vetoes(
        clusters, off_spectral, rest_grid, templates, subsets, widths,
        V0P5_SETTINGS["local_off_tolerance_hz"],
        V0P5_SETTINGS["single_epoch_snr_floor"],
        minimum_active_epoch_snr, stack_statistic,
    )
    annotate_receiver_frame_aliases(
        clusters, scans_by_kind["on"], config,
        V0P5_SETTINGS["receiver_local_half_width_hz"],
        V0P5_SETTINGS["receiver_alias_tolerance_hz"],
        V0P5_SETTINGS["receiver_alias_minimum_shared_epochs"],
        V0P5_SETTINGS["single_epoch_snr_floor"],
    )
    reporting = config["search"]["candidate_reporting"]
    apply_candidate_flags(
        clusters, frozen_reduction["arithmetic_frequency_families"],
        operational_threshold, reporting["template_multiplicity_flag"],
    )

    records = []
    for index, (frozen, revised) in enumerate(zip(frozen_clusters, clusters)):
        if frozen["disposition"] not in (FORMAL_SURVIVOR, FAMILY_REVIEW):
            continue
        records.append({
            "window_id": window_id,
            "frozen_cluster_index": index,
            "frequency_mhz": float(frozen["cluster_frequency_mhz"]),
            "max_snr": float(frozen["max_snr"]),
            "frozen_disposition": frozen["disposition"],
            "v0p5_disposition": revised["disposition"],
            "v0p5_flags": revised["flags"],
            "best_hypothesis": revised["best_hypothesis"],
            "v0p5_off_diagnostics": revised["v0p5_off_diagnostics"],
            "v0p5_receiver_frame_signature": revised["v0p5_receiver_frame_signature"],
            "v0p5_receiver_frame_aliases": revised["v0p5_receiver_frame_aliases"],
        })
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config/lhs1140b_new_target_m11.json"))
    parser.add_argument("--summary", type=Path, default=Path("results_m11/search_summary.json"))
    parser.add_argument("--data-dir", type=Path, default=Path("data_m12_validation"))
    parser.add_argument("--output", type=Path, default=Path("results_m12/development_validation.json"))
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()

    config = read_json(args.config)
    frozen_summary = read_json(args.summary)
    if args.extract:
        extract_development_windows(config, args.data_dir, args.workers)

    operational_threshold = float(
        frozen_summary["global_result"]["operational_threshold_snr"]
    )
    records = []
    for window in config["windows"]:
        if window["id"] in DEVELOPMENT_WINDOWS:
            print(f"validate {window['id']}", flush=True)
            records.extend(validate_window(
                window, config, frozen_summary, args.data_dir, operational_threshold
            ))

    formal = [item for item in records if item["frozen_disposition"] == FORMAL_SURVIVOR]
    families = [item for item in records if item["frozen_disposition"] == FAMILY_REVIEW]
    formal_all_vetoed = len(formal) == 5 and all(
        item["v0p5_disposition"].startswith("rfi_veto_") for item in formal
    )
    families_conservative = len(families) == 16 and all(
        item["v0p5_disposition"] != "survives_for_followup" for item in families
    )
    disposition_counts: dict[str, int] = {}
    for item in records:
        disposition = item["v0p5_disposition"]
        disposition_counts[disposition] = disposition_counts.get(disposition, 0) + 1
    result = {
        "milestone": 12,
        "purpose": "labelled detector-development validation; not independent evidence",
        "detector_version": "0.5.0-development",
        "source_detector_version": frozen_summary["pipeline"]["version"],
        "operational_threshold_snr": operational_threshold,
        "settings": V0P5_SETTINGS,
        "development_set": {
            "formal_survivors": len(formal),
            "arithmetic_family_review_clusters": len(families),
            "total": len(records),
        },
        "disposition_counts": disposition_counts,
        "acceptance": {
            "exactly_five_formal_survivors": len(formal) == 5,
            "all_formal_survivors_vetoed": formal_all_vetoed,
            "exactly_sixteen_family_review_clusters": len(families) == 16,
            "family_review_clusters_not_silently_promoted": families_conservative,
            "passed": bool(formal_all_vetoed and families_conservative),
        },
        "candidates": records,
    }
    write_json(args.output, result)
    print(json.dumps({
        "development_set": result["development_set"],
        "disposition_counts": disposition_counts,
        "acceptance": result["acceptance"],
    }, indent=2), flush=True)
    if not result["acceptance"]["passed"]:
        raise SystemExit("M12 development validation did not pass preregistered acceptance")


if __name__ == "__main__":
    main()
