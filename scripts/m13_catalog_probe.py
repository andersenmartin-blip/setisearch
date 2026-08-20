#!/usr/bin/env python3
"""Metadata-only probe for a new Milestone 13 Breakthrough Listen cadence.

This script reads the public catalogue API, HTTP metadata, and SIGPROC headers only.
It never requests bytes from the spectral payload beyond the header prefix.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from seti_repeater.sigproc import remote_header


ARCHIVE_API = "https://seti.berkeley.edu/opendata/api/query-files"
TARGETS_API = "https://seti.berkeley.edu/opendata/api/list-targets"
NASA_TAP_API = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
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
GJ411_FINE_HDF5_URLS = [
    "https://bldata.berkeley.edu/pipeline/AGBT16A_999_213/holding/spliced_blc0001020304050607_guppi_57542_84369_GJ411_0003.gpuspec.0000.h5",
    "https://bldata.berkeley.edu/pipeline/AGBT16A_999_213/holding/spliced_blc0001020304050607_guppi_57542_84744_HIP52936_0004.gpuspec.0000.h5",
    "https://bldata.berkeley.edu/pipeline/AGBT16A_999_213/holding/spliced_blc0001020304050607_guppi_57542_85092_GJ411_0005.gpuspec.0000.h5",
    "https://bldata.berkeley.edu/pipeline/AGBT16A_999_213/holding/spliced_blc0001020304050607_guppi_57542_85446_HIP52941_0006.gpuspec.0000.h5",
    "https://bldata.berkeley.edu/pipeline/AGBT16A_999_213/holding/spliced_blc0001020304050607_guppi_57542_85812_GJ411_0007.gpuspec.0000.h5",
    "https://bldata.berkeley.edu/pipeline/AGBT16A_999_213/holding/spliced_blc0001020304050607_guppi_57542_86169_HIP53002_0008.gpuspec.0000.h5",
]


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
        if isinstance(decoded, list):
            record["result"] = "success"
            record["data"] = decoded
        else:
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


def normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def resolve_catalog_names(requested: list[str], catalog: list[str]) -> list[str]:
    requested_keys = {normalized_name(value) for value in requested}
    matches = sorted({
        value
        for value in catalog
        if normalized_name(value) in requested_keys
    })
    return matches or requested


def target_queries(alias: str, limit: int) -> list[dict]:
    return [
        {
            "target": alias,
            "limit": str(limit),
        },
        {
            "target": alias,
            "telescope": "GBT",
            "cadence": "True",
            "primaryTarget": "True",
            "limit": str(limit),
        },
    ]


def global_filterbank_queries(limit: int) -> list[dict]:
    common = {
        "target": "",
        "telescope": "GBT",
        "cadence": "True",
        "primaryTarget": "True",
        "center_freq": "1475.09765625",
        "grades": "fine",
        "limit": str(limit),
    }
    return [
        {**common, "file_type": value}
        for value in ("FILTERBANK", "filterbank", "FIL")
    ]


def nasa_metadata_queries(hostname: str) -> list[dict]:
    escaped_hostname = hostname.replace("'", "''")
    return [
        {
            "label": "composite_planet_parameters",
            "query": (
                "select top 1 * from pscomppars "
                f"where hostname='{escaped_hostname}'"
            ),
        },
        {
            "label": "published_planet_solutions",
            "query": (
                f"select * from ps where hostname='{escaped_hostname}' "
                "and default_flag=1"
            ),
        },
    ]


def json_value(value):
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, list):
        return [json_value(item) for item in value]
    if isinstance(value, tuple):
        return [json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def hdf5_header_record(url: str) -> dict:
    record: dict = {"url": url, "spectral_dataset_values_read": False}
    try:
        import fsspec
        import h5py

        request = Request(
            url,
            method="HEAD",
            headers={"User-Agent": "setisearch-m13-metadata/1.0"},
        )
        with urlopen(request, timeout=60) as response:
            record["http_status"] = int(
                getattr(response, "status", response.getcode())
            )
            record["remote_size_bytes"] = int(response.headers["Content-Length"])
            record["accept_ranges"] = response.headers.get("Accept-Ranges")
            record["etag"] = response.headers.get("ETag")

        with fsspec.open(
            url,
            mode="rb",
            block_size=1_048_576,
            cache_type="blockcache",
        ) as remote:
            with h5py.File(remote, "r") as handle:
                dataset = handle["data"]
                root_attrs = {
                    key: json_value(value)
                    for key, value in handle.attrs.items()
                }
                data_attrs = {
                    key: json_value(value)
                    for key, value in dataset.attrs.items()
                }
                record.update({
                    "root_attributes": root_attrs,
                    "data_attributes": data_attrs,
                    "dataset_shape": [int(value) for value in dataset.shape],
                    "dataset_dtype": str(dataset.dtype),
                    "dataset_chunks": (
                        [int(value) for value in dataset.chunks]
                        if dataset.chunks else None
                    ),
                    "dataset_compression": dataset.compression,
                })
                attrs = {**root_attrs, **data_attrs}
                fch1 = float(attrs["fch1"])
                foff = float(attrs["foff"])
                nchans = int(dataset.shape[-1])
                end_mhz = fch1 + (nchans - 1) * foff
                low_mhz, high_mhz = sorted((fch1, end_mhz))
                record.update({
                    "source_name": attrs.get("source_name"),
                    "tstart_mjd": float(attrs["tstart"]),
                    "tsamp_s": float(attrs["tsamp"]),
                    "nchans": nchans,
                    "fch1_mhz": fch1,
                    "foff_mhz": foff,
                    "frequency_low_mhz": low_mhz,
                    "frequency_high_mhz": high_mhz,
                    "ntime": int(dataset.shape[0]),
                    "duration_s": float(dataset.shape[0] * float(attrs["tsamp"])),
                    "covers_required_guarded_range": bool(
                        low_mhz <= 1399.65 and high_mhz >= 1425.85
                    ),
                })
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


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


def is_fine_hdf5_url(url: str) -> bool:
    lowered = url.lower()
    return lowered.endswith(".h5") and (
        lowered.endswith(".gpuspec.0000.h5")
        or lowered.endswith("_fine.h5")
    )


def find_hdf5_abacad(headers: list[dict]) -> list[dict]:
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
            (
                tuple(item["dataset_shape"]),
                item["dataset_dtype"],
                item["tsamp_s"],
                item["foff_mhz"],
            )
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


def inspect_cadence(cadence_url: str, probe_hdf5_headers: bool = False) -> dict:
    payload = fetch_json(cadence_url)
    rows = [compact_api_record(item) for item in payload.get("data", [])]
    urls = sorted({
        item["url"]
        for item in rows
        if isinstance(item.get("url"), str)
        and item["url"].lower().endswith(".fil")
    })
    headers = [header_record(url) for url in urls]
    hdf5_urls = sorted({
        item["url"]
        for item in rows
        if isinstance(item.get("url"), str)
        and is_fine_hdf5_url(item["url"])
    })
    hdf5_headers = [
        hdf5_header_record(url)
        for url in (hdf5_urls if probe_hdf5_headers else [])
    ]
    return {
        "cadence_url": cadence_url,
        "api_status": payload.get("status"),
        "api_result": payload.get("result"),
        "api_error": payload.get("error"),
        "records": rows,
        "filterbank_urls": urls,
        "headers": headers,
        "qualifying_abacad_cadences": find_abacad(headers),
        "fine_hdf5_urls": hdf5_urls,
        "hdf5_headers": hdf5_headers,
        "qualifying_hdf5_abacad_cadences": find_hdf5_abacad(hdf5_headers),
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
    parser.add_argument("--max-cadences-per-alias", type=int, default=0)
    parser.add_argument("--global-query-limit", type=int, default=0)
    parser.add_argument("--probe-hdf5-headers", action="store_true")
    parser.add_argument("--probe-cadence-hdf5-headers", action="store_true")
    parser.add_argument("--target-id", choices=sorted(CANDIDATE_TARGETS))
    parser.add_argument("--nasa-host", default="GJ 411")
    args = parser.parse_args()

    catalog_payload = fetch_json(TARGETS_API)
    catalog = [
        item
        for item in catalog_payload.get("data", [])
        if isinstance(item, str)
    ]
    global_queries = []
    for params in (
        global_filterbank_queries(args.global_query_limit)
        if args.global_query_limit > 0 else []
    ):
        payload = fetch_json(ARCHIVE_API, params)
        global_queries.append({
            "params": params,
            "api_url": payload.get("url"),
            "status": payload.get("status"),
            "result": payload.get("result"),
            "message": payload.get("message"),
            "error": payload.get("error"),
            "records": [
                compact_api_record(item)
                for item in payload.get("data", [])
            ],
        })
    nasa_queries = []
    for query in nasa_metadata_queries(args.nasa_host):
        payload = fetch_json(
            NASA_TAP_API,
            {"query": query["query"], "format": "json"},
        )
        nasa_queries.append({
            "label": query["label"],
            "query": query["query"],
            "api_url": payload.get("url"),
            "status": payload.get("status"),
            "result": payload.get("result"),
            "error": payload.get("error"),
            "records": payload.get("data", []),
        })
    targets = []
    target_items = CANDIDATE_TARGETS.items()
    if args.target_id:
        target_items = [(args.target_id, CANDIDATE_TARGETS[args.target_id])]
    for target_id, requested_aliases in target_items:
        aliases = resolve_catalog_names(requested_aliases, catalog)
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
                inspect_cadence(url, args.probe_cadence_hdf5_headers)
                for url in sorted(cadence_urls)[:args.max_cadences_per_alias]
            ]
            alias_records.append({
                "alias": alias,
                "queries": query_records,
                "cadence_urls_found": len(cadence_urls),
                "cadences_inspected": inspected,
            })
        targets.append({
            "target_id": target_id,
            "requested_aliases": requested_aliases,
            "catalog_matches": aliases,
            "aliases": alias_records,
        })

    result = {
        "purpose": "Milestone 13 metadata/header-only target selection",
        "spectral_payload_inspected": False,
        "archive_api": ARCHIVE_API,
        "targets_api": TARGETS_API,
        "target_catalog_status": catalog_payload.get("status"),
        "target_catalog_result": catalog_payload.get("result"),
        "target_catalog_error": catalog_payload.get("error"),
        "target_catalog_count": len(catalog),
        "global_filterbank_queries": global_queries,
        "nasa_exoplanet_archive_queries": nasa_queries,
        "gj411_fine_hdf5_header_probe": [
            hdf5_header_record(url)
            for url in (
                GJ411_FINE_HDF5_URLS
                if args.probe_hdf5_headers else []
            )
        ],
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
                    "qualifying_hdf5_cadences": sum(
                        len(cadence["qualifying_hdf5_abacad_cadences"])
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
