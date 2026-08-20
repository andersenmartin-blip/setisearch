#!/usr/bin/env python3
"""Labelled post-hoc morphology checks for Milestone 11 survivors.

This script does not change, rerun, or tune the frozen v0.4.0 detector.  It
re-extracts only the two public filterbank windows containing the five formal
survivors, measures local topocentric morphology in all six ABACAD scans, and
tests for receiver-frame ON/OFF coincidences within the already frozen 20 Hz
candidate-clustering tolerance.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from seti_repeater.dedoppler import dedoppler_max
from seti_repeater.orbit import celestial_frequency_factor, make_location, make_target
from seti_repeater.search import load_scan
from seti_repeater.sigproc import extract_frequency_window
from seti_repeater.spectral import normalized_boxcar


WINDOW_IDS = ("m11_1400p5", "m11_1425p0")
LOCAL_HALF_WIDTH_HZ = 100.0
COINCIDENCE_TOLERANCE_HZ = 20.0
LOCAL_PEAK_FLOOR = 5.5


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def find_survivors(summary: dict, windows: list[dict]) -> list[dict]:
    """Find cluster records without depending on the summary's nesting layout."""
    found: list[dict] = []

    def walk(value: object) -> None:
        if isinstance(value, dict):
            if value.get("disposition") == "survives_for_followup" and "best_hypothesis" in value:
                found.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(summary)
    unique: dict[tuple[float, int, int], dict] = {}
    for item in found:
        best = item["best_hypothesis"]
        key = (
            round(float(best["frequency_mhz"]), 12),
            int(best["template_index"]),
            int(best["spectral_width_channels"]),
        )
        unique[key] = item
    records = []
    for item in unique.values():
        best = item["best_hypothesis"]
        frequency = float(best["frequency_mhz"])
        matches = [
            window["id"] for window in windows
            if window["rest_center_mhz"] - window["rest_half_width_khz"] / 1000.0
            <= frequency <=
            window["rest_center_mhz"] + window["rest_half_width_khz"] / 1000.0
        ]
        if len(matches) != 1:
            raise RuntimeError(f"Could not assign {frequency:.9f} MHz to exactly one search window")
        records.append({"window_id": matches[0], "cluster": item})
    records.sort(key=lambda item: -float(item["cluster"]["max_snr"]))
    if len(records) != 5:
        raise RuntimeError(f"Expected five formal survivors, found {len(records)}")
    return records


def extract_needed(config: dict, data_dir: Path, window_ids: set[str], workers: int) -> None:
    for window in config["windows"]:
        if window["id"] not in window_ids:
            continue
        for scan in config["scans"]:
            output = data_dir / window["id"] / f"{scan['label']}.npz"
            print(f"extract {window['id']} {scan['label']}", flush=True)
            extract_frequency_window(
                scan["url"], window["fmin_mhz"], window["fmax_mhz"], output,
                workers=workers,
            )


def predicted_track(scan: dict, rest_mhz: float, scale: float, phase: float, config: dict) -> tuple[np.ndarray, np.ndarray]:
    factor, _, _ = celestial_frequency_factor(
        scan["times"], scale, phase,
        make_target(config["target"]), make_location(config["observatory"]),
        config["orbit"],
    )
    return rest_mhz * factor, factor


def greedy_peaks(frequency_mhz: np.ndarray, spectrum: np.ndarray, floor: float, separation_bins: int, limit: int = 12) -> list[dict]:
    finite = np.flatnonzero(np.isfinite(spectrum) & (spectrum >= floor))
    order = finite[np.argsort(spectrum[finite])[::-1]]
    accepted: list[int] = []
    for index in order:
        if all(abs(int(index) - old) > separation_bins for old in accepted):
            accepted.append(int(index))
        if len(accepted) >= limit:
            break
    return [
        {"frequency_mhz": float(frequency_mhz[index]), "snr": float(spectrum[index])}
        for index in accepted
    ]


def analyse_scan(scan: dict, best: dict, config: dict) -> tuple[dict, dict]:
    frequencies = scan["frequency_mhz"]
    normalized = scan["normalized"]
    width = int(best["spectral_width_channels"])
    rest_mhz = float(best["frequency_mhz"])
    track_mhz, factor = predicted_track(
        scan, rest_mhz, float(best["projected_scale"]),
        float(best["phase_offset_cycles"]), config,
    )
    df_hz = abs(float(frequencies[1] - frequencies[0])) * 1e6
    duration_s = (scan["times"][-1] - scan["times"][0]).to_value("s")
    filtered = normalized_boxcar(normalized, width)
    indices = np.rint((track_mhz - frequencies[0]) / (frequencies[1] - frequencies[0])).astype(int)
    path_values = filtered[np.arange(filtered.shape[0]), indices]
    path_snr = float(np.sum(path_values) / np.sqrt(path_values.size))

    center_mhz = float(np.mean(track_mhz))
    local = np.abs((frequencies - center_mhz) * 1e6) <= LOCAL_HALF_WIDTH_HZ
    local_indices = np.flatnonzero(local)
    stationary = np.sum(filtered, axis=0) / np.sqrt(filtered.shape[0])
    stationary_index = int(local_indices[np.nanargmax(stationary[local])])

    free_snr, free_drift, margin = dedoppler_max(
        filtered, float(scan["header"]["tsamp"]), df_hz, max_drift_hz_s=2.0,
    )
    safe_local = local.copy()
    safe_local[:margin] = False
    if margin:
        safe_local[-margin:] = False
    free_index = int(np.flatnonzero(safe_local)[np.nanargmax(free_snr[safe_local])])
    peaks = greedy_peaks(
        frequencies[local], stationary[local], LOCAL_PEAK_FLOOR,
        separation_bins=max(1, width // 2),
    )
    predicted_drift = float((track_mhz[-1] - track_mhz[0]) * 1e6 / duration_s)
    metrics = {
        "predicted_start_mhz": float(track_mhz[0]),
        "predicted_mid_mhz": center_mhz,
        "predicted_end_mhz": float(track_mhz[-1]),
        "predicted_drift_hz_s": predicted_drift,
        "candidate_track_snr": path_snr,
        "candidate_track_row_values": [float(value) for value in path_values],
        "best_stationary_frequency_mhz": float(frequencies[stationary_index]),
        "best_stationary_snr": float(stationary[stationary_index]),
        "best_stationary_offset_from_prediction_hz": float((frequencies[stationary_index] - center_mhz) * 1e6),
        "best_free_frequency_mhz": float(frequencies[free_index]),
        "best_free_snr": float(free_snr[free_index]),
        "best_free_drift_hz_s": float(free_drift[free_index]),
        "stationary_peaks_snr_ge_5p5": peaks,
    }
    plot = {
        "frequency_mhz": frequencies[local],
        "normalized": normalized[:, local],
        "track_mhz": track_mhz,
        "stationary_spectrum": stationary[local],
    }
    return metrics, plot


def closest_peak(peaks: list[dict], frequency_mhz: float) -> dict | None:
    if not peaks:
        return None
    peak = min(peaks, key=lambda item: abs((item["frequency_mhz"] - frequency_mhz) * 1e6))
    result = dict(peak)
    result["delta_hz"] = float((result["frequency_mhz"] - frequency_mhz) * 1e6)
    return result


def add_coincidences(candidate: dict) -> None:
    best = candidate["best_hypothesis"]
    active = set(int(value) for value in best["active_epochs_zero_based"])
    coincidences = []
    for epoch in sorted(active):
        on = candidate["scans"][f"epoch{epoch + 1}_on"]
        off = candidate["scans"][f"epoch{epoch + 1}_off"]
        on_frequency = float(on["best_stationary_frequency_mhz"])
        nearest = closest_peak(off["stationary_peaks_snr_ge_5p5"], on_frequency)
        coincidences.append({
            "epoch_zero_based": epoch,
            "on_peak_frequency_mhz": on_frequency,
            "on_peak_snr": float(on["best_stationary_snr"]),
            "nearest_off_peak": nearest,
            "within_20_hz": bool(nearest is not None and abs(nearest["delta_hz"]) <= COINCIDENCE_TOLERANCE_HZ),
            "off_candidate_track_snr": float(off["candidate_track_snr"]),
            "off_candidate_track_snr_ge_5p5": bool(float(off["candidate_track_snr"]) >= LOCAL_PEAK_FLOOR),
        })
    candidate["adjacent_off_receiver_frame_checks"] = coincidences
    candidate["off_coincidence_count"] = sum(item["within_20_hz"] for item in coincidences)

    # The frozen verdict is retained; this is a deliberately labelled post-hoc triage result.
    frequency = float(best["frequency_mhz"])
    near_integer_mhz_hz = abs(frequency - round(frequency)) * 1e6
    reasons = []
    if candidate["off_coincidence_count"]:
        reasons.append("adjacent_OFF_peak_within_20_Hz")
    if any(item["off_candidate_track_snr_ge_5p5"] for item in coincidences):
        reasons.append("adjacent_OFF_same_candidate_track_SNR_ge_5p5")
    if near_integer_mhz_hz <= 1000.0:
        reasons.append("within_1_kHz_of_integer_MHz_boundary")
    if int(best["spectral_width_channels"]) == 9:
        reasons.append("selected_widest_frozen_boxcar")
    candidate["integer_mhz_distance_hz"] = float(near_integer_mhz_hz)
    candidate["posthoc_triage_reasons"] = reasons
    candidate["posthoc_classification"] = "PENDING_CROSS_CANDIDATE_CHECK"


def add_cross_candidate_aliases(candidates: list[dict]) -> None:
    """Find different rest/template solutions mapping to one receiver feature."""
    for candidate in candidates:
        candidate["cross_candidate_receiver_aliases"] = []
    for left_index, left in enumerate(candidates):
        left_active = set(int(value) for value in left["best_hypothesis"]["active_epochs_zero_based"])
        for right in candidates[left_index + 1:]:
            right_active = set(int(value) for value in right["best_hypothesis"]["active_epochs_zero_based"])
            matches = []
            for epoch in sorted(left_active & right_active):
                left_frequency = float(left["scans"][f"epoch{epoch + 1}_on"]["best_stationary_frequency_mhz"])
                right_frequency = float(right["scans"][f"epoch{epoch + 1}_on"]["best_stationary_frequency_mhz"])
                delta_hz = (right_frequency - left_frequency) * 1e6
                if abs(delta_hz) <= COINCIDENCE_TOLERANCE_HZ:
                    matches.append({"epoch_zero_based": epoch, "delta_hz": float(delta_hz)})
            if len(matches) >= 2:
                left["cross_candidate_receiver_aliases"].append({
                    "other_candidate_ordinal": right["ordinal"], "matched_active_epochs": matches,
                })
                right["cross_candidate_receiver_aliases"].append({
                    "other_candidate_ordinal": left["ordinal"], "matched_active_epochs": matches,
                })

    for candidate in candidates:
        reasons = candidate["posthoc_triage_reasons"]
        if candidate["cross_candidate_receiver_aliases"]:
            reasons.append("different_planet_templates_map_to_same_receiver_feature")
        rfi_reasons = {
            "adjacent_OFF_peak_within_20_Hz",
            "adjacent_OFF_same_candidate_track_SNR_ge_5p5",
            "within_1_kHz_of_integer_MHz_boundary",
            "different_planet_templates_map_to_same_receiver_feature",
        }
        if rfi_reasons.intersection(reasons):
            candidate["posthoc_classification"] = "RFI_OR_INSTRUMENTAL"
        else:
            active = set(int(value) for value in candidate["best_hypothesis"]["active_epochs_zero_based"])
            if all(
                float(candidate["scans"][f"epoch{epoch + 1}_on"]["candidate_track_snr"]) < 3.0
                for epoch in active
            ):
                candidate["posthoc_classification"] = "NOT_REPRODUCED_BY_LOCAL_TRACK_CHECK"
            else:
                candidate["posthoc_classification"] = "UNRESOLVED_REQUIRES_INDEPENDENT_CADENCE"


def plot_candidate(candidate: dict, output: Path) -> None:
    labels = [f"epoch{epoch}_{kind}" for epoch in (1, 2, 3) for kind in ("on", "off")]
    fig, axes = plt.subplots(6, 2, figsize=(12, 14), constrained_layout=True,
                             gridspec_kw={"width_ratios": [3.2, 1.2]})
    for row, label in enumerate(labels):
        plot = candidate["_plots"][label]
        frequency = plot["frequency_mhz"]
        offsets = (frequency - candidate["scans"][label]["predicted_mid_mhz"]) * 1e6
        image = axes[row, 0].imshow(
            plot["normalized"], aspect="auto", origin="lower",
            extent=[offsets[0], offsets[-1], 0, plot["normalized"].shape[0]],
            interpolation="nearest", cmap="viridis",
            vmin=-2.5, vmax=min(12.0, float(np.nanpercentile(plot["normalized"], 99.8))),
        )
        track_offsets = (plot["track_mhz"] - candidate["scans"][label]["predicted_mid_mhz"]) * 1e6
        axes[row, 0].plot(track_offsets, np.arange(track_offsets.size) + 0.5, color="white", lw=0.8)
        axes[row, 0].set_ylabel(label)
        axes[row, 0].set_xlabel("offset from predicted midpoint (Hz)")
        axes[row, 1].plot(plot["stationary_spectrum"], offsets, lw=0.8)
        axes[row, 1].axhline(0, color="black", lw=0.5, alpha=0.5)
        axes[row, 1].set_xlabel("stationary S/N")
        axes[row, 1].set_ylabel("offset (Hz)")
    fig.colorbar(image, ax=axes[:, 0], label="robust per-row normalized power", shrink=0.5)
    best = candidate["best_hypothesis"]
    fig.suptitle(
        f"M11 post-hoc candidate {best['frequency_mhz']:.9f} MHz; "
        f"frozen S/N {best['snr']:.3f}, width {best['spectral_width_channels']} ch",
        fontsize=12,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150)
    plt.close(fig)


def probe_archive(config: dict) -> dict:
    """Record a reproducible, conservative search for other LHS 1140 files."""
    urls = ["http://blpd0.ssl.berkeley.edu/LHS1140/", "http://blpd0.ssl.berkeley.edu/LHS1140/L/"]
    probes = []
    href_pattern = re.compile(r'href=["\']([^"\']+)', re.IGNORECASE)
    for url in urls:
        record: dict = {"url": url}
        try:
            request = Request(url, headers={"User-Agent": "setisearch-m11-posthoc/1.0"})
            with urlopen(request, timeout=60) as response:
                payload = response.read(5_000_000)
                record["status"] = int(getattr(response, "status", response.getcode()))
                record["final_url"] = response.geturl()
            text = payload.decode("utf-8", errors="replace")
            record["sha256"] = hashlib.sha256(payload).hexdigest()
            record["hrefs"] = href_pattern.findall(text)
            record["lhs1140_fil_hrefs"] = [
                href for href in record["hrefs"]
                if "LHS1140" in href.upper() and href.lower().endswith((".fil", ".h5"))
            ]
        except Exception as exc:  # evidence includes access failures
            record["error"] = f"{type(exc).__name__}: {exc}"
        probes.append(record)

    selected_urls = {scan["url"] for scan in config["scans"] if scan["kind"] == "on"}
    observation_pattern = re.compile(r"guppi_\d+_\d+_LHS1140_\d+", re.IGNORECASE)

    def observation_id(name: str) -> str | None:
        match = observation_pattern.search(name)
        return None if match is None else match.group(0).upper()

    discovered_names = set()
    for probe in probes:
        for href in probe.get("lhs1140_fil_hrefs", []):
            discovered_names.add(href.rsplit("/", 1)[-1])
    selected_names = {url.rsplit("/", 1)[-1] for url in selected_urls}
    selected_observations = {observation_id(name) for name in selected_names}
    discovered_observations = {observation_id(name) for name in discovered_names}
    selected_observations.discard(None)
    discovered_observations.discard(None)
    additional_observations = sorted(discovered_observations - selected_observations)
    product_variants = sorted(discovered_names - selected_names)
    return {
        "scope": "public blpd0 LHS1140 directory index, checked 2026-08-20",
        "probes": probes,
        "selected_on_files": sorted(selected_names),
        "selected_observation_ids": sorted(selected_observations),
        "same_observation_product_variants": product_variants,
        "additional_observation_ids": additional_observations,
        "independent_cadence_found": bool(additional_observations),
        "interpretation": (
            "No independent cadence was exposed by the checked directory index. The extra .0002 "
            "and .8.0001 files are alternate products of the same three observation IDs, not new "
            "pointings. This is an archive-availability result, not evidence of non-recurrence."
            if not additional_observations else
            "Additional observation IDs were exposed and require a separately preregistered recurrence test."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config/lhs1140b_new_target_m11.json"))
    parser.add_argument("--summary", type=Path, default=Path("results_m11/search_summary.json"))
    parser.add_argument("--data-dir", type=Path, default=Path("data_m11_posthoc"))
    parser.add_argument("--output-dir", type=Path, default=Path("results_m11_candidate_investigation"))
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()

    config = read_json(args.config)
    summary = read_json(args.summary)
    survivors = find_survivors(summary, config["windows"])
    if args.extract:
        extract_needed(config, args.data_dir, {item["window_id"] for item in survivors}, args.workers)

    output_candidates = []
    csv_rows = []
    for ordinal, survivor in enumerate(survivors, 1):
        best = survivor["cluster"]["best_hypothesis"]
        candidate = {
            "ordinal": ordinal,
            "window_id": survivor["window_id"],
            "frozen_cluster_max_snr": float(survivor["cluster"]["max_snr"]),
            "frozen_cluster_member_count": int(survivor["cluster"]["member_count"]),
            "frozen_cluster_frequency_span_hz": float(survivor["cluster"]["frequency_span_hz"]),
            "frozen_flags": survivor["cluster"].get("flags", []),
            "frozen_off_at_best_hypothesis_snr": survivor["cluster"].get("off_at_best_hypothesis_snr"),
            "best_hypothesis": best,
            "scans": {},
            "_plots": {},
        }
        for scan_config in config["scans"]:
            path = args.data_dir / survivor["window_id"] / f"{scan_config['label']}.npz"
            scan = load_scan(path)
            metrics, plot = analyse_scan(scan, best, config)
            metrics["kind"] = scan_config["kind"]
            metrics["epoch"] = int(scan_config["epoch"])
            candidate["scans"][scan_config["label"]] = metrics
            candidate["_plots"][scan_config["label"]] = plot
            csv_rows.append({
                "candidate_ordinal": ordinal,
                "rest_frequency_mhz": float(best["frequency_mhz"]),
                "window_id": survivor["window_id"],
                "scan": scan_config["label"],
                "kind": scan_config["kind"],
                "epoch": scan_config["epoch"],
                "width_channels": int(best["spectral_width_channels"]),
                **{key: value for key, value in metrics.items() if isinstance(value, (int, float))},
            })
        add_coincidences(candidate)
        slug = f"candidate_{ordinal}_{float(best['frequency_mhz']):.6f}MHz".replace(".", "p")
        plot_candidate(candidate, args.output_dir / f"{slug}.png")
        candidate.pop("_plots")
        output_candidates.append(candidate)

    add_cross_candidate_aliases(output_candidates)

    archive = probe_archive(config)
    result = {
        "analysis_label": "post-hoc candidate investigation",
        "detector_status": "frozen v0.4.0; no search or threshold setting changed",
        "date_utc": "2026-08-20",
        "local_half_width_hz": LOCAL_HALF_WIDTH_HZ,
        "receiver_frame_coincidence_tolerance_hz": COINCIDENCE_TOLERANCE_HZ,
        "local_peak_floor_snr": LOCAL_PEAK_FLOOR,
        "candidate_count": len(output_candidates),
        "candidates": output_candidates,
        "archive_cross_cadence_search": archive,
        "interpretive_limit": (
            "These targeted checks can identify terrestrial/instrumental coincidences but cannot "
            "increase the frozen search significance. A surviving unresolved feature still needs "
            "an independent observing cadence."
        ),
    }
    write_json(args.output_dir / "candidate_investigation.json", result)
    write_json(args.output_dir / "archive_cross_cadence_search.json", archive)
    with (args.output_dir / "scan_metrics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted({key for row in csv_rows for key in row}))
        writer.writeheader()
        writer.writerows(csv_rows)
    print(json.dumps({
        "candidate_count": len(output_candidates),
        "classifications": [item["posthoc_classification"] for item in output_candidates],
        "independent_cadence_found": archive["independent_cadence_found"],
    }, indent=2))


if __name__ == "__main__":
    main()

# Temporary pull-request run marker; never merged.
