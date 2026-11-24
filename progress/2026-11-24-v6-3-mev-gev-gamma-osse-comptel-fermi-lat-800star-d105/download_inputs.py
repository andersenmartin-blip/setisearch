#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D105 (`V6.3`) Stage-2 Verified Downloader & File-Integrity Validator.
Verifies all Stage-1 SHA-256 locks, records `FIRST_SCIENCE_DOWNLOAD_RECEIPT.json`
(>= 10 s after Stage-1 seal), deduplicates and downloads all 82 unique physical
archival files across 126 target-instrument observations into `$RAW105`,
validates every tar/FITS schema, and emits `FULL_D105_INPUT_MANIFEST.json`.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import os
import tarfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from astropy.io import fits

WS = Path(__file__).resolve().parent
ROOT = WS.parent.parent
RAW_DIR = ROOT / "inputs_d105_v6_3"


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
        if expected_bytes <= 0 or abs(dest.stat().st_size - expected_bytes) <= 64:
            return int(dest.stat().st_size)

    last_err: Exception | None = None
    for attempt in range(6):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "SETI-V6.3-D105-Science-Pipeline/1.0", "Connection": "close"},
            )
            with urllib.request.urlopen(req, timeout=240) as resp:
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
    raise RuntimeError(f"Failed download after 6 tries ({url}): {last_err}")


def _validate_physical_file(path: Path, inst: str) -> str:
    if inst == "CGRO_OSSE":
        has_pha = has_rmf = False
        sub_cnt = 0
        with tarfile.open(path, "r:gz") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                bn = m.name.rsplit("/", 1)[-1].lower()
                if bn.endswith("_n.pha"):
                    with fits.open(io.BytesIO(tf.extractfile(m).read()), memmap=False) as hp:
                        if "SPECTRUM" not in hp:
                            raise ValueError(f"OSSE _n.pha missing SPECTRUM in {path.name}")
                    has_pha = True
                elif bn.endswith("_n.rmf"):
                    with fits.open(io.BytesIO(tf.extractfile(m).read()), memmap=False) as hr:
                        if "EBOUNDS" not in hr:
                            raise ValueError(f"OSSE _n.rmf missing EBOUNDS in {path.name}")
                    has_rmf = True
                elif "_vp" in bn and bn.endswith("_w.pha"):
                    sub_cnt += 1
        if not (has_pha and has_rmf):
            raise ValueError(f"OSSE tarball missing _n.pha/_n.rmf: {path.name}")
        return f"cgro_osse_targz:subperiods={sub_cnt}"

    if path.name.endswith(".gz"):
        with gzip.open(path, "rb") as gz:
            head = gz.read(2880)
        if not head.startswith(b"SIMPLE"):
            raise ValueError(f"Invalid gzipped FITS signature: {path}")

    with fits.open(path, memmap=True) as hdul:
        if inst == "CGRO_COMPTEL":
            h1 = hdul["COMPTEL_EVP"] if "COMPTEL_EVP" in hdul else hdul[1]
            cols = set(h1.columns.names)
            need = {"E_D1", "E_D2", "PHIBAR", "GLON_SCAT", "GLAT_SCAT", "TJD"}
            if not need.issubset(cols):
                raise ValueError(f"COMPTEL EVP missing cols in {path.name}: {need - cols}")
            return f"cgro_comptel_evp:rows={len(h1.data)}"

        if inst == "FERMI_LAT":
            ev = hdul["EVENTS"]
            cols = set(ev.columns.names)
            need = {"ENERGY", "RA", "DEC", "ZENITH_ANGLE", "EVENT_CLASS", "CONVERSION_TYPE"}
            if not need.issubset(cols) or "GTI" not in hdul:
                raise ValueError(f"Fermi LAT missing cols/GTI in {path.name}")
            return f"fermi_lat_p305:rows={len(ev.data)}"

        if inst == "CARMENES_VIS":
            if len(hdul) < 5 or hdul[1].data is None or hdul[3].data is None or hdul[4].data is None:
                raise ValueError(f"CARMENES VIS invalid extensions in {path.name}")
            return f"carmenes_vis:shape={hdul[1].data.shape}"

        if inst in ("ESO_ESPRESSO", "ESO_HARPS", "ESO_FEROS"):
            if len(hdul) < 2 or hdul[1].data is None:
                raise ValueError(f"ESO 1D spectrum missing ext[1] in {path.name}")
            return f"{inst.lower()}:rows={len(hdul[1].data)}"

        raise ValueError(f"Unknown instrument {inst}")


def _process_physical_file(spec: dict[str, Any]) -> dict[str, Any]:
    rel = str(spec["rel"])
    url = str(spec["url"])
    inst = str(spec["instrument"])
    exp_bytes = int(spec.get("bytes") or 0)
    dest = RAW_DIR / rel
    sz = _download_with_retry(url, dest, expected_bytes=exp_bytes)
    info = _validate_physical_file(dest, inst)
    sha = _sha256_file(dest)
    return {
        "rel_path": rel,
        "url": url,
        "instrument": inst,
        "bytes": sz,
        "sha256": sha,
        "info": info,
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
        "schema": "D105_FIRST_SCIENCE_DOWNLOAD_RECEIPT",
        "phase_id": "D105",
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

    with open(WS / "FROZEN_COHORT_D105.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 126:
        raise RuntimeError(f"Expected 126 cohort rows, got {len(rows)}")

    # Collect unique physical files across primary f1_rel + extra_files
    phys_specs: dict[str, dict[str, Any]] = {}
    for r in rows:
        rel = r["f1_rel"]
        if rel not in phys_specs:
            phys_specs[rel] = {
                "rel": rel,
                "url": r["f1_url"],
                "bytes": int(r.get("f1_bytes") or 0),
                "instrument": r["instrument"],
            }
        extras = json.loads(r.get("extra_files") or "[]")
        for ex in extras:
            erel = ex["rel"]
            if erel not in phys_specs:
                phys_specs[erel] = {
                    "rel": erel,
                    "url": ex["url"],
                    "bytes": int(ex.get("bytes") or 0),
                    "instrument": r["instrument"],
                }

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    phys_done: dict[str, dict[str, Any]] = {}
    phys_errors: dict[str, str] = {}
    items = sorted(phys_specs.values(), key=lambda x: x["rel"])
    print(f"Downloading & validating {len(items)} unique physical archival files for {len(rows)} D105 observations...")
    with ThreadPoolExecutor(max_workers=4) as ex:
        fut_map = {ex.submit(_process_physical_file, sp): sp for sp in items}
        for i, fut in enumerate(as_completed(fut_map), 1):
            sp = fut_map[fut]
            rel = sp["rel"]
            try:
                rec = fut.result()
                phys_done[rel] = rec
                print(f"[{i}/{len(items)}] {rec['instrument']} {rel} OK ({rec['bytes']:,} B)")
            except Exception as exc:
                phys_errors[rel] = str(exc)
                print(f"[ERR] {rel}: {exc}")

    # Map physical file results onto all 126 observation rows
    obs_results: list[dict[str, Any]] = []
    obs_errors: list[dict[str, str]] = []
    for r in rows:
        rels = [r["f1_rel"]] + [ex["rel"] for ex in json.loads(r.get("extra_files") or "[]")]
        if any(rel in phys_errors for rel in rels):
            err_msg = "; ".join(f"{rel}: {phys_errors[rel]}" for rel in rels if rel in phys_errors)
            obs_errors.append({"dp_id": r["dp_id"], "star": r["canonical_target"], "error": err_msg})
            continue
        f_list = []
        for idx_f, rel in enumerate(rels):
            pm = phys_done[rel]
            f_list.append({
                "role": "PRIMARY" if idx_f == 0 else f"EXTRA_{idx_f}",
                "rel_path": pm["rel_path"],
                "url": pm["url"],
                "bytes": pm["bytes"],
                "sha256": pm["sha256"],
            })
        pm0 = phys_done[rels[0]]
        obs_results.append({
            "status": "DOWNLOADED",
            "dp_id": r["dp_id"],
            "instrument": r["instrument"],
            "star": r["canonical_target"],
            "rel_path": pm0["rel_path"],
            "url": pm0["url"],
            "bytes": sum(int(x["bytes"]) for x in f_list),
            "sha256": pm0["sha256"],
            "info": pm0["info"],
            "files": f_list,
        })

    obs_results.sort(key=lambda x: (x["instrument"], x["star"], x["dp_id"]))
    tot_unique_bytes = sum(int(v["bytes"]) for v in phys_done.values())
    manifest = {
        "schema": "D105_FULL_INPUT_MANIFEST",
        "phase_id": "D105",
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "raw_dir": str(RAW_DIR),
        "expected_observations": len(rows),
        "valid_observations": len(obs_results),
        "failed_observations": len(obs_errors),
        "expected_physical_files": len(items),
        "valid_physical_files": len(phys_done),
        "failed_physical_files": len(phys_errors),
        "total_bytes": tot_unique_bytes,
        "total_mib": round(tot_unique_bytes / (1024.0 * 1024.0), 4),
        "errors": obs_errors,
        "physical_file_errors": phys_errors,
        "physical_files": sorted(phys_done.values(), key=lambda x: x["rel_path"]),
        "observations": obs_results,
    }
    (WS / "FULL_D105_INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest written: valid_obs={len(obs_results)}/{len(rows)}, valid_files={len(phys_done)}/{len(items)}, total={manifest['total_mib']:.2f} MiB")
    if obs_errors or len(phys_done) != len(items):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
