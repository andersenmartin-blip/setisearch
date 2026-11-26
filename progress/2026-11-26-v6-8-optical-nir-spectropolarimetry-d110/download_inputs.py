#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D110 (V6.8) Stage-1 Locked Post-Seal Downloader:
  - Enforces immutable Stage-1 seal (METHOD_LOCK.json & LOCK_RECEIPT.json).
  - Enforces chronology_lag_seconds >= 10.5 s before creating inputs_d110_v6_8.
  - Downloads all locked TBL_NARVAL (.s via HTTP GET only), CFHT_ESPADONS_POL (*p.fits),
    and CFHT_SPIROU_POL (*p.fits) science exposures, validating every physical file with
    the sealed V6.8 spectropolarimetric loaders in `v6_8_detector.py`.
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
RAW_DIR = ROOT / "inputs_d110_v6_8"

if str(WS) not in sys.path:
    sys.path.insert(0, str(WS))

import v6_8_detector as det  # noqa: E402


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
            req = urllib.request.Request(url, headers={"User-Agent": "SETI-D110-Downloader/1.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                if r.status not in (200, 206):
                    raise RuntimeError(f"HTTP {r.status} for {url}")
                data = r.read()
            if len(data) < min_bytes:
                raise RuntimeError(f"File too small ({len(data)} B) for {url}")
            # Reject accidental HTML error payloads
            head_lo = data[:256].lstrip().lower()
            if head_lo.startswith(b"<!doctype") or head_lo.startswith(b"<html"):
                raise RuntimeError(f"Unexpected HTML payload for {url}")
            dest.write_bytes(data)
            return len(data)
        except Exception as exc:
            last_err = exc
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"Download failed after 5 attempts for {url}: {last_err}")


def _validate_pol_file(inst: str, path: Path) -> dict[str, Any]:
    if inst == "TBL_NARVAL":
        d = det.load_narval_polarbase_s(path)
        assert len(d["wave_a"]) >= 20000, f"NARVAL pixels too few: {len(d['wave_a'])}"
    elif inst == "CFHT_ESPADONS_POL":
        d = det.load_espadons_pol_fits(path)
        assert len(d["wave_a"]) >= 40000, f"ESPaDOnS pixels too few: {len(d['wave_a'])}"
    elif inst == "CFHT_SPIROU_POL":
        d = det.load_spirou_pol_fits(path)
        assert len(d["wave_a"]) >= 40000, f"SPIRou pixels too few: {len(d['wave_a'])}"
    else:
        raise ValueError(f"Unknown instrument {inst}")
    return {
        "n_valid_raw": int(len(d["wave_a"])),
        "wave_min_a": round(float(d["wave_a"][0]), 3),
        "wave_max_a": round(float(d["wave_a"][-1]), 3),
        "regime": str(d["regime"]),
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
    with (WS / "FROZEN_COHORT_D110.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows, "Empty FROZEN_COHORT_D110.csv!"

    fdr = {
        "schema": "D110_FIRST_DOWNLOAD_RECEIPT",
        "phase_id": "D110",
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
    print(f"Stage-1 lock verified (lag=+{lag:.3f}s). Downloading {len(rows)} polarimetric spectra to {RAW_DIR}...", flush=True)

    def _fetch_one(r: dict[str, Any]) -> dict[str, Any]:
        inst = r["instrument"]
        rel = r["f1_rel"]
        dest = RAW_DIR / rel
        if dest.exists() and dest.stat().st_size >= 8000:
            try:
                vmeta = _validate_pol_file(inst, dest)
                sz = int(dest.stat().st_size)
                return {"ok": True, "row": r, "bytes": sz, "sha256": _sha256_file(dest), "vmeta": vmeta}
            except Exception:
                pass
        sz = _download_file(r["f1_url"], dest)
        vmeta = _validate_pol_file(inst, dest)
        return {"ok": True, "row": r, "bytes": sz, "sha256": _sha256_file(dest), "vmeta": vmeta}

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for idx, res in enumerate(pool.map(_fetch_one, rows), 1):
            results.append(res)
            r = res["row"]
            if idx % 12 == 0 or idx == len(rows):
                print(f"  [{idx}/{len(rows)}] {r['instrument']} {r['canonical_target']} {r['stokes']} ({res['bytes']} B, raw_px={res['vmeta']['n_valid_raw']})", flush=True)

    obs_list = []
    tot_b = 0
    for res in results:
        r = res["row"]
        b = int(res["bytes"])
        tot_b += b
        obs_list.append({
            "instrument": r["instrument"],
            "star": r["canonical_target"],
            "common_name": r["common_name"],
            "role": r["role"],
            "stokes": r["stokes"],
            "dp_id": r["dp_id"],
            "f1_rel": r["f1_rel"],
            "raw_bytes": b,
            "raw_sha256": res["sha256"],
            "n_valid_raw": res["vmeta"]["n_valid_raw"],
            "wave_min_a": res["vmeta"]["wave_min_a"],
            "wave_max_a": res["vmeta"]["wave_max_a"],
            "regime": res["vmeta"]["regime"],
        })

    man = {
        "schema": "D110_FULL_INPUT_MANIFEST",
        "phase_id": "D110",
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "expected_observations": len(rows),
        "downloaded_observations": len(obs_list),
        "valid_physical_files": len(obs_list),
        "failed_observations": 0,
        "total_bytes": tot_b,
        "total_mib": round(tot_b / (1024.0 * 1024.0), 3),
        "observations": obs_list,
    }
    (WS / "FULL_D110_INPUT_MANIFEST.json").write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
    print(f"DOWNLOAD COMPLETE: {len(obs_list)}/{len(rows)} valid files, {tot_b/(1024*1024):.3f} MiB, 0 failures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
