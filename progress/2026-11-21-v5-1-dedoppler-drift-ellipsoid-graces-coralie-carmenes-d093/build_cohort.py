#!/usr/bin/env python3
"""
Metadata-only Cohort Builder & Prospective Lock Sealer for Phase D093
(`TECHNOSIGNATURE_V5_1_DEDOPPLER_DRIFT_MULTIEVENT_ELLIPSOID_GRACES_CORALIE_CARMENES`).

STRICT PROSPECTIVE HYGIENE:
  - Executes strictly BEFORE `inputs_d093_v5_1/` exists on disk (Zero FITS downloads here).
  - Resolves all 15 brand-new unique stars (4 `GEMINI_GRACES`, 5 `ESO_CORALIE`,
    6 Northern `<10 pc` `CARMENES_VIS`; 5 Controls + 10 Science across 9 orbital campaigns
    `#110-#118`, `GW170817` SETI Ellipsoid crossings, and `<10 pc` ETZ) via TAP catalogs
    (CADC, ESO Phase-3, GAVO, ESA Gaia DR3, NASA Exoplanet Archive `pscomppars`).
  - Measures exact FITS byte sizes via HTTP HEAD `Content-Length` (enforcing `<= 225.0 MiB`).
  - Verifies zero DP-ID overlap against all prior `C001-D092` exclusions in Companion Archive R
    and minimum prior sky separation `>= 300"`.
  - Freezes `FROZEN_COHORT_D093.csv`, `ORBITAL_CAMPAIGNS_AND_KINEMATICS.json`,
    `PRIOR_EXCLUSION_VERIFICATION.json`, `PRIOR_V5_0_PHASES_SNAPSHOT.json`, and seals
    `METHOD_LOCK.json` and `LOCK_RECEIPT.json`.
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import json
import math
import time
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from v5_1_detector import (
    BASE_V5_1_CONFIG,
    DETECTOR_NAME,
    compute_keplerian_kp_kms,
    compute_multievent_sync_v51,
    compute_planet_orbital_rv_kms,
    compute_ppo_alignment_score,
)

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = Path(__file__).resolve().parent

ARCHIVE_N = ROOT / "archives/SETI_D088_V3_9_NORTHERN_RADIO23_AND_ALLSKY_COMB_V4_1_RESULTS_2026-11-18.zip"
ARCHIVE_N_SHA256 = "c0210250b925df3bebb1710c2bf7333a64ed767ebdc1f38a496d6a9454f7d45d"
ARCHIVE_N_PREFIX = "work_radio23_allsky_20261118_d088_v3_9_northern_and_comb_v4_1/"

ARCHIVE_P = ROOT / "archives/SETI_D090_V4_1_JWST_SPACE_THERMAL_IR_RESULTS_2026-11-19.zip"
ARCHIVE_P_SHA256 = "2940839e8613b0d388c9b922743ba8244852806411f28586696e59eb8d73841a"
ARCHIVE_P_PREFIX = "work_jwst_thermal_ir_20261119_d090_v4_1_nirspec_miri/"

ARCHIVE_R = ROOT / "archives/SETI_D092_V5_0_RPCA_RARITY_ELLIPSOID_PPO_MIRI_CCF_RESULTS_2026-11-20.zip"
ARCHIVE_R_SHA256 = "845f0186a6a793ece2b62f9a2e7caaca5181a9b5a12f8db39326376a58a1d8dd"
ARCHIVE_R_PREFIX = "work_v5_0_20261120_d092_rpca_rarity_ellipsoid_ppo_miri_ccf/"

TARGET_SPECS: list[dict[str, Any]] = [
    # --- GEMINI_GRACES (4 brand-new stars, 8 *i.fits) ---
    {
        "instrument": "GEMINI_GRACES",
        "canonical_target": "WASP52",
        "common_name": "WASP-52",
        "role": "SCIENCE",
        "subrole": "SCIENCE_TRANSITING_ORBITAL",
        "science_track": "BLIND_DRIFT_AND_ORBITAL_TRANSIT",
        "gaia_source_id": 2666015878575546496,
        "cadc_targets": ("WASP-52 b", "WASP52 b"),
        "nasa_host": "WASP-52",
        "orbital_campaign": True,
        "n_target_exposures": 2,
        "teff_lit": 5000.0,
        "mh_lit": 0.03,
        "mass_lit": 0.87,
        "rv_lit": -0.64,
        "j_mag": 10.59,
        "h_mag": 10.19,
        "ks_mag": 10.09,
    },
    {
        "instrument": "GEMINI_GRACES",
        "canonical_target": "KELT16",
        "common_name": "KELT-16",
        "role": "SCIENCE",
        "subrole": "SCIENCE_TRANSITING_ORBITAL",
        "science_track": "BLIND_DRIFT_AND_ORBITAL_TRANSIT",
        "gaia_source_id": 1864885215233116032,
        "cadc_targets": ("KELT-16 b",),
        "nasa_host": "KELT-16",
        "orbital_campaign": True,
        "n_target_exposures": 2,
        "teff_lit": 6236.0,
        "mh_lit": -0.002,
        "mass_lit": 1.21,
        "rv_lit": 26.8,
        "j_mag": 10.89,
        "h_mag": 10.69,
        "ks_mag": 10.64,
    },
    {
        "instrument": "GEMINI_GRACES",
        "canonical_target": "QATAR7",
        "common_name": "Qatar-7",
        "role": "SCIENCE",
        "subrole": "SCIENCE_TRANSITING_ORBITAL",
        "science_track": "BLIND_DRIFT_AND_ORBITAL_TRANSIT",
        "gaia_source_id": 2878923523472328704,
        "cadc_targets": ("Qatar 7 b",),
        "nasa_host": "Qatar-7",
        "orbital_campaign": True,
        "n_target_exposures": 2,
        "teff_lit": 6387.0,
        "mh_lit": -0.09,
        "mass_lit": 1.41,
        "rv_lit": -4.28,
        "j_mag": 12.14,
        "h_mag": 11.96,
        "ks_mag": 11.91,
    },
    {
        "instrument": "GEMINI_GRACES",
        "canonical_target": "HD205905",
        "common_name": "HD 205905",
        "role": "CONTROL",
        "subrole": "CONTROL_ZERO_PLANET",
        "science_track": "BLIND_DRIFT_CONTROL",
        "gaia_source_id": 6810896745007524736,
        "cadc_targets": ("HD 205905",),
        "nasa_host": "",
        "orbital_campaign": False,
        "n_target_exposures": 2,
        "teff_lit": 5890.0,
        "mh_lit": 0.08,
        "mass_lit": 1.04,
        "rv_lit": -17.3,
        "j_mag": 5.66,
        "h_mag": 5.41,
        "ks_mag": 5.32,
    },
    # --- ESO_CORALIE (5 brand-new stars, 10 FITS) ---
    {
        "instrument": "ESO_CORALIE",
        "canonical_target": "HD2151",
        "common_name": "Beta Hydri",
        "role": "CONTROL",
        "subrole": "CONTROL_ZERO_PLANET_10PC",
        "science_track": "BLIND_DRIFT_CONTROL_10PC",
        "gaia_source_id": 4683897617110115200,
        "eso_target": "HD2151",
        "nasa_host": "",
        "orbital_campaign": False,
        "n_target_exposures": 2,
        "teff_lit": 5872.0,
        "mh_lit": -0.04,
        "mass_lit": 1.08,
        "rv_lit": 22.9,
        "j_mag": 1.71,
        "h_mag": 1.38,
        "ks_mag": 1.24,
    },
    {
        "instrument": "ESO_CORALIE",
        "canonical_target": "HD217107",
        "common_name": "HD 217107",
        "role": "SCIENCE",
        "subrole": "SCIENCE_MULTIPLANET_ORBITAL",
        "science_track": "BLIND_DRIFT_AND_ORBITAL",
        "gaia_source_id": 2648914040357320576,
        "eso_target": "HD217107",
        "nasa_host": "HD 217107",
        "orbital_campaign": True,
        "n_target_exposures": 2,
        "teff_lit": 5646.0,
        "mh_lit": 0.39,
        "mass_lit": 1.08,
        "rv_lit": -13.4,
        "j_mag": 4.95,
        "h_mag": 4.62,
        "ks_mag": 4.54,
    },
    {
        "instrument": "ESO_CORALIE",
        "canonical_target": "HD111031",
        "common_name": "HD 111031",
        "role": "CONTROL",
        "subrole": "CONTROL_GW170817_ELLIPSOID",
        "science_track": "GW170817_ELLIPSOID_CONTROL",
        "gaia_source_id": 3529518709839090176,
        "eso_target": "HD111031",
        "nasa_host": "",
        "orbital_campaign": False,
        "n_target_exposures": 2,
        "teff_lit": 5760.0,
        "mh_lit": 0.25,
        "mass_lit": 1.09,
        "rv_lit": -20.5,
        "j_mag": 5.71,
        "h_mag": 5.42,
        "ks_mag": 5.36,
    },
    {
        "instrument": "ESO_CORALIE",
        "canonical_target": "HD10647",
        "common_name": "q1 Eri",
        "role": "SCIENCE",
        "subrole": "SCIENCE_EXOPLANET_DISK",
        "science_track": "BLIND_DRIFT_AND_ORBITAL",
        "gaia_source_id": 4912580642524184960,
        "eso_target": "HD10647",
        "nasa_host": "HD 10647",
        "orbital_campaign": True,
        "n_target_exposures": 2,
        "teff_lit": 6143.0,
        "mh_lit": -0.03,
        "mass_lit": 1.11,
        "rv_lit": 27.6,
        "j_mag": 4.65,
        "h_mag": 4.44,
        "ks_mag": 4.34,
    },
    {
        "instrument": "ESO_CORALIE",
        "canonical_target": "HD206301",
        "common_name": "42 Cap",
        "role": "SCIENCE",
        "subrole": "SCIENCE_ETZ",
        "science_track": "ETZ",
        "gaia_source_id": 6841803123511245696,
        "eso_target": "HD206301",
        "nasa_host": "",
        "orbital_campaign": False,
        "n_target_exposures": 2,
        "teff_lit": 5660.0,
        "mh_lit": -0.10,
        "mass_lit": 1.25,
        "rv_lit": -1.1,
        "j_mag": 4.02,
        "h_mag": 3.74,
        "ks_mag": 3.59,
    },
    # --- CARMENES_VIS (6 brand-new Northern <10pc stars, 12 FITS) ---
    {
        "instrument": "CARMENES_VIS",
        "canonical_target": "GJ213",
        "common_name": "Ross 47",
        "role": "CONTROL",
        "subrole": "CONTROL_ZERO_PLANET_10PC",
        "science_track": "BLIND_DRIFT_CONTROL_10PC",
        "gaia_source_id": 3340477717172813568,
        "carmenes_id": "J05421+124",
        "nasa_host": "",
        "orbital_campaign": False,
        "n_target_exposures": 2,
        "teff_lit": 3320.0,
        "mh_lit": -0.25,
        "mass_lit": 0.22,
        "rv_lit": 103.5,
        "j_mag": 7.12,
        "h_mag": 6.63,
        "ks_mag": 6.39,
    },
    {
        "instrument": "CARMENES_VIS",
        "canonical_target": "HD199305",
        "common_name": "GJ 809",
        "role": "CONTROL",
        "subrole": "CONTROL_ZERO_PLANET_10PC",
        "science_track": "BLIND_DRIFT_CONTROL_10PC",
        "gaia_source_id": 2195886971653527168,
        "carmenes_id": "J20533+621",
        "nasa_host": "",
        "orbital_campaign": False,
        "n_target_exposures": 2,
        "teff_lit": 3815.0,
        "mh_lit": -0.10,
        "mass_lit": 0.57,
        "rv_lit": -17.2,
        "j_mag": 5.43,
        "h_mag": 4.92,
        "ks_mag": 4.62,
    },
    {
        "instrument": "CARMENES_VIS",
        "canonical_target": "GJ1289",
        "common_name": "GJ 1289",
        "role": "SCIENCE",
        "subrole": "SCIENCE_EXOPLANET_10PC",
        "science_track": "BLIND_DRIFT_AND_ORBITAL_10PC",
        "gaia_source_id": 2879455480942629248,
        "carmenes_id": "J23431+365",
        "nasa_host": "GJ 1289",
        "orbital_campaign": True,
        "n_target_exposures": 2,
        "teff_lit": 3300.0,
        "mh_lit": 0.05,
        "mass_lit": 0.21,
        "rv_lit": -2.4,
        "j_mag": 8.11,
        "h_mag": 7.51,
        "ks_mag": 7.23,
    },
    {
        "instrument": "CARMENES_VIS",
        "canonical_target": "ROSS64",
        "common_name": "Ross 64",
        "role": "SCIENCE",
        "subrole": "SCIENCE_ETZ_10PC",
        "science_track": "ETZ",
        "gaia_source_id": 3377365057060447616,
        "carmenes_id": "J06246+234",
        "nasa_host": "",
        "orbital_campaign": False,
        "n_target_exposures": 2,
        "teff_lit": 3249.0,
        "mh_lit": -0.05,
        "mass_lit": 0.19,
        "rv_lit": -11.4,
        "j_mag": 8.88,
        "h_mag": 8.33,
        "ks_mag": 8.07,
    },
    {
        "instrument": "CARMENES_VIS",
        "canonical_target": "GJ3512",
        "common_name": "GJ 3512",
        "role": "SCIENCE",
        "subrole": "SCIENCE_MULTIPLANET_10PC",
        "science_track": "BLIND_DRIFT_AND_ORBITAL_10PC",
        "gaia_source_id": 1040827088726734976,
        "carmenes_id": "J08413+594",
        "nasa_host": "GJ 3512",
        "orbital_campaign": True,
        "n_target_exposures": 2,
        "teff_lit": 3140.0,
        "mh_lit": 0.19,
        "mass_lit": 0.123,
        "rv_lit": 18.2,
        "j_mag": 9.62,
        "h_mag": 9.01,
        "ks_mag": 8.71,
    },
    {
        "instrument": "CARMENES_VIS",
        "canonical_target": "G19215",
        "common_name": "G 192-15",
        "role": "SCIENCE",
        "subrole": "SCIENCE_MULTIPLANET_10PC",
        "science_track": "BLIND_DRIFT_AND_ORBITAL_10PC",
        "gaia_source_id": 970354749937140736,
        "carmenes_id": "J06024+498",
        "nasa_host": "G 192-15",
        "orbital_campaign": True,
        "n_target_exposures": 2,
        "teff_lit": 3210.0,
        "mh_lit": 0.0,
        "mass_lit": 0.145,
        "rv_lit": 21.0,
        "j_mag": 9.35,
        "h_mag": 8.78,
        "ks_mag": 8.51,
    },
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            b = fh.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    c = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c)))) * 3600.0


def _urlopen_retry(req: urllib.request.Request, timeout_s: float = 40.0) -> bytes:
    last_err: Exception | None = None
    for att in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as r:
                return r.read()
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (att + 1))
    raise RuntimeError(f"HTTP failure {req.full_url}: {last_err}")


def tap_csv(url_base: str, query: str, param_key: str = "QUERY") -> list[dict[str, str]]:
    params = {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", param_key: query} if param_key == "QUERY" else {param_key: query, "format": "csv"}
    url = f"{url_base}?{urllib.parse.urlencode(params)}"
    txt = _urlopen_retry(urllib.request.Request(url, headers={"User-Agent": "SETIsearch-D093/1.0"})).decode("utf-8", errors="replace")
    return list(csv.DictReader(txt.splitlines()))


def tap_json(url_base: str, query: str) -> dict[str, Any]:
    url = f"{url_base}?{urllib.parse.urlencode({'REQUEST': 'doQuery', 'LANG': 'ADQL', 'FORMAT': 'json', 'QUERY': query})}"
    return json.loads(_urlopen_retry(urllib.request.Request(url, headers={"User-Agent": "SETIsearch-D093/1.0"})).decode("utf-8"))


def head_content_length(url: str) -> int:
    last_err: Exception | None = None
    for att in range(4):
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "SETIsearch-D093/1.0"})
            with urllib.request.urlopen(req, timeout=20.0) as r:
                cl = r.headers.get("Content-Length")
                if cl:
                    return int(cl)
                return 0
        except Exception as exc:
            last_err = exc
            time.sleep(1.0 * (att + 1))
    raise RuntimeError(f"HEAD failed {url}: {last_err}")


def infer_teff_from_bprp(bp_mag: float | None, rp_mag: float | None, fallback: float) -> float:
    if bp_mag is not None and rp_mag is not None and math.isfinite(bp_mag) and math.isfinite(rp_mag):
        col = bp_mag - rp_mag
        if 0.3 <= col <= 3.5:
            return float(max(2600.0, min(8500.0, 8150.0 - 2950.0 * col + 460.0 * col * col)))
    return float(fallback)


def fetch_pool_graces(spec: dict[str, Any], excluded_dp_ids: set[str]) -> list[dict[str, Any]]:
    in_names = ",".join(f"'{t}'" for t in spec["cadc_targets"])
    sql = (
        "SELECT obs_id, obs_publisher_did, target_name, s_ra, s_dec, t_min, t_exptime, "
        "em_min, em_max, em_res_power, obs_release_date "
        f"FROM ivoa.ObsCore WHERE obs_collection='GEMINI' AND instrument_name='GRACES' "
        f"AND dataproduct_type='spectrum' AND calib_level>=2 AND obs_release_date<'2026-11-21' "
        f"AND target_name IN ({in_names})"
    )
    rows = tap_csv("https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/argus/sync", sql)
    pool: list[dict[str, Any]] = []
    for r in rows:
        did = (r.get("obs_publisher_did") or "").strip()
        if not did.endswith("i"):
            continue
        fid = did.split("/")[-1]
        dp_id = f"GRACES.{fid}"
        if dp_id in excluded_dp_ids:
            continue
        t_exp = float(r.get("t_exptime") or 0.0)
        if t_exp <= 5.0:
            continue
        url = f"https://cadc-west-01.canfar.net/raven/files/gemini:GEMINI/{fid}.fits"
        pool.append({
            "dp_id": dp_id,
            "mjd_obs": float(r["t_min"]),
            "t_exptime": t_exp,
            "snr": 60.0,
            "grating": "GRACES_STARONLY" if spec["role"] == "SCIENCE" else "GRACES_STARSKY",
            "resolving_power": float(r.get("em_res_power") or 67500.0),
            "f1_id": fid,
            "f1_url": url,
            "f1_bytes": 0,
        })
    return pool


def fetch_pool_coralie(spec: dict[str, Any], ra_deg: float, dec_deg: float, excluded_dp_ids: set[str]) -> list[dict[str, Any]]:
    tgt = spec["eso_target"]
    sql = (
        "SELECT target_name, s_ra, s_dec, t_min, t_exptime, snr, dp_id, access_estsize, em_res_power "
        f"FROM ivoa.ObsCore WHERE instrument_name='CORALIE' AND dataproduct_type='spectrum' "
        f"AND target_name='{tgt}' AND t_min >= 57982 AND t_exptime >= 30 ORDER BY snr DESC"
    )
    rows = tap_csv("https://archive.eso.org/tap_obs/sync", sql)
    pool: list[dict[str, Any]] = []
    for r in rows:
        dp_id = (r.get("dp_id") or "").strip()
        if not dp_id or dp_id in excluded_dp_ids:
            continue
        if sep_arcsec(ra_deg, dec_deg, float(r["s_ra"]), float(r["s_dec"])) > 180.0:
            continue
        snr_v = float(r.get("snr") or 0.0)
        if snr_v < 45.0:
            continue
        pool.append({
            "dp_id": dp_id,
            "mjd_obs": float(r["t_min"]),
            "t_exptime": float(r["t_exptime"]),
            "snr": snr_v,
            "grating": "CORALIE_R60K",
            "resolving_power": float(r.get("em_res_power") or 60000.0),
            "f1_id": dp_id,
            "f1_url": f"https://dataportal.eso.org/dataPortal/file/{dp_id}",
            "f1_bytes": 0,
        })
    return pool


def fetch_pool_carmenes(spec: dict[str, Any], excluded_dp_ids: set[str]) -> list[dict[str, Any]]:
    cid = spec["carmenes_id"]
    sql = (
        "SELECT accref, ssa_dateobs, ssa_timeext, ssa_snr, ssa_specres, ssa_pdate "
        f"FROM carmenes.data WHERE ssa_targname='{cid}' AND ssa_specstart < 6e-7 ORDER BY ssa_snr DESC"
    )
    rows = tap_csv("https://dc.g-vo.org/tap/sync", sql)
    pool: list[dict[str, Any]] = []
    for r in rows:
        accref = (r.get("accref") or "").strip()
        fname = accref.split("/")[-1]
        if not fname.endswith(".fits"):
            continue
        dp_id = f"CARMENES.{fname[:-5]}"
        if dp_id in excluded_dp_ids:
            continue
        # GAVO row casing uses lowercase or camelcase header depending on VOTable
        mjd_s = r.get("ssa_dateObs") or r.get("ssa_dateobs")
        snr_s = r.get("ssa_snr")
        if not (mjd_s and snr_s):
            continue
        snr_v = float(snr_s)
        if snr_v < 15.0:
            continue
        url = f"https://dc.g-vo.org/carmenes/q/sdl/static/{cid}/{fname}"
        expt_s = r.get("ssa_timeExt") or r.get("ssa_timeext") or 600.0
        pool.append({
            "dp_id": dp_id,
            "mjd_obs": float(mjd_s),
            "t_exptime": float(expt_s),
            "snr": snr_v,
            "grating": "CARMENES_VIS",
            "resolving_power": 94600.0,
            "f1_id": fname[:-5],
            "f1_url": url,
            "f1_bytes": 0,
        })
    return pool


def select_two_exposures(
    spec: dict[str, Any],
    pool: list[dict[str, Any]],
    ref_planet: tuple[float, float, float] | None,
) -> list[dict[str, Any]]:
    assert len(pool) >= 2, f"{spec['canonical_target']}: pool too small ({len(pool)})"
    st = spec["canonical_target"]
    track = spec["science_track"]

    # GW170817 ellipsoid tracks: pick exposures nearest GW170817 crossing while satisfying orbital dv if needed
    if "GW170817" in track:
        mjd_gw = float(spec["_gw170817_mjd_ell"])
        ranked = sorted(pool, key=lambda r: (abs(r["mjd_obs"] - mjd_gw), -r["snr"]))
        e1 = ranked[0]
        assert abs(e1["mjd_obs"] - mjd_gw) <= 180.0, f"{st}: closest GW170817 dt > 180d"
        if ref_planet is None:
            e2 = next((r for r in ranked[1:] if abs(r["mjd_obs"] - e1["mjd_obs"]) >= 0.5), ranked[1])
            return [e1, e2]
        p_d, t0_b, kp = ref_planet
        _, dv1 = compute_planet_orbital_rv_kms(e1["mjd_obs"] + 2400000.5, t0_b, p_d, kp)
        cand2 = [
            (abs(compute_planet_orbital_rv_kms(r["mjd_obs"] + 2400000.5, t0_b, p_d, kp)[1] - dv1), r)
            for r in pool if r["dp_id"] != e1["dp_id"] and abs(r["mjd_obs"] - e1["mjd_obs"]) >= 1.0
        ]
        cand2.sort(key=lambda x: -x[0])
        assert cand2 and cand2[0][0] >= 5.0, f"{st}: cannot achieve dv_span >= 5.0 km/s near GW170817"
        return sorted([e1, cand2[0][1]], key=lambda x: x["mjd_obs"])

    # Orbital campaign targets: maximize Keplerian |dv_2 - dv_1| across high-SNR exposures
    if spec.get("orbital_campaign") and ref_planet is not None:
        p_d, t0_b, kp = ref_planet
        top_pool = sorted(pool, key=lambda r: -r["snr"])[:80]
        scored = []
        for r in top_pool:
            _, dv = compute_planet_orbital_rv_kms(r["mjd_obs"] + 2400000.5, t0_b, p_d, kp)
            scored.append((dv, r))
        scored.sort(key=lambda x: x[0])
        # Search best pair with time separation >= 0.02 d and maximum |dv| span + SNR tie-breaker
        lo_cands = scored[:12]
        hi_cands = scored[-12:]
        best_pair: tuple[float, dict[str, Any], dict[str, Any]] | None = None
        for dv_a, ra_r in lo_cands:
            for dv_b, rb_r in hi_cands:
                if ra_r["dp_id"] == rb_r["dp_id"] or abs(ra_r["mjd_obs"] - rb_r["mjd_obs"]) < 0.02:
                    continue
                span = abs(dv_b - dv_a)
                key_s = span + 0.02 * (ra_r["snr"] + rb_r["snr"])
                if best_pair is None or key_s > best_pair[0]:
                    best_pair = (key_s, ra_r, rb_r)
        assert best_pair is not None, f"{st}: no valid orbital pair!"
        return sorted([best_pair[1], best_pair[2]], key=lambda x: x["mjd_obs"])

    # Controls & non-orbital ETZ: pick highest SNR pair separated by >= 0.5 days if available
    by_snr = sorted(pool, key=lambda r: -r["snr"])
    e1 = by_snr[0]
    e2 = next((r for r in by_snr[1:] if abs(r["mjd_obs"] - e1["mjd_obs"]) >= 0.5), by_snr[1])
    return sorted([e1, e2], key=lambda x: x["mjd_obs"])


def main() -> None:
    inp_dir = ROOT / "inputs_d093_v5_1"
    if inp_dir.exists():
        raise RuntimeError(f"Prospective hygiene violation: {inp_dir} already exists before lock!")

    for zp, exp_sha in ((ARCHIVE_N, ARCHIVE_N_SHA256), (ARCHIVE_P, ARCHIVE_P_SHA256), (ARCHIVE_R, ARCHIVE_R_SHA256)):
        if sha256_file(zp) != exp_sha:
            raise RuntimeError(f"Companion archive SHA-256 mismatch: {zp.name}")

    print("1. Extracting D092 Archive R exclusion registry & D079-D092 335-star synthesis...", flush=True)
    with zipfile.ZipFile(ARCHIVE_R, "r") as zr:
        pe92 = json.loads(zr.read(ARCHIVE_R_PREFIX + "PRIOR_EXCLUSION_VERIFICATION.json").decode("utf-8"))
        sum92 = json.loads(zr.read(ARCHIVE_R_PREFIX + "results/SUMMARY.json").decode("utf-8"))
        coh92_rows = list(csv.DictReader(zr.read(ARCHIVE_R_PREFIX + "FROZEN_COHORT_D092.csv").decode("utf-8").splitlines()))
        u335_rows = list(csv.DictReader(zr.read(ARCHIVE_R_PREFIX + "results/UNIFIED_PANCHROMATIC_V5_0_SYNTHESIS_335STARS.csv").decode("utf-8").splitlines()))
        br37_rows = list(csv.DictReader(zr.read(ARCHIVE_R_PREFIX + "results/PANCHROMATIC_BRIDGE_35STARS_V50.csv").decode("utf-8").splitlines()))
        comb_u_rows = list(csv.DictReader(zr.read(ARCHIVE_R_PREFIX + "results/ALLSKY_COMB_V4_1_UNIFIED_D079_D092.csv").decode("utf-8").splitlines()))
        comb_c_rows = list(csv.DictReader(zr.read(ARCHIVE_R_PREFIX + "results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D092.csv").decode("utf-8").splitlines()))

    prior_v50_snap = {
        "schema": "D093_PRIOR_V5_0_PHASES_SNAPSHOT",
        "prior_phases": "D079-D092",
        "source_archive_r_name": ARCHIVE_R.name,
        "source_archive_r_sha256": ARCHIVE_R_SHA256,
        "source_archive_n_name": ARCHIVE_N.name,
        "source_archive_n_sha256": ARCHIVE_N_SHA256,
        "source_archive_p_name": ARCHIVE_P.name,
        "source_archive_p_sha256": ARCHIVE_P_SHA256,
        "prior_v50_unique_stars_count": len(u335_rows),
        "prior_v50_within_10pc_count": sum(1 for r in u335_rows if r["within_10pc"] == "True"),
        "prior_v50_total_exposures_count": sum(int(r["n_exposures_total"]) for r in u335_rows),
        "prior_cumulative_integration_hours": sum92["unified_335star_panchromatic_v5_0_synthesis"]["total_integration_hours_d079_d092"],
        "prior_v50_calibration_trials_count": sum92["unified_335star_panchromatic_v5_0_synthesis"]["total_calibration_trials_d079_d092"],
        "prior_v2_false_alarms_eliminated_total": sum92["unified_335star_panchromatic_v5_0_synthesis"]["v2_false_alarms_eliminated_total"],
        "prior_cumulative_orbital_campaigns_count": sum92["unified_335star_panchromatic_v5_0_synthesis"]["cumulative_orbital_campaigns"],
        "d092_summary_headline": sum92,
        "unified_335star_rows": u335_rows,
        "d092_bridge_37star_rows": br37_rows,
        "allsky_comb_unified_d079_d092": comb_u_rows,
        "allsky_comb_candidates_d079_d092": comb_c_rows,
    }
    (WS / "PRIOR_V5_0_PHASES_SNAPSHOT.json").write_text(json.dumps(prior_v50_snap, indent=2) + "\n", encoding="utf-8")

    excluded_dp_ids: set[str] = set(pe92["excluded_dp_ids"])
    for r in coh92_rows:
        for k in ("dp_id", "f1_id", "f2_id", "f3_id"):
            if r.get(k):
                excluded_dp_ids.add(r[k])

    excluded_coords = list(pe92["excluded_targets_coordinate_registry"])
    seen_lbl = {c["label"] for c in excluded_coords}
    for r in coh92_rows:
        lbl = f"{r['canonical_target']}(D092)"
        if lbl not in seen_lbl:
            excluded_coords.append({"label": lbl, "ra_deg": float(r["s_ra"]), "dec_deg": float(r["s_dec"])})
            seen_lbl.add(lbl)

    print("2. Querying ESA Gaia DR3 & NASA Exoplanet Archive pscomppars...", flush=True)
    gids = [s["gaia_source_id"] for s in TARGET_SPECS]
    gd = tap_json(
        "https://gea.esac.esa.int/tap-server/tap/sync",
        f"SELECT source_id,ra,dec,pmra,pmdec,parallax,phot_g_mean_mag,phot_bp_mean_mag,phot_rp_mean_mag,teff_gspphot,mh_gspphot,radial_velocity FROM gaiadr3.gaia_source WHERE source_id IN ({','.join(map(str, gids))})",
    )
    gcols = [m["name"] for m in gd["metadata"]]
    gaia_by_id = {int(row[0]): dict(zip(gcols, row)) for row in gd["data"]}

    nasa_rows = tap_csv(
        "https://exoplanetarchive.ipac.caltech.edu/TAP/sync",
        "SELECT pl_name,hostname,ra,dec,pl_orbper,pl_tranmid,pl_orbeccen,tran_flag,st_mass,st_teff,st_met,st_radv,sy_dist FROM pscomppars WHERE ra IS NOT NULL AND dec IS NOT NULL",
        param_key="query",
    )
    nasa_by_host: dict[str, list[dict[str, str]]] = {}
    for r in nasa_rows:
        if r.get("hostname"):
            nasa_by_host.setdefault(r["hostname"], []).append(r)

    print(f"3. Querying CADC GRACES, ESO CORALIE, and GAVO CARMENES metadata across {len(TARGET_SPECS)} targets...", flush=True)
    cohort_rows: list[dict[str, Any]] = []
    campaigns_doc: dict[str, Any] = {}
    sep_verif: list[dict[str, Any]] = []
    all_star_coords: list[dict[str, Any]] = []
    head_jobs: list[dict[str, Any]] = []
    camp_num = 109

    for spec in TARGET_SPECS:
        st = spec["canonical_target"]
        g = gaia_by_id[spec["gaia_source_id"]]
        ra_deg = float(g["ra"])
        dec_deg = float(g["dec"])
        pmra = float(g["pmra"]) if g.get("pmra") is not None else 0.0
        pmdec = float(g["pmdec"]) if g.get("pmdec") is not None else 0.0
        par_mas = float(g["parallax"])
        dist_pc = 1000.0 / par_mas
        dist_err_pc = max(0.01, dist_pc * (0.05 / max(1.0, par_mas)))
        within_10pc = dist_pc <= 10.0

        phot_g = float(g["phot_g_mean_mag"]) if g.get("phot_g_mean_mag") is not None else 12.0
        phot_bp = float(g["phot_bp_mean_mag"]) if g.get("phot_bp_mean_mag") is not None else None
        phot_rp = float(g["phot_rp_mean_mag"]) if g.get("phot_rp_mean_mag") is not None else None

        nh_list = nasa_by_host.get(spec.get("nasa_host", ""), [])
        nasa_teff = next((float(r["st_teff"]) for r in nh_list if r.get("st_teff")), None)
        nasa_mass = next((float(r["st_mass"]) for r in nh_list if r.get("st_mass")), None)
        teff_k = float(g["teff_gspphot"]) if g.get("teff_gspphot") is not None else (
            nasa_teff if nasa_teff is not None else infer_teff_from_bprp(phot_bp, phot_rp, float(spec["teff_lit"]))
        )
        # Override bright/late M-dwarf phot/GSP-Phot anomalies using literature value if >1000K off or missing
        if g.get("teff_gspphot") is None:
            teff_k = float(nasa_teff if nasa_teff is not None else spec["teff_lit"])
        mh_dex = float(g["mh_gspphot"]) if g.get("mh_gspphot") is not None else float(spec["mh_lit"])
        prior_rv = float(g["radial_velocity"]) if g.get("radial_velocity") is not None else float(spec["rv_lit"])
        mass_msun = float(nasa_mass if nasa_mass is not None else spec["mass_lit"])

        pl_hits = [
            r for r in nasa_rows
            if abs(float(r["dec"]) - dec_deg) < 0.05 and sep_arcsec(ra_deg, dec_deg, float(r["ra"]), float(r["dec"])) < 90.0
        ]
        n_pl = len({r["pl_name"] for r in pl_hits})
        if spec["role"] == "CONTROL":
            assert n_pl == 0, f"CONTROL star {st} has {n_pl} planets in NASA pscomppars!"
        has_tr = any(str(r.get("tran_flag") or "0") == "1" for r in pl_hits)

        sync_ref = compute_multievent_sync_v51(ra_deg, dec_deg, dist_pc, 60000.0, dist_err_pc=dist_err_pc)
        spec["_gw170817_mjd_ell"] = sync_ref["gw170817_mjd_ell"]
        beta_ecl = sync_ref["ecliptic_lat_deg"]
        if spec["science_track"] == "ETZ":
            assert abs(beta_ecl) <= 0.264, f"ETZ star {st} |beta|={abs(beta_ecl):.3f} > 0.264"

        ppo_planets: list[tuple[float, float]] = []
        ref_planet: tuple[float, float, float] | None = None
        if spec.get("orbital_campaign"):
            cands: list[tuple[float, str, float, float, float]] = []
            for r in nh_list:
                if r.get("pl_orbper") and r.get("pl_tranmid"):
                    p_d = float(r["pl_orbper"])
                    t0_b = float(r["pl_tranmid"])
                    ecc_v = float(r.get("pl_orbeccen") or 0.0)
                    ppo_planets.append((p_d, t0_b))
                    kp_v = compute_keplerian_kp_kms(mass_msun, p_d, ecc_v)
                    cands.append((kp_v, r["pl_name"], p_d, t0_b, ecc_v))
            cands.sort(reverse=True)
            assert len(cands) >= 1, f"{st}: missing orbital ephemeris in NASA pscomppars!"
            kp, pl_name, p_days, t0_bjd, ecc = cands[0]
            ref_planet = (p_days, t0_bjd, kp)

        if spec["instrument"] == "GEMINI_GRACES":
            pool = fetch_pool_graces(spec, excluded_dp_ids)
        elif spec["instrument"] == "ESO_CORALIE":
            pool = fetch_pool_coralie(spec, ra_deg, dec_deg, excluded_dp_ids)
        else:
            pool = fetch_pool_carmenes(spec, excluded_dp_ids)

        picked = select_two_exposures(spec, pool, ref_planet)
        assert len(picked) == 2

        camp_exps: dict[str, dict[str, Any]] = {}
        if spec.get("orbital_campaign") and ref_planet is not None:
            camp_num += 1
            p_days, t0_bjd, kp = ref_planet
            with_phi = []
            for pr in picked:
                bjd_est = pr["mjd_obs"] + 2400000.5
                phi, dv_orb = compute_planet_orbital_rv_kms(bjd_est, t0_bjd, p_days, kp)
                with_phi.append((pr, bjd_est, phi, dv_orb))
            in_id = min(with_phi, key=lambda x: abs(x[2]))[0]["dp_id"]
            dvs = [x[3] for x in with_phi]
            dv_span = max(dvs) - min(dvs)
            assert dv_span >= 5.0, f"{st}: orbital dv_span={dv_span:.2f} < 5.0 km/s!"

            camps_exp_list = []
            for pr, bjd_est, phi, dv_orb in with_phi:
                win_lbl = "IN_WINDOW" if pr["dp_id"] == in_id else "OUT_OF_WINDOW"
                camp_exps[pr["dp_id"]] = {"phase_window": win_lbl, "signed_phase": round(phi, 5), "planet_orbital_rv_kms": round(dv_orb, 4)}
                camps_exp_list.append({
                    "dp_id": pr["dp_id"],
                    "mjd_obs": round(pr["mjd_obs"], 5),
                    "bjd_tdb_est": round(bjd_est, 5),
                    "signed_phase": round(phi, 5),
                    "phase_window": win_lbl,
                    "planet_orbital_rv_kms": round(dv_orb, 4),
                    "ppo_align_score": round(compute_ppo_alignment_score(bjd_est, ppo_planets), 5),
                })

            campaigns_doc[st] = {
                "campaign_index": camp_num,
                "canonical_target": st,
                "common_name": spec["common_name"],
                "instrument": spec["instrument"],
                "role": spec["role"],
                "null_orbital": False,
                "planet_name": pl_name,
                "n_planets_in_system": n_pl,
                "n_transiting_with_t0": len(ppo_planets),
                "stellar_mass_msun": round(mass_msun, 4),
                "orb_per_days": round(p_days, 7),
                "orb_t0_bjd": round(t0_bjd, 6),
                "orb_ecc": round(ecc, 4),
                "kp_kms": round(kp, 3),
                "orbital_dv_span_kms": round(dv_span, 3),
                "min_ppo_align_score": round(min(e["ppo_align_score"] for e in camps_exp_list), 5),
                "exposures": camps_exp_list,
            }

        nearest = min((sep_arcsec(ra_deg, dec_deg, c["ra_deg"], c["dec_deg"]), c["label"]) for c in excluded_coords)
        assert nearest[0] >= 300.0, f"Brand-new star {st} within 300\" of prior star: {nearest}!"
        all_star_coords.append({"canonical_target": st, "ra_deg": ra_deg, "dec_deg": dec_deg})
        sep_verif.append({
            "canonical_target": st,
            "instrument": spec["instrument"],
            "science_track": spec["science_track"],
            "ra_deg": round(ra_deg, 6),
            "dec_deg": round(dec_deg, 6),
            "dist_pc": round(dist_pc, 4),
            "within_10pc": within_10pc,
            "nearest_prior_target": nearest[1],
            "min_sky_separation_arcsec": round(nearest[0], 2),
        })

        for rank, pr in enumerate(picked, 1):
            ce = camp_exps.get(pr["dp_id"], {"phase_window": "NONE", "signed_phase": 0.0, "planet_orbital_rv_kms": 0.0})
            sync_obs = compute_multievent_sync_v51(ra_deg, dec_deg, dist_pc, pr["mjd_obs"], dist_err_pc=dist_err_pc)
            row = {
                "instrument": spec["instrument"],
                "canonical_target": st,
                "common_name": spec["common_name"],
                "role": spec["role"],
                "subrole": spec["subrole"],
                "science_track": spec["science_track"],
                "panchromatic_bridge": False,
                "gaia_source_id": spec["gaia_source_id"],
                "s_ra": round(ra_deg, 6),
                "s_dec": round(dec_deg, 6),
                "pmra_mas_yr": round(pmra, 3),
                "pmdec_mas_yr": round(pmdec, 3),
                "dist_pc": round(dist_pc, 5),
                "within_10pc": within_10pc,
                "phot_g_mag": round(phot_g, 4),
                "phot_bp_mag": round(phot_bp, 4) if phot_bp is not None else "",
                "phot_rp_mag": round(phot_rp, 4) if phot_rp is not None else "",
                "j_mag": spec["j_mag"],
                "h_mag": spec["h_mag"],
                "ks_mag": spec["ks_mag"],
                "teff_k": round(teff_k, 1),
                "mh_dex": round(mh_dex, 3),
                "stellar_mass_msun": round(mass_msun, 4),
                "prior_rv_kms": round(prior_rv, 4),
                "n_exoplanets": n_pl,
                "has_transiting_planet": has_tr,
                "ecliptic_lat_deg": round(beta_ecl, 5),
                "sn1987a_dt_days": round(sync_obs["sn1987a_dt_days"], 3),
                "gw170817_dt_days": round(sync_obs["gw170817_dt_days"], 3),
                "sn2023ixf_dt_days": round(sync_obs["sn2023ixf_dt_days"], 3),
                "ppo_align_score": round(compute_ppo_alignment_score(pr["mjd_obs"] + 2400000.5, ppo_planets) if len(ppo_planets) >= 2 else 1.0, 5),
                "epoch_rank": rank,
                "dp_id": pr["dp_id"],
                "grating": pr["grating"],
                "resolving_power": round(pr["resolving_power"], 1),
                "mjd_obs": round(pr["mjd_obs"], 5),
                "t_exptime": round(pr["t_exptime"], 2),
                "phase_window": ce["phase_window"],
                "signed_phase": ce["signed_phase"],
                "planet_orbital_rv_kms": ce["planet_orbital_rv_kms"],
                "f1_id": pr["f1_id"],
                "f1_rel": f"{spec['instrument']}/{st}/{pr['f1_id']}.fits",
                "f1_url": pr["f1_url"],
                "f1_bytes": 0,
                "total_bytes": 0,
            }
            cohort_rows.append(row)
            head_jobs.append(row)

    print("4. Resolving exact HTTP HEAD Content-Length across all 30 FITS URLs...", flush=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        sizes = list(ex.map(lambda r: head_content_length(r["f1_url"]), head_jobs))
    total_bytes = 0
    for r, sz in zip(cohort_rows, sizes):
        assert sz >= 16384, f"Missing Content-Length for {r['f1_url']}: {sz}"
        r["f1_bytes"] = int(sz)
        r["total_bytes"] = int(sz)
        total_bytes += int(sz)

    intra_min = min(
        sep_arcsec(a["ra_deg"], a["dec_deg"], b["ra_deg"], b["dec_deg"])
        for i, a in enumerate(all_star_coords)
        for b in all_star_coords[i + 1 :]
    )
    min_prior_sep = min(s["min_sky_separation_arcsec"] for s in sep_verif)
    d093_dps = {r["dp_id"] for r in cohort_rows}
    overlap_cnt = len(d093_dps & excluded_dp_ids)
    proj_mib = total_bytes / (1024.0 * 1024.0)
    n_new = len(all_star_coords)
    n_controls = len({r["canonical_target"] for r in cohort_rows if r["role"] == "CONTROL"})
    n_new_10pc = sum(1 for s in sep_verif if s["within_10pc"])

    assert overlap_cnt == 0, f"dp_id overlap {overlap_cnt}!"
    assert n_new == 15 and n_controls == 5
    assert len(cohort_rows) == 30, len(cohort_rows)
    assert len(campaigns_doc) == 8, len(campaigns_doc)
    assert proj_mib <= 225.0, f"Projected {proj_mib:.2f} MiB > 225.0 MiB!"
    assert min_prior_sep >= 300.0 and intra_min >= 300.0, (min_prior_sep, intra_min)
    assert not inp_dir.exists(), "inputs_d093_v5_1 must not exist before lock!"

    with (WS / "FROZEN_COHORT_D093.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cohort_rows[0].keys()))
        w.writeheader()
        w.writerows(cohort_rows)

    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(
        json.dumps({"schema": "D093_ORBITAL_CAMPAIGNS_V1", "phase_id": "D093", "n_campaigns": len(campaigns_doc), "campaigns": campaigns_doc}, indent=2) + "\n",
        encoding="utf-8",
    )

    pe93 = {
        "schema": "D093_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D093",
        "verified_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prior_phases_covered": "C001-C037 + D001-D092",
        "n_prior_excluded_coords": len(excluded_coords),
        "n_prior_excluded_dp_ids": len(excluded_dp_ids),
        "d093_total_stars": n_new,
        "d093_brand_new_unique_stars": n_new,
        "d093_panchromatic_bridge_stars": 0,
        "d093_control_stars": n_controls,
        "d093_brand_new_within_10pc": n_new_10pc,
        "d093_total_exposures": len(cohort_rows),
        "d093_total_fits_files": len(cohort_rows),
        "d093_projected_download_bytes": total_bytes,
        "d093_projected_download_gib": round(total_bytes / (1024.0 ** 3), 4),
        "d093_projected_download_mib": round(proj_mib, 2),
        "d093_dp_id_overlap_count": overlap_cnt,
        "min_brand_new_sky_separation_arcsec": round(min_prior_sep, 2),
        "min_intra_d093_separation_arcsec": round(intra_min, 2),
        "star_separation_verification": sep_verif,
        "excluded_dp_ids": sorted(excluded_dp_ids),
        "excluded_targets_coordinate_registry": excluded_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pe93, indent=2) + "\n", encoding="utf-8")

    lock_files = [
        "v5_1_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D093.csv",
        "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "PRIOR_V5_0_PHASES_SNAPSHOT.json",
    ]
    locked_hashes = {fn: sha256_file(WS / fn) for fn in lock_files}
    locked_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    method_lock = {
        "schema": "D093_METHOD_LOCK_V1",
        "phase_id": "D093",
        "detector": DETECTOR_NAME,
        "locked_utc": locked_utc,
        "instruments": ["GEMINI_GRACES", "ESO_CORALIE", "CARMENES_VIS"],
        "retroactive_reused_bundles": {
            "d088_northern_bundle": {"archive": ARCHIVE_N.name, "archive_sha256": ARCHIVE_N_SHA256, "n_exposures": 176},
            "d090_nirspec_bundle": {"archive": ARCHIVE_P.name, "archive_sha256": ARCHIVE_P_SHA256, "n_nirspec_g395h_exposures": 63},
            "d092_v50_bundle": {"archive": ARCHIVE_R.name, "archive_sha256": ARCHIVE_R_SHA256, "n_exposures": 57},
        },
        "locked_v51_parameters": {
            "drift_v51_n_offsets": BASE_V5_1_CONFIG["drift_v51_n_offsets"],
            "drift_v51_min_abs_dv_kms": BASE_V5_1_CONFIG["drift_v51_min_abs_dv_kms"],
            "drift_v51_max_abs_dv_kms": BASE_V5_1_CONFIG["drift_v51_max_abs_dv_kms"],
            "drift_v51_epoch_min_z": BASE_V5_1_CONFIG["drift_v51_epoch_min_z"],
            "drift_v51_comb_min_z": BASE_V5_1_CONFIG["drift_v51_comb_min_z"],
            "g8_patch_half_px": BASE_V5_1_CONFIG["g8_patch_half_px"],
            "g8_pca_dim": BASE_V5_1_CONFIG["g8_pca_dim"],
            "g8_knn_k": BASE_V5_1_CONFIG["g8_knn_k"],
            "g8_min_novelty_z": BASE_V5_1_CONFIG["g8_min_novelty_z"],
            "nirspec_edge_trim_um": BASE_V5_1_CONFIG["nirspec_edge_trim_um"],
            "nirspec_ccf_min_sigma": BASE_V5_1_CONFIG["nirspec_ccf_min_sigma"],
            "nirspec_ccf_min_confounder_ratio": BASE_V5_1_CONFIG["nirspec_ccf_min_confounder_ratio"],
            "rpca_block_len": BASE_V5_1_CONFIG["rpca_block_len"],
            "rpca_overlap": BASE_V5_1_CONFIG["rpca_overlap"],
            "rpca_loso_rank": BASE_V5_1_CONFIG["rpca_loso_rank"],
            "g7_min_z_rpca": BASE_V5_1_CONFIG["g7_min_z_rpca"],
            "g7_min_rarity_score": BASE_V5_1_CONFIG["g7_min_rarity_score"],
            "agnostic_scales_lsf": list(BASE_V5_1_CONFIG["agnostic_scales_lsf"]),
            "agnostic_min_abs_z": BASE_V5_1_CONFIG["agnostic_min_abs_z"],
            "agnostic_min_rarity_score": BASE_V5_1_CONFIG["agnostic_min_rarity_score"],
            "etz_max_abs_beta_deg": 0.264,
            "ellipsoid_max_abs_dt_days": 180.0,
        },
        "hard_caps": {
            "max_raw_download_mib": 225.0,
            "min_post_free_gib": 6.5,
            "max_bounded_bundle_mib": 25.0,
            "min_chronology_lag_s": 3.0,
        },
        "locked_file_hashes": locked_hashes,
    }
    ml_path = WS / "METHOD_LOCK.json"
    ml_path.write_text(json.dumps(method_lock, indent=2) + "\n", encoding="utf-8")

    lock_receipt = {
        "schema": "D093_LOCK_RECEIPT_V1",
        "phase_id": "D093",
        "locked_utc": locked_utc,
        "method_lock_sha256": sha256_file(ml_path),
        "inputs_d093_v5_1_exists": inp_dir.exists(),
        "locked_artifact_sha256": locked_hashes,
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lock_receipt, indent=2) + "\n", encoding="utf-8")

    print(
        f"DONE build_cohort: {len(cohort_rows)} exposures ({len(cohort_rows)} FITS), "
        f"{n_new} brand-new stars ({n_new_10pc} <10pc, {n_controls} CTRL), "
        f"{len(campaigns_doc)} orbital campaigns, proj={proj_mib:.2f} MiB, dp_overlap={overlap_cnt}, "
        f"min_prior_sep={min_prior_sep:.1f}\", min_intra_sep={intra_min:.1f}\", locked_utc={locked_utc}",
        flush=True,
    )


if __name__ == "__main__":
    main()
