#!/usr/bin/env python3
"""Reproduce LS1's metadata-only HD 219134 cadence ranking."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from seti_repeater.light_sail import CircularTransitPlanet, rank_cadences
from seti_repeater.search_v0p6 import canonical_json_bytes


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_bytes(canonical_json_bytes(value))
    os.replace(temporary, path)


def build_ranking(config: dict[str, Any], source_path: Path) -> dict[str, Any]:
    if config["artifact_type"] != "seti_repeater.ls1_preregistration":
        raise RuntimeError("wrong LS1 config artifact")
    observed_source_hash = sha256_file(source_path)
    expected_source_hash = config["archive_inventory"]["source_sha256"]
    if observed_source_hash != expected_source_hash:
        raise RuntimeError("M16 metadata inventory identity changed")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if source.get("spectral_dataset_values_read") is not False:
        raise RuntimeError("ranking source is not metadata-only")
    target = next(
        item
        for item in source["screened_targets"]
        if item["archive_target"] == config["target"]["archive_target"]
    )
    expected_ids = list(config["archive_inventory"]["eligible_cadence_ids"])
    cadence_inputs: list[dict[str, Any]] = []
    for cadence in target["cadences"]:
        cadence_id = cadence["cadence_url"].rsplit("/", 1)[-1]
        first_header = cadence["hdf5_headers"][0]
        cadence_inputs.append(
            {
                "cadence_id": cadence_id,
                "first_on_tstart_mjd": first_header["tstart_mjd"],
                "first_on_duration_s": first_header["ntime"] * first_header["tsamp_s"],
            }
        )
    if sorted(item["cadence_id"] for item in cadence_inputs) != sorted(expected_ids):
        raise RuntimeError("eligible cadence inventory changed")
    first, second = [
        CircularTransitPlanet.from_mapping(item) for item in config["geometry"]["planets"]
    ]
    ranking = rank_cadences(
        cadence_inputs,
        first,
        second,
        float(config["geometry"]["stellar_radius_solar"]),
    )
    selected = ranking[0]["cadence_id"]
    if selected != config["archive_inventory"]["selected_cadence_id"]:
        raise RuntimeError("frozen selected cadence is not rank 1")
    result: dict[str, Any] = {
        "artifact_type": "seti_repeater.ls1_conjunction_ranking",
        "schema_version": 1,
        "status": "complete-metadata-only-ranking",
        "config_sha256": hashlib.sha256(canonical_json_bytes(config)).hexdigest(),
        "source_path": str(source_path),
        "source_sha256": observed_source_hash,
        "model": config["geometry"]["model"],
        "planet_pair": [first.name, second.name],
        "stellar_radius_solar": config["geometry"]["stellar_radius_solar"],
        "ranking": ranking,
        "selected_cadence_id": selected,
        "spectral_dataset_values_read": False,
        "remote_files_opened": False,
        "technosignature_claimed": False,
    }
    result["result_sha256"] = hashlib.sha256(canonical_json_bytes(result)).hexdigest()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("results_m16_header_screen_corrected/header_screen.json"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("results_ls1/conjunction_ranking.json")
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    result = build_ranking(config, args.source)
    atomic_json(args.output, result)
    print(canonical_json_bytes(result).decode("utf-8"))


if __name__ == "__main__":
    main()
