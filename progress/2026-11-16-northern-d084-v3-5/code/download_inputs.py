#!/usr/bin/env python3
"""Prospective post-lock FITS downloader for Phase D084 (NORTHERN_V3_5).

Creates inputs_d084_v3_5 strictly AFTER LOCK_RECEIPT.json, logs FIRST_SCIENCE_DOWNLOAD_RECEIPT.json
on the first archival spectrum download, and writes FULL_NORTHERN_INPUT_MANIFEST.json.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import time
import urllib.request

WS = Path(__file__).resolve().parent
INPUTS_DIR = WS.parent.parent / "inputs_d084_v3_5"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def download_one(url: str, dest: Path, expected_gzip: bool) -> tuple[str, int]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 10000:
        return sha256_file(dest), dest.stat().st_size

    tmp = dest.with_suffix(dest.suffix + ".tmp")
    last_err: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETI-D084-Prospective/1.0"})
            with urllib.request.urlopen(req, timeout=60.0) as resp, tmp.open("wb") as out:
                while True:
                    buf = resp.read(256 * 1024)
                    if not buf:
                        break
                    out.write(buf)
            data_head = tmp.read_bytes()[:16]
            sz = tmp.stat().st_size
            if sz < 10000:
                raise RuntimeError(f"Suspiciously small download ({sz} B) from {url}")
            if expected_gzip:
                if data_head[:2] != b"\x1f\x8b":
                    raise RuntimeError(f"Invalid gzip magic from {url}: {data_head[:8]!r}")
                with gzip.open(tmp, "rb") as gz:
                    hdr6 = gz.read(6)
                    if hdr6 != b"SIMPLE":
                        raise RuntimeError(f"Invalid gzipped FITS header from {url}: {hdr6!r}")
            else:
                if data_head[:6] != b"SIMPLE":
                    raise RuntimeError(f"Invalid FITS header from {url}: {data_head[:8]!r}")
            tmp.replace(dest)
            return sha256_file(dest), sz
        except Exception as exc:
            last_err = exc
            tmp.unlink(missing_ok=True)
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed downloading {url}: {last_err}")


def main() -> None:
    lrcpt = json.loads((WS / "LOCK_RECEIPT.json").read_text(encoding="utf-8"))
    if sha256_file(WS / "METHOD_LOCK.json") != lrcpt["method_lock_sha256"]:
        raise RuntimeError("METHOD_LOCK.json digest mismatch!")
    lock_dt = dt.datetime.fromisoformat(lrcpt["lock_utc"].replace("Z", "+00:00"))
    while (dt.datetime.now(dt.timezone.utc) - lock_dt).total_seconds() < 3.0:
        time.sleep(0.5)

    rows = list(csv.DictReader((WS / "FROZEN_COHORT_D084.csv").open("r", encoding="utf-8")))
    assert len(rows) == 183, f"Expected 183 cohort rows, got {len(rows)}"

    (INPUTS_DIR / "carmenes_vis").mkdir(parents=True, exist_ok=True)
    (INPUTS_DIR / "harps_n").mkdir(parents=True, exist_ok=True)

    # First archival download to stamp FIRST_SCIENCE_DOWNLOAD_RECEIPT.json
    r0 = rows[0]
    first_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if r0["instrument"] == "HARPS_N":
        rel0 = f"harps_n/{r0['dp_id']}_s1d_A.fits.gz"
        sha0, sz0 = download_one(r0["access_url"], INPUTS_DIR / rel0, expected_gzip=True)
        url0 = r0["access_url"]
    else:
        rel0 = f"carmenes_vis/{r0['dp_id']}.fits"
        sha0, sz0 = download_one(r0["access_url"], INPUTS_DIR / rel0, expected_gzip=False)
        url0 = r0["access_url"]

    dl_rcpt = {
        "schema": "D084_FIRST_SCIENCE_DOWNLOAD_RECEIPT",
        "phase_id": "D084",
        "lock_utc": lrcpt["lock_utc"],
        "first_download_utc": first_utc,
        "first_dp_id": r0["dp_id"],
        "first_url": url0,
        "first_relpath": rel0,
        "first_bytes": sz0,
        "first_sha256": sha0,
    }
    (WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json").write_text(json.dumps(dl_rcpt, indent=2) + "\n", encoding="utf-8")
    print(f"[download_inputs] Stamped FIRST_SCIENCE_DOWNLOAD_RECEIPT at {first_utc} (lock={lrcpt['lock_utc']})", flush=True)

    tasks: list[tuple[str, str, str, bool]] = []
    for r in rows:
        dp = r["dp_id"]
        if r["instrument"] == "CARMENES_VIS":
            rel = f"carmenes_vis/{dp}.fits"
            tasks.append((dp, "fits", r["access_url"], False))
        else:
            tasks.append((dp, "s1d", r["access_url"], True))
            tasks.append((dp, "e2ds", r["e2ds_url"], True))

    results: dict[tuple[str, str], tuple[str, str, int]] = {}
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=6) as ex:
        fut_map = {}
        for dp, kind, url, is_gz in tasks:
            rel = f"carmenes_vis/{dp}.fits" if kind == "fits" else f"harps_n/{dp}_{kind}_A.fits.gz"
            fut_map[ex.submit(download_one, url, INPUTS_DIR / rel, is_gz)] = (dp, kind, rel)
        done_n = 0
        for fut in as_completed(fut_map):
            dp, kind, rel = fut_map[fut]
            digest, sz = fut.result()
            results[(dp, kind)] = (rel, digest, sz)
            done_n += 1
            if done_n % 40 == 0 or done_n == len(tasks):
                print(f"  [download_inputs] {done_n}/{len(tasks)} FITS verified ({time.time() - t_start:.1f}s)", flush=True)

    exposures = []
    total_bytes = 0
    for r in rows:
        dp = r["dp_id"]
        if r["instrument"] == "CARMENES_VIS":
            rel, dig, sz = results[(dp, "fits")]
            total_bytes += sz
            exposures.append({
                "dp_id": dp,
                "instrument": "CARMENES_VIS",
                "star": r["canonical_target"],
                "fits_relpath": rel,
                "fits_sha256": dig,
                "fits_bytes": sz,
            })
        else:
            srel, sdig, ssz = results[(dp, "s1d")]
            erel, edig, esz = results[(dp, "e2ds")]
            total_bytes += ssz + esz
            exposures.append({
                "dp_id": dp,
                "instrument": "HARPS_N",
                "star": r["canonical_target"],
                "s1d_relpath": srel,
                "s1d_sha256": sdig,
                "s1d_bytes": ssz,
                "e2ds_relpath": erel,
                "e2ds_sha256": edig,
                "e2ds_bytes": esz,
            })

    manifest = {
        "schema": "D084_FULL_NORTHERN_INPUT_MANIFEST",
        "phase_id": "D084",
        "created_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "n_exposures": len(exposures),
        "n_files": len(tasks),
        "total_bytes": total_bytes,
        "exposures": exposures,
    }
    (INPUTS_DIR / "FULL_NORTHERN_INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[download_inputs] COMPLETE: {len(exposures)} exposures ({len(tasks)} FITS files, {total_bytes/(1024*1024):.1f} MiB)")


if __name__ == "__main__":
    main()
