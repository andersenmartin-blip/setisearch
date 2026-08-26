#!/usr/bin/env python3
"""Fetch and validate only the official HD 156668 b metadata record."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener


NASA_TAP_API = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
PLANET_NAME = "HD 156668 b"
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
EXPECTED_TEXT = {
    "pl_name": "HD 156668 b",
    "hostname": "HD 156668",
    "hip_name": "HIP 84607",
    "hd_name": "HD 156668",
}
EXPECTED_FROZEN_NUMERIC = {
    "sy_dist": 24.3323,
    "pl_orbper": 4.6455,
    "pl_orbsmax": 0.05,
    "pl_orbeccen": 0.0,
    "pl_orbtper": 2454718.57,
    "pl_orblper": 36.0,
}


class RejectRedirects(HTTPRedirectHandler):
    """Prevent an official-metadata request from contacting another URL."""

    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        raise RuntimeError(
            f"Official metadata endpoint attempted a blocked redirect: {newurl!r}"
        )


def require_finite_number(record: dict[str, Any], field: str) -> float:
    value = record[field]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"Non-numeric value for {field}: {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise RuntimeError(f"Non-finite value for {field}: {value!r}")
    return number


def require_complete_record(record: dict[str, Any]) -> None:
    if set(record) != set(FIELDS):
        raise RuntimeError(
            "Official metadata field set changed: "
            f"expected {sorted(FIELDS)!r}, received {sorted(record)!r}"
        )
    missing = [field for field in FIELDS if record.get(field) is None]
    if missing:
        raise RuntimeError(f"Selected record is incomplete: {missing}")

    for field, expected in EXPECTED_TEXT.items():
        if record[field] != expected:
            raise RuntimeError(
                f"Frozen identity mismatch for {field}: "
                f"expected {expected!r}, received {record[field]!r}"
            )

    for field, expected in EXPECTED_FROZEN_NUMERIC.items():
        value = require_finite_number(record, field)
        if value != expected:
            raise RuntimeError(
                f"Frozen discovery mismatch for {field}: "
                f"expected {expected!r}, received {value!r}"
            )

    for field in ("ra", "dec", "sy_plx", "sy_pmra", "sy_pmdec", "st_radv"):
        require_finite_number(record, field)
    if not 0.0 <= float(record["ra"]) < 360.0:
        raise RuntimeError(f"RA is outside [0, 360): {record['ra']!r}")
    if not -90.0 <= float(record["dec"]) <= 90.0:
        raise RuntimeError(f"Declination is outside [-90, 90]: {record['dec']!r}")
    if float(record["sy_dist"]) <= 0.0 or float(record["sy_plx"]) <= 0.0:
        raise RuntimeError("Distance and parallax must both be positive")
    if float(record["pl_orbper"]) <= 0.0 or float(record["pl_orbsmax"]) <= 0.0:
        raise RuntimeError("Period and semimajor axis must both be positive")
    if not 0.0 <= float(record["pl_orbeccen"]) < 1.0:
        raise RuntimeError("Eccentricity must be in [0, 1)")
    for field in ("rastr", "decstr"):
        if not isinstance(record[field], str) or not record[field].strip():
            raise RuntimeError(f"Empty coordinate string for {field}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results_m37_selected_metadata/hd156668b.json"),
    )
    args = parser.parse_args()

    query = (
        f"select {','.join(FIELDS)} from pscomppars "
        f"where pl_name='{PLANET_NAME}'"
    )
    url = f"{NASA_TAP_API}?{urlencode({'query': query, 'format': 'json'})}"
    request = Request(url, headers={"User-Agent": "setisearch-m37-metadata/1.0"})
    opener = build_opener(RejectRedirects)
    with opener.open(request, timeout=120) as response:
        payload = response.read(5_000_001)
        status = int(getattr(response, "status", response.getcode()))
        content_type = response.headers.get_content_type()
        final_url = response.geturl()
    if final_url != url:
        raise RuntimeError(
            f"Official metadata response URL changed: {final_url!r} != {url!r}"
        )
    if len(payload) > 5_000_000:
        raise RuntimeError("Official metadata response exceeded 5 MB")

    try:
        records = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Official metadata response was not valid UTF-8 JSON") from error
    if status != 200 or not isinstance(records, list) or len(records) != 1:
        raise RuntimeError(
            f"Unexpected official metadata response: {status=} {records=!r}"
        )
    record = records[0]
    if not isinstance(record, dict):
        raise RuntimeError(f"Official metadata row is not an object: {record!r}")
    require_complete_record(record)

    result = {
        "purpose": "Milestone 37 selected-target official metadata completion",
        "spectral_payload_inspected": False,
        "spectral_dataset_values_read": False,
        "telescope_remote_request_made": False,
        "source": "NASA Exoplanet Archive pscomppars composite record",
        "query": query,
        "api_url": url,
        "response_url": final_url,
        "http_status": status,
        "http_content_type": content_type,
        "frozen_discovery_match": "exact numeric and text equality",
        "record": record,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(record, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
