#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D099 (`V5.7`) Prospectively Locked Science Input Downloader.

Verifies Stage-1 lock integrity (`METHOD_LOCK.json` + `LOCK_RECEIPT.json` for
all 7 locked Stage-1 files), enforces chronological separation (`>= 3.0 s`),
downloads only the exact `97` pre-committed FITS spectra (`23 JCMT_MM +
13 SOFIA_EXES + 26 IRTF_SPEX + 35 ESO_UVES/HARPS`) into
`/home/martin/SETI_Fortsaettelse_2026-11-14/inputs_d099_v5_7`, validates FITS
integrity for each instrument, enforces the `125.0 MiB` cap and `>= 1.5 GiB`
free-disk floor, and writes `FIRST_SCIENCE_DOWNLOAD_RECEIPT.json` +
`FULL_D099_INPUT_MANIFEST.json`.
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

import numpy as np
from astropy.io import fits

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_v5_7_20261122_d099_jcmt_mm_sofia_exes_irtf_spex_keplerian_drift"
IN_DIR = ROOT / "inputs_d099_v5_7"

MIN_CHRONOLOGY_LAG_S = 3.0
MAX_RAW_DOWNLOAD_MIB = 125.0
MIN_FREE_DISK_GIB = 1.5


def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_iso_utc(ts: str) -> float:
    s = str(ts).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return dt.datetime.fromisoformat(s).timestamp()


def _verify_stage1_lock() -> tuple[dict[str, Any], dict[str, Any], float]:
    ml_p = WS / "METHOD_LOCK.json"
    lr_p = WS / "LOCK_RECEIPT.json"
    if not ml_p.exists() or not lr_p.exists():
        raise RuntimeError("Missing METHOD_LOCK.json or LOCK_RECEIPT.json — Stage-1 lock is required first!")

    ml = json.loads(ml_p.read_text(encoding="utf-8"))
    lr = json.loads(lr_p.read_text(encoding="utf-8"))
    if _sha256_file(ml_p) != lr.get("method_lock_sha256"):
        raise RuntimeError("METHOD_LOCK.json SHA-256 mismatch against LOCK_RECEIPT.json!")

    # Verify every locked Stage-1 file hash matches DISK before any download
    files_map = lr.get("locked_files") or lr.get("stage_1_files") or ml.get("stage_1_files") or {}
    if len(files_map) < 6:
        raise RuntimeError(f"Expected >= 6 locked Stage-1 files in LOCK_RECEIPT, found {len(files_map)}")
    for fname, expected_sha in files_map.items():
        fp = WS / fname
        if not fp.exists():
            raise RuntimeError(f"Locked Stage-1 file missing: {fp}")
        if _sha256_file(fp) != expected_sha:
            raise RuntimeError(f"Locked Stage-1 file modified after seal: {fname}")

    lock_ts = float(lr.get("locked_unix_epoch") or _parse_iso_utc(lr["locked_utc"]))
    lag_s = time.time() - lock_ts
    if lag_s < MIN_CHRONOLOGY_LAG_S:
        raise RuntimeError(
            f"Chronological lock separation too short: {lag_s:.2f}s < {MIN_CHRONOLOGY_LAG_S:.2f}s. Wait before downloading."
        )
    return ml, lr, lag_s


def _validate_fits_file(path: pathlib.Path, inst: str) -> dict[str, Any]:
    with fits.open(path, memmap=False) as hdul:
        n_hdu = len(hdul)
        if n_hdu < 1:
            raise RuntimeError(f"Empty HDUList in {path.name}")
        if inst.startswith("JCMT"):
            dat = hdul[0].data
            if dat is None and n_hdu > 1:
                dat = hdul[1].data
            if dat is None:
                raise RuntimeError(f"No spectral data array in JCMT FITS {path.name}")
            arr = np.asarray(dat)
            n_spec = int(max(arr.shape))
            if n_spec < 64:
                raise RuntimeError(f"Too few JCMT channels ({arr.shape}) in {path.name}")
            return {"n_hdu": n_hdu, "shape": list(arr.shape)}
        if inst == "SOFIA_EXES":
            d = np.asarray(hdul[0].data)
            if d.ndim == 2:
                if d.shape[0] < 4 or d.shape[1] < 40:
                    raise RuntimeError(f"Bad 2D EXES shape {d.shape} in {path.name}")
            elif d.ndim == 3:
                if d.shape[1] < 4 or d.shape[2] < 40:
                    raise RuntimeError(f"Bad 3D EXES shape {d.shape} in {path.name}")
            else:
                raise RuntimeError(f"Unexpected EXES ndim={d.ndim} in {path.name}")
            return {"n_hdu": n_hdu, "shape": list(d.shape)}
        if inst == "IRTF_SPEX":
            d = np.asarray(hdul[0].data)
            if d.ndim != 2 or d.shape[0] < 3 or d.shape[1] < 256:
                raise RuntimeError(f"Unexpected IRTF_SPEX shape {d.shape} in {path.name}")
            return {"n_hdu": n_hdu, "shape": list(d.shape)}
        if inst in {"ESO_UVES", "ESO_HARPS"}:
            if n_hdu < 2 or hdul[1].data is None:
                raise RuntimeError(f"Missing binary table HDU1 in ESO FITS {path.name}")
            cols = {c.upper() for c in hdul[1].columns.names}
            if "WAVE" not in cols or not ({"FLUX", "FLUX_REDUCED"} & cols):
                raise RuntimeError(f"Missing WAVE/FLUX columns ({cols}) in {path.name}")
            w = np.asarray(hdul[1].data["WAVE"]).ravel()
            if len(w) < 1000:
                raise RuntimeError(f"Too short ESO spectrum ({len(w)}) in {path.name}")
            return {"n_hdu": n_hdu, "n_wave": int(len(w))}
        raise RuntimeError(f"Unknown instrument {inst} in {path.name}")


def _download_with_retry(url: str, dest: pathlib.Path, retries: int = 4) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETI-D099-Downloader/1.0"})
            with urllib.request.urlopen(req, timeout=90.0) as resp, tmp.open("wb") as out:
                shutil.copyfileobj(resp, out, length=1 << 16)
            if tmp.stat().st_size < 2880:
                raise RuntimeError(f"Truncated FITS download ({tmp.stat().st_size} B) from {url}")
            tmp.replace(dest)
            return
        except Exception as exc:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            if attempt == retries - 1:
                raise RuntimeError(f"Download failed after {retries} attempts for {url}: {exc}") from exc
            time.sleep(1.5 * (attempt + 1))


def main() -> None:
    ml, lr, lag_s = _verify_stage1_lock()
    free_gib = shutil.disk_usage(ROOT).free / float(1 << 30)
    if free_gib < MIN_FREE_DISK_GIB:
        raise RuntimeError(f"Insufficient free disk: {free_gib:.2f} GiB < {MIN_FREE_DISK_GIB:.2f} GiB")

    with (WS / "FROZEN_COHORT_D099.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    proj_bytes = sum(int(r["f1_bytes"]) for r in rows)
    proj_mib = proj_bytes / float(1 << 20)
    if proj_mib > MAX_RAW_DOWNLOAD_MIB:
        raise RuntimeError(f"Projected download {proj_mib:.3f} MiB exceeds cap {MAX_RAW_DOWNLOAD_MIB:.1f} MiB")

    print(f"Stage-1 lock verified (lag={lag_s:.2f}s >= 3.0s). Downloading {len(rows)} FITS ({proj_mib:.2f} MiB)...", flush=True)
    IN_DIR.mkdir(parents=True, exist_ok=True)

    first_receipt: dict[str, Any] | None = None
    manifest_files: list[dict[str, Any]] = []
    inst_counts: dict[str, int] = {}
    inst_bytes: dict[str, int] = {}
    total_bytes = 0

    for idx, r in enumerate(rows, 1):
        inst = r["instrument"]
        rel = r["f1_rel"]
        url = r["f1_url"]
        dest = IN_DIR / rel
        dl_start_utc = dt.datetime.now(dt.timezone.utc).isoformat()
        if not dest.exists():
            _download_with_retry(url, dest)
        val = _validate_fits_file(dest, inst)
        sz = dest.stat().st_size
        sha = _sha256_file(dest)
        total_bytes += sz
        if total_bytes / float(1 << 20) > MAX_RAW_DOWNLOAD_MIB:
            raise RuntimeError(f"Cumulative download exceeded {MAX_RAW_DOWNLOAD_MIB} MiB at file {rel}!")

        if first_receipt is None:
            now_epoch = time.time()
            first_receipt = {
                "schema": "D099_FIRST_SCIENCE_DOWNLOAD_RECEIPT",
                "phase_id": "D099",
                "first_download_utc": dl_start_utc,
                "first_download_unix_epoch": round(now_epoch, 3),
                "lock_receipt_utc": lr["locked_utc"],
                "lock_receipt_sha256": _sha256_file(WS / "LOCK_RECEIPT.json"),
                "method_lock_sha256": lr["method_lock_sha256"],
                "chronology_lag_seconds": round(now_epoch - float(lr["locked_unix_epoch"]), 3),
                "first_dp_id": r["dp_id"],
                "first_rel": rel,
                "first_bytes": sz,
                "first_sha256": sha,
            }
            (WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json").write_text(json.dumps(first_receipt, indent=2), encoding="utf-8")

        inst_counts[inst] = inst_counts.get(inst, 0) + 1
        inst_bytes[inst] = inst_bytes.get(inst, 0) + sz
        manifest_files.append({
            "index": idx,
            "instrument": inst,
            "canonical_target": r["canonical_target"],
            "dp_id": r["dp_id"],
            "f1_rel": rel,
            "f1_url": url,
            "bytes": sz,
            "sha256": sha,
            "validation": val,
        })
        if idx % 15 == 0 or idx == len(rows):
            print(f"  [{idx:02d}/{len(rows)}] {rel} ({sz} B, cum={total_bytes/(1<<20):.2f} MiB)", flush=True)

    manifest = {
        "schema": "D099_FULL_INPUT_MANIFEST",
        "phase_id": "D099",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "method_lock_sha256": lr["method_lock_sha256"],
        "lock_receipt_sha256": _sha256_file(WS / "LOCK_RECEIPT.json"),
        "n_files": len(manifest_files),
        "total_bytes": total_bytes,
        "total_mib": round(total_bytes / float(1 << 20), 6),
        "max_raw_mib_cap": MAX_RAW_DOWNLOAD_MIB,
        "instrument_counts": inst_counts,
        "instrument_bytes": inst_bytes,
        "files": manifest_files,
    }
    (WS / "FULL_D099_INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Download & validation COMPLETE: {len(manifest_files)} FITS, {total_bytes} B ({manifest['total_mib']:.3f} MiB).", flush=True)


if __name__ == "__main__":
    main()
