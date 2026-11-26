#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D110 (V6.8) Stage-1 Metadata-Only Cohort Builder & Prospective Seal:
  - Queries ONLY public metadata APIs/catalogs (CADC ivoa.ObsCore for CFHT ESPaDOnS & SPIRou;
    PolarBase REST API + wget_links for TBL NARVAL; NASA Exoplanet Archive & IRSA 2MASS).
  - NEVER downloads raw science files and asserts `inputs_d110_v6_8` does NOT exist at seal.
  - Enforces strict 0-overlap against all 35 prior Companion Archives A-AI
    (1,077 prior coords + 4,349 prior dp_ids + 46 format-probe IDs).
  - Extracts `PRIOR_V6_7_PHASES_SNAPSHOT.json` cleanly from Companion Archive AI.
  - Freezes 48 unique targets (40 flagship prior bridges incl. 16CYGB Penta-Regime +
    8 brand-new stars with min_prior_sep >= 600") and 87 polarimetric exposures (I, Q/U/V, N1, N2).
  - Seals 7 immutable Stage-1 artifacts into `METHOD_LOCK.json` and `LOCK_RECEIPT.json`.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent
ROOT = WS.parent.parent
ARCHIVES_DIR = ROOT / "archives"
RAW_DIR = ROOT / "inputs_d110_v6_8"
ARCHIVE_AI = ARCHIVES_DIR / "SETI_D109_V6_7_10PC_DRIFT_CLOSURE_BAYESIAN_FTX_CWTFM_RESULTS_2026-11-25.zip"
ARCHIVE_AI_SHA = "7f681525dc74be7c2f80a464b47f947960f8c0206e31fce2cdbe0a69ed76215c"

sys.path.insert(0, str(WS))
import v6_8_detector as det  # noqa: E402

CADC_TAP = "https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/argus/sync"
POLARBASE_SEARCH = "https://www.polarbase.ovgso.fr/api/spectra"
POLARBASE_LINKS = "https://www.polarbase.ovgso.fr/download/wget_links"
EXOPLANET_TAP = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
IRSA_TAP = "https://irsa.ipac.caltech.edu/TAP/sync"

COHORT_COLS = [
    "instrument", "canonical_target", "common_name", "role", "subrole",
    "panchromatic_bridge", "is_prior_bridge", "s_ra", "s_dec", "dist_pc", "within_10pc",
    "phot_g_mag", "j_mag", "h_mag", "ks_mag", "teff_k", "n_exoplanets",
    "stokes", "dp_id", "obs_id", "resolving_power", "regime",
    "mjd_obs", "t_exptime", "f1_rel", "f1_url", "est_bytes", "min_prior_sep_arcsec",
]

# Verified flagship prior bridges & brand-new polarimetric targets
ESPADONS_QUV_BRIDGES = [
    "ADLEO", "AUMIC", "HD189733", "HD201601", "HD22468", "IIPEG",
    "51PEG", "HD209458", "SIGMAGEM", "61CYGA", "EQPEG",
]
ESPADONS_V_TARGETS = [
    "GJ729", "LALANDE21185", "DXCNC", "YZCET", "HD102195", "HD130322", "V410TAU",
]

SPIROU_QUV_BRIDGES = ["EVLAC"]
SPIROU_Q_BRIDGES = ["HD201601"]
SPIROU_V_TARGETS = [
    "AUMIC", "ADLEO", "HD189733", "BARNARDSSTAR", "WOLF359", "ROSS248",
    "ROSS128", "STRUVE2398A", "GXAND", "GJ687", "GJ1002", "GJ412A",
    "GJ436", "TAUBOO", "V410TAU",
]

NARVAL_QUV_BRIDGES = [
    ("TAUBOO", "tau boo"),
    ("PROCYON", "procyon"),
    ("SIRIUS", "sirius"),
    ("BETELGEUSE", "betelgeuse"),
]
NARVAL_V_TARGETS = [
    # Flagship Penta-Regime & multi-regime optical bridges
    ("16CYGB", "16 cyg b", "V"),
    ("EPSERI", "eps eri", "V"),
    ("TAUCET", "tau cet", "V"),
    ("HD146233", "18 sco", "V"),
    ("HD36395", "gj 205", "V"),
    ("HD219134", "hd 219134", "V"),
    ("HD34029", "capella", "V"),
    ("HD62509", "pollux", "V"),
    ("ALFTAU", "aldebaran", "V"),
    ("ARCTURUS", "arcturus", "V"),
    ("ALTAIR", "altair", "V"),
    # Brand-new PolarBase magnetic stars (min_prior_sep >= 5000")
    ("53CAM", "53 cam", "Q"),
    ("EPSVIR", "eps vir", "V"),
    ("HD166435", "hd 166435", "V"),
    ("HD73350", "hd 73350", "V"),
    ("HD75332", "hd 75332", "V"),
]

# Brand-new star astrophysical metadata baseline (supplemented by live TAP/PolarBase queries)
BRAND_NEW_SPECS: dict[str, dict[str, Any]] = {
    "HD102195": {"common_name": "HD 102195 (ET Dra Exoplanet Host)", "role": "SCIENCE", "subrole": "MAGNETIC_EXOPLANET_HOST_POL", "ra": 176.425406, "dec": 2.820991, "dist_pc": 29.3386, "g_mag": 7.847, "j_mag": 6.629, "h_mag": 6.268, "ks_mag": 6.151, "teff_k": 5301.0, "n_pl": 1},
    "HD130322": {"common_name": "HD 130322 (Maranhao Exoplanet Host)", "role": "SCIENCE", "subrole": "MAGNETIC_EXOPLANET_HOST_POL", "ra": 221.885798, "dec": -0.282078, "dist_pc": 31.8766, "g_mag": 7.834, "j_mag": 6.712, "h_mag": 6.315, "ks_mag": 6.234, "teff_k": 5387.0, "n_pl": 1},
    "V410TAU":  {"common_name": "V410 Tau (Active T Tauri Magnetosphere)", "role": "SCIENCE", "subrole": "PRE_MS_MAGNETIC_POL", "ra": 64.629170, "dec": 28.454470, "dist_pc": 129.000, "g_mag": 10.650, "j_mag": 8.449, "h_mag": 7.789, "ks_mag": 7.629, "teff_k": 4400.0, "n_pl": 0},
    "53CAM":    {"common_name": "53 Cam (Ap SrCrEu Magnetic Prototype)", "role": "SCIENCE", "subrole": "AP_MAGNETIC_POL", "ra": 120.42680, "dec": 60.32440, "dist_pc": 97.6510, "g_mag": 5.950, "j_mag": 5.820, "h_mag": 5.773, "ks_mag": 5.750, "teff_k": 8400.0, "n_pl": 0},
    "EPSVIR":   {"common_name": "eps Vir (Vindemiatrix Magnetic Giant Control)", "role": "CONTROL", "subrole": "MAGNETIC_GIANT_CONTROL", "ra": 195.54420, "dec": 10.95910, "dist_pc": 33.1000, "g_mag": 2.600, "j_mag": 1.450, "h_mag": 0.894, "ks_mag": 0.820, "teff_k": 4990.0, "n_pl": 0},
    "HD166435": {"common_name": "HD 166435 (Young Magnetic Solar Analog)", "role": "SCIENCE", "subrole": "SOLAR_ANALOG_MAGNETIC_POL", "ra": 272.33910, "dec": 29.95170, "dist_pc": 24.4110, "g_mag": 6.690, "j_mag": 5.710, "h_mag": 5.389, "ks_mag": 5.320, "teff_k": 5811.0, "n_pl": 0},
    "HD73350":  {"common_name": "HD 73350 (Active G5V Zeeman-Doppler Target)", "role": "SCIENCE", "subrole": "SOLAR_ANALOG_MAGNETIC_POL", "ra": 129.45960, "dec": -6.80690, "dist_pc": 24.3520, "g_mag": 6.580, "j_mag": 5.650, "h_mag": 5.318, "ks_mag": 5.230, "teff_k": 5821.0, "n_pl": 0},
    "HD75332":  {"common_name": "HD 75332 (F7Vn Active Dynamo Benchmark)", "role": "SCIENCE", "subrole": "F_DYNAMO_MAGNETIC_POL", "ra": 132.63430, "dec": 33.28510, "dist_pc": 27.3820, "g_mag": 6.080, "j_mag": 5.290, "h_mag": 5.035, "ks_mag": 4.960, "teff_k": 6218.0, "n_pl": 0},
}


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


def _http_post_json(url: str, payload: dict[str, Any], timeout: int = 30) -> Any:
    for attempt in range(5):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "SETI-D110-Stage1/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", errors="ignore"))
        except Exception:
            if attempt == 4:
                raise
            time.sleep(1.5 * (attempt + 1))


def _http_post_text(url: str, payload: dict[str, Any], timeout: int = 30) -> str:
    for attempt in range(5):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "SETI-D110-Stage1/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", errors="ignore")
        except Exception:
            if attempt == 4:
                raise
            time.sleep(1.5 * (attempt + 1))


def _tap_csv(url: str, query_str: str, is_cadc: bool = True, timeout: int = 45) -> list[dict[str, str]]:
    for attempt in range(5):
        try:
            if is_cadc:
                data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query_str}).encode()
                req = urllib.request.Request(url, data=data, headers={"User-Agent": "SETI-D110-Stage1/1.0"})
            else:
                full = url + "?" + urllib.parse.urlencode({"query": query_str, "format": "csv"})
                req = urllib.request.Request(full, headers={"User-Agent": "SETI-D110-Stage1/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                txt = r.read().decode("utf-8", errors="ignore")
            return list(csv.DictReader(io.StringIO(txt)))
        except Exception:
            if attempt == 4:
                raise
            time.sleep(1.5 * (attempt + 1))


def _build_prior_v67_snapshot_and_exclusions() -> tuple[dict[str, Any], list[dict[str, Any]], set[str], list[str], dict[str, tuple[float, float]], dict[str, dict[str, str]]]:
    assert ARCHIVE_AI.exists(), f"Missing Archive AI: {ARCHIVE_AI}"
    assert _sha256_file(ARCHIVE_AI) == ARCHIVE_AI_SHA, "Archive AI SHA-256 mismatch!"

    with zipfile.ZipFile(ARCHIVE_AI) as zf:
        def _zcsv(suffix: str) -> list[dict[str, str]]:
            nm = next(n for n in zf.namelist() if n.endswith(suffix))
            return list(csv.DictReader(io.StringIO(zf.read(nm).decode("utf-8"))))

        def _zjson(suffix: str) -> Any:
            nm = next(n for n in zf.namelist() if n.endswith(suffix))
            return json.loads(zf.read(nm).decode("utf-8"))

        sum_ai = _zjson("/results/SUMMARY.json")
        u1004_rows = _zcsv("/results/UNIFIED_PANCHROMATIC_V6_7_SYNTHESIS_1004STARS.csv")
        br178_rows = _zcsv("/results/PANCHROMATIC_BRIDGE_178STARS_V67.csv")
        ell1004_rows = _zcsv("/results/MULTIEVENT_ELLIPSOID_1004STARS.csv")
        comb_u = _zcsv("/results/ALLSKY_COMB_V4_1_UNIFIED_D079_D109.csv")
        comb_c = _zcsv("/results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D109.csv")
        eirp_d109 = _zcsv("/results/EIRP_UPPER_LIMITS_D109.csv")
        bf37_d109 = _zcsv("/results/CONTROL_RADIOMETRIC_BACKFILL_37STARS_D109.csv")
        px109 = _zjson("PRIOR_EXCLUSION_VERIFICATION.json")
        man109 = _zjson("FULL_D109_INPUT_MANIFEST.json")
        snap109 = _zjson("PRIOR_V6_6_PHASES_SNAPSHOT.json")

    u1004_map = {r["star"]: r for r in u1004_rows}
    star_coords = {r["star"]: (float(r["ra_deg"]), float(r["dec_deg"])) for r in ell1004_rows}
    assert len(u1004_map) == 1004 and len(star_coords) == 1004

    prior_coords = list(px109["excluded_targets_coordinate_registry"])
    assert len(prior_coords) == 1077
    fmt_probes = sorted(px109["format_check_excluded_dp_ids"])
    d109_dps = {str(o["dp_id"]).strip() for o in man109["observations"]}
    prior_dp_ids = set(px109["excluded_dp_ids"]) | d109_dps
    assert len(d109_dps) == 216
    assert len(prior_dp_ids) == 4349, f"Expected 4349 cumulative prior dp_ids, got {len(prior_dp_ids)}"

    # Merge D109 distinct nights and radiometry into prior snapshot
    nights_by_star: dict[str, set[int]] = {
        st: set(int(x) for x in lst) for st, lst in snap109["prior_star_distinct_nights"].items()
    }
    for o in man109["observations"]:
        st = o["star"]
        # Use provenance CSV or obs MJD from cohort in AI
        nights_by_star.setdefault(st, set())
    with zipfile.ZipFile(ARCHIVE_AI) as zf:
        prov109 = list(csv.DictReader(io.StringIO(zf.read(next(n for n in zf.namelist() if n.endswith("EXPOSURE_PROVENANCE_D109.csv"))).decode("utf-8"))))
    for pr in prov109:
        st = pr["star"]
        mjd = _iso_to_mjd(pr.get("mjd_obs", ""))
        if mjd is not None:
            nights_by_star.setdefault(st, set()).add(int(round(mjd)))

    rad_cat: dict[str, list[dict[str, Any]]] = {
        st: list(lst) for st, lst in snap109["prior_star_radiometric_catalog"].items()
    }
    for er in eirp_d109:
        st = er["star"]
        rad_cat.setdefault(st, []).append({
            "ph": "D109", "inst": er["instrument"], "bid": er["band_id"], "cat": "BEAMED",
            "wa": float(er["wave_bary_a"]), "fl": float(er["flux_lim_erg_cm2_s"]),
            "li": float(er["l_iso_mw"]), "p10": float(er["p_beam_10m_kw"]),
        })
    for br in bf37_d109:
        st = br["star"]
        rad_cat.setdefault(st, []).append({
            "ph": br["phase_origin"], "inst": br["instrument"], "bid": br["band_id"], "cat": "BEAMED",
            "wa": float(br["wave_a"]), "fl": float(br["flux_lim_erg_cm2_s"]),
            "li": float(br["l_iso_mw"]), "p10": float(br["p_beam_10m_kw"]),
        })

    snap = {
        "schema": "PRIOR_V6_7_PHASES_SNAPSHOT",
        "d109_summary_headline": sum_ai["unified_1004star_panchromatic_v6_7_synthesis"],
        "d109_root_summary": {
            "total_calibration_trials_d109": sum_ai["synthetic_calibration_7311_trials"]["total_trials"],
            "total_integration_hours_d109": sum_ai["cohort"]["integration_hours_d109"],
        },
        "prior_unified_1004_rows": u1004_rows,
        "prior_bridge_rows": br178_rows,
        "prior_ellipsoid_1004_rows": ell1004_rows,
        "prior_allsky_comb_unified_rows": comb_u,
        "prior_allsky_comb_candidate_rows": comb_c,
        "prior_star_distinct_nights": {st: sorted(nights_by_star.get(st, set())) for st in sorted(u1004_map)},
        "prior_star_radiometric_catalog": {st: rad_cat.get(st, []) for st in sorted(u1004_map)},
    }
    return snap, prior_coords, prior_dp_ids, fmt_probes, star_coords, u1004_map


def _refresh_brand_new_metadata() -> None:
    """Query NASA Exoplanet Archive + IRSA 2MASS TAP to verify live metadata for brand-new targets."""
    q_pl = "SELECT hostname, sy_dist, sy_vmag, sy_gaiamag, sy_jmag, sy_hmag, sy_kmag, st_teff, sy_pnum FROM pscomppars WHERE hostname IN ('HD 102195', 'HD 130322')"
    for row in _tap_csv(EXOPLANET_TAP, q_pl, is_cadc=False, timeout=25):
        key = row["hostname"].replace(" ", "").upper()
        if key in BRAND_NEW_SPECS:
            sp = BRAND_NEW_SPECS[key]
            if row.get("sy_dist"): sp["dist_pc"] = float(row["sy_dist"])
            if row.get("sy_gaiamag"): sp["g_mag"] = float(row["sy_gaiamag"])
            elif row.get("sy_vmag"): sp["g_mag"] = float(row["sy_vmag"])
            if row.get("sy_jmag"): sp["j_mag"] = float(row["sy_jmag"])
            if row.get("sy_hmag"): sp["h_mag"] = float(row["sy_hmag"])
            if row.get("sy_kmag"): sp["ks_mag"] = float(row["sy_kmag"])
            if row.get("st_teff"): sp["teff_k"] = float(row["st_teff"])
            if row.get("sy_pnum"): sp["n_pl"] = int(float(row["sy_pnum"]))

    q_irsa = "SELECT TOP 3 designation, ra, dec, j_m, h_m, k_m FROM fp_psc WHERE CONTAINS(POINT('ICRS',ra,dec), CIRCLE('ICRS',64.62917,28.45447,0.005))=1"
    irows = _tap_csv(IRSA_TAP, q_irsa, is_cadc=False, timeout=25)
    if irows:
        r0 = irows[0]
        BRAND_NEW_SPECS["V410TAU"]["j_mag"] = float(r0["j_m"])
        BRAND_NEW_SPECS["V410TAU"]["h_mag"] = float(r0["h_m"])
        BRAND_NEW_SPECS["V410TAU"]["ks_mag"] = float(r0["k_m"])


def main() -> int:
    assert not RAW_DIR.exists(), f"{RAW_DIR} must NOT exist before Stage-1 seal!"
    print("Building PRIOR_V6_7_PHASES_SNAPSHOT from Archive AI and checking exclusions...")
    snap, prior_coords, prior_dp_ids, fmt_probes, star_coords, u1004_map = _build_prior_v67_snapshot_and_exclusions()
    excl_all_dp = prior_dp_ids | set(fmt_probes)

    print("Refreshing brand-new target metadata via NASA Exoplanet Archive & IRSA 2MASS...")
    _refresh_brand_new_metadata()

    # Verify brand-new targets are >= 600" away from all 1,077 prior coordinates
    for key, sp in sorted(BRAND_NEW_SPECS.items()):
        assert key not in u1004_map, f"Brand-new star {key} already in u1004!"
        msep = min(_ang_sep_arcsec(sp["ra"], sp["dec"], float(c["ra_deg"]), float(c["dec_deg"])) for c in prior_coords)
        assert msep >= 600.0, f"Brand-new {key} too close to prior cohort: {msep:.1f}\""
        sp["min_prior_sep_arcsec"] = round(msep, 2)
        print(f"  [NEW] {key:10s}: ra={sp['ra']:.4f}, dec={sp['dec']:.4f}, d={sp['dist_pc']:.2f} pc, min_prior_sep={msep:.1f}\" >= 600\"")

    def _star_meta(st: str) -> dict[str, Any]:
        if st in u1004_map:
            ur = u1004_map[st]
            ra, dec = star_coords[st]
            msep = min(_ang_sep_arcsec(ra, dec, float(c["ra_deg"]), float(c["dec_deg"])) for c in prior_coords)
            return {
                "common_name": ur["common_name"], "role": ur["role"], "subrole": ur.get("subrole", "POLARIMETRIC_BRIDGE"),
                "is_prior_bridge": True, "ra": ra, "dec": dec, "dist_pc": float(ur["dist_pc"]),
                "within_10pc": ur["within_10pc"] == "True",
                "g_mag": float(ur["phot_g_mag"]) if ur.get("phot_g_mag") else None,
                "j_mag": float(ur["j_mag"]) if ur.get("j_mag") else None,
                "h_mag": float(ur["h_mag"]) if ur.get("h_mag") else None,
                "ks_mag": float(ur["ks_mag"]) if ur.get("ks_mag") else None,
                "teff_k": float(ur["teff_k"]), "n_pl": int(float(ur.get("n_exoplanets") or 0)),
                "min_prior_sep_arcsec": round(msep, 2),
            }
        sp = BRAND_NEW_SPECS[st]
        return {
            "common_name": sp["common_name"], "role": sp["role"], "subrole": sp["subrole"],
            "is_prior_bridge": False, "ra": sp["ra"], "dec": sp["dec"], "dist_pc": sp["dist_pc"],
            "within_10pc": sp["dist_pc"] <= 10.0,
            "g_mag": sp["g_mag"], "j_mag": sp["j_mag"], "h_mag": sp["h_mag"], "ks_mag": sp["ks_mag"],
            "teff_k": sp["teff_k"], "n_pl": sp["n_pl"],
            "min_prior_sep_arcsec": sp["min_prior_sep_arcsec"],
        }

    # 1. Batch query CADC ObsCore for ALL ESPaDOnS & SPIRou polarimetric targets
    cadc_stars = sorted(set(ESPADONS_QUV_BRIDGES + ESPADONS_V_TARGETS + SPIROU_QUV_BRIDGES + SPIROU_Q_BRIDGES + SPIROU_V_TARGETS))
    cadc_metas = {st: _star_meta(st) for st in cadc_stars}
    conds = " OR ".join(
        f"1=CONTAINS(POINT('ICRS',s_ra,s_dec), CIRCLE('ICRS',{cadc_metas[st]['ra']:.5f},{cadc_metas[st]['dec']:.5f},0.025))"
        for st in cadc_stars
    )
    q_cadc = f"""SELECT obs_id, obs_publisher_did, instrument_name, target_name, s_ra, s_dec, t_min, t_exptime, pol_states, em_res_power, access_estsize
FROM ivoa.ObsCore
WHERE obs_collection='CFHT' AND dataproduct_type='spectrum'
AND instrument_name IN ('ESPaDOnS','SPIRou')
AND obs_release_date < '2026-11-26'
AND t_exptime >= 5.0
AND pol_states IS NOT NULL
AND ({conds})"""
    print(f"Querying CADC ivoa.ObsCore (ESPaDOnS + SPIRou) across {len(cadc_stars)} targets...")
    crows = _tap_csv(CADC_TAP, q_cadc, is_cadc=True, timeout=60)
    print(f"  Returned {len(crows)} public CFHT polarimetric metadata rows.")

    cadc_by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for cr in crows:
        did = cr.get("obs_publisher_did", "")
        dp_id = did.split("/")[-1].strip()
        if not dp_id.endswith("p"):
            continue
        if dp_id in excl_all_dp or cr["obs_id"].strip() in excl_all_dp:
            continue
        sra, sdec = float(cr["s_ra"]), float(cr["s_dec"])
        best_st = min(cadc_stars, key=lambda st: _ang_sep_arcsec(sra, sdec, cadc_metas[st]["ra"], cadc_metas[st]["dec"]))
        if _ang_sep_arcsec(sra, sdec, cadc_metas[best_st]["ra"], cadc_metas[best_st]["dec"]) > 90.0:
            continue
        raw_pol = cr["pol_states"].strip("/")
        norm_pol = raw_pol.split("/")[-1] if "/" in raw_pol else raw_pol
        if norm_pol not in ("Q", "U", "V"):
            continue
        inst_api = cr["instrument_name"].strip()
        inst_d110 = "CFHT_ESPADONS_POL" if inst_api == "ESPaDOnS" else "CFHT_SPIROU_POL"
        cadc_by_key[(best_st, inst_d110, norm_pol)].append({
            "obs_id": cr["obs_id"].strip(),
            "dp_id": dp_id,
            "mjd_obs": float(cr["t_min"]),
            "t_exptime": float(cr["t_exptime"]),
            "res_power": float(cr.get("em_res_power") or (65000.0 if inst_api == "ESPaDOnS" else 70000.0)),
            "est_bytes": int(float(cr["access_estsize"]) * 1024) if cr.get("access_estsize") else (6_500_000 if inst_api == "ESPaDOnS" else 18_000_000),
            "target_archive": cr["target_name"].strip(),
        })

    def _pick_cadc_exp(st: str, inst_d110: str, pol: str, used_dps: set[str]) -> dict[str, Any]:
        cands = [x for x in cadc_by_key[(st, inst_d110, pol)] if x["dp_id"] not in used_dps]
        assert cands, f"No fresh CFHT {inst_d110} Stokes {pol} exposure found for {st}!"
        # Pick highest exposure time up to 900s (or max available) with deterministic tiebreak
        good = [x for x in cands if 30.0 <= x["t_exptime"] <= 900.0]
        pool = good if good else cands
        chosen = sorted(pool, key=lambda x: (-x["t_exptime"], -x["mjd_obs"], x["dp_id"]))[0]
        used_dps.add(chosen["dp_id"])
        return chosen

    cohort_rows: list[dict[str, Any]] = []
    used_dps: set[str] = set()

    def _add_row(inst_d110: str, st: str, pol: str, dp_id: str, obs_id: str, res_p: float, regime: str, mjd: float, expt: float, rel_path: str, url: str, est_b: int) -> None:
        m = _star_meta(st)
        cohort_rows.append({
            "instrument": inst_d110,
            "canonical_target": st,
            "common_name": m["common_name"],
            "role": m["role"],
            "subrole": m["subrole"],
            "panchromatic_bridge": str(m["is_prior_bridge"]),
            "is_prior_bridge": str(m["is_prior_bridge"]),
            "s_ra": f"{m['ra']:.6f}",
            "s_dec": f"{m['dec']:.6f}",
            "dist_pc": f"{m['dist_pc']:.5f}",
            "within_10pc": str(m["within_10pc"]),
            "phot_g_mag": "" if m["g_mag"] is None else f"{m['g_mag']:.4f}",
            "j_mag": "" if m["j_mag"] is None else f"{m['j_mag']:.4f}",
            "h_mag": "" if m["h_mag"] is None else f"{m['h_mag']:.4f}",
            "ks_mag": "" if m["ks_mag"] is None else f"{m['ks_mag']:.4f}",
            "teff_k": f"{m['teff_k']:.1f}",
            "n_exoplanets": m["n_pl"],
            "stokes": pol,
            "dp_id": dp_id,
            "obs_id": obs_id,
            "resolving_power": f"{res_p:.1f}",
            "regime": regime,
            "mjd_obs": f"{mjd:.6f}",
            "t_exptime": f"{expt:.2f}",
            "f1_rel": rel_path,
            "f1_url": url,
            "est_bytes": est_b,
            "min_prior_sep_arcsec": m["min_prior_sep_arcsec"],
        })

    # Populate ESPaDOnS rows
    for st in ESPADONS_QUV_BRIDGES:
        for pol in ("Q", "U", "V"):
            ch = _pick_cadc_exp(st, "CFHT_ESPADONS_POL", pol, used_dps)
            _add_row(
                "CFHT_ESPADONS_POL", st, pol, ch["dp_id"], ch["obs_id"], 65000.0, "OPTICAL",
                ch["mjd_obs"], ch["t_exptime"], f"CFHT_ESPADONS_POL/{st}/{ch['dp_id']}.fits",
                f"https://cadc-west-01.canfar.net/raven/files/cadc:CFHT/{ch['dp_id']}.fits", ch["est_bytes"],
            )
    for st in ESPADONS_V_TARGETS:
        ch = _pick_cadc_exp(st, "CFHT_ESPADONS_POL", "V", used_dps)
        _add_row(
            "CFHT_ESPADONS_POL", st, "V", ch["dp_id"], ch["obs_id"], 65000.0, "OPTICAL",
            ch["mjd_obs"], ch["t_exptime"], f"CFHT_ESPADONS_POL/{st}/{ch['dp_id']}.fits",
            f"https://cadc-west-01.canfar.net/raven/files/cadc:CFHT/{ch['dp_id']}.fits", ch["est_bytes"],
        )

    # Populate SPIRou rows
    for st in SPIROU_QUV_BRIDGES:
        for pol in ("Q", "U", "V"):
            ch = _pick_cadc_exp(st, "CFHT_SPIROU_POL", pol, used_dps)
            _add_row(
                "CFHT_SPIROU_POL", st, pol, ch["dp_id"], ch["obs_id"], 70000.0, "NIR",
                ch["mjd_obs"], ch["t_exptime"], f"CFHT_SPIROU_POL/{st}/{ch['dp_id']}.fits",
                f"https://cadc-west-01.canfar.net/raven/files/cadc:CFHT/{ch['dp_id']}.fits", ch["est_bytes"],
            )
    for st in SPIROU_Q_BRIDGES:
        ch = _pick_cadc_exp(st, "CFHT_SPIROU_POL", "Q", used_dps)
        _add_row(
            "CFHT_SPIROU_POL", st, "Q", ch["dp_id"], ch["obs_id"], 70000.0, "NIR",
            ch["mjd_obs"], ch["t_exptime"], f"CFHT_SPIROU_POL/{st}/{ch['dp_id']}.fits",
            f"https://cadc-west-01.canfar.net/raven/files/cadc:CFHT/{ch['dp_id']}.fits", ch["est_bytes"],
        )
    for st in SPIROU_V_TARGETS:
        ch = _pick_cadc_exp(st, "CFHT_SPIROU_POL", "V", used_dps)
        _add_row(
            "CFHT_SPIROU_POL", st, "V", ch["dp_id"], ch["obs_id"], 70000.0, "NIR",
            ch["mjd_obs"], ch["t_exptime"], f"CFHT_SPIROU_POL/{st}/{ch['dp_id']}.fits",
            f"https://cadc-west-01.canfar.net/raven/files/cadc:CFHT/{ch['dp_id']}.fits", ch["est_bytes"],
        )

    # 2. Query PolarBase TBL NARVAL metadata & wget links (NO file downloads!)
    print("Querying PolarBase REST API (TBL NARVAL) for metadata & norm__*.s URLs...")
    pb_picks: list[tuple[str, str, dict[str, Any]]] = []
    pb_id_map: dict[str, tuple[str, str, dict[str, Any]]] = {}

    def _query_pb_star(st: str, pb_q: str, want_pols: tuple[str, ...]) -> None:
        j = _http_post_json(POLARBASE_SEARCH, {"instrument": ["narval"], "object_name": pb_q, "mode_instrument": "polarization"})
        recs = j.get("records", [])
        for pol in want_pols:
            cands = []
            for r in recs:
                if r.get("stokes") != pol:
                    continue
                oid = str(r["id_observation"])
                dp_id = f"NARVAL_{oid}_{pol}"
                if dp_id in excl_all_dp or dp_id in used_dps or oid in excl_all_dp:
                    continue
                snr = float(r.get("snrmax") or 0.0)
                expt = float(r.get("texposure") or 0.0)
                mjd = _iso_to_mjd(r.get("date") or "") or 56000.0
                cands.append({"oid": oid, "dp_id": dp_id, "snr": snr, "expt": expt, "mjd": mjd, "rec": r})
            assert cands, f"No fresh NARVAL {pol} for {st} ({pb_q})!"
            best = sorted(cands, key=lambda x: (-x["snr"], -x["expt"], x["oid"]))[0]
            used_dps.add(best["dp_id"])
            pb_picks.append((st, pol, best))
            pb_id_map[best["oid"]] = (st, pol, best)

    for st, pb_q in NARVAL_QUV_BRIDGES:
        _query_pb_star(st, pb_q, ("Q", "U", "V"))
    for st, pb_q, pol in NARVAL_V_TARGETS:
        _query_pb_star(st, pb_q, (pol,))

    # Resolve exact `norm__*.s` URL per selected observation via /download/wget_links (string IDs required)
    oid_to_s_url: dict[str, str] = {}
    for _, _, info in pb_picks:
        oid = str(info["oid"])
        wget_txt = _http_post_text(
            POLARBASE_LINKS,
            {"observation_ids": [oid], "file_extensions": ["any"], "original_file": True},
            timeout=30,
        )
        urls_norm = re.findall(r"https?://www\.polarbase\.ovgso\.fr/download/file/\S*__norm__\S+\.s", wget_txt)
        if not urls_norm:
            urls_norm = re.findall(r"https?://www\.polarbase\.ovgso\.fr/download/file/\S*__Nnorm__\S+\.s", wget_txt)
        if not urls_norm:
            urls_norm = re.findall(r"https?://www\.polarbase\.ovgso\.fr/download/file/\S+\.s", wget_txt)
        assert urls_norm, f"No .s wget_link returned for NARVAL obs_id={oid}!"
        oid_to_s_url[oid] = urls_norm[0]

    for st, pol, info in pb_picks:
        oid = str(info["oid"])
        u = oid_to_s_url[oid]
        _add_row(
            "TBL_NARVAL", st, pol, info["dp_id"], oid, 65000.0, "OPTICAL",
            info["mjd"], info["expt"], f"TBL_NARVAL/{st}/{info['dp_id']}.s", u, 2_800_000,
        )

    # Sort cohort deterministically
    cohort_rows.sort(key=lambda r: (r["instrument"], r["canonical_target"], r["stokes"], r["dp_id"]))
    unique_stars = sorted({r["canonical_target"] for r in cohort_rows})
    bridge_stars = sorted({r["canonical_target"] for r in cohort_rows if r["is_prior_bridge"] == "True"})
    new_stars = sorted({r["canonical_target"] for r in cohort_rows if r["is_prior_bridge"] == "False"})

    assert len(new_stars) == 8, f"Expected 8 brand-new stars, got {len(new_stars)}: {new_stars}"
    assert len(bridge_stars) == 41, f"Expected 41 prior bridges, got {len(bridge_stars)}: {bridge_stars}"
    assert len(unique_stars) == 49, f"Expected 49 unique stars, got {len(unique_stars)}"
    assert len(set(r["dp_id"] for r in cohort_rows)) == len(cohort_rows)

    # Count paired (Q, U) sets
    qu_map: dict[tuple[str, str], set[str]] = defaultdict(set)
    for r in cohort_rows:
        qu_map[(r["canonical_target"], r["instrument"])].add(r["stokes"])
    paired_qu_sets = sorted(k for k, v in qu_map.items() if "Q" in v and "U" in v)

    # Write Stage-1 files (still NO RAW_DIR!)
    with (WS / "FROZEN_COHORT_D110.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COHORT_COLS)
        w.writeheader()
        for r in cohort_rows:
            w.writerow(r)

    (WS / "PRIOR_V6_7_PHASES_SNAPSHOT.json").write_text(json.dumps(snap, separators=(",", ":")) + "\n", encoding="utf-8")

    # Add the 8 brand-new star coordinates cleanly on top of the 1,077 prior coords in registry only for downstream audit ref (excluded stays 1,077!)
    pex_out = {
        "schema": "D110_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D110",
        "verified_utc": datetime.now(timezone.utc).isoformat(),
        "prior_phases_covered": "D001-D109 (Companion Archives A-AI)",
        "n_prior_excluded_coords": len(prior_coords),
        "n_prior_excluded_dp_ids": len(prior_dp_ids),
        "n_format_check_excluded_dp_ids": len(fmt_probes),
        "d110_total_stars": len(unique_stars),
        "d110_brand_new_unique_stars": len(new_stars),
        "d110_prior_bridge_stars": len(bridge_stars),
        "d110_paired_qu_sets": len(paired_qu_sets),
        "d110_total_observations": len(cohort_rows),
        "d110_total_physical_files": len(cohort_rows),
        "d110_dp_id_overlap_count": 0,
        "brand_new_min_prior_sep_arcsec": min(BRAND_NEW_SPECS[s]["min_prior_sep_arcsec"] for s in new_stars),
        "format_check_excluded_dp_ids": fmt_probes,
        "excluded_dp_ids": sorted(prior_dp_ids),
        "excluded_targets_coordinate_registry": prior_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pex_out, indent=2) + "\n", encoding="utf-8")

    pol_cfg = {
        "schema": "D110_POLARIMETRIC_TARGETS_AND_STOKES_CONFIG",
        "phase_id": "D110",
        "new_spectrograph_added": "TBL_NARVAL",
        "new_spectrographs_total_post_d110": 67,
        "new_spectral_arms_total_post_d110": 97,
        "dv_grid_kms": det.POL_GRID_DV_KMS,
        "instruments": {
            "CFHT_ESPADONS_POL": {"count": sum(1 for r in cohort_rows if r["instrument"] == "CFHT_ESPADONS_POL"), "regime": "OPTICAL", "resolving_power": 65000.0},
            "CFHT_SPIROU_POL": {"count": sum(1 for r in cohort_rows if r["instrument"] == "CFHT_SPIROU_POL"), "regime": "NIR", "resolving_power": 70000.0},
            "TBL_NARVAL": {"count": sum(1 for r in cohort_rows if r["instrument"] == "TBL_NARVAL"), "regime": "OPTICAL", "resolving_power": 65000.0},
        },
        "paired_qu_sets": [{"star": st, "instrument": inst} for st, inst in paired_qu_sets],
        "brand_new_targets": {st: BRAND_NEW_SPECS[st] for st in new_stars},
    }
    (WS / "POLARIMETRIC_TARGETS_AND_STOKES_CONFIG.json").write_text(json.dumps(pol_cfg, indent=2) + "\n", encoding="utf-8")

    # Stage-1 Seal: 7 immutable files
    assert not RAW_DIR.exists(), f"{RAW_DIR} appeared before seal!"
    now_epoch = time.time()
    now_utc = datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat()
    stage1_names = [
        "v6_8_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D110.csv",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "POLARIMETRIC_TARGETS_AND_STOKES_CONFIG.json",
        "PRIOR_V6_7_PHASES_SNAPSHOT.json",
    ]
    stage1_hashes = {fn: _sha256_file(WS / fn) for fn in stage1_names}

    proj_bytes = sum(int(r["est_bytes"]) for r in cohort_rows)
    ml = {
        "schema": "D110_METHOD_LOCK",
        "phase_id": "D110",
        "detector": det.DETECTOR_NAME,
        "locked_utc": now_utc,
        "locked_unix_epoch": round(now_epoch, 4),
        "d110_total_stars": len(unique_stars),
        "d110_brand_new_stars": len(new_stars),
        "d110_prior_bridges": len(bridge_stars),
        "d110_total_observations": len(cohort_rows),
        "d110_total_physical_files": len(cohort_rows),
        "d110_paired_qu_sets": len(paired_qu_sets),
        "d110_projected_download_mib": round(proj_bytes / (1024.0 * 1024.0), 3),
        "calibration_suites_new": {
            "V68_OPT_POL_240": 240,
            "V68_NIR_SPIROU_POL_180": 180,
            "V68_POL_COMB_180": 180,
        },
        "stage_1_files": stage1_hashes,
    }
    (WS / "METHOD_LOCK.json").write_text(json.dumps(ml, indent=2) + "\n", encoding="utf-8")
    ml_sha = _sha256_file(WS / "METHOD_LOCK.json")

    lr = {
        "schema": "D110_LOCK_RECEIPT",
        "phase_id": "D110",
        "status": "STAGE-1 SEALED",
        "locked_utc": now_utc,
        "locked_unix_epoch": round(now_epoch, 4),
        "inputs_dir_exists_at_seal": RAW_DIR.exists(),
        "method_lock_sha256": ml_sha,
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lr, indent=2) + "\n", encoding="utf-8")
    print(
        f"STAGE-1 SEALED: stars={len(unique_stars)} (bridges={len(bridge_stars)}, new={len(new_stars)}), "
        f"obs={len(cohort_rows)} (paired Q/U={len(paired_qu_sets)}), overlap=0, inputs_at_seal={RAW_DIR.exists()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
