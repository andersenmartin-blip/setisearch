#!/usr/bin/env python3
"""
Phase D088 verified public archival downloader (`inputs_d088_v3_9/`).

Enforces strict prospective chronology and filesystem safety bounds:
1. Verifies `METHOD_LOCK.json` and `LOCK_RECEIPT.json` hashes before touching any FITS byte.
2. Enforces `now_epoch - lock_epoch >= 3.0 s` (waiting cleanly if invoked immediately after lock).
3. Verifies free disk space on `/` stays `>= 8.5 GiB` post-download.
4. Stamps `FIRST_SCIENCE_DOWNLOAD_RECEIPT.json` right before the first FITS HTTP byte.
5. Downloads all 176 locked science spectra (+ 68 SOPHIE `e2ds` Fiber-B ancillaries) into
   `ROOT/inputs_d088_v3_9/{sophie,elodie,espadons}/` and records `FULL_D088_INPUT_MANIFEST.json`.
"""

from __future__ import annotations

import csv
import datetime
import hashlib
import json
import shutil
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(".")
AWS = ROOT / "analysis_workspace"
WS = AWS / "work_radio23_allsky_20261118_d088_v3_9_northern_and_comb_v4_1"
INP_DIR = ROOT / "inputs_d088_v3_9"

MIN_POST_FREE_GIB = 8.5
MIN_LOCK_LAG_S = 3.0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def parse_iso_utc(ts: str) -> float:
    return datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp()


def fetch_fits_with_retry(url: str, dst: Path, timeout: float = 60.0, retries: int = 4) -> tuple[int, str]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size >= 2880:
        with dst.open("rb") as fh:
            head = fh.read(10)
        if head.startswith(b"SIMPLE"):
            return dst.stat().st_size, sha256_file(dst)

    tmp = dst.with_suffix(dst.suffix + ".part")
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETI-D088-Downloader/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r, tmp.open("wb") as out:
                while True:
                    blk = r.read(65536)
                    if not blk:
                        break
                    out.write(blk)
            sz = tmp.stat().st_size
            with tmp.open("rb") as fh:
                head = fh.read(10)
            if sz < 2880 or not head.startswith(b"SIMPLE"):
                raise RuntimeError(f"Invalid FITS payload from {url}: size={sz}, head={head!r}")
            tmp.replace(dst)
            return sz, sha256_file(dst)
        except Exception as exc:
            last_err = exc
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"Download failed for {url} -> {dst}: {last_err}")


def main() -> None:
    lock_path = WS / "METHOD_LOCK.json"
    receipt_path = WS / "LOCK_RECEIPT.json"
    cohort_path = WS / "FROZEN_COHORT_D088.csv"
    if not lock_path.exists() or not receipt_path.exists():
        raise RuntimeError("Missing METHOD_LOCK.json or LOCK_RECEIPT.json; seal prospective lock first!")

    lock_doc = json.loads(lock_path.read_text(encoding="utf-8"))
    rec_doc = json.loads(receipt_path.read_text(encoding="utf-8"))
    if sha256_file(lock_path) != rec_doc["method_lock_sha256"]:
        raise RuntimeError("METHOD_LOCK.json SHA-256 mismatch vs LOCK_RECEIPT.json!")
    for rel_name, expected_sha in rec_doc["locked_artifact_sha256"].items():
        fp = WS / rel_name
        if not fp.exists() or sha256_file(fp) != expected_sha:
            raise RuntimeError(f"Prospective lock hash mismatch on {rel_name}!")

    with cohort_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != 176:
        raise RuntimeError(f"Expected 176 locked rows in FROZEN_COHORT_D088.csv, found {len(rows)}")

    proj_bytes = sum(int(r["this_bytes"]) + int(r["aux_bytes"] or 0) for r in rows)
    proj_gib = proj_bytes / (1024.0**3)
    free_gib = shutil.disk_usage(ROOT).free / (1024.0**3)
    post_free_gib = free_gib - proj_gib
    if post_free_gib < MIN_POST_FREE_GIB:
        raise RuntimeError(
            f"Safety disk guard triggered: free={free_gib:.2f} GiB, proj={proj_gib:.3f} GiB, "
            f"post={post_free_gib:.2f} GiB < {MIN_POST_FREE_GIB:.2f} GiB"
        )

    lock_epoch = parse_iso_utc(rec_doc["locked_utc"])
    now_epoch = time.time()
    if now_epoch - lock_epoch < MIN_LOCK_LAG_S + 0.5:
        wait_s = (MIN_LOCK_LAG_S + 0.6) - (now_epoch - lock_epoch)
        print(f"Respecting >= {MIN_LOCK_LAG_S:.1f}s prospective lock lag; waiting {wait_s:.2f}s...", flush=True)
        time.sleep(max(0.1, wait_s))

    first_receipt_path = WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json"
    if not first_receipt_path.exists():
        first_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        dt_s = parse_iso_utc(first_utc) - lock_epoch
        if dt_s < MIN_LOCK_LAG_S:
            time.sleep(MIN_LOCK_LAG_S - dt_s + 1.0)
            first_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            dt_s = parse_iso_utc(first_utc) - lock_epoch
        first_doc = {
            "schema": "SETI_D088_FIRST_SCIENCE_DOWNLOAD_RECEIPT_V1",
            "phase_id": "D088",
            "locked_utc": rec_doc["locked_utc"],
            "first_download_utc": first_utc,
            "lock_to_first_download_seconds": round(dt_s, 3),
            "free_gib_before_download": round(free_gib, 4),
            "projected_download_gib": round(proj_gib, 4),
        }
        first_receipt_path.write_text(json.dumps(first_doc, indent=2) + "\n", encoding="utf-8")

    INP_DIR.mkdir(parents=True, exist_ok=True)
    for sub in ("sophie", "elodie", "espadons"):
        (INP_DIR / sub).mkdir(parents=True, exist_ok=True)

    def dl_one(r: dict[str, Any]) -> dict[str, Any]:
        inst = r["instrument"]
        dp_id = r["dp_id"]
        if inst == "OHP_SOPHIE":
            this_rel = f"sophie/{dp_id}_s1d.fits"
            aux_rel = f"sophie/{dp_id}_e2ds.fits"
        elif inst == "OHP_ELODIE":
            this_rel = f"elodie/{dp_id}_s1d.fits"
            aux_rel = ""
        elif inst == "CFHT_ESPADONS":
            this_rel = f"espadons/{dp_id}.fits"
            aux_rel = ""
        else:
            raise ValueError(inst)

        this_bytes, this_sha = fetch_fits_with_retry(r["this_url"], INP_DIR / this_rel)
        if aux_rel and r["aux_url"]:
            aux_bytes, aux_sha = fetch_fits_with_retry(r["aux_url"], INP_DIR / aux_rel)
        else:
            aux_bytes, aux_sha = 0, ""

        return {
            "phase_id": "D088",
            "instrument": inst,
            "star": r["canonical_target"],
            "role": r["role"],
            "dp_id": dp_id,
            "this_rel": this_rel,
            "this_bytes": this_bytes,
            "this_sha256": this_sha,
            "aux_rel": aux_rel,
            "aux_bytes": aux_bytes,
            "aux_sha256": aux_sha,
            "this_url": r["this_url"],
            "aux_url": r["aux_url"],
            "aux_category": r["aux_category"],
        }

    print(f"=== Phase D088 Download ({len(rows)} exposures, proj={proj_gib:.3f} GiB) ===", flush=True)
    with ThreadPoolExecutor(max_workers=6) as ex:
        manifest_rows = list(ex.map(dl_one, rows))

    tot_bytes = sum(m["this_bytes"] + m["aux_bytes"] for m in manifest_rows)
    manifest = {
        "schema": "FULL_D088_INPUT_MANIFEST_V1",
        "phase_id": "D088",
        "downloaded_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_exposures": len(manifest_rows),
        "n_ancillary_files": sum(1 for m in manifest_rows if m["aux_rel"]),
        "total_bytes": tot_bytes,
        "total_gib": round(tot_bytes / (1024.0**3), 4),
        "exposures": manifest_rows,
    }
    (INP_DIR / "FULL_D088_INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    post_free = shutil.disk_usage(ROOT).free / (1024.0**3)
    print(f"DONE: downloaded {len(manifest_rows)} exposures ({tot_bytes/(1024**3):.4f} GiB); free={post_free:.2f} GiB", flush=True)


if __name__ == "__main__":
    main()
