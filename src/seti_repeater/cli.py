"""Command-line interface for extraction, validation, and real-data search."""

from __future__ import annotations

from pathlib import Path
import argparse
import csv
import gc
import json
import platform
import sys

import numpy as np

from . import __version__
from .candidates import (
    annotate_local_off_vetoes, annotate_receiver_frame_aliases,
    apply_candidate_flags, build_single_epoch_rfi_mask, cluster_peaks,
    collect_hypothesis_peaks, detect_arithmetic_frequency_families,
)
from .dedoppler import dedoppler_shifts
from .diagnostics import acceleration_smearing, leakage_summary, smearing_table
from .injections import smeared_signal_vector
from .search import (
    build_bank, empirical_p, evaluate_spectral_record, load_scan, make_rest_grid,
    make_subsets, make_templates, scramble_maxima, search_bank, search_spectral_bank,
)
from .sigproc import extract_frequency_window
from .spectral import make_spectral_bank, normalized_boxcar, validate_widths


def read_config(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def _json_safe(value):
    """Replace non-finite diagnostics with JSON null while preserving structure."""
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return None
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(value), indent=2, allow_nan=False) + "\n")


def run_synthetic_validation(seed: int = 481516) -> dict:
    """Known-answer intermittent-track test, independent of celestial code."""
    rng = np.random.default_rng(seed)
    ntime, nfreq = 48, 4096
    tone_bin = 2113
    truth_template = 2
    truth_subset = [0, 2]
    single_epoch_target = 9.0
    truth_ends = np.array([13, -8, 6])
    arrays = [rng.normal(size=(ntime, nfreq)).astype(np.float32) for _ in range(3)]
    truth_shifts = []
    for epoch, end in enumerate(truth_ends):
        shifts = np.rint(end * np.arange(ntime) / (ntime - 1)).astype(int)
        truth_shifts.append(shifts)
        if epoch in truth_subset:
            arrays[epoch][np.arange(ntime), tone_bin + shifts] += single_epoch_target / np.sqrt(ntime)

    vectors = np.empty((5, 3, nfreq), dtype=np.float32)
    for template_index, delta in enumerate((-8, -4, 0, 4, 8)):
        for epoch in range(3):
            trial_end = truth_ends[epoch] + delta
            trial_shifts = np.rint(trial_end * np.arange(ntime) / (ntime - 1)).astype(int)
            vectors[template_index, epoch], _ = dedoppler_shifts(arrays[epoch], trial_shifts)
    templates = [(float(index), 0.0) for index in range(5)]
    subsets = [(0, 1), (0, 2), (1, 2), (0, 1, 2)]
    frequencies = np.arange(nfreq, dtype=float)
    best = search_bank(vectors, frequencies, templates, subsets)
    recovered = (
        best["template_index"] == truth_template
        and best["active_epochs_zero_based"] == truth_subset
        and best["frequency_index"] == tone_bin
        and best["snr"] >= 10.0
    )
    result = {
        "test": "synthetic intermittent drifting tone",
        "seed": seed,
        "truth": {
            "template_index": truth_template,
            "active_epochs_zero_based": truth_subset,
            "frequency_index": tone_bin,
            "single_epoch_target_snr": single_epoch_target,
        },
        "recovered": best,
        "passed": bool(recovered),
    }
    if not recovered:
        raise AssertionError(f"Known-answer validation failed: {result}")
    spread = np.zeros((1, 3, nfreq), dtype=np.float32)
    spread[0, 0, tone_bin - 2:tone_bin + 3] = 5.0
    spread[0, 2, tone_bin - 2:tone_bin + 3] = 5.0
    widths = (1, 3, 5, 9)
    spectral = make_spectral_bank(spread, widths)
    spectral_best = search_spectral_bank(
        spectral, frequencies, [(0.0, 0.0)], subsets, widths
    )
    spectral_passed = (
        spectral_best["spectral_width_channels"] == 5
        and spectral_best["active_epochs_zero_based"] == truth_subset
        and spectral_best["frequency_index"] == tone_bin
    )
    result["multi_channel_known_answer"] = {
        "truth_width_channels": 5,
        "recovered": spectral_best,
        "passed": bool(spectral_passed),
    }
    result["passed"] = bool(recovered and spectral_passed)
    if not spectral_passed:
        raise AssertionError(f"Multi-channel validation failed: {result}")
    return result


def command_extract(args: argparse.Namespace) -> None:
    config = read_config(args.config)
    data_dir = Path(args.data_dir)
    for window in config["windows"]:
        for scan in config["scans"]:
            output = data_dir / window["id"] / f"{scan['label']}.npz"
            print(f"{window['id']} {scan['label']}: {output}", flush=True)
            extract_frequency_window(
                scan["url"], window["fmin_mhz"], window["fmax_mhz"],
                output, workers=args.workers,
            )
            print(f"  {output.stat().st_size / 2**20:.1f} MiB", flush=True)


def _candidate_diagnostics(best: dict, details: list[list[dict]], scan: dict) -> dict:
    template_details = details[best["template_index"]]
    df_hz = abs(float(scan["frequency_mhz"][1] - scan["frequency_mhz"][0])) * 1e6
    tsamp_s = float(scan["header"]["tsamp"])
    epochs = []
    for epoch in best["active_epochs_zero_based"]:
        info = dict(template_details[epoch])
        info.update(acceleration_smearing(info["predicted_drift_hz_s"], tsamp_s, df_hz))
        info["epoch_zero_based"] = epoch
        epochs.append(info)
    return {
        "spectral_leakage": leakage_summary(),
        "acceleration_smearing_by_active_epoch": epochs,
        "channel_width_hz": df_hz,
        "integration_time_s": tsamp_s,
        "important_note": (
            "The pipeline searches normalized multi-channel boxcars and measures their recovery with "
            "time-averaged sinc-squared injections. These analytic loss fields remain approximations."
        ),
    }


def _plot_calibration(global_null: np.ndarray, observed: float, output: Path) -> None:
    import matplotlib.pyplot as plt

    q99 = float(np.quantile(global_null, 0.99, method="higher"))
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.hist(global_null, bins=24, color="#5b7c99", alpha=0.85, edgecolor="white")
    ax.axvline(q99, color="#c87f0a", linewidth=2, label=f"99th percentile: {q99:.2f}")
    ax.axvline(observed, color="#a23b3b", linewidth=2.5, label=f"Observed maximum: {observed:.2f}")
    ax.set_xlabel("Maximum recurrence S/N across all configured bands")
    ax.set_ylabel("Scramble count")
    ax.set_title("Empirical global false-alarm calibration")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def _run_completeness(
    config: dict,
    scans: list[dict],
    background_bank: np.ndarray,
    rest_grid: np.ndarray,
    templates: list[tuple[float, float]],
    spectral_widths: tuple[int, ...],
    detection_threshold: float,
    exclusion_mask: np.ndarray | None = None,
) -> dict:
    """Recovery experiment using real-noise spectra and realistic signal response."""
    settings = config["search"]["completeness"]
    minimum_active_epoch_snr = config["search"].get("minimum_active_epoch_snr")
    stack_statistic = config["search"].get("stack_statistic", "sum")
    rng = np.random.default_rng(settings["seed"])
    active_epochs = list(settings["active_epochs_zero_based"])
    truth_templates = list(settings["truth_template_indices"])
    trials_per_level = int(settings["trials_per_level"])
    min_shift = int(config["search"]["min_scramble_shift_bins"])
    nfreq = rest_grid.size
    channel_width_mhz = float(np.median(np.diff(rest_grid)))
    trial_models = []

    def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
        proportion = successes / total
        denominator = 1 + z**2 / total
        center = (proportion + z**2 / (2 * total)) / denominator
        radius = z * np.sqrt(proportion * (1 - proportion) / total + z**2 / (4 * total**2)) / denominator
        return [float(max(0.0, center - radius)), float(min(1.0, center + radius))]

    for trial in range(trials_per_level):
        template_index = truth_templates[trial % len(truth_templates)]
        scale, phase = templates[template_index]
        truth_frequency = float(
            np.mean(rest_grid) + rng.uniform(-0.010, 0.010)
            + rng.uniform(-0.5, 0.5) * channel_width_mhz
        )
        unit_signals = np.zeros((len(scans), nfreq), dtype=np.float32)
        epoch_diagnostics = []
        for epoch in active_epochs:
            unit_signals[epoch], details = smeared_signal_vector(
                scans[epoch], rest_grid, float(np.mean(rest_grid)),
                truth_frequency, scale, phase, 1.0, config,
                subintegrations=settings["subintegrations"],
            )
            details["epoch_zero_based"] = epoch
            epoch_diagnostics.append(details)
        trial_models.append({
            "template_index": template_index,
            "projected_scale": scale,
            "phase_offset_cycles": phase,
            "truth_frequency_mhz": truth_frequency,
            "truth_frequency_index": int(np.argmin(np.abs(rest_grid - truth_frequency))),
            "unit_signals": unit_signals,
            "epoch_diagnostics": epoch_diagnostics,
        })

    levels = []
    trial_records = []
    local_half_width = max(spectral_widths) // 2 + 3
    one_channel_width_index = spectral_widths.index(1)
    for ideal_snr in settings["ideal_single_epoch_snr_grid"]:
        recovered_multi = 0
        recovered_one = 0
        multi_scores = []
        one_scores = []
        selected_widths = []
        template_stats = {
            template_index: {"trials": 0, "multi": 0, "one": 0}
            for template_index in truth_templates
        }
        for trial_index, model in enumerate(trial_models):
            template_index = model["template_index"]
            combined = np.empty((len(scans), nfreq), dtype=np.float32)
            noise_shifts = []
            rolled_masks = []
            for epoch in range(len(scans)):
                shift = int(rng.integers(min_shift, nfreq - min_shift))
                noise_shifts.append(shift)
                combined[epoch] = np.roll(background_bank[template_index, epoch], shift)
                if exclusion_mask is not None:
                    rolled_masks.append(np.roll(
                        exclusion_mask[:, template_index, epoch], shift, axis=-1
                    ))
                if epoch in active_epochs:
                    combined[epoch] += float(ideal_snr) * model["unit_signals"][epoch]
            filtered = np.stack(
                [normalized_boxcar(combined, width) for width in spectral_widths], axis=0
            )
            active_multi = filtered[:, active_epochs]
            active_one = combined[active_epochs]
            if stack_statistic == "sum":
                stacked_multi = np.sum(active_multi, axis=1) / np.sqrt(len(active_epochs))
                stacked_one = np.sum(active_one, axis=0) / np.sqrt(len(active_epochs))
            elif stack_statistic == "minimum_epoch":
                stacked_multi = np.sqrt(len(active_epochs)) * np.min(active_multi, axis=1)
                stacked_one = np.sqrt(len(active_epochs)) * np.min(active_one, axis=0)
            else:
                raise ValueError(f"Unknown stack statistic: {stack_statistic}")
            if minimum_active_epoch_snr is not None:
                stacked_multi = np.where(
                    np.all(active_multi >= minimum_active_epoch_snr, axis=1),
                    stacked_multi, -np.inf,
                )
                stacked_one = np.where(
                    np.all(active_one >= minimum_active_epoch_snr, axis=0),
                    stacked_one, -np.inf,
                )
            if exclusion_mask is not None:
                active_mask = rolled_masks[active_epochs[0]].copy()
                for epoch in active_epochs[1:]:
                    active_mask |= rolled_masks[epoch]
                stacked_multi[active_mask] = -np.inf
                stacked_one[active_mask[one_channel_width_index]] = -np.inf
            center = model["truth_frequency_index"]
            lo = center - local_half_width
            hi = center + local_half_width + 1
            local_multi = stacked_multi[:, lo:hi]
            if np.any(np.isfinite(local_multi)):
                flat_index = int(np.nanargmax(local_multi))
                width_index, _ = np.unravel_index(flat_index, local_multi.shape)
                multi_score = float(np.nanmax(local_multi))
            else:
                width_index = 0
                multi_score = -999.0
            local_one = stacked_one[lo:hi]
            one_score = float(np.nanmax(local_one)) if np.any(np.isfinite(local_one)) else -999.0
            multi_hit = multi_score >= detection_threshold
            one_hit = one_score >= detection_threshold
            recovered_multi += int(multi_hit)
            recovered_one += int(one_hit)
            multi_scores.append(multi_score)
            one_scores.append(one_score)
            selected_widths.append(int(spectral_widths[width_index]))
            template_stats[template_index]["trials"] += 1
            template_stats[template_index]["multi"] += int(multi_hit)
            template_stats[template_index]["one"] += int(one_hit)
            trial_records.append({
                "ideal_single_epoch_snr": float(ideal_snr),
                "trial_index": trial_index,
                "template_index": template_index,
                "projected_scale": model["projected_scale"],
                "phase_offset_cycles": model["phase_offset_cycles"],
                "truth_frequency_mhz": model["truth_frequency_mhz"],
                "multi_channel_recovered": bool(multi_hit),
                "one_channel_recovered": bool(one_hit),
                "multi_channel_local_snr": multi_score,
                "one_channel_local_snr": one_score,
                "selected_width_channels": int(spectral_widths[width_index]),
                "noise_shifts_bins": noise_shifts,
                "epoch_diagnostics": model["epoch_diagnostics"],
            })
        levels.append({
            "ideal_single_epoch_snr": float(ideal_snr),
            "trials": trials_per_level,
            "multi_channel_recovered": recovered_multi,
            "multi_channel_recovery_fraction": recovered_multi / trials_per_level,
            "multi_channel_wilson_95_interval": wilson_interval(recovered_multi, trials_per_level),
            "one_channel_recovered": recovered_one,
            "one_channel_recovery_fraction": recovered_one / trials_per_level,
            "one_channel_wilson_95_interval": wilson_interval(recovered_one, trials_per_level),
            "median_multi_channel_local_snr": float(np.median(multi_scores)),
            "median_one_channel_local_snr": float(np.median(one_scores)),
            "selected_width_counts": {
                str(width): selected_widths.count(width) for width in spectral_widths
            },
            "by_truth_template": [
                {
                    "template_index": template_index,
                    "projected_scale": templates[template_index][0],
                    "phase_offset_cycles": templates[template_index][1],
                    "trials": stats["trials"],
                    "mean_bins_swept_per_integration": float(np.mean([
                        epoch["mean_bins_swept_per_integration"]
                        for model in trial_models if model["template_index"] == template_index
                        for epoch in model["epoch_diagnostics"]
                    ])),
                    "multi_channel_recovery_fraction": stats["multi"] / stats["trials"],
                    "one_channel_recovery_fraction": stats["one"] / stats["trials"],
                }
                for template_index, stats in template_stats.items()
            ],
        })
    return {
        "method": (
            f"Real {settings['background_window']} planet-frame noise vectors are independently circularly shifted by epoch; "
            "signals use time-averaged sinc-squared leakage and model acceleration within each integration."
        ),
        "ideal_snr_definition": (
            "Single-epoch S/N the same total signal power would produce as a stationary bin-centred one-channel tone."
        ),
        "detection_threshold_snr": float(detection_threshold),
        "minimum_active_epoch_snr": minimum_active_epoch_snr,
        "stack_statistic": stack_statistic,
        "single_epoch_rfi_mask_applied": exclusion_mask is not None,
        "active_epochs_zero_based": active_epochs,
        "truth_template_indices": truth_templates,
        "spectral_widths_channels": list(spectral_widths),
        "levels": levels,
        "trials": trial_records,
    }


def _plot_completeness(completeness: dict, output: Path) -> None:
    import matplotlib.pyplot as plt

    levels = completeness["levels"]
    x = [item["ideal_single_epoch_snr"] for item in levels]
    multi = [100 * item["multi_channel_recovery_fraction"] for item in levels]
    one = [100 * item["one_channel_recovery_fraction"] for item in levels]
    multi_error = [
        [100 * (item["multi_channel_recovery_fraction"] - item["multi_channel_wilson_95_interval"][0]) for item in levels],
        [100 * (item["multi_channel_wilson_95_interval"][1] - item["multi_channel_recovery_fraction"]) for item in levels],
    ]
    one_error = [
        [100 * (item["one_channel_recovery_fraction"] - item["one_channel_wilson_95_interval"][0]) for item in levels],
        [100 * (item["one_channel_wilson_95_interval"][1] - item["one_channel_recovery_fraction"]) for item in levels],
    ]
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.errorbar(x, multi, yerr=multi_error, marker="o", capsize=3, linewidth=2.4, label="1/3/5/9-channel bank")
    ax.errorbar(x, one, yerr=one_error, marker="o", capsize=3, linewidth=2.0, label="One channel only")
    ax.set_xlabel("Ideal unsmeared single-epoch S/N")
    ax.set_ylabel("Recovery fraction (%)")
    ax.set_ylim(-3, 103)
    ax.set_title("Real-noise smeared-tone injection recovery")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def command_validate(args: argparse.Namespace) -> None:
    result = {
        "software_version": __version__,
        "known_answer": run_synthetic_validation(seed=args.seed),
        "spectral_leakage": leakage_summary(),
        "acceleration_smearing_table": smearing_table(args.tsamp, args.channel_width),
    }
    if args.output:
        write_json(Path(args.output), result)
    print(json.dumps(result, indent=2))


def command_search(args: argparse.Namespace) -> None:
    config = read_config(args.config)
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    validation = run_synthetic_validation()
    print("One-channel and multi-channel known-answer validation: PASS", flush=True)

    templates = make_templates(config)
    subsets = make_subsets(3, config["search"]["minimum_active_epochs"])
    spectral_widths = validate_widths(config["search"]["spectral_widths_channels"])
    minimum_active_epoch_snr = config["search"].get("minimum_active_epoch_snr")
    stack_statistic = config["search"].get("stack_statistic", "sum")
    on_banks: dict[str, np.ndarray] = {}
    on_masks: dict[str, np.ndarray] = {}
    window_products: dict[str, dict] = {}
    completeness_scans = None
    completeness_bank = None
    completeness_rest_grid = None
    completeness_mask = None
    completeness_window = config["search"]["completeness"]["background_window"]
    reporting = config["search"].get("candidate_reporting")
    rfi_excision = config["search"].get("rfi_excision")
    candidate_veto_v0p5 = config["search"].get("candidate_veto_v0p5")

    for window in config["windows"]:
        window_id = window["id"]
        print(f"Building orbital and spectral banks: {window_id}", flush=True)
        scans_by_kind = {}
        for kind in ("on", "off"):
            definitions = sorted(
                (scan for scan in config["scans"] if scan["kind"] == kind),
                key=lambda item: item["epoch"],
            )
            paths = [data_dir / window_id / f"{scan['label']}.npz" for scan in definitions]
            missing = [str(path) for path in paths if not path.exists()]
            if missing:
                raise FileNotFoundError("Missing extracted slices; run extract first: " + ", ".join(missing))
            scans_by_kind[kind] = [load_scan(path) for path in paths]

        first_scan = scans_by_kind["on"][0]
        channel_width_mhz = abs(float(
            first_scan["frequency_mhz"][1] - first_scan["frequency_mhz"][0]
        ))
        rest_grid = make_rest_grid(window, channel_width_mhz)
        on_bank, on_details = build_bank(
            scans_by_kind["on"], rest_grid, window["rest_center_mhz"], templates, config
        )
        off_bank, _ = build_bank(
            scans_by_kind["off"], rest_grid, window["rest_center_mhz"], templates, config
        )
        on_spectral = make_spectral_bank(on_bank, spectral_widths)
        off_spectral = make_spectral_bank(off_bank, spectral_widths)
        if rfi_excision:
            on_mask = build_single_epoch_rfi_mask(
                on_spectral, rfi_excision["single_epoch_strong_snr"],
                rfi_excision["other_epochs_below_snr"], rfi_excision["guard_channels"],
            )
            off_mask = build_single_epoch_rfi_mask(
                off_spectral, rfi_excision["single_epoch_strong_snr"],
                rfi_excision["other_epochs_below_snr"], rfi_excision["guard_channels"],
            )
        else:
            on_mask = off_mask = None
        width_one_index = spectral_widths.index(1)
        one_channel_best = search_bank(
            on_bank, rest_grid, templates, subsets, minimum_active_epoch_snr,
            stack_statistic, None if on_mask is None else on_mask[width_one_index],
        )
        on_best = search_spectral_bank(
            on_spectral, rest_grid, templates, subsets, spectral_widths,
            minimum_active_epoch_snr, stack_statistic, on_mask,
        )
        off_best = search_spectral_bank(
            off_spectral, rest_grid, templates, subsets, spectral_widths,
            minimum_active_epoch_snr, stack_statistic, off_mask,
        )
        on_best["off_at_same_hypothesis_snr"] = evaluate_spectral_record(
            off_spectral, on_best, minimum_active_epoch_snr, stack_statistic
        )
        diagnostics = _candidate_diagnostics(on_best, on_details, first_scan)
        candidate_product = None
        if reporting:
            peak_records = collect_hypothesis_peaks(
                on_spectral, rest_grid, templates, subsets, spectral_widths,
                reporting["peaks_per_hypothesis"], reporting["snr_floor"],
                minimum_active_epoch_snr, stack_statistic, on_mask,
            )
            all_clusters = cluster_peaks(peak_records, reporting["cluster_tolerance_hz"])
            retained_clusters = all_clusters[:reporting["max_report_clusters"]]
            for cluster in retained_clusters:
                cluster["off_at_best_hypothesis_snr"] = evaluate_spectral_record(
                    off_spectral, cluster["best_hypothesis"],
                    minimum_active_epoch_snr, stack_statistic,
                )
            if candidate_veto_v0p5:
                annotate_local_off_vetoes(
                    retained_clusters, off_spectral, rest_grid, templates, subsets,
                    spectral_widths,
                    candidate_veto_v0p5["local_off_tolerance_hz"],
                    candidate_veto_v0p5["single_epoch_snr_floor"],
                    minimum_active_epoch_snr, stack_statistic,
                )
                annotate_receiver_frame_aliases(
                    retained_clusters, scans_by_kind["on"], config,
                    candidate_veto_v0p5["receiver_local_half_width_hz"],
                    candidate_veto_v0p5["receiver_alias_tolerance_hz"],
                    candidate_veto_v0p5["receiver_alias_minimum_shared_epochs"],
                    candidate_veto_v0p5["single_epoch_snr_floor"],
                )
            families = detect_arithmetic_frequency_families(
                retained_clusters,
                reporting["family_spacing_tolerance_hz"],
                reporting["family_min_members"],
            )
            candidate_product = {
                "hypothesis_peak_count": len(peak_records),
                "cluster_count_before_report_limit": len(all_clusters),
                "reported_cluster_count": len(retained_clusters),
                "clusters": retained_clusters,
                "arithmetic_frequency_families": families,
                "candidate_veto_v0p5": candidate_veto_v0p5,
            }
        on_banks[window_id] = on_spectral
        if on_mask is not None:
            on_masks[window_id] = on_mask
        mask_product = None
        if on_mask is not None:
            unique = on_mask[0]
            mask_product = {
                "settings": rfi_excision,
                "on_masked_template_epoch_frequency_cells": int(np.count_nonzero(unique)),
                "on_masked_fraction": float(np.mean(unique)),
                "on_masked_cells_by_epoch": [
                    int(np.count_nonzero(unique[:, epoch])) for epoch in range(unique.shape[1])
                ],
                "off_masked_template_epoch_frequency_cells": int(np.count_nonzero(off_mask[0])),
                "off_masked_fraction": float(np.mean(off_mask[0])),
                "mask_moves_with_each_epoch_in_scrambled_controls": True,
            }
        window_products[window_id] = {
            "window": window,
            "rest_bins": int(rest_grid.size),
            "on_best": on_best,
            "one_channel_regression_best": one_channel_best,
            "off_global_best": off_best,
            "diagnostics_for_on_best": diagnostics,
            "candidate_reduction": candidate_product,
            "single_epoch_rfi_excision": mask_product,
        }
        print(
            f"  ON {on_best['snr']:.3f} ({on_best['spectral_width_channels']} ch) "
            f"at {on_best['frequency_mhz']:.9f} MHz; "
            f"OFF-global {off_best['snr']:.3f}; OFF-matched {on_best['off_at_same_hypothesis_snr']:.3f}",
            flush=True,
        )
        if window_id == completeness_window:
            completeness_scans = scans_by_kind["on"]
            completeness_bank = on_bank
            completeness_rest_grid = rest_grid
            completeness_mask = on_mask
        del scans_by_kind, off_bank, off_spectral, on_details
        gc.collect()

    n_scrambles = args.scrambles or config["search"]["scrambles"]
    print(f"Running {n_scrambles} coherence-destroying scrambles", flush=True)
    global_null, per_window_null = scramble_maxima(
        on_banks, subsets, n_scrambles,
        config["search"]["scramble_seed"],
        config["search"]["min_scramble_shift_bins"],
        minimum_active_epoch_snr,
        stack_statistic,
        on_masks or None,
    )
    observed_global = max(item["on_best"]["snr"] for item in window_products.values())
    for window_id, product in window_products.items():
        product["empirical_null"] = {
            "p_value_window": empirical_p(product["on_best"]["snr"], per_window_null[window_id]),
            "null_median": float(np.median(per_window_null[window_id])),
            "null_99th_percentile": float(np.quantile(per_window_null[window_id], 0.99, method="higher")),
        }

    global_p = empirical_p(observed_global, global_null)
    reference_snr = config["search"]["candidate_snr_reference"]
    global_q99 = float(np.quantile(global_null, 0.99, method="higher"))
    operational_threshold = max(float(reference_snr), global_q99)
    if observed_global < operational_threshold:
        assessment = "NO CANDIDATE: every ON maximum is below the calibrated operational threshold."
    elif global_p > 0.01:
        assessment = "NO CANDIDATE: the strongest maximum is compatible with the empirical global null."
    else:
        assessment = "FOLLOW-UP REQUIRED: significance and OFF-source evidence must be reviewed manually."

    candidate_reduction_summary = None
    if reporting:
        dispositions: dict[str, int] = {}
        for product in window_products.values():
            reduction = product["candidate_reduction"]
            apply_candidate_flags(
                reduction["clusters"], reduction["arithmetic_frequency_families"],
                operational_threshold, reporting["template_multiplicity_flag"],
            )
            for cluster in reduction["clusters"]:
                disposition = cluster["disposition"]
                dispositions[disposition] = dispositions.get(disposition, 0) + 1
        candidate_reduction_summary = {
            "settings": reporting,
            "hypothesis_peaks_retained": int(sum(
                product["candidate_reduction"]["hypothesis_peak_count"]
                for product in window_products.values()
            )),
            "frequency_clusters_before_report_limit": int(sum(
                product["candidate_reduction"]["cluster_count_before_report_limit"]
                for product in window_products.values()
            )),
            "reported_clusters": int(sum(
                product["candidate_reduction"]["reported_cluster_count"]
                for product in window_products.values()
            )),
            "dispositions": dispositions,
        }

    if completeness_scans is None or completeness_bank is None or completeness_rest_grid is None:
        raise RuntimeError("Configured completeness background window was not processed")
    print("Running real-noise smeared-tone completeness experiment", flush=True)
    completeness = _run_completeness(
        config, completeness_scans, completeness_bank, completeness_rest_grid,
        templates, spectral_widths, operational_threshold,
        completeness_mask,
    )
    completeness_summary = {key: value for key, value in completeness.items() if key != "trials"}
    searched_bandwidth_mhz = sum(
        2 * float(window["rest_half_width_khz"]) / 1000 for window in config["windows"]
    )
    if "confirmation_scope" in config["project"]:
        provenance_limit = "Confirmation scope: " + config["project"]["confirmation_scope"]
    else:
        provenance_limit = (
            "The strong-single-epoch RFI mask and recurrence statistic were added after the "
            "first Milestone 7 diagnostic run; independent future bands are required for confirmation."
        )

    summary = {
        "pipeline": {
            "name": "seti-repeater", "version": __version__,
            "python": platform.python_version(), "numpy": np.__version__,
        },
        "preregistration": config["project"],
        "known_answer_validation": validation,
        "search_dimensions": {
            "windows": len(config["windows"]),
            "templates": len(templates), "epoch_subsets": len(subsets),
            "spectral_width_templates": list(spectral_widths),
            "minimum_active_epoch_snr": minimum_active_epoch_snr,
            "stack_statistic": stack_statistic,
            "single_epoch_rfi_excision": rfi_excision,
            "candidate_veto_v0p5": candidate_veto_v0p5,
            "scrambles": n_scrambles,
            "approx_nominal_trials": int(sum(
                len(spectral_widths) * len(templates) * len(subsets) * product["rest_bins"]
                for product in window_products.values()
            )),
        },
        "global_result": {
            "observed_max_snr": float(observed_global),
            "empirical_global_p_value": global_p,
            "null_median": float(np.median(global_null)),
            "null_99th_percentile": global_q99,
            "pre_registered_snr_reference": reference_snr,
            "operational_threshold_snr": operational_threshold,
            "assessment": assessment,
        },
        "windows": window_products,
        "candidate_reduction": candidate_reduction_summary,
        "completeness": completeness_summary,
        "interpretation_limits": [
            f"This search covers {len(config['windows'])} disjoint planet-frame bands totaling "
            f"{searched_bandwidth_mhz:g} MHz, not the full receiver band.",
            "A null result constrains only signals present in at least two of the three epochs and represented by the orbital template bank.",
            "The 1/3/5/9-channel boxcars approximate, but do not exactly match, every fractional-bin and acceleration-smeared line shape.",
            "Completeness is measured for exact orbital-bank templates active in epochs 1 and 3; it is not yet marginalized over orbital-model error or every duty cycle.",
            "When configured, the recurrence guard requires every claimed active epoch to exceed its stated single-epoch S/N floor.",
            provenance_limit,
            "The per-epoch RFI mask follows each circularly shifted epoch in the empirical null and completeness trials.",
            "Scramble p-values are empirical ranks with resolution 1/(N+1), not Gaussian sigma conversions.",
        ],
    }
    write_json(output_dir / "search_summary.json", summary)
    write_json(output_dir / "completeness.json", completeness)
    np.savez(
        output_dir / "scramble_nulls.npz",
        global_maxima=global_null,
        **{f"{key}_maxima": value for key, value in per_window_null.items()},
    )
    with (output_dir / "window_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "window", "on_max_snr", "spectral_width_channels", "one_channel_max_snr",
            "frequency_mhz", "scale", "phase_cycles",
            "active_epochs", "off_same_hypothesis_snr", "off_global_max_snr",
            "empirical_window_p", "null_99th_percentile",
        ])
        writer.writeheader()
        for window_id, product in window_products.items():
            best = product["on_best"]
            writer.writerow({
                "window": window_id, "on_max_snr": best["snr"],
                "spectral_width_channels": best["spectral_width_channels"],
                "one_channel_max_snr": product["one_channel_regression_best"]["snr"],
                "frequency_mhz": best["frequency_mhz"],
                "scale": best["projected_scale"],
                "phase_cycles": best["phase_offset_cycles"],
                "active_epochs": "+".join(str(index + 1) for index in best["active_epochs_zero_based"]),
                "off_same_hypothesis_snr": best["off_at_same_hypothesis_snr"],
                "off_global_max_snr": product["off_global_best"]["snr"],
                "empirical_window_p": product["empirical_null"]["p_value_window"],
                "null_99th_percentile": product["empirical_null"]["null_99th_percentile"],
            })
    _plot_calibration(global_null, observed_global, output_dir / "false_alarm_calibration.png")
    _plot_completeness(completeness, output_dir / "completeness_curve.png")
    print(json.dumps(summary["global_result"], indent=2), flush=True)
    print("Completeness:", json.dumps(completeness_summary["levels"], indent=2), flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="seti-repeater")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser("extract", help="Fetch configured filterbank slices")
    extract.add_argument("--config", required=True)
    extract.add_argument("--data-dir", required=True)
    extract.add_argument("--workers", type=int, default=12)
    extract.set_defaults(function=command_extract)

    validate = subparsers.add_parser("validate", help="Run known-answer and loss-model checks")
    validate.add_argument("--seed", type=int, default=481516)
    validate.add_argument("--tsamp", type=float, default=16.777216)
    validate.add_argument("--channel-width", type=float, default=3.814697265625)
    validate.add_argument("--output")
    validate.set_defaults(function=command_validate)

    search = subparsers.add_parser("search", help="Run the configured planet-frame search")
    search.add_argument("--config", required=True)
    search.add_argument("--data-dir", required=True)
    search.add_argument("--output-dir", required=True)
    search.add_argument("--scrambles", type=int)
    search.set_defaults(function=command_search)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        args.function(args)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
