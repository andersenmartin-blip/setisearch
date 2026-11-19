#!/usr/bin/env python3
"""
Phase D089 prospective cohort builder & lock metadata generator (`SPACE_LYMAN_FUV_NUV_V4_0`).

Strict prospective rule:
- Runs BEFORE any D089 science FITS bytes are touched (`ROOT/inputs_d089_v4_0` MUST NOT EXIST).
- Queries ONLY archival metadata endpoints (read-only):
  * STScI FUSE CSV search (`archive.stsci.edu/fuse/search.php`) + MAST CAOM Products (`fcal.fit.gz`)
  * STScI HST CSV search (`archive.stsci.edu/hst/search.php`) + MAST CAOM Products (`*_x1d.fits`)
  * ESA Gaia DR3 TAP (astrometry, parallax, G/BP/RP photometry, RV)
  * GAVO 2MASS PSC TAP (J, H, Ks photometry & designations)
  * NASA Exoplanet Archive `pscomppars` TAP (planet counts & Keplerian ephemerides)
- Emits 5 prospective lock files in WS/:
  1. `FROZEN_COHORT_D089.csv` (37 stars / 192 exposures: 36 FUSE + 84 COS + 72 STIS NUV)
  2. `ORBITAL_CAMPAIGNS_AND_KINEMATICS.json` (10 campaigns #71-#80: 3 null controls + 7 science)
  3. `PRIOR_EXCLUSION_VERIFICATION.json` (C001-C037 + D001-D088 + D089 format checks)
  4. `PRIOR_V3_PHASES_SNAPSHOT.json` (frozen D079-D088: 220 stars, 1,567 exp, 117 <10pc, 21 bridges)
  5. `MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json` (23/23 radio + 1 TESS closure)
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import io
import json
import math
import time
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from v4_0_detector import (
    compute_keplerian_kp_kms,
    compute_planet_orbital_rv_kms,
)

ROOT = Path(".")
AWS = ROOT / "analysis_workspace"
WS = Path(__file__).resolve().parent
INP_DIR = ROOT / "inputs_d089_v4_0"

D080_WS = AWS / "work_echelle_20261114_d080_v3_1_exoplanet_survey"
D081_WS = AWS / "work_echelle_20261115_d081_v3_2_transit_kinematics_and_10pc_survey"
D083_WS = AWS / "work_crires_20261115_d083_v3_4_kband_and_100star_synthesis"
D086_WS = AWS / "work_uves_panchrom_20261117_d086_v3_7_nuv_and_comb_v4_1"
D088_WS = AWS / "work_radio23_allsky_20261118_d088_v3_9_northern_and_comb_v4_1"

GAIA_TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
GAVO_TAP = "https://dc.g-vo.org/tap/sync"
NASA_TAP = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
MAST_INVOKE = "https://mast.stsci.edu/api/v0/invoke"
FUSE_SEARCH = "https://archive.stsci.edu/fuse/search.php"
HST_SEARCH = "https://archive.stsci.edu/hst/search.php"

MAX_PROJ_DOWNLOAD_GIB = 0.55

D089_FORMAT_CHECKS = [
    {
        "label": "BD+28D4211 (D089 FUSE & STIS NUV format check)",
        "ra_deg": 327.795958,
        "dec_deg": 28.863944,
        "dp_ids": ["m1031201000", "m103120100000all4ttag", "o3zx02050"],
    },
    {
        "label": "G191B2B (D089 COS G130M format check)",
        "ra_deg": 76.377500,
        "dec_deg": 52.831083,
        "dp_ids": ["lbxn01t6q", "lbxn01010"],
    },
]

# 37 stars / 192 exposures (36 FUSE + 84 COS + 72 STIS NUV)
TARGET_SPECS: list[dict[str, Any]] = [
    # ==================== FUSE_FUV (8 stars / 36 exp: 2 CTRL + 6 SCI) ====================
    {
        "instrument": "FUSE_FUV", "canonical_target": "HD222107", "common_name": "lambda And (HD 222107)",
        "role": "CONTROL", "subrole": "NULL_FUSE_CONTROL", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 1939115478598580352, "n_target_exposures": 4, "orbital_campaign": False,
        "fuse_allow": ("HD222107", "LAMAND"), "teff_lit": 4650.0, "mh_lit": -0.30, "mass_lit": 1.10, "rv_lit": 6.3,
    },
    {
        "instrument": "FUSE_FUV", "canonical_target": "HD180711", "common_name": "delta Dra (HD 180711)",
        "role": "CONTROL", "subrole": "NULL_FUSE_CONTROL", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 2255173119658513408, "n_target_exposures": 4, "orbital_campaign": False,
        "fuse_allow": ("DELDRA", "HD180711"), "teff_lit": 4820.0, "mh_lit": -0.12, "mass_lit": 1.80, "rv_lit": 24.8,
    },
    {
        "instrument": "FUSE_FUV", "canonical_target": "ALPCENA", "common_name": "alpha Cen A (HD 128620)",
        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_LYMAN_10PC", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": None, "n_target_exposures": 3, "orbital_campaign": False,
        "fuse_allow": ("HD128620", "ACENA-VISIT1", "ACENA"),
        "ra_lit": 219.902058, "dec_lit": -60.833993, "pmra_lit": -3679.25, "pmdec_lit": 473.67,
        "dist_lit": 1.339, "vmag_lit": 0.01, "teff_lit": 5790.0, "mh_lit": 0.20, "mass_lit": 1.1055, "rv_lit": -21.4,
    },
    {
        "instrument": "FUSE_FUV", "canonical_target": "ALFTAU", "common_name": "Aldebaran (alpha Tau)",
        "role": "SCIENCE", "subrole": "LYMAN_FUV_EXOPLANET_HOST", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": None, "n_target_exposures": 4, "orbital_campaign": False,
        "nasa_hostname": "alf Tau", "fuse_allow": ("HD029139", "HD29139", "ALFTAU"),
        "ra_lit": 68.980163, "dec_lit": 16.509302, "pmra_lit": 63.45, "pmdec_lit": -188.94,
        "dist_lit": 20.4332, "vmag_lit": 0.86, "teff_lit": 4055.0, "mh_lit": -0.10, "mass_lit": 1.13, "rv_lit": 54.26,
    },
    {
        "instrument": "FUSE_FUV", "canonical_target": "HD179949", "common_name": "HD 179949",
        "role": "SCIENCE", "subrole": "LYMAN_FUV_EXOPLANET_HOST", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 6770313530317154560, "n_target_exposures": 4, "orbital_campaign": False,
        "nasa_hostname": "HD 179949", "fuse_allow": ("HD179949",),
        "teff_lit": 6168.0, "mh_lit": 0.14, "mass_lit": 1.21, "rv_lit": -24.7,
    },
    {
        "instrument": "FUSE_FUV", "canonical_target": "HD203387", "common_name": "iota Cap (HD 203387)",
        "role": "SCIENCE", "subrole": "LYMAN_FUV_CHROMOSPHERE", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 6835905927256722688, "n_target_exposures": 4, "orbital_campaign": False,
        "fuse_allow": ("HD203387", "IOTACAP"), "teff_lit": 5240.0, "mh_lit": -0.05, "mass_lit": 2.40, "rv_lit": 12.1,
    },
    {
        "instrument": "FUSE_FUV", "canonical_target": "EPSERI", "common_name": "eps Eri (HD 22049)",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_LYMAN_NIR_BRIDGE_10PC", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 5164707970261890560, "n_target_exposures": 8, "orbital_campaign": False,
        "nasa_hostname": "eps Eri", "fuse_allow": ("HD22049", "EPSERI"),
        "teff_lit": 5020.4, "mh_lit": -0.09, "mass_lit": 0.82, "rv_lit": 16.0,
    },
    {
        "instrument": "FUSE_FUV", "canonical_target": "BETPIC", "common_name": "beta Pictoris (HD 39060)",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_LYMAN_KBAND_BRIDGE", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 4792774797545800832, "n_target_exposures": 5, "orbital_campaign": False,
        "nasa_hostname": "bet Pic", "fuse_allow": ("HD39060", "BETPIC"),
        "teff_lit": 8038.7, "mh_lit": 0.0, "mass_lit": 1.789, "rv_lit": 20.0,
    },

    # ==================== HST_COS_FUV G130M (17 stars / 84 exp: 3 CTRL + 14 SCI) ====================
    {
        "instrument": "HST_COS_FUV", "canonical_target": "LTT2050", "common_name": "LTT 2050 (GJ 3304)",
        "role": "CONTROL", "subrole": "NULL_ORBITAL_CONTROL_COS", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3184351876391975808, "n_target_exposures": 8, "orbital_campaign": True, "null_orbital": True,
        "planet_name": "Null Control (synthetic P=1.27d)", "orb_per_days": 1.2731, "orb_e": 0.0, "window_mode": "CONJUNCTION", "half_phase_window": 0.16,
        "teff_lit": 3450.0, "mh_lit": -0.20, "mass_lit": 0.42, "rv_lit": -7.1,
    },
    {
        "instrument": "HST_COS_FUV", "canonical_target": "LHS2686", "common_name": "LHS 2686",
        "role": "CONTROL", "subrole": "NULL_CONTROL_COS", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 1554433777791815808, "n_target_exposures": 4, "orbital_campaign": False,
        "teff_lit": 3120.0, "mh_lit": -0.10, "mass_lit": 0.16, "rv_lit": -11.9,
    },
    {
        "instrument": "HST_COS_FUV", "canonical_target": "HD199288", "common_name": "HD 199288",
        "role": "CONTROL", "subrole": "NULL_CONTROL_COS", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 6484716209628726912, "n_target_exposures": 4, "orbital_campaign": False,
        "teff_lit": 5760.0, "mh_lit": -0.63, "mass_lit": 0.85, "rv_lit": -7.7,
    },
    {
        "instrument": "HST_COS_FUV", "canonical_target": "GJ667C", "common_name": "GJ 667 C",
        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_COS_10PC", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 5975663354131618304, "n_target_exposures": 4, "orbital_campaign": False,
        "nasa_hostname": "GJ 667 C", "teff_lit": 3350.0, "mh_lit": -0.55, "mass_lit": 0.33, "rv_lit": 6.5,
    },
    {
        "instrument": "HST_COS_FUV", "canonical_target": "GJ367", "common_name": "GJ 367 (Tahay)",
        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_COS_10PC", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 5412250540681250560, "n_target_exposures": 4, "orbital_campaign": False,
        "nasa_hostname": "GJ 367", "teff_lit": 3522.0, "mh_lit": -0.01, "mass_lit": 0.455, "rv_lit": 47.9,
    },
    {
        "instrument": "HST_COS_FUV", "canonical_target": "TRAPPIST1", "common_name": "TRAPPIST-1",
        "role": "SCIENCE", "subrole": "SPACE_FUV_TRANSIT_ORBITAL", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 2635476908753563008, "n_target_exposures": 8, "orbital_campaign": True, "null_orbital": False,
        "nasa_hostname": "TRAPPIST-1", "planet_name": "TRAPPIST-1 e", "transiting": True,
        "orb_per_days": 6.101013, "orb_t0_bjd": 2457660.3676621, "orb_e": 0.0051,
        "window_mode": "CONJUNCTION", "half_phase_window": 0.16,
        "teff_lit": 2566.0, "mh_lit": 0.04, "mass_lit": 0.0898, "rv_lit": -52.0,
    },
    {
        "instrument": "HST_COS_FUV", "canonical_target": "HD97658", "common_name": "HD 97658",
        "role": "SCIENCE", "subrole": "SPACE_FUV_TRANSIT_ORBITAL", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3997075206232885888, "n_target_exposures": 8, "orbital_campaign": True, "null_orbital": False,
        "nasa_hostname": "HD 97658", "planet_name": "HD 97658 b", "transiting": True,
        "orb_per_days": 9.4897116, "orb_t0_bjd": 2458904.9366, "orb_e": 0.05,
        "window_mode": "CONJUNCTION", "half_phase_window": 0.16,
        "teff_lit": 5212.0, "mh_lit": -0.23, "mass_lit": 0.85, "rv_lit": -1.39,
    },
    {
        "instrument": "HST_COS_FUV", "canonical_target": "TOI776", "common_name": "TOI-776",
        "role": "SCIENCE", "subrole": "SPACE_FUV_TRANSIT_ORBITAL", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3460438662009633408, "n_target_exposures": 8, "orbital_campaign": True, "null_orbital": False,
        "nasa_hostname": "TOI-776", "planet_name": "TOI-776 c", "transiting": True,
        "orb_per_days": 15.665323, "orb_t0_bjd": 2459324.53478, "orb_e": 0.089,
        "window_mode": "CONJUNCTION", "half_phase_window": 0.16,
        "teff_lit": 3725.0, "mh_lit": -0.20, "mass_lit": 0.542, "rv_lit": 49.34,
    },
    {
        "instrument": "HST_COS_FUV", "canonical_target": "GJ3470", "common_name": "GJ 3470",
        "role": "SCIENCE", "subrole": "SPACE_FUV_TRANSIT_HOST", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 654687847820642560, "n_target_exposures": 4, "orbital_campaign": False,
        "nasa_hostname": "GJ 3470", "teff_lit": 3600.0, "mh_lit": 0.20, "mass_lit": 0.539, "rv_lit": 26.52,
    },
    {
        "instrument": "HST_COS_FUV", "canonical_target": "HATP11", "common_name": "HAT-P-11",
        "role": "SCIENCE", "subrole": "SPACE_FUV_TRANSIT_HOST", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 2086512227851023872, "n_target_exposures": 4, "orbital_campaign": False,
        "nasa_hostname": "HAT-P-11", "teff_lit": 4653.0, "mh_lit": 0.31, "mass_lit": 0.811, "rv_lit": -63.24,
    },
    {
        "instrument": "HST_COS_FUV", "canonical_target": "TOI2076", "common_name": "TOI-2076",
        "role": "SCIENCE", "subrole": "SPACE_FUV_TRANSIT_HOST", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 1490845584382687232, "n_target_exposures": 4, "orbital_campaign": False,
        "nasa_hostname": "TOI-2076", "teff_lit": 5187.0, "mh_lit": -0.03, "mass_lit": 0.849, "rv_lit": -12.8,
    },
    {
        "instrument": "HST_COS_FUV", "canonical_target": "WASP69", "common_name": "WASP-69",
        "role": "SCIENCE", "subrole": "SPACE_FUV_TRANSIT_HOST", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 6910753016653587840, "n_target_exposures": 4, "orbital_campaign": False,
        "nasa_hostname": "WASP-69", "teff_lit": 4792.0, "mh_lit": 0.14, "mass_lit": 0.83, "rv_lit": -9.63,
    },
    {
        "instrument": "HST_COS_FUV", "canonical_target": "GJ3929", "common_name": "GJ 3929",
        "role": "SCIENCE", "subrole": "SPACE_FUV_TRANSIT_HOST", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 1372215976327300480, "n_target_exposures": 4, "orbital_campaign": False,
        "nasa_hostname": "GJ 3929", "teff_lit": 3384.0, "mh_lit": -0.02, "mass_lit": 0.313, "rv_lit": 10.27,
    },
    {
        "instrument": "HST_COS_FUV", "canonical_target": "TOI1468", "common_name": "TOI-1468",
        "role": "SCIENCE", "subrole": "SPACE_FUV_TRANSIT_HOST", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 2785466581298775680, "n_target_exposures": 4, "orbital_campaign": False,
        "nasa_hostname": "TOI-1468", "teff_lit": 3376.0, "mh_lit": -0.04, "mass_lit": 0.3527, "rv_lit": -17.0,
    },
    {
        "instrument": "HST_COS_FUV", "canonical_target": "LTT3780", "common_name": "LTT 3780",
        "role": "SCIENCE", "subrole": "SPACE_FUV_TRANSIT_HOST", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3767281845873242112, "n_target_exposures": 4, "orbital_campaign": False,
        "nasa_hostname": "LTT 3780", "teff_lit": 3358.0, "mh_lit": 0.06, "mass_lit": 0.381, "rv_lit": 0.27,
    },
    {
        "instrument": "HST_COS_FUV", "canonical_target": "GJ832", "common_name": "GJ 832",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_COS_FUV_OPTICAL_10PC", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 6562924609150908416, "n_target_exposures": 4, "orbital_campaign": False,
        "nasa_hostname": "GJ 832", "teff_lit": 3472.0, "mh_lit": -0.30, "mass_lit": 0.45, "rv_lit": 12.52,
    },
    {
        "instrument": "HST_COS_FUV", "canonical_target": "GJ876", "common_name": "IL Aqr (GJ 876)",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_COS_FUV_OPTICAL_10PC", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 2603090003484152064, "n_target_exposures": 4, "orbital_campaign": False,
        "nasa_hostname": "GJ 876", "teff_lit": 3293.7, "mh_lit": 0.19, "mass_lit": 0.32, "rv_lit": -1.6,
    },

    # ==================== HST_STIS_NUV E230M/E230H (12 stars / 72 exp: 4 CTRL + 8 SCI) ====================
    {
        "instrument": "HST_STIS_NUV", "canonical_target": "HD108317", "common_name": "HD 108317",
        "role": "CONTROL", "subrole": "NULL_STIS_NUV_BLUE_CONTROL", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3708088881477489792, "n_target_exposures": 4, "orbital_campaign": False,
        "stis_grat": "E230M", "stis_cenwave": "1978",
        "teff_lit": 5280.0, "mh_lit": -2.30, "mass_lit": 0.80, "rv_lit": 6.5,
    },
    {
        "instrument": "HST_STIS_NUV", "canonical_target": "HD128279", "common_name": "HD 128279",
        "role": "CONTROL", "subrole": "NULL_STIS_NUV_BLUE_CONTROL", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 6221846137890957312, "n_target_exposures": 4, "orbital_campaign": False,
        "stis_grat": "E230M", "stis_cenwave": "1978",
        "teff_lit": 5290.0, "mh_lit": -2.20, "mass_lit": 0.80, "rv_lit": -76.0,
    },
    {
        "instrument": "HST_STIS_NUV", "canonical_target": "HD211998", "common_name": "nu Ind (HD 211998)",
        "role": "CONTROL", "subrole": "NULL_ORBITAL_CONTROL_STIS_NUV", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 6382933589314905472, "n_target_exposures": 8, "orbital_campaign": True, "null_orbital": True,
        "stis_grat": "E230H", "stis_cenwave": "2013",
        "planet_name": "Null Control (synthetic P=1.37d)", "orb_per_days": 1.3700, "orb_e": 0.0, "window_mode": "CONJUNCTION", "half_phase_window": 0.16,
        "teff_lit": 5300.0, "mh_lit": -1.50, "mass_lit": 0.85, "rv_lit": 26.2,
    },
    {
        "instrument": "HST_STIS_NUV", "canonical_target": "HD122563", "common_name": "HD 122563",
        "role": "CONTROL", "subrole": "NULL_ORBITAL_CONTROL_STIS_NUV", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3723554268436602240, "n_target_exposures": 8, "orbital_campaign": True, "null_orbital": True,
        "stis_grat": "E230M", "stis_cenwave": "2707",
        "planet_name": "Null Control (synthetic P=2.41d)", "orb_per_days": 2.4137, "orb_e": 0.0, "window_mode": "CONJUNCTION", "half_phase_window": 0.16,
        "teff_lit": 4635.0, "mh_lit": -2.64, "mass_lit": 0.86, "rv_lit": -26.5,
    },
    {
        "instrument": "HST_STIS_NUV", "canonical_target": "HD62509", "common_name": "Pollux (beta Gem / HD 62509)",
        "role": "SCIENCE", "subrole": "SPACE_NUV_GAP_EXOPLANET_HOST", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": None, "n_target_exposures": 4, "orbital_campaign": False,
        "stis_grat": "E230M", "stis_cenwave": "1978", "nasa_hostname": "HD 62509",
        "ra_lit": 116.328958, "dec_lit": 28.026199, "pmra_lit": -626.55, "pmdec_lit": -45.80,
        "dist_lit": 10.34, "vmag_lit": 1.14, "teff_lit": 4892.6, "mh_lit": 0.09, "mass_lit": 2.0, "rv_lit": 3.23,
    },
    {
        "instrument": "HST_STIS_NUV", "canonical_target": "PROCYON", "common_name": "Procyon A (alpha CMi)",
        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_STIS_NUV_10PC", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": None, "n_target_exposures": 4, "orbital_campaign": False,
        "stis_grat": "E230H", "stis_cenwave": "2762",
        "ra_lit": 114.825493, "dec_lit": 5.224993, "pmra_lit": -714.59, "pmdec_lit": -1036.80,
        "dist_lit": 3.514, "vmag_lit": 0.34, "teff_lit": 6530.0, "mh_lit": -0.05, "mass_lit": 1.499, "rv_lit": -3.20,
    },
    {
        "instrument": "HST_STIS_NUV", "canonical_target": "ARCTURUS", "common_name": "Arcturus (alpha Boo)",
        "role": "SCIENCE", "subrole": "SPACE_NUV_GAP_COOL_GIANT", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": None, "n_target_exposures": 4, "orbital_campaign": False,
        "stis_grat": "E230H", "stis_cenwave": "3012",
        "ra_lit": 213.915300, "dec_lit": 19.182409, "pmra_lit": -1093.45, "pmdec_lit": -1999.40,
        "dist_lit": 11.26, "vmag_lit": -0.05, "teff_lit": 4286.0, "mh_lit": -0.52, "mass_lit": 1.08, "rv_lit": -5.19,
    },
    {
        "instrument": "HST_STIS_NUV", "canonical_target": "LTT9779", "common_name": "LTT 9779",
        "role": "SCIENCE", "subrole": "SPACE_NUV_TRANSIT_ORBITAL", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 2307504062045842688, "n_target_exposures": 8, "orbital_campaign": True, "null_orbital": False,
        "stis_grat": "E230M", "stis_cenwave": "2707", "nasa_hostname": "LTT 9779", "planet_name": "LTT 9779 b", "transiting": True,
        "orb_per_days": 0.792052, "orb_t0_bjd": 2458354.2143, "orb_e": 0.0,
        "window_mode": "TRANSIT_CONJUNCTION", "half_phase_window": 0.06,
        "teff_lit": 5443.0, "mh_lit": 0.27, "mass_lit": 1.02, "rv_lit": -10.63,
    },
    {
        "instrument": "HST_STIS_NUV", "canonical_target": "HATP41", "common_name": "HAT-P-41",
        "role": "SCIENCE", "subrole": "SPACE_NUV_TRANSIT_HOST", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 4290415081653653632, "n_target_exposures": 4, "orbital_campaign": False,
        "stis_grat": "E230M", "stis_cenwave": "2707", "nasa_hostname": "HAT-P-41",
        "teff_lit": 6390.0, "mh_lit": 0.21, "mass_lit": 2.56, "rv_lit": 31.68,
    },
    {
        "instrument": "HST_STIS_NUV", "canonical_target": "55CNC", "common_name": "55 Cnc (rho1 Cnc)",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_STIS_NUV_ORBITAL_BRIDGE", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 704967037090946688, "n_target_exposures": 8, "orbital_campaign": True, "null_orbital": False,
        "stis_grat": "E230M", "stis_cenwave": "2707", "nasa_hostname": "55 Cnc", "planet_name": "55 Cnc e", "transiting": True,
        "orb_per_days": 0.7365474, "orb_t0_bjd": 2457063.2096, "orb_e": 0.05,
        "window_mode": "CONJUNCTION", "half_phase_window": 0.16,
        "teff_lit": 5198.0, "mh_lit": 0.31, "mass_lit": 1.015, "rv_lit": 27.41,
    },
    {
        "instrument": "HST_STIS_NUV", "canonical_target": "HD189733", "common_name": "HD 189733",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_STIS_NUV_ORBITAL_BRIDGE", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 1827242816201846144, "n_target_exposures": 8, "orbital_campaign": True, "null_orbital": False,
        "stis_grat": "E230M", "stis_cenwave": "2707", "nasa_hostname": "HD 189733", "planet_name": "HD 189733 b", "transiting": True,
        "orb_per_days": 2.21857567, "orb_t0_bjd": 2453955.5255511, "orb_e": 0.0,
        "window_mode": "TRANSIT_CONJUNCTION", "half_phase_window": 0.05,
        "teff_lit": 5052.0, "mh_lit": -0.03, "mass_lit": 0.79, "rv_lit": -2.20,
    },
    {
        "instrument": "HST_STIS_NUV", "canonical_target": "HD209458", "common_name": "HD 209458",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_STIS_NUV_ORBITAL_BRIDGE", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 1779546757669063552, "n_target_exposures": 8, "orbital_campaign": True, "null_orbital": False,
        "stis_grat": "E230M", "stis_cenwave": "2707", "nasa_hostname": "HD 209458", "planet_name": "HD 209458 b", "transiting": True,
        "orb_per_days": 3.52474859, "orb_t0_bjd": 2451659.93742, "orb_e": 0.0,
        "window_mode": "TRANSIT_CONJUNCTION", "half_phase_window": 0.03,
        "teff_lit": 6091.0, "mh_lit": 0.02, "mass_lit": 1.23, "rv_lit": -14.74,
    },
]


def sky_sep_arcsec(r1: float, d1: float, r2: float, d2: float) -> float:
    r1r, d1r, r2r, d2r = map(math.radians, (r1, d1, r2, d2))
    c = max(-1.0, min(1.0, math.sin(d1r) * math.sin(d2r) + math.cos(d1r) * math.cos(d2r) * math.cos(r1r - r2r)))
    return math.degrees(math.acos(c)) * 3600.0


def parse_hms_dms(ra_s: str, dec_s: str) -> tuple[float, float]:
    rt = [float(x) for x in ra_s.strip().split()]
    dt = [float(x) for x in dec_s.strip().split()]
    ra_deg = 15.0 * (rt[0] + rt[1] / 60.0 + rt[2] / 3600.0)
    sgn = -1.0 if dec_s.strip().startswith("-") else 1.0
    dec_deg = sgn * (abs(dt[0]) + dt[1] / 60.0 + dt[2] / 3600.0)
    return ra_deg, dec_deg


def parse_stsci_time_to_mjd(s: str) -> float | None:
    s = s.strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.datetime.strptime(s[:26], fmt) if ".%f" in fmt else datetime.datetime.strptime(s[:19], fmt)
            return dt.replace(tzinfo=datetime.timezone.utc).timestamp() / 86400.0 + 40587.0
        except Exception:
            pass
    return None


def mjd_to_bjd_est(mjd_mid: float, ra_deg: float, dec_deg: float) -> float:
    jd = float(mjd_mid) + 2400000.5
    d = jd - 2451545.0
    t_c = d / 36525.0
    g = math.radians((357.5291092 + 35999.0502909 * t_c) % 360.0)
    l0 = math.radians((280.46646 + 36000.76983 * t_c) % 360.0)
    c_eq = math.radians((1.914602 - 0.004817 * t_c) * math.sin(g) + 0.019993 * math.sin(2.0 * g))
    lam_sun = l0 + c_eq
    eps = math.radians(23.4392911 - 0.0130042 * t_c)
    ra, dec = math.radians(ra_deg), math.radians(dec_deg)
    roemer_days = (499.00478 / 86400.0) * (
        math.cos(dec) * math.cos(ra) * (-math.cos(lam_sun))
        + math.cos(dec) * math.sin(ra) * (-math.sin(lam_sun) * math.cos(eps))
        + math.sin(dec) * (-math.sin(lam_sun) * math.sin(eps))
    )
    return jd + roemer_days


def http_get_text(url: str, timeout: float = 35.0, retries: int = 4) -> str:
    last_e: Exception | None = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETI-D089/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as exc:
            last_e = exc
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"HTTP GET failed {url}: {last_e}")


def tap_json(base: str, params: dict[str, Any], timeout: float = 45.0, use_get: bool = False) -> Any:
    enc = urllib.parse.urlencode(params)
    last_e: Exception | None = None
    for i in range(4):
        try:
            if use_get:
                req = urllib.request.Request(f"{base}?{enc}", headers={"User-Agent": "SETI-D089/1.0"})
            else:
                req = urllib.request.Request(base, data=enc.encode(), headers={"User-Agent": "SETI-D089/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:
            last_e = exc
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"TAP query failed {base}: {last_e}")


def mast_invoke(svc: str, params: dict[str, Any], timeout: float = 55.0, retries: int = 5) -> list[dict[str, Any]]:
    body = urllib.parse.urlencode({"request": json.dumps({"service": svc, "format": "json", "params": params})}).encode()
    last_e: Exception | None = None
    for i in range(retries):
        try:
            req = urllib.request.Request(MAST_INVOKE, data=body, headers={"User-Agent": "SETI-D089/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))["data"]
        except Exception as exc:
            last_e = exc
            time.sleep(2.0 * (i + 1))
    raise RuntimeError(f"MAST {svc} failed: {last_e}")


def signed_phase(bjd: float, t0: float, orb_per: float) -> float:
    return ((bjd - t0) / orb_per + 0.5) % 1.0 - 0.5


def _select_time_spaced(items: list[dict[str, Any]], n_target: int) -> list[dict[str, Any]]:
    ordered = sorted(items, key=lambda x: x["mjd_mid"])
    if len(ordered) <= n_target:
        return ordered
    idxs = sorted({min(len(ordered) - 1, int(round(i * (len(ordered) - 1) / max(1, n_target - 1)))) for i in range(n_target)})
    while len(idxs) < n_target:
        for j in range(len(ordered)):
            if j not in idxs:
                idxs.append(j)
                if len(idxs) == n_target:
                    break
    return [ordered[j] for j in sorted(idxs)]


def query_stsci_csv(base: str, params: dict[str, str]) -> list[dict[str, str]]:
    txt = http_get_text(f"{base}?{urllib.parse.urlencode(params)}", timeout=30.0)
    lines = [ln for ln in txt.splitlines() if ln.strip() and not ln.startswith("#")]
    if len(lines) < 3:
        return []
    return list(csv.DictReader([lines[0]] + lines[2:]))


def build() -> None:
    if INP_DIR.exists():
        raise RuntimeError(f"STRICT PROSPECTIVE LOCK VIOLATION: {INP_DIR} already exists before cohort lock!")

    print("=== Phase D089 Build Cohort (SPACE_LYMAN_FUV_NUV_V4_0) ===", flush=True)

    # 1. Prior Exclusion Registry (C001-C037 + D001-D088 + D089 format checks)
    pe_d88 = json.loads((D088_WS / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    excl_dp_ids: set[str] = set(pe_d88["excluded_dp_ids"])
    excl_coords: list[dict[str, Any]] = list(pe_d88["excluded_targets_coordinate_registry"])
    seen_coord_labels = {ec["label"] for ec in excl_coords}

    with (D088_WS / "FROZEN_COHORT_D088.csv").open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            excl_dp_ids.add(row["dp_id"])
            if row["panchromatic_bridge"] != "True":
                lbl = f"{row['canonical_target']}(D088)"
                if lbl not in seen_coord_labels:
                    seen_coord_labels.add(lbl)
                    excl_coords.append({
                        "label": lbl,
                        "ra_deg": round(float(row["s_ra"]), 6),
                        "dec_deg": round(float(row["s_dec"]), 6),
                    })

    for fc in D089_FORMAT_CHECKS:
        for dpid in fc["dp_ids"]:
            excl_dp_ids.add(dpid)
        if fc["label"] not in seen_coord_labels:
            seen_coord_labels.add(fc["label"])
            excl_coords.append({"label": fc["label"], "ra_deg": fc["ra_deg"], "dec_deg": fc["dec_deg"]})

    # 2. Gaia DR3 batch + NASA Exoplanet Archive pscomppars + 2MASS PSC
    print("  Querying Gaia DR3 batch...", flush=True)
    gids = [s["gaia_source_id"] for s in TARGET_SPECS if s["gaia_source_id"] is not None]
    gaia_cols = "source_id,ra,dec,parallax,pmra,pmdec,phot_g_mean_mag,phot_bp_mean_mag,phot_rp_mean_mag,bp_rp,radial_velocity,teff_gspphot,mh_gspphot"
    gaia_sql = f"SELECT {gaia_cols} FROM gaiadr3.gaia_source WHERE source_id IN ({','.join(map(str, gids))})"
    gaia_res = tap_json(GAIA_TAP, {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "json", "QUERY": gaia_sql})
    col_names = [m["name"] for m in gaia_res["metadata"]]
    gaia_by_id = {int(rec["source_id"]): rec for rec in (dict(zip(col_names, r)) for r in gaia_res["data"])}
    assert len(gaia_by_id) == len(gids), f"Expected {len(gids)} Gaia stars, got {len(gaia_by_id)}"

    print(f"  Got {len(gaia_by_id)} Gaia stars. Querying NASA pscomppars...", flush=True)
    nasa_hosts = sorted({s["nasa_hostname"] for s in TARGET_SPECS if s.get("nasa_hostname")})
    hn_sql = ",".join(f"'{h}'" for h in nasa_hosts)
    gaia_str = ",".join(f"'Gaia DR3 {g}'" for g in gids)
    nasa_rows = tap_json(
        NASA_TAP,
        {"query": f"SELECT hostname, gaia_dr3_id, sy_pnum, pl_name, tran_flag, pl_orbper, pl_tranmid, pl_orbeccen, st_teff, st_met, st_mass, st_radv FROM pscomppars WHERE hostname IN ({hn_sql})", "format": "json"},
        use_get=True,
    )
    nasa_rows_gid = tap_json(
        NASA_TAP,
        {"query": f"SELECT hostname, gaia_dr3_id, sy_pnum, pl_name, tran_flag, pl_orbper, pl_tranmid, pl_orbeccen, st_teff, st_met, st_mass, st_radv FROM pscomppars WHERE gaia_dr3_id IN ({gaia_str})", "format": "json"},
        use_get=True,
    )
    nasa_rows = list(nasa_rows) + list(nasa_rows_gid)
    nasa_by_gid: dict[int, list[dict[str, Any]]] = {}
    nasa_by_host: dict[str, list[dict[str, Any]]] = {}
    for nr in nasa_rows:
        hn = str(nr.get("hostname") or "").strip()
        nasa_by_host.setdefault(hn, []).append(nr)
        gd = str(nr.get("gaia_dr3_id") or "")
        if gd.startswith("Gaia DR3 "):
            nasa_by_gid.setdefault(int(gd.split()[-1]), []).append(nr)

    # Resolve Gaia/2MASS/NASA metadata for each target and run search.php
    print("  Querying 2MASS PSC + STScI FUSE/HST CSV metadata across 37 targets...", flush=True)
    star_meta_map: dict[str, dict[str, Any]] = {}
    raw_obs_by_star: dict[str, list[dict[str, Any]]] = {}
    all_obs_ids_need_caom: list[str] = []

    for idx_s, spec in enumerate(TARGET_SPECS, 1):
        st = spec["canonical_target"]
        print(f"    [{idx_s:2d}/{len(TARGET_SPECS)}] {st} ({spec['instrument']})...", flush=True)
        gid = spec["gaia_source_id"]
        if gid is not None:
            g = gaia_by_id[gid]
            ra16, dec16 = float(g["ra"]), float(g["dec"])
            pmra, pmdec = float(g["pmra"] or 0.0), float(g["pmdec"] or 0.0)
            cosd = max(0.1, math.cos(math.radians(dec16)))
            ra00 = ra16 - (16.0 * pmra) / (3600000.0 * cosd)
            dec00 = dec16 - (16.0 * pmdec) / 3600000.0
            dist_pc = 1000.0 / float(g["parallax"])
            g_mag = float(g["phot_g_mean_mag"])
            bp_mag = float(g["phot_bp_mean_mag"]) if g.get("phot_bp_mean_mag") is not None else float("nan")
            rp_mag = float(g["phot_rp_mean_mag"]) if g.get("phot_rp_mean_mag") is not None else float("nan")
            bp_rp = float(g["bp_rp"]) if g.get("bp_rp") is not None else (bp_mag - rp_mag)
            vmag_val = None
        else:
            ra16, dec16 = float(spec["ra_lit"]), float(spec["dec_lit"])
            ra00, dec00 = ra16, dec16
            pmra, pmdec = float(spec["pmra_lit"]), float(spec["pmdec_lit"])
            dist_pc = float(spec["dist_lit"])
            g_mag, bp_mag, rp_mag, bp_rp = float("nan"), float("nan"), float("nan"), float("nan")
            vmag_val = float(spec["vmag_lit"])
        within_10pc = dist_pc < 10.0

        tm_sql = (
            f"SELECT TOP 2 mainid, jmag, hmag, kmag, "
            f"DISTANCE(POINT('ICRS', raj2000, dej2000), POINT('ICRS', {ra00:.6f}, {dec00:.6f}))*3600.0 AS sep "
            f"FROM twomass.data "
            f"WHERE 1=CONTAINS(POINT('ICRS', raj2000, dej2000), CIRCLE('ICRS', {ra00:.6f}, {dec00:.6f}, 0.04)) "
            f"ORDER BY sep ASC"
        )
        tm_rows = tap_json(GAVO_TAP, {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "json", "QUERY": tm_sql})["data"]
        if not tm_rows or tm_rows[0][1] is None:
            raise RuntimeError(f"2MASS PSC lookup failed for {st}")
        twomass_id = str(tm_rows[0][0]).strip()
        j_mag = float(tm_rows[0][1])
        h_mag = float(tm_rows[0][2]) if tm_rows[0][2] is not None else float("nan")
        ks_mag = float(tm_rows[0][3]) if tm_rows[0][3] is not None else float("nan")

        nr_list = nasa_by_host.get(spec.get("nasa_hostname", ""), [])
        if not nr_list and gid is not None:
            nr_list = nasa_by_gid.get(gid, [])
        nr = nr_list[0] if nr_list else None
        n_exo = int(nr["sy_pnum"]) if nr and nr.get("sy_pnum") is not None else 0
        if spec["role"] == "CONTROL" and n_exo != 0:
            raise RuntimeError(f"CONTROL star {st} has n_exo={n_exo}!")
        has_transit = any(int(r.get("tran_flag") or 0) == 1 for r in nr_list) if nr_list else False

        teff_k = float(nr["st_teff"]) if (nr and nr.get("st_teff") is not None) else (float(gaia_by_id[gid]["teff_gspphot"]) if (gid and gaia_by_id[gid].get("teff_gspphot") is not None) else float(spec["teff_lit"]))
        mh_dex = float(nr["st_met"]) if (nr and nr.get("st_met") is not None) else (float(gaia_by_id[gid]["mh_gspphot"]) if (gid and gaia_by_id[gid].get("mh_gspphot") is not None) else float(spec["mh_lit"]))
        st_mass = float(nr["st_mass"]) if (nr and nr.get("st_mass") is not None) else float(spec["mass_lit"])
        rv_kms = float(gaia_by_id[gid]["radial_velocity"]) if (gid and gaia_by_id[gid].get("radial_velocity") is not None) else (float(nr["st_radv"]) if (nr and nr.get("st_radv") is not None) else float(spec["rv_lit"]))

        min_sep, nearest = min((sky_sep_arcsec(ra16, dec16, ec["ra_deg"], ec["dec_deg"]), ec["label"]) for ec in excl_coords)
        if (not spec["panchromatic_bridge"]) and min_sep < 5000.0:
            raise RuntimeError(f"Brand-new star {st} too close to prior {nearest}: {min_sep:.1f}\"")

        star_meta_map[st] = {
            "star": st, "gaia_source_id": str(gid) if gid is not None else "", "twomass_id": twomass_id,
            "ra_deg": ra16, "dec_deg": dec16, "dist_pc": dist_pc, "within_10pc": within_10pc,
            "g_mag": g_mag, "bp_mag": bp_mag, "rp_mag": rp_mag, "bp_rp": bp_rp, "vmag": vmag_val,
            "j_mag": j_mag, "h_mag": h_mag, "ks_mag": ks_mag, "teff_k": teff_k, "mh_dex": mh_dex,
            "st_mass": st_mass, "prior_rv_kms": rv_kms, "n_exoplanets": n_exo,
            "has_transiting_planet": has_transit, "min_prior_sep_arcsec": min_sep, "nearest_prior_target": nearest,
        }

        inst = spec["instrument"]
        obs_list: list[dict[str, Any]] = []
        if inst == "FUSE_FUV":
            rows = query_stsci_csv(FUSE_SEARCH, {"ra": f"{ra16:.5f}", "dec": f"{dec16:.5f}", "radius": "3.0", "action": "Search", "outputformat": "CSV", "max_records": "80"})
            allow = {a.upper() for a in spec["fuse_allow"]}
            seen_oid = set()
            for r in rows:
                oid = r["Data ID"].strip().lower()
                if not oid or oid in seen_oid or oid in excl_dp_ids:
                    continue
                tname = r.get("Target Name", "").strip().upper()
                if not any(tname.startswith(a) for a in allow):
                    continue
                t0_mjd = parse_stsci_time_to_mjd(r.get("Start Time", ""))
                expt = float(r.get("Exp Time") or 0.0)
                if t0_mjd is None or expt < 5.0:
                    continue
                ra_o, dec_o = parse_hms_dms(r["RA (J2000)"], r["Dec (J2000)"])
                seen_oid.add(oid)
                all_obs_ids_need_caom.append(oid)
                obs_list.append({
                    "obs_id": oid, "target_name_archive": r.get("Target Name", "").strip(),
                    "s_ra": ra_o, "s_dec": dec_o, "t_min": t0_mjd, "t_max": t0_mjd + max(expt, 60.0) / 86400.0,
                    "exptime": expt, "em_min_a": 905.0, "em_max_a": 1187.0, "em_res_power": 20000.0,
                    "obs_release_date": r.get("Release Date", "").strip()[:10],
                })
        elif inst == "HST_COS_FUV":
            rows = query_stsci_csv(HST_SEARCH, {"ra": f"{ra16:.5f}", "dec": f"{dec16:.5f}", "radius": "3.0", "sci_instrume": "COS", "sci_spec_1234": "G130M", "action": "Search", "outputformat": "CSV", "max_records": "120"})
            seen_oid = set()
            for r in rows:
                if r.get("Access", "").strip().upper() == "PRIVATE":
                    continue
                oid = r["Dataset"].strip().lower()
                if not oid or oid in seen_oid or oid in excl_dp_ids:
                    continue
                t0_mjd = parse_stsci_time_to_mjd(r.get("Start Time", ""))
                t1_mjd = parse_stsci_time_to_mjd(r.get("Stop Time", ""))
                expt = float(r.get("Exp Time") or 0.0)
                if t0_mjd is None or t1_mjd is None or expt < 5.0:
                    continue
                ra_o, dec_o = parse_hms_dms(r["RA (J2000)"], r["Dec (J2000)"])
                seen_oid.add(oid)
                all_obs_ids_need_caom.append(oid)
                obs_list.append({
                    "obs_id": oid, "target_name_archive": r.get("Target Name", "").strip(),
                    "s_ra": ra_o, "s_dec": dec_o, "t_min": t0_mjd, "t_max": max(t1_mjd, t0_mjd + expt / 86400.0),
                    "exptime": expt, "em_min_a": 1125.0, "em_max_a": 1450.0, "em_res_power": 18000.0,
                    "obs_release_date": r.get("Release Date", "").strip()[:10],
                })
        elif inst == "HST_STIS_NUV":
            gr = spec["stis_grat"]
            cw = spec["stis_cenwave"]
            rpow = 114000.0 if "E230H" in gr else 30000.0
            rows = query_stsci_csv(HST_SEARCH, {"ra": f"{ra16:.5f}", "dec": f"{dec16:.5f}", "radius": "3.0", "sci_instrume": "STIS", "sci_spec_1234": gr, "action": "Search", "outputformat": "CSV", "max_records": "200"})
            seen_oid = set()
            for r in rows:
                if r.get("Access", "").strip().upper() == "PRIVATE":
                    continue
                if not r.get("Central Wavelength", "").strip().startswith(cw):
                    continue
                oid = r["Dataset"].strip().lower()
                if not oid or oid in seen_oid or oid in excl_dp_ids:
                    continue
                t0_mjd = parse_stsci_time_to_mjd(r.get("Start Time", ""))
                t1_mjd = parse_stsci_time_to_mjd(r.get("Stop Time", ""))
                expt = float(r.get("Exp Time") or 0.0)
                if t0_mjd is None or t1_mjd is None or expt < 1.0:
                    continue
                ra_o, dec_o = parse_hms_dms(r["RA (J2000)"], r["Dec (J2000)"])
                seen_oid.add(oid)
                all_obs_ids_need_caom.append(oid)
                obs_list.append({
                    "obs_id": oid, "target_name_archive": r.get("Target Name", "").strip(),
                    "s_ra": ra_o, "s_dec": dec_o, "t_min": t0_mjd, "t_max": max(t1_mjd, t0_mjd + expt / 86400.0),
                    "exptime": expt, "em_min_a": 1605.0, "em_max_a": 3150.0, "em_res_power": rpow,
                    "obs_release_date": r.get("Release Date", "").strip()[:10],
                })
        raw_obs_by_star[st] = sorted(obs_list, key=lambda x: x["t_min"])

    # 3. Batch MAST CAOM obs_id -> numeric obsid (in chunks of 60 obs_ids)
    # Wait: pre-filter ALPCENA and COS/STIS non-orbital targets if obs list is large, or fetch all unique obs_ids
    unique_obs_ids = sorted(set(all_obs_ids_need_caom))
    print(f"  Resolving {len(unique_obs_ids)} unique MAST obs_ids in CAOM batches...", flush=True)
    caom_by_obsid: dict[str, dict[str, Any]] = {}
    for i in range(0, len(unique_obs_ids), 60):
        chunk = unique_obs_ids[i : i + 60]
        res = mast_invoke("Mast.Caom.Filtered", {
            "columns": "obsid,obs_id,t_min,t_max,dataRights",
            "filters": [{"paramName": "obs_id", "values": chunk}],
        })
        for row in res:
            if row.get("dataRights") == "PUBLIC":
                caom_by_obsid[row["obs_id"].strip().lower()] = row

    # For non-orbital stars with many obsids, keep evenly spaced subset before querying Mast.Caom.Products
    obs_to_fetch: dict[str, tuple[str, dict[str, Any]]] = {}  # obs_id -> (caom_obsid, obs_meta)
    for spec in TARGET_SPECS:
        st = spec["canonical_target"]
        inst = spec["instrument"]
        olist = [o for o in raw_obs_by_star[st] if o["obs_id"] in caom_by_obsid]
        # Attach exact CAOM t_min/t_max when present
        for o in olist:
            co = caom_by_obsid[o["obs_id"]]
            o["caom_obsid"] = str(co["obsid"])
            if co.get("t_min") is not None and co.get("t_max") is not None:
                o["t_min"] = float(co["t_min"])
                o["t_max"] = float(co["t_max"])
        if not spec["orbital_campaign"]:
            if inst in ("FUSE_FUV", "HST_STIS_NUV") and len(olist) > spec["n_target_exposures"] + 4:
                olist = [olist[int(round(j * (len(olist) - 1) / (spec["n_target_exposures"] + 3)))] for j in range(spec["n_target_exposures"] + 4)]
            elif inst == "HST_COS_FUV" and len(olist) > 6:
                olist = [olist[int(round(j * (len(olist) - 1) / 5.0))] for j in range(6)]
        raw_obs_by_star[st] = olist
        for o in olist:
            obs_to_fetch[o["obs_id"]] = (o["caom_obsid"], o)

    print(f"  Querying Mast.Caom.Products for {len(obs_to_fetch)} selected PUBLIC obsids...", flush=True)

    def fetch_products(item: tuple[str, tuple[str, dict[str, Any]]]) -> tuple[str, list[dict[str, Any]]]:
        oid, (c_oid, _) = item
        prods = mast_invoke("Mast.Caom.Products", {"obsid": c_oid, "pagesize": 2000})
        return oid, prods

    with ThreadPoolExecutor(max_workers=3) as ex:
        prod_map = dict(ex.map(fetch_products, list(obs_to_fetch.items())))

    # 4. Assemble candidate exposures per star & select locked cohort + orbital campaigns
    frozen_rows: list[dict[str, Any]] = []
    orbital_campaigns: dict[str, Any] = {}
    total_proj_bytes = 0
    brand_new_meta: list[tuple[dict[str, Any], dict[str, Any]]] = []

    for spec in TARGET_SPECS:
        st = spec["canonical_target"]
        inst = spec["instrument"]
        n_target = spec["n_target_exposures"]
        meta = star_meta_map[st]
        if not spec["panchromatic_bridge"]:
            brand_new_meta.append((spec, meta))

        cands: list[dict[str, Any]] = []
        seen_dps: set[str] = set()
        for o in raw_obs_by_star[st]:
            prods = prod_map[o["obs_id"]]
            if inst == "FUSE_FUV":
                matches = [
                    p for p in prods
                    if "00000all" in p.get("productFilename", "") and p.get("productFilename", "").endswith("fcal.fit.gz")
                    and int(p.get("size") or 0) >= 50_000
                ][:1]
                k_m = len(matches)
                t0, t1 = o["t_min"], o["t_max"]
                for mi, p in enumerate(matches):
                    fn = p["productFilename"].strip()
                    dp_id = fn[:-len("fcal.fit.gz")].rstrip("_")
                    if dp_id in seen_dps or dp_id in excl_dp_ids:
                        continue
                    seen_dps.add(dp_id)
                    mjd_mid = t0 + ((mi + 0.5) / max(1, k_m)) * max(1e-4, t1 - t0)
                    cands.append({
                        **o, "dp_id": dp_id, "mjd_obs": mjd_mid, "mjd_mid": mjd_mid,
                        "exptime": o["exptime"] / max(1, k_m),
                        "this_url": "https://mast.stsci.edu/api/v0.1/Download/file?uri=" + urllib.parse.quote(p["dataURI"], safe=":/"),
                        "this_bytes": int(p.get("size") or 500_000),
                        "aux_url": "", "aux_bytes": 0, "aux_category": "CALFUSE_8CHAN",
                        "bjd_mid_approx": mjd_to_bjd_est(mjd_mid, o["s_ra"], o["s_dec"]),
                    })
            else:
                x1ds = sorted([p for p in prods if p.get("productFilename", "").endswith("_x1d.fits")], key=lambda x: x["productFilename"])
                if inst == "HST_COS_FUV" and x1ds:
                    # Exclude internal Pt-Ne calibration lamp exposures (EXP-SWAVE / TARGNAME='WAVE' / FLUXCORR='OMIT')
                    asns = [p for p in prods if p.get("productFilename", "").endswith("_asn.fits") and p.get("dataURI")]
                    science_members: set[str] = set()
                    if asns:
                        try:
                            from astropy.io import fits as _fits
                            asn_url = "https://mast.stsci.edu/api/v0.1/Download/file?uri=" + urllib.parse.quote(asns[0]["dataURI"], safe=":/")
                            with urllib.request.urlopen(urllib.request.Request(asn_url, headers={"User-Agent": "SETI-D089/4.0"}), timeout=25) as resp_a:
                                raw_asn = resp_a.read()
                            with _fits.open(io.BytesIO(raw_asn), memmap=False) as h_asn:
                                if len(h_asn) > 1 and h_asn[1].data is not None and "MEMNAME" in h_asn[1].columns.names and "MEMTYPE" in h_asn[1].columns.names:
                                    for arow in h_asn[1].data:
                                        mname = str(arow["MEMNAME"]).strip().lower()
                                        mtype = str(arow["MEMTYPE"]).strip().upper()
                                        if mtype.startswith("EXP-") and ("WAVE" not in mtype):
                                            science_members.add(mname)
                        except Exception as exc_asn:
                            print(f"  [WARN] ASN fetch failed for {st}/{o['obs_id']}: {exc_asn}", flush=True)
                    x1ds = [
                        p for p in x1ds
                        if int(p.get("size") or 0) >= 100_000
                        and (not science_members or p["productFilename"][:-len("_x1d.fits")].strip().lower() in science_members)
                    ]
                k_m = len(x1ds)
                t0, t1 = o["t_min"], o["t_max"]
                if inst == "HST_STIS_NUV" and x1ds:
                    # One *_x1d.fits per STIS exposure dataset (prefer dataset-matching x1d)
                    x1ds = x1ds[:1]
                    k_m = 1
                for mi, p in enumerate(x1ds):
                    fn = p["productFilename"].strip()
                    dp_id = fn[:-len("_x1d.fits")]
                    if dp_id in seen_dps or dp_id in excl_dp_ids:
                        continue
                    seen_dps.add(dp_id)
                    mjd_mid = t0 + ((mi + 0.5) / max(1, k_m)) * max(1e-4, t1 - t0)
                    cands.append({
                        **o, "dp_id": dp_id, "mjd_obs": mjd_mid, "mjd_mid": mjd_mid,
                        "exptime": o["exptime"] / max(1, k_m) if k_m > 1 else o["exptime"],
                        "this_url": "https://mast.stsci.edu/api/v0.1/Download/file?uri=" + urllib.parse.quote(p["dataURI"], safe=":/"),
                        "this_bytes": int(p.get("size") or 2_000_000),
                        "aux_url": "", "aux_bytes": 0,
                        "aux_category": "CALCOS_X1D" if inst == "HST_COS_FUV" else "CALSTIS_NUV_X1D",
                        "bjd_mid_approx": mjd_to_bjd_est(mjd_mid, o["s_ra"], o["s_dec"]),
                    })

        cands = sorted(cands, key=lambda x: x["mjd_mid"])
        if len(cands) < n_target:
            raise RuntimeError(f"Star {st} ({inst}) yielded only {len(cands)} < {n_target} exposures!")

        if spec["orbital_campaign"]:
            hw = float(spec["half_phase_window"])
            ecc = float(spec["orb_e"])
            if spec.get("null_orbital"):
                # Search period around nominal value + candidate T0 to yield >=4 IN + >=4 OUT and max IN dv_span
                base_p = float(spec["orb_per_days"])
                best_choice = None
                for dp_mult in [1.0 + 0.0007 * k for k in range(-30, 31)]:
                    per_try = round(base_p * dp_mult, 6)
                    t0_seeds = [float(cands[j]["bjd_mid_approx"]) for j in range(0, len(cands), max(1, len(cands) // 12))]
                    if st == "LTT2050":
                        # Put T0 at midpoint of dense association ldab57010 so 4+ IN span [-0.14,+0.14] and ldab33030 falls OUT
                        dense = [c for c in cands if c["obs_id"] == "ldab57010"]
                        if len(dense) >= 4:
                            t0_seeds = [0.5 * (dense[0]["bjd_mid_approx"] + dense[-1]["bjd_mid_approx"])]
                    for t_try in t0_seeds:
                        in_c = [c for c in cands if abs(signed_phase(c["bjd_mid_approx"], t_try, per_try)) <= hw - 0.015]
                        out_c = [c for c in cands if abs(signed_phase(c["bjd_mid_approx"], t_try, per_try)) >= hw + 0.04]
                        if len(in_c) >= 4 and len(out_c) >= 4:
                            in_s = sorted(in_c, key=lambda x: signed_phase(x["bjd_mid_approx"], t_try, per_try))
                            ph_span = signed_phase(in_s[-1]["bjd_mid_approx"], t_try, per_try) - signed_phase(in_s[0]["bjd_mid_approx"], t_try, per_try)
                            if best_choice is None or ph_span > best_choice[0]:
                                best_choice = (ph_span, per_try, t_try, in_s, out_c)
                if best_choice is None:
                    raise RuntimeError(f"Could not construct balanced null orbital split for {st}")
                _, per, t0, in_cands, out_cands = best_choice
            else:
                per = float(spec["orb_per_days"])
                t0 = float(spec["orb_t0_bjd"])
                in_cands = sorted([c for c in cands if abs(signed_phase(c["bjd_mid_approx"], t0, per)) <= hw], key=lambda x: signed_phase(x["bjd_mid_approx"], t0, per))
                out_cands = [c for c in cands if abs(signed_phase(c["bjd_mid_approx"], t0, per)) > hw]
                if len(in_cands) < 4 or len(out_cands) < 4:
                    raise RuntimeError(f"Orbital campaign {st}: in={len(in_cands)}, out={len(out_cands)} (<4) with P={per}, hw={hw}")

            # Pick 4 IN spanning full phase width + 4 OUT time-spaced
            in_idxs = sorted({min(len(in_cands) - 1, int(round(i * (len(in_cands) - 1) / 3.0))) for i in range(4)})
            while len(in_idxs) < 4:
                for j in range(len(in_cands)):
                    if j not in in_idxs:
                        in_idxs.append(j)
                        if len(in_idxs) == 4:
                            break
            sel_in = [in_cands[j] for j in sorted(in_idxs)]
            sel_out = _select_time_spaced(out_cands, 4)
            selected = sorted(sel_in + sel_out, key=lambda x: x["mjd_mid"])

            kp_kms = compute_keplerian_kp_kms(meta["st_mass"], per, ecc)
            orb_exps = []
            in_rvs = []
            for rank, item in enumerate(selected, 1):
                bjd_m = float(item["bjd_mid_approx"])
                ph_s, orb_rv = compute_planet_orbital_rv_kms(bjd_m, t0, per, kp_kms)
                win = "IN_WINDOW" if abs(ph_s) <= hw else "OUT_OF_WINDOW"
                item["phase_window"] = win
                item["orbital_phase_signed"] = ph_s
                item["planet_orbital_rv_kms"] = orb_rv
                if win == "IN_WINDOW":
                    in_rvs.append(orb_rv)
                orb_exps.append({
                    "dp_id": item["dp_id"], "epoch_rank": rank, "bjd_mid_approx": round(bjd_m, 7),
                    "phase_window": win, "orbital_phase_signed": round(ph_s, 7), "planet_orbital_rv_kms": round(orb_rv, 5),
                })
            assert len(in_rvs) == 4 and len(orb_exps) == 8, f"Imbalanced orbital split on {st}: in={len(in_rvs)}"
            orbital_campaigns[st] = {
                "star": st, "common_name": spec["common_name"], "instrument": inst, "role": spec["role"],
                "subrole": spec["subrole"], "planet_name": spec["planet_name"], "transiting": bool(spec.get("transiting", False)),
                "window_mode": spec["window_mode"], "half_phase_window": hw,
                "st_mass_msun": round(meta["st_mass"], 4), "orbper_days": per, "t0_bjd": round(t0, 6), "ecc": ecc,
                "kp_kms": round(kp_kms, 4), "orbital_dv_span_kms": round(max(in_rvs) - min(in_rvs), 4),
                "n_in_window": 4, "n_out_of_window": 4, "exposures": orb_exps,
            }
        else:
            selected = _select_time_spaced(cands, n_target)
            for item in selected:
                item["phase_window"] = "MULTI_EPOCH"
                item["orbital_phase_signed"] = 0.0
                item["planet_orbital_rv_kms"] = 0.0

        for rank, item in enumerate(selected, 1):
            total_proj_bytes += item["this_bytes"] + item["aux_bytes"]
            frozen_rows.append({
                "phase_id": "D089", "instrument": inst, "canonical_target": st, "common_name": spec["common_name"],
                "role": spec["role"], "subrole": spec["subrole"],
                "panchromatic_bridge": str(spec["panchromatic_bridge"]), "radio_mm_id": spec["radio_mm_id"],
                "gaia_source_id": meta["gaia_source_id"], "twomass_id": meta["twomass_id"],
                "dp_id": item["dp_id"], "obs_id": item["obs_id"], "target_name_archive": item["target_name_archive"],
                "this_url": item["this_url"], "this_bytes": item["this_bytes"],
                "aux_url": item["aux_url"], "aux_bytes": item["aux_bytes"], "aux_category": item["aux_category"],
                "epoch_rank": rank, "phase_window": item["phase_window"],
                "orbital_phase_signed": f"{item['orbital_phase_signed']:.7f}",
                "planet_orbital_rv_kms": f"{item['planet_orbital_rv_kms']:.5f}",
                "s_ra": f"{item['s_ra']:.7f}", "s_dec": f"{item['s_dec']:.7f}",
                "mjd_obs": f"{item['mjd_obs']:.7f}", "mjd_mid": f"{item['mjd_mid']:.7f}",
                "t_exptime": f"{item['exptime']:.2f}", "em_min_a": f"{item['em_min_a']:.1f}",
                "em_max_a": f"{item['em_max_a']:.1f}", "em_res_power": f"{item['em_res_power']:.1f}",
                "obs_release_date": item["obs_release_date"], "dist_pc": f"{meta['dist_pc']:.6f}",
                "within_10pc": str(meta["within_10pc"]),
                "phot_g_mag": "" if math.isnan(meta["g_mag"]) else f"{meta['g_mag']:.5f}",
                "phot_bp_mag": "" if math.isnan(meta["bp_mag"]) else f"{meta['bp_mag']:.5f}",
                "phot_rp_mag": "" if math.isnan(meta["rp_mag"]) else f"{meta['rp_mag']:.5f}",
                "bp_rp": "" if math.isnan(meta["bp_rp"]) else f"{meta['bp_rp']:.5f}",
                "vmag": "" if meta["vmag"] is None else f"{meta['vmag']:.5f}",
                "j_mag": f"{meta['j_mag']:.4f}",
                "h_mag": "" if math.isnan(meta["h_mag"]) else f"{meta['h_mag']:.4f}",
                "ks_mag": "" if math.isnan(meta["ks_mag"]) else f"{meta['ks_mag']:.4f}",
                "teff_k": f"{meta['teff_k']:.1f}", "mh_dex": f"{meta['mh_dex']:.4f}",
                "stellar_mass_msun": f"{meta['st_mass']:.4f}", "prior_rv_kms": f"{meta['prior_rv_kms']:.5f}",
                "n_exoplanets": meta["n_exoplanets"], "has_transiting_planet": str(meta["has_transiting_planet"]),
                "min_prior_sep_arcsec": f"{meta['min_prior_sep_arcsec']:.2f}",
            })

    # 5. Integrity assertions
    proj_gib = total_proj_bytes / (1024.0**3)
    assert proj_gib < MAX_PROJ_DOWNLOAD_GIB, f"Projected download {proj_gib:.3f} GiB >= {MAX_PROJ_DOWNLOAD_GIB}"
    assert len(frozen_rows) == 192, f"Expected 192 exposures, got {len(frozen_rows)}"
    assert len({r["dp_id"] for r in frozen_rows}) == 192, "Duplicate dp_id detected!"
    assert len(brand_new_meta) == 30, f"Expected 30 brand-new stars, got {len(brand_new_meta)}"
    n_new_10pc = sum(1 for _, m in brand_new_meta if m["within_10pc"])
    assert n_new_10pc == 4, f"Expected 4 brand-new <10pc stars, got {n_new_10pc}"
    assert len(orbital_campaigns) == 10, f"Expected 10 orbital campaigns, got {len(orbital_campaigns)}"
    n_wide_dv = sum(1 for c in orbital_campaigns.values() if c["orbital_dv_span_kms"] >= 30.0)
    assert n_wide_dv >= 3, f"Expected >=3 campaigns with dv_span >= 30 km/s, got {n_wide_dv}"

    min_intra = min(
        sky_sep_arcsec(brand_new_meta[i][1]["ra_deg"], brand_new_meta[i][1]["dec_deg"], brand_new_meta[j][1]["ra_deg"], brand_new_meta[j][1]["dec_deg"])
        for i in range(len(brand_new_meta)) for j in range(i + 1, len(brand_new_meta))
    )
    assert min_intra >= 300.0, f"Intra-D089 separation {min_intra:.1f}\" < 300\""
    overlap_cnt = len({r["dp_id"] for r in frozen_rows} & excl_dp_ids)
    assert overlap_cnt == 0, f"Overlap with excluded dp_ids: {overlap_cnt}"

    # Write FROZEN_COHORT_D089.csv
    with (WS / "FROZEN_COHORT_D089.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(frozen_rows[0].keys()))
        w.writeheader()
        w.writerows(frozen_rows)

    # Write ORBITAL_CAMPAIGNS_AND_KINEMATICS.json
    orb_doc = {
        "schema": "SPACE_LYMAN_V4_0_ORBITAL_CAMPAIGNS",
        "phase_id": "D089",
        "instruments": ["FUSE_FUV", "HST_COS_FUV", "HST_STIS_NUV"],
        "n_campaigns": len(orbital_campaigns),
        "n_science_orbital_campaigns": sum(1 for c in orbital_campaigns.values() if c["role"] == "SCIENCE"),
        "n_control_null_campaigns": sum(1 for c in orbital_campaigns.values() if c["role"] == "CONTROL"),
        "campaigns": orbital_campaigns,
    }
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_doc, indent=2) + "\n", encoding="utf-8")

    # Write PRIOR_EXCLUSION_VERIFICATION.json
    star_sep_ver = [
        {
            "canonical_target": s["canonical_target"], "common_name": s["common_name"], "instrument": s["instrument"],
            "role": s["role"], "panchromatic_bridge": s["panchromatic_bridge"],
            "dist_pc": round(star_meta_map[s["canonical_target"]]["dist_pc"], 5),
            "within_10pc": star_meta_map[s["canonical_target"]]["within_10pc"],
            "ra_deg": round(star_meta_map[s["canonical_target"]]["ra_deg"], 6),
            "dec_deg": round(star_meta_map[s["canonical_target"]]["dec_deg"], 6),
            "nearest_prior_target": star_meta_map[s["canonical_target"]]["nearest_prior_target"],
            "min_sky_separation_arcsec": round(star_meta_map[s["canonical_target"]]["min_prior_sep_arcsec"], 2),
            "status": "INTENTIONAL_PANCHROMATIC_BRIDGE" if s["panchromatic_bridge"] else "VERIFIED_BRAND_NEW_STAR",
        }
        for s in TARGET_SPECS
    ]
    pe_doc = {
        "schema": "D089_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D089",
        "verified_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prior_phases_covered": "C001-C037 + D001-D088",
        "format_check_excluded_targets": pe_d88["format_check_excluded_targets"] + [fc["label"] for fc in D089_FORMAT_CHECKS],
        "format_check_excluded_dp_ids": pe_d88["format_check_excluded_dp_ids"] + [d for fc in D089_FORMAT_CHECKS for d in fc["dp_ids"]],
        "n_prior_excluded_coords": len(excl_coords),
        "n_prior_excluded_dp_ids": len(excl_dp_ids),
        "d089_total_stars": len(TARGET_SPECS),
        "d089_brand_new_unique_stars": len(brand_new_meta),
        "d089_panchromatic_bridge_stars": sum(1 for s in TARGET_SPECS if s["panchromatic_bridge"]),
        "d089_brand_new_within_10pc": n_new_10pc,
        "d089_total_exposures": len(frozen_rows),
        "d089_projected_download_bytes": total_proj_bytes,
        "d089_projected_download_gib": round(proj_gib, 4),
        "d089_dp_id_overlap_count": overlap_cnt,
        "min_brand_new_sky_separation_arcsec": round(min(m["min_prior_sep_arcsec"] for _, m in brand_new_meta), 2),
        "min_intra_d089_brand_new_separation_arcsec": round(min_intra, 2),
        "star_separation_verification": star_sep_ver,
        "excluded_dp_ids": sorted(excl_dp_ids),
        "excluded_targets_coordinate_registry": excl_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pe_doc, indent=2) + "\n", encoding="utf-8")

    # Write PRIOR_V3_PHASES_SNAPSHOT.json from canonical Companion Archive N (D088)
    arch_n = ROOT / "archives" / "SETI_D088_V3_9_NORTHERN_RADIO23_AND_ALLSKY_COMB_V4_1_RESULTS_2026-11-18.zip"
    assert hashlib.sha256(arch_n.read_bytes()).hexdigest() == "c0210250b925df3bebb1710c2bf7333a64ed767ebdc1f38a496d6a9454f7d45d", "Archive N SHA-256 mismatch!"
    d88_prefix = "work_radio23_allsky_20261118_d088_v3_9_northern_and_comb_v4_1"
    with zipfile.ZipFile(arch_n, "r") as zf:
        d88_sum = json.loads(zf.read(f"{d88_prefix}/results/SUMMARY.json").decode("utf-8"))
        d88_snap = json.loads(zf.read(f"{d88_prefix}/PRIOR_V3_PHASES_SNAPSHOT.json").decode("utf-8"))
        unified_220 = list(csv.DictReader(zf.read(f"{d88_prefix}/results/UNIFIED_PANCHROMATIC_V3_SYNTHESIS_220STARS.csv").decode("utf-8").splitlines()))
        bridge_21 = list(csv.DictReader(zf.read(f"{d88_prefix}/results/PANCHROMATIC_BRIDGE_21STARS.csv").decode("utf-8").splitlines()))
        allsky_unified = list(csv.DictReader(zf.read(f"{d88_prefix}/results/ALLSKY_COMB_V4_1_UNIFIED_D079_D088.csv").decode("utf-8").splitlines()))
        allsky_cands = list(csv.DictReader(zf.read(f"{d88_prefix}/results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D088.csv").decode("utf-8").splitlines()))

    prior_new_bridge_ul: list[dict[str, Any]] = []
    bridge_sources = [
        ("D083", "THERMAL_KBAND_1p96_2p48um", D083_WS / "results" / "STAR_UPPER_LIMITS_162.csv", {"BETPIC"}, "wave_bary_vac_A", {"BETPIC": "beta Pictoris"}),
        ("D080", "OPTICAL_0p38_0p69um", D080_WS / "results" / "STAR_UPPER_LIMITS_186.csv", {"HD189733"}, "wave_bary_air_A", {"HD189733": "HD 189733"}),
        ("D081", "OPTICAL_0p38_0p78um", D081_WS / "results" / "STAR_UPPER_LIMITS_153.csv", {"55CNC", "GJ832"}, "wave_bary_air_A", {"55CNC": "55 Cnc", "GJ832": "GJ 832"}),
        ("D086", "OPTICAL_0p38_0p69um", D086_WS / "results" / "STAR_UPPER_LIMITS_D086.csv", {"GJ876"}, "wave_bary_air_A", {"GJ876": "IL Aqr (GJ 876)"}),
    ]
    for ph_b, reg_b, ul_p, st_set, wcol, cname_map in bridge_sources:
        with ul_p.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["star"] in st_set:
                    pw = r.get("p_beam_10m_w") or str(round(float(r["p_beam_10m_kw"]) * 1000.0, 5))
                    prior_new_bridge_ul.append({
                        "phase_id": ph_b, "spectral_regime": reg_b, "instrument": r["instrument"],
                        "star": r["star"], "common_name": r.get("common_name") or cname_map[r["star"]],
                        "dist_pc": r["dist_pc"], "band_id": r["band_id"], "wave_A": r[wcol],
                        "ew_lim_mA": r["ew_lim_mA"], "flux_lim_erg_cm2_s": r["flux_lim_erg_cm2_s"],
                        "l_iso_mw": r["l_iso_mw"], "p_beam_10m_kw": r["p_beam_10m_kw"], "p_beam_10m_w": pw,
                    })

    # Exact D079-D088 exposure provenance integration hours
    prior_hours = 0.0
    for ph_dir in sorted(AWS.glob("work_*")):
        for pf in ph_dir.glob("results/EXPOSURE_PROVENANCE_*.csv"):
            if "d089" in ph_dir.name:
                continue
            with pf.open(newline="", encoding="utf-8") as fh:
                rows_p = list(csv.DictReader(fh))
                hk = "t_exptime_s" if "t_exptime_s" in rows_p[0] else "exptime_s"
                prior_hours += sum(float(x[hk]) for x in rows_p) / 3600.0

    u_synth = d88_sum["unified_220star_panchromatic_v3_synthesis"]
    snap_doc = {
        "schema": "D089_PRIOR_V3_PHASES_SNAPSHOT",
        "prior_phases": "D079-D088",
        "prior_v3_unique_stars_count": int(u_synth["unique_stars_total"]),
        "prior_v3_within_10pc_count": int(u_synth["within_10pc_unique_stars"]),
        "prior_v3_total_exposures_count": int(u_synth["total_exposures_d079_d088"]),
        "prior_cumulative_integration_hours": round(prior_hours, 4),
        "prior_v3_calibration_trials_count": int(u_synth["total_calibration_trials_d079_d088"]),
        "prior_v2_false_alarms_eliminated_total": int(u_synth["v2_false_alarms_eliminated_total"]),
        "prior_cumulative_orbital_campaigns_count": int(u_synth["cumulative_orbital_campaigns"]),
        "d088_summary_headline": d88_sum,
        "d087_summary_headline": d88_snap["d087_summary_headline"],
        "d086_summary_headline": d88_snap["d086_summary_headline"],
        "d085_summary_headline": d88_snap["d085_summary_headline"],
        "d084_summary_headline": d88_snap["d084_summary_headline"],
        "d083_summary_headline": d88_snap["d083_summary_headline"],
        "d079_d082_headlines": d88_snap["d079_d082_headlines"],
        "unified_220star_rows": unified_220,
        "d088_bridge_21star_rows": bridge_21,
        "prior_new_bridge_upper_limits": prior_new_bridge_ul,
        "allsky_comb_unified_d079_d088": allsky_unified,
        "allsky_comb_candidates_d079_d088": allsky_cands,
    }
    (WS / "PRIOR_V3_PHASES_SNAPSHOT.json").write_text(json.dumps(snap_doc, indent=2) + "\n", encoding="utf-8")

    # Copy MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json cleanly (already 23/23 + 1 TESS)
    mm88 = json.loads((D088_WS / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").read_text(encoding="utf-8"))
    mm88["schema"] = "D089_MULTIMESSENGER_RADIO_TESS_SNAPSHOT"
    (WS / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").write_text(json.dumps(mm88, indent=2) + "\n", encoding="utf-8")

    print(
        f"DONE: {len(TARGET_SPECS)} stars ({len(brand_new_meta)} new [{n_new_10pc} <10pc] + "
        f"{pe_doc['d089_panchromatic_bridge_stars']} bridges), {len(frozen_rows)} exposures "
        f"({sum(1 for r in frozen_rows if r['instrument']=='FUSE_FUV')} FUSE + "
        f"{sum(1 for r in frozen_rows if r['instrument']=='HST_COS_FUV')} COS + "
        f"{sum(1 for r in frozen_rows if r['instrument']=='HST_STIS_NUV')} STIS_NUV), "
        f"{len(orbital_campaigns)} orbital ({n_wide_dv} with dv>=30), proj={proj_gib:.3f} GiB, "
        f"min_prior_sep={pe_doc['min_brand_new_sky_separation_arcsec']}\", prior_hours={prior_hours:.4f}h.",
        flush=True,
    )


if __name__ == "__main__":
    build()
