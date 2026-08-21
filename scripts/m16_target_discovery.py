#!/usr/bin/env python3
"""Metadata-only discovery of new low-smearing exoplanet cadences.

The script reads catalogue/API JSON only.  It does not open telescope products,
read HDF5 headers, or inspect spectral payload values.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ARCHIVE_API = "https://seti.berkeley.edu/opendata/api/query-files"
NASA_TAP_API = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
SPEED_OF_LIGHT_M_S = 299_792_458.0
AU_M = 149_597_870_700.0
REFERENCE_FREQUENCY_HZ = 1_425_000_000.0
LOW_SMEARING_UPPER_DRIFT_HZ_S = 1.0

# Prior spectral-contact targets, previous ineligible screens, and targets whose
# target-specific public result pages were exposed during earlier planning.
EXCLUDED_NAMES = {
    "Proxima Centauri",
    "LHS 1140",
    "GJ 411",
    "HIP 54035",
    "GJ 687",
    "HIP 86162",
    "GJ 581",
    "HIP 74995",
    "Tau Ceti",
    "HIP 8102",
    "GJ 667 C",
    "HIP 84709",
    "GJ 273",
    "GJ 1002",
    "Ross 128",
    "HIP 57548",
}


def fetch_json(url: str, params: dict[str, str]) -> dict:
    request_url = f"{url}?{urlencode(params)}"
    record: dict = {"url": request_url, "params": params}
    try:
        request = Request(
            request_url,
            headers={"User-Agent": "setisearch-m16-metadata/1.0"},
        )
        with urlopen(request, timeout=120) as response:
            payload = response.read(50_000_000)
            record["status"] = int(getattr(response, "status", response.getcode()))
            record["final_url"] = response.geturl()
        decoded = json.loads(payload.decode("utf-8"))
        if isinstance(decoded, list):
            record["result"] = "success"
            record["data"] = decoded
        else:
            record["result"] = decoded.get("result")
            record["message"] = decoded.get("message")
            record["data"] = decoded.get("data", [])
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["data"] = []
    return record


def normalized_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def compact_archive_record(record: dict) -> dict:
    return {
        key: record.get(key)
        for key in (
            "id",
            "target",
            "telescope",
            "utc",
            "mjd",
            "center_freq",
            "file_type",
            "quality",
            "size",
            "url",
            "cadence_url",
        )
    }


def complete_orbit_query() -> str:
    columns = (
        "pl_name,hostname,hip_name,hd_name,sy_dist,sy_plx,ra,dec,sy_pmra,"
        "sy_pmdec,st_radv,pl_orbper,pl_orbsmax,pl_orbeccen,pl_orbtper,"
        "pl_orblper"
    )
    required = (
        "sy_dist", "sy_plx", "ra", "dec", "sy_pmra", "sy_pmdec", "st_radv",
        "pl_orbper", "pl_orbsmax", "pl_orbeccen", "pl_orbtper", "pl_orblper",
    )
    where = " and ".join(f"{field} is not null" for field in required)
    return f"select {columns} from pscomppars where {where}"


def orbital_drift_upper_hz_s(record: dict) -> float:
    period_s = float(record["pl_orbper"]) * 86400.0
    semi_major_m = float(record["pl_orbsmax"]) * AU_M
    eccentricity = float(record["pl_orbeccen"])
    mean_motion = 2.0 * math.pi / period_s
    periastron_acceleration = (
        mean_motion * mean_motion * semi_major_m / (1.0 - eccentricity) ** 2
    )
    return REFERENCE_FREQUENCY_HZ * periastron_acceleration / SPEED_OF_LIGHT_M_S


def archive_aliases(record: dict) -> set[str]:
    return {
        normalized_name(record.get("hostname")),
        normalized_name(record.get("hip_name")),
        normalized_name(record.get("hd_name")),
    } - {""}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("results_m16_discovery/discovery.json"))
    parser.add_argument("--archive-limit", type=int, default=10000)
    args = parser.parse_args()

    archive_params = {
        "target": "",
        "telescope": "GBT",
        "cadence": "True",
        "primaryTarget": "True",
        "center_freq": "1475.09765625",
        "grades": "fine",
        "limit": str(args.archive_limit),
    }
    archive = fetch_json(ARCHIVE_API, archive_params)
    if archive.get("error") or not archive.get("data"):
        raise RuntimeError(f"Archive discovery query failed or returned no rows: {archive}")

    nasa_query = complete_orbit_query()
    nasa = fetch_json(NASA_TAP_API, {"query": nasa_query, "format": "json"})
    if nasa.get("error") or not nasa.get("data"):
        raise RuntimeError(f"NASA orbit query failed or returned no rows: {nasa}")

    excluded = {normalized_name(value) for value in EXCLUDED_NAMES}
    orbit_index: dict[str, list[dict]] = defaultdict(list)
    for record in nasa["data"]:
        aliases = archive_aliases(record)
        if aliases & excluded:
            continue
        for alias in aliases:
            orbit_index[alias].append(record)

    grouped: dict[tuple[str, str], dict] = {}
    unmatched_targets: set[str] = set()
    for raw in archive["data"]:
        compact = compact_archive_record(raw)
        target = str(compact.get("target") or "")
        key = normalized_name(target)
        if not key or key in excluded:
            continue
        matches = orbit_index.get(key, [])
        if not matches:
            unmatched_targets.add(target)
            continue
        for orbit in matches:
            group_key = (str(orbit["pl_name"]), target)
            entry = grouped.setdefault(
                group_key,
                {
                    "archive_target": target,
                    "planet": orbit,
                    "cadence_urls": set(),
                    "archive_records": [],
                },
            )
            if compact.get("cadence_url"):
                entry["cadence_urls"].add(compact["cadence_url"])
            entry["archive_records"].append(compact)

    matches = []
    for entry in grouped.values():
        if not entry["cadence_urls"]:
            continue
        orbit = entry["planet"]
        drift = orbital_drift_upper_hz_s(orbit)
        records = sorted(
            entry["archive_records"],
            key=lambda item: (str(item.get("utc") or ""), str(item.get("url") or "")),
        )
        matches.append({
            "archive_target": entry["archive_target"],
            "planet_name": orbit["pl_name"],
            "hostname": orbit["hostname"],
            "hip_name": orbit.get("hip_name"),
            "hd_name": orbit.get("hd_name"),
            "distance_pc": float(orbit["sy_dist"]),
            "period_days": float(orbit["pl_orbper"]),
            "semi_major_axis_au": float(orbit["pl_orbsmax"]),
            "eccentricity": float(orbit["pl_orbeccen"]),
            "periastron_epoch_bjd": float(orbit["pl_orbtper"]),
            "longitude_periastron_deg": float(orbit["pl_orblper"]),
            "periastron_acceleration_upper_drift_hz_s_at_1425_mhz": drift,
            "low_smearing_bucket": bool(drift <= LOW_SMEARING_UPPER_DRIFT_HZ_S),
            "cadence_urls": sorted(entry["cadence_urls"]),
            "archive_records": records,
        })

    matches.sort(key=lambda item: (
        not item["low_smearing_bucket"],
        item["distance_pc"] if item["low_smearing_bucket"] else item["periastron_acceleration_upper_drift_hz_s_at_1425_mhz"],
        item["periastron_acceleration_upper_drift_hz_s_at_1425_mhz"],
        item["planet_name"],
        item["archive_target"],
    ))
    low_smearing = [item for item in matches if item["low_smearing_bucket"]]
    unique_hosts = []
    seen_hosts = set()
    for item in low_smearing:
        host_key = normalized_name(item["hostname"])
        if host_key in seen_hosts:
            continue
        seen_hosts.add(host_key)
        unique_hosts.append(item)
        if len(unique_hosts) == 5:
            break

    result = {
        "purpose": "Milestone 16 metadata-only discovery of a new low-smearing GBT L-band exoplanet cadence",
        "spectral_payload_inspected": False,
        "remote_telescope_products_opened": False,
        "reference_frequency_hz": REFERENCE_FREQUENCY_HZ,
        "low_smearing_upper_drift_hz_s": LOW_SMEARING_UPPER_DRIFT_HZ_S,
        "selection_order": (
            "Complete orbit/astrometry plus public GBT primary-target cadence metadata; "
            "retain drift upper bound <=1 Hz/s, rank unique hosts by distance, then drift, "
            "planet name, and archive target. The first five unique hosts advance to a "
            "separate HDF5-header cadence screen."
        ),
        "excluded_names": sorted(EXCLUDED_NAMES),
        "archive_query": {
            "url": archive.get("url"),
            "status": archive.get("status"),
            "result": archive.get("result"),
            "message": archive.get("message"),
            "row_count": len(archive["data"]),
        },
        "nasa_query": {
            "url": nasa.get("url"),
            "status": nasa.get("status"),
            "result": nasa.get("result"),
            "row_count": len(nasa["data"]),
            "query": nasa_query,
        },
        "matched_planet_target_pairs": len(matches),
        "low_smearing_pair_count": len(low_smearing),
        "top_five_unique_hosts_for_header_screen": unique_hosts,
        "all_matches": matches,
        "unmatched_archive_targets": sorted(unmatched_targets),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "archive_rows": len(archive["data"]),
        "complete_orbit_rows": len(nasa["data"]),
        "matched_pairs": len(matches),
        "low_smearing_pairs": len(low_smearing),
        "top_five": [
            {
                "archive_target": item["archive_target"],
                "planet_name": item["planet_name"],
                "distance_pc": item["distance_pc"],
                "drift_upper_hz_s": item["periastron_acceleration_upper_drift_hz_s_at_1425_mhz"],
            }
            for item in unique_hosts
        ],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
