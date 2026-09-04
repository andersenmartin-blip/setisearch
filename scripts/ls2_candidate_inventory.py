#!/usr/bin/env python3
"""Build the LS2 planet-geometry and public-radio metadata inventory.

This script calls catalogue APIs and cadence-listing APIs only.  It never opens
any HDF5/FIL URL and therefore never reads a radio spectral dataset value.
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
    rank_target_inventory,
    resolve_archive_aliases,
    summarize_cadence_records,
)
from seti_repeater.search_v0p6 import canonical_json_bytes


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def fetch_json(url: str, params: Mapping[str, str] | None, user_agent: str) -> dict[str, Any]:
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


def deduplicate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[Any, Any], dict[str, Any]] = {}
    for record in records:
        key = (record.get("id"), record.get("url"))
        unique[key] = record
    return sorted(
        unique.values(),
        key=lambda item: (
            str(item.get("utc") or ""),
            str(item.get("target") or ""),
            str(item.get("url") or ""),
        ),
    )


def nasa_query(hostname: str, fields: list[str]) -> str:
    escaped = hostname.replace("'", "''")
    return (
        f"select {','.join(fields)} from ps "
        f"where hostname='{escaped}' and default_flag=1 order by pl_name"
    )


def build_inventory(config: dict[str, Any]) -> dict[str, Any]:
    if config.get("artifact_type") != "seti_repeater.ls2_candidate_inventory_plan":
        raise RuntimeError("wrong LS2 configuration artifact")
    endpoints = config["endpoints"]
    limits = config["limits"]
    user_agent = config["network"]["user_agent"]

    target_catalog_response = fetch_json(
        endpoints["breakthrough_listen_target_catalog"], None, user_agent
    )
    catalog_targets = [
        str(value) for value in target_catalog_response["data"] if isinstance(value, str)
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

        query_receipts: list[dict[str, Any]] = []
        archive_records: list[dict[str, Any]] = []
        for alias in resolved_aliases:
            response = fetch_json(
                endpoints["breakthrough_listen_query_files"],
                {"target": alias, "limit": str(limits["maximum_records_per_alias"])},
                user_agent,
            )
            compact = [compact_archive_record(item) for item in response["data"]]
            archive_records.extend(compact)
            query_receipts.append(
                {
                    "alias": alias,
                    "request_url": response["request_url"],
                    "final_url": response["final_url"],
                    "http_status": response["http_status"],
                    "api_result": response["result"],
                    "api_message": response["message"],
                    "record_count": len(compact),
                }
            )

        archive_records = deduplicate_records(archive_records)
        cadence_urls = sorted(
            {
                str(record["cadence_url"])
                for record in archive_records
                if record.get("cadence_url")
            }
        )
        if len(cadence_urls) > limits["maximum_cadences_per_target"]:
            raise RuntimeError(
                f"{target_spec['target_id']} exceeds frozen cadence retention limit"
            )
        cadences: list[dict[str, Any]] = []
        for cadence_url in cadence_urls:
            cadence_response = fetch_json(cadence_url, None, user_agent)
            cadence_rows = [
                compact_archive_record(item) for item in cadence_response["data"]
            ]
            cadences.append(
                {
                    "cadence_url": cadence_url,
                    "final_url": cadence_response["final_url"],
                    "http_status": cadence_response["http_status"],
                    "api_result": cadence_response["result"],
                    "summary": summarize_cadence_records(cadence_rows),
                    "records": cadence_rows,
                    "spectral_urls_opened": False,
                }
            )

        targets.append(
            {
                "priority": target_spec["priority"],
                "target_id": target_spec["target_id"],
                "hostname": target_spec["hostname"],
                "requested_archive_aliases": target_spec["archive_aliases"],
                "resolved_archive_aliases": resolved_aliases,
                "nasa_query": query,
                "nasa_request_url": nasa_response["request_url"],
                "nasa_http_status": nasa_response["http_status"],
                "geometry": geometry,
                "archive_query_receipts": query_receipts,
                "archive_record_count": len(archive_records),
                "archive_records": archive_records,
                "cadences": cadences,
            }
        )

    ranking = rank_target_inventory(targets)
    selected = next(
        (item for item in ranking if item["eligible_for_header_preflight"]), None
    )
    result: dict[str, Any] = {
        "artifact_type": "seti_repeater.ls2_candidate_inventory_result",
        "schema_version": 1,
        "status": "complete-metadata-only-inventory",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "config_sha256": hashlib.sha256(canonical_json_bytes(config)).hexdigest(),
        "target_catalog": {
            "request_url": target_catalog_response["request_url"],
            "final_url": target_catalog_response["final_url"],
            "http_status": target_catalog_response["http_status"],
            "api_result": target_catalog_response["result"],
            "target_count": len(catalog_targets),
        },
        "selection_rule": config["selection_rule"],
        "target_ranking": ranking,
        "selected_for_separate_header_preflight": selected,
        "technical_no_selection": selected is None,
        "targets": targets,
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
        "# LS2 candidate-system inventory result",
        "",
        "Status: **COMPLETE METADATA-ONLY INVENTORY; NO SPECTRAL DATA READ; "
        "NO SEARCH AUTHORIZED**.",
        "",
        "LS2 checked the frozen priority list against the NASA Exoplanet Archive "
        "and the Breakthrough Listen public catalogue. The table is a preflight "
        "decision record, not a technosignature result.",
        "",
        "| Priority | System | Geometry-ready planets | Archive aliases | Candidate cadences | Header preflight |",
        "|---:|---|---:|---:|---:|---|",
    ]
    target_by_id = {item["target_id"]: item for item in result["targets"]}
    for item in result["target_ranking"]:
        geometry = target_by_id[item["target_id"]]["geometry"]
        lines.append(
            f"| {item['priority']} | {item['hostname']} | "
            f"{geometry['eligible_planet_count']} | "
            f"{len(item['resolved_archive_aliases'])} | "
            f"{item['candidate_cadence_count']} | "
            f"{'eligible' if item['eligible_for_header_preflight'] else 'not yet eligible'} |"
        )
    selected = result["selected_for_separate_header_preflight"]
    lines.extend(["", "## Decision", ""])
    if selected is None:
        lines.append(
            "No system satisfies both the frozen transit-geometry and public "
            "medium-resolution cadence gates. LS2 therefore stops without a "
            "target selection."
        )
    else:
        lines.append(
            f"The first priority-qualified system is **{selected['hostname']}**. "
            "Its listed cadence metadata may proceed to a separately frozen "
            "HDF5-header-only preflight; this result does not authorize opening "
            "spectral dataset values."
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "Only catalogue JSON and cadence listing JSON were read. No linked "
            "HDF5 or filterbank URL was opened, no signal statistic was evaluated, "
            "and no technosignature, sensitivity, or occurrence-rate claim is made.",
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
        "--output", type=Path, default=Path("results_ls2_inventory/inventory.json")
    )
    parser.add_argument(
        "--markdown", type=Path, default=Path("LS2_INVENTORY_RESULT.md")
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    result = build_inventory(config)
    atomic_write(args.output, canonical_json_bytes(result))
    atomic_write(args.markdown, markdown_result(result).encode("utf-8"))
    print(canonical_json_bytes({
        "status": result["status"],
        "selected": result["selected_for_separate_header_preflight"],
        "result_sha256": result["result_sha256"],
    }).decode("utf-8"))


if __name__ == "__main__":
    main()
