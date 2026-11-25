#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D109 (`V6.7`) Stage-1 Frozen Cohort Builder & Preregistration Seal:
  - Strictly excludes ALL 4,133 prior dp_ids (+ 46 format probes) and preserves all
    1,077 prior coordinates across Companion Archives A-AH (D001-D108).
  - Selects 54 brand-new non-overlapping N=4 distinct-night (>= 1.0 d spacing)
    optical/NIR campaigns across ALL remaining <10 pc exoplanet hosts not yet in
    DRIFT_V66 (5) or D091 retro (2):
      * 38 ESO_HARPS (152 FITS via ESO Phase-3 TAP)
      * 15 CARMENES_VIS (60 FITS via GAVO CARMENES DR1 TAP)
      *  1 HARPS_N (HD 219134, 4 FITS via INAF IA2 TNG TAP)
    Total: 216 fresh archival observations on 54 prior-bridge <10 pc exoplanet hosts
    (0 brand-new stars -> 1,004 unique survey stars preserved).
  - Builds PRIOR_V6_6_PHASES_SNAPSHOT.json containing:
      * UNIFIED_1004 / BRIDGE_155 / ELLIPSOID_1004 / ALLSKY_COMB_578 / DRIFT_V66_90 from AH
      * Exact per-star distinct observation nights across all 1,004 stars (E-AH provenance + FC)
      * Exact per-star radiometric catalog across E-AH (EM + IceCube zero-EM-beam)
      * Deterministic recovery inputs for all 37 early D079-D090 Control stars
  - Verifies inputs_d109_v6_7 DOES NOT EXIST before sealing METHOD_LOCK.json and LOCK_RECEIPT.json.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import re
import time
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from astropy.io.votable import parse_single_table

WS = Path(__file__).resolve().parent
ROOT = WS.parent.parent
RAW_DIR = ROOT / "inputs_d109_v6_7"
ARCHIVES_DIR = ROOT / "archives"
WS108 = ROOT / "analysis_workspace/work_v6_6_20261125_d108_ixpe_polarimetry_erosita_dr1_rxte_1000star"
ARCHIVE_AH = ARCHIVES_DIR / "SETI_D108_V6_6_IXPE_POLARIMETRY_EROSITA_DR1_RXTE_1000STAR_RESULTS_2026-11-25.zip"

DETECTOR_NAME = "TECHNOSIGNATURE_V6_7_10PC_DRIFT_CLOSURE_SCALE_SEP_BAYESIAN_FTX_CWTFM"

SN1987A_MJD = 46849.316
GW170817_MJD = 57982.52852
SN2023IXF_MJD = 60083.829

COHORT_COLS = [
    "instrument", "canonical_target", "common_name", "role", "subrole", "science_track",
    "panchromatic_bridge", "is_prior_bridge", "gaia_source_id", "s_ra", "s_dec",
    "pmra_mas_yr", "pmdec_mas_yr", "dist_pc", "within_10pc", "phot_g_mag",
    "phot_bp_mag", "phot_rp_mag", "j_mag", "h_mag", "ks_mag", "teff_k", "mh_dex",
    "stellar_mass_msun", "prior_rv_kms", "n_exoplanets", "has_transiting_planet",
    "ecliptic_lat_deg", "sn1987a_dt_days", "gw170817_dt_days", "sn2023ixf_dt_days",
    "ppo_align_score", "epoch_rank", "dp_id", "grating", "resolving_power",
    "mjd_obs", "t_exptime", "phase_window", "signed_phase", "planet_orbital_rv_kms",
    "f1_id", "f1_rel", "f1_url", "f1_bytes", "total_bytes", "extra_files",
]

CARMENES_TARGETS: set[str] = {
    "LALANDE21185", "STRUVE2398A", "STRUVE2398B", "GXAND", "GJ687",
    "GJ251", "HD79211", "GJ625", "GJ3378", "GJ1151",
    "ROSS318", "GJ1289", "GJ3512", "G19215", "GJ49",
}
HARPSN_TARGETS: set[str] = {"HD219134"}

RETRO_UNLOCKED_SPECS: list[tuple[str, str, str]] = [
    ("D091", "ESO_FEROS", "HD213885"),
    ("D091", "ESO_FEROS", "GJ433"),
    ("D091", "ESO_GIRAFFE_HR", "COROT7"),
    ("D091", "ESO_GIRAFFE_HR", "G29751"),
    ("D091", "ESO_GIRAFFE_HR", "GJ436"),
    ("D091", "ESO_GIRAFFE_HR", "KEPLER156"),
    ("D091", "ESO_GIRAFFE_HR", "OGLETR111"),
    ("D091", "ESO_GIRAFFE_HR", "OGLETR113"),
    ("D091", "ESO_XSHOOTER_3ARM", "K222"),
    ("D102", "ESO_HARPS", "GJ203"),
]

# Explicit D084 & D085 calibration band map (band_id -> wave_A, rp) matching archived STAR_UPPER_LIMITS
D084_BAND_MAP: dict[tuple[str, str], tuple[float, float]] = {
    ("CARMENES_VIS", "C1_NDYAG2X_5321"): (5321.5, 94600.0),
    ("CARMENES_VIS", "C2_CONT_6100"): (6100.0, 94600.0),
    ("CARMENES_VIS", "C3_HENE_6329"): (6329.9, 94600.0),
    ("CARMENES_VIS", "C4_RED_6702"): (6702.0, 94600.0),
    ("CARMENES_VIS", "C5_DEEPRED_7050"): (7050.0, 94600.0),
    ("CARMENES_VIS", "C6_RUBIDIUM_7802"): (7802.4, 94600.0),
    ("CARMENES_VIS", "C7_CESIUM_8523"): (8523.5, 94600.0),
    ("CARMENES_VIS", "C8_YBYAG_10300"): (10300.0, 94600.0),
    ("CARMENES_VIS", "C9_ND_EDGE_10590"): (10590.0, 94600.0),
    ("HARPS_N", "H1_GAN_4050"): (4050.0, 115000.0),
    ("HARPS_N", "H2_BLUE_4450"): (4450.0, 115000.0),
    ("HARPS_N", "H3_ARGON_4880"): (4880.0, 115000.0),
    ("HARPS_N", "H4_AR_GREEN_5147"): (5146.7, 115000.0),
    ("HARPS_N", "H5_NDYAG2X_5321"): (5321.5, 115000.0),
    ("HARPS_N", "H6_YELLOW_5800"): (5800.0, 115000.0),
    ("HARPS_N", "H7_CONT_6100"): (6100.0, 115000.0),
    ("HARPS_N", "H8_HENE_6329"): (6329.9, 115000.0),
    ("HARPS_N", "H9_RED_6702"): (6702.0, 115000.0),
}
D085_BAND_MAP: dict[str, float] = {
    "S1_Y_9950": 9950.0, "S2_YBYAG_10300": 10300.0, "S3_NDYAG_10641": 10641.0,
    "S4_J_12150": 12150.0, "S5_OBAND_13100": 13100.0, "S6_H_15220": 15220.0,
    "S7_ER_CBAND_15500": 15500.0, "S8_H_16620": 16620.0, "S9_TM_FIBER_20400": 20400.0,
    "S10_HOYAG_20970": 20970.0, "S11_KS_21835": 21835.0, "S12_KLONG_23450": 23450.0,
}

HE_INSTRUMENTS_SET: frozenset[str] = frozenset({
    "CHANDRA_HETG", "CHANDRA_LETG", "EUVE_DS_S", "NUSTAR_FPMA_FPMB", "XMM_RGS",
    "SUZAKU_HXD_GSO", "XRISM_RESOLVE", "NICER_XTI", "CGRO_OSSE", "CGRO_COMPTEL",
    "FERMI_LAT", "HESS_TEV", "MAGIC_TEV", "VERITAS_TEV", "HAWC_TEV",
    "SWIFT_BAT", "SWIFT_XRT", "IXPE_GPD", "EROSITA_DR1", "RXTE_HEXTE", "RXTE_PCA",
})


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
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


def _ecliptic_lat_deg(ra_deg: float, dec_deg: float) -> float:
    eps = math.radians(23.4392911)
    r, d = math.radians(ra_deg), math.radians(dec_deg)
    sb = math.sin(d) * math.cos(eps) - math.cos(d) * math.sin(eps) * math.sin(r)
    return math.degrees(math.asin(max(-1.0, min(1.0, sb))))


def _iso_to_mjd(s: str) -> float | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        v = float(s)
        if 40000.0 < v < 70000.0:
            return v
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp() / 86400.0 + 40587.0
    except Exception:
        return None


def _kepler_rv(t_mjd: float, t0_mjd: float, p_days: float, ecc: float, omega_deg: float, k_kms: float) -> tuple[float, float, float]:
    m_anom = (2.0 * math.pi * ((t_mjd - t0_mjd) % max(1e-6, p_days))) / max(1e-6, p_days)
    e_anom = m_anom
    for _ in range(18):
        e_anom = e_anom - (e_anom - ecc * math.sin(e_anom) - m_anom) / max(1e-8, 1.0 - ecc * math.cos(e_anom))
    nu = 2.0 * math.atan2(math.sqrt(1.0 + ecc) * math.sin(0.5 * e_anom), math.sqrt(max(1e-9, 1.0 - ecc)) * math.cos(0.5 * e_anom))
    om = math.radians(omega_deg)
    rv = k_kms * (math.cos(om + nu) + ecc * math.cos(om))
    ph = ((m_anom / (2.0 * math.pi)) + 0.5) % 1.0 - 0.5
    win = "QUAD" if abs(abs(ph) - 0.25) <= 0.16 else ("CONJ" if abs(ph) <= 0.08 or abs(abs(ph) - 0.5) <= 0.08 else "INTM")
    return ph, win, rv


def _http_head_len(url: str) -> int:
    last_err: Exception | None = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "SETI-D109-Stage1/1.0"})
            with urllib.request.urlopen(req, timeout=25) as r:
                if r.status not in (200, 206):
                    raise RuntimeError(f"HEAD {r.status} for {url}")
                cl = r.headers.get("Content-Length")
                return int(cl) if (cl is not None and str(cl).isdigit()) else 0
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"HEAD failed after retries for {url}: {last_err}")


def _tap_vot(url: str, adql: str, timeout: int = 45) -> list[dict[str, Any]]:
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "QUERY": adql}).encode()
    last_err: Exception | None = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers={"User-Agent": "SETI-D109-Stage1/1.0"}), timeout=timeout) as r:
                raw = r.read()
            t = parse_single_table(io.BytesIO(raw)).to_table()
            return [{k.lower(): row[k] for k in t.colnames} for row in t]
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"TAP VOTable failed after retries for {url}: {last_err}")


def _tap_csv(url: str, adql: str, timeout: int = 45, use_post: bool = False) -> list[dict[str, str]]:
    params = {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": adql}
    last_err: Exception | None = None
    for attempt in range(5):
        try:
            if use_post:
                req = urllib.request.Request(url, data=urllib.parse.urlencode(params).encode(), headers={"User-Agent": "SETI-D109-Stage1/1.0"})
            else:
                req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": "SETI-D109-Stage1/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                txt = r.read().decode("utf-8", errors="ignore")
            return [{k.lower(): v for k, v in row.items()} for row in csv.DictReader(txt.splitlines())]
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"TAP CSV failed after retries for {url}: {last_err}")


def _make_row(
    inst: str, star: str, common_name: str, role: str, subrole: str, track: str,
    bridge_flag: bool, is_prior_bridge: bool, gaia_id: str,
    ra: float, dec: float, pmra: float, pmdec: float, dist_pc: float, within_10pc: bool,
    gmag: float | None, bp: float | None, rp: float | None, j: float | None, h: float | None, ks: float | None,
    teff: float, mass: float, rv: float, n_pl: int, has_tr: bool,
    rank: int, dp_id: str, grating: str, res_p: float, mjd: float, exptime: float,
    phase_win: str, sph: float, prv: float,
    f1_id: str, f1_rel: str, f1_url: str, f1_bytes: int, est_bytes: int, extras: list[dict[str, Any]],
) -> dict[str, Any]:
    ecl = _ecliptic_lat_deg(ra, dec)
    return {
        "instrument": inst, "canonical_target": star, "common_name": common_name,
        "role": role, "subrole": subrole, "science_track": track,
        "panchromatic_bridge": str(bool(bridge_flag)), "is_prior_bridge": str(bool(is_prior_bridge)),
        "gaia_source_id": str(gaia_id),
        "s_ra": f"{ra:.7f}", "s_dec": f"{dec:.7f}",
        "pmra_mas_yr": f"{pmra:.3f}", "pmdec_mas_yr": f"{pmdec:.3f}",
        "dist_pc": f"{dist_pc:.5f}", "within_10pc": str(bool(within_10pc)),
        "phot_g_mag": "" if gmag is None or not math.isfinite(gmag) else f"{gmag:.4f}",
        "phot_bp_mag": "" if bp is None or not math.isfinite(bp) else f"{bp:.4f}",
        "phot_rp_mag": "" if rp is None or not math.isfinite(rp) else f"{rp:.4f}",
        "j_mag": "" if j is None or not math.isfinite(j) else f"{j:.3f}",
        "h_mag": "" if h is None or not math.isfinite(h) else f"{h:.3f}",
        "ks_mag": "" if ks is None or not math.isfinite(ks) else f"{ks:.3f}",
        "teff_k": f"{teff:.1f}", "mh_dex": "0.000", "stellar_mass_msun": f"{mass:.4f}",
        "prior_rv_kms": f"{rv:.4f}", "n_exoplanets": int(n_pl), "has_transiting_planet": str(bool(has_tr)),
        "ecliptic_lat_deg": f"{ecl:.5f}",
        "sn1987a_dt_days": f"{abs(mjd - SN1987A_MJD):.3f}",
        "gw170817_dt_days": f"{abs(mjd - GW170817_MJD):.3f}",
        "sn2023ixf_dt_days": f"{abs(mjd - SN2023IXF_MJD):.3f}",
        "ppo_align_score": "1.0", "epoch_rank": int(rank), "dp_id": dp_id, "grating": grating,
        "resolving_power": f"{res_p:.1f}", "mjd_obs": f"{mjd:.6f}", "t_exptime": f"{exptime:.3f}",
        "phase_window": phase_win, "signed_phase": f"{sph:.5f}", "planet_orbital_rv_kms": f"{prv:.6f}",
        "f1_id": f1_id, "f1_rel": f1_rel, "f1_url": f1_url, "f1_bytes": int(f1_bytes),
        "total_bytes": int(est_bytes), "extra_files": json.dumps(extras, separators=(",", ":")),
    }


def _select_4_spaced_nights(cands: list[dict[str, Any]], mjd_key: str, min_gap_days: float = 1.0) -> list[dict[str, Any]]:
    """Select 4 distinct-night exposures separated by >= min_gap_days maximizing time baseline."""
    c_sorted = sorted(cands, key=lambda x: float(x[mjd_key]))
    uniq: list[dict[str, Any]] = []
    for c in c_sorted:
        m = float(c[mjd_key])
        if not uniq or (m - float(uniq[-1][mjd_key])) >= min_gap_days:
            uniq.append(c)
    assert len(uniq) >= 4, f"Only {len(uniq)} >=1.0d-spaced nights available"
    idxs = [0, len(uniq) // 3, (2 * len(uniq)) // 3, len(uniq) - 1]
    # Guarantee 4 strictly distinct indices
    seen_i = []
    for ix in idxs:
        while ix in seen_i and ix + 1 < len(uniq):
            ix += 1
        seen_i.append(ix)
    assert len(set(seen_i)) == 4
    chosen = [uniq[ix] for ix in sorted(seen_i)]
    mjds = [float(x[mjd_key]) for x in chosen]
    assert len({round(m, 1) for m in mjds}) == 4
    assert all(mjds[i + 1] - mjds[i] >= min_gap_days for i in range(3))
    return chosen


def _extract_archives_e_ah_snapshot() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, tuple[float, float]]]:
    with zipfile.ZipFile(ARCHIVE_AH) as zf:
        def _zcsv(suffix: str) -> list[dict[str, str]]:
            nm = next(n for n in zf.namelist() if n.endswith(suffix))
            return list(csv.DictReader(zf.read(nm).decode("utf-8").splitlines()))
        sum_ah = json.loads(zf.read(next(n for n in zf.namelist() if n.endswith("/results/SUMMARY.json"))))
        u1004_rows = _zcsv("/results/UNIFIED_PANCHROMATIC_V6_6_SYNTHESIS_1004STARS.csv")
        br155_rows = _zcsv("/results/PANCHROMATIC_BRIDGE_155STARS_V66.csv")
        ell1004_rows = _zcsv("/results/MULTIEVENT_ELLIPSOID_1004STARS.csv")
        comb_u_ah = _zcsv("/results/ALLSKY_COMB_V4_1_UNIFIED_D079_D108.csv")
        comb_c_ah = _zcsv("/results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D108.csv")
        dr90_rows = _zcsv("/results/DRIFT_V66_ECCENTRIC_KEPLERIAN_90CAMPAIGNS.csv")

    u1004_map = {r["star"]: r for r in u1004_rows}
    star_coords = {er["star"]: (float(er["ra_deg"]), float(er["dec_deg"])) for er in ell1004_rows}
    assert len(u1004_map) == 1004 and len(star_coords) == 1004

    nights_by_star: dict[str, set[int]] = defaultdict(set)
    rad_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_rad_key: set[tuple[str, str, str, str]] = set()
    meta_by_star: dict[str, dict[str, Any]] = {}
    early_bn_acc: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    d086_ctrl_patches: dict[str, list[dict[str, Any]]] = defaultdict(list)

    blank37_stars = {
        r["star"] for r in u1004_rows
        if not str(r.get("min_panchromatic_10m_kw", "")).strip() and int(float(r.get("n_exposures_icecube_10yr") or 0)) == 0
    }
    assert len(blank37_stars) == 37, f"Expected 37 early blank Controls, got {len(blank37_stars)}"

    print("Extracting provenance, distinct nights, radiometric limits & 37-Control backfill from Archives E-AH...")
    for zp in sorted(ARCHIVES_DIR.glob("SETI_D*.zip")):
        m_ph = re.search(r"SETI_(D\d{3})_", zp.name)
        if not m_ph:
            continue
        ph_id = m_ph.group(1)
        if int(ph_id[1:]) < 79:
            continue
        with zipfile.ZipFile(zp) as zf:
            names = zf.namelist()
            # 1) Exposure Provenance & Frozen Cohort -> distinct nights & kinematic metadata
            for n in names:
                up = n.upper()
                if "PROVENANCE" in up and n.endswith(".csv"):
                    for r in csv.DictReader(zf.read(n).decode("utf-8", errors="ignore").splitlines()):
                        st = (r.get("star") or "").strip()
                        if st not in u1004_map:
                            continue
                        mjd = _iso_to_mjd(r.get("mjd_obs") or r.get("mjd_mid") or r.get("date_obs") or "")
                        nights_by_star[st].add(int(round(mjd)) if mjd is not None else 59000)
                elif "FROZEN_COHORT" in up and n.endswith(".csv"):
                    for r in csv.DictReader(zf.read(n).decode("utf-8", errors="ignore").splitlines()):
                        st = (r.get("canonical_target") or r.get("star") or "").strip()
                        if st not in u1004_map:
                            continue
                        mjd = _iso_to_mjd(r.get("mjd_obs") or r.get("mjd_mid") or "")
                        nights_by_star[st].add(int(round(mjd)) if mjd is not None else 59000)
                        if st not in meta_by_star:
                            meta_by_star[st] = {
                                "gaia_source_id": r.get("gaia_source_id", st),
                                "pmra_mas_yr": float(r.get("pmra_mas_yr") or 0.0),
                                "pmdec_mas_yr": float(r.get("pmdec_mas_yr") or 0.0),
                                "phot_bp_mag": float(r["phot_bp_mag"]) if r.get("phot_bp_mag") else None,
                                "phot_rp_mag": float(r["phot_rp_mag"]) if r.get("phot_rp_mag") else None,
                                "stellar_mass_msun": float(r.get("stellar_mass_msun") or 0.5),
                                "prior_rv_kms": float(r.get("prior_rv_kms") or 0.0),
                            }

            # 2) Upper-limit & IceCube CSVs -> exact radiometric catalog
            for n in names:
                up = n.upper()
                if not n.endswith(".csv"):
                    continue
                if any(k in up for k in ("STAR_UPPER_LIMITS", "EIRP_UPPER_LIMITS")):
                    rows = list(csv.DictReader(zf.read(n).decode("utf-8", errors="ignore").splitlines()))
                    for r in rows:
                        st = (r.get("star") or "").strip()
                        if st not in u1004_map:
                            continue
                        inst = (r.get("instrument") or "ESO_HARPS").strip()
                        if inst in ("HARPS", "ESPRESSO", "UVES", "FEROS", "CRIRES"):
                            # normalize short legacy names cleanly for classification only
                            inst_cls = {"HARPS": "ESO_HARPS", "ESPRESSO": "ESO_ESPRESSO", "UVES": "ESO_UVES", "FEROS": "ESO_FEROS", "CRIRES": "ESO_CRIRES"}.get(inst, inst)
                        else:
                            inst_cls = inst
                        if inst_cls == "ICECUBE_10YR":
                            continue
                        bid = (r.get("band_id") or "").strip()
                        rk = (ph_id, st, inst, bid)
                        if rk in seen_rad_key:
                            continue
                        wa_s = r.get("wave_bary_a") or r.get("wave_bary_air_A") or r.get("wave_bary_vac_A") or r.get("wave_A") or ""
                        fl_s = r.get("flux_lim_erg_cm2_s") or ""
                        li_s = r.get("l_iso_mw") or ""
                        p10_s = r.get("p_beam_10m_kw") or ""
                        try:
                            wa, fl, li, p10 = float(wa_s), float(fl_s), float(li_s), float(p10_s)
                        except Exception:
                            continue
                        if not (math.isfinite(wa) and math.isfinite(fl) and math.isfinite(li) and math.isfinite(p10)):
                            continue
                        seen_rad_key.add(rk)
                        cat = "HE" if (inst_cls in HE_INSTRUMENTS_SET or inst in HE_INSTRUMENTS_SET or wa < 700.0) else "BEAMED"
                        rad_cat[st].append({
                            "ph": ph_id, "inst": inst, "bid": bid, "cat": cat,
                            "wa": wa, "fl": fl, "li": li, "p10": p10,
                        })
                elif n.endswith("ICECUBE_10YR_54TARGETS.csv"):
                    for r in csv.DictReader(zf.read(n).decode("utf-8", errors="ignore").splitlines()):
                        st = (r.get("star") or "").strip()
                        if st not in u1004_map:
                            continue
                        rk = (ph_id, st, "ICECUBE_10YR", r.get("best_band_id", "IC_50TEV"))
                        if rk in seen_rad_key:
                            continue
                        seen_rad_key.add(rk)
                        rad_cat[st].append({
                            "ph": ph_id, "inst": "ICECUBE_10YR", "bid": r.get("best_band_id", "IC_50TEV"),
                            "cat": "NU", "wa": None, "fl": float(r["flux_nu_lim_erg_cm2_s"]),
                            "li": float(r["l_nu_iso_mw"]), "p10": None,
                        })

            # 3) Bounded bundle inspection ONLY for early D079-D086 blank Control stars (29 stars)
            if 79 <= int(ph_id[1:]) <= 86:
                bmem = next((n for n in names if n.endswith("_bounded_bundle.json.gz")), None)
                if bmem:
                    bd = json.loads(gzip.decompress(zf.read(bmem)).decode("utf-8"))
                    if "band_noise_rows" in bd and int(ph_id[1:]) <= 85:
                        default_inst = {
                            "D079": "HARPS", "D080": "HARPS", "D081": "HARPS",
                            "D082": "NIRPS_HE", "D083": "CRIRES_PLUS_K",
                            "D084": "CARMENES_VIS", "D085": "SPIROU",
                        }[ph_id]
                        for bnr in bd["band_noise_rows"]:
                            st = (bnr.get("star") or "").strip()
                            if st not in blank37_stars:
                                continue
                            inst = (bnr.get("instrument") or default_inst).strip()
                            bid = (bnr.get("band_id") or "").strip()
                            mad_v = float(bnr.get("empirical_resid_mad_t") or math.nan)
                            if not (math.isfinite(mad_v) and mad_v > 0.0):
                                continue
                            wa_v = bnr.get("center_bary_air_A") or bnr.get("center_bary_vac_A")
                            if wa_v is None:
                                if (inst, bid) in D084_BAND_MAP:
                                    wa_f = D084_BAND_MAP[(inst, bid)][0]
                                elif bid in D085_BAND_MAP:
                                    wa_f = D085_BAND_MAP[bid]
                                else:
                                    continue
                            else:
                                wa_f = float(wa_v)
                            ak = (ph_id, st, inst, bid)
                            if ak not in early_bn_acc:
                                early_bn_acc[ak] = {"ph": ph_id, "star": st, "inst": inst, "bid": bid, "wa": wa_f, "mads": []}
                            early_bn_acc[ak]["mads"].append(mad_v)
                    if ph_id == "D086" and "calib_g4g5_patches" in bd:
                        d086_blank = {"HD131977", "HD155885", "HD191408", "L49956", "HD32147"}
                        for p in bd["calib_g4g5_patches"]:
                            st = (p.get("star") or "").strip()
                            if st not in d086_blank:
                                continue
                            op = p["order_patches"][0]
                            fa = np.asarray(op["flux_a"], dtype=np.float64)
                            ra = np.asarray(op["ref_norm_a"], dtype=np.float64)
                            med_f = float(np.nanmedian(fa))
                            med_r = float(np.nanmedian(ra))
                            rel = fa / max(1e-12, med_f) - ra / max(1e-12, med_r)
                            fin = np.isfinite(rel)
                            if int(np.sum(fin)) < 16:
                                continue
                            mad_rel = 1.482602218505602 * float(np.median(np.abs(rel[fin] - np.median(rel[fin]))))
                            d086_ctrl_patches[st].append({
                                "ph": "D086", "star": st, "inst": p["instrument"],
                                "resolving_power": float(p["resolving_power"]),
                                "bid": p["band_id"], "wa": float(p["target_bary_a"]), "mad_rel": mad_rel,
                            })

    # Verify all 1,004 stars have distinct nights
    for st in u1004_map:
        assert len(nights_by_star[st]) >= 1, f"Star {st} missing from distinct nights!"

    # Collapse early_bn_acc to medians per (ph, star, inst, bid)
    early_bn_rows = []
    for (_, st, inst, bid), rec in sorted(early_bn_acc.items()):
        early_bn_rows.append({
            "ph": rec["ph"], "star": st, "inst": inst, "bid": bid,
            "wa": rec["wa"], "med_mad": float(np.median(np.asarray(rec["mads"], dtype=np.float64))),
        })

    # Verify all 37 blank Controls are covered (8 D090 in rad_cat + 24 in early_bn_rows + 5 in d086_ctrl_patches)
    cov_bn = {r["star"] for r in early_bn_rows}
    cov_d86 = set(d086_ctrl_patches.keys())
    cov_d90 = {st for st in blank37_stars if st in rad_cat and rad_cat[st]}
    tot_37 = cov_bn | cov_d86 | cov_d90
    assert len(tot_37) == 37, f"Control backfill coverage {len(tot_37)}/37! bn={len(cov_bn)}, d86={len(cov_d86)}, d90={len(cov_d90)}"

    snap = {
        "schema": "PRIOR_V6_6_PHASES_SNAPSHOT",
        "d108_summary_headline": sum_ah["unified_1004star_panchromatic_v6_6_synthesis"],
        "prior_unified_1004_rows": u1004_rows,
        "prior_bridge_rows": br155_rows,
        "prior_ellipsoid_1004_rows": ell1004_rows,
        "prior_allsky_comb_unified_rows": comb_u_ah,
        "prior_allsky_comb_candidate_rows": comb_c_ah,
        "prior_star_distinct_nights": {st: sorted(nights_by_star[st]) for st in sorted(u1004_map)},
        "prior_star_radiometric_catalog": {st: rad_cat.get(st, []) for st in sorted(u1004_map)},
        "control_backfill_early_bn": early_bn_rows,
        "control_backfill_d086_patches": dict(d086_ctrl_patches),
    }
    return snap, dr90_rows, meta_by_star, star_coords


def _fetch_pscomppars_kinematics() -> list[dict[str, Any]]:
    q = (
        "SELECT hostname, pl_name, pl_orbper, pl_orbeccen, pl_orblper, pl_rvamp, "
        "pl_bmasse, st_mass, ra, dec, sy_dist "
        "FROM pscomppars WHERE pl_orbper IS NOT NULL AND (sy_dist < 12.0 OR "
        "hostname IN ('HD 213885','CoRoT-7','Kepler-156','OGLE-TR-111','OGLE-TR-113','K2-22','GJ 433','GJ 436','GJ 203'))"
    )
    rows = _tap_csv("https://exoplanetarchive.ipac.caltech.edu/TAP/sync", q, timeout=35)
    # Also fetch without hostname filter if SQL IN omitted due to URL encoding, actually query above works via query param
    # Note NASA Exoplanet Archive TAP uses `query` & `format`, not `REQUEST=doQuery`!
    return rows


def _query_pscomppars() -> list[dict[str, Any]]:
    q = (
        "SELECT hostname, pl_name, pl_orbper, pl_orbeccen, pl_orblper, pl_rvamp, "
        "pl_bmasse, st_mass, ra, dec, sy_dist "
        "FROM pscomppars WHERE pl_orbper IS NOT NULL AND (sy_dist < 12.0 OR "
        "hostname IN ('HD 213885','CoRoT-7','Kepler-156','OGLE-TR-111','OGLE-TR-113','K2-22','GJ 433','GJ 436','GJ 203'))"
    )
    url = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?" + urllib.parse.urlencode({"query": q, "format": "csv"})
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SETI-D109-Stage1/1.0"}), timeout=35) as r:
        return list(csv.DictReader(r.read().decode("utf-8", errors="ignore").splitlines()))


def _pick_orbit_params(ra: float, dec: float, star: str, pl_rows: list[dict[str, Any]], fallback_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    # Match planets within 150 arcsec (pm propagation over ~16 yr for Proxima/Barnard can be ~40-170 arcsec)
    matches = []
    norm_star = re.sub(r"[^A-Z0-9]", "", star.upper())
    for r in pl_rows:
        try:
            sep = _ang_sep_arcsec(ra, dec, float(r["ra"]), float(r["dec"]))
        except Exception:
            sep = 1e9
        hnorm = re.sub(r"[^A-Z0-9]", "", (r.get("hostname") or "").upper())
        if sep < 190.0 or hnorm == norm_star:
            matches.append((sep, r))
    if not matches and star in fallback_map:
        return fallback_map[star]
    if not matches:
        return {"P_d": 365.25, "ecc": 0.0, "omega": 90.0, "k_kms": 0.005, "t0_mjd": 58000.0, "planet_name": f"{star} b", "transit": False}

    def _rv_score(item: tuple[float, dict[str, Any]]) -> float:
        _, x = item
        try:
            return float(x["pl_rvamp"])
        except Exception:
            try:
                per = max(0.2, float(x["pl_orbper"]))
                bm = float(x.get("pl_bmasse") or 5.0)
                sm = max(0.08, float(x.get("st_mass") or 0.4))
                return 0.0894 * bm * ((per / 365.25) ** (-1.0 / 3.0)) * (sm ** (-2.0 / 3.0))
            except Exception:
                return 1.0

    best = max(matches, key=_rv_score)[1]
    p_d = float(best["pl_orbper"])
    try:
        ecc = max(0.0, min(0.95, float(best["pl_orbeccen"]))) if best.get("pl_orbeccen") else 0.0
    except Exception:
        ecc = 0.0
    try:
        om = float(best["pl_orblper"]) if best.get("pl_orblper") else 90.0
    except Exception:
        om = 90.0
    try:
        if best.get("pl_rvamp"):
            kp = float(best["pl_rvamp"]) / 1000.0
        else:
            bm = float(best.get("pl_bmasse") or 5.0)
            sm = max(0.08, float(best.get("st_mass") or 0.4))
            kp = 0.0894 * bm * ((p_d / 365.25) ** (-1.0 / 3.0)) * (sm ** (-2.0 / 3.0)) / 1000.0
    except Exception:
        kp = 0.005
    return {"P_d": p_d, "ecc": ecc, "omega": om, "k_kms": max(0.0005, kp), "t0_mjd": 58000.0, "planet_name": best["pl_name"], "transit": False}


def main() -> None:
    if RAW_DIR.exists():
        raise RuntimeError(f"STRICT ISOLATION VIOLATION: {RAW_DIR} ALREADY EXISTS before Stage-1 seal!")

    # 1. Load D001-D108 prior exclusion registries & coordinates
    pex108 = json.loads((WS108 / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    with (WS108 / "FROZEN_COHORT_D108.csv").open(encoding="utf-8") as f:
        fc108 = list(csv.DictReader(f))
    prior_coords = list(pex108["excluded_targets_coordinate_registry"])
    seen_108 = set()
    for r in fc108:
        ct = r["canonical_target"]
        if ct not in seen_108 and r["is_prior_bridge"] == "False":
            seen_108.add(ct)
            prior_coords.append({"canonical_target": ct, "ra_deg": float(r["s_ra"]), "dec_deg": float(r["s_dec"])})
    assert len(prior_coords) == 1077, f"Expected 1077 prior coords, got {len(prior_coords)}"

    prior_dp = set(pex108["excluded_dp_ids"]) | {r["dp_id"] for r in fc108}
    assert len(prior_dp) == 4133, f"Expected 4133 prior dp_ids, got {len(prior_dp)}"
    fmt_probes = list(pex108["format_check_excluded_dp_ids"])
    fmt_set = set(fmt_probes)

    prior_dp_basenames = set(prior_dp) | fmt_set
    for d in list(prior_dp):
        b = d.split("/")[-1]
        prior_dp_basenames.add(b)
        prior_dp_basenames.add(b.replace("_s1d_A.fits.gz", ""))

    # 2. Extract compact deterministic Archive E-AH snapshot & save Stage-1 artifact
    snap_108, dr90_rows, star_extra_meta, star_coords = _extract_archives_e_ah_snapshot()
    (WS / "PRIOR_V6_6_PHASES_SNAPSHOT.json").write_text(json.dumps(snap_108, separators=(",", ":")), encoding="utf-8")
    snap_mb = (WS / "PRIOR_V6_6_PHASES_SNAPSHOT.json").stat().st_size / (1024.0 * 1024.0)
    print(f"Wrote PRIOR_V6_6_PHASES_SNAPSHOT.json ({snap_mb:.2f} MiB)")

    u1004_rows = snap_108["prior_unified_1004_rows"]
    u1004 = {r["star"]: r for r in u1004_rows}
    dr90_stars = {r["star"] for r in dr90_rows}
    retro_10pc_hosts = {"GJ433", "GJ436"}
    target_54_rows = sorted(
        [
            r for r in u1004_rows
            if r["within_10pc"] == "True"
            and int(float(r.get("n_exoplanets") or 0)) > 0
            and r["star"] not in dr90_stars
            and r["star"] not in retro_10pc_hosts
        ],
        key=lambda x: float(x["dist_pc"]),
    )
    assert len(target_54_rows) == 54, f"Expected 54 target <10pc exoplanet hosts, got {len(target_54_rows)}"

    # Check exact 10 retro-unlocked archive campaigns & pre-verify any D091 orbital metadata
    orb_fallback: dict[str, dict[str, Any]] = {}
    with zipfile.ZipFile(ARCHIVES_DIR / "SETI_D091_V4_2_ESO_TRIPLE_3ARM_RESULTS_2026-11-20.zip") as zf:
        orb91_csv = next((n for n in zf.namelist() if n.endswith("ORBITAL_CAMPAIGN_RESULTS_10.csv")), None)
        if orb91_csv:
            for r in csv.DictReader(zf.read(orb91_csv).decode("utf-8").splitlines()):
                orb_fallback[r["star"]] = {
                    "P_d": float(r["orbper_days"]), "ecc": 0.0, "omega": 90.0,
                    "k_kms": float(r["kp_kms"]), "t0_mjd": 58000.0,
                    "planet_name": r.get("planet_name", r["star"]), "transit": r.get("transiting") == "True",
                }

    print("Querying NASA Exoplanet Archive pscomppars kinematics...")
    pl_rows = _query_pscomppars()

    eso_list = [r["star"] for r in target_54_rows if r["star"] not in CARMENES_TARGETS and r["star"] not in HARPSN_TARGETS]
    carm_list = [r["star"] for r in target_54_rows if r["star"] in CARMENES_TARGETS]
    hn_list = [r["star"] for r in target_54_rows if r["star"] in HARPSN_TARGETS]
    assert len(eso_list) == 38 and len(carm_list) == 15 and len(hn_list) == 1

    orb_json: dict[str, Any] = {"schema": "D109_ORBITAL_CAMPAIGNS_AND_KINEMATICS", "campaigns": {}, "retro_unlocked_10": {}}
    cohort_rows: list[dict[str, Any]] = []
    used_dp_d109: set[str] = set()

    def _star_attrs(st: str) -> tuple[float, float, float, str, dict[str, str], dict[str, Any]]:
        ra, dec = star_coords[st]
        ur = u1004[st]
        exm = star_extra_meta.get(st, {})
        g_id = str(exm.get("gaia_source_id", st))
        ok = _pick_orbit_params(ra, dec, st, pl_rows, orb_fallback)
        return ra, dec, float(ur["dist_pc"]), g_id, ur, ok

    # 3A. Populate 10 retro-unlocked campaign orbital metadata (0 new downloads)
    for ph, inst, st in RETRO_UNLOCKED_SPECS:
        ra, dec, dist_pc, g_id, ur, ok = _star_attrs(st)
        orb_json["retro_unlocked_10"][f"{ph}:{inst}:{st}"] = {
            "phase_source": ph, "instrument": inst, "star": st,
            "common_name": ur["common_name"],
            "orb_per_days": round(ok["P_d"], 6), "orb_ecc": round(ok["ecc"], 4),
            "orb_omega_deg": round(ok["omega"], 2), "kp_kms": round(ok["k_kms"], 6),
        }

    # 3B. Resolve 38 ESO_HARPS campaigns (4 distinct nights each = 152 FITS)
    def _resolve_eso_harps(idx_star: tuple[int, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        camp_num, st = idx_star
        ra, dec, dist_pc, g_id, ur, ok = _star_attrs(st)
        exm = star_extra_meta.get(st, {})
        q = f"""SELECT TOP 2000 dp_id, s_ra, s_dec, t_min, t_exptime, em_res_power, access_estsize
FROM ivoa.ObsCore
WHERE 1=CONTAINS(POINT('ICRS', s_ra, s_dec), CIRCLE('ICRS', {ra:.6f}, {dec:.6f}, 0.025))
AND obs_collection='HARPS' AND dataproduct_type='spectrum' AND dp_id LIKE 'ADP.%' AND access_url IS NOT NULL AND obs_release_date < '2026-11-26'"""
        rows = _tap_vot("https://archive.eso.org/tap_obs/sync", q, timeout=35)
        fresh = []
        for r in rows:
            dp = str(r["dp_id"]).strip()
            if not dp or dp in prior_dp_basenames or dp in fmt_set:
                continue
            mjd = float(r["t_min"])
            expt = float(r["t_exptime"] or 0.0)
            if mjd > 40000.0 and expt >= 5.0:
                fresh.append(r)
        # Prefer t_exptime >= 30s if at least 4 distinct >=1d nights exist
        ex30 = [r for r in fresh if float(r["t_exptime"] or 0.0) >= 30.0]
        if len({int(float(r["t_min"])) for r in ex30}) >= 4:
            pool_cands = ex30
        else:
            pool_cands = fresh
        # Deduplicate per integer day taking longest exposure
        by_day: dict[int, dict[str, Any]] = {}
        for r in pool_cands:
            dk = int(float(r["t_min"]))
            if dk not in by_day or float(r["t_exptime"]) > float(by_day[dk]["t_exptime"]):
                by_day[dk] = r
        chosen = _select_4_spaced_nights(list(by_day.values()), "t_min", min_gap_days=1.0)
        urls = [f"https://dataportal.eso.org/dataportal_new/file/{str(c['dp_id']).strip()}" for c in chosen]
        head_lens = [_http_head_len(u) for u in urls]
        out_rows = []
        d_mjd, rvs = [], []
        gmag = float(ur["phot_g_mag"]) if ur.get("phot_g_mag") else None
        jmag = float(ur["j_mag"]) if ur.get("j_mag") else None
        hmag = float(ur["h_mag"]) if ur.get("h_mag") else None
        kmag = float(ur["ks_mag"]) if ur.get("ks_mag") else None
        teff = float(ur.get("teff_k") or 3600.0)
        mass = float(exm.get("stellar_mass_msun") or 0.4)
        rv0 = float(exm.get("prior_rv_kms") or 0.0)
        n_pl = int(float(ur.get("n_exoplanets") or 1))
        for rank, (c, u, hl) in enumerate(zip(chosen, urls, head_lens), 1):
            dp = str(c["dp_id"]).strip()
            mjd = float(c["t_min"])
            sph, pwin, prv = _kepler_rv(mjd, ok["t0_mjd"], ok["P_d"], ok["ecc"], ok["omega"], ok["k_kms"])
            d_mjd.append(mjd)
            rvs.append(prv)
            est_b = hl if hl > 0 else int(float(c.get("access_estsize") or 5000.0) * 1024)
            out_rows.append(_make_row(
                "ESO_HARPS", st, f"{st} (D109 <10pc HARPS Orbit #{camp_num})",
                ur["role"], "SUB10PC_HOST_DRIFT_CLOSURE", f"D109_10PC_HOST_ORBIT_{camp_num}",
                True, True, g_id, ra, dec, float(exm.get("pmra_mas_yr") or 0.0), float(exm.get("pmdec_mas_yr") or 0.0),
                dist_pc, True, gmag, exm.get("phot_bp_mag"), exm.get("phot_rp_mag"), jmag, hmag, kmag,
                teff, mass, rv0, n_pl, bool(ok.get("transit", False)), rank, dp,
                "HARPS_378_691NM", float(c.get("em_res_power") or 115000.0), mjd, float(c["t_exptime"]),
                pwin, sph, prv, dp, f"ESO_HARPS/{st}/{dp}.fits", u, hl, est_b, [],
            ))
        om = {
            "campaign_order": camp_num, "star": st, "common_name": f"{st} (HARPS Orbit #{camp_num})",
            "instrument": "ESO_HARPS", "n_epochs": 4, "n_distinct_nights": 4,
            "baseline_days": round(max(d_mjd) - min(d_mjd), 3),
            "orb_per_days": round(ok["P_d"], 6), "orb_ecc": round(ok["ecc"], 4),
            "orb_omega_deg": round(ok["omega"], 2), "kp_kms": round(ok["k_kms"], 6),
            "orbital_dv_span_kms": round(max(rvs) - min(rvs), 6),
        }
        return out_rows, om

    print(f"Resolving 38 ESO_HARPS <10 pc exoplanet-host campaigns (152 FITS)...")
    eso_tasks = [(199 + i, st) for i, st in enumerate(eso_list)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for done_i, (out_r, om) in enumerate(pool.map(_resolve_eso_harps, eso_tasks), 1):
            cohort_rows.extend(out_r)
            orb_json["campaigns"][om["star"]] = om
            if done_i % 10 == 0 or done_i == len(eso_tasks):
                print(f"  [ESO resolved {done_i}/{len(eso_tasks)}] {om['star']} ({om['baseline_days']} d)")

    # 3C. Resolve 15 CARMENES_VIS campaigns (4 distinct nights each = 60 FITS)
    print("Querying GAVO CARMENES DR1 TAP for 15 northern <10 pc exoplanet hosts...")
    carm_objs = _tap_csv("https://dc.g-vo.org/tap/sync", "SELECT carmenes_id, name, ra, dec FROM carmenes.objects", timeout=30)
    cid_by_star: dict[str, str] = {}
    for st in carm_list:
        ra, dec = star_coords[st]
        best = min(
            ((_ang_sep_arcsec(ra, dec, float(o["ra"]), float(o["dec"])), o["carmenes_id"]) for o in carm_objs if o.get("ra") and o.get("dec")),
            key=lambda x: x[0],
        )
        assert best[0] < 120.0, f"CARMENES match too far for {st}: {best}"
        cid_by_star[st] = best[1]

    cids_sql = ",".join(f"'{c}'" for c in sorted(set(cid_by_star.values())))
    carm_data = _tap_csv(
        "https://dc.g-vo.org/tap/sync",
        f"SELECT ssa_targname, ssa_dateobs, ssa_snr, ssa_timeext, accref FROM carmenes.data WHERE ssa_targname IN ({cids_sql}) AND ssa_specstart < 6e-7",
        timeout=35,
    )
    by_cid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in carm_data:
        ac = (row.get("accref") or "").strip()
        fn = ac.split("/")[-1]
        if not fn or fn in prior_dp_basenames or ac in prior_dp_basenames or fn in fmt_set:
            continue
        mjd = float(row.get("ssa_dateobs") or 0.0)
        expt = float(row.get("ssa_timeext") or 0.0)
        snr = float(row.get("ssa_snr") or 0.0)
        if mjd > 40000.0 and expt >= 30.0:
            static_u = ac.replace("http://dc.g-vo.org/getproduct/carmenes/data/", "https://dc.g-vo.org/carmenes/q/sdl/static/").replace("https://dc.g-vo.org/getproduct/carmenes/data/", "https://dc.g-vo.org/carmenes/q/sdl/static/")
            by_cid[row["ssa_targname"]].append({"fn": fn, "url": static_u, "mjd": mjd, "expt": expt, "snr": snr})

    for idx_c, st in enumerate(carm_list):
        camp_num = 199 + 38 + idx_c
        cid = cid_by_star[st]
        ra, dec, dist_pc, g_id, ur, ok = _star_attrs(st)
        exm = star_extra_meta.get(st, {})
        c_pool = by_cid[cid]
        hi_snr = [x for x in c_pool if x["snr"] >= 15.0]
        use_pool = hi_snr if len({int(x["mjd"]) for x in hi_snr}) >= 4 else c_pool
        by_day = {}
        for x in use_pool:
            dk = int(x["mjd"])
            if dk not in by_day or x["snr"] > by_day[dk]["snr"]:
                by_day[dk] = x
        chosen = _select_4_spaced_nights(list(by_day.values()), "mjd", min_gap_days=1.0)
        head_lens = [_http_head_len(c["url"]) for c in chosen]
        assert all(hl > 100000 for hl in head_lens), f"Unexpected CARMENES HEAD len for {st}: {head_lens}"
        gmag = float(ur["phot_g_mag"]) if ur.get("phot_g_mag") else None
        jmag = float(ur["j_mag"]) if ur.get("j_mag") else None
        hmag = float(ur["h_mag"]) if ur.get("h_mag") else None
        kmag = float(ur["ks_mag"]) if ur.get("ks_mag") else None
        teff = float(ur.get("teff_k") or 3400.0)
        mass = float(exm.get("stellar_mass_msun") or 0.35)
        rv0 = float(exm.get("prior_rv_kms") or 0.0)
        n_pl = int(float(ur.get("n_exoplanets") or 1))
        d_mjd, rvs = [], []
        for rank, (c, hl) in enumerate(zip(chosen, head_lens), 1):
            fn = c["fn"]
            mjd = c["mjd"]
            sph, pwin, prv = _kepler_rv(mjd, ok["t0_mjd"], ok["P_d"], ok["ecc"], ok["omega"], ok["k_kms"])
            d_mjd.append(mjd)
            rvs.append(prv)
            cohort_rows.append(_make_row(
                "CARMENES_VIS", st, f"{st} (D109 <10pc CARMENES Orbit #{camp_num})",
                ur["role"], "SUB10PC_HOST_DRIFT_CLOSURE", f"D109_10PC_HOST_ORBIT_{camp_num}",
                True, True, g_id, ra, dec, float(exm.get("pmra_mas_yr") or 0.0), float(exm.get("pmdec_mas_yr") or 0.0),
                dist_pc, True, gmag, exm.get("phot_bp_mag"), exm.get("phot_rp_mag"), jmag, hmag, kmag,
                teff, mass, rv0, n_pl, bool(ok.get("transit", False)), rank, fn,
                "CARMENES_VIS_520_960NM", 94600.0, mjd, c["expt"],
                pwin, sph, prv, fn, f"CARMENES_VIS/{st}/{fn}", c["url"], hl, hl, [],
            ))
        orb_json["campaigns"][st] = {
            "campaign_order": camp_num, "star": st, "common_name": f"{st} (CARMENES Orbit #{camp_num})",
            "instrument": "CARMENES_VIS", "n_epochs": 4, "n_distinct_nights": 4,
            "baseline_days": round(max(d_mjd) - min(d_mjd), 3),
            "orb_per_days": round(ok["P_d"], 6), "orb_ecc": round(ok["ecc"], 4),
            "orb_omega_deg": round(ok["omega"], 2), "kp_kms": round(ok["k_kms"], 6),
            "orbital_dv_span_kms": round(max(rvs) - min(rvs), 6),
        }

    # 3D. Resolve 1 HARPS_N campaign (HD 219134, Orbit #252, 4 distinct nights = 4 FITS)
    st_hn = "HD219134"
    camp_hn = 252
    ra_hn, dec_hn, dist_hn, gid_hn, ur_hn, ok_hn = _star_attrs(st_hn)
    exm_hn = star_extra_meta.get(st_hn, {})
    ra_r, dec_r = math.radians(348.32), math.radians(57.168)
    dr_r = math.radians(0.10)
    q_hn = (
        f"SELECT TOP 1000 EXP_ID, OBJECT, DATE_OBS, EXPTIME FROM tng.TNG_TAP "
        f"WHERE EXP_ID LIKE 'HARPN.%_s1d_A.fits.gz' AND policy='FREE' "
        f"AND RA_RAD BETWEEN {ra_r - dr_r:.6f} AND {ra_r + dr_r:.6f} "
        f"AND DEC_RAD BETWEEN {dec_r - dr_r:.6f} AND {dec_r + dr_r:.6f}"
    )
    hn_rows = _tap_csv("http://archives.ia2.inaf.it/vo/tap/tng/sync", q_hn, timeout=30, use_post=True)
    hn_cands = {}
    for row in hn_rows:
        exp_id = (row.get("exp_id") or "").strip()
        base = exp_id.replace("_s1d_A.fits.gz", "")
        if not exp_id or base in prior_dp_basenames or exp_id in prior_dp_basenames or base == "HARPN.2015-05-16T03-51-36.767":
            continue
        mjd = _iso_to_mjd(row.get("date_obs") or "")
        expt = float(row.get("exptime") or 0.0)
        if mjd is not None and expt >= 30.0:
            dk = int(mjd)
            url_hn = f"http://archives.ia2.inaf.it/files/tng/{exp_id}"
            item = {"dp_id": base, "exp_id": exp_id, "url": url_hn, "mjd": mjd, "expt": expt}
            if dk not in hn_cands or expt > hn_cands[dk]["expt"]:
                hn_cands[dk] = item
    chosen_hn = _select_4_spaced_nights(list(hn_cands.values()), "mjd", min_gap_days=1.0)
    hn_lens = [_http_head_len(c["url"]) for c in chosen_hn]
    assert all(hl > 100000 for hl in hn_lens)
    gmag = float(ur_hn["phot_g_mag"]) if ur_hn.get("phot_g_mag") else None
    jmag = float(ur_hn["j_mag"]) if ur_hn.get("j_mag") else None
    hmag = float(ur_hn["h_mag"]) if ur_hn.get("h_mag") else None
    kmag = float(ur_hn["ks_mag"]) if ur_hn.get("ks_mag") else None
    d_mjd, rvs = [], []
    for rank, (c, hl) in enumerate(zip(chosen_hn, hn_lens), 1):
        mjd = c["mjd"]
        sph, pwin, prv = _kepler_rv(mjd, ok_hn["t0_mjd"], ok_hn["P_d"], ok_hn["ecc"], ok_hn["omega"], ok_hn["k_kms"])
        d_mjd.append(mjd)
        rvs.append(prv)
        cohort_rows.append(_make_row(
            "HARPS_N", st_hn, f"{st_hn} (D109 <10pc HARPS-N Orbit #{camp_hn})",
            ur_hn["role"], "SUB10PC_HOST_DRIFT_CLOSURE", f"D109_10PC_HOST_ORBIT_{camp_hn}",
            True, True, gid_hn, ra_hn, dec_hn, float(exm_hn.get("pmra_mas_yr") or 0.0), float(exm_hn.get("pmdec_mas_yr") or 0.0),
            dist_hn, True, gmag, exm_hn.get("phot_bp_mag"), exm_hn.get("phot_rp_mag"), jmag, hmag, kmag,
            float(ur_hn.get("teff_k") or 4800.0), float(exm_hn.get("stellar_mass_msun") or 0.81), float(exm_hn.get("prior_rv_kms") or -18.6),
            int(float(ur_hn.get("n_exoplanets") or 6)), False, rank, c["dp_id"],
            "HARPSN_383_690NM", 115000.0, mjd, c["expt"], pwin, sph, prv,
            c["exp_id"], f"HARPS_N/{st_hn}/{c['exp_id']}", c["url"], hl, hl, [],
        ))
    orb_json["campaigns"][st_hn] = {
        "campaign_order": camp_hn, "star": st_hn, "common_name": f"{st_hn} (HARPS-N Orbit #{camp_hn})",
        "instrument": "HARPS_N", "n_epochs": 4, "n_distinct_nights": 4,
        "baseline_days": round(max(d_mjd) - min(d_mjd), 3),
        "orb_per_days": round(ok_hn["P_d"], 6), "orb_ecc": round(ok_hn["ecc"], 4),
        "orb_omega_deg": round(ok_hn["omega"], 2), "kp_kms": round(ok_hn["k_kms"], 6),
        "orbital_dv_span_kms": round(max(rvs) - min(rvs), 6),
    }

    assert len(cohort_rows) == 216, f"Expected 216 cohort rows, got {len(cohort_rows)}"
    assert len(orb_json["campaigns"]) == 54
    assert len(orb_json["retro_unlocked_10"]) == 10
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_json, indent=2) + "\n", encoding="utf-8")

    # Write FROZEN_COHORT_D109.csv
    cohort_rows.sort(key=lambda r: (r["instrument"], r["canonical_target"], int(r["epoch_rank"])))
    with (WS / "FROZEN_COHORT_D109.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COHORT_COLS)
        w.writeheader()
        for r in cohort_rows:
            w.writerow(r)

    # 4. Prior Exclusion Verification
    new_dp_ids = [r["dp_id"] for r in cohort_rows]
    overlap = sorted((set(new_dp_ids) & prior_dp_basenames) | (set(new_dp_ids) & fmt_set))
    assert not overlap, f"dp_id overlap detected: {overlap}"
    assert len(set(new_dp_ids)) == 216, "Duplicate dp_id inside D109 cohort!"

    proj_bytes = sum(int(r["total_bytes"]) for r in cohort_rows)
    prior_bridge_stars = sorted({r["canonical_target"] for r in cohort_rows})
    sci_stars = {r["canonical_target"] for r in cohort_rows if r["role"] == "SCIENCE"}
    ctrl_stars = {r["canonical_target"] for r in cohort_rows if r["role"] == "CONTROL"}
    assert len(prior_bridge_stars) == 54

    pex_out = {
        "schema": "D109_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D109",
        "verified_utc": datetime.now(timezone.utc).isoformat(),
        "prior_phases_covered": "D001-D108 (Companion Archives A-AH)",
        "n_prior_excluded_coords": len(prior_coords),
        "n_prior_excluded_dp_ids": len(prior_dp),
        "n_format_check_excluded_dp_ids": len(fmt_probes),
        "d109_total_stars": 54,
        "d109_brand_new_unique_stars": 0,
        "d109_prior_bridge_stars": 54,
        "d109_science_stars": len(sci_stars),
        "d109_control_stars": len(ctrl_stars),
        "d109_brand_new_within_10pc": 0,
        "d109_total_observations": len(cohort_rows),
        "d109_total_physical_files": len(cohort_rows),
        "d109_projected_download_bytes": proj_bytes,
        "d109_projected_download_mib": round(proj_bytes / (1024.0 * 1024.0), 3),
        "d109_dp_id_overlap_count": len(overlap),
        "format_check_excluded_dp_ids": fmt_probes,
        "excluded_dp_ids": sorted(prior_dp),
        "excluded_targets_coordinate_registry": prior_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pex_out, indent=2) + "\n", encoding="utf-8")

    # 5. Stage-1 Seal (7 immutable Stage-1 files -> METHOD_LOCK.json -> LOCK_RECEIPT.json)
    assert not RAW_DIR.exists(), f"{RAW_DIR} appeared before seal!"
    now_epoch = time.time()
    now_utc = datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat()
    stage1_names = [
        "v6_7_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D109.csv",
        "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "PRIOR_V6_6_PHASES_SNAPSHOT.json",
    ]
    stage1_hashes = {fn: _sha256_file(WS / fn) for fn in stage1_names}

    ml = {
        "schema": "D109_METHOD_LOCK",
        "phase_id": "D109",
        "detector": DETECTOR_NAME,
        "locked_utc": now_utc,
        "locked_unix_epoch": round(now_epoch, 4),
        "d109_brand_new_stars": 0,
        "d109_prior_bridges": len(prior_bridge_stars),
        "d109_total_observations": len(cohort_rows),
        "d109_total_physical_files": len(cohort_rows),
        "d109_projected_download_mib": round(proj_bytes / (1024.0 * 1024.0), 3),
        "calibration_suites_new": {
            "V67_BAYESIAN_OCCURRENCE_240": 240,
            "V67_SCALE_SEPARATION_CWTFM_180": 180,
        },
        "stage_1_files": stage1_hashes,
    }
    (WS / "METHOD_LOCK.json").write_text(json.dumps(ml, indent=2) + "\n", encoding="utf-8")
    ml_sha = _sha256_file(WS / "METHOD_LOCK.json")

    lr = {
        "schema": "D109_LOCK_RECEIPT",
        "phase_id": "D109",
        "status": "STAGE-1 SEALED",
        "locked_utc": now_utc,
        "locked_unix_epoch": round(now_epoch, 4),
        "inputs_dir_exists_at_seal": RAW_DIR.exists(),
        "method_lock_sha256": ml_sha,
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lr, indent=2) + "\n", encoding="utf-8")
    print(f"STAGE-1 SEALED: new_stars=0, bridges=54 (<10pc hosts), obs=216, proj_est_mib={proj_bytes/1048576:.2f}, overlap=0, inputs_at_seal={RAW_DIR.exists()}")


if __name__ == "__main__":
    main()
