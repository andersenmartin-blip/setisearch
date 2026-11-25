#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D108 (`V6.6`) Stage-1 Frozen Cohort Builder & Preregistration Seal:
  - Strictly excludes ALL 977 prior target coordinates (D001-D107) and ALL 3,935
    prior dp_ids (+ 46 format probes) for every brand-new D108 target (>= 600 arcsec).
  - Selects 17 IXPE GPD targets (12 bridges + 5 brand-new), 16 RXTE HEXTE+PCA targets
    (15 bridges + 1 brand-new AR Lac = 32 obs), 111 SRG/eROSITA-DE DR1 HamStar targets
    (24 prior bridges + LP 655-48 intra-D108 bridge + 3 brand-new <10 pc + 83 brand-new
    10-20 pc coronal stars), 6 ESO Orbits #193-#198 (N=5 distinct nights = 30 FITS),
    and 2 <10 pc ESO UVES targets (WD 0435-088, LP 655-48 = 9 FITS).
  - Exact brand-new count: 5 IXPE + 1 RXTE + 6 Orbits + 2 UVES + 3 eROSITA <10pc
    + 83 eROSITA 10-20pc = 100 EXACT unique brand-new stars -> 1,004 cumulative stars.
  - Verifies inputs_d108_v6_6 DOES NOT EXIST before sealing METHOD_LOCK.json and LOCK_RECEIPT.json.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import tarfile
import time
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits
from astropy.io.votable import parse_single_table

WS = Path(__file__).resolve().parent
ROOT = WS.parent.parent
RAW_DIR = ROOT / "inputs_d108_v6_6"
ARCHIVES_DIR = ROOT / "archives"
WS107 = ROOT / "analysis_workspace/work_v6_5_20261125_d107_icecube_neutrino_swift_bat_xrt_900star"
ARCHIVE_AG = ARCHIVES_DIR / "SETI_D107_V6_5_ICECUBE_NEUTRINO_SWIFT_BAT_XRT_900STAR_RESULTS_2026-11-25.zip"

DETECTOR_NAME = "TECHNOSIGNATURE_V6_6_IXPE_POLARIMETRY_EROSITA_DR1_RXTE_HEXTE_PCA_1000STAR_SYNTHESIS"
HAMSTAR_URL = "https://erosita.mpe.mpg.de/dr1/AllSkySurveyData_dr1/Catalogues_dr1/FreundS_DR1/HamStar_eRASS1_Main_Likely_Identifications_v1.1.fits.tgz"

AU_M = 1.495978707e11
MSUN_KG = 1.98847e30
G_CONST = 6.67430e-11
DAY_S = 86400.0
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

# Verified IXPE public targets (12 prior bridges + 5 brand-new controls)
IXPE_TARGETS: list[dict[str, Any]] = [
    {"obsid": "01002501", "star": "VELAX1",   "common_name": "Vela X-1 (HMXB Accreting Pulsar)",       "role": "CONTROL", "subrole": "IXPE_XRB_POLARIMETRY_BRIDGE",  "bridge": True,  "dist_pc": 2000.0,      "teff": 26000.0, "rv": -7.0},
    {"obsid": "01003601", "star": "IC4329A",  "common_name": "IC 4329A (Seyfert-1 AGN z=0.016)",       "role": "CONTROL", "subrole": "IXPE_AGN_POLARIMETRY_BRIDGE",  "bridge": True,  "dist_pc": 70000000.0,  "teff": 4500.0,  "rv": 4813.0},
    {"obsid": "01003701", "star": "MRK421",   "common_name": "Mrk 421 (TeV HBL Blazar z=0.030)",       "role": "CONTROL", "subrole": "IXPE_BLAZAR_POLARIMETRY_BRIDGE", "bridge": True, "dist_pc": 136000000.0, "teff": 12000.0, "rv": 9000.0},
    {"obsid": "01004301", "star": "CENA",     "common_name": "Centaurus A (Radio Galaxy z=0.0018)",    "role": "CONTROL", "subrole": "IXPE_AGN_POLARIMETRY_BRIDGE",  "bridge": True,  "dist_pc": 3800000.0,   "teff": 5000.0,  "rv": 547.0},
    {"obsid": "01005701", "star": "3C279",    "common_name": "3C 279 (FSRQ Blazar z=0.536)",           "role": "CONTROL", "subrole": "IXPE_BLAZAR_POLARIMETRY_BRIDGE", "bridge": True, "dist_pc": 3100000000.0, "teff": 15000.0, "rv": 0.0},
    {"obsid": "01005901", "star": "3C273",    "common_name": "3C 273 (Flat-Spectrum Quasar z=0.158)",  "role": "CONTROL", "subrole": "IXPE_AGN_POLARIMETRY_BRIDGE",  "bridge": True,  "dist_pc": 749000000.0, "teff": 15000.0, "rv": 0.0},
    {"obsid": "02005601", "star": "PKS2155",  "common_name": "PKS 2155-304 (TeV Blazar z=0.116)",      "role": "CONTROL", "subrole": "IXPE_BLAZAR_POLARIMETRY_BRIDGE", "bridge": True, "dist_pc": 540000000.0, "teff": 12000.0, "rv": 0.0},
    {"obsid": "02007001", "star": "SMCX1",    "common_name": "SMC X-1 (Super-Eddington X-Ray PSR)",    "role": "CONTROL", "subrole": "IXPE_XRB_POLARIMETRY_BRIDGE",  "bridge": True,  "dist_pc": 60000.0,     "teff": 30000.0, "rv": 180.0},
    {"obsid": "02008001", "star": "NGC1068",  "common_name": "NGC 1068 (Seyfert-2 AGN z=0.0038)",      "role": "CONTROL", "subrole": "IXPE_AGN_POLARIMETRY_BRIDGE",  "bridge": True,  "dist_pc": 14400000.0,  "teff": 4500.0,  "rv": 1137.0},
    {"obsid": "03006899", "star": "NGC4151",  "common_name": "NGC 4151 (Seyfert-1.5 AGN z=0.0033)",    "role": "CONTROL", "subrole": "IXPE_AGN_POLARIMETRY_BRIDGE",  "bridge": True,  "dist_pc": 15800000.0,  "teff": 4500.0,  "rv": 995.0},
    {"obsid": "03007199", "star": "NGC4945",  "common_name": "NGC 4945 (Compton-Thick AGN 3.7 Mpc)",   "role": "CONTROL", "subrole": "IXPE_AGN_POLARIMETRY_BRIDGE",  "bridge": True,  "dist_pc": 3720000.0,   "teff": 4500.0,  "rv": 563.0},
    {"obsid": "04003999", "star": "EXHYA",    "common_name": "EX Hya (Intermediate Polar CV)",         "role": "CONTROL", "subrole": "IXPE_CV_POLARIMETRY_BRIDGE",   "bridge": True,  "dist_pc": 56.91,       "teff": 4000.0,  "rv": 0.0},
    # 5 Brand-new IXPE targets (verified sep >= 4,660'' from all 977 prior coords)
    {"obsid": "01002701", "star": "4U1626",   "common_name": "4U 1626-67 (Ultracompact X-Ray PSR)",    "role": "CONTROL", "subrole": "IXPE_NEW_ULTRACOMPACT_PSR",    "bridge": False, "dist_pc": 3500.0,      "teff": 5990.5,  "rv": 0.0},
    {"obsid": "02009701", "star": "BLLAC",    "common_name": "BL Lacertae (TeV BL Lac AGN z=0.069)",   "role": "CONTROL", "subrole": "IXPE_NEW_BLAZAR_POLARIMETRY",  "bridge": False, "dist_pc": 310000000.0, "teff": 4578.3,  "rv": -22.6},
    {"obsid": "03005599", "star": "PSRJ1023", "common_name": "PSR J1023+0038 (Transitional Millisecond PSR)", "role": "CONTROL", "subrole": "IXPE_NEW_MSP_POLARIMETRY", "bridge": False, "dist_pc": 1368.0,   "teff": 5965.6,  "rv": 0.0},
    {"obsid": "05003499", "star": "LSI61303", "common_name": "LS I +61 303 (TeV Gamma-Ray Binary)",    "role": "CONTROL", "subrole": "IXPE_NEW_GAMMA_BINARY",        "bridge": False, "dist_pc": 2650.0,      "teff": 28000.0, "rv": -41.4},
    {"obsid": "05004799", "star": "MRK501",   "common_name": "Mrk 501 (TeV HBL Blazar z=0.033)",       "role": "CONTROL", "subrole": "IXPE_NEW_BLAZAR_POLARIMETRY",  "bridge": False, "dist_pc": 146000000.0, "teff": 12000.0, "rv": 9900.0},
]

# Verified RXTE HEXTE + PCA public targets (15 prior bridges + 1 brand-new AR Lac)
RXTE_TARGETS: list[dict[str, Any]] = [
    {"obsid": "10001-02-01-00", "ao": "AO1", "prnb": "10001", "star": "HD34029",  "common_name": "Capella (alpha Aur)",          "role": "SCIENCE", "bridge": True},
    {"obsid": "10006-01-01-00", "ao": "AO1", "prnb": "10006", "star": "ARLAC",    "common_name": "AR Lac (Eclipsing RS CVn)",    "role": "SCIENCE", "bridge": False},
    {"obsid": "10008-01-01-00", "ao": "AO1", "prnb": "10008", "star": "AUMIC",    "common_name": "AU Mic (<10 pc Planet Host)",  "role": "SCIENCE", "bridge": True},
    {"obsid": "20009-01-01-00", "ao": "AO2", "prnb": "20009", "star": "ABDOR",    "common_name": "AB Doradus (BY Dra Host)",     "role": "SCIENCE", "bridge": True},
    {"obsid": "20022-01-01-00", "ao": "AO2", "prnb": "20022", "star": "FOAQR",    "common_name": "FO Aqr (Intermediate Polar)",  "role": "CONTROL", "bridge": True},
    {"obsid": "30003-01-01-00", "ao": "AO3", "prnb": "30003", "star": "HD22468",  "common_name": "HR 1099 (V711 Tau RS CVn)",    "role": "SCIENCE", "bridge": True},
    {"obsid": "30004-01-01-00", "ao": "AO3", "prnb": "30004", "star": "IIPEG",    "common_name": "II Peg (RS CVn Coronal Star)", "role": "SCIENCE", "bridge": True},
    {"obsid": "30016-01-01-00", "ao": "AO3", "prnb": "30016", "star": "EXHYA",    "common_name": "EX Hya (Intermediate Polar)",  "role": "CONTROL", "bridge": True},
    {"obsid": "40099-01-01-00", "ao": "AO4", "prnb": "40099", "star": "CYGX1",    "common_name": "Cygnus X-1 (BH X-Ray Binary)", "role": "CONTROL", "bridge": True},
    {"obsid": "50001-01-01-00", "ao": "AO5", "prnb": "50001", "star": "HD019356", "common_name": "Algol (beta Per)",           "role": "CONTROL", "bridge": True},
    {"obsid": "50007-01-01-00", "ao": "AO5", "prnb": "50007", "star": "V2400OPH", "common_name": "V2400 Oph (Intermediate Polar)", "role": "CONTROL", "bridge": True},
    {"obsid": "60003-01-01-00", "ao": "AO6", "prnb": "60003", "star": "ETACAR",   "common_name": "Eta Carinae (Colliding-Wind)", "role": "CONTROL", "bridge": True},
    {"obsid": "60017-03-01-00", "ao": "AO6", "prnb": "60017", "star": "HERX1",    "common_name": "Hercules X-1 (X-Ray Pulsar)",  "role": "CONTROL", "bridge": True},
    {"obsid": "80007-01-01-00", "ao": "AO8", "prnb": "80007", "star": "TVCOL",    "common_name": "TV Col (Intermediate Polar)",  "role": "CONTROL", "bridge": True},
    {"obsid": "80172-01-01-00", "ao": "AO8", "prnb": "80172", "star": "MRK421",   "common_name": "Mrk 421 (TeV HBL Blazar)",     "role": "CONTROL", "bridge": True},
    {"obsid": "90007-01-01-00", "ao": "AO9", "prnb": "90007", "star": "SSCYG",    "common_name": "SS Cyg (Dwarf Nova)",          "role": "CONTROL", "bridge": True},
]

# 6 ESO Orbits #193-#198 (N=5 distinct nights each = 30 FITS)
ESO_ORBIT_SPECS: list[dict[str, Any]] = [
    {"campaign_order": 193, "star": "GJ317",    "common_name": "GJ 317 (NIRPS Orbit #193)",    "inst": "ESO_NIRPS",    "eso_col": "obs_collection='NIRPS'",    "grating": "NIRPS_YJH_966_1923NM",  "res_p": 70000.0,  "ra": 130.2444557, "dec": -23.4526970, "dist_pc": 15.1798, "pmra": -461.344, "pmdec": 805.221,  "gaia_id": "5701750715316821248", "gmag": 10.7651, "bp": 12.2327, "rp": 9.5689, "j": 7.934, "h": 7.321, "ks": 7.028, "teff": 3496.0, "mass": 0.402, "rv": 87.108, "n_pl": 2, "P_d": 695.69,     "ecc": 0.0826, "omega": 295.0, "k_kms": 0.07139,  "t0_mjd": 58088.90},
    {"campaign_order": 194, "star": "GJ1252",   "common_name": "GJ 1252 (NIRPS Orbit #194)",   "inst": "ESO_NIRPS",    "eso_col": "obs_collection='NIRPS'",    "grating": "NIRPS_YJH_966_1923NM",  "res_p": 70000.0,  "ra": 306.9286462, "dec": -56.4622865, "dist_pc": 20.3730, "pmra": 424.414,  "pmdec": -1230.620, "gaia_id": "GJ1252",              "gmag": 11.2364, "bp": None,    "rp": None,   "j": 8.697, "h": 8.161, "ks": 7.915, "teff": 3325.0, "mass": 0.381, "rv": 7.4836, "n_pl": 1, "P_d": 0.518235,   "ecc": 0.0000, "omega": 90.0,  "k_kms": 0.002360, "t0_mjd": 58667.597, "transit": True},
    {"campaign_order": 195, "star": "TOI198",   "common_name": "TOI-198 (ESPRESSO Orbit #195)", "inst": "ESO_ESPRESSO", "eso_col": "instrument_name='ESPRESSO'", "grating": "ESPRESSO_377_790NM", "res_p": 140000.0, "ra": 2.2716168,   "dec": -27.1217327, "dist_pc": 23.7760, "pmra": 692.224,  "pmdec": 90.067,   "gaia_id": "2333676738050041728", "gmag": 10.9157, "bp": 11.9105, "rp": 9.9302, "j": 8.636, "h": 8.059, "ks": 7.856, "teff": 3801.0, "mass": 0.417, "rv": 19.701, "n_pl": 1, "P_d": 10.215213,  "ecc": 0.1500, "omega": 90.0,  "k_kms": 0.001673, "t0_mjd": 59479.548, "transit": True},
    {"campaign_order": 196, "star": "TOI244",   "common_name": "TOI-244 (ESPRESSO Orbit #196)", "inst": "ESO_ESPRESSO", "eso_col": "instrument_name='ESPRESSO'", "grating": "ESPRESSO_377_790NM", "res_p": 140000.0, "ra": 10.5697269,  "dec": -36.7179680, "dist_pc": 22.0751, "pmra": -154.880, "pmdec": 45.632,   "gaia_id": "5001098681543159040", "gmag": 11.5490, "bp": 12.9330, "rp": 10.3878, "j": 8.826, "h": 8.219, "ks": 7.970, "teff": 3433.0, "mass": 0.428, "rv": 14.514, "n_pl": 1, "P_d": 7.397225,   "ecc": 0.0000, "omega": 90.0,  "k_kms": 0.001550, "t0_mjd": 58356.863, "transit": True},
    {"campaign_order": 197, "star": "GJ3293",   "common_name": "GJ 3293 (HARPS Orbit #197)",    "inst": "ESO_HARPS",    "eso_col": "instrument_name='HARPS'",    "grating": "HARPS_378_691NM",    "res_p": 115000.0, "ra": 67.1484300,  "dec": -25.1714070, "dist_pc": 20.2074, "pmra": -81.375,  "pmdec": -485.454, "gaia_id": "4893118771316702720", "gmag": 10.9880, "bp": 12.2865, "rp": 9.8565, "j": 8.362, "h": 7.749, "ks": 7.486, "teff": 3466.0, "mass": 0.420, "rv": 12.674, "n_pl": 4, "P_d": 30.5987,    "ecc": 0.0600, "omega": 340.0, "k_kms": 0.008603, "t0_mjd": 57000.00},
    {"campaign_order": 198, "star": "7CMA",     "common_name": "7 CMa (HARPS Orbit #198)",      "inst": "ESO_HARPS",    "eso_col": "instrument_name='HARPS'",    "grating": "HARPS_378_691NM",    "res_p": 115000.0, "ra": 99.1712853,  "dec": -19.2561907, "dist_pc": 20.4712, "pmra": 62.660,   "pmdec": -69.816,  "gaia_id": "2939555954755196160", "gmag": 3.6732,  "bp": 4.2478,  "rp": 2.9954, "j": 2.266, "h": 1.720, "ks": 1.564, "teff": 4826.0, "mass": 1.340, "rv": 4.000,  "n_pl": 2, "P_d": 735.10,     "ecc": 0.0600, "omega": 90.0,  "k_kms": 0.03430,  "t0_mjd": 57000.00},
]

# 2 <10 pc ESO UVES stars (LP 655-48 is intra-D108 bridge with EROSITA_DR1)
ESO_UVES_10PC: list[dict[str, Any]] = [
    {"star": "WD0435_088", "common_name": "WD 0435-088 (<10 pc DQ8 White Dwarf)", "role": "CONTROL", "subrole": "SUB10PC_WHITE_DWARF_UVES", "track": "SOLAR_NEIGHBORHOOD_10PC_UVES", "ra": 69.4486024, "dec": -8.8265162, "dist_pc": 9.4039, "pmra": 238.381, "pmdec": -1552.408, "gaia_id": "3186021141200137472", "gmag": 13.6007, "bp": 13.8070, "rp": 13.2378, "j": 12.660, "h": 12.375, "ks": 12.313, "teff": 6400.0, "mass": 0.60, "rv": 0.0, "bridge_d108": False},
    {"star": "LP655_48",   "common_name": "LP 655-48 (<10 pc M6V + eROSITA Bridge)", "role": "SCIENCE", "subrole": "SUB10PC_MDWARF_UVES_EROSITA", "track": "SOLAR_NEIGHBORHOOD_10PC_UVES_EROSITA_BRIDGE", "ra": 70.0988633, "dec": -5.5015398, "dist_pc": 9.7471, "pmra": 195.0, "pmdec": -285.0, "gaia_id": "3200303384927512960", "gmag": 14.9043, "bp": 17.01, "rp": 13.45, "j": 10.66, "h": 10.03, "ks": 9.64, "teff": 2850.0, "mass": 0.14, "rv": 0.0, "bridge_d108": True, "detuid": "em01_071096_020_ML00087_002_c010"},
]


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


def _http_head(url: str) -> int:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "SETI-D108-Stage1/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        if r.status not in (200, 206):
            raise RuntimeError(f"HEAD {r.status} for {url}")
        return int(r.headers.get("Content-Length") or 0)


def _tap_vot(url: str, adql: str, timeout: int = 35) -> list[dict[str, Any]]:
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "QUERY": adql}).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers={"User-Agent": "SETI-D108-Stage1/1.0"}), timeout=timeout) as r:
        raw = r.read()
    t = parse_single_table(io.BytesIO(raw)).to_table()
    return [{k.lower(): row[k] for k in t.colnames} for row in t]


def _make_canonical_star_from_hamstar(detuid: str, ctp_id: str, sim_name: str, used: set[str]) -> str:
    s = re.sub(r"[^A-Za-z0-9]", "", sim_name.replace("*", "").replace("V*", "").strip()).upper()
    if s and 3 <= len(s) <= 14 and s not in used and not s.isdigit():
        used.add(s)
        return s
    cand = f"ERO_{re.sub(r'[^A-Za-z0-9]', '', ctp_id)[:12].upper()}"
    if cand in used or len(cand) <= 5:
        cand = f"ERO_{detuid[5:11]}_{detuid.split('_ML')[1][:5]}"
    used.add(cand)
    return cand


def _estimate_teff_from_bprp(bprp: float) -> float:
    if not math.isfinite(bprp):
        return 3600.0
    if bprp < 0.0:
        return 12000.0
    if bprp < 0.8:
        return max(5000.0, 8800.0 - 4500.0 * bprp)
    if bprp < 2.2:
        return max(3400.0, 5600.0 - 1550.0 * (bprp - 0.8))
    return max(2400.0, 3400.0 - 380.0 * (bprp - 2.2))


def _make_row(
    inst: str, star: str, common_name: str, role: str, subrole: str, track: str,
    bridge_flag: bool, is_prior_bridge: bool, gaia_id: str,
    ra: float, dec: float, pmra: float, pmdec: float, dist_pc: float, within_10pc: bool,
    gmag: float | None, bp: float | None, rp: float | None, j: float | None, h: float | None, ks: float | None,
    teff: float, mass: float, rv: float, n_pl: int, has_tr: bool,
    rank: int, dp_id: str, grating: str, res_p: float, mjd: float, exptime: float,
    phase_win: str, sph: float, prv: float,
    f1_id: str, f1_rel: str, f1_url: str, f1_bytes: int, extras: list[dict[str, Any]],
) -> dict[str, Any]:
    ecl = _ecliptic_lat_deg(ra, dec)
    tot_b = int(f1_bytes) + sum(int(e["bytes"]) for e in extras)
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
        "total_bytes": int(tot_b), "extra_files": json.dumps(extras, separators=(",", ":")),
    }


def main() -> None:
    if RAW_DIR.exists():
        raise RuntimeError(f"STRICT ISOLATION VIOLATION: {RAW_DIR} ALREADY EXISTS before Stage-1 seal!")

    # 1. Load D001-D107 exclusion & Archive AG snapshot
    pex107 = json.loads((WS107 / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    with (WS107 / "FROZEN_COHORT_D107.csv").open(encoding="utf-8") as f:
        fc107 = list(csv.DictReader(f))
    prior_coords = list(pex107["excluded_targets_coordinate_registry"])
    seen_107 = set()
    for r in fc107:
        ct = r["canonical_target"]
        if ct not in seen_107 and r["is_prior_bridge"] == "False":
            seen_107.add(ct)
            prior_coords.append({"canonical_target": ct, "ra_deg": float(r["s_ra"]), "dec_deg": float(r["s_dec"])})
    assert len(prior_coords) == 977, f"Expected 977 prior coords, got {len(prior_coords)}"

    prior_dp = set(pex107["excluded_dp_ids"]) | {r["dp_id"] for r in fc107}
    assert len(prior_dp) == 3935, f"Expected 3935 prior dp_ids, got {len(prior_dp)}"
    fmt_probes = list(pex107["format_check_excluded_dp_ids"])
    fmt_set = set(fmt_probes)

    with zipfile.ZipFile(ARCHIVE_AG) as zf:
        def _zcsv(suffix: str) -> list[dict[str, str]]:
            nm = next(n for n in zf.namelist() if n.endswith(suffix))
            return list(csv.DictReader(zf.read(nm).decode("utf-8").splitlines()))
        sum_ag = json.loads(zf.read(next(n for n in zf.namelist() if n.endswith("/results/SUMMARY.json"))))
        u904_rows = _zcsv("/results/UNIFIED_PANCHROMATIC_V6_5_SYNTHESIS_904STARS.csv")
        br145_rows = _zcsv("/results/PANCHROMATIC_BRIDGE_145STARS_V65.csv")
        ell904_rows = _zcsv("/results/MULTIEVENT_ELLIPSOID_904STARS.csv")
        comb_u_ag = _zcsv("/results/ALLSKY_COMB_V4_1_UNIFIED_D079_D107.csv")
        comb_c_ag = _zcsv("/results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D107.csv")

    u904 = {r["star"]: r for r in u904_rows}
    star_coords: dict[str, tuple[float, float]] = {}
    for er in ell904_rows:
        star_coords[er["star"]] = (float(er["ra_deg"]), float(er["dec_deg"]))
    assert len(star_coords) == 904

    snap_107 = {
        "schema": "PRIOR_V6_5_PHASES_SNAPSHOT",
        "d107_summary_headline": sum_ag["unified_904star_panchromatic_v6_5_synthesis"],
        "prior_unified_904_rows": u904_rows,
        "prior_bridge_rows": br145_rows,
        "prior_ellipsoid_904_rows": ell904_rows,
        "prior_allsky_comb_unified_rows": comb_u_ag,
        "prior_allsky_comb_candidate_rows": comb_c_ag,
    }
    (WS / "PRIOR_V6_5_PHASES_SNAPSHOT.json").write_text(json.dumps(snap_107), encoding="utf-8")

    used_stars = set(u904.keys())
    cohort_rows: list[dict[str, Any]] = []
    brand_new_meta: dict[str, tuple[float, float]] = {}

    def _check_new_sep(star_k: str, ra: float, dec: float) -> float:
        bs = min(_ang_sep_arcsec(ra, dec, pc["ra_deg"], pc["dec_deg"]) for pc in prior_coords)
        assert bs >= 600.0, f"Separation fail vs prior for {star_k}: {bs:.2f}''"
        return bs

    # 2. IXPE CALDB (9 shared files) + 17 IXPE Targets
    cal_urls = [
        ("IXPE_GPD/CALDB/" + fn, f"https://heasarc.gsfc.nasa.gov/FTP/caldb/data/ixpe/gpd/cpf/{k}/{fn}")
        for k, fn in [
            ("arf", "ixpe_d1_20170101_05.arf"), ("arf", "ixpe_d2_20170101_05.arf"), ("arf", "ixpe_d3_20170101_05.arf"),
            ("mrf", "ixpe_d1_20170101_05.mrf"), ("mrf", "ixpe_d2_20170101_05.mrf"), ("mrf", "ixpe_d3_20170101_05.mrf"),
            ("rmf", "ixpe_d1_20211209_01.rmf"), ("rmf", "ixpe_d2_20211209_01.rmf"), ("rmf", "ixpe_d3_20211209_01.rmf"),
        ]
    ]
    cal_extras: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        szs = list(pool.map(lambda item: _http_head(item[1]), cal_urls))
    for (rel, u), sz in zip(cal_urls, szs):
        cal_extras.append({"rel": rel, "url": u, "bytes": sz})

    ix_ids_q = ",".join(f"'{t['obsid']}'" for t in IXPE_TARGETS)
    ix_tap = _tap_vot("https://heasarc.gsfc.nasa.gov/xamin/vo/tap/sync",
                      f"SELECT obsid, name, ra, dec, exposure_1, exposure_2, exposure_3, time FROM ixmaster WHERE obsid IN ({ix_ids_q})")
    ix_map = {str(r["datalinkid"]).strip(): r for r in ix_tap}

    def _resolve_ixpe(spec: dict[str, Any]) -> dict[str, Any]:
        oid = spec["obsid"]
        cyc = oid[:2]
        tr = ix_map[oid]
        ra, dec = float(tr["ra"]), float(tr["dec"])
        mjd = float(tr["time"])
        exp = float(tr["exposure_1"]) + float(tr["exposure_2"]) + float(tr["exposure_3"])
        base = f"https://heasarc.gsfc.nasa.gov/FTP/ixpe/data/obs/{cyc}/{oid}/event_l2/"
        html = urllib.request.urlopen(base, timeout=20).read().decode("utf-8", "replace")
        evts = sorted(set(re.findall(r'ixpe[0-9]+_det[123]_evt2_v[0-9]+\.fits(?:\.gz)?', html)))
        assert len(evts) == 3, f"Expected 3 evt2 files for IXPE {oid}, got {evts}"
        f_sz = [_http_head(base + fn) for fn in evts]
        st = spec["star"]
        if spec["bridge"]:
            ra, dec = star_coords[st]
            dist_pc = float(u904[st]["dist_pc"])
            cname = u904[st]["common_name"]
        else:
            dist_pc = float(spec["dist_pc"])
            cname = spec["common_name"]
            _check_new_sep(st, ra, dec)
            brand_new_meta[st] = (ra, dec)
        extras = [{"rel": f"IXPE_GPD/{oid}/{evts[k]}", "url": base + evts[k], "bytes": f_sz[k]} for k in (1, 2)] + cal_extras
        return _make_row(
            "IXPE_GPD", st, cname, spec["role"], spec["subrole"], "XRAY_SPECTROPOLARIMETRIC_SETI_2_8KEV",
            True, spec["bridge"], st, ra, dec, 0.0, 0.0, dist_pc, dist_pc <= 10.0,
            None, None, None, None, None, None, spec["teff"], 1.0, spec["rv"], 0, False,
            1, f"IXPE_GPD_{oid}_{st}", "IXPE_3GPD_2_8KEV_STOKES_IQU", 10.4, mjd, exp,
            "NONE", 0.0, 0.0, evts[0], f"IXPE_GPD/{oid}/{evts[0]}", base + evts[0], f_sz[0], extras,
        )

    print("Resolving 17 IXPE GPD targets + CALDB...")
    with ThreadPoolExecutor(max_workers=6) as pool:
        cohort_rows.extend(list(pool.map(_resolve_ixpe, IXPE_TARGETS)))

    # 3. 16 RXTE HEXTE + PCA Targets (= 32 observations)
    xte_ids_q = ",".join(f"'{t['obsid']}'" for t in RXTE_TARGETS)
    xte_tap = _tap_vot("https://heasarc.gsfc.nasa.gov/xamin/vo/tap/sync",
                       f"SELECT obsid, target_name, ra, dec, exposure, prnb, time FROM xtemaster WHERE obsid IN ({xte_ids_q})")
    xte_map = {str(r["datalinkid"]).strip(): r for r in xte_tap}

    def _resolve_rxte_pair(spec: dict[str, Any]) -> list[dict[str, Any]]:
        oid = spec["obsid"]
        st = spec["star"]
        tr = xte_map[oid]
        ra, dec = float(tr["ra"]), float(tr["dec"])
        mjd = float(tr["time"])
        exp = float(tr["exposure"])
        base = f"https://heasarc.gsfc.nasa.gov/FTP/rxte/data/archive/{spec['ao']}/P{spec['prnb']}/{oid}/stdprod/"
        html = urllib.request.urlopen(base, timeout=20).read().decode("utf-8", "replace")
        s0 = sorted(set(re.findall(r'xh[^"?/]+_s0\.pha\.gz', html)))[0]
        b0 = sorted(set(re.findall(r'xh[^"?/]+_b0\.pha\.gz', html)))[0]
        s1 = sorted(set(re.findall(r'xh[^"?/]+_s1\.pha\.gz', html)))[0]
        b1 = sorted(set(re.findall(r'xh[^"?/]+_b1\.pha\.gz', html)))[0]
        ha_files = sorted(set(re.findall(r'hexte_[^"?/]+\.arf\.gz', html)))
        hr_files = sorted(set(re.findall(r'xh[^"?/]+\.rmf\.gz', html)))
        s2 = sorted(set(re.findall(r'xp[^"?/]+_s2\.pha\.gz', html)))[0]
        b2 = sorted(set(re.findall(r'xp[^"?/]+_b2\.pha\.gz', html)))[0]
        rsp = sorted(set(re.findall(r'xp[^"?/]+\.rsp\.gz', html)))[0]
        all_f = [s0, b0, s1, b1] + ha_files + hr_files + [s2, b2, rsp]
        sz_map = {fn: _http_head(base + fn) for fn in all_f}
        if spec["bridge"]:
            ru = u904[st]
            ra, dec = star_coords[st]
            dist_pc = float(ru["dist_pc"])
            cname = ru["common_name"]
            teff = float(ru["teff_k"] or 5000.0)
            gmag = float(ru["phot_g_mag"]) if ru.get("phot_g_mag") else None
            n_pl = int(float(ru["n_exoplanets"] or 0))
            within10 = ru["within_10pc"] == "True"
        else:
            # AR Lac (brand-new RXTE RS CVn binary, verified Gaia DR3 1962909425622345728)
            ra, dec, dist_pc, gmag, teff, n_pl, within10 = 332.1697427, 45.7424608, 42.50875, 5.9107, 5573.8, 0, False
            cname = spec["common_name"]
            _check_new_sep(st, ra, dec)
            brand_new_meta[st] = (ra, dec)
        hx_ex = [{"rel": f"RXTE/{oid}/{fn}", "url": base + fn, "bytes": sz_map[fn]} for fn in [b0, s1, b1] + ha_files + hr_files]
        pca_ex = [{"rel": f"RXTE/{oid}/{fn}", "url": base + fn, "bytes": sz_map[fn]} for fn in [b2, rsp]]
        r_hx = _make_row(
            "RXTE_HEXTE", st, cname, spec["role"], "RXTE_HEXTE_HARD_XRAY_15_250KEV", "HARD_XRAY_HEXTE_PCA_BRIDGE",
            True, spec["bridge"], st, ra, dec, 0.0, 0.0, dist_pc, within10, gmag, None, None, None, None, None,
            teff, 1.0, 0.0, n_pl, False, 1, f"RXTE_HEXTE_{oid}_{st}", "HEXTE_CLUSTER_AB_15_250KEV", 6.25, mjd, exp,
            "NONE", 0.0, 0.0, s0, f"RXTE/{oid}/{s0}", base + s0, sz_map[s0], hx_ex,
        )
        r_pca = _make_row(
            "RXTE_PCA", st, cname, spec["role"], "RXTE_PCA_STD2_2_60KEV", "HARD_XRAY_HEXTE_PCA_BRIDGE",
            True, spec["bridge"], st, ra, dec, 0.0, 0.0, dist_pc, within10, gmag, None, None, None, None, None,
            teff, 1.0, 0.0, n_pl, False, 1, f"RXTE_PCA_{oid}_{st}", "PCA_STD2_2_60KEV", 5.56, mjd, exp,
            "NONE", 0.0, 0.0, s2, f"RXTE/{oid}/{s2}", base + s2, sz_map[s2], pca_ex,
        )
        return [r_hx, r_pca]

    print("Resolving 16 RXTE HEXTE+PCA target pairs (32 obs)...")
    with ThreadPoolExecutor(max_workers=6) as pool:
        for pair in pool.map(_resolve_rxte_pair, RXTE_TARGETS):
            cohort_rows.extend(pair)

    # 4. ESO Orbits #193-#198 (N=5 distinct nights = 30 FITS) + 2 <10 pc UVES
    orb_json: dict[str, Any] = {"schema": "D108_ORBITAL_CAMPAIGNS_AND_KINEMATICS", "campaigns": {}}

    def _resolve_eso_orbit(spec: dict[str, Any]) -> list[dict[str, Any]]:
        st = spec["star"]
        _check_new_sep(st, spec["ra"], spec["dec"])
        brand_new_meta[st] = (spec["ra"], spec["dec"])
        q = f"""SELECT TOP 1500 dp_id, target_name, s_ra, s_dec, t_min, t_exptime, em_min, em_max, em_res_power
FROM ivoa.ObsCore
WHERE 1=CONTAINS(POINT('ICRS', s_ra, s_dec), CIRCLE('ICRS', {spec['ra']}, {spec['dec']}, 0.03))
AND {spec['eso_col']} AND dataproduct_type='spectrum' AND access_url IS NOT NULL AND obs_release_date < '2026-04-01'"""
        rows = _tap_vot("https://archive.eso.org/tap_obs/sync", q, timeout=30)
        by_night: dict[int, dict[str, Any]] = {}
        for r in rows:
            dp = str(r["dp_id"])
            if dp in prior_dp or dp in fmt_set:
                continue
            mjd = float(r["t_min"])
            expt = float(r["t_exptime"])
            if expt < 15.0:
                continue
            nk = int(mjd)
            if nk not in by_night or expt > float(by_night[nk]["t_exptime"]):
                by_night[nk] = r
        assert len(by_night) >= 5, f"Only {len(by_night)} nights for {st}"
        cands = sorted(by_night.values(), key=lambda x: float(x["t_min"]))
        # Pick 5 well-spaced distinct nights spanning longest baseline + phase diversity
        idxs = [int(round(k * (len(cands) - 1) / 4.0)) for k in range(5)]
        chosen = [cands[k] for k in idxs]
        assert len({int(float(c["t_min"])) for c in chosen}) == 5
        url_list = [f"https://dataportal.eso.org/dataportal_new/file/{str(c['dp_id'])}" for c in chosen]
        sz_list = [_http_head(u) for u in url_list]
        out = []
        d_mjd, rvs = [], []
        for rank, (c, u, sz) in enumerate(zip(chosen, url_list, sz_list), 1):
            dp = str(c["dp_id"])
            mjd = float(c["t_min"])
            sph, pwin, prv = _kepler_rv(mjd, spec["t0_mjd"], spec["P_d"], spec["ecc"], spec["omega"], spec["k_kms"])
            d_mjd.append(mjd)
            rvs.append(prv)
            out.append(_make_row(
                spec["inst"], st, spec["common_name"], "SCIENCE", "KEPLERIAN_ORBIT_CAMPAIGN", f"ORBITAL_CAMPAIGN_V66_{spec['campaign_order']}",
                False, False, spec["gaia_id"], spec["ra"], spec["dec"], spec["pmra"], spec["pmdec"],
                spec["dist_pc"], False, spec["gmag"], spec["bp"], spec["rp"], spec["j"], spec["h"], spec["ks"],
                spec["teff"], spec["mass"], spec["rv"], spec["n_pl"], bool(spec.get("transit", False)),
                rank, dp, spec["grating"], spec["res_p"], mjd, float(c["t_exptime"]), pwin, sph, prv,
                dp, f"{spec['inst']}/{st}/{dp}.fits", u, sz, [],
            ))
        orb_json["campaigns"][st] = {
            "campaign_order": spec["campaign_order"], "star": st, "common_name": spec["common_name"],
            "instrument": spec["inst"], "n_epochs": 5, "n_distinct_nights": 5,
            "baseline_days": round(max(d_mjd) - min(d_mjd), 3),
            "orb_per_days": spec["P_d"], "orb_ecc": spec["ecc"], "orb_omega_deg": spec["omega"],
            "kp_kms": spec["k_kms"], "orbital_dv_span_kms": round(max(rvs) - min(rvs), 6),
        }
        return out

    print("Resolving 6 ESO Orbits #193-#198 (30 FITS across 5 distinct nights each)...")
    for o_spec in ESO_ORBIT_SPECS:
        used_stars.add(o_spec["star"])
        cohort_rows.extend(_resolve_eso_orbit(o_spec))
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_json, indent=2) + "\n", encoding="utf-8")

    print("Resolving 2 <10 pc ESO_UVES targets (WD0435_088, LP655_48)...")
    lp_detuid = ""
    for uv in ESO_UVES_10PC:
        st = uv["star"]
        used_stars.add(st)
        _check_new_sep(st, uv["ra"], uv["dec"])
        brand_new_meta[st] = (uv["ra"], uv["dec"])
        q = f"""SELECT TOP 20 dp_id, target_name, s_ra, s_dec, t_min, t_exptime, em_min, em_max, em_res_power
FROM ivoa.ObsCore
WHERE 1=CONTAINS(POINT('ICRS', s_ra, s_dec), CIRCLE('ICRS', {uv['ra']}, {uv['dec']}, 0.03))
AND instrument_name='UVES' AND dataproduct_type='spectrum' AND access_url IS NOT NULL AND obs_release_date < '2026-04-01'"""
        rows = sorted([r for r in _tap_vot("https://archive.eso.org/tap_obs/sync", q) if str(r["dp_id"]) not in prior_dp and str(r["dp_id"]) not in fmt_set], key=lambda x: (float(x["t_min"]), float(x["em_min"])))
        assert rows, f"No UVES spectra for {st}"
        for rank, c in enumerate(rows, 1):
            dp = str(c["dp_id"])
            u = f"https://dataportal.eso.org/dataportal_new/file/{dp}"
            sz = _http_head(u)
            elo_nm, ehi_nm = round(float(c["em_min"]) * 1e9), round(float(c["em_max"]) * 1e9)
            cohort_rows.append(_make_row(
                "ESO_UVES", st, uv["common_name"], uv["role"], uv["subrole"], uv["track"],
                uv["bridge_d108"], False, uv["gaia_id"], uv["ra"], uv["dec"], uv["pmra"], uv["pmdec"],
                uv["dist_pc"], True, uv["gmag"], uv["bp"], uv["rp"], uv["j"], uv["h"], uv["ks"],
                uv["teff"], uv["mass"], uv["rv"], 0, False, rank, dp, f"UVES_{elo_nm}_{ehi_nm}NM",
                float(c["em_res_power"] or 42000.0), float(c["t_min"]), float(c["t_exptime"]), "NONE", 0.0, 0.0,
                dp, f"ESO_UVES/{st}/{dp}.fits", u, sz, [],
            ))
        if uv["bridge_d108"]:
            lp_detuid = uv["detuid"]

    # 5. SRG/eROSITA-DE DR1 HamStar: 24 prior bridges + LP655_48 + 3 brand-new <10 pc + 83 brand-new 10-20 pc = 111
    print("Streaming HamStar v1.1 FITS catalog and verifying live eROSITA SourceProducts URLs...")
    raw_hs = urllib.request.urlopen(urllib.request.Request(HAMSTAR_URL, headers={"User-Agent": "SETI-D108-Stage1/1.0"}), timeout=90).read()
    tf = tarfile.open(fileobj=io.BytesIO(raw_hs), mode="r:gz")
    mem = [m for m in tf.getmembers() if m.name.endswith(".fits")][0]
    hs = fits.open(io.BytesIO(tf.extractfile(mem).read()), memmap=False)[1].data

    plx = np.asarray(hs["PLX"], dtype=np.float64)
    ra_a = np.asarray(hs["CTP_RA"], dtype=np.float64)
    dec_a = np.asarray(hs["CTP_DEC"], dtype=np.float64)
    fx_a = np.asarray(hs["Fx"], dtype=np.float64)
    valid = np.where(np.isfinite(plx) & (plx > 0) & np.isfinite(ra_a) & np.isfinite(dec_a))[0]
    ra_r, dec_r = np.radians(ra_a[valid]), np.radians(dec_a[valid])
    sd, cd = np.sin(dec_r), np.cos(dec_r)

    def _min_sep_mat(lats_deg: list[float], lons_deg: list[float]) -> tuple[np.ndarray, np.ndarray]:
        lp = np.radians(lons_deg)[:, None]
        dp = np.radians(lats_deg)[:, None]
        sp, cp = np.sin(dp), np.cos(dp)
        ms = np.empty(len(valid))
        mi = np.empty(len(valid), dtype=np.int32)
        for s0 in range(0, len(valid), 5000):
            s1 = min(len(valid), s0 + 5000)
            ca = np.clip(sp * sd[None, s0:s1] + cp * cd[None, s0:s1] * np.cos(lp - ra_r[None, s0:s1]), -1.0, 1.0)
            ang = np.degrees(np.arccos(ca)) * 3600.0
            k = np.argmin(ang, axis=0)
            mi[s0:s1] = k
            ms[s0:s1] = ang[k, np.arange(s1 - s0)]
        return ms, mi

    s_prior, _ = _min_sep_mat([p["dec_deg"] for p in prior_coords], [p["ra_deg"] for p in prior_coords])
    u_names = sorted(u904.keys())
    s_u, i_u = _min_sep_mat([star_coords[s][1] for s in u_names], [star_coords[s][0] for s in u_names])

    br_by_star: dict[str, tuple[Any, float, float]] = {}
    new10_pool: list[tuple[Any, float]] = []
    new20_pool: list[tuple[Any, float]] = []
    lp_row = None

    for j, idx in enumerate(valid):
        row = hs[idx]
        du = str(row["ERO_DETUID"]).strip()
        if not du.startswith("em01_"):
            continue
        if du == lp_detuid:
            lp_row = row
            continue
        fval = float(fx_a[idx]) if math.isfinite(fx_a[idx]) else 0.0
        dist = 1000.0 / float(plx[idx])
        if s_u[j] <= 35.0:
            st = u_names[i_u[j]]
            if st not in br_by_star or fval > br_by_star[st][1]:
                br_by_star[st] = (row, fval, float(s_u[j]))
        elif s_prior[j] >= 600.0 and s_u[j] >= 600.0:
            if all(_ang_sep_arcsec(float(ra_a[idx]), float(dec_a[idx]), bn[0], bn[1]) >= 600.0 for bn in brand_new_meta.values()):
                if dist <= 10.0:
                    new10_pool.append((row, fval))
                elif dist <= 20.0:
                    new20_pool.append((row, fval))

    assert lp_row is not None, f"Missing LP 655-48 {lp_detuid} in HamStar"
    # Deduplicate 24 prior bridges by ERO_DETUID
    dir_cache: dict[str, list[str]] = {}

    def _resolve_sp_url(du: str) -> tuple[str, int] | None:
        pref, rrr, sss = du[:4], du[5:8], du[8:11]
        ml_id = int(du.split("_ML")[1][:5])
        base = f"https://erosita.mpe.mpg.de/erodat/data/download/{sss}/{rrr}/SOU_010/"
        if base not in dir_cache:
            try:
                html = urllib.request.urlopen(base, timeout=15).read().decode("utf-8", "replace")
                dir_cache[base] = sorted(set(d.strip("/") for d in re.findall(r'href="([0-9]{2}/)"', html)))
            except Exception:
                dir_cache[base] = ["01", "02", "03"]
        fn = f"{pref}_{rrr}{sss}_000_SourceProducts_{ml_id:05d}_c010.tar.xz"
        for sd_k in dir_cache[base]:
            u = f"{base}{sd_k}/{fn}"
            try:
                sz = _http_head(u)
                if sz > 10000:
                    return u, sz
            except Exception:
                pass
        return None

    ero_picks: list[tuple[str, Any, bool, bool, str, int, str]] = []
    seen_du: set[str] = set()
    # 24 Prior Bridges
    for st, (row, fval, _) in sorted(br_by_star.items(), key=lambda kv: -kv[1][1]):
        du = str(row["ERO_DETUID"]).strip()
        if du in seen_du:
            continue
        sp = _resolve_sp_url(du)
        if sp is None:
            continue
        seen_du.add(du)
        ero_picks.append((st, row, True, True, sp[0], sp[1], "BRIDGE"))
        if len(ero_picks) == 24:
            break
    assert len(ero_picks) == 24

    # LP 655-48 intra-D108 bridge (< 10 pc)
    sp_lp = _resolve_sp_url(lp_detuid)
    assert sp_lp is not None
    seen_du.add(lp_detuid)
    ero_picks.append(("LP655_48", lp_row, True, False, sp_lp[0], sp_lp[1], "INTRA_D108_10PC"))

    # 3 Brand-new < 10 pc stars
    new10_pool.sort(key=lambda x: 1000.0 / float(x[0]["PLX"]))
    for row, fval in new10_pool:
        du = str(row["ERO_DETUID"]).strip()
        if du in seen_du:
            continue
        ra_e, dec_e = float(row["CTP_RA"]), float(row["CTP_DEC"])
        if any(_ang_sep_arcsec(ra_e, dec_e, bn[0], bn[1]) < 600.0 for bn in brand_new_meta.values()):
            continue
        sp = _resolve_sp_url(du)
        if sp is None:
            continue
        seen_du.add(du)
        st = _make_canonical_star_from_hamstar(du, str(row["CTP_ID"]), str(row["SIMBAD_NAME"]), used_stars)
        brand_new_meta[st] = (ra_e, dec_e)
        ero_picks.append((st, row, False, False, sp[0], sp[1], "NEW_10PC"))
    assert sum(1 for x in ero_picks if x[6] == "NEW_10PC") == 3

    # 83 Brand-new 10-20 pc stars -> exact total brand-new = 100!
    need_20 = 100 - len(brand_new_meta)
    assert need_20 == 83, f"Expected need_20=83, got {need_20}"
    new20_pool.sort(key=lambda x: -x[1])
    for row, fval in new20_pool:
        du = str(row["ERO_DETUID"]).strip()
        if du in seen_du:
            continue
        ra_e, dec_e = float(row["CTP_RA"]), float(row["CTP_DEC"])
        if any(_ang_sep_arcsec(ra_e, dec_e, bn[0], bn[1]) < 600.0 for bn in brand_new_meta.values()):
            continue
        sp = _resolve_sp_url(du)
        if sp is None:
            continue
        seen_du.add(du)
        st = _make_canonical_star_from_hamstar(du, str(row["CTP_ID"]), str(row["SIMBAD_NAME"]), used_stars)
        brand_new_meta[st] = (ra_e, dec_e)
        ero_picks.append((st, row, False, False, sp[0], sp[1], "NEW_20PC"))
        if sum(1 for x in ero_picks if x[6] == "NEW_20PC") == need_20:
            break
    assert len(brand_new_meta) == 100, f"Brand-new unique stars must equal 100, got {len(brand_new_meta)}"

    for st, row, is_br, is_prior_br, sp_url, sp_bytes, tag in ero_picks:
        du = str(row["ERO_DETUID"]).strip()
        cid = str(row["CTP_ID"]).strip()
        sim = str(row["SIMBAD_NAME"]).strip().lstrip("* ").strip()
        g_v = float(row["G"]) if math.isfinite(row["G"]) else None
        bprp = float(row["BP_RP"]) if math.isfinite(row["BP_RP"]) else 1.5
        if is_prior_br:
            ru = u904[st]
            ra_e, dec_e = star_coords[st]
            dist = float(ru["dist_pc"])
            cname = ru["common_name"]
            role = ru["role"]
            subrole = "EROSITA_DR1_CORONAL_BRIDGE"
            track = "SOFT_XRAY_EROSITA_DR1_BRIDGE"
            teff = float(ru["teff_k"] or _estimate_teff_from_bprp(bprp))
            n_pl = int(float(ru["n_exoplanets"] or 0))
            w10 = ru["within_10pc"] == "True"
        else:
            ra_e, dec_e = float(row["CTP_RA"]), float(row["CTP_DEC"])
            dist = 1000.0 / float(row["PLX"])
            if tag == "INTRA_D108_10PC":
                cname = "LP 655-48 (<10 pc M6V + eROSITA Bridge)"
                role, subrole, track, teff = "SCIENCE", "SUB10PC_MDWARF_UVES_EROSITA", "SOLAR_NEIGHBORHOOD_10PC_UVES_EROSITA_BRIDGE", 2850.0
            elif tag == "NEW_10PC":
                lbl = sim or f"Gaia DR3 {cid}"
                cname = f"{lbl} (eROSITA DR1 <10 pc)"
                role, subrole, track, teff = "SCIENCE", "SUB10PC_EROSITA_DR1_CORONAL", "SOLAR_NEIGHBORHOOD_10PC_EROSITA_DR1", _estimate_teff_from_bprp(bprp)
            else:
                lbl = sim or f"Gaia DR3 {cid}"
                cname = f"{lbl} (eROSITA DR1 10-20 pc)"
                role, subrole, track, teff = "SCIENCE", "EROSITA_DR1_CORONAL_20PC", "EROSITA_DR1_HAMSTAR_CORONAL_SURVEY", _estimate_teff_from_bprp(bprp)
            n_pl = 0
            w10 = dist <= 10.0
        fn = sp_url.split("/")[-1]
        mjd = float(row["ERO_MJD"]) if math.isfinite(row["ERO_MJD"]) else 58900.0
        cohort_rows.append(_make_row(
            "EROSITA_DR1", st, cname, role, subrole, track,
            is_br, is_prior_br, cid, ra_e, dec_e, 0.0, 0.0, dist, w10, g_v, None, None, None, None, None,
            teff, 0.6, 0.0, n_pl, False, 1, f"EROSITA_DR1_{du}_{st}", "EROSITA_TM1_7_0P2_8KEV",
            17.0, mjd, 250.0, "NONE", 0.0, 0.0, du, f"EROSITA_DR1/{st}/{fn}", sp_url, sp_bytes, [],
        ))

    # Write FROZEN_COHORT_D108.csv
    with (WS / "FROZEN_COHORT_D108.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COHORT_COLS)
        w.writeheader()
        for r in cohort_rows:
            w.writerow(r)

    # Verify exclusion & separations
    new_dp_ids = [r["dp_id"] for r in cohort_rows]
    overlap = sorted((set(new_dp_ids) & prior_dp) | (set(new_dp_ids) & fmt_set))
    assert not overlap, f"dp_id overlap detected: {overlap}"

    star_sep_ver = []
    min_prior_sep = 1e9
    for st in sorted(brand_new_meta):
        ra1, dec1 = brand_new_meta[st]
        best_s, best_n = 1e9, ""
        for pc in prior_coords:
            s = _ang_sep_arcsec(ra1, dec1, pc["ra_deg"], pc["dec_deg"])
            if s < best_s:
                best_s, best_n = s, pc["canonical_target"]
        min_prior_sep = min(min_prior_sep, best_s)
        star_sep_ver.append({"star": st, "min_prior_sep_arcsec": round(best_s, 2), "nearest_prior": best_n})

    bn_list = sorted(brand_new_meta.items())
    min_intra = 1e9
    for i, (s1, (r1, d1)) in enumerate(bn_list):
        for j in range(i + 1, len(bn_list)):
            s2, (r2, d2) = bn_list[j]
            s = _ang_sep_arcsec(r1, d1, r2, d2)
            min_intra = min(min_intra, s)
            assert s >= 600.0, f"Intra-D108 overlap {s1} vs {s2}: {s:.2f}''"

    uniq_phys: dict[str, int] = {}
    for r in cohort_rows:
        uniq_phys[r["f1_rel"]] = int(r["f1_bytes"])
        for ex in json.loads(r["extra_files"]):
            uniq_phys[ex["rel"]] = int(ex["bytes"])
    proj_bytes = sum(uniq_phys.values())

    prior_bridge_stars = sorted({r["canonical_target"] for r in cohort_rows if r["is_prior_bridge"] == "True"})
    sci_stars = {r["canonical_target"] for r in cohort_rows if r["role"] == "SCIENCE"}
    ctrl_stars = {r["canonical_target"] for r in cohort_rows if r["role"] == "CONTROL"}
    new_10pc_cnt = sum(1 for st in brand_new_meta if any(r["canonical_target"] == st and r["within_10pc"] == "True" for r in cohort_rows))

    pex_out = {
        "schema": "D108_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D108",
        "verified_utc": datetime.now(timezone.utc).isoformat(),
        "prior_phases_covered": "D001-D107 (Companion Archives A-AG)",
        "n_prior_excluded_coords": len(prior_coords),
        "n_prior_excluded_dp_ids": len(prior_dp),
        "n_format_check_excluded_dp_ids": len(fmt_probes),
        "d108_total_stars": len(brand_new_meta) + len(prior_bridge_stars),
        "d108_brand_new_unique_stars": len(brand_new_meta),
        "d108_prior_bridge_stars": len(prior_bridge_stars),
        "d108_science_stars": len(sci_stars),
        "d108_control_stars": len(ctrl_stars),
        "d108_brand_new_within_10pc": new_10pc_cnt,
        "d108_total_observations": len(cohort_rows),
        "d108_total_physical_files": len(uniq_phys),
        "d108_projected_download_bytes": proj_bytes,
        "d108_projected_download_mib": round(proj_bytes / (1024.0 * 1024.0), 3),
        "d108_dp_id_overlap_count": len(overlap),
        "min_brand_new_sky_separation_arcsec": round(min_prior_sep, 2),
        "min_intra_d108_separation_arcsec": round(min_intra, 2),
        "star_separation_verification": star_sep_ver,
        "format_check_excluded_dp_ids": fmt_probes,
        "excluded_dp_ids": sorted(prior_dp),
        "excluded_targets_coordinate_registry": prior_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pex_out, indent=2) + "\n", encoding="utf-8")

    # Stage-1 Seal (7 immutable Stage-1 files -> METHOD_LOCK.json -> LOCK_RECEIPT.json)
    assert not RAW_DIR.exists(), f"{RAW_DIR} appeared before seal!"
    now_epoch = time.time()
    now_utc = datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat()
    stage1_names = [
        "v6_6_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D108.csv",
        "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "PRIOR_V6_5_PHASES_SNAPSHOT.json",
    ]
    stage1_hashes = {fn: _sha256_file(WS / fn) for fn in stage1_names}

    ml = {
        "schema": "D108_METHOD_LOCK",
        "phase_id": "D108",
        "detector": DETECTOR_NAME,
        "locked_utc": now_utc,
        "locked_unix_epoch": round(now_epoch, 4),
        "d108_brand_new_stars": len(brand_new_meta),
        "d108_prior_bridges": len(prior_bridge_stars),
        "d108_total_observations": len(cohort_rows),
        "d108_total_physical_files": len(uniq_phys),
        "d108_projected_download_mib": round(proj_bytes / (1024.0 * 1024.0), 3),
        "calibration_suites_new": {
            "IXPE_240": 240, "EROSITA_240": 240, "RXTE_HEXTE_180": 180, "RXTE_PCA_180": 180,
        },
        "stage_1_files": stage1_hashes,
    }
    (WS / "METHOD_LOCK.json").write_text(json.dumps(ml, indent=2) + "\n", encoding="utf-8")
    ml_sha = _sha256_file(WS / "METHOD_LOCK.json")

    lr = {
        "schema": "D108_LOCK_RECEIPT",
        "phase_id": "D108",
        "status": "STAGE-1 SEALED",
        "locked_utc": now_utc,
        "locked_unix_epoch": round(now_epoch, 4),
        "inputs_dir_exists_at_seal": RAW_DIR.exists(),
        "method_lock_sha256": ml_sha,
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lr, indent=2) + "\n", encoding="utf-8")
    print(f"STAGE-1 SEALED: new_stars={len(brand_new_meta)} (10pc={new_10pc_cnt}), bridges={len(prior_bridge_stars)}, obs={len(cohort_rows)}, phys_files={len(uniq_phys)}, proj_mib={proj_bytes/1048576:.2f}, min_prior_sep={min_prior_sep:.1f}'', min_intra_sep={min_intra:.1f}''")


if __name__ == "__main__":
    main()
