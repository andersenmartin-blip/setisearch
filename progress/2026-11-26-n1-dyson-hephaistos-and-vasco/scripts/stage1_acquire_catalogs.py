#!/usr/bin/env python3
"""
Stage 1: Acquire all raw public survey catalogs and Hephaistos cutouts for Spor N1:
  - N1A: Gaia DR3, 2MASS, AllWISE, NERSC Legacy DR10 Tractor, Fink Rubin LSST,
         SIMBAD, and 4 FITS cutouts (DSS2, LS DR10, unWISE, VLASS) for A-G
  - N1B: Blind Gaia DR3 + 2MASS + AllWISE cones across COSMOS, EDFS_B, ELAIS_S1 (0.50 deg)
  - N1C: NERSC Legacy DR10 Tractor bricks + Pan-STARRS1 DR2 COSMOS (0.25 deg)
Seals METHOD_LOCK.json and IMPLEMENTATION_LOCK.json before running n1_analyzer.py.
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import io
import json
import math
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits

WS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/analysis_workspace/work_n1_20261126_dyson_hephaistos_and_vasco")
INPUTS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/inputs_n1_20261126")
RESULTS = WS / "results"

GAIA_TAP = "https://gaia.ari.uni-heidelberg.de/tap/sync"
IRSA_TAP = "https://irsa.ipac.caltech.edu/TAP/sync"
FINK_CONE = "https://api.lsst.fink-portal.org/api/v1/conesearch"
SIMBAD_TAP = "https://simbad.cds.unistra.fr/simbad/sim-tap/sync"
PS1_URL = "https://catalogs.mast.stsci.edu/api/v0.1/panstarrs/dr2/mean.csv"

HEPHAISTOS_7 = [
    ("A", "3496509309189181184"),
    ("B", "4843191593270342656"),
    ("C", "4649396037451459712"),
    ("D", "2660349163149053824"),
    ("E", "3190232820489766656"),
    ("F", "2956570141274256512"),
    ("G", "2644370304260053376"),
]

DDFS = [
    ("COSMOS", 150.1190, 2.2058),
    ("EDFS_B", 63.6000, -48.0000),
    ("ELAIS_S1", 9.4500, -44.0000),
]


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def angsep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    cos_a = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_a)))) * 3600.0


def fetch_bytes(url: str, save_path: Path | None = None, form_dict: dict[str, str] | None = None, json_payload: Any = None, timeout: int = 45, max_attempts: int = 4) -> bytes:
    if save_path and save_path.exists():
        return save_path.read_bytes()
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
    last_err = None
    for attempt in range(1, max_attempts + 1):
        t0 = time.monotonic()
        try:
            headers = {"User-Agent": "SETI-N1/1.0"}
            data = None
            method = "GET"
            if form_dict is not None:
                data = urllib.parse.urlencode(form_dict).encode("utf-8")
                headers["Content-Type"] = "application/x-www-form-urlencoded"
                method = "POST"
            elif json_payload is not None:
                data = json.dumps(json_payload).encode("utf-8")
                headers["Content-Type"] = "application/json"
                method = "POST"
            req = urllib.request.Request(url, data=data, method=method, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if save_path:
                    save_path.write_bytes(raw)
                    rec = {"utc": now_utc(), "url": url, "status": r.status, "elapsed_s": round(time.monotonic() - t0, 3), "bytes": len(raw), "sha256": sha256_bytes(raw)}
                    save_path.with_suffix(save_path.suffix + ".receipt.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
                return raw
        except Exception as exc:
            last_err = repr(exc)
            time.sleep(min(20, 2 ** attempt))
    raise RuntimeError(f"Failed {url}: {last_err}")


def discover_ls_tractor_urls(ra: float, dec: float) -> list[str]:
    html = fetch_bytes(f"https://www.legacysurvey.org/viewer/data-for-radec/?ra={ra:.6f}&dec={dec:.6f}&layer=ls-dr10", timeout=20).decode("utf-8", errors="replace")
    urls = re.findall(r'https://[^\s"<>]+/dr10/south/tractor/[^\s"<>]+\.fits', html)
    if not urls:
        urls = re.findall(r'https://[^\s"<>]+tractor-[0-9pm]+\.fits', html)
    return list(dict.fromkeys(urls))


def extract_tractor_rows(fits_bytes: bytes) -> tuple[list[dict[str, Any]], list[float]]:
    with fits.open(io.BytesIO(fits_bytes)) as hdul:
        d = hdul[1].data
        cols = [c for c in ("brickid", "objid", "ra", "dec", "type", "flux_g", "flux_r", "flux_i", "flux_z", "flux_w1", "flux_w2", "flux_w3", "flux_w4", "maskbits") if c in d.names]
        ras = np.array(d["ra"], dtype=float)
        decs = np.array(d["dec"], dtype=float)
        bounds = [float(np.min(ras)), float(np.max(ras)), float(np.min(decs)), float(np.max(decs))]
        out = []
        arrs = {c: d[c] for c in cols}
        for i in range(len(d)):
            row = {}
            for c in cols:
                v = arrs[c][i]
                if isinstance(v, (bytes, np.bytes_)):
                    v = v.decode("utf-8", errors="replace").strip()
                row[c] = v.item() if hasattr(v, "item") else v
            row["ls_id"] = f"{row.get('brickid','')}_{row.get('objid','')}"
            out.append(row)
        return out, bounds


def write_tractor_csv(rows: list[dict[str, Any]], out_path: Path) -> None:
    fn = ["ls_id", "brickid", "objid", "ra", "dec", "type", "flux_g", "flux_r", "flux_i", "flux_z", "flux_w1", "flux_w2", "flux_w3", "flux_w4", "maskbits"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fn)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fn})


def acquire_hephaistos() -> None:
    print("=== N1A: Acquiring 7 Hephaistos Candidates A-G ===", flush=True)
    ids_csv = ",".join(gid for _, gid in HEPHAISTOS_7)
    g_raw = fetch_bytes(
        GAIA_TAP,
        INPUTS / "hephaistos" / "hephaistos_gaia.csv",
        form_dict={
            "REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
            "QUERY": (
                "SELECT source_id, ra, dec, pmra, pmra_error, pmdec, pmdec_error, parallax, parallax_error, "
                "ruwe, duplicated_source, phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag, bp_rp "
                f"FROM gaiadr3.gaia_source WHERE source_id IN ({ids_csv})"
            ),
        },
    )
    gaia_rows = {r["source_id"]: r for r in csv.DictReader(io.StringIO(g_raw.decode("utf-8")))}

    tm_rows_all: list[dict[str, str]] = []
    wise_rows_all: list[dict[str, str]] = []
    ls_rows_all: list[dict[str, Any]] = []
    fink_matches: dict[str, Any] = {}
    simbad_matches: dict[str, Any] = {}
    brick_cache: dict[str, list[dict[str, Any]]] = {}

    for label, gid in HEPHAISTOS_7:
        g = gaia_rows[gid]
        ra, dec = float(g["ra"]), float(g["dec"])
        print(f"  Candidate {label} ({gid}): ({ra:.5f}, {dec:.5f})", flush=True)

        # 2MASS & AllWISE via IRSA
        q2m = f"SELECT designation, ra, dec, j_m, j_msigcom, h_m, h_msigcom, k_m, k_msigcom, ph_qual FROM fp_psc WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra:.6f}, {dec:.6f}, 0.0028))=1"
        r2m = fetch_bytes(IRSA_TAP, form_dict={"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": q2m})
        tm_rows_all.extend(list(csv.DictReader(io.StringIO(r2m.decode("utf-8")))))

        qw = f"SELECT designation, ra, dec, w1mpro, w1sigmpro, w2mpro, w2sigmpro, w3mpro, w3sigmpro, w4mpro, w4sigmpro, w3snr, w4snr, cc_flags, ext_flg FROM allwise_p3as_psd WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra:.6f}, {dec:.6f}, 0.0033))=1"
        rw = fetch_bytes(IRSA_TAP, form_dict={"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": qw})
        wise_rows_all.extend(list(csv.DictReader(io.StringIO(rw.decode("utf-8")))))

        # Exact NERSC Tractor brick extraction within 20"
        b_urls = discover_ls_tractor_urls(ra, dec)
        for bu in b_urls[:1]:
            if bu not in brick_cache:
                fb = fetch_bytes(bu, timeout=60)
                b_rows, _ = extract_tractor_rows(fb)
                brick_cache[bu] = b_rows
            for lr in brick_cache[bu]:
                if angsep_arcsec(ra, dec, float(lr["ra"]), float(lr["dec"])) <= 20.0:
                    ls_rows_all.append(lr)

        # Fink Rubin LSST check (10")
        try:
            fraw = fetch_bytes(FINK_CONE, json_payload={"ra": f"{ra:.6f}", "dec": f"{dec:.6f}", "radius": "10", "columns": "r:diaObjectId,f:firstDiaSourceMjdTaiFink,r:ra,r:dec", "output-format": "json"}, timeout=20)
            fink_matches[label] = json.loads(fraw.decode("utf-8"), parse_int=str)
        except Exception:
            fink_matches[label] = []

        # SIMBAD check (10")
        try:
            qs = f"SELECT main_id, otype, sp_type, ra, dec FROM basic WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra:.6f}, {dec:.6f}, 0.0028))=1"
            sraw = fetch_bytes(SIMBAD_TAP, form_dict={"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": qs}, timeout=20)
            simbad_matches[label] = list(csv.DictReader(io.StringIO(sraw.decode("utf-8"))))
        except Exception:
            simbad_matches[label] = []

        # 4 FITS Cutouts per candidate (28 files total)
        cut_specs = [
            ("dss2", f"https://archive.stsci.edu/cgi-bin/dss_search?v=poss2ukstu_red&r={ra:.6f}&d={dec:.6f}&e=J2000&h=1.2&w=1.2&f=fits&c=none"),
            ("ls_dr10", f"https://www.legacysurvey.org/viewer/fits-cutout?ra={ra:.6f}&dec={dec:.6f}&layer=ls-dr10&pixscale=0.262&size=128"),
            ("unwise", f"https://www.legacysurvey.org/viewer/fits-cutout?ra={ra:.6f}&dec={dec:.6f}&layer=unwise-neo7&pixscale=2.75&size=32"),
            ("vlass", f"https://www.legacysurvey.org/viewer/fits-cutout?ra={ra:.6f}&dec={dec:.6f}&layer=vlass1.2&pixscale=1.0&size=64"),
        ]
        for cname, curl in cut_specs:
            cp = INPUTS / "cutouts" / f"heph_{label}_{cname}.fits"
            try:
                fetch_bytes(curl, cp, timeout=25, max_attempts=3)
            except Exception as exc:
                print(f"    [note] cutout {label} {cname}: {exc}", flush=True)

    # Save merged N1A tables
    def write_dicts(rows: list[dict[str, Any]], p: Path, default_cols: list[str]) -> None:
        cols = list(rows[0].keys()) if rows else default_cols
        with p.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerow(r)

    write_dicts(tm_rows_all, INPUTS / "hephaistos" / "hephaistos_2mass.csv", ["designation", "ra", "dec", "j_m", "h_m", "k_m"])
    write_dicts(wise_rows_all, INPUTS / "hephaistos" / "hephaistos_allwise.csv", ["designation", "ra", "dec", "w1mpro", "w2mpro", "w3mpro", "w4mpro"])
    write_tractor_csv(ls_rows_all, INPUTS / "hephaistos" / "hephaistos_ls_dr10.csv")
    (INPUTS / "hephaistos" / "hephaistos_fink_matches.json").write_text(json.dumps(fink_matches, indent=2) + "\n", encoding="utf-8")
    (INPUTS / "hephaistos" / "hephaistos_simbad.json").write_text(json.dumps(simbad_matches, indent=2) + "\n", encoding="utf-8")


def acquire_ddf_and_vasco() -> None:
    print("=== N1B + N1C: Acquiring 3 DDF Survey Catalogs (Gaia, 2MASS, AllWISE, NERSC LS-DR10, PS1) ===", flush=True)
    brick_bounds: dict[str, list[list[float]]] = {}
    brick_cache: dict[str, tuple[list[dict[str, Any]], list[float]]] = {}

    for fname, ra0, dec0 in DDFS:
        print(f"--- DDF {fname} ({ra0}, {dec0}) ---", flush=True)
        q_gaia = (
            "SELECT source_id, ra, dec, pmra, pmdec, parallax, parallax_over_error, ruwe, "
            "duplicated_source, astrometric_params_solved, phot_g_n_obs, phot_g_mean_mag, "
            "phot_bp_mean_mag, phot_rp_mean_mag, bp_rp, classprob_dsc_combmod_star "
            "FROM gaiadr3.gaia_source "
            f"WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra0:.6f}, {dec0:.6f}, 0.50))=1 AND phot_g_mean_mag IS NOT NULL"
        )
        fetch_bytes(GAIA_TAP, INPUTS / "dyson_blind" / f"gaia_{fname}.csv", form_dict={"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "MAXREC": "50000", "QUERY": q_gaia}, timeout=45)

        q_tm = (
            "SELECT designation, ra, dec, j_m, j_msigcom, h_m, h_msigcom, k_m, k_msigcom, ph_qual "
            f"FROM fp_psc WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra0:.6f}, {dec0:.6f}, 0.52))=1"
        )
        fetch_bytes(IRSA_TAP, INPUTS / "dyson_blind" / f"twomass_{fname}.csv", form_dict={"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "MAXREC": "50000", "QUERY": q_tm}, timeout=45)

        q_w = (
            "SELECT designation, ra, dec, w1mpro, w1sigmpro, w2mpro, w2sigmpro, w3mpro, w3sigmpro, w4mpro, w4sigmpro, w3snr, w4snr, cc_flags, ext_flg "
            f"FROM allwise_p3as_psd WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra0:.6f}, {dec0:.6f}, 0.52))=1"
        )
        fetch_bytes(IRSA_TAP, INPUTS / "dyson_blind" / f"allwise_{fname}.csv", form_dict={"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "MAXREC": "50000", "QUERY": q_w}, timeout=45)

        # Discover and stream the ~4 NERSC Tractor FITS bricks covering +/-0.14 deg core of this DDF
        ls_csv = INPUTS / "dyson_blind" / f"ls_dr10_{fname}.csv"
        cos_d = max(0.1, math.cos(math.radians(dec0)))
        brick_urls = set()
        for dra in (-0.12 / cos_d, 0.0, 0.12 / cos_d):
            for ddec in (-0.12, 0.0, 0.12):
                for bu in discover_ls_tractor_urls(ra0 + dra, dec0 + ddec):
                    brick_urls.add(bu)
        print(f"  Discovered {len(brick_urls)} NERSC Tractor bricks for {fname} core: {sorted(u.split('/')[-1] for u in brick_urls)}", flush=True)
        ls_rows: list[dict[str, Any]] = []
        b_bounds = []
        for bu in sorted(brick_urls):
            if bu not in brick_cache:
                fb = fetch_bytes(bu, timeout=60)
                brick_cache[bu] = extract_tractor_rows(fb)
            rows_b, bd = brick_cache[bu]
            ls_rows.extend(rows_b)
            b_bounds.append(bd)
        brick_bounds[fname] = b_bounds
        if not ls_csv.exists():
            write_tractor_csv(ls_rows, ls_csv)
            print(f"  Saved {len(ls_rows):,} Tractor rows to {ls_csv.name}", flush=True)

    bounds_p = INPUTS / "vasco" / "ls_dr10_brick_bounds.json"
    bounds_p.parent.mkdir(parents=True, exist_ok=True)
    bounds_p.write_text(json.dumps(brick_bounds, indent=2) + "\n", encoding="utf-8")

    # Pan-STARRS1 DR2 in COSMOS 0.25 deg core
    ps1_p = INPUTS / "vasco" / "ps1_cosmos_0p25deg.csv"
    if not ps1_p.exists():
        ps1_url = f"{PS1_URL}?ra=150.119&dec=2.2058&radius=0.25&pagesize=50000&columns=objID,raMean,decMean,nDetections,rMeanPSFMag,iMeanPSFMag,iMeanKronMag,zMeanPSFMag"
        fetch_bytes(ps1_url, ps1_p, timeout=60)
        print("  Saved COSMOS PS1 DR2 catalog.", flush=True)


def seal_locks() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    lock_files = [
        "scripts/n1_analyzer.py",
    ]
    hashes = {rel: sha256_file(WS / rel) for rel in lock_files}
    utc = now_utc()
    ml = {
        "locked_utc": utc,
        "campaign": "SPOR_N1_DYSON_HEPHAISTOS_AND_VASCO",
        "hephaistos_ids": [gid for _, gid in HEPHAISTOS_7],
        "ddfs": [f for f, _, _ in DDFS],
        "thresholds": {
            "n1b_w1_minus_w3_min": 1.0,
            "n1b_w1_minus_w4_min": 2.5,
            "n1b_gamma_min": 0.02,
            "n1b_delta_chi2_min": 25.0,
            "n1c_gaia_ls_match_radius_arcsec": 3.0,
            "n1c_ps1_ls_match_radius_arcsec": 2.5,
            "n1c_extreme_dim_mag": 1.5,
        },
        "sha256": hashes,
    }
    il = {"locked_utc": utc, "analyzer_script": "scripts/n1_analyzer.py", "analyzer_sha256": hashes["scripts/n1_analyzer.py"], "method_lock_sha256": None}
    (RESULTS / "METHOD_LOCK.json").write_text(json.dumps(ml, indent=2) + "\n", encoding="utf-8")
    il["method_lock_sha256"] = sha256_file(RESULTS / "METHOD_LOCK.json")
    (RESULTS / "IMPLEMENTATION_LOCK.json").write_text(json.dumps(il, indent=2) + "\n", encoding="utf-8")
    print(f"METHOD_LOCK & IMPLEMENTATION_LOCK sealed at {utc}", flush=True)


def main() -> int:
    seal_locks()
    acquire_hephaistos()
    acquire_ddf_and_vasco()
    print("STAGE 1 COMPLETE.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
