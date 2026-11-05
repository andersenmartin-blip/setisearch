#!/usr/bin/env python3
"""One bounded metadata-only check of the already fixed D001 fresh cohort."""
import concurrent.futures
import csv
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
D001 = ROOT / "work_seti_20261105_d001_delivery"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def table(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def query(out, name, adql):
    url = "https://archive.eso.org/tap_obs/sync?" + urllib.parse.urlencode(
        dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=adql, MAXREC=1000))
    receipt = dict(url=url, adql=adql, max_response_bytes=1_000_000,
                   started_utc=dt.datetime.now(dt.timezone.utc).isoformat(), attempts=1,
                   timeout_seconds=45, science_arrays_read=0)
    started = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=45) as response:
            data = response.read(1_000_001)
            receipt.update(http_status=response.status, content_type=response.headers.get("Content-Type"))
        (out / (name + ".response")).write_bytes(data)
        assert len(data) <= 1_000_000, "Response byte cap exceeded"
        assert not data.lstrip().startswith(b"<"), "Non-CSV service response"
        values = list(csv.DictReader(io.StringIO(data.decode())))
        assert len(values) < 1000, "Possible truncated metadata response"
        (out / (name + ".csv")).write_bytes(data)
        receipt.update(status="COMPLETE", bytes=len(data), rows=len(values), sha256=hashlib.sha256(data).hexdigest())
    except Exception as exc:
        receipt.update(status="FAILED_NO_RETRY", error_type=type(exc).__name__, error=str(exc))
    receipt["elapsed_seconds"] = time.monotonic() - started
    dump(out / (name + "_QUERY.json"), receipt)
    print(json.dumps(dict(name=name, status=receipt["status"], rows=receipt.get("rows"))), flush=True)
    return receipt


def main():
    plan = json.loads((HERE / "METADATA_PLAN.json").read_text())
    for name, expected in plan["source_hashes"].items():
        assert sha(ROOT / name) == expected, name
    assert sha(Path(__file__)) == plan["code_sha256"]
    selected = table(D001 / "results/FRESH_METADATA_COHORT54.csv")
    assert len(selected) == len({r["dp_id"] for r in selected}) == 54
    out = HERE / "metadata"
    out.mkdir(exist_ok=False)
    ids = ",".join("'" + r["dp_id"] + "'" for r in selected)
    tasks = [
        ("RAW_PROVENANCE", "SELECT f.product_id,f.archive_id,f.internal_file_id,p.source_file FROM phase3v2.product_files AS f JOIN phase3v2.provenance AS p ON f.internal_file_id=p.product_file WHERE f.product_id IN (" + ids + ") AND f.archive_id=f.product_id"),
        ("PRODUCT_METADATA", "SELECT product_id,archive_id,extension,eso_category,original_filename,access_url,access_estsize FROM phase3v2.product_files WHERE product_id IN (" + ids + ")"),
        ("CURRENT_OBSCORE", "SELECT dp_id,target_name,s_ra,s_dec,instrument_name,t_min,t_max,t_exptime,em_min,em_max,em_res_power,snr,n_obs,multi_ob,obs_release_date,access_url,access_estsize FROM ivoa.ObsCore WHERE dp_id IN (" + ids + ")"),
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        receipts = list(pool.map(lambda task: query(out, *task), tasks))
    dump(out / "QUERY_SUMMARY.json", dict(queries=receipts, science_arrays_opened=0,
                                         total_successful_response_bytes=sum(r.get("bytes", 0) for r in receipts)))
    assert all(r["status"] == "COMPLETE" for r in receipts), "Metadata route blocked; preserve failures, do not replace cohort"
    current = table(out / "CURRENT_OBSCORE.csv")
    provenance = table(out / "RAW_PROVENANCE.csv")
    products = table(out / "PRODUCT_METADATA.csv")
    prior = table(D001 / "results/PRIOR309_EXCLUSIONS.csv")
    prior_ids = {r["dp_id"] for r in prior}
    prior_raw = {s for r in prior for s in json.loads(r["raw_ids"])}
    upstream = json.loads((ROOT / "work_harps_20261101/literature/UPSTREAM_REFERENCED_IDS.json").read_text())
    checks, enriched = [], []
    epoch = dt.datetime(1858, 11, 17, tzinfo=dt.timezone.utc)
    selected_raw = set()
    for row in selected:
        dp = row["dp_id"]
        c = [r for r in current if r["dp_id"] == dp]
        p = [r for r in provenance if r["product_id"] == dp]
        science = [r for r in products if r["product_id"] == dp and r["archive_id"] == dp and r["extension"] == "FITS" and r["eso_category"] == "SCIENCE.SPECTRUM"]
        ancillary = [r for r in products if r["product_id"] == dp and r["extension"] == "TAR" and r["eso_category"] == "ANCILLARY.HARPSTAR"]
        tests = dict(unique_current_row=len(c) == 1, unique_provenance=len(p) == 1,
                     unique_science_product=len(science) == 1, unique_ancillary=len(ancillary) == 1,
                     no_prior_or_pinned_adp_overlap=dp not in prior_ids and dp not in upstream["ADP"])
        mismatches = []
        if len(c) == 1:
            for key, value in c[0].items():
                if key not in row:
                    continue
                equal = value == row[key]
                if not equal:
                    try:
                        equal = float(value) == float(row[key])
                    except ValueError:
                        pass
                if not equal:
                    mismatches.append(dict(field=key, fixed=row[key], current=value))
        tests["current_metadata_unchanged"] = len(c) == 1 and not mismatches
        raw = p[0]["source_file"] if len(p) == 1 else ""
        tests["valid_raw_id"] = bool(re.fullmatch(r"HARPS\.\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}", raw))
        tests["no_prior_or_pinned_raw_overlap"] = raw not in prior_raw and raw not in upstream["HARPS"]
        tests["unique_raw_within_selected"] = bool(raw) and raw not in selected_raw
        selected_raw.add(raw)
        offset = None
        if tests["valid_raw_id"]:
            date = dt.datetime.fromisoformat(raw[len("HARPS."):]).replace(tzinfo=dt.timezone.utc)
            offset = ((date - epoch).total_seconds() / 86400 - float(row["t_min"])) * 86400
        tests["raw_start_matches_within_0p01s"] = offset is not None and abs(offset) < .01
        accepted = all(tests.values())
        checks.append(dict(dp_id=dp, target=row["canonical_target"], role=row["role"],
                           status="PASS_FIXED_METADATA" if accepted else "EXCLUDED_NO_REPLACEMENT",
                           checks=tests, current_metadata_mismatches=mismatches, raw_id=raw,
                           raw_start_minus_fixed_metadata_seconds=offset))
        enriched.append(dict(row, raw_progenitor_id=raw,
                             source_url=science[0]["access_url"] if len(science) == 1 else "",
                             ancillary_archive_id=ancillary[0]["archive_id"] if len(ancillary) == 1 else "",
                             metadata_status=checks[-1]["status"]))
    with (out / "VERIFIED_COHORT54.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(enriched[0]))
        writer.writeheader()
        writer.writerows(enriched)
    dump(out / "VERIFICATION.json", dict(status="PASS_ALL_FIXED_METADATA" if all(all(r["checks"].values()) for r in checks) else "PARTIAL_FIXED_COHORT_WITH_EXCLUSIONS",
                                         selected=54, admitted=sum(all(r["checks"].values()) for r in checks),
                                         checks=checks, science_files_downloaded=0, science_arrays_read=0,
                                         candidate_replacement=False, code_sha256=sha(Path(__file__)),
                                         source_hashes={str(p.relative_to(ROOT)):sha(p) for p in sorted(out.iterdir()) if p.is_file()}))
    print(json.dumps(dict(selected=54, admitted=sum(all(r["checks"].values()) for r in checks), science_values_read=0)), flush=True)


if __name__ == "__main__":
    main()
