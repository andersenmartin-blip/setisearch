#!/usr/bin/env python3
"""
Phase D089 verified public MAST downloader (`inputs_d089_v4_0/`).

Enforces strict prospective chronology and filesystem safety bounds:
1. Verifies `METHOD_LOCK.json` and `LOCK_RECEIPT.json` hashes before touching any FITS byte.
2. Enforces `now_epoch - lock_epoch >= 3.0 s`.
3. Verifies free disk space on `/` stays `>= 8.5 GiB` post-download.
4. Stamps `FIRST_SCIENCE_DOWNLOAD_RECEIPT.json` right before the first FITS HTTP byte.
5. Downloads all 192 locked space-UV spectra (`FUSE_FUV` `*fcal.fit.gz`,
   `HST_COS_FUV` `*_x1d.fits`, `HST_STIS_NUV` `*_x1d.fits`) into
   `ROOT/inputs_d089_v4_0/{fuse,cos,stis_nuv}/` and records `FULL_D089_INPUT_MANIFEST.json`.
"""
from __future__ import annotations

import csv
import datetime
import gzip
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
WS = AWS / "work_space_lyman_nuv_20261119_d089_v4_0_fuse_cos_stis_nuv"
INP_DIR = ROOT / "inputs_d089_v4_0"

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


def _valid_fits_payload(path: Path, is_gz: bool) -> bool:
    sz = path.stat().st_size
    if is_gz:
        if sz < 1024:
            return False
        with path.open("rb") as fh:
            if fh.read(2) != b"\x1f\x8b":
                return False
        with gzip.open(path, "rb") as gzf:
            return gzf.read(6) == b"SIMPLE"
    if sz < 2880:
        return False
    with path.open("rb") as fh:
        return fh.read(6) == b"SIMPLE"


def fetch_fits_with_retry(url: str, dst: Path, is_gz: bool = False, timeout: float = 60.0, retries: int = 5) -> tuple[int, str]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and _valid_fits_payload(dst, is_gz):
        return dst.stat().st_size, sha256_file(dst)

    tmp = dst.with_suffix(dst.suffix + ".part")
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETI-D089-Downloader/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r, tmp.open("wb") as out:
                while True:
                    blk = r.read(65536)
                    if not blk:
                        break
                    out.write(blk)
            if not _valid_fits_payload(tmp, is_gz):
                raise RuntimeError(f"Invalid FITS payload from {url}: size={tmp.stat().st_size}")
            tmp.replace(dst)
            return dst.stat().st_size, sha256_file(dst)
        except Exception as exc:
            last_err = exc
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Download failed for {url} -> {dst}: {last_err}")


def main() -> None:
    lock_path = WS / "METHOD_LOCK.json"
    receipt_path = WS / "LOCK_RECEIPT.json"
    cohort_path = WS / "FROZEN_COHORT_D089.csv"
    if not lock_path.exists() or not receipt_path.exists():
        raise RuntimeError("Missing METHOD_LOCK.json or LOCK_RECEIPT.json; seal prospective lock first!")

    rec_doc = json.loads(receipt_path.read_text(encoding="utf-8"))
    if sha256_file(lock_path) != rec_doc["method_lock_sha256"]:
        raise RuntimeError("METHOD_LOCK.json SHA-256 mismatch vs LOCK_RECEIPT.json!")
    for rel_name, expected_sha in rec_doc["locked_artifact_sha256"].items():
        fp = WS / rel_name
        if not fp.exists() or sha256_file(fp) != expected_sha:
            raise RuntimeError(f"Prospective lock hash mismatch on {rel_name}!")

    with cohort_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != 192:
        raise RuntimeError(f"Expected 192 locked rows in FROZEN_COHORT_D089.csv, found {len(rows)}")

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
            "schema": "SETI_D089_FIRST_SCIENCE_DOWNLOAD_RECEIPT_V1",
            "phase_id": "D089",
            "locked_utc": rec_doc["locked_utc"],
            "first_download_utc": first_utc,
            "lock_to_first_download_seconds": round(dt_s, 3),
            "free_gib_before_download": round(free_gib, 4),
            "projected_download_gib": round(proj_gib, 4),
        }
        first_receipt_path.write_text(json.dumps(first_doc, indent=2) + "\n", encoding="utf-8")

    INP_DIR.mkdir(parents=True, exist_ok=True)
    for sub in ("fuse", "cos", "stis_nuv"):
        (INP_DIR / sub).mkdir(parents=True, exist_ok=True)

    def dl_one(r: dict[str, Any]) -> dict[str, Any]:
        inst = r["instrument"]
        dp_id = r["dp_id"]
        if inst == "FUSE_FUV":
            is_gz = True
            this_rel = f"fuse/{dp_id}_fcal.fit.gz"
        elif inst == "HST_COS_FUV":
            is_gz = False
            this_rel = f"cos/{dp_id}_x1d.fits"
        elif inst == "HST_STIS_NUV":
            is_gz = False
            this_rel = f"stis_nuv/{dp_id}_x1d.fits"
        else:
            raise ValueError(inst)

        this_bytes, this_sha = fetch_fits_with_retry(r["this_url"], INP_DIR / this_rel, is_gz=is_gz)
        return {
            "phase_id": "D089",
            "instrument": inst,
            "star": r["canonical_target"],
            "role": r["role"],
            "dp_id": dp_id,
            "this_rel": this_rel,
            "this_bytes": this_bytes,
            "this_sha256": this_sha,
            "this_url": r["this_url"],
        }

    print(f"=== Phase D089 Download ({len(rows)} exposures, proj={proj_gib:.3f} GiB) ===", flush=True)
    with ThreadPoolExecutor(max_workers=3) as ex:
        manifest_rows = list(ex.map(dl_one, rows))

    tot_bytes = sum(m["this_bytes"] for m in manifest_rows)
    manifest = {
        "schema": "FULL_D089_INPUT_MANIFEST_V1",
        "phase_id": "D089",
        "downloaded_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_exposures": len(manifest_rows),
        "total_bytes": tot_bytes,
        "total_gib": round(tot_bytes / (1024.0**3), 4),
        "exposures": manifest_rows,
    }
    (INP_DIR / "FULL_D089_INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    post_free = shutil.disk_usage(ROOT).free / (1024.0**3)
    print(f"DONE Download: {len(manifest_rows)} files, {tot_bytes / (1024.0**2):.2f} MiB, free_on_disk={post_free:.2f} GiB", flush=True)


if __name__ == "__main__":
    main()
