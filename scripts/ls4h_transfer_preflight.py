#!/usr/bin/env python3
"""LS4H metadata and analytic adapter preflight; never reads telescope spectra."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def verify_freeze(root=ROOT):
    for line in (root / "LS4H_FREEZE.sha256").read_text().splitlines():
        expected, relative = line.split("  ", 1)
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f"freeze mismatch: {relative}")


def geometry(medium, htr):
    tr = medium["tsamp_s"] / htr["tsamp_s"]
    fr = htr["foff_mhz"] / medium["foff_mhz"]
    nt, nf = round(tr), round(fr)
    if nt < 1 or nf < 1 or not math.isclose(tr, nt, abs_tol=1e-9, rel_tol=0) or not math.isclose(fr, nf, abs_tol=1e-9, rel_tol=0):
        raise ValueError("noninteger grid ratios")
    if medium["nchans"] != htr["nchans"] * nf:
        raise ValueError("frequency channel counts do not group exactly")
    expected = medium["fch1_mhz"] + ((nf - 1) / 2 + np.arange(htr["nchans"]) * nf) * medium["foff_mhz"]
    observed = htr["fch1_mhz"] + np.arange(htr["nchans"]) * htr["foff_mhz"]
    error = float(np.max(np.abs(expected - observed)))
    if error > 1e-9:
        raise ValueError("frequency centers do not align")
    common_medium = min(medium["ntime"], htr["ntime"] // nt)
    return {"time_group_factor": nt, "frequency_group_factor": nf,
            "maximum_frequency_center_error_mhz": error,
            "common_medium_samples": common_medium,
            "common_htr_samples": common_medium * nt,
            "common_duration_s": common_medium * medium["tsamp_s"],
            "unused_htr_samples": htr["ntime"] - common_medium * nt,
            "unused_htr_duration_s": (htr["ntime"] - common_medium * nt) * htr["tsamp_s"],
            "unused_medium_samples": medium["ntime"] - common_medium}


def integrated_boxes(n, dt, boxes):
    """Mean rectangular signal in each bin, including fractional edge coverage."""
    if n < 1 or not math.isfinite(dt) or dt <= 0:
        raise ValueError("invalid integration grid")
    left = np.arange(n) * dt
    right = (np.arange(n) + 1) * dt
    result = np.zeros(n)
    for start, stop, amplitude in boxes:
        if not all(math.isfinite(v) for v in (start, stop, amplitude)) or not 0 <= start < stop <= n * dt:
            raise ValueError("box outside common support")
        result += amplitude * np.maximum(0., np.minimum(right, stop) - np.maximum(left, start)) / dt
    return result


def time_adapter_check(medium, htr, example, grid):
    start, stop = example["envelope_s"]
    boxes = [(start, stop, example["envelope_amplitude"])]
    width = example["pulse_width_s"]
    boxes += [(t - width / 2, t + width / 2, example["pulse_amplitude"]) for t in example["pulse_times_s"]]
    m = integrated_boxes(grid["common_medium_samples"], medium["tsamp_s"], boxes)
    h = integrated_boxes(grid["common_htr_samples"], htr["tsamp_s"], boxes)
    regrouped = h.reshape(-1, grid["time_group_factor"]).mean(axis=1)
    expected_area = sum((b - a) * amplitude for a, b, amplitude in boxes)
    passed = bool(np.allclose(m, regrouped, rtol=1e-10, atol=1e-10) and
                  math.isclose(float(m.sum() * medium["tsamp_s"]), expected_area, rel_tol=1e-10) and
                  math.isclose(float(h.sum() * htr["tsamp_s"]), expected_area, rel_tol=1e-10))
    return {"passed": passed, "expected_area": expected_area,
            "medium_area": float(m.sum() * medium["tsamp_s"]),
            "htr_area": float(h.sum() * htr["tsamp_s"]),
            "max_regrouping_error": float(np.max(np.abs(m - regrouped))),
            "physical_instrument_response_verified": False}


def quantize(value, low, high):
    if not all(math.isfinite(v) for v in (value, low, high)) or low >= high:
        raise ValueError("invalid quantizer")
    return int(np.clip((value - low) / (high - low) * 255, 0, 255))


def quantization_examples():
    specs = [
        ("unknown_gain", [(100., 0., 255.), (200., 0., 510.)], 1.),
        ("unknown_sub_bin_input", [(100.1, 0., 255.), (100.9, 0., 255.)], .2),
    ]
    results = []
    for name, cases, increment in specs:
        before = [quantize(x, lo, hi) for x, lo, hi in cases]
        after = [quantize(x + increment, lo, hi) for x, lo, hi in cases]
        results.append({"case": name, "inputs_and_limits": cases, "common_increment": increment,
                        "bytes_before": before, "bytes_after": after,
                        "ambiguous_response_demonstrated": before[0] == before[1] and after[0] != after[1]})
    return results


def check_partitions(config):
    groups = [set(config[k]) for k in ("development_labels", "reserved_validation_labels", "excluded_bridge_labels")]
    if any(groups[i] & groups[j] for i in range(3) for j in range(i)):
        raise ValueError("partition overlap")
    by_label = {s["label"]: s for s in config["scans"]}
    if set.union(*groups) != set(by_label):
        raise ValueError("partition does not cover inventory")
    for group in groups[:2]:
        for label in group:
            s = by_label[label]
            if s["role"] == "ON" and not set(s["adjacent_off_labels"]).issubset(group):
                raise ValueError("required OFF control crosses partition")
    return {"scan_groups_disjoint": True, "off_adjacency_complete": True,
            "independent_epochs": False, "historically_blind_medium_data": False}


def match_catalog(catalog, config):
    rows = catalog["data"]
    by_url = {r["url"]: r for r in rows}
    if len(by_url) != len(rows):
        raise ValueError("duplicate catalog URL")
    checked = []
    for scan in config["scans"]:
        for product in ("medium_resolution", "high_time_resolution"):
            frozen = scan[product]
            row = by_url.get(frozen["url"])
            if row is None or row["size"] != frozen["expected_size_bytes"]:
                raise ValueError(f"catalog identity mismatch: {scan['label']} {product}")
            if row["target"].casefold() != scan["expected_source_name"].casefold() or not math.isclose(row["mjd"], scan["expected_tstart_mjd"], rel_tol=0, abs_tol=1e-9):
                raise ValueError(f"catalog source/epoch mismatch: {scan['label']}")
            checked.append({"label": scan["label"], "product": product, "archive_id": row["id"]})
    return {"matched_product_count": len(checked), "matched_products": checked,
            "catalog_entries": len(rows),
            "listed_float_htr_urls": [r["url"] for r in rows if r["url"].endswith('.gpuspec.0001.fil')]}


def network_probe(config, output):
    net = config["network"]
    result = {"checked_utc": datetime.now(timezone.utc).isoformat(), "spectral_body_bytes_read": 0,
              "catalog_url": net["cadence_url"], "head_checks": []}
    try:
        request = Request(net["cadence_url"], headers={"User-Agent": "setisearch-ls4h-preflight/1.0"})
        with urlopen(request, timeout=net["timeout_s"]) as response:
            payload = response.read(net["metadata_byte_limit"] + 1)
            if len(payload) > net["metadata_byte_limit"]:
                raise ValueError("metadata byte cap exceeded")
            result["catalog_http_status"] = response.status
        (output / "cadence_response.json").write_bytes(payload)
        result["catalog_response_sha256"] = hashlib.sha256(payload).hexdigest()
        result["catalog"] = match_catalog(json.loads(payload), config)
    except Exception as exc:
        result["catalog_error"] = str(exc)
    scans = {s["label"]: s for s in config["scans"]}
    for label in net["inferred_float_htr_head_labels"]:
        url = scans[label]["high_time_resolution"]["url"].replace('.gpuspec.8.0001.fil', '.gpuspec.0001.fil')
        record = {"label": label, "inferred_url": url, "method": "HEAD", "body_bytes_read": 0}
        try:
            with urlopen(Request(url, method="HEAD"), timeout=net["timeout_s"]) as response:
                record.update({"http_status": response.status, "content_length": response.headers.get("Content-Length")})
        except HTTPError as exc:
            record.update({"http_status": exc.code, "error": str(exc)})
            exc.close()
        except Exception as exc:
            record["error"] = str(exc)
        result["head_checks"].append(record)
    return result


def main():
    verify_freeze()
    config = json.loads((ROOT / "config/ls4h_transfer_preflight.json").read_text())
    for p, expected in config["input_sha256"].items():
        if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != expected:
            raise ValueError(f"input mismatch: {p}")
    output = ROOT / "results_ls4h_transfer_preflight"
    output.mkdir(exist_ok=False)
    try:
        medium = json.loads((ROOT / 'config/ls4b_lhs1140_x_light_sail.json').read_text())["expected_filterbank_header"]
        htr = json.loads((ROOT / 'config/ls4c_lhs1140_x_htr_followup.json').read_text())["expected_filterbank_header"]
        grid = geometry(medium, htr)
        analytic = time_adapter_check(medium, htr, config["analytic_adapter_example"], grid)
        examples = quantization_examples()
        partitions = check_partitions(config)
        local = json.loads((ROOT / 'results_ls4a_header/preflight.json').read_text())
        headers = next(c for c in local["cadences"] if c["band"] == "X")["headers"]
        header_keys = sorted(set().union(*(set(h["header"]) for h in headers.values())))
        if not analytic["passed"] or not all(x["ambiguous_response_demonstrated"] for x in examples):
            raise ValueError("analytic qualification failed")
        net = network_probe(config, output)
        resources = {}
        for group in ("development_labels", "reserved_validation_labels"):
            resources[group] = sum(s[p]["expected_size_bytes"] for s in config["scans"] if s["label"] in config[group]
                                   for p in ("medium_resolution", "high_time_resolution"))
        result = {"artifact_type": "seti_repeater.ls4h_transfer_preflight_result", "version": 1,
                  "status": "preflight-complete-joint-physical-injections-not-ready",
                  "geometry": grid, "analytic_time_integration": analytic,
                  "quantization_ambiguity_examples": examples, "partitions": partitions,
                  "observed_header_keys": header_keys, "network": net, "future_download_bytes": resources,
                  "identified_file_specific_transfer_calibration": False,
                  "raw_spectral_values_read": False, "measured_background_injections_executed": False,
                  "pipeline_recovery_fraction": None, "historical_candidate_dispositions_changed": False,
                  "blocking_reason": "No identified file-specific pre-quantization transfer model; geometric grouping is not amplitude calibration.",
                  "freeze_sha256": hashlib.sha256((ROOT / 'LS4H_FREEZE.sha256').read_bytes()).hexdigest()}
        result["result_sha256"] = hashlib.sha256(encoded(result)).hexdigest()
        (output / 'preflight.json').write_bytes(encoded(result))
        print(json.dumps({"status": result["status"], "catalog_match_count": net.get('catalog', {}).get('matched_product_count'),
                          "result_sha256": result["result_sha256"]}))
    except Exception as exc:
        (output / 'abort.json').write_bytes(encoded({"status": "aborted", "error": str(exc)}))
        raise


if __name__ == '__main__':
    main()
