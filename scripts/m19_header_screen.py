#!/usr/bin/env python3
"""Header-only cadence screen for ranks 6-10 of the frozen M16 discovery."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from m13_catalog_probe import inspect_cadence


EXPECTED_DISCOVERY_EXTENSION = [
    {
        "archive_target": "HIP79755",
        "planet_name": "HD 147379 b",
        "cadence_urls": [
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-77605",
        ],
    },
    {
        "archive_target": "HIP43587",
        "planet_name": "55 Cnc d",
        "cadence_urls": [
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-64578",
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-69774",
        ],
    },
    {
        "archive_target": "HIP53721",
        "planet_name": "47 UMa d",
        "cadence_urls": [
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-73992",
        ],
    },
    {
        "archive_target": "HIP32769",
        "planet_name": "HD 48948 d",
        "cadence_urls": [
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-83329",
        ],
    },
    {
        "archive_target": "HIP78459",
        "planet_name": "rho CrB c",
        "cadence_urls": [
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-71771",
        ],
    },
]

CANONICAL_CADENCE_URLS = {
    "HIP79755": [
        "http://seti.berkeley.edu/opendata/api/get-cadence/--77605",
    ],
    "HIP43587": [
        "http://seti.berkeley.edu/opendata/api/get-cadence/--64578",
        "http://seti.berkeley.edu/opendata/api/get-cadence/--69774",
    ],
    "HIP53721": [
        "http://seti.berkeley.edu/opendata/api/get-cadence/--73992",
    ],
    "HIP32769": [
        "http://seti.berkeley.edu/opendata/api/get-cadence/--83329",
    ],
    "HIP78459": [
        "http://seti.berkeley.edu/opendata/api/get-cadence/--71771",
    ],
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def normalized_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def unique_ranked_low_smearing_hosts(discovery: dict) -> list[dict]:
    ranked = []
    seen_hosts = set()
    for item in discovery["all_matches"]:
        if not item["low_smearing_bucket"]:
            continue
        host_key = normalized_name(item["hostname"])
        if host_key in seen_hosts:
            continue
        seen_hosts.add(host_key)
        ranked.append(item)
    return ranked


def compact_expected(record: dict) -> dict:
    return {
        "archive_target": record["archive_target"],
        "planet_name": record["planet_name"],
        "cadence_urls": record["cadence_urls"],
    }


def ensure_boundary(value: object) -> None:
    if isinstance(value, dict):
        if "spectral_dataset_values_read" in value:
            assert value["spectral_dataset_values_read"] is False
        for child in value.values():
            ensure_boundary(child)
    elif isinstance(value, list):
        for child in value:
            ensure_boundary(child)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--discovery",
        type=Path,
        default=Path("results_m16_discovery/discovery.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results_m19_header_screen/header_screen.json"),
    )
    args = parser.parse_args()

    discovery = read_json(args.discovery)
    ranked_hosts = unique_ranked_low_smearing_hosts(discovery)
    extension = ranked_hosts[5:10]
    observed = [compact_expected(item) for item in extension]
    if observed != EXPECTED_DISCOVERY_EXTENSION:
        raise RuntimeError(
            "Discovery ranks 6-10 do not match the frozen Milestone 19 input: "
            f"{observed!r}"
        )

    screened = []
    for rank, (expected, discovered) in enumerate(
        zip(EXPECTED_DISCOVERY_EXTENSION, extension),
        6,
    ):
        cadences = []
        canonical_urls = CANONICAL_CADENCE_URLS[expected["archive_target"]]
        for url in canonical_urls:
            print(f"header screen rank {rank}: {url}", flush=True)
            cadences.append(inspect_cadence(url, probe_hdf5_headers=True))
        qualifying = []
        for cadence in cadences:
            for match in cadence["qualifying_hdf5_abacad_cadences"]:
                qualifying.append({
                    "cadence_url": cadence["cadence_url"],
                    **match,
                })
        qualifying.sort(key=lambda item: (item["start_mjd"], item["cadence_url"]))
        screened.append({
            "rank": rank,
            "archive_target": expected["archive_target"],
            "planet_name": expected["planet_name"],
            "hostname": discovered["hostname"],
            "distance_pc": discovered["distance_pc"],
            "drift_upper_hz_s_at_1425_mhz": discovered[
                "periastron_acceleration_upper_drift_hz_s_at_1425_mhz"
            ],
            "planet_record": {
                key: discovered[key]
                for key in (
                    "planet_name",
                    "hostname",
                    "hip_name",
                    "hd_name",
                    "distance_pc",
                    "period_days",
                    "semi_major_axis_au",
                    "eccentricity",
                    "periastron_epoch_bjd",
                    "longitude_periastron_deg",
                )
            },
            "discovery_cadence_urls": expected["cadence_urls"],
            "canonical_cadence_urls": canonical_urls,
            "cadences": cadences,
            "qualifying_hdf5_abacad_cadences": qualifying,
            "qualifying_count": len(qualifying),
        })

    selected = None
    for target in screened:
        if target["qualifying_hdf5_abacad_cadences"]:
            selected = {
                "rank": target["rank"],
                "archive_target": target["archive_target"],
                "planet_name": target["planet_name"],
                "hostname": target["hostname"],
                "distance_pc": target["distance_pc"],
                "drift_upper_hz_s_at_1425_mhz": target[
                    "drift_upper_hz_s_at_1425_mhz"
                ],
                "planet_record": target["planet_record"],
                "cadence": target["qualifying_hdf5_abacad_cadences"][0],
            }
            break

    result = {
        "purpose": "Milestone 19 HDF5-header-only cadence qualification",
        "spectral_payload_inspected": False,
        "spectral_dataset_values_read": False,
        "selection_rule": (
            "Within frozen discovery ranks 6-10, select the nearest ranked host "
            "with at least one complete, compatible, byte-range-accessible fine "
            "HDF5 ABACAD cadence covering the full established guarded frequency "
            "range; choose its earliest qualifying cadence."
        ),
        "prior_discovery_ranks_already_resolved": [1, 2, 3, 4, 5],
        "frozen_extension_ranks": [6, 7, 8, 9, 10],
        "discovery_result_sha256": (
            "0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750"
        ),
        "screened_targets": screened,
        "selected": selected,
        "technical_no_selection": selected is None,
    }
    ensure_boundary(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "screened": [
            {
                "rank": item["rank"],
                "target": item["archive_target"],
                "qualifying": item["qualifying_count"],
            }
            for item in screened
        ],
        "selected": (
            None
            if selected is None
            else {
                "rank": selected["rank"],
                "target": selected["archive_target"],
                "planet": selected["planet_name"],
                "cadence_url": selected["cadence"]["cadence_url"],
                "start_mjd": selected["cadence"]["start_mjd"],
            }
        ),
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
