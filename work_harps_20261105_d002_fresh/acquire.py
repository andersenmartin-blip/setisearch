#!/usr/bin/env python3
"""Acquire the fixed D002 cohort; inspect headers before spectral array access."""
import concurrent.futures
import json
import math
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request

from common import BASE, HERE, ROOT, csvout, dump, gates, load_module, now, sha, table

LOCK = threading.Lock()
CHARGED = 0
RETURNED = 0
STARTED = 0.0


def fetch(row, plan, inspector, upstream, out):
    global CHARGED, RETURNED
    receipt = dict(dp_id=row["dp_id"], target=row["canonical_target"], role=row["role"],
                   started_utc=now(), source_url=row["source_url"], attempts=[], array_values_inspected=False)
    if row["metadata_status"] != "PASS_FIXED_METADATA":
        receipt.update(status="EXCLUDED_FIXED_METADATA", header_status="NOT_ADMITTED")
        return receipt
    folder = "control" if row["role"] == "fresh_control_only" else "main"
    relative = "data/" + folder + "/" + row["dp_id"].replace(":", "_") + ".fits"
    path = HERE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    assert not path.exists()
    receipt["relative_path"] = relative
    for timeout in plan["attempt_timeouts_seconds"]:
        attempt = dict(started_utc=now(), timeout_seconds=timeout)
        if time.monotonic() - STARTED > plan["maximum_start_wall_seconds"]:
            receipt["status"] = "NOT_RUN_WALL_BOUND"
            break
        with LOCK:
            if CHARGED + plan["per_file_byte_cap"] > plan["conservative_byte_cap"]:
                receipt["status"] = "NOT_RUN_BYTE_BOUND"
                break
            CHARGED += plan["per_file_byte_cap"]
        started = time.monotonic()
        try:
            assert row["source_url"] == "https://dataportal.eso.org/dataPortal/file/" + row["dp_id"]
            request = urllib.request.Request(row["source_url"], headers={"User-Agent":"SETI-HARPS-reproducible-pilot/1.0"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                attempt.update(http_status=response.status, final_url=response.url,
                               content_length=response.headers.get("Content-Length"),
                               content_type=response.headers.get("Content-Type"))
                data = response.read(plan["per_file_byte_cap"] + 1)
            with LOCK:
                RETURNED += len(data)
            attempt["returned_payload_bytes"] = len(data)
            assert len(data) <= plan["per_file_byte_cap"]
            assert data.startswith(b"SIMPLE  ") and len(data) % 2880 == 0
            assert attempt["content_length"] is None or int(attempt["content_length"]) == len(data)
            path.write_bytes(data)
            receipt.update(bytes=len(data), sha256=sha(path), status="DOWNLOADED")
            checked = inspector.inspect(path, row, upstream)
            p, e = checked["primary_header"], checked["extension_header"]
            checks = checked["checks"]
            checks.update(raw_exact_fixed_metadata=checked["raw_progenitor_ids"] == [row["raw_progenitor_id"]],
                          barycentric=p.get("SPECSYS") == "BARYCENT", air_wavelength=e.get("TUCD1") == "em.wl;obs.atmos",
                          wavelength_angstrom=str(e.get("TUNIT1", "")).lower() == "angstrom",
                          flux_adu=str(e.get("TUNIT2", "")).lower() == "adu",
                          nominal_grid_step=abs(float(p.get("SPEC_BIN", 0)) * 10 - .01) < 1e-10,
                          nominal_resolving_power=abs(float(p.get("SPEC_RES", 0)) - 115000) < 1,
                          single_exposure=p.get("NCOMBINE") == 1,
                          finite_berv=math.isfinite(float(p.get("HIERARCH ESO DRS BERV", float("nan")))))
            checked["header_status"] = "PASS_METADATA_ONLY" if all(checks.values()) else "EXCLUDED_NO_REPLACEMENT"
            receipt.update(checked)
            receipt["physical_identity_scope"] = "Catalogue label and same-observation header/pointing consistency; no new independent Gaia identity confirmation."
            attempt["outcome"] = "SUCCESS"
            receipt["attempts"].append(dict(attempt, elapsed_seconds=time.monotonic() - started))
            break
        except Exception as exc:
            attempt.update(outcome="FAILED", error_type=type(exc).__name__, error=str(exc), elapsed_seconds=time.monotonic() - started)
            receipt["attempts"].append(attempt)
            receipt["status"] = "FAILED"
            if path.exists():
                receipt.update(status="DOWNLOADED_HEADER_REVIEW_FAILED", header_status="EXCLUDED_NO_REPLACEMENT")
                break
            if isinstance(exc, urllib.error.HTTPError) and exc.code in (401,403,404):
                break
    receipt["finished_utc"] = now()
    dump(out / "receipts" / (row["dp_id"].replace(":", "_") + ".json"), receipt)
    print(json.dumps({k:receipt.get(k) for k in ("dp_id","role","status","header_status")}), flush=True)
    return receipt


def main():
    global STARTED
    freeze = gates()
    out = HERE / "acquisition"
    out.mkdir(exist_ok=False)
    (out / "receipts").mkdir()
    selected = table(HERE / "metadata/VERIFIED_COHORT54.csv")
    inspector = load_module("d002_header_only", BASE / "acquisition/download_selected.py")
    upstream = json.loads((BASE / "literature/UPSTREAM_REFERENCED_IDS.json").read_text())
    STARTED = time.monotonic()
    # Cohort ordering places the four controls before the fifty main inputs.
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(lambda row:fetch(row,freeze["acquisition"],inspector,upstream,out), selected))
    dump(out / "MANIFEST.json", records)
    summary = dict(status="COMPLETE_BOUNDED_ACQUISITION", started_files=54,
                   admitted_headers=sum(r.get("header_status") == "PASS_METADATA_ONLY" for r in records),
                   conservative_charged_bytes=CHARGED, completed_response_bytes=RETURNED,
                   accounting="Every attempt charged its full8MB reservation, including read errors; completed bodies also measured. HTTP/TLS overhead not measured.",
                   failed_inputs=[r["dp_id"] for r in records if r.get("header_status") != "PASS_METADATA_ONLY"],
                   science_arrays_opened=0, no_substitutions=True, elapsed_seconds=time.monotonic()-STARTED,
                   method_freeze_sha256=sha(HERE / "FREEZE.json"))
    dump(out / "SUMMARY.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
