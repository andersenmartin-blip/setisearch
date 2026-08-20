#!/usr/bin/env python3
"""Targeted follow-up of three M14 candidates in a partial independent cadence.

This is a labelled post-hoc persistence check, not a rerun of the frozen
detector and not a new blind search.  The candidate hypotheses and disposition
rules are fixed in MILESTONE_14_INDEPENDENT_CADENCE_PLAN.md.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from m11_candidate_investigation import (
    COINCIDENCE_TOLERANCE_HZ,
    LOCAL_PEAK_FLOOR,
    analyse_scan,
    closest_peak,
    read_json,
    write_json,
)
from m13_hdf5_extract import extract_scan
from seti_repeater.search import load_scan


FROZEN_CANDIDATES = {
    1: (1425.3152769058943, 1.0, 0.1, 9, 19),
    3: (1425.1348843798041, 1.0, -0.1, 9, 17),
    5: (1425.3288304433227, 0.25, 0.2, 9, 5),
}
ON_LABELS = ("independent_on1", "independent_on2")
OFF_LABELS = ("independent_off1", "independent_off_late")


def select_candidates(investigation: dict) -> list[dict]:
    candidates = [
        item for item in investigation["candidates"]
        if item["posthoc_classification"]
        == "UNRESOLVED_REQUIRES_INDEPENDENT_CADENCE"
    ]
    if [int(item["ordinal"]) for item in candidates] != [1, 3, 5]:
        raise RuntimeError("The fixed unresolved candidate set changed")
    for item in candidates:
        best = item["best_hypothesis"]
        observed = (
            float(best["frequency_mhz"]),
            float(best["projected_scale"]),
            float(best["phase_offset_cycles"]),
            int(best["spectral_width_channels"]),
            int(best["template_index"]),
        )
        expected = FROZEN_CANDIDATES[int(item["ordinal"])]
        if observed != expected:
            raise RuntimeError(
                f"Candidate {item['ordinal']} hypothesis changed: "
                f"{observed!r} != {expected!r}"
            )
    return candidates


def classify(candidate: dict) -> None:
    comparisons = []
    for on_label in ON_LABELS:
        on = candidate["scans"][on_label]
        on_frequency = float(on["best_stationary_frequency_mhz"])
        for off_label in OFF_LABELS:
            off = candidate["scans"][off_label]
            nearest = closest_peak(
                off["stationary_peaks_snr_ge_5p5"], on_frequency
            )
            comparisons.append({
                "on_scan": on_label,
                "off_scan": off_label,
                "on_peak_frequency_mhz": on_frequency,
                "on_peak_snr": float(on["best_stationary_snr"]),
                "nearest_off_peak": nearest,
                "within_20_hz": bool(
                    nearest is not None
                    and abs(float(nearest["delta_hz"]))
                    <= COINCIDENCE_TOLERANCE_HZ
                ),
                "off_candidate_track_snr": float(
                    off["candidate_track_snr"]
                ),
                "off_candidate_track_snr_ge_5p5": bool(
                    float(off["candidate_track_snr"])
                    >= LOCAL_PEAK_FLOOR
                ),
                "off_is_adjacent": off_label == "independent_off1",
            })
    candidate["receiver_frame_on_off_checks"] = comparisons
    on_recurrence = {
        label: bool(
            float(candidate["scans"][label]["candidate_track_snr"]) >= 3.0
        )
        for label in ON_LABELS
    }
    candidate["on_candidate_track_snr_ge_3"] = on_recurrence
    reasons = []
    if any(item["within_20_hz"] for item in comparisons):
        reasons.append("OFF_peak_within_20_Hz_of_ON_peak")
    if any(
        item["off_candidate_track_snr_ge_5p5"] for item in comparisons
    ):
        reasons.append("OFF_same_candidate_track_SNR_ge_5p5")
    if reasons:
        classification = "RFI_OR_INSTRUMENTAL"
    elif all(on_recurrence.values()):
        classification = (
            "PERSISTS_IN_PARTIAL_INDEPENDENT_CADENCE_"
            "REQUIRES_FURTHER_FOLLOWUP"
        )
    else:
        classification = "NOT_REDETECTED_IN_PARTIAL_INDEPENDENT_CADENCE"
    candidate["followup_reasons"] = reasons
    candidate["followup_classification"] = classification


def plot_candidate(candidate: dict, output: Path) -> None:
    labels = (*ON_LABELS[:1], *OFF_LABELS[:1], *ON_LABELS[1:], *OFF_LABELS[1:])
    fig, axes = plt.subplots(
        len(labels), 2, figsize=(12, 10), constrained_layout=True,
        gridspec_kw={"width_ratios": [3.2, 1.2]},
    )
    image = None
    for row, label in enumerate(labels):
        plot = candidate["_plots"][label]
        metrics = candidate["scans"][label]
        frequency = plot["frequency_mhz"]
        offsets = (frequency - metrics["predicted_mid_mhz"]) * 1e6
        image = axes[row, 0].imshow(
            plot["normalized"], aspect="auto", origin="lower",
            extent=[offsets[0], offsets[-1], 0, plot["normalized"].shape[0]],
            interpolation="nearest", cmap="viridis", vmin=-2.5,
            vmax=min(12.0, float(np.nanpercentile(plot["normalized"], 99.8))),
        )
        track_offsets = (
            plot["track_mhz"] - metrics["predicted_mid_mhz"]
        ) * 1e6
        axes[row, 0].plot(
            track_offsets,
            np.arange(track_offsets.size) + 0.5,
            color="white", lw=0.8,
        )
        axes[row, 0].set_ylabel(label)
        axes[row, 0].set_xlabel("offset from predicted midpoint (Hz)")
        axes[row, 1].plot(plot["stationary_spectrum"], offsets, lw=0.8)
        axes[row, 1].axhline(0, color="black", lw=0.5, alpha=0.5)
        axes[row, 1].set_xlabel("stationary S/N")
        axes[row, 1].set_ylabel("offset (Hz)")
    if image is not None:
        fig.colorbar(
            image, ax=axes[:, 0],
            label="robust per-row normalized power", shrink=0.55,
        )
    best = candidate["best_hypothesis"]
    fig.suptitle(
        f"Partial independent-cadence follow-up: "
        f"{best['frequency_mhz']:.9f} MHz; width "
        f"{best['spectral_width_channels']} ch",
        fontsize=12,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path,
        default=Path("config/gj687b_m14_partial_independent_followup.json"),
    )
    parser.add_argument(
        "--investigation", type=Path,
        default=Path(
            "results_m14_candidate_investigation/candidate_investigation.json"
        ),
    )
    parser.add_argument(
        "--data-dir", type=Path,
        default=Path("data_m14_independent_followup"),
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("results_m14_independent_followup"),
    )
    parser.add_argument("--extract", action="store_true")
    args = parser.parse_args()

    config = read_json(args.config)
    if config["project"]["status"] != "frozen_before_independent_spectral_contact":
        raise RuntimeError("Independent follow-up config is not frozen")
    candidates = select_candidates(read_json(args.investigation))
    window = config["windows"][0]
    if args.extract:
        for scan_config in config["scans"]:
            print(f"extract {scan_config['label']}", flush=True)
            extract_scan(scan_config, [window], args.data_dir)

    output_candidates = []
    csv_rows = []
    for original in candidates:
        best = original["best_hypothesis"]
        candidate = {
            "original_ordinal": int(original["ordinal"]),
            "original_posthoc_classification": original[
                "posthoc_classification"
            ],
            "best_hypothesis": best,
            "scans": {},
            "_plots": {},
        }
        for scan_config in config["scans"]:
            path = (
                args.data_dir / window["id"]
                / f"{scan_config['label']}.npz"
            )
            metrics, plot = analyse_scan(load_scan(path), best, config)
            metrics["kind"] = scan_config["kind"]
            metrics["epoch"] = int(scan_config["epoch"])
            candidate["scans"][scan_config["label"]] = metrics
            candidate["_plots"][scan_config["label"]] = plot
            csv_rows.append({
                "original_candidate_ordinal": int(original["ordinal"]),
                "rest_frequency_mhz": float(best["frequency_mhz"]),
                "scan": scan_config["label"],
                "kind": scan_config["kind"],
                "width_channels": int(best["spectral_width_channels"]),
                **{
                    key: value for key, value in metrics.items()
                    if isinstance(value, (int, float))
                },
            })
        classify(candidate)
        slug = (
            f"candidate_{candidate['original_ordinal']}_"
            f"{float(best['frequency_mhz']):.6f}MHz"
        ).replace(".", "p")
        plot_candidate(candidate, args.output_dir / f"{slug}.png")
        candidate.pop("_plots")
        output_candidates.append(candidate)

    result = {
        "analysis_label": "targeted partial independent-cadence follow-up",
        "date_utc": "2026-08-20",
        "cadence_sequence": ["A", "B", "A", "D"],
        "complete_abacad": False,
        "candidate_count": len(output_candidates),
        "receiver_frame_coincidence_tolerance_hz": COINCIDENCE_TOLERANCE_HZ,
        "off_candidate_track_floor_snr": LOCAL_PEAK_FLOOR,
        "on_candidate_track_floor_snr": 3.0,
        "candidates": output_candidates,
        "interpretive_limit": (
            "This targeted follow-up can reject candidates or document "
            "persistence in two independent ON scans. It cannot increase the "
            "frozen global significance or substitute for a complete ABACAD "
            "confirmation."
        ),
    }
    write_json(args.output_dir / "independent_followup.json", result)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "scan_metrics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=sorted({key for row in csv_rows for key in row}),
        )
        writer.writeheader()
        writer.writerows(csv_rows)
    print(json.dumps({
        "candidate_count": len(output_candidates),
        "classifications": [
            item["followup_classification"] for item in output_candidates
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
