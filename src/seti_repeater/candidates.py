"""Candidate peak reduction, clustering, and auditable RFI-family flags."""

from __future__ import annotations

import numpy as np


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
        elif "arithmetic_frequency_family" in flags:
            disposition = "rfi_family_veto_pending_manual_review"
        else:
            disposition = "survives_for_followup"
        cluster["disposition"] = disposition
