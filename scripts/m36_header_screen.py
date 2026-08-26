#!/usr/bin/env python3
"""Header-only cadence screen for frozen M16 unique-host ranks 36--40."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from m13_catalog_probe import inspect_cadence


EXPECTED_DISCOVERY_EXTENSION = [
    {
        "archive_target": "HIP48714",
        "planet_name": "HIP 48714 b",
        "cadence_urls": [
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-68360",
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-76348",
        ],
    },
    {
        "archive_target": "HIP84607",
        "planet_name": "HD 156668 b",
        "cadence_urls": [
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-85168",
        ],
    },
    {
        "archive_target": "HIP1499",
        "planet_name": "HD 1461 b",
        "cadence_urls": [
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-71139",
        ],
    },
    {
        "archive_target": "HIP113357",
        "planet_name": "51 Peg b",
        "cadence_urls": [
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-80977",
        ],
    },
    {
        "archive_target": "HIP67275",
        "planet_name": "tau Boo b",
        "cadence_urls": [
            "http://seti.berkeley.edu/opendata/api/get-cadence/-grades:fine;-68396",
        ],
    },
]

CANONICAL_CADENCE_URLS = {
    "HIP48714": [
        "http://seti.berkeley.edu/opendata/api/get-cadence/--68360",
        "http://seti.berkeley.edu/opendata/api/get-cadence/--76348",
    ],
    "HIP84607": ["http://seti.berkeley.edu/opendata/api/get-cadence/--85168"],
    "HIP1499": ["http://seti.berkeley.edu/opendata/api/get-cadence/--71139"],
    "HIP113357": ["http://seti.berkeley.edu/opendata/api/get-cadence/--80977"],
    "HIP67275": ["http://seti.berkeley.edu/opendata/api/get-cadence/--68396"],
}

FROZEN_WIDTH_BANK = [1, 3, 5, 9, 17, 33, 65, 129]
FROZEN_REPORT_CAP = 2200
MAXIMUM_HYPOTHESIS_PEAKS_PER_WINDOW = 2016


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def normalized_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def unique_ranked_hosts(discovery: dict) -> list[dict]:
    ranked = []
    seen_hosts = set()
    for item in discovery["all_matches"]:
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


def require_successful_header_probe(cadence: dict, rank: int) -> None:
    """Stop rather than skip a higher-ranked host after an incomplete probe."""
    if (
        cadence.get("api_status") != 200
        or cadence.get("api_result") != "success"
        or cadence.get("api_error") is not None
    ):
        raise RuntimeError(
            f"Rank {rank} cadence API probe was incomplete: "
            f"{cadence.get('cadence_url')}"
        )
    urls = cadence.get("fine_hdf5_urls", [])
    headers = cadence.get("hdf5_headers", [])
    if not urls or len(headers) != len(urls):
        raise RuntimeError(
            f"Rank {rank} fine-HDF5 enumeration was incomplete: "
            f"{cadence.get('cadence_url')}"
        )
    failed = [item.get("url") for item in headers if "error" in item]
    if failed:
        raise RuntimeError(
            f"Rank {rank} HDF5 header probe failed for: {failed!r}"
        )


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
        default=Path("results_m36_header_screen/header_screen.json"),
    )
    args = parser.parse_args()

    discovery = read_json(args.discovery)
    ranked_hosts = unique_ranked_hosts(discovery)
    assert len(ranked_hosts) == 43
    assert sum(item["low_smearing_bucket"] for item in ranked_hosts) == 30
    extension = ranked_hosts[35:40]
    observed = [compact_expected(item) for item in extension]
    if observed != EXPECTED_DISCOVERY_EXTENSION:
        raise RuntimeError(
            "Discovery ranks 36--40 do not match the frozen Milestone 36 input: "
            f"{observed!r}"
        )

    screened = []
    for rank, (expected, discovered) in enumerate(
        zip(EXPECTED_DISCOVERY_EXTENSION, extension),
        36,
    ):
        cadences = []
        canonical_urls = CANONICAL_CADENCE_URLS[expected["archive_target"]]
        for url in canonical_urls:
            print(f"header screen rank {rank}: {url}", flush=True)
            cadence = inspect_cadence(url, probe_hdf5_headers=True)
            require_successful_header_probe(cadence, rank)
            cadences.append(cadence)
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
            "low_smearing_bucket": discovered["low_smearing_bucket"],
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
                "additional_qualifying_cadences": target[
                    "qualifying_hdf5_abacad_cadences"
                ][1:],
            }
            break

    result = {
        "purpose": "Milestone 36 ranks 36--40 high-smearing HDF5-header-only qualification",
        "spectral_payload_inspected": False,
        "spectral_dataset_values_read": False,
        "selection_rule": (
            "Within frozen discovery extension ranks 36--40, select the first "
            "host with at least one complete, compatible fine HDF5 ABACAD cadence "
            "covering the established guarded range; choose its earliest "
            "qualifying cadence as the prospective primary."
        ),
        "prior_discovery_ranks_already_resolved": list(range(1, 36)),
        "frozen_extension_ranks": [36, 37, 38, 39, 40],
        "high_smearing_width_bank_frozen": FROZEN_WIDTH_BANK,
        "candidate_report_cap_frozen": FROZEN_REPORT_CAP,
        "maximum_hypothesis_peaks_per_window": MAXIMUM_HYPOTHESIS_PEAKS_PER_WINDOW,
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
                "additional_qualifying": len(
                    selected["additional_qualifying_cadences"]
                ),
            }
        ),
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
