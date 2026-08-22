#!/usr/bin/env python3
"""Fixed post-hoc morphology checks for the two Milestone 16 review cases.

The implementation reuses the already published Milestone 11 local-cutout
measurements without modifying that historical script.  It combines the
Milestone 16 automated survivor and manual arithmetic-family case so that the
fixed cross-candidate receiver-frame-alias check is evaluated across both.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from m11_candidate_investigation import (
    LOCAL_HALF_WIDTH_HZ,
    LOCAL_PEAK_FLOOR,
    COINCIDENCE_TOLERANCE_HZ,
    add_coincidences,
    add_cross_candidate_aliases,
    analyse_scan,
    extract_needed,
    find_survivors,
    load_scan,
    plot_candidate,
    read_json,
    write_json,
)


SELECTED_DISPOSITIONS = (
    ("survives_for_followup", 1),
    ("rfi_family_veto_pending_manual_review", 1),
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/hd219134h_heldout_m16.json"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results_m16/search_summary.json"),
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data_m16_candidate_investigation"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results_m16_candidate_investigation"),
    )
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--date-utc", default="2026-08-22")
    args = parser.parse_args()

    config = read_json(args.config)
    summary = read_json(args.summary)
    selected = []
    for disposition, expected_count in SELECTED_DISPOSITIONS:
        records = find_survivors(
            summary,
            config["windows"],
            disposition=disposition,
            expected_count=expected_count,
        )
        for record in records:
            record["original_disposition"] = disposition
        selected.extend(records)
    selected.sort(key=lambda item: -float(item["cluster"]["max_snr"]))

    if args.extract:
        extract_needed(
            config,
            args.data_dir,
            {item["window_id"] for item in selected},
            args.workers,
        )

    output_candidates = []
    csv_rows = []
    for ordinal, selected_record in enumerate(selected, 1):
        cluster = selected_record["cluster"]
        best = cluster["best_hypothesis"]
        candidate = {
            "ordinal": ordinal,
            "window_id": selected_record["window_id"],
            "frozen_original_disposition": selected_record["original_disposition"],
            "frozen_cluster_max_snr": float(cluster["max_snr"]),
            "frozen_cluster_member_count": int(cluster["member_count"]),
            "frozen_cluster_frequency_span_hz": float(cluster["frequency_span_hz"]),
            "frozen_flags": cluster.get("flags", []),
            "frozen_frequency_family_ids": cluster.get("frequency_family_ids", []),
            "frozen_off_at_best_hypothesis_snr": cluster.get(
                "off_at_best_hypothesis_snr"
            ),
            "best_hypothesis": best,
            "scans": {},
            "_plots": {},
        }
        for scan_config in config["scans"]:
            path = (
                args.data_dir
                / selected_record["window_id"]
                / f"{scan_config['label']}.npz"
            )
            scan = load_scan(path)
            metrics, plot = analyse_scan(scan, best, config)
            metrics["kind"] = scan_config["kind"]
            metrics["epoch"] = int(scan_config["epoch"])
            candidate["scans"][scan_config["label"]] = metrics
            candidate["_plots"][scan_config["label"]] = plot
            csv_rows.append(
                {
                    "candidate_ordinal": ordinal,
                    "frozen_original_disposition": selected_record[
                        "original_disposition"
                    ],
                    "rest_frequency_mhz": float(best["frequency_mhz"]),
                    "window_id": selected_record["window_id"],
                    "scan": scan_config["label"],
                    "kind": scan_config["kind"],
                    "epoch": scan_config["epoch"],
                    "width_channels": int(best["spectral_width_channels"]),
                    **{
                        key: value
                        for key, value in metrics.items()
                        if isinstance(value, (int, float))
                    },
                }
            )
        add_coincidences(candidate)
        slug = (
            f"candidate_{ordinal}_{float(best['frequency_mhz']):.6f}MHz"
        ).replace(".", "p")
        plot_candidate(candidate, args.output_dir / f"{slug}.png")
        candidate.pop("_plots")
        output_candidates.append(candidate)

    add_cross_candidate_aliases(output_candidates)

    archive = {
        "scope": "not run in this fixed morphology stage",
        "independent_cadence_found_by_prior_header_screen": True,
        "interpretation": (
            "The corrected Milestone 16 header-only screen already identified "
            "additional qualifying HD 219134 cadences. Selection and spectral "
            "testing are deferred until this morphology result is published."
        ),
    }
    result = {
        "analysis_label": "post-hoc candidate investigation",
        "detector_status": (
            f"frozen v{config['project'].get('detector_version_frozen', '0.5.0')}; "
            "no search or threshold setting changed"
        ),
        "date_utc": args.date_utc,
        "selected_frozen_dispositions": [item[0] for item in SELECTED_DISPOSITIONS],
        "local_half_width_hz": LOCAL_HALF_WIDTH_HZ,
        "receiver_frame_coincidence_tolerance_hz": COINCIDENCE_TOLERANCE_HZ,
        "local_peak_floor_snr": LOCAL_PEAK_FLOOR,
        "candidate_count": len(output_candidates),
        "candidates": output_candidates,
        "archive_cross_cadence_search": archive,
        "interpretive_limit": (
            "These targeted checks can identify terrestrial or instrumental "
            "coincidences but cannot increase the frozen search significance. "
            "Any surviving unresolved feature still needs an independent cadence."
        ),
    }
    write_json(args.output_dir / "candidate_investigation.json", result)
    write_json(args.output_dir / "archive_cross_cadence_search.json", archive)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "scan_metrics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=sorted({key for row in csv_rows for key in row}),
        )
        writer.writeheader()
        writer.writerows(csv_rows)

    print(
        json.dumps(
            {
                "candidate_count": len(output_candidates),
                "classifications": [
                    item["posthoc_classification"] for item in output_candidates
                ],
                "independent_cadence_known": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
