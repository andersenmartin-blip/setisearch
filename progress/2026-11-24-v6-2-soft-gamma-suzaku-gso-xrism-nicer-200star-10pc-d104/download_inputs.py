#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D104 (`V6.2`) Stage-2 Verified Downloader & File-Integrity Validator.
Verifies all Stage-1 SHA-256 locks, records `FIRST_SCIENCE_DOWNLOAD_RECEIPT.json`
(>= 10 s after Stage-1 seal), downloads all 104 verified observations into `$RAW104`,
validates every FITS extension & schema, and emits `FULL_D104_INPUT_MANIFEST.json`.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from astropy.io import fits

WS = Path(__file__).resolve().parent
ROOT = WS.parent.parent
RAW_DIR = ROOT / "inputs_d104_v6_2"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _verify_stage1_locks() -> tuple[dict[str, Any], float, str]:
    method_path = WS / "METHOD_LOCK.json"
    receipt_path = WS / "LOCK_RECEIPT.json"
    if not method_path.exists() or not receipt_path.exists():
        raise RuntimeError("Stage-1 METHOD_LOCK.json or LOCK_RECEIPT.json missing!")
    ml = json.loads(method_path.read_text(encoding="utf-8"))
    lr = json.loads(receipt_path.read_text(encoding="utf-8"))
    ml_sha = _sha256_file(method_path)
    if ml_sha != lr.get("method_lock_sha256"):
        raise RuntimeError("METHOD_LOCK.json SHA-256 mismatch vs LOCK_RECEIPT.json!")
    for fn, exp_sha in ml["stage_1_files"].items():
        fp = WS / fn
        if not fp.exists():
            raise RuntimeError(f"Stage-1 locked file missing: {fn}")
        got = _sha256_file(fp)
        if got != exp_sha:
            raise RuntimeError(f"Stage-1 file modified after lock: {fn} ({got} != {exp_sha})")
    return ml, float(lr["locked_unix_epoch"]), ml_sha


def _download_with_retry(url: str, dest: Path, expected_bytes: int = 0) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    if dest.exists() and dest.stat().st_size > 1000:
        if expected_bytes <= 0 or dest.stat().st_size == expected_bytes:
            return int(dest.stat().st_size)

    last_err: Exception | None = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "SETI-V6.2-D104-Science-Pipeline/1.0"},
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                with open(tmp, "wb") as out:
                    while chunk := resp.read(1 << 18):
                        out.write(chunk)
            size = int(tmp.stat().st_size)
            if size < 1000:
                raise IOError(f"Truncated response ({size} B) for {url}")
            if expected_bytes > 0 and abs(size - expected_bytes) > 64:
                raise IOError(f"Size mismatch for {url}: got {size}, expected {expected_bytes}")
            os.replace(tmp, dest)
            return size
        except Exception as exc:
            last_err = exc
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"Failed download after 5 tries ({url}): {last_err}")


def _validate_fits(path: Path, inst: str) -> str:
    if path.name.endswith(".gz"):
        with gzip.open(path, "rb") as gz:
            head = gz.read(2880)
        if not head.startswith(b"SIMPLE"):
            raise ValueError(f"Invalid gzipped FITS signature: {path}")

    with fits.open(path, memmap=True) as hdul:
        if inst == "SUZAKU_HXD_GSO":
            h1 = hdul["EVENTS"] if "EVENTS" in hdul else hdul[1]
            cols = set(h1.columns.names)
            if not {"PI_SLOW", "UNITID"}.issubset(cols):
                raise ValueError(f"Suzaku GSO missing PI_SLOW/UNITID in {path.name}: {cols}")
            expt = float(h1.header.get("EXPOSURE", hdul[0].header.get("EXPOSURE", 0.0)) or 0.0)
            if expt <= 0.0:
                raise ValueError(f"Suzaku GSO non-positive EXPOSURE in {path.name}")
            return f"suzaku_gso:rows={len(h1.data)};exp={expt:.1f}"

        if inst == "XRISM_RESOLVE":
            h1 = hdul["EVENTS"] if "EVENTS" in hdul else hdul[1]
            filt = str(h1.header.get("FILTER", hdul[0].header.get("FILTER", "")) or "").strip().upper()
            if filt != "OPEN":
                raise ValueError(f"XRISM Resolve non-OPEN filter={filt} in {path.name}")
            cols = set(h1.columns.names)
            if not {"PIXEL", "ITYPE"}.issubset(cols):
                raise ValueError(f"XRISM Resolve missing PIXEL/ITYPE in {path.name}: {cols}")
            expt = float(h1.header.get("EXPOSURE", hdul[0].header.get("EXPOSURE", 0.0)) or 0.0)
            return f"xrism_resolve:rows={len(h1.data)};filter={filt};exp={expt:.1f}"

        if inst == "NICER_XTI":
            h1 = hdul["EVENTS"] if "EVENTS" in hdul else hdul[1]
            cols = set(h1.columns.names)
            if not {"PI", "DET_ID"}.issubset(cols):
                raise ValueError(f"NICER XTI missing PI/DET_ID in {path.name}: {cols}")
            expt = float(h1.header.get("EXPOSURE", hdul[0].header.get("EXPOSURE", 0.0)) or 0.0)
            return f"nicer_xti:rows={len(h1.data)};exp={expt:.1f}"

        if inst == "CARMENES_VIS":
            if len(hdul) < 5 or hdul[1].data is None or hdul[3].data is None or hdul[4].data is None:
                raise ValueError(f"CARMENES VIS invalid extensions in {path.name}")
            return f"carmenes_vis:shape={hdul[1].data.shape}"

        if inst in ("ESO_ESPRESSO", "ESO_HARPS"):
            if len(hdul) < 2 or hdul[1].data is None:
                raise ValueError(f"ESO 1D spectrum missing ext[1] in {path.name}")
            return f"{inst.lower()}:rows={len(hdul[1].data)}"

        raise ValueError(f"Unknown instrument {inst}")


def _process_row(row: dict[str, str]) -> dict[str, Any]:
    inst = row["instrument"]
    dp_id = row["dp_id"]
    star = row["canonical_target"]
    rel = row["f1_rel"]
    url = row["f1_url"]
    exp_bytes = int(row.get("f1_bytes") or 0)
    dest = RAW_DIR / rel
    sz = _download_with_retry(url, dest, expected_bytes=exp_bytes)
    info = _validate_fits(dest, inst)
    sha = _sha256_file(dest)
    return {
        "status": "DOWNLOADED",
        "dp_id": dp_id,
        "instrument": inst,
        "star": star,
        "rel_path": rel,
        "url": url,
        "bytes": sz,
        "sha256": sha,
        "info": info,
        "files": [
            {
                "role": "PRIMARY",
                "rel_path": rel,
                "url": url,
                "bytes": sz,
                "sha256": sha,
            }
        ],
    }


def main() -> None:
    ml, lock_epoch, ml_sha = _verify_stage1_locks()
    now_epoch = time.time()
    lag = now_epoch - lock_epoch
    if lag < 10.2:
        wait_s = 10.5 - lag
        print(f"Respecting >= 10 s Stage-1 chronology separation: sleeping {wait_s:.2f} s...")
        time.sleep(wait_s)

    first_epoch = time.time()
    receipt = {
        "schema": "D104_FIRST_SCIENCE_DOWNLOAD_RECEIPT",
        "phase_id": "D104",
        "locked_utc": ml["locked_utc"],
        "locked_unix_epoch": round(lock_epoch, 4),
        "first_download_utc": datetime.fromtimestamp(first_epoch, tz=timezone.utc).isoformat(),
        "first_download_unix_epoch": round(first_epoch, 4),
        "chronology_lag_seconds": round(first_epoch - lock_epoch, 3),
        "method_lock_sha256": ml_sha,
    }
    if receipt["chronology_lag_seconds"] < 10.0:
        raise RuntimeError(f"Chronology lag {receipt['chronology_lag_seconds']} s < 10.0 s!")
    (WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    with open(WS / "FROZEN_COHORT_D104.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 104:
        raise RuntimeError(f"Expected 104 cohort rows, got {len(rows)}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        fut_map = {ex.submit(_process_row, r): r for r in rows}
        for i, fut in enumerate(as_completed(fut_map), 1):
            r = fut_map[fut]
            try:
                rec = fut.result()
                results.append(rec)
                if i % 10 == 0 or i == len(rows):
                    print(f"[{i}/{len(rows)}] {rec['instrument']} {rec['star']} OK ({rec['bytes']:,} B)")
            except Exception as exc:
                errors.append({"dp_id": r["dp_id"], "star": r["canonical_target"], "error": str(exc)})
                print(f"[ERR] {r['dp_id']} ({r['canonical_target']}): {exc}")

    results.sort(key=lambda x: (x["instrument"], x["star"], x["dp_id"]))
    tot_bytes = sum(int(r["bytes"]) for r in results)
    manifest = {
        "schema": "D104_FULL_INPUT_MANIFEST",
        "phase_id": "D104",
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "raw_dir": str(RAW_DIR),
        "expected_observations": len(rows),
        "valid_observations": len(results),
        "failed_observations": len(errors),
        "valid_physical_files": sum(len(r["files"]) for r in results),
        "total_bytes": tot_bytes,
        "total_mib": round(tot_bytes / (1024.0 * 1024.0), 4),
        "errors": errors,
        "observations": results,
    }
    (WS / "FULL_D104_INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest written: valid={len(results)}/{len(rows)}, failed={len(errors)}, total={manifest['total_mib']:.2f} MiB")
    if errors or len(results) != len(rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
