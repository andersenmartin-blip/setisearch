#!/usr/bin/env python3
"""Metadata-only cohort builder & prospective exclusion verifier for Phase D085 (SPIROU_V3_6_AND_COMB_V4).

Queries ONLY archival metadata catalogs (CADC ivoa.ObsCore for CFHT SPIRou APERO `*t`,
ESA Gaia DR3 TAP, GAVO 2MASS PSC + CARMENES objects, NASA Exoplanet Archive pscomppars,
and MAST TICv8 for GJ 1245 B) WITHOUT downloading any science FITS spectrum files.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import csv
import datetime as dt
import io
import json
import math
from pathlib import Path
from typing import Any
import urllib.parse
import urllib.request

from v3_6_detector import (
    C_KMS,
    DAY_S,
    G_SI,
    M_SUN_KG,
    compute_keplerian_kp_kms,
    compute_planet_orbital_rv_kms,
)

WS = Path(__file__).resolve().parent
D084_WS = WS.parent / "work_northern_20261115_d084_v3_5_harpsn_carmenes_survey"
D083_BRIDGE_CSV = (
    WS.parent.parent
    / "setisearch"
    / "progress"
    / "2026-11-15-crires-d083-v3-4"
    / "PANCHROMATIC_OPTICAL_NIR_KBAND_BRIDGE.csv"
)

GAIA_TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
GAVO_TAP = "https://dc.g-vo.org/__system__/tap/run/sync"
CADC_TAP = "https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/argus/sync"
NASA_TAP = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
MAST_API = "https://mast.stsci.edu/api/v0/invoke"

AU_KM = 149597870.7

TARGET_SPECS: list[dict[str, Any]] = [
    # --- 4 Zero-Planet < 10 pc CONTROL Stars (28 exposures) ---
    {
        "canonical_target": "EVLAC",
        "common_name": "EV Lac (GJ 873)",
        "gaia_source_id": 1934263333784036736,
        "cadc_names": ["EVLac", "Gl873", "V* EV Lac"],
        "carm_id": "J22468+443",
        "role": "CONTROL",
        "subrole": "CONTROL_TIMESERIES_10PC",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "SYNTHETIC_NULL_EPHEMERIS",
            "orbper_days": 2.3117,
            "t0_bjd": None,
            "ecc": 0.0,
            "st_mass_msun": 0.336,
            "transiting": True,
        },
        "teff_lit": 3310.0,
        "mh_lit": 0.00,
        "mass_lit": 0.336,
        "rv_lit": -0.23,
    },
    {
        "canonical_target": "HD36395",
        "common_name": "HD 36395 (GJ 205)",
        "gaia_source_id": 3209938366665770752,
        "cadc_names": ["Gl205"],
        "carm_id": "J05314-036",
        "role": "CONTROL",
        "subrole": "CONTROL_TIMESERIES_10PC",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "SYNTHETIC_NULL_EPHEMERIS",
            "orbper_days": 3.14159,
            "t0_bjd": None,
            "ecc": 0.0,
            "st_mass_msun": 0.582,
            "transiting": True,
        },
        "teff_lit": 3850.0,
        "mh_lit": 0.25,
        "mass_lit": 0.582,
        "rv_lit": 8.20,
    },
    {
        "canonical_target": "GJ408",
        "common_name": "GJ 408 (Ross 104)",
        "gaia_source_id": 3988987164339438208,
        "cadc_names": ["Gl408"],
        "carm_id": "J11000+228",
        "role": "CONTROL",
        "subrole": "CONTROL_10PC",
        "panchromatic_bridge": False,
        "n_exp": 6,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3532.0,
        "mh_lit": -0.09,
        "mass_lit": 0.370,
        "rv_lit": 2.65,
    },
    {
        "canonical_target": "GJ880",
        "common_name": "GJ 880 (HD 216899)",
        "gaia_source_id": 2828928008202069376,
        "cadc_names": ["Gl880"],
        "carm_id": "J22565+165",
        "role": "CONTROL",
        "subrole": "CONTROL_10PC",
        "panchromatic_bridge": False,
        "n_exp": 6,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3798.0,
        "mh_lit": 0.12,
        "mass_lit": 0.528,
        "rv_lit": -27.87,
    },
    # --- 7 Brand-New SCIENCE Orbital Campaigns (56 exposures = 7 x 8) ---
    {
        "canonical_target": "YZCET",
        "common_name": "YZ Cet (GJ 54.1)",
        "gaia_source_id": 2358524597030794112,
        "cadc_names": ["V* YZ Cet"],
        "carm_id": "J01125-169",
        "role": "SCIENCE",
        "subrole": "EXOPLANET_ORBITAL_10PC",
        "panchromatic_bridge": False,
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
        "gaia_source_id": 2441630500517079808,
        "cadc_names": ["GJ1002"],
        "carm_id": "J00067-075",
        "role": "SCIENCE",
        "subrole": "EXOPLANET_ORBITAL_10PC",
        "panchromatic_bridge": False,
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
        "canonical_target": "HD79211",
        "common_name": "HD 79211 (GJ 338 B)",
        "gaia_source_id": 1022456104850892928,
        "cadc_names": ["Gl338B"],
        "carm_id": "J09144+526",
        "role": "SCIENCE",
        "subrole": "EXOPLANET_ORBITAL_10PC",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "GJ 338 B b",
            "orbper_days": 24.422,
            "t0_bjd": 2457521.43,
            "ecc": 0.109,
            "st_mass_msun": 0.640,
            "transiting": False,
        },
        "teff_lit": 4014.0,
        "mh_lit": -0.03,
        "mass_lit": 0.640,
        "rv_lit": 11.97,
    },
    {
        "canonical_target": "GJ436",
        "common_name": "GJ 436 (Ross 905)",
        "gaia_source_id": 4017860992519744384,
        "cadc_names": ["Gl436"],
        "carm_id": "J11421+267",
        "role": "SCIENCE",
        "subrole": "TRANSITING_ORBITAL_10PC",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "GJ 436 b",
            "orbper_days": 2.64388312,
            "t0_bjd": 2454510.80162,
            "ecc": 0.13827,
            "st_mass_msun": 0.470,
            "transiting": True,
        },
        "teff_lit": 3586.0,
        "mh_lit": 0.10,
        "mass_lit": 0.470,
        "rv_lit": 9.60,
    },
    {
        "canonical_target": "LP79118",
        "common_name": "LP 791-18 (TOI-736)",
        "gaia_source_id": 3562427951852172288,
        "cadc_names": ["LP  791-18", "LP 791-18", "TOI-736"],
        "carm_id": None,
        "role": "SCIENCE",
        "subrole": "TRANSITING_ORBITAL_HOST",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "LP 791-18 d",
            "orbper_days": 2.75485,
            "t0_bjd": 2458546.37888,
            "ecc": 0.0011,
            "st_mass_msun": 0.139,
            "transiting": True,
        },
        "teff_lit": 2960.0,
        "mh_lit": -0.09,
        "mass_lit": 0.139,
        "rv_lit": 14.10,
    },
    {
        "canonical_target": "TOI1452",
        "common_name": "TOI-1452",
        "gaia_source_id": 2264839957167921024,
        "cadc_names": ["TOI-1452"],
        "carm_id": "J19206+731S",
        "role": "SCIENCE",
        "subrole": "TRANSITING_ORBITAL_HOST",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "TOI-1452 b",
            "orbper_days": 11.06201,
            "t0_bjd": 2458691.5321,
            "ecc": 0.0,
            "st_mass_msun": 0.249,
            "transiting": True,
        },
        "teff_lit": 3185.0,
        "mh_lit": -0.07,
        "mass_lit": 0.249,
        "rv_lit": -34.94,
    },
    {
        "canonical_target": "TOI2136",
        "common_name": "TOI-2136 (LSPM J1844+3633)",
        "gaia_source_id": 2096535783864546944,
        "cadc_names": ["TOI2136", "LSPM J1844+3633"],
        "carm_id": None,
        "role": "SCIENCE",
        "subrole": "TRANSITING_ORBITAL_HOST",
        "panchromatic_bridge": False,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "TOI-2136 b",
            "orbper_days": 7.851928,
            "t0_bjd": 2459017.7043,
            "ecc": 0.0,
            "st_mass_msun": 0.340,
            "transiting": True,
        },
        "teff_lit": 3342.0,
        "mh_lit": 0.03,
        "mass_lit": 0.340,
        "rv_lit": -28.80,
    },
    # --- 14 Brand-New SCIENCE Multi-Epoch Stars (70 exposures = 14 x 5) ---
    {
        "canonical_target": "GJ1245B",
        "common_name": "GJ 1245 B (V1581 Cyg B)",
        "gaia_source_id": 2079073928612821760,
        "cadc_names": ["GJ1245B"],
        "carm_id": None,
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 2865.0,  # MAST TIC 274127413
        "mh_lit": -0.05,
        "mass_lit": 0.1154,
        "rv_lit": 3.93,
    },
    {
        "canonical_target": "GJ1691A",
        "common_name": "Stein 2051 A (GJ 169.1 A)",
        "gaia_source_id": 470826482637310080,
        "cadc_names": ["Gl169.1A"],
        "carm_id": "J04311+589",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3380.0,
        "mh_lit": -0.10,
        "mass_lit": 0.277,
        "rv_lit": 27.82,
    },
    {
        "canonical_target": "ROSS619",
        "common_name": "Ross 619 (GJ 299)",
        "gaia_source_id": 3098328182579892096,
        "cadc_names": ["Gl299"],
        "carm_id": "J08119+087",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3245.0,
        "mh_lit": -0.15,
        "mass_lit": 0.147,
        "rv_lit": 14.11,
    },
    {
        "canonical_target": "LSPMJ2146P3813",
        "common_name": "LSPM J2146+3813",
        "gaia_source_id": 1952802469918554368,
        "cadc_names": ["PM_J21463+3813"],
        "carm_id": "J21463+382",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3247.0,
        "mh_lit": -0.20,
        "mass_lit": 0.202,
        "rv_lit": -82.91,
    },
    {
        "canonical_target": "GJ382",
        "common_name": "GJ 382 (AN Sex)",
        "gaia_source_id": 3828238392559860992,
        "cadc_names": ["Gl382"],
        "carm_id": "J10122-037",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3720.0,
        "mh_lit": 0.05,
        "mass_lit": 0.497,
        "rv_lit": 7.37,
    },
    {
        "canonical_target": "GJ3378",
        "common_name": "GJ 3378 (G 192-13)",
        "gaia_source_id": 999747822484300800,
        "cadc_names": ["GJ3378"],
        "carm_id": "J06011+595",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3340.0,
        "mh_lit": -0.09,
        "mass_lit": 0.262,
        "rv_lit": 1.78,
    },
    {
        "canonical_target": "GJ1093",
        "common_name": "GJ 1093",
        "gaia_source_id": 3365063724883180288,
        "cadc_names": ["GJ1093"],
        "carm_id": "J06594+193",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3150.0,
        "mh_lit": -0.10,
        "mass_lit": 0.118,
        "rv_lit": -28.63,
    },
    {
        "canonical_target": "GJ1151",
        "common_name": "GJ 1151",
        "gaia_source_id": 786834302080370304,
        "cadc_names": ["GJ1151"],
        "carm_id": "J11509+483",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3280.0,
        "mh_lit": -0.12,
        "mass_lit": 0.1639,
        "rv_lit": -36.13,
    },
    {
        "canonical_target": "GJ300",
        "common_name": "GJ 300",
        "gaia_source_id": 5700706729031126656,
        "cadc_names": ["Gl300"],
        "carm_id": "J08126-215",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3360.0,
        "mh_lit": -0.05,
        "mass_lit": 0.262,
        "rv_lit": 8.93,
    },
    {
        "canonical_target": "ROSS318",
        "common_name": "Ross 318 (GJ 48)",
        "gaia_source_id": 533621859441169920,
        "cadc_names": ["Gl48"],
        "carm_id": "J01025+716",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3450.0,
        "mh_lit": -0.10,
        "mass_lit": 0.470,
        "rv_lit": 1.34,
    },
    {
        "canonical_target": "GJ1105",
        "common_name": "GJ 1105",
        "gaia_source_id": 922225002820369152,
        "cadc_names": ["GJ1105"],
        "carm_id": "J07582+413",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3431.0,
        "mh_lit": -0.05,
        "mass_lit": 0.256,
        "rv_lit": -20.87,
    },
    {
        "canonical_target": "GJ102",
        "common_name": "GJ 102",
        "gaia_source_id": 102162639019033600,
        "cadc_names": ["Gl102"],
        "carm_id": "J02336+249",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3313.0,
        "mh_lit": -0.15,
        "mass_lit": 0.216,
        "rv_lit": -6.48,
    },
    {
        "canonical_target": "RHOCRB",
        "common_name": "rho CrB (HD 143761)",
        "gaia_source_id": 1323427759184545536,
        "cadc_names": ["* rho CrB", "rhoCrB"],
        "carm_id": None,
        "role": "SCIENCE",
        "subrole": "RADIO_OVERLAP_HOST",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "M20_RHOCRB",
        "orbital_campaign": None,
        "teff_lit": 5817.0,
        "mh_lit": -0.20,
        "mass_lit": 1.000,
        "rv_lit": 17.88,
    },
    {
        "canonical_target": "K218",
        "common_name": "K2-18",
        "gaia_source_id": 3910747531814692736,
        "cadc_names": ["K2-18"],
        "carm_id": "J11302+076",
        "role": "SCIENCE",
        "subrole": "TEMPERATE_SUBNEPTUNE_HOST",
        "panchromatic_bridge": False,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3457.0,
        "mh_lit": 0.12,
        "mass_lit": 0.359,
        "rv_lit": 0.65,
    },
    # --- 4 Northern < 10 pc Dichroic-Bridge Stars from D084 (23 exposures = 5+8+5+5) ---
    {
        "canonical_target": "WOLF359",
        "common_name": "Wolf 359 (CN Leo)",
        "gaia_source_id": 3864972938605115520,
        "cadc_names": ["Gl406"],
        "carm_id": "J10564+070",
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_BRIDGE_NORTH_10PC",
        "panchromatic_bridge": True,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3071.0,
        "mh_lit": 0.18,
        "mass_lit": 0.095,
        "rv_lit": 19.32,
    },
    {
        "canonical_target": "LALANDE21185",
        "common_name": "Lalande 21185 (GJ 411)",
        "gaia_source_id": 762815470562110464,
        "cadc_names": ["Gl411"],
        "carm_id": "J11033+359",
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_BRIDGE_ORBITAL_10PC",
        "panchromatic_bridge": True,
        "n_exp": 8,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "GJ 411 b",
            "orbper_days": 12.9394,
            "t0_bjd": 2456305.38,
            "ecc": 0.063,
            "st_mass_msun": 0.3899,
            "transiting": False,
        },
        "teff_lit": 3557.0,
        "mh_lit": -0.3621,
        "mass_lit": 0.3899,
        "rv_lit": -85.11,
    },
    {
        "canonical_target": "DXCNC",
        "common_name": "DX Cnc (GJ 1111)",
        "gaia_source_id": 703790044252850688,
        "cadc_names": ["GJ1111"],
        "carm_id": "J08298+267",
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_BRIDGE_NORTH_10PC",
        "panchromatic_bridge": True,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3000.0,
        "mh_lit": 0.04,
        "mass_lit": 0.100,
        "rv_lit": 10.30,
    },
    {
        "canonical_target": "GJ486",
        "common_name": "GJ 486 (Wolf 437)",
        "gaia_source_id": 3735000631158990976,
        "cadc_names": ["GJ 486"],
        "carm_id": "J12479+097",
        "role": "SCIENCE",
        "subrole": "PANCHROMATIC_BRIDGE_NORTH_10PC",
        "panchromatic_bridge": True,
        "n_exp": 5,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3317.0,
        "mh_lit": -0.15,
        "mass_lit": 0.312,
        "rv_lit": 19.20,
    },
]


def sky_sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    a = math.sin(0.5 * (d2 - d1)) ** 2 + math.cos(d1) * math.cos(d2) * math.sin(0.5 * (r2 - r1)) ** 2
    return 3600.0 * math.degrees(2.0 * math.asin(min(1.0, math.sqrt(max(0.0, a)))))


def tap_csv(url: str, adql: str, timeout: float = 45.0) -> list[dict[str, str]]:
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": adql}).encode()
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "ANDERSEN-SETI-D085/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8", errors="replace"))))


def tap_json(url: str, params: dict[str, str], timeout: float = 45.0) -> Any:
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "ANDERSEN-SETI-D085/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def mjd_to_bjd_est(mjd_mid: float, ra_deg: float, dec_deg: float) -> float:
    jd = 2400000.5 + float(mjd_mid)
    t_days = jd - 2451545.0
    g_rad = math.radians((357.528 + 0.98560028 * t_days) % 360.0)
    lam_sun = math.radians((280.460 + 0.9856474 * t_days + 1.915 * math.sin(g_rad) + 0.020 * math.sin(2.0 * g_rad)) % 360.0)
    eps = math.radians(23.439 - 0.0000004 * t_days)
    r_au = 1.00014 - 0.01671 * math.cos(g_rad) - 0.00014 * math.cos(2.0 * g_rad)
    sun_x = r_au * math.cos(lam_sun)
    sun_y = r_au * math.cos(eps) * math.sin(lam_sun)
    sun_z = r_au * math.sin(eps) * math.sin(lam_sun)
    ra_r, dec_r = math.radians(ra_deg), math.radians(dec_deg)
    lt_days = (sun_x * math.cos(dec_r) * math.cos(ra_r) + sun_y * math.cos(dec_r) * math.sin(ra_r) + sun_z * math.sin(dec_r)) * (AU_KM / C_KMS) / DAY_S
    return float(jd - lt_days)


def select_night_spaced_exposures(cands: list[dict[str, Any]], n_target: int) -> list[dict[str, Any]]:
    by_night: dict[int, list[dict[str, Any]]] = {}
    for c in sorted(cands, key=lambda x: x["mjd_mid"]):
        by_night.setdefault(int(round(c["mjd_obs"])), []).append(c)
    nights = sorted(by_night.keys())
    if len(nights) >= n_target:
        picks: list[dict[str, Any]] = []
        used: set[int] = set()
        for k in range(n_target):
            idx = round(k * (len(nights) - 1) / (n_target - 1)) if n_target > 1 else 0
            while idx in used and idx + 1 < len(nights):
                idx += 1
            used.add(idx)
            grp = by_night[nights[idx]]
            picks.append(sorted(grp, key=lambda x: (-x["exptime"], x["mjd_mid"]))[0])
        return sorted(picks, key=lambda x: x["mjd_mid"])

    # Fewer distinct nights than n_target (e.g., RHOCRB=2 nights, K218=1 night): sample evenly within nights
    if len(nights) >= 2:
        chosen: list[dict[str, Any]] = []
        rem = n_target
        for i, nk in enumerate(nights):
            grp = sorted(by_night[nk], key=lambda x: x["mjd_mid"])
            take = max(1, round(rem / (len(nights) - i))) if i < len(nights) - 1 else rem
            take = min(take, len(grp), rem)
            idxs = [round(j * (len(grp) - 1) / (take - 1)) if take > 1 else 0 for j in range(take)]
            for ix in idxs:
                chosen.append(grp[ix])
            rem -= take
        return sorted(chosen[:n_target], key=lambda x: x["mjd_mid"])

    grp = sorted(cands, key=lambda x: x["mjd_mid"])
    idxs = [round(k * (len(grp) - 1) / (n_target - 1)) for k in range(n_target)]
    return [grp[i] for i in idxs]


def _pick_phase_spread(cands: list[dict[str, Any]], n_take: int) -> list[dict[str, Any]]:
    """Prefer distinct nights spanning positive and negative orbital phases."""
    by_night: dict[int, list[dict[str, Any]]] = {}
    for c in cands:
        by_night.setdefault(int(round(c["mjd_obs"])), []).append(c)
    if len(by_night) < n_take:
        raise RuntimeError(f"Insufficient distinct nights ({len(by_night)} < {n_take})")
    # Representative per night: alternating extremes or sorted by signed phase
    reps = [sorted(grp, key=lambda x: (-x["exptime"], abs(x["orbital_phase_signed"])))[0] for grp in by_night.values()]
    reps.sort(key=lambda x: x["orbital_phase_signed"])
    idxs = [round(k * (len(reps) - 1) / (n_take - 1)) if n_take > 1 else 0 for k in range(n_take)]
    return sorted([reps[i] for i in idxs], key=lambda x: x["mjd_mid"])


def build() -> None:
    now_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    print(f"[build_cohort] Starting D085 SPIRou metadata-only build at {now_utc}", flush=True)

    # 1. Exclusion registry (C001-D084 + D085 format-check star * ups And / 2663606t)
    d84_pe = json.loads((D084_WS / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    excl_coords: list[dict[str, Any]] = list(d84_pe["excluded_targets_coordinate_registry"])
    excl_dp_ids: set[str] = set(d84_pe["excluded_dp_ids"]) | set(d84_pe["format_check_excluded_dp_ids"])

    seen84: set[str] = set()
    bridge_stars = {t["canonical_target"] for t in TARGET_SPECS if t["panchromatic_bridge"]}
    with (D084_WS / "FROZEN_COHORT_D084.csv").open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            excl_dp_ids.add(row["dp_id"].strip())
            st = row["canonical_target"].strip()
            if st not in seen84:
                seen84.add(st)
                excl_coords.append({"label": f"{st}(D084)", "ra_deg": float(row["s_ra"]), "dec_deg": float(row["s_dec"])})

    fmt_targets = list(d84_pe["format_check_excluded_targets"]) + ["UPS_AND (D085 CFHT SPIRou format check)"]
    fmt_dps = list(d84_pe["format_check_excluded_dp_ids"]) + ["2663606t"]
    excl_dp_ids.add("2663606t")
    excl_coords.append({"label": "UPS_AND(D085_FMT)", "ra_deg": 24.199345, "dec_deg": 41.405460})

    # 2. Query ESA Gaia DR3, NASA pscomppars, GAVO CARMENES+2MASS
    gids_sql = ",".join(str(t["gaia_source_id"]) for t in TARGET_SPECS)
    gaia_rows = tap_csv(
        GAIA_TAP,
        f"SELECT source_id, ra, dec, pmra, pmdec, parallax, radial_velocity, phot_g_mean_mag, bp_rp, teff_gspphot, mh_gspphot, ruwe FROM gaiadr3.gaia_source WHERE source_id IN ({gids_sql})",
    )
    gaia_by_id = {int(r["source_id"]): r for r in gaia_rows}
    if len(gaia_by_id) != len(TARGET_SPECS):
        raise RuntimeError(f"Expected {len(TARGET_SPECS)} Gaia rows, got {len(gaia_by_id)}")

    carm_ids = [t["carm_id"] for t in TARGET_SPECS if t["carm_id"]]
    carm_in = ",".join(f"'{c}'" for c in carm_ids)
    carm_rows = tap_json(GAVO_TAP, {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "json", "QUERY": f"SELECT carmenes_id, name, teff, mass FROM carmenes.objects WHERE carmenes_id IN ({carm_in})"})["data"]
    carm_by_id = {r[0]: {"teff": float(r[2]), "mass": float(r[3])} for r in carm_rows}

    nasa_rows = tap_json(
        NASA_TAP,
        {"query": "SELECT hostname, gaia_dr3_id, sy_pnum, ra, dec, st_teff, st_met, st_mass, st_radv FROM pscomppars WHERE gaia_dr3_id IS NOT NULL OR hostname IN ('GJ 411', 'GJ 338 B')", "format": "json"},
    )
    nasa_by_gid: dict[int, dict[str, Any]] = {}
    nasa_by_name: dict[str, dict[str, Any]] = {}
    for nr in nasa_rows:
        nasa_by_name[nr["hostname"]] = nr
        gd = str(nr.get("gaia_dr3_id") or "")
        if gd.startswith("Gaia DR3 "):
            nasa_by_gid[int(gd.split()[-1])] = nr

    def query_tm_and_cadc(spec: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        st = spec["canonical_target"]
        gid = spec["gaia_source_id"]
        g = gaia_by_id[gid]
        ra16, dec16 = float(g["ra"]), float(g["dec"])
        pmra = float(g["pmra"] or 0.0)
        pmdec = float(g["pmdec"] or 0.0)
        ra00 = ra16 - (16.0 * pmra) / (3600000.0 * math.cos(math.radians(dec16)))
        dec00 = dec16 - (16.0 * pmdec) / 3600000.0
        ra21 = ra16 + (5.0 * pmra) / (3600000.0 * math.cos(math.radians(dec16)))
        dec21 = dec16 + (5.0 * pmdec) / 3600000.0

        tm_rows = tap_json(
            GAVO_TAP,
            {
                "REQUEST": "doQuery",
                "LANG": "ADQL",
                "FORMAT": "json",
                "QUERY": f"SELECT TOP 2 mainid, jmag, hmag, kmag, DISTANCE(POINT('ICRS', raj2000, dej2000), POINT('ICRS', {ra00:.6f}, {dec00:.6f}))*3600.0 AS sep FROM twomass.data WHERE 1=CONTAINS(POINT('ICRS', raj2000, dej2000), CIRCLE('ICRS', {ra00:.6f}, {dec00:.6f}, 0.012)) ORDER BY sep ASC",
            },
        )["data"]
        if not tm_rows or tm_rows[0][1] is None or tm_rows[0][2] is None or tm_rows[0][3] is None:
            raise RuntimeError(f"2MASS lookup failed for {st}")

        plx_mas = float(g["parallax"])
        dist_pc = 1000.0 / plx_mas
        nr = nasa_by_gid.get(gid)
        if nr is None and st == "LALANDE21185":
            nr = nasa_by_name.get("GJ 411")
        if nr is None and st == "HD79211":
            nr = nasa_by_name.get("GJ 338 B")

        n_exo = int(nr["sy_pnum"]) if nr and nr.get("sy_pnum") is not None else 0
        if spec["role"] == "CONTROL" and n_exo != 0:
            raise RuntimeError(f"CONTROL star {st} has n_exo={n_exo}!")

        # Prefer homogeneous NASA pscomppars / CARMENES DR1 Teff & mass, then MAST/lit fallback
        if nr and nr.get("st_teff"):
            teff_k = float(nr["st_teff"])
        elif spec["carm_id"] and spec["carm_id"] in carm_by_id:
            teff_k = carm_by_id[spec["carm_id"]]["teff"]
        else:
            teff_k = float(spec["teff_lit"])

        if nr and nr.get("st_met") is not None:
            mh_dex = float(nr["st_met"])
        else:
            mh_dex = float(spec["mh_lit"])

        if nr and nr.get("st_mass"):
            st_mass = float(nr["st_mass"])
        elif spec["carm_id"] and spec["carm_id"] in carm_by_id:
            st_mass = carm_by_id[spec["carm_id"]]["mass"]
        else:
            st_mass = float(spec["mass_lit"])

        rv_kms = float(g["radial_velocity"]) if g.get("radial_velocity") else float(spec["rv_lit"])

        min_sep = 1e9
        nearest = ""
        for ec in excl_coords:
            s = sky_sep_arcsec(ra16, dec16, ec["ra_deg"], ec["dec_deg"])
            if s < min_sep:
                min_sep, nearest = s, ec["label"]
        if (not spec["panchromatic_bridge"]) and min_sep < 9800.0:
            raise RuntimeError(f"Brand-new star {st} too close to prior {nearest}: {min_sep:.1f}\"")

        in_t = ",".join(f"'{n}'" for n in spec["cadc_names"])
        adql = f"""SELECT obs_id, obs_publisher_did, target_name, s_ra, s_dec, t_min, t_max, t_exptime, obs_release_date
FROM ivoa.ObsCore
WHERE obs_collection = 'CFHT' AND instrument_name = 'SPIRou'
  AND obs_publisher_did LIKE '%t'
  AND t_exptime >= 30.0
  AND obs_release_date <= '2026-11-16'
  AND target_name IN ({in_t})
  AND 1 = CONTAINS(POINT('ICRS', s_ra, s_dec), CIRCLE('ICRS', {ra21:.6f}, {dec21:.6f}, 0.06))
ORDER BY t_min ASC"""
        crows = tap_csv(CADC_TAP, adql, timeout=45.0)
        exps: list[dict[str, Any]] = []
        seen_obs: set[str] = set()
        for cr in crows:
            obs_id = cr["obs_id"].strip()
            dp_id = f"{obs_id}t"
            if dp_id in excl_dp_ids or dp_id in seen_obs:
                continue
            seen_obs.add(dp_id)
            tmin, tmax = float(cr["t_min"]), float(cr["t_max"])
            mjd_mid = 0.5 * (tmin + tmax)
            exps.append({
                "obs_id": obs_id,
                "dp_id": dp_id,
                "target_name_archive": cr["target_name"].strip(),
                "access_url": f"https://cadc-west-01.canfar.net/raven/files/cadc:CFHT/{dp_id}.fits",
                "s_ra": float(cr["s_ra"]),
                "s_dec": float(cr["s_dec"]),
                "mjd_obs": tmin,
                "mjd_mid": mjd_mid,
                "exptime": float(cr["t_exptime"]),
                "obs_release_date": cr["obs_release_date"].strip(),
                "bjd_mid_approx": mjd_to_bjd_est(mjd_mid, float(cr["s_ra"]), float(cr["s_dec"])),
            })

        meta = {
            "star": st,
            "gaia_source_id": str(gid),
            "ra_deg": ra16,
            "dec_deg": dec16,
            "ra00_deg": ra00,
            "dec00_deg": dec00,
            "pmra_mas_yr": pmra,
            "pmdec_mas_yr": pmdec,
            "parallax_mas": plx_mas,
            "dist_pc": dist_pc,
            "within_10pc": dist_pc < 10.0,
            "phot_g_mag": float(g["phot_g_mean_mag"]),
            "bp_rp": float(g["bp_rp"]) if g.get("bp_rp") else 2.5,
            "twomass_id": str(tm_rows[0][0]),
            "j_mag": float(tm_rows[0][1]),
            "h_mag": float(tm_rows[0][2]),
            "ks_mag": float(tm_rows[0][3]),
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

    print("  Querying 2MASS PSC + CADC SPIRou APERO `*t` exposure metadata across 29 targets...", flush=True)
    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(query_tm_and_cadc, TARGET_SPECS))

    # 3. Deterministic exposure selection + Keplerian kinematics
    cohort_rows: list[dict[str, Any]] = []
    orbital_campaigns: dict[str, Any] = {}
    star_sep_verif: list[dict[str, Any]] = []
    meta_by_star: dict[str, dict[str, Any]] = {}

    for spec, (meta, cands) in zip(TARGET_SPECS, results):
        st = spec["canonical_target"]
        meta_by_star[st] = meta
        orb = spec["orbital_campaign"]
        if orb is None:
            picks = select_night_spaced_exposures(cands, spec["n_exp"])
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
            p_in = _pick_phase_spread(in_cands, 4)
            p_out = _pick_phase_spread(out_cands, 4)
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
                "instrument": "SPIROU",
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
            cohort_rows.append({
                "phase_id": "D085",
                "instrument": "SPIROU",
                "canonical_target": st,
                "common_name": spec["common_name"],
                "role": spec["role"],
                "subrole": spec["subrole"],
                "panchromatic_bridge": str(bool(spec["panchromatic_bridge"])),
                "radio_mm_id": spec["radio_mm_id"],
                "gaia_source_id": meta["gaia_source_id"],
                "twomass_id": meta["twomass_id"],
                "dp_id": p["dp_id"],
                "obs_id": p["obs_id"],
                "target_name_archive": p["target_name_archive"],
                "access_url": p["access_url"],
                "epoch_rank": p["epoch_rank"],
                "phase_window": p["phase_window"],
                "orbital_phase_signed": round(float(p["orbital_phase_signed"]), 7),
                "planet_orbital_rv_kms": round(float(p["planet_orbital_rv_kms"]), 5),
                "s_ra": round(float(meta["ra_deg"]), 7),
                "s_dec": round(float(meta["dec_deg"]), 7),
                "mjd_obs": round(float(p["mjd_obs"]), 7),
                "mjd_mid": round(float(p["mjd_mid"]), 7),
                "t_exptime": round(float(p["exptime"]), 3),
                "obs_release_date": p["obs_release_date"],
                "dist_pc": round(float(meta["dist_pc"]), 6),
                "within_10pc": str(bool(meta["within_10pc"])),
                "phot_g_mag": round(float(meta["phot_g_mag"]), 5),
                "bp_rp": round(float(meta["bp_rp"]), 5),
                "j_mag": round(float(meta["j_mag"]), 4),
                "h_mag": round(float(meta["h_mag"]), 4),
                "ks_mag": round(float(meta["ks_mag"]), 4),
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
            "instrument": "SPIROU",
            "role": spec["role"],
            "panchromatic_bridge": bool(spec["panchromatic_bridge"]),
            "dist_pc": round(float(meta["dist_pc"]), 5),
            "within_10pc": bool(meta["within_10pc"]),
            "ra_deg": round(float(meta["ra_deg"]), 6),
            "dec_deg": round(float(meta["dec_deg"]), 6),
            "nearest_prior_target": meta["nearest_prior_label"],
            "min_sky_separation_arcsec": round(float(meta["min_prior_sep_arcsec"]), 2),
            "status": "VERIFIED_NORTHERN_BRIDGE_D084_PLUS_D085" if spec["panchromatic_bridge"] else "VERIFIED_BRAND_NEW_SPIROU_STAR",
        })

    # Verify intra-D085 pairwise separations among the 25 brand-new stars
    new_verifs = [v for v in star_sep_verif if not v["panchromatic_bridge"]]
    min_intra_sep = 1e9
    for i, a in enumerate(new_verifs):
        for b in new_verifs[i + 1 :]:
            min_intra_sep = min(min_intra_sep, sky_sep_arcsec(a["ra_deg"], a["dec_deg"], b["ra_deg"], b["dec_deg"]))
    min_brand_new_sep = min(v["min_sky_separation_arcsec"] for v in new_verifs)
    new_10pc = sum(1 for v in new_verifs if v["within_10pc"])
    print(f"  Selected {len(cohort_rows)} exposures across {len(TARGET_SPECS)} stars ({len(new_verifs)} brand-new, {new_10pc} new <10pc; min_prior_sep={min_brand_new_sep:.2f}\", min_intra_sep={min_intra_sep:.2f}\")", flush=True)

    # Write FROZEN_COHORT_D085.csv
    cohort_path = WS / "FROZEN_COHORT_D085.csv"
    with cohort_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(cohort_rows[0].keys()))
        w.writeheader()
        w.writerows(cohort_rows)

    # Write ORBITAL_CAMPAIGNS_AND_KINEMATICS.json
    orb_doc = {
        "schema": "SPIROU_V3_6_ORBITAL_CAMPAIGNS",
        "phase_id": "D085",
        "instrument": "SPIROU",
        "n_campaigns": len(orbital_campaigns),
        "n_science_orbital_campaigns": sum(1 for c in orbital_campaigns.values() if c["role"] == "SCIENCE"),
        "n_control_null_campaigns": sum(1 for c in orbital_campaigns.values() if c["role"] == "CONTROL"),
        "campaigns": orbital_campaigns,
    }
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    # Write PRIOR_EXCLUSION_VERIFICATION.json
    excl_doc = {
        "schema": "D085_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D085",
        "verified_utc": now_utc,
        "prior_phases_covered": "C001-C037 + D001-D084",
        "format_check_excluded_targets": fmt_targets,
        "format_check_excluded_dp_ids": fmt_dps,
        "n_prior_excluded_coords": len(excl_coords),
        "n_prior_excluded_dp_ids": len(excl_dp_ids),
        "d085_total_stars": len(TARGET_SPECS),
        "d085_brand_new_unique_stars": len(new_verifs),
        "d085_panchromatic_bridge_stars": len(bridge_stars),
        "d085_brand_new_within_10pc": new_10pc,
        "d085_total_exposures": len(cohort_rows),
        "d085_dp_id_overlap_count": len({r["dp_id"] for r in cohort_rows} & excl_dp_ids),
        "min_brand_new_sky_separation_arcsec": round(min_brand_new_sep, 2),
        "min_intra_d085_brand_new_separation_arcsec": round(min_intra_sep, 2),
        "star_separation_verification": star_sep_verif,
        "excluded_dp_ids": sorted(excl_dp_ids),
        "excluded_targets_coordinate_registry": excl_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(excl_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    # Snapshot prior V3.0-V3.5 synthesis + D083 southern bridge + D084 northern bridge optical limits
    d84_summary = json.loads((D084_WS / "results" / "SUMMARY.json").read_text(encoding="utf-8"))
    d84_snap = json.loads((D084_WS / "PRIOR_V3_PHASES_SNAPSHOT.json").read_text(encoding="utf-8"))
    with (D084_WS / "results" / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_125STARS.csv").open("r", encoding="utf-8", newline="") as f:
        unified_125 = list(csv.DictReader(f))
    with D083_BRIDGE_CSV.open("r", encoding="utf-8", newline="") as f:
        bridge_south = list(csv.DictReader(f))
    with (D084_WS / "results" / "STAR_UPPER_LIMITS_189.csv").open("r", encoding="utf-8", newline="") as f:
        d84_north_bridge_ul = [r for r in csv.DictReader(f) if r["star"] in bridge_stars]

    prior_snap = {
        "schema": "D085_PRIOR_V3_PHASES_SNAPSHOT",
        "prior_phases": "D079-D084",
        "prior_v3_unique_stars_count": len(unified_125),
        "prior_v3_within_10pc_count": sum(1 for r in unified_125 if r["within_10pc"] == "True"),
        "prior_v3_total_exposures_count": sum(int(r["n_exposures_total"]) for r in unified_125),
        "prior_v3_calibration_trials_count": int(d84_summary["unified_125star_panchromatic_v3_synthesis"]["total_calibration_trials_d079_d084"]),
        "prior_v2_false_alarms_eliminated_total": int(d84_summary["unified_125star_panchromatic_v3_synthesis"]["v2_false_alarms_eliminated_total"]),
        "d084_summary_headline": d84_summary,
        "d083_summary_headline": d84_snap["d083_summary_headline"],
        "d079_d082_headlines": d84_snap["d079_d082_headlines"],
        "unified_125star_rows": unified_125,
        "d083_southern_bridge_rows": bridge_south,
        "d084_northern_bridge_optical_rows": d84_north_bridge_ul,
    }
    (WS / "PRIOR_V3_PHASES_SNAPSHOT.json").write_text(json.dumps(prior_snap, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    # Multi-messenger snapshot: update M20_RHOCRB canonical_v3_star = "RHOCRB" -> 14 direct overlaps
    d84_mm = json.loads((D084_WS / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").read_text(encoding="utf-8"))
    for s in d84_mm["systems"]:
        if s["mm_id"] == "M20_RHOCRB":
            s["canonical_v3_star"] = "RHOCRB"
    ov_stars = sorted({s["canonical_v3_star"] for s in d84_mm["systems"] if s["canonical_v3_star"]})
    mm_doc = dict(d84_mm)
    mm_doc["schema"] = "D085_MULTIMESSENGER_RADIO_TESS_SNAPSHOT"
    mm_doc["n_direct_echelle_multimessenger_overlap_stars"] = len(ov_stars)
    mm_doc["overlapping_v3_stars"] = ov_stars
    (WS / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").write_text(json.dumps(mm_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("[build_cohort] Wrote all 5 locked metadata & snapshot artifacts successfully.", flush=True)


if __name__ == "__main__":
    build()
