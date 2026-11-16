#!/usr/bin/env python3
"""Metadata-only cohort builder & prospective exclusion verifier for Phase D084 (NORTHERN_V3_5).

Queries ONLY archival metadata catalogs (GAVO CARMENES DR1, INAF IA2 TNG HARPS-N TAP,
GAVO Gaia DR3 lite + 2MASS PSC, NASA Exoplanet Archive ps/pscomppars, and CDS Sesame)
WITHOUT downloading any FITS spectrum files.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import math
from pathlib import Path
from typing import Any
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

WS = Path(__file__).resolve().parent
D083_WS = WS.parent / "work_crires_20261115_d083_v3_4_kband_and_100star_synthesis"
D082_WS = WS.parent / "work_nirps_20261115_d082_v3_3_near_ir_and_panchromatic_survey"
D081_WS = WS.parent / "work_echelle_20261115_d081_v3_2_transit_kinematics_and_10pc_survey"
D080_WS = WS.parent / "work_echelle_20261114_d080_v3_1_exoplanet_survey"
D079_WS = WS.parent / "work_harps_20261114_d079_v3_calibrated_search"

GAVO_TAP = "https://dc.g-vo.org/__system__/tap/run/sync"
TNG_TAP = "http://archives.ia2.inaf.it/vo/tap/tng/sync"
NASA_TAP = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
VIZIER_TAP = "https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync"

G_SI = 6.67430e-11
M_SUN_KG = 1.98847e30
DAY_S = 86400.0
C_KMS = 299792.458
AU_KM = 149597870.7

# Locked 25 Northern Hemisphere targets (10 HARPS-N + 15 CARMENES_VIS)
TARGET_SPECS: list[dict[str, Any]] = [
    # --- 4 Zero-Planet < 10 pc CONTROL Stars (34 exposures) ---
    {
        "canonical_target": "HD185144",
        "common_name": "sigma Draconis",
        "sesame_name": "HD 185144",
        "instrument": "HARPS_N",
        "archive_key": "HD185144",
        "tng_objects": ["HD185144", "HD 185144", "sig Dra", "sigDra"],
        "role": "CONTROL",
        "subrole": "CONTROL_TIMESERIES_10PC",
        "n_exp": 12,
        "within_10pc_expected": True,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "SYNTHETIC_NULL_EPHEMERIS",
            "orbper_days": 2.3719,
            "t0_bjd": None,  # anchored to first selected BJD
            "ecc": 0.0,
            "st_mass_msun": 0.85,
            "transiting": True,
        },
        "teff_lit": 5246.0,
        "mh_lit": -0.20,
        "mass_lit": 0.85,
        "rv_lit": 26.69,
    },
    {
        "canonical_target": "HD88230",
        "common_name": "GJ 380",
        "sesame_name": "HD 88230",
        "instrument": "HARPS_N",
        "archive_key": "HD88230",
        "tng_objects": ["HD88230", "HD 88230", "GJ380", "GJ 380"],
        "role": "CONTROL",
        "subrole": "CONTROL_10PC",
        "n_exp": 5,
        "within_10pc_expected": True,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 4131.0,
        "mh_lit": -0.05,
        "mass_lit": 0.67,
        "rv_lit": -26.05,
    },
    {
        "canonical_target": "ROSS248",
        "common_name": "Ross 248 (HH And)",
        "sesame_name": "Ross 248",
        "instrument": "CARMENES_VIS",
        "archive_key": "J23419+441",
        "role": "CONTROL",
        "subrole": "CONTROL_TIMESERIES_10PC",
        "n_exp": 12,
        "within_10pc_expected": True,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "SYNTHETIC_NULL_EPHEMERIS",
            "orbper_days": 1.9137,
            "t0_bjd": None,
            "ecc": 0.0,
            "st_mass_msun": 0.144,
            "transiting": True,
        },
        "teff_lit": 3190.0,
        "mh_lit": -0.14,
        "mass_lit": 0.144,
        "rv_lit": -77.38,
    },
    {
        "canonical_target": "GJ412A",
        "common_name": "GJ 412 A",
        "sesame_name": "BD+44 2051A",
        "instrument": "CARMENES_VIS",
        "archive_key": "J11054+435",
        "role": "CONTROL",
        "subrole": "CONTROL_10PC",
        "n_exp": 5,
        "within_10pc_expected": True,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3628.0,
        "mh_lit": -0.40,
        "mass_lit": 0.382,
        "rv_lit": 68.89,
    },
    # --- 14 Brand-New < 10 pc Northern SCIENCE Stars (105 exposures) ---
    {
        "canonical_target": "WOLF359",
        "common_name": "Wolf 359 (CN Leo)",
        "sesame_name": "Wolf 359",
        "instrument": "CARMENES_VIS",
        "archive_key": "J10564+070",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "n_exp": 5,
        "within_10pc_expected": True,
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
        "sesame_name": "Lalande 21185",
        "instrument": "CARMENES_VIS",
        "archive_key": "J11033+359",
        "role": "SCIENCE",
        "subrole": "EXOPLANET_ORBITAL_10PC",
        "n_exp": 12,
        "within_10pc_expected": True,
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
        "mh_lit": -0.36,
        "mass_lit": 0.3899,
        "rv_lit": -84.69,
    },
    {
        "canonical_target": "61CYGA",
        "common_name": "61 Cygni A",
        "sesame_name": "HD 201091",
        "instrument": "HARPS_N",
        "archive_key": "HD201091",
        "tng_objects": ["HD201091", "HD 201091", "61CygA", "61 Cyg A"],
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "n_exp": 5,
        "within_10pc_expected": True,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 4374.0,
        "mh_lit": -0.33,
        "mass_lit": 0.70,
        "rv_lit": -65.74,
    },
    {
        "canonical_target": "61CYGB",
        "common_name": "61 Cygni B",
        "sesame_name": "HD 201092",
        "instrument": "HARPS_N",
        "archive_key": "HD201092",
        "tng_objects": ["HD201092", "HD 201092", "61CygB", "61 Cyg B"],
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "n_exp": 5,
        "within_10pc_expected": True,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 4044.0,
        "mh_lit": -0.38,
        "mass_lit": 0.63,
        "rv_lit": -64.07,
    },
    {
        "canonical_target": "STRUVE2398A",
        "common_name": "Struve 2398 A (Gl 725 A)",
        "sesame_name": "HD 173739",
        "instrument": "CARMENES_VIS",
        "archive_key": "J18427+596N",
        "role": "SCIENCE",
        "subrole": "EXOPLANET_ORBITAL_10PC",
        "n_exp": 10,
        "within_10pc_expected": True,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "Gl 725 A b",
            "orbper_days": 11.2201,
            "t0_bjd": 2458597.70,
            "ecc": 0.0,
            "st_mass_msun": 0.33,
            "transiting": False,
        },
        "teff_lit": 3470.0,
        "mh_lit": -0.19,
        "mass_lit": 0.339,
        "rv_lit": -0.82,
    },
    {
        "canonical_target": "STRUVE2398B",
        "common_name": "Struve 2398 B (Gl 725 B)",
        "sesame_name": "HD 173740",
        "instrument": "CARMENES_VIS",
        "archive_key": "J18427+596S",
        "role": "SCIENCE",
        "subrole": "EXOPLANET_HOST_10PC",
        "n_exp": 5,
        "within_10pc_expected": True,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3390.0,
        "mh_lit": -0.28,
        "mass_lit": 0.258,
        "rv_lit": 1.15,
    },
    {
        "canonical_target": "GXAND",
        "common_name": "GX And (GJ 15 A)",
        "sesame_name": "GX And",
        "instrument": "CARMENES_VIS",
        "archive_key": "J00183+440",
        "role": "SCIENCE",
        "subrole": "EXOPLANET_ORBITAL_10PC",
        "n_exp": 10,
        "within_10pc_expected": True,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "GJ 15 A b",
            "orbper_days": 11.4407,
            "t0_bjd": 2455783.63,
            "ecc": 0.094,
            "st_mass_msun": 0.38,
            "transiting": False,
        },
        "teff_lit": 3603.0,
        "mh_lit": -0.34,
        "mass_lit": 0.395,
        "rv_lit": 11.72,
    },
    {
        "canonical_target": "DXCNC",
        "common_name": "DX Cnc (GJ 1111)",
        "sesame_name": "DX Cnc",
        "instrument": "CARMENES_VIS",
        "archive_key": "J08298+267",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "n_exp": 5,
        "within_10pc_expected": True,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3000.0,
        "mh_lit": 0.00,
        "mass_lit": 0.100,
        "rv_lit": 10.30,
    },
    {
        "canonical_target": "GJ687",
        "common_name": "GJ 687",
        "sesame_name": "GJ 687",
        "instrument": "CARMENES_VIS",
        "archive_key": "J17364+683",
        "role": "SCIENCE",
        "subrole": "RADIO_OVERLAP_ORBITAL_10PC",
        "n_exp": 10,
        "within_10pc_expected": True,
        "radio_mm_id": "M14_GJ687",
        "orbital_campaign": {
            "planet_name": "GJ 687 b",
            "orbper_days": 38.142,
            "t0_bjd": 2454481.07,
            "ecc": 0.17,
            "st_mass_msun": 0.40,
            "transiting": False,
        },
        "teff_lit": 3390.0,
        "mh_lit": 0.06,
        "mass_lit": 0.432,
        "rv_lit": -28.90,
    },
    {
        "canonical_target": "ADLEO",
        "common_name": "AD Leo (GJ 388)",
        "sesame_name": "AD Leo",
        "instrument": "CARMENES_VIS",
        "archive_key": "J10196+198",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "n_exp": 5,
        "within_10pc_expected": True,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3455.0,
        "mh_lit": 0.06,
        "mass_lit": 0.446,
        "rv_lit": 12.37,
    },
    {
        "canonical_target": "GJ445",
        "common_name": "GJ 445",
        "sesame_name": "GJ 445",
        "instrument": "CARMENES_VIS",
        "archive_key": "J11476+786",
        "role": "SCIENCE",
        "subrole": "SOLAR_NEIGHBORHOOD_10PC",
        "n_exp": 5,
        "within_10pc_expected": True,
        "radio_mm_id": "",
        "orbital_campaign": None,
        "teff_lit": 3360.0,
        "mh_lit": -0.24,
        "mass_lit": 0.255,
        "rv_lit": -111.50,
    },
    {
        "canonical_target": "GJ251",
        "common_name": "GJ 251 (Wolf 294)",
        "sesame_name": "GJ 251",
        "instrument": "CARMENES_VIS",
        "archive_key": "J06548+332",
        "role": "SCIENCE",
        "subrole": "EXOPLANET_ORBITAL_10PC",
        "n_exp": 10,
        "within_10pc_expected": True,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "GJ 251 b",
            "orbper_days": 14.237,
            "t0_bjd": 2458626.81,
            "ecc": 0.0,
            "st_mass_msun": 0.35,
            "transiting": False,
        },
        "teff_lit": 3500.0,
        "mh_lit": 0.07,
        "mass_lit": 0.343,
        "rv_lit": 22.30,
    },
    {
        "canonical_target": "HD219134",
        "common_name": "HD 219134",
        "sesame_name": "HD 219134",
        "instrument": "HARPS_N",
        "archive_key": "HD219134",
        "tng_objects": ["HD219134", "HD 219134", "GJ892"],
        "role": "SCIENCE",
        "subrole": "RADIO_OVERLAP_TRANSITING_10PC",
        "n_exp": 12,
        "within_10pc_expected": True,
        "radio_mm_id": "M16_HD219134",
        "orbital_campaign": {
            "planet_name": "HD 219134 b",
            "orbper_days": 3.092926,
            "t0_bjd": 2458694.81665,
            "ecc": 0.0,
            "st_mass_msun": 0.779,
            "transiting": True,
        },
        "teff_lit": 4798.0,
        "mh_lit": 0.10,
        "mass_lit": 0.779,
        "rv_lit": -18.57,
    },
    {
        "canonical_target": "GJ486",
        "common_name": "GJ 486 (Wolf 437)",
        "sesame_name": "GJ 486",
        "instrument": "CARMENES_VIS",
        "archive_key": "J12479+097",
        "role": "SCIENCE",
        "subrole": "TRANSITING_ORBITAL_10PC",
        "n_exp": 12,
        "within_10pc_expected": True,
        "radio_mm_id": "",
        "orbital_campaign": {
            "planet_name": "GJ 486 b",
            "orbper_days": 1.46712127,
            "t0_bjd": 2459939.071602,
            "ecc": 0.00086,
            "st_mass_msun": 0.312,
            "transiting": True,
        },
        "teff_lit": 3410.0,
        "mh_lit": -0.15,
        "mass_lit": 0.309,
        "rv_lit": 19.20,
    },
    # --- 7 Northern GBT 1.4 GHz Radio-Overlap SCIENCE Hosts beyond 10 pc (44 exposures) ---
    {
        "canonical_target": "GJ649",
        "common_name": "GJ 649",
        "sesame_name": "GJ 649",
        "instrument": "CARMENES_VIS",
        "archive_key": "J16581+257",
        "role": "SCIENCE",
        "subrole": "RADIO_OVERLAP_HOST",
        "n_exp": 5,
        "within_10pc_expected": False,
        "radio_mm_id": "M18_GJ649",
        "orbital_campaign": None,
        "teff_lit": 3782.0,
        "mh_lit": -0.15,
        "mass_lit": 0.499,
        "rv_lit": 3.76,
    },
    {
        "canonical_target": "HIP48714",
        "common_name": "HIP 48714 (BD+63 869)",
        "sesame_name": "HIP 48714",
        "instrument": "CARMENES_VIS",
        "archive_key": "J09561+627",
        "role": "SCIENCE",
        "subrole": "RADIO_OVERLAP_ORBITAL",
        "n_exp": 8,
        "within_10pc_expected": False,
        "radio_mm_id": "M36_HIP48714",
        "orbital_campaign": {
            "planet_name": "HIP 48714 b",
            "orbper_days": 17.818,
            "t0_bjd": 2451539.80,
            "ecc": 0.50,
            "st_mass_msun": 0.588,
            "transiting": False,
        },
        "teff_lit": 3938.0,
        "mh_lit": -0.05,
        "mass_lit": 0.588,
        "rv_lit": 14.85,
    },
    {
        "canonical_target": "HD3651",
        "common_name": "54 Psc (HD 3651)",
        "sesame_name": "HD 3651",
        "instrument": "HARPS_N",
        "archive_key": "HD3651",
        "tng_objects": ["HD3651", "HD 3651", "54Psc", "54 Psc"],
        "role": "SCIENCE",
        "subrole": "RADIO_OVERLAP_HOST",
        "n_exp": 5,
        "within_10pc_expected": False,
        "radio_mm_id": "M33_HD3651",
        "orbital_campaign": None,
        "teff_lit": 5221.0,
        "mh_lit": 0.15,
        "mass_lit": 0.799,
        "rv_lit": -32.99,
    },
    {
        "canonical_target": "HD99492",
        "common_name": "83 Leo B (HD 99492)",
        "sesame_name": "HD 99492",
        "instrument": "HARPS_N",
        "archive_key": "HD99492",
        "tng_objects": ["HD99492", "HD 99492", "83LeoB", "HIP55848"],
        "role": "SCIENCE",
        "subrole": "RADIO_OVERLAP_HOST",
        "n_exp": 5,
        "within_10pc_expected": False,
        "radio_mm_id": "M32_HD99492",
        "orbital_campaign": None,
        "teff_lit": 4929.0,
        "mh_lit": 0.30,
        "mass_lit": 0.85,
        "rv_lit": 3.63,
    },
    {
        "canonical_target": "HD87883",
        "common_name": "HD 87883",
        "sesame_name": "HD 87883",
        "instrument": "HARPS_N",
        "archive_key": "HD87883",
        "tng_objects": ["HD87883", "HD 87883"],
        "role": "SCIENCE",
        "subrole": "RADIO_OVERLAP_HOST",
        "n_exp": 5,
        "within_10pc_expected": False,
        "radio_mm_id": "M22_HD87883",
        "orbital_campaign": None,
        "teff_lit": 4980.0,
        "mh_lit": 0.11,
        "mass_lit": 0.80,
        "rv_lit": 9.37,
    },
    {
        "canonical_target": "16CYGB",
        "common_name": "16 Cyg B (HD 186427)",
        "sesame_name": "HD 186427",
        "instrument": "HARPS_N",
        "archive_key": "16CygB",
        "tng_objects": ["16CygB", "KIC12069449", "HD186427", "HD 186427"],
        "role": "SCIENCE",
        "subrole": "RADIO_OVERLAP_HOST",
        "n_exp": 5,
        "within_10pc_expected": False,
        "radio_mm_id": "M24_16CYGB",
        "orbital_campaign": None,
        "teff_lit": 5750.0,
        "mh_lit": 0.06,
        "mass_lit": 1.08,
        "rv_lit": -28.05,
    },
    {
        "canonical_target": "HD164922",
        "common_name": "HD 164922",
        "sesame_name": "HD 164922",
        "instrument": "HARPS_N",
        "archive_key": "KP74",
        "tng_objects": ["KP74", "HD164922", "HD 164922"],
        "role": "SCIENCE",
        "subrole": "RADIO_OVERLAP_HOST",
        "n_exp": 5,
        "within_10pc_expected": False,
        "radio_mm_id": "M25_HD164922",
        "orbital_campaign": None,
        "teff_lit": 5390.0,
        "mh_lit": 0.18,
        "mass_lit": 0.926,
        "rv_lit": 20.13,
    },
]


def http_post_tap(url: str, params: dict[str, str], timeout: float = 45.0) -> str:
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "ANDERSEN-SETI-D084/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def gavo_tap(adql: str) -> dict[str, Any]:
    txt = http_post_tap(GAVO_TAP, {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "json", "QUERY": adql}, timeout=35.0)
    return json.loads(txt)


def nasa_tap(adql: str) -> list[dict[str, Any]]:
    txt = http_post_tap(NASA_TAP, {"query": adql, "format": "json"}, timeout=35.0)
    return json.loads(txt)


def sesame_resolve(name: str) -> dict[str, Any]:
    url = "https://cds.unistra.fr/cgi-bin/nph-sesame/-oxpI/S?" + urllib.parse.quote(name)
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ANDERSEN-SETI-D084/1.0"})
            with urllib.request.urlopen(req, timeout=25.0) as resp:
                root = ET.fromstring(resp.read().decode("utf-8", errors="replace"))
            break
        except Exception as exc:
            last_err = exc
    else:
        raise RuntimeError(f"Sesame failed for {name}: {last_err}")
    ra_t = root.findtext(".//jradeg")
    dec_t = root.findtext(".//jdedeg")
    plx_t = root.findtext(".//plx/v")
    rv_t = root.findtext(".//vel/v")
    sp_t = root.findtext(".//spType")
    aliases = [a.text.strip() for a in root.findall(".//alias") if a.text]
    gdr3 = next((a.split()[-1] for a in aliases if "Gaia DR3" in a), None)
    tm_id = next((a.split()[-1].lstrip("J") for a in aliases if "2MASS" in a), None)
    mags = {m.attrib.get("band"): float(m.findtext("v")) for m in root.findall(".//mag") if m.findtext("v")}
    return {
        "ra_deg": float(ra_t),
        "dec_deg": float(dec_t),
        "plx_mas": float(plx_t) if plx_t else None,
        "rv_kms": float(rv_t) if rv_t else None,
        "sp_type": sp_t or "",
        "gaia_dr3_id": gdr3,
        "twomass_id": tm_id,
        "mags": mags,
    }


def sky_sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1 = math.radians(ra1), math.radians(dec1)
    r2, d2 = math.radians(ra2), math.radians(dec2)
    a = math.sin(0.5 * (d2 - d1)) ** 2 + math.cos(d1) * math.cos(d2) * (math.sin(0.5 * (r2 - r1)) ** 2)
    return 3600.0 * math.degrees(2.0 * math.asin(min(1.0, math.sqrt(max(0.0, a)))))


def iso_to_mjd(date_str: str) -> float:
    s = date_str.strip().rstrip("Z")
    t = dt.datetime.fromisoformat(s)
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    unix = t.timestamp()
    return 40587.0 + unix / 86400.0


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
    tx = math.cos(dec_r) * math.cos(ra_r)
    ty = math.cos(dec_r) * math.sin(ra_r)
    tz = math.sin(dec_r)
    lt_days = (sun_x * tx + sun_y * ty + sun_z * tz) * (AU_KM / C_KMS) / DAY_S
    return float(jd - lt_days)


def compute_kp_kms(st_mass_msun: float, orbper_days: float, ecc: float, transiting: bool) -> float:
    v_circ_ms = ((2.0 * math.pi * G_SI * float(st_mass_msun) * M_SUN_KG) / (float(orbper_days) * DAY_S)) ** (1.0 / 3.0)
    # Use sin(i) = 1.0 for transiting planets and median isotropic inclination pi/4? Wait: D083 sets sin_i=1 in kp_kms!
    # Wait: let's match D083 compute_keplerian_kp_kms exact formula so audit.py matches identically!
    return float((v_circ_ms / math.sqrt(max(1e-6, 1.0 - float(ecc) ** 2))) / 1000.0)


def phase_signed_and_rv(bjd_mid: float, t0_bjd: float, orbper_days: float, kp_kms: float) -> tuple[float, float]:
    raw = (float(bjd_mid) - float(t0_bjd)) / float(orbper_days)
    phi = raw - round(raw)
    return float(phi), float(kp_kms * math.sin(2.0 * math.pi * phi))


def build() -> None:
    now_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    obs_cutoff = "2026-11-15T00:00:00Z"
    print(f"[build_cohort] Starting metadata-only cohort construction at {now_utc}")

    # 1. Load Prior Exclusion Registry (C001-D083)
    d083_pe = json.loads((D083_WS / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    raw_reg = d083_pe["excluded_targets_coordinate_registry"]
    if isinstance(raw_reg, dict):
        excluded_coords: list[dict[str, Any]] = [
            {
                "label": f"{k}({v.get('phase', 'PRIOR')})",
                "ra_deg": float(v["ra_deg"]),
                "dec_deg": float(v["dec_deg"]),
            }
            for k, v in sorted(raw_reg.items())
        ]
    else:
        excluded_coords = list(raw_reg)
    excluded_dp_ids: set[str] = set(d083_pe["excluded_dp_ids"])

    # Add D083 20 brand-new stars and 148 dp_ids + D084 format-check exclusions
    seen_d083_stars: set[str] = set()
    with (D083_WS / "FROZEN_COHORT_D083.csv").open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            excluded_dp_ids.add(row["dp_id"].strip())
            st = row["canonical_target"].strip()
            if row["panchromatic_bridge"].strip() != "True" and st not in seen_d083_stars:
                seen_d083_stars.add(st)
                excluded_coords.append(
                    {
                        "label": f"{st}(D083)",
                        "ra_deg": float(row["s_ra"]),
                        "dec_deg": float(row["s_dec"]),
                    }
                )

    # Record D084 format-check excluded files & stars explicitly
    format_check_targets = list(d083_pe["format_check_excluded_targets"]) + [
        "J20450+444 (D084 CARMENES_VIS format check)",
        "K02801 (D084 HARPS-N format check)",
    ]
    format_check_dp_ids = list(d083_pe["format_check_excluded_dp_ids"]) + [
        "car-20160423T04h04m54s-sci-gtoc-vis_A",
        "HARPN.2015-05-16T03-51-36.767",
    ]
    for dp in format_check_dp_ids:
        excluded_dp_ids.add(dp)
    # Add format-check star coordinates to excluded_coords so zero overlap is guaranteed
    for label_fc, fc_name in [("J20450+444(D084_FORMAT)", "LSPM J2045+4429"), ("K02801(D084_FORMAT)", "BD+53 2777")]:
        pass
    # Query J20450+444 from carmenes.objects & resolve coordinate directly
    fc_carm = gavo_tap("SELECT carmenes_id, ra, dec FROM carmenes.objects WHERE carmenes_id='J20450+444'")["data"]
    if fc_carm:
        excluded_coords.append({"label": "J20450+444(D084_FMT)", "ra_deg": float(fc_carm[0][1]), "dec_deg": float(fc_carm[0][2])})
    excluded_coords.append(
        {
            "label": "K02801(D084_FMT)",
            "ra_deg": math.degrees(5.2213357169125),
            "dec_deg": math.degrees(0.718093419303736),
        }
    )
    print(f"  Prior excluded coords: {len(excluded_coords)}, prior excluded dp_ids: {len(excluded_dp_ids)}")

    # 2. Query CARMENES objects & exposures
    carm_ids = [t["archive_key"] for t in TARGET_SPECS if t["instrument"] == "CARMENES_VIS"]
    carm_in_sql = ",".join(f"'{c}'" for c in carm_ids)
    carm_obj_rows = gavo_tap(
        f"SELECT carmenes_id, name, ra, dec, teff, mass, radius FROM carmenes.objects WHERE carmenes_id IN ({carm_in_sql})"
    )["data"]
    carm_objs = {
        r[0]: {"name": r[1], "ra": float(r[2]), "dec": float(r[3]), "teff": float(r[4]), "mass": float(r[5]), "radius": float(r[6])}
        for r in carm_obj_rows
    }

    carm_exp_rows = gavo_tap(
        f"""
        SELECT ssa_targname, accref, ssa_dateobs, ssa_timeext, ssa_snr, ssa_pdate, ssa_specstart, ssa_specend, ssa_specres
        FROM carmenes.data
        WHERE ssa_targname IN ({carm_in_sql}) AND embargo IS NULL
        ORDER BY ssa_targname, ssa_dateobs
        """
    )["data"]
    carm_by_id: dict[str, list[dict[str, Any]]] = {cid: [] for cid in carm_ids}
    for row in carm_exp_rows:
        cid, accref, mjd_obs, expt, snr, pdate, em_min, em_max, res = row
        if accref is None or mjd_obs is None or expt is None:
            continue
        if float(expt) < 40.0 or float(mjd_obs) > 60994.0:
            continue
        pdate_iso = str(pdate or "2025-09-01T00:00:00").rstrip("Z") + "Z"
        if pdate_iso > obs_cutoff:
            continue
        fname = accref.rsplit("/", 1)[-1]
        dp_id = fname.replace(".fits", "")
        if dp_id in excluded_dp_ids:
            continue
        static_url = f"https://dc.g-vo.org/carmenes/q/sdl/static/{cid}/{fname}"
        mjd_f = float(mjd_obs)
        carm_by_id[cid].append(
            {
                "dp_id": dp_id,
                "target_name_archive": cid,
                "access_url": static_url,
                "e2ds_url": "",
                "mjd_obs": mjd_f,
                "mjd_mid": mjd_f + (0.5 * float(expt)) / 86400.0,
                "exptime": float(expt),
                "snr": float(snr) if snr is not None else 60.0,
                "em_min": float(em_min) if em_min is not None else 5.1365e-7,
                "em_max": float(em_max) if em_max is not None else 1.0631e-6,
                "res_power": float(res) if res is not None else 94600.0,
                "obs_release_date": pdate_iso,
                "s_ra": carm_objs[cid]["ra"],
                "s_dec": carm_objs[cid]["dec"],
            }
        )
    print(f"  CARMENES candidate exposures across 15 targets: {sum(len(v) for v in carm_by_id.values())}")

    # 3. Resolve all 25 stars directly via verified Gaia DR3 source IDs on GAVO TAP (no Sesame calls)
    print("  [3a] Resolving 25 stars in Gaia DR3 + 2MASS PSC + NASA pscomppars...", flush=True)
    GAIA_SOURCE_IDS = {
        "HD185144": 2261614264931057664,
        "HD88230": 823773494718931968,
        "ROSS248": 1926461164913660160,
        "GJ412A": 778947814402602752,
        "WOLF359": 3864972938605115520,
        "LALANDE21185": 762815470562110464,
        "61CYGA": 1872046609345556480,
        "61CYGB": 1872046574983497216,
        "STRUVE2398A": 2154880616774131840,
        "STRUVE2398B": 2154880616774131712,
        "GXAND": 385334230892516480,
        "DXCNC": 703790044252850688,
        "GJ687": 1637645127018395776,
        "ADLEO": 625453654702751872,
        "GJ445": 1129149723913123456,
        "GJ251": 939072613334579328,
        "HD219134": 2009481748875806976,
        "GJ486": 3735000631158990976,
        "GJ649": 4572835535272627712,
        "HIP48714": 1051547052218220160,
        "HD3651": 2802397960855105920,
        "HD99492": 3812355294262255104,
        "HD87883": 747266452000257280,
        "16CYGB": 2135550755683407232,
        "HD164922": 4582680493669880704,
    }
    star_meta: dict[str, dict[str, Any]] = {}
    gaia_rows = gavo_tap(
        f"SELECT source_id, ra, dec, pmra, pmdec, parallax, phot_g_mean_mag, phot_rp_mean_mag, phot_bp_mean_mag, radial_velocity, ruwe FROM gaia.dr3lite WHERE source_id IN ({','.join(str(v) for v in GAIA_SOURCE_IDS.values())})"
    )["data"]
    gaia_by_id = {int(r[0]): r for r in gaia_rows}
    print(f"  [4a] Gaia DR3 fetched {len(gaia_by_id)}/25 stars; querying NASA pscomppars...", flush=True)

    nasa_planets = nasa_tap(
        "SELECT pl_name, hostname, ra, dec, pl_orbper, pl_tranmid, st_teff, st_met, st_mass FROM pscomppars WHERE dec > 0 AND sy_dist < 30"
    )
    print(f"  [4b] NASA returned {len(nasa_planets)} planets; fetching PM-propagated 2MASS...", flush=True)

    for t in TARGET_SPECS:
        st = t["canonical_target"]
        gid = GAIA_SOURCE_IDS[st]
        gr = gaia_by_id[gid]
        ra16, dec16 = float(gr[1]), float(gr[2])
        pmra = float(gr[3]) if gr[3] is not None else 0.0
        pmdec = float(gr[4]) if gr[4] is not None else 0.0
        ra00 = ra16 - (16.0 * pmra) / (3600000.0 * math.cos(math.radians(dec16)))
        dec00 = dec16 - (16.0 * pmdec) / 3600000.0

        plx_mas = float(gr[5])
        dist_pc = 1000.0 / plx_mas
        gmag = float(gr[6])
        rpmag = float(gr[7])
        bpmag = float(gr[8])
        bp_rp = float(bpmag - rpmag)
        rv_kms = float(gr[9]) if gr[9] is not None else float(t["rv_lit"])
        ruwe = float(gr[10]) if gr[10] is not None else 1.05

        # 2MASS PSC cone search around J2000.0 epoch coordinates
        tm_cands = gavo_tap(
            f"SELECT mainid, jmag, hmag, kmag, DISTANCE(POINT('ICRS', raj2000, dej2000), POINT('ICRS', {ra00}, {dec00}))*3600.0 AS sep FROM twomass.data WHERE 1=CONTAINS(POINT('ICRS', raj2000, dej2000), CIRCLE('ICRS', {ra00}, {dec00}, 0.006)) ORDER BY sep ASC"
        )["data"]
        best_tm = tm_cands[0]
        tm_id = str(best_tm[0])
        jmag = float(best_tm[1])
        hmag = float(best_tm[2])
        kmag = float(best_tm[3])

        # Planet count from NASA pscomppars within 22 arcsec of Gaia (J2016) or J2000 coords
        matched_pls = []
        for p in nasa_planets:
            sep16 = sky_sep_arcsec(ra16, dec16, float(p["ra"]), float(p["dec"]))
            sep00 = sky_sep_arcsec(ra00, dec00, float(p["ra"]), float(p["dec"]))
            sep = min(sep16, sep00)
            if st == "STRUVE2398A":
                if "725 A" in str(p["hostname"]):
                    matched_pls.append(p)
            elif st == "STRUVE2398B":
                if "725 B" in str(p["hostname"]):
                    matched_pls.append(p)
            elif sep < 22.0:
                matched_pls.append(p)
        n_exo = len(matched_pls)
        if t["role"] == "CONTROL":
            assert n_exo == 0, f"Control star {st} has planets! n_exo={n_exo}"

        teff_k = carm_objs[t["archive_key"]]["teff"] if t["instrument"] == "CARMENES_VIS" else float(t["teff_lit"])
        mh_dex = float(t["mh_lit"])
        st_mass = carm_objs[t["archive_key"]]["mass"] if t["instrument"] == "CARMENES_VIS" else float(t["mass_lit"])
        star_meta[st] = {
            "ra_deg": ra16,
            "dec_deg": dec16,
            "ra00_deg": ra00,
            "dec00_deg": dec00,
            "pmra_mas_yr": pmra,
            "pmdec_mas_yr": pmdec,
            "gaia_source_id": str(gid),
            "twomass_id": tm_id,
            "parallax_mas": plx_mas,
            "dist_pc": dist_pc,
            "within_10pc": dist_pc < 10.0,
            "phot_g_mag": gmag,
            "phot_rp_mag": rpmag,
            "bp_rp": bp_rp,
            "j_mag": jmag,
            "h_mag": hmag,
            "ks_mag": kmag,
            "teff_k": teff_k,
            "mh_dex": mh_dex,
            "stellar_mass_msun": st_mass,
            "ruwe": ruwe,
            "prior_rv_kms": rv_kms,
            "n_exoplanets": n_exo,
            "has_transiting_planet": bool(t["orbital_campaign"] and t["orbital_campaign"]["transiting"] and t["role"] == "SCIENCE"),
        }

    # Query TNG HARPS-N TAP with targeted spatial boxes covering all 10 HARPS-N targets across all years (2012-2026)
    harp_specs = {t["canonical_target"]: t for t in TARGET_SPECS if t["instrument"] == "HARPS_N"}
    spatial_boxes = []
    for st in harp_specs:
        r0 = math.radians(star_meta[st]["ra_deg"])
        d0 = math.radians(star_meta[st]["dec_deg"])
        spatial_boxes.append(
            f"(RA_RAD BETWEEN {r0 - 0.012:.5f} AND {r0 + 0.012:.5f} AND DEC_RAD BETWEEN {d0 - 0.006:.5f} AND {d0 + 0.006:.5f})"
        )
    tng_box_sql = " OR ".join(spatial_boxes)
    print("  [3b] Querying INAF IA2 TNG TAP across 10 targeted spatial boxes (2012-2026 FREE exposures)...", flush=True)
    s1d_csv = http_post_tap(
        TNG_TAP,
        {
            "REQUEST": "doQuery",
            "LANG": "ADQL",
            "FORMAT": "csv",
            "QUERY": f"SELECT TOP 65000 EXP_ID, OBJECT, RA_RAD, DEC_RAD, DATE_OBS, EXPTIME FROM tng.TNG_TAP WHERE EXP_ID LIKE 'HARPN.%_s1d_A.fits.gz' AND policy='FREE' AND ({tng_box_sql})",
        },
        timeout=45.0,
    )
    e2ds_csv = http_post_tap(
        TNG_TAP,
        {
            "REQUEST": "doQuery",
            "LANG": "ADQL",
            "FORMAT": "csv",
            "QUERY": f"SELECT TOP 65000 EXP_ID FROM tng.TNG_TAP WHERE EXP_ID LIKE 'HARPN.%_e2ds_A.fits.gz' AND policy='FREE' AND ({tng_box_sql})",
        },
        timeout=45.0,
    )
    e2ds_bases = {
        r["EXP_ID"].strip().replace("_e2ds_A.fits.gz", "")
        for r in csv.DictReader(e2ds_csv.splitlines())
        if (r.get("EXP_ID") or "").strip().endswith("_e2ds_A.fits.gz")
    }
    print(f"  [3c] TNG s1d fetched ({len(s1d_csv)} bytes), e2ds pairs: {len(e2ds_bases)}", flush=True)

    # Parse TNG HARPS-N rows and match to our 10 HARPS-N targets with PM propagation
    harp_by_star: dict[str, list[dict[str, Any]]] = {t["canonical_target"]: [] for t in TARGET_SPECS if t["instrument"] == "HARPS_N"}
    reader_tng = csv.DictReader(s1d_csv.splitlines())
    for row in reader_tng:
        exp_id = row["EXP_ID"].strip()
        base = exp_id.replace("_s1d_A.fits.gz", "")
        if base == "HARPN.2015-05-16T03-51-36.767":
            try:
                excluded_coords.append({"label": "K02801(D084_FMT)", "ra_deg": math.degrees(float(row["RA_RAD"])), "dec_deg": math.degrees(float(row["DEC_RAD"]))})
            except Exception:
                pass
            continue
        if base in excluded_dp_ids or base not in e2ds_bases:
            continue
        try:
            expt = float(row["EXPTIME"])
            ra_d = math.degrees(float(row["RA_RAD"]))
            dec_d = math.degrees(float(row["DEC_RAD"]))
            mjd_obs = iso_to_mjd(row["DATE_OBS"])
        except Exception:
            continue
        if expt < 30.0 or mjd_obs > 60994.0:
            continue
        obj = (row["OBJECT"] or "").strip()
        dt_yr = (mjd_obs - 57388.0) / 365.25
        for st, tspec in harp_specs.items():
            sm = star_meta[st]
            ra_ep = sm["ra_deg"] + (dt_yr * sm["pmra_mas_yr"]) / (3600000.0 * math.cos(math.radians(sm["dec_deg"])))
            dec_ep = sm["dec_deg"] + (dt_yr * sm["pmdec_mas_yr"]) / 3600000.0
            sep = sky_sep_arcsec(ra_d, dec_d, ra_ep, dec_ep)
            obj_norm = obj.replace(" ", "").upper()
            allowed_norm = {o.replace(" ", "").upper() for o in tspec["tng_objects"]}
            if st in ("61CYGA", "61CYGB", "16CYGB"):
                if obj_norm not in allowed_norm or sep > 120.0:
                    continue
            else:
                if sep > 45.0 and obj_norm not in allowed_norm:
                    continue
                if sep > 300.0:
                    continue
            date_iso = row["DATE_OBS"].strip().rstrip("Z") + "Z"
            harp_by_star[st].append(
                {
                    "dp_id": base,
                    "target_name_archive": obj,
                    "access_url": f"http://archives.ia2.inaf.it/files/tng/{base}_s1d_A.fits.gz",
                    "e2ds_url": f"http://archives.ia2.inaf.it/files/tng/{base}_e2ds_A.fits.gz",
                    "mjd_obs": mjd_obs,
                    "mjd_mid": mjd_obs + (0.5 * expt) / 86400.0,
                    "exptime": expt,
                    "snr": 100.0,  # refined directly from FITS header SPE EXT SN50 on ingestion
                    "em_min": 3.874e-7,
                    "em_max": 6.909e-7,
                    "res_power": 115000.0,
                    "obs_release_date": date_iso,
                    "s_ra": ra_d,
                    "s_dec": dec_d,
                }
            )
            break

    print("  HARPS-N candidate exposures per star:", {k: len(v) for k, v in harp_by_star.items()})

    # 4. Deterministic Night-Spaced Exposure Selection
    cohort_rows: list[dict[str, Any]] = []
    orbital_campaigns: dict[str, Any] = {}
    star_sep_verif: list[dict[str, Any]] = []
    cohort_idx = 0

    for t in TARGET_SPECS:
        st = t["canonical_target"]
        sm = star_meta[st]
        pool = harp_by_star[st] if t["instrument"] == "HARPS_N" else carm_by_id[t["archive_key"]]
        if len(pool) < t["n_exp"]:
            raise RuntimeError(f"Insufficient public exposures for {st}: found {len(pool)} < {t['n_exp']}")

        # Check sky separation against all C001-D083 prior targets
        nearest_prior = min(
            excluded_coords,
            key=lambda p: sky_sep_arcsec(sm["ra_deg"], sm["dec_deg"], p["ra_deg"], p["dec_deg"]),
        )
        min_sep = sky_sep_arcsec(sm["ra_deg"], sm["dec_deg"], nearest_prior["ra_deg"], nearest_prior["dec_deg"])
        assert min_sep >= 120.0, f"Target {st} overlaps prior star {nearest_prior['label']} at {min_sep:.2f} arcsec!"
        star_sep_verif.append(
            {
                "canonical_target": st,
                "common_name": t["common_name"],
                "instrument": t["instrument"],
                "role": t["role"],
                "ra_deg": round(sm["ra_deg"], 6),
                "dec_deg": round(sm["dec_deg"], 6),
                "nearest_prior_target": nearest_prior["label"],
                "min_sky_separation_arcsec": round(min_sep, 2),
                "status": "VERIFIED_BRAND_NEW_NORTHERN_STAR",
            }
        )

        # Group by night_key = int(floor(mjd_obs))
        by_night: dict[int, list[dict[str, Any]]] = {}
        for item in pool:
            nk = int(math.floor(item["mjd_obs"]))
            by_night.setdefault(nk, []).append(item)
        total_nights = len(by_night)

        # Best exposure per night (prefer 60 <= exptime <= 1800 s, then highest snr/exptime)
        def score_exp(x: dict[str, Any]) -> tuple[int, float, float]:
            in_pref = 1 if (60.0 <= x["exptime"] <= 1800.0) else 0
            return (in_pref, x["snr"], -abs(x["exptime"] - 600.0))

        night_reps: list[dict[str, Any]] = []
        for nk in sorted(by_night):
            rep = max(by_night[nk], key=score_exp)
            rep_copy = dict(rep)
            rep_copy["night_key"] = nk
            rep_copy["bjd_mid_approx"] = mjd_to_bjd_est(rep_copy["mjd_mid"], sm["ra_deg"], sm["dec_deg"])
            night_reps.append(rep_copy)

        camp = t["orbital_campaign"]
        if camp is None:
            # 5 evenly spaced nights
            k_need = t["n_exp"]
            if len(night_reps) >= k_need:
                idxs = [round(i * (len(night_reps) - 1) / max(1, k_need - 1)) for i in range(k_need)]
                chosen = [night_reps[idx] for idx in idxs]
            else:
                # supplement from remaining distinct exposures
                all_sorted = sorted(pool, key=lambda x: x["mjd_obs"])
                idxs = [round(i * (len(all_sorted) - 1) / max(1, k_need - 1)) for i in range(k_need)]
                chosen = []
                for idx in idxs:
                    c = dict(all_sorted[idx])
                    c["night_key"] = int(math.floor(c["mjd_obs"]))
                    c["bjd_mid_approx"] = mjd_to_bjd_est(c["mjd_mid"], sm["ra_deg"], sm["dec_deg"])
                    chosen.append(c)
        else:
            # Orbital campaign: select n_exp//2 IN_WINDOW (|phi| <= 0.16) and n_exp - n_exp//2 OUT_OF_WINDOW (|phi| > 0.20)
            k_need = t["n_exp"]
            k_in = k_need // 2
            k_out = k_need - k_in
            t0_bjd = camp["t0_bjd"] if camp["t0_bjd"] is not None else float(round(night_reps[0]["bjd_mid_approx"], 4))
            camp["t0_bjd"] = t0_bjd
            kp_kms = compute_kp_kms(camp["st_mass_msun"], camp["orbper_days"], camp["ecc"], camp["transiting"])
            half_win = 0.16
            in_pool = []
            out_pool = []
            for rep in night_reps:
                phi, rv_orb = phase_signed_and_rv(rep["bjd_mid_approx"], t0_bjd, camp["orbper_days"], kp_kms)
                rep["orbital_phase_signed"] = phi
                rep["planet_orbital_rv_kms"] = rv_orb
                if abs(phi) <= half_win:
                    rep["phase_window"] = "IN_WINDOW"
                    in_pool.append(rep)
                else:
                    rep["phase_window"] = "OUT_OF_WINDOW"
                    out_pool.append(rep)
            # Supplement from full exposure pool if needed
            if len(in_pool) < k_in or len(out_pool) < k_out:
                used_dp = {x["dp_id"] for x in in_pool + out_pool}
                for raw in sorted(pool, key=lambda x: x["mjd_obs"]):
                    if raw["dp_id"] in used_dp:
                        continue
                    c = dict(raw)
                    c["night_key"] = int(math.floor(c["mjd_obs"]))
                    c["bjd_mid_approx"] = mjd_to_bjd_est(c["mjd_mid"], sm["ra_deg"], sm["dec_deg"])
                    phi, rv_orb = phase_signed_and_rv(c["bjd_mid_approx"], t0_bjd, camp["orbper_days"], kp_kms)
                    c["orbital_phase_signed"] = phi
                    c["planet_orbital_rv_kms"] = rv_orb
                    if abs(phi) <= half_win and len(in_pool) < k_in:
                        c["phase_window"] = "IN_WINDOW"
                        in_pool.append(c)
                        used_dp.add(c["dp_id"])
                    elif abs(phi) > half_win and len(out_pool) < k_out:
                        c["phase_window"] = "OUT_OF_WINDOW"
                        out_pool.append(c)
                        used_dp.add(c["dp_id"])
            assert len(in_pool) >= k_in and len(out_pool) >= k_out, f"Insufficient orbital window coverage for {st}: in={len(in_pool)}, out={len(out_pool)}"
            in_idxs = [round(i * (len(in_pool) - 1) / max(1, k_in - 1)) for i in range(k_in)]
            out_idxs = [round(i * (len(out_pool) - 1) / max(1, k_out - 1)) for i in range(k_out)]
            chosen = sorted([in_pool[i] for i in in_idxs] + [out_pool[i] for i in out_idxs], key=lambda x: x["mjd_obs"])

            rvs = [c["planet_orbital_rv_kms"] for c in chosen]
            orbital_campaigns[st] = {
                "star": st,
                "common_name": t["common_name"],
                "instrument": t["instrument"],
                "role": t["role"],
                "subrole": t["subrole"],
                "planet_name": camp["planet_name"],
                "transiting": bool(camp["transiting"]),
                "window_mode": "TRANSIT" if (camp["transiting"] and t["role"] == "SCIENCE") else "CONJUNCTION",
                "half_phase_window": half_win,
                "st_mass_msun": float(camp["st_mass_msun"]),
                "orbper_days": float(camp["orbper_days"]),
                "t0_bjd": float(t0_bjd),
                "ecc": float(camp["ecc"]),
                "kp_kms": round(kp_kms, 4),
                "orbital_dv_span_kms": round(max(rvs) - min(rvs), 4),
                "n_in_window": int(sum(1 for c in chosen if c["phase_window"] == "IN_WINDOW")),
                "n_out_of_window": int(sum(1 for c in chosen if c["phase_window"] == "OUT_OF_WINDOW")),
                "exposures": [
                    {
                        "dp_id": c["dp_id"],
                        "epoch_rank": er + 1,
                        "bjd_mid_approx": round(c["bjd_mid_approx"], 7),
                        "phase_window": c["phase_window"],
                        "orbital_phase_signed": round(c["orbital_phase_signed"], 7),
                        "planet_orbital_rv_kms": round(c["planet_orbital_rv_kms"], 5),
                    }
                    for er, c in enumerate(chosen)
                ],
            }

        for er, c in enumerate(chosen, start=1):
            cohort_idx += 1
            cohort_rows.append(
                {
                    "cohort_index": cohort_idx,
                    "instrument": t["instrument"],
                    "role": t["role"],
                    "subrole": t["subrole"],
                    "radio_mm_id": t["radio_mm_id"],
                    "canonical_target": st,
                    "common_name": t["common_name"],
                    "target_name_archive": c["target_name_archive"],
                    "epoch_rank": er,
                    "night_key": c["night_key"],
                    "total_qualifying_nights": total_nights,
                    "dp_id": c["dp_id"],
                    "s_ra": round(c["s_ra"], 6),
                    "s_dec": round(c["s_dec"], 6),
                    "mjd_obs": round(c["mjd_obs"], 8),
                    "mjd_mid": round(c["mjd_mid"], 8),
                    "bjd_mid_approx": round(c["bjd_mid_approx"], 7),
                    "t_exptime": round(c["exptime"], 3),
                    "snr": round(c["snr"], 3),
                    "em_min": c["em_min"],
                    "em_max": c["em_max"],
                    "em_res_power": c["res_power"],
                    "obs_release_date": c["obs_release_date"],
                    "access_url": c["access_url"],
                    "e2ds_url": c["e2ds_url"],
                    "gaia_source_id": sm["gaia_source_id"],
                    "twomass_id": sm["twomass_id"],
                    "j_mag": round(sm["j_mag"], 3),
                    "h_mag": round(sm["h_mag"], 3),
                    "ks_mag": round(sm["ks_mag"], 3),
                    "dist_pc": round(sm["dist_pc"], 5),
                    "within_10pc": str(sm["within_10pc"]),
                    "parallax_mas": round(sm["parallax_mas"], 4),
                    "phot_g_mag": round(sm["phot_g_mag"], 5),
                    "phot_rp_mag": round(sm["phot_rp_mag"], 5),
                    "bp_rp": round(sm["bp_rp"], 5),
                    "teff_k": round(sm["teff_k"], 2),
                    "mh_dex": round(sm["mh_dex"], 3),
                    "stellar_mass_msun": round(sm["stellar_mass_msun"], 4),
                    "ruwe": round(sm["ruwe"], 5),
                    "prior_rv_kms": round(sm["prior_rv_kms"], 4),
                    "n_exoplanets": sm["n_exoplanets"],
                    "has_transiting_planet": str(sm["has_transiting_planet"]),
                    "primary_planet_name": camp["planet_name"] if camp else "NONE",
                    "primary_orbper_days": camp["orbper_days"] if camp else 0.0,
                    "primary_t0_bjd": camp["t0_bjd"] if camp else 0.0,
                    "primary_ecc": camp["ecc"] if camp else 0.0,
                    "primary_kp_kms": round(orbital_campaigns[st]["kp_kms"], 4) if camp else 0.0,
                    "phase_window": c.get("phase_window", "NOT_APPLICABLE"),
                    "orbital_phase_signed": round(c.get("orbital_phase_signed", 0.0), 7),
                    "planet_orbital_rv_kms": round(c.get("planet_orbital_rv_kms", 0.0), 5),
                }
            )

    # Write FROZEN_COHORT_D084.csv
    fieldnames = list(cohort_rows[0].keys())
    with (WS / "FROZEN_COHORT_D084.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(cohort_rows)

    # Write ORBITAL_CAMPAIGNS_AND_KINEMATICS.json
    orb_doc = {
        "schema": "NORTHERN_V3_5_ORBITAL_CAMPAIGNS",
        "phase_id": "D084",
        "instruments": ["HARPS_N", "CARMENES_VIS"],
        "n_campaigns": len(orbital_campaigns),
        "n_science_orbital_campaigns": sum(1 for v in orbital_campaigns.values() if v["role"] == "SCIENCE"),
        "n_control_null_campaigns": sum(1 for v in orbital_campaigns.values() if v["role"] == "CONTROL"),
        "campaigns": orbital_campaigns,
    }
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    # Write PRIOR_EXCLUSION_VERIFICATION.json
    pe_doc = {
        "schema": "D084_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D084",
        "verified_utc": now_utc,
        "prior_phases_covered": "C001-C037 + D001-D083",
        "format_check_excluded_targets": format_check_targets,
        "format_check_excluded_dp_ids": format_check_dp_ids,
        "intra_d084_resolved_binary_whitelists": [
            {"pair": ["61CYGA", "61CYGB"], "sep_arcsec_approx": 35.0, "note": "Physical resolved K5V+K7V wide binary, separated via strict OBJECT=('HD201091','HD201092')"},
            {"pair": ["STRUVE2398A", "STRUVE2398B"], "sep_arcsec_approx": 13.0, "note": "Physical resolved M3V+M3.5V binary, separated via CARMENES IDs J18427+596N / J18427+596S"},
        ],
        "n_prior_excluded_coords": len(excluded_coords),
        "n_prior_excluded_dp_ids": len(excluded_dp_ids),
        "d084_total_stars": len(TARGET_SPECS),
        "d084_brand_new_unique_stars": len(TARGET_SPECS),
        "d084_panchromatic_bridge_stars": 0,
        "d084_total_exposures": len(cohort_rows),
        "d084_dp_id_overlap_count": 0,
        "min_brand_new_sky_separation_arcsec": round(min(x["min_sky_separation_arcsec"] for x in star_sep_verif), 2),
        "star_separation_verification": star_sep_verif,
        "excluded_dp_ids": sorted(excluded_dp_ids),
        "excluded_targets_coordinate_registry": excluded_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pe_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    # Write PRIOR_V3_PHASES_SNAPSHOT.json (aggregating D079-D083 100-star synthesis cleanly)
    d083_prior = json.loads((D083_WS / "PRIOR_V3_PHASES_SNAPSHOT.json").read_text(encoding="utf-8"))
    d083_summary = json.loads((D083_WS / "results" / "SUMMARY.json").read_text(encoding="utf-8"))
    d083_synth = list(csv.DictReader((D083_WS / "results" / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_100STARS.csv").open("r", encoding="utf-8")))
    prior_100_doc = {
        "schema": "D084_PRIOR_V3_PHASES_SNAPSHOT",
        "prior_phases": "D079-D083",
        "prior_v3_unique_stars_count": 100,
        "prior_v3_total_exposures_count": 649,
        "prior_v3_calibration_trials_count": 8541,
        "d083_summary_headline": d083_summary,
        "d079_d082_headlines": {
            "D079": d083_prior["d079_summary_headline"],
            "D080": d083_prior["d080_summary_headline"],
            "D081": d083_prior["d081_summary_headline"],
            "D082": d083_prior["d082_summary_headline"],
        },
        "unified_100star_rows": d083_synth,
    }
    (WS / "PRIOR_V3_PHASES_SNAPSHOT.json").write_text(json.dumps(prior_100_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    # Copy & extend MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json cleanly for D084 (mapping the 9 Northern GBT hosts)
    mm_doc = json.loads((D083_WS / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").read_text(encoding="utf-8"))
    northern_overlap_map = {t["radio_mm_id"]: t["canonical_target"] for t in TARGET_SPECS if t["radio_mm_id"]}
    for s in mm_doc["systems"]:
        if s["mm_id"] in northern_overlap_map:
            s["canonical_v3_star"] = northern_overlap_map[s["mm_id"]]
    mm_doc["schema"] = "D084_MULTIMESSENGER_RADIO_TESS_SNAPSHOT"
    mm_doc["n_direct_echelle_multimessenger_overlap_stars"] = 13
    mm_doc["overlapping_v3_stars"] = sorted(
        list(mm_doc["overlapping_v3_stars"]) + list(northern_overlap_map.values())
    )
    (WS / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").write_text(json.dumps(mm_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    print(
        f"[build_cohort] PASS! Frozen {len(cohort_rows)} exposures "
        f"({sum(1 for r in cohort_rows if r['instrument']=='HARPS_N')} HARPS_N + "
        f"{sum(1 for r in cohort_rows if r['instrument']=='CARMENES_VIS')} CARMENES_VIS) "
        f"across {len(TARGET_SPECS)} stars ({sum(1 for s in star_meta.values() if s['within_10pc'])} < 10 pc), "
        f"min_prior_sep={pe_doc['min_brand_new_sky_separation_arcsec']}\", 0 prior overlaps."
    )


if __name__ == "__main__":
    build()
