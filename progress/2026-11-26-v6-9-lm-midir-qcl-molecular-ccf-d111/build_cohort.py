#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D111 (V6.9) Stage-1 Metadata-Only Cohort Builder & Prospective Seal:
  - Queries ONLY public metadata APIs/catalogs (MAST JWST NIRSpec G395H/G395M & MIRI/MRS,
    ESO TAP CRIRES+ K-band, NASA Exoplanet Archive pscomppars, IRSA 2MASS, ESA Gaia DR3).
  - NEVER downloads raw science files and asserts `inputs_d111_v6_9` does NOT exist at seal.
  - Enforces strict 0-overlap against all 36 prior Companion Archives A-AJ
    (1,085 prior coords + 4,436 prior science dp_ids + 46 format-probe IDs = 4,482 excluded IDs).
  - Adds the BRAND-NEW 98th spectral arm (`JWST_NIRSPEC_G395M`; spectrographs stay 67).
  - Seals 7 immutable Stage-1 files into `METHOD_LOCK.json` and `LOCK_RECEIPT.json`.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent
ROOT = WS.parent.parent
ARCHIVES_DIR = ROOT / "archives"
RAW_DIR = ROOT / "inputs_d111_v6_9"
ARCHIVE_AJ = ARCHIVES_DIR / "SETI_D110_V6_8_OPTICAL_NIR_SPECTROPOLARIMETRY_RESULTS_2026-11-26.zip"
ARCHIVE_AJ_SHA = "11b2ba8cdb2a8b7aeaa97687fc75bf5d30ab82d7b92a880c5d29509f96e621dd"

sys.path.insert(0, str(WS))
import v6_9_detector as det  # noqa: E402

MAST_API = "https://mast.stsci.edu/api/v0/invoke"
ESO_TAP = "https://archive.eso.org/tap_obs/sync"
EXOPLANET_TAP = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
IRSA_TAP = "https://irsa.ipac.caltech.edu/TAP/sync"
GAIA_TAP = "https://gea.esac.esa.int/tap-server/tap/sync"

COHORT_COLS = [
    "instrument", "canonical_target", "common_name", "role", "subrole",
    "panchromatic_bridge", "is_prior_bridge", "s_ra", "s_dec", "dist_pc", "within_10pc",
    "phot_g_mag", "j_mag", "h_mag", "ks_mag", "teff_k", "n_exoplanets",
    "dp_id", "obs_id", "miri_subband", "resolving_power", "regime",
    "mjd_obs", "t_exptime", "f1_rel", "f1_url", "est_bytes", "min_prior_sep_arcsec",
]


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _ang_sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    c = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c)))) * 3600.0


def _canon_key(s: str) -> str:
    return "".join(ch for ch in s.upper() if ch.isalnum())


def _mast_invoke(service: str, params: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    payload = urllib.parse.urlencode({"request": json.dumps({"service": service, "format": "json", "params": params})}).encode()
    for attempt in range(5):
        try:
            req = urllib.request.Request(MAST_API, data=payload, headers={"User-Agent": "SETI-D111-Stage1/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", errors="ignore"))
        except Exception:
            if attempt == 4:
                raise
            time.sleep(1.5 * (attempt + 1))
    return {}


def _tap_csv(url: str, query_str: str, mode: str = "adql", timeout: int = 45) -> list[dict[str, str]]:
    for attempt in range(5):
        try:
            if mode == "adql":
                data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query_str}).encode()
                req = urllib.request.Request(url, data=data, headers={"User-Agent": "SETI-D111-Stage1/1.0"})
            else:
                full = url + "?" + urllib.parse.urlencode({"query": query_str, "format": "csv"})
                req = urllib.request.Request(full, headers={"User-Agent": "SETI-D111-Stage1/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                txt = r.read().decode("utf-8", errors="ignore")
            return list(csv.DictReader(io.StringIO(txt)))
        except Exception:
            if attempt == 4:
                raise
            time.sleep(1.5 * (attempt + 1))
    return []


def _build_prior_v68_snapshot_and_exclusions() -> tuple[
    dict[str, Any], list[dict[str, Any]], set[str], list[str], dict[str, tuple[float, float]], dict[str, dict[str, str]]
]:
    assert ARCHIVE_AJ.exists(), f"Missing Archive AJ: {ARCHIVE_AJ}"
    assert _sha256_file(ARCHIVE_AJ) == ARCHIVE_AJ_SHA, "Archive AJ SHA-256 mismatch!"

    with zipfile.ZipFile(ARCHIVE_AJ) as zf:
        def _zcsv(suffix: str) -> list[dict[str, str]]:
            nm = next(n for n in zf.namelist() if n.endswith(suffix))
            return list(csv.DictReader(io.StringIO(zf.read(nm).decode("utf-8"))))

        def _zjson(suffix: str) -> Any:
            nm = next(n for n in zf.namelist() if n.endswith(suffix))
            return json.loads(zf.read(nm).decode("utf-8"))

        sum_aj = _zjson("/results/SUMMARY.json")
        u1012_rows = _zcsv("/results/UNIFIED_PANCHROMATIC_V6_8_SYNTHESIS_1012STARS.csv")
        br179_rows = _zcsv("/results/PANCHROMATIC_BRIDGE_179STARS_V68.csv")
        ell1012_rows = _zcsv("/results/MULTIEVENT_ELLIPSOID_1012STARS.csv")
        comb_u = _zcsv("/results/ALLSKY_COMB_V4_1_UNIFIED_D079_D110.csv")
        comb_c = _zcsv("/results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D110.csv")
        eirp_d110 = _zcsv("/results/POLARIZED_EIRP_UPPER_LIMITS_D110.csv")
        cohort110 = _zcsv("FROZEN_COHORT_D110.csv")
        prov110 = _zcsv("/results/EXPOSURE_PROVENANCE_D110.csv")
        px110 = _zjson("PRIOR_EXCLUSION_VERIFICATION.json")
        man110 = _zjson("FULL_D110_INPUT_MANIFEST.json")
        snap109 = _zjson("PRIOR_V6_7_PHASES_SNAPSHOT.json")

    u1012_map = {r["star"]: r for r in u1012_rows}
    star_coords = {r["star"]: (float(r["ra_deg"]), float(r["dec_deg"])) for r in ell1012_rows}
    assert len(u1012_map) == 1012 and len(star_coords) == 1012

    # 1,077 prior coords + 8 brand-new D110 coords = 1,085 prior excluded coords
    prior_coords = list(px110["excluded_targets_coordinate_registry"])
    assert len(prior_coords) == 1077
    new_d110_coords: dict[str, tuple[float, float]] = {}
    for cr in cohort110:
        if cr.get("is_prior_bridge") == "False":
            st = cr["canonical_target"]
            if st not in new_d110_coords:
                new_d110_coords[st] = (float(cr["s_ra"]), float(cr["s_dec"]))
                prior_coords.append({"star": st, "ra_deg": float(cr["s_ra"]), "dec_deg": float(cr["s_dec"])})
    assert len(new_d110_coords) == 8 and len(prior_coords) == 1085

    fmt_probes = sorted(px110["format_check_excluded_dp_ids"])
    d110_dps = {str(o["dp_id"]).strip() for o in man110["observations"]}
    prior_dp_ids = set(px110["excluded_dp_ids"]) | d110_dps
    assert len(d110_dps) == 87
    assert len(prior_dp_ids) == 4436, f"Expected 4436 prior science dp_ids, got {len(prior_dp_ids)}"

    # Merge D110 distinct nights and radiometry
    nights_by_star: dict[str, set[int]] = {
        st: set(int(x) for x in lst) for st, lst in snap109["prior_star_distinct_nights"].items()
    }
    for pr in prov110:
        st = pr["star"]
        try:
            mjd = float(pr["mjd_obs"])
            nights_by_star.setdefault(st, set()).add(int(round(mjd)))
        except Exception:
            pass

    rad_cat: dict[str, list[dict[str, Any]]] = {
        st: list(lst) for st, lst in snap109["prior_star_radiometric_catalog"].items()
    }
    for er in eirp_d110:
        st = er["star"]
        rad_cat.setdefault(st, []).append({
            "ph": "D110", "inst": er["instrument"], "bid": er["band_id"], "cat": "BEAMED",
            "wa": float(er["wave_bary_a"]), "fl": float(er["flux_lim_erg_cm2_s"]),
            "li": float(er["l_iso_mw"]), "p10": float(er["p_beam_10m_kw"]),
        })

    snap = {
        "schema": "PRIOR_V6_8_PHASES_SNAPSHOT",
        "d110_summary_headline": sum_aj["unified_1012star_panchromatic_v6_8_synthesis"],
        "d110_root_summary": {
            "total_calibration_trials_d110": sum_aj["synthetic_calibration_7911_trials"]["total_trials"],
            "total_integration_hours_d110": sum_aj["cohort"]["integration_hours_d110"],
        },
        "prior_unified_1012_rows": u1012_rows,
        "prior_bridge_rows": br179_rows,
        "prior_ellipsoid_1012_rows": ell1012_rows,
        "prior_allsky_comb_unified_rows": comb_u,
        "prior_allsky_comb_candidate_rows": comb_c,
        "prior_star_distinct_nights": {st: sorted(nights_by_star.get(st, set())) for st in sorted(u1012_map)},
        "prior_star_radiometric_catalog": {st: rad_cat.get(st, []) for st in sorted(u1012_map)},
    }
    return snap, prior_coords, prior_dp_ids, fmt_probes, star_coords, u1012_map


def _pick_x1d_product(obsid: int, excl_all_dp: set[str], used_dps: set[str]) -> dict[str, Any] | None:
    prods = _mast_invoke("Mast.Caom.Products", {"obsid": str(obsid)}, timeout=40).get("data", [])
    cands: list[dict[str, Any]] = []
    for p in prods:
        fn = str(p.get("productFilename") or "").strip()
        if not fn.endswith("_x1d.fits"):
            continue
        if fn in excl_all_dp or fn in used_dps:
            continue
        sz = int(p.get("size") or 0)
        if not (8_000 <= sz <= 5_242_880):
            continue
        cl = int(p.get("calib_level") or 0)
        uri = str(p.get("dataURI") or "").strip()
        if not uri:
            continue
        # Prefer Level-3 1D combined spectrum over Level-2
        cands.append({"fn": fn, "sz": sz, "cl": cl, "uri": uri})
    if not cands:
        return None
    return sorted(cands, key=lambda x: (-x["cl"], x["sz"], x["fn"]))[0]


def main() -> int:
    assert not RAW_DIR.exists(), f"{RAW_DIR} must NOT exist before Stage-1 seal!"
    print("Extracting PRIOR_V6_8_PHASES_SNAPSHOT from Archive AJ and checking 4,482 excluded dp_ids...")
    snap, prior_coords, prior_dp_ids, fmt_probes, star_coords, u1012_map = _build_prior_v68_snapshot_and_exclusions()
    excl_all_dp = prior_dp_ids | set(fmt_probes)

    prior_coord_list = [(float(c["ra_deg"]), float(c["dec_deg"])) for c in prior_coords]

    def _min_sep_prior(ra: float, dec: float) -> float:
        best = 1e9
        for r0, d0 in prior_coord_list:
            if abs(d0 - dec) > 2.0 and best < 1e8:
                continue
            s = _ang_sep_arcsec(ra, dec, r0, d0)
            if s < best:
                best = s
        if best > 1e8:
            best = min(_ang_sep_arcsec(ra, dec, r0, d0) for r0, d0 in prior_coord_list)
        return best

    def _nearest_u1012(ra: float, dec: float) -> tuple[str | None, float]:
        best_s, best_d = None, 1e9
        for st, (r0, d0) in star_coords.items():
            if abs(d0 - dec) > 0.25:
                continue
            d = _ang_sep_arcsec(ra, dec, r0, d0)
            if d < best_d:
                best_d, best_s = d, st
        return best_s, best_d

    print("Querying NASA Exoplanet Archive (pscomppars) for exoplanet hosts...")
    exo_rows = _tap_csv(
        EXOPLANET_TAP,
        "SELECT hostname, ra, dec, sy_dist, sy_gaiamag, sy_vmag, sy_jmag, sy_hmag, sy_kmag, st_teff, sy_pnum "
        "FROM pscomppars WHERE ra IS NOT NULL AND dec IS NOT NULL",
        mode="exo",
        timeout=35,
    )
    exo_hosts: dict[str, dict[str, Any]] = {}
    for row in exo_rows:
        hn = row["hostname"].strip()
        if hn in exo_hosts:
            continue
        try:
            exo_hosts[hn] = {
                "hostname": hn,
                "canonical": _canon_key(hn),
                "ra": float(row["ra"]),
                "dec": float(row["dec"]),
                "dist_pc": float(row["sy_dist"]) if row.get("sy_dist") else 50.0,
                "g_mag": float(row["sy_gaiamag"]) if row.get("sy_gaiamag") else (float(row["sy_vmag"]) if row.get("sy_vmag") else None),
                "j_mag": float(row["sy_jmag"]) if row.get("sy_jmag") else None,
                "h_mag": float(row["sy_hmag"]) if row.get("sy_hmag") else None,
                "ks_mag": float(row["sy_kmag"]) if row.get("sy_kmag") else None,
                "teff_k": float(row["st_teff"]) if row.get("st_teff") else 4800.0,
                "n_pl": int(float(row["sy_pnum"])) if row.get("sy_pnum") else 1,
            }
        except Exception:
            pass
    exo_list = list(exo_hosts.values())
    print(f"  Loaded {len(exo_list)} unique confirmed exoplanet hosts.")

    def _nearest_exo(ra: float, dec: float) -> tuple[dict[str, Any] | None, float]:
        best_e, best_d = None, 1e9
        for e in exo_list:
            if abs(e["dec"] - dec) > 0.12:
                continue
            d = _ang_sep_arcsec(ra, dec, e["ra"], e["dec"])
            if d < best_d:
                best_d, best_e = d, e
        return best_e, best_d

    # 1. Query MAST JWST NIRSpec G395H/G395M (non-timeseries: spectrum & cube)
    print("Querying MAST for JWST NIRSpec F290LP;G395H & G395M non-timeseries observations...")
    nirspec_raw = _mast_invoke("Mast.Caom.Filtered", {
        "columns": "obsid,obs_id,target_name,s_ra,s_dec,filters,instrument_name,t_exptime,t_min,dataproduct_type",
        "filters": [
            {"paramName": "obs_collection", "values": ["JWST"]},
            {"paramName": "instrument_name", "values": ["NIRSPEC/SLIT", "NIRSPEC/IFU"]},
            {"paramName": "filters", "values": ["F290LP;G395H", "F290LP;G395M"]},
            {"paramName": "dataproduct_type", "values": ["spectrum", "cube"]},
            {"paramName": "calib_level", "values": [3]},
            {"paramName": "dataRights", "values": ["PUBLIC"]},
            {"paramName": "intentType", "values": ["science"]},
        ],
        "pagesize": 5000,
        "page": 1,
    }).get("data", [])

    # 2. Query MAST JWST MIRI/MRS IFU
    print("Querying MAST for JWST MIRI/MRS IFU observations...")
    miri_raw = _mast_invoke("Mast.Caom.Filtered", {
        "columns": "obsid,obs_id,target_name,s_ra,s_dec,filters,instrument_name,t_exptime,t_min,dataproduct_type",
        "filters": [
            {"paramName": "obs_collection", "values": ["JWST"]},
            {"paramName": "instrument_name", "values": ["MIRI/IFU"]},
            {"paramName": "calib_level", "values": [3]},
            {"paramName": "dataRights", "values": ["PUBLIC"]},
            {"paramName": "intentType", "values": ["science"]},
        ],
        "pagesize": 5000,
        "page": 1,
    }).get("data", [])

    # 3. Query ESO TAP CRIRES+ K-band (1.95-2.49 um, R>=40000, snr>=25)
    print("Querying ESO TAP for fresh CRIRES+ K-band (R=43k/86k) spectra...")
    crires_raw = _tap_csv(
        ESO_TAP,
        "SELECT dp_id, target_name, s_ra, s_dec, em_min*1e6 AS wmin, em_max*1e6 AS wmax, "
        "em_res_power, t_exptime, t_min, snr, access_estsize, obs_release_date "
        "FROM ivoa.ObsCore "
        "WHERE instrument_name='CRIRES' AND dataproduct_type='spectrum' "
        "AND obs_release_date < '2026-11-26' "
        "AND em_min >= 1.90e-6 AND em_res_power >= 40000 AND snr >= 25.0",
        mode="adql",
        timeout=60,
    )

    used_dps: set[str] = set()
    brand_new_meta: dict[str, dict[str, Any]] = {}
    cand_obs_jwst: list[dict[str, Any]] = []

    def _classify_target(ra: float, dec: float) -> tuple[str, bool, float, dict[str, Any] | None] | None:
        st, d_p = _nearest_u1012(ra, dec)
        if st is not None and d_p <= 120.0:
            return st, True, _min_sep_prior(ra, dec), None
        msep = _min_sep_prior(ra, dec)
        if msep >= 600.0:
            ex, d_e = _nearest_exo(ra, dec)
            if ex is not None and d_e <= 30.0:
                ck = ex["canonical"]
                if ck not in u1012_map:
                    return ck, False, msep, ex
        return None

    # --- Select NIRSpec G395H & G395M candidate observations ---
    g395h_bridge_map: dict[str, dict[str, Any]] = {}
    g395h_new_map: dict[str, dict[str, Any]] = {}
    g395m_cands: list[dict[str, Any]] = []

    for r in nirspec_raw:
        oid_s = str(r.get("obs_id") or "").strip()
        if not oid_s or oid_s in excl_all_dp or str(r.get("obsid")) in excl_all_dp:
            continue
        ra, dec = r.get("s_ra"), r.get("s_dec")
        if ra is None or dec is None:
            continue
        cls = _classify_target(float(ra), float(dec))
        if cls is None:
            continue
        st, is_br, msep, ex = cls
        filt = str(r.get("filters") or "")
        inst_d = "JWST_NIRSPEC_G395M" if "G395M" in filt else "JWST_NIRSPEC_G395H"
        rec = {
            "inst_d": inst_d, "st": st, "is_br": is_br, "msep": msep, "ex": ex,
            "obsid": int(r["obsid"]), "obs_id": oid_s, "filt": filt,
            "dist_pc": float(u1012_map[st]["dist_pc"]) if is_br else float(ex["dist_pc"]),
            "t_exptime": float(r.get("t_exptime") or 600.0),
            "mjd_obs": float(r.get("t_min") or 60000.0),
            "rp": 1000.0 if inst_d == "JWST_NIRSPEC_G395M" else 2700.0,
        }
        if inst_d == "JWST_NIRSPEC_G395M":
            g395m_cands.append(rec)
        elif is_br:
            # Prefer nearest stars and SLIT/IFU highest exptime
            if st not in g395h_bridge_map or rec["t_exptime"] > g395h_bridge_map[st]["t_exptime"]:
                g395h_bridge_map[st] = rec
        else:
            if st not in g395h_new_map or rec["t_exptime"] > g395h_new_map[st]["t_exptime"]:
                g395h_new_map[st] = rec

    # Also check any non-excluded non-timeseries G395M stellar calibration/brown-dwarf targets at >= 600" if g395m needs depth
    g395h_bridges_sorted = sorted(g395h_bridge_map.values(), key=lambda x: (x["dist_pc"], x["st"]))[:22]
    g395h_new_sorted = sorted(g395h_new_map.values(), key=lambda x: (x["dist_pc"], x["st"]))[:10]

    # Pick unique G395M stars (prioritize bridges + new)
    seen_g395m: set[str] = set()
    g395m_selected: list[dict[str, Any]] = []
    for rec in sorted(g395m_cands, key=lambda x: (x["is_br"] is False, x["dist_pc"], -x["t_exptime"], x["st"])):
        if rec["st"] not in seen_g395m:
            seen_g395m.add(rec["st"])
            g395m_selected.append(rec)
        if len(g395m_selected) >= 6:
            break

    # --- Select MIRI/MRS candidate observations (prioritize ch1-short/medium, ch2-medium/long, ch3-short -> up to 2 subbands/star) ---
    SUBBAND_PRIORITY = {"CH2-MEDIUM": 0, "CH3-SHORT": 1, "CH1-MEDIUM": 2, "CH1-SHORT": 3, "CH2-LONG": 4, "CH1-LONG": 5, "CH2-SHORT": 6, "CH3-MEDIUM": 7}
    miri_by_star: dict[tuple[str, str], dict[str, Any]] = {}
    for r in miri_raw:
        oid_s = str(r.get("obs_id") or "").strip()
        if not oid_s or oid_s in excl_all_dp or str(r.get("obsid")) in excl_all_dp:
            continue
        filt = str(r.get("filters") or "").upper()
        if filt not in SUBBAND_PRIORITY:
            continue
        ra, dec = r.get("s_ra"), r.get("s_dec")
        if ra is None or dec is None:
            continue
        cls = _classify_target(float(ra), float(dec))
        if cls is None:
            continue
        st, is_br, msep, ex = cls
        rec = {
            "inst_d": "JWST_MIRI_MRS", "st": st, "is_br": is_br, "msep": msep, "ex": ex,
            "obsid": int(r["obsid"]), "obs_id": oid_s, "filt": filt,
            "dist_pc": float(u1012_map[st]["dist_pc"]) if is_br else float(ex["dist_pc"]),
            "t_exptime": float(r.get("t_exptime") or 600.0),
            "mjd_obs": float(r.get("t_min") or 60000.0),
            "rp": 2500.0,
        }
        key = (st, filt)
        if key not in miri_by_star or rec["t_exptime"] > miri_by_star[key]["t_exptime"]:
            miri_by_star[key] = rec

    # Pick <= 2 priority subbands per star for closest 14 MIRI bridges + all MIRI brand-new exoplanet hosts
    miri_stars_br = sorted({st for st, _ in miri_by_star if miri_by_star[(st, _)]["is_br"]}, key=lambda s: float(u1012_map[s]["dist_pc"]))
    # Ensure 16CYGB is included!
    miri_br_pick = [s for s in miri_stars_br[:13]]
    if "16CYGB" in miri_stars_br and "16CYGB" not in miri_br_pick:
        miri_br_pick.append("16CYGB")
    miri_new_pick = sorted({st for st, _ in miri_by_star if not miri_by_star[(st, _)]["is_br"]})

    miri_selected: list[dict[str, Any]] = []
    for st in miri_br_pick + miri_new_pick:
        subs = [v for (s0, _), v in miri_by_star.items() if s0 == st]
        subs.sort(key=lambda x: SUBBAND_PRIORITY.get(x["filt"], 99))
        miri_selected.extend(subs[:2])

    cand_obs_jwst = g395h_bridges_sorted + g395h_new_sorted + g395m_selected + miri_selected
    print(f"Resolving lightweight Level-3 x1d.fits MAST products for {len(cand_obs_jwst)} JWST observations (parallel)...")

    def _resolve_jwst(rec: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
        prods = _mast_invoke("Mast.Caom.Products", {"obsid": str(rec["obsid"])}, timeout=45).get("data", [])
        cands = []
        for p in prods:
            fn = str(p.get("productFilename") or "").strip()
            if not fn.endswith("_x1d.fits") or fn in excl_all_dp:
                continue
            sz = int(p.get("size") or 0)
            if not (8_000 <= sz <= 5_242_880):
                continue
            cl = int(p.get("calib_level") or 0)
            uri = str(p.get("dataURI") or "").strip()
            if uri:
                cands.append({"fn": fn, "sz": sz, "cl": cl, "uri": uri})
        if not cands:
            return rec, None
        best = sorted(cands, key=lambda x: (-x["cl"], x["sz"], x["fn"]))[0]
        return rec, best

    resolved_jwst: list[tuple[dict[str, Any], dict[str, Any]]] = []
    with ThreadPoolExecutor(max_workers=8) as ex_pool:
        for rec, prod in ex_pool.map(_resolve_jwst, cand_obs_jwst):
            if prod is not None and prod["fn"] not in used_dps and prod["fn"] not in excl_all_dp:
                used_dps.add(prod["fn"])
                resolved_jwst.append((rec, prod))

    # --- Select ESO CRIRES+ K-band observations (highest SNR per star) ---
    cr_br_map: dict[str, dict[str, Any]] = {}
    cr_new_map: dict[str, dict[str, Any]] = {}
    for r in crires_raw:
        dp = str(r.get("dp_id") or "").strip()
        if not dp or dp in excl_all_dp or dp in used_dps:
            continue
        try:
            ra, dec = float(r["s_ra"]), float(r["s_dec"])
            snr = float(r["snr"])
            rp = float(r.get("em_res_power") or 86000.0)
        except Exception:
            continue
        cls = _classify_target(ra, dec)
        if cls is None:
            continue
        st, is_br, msep, ex = cls
        sz = int(float(r.get("access_estsize") or 1200) * 1024)
        rec = {
            "inst_d": "ESO_CRIRES_PLUS", "st": st, "is_br": is_br, "msep": msep, "ex": ex,
            "dp_id": dp, "obs_id": dp, "filt": "CRIRES_PLUS_K",
            "dist_pc": float(u1012_map[st]["dist_pc"]) if is_br else float(ex["dist_pc"]),
            "t_exptime": float(r.get("t_exptime") or 120.0),
            "mjd_obs": float(r.get("t_min") or 60000.0),
            "rp": rp, "snr": snr, "est_bytes": max(100_000, sz),
        }
        if is_br:
            if st not in cr_br_map or snr > cr_br_map[st]["snr"]:
                cr_br_map[st] = rec
        else:
            if st not in cr_new_map or snr > cr_new_map[st]["snr"]:
                cr_new_map[st] = rec

    cr_bridges_sorted = sorted(cr_br_map.values(), key=lambda x: (x["dist_pc"], -x["snr"]))[:16]
    cr_new_sorted = sorted(cr_new_map.values(), key=lambda x: (x["dist_pc"], -x["snr"]))[:18]
    for rec in cr_bridges_sorted + cr_new_sorted:
        used_dps.add(rec["dp_id"])

    # Register all brand-new target metadata & verify 2MASS Ks/H photometry where needed
    for rec in [r for r, _ in resolved_jwst] + cr_bridges_sorted + cr_new_sorted:
        if not rec["is_br"] and rec["st"] not in brand_new_meta:
            ex = dict(rec["ex"])
            ex["min_prior_sep_arcsec"] = round(rec["msep"], 2)
            brand_new_meta[rec["st"]] = ex

    print(f"Enriching 2MASS photometry for {len(brand_new_meta)} brand-new exoplanet hosts...")
    for st, bm in sorted(brand_new_meta.items()):
        if bm.get("h_mag") is None or bm.get("ks_mag") is None:
            q_i = (
                f"SELECT TOP 1 j_m, h_m, k_m FROM fp_psc "
                f"WHERE CONTAINS(POINT('ICRS',ra,dec), CIRCLE('ICRS',{bm['ra']:.5f},{bm['dec']:.5f},0.004))=1"
            )
            irows = _tap_csv(IRSA_TAP, q_i, mode="exo", timeout=20)
            if irows:
                if irows[0].get("j_m"): bm["j_mag"] = float(irows[0]["j_m"])
                if irows[0].get("h_m"): bm["h_mag"] = float(irows[0]["h_m"])
                if irows[0].get("k_m"): bm["ks_mag"] = float(irows[0]["k_m"])

    # Build FROZEN_COHORT_D111.csv rows
    cohort_rows: list[dict[str, Any]] = []

    def _emit_row(inst_d: str, st: str, is_br: bool, msep: float, dp_id: str, obs_id: str, subband: str, rp: float, mjd: float, expt: float, f1_rel: str, f1_url: str, est_b: int) -> None:
        if is_br:
            ur = u1012_map[st]
            ra0, dec0 = star_coords[st]
            common = ur["common_name"]
            role = ur["role"]
            subrole = ur.get("subrole", "IR_QCL_CCF_BRIDGE")
            dist_pc = float(ur["dist_pc"])
            w10 = ur["within_10pc"] == "True"
            g_m = float(ur["phot_g_mag"]) if ur.get("phot_g_mag") else None
            j_m = float(ur["j_mag"]) if ur.get("j_mag") else None
            h_m = float(ur["h_mag"]) if ur.get("h_mag") else None
            ks_m = float(ur["ks_mag"]) if ur.get("ks_mag") else None
            teff = float(ur["teff_k"])
            npl = int(float(ur.get("n_exoplanets") or 0))
            msep_eff = round(_ang_sep_arcsec(ra0, dec0, ra0, dec0), 2)
        else:
            bm = brand_new_meta[st]
            ra0, dec0 = bm["ra"], bm["dec"]
            common = f"{bm['hostname']} (EXOHOST IR QCL/CCF)"
            role = "SCIENCE"
            subrole = "EXOPLANET_HOST_IR_LM"
            dist_pc = float(bm["dist_pc"])
            w10 = dist_pc <= 10.0
            g_m, j_m, h_m, ks_m = bm.get("g_mag"), bm.get("j_mag"), bm.get("h_mag"), bm.get("ks_mag")
            teff = float(bm.get("teff_k") or 4800.0)
            npl = int(bm.get("n_pl") or 1)
            msep_eff = bm["min_prior_sep_arcsec"]

        regime = "MIDIR" if inst_d == "JWST_MIRI_MRS" else ("LM_IR" if "NIRSPEC" in inst_d else "NIR")
        cohort_rows.append({
            "instrument": inst_d,
            "canonical_target": st,
            "common_name": common,
            "role": role,
            "subrole": subrole,
            "panchromatic_bridge": str(is_br),
            "is_prior_bridge": str(is_br),
            "s_ra": f"{ra0:.6f}",
            "s_dec": f"{dec0:.6f}",
            "dist_pc": f"{dist_pc:.5f}",
            "within_10pc": str(w10),
            "phot_g_mag": "" if g_m is None else f"{g_m:.4f}",
            "j_mag": "" if j_m is None else f"{j_m:.4f}",
            "h_mag": "" if h_m is None else f"{h_m:.4f}",
            "ks_mag": "" if ks_m is None else f"{ks_m:.4f}",
            "teff_k": f"{teff:.1f}",
            "n_exoplanets": npl,
            "dp_id": dp_id,
            "obs_id": obs_id,
            "miri_subband": subband,
            "resolving_power": f"{rp:.1f}",
            "regime": regime,
            "mjd_obs": f"{mjd:.6f}",
            "t_exptime": f"{expt:.2f}",
            "f1_rel": f1_rel,
            "f1_url": f1_url,
            "est_bytes": est_b,
            "min_prior_sep_arcsec": msep_eff,
        })

    for rec, prod in resolved_jwst:
        fn = prod["fn"]
        url = f"https://mast.stsci.edu/api/v0.1/Download/file?uri={urllib.parse.quote(prod['uri'], safe='')}"
        _emit_row(
            rec["inst_d"], rec["st"], rec["is_br"], rec["msep"], fn, rec["obs_id"],
            rec["filt"], rec["rp"], rec["mjd_obs"], rec["t_exptime"],
            f"{rec['inst_d']}/{rec['st']}/{fn}", url, prod["sz"],
        )

    for rec in cr_bridges_sorted + cr_new_sorted:
        dp = rec["dp_id"]
        fn = f"{dp}.fits"
        url = f"https://dataportal.eso.org/dataportal_new/file/{dp}"
        _emit_row(
            "ESO_CRIRES_PLUS", rec["st"], rec["is_br"], rec["msep"], dp, rec["obs_id"],
            "CRIRES_PLUS_K", rec["rp"], rec["mjd_obs"], rec["t_exptime"],
            f"ESO_CRIRES_PLUS/{rec['st']}/{fn}", url, rec["est_bytes"],
        )

    cohort_rows.sort(key=lambda r: (r["instrument"], r["canonical_target"], r["miri_subband"], r["dp_id"]))

    unique_stars = sorted({r["canonical_target"] for r in cohort_rows})
    bridge_stars = sorted({r["canonical_target"] for r in cohort_rows if r["is_prior_bridge"] == "True"})
    new_stars = sorted({r["canonical_target"] for r in cohort_rows if r["is_prior_bridge"] == "False"})
    by_inst = defaultdict(int)
    for r in cohort_rows:
        by_inst[r["instrument"]] += 1

    assert by_inst["JWST_NIRSPEC_G395M"] >= 2, f"Need >=2 JWST_NIRSPEC_G395M exposures, got {by_inst}"
    assert by_inst["JWST_NIRSPEC_G395H"] >= 15
    assert by_inst["JWST_MIRI_MRS"] >= 10
    assert by_inst["ESO_CRIRES_PLUS"] >= 20
    assert len(bridge_stars) >= 25
    assert len(new_stars) >= 18
    assert all(float(brand_new_meta[s]["min_prior_sep_arcsec"]) >= 600.0 for s in new_stars)
    assert all(r["dp_id"] not in excl_all_dp and r["obs_id"] not in excl_all_dp for r in cohort_rows)

    proj_bytes = sum(int(r["est_bytes"]) for r in cohort_rows)
    assert proj_bytes <= 400 * 1024 * 1024, f"Projected download too large: {proj_bytes / 1048576:.1f} MiB"

    # Write Stage-1 files (still NO RAW_DIR!)
    with (WS / "FROZEN_COHORT_D111.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COHORT_COLS)
        w.writeheader()
        for r in cohort_rows:
            w.writerow(r)

    (WS / "PRIOR_V6_8_PHASES_SNAPSHOT.json").write_text(json.dumps(snap, separators=(",", ":")) + "\n", encoding="utf-8")

    pex_out = {
        "schema": "D111_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D111",
        "verified_utc": datetime.now(timezone.utc).isoformat(),
        "prior_phases_covered": "D001-D110 (Companion Archives A-AJ)",
        "n_prior_excluded_coords": len(prior_coords),
        "n_prior_excluded_dp_ids": len(prior_dp_ids),
        "n_format_check_excluded_dp_ids": len(fmt_probes),
        "d111_total_stars": len(unique_stars),
        "d111_brand_new_unique_stars": len(new_stars),
        "d111_prior_bridge_stars": len(bridge_stars),
        "d111_total_observations": len(cohort_rows),
        "d111_total_physical_files": len(cohort_rows),
        "d111_dp_id_overlap_count": 0,
        "brand_new_min_prior_sep_arcsec": min(brand_new_meta[s]["min_prior_sep_arcsec"] for s in new_stars),
        "format_check_excluded_dp_ids": fmt_probes,
        "excluded_dp_ids": sorted(prior_dp_ids),
        "excluded_targets_coordinate_registry": prior_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pex_out, indent=2) + "\n", encoding="utf-8")

    ir_cfg = {
        "schema": "D111_IR_QCL_MOLECULAR_CONFIG",
        "phase_id": "D111",
        "new_spectrograph_added": None,
        "new_spectral_arm_added": "JWST_NIRSPEC_G395M",
        "new_spectrographs_total_post_d111": 67,
        "new_spectral_arms_total_post_d111": 98,
        "instruments": {
            k: {"count": int(v), "wavelength_um": ("2.87-5.27" if "NIRSPEC" in k else ("4.90-18.0" if "MIRI" in k else "1.95-2.49"))}
            for k, v in sorted(by_inst.items())
        },
        "n_mol_ccf_species": len(det.MOL_CCF_V69_TEMPLATES_UM),
        "mol_ccf_species": sorted(det.MOL_CCF_V69_TEMPLATES_UM.keys()),
        "n_mol_confounders": len(det.MOL_CCF_V69_CONFOUNDERS_UM),
        "qcl_canonical_bands": [b[0] for b in det.QCL_IR_CANONICAL_BANDS],
        "brand_new_targets": {st: brand_new_meta[st] for st in new_stars},
    }
    (WS / "IR_QCL_MOLECULAR_CONFIG.json").write_text(json.dumps(ir_cfg, indent=2) + "\n", encoding="utf-8")

    assert not RAW_DIR.exists(), f"{RAW_DIR} appeared before Stage-1 seal!"
    now_epoch = time.time()
    now_utc = datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat()
    stage1_names = [
        "v6_9_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D111.csv",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "IR_QCL_MOLECULAR_CONFIG.json",
        "PRIOR_V6_8_PHASES_SNAPSHOT.json",
    ]
    stage1_hashes = {fn: _sha256_file(WS / fn) for fn in stage1_names}

    ml = {
        "schema": "D111_METHOD_LOCK",
        "phase_id": "D111",
        "detector": "TECHNOSIGNATURE_V6_9_LM_MIDIR_QCL_LASER_AND_MOLECULAR_CCF",
        "locked_utc": now_utc,
        "locked_unix_epoch": round(now_epoch, 4),
        "d111_total_stars": len(unique_stars),
        "d111_brand_new_stars": len(new_stars),
        "d111_prior_bridges": len(bridge_stars),
        "d111_total_observations": len(cohort_rows),
        "d111_total_physical_files": len(cohort_rows),
        "d111_instruments_counts": dict(sorted(by_inst.items())),
        "d111_projected_download_mib": round(proj_bytes / (1024.0 * 1024.0), 3),
        "calibration_suites_new": {
            "V69_QCL_LM_240": 240,
            "V69_MOL_CCF_240": 240,
            "V69_CRIRES_K_COMB_120": 120,
        },
        "stage_1_files": stage1_hashes,
    }
    (WS / "METHOD_LOCK.json").write_text(json.dumps(ml, indent=2) + "\n", encoding="utf-8")
    ml_sha = _sha256_file(WS / "METHOD_LOCK.json")

    lr = {
        "schema": "D111_LOCK_RECEIPT",
        "phase_id": "D111",
        "status": "STAGE-1 SEALED",
        "locked_utc": now_utc,
        "locked_unix_epoch": round(now_epoch, 4),
        "inputs_dir_exists_at_seal": RAW_DIR.exists(),
        "method_lock_sha256": ml_sha,
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lr, indent=2) + "\n", encoding="utf-8")
    print(
        f"STAGE-1 SEALED: stars={len(unique_stars)} (bridges={len(bridge_stars)}, new={len(new_stars)}), "
        f"obs={len(cohort_rows)}, by_inst={dict(by_inst)}, proj={ml['d111_projected_download_mib']:.2f} MiB, "
        f"overlap=0, inputs_at_seal={RAW_DIR.exists()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
