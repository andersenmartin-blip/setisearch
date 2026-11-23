#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D101 Science Input Downloader (`V5.9`)
Enforces strict Stage-1 prospective chronology (>= 3.0s after LOCK_RECEIPT.json),
downloads 63 anonymous IVOA ALMA SODA 3D spectral cube cutouts (Bands 1/3/4/5) +
39 ESO Phase-3 1D optical high-resolution spectra (ESPRESSO + HARPS), validates FITS
structure and bounds, and seals FULL_D101_INPUT_MANIFEST.json.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from astropy.io import fits
import numpy as np

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_v5_9_20261123_d101_alma_mm_band1_gap_closure_drifting_comb"
IN_DIR = ROOT / "inputs_d101_v5_9"
COHORT_CSV = WS / "FROZEN_COHORT_D101.csv"
LOCK_RECEIPT_PATH = WS / "LOCK_RECEIPT.json"
FIRST_RECEIPT_PATH = WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json"
MANIFEST_PATH = WS / "FULL_D101_INPUT_MANIFEST.json"
MAX_RAW_DOWNLOAD_MIB = 1200.0
USER_AGENT = "AntigravitySETI/5.9 (mailto:research@seti-survey.invalid)"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _http_fetch(url: str, timeout: int = 120, max_retries: int = 4) -> bytes:
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (2 ** attempt))
    raise RuntimeError(f"Download failed after {max_retries} attempts for {url}: {last_err}")


def _validate_fits_bytes(raw: bytes, is_alma: bool) -> dict[str, Any]:
    if not raw[:6].startswith(b"SIMPLE"):
        raise ValueError(f"Not a FITS file (magic={raw[:16]!r})")
    import io
    with fits.open(io.BytesIO(raw), memmap=False) as hdul:
        if is_alma:
            data = None
            hdr = None
            for hdu in hdul:
                if hdu.data is not None and hdu.data.ndim >= 3:
                    data = hdu.data
                    hdr = hdu.header
                    break
            if data is None or hdr is None:
                raise ValueError("ALMA FITS contains no >=3D cube HDU")
            arr = data[0] if data.ndim == 4 else data
            if arr.shape[0] < 12 or arr.shape[1] < 4 or arr.shape[2] < 4:
                raise ValueError(f"ALMA cube too small: shape={data.shape}")
            fin_frac = float(np.mean(np.isfinite(arr)))
            return {
                "shape": list(data.shape),
                "finite_frac": round(fin_frac, 4),
                "crval3": float(hdr.get("CRVAL3", 0.0) or 0.0),
                "cdelt3": float(hdr.get("CDELT3", 0.0) or 0.0),
            }
        # ESO Phase-3 1D tabular spectrum
        if len(hdul) < 2 or hdul[1].data is None:
            raise ValueError("ESO FITS missing binary table HDU 1")
        tbl = hdul[1].data
        cols = [c.upper() for c in tbl.names]
        if "WAVE" not in cols or ("FLUX" not in cols and "FLUX_REDUCED" not in cols):
            raise ValueError(f"ESO FITS missing WAVE/FLUX columns: {cols}")
        w = np.asarray(tbl["WAVE"]).ravel()
        return {"n_wave": int(len(w)), "w_min_a": round(float(np.nanmin(w)), 3), "w_max_a": round(float(np.nanmax(w)), 3)}


def _download_one(row: dict[str, str]) -> dict[str, Any]:
    inst = row["instrument"]
    is_alma = inst.startswith("ALMA_")
    rel_path = row["f1_rel"]
    dest = IN_DIR / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = row["f1_url"]

    raw: bytes | None = None
    used_url = url
    if dest.exists() and dest.stat().st_size > 4096:
        raw = dest.read_bytes()
        try:
            meta = _validate_fits_bytes(raw, is_alma)
            return {
                "dp_id": row["dp_id"],
                "canonical_target": row["canonical_target"],
                "instrument": inst,
                "rel_path": rel_path,
                "url": used_url,
                "bytes": len(raw),
                "sha256": _sha256_bytes(raw),
                "validated": meta,
                "status": "CACHED",
            }
        except Exception:
            raw = None

    urls_to_try = [url]
    if is_alma:
        ra = float(row["s_ra"])
        dec = float(row["s_dec"])
        fid = urllib.parse.quote(row["f1_id"])
        # Fallback wider cutout radii if tight cutout clips beam, then DataPortal direct if <= 60 MiB
        urls_to_try.append(f"https://almascience.eso.org/soda/sync?ID={fid}&CIRCLE={ra:.6f}%20{dec:.6f}%20{0.0025:.7f}")
        urls_to_try.append(f"https://almascience.eso.org/soda/sync?ID={fid}&CIRCLE={ra:.6f}%20{dec:.6f}%20{0.0055:.7f}")

    last_err: Exception | None = None
    for idx_u, cand_url in enumerate(urls_to_try):
        try:
            raw_try = _http_fetch(cand_url, timeout=140 if is_alma else 90, max_retries=3)
            meta = _validate_fits_bytes(raw_try, is_alma)
            raw = raw_try
            used_url = cand_url
            break
        except Exception as exc:
            last_err = exc
            if idx_u == len(urls_to_try) - 1 and is_alma:
                dp_url = f"https://almascience.eso.org/dataPortal/{urllib.parse.quote(row['f1_id'])}"
                try:
                    req = urllib.request.Request(dp_url, method="HEAD", headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=30) as hresp:
                        clen = int(hresp.headers.get("Content-Length", "999999999") or "999999999")
                    if clen <= 65 * 1024 * 1024:
                        raw_try = _http_fetch(dp_url, timeout=180, max_retries=2)
                        meta = _validate_fits_bytes(raw_try, is_alma)
                        raw = raw_try
                        used_url = dp_url
                        break
                except Exception as exc2:
                    last_err = exc2

    if raw is None:
        raise RuntimeError(f"Failed downloading/validating {row['dp_id']} ({row['canonical_target']}): {last_err}")

    dest.write_bytes(raw)
    return {
        "dp_id": row["dp_id"],
        "canonical_target": row["canonical_target"],
        "instrument": inst,
        "rel_path": rel_path,
        "url": used_url,
        "bytes": len(raw),
        "sha256": _sha256_bytes(raw),
        "validated": meta,
        "status": "DOWNLOADED",
    }


def main() -> int:
    if not LOCK_RECEIPT_PATH.exists() or not COHORT_CSV.exists():
        print("CRITICAL: Stage-1 lock or cohort CSV missing; run build_cohort.py first.", file=sys.stderr)
        return 1
    receipt = json.loads(LOCK_RECEIPT_PATH.read_text())
    locked_epoch = float(receipt["locked_unix_epoch"])
    now_epoch = time.time()
    lag_s = now_epoch - locked_epoch
    if lag_s < 3.0:
        print(f"CRITICAL: Chronology lag too small ({lag_s:.3f}s < 3.0s). Wait before downloading.", file=sys.stderr)
        return 1

    IN_DIR.mkdir(parents=True, exist_ok=True)
    if not FIRST_RECEIPT_PATH.exists():
        first_rec = {
            "schema": "D101_FIRST_SCIENCE_DOWNLOAD_RECEIPT",
            "phase_id": "D101",
            "locked_unix_epoch": locked_epoch,
            "first_download_unix_epoch": round(now_epoch, 4),
            "first_download_utc": dt.datetime.fromtimestamp(now_epoch, tz=dt.timezone.utc).isoformat(),
            "chronology_lag_seconds": round(lag_s, 4),
            "raw_input_dir": str(IN_DIR),
        }
        FIRST_RECEIPT_PATH.write_text(json.dumps(first_rec, indent=2) + "\n")
    else:
        first_rec = json.loads(FIRST_RECEIPT_PATH.read_text())

    with COHORT_CSV.open() as f:
        rows = list(csv.DictReader(f))

    alma_rows = [r for r in rows if r["instrument"].startswith("ALMA_")]
    eso_rows = [r for r in rows if r["instrument"].startswith("ESO_")]
    print(f"Phase D101 Download Starting (lag={lag_s:.2f}s): {len(alma_rows)} ALMA SODA cubes + {len(eso_rows)} ESO Phase-3 spectra")

    results: list[dict[str, Any]] = []
    errors: list[str] = []

    # Parallel download for ALMA SODA cutouts (anonymous IVOA SODA, 6 workers)
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(_download_one, r): r for r in alma_rows}
        for i, fut in enumerate(as_completed(futs), 1):
            r = futs[fut]
            try:
                res = fut.result()
                results.append(res)
                if i % 10 == 0 or i == len(alma_rows):
                    print(f"  ALMA [{i}/{len(alma_rows)}] {r['canonical_target']} {res['bytes']/1024:.1f} KiB ({res['status']})")
            except Exception as exc:
                msg = f"ALMA ERR {r['canonical_target']} {r['dp_id']}: {exc}"
                print(" ", msg, file=sys.stderr)
                errors.append(msg)

    # Sequential polite download for ESO Phase-3 spectra
    for i, r in enumerate(eso_rows, 1):
        try:
            res = _download_one(r)
            results.append(res)
            if i % 10 == 0 or i == len(eso_rows):
                print(f"  ESO  [{i}/{len(eso_rows)}] {r['canonical_target']} {res['bytes']/1024:.1f} KiB ({res['status']})")
            time.sleep(0.12)
        except Exception as exc:
            msg = f"ESO ERR {r['canonical_target']} {r['dp_id']}: {exc}"
            print(" ", msg, file=sys.stderr)
            errors.append(msg)

    results.sort(key=lambda x: x["rel_path"])
    total_bytes = sum(x["bytes"] for x in results)
    total_mib = total_bytes / (1024.0 * 1024.0)
    if total_mib > MAX_RAW_DOWNLOAD_MIB:
        print(f"WARNING: Raw download {total_mib:.2f} MiB exceeds soft cap {MAX_RAW_DOWNLOAD_MIB:.1f} MiB", file=sys.stderr)

    manifest = {
        "schema": "D101_FULL_INPUT_MANIFEST",
        "phase_id": "D101",
        "generated_utc": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        "chronology_lag_seconds": first_rec["chronology_lag_seconds"],
        "expected_files": len(rows),
        "downloaded_valid_files": len(results),
        "error_count": len(errors),
        "errors": errors,
        "total_bytes": int(total_bytes),
        "total_mib": round(total_mib, 4),
        "files": results,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Download finished: {len(results)}/{len(rows)} valid FITS, {total_mib:.2f} MiB, errors={len(errors)}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
