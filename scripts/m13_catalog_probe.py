#!/usr/bin/env python3
"""Metadata-only probe for a new Milestone 13 Breakthrough Listen cadence.

This script reads directory indexes, HTTP metadata, and SIGPROC headers only.
It never requests bytes from the spectral payload beyond the header prefix.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from seti_repeater.sigproc import remote_header


ARCHIVE_ROOT = "http://blpd0.ssl.berkeley.edu/"
CANDIDATE_ALIASES = {
    "trappist_1": ["TRAPPIST1", "TRAPPIST-1"],
    "toi_700": ["TOI700", "TOI-700"],
    "k2_18": ["K2-18", "K218"],
    "gj_667c": ["GJ667C", "GJ667"],
    "gj_273": ["GJ273", "LUYTEN"],
    "gj_581": ["GJ581"],
    "ross_128": ["ROSS128"],
    "tau_ceti": ["TAUCETI", "TAU-CETI"],
    "teegarden": ["TEEGARDEN", "TEEGARDENSSTAR"],
    "gj_1002": ["GJ1002"],
    "wolf_1061": ["WOLF1061"],
    "gj_1061": ["GJ1061"],
}
HREF_PATTERN = re.compile(r'href=["\']([^"\']+)', re.IGNORECASE)


def fetch_index(url: str) -> dict:
    record: dict = {"url": url}
    try:
        request = Request(url, headers={"User-Agent": "setisearch-m13-metadata/1.0"})
        with urlopen(request, timeout=60) as response:
            payload = response.read(10_000_000)
            record["status"] = int(getattr(response, "status", response.getcode()))
            record["final_url"] = response.geturl()
        text = payload.decode("utf-8", errors="replace")
        record["hrefs"] = [html.unescape(value) for value in HREF_PATTERN.findall(text)]
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def standard_filterbanks(index: dict) -> list[str]:
    files = []
    for href in index.get("hrefs", []):
        name = href.rsplit("/", 1)[-1]
        if name.lower().endswith(".gpuspec.0000.fil"):
            files.append(urljoin(index["final_url"], href))
    return sorted(set(files))


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
    parser.add_argument("--max-files-per-alias", type=int, default=60)
    args = parser.parse_args()

    top_level = fetch_index(ARCHIVE_ROOT)
    targets = []
    for target_id, aliases in CANDIDATE_ALIASES.items():
        alias_records = []
        for alias in aliases:
            root_index = fetch_index(urljoin(ARCHIVE_ROOT, alias + "/"))
            band_index = fetch_index(urljoin(ARCHIVE_ROOT, alias + "/L/"))
            urls = standard_filterbanks(band_index)[:args.max_files_per_alias]
            headers = [header_record(url) for url in urls]
            alias_records.append({
                "alias": alias,
                "root_index": root_index,
                "l_band_index": band_index,
                "standard_filterbank_count": len(urls),
                "headers": headers,
                "qualifying_abacad_cadences": find_abacad(headers),
            })
        targets.append({"target_id": target_id, "aliases": alias_records})

    result = {
        "purpose": "Milestone 13 metadata/header-only target selection",
        "spectral_payload_inspected": False,
        "archive_root": ARCHIVE_ROOT,
        "required_guarded_range_mhz": [1399.65, 1425.85],
        "top_level_index": top_level,
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
                    "files": alias["standard_filterbank_count"],
                    "cadences": len(alias["qualifying_abacad_cadences"]),
                    "error": alias["l_band_index"].get("error"),
                }
                for alias in item["aliases"]
            ],
        }
        for item in targets
    ]
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
