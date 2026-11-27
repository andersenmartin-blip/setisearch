#!/usr/bin/env python3
"""Stage 1 live acquisition: NASA TESS 2-min SPOC photometry across 680 Milky Way stars (Spor N7)."""
from __future__ import annotations

import concurrent.futures
import csv
import json
import math
import socket
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from astropy.io import fits

# Force IPv4 cleanly in every session
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(*args: Any, **kwargs: Any) -> Any:
    return [r for r in _orig_getaddrinfo(*args, **kwargs) if r[0] == socket.AF_INET]


socket.getaddrinfo = _ipv4_getaddrinfo

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
INP = ROOT / "inputs_n7_20261127"
CAT_DIR = INP / "catalogs"
LC_DIR = INP / "tess_lc"
MASTER_CSV = ROOT / "setisearch/zenodo_package/tables/table1_master_catalog_1083stars.csv"
GAIA_CSV = ROOT / "inputs_n5_20261127/gaia/gaia_dr3_1096.csv"

EXTERNAL_BENCHMARKS = [
    {"star": "BOYAJIAN", "common_name": "Boyajian's Star (KIC 8462852)", "ra_j2000": 301.564397, "dec_j2000": 44.456887, "dist_pc": 450.8, "tic_id": "185336364"},
    {"star": "HD139139", "common_name": "HD 139139 (Random Transiter)", "ra_j2000": 234.274083, "dec_j2000": -19.144611, "dist_pc": 107.6, "tic_id": "100100827"},
    {"star": "TOI700", "common_name": "TOI-700 (Multi-Planet M-dwarf)", "ra_j2000": 97.096833, "dec_j2000": -65.579333, "dist_pc": 31.1, "tic_id": "150428135"},
    {"star": "WD1145", "common_name": "WD 1145+017 (Disintegrating Planetesimals)", "ra_j2000": 177.139875, "dec_j2000": 1.483222, "dist_pc": 146.1, "tic_id": "278661431"},
]
INTERNAL_BENCHMARK_STARS = {"PROXIMACEN", "AUMIC", "L9859", "BETAPIC"}


def _f(v: Any, default: float | None = None) -> float | None:
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def _http_post_form(url: str, params: dict[str, str], timeout: int = 35) -> bytes:
    data = urllib.parse.urlencode(params).encode("utf-8")
    last_err: Exception | None = None
    for i in range(5):
        try:
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "SETI-N7/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"POST failed {url}: {last_err}")


def _http_get(url: str, timeout: int = 35) -> bytes:
    last_err: Exception | None = None
    for i in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETI-N7/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GET failed {url}: {last_err}")


def build_priority_targets() -> list[dict[str, Any]]:
    gaia_map = {r["star"]: r for r in csv.DictReader(GAIA_CSV.open("r", encoding="utf-8"))}
    targets: list[dict[str, Any]] = []
    for r in csv.DictReader(MASTER_CSV.open("r", encoding="utf-8")):
        is_10 = r["within_10pc"] == "True"
        is_etz = r["etz_qualified"] == "True"
        is_ell = r["ellipsoid_180d"] == "True"
        n_pl = int(r["n_exoplanets"] or 0)
        if not (is_10 or is_etz or is_ell or n_pl > 0):
            continue
        tags = []
        if is_10:
            tags.append("<10pc")
        if is_etz:
            tags.append("ETZ")
        if is_ell:
            tags.append("Ellipsoid180d")
        if n_pl > 0:
            tags.append("ExoHost")
        g = gaia_map.get(r["star"], {})
        ra = _f(g.get("ra")) or float(r["ra_deg"])
        dec = _f(g.get("dec")) or float(r["dec_deg"])
        pmra = _f(g.get("pmra"), 0.0) or 0.0
        pmdec = _f(g.get("pmdec"), 0.0) or 0.0
        if g.get("ra"):
            # Propagate Gaia J2016.0 -> J2000.0 (TIC epoch)
            cosd = max(0.05, math.cos(math.radians(dec)))
            ra_j2000 = (ra - 16.0 * (pmra / 3.6e6) / cosd) % 360.0
            dec_j2000 = max(-89.99, min(89.99, dec - 16.0 * (pmdec / 3.6e6)))
        else:
            ra_j2000, dec_j2000 = ra, dec
        targets.append({
            "star": r["star"],
            "common_name": r["common_name"],
            "cohort_tags": "|".join(tags),
            "is_benchmark": "True" if r["star"] in INTERNAL_BENCHMARK_STARS else "False",
            "ra_j2000": round(ra_j2000, 6),
            "dec_j2000": round(dec_j2000, 6),
            "dist_pc": _f(r["dist_pc"], -1.0),
            "within_10pc": r["within_10pc"],
            "etz_qualified": r["etz_qualified"],
            "ellipsoid_180d": r["ellipsoid_180d"],
            "n_exoplanets": n_pl,
            "gaia_gmag": _f(g.get("phot_g_mean_mag")),
            "preset_tic": "",
        })

    for b in EXTERNAL_BENCHMARKS:
        targets.append({
            "star": b["star"],
            "common_name": b["common_name"],
            "cohort_tags": "EXTERNAL_BENCHMARK",
            "is_benchmark": "True",
            "ra_j2000": b["ra_j2000"],
            "dec_j2000": b["dec_j2000"],
            "dist_pc": b["dist_pc"],
            "within_10pc": "False",
            "etz_qualified": "False",
            "ellipsoid_180d": "False",
            "n_exoplanets": 0,
            "gaia_gmag": None,
            "preset_tic": b["tic_id"],
        })
    return targets


def fetch_nasa_exoplanets() -> tuple[list[dict[str, str]], dict[str, str]]:
    out = CAT_DIR / "nasa_exoplanets_pscomppars.csv"
    if not (out.exists() and out.stat().st_size > 10000):
        q = "select hostname,pl_name,tic_id,ra,dec,pl_orbper,pl_trandep,pl_trandur,tran_flag from pscomppars where tic_id is not null"
        url = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?" + urllib.parse.urlencode({"query": q, "format": "csv"})
        raw = _http_get(url, timeout=60)
        out.write_bytes(raw)
    rows = list(csv.DictReader(out.open("r", encoding="utf-8")))
    tic_by_host: dict[str, str] = {}
    for r in rows:
        hk = "".join(ch for ch in r["hostname"].upper() if ch.isalnum())
        tid = r["tic_id"].replace("TIC", "").strip()
        if hk and tid.isdigit():
            tic_by_host[hk] = tid
    return rows, tic_by_host


def _tic_cone_one(t: dict[str, Any]) -> dict[str, Any]:
    req_cone = json.dumps({
        "service": "Mast.Catalogs.Tic.Cone", "format": "json",
        "params": {"ra": t["ra_j2000"], "dec": t["dec_j2000"], "radius": 0.012},
    })
    raw = _http_post_form("https://mast.stsci.edu/api/v0/invoke", {"request": req_cone}, timeout=25)
    data = json.loads(raw.decode("utf-8")).get("data", [])
    if not data:
        return {"star": t["star"], "tic_id": "", "tmag": "", "teff": "", "rad_rsun": "", "mass_msun": "", "contratio": "", "match_sep_arcsec": ""}

    gmag = t.get("gaia_gmag")
    # Prioritize bright stars (Tmag < 16) within 25" matching Gaia G - 0.5, else nearest bright star
    def score(row: dict[str, Any]) -> tuple[float, float]:
        sep = _f(row.get("dstArcSec"), 99.0) or 99.0
        tm = _f(row.get("Tmag"), 25.0) or 25.0
        if gmag is not None:
            dm = abs(tm - (gmag - 0.5))
            return (0.0 if sep < 20.0 else 1.0, dm + 0.05 * sep)
        return (0.0 if (sep < 15.0 and tm < 15.0) else 1.0, sep + 0.5 * tm)

    best = sorted(data, key=score)[0]
    return {
        "star": t["star"],
        "tic_id": str(best.get("ID", "")),
        "tmag": best.get("Tmag", ""),
        "teff": best.get("Teff", ""),
        "rad_rsun": best.get("rad", ""),
        "mass_msun": best.get("mass", ""),
        "contratio": best.get("contratio", ""),
        "match_sep_arcsec": round(_f(best.get("dstArcSec"), 99.0) or 99.0, 3),
    }


def resolve_all_tics(targets: list[dict[str, Any]], tic_by_host: dict[str, str]) -> dict[str, dict[str, Any]]:
    cache_p = CAT_DIR / "tic_crossmatch_680.csv"
    cached: dict[str, dict[str, Any]] = {}
    if cache_p.exists() and cache_p.stat().st_size > 1000:
        for r in csv.DictReader(cache_p.open("r", encoding="utf-8")):
            cached[r["star"]] = r
        if len(cached) >= len(targets):
            return cached

    need = [t for t in targets if t["star"] not in cached]
    results = dict(cached)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(_tic_cone_one, t): t for t in need}
        for i, fut in enumerate(concurrent.futures.as_completed(futs), 1):
            t = futs[fut]
            try:
                rec = fut.result()
            except Exception:
                rec = {"star": t["star"], "tic_id": "", "tmag": "", "teff": "", "rad_rsun": "", "mass_msun": "", "contratio": "", "match_sep_arcsec": ""}
            # Override with preset benchmark TIC or exact exoplanet archive host TIC when known
            if t["preset_tic"]:
                rec["tic_id"] = t["preset_tic"]
            elif not rec["tic_id"]:
                cname_key = "".join(ch for ch in t["common_name"].split("(")[0].upper() if ch.isalnum())
                rec["tic_id"] = tic_by_host.get(t["star"], "") or tic_by_host.get(cname_key, "")
            results[t["star"]] = rec
            if i % 100 == 0 or i == len(need):
                print(f"  TIC crossmatch: {i}/{len(need)}", flush=True)

    fields = ["star", "tic_id", "tmag", "teff", "rad_rsun", "mass_msun", "contratio", "match_sep_arcsec"]
    with cache_p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for t in targets:
            w.writerow(results[t["star"]])
    return results


def discover_mast_tess_spoc(tic_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    idx_p = CAT_DIR / "mast_tess_spoc_2min_index.csv"
    by_tic: dict[str, list[dict[str, Any]]] = {}
    if idx_p.exists() and idx_p.stat().st_size > 5000:
        for r in csv.DictReader(idx_p.open("r", encoding="utf-8")):
            by_tic.setdefault(r["target_name"], []).append(r)
        return by_tic

    all_rows: list[dict[str, Any]] = []
    uniq = sorted(set(x for x in tic_ids if x.isdigit()))
    for i in range(0, len(uniq), 80):
        chunk = uniq[i:i + 80]
        req_obj = json.dumps({
            "service": "Mast.Caom.Filtered", "format": "json",
            "params": {
                "columns": "obs_id,target_name,t_exptime,dataURL,t_min,t_max",
                "filters": [
                    {"paramName": "obs_collection", "values": ["TESS"]},
                    {"paramName": "provenance_name", "values": ["SPOC"]},
                    {"paramName": "dataproduct_type", "values": ["timeseries"]},
                    {"paramName": "target_name", "values": chunk},
                ],
            },
        })
        raw = _http_post_form("https://mast.stsci.edu/api/v0/invoke", {"request": req_obj}, timeout=40)
        data = json.loads(raw.decode("utf-8")).get("data", [])
        for row in data:
            u = str(row.get("dataURL", ""))
            texp = _f(row.get("t_exptime"), 999.0) or 999.0
            if u.endswith("_lc.fits") and texp <= 130.0:
                rec = {
                    "target_name": str(row.get("target_name", "")),
                    "obs_id": str(row.get("obs_id", "")),
                    "t_exptime": texp,
                    "t_min": _f(row.get("t_min"), 0.0) or 0.0,
                    "t_max": _f(row.get("t_max"), 0.0) or 0.0,
                    "dataURL": u,
                }
                all_rows.append(rec)
                by_tic.setdefault(rec["target_name"], []).append(rec)
        print(f"  MAST CAOM SPOC chunk {i//80 + 1}/{(len(uniq)+79)//80}: cum_files={len(all_rows)}", flush=True)

    with idx_p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["target_name", "obs_id", "t_exptime", "t_min", "t_max", "dataURL"])
        w.writeheader()
        w.writerows(all_rows)
    return by_tic


def _download_one_fits(job: tuple[str, str, list[dict[str, Any]]]) -> tuple[str, str, str, int]:
    star, tic, sectors = job
    # Prefer latest sector first, fall back to earlier sector if needed
    ordered = sorted(sectors, key=lambda x: -float(x["t_max"]))
    for s in ordered[:3]:
        fname = f"{star}_TIC{tic}_{Path(s['dataURL']).name}"
        out = LC_DIR / fname
        if out.exists() and out.stat().st_size > 10000:
            try:
                with fits.open(out, memmap=False) as hdul:
                    if len(hdul[1].data) >= 2000:
                        return star, fname, str(hdul[0].header.get("SECTOR", "")), len(hdul[1].data)
            except Exception:
                out.unlink(missing_ok=True)
        try:
            url = "https://mast.stsci.edu/api/v0.1/Download/file?uri=" + urllib.parse.quote(s["dataURL"], safe="")
            blob = _http_get(url, timeout=45)
            out.write_bytes(blob)
            with fits.open(out, memmap=False) as hdul:
                nrows = len(hdul[1].data)
                sec = str(hdul[0].header.get("SECTOR", ""))
                if nrows >= 2000:
                    return star, fname, sec, nrows
        except Exception:
            out.unlink(missing_ok=True)
    return star, "", "", 0


def main() -> int:
    CAT_DIR.mkdir(parents=True, exist_ok=True)
    LC_DIR.mkdir(parents=True, exist_ok=True)

    print("1/4 Building priority Milky Way target list + NASA Exoplanet Archive TAP...", flush=True)
    targets = build_priority_targets()
    exo_rows, tic_by_host = fetch_nasa_exoplanets()
    print(f"  Targets: {len(targets)}, NASA pscomppars rows: {len(exo_rows)}", flush=True)

    print("2/4 Crossmatching targets to TIC v8.2...", flush=True)
    tic_map = resolve_all_tics(targets, tic_by_host)
    matched_tics = [v["tic_id"] for v in tic_map.values() if v["tic_id"].isdigit()]
    print(f"  TIC matched: {len(matched_tics)}/{len(targets)}", flush=True)

    print("3/4 Discovering TESS SPOC 2-min light curves via MAST CAOM...", flush=True)
    spoc_by_tic = discover_mast_tess_spoc(matched_tics)
    jobs = [(t["star"], tic_map[t["star"]]["tic_id"], spoc_by_tic[tic_map[t["star"]]["tic_id"]])
            for t in targets if tic_map[t["star"]]["tic_id"] in spoc_by_tic]
    print(f"  Stars with TESS SPOC 2-min coverage: {len(jobs)}/{len(targets)}", flush=True)

    print("4/4 Downloading 1 primary SPOC 2-min FITS per covered star...", flush=True)
    dl_map: dict[str, tuple[str, str, int]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(_download_one_fits, j) for j in jobs]
        for i, fut in enumerate(concurrent.futures.as_completed(futs), 1):
            st, fname, sec, nrows = fut.result()
            if fname:
                dl_map[st] = (fname, sec, nrows)
            if i % 50 == 0 or i == len(jobs):
                print(f"  Downloaded verified FITS: {len(dl_map)} ({i}/{len(jobs)} processed)", flush=True)

    man_rows: list[dict[str, Any]] = []
    for t in targets:
        st = t["star"]
        if st not in dl_map:
            continue
        tm = tic_map[st]
        fname, sec, nrows = dl_map[st]
        man_rows.append({
            "star": st,
            "common_name": t["common_name"],
            "cohort_tags": t["cohort_tags"],
            "is_benchmark": t["is_benchmark"],
            "ra_j2000": t["ra_j2000"],
            "dec_j2000": t["dec_j2000"],
            "dist_pc": t["dist_pc"],
            "within_10pc": t["within_10pc"],
            "etz_qualified": t["etz_qualified"],
            "ellipsoid_180d": t["ellipsoid_180d"],
            "n_exoplanets": t["n_exoplanets"],
            "tic_id": tm["tic_id"],
            "tmag": tm["tmag"],
            "teff": tm["teff"],
            "rad_rsun": tm["rad_rsun"],
            "mass_msun": tm["mass_msun"],
            "contratio": tm["contratio"],
            "n_spoc_sectors": len(spoc_by_tic[tm["tic_id"]]),
            "primary_sector": sec,
            "primary_fits_file": fname,
            "raw_fits_rows": nrows,
        })

    man_p = CAT_DIR / "n7_milky_way_tess_manifest.csv"
    with man_p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(man_rows[0].keys()))
        w.writeheader()
        w.writerows(man_rows)

    summary = {
        "targets_total": len(targets),
        "tic_matched": len(matched_tics),
        "tess_spoc_covered": len(jobs),
        "tess_primary_fits_downloaded": len(man_rows),
        "nasa_exoplanet_rows": len(exo_rows),
    }
    (INP / "STAGE1_MANIFEST.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("STAGE1_DONE:", json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
