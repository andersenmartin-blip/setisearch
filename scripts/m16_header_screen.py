#!/usr/bin/env python3
"""Header-only cadence screen for the frozen Milestone 16 discovery shortlist."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from m13_catalog_probe import inspect_cadence


EXPECTED_DISCOVERY_TOP = [
    {
        "archive_target": "GJ876",
        "planet_name": "GJ 876 e",
        "cadence_urls": [
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-76697",
        ],
    },
    {
        "archive_target": "HIP114622",
        "planet_name": "HD 219134 h",
        "cadence_urls": [
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-63424",
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-65393",
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-66869",
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-67073",
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-67169",
        ],
    },
    {
        "archive_target": "HIP65859",
        "planet_name": "GJ 514 b",
        "cadence_urls": [
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-82035",
        ],
    },
    {
        "archive_target": "HIP109388",
        "planet_name": "GJ 849 b",
        "cadence_urls": [
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-73890",
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-74424",
        ],
    },
    {
        "archive_target": "HIP83043",
        "planet_name": "GJ 649 b",
        "cadence_urls": [
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-70291",
        ],
    },
]

CANONICAL_CADENCE_URLS = {
    "GJ876": [
        "http://seti.berkeley.edu/opendata/api/get-cadence/--76697",
    ],
    "HIP114622": [
        "http://seti.berkeley.edu/opendata/api/get-cadence/--63424",
        "http://seti.berkeley.edu/opendata/api/get-cadence/--65393",
        "http://seti.berkeley.edu/opendata/api/get-cadence/--66869",
        "http://seti.berkeley.edu/opendata/api/get-cadence/--67073",
        "http://seti.berkeley.edu/opendata/api/get-cadence/--67169",
    ],
    "HIP65859": [
        "http://seti.berkeley.edu/opendata/api/get-cadence/--82035",
    ],
    "HIP109388": [
        "http://seti.berkeley.edu/opendata/api/get-cadence/--73890",
        "http://seti.berkeley.edu/opendata/api/get-cadence/--74424",
    ],
    "HIP83043": [
        "http://seti.berkeley.edu/opendata/api/get-cadence/--70291",
    ],
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


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
        default=Path("results_m16_header_screen/header_screen.json"),
    )
    args = parser.parse_args()

    discovery = read_json(args.discovery)
    observed_top = [
        compact_expected(item)
        for item in discovery["top_five_unique_hosts_for_header_screen"]
    ]
    if observed_top != EXPECTED_DISCOVERY_TOP:
        raise RuntimeError(
            "Discovery shortlist does not match the frozen header-screen input: "
            f"{observed_top!r}"
        )

    screened = []
    for rank, (expected, discovered) in enumerate(
        zip(EXPECTED_DISCOVERY_TOP, discovery["top_five_unique_hosts_for_header_screen"]),
        1,
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
        "purpose": "Milestone 16 HDF5-header-only cadence qualification",
        "spectral_payload_inspected": False,
        "spectral_dataset_values_read": False,
        "selection_rule": (
            "Select the nearest discovery-ranked host with at least one complete, "
            "compatible, byte-range-accessible fine HDF5 ABACAD cadence covering "
            "the full established guarded frequency range; choose its earliest "
            "qualifying cadence."
        ),
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
                "target": selected["archive_target"],
                "planet": selected["planet_name"],
                "cadence_url": selected["cadence"]["cadence_url"],
                "start_mjd": selected["cadence"]["start_mjd"],
            }
        ),
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
