#!/usr/bin/env python3
"""Propose min/max recorded-BERV epochs; does not authorize payload retrieval."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    plan = json.loads((HERE / "PLAN.json").read_text())
    result_path = HERE / "HEADER_RESULTS.json"
    result = json.loads(result_path.read_text())
    if result["plan_sha256"] != sha(HERE / "PLAN.json") or result["status"] not in {"COMPLETE", "COMPLETE_WITH_STOP"}:
        raise ValueError("Header results are not final and plan matched")
    if result["code_hashes"] != plan["code_hashes"]:
        raise ValueError("Header result code hashes differ from plan")
    for name, digest in plan["code_hashes"].items():
        if sha(HERE / name) != digest:
            raise ValueError("Changed frozen code: " + name)
    jobs = {row["job_index"]: row for row in plan["jobs"]}
    indices = [row["job_index"] for row in result["results"]]
    if len(set(indices)) != len(indices) or set(indices) != set(jobs):
        raise ValueError("Header results do not account for each planned job exactly once")
    for row in result["results"]:
        job = jobs[row["job_index"]]
        if row["dp_id"] != job["dp_id"] or row["target"] != job["target"]:
            raise ValueError("Header result identity differs from planned job")
    selected, target_summary = [], {}
    for target in ("HD122640", "HD135204"):
        rows = [row for row in result["results"] if row["target"] == target and row["status"] == "PASS_RECORDED_BERV"]
        rows.sort(key=lambda row: (row["inspection"]["berv_km_s"], row["dp_id"]))
        chosen = []
        if rows:
            low = rows[0]
            maximum = rows[-1]["inspection"]["berv_km_s"]
            high = min((row for row in rows if row["inspection"]["berv_km_s"] == maximum), key=lambda row: row["dp_id"])
            chosen = [low] if low["dp_id"] == high["dp_id"] else [low, high]
        target_summary[target] = {"verified_headers": len(rows), "candidate_extreme_epochs": len(chosen), "candidate_extreme_dp_ids": [row["dp_id"] for row in chosen], "recorded_berv_span_km_s": (rows[-1]["inspection"]["berv_km_s"] - rows[0]["inspection"]["berv_km_s"]) if rows else None}
        old = plan["existing_berv_benchmark"][target]
        summary = target_summary[target]
        summary["existing_berv_benchmark"] = old
        combined = old["span_km_s"]
        if rows:
            low_value, high_value = rows[0]["inspection"]["berv_km_s"], rows[-1]["inspection"]["berv_km_s"]
            combined = max(old["maximum_berv_km_s"], high_value) - min(old["minimum_berv_km_s"], low_value)
            summary.update({"combined_span_km_s": combined, "combined_span_increase_km_s": combined - old["span_km_s"], "extends_existing_range": low_value < old["minimum_berv_km_s"] or high_value > old["maximum_berv_km_s"], "new_span_resolution_elements_R115000": (high_value - low_value) / (299792.458 / 115000), "combined_span_resolution_elements_R115000": combined / (299792.458 / 115000)})
        else:
            summary.update({"combined_span_km_s": combined, "combined_span_increase_km_s": 0, "extends_existing_range": False, "new_span_resolution_elements_R115000": None, "combined_span_resolution_elements_R115000": combined / (299792.458 / 115000)})
        ready = bool(rows) and combined > plan["payload_readiness_gate"]["combined_span_km_s_threshold"]
        summary["payload_readiness_gate_passed"] = ready
        summary["selected_epochs"] = len(chosen) if ready else 0
        summary["no_origin_or_completeness_claim"] = True
        if not ready:
            continue
        for row in chosen:
            for key in ("body", "receipt"):
                if sha(HERE / row[key + "_path"]) != row[key + "_sha256"]:
                    raise ValueError("Changed header evidence")
            job = jobs[row["job_index"]]
            selected.append({"dp_id": row["dp_id"], "target": target, "berv_km_s": row["inspection"]["berv_km_s"], "header_result_job_index": row["job_index"], "header_body_path": row["body_path"], "header_body_sha256": row["body_sha256"], "header_receipt_path": row["receipt_path"], "header_receipt_sha256": row["receipt_sha256"], "source_file_ids": job["source_file_ids"], "metadata": job["metadata"], "primary_header": row["inspection"]["primary_header"]})
    if len({row["source_file_ids"][0] for row in selected}) != len(selected):
        raise ValueError("Selected raw progenitors not unique")
    output = {"schema": "HARPS_BERV_EXTREME_SELECTION_V1", "status": "PROPOSED_PENDING_SEPARATE_PAYLOAD_RELEASE", "selection_rule": plan["extreme_selection_rule"], "payload_readiness_gate": plan["payload_readiness_gate"], "header_results_sha256": sha(result_path), "header_plan_sha256": sha(HERE / "PLAN.json"), "header_batch_status": result["status"], "all_planned_jobs_attempted": all("receipt_path" in row for row in result["results"]), "header_sampling_is_partial": result["status"] == "COMPLETE_WITH_STOP" or any(row["status"] != "PASS_RECORDED_BERV" for row in result["results"]), "selected": selected, "target_summary": target_summary, "spectral_payload_acquisition_authorized": False, "representation_compatibility": "Provisional until independent payload header checks before arrays; pipeline/version changes must be flagged."}
    (HERE / "EXTREME_SELECTION.json").write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps(target_summary, indent=2))


if __name__ == "__main__":
    main()
