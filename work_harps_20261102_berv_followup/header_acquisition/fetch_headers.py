#!/usr/bin/env python3
"""Run the released, bounded header-only batch once; never retrieve spectra."""
import hashlib
import json
import signal
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from header_tools import ADP_RE, HeaderError, check_identity, parse_header_response

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def time_limit(signum, frame):
    raise TimeoutError("Frozen total request time limit reached")


def request_header(job, limits, remaining_bytes):
    start = time.monotonic()
    receipt = {"started_utc": now(), "job_index": job["job_index"], "dp_id": job["dp_id"], "target": job["target"], "url": job["url"], "attempts": 1, "retries": 0, "redirects_followed": 0, "http_status": None, "response_headers": {}, "complete": False, "error": None}
    chunks, size = [], 0
    cap = min(limits["max_response_bytes"], remaining_bytes)
    signal.signal(signal.SIGALRM, time_limit)
    signal.setitimer(signal.ITIMER_REAL, limits["timeout_seconds"])
    try:
        opener = urllib.request.build_opener(NoRedirect())
        request = urllib.request.Request(job["url"], headers={"Accept": "text/plain,text/html", "User-Agent": "SETI-HARPS-header-feasibility/1.0 (public archive metadata)"})
        try:
            response = opener.open(request, timeout=limits["timeout_seconds"])
        except urllib.error.HTTPError as error:
            response = error
        with response:
            receipt["http_status"] = response.status
            receipt["response_headers"] = {key: response.headers.get(key) for key in ("Date", "Content-Type", "Content-Length", "Content-Disposition", "Location", "Last-Modified")}
            while size < cap:
                block = response.read(min(8192, cap - size))
                if not block:
                    receipt["complete"] = True
                    break
                chunks.append(block)
                size += len(block)
            if size >= cap:
                receipt["error"] = "BYTE_CAP_REACHED_RESPONSE_NOT_CONFIRMED_COMPLETE"
            if receipt["http_status"] != 200:
                receipt["error"] = "HTTP_STATUS_" + str(receipt["http_status"])
    except Exception as error:
        receipt["error"] = type(error).__name__ + ": " + str(error)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    body = b"".join(chunks)
    receipt.update({"finished_utc": now(), "elapsed_seconds": time.monotonic() - start, "bytes_saved": len(body), "body_sha256": hashlib.sha256(body).hexdigest(), "effective_byte_cap": cap})
    return body, receipt


def main():
    plan_path = HERE / "PLAN.json"
    plan = json.loads(plan_path.read_text())
    release = json.loads((HERE / "ROOT_RELEASE.json").read_text())
    if release.get("approved") is not True or release.get("plan_sha256") != sha(plan_path):
        raise ValueError("Exact root release absent")
    if release.get("code_hashes") != plan["code_hashes"]:
        raise ValueError("Release code mismatch")
    for name, digest in plan["code_hashes"].items():
        if sha(HERE / name) != digest:
            raise ValueError("Changed code: " + name)
    for item in plan["inputs"]:
        relative = Path(item["path"])
        if relative.is_absolute():
            raise ValueError("Plan input must be repository-relative")
        path = (REPO / relative).resolve()
        path.relative_to(REPO)  # Raises for any path or symlink escaping repo.
        if sha(path) != item["sha256"]:
            raise ValueError("Changed metadata input: " + item["path"])
    jobs, limits = plan["jobs"], plan["limits"]
    if not 0 < len(jobs) <= limits["max_jobs"] <= 24:
        raise ValueError("Job cap invalid")
    for job in jobs:
        expected = "https://archive.eso.org/hdr?" + urllib.parse.urlencode({"DpId": job["dp_id"]})
        if not ADP_RE.fullmatch(job["dp_id"]) or job["url"] != expected:
            raise ValueError("Unexpected endpoint or identifier")
    for target in {job["target"] for job in jobs}:
        if sum(job["target"] == target for job in jobs) > 12:
            raise ValueError("Per-target cap exceeded")
    with (HERE / "REQUEST_STARTED.json").open("x") as handle:
        json.dump({"started_utc": now(), "plan_sha256": sha(plan_path), "root_release_sha256": sha(HERE / "ROOT_RELEASE.json")}, handle)
        handle.write("\n")
    (HERE / "responses").mkdir(exist_ok=True)
    (HERE / "receipts").mkdir(exist_ok=True)
    results, total_bytes, stop_reason = [], 0, None
    for job in jobs:
        result = {key: job[key] for key in ("job_index", "target", "dp_id", "month_number")}
        if stop_reason:
            result.update({"status": "NOT_REQUESTED_BATCH_STOPPED", "reason": stop_reason})
            results.append(result)
            continue
        remaining = limits["max_total_response_bytes"] - total_bytes
        if remaining <= 0:
            stop_reason = "TOTAL_BYTE_CAP"
            result.update({"status": "NOT_REQUESTED_BATCH_STOPPED", "reason": stop_reason})
            results.append(result)
            continue
        stem = job["dp_id"].replace(":", "_")
        body_path = HERE / "responses" / (stem + ".body")
        receipt_path = HERE / "receipts" / (stem + ".json")
        body, receipt = request_header(job, limits, remaining)
        total_bytes += len(body)
        body_path.write_bytes(body)
        receipt["plan_sha256"] = sha(plan_path)
        receipt["code_hashes"] = plan["code_hashes"]
        receipt["body_path"] = str(body_path.relative_to(HERE))
        save(receipt_path, receipt)
        result.update({"body_path": str(body_path.relative_to(HERE)), "body_sha256": sha(body_path), "receipt_path": str(receipt_path.relative_to(HERE)), "receipt_sha256": sha(receipt_path)})
        if receipt["http_status"] != 200 or not receipt["complete"] or receipt["error"]:
            result.update({"status": "REQUEST_FAILED", "reason": receipt["error"] or "INCOMPLETE"})
            if job["job_index"] == 0:
                stop_reason = "CANARY_REQUEST_FAILED"
        else:
            try:
                header, rendering = parse_header_response(body, receipt["response_headers"]["Content-Type"] or "")
                inspection = check_identity(header, job)
                inspection["parser"] = rendering
                result.update({"status": inspection["status"], "inspection": inspection})
                if job["job_index"] == 0 and inspection["status"] != "PASS_RECORDED_BERV":
                    stop_reason = "CANARY_VALIDATION_FAILED"
            except HeaderError as error:
                result.update({"status": "UNRECOGNIZED_HEADER_RESPONSE", "reason": str(error)})
                stop_reason = "HEADER_FORMAT_FAILURE"
        results.append(result)
        save(HERE / "HEADER_RESULTS.json", {"schema": "HARPS_BERV_HEADER_RESULTS_V1", "status": "IN_PROGRESS", "plan_sha256": sha(plan_path), "results": results})
        print(json.dumps({"job_index": job["job_index"], "dp_id": job["dp_id"], "status": result["status"], "bytes": len(body), "stop_reason": stop_reason}), flush=True)
    final = {"schema": "HARPS_BERV_HEADER_RESULTS_V1", "status": "COMPLETE_WITH_STOP" if stop_reason else "COMPLETE", "completed_utc": now(), "plan_sha256": sha(plan_path), "root_release_sha256": sha(HERE / "ROOT_RELEASE.json"), "code_hashes": plan["code_hashes"], "requests_attempted": sum("receipt_path" in row for row in results), "response_bytes": total_bytes, "stop_reason": stop_reason, "results": results, "spectral_arrays_requested_or_read": False}
    save(HERE / "HEADER_RESULTS.json", final)
    print(json.dumps({key: final[key] for key in ("status", "requests_attempted", "response_bytes", "stop_reason")}, indent=2))


if __name__ == "__main__":
    main()
