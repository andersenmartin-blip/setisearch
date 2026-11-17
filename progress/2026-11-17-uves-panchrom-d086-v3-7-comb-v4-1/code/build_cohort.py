#!/usr/bin/env python3
"""Metadata-only cohort builder & prospective exclusion verifier for Phase D086
(PANCHROM_NUV_OPT_V3_7_AND_COMB_V4_1).

Strict rules:
- Queries ONLY Gaia DR3 TAP, GAVO 2MASS TAP, NASA Exoplanet Archive TAP,
  ESO TAP (ivoa.ObsCore), and ESO DataLink VOTable XML metadata.
- ZERO science FITS/TAR downloads occur in this script.
- Locks all 31 targets (181 exposures: 55 UVES_NUV + 48 ESPRESSO + 78 HARPS),
  10 orbital campaigns (3 n_exo=0 controls + 7 planet hosts), and
  6 <10pc panchromatic bridges (PROXIMACEN, EPSERI, GJ285, YZCET, GJ1002, TAUCET).
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import math
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent
ANALYSIS_ROOT = WS.parent
D085_WS = ANALYSIS_ROOT / "work_spirou_20261116_d085_v3_6_yjhk_and_comb_v4"
D084_WS = ANALYSIS_ROOT / "work_northern_20261115_d084_v3_5_harpsn_carmenes_survey"
D082_WS = ANALYSIS_ROOT / "work_nirps_20261115_d082_v3_3_near_ir_and_panchromatic_survey"
D083_WS = ANALYSIS_ROOT / "work_crires_20261115_d083_v3_4_kband_and_100star_synthesis"

GAIA_TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
GAVO_TAP = "http://dc.g-vo.org/tap/sync"
NASA_TAP = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
ESO_TAP = "https://archive.eso.org/tap_obs/sync"
ESO_DATALINK = "https://archive.eso.org/datalink/links"

G_SI = 6.67430e-11
M_SUN_KG = 1.98847e30
DAY_S = 86400.0
OBS_RELEASE_CUTOFF = "2026-11-17T00:00:00Z"

# ---------------------------------------------------------------------------
# 31 Locked Targets across UVES_NUV (12), ESPRESSO (6), HARPS (13) = 181 exp
# ---------------------------------------------------------------------------
TARGET_SPECS: list[dict[str, Any]] = [
    # ==== UVES_NUV (12 stars, 55 exposures): 2 CONTROL + 3 BRIDGE + 7 NEW SCIENCE ====
    {
        "canonical_target": "HD155885",
        "common_name": "36 Oph A (HD 155885)",
        "instrument": "UVES_NUV",
        "eso_instrument": "UVES",
        "gaia_source_id": 4109030160308317312,
        "role": "CONTROL",
        "subrole": "NULL_CONTROL_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 5110.0,
        "mh_lit": -0.20,
        "mass_lit": 0.85,
        "rv_lit": -0.60,
    },
    {
        "canonical_target": "HD20630",
        "common_name": "kap01 Cet (HD 20630)",
        "instrument": "UVES_NUV",
        "eso_instrument": "UVES",
        "gaia_source_id": 3269362645115584640,
        "role": "CONTROL",
        "subrole": "NULL_CONTROL_10PC",
        "panchromatic_bridge": False,
        "n_exp": 4,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 5742.0,
        "mh_lit": 0.04,
        "mass_lit": 1.02,
        "rv_lit": 18.73,
    },
    {
        "canonical_target": "PROXIMACEN",
        "common_name": "Proxima Centauri",
        "instrument": "UVES_NUV",
        "eso_instrument": "UVES",
        "gaia_source_id": 5853498713190525696,
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_TRIREGIME_BRIDGE_10PC",
        "panchromatic_bridge": True,
        "n_exp": 5,
        "radio_mm_id": "M05_M10_PROXIMA",
        "orbital_campaign": None,
        "teff_lit": 2992.0,
        "mh_lit": 0.05,
        "mass_lit": 0.1221,
        "rv_lit": -21.94,
    },
    {
        "canonical_target": "EPSERI",
        "common_name": "eps Eri",
        "instrument": "UVES_NUV",
        "eso_instrument": "UVES",
        "gaia_source_id": 5164707970261890560,
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_NUV_NIR_BRIDGE_10PC",
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
        "canonical_target": "GJ285",
        "common_name": "YZ CMi (GJ 285)",
        "instrument": "UVES_NUV",
        "eso_instrument": "UVES",
        "gaia_source_id": 3136952686035250688,
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_NUV_KBAND_BRIDGE_10PC",
        "panchromatic_bridge": True,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3180.0,
        "mh_lit": 0.10,
        "mass_lit": 0.31,
        "rv_lit": 25.72,
    },
    {
        "canonical_target": "HD10361",
        "common_name": "p Eri B (HD 10361)",
        "instrument": "UVES_NUV",
        "eso_instrument": "UVES",
        "gaia_source_id": 4911306239828325632,
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 4,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 5044.0,
        "mh_lit": 0.05,
        "mass_lit": 0.86,
        "rv_lit": 21.74,
    },
    {
        "canonical_target": "HD203608",
        "common_name": "gam Pav (HD 203608)",
        "instrument": "UVES_NUV",
        "eso_instrument": "UVES",
        "gaia_source_id": 6401464693867773568,
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 4,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 6093.0,
        "mh_lit": -0.68,
        "mass_lit": 0.90,
        "rv_lit": -29.78,
    },
    {
        "canonical_target": "HD102365",
        "common_name": "66 Cen (HD 102365)",
        "instrument": "UVES_NUV",
        "eso_instrument": "UVES",
        "gaia_source_id": 5381537023379295232,
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 4,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 5629.0,
        "mh_lit": -0.29,
        "mass_lit": 0.85,
        "rv_lit": 16.94,
    },
    {
        "canonical_target": "HD154363",
        "common_name": "HD 154363",
        "instrument": "UVES_NUV",
        "eso_instrument": "UVES",
        "gaia_source_id": 4364527594192166400,
        "role": "SCIENCE",
        "subrole": "NUV_FRONTIER_EXTENDED",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 4311.0,
        "mh_lit": -0.35,
        "mass_lit": 0.65,
        "rv_lit": 34.12,
    },
    {
        "canonical_target": "HD146233",
        "common_name": "18 Sco (HD 146233)",
        "instrument": "UVES_NUV",
        "eso_instrument": "UVES",
        "gaia_source_id": 4345775217221821312,
        "role": "SCIENCE",
        "subrole": "SOLAR_TWIN_NUV",
        "panchromatic_bridge": False,
        "n_exp": 4,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 5790.0,
        "mh_lit": 0.04,
        "mass_lit": 1.02,
        "rv_lit": 11.71,
    },
    {
        "canonical_target": "TAUBOO",
        "common_name": "tau Boo",
        "instrument": "UVES_NUV",
        "eso_instrument": "UVES",
        "gaia_source_id": 1244571953471006720,
        "role": "SCIENCE",
        "subrole": "HOT_JUPITER_NUV",
        "panchromatic_bridge": False,
        "n_exp": 4,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 6387.0,
        "mh_lit": 0.28,
        "mass_lit": 1.32,
        "rv_lit": -16.75,
    },
    {
        "canonical_target": "HD1835",
        "common_name": "9 Cet (HD 1835)",
        "instrument": "UVES_NUV",
        "eso_instrument": "UVES",
        "gaia_source_id": 2423493369021649920,
        "role": "SCIENCE",
        "subrole": "SOLAR_ANALOG_NUV",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 5810.0,
        "mh_lit": 0.20,
        "mass_lit": 1.05,
        "rv_lit": -2.55,
    },
    # ==== ESPRESSO (6 stars, 48 exposures = 6 x 8 orbital): 2 CONTROL + 2 BRIDGE + 2 NEW ====
    {
        "canonical_target": "HD191408",
        "common_name": "HR 7703 (HD 191408)",
        "instrument": "ESPRESSO",
        "eso_instrument": "ESPRESSO",
        "gaia_source_id": 6697578465310949376,
        "role": "CONTROL",
        "subrole": "NULL_ORBITAL_CONTROL_10PC",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "Null Control (synthetic P=2.4117d)",
            "orbper_days": 2.4117,
            "t0_bjd": None,
            "ecc": 0.0,
            "st_mass_msun": 0.76,
            "transiting": False,
        },
        "teff_lit": 4922.0,
        "mh_lit": -0.55,
        "mass_lit": 0.76,
        "rv_lit": -129.27,
    },
    {
        "canonical_target": "L49956",
        "common_name": "L 499-56 (GJ 1265)",
        "instrument": "ESPRESSO",
        "eso_instrument": "ESPRESSO",
        "gaia_source_id": 6575069780231675264,
        "role": "CONTROL",
        "subrole": "NULL_ORBITAL_CONTROL_10PC",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "Null Control (synthetic P=2.8531d)",
            "orbper_days": 2.8531,
            "t0_bjd": None,
            "ecc": 0.0,
            "st_mass_msun": 0.35,
            "transiting": False,
        },
        "teff_lit": 3380.0,
        "mh_lit": -0.10,
        "mass_lit": 0.35,
        "rv_lit": -14.17,
    },
    {
        "canonical_target": "YZCET",
        "common_name": "YZ Cet",
        "instrument": "ESPRESSO",
        "eso_instrument": "ESPRESSO",
        "gaia_source_id": 2358524597030794112,
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_OPT_YJHK_BRIDGE_ORBITAL_10PC",
        "panchromatic_bridge": True,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "YZ Cet b",
            "orbper_days": 2.02087,
            "t0_bjd": 2452996.25,
            "ecc": 0.06,
            "st_mass_msun": 0.142,
            "transiting": False,
        },
        "teff_lit": 3151.0,
        "mh_lit": -0.18,
        "mass_lit": 0.142,
        "rv_lit": 28.30,
    },
    {
        "canonical_target": "GJ1002",
        "common_name": "GJ 1002",
        "instrument": "ESPRESSO",
        "eso_instrument": "ESPRESSO",
        "gaia_source_id": 2441630500517079808,
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_OPT_YJHK_BRIDGE_ORBITAL_10PC",
        "panchromatic_bridge": True,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "GJ 1002 b",
            "orbper_days": 10.3465,
            "t0_bjd": 2458583.27,
            "ecc": 0.0,
            "st_mass_msun": 0.120,
            "transiting": False,
        },
        "teff_lit": 3024.0,
        "mh_lit": -0.25,
        "mass_lit": 0.120,
        "rv_lit": -40.46,
    },
    {
        "canonical_target": "GJ1061",
        "common_name": "GJ 1061",
        "instrument": "ESPRESSO",
        "eso_instrument": "ESPRESSO",
        "gaia_source_id": 4848140361962951552,
        "role": "SCIENCE",
        "subrole": "EXOPLANET_ORBITAL_10PC",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "GJ 1061 b",
            "orbper_days": 3.2073,
            "t0_bjd": 2458300.61,
            "ecc": 0.05,
            "st_mass_msun": 0.120,
            "transiting": False,
        },
        "teff_lit": 2953.0,
        "mh_lit": -0.08,
        "mass_lit": 0.120,
        "rv_lit": 1.49,
    },
    {
        "canonical_target": "LHS1140",
        "common_name": "LHS 1140",
        "instrument": "ESPRESSO",
        "eso_instrument": "ESPRESSO",
        "gaia_source_id": 2371032916186181760,
        "role": "SCIENCE",
        "subrole": "TRANSITING_MM_OVERLAP_ORBITAL",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "M11_LHS1140",
        "orbital_campaign": {
            "planet_name": "LHS 1140 c",
            "orbper_days": 3.77794,
            "t0_bjd": 2458389.2939,
            "ecc": 0.05,
            "st_mass_msun": 0.1844,
            "transiting": True,
        },
        "teff_lit": 3096.0,
        "mh_lit": -0.15,
        "mass_lit": 0.1844,
        "rv_lit": -13.74,
    },
    # ==== HARPS (13 stars, 78 exposures): 2 CONTROL + 1 BRIDGE + 3 GBT MM + 7 <10pc ====
    {
        "canonical_target": "HD131977",
        "common_name": "KX Lib (HD 131977)",
        "instrument": "HARPS",
        "eso_instrument": "HARPS",
        "gaia_source_id": 6232511606838403968,
        "role": "CONTROL",
        "subrole": "NULL_ORBITAL_CONTROL_10PC",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "Null Control (synthetic P=2.6180d)",
            "orbper_days": 2.6180,
            "t0_bjd": None,
            "ecc": 0.0,
            "st_mass_msun": 0.76,
            "transiting": False,
        },
        "teff_lit": 4503.0,
        "mh_lit": -0.04,
        "mass_lit": 0.76,
        "rv_lit": 26.75,
    },
    {
        "canonical_target": "HD32147",
        "common_name": "HR 1614 (HD 32147)",
        "instrument": "HARPS",
        "eso_instrument": "HARPS",
        "gaia_source_id": 3211461469444773376,
        "role": "CONTROL",
        "subrole": "NULL_CONTROL_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 4627.0,
        "mh_lit": 0.10,
        "mass_lit": 0.78,
        "rv_lit": 21.36,
    },
    {
        "canonical_target": "TAUCET",
        "common_name": "tau Cet",
        "instrument": "HARPS",
        "eso_instrument": "HARPS",
        "gaia_source_id": 2452378776434477184,
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_OPT_NIR_BRIDGE_10PC",
        "panchromatic_bridge": True,
        "n_exp": 6,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 5310.0,
        "mh_lit": -0.52,
        "mass_lit": 0.783,
        "rv_lit": -16.68,
    },
    {
        "canonical_target": "HD192263",
        "common_name": "HD 192263",
        "instrument": "HARPS",
        "eso_instrument": "HARPS",
        "gaia_source_id": 4224259562941398400,
        "role": "SCIENCE",
        "subrole": "MM_GBT_OVERLAP_HOST",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "M31_HD192263",
        "orbital_campaign": None,
        "teff_lit": 4965.0,
        "mh_lit": -0.02,
        "mass_lit": 0.66,
        "rv_lit": -10.95,
    },
    {
        "canonical_target": "HD19994",
        "common_name": "94 Cet (HD 19994)",
        "instrument": "HARPS",
        "eso_instrument": "HARPS",
        "gaia_source_id": 3265335443260522112,
        "role": "SCIENCE",
        "subrole": "MM_GBT_OVERLAP_HOST",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "M26_HD19994",
        "orbital_campaign": None,
        "teff_lit": 6190.0,
        "mh_lit": 0.23,
        "mass_lit": 1.365,
        "rv_lit": 19.30,
    },
    {
        "canonical_target": "HD11964",
        "common_name": "HD 11964",
        "instrument": "HARPS",
        "eso_instrument": "HARPS",
        "gaia_source_id": 2462426800883134336,
        "role": "SCIENCE",
        "subrole": "MM_GBT_OVERLAP_HOST",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "M29_HD11964",
        "orbital_campaign": None,
        "teff_lit": 5349.0,
        "mh_lit": 0.12,
        "mass_lit": 0.91,
        "rv_lit": -9.39,
    },
    {
        "canonical_target": "GJ729",
        "common_name": "V1216 Sgr (GJ 729)",
        "instrument": "HARPS",
        "eso_instrument": "HARPS",
        "gaia_source_id": 4075141768785646848,
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3240.0,
        "mh_lit": -0.20,
        "mass_lit": 0.17,
        "rv_lit": -11.12,
    },
    {
        "canonical_target": "GJ876",
        "common_name": "IL Aqr (GJ 876)",
        "instrument": "HARPS",
        "eso_instrument": "HARPS",
        "gaia_source_id": 2603090003484152064,
        "role": "SCIENCE",
        "subrole": "EXOPLANET_ORBITAL_10PC",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "GJ 876 d",
            "orbper_days": 1.93778,
            "t0_bjd": 2455200.064,
            "ecc": 0.207,
            "st_mass_msun": 0.320,
            "transiting": False,
        },
        "teff_lit": 3201.0,
        "mh_lit": 0.15,
        "mass_lit": 0.320,
        "rv_lit": -2.09,
    },
    {
        "canonical_target": "HD26965",
        "common_name": "40 Eri A (HD 26965)",
        "instrument": "HARPS",
        "eso_instrument": "HARPS",
        "gaia_source_id": 3195919528989223040,
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 5147.0,
        "mh_lit": -0.28,
        "mass_lit": 0.78,
        "rv_lit": -42.47,
    },
    {
        "canonical_target": "HD119850",
        "common_name": "FN Vir (GJ 526 / HD 119850)",
        "instrument": "HARPS",
        "eso_instrument": "HARPS",
        "gaia_source_id": 3741297293732404352,
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3618.0,
        "mh_lit": -0.30,
        "mass_lit": 0.49,
        "rv_lit": 15.58,
    },
    {
        "canonical_target": "GJ393",
        "common_name": "GJ 393",
        "instrument": "HARPS",
        "eso_instrument": "HARPS",
        "gaia_source_id": 3855208897392952192,
        "role": "SCIENCE",
        "subrole": "EXOPLANET_ORBITAL_10PC",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "GJ 393 b",
            "orbper_days": 7.02679,
            "t0_bjd": 2458002.72,
            "ecc": 0.0,
            "st_mass_msun": 0.426,
            "transiting": False,
        },
        "teff_lit": 3548.0,
        "mh_lit": -0.18,
        "mass_lit": 0.426,
        "rv_lit": 7.98,
    },
    {
        "canonical_target": "HD4628",
        "common_name": "HR 222 (HD 4628)",
        "instrument": "HARPS",
        "eso_instrument": "HARPS",
        "gaia_source_id": 2552925644460225152,
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 4950.0,
        "mh_lit": -0.26,
        "mass_lit": 0.75,
        "rv_lit": -10.37,
    },
    {
        "canonical_target": "GJ357",
        "common_name": "GJ 357",
        "instrument": "HARPS",
        "eso_instrument": "HARPS",
        "gaia_source_id": 5664814198431308288,
        "role": "SCIENCE",
        "subrole": "TRANSITING_ORBITAL_10PC",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "GJ 357 b",
            "orbper_days": 3.9306,
            "t0_bjd": 2459272.6757,
            "ecc": 0.0,
            "st_mass_msun": 0.342,
            "transiting": True,
        },
        "teff_lit": 3505.0,
        "mh_lit": -0.12,
        "mass_lit": 0.342,
        "rv_lit": -35.03,
    },
]


def sky_sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    a = math.sin((d2 - d1) / 2.0) ** 2 + math.cos(d1) * math.cos(d2) * math.sin((r2 - r1) / 2.0) ** 2
    return math.degrees(2.0 * math.asin(min(1.0, math.sqrt(a)))) * 3600.0


def fetch_text(url: str, timeout: float = 45.0, retries: int = 3) -> str:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as exc:
            last_err = exc
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    assert last_err is not None
    raise last_err


def tap_csv(url: str, adql: str, timeout: float = 45.0) -> list[dict[str, str]]:
    full = f"{url}?{urllib.parse.urlencode({'REQUEST': 'doQuery', 'LANG': 'ADQL', 'FORMAT': 'csv', 'QUERY': adql})}"
    return list(csv.DictReader(io.StringIO(fetch_text(full, timeout=timeout))))


def tap_json(url: str, params: dict[str, str], timeout: float = 45.0) -> Any:
    full = f"{url}?{urllib.parse.urlencode(params)}"
    return json.loads(fetch_text(full, timeout=timeout))


def mjd_to_bjd_est(mjd_mid: float, ra_deg: float, dec_deg: float) -> float:
    t_jd = float(mjd_mid) + 2400000.5
    lam_sun = math.radians((280.46 + 0.9856474 * (t_jd - 2451545.0)) % 360.0)
    eps = math.radians(23.439)
    ra_r, dec_r = math.radians(ra_deg), math.radians(dec_deg)
    roemer_days = (499.00478 / 86400.0) * (
        math.cos(lam_sun) * math.cos(ra_r) * math.cos(dec_r)
        + math.sin(lam_sun) * (math.sin(ra_r) * math.cos(dec_r) * math.cos(eps) + math.sin(dec_r) * math.sin(eps))
    )
    return t_jd + roemer_days


def compute_keplerian_kp_kms(st_mass_msun: float, orbper_days: float, ecc: float) -> float:
    e_val = float(ecc) if (ecc is not None and 0.0 <= float(ecc) < 0.95) else 0.0
    v_circ_ms = ((2.0 * math.pi * G_SI * float(st_mass_msun) * M_SUN_KG) / (float(orbper_days) * DAY_S)) ** (1.0 / 3.0)
    return float((v_circ_ms / math.sqrt(1.0 - e_val * e_val)) / 1000.0)


def compute_planet_orbital_rv_kms(bjd_mid: float, t0_bjd: float, orbper_days: float, kp_kms: float) -> tuple[float, float]:
    raw_phi = (float(bjd_mid) - float(t0_bjd)) / float(orbper_days)
    phi_signed = raw_phi - round(raw_phi)
    return float(phi_signed), float(kp_kms * math.sin(2.0 * math.pi * phi_signed))


def parse_eso_datalink(dp_id: str, inst: str) -> dict[str, Any] | None:
    """Fetch metadata-only DataLink XML and resolve primary + required ancillary URLs & byte lengths."""
    url = f"{ESO_DATALINK}?ID={urllib.parse.quote(f'ivo://eso.org/ID?{dp_id}', safe='')}"
    xml_txt = fetch_text(url, timeout=30.0)
    root = ET.fromstring(xml_txt)
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"
    rows = root.findall(f".//{ns}TABLEDATA/{ns}TR")

    this_url = ""
    this_bytes = 0
    aux_url = ""
    aux_bytes = 0
    aux_orig = ""
    aux_cat = ""

    for tr in rows:
        tds = [(td.text or "").strip() for td in tr.findall(f"{ns}TD")]
        if len(tds) < 10:
            continue
        acc_url = tds[1]
        sem = tds[4]
        clen = int(tds[7]) if tds[7].isdigit() else 0
        orig = tds[8]
        cat = tds[9]
        if sem == "#this" and acc_url:
            this_url = acc_url
            this_bytes = clen
        elif sem == "#auxiliary" and acc_url:
            if inst == "ESPRESSO" and cat == "ANCILLARY.SPECTRUM" and ("SFLB" in orig or "S1D_B" in orig or orig.endswith(".fits")):
                aux_url = acc_url
                aux_bytes = clen
                aux_orig = orig
                aux_cat = cat
            elif inst == "HARPS" and cat == "ANCILLARY.HARPSTAR" and orig.endswith(".tar"):
                aux_url = acc_url
                aux_bytes = clen
                aux_orig = orig
                aux_cat = cat

    if not this_url:
        return None
    if inst in ("ESPRESSO", "HARPS") and not aux_url:
        return None
    return {
        "this_url": this_url,
        "this_bytes": this_bytes,
        "aux_url": aux_url,
        "aux_bytes": aux_bytes,
        "aux_orig": aux_orig,
        "aux_cat": aux_cat,
        "total_bytes": this_bytes + aux_bytes,
    }


def select_candidates_with_datalink(
    cands: list[dict[str, Any]],
    n_target: int,
    inst: str,
) -> list[dict[str, Any]]:
    """Select n_target night-spaced candidates and confirm DataLink endpoints."""
    by_night: dict[int, list[dict[str, Any]]] = {}
    for c in cands:
        by_night.setdefault(int(c["mjd_mid"]), []).append(c)

    # First pick best representative per distinct night (prefer highest SNR then exptime)
    night_reps = []
    for _n, lst in sorted(by_night.items()):
        lst_s = sorted(lst, key=lambda x: (-x["snr_tap"], -x["exptime"], x["mjd_mid"]))
        night_reps.append(lst_s[0])

    ordered: list[dict[str, Any]] = []
    if len(night_reps) >= n_target:
        idxs = [round(k * (len(night_reps) - 1) / (n_target - 1)) if n_target > 1 else 0 for k in range(n_target)]
        ordered.extend(night_reps[i] for i in idxs)
    else:
        ordered.extend(night_reps)
        used = {x["dp_id"] for x in ordered}
        rem = [x for x in sorted(cands, key=lambda r: (r["mjd_mid"], -r["snr_tap"])) if x["dp_id"] not in used]
        ordered.extend(rem)

    used_dp = {x["dp_id"] for x in ordered}
    fallback_pool = [x for x in sorted(cands, key=lambda r: (-r["snr_tap"], r["mjd_mid"])) if x["dp_id"] not in used_dp]
    trial_queue = ordered + fallback_pool

    verified: list[dict[str, Any]] = []
    seen: set[str] = set()
    for c in trial_queue:
        if c["dp_id"] in seen:
            continue
        seen.add(c["dp_id"])
        dl = parse_eso_datalink(c["dp_id"], inst)
        if dl is None:
            continue
        verified.append({**c, **dl})
        if len(verified) == n_target:
            break

    if len(verified) != n_target:
        raise RuntimeError(f"Only verified {len(verified)}/{n_target} DataLink exposures for {inst}")
    return sorted(verified, key=lambda x: x["mjd_mid"])


def select_orbital_with_datalink(
    cands: list[dict[str, Any]],
    n_take: int,
    inst: str,
) -> list[dict[str, Any]]:
    by_night: dict[int, list[dict[str, Any]]] = {}
    for c in cands:
        by_night.setdefault(int(c["mjd_mid"]), []).append(c)
    reps = [max(lst, key=lambda x: (x["snr_tap"], -abs(x["orbital_phase_signed"]))) for lst in by_night.values()]
    reps.sort(key=lambda x: x["orbital_phase_signed"])
    if len(reps) < n_take:
        reps = sorted(cands, key=lambda x: x["orbital_phase_signed"])
    idxs = [round(k * (len(reps) - 1) / (n_take - 1)) if n_take > 1 else 0 for k in range(n_take)]
    chosen_first = [reps[i] for i in idxs]
    used = {x["dp_id"] for x in chosen_first}
    queue = chosen_first + [r for r in reps if r["dp_id"] not in used] + [c for c in cands if c["dp_id"] not in used]

    verified: list[dict[str, Any]] = []
    seen: set[str] = set()
    for c in queue:
        if c["dp_id"] in seen:
            continue
        seen.add(c["dp_id"])
        dl = parse_eso_datalink(c["dp_id"], inst)
        if dl is None:
            continue
        verified.append({**c, **dl})
        if len(verified) == n_take:
            break
    if len(verified) != n_take:
        raise RuntimeError(f"Only verified {len(verified)}/{n_take} orbital DataLink exposures for {inst}")
    return sorted(verified, key=lambda x: x["mjd_mid"])


def build() -> None:
    now_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    print(f"[build_cohort] Starting D086 UVES_NUV+ESPRESSO+HARPS metadata-only build at {now_utc}", flush=True)

    # 1. Exclusion registry (C001-D085 + D086 format-check star HD 38666 / ADP.2020-09-07T09:38:30.546)
    d85_pe = json.loads((D085_WS / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    excl_coords: list[dict[str, Any]] = list(d85_pe["excluded_targets_coordinate_registry"])
    excl_dp_ids: set[str] = set(d85_pe["excluded_dp_ids"]) | set(d85_pe["format_check_excluded_dp_ids"])

    seen85: set[str] = set()
    with (D085_WS / "FROZEN_COHORT_D085.csv").open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            excl_dp_ids.add(row["dp_id"].strip())
            st = row["canonical_target"].strip()
            if st not in seen85 and row["panchromatic_bridge"] != "True":
                seen85.add(st)
                excl_coords.append({"label": f"{st}(D085)", "ra_deg": float(row["s_ra"]), "dec_deg": float(row["s_dec"])})

    fmt_targets = list(d85_pe["format_check_excluded_targets"]) + ["HD38666 (mu Col — D086 UVES Blue-Arm format check)"]
    fmt_dps = list(d85_pe["format_check_excluded_dp_ids"]) + ["ADP.2020-09-07T09:38:30.546"]
    excl_dp_ids.add("ADP.2020-09-07T09:38:30.546")
    excl_coords.append({"label": "HD38666(D086_FMT)", "ra_deg": 86.499583, "dec_deg": -32.306390})

    # 2. Query ESA Gaia DR3 & NASA Exoplanet Archive pscomppars
    gids_sql = ",".join(str(t["gaia_source_id"]) for t in TARGET_SPECS)
    gaia_rows = tap_csv(
        GAIA_TAP,
        "SELECT source_id, ra, dec, pmra, pmdec, parallax, radial_velocity, phot_g_mean_mag, "
        "phot_bp_mean_mag, phot_rp_mean_mag, bp_rp, teff_gspphot, mh_gspphot, ruwe "
        f"FROM gaiadr3.gaia_source WHERE source_id IN ({gids_sql})",
    )
    gaia_by_id = {int(r["source_id"]): r for r in gaia_rows}
    if len(gaia_by_id) != len(TARGET_SPECS):
        raise RuntimeError(f"Expected {len(TARGET_SPECS)} Gaia rows, got {len(gaia_by_id)}")

    nasa_rows = tap_json(
        NASA_TAP,
        {"query": "SELECT hostname, gaia_dr3_id, sy_pnum, ra, dec, st_teff, st_met, st_mass, st_radv FROM pscomppars WHERE sy_dist < 45", "format": "json"},
    )
    nasa_by_gid: dict[int, dict[str, Any]] = {}
    for nr in nasa_rows:
        gd = str(nr.get("gaia_dr3_id") or "")
        if gd.startswith("Gaia DR3 "):
            nasa_by_gid[int(gd.split()[-1])] = nr

    def query_target_metadata(spec: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        st = spec["canonical_target"]
        gid = spec["gaia_source_id"]
        inst = spec["instrument"]
        eso_inst = spec["eso_instrument"]
        g = gaia_by_id[gid]
        ra16, dec16 = float(g["ra"]), float(g["dec"])
        pmra = float(g["pmra"] or 0.0)
        pmdec = float(g["pmdec"] or 0.0)
        ra00 = ra16 - (16.0 * pmra) / (3600000.0 * math.cos(math.radians(dec16)))
        dec00 = dec16 - (16.0 * pmdec) / 3600000.0

        # 2MASS J/H/Ks via GAVO TAP (optional for NUV/Optical, nice to keep populated where available)
        j_mag, h_mag, ks_mag, tm_id = "", "", "", ""
        try:
            tm_rows = tap_json(
                GAVO_TAP,
                {
                    "REQUEST": "doQuery",
                    "LANG": "ADQL",
                    "FORMAT": "json",
                    "QUERY": (
                        "SELECT TOP 2 mainid, jmag, hmag, kmag, "
                        f"DISTANCE(POINT('ICRS', raj2000, dej2000), POINT('ICRS', {ra00:.6f}, {dec00:.6f}))*3600.0 AS sep "
                        f"FROM twomass.data WHERE 1=CONTAINS(POINT('ICRS', raj2000, dej2000), CIRCLE('ICRS', {ra00:.6f}, {dec00:.6f}, 0.015)) "
                        "ORDER BY sep ASC"
                    ),
                },
            )["data"]
            if tm_rows:
                tm_id = str(tm_rows[0][0])
                j_mag = round(float(tm_rows[0][1]), 4) if tm_rows[0][1] is not None else ""
                h_mag = round(float(tm_rows[0][2]), 4) if tm_rows[0][2] is not None else ""
                ks_mag = round(float(tm_rows[0][3]), 4) if tm_rows[0][3] is not None else ""
        except Exception:
            pass

        plx_mas = float(g["parallax"])
        dist_pc = 1000.0 / plx_mas

        nr = nasa_by_gid.get(gid)
        if nr is None:
            best_nr = None
            best_s = 25.0
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

        # ESO TAP ObsCore query
        if eso_inst == "UVES":
            extra = "AND em_min >= 3.0e-7 AND em_max <= 4.7e-7 AND em_res_power >= 35000 AND t_exptime >= 3.0"
            rad = 0.12
        elif eso_inst == "ESPRESSO":
            extra = "AND em_res_power >= 120000 AND t_exptime >= 30.0"
            rad = 0.08
        else:
            extra = "AND em_res_power >= 100000 AND t_exptime >= 30.0"
            rad = 0.08

        adql = (
            "SELECT dp_id, target_name, s_ra, s_dec, t_min, t_max, t_exptime, "
            "em_min, em_max, em_res_power, snr, obs_release_date "
            f"FROM ivoa.ObsCore WHERE instrument_name='{eso_inst}' AND dp_id LIKE 'ADP.%' "
            f"AND CONTAINS(POINT('ICRS', s_ra, s_dec), CIRCLE('ICRS', {ra16:.6f}, {dec16:.6f}, {rad}))=1 "
            f"{extra} AND obs_release_date <= '{OBS_RELEASE_CUTOFF}' ORDER BY t_min ASC"
        )
        erows = tap_csv(ESO_TAP, adql, timeout=45.0)
        exps: list[dict[str, Any]] = []
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
            "has_transiting_planet": bool(spec["orbital_campaign"] and spec["orbital_campaign"]["transiting"] and spec["role"] == "SCIENCE"),
            "min_prior_sep_arcsec": min_sep,
            "nearest_prior_label": nearest,
        }
        return meta, exps

    print("  Querying Gaia DR3 + 2MASS + NASA pscomppars + ESO TAP ObsCore across 31 targets...", flush=True)
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
            picks = select_candidates_with_datalink(cands, spec["n_exp"], inst)
            for rk, pk in enumerate(picks, start=1):
                pk["phase_window"] = "MULTI_EPOCH"
                pk["orbital_phase_signed"] = 0.0
                pk["planet_orbital_rv_kms"] = 0.0
                pk["epoch_rank"] = rk
        else:
            t0 = orb["t0_bjd"] if orb["t0_bjd"] is not None else cands[0]["bjd_mid_approx"]
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
            p_in = select_orbital_with_datalink(in_cands, 4, inst)
            in_used = {p["dp_id"] for p in p_in}
            p_out = select_orbital_with_datalink([c for c in out_cands if c["dp_id"] not in in_used], 4, inst)
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
                "phase_id": "D086",
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
        f"({len(new_verifs)} brand-new [{new_10pc} <10pc] + 6 bridge); "
        f"min_prior_sep={min_brand_new_sep:.2f}\", min_intra_sep={min_intra_sep:.2f}\"; "
        f"projected download={proj_gib:.3f} GiB",
        flush=True,
    )
    if proj_gib > 4.2:
        raise RuntimeError(f"Projected download size {proj_gib:.3f} GiB exceeds 4.2 GiB safety limit!")

    # Write FROZEN_COHORT_D086.csv
    cohort_path = WS / "FROZEN_COHORT_D086.csv"
    with cohort_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(cohort_rows[0].keys()))
        w.writeheader()
        w.writerows(cohort_rows)

    # Write ORBITAL_CAMPAIGNS_AND_KINEMATICS.json
    orb_doc = {
        "schema": "PANCHROM_V3_7_ORBITAL_CAMPAIGNS",
        "phase_id": "D086",
        "instruments": ["ESPRESSO", "HARPS"],
        "n_campaigns": len(orbital_campaigns),
        "n_science_orbital_campaigns": sum(1 for c in orbital_campaigns.values() if c["role"] == "SCIENCE"),
        "n_control_null_campaigns": sum(1 for c in orbital_campaigns.values() if c["role"] == "CONTROL"),
        "campaigns": orbital_campaigns,
    }
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    # Write PRIOR_EXCLUSION_VERIFICATION.json
    bridge_stars = {t["canonical_target"] for t in TARGET_SPECS if t["panchromatic_bridge"]}
    excl_doc = {
        "schema": "D086_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D086",
        "verified_utc": now_utc,
        "prior_phases_covered": "C001-C037 + D001-D085",
        "format_check_excluded_targets": fmt_targets,
        "format_check_excluded_dp_ids": fmt_dps,
        "n_prior_excluded_coords": len(excl_coords),
        "n_prior_excluded_dp_ids": len(excl_dp_ids),
        "d086_total_stars": len(TARGET_SPECS),
        "d086_brand_new_unique_stars": len(new_verifs),
        "d086_panchromatic_bridge_stars": len(bridge_stars),
        "d086_brand_new_within_10pc": new_10pc,
        "d086_total_exposures": len(cohort_rows),
        "d086_projected_download_bytes": total_projected_bytes,
        "d086_projected_download_gib": round(proj_gib, 4),
        "d086_dp_id_overlap_count": len({r["dp_id"] for r in cohort_rows} & excl_dp_ids),
        "min_brand_new_sky_separation_arcsec": round(min_brand_new_sep, 2),
        "min_intra_d086_brand_new_separation_arcsec": round(min_intra_sep, 2),
        "star_separation_verification": star_sep_verif,
        "excluded_dp_ids": sorted(excl_dp_ids),
        "excluded_targets_coordinate_registry": excl_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(excl_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    # Snapshot prior V3.0-V3.6 synthesis (150 stars, 73 <10pc, 1,009 exp, 8 bridge stars) + bridge prior limits
    d85_summary = json.loads((D085_WS / "results" / "SUMMARY.json").read_text(encoding="utf-8"))
    d85_snap = json.loads((D085_WS / "PRIOR_V3_PHASES_SNAPSHOT.json").read_text(encoding="utf-8"))
    with (D085_WS / "results" / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_150STARS.csv").open("r", encoding="utf-8", newline="") as f:
        unified_150 = list(csv.DictReader(f))
    with (D085_WS / "results" / "PANCHROMATIC_OPTICAL_NIR_K_BRIDGE_8STARS.csv").open("r", encoding="utf-8", newline="") as f:
        bridge_8 = list(csv.DictReader(f))

    # Extract prior upper limits for new D086 bridges (EPSERI & TAUCET from D082, GJ285 from D083, YZCET & GJ1002 from D085)
    prior_new_bridge_ul: list[dict[str, Any]] = []
    with (D082_WS / "results" / "STAR_UPPER_LIMITS_162.csv").open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["star"] in ("EPSERI", "TAUCET"):
                prior_new_bridge_ul.append({"phase_id": "D082", "spectral_regime": "NEAR_IR_0p98_1p80um", "instrument": "NIRPS_HE", **r})
    with (D083_WS / "results" / "STAR_UPPER_LIMITS_162.csv").open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["star"] == "GJ285":
                prior_new_bridge_ul.append({"phase_id": "D083", "spectral_regime": "THERMAL_KBAND_1p96_2p48um", "instrument": "CRIRES_PLUS_K", **r})
    with (D085_WS / "results" / "STAR_UPPER_LIMITS_300.csv").open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["star"] in ("YZCET", "GJ1002"):
                prior_new_bridge_ul.append({"phase_id": "D085", "spectral_regime": "YJHK_0p955_2p515um", "instrument": "SPIROU", **r})

    prior_snap = {
        "schema": "D086_PRIOR_V3_PHASES_SNAPSHOT",
        "prior_phases": "D079-D085",
        "prior_v3_unique_stars_count": len(unified_150),
        "prior_v3_within_10pc_count": sum(1 for r in unified_150 if r["within_10pc"] == "True"),
        "prior_v3_total_exposures_count": sum(int(r["n_exposures_total"]) for r in unified_150),
        "prior_v3_calibration_trials_count": int(d85_summary["unified_150star_panchromatic_v3_synthesis"]["total_calibration_trials_d079_d085"]),
        "prior_v2_false_alarms_eliminated_total": int(d85_summary["unified_150star_panchromatic_v3_synthesis"]["v2_false_alarms_eliminated_total"]),
        "d085_summary_headline": d85_summary,
        "d084_summary_headline": d85_snap["d084_summary_headline"],
        "d083_summary_headline": d85_snap["d083_summary_headline"],
        "d079_d082_headlines": d85_snap["d079_d082_headlines"],
        "unified_150star_rows": unified_150,
        "d085_bridge_8star_rows": bridge_8,
        "prior_new_bridge_upper_limits": prior_new_bridge_ul,
    }
    (WS / "PRIOR_V3_PHASES_SNAPSHOT.json").write_text(json.dumps(prior_snap, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    # Multi-messenger snapshot: update M11_LHS1140, M26_HD19994, M29_HD11964, M31_HD192263 -> 18 direct overlaps
    d85_mm = json.loads((D085_WS / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").read_text(encoding="utf-8"))
    mm_map = {
        "M11_LHS1140": "LHS1140",
        "M26_HD19994": "HD19994",
        "M29_HD11964": "HD11964",
        "M31_HD192263": "HD192263",
    }
    for s in d85_mm["systems"]:
        if s["mm_id"] in mm_map:
            s["canonical_v3_star"] = mm_map[s["mm_id"]]
    ov_stars = sorted({s["canonical_v3_star"] for s in d85_mm["systems"] if s["canonical_v3_star"]})
    mm_doc = dict(d85_mm)
    mm_doc["schema"] = "D086_MULTIMESSENGER_RADIO_TESS_SNAPSHOT"
    mm_doc["n_direct_echelle_multimessenger_overlap_stars"] = len(ov_stars)
    mm_doc["overlapping_v3_stars"] = ov_stars
    (WS / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").write_text(json.dumps(mm_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("[build_cohort] Wrote all 5 locked metadata & snapshot artifacts successfully.", flush=True)


if __name__ == "__main__":
    build()
