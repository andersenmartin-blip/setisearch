#!/usr/bin/env python3
"""
Prospective Stage-1 Download Script for SETI Phase D097 (V5.5).

Verifies immutable Stage-1 METHOD_LOCK hashes and chronology lag (>= 3.0 s) before
creating `inputs_d097_v5_5/`, validates every downloaded FITS or IPAC `.new.tbl`
file, and writes `FIRST_SCIENCE_DOWNLOAD_RECEIPT.json` and `FULL_D097_INPUT_MANIFEST.json`.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import pathlib
import shutil
import sys
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any

from astropy.io import fits

WS = pathlib.Path(__file__).resolve().parent
ROOT = WS.parent.parent
IN_DIR = ROOT / "inputs_d097_v5_5"


def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _validate_payload(path: pathlib.Path, instrument: str) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size < 256:
        raise RuntimeError(f"Empty or missing file: {path}")
    if instrument == "HERSCHEL_HIFI" or path.suffix.lower() == ".tbl":
        txt = path.read_text(encoding="utf-8", errors="replace")
        n_rows = 0
        has_header = ("frequency" in txt.lower() and "flux" in txt.lower())
        for ln in txt.splitlines():
            s = ln.strip()
            if not s or s.startswith("\\") or s.startswith("|"):
                continue
            parts = s.split()
            if len(parts) >= 2:
                float(parts[0])
                float(parts[1])
                n_rows += 1
        if not has_header or n_rows < 500:
            raise RuntimeError(f"Invalid HIFI IPAC table {path.name}: header={has_header}, rows={n_rows}")
        return {"format": "IPAC_ASCII_TBL", "n_rows": n_rows}

    with fits.open(path, memmap=False) as hdul:
        n_hdus = len(hdul)
        if n_hdus < 1:
            raise RuntimeError(f"Empty FITS HDU list in {path.name}")
        return {"format": "FITS", "n_hdus": n_hdus}


def _download_with_retry(url: str, dest: pathlib.Path, max_retries: int = 4) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "SETI-D097-V5_5-Harvester/1.0"},
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                if resp.status not in (200, 206):
                    raise RuntimeError(f"HTTP {resp.status} for {url}")
                with tmp.open("wb") as out:
                    while True:
                        chunk = resp.read(262144)
                        if not chunk:
                            break
                        out.write(chunk)
            tmp.replace(dest)
            return int(dest.stat().st_size)
        except Exception as exc:
            last_err = exc
            if tmp.exists():
                tmp.unlink()
            time.sleep(2.0 * (2 ** attempt))
    raise RuntimeError(f"Failed download after {max_retries} retries for {url}: {last_err}")


def main() -> int:
    ml_path = WS / "METHOD_LOCK.json"
    lr_path = WS / "LOCK_RECEIPT.json"
    fc_path = WS / "FROZEN_COHORT_D097.csv"
    if not (ml_path.is_file() and lr_path.is_file() and fc_path.is_file()):
        raise RuntimeError("Stage-1 lock files missing; run build_cohort.py first.")

    ml = json.loads(ml_path.read_text(encoding="utf-8"))
    lr = json.loads(lr_path.read_text(encoding="utf-8"))

    ml_sha = _sha256_file(ml_path)
    if lr["method_lock_sha256"] != ml_sha:
        raise RuntimeError("LOCK_RECEIPT method_lock_sha256 mismatch!")

    for fn, exp_sha in ml["locked_file_hashes"].items():
        fp = WS / fn
        if not fp.is_file() or _sha256_file(fp) != exp_sha:
            raise RuntimeError(f"Stage-1 locked file tampered or missing before download: {fn}")

    now_dt = datetime.now(timezone.utc)
    now_unix = now_dt.timestamp()
    lag = now_unix - float(lr["locked_at_unix"])
    min_lag = float(ml["hard_caps"]["min_chronology_lag_seconds"])
    if lag < min_lag:
        raise RuntimeError(f"Chronology lag {lag:.2f}s < required {min_lag:.2f}s")

    free_gib = shutil.disk_usage(ROOT).free / (1024.0 ** 3)
    min_free = float(ml["hard_caps"]["min_free_disk_gib"])
    if free_gib < min_free:
        raise RuntimeError(f"Insufficient free disk: {free_gib:.2f} GiB < {min_free:.2f} GiB")

    max_bytes = int(float(ml["hard_caps"]["max_download_mib"]) * 1024.0 * 1024.0)
    with fc_path.open("r", encoding="utf-8", newline="") as fh:
        exposures = list(csv.DictReader(fh))
    proj_bytes = sum(int(e["f1_bytes"]) for e in exposures)
    if proj_bytes > max_bytes:
        raise RuntimeError(f"Projected bytes {proj_bytes} exceed hard cap {max_bytes}")

    IN_DIR.mkdir(parents=True, exist_ok=True)
    receipt_written = False
    manifest_rows: list[dict[str, Any]] = []
    total_bytes = 0

    for idx, exp in enumerate(exposures, start=1):
        inst = str(exp["instrument"])
        rel_path = pathlib.Path(exp["f1_rel"])
        dest = IN_DIR / rel_path
        url = str(exp["f1_url"])

        if dest.is_file() and dest.stat().st_size > 256:
            sz = int(dest.stat().st_size)
        else:
            sz = _download_with_retry(url, dest)
        val_info = _validate_payload(dest, inst)
        f_sha = _sha256_file(dest)
        total_bytes += sz
        if total_bytes > max_bytes:
            raise RuntimeError(f"Cumulative download bytes {total_bytes} exceeded {max_bytes}")

        if not receipt_written:
            receipt = {
                "schema": "D097_FIRST_SCIENCE_DOWNLOAD_RECEIPT_V1",
                "phase_id": "D097",
                "method_lock_sha256": ml_sha,
                "locked_at_utc": lr["locked_at_utc"],
                "locked_at_unix": lr["locked_at_unix"],
                "first_download_utc": now_dt.isoformat(),
                "first_download_unix": round(now_unix, 3),
                "chronology_lag_seconds": round(lag, 3),
                "first_file_relpath": str(rel_path),
                "first_file_sha256": f_sha,
                "first_file_bytes": sz,
            }
            (WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json").write_text(
                json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
            )
            receipt_written = True

        manifest_rows.append({
            "index": idx,
            "instrument": inst,
            "canonical_target": exp["canonical_target"],
            "dp_id": exp["dp_id"],
            "local_relpath": str(rel_path),
            "bytes": sz,
            "sha256": f_sha,
            **val_info,
        })
        if idx % 10 == 0 or idx == len(exposures):
            print(f"[{idx}/{len(exposures)}] {rel_path} -> {sz} B ({total_bytes / 1048576.0:.2f} MiB)")

    post_free_gib = shutil.disk_usage(ROOT).free / (1024.0 ** 3)
    manifest = {
        "schema": "D097_FULL_INPUT_MANIFEST_V1",
        "phase_id": "D097",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "n_files": len(manifest_rows),
        "total_bytes": total_bytes,
        "total_mib": round(total_bytes / 1048576.0, 4),
        "post_download_free_gib": round(post_free_gib, 3),
        "method_lock_sha256": ml_sha,
        "files": manifest_rows,
    }
    (WS / "FULL_D097_INPUT_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Downloaded/verified {len(manifest_rows)} files = {manifest['total_mib']:.3f} MiB (free={post_free_gib:.2f} GiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
