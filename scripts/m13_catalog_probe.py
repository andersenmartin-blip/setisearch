#!/usr/bin/env python3
"""Metadata-only probe for a new Milestone 13 Breakthrough Listen cadence.

This script reads the public catalogue API, HTTP metadata, and SIGPROC headers only.
It never requests bytes from the spectral payload beyond the header prefix.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from seti_repeater.sigproc import remote_header


ARCHIVE_API = "https://seti.berkeley.edu/opendata/api/query-files"
CANDIDATE_TARGETS = {
    # Query both common and Hipparcos designations.  GJ 273 and GJ 1002 are
    # deliberately absent:
    # their published hit-summary pages were exposed while discovering the
    # archive naming convention, so neither remains eligible for held-out use.
    "gj_411": ["GJ411", "HIP54035"],
    "gj_687": ["GJ687", "HIP86162"],
    "tau_ceti": ["TAUCETI", "HIP8102"],
    "ross_128": ["ROSS128", "HIP57548"],
    "gj_581": ["GJ581", "HIP74995"],
    "gj_667c": ["GJ667C", "HIP84709"],
}


def fetch_json(url: str, params: dict | None = None) -> dict:
    request_url = url if not params else f"{url}?{urlencode(params)}"
    record: dict = {"url": request_url}
    try:
        request = Request(
            request_url,
            headers={"User-Agent": "setisearch-m13-metadata/1.0"},
        )
        with urlopen(request, timeout=60) as response:
            payload = response.read(25_000_000)
            record["status"] = int(getattr(response, "status", response.getcode()))
            record["final_url"] = response.geturl()
        decoded = json.loads(payload.decode("utf-8"))
        record["result"] = decoded.get("result")
        record["message"] = decoded.get("message")
        record["data"] = decoded.get("data", [])
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def compact_api_record(record: dict) -> dict:
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


def target_queries(alias: str, limit: int) -> list[dict]:
    return [
        {
            "target": alias,
            "telescopes": "GBT",
            "file-types": "filterbank",
            "grades": "fine",
            "limit": str(limit),
        },
        {
            "target": alias,
            "telescope": "GBT",
            "cadence": "true",
            "file_type": "FILTERBANK",
            "center_freq": "1475.09765625",
            "primaryTarget": "true",
            "grades": "fine",
            "limit": str(limit),
        },
    ]


def header_record(url: str) -> dict:
    record: dict = {"url": url, "name": url.rsplit("/", 1)[-1]}
    try:
        header, data_offset, size, ntime = remote_header(url)
        end_mhz = header["fch1"] + (header["nchans"] - 1) * header["foff"]
        low_mhz, high_mhz = sorted((float(header["fch1"]), float(end_mhz)))
        record.update({
            "source_name": header.get("source_name"),
            "tstart_mjd": float(header["tstart"]),
            "tsamp_s": float(header["tsamp"]),
            "nchans": int(header["nchans"]),
            "nbits": int(header["nbits"]),
            "nifs": int(header["nifs"]),
            "fch1_mhz": float(header["fch1"]),
            "foff_mhz": float(header["foff"]),
            "frequency_low_mhz": low_mhz,
            "frequency_high_mhz": high_mhz,
            "data_offset_bytes": int(data_offset),
            "remote_size_bytes": int(size),
            "ntime": int(ntime),
            "duration_s": float(ntime * header["tsamp"]),
            "covers_required_guarded_range": bool(
                low_mhz <= 1399.65 and high_mhz >= 1425.85
            ),
        })
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def inspect_cadence(cadence_url: str) -> dict:
    payload = fetch_json(cadence_url)
    rows = [compact_api_record(item) for item in payload.get("data", [])]
    urls = sorted({
        item["url"]
        for item in rows
        if isinstance(item.get("url"), str)
        and item["url"].lower().endswith(".fil")
    })
    headers = [header_record(url) for url in urls]
    return {
        "cadence_url": cadence_url,
        "api_status": payload.get("status"),
        "api_result": payload.get("result"),
        "api_error": payload.get("error"),
        "records": rows,
        "filterbank_urls": urls,
        "headers": headers,
        "qualifying_abacad_cadences": find_abacad(headers),
    }


def find_abacad(headers: list[dict]) -> list[dict]:
    usable = sorted(
        (item for item in headers if "error" not in item),
        key=lambda item: item["tstart_mjd"],
    )
    cadences = []
    for start in range(max(0, len(usable) - 5)):
        group = usable[start:start + 6]
        if len(group) != 6:
            continue
        sources = [item["source_name"] for item in group]
        on_source = sources[0]
        alternating = (
            sources[2] == on_source
            and sources[4] == on_source
            and all(sources[index] != on_source for index in (1, 3, 5))
        )
        geometry_matches = (
            max(item["tstart_mjd"] for item in group)
            - min(item["tstart_mjd"] for item in group)
        ) <= 0.04
        compatible = len({
            (item["nchans"], item["nbits"], item["nifs"], item["tsamp_s"], item["foff_mhz"])
            for item in group
        }) == 1
        coverage = all(item["covers_required_guarded_range"] for item in group)
        if alternating and geometry_matches and compatible and coverage:
            cadences.append({
                "on_source": on_source,
                "start_mjd": group[0]["tstart_mjd"],
                "elapsed_start_to_start_s": float(
                    (group[-1]["tstart_mjd"] - group[0]["tstart_mjd"]) * 86400
                ),
                "scan_urls": [item["url"] for item in group],
                "scan_sources": sources,
                "headers": group,
            })
    return cadences


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("results_m13/catalog_probe.json"))
    parser.add_argument("--max-records-per-query", type=int, default=200)
    parser.add_argument("--max-cadences-per-alias", type=int, default=10)
    args = parser.parse_args()

    targets = []
    for target_id, aliases in CANDIDATE_TARGETS.items():
        alias_records = []
        for alias in aliases:
            query_records = []
            cadence_urls = set()
            for params in target_queries(alias, args.max_records_per_query):
                payload = fetch_json(ARCHIVE_API, params)
                rows = [compact_api_record(item) for item in payload.get("data", [])]
                query_records.append({
                    "params": params,
                    "api_url": payload.get("url"),
                    "status": payload.get("status"),
                    "result": payload.get("result"),
                    "message": payload.get("message"),
                    "error": payload.get("error"),
                    "records": rows,
                })
                cadence_urls.update(
                    item["cadence_url"]
                    for item in rows
                    if isinstance(item.get("cadence_url"), str)
                    and item["cadence_url"]
                )
            inspected = [
                inspect_cadence(url)
                for url in sorted(cadence_urls)[:args.max_cadences_per_alias]
            ]
            alias_records.append({
                "alias": alias,
                "queries": query_records,
                "cadence_urls_found": len(cadence_urls),
                "cadences_inspected": inspected,
            })
        targets.append({"target_id": target_id, "aliases": alias_records})

    result = {
        "purpose": "Milestone 13 metadata/header-only target selection",
        "spectral_payload_inspected": False,
        "archive_api": ARCHIVE_API,
        "required_guarded_range_mhz": [1399.65, 1425.85],
        "targets": targets,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    summary = [
        {
            "target_id": item["target_id"],
            "aliases": [
                {
                    "alias": alias["alias"],
                    "query_records": [
                        len(query["records"])
                        for query in alias["queries"]
                    ],
                    "cadence_urls": alias["cadence_urls_found"],
                    "qualifying_cadences": sum(
                        len(cadence["qualifying_abacad_cadences"])
                        for cadence in alias["cadences_inspected"]
                    ),
                    "errors": [
                        query["error"]
                        for query in alias["queries"]
                        if query.get("error")
                    ],
                }
                for alias in item["aliases"]
            ],
        }
        for item in targets
    ]
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
