#!/usr/bin/env python3
"""Stage 1 for Spor N10: Acquire 6 verified GBT L-band ABACAD cadences (36 .0002.h5 files)."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n10_20261127_bl_radio_blindspot_abacad"
PYDEPS = WS / "pydeps"
if str(PYDEPS) not in sys.path:
    sys.path.insert(0, str(PYDEPS))

import h5py

INP = ROOT / "inputs_n10_20261127"
RAW_DIR = INP / "raw_h5"

CADENCES = [
    {"target": "GJ411", "master_star": "LALANDE21185", "cadence_id": "--72283", "dist_pc": 2.54613, "n_exoplanets": 2},
    {"target": "GJ65A", "master_star": "GJ65A", "cadence_id": "--73638", "dist_pc": 2.67491, "n_exoplanets": 0},
    {"target": "GJ54.1", "master_star": "YZCET", "cadence_id": "--73620", "dist_pc": 3.71668, "n_exoplanets": 3},
    {"target": "GJ273", "master_star": "GJ273", "cadence_id": "--517180", "dist_pc": 3.7861, "n_exoplanets": 2},
    {"target": "GJ687", "master_star": "GJ687", "cadence_id": "--75045", "dist_pc": 4.5499, "n_exoplanets": 2},
    {"target": "GJ1002", "master_star": "GJ1002", "cadence_id": "--72885", "dist_pc": 4.8473, "n_exoplanets": 2},
]


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_cadence_metadata(cad: dict) -> dict:
    url = f"http://seti.berkeley.edu/opendata/api/get-cadence/{cad['cadence_id']}"
    req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-N10/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    mids = sorted([x for x in data.get("data", []) if x.get("url", "").endswith(".0002.h5")], key=lambda x: float(x["mjd"]))
    if len(mids) != 6:
        raise RuntimeError(f"Expected 6 mid-res scans for {cad['target']}, got {len(mids)}")
    roles = ["A1", "B1", "A2", "C1", "A3", "D1"]
    scans = []
    for idx, x in enumerate(mids):
        fname = x["url"].split("/")[-1]
        scans.append({
            "role": roles[idx],
            "scan_idx": idx,
            "on_off": "ON" if idx in (0, 2, 4) else "OFF",
            "api_target": x["target"],
            "mjd": float(x["mjd"]),
            "ra_deg": float(x["ra"]),
            "dec_deg": float(x["decl"]),
            "center_freq_mhz": float(x["center_freq"]),
            "expected_bytes": int(x["size"]),
            "expected_md5": str(x["md5sum"]).strip().lower(),
            "url": x["url"],
            "filename": fname,
            "local_path": str(RAW_DIR / cad["target"].replace(".", "_") / fname),
        })
    return {**cad, "scans": scans}


def download_one(scan: dict) -> dict:
    dest = Path(scan["local_path"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    exp_size = scan["expected_bytes"]
    exp_md5 = scan["expected_md5"]

    if dest.exists() and dest.stat().st_size == exp_size:
        got_md5 = md5_file(dest)
        if got_md5 == exp_md5:
            return {**scan, "status": "CACHED_MD5_OK", "bytes": exp_size, "md5": got_md5}

    for attempt in range(1, 5):
        try:
            existing = part.stat().st_size if part.exists() else 0
            if existing > exp_size:
                part.unlink()
                existing = 0
            headers = {"User-Agent": "SETIsearch-N10/1.0"}
            mode = "wb"
            if 0 < existing < exp_size:
                headers["Range"] = f"bytes={existing}-"
                mode = "ab"
            req = urllib.request.Request(scan["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                if mode == "ab" and getattr(resp, "status", 200) != 206:
                    existing = 0
                    mode = "wb"
                with part.open(mode) as fh:
                    while True:
                        buf = resp.read(1 << 20)
                        if not buf:
                            break
                        fh.write(buf)
            if part.stat().st_size != exp_size:
                raise IOError(f"Size mismatch: {part.stat().st_size} != {exp_size}")
            got_md5 = md5_file(part)
            if got_md5 != exp_md5:
                part.unlink(missing_ok=True)
                raise IOError(f"MD5 mismatch: {got_md5} != {exp_md5}")
            part.replace(dest)
            return {**scan, "status": "DOWNLOADED_MD5_OK", "bytes": exp_size, "md5": got_md5}
        except Exception as exc:
            print(f"  [WARN] attempt {attempt} failed for {scan['filename']}: {exc}", flush=True)
            time.sleep(2 * attempt)
    raise RuntimeError(f"Failed to download verified {scan['filename']}")


def main() -> int:
    t0 = time.time()
    INP.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    cads = [fetch_cadence_metadata(c) for c in CADENCES]
    all_scans = [s for c in cads for s in c["scans"]]
    print(f"[N10 Stage 1] Resolved {len(cads)} ABACAD cadences ({len(all_scans)} .0002.h5 files, {sum(s['expected_bytes'] for s in all_scans)/(1<<30):.2f} GiB).", flush=True)

    manifest = {
        "campaign": "SPOR_N10_BL_RADIO_BLINDSPOT_ABACAD",
        "acquired_utc": datetime.now(timezone.utc).isoformat(),
        "cadences": cads,
    }
    (INP / "n10_abacad_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    results = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(download_one, s): s for s in all_scans}
        done_n = 0
        for fut in as_completed(futs):
            res = fut.result()
            results.append(res)
            done_n += 1
            if done_n % 6 == 0 or done_n == len(all_scans):
                print(f"  [{done_n}/{len(all_scans)}] verified {res['filename']} ({res['status']})", flush=True)

    # Verify HDF5 headers cleanly
    h5_meta = []
    for s in all_scans:
        with h5py.File(s["local_path"], "r") as hf:
            ds = hf["data"]
            at = dict(ds.attrs)
            h5_meta.append({
                "target": s["api_target"],
                "role": s["role"],
                "filename": s["filename"],
                "shape": list(ds.shape),
                "fch1": float(at["fch1"]),
                "foff": float(at["foff"]),
                "tsamp": float(at["tsamp"]),
                "tstart": float(at["tstart"]),
                "md5": s["expected_md5"],
                "bytes": s["expected_bytes"],
            })

    with (INP / "n10_abacad_scans.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(h5_meta[0].keys()))
        w.writeheader()
        w.writerows(h5_meta)

    acq_log = {
        "campaign": "SPOR_N10_BL_RADIO_BLINDSPOT_ABACAD",
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": round(time.time() - t0, 2),
        "cadences": len(cads),
        "files_verified": len(h5_meta),
        "total_bytes": sum(s["expected_bytes"] for s in all_scans),
        "md5_all_verified": True,
        "external_contacts": 0,
    }
    (INP / "stage1_acquisition_log.json").write_text(json.dumps(acq_log, indent=2), encoding="utf-8")
    print(f"[N10 Stage 1] Complete in {acq_log['elapsed_s']}s: {len(h5_meta)}/36 HDF5 MD5-verified.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
