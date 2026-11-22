#!/usr/bin/env python3
"""
Phase D100 (V5.8) Science Input Downloader.
Executes strictly AFTER METHOD_LOCK.json and LOCK_RECEIPT.json are sealed
with inputs_d100_v5_8 absent, and enforces >= 3.0 s prospective lock chronology lag,
<= 125.0 MiB raw download cap, and >= 1.5 GiB free disk guard.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import os
import pathlib
import shutil
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from astropy.io import fits

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_v5_8_20261122_d100_jcmt_3mm_sofia_fifils_iue_eccentric_keplerian"
IN_DIR = ROOT / "inputs_d100_v5_8"

MIN_CHRONOLOGY_LAG_S = 3.0
MAX_RAW_DOWNLOAD_MIB = 125.0
MIN_FREE_DISK_GIB = 1.5


def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(1048576)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _validate_fits_bytes(raw: bytes, rel_path: str) -> None:
    if len(raw) < 2880:
        raise RuntimeError(f"Short file ({len(raw)} B) for {rel_path}")
    payload = gzip.decompress(raw) if rel_path.endswith(".gz") or raw[:2] == b"\x1f\x8b" else raw
    with fits.open(io.BytesIO(payload), ignore_missing_end=True) as hdul:
        if len(hdul) < 1:
            raise RuntimeError(f"Empty HDU list in {rel_path}")


def _download_one(row: dict[str, str], idx: int, total: int) -> dict[str, Any]:
    rel = row["f1_rel"]
    url = row["f1_url"]
    dp_id = row["dp_id"]
    dest = IN_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= 2880:
        raw = dest.read_bytes()
        _validate_fits_bytes(raw, rel)
        return {
            "dp_id": dp_id,
            "instrument": row["instrument"],
            "canonical_target": row["canonical_target"],
            "rel_path": rel,
            "url": url,
            "bytes": len(raw),
            "sha256": _sha256_file(dest),
            "cached": True,
        }

    last_err: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Panchromatic-SETI-D100)"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read()
            _validate_fits_bytes(raw, rel)
            tmp = dest.with_suffix(dest.suffix + ".part")
            tmp.write_bytes(raw)
            os.replace(tmp, dest)
            print(f"[{idx:02d}/{total:02d}] OK {row['instrument']} {row['canonical_target']} ({len(raw)} B) -> {rel}", flush=True)
            return {
                "dp_id": dp_id,
                "instrument": row["instrument"],
                "canonical_target": row["canonical_target"],
                "rel_path": rel,
                "url": url,
                "bytes": len(raw),
                "sha256": _sha256_file(dest),
                "cached": False,
            }
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed downloading {dp_id} from {url}: {last_err}")


def main() -> int:
    lock_path = WS / "LOCK_RECEIPT.json"
    method_path = WS / "METHOD_LOCK.json"
    cohort_csv = WS / "FROZEN_COHORT_D100.csv"
    if not (lock_path.exists() and method_path.exists() and cohort_csv.exists()):
        raise RuntimeError("Stage-1 lock receipts or frozen cohort CSV missing — run build_cohort.py first.")

    lock_rec = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock_rec.get("inputs_dir_exists_at_seal") is not False:
        raise RuntimeError("Prospective lock violated: inputs_dir_exists_at_seal is not False.")

    locked_dt = datetime.fromisoformat(lock_rec["locked_utc"])
    now_dt = datetime.now(timezone.utc)
    lag_s = (now_dt - locked_dt).total_seconds()
    if lag_s < MIN_CHRONOLOGY_LAG_S:
        raise RuntimeError(f"Chronology lag {lag_s:.3f}s < required {MIN_CHRONOLOGY_LAG_S:.1f}s.")

    du = shutil.disk_usage(ROOT)
    free_gib = du.free / (1024.0 ** 3)
    if free_gib < MIN_FREE_DISK_GIB:
        raise RuntimeError(f"Insufficient free disk: {free_gib:.3f} GiB < {MIN_FREE_DISK_GIB:.2f} GiB.")

    with cohort_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError("FROZEN_COHORT_D100.csv is empty.")

    proj_mib = sum(int(r["f1_bytes"]) for r in rows) / 1048576.0
    if proj_mib > MAX_RAW_DOWNLOAD_MIB:
        raise RuntimeError(f"Projected raw download {proj_mib:.2f} MiB exceeds {MAX_RAW_DOWNLOAD_MIB:.1f} MiB cap.")

    IN_DIR.mkdir(parents=True, exist_ok=True)
    receipt_path = WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json"
    if not receipt_path.exists():
        first_utc = datetime.now(timezone.utc)
        first_rec = {
            "schema": "D100_FIRST_SCIENCE_DOWNLOAD_RECEIPT",
            "phase_id": "D100",
            "locked_utc": lock_rec["locked_utc"],
            "first_science_download_started_utc": first_utc.isoformat(),
            "chronology_lag_seconds": round((first_utc - locked_dt).total_seconds(), 4),
            "first_target": rows[0]["canonical_target"],
            "first_dp_id": rows[0]["dp_id"],
            "inputs_dir": str(IN_DIR),
            "planned_files": len(rows),
            "projected_mib": round(proj_mib, 4),
        }
        receipt_path.write_text(json.dumps(first_rec, indent=2) + "\n", encoding="utf-8")

    # Download non-ESO in small parallel pool (max_workers=4), ESO sequentially (proxy rate-limit friendly)
    non_eso = [(i + 1, r) for i, r in enumerate(rows) if not r["instrument"].startswith("ESO_")]
    eso_only = [(i + 1, r) for i, r in enumerate(rows) if r["instrument"].startswith("ESO_")]
    tot_n = len(rows)

    manifest_items: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(_download_one, r, idx, tot_n) for idx, r in non_eso]
        for fu in futs:
            manifest_items.append(fu.result())

    for idx, r in eso_only:
        manifest_items.append(_download_one(r, idx, tot_n))

    manifest_items.sort(key=lambda d: (d["instrument"], d["canonical_target"], d["dp_id"]))
    total_bytes = sum(int(it["bytes"]) for it in manifest_items)
    total_mib = total_bytes / 1048576.0
    if total_mib > MAX_RAW_DOWNLOAD_MIB:
        raise RuntimeError(f"Actual downloaded size {total_mib:.3f} MiB exceeds {MAX_RAW_DOWNLOAD_MIB:.1f} MiB cap.")

    manifest = {
        "schema": "D100_FULL_INPUT_MANIFEST",
        "phase_id": "D100",
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "inputs_dir": str(IN_DIR),
        "n_files": len(manifest_items),
        "total_bytes": total_bytes,
        "total_mib": round(total_mib, 4),
        "files": manifest_items,
    }
    (WS / "FULL_D100_INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"D100 download complete: {len(manifest_items)} files, {total_bytes} B ({total_mib:.4f} MiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
