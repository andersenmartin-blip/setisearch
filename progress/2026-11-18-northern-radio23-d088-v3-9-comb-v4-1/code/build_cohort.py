#!/usr/bin/env python3
"""
Phase D088 prospective cohort builder & lock registry generator.

Strict prospective rule:
- Runs BEFORE any D088 science FITS bytes are touched (`inputs_d088_v3_9` MUST NOT EXIST).
- Queries ONLY external archival metadata endpoints:
  * ESA Gaia DR3 TAP (ICRS positions, PMs, parallaxes, G/BP/RP photometry, RV)
  * GAVO 2MASS PSC TAP (J, H, Ks photometry & designations)
  * NASA Exoplanet Archive pscomppars TAP (planet counts & Keplerian ephemerides)
  * OHP SOPHIE text table + header metadata (`z=fd`)
  * OHP ELODIE text table + header metadata (`z=fd`)
  * CADC ivoa.ObsCore TAP for CFHT ESPaDOnS (`*i.fits` intensity spectra)
- Outputs:
  * FROZEN_COHORT_D088.csv (25 stars / 176 exposures)
  * ORBITAL_CAMPAIGNS_AND_KINEMATICS.json (10 campaigns: 7 science + 3 null controls, 4 IN + 4 OUT)
  * PRIOR_EXCLUSION_VERIFICATION.json (excludes C001-C037 + D001-D087 + D088 Vega format check)
  * PRIOR_V3_PHASES_SNAPSHOT.json (frozen snapshot of D079-D087 = 200 stars / 1,391 exposures / 103 <10pc / 17 bridges)
  * MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json (updated for 23/23 GBT 1.4 GHz + 1 TESS closure)
"""

from __future__ import annotations

import csv
import datetime
import html
import io
import json
import math
import os
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from v3_9_detector import (
    compute_keplerian_kp_kms,
    compute_planet_orbital_rv_kms,
)

ROOT = Path(".")
AWS = ROOT / "analysis_workspace"
WS = AWS / "work_radio23_allsky_20261118_d088_v3_9_northern_and_comb_v4_1"
INP_DIR = ROOT / "inputs_d088_v3_9"

D084_WS = AWS / "work_northern_20261115_d084_v3_5_harpsn_carmenes_survey"
D085_WS = AWS / "work_spirou_20261116_d085_v3_6_yjhk_and_comb_v4"
D086_WS = AWS / "work_uves_panchrom_20261117_d086_v3_7_nuv_and_comb_v4_1"
D087_WS = AWS / "work_stis_farred_20261118_d087_v3_8_space_uv_and_200star"

GAIA_TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
GAVO_TAP = "https://dc.g-vo.org/tap/sync"
NASA_TAP = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
CADC_TAP = "https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/argus/sync"
SOPHIE_CGI = "http://atlas.obs-hp.fr/sophie/sophie.cgi"
ELODIE_CGI = "http://atlas.obs-hp.fr/elodie/fE.cgi"

OBS_RELEASE_CUTOFF_ISO = "2026-11-18"
MAX_PROJ_DOWNLOAD_GIB = 1.8

VEGA_FORMAT_CHECK = {
    "label": "HD172167 (Vega -- D088 OHP/CFHT format check)",
    "ra_deg": 279.234735,
    "dec_deg": 38.783689,
    "dp_ids": ["SOPHIE_format_vega", "ELODIE_format_vega", "CFHT_format_vega"],
}

TARGET_SPECS: list[dict[str, Any]] = [
    # --- OHP SOPHIE (9 brand-new stars, 68 HR exposures) ---
    {
        "instrument": "OHP_SOPHIE",
        "canonical_target": "HD109358",
        "common_name": "beta CVn (HD 109358)",
        "role": "CONTROL",
        "subrole": "NULL_ORBITAL_CONTROL_10PC",
        "panchromatic_bridge": False,
        "radio_mm_id": "",
        "gaia_source_id": 1534011998572555776,
        "ohp_queries": ["HD109358"],
        "n_target_exposures": 8,
        "orbital_campaign": True,
        "null_orbital": True,
        "planet_name": "Null Control (synthetic P=2.4137d)",
        "orb_per_days": 2.4137,
        "orb_e": 0.0,
        "teff_lit": 5890.0,
        "mh_lit": -0.20,
        "mass_lit": 0.98,
        "rv_lit": 6.3,
    },
    {
        "instrument": "OHP_SOPHIE",
        "canonical_target": "HD114710",
        "common_name": "beta Com (HD 114710)",
        "role": "CONTROL",
        "subrole": "NULL_CONTROL_10PC",
        "panchromatic_bridge": False,
        "radio_mm_id": "",
        "gaia_source_id": 1460229442589223424,
        "ohp_queries": ["HD114710"],
        "n_target_exposures": 6,
        "orbital_campaign": False,
        "teff_lit": 6020.0,
        "mh_lit": 0.05,
        "mass_lit": 1.10,
        "rv_lit": 5.3,
    },
    {
        "instrument": "OHP_SOPHIE",
        "canonical_target": "47UMA",
        "common_name": "47 UMa (HD 95128)",
        "role": "SCIENCE",
        "subrole": "RADIO_GBT_ORBITAL_47UMA",
        "panchromatic_bridge": False,
        "radio_mm_id": "M19_47UMA",
        "gaia_source_id": 777254360337133312,
        "ohp_queries": ["HD95128"],
        "n_target_exposures": 8,
        "orbital_campaign": True,
        "null_orbital": False,
        "nasa_hostname": "47 UMa",
        "planet_name": "47 UMa b",
        "orb_per_days": 1078.0,
        "orb_t0_bjd": 2454415.6,
        "orb_e": 0.032,
        "teff_lit": 5872.0,
        "mh_lit": 0.04,
        "mass_lit": 1.06,
        "rv_lit": 11.3,
    },
    {
        "instrument": "OHP_SOPHIE",
        "canonical_target": "HD154345",
        "common_name": "HD 154345",
        "role": "SCIENCE",
        "subrole": "RADIO_GBT_HOST",
        "panchromatic_bridge": False,
        "radio_mm_id": "M21_HD154345",
        "gaia_source_id": 1359938520253565952,
        "ohp_queries": ["HD154345"],
        "n_target_exposures": 6,
        "orbital_campaign": False,
        "nasa_hostname": "HD 154345",
        "teff_lit": 5468.0,
        "mh_lit": -0.105,
        "mass_lit": 0.89,
        "rv_lit": -47.3,
    },
    {
        "instrument": "OHP_SOPHIE",
        "canonical_target": "PSI1DRAB",
        "common_name": "psi1 Dra B (HD 162004)",
        "role": "SCIENCE",
        "subrole": "RADIO_GBT_HOST",
        "panchromatic_bridge": False,
        "radio_mm_id": "M28_PSI1DRAB",
        "gaia_source_id": 1651268763282397312,
        "ohp_queries": ["HD162004"],
        "n_target_exposures": 8,
        "orbital_campaign": False,
        "nasa_hostname": "psi1 Dra B",
        "teff_lit": 6212.0,
        "mh_lit": 0.01,
        "mass_lit": 1.19,
        "rv_lit": -11.0,
    },
    {
        "instrument": "OHP_SOPHIE",
        "canonical_target": "GJ625",
        "common_name": "GJ 625 (G 202-48)",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_ORBITAL_10PC",
        "panchromatic_bridge": False,
        "radio_mm_id": "",
        "gaia_source_id": 1428427236986209024,
        "ohp_queries": ["GJ625"],
        "n_target_exposures": 8,
        "orbital_campaign": True,
        "null_orbital": False,
        "nasa_hostname": "GJ 625",
        "planet_name": "GJ 625 b",
        "orb_per_days": 14.628,
        "orb_t0_bjd": None,
        "orb_e": 0.13,
        "teff_lit": 3499.0,
        "mh_lit": -0.38,
        "mass_lit": 0.30,
        "rv_lit": -13.0,
    },
    {
        "instrument": "OHP_SOPHIE",
        "canonical_target": "GJ686",
        "common_name": "Gl 686 (BD+18 3421)",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_ORBITAL_10PC",
        "panchromatic_bridge": False,
        "radio_mm_id": "",
        "gaia_source_id": 4550763526539955712,
        "ohp_queries": ["GJ686"],
        "n_target_exposures": 8,
        "orbital_campaign": True,
        "null_orbital": False,
        "nasa_hostname": "Gl 686",
        "planet_name": "Gl 686 b",
        "orb_per_days": 15.53,
        "orb_t0_bjd": 2450606.8,
        "orb_e": 0.05,
        "teff_lit": 3657.0,
        "mh_lit": -0.28,
        "mass_lit": 0.426,
        "rv_lit": -9.5,
    },
    {
        "instrument": "OHP_SOPHIE",
        "canonical_target": "HD285968",
        "common_name": "GJ 176 (HD 285968)",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_EXO_10PC",
        "panchromatic_bridge": False,
        "radio_mm_id": "",
        "gaia_source_id": 3409711211681795584,
        "ohp_queries": ["HD285968"],
        "n_target_exposures": 8,
        "orbital_campaign": False,
        "nasa_hostname": "GJ 176",
        "teff_lit": 3680.0,
        "mh_lit": 0.14,
        "mass_lit": 0.45,
        "rv_lit": 25.8,
    },
    {
        "instrument": "OHP_SOPHIE",
        "canonical_target": "HD157881",
        "common_name": "GJ 673 (HD 157881)",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "radio_mm_id": "",
        "gaia_source_id": 4375233191015944192,
        "ohp_queries": ["HD157881"],
        "n_target_exposures": 8,
        "orbital_campaign": False,
        "teff_lit": 4125.0,
        "mh_lit": -0.05,
        "mass_lit": 0.65,
        "rv_lit": -23.9,
    },
    # --- OHP ELODIE (7 brand-new stars, 48 exposures) ---
    {
        "instrument": "OHP_ELODIE",
        "canonical_target": "HD6582",
        "common_name": "mu Cas (HD 6582)",
        "role": "CONTROL",
        "subrole": "NULL_ORBITAL_CONTROL_10PC",
        "panchromatic_bridge": False,
        "radio_mm_id": "",
        "gaia_source_id": 411413822074322432,
        "ohp_queries": ["HD6582"],
        "n_target_exposures": 8,
        "orbital_campaign": True,
        "null_orbital": True,
        "planet_name": "Null Control (synthetic P=3.1729d)",
        "orb_per_days": 3.1729,
        "orb_e": 0.0,
        "teff_lit": 5350.0,
        "mh_lit": -0.81,
        "mass_lit": 0.74,
        "rv_lit": -97.1,
    },
    {
        "instrument": "OHP_ELODIE",
        "canonical_target": "HD30652",
        "common_name": "pi3 Ori (HD 30652)",
        "role": "CONTROL",
        "subrole": "NULL_CONTROL_10PC",
        "panchromatic_bridge": False,
        "radio_mm_id": "",
        "gaia_source_id": 3288921720025503360,
        "ohp_queries": ["HD30652"],
        "n_target_exposures": 6,
        "orbital_campaign": False,
        "teff_lit": 6440.0,
        "mh_lit": -0.02,
        "mass_lit": 1.24,
        "rv_lit": 24.3,
    },
    {
        "instrument": "OHP_ELODIE",
        "canonical_target": "HD33564",
        "common_name": "HD 33564",
        "role": "SCIENCE",
        "subrole": "RADIO_GBT_ORBITAL_HD33564",
        "panchromatic_bridge": False,
        "radio_mm_id": "M23_HD33564",
        "gaia_source_id": 553480551264062848,
        "ohp_queries": ["HD33564"],
        "n_target_exposures": 8,
        "orbital_campaign": True,
        "null_orbital": False,
        "nasa_hostname": "HD 33564",
        "planet_name": "HD 33564 b",
        "orb_per_days": 388.0,
        "orb_t0_bjd": 2452603.0,
        "orb_e": 0.34,
        "teff_lit": 6250.0,
        "mh_lit": -0.12,
        "mass_lit": 1.25,
        "rv_lit": -10.2,
    },
    {
        "instrument": "OHP_ELODIE",
        "canonical_target": "HD127506",
        "common_name": "HD 127506 (GJ 554)",
        "role": "SCIENCE",
        "subrole": "RADIO_GBT_ORBITAL_HD127506",
        "panchromatic_bridge": False,
        "radio_mm_id": "M27_HD127506",
        "gaia_source_id": 1480314599451475712,
        "ohp_queries": ["HD127506"],
        "n_target_exposures": 8,
        "orbital_campaign": True,
        "null_orbital": False,
        "nasa_hostname": "HD 127506",
        "planet_name": "HD 127506 b",
        "orb_per_days": 65.78395,
        "orb_t0_bjd": 2456787.645,
        "orb_e": 0.24,
        "teff_lit": 4750.0,
        "mh_lit": -0.07,
        "mass_lit": 0.73,
        "rv_lit": -19.5,
    },
    {
        "instrument": "OHP_ELODIE",
        "canonical_target": "HD165341",
        "common_name": "70 Oph (HD 165341)",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "radio_mm_id": "",
        "gaia_source_id": 4468557611984384512,
        "ohp_queries": ["HD165341"],
        "n_target_exposures": 6,
        "orbital_campaign": False,
        "teff_lit": 5300.0,
        "mh_lit": 0.04,
        "mass_lit": 0.90,
        "rv_lit": -7.2,
    },
    {
        "instrument": "OHP_ELODIE",
        "canonical_target": "HD4614",
        "common_name": "eta Cas A (HD 4614)",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "radio_mm_id": "",
        "gaia_source_id": 425040000962559616,
        "ohp_queries": ["HD4614"],
        "n_target_exposures": 6,
        "orbital_campaign": False,
        "teff_lit": 5970.0,
        "mh_lit": -0.25,
        "mass_lit": 0.97,
        "rv_lit": 8.3,
    },
    {
        "instrument": "OHP_ELODIE",
        "canonical_target": "HD10476",
        "common_name": "107 Psc (HD 10476)",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "radio_mm_id": "",
        "gaia_source_id": 96331172942614528,
        "ohp_queries": ["HD10476"],
        "n_target_exposures": 6,
        "orbital_campaign": False,
        "teff_lit": 5190.0,
        "mh_lit": -0.04,
        "mass_lit": 0.81,
        "rv_lit": -33.6,
    },
    # --- CFHT ESPaDOnS (4 brand-new + 5 <10 pc bridges = 9 stars, 60 exposures) ---
    {
        "instrument": "CFHT_ESPADONS",
        "canonical_target": "HD39587",
        "common_name": "chi1 Ori (HD 39587)",
        "role": "CONTROL",
        "subrole": "NULL_ORBITAL_CONTROL_10PC",
        "panchromatic_bridge": False,
        "radio_mm_id": "",
        "gaia_source_id": 3399063235755057792,
        "cadc_names": ["HD 39587", "HD39587"],
        "n_target_exposures": 8,
        "orbital_campaign": True,
        "null_orbital": True,
        "planet_name": "Null Control (synthetic P=2.8713d)",
        "orb_per_days": 2.8713,
        "orb_e": 0.0,
        "teff_lit": 5940.0,
        "mh_lit": -0.04,
        "mass_lit": 1.01,
        "rv_lit": -13.7,
    },
    {
        "instrument": "CFHT_ESPADONS",
        "canonical_target": "HD161797",
        "common_name": "mu Her (HD 161797)",
        "role": "CONTROL",
        "subrole": "NULL_CONTROL_10PC",
        "panchromatic_bridge": False,
        "radio_mm_id": "",
        "gaia_source_id": 4594497769766809216,
        "cadc_names": ["HIP 86974", "J17462507+2743014", "HD 161797", "HD161797"],
        "n_target_exposures": 6,
        "orbital_campaign": False,
        "teff_lit": 5560.0,
        "mh_lit": 0.25,
        "mass_lit": 1.10,
        "rv_lit": -16.4,
    },
    {
        "instrument": "CFHT_ESPADONS",
        "canonical_target": "BETUMI",
        "common_name": "beta UMi (Kochab, HIP 72607)",
        "role": "SCIENCE",
        "subrole": "RADIO_GBT_ORBITAL_BETUMI",
        "panchromatic_bridge": False,
        "radio_mm_id": "M30_BETUMI",
        "gaia_source_id": None,
        "cadc_names": ["beta UMi", "HD 131873"],
        "n_target_exposures": 8,
        "orbital_campaign": True,
        "null_orbital": False,
        "nasa_hostname": "bet UMi",
        "planet_name": "bet UMi b",
        "orb_per_days": 522.3,
        "orb_t0_bjd": 2453175.3,
        "orb_e": 0.19,
        "ra_lit": 222.676495,
        "dec_lit": 74.155548,
        "pmra_lit": -32.6,
        "pmdec_lit": 11.4,
        "dist_lit": 38.77472,
        "vmag_lit": 2.0569,
        "teff_lit": 4126.0,
        "mh_lit": -0.27,
        "mass_lit": 1.40,
        "rv_lit": 16.9,
    },
    {
        "instrument": "CFHT_ESPADONS",
        "canonical_target": "GJ49",
        "common_name": "Gl 49 (HIP 4872)",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_ORBITAL_10PC",
        "panchromatic_bridge": False,
        "radio_mm_id": "",
        "gaia_source_id": 522863309964987520,
        "cadc_names": ["Gl49", "HIP 4872", "Gl 49"],
        "n_target_exposures": 8,
        "orbital_campaign": True,
        "null_orbital": False,
        "nasa_hostname": "Gl 49",
        "planet_name": "Gl 49 b",
        "orb_per_days": 13.8508,
        "orb_t0_bjd": 2455995.88,
        "orb_e": 0.363,
        "teff_lit": 3805.0,
        "mh_lit": 0.13,
        "mass_lit": 0.515,
        "rv_lit": -5.9,
    },
    {
        "instrument": "CFHT_ESPADONS",
        "canonical_target": "61CYGA",
        "common_name": "61 Cygni A",
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_BRIDGE_10PC",
        "panchromatic_bridge": True,
        "radio_mm_id": "",
        "gaia_source_id": 1872046609345556480,
        "cadc_names": ["61 Cyg A", "61 cyg A", "HD201091", "HR 8085"],
        "max_cadc_sep_arcsec": 180.0,
        "n_target_exposures": 6,
        "orbital_campaign": False,
        "teff_lit": 4526.0,
        "mh_lit": -0.20,
        "mass_lit": 0.70,
        "rv_lit": -65.7,
    },
    {
        "instrument": "CFHT_ESPADONS",
        "canonical_target": "61CYGB",
        "common_name": "61 Cygni B",
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_BRIDGE_10PC",
        "panchromatic_bridge": True,
        "radio_mm_id": "",
        "gaia_source_id": 1872046574983497216,
        "cadc_names": ["61 Cyg B", "61 cyg B", "HD201092"],
        "max_cadc_sep_arcsec": 180.0,
        "n_target_exposures": 6,
        "orbital_campaign": False,
        "teff_lit": 4077.0,
        "mh_lit": -0.27,
        "mass_lit": 0.63,
        "rv_lit": -64.1,
    },
    {
        "instrument": "CFHT_ESPADONS",
        "canonical_target": "GXAND",
        "common_name": "GX And (GJ 15 A)",
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_BRIDGE_10PC",
        "panchromatic_bridge": True,
        "radio_mm_id": "",
        "gaia_source_id": 385334230892516480,
        "cadc_names": ["Gl 15A", "HD1326", "J00182549+4401376", "PM_I00184+4401", "gx and", "gxand", "m2_hd1326"],
        "max_cadc_sep_arcsec": 180.0,
        "n_target_exposures": 6,
        "orbital_campaign": False,
        "nasa_hostname": "GJ 15 A",
        "teff_lit": 3607.0,
        "mh_lit": -0.34,
        "mass_lit": 0.39,
        "rv_lit": 11.7,
    },
    {
        "instrument": "CFHT_ESPADONS",
        "canonical_target": "GJ687",
        "common_name": "GJ 687",
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_BRIDGE_RADIO_10PC",
        "panchromatic_bridge": True,
        "radio_mm_id": "M14_GJ687",
        "gaia_source_id": 1637645127018395776,
        "cadc_names": ["GJ687", "GJ_687_STD"],
        "n_target_exposures": 6,
        "orbital_campaign": False,
        "nasa_hostname": "GJ 687",
        "teff_lit": 3475.0,
        "mh_lit": 0.05,
        "mass_lit": 0.40,
        "rv_lit": -28.8,
    },
    {
        "instrument": "CFHT_ESPADONS",
        "canonical_target": "LALANDE21185",
        "common_name": "Lalande 21185 (GJ 411)",
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_BRIDGE_10PC",
        "panchromatic_bridge": True,
        "radio_mm_id": "",
        "gaia_source_id": 762815470562110464,
        "cadc_names": ["GJ411", "GL411", "Gl 411", "Gl411", "HD95735", "PM_I11033+3558"],
        "n_target_exposures": 6,
        "orbital_campaign": False,
        "nasa_hostname": "GJ 411",
        "teff_lit": 3557.0,
        "mh_lit": -0.35,
        "mass_lit": 0.39,
        "rv_lit": -84.7,
    },
]


def sky_sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    cos_ang = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    cos_ang = max(-1.0, min(1.0, cos_ang))
    return math.degrees(math.acos(cos_ang)) * 3600.0


def parse_j2000_tag(tag: str) -> tuple[float, float] | None:
    m = re.match(r"^J(\d{2})(\d{2})(\d{2}(?:\.\d+)?)([+-])(\d{2})(\d{2})(\d{2}(?:\.\d+)?)$", tag.strip())
    if not m:
        return None
    hh, mm, ss, sgn, dd, dm, ds = m.groups()
    ra = (int(hh) + int(mm) / 60.0 + float(ss) / 3600.0) * 15.0
    dec_abs = int(dd) + int(dm) / 60.0 + float(ds) / 3600.0
    dec = -dec_abs if sgn == "-" else dec_abs
    return ra, dec


def mjd_to_bjd_est(mjd_mid: float, ra_deg: float, dec_deg: float) -> float:
    jd = mjd_mid + 2400000.5
    n = jd - 2451545.0
    L = math.radians((280.460 + 0.9856474 * n) % 360.0)
    g = math.radians((357.528 + 0.9856003 * n) % 360.0)
    lam = L + math.radians(1.915) * math.sin(g) + math.radians(0.020) * math.sin(2.0 * g)
    eps = math.radians(23.439 - 0.0000004 * n)
    x = math.cos(lam)
    y = math.cos(eps) * math.sin(lam)
    z = math.sin(eps) * math.sin(lam)
    ra_r, dec_r = math.radians(ra_deg), math.radians(dec_deg)
    roemer_days = (x * math.cos(dec_r) * math.cos(ra_r) + y * math.cos(dec_r) * math.sin(ra_r) + z * math.sin(dec_r)) * (499.00478 / 86400.0)
    return jd + roemer_days


def mjd_to_iso_utc(mjd_val: float) -> str:
    unix_ts = (mjd_val + 2400000.5 - 2440587.5) * 86400.0
    return datetime.datetime.fromtimestamp(unix_ts, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_text(url: str, timeout: float = 35.0, retries: int = 3) -> str:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETI-D088-CohortBuilder/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as exc:
            last_err = exc
            time.sleep(0.6 * (attempt + 1))
    raise RuntimeError(f"GET failed for {url}: {last_err}")


def tap_json(url: str, params: dict[str, str], timeout: float = 45.0, use_get: bool = False) -> Any:
    if use_get:
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(full_url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def tap_csv(url: str, sql: str, timeout: float = 45.0) -> list[dict[str, str]]:
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": sql}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "SETI-D088-CohortBuilder/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        txt = r.read().decode("utf-8", "replace")
    return list(csv.DictReader(io.StringIO(txt)))


def probe_head_bytes(url: str, default_bytes: int, timeout: float = 15.0) -> int:
    if "atlas.obs-hp.fr" in url:
        return default_bytes
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "SETI-D088-CohortBuilder/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            cl = r.headers.get("Content-Length")
            if cl and int(cl) > 1000:
                return int(cl)
    except Exception:
        pass
    return default_bytes


def parse_ohp_zfd_header(raw_html: str) -> dict[str, str]:
    txt = html.unescape(re.sub(r"<[^>]+>", "", raw_html))
    cards: dict[str, str] = {}
    for line in txt.splitlines():
        s = line.strip()
        if not s:
            continue
        # Match FITS card syntax or fixed columns: KEY  VALUE  COMMENT
        m = re.match(r"^(OHP\s+[A-Z0-9_\s]+?|DATE-OBS|MJD-OBS|EXPTIME|BERV|SN|IMAGETYP|FILERC|OBJECT)\s+('(?:[^']*)'|[+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)(?:\s|$)", s)
        if m:
            k = " ".join(m.group(1).split())
            v = m.group(2).strip().strip("'")
            cards[k] = v
    return cards


def query_sophie_table(obj_query: str, ra_ref: float, dec_ref: float, excl_dp_ids: set[str]) -> list[dict[str, Any]]:
    url = f"{SOPHIE_CGI}?n=sophie&c=o&a=t&o={urllib.parse.quote(obj_query)}"
    lines = fetch_text(url, timeout=30.0).splitlines()
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        toks = s.split()
        # Expected columns: objname, j2000, S/link, E/link, seq, slen, date, mode, fiber_b, exptime, sn26, ...
        if len(toks) < 11:
            continue
        # Locate J2000 tag
        j_idx = next((i for i, t in enumerate(toks) if re.match(r"^J\d{6}", t)), None)
        if j_idx is None:
            continue
        coords = parse_j2000_tag(toks[j_idx])
        if coords is None:
            continue
        sep = sky_sep_arcsec(ra_ref, dec_ref, coords[0], coords[1])
        if sep > 300.0:
            continue
        # Locate YYYY-MM-DD token
        d_idx = next((i for i in range(j_idx + 1, min(len(toks), j_idx + 8)) if re.match(r"^\d{4}-\d{2}-\d{2}$", toks[i])), None)
        if d_idx is None or d_idx < 2 or d_idx + 4 >= len(toks):
            continue
        seq = toks[d_idx - 2]
        if not seq.isdigit():
            continue
        date_str = toks[d_idx]
        if date_str > OBS_RELEASE_CUTOFF_ISO:
            continue
        mode = toks[d_idx + 1]
        fiber_b = toks[d_idx + 2]
        if mode != "HR":
            continue
        try:
            exptime = float(toks[d_idx + 3])
            sn26 = float(toks[d_idx + 4])
        except ValueError:
            continue
        if exptime < 2.0 or sn26 < 10.0:
            continue
        dp_id = f"SOPHIE_{seq}"
        if dp_id in excl_dp_ids or dp_id in seen:
            continue
        seen.add(dp_id)
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
        mjd_est = dt.timestamp() / 86400.0 + 2440587.5 - 2400000.5 + 0.05
        out.append({
            "dp_id": dp_id,
            "seq": seq,
            "target_name_archive": " ".join(toks[:j_idx]),
            "s_ra": coords[0],
            "s_dec": coords[1],
            "mjd_obs": mjd_est,
            "mjd_mid": mjd_est + exptime / 172800.0,
            "exptime": exptime,
            "sn": sn26,
            "fiber_b": fiber_b,
            "em_min_a": 3872.0,
            "em_max_a": 6943.0,
            "em_res_power": 75000.0,
            "obs_release_date": f"{date_str}T00:00:00Z",
            "this_url": f"{SOPHIE_CGI}?c=i&a=mime:application/fits&o=sophie:[s1d,{seq}]",
            "aux_url": f"{SOPHIE_CGI}?c=i&a=mime:application/fits&o=sophie:[e2ds,{seq}]",
            "aux_category": f"SOPHIE_E2DS_FIBERB_{fiber_b}",
            "zfd_url": f"{SOPHIE_CGI}?n=sophie&c=i&z=fd&o=sophie:[e2ds,{seq}]",
            "this_bytes_est": 2_470_000,
            "aux_bytes_est": 4_230_000,
        })
    return sorted(out, key=lambda x: x["mjd_mid"])


def enrich_sophie_item(item: dict[str, Any]) -> dict[str, Any] | None:
    try:
        raw = fetch_text(item["zfd_url"], timeout=25.0)
    except Exception:
        return None
    cards = parse_ohp_zfd_header(raw)
    dpr = cards.get("OHP DPR TYPE", "").upper()
    if any(bad in dpr for bad in ("DARK,DARK", "FLAT", "BIAS", "WAVE,WAVE")):
        return None
    if not ("STAR" in dpr or "OBJ" in dpr or dpr == ""):
        return None
    mjd_s = cards.get("OHP OBS MJD")
    bjd_s = cards.get("OHP DRS BJD")
    if mjd_s is None:
        return None
    mjd_obs = float(mjd_s)
    mjd_mid = mjd_obs + item["exptime"] / 172800.0
    bjd_mid = float(bjd_s) if bjd_s else mjd_to_bjd_est(mjd_mid, item["s_ra"], item["s_dec"])
    out = dict(item)
    out["mjd_obs"] = mjd_obs
    out["mjd_mid"] = mjd_mid
    out["bjd_mid_approx"] = bjd_mid
    out["dpr_type"] = dpr
    return out


def query_elodie_table(obj_query: str, ra_ref: float, dec_ref: float, excl_dp_ids: set[str]) -> list[dict[str, Any]]:
    url = f"{ELODIE_CGI}?n=e500&c=o&a=t&o={urllib.parse.quote(obj_query)}"
    lines = fetch_text(url, timeout=30.0).splitlines()
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        toks = s.split()
        j_idx = next((i for i, t in enumerate(toks) if re.match(r"^J\d{6}", t)), None)
        if j_idx is None:
            continue
        coords = parse_j2000_tag(toks[j_idx])
        if coords is None:
            continue
        sep = sky_sep_arcsec(ra_ref, dec_ref, coords[0], coords[1])
        if sep > 300.0:
            continue
        d_idx = next((i for i in range(j_idx + 1, min(len(toks), j_idx + 6)) if re.match(r"^\d{8}$", toks[i])), None)
        if d_idx is None or d_idx + 4 >= len(toks):
            continue
        dataset = toks[d_idx]
        imanum = toks[d_idx + 1]
        imatyp = toks[d_idx + 2]
        if imatyp not in ("OBJO", "OBJOd", "OBTHs"):
            continue
        try:
            exptime = float(toks[d_idx + 3])
            sn = float(toks[d_idx + 4])
        except ValueError:
            continue
        if exptime < 2.0 or sn < 20.0:
            continue
        dp_id = f"ELODIE_{dataset}_{imanum}"
        if dp_id in excl_dp_ids or dp_id in seen:
            continue
        seen.add(dp_id)
        dt = datetime.datetime.strptime(dataset, "%Y%m%d").replace(tzinfo=datetime.timezone.utc)
        mjd_est = dt.timestamp() / 86400.0 + 2440587.5 - 2400000.5 + 0.05
        out.append({
            "dp_id": dp_id,
            "dataset": dataset,
            "imanum": imanum,
            "imatyp": imatyp,
            "target_name_archive": " ".join(toks[:j_idx]),
            "s_ra": coords[0],
            "s_dec": coords[1],
            "mjd_obs": mjd_est,
            "mjd_mid": mjd_est + exptime / 172800.0,
            "exptime": exptime,
            "sn": sn,
            "em_min_a": 4000.0,
            "em_max_a": 6800.0,
            "em_res_power": 42000.0,
            "obs_release_date": f"{dataset[:4]}-{dataset[4:6]}-{dataset[6:8]}T00:00:00Z",
            "this_url": f"{ELODIE_CGI}?n=e500&c=i&z=s1d&a=mime:application/fits&o=elodie:{dataset}/{imanum}",
            "aux_url": "",
            "aux_category": f"ELODIE_IMATYP_{imatyp}",
            "zfd_url": f"{ELODIE_CGI}?n=e500&c=i&z=fd&o=elodie:{dataset}/{imanum}",
            "this_bytes_est": 480_000,
            "aux_bytes_est": 0,
        })
    return sorted(out, key=lambda x: x["mjd_mid"])


def enrich_elodie_item(item: dict[str, Any]) -> dict[str, Any] | None:
    try:
        raw = fetch_text(item["zfd_url"], timeout=25.0)
    except Exception:
        return None
    cards = parse_ohp_zfd_header(raw)
    mjd_s = cards.get("MJD-OBS")
    if mjd_s is None:
        return None
    mjd_obs = float(mjd_s)
    expt = float(cards.get("EXPTIME", item["exptime"]))
    mjd_mid = mjd_obs + expt / 172800.0
    out = dict(item)
    out["mjd_obs"] = mjd_obs
    out["mjd_mid"] = mjd_mid
    out["exptime"] = expt
    out["bjd_mid_approx"] = mjd_to_bjd_est(mjd_mid, item["s_ra"], item["s_dec"])
    return out


def query_espadons_cadc(
    spec: dict[str, Any],
    ra16: float,
    dec16: float,
    pmra: float,
    pmdec: float,
    excl_dp_ids: set[str],
) -> list[dict[str, Any]]:
    names = spec["cadc_names"]
    allowed_lower = {n.strip().lower() for n in names}
    in_clause = ",".join(f"'{n}'" for n in names)
    max_sep = float(spec.get("max_cadc_sep_arcsec", 120.0))
    sql = f"""SELECT obs_id, obs_publisher_did, target_name, s_ra, s_dec, t_min, t_max, t_exptime, em_min, em_max, em_res_power, obs_release_date
FROM ivoa.ObsCore
WHERE obs_collection = 'CFHT'
  AND instrument_name LIKE '%ESPaDOnS%'
  AND obs_publisher_did LIKE '%i'
  AND t_exptime >= 2.0
  AND obs_release_date <= '{OBS_RELEASE_CUTOFF_ISO}'
  AND target_name IN ({in_clause})
  AND 1 = CONTAINS(POINT('ICRS', s_ra, s_dec), CIRCLE('ICRS', {ra16:.6f}, {dec16:.6f}, 0.08))
ORDER BY t_min ASC"""
    crows = tap_csv(CADC_TAP, sql, timeout=45.0)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    cosd = max(0.1, math.cos(math.radians(dec16)))
    for cr in crows:
        obs_id = cr["obs_id"].strip()
        dp_id = f"{obs_id}i"
        tname = cr["target_name"].strip()
        if tname.lower() not in allowed_lower:
            continue
        if dp_id in excl_dp_ids or dp_id in seen:
            continue
        tmin, tmax = float(cr["t_min"]), float(cr["t_max"])
        mjd_mid = 0.5 * (tmin + tmax)
        yr = 2000.0 + (mjd_mid - 51544.5) / 365.25
        dt_yr = yr - 2016.0
        ra_ep = ra16 + (dt_yr * pmra) / (3600000.0 * cosd)
        dec_ep = dec16 + (dt_yr * pmdec) / 3600000.0
        sra, sdec = float(cr["s_ra"]), float(cr["s_dec"])
        if sky_sep_arcsec(sra, sdec, ra_ep, dec_ep) > max_sep and sky_sep_arcsec(sra, sdec, ra16, dec16) > max_sep:
            continue
        seen.add(dp_id)
        res_p = float(cr["em_res_power"]) if cr.get("em_res_power") else 65000.0
        out.append({
            "dp_id": dp_id,
            "obs_id": obs_id,
            "target_name_archive": tname,
            "s_ra": sra,
            "s_dec": sdec,
            "mjd_obs": tmin,
            "mjd_mid": mjd_mid,
            "exptime": float(cr["t_exptime"]),
            "em_min_a": 3700.0,
            "em_max_a": 10480.0,
            "em_res_power": res_p,
            "obs_release_date": cr["obs_release_date"].strip(),
            "this_url": f"https://cadc-west-01.canfar.net/raven/files/cadc:CFHT/{dp_id}.fits",
            "aux_url": "",
            "aux_category": "",
            "bjd_mid_approx": mjd_to_bjd_est(mjd_mid, sra, sdec),
            "this_bytes_est": 5_400_000,
            "aux_bytes_est": 0,
        })
    return sorted(out, key=lambda x: x["mjd_mid"])


def signed_phase(bjd: float, t0: float, orb_per: float) -> float:
    return ((bjd - t0) / orb_per + 0.5) % 1.0 - 0.5


def _select_time_spaced(items: list[dict[str, Any]], n_target: int) -> list[dict[str, Any]]:
    if len(items) <= n_target:
        return sorted(items, key=lambda x: x["mjd_mid"])
    ordered = sorted(items, key=lambda x: x["mjd_mid"])
    idxs = sorted({min(len(ordered) - 1, int(round(i * (len(ordered) - 1) / max(1, n_target - 1)))) for i in range(n_target)})
    while len(idxs) < n_target:
        for j in range(len(ordered)):
            if j not in idxs:
                idxs.append(j)
                if len(idxs) == n_target:
                    break
    return [ordered[j] for j in sorted(idxs)]


def build() -> None:
    if INP_DIR.exists():
        raise RuntimeError(f"STRICT PROSPECTIVE LOCK VIOLATION: {INP_DIR} already exists before cohort lock!")

    print("=== Phase D088 Build Cohort (NORTHERN_RADIO23_AND_ALLSKY_COMB_V4_1_V3_9) ===", flush=True)

    # 1. Load prior exclusion registry (C001-C037 + D001-D087 + format checks)
    pe_d87 = json.loads((D087_WS / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    excl_dp_ids: set[str] = set(pe_d87["excluded_dp_ids"])
    excl_coords: list[dict[str, Any]] = list(pe_d87["excluded_targets_coordinate_registry"])
    seen_coord_labels = {ec["label"] for ec in excl_coords}

    with (D087_WS / "FROZEN_COHORT_D087.csv").open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            excl_dp_ids.add(row["dp_id"])
            if row["panchromatic_bridge"] != "True":
                lbl = f"{row['canonical_target']}(D087)"
                if lbl not in seen_coord_labels:
                    seen_coord_labels.add(lbl)
                    excl_coords.append({
                        "label": lbl,
                        "ra_deg": round(float(row["s_ra"]), 6),
                        "dec_deg": round(float(row["s_dec"]), 6),
                    })

    # Add D088 Vega format check exclusion
    for dpid in VEGA_FORMAT_CHECK["dp_ids"]:
        excl_dp_ids.add(dpid)
    if VEGA_FORMAT_CHECK["label"] not in seen_coord_labels:
        excl_coords.append({
            "label": VEGA_FORMAT_CHECK["label"],
            "ra_deg": VEGA_FORMAT_CHECK["ra_deg"],
            "dec_deg": VEGA_FORMAT_CHECK["dec_deg"],
        })

    # 2. Query Gaia DR3 batch
    gids = [s["gaia_source_id"] for s in TARGET_SPECS if s["gaia_source_id"] is not None]
    gaia_cols = (
        "source_id,ra,dec,parallax,pmra,pmdec,"
        "phot_g_mean_mag,phot_bp_mean_mag,phot_rp_mean_mag,bp_rp,"
        "radial_velocity,teff_gspphot,mh_gspphot"
    )
    gaia_sql = f"SELECT {gaia_cols} FROM gaiadr3.gaia_source WHERE source_id IN ({','.join(map(str, gids))})"
    gaia_res = tap_json(GAIA_TAP, {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "json", "QUERY": gaia_sql}, timeout=60.0)
    col_names = [m["name"] for m in gaia_res["metadata"]]
    gaia_by_id: dict[int, dict[str, Any]] = {}
    for row in gaia_res["data"]:
        rec = dict(zip(col_names, row))
        gaia_by_id[int(rec["source_id"])] = rec
    if len(gaia_by_id) != len(gids):
        raise RuntimeError(f"Expected {len(gids)} Gaia DR3 stars, got {len(gaia_by_id)}")

    # 3. Query NASA pscomppars
    gaia_dr3_str_list = ",".join(f"'Gaia DR3 {gid}'" for gid in gids)
    nasa_sql = (
        "SELECT hostname, gaia_dr3_id, sy_pnum, pl_name, tran_flag, pl_orbper, pl_tranmid, "
        "pl_orbtper, pl_orbeccen, pl_orblper, pl_rvamp, ra, dec, sy_dist, sy_vmag, "
        "sy_jmag, sy_hmag, sy_kmag, st_teff, st_met, st_mass, st_radv "
        "FROM pscomppars "
        "WHERE hostname IN ('47 UMa','HD 154345','psi1 Dra B','GJ 625','Gl 686','GJ 176',"
        "'HD 33564','HD 127506','bet UMi','Gl 49','GJ 15 A','GJ 687','GJ 411',"
        "'HD 109358','HD 114710','HD 6582','HD 30652','HD 39587','HD 161797') "
        f"OR gaia_dr3_id IN ({gaia_dr3_str_list})"
    )
    nasa_rows = tap_json(NASA_TAP, {"query": nasa_sql, "format": "json"}, timeout=60.0, use_get=True)
    nasa_by_gid: dict[int, list[dict[str, Any]]] = {}
    nasa_by_host: dict[str, list[dict[str, Any]]] = {}
    for nr in nasa_rows:
        hn = str(nr.get("hostname") or "").strip()
        nasa_by_host.setdefault(hn, []).append(nr)
        gd = str(nr.get("gaia_dr3_id") or "")
        if gd.startswith("Gaia DR3 "):
            nasa_by_gid.setdefault(int(gd.split()[-1]), []).append(nr)

    # 4. Query 2MASS PSC + Archival tables per target
    def prepare_star(spec: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        st = spec["canonical_target"]
        gid = spec["gaia_source_id"]
        if gid is not None:
            g = gaia_by_id[gid]
            ra16, dec16 = float(g["ra"]), float(g["dec"])
            pmra = float(g["pmra"] or 0.0)
            pmdec = float(g["pmdec"] or 0.0)
            cosd = max(0.1, math.cos(math.radians(dec16)))
            ra00 = ra16 - (16.0 * pmra) / (3600000.0 * cosd)
            dec00 = dec16 - (16.0 * pmdec) / 3600000.0
            dist_pc = 1000.0 / float(g["parallax"])
            within_10pc = dist_pc < 10.0
            g_mag = float(g["phot_g_mean_mag"])
            bp_mag = float(g["phot_bp_mean_mag"]) if g.get("phot_bp_mean_mag") is not None else float("nan")
            rp_mag = float(g["phot_rp_mean_mag"]) if g.get("phot_rp_mean_mag") is not None else float("nan")
            bp_rp = float(g["bp_rp"]) if g.get("bp_rp") is not None else (bp_mag - rp_mag)
            vmag_val = None
        else:
            # BETUMI (HIP 72607)
            ra16, dec16 = float(spec["ra_lit"]), float(spec["dec_lit"])
            ra00, dec00 = ra16, dec16
            pmra, pmdec = float(spec["pmra_lit"]), float(spec["pmdec_lit"])
            dist_pc = float(spec["dist_lit"])
            within_10pc = dist_pc < 10.0
            g_mag, bp_mag, rp_mag, bp_rp = float("nan"), float("nan"), float("nan"), float("nan")
            vmag_val = float(spec["vmag_lit"])

        tm_sql = (
            f"SELECT TOP 2 mainid, jmag, hmag, kmag, "
            f"DISTANCE(POINT('ICRS', raj2000, dej2000), POINT('ICRS', {ra00:.6f}, {dec00:.6f}))*3600.0 AS sep "
            f"FROM twomass.data "
            f"WHERE 1=CONTAINS(POINT('ICRS', raj2000, dej2000), CIRCLE('ICRS', {ra00:.6f}, {dec00:.6f}, 0.025)) "
            f"ORDER BY sep ASC"
        )
        tm_rows = tap_json(GAVO_TAP, {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "json", "QUERY": tm_sql}, timeout=45.0)["data"]
        if not tm_rows or tm_rows[0][1] is None:
            raise RuntimeError(f"2MASS PSC lookup failed for {st}")
        twomass_id = str(tm_rows[0][0]).strip()
        j_mag = float(tm_rows[0][1])
        h_mag = float(tm_rows[0][2]) if tm_rows[0][2] is not None else float("nan")
        ks_mag = float(tm_rows[0][3]) if tm_rows[0][3] is not None else float("nan")

        # NASA exoplanet match
        nr_list = nasa_by_host.get(spec.get("nasa_hostname", ""), [])
        if not nr_list and gid is not None:
            nr_list = nasa_by_gid.get(gid, [])
        nr = nr_list[0] if nr_list else None
        n_exo = int(nr["sy_pnum"]) if nr and nr.get("sy_pnum") is not None else 0
        if spec["role"] == "CONTROL" and n_exo != 0:
            raise RuntimeError(f"CONTROL star {st} has n_exo={n_exo}!")
        has_transit = any(int(r.get("tran_flag") or 0) == 1 for r in nr_list) if nr_list else False

        if nr and nr.get("st_teff") is not None:
            teff_k = float(nr["st_teff"])
        elif gid is not None and gaia_by_id[gid].get("teff_gspphot") is not None:
            teff_k = float(gaia_by_id[gid]["teff_gspphot"])
        else:
            teff_k = float(spec["teff_lit"])

        if nr and nr.get("st_met") is not None:
            mh_dex = float(nr["st_met"])
        elif gid is not None and gaia_by_id[gid].get("mh_gspphot") is not None:
            mh_dex = float(gaia_by_id[gid]["mh_gspphot"])
        else:
            mh_dex = float(spec["mh_lit"])

        if nr and nr.get("st_mass") is not None:
            st_mass = float(nr["st_mass"])
        else:
            st_mass = float(spec["mass_lit"])

        if gid is not None and gaia_by_id[gid].get("radial_velocity") is not None:
            rv_kms = float(gaia_by_id[gid]["radial_velocity"])
        elif nr and nr.get("st_radv") is not None:
            rv_kms = float(nr["st_radv"])
        else:
            rv_kms = float(spec["rv_lit"])

        # Sky separation verification vs all prior coordinates
        min_sep = 1e9
        nearest = ""
        for ec in excl_coords:
            sep = sky_sep_arcsec(ra16, dec16, ec["ra_deg"], ec["dec_deg"])
            if sep < min_sep:
                min_sep, nearest = sep, ec["label"]
        if (not spec["panchromatic_bridge"]) and min_sep < 5000.0:
            raise RuntimeError(f"Brand-new star {st} too close to prior {nearest}: {min_sep:.1f}\"")

        # Archival metadata query
        inst = spec["instrument"]
        cands: list[dict[str, Any]] = []
        if inst == "OHP_SOPHIE":
            for q in spec["ohp_queries"]:
                cands.extend(query_sophie_table(q, ra16, dec16, excl_dp_ids))
        elif inst == "OHP_ELODIE":
            for q in spec["ohp_queries"]:
                cands.extend(query_elodie_table(q, ra16, dec16, excl_dp_ids))
        elif inst == "CFHT_ESPADONS":
            cands = query_espadons_cadc(spec, ra16, dec16, pmra, pmdec, excl_dp_ids)
        else:
            raise ValueError(inst)

        meta = {
            "star": st,
            "gaia_source_id": str(gid) if gid is not None else "",
            "twomass_id": twomass_id,
            "ra_deg": ra16,
            "dec_deg": dec16,
            "dist_pc": dist_pc,
            "within_10pc": within_10pc,
            "g_mag": g_mag,
            "bp_mag": bp_mag,
            "rp_mag": rp_mag,
            "bp_rp": bp_rp,
            "vmag": vmag_val,
            "j_mag": j_mag,
            "h_mag": h_mag,
            "ks_mag": ks_mag,
            "teff_k": teff_k,
            "mh_dex": mh_dex,
            "st_mass": st_mass,
            "prior_rv_kms": rv_kms,
            "n_exoplanets": n_exo,
            "has_transiting_planet": has_transit,
            "min_prior_sep_arcsec": min_sep,
            "nearest_prior_target": nearest,
            "nasa_nr": nr_list,
        }
        return meta, cands

    print("  Querying 2MASS PSC + OHP/CADC metadata across 25 targets...", flush=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        raw_results = list(ex.map(prepare_star, TARGET_SPECS))

    # 5. Enrich OHP candidates via exact z=fd FITS headers & select locked exposures
    frozen_rows: list[dict[str, Any]] = []
    orbital_campaigns: dict[str, Any] = {}
    star_meta_list: list[dict[str, Any]] = []
    total_proj_bytes = 0

    for spec, (meta, cands) in zip(TARGET_SPECS, raw_results):
        st = spec["canonical_target"]
        inst = spec["instrument"]
        n_target = spec["n_target_exposures"]
        star_meta_list.append((spec, meta))

        if inst in ("OHP_SOPHIE", "OHP_ELODIE"):
            # Subsample evenly across time up to 32 candidates (preserving long baselines) before z=fd
            if len(cands) > 32:
                idxs = sorted({int(round(i * (len(cands) - 1) / 31.0)) for i in range(32)})
                pool = [cands[j] for j in idxs]
            else:
                pool = list(cands)
            fn = enrich_sophie_item if inst == "OHP_SOPHIE" else enrich_elodie_item
            with ThreadPoolExecutor(max_workers=8) as ex:
                enriched = [r for r in ex.map(fn, pool) if r is not None]
            cands = sorted(enriched, key=lambda x: x["mjd_mid"])

        if len(cands) < n_target:
            raise RuntimeError(f"Star {st} ({inst}) yielded only {len(cands)} < {n_target} clean candidates!")

        if spec["orbital_campaign"]:
            per = float(spec["orb_per_days"])
            ecc = float(spec["orb_e"])
            t0_fix = spec.get("orb_t0_bjd")
            if t0_fix is None:
                # Choose earliest candidate yielding >= 4 IN_WINDOW and >= 4 OUT_OF_WINDOW
                chosen_t0 = None
                for cand in cands:
                    t_try = float(cand["bjd_mid_approx"])
                    in_c = [c for c in cands if abs(signed_phase(float(c["bjd_mid_approx"]), t_try, per)) <= 0.16]
                    out_c = [c for c in cands if abs(signed_phase(float(c["bjd_mid_approx"]), t_try, per)) > 0.16]
                    if len(in_c) >= 4 and len(out_c) >= 4:
                        chosen_t0 = t_try
                        break
                if chosen_t0 is None:
                    raise RuntimeError(f"Could not find balanced t0 for {st}")
                t0 = chosen_t0
            else:
                t0 = float(t0_fix)

            in_cands = [c for c in cands if abs(signed_phase(float(c["bjd_mid_approx"]), t0, per)) <= 0.16]
            out_cands = [c for c in cands if abs(signed_phase(float(c["bjd_mid_approx"]), t0, per)) > 0.16]
            if len(in_cands) < 4 or len(out_cands) < 4:
                raise RuntimeError(f"Orbital campaign {st}: in={len(in_cands)}, out={len(out_cands)} (<4)")
            in_cands_ph = sorted(in_cands, key=lambda c: signed_phase(float(c["bjd_mid_approx"]), t0, per))
            in_idxs = sorted({min(len(in_cands_ph) - 1, int(round(i * (len(in_cands_ph) - 1) / 3.0))) for i in range(4)})
            while len(in_idxs) < 4:
                for j in range(len(in_cands_ph)):
                    if j not in in_idxs:
                        in_idxs.append(j)
                        if len(in_idxs) == 4:
                            break
            sel_in = [in_cands_ph[j] for j in sorted(in_idxs)]
            sel_out = _select_time_spaced(out_cands, 4)
            selected = sorted(sel_in + sel_out, key=lambda x: x["mjd_mid"])

            kp_kms = compute_keplerian_kp_kms(meta["st_mass"], per, ecc)
            orb_exps = []
            in_rvs = []
            for rank, item in enumerate(selected, 1):
                bjd_m = float(item["bjd_mid_approx"])
                ph_s, orb_rv = compute_planet_orbital_rv_kms(bjd_m, t0, per, kp_kms)
                win = "IN_WINDOW" if abs(ph_s) <= 0.16 else "OUT_OF_WINDOW"
                item["phase_window"] = win
                item["orbital_phase_signed"] = ph_s
                item["planet_orbital_rv_kms"] = orb_rv
                if win == "IN_WINDOW":
                    in_rvs.append(orb_rv)
                orb_exps.append({
                    "dp_id": item["dp_id"],
                    "epoch_rank": rank,
                    "bjd_mid_approx": round(bjd_m, 7),
                    "phase_window": win,
                    "orbital_phase_signed": round(ph_s, 7),
                    "planet_orbital_rv_kms": round(orb_rv, 5),
                })
            orbital_campaigns[st] = {
                "star": st,
                "common_name": spec["common_name"],
                "instrument": inst,
                "role": spec["role"],
                "subrole": spec["subrole"],
                "planet_name": spec["planet_name"],
                "transiting": False,
                "window_mode": "CONJUNCTION",
                "half_phase_window": 0.16,
                "st_mass_msun": round(meta["st_mass"], 4),
                "orbper_days": per,
                "t0_bjd": round(t0, 6),
                "ecc": ecc,
                "kp_kms": round(kp_kms, 4),
                "orbital_dv_span_kms": round(max(in_rvs) - min(in_rvs), 4),
                "n_in_window": 4,
                "n_out_of_window": 4,
                "exposures": orb_exps,
            }
        else:
            selected = _select_time_spaced(cands, n_target)
            for item in selected:
                item["phase_window"] = "MULTI_EPOCH"
                item["orbital_phase_signed"] = 0.0
                item["planet_orbital_rv_kms"] = 0.0

        # Probe exact HEAD bytes on selected URLs where supported
        for rank, item in enumerate(selected, 1):
            tb = probe_head_bytes(item["this_url"], int(item["this_bytes_est"]))
            ab = probe_head_bytes(item["aux_url"], int(item["aux_bytes_est"])) if item["aux_url"] else 0
            total_proj_bytes += tb + ab
            frozen_rows.append({
                "phase_id": "D088",
                "instrument": inst,
                "canonical_target": st,
                "common_name": spec["common_name"],
                "role": spec["role"],
                "subrole": spec["subrole"],
                "panchromatic_bridge": str(spec["panchromatic_bridge"]),
                "radio_mm_id": spec["radio_mm_id"],
                "gaia_source_id": meta["gaia_source_id"],
                "twomass_id": meta["twomass_id"],
                "dp_id": item["dp_id"],
                "target_name_archive": item["target_name_archive"],
                "this_url": item["this_url"],
                "this_bytes": tb,
                "aux_url": item["aux_url"],
                "aux_bytes": ab,
                "aux_category": item["aux_category"],
                "epoch_rank": rank,
                "phase_window": item["phase_window"],
                "orbital_phase_signed": f"{item['orbital_phase_signed']:.7f}",
                "planet_orbital_rv_kms": f"{item['planet_orbital_rv_kms']:.5f}",
                "s_ra": f"{item['s_ra']:.7f}",
                "s_dec": f"{item['s_dec']:.7f}",
                "mjd_obs": f"{item['mjd_obs']:.7f}",
                "mjd_mid": f"{item['mjd_mid']:.7f}",
                "t_exptime": f"{item['exptime']:.2f}",
                "em_min_a": f"{item['em_min_a']:.1f}",
                "em_max_a": f"{item['em_max_a']:.1f}",
                "em_res_power": f"{item['em_res_power']:.1f}",
                "obs_release_date": item["obs_release_date"],
                "dist_pc": f"{meta['dist_pc']:.6f}",
                "within_10pc": str(meta["within_10pc"]),
                "phot_g_mag": "" if math.isnan(meta["g_mag"]) else f"{meta['g_mag']:.5f}",
                "phot_bp_mag": "" if math.isnan(meta["bp_mag"]) else f"{meta['bp_mag']:.5f}",
                "phot_rp_mag": "" if math.isnan(meta["rp_mag"]) else f"{meta['rp_mag']:.5f}",
                "bp_rp": "" if math.isnan(meta["bp_rp"]) else f"{meta['bp_rp']:.5f}",
                "vmag": "" if meta["vmag"] is None else f"{meta['vmag']:.5f}",
                "j_mag": f"{meta['j_mag']:.4f}",
                "h_mag": "" if math.isnan(meta["h_mag"]) else f"{meta['h_mag']:.4f}",
                "ks_mag": "" if math.isnan(meta["ks_mag"]) else f"{meta['ks_mag']:.4f}",
                "teff_k": f"{meta['teff_k']:.1f}",
                "mh_dex": f"{meta['mh_dex']:.4f}",
                "stellar_mass_msun": f"{meta['st_mass']:.4f}",
                "prior_rv_kms": f"{meta['prior_rv_kms']:.5f}",
                "n_exoplanets": meta["n_exoplanets"],
                "has_transiting_planet": str(meta["has_transiting_planet"]),
                "min_prior_sep_arcsec": f"{meta['min_prior_sep_arcsec']:.2f}",
            })

    proj_gib = total_proj_bytes / (1024.0**3)
    if proj_gib > MAX_PROJ_DOWNLOAD_GIB:
        raise RuntimeError(f"Projected download {proj_gib:.3f} GiB exceeds safety bound {MAX_PROJ_DOWNLOAD_GIB} GiB")

    # 6. Check intra-D088 brand-new separations & overlaps
    brand_new_meta = [(s, m) for s, m in star_meta_list if not s["panchromatic_bridge"]]
    min_intra = 1e9
    for i in range(len(brand_new_meta)):
        for j in range(i + 1, len(brand_new_meta)):
            sep = sky_sep_arcsec(
                brand_new_meta[i][1]["ra_deg"],
                brand_new_meta[i][1]["dec_deg"],
                brand_new_meta[j][1]["ra_deg"],
                brand_new_meta[j][1]["dec_deg"],
            )
            min_intra = min(min_intra, sep)
    if min_intra < 300.0:
        raise RuntimeError(f"Intra-D088 brand-new sky separation too tight: {min_intra:.1f}\"")

    d088_dp_ids = [r["dp_id"] for r in frozen_rows]
    overlap_cnt = len(set(d088_dp_ids) & excl_dp_ids)
    if overlap_cnt != 0:
        raise RuntimeError(f"dp_id overlap detected: {overlap_cnt}")

    # Write FROZEN_COHORT_D088.csv
    fieldnames = list(frozen_rows[0].keys())
    with (WS / "FROZEN_COHORT_D088.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(frozen_rows)

    # Write ORBITAL_CAMPAIGNS_AND_KINEMATICS.json
    orb_doc = {
        "schema": "PANCHROM_V3_9_ORBITAL_CAMPAIGNS",
        "phase_id": "D088",
        "instruments": ["OHP_SOPHIE", "OHP_ELODIE", "CFHT_ESPADONS"],
        "n_campaigns": len(orbital_campaigns),
        "n_science_orbital_campaigns": sum(1 for c in orbital_campaigns.values() if c["role"] == "SCIENCE"),
        "n_control_null_campaigns": sum(1 for c in orbital_campaigns.values() if c["role"] == "CONTROL"),
        "campaigns": orbital_campaigns,
    }
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_doc, indent=2) + "\n", encoding="utf-8")

    # Write PRIOR_EXCLUSION_VERIFICATION.json
    star_sep_ver = []
    for s, m in star_meta_list:
        star_sep_ver.append({
            "canonical_target": s["canonical_target"],
            "common_name": s["common_name"],
            "instrument": s["instrument"],
            "role": s["role"],
            "panchromatic_bridge": s["panchromatic_bridge"],
            "dist_pc": round(m["dist_pc"], 5),
            "within_10pc": m["within_10pc"],
            "ra_deg": round(m["ra_deg"], 6),
            "dec_deg": round(m["dec_deg"], 6),
            "nearest_prior_target": m["nearest_prior_target"],
            "min_sky_separation_arcsec": round(m["min_prior_sep_arcsec"], 2),
            "status": "INTENTIONAL_PANCHROMATIC_BRIDGE" if s["panchromatic_bridge"] else "VERIFIED_BRAND_NEW_STAR",
        })
    pe_doc = {
        "schema": "D088_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D088",
        "verified_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prior_phases_covered": "C001-C037 + D001-D087",
        "format_check_excluded_targets": pe_d87["format_check_excluded_targets"] + [VEGA_FORMAT_CHECK["label"]],
        "format_check_excluded_dp_ids": pe_d87["format_check_excluded_dp_ids"] + VEGA_FORMAT_CHECK["dp_ids"],
        "n_prior_excluded_coords": len(excl_coords),
        "n_prior_excluded_dp_ids": len(excl_dp_ids),
        "d088_total_stars": len(TARGET_SPECS),
        "d088_brand_new_unique_stars": len(brand_new_meta),
        "d088_panchromatic_bridge_stars": sum(1 for s in TARGET_SPECS if s["panchromatic_bridge"]),
        "d088_brand_new_within_10pc": sum(1 for s, m in brand_new_meta if m["within_10pc"]),
        "d088_total_exposures": len(frozen_rows),
        "d088_projected_download_bytes": total_proj_bytes,
        "d088_projected_download_gib": round(proj_gib, 4),
        "d088_dp_id_overlap_count": overlap_cnt,
        "min_brand_new_sky_separation_arcsec": round(min(m["min_prior_sep_arcsec"] for _, m in brand_new_meta), 2),
        "min_intra_d088_brand_new_separation_arcsec": round(min_intra, 2),
        "star_separation_verification": star_sep_ver,
        "excluded_dp_ids": sorted(excl_dp_ids),
        "excluded_targets_coordinate_registry": excl_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pe_doc, indent=2) + "\n", encoding="utf-8")

    # Write PRIOR_V3_PHASES_SNAPSHOT.json (freezing D079-D087 = 200 stars, 103 <10pc, 17 bridges)
    d87_sum = json.loads((D087_WS / "results" / "SUMMARY.json").read_text(encoding="utf-8"))
    d87_snap = json.loads((D087_WS / "PRIOR_V3_PHASES_SNAPSHOT.json").read_text(encoding="utf-8"))
    with (D087_WS / "results" / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_200STARS.csv").open(newline="", encoding="utf-8") as fh:
        unified_200 = list(csv.DictReader(fh))
    with (D087_WS / "results" / "PANCHROMATIC_BRIDGE_17STARS.csv").open(newline="", encoding="utf-8") as fh:
        bridge_17 = list(csv.DictReader(fh))

    newly_bridged_stars = {"61CYGA", "61CYGB", "GXAND", "GJ687"}
    prior_new_bridge_ul: list[dict[str, Any]] = []
    with (D084_WS / "results" / "STAR_UPPER_LIMITS_189.csv").open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["star"] in newly_bridged_stars:
                prior_new_bridge_ul.append({
                    "phase_id": "D084",
                    "spectral_regime": "OPTICAL_FARRED_0p38_0p96um",
                    "instrument": r["instrument"],
                    "star": r["star"],
                    "common_name": r["common_name"],
                    "dist_pc": r["dist_pc"],
                    "band_id": r["band_id"],
                    "wave_A": r["wave_bary_vac_A"],
                    "ew_lim_mA": r["ew_lim_mA"],
                    "flux_lim_erg_cm2_s": r["flux_lim_erg_cm2_s"],
                    "l_iso_mw": r["l_iso_mw"],
                    "p_beam_10m_kw": r["p_beam_10m_kw"],
                    "p_beam_10m_w": r["p_beam_10m_w"],
                })

    u_synth = d87_sum["unified_200star_panchromatic_v3_synthesis"]
    snap_doc = {
        "schema": "D088_PRIOR_V3_PHASES_SNAPSHOT",
        "prior_phases": "D079-D087",
        "prior_v3_unique_stars_count": int(u_synth["unique_stars_total"]),
        "prior_v3_within_10pc_count": int(u_synth["within_10pc_unique_stars"]),
        "prior_v3_total_exposures_count": int(u_synth["total_exposures_d079_d087"]),
        "prior_v3_calibration_trials_count": int(u_synth["total_calibration_trials_d079_d087"]),
        "prior_v2_false_alarms_eliminated_total": int(u_synth["v2_false_alarms_eliminated_total"]),
        "prior_cumulative_orbital_campaigns_count": int(u_synth["cumulative_orbital_campaigns"]),
        "d087_summary_headline": d87_sum,
        "d086_summary_headline": d87_snap["d086_summary_headline"],
        "d085_summary_headline": d87_snap["d085_summary_headline"],
        "d084_summary_headline": d87_snap["d084_summary_headline"],
        "d083_summary_headline": d87_snap["d083_summary_headline"],
        "d079_d082_headlines": d87_snap["d079_d082_headlines"],
        "unified_200star_rows": unified_200,
        "d087_bridge_17star_rows": bridge_17,
        "prior_new_bridge_upper_limits": prior_new_bridge_ul,
    }
    (WS / "PRIOR_V3_PHASES_SNAPSHOT.json").write_text(json.dumps(snap_doc, indent=2) + "\n", encoding="utf-8")

    # Write MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json (updating the 6 newly bridged GBT hosts -> 23/23 radio + 1 TESS = 24)
    mm87 = json.loads((D087_WS / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").read_text(encoding="utf-8"))
    new_mm_map = {s["radio_mm_id"]: s["canonical_target"] for s in TARGET_SPECS if s["radio_mm_id"]}
    overlapping: set[str] = set(mm87["overlapping_v3_stars"])
    for sys_rec in mm87["systems"]:
        mm_id = sys_rec["mm_id"]
        if mm_id in new_mm_map:
            sys_rec["canonical_v3_star"] = new_mm_map[mm_id]
        if sys_rec.get("canonical_v3_star"):
            overlapping.add(sys_rec["canonical_v3_star"])
    mm87["schema"] = "D088_MULTIMESSENGER_RADIO_TESS_SNAPSHOT"
    mm87["n_direct_echelle_multimessenger_overlap_stars"] = len(overlapping)
    mm87["n_radio_echelle_overlaps"] = sum(1 for r in mm87["systems"] if r["mm_id"].startswith("M") and r.get("canonical_v3_star"))
    mm87["overlapping_v3_stars"] = sorted(overlapping)
    (WS / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").write_text(json.dumps(mm87, indent=2) + "\n", encoding="utf-8")

    print(
        f"DONE: {len(TARGET_SPECS)} stars ({len(brand_new_meta)} new [{pe_doc['d088_brand_new_within_10pc']} <10pc] + "
        f"{pe_doc['d088_panchromatic_bridge_stars']} bridges), {len(frozen_rows)} exposures, "
        f"{len(orbital_campaigns)} orbital campaigns, proj={proj_gib:.3f} GiB, "
        f"min_prior_sep={pe_doc['min_brand_new_sky_separation_arcsec']}\", "
        f"min_intra_sep={pe_doc['min_intra_d088_brand_new_separation_arcsec']}\", "
        f"radio_overlap={mm87['n_radio_echelle_overlaps']}/23 ({len(overlapping)} total MM overlaps).",
        flush=True,
    )


if __name__ == "__main__":
    build()
