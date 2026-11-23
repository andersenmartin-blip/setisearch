#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Stage-2 Downloader & FITS Validator for Phase D103 (V6.1):
  1. Verifies Stage-1 Method Lock Integrity (hash + chronology lag >= 10 s + pre-download guard).
  2. Emits FIRST_SCIENCE_DOWNLOAD_RECEIPT.json BEFORE writing any science bytes to $RAW103.
  3. Downloads NuSTAR (FPMA+FPMB A01/B01 .evt.gz), XMM-Newton RGS (R1/R2 SR+BG .FTZ),
     ALMA Band 9/10 SODA cutouts (with full-cube <=85MB fallback if SODA transiently fails),
     and ESO ESPRESSO/HARPS 1D spectra.
  4. Validates 100% of downloaded FITS structures & emits FULL_D103_INPUT_MANIFEST.json.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from astropy.io import fits
import numpy as np

WS = Path(__file__).resolve().parent
ROOT = WS.parent.parent
RAW_DIR = ROOT / "inputs_d103_v6_1"


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _validate_single_file(path: Path, inst: str, role: str = "PRIMARY") -> tuple[bool, str]:
    if not path.exists() or path.stat().st_size < 1024:
        return False, "missing_or_tiny"
    head = path.read_bytes()[:8]
    if not (head.startswith(b"SIMPLE") or head[:2] == b"\x1f\x8b"):
        return False, f"not_fits_or_gz:{head[:16]!r}"
    try:
        with fits.open(path, memmap=False) as hdul:
            if inst == "NUSTAR_FPMA_FPMB":
                hdu = hdul["EVENTS"] if "EVENTS" in hdul else hdul[1]
                tbl = hdu.data
                cols = {c.upper() for c in tbl.names}
                need = {"PI", "X", "Y", "TIME"}
                if not need.issubset(cols) or len(tbl) < 100:
                    return False, f"bad_nustar_cols:{sorted(cols)}:rows={len(tbl)}"
                return True, f"nustar_{role}:rows={len(tbl)}"
            if inst == "XMM_RGS":
                hdu = hdul["SPECTRUM"] if "SPECTRUM" in hdul else hdul[1]
                tbl = hdu.data
                cols = {c.upper() for c in tbl.names}
                need = {"CHANNEL", "COUNTS"}
                has_backscal = ("BACKSCAL" in cols) or ("BACKSCAL" in hdu.header)
                if not need.issubset(cols) or not has_backscal or len(tbl) < 1000:
                    return False, f"bad_xmm_rgs_cols:{sorted(cols)}:backscal={has_backscal}:rows={len(tbl)}"
                return True, f"xmm_rgs_{role}:rows={len(tbl)}"
            if inst.startswith("ALMA_"):
                hdu = next((h for h in hdul if h.data is not None and h.data.ndim >= 3), None)
                if hdu is None:
                    return False, "no_3d_hdu"
                shape = tuple(int(x) for x in hdu.data.shape)
                if shape[-3] < 16 or int(np.sum(np.isfinite(hdu.data))) < 100:
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


def _fetch_file(url: str, dest: Path, inst: str, role: str, fallback_urls: list[str] | None = None) -> tuple[bool, str, str]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        ok, info = _validate_single_file(dest, inst, role)
        if ok:
            return True, f"CACHED:{info}", url
        dest.unlink(missing_ok=True)

    urls_to_try = [url] + (fallback_urls or [])
    last_err = ""
    for try_url in urls_to_try:
        for attempt in range(4):
            try:
                req = urllib.request.Request(try_url, headers={"User-Agent": "Mozilla/5.0 (compatible; SETI-D103-Pipeline/6.1)"})
                tmp = dest.with_suffix(dest.suffix + ".part")
                with urllib.request.urlopen(req, timeout=180 if inst.startswith("ALMA_") else 90) as resp:
                    if resp.status >= 400:
                        raise RuntimeError(f"HTTP_{resp.status}")
                    with tmp.open("wb") as out:
                        while True:
                            blk = resp.read(262144)
                            if not blk:
                                break
                            out.write(blk)
                tmp.replace(dest)
                ok, info = _validate_single_file(dest, inst, role)
                if ok:
                    return True, info, try_url
                last_err = info
                dest.unlink(missing_ok=True)
            except Exception as exc:
                last_err = f"{type(exc).__name__}:{exc}"
                if "HTTP Error 404" in last_err:
                    break
            time.sleep(1.5 * (attempt + 1))
    return False, last_err, urls_to_try[-1]


def _download_row(row: dict[str, Any]) -> dict[str, Any]:
    inst = row["instrument"]
    dp_id = row["dp_id"]
    rel1 = row["f1_rel"]
    url1 = row["f1_url"]
    fb1: list[str] = []
    if inst.startswith("ALMA_") and int(row.get("f1_bytes") or 0) <= 85_000_000:
        fb1.append(f"https://almascience.eso.org/dataPortal/{urllib.parse.quote(dp_id)}")

    role1 = "FPMA" if inst == "NUSTAR_FPMA_FPMB" else ("R1_SR" if inst == "XMM_RGS" else "PRIMARY")
    dest1 = RAW_DIR / rel1
    ok1, info1, used_u1 = _fetch_file(url1, dest1, inst, role1, fallback_urls=fb1)

    file_records: list[dict[str, Any]] = []
    tot_b = 0
    if ok1:
        b1 = dest1.stat().st_size
        tot_b += b1
        file_records.append({"role": role1, "rel_path": rel1, "url": used_u1, "bytes": b1, "sha256": _sha256_file(dest1), "info": info1})
    else:
        return {"status": "FAILED", "dp_id": dp_id, "instrument": inst, "star": row["canonical_target"],
                "rel_path": rel1, "url": used_u1, "bytes": 0, "sha256": "", "error": info1, "files": []}

    extras = json.loads(row.get("extra_files") or "[]")
    all_infos = [info1]
    for ex in extras:
        erel, eurl, erole = ex["rel"], ex["url"], ex["role"]
        edest = RAW_DIR / erel
        okx, infox, used_ux = _fetch_file(eurl, edest, inst, erole)
        if not okx:
            return {"status": "FAILED", "dp_id": dp_id, "instrument": inst, "star": row["canonical_target"],
                    "rel_path": erel, "url": used_ux, "bytes": 0, "sha256": "", "error": f"{erole}:{infox}", "files": file_records}
        bx = edest.stat().st_size
        tot_b += bx
        all_infos.append(infox)
        file_records.append({"role": erole, "rel_path": erel, "url": used_ux, "bytes": bx, "sha256": _sha256_file(edest), "info": infox})

    st = "CACHED" if all(i.startswith("CACHED:") for i in all_infos) else "DOWNLOADED"
    return {
        "status": st,
        "dp_id": dp_id,
        "instrument": inst,
        "star": row["canonical_target"],
        "rel_path": rel1,
        "url": used_u1,
        "bytes": tot_b,
        "sha256": file_records[0]["sha256"],
        "info": ";".join(all_infos),
        "files": file_records,
    }


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

    wait_s = 10.5 - (time.time() - float(lr["locked_unix_epoch"]))
    if wait_s > 0.0:
        print(f"Waiting {wait_s:.2f} s to guarantee >= 10 s Stage-1 -> Stage-2 chronology gap...")
        time.sleep(wait_s)

    first_utc = dt.datetime.now(tz=dt.timezone.utc)
    fdr_path = WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json"
    fdr_out = {
        "schema": "D103_FIRST_SCIENCE_DOWNLOAD_RECEIPT",
        "phase_id": "D103",
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
    with (WS / "FROZEN_COHORT_D103.csv").open() as f:
        rows = list(csv.DictReader(f))

    fast_rows = [r for r in rows if not r["instrument"].startswith("ESO_") and not r["instrument"].startswith("ALMA_")]
    alma_rows = [r for r in rows if r["instrument"].startswith("ALMA_")]
    eso_rows = [r for r in rows if r["instrument"].startswith("ESO_")]

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for res in pool.map(_download_row, fast_rows):
            results.append(res)
            print(f"  [{len(results):3d}/{len(rows)}] {res['status']:10s} {res['instrument']:16s} {res['star']:14s} {res.get('info') or res.get('error','')}", flush=True)

    with ThreadPoolExecutor(max_workers=3) as pool:
        for res in pool.map(_download_row, alma_rows):
            results.append(res)
            print(f"  [{len(results):3d}/{len(rows)}] {res['status']:10s} {res['instrument']:16s} {res['star']:14s} {res.get('info') or res.get('error','')}", flush=True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        for res in pool.map(_download_row, eso_rows):
            results.append(res)
            print(f"  [{len(results):3d}/{len(rows)}] {res['status']:10s} {res['instrument']:16s} {res['star']:14s} {res.get('info') or res.get('error','')}", flush=True)

    ok_res = [r for r in results if r["status"] in ("DOWNLOADED", "CACHED")]
    err_res = [r for r in results if r["status"] == "FAILED"]
    tot_b = sum(int(r["bytes"]) for r in ok_res)
    tot_phys = sum(len(r.get("files", [])) for r in ok_res)

    manifest = {
        "schema": "D103_FULL_INPUT_MANIFEST",
        "phase_id": "D103",
        "downloaded_utc": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        "raw_dir": str(RAW_DIR),
        "expected_observations": len(rows),
        "valid_observations": len(ok_res),
        "failed_observations": len(err_res),
        "valid_physical_files": tot_phys,
        "total_bytes": tot_b,
        "total_mib": round(tot_b / (1024.0 * 1024.0), 4),
        "errors": err_res,
        "observations": results,
    }
    (WS / "FULL_D103_INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Stage-2 download summary: {len(ok_res)}/{len(rows)} valid obs ({tot_phys} files, {len(err_res)} failed), {manifest['total_mib']:.2f} MiB")
    assert len(ok_res) == len(rows) or len(ok_res) >= 0.90 * len(rows), f"Too many download failures: {len(err_res)}/{len(rows)}"
    return 0 if not err_res else 1


if __name__ == "__main__":
    raise SystemExit(main())
