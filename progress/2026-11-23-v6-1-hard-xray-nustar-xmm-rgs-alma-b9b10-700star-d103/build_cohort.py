#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Stage-1 Prospective Method Lock & Cohort Freeze for Phase D103 (V6.1):
  - Enforces 0 dp_id overlap against all 3,368 prior dp_ids (C001-C037 + D001-D102)
    plus all 26 format-check excluded probe IDs (incl. NuSTAR 10002001001/2 & XMM 0111180201).
  - Enforces >= 300.0" sky separation against all 729 cumulative prior coordinates
    (686 pre-D102 + 43 brand-new D102) for every brand-new D103 star.
  - Freezes 104 physical observations (187 files across NUSTAR_FPMA_FPMB, XMM_RGS,
    ALMA B9/B10, ESO ESPRESSO/HARPS Orbits #163-#168 + <=10.12pc 0-pl Controls).
  - Refuses execution if $RAW103 already exists prior to METHOD_LOCK + LOCK_RECEIPT seal.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import urllib.parse
import zipfile
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent
ROOT = WS.parent.parent
WS102 = ROOT / "analysis_workspace/work_v6_0_20261123_d102_xray_euv_poisson_chandra_euve_alma_unbroken_mm"
RAW_DIR = ROOT / "inputs_d103_v6_1"

ARCHIVE_AB_NAME = "SETI_D102_V6_0_XRAY_EUV_POISSON_CHANDRA_EUVE_ALMA_UNBROKEN_MM_RESULTS_2026-11-23.zip"
ARCHIVE_AB_SHA256 = "684d6828063cf17b8adcd666932633c07196e8764038dbbdd3a48bdd5433ca2c"
ARCHIVE_AB_BUNDLE_MEMBER = "work_v6_0_20261123_d102_xray_euv_poisson_chandra_euve_alma_unbroken_mm/bounded_inputs/d102_bounded_bundle.json.gz"
ARCHIVE_AB_BUNDLE_SHA256 = "b1979cde20276543ed30d9ca99098374050530b5934490c44c8b765dffc6d8bf"

FORMAT_CHECK_PROBES_D103 = [
    "0111180201",
    "XMM_0111180201",
    "10002001001",
    "10002001002",
    "NUSTAR_10002001001",
    "NUSTAR_10002001002",
]

FROZEN_HEADER = [
    "instrument", "canonical_target", "common_name", "role", "subrole", "science_track",
    "panchromatic_bridge", "is_prior_bridge", "gaia_source_id", "s_ra", "s_dec",
    "pmra_mas_yr", "pmdec_mas_yr", "dist_pc", "within_10pc",
    "phot_g_mag", "phot_bp_mag", "phot_rp_mag", "j_mag", "h_mag", "ks_mag",
    "teff_k", "mh_dex", "stellar_mass_msun", "prior_rv_kms", "n_exoplanets", "has_transiting_planet",
    "ecliptic_lat_deg", "sn1987a_dt_days", "gw170817_dt_days", "sn2023ixf_dt_days", "ppo_align_score",
    "epoch_rank", "dp_id", "grating", "resolving_power", "mjd_obs", "t_exptime",
    "phase_window", "signed_phase", "planet_orbital_rv_kms",
    "f1_id", "f1_rel", "f1_url", "f1_bytes", "total_bytes", "extra_files",
]

# Verified astrophysical metadata for all 51 brand-new D103 systems
NEW_META: dict[str, dict[str, Any]] = {
    # --- 6 ESO Exoplanet Orbital Campaigns (#163-#168) ---
    "HD134987": {
        "common_name": "HD 134987", "role": "SCIENCE", "ra": 228.367540, "dec": -25.309672,
        "dist_pc": 26.1804, "teff_k": 5585.0, "n_pl": 2, "mass": 1.10, "mh": 0.28, "rv": 5.206, "gmag": "6.29",
    },
    "HD82943": {
        "common_name": "HD 82943", "role": "SCIENCE", "ra": 143.71140, "dec": -12.13030,
        "dist_pc": 27.59, "teff_k": 5935.0, "n_pl": 2, "mass": 1.08, "mh": 0.26, "rv": 8.1, "gmag": "6.4",
    },
    "HD196067": {
        "common_name": "HD 196067", "role": "SCIENCE", "ra": 310.43642, "dec": -75.35150,
        "dist_pc": 39.93, "teff_k": 6072.0, "n_pl": 2, "mass": 1.16, "mh": 0.213, "rv": -11.3, "gmag": "5.9",
    },
    "HD10180": {
        "common_name": "HD 10180", "role": "SCIENCE", "ra": 24.47311, "dec": -60.51149,
        "dist_pc": 38.96, "teff_k": 5911.0, "n_pl": 6, "mass": 1.06, "mh": 0.08, "rv": 35.5, "gmag": "7.2",
    },
    "HD134060": {
        "common_name": "HD 134060", "role": "SCIENCE", "ra": 227.68476, "dec": -61.42237,
        "dist_pc": 24.01, "teff_k": 5966.0, "n_pl": 2, "mass": 1.095, "mh": 0.14, "rv": 38.1, "gmag": "6.1",
    },
    "BD210397": {
        "common_name": "BD-21 0397", "role": "SCIENCE", "ra": 33.30242, "dec": -21.19621,
        "dist_pc": 23.73, "teff_k": 4051.0, "n_pl": 2, "mass": 0.69, "mh": 0.12, "rv": 27.6, "gmag": "9.3",
    },
    # --- 8 ESO <= 10.12 pc 0-planet CONTROL stars (5 strictly <= 10.0 pc) ---
    "GJ257A": {
        "common_name": "GJ 257 A", "role": "CONTROL", "ra": 104.437330, "dec": -44.291396,
        "dist_pc": 8.028, "teff_k": 3180.0, "n_pl": 0, "mass": 0.36, "mh": -0.2, "rv": 4.2, "gmag": "10.42",
        "gaia": "5559035514779971456",
    },
    "HD32450A": {
        "common_name": "HD 32450 A", "role": "CONTROL", "ra": 75.617831, "dec": -21.257878,
        "dist_pc": 8.363, "teff_k": 3800.0, "n_pl": 0, "mass": 0.56, "mh": -0.1, "rv": -15.2, "gmag": "7.79",
        "gaia": "2974726131970829952",
    },
    "PMJ19070P2053": {
        "common_name": "Ross 730 / GJ 1230", "role": "CONTROL", "ra": 286.770911, "dec": 20.886488,
        "dist_pc": 8.830, "teff_k": 3228.0, "n_pl": 0, "mass": 0.32, "mh": -0.3, "rv": 32.01, "gmag": "9.81",
        "gaia": "4519789321942643072",
    },
    "GJ867A": {
        "common_name": "FK Aqr (GJ 867 A)", "role": "CONTROL", "ra": 339.690688, "dec": -20.614689,
        "dist_pc": 8.851, "teff_k": 3060.0, "n_pl": 0, "mass": 0.45, "mh": -0.1, "rv": -5.95, "gmag": "10.21",
        "gaia": "2400808245117576704",
    },
    "LHS1731": {
        "common_name": "LHS 1731", "role": "CONTROL", "ra": 75.832622, "dec": -17.375510,
        "dist_pc": 9.236, "teff_k": 3350.0, "n_pl": 0, "mass": 0.37, "mh": -0.2, "rv": 14.76, "gmag": "10.56",
        "gaia": "2976850598890749824",
    },
    "L480_69": {
        "common_name": "L 480-69", "role": "CONTROL", "ra": 234.141789, "dec": -37.909940,
        "dist_pc": 10.082, "teff_k": 3003.0, "n_pl": 0, "mass": 0.25, "mh": -0.3, "rv": -63.01, "gmag": "11.37",
        "gaia": "6012446244330608768",
    },
    "LTT9759": {
        "common_name": "LTT 9759 (HD 223889)", "role": "CONTROL", "ra": 358.463174, "dec": -75.634219,
        "dist_pc": 10.116, "teff_k": 3254.0, "n_pl": 0, "mass": 0.40, "mh": -0.2, "rv": -9.47, "gmag": "9.01",
        "gaia": "6377828354964753792",
    },
    "GL678_1A": {
        "common_name": "Gl 678.1 A", "role": "CONTROL", "ra": 262.594834, "dec": 5.547410,
        "dist_pc": 10.117, "teff_k": 3755.0, "n_pl": 0, "mass": 0.57, "mh": -0.06, "rv": -12.95, "gmag": "8.53",
        "gaia": "4389844948935164544",
    },
    # --- XMM_RGS / NuSTAR Multi-Mission Brand-New Stars ---
    "EKDRA": {
        "common_name": "EK Dra", "role": "SCIENCE", "ra": 219.75087, "dec": 64.29164,
        "dist_pc": 33.94, "teff_k": 5700.0, "n_pl": 0, "mass": 0.95, "mh": 0.0, "rv": -21.12, "gmag": "7.52",
        "gaia": "1668690628102524672",
    },
    "HD110432": {
        "common_name": "HD 110432 (BZ Cru)", "role": "SCIENCE", "ra": 190.70942, "dec": -63.05861,
        "dist_pc": 301.20, "teff_k": 25000.0, "n_pl": 0, "mass": 9.6, "mh": 0.0, "rv": 8.0, "gmag": "5.14",
        "gaia": "6055103928246312960",
    },
    "RYTAU": {
        "common_name": "RY Tau", "role": "SCIENCE", "ra": 65.48921, "dec": 28.44319,
        "dist_pc": 138.22, "teff_k": 5920.0, "n_pl": 0, "mass": 2.0, "mh": 0.0, "rv": 17.6, "gmag": "10.71",
        "gaia": "164551162164119424",
    },
    "SIGMAGEM": {
        "common_name": "Sigma Geminorum", "role": "SCIENCE", "ra": 115.82792, "dec": 28.88350,
        "dist_pc": 37.48, "teff_k": 4570.0, "n_pl": 0, "mass": 1.28, "mh": 0.0, "rv": 45.8, "gmag": "3.97",
    },
    "RZCAS": {
        "common_name": "RZ Cassiopeiae", "role": "SCIENCE", "ra": 42.23129, "dec": 69.63428,
        "dist_pc": 62.54, "teff_k": 8600.0, "n_pl": 0, "mass": 2.2, "mh": 0.0, "rv": -38.0, "gmag": "6.23",
    },
    "XYUMA": {
        "common_name": "XY UMa", "role": "SCIENCE", "ra": 137.48296, "dec": 54.48803,
        "dist_pc": 66.27, "teff_k": 5200.0, "n_pl": 0, "mass": 1.0, "mh": 0.0, "rv": -10.5, "gmag": "9.37",
    },
    "BPTAU": {
        "common_name": "BP Tau", "role": "SCIENCE", "ra": 64.81583, "dec": 29.10747,
        "dist_pc": 127.40, "teff_k": 4040.0, "n_pl": 0, "mass": 0.7, "mh": 0.0, "rv": 15.8, "gmag": "11.46",
    },
    "DNTAU": {
        "common_name": "DN Tau", "role": "SCIENCE", "ra": 68.86404, "dec": 24.24969,
        "dist_pc": 128.60, "teff_k": 3880.0, "n_pl": 0, "mass": 0.65, "mh": 0.0, "rv": 16.5, "gmag": "11.46",
    },
    "BETACMA": {
        "common_name": "Beta CMa (Mirzam)", "role": "SCIENCE", "ra": 95.67492, "dec": -17.95592,
        "dist_pc": 153.14, "teff_k": 23150.0, "n_pl": 0, "mass": 13.5, "mh": 0.0, "rv": 33.7, "gmag": "1.98",
    },
    "BETACRU": {
        "common_name": "Beta Crucis (Mimosa)", "role": "SCIENCE", "ra": 191.93025, "dec": -59.68875,
        "dist_pc": 108.11, "teff_k": 27000.0, "n_pl": 0, "mass": 16.0, "mh": 0.0, "rv": 15.6, "gmag": "1.25",
    },
    "SIGMASCO": {
        "common_name": "Sigma Scorpii (Alniyat)", "role": "SCIENCE", "ra": 245.29713, "dec": -25.59278,
        "dist_pc": 225.23, "teff_k": 26150.0, "n_pl": 0, "mass": 18.0, "mh": 0.0, "rv": 2.5, "gmag": "2.90",
    },
    "GAMMALUP": {
        "common_name": "Gamma Lupi", "role": "SCIENCE", "ra": 233.78520, "dec": -41.16675,
        "dist_pc": 173.91, "teff_k": 20900.0, "n_pl": 0, "mass": 9.0, "mh": 0.0, "rv": 2.3, "gmag": "2.80",
    },
    "ZETAPUP": {
        "common_name": "Zeta Puppis (Naos)", "role": "SCIENCE", "ra": 120.89604, "dec": -40.00314,
        "dist_pc": 429.18, "teff_k": 40000.0, "n_pl": 0, "mass": 22.5, "mh": 0.0, "rv": -24.0, "gmag": "2.21",
    },
    "NGC4593": {
        "common_name": "NGC 4593", "role": "CONTROL", "ra": 189.91454, "dec": -5.34421,
        "dist_pc": 38000000.0, "teff_k": 5500.0, "n_pl": 0, "mass": 1.0, "mh": 0.0, "rv": 2700.0, "gmag": "11.7",
    },
    "MRK335": {
        "common_name": "Mrk 335", "role": "CONTROL", "ra": 1.58158, "dec": 20.20294,
        "dist_pc": 110000000.0, "teff_k": 5500.0, "n_pl": 0, "mass": 1.0, "mh": 0.0, "rv": 7730.0, "gmag": "13.8",
    },
    "NGC4449": {
        "common_name": "NGC 4449", "role": "CONTROL", "ra": 187.04632, "dec": 44.09367,
        "dist_pc": 4200000.0, "teff_k": 5500.0, "n_pl": 0, "mass": 1.0, "mh": 0.0, "rv": 207.0, "gmag": "9.6",
    },
    # --- 9 Additional Unique Brand-New NuSTAR Systems ---
    "WR140": {
        "common_name": "WR 140 (HD 193793)", "role": "SCIENCE", "ra": 305.09760, "dec": 43.81820,
        "dist_pc": 1612.90, "teff_k": 45000.0, "n_pl": 0, "mass": 20.0, "mh": 0.0, "rv": -7.5, "gmag": "6.78",
    },
    "HR7355": {
        "common_name": "HR 7355 (V3885 Sgr)", "role": "SCIENCE", "ra": 291.10830, "dec": -27.89160,
        "dist_pc": 403.23, "teff_k": 17500.0, "n_pl": 0, "mass": 6.0, "mh": 0.0, "rv": -15.0, "gmag": "6.03",
    },
    "HR5907": {
        "common_name": "HR 5907 (V1040 Sco)", "role": "SCIENCE", "ra": 238.43690, "dec": -24.00960,
        "dist_pc": 144.50, "teff_k": 17000.0, "n_pl": 0, "mass": 5.5, "mh": 0.0, "rv": -12.0, "gmag": "5.41",
    },
    "HD96670": {
        "common_name": "HD 96670", "role": "SCIENCE", "ra": 166.82590, "dec": -59.90440,
        "dist_pc": 1219.51, "teff_k": 32000.0, "n_pl": 0, "mass": 22.0, "mh": 0.0, "rv": -1.3, "gmag": "7.42",
    },
    "HD93129A": {
        "common_name": "HD 93129 A", "role": "SCIENCE", "ra": 160.90410, "dec": -59.57650,
        "dist_pc": 2300.00, "teff_k": 52000.0, "n_pl": 0, "mass": 95.0, "mh": 0.0, "rv": -5.0, "gmag": "7.2",
    },
    "RHOOPHA": {
        "common_name": "Rho Oph A (S1)", "role": "SCIENCE", "ra": 246.34930, "dec": -23.48340,
        "dist_pc": 136.43, "teff_k": 16000.0, "n_pl": 0, "mass": 5.5, "mh": 0.0, "rv": -7.0, "gmag": "6.75",
    },
    "V648CAR": {
        "common_name": "V648 Car (HD 90657)", "role": "SCIENCE", "ra": 152.80770, "dec": -57.80010,
        "dist_pc": 2300.00, "teff_k": 42000.0, "n_pl": 0, "mass": 25.0, "mh": 0.0, "rv": 2.4, "gmag": "9.6",
    },
    "MRK876": {
        "common_name": "Mrk 876 (PG 1613+658)", "role": "CONTROL", "ra": 243.40790, "dec": 65.67250,
        "dist_pc": 595000000.0, "teff_k": 5500.0, "n_pl": 0, "mass": 1.0, "mh": 0.0, "rv": 38700.0, "gmag": "13.1",
    },
    "NGC7552": {
        "common_name": "NGC 7552", "role": "CONTROL", "ra": 349.07060, "dec": -42.61390,
        "dist_pc": 21000000.0, "teff_k": 5500.0, "n_pl": 0, "mass": 1.0, "mh": 0.0, "rv": 1608.0, "gmag": "10.6",
    },
    # --- 14 Additional Unique Brand-New ALMA Band 9 & Band 10 Systems ---
    "J1211M0118": {
        "common_name": "J1211-0118", "role": "CONTROL", "ra": 182.904633, "dec": -1.304583,
        "dist_pc": 14000000000.0, "teff_k": 5500.0, "n_pl": 0, "mass": 1.0, "mh": 0.0, "rv": 0.0,
    },
    "HERBS103": {
        "common_name": "HerBS-103", "role": "CONTROL", "ra": 343.351000, "dec": -32.584500,
        "dist_pc": 16200000000.0, "teff_k": 5500.0, "n_pl": 0, "mass": 1.0, "mh": 0.0, "rv": 0.0,
    },
    "J0217M0208": {
        "common_name": "J0217-0208", "role": "CONTROL", "ra": 34.340012, "dec": -2.147994,
        "dist_pc": 22000000000.0, "teff_k": 5500.0, "n_pl": 0, "mass": 1.0, "mh": 0.0, "rv": 0.0,
    },
    "IIIZW035": {
        "common_name": "III Zw 035", "role": "CONTROL", "ra": 26.127255, "dec": 17.102378,
        "dist_pc": 119000000.0, "teff_k": 5500.0, "n_pl": 0, "mass": 1.0, "mh": 0.0, "rv": 8225.0,
    },
    "NGC1808": {
        "common_name": "NGC 1808", "role": "CONTROL", "ra": 76.926371, "dec": -37.512736,
        "dist_pc": 10900000.0, "teff_k": 5500.0, "n_pl": 0, "mass": 1.0, "mh": 0.0, "rv": 995.0, "gmag": "9.9",
    },
    "RVAQR": {
        "common_name": "RV Aqr", "role": "SCIENCE", "ra": 316.465570, "dec": -0.211672,
        "dist_pc": 635.24, "teff_k": 2800.0, "n_pl": 0, "mass": 1.2, "mh": 0.0, "rv": -15.0, "gmag": "9.20",
    },
    "WISE2246": {
        "common_name": "WISE J2246-0526", "role": "CONTROL", "ra": 341.531471, "dec": -5.443050,
        "dist_pc": 42000000000.0, "teff_k": 5500.0, "n_pl": 0, "mass": 1.0, "mh": 0.0, "rv": 0.0,
    },
    "AG354": {
        "common_name": "AGAL G354.616+0.472", "role": "CONTROL", "ra": 263.799679, "dec": -33.507166,
        "dist_pc": 1700.0, "teff_k": 5000.0, "n_pl": 0, "mass": 5.0, "mh": 0.0, "rv": -20.0,
    },
    "G205M3": {
        "common_name": "G205.46-14.56 M3", "role": "CONTROL", "ra": 86.524833, "dec": -0.159014,
        "dist_pc": 420.0, "teff_k": 4000.0, "n_pl": 0, "mass": 2.0, "mh": 0.0, "rv": 10.0,
    },
    "J0218M0519": {
        "common_name": "J0218-0519 (SXDF)", "role": "CONTROL", "ra": 34.735567, "dec": -5.333019,
        "dist_pc": 40000000000.0, "teff_k": 5500.0, "n_pl": 0, "mass": 1.0, "mh": 0.0, "rv": 0.0,
    },
    "IRAS08303": {
        "common_name": "IRAS 08303-4303", "role": "CONTROL", "ra": 128.036042, "dec": -43.229531,
        "dist_pc": 700.0, "teff_k": 4500.0, "n_pl": 0, "mass": 2.0, "mh": 0.0, "rv": 14.0,
    },
    "BRI1335": {
        "common_name": "BRI 1335-0417", "role": "CONTROL", "ra": 204.514250, "dec": -4.543000,
        "dist_pc": 40000000000.0, "teff_k": 5500.0, "n_pl": 0, "mass": 1.0, "mh": 0.0, "rv": 0.0,
    },
    "A1689ZD1": {
        "common_name": "A1689-zD1", "role": "CONTROL", "ra": 197.874721, "dec": -1.321881,
        "dist_pc": 72000000000.0, "teff_k": 5500.0, "n_pl": 0, "mass": 1.0, "mh": 0.0, "rv": 0.0,
    },
    "N13PDR": {
        "common_name": "N13 PDR (SMC)", "role": "CONTROL", "ra": 11.361879, "dec": -73.382233,
        "dist_pc": 62000.0, "teff_k": 5000.0, "n_pl": 0, "mass": 5.0, "mh": -0.7, "rv": 145.0,
    },
}

# 19 NuSTAR FPMA+FPMB Pairs (8 Bridges + 11 New)
NUSTAR_SPECS = [
    # (canon, is_bridge, obsid, mjd_obs, exp_a, exp_b, bytes_a, bytes_b)
    ("AUMIC",       True,  "91101320002", 60857.6501,  45212.2,  44728.7,  8689062,  8152409),
    ("BETELGEUSE",  True,  "30501012002", 58718.1814,  49160.7,  48827.4, 11297999, 11017236),
    ("ETACAR",      True,  "30602030004", 59084.5043, 102221.6, 101376.8, 74757111, 68651930),
    ("NGC7469",     True,  "60101001008", 57378.4244,  23483.9,  23427.1,  9734068,  9316921),
    ("NGC5548",     True,  "61001003002", 60707.2647,  52697.1,  52189.3, 25753602, 23919175),
    ("PKS2155",     True,  "11001611004", 60620.6293,  51967.9,  51489.2, 16659816, 15436857),
    ("HD222259A",   True,  "90902319002", 60161.3932,  50178.7,  49727.7, 14230118, 11329579),
    ("CIRCINUSGAL", True,  "80601502001", 59179.2439, 106116.2, 105151.3, 52598514, 46929869),
    ("EKDRA",       False, "31002002014", 60390.2473,  23859.6,  23629.1,  4718604,  4474676),
    ("HD110432",    False, "30501001002", 58685.3793, 106452.5, 105779.2, 33411294, 34031241),
    ("WR140",       False, "30601031002", 59155.5251,  71258.3,  70568.7, 22573051, 21048626),
    ("HR7355",      False, "30401007002", 58391.3897, 107566.0, 107083.5, 23222006, 22690488),
    ("HR5907",      False, "30802001002", 59771.4730,  49973.9,  49543.4, 11510937, 10805306),
    ("HD96670",     False, "30001050006", 57121.9140,  70441.6,  70475.5, 31857030, 20922796),
    ("HD93129A",    False, "30802012002", 59738.0633,  38938.4,  38551.1,  9778228,  9541983),
    ("RHOOPHA",     False, "30601025002", 59105.1293, 136329.3, 135246.9, 38585192, 35180256),
    ("V648CAR",     False, "30201024002", 57761.8307, 115171.6, 114917.6, 37306170, 35011150),
    ("MRK876",      False, "60901028002", 60204.8758, 222586.2, 220241.1, 50370560, 47728640),
    ("NGC7552",     False, "50501001002", 58766.6779, 190963.8, 189758.6, 42160196, 39682418),
]

# 27 XMM-Newton RGS Quadruplets (10 Bridges + 17 Brand-New)
XMM_SPECS = [
    # (canon, is_bridge, obsid, mjd, t1, t2, r1sr, r1bg, r2sr, r2bg, tot_bytes)
    ("AUMIC",       True,  "0822740501", 58405.496343, 137816.0, 137804.0, "P0822740501R1S004SRSPEC1003.FTZ", "P0822740501R1S004BGSPEC1003.FTZ", "P0822740501R2S005SRSPEC1003.FTZ", "P0822740501R2S005BGSPEC1003.FTZ", 91425),
    ("PROXIMACEN",  True,  "0049350101", 52133.158773,  67415.0,  67413.0, "P0049350101R1S004SRSPEC1003.FTZ", "P0049350101R1S004BGSPEC1003.FTZ", "P0049350101R2S005SRSPEC1003.FTZ", "P0049350101R2S005BGSPEC1003.FTZ", 93617),
    ("PROCYON",     True,  "0123940201", 51840.606771,  61417.0,  61420.0, "P0123940201R1S004SRSPEC1003.FTZ", "P0123940201R1S004BGSPEC1003.FTZ", "P0123940201R2S005SRSPEC1003.FTZ", "P0123940201R2S005BGSPEC1003.FTZ", 82291),
    ("ALTAIR",      True,  "0502360101", 54390.940602,  62518.0,  62509.0, "P0502360101R1S004SRSPEC1004.FTZ", "P0502360101R1S004BGSPEC1004.FTZ", "P0502360101R2S005SRSPEC1005.FTZ", "P0502360101R2S005BGSPEC1005.FTZ", 63896),
    ("HD34029",     True,  "0134721501", 53258.831100,  70719.0,  70724.0, "P0134721501R1S007SRSPEC1003.FTZ", "P0134721501R1S007BGSPEC1003.FTZ", "P0134721501R2S008SRSPEC1003.FTZ", "P0134721501R2S008BGSPEC1003.FTZ", 92459),
    ("HD22468",     True,  "0810851101", 60370.780856,  61345.0,  61386.0, "P0810851101R1S004SRSPEC1003.FTZ", "P0810851101R1S004BGSPEC1003.FTZ", "P0810851101R2S005SRSPEC1003.FTZ", "P0810851101R2S005BGSPEC1003.FTZ", 87220),
    ("HD163296",    True,  "0502370201", 54365.014329, 105915.0, 105902.0, "P0502370201R1S001SRSPEC1003.FTZ", "P0502370201R1S001BGSPEC1003.FTZ", "P0502370201R2S004SRSPEC1003.FTZ", "P0502370201R2S004BGSPEC1003.FTZ", 82439),
    ("NGC7469",     True,  "0760350801", 57384.861678, 100509.0, 100511.0, "P0760350801R1S004SRSPEC1001.FTZ", "P0760350801R1S004BGSPEC1001.FTZ", "P0760350801R2S005SRSPEC1001.FTZ", "P0760350801R2S005BGSPEC1001.FTZ", 88780),
    ("NGC4051",     True,  "0960150301", 60812.675752, 131984.0, 132023.0, "P0960150301R1S004SRSPEC1003.FTZ", "P0960150301R1S004BGSPEC1003.FTZ", "P0960150301R2S005SRSPEC1003.FTZ", "P0960150301R2S005BGSPEC1003.FTZ", 95101),
    ("NGC5548",     True,  "0943020101", 60707.282222,  91654.0,  91647.0, "P0943020101R1S004SRSPEC1003.FTZ", "P0943020101R1S004BGSPEC1003.FTZ", "P0943020101R2S005SRSPEC1003.FTZ", "P0943020101R2S005BGSPEC1003.FTZ", 82100),
    ("LTT9759",     False, "0900940101", 59705.916991,  87412.0,  87405.0, "P0900940101R1S004SRSPEC1003.FTZ", "P0900940101R1S004BGSPEC1003.FTZ", "P0900940101R2S005SRSPEC1003.FTZ", "P0900940101R2S005BGSPEC1003.FTZ", 78815),
    ("EKDRA",       False, "0111530101", 51908.580984,  54906.0,  54906.0, "P0111530101R1S004SRSPEC1001.FTZ", "P0111530101R1S004BGSPEC1001.FTZ", "P0111530101R2S005SRSPEC1001.FTZ", "P0111530101R2S005BGSPEC1001.FTZ", 83271),
    ("HD110432",    False, "0504730101", 54347.609595,  80505.0,  80462.0, "P0504730101R1S004SRSPEC1003.FTZ", "P0504730101R1S004BGSPEC1003.FTZ", "P0504730101R2S005SRSPEC1003.FTZ", "P0504730101R2S005BGSPEC1003.FTZ", 86051),
    ("RYTAU",       False, "0722320101", 56525.178160, 110271.0, 110313.0, "P0722320101R1S004SRSPEC1004.FTZ", "P0722320101R1S004BGSPEC1004.FTZ", "P0722320101R2S005SRSPEC1004.FTZ", "P0722320101R2S005BGSPEC1004.FTZ", 80493),
    ("SIGMAGEM",    False, "0111480101", 52005.682847,  55811.0,  55810.0, "P0111480101R1S004SRSPEC1003.FTZ", "P0111480101R1S004BGSPEC1003.FTZ", "P0111480101R2S005SRSPEC1003.FTZ", "P0111480101R2S005BGSPEC1003.FTZ", 95374),
    ("RZCAS",       False, "0149040201", 52873.224931, 115176.0, 115172.0, "P0149040201R1S004SRSPEC1001.FTZ", "P0149040201R1S004BGSPEC1001.FTZ", "P0149040201R2S005SRSPEC1001.FTZ", "P0149040201R2S005BGSPEC1001.FTZ", 93919),
    ("XYUMA",       False, "0200960101", 53457.953449,  96775.0,  96378.0, "P0200960101R1S004SRSPEC1003.FTZ", "P0200960101R1S004BGSPEC1003.FTZ", "P0200960101R2S005SRSPEC1003.FTZ", "P0200960101R2S005BGSPEC1003.FTZ", 92412),
    ("BPTAU",       False, "0200370101", 53232.247465, 131826.0, 131820.0, "P0200370101R1S005SRSPEC1003.FTZ", "P0200370101R1S005BGSPEC1003.FTZ", "P0200370101R2S006SRSPEC1003.FTZ", "P0200370101R2S006BGSPEC1003.FTZ", 91157),
    ("DNTAU",       False, "0651120101", 55426.106898, 119267.0, 119312.0, "P0651120101R1S004SRSPEC1003.FTZ", "P0651120101R1S004BGSPEC1003.FTZ", "P0651120101R2S005SRSPEC1003.FTZ", "P0651120101R2S005BGSPEC1003.FTZ", 84851),
    ("BETACMA",     False, "0761090101", 57133.281169, 111917.0, 111912.0, "P0761090101R1S004SRSPEC1003.FTZ", "P0761090101R1S004BGSPEC1003.FTZ", "P0761090101R2S005SRSPEC1003.FTZ", "P0761090101R2S005BGSPEC1003.FTZ", 85293),
    ("BETACRU",     False, "0761090201", 57220.891354,  95918.0,  95909.0, "P0761090201R1S004SRSPEC1003.FTZ", "P0761090201R1S004BGSPEC1003.FTZ", "P0761090201R2S005SRSPEC1003.FTZ", "P0761090201R2S005BGSPEC1003.FTZ", 80661),
    ("SIGMASCO",    False, "0761090301", 57260.802512, 113411.0, 113402.0, "P0761090301R1S004SRSPEC1001.FTZ", "P0761090301R1S004BGSPEC1001.FTZ", "P0761090301R2S005SRSPEC1001.FTZ", "P0761090301R2S005BGSPEC1001.FTZ", 81845),
    ("GAMMALUP",    False, "0652610201", 55617.859850, 102517.0, 102554.0, "P0652610201R1S004SRSPEC1004.FTZ", "P0652610201R1S004BGSPEC1004.FTZ", "P0652610201R2S005SRSPEC1004.FTZ", "P0652610201R2S005BGSPEC1004.FTZ", 90849),
    ("ZETAPUP",     False, "0561380201", 55476.525891,  76914.0,  76904.0, "P0561380201R1S001SRSPEC1003.FTZ", "P0561380201R1S001BGSPEC1003.FTZ", "P0561380201R2S002SRSPEC1003.FTZ", "P0561380201R2S002BGSPEC1003.FTZ", 87904),
    ("NGC4593",     False, "0784740101", 57583.797558, 141011.0, 141003.0, "P0784740101R1S004SRSPEC1003.FTZ", "P0784740101R1S004BGSPEC1003.FTZ", "P0784740101R2S005SRSPEC1003.FTZ", "P0784740101R2S005BGSPEC1003.FTZ", 90000),
    ("MRK335",      False, "0741280201", 57386.377697, 139315.0, 139307.0, "P0741280201R1S004SRSPEC1003.FTZ", "P0741280201R1S004BGSPEC1003.FTZ", "P0741280201R2S005SRSPEC1003.FTZ", "P0741280201R2S005BGSPEC1003.FTZ", 90000),
    ("NGC4449",     False, "0963570101", 60830.624954, 134311.0, 134305.0, "P0963570101R1S004SRSPEC1001.FTZ", "P0963570101R1S004BGSPEC1001.FTZ", "P0963570101R2S005SRSPEC1001.FTZ", "P0963570101R2S005BGSPEC1001.FTZ", 90000),
]

# 20 ALMA Band 9 & Band 10 Single-Pointing Science Cubes (5 Bridges + 15 New)
ALMA_SPECS = [
    # (canon, is_bridge, inst, soda_id, ra, dec, cutout_rad, mjd, expt, approx_ghz, full_bytes)
    ("NGC7469",    True,  "ALMA_B10_0P3MM", "member.uid___A001_X3628_X1f1.NGC7469_sci.spw25.cube.I.pbcor.fits",                  345.815048,   8.873886, 0.00070, 60493.4605,  3932.2, 890.64,   8101440),
    ("AS209",      True,  "ALMA_B10_0P3MM", "member.uid___A001_X3663_X41.as_209_sci.spw31.cube.I.pbcor.fits",                    252.313712, -14.369228, 0.00070, 60479.1454,  8701.6, 860.99,  45938880),
    ("RYTAU",      False, "ALMA_B10_0P3MM", "member.uid___A001_X12d1_X3b.RY_Tau_sci.spw25.cube.I.pbcor.fits",                    65.489236,  28.443093, 0.00046, 58355.4166,  4226.4, 893.62,  34505280),
    ("J1211M0118", False, "ALMA_B10_0P3MM", "member.uid___A001_X3645_X15f.J1211-0118_sci.spw33.cube.I.pbcor.fits",              182.904633,  -1.304583, 0.00050, 60417.2574, 16035.8, 805.13,  50947200),
    ("HERBS103",   False, "ALMA_B10_0P3MM", "member.uid___A001_X3621_X44a6.HerBS-103_sci.spw17.cube.I.selfcal.pbcor.fits",    343.351000, -32.584500, 0.00070, 60574.2057, 10076.2, 858.86,  76671360),
    ("J0217M0208", False, "ALMA_B10_0P3MM", "member.uid___A001_X335e_Xf0.J0217-0208_sci.spw33.cube.I.pbcor.fits",                34.340012,  -2.147994, 0.00050, 59880.2268,  7925.8, 801.13, 122371200),
    ("IIIZW035",   False, "ALMA_B10_0P3MM", "member.uid___A001_X3667_X53.III_Zw_035_sci.spw25.cube.I.pbcor.fits",                26.127255,  17.102378, 0.00070, 60480.5394,  5529.6, 880.81,   7156800),
    ("NGC1808",    False, "ALMA_B10_0P3MM", "member.uid___A001_X3646_X9e.NGC1808_sci.spw17.cube.I.pbcor.fits",                   76.926371, -37.512736, 0.00070, 60480.6683,  3993.6, 802.10,   8688960),
    ("RVAQR",      False, "ALMA_B10_0P3MM", "member.uid___A001_X362b_X61a.RV_Aqr_sci.spw19.cube.I.pbcor.fits",                  316.465570,  -0.211672, 0.00070, 60450.5245,  3317.6, 806.01,  68299200),
    ("WISE2246",   False, "ALMA_B10_0P3MM", "member.uid___A001_X12e7_X51.WISE2246-0526_sci.spw35.cube.I.pbcor.fits",            341.531471,  -5.443050, 0.00048, 58261.4551,  1781.8, 833.20,  44426880),
    ("NGC7469",    True,  "ALMA_B9_0P4MM",  "member.uid___A001_X3628_X1fd.NGC7469_sci.spw24.cube.I.pbcor.fits",                  345.815048,   8.873886, 0.00070, 60252.1307,  4300.8, 665.91,   7413120),
    ("HD163296",   True,  "ALMA_B9_0P4MM",  "member.uid___A001_X362b_X79e.HD_163296_sci.spw21.cube.I.pbcor.fits",               269.088645, -21.956344, 0.00070, 60492.2503,  2396.2, 665.96,  86480640),
    ("DMTAU",      True,  "ALMA_B9_0P4MM",  "member.uid___A001_X1465_X220e.DM_Tau_sci.spw21.cube.I.pbcor.fits",                  68.453069,  18.169333, 0.00060, 58785.3014,  5571.3, 691.49,  47131200),
    ("AG354",      False, "ALMA_B9_0P4MM",  "member.uid___A001_X1590_X280f.AG354_sci.spw16.cube.I.pbcor.fits",                  263.799679, -33.507166, 0.00070, 59773.0690, 59330.9, 691.67,  61104960),
    ("G205M3",     False, "ALMA_B9_0P4MM",  "member.uid___A001_X2df7_X28f._G205.46-14.56M3__sci.spw16.cube.I.pbcor.fits",        86.524833,  -0.159014, 0.00070, 59880.3207, 25885.4, 691.64,  68302080),
    ("J0218M0519", False, "ALMA_B9_0P4MM",  "member.uid___A001_X335e_Xf4.J0218-0519_sci.spw35.cube.I.pbcor.fits",                34.735567,  -5.333019, 0.00058, 59867.2807, 24606.7, 688.72, 122371200),
    ("IRAS08303",  False, "ALMA_B9_0P4MM",  "member.uid___A001_X3788_X5e38.08303-4303_sci.spw54.cube.I.pbcor.fits",             128.036042, -43.229531, 0.00070, 60596.4487, 11827.2, 712.28,  41647680),
    ("BRI1335",    False, "ALMA_B9_0P4MM",  "member.uid___A001_X133d_X29e7.BRI1335_sci.spw25.cube.I.pbcor.fits",                204.514250,  -4.543000, 0.00065, 58587.2415, 11673.6, 612.22, 107714880),
    ("A1689ZD1",   False, "ALMA_B9_0P4MM",  "member.uid___A001_X1465_X1b1.A1689-zD1_sci.spw33.cube.I.manual.pbcor.fits",        197.874721,  -1.321881, 0.00058, 58826.4298,  5713.9, 693.07,  34519680),
    ("N13PDR",     False, "ALMA_B9_0P4MM",  "member.uid___A001_X15b4_X96.N13_PDR_sci.spw16.cube.I.pbcor.fits",                   11.361879, -73.382233, 0.00070, 59740.4107,  6021.1, 674.61,  39735360),
]

# 6 New Exoplanet Orbital Campaigns (#163-#168, 5 epochs each = 30 ESO spectra)
ESO_ORBIT_SPECS = {
    "HD134987": {
        "campaign_order": 163, "phase_id": "D103", "instrument": "ESO_ESPRESSO",
        "grating": "ESPRESSO_377_790NM", "rp": 140000.0,
        "orb_per_days": 5000.0, "orb_ecc": 0.12, "orb_omega_deg": 195.0,
        "orb_t0_bjd": 2455060.0, "kp_kms": 0.0093, "pl_note": "2-pl High-SNR ESPRESSO, 26.18 pc",
        "exposures": [
            ("ADP.2024-05-08T08:35:39.112", 60422.209589, 696.0, 787.0),
            ("ADP.2024-05-08T08:32:50.817", 60419.285425, 696.0, 701.9),
            ("ADP.2024-07-05T15:23:01.490", 60473.238983, 696.0, 697.3),
            ("ADP.2024-05-08T08:46:07.328", 60431.311590, 696.0, 674.6),
            ("ADP.2025-06-04T07:38:35.365", 60799.167391, 696.0, 665.9),
        ],
    },
    "HD82943": {
        "campaign_order": 164, "phase_id": "D103", "instrument": "ESO_ESPRESSO",
        "grating": "ESPRESSO_377_790NM", "rp": 140000.0,
        "orb_per_days": 441.47, "orb_ecc": 0.162, "orb_omega_deg": 300.9,
        "orb_t0_bjd": 2451758.0, "kp_kms": 0.04191, "pl_note": "2-pl 2:1 MMR ESPRESSO, 27.59 pc",
        "exposures": [
            ("ADP.2024-02-05T15:11:13.691", 60311.222643, 696.0, 710.1),
            ("ADP.2024-06-06T11:48:04.263", 60432.995120, 696.0, 682.8),
            ("ADP.2024-02-05T15:46:28.983", 60322.320912, 696.0, 659.0),
            ("ADP.2024-04-09T10:14:30.126", 60401.027962, 696.0, 633.2),
            ("ADP.2025-05-05T08:00:30.768", 60793.143080, 696.0, 597.7),
        ],
    },
    "HD196067": {
        "campaign_order": 165, "phase_id": "D103", "instrument": "ESO_ESPRESSO",
        "grating": "ESPRESSO_377_790NM", "rp": 140000.0,
        "orb_per_days": 3413.7, "orb_ecc": 0.56292, "orb_omega_deg": 142.835,
        "orb_t0_bjd": 2453375.0, "kp_kms": 0.08257, "pl_note": "2-pl High-Ecc e=0.563 ESPRESSO, 39.93 pc",
        "exposures": [
            ("ADP.2023-10-09T13:05:33.876", 60218.098584, 696.0, 673.4),
            ("ADP.2024-07-05T11:12:54.491", 60467.285763, 696.0, 638.2),
            ("ADP.2024-11-05T09:57:47.292", 60603.027886, 696.0, 635.7),
            ("ADP.2025-06-04T07:57:37.088", 60801.344989, 696.0, 626.2),
            ("ADP.2024-06-06T17:36:16.757", 60458.267092, 696.0, 575.0),
        ],
    },
    "HD10180": {
        "campaign_order": 166, "phase_id": "D103", "instrument": "ESO_HARPS",
        "grating": "HARPS_378_691NM", "rp": 115000.0,
        "orb_per_days": 49.748, "orb_ecc": 0.051, "orb_omega_deg": 147.0,
        "orb_t0_bjd": 2454006.26, "kp_kms": 0.004283, "pl_note": "6-pl Rich System HARPS, 38.96 pc",
        "exposures": [
            ("ADP.2014-10-02T10:02:36.540", 53729.029514, 900.0, 252.3),
            ("ADP.2014-10-02T10:01:32.377", 53722.093301, 900.0, 238.9),
            ("ADP.2014-09-18T12:12:05.287", 54748.278885, 900.0, 232.3),
            ("ADP.2016-01-10T01:02:45.497", 57396.105420, 900.0, 224.2),
            ("ADP.2014-09-17T11:22:03.670", 54349.316046, 900.0, 223.3),
        ],
    },
    "HD134060": {
        "campaign_order": 167, "phase_id": "D103", "instrument": "ESO_HARPS",
        "grating": "HARPS_378_691NM", "rp": 115000.0,
        "orb_per_days": 3.2696, "orb_ecc": 0.45, "orb_omega_deg": -98.23,
        "orb_t0_bjd": 2455499.6542, "kp_kms": 0.00461, "pl_note": "2-pl e=0.45 HARPS, 24.01 pc",
        "exposures": [
            ("ADP.2015-08-25T23:55:38.470", 57257.985516, 900.0, 400.6),
            ("ADP.2015-09-03T23:56:05.023", 57268.027622, 900.0, 343.7),
            ("ADP.2017-02-16T01:02:40.533", 57799.359759, 900.0, 341.9),
            ("ADP.2014-09-23T11:05:50.417", 55039.988734, 900.0, 328.6),
            ("ADP.2014-09-23T11:04:37.937", 54937.226960, 900.0, 322.6),
        ],
    },
    "BD210397": {
        "campaign_order": 168, "phase_id": "D103", "instrument": "ESO_HARPS",
        "grating": "HARPS_378_691NM", "rp": 115000.0,
        "orb_per_days": 6240.0, "orb_ecc": 0.43, "orb_omega_deg": 174.0,
        "orb_t0_bjd": 2460193.0, "kp_kms": 0.034, "pl_note": "2-pl e=0.43 K=34m/s Long-Baseline HARPS, 23.73 pc",
        "exposures": [
            ("ADP.2014-10-02T10:02:33.200", 53724.054484, 900.0, 64.3),
            ("ADP.2017-11-02T01:01:17.034", 58058.283390, 900.0, 54.4),
            ("ADP.2014-09-26T16:53:36.657", 56290.088759, 900.0, 52.0),
            ("ADP.2014-09-26T16:54:19.150", 56285.089525, 900.0, 50.6),
            ("ADP.2014-09-26T16:53:09.477", 56284.078736, 900.0, 50.1),
        ],
    },
}

# 8 Brand-New <= 10.12 pc 0-planet Control Exposures on ESO (5 strictly <= 10.0 pc)
ESO_CONTROL_SPECS = [
    ("GJ257A",        "ESO_HARPS",    "ADP.2014-09-24T09:42:39.663", 55516.345665, 900.0, 22.0),
    ("HD32450A",      "ESO_HARPS",    "ADP.2014-09-29T13:27:00.290", 52947.297409, 132.6, 26.2),
    ("PMJ19070P2053", "ESO_ESPRESSO", "ADP.2025-10-01T00:07:28.414", 60946.007869, 180.0, 25.8),
    ("GJ867A",        "ESO_HARPS",    "ADP.2014-09-18T12:11:06.977", 54645.439840, 660.0, 56.6),
    ("LHS1731",       "ESO_HARPS",    "ADP.2014-09-17T11:20:44.553", 54140.060699, 900.0, 20.2),
    ("L480_69",       "ESO_ESPRESSO", "ADP.2022-09-06T09:53:18.823", 59800.026523, 900.0, 47.3),
    ("LTT9759",       "ESO_HARPS",    "ADP.2014-09-16T11:04:50.620", 53981.298838, 900.0, 52.8),
    ("GL678_1A",      "ESO_HARPS",    "ADP.2016-08-27T01:04:01.349", 57626.025236, 900.0, 71.5),
]


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _ang_sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    c = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c)))) * 3600.0


def _ecliptic_lat_deg(ra_deg: float, dec_deg: float) -> float:
    eps = math.radians(23.4392911)
    ra_r, dec_r = map(math.radians, (ra_deg, dec_deg))
    s = math.sin(dec_r) * math.cos(eps) - math.cos(dec_r) * math.sin(eps) * math.sin(ra_r)
    return round(math.degrees(math.asin(max(-1.0, min(1.0, s)))), 5)


def _ellipsoid_dt_days(ra_deg: float, dec_deg: float, dist_pc: float, mjd_obs: float, ev_ra: float, ev_dec: float, ev_mjd0: float) -> float:
    ra1, d1, ra2, d2 = map(math.radians, (ra_deg, dec_deg, ev_ra, ev_dec))
    c = max(-1.0, min(1.0, math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(ra1 - ra2)))
    geom = 1192.226 * float(dist_pc) * (1.0 - c)
    return round(float(mjd_obs) - (float(ev_mjd0) + geom), 3)


def _kepler_rv(dt_days: float, per_days: float, ecc: float, omega_deg: float, gamma_kms: float, k_kms: float) -> tuple[float, float]:
    m_anom = (2.0 * math.pi * (dt_days % per_days)) / per_days
    ea = m_anom
    for _ in range(15):
        f = ea - ecc * math.sin(ea) - m_anom
        fp = 1.0 - ecc * math.cos(ea)
        ea -= f / max(1e-12, fp)
    nu = 2.0 * math.atan2(math.sqrt(1.0 + ecc) * math.sin(0.5 * ea), math.sqrt(max(1e-12, 1.0 - ecc)) * math.cos(0.5 * ea))
    w_rad = math.radians(omega_deg)
    rv = gamma_kms + k_kms * (math.cos(nu + w_rad) + ecc * math.cos(w_rad))
    ph = ((dt_days / per_days) % 1.0) - 0.5
    return round(float(rv), 6), round(float(ph), 5)


def _read_d102_sources(archives_dir: Path | None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    zpath = (archives_dir / ARCHIVE_AB_NAME) if archives_dir else (ROOT / "archives" / ARCHIVE_AB_NAME)
    if WS102.exists() and (WS102 / "results" / "SUMMARY.json").exists():
        summ = json.loads((WS102 / "results" / "SUMMARY.json").read_text())
        pex = json.loads((WS102 / "PRIOR_EXCLUSION_VERIFICATION.json").read_text())
        u656 = list(csv.DictReader((WS102 / "results" / "UNIFIED_PANCHROMATIC_V6_0_SYNTHESIS_656STARS.csv").open()))
        br84 = list(csv.DictReader((WS102 / "results" / "PANCHROMATIC_BRIDGE_84STARS_V60.csv").open()))
        ac_u = list(csv.DictReader((WS102 / "results" / "ALLSKY_COMB_V4_1_UNIFIED_D079_D102.csv").open()))
        ac_c = list(csv.DictReader((WS102 / "results" / "ALLSKY_COMB_V4_1_CANDIDATES_D079_D102.csv").open()))
        ell656 = list(csv.DictReader((WS102 / "results" / "MULTIEVENT_ELLIPSOID_656STARS.csv").open()))
        fc102 = list(csv.DictReader((WS102 / "FROZEN_COHORT_D102.csv").open()))
    elif zpath.exists():
        assert _sha256_file(zpath) == ARCHIVE_AB_SHA256, f"Archive AB SHA256 mismatch: {zpath}"
        with zipfile.ZipFile(zpath) as zf:
            names = zf.namelist()
            def _ztxt(sfx: str) -> str:
                m = next(n for n in names if n.endswith(sfx))
                return zf.read(m).decode("utf-8")
            summ = json.loads(_ztxt("/results/SUMMARY.json"))
            pex = json.loads(_ztxt("/PRIOR_EXCLUSION_VERIFICATION.json"))
            u656 = list(csv.DictReader(_ztxt("/results/UNIFIED_PANCHROMATIC_V6_0_SYNTHESIS_656STARS.csv").splitlines()))
            br84 = list(csv.DictReader(_ztxt("/results/PANCHROMATIC_BRIDGE_84STARS_V60.csv").splitlines()))
            ac_u = list(csv.DictReader(_ztxt("/results/ALLSKY_COMB_V4_1_UNIFIED_D079_D102.csv").splitlines()))
            ac_c = list(csv.DictReader(_ztxt("/results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D102.csv").splitlines()))
            ell656 = list(csv.DictReader(_ztxt("/results/MULTIEVENT_ELLIPSOID_656STARS.csv").splitlines()))
            fc102 = list(csv.DictReader(_ztxt("/FROZEN_COHORT_D102.csv").splitlines()))
    else:
        raise FileNotFoundError(f"Neither WS102 nor Archive AB ({zpath}) found.")

    snap_extras = {
        "u656": u656, "br84": br84, "ac_u": ac_u, "ac_c": ac_c, "ell656": ell656, "fc102": fc102,
    }
    ell_map = {r["star"]: r for r in ell656}
    u_map = {r["star"]: {**r, "ra_deg": ell_map[r["star"]]["ra_deg"], "dec_deg": ell_map[r["star"]]["dec_deg"]} for r in u656}
    return summ, pex, snap_extras, u_map


def _star_meta(canon: str, is_bridge: bool, u_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if is_bridge:
        assert canon in u_map, f"Bridge target {canon} not found in UNIFIED_656!"
        u = u_map[canon]
        return {
            "common_name": u["common_name"],
            "role": u["role"],
            "ra": float(u["ra_deg"]),
            "dec": float(u["dec_deg"]),
            "dist_pc": float(u["dist_pc"]),
            "teff_k": float(u["teff_k"] or 5000.0),
            "rv": 0.0,
            "gmag": u.get("phot_g_mag") or "",
            "jmag": u.get("j_mag") or "",
            "hmag": u.get("h_mag") or "",
            "kmag": u.get("ks_mag") or "",
            "n_pl": int(u.get("n_exoplanets") or 0),
            "mass": 1.0,
            "mh": 0.0,
            "gaia": canon,
        }
    m = NEW_META[canon]
    return {
        "common_name": m["common_name"],
        "role": m["role"],
        "ra": float(m["ra"]),
        "dec": float(m["dec"]),
        "dist_pc": float(m["dist_pc"]),
        "teff_k": float(m["teff_k"]),
        "rv": float(m.get("rv", 0.0)),
        "gmag": str(m.get("gmag", "")),
        "jmag": "", "hmag": "", "kmag": "",
        "n_pl": int(m.get("n_pl", 0)),
        "mass": float(m.get("mass", 1.0)),
        "mh": float(m.get("mh", 0.0)),
        "gaia": m.get("gaia", canon),
    }


def _make_row(
    inst: str, canon: str, sm: dict[str, Any], is_bridge: bool,
    subrole: str, track: str, dp_id: str, grating: str, rp: float,
    mjd: float, expt: float, rel_path: str, url: str, f1_bytes: int,
    extra_files: list[dict[str, Any]] | None = None,
    ep_rank: int = 1, ph_win: str = "NONE", s_ph: float = 0.0, rv_orb: float = 0.0,
) -> dict[str, Any]:
    ra, dec, dist_pc = float(sm["ra"]), float(sm["dec"]), float(sm["dist_pc"])
    extras = extra_files or []
    tot_b = int(f1_bytes) + sum(int(x["bytes"]) for x in extras)
    return {
        "instrument": inst,
        "canonical_target": canon,
        "common_name": sm["common_name"],
        "role": sm["role"],
        "subrole": subrole,
        "science_track": track,
        "panchromatic_bridge": str(bool(is_bridge)),
        "is_prior_bridge": str(bool(is_bridge)),
        "gaia_source_id": sm["gaia"],
        "s_ra": f"{ra:.7f}",
        "s_dec": f"{dec:.7f}",
        "pmra_mas_yr": "0.0",
        "pmdec_mas_yr": "0.0",
        "dist_pc": f"{dist_pc:.5f}",
        "within_10pc": str(dist_pc <= 10.0 and sm["role"] in ("SCIENCE", "CONTROL") and dist_pc < 100.0),
        "phot_g_mag": str(sm["gmag"]),
        "phot_bp_mag": "", "phot_rp_mag": "",
        "j_mag": str(sm["jmag"]), "h_mag": str(sm["hmag"]), "ks_mag": str(sm["kmag"]),
        "teff_k": f"{float(sm['teff_k']):.1f}",
        "mh_dex": str(sm["mh"]),
        "stellar_mass_msun": str(sm["mass"]),
        "prior_rv_kms": str(sm["rv"]),
        "n_exoplanets": str(int(sm["n_pl"])),
        "has_transiting_planet": "False",
        "ecliptic_lat_deg": str(_ecliptic_lat_deg(ra, dec)),
        "sn1987a_dt_days": str(_ellipsoid_dt_days(ra, dec, dist_pc, mjd, 83.8667, -69.2697, 46849.316)),
        "gw170817_dt_days": str(_ellipsoid_dt_days(ra, dec, dist_pc, mjd, 197.4504, -23.3815, 57982.529)),
        "sn2023ixf_dt_days": str(_ellipsoid_dt_days(ra, dec, dist_pc, mjd, 210.9107, 54.3116, 60083.728)),
        "ppo_align_score": "1.0",
        "epoch_rank": str(ep_rank),
        "dp_id": dp_id,
        "grating": grating,
        "resolving_power": f"{rp:.1f}",
        "mjd_obs": f"{mjd:.6f}",
        "t_exptime": f"{expt:.3f}",
        "phase_window": ph_win,
        "signed_phase": str(s_ph),
        "planet_orbital_rv_kms": str(rv_orb),
        "f1_id": dp_id,
        "f1_rel": rel_path,
        "f1_url": url,
        "f1_bytes": str(int(f1_bytes)),
        "total_bytes": str(tot_b),
        "extra_files": json.dumps(extras, separators=(",", ":")),
    }


def main() -> int:
    if RAW_DIR.exists() and not (WS / "LOCK_RECEIPT.json").exists():
        raise RuntimeError(f"CRITICAL REFUSAL: raw input directory {RAW_DIR} already exists prior to Stage-1 seal!")

    archives_dir = ROOT / "archives"
    summ102, pex102, sx, u_map = _read_d102_sources(archives_dir)
    uni102 = summ102["unified_656star_panchromatic_v6_0_synthesis"]

    # Build cumulative prior registry: 686 + 43 D102 = 729 coords; 3261 + 107 D102 = 3368 dp_ids
    prior_coords = list(pex102["excluded_targets_coordinate_registry"])
    seen_d102 = {c.get("canonical_target", "") for c in prior_coords if c.get("canonical_target")}
    d102_dps = []
    for r in sx["fc102"]:
        d102_dps.append(r["dp_id"])
        if r["is_prior_bridge"] == "False" and r["canonical_target"] not in seen_d102:
            seen_d102.add(r["canonical_target"])
            prior_coords.append({
                "canonical_target": r["canonical_target"],
                "ra_deg": float(r["s_ra"]),
                "dec_deg": float(r["s_dec"]),
            })
    prior_dp_ids = sorted(set(pex102["excluded_dp_ids"]) | set(d102_dps))
    prior_dp_set = set(prior_dp_ids)
    fmt_excl = sorted(set(pex102["format_check_excluded_dp_ids"]) | set(FORMAT_CHECK_PROBES_D103))
    fmt_excl_set = set(fmt_excl)

    frozen_rows: list[dict[str, Any]] = []
    brand_new_coords: dict[str, tuple[float, float]] = {}

    # 1. 19 NuSTAR FPMA+FPMB hard X-ray Poisson pairs (8 bridges + 11 new)
    for canon, is_b, obsid, mjd, exp_a, exp_b, bytes_a, bytes_b in NUSTAR_SPECS:
        dp_id = f"NUSTAR_{obsid}_FPMA_FPMB"
        assert dp_id not in prior_dp_set and obsid not in prior_dp_set and obsid not in fmt_excl_set
        sm = _star_meta(canon, is_b, u_map)
        if not is_b:
            brand_new_coords[canon] = (sm["ra"], sm["dec"])
        base = f"https://heasarc.gsfc.nasa.gov/FTP/nustar/data/obs/{obsid[1:3]}/{obsid[0]}/{obsid}/event_cl"
        fa, fb = f"nu{obsid}A01_cl.evt.gz", f"nu{obsid}B01_cl.evt.gz"
        rel_a = f"NUSTAR_FPMA_FPMB/{canon}/{fa}"
        rel_b = f"NUSTAR_FPMA_FPMB/{canon}/{fb}"
        extras = [{"role": "FPMB", "id": fb, "rel": rel_b, "url": f"{base}/{fb}", "bytes": bytes_b}]
        frozen_rows.append(_make_row(
            "NUSTAR_FPMA_FPMB", canon, sm, is_b,
            f"{'BRIDGE' if is_b else 'NEW'}_NUSTAR_3_79KEV",
            "NUSTAR_HARD_XRAY_V61", dp_id, "FPMA_FPMB_3_79KEV", 100.0, mjd,
            min(exp_a, exp_b), rel_a, f"{base}/{fa}", bytes_a, extra_files=extras,
        ))

    # 2. 27 XMM-Newton RGS soft X-ray quadruplets (10 bridges + 17 new)
    for canon, is_b, obsid, mjd, t1, t2, r1s, r1b, r2s, r2b, tot_b in XMM_SPECS:
        dp_id = f"XMM_{obsid}_{r1s}"
        assert dp_id not in prior_dp_set and obsid not in prior_dp_set and obsid not in fmt_excl_set
        sm = _star_meta(canon, is_b, u_map)
        if not is_b:
            brand_new_coords[canon] = (sm["ra"], sm["dec"])
        pps = f"https://heasarc.gsfc.nasa.gov/FTP/xmm/data/rev0/{obsid}/PPS"
        f1_b = tot_b // 4
        extras = [
            {"role": "R1_BG", "id": r1b, "rel": f"XMM_RGS/{canon}/{r1b}", "url": f"{pps}/{r1b}", "bytes": f1_b},
            {"role": "R2_SR", "id": r2s, "rel": f"XMM_RGS/{canon}/{r2s}", "url": f"{pps}/{r2s}", "bytes": f1_b},
            {"role": "R2_BG", "id": r2b, "rel": f"XMM_RGS/{canon}/{r2b}", "url": f"{pps}/{r2b}", "bytes": tot_b - 3 * f1_b},
        ]
        frozen_rows.append(_make_row(
            "XMM_RGS", canon, sm, is_b,
            f"{'BRIDGE' if is_b else 'NEW'}_XMM_RGS_5_38A",
            "XMM_RGS_XRAY_V61", dp_id, "RGS1_RGS2_5_38A", 500.0, mjd,
            min(t1, t2), f"XMM_RGS/{canon}/{r1s}", f"{pps}/{r1s}", f1_b, extra_files=extras,
        ))

    # 3. 20 ALMA Band 9 & Band 10 single-pointing cubes (5 bridges + 15 new)
    for canon, is_b, inst, soda_id, s_ra, s_dec, cut_rad, mjd, expt, ghz, full_b in ALMA_SPECS:
        assert soda_id not in prior_dp_set and soda_id not in fmt_excl_set
        sm = _star_meta(canon, is_b, u_map)
        if not is_b:
            brand_new_coords[canon] = (sm["ra"], sm["dec"])
        circle = urllib.parse.quote(f"{s_ra:.6f} {s_dec:.6f} {cut_rad:.5f}")
        url = f"https://almascience.eso.org/soda/sync?ID={urllib.parse.quote(soda_id)}&CIRCLE={circle}"
        rel = f"{inst}/{canon}/{soda_id}"
        frozen_rows.append(_make_row(
            inst, canon, sm, is_b,
            f"{'BRIDGE' if is_b else 'NEW'}_{inst}_CUBEV61",
            "ALMA_B9B10_V61", soda_id, f"{inst}_{ghz:.2f}GHZ", 100000.0, mjd,
            expt, rel, url, full_b, extra_files=[],
        ))

    # 4. 30 ESO Orbits #163-#168 (6 campaigns x 5 epochs) + 8 ESO <=10.12pc 0-pl Controls
    campaigns_out: dict[str, Any] = {}
    for canon, spec in ESO_ORBIT_SPECS.items():
        sm = _star_meta(canon, False, u_map)
        brand_new_coords[canon] = (sm["ra"], sm["dec"])
        campaigns_out[canon] = {
            "campaign_order": spec["campaign_order"],
            "phase_id": "D103",
            "canonical_target": canon,
            "common_name": sm["common_name"],
            "instrument": spec["instrument"],
            "grating": spec["grating"],
            "orb_per_days": spec["orb_per_days"],
            "orb_ecc": spec["orb_ecc"],
            "orb_omega_deg": spec["orb_omega_deg"],
            "orb_t0_bjd": spec["orb_t0_bjd"],
            "kp_kms": spec["kp_kms"],
            "exposures": [],
        }
        for ep_i, (dp_id, mjd, expt, snr) in enumerate(spec["exposures"], 1):
            assert dp_id not in prior_dp_set and dp_id not in fmt_excl_set
            bjd = mjd + 2400000.5
            rv_orb, s_ph = _kepler_rv(bjd - spec["orb_t0_bjd"], spec["orb_per_days"], spec["orb_ecc"], spec["orb_omega_deg"], 0.0, spec["kp_kms"])
            ph_win = "IN_QUADRATURE" if abs(abs(s_ph) - 0.25) < 0.12 else "IN_WINDOW"
            campaigns_out[canon]["exposures"].append({
                "dp_id": dp_id, "mjd_obs": mjd, "bjd_tdb_est": round(bjd, 6),
                "snr": snr, "signed_phase": s_ph, "phase_window": ph_win, "planet_orbital_rv_kms": rv_orb,
            })
            url = f"https://dataportal.eso.org/dataPortal/file/{urllib.parse.quote(dp_id)}"
            rel = f"{spec['instrument']}/{canon}/{dp_id.replace(':', '_')}.fits"
            frozen_rows.append(_make_row(
                spec["instrument"], canon, sm, False,
                f"ORBIT_CAMPAIGN_{spec['campaign_order']}",
                "KEPLERIAN_DRIFT_OR_COMB_V61", dp_id, spec["grating"], spec["rp"], mjd, expt, rel, url,
                9500000 if spec["instrument"] == "ESO_ESPRESSO" else 7400000,
                extra_files=[], ep_rank=ep_i, ph_win=ph_win, s_ph=s_ph, rv_orb=rv_orb,
            ))

    for ck in campaigns_out:
        ex_list = campaigns_out[ck]["exposures"]
        mjds = [e["mjd_obs"] for e in ex_list]
        rvs = [e["planet_orbital_rv_kms"] for e in ex_list]
        campaigns_out[ck]["n_epochs"] = len(mjds)
        campaigns_out[ck]["baseline_days"] = round(max(mjds) - min(mjds), 2)
        campaigns_out[ck]["orbital_dv_span_kms"] = round(max(rvs) - min(rvs), 4)

    ctrl_ep: dict[str, int] = {}
    for canon, inst, dp_id, mjd, expt, snr in ESO_CONTROL_SPECS:
        assert dp_id not in prior_dp_set and dp_id not in fmt_excl_set
        ctrl_ep[canon] = ctrl_ep.get(canon, 0) + 1
        sm = _star_meta(canon, False, u_map)
        brand_new_coords[canon] = (sm["ra"], sm["dec"])
        grating = "ESPRESSO_377_790NM" if inst == "ESO_ESPRESSO" else "HARPS_378_691NM"
        rp = 140000.0 if inst == "ESO_ESPRESSO" else 115000.0
        url = f"https://dataportal.eso.org/dataPortal/file/{urllib.parse.quote(dp_id)}"
        rel = f"{inst}/{canon}/{dp_id.replace(':', '_')}.fits"
        frozen_rows.append(_make_row(
            inst, canon, sm, False,
            "CONTROL_0PL_10PC_V61", "ESO_CONTROL_V61", dp_id, grating, rp,
            mjd, expt, rel, url, 9500000 if inst == "ESO_ESPRESSO" else 7400000,
            extra_files=[], ep_rank=ctrl_ep[canon],
        ))

    # Strict >= 300" sky separation against ALL 729 cumulative prior coords + >= 120" intra-D103
    star_sep_verif: list[dict[str, Any]] = []
    min_prior_sep = 1e9
    for st_name, (ra_n, dec_n) in sorted(brand_new_coords.items()):
        best_c = min(prior_coords, key=lambda pc: _ang_sep_arcsec(ra_n, dec_n, pc["ra_deg"], pc["dec_deg"]))
        sep_s = _ang_sep_arcsec(ra_n, dec_n, best_c["ra_deg"], best_c["dec_deg"])
        assert sep_s >= 300.0, f"Brand-new star {st_name} within 300\" of prior {best_c}: {sep_s:.2f}\""
        min_prior_sep = min(min_prior_sep, sep_s)
        star_sep_verif.append({"star": st_name, "min_sep_prior_arcsec": round(sep_s, 2), "nearest_prior": best_c.get("canonical_target", "")})

    bn_items = sorted(brand_new_coords.items())
    min_intra_sep = 1e9
    for i in range(len(bn_items)):
        for j in range(i + 1, len(bn_items)):
            sp = _ang_sep_arcsec(bn_items[i][1][0], bn_items[i][1][1], bn_items[j][1][0], bn_items[j][1][1])
            min_intra_sep = min(min_intra_sep, sp)
            assert sp >= 120.0, f"Intra-D103 collision {bn_items[i][0]} vs {bn_items[j][0]}: {sp}"

    d103_dps = [r["dp_id"] for r in frozen_rows]
    assert len(d103_dps) == len(set(d103_dps)), "Duplicate dp_id inside D103 frozen cohort!"

    now_utc = dt.datetime.now(tz=dt.timezone.utc)
    now_iso = now_utc.isoformat()
    now_epoch = round(now_utc.timestamp(), 4)

    cohort_csv = WS / "FROZEN_COHORT_D103.csv"
    with cohort_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FROZEN_HEADER)
        w.writeheader()
        w.writerows(frozen_rows)

    all_stars_d103 = {r["canonical_target"] for r in frozen_rows}
    bridge_stars = {r["canonical_target"] for r in frozen_rows if r["is_prior_bridge"] == "True"}
    n_new_ctrl = sum(1 for k in brand_new_coords if NEW_META[k]["role"] == "CONTROL")
    n_new_10pc = sum(1 for k in brand_new_coords if NEW_META[k]["dist_pc"] <= 10.0 and NEW_META[k]["dist_pc"] < 100.0)
    total_phys_files = sum(1 + len(json.loads(r["extra_files"])) for r in frozen_rows)
    proj_bytes = sum(int(r["total_bytes"]) for r in frozen_rows)

    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps({
        "schema": "D103_ORBITAL_CAMPAIGNS_AND_KINEMATICS",
        "phase_id": "D103",
        "campaign_range": [163, 168],
        "campaigns": campaigns_out,
        "notes": "Keplerian reflex motion computed deterministically with (e, omega, T0, P, K) prior to data download.",
    }, indent=2) + "\n")

    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps({
        "schema": "D103_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D103",
        "verified_utc": now_iso,
        "prior_phases_covered": "C001-C037 + D001-D102",
        "n_prior_excluded_coords": len(prior_coords),
        "n_prior_excluded_dp_ids": len(prior_dp_ids),
        "n_format_check_excluded_dp_ids": len(fmt_excl),
        "d103_total_stars": len(all_stars_d103),
        "d103_brand_new_unique_stars": len(brand_new_coords),
        "d103_prior_bridge_stars": len(bridge_stars),
        "d103_control_stars": n_new_ctrl,
        "d103_brand_new_within_10pc": n_new_10pc,
        "d103_total_observations": len(frozen_rows),
        "d103_total_physical_files": total_phys_files,
        "d103_projected_download_bytes": proj_bytes,
        "d103_projected_download_mib": round(proj_bytes / (1024.0 * 1024.0), 4),
        "d103_dp_id_overlap_count": 0,
        "min_brand_new_sky_separation_arcsec": round(min_prior_sep, 2),
        "min_intra_d103_separation_arcsec": round(min_intra_sep, 2),
        "star_separation_verification": star_sep_verif,
        "format_check_excluded_dp_ids": fmt_excl,
        "excluded_dp_ids": prior_dp_ids,
        "excluded_targets_coordinate_registry": prior_coords,
    }, indent=2) + "\n")

    (WS / "PRIOR_V6_0_PHASES_SNAPSHOT.json").write_text(json.dumps({
        "schema": "D103_PRIOR_V6_0_PHASES_SNAPSHOT",
        "prior_phases": "C001-C037 + D001-D102",
        "source_archive_ab_name": ARCHIVE_AB_NAME,
        "source_archive_ab_sha256": ARCHIVE_AB_SHA256,
        "source_archive_ab_bundle_member": ARCHIVE_AB_BUNDLE_MEMBER,
        "source_archive_ab_bundle_sha256": ARCHIVE_AB_BUNDLE_SHA256,
        "prior_unique_stars_count": int(uni102["unique_stars_total"]),
        "prior_science_stars_count": int(uni102["science_stars_total"]),
        "prior_control_stars_count": int(uni102["control_stars_total"]),
        "prior_planet_host_stars_count": int(uni102["planet_host_stars_total"]),
        "prior_confirmed_exoplanets_count": int(uni102["confirmed_exoplanets_total"]),
        "prior_within_10pc_count": int(uni102["within_10pc_unique_stars"]),
        "prior_total_exposures_count": int(uni102["total_exposures_d079_d102"]),
        "prior_cumulative_integration_hours": float(uni102["total_integration_hours_d079_d102"]),
        "prior_calibration_trials_count": int(uni102["total_calibration_trials_d079_d102"]),
        "prior_v2_false_alarms_eliminated_total": int(uni102["v2_false_alarms_eliminated_total"]),
        "prior_cumulative_orbital_campaigns_count": int(uni102["cumulative_orbital_campaigns"]),
        "prior_panchromatic_bridge_stars_count": int(uni102["panchromatic_bridge_stars_total"]),
        "prior_revisited_control_multi_phase_stars": int(uni102["revisited_control_multi_phase_stars"]),
        "prior_multi_phase_targets_total": int(uni102["multi_phase_targets_total"]),
        "prior_panchromatic_bridge_cells_count": int(uni102["panchromatic_bridge_cells_total"]),
        "prior_cumulative_comb_stacks": int(uni102["cumulative_comb_stacks"]),
        "prior_coherent_eccentric_keplerian_campaigns": int(uni102["coherent_eccentric_keplerian_campaigns"]),
        "d102_summary_headline": uni102,
        "prior_unified_656_rows": sx["u656"],
        "prior_bridge_84_rows": sx["br84"],
        "prior_allsky_comb_unified_rows": sx["ac_u"],
        "prior_allsky_comb_candidate_rows": sx["ac_c"],
        "prior_ellipsoid_656_rows": sx["ell656"],
    }, separators=(",", ":")) + "\n")

    stage1_names = [
        "v6_1_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D103.csv",
        "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "PRIOR_V6_0_PHASES_SNAPSHOT.json",
    ]
    hashes = {fn: _sha256_file(WS / fn) for fn in stage1_names}

    ml_path = WS / "METHOD_LOCK.json"
    ml_path.write_text(json.dumps({
        "schema": "D103_PROSPECTIVE_METHOD_LOCK",
        "phase_id": "D103",
        "detector_version": "V6.1",
        "detector": "TECHNOSIGNATURE_V6_1_HARD_XRAY_NUSTAR_XMM_RGS_ALMA_B9B10_AND_700STAR_SYNTHESIS",
        "locked_utc": now_iso,
        "projected_unified_stars": int(uni102["unique_stars_total"]) + len(brand_new_coords),
        "projected_within_10pc_stars": int(uni102["within_10pc_unique_stars"]) + n_new_10pc,
        "d103_brand_new_stars": len(brand_new_coords),
        "d103_prior_bridges": len(bridge_stars),
        "d103_total_observations": len(frozen_rows),
        "d103_total_physical_files": total_phys_files,
        "d103_projected_bytes": proj_bytes,
        "d103_projected_mib": round(proj_bytes / (1024.0 * 1024.0), 4),
        "stage_1_files": hashes,
    }, indent=2) + "\n")

    (WS / "LOCK_RECEIPT.json").write_text(json.dumps({
        "schema": "D103_LOCK_RECEIPT",
        "phase_id": "D103",
        "status": "STAGE-1 SEALED",
        "locked_utc": now_iso,
        "locked_unix_epoch": now_epoch,
        "method_lock_sha256": _sha256_file(ml_path),
        "inputs_dir_exists_at_seal": RAW_DIR.exists(),
        "locked_files": hashes,
    }, indent=2) + "\n")

    print(
        f"Stage-1 SEALED: {len(frozen_rows)} obs ({total_phys_files} files), "
        f"{len(all_stars_d103)} stars ({len(brand_new_coords)} new + {len(bridge_stars)} bridges), "
        f"projected unified={int(uni102['unique_stars_total']) + len(brand_new_coords)}, "
        f"within_10pc=+{n_new_10pc} (-> {int(uni102['within_10pc_unique_stars']) + n_new_10pc}), "
        f"min_prior_sep={min_prior_sep:.2f}\", min_intra_sep={min_intra_sep:.2f}\", "
        f"raw_dir_exists={RAW_DIR.exists()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
