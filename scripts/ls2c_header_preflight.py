#!/usr/bin/env python3
"""Header-only qualification and conjunction ranking for HD 260655 cadences."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.request import Request, urlopen

from seti_repeater.light_sail import (
    CircularTransitPlanet,
    projected_pair_separation_stellar_radii,
)
from seti_repeater.light_sail_catalog import normalize_target_name
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


def json_value(value: Any) -> Any:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def hdf5_header_record(url: str, user_agent: str) -> dict[str, Any]:
    """Read HTTP/HDF5 metadata without indexing the spectral dataset."""

    import fsspec
    import h5py

    record: dict[str, Any] = {
        "url": url,
        "spectral_dataset_values_read": False,
    }
    try:
        request = Request(url, method="HEAD", headers={"User-Agent": user_agent})
        with urlopen(request, timeout=90) as response:
            record["http_status"] = int(
                getattr(response, "status", response.getcode())
            )
            record["final_url"] = response.geturl()
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
                attrs = {
                    key: json_value(value) for key, value in handle.attrs.items()
                }
                attrs.update(
                    {key: json_value(value) for key, value in dataset.attrs.items()}
                )
                fch1 = float(attrs["fch1"])
                foff = float(attrs["foff"])
                nchans = int(dataset.shape[-1])
                end_mhz = fch1 + (nchans - 1) * foff
                low_mhz, high_mhz = sorted((fch1, end_mhz))
                record.update(
                    {
                        "source_name": str(attrs.get("source_name", "")),
                        "tstart_mjd": float(attrs["tstart"]),
                        "tsamp_s": float(attrs["tsamp"]),
                        "nchans": nchans,
                        "ntime": int(dataset.shape[0]),
                        "fch1_mhz": fch1,
                        "foff_mhz": foff,
                        "frequency_low_mhz": low_mhz,
                        "frequency_high_mhz": high_mhz,
                        "bandwidth_mhz": high_mhz - low_mhz,
                        "dataset_shape": [int(value) for value in dataset.shape],
                        "dataset_dtype": str(dataset.dtype),
                        "dataset_chunks": (
                            [int(value) for value in dataset.chunks]
                            if dataset.chunks
                            else None
                        ),
                        "dataset_compression": dataset.compression,
                    }
                )
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def scan_key(url: str) -> str:
    match = re.search(r"_(\d{4})\.gpuspec", url)
    if not match:
        raise RuntimeError(f"cannot identify scan key from {url}")
    return match.group(1)


def build_cadence_inputs(
    source: Mapping[str, Any], target_id: str, expected_urls: list[str]
) -> list[dict[str, Any]]:
    target = next(item for item in source["targets"] if item["target_id"] == target_id)
    by_url = {item["cadence_url"]: item for item in target["cadences"]}
    if sorted(by_url) != sorted(expected_urls):
        raise RuntimeError("LS2B cadence inventory changed")
    outputs = []
    for cadence_url in expected_urls:
        cadence = by_url[cadence_url]
        scans: dict[str, dict[str, Any]] = {}
        for record in cadence["records"]:
            url = str(record.get("url") or "")
            if not url.endswith((".gpuspec.0002.h5", ".gpuspec.8.0001.h5")):
                continue
            key = scan_key(url)
            scan = scans.setdefault(
                key,
                {
                    "scan_key": key,
                    "listing_target": record["target"],
                    "listing_mjd": record["mjd"],
                    "medium_url": None,
                    "htr_url": None,
                },
            )
            field = "medium_url" if url.endswith(".gpuspec.0002.h5") else "htr_url"
            if scan[field] is not None:
                raise RuntimeError(f"duplicate {field} for scan {key}")
            scan[field] = url
        ordered = sorted(scans.values(), key=lambda item: (item["listing_mjd"], item["scan_key"]))
        outputs.append({"cadence_url": cadence_url, "scans": ordered})
    return outputs


def ephemeris_uncertainty_metrics(
    reference_bjd: float,
    first_record: Mapping[str, Any],
    second_record: Mapping[str, Any],
    stellar_radius_solar: float,
) -> dict[str, Any]:
    """Return nominal separation and a deterministic ±1σ input-corner envelope."""

    def error(record: Mapping[str, Any], name: str) -> float:
        return max(abs(float(record.get(f"{name}err1") or 0.0)), abs(float(record.get(f"{name}err2") or 0.0)))

    def planet(record: Mapping[str, Any], period_delta: float, epoch_delta: float) -> CircularTransitPlanet:
        return CircularTransitPlanet(
            str(record["pl_name"]),
            float(record["pl_orbper"]) + period_delta,
            float(record["pl_tranmid"]) + epoch_delta,
            float(record["pl_orbsmax"]),
        )

    first_period_error = error(first_record, "pl_orbper")
    second_period_error = error(second_record, "pl_orbper")
    first_epoch_error = error(first_record, "pl_tranmid")
    second_epoch_error = error(second_record, "pl_tranmid")
    nominal_first = planet(first_record, 0.0, 0.0)
    nominal_second = planet(second_record, 0.0, 0.0)
    nominal = projected_pair_separation_stellar_radii(
        reference_bjd, nominal_first, nominal_second, stellar_radius_solar
    )
    separations = []
    signs = (-1.0, 0.0, 1.0)
    for first_period_sign, first_epoch_sign, second_period_sign, second_epoch_sign in itertools.product(signs, repeat=4):
        first = planet(
            first_record,
            first_period_sign * first_period_error,
            first_epoch_sign * first_epoch_error,
        )
        second = planet(
            second_record,
            second_period_sign * second_period_error,
            second_epoch_sign * second_epoch_error,
        )
        separations.append(
            projected_pair_separation_stellar_radii(
                reference_bjd, first, second, stellar_radius_solar
            )
        )

    def propagated_timing(record: Mapping[str, Any], period_error: float, epoch_error: float) -> dict[str, Any]:
        cycles = abs((reference_bjd - float(record["pl_tranmid"])) / float(record["pl_orbper"]))
        uncertainty_days = math.sqrt(epoch_error**2 + (cycles * period_error) ** 2)
        return {
            "planet": record["pl_name"],
            "cycles_from_reference_epoch": cycles,
            "propagated_one_sigma_timing_uncertainty_minutes": uncertainty_days * 1440.0,
        }

    return {
        "model": "circular edge-on common-node; MJD treated as BJD for ranking",
        "reference_bjd_utc_approximation": reference_bjd,
        "nominal_projected_separation_stellar_radii": nominal,
        "one_sigma_input_corner_separation_min_stellar_radii": min(separations),
        "one_sigma_input_corner_separation_max_stellar_radii": max(separations),
        "corner_evaluation_count": len(separations),
        "timing_uncertainties": [
            propagated_timing(first_record, first_period_error, first_epoch_error),
            propagated_timing(second_record, second_period_error, second_epoch_error),
        ],
        "interpretation": "The corner envelope is a deterministic sensitivity diagnostic, not a confidence interval.",
    }


def qualify_cadence(
    cadence_input: Mapping[str, Any],
    headers: Mapping[str, Mapping[str, Any]],
    target_name: str,
    criteria: Mapping[str, Any],
    geometry: Mapping[str, Any],
) -> dict[str, Any]:
    scans = list(cadence_input["scans"])
    medium = [headers[scan["medium_url"]] for scan in scans if scan["medium_url"]]
    htr = [headers[scan["htr_url"]] for scan in scans if scan["htr_url"]]
    medium_complete = len(medium) == 6 and all("error" not in item for item in medium)
    htr_complete = len(htr) == 6 and all("error" not in item for item in htr)
    sources = [item.get("source_name") for item in medium]
    on_key = normalize_target_name(target_name)
    sequence_matches = bool(
        medium_complete
        and len(sources) == 6
        and all(normalize_target_name(str(sources[index])) == on_key for index in (0, 2, 4))
        and all(normalize_target_name(str(sources[index])) != on_key for index in (1, 3, 5))
    )
    medium_geometry_matches = bool(
        medium_complete
        and len({(item["nchans"], item["tsamp_s"], item["foff_mhz"]) for item in medium}) == 1
        and all(criteria["medium_tsamp_s"][0] <= item["tsamp_s"] <= criteria["medium_tsamp_s"][1] for item in medium)
        and all(criteria["medium_abs_foff_khz"][0] <= abs(item["foff_mhz"]) * 1000.0 <= criteria["medium_abs_foff_khz"][1] for item in medium)
        and all(item["bandwidth_mhz"] >= criteria["minimum_medium_bandwidth_mhz"] for item in medium)
    )
    htr_geometry_matches = bool(
        htr_complete
        and all(criteria["htr_tsamp_s"][0] <= item["tsamp_s"] <= criteria["htr_tsamp_s"][1] for item in htr)
    )
    medium_qualified = medium_complete and sequence_matches and medium_geometry_matches
    metrics = None
    if medium_qualified:
        first = medium[0]
        reference_bjd = (
            first["tstart_mjd"]
            + 2_400_000.5
            + (first["ntime"] * first["tsamp_s"]) / (2.0 * 86_400.0)
        )
        metrics = ephemeris_uncertainty_metrics(
            reference_bjd,
            geometry["eligible_planets"][0],
            geometry["eligible_planets"][1],
            float(geometry["stellar_radius_solar"]),
        )
    return {
        "cadence_url": cadence_input["cadence_url"],
        "scan_count": len(scans),
        "sources": sources,
        "medium_header_count": len(medium),
        "htr_header_count": len(htr),
        "medium_complete": medium_complete,
        "htr_complete": htr_complete,
        "sequence_matches_abacad": sequence_matches,
        "medium_geometry_matches": medium_geometry_matches,
        "htr_geometry_matches": htr_geometry_matches,
        "medium_qualified": medium_qualified,
        "fully_followup_capable": medium_qualified and htr_geometry_matches,
        "conjunction": metrics,
        "headers": {url: dict(record) for url, record in headers.items()},
        "spectral_dataset_values_read": False,
    }


def select_cadence(cadences: list[Mapping[str, Any]]) -> dict[str, Any] | None:
    eligible = [item for item in cadences if item["medium_qualified"]]
    eligible.sort(
        key=lambda item: (
            not item["fully_followup_capable"],
            item["conjunction"]["nominal_projected_separation_stellar_radii"],
            item["conjunction"]["reference_bjd_utc_approximation"],
            item["cadence_url"],
        )
    )
    if not eligible:
        return None
    selected = eligible[0]
    return {
        key: selected[key]
        for key in (
            "cadence_url",
            "fully_followup_capable",
            "conjunction",
            "sources",
        )
    }


def markdown_result(result: Mapping[str, Any]) -> str:
    lines = [
        "# LS2C HD 260655 header preflight result",
        "",
        "Status: **COMPLETE HEADER-ONLY PREFLIGHT; NO SPECTRAL DATASET VALUES READ; NO SEARCH AUTHORIZED**.",
        "",
        "| Cadence | Band (MHz) | Medium qualified | Full HTR | Nominal separation (stellar radii) | ±1σ-input corner range |",
        "|---|---|---|---|---:|---:|",
    ]
    for item in result["cadences"]:
        medium_headers = [
            header
            for url, header in item["headers"].items()
            if url.endswith(".gpuspec.0002.h5") and "error" not in header
        ]
        band = "n/a" if not medium_headers else f"{min(h['frequency_low_mhz'] for h in medium_headers):.1f}--{max(h['frequency_high_mhz'] for h in medium_headers):.1f}"
        conjunction = item["conjunction"]
        nominal = "n/a" if conjunction is None else f"{conjunction['nominal_projected_separation_stellar_radii']:.6f}"
        envelope = "n/a" if conjunction is None else f"{conjunction['one_sigma_input_corner_separation_min_stellar_radii']:.6f}--{conjunction['one_sigma_input_corner_separation_max_stellar_radii']:.6f}"
        lines.append(
            f"| `{item['cadence_url'].rsplit('/', 1)[-1]}` | {band} | "
            f"{'yes' if item['medium_qualified'] else 'no'} | "
            f"{'yes' if item['fully_followup_capable'] else 'no'} | {nominal} | {envelope} |"
        )
    lines.extend(["", "## Decision", ""])
    selected = result["selected_for_preregistration"]
    if selected is None:
        lines.append("No cadence passes the frozen header gate. All spectral data remain closed.")
    else:
        lines.append(
            f"Cadence `{selected['cadence_url'].rsplit('/', 1)[-1]}` is selected for a separately frozen LS2 signal-search preregistration. This result does not itself authorize spectral access."
        )
    lines.extend(
        [
            "",
            "The ephemeris corner range perturbs both periods and transit epochs by their published ±1σ values. It is a deterministic sensitivity diagnostic, not a confidence interval.",
            "",
            f"Result identity: `{result['result_sha256']}`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path, default=Path("results_ls2c_header/preflight.json"))
    parser.add_argument("--markdown", type=Path, default=Path("LS2C_HEADER_RESULT.md"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config.get("artifact_type") != "seti_repeater.ls2c_header_preflight_plan":
        raise RuntimeError("wrong LS2C configuration artifact")
    ls2b_path = Path(config["sources"]["ls2b_cadence"]["path"])
    ls2_path = Path(config["sources"]["ls2_inventory"]["path"])
    if sha256_file(ls2b_path) != config["sources"]["ls2b_cadence"]["sha256"]:
        raise RuntimeError("LS2B source hash changed")
    if sha256_file(ls2_path) != config["sources"]["ls2_inventory"]["sha256"]:
        raise RuntimeError("LS2 source hash changed")
    ls2b = json.loads(ls2b_path.read_text(encoding="utf-8"))
    ls2 = json.loads(ls2_path.read_text(encoding="utf-8"))
    if ls2b["result_sha256"] != config["sources"]["ls2b_cadence"]["result_identity"]:
        raise RuntimeError("LS2B result identity changed")
    if ls2["result_sha256"] != config["sources"]["ls2_inventory"]["result_identity"]:
        raise RuntimeError("LS2 result identity changed")
    if ls2b.get("spectral_dataset_values_read") is not False or ls2.get("spectral_dataset_values_read") is not False:
        raise RuntimeError("source chain is not metadata-only")

    cadence_inputs = build_cadence_inputs(
        ls2b, config["target"]["target_id"], config["target"]["cadence_urls"]
    )
    geometry_source = next(
        item for item in ls2["targets"] if item["target_id"] == config["target"]["target_id"]
    )["geometry"]
    geometry = {
        **geometry_source,
        "stellar_radius_solar": config["target"]["stellar_radius_solar"],
    }
    cadence_results = []
    for cadence_input in cadence_inputs:
        headers = {}
        for scan in cadence_input["scans"]:
            for field in ("medium_url", "htr_url"):
                url = scan[field]
                if url:
                    headers[url] = hdf5_header_record(url, config["network"]["user_agent"])
        cadence_results.append(
            qualify_cadence(
                cadence_input,
                headers,
                config["target"]["archive_source_name"],
                config["header_criteria"],
                geometry,
            )
        )
    selected = select_cadence(cadence_results)
    result: dict[str, Any] = {
        "artifact_type": "seti_repeater.ls2c_header_preflight_result",
        "schema_version": 1,
        "status": "complete-header-only-preflight",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "target": config["target"],
        "geometry": geometry,
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
    print(canonical_json_bytes({
        "status": result["status"],
        "selected": result["selected_for_preregistration"],
        "result_sha256": result["result_sha256"],
    }).decode("utf-8"))


if __name__ == "__main__":
    main()
