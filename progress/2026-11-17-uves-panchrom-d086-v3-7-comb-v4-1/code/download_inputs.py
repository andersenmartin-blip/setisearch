#!/usr/bin/env python3
"""Post-lock ESO downloader for Phase D086 (UVES_NUV, ESPRESSO S1D_A+S1D_B, HARPS S1D+HARPSTAR).

Enforces strict prospective chronology:
- Refuses to execute unless METHOD_LOCK.json and LOCK_RECEIPT.json exist, all
  locked script/cohort SHA-256 digests match, and now_utc >= locked_utc + 3.0s.
- Records FIRST_SCIENCE_DOWNLOAD_RECEIPT.json immediately before the first byte
  of science data is written to inputs_d086_v3_7/.
- Monitors free disk (>= 10.0 GiB) and total cache size (<= 4.2 GiB).
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import shutil
import tarfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent
SETI_ROOT = WS.parent.parent
INPUTS_DIR = SETI_ROOT / "inputs_d086_v3_7"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_iso_utc(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def verify_lock_before_download() -> tuple[dict[str, Any], dict[str, Any]]:
    lock_p = WS / "METHOD_LOCK.json"
    rec_p = WS / "LOCK_RECEIPT.json"
    if not lock_p.is_file() or not rec_p.is_file():
        raise RuntimeError("PROSPECTIVE_LOCK_MISSING: Seal METHOD_LOCK.json & LOCK_RECEIPT.json first!")
    mlock = json.loads(lock_p.read_text(encoding="utf-8"))
    rec = json.loads(rec_p.read_text(encoding="utf-8"))
    if sha256_file(lock_p) != rec["method_lock_sha256"]:
        raise RuntimeError("METHOD_LOCK.json SHA-256 mismatch vs LOCK_RECEIPT.json")
    for rel, expected_sha in rec["locked_artifact_sha256"].items():
        fp = WS / rel
        if not fp.is_file() or sha256_file(fp) != expected_sha:
            raise RuntimeError(f"Locked artifact tampered or missing: {rel}")

    locked_dt = parse_iso_utc(rec["locked_utc"])
    now_dt = dt.datetime.now(dt.timezone.utc)
    delta = (now_dt - locked_dt).total_seconds()
    if delta < 3.0:
        wait_s = 3.2 - delta
        print(f"[download_inputs] Waiting {wait_s:.2f}s to satisfy >= +3.0s post-lock chronology...", flush=True)
        time.sleep(wait_s)
        now_dt = dt.datetime.now(dt.timezone.utc)
    return mlock, rec


def safe_dp_name(dp_id: str) -> str:
    return dp_id.strip().replace(":", "_")


def download_one_file(url: str, dst: Path, expect_fits: bool = False, expect_tar: bool = False, min_bytes: int = 1024) -> tuple[str, int]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_file() and dst.stat().st_size >= min_bytes:
        if expect_fits:
            with dst.open("rb") as f:
                if f.read(6) != b"SIMPLE":
                    dst.unlink()
        elif expect_tar:
            try:
                with tarfile.open(dst, "r:*") as tf:
                    if not tf.getnames():
                        dst.unlink()
            except Exception:
                dst.unlink()

    if not dst.is_file() or dst.stat().st_size < min_bytes:
        tmp = dst.with_suffix(dst.suffix + ".part")
        last_err: Exception | None = None
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "SETI-D086-Pipeline/1.0"})
                with urllib.request.urlopen(req, timeout=120.0) as resp, tmp.open("wb") as out:
                    shutil.copyfileobj(resp, out, length=1024 * 1024)
                sz = tmp.stat().st_size
                if sz < min_bytes:
                    raise RuntimeError(f"Truncated file {dst.name}: {sz} bytes")
                if expect_fits:
                    with tmp.open("rb") as f:
                        if f.read(6) != b"SIMPLE":
                            raise RuntimeError(f"Invalid FITS header in {dst.name}")
                if expect_tar:
                    with tarfile.open(tmp, "r:*") as tf:
                        names = tf.getnames()
                        if not any("_e2ds_A.fits" in n for n in names):
                            raise RuntimeError(f"HARPSTAR tar {dst.name} missing _e2ds_A.fits")
                os.replace(tmp, dst)
                break
            except Exception as exc:
                last_err = exc
                if tmp.exists():
                    tmp.unlink()
                if attempt + 1 < 4:
                    time.sleep(2.0 * (attempt + 1))
        else:
            assert last_err is not None
            raise last_err

    return sha256_file(dst), int(dst.stat().st_size)


def main() -> None:
    _mlock, rec = verify_lock_before_download()
    free_gib = shutil.disk_usage(SETI_ROOT).free / (1024.0 ** 3)
    if free_gib < 10.0:
        raise RuntimeError(f"Insufficient disk space: {free_gib:.2f} GiB free (< 10.0 GiB)")

    with (WS / "FROZEN_COHORT_D086.csv").open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 181:
        raise RuntimeError(f"Expected 181 cohort exposures, got {len(rows)}")

    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    receipt_path = INPUTS_DIR / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json"
    if not receipt_path.is_file():
        first_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        rc_doc = {
            "schema": "SETI_D086_FIRST_SCIENCE_DOWNLOAD_RECEIPT_V1",
            "phase_id": "D086",
            "locked_utc": rec["locked_utc"],
            "first_download_utc": first_utc,
            "method_lock_sha256": rec["method_lock_sha256"],
        }
        receipt_path.write_text(json.dumps(rc_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    print(f"[download_inputs] Downloading 181 exposures (307 ESO files) into {INPUTS_DIR}...", flush=True)

    def _job(row: dict[str, str]) -> dict[str, Any]:
        inst = row["instrument"]
        dp = row["dp_id"].strip()
        sdp = safe_dp_name(dp)
        if inst == "UVES_NUV":
            rel_a = f"uves_nuv/s1d/{sdp}_s1d.fits"
            sha_a, sz_a = download_one_file(row["this_url"], INPUTS_DIR / rel_a, expect_fits=True)
            return {
                "dp_id": dp,
                "instrument": inst,
                "star": row["canonical_target"],
                "s1d_relpath": rel_a,
                "s1d_sha256": sha_a,
                "s1d_bytes": sz_a,
                "aux_relpath": "",
                "aux_sha256": "",
                "aux_bytes": 0,
            }
        elif inst == "ESPRESSO":
            rel_a = f"espresso/s1d_a/{sdp}_s1d_a.fits"
            rel_b = f"espresso/s1d_b/{sdp}_s1d_b.fits"
            sha_a, sz_a = download_one_file(row["this_url"], INPUTS_DIR / rel_a, expect_fits=True)
            sha_b, sz_b = download_one_file(row["aux_url"], INPUTS_DIR / rel_b, expect_fits=True)
            return {
                "dp_id": dp,
                "instrument": inst,
                "star": row["canonical_target"],
                "s1d_relpath": rel_a,
                "s1d_sha256": sha_a,
                "s1d_bytes": sz_a,
                "aux_relpath": rel_b,
                "aux_sha256": sha_b,
                "aux_bytes": sz_b,
            }
        else:  # HARPS
            rel_a = f"harps/s1d/{sdp}_s1d.fits"
            rel_b = f"harps/harpstar/{sdp}.tar"
            sha_a, sz_a = download_one_file(row["this_url"], INPUTS_DIR / rel_a, expect_fits=True)
            sha_b, sz_b = download_one_file(row["aux_url"], INPUTS_DIR / rel_b, expect_tar=True)
            return {
                "dp_id": dp,
                "instrument": inst,
                "star": row["canonical_target"],
                "s1d_relpath": rel_a,
                "s1d_sha256": sha_a,
                "s1d_bytes": sz_a,
                "aux_relpath": rel_b,
                "aux_sha256": sha_b,
                "aux_bytes": sz_b,
            }

    manifest_rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(6) as ex:
        for idx, res in enumerate(ex.map(_job, rows), start=1):
            manifest_rows.append(res)
            if idx % 25 == 0 or idx == len(rows):
                tot_b = sum(r["s1d_bytes"] + r["aux_bytes"] for r in manifest_rows)
                print(f"  progress: {idx}/{len(rows)} exposures verified ({tot_b / (1024**3):.3f} GiB)", flush=True)

    tot_bytes = sum(r["s1d_bytes"] + r["aux_bytes"] for r in manifest_rows)
    tot_gib = tot_bytes / (1024.0 ** 3)
    free_after_gib = shutil.disk_usage(SETI_ROOT).free / (1024.0 ** 3)
    if tot_gib > 4.2 or free_after_gib < 10.0:
        raise RuntimeError(f"Disk budget exceeded: cache={tot_gib:.3f} GiB, free={free_after_gib:.2f} GiB")

    manifest_doc = {
        "schema": "SETI_D086_FULL_INPUT_MANIFEST_V1",
        "phase_id": "D086",
        "created_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "total_exposures": len(manifest_rows),
        "total_bytes": tot_bytes,
        "total_gib": round(tot_gib, 4),
        "exposures": manifest_rows,
    }
    (INPUTS_DIR / "FULL_D086_INPUT_MANIFEST.json").write_text(json.dumps(manifest_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"[download_inputs] DONE: {len(manifest_rows)} exposures ({tot_gib:.3f} GiB), free={free_after_gib:.2f} GiB.", flush=True)


if __name__ == "__main__":
    main()
