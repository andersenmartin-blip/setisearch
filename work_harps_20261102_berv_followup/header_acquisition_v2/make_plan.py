#!/usr/bin/env python3
"""Freeze metadata-only month-of-year choices; never request target headers."""
import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from header_tools import ADP_RE, RAW_RE, mjd_to_datetime

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TARGET_ORDER = ["HD122640", "HD135204"]
CODE_FILES = ["header_tools.py", "make_plan.py", "fetch_headers.py", "select_extremes.py"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select(candidates):
    grouped = {}
    for row in candidates:
        if row["status"] != "METADATA_CANDIDATE_PENDING_HEADER_IDENTITY_BERV" or row.get("reasons"):
            continue
        if row["target"] not in TARGET_ORDER:
            raise ValueError("Unexpected target")
        if not ADP_RE.fullmatch(row["dp_id"]):
            raise ValueError("Invalid ADP identifier")
        if len(row["source_file_ids"]) != 1 or not RAW_RE.fullmatch(row["source_file_ids"][0]):
            raise ValueError("Invalid single raw provenance")
        month = mjd_to_datetime(row["metadata"]["t_min"]).month
        key = row["target"], month
        rank = -float(row["metadata"]["t_min"]), row["dp_id"]
        if key not in grouped or rank < grouped[key][0]:
            grouped[key] = rank, row
    output = []
    for target in TARGET_ORDER:
        for month in range(1, 13):
            if (target, month) not in grouped:
                continue
            row = grouped[target, month][1]
            output.append({
                "job_index": len(output), "target": target, "month_number": month,
                "dp_id": row["dp_id"], "source_file_ids": row["source_file_ids"],
                "metadata": row["metadata"],
                "url": "https://archive.eso.org/hdr?DpId=" + row["dp_id"],
            })
    if len({row["dp_id"] for row in output}) != len(output):
        raise ValueError("Repeated ADP identifier")
    if len({row["source_file_ids"][0] for row in output}) != len(output):
        raise ValueError("Repeated raw progenitor")
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--metadata-summary", type=Path, required=True)
    parser.add_argument("--berv-coverage", type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads(args.metadata_summary.read_text())
    if summary.get("status") != "COMPLETE_BOUNDED_METADATA" or summary.get("target_requests") != 2 or summary.get("request_statuses") != ["COMPLETE_METADATA_RESPONSE", "COMPLETE_METADATA_RESPONSE"]:
        raise ValueError("Both explicitly selected metadata queries must have completed successfully")
    candidates = json.loads(args.candidates.read_text())
    if not isinstance(candidates, list):
        raise ValueError("Candidate input must be the declared list schema")
    jobs = select(candidates)
    if not jobs:
        raise ValueError("No eligible header jobs")
    existing = list(csv.DictReader(args.berv_coverage.open()))
    benchmark = {}
    for target in TARGET_ORDER:
        rows = [row for row in existing if row["target"] == target and row["scope"] == "all_existing300"]
        if len(rows) != 1:
            raise ValueError("Missing/invalid existing BERV benchmark")
        row = rows[0]
        low, high = float(row["berv_min_km_s"]), float(row["berv_max_km_s"])
        if not -100 <= low <= high <= 100:
            raise ValueError("Invalid existing BERV limits")
        benchmark[target] = {"scope": "all_existing300", "existing_exposures": int(row["exposures"]), "minimum_berv_km_s": low, "maximum_berv_km_s": high, "span_km_s": high - low}
    plan = {
        "schema": "HARPS_BERV_HEADER_PLAN_V1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FROZEN_IDS_PENDING_ROOT_RELEASE",
        "selection_rule": "For each target and calendar month NUMBER 1..12 across ALL years, latest eligible t_min; ties lexicographically smallest dp_id. No flux/BERV used. Missing months remain absent.",
        "request_order": "HD122640 then HD135204, month number ascending; first job is canary.",
        "scope": "Additional archival follow-up outside the original 300-spectrum survey; no prior result or threshold changes.",
        "inputs": [{"path": path.resolve().relative_to(REPO).as_posix(), "sha256": sha(path)} for path in (args.candidates, args.targets, args.metadata_summary, args.berv_coverage)],
        "code_hashes": {name: sha(HERE / name) for name in CODE_FILES},
        "jobs": jobs,
        "limits": {"max_jobs": 24, "max_jobs_per_target": 12, "timeout_seconds": 30, "max_response_bytes": 524288, "max_total_response_bytes": 12582912, "attempts_per_job": 1, "retries": 0, "redirects": 0},
        "canary_rule": "Unexpected format or any validation failure on first job stops all remaining jobs. Any later format failure also stops remaining jobs; ordinary identity/BERV failures are retained as exclusions.",
        "cap_rule": "Never read beyond the byte cap. A response reaching the cap is incomplete even if its true length might equal the cap; no overflow probe and no spectrum fallback.",
        "identity_tolerances": {"mjd_days": 1e-7, "date_mjd_seconds": .02, "exposure_seconds": .02, "position_vs_metadata_arcsec": 1},
        "spectral_arrays_allowed": False,
        "primary_only_parser": True,
        "mode_eligibility": "SPEC_RES=115000 required; HEFS ST=true excluded as EGGS; HEFS ST=false supports high-resolution mode regardless of INS MODE string. Missing/nonboolean HEFS remains pending and is excluded from automatic extrema selection.",
        "berv_sanity_gate_km_s": 100,
        "existing_berv_benchmark": benchmark,
        "extreme_selection_rule": "HD122640 then HD135204; minimum then maximum verified BERV among PASS_RECORDED_BERV headers; each equal-BERV tie lexicographically smallest dp_id; identical selected dp_id deduplicated. Propose payloads only for targets whose combined existing+passing-new span exceeds c/R. No outcome-driven sample expansion.",
        "payload_readiness_gate": {"comparison": "strictly greater than", "combined_span_km_s_threshold": 299792.458 / 115000, "meaning": "Descriptive planning displacement only, not statistical power, origin classification, or adequacy."},
        "span_diagnostics": "Report existing, new, and combined BERV span, combined span increase, and span/(299792.458/115000). These are descriptive displacement scales, not origin or adequacy claims.",
        "representation_compatibility": "Must still verify full payload headers before any array access; header BERV selection alone is not spectrum compatibility.",
        "required_release": {"filename": "ROOT_RELEASE.json", "approved": True, "plan_sha256": "exact SHA256 of PLAN.json", "code_hashes": "exact match to plan code_hashes"},
    }
    with (HERE / "PLAN.json").open("x") as handle:
        json.dump(plan, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"jobs": len(jobs), "plan_sha256": sha(HERE / "PLAN.json")}, indent=2))


if __name__ == "__main__":
    main()
