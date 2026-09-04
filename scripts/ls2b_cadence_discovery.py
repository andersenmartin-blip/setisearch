#!/usr/bin/env python3
"""Resolve dedicated Breakthrough Listen cadence metadata after LS2.

LS2B is conditioned only on LS2's published catalogue metadata.  It queries
the archive's cadence view and cadence-listing JSON but never opens a linked
HDF5 or filterbank payload.
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

from seti_repeater.light_sail_catalog import summarize_cadence_records
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


def select_preflight_cadence(targets: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Apply LS2B's priority, completeness and deterministic tie-break rules."""

    eligible: list[dict[str, Any]] = []
    for target in targets:
        for cadence in target["cadences"]:
            summary = cadence["summary"]
            medium_count = summary["product_counts"].get(
                "medium_resolution_hdf5", 0
            )
            if medium_count < 6 or not summary["has_at_least_six_scan_times"]:
                continue
            eligible.append(
                {
                    "source_priority": int(target["source_priority"]),
                    "target_id": target["target_id"],
                    "hostname": target["hostname"],
                    "archive_alias": target["archive_alias"],
                    "cadence_url": cadence["cadence_url"],
                    "mjd_min": summary["mjd_min"],
                    "mjd_max": summary["mjd_max"],
                    "center_frequencies_mhz": summary["center_frequencies_mhz"],
                    "medium_resolution_product_count": medium_count,
                    "high_time_resolution_product_count": summary[
                        "product_counts"
                    ].get("high_time_resolution_hdf5", 0),
                }
            )
    eligible.sort(
        key=lambda item: (
            item["source_priority"],
            float(item["mjd_min"]),
            item["cadence_url"],
        )
    )
    return eligible[0] if eligible else None


def build_discovery(config: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    if config.get("artifact_type") != "seti_repeater.ls2b_cadence_discovery_plan":
        raise RuntimeError("wrong LS2B configuration artifact")
    for boundary in (
        "spectral_payload_inspected",
        "spectral_dataset_values_read",
        "spectral_urls_opened",
    ):
        if source.get(boundary) is not False:
            raise RuntimeError(f"LS2 source violates metadata boundary: {boundary}")
    if source.get("result_sha256") != config["source"]["result_identity"]:
        raise RuntimeError("LS2 source result identity changed")

    source_by_id = {target["target_id"]: target for target in source["targets"]}
    discovered_targets: list[dict[str, Any]] = []
    for target_spec in config["targets"]:
        source_target = source_by_id[target_spec["target_id"]]
        if not source_target["geometry"]["geometry_ready"]:
            raise RuntimeError(f"{target_spec['target_id']} lost its LS2 geometry gate")
        alias = target_spec["archive_alias"]
        if alias not in source_target["resolved_archive_aliases"]:
            raise RuntimeError(f"{alias} was not resolved prospectively in LS2")
        query_params = {
            "target": alias,
            "telescope": config["query"]["telescope"],
            "cadence": "True",
            "primaryTarget": "True",
            "limit": str(config["limits"]["maximum_records_per_target"]),
        }
        response = fetch_json(
            config["endpoint"], query_params, config["network"]["user_agent"]
        )
        records = [compact_archive_record(item) for item in response["data"]]
        cadence_urls = sorted(
            {
                str(record["cadence_url"])
                for record in records
                if record.get("cadence_url")
            }
        )
        if len(cadence_urls) > config["limits"]["maximum_cadences_per_target"]:
            raise RuntimeError(f"{alias} exceeds the frozen cadence retention cap")
        cadences = []
        for cadence_url in cadence_urls:
            cadence_response = fetch_json(
                cadence_url, None, config["network"]["user_agent"]
            )
            cadence_records = [
                compact_archive_record(item) for item in cadence_response["data"]
            ]
            cadences.append(
                {
                    "cadence_url": cadence_url,
                    "final_url": cadence_response["final_url"],
                    "http_status": cadence_response["http_status"],
                    "api_result": cadence_response["result"],
                    "summary": summarize_cadence_records(cadence_records),
                    "records": cadence_records,
                    "spectral_urls_opened": False,
                }
            )
        discovered_targets.append(
            {
                "source_priority": source_target["priority"],
                "target_id": target_spec["target_id"],
                "hostname": source_target["hostname"],
                "archive_alias": alias,
                "query": query_params,
                "request_url": response["request_url"],
                "final_url": response["final_url"],
                "http_status": response["http_status"],
                "api_result": response["result"],
                "api_message": response["message"],
                "query_record_count": len(records),
                "cadence_count": len(cadences),
                "cadences": cadences,
            }
        )

    selected = select_preflight_cadence(discovered_targets)
    result: dict[str, Any] = {
        "artifact_type": "seti_repeater.ls2b_cadence_discovery_result",
        "schema_version": 1,
        "status": "complete-metadata-only-cadence-discovery",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "source_ls2_result_identity": source["result_sha256"],
        "selection_rule": config["selection_rule"],
        "targets": discovered_targets,
        "selected_for_separate_header_preflight": selected,
        "technical_no_selection": selected is None,
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
        "# LS2B cadence discovery result",
        "",
        "Status: **COMPLETE METADATA-ONLY CADENCE DISCOVERY; NO SPECTRAL DATA "
        "READ; NO SEARCH AUTHORIZED**.",
        "",
        "LS2B queried the dedicated Breakthrough Listen cadence view for the two "
        "systems whose LS2 records contained GBT medium-resolution products.",
        "",
        "| System | Alias | Cadence-query records | Cadences |",
        "|---|---|---:|---:|",
    ]
    for target in result["targets"]:
        lines.append(
            f"| {target['hostname']} | `{target['archive_alias']}` | "
            f"{target['query_record_count']} | {target['cadence_count']} |"
        )
    lines.extend(["", "## Decision", ""])
    selected = result["selected_for_separate_header_preflight"]
    if selected is None:
        lines.append(
            "No cadence listing contains six distinct scan times and six "
            "medium-resolution products. The branch stops without spectral access."
        )
    else:
        lines.append(
            f"**{selected['hostname']}** cadence `{selected['cadence_url'].rsplit('/', 1)[-1]}` "
            "is the first priority-qualified opportunity. It may proceed only to "
            "a separately frozen HDF5-header preflight."
        )
        lines.append("")
        lines.append(
            f"The listing spans MJD {selected['mjd_min']}--{selected['mjd_max']}, "
            f"with {selected['medium_resolution_product_count']} medium-resolution "
            f"and {selected['high_time_resolution_product_count']} high-time-resolution products."
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "Only archive query and cadence-listing JSON were read. Linked radio "
            "files remain unopened; this is neither a search nor a technosignature result.",
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
        "--output", type=Path, default=Path("results_ls2b_cadence/cadences.json")
    )
    parser.add_argument(
        "--markdown", type=Path, default=Path("LS2B_CADENCE_RESULT.md")
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    source_path = Path(config["source"]["path"])
    if sha256_file(source_path) != config["source"]["sha256"]:
        raise RuntimeError("LS2 source file hash changed")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    result = build_discovery(config, source)
    atomic_write(args.output, canonical_json_bytes(result))
    atomic_write(args.markdown, markdown_result(result).encode("utf-8"))
    print(canonical_json_bytes({
        "status": result["status"],
        "selected": result["selected_for_separate_header_preflight"],
        "result_sha256": result["result_sha256"],
    }).decode("utf-8"))


if __name__ == "__main__":
    main()
