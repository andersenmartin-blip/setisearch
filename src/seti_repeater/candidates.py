"""Candidate peak reduction, clustering, and auditable RFI-family flags."""

from __future__ import annotations

import numpy as np


def _stack_active_epochs(
    active: np.ndarray,
    stack_statistic: str,
    minimum_active_epoch_snr: float | None,
) -> np.ndarray:
    """Apply the configured recurrence statistic to [epoch, frequency] values."""
    if stack_statistic == "sum":
        stack = np.sum(active, axis=0) / np.sqrt(active.shape[0])
    elif stack_statistic == "minimum_epoch":
        stack = np.sqrt(active.shape[0]) * np.min(active, axis=0)
    else:
        raise ValueError(f"Unknown stack statistic: {stack_statistic}")
    if minimum_active_epoch_snr is not None:
        stack = np.where(
            np.all(active >= minimum_active_epoch_snr, axis=0), stack, -np.inf
        )
    return stack


def evaluate_local_off_veto(
    spectral_bank: np.ndarray,
    rest_frequency_mhz: np.ndarray,
    candidate: dict,
    templates: list[tuple[float, float]],
    subsets: list[tuple[int, ...]],
    spectral_widths: tuple[int, ...],
    tolerance_hz: float,
    single_epoch_snr_floor: float,
    minimum_active_epoch_snr: float | None = None,
    stack_statistic: str = "sum",
) -> dict:
    """Measure nearby recurring and exact-track evidence in adjacent OFF scans.

    The local search deliberately considers every configured width, orbital
    template, and activity subset. The exact-track diagnostic is evaluated
    separately so a single strong adjacent OFF scan cannot be hidden by the
    recurrence requirement or a single-epoch RFI mask.
    """
    if spectral_bank.ndim != 4:
        raise ValueError("spectral_bank must have [width, template, epoch, frequency] axes")
    if spectral_bank.shape[:2] != (len(spectral_widths), len(templates)):
        raise ValueError("spectral bank shape does not match widths/templates")

    best = candidate.get("best_hypothesis", candidate)
    center_index = int(best["frequency_index"])
    df_hz = abs(float(rest_frequency_mhz[1] - rest_frequency_mhz[0])) * 1e6
    tolerance_bins = int(np.ceil(tolerance_hz / df_hz))
    lo = max(0, center_index - tolerance_bins)
    hi = min(rest_frequency_mhz.size, center_index + tolerance_bins + 1)
    if lo >= hi:
        raise ValueError("candidate neighbourhood is outside the frequency grid")

    local_best: dict | None = None
    for width_index, width in enumerate(spectral_widths):
        for template_index, (scale, phase) in enumerate(templates):
            for subset in subsets:
                active = spectral_bank[
                    width_index, template_index, list(subset), lo:hi
                ]
                stack = _stack_active_epochs(
                    active, stack_statistic, minimum_active_epoch_snr
                )
                if not np.any(np.isfinite(stack)):
                    continue
                local_index = int(np.nanargmax(stack))
                frequency_index = lo + local_index
                record = {
                    "snr": float(stack[local_index]),
                    "frequency_mhz": float(rest_frequency_mhz[frequency_index]),
                    "frequency_index": frequency_index,
                    "offset_from_candidate_hz": float(
                        (rest_frequency_mhz[frequency_index]
                         - rest_frequency_mhz[center_index]) * 1e6
                    ),
                    "spectral_width_channels": int(width),
                    "spectral_width_index": int(width_index),
                    "template_index": int(template_index),
                    "projected_scale": float(scale),
                    "phase_offset_cycles": float(phase),
                    "active_epochs_zero_based": list(subset),
                    "epoch_values_at_frequency": [
                        float(value)
                        for value in spectral_bank[
                            width_index, template_index, :, frequency_index
                        ]
                    ],
                }
                if local_best is None or record["snr"] > local_best["snr"]:
                    local_best = record

    width_index = int(best["spectral_width_index"])
    template_index = int(best["template_index"])
    active_epochs = [int(epoch) for epoch in best["active_epochs_zero_based"]]
    exact_epoch_values = spectral_bank[
        width_index, template_index, :, center_index
    ]
    matching_epochs = [
        epoch for epoch in active_epochs
        if float(exact_epoch_values[epoch]) >= single_epoch_snr_floor
    ]
    return {
        "local_tolerance_hz": float(tolerance_hz),
        "local_tolerance_bins": tolerance_bins,
        "best_local_recurrence": local_best,
        "same_candidate_track": {
            "single_epoch_snr_floor": float(single_epoch_snr_floor),
            "epoch_values": [float(value) for value in exact_epoch_values],
            "active_epochs_zero_based": active_epochs,
            "matching_active_epochs_zero_based": matching_epochs,
            "maximum_active_epoch_snr": float(max(
                exact_epoch_values[epoch] for epoch in active_epochs
            )),
        },
    }


def annotate_local_off_vetoes(
    clusters: list[dict],
    spectral_bank: np.ndarray,
    rest_frequency_mhz: np.ndarray,
    templates: list[tuple[float, float]],
    subsets: list[tuple[int, ...]],
    spectral_widths: tuple[int, ...],
    tolerance_hz: float,
    single_epoch_snr_floor: float,
    minimum_active_epoch_snr: float | None = None,
    stack_statistic: str = "sum",
) -> None:
    """Attach v0.5 OFF-source diagnostics to candidate clusters in place."""
    for cluster in clusters:
        cluster["v0p5_off_diagnostics"] = evaluate_local_off_veto(
            spectral_bank, rest_frequency_mhz, cluster, templates, subsets,
            spectral_widths, tolerance_hz, single_epoch_snr_floor,
            minimum_active_epoch_snr, stack_statistic,
        )


def build_receiver_frame_signature(
    cluster: dict,
    scans: list[dict],
    config: dict,
    local_half_width_hz: float,
    _stationary_cache: dict[tuple[int, int], np.ndarray] | None = None,
    _factor_cache: dict[tuple[int, float, float], np.ndarray] | None = None,
    _target=None,
    _location=None,
) -> list[dict]:
    """Reconstruct strongest local topocentric peaks for active ON epochs."""
    from .orbit import celestial_frequency_factor, make_location, make_target
    from .spectral import normalized_boxcar

    best = cluster["best_hypothesis"]
    rest_mhz = float(best["frequency_mhz"])
    scale = float(best["projected_scale"])
    phase = float(best["phase_offset_cycles"])
    width = int(best["spectral_width_channels"])
    target = make_target(config["target"]) if _target is None else _target
    location = make_location(config["observatory"]) if _location is None else _location
    stationary_cache = {} if _stationary_cache is None else _stationary_cache
    factor_cache = {} if _factor_cache is None else _factor_cache
    signature = []
    for epoch in best["active_epochs_zero_based"]:
        epoch = int(epoch)
        scan = scans[epoch]
        factor_key = (epoch, scale, phase)
        if factor_key not in factor_cache:
            factor_cache[factor_key] = celestial_frequency_factor(
                scan["times"], scale, phase, target, location, config["orbit"]
            )[0]
        factor = factor_cache[factor_key]
        predicted_mid_mhz = float(np.mean(rest_mhz * factor))
        frequencies = scan["frequency_mhz"]
        local = np.abs((frequencies - predicted_mid_mhz) * 1e6) <= local_half_width_hz
        if not np.any(local):
            raise ValueError("receiver-frame neighbourhood is outside the scan")
        stationary_key = (epoch, width)
        if stationary_key not in stationary_cache:
            filtered = normalized_boxcar(scan["normalized"], width)
            stationary_cache[stationary_key] = (
                np.sum(filtered, axis=0) / np.sqrt(filtered.shape[0])
            )
        stationary = stationary_cache[stationary_key]
        local_indices = np.flatnonzero(local)
        frequency_index = int(local_indices[np.nanargmax(stationary[local])])
        signature.append({
            "epoch_zero_based": epoch,
            "predicted_mid_mhz": predicted_mid_mhz,
            "peak_frequency_mhz": float(frequencies[frequency_index]),
            "peak_snr": float(stationary[frequency_index]),
            "offset_from_prediction_hz": float(
                (frequencies[frequency_index] - predicted_mid_mhz) * 1e6
            ),
        })
    return signature


def flag_receiver_frame_aliases(
    clusters: list[dict],
    tolerance_hz: float,
    minimum_shared_epochs: int,
    local_peak_snr_floor: float,
) -> None:
    """Flag different rest/template solutions that resolve to the same receiver peaks."""
    for cluster in clusters:
        cluster["v0p5_receiver_frame_aliases"] = []
    for left_index, left in enumerate(clusters):
        left_by_epoch = {
            int(item["epoch_zero_based"]): item
            for item in left.get("v0p5_receiver_frame_signature", [])
        }
        for right_index in range(left_index + 1, len(clusters)):
            right = clusters[right_index]
            right_by_epoch = {
                int(item["epoch_zero_based"]): item
                for item in right.get("v0p5_receiver_frame_signature", [])
            }
            matches = []
            for epoch in sorted(set(left_by_epoch) & set(right_by_epoch)):
                left_peak = left_by_epoch[epoch]
                right_peak = right_by_epoch[epoch]
                delta_hz = float(
                    (right_peak["peak_frequency_mhz"]
                     - left_peak["peak_frequency_mhz"]) * 1e6
                )
                if (
                    float(left_peak["peak_snr"]) >= local_peak_snr_floor
                    and float(right_peak["peak_snr"]) >= local_peak_snr_floor
                    and abs(delta_hz) <= tolerance_hz
                ):
                    matches.append({
                        "epoch_zero_based": epoch,
                        "delta_hz": delta_hz,
                        "left_peak_snr": float(left_peak["peak_snr"]),
                        "right_peak_snr": float(right_peak["peak_snr"]),
                    })
            if len(matches) < minimum_shared_epochs:
                continue
            left["v0p5_receiver_frame_aliases"].append({
                "other_cluster_index": right_index,
                "other_frequency_mhz": float(right["cluster_frequency_mhz"]),
                "matched_active_epochs": matches,
            })
            right["v0p5_receiver_frame_aliases"].append({
                "other_cluster_index": left_index,
                "other_frequency_mhz": float(left["cluster_frequency_mhz"]),
                "matched_active_epochs": matches,
            })


def annotate_receiver_frame_aliases(
    clusters: list[dict],
    scans: list[dict],
    config: dict,
    local_half_width_hz: float,
    tolerance_hz: float,
    minimum_shared_epochs: int,
    local_peak_snr_floor: float,
) -> None:
    """Build receiver signatures and flag aliases in place."""
    from .orbit import make_location, make_target

    stationary_cache: dict[tuple[int, int], np.ndarray] = {}
    factor_cache: dict[tuple[int, float, float], np.ndarray] = {}
    target = make_target(config["target"])
    location = make_location(config["observatory"])
    for cluster in clusters:
        cluster["v0p5_receiver_frame_signature"] = build_receiver_frame_signature(
            cluster, scans, config, local_half_width_hz,
            stationary_cache, factor_cache, target, location,
        )
    flag_receiver_frame_aliases(
        clusters, tolerance_hz, minimum_shared_epochs, local_peak_snr_floor
    )


def build_single_epoch_rfi_mask(
    spectral_bank: np.ndarray,
    strong_snr: float,
    other_epochs_below_snr: float,
    guard_channels: int,
) -> np.ndarray:
    """Return [width, template, epoch, frequency] masks for isolated strong epochs."""
    ordered = np.sort(spectral_bank, axis=2)
    base = (ordered[:, :, -1, :] >= strong_snr) & (
        ordered[:, :, -2, :] < other_epochs_below_snr
    )
    strongest_epoch = np.argmax(spectral_bank, axis=2)
    epoch_mask = np.zeros_like(spectral_bank, dtype=bool)
    for epoch in range(spectral_bank.shape[2]):
        epoch_mask[:, :, epoch, :] = base & (strongest_epoch == epoch)
    template_mask = np.any(epoch_mask, axis=0)
    dilated = template_mask.copy()
    for offset in range(1, guard_channels + 1):
        right = np.roll(template_mask, offset, axis=-1)
        right[..., :offset] = False
        left = np.roll(template_mask, -offset, axis=-1)
        left[..., -offset:] = False
        dilated |= right | left
    return np.broadcast_to(dilated[None, ...], spectral_bank.shape).copy()


def collect_hypothesis_peaks(
    spectral_bank: np.ndarray,
    rest_frequency_mhz: np.ndarray,
    templates: list[tuple[float, float]],
    subsets: list[tuple[int, ...]],
    spectral_widths: tuple[int, ...],
    peaks_per_hypothesis: int,
    snr_floor: float,
    minimum_active_epoch_snr: float | None = None,
    stack_statistic: str = "sum",
    exclusion_mask: np.ndarray | None = None,
) -> list[dict]:
    """Retain a few non-adjacent peaks from every width/orbit/activity hypothesis."""
    records: list[dict] = []
    for width_index, width in enumerate(spectral_widths):
        separation = max(1, width // 2)
        for template_index, (scale, phase) in enumerate(templates):
            for subset in subsets:
                active = spectral_bank[width_index, template_index, list(subset)]
                if stack_statistic == "sum":
                    stack = np.sum(active, axis=0) / np.sqrt(len(subset))
                elif stack_statistic == "minimum_epoch":
                    stack = np.sqrt(len(subset)) * np.min(active, axis=0)
                else:
                    raise ValueError(f"Unknown stack statistic: {stack_statistic}")
                if minimum_active_epoch_snr is not None:
                    stack = np.where(
                        np.all(active >= minimum_active_epoch_snr, axis=0), stack, -np.inf
                    )
                if exclusion_mask is not None:
                    mask = exclusion_mask[width_index, template_index]
                    if mask.ndim == 2:
                        mask = np.any(mask[list(subset)], axis=0)
                    stack = np.where(mask, -np.inf, stack)
                scores = np.nan_to_num(stack, nan=-np.inf)
                pool_size = min(scores.size, max(peaks_per_hypothesis * 5, peaks_per_hypothesis))
                pool = np.argpartition(scores, -pool_size)[-pool_size:]
                pool = pool[np.argsort(scores[pool])[::-1]]
                selected: list[int] = []
                for frequency_index in pool:
                    if scores[frequency_index] < snr_floor:
                        break
                    if any(abs(int(frequency_index) - prior) <= separation for prior in selected):
                        continue
                    selected.append(int(frequency_index))
                    epoch_values = spectral_bank[
                        width_index, template_index, :, frequency_index
                    ]
                    records.append({
                        "snr": float(scores[frequency_index]),
                        "frequency_mhz": float(rest_frequency_mhz[frequency_index]),
                        "frequency_index": int(frequency_index),
                        "spectral_width_channels": int(width),
                        "spectral_width_index": int(width_index),
                        "template_index": int(template_index),
                        "projected_scale": float(scale),
                        "phase_offset_cycles": float(phase),
                        "active_epochs_zero_based": list(subset),
                        "epoch_values_at_frequency": [float(value) for value in epoch_values],
                    })
                    if len(selected) == peaks_per_hypothesis:
                        break
    return records


def cluster_peaks(records: list[dict], tolerance_hz: float) -> list[dict]:
    """Cluster redundant records by their recovered planet-frame frequency."""
    if not records:
        return []
    tolerance_mhz = tolerance_hz / 1e6
    groups: list[list[dict]] = []
    for record in sorted(records, key=lambda item: item["frequency_mhz"]):
        if not groups:
            groups.append([record])
            continue
        center = float(np.median([item["frequency_mhz"] for item in groups[-1]]))
        if abs(record["frequency_mhz"] - center) <= tolerance_mhz:
            groups[-1].append(record)
        else:
            groups.append([record])

    clusters = []
    for group in groups:
        members = sorted(group, key=lambda item: item["snr"], reverse=True)
        best = dict(members[0])
        frequencies = [item["frequency_mhz"] for item in members]
        clusters.append({
            "cluster_frequency_mhz": best["frequency_mhz"],
            "max_snr": best["snr"],
            "member_count": len(members),
            "distinct_template_count": len({item["template_index"] for item in members}),
            "distinct_spectral_widths": sorted({item["spectral_width_channels"] for item in members}),
            "distinct_activity_subsets": sorted({
                "+".join(str(epoch + 1) for epoch in item["active_epochs_zero_based"])
                for item in members
            }),
            "frequency_span_hz": float((max(frequencies) - min(frequencies)) * 1e6),
            "best_hypothesis": best,
            "top_members": members[:20],
        })
    return sorted(clusters, key=lambda item: item["max_snr"], reverse=True)


def detect_arithmetic_frequency_families(
    clusters: list[dict],
    tolerance_hz: float,
    minimum_members: int = 3,
) -> list[dict]:
    """Find three-or-more cluster combs with approximately constant spacing."""
    if len(clusters) < minimum_members:
        return []
    ordered = sorted(enumerate(clusters), key=lambda pair: pair[1]["cluster_frequency_mhz"])
    frequencies_hz = np.array([item[1]["cluster_frequency_mhz"] * 1e6 for item in ordered])
    original_indices = [item[0] for item in ordered]
    families: list[dict] = []
    seen: set[tuple[int, ...]] = set()
    for left in range(len(ordered) - 2):
        for middle in range(left + 1, len(ordered) - 1):
            spacing = frequencies_hz[middle] - frequencies_hz[left]
            if spacing <= 5 * tolerance_hz:
                continue
            members = [left, middle]
            target = frequencies_hz[middle] + spacing
            while target <= frequencies_hz[-1] + tolerance_hz:
                nearest = int(np.argmin(np.abs(frequencies_hz - target)))
                if abs(frequencies_hz[nearest] - target) <= tolerance_hz and nearest not in members:
                    members.append(nearest)
                target += spacing
            members = sorted(set(members))
            if len(members) < minimum_members:
                continue
            key = tuple(original_indices[index] for index in members)
            if key in seen:
                continue
            seen.add(key)
            families.append({
                "family_id": f"family_{len(families) + 1}",
                "spacing_hz": float(spacing),
                "cluster_indices": list(key),
                "member_frequencies_mhz": [
                    float(frequencies_hz[index] / 1e6) for index in members
                ],
            })
    return families


def apply_candidate_flags(
    clusters: list[dict],
    families: list[dict],
    operational_threshold: float,
    template_multiplicity_flag: int,
) -> None:
    family_membership: dict[int, list[str]] = {}
    for family in families:
        for cluster_index in family["cluster_indices"]:
            family_membership.setdefault(cluster_index, []).append(family["family_id"])
    for cluster_index, cluster in enumerate(clusters):
        flags = []
        if cluster["max_snr"] < operational_threshold:
            flags.append("below_global_threshold")
        if cluster.get("off_at_best_hypothesis_snr", -np.inf) >= operational_threshold:
            flags.append("off_source_coincidence")
        v0p5_off = cluster.get("v0p5_off_diagnostics")
        if v0p5_off:
            local_best = v0p5_off.get("best_local_recurrence")
            if local_best and local_best.get("snr", -np.inf) >= operational_threshold:
                flags.append("off_source_local_hypothesis_coincidence")
            if v0p5_off.get("same_candidate_track", {}).get(
                "matching_active_epochs_zero_based"
            ):
                flags.append("off_source_single_epoch_track")
        if cluster.get("v0p5_receiver_frame_aliases"):
            flags.append("receiver_frame_template_alias")
        if cluster["distinct_template_count"] >= template_multiplicity_flag:
            flags.append("high_template_multiplicity")
        if cluster["best_hypothesis"]["spectral_width_channels"] == 9:
            flags.append("widest_spectral_template")
        family_ids = family_membership.get(cluster_index, [])
        if family_ids:
            flags.append("arithmetic_frequency_family")
        cluster["frequency_family_ids"] = family_ids
        cluster["flags"] = flags
        if "below_global_threshold" in flags:
            disposition = "below_threshold"
        elif "off_source_coincidence" in flags:
            disposition = "rfi_veto_off_source"
        elif "off_source_local_hypothesis_coincidence" in flags:
            disposition = "rfi_veto_local_off_source"
        elif "off_source_single_epoch_track" in flags:
            disposition = "rfi_veto_single_adjacent_off"
        elif "receiver_frame_template_alias" in flags:
            disposition = "rfi_veto_receiver_frame_alias"
        elif "arithmetic_frequency_family" in flags:
            disposition = "rfi_family_veto_pending_manual_review"
        else:
            disposition = "survives_for_followup"
        cluster["disposition"] = disposition
