#!/usr/bin/env python3
"""Fixed post-hoc morphology check for the Milestone 20 review case.

The implementation reuses the published Milestone 11 local-cutout
measurements without modifying the historical script. Only the one frozen
Milestone 20 arithmetic-family case is selected.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from m18_candidate_investigation import (
    COINCIDENCE_TOLERANCE_HZ,
    LOCAL_HALF_WIDTH_HZ,
    LOCAL_PEAK_FLOOR,
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


SELECTED_DISPOSITION = "rfi_family_veto_pending_manual_review"
EXPECTED_COUNT = 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/rhocrbc_heldout_m20.json"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results_m20/search_summary.json"),
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data_m20_candidate_investigation"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results_m20_candidate_investigation"),
    )
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--date-utc", default="2026-08-22")
    args = parser.parse_args()

    config = read_json(args.config)
    summary = read_json(args.summary)
    selected = find_survivors(
        summary,
        config["windows"],
        disposition=SELECTED_DISPOSITION,
        expected_count=EXPECTED_COUNT,
    )

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
            "frozen_original_disposition": SELECTED_DISPOSITION,
            "frozen_cluster_max_snr": float(cluster["max_snr"]),
            "frozen_cluster_member_count": int(cluster["member_count"]),
            "frozen_cluster_frequency_span_hz": float(
                cluster["frequency_span_hz"]
            ),
            "frozen_flags": cluster.get("flags", []),
            "frozen_frequency_family_ids": cluster.get(
                "frequency_family_ids", []
            ),
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
                    "frozen_original_disposition": SELECTED_DISPOSITION,
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
        "independent_cadence_found_by_prior_header_screen": False,
        "interpretation": (
            "The frozen Milestone 20 header-only screen found no second "
            "qualifying rho CrB cadence. Any unresolved case still requires "
            "a later independent public observation."
        ),
    }
    result = {
        "analysis_label": "Milestone 20 post-hoc candidate investigation",
        "detector_status": (
            f"frozen v{config['project'].get('detector_version_frozen', '0.5.0')}; "
            "no search or threshold setting changed"
        ),
        "date_utc": args.date_utc,
        "selected_frozen_disposition": SELECTED_DISPOSITION,
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
                "independent_cadence_known": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
