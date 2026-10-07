#!/usr/bin/env python3
"""Run one bounded official Voyager engineering reference, never a sky pilot."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ALLOWED_HOSTS = {"blpd0.ssl.berkeley.edu"}
CHUNK = 1024 * 1024


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def strict_config(path: Path) -> dict:
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError(f"duplicate JSON key: {key}")
            out[key] = value
        return out
    def invalid(value):
        raise ValueError(f"non-finite JSON value: {value}")
    cfg = json.loads(path.read_bytes(), object_pairs_hook=pairs, parse_constant=invalid)
    if cfg["status"] != "FROZEN_ENGINEERING_REFERENCE_NOT_PILOT":
        raise ValueError("engineering-only status required")
    if any(cfg["authority"].values()):
        raise ValueError("all pilot/science/retry authority must remain false")
    if cfg["limits"]["attempts"] != 1:
        raise ValueError("exactly one bootstrap attempt required")
    return cfg


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("unapproved reference URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("credentials/query/fragment forbidden")


def download(url: str, destination: Path, minimum: int, maximum: int, timeout: int) -> dict:
    validate_url(url)
    request = Request(url, headers={"User-Agent": "setisearch-voyager-reference/1"})
    digest = hashlib.sha256()
    count = 0
    with urlopen(request, timeout=timeout) as response, destination.open("xb") as stream:
        final_url = response.geturl()
        validate_url(final_url)
        declared = response.headers.get("Content-Length")
        if declared is not None and int(declared) > maximum:
            raise ValueError("declared download exceeds cap")
        while True:
            body = response.read(CHUNK)
            if not body:
                break
            count += len(body)
            if count > maximum:
                raise ValueError("received download exceeds cap")
            stream.write(body)
            digest.update(body)
        stream.flush()
        os.fsync(stream.fileno())
    if count < minimum:
        raise ValueError("download shorter than frozen minimum")
    return {"requested_url": url, "final_url": final_url, "bytes": count,
            "sha256": digest.hexdigest(), "declared_content_length": int(declared) if declared else None}


def close(a: float, b: float, tolerance: float) -> bool:
    return abs(float(a) - float(b)) <= tolerance


def validate_header(header: dict, shape: tuple[int, ...], expected: dict) -> dict:
    checks = {
        "source_name": str(header["source_name"]) == expected["source_name"],
        "shape": list(shape) == expected["shape"],
        "fch1_mhz": close(header["fch1"], expected["fch1_mhz"], 1e-12),
        "foff_mhz": close(header["foff"], expected["foff_mhz"], 1e-18),
        "tsamp_s": close(header["tsamp"], expected["tsamp_s"], 1e-12),
        "tstart_mjd": close(header["tstart"], expected["tstart_mjd"], 1e-10),
    }
    if not all(checks.values()):
        raise ValueError(f"header mismatch: {checks}")
    return checks


def validate_hits(rows: list[dict], expected: list[dict], frequency_tolerance: float,
                  snr_tolerance: float) -> list[dict]:
    matched = []
    for target in expected:
        candidates = [row for row in rows if close(row["frequency_mhz"], target["frequency_mhz"], frequency_tolerance)]
        if len(candidates) != 1:
            raise ValueError(f"expected one matching reference hit, got {len(candidates)}")
        row = candidates[0]
        if not close(row["snr"], target["snr"], snr_tolerance):
            raise ValueError("reference hit SNR mismatch")
        matched.append(row)
    return matched


def parse_dat(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 12:
            raise ValueError("malformed DAT hit row")
        rows.append({"top_hit": int(fields[0]), "drift_hz_s": float(fields[1]),
                     "snr": float(fields[2]), "frequency_mhz": float(fields[3]),
                     "corrected_frequency_mhz": float(fields[4]), "raw": line})
    return rows


def file_pin(path: Path) -> dict:
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def run(config_path: Path, output: Path) -> dict:
    cfg = strict_config(config_path)
    output.mkdir(parents=False, exist_ok=False)
    started = time.monotonic()
    source_path = output / cfg["source"]["expected_filename"]
    transfer = download(cfg["source"]["url"], source_path,
                        cfg["source"]["minimum_bytes"], cfg["source"]["maximum_bytes"],
                        cfg["limits"]["download_timeout_seconds"])
    expected_sha = cfg["source"]["expected_sha256"]
    if expected_sha is not None and transfer["sha256"] != expected_sha:
        raise ValueError("download SHA256 differs from frozen value")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import blimpy
    from blimpy import Waterfall
    import turbo_seti
    from turbo_seti.find_doppler.find_doppler import FindDoppler

    waterfall = Waterfall(str(source_path))
    shape = tuple(int(x) for x in waterfall.container.file_shape)
    header_checks = validate_header(waterfall.header, shape, cfg["expected_header"])
    search = cfg["search"]
    fdop = FindDoppler(datafile=str(source_path), max_drift=search["max_drift_hz_s"],
                       snr=search["minimum_snr"], out_dir=str(output), n_coarse_chan=1)
    search_started = time.monotonic()
    fdop.search()
    search_seconds = time.monotonic() - search_started
    dat_path = output / source_path.with_suffix(".dat").name
    rows = parse_dat(dat_path)
    matched = validate_hits(rows, search["expected_reference_hits"],
                            search["frequency_tolerance_mhz"], search["snr_tolerance"])

    plot = Waterfall(str(source_path), f_start=8419.272, f_stop=8419.322)
    plot.plot_waterfall()
    plt.tight_layout()
    png_path = output / "voyager_reference_waterfall.png"
    plt.savefig(png_path, dpi=150)
    plt.close("all")
    source_path.unlink()

    result = {
        "schema": "radio-reference-voyager-result-v1",
        "status": "PASSED_ENGINEERING_REFERENCE_NOT_PILOT",
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "transfer": {**transfer, "payload_retained": False},
        "header_checks": header_checks,
        "search": {"max_drift_hz_s": search["max_drift_hz_s"],
                   "minimum_snr": search["minimum_snr"], "reported_hits": len(rows),
                   "matched_official_reference_hits": matched,
                   "elapsed_seconds": search_seconds},
        "software": {"python": platform.python_version(), "blimpy": blimpy.__version__,
                     "turbo_seti": getattr(turbo_seti, "__version__", "2.3.2")},
        "outputs": {dat_path.name: file_pin(dat_path), png_path.name: file_pin(png_path)},
        "total_elapsed_seconds": time.monotonic() - started,
        "authority": dict(cfg["authority"]),
        "pilot_spectra_opened": False,
        "scientific_claim": False,
    }
    (output / "RESULT.json").write_bytes(canonical(result))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.config, args.output)
    except Exception as error:
        args.output.mkdir(parents=True, exist_ok=True)
        # The source array is an explicitly transient input. Never publish a
        # complete or partial telescope payload when a bounded run fails.
        for payload in args.output.glob("*.h5"):
            payload.unlink()
        failure = {"schema": "radio-reference-voyager-failure-v1", "status": "FAILED_CLOSED",
                   "error_type": type(error).__name__, "error": str(error),
                   "pilot_spectra_opened": False, "scientific_claim": False,
                   "automatic_retry": False}
        (args.output / "FAILURE.json").write_bytes(canonical(failure))
        raise
    print(json.dumps({"status": result["status"], "reported_hits": result["search"]["reported_hits"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
