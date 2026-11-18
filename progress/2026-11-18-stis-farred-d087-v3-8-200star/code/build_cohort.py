#!/usr/bin/env python3
"""
Prospective Cohort Builder & Metadata Snapshotter for Phase D087
(SPACE_UV_STIS_AND_FARRED_V3_8).

Executes BEFORE any science FITS download (while inputs_d087_v3_8 does not exist)
and produces the 5 locked pre-ingestion metadata artifacts:
  1. FROZEN_COHORT_D087.csv (201 exposures across 33 stars: 10 HST_STIS, 10 UVES_RED, 13 ESPRESSO)
  2. ORBITAL_CAMPAIGNS_AND_KINEMATICS.json (10 campaigns: 3 null-controls + 7 exoplanet hosts)
  3. PRIOR_EXCLUSION_VERIFICATION.json (1,571+ excluded dp_ids, 215+ excluded coords incl. BD+28D4211)
  4. PRIOR_V3_PHASES_SNAPSHOT.json (D079-D086 offline synthesis snapshot: 175 stars, 13 bridges)
  5. MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json (23 radio + 1 TESS systems, 18 direct overlaps)
"""
from __future__ import annotations

import csv
import io
import json
import math
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from v3_8_detector import compute_keplerian_kp_kms, compute_planet_orbital_rv_kms

ROOT = Path(".")
AWS = ROOT / "analysis_workspace"
WS = AWS / "work_stis_farred_20261118_d087_v3_8_space_uv_and_200star"

D081_WS = AWS / "work_echelle_20261115_d081_v3_2_transit_kinematics_and_10pc_survey"
D084_WS = AWS / "work_northern_20261115_d084_v3_5_harpsn_carmenes_survey"
D086_WS = AWS / "work_uves_panchrom_20261117_d086_v3_7_nuv_and_comb_v4_1"

GAIA_TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
NASA_TAP = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
ESO_TAP = "https://archive.eso.org/tap_obs/sync"
ESO_DATALINK = "https://archive.eso.org/datalink/links"
MAST_API = "https://mast.stsci.edu/api/v0/invoke"
MAST_DL = "https://mast.stsci.edu/api/v0.1/Download/file"

OBS_RELEASE_CUTOFF_ISO = "2026-11-18T00:00:00Z"
OBS_RELEASE_CUTOFF_MJD = 61362.0  # 2026-11-18T00:00:00Z
MAX_PROJ_DOWNLOAD_GIB = 6.0

# Format-check single exposure inspected strictly to verify HST_STIS E140M CALSTIS headers/cols
BD28_FORMAT_CHECK = {
    "label": "BD+28D4211 (D087 HST_STIS format check)",
    "ra_deg": 327.796125,
    "dec_deg": 28.864389,
    "obs_id": "o45931020",
}


TARGET_SPECS: list[dict[str, Any]] = [
    # ==================== HST_STIS E140M (10 stars = 2 controls + 4 bridges + 4 brand-new science, 54 exp) ====================
    {
        "canonical_target": "HD142373",
        "common_name": "chi Her (HD 142373)",
        "instrument": "HST_STIS",
        "gaia_source_id": 1384195086792268800,
        "role": "CONTROL",
        "subrole": "NULL_FUV_SOLAR_ANALOG",
        "panchromatic_bridge": False,
        "n_exp": 4,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 5820.0,
        "mh_lit": -0.50,
        "mass_lit": 0.82,
        "rv_lit": -55.40,
    },
    {
        "canonical_target": "HD73752",
        "common_name": "HD 73752",
        "instrument": "HST_STIS",
        "gaia_source_id": 5702029029197580160,
        "role": "CONTROL",
        "subrole": "NULL_FUV_G_SUBGIANT",
        "panchromatic_bridge": False,
        "n_exp": 4,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 5700.0,
        "mh_lit": 0.35,
        "mass_lit": 1.18,
        "rv_lit": 43.80,
    },
    {
        "canonical_target": "PROXIMACEN",
        "common_name": "Proxima Centauri",
        "instrument": "HST_STIS",
        "gaia_source_id": 5853498713190525696,
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_FUV_K_BRIDGE_10PC",
        "panchromatic_bridge": True,
        "n_exp": 6,
        "radio_mm_id": "M05_M10_PROXIMA",
        "orbital_campaign": None,
        "teff_lit": 2992.0,
        "mh_lit": -0.07,
        "mass_lit": 0.122,
        "rv_lit": -21.70,
    },
    {
        "canonical_target": "ADLEO",
        "common_name": "AD Leo (GJ 388)",
        "instrument": "HST_STIS",
        "gaia_source_id": 625453654702751872,
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_FUV_OPT_BRIDGE_10PC",
        "panchromatic_bridge": True,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3455.0,
        "mh_lit": 0.05,
        "mass_lit": 0.42,
        "rv_lit": 12.40,
    },
    {
        "canonical_target": "AUMIC",
        "common_name": "AU Mic (GJ 803)",
        "instrument": "HST_STIS",
        "gaia_source_id": 6794047652729201024,
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_FUV_TRANSIT_ORBITAL_10PC",
        "panchromatic_bridge": True,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "AU Mic b",
            "orbper_days": 8.463446,
            "t0_bjd": 2458330.350878,
            "ecc": 0.07,
            "st_mass_msun": 0.635,
            "transiting": True,
        },
        "teff_lit": 3540.0,
        "mh_lit": 0.01,
        "mass_lit": 0.635,
        "rv_lit": -4.70,
    },
    {
        "canonical_target": "HD209458",
        "common_name": "HD 209458",
        "instrument": "HST_STIS",
        "gaia_source_id": 1779546757669063552,
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_FUV_TRANSIT_HOST_BRIDGE",
        "panchromatic_bridge": True,
        "n_exp": 4,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 6091.0,
        "mh_lit": 0.02,
        "mass_lit": 1.15,
        "rv_lit": -14.70,
    },
    {
        "canonical_target": "GJ754",
        "common_name": "GJ 754 (LP 1027-44)",
        "instrument": "HST_STIS",
        "gaia_source_id": 6663600360560306560,
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_FUV_10PC",
        "panchromatic_bridge": False,
        "n_exp": 4,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3085.0,
        "mh_lit": -0.10,
        "mass_lit": 0.17,
        "rv_lit": 8.00,
    },
    {
        "canonical_target": "HD1237",
        "common_name": "GJ 3021 (HD 1237)",
        "instrument": "HST_STIS",
        "gaia_source_id": 4634528720388462592,
        "role": "SCIENCE",
        "subrole": "EXOPLANET_HOST_FUV",
        "panchromatic_bridge": False,
        "n_exp": 4,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 5489.0,
        "mh_lit": 0.12,
        "mass_lit": 0.90,
        "rv_lit": -5.70,
    },
    {
        "canonical_target": "HD172555",
        "common_name": "HD 172555",
        "instrument": "HST_STIS",
        "gaia_source_id": 6438274350302427776,
        "role": "SCIENCE",
        "subrole": "YOUNG_A_STAR_FUV",
        "panchromatic_bridge": False,
        "n_exp": 6,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 7800.0,
        "mh_lit": 0.05,
        "mass_lit": 1.76,
        "rv_lit": 2.00,
    },
    {
        "canonical_target": "KELT9",
        "common_name": "KELT-9 (HD 195689)",
        "instrument": "HST_STIS",
        "gaia_source_id": 2064327278651198336,
        "role": "SCIENCE",
        "subrole": "ULTRA_HOT_JUPITER_FUV_HOST",
        "panchromatic_bridge": False,
        "n_exp": 6,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 9270.0,
        "mh_lit": 0.07,
        "mass_lit": 2.32,
        "rv_lit": -19.80,
    },

    # ==================== UVES_RED 0.5655-1.0425 um (10 stars = 1 control + 4 bridges + 5 brand-new science, 55 exp) ====================
    {
        "canonical_target": "GJ105B",
        "common_name": "GJ 105 B (BX Cet)",
        "instrument": "UVES_RED",
        "gaia_source_id": 18565464288396416,
        "role": "CONTROL",
        "subrole": "NULL_CONTROL_10PC_FARRED",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3284.0,
        "mh_lit": -0.12,
        "mass_lit": 0.25,
        "rv_lit": 25.70,
    },
    {
        "canonical_target": "HD20807",
        "common_name": "zet02 Ret (HD 20807)",
        "instrument": "UVES_RED",
        "gaia_source_id": 4722135642226902656,
        "role": "SCIENCE",
        "subrole": "SOLAR_ANALOG_FARRED",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 5840.0,
        "mh_lit": -0.23,
        "mass_lit": 0.96,
        "rv_lit": 11.94,
    },
    {
        "canonical_target": "EPSERI",
        "common_name": "eps Eri",
        "instrument": "UVES_RED",
        "gaia_source_id": 5164707970261890560,
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_NUV_FARRED_NIR_BRIDGE_10PC",
        "panchromatic_bridge": True,
        "n_exp": 6,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 5020.4,
        "mh_lit": -0.13,
        "mass_lit": 0.82,
        "rv_lit": 16.43,
    },
    {
        "canonical_target": "GJ1061",
        "common_name": "GJ 1061",
        "instrument": "UVES_RED",
        "gaia_source_id": 4848140361962951552,
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_OPT_FARRED_BRIDGE_10PC",
        "panchromatic_bridge": True,
        "n_exp": 6,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 2953.0,
        "mh_lit": -0.08,
        "mass_lit": 0.12,
        "rv_lit": 1.49,
    },
    {
        "canonical_target": "GJ285",
        "common_name": "YZ CMi (GJ 285)",
        "instrument": "UVES_RED",
        "gaia_source_id": 3136952686035250688,
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_NUV_FARRED_KBAND_BRIDGE_10PC",
        "panchromatic_bridge": True,
        "n_exp": 6,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3099.0,
        "mh_lit": 0.00,
        "mass_lit": 0.32,
        "rv_lit": 25.72,
    },
    {
        "canonical_target": "GJ729",
        "common_name": "V1216 Sgr (GJ 729)",
        "instrument": "UVES_RED",
        "gaia_source_id": 4075141768785646848,
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_OPT_FARRED_BRIDGE_10PC",
        "panchromatic_bridge": True,
        "n_exp": 6,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3117.4,
        "mh_lit": -0.20,
        "mass_lit": 0.17,
        "rv_lit": -11.12,
    },
    {
        "canonical_target": "GJ65A",
        "common_name": "BL Cet (GJ 65 A)",
        "instrument": "UVES_RED",
        "gaia_source_id": 5140693571158946048,
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_FARRED_10PC",
        "panchromatic_bridge": False,
        "n_exp": 6,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 2910.0,
        "mh_lit": -0.10,
        "mass_lit": 0.12,
        "rv_lit": 29.00,
    },
    {
        "canonical_target": "GJ1224",
        "common_name": "GJ 1224",
        "instrument": "UVES_RED",
        "gaia_source_id": 4145870293808914688,
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_FARRED_10PC",
        "panchromatic_bridge": False,
        "n_exp": 4,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3040.0,
        "mh_lit": -0.10,
        "mass_lit": 0.14,
        "rv_lit": -32.50,
    },
    {
        "canonical_target": "GJ799A",
        "common_name": "AT Mic N (GJ 799 A)",
        "instrument": "UVES_RED",
        "gaia_source_id": 6792436799477051904,
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_FARRED_10PC",
        "panchromatic_bridge": False,
        "n_exp": 6,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3160.0,
        "mh_lit": 0.00,
        "mass_lit": 0.22,
        "rv_lit": -4.00,
    },
    {
        "canonical_target": "HD190007",
        "common_name": "HD 190007",
        "instrument": "UVES_RED",
        "gaia_source_id": 4247023886053586304,
        "role": "SCIENCE",
        "subrole": "EXOPLANET_HOST_FARRED",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 4610.0,
        "mh_lit": 0.16,
        "mass_lit": 0.77,
        "rv_lit": -30.30,
    },

    # ==================== ESPRESSO HR/UHR (13 brand-new stars = 3 null-orbital controls + 10 science incl. 6 orbital hosts, 92 exp) ====================
    {
        "canonical_target": "41ARA",
        "common_name": "41 Ara (HD 156274)",
        "instrument": "ESPRESSO",
        "gaia_source_id": 5951165616611763456,
        "role": "CONTROL",
        "subrole": "NULL_ORBITAL_CONTROL_10PC",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "Null Control (synthetic P=2.1873d)",
            "orbper_days": 2.1873,
            "t0_bjd": None,
            "t0_mode": "first",
            "ecc": 0.0,
            "st_mass_msun": 0.79,
            "transiting": False,
        },
        "teff_lit": 5280.0,
        "mh_lit": -0.30,
        "mass_lit": 0.79,
        "rv_lit": 22.90,
    },
    {
        "canonical_target": "HD100623",
        "common_name": "HD 100623",
        "instrument": "ESPRESSO",
        "gaia_source_id": 3478127463341507072,
        "role": "CONTROL",
        "subrole": "NULL_ORBITAL_CONTROL_10PC",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "Null Control (synthetic P=2.6519d)",
            "orbper_days": 2.6519,
            "t0_bjd": None,
            "t0_mode": "first",
            "ecc": 0.0,
            "st_mass_msun": 0.78,
            "transiting": False,
        },
        "teff_lit": 5175.0,
        "mh_lit": -0.42,
        "mass_lit": 0.78,
        "rv_lit": -22.20,
    },
    {
        "canonical_target": "G16028",
        "common_name": "G 160-28 (PM J03335+0246)",
        "instrument": "ESPRESSO",
        "gaia_source_id": 3243715604392800512,
        "role": "CONTROL",
        "subrole": "NULL_ORBITAL_CONTROL_10PC",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "Null Control (synthetic P=2.4137d)",
            "orbper_days": 2.4137,
            "t0_bjd": None,
            "t0_mode": "mid",
            "ecc": 0.0,
            "st_mass_msun": 0.26,
            "transiting": False,
        },
        "teff_lit": 3260.0,
        "mh_lit": 0.00,
        "mass_lit": 0.26,
        "rv_lit": 31.00,
    },
    {
        "canonical_target": "L47142",
        "common_name": "L 471-42 (WT 308)",
        "instrument": "ESPRESSO",
        "gaia_source_id": 6153483658836320384,
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3320.0,
        "mh_lit": -0.15,
        "mass_lit": 0.35,
        "rv_lit": -5.00,
    },
    {
        "canonical_target": "HD165222",
        "common_name": "HD 165222 (GJ 701)",
        "instrument": "ESPRESSO",
        "gaia_source_id": 4177731838628465408,
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3600.0,
        "mh_lit": -0.25,
        "mass_lit": 0.45,
        "rv_lit": 32.50,
    },
    {
        "canonical_target": "L39968",
        "common_name": "L 399-68 (GJ 452)",
        "instrument": "ESPRESSO",
        "gaia_source_id": 6133474952391837824,
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3250.0,
        "mh_lit": -0.15,
        "mass_lit": 0.30,
        "rv_lit": 10.00,
    },
    {
        "canonical_target": "PMJ11413",
        "common_name": "PM J11413-2900 (LP 907-23)",
        "instrument": "ESPRESSO",
        "gaia_source_id": 3464485826872541440,
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3350.0,
        "mh_lit": -0.10,
        "mass_lit": 0.35,
        "rv_lit": 12.00,
    },
    {
        "canonical_target": "CDCET",
        "common_name": "CD Cet (GJ 1057)",
        "instrument": "ESPRESSO",
        "gaia_source_id": 3179036008830848,
        "role": "SCIENCE",
        "subrole": "EXOPLANET_ORBITAL_10PC",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "CD Cet b",
            "orbper_days": 2.2907,
            "t0_bjd": 2458804.489,
            "ecc": 0.0,
            "st_mass_msun": 0.161,
            "transiting": False,
        },
        "teff_lit": 3130.0,
        "mh_lit": 0.13,
        "mass_lit": 0.161,
        "rv_lit": -29.10,
    },
    {
        "canonical_target": "GJ3138",
        "common_name": "GJ 3138 (BD-17 400)",
        "instrument": "ESPRESSO",
        "gaia_source_id": 5144740907820131840,
        "role": "SCIENCE",
        "subrole": "EXOPLANET_ORBITAL_UHR_HR",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "GJ 3138 b",
            "orbper_days": 1.22003,
            "t0_bjd": None,
            "t0_mode": "first",
            "ecc": 0.19,
            "st_mass_msun": 0.681,
            "transiting": False,
        },
        "teff_lit": 3717.0,
        "mh_lit": -0.30,
        "mass_lit": 0.681,
        "rv_lit": 13.50,
    },
    {
        "canonical_target": "HD40307",
        "common_name": "HD 40307",
        "instrument": "ESPRESSO",
        "gaia_source_id": 4758877919212831104,
        "role": "SCIENCE",
        "subrole": "MULTI_PLANET_ORBITAL_5P",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "HD 40307 b",
            "orbper_days": 4.3123,
            "t0_bjd": None,
            "t0_mode": "last",
            "ecc": 0.20,
            "st_mass_msun": 0.77,
            "transiting": False,
        },
        "teff_lit": 4956.0,
        "mh_lit": -0.31,
        "mass_lit": 0.77,
        "rv_lit": 31.30,
    },
    {
        "canonical_target": "TOI700",
        "common_name": "TOI-700",
        "instrument": "ESPRESSO",
        "gaia_source_id": 5284517766615850752,
        "role": "SCIENCE",
        "subrole": "TRANSITING_ORBITAL_MULTI_4P",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "TOI-700 b",
            "orbper_days": 9.97722,
            "t0_bjd": 2458880.0994,
            "ecc": 0.032,
            "st_mass_msun": 0.417,
            "transiting": True,
        },
        "teff_lit": 3459.0,
        "mh_lit": -0.07,
        "mass_lit": 0.417,
        "rv_lit": 27.00,
    },
    {
        "canonical_target": "TOI178",
        "common_name": "TOI-178",
        "instrument": "ESPRESSO",
        "gaia_source_id": 2318295979126499200,
        "role": "SCIENCE",
        "subrole": "TRANSITING_ORBITAL_MULTI_6P",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "TOI-178 b",
            "orbper_days": 1.9145601,
            "t0_bjd": 2458931.1793,
            "ecc": 0.0,
            "st_mass_msun": 0.647,
            "transiting": True,
        },
        "teff_lit": 4316.0,
        "mh_lit": -0.23,
        "mass_lit": 0.647,
        "rv_lit": 57.00,
    },
    {
        "canonical_target": "K23",
        "common_name": "K2-3",
        "instrument": "ESPRESSO",
        "gaia_source_id": 3796690380302214272,
        "role": "SCIENCE",
        "subrole": "TRANSITING_ORBITAL_MULTI_3P",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "K2-3 b",
            "orbper_days": 10.0546535,
            "t0_bjd": 2457165.32947,
            "ecc": 0.107,
            "st_mass_msun": 0.549,
            "transiting": True,
        },
        "teff_lit": 3835.0,
        "mh_lit": -0.32,
        "mass_lit": 0.549,
        "rv_lit": 32.50,
    },
]


def sky_sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1 = math.radians(ra1), math.radians(dec1)
    r2, d2 = math.radians(ra2), math.radians(dec2)
    cos_t = max(-1.0, min(1.0, math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)))
    return math.degrees(math.acos(cos_t)) * 3600.0


def mjd_to_bjd_est(mjd_mid: float, ra_deg: float, dec_deg: float) -> float:
    jd = float(mjd_mid) + 2400000.5
    t_c = (jd - 2451545.0) / 36525.0
    g = math.radians((357.529 + 35999.050 * t_c) % 360.0)
    lam_sun = math.radians((280.466 + 36000.770 * t_c) % 360.0 + 1.915 * math.sin(g) + 0.020 * math.sin(2.0 * g))
    eps = math.radians(23.439)
    xs, ys, zs = math.cos(lam_sun), math.sin(lam_sun) * math.cos(eps), math.sin(lam_sun) * math.sin(eps)
    ra, dec = math.radians(ra_deg), math.radians(dec_deg)
    roemer_days = 499.00478 / 86400.0 * (
        xs * math.cos(dec) * math.cos(ra) + ys * math.cos(dec) * math.sin(ra) + zs * math.sin(dec)
    )
    return jd + roemer_days


def mjd_to_iso_utc(mjd_val: float) -> str:
    dt = datetime(1858, 11, 17, tzinfo=timezone.utc) + timedelta(days=float(mjd_val))
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def tap_csv(url: str, query: str, timeout: float = 45.0) -> list[dict[str, str]]:
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query}).encode()
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "SETI-D087-CohortBuilder/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        txt = resp.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(txt)))


def tap_nasa_json(query: str, timeout: float = 45.0) -> list[dict[str, Any]]:
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "json", "QUERY": query}).encode()
    req = urllib.request.Request(NASA_TAP, data=data, headers={"User-Agent": "SETI-D087-CohortBuilder/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def query_stis_candidates(ra_deg: float, dec_deg: float, excl_dp_ids: set[str]) -> list[dict[str, Any]]:
    payload = {
        "service": "Mast.Caom.Filtered.Position",
        "format": "json",
        "params": {
            "columns": "obs_id,target_name,s_ra,s_dec,t_min,t_max,t_exptime,instrument_name,filters,em_min,em_max,t_obs_release",
            "filters": [
                {"paramName": "obs_collection", "values": ["HST"]},
                {"paramName": "instrument_name", "values": ["STIS/FUV-MAMA", "STIS"]},
                {"paramName": "filters", "values": ["E140M"]},
            ],
            "position": f"{ra_deg:.6f}, {dec_deg:.6f}, 0.08",
        },
    }
    data = urllib.parse.urlencode({"request": json.dumps(payload)}).encode("utf-8")
    req = urllib.request.Request(MAST_API, data=data, headers={"User-Agent": "SETI-D087-CohortBuilder/1.0"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        rows = json.loads(resp.read().decode("utf-8")).get("data", [])

    cands: list[dict[str, Any]] = []
    seen: set[str] = set()
    for er in rows:
        dp_id = str(er.get("obs_id", "")).strip()
        if not dp_id or dp_id in excl_dp_ids or dp_id in seen:
            continue
        t_rel = er.get("t_obs_release")
        if t_rel is None or float(t_rel) > OBS_RELEASE_CUTOFF_MJD:
            continue
        tmin, tmax = float(er["t_min"]), float(er["t_max"])
        if not (math.isfinite(tmin) and math.isfinite(tmax)):
            continue
        seen.add(dp_id)
        mjd_mid = 0.5 * (tmin + tmax)
        s_ra = float(er.get("s_ra") or ra_deg)
        s_dec = float(er.get("s_dec") or dec_deg)
        cands.append({
            "dp_id": dp_id,
            "target_name_archive": str(er.get("target_name", "")).strip(),
            "s_ra": s_ra,
            "s_dec": s_dec,
            "mjd_obs": tmin,
            "mjd_mid": mjd_mid,
            "exptime": float(er.get("t_exptime") or max(1.0, (tmax - tmin) * 86400.0)),
            "em_min_a": round(float(er.get("em_min") or 1.14e-7) * 1e10 if float(er.get("em_min") or 114.0) < 1e-4 else float(er.get("em_min") or 114.0) * 10.0, 2),
            "em_max_a": round(float(er.get("em_max") or 1.71e-7) * 1e10 if float(er.get("em_max") or 171.0) < 1e-4 else float(er.get("em_max") or 171.0) * 10.0, 2),
            "em_res_power": 45800.0,
            "snr_tap": 10.0,
            "obs_release_date": mjd_to_iso_utc(float(t_rel)),
            "bjd_mid_approx": mjd_to_bjd_est(mjd_mid, s_ra, s_dec),
        })
    cands.sort(key=lambda x: x["mjd_mid"])
    return cands


def probe_stis_head(dp_id: str) -> dict[str, Any] | None:
    url = f"{MAST_DL}?uri=mast:HST/product/{dp_id}_x1d.fits"
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "SETI-D087-CohortBuilder/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as hr:
            if hr.status != 200:
                return None
            cl = int(hr.headers.get("Content-Length") or 1756800)
            return {
                "this_url": url,
                "this_bytes": cl,
                "aux_url": "",
                "aux_bytes": 0,
                "aux_cat": "",
                "total_bytes": cl,
            }
    except Exception:
        return None


def parse_eso_datalink(dp_id: str, inst: str) -> dict[str, Any] | None:
    url = f"{ESO_DATALINK}?ID={urllib.parse.quote('ivo://eso.org/ID?' + dp_id, safe='')}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SETI-D087-CohortBuilder/1.0"}), timeout=25) as r:
            root = ET.fromstring(r.read())
    except Exception:
        return None
    ns = {"v": "http://www.ivoa.net/xml/VOTable/v1.3"}
    fields = [f.attrib.get("name", "") for f in root.findall(".//v:FIELD", ns)]
    this_url, this_bytes = "", 0
    aux_url, aux_bytes, aux_cat = "", 0, ""
    fallback_aux: tuple[str, int, str] | None = None

    for tr in root.findall(".//v:TR", ns):
        vals = [(td.text or "").strip() for td in tr.findall("v:TD", ns)]
        row = dict(zip(fields, vals))
        sem = row.get("semantics", "")
        aurl = row.get("access_url", "")
        if not aurl:
            continue
        cl = int(row.get("content_length") or 0)
        cat = row.get("eso_category", "")
        orig = row.get("eso_origfile", "")
        if sem == "#this":
            this_url, this_bytes = aurl, cl
        elif inst == "ESPRESSO" and sem == "#auxiliary" and cat == "ANCILLARY.SPECTRUM":
            if "SFLB" in orig and not aux_url:
                aux_url, aux_bytes, aux_cat = aurl, cl, cat
            elif fallback_aux is None and ("_B" in orig or "S1D" in orig):
                fallback_aux = (aurl, cl, cat)

    if inst == "ESPRESSO" and not aux_url and fallback_aux is not None:
        aux_url, aux_bytes, aux_cat = fallback_aux

    if not this_url or this_bytes <= 0:
        return None
    if inst == "ESPRESSO" and not aux_url:
        return None
    return {
        "this_url": this_url,
        "this_bytes": this_bytes,
        "aux_url": aux_url,
        "aux_bytes": aux_bytes,
        "aux_cat": aux_cat,
        "total_bytes": this_bytes + aux_bytes,
    }


def _select_time_spaced(valid_items: list[dict[str, Any]], n_target: int) -> list[dict[str, Any]]:
    if len(valid_items) <= n_target:
        return sorted(valid_items, key=lambda x: x["mjd_mid"])
    # Maximize time span + resolving power (e.g. pick highest R exposure first if available)
    by_r = sorted(valid_items, key=lambda x: (-round(x["em_res_power"], -2), x["mjd_mid"]))
    picked: list[dict[str, Any]] = []
    # Guarantee at least one exposure from the highest R tier when mixed (e.g. GJ3138 UHR)
    r_top = round(by_r[0]["em_res_power"], -2)
    r_bot = min(round(x["em_res_power"], -2) for x in valid_items)
    ordered = sorted(valid_items, key=lambda x: x["mjd_mid"])
    if r_top > r_bot:
        best_r = max((x for x in valid_items if round(x["em_res_power"], -2) == r_top), key=lambda x: x["exptime"])
        picked.append(best_r)
        rem = [x for x in ordered if x["dp_id"] != best_r["dp_id"]]
        need = n_target - 1
        if need > 0 and rem:
            idxs = sorted({min(len(rem) - 1, int(round(i * (len(rem) - 1) / max(1, need - 1)))) for i in range(need)})
            while len(idxs) < min(need, len(rem)):
                for j in range(len(rem)):
                    if j not in idxs:
                        idxs.append(j)
                        if len(idxs) == min(need, len(rem)):
                            break
            for j in sorted(idxs):
                picked.append(rem[j])
        return sorted(picked, key=lambda x: x["mjd_mid"])

    idxs = sorted({min(len(ordered) - 1, int(round(i * (len(ordered) - 1) / max(1, n_target - 1)))) for i in range(n_target)})
    while len(idxs) < n_target:
        for j in range(len(ordered)):
            if j not in idxs:
                idxs.append(j)
                if len(idxs) == n_target:
                    break
    return [ordered[j] for j in sorted(idxs)]


def select_candidates(cands: list[dict[str, Any]], n_target: int, inst: str) -> list[dict[str, Any]]:
    # For large lists, subsample evenly across time + high-exptime/highest-R candidates before network HEAD/DataLink
    pool = sorted(cands, key=lambda x: x["mjd_mid"])
    if len(pool) > 36:
        idxs = sorted({int(round(i * (len(pool) - 1) / 31.0)) for i in range(32)})
        pool = [pool[j] for j in idxs]
    elif len(pool) > n_target + 6 and inst == "HST_STIS":
        pool = sorted(pool, key=lambda x: (-x.get("em_res_power", 0.0), x["mjd_mid"]))

    valid: list[dict[str, Any]] = []
    # Deduplicate close exposures only when many are available so epochs spread across time
    dedup_pool: list[dict[str, Any]] = []
    if len(pool) > n_target * 2:
        for c in sorted(pool, key=lambda x: (-x["exptime"], x["mjd_mid"])):
            if all(abs(c["mjd_mid"] - p["mjd_mid"]) >= 0.04 for p in dedup_pool):
                dedup_pool.append(c)
        if len(dedup_pool) < n_target:
            seen_d = {x["dp_id"] for x in dedup_pool}
            for c in pool:
                if c["dp_id"] not in seen_d:
                    dedup_pool.append(c)
                    seen_d.add(c["dp_id"])
    else:
        dedup_pool = pool

    probe_fn = probe_stis_head if inst == "HST_STIS" else (lambda dp: parse_eso_datalink(dp, inst))
    for c in dedup_pool:
        dl = probe_fn(c["dp_id"])
        if dl is None:
            continue
        item = dict(c)
        item.update(dl)
        valid.append(item)
        if len(valid) >= max(n_target * 2, n_target + 4) and len(dedup_pool) <= 24:
            # Ensure we didn't miss high-R or late epochs
            pass

    if len(valid) < n_target:
        seen_v = {x["dp_id"] for x in valid}
        for c in cands:
            if c["dp_id"] in seen_v:
                continue
            dl = probe_fn(c["dp_id"])
            if dl is None:
                continue
            item = dict(c)
            item.update(dl)
            valid.append(item)
            if len(valid) >= n_target + 2:
                break

    if len(valid) < n_target:
        raise RuntimeError(f"Only {len(valid)}/{n_target} valid archive products found for {inst} target!")
    return _select_time_spaced(valid, n_target)


def select_orbital(cands: list[dict[str, Any]], n_target: int, inst: str) -> list[dict[str, Any]]:
    # Prioritize highest R (e.g. GJ3138 UHR R=190,000), then spread across time and exptime
    pool = sorted(cands, key=lambda x: (-round(x["em_res_power"], -2), -x["exptime"], x["mjd_mid"]))
    # Prefer distinct time blocks when many exposures are available
    ordered: list[dict[str, Any]] = []
    if len(pool) > 16:
        for c in pool:
            if all(abs(c["mjd_mid"] - p["mjd_mid"]) >= 0.05 for p in ordered):
                ordered.append(c)
        if len(ordered) < n_target + 4:
            seen_d = {x["dp_id"] for x in ordered}
            for c in pool:
                if c["dp_id"] not in seen_d:
                    ordered.append(c)
                    seen_d.add(c["dp_id"])
    else:
        ordered = pool

    probe_fn = probe_stis_head if inst == "HST_STIS" else (lambda dp: parse_eso_datalink(dp, inst))
    valid: list[dict[str, Any]] = []
    for c in ordered:
        dl = probe_fn(c["dp_id"])
        if dl is None:
            continue
        item = dict(c)
        item.update(dl)
        valid.append(item)
        if len(valid) >= n_target + 4 and round(valid[0]["em_res_power"], -2) >= round(c["em_res_power"], -2):
            break
    if len(valid) < n_target:
        seen_v = {x["dp_id"] for x in valid}
        for c in cands:
            if c["dp_id"] in seen_v:
                continue
            dl = probe_fn(c["dp_id"])
            if dl is None:
                continue
            item = dict(c)
            item.update(dl)
            valid.append(item)
            if len(valid) >= n_target:
                break
    if len(valid) < n_target:
        raise RuntimeError(f"Only {len(valid)}/{n_target} valid orbital exposures found for {inst}!")
    return _select_time_spaced(valid, n_target)


def build() -> None:
    WS.mkdir(parents=True, exist_ok=True)
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. Load prior exclusion registry from D086 and add BD+28D4211 format check
    d86_excl = json.loads((D086_WS / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    excl_dp_ids: set[str] = set(d86_excl["excluded_dp_ids"])
    excl_coords: list[dict[str, Any]] = list(d86_excl["excluded_targets_coordinate_registry"])
    with (D086_WS / "FROZEN_COHORT_D086.csv").open("r", encoding="utf-8", newline="") as f:
        d86_coord_added: set[str] = set()
        for r in csv.DictReader(f):
            excl_dp_ids.add(r["dp_id"])
            if r["canonical_target"] not in d86_coord_added and r["panchromatic_bridge"] != "True":
                excl_coords.append({
                    "label": f"{r['canonical_target']}(D086)",
                    "ra_deg": float(r["s_ra"]),
                    "dec_deg": float(r["s_dec"]),
                })
                d86_coord_added.add(r["canonical_target"])

    excl_dp_ids.add(BD28_FORMAT_CHECK["obs_id"])
    excl_coords.append({
        "label": BD28_FORMAT_CHECK["label"],
        "ra_deg": BD28_FORMAT_CHECK["ra_deg"],
        "dec_deg": BD28_FORMAT_CHECK["dec_deg"],
    })
    fmt_targets = list(d86_excl["format_check_excluded_targets"]) + [BD28_FORMAT_CHECK["label"]]
    fmt_dps = list(d86_excl["format_check_excluded_dp_ids"]) + [BD28_FORMAT_CHECK["obs_id"]]

    # 2. Batch Gaia DR3 + 2MASS + NASA pscomppars
    gids = [str(s["gaia_source_id"]) for s in TARGET_SPECS]
    gaia_q = (
        "SELECT source_id, ra, dec, parallax, pmra, pmdec, radial_velocity, "
        "phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag, bp_rp, teff_gspphot, mh_gspphot, ruwe "
        f"FROM gaiadr3.gaia_source WHERE source_id IN ({','.join(gids)})"
    )
    gaia_by_gid = {int(r["source_id"]): r for r in tap_csv(GAIA_TAP, gaia_q)}
    if len(gaia_by_gid) != len(TARGET_SPECS):
        raise RuntimeError(f"Expected {len(TARGET_SPECS)} Gaia DR3 rows, got {len(gaia_by_gid)}")

    # 2MASS crossmatch + J2000 cone fallback in gaiadr1.tmass_original_valid
    tm_best_q = (
        "SELECT xm.source_id, tm.designation, tm.j_m, tm.h_m, tm.ks_m "
        "FROM gaiadr3.tmass_psc_xsc_best_neighbour AS xm "
        "JOIN gaiadr3.tmass_psc_xsc_join AS xj ON xm.original_ext_source_id = xj.original_ext_source_id "
        "JOIN gaiadr1.tmass_original_valid AS tm ON xj.clean_tmass_psc_xsc_oid = tm.tmass_oid "
        f"WHERE xm.source_id IN ({','.join(gids)})"
    )
    tm_by_gid: dict[int, dict[str, str]] = {}
    try:
        for r in tap_csv(GAIA_TAP, tm_best_q):
            tm_by_gid[int(r["source_id"])] = r
    except Exception:
        pass

    # NASA Exoplanet Archive pscomppars
    nasa_rows = tap_nasa_json(
        "SELECT pl_name, hostname, gaia_dr3_id, ra, dec, sy_pnum, pl_orbper, pl_tranmid, "
        "pl_orbtper, pl_orbeccen, tran_flag, st_teff, st_met, st_mass "
        "FROM pscomppars"
    )
    nasa_by_gid: dict[int, dict[str, Any]] = {}
    for nr in nasa_rows:
        gtxt = str(nr.get("gaia_dr3_id") or "").strip()
        if "Gaia DR3 " in gtxt:
            try:
                ng = int(gtxt.replace("Gaia DR3", "").strip())
                nasa_by_gid.setdefault(ng, nr)
            except Exception:
                pass

    def query_target_metadata(spec: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        st = spec["canonical_target"]
        inst = spec["instrument"]
        gid = int(spec["gaia_source_id"])
        g = gaia_by_gid[gid]
        ra16 = float(g["ra"])
        dec16 = float(g["dec"])
        pmra = float(g["pmra"]) if g.get("pmra") else 0.0
        pmdec = float(g["pmdec"]) if g.get("pmdec") else 0.0
        dt_yr = 2000.0 - 2016.0
        cosd = max(0.05, math.cos(math.radians(dec16)))
        ra00 = ra16 + (pmra * dt_yr) / (3600000.0 * cosd)
        dec00 = dec16 + (pmdec * dt_yr) / 3600000.0

        tm_id, j_mag, h_mag, ks_mag = "", "", "", ""
        tmr = tm_by_gid.get(gid)
        if tmr and tmr.get("j_m"):
            tm_id = str(tmr.get("designation") or "")
            j_mag = round(float(tmr["j_m"]), 4)
            h_mag = round(float(tmr["h_m"]), 4) if tmr.get("h_m") else ""
            ks_mag = round(float(tmr["ks_m"]), 4) if tmr.get("ks_m") else ""
        else:
            q_cone = (
                "SELECT TOP 2 designation, j_m, h_m, ks_m, "
                f"DISTANCE(POINT('ICRS', ra, dec), POINT('ICRS', {ra00:.6f}, {dec00:.6f}))*3600.0 AS sep "
                "FROM gaiadr1.tmass_original_valid "
                f"WHERE 1=CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra00:.6f}, {dec00:.6f}, 0.015)) "
                "ORDER BY sep ASC"
            )
            crows = tap_csv(GAIA_TAP, q_cone, timeout=30.0)
            if crows and crows[0].get("j_m"):
                tm_id = str(crows[0].get("designation") or "")
                j_mag = round(float(crows[0]["j_m"]), 4)
                h_mag = round(float(crows[0]["h_m"]), 4) if crows[0].get("h_m") else ""
                ks_mag = round(float(crows[0]["ks_m"]), 4) if crows[0].get("ks_m") else ""

        if inst == "UVES_RED" and j_mag == "":
            raise RuntimeError(f"Missing required 2MASS J magnitude for UVES_RED target {st}")

        plx_mas = float(g["parallax"])
        dist_pc = 1000.0 / plx_mas

        nr = nasa_by_gid.get(gid)
        if nr is None:
            best_nr, best_s = None, 25.0
            for cand_nr in nasa_rows:
                if cand_nr.get("ra") is not None and cand_nr.get("dec") is not None:
                    s = sky_sep_arcsec(ra16, dec16, float(cand_nr["ra"]), float(cand_nr["dec"]))
                    if s < best_s:
                        best_s, best_nr = s, cand_nr
            nr = best_nr

        n_exo = int(nr["sy_pnum"]) if nr and nr.get("sy_pnum") is not None else 0
        if spec["role"] == "CONTROL" and n_exo != 0:
            raise RuntimeError(f"CONTROL star {st} has n_exo={n_exo} in pscomppars!")

        teff_k = float(nr["st_teff"]) if (nr and nr.get("st_teff")) else (
            float(g["teff_gspphot"]) if g.get("teff_gspphot") else float(spec["teff_lit"])
        )
        mh_dex = float(nr["st_met"]) if (nr and nr.get("st_met") is not None) else (
            float(g["mh_gspphot"]) if g.get("mh_gspphot") else float(spec["mh_lit"])
        )
        st_mass = float(nr["st_mass"]) if (nr and nr.get("st_mass")) else float(spec["mass_lit"])
        rv_kms = float(g["radial_velocity"]) if g.get("radial_velocity") else float(spec["rv_lit"])

        min_sep = 1e9
        nearest = ""
        for ec in excl_coords:
            s = sky_sep_arcsec(ra16, dec16, ec["ra_deg"], ec["dec_deg"])
            if s < min_sep:
                min_sep, nearest = s, ec["label"]
        if (not spec["panchromatic_bridge"]) and min_sep < 3000.0:
            raise RuntimeError(f"Brand-new star {st} too close to prior {nearest}: {min_sep:.1f}\"")

        # Archive queries per instrument
        if inst == "HST_STIS":
            exps = query_stis_candidates(ra16, dec16, excl_dp_ids)
        else:
            if inst == "UVES_RED":
                eso_inst = "UVES"
                extra = "AND em_min <= 0.67e-6 AND em_max >= 0.94e-6 AND em_res_power >= 38000 AND t_exptime >= 3.0"
                rad = 0.12
            else:
                eso_inst = "ESPRESSO"
                extra = "AND em_res_power >= 120000 AND t_exptime >= 30.0"
                rad = 0.12
            adql = (
                "SELECT dp_id, target_name, s_ra, s_dec, t_min, t_max, t_exptime, "
                "em_min, em_max, em_res_power, snr, obs_release_date "
                f"FROM ivoa.ObsCore WHERE instrument_name='{eso_inst}' AND dp_id LIKE 'ADP.%' "
                f"AND CONTAINS(POINT('ICRS', s_ra, s_dec), CIRCLE('ICRS', {ra16:.6f}, {dec16:.6f}, {rad}))=1 "
                f"{extra} AND obs_release_date <= '{OBS_RELEASE_CUTOFF_ISO}' ORDER BY t_min ASC"
            )
            erows = tap_csv(ESO_TAP, adql, timeout=45.0)
            exps = []
            seen_dp: set[str] = set()
            for er in erows:
                dp_id = er["dp_id"].strip()
                if dp_id in excl_dp_ids or dp_id in seen_dp:
                    continue
                seen_dp.add(dp_id)
                tmin, tmax = float(er["t_min"]), float(er["t_max"])
                mjd_mid = 0.5 * (tmin + tmax)
                exps.append({
                    "dp_id": dp_id,
                    "target_name_archive": er["target_name"].strip(),
                    "s_ra": float(er["s_ra"]),
                    "s_dec": float(er["s_dec"]),
                    "mjd_obs": tmin,
                    "mjd_mid": mjd_mid,
                    "exptime": float(er["t_exptime"]),
                    "em_min_a": round(float(er["em_min"]) * 1e10, 2),
                    "em_max_a": round(float(er["em_max"]) * 1e10, 2),
                    "em_res_power": float(er["em_res_power"]),
                    "snr_tap": float(er["snr"]) if er.get("snr") else 10.0,
                    "obs_release_date": er["obs_release_date"].strip(),
                    "bjd_mid_approx": mjd_to_bjd_est(mjd_mid, float(er["s_ra"]), float(er["s_dec"])),
                })

        meta = {
            "star": st,
            "gaia_source_id": str(gid),
            "ra_deg": ra16,
            "dec_deg": dec16,
            "parallax_mas": plx_mas,
            "dist_pc": dist_pc,
            "within_10pc": dist_pc < 10.0,
            "phot_g_mag": float(g["phot_g_mean_mag"]),
            "phot_bp_mag": float(g["phot_bp_mean_mag"]),
            "phot_rp_mag": float(g["phot_rp_mean_mag"]),
            "bp_rp": float(g["bp_rp"]) if g.get("bp_rp") else 1.5,
            "twomass_id": tm_id,
            "j_mag": j_mag,
            "h_mag": h_mag,
            "ks_mag": ks_mag,
            "teff_k": teff_k,
            "mh_dex": mh_dex,
            "stellar_mass_msun": st_mass,
            "ruwe": float(g["ruwe"]) if g.get("ruwe") else 1.05,
            "prior_rv_kms": rv_kms,
            "n_exoplanets": n_exo,
            "has_transiting_planet": bool((nr and int(nr.get("tran_flag") or 0) == 1) or (spec["orbital_campaign"] and spec["orbital_campaign"]["transiting"] and spec["role"] == "SCIENCE")),
            "min_prior_sep_arcsec": min_sep,
            "nearest_prior_label": nearest,
        }
        return meta, exps

    print("  Querying Gaia DR3 + 2MASS + NASA pscomppars + MAST/ESO across 33 D087 targets...", flush=True)
    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(query_target_metadata, TARGET_SPECS))

    cohort_rows: list[dict[str, Any]] = []
    orbital_campaigns: dict[str, Any] = {}
    star_sep_verif: list[dict[str, Any]] = []
    total_projected_bytes = 0

    for spec, (meta, cands) in zip(TARGET_SPECS, results):
        st = spec["canonical_target"]
        inst = spec["instrument"]
        orb = spec["orbital_campaign"]
        if orb is None:
            picks = select_candidates(cands, spec["n_exp"], inst)
            for rk, pk in enumerate(picks, start=1):
                pk["phase_window"] = "MULTI_EPOCH"
                pk["orbital_phase_signed"] = 0.0
                pk["planet_orbital_rv_kms"] = 0.0
                pk["epoch_rank"] = rk
        else:
            if orb["t0_bjd"] is not None:
                t0 = float(orb["t0_bjd"])
            elif orb.get("t0_mode") == "last":
                t0 = float(cands[-1]["bjd_mid_approx"])
            elif orb.get("t0_mode") == "mid":
                t0 = float(cands[len(cands) // 2]["bjd_mid_approx"])
            else:
                t0 = float(cands[0]["bjd_mid_approx"])
            kp_kms = compute_keplerian_kp_kms(orb["st_mass_msun"], orb["orbper_days"], orb["ecc"])
            in_cands, out_cands = [], []
            for c in cands:
                phi, dv_p = compute_planet_orbital_rv_kms(c["bjd_mid_approx"], t0, orb["orbper_days"], kp_kms)
                c["orbital_phase_signed"] = phi
                c["planet_orbital_rv_kms"] = dv_p
                if abs(phi) <= 0.16:
                    in_cands.append(c)
                elif 0.20 <= abs(phi) <= 0.48:
                    out_cands.append(c)
            p_in = select_orbital(in_cands, 4, inst)
            in_used = {p["dp_id"] for p in p_in}
            p_out = select_orbital([c for c in out_cands if c["dp_id"] not in in_used], 4, inst)
            for c in p_in:
                c["phase_window"] = "IN_WINDOW"
            for c in p_out:
                c["phase_window"] = "OUT_OF_WINDOW"
            picks = sorted(p_in + p_out, key=lambda x: x["mjd_mid"])
            for rk, pk in enumerate(picks, start=1):
                pk["epoch_rank"] = rk
            in_dvs = [c["planet_orbital_rv_kms"] for c in p_in]
            orbital_campaigns[st] = {
                "star": st,
                "common_name": spec["common_name"],
                "instrument": inst,
                "role": spec["role"],
                "subrole": spec["subrole"],
                "planet_name": orb["planet_name"],
                "transiting": bool(orb["transiting"]),
                "window_mode": "CONJUNCTION",
                "half_phase_window": 0.16,
                "st_mass_msun": round(float(orb["st_mass_msun"]), 6),
                "orbper_days": round(float(orb["orbper_days"]), 8),
                "t0_bjd": round(float(t0), 6),
                "ecc": round(float(orb["ecc"]), 6),
                "kp_kms": round(float(kp_kms), 4),
                "orbital_dv_span_kms": round(float(max(in_dvs) - min(in_dvs)), 4),
                "n_in_window": len(p_in),
                "n_out_of_window": len(p_out),
                "exposures": [
                    {
                        "dp_id": p["dp_id"],
                        "epoch_rank": p["epoch_rank"],
                        "bjd_mid_approx": round(float(p["bjd_mid_approx"]), 7),
                        "phase_window": p["phase_window"],
                        "orbital_phase_signed": round(float(p["orbital_phase_signed"]), 7),
                        "planet_orbital_rv_kms": round(float(p["planet_orbital_rv_kms"]), 5),
                    }
                    for p in picks
                ],
            }

        for p in picks:
            total_projected_bytes += int(p["total_bytes"])
            cohort_rows.append({
                "phase_id": "D087",
                "instrument": inst,
                "canonical_target": st,
                "common_name": spec["common_name"],
                "role": spec["role"],
                "subrole": spec["subrole"],
                "panchromatic_bridge": str(bool(spec["panchromatic_bridge"])),
                "radio_mm_id": spec["radio_mm_id"],
                "gaia_source_id": meta["gaia_source_id"],
                "twomass_id": meta["twomass_id"],
                "dp_id": p["dp_id"],
                "target_name_archive": p["target_name_archive"],
                "this_url": p["this_url"],
                "this_bytes": p["this_bytes"],
                "aux_url": p["aux_url"],
                "aux_bytes": p["aux_bytes"],
                "aux_category": p["aux_cat"],
                "epoch_rank": p["epoch_rank"],
                "phase_window": p["phase_window"],
                "orbital_phase_signed": round(float(p["orbital_phase_signed"]), 7),
                "planet_orbital_rv_kms": round(float(p["planet_orbital_rv_kms"]), 5),
                "s_ra": round(float(meta["ra_deg"]), 7),
                "s_dec": round(float(meta["dec_deg"]), 7),
                "mjd_obs": round(float(p["mjd_obs"]), 7),
                "mjd_mid": round(float(p["mjd_mid"]), 7),
                "t_exptime": round(float(p["exptime"]), 3),
                "em_min_a": p["em_min_a"],
                "em_max_a": p["em_max_a"],
                "em_res_power": round(float(p["em_res_power"]), 1),
                "obs_release_date": p["obs_release_date"],
                "dist_pc": round(float(meta["dist_pc"]), 6),
                "within_10pc": str(bool(meta["within_10pc"])),
                "phot_g_mag": round(float(meta["phot_g_mag"]), 5),
                "phot_bp_mag": round(float(meta["phot_bp_mag"]), 5),
                "phot_rp_mag": round(float(meta["phot_rp_mag"]), 5),
                "bp_rp": round(float(meta["bp_rp"]), 5),
                "j_mag": meta["j_mag"],
                "h_mag": meta["h_mag"],
                "ks_mag": meta["ks_mag"],
                "teff_k": round(float(meta["teff_k"]), 1),
                "mh_dex": round(float(meta["mh_dex"]), 4),
                "stellar_mass_msun": round(float(meta["stellar_mass_msun"]), 4),
                "prior_rv_kms": round(float(meta["prior_rv_kms"]), 5),
                "n_exoplanets": meta["n_exoplanets"],
                "has_transiting_planet": str(bool(meta["has_transiting_planet"])),
                "min_prior_sep_arcsec": round(float(meta["min_prior_sep_arcsec"]), 2),
            })

        star_sep_verif.append({
            "canonical_target": st,
            "common_name": spec["common_name"],
            "instrument": inst,
            "role": spec["role"],
            "panchromatic_bridge": bool(spec["panchromatic_bridge"]),
            "dist_pc": round(float(meta["dist_pc"]), 5),
            "within_10pc": bool(meta["within_10pc"]),
            "ra_deg": round(float(meta["ra_deg"]), 6),
            "dec_deg": round(float(meta["dec_deg"]), 6),
            "nearest_prior_target": meta["nearest_prior_label"],
            "min_sky_separation_arcsec": round(float(meta["min_prior_sep_arcsec"]), 2),
            "status": "VERIFIED_PANCHROMATIC_BRIDGE_STAR" if spec["panchromatic_bridge"] else "VERIFIED_BRAND_NEW_STAR",
        })

    new_verifs = [v for v in star_sep_verif if not v["panchromatic_bridge"]]
    min_intra_sep = 1e9
    for i, a in enumerate(new_verifs):
        for b in new_verifs[i + 1 :]:
            min_intra_sep = min(min_intra_sep, sky_sep_arcsec(a["ra_deg"], a["dec_deg"], b["ra_deg"], b["dec_deg"]))
    min_brand_new_sep = min(v["min_sky_separation_arcsec"] for v in new_verifs)
    new_10pc = sum(1 for v in new_verifs if v["within_10pc"])
    proj_gib = total_projected_bytes / (1024.0 ** 3)
    print(
        f"  Selected {len(cohort_rows)} exposures across {len(TARGET_SPECS)} stars "
        f"({len(new_verifs)} brand-new [{new_10pc} <10pc] + {len(star_sep_verif) - len(new_verifs)} bridge); "
        f"min_prior_sep={min_brand_new_sep:.2f}\", min_intra_sep={min_intra_sep:.2f}\"; "
        f"projected download={proj_gib:.3f} GiB",
        flush=True,
    )
    if proj_gib > MAX_PROJ_DOWNLOAD_GIB:
        raise RuntimeError(f"Projected download size {proj_gib:.3f} GiB exceeds {MAX_PROJ_DOWNLOAD_GIB:.1f} GiB limit!")

    # 3. Write FROZEN_COHORT_D087.csv
    with (WS / "FROZEN_COHORT_D087.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(cohort_rows[0].keys()))
        w.writeheader()
        w.writerows(cohort_rows)

    # 4. Write ORBITAL_CAMPAIGNS_AND_KINEMATICS.json
    orb_doc = {
        "schema": "PANCHROM_V3_8_ORBITAL_CAMPAIGNS",
        "phase_id": "D087",
        "instruments": ["HST_STIS", "ESPRESSO"],
        "n_campaigns": len(orbital_campaigns),
        "n_science_orbital_campaigns": sum(1 for c in orbital_campaigns.values() if c["role"] == "SCIENCE"),
        "n_control_null_campaigns": sum(1 for c in orbital_campaigns.values() if c["role"] == "CONTROL"),
        "campaigns": orbital_campaigns,
    }
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    # 5. Write PRIOR_EXCLUSION_VERIFICATION.json
    bridge_stars = {t["canonical_target"] for t in TARGET_SPECS if t["panchromatic_bridge"]}
    excl_doc = {
        "schema": "D087_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D087",
        "verified_utc": now_utc,
        "prior_phases_covered": "C001-C037 + D001-D086",
        "format_check_excluded_targets": fmt_targets,
        "format_check_excluded_dp_ids": fmt_dps,
        "n_prior_excluded_coords": len(excl_coords),
        "n_prior_excluded_dp_ids": len(excl_dp_ids),
        "d087_total_stars": len(TARGET_SPECS),
        "d087_brand_new_unique_stars": len(new_verifs),
        "d087_panchromatic_bridge_stars": len(bridge_stars),
        "d087_brand_new_within_10pc": new_10pc,
        "d087_total_exposures": len(cohort_rows),
        "d087_projected_download_bytes": total_projected_bytes,
        "d087_projected_download_gib": round(proj_gib, 4),
        "d087_dp_id_overlap_count": len({r["dp_id"] for r in cohort_rows} & excl_dp_ids),
        "min_brand_new_sky_separation_arcsec": round(min_brand_new_sep, 2),
        "min_intra_d087_brand_new_separation_arcsec": round(min_intra_sep, 2),
        "star_separation_verification": star_sep_verif,
        "excluded_dp_ids": sorted(excl_dp_ids),
        "excluded_targets_coordinate_registry": excl_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(excl_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    # 6. Snapshot prior V3.0-V3.7 synthesis (175 stars, 90 <10pc, 1,190 exp, 13 bridge stars) + prior ULs for 4 newly promoted bridges
    d86_summary = json.loads((D086_WS / "results" / "SUMMARY.json").read_text(encoding="utf-8"))
    d86_snap = json.loads((D086_WS / "PRIOR_V3_PHASES_SNAPSHOT.json").read_text(encoding="utf-8"))
    with (D086_WS / "results" / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_175STARS.csv").open("r", encoding="utf-8", newline="") as f:
        unified_175 = list(csv.DictReader(f))
    with (D086_WS / "results" / "PANCHROMATIC_BRIDGE_13STARS.csv").open("r", encoding="utf-8", newline="") as f:
        bridge_13 = list(csv.DictReader(f))

    prior_new_bridge_ul: list[dict[str, Any]] = []
    with (D081_WS / "results" / "STAR_UPPER_LIMITS_153.csv").open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["star"] == "HD209458":
                prior_new_bridge_ul.append({
                    "phase_id": "D081",
                    "spectral_regime": "OPTICAL_0p38_0p78um",
                    "phot_anchor_band": "GAIA_DR3_G",
                    "wave_bary_vac_A": r.get("wave_bary_air_A", ""),
                    **r,
                })
    with (D084_WS / "results" / "STAR_UPPER_LIMITS_189.csv").open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["star"] == "ADLEO":
                prior_new_bridge_ul.append({
                    "phase_id": "D084",
                    "spectral_regime": "OPTICAL_FARRED_0p52_1p06um",
                    "phot_anchor_band": r.get("radiometric_anchor", "GAIA_DR3_G"),
                    **r,
                })
    with (D086_WS / "results" / "STAR_UPPER_LIMITS_D086.csv").open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["star"] in ("GJ1061", "GJ729"):
                prior_new_bridge_ul.append({
                    "phase_id": "D086",
                    "spectral_regime": "OPTICAL_0p38_0p78um",
                    "phot_anchor_band": r.get("radiometric_anchor", "GAIA_DR3_G"),
                    "wave_bary_vac_A": r.get("wave_bary_air_A", ""),
                    **r,
                })

    prior_snap = {
        "schema": "D087_PRIOR_V3_PHASES_SNAPSHOT",
        "prior_phases": "D079-D086",
        "prior_v3_unique_stars_count": len(unified_175),
        "prior_v3_within_10pc_count": sum(1 for r in unified_175 if r["within_10pc"] == "True"),
        "prior_v3_total_exposures_count": sum(int(r["n_exposures_total"]) for r in unified_175),
        "prior_v3_calibration_trials_count": int(d86_summary["unified_175star_panchromatic_v3_synthesis"]["total_calibration_trials_d079_d086"]),
        "prior_v2_false_alarms_eliminated_total": int(d86_summary["unified_175star_panchromatic_v3_synthesis"]["v2_false_alarms_eliminated_total"]),
        "d086_summary_headline": d86_summary,
        "d085_summary_headline": d86_snap["d085_summary_headline"],
        "d084_summary_headline": d86_snap["d084_summary_headline"],
        "d083_summary_headline": d86_snap["d083_summary_headline"],
        "d079_d082_headlines": d86_snap["d079_d082_headlines"],
        "unified_175star_rows": unified_175,
        "d086_bridge_13star_rows": bridge_13,
        "prior_new_bridge_upper_limits": prior_new_bridge_ul,
    }
    (WS / "PRIOR_V3_PHASES_SNAPSHOT.json").write_text(json.dumps(prior_snap, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    # 7. Multi-messenger snapshot: verify unlinked radio/TESS systems remain distinct -> 18 direct overlaps, 206 total
    d86_mm = json.loads((D086_WS / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").read_text(encoding="utf-8"))
    ov_stars = sorted({s["canonical_v3_star"] for s in d86_mm["systems"] if s.get("canonical_v3_star")})
    mm_doc = dict(d86_mm)
    mm_doc["schema"] = "D087_MULTIMESSENGER_RADIO_TESS_SNAPSHOT"
    mm_doc["n_direct_echelle_multimessenger_overlap_stars"] = len(ov_stars)
    mm_doc["overlapping_v3_stars"] = ov_stars
    (WS / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").write_text(json.dumps(mm_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("[build_cohort] Wrote all 5 locked metadata & snapshot artifacts successfully.", flush=True)


if __name__ == "__main__":
    build()
