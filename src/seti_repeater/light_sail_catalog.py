"""Pure metadata helpers for the LS2 candidate-system inventory.

LS2 deliberately stops before opening any radio spectral payload.  The
functions in this module normalize public-catalogue metadata, identify planet
pairs with enough transit geometry for a later conjunction calculation, and
summarize archive records without interpreting their signal values.
"""

from __future__ import annotations

from collections import Counter
import math
import re
from typing import Any, Iterable, Mapping, Sequence


def normalize_target_name(value: str) -> str:
    """Return a conservative comparison key for public target aliases."""

    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def resolve_archive_aliases(
    requested_aliases: Sequence[str], catalog_targets: Iterable[str]
) -> list[str]:
    """Resolve only exact normalized aliases from an archive target list.

    Substring or coordinate matching is intentionally excluded: a false target
    association is more damaging than an unresolved alias at this stage.
    """

    requested = {
        normalize_target_name(alias)
        for alias in requested_aliases
        if normalize_target_name(alias)
    }
    return sorted(
        {
            str(target)
            for target in catalog_targets
            if normalize_target_name(str(target)) in requested
        },
        key=lambda value: (normalize_target_name(value), value),
    )


def _finite_positive(value: Any) -> bool:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(parsed) and parsed > 0.0


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def geometry_planet_inventory(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Identify transiting planets usable in a later conjunction calculation."""

    eligible: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for source in records:
        record = dict(source)
        reasons: list[str] = []
        if int(record.get("tran_flag") or 0) != 1:
            reasons.append("not_flagged_transiting")
        if not _finite_positive(record.get("pl_orbper")):
            reasons.append("missing_positive_period")
        if not _finite(record.get("pl_tranmid")):
            reasons.append("missing_transit_midpoint")
        if not _finite_positive(record.get("pl_orbsmax")):
            reasons.append("missing_positive_semimajor_axis")
        compact = {
            key: record.get(key)
            for key in (
                "pl_name",
                "hostname",
                "pl_orbper",
                "pl_orbpererr1",
                "pl_orbpererr2",
                "pl_tranmid",
                "pl_tranmiderr1",
                "pl_tranmiderr2",
                "pl_orbsmax",
                "pl_orbeccen",
                "pl_orbincl",
                "tran_flag",
                "sy_dist",
                "st_rad",
                "rowupdate",
            )
        }
        if reasons:
            rejected.append({**compact, "reasons": reasons})
        else:
            eligible.append(compact)

    eligible.sort(key=lambda item: (float(item["pl_orbsmax"]), str(item["pl_name"])))
    adjacent_pairs = []
    for inner, outer in zip(eligible, eligible[1:]):
        adjacent_pairs.append(
            {
                "inner_planet": inner["pl_name"],
                "outer_planet": outer["pl_name"],
                "semimajor_axis_gap_au": float(outer["pl_orbsmax"])
                - float(inner["pl_orbsmax"]),
            }
        )
    return {
        "eligible_planets": eligible,
        "rejected_planets": rejected,
        "eligible_planet_count": len(eligible),
        "adjacent_pairs": adjacent_pairs,
        "geometry_ready": len(eligible) >= 2,
    }


def classify_archive_product(url: Any) -> str:
    """Classify relevant Breakthrough Listen products from their public URL."""

    lowered = str(url or "").casefold()
    if lowered.endswith(".gpuspec.8.0001.h5"):
        return "high_time_resolution_hdf5"
    if lowered.endswith(".gpuspec.0002.h5"):
        return "medium_resolution_hdf5"
    if lowered.endswith(".gpuspec.0000.h5") or lowered.endswith("_fine.h5"):
        return "fine_resolution_hdf5"
    if lowered.endswith(".h5"):
        return "other_hdf5"
    if lowered.endswith(".fil"):
        return "filterbank"
    return "other"


def summarize_cadence_records(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize one cadence API response without opening linked data files."""

    rows = [dict(record) for record in records]
    product_counts = Counter(classify_archive_product(row.get("url")) for row in rows)
    mjds = sorted(
        {
            float(row["mjd"])
            for row in rows
            if _finite(row.get("mjd"))
        }
    )
    dates = sorted(
        {
            str(row["utc"])
            for row in rows
            if row.get("utc") not in (None, "")
        }
    )
    center_frequencies = sorted(
        {
            float(row["center_freq"])
            for row in rows
            if _finite(row.get("center_freq"))
        }
    )
    return {
        "record_count": len(rows),
        "product_counts": dict(sorted(product_counts.items())),
        "distinct_mjd_count": len(mjds),
        "mjd_min": mjds[0] if mjds else None,
        "mjd_max": mjds[-1] if mjds else None,
        "utc_values": dates,
        "center_frequencies_mhz": center_frequencies,
        "telescopes": sorted(
            {
                str(row["telescope"])
                for row in rows
                if row.get("telescope") not in (None, "")
            }
        ),
        "has_medium_resolution_hdf5": product_counts["medium_resolution_hdf5"] > 0,
        "has_high_time_resolution_hdf5": (
            product_counts["high_time_resolution_hdf5"] > 0
        ),
        "has_at_least_six_scan_times": len(mjds) >= 6,
    }


def rank_target_inventory(targets: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Apply the frozen LS2 priority order and header-preflight gate."""

    ranked: list[dict[str, Any]] = []
    for source in targets:
        target = dict(source)
        cadences = target.get("cadences", [])
        candidate_cadences = [
            cadence
            for cadence in cadences
            if cadence.get("summary", {}).get("has_medium_resolution_hdf5")
            and cadence.get("summary", {}).get("has_at_least_six_scan_times")
        ]
        ranked.append(
            {
                "priority": int(target["priority"]),
                "target_id": target["target_id"],
                "hostname": target["hostname"],
                "geometry_ready": bool(target["geometry"]["geometry_ready"]),
                "resolved_archive_aliases": list(target["resolved_archive_aliases"]),
                "cadence_count": len(cadences),
                "candidate_cadence_count": len(candidate_cadences),
                "candidate_cadence_urls": [
                    cadence["cadence_url"] for cadence in candidate_cadences
                ],
                "eligible_for_header_preflight": bool(
                    target["geometry"]["geometry_ready"] and candidate_cadences
                ),
            }
        )
    ranked.sort(key=lambda item: (item["priority"], item["target_id"]))
    return ranked
