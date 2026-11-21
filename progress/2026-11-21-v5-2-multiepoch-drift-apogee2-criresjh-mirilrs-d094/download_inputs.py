#!/usr/bin/env python3
"""
Phase D094 Stage-1 Downloader.

Reads `LOCK_RECEIPT.json`, verifies that all 7 Stage-1 locked files remain unmodified on disk
and that `chronology_lag_seconds >= 3.0`, checks strict disk/download caps (`<= 98.0 MiB`
download and `>= 1.50 GiB` free on `/`), and downloads all frozen `FROZEN_COHORT_D094.csv`
FITS spectra into `<ROOT>/inputs_d094_v5_2/`.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import pathlib
import shutil
import time
import urllib.request
from typing import Any

WS = pathlib.Path(__file__).resolve().parent
ROOT = WS.parent.parent
INP_DIR = ROOT / "inputs_d094_v5_2"


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            b = fh.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def parse_utc(ts: str) -> dt.datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return dt.datetime.fromisoformat(ts)


def _download_with_retry(url: str, dst: pathlib.Path, timeout_s: float = 90.0) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    last_err: Exception | None = None
    for att in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-D094/1.0"})
            with urllib.request.urlopen(req, timeout=timeout_s) as resp, tmp.open("wb") as out:
                while True:
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
            with tmp.open("rb") as chk:
                hdr = chk.read(9)
            if hdr != b"SIMPLE  =":
                raise RuntimeError(f"Invalid FITS header {hdr!r} from {url}")
            tmp.replace(dst)
            return
        except Exception as exc:
            last_err = exc
            if tmp.exists():
                tmp.unlink()
            time.sleep(2.0 * (att + 1))
    raise RuntimeError(f"Failed download {url}: {last_err}")


def main() -> None:
    lock_path = WS / "METHOD_LOCK.json"
    rec_path = WS / "LOCK_RECEIPT.json"
    coh_path = WS / "FROZEN_COHORT_D094.csv"
    if not (lock_path.exists() and rec_path.exists() and coh_path.exists()):
        raise RuntimeError("Stage-1 lock files missing; run build_cohort.py first.")

    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    rec = json.loads(rec_path.read_text(encoding="utf-8"))

    # Verify all 7 locked Stage-1 files match hashes before downloading any science file
    for fname, exp_sha in lock["locked_file_hashes"].items():
        fpath = WS / fname
        if not fpath.exists():
            raise RuntimeError(f"Locked Stage-1 file missing: {fname}")
        got = sha256_file(fpath)
        if got != exp_sha:
            raise RuntimeError(f"Stage-1 integrity violation in {fname}: {got} != {exp_sha}")

    if rec.get("inputs_d094_v5_2_exists") is not False:
        raise RuntimeError("LOCK_RECEIPT recorded inputs_d094_v5_2_exists != False!")

    # Verify chronology lag >= 3.0s since lock timestamp
    lock_ts = parse_utc(rec["locked_utc"])
    now_ts = dt.datetime.now(dt.timezone.utc)
    lag_s = (now_ts - lock_ts).total_seconds()
    min_lag = float(lock["hard_caps"]["min_chronology_lag_seconds"])
    if lag_s < min_lag:
        wait_s = (min_lag - lag_s) + 0.5
        print(f"Waiting {wait_s:.2f}s to satisfy Stage-1 chronology lag >= {min_lag}s...", flush=True)
        time.sleep(wait_s)
        now_ts = dt.datetime.now(dt.timezone.utc)
        lag_s = (now_ts - lock_ts).total_seconds()

    # Check disk headroom on '/'
    free_bytes = shutil.disk_usage(ROOT).free
    min_free_bytes = int(float(lock["hard_caps"]["min_free_disk_gib"]) * (1024 ** 3))
    rows = list(csv.DictReader(coh_path.open("r", encoding="utf-8")))
    proj_bytes = sum(int(r["f1_bytes"]) for r in rows)
    max_dl_bytes = int(float(lock["hard_caps"]["max_download_mib"]) * (1024 ** 2))
    if proj_bytes > max_dl_bytes:
        raise RuntimeError(f"Projected download {proj_bytes / 1048576:.2f} MiB exceeds cap {lock['hard_caps']['max_download_mib']} MiB")
    if (free_bytes - proj_bytes) < min_free_bytes:
        raise RuntimeError(f"Insufficient disk headroom: free={free_bytes / (1024**3):.3f} GiB")

    # Download each unique relative file
    seen_rel: set[str] = set()
    INP_DIR.mkdir(parents=True, exist_ok=True)
    first_receipt_written = False
    manifest_rows: list[dict[str, Any]] = []
    tot_dl_bytes = 0

    for idx, r in enumerate(rows, 1):
        rel = r["f1_rel"]
        url = r["f1_url"]
        dst = INP_DIR / rel
        if rel not in seen_rel:
            seen_rel.add(rel)
            if dst.exists() and dst.stat().st_size >= 16384:
                with dst.open("rb") as chk:
                    if chk.read(9) != b"SIMPLE  =":
                        _download_with_retry(url, dst)
            else:
                _download_with_retry(url, dst)
            sz = dst.stat().st_size
            if sz < 16384:
                raise RuntimeError(f"FITS too small ({sz} B): {rel}")
            sha = sha256_file(dst)
            tot_dl_bytes += sz
            if not first_receipt_written:
                dl_ts = dt.datetime.now(dt.timezone.utc)
                rec_dl = {
                    "schema": "D094_FIRST_SCIENCE_DOWNLOAD_RECEIPT",
                    "phase_id": "D094",
                    "locked_utc": rec["locked_utc"],
                    "first_science_download_utc": dl_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "chronology_lag_seconds": round((dl_ts - lock_ts).total_seconds(), 3),
                    "first_file_rel": rel,
                    "first_file_bytes": sz,
                    "first_file_sha256": sha,
                    "method_lock_sha256": sha256_file(lock_path),
                }
                (WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json").write_text(json.dumps(rec_dl, indent=2) + "\n", encoding="utf-8")
                first_receipt_written = True
                print(f"First science download receipt written (lag={rec_dl['chronology_lag_seconds']}s)", flush=True)
            print(f"[{idx:02d}/{len(rows)}] {rel} ({sz / 1048576:.3f} MiB)", flush=True)
        else:
            sz = dst.stat().st_size
            sha = sha256_file(dst)

        manifest_rows.append({
            "instrument": r["instrument"],
            "canonical_target": r["canonical_target"],
            "dp_id": r["dp_id"],
            "f1_rel": rel,
            "f1_url": url,
            "bytes": sz,
            "sha256": sha,
            "mjd_obs": float(r["mjd_obs"]),
            "t_exptime": float(r["t_exptime"]),
        })

    tot_mib = tot_dl_bytes / 1048576.0
    if tot_mib > float(lock["hard_caps"]["max_download_mib"]):
        raise RuntimeError(f"Actual download {tot_mib:.3f} MiB exceeded cap {lock['hard_caps']['max_download_mib']} MiB!")
    post_free_gib = shutil.disk_usage(ROOT).free / (1024 ** 3)
    if post_free_gib < float(lock["hard_caps"]["min_free_disk_gib"]):
        raise RuntimeError(f"Free disk dropped below {lock['hard_caps']['min_free_disk_gib']} GiB: {post_free_gib:.3f} GiB")

    manifest = {
        "schema": "FULL_D094_INPUT_MANIFEST",
        "phase_id": "D094",
        "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_fits_files": len(seen_rel),
        "total_bytes": tot_dl_bytes,
        "total_mib": round(tot_mib, 3),
        "post_download_free_gib": round(post_free_gib, 3),
        "method_lock_sha256": sha256_file(lock_path),
        "files": manifest_rows,
    }
    (WS / "FULL_D094_INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"DONE: downloaded {len(seen_rel)} FITS ({tot_mib:.2f} MiB), free disk {post_free_gib:.2f} GiB.", flush=True)


if __name__ == "__main__":
    main()
