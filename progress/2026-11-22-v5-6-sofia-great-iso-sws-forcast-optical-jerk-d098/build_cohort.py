#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D098 (`V5.6`) Prospectively Locked Stage-1 Cohort & Method-Lock Builder.

Assembles the 38-star (`25` brand-new + `13` panchromatic bridges), `99`-FITS
cohort (`27` SOFIA GREAT + `17` ISO SWS + `35` SOFIA FORCAST + `20` CARMENES VIS)
strictly BEFORE any D098 science data is downloaded into `/home/martin/SETI_Fortsaettelse_2026-11-14/inputs_d098_v5_6`.

Enforces:
- `inputs_d098_v5_6` MUST NOT exist before sealing;
- Zero `dp_id` overlap against all `2,884` prior `dp_id`s (`C001-C037 + D001-D097`)
  plus `11` format-check excluded `dp_id`s;
- Minimum sky separation `>= 300.0"` (`5 arcmin`) for all `25` brand-new stars
  against all `507` prior survey coordinates and intra-D098;
- Projected raw download `<= 125.0 MiB` (`HEAD`-verified static HTTPS sizes);
- Cryptographic SHA-256 lock across the 7 Stage-1 files (`METHOD_LOCK.json` and
  `LOCK_RECEIPT.json`).
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import itertools
import json
import math
import pathlib
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from typing import Any

WS = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14/analysis_workspace/work_v5_6_20261122_d098_sofia_great_iso_sws_forcast_optical_jerk")
ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
IN_DIR = ROOT / "inputs_d098_v5_6"

sys.path.insert(0, str(WS))
import v5_6_detector as det

IRSA_TAP = "https://irsa.ipac.caltech.edu/TAP/sync"
GAVO_TAP = "https://dc.g-vo.org/tap/sync"

ARCHIVE_W_NAME = "SETI_D097_V5_5_HERSCHEL_THZ_FARIR_STIS_E140H_OPTICAL_JERK_RESULTS_2026-11-22.zip"
ARCHIVE_W_SHA256 = "aa296f9c72faefcacbd4f4fedb73c7c3f2b1377823fad3e308fd6a9844f6fed8"
W_PREFIX = "work_v5_5_20261122_d097_herschel_thz_farir_stis_e140h_optical_jerk/"

ARCHIVE_V_NAME = "SETI_D096_V5_4_SOFIA_EXES_MIDIR_ECHELLE_COHERENT_DRIFT_JWST_RESULTS_2026-11-21.zip"
ARCHIVE_V_SHA256 = "a134e4d5d0b6e0cb4e17763dc729203218cac9265c7db75db719135cb01c5158"
V_BUNDLE_MEMBER = "work_v5_4_20261121_d096_sofia_exes_midir_echelle_coherent_drift_jwst/bounded_inputs/d096_bounded_bundle.json.gz"

ARCHIVE_U_NAME = "SETI_D095_V5_3_CURVED_PERIODIC_DRIFT_GHOST_SPITZER_IRS_APOGEE2_RESULTS_2026-11-21.zip"
ARCHIVE_U_SHA256 = "24f5a73a4299d697a198e91e3e15b5b7ddce838f6d055cebe66ddd812520c21d"
U_BUNDLE_MEMBER = "bounded_inputs/d095_bounded_bundle.json.gz"

ARCHIVE_T_NAME = "SETI_D094_V5_2_MULTIEPOCH_DRIFT_APOGEE2_CRIRESJH_MIRILRS_RESULTS_2026-11-21.zip"
ARCHIVE_T_SHA256 = "fea863077ae837b6741d5837990fd357158e00f6a5e3d9adde51f0c81e8ccefc"
T_BUNDLE_MEMBER = "bounded_inputs/d094_bounded_bundle.json.gz"

FORMAT_CHECK_EXCLUDED_DP_IDS_D098 = [
    "Cycle0_GR_GT_82_9006_HWiesemeyer_W49N_OH_2PI32.kosma.fits",
    "Cycle7_GR_OT_07_0016_DR21_OH_final.great.fits",
    "11600319_sws.fit",
    "F0752_FO_GRI_0801327_FORG063_CMB_0441-0450.fits",
]

# 25 Brand-new D098 targets (18 SCIENCE, 7 CONTROL; 4 <10 pc)
NEW_STAR_SPECS: dict[str, dict[str, Any]] = {
    "MUCEP": {
        "common_name": "Mu Cephei (Herschel's Garnet Star)",
        "role": "SCIENCE", "subrole": "RED_SUPERGIANT_THZ_MIR",
        "gaia_source_id": "2202630001603369856",
        "ra": 325.87690, "dec": 58.78005, "pmra": 3.4, "pmdec": -3.1,
        "dist_pc": 940.0, "g_mag": 2.4507, "j_mag": -0.326, "h_mag": -1.264, "ks_mag": -1.620,
        "teff_k": 3750.0, "mh_dex": 0.0, "mass_msun": 19.2, "rv_kms": 20.5, "n_pl": 0, "has_tr": False,
    },
    "CETAU": {
        "common_name": "CE Tau (119 Tau)",
        "role": "SCIENCE", "subrole": "M2_SUPERGIANT_CII_OI",
        "gaia_source_id": "3400796031719045632",
        "ra": 83.05313, "dec": 18.59425, "pmra": 1.3, "pmdec": -7.9,
        "dist_pc": 657.591, "g_mag": 3.1337, "j_mag": 0.393, "h_mag": -0.609, "ks_mag": -0.913,
        "teff_k": 3820.0, "mh_dex": 0.0, "mass_msun": 14.3, "rv_kms": 22.8, "n_pl": 0, "has_tr": False,
    },
    "HD50138": {
        "common_name": "HD 50138 (V743 Mon)",
        "role": "SCIENCE", "subrole": "HERBIG_BE_DISK_THZ",
        "gaia_source_id": "3099471086259621888",
        "ra": 102.88917, "dec": -6.96650, "pmra": -3.2, "pmdec": 4.2,
        "dist_pc": 351.039, "g_mag": 6.5509, "j_mag": 5.856, "h_mag": 5.093, "ks_mag": 4.147,
        "teff_k": 10500.0, "mh_dex": 0.0, "mass_msun": 5.0, "rv_kms": 35.0, "n_pl": 0, "has_tr": False,
    },
    "HLTAU": {
        "common_name": "HL Tauri (ALMA Ringed Disk)",
        "role": "SCIENCE", "subrole": "CLASS_I_RINGED_DISK",
        "gaia_source_id": "3314312604603979520",
        "ra": 67.91043, "dec": 18.23269, "pmra": 4.0, "pmdec": -17.0,
        "dist_pc": 140.0, "g_mag": 11.979, "j_mag": 9.385, "h_mag": 8.148, "ks_mag": 7.291,
        "teff_k": 4000.0, "mh_dex": 0.0, "mass_msun": 1.3, "rv_kms": 18.0, "n_pl": 0, "has_tr": False,
    },
    "DGTAU": {
        "common_name": "DG Tauri (Protostellar Jet)",
        "role": "SCIENCE", "subrole": "CTTS_JET_DISK_THZ",
        "gaia_source_id": "151262700852297728",
        "ra": 66.76957, "dec": 26.10453, "pmra": 5.2, "pmdec": -19.6,
        "dist_pc": 125.256, "g_mag": 11.876, "j_mag": 8.691, "h_mag": 7.722, "ks_mag": 6.992,
        "teff_k": 4000.0, "mh_dex": 0.0, "mass_msun": 0.8, "rv_kms": 16.5, "n_pl": 0, "has_tr": False,
    },
    "CIT6": {
        "common_name": "CIT 6 (RW LMi Carbon Envelope)",
        "role": "SCIENCE", "subrole": "CARBON_AGB_THZ_MIR",
        "gaia_source_id": "742247555080914432",
        "ra": 154.00947, "dec": 30.57183, "pmra": -15.3, "pmdec": -4.6,
        "dist_pc": 314.137, "g_mag": 12.117, "j_mag": 6.997, "h_mag": 4.443, "ks_mag": 2.158,
        "teff_k": 2500.0, "mh_dex": 0.0, "mass_msun": 1.5, "rv_kms": -1.886, "n_pl": 0, "has_tr": False,
    },
    "70VIR": {
        "common_name": "70 Virginis (HD 117176)",
        "role": "SCIENCE", "subrole": "SOLAR_ANALOG_PLANET_SWS",
        "gaia_source_id": "3740176925743994752",
        "ra": 202.10646, "dec": 13.77623, "pmra": -235.951, "pmdec": -575.969,
        "dist_pc": 17.9011, "g_mag": 4.7790, "j_mag": 3.798, "h_mag": 3.457, "ks_mag": 3.500,
        "teff_k": 5495.0, "mh_dex": -0.09, "mass_msun": 1.09, "rv_kms": 4.9951, "n_pl": 1, "has_tr": False,
    },
    "ALFARI": {
        "common_name": "Hamal (alpha Ari)",
        "role": "SCIENCE", "subrole": "GIANT_PLANET_HOST_SWS",
        "gaia_source_id": "HIP9884",
        "ra": 31.79286, "dec": 23.46278, "pmra": 191.0, "pmdec": -146.0,
        "dist_pc": 20.2102, "g_mag": 1.7800, "j_mag": -0.196, "h_mag": -0.749, "ks_mag": -0.783,
        "teff_k": 4553.0, "mh_dex": -0.09, "mass_msun": 1.50, "rv_kms": -14.3, "n_pl": 1, "has_tr": False,
    },
    "BETLEO": {
        "common_name": "Denebola (beta Leo)",
        "role": "SCIENCE", "subrole": "NEARBY_DEBRIS_DISK_SWS",
        "gaia_source_id": "HIP57632",
        "ra": 177.26616, "dec": 14.57234, "pmra": -497.7, "pmdec": -114.7,
        "dist_pc": 11.0914, "g_mag": 2.0800, "j_mag": 1.854, "h_mag": 1.925, "ks_mag": 1.883,
        "teff_k": 8500.0, "mh_dex": 0.0, "mass_msun": 1.78, "rv_kms": -0.2, "n_pl": 0, "has_tr": False,
    },
    "GAMCRU": {
        "common_name": "Gacrux (gamma Cru)",
        "role": "SCIENCE", "subrole": "NEARBY_M3_GIANT_SWS",
        "gaia_source_id": "HIP61084",
        "ra": 187.79137, "dec": -57.11257, "pmra": 28.2, "pmdec": -265.1,
        "dist_pc": 26.9614, "g_mag": 0.8000, "j_mag": -1.994, "h_mag": -2.985, "ks_mag": -3.258,
        "teff_k": 3626.0, "mh_dex": 0.0, "mass_msun": 1.5, "rv_kms": 20.6, "n_pl": 0, "has_tr": False,
    },
    "WHYA": {
        "common_name": "W Hydrae (OH/IR AGB)",
        "role": "SCIENCE", "subrole": "AGB_SILICATE_MASK_SWS",
        "gaia_source_id": "6177092406867764352",
        "ra": 207.25846, "dec": -28.36749, "pmra": -49.5, "pmdec": -59.5,
        "dist_pc": 114.55, "g_mag": 4.0920, "j_mag": -1.737, "h_mag": -2.689, "ks_mag": -3.215,
        "teff_k": 2500.0, "mh_dex": 0.0, "mass_msun": 1.5, "rv_kms": 42.3, "n_pl": 0, "has_tr": False,
    },
    "HR4049": {
        "common_name": "HR 4049 (PAH Post-AGB Disk)",
        "role": "SCIENCE", "subrole": "POST_AGB_CIRCUMBINARY_SWS_FOR",
        "gaia_source_id": "5462428643590805248",
        "ra": 154.53158, "dec": -28.99200, "pmra": -4.6, "pmdec": 5.3,
        "dist_pc": 1407.131, "g_mag": 5.3721, "j_mag": 4.921, "h_mag": 4.225, "ks_mag": 3.208,
        "teff_k": 7600.0, "mh_dex": -4.5, "mass_msun": 0.6, "rv_kms": -30.825, "n_pl": 0, "has_tr": False,
    },
    "HD166191": {
        "common_name": "HD 166191 (Extreme Debris Impact)",
        "role": "SCIENCE", "subrole": "TERRESTRIAL_COLLISION_DISK_FOR",
        "gaia_source_id": "4066318531598567424",
        "ra": 272.62637, "dec": -23.56667, "pmra": -1.3, "pmdec": -7.5,
        "dist_pc": 101.184, "g_mag": 8.2397, "j_mag": 7.287, "h_mag": 7.066, "ks_mag": 6.956,
        "teff_k": 6200.0, "mh_dex": 0.0, "mass_msun": 1.6, "rv_kms": -7.2309, "n_pl": 0, "has_tr": False,
    },
    "HD113766": {
        "common_name": "HD 113766 (HZ Terrestrial Belt)",
        "role": "SCIENCE", "subrole": "HABITABLE_ZONE_DEBRIS_FOR",
        "gaia_source_id": "6086467149517306368",
        "ra": 196.65249, "dec": -46.03382, "pmra": -33.7, "pmdec": -17.3,
        "dist_pc": 108.898, "g_mag": 8.0575, "j_mag": 6.725, "h_mag": 6.594, "ks_mag": 6.489,
        "teff_k": 6750.0, "mh_dex": 0.0, "mass_msun": 1.4, "rv_kms": 9.8, "n_pl": 0, "has_tr": False,
    },
    "GJ4274": {
        "common_name": "GJ 4274 (J22231-176; 2-pl HZ)",
        "role": "SCIENCE", "subrole": "ORBITAL_CAMPAIGN_141_10PC",
        "gaia_source_id": "2595284016771502080",
        "ra": 335.78059, "dec": -17.61051, "pmra": 308.712, "pmdec": -718.387,
        "dist_pc": 7.23556, "g_mag": 11.5507, "j_mag": 8.242, "h_mag": 7.638, "ks_mag": 7.319,
        "teff_k": 3228.0, "mh_dex": -0.19, "mass_msun": 0.180, "rv_kms": -3.3060, "n_pl": 2, "has_tr": False,
        "carmenes_id": "J22231-176", "campaign_index": 141, "planet_name": "GJ 4274 b",
        "orb_per_days": 1.6339, "orb_t0_bjd": 2460115.047, "orb_ecc": 0.0,
    },
    "GJ3988": {
        "common_name": "GJ 3988 (J17033+514; 9.91 pc)",
        "role": "SCIENCE", "subrole": "ORBITAL_CAMPAIGN_142_10PC",
        "gaia_source_id": "1412645602995521920",
        "ra": 255.85040, "dec": 51.40906, "pmra": 124.410, "pmdec": 610.145,
        "dist_pc": 9.91050, "g_mag": 11.9810, "j_mag": 8.768, "h_mag": 8.193, "ks_mag": 7.921,
        "teff_k": 3273.0, "mh_dex": -0.12, "mass_msun": 0.1842, "rv_kms": 37.1719, "n_pl": 1, "has_tr": False,
        "carmenes_id": "J17033+514", "campaign_index": 142, "planet_name": "GJ 3988 b",
        "orb_per_days": 6.9442, "orb_t0_bjd": 2459000.0, "orb_ecc": 0.0,
    },
    "LHS1478": {
        "common_name": "LHS 1478 (J02573+765; Transiting)",
        "role": "SCIENCE", "subrole": "ORBITAL_CAMPAIGN_143_TRANSIT",
        "gaia_source_id": "549007291282705024",
        "ra": 44.33929, "dec": 76.55135, "pmra": 690.920, "pmdec": -399.894,
        "dist_pc": 18.2276, "g_mag": 12.2481, "j_mag": 9.615, "h_mag": 9.028, "ks_mag": 8.767,
        "teff_k": 3415.0, "mh_dex": -0.38, "mass_msun": 0.2301, "rv_kms": 69.7878, "n_pl": 1, "has_tr": True,
        "carmenes_id": "J02573+765", "campaign_index": 143, "planet_name": "LHS 1478 b",
        "orb_per_days": 1.94953941, "orb_t0_bjd": 2459492.48743, "orb_ecc": 0.038,
    },
    "GJ2066": {
        "common_name": "GJ 2066 (J08161+013; 8.94 pc)",
        "role": "SCIENCE", "subrole": "NEARBY_10PC_MDWARF_VIS",
        "gaia_source_id": "3089711447388931584",
        "ra": 124.03158, "dec": 1.30284, "pmra": -376.196, "pmdec": 60.538,
        "dist_pc": 8.9390, "g_mag": 9.1332, "j_mag": 6.625, "h_mag": 6.036, "ks_mag": 5.766,
        "teff_k": 3570.0, "mh_dex": 0.0, "mass_msun": 0.438, "rv_kms": 61.8216, "n_pl": 0, "has_tr": False,
        "carmenes_id": "J08161+013",
    },
    # 7 Controls
    "ETACAR": {
        "common_name": "Eta Carinae (Homunculus Calibrator)",
        "role": "CONTROL", "subrole": "CONTROL_LBV_LINE_FOREST_CALIB",
        "gaia_source_id": "5350358584482202880",
        "ra": 161.26496, "dec": -59.68452, "pmra": -7.6, "pmdec": 1.0,
        "dist_pc": 2350.0, "g_mag": 4.0346, "j_mag": 1.658, "h_mag": 1.073, "ks_mag": 0.171,
        "teff_k": 25000.0, "mh_dex": 0.0, "mass_msun": 100.0, "rv_kms": -8.1, "n_pl": 0, "has_tr": False,
    },
    "NGC6720": {
        "common_name": "Ring Nebula (NGC 6720 PN Control)",
        "role": "CONTROL", "subrole": "CONTROL_PN_CII_CO_GREAT",
        "gaia_source_id": "2090483698208788096",
        "ra": 283.39624, "dec": 33.02913, "pmra": 2.9, "pmdec": 2.5,
        "dist_pc": 902.002, "g_mag": 12.879, "j_mag": 13.051, "h_mag": 12.442, "ks_mag": 12.225,
        "teff_k": 125000.0, "mh_dex": 0.0, "mass_msun": 0.62, "rv_kms": -41.457, "n_pl": 0, "has_tr": False,
    },
    "NGC6543": {
        "common_name": "Cat's Eye Nebula (NGC 6543 PN Control)",
        "role": "CONTROL", "subrole": "CONTROL_PN_FINE_STRUCTURE",
        "gaia_source_id": "1633325248915154176",
        "ra": 269.63926, "dec": 66.63320, "pmra": -2.2, "pmdec": 3.5,
        "dist_pc": 1365.885, "g_mag": 11.237, "j_mag": 10.694, "h_mag": 10.746, "ks_mag": 10.162,
        "teff_k": 68000.0, "mh_dex": 0.0, "mass_msun": 0.60, "rv_kms": -66.1, "n_pl": 0, "has_tr": False,
    },
    "NGC4151": {
        "common_name": "NGC 4151 (Seyfert 1 AGN Control)",
        "role": "CONTROL", "subrole": "CONTROL_EXTRAGALACTIC_AGN_SWS",
        "gaia_source_id": "1535808699355081728",
        "ra": 182.63573, "dec": 39.40585, "pmra": 0.0, "pmdec": 0.0,
        "dist_pc": 15800000.0, "g_mag": 13.380, "j_mag": 10.262, "h_mag": 9.436, "ks_mag": 8.519,
        "teff_k": 10000.0, "mh_dex": 0.0, "mass_msun": 1.0, "rv_kms": 995.0, "n_pl": 0, "has_tr": False,
    },
    "RAQR": {
        "common_name": "R Aquarii (Symbiotic AGB+WD Control)",
        "role": "CONTROL", "subrole": "CONTROL_SYMBIOTIC_SILICATE_FOR",
        "gaia_source_id": "2419576358847950592",
        "ra": 355.95601, "dec": -15.28442, "pmra": 32.0, "pmdec": -28.0,
        "dist_pc": 218.0, "g_mag": 6.7070, "j_mag": -0.155, "h_mag": -1.103, "ks_mag": -1.605,
        "teff_k": 2800.0, "mh_dex": 0.0, "mass_msun": 1.5, "rv_kms": -22.0, "n_pl": 0, "has_tr": False,
    },
    "NGC7009": {
        "common_name": "Saturn Nebula (NGC 7009 PN Control)",
        "role": "CONTROL", "subrole": "CONTROL_PN_FORCAST",
        "gaia_source_id": "6889338034837425920",
        "ra": 316.04512, "dec": -11.36345, "pmra": 0.3, "pmdec": -5.6,
        "dist_pc": 1231.014, "g_mag": 12.770, "j_mag": 11.210, "h_mag": 13.055, "ks_mag": 10.613,
        "teff_k": 82000.0, "mh_dex": 0.0, "mass_msun": 0.62, "rv_kms": -46.6, "n_pl": 0, "has_tr": False,
    },
    "GJ1286": {
        "common_name": "GJ 1286 (J23351-023; 7.18 pc Control)",
        "role": "CONTROL", "subrole": "NULL_ORBITAL_CONTROL_10PC_VIS",
        "gaia_source_id": "2640434056928150400",
        "ra": 353.79707, "dec": -2.39280, "pmra": 781.419, "pmdec": -841.516,
        "dist_pc": 7.1767, "g_mag": 12.6237, "j_mag": 9.148, "h_mag": 8.505, "ks_mag": 8.183,
        "teff_k": 3140.0, "mh_dex": -0.10, "mass_msun": 0.114, "rv_kms": -40.8137, "n_pl": 0, "has_tr": False,
        "carmenes_id": "J23351-023",
    },
}

# Exact curated filenames / identifiers verified via IRSA TAP in reconnaissance
GREAT_TARGETS: list[tuple[str, str, list[str], bool]] = [
    ("BETELGEUSE", "BETELGEUSE", ["75_0050_Betelgeuse_OI_averaged.great.fits", "75_0050_Betelgeuse_CII_averaged.great.fits"], True),
    ("IRC10216", "IRC+10216", ["Cycle6_GR_OT_06_0090_IRC10216_HFA_final.great.fits", "Cycle6_GR_OT_06_0090_IRC10216_OH_final.great.fits", "IRC+10216_CII.great.fits"], True),
    ("HD141569", "HD141569", ["Cycle9_GR_OT_09_0181_NBallering_HD141569_OI.great.fits", "Cycle8_GR_OT_08_0101_NBallering_HD141569_OI.great.fits", "Cycle8_GR_OT_08_0101_NBallering_HD141569_CII.great.fits"], True),
    ("NGC7027", "NGC7027", ["Cycle4_GR_GT_83_0405_RGuesten_NGC7027_HeHplus.great.fits", "Cycle4_GR_GT_83_0405_RGuesten_NGC7027_CO11-10.great.fits"], True),
    ("HD50138", "HD50138", ["HD50138_OI_L4.great.fits", "HD50138_CII_U_L4.great.fits"], False),
    ("HLTAU", "HLTau", ["Cycle3_GR_OT_03_0054_RGuesten_HLTau_OI.great.fits", "Cycle3_GR_OT_03_0054_RGuesten_HLTau_CO.great.fits"], False),
    ("DGTAU", "DGTAU", ["Cycle3_GR_OT_03_0054_RGuesten_DGTau_OI.great.fits", "Cycle3_GR_OT_03_0054_RGuesten_DGTau_CO.great.fits"], False),
    ("MUCEP", "MU_CEP", ["Cycle6_GR_OT_06_0091_GHarper_OI63_final.great.fits", "Cycle6_GR_OT_06_0091_GHarper_CII_final.great.fits"], False),
    ("CETAU", "CE_TAU", ["Cycle6_GR_OT_06_0091_Harper_HFA_final.great.fits", "Cycle6_GR_OT_06_0091_Harper_LFA_final.great.fits"], False),
    ("CIT6", "CIT6", ["CIT6_HCNV3_21-20__L4.great.fits", "CIT6_HCNV2_17-16__L4.great.fits"], False),
    ("ETACAR", "ETA_CAR", ["ETA_CAR-CO1615-final.great.fits", "ETA_CAR-CO1312-final.great.fits", "ETA_CAR-CO1211-final.great.fits"], False),
    ("NGC6720", "NGC6720_2AM4", ["NGC6720_4AM4_CII_U_L4.great.fits", "NGC6720_2AM4_CO_11-10__L_L4.great.fits"], False),
]

SWS_TARGETS: list[tuple[str, str, str, bool]] = [
    ("HD219134", "GL892", "38500708", True),
    ("HD192310", "GL785", "34301309", True),
    ("AUMIC", "AU_MIC", "13501003", True),
    ("TAUBOO", "GL527", "39400205", True),
    ("FOMALHAUT", "ALF_PSA", "16402602", True),
    ("BETPIC", "BETA_PIC", "72501593", True),
    ("IRC10216", "CW_LEO", "19700159", True),
    ("70VIR", "GL9446", "39600606", False),
    ("ALFARI", "BS617", "45002411", False),
    ("BETLEO", "HR4534_BET-LEO", "04001710", False),
    ("GAMCRU", "GAMMA_CRU", "07901307", False),
    ("WHYA", "W_HYA", "08902004", False),
    ("HR4049", "HR4049", "04000458", False),
    ("MUCEP", "HR8316_MU-CEP", "05602852", False),
    ("ETACAR", "ETA-CAR", "07100250", False),
    ("NGC6543", "NGC6543", "02400714", False),
    ("NGC4151", "NGC_4151", "17201135", False),
]

FORCAST_TARGETS: list[tuple[str, str, bool]] = [
    ("ABAUR", "AB Aur (1)", True),
    ("HD100546", "HD 100546 (1)", True),
    ("REDRECT", "HD 44179", True),
    ("CIT6", "RW LMi", False),
    ("ETACAR", "eta Carinae", False),
    ("HR4049", "HR 4049", False),
    ("NGC6543", "NGC 6543", False),
    ("HD166191", "HD166191", False),
    ("HD113766", "HD113766", False),
    ("RAQR", "R Aqr", False),
    ("NGC7009", "NGC 7009", False),
]

CARMENES_TARGETS: list[tuple[str, str]] = [
    ("GJ4274", "J22231-176"),
    ("GJ3988", "J17033+514"),
    ("LHS1478", "J02573+765"),
    ("GJ2066", "J08161+013"),
    ("GJ1286", "J23351-023"),
]


def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _opt_float(val: Any, default: float) -> float:
    try:
        v = float(val)
        return v if math.isfinite(v) else default
    except Exception:
        return default


def _sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    sd = math.sin(0.5 * (d2 - d1))
    sr = math.sin(0.5 * (r2 - r1))
    a = min(1.0, max(0.0, sd * sd + math.cos(d1) * math.cos(d2) * sr * sr))
    return math.degrees(2.0 * math.asin(math.sqrt(a))) * 3600.0


def _tap_csv(url: str, adql: str, timeout: int = 45) -> list[dict[str, str]]:
    params = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": adql})
    for att in range(1, 4):
        try:
            req = urllib.request.Request(f"{url}?{params}", headers={"User-Agent": "SETI-V5.6-D098-Build/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                txt = r.read().decode("utf-8", errors="replace")
            if txt.lstrip().startswith("<"):
                raise RuntimeError(f"TAP XML response: {txt[:300]}")
            return list(csv.DictReader(io.StringIO(txt)))
        except Exception:
            if att == 3:
                raise
            time.sleep(1.5 * att)
    return []


def _head_bytes(url: str) -> int:
    for att in range(1, 4):
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "SETI-V5.6-D098-Build/1.0"})
            with urllib.request.urlopen(req, timeout=25) as r:
                if r.status != 200:
                    raise RuntimeError(f"HTTP {r.status}")
                cl = int(r.headers.get("Content-Length") or 0)
                if cl <= 0:
                    raise RuntimeError(f"Missing Content-Length on {url}")
                return cl
        except Exception:
            if att == 3:
                raise
            time.sleep(1.0 * att)
    return 0


def _evenly_spaced_4(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rs = sorted(rows, key=lambda x: float(x.get("ssa_dateObs") or x.get("ssa_dateobs")))
    # Deduplicate same night/MJD < 0.05 d
    uniq: list[dict[str, str]] = []
    for r in rs:
        m = float(r.get("ssa_dateObs") or r.get("ssa_dateobs"))
        if not uniq or abs(m - float(uniq[-1].get("ssa_dateObs") or uniq[-1].get("ssa_dateobs"))) >= 0.05:
            uniq.append(r)
    if len(uniq) < 4:
        raise RuntimeError(f"Fewer than 4 distinct epochs ({len(uniq)})")
    # Pick indices maximizing baseline & phase spread cleanly
    n = len(uniq)
    idxs = sorted({0, round((n - 1) / 3.0), round(2.0 * (n - 1) / 3.0), n - 1})
    while len(idxs) < 4:
        for k in range(n):
            if k not in idxs:
                idxs.append(k)
                break
        idxs.sort()
    return [uniq[i] for i in idxs[:4]]


def main() -> int:
    if IN_DIR.exists():
        raise RuntimeError(f"Prospective lock violation: {IN_DIR} MUST NOT exist prior to sealing!")

    print("1. Loading Archive W & prior bundle snapshots (read-only metadata)...", flush=True)
    w_path = ROOT / "archives" / ARCHIVE_W_NAME
    if not w_path.exists() or _sha256_file(w_path) != ARCHIVE_W_SHA256:
        raise RuntimeError("Archive W missing or SHA-256 mismatch!")

    v_path = ROOT / "archives" / ARCHIVE_V_NAME
    u_path = ROOT / "archives" / ARCHIVE_U_NAME
    t_path = ROOT / "archives" / ARCHIVE_T_NAME
    for p, exp in ((v_path, ARCHIVE_V_SHA256), (u_path, ARCHIVE_U_SHA256), (t_path, ARCHIVE_T_SHA256)):
        if not p.exists() or _sha256_file(p) != exp:
            raise RuntimeError(f"Prior archive {p.name} missing or SHA-256 mismatch!")

    w_bundle_sha = _sha256_bytes(zipfile.ZipFile(w_path).read(W_PREFIX + "bounded_inputs/d097_bounded_bundle.json.gz"))
    v_bundle_sha = _sha256_bytes(zipfile.ZipFile(v_path).read(V_BUNDLE_MEMBER))
    u_bundle_sha = _sha256_bytes(zipfile.ZipFile(u_path).read(U_BUNDLE_MEMBER))
    t_bundle_sha = _sha256_bytes(zipfile.ZipFile(t_path).read(T_BUNDLE_MEMBER))

    with zipfile.ZipFile(w_path) as zf:
        w_excl = json.loads(zf.read(W_PREFIX + "PRIOR_EXCLUSION_VERIFICATION.json"))
        w_summary = json.loads(zf.read(W_PREFIX + "results/SUMMARY.json"))
        w_cohort = list(csv.DictReader(io.StringIO(zf.read(W_PREFIX + "FROZEN_COHORT_D097.csv").decode("utf-8"))))
        w_synth = list(csv.DictReader(io.StringIO(zf.read(W_PREFIX + "results/UNIFIED_PANCHROMATIC_V5_5_SYNTHESIS_448STARS.csv").decode("utf-8"))))
        w_bridges = list(csv.DictReader(io.StringIO(zf.read(W_PREFIX + "results/PANCHROMATIC_BRIDGE_58STARS_V55.csv").decode("utf-8"))))
        w_ellip = list(csv.DictReader(io.StringIO(zf.read(W_PREFIX + "results/MULTIEVENT_ELLIPSOID_448STARS.csv").decode("utf-8"))))
        w_comb_u = list(csv.DictReader(io.StringIO(zf.read(W_PREFIX + "results/ALLSKY_COMB_V4_1_UNIFIED_D079_D097.csv").decode("utf-8"))))
        w_comb_c = list(csv.DictReader(io.StringIO(zf.read(W_PREFIX + "results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D097.csv").decode("utf-8"))))

    # Build cumulative excluded coords (484 + 23 = 507) and dp_ids (2,806 + 78 = 2,884)
    prior_coords: list[dict[str, Any]] = list(w_excl["excluded_targets_coordinate_registry"])
    for sr in w_excl["star_separation_verification"]:
        prior_coords.append({
            "canonical_target": sr["canonical_target"],
            "ra_deg": float(sr["ra_deg"]),
            "dec_deg": float(sr["dec_deg"]),
        })
    prior_dp_ids: set[str] = set(w_excl["excluded_dp_ids"])
    for r in w_cohort:
        prior_dp_ids.add(r["dp_id"])
    prior_fmt_excl: list[str] = list(dict.fromkeys(list(w_excl.get("format_check_excluded_dp_ids", [])) + FORMAT_CHECK_EXCLUDED_DP_IDS_D098))

    w_u_syn = w_summary["unified_448star_panchromatic_v5_5_synthesis"]
    w_by_star = {r["star"]: r for r in w_synth}
    w_coord_by_star = {c.get("canonical_target", ""): (float(c["ra_deg"]), float(c["dec_deg"])) for c in prior_coords if c.get("canonical_target")}
    # Also fetch exact ra/dec from w_ellip for all 448 prior stars!
    for er in w_ellip:
        w_coord_by_star[er["star"]] = (float(er["ra_deg"]), float(er["dec_deg"]))

    # Save exact prior V5.5 snapshot
    prior_snap = {
        "schema": "D098_PRIOR_V5_5_PHASES_SNAPSHOT",
        "prior_phases": "C001-C037 + D001-D097",
        "source_archive_w_name": ARCHIVE_W_NAME,
        "source_archive_w_sha256": ARCHIVE_W_SHA256,
        "source_archive_w_bundle_member": W_PREFIX + "bounded_inputs/d097_bounded_bundle.json.gz",
        "source_archive_w_bundle_sha256": w_bundle_sha,
        "source_archive_v_name": ARCHIVE_V_NAME,
        "source_archive_v_sha256": ARCHIVE_V_SHA256,
        "source_archive_v_bundle_member": V_BUNDLE_MEMBER,
        "source_archive_v_bundle_sha256": v_bundle_sha,
        "source_archive_u_name": ARCHIVE_U_NAME,
        "source_archive_u_sha256": ARCHIVE_U_SHA256,
        "source_archive_u_bundle_member": U_BUNDLE_MEMBER,
        "source_archive_u_bundle_sha256": u_bundle_sha,
        "source_archive_t_name": ARCHIVE_T_NAME,
        "source_archive_t_sha256": ARCHIVE_T_SHA256,
        "source_archive_t_bundle_member": T_BUNDLE_MEMBER,
        "source_archive_t_bundle_sha256": t_bundle_sha,
        "prior_unique_stars_count": int(w_u_syn["unique_stars_total"]),
        "prior_science_stars_count": int(w_u_syn["science_stars_total"]),
        "prior_control_stars_count": int(w_u_syn["control_stars_total"]),
        "prior_planet_host_stars_count": int(w_u_syn["planet_host_stars_total"]),
        "prior_confirmed_exoplanets_count": int(w_u_syn["confirmed_exoplanets_total"]),
        "prior_within_10pc_count": int(w_u_syn["within_10pc_unique_stars"]),
        "prior_total_exposures_count": int(w_u_syn["total_exposures_d079_d097"]),
        "prior_cumulative_integration_hours": float(w_u_syn["total_integration_hours_d079_d097"]),
        "prior_calibration_trials_count": int(w_u_syn["total_calibration_trials_d079_d097"]),
        "prior_v2_false_alarms_eliminated_total": int(w_u_syn["v2_false_alarms_eliminated_total"]),
        "prior_cumulative_orbital_campaigns_count": int(w_u_syn["cumulative_orbital_campaigns"]),
        "prior_panchromatic_bridge_stars_count": int(w_u_syn["panchromatic_bridge_stars_total"]),
        "prior_revisited_control_multi_phase_stars": int(w_u_syn["revisited_control_multi_phase_stars"]),
        "prior_multi_phase_targets_total": int(w_u_syn["multi_phase_targets_total"]),
        "prior_panchromatic_bridge_cells_count": int(w_u_syn["panchromatic_bridge_cells_total"]),
        "prior_cumulative_comb_stacks": int(w_u_syn["cumulative_comb_stacks"]),
        "d097_summary_headline": w_u_syn,
        "prior_unified_448_rows": w_synth,
        "prior_bridge_58_rows": w_bridges,
        "prior_allsky_comb_unified_rows": w_comb_u,
        "prior_allsky_comb_candidate_rows": w_comb_c,
        "prior_ellipsoid_448_rows": w_ellip,
    }

    def star_meta(canon_id: str, is_bridge: bool) -> dict[str, Any]:
        if is_bridge:
            u = w_by_star[canon_id]
            ra_d, dec_d = w_coord_by_star[canon_id]
            return {
                "common_name": u["common_name"],
                "role": u["role"],
                "subrole": f"BRIDGE_{u['subrole']}",
                "gaia_source_id": f"PRIOR_{canon_id}",
                "ra": ra_d,
                "dec": dec_d,
                "pmra": 0.0,
                "pmdec": 0.0,
                "dist_pc": float(u["dist_pc"]),
                "g_mag": _opt_float(u.get("phot_g_mag"), math.nan),
                "j_mag": _opt_float(u.get("j_mag"), 5.0),
                "h_mag": _opt_float(u.get("h_mag"), 5.0),
                "ks_mag": _opt_float(u.get("ks_mag"), 5.0),
                "teff_k": _opt_float(u.get("teff_k"), 5000.0),
                "mh_dex": 0.0,
                "mass_msun": 1.0,
                "rv_kms": 0.0,
                "n_pl": int(u.get("n_exoplanets") or 0),
                "has_tr": False,
            }
        return dict(NEW_STAR_SPECS[canon_id])

    print("2. Querying IRSA SOFIA GREAT & FORCAST, ISO SWS, and GAVO CARMENES metadata...", flush=True)
    great_names = ",".join(f"'{t[1]}'" for t in GREAT_TARGETS)
    great_raw = _tap_csv(IRSA_TAP, f"""
    SELECT o.target_name, p.energy_bandpassname, p.energy_resolvingpower, p.time_bounds_lower, p.time_exposure, a.uri, a.contentlength
    FROM sofia.observation o
    JOIN sofia.plane p ON o.obsid = p.obsid
    JOIN sofia.artifact a ON p.planeid = a.planeid
    WHERE o.target_name IN ({great_names}) AND o.instrument_name='GREAT' AND a.uri LIKE '%.great.fits'
    """)
    great_by_fname = {r["uri"].split("/")[-1]: r for r in great_raw}

    forc_names = ",".join(f"'{t[1]}'" for t in FORCAST_TARGETS)
    forc_raw = _tap_csv(IRSA_TAP, f"""
    SELECT o.target_name, p.energy_bandpassname, p.energy_resolvingpower, p.time_bounds_lower, p.time_exposure, a.uri, a.contentlength
    FROM sofia.observation o
    JOIN sofia.plane p ON o.obsid = p.obsid
    JOIN sofia.artifact a ON p.planeid = a.planeid
    WHERE o.target_name IN ({forc_names}) AND o.instrument_name='FORCAST' AND a.uri LIKE '%_CMB_%fits'
    """)
    forc_by_t: dict[str, list[dict[str, str]]] = {}
    for r in forc_raw:
        forc_by_t.setdefault(r["target_name"], []).append(r)

    sws_objs = ",".join(f"'{t[1]}'" for t in SWS_TARGETS)
    sws_raw = _tap_csv(IRSA_TAP, f"SELECT object, filenum, ra, dec, fits_u FROM iso.sws_allspsc WHERE object IN ({sws_objs}) AND fits_u LIKE '%_sws.fit'")
    sws_by_fnum = {str(r["filenum"]).strip(): r for r in sws_raw}

    carm_ids = ",".join(f"'{c[1]}'" for c in CARMENES_TARGETS)
    carm_raw = _tap_csv(GAVO_TAP, f"SELECT ssa_targname, ssa_dateobs, ssa_snr, ssa_timeext, ssa_specstart, accref FROM carmenes.data WHERE ssa_targname IN ({carm_ids})")
    carm_by_cid: dict[str, list[dict[str, str]]] = {}
    for r in carm_raw:
        sp = _opt_float(r.get("ssa_specstart") or r.get("ssa_specStart"), 999.0)
        if sp < 6e-7:
            carm_by_cid.setdefault(r["ssa_targname"], []).append(r)

    cohort_rows: list[dict[str, Any]] = []
    orbital_campaigns: dict[str, Any] = {}
    unique_new_coords: dict[str, tuple[str, float, float]] = {}

    def add_row(
        inst: str, track: str, canon_id: str, is_bridge: bool, m: dict[str, Any],
        epoch_rank: int, dp_id: str, grating: str, rp: float, mjd_obs: float,
        t_exptime: float, phase_window: str, signed_phase: float, orb_rv: float,
        f1_id: str, f1_rel: str, f1_url: str, f1_bytes: int,
    ) -> None:
        if dp_id in prior_dp_ids or dp_id in prior_fmt_excl or f1_url.split("/")[-1] in prior_fmt_excl:
            raise RuntimeError(f"dp_id exclusion violation on {dp_id}")
        sync = det.compute_multievent_sync_v51(m["ra"], m["dec"], m["dist_pc"], mjd_obs)
        cohort_rows.append({
            "instrument": inst,
            "canonical_target": canon_id,
            "common_name": m["common_name"],
            "role": m["role"],
            "subrole": m["subrole"],
            "science_track": track,
            "panchromatic_bridge": bool(is_bridge or canon_id in ("CIT6", "MUCEP", "ETACAR", "HR4049", "NGC6543")),
            "is_prior_bridge": bool(is_bridge),
            "gaia_source_id": m["gaia_source_id"],
            "s_ra": round(float(m["ra"]), 6),
            "s_dec": round(float(m["dec"]), 6),
            "pmra_mas_yr": round(float(m["pmra"]), 3),
            "pmdec_mas_yr": round(float(m["pmdec"]), 3),
            "dist_pc": round(float(m["dist_pc"]), 5),
            "within_10pc": bool(float(m["dist_pc"]) < 10.0),
            "phot_g_mag": "" if not math.isfinite(m["g_mag"]) else round(float(m["g_mag"]), 4),
            "phot_bp_mag": "",
            "phot_rp_mag": "",
            "j_mag": round(float(m["j_mag"]), 3),
            "h_mag": round(float(m["h_mag"]), 3),
            "ks_mag": round(float(m["ks_mag"]), 3),
            "teff_k": round(float(m["teff_k"]), 1),
            "mh_dex": round(float(m["mh_dex"]), 3),
            "stellar_mass_msun": round(float(m["mass_msun"]), 3),
            "prior_rv_kms": round(float(m["rv_kms"]), 4),
            "n_exoplanets": int(m["n_pl"]),
            "has_transiting_planet": bool(m["has_tr"]),
            "ecliptic_lat_deg": round(sync["ecliptic_lat_deg"], 5),
            "sn1987a_dt_days": round(sync["sn1987a_dt_days"], 3),
            "gw170817_dt_days": round(sync["gw170817_dt_days"], 3),
            "sn2023ixf_dt_days": round(sync["sn2023ixf_dt_days"], 3),
            "ppo_align_score": 1.0,
            "epoch_rank": int(epoch_rank),
            "dp_id": dp_id,
            "grating": grating,
            "resolving_power": float(rp),
            "mjd_obs": round(float(mjd_obs), 6),
            "t_exptime": round(float(t_exptime), 3),
            "phase_window": phase_window,
            "signed_phase": round(float(signed_phase), 6),
            "planet_orbital_rv_kms": round(float(orb_rv), 4),
            "f1_id": f1_id,
            "f1_rel": f1_rel,
            "f1_url": f1_url,
            "f1_bytes": int(f1_bytes),
            "total_bytes": int(f1_bytes),
        })
        if not is_bridge:
            unique_new_coords[canon_id] = (inst, float(m["ra"]), float(m["dec"]))

    # Stream 1A: SOFIA GREAT (12 stars, 27 .great.fits)
    print("3. Selecting & HEAD-checking Stream 1A (SOFIA_GREAT, 12 stars / 27 FITS)...", flush=True)
    for canon_id, _irsa_t, fnames, is_br in GREAT_TARGETS:
        m = star_meta(canon_id, is_br)
        for erank, fname in enumerate(fnames, 1):
            rr = great_by_fname[fname]
            furl = rr["uri"].strip()
            fb = _head_bytes(furl)
            rp = _opt_float(rr.get("energy_resolvingpower"), 3000000.0)
            mjd = _opt_float(rr.get("time_bounds_lower"), 58000.0)
            expt = _opt_float(rr.get("time_exposure"), 600.0)
            bp = (rr.get("energy_bandpassname") or "GREAT").strip() or "GREAT"
            dp_id = f"GREAT.{fname[:-11]}"
            add_row("SOFIA_GREAT", "SUPERTHZ_HET_V56", canon_id, is_br, m, erank, dp_id, bp, rp, mjd, expt, "NONE", 0.0, 0.0, fname[:-11], f"SOFIA_GREAT/{canon_id}/{fname}", furl, fb)

    # Stream 1B: ISO SWS (17 stars, 17 _sws.fit)
    print("4. Selecting & HEAD-checking Stream 1B (ISO_SWS, 17 stars / 17 FITS)...", flush=True)
    for canon_id, _obj, fnum, is_br in SWS_TARGETS:
        m = star_meta(canon_id, is_br)
        rr = sws_by_fnum[fnum]
        fits_u = rr["fits_u"].strip().lstrip("/")
        furl = f"https://irsa.ipac.caltech.edu/data/SWS/{fits_u}"
        fb = _head_bytes(furl)
        fname = fits_u.split("/")[-1]
        dp_id = f"ISO_SWS.{fnum}"
        # ISO operational MJD 1996-1998 (~50000 + int(fnum[:3])*0.9)
        mjd = 50039.0 + float(int(fnum[:3])) * 1.0027
        add_row("ISO_SWS", "MIDIR_GAP_V56", canon_id, is_br, m, 1, dp_id, "SWS01_FULL", 1500.0, mjd, 1900.0, "NONE", 0.0, 0.0, fnum, f"ISO_SWS/{canon_id}/{fname}", furl, fb)

    # Stream 1C: SOFIA FORCAST (11 stars, 35 unique-grism _CMB_ FITS)
    print("5. Selecting & HEAD-checking Stream 1C (SOFIA_FORCAST, 11 stars / 35 FITS)...", flush=True)
    for canon_id, irsa_t, is_br in FORCAST_TARGETS:
        m = star_meta(canon_id, is_br)
        seen: dict[str, dict[str, str]] = {}
        for r in sorted(forc_by_t[irsa_t], key=lambda x: int(x.get("contentlength") or 0), reverse=True):
            bn = r["uri"].split("/")[-1]
            for g in ("FORG063", "FORG111", "FORG227", "FORG329"):
                if g in bn and g not in seen:
                    seen[g] = r
        for erank, (g, r) in enumerate(sorted(seen.items()), 1):
            furl = r["uri"].strip()
            fb = _head_bytes(furl)
            fname = furl.split("/")[-1]
            rp = _opt_float(r.get("energy_resolvingpower"), 200.0)
            mjd = _opt_float(r.get("time_bounds_lower"), 58000.0)
            expt = _opt_float(r.get("time_exposure"), 300.0)
            dp_id = f"FORCAST.{fname[:-5]}"
            add_row("SOFIA_FORCAST", "MIDIR_GRISM_V56", canon_id, is_br, m, erank, dp_id, g, rp, mjd, expt, "NONE", 0.0, 0.0, fname[:-5], f"SOFIA_FORCAST/{canon_id}/{fname}", furl, fb)

    # Stream 2: CARMENES VIS (5 stars, 20 FITS + Orbital #141-#143 + DRIFT_V56)
    print("6. Selecting & HEAD-checking Stream 2 (CARMENES_VIS, 5 stars / 20 FITS)...", flush=True)
    for canon_id, cid in CARMENES_TARGETS:
        m = star_meta(canon_id, False)
        picks = _evenly_spaced_4(carm_by_cid[cid])
        exps_orb = []
        has_orb = "campaign_index" in m
        kp = det.compute_keplerian_kp_kms(m["mass_msun"], m["orb_per_days"], ecc=m["orb_ecc"]) if has_orb else 0.0
        for erank, r in enumerate(picks, 1):
            ac = r["accref"].strip()
            furl = ac.replace("http://dc.g-vo.org/getproduct/carmenes/data/", "https://dc.g-vo.org/carmenes/q/sdl/static/")
            fb = _head_bytes(furl)
            fname = furl.split("/")[-1]
            mjd = float(r.get("ssa_dateObs") or r.get("ssa_dateobs"))
            expt = _opt_float(r.get("ssa_timeext"), 900.0)
            dp_id = f"CARMENES.{fname[:-5]}"
            if has_orb:
                s_ph, o_rv = det.compute_planet_orbital_rv_kms(mjd + 2400000.5, m["orb_t0_bjd"], m["orb_per_days"], kp)
                ph_w = "IN_WINDOW" if abs(o_rv) > 0.4 * kp else "OUT_OF_WINDOW"
                exps_orb.append({
                    "dp_id": dp_id,
                    "mjd_obs": round(mjd, 6),
                    "bjd_tdb_est": round(mjd + 2400000.5, 6),
                    "signed_phase": round(s_ph, 6),
                    "phase_window": ph_w,
                    "planet_orbital_rv_kms": round(o_rv, 4),
                    "ppo_align_score": 1.0,
                })
            else:
                s_ph, o_rv, ph_w = 0.0, 0.0, "NULL_CONTROL" if m["role"] == "CONTROL" else "NONE"
            add_row("CARMENES_VIS", "OPTICAL_JERK_V56", canon_id, False, m, erank, dp_id, "CARMENES_VIS", 94600.0, mjd, expt, ph_w, s_ph, o_rv, fname[:-5], f"CARMENES_VIS/{canon_id}/{fname}", furl, fb)
        if has_orb:
            dvs = [e["planet_orbital_rv_kms"] for e in exps_orb]
            orbital_campaigns[canon_id] = {
                "campaign_index": int(m["campaign_index"]),
                "canonical_target": canon_id,
                "common_name": m["common_name"],
                "instrument": "CARMENES_VIS",
                "role": m["role"],
                "null_orbital": False,
                "planet_name": m["planet_name"],
                "n_planets_in_system": int(m["n_pl"]),
                "stellar_mass_msun": round(float(m["mass_msun"]), 3),
                "orb_per_days": float(m["orb_per_days"]),
                "orb_t0_bjd": float(m["orb_t0_bjd"]),
                "orb_ecc": float(m["orb_ecc"]),
                "kp_kms": round(kp, 3),
                "orbital_dv_span_kms": round(max(dvs) - min(dvs), 3),
                "n_epochs": len(exps_orb),
                "exposures": exps_orb,
            }

    print("7. Enforcing 5-arcmin prior exclusion, intra-D098 spacing, dp_id disjointness, and caps...", flush=True)
    star_seps: list[dict[str, Any]] = []
    min_brand_new_sep = 1e18
    for st, (_inst, ra, dec) in sorted(unique_new_coords.items()):
        best_sep = 1e18
        for p in prior_coords:
            sp = _sep_arcsec(ra, dec, float(p["ra_deg"]), float(p["dec_deg"]))
            if sp < best_sep:
                best_sep = sp
        if best_sep < 300.0:
            raise RuntimeError(f"5-arcmin exclusion FAILED for {st}: {best_sep:.2f}\" < 300\"")
        min_brand_new_sep = min(min_brand_new_sep, best_sep)
        star_seps.append({"canonical_target": st, "ra_deg": round(ra, 6), "dec_deg": round(dec, 6), "min_sep_arcsec": round(best_sep, 2), "nearest_prior": ""})

    intra_seps = [_sep_arcsec(a[1], a[2], b[1], b[2]) for (_, a), (_, b) in itertools.combinations(sorted(unique_new_coords.items()), 2)]
    min_intra_sep = min(intra_seps) if intra_seps else 999999.0
    if min_intra_sep < 300.0:
        raise RuntimeError(f"Intra-D098 separation violation: {min_intra_sep:.2f}\" < 300\"")

    tot_bytes = sum(r["f1_bytes"] for r in cohort_rows)
    tot_mib = tot_bytes / 1048576.0
    if tot_mib > 125.0:
        raise RuntimeError(f"Projected download {tot_mib:.3f} MiB > 125.0 MiB!")

    all_stars_d098 = sorted({r["canonical_target"] for r in cohort_rows})
    prior_bridges_d098 = sorted({r["canonical_target"] for r in cohort_rows if r["is_prior_bridge"]})
    new_10pc = sum(1 for st in unique_new_coords if next(r["within_10pc"] for r in cohort_rows if r["canonical_target"] == st))
    new_ctrl = sum(1 for st in unique_new_coords if next(r["role"] == "CONTROL" for r in cohort_rows if r["canonical_target"] == st))
    all_ctrl = sum(1 for st in all_stars_d098 if next(r["role"] == "CONTROL" for r in cohort_rows if r["canonical_target"] == st))

    assert len(all_stars_d098) == 38, f"Expected 38 stars, got {len(all_stars_d098)}"
    assert len(unique_new_coords) == 25, f"Expected 25 new stars, got {len(unique_new_coords)}"
    assert len(prior_bridges_d098) == 13, f"Expected 13 bridges, got {len(prior_bridges_d098)}"
    assert len(cohort_rows) == 99, f"Expected 99 files, got {len(cohort_rows)}"
    assert len(orbital_campaigns) == 3, f"Expected 3 orbital campaigns (#141-#143), got {len(orbital_campaigns)}"

    (WS / "PRIOR_V5_5_PHASES_SNAPSHOT.json").write_text(json.dumps(prior_snap, indent=2) + "\n")

    prior_excl = {
        "schema": "D098_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D098",
        "verified_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prior_phases_covered": "C001-C037 + D001-D097",
        "n_prior_excluded_coords": len(prior_coords),
        "n_prior_excluded_dp_ids": len(prior_dp_ids),
        "n_format_check_excluded_dp_ids": len(prior_fmt_excl),
        "d098_total_stars": len(all_stars_d098),
        "d098_brand_new_unique_stars": len(unique_new_coords),
        "d098_prior_bridge_stars": len(prior_bridges_d098),
        "d098_control_stars": all_ctrl,
        "d098_brand_new_controls": new_ctrl,
        "d098_brand_new_within_10pc": new_10pc,
        "d098_total_input_files": len(cohort_rows),
        "d098_projected_download_bytes": tot_bytes,
        "d098_projected_download_mib": round(tot_mib, 3),
        "d098_dp_id_overlap_count": 0,
        "min_brand_new_sky_separation_arcsec": round(min_brand_new_sep, 2),
        "min_intra_d098_separation_arcsec": round(min_intra_sep, 2),
        "star_separation_verification": star_seps,
        "format_check_excluded_dp_ids": prior_fmt_excl,
        "excluded_dp_ids": sorted(prior_dp_ids),
        "excluded_targets_coordinate_registry": prior_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(prior_excl, indent=2) + "\n")

    with (WS / "FROZEN_COHORT_D098.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cohort_rows[0].keys()))
        w.writeheader()
        w.writerows(cohort_rows)

    orb_doc = {
        "schema": "D098_ORBITAL_CAMPAIGNS_AND_KINEMATICS",
        "phase_id": "D098",
        "campaign_range": "#141-#143",
        "n_campaigns": len(orbital_campaigns),
        "campaigns": orbital_campaigns,
    }
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_doc, indent=2) + "\n")

    locked_names = [
        "v5_6_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D098.csv",
        "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "PRIOR_V5_5_PHASES_SNAPSHOT.json",
    ]
    hashes = {fn: _sha256_file(WS / fn) for fn in locked_names}
    now_t = time.time()
    locked_utc = dt.datetime.fromtimestamp(now_t, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    locked_iso = dt.datetime.fromtimestamp(now_t, tz=dt.timezone.utc).isoformat()

    method_lock = {
        "schema": "D098_STAGE1_PROSPECTIVE_METHOD_LOCK",
        "phase_id": "D098",
        "detector_name": det.DETECTOR_NAME,
        "locked_utc": locked_utc,
        "retroactive_reused_bundles": [
            {"phase_id": "D097", "archive_name": ARCHIVE_W_NAME, "archive_sha256": ARCHIVE_W_SHA256, "bundle_member": W_PREFIX + "bounded_inputs/d097_bounded_bundle.json.gz", "bundle_sha256": w_bundle_sha},
            {"phase_id": "D096", "archive_name": ARCHIVE_V_NAME, "archive_sha256": ARCHIVE_V_SHA256, "bundle_member": V_BUNDLE_MEMBER, "bundle_sha256": v_bundle_sha},
            {"phase_id": "D095", "archive_name": ARCHIVE_U_NAME, "archive_sha256": ARCHIVE_U_SHA256, "bundle_member": U_BUNDLE_MEMBER, "bundle_sha256": u_bundle_sha},
            {"phase_id": "D094", "archive_name": ARCHIVE_T_NAME, "archive_sha256": ARCHIVE_T_SHA256, "bundle_member": T_BUNDLE_MEMBER, "bundle_sha256": t_bundle_sha},
        ],
        "locked_v56_parameters": det.BASE_V5_5_CONFIG,
        "hard_caps": {
            "max_download_mib": 125.0,
            "max_bounded_bundle_mib": 22.0,
            "max_companion_archive_mib": 25.0,
            "min_free_disk_gib": 1.5,
            "min_chronology_lag_seconds": 3.0,
            "min_brand_new_separation_arcsec": 300.0,
        },
        "locked_file_hashes": hashes,
    }
    (WS / "METHOD_LOCK.json").write_text(json.dumps(method_lock, indent=2) + "\n")

    lock_receipt = {
        "schema": "D098_STAGE1_LOCK_RECEIPT",
        "phase_id": "D098",
        "locked_utc": locked_utc,
        "locked_at_utc": locked_iso,
        "locked_at_unix": round(now_t, 3),
        "inputs_d098_v5_6_exists": False,
        "method_lock_sha256": _sha256_file(WS / "METHOD_LOCK.json"),
        "frozen_cohort_sha256": hashes["FROZEN_COHORT_D098.csv"],
        "projected_download_mib": round(tot_mib, 3),
        "n_input_files": len(cohort_rows),
        "n_total_stars": len(all_stars_d098),
        "n_unique_new_stars": len(unique_new_coords),
        "n_prior_bridge_stars": len(prior_bridges_d098),
        "n_orbital_campaigns": len(orbital_campaigns),
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lock_receipt, indent=2) + "\n")
    print(f"STAGE-1 SEALED: {len(all_stars_d098)} stars ({len(unique_new_coords)} new, {len(prior_bridges_d098)} bridges, {new_10pc} new <10pc), {len(cohort_rows)} files ({tot_mib:.3f} MiB), min_sep={min_brand_new_sep:.2f}\", {len(orbital_campaigns)} orbital campaigns (#141-#143).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
