#!/usr/bin/env python3
"""Frozen retrospective LS4F reanalysis; derived evidence only is retained."""
from __future__ import annotations

import hashlib
import itertools
import json
import os
from pathlib import Path
import shutil
import time
from urllib.request import Request, urlopen

import numpy as np

from ls4c_htr_followup import parse_and_validate_header
from seti_repeater.light_sail_htr import evaluate_timeseries, compare_on_off
from seti_repeater.light_sail_residual import channel_indices, residual_metrics, compare_residuals, matched_pulses
from seti_repeater.search_v0p6 import canonical_json_bytes

ROOT = Path(__file__).resolve().parents[1]


def atomic_json(path: Path, data: dict):
    path.parent.mkdir(exist_ok=True, parents=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_json_bytes(data))
    os.replace(temporary, path)


def verify_manifest(path: Path):
    for line in path.read_text().splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
            raise ValueError(f"manifest mismatch: {relative}")


def download_exact(source: dict, path: Path, config: dict) -> dict:
    expected = source["source_size_bytes"]
    if shutil.disk_usage(path.parent).free < expected + config["resource"]["free_headroom_bytes"]:
        raise RuntimeError("insufficient free disk")
    digest, count, started = hashlib.sha256(), 0, time.monotonic()
    temporary = path.with_suffix(".part")
    request = Request(source["source_url"], headers={"User-Agent": "setisearch-ls4f/1.0", "Accept-Encoding": "identity"})
    try:
        with urlopen(request, timeout=30) as response, temporary.open("wb") as out:
            if response.status != 200:
                raise RuntimeError("expected full-file HTTP 200")
            length = response.headers.get("Content-Length")
            if length is not None and int(length) != expected:
                raise RuntimeError("remote size differs from frozen source")
            final_url = response.url
            while count < expected:
                chunk = response.read(min(8 * 1024 * 1024, expected - count))
                if not chunk:
                    raise RuntimeError(f"short download at {count}/{expected}")
                out.write(chunk)
                digest.update(chunk)
                previous = count
                count += len(chunk)
                if count // (512 * 1024 * 1024) != previous // (512 * 1024 * 1024):
                    print(f"{source['label']}: downloaded {count / 1e9:.2f}/{expected / 1e9:.2f} GB", flush=True)
            out.flush()
            os.fsync(out.fileno())
        if count != expected or digest.hexdigest() != source["source_sha256"]:
            raise RuntimeError("source size or SHA256 mismatch")
        os.replace(temporary, path)
        return {"source_sha256": digest.hexdigest(), "bytes": count, "final_url": final_url,
                "download_seconds": time.monotonic() - started}
    finally:
        temporary.unlink(missing_ok=True)


def extract_bands(matrix, original: np.ndarray, corrected: np.ndarray, lo: int, hi: int, before: int, after: int, chunk_rows: int):
    """One chunked pass: two collapsed series and channel reference statistics."""
    n = len(matrix)
    old_series, new_series = np.empty(n), np.empty(n)
    reference_sum = np.zeros(len(original))
    reference_count = 0
    zero_count = np.zeros(len(original), dtype=np.int64)
    high_count = zero_count.copy()
    corrected_local = np.flatnonzero(np.isin(original, corrected))
    for start in range(0, n, chunk_rows):
        stop = min(n, start + chunk_rows)
        block = np.asarray(matrix[start:stop, original], dtype=np.float64)
        old_series[start:stop] = block.mean(axis=1)
        new_series[start:stop] = block[:, corrected_local].mean(axis=1)
        indices = np.arange(start, stop)
        reference = (indices < before) | (indices >= after)
        reference_sum += block[reference].sum(axis=0)
        reference_count += int(reference.sum())
        zero_count += (block == 0).sum(axis=0)
        high_count += (block == 255).sum(axis=0)
    if reference_count < 32:
        raise ValueError("short channel reference")
    return old_series, new_series, reference_sum / reference_count, {
        "channel_indices": original.tolist(), "reference_sample_count": reference_count,
        "zero_byte_counts": zero_count.tolist(), "max_byte_counts": high_count.tolist(),
        "sample_count_per_channel": n,
        "interpretation": "Endpoint occupancy in an 8-bit product is descriptive; it does not prove hardware saturation.",
    }


def concentration(matrix, indices: np.ndarray, baseline, peak: float, width: float, dt: float, corrected):
    centers_start = max(0, int(np.ceil((peak - width / 2) / dt - 0.5)))
    centers_stop = min(len(matrix), int(np.ceil((peak + width / 2) / dt - 0.5)))
    if centers_stop <= centers_start:
        return {"available": False}
    power = np.asarray(matrix[centers_start:centers_stop, indices], dtype=np.float64).mean(axis=0)
    positive = np.maximum(power - baseline, 0)
    total = positive.sum()
    extras = ~np.isin(indices, corrected)
    return {"available": bool(total > 0), "sample_count": centers_stop - centers_start,
            "largest_channel_fraction": float(positive.max() / total) if total > 0 else None,
            "extra_channel_fraction": float(positive[extras].sum() / total) if total > 0 else None,
            "largest_channel_index": int(indices[np.argmax(positive)]) if total > 0 else None}


def numeric_agreement(actual, expected, rtol, atol):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and actual.keys() == expected.keys() and all(numeric_agreement(actual[k], v, rtol, atol) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(numeric_agreement(a, b, rtol, atol) for a, b in zip(actual, expected))
    if isinstance(expected, float):
        return bool(np.isclose(actual, expected, rtol=rtol, atol=atol))
    return actual == expected


def evaluate_source(path: Path, source: dict, config: dict, historical: dict, old_config: dict, settings: dict):
    old_source = next(x for x in old_config["sources"] if x["label"] == source["label"])
    header, offset = parse_and_validate_header(path, old_source, old_config)
    dimensions = old_config["expected_filterbank_header"]
    dt, n = header["tsamp"], dimensions["ntime"]
    matrix = np.memmap(path, mode="r", dtype=np.uint8, offset=offset, shape=(n, dimensions["nchans"]))
    role = "on" if source["label"] == "A1" else "off"
    records, pulse_count = [], 0
    for item in historical["candidates"]:
        event, band = item["stage1_event"], item[role + "_band"]
        old_indices = np.arange(band["channel_start"], band["channel_stop"])
        new_indices = channel_indices(header["fch1"], header["foff"], header["nchans"], band["requested_frequency_low_mhz"], band["requested_frequency_high_mhz"])
        start, stop = event["time_start_s"], event["time_stop_s"]
        times = (np.arange(n) + 0.5) * dt
        lo, hi = np.searchsorted(times, [start, stop])
        before, after = np.searchsorted(times, [start - settings["reference_guard_s"], stop + settings["reference_guard_s"]])
        old_series, new_series, baseline, occupancy = extract_bands(matrix, old_indices, new_indices, lo, hi, before, after, config["resource"]["chunk_rows"])
        old_metrics = evaluate_timeseries(old_series, dt, start, stop, old_config["analysis"]["pulse_width_s"], reference_guard_s=old_config["analysis"]["reference_guard_s"], pulse_score_threshold=old_config["analysis"]["pulse_score_threshold"])
        if not numeric_agreement(old_metrics, item[role + "_metrics"], **config["replay_tolerance"]):
            raise RuntimeError(f"historical metric replay mismatch: {item['candidate_id']} {role}")
        variants = {}
        for name, series, indices in [("original", old_series, old_indices), ("corrected", new_series, new_indices)]:
            legacy = old_metrics if name == "original" else evaluate_timeseries(series, dt, start, stop, old_config["analysis"]["pulse_width_s"], reference_guard_s=old_config["analysis"]["reference_guard_s"], pulse_score_threshold=old_config["analysis"]["pulse_score_threshold"])
            metrics = residual_metrics(series, dt, start, stop, settings)
            for scale in metrics["scales"]:
                for region in ("inside_pulses", "reference_pulses"):
                    for pulse in scale[region]:
                        pulse_count += 1
                        if pulse_count > config["resource"]["max_pulse_records_per_source"]:
                            raise RuntimeError("pulse record limit exceeded; no truncation permitted")
                        pulse["channel_concentration_in_original_band"] = concentration(matrix, old_indices, baseline, pulse["peak_time_s"], scale["effective_width_s"], dt, new_indices)
            variants[name] = {"indices": indices.tolist(), "legacy_metrics": legacy, "residual_metrics": metrics}
        records.append({"candidate_id": item["candidate_id"], "historical_replay_agrees": True,
                        "channel_endpoint_occupancy": occupancy, "variants": variants})
        print(f"{source['label']}: evaluated {item['candidate_id']}", flush=True)
    del matrix
    cross_band = []
    for left, right in itertools.combinations(records, 2):
        for a, b in zip(left["variants"]["corrected"]["residual_metrics"]["scales"], right["variants"]["corrected"]["residual_metrics"]["scales"]):
            aa = sorted(a["inside_pulses"] + a["reference_pulses"], key=lambda p: p["peak_time_s"])
            bb = sorted(b["inside_pulses"] + b["reference_pulses"], key=lambda p: p["peak_time_s"])
            count = matched_pulses(aa, bb, a["effective_width_s"])
            cross_band.append({"candidate_pair": [left["candidate_id"], right["candidate_id"]],
                               "width_s": a["requested_width_s"], "matched_pulses": count,
                               "pulse_counts": [len(aa), len(bb)]})
    return {"label": source["label"], "source_sha256": source["source_sha256"], "candidates": records,
            "cross_band_corrected_matches": cross_band, "pulse_record_count": pulse_count}


def main():
    verify_manifest(ROOT / "LS4F_FREEZE.sha256")
    verify_manifest(ROOT / "LS4E_FREEZE.sha256")
    config = json.loads((ROOT / "config/ls4f_native_reanalysis.json").read_text())
    for relative, expected in config["input_sha256"].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"input changed: {relative}")
    historical = json.loads((ROOT / "results_ls4c_htr/followup.json").read_text())
    old_config = json.loads((ROOT / "config/ls4c_lhs1140_x_htr_followup.json").read_text())
    settings = json.loads((ROOT / "config/ls4e_residual_qualification.json").read_text())["settings"]
    if config["sources"] != historical["source_receipts"]:
        raise RuntimeError("source inventory differs from frozen LS4C receipts")
    qualification = json.loads((ROOT / "results_ls4e_qualification/qualification.json").read_text())
    if qualification["status"] != "synthetic-gate-passed":
        raise RuntimeError("LS4E gate not passed")
    if sum(x["source_size_bytes"] for x in config["sources"]) > config["resource"]["max_total_download_bytes"]:
        raise RuntimeError("resource cap exceeded")
    output = ROOT / "results_ls4f_reanalysis"
    if output.exists():
        raise RuntimeError("result directory exists; preserve prior execution")
    output.mkdir()
    rawdir = ROOT / "data_ls4f_runtime"
    rawdir.mkdir(exist_ok=True)
    records = []
    try:
        for source in config["sources"]:
            path = rawdir / f"{source['label']}.fil"
            try:
                receipt = download_exact(source, path, config)
                record = evaluate_source(path, source, config, historical, old_config, settings)
                record["download_receipt"] = receipt
            finally:
                path.unlink(missing_ok=True)
                path.with_suffix(".part").unlink(missing_ok=True)
            record["raw_file_deleted"] = True
            atomic_json(output / f"{source['label']}_derived.json", record)
            records.append(record)
        comparisons = []
        for on, off in zip(records[0]["candidates"], records[1]["candidates"]):
            variants = {}
            for name in ("original", "corrected"):
                a, b = on["variants"][name], off["variants"][name]
                legacy = compare_on_off(a["legacy_metrics"], b["legacy_metrics"], **{k: old_config["analysis"][k] for k in ["envelope_on_threshold", "envelope_off_veto_threshold", "pulse_score_threshold", "minimum_on_off_pulse_margin", "required_subsecond_scales"]})
                variants[name] = {"legacy_comparison": legacy, "residual_comparison": compare_residuals(a["residual_metrics"], b["residual_metrics"], settings)}
            previous = next(x for x in historical["candidates"] if x["candidate_id"] == on["candidate_id"])
            if not numeric_agreement(variants["original"]["legacy_comparison"], previous["comparison"], **config["replay_tolerance"]):
                raise RuntimeError("historical disposition does not replay")
            comparisons.append({"candidate_id": on["candidate_id"], "variants": variants})
        result = {"artifact_type": "seti_repeater.ls4f_native_reanalysis", "status": "retrospective-reanalysis-complete",
                  "candidates": comparisons, "new_radio_spectral_values_read": True, "independent_observation_completed": False,
                  "technosignature_claimed": False, "raw_spectral_payload_published": False,
                  "derived_source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob('*_derived.json')},
                  "config_sha256": hashlib.sha256((ROOT / 'config/ls4f_native_reanalysis.json').read_bytes()).hexdigest()}
        result["result_sha256"] = hashlib.sha256(canonical_json_bytes(result)).hexdigest()
        atomic_json(output / "reanalysis.json", result)
        print(json.dumps({"status": result["status"], "result_sha256": result["result_sha256"]}), flush=True)
    except Exception as error:
        atomic_json(output / "abort.json", {"status": "aborted-no-complete-conclusion", "error": str(error), "completed_sources": [r["label"] for r in records]})
        raise


if __name__ == "__main__":
    main()
