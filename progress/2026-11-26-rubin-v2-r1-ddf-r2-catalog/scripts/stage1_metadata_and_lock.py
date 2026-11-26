#!/usr/bin/env python3
"""
Stage 1: Extract prior 210 excluded Rubin IDs (read-only from git), acquire public
Fink LSST 2026 statistics, DDF conesearch object lists, ESA Gaia DR3 TAP stellar
catalogs, Fink /objects metadata depth counts, select Spor R1 (up to 300 isolated
Gaia stars + 20 controls) & Spor R2 (538 Southern catalog stars), and seal
METHOD_LOCK.json + IMPLEMENTATION_LOCK.json before any Stage-2 photometry fetch.
"""
from __future__ import annotations

import collections
import csv
import datetime
import hashlib
import io
import json
import math
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

WS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/analysis_workspace/work_rubin_v2_20261126_r1_ddf_and_r2_catalog")
INPUTS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/inputs_rubin_v2_20261126")
RESULTS = WS / "results"
REPO = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/setisearch")
TABLE1_CSV = REPO / "zenodo_package" / "tables" / "table1_master_catalog_1083stars.csv"

FINK_BASE = "https://api.lsst.fink-portal.org"
GAIA_TAP_URL = "https://gaia.ari.uni-heidelberg.de/tap/sync"

DDFS = [
    ("COSMOS", 150.1190, 2.2058),
    ("EDFS_B", 63.6000, -48.0000),
    ("ELAIS_S1", 9.4500, -44.0000),
]

EPOCH_GAIA_JYEAR = 2016.0
EPOCH_RUBIN_JYEAR = 2026.85


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def angsep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    cos_a = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    cos_a = max(-1.0, min(1.0, cos_a))
    return math.degrees(math.acos(cos_a)) * 3600.0


def fetch_with_receipt(
    url: str,
    save_path: Path,
    payload: Any = None,
    form_data: bytes | None = None,
    method: str = "GET",
    timeout: int = 45,
    max_attempts: int = 5,
) -> bytes:
    if save_path.exists():
        return save_path.read_bytes()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    last_err = None
    for attempt in range(1, max_attempts + 1):
        t0 = time.monotonic()
        try:
            if form_data is not None:
                data = form_data
                headers = {"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "SETI-Rubin-V2/1.0"}
            elif payload is not None:
                data = json.dumps(payload).encode("utf-8")
                headers = {"Content-Type": "application/json", "User-Agent": "SETI-Rubin-V2/1.0"}
            else:
                data = None
                headers = {"User-Agent": "SETI-Rubin-V2/1.0"}
            req = urllib.request.Request(url, data=data, method=method, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                rec = {
                    "utc": now_utc(),
                    "url": url,
                    "method": method,
                    "attempt": attempt,
                    "http_status": resp.status,
                    "elapsed_s": round(time.monotonic() - t0, 3),
                    "bytes": len(raw),
                    "sha256": sha256_bytes(raw),
                }
                save_path.write_bytes(raw)
                save_path.with_suffix(save_path.suffix + ".receipt.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
                return raw
        except Exception as exc:
            last_err = repr(exc)
            backoff = min(30, 2 ** attempt)
            print(f"[retry {attempt}/{max_attempts}] {url} err={last_err}; sleeping {backoff}s", flush=True)
            time.sleep(backoff)
    raise RuntimeError(f"Failed {url} after {max_attempts} attempts: {last_err}")


def extract_prior_excluded_ids() -> set[str]:
    prior_rows = []
    sources = [
        ("access_pilot", "work_rubin_20261102/access_pilot/DEVELOPMENT_SELECTION.csv"),
        ("main_188", "work_rubin_20261102/main_acquisition/MAIN_SELECTION_FROZEN.csv"),
        ("ext_2", "work_rubin_20261102/extension_main_acquisition/MAIN_SELECTION_FROZEN.csv"),
    ]
    seen: set[str] = set()
    for tag, rel in sources:
        txt = subprocess.check_output(["git", "-C", str(REPO), "show", f"HEAD:{rel}"], text=True)
        for row in csv.DictReader(io.StringIO(txt)):
            oid = str(row.get("r:diaObjectId") or row.get("diaObjectId") or "").strip()
            if oid and oid not in seen:
                seen.add(oid)
                prior_rows.append({"diaObjectId": oid, "source_cohort": tag, "matched_gaia_source_id": str(row.get("matched_gaia_source_id") or "")})
    with (RESULTS / "EXCLUDED_PRIOR_RUBIN_210IDS.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["diaObjectId", "source_cohort", "matched_gaia_source_id"])
        w.writeheader()
        for r in prior_rows:
            w.writerow(r)
    print(f"Extracted {len(seen)} excluded prior work_rubin_20261102 diaObjectIds", flush=True)
    return seen


def fetch_fink_2026_stats() -> dict[str, Any]:
    months = {}
    for ym in [f"2026{m:02d}" for m in range(2, 12)]:
        raw = fetch_with_receipt(
            f"{FINK_BASE}/api/v1/statistics",
            INPUTS / "metadata" / f"fink_stats_{ym}.json",
            payload={
                "date": ym,
                "columns": "f:night,f:alerts,f:objects,f:visits,f:alerts_u,f:alerts_g,f:alerts_r,f:alerts_i,f:alerts_z,f:alerts_y,f:lsst_schema_version",
                "output-format": "json",
            },
            method="POST",
        )
        rows = json.loads(raw.decode("utf-8"), parse_int=str)
        months[ym] = rows
    total_nights = sum(len(v) for v in months.values())
    total_alerts = sum(int(x.get("f:alerts", 0)) for v in months.values() for x in v)
    (INPUTS / "metadata" / "fink_2026_stats_combined.json").write_text(json.dumps(months, indent=2) + "\n", encoding="utf-8")
    print(f"Fink 2026 stats: {total_nights} nights, {total_alerts:,} alerts", flush=True)
    return months


def parse_float(v: Any) -> float | None:
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def main() -> int:
    excluded_ids = extract_prior_excluded_ids()
    assert len(excluded_ids) >= 210, f"Expected >=210 prior excluded IDs, got {len(excluded_ids)}"
    fetch_fink_2026_stats()

    all_clean_candidates: list[dict[str, Any]] = []
    field_variable_candidates: list[dict[str, Any]] = []

    for fname, ra0, dec0 in DDFS:
        print(f"--- Querying DDF {fname} ({ra0}, {dec0}) ---", flush=True)
        cone_raw = fetch_with_receipt(
            f"{FINK_BASE}/api/v1/conesearch",
            INPUTS / "metadata" / f"fink_cone_{fname}.json",
            payload={"ra": str(ra0), "dec": str(dec0), "radius": "1800", "columns": "r:diaObjectId,f:firstDiaSourceMjdTaiFink,r:ra,r:dec", "output-format": "json"},
            method="POST",
            timeout=60,
        )
        fink_objs = json.loads(cone_raw.decode("utf-8"), parse_int=str)
        print(f"  Fink conesearch {fname}: {len(fink_objs)} objects", flush=True)

        # Fetch ALL Gaia DR3 sources in r=0.52 deg cone so isolation check sees ALL neighbors, not just filtered ones!
        adql = (
            "SELECT source_id, ra, dec, pmra, pmra_error, pmdec, pmdec_error, "
            "parallax, parallax_error, parallax_over_error, ruwe, "
            "phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag, bp_rp, "
            "classprob_dsc_combmod_star, phot_variable_flag, duplicated_source "
            "FROM gaiadr3.gaia_source "
            f"WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra0:.6f}, {dec0:.6f}, 0.52)) = 1 "
            "AND phot_g_mean_mag IS NOT NULL"
        )
        form = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "MAXREC": "50000", "QUERY": adql}).encode()
        gaia_raw = fetch_with_receipt(
            GAIA_TAP_URL,
            INPUTS / "gaia" / f"gaia_dr3_{fname}.csv",
            form_data=form,
            method="POST",
            timeout=60,
        )
        gaia_rows = list(csv.DictReader(io.StringIO(gaia_raw.decode("utf-8"))))
        print(f"  Gaia DR3 {fname}: {len(gaia_rows)} total catalog sources in r=0.52 deg", flush=True)

        # Build fast 0.01-deg grid spatial index on propagated J2026.85 Gaia positions
        dt_yr = EPOCH_RUBIN_JYEAR - EPOCH_GAIA_JYEAR
        grid: dict[tuple[int, int], list[tuple[float, float, dict[str, Any]]]] = collections.defaultdict(list)
        for g in gaia_rows:
            gra = float(g["ra"])
            gdec = float(g["dec"])
            pmra = parse_float(g.get("pmra")) or 0.0
            pmdec = parse_float(g.get("pmdec")) or 0.0
            cos_d = max(0.05, math.cos(math.radians(gdec)))
            ra_p = gra + (pmra * dt_yr) / (3600000.0 * cos_d)
            dec_p = gdec + (pmdec * dt_yr) / 3600000.0
            cell = (int(math.floor(ra_p * 100)), int(math.floor(dec_p * 100)))
            grid[cell].append((ra_p, dec_p, g))

        matched_stars = []
        for f in fink_objs:
            oid = str(f.get("r:diaObjectId") or "")
            if not oid or oid in excluded_ids:
                continue
            fra = parse_float(f.get("r:ra"))
            fdec = parse_float(f.get("r:dec"))
            if fra is None or fdec is None:
                continue
            cx, cy = int(math.floor(fra * 100)), int(math.floor(fdec * 100))
            neighbors = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for r_p, d_p, g in grid.get((cx + dx, cy + dy), ()):
                        sep = angsep_arcsec(fra, fdec, r_p, d_p)
                        if sep <= 3.0:
                            neighbors.append((sep, g))
            if len(neighbors) != 1:
                continue
            sep0, g0 = neighbors[0]
            if sep0 > 1.0:
                continue

            gmag = parse_float(g0.get("phot_g_mean_mag"))
            ruwe = parse_float(g0.get("ruwe"))
            pstar = parse_float(g0.get("classprob_dsc_combmod_star")) or 0.0
            plx_snr = parse_float(g0.get("parallax_over_error")) or 0.0
            plx = parse_float(g0.get("parallax")) or 0.0
            pmra = parse_float(g0.get("pmra")) or 0.0
            pmra_e = parse_float(g0.get("pmra_error"))
            pmdec = parse_float(g0.get("pmdec")) or 0.0
            pmdec_e = parse_float(g0.get("pmdec_error"))
            pm_sig = 0.0
            if pmra_e and pmdec_e and pmra_e > 0 and pmdec_e > 0:
                pm_sig = math.hypot(pmra / pmra_e, pmdec / pmdec_e)
            dup = str(g0.get("duplicated_source") or "").strip().lower() in ("true", "1")

            if gmag is None or not (16.0 <= gmag <= 21.0):
                continue
            if ruwe is None or ruwe >= 1.4 or dup:
                continue
            is_stellar = (pstar >= 0.85) or (plx_snr >= 3.0 and plx > 0.0) or (pm_sig >= 3.0)
            if not is_stellar:
                continue

            rec = {
                "diaObjectId": oid,
                "field": fname,
                "ra_deg": f"{fra:.7f}",
                "dec_deg": f"{fdec:.7f}",
                "gaia_source_id": g0["source_id"],
                "gaia_sep_arcsec": f"{sep0:.4f}",
                "phot_g_mean_mag": f"{gmag:.4f}",
                "bp_rp": g0.get("bp_rp") or "",
                "parallax_mas": g0.get("parallax") or "",
                "ruwe": f"{ruwe:.4f}",
                "classprob_star": f"{pstar:.4f}",
                "phot_variable_flag": g0.get("phot_variable_flag") or "",
            }
            matched_stars.append(rec)
            if str(g0.get("phot_variable_flag") or "").upper() == "VARIABLE":
                field_variable_candidates.append(rec)

        print(f"  Clean isolated Gaia-matched stellar candidates in {fname}: {len(matched_stars)}", flush=True)

        # Fetch Fink /api/v1/objects metadata depth ONLY (never opening lightcurves yet)
        oids_field = [m["diaObjectId"] for m in matched_stars]
        depth_by_oid: dict[str, dict[str, Any]] = {}
        for i in range(0, len(oids_field), 150):
            batch = oids_field[i:i + 150]
            raw_obj = fetch_with_receipt(
                f"{FINK_BASE}/api/v1/objects",
                INPUTS / "metadata" / f"fink_objects_meta_{fname}_{i//150:03d}.json",
                payload={
                    "diaObjectId": ",".join(batch),
                    "columns": "r:diaObjectId,r:nDiaSources,r:u_psfFluxNdata,r:g_psfFluxNdata,r:r_psfFluxNdata,r:i_psfFluxNdata,r:z_psfFluxNdata,r:y_psfFluxNdata,r:firstDiaSourceMjdTai",
                    "output-format": "json",
                },
                method="POST",
                timeout=45,
            )
            for row in json.loads(raw_obj.decode("utf-8"), parse_int=str):
                depth_by_oid[str(row.get("r:diaObjectId") or "")] = row

        for m in matched_stars:
            d = depth_by_oid.get(m["diaObjectId"], {})
            band_counts = {b: int(d.get(f"r:{b}_psfFluxNdata") or 0) for b in ("u", "g", "r", "i", "z", "y")}
            max_band = max(band_counts.values()) if band_counts else 0
            n_dia = int(d.get("r:nDiaSources") or 0)
            m["nDiaSources"] = str(n_dia)
            m["max_band_ndata"] = str(max_band)
            m["band_ndata_summary"] = ";".join(f"{b}:{band_counts[b]}" for b in ("u", "g", "r", "i", "z", "y"))
            if max_band >= 8:
                all_clean_candidates.append(m)

    print(f"Total Gaia-isolated stellar candidates with max_band_ndata >= 8 across 3 DDFs: {len(all_clean_candidates)}", flush=True)

    # Deterministically balance up to 300 stars across COSMOS, EDFS_B, ELAIS_S1 (deduplicated on both diaObjectId and gaia_source_id)
    by_field = collections.defaultdict(list)
    for c in all_clean_candidates:
        by_field[c["field"]].append(c)
    for fname in by_field:
        by_field[fname].sort(key=lambda x: (-int(x["max_band_ndata"]), -int(x["nDiaSources"]), x["diaObjectId"]))

    selected: list[dict[str, Any]] = []
    used_oids: set[str] = set()
    used_gaia: set[str] = set()
    # First pass: take up to 100 from each field; second pass fill up to 300 from remaining highest-depth fields
    for target_per_field in (100, 300):
        for fname, _, _ in DDFS:
            cnt_f = sum(1 for s in selected if s["field"] == fname)
            for c in by_field[fname]:
                if len(selected) >= 300:
                    break
                if target_per_field == 100 and cnt_f >= 100:
                    break
                if c["diaObjectId"] in used_oids or c["gaia_source_id"] in used_gaia or c["diaObjectId"] in excluded_ids:
                    continue
                selected.append(c)
                used_oids.add(c["diaObjectId"])
                used_gaia.add(c["gaia_source_id"])
                cnt_f += 1

    assert len(selected) >= 100, f"Too few R1 stars selected: {len(selected)} (need >= 100)"
    fieldnames = [
        "diaObjectId", "field", "ra_deg", "dec_deg", "gaia_source_id", "gaia_sep_arcsec",
        "phot_g_mean_mag", "bp_rp", "parallax_mas", "ruwe", "classprob_star",
        "phot_variable_flag", "nDiaSources", "max_band_ndata", "band_ndata_summary",
    ]
    with (RESULTS / "R1_COHORT_FROZEN.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in selected:
            w.writerow(r)

    # Select 20 disjoint explicit astrophysical controls (10 mdwarf_flare + 10 in_tns/Gaia VARIABLE)
    controls: list[dict[str, Any]] = []
    ctrl_oids = set(used_oids) | excluded_ids
    for tag_name, need in [("mdwarf_flare", 10), ("in_tns", 10)]:
        raw_t = fetch_with_receipt(
            f"{FINK_BASE}/api/v1/tags",
            INPUTS / "metadata" / f"fink_ctrl_tag_{tag_name}.json",
            payload={
                "tag": tag_name, "n": 50,
                "startdate": "2026-11-05 00:00:00", "stopdate": "2026-11-16 00:00:00",
                "columns": "r:diaObjectId,r:ra,r:dec,r:band,r:midpointMjdTai",
                "output-format": "json",
            },
            method="POST",
            timeout=45,
        )
        trows = json.loads(raw_t.decode("utf-8"), parse_int=str)
        added = 0
        for tr in trows:
            oid = str(tr.get("r:diaObjectId") or "")
            if not oid or oid in ctrl_oids:
                continue
            ctrl_oids.add(oid)
            controls.append({
                "diaObjectId": oid,
                "field": f"CTRL_{tag_name.upper()}",
                "ra_deg": str(tr.get("r:ra") or ""),
                "dec_deg": str(tr.get("r:dec") or ""),
                "gaia_source_id": f"FINK_TAG_{tag_name}",
                "phot_g_mean_mag": "",
                "bp_rp": "",
                "phot_variable_flag": tag_name.upper(),
            })
            added += 1
            if added >= need:
                break

    with (RESULTS / "R1_CONTROLS_FROZEN.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["diaObjectId", "field", "ra_deg", "dec_deg", "gaia_source_id", "phot_g_mean_mag", "bp_rp", "phot_variable_flag"])
        w.writeheader()
        for c in controls:
            w.writerow(c)

    # Freeze Spor R2 Southern 538 Science stars from table1_master_catalog_1083stars.csv
    r2_stars = [
        r for r in csv.DictReader(TABLE1_CSV.open(encoding="utf-8"))
        if r["role"] == "SCIENCE" and float(r["dec_deg"]) <= 15.0
    ]
    assert len(r2_stars) == 538, f"Expected 538 Southern stars, got {len(r2_stars)}"
    with (RESULTS / "R2_SOUTHERN_538STARS_FROZEN.csv").open("w", newline="", encoding="utf-8") as fh:
        fn2 = ["star", "common_name", "ra_deg", "dec_deg", "dist_pc", "within_10pc", "n_exoplanets", "n_instruments", "phases"]
        w = csv.DictWriter(fh, fieldnames=fn2)
        w.writeheader()
        for r in r2_stars:
            w.writerow({k: r[k] for k in fn2})

    # Seal METHOD_LOCK.json + IMPLEMENTATION_LOCK.json BEFORE any Stage-2 photometry
    lock_files = [
        "results/EXCLUDED_PRIOR_RUBIN_210IDS.csv",
        "results/R1_COHORT_FROZEN.csv",
        "results/R1_CONTROLS_FROZEN.csv",
        "results/R2_SOUTHERN_538STARS_FROZEN.csv",
        "scripts/rubin_v2_detector.py",
    ]
    hashes = {rel: sha256_file(WS / rel) for rel in lock_files}
    lock_utc = now_utc()
    method_lock = {
        "locked_utc": lock_utc,
        "campaign": "RUBIN_V2_SPOR_R1_R2",
        "r1_selected_stars": len(selected),
        "r1_by_field": {fn: sum(1 for s in selected if s["field"] == fn) for fn, _, _ in DDFS},
        "r1_controls": len(controls),
        "r2_southern_science_stars": len(r2_stars),
        "prior_excluded_rubin_ids": len(excluded_ids),
        "thresholds": {
            "dim_ratio_max": 10.0 ** (-0.4 * 0.30),
            "dim_z_min": 5.0,
            "flash_ratio_min": 10.0 ** (0.4 * 0.50),
            "flash_z_min": 6.0,
            "baseline_window_days": 180.0,
            "min_base_visits": 5,
            "min_base_dates": 3,
            "min_base_snr": 10.0,
        },
        "sha256": hashes,
    }
    impl_lock = {
        "locked_utc": lock_utc,
        "detector_script": "scripts/rubin_v2_detector.py",
        "detector_sha256": hashes["scripts/rubin_v2_detector.py"],
        "method_lock_sha256": None,
    }
    (RESULTS / "METHOD_LOCK.json").write_text(json.dumps(method_lock, indent=2) + "\n", encoding="utf-8")
    impl_lock["method_lock_sha256"] = sha256_file(RESULTS / "METHOD_LOCK.json")
    (RESULTS / "IMPLEMENTATION_LOCK.json").write_text(json.dumps(impl_lock, indent=2) + "\n", encoding="utf-8")

    print(f"STAGE1 COMPLETE & LOCKED at {lock_utc}: R1={len(selected)} stars {method_lock['r1_by_field']}, Controls={len(controls)}, R2={len(r2_stars)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
