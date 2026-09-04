#!/usr/bin/env python3
"""Header-only qualification and adjacent-pair ranking for HD 63433."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from ls2c_header_preflight import (
    atomic_write,
    build_cadence_inputs,
    canonical_json_bytes,
    ephemeris_uncertainty_metrics,
    hdf5_header_record,
    qualify_cadence as qualify_single_pair,
    sha256_file,
)


def adjacent_planet_pairs(
    planets: list[Mapping[str, Any]],
) -> list[tuple[Mapping[str, Any], Mapping[str, Any]]]:
    ordered = sorted(planets, key=lambda item: (float(item["pl_orbsmax"]), item["pl_name"]))
    if len(ordered) < 2:
        raise RuntimeError("at least two planets are required")
    return list(zip(ordered, ordered[1:]))


def qualify_cadence(
    cadence_input: Mapping[str, Any],
    headers: Mapping[str, Mapping[str, Any]],
    target_name: str,
    criteria: Mapping[str, Any],
    planets: list[Mapping[str, Any]],
    stellar_radius_solar: float,
) -> dict[str, Any]:
    pairs = adjacent_planet_pairs(planets)
    first_geometry = {
        "stellar_radius_solar": stellar_radius_solar,
        "eligible_planets": [pairs[0][0], pairs[0][1]],
    }
    result = qualify_single_pair(
        cadence_input, headers, target_name, criteria, first_geometry
    )
    result.pop("conjunction", None)
    pair_results: list[dict[str, Any]] = []
    if result["medium_qualified"]:
        first_scan = cadence_input["scans"][0]
        first_header = headers[first_scan["medium_url"]]
        reference_bjd = (
            float(first_header["tstart_mjd"])
            + 2_400_000.5
            + (float(first_header["ntime"]) * float(first_header["tsamp_s"]))
            / (2.0 * 86_400.0)
        )
        for inner, outer in pairs:
            pair_results.append(
                {
                    "planet_pair": [inner["pl_name"], outer["pl_name"]],
                    "inner_semimajor_axis_au": inner["pl_orbsmax"],
                    "outer_semimajor_axis_au": outer["pl_orbsmax"],
                    "conjunction": ephemeris_uncertainty_metrics(
                        reference_bjd, inner, outer, stellar_radius_solar
                    ),
                }
            )
    result["pair_conjunctions"] = pair_results
    return result


def select_cadence_pair(cadences: list[Mapping[str, Any]]) -> dict[str, Any] | None:
    eligible: list[dict[str, Any]] = []
    for cadence in cadences:
        if not cadence["medium_qualified"]:
            continue
        for pair in cadence["pair_conjunctions"]:
            eligible.append(
                {
                    "cadence_url": cadence["cadence_url"],
                    "fully_followup_capable": cadence["fully_followup_capable"],
                    "sources": cadence["sources"],
                    **pair,
                }
            )
    eligible.sort(
        key=lambda item: (
            not item["fully_followup_capable"],
            item["conjunction"]["nominal_projected_separation_stellar_radii"],
            item["conjunction"]["reference_bjd_utc_approximation"],
            item["cadence_url"],
            item["planet_pair"],
        )
    )
    return eligible[0] if eligible else None


def markdown_result(result: Mapping[str, Any]) -> str:
    lines = [
        "# LS3B HD 63433 header preflight result",
        "",
        "Status: **COMPLETE HEADER-ONLY PREFLIGHT; NO SPECTRAL DATASET VALUES READ; NO SEARCH AUTHORIZED**.",
        "",
        "| Cadence | Band (MHz) | Full HTR | Adjacent pair | Nominal separation (stellar radii) | ±1σ timing-input range |",
        "|---|---|---|---|---:|---:|",
    ]
    for cadence in result["cadences"]:
        medium_headers = [
            header
            for url, header in cadence["headers"].items()
            if url.endswith(".gpuspec.0002.h5") and "error" not in header
        ]
        band = (
            "n/a"
            if not medium_headers
            else f"{min(h['frequency_low_mhz'] for h in medium_headers):.1f}--{max(h['frequency_high_mhz'] for h in medium_headers):.1f}"
        )
        if not cadence["pair_conjunctions"]:
            lines.append(
                f"| `{cadence['cadence_url'].rsplit('/', 1)[-1]}` | {band} | no | n/a | n/a | n/a |"
            )
            continue
        for pair in cadence["pair_conjunctions"]:
            conjunction = pair["conjunction"]
            label = "–".join(name.rsplit(" ", 1)[-1] for name in pair["planet_pair"])
            lines.append(
                f"| `{cadence['cadence_url'].rsplit('/', 1)[-1]}` | {band} | "
                f"{'yes' if cadence['fully_followup_capable'] else 'no'} | {label} | "
                f"{conjunction['nominal_projected_separation_stellar_radii']:.6f} | "
                f"{conjunction['one_sigma_input_corner_separation_min_stellar_radii']:.6f}--"
                f"{conjunction['one_sigma_input_corner_separation_max_stellar_radii']:.6f} |"
            )
    lines.extend(["", "## Decision", ""])
    selected = result["selected_for_preregistration"]
    if selected is None:
        lines.append("No cadence-pair combination passes the frozen header gate. All spectral data remain closed.")
    else:
        pair = "–".join(name.rsplit(" ", 1)[-1] for name in selected["planet_pair"])
        separation = selected["conjunction"]["nominal_projected_separation_stellar_radii"]
        lines.append(
            f"Cadence `{selected['cadence_url'].rsplit('/', 1)[-1]}` with adjacent pair {pair} "
            f"({separation:.6f} stellar radii nominal separation) is selected for a separately frozen "
            "LS3C signal-search preregistration. This result does not itself authorize spectral access."
        )
    lines.extend(
        [
            "",
            "The geometry is a circular, edge-on, common-node ranking approximation. The corner range perturbs periods and transit epochs only; it is a deterministic sensitivity diagnostic, not a confidence interval.",
            "",
            "The ephemeris is frozen from Mallorquín et al. (2024), Table 5 (free-eccentricity solution); the stellar radius is from Table 2.",
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
        "--output", type=Path, default=Path("results_ls3b_header/preflight.json")
    )
    parser.add_argument("--markdown", type=Path, default=Path("LS3B_HEADER_RESULT.md"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config.get("artifact_type") != "seti_repeater.ls3b_header_preflight_plan":
        raise RuntimeError("wrong LS3B configuration artifact")
    inventory_path = Path(config["source"]["inventory_path"])
    if sha256_file(inventory_path) != config["source"]["inventory_sha256"]:
        raise RuntimeError("LS3 inventory source hash changed")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if inventory["result_sha256"] != config["source"]["inventory_result_identity"]:
        raise RuntimeError("LS3 inventory result identity changed")
    if inventory.get("spectral_dataset_values_read") is not False:
        raise RuntimeError("source chain is not metadata-only")

    planets = config["ephemeris"]["planets"]
    if [pair[0]["pl_name"] + ":" + pair[1]["pl_name"] for pair in adjacent_planet_pairs(planets)] != [
        "HD 63433 d:HD 63433 b",
        "HD 63433 b:HD 63433 c",
    ]:
        raise RuntimeError("unexpected adjacent-pair ordering")
    cadence_inputs = build_cadence_inputs(
        inventory, config["target"]["target_id"], config["target"]["cadence_urls"]
    )
    cadence_results = []
    for cadence_input in cadence_inputs:
        headers: dict[str, dict[str, Any]] = {}
        for scan in cadence_input["scans"]:
            for field in ("medium_url", "htr_url"):
                url = scan[field]
                if url:
                    headers[url] = hdf5_header_record(
                        url, config["network"]["user_agent"]
                    )
        cadence_results.append(
            qualify_cadence(
                cadence_input,
                headers,
                config["target"]["archive_source_name"],
                config["header_criteria"],
                planets,
                float(config["target"]["stellar_radius_solar"]),
            )
        )
    selected = select_cadence_pair(cadence_results)
    result: dict[str, Any] = {
        "artifact_type": "seti_repeater.ls3b_header_preflight_result",
        "schema_version": 1,
        "status": "complete-header-only-preflight",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "target": config["target"],
        "ephemeris": config["ephemeris"],
        "geometry_model": config["geometry"],
        "cadences": cadence_results,
        "selected_for_preregistration": selected,
        "technical_no_selection": selected is None,
        "remote_hdf5_metadata_opened": True,
        "spectral_dataset_values_read": False,
        "raw_spectral_payload_published": False,
        "technosignature_claimed": False,
        "search_authorized": False,
    }
    result["result_sha256"] = hashlib.sha256(canonical_json_bytes(result)).hexdigest()
    atomic_write(args.output, canonical_json_bytes(result))
    atomic_write(args.markdown, markdown_result(result).encode("utf-8"))
    print(
        canonical_json_bytes(
            {
                "status": result["status"],
                "selected": selected,
                "result_sha256": result["result_sha256"],
            }
        ).decode("utf-8")
    )


if __name__ == "__main__":
    main()
