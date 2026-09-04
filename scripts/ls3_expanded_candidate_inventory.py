#!/usr/bin/env python3
"""Build the LS3 expanded light-sail target and cadence inventory.

Only public JSON catalogue and cadence-listing metadata are requested. Linked
radio products are recorded by URL but are never opened in this phase.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from seti_repeater.light_sail_catalog import (
    geometry_planet_inventory,
    resolve_archive_aliases,
    summarize_cadence_records,
)
from seti_repeater.search_v0p6 import canonical_json_bytes


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def fetch_json(
    url: str, params: Mapping[str, str] | None, user_agent: str
) -> dict[str, Any]:
    request_url = url if not params else f"{url}?{urlencode(params)}"
    request = Request(request_url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=90) as response:
        payload = response.read(50_000_000)
        status = int(getattr(response, "status", response.getcode()))
        final_url = response.geturl()
    decoded = json.loads(payload.decode("utf-8"))
    if isinstance(decoded, list):
        data = decoded
        result = "success"
        message = None
    elif isinstance(decoded, dict):
        data = decoded.get("data", [])
        result = decoded.get("result")
        message = decoded.get("message")
    else:
        raise RuntimeError(f"unexpected JSON payload from {request_url}")
    if not isinstance(data, list):
        raise RuntimeError(f"non-list data payload from {request_url}")
    return {
        "request_url": request_url,
        "final_url": final_url,
        "http_status": status,
        "result": result,
        "message": message,
        "data": data,
    }


def compact_archive_record(record: Mapping[str, Any]) -> dict[str, Any]:
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


def nasa_query(hostname: str, fields: list[str]) -> str:
    escaped = hostname.replace("'", "''")
    return (
        f"select {','.join(fields)} from ps "
        f"where hostname='{escaped}' and default_flag=1 order by pl_name"
    )


def cadence_is_data_ready(cadence: Mapping[str, Any]) -> bool:
    summary = cadence["summary"]
    medium_count = summary["product_counts"].get("medium_resolution_hdf5", 0)
    return bool(summary["has_at_least_six_scan_times"] and medium_count >= 6)


def advancing_candidates(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return every geometry- and cadence-ready system in frozen order."""

    advancing: list[dict[str, Any]] = []
    for target in sorted(targets, key=lambda item: (item["priority"], item["target_id"])):
        if not target["geometry"]["geometry_ready"]:
            continue
        ready_cadences = [
            cadence for cadence in target["cadences"] if cadence_is_data_ready(cadence)
        ]
        if not ready_cadences:
            continue
        advancing.append(
            {
                "priority": target["priority"],
                "cohort": target["cohort"],
                "target_id": target["target_id"],
                "hostname": target["hostname"],
                "distance_pc": target["distance_pc"],
                "geometry_ready_planet_count": target["geometry"][
                    "eligible_planet_count"
                ],
                "resolved_archive_aliases": target["resolved_archive_aliases"],
                "cadence_count": len(ready_cadences),
                "cadence_urls": [item["cadence_url"] for item in ready_cadences],
                "medium_resolution_product_counts": [
                    item["summary"]["product_counts"].get(
                        "medium_resolution_hdf5", 0
                    )
                    for item in ready_cadences
                ],
                "high_time_resolution_product_counts": [
                    item["summary"]["product_counts"].get(
                        "high_time_resolution_hdf5", 0
                    )
                    for item in ready_cadences
                ],
            }
        )
    return advancing


def build_inventory(config: dict[str, Any]) -> dict[str, Any]:
    expected_type = "seti_repeater.ls3_expanded_candidate_inventory_plan"
    if config.get("artifact_type") != expected_type:
        raise RuntimeError("wrong LS3 configuration artifact")

    endpoints = config["endpoints"]
    limits = config["limits"]
    user_agent = config["network"]["user_agent"]
    target_catalog_response = fetch_json(
        endpoints["breakthrough_listen_target_catalog"], None, user_agent
    )
    catalog_targets = [
        str(value)
        for value in target_catalog_response["data"]
        if isinstance(value, str)
    ]

    targets: list[dict[str, Any]] = []
    for target_spec in config["targets"]:
        query = nasa_query(target_spec["hostname"], config["nasa_fields"])
        nasa_response = fetch_json(
            endpoints["nasa_exoplanet_archive_tap"],
            {"query": query, "format": "json"},
            user_agent,
        )
        geometry = geometry_planet_inventory(nasa_response["data"])
        resolved_aliases = resolve_archive_aliases(
            target_spec["archive_aliases"], catalog_targets
        )

        alias_queries: list[dict[str, Any]] = []
        cadence_sources: dict[str, set[str]] = {}
        for alias in resolved_aliases:
            params = {
                "target": alias,
                "telescope": config["query"]["telescope"],
                "cadence": "True",
                "primaryTarget": "True",
                "limit": str(limits["maximum_records_per_alias"]),
            }
            response = fetch_json(
                endpoints["breakthrough_listen_query_files"], params, user_agent
            )
            records = [compact_archive_record(item) for item in response["data"]]
            urls = sorted(
                {
                    str(item["cadence_url"])
                    for item in records
                    if item.get("cadence_url")
                }
            )
            for cadence_url in urls:
                cadence_sources.setdefault(cadence_url, set()).add(alias)
            alias_queries.append(
                {
                    "alias": alias,
                    "request_url": response["request_url"],
                    "final_url": response["final_url"],
                    "http_status": response["http_status"],
                    "api_result": response["result"],
                    "api_message": response["message"],
                    "record_count": len(records),
                    "cadence_urls": urls,
                }
            )

        cadence_urls = sorted(cadence_sources)
        if len(cadence_urls) > limits["maximum_cadences_per_target"]:
            raise RuntimeError(
                f"{target_spec['target_id']} exceeds the cadence retention cap"
            )
        cadences: list[dict[str, Any]] = []
        for cadence_url in cadence_urls:
            cadence_response = fetch_json(cadence_url, None, user_agent)
            cadence_records = [
                compact_archive_record(item) for item in cadence_response["data"]
            ]
            cadences.append(
                {
                    "cadence_url": cadence_url,
                    "resolved_via_aliases": sorted(cadence_sources[cadence_url]),
                    "final_url": cadence_response["final_url"],
                    "http_status": cadence_response["http_status"],
                    "api_result": cadence_response["result"],
                    "summary": summarize_cadence_records(cadence_records),
                    "records": cadence_records,
                    "spectral_urls_opened": False,
                }
            )

        planet_records = geometry["eligible_planets"] + [
            {key: value for key, value in item.items() if key != "reasons"}
            for item in geometry["rejected_planets"]
        ]
        distances = [
            float(item["sy_dist"])
            for item in planet_records
            if item.get("sy_dist") not in (None, "")
        ]
        targets.append(
            {
                "priority": target_spec["priority"],
                "cohort": target_spec["cohort"],
                "target_id": target_spec["target_id"],
                "hostname": target_spec["hostname"],
                "science_reference": target_spec["science_reference"],
                "distance_pc": min(distances) if distances else None,
                "requested_archive_aliases": target_spec["archive_aliases"],
                "resolved_archive_aliases": resolved_aliases,
                "nasa_query": query,
                "nasa_request_url": nasa_response["request_url"],
                "nasa_http_status": nasa_response["http_status"],
                "geometry": geometry,
                "archive_query_receipts": alias_queries,
                "cadence_count": len(cadences),
                "data_ready_cadence_count": sum(
                    cadence_is_data_ready(item) for item in cadences
                ),
                "cadences": cadences,
            }
        )

    advancing = advancing_candidates(targets)
    result: dict[str, Any] = {
        "artifact_type": "seti_repeater.ls3_expanded_candidate_inventory_result",
        "schema_version": 1,
        "status": "complete-metadata-only-expanded-inventory",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "config_sha256": hashlib.sha256(canonical_json_bytes(config)).hexdigest(),
        "target_catalog": {
            "request_url": target_catalog_response["request_url"],
            "final_url": target_catalog_response["final_url"],
            "http_status": target_catalog_response["http_status"],
            "api_result": target_catalog_response["result"],
            "target_count": len(catalog_targets),
        },
        "advancement_rule": config["advancement_rule"],
        "targets": targets,
        "advancing_candidates_for_separate_header_preflight": advancing,
        "advancing_candidate_count": len(advancing),
        "technical_no_advancing_candidate": not advancing,
        "spectral_payload_inspected": False,
        "spectral_dataset_values_read": False,
        "spectral_urls_opened": False,
        "raw_spectral_payload_published": False,
        "technosignature_claimed": False,
        "search_authorized": False,
    }
    result["result_sha256"] = hashlib.sha256(canonical_json_bytes(result)).hexdigest()
    return result


def markdown_result(result: Mapping[str, Any]) -> str:
    lines = [
        "# LS3 expanded candidate inventory result",
        "",
        "Status: **COMPLETE METADATA-ONLY INVENTORY; NO RADIO FILE OPENED; NO SEARCH AUTHORIZED**.",
        "",
        "| Priority | Cohort | System | Distance (pc) | Geometry-ready planets | Archive aliases | Cadences | Data-ready cadences |",
        "|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for target in sorted(
        result["targets"], key=lambda item: (item["priority"], item["target_id"])
    ):
        distance = (
            "n/a"
            if target["distance_pc"] is None
            else f"{target['distance_pc']:.2f}"
        )
        lines.append(
            f"| {target['priority']} | {target['cohort']} | {target['hostname']} | "
            f"{distance} | {target['geometry']['eligible_planet_count']} | "
            f"{len(target['resolved_archive_aliases'])} | {target['cadence_count']} | "
            f"{target['data_ready_cadence_count']} |"
        )

    lines.extend(["", "## Decision", ""])
    advancing = result["advancing_candidates_for_separate_header_preflight"]
    if not advancing:
        lines.append(
            "No system currently satisfies both frozen gates. LS3 stops without "
            "opening a radio file."
        )
    else:
        names = ", ".join(f"**{item['hostname']}**" for item in advancing)
        lines.append(
            f"{names} satisfy both frozen metadata gates. All advance together "
            "to a separately frozen header-only cadence and conjunction comparison."
        )
        lines.append("")
        lines.append(
            "No single system is selected here; convenient data availability cannot "
            "override the later geometry and sampling comparison."
        )

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "Only catalogue, query and cadence-listing JSON were read. Linked HDF5 "
            "and filterbank files remained unopened. This is neither a signal search "
            "nor a technosignature result.",
            "",
            f"Result identity: `{result['result_sha256']}`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results_ls3_inventory/inventory.json"),
    )
    parser.add_argument(
        "--markdown", type=Path, default=Path("LS3_EXPANDED_CANDIDATE_RESULT.md")
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    result = build_inventory(config)
    atomic_write(args.output, canonical_json_bytes(result))
    atomic_write(args.markdown, markdown_result(result).encode("utf-8"))
    print(
        canonical_json_bytes(
            {
                "status": result["status"],
                "advancing": result[
                    "advancing_candidates_for_separate_header_preflight"
                ],
                "result_sha256": result["result_sha256"],
            }
        ).decode("utf-8")
    )


if __name__ == "__main__":
    main()
