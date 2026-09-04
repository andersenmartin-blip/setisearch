#!/usr/bin/env python3
"""Header-only qualification of four LHS 1140 SIGPROC filterbank cadences."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import itertools
import json
import math
import os
from pathlib import Path
import re
import struct
from typing import Any, BinaryIO, Mapping
from urllib.request import Request, urlopen

from seti_repeater.light_sail import CircularTransitPlanet, projected_pair_separation_stellar_radii
from seti_repeater.light_sail_catalog import normalize_target_name
from seti_repeater.search_v0p6 import canonical_json_bytes


HEADER_TYPES = {
    "telescope_id": "<i", "machine_id": "<i", "data_type": "<i",
    "barycentric": "<i", "pulsarcentric": "<i", "nbits": "<i",
    "nsamples": "<i", "nchans": "<i", "nifs": "<i", "nbeams": "<i",
    "ibeam": "<i", "rawdatafile": "str", "source_name": "str",
    "az_start": "<d", "za_start": "<d", "tstart": "<d", "tsamp": "<d",
    "fch1": "<d", "foff": "<d", "refdm": "<d", "period": "<d",
    "src_raj": "<d", "src_dej": "<d",
}


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


def read_exact(handle: BinaryIO, size: int) -> bytes:
    data = handle.read(size)
    if len(data) != size:
        raise RuntimeError("unexpected end of SIGPROC header")
    return data


def read_length(handle: BinaryIO, maximum: int) -> int:
    value = struct.unpack("<I", read_exact(handle, 4))[0]
    if value > maximum:
        raise RuntimeError(f"invalid SIGPROC string length {value}")
    return value


def parse_sigproc_header(handle: BinaryIO, maximum_header_bytes: int) -> tuple[dict[str, Any], int]:
    """Parse only serialized header fields and stop immediately after HEADER_END."""

    header: dict[str, Any] = {}
    consumed = 0
    while consumed < maximum_header_bytes:
        length = read_length(handle, 255)
        consumed += 4
        keyword = read_exact(handle, length).decode("ascii")
        consumed += length
        if keyword == "HEADER_START":
            if header or consumed != 4 + len("HEADER_START"):
                raise RuntimeError("misplaced HEADER_START")
            continue
        if keyword == "HEADER_END":
            return header, consumed
        kind = HEADER_TYPES.get(keyword)
        if kind is None:
            raise RuntimeError(f"unsupported SIGPROC header keyword {keyword!r}")
        if kind == "str":
            value_length = read_length(handle, maximum_header_bytes - consumed)
            consumed += 4
            value = read_exact(handle, value_length).decode("ascii")
            consumed += value_length
        else:
            size = struct.calcsize(kind)
            value = struct.unpack(kind, read_exact(handle, size))[0]
            consumed += size
        header[keyword] = value
    raise RuntimeError("HEADER_END not found within frozen byte limit")


def remote_filterbank_header(url: str, expected_size: int, config: Mapping[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "url": url,
        "expected_size_bytes": expected_size,
        "spectral_sample_unpacked": False,
        "spectral_values_read": False,
    }
    try:
        request = Request(url, headers={"User-Agent": config["network"]["user_agent"]})
        with urlopen(request, timeout=float(config["network"]["timeout_s"])) as response:
            remote_size = int(response.headers["Content-Length"])
            header, header_bytes = parse_sigproc_header(
                response, int(config["header_criteria"]["maximum_header_bytes"])
            )
            record.update({
                "http_status": int(getattr(response, "status", response.getcode())),
                "final_url": response.geturl(),
                "remote_size_bytes": remote_size,
                "remote_size_matches_inventory": remote_size == expected_size,
                "header_bytes_read": header_bytes,
                "parser_stopped_after_header_end": True,
                "header": header,
            })
        nchans = int(header["nchans"])
        nifs = int(header["nifs"])
        nbits = int(header["nbits"])
        payload_bits = (remote_size - header_bytes) * 8
        denominator = nchans * nifs * nbits
        if payload_bits < 0 or denominator <= 0 or payload_bits % denominator:
            raise RuntimeError("filterbank payload size is inconsistent with header geometry")
        ntime = payload_bits // denominator
        fch1 = float(header["fch1"])
        foff = float(header["foff"])
        end = fch1 + (nchans - 1) * foff
        low, high = sorted((fch1, end))
        record.update({
            "source_name": str(header["source_name"]),
            "tstart_mjd": float(header["tstart"]),
            "tsamp_s": float(header["tsamp"]),
            "nchans": nchans,
            "nifs": nifs,
            "nbits": nbits,
            "ntime": int(ntime),
            "fch1_mhz": fch1,
            "foff_mhz": foff,
            "frequency_low_mhz": low,
            "frequency_high_mhz": high,
            "bandwidth_mhz": high - low,
        })
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def scan_key(url: str) -> str:
    match = re.search(r"_(\d{4})\.gpuspec", url)
    if not match:
        raise RuntimeError(f"cannot identify scan key from {url}")
    return match.group(1)


def build_cadence_inputs(inventory: Mapping[str, Any], config: Mapping[str, Any]) -> list[dict[str, Any]]:
    target = next(item for item in inventory["targets"] if item["target_id"] == config["target"]["target_id"])
    source_by_url = {item["cadence_url"]: item for item in target["cadences"]}
    outputs = []
    for frozen in config["target"]["cadences"]:
        cadence = source_by_url[frozen["cadence_url"]]
        scans: dict[str, dict[str, Any]] = {}
        for record in cadence["records"]:
            url = str(record.get("url") or "")
            if not url.endswith((config["header_criteria"]["medium_product_suffix"], config["header_criteria"]["htr_product_suffix"])):
                continue
            key = scan_key(url)
            scan = scans.setdefault(key, {"scan_key": key, "listing_target": record["target"], "listing_mjd": record["mjd"], "medium": None, "htr": None})
            field = "medium" if url.endswith(config["header_criteria"]["medium_product_suffix"]) else "htr"
            if scan[field] is not None:
                raise RuntimeError(f"duplicate {field} product for scan {key}")
            scan[field] = {"url": url, "expected_size_bytes": int(record["size"])}
        outputs.append({
            "band": frozen["band"],
            "cadence_url": frozen["cadence_url"],
            "scans": sorted(scans.values(), key=lambda item: (item["listing_mjd"], item["scan_key"])),
        })
    return outputs


def geometry_metrics(reference_bjd: float, planets: list[Mapping[str, Any]], stellar_radius: float) -> dict[str, Any]:
    def error(record: Mapping[str, Any], name: str) -> float:
        return max(abs(float(record[f"{name}err1"])), abs(float(record[f"{name}err2"])))

    def planet(record: Mapping[str, Any], period_delta: float, epoch_delta: float) -> CircularTransitPlanet:
        return CircularTransitPlanet(str(record["pl_name"]), float(record["pl_orbper"]) + period_delta, float(record["pl_tranmid"]) + epoch_delta, float(record["pl_orbsmax"]))

    first, second = planets
    nominal = projected_pair_separation_stellar_radii(reference_bjd, planet(first, 0, 0), planet(second, 0, 0), stellar_radius)
    separations = []
    for p1, t1, p2, t2 in itertools.product((-1.0, 0.0, 1.0), repeat=4):
        separations.append(projected_pair_separation_stellar_radii(
            reference_bjd,
            planet(first, p1 * error(first, "pl_orbper"), t1 * error(first, "pl_tranmid")),
            planet(second, p2 * error(second, "pl_orbper"), t2 * error(second, "pl_tranmid")),
            stellar_radius,
        ))
    return {
        "planet_pair": [first["pl_name"], second["pl_name"]],
        "reference_bjd_utc_approximation": reference_bjd,
        "nominal_projected_separation_stellar_radii": nominal,
        "one_sigma_input_corner_separation_min_stellar_radii": min(separations),
        "one_sigma_input_corner_separation_max_stellar_radii": max(separations),
        "corner_evaluation_count": len(separations),
        "interpretation": "Deterministic period/epoch sensitivity diagnostic, not a confidence interval.",
    }


def qualify_cadence(cadence: Mapping[str, Any], headers: Mapping[str, Mapping[str, Any]], config: Mapping[str, Any]) -> dict[str, Any]:
    scans = list(cadence["scans"])
    medium = [headers[scan["medium"]["url"]] for scan in scans if scan["medium"]]
    htr = [headers[scan["htr"]["url"]] for scan in scans if scan["htr"]]
    required = int(config["header_criteria"]["required_scan_count"])
    medium_complete = len(medium) == required and all("error" not in item for item in medium)
    htr_complete = len(htr) == required and all("error" not in item for item in htr)
    target_key = normalize_target_name(config["target"]["archive_source_name"])
    sources = [item.get("source_name") for item in medium]
    sequence_matches = bool(medium_complete and all(normalize_target_name(str(sources[index])) == target_key for index in (0, 2, 4)) and all(normalize_target_name(str(sources[index])) != target_key for index in (1, 3, 5)))
    medium_geometry = bool(medium_complete and all(item["remote_size_matches_inventory"] for item in medium) and all(config["header_criteria"]["medium_tsamp_s"][0] <= item["tsamp_s"] <= config["header_criteria"]["medium_tsamp_s"][1] for item in medium) and all(config["header_criteria"]["medium_abs_foff_khz"][0] <= abs(item["foff_mhz"]) * 1000 <= config["header_criteria"]["medium_abs_foff_khz"][1] for item in medium) and all(item["bandwidth_mhz"] >= config["header_criteria"]["minimum_medium_bandwidth_mhz"] for item in medium))
    htr_geometry = bool(htr_complete and all(item["remote_size_matches_inventory"] for item in htr) and all(config["header_criteria"]["htr_tsamp_s"][0] <= item["tsamp_s"] <= config["header_criteria"]["htr_tsamp_s"][1] for item in htr))
    medium_bytes = sum(int(scan["medium"]["expected_size_bytes"]) for scan in scans if scan["medium"])
    resource_pass = medium_bytes <= int(config["resource_gate"]["maximum_selected_medium_download_bytes"])
    qualified = medium_complete and sequence_matches and medium_geometry
    geometry = None
    centre = None
    frequency_distance = None
    if qualified:
        first = medium[0]
        reference = first["tstart_mjd"] + 2_400_000.5 + first["ntime"] * first["tsamp_s"] / (2 * 86_400)
        geometry = geometry_metrics(reference, config["ephemeris"]["planets"], float(config["target"]["stellar_radius_solar"]))
        centre = sum((item["frequency_low_mhz"] + item["frequency_high_mhz"]) / 2 for item in medium) / len(medium)
        frequency_distance = abs(math.log10(centre / float(config["motivation"]["illustrative_optimum_frequency_mhz"])))
    return {
        "band": cadence["band"], "cadence_url": cadence["cadence_url"], "scan_count": len(scans),
        "sources": sources, "medium_header_count": len(medium), "htr_header_count": len(htr),
        "medium_complete": medium_complete, "htr_complete": htr_complete,
        "sequence_matches_abacad": sequence_matches, "medium_geometry_matches": medium_geometry,
        "htr_geometry_matches": htr_geometry, "medium_qualified": qualified,
        "fully_followup_capable": qualified and htr_geometry,
        "medium_download_bytes": medium_bytes, "resource_gate_passes": resource_pass,
        "mean_band_centre_mhz": centre, "log10_frequency_distance_from_anchor": frequency_distance,
        "conjunction": geometry, "headers": {url: dict(value) for url, value in headers.items()},
        "spectral_values_read": False,
    }


def select_cadence(cadences: list[Mapping[str, Any]]) -> dict[str, Any] | None:
    eligible = [item for item in cadences if item["medium_qualified"] and item["fully_followup_capable"] and item["resource_gate_passes"]]
    eligible.sort(key=lambda item: (item["log10_frequency_distance_from_anchor"], item["conjunction"]["nominal_projected_separation_stellar_radii"], item["conjunction"]["reference_bjd_utc_approximation"], item["cadence_url"]))
    if not eligible:
        return None
    item = eligible[0]
    return {key: item[key] for key in ("band", "cadence_url", "medium_download_bytes", "mean_band_centre_mhz", "log10_frequency_distance_from_anchor", "conjunction")}


def markdown_result(result: Mapping[str, Any]) -> str:
    lines = ["# LS4A LHS 1140 filterbank-header preflight result", "", "Status: **COMPLETE HEADER-ONLY PREFLIGHT; NO SPECTRAL VALUES READ; NO SEARCH AUTHORIZED**.", "", "| Band | Cadence | Coverage (MHz) | Medium / HTR | Download (GB) | Nominal c–b separation (Rstar) | Gate |", "|---|---|---:|---:|---:|---:|---|"]
    for item in result["cadences"]:
        med = [h for url, h in item["headers"].items() if url.endswith(".gpuspec.0002.fil") and "error" not in h]
        coverage = "n/a" if not med else f"{min(h['frequency_low_mhz'] for h in med):.1f}--{max(h['frequency_high_mhz'] for h in med):.1f}"
        separation = "n/a" if not item["conjunction"] else f"{item['conjunction']['nominal_projected_separation_stellar_radii']:.3f}"
        gate = item["medium_qualified"] and item["fully_followup_capable"] and item["resource_gate_passes"]
        lines.append(f"| {item['band']} | `{item['cadence_url'].rsplit('/', 1)[-1]}` | {coverage} | {item['medium_header_count']} / {item['htr_header_count']} | {item['medium_download_bytes']/1e9:.3f} | {separation} | {'pass' if gate else 'fail'} |")
    lines.extend(["", "## Decision", ""])
    selected = result["selected_for_preregistration"]
    if selected:
        lines.append(f"The {selected['band']}-band cadence `{selected['cadence_url'].rsplit('/', 1)[-1]}` is selected for a separately frozen filterbank signal-search preregistration. Expected medium-resolution download: {selected['medium_download_bytes']/1e9:.3f} GB. This result does not authorize spectral access.")
    else:
        lines.append("No cadence passes every frozen header and resource gate. All spectral payloads remain closed.")
    lines.extend(["", "The 10 GHz anchor is only a deterministic ranking proxy for the paper's optimum on the order of tens of GHz. Conjunction geometry remains approximate.", "", f"Result identity: `{result['result_sha256']}`.", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path, default=Path("results_ls4a_header/preflight.json"))
    parser.add_argument("--markdown", type=Path, default=Path("LS4A_HEADER_RESULT.md"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config.get("artifact_type") != "seti_repeater.ls4a_fil_header_preflight_plan":
        raise RuntimeError("wrong LS4A configuration artifact")
    source_path = Path(config["source"]["inventory_path"])
    if sha256_file(source_path) != config["source"]["inventory_sha256"]:
        raise RuntimeError("LS3 inventory source hash changed")
    inventory = json.loads(source_path.read_text(encoding="utf-8"))
    if inventory["result_sha256"] != config["source"]["inventory_result_identity"] or inventory.get("spectral_dataset_values_read") is not False:
        raise RuntimeError("LS3 inventory source boundary changed")
    cadence_results = []
    for cadence in build_cadence_inputs(inventory, config):
        headers = {}
        for scan in cadence["scans"]:
            for field in ("medium", "htr"):
                product = scan[field]
                if product:
                    headers[product["url"]] = remote_filterbank_header(product["url"], product["expected_size_bytes"], config)
        cadence_results.append(qualify_cadence(cadence, headers, config))
    selected = select_cadence(cadence_results)
    result: dict[str, Any] = {
        "artifact_type": "seti_repeater.ls4a_fil_header_preflight_result", "schema_version": 1,
        "status": "complete-filterbank-header-only-preflight", "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "target": config["target"], "ephemeris": config["ephemeris"], "motivation": config["motivation"],
        "cadences": cadence_results, "selected_for_preregistration": selected, "technical_no_selection": selected is None,
        "remote_filterbank_headers_opened": True, "spectral_sample_unpacked": False, "spectral_values_read": False,
        "raw_spectral_payload_published": False, "search_authorized": False, "technosignature_claimed": False,
    }
    result["result_sha256"] = hashlib.sha256(canonical_json_bytes(result)).hexdigest()
    atomic_write(args.output, canonical_json_bytes(result))
    atomic_write(args.markdown, markdown_result(result).encode("utf-8"))
    print(canonical_json_bytes({"status": result["status"], "selected": selected, "result_sha256": result["result_sha256"]}).decode("utf-8"))


if __name__ == "__main__":
    main()
