#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D098 (`V5.6`) Prospectively Locked Science Input Downloader.

Verifies Stage-1 lock integrity (`METHOD_LOCK.json` + `LOCK_RECEIPT.json` for
all 7 locked Stage-1 files), enforces chronological separation (`>= 3.0 s`),
downloads only the exact `99` pre-committed FITS spectra (`27 SOFIA_GREAT +
17 ISO_SWS + 35 SOFIA_FORCAST + 20 CARMENES_VIS`) into
`/home/martin/SETI_Fortsaettelse_2026-11-14/inputs_d098_v5_6`, validates FITS
integrity for each instrument, enforces the `125.0 MiB` cap and `>= 1.5 GiB`
free-disk floor, and writes `FIRST_SCIENCE_DOWNLOAD_RECEIPT.json` +
`FULL_D098_INPUT_MANIFEST.json`.
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

from astropy.io import fits

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_v5_6_20261122_d098_sofia_great_iso_sws_forcast_optical_jerk"
IN_DIR = ROOT / "inputs_d098_v5_6"

MIN_CHRONOLOGY_LAG_S = 3.0
MAX_RAW_DOWNLOAD_MIB = 125.0
MIN_FREE_DISK_GIB = 1.5


def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_stage1_lock() -> tuple[dict[str, Any], dict[str, Any], str]:
    receipt_p = WS / "LOCK_RECEIPT.json"
    method_p = WS / "METHOD_LOCK.json"
    if not receipt_p.exists() or not method_p.exists():
        raise RuntimeError("Stage-1 lock missing: run build_cohort.py before download_inputs.py.")
    receipt = json.loads(receipt_p.read_text())
    method = json.loads(method_p.read_text())
    method_sha = _sha256_file(method_p)
    if receipt.get("method_lock_sha256") != method_sha:
        raise RuntimeError("LOCK_RECEIPT method_lock_sha256 does not match METHOD_LOCK.json")
    locked_hashes = method.get("locked_file_hashes") or {}
    if len(locked_hashes) != 7:
        raise RuntimeError(f"Expected 7 locked Stage-1 files, found {len(locked_hashes)}")
    for rel, rec in locked_hashes.items():
        fp = WS / rel
        if not fp.exists():
            raise RuntimeError(f"Missing locked Stage-1 file: {rel}")
        exp_sha = rec["sha256"] if isinstance(rec, dict) else str(rec)
        obs_sha = _sha256_file(fp)
        if obs_sha != exp_sha:
            raise RuntimeError(f"Stage-1 lock hash mismatch on {rel}: {obs_sha} != {exp_sha}")
    return receipt, method, method_sha


def _validate_fits(path: pathlib.Path, instrument: str) -> dict[str, Any]:
    with fits.open(path, memmap=False) as hdul:
        if instrument == "SOFIA_GREAT":
            arr = hdul[1].data if len(hdul) > 1 and hdul[1].data is not None else hdul[0].data
            if arr is None or arr.size < 32:
                raise RuntimeError(f"Invalid GREAT FITS shape in {path.name}")
            return {"format": "FITS_GREAT_SPECTRUM", "n_hdu": len(hdul), "n_rows": int(arr.size)}
        if instrument == "ISO_SWS":
            arr = hdul[0].data
            if arr is None or arr.ndim != 2 or arr.shape[1] < 4 or arr.shape[0] < 100:
                raise RuntimeError(f"Invalid ISO_SWS FITS shape {getattr(arr, 'shape', None)} in {path.name}")
            return {"format": "FITS_ISO_SWS_4COL", "n_hdu": len(hdul), "n_rows": int(arr.shape[0])}
        if instrument == "SOFIA_FORCAST":
            arr = hdul[0].data
            if arr is None or arr.ndim != 2 or arr.shape[0] < 5 or arr.shape[1] < 24:
                raise RuntimeError(f"Invalid SOFIA_FORCAST FITS shape {getattr(arr, 'shape', None)} in {path.name}")
            return {"format": "FITS_FORCAST_5ROW", "n_hdu": len(hdul), "n_rows": int(arr.shape[1])}
        if instrument == "CARMENES_VIS":
            if len(hdul) < 5 or hdul[1].data is None or hdul[4].data is None:
                raise RuntimeError(f"Invalid CARMENES_VIS FITS structure in {path.name}")
            return {"format": "FITS_CARMENES_4EXT", "n_hdu": len(hdul), "n_rows": int(hdul[1].data.size)}
    raise RuntimeError(f"Unknown instrument {instrument}")


def _download_one(url: str, dst: pathlib.Path, max_retries: int = 4) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for attempt in range(1, max_retries + 1):
        tmp = dst.with_suffix(dst.suffix + ".part")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETI-V5.6-D098-Downloader/1.0"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = resp.read()
            if len(data) < 2880:
                raise RuntimeError(f"Truncated FITS payload ({len(data)} B) from {url}")
            tmp.write_bytes(data)
            tmp.replace(dst)
            return
        except Exception as exc:
            last_err = exc
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            if attempt < max_retries:
                time.sleep(1.5 * attempt)
    raise RuntimeError(f"Failed downloading {url}: {last_err}")


def main() -> int:
    receipt, _method, method_sha = _verify_stage1_lock()
    lock_epoch = float(receipt["locked_at_unix"])
    now_epoch = time.time()
    lag_s = now_epoch - lock_epoch
    if lag_s < MIN_CHRONOLOGY_LAG_S:
        raise RuntimeError(f"Chronological lock violation: lag={lag_s:.3f}s < {MIN_CHRONOLOGY_LAG_S:.1f}s")

    cohort_p = WS / "FROZEN_COHORT_D098.csv"
    with cohort_p.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 99:
        raise RuntimeError(f"Expected 99 rows in FROZEN_COHORT_D098.csv, found {len(rows)}")

    IN_DIR.mkdir(parents=True, exist_ok=True)
    first_receipt_p = WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json"
    manifest_entries: list[dict[str, Any]] = []
    total_bytes = 0

    for idx, r in enumerate(rows, 1):
        inst = r["instrument"]
        star = r["canonical_target"]
        dp_id = r["dp_id"]
        rel_path = r["f1_rel"]
        url = r["f1_url"]
        dst = IN_DIR / rel_path
        if not dst.exists():
            _download_one(url, dst)
        if not first_receipt_p.exists():
            dl_epoch = time.time()
            first_receipt = {
                "schema": "D098_FIRST_SCIENCE_DOWNLOAD_RECEIPT_V1",
                "phase_id": "D098",
                "method_lock_sha256": method_sha,
                "locked_at_utc": receipt["locked_at_utc"],
                "locked_at_unix": round(lock_epoch, 3),
                "first_download_utc": dt.datetime.fromtimestamp(dl_epoch, tz=dt.timezone.utc).isoformat(),
                "first_download_unix": round(dl_epoch, 3),
                "chronology_lag_seconds": round(dl_epoch - lock_epoch, 3),
                "first_file_relpath": rel_path,
                "first_dp_id": dp_id,
                "first_star": star,
                "first_instrument": inst,
                "first_file_sha256": _sha256_file(dst),
                "first_file_bytes": dst.stat().st_size,
            }
            first_receipt_p.write_text(json.dumps(first_receipt, indent=2) + "\n")

        fmeta = _validate_fits(dst, inst)
        sz = dst.stat().st_size
        total_bytes += sz
        manifest_entries.append({
            "index": idx,
            "instrument": inst,
            "canonical_target": star,
            "dp_id": dp_id,
            "local_relpath": rel_path,
            "bytes": sz,
            "sha256": _sha256_file(dst),
            **fmeta,
        })
        if idx % 20 == 0 or idx == len(rows):
            print(f"[{idx:02d}/{len(rows)}] {inst:13s} {star:10s} cum={total_bytes/1048576:.2f} MiB", flush=True)

    total_mib = total_bytes / 1048576.0
    if total_mib > MAX_RAW_DOWNLOAD_MIB:
        raise RuntimeError(f"Download cap exceeded: {total_mib:.3f} MiB > {MAX_RAW_DOWNLOAD_MIB} MiB")

    free_gib = shutil.disk_usage(ROOT).free / (1024 ** 3)
    if free_gib < MIN_FREE_DISK_GIB:
        raise RuntimeError(f"Low disk space after download: {free_gib:.3f} GiB < {MIN_FREE_DISK_GIB} GiB")

    manifest = {
        "schema": "D098_FULL_INPUT_MANIFEST_V1",
        "phase_id": "D098",
        "detector_version": "V5.6",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "inputs_dir": str(IN_DIR),
        "n_files": len(manifest_entries),
        "total_bytes": total_bytes,
        "total_mib": round(total_mib, 3),
        "max_raw_download_mib": MAX_RAW_DOWNLOAD_MIB,
        "post_download_free_gib": round(free_gib, 3),
        "method_lock_sha256": method_sha,
        "by_instrument": {
            inst: {
                "n_files": sum(1 for e in manifest_entries if e["instrument"] == inst),
                "bytes": sum(e["bytes"] for e in manifest_entries if e["instrument"] == inst),
            }
            for inst in ("SOFIA_GREAT", "ISO_SWS", "SOFIA_FORCAST", "CARMENES_VIS")
        },
        "files": manifest_entries,
    }
    (WS / "FULL_D098_INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Downloaded and validated {len(manifest_entries)}/99 files ({total_mib:.3f} MiB <= {MAX_RAW_DOWNLOAD_MIB} MiB; free={free_gib:.2f} GiB).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
