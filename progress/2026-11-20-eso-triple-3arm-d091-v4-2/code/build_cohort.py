#!/usr/bin/env python3
"""
Phase D091 Cohort Builder: `ESO_TRIPLE_SPECTROGRAPH_3ARM_V4_2`

Strictly queries public ESO Phase-3 TAP (`ivoa.ObsCore`), ESA Gaia DR3 TAP,
NASA Exoplanet Archive (`pscomppars`), and verified Companion Archive P
(Phase D090) BEFORE `inputs_d091_v4_2/` exists or any science FITS file is
downloaded.

Outputs:
  - FROZEN_COHORT_D091.csv (37 stars: 9 CONTROL + 28 SCIENCE; 30 brand-new + 7 bridges)
  - ORBITAL_CAMPAIGNS_AND_KINEMATICS.json (10 campaigns #91-#100)
  - PRIOR_EXCLUSION_VERIFICATION.json (0 overlaps vs C001-D090 + D091 format checks)
  - PRIOR_V4_1_PHASES_SNAPSHOT.json (D079-D090 280-star baseline from Archive P)
  - MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json (23/23 GBT/Parkes radio + 1 TESS closure)
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

from v4_2_detector import compute_keplerian_kp_kms, compute_planet_orbital_rv_kms

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = Path(__file__).resolve().parent
ARCHIVE_P = ROOT / "archives" / "SETI_D090_V4_1_JWST_SPACE_THERMAL_IR_RESULTS_2026-11-19.zip"
ARCHIVE_P_SHA256 = "2940839e8613b0d388c9b922743ba8244852806411f28586696e59eb8d73841a"
ARCHIVE_P_PREFIX = "work_jwst_thermal_ir_20261119_d090_v4_1_nirspec_miri/"

FORMAT_CHECK_EXCLUDED = [
    ("4Vesta(D091_FMT_IRSA_EXES_TEXES)", 329.655532, -22.447282),
    ("HD-34282(D091_FMT_ESO_XSHOOTER)", 75.507800, -9.473900),
    ("HD123097(D091_FMT_ESO_GIRAFFE)", 211.500000, -25.000000),
]

TARGET_SPECS: list[dict[str, Any]] = [
    # ==================== ESO_XSHOOTER_3ARM (10 stars: 3 CTRL + 5 <10pc BRIDGES + 2 NEW SCI) ====================
    {
        "instrument": "ESO_XSHOOTER_3ARM", "eso_target": "HD 1064", "canonical_target": "HD1064", "common_name": "HD 1064",
        "role": "CONTROL", "subrole": "NULL_FLUX_STANDARD_XSHOOTER", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 2428341184508675456, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 11489.0, "mh_lit": 0.0, "mass_lit": 2.6, "rv_lit": 12.0, "j_mag": 5.83, "h_mag": 5.86, "ks_mag": 5.88,
    },
    {
        "instrument": "ESO_XSHOOTER_3ARM", "eso_target": "HD 104600", "canonical_target": "HD104600", "common_name": "HD 104600",
        "role": "CONTROL", "subrole": "NULL_FLUX_STANDARD_XSHOOTER", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 5859187277060333184, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 11587.0, "mh_lit": 0.0, "mass_lit": 2.6, "rv_lit": 10.0, "j_mag": 5.95, "h_mag": 5.98, "ks_mag": 5.98,
    },
    {
        "instrument": "ESO_XSHOOTER_3ARM", "eso_target": "HD 11210", "canonical_target": "HD11210", "common_name": "HD 11210",
        "role": "CONTROL", "subrole": "NULL_TELLURIC_STANDARD_XSHOOTER", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 4940542558952219392, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 10772.0, "mh_lit": 0.0, "mass_lit": 2.4, "rv_lit": 31.11, "j_mag": 7.62, "h_mag": 7.64, "ks_mag": 7.65,
    },
    {
        "instrument": "ESO_XSHOOTER_3ARM", "eso_target": "Gl-908", "canonical_target": "GJ908", "common_name": "GJ 908 (BR Psc)",
        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_XSHOOTER_10PC", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 2739689239311660672, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 3619.1, "mh_lit": -0.35, "mass_lit": 0.42, "rv_lit": -71.37, "j_mag": 5.83, "h_mag": 5.28, "ks_mag": 5.04,
    },
    {
        "instrument": "ESO_XSHOOTER_3ARM", "eso_target": "K2-22b", "canonical_target": "K222", "common_name": "K2-22 (EPIC 201637175)",
        "role": "SCIENCE", "subrole": "USP_DISINTEGRATING_TRANSIT_ORBITAL_XSHOOTER", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3811002791880297600, "n_target_exposures": 6, "orbital_campaign": True, "null_orbital": False,
        "nasa_pl_name": "K2-22 b", "orb_per_days": 0.381073, "orb_t0_bjd": 2456811.1208, "orb_e": 0.0,
        "teff_lit": 3830.0, "mh_lit": -0.05, "mass_lit": 0.60, "rv_lit": 18.0, "j_mag": 12.74, "h_mag": 12.09, "ks_mag": 11.91,
    },
    {
        "instrument": "ESO_XSHOOTER_3ARM", "eso_target": "LTT 4364", "canonical_target": "LAWD37", "common_name": "LAWD 37 (LTT 4364)",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_JWST_MIRI_XSHOOTER_WD_10PC_BRIDGE", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 5332606522595645952, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 7850.0, "mh_lit": -0.50, "mass_lit": 0.56, "rv_lit": 30.0, "j_mag": 11.15, "h_mag": 11.09, "ks_mag": 11.05,
    },
    {
        "instrument": "ESO_XSHOOTER_3ARM", "eso_target": "Gl-849", "canonical_target": "GJ849", "common_name": "GJ 849 (BD-05 5715)",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_RADIO_NIRPS_XSHOOTER_10PC_BRIDGE", "panchromatic_bridge": True, "radio_mm_id": "M17_GJ849",
        "gaia_source_id": 2627117287488522240, "n_target_exposures": 3, "orbital_campaign": False,
        "nasa_pl_name": "GJ 849 b", "n_exoplanets_lit": 2,
        "teff_lit": 3229.7, "mh_lit": 0.35, "mass_lit": 0.49, "rv_lit": -15.61, "j_mag": 6.51, "h_mag": 5.90, "ks_mag": 5.59,
    },
    {
        "instrument": "ESO_XSHOOTER_3ARM", "eso_target": "Gl-674", "canonical_target": "GJ674", "common_name": "GJ 674 (CD-46 11540)",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_HARPS_XSHOOTER_10PC_BRIDGE", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 5951824121022278144, "n_target_exposures": 3, "orbital_campaign": False,
        "nasa_pl_name": "GJ 674 b", "n_exoplanets_lit": 1,
        "teff_lit": 3274.9, "mh_lit": -0.25, "mass_lit": 0.35, "rv_lit": -3.37, "j_mag": 5.71, "h_mag": 5.15, "ks_mag": 4.86,
    },
    {
        "instrument": "ESO_XSHOOTER_3ARM", "eso_target": "Gl-832", "canonical_target": "GJ832", "common_name": "GJ 832 (HD 204961)",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_COS_HARPS_XSHOOTER_10PC_BRIDGE", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 6562924609150908416, "n_target_exposures": 3, "orbital_campaign": False,
        "nasa_pl_name": "GJ 832 b", "n_exoplanets_lit": 1,
        "teff_lit": 3310.1, "mh_lit": -0.20, "mass_lit": 0.45, "rv_lit": 12.72, "j_mag": 5.35, "h_mag": 4.77, "ks_mag": 4.50,
    },
    {
        "instrument": "ESO_XSHOOTER_3ARM", "eso_target": "e Eri", "canonical_target": "HD20794", "common_name": "82 G. Eri (HD 20794)",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_ESPRESSO_XSHOOTER_10PC_BRIDGE", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 4847957293278177024, "n_target_exposures": 3, "orbital_campaign": False,
        "nasa_pl_name": "HD 20794 b", "n_exoplanets_lit": 4,
        "teff_lit": 5427.3, "mh_lit": -0.40, "mass_lit": 0.70, "rv_lit": 87.76, "j_mag": 3.03, "h_mag": 2.66, "ks_mag": 2.55,
    },

    # ==================== ESO_FEROS (10 stars: 3 CTRL <10pc + 7 SCI [6 <10pc + HD213885]) ====================
    {
        "instrument": "ESO_FEROS", "eso_target": "HIP-103039", "canonical_target": "HIP103039", "common_name": "LHS 3589 (HIP 103039)",
        "role": "CONTROL", "subrole": "NULL_SOLAR_NEIGHBORHOOD_FEROS_10PC", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 6882963066420161664, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 3100.0, "mh_lit": 0.0, "mass_lit": 0.23, "rv_lit": 0.0, "j_mag": 7.06, "h_mag": 6.51, "ks_mag": 6.20,
    },
    {
        "instrument": "ESO_FEROS", "eso_target": "GJ-1128", "canonical_target": "GJ1128", "common_name": "GJ 1128 (LHS 271)",
        "role": "CONTROL", "subrole": "NULL_SOLAR_NEIGHBORHOOD_FEROS_10PC", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 5243594081269535872, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 3040.3, "mh_lit": -0.10, "mass_lit": 0.18, "rv_lit": 30.43, "j_mag": 7.95, "h_mag": 7.39, "ks_mag": 7.04,
    },
    {
        "instrument": "ESO_FEROS", "eso_target": "GL402", "canonical_target": "GJ402", "common_name": "GJ 402 (EE Leo)",
        "role": "CONTROL", "subrole": "NULL_SOLAR_NEIGHBORHOOD_FEROS_10PC", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3864615459886222464, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 3000.7, "mh_lit": 0.05, "mass_lit": 0.25, "rv_lit": -1.24, "j_mag": 7.32, "h_mag": 6.71, "ks_mag": 6.37,
    },
    {
        "instrument": "ESO_FEROS", "eso_target": "SCR1845", "canonical_target": "SCR1845", "common_name": "SCR J1845-6357 (4.01 pc)",
        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_FEROS_4PC_BD_HOST", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 6439125097427143808, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 2600.0, "mh_lit": 0.0, "mass_lit": 0.07, "rv_lit": -56.0, "j_mag": 9.54, "h_mag": 8.97, "ks_mag": 8.51,
    },
    {
        "instrument": "ESO_FEROS", "eso_target": "LP-944-20", "canonical_target": "LP94420", "common_name": "LP 944-20 (6.43 pc)",
        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_FEROS_BROWN_DWARF_10PC", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 4860376345833699840, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 2250.0, "mh_lit": 0.0, "mass_lit": 0.06, "rv_lit": 9.0, "j_mag": 10.73, "h_mag": 10.02, "ks_mag": 9.55,
    },
    {
        "instrument": "ESO_FEROS", "eso_target": "hd_216803", "canonical_target": "HD216803", "common_name": "TW PsA (HD 216803)",
        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_FEROS_FOMALHAUT_B_10PC", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 6604147121141267712, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 4463.1, "mh_lit": 0.05, "mass_lit": 0.72, "rv_lit": 6.79, "j_mag": 4.49, "h_mag": 3.92, "ks_mag": 3.80,
    },
    {
        "instrument": "ESO_FEROS", "eso_target": "zet Tuc", "canonical_target": "ZETTUC", "common_name": "zeta Tuc (HD 1581)",
        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_FEROS_G0V_DEBRIS_10PC", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 4900108950849461248, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 5857.8, "mh_lit": -0.20, "mass_lit": 0.99, "rv_lit": 9.28, "j_mag": 3.09, "h_mag": 2.79, "ks_mag": 2.74,
    },
    {
        "instrument": "ESO_FEROS", "eso_target": "del Eri", "canonical_target": "DELERI", "common_name": "delta Eri (HD 23249)",
        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_FEROS_SUBGIANT_10PC", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 5164120762333028736, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 5050.0, "mh_lit": 0.10, "mass_lit": 1.20, "rv_lit": -6.30, "j_mag": 2.13, "h_mag": 1.66, "ks_mag": 1.56,
    },
    {
        "instrument": "ESO_FEROS", "eso_target": "GJ433", "canonical_target": "GJ433", "common_name": "GJ 433 (CD-31 9113)",
        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_FEROS_ORBITAL_3PLANET_10PC", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3478160727866058368, "n_target_exposures": 6, "orbital_campaign": True, "null_orbital": False,
        "nasa_pl_name": "GJ 433 b", "orb_per_days": 7.3709, "orb_t0_bjd": 2454289.2, "orb_e": 0.04,
        "teff_lit": 3580.5, "mh_lit": -0.15, "mass_lit": 0.48, "rv_lit": 17.69, "j_mag": 6.47, "h_mag": 5.86, "ks_mag": 5.62,
    },
    {
        "instrument": "ESO_FEROS", "eso_target": "HD213885", "canonical_target": "HD213885", "common_name": "HD 213885 (TOI-141)",
        "role": "SCIENCE", "subrole": "TRANSITING_USP_ORBITAL_FEROS", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 6407428994690988928, "n_target_exposures": 6, "orbital_campaign": True, "null_orbital": False,
        "nasa_pl_name": "HD 213885 b", "orb_per_days": 1.008035, "orb_t0_bjd": 2458379.9704, "orb_e": 0.0,
        "teff_lit": 5747.6, "mh_lit": 0.0, "mass_lit": 1.07, "rv_lit": 36.04, "j_mag": 6.81, "h_mag": 6.50, "ks_mag": 6.42,
    },

    # ==================== ESO_GIRAFFE_HR (17 stars: 3 CTRL + 2 BRIDGES + 5 NEW PLANETS + 7 FIELD HR09B) ====================
    {
        "instrument": "ESO_GIRAFFE_HR", "eso_target": "HD220009", "canonical_target": "HD220009", "common_name": "7 Psc (HD 220009)",
        "role": "CONTROL", "subrole": "NULL_ORBITAL_CONTROL_GIRAFFE_HR", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 2661005953843811456, "n_target_exposures": 8, "orbital_campaign": True, "null_orbital": True,
        "planet_name": "Null Control (synthetic P=1.1842d)", "orb_per_days": 1.1842, "orb_e": 0.0,
        "teff_lit": 4635.7, "mh_lit": -0.35, "mass_lit": 1.25, "rv_lit": 40.50, "j_mag": 3.01, "h_mag": 2.40, "ks_mag": 2.27,
    },
    {
        "instrument": "ESO_GIRAFFE_HR", "eso_target": "HD107328", "canonical_target": "HD107328", "common_name": "16 Vir (HD 107328)",
        "role": "CONTROL", "subrole": "NULL_ORBITAL_CONTROL_GIRAFFE_HR", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3701693091058501504, "n_target_exposures": 6, "orbital_campaign": True, "null_orbital": True,
        "planet_name": "Null Control (synthetic P=1.4215d)", "orb_per_days": 1.4215, "orb_e": 0.0,
        "teff_lit": 4450.0, "mh_lit": -0.34, "mass_lit": 1.40, "rv_lit": 36.63, "j_mag": 2.96, "h_mag": 2.34, "ks_mag": 2.18,
    },
    {
        "instrument": "ESO_GIRAFFE_HR", "eso_target": "29751", "canonical_target": "G29751", "common_name": "GIRAFFE HR09B 29751",
        "role": "CONTROL", "subrole": "NULL_ORBITAL_CONTROL_GIRAFFE_HR", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 4258498011459868416, "n_target_exposures": 8, "orbital_campaign": True, "null_orbital": True,
        "planet_name": "Null Control (synthetic P=2.3170d)", "orb_per_days": 2.3170, "orb_e": 0.0,
        "teff_lit": 4800.0, "mh_lit": -0.20, "mass_lit": 1.00, "rv_lit": 0.0, "j_mag": 10.10, "h_mag": 9.70, "ks_mag": 9.55,
    },
    {
        "instrument": "ESO_GIRAFFE_HR", "eso_target": "GJ436", "canonical_target": "GJ436", "common_name": "GJ 436 (Ross 905)",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_TRANSITING_ORBITAL_10PC_BRIDGE", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 4017860992519744384, "n_target_exposures": 8, "orbital_campaign": True, "null_orbital": False,
        "nasa_pl_name": "GJ 436 b", "orb_per_days": 2.643883, "orb_t0_bjd": 2454222.616, "orb_e": 0.138,
        "teff_lit": 3228.1, "mh_lit": -0.03, "mass_lit": 0.445, "rv_lit": 8.87, "j_mag": 6.90, "h_mag": 6.32, "ks_mag": 6.07,
    },
    {
        "instrument": "ESO_GIRAFFE_HR", "eso_target": "tauCet", "canonical_target": "TAUCET", "common_name": "tau Cet (HD 10700)",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_NIRPS_HARPS_GIRAFFE_10PC_BRIDGE", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 2452378776434477184, "n_target_exposures": 6, "orbital_campaign": False,
        "nasa_pl_name": "tau Cet e", "n_exoplanets_lit": 4,
        "teff_lit": 5344.0, "mh_lit": -0.52, "mass_lit": 0.783, "rv_lit": -16.60, "j_mag": 2.15, "h_mag": 1.80, "ks_mag": 1.79,
    },
    {
        "instrument": "ESO_GIRAFFE_HR", "eso_target": "muAra", "canonical_target": "MUARA", "common_name": "mu Ara (HD 160691)",
        "role": "SCIENCE", "subrole": "MULTIPLANET_HOST_GIRAFFE_HR09B", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 5945941905576552064, "n_target_exposures": 6, "orbital_campaign": False,
        "nasa_pl_name": "HD 160691 b", "n_exoplanets_lit": 4,
        "teff_lit": 5590.9, "mh_lit": 0.28, "mass_lit": 1.08, "rv_lit": -9.54, "j_mag": 4.16, "h_mag": 3.72, "ks_mag": 3.68,
    },
    {
        "instrument": "ESO_GIRAFFE_HR", "eso_target": "CoRoT_102708694", "canonical_target": "COROT7", "common_name": "CoRoT-7 (TYC 4799-1733-1)",
        "role": "SCIENCE", "subrole": "TRANSITING_LAVA_WORLD_HOST_GIRAFFE_HR21", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3107267177757848576, "n_target_exposures": 4, "orbital_campaign": False,
        "nasa_pl_name": "CoRoT-7 b", "n_exoplanets_lit": 3,
        "teff_lit": 5351.1, "mh_lit": 0.03, "mass_lit": 0.91, "rv_lit": 31.05, "j_mag": 10.30, "h_mag": 9.88, "ks_mag": 9.81,
    },
    {
        "instrument": "ESO_GIRAFFE_HR", "eso_target": "OGLE-TR-113", "canonical_target": "OGLETR113", "common_name": "OGLE-TR-113",
        "role": "SCIENCE", "subrole": "TRANSITING_HOT_JUPITER_ORBITAL_GIRAFFE_HR11", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 5242077889097539072, "dist_lit": 566.46, "n_target_exposures": 6, "orbital_campaign": True, "null_orbital": False,
        "nasa_pl_name": "OGLE-TR-113 b", "orb_per_days": 1.432475, "orb_t0_bjd": 2453464.6166, "orb_e": 0.0,
        "teff_lit": 4800.0, "mh_lit": 0.14, "mass_lit": 0.78, "rv_lit": -10.0, "j_mag": 12.80, "h_mag": 12.30, "ks_mag": 12.15,
    },
    {
        "instrument": "ESO_GIRAFFE_HR", "eso_target": "OGLE-TR-111", "canonical_target": "OGLETR111", "common_name": "OGLE-TR-111",
        "role": "SCIENCE", "subrole": "TRANSITING_HOT_JUPITER_ORBITAL_GIRAFFE_HR11", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 5242089223507797632, "dist_lit": 1068.33, "n_target_exposures": 6, "orbital_campaign": True, "null_orbital": False,
        "nasa_pl_name": "OGLE-TR-111 b", "orb_per_days": 4.014446, "orb_t0_bjd": 2452330.461, "orb_e": 0.0,
        "teff_lit": 5044.0, "mh_lit": 0.19, "mass_lit": 0.82, "rv_lit": 40.99, "j_mag": 13.80, "h_mag": 13.30, "ks_mag": 13.15,
    },
    {
        "instrument": "ESO_GIRAFFE_HR", "eso_target": "RHB.24771", "canonical_target": "KEPLER156", "common_name": "Kepler-156 (KOI-442)",
        "role": "SCIENCE", "subrole": "TRANSITING_MULTIPLANET_ORBITAL_GIRAFFE_HR13", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 2051105410816218368, "n_target_exposures": 8, "orbital_campaign": True, "null_orbital": False,
        "nasa_pl_name": "Kepler-156 b", "orb_per_days": 15.90680, "orb_t0_bjd": 2454972.34, "orb_e": 0.0,
        "teff_lit": 4972.9, "mh_lit": -0.20, "mass_lit": 0.85, "rv_lit": -26.08, "j_mag": 12.80, "h_mag": 12.30, "ks_mag": 12.18,
    },
    {
        "instrument": "ESO_GIRAFFE_HR", "eso_target": "105894039", "canonical_target": "G105894039", "common_name": "CoRoT 105894039",
        "role": "SCIENCE", "subrole": "GALACTIC_FIELD_HR09B_GIRAFFE", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3834884592457084416, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 5593.0, "mh_lit": 0.0, "mass_lit": 1.00, "rv_lit": -18.65, "j_mag": 10.40, "h_mag": 10.10, "ks_mag": 10.02,
    },
    {
        "instrument": "ESO_GIRAFFE_HR", "eso_target": "06572127+0315053", "canonical_target": "G06572127", "common_name": "2MASS J06572127+0315053",
        "role": "SCIENCE", "subrole": "GALACTIC_FIELD_HR09B_GIRAFFE", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3127866699899747072, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 6196.3, "mh_lit": 0.0, "mass_lit": 1.15, "rv_lit": -3.16, "j_mag": 13.00, "h_mag": 12.70, "ks_mag": 12.60,
    },
    {
        "instrument": "ESO_GIRAFFE_HR", "eso_target": "1065", "canonical_target": "G1065", "common_name": "GIRAFFE HR09B 1065",
        "role": "SCIENCE", "subrole": "GALACTIC_FIELD_HR09B_GIRAFFE", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 4666336801505677440, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 4750.0, "mh_lit": -0.30, "mass_lit": 1.10, "rv_lit": 4.91, "j_mag": 12.50, "h_mag": 12.00, "ks_mag": 11.85,
    },
    {
        "instrument": "ESO_GIRAFFE_HR", "eso_target": "115", "canonical_target": "G115", "common_name": "GIRAFFE HR09B 115",
        "role": "SCIENCE", "subrole": "GALACTIC_FIELD_HR09B_GIRAFFE", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 2928871691035378048, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 6150.2, "mh_lit": 0.0, "mass_lit": 1.15, "rv_lit": 33.50, "j_mag": 12.60, "h_mag": 12.30, "ks_mag": 12.20,
    },
    {
        "instrument": "ESO_GIRAFFE_HR", "eso_target": "1541", "canonical_target": "G1541", "common_name": "GIRAFFE HR09B 1541",
        "role": "SCIENCE", "subrole": "GALACTIC_FIELD_HR09B_GIRAFFE", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 6017554467972046208, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 4650.0, "mh_lit": -0.10, "mass_lit": 1.10, "rv_lit": 4.60, "j_mag": 11.60, "h_mag": 11.10, "ks_mag": 10.95,
    },
    {
        "instrument": "ESO_GIRAFFE_HR", "eso_target": "2421", "canonical_target": "G2421", "common_name": "GIRAFFE HR09B 2421",
        "role": "SCIENCE", "subrole": "GALACTIC_FIELD_HR09B_GIRAFFE", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3464520633287612928, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 5128.4, "mh_lit": -0.20, "mass_lit": 0.90, "rv_lit": 0.0, "j_mag": 13.70, "h_mag": 13.30, "ks_mag": 13.20,
    },
    {
        "instrument": "ESO_GIRAFFE_HR", "eso_target": "2m06410702-16281867", "canonical_target": "G06410702", "common_name": "2MASS J06410702-1628186",
        "role": "SCIENCE", "subrole": "GALACTIC_FIELD_HR09B_GIRAFFE", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 2946941339994237824, "n_target_exposures": 3, "orbital_campaign": False,
        "teff_lit": 5911.8, "mh_lit": -0.10, "mass_lit": 1.05, "rv_lit": 20.0, "j_mag": 13.90, "h_mag": 13.60, "ks_mag": 13.50,
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


def tap_json(base_url: str, adql: str, timeout_s: float = 45.0) -> dict[str, Any]:
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "json", "QUERY": adql}).encode()
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(base_url, data=data, headers={"User-Agent": "SETIsearch-D091-Build/1.0"})
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"TAP query failed ({base_url}): {last_err}")


def tap_csv(base_url: str, adql: str, timeout_s: float = 45.0) -> list[dict[str, str]]:
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": adql}).encode()
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(base_url, data=data, headers={"User-Agent": "SETIsearch-D091-Build/1.0"})
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                return list(csv.DictReader(resp.read().decode("utf-8").splitlines()))
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"TAP CSV query failed ({base_url}): {last_err}")


def sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    c = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c)))) * 3600.0


def fetch_eso_records_for_target(spec: dict[str, Any], excluded_dp_ids: set[str]) -> list[dict[str, Any]]:
    inst = spec["instrument"]
    tn = spec["eso_target"]
    eso_inst = {"ESO_XSHOOTER_3ARM": "XSHOOTER", "ESO_FEROS": "FEROS", "ESO_GIRAFFE_HR": "GIRAFFE"}[inst]
    extra = " AND em_res_power >= 18000 AND em_min >= 5.0e-7 AND em_max <= 9.0e-7" if inst == "ESO_GIRAFFE_HR" else ""
    q = (
        f"SELECT dp_id, target_name, s_ra, s_dec, t_min, t_exptime, em_min*1e9 AS lmin_nm, "
        f"em_max*1e9 AS lmax_nm, em_res_power, access_estsize "
        f"FROM ivoa.ObsCore WHERE instrument_name='{eso_inst}' AND dataproduct_type='spectrum' "
        f"AND target_name='{tn}'{extra} ORDER BY t_min"
    )
    rows = [r for r in tap_csv("https://archive.eso.org/tap_obs/sync", q) if r["dp_id"] not in excluded_dp_ids]

    if inst == "ESO_XSHOOTER_3ARM":
        uvbs = [r for r in rows if float(r["lmin_nm"]) < 400.0 and float(r["em_res_power"]) >= 5000.0]
        viss = [r for r in rows if 450.0 <= float(r["lmin_nm"]) <= 600.0 and float(r["em_res_power"]) >= 7000.0]
        nirs = [r for r in rows if float(r["lmin_nm"]) >= 950.0 and float(r["em_res_power"]) >= 5000.0]
        triplets: list[dict[str, Any]] = []
        used_v, used_n = set(), set()
        for u in uvbs:
            tu = float(u["t_min"])
            vm = [v for v in viss if v["dp_id"] not in used_v and abs(float(v["t_min"]) - tu) < 0.005]
            nm = [n for n in nirs if n["dp_id"] not in used_n and abs(float(n["t_min"]) - tu) < 0.005]
            if not vm or not nm:
                continue
            v = min(vm, key=lambda x: (-float(x["em_res_power"]), abs(float(x["t_min"]) - tu)))
            n = min(nm, key=lambda x: abs(float(x["t_min"]) - tu))
            used_v.add(v["dp_id"])
            used_n.add(n["dp_id"])
            kb1 = int(round(float(u["access_estsize"] or 725))) * 1024
            kb2 = int(round(float(v["access_estsize"] or 1330))) * 1024
            kb3 = int(round(float(n["access_estsize"] or 1360))) * 1024
            triplets.append({
                "dp_id": v["dp_id"],
                "mjd_obs": float(v["t_min"]),
                "t_exptime": float(v["t_exptime"] or u["t_exptime"] or 60.0),
                "s_ra": float(v["s_ra"]),
                "s_dec": float(v["s_dec"]),
                "resolving_power": float(v["em_res_power"]),
                "grating": "UVB+VIS+NIR",
                "f1_id": u["dp_id"], "f1_bytes": kb1, "f1_url": f"https://dataportal.eso.org/dataPortal/file/{u['dp_id']}",
                "f2_id": v["dp_id"], "f2_bytes": kb2, "f2_url": f"https://dataportal.eso.org/dataPortal/file/{v['dp_id']}",
                "f3_id": n["dp_id"], "f3_bytes": kb3, "f3_url": f"https://dataportal.eso.org/dataPortal/file/{n['dp_id']}",
                "total_bytes": kb1 + kb2 + kb3,
            })
        # Prefer R_vis >= 18000 triplets if at least n_target_exposures exist
        hi_r = [t for t in triplets if t["resolving_power"] >= 18000.0]
        if len(hi_r) >= int(spec["n_target_exposures"]):
            triplets = hi_r
        triplets.sort(key=lambda x: (x["mjd_obs"], x["dp_id"]))
        return triplets

    if inst == "ESO_GIRAFFE_HR":
        by_setting: dict[tuple[int, int], list[dict[str, str]]] = {}
        for r in rows:
            key = (int(round(float(r["lmin_nm"]))), int(round(float(r["lmax_nm"]))))
            by_setting.setdefault(key, []).append(r)
        best_grp = max(by_setting.values(), key=len) if by_setting else []
        out = []
        for r in best_grp:
            b = int(round(float(r["access_estsize"] or 220))) * 1024
            lo_n, hi_n = float(r["lmin_nm"]), float(r["lmax_nm"])
            grating = "HR21" if lo_n > 800 else ("HR13" if lo_n > 600 else ("HR11" if lo_n > 550 else ("HR10" if lo_n > 530 else "HR09B")))
            out.append({
                "dp_id": r["dp_id"],
                "mjd_obs": float(r["t_min"]),
                "t_exptime": float(r["t_exptime"] or 300.0),
                "s_ra": float(r["s_ra"]),
                "s_dec": float(r["s_dec"]),
                "resolving_power": float(r["em_res_power"]),
                "grating": f"{grating}_{lo_n:.1f}_{hi_n:.1f}nm",
                "f1_id": r["dp_id"], "f1_bytes": b, "f1_url": f"https://dataportal.eso.org/dataPortal/file/{r['dp_id']}",
                "f2_id": "", "f2_bytes": 0, "f2_url": "",
                "f3_id": "", "f3_bytes": 0, "f3_url": "",
                "total_bytes": b,
            })
        out.sort(key=lambda x: (x["mjd_obs"], x["dp_id"]))
        return out

    # ESO_FEROS
    out = []
    for r in rows:
        b = int(round(float(r["access_estsize"] or 3004))) * 1024
        out.append({
            "dp_id": r["dp_id"],
            "mjd_obs": float(r["t_min"]),
            "t_exptime": float(r["t_exptime"] or 300.0),
            "s_ra": float(r["s_ra"]),
            "s_dec": float(r["s_dec"]),
            "resolving_power": float(r["em_res_power"]),
            "grating": "FEROS_ECHELLE",
            "f1_id": r["dp_id"], "f1_bytes": b, "f1_url": f"https://dataportal.eso.org/dataPortal/file/{r['dp_id']}",
            "f2_id": "", "f2_bytes": 0, "f2_url": "",
            "f3_id": "", "f3_bytes": 0, "f3_url": "",
            "total_bytes": b,
        })
    out.sort(key=lambda x: (x["mjd_obs"], x["dp_id"]))
    return out


def select_target_exposures(spec: dict[str, Any], pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
    k = int(spec["n_target_exposures"])
    if len(pool) <= k:
        return list(pool)
    if spec.get("orbital_campaign"):
        by_night: dict[int, list[dict[str, Any]]] = {}
        for item in pool:
            by_night.setdefault(int(item["mjd_obs"]), []).append(item)
        nights = sorted(by_night.keys())
        if len(nights) >= 2:
            pick_n = nights if len(nights) <= k else [nights[int(round(i * (len(nights) - 1) / (k - 1)))] for i in range(k)]
            chosen: list[dict[str, Any]] = []
            used_dps: set[str] = set()
            for nt in pick_n:
                cand = by_night[nt][len(by_night[nt]) // 2]
                chosen.append(cand)
                used_dps.add(cand["dp_id"])
            if len(chosen) < k:
                rem = [p for p in pool if p["dp_id"] not in used_dps]
                need = k - len(chosen)
                for i in range(need):
                    j = int(round(i * (len(rem) - 1) / max(1, need - 1))) if need > 1 else len(rem) // 2
                    chosen.append(rem[j])
            chosen.sort(key=lambda x: (x["mjd_obs"], x["dp_id"]))
            return chosen[:k]
    idxs = [int(round(i * (len(pool) - 1) / (k - 1))) for i in range(k)]
    return [pool[i] for i in idxs]


def _load_newly_bridged_5star_prior_rows() -> list[dict[str, str]]:
    """Extract normalized 14-col prior upper limits for GJ674, HD20794, GJ849, GJ436, LAWD37."""
    sources = [
        ("SETI_D081_V3_2_TRANSIT_KINEMATICS_AND_10PC_RESULTS_2026-11-15.zip",
         "work_echelle_20261115_d081_v3_2_transit_kinematics_and_10pc_survey/results/STAR_UPPER_LIMITS_153.csv",
         {"GJ674", "HD20794"}, "D081", "OPTICAL", "wave_bary_air_A"),
        ("SETI_D082_V3_3_NIRPS_NEAR_IR_AND_PANCHROMATIC_RESULTS_2026-11-15.zip",
         "work_nirps_20261115_d082_v3_3_near_ir_and_panchromatic_survey/results/STAR_UPPER_LIMITS_162.csv",
         {"GJ849"}, "D082", "NIR_YJH", "wave_bary_air_A"),
        ("SETI_D085_V3_6_SPIROU_YJHK_AND_COMB_V4_RESULTS_2026-11-17.zip",
         "work_spirou_20261116_d085_v3_6_yjhk_and_comb_v4/results/STAR_UPPER_LIMITS_300.csv",
         {"GJ436"}, "D085", "NIR_YJHK", "wave_bary_vac_A"),
        ("SETI_D090_V4_1_JWST_SPACE_THERMAL_IR_RESULTS_2026-11-19.zip",
         "work_jwst_thermal_ir_20261119_d090_v4_1_nirspec_miri/results/STAR_UPPER_LIMITS_D090.csv",
         {"LAWD37"}, "D090", "THERMAL_IR_MIRI_4p90_28p0um", "wave_bary_a"),
    ]
    out: list[dict[str, str]] = []
    for zname, member, wanted_stars, ph, regime, wcol in sources:
        with zipfile.ZipFile(ROOT / "archives" / zname, "r") as zf:
            rows = list(csv.DictReader(zf.read(member).decode("utf-8").splitlines()))
        for r in rows:
            if r.get("star") not in wanted_stars:
                continue
            w_a = float(r[wcol])
            p_kw = float(r["p_beam_10m_kw"])
            p_w = float(r["p_beam_10m_w"]) if r.get("p_beam_10m_w") else (1000.0 * p_kw)
            out.append({
                "band_id": r["band_id"],
                "common_name": r["common_name"],
                "dist_pc": r["dist_pc"],
                "ew_lim_mA": r["ew_lim_mA"],
                "flux_lim_erg_cm2_s": r["flux_lim_erg_cm2_s"],
                "instrument": r["instrument"],
                "l_iso_mw": r["l_iso_mw"],
                "p_beam_10m_kw": r["p_beam_10m_kw"],
                "p_beam_10m_w": f"{p_w:.8g}",
                "phase_id": ph,
                "spectral_regime": regime,
                "star": r["star"],
                "wave_A": f"{w_a:.6g}",
                "wave_um": f"{w_a / 1e4:.6g}",
            })
    assert {r["star"] for r in out} == {"GJ674", "HD20794", "GJ849", "GJ436", "LAWD37"}
    return out


def main() -> None:
    inp_dir = ROOT / "inputs_d091_v4_2"
    if inp_dir.exists():
        raise RuntimeError(f"Prospective hygiene violation: {inp_dir} already exists before cohort build/lock!")

    if sha256_file(ARCHIVE_P) != ARCHIVE_P_SHA256:
        raise RuntimeError("Companion Archive P SHA-256 mismatch!")

    print("1. Extracting D090 Archive P baseline & prior exclusion registry...", flush=True)
    with zipfile.ZipFile(ARCHIVE_P, "r") as zf:
        pe90 = json.loads(zf.read(ARCHIVE_P_PREFIX + "PRIOR_EXCLUSION_VERIFICATION.json").decode("utf-8"))
        mm90 = json.loads(zf.read(ARCHIVE_P_PREFIX + "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").decode("utf-8"))
        sum90 = json.loads(zf.read(ARCHIVE_P_PREFIX + "results/SUMMARY.json").decode("utf-8"))
        u280_rows = list(csv.DictReader(zf.read(ARCHIVE_P_PREFIX + "results/UNIFIED_PANCHROMATIC_V4_1_SYNTHESIS_280STARS.csv").decode("utf-8").splitlines()))
        br30_rows = list(csv.DictReader(zf.read(ARCHIVE_P_PREFIX + "results/PANCHROMATIC_BRIDGE_30STARS.csv").decode("utf-8").splitlines()))
        comb_u_rows = list(csv.DictReader(zf.read(ARCHIVE_P_PREFIX + "results/ALLSKY_COMB_V4_1_UNIFIED_D079_D090.csv").decode("utf-8").splitlines()))
        comb_c_rows = list(csv.DictReader(zf.read(ARCHIVE_P_PREFIX + "results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D090.csv").decode("utf-8").splitlines()))
        d090_coh_rows = list(csv.DictReader(zf.read(ARCHIVE_P_PREFIX + "FROZEN_COHORT_D090.csv").decode("utf-8").splitlines()))

    prior_5bridge_rows = _load_newly_bridged_5star_prior_rows()
    prior_v41_snap = {
        "schema": "D091_PRIOR_V4_1_PHASES_SNAPSHOT",
        "prior_phases": "D079-D090",
        "source_archive_name": ARCHIVE_P.name,
        "source_archive_sha256": ARCHIVE_P_SHA256,
        "prior_v41_unique_stars_count": len(u280_rows),
        "prior_v41_within_10pc_count": sum(1 for r in u280_rows if r["within_10pc"] == "True"),
        "prior_v41_total_exposures_count": sum(int(r["n_exposures_total"]) for r in u280_rows),
        "prior_cumulative_integration_hours": sum90["unified_280star_panchromatic_v4_1_synthesis"]["total_integration_hours_d079_d090"],
        "prior_v41_calibration_trials_count": sum90["unified_280star_panchromatic_v4_1_synthesis"]["total_calibration_trials_d079_d090"],
        "prior_v2_false_alarms_eliminated_total": sum90["unified_280star_panchromatic_v4_1_synthesis"]["v2_false_alarms_eliminated_total"],
        "prior_cumulative_orbital_campaigns_count": sum90["unified_280star_panchromatic_v4_1_synthesis"]["cumulative_orbital_campaigns"],
        "d090_summary_headline": sum90,
        "unified_280star_rows": u280_rows,
        "d090_bridge_30star_rows": br30_rows,
        "newly_bridged_5star_prior_rows": prior_5bridge_rows,
        "allsky_comb_unified_d079_d090": comb_u_rows,
        "allsky_comb_candidates_d079_d090": comb_c_rows,
    }
    (WS / "PRIOR_V4_1_PHASES_SNAPSHOT.json").write_text(json.dumps(prior_v41_snap, indent=2) + "\n", encoding="utf-8")
    (WS / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").write_text(json.dumps({**mm90, "schema": "D091_MULTIMESSENGER_RADIO_TESS_SNAPSHOT"}, indent=2) + "\n", encoding="utf-8")

    excluded_dp_ids = set(pe90["excluded_dp_ids"])
    excluded_dp_ids.update(r["dp_id"] for r in d090_coh_rows)
    excluded_coords = list(pe90["excluded_targets_coordinate_registry"])
    seen_lbl = {c["label"] for c in excluded_coords}
    for s in pe90["star_separation_verification"]:
        lbl = f"{s['canonical_target']}(D090)"
        if lbl not in seen_lbl:
            excluded_coords.append({"label": lbl, "ra_deg": float(s["ra_deg"]), "dec_deg": float(s["dec_deg"])})
            seen_lbl.add(lbl)
    for lbl, r_f, d_f in FORMAT_CHECK_EXCLUDED:
        if lbl not in seen_lbl:
            excluded_coords.append({"label": lbl, "ra_deg": r_f, "dec_deg": d_f})
            seen_lbl.add(lbl)

    print("2. Querying Gaia DR3 & NASA Exoplanet Archive pscomppars...", flush=True)
    gids = [s["gaia_source_id"] for s in TARGET_SPECS if s["gaia_source_id"] is not None]
    gd = tap_json(
        "https://gea.esac.esa.int/tap-server/tap/sync",
        f"SELECT source_id,ra,dec,pmra,pmdec,parallax,phot_g_mean_mag,phot_bp_mean_mag,phot_rp_mean_mag,teff_gspphot,mh_gspphot,radial_velocity FROM gaiadr3.gaia_source WHERE source_id IN ({','.join(map(str, gids))})",
    )
    gcols = [m["name"] for m in gd["metadata"]]
    gaia_by_id = {int(row[0]): dict(zip(gcols, row)) for row in gd["data"]}

    nasa_rows = tap_csv(
        "https://exoplanetarchive.ipac.caltech.edu/TAP/sync",
        "SELECT pl_name,hostname,ra,dec,pl_orbper,pl_tranmid,pl_orbeccen,tran_flag,st_mass,st_teff,st_met,st_radv,sy_dist FROM pscomppars WHERE ra IS NOT NULL AND dec IS NOT NULL",
    )
    nasa_by_pl = {r["pl_name"]: r for r in nasa_rows if r.get("pl_name")}

    print(f"3. Querying ESO Phase-3 TAP ObsCore across {len(TARGET_SPECS)} targets...", flush=True)
    with ThreadPoolExecutor(max_workers=10) as ex:
        all_pools = list(ex.map(lambda sp: fetch_eso_records_for_target(sp, excluded_dp_ids), TARGET_SPECS))

    cohort_rows: list[dict[str, Any]] = []
    campaigns_doc: dict[str, Any] = {}
    sep_verif: list[dict[str, Any]] = []
    total_bytes = 0

    for spec, pool in zip(TARGET_SPECS, all_pools):
        st = spec["canonical_target"]
        picked = select_target_exposures(spec, pool)
        assert len(picked) == int(spec["n_target_exposures"]), f"{st}: expected {spec['n_target_exposures']}, got {len(picked)}"

        g = gaia_by_id[spec["gaia_source_id"]]
        ra_deg = float(g["ra"])
        dec_deg = float(g["dec"])
        pmra = float(g["pmra"]) if g.get("pmra") is not None else 0.0
        pmdec = float(g["pmdec"]) if g.get("pmdec") is not None else 0.0
        dist_pc = float(spec.get("dist_lit") or (1000.0 / float(g["parallax"])))
        within_10pc = dist_pc <= 10.0

        phot_g = float(g["phot_g_mean_mag"]) if g.get("phot_g_mean_mag") is not None else 12.0
        phot_bp = float(g["phot_bp_mean_mag"]) if g.get("phot_bp_mean_mag") is not None else ""
        phot_rp = float(g["phot_rp_mean_mag"]) if g.get("phot_rp_mean_mag") is not None else ""
        teff_k = float(g["teff_gspphot"]) if g.get("teff_gspphot") is not None else float(spec["teff_lit"])
        mh_dex = float(g["mh_gspphot"]) if g.get("mh_gspphot") is not None else float(spec["mh_lit"])
        prior_rv = float(g["radial_velocity"]) if g.get("radial_velocity") is not None else float(spec["rv_lit"])
        mass_msun = float(spec["mass_lit"])

        pl_hits = [r for r in nasa_rows if abs(float(r["dec"]) - dec_deg) < 0.05 and sep_arcsec(ra_deg, dec_deg, float(r["ra"]), float(r["dec"])) < 90.0]
        n_pl = int(spec.get("n_exoplanets_lit") or len(pl_hits))
        if spec["role"] == "CONTROL":
            assert n_pl == 0, f"CONTROL star {st} has {n_pl} planets in pscomppars!"
        has_tr = any(str(r.get("tran_flag") or "0") == "1" for r in pl_hits)

        camp_exps: dict[str, dict[str, Any]] = {}
        if spec.get("orbital_campaign"):
            if spec.get("null_orbital"):
                t0_bjd = 2457000.5
                p_days = float(spec["orb_per_days"])
                ecc = float(spec["orb_e"])
                pl_name = spec["planet_name"]
                kp = compute_keplerian_kp_kms(mass_msun, p_days, ecc)
            else:
                nr = nasa_by_pl[spec["nasa_pl_name"]]
                p_days = float(nr["pl_orbper"] or spec["orb_per_days"])
                ecc = float(nr["pl_orbeccen"] or spec["orb_e"])
                t0_bjd = float(nr["pl_tranmid"] or spec["orb_t0_bjd"])
                mass_msun = float(nr["st_mass"] or mass_msun)
                pl_name = spec["nasa_pl_name"]
                kp = compute_keplerian_kp_kms(mass_msun, p_days, ecc)

            with_phi = []
            for pr in picked:
                bjd_est = pr["mjd_obs"] + 2400000.5
                phi, dv_orb = compute_planet_orbital_rv_kms(bjd_est, t0_bjd, p_days, kp)
                with_phi.append((pr, bjd_est, phi, dv_orb))

            n_half = len(picked) // 2
            ordered_phi = sorted(with_phi, key=lambda x: abs(x[2]))
            in_ids = {x[0]["dp_id"] for x in ordered_phi[:n_half]}
            in_dvs = [x[3] for x in with_phi if x[0]["dp_id"] in in_ids]
            dv_span = max(in_dvs) - min(in_dvs)
            if dv_span < 5.0:
                in_ids = {x[0]["dp_id"] for x in with_phi[:n_half]}
                in_dvs = [x[3] for x in with_phi if x[0]["dp_id"] in in_ids]
                dv_span = max(in_dvs) - min(in_dvs)

            camps_exp_list = []
            for pr, bjd_est, phi, dv_orb in with_phi:
                win_lbl = "IN_WINDOW" if pr["dp_id"] in in_ids else "OUT_OF_WINDOW"
                camp_exps[pr["dp_id"]] = {"phase_window": win_lbl, "signed_phase": round(phi, 5), "planet_orbital_rv_kms": round(dv_orb, 4)}
                camps_exp_list.append({
                    "dp_id": pr["dp_id"], "mjd_obs": round(pr["mjd_obs"], 5),
                    "phase_window": win_lbl, "signed_phase": round(phi, 5), "planet_orbital_rv_kms": round(dv_orb, 4),
                })

            campaigns_doc[st] = {
                "instrument": spec["instrument"], "common_name": spec["common_name"], "role": spec["role"],
                "planet_name": pl_name, "transiting": has_tr, "null_orbital": bool(spec.get("null_orbital")),
                "st_mass_msun": round(mass_msun, 4), "orbper_days": round(p_days, 6), "t0_bjd": round(t0_bjd, 5),
                "ecc": round(ecc, 4), "kp_kms": round(kp, 4), "orbital_dv_span_kms": round(dv_span, 4),
                "n_in_window": n_half, "n_out_of_window": len(picked) - n_half, "exposures": camps_exp_list,
            }

        best_p = min(excluded_coords, key=lambda c: sep_arcsec(ra_deg, dec_deg, float(c["ra_deg"]), float(c["dec_deg"])))
        min_s = sep_arcsec(ra_deg, dec_deg, float(best_p["ra_deg"]), float(best_p["dec_deg"]))
        if not spec["panchromatic_bridge"]:
            sep_verif.append({
                "canonical_target": st, "common_name": spec["common_name"], "instrument": spec["instrument"],
                "role": spec["role"], "panchromatic_bridge": False, "dist_pc": round(dist_pc, 5), "within_10pc": within_10pc,
                "ra_deg": round(ra_deg, 6), "dec_deg": round(dec_deg, 6),
                "nearest_prior_target": best_p["label"], "min_sky_separation_arcsec": round(min_s, 2),
                "status": "VERIFIED_BRAND_NEW_STAR",
            })

        for rank, pr in enumerate(picked, 1):
            ce = camp_exps.get(pr["dp_id"], {"phase_window": "NONE", "signed_phase": 0.0, "planet_orbital_rv_kms": 0.0})
            inst_dir = spec["instrument"]
            total_bytes += pr["total_bytes"]
            f1_rel = f"{inst_dir}/{st}/{pr['f1_id']}.fits"
            f2_rel = f"{inst_dir}/{st}/{pr['f2_id']}.fits" if pr["f2_id"] else ""
            f3_rel = f"{inst_dir}/{st}/{pr['f3_id']}.fits" if pr["f3_id"] else ""
            cohort_rows.append({
                "instrument": spec["instrument"], "canonical_target": st, "common_name": spec["common_name"],
                "role": spec["role"], "subrole": spec["subrole"],
                "panchromatic_bridge": spec["panchromatic_bridge"], "radio_mm_id": spec["radio_mm_id"],
                "gaia_source_id": spec["gaia_source_id"], "s_ra": round(ra_deg, 6), "s_dec": round(dec_deg, 6),
                "pmra_mas_yr": round(pmra, 3), "pmdec_mas_yr": round(pmdec, 3),
                "dist_pc": round(dist_pc, 5), "within_10pc": within_10pc,
                "phot_g_mag": round(phot_g, 4),
                "phot_bp_mag": round(phot_bp, 4) if phot_bp != "" else "",
                "phot_rp_mag": round(phot_rp, 4) if phot_rp != "" else "",
                "j_mag": spec["j_mag"], "h_mag": spec["h_mag"], "ks_mag": spec["ks_mag"],
                "teff_k": round(teff_k, 1), "mh_dex": round(mh_dex, 3), "stellar_mass_msun": round(mass_msun, 4),
                "prior_rv_kms": round(prior_rv, 4), "n_exoplanets": n_pl, "has_transiting_planet": has_tr,
                "epoch_rank": rank, "dp_id": pr["dp_id"], "grating": pr["grating"],
                "resolving_power": round(pr["resolving_power"], 1), "mjd_obs": round(pr["mjd_obs"], 5),
                "t_exptime": round(pr["t_exptime"], 2), "phase_window": ce["phase_window"],
                "signed_phase": ce["signed_phase"], "planet_orbital_rv_kms": ce["planet_orbital_rv_kms"],
                "f1_id": pr["f1_id"], "f1_rel": f1_rel, "f1_url": pr["f1_url"], "f1_bytes": pr["f1_bytes"],
                "f2_id": pr["f2_id"], "f2_rel": f2_rel, "f2_url": pr["f2_url"], "f2_bytes": pr["f2_bytes"],
                "f3_id": pr["f3_id"], "f3_rel": f3_rel, "f3_url": pr["f3_url"], "f3_bytes": pr["f3_bytes"],
                "total_bytes": pr["total_bytes"],
            })

    intra_min = min(
        sep_arcsec(a["ra_deg"], a["dec_deg"], b["ra_deg"], b["dec_deg"])
        for i, a in enumerate(sep_verif)
        for b in sep_verif[i + 1 :]
    )
    min_prior_sep = min(s["min_sky_separation_arcsec"] for s in sep_verif)
    d091_dps = set()
    for r in cohort_rows:
        for k in ("dp_id", "f1_id", "f2_id", "f3_id"):
            if r[k]:
                d091_dps.add(r[k])
    overlap_cnt = len(d091_dps & excluded_dp_ids)
    proj_mib = total_bytes / (1024.0 * 1024.0)
    n_new = len(sep_verif)
    n_new_10pc = sum(1 for s in sep_verif if s["within_10pc"])
    n_bridges = len({r["canonical_target"] for r in cohort_rows if r["panchromatic_bridge"]})

    assert overlap_cnt == 0, f"dp_id overlap {overlap_cnt}!"
    assert n_new == 30 and n_bridges == 7 and n_new_10pc == 10, (n_new, n_bridges, n_new_10pc)
    assert len(campaigns_doc) == 10, len(campaigns_doc)
    assert proj_mib <= 238.0, f"Projected {proj_mib:.2f} MiB > 238 MiB!"
    assert min_prior_sep >= 600.0 and intra_min >= 300.0, (min_prior_sep, intra_min)
    assert not inp_dir.exists(), "inputs_d091_v4_2 must not exist!"

    with (WS / "FROZEN_COHORT_D091.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cohort_rows[0].keys()))
        w.writeheader()
        w.writerows(cohort_rows)

    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(
        json.dumps({"schema": "D091_ORBITAL_CAMPAIGNS_V1", "phase_id": "D091", "n_campaigns": len(campaigns_doc), "campaigns": campaigns_doc}, indent=2) + "\n",
        encoding="utf-8",
    )

    n_fits = sum((1 if r["f1_id"] else 0) + (1 if r["f2_id"] else 0) + (1 if r["f3_id"] else 0) for r in cohort_rows)
    pe91 = {
        "schema": "D091_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D091",
        "verified_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prior_phases_covered": "C001-C037 + D001-D090",
        "format_check_excluded_targets": [x[0] for x in FORMAT_CHECK_EXCLUDED],
        "n_prior_excluded_coords": len(excluded_coords),
        "n_prior_excluded_dp_ids": len(excluded_dp_ids),
        "d091_total_stars": n_new + n_bridges,
        "d091_brand_new_unique_stars": n_new,
        "d091_panchromatic_bridge_stars": n_bridges,
        "d091_brand_new_within_10pc": n_new_10pc,
        "d091_total_exposures": len(cohort_rows),
        "d091_total_fits_files": n_fits,
        "d091_projected_download_bytes": total_bytes,
        "d091_projected_download_gib": round(total_bytes / (1024.0 ** 3), 4),
        "d091_projected_download_mib": round(proj_mib, 2),
        "d091_dp_id_overlap_count": overlap_cnt,
        "min_brand_new_sky_separation_arcsec": round(min_prior_sep, 2),
        "min_intra_d091_brand_new_separation_arcsec": round(intra_min, 2),
        "star_separation_verification": sep_verif,
        "excluded_dp_ids": sorted(excluded_dp_ids),
        "excluded_targets_coordinate_registry": excluded_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pe91, indent=2) + "\n", encoding="utf-8")

    print(
        f"DONE build_cohort: {len(cohort_rows)} exposures ({n_fits} FITS), "
        f"{n_new + n_bridges} stars ({n_new} new [{n_new_10pc} <10pc] + {n_bridges} bridges), "
        f"{len(campaigns_doc)} orbital campaigns, proj={proj_mib:.2f} MiB, dp_overlap={overlap_cnt}, "
        f"min_prior_sep={min_prior_sep:.1f}\", min_intra_sep={intra_min:.1f}\"",
        flush=True,
    )


if __name__ == "__main__":
    main()
