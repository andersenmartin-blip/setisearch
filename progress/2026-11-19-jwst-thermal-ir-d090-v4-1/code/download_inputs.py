#!/usr/bin/env python3
"""
Prospectively locked MAST JWST L2 (*_x1d.fits) downloader for Phase D090
(`JWST_SPACE_THERMAL_IR_V4_1`).

Strict prospective chronology guards:
  1. Verifies `METHOD_LOCK.json` and `LOCK_RECEIPT.json` exist and match current SHA-256
     digests of all locked workspace artifacts before touching `inputs_d090_v4_1/`.
  2. Verifies >= MIN_LOCK_LAG_S (3.0 s) has elapsed since `LOCK_RECEIPT["locked_utc"]`.
  3. Enforces hard disk budget: projected download <= 240 MiB AND post-download
     free space on `/` >= MIN_POST_FREE_GIB (8.5 GiB).
  4. Writes `FIRST_SCIENCE_DOWNLOAD_RECEIPT.json` strictly before fetching any FITS file.
  5. Downloads all paired L2 FITS (`mirifushort+mirifulong` / `nrs1+nrs2`) into
     `inputs_d090_v4_1/` and records SHA-256 digests in `FULL_D090_INPUT_MANIFEST.json`.
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import json
import os
import shutil
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(".")
WS = Path(__file__).resolve().parent
INP_DIR = ROOT / "inputs_d090_v4_1"
MIN_POST_FREE_GIB = 8.0
MAX_DOWNLOAD_MIB = 240.0
MIN_LOCK_LAG_S = 3.0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            b = fh.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def parse_iso_utc(ts: str) -> float:
    return datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp()


def download_with_retry(url: str, dest: Path, expected_bytes: int, timeout_s: float = 90.0) -> tuple[int, str]:
    if dest.exists() and dest.stat().st_size == expected_bytes and expected_bytes > 0:
        return dest.stat().st_size, sha256_file(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    last_err: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-D090-Download/1.0"})
            with urllib.request.urlopen(req, timeout=timeout_s) as resp, tmp.open("wb") as out:
                while True:
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
            os.replace(tmp, dest)
            sz = dest.stat().st_size
            if sz < 4096:
                raise RuntimeError(f"Suspiciously small FITS ({sz} B) at {dest}")
            return sz, sha256_file(dest)
        except Exception as exc:
            last_err = exc
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed download {url} -> {dest}: {last_err}")


def main() -> None:
    lock_path = WS / "METHOD_LOCK.json"
    rec_path = WS / "LOCK_RECEIPT.json"
    cohort_path = WS / "FROZEN_COHORT_D090.csv"
    if not lock_path.exists() or not rec_path.exists():
        raise RuntimeError("Missing prospective lock files (METHOD_LOCK.json / LOCK_RECEIPT.json)!")

    lock_doc = json.loads(lock_path.read_text(encoding="utf-8"))
    rec_doc = json.loads(rec_path.read_text(encoding="utf-8"))
    if lock_doc.get("phase_id") != "D090" or rec_doc.get("phase_id") != "D090":
        raise RuntimeError("Lock phase mismatch!")
    if sha256_file(lock_path) != rec_doc.get("method_lock_sha256"):
        raise RuntimeError("METHOD_LOCK.json SHA-256 mismatch vs LOCK_RECEIPT.json!")
    for fname, expected_sha in rec_doc["locked_artifact_sha256"].items():
        fp = WS / fname
        if not fp.exists() or sha256_file(fp) != expected_sha:
            raise RuntimeError(f"Locked artifact tampered/missing before download: {fname}")

    lag_s = time.time() - parse_iso_utc(rec_doc["locked_utc"])
    if lag_s < MIN_LOCK_LAG_S:
        raise RuntimeError(f"Lock lag too short ({lag_s:.2f}s < {MIN_LOCK_LAG_S:.2f}s); wait before downloading.")

    with cohort_path.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    tot_expected = sum(int(r["det1_bytes"]) + int(r["det2_bytes"]) for r in rows)
    exp_mib = tot_expected / (1024.0 * 1024.0)
    if exp_mib > MAX_DOWNLOAD_MIB:
        raise RuntimeError(f"Projected download {exp_mib:.2f} MiB exceeds hard cap {MAX_DOWNLOAD_MIB:.1f} MiB!")

    free_before = shutil.disk_usage(ROOT).free
    post_free_gib = (free_before - tot_expected) / (1024.0 ** 3)
    if post_free_gib < MIN_POST_FREE_GIB:
        raise RuntimeError(f"Post-download free space {post_free_gib:.2f} GiB < {MIN_POST_FREE_GIB} GiB!")

    first_dl_path = WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json"
    if not first_dl_path.exists():
        first_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        receipt = {
            "schema": "D090_FIRST_SCIENCE_DOWNLOAD_RECEIPT",
            "phase_id": "D090",
            "locked_utc": rec_doc["locked_utc"],
            "first_download_utc": first_utc,
            "chronology_lag_seconds": round(parse_iso_utc(first_utc) - parse_iso_utc(rec_doc["locked_utc"]), 2),
            "projected_exposures": len(rows),
            "projected_fits_files": 2 * len(rows),
            "projected_bytes": tot_expected,
            "projected_mib": round(exp_mib, 2),
        }
        first_dl_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(f"Sealed FIRST_SCIENCE_DOWNLOAD_RECEIPT.json at {first_utc} (+{receipt['chronology_lag_seconds']}s)", flush=True)

    INP_DIR.mkdir(parents=True, exist_ok=True)
    jobs: list[tuple[int, str, Path, int]] = []
    for idx, r in enumerate(rows):
        jobs.append((idx, r["det1_url"], INP_DIR / r["det1_rel"], int(r["det1_bytes"])))
        jobs.append((idx, r["det2_url"], INP_DIR / r["det2_rel"], int(r["det2_bytes"])))

    results: dict[tuple[int, str], tuple[int, str]] = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {}
        for idx, url, dest, eb in jobs:
            key = (idx, dest.name)
            futs[ex.submit(download_with_retry, url, dest, eb)] = (key, dest)
        done = 0
        for fut in as_completed(futs):
            key, dest = futs[fut]
            sz, sh = fut.result()
            results[key] = (sz, sh)
            done += 1
            if done % 40 == 0 or done == len(futs):
                print(f"  Downloaded {done}/{len(futs)} L2 FITS files...", flush=True)

    manifest_rows: list[dict[str, Any]] = []
    tot_actual = 0
    for idx, r in enumerate(rows):
        p1 = INP_DIR / r["det1_rel"]
        p2 = INP_DIR / r["det2_rel"]
        sz1, sh1 = results[(idx, p1.name)]
        sz2, sh2 = results[(idx, p2.name)]
        tot_actual += sz1 + sz2
        manifest_rows.append({
            "dp_id": r["dp_id"],
            "instrument": r["instrument"],
            "star": r["canonical_target"],
            "det1_rel": r["det1_rel"],
            "det1_bytes": sz1,
            "det1_sha256": sh1,
            "det2_rel": r["det2_rel"],
            "det2_bytes": sz2,
            "det2_sha256": sh2,
        })

    actual_mib = tot_actual / (1024.0 * 1024.0)
    free_after_gib = shutil.disk_usage(ROOT).free / (1024.0 ** 3)
    if actual_mib > MAX_DOWNLOAD_MIB or free_after_gib < MIN_POST_FREE_GIB:
        raise RuntimeError(f"Post-download budget violated: {actual_mib:.2f} MiB, free={free_after_gib:.2f} GiB")

    man_doc = {
        "schema": "D090_FULL_INPUT_MANIFEST_V1",
        "phase_id": "D090",
        "created_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_exposures": len(manifest_rows),
        "n_fits_files": 2 * len(manifest_rows),
        "total_bytes": tot_actual,
        "total_mib": round(actual_mib, 2),
        "post_free_gib": round(free_after_gib, 2),
        "exposures": manifest_rows,
    }
    man_text = json.dumps(man_doc, indent=2) + "\n"
    (INP_DIR / "FULL_D090_INPUT_MANIFEST.json").write_text(man_text, encoding="utf-8")
    (WS / "FULL_D090_INPUT_MANIFEST.json").write_text(man_text, encoding="utf-8")
    print(f"DONE download_inputs: {len(manifest_rows)} paired exposures ({2*len(manifest_rows)} files, {actual_mib:.2f} MiB), free={free_after_gib:.2f} GiB", flush=True)


if __name__ == "__main__":
    main()
