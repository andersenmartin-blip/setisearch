#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Stage-2 Downloader & FITS Validator for Phase D102 (V6.0):
  1. Verifies Stage-1 Method Lock Integrity (hash + chronology lag >= 10 s + pre-download guard).
  2. Emits FIRST_SCIENCE_DOWNLOAD_RECEIPT.json BEFORE downloading science bytes.
  3. Downloads Chandra pha2.fits.gz, EUVE *_vo.fits, ALMA SODA cutouts, and ESO 1D FITS.
  4. Validates every FITS structure & emits FULL_D102_INPUT_MANIFEST.json.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from astropy.io import fits
import numpy as np

WS = Path(__file__).resolve().parent
ROOT = WS.parent.parent
RAW_DIR = ROOT / "inputs_d102_v6_0"


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _validate_fits_file(path: Path, inst: str) -> tuple[bool, str]:
    if not path.exists() or path.stat().st_size < 1024:
        return False, "missing_or_tiny"
    head = path.read_bytes()[:8]
    if not (head.startswith(b"SIMPLE") or head[:2] == b"\x1f\x8b"):
        return False, f"not_fits_or_gz:{head[:16]!r}"
    try:
        with fits.open(path, memmap=False) as hdul:
            if inst.startswith("CHANDRA_"):
                hdu = hdul["SPECTRUM"] if "SPECTRUM" in hdul else hdul[1]
                tbl = hdu.data
                cols = {c.upper() for c in tbl.names}
                need = {"TG_PART", "TG_M", "BIN_LO", "BIN_HI", "COUNTS"}
                if not need.issubset(cols) or len(tbl) < 2:
                    return False, f"bad_chandra_pha2_cols:{sorted(cols)}:rows={len(tbl)}"
                return True, f"chandra_ok:rows={len(tbl)}"
            if inst == "EUVE_DS_S":
                tbl = hdul[1].data
                cols = {c.upper(): c for c in tbl.names}
                if "WAVE" not in cols or "FLUX" not in cols:
                    return False, f"bad_euve_cols:{list(cols.keys())}"
                w = np.asarray(tbl[cols["WAVE"]], dtype=np.float64).ravel()
                f = np.asarray(tbl[cols["FLUX"]], dtype=np.float64).ravel()
                if len(w) < 1000 or int(np.sum(np.isfinite(f))) < 1000:
                    return False, f"short_euve:{len(w)}"
                return True, f"euve_ok:len={len(w)}"
            if inst.startswith("ALMA_"):
                hdu = next((h for h in hdul if h.data is not None and h.data.ndim >= 3), None)
                if hdu is None:
                    return False, "no_3d_hdu"
                shape = tuple(int(x) for x in hdu.data.shape)
                n_chan = shape[-3]
                if n_chan < 16 or int(np.sum(np.isfinite(hdu.data))) < 100:
                    return False, f"empty_cube:{shape}"
                return True, f"alma_ok:shape={shape}"
            tbl = hdul[1].data
            cols = {c.upper(): c for c in tbl.names}
            if "WAVE" not in cols or "FLUX" not in cols:
                return False, f"bad_eso_cols:{list(cols.keys())}"
            w = np.asarray(tbl[cols["WAVE"]], dtype=np.float64).ravel()
            fl = np.asarray(tbl[cols["FLUX"]], dtype=np.float64).ravel()
            if len(w) < 10000 or int(np.sum(np.isfinite(fl))) < 5000:
                return False, f"short_eso:{len(w)}"
            return True, f"eso_ok:len={len(w)}"
    except Exception as exc:
        return False, f"fits_exc:{type(exc).__name__}:{exc}"


def _download_one(row: dict[str, Any]) -> dict[str, Any]:
    inst = row["instrument"]
    dp_id = row["dp_id"]
    rel = row["f1_rel"]
    url = row["f1_url"]
    dest = RAW_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        ok, info = _validate_fits_file(dest, inst)
        if ok:
            return {"status": "CACHED", "dp_id": dp_id, "instrument": inst, "star": row["canonical_target"],
                    "rel_path": rel, "url": url, "bytes": dest.stat().st_size, "sha256": _sha256_file(dest), "info": info}
        dest.unlink(missing_ok=True)

    last_err = ""
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; SETI-D102-Pipeline/6.0)"})
            tmp = dest.with_suffix(dest.suffix + ".part")
            with urllib.request.urlopen(req, timeout=90) as resp:
                if resp.status >= 400:
                    raise RuntimeError(f"HTTP_{resp.status}")
                with tmp.open("wb") as out:
                    while True:
                        blk = resp.read(262144)
                        if not blk:
                            break
                        out.write(blk)
            tmp.replace(dest)
            ok, info = _validate_fits_file(dest, inst)
            if ok:
                return {"status": "DOWNLOADED", "dp_id": dp_id, "instrument": inst, "star": row["canonical_target"],
                        "rel_path": rel, "url": url, "bytes": dest.stat().st_size, "sha256": _sha256_file(dest), "info": info}
            last_err = info
            dest.unlink(missing_ok=True)
        except Exception as exc:
            last_err = f"{type(exc).__name__}:{exc}"
            if "HTTP Error 400" in last_err or "HTTP Error 404" in last_err:
                break
        time.sleep(1.5 * (attempt + 1))

    return {"status": "FAILED", "dp_id": dp_id, "instrument": inst, "star": row["canonical_target"],
            "rel_path": rel, "url": url, "bytes": 0, "sha256": "", "error": last_err}


def main() -> int:
    lr_path = WS / "LOCK_RECEIPT.json"
    ml_path = WS / "METHOD_LOCK.json"
    assert lr_path.exists() and ml_path.exists(), "Run build_cohort.py to seal Stage 1 first!"
    lr = json.loads(lr_path.read_text())
    ml = json.loads(ml_path.read_text())
    assert lr["status"] == "STAGE-1 SEALED"
    assert lr["inputs_dir_exists_at_seal"] is False
    assert _sha256_file(ml_path) == lr["method_lock_sha256"]
    for fn, exp_sha in ml["stage_1_files"].items():
        act = _sha256_file(WS / fn)
        assert act == exp_sha, f"Stage-1 integrity drift on {fn}: {act} != {exp_sha}"

    wait_s = 10.2 - (time.time() - float(lr["locked_unix_epoch"]))
    if wait_s > 0.0:
        print(f"Waiting {wait_s:.2f} s to guarantee >= 10 s Stage-1 -> Stage-2 chronology gap...")
        time.sleep(wait_s)

    first_utc = dt.datetime.now(tz=dt.timezone.utc)
    fdr_path = WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json"
    fdr_out = {
        "schema": "D102_FIRST_SCIENCE_DOWNLOAD_RECEIPT",
        "phase_id": "D102",
        "locked_utc": lr["locked_utc"],
        "locked_unix_epoch": lr["locked_unix_epoch"],
        "first_download_utc": first_utc.isoformat(),
        "first_download_unix_epoch": round(first_utc.timestamp(), 4),
        "chronology_lag_seconds": round(first_utc.timestamp() - float(lr["locked_unix_epoch"]), 3),
        "method_lock_sha256": lr["method_lock_sha256"],
    }
    fdr_path.write_text(json.dumps(fdr_out, indent=2) + "\n")
    print(f"Chronology receipt written (lag = {fdr_out['chronology_lag_seconds']:.2f} s >= 10.0 s). Starting downloads...")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with (WS / "FROZEN_COHORT_D102.csv").open() as f:
        rows = list(csv.DictReader(f))

    # Threaded Chandra/EUVE/ALMA + polite 2-worker ESO
    fast_rows = [r for r in rows if not r["instrument"].startswith("ESO_")]
    eso_rows = [r for r in rows if r["instrument"].startswith("ESO_")]

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for res in pool.map(_download_one, fast_rows):
            results.append(res)
            print(f"  [{len(results):3d}/{len(rows)}] {res['status']:10s} {res['instrument']:14s} {res['star']:12s} {res.get('info') or res.get('error','')}", flush=True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        for res in pool.map(_download_one, eso_rows):
            results.append(res)
            print(f"  [{len(results):3d}/{len(rows)}] {res['status']:10s} {res['instrument']:14s} {res['star']:12s} {res.get('info') or res.get('error','')}", flush=True)

    ok_res = [r for r in results if r["status"] in ("DOWNLOADED", "CACHED")]
    err_res = [r for r in results if r["status"] == "FAILED"]
    tot_b = sum(int(r["bytes"]) for r in ok_res)

    manifest = {
        "schema": "D102_FULL_INPUT_MANIFEST",
        "phase_id": "D102",
        "downloaded_utc": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        "raw_dir": str(RAW_DIR),
        "expected_files": len(rows),
        "valid_files": len(ok_res),
        "failed_files": len(err_res),
        "total_bytes": tot_b,
        "total_mib": round(tot_b / (1024.0 * 1024.0), 4),
        "errors": err_res,
        "files": results,
    }
    (WS / "FULL_D102_INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Stage-2 download summary: {len(ok_res)}/{len(rows)} valid ({len(err_res)} failed), {manifest['total_mib']:.2f} MiB")
    assert len(ok_res) >= 0.90 * len(rows), f"Too many download failures: {len(err_res)}/{len(rows)}"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
