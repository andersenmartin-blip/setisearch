#!/usr/bin/env python3
"""Fetch the official GJ 849 b orbit and host astrometry only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


NASA_TAP_API = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
PLANET_NAME = "GJ 849 b"
FIELDS = (
    "pl_name",
    "hostname",
    "hip_name",
    "hd_name",
    "ra",
    "dec",
    "rastr",
    "decstr",
    "sy_dist",
    "sy_plx",
    "sy_pmra",
    "sy_pmdec",
    "st_radv",
    "pl_orbper",
    "pl_orbsmax",
    "pl_orbeccen",
    "pl_orbtper",
    "pl_orblper",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results_m17_selected_metadata/gj849b.json"),
    )
    args = parser.parse_args()

    query = (
        f"select {','.join(FIELDS)} from pscomppars "
        f"where pl_name='{PLANET_NAME}'"
    )
    url = f"{NASA_TAP_API}?{urlencode({'query': query, 'format': 'json'})}"
    request = Request(url, headers={"User-Agent": "setisearch-m17-metadata/1.0"})
    with urlopen(request, timeout=120) as response:
        payload = response.read(5_000_000)
        status = int(getattr(response, "status", response.getcode()))
    records = json.loads(payload.decode("utf-8"))
    if status != 200 or len(records) != 1 or records[0].get("pl_name") != PLANET_NAME:
        raise RuntimeError(f"Unexpected official metadata response: {status=} {records=}")
    record = records[0]
    missing = [field for field in FIELDS if record.get(field) is None]
    if missing:
        raise RuntimeError(f"Selected record is incomplete: {missing}")

    result = {
        "purpose": "Milestone 17 selected-target official metadata completion",
        "spectral_payload_inspected": False,
        "source": "NASA Exoplanet Archive pscomppars composite record",
        "query": query,
        "api_url": url,
        "http_status": status,
        "record": record,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(record, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
