#!/usr/bin/env python3
"""
Stage 2: Verify prospective METHOD_LOCK & IMPLEMENTATION_LOCK before downloading
Stage-2 Fink LSST /sources and /fp photometry for Spor R1 (DDF Gaia stars + controls)
and Spor R2 (538 Southern SETI catalog stars conesearch + /sources + /fp).
"""
from __future__ import annotations

import concurrent.futures
import csv
import datetime
import hashlib
import json
import math
import time
import urllib.request
from pathlib import Path
from typing import Any

WS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/analysis_workspace/work_rubin_v2_20261126_r1_ddf_and_r2_catalog")
INPUTS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/inputs_rubin_v2_20261126")
RESULTS = WS / "results"
FINK_BASE = "https://api.lsst.fink-portal.org"

SOURCES_COLS = ",".join([
    "r:diaObjectId", "r:diaSourceId", "r:midpointMjdTai", "r:band", "r:ra", "r:dec",
    "r:scienceFlux", "r:scienceFluxErr", "r:psfFlux", "r:psfFluxErr",
    "r:pixelFlags_saturated", "r:pixelFlags_saturatedCenter",
    "r:pixelFlags_cr", "r:pixelFlags_crCenter",
    "r:pixelFlags_bad", "r:pixelFlags_edge", "r:pixelFlags_offimage",
    "r:pixelFlags_nodata", "r:pixelFlags_interpolatedCenter", "r:isDipole",
    "r:forced_PsfFlux_flag", "r:forced_PsfFlux_flag_edge", "r:forced_PsfFlux_flag_noGoodPixels",
    "r:timeWithdrawnMjdTai", "r:reliability", "r:snr",
])
FP_COLS = ",".join([
    "r:diaObjectId", "r:diaForcedSourceId", "r:midpointMjdTai", "r:band",
    "r:scienceFlux", "r:scienceFluxErr", "r:psfFlux", "r:psfFluxErr",
    "r:timeWithdrawnMjdTai",
])


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def angsep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    cos_a = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_a)))) * 3600.0


def post_fink(ep: str, payload: dict[str, Any], timeout: int = 45, max_attempts: int = 6) -> tuple[bytes, dict[str, Any]]:
    url = FINK_BASE + ep
    body = json.dumps(payload).encode("utf-8")
    last_err = None
    for attempt in range(1, max_attempts + 1):
        t0 = time.monotonic()
        try:
            req = urllib.request.Request(
                url,
                data=body,
                method="POST",
                headers={"Content-Type": "application/json", "User-Agent": "SETI-Rubin-V2/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                rec = {
                    "utc": now_utc(),
                    "url": url,
                    "attempt": attempt,
                    "http_status": r.status,
                    "elapsed_s": round(time.monotonic() - t0, 3),
                    "bytes": len(raw),
                    "sha256": sha256_bytes(raw),
                }
                return raw, rec
        except Exception as exc:
            last_err = repr(exc)
            time.sleep(min(30, 1.5 * (2 ** (attempt - 1))))
    raise RuntimeError(f"Failed {url} after {max_attempts} attempts: {last_err}")


def fetch_batches(oids: list[str], ep: str, cols: str, out_dir: Path, prefix: str, batch_size: int = 25) -> int:
    total_rows = 0
    for i in range(0, len(oids), batch_size):
        batch = oids[i:i + batch_size]
        out_p = out_dir / f"{prefix}_{i//batch_size:03d}.json"
        if out_p.exists():
            rows = json.loads(out_p.read_text(encoding="utf-8"), parse_int=str)
            total_rows += len(rows)
            continue
        raw, rec = post_fink(ep, {"diaObjectId": ",".join(batch), "columns": cols, "output-format": "json"})
        out_p.write_bytes(raw)
        out_p.with_suffix(".json.receipt.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        rows = json.loads(raw.decode("utf-8"), parse_int=str)
        total_rows += len(rows)
        if ((i // batch_size) + 1) % 4 == 0 or i + batch_size >= len(oids):
            print(f"  [{prefix}] batch {(i//batch_size)+1}/{(len(oids)+batch_size-1)//batch_size}: {len(rows)} rows (cum={total_rows})", flush=True)
        time.sleep(0.25)
    return total_rows


def main() -> int:
    ml = json.loads((RESULTS / "METHOD_LOCK.json").read_text(encoding="utf-8"))
    il = json.loads((RESULTS / "IMPLEMENTATION_LOCK.json").read_text(encoding="utf-8"))
    assert sha256_file(RESULTS / "METHOD_LOCK.json") == il["method_lock_sha256"], "METHOD_LOCK hash mismatch"
    for rel, exp in ml["sha256"].items():
        assert sha256_file(WS / rel) == exp, f"Locked file modified before Stage-2: {rel}"

    started_p = RESULTS / "STAGE2_STARTED.json"
    if not started_p.exists():
        started_p.write_text(json.dumps({"utc": now_utc(), "method_lock_utc": ml["locked_utc"]}, indent=2) + "\n", encoding="utf-8")

    # 1. Spor R1 Science + Controls IDs
    r1_rows = list(csv.DictReader((RESULTS / "R1_COHORT_FROZEN.csv").open(encoding="utf-8")))
    ctrl_rows = list(csv.DictReader((RESULTS / "R1_CONTROLS_FROZEN.csv").open(encoding="utf-8")))
    r1_all_oids = [r["diaObjectId"] for r in r1_rows] + [r["diaObjectId"] for r in ctrl_rows]
    # Deduplicate preserving order
    r1_all_oids = list(dict.fromkeys(r1_all_oids))
    print(f"Fetching Stage-2 R1 sources & fp for {len(r1_all_oids)} objects...", flush=True)
    n_src = fetch_batches(r1_all_oids, "/api/v1/sources", SOURCES_COLS, INPUTS / "fink_sources", "r1_sources", batch_size=25)
    n_fp = fetch_batches(r1_all_oids, "/api/v1/fp", FP_COLS, INPUTS / "fink_fp", "r1_fp", batch_size=25)
    print(f"R1 fetched: sources={n_src} rows, fp={n_fp} rows", flush=True)

    # 2. Spor R2 Conesearch across all 538 Southern Science stars
    r2_stars = list(csv.DictReader((RESULTS / "R2_SOUTHERN_538STARS_FROZEN.csv").open(encoding="utf-8")))
    r2_out_p = INPUTS / "r2_catalog" / "r2_conesearch_matches.json"
    if r2_out_p.exists():
        r2_summary = json.loads(r2_out_p.read_text(encoding="utf-8"), parse_int=str)
    else:
        print(f"Querying Fink LSST conesearch (r=10\") for all {len(r2_stars)} Southern SETI stars...", flush=True)
        matches = []
        star_status = []

        def query_star(row: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
            raw, rec = post_fink(
                "/api/v1/conesearch",
                {
                    "ra": row["ra_deg"],
                    "dec": row["dec_deg"],
                    "radius": "10",
                    "columns": "r:diaObjectId,f:firstDiaSourceMjdTaiFink,r:ra,r:dec",
                    "output-format": "json",
                },
                timeout=35,
                max_attempts=5,
            )
            hits = json.loads(raw.decode("utf-8"), parse_int=str)
            st_rec = {
                "star": row["star"],
                "ra_deg": row["ra_deg"],
                "dec_deg": row["dec_deg"],
                "http_status": rec["http_status"],
                "n_hits": len(hits),
            }
            m_list = []
            for h in hits:
                oid = str(h.get("r:diaObjectId") or "")
                ora = float(h["r:ra"])
                odec = float(h["r:dec"])
                sep = angsep_arcsec(float(row["ra_deg"]), float(row["dec_deg"]), ora, odec)
                m_list.append({
                    "star": row["star"],
                    "common_name": row["common_name"],
                    "dist_pc": row["dist_pc"],
                    "star_ra_deg": row["ra_deg"],
                    "star_dec_deg": row["dec_deg"],
                    "diaObjectId": oid,
                    "obj_ra_deg": f"{ora:.7f}",
                    "obj_dec_deg": f"{odec:.7f}",
                    "separation_arcsec": round(sep, 4),
                    "firstDiaSourceMjdTaiFink": h.get("f:firstDiaSourceMjdTaiFink", ""),
                })
            return st_rec, m_list

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futs = [ex.submit(query_star, r) for r in r2_stars]
            for idx, fut in enumerate(concurrent.futures.as_completed(futs), 1):
                st_rec, m_list = fut.result()
                star_status.append(st_rec)
                matches.extend(m_list)
                if idx % 100 == 0 or idx == len(r2_stars):
                    print(f"  [R2 conesearch] {idx}/{len(r2_stars)} done (matches so far={len(matches)})", flush=True)

        matches.sort(key=lambda x: (x["separation_arcsec"], x["star"], x["diaObjectId"]))
        r2_summary = {
            "utc": now_utc(),
            "stars_queried": len(star_status),
            "http_200_count": sum(1 for s in star_status if s["http_status"] == 200),
            "stars_with_match": len({m["star"] for m in matches}),
            "total_matches": len(matches),
            "matches": matches,
            "star_status": sorted(star_status, key=lambda x: x["star"]),
        }
        r2_out_p.write_text(json.dumps(r2_summary, indent=2) + "\n", encoding="utf-8")

    r2_oids = list(dict.fromkeys(m["diaObjectId"] for m in r2_summary["matches"] if m.get("diaObjectId")))
    print(f"R2 unique matched diaObjectIds: {len(r2_oids)}; fetching /sources and /fp...", flush=True)
    if r2_oids:
        r2_src = fetch_batches(r2_oids, "/api/v1/sources", SOURCES_COLS, INPUTS / "r2_catalog", "r2_sources", batch_size=25)
        r2_fp = fetch_batches(r2_oids, "/api/v1/fp", FP_COLS, INPUTS / "r2_catalog", "r2_fp", batch_size=25)
        print(f"R2 fetched: sources={r2_src} rows, fp={r2_fp} rows", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
