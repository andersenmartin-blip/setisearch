#!/usr/bin/env python3
"""Audit retained Voyager output without replaying the failed reference run."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def parse_dat(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) != 12:
            raise ValueError("unexpected DAT row width")
        rows.append({"top_hit": int(fields[0]), "drift_hz_s": float(fields[1]),
                     "snr": float(fields[2]), "frequency_mhz": float(fields[3]),
                     "raw": line})
    return rows


def verify_manifest(root: Path) -> int:
    count = 0
    for line in (root / "SHA256SUMS").read_text().splitlines():
        digest, relative = line.split("  ", 1)
        body = (root / relative).read_bytes()
        if hashlib.sha256(body).hexdigest() != digest:
            raise ValueError(f"manifest mismatch: {relative}")
        count += 1
    return count


def np_isclose_scalar(actual: float, expected: float, *, rtol: float = 1e-5,
                      atol: float = 1e-3) -> bool:
    """The finite-scalar rule used by numpy.isclose in the pinned upstream test."""
    return abs(actual - expected) <= atol + rtol * abs(expected)


def audit(root: Path, config_path: Path) -> dict:
    manifest_members = verify_manifest(root)
    failure = json.loads((root / "FAILURE.json").read_text())
    status = json.loads((root / "RUN_STATUS.json").read_text())
    config = json.loads(config_path.read_text())
    rows = parse_dat(root / config["source"]["expected_filename"].replace(".h5", ".dat"))
    expected = config["search"]["expected_reference_hits"]
    if len(rows) != len(expected):
        raise ValueError("retained row count differs from frozen expected-hit count")

    comparisons = []
    for row, target in zip(rows, expected):
        frequency_delta = row["frequency_mhz"] - target["frequency_mhz"]
        snr_delta = row["snr"] - target["snr"]
        comparisons.append({
            "top_hit": row["top_hit"],
            "frequency_mhz": row["frequency_mhz"],
            "expected_frequency_mhz": target["frequency_mhz"],
            "frequency_delta_mhz": frequency_delta,
            "snr": row["snr"],
            "expected_snr": target["snr"],
            "snr_delta": snr_delta,
            "original_absolute_snr_gate_pass": abs(snr_delta) <= config["search"]["snr_tolerance"],
            "upstream_np_isclose_frequency_pass": np_isclose_scalar(
                row["frequency_mhz"], target["frequency_mhz"]),
            "upstream_np_isclose_snr_pass": np_isclose_scalar(row["snr"], target["snr"]),
        })

    return {
        "schema": "radio-reference-voyager-posthoc-review-v1",
        "status": "REVIEW_COMPLETE_ORIGINAL_RUN_REMAINS_FAILED_CLOSED",
        "original_run_id": status["run_id"],
        "original_execution_commit": status["execution_commit"],
        "original_execution_outcome": status["execution_outcome"],
        "original_scientific_status": status["scientific_status"],
        "original_error": failure["error"],
        "retained_manifest_members_verified": manifest_members,
        "retained_dat_rows": len(rows),
        "comparisons": comparisons,
        "original_absolute_snr_gate_failures": sum(
            not item["original_absolute_snr_gate_pass"] for item in comparisons),
        "upstream_np_isclose_frequency_failures": sum(
            not item["upstream_np_isclose_frequency_pass"] for item in comparisons),
        "upstream_np_isclose_snr_failures": sum(
            not item["upstream_np_isclose_snr_pass"] for item in comparisons),
        "upstream_test_source": {
            "repository": "UCBerkeleySETI/turbo_seti",
            "commit": "7d9b4fde9bc98d834dc11cfc0acd2380e6676f0e",
            "path": "test/test_turbo_seti.py",
            "blob_sha": "475e6d7ac728bd6ab3fd65bc8c95c1d91714394a",
            "rule": "numpy.isclose(actual, expected, atol=0.001) with default rtol=1e-5",
        },
        "source_sha256_recorded": False,
        "source_bytes_recorded": False,
        "waterfall_recorded": False,
        "analysis_replayed": False,
        "pilot_spectra_opened": False,
        "scientific_claim": False,
        "authority_change": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root, args.config)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"],
                      "original_gate_failures": result["original_absolute_snr_gate_failures"],
                      "upstream_semantics_failures": result["upstream_np_isclose_snr_failures"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
