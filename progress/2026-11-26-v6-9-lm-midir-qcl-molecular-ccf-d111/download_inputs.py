#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D111 (V6.9) Stage-1 Locked Post-Seal Downloader:
  - Enforces immutable Stage-1 seal (METHOD_LOCK.json & LOCK_RECEIPT.json).
  - Enforces chronology_lag_seconds >= 10.5 s before creating inputs_d111_v6_9.
  - Downloads all locked JWST NIRSpec G395H, JWST NIRSpec G395M, JWST MIRI/MRS x1d.fits,
    and ESO CRIRES+ K-band 1D FITS exposures, validating every physical file with the
    sealed V6.9 loaders in `v6_9_detector.py`.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent
ROOT = WS.parent.parent
RAW_DIR = ROOT / "inputs_d111_v6_9"

if str(WS) not in sys.path:
    sys.path.insert(0, str(WS))

import v6_9_detector as det  # noqa: E402


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _verify_stage1_lock() -> tuple[dict[str, Any], dict[str, Any]]:
    lr_p = WS / "LOCK_RECEIPT.json"
    ml_p = WS / "METHOD_LOCK.json"
    assert lr_p.exists() and ml_p.exists(), "Missing LOCK_RECEIPT.json or METHOD_LOCK.json!"
    lr = json.loads(lr_p.read_text(encoding="utf-8"))
    ml = json.loads(ml_p.read_text(encoding="utf-8"))
    assert lr.get("inputs_dir_exists_at_seal") is False, "Stage-1 integrity violation: inputs_dir existed at seal!"
    assert _sha256_file(ml_p) == lr.get("method_lock_sha256"), "METHOD_LOCK.json SHA-256 mismatch!"
    s1 = ml.get("stage_1_files", {})
    assert len(s1) == 7, f"Expected 7 Stage-1 files, got {len(s1)}"
    for fn, exp_sha in s1.items():
        fp = WS / fn
        assert fp.exists(), f"Missing locked Stage-1 file: {fn}"
        act = _sha256_file(fp)
        assert act == exp_sha, f"Locked Stage-1 tamper on {fn}: {act} != {exp_sha}"
    return lr, ml


def _download_file(url: str, dest: Path, min_bytes: int = 8000) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETI-D111-Downloader/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                if r.status not in (200, 206):
                    raise RuntimeError(f"HTTP {r.status} for {url}")
                data = r.read()
            if len(data) < min_bytes:
                raise RuntimeError(f"File too small ({len(data)} B) for {url}")
            head_lo = data[:256].lstrip().lower()
            if head_lo.startswith(b"<!doctype") or head_lo.startswith(b"<html"):
                raise RuntimeError(f"Unexpected HTML payload for {url}")
            dest.write_bytes(data)
            return len(data)
        except Exception as exc:
            last_err = exc
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"Download failed after 5 attempts for {url}: {last_err}")


def _validate_ir_file(inst: str, path: Path) -> dict[str, Any]:
    if inst.startswith("JWST_"):
        d = det.load_jwst_x1d_fits(path)
    elif inst == "ESO_CRIRES_PLUS":
        d = det.load_eso_crires_plus_fits(path)
    else:
        raise ValueError(f"Unknown D111 instrument {inst}")
    w = d["wave_um"]
    assert len(w) >= 80, f"Too few spectral bins in {path.name}: {len(w)}"
    return {
        "n_valid_raw": int(len(w)),
        "wave_min_um": round(float(w[0]), 5),
        "wave_max_um": round(float(w[-1]), 5),
        "flux_is_jy": bool(d.get("flux_is_jy", False)),
        "mjd_obs": float(d.get("mjd_obs", 60000.0)),
    }


def main() -> int:
    lr, ml = _verify_stage1_lock()
    lock_epoch = float(lr["locked_unix_epoch"])
    now_epoch = time.time()
    lag = now_epoch - lock_epoch
    if lag < 10.5:
        wait_s = 10.5 - lag + 0.15
        print(f"Enforcing Stage-1 chronology buffer: sleeping {wait_s:.2f}s (current lag={lag:.2f}s)...", flush=True)
        time.sleep(wait_s)
        now_epoch = time.time()
        lag = now_epoch - lock_epoch

    assert lag >= 10.0, f"Chronology lag too small: {lag}"
    first_utc = datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat()
    with (WS / "FROZEN_COHORT_D111.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows, "Empty FROZEN_COHORT_D111.csv!"

    fdr = {
        "schema": "D111_FIRST_DOWNLOAD_RECEIPT",
        "phase_id": "D111",
        "locked_utc": ml["locked_utc"],
        "method_lock_sha256": lr["method_lock_sha256"],
        "first_download_utc": first_utc,
        "first_download_unix_epoch": round(now_epoch, 4),
        "chronology_lag_seconds": round(lag, 3),
        "first_target": rows[0]["canonical_target"],
        "first_dp_id": rows[0]["dp_id"],
        "first_url": rows[0]["f1_url"],
    }
    (WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json").write_text(json.dumps(fdr, indent=2) + "\n", encoding="utf-8")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Stage-1 lock verified (lag=+{lag:.3f}s). Downloading {len(rows)} IR spectra to {RAW_DIR}...", flush=True)

    def _fetch_one(r: dict[str, Any]) -> dict[str, Any]:
        dest = RAW_DIR / r["f1_rel"]
        nbytes = _download_file(r["f1_url"], dest)
        val = _validate_ir_file(r["instrument"], dest)
        sha = _sha256_file(dest)
        return {
            "star": r["canonical_target"],
            "instrument": r["instrument"],
            "dp_id": r["dp_id"],
            "obs_id": r["obs_id"],
            "relpath": r["f1_rel"],
            "url": r["f1_url"],
            "bytes": nbytes,
            "sha256": sha,
            "valid": True,
            **val,
        }

    records: list[dict[str, Any]] = []
    failed = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(_fetch_one, r) for r in rows]
        for idx, fut in enumerate(futs, 1):
            try:
                rec = fut.result()
                records.append(rec)
                if idx % 15 == 0 or idx == len(rows):
                    print(f"  [{idx}/{len(rows)}] {rec['instrument']} {rec['star']} ({rec['bytes']} B, {rec['n_valid_raw']} bins, {rec['wave_min_um']}-{rec['wave_max_um']} um) OK", flush=True)
            except Exception as exc:
                failed += 1
                print(f"  [FAIL {idx}/{len(rows)}] {rows[idx - 1]['dp_id']}: {exc}", flush=True)
                records.append({
                    "star": rows[idx - 1]["canonical_target"],
                    "instrument": rows[idx - 1]["instrument"],
                    "dp_id": rows[idx - 1]["dp_id"],
                    "valid": False,
                    "error": str(exc),
                })

    tot_bytes = sum(int(x.get("bytes", 0)) for x in records if x.get("valid"))
    manifest = {
        "schema": "D111_INPUT_MANIFEST",
        "phase_id": "D111",
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "chronology_lag_seconds": round(lag, 3),
        "expected_observations": len(rows),
        "valid_physical_files": sum(1 for x in records if x.get("valid")),
        "failed_observations": failed,
        "total_bytes": tot_bytes,
        "total_mib": round(tot_bytes / (1024.0 * 1024.0), 3),
        "observations": records,
    }
    (WS / "FULL_D111_INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assert failed == 0, f"{failed} downloads failed!"
    assert manifest["valid_physical_files"] == len(rows)
    print(f"Download complete: {manifest['valid_physical_files']}/{len(rows)} valid physical FITS files ({manifest['total_mib']:.3f} MiB), 0 failed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
