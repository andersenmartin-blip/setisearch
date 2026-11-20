#!/usr/bin/env python3
"""
Phase D092 Cohort Builder & Prospective Lock Sealer:
`TECHNOSIGNATURE_V5_0_RPCA_RARITY_ELLIPSOID_PPO_MIRI_CCF`

Deterministically queries Gaia DR3, NASA Exoplanet Archive (`pscomppars`),
ESO Phase-3 TAP (`ivoa.ObsCore`), Archive Q (Phase D091), and Archive P
(Phase D090 MIRI MRS) strictly BEFORE `inputs_d092_v5_0/` exists.

Locks:
  - 28 stars (25 brand-new + 3 NIR Y-band CRIRES bridges; 6 CONTROL + 22 SCIENCE)
  - 57 fresh ESO Phase-3 exposures (~214 MiB <= 220 MiB hard cap) across:
      * ESO_HARPS  (12 stars x 2 = 24 exp; 4 PPO, 2 ETZ, 3 <10pc Ellipsoid, 3 CTRL)
      * ESO_FEROS  (10 stars x 2 = 20 exp; 3 PPO, 3 ETZ, 2 <10pc Ellipsoid, 2 CTRL)
      * ESO_CRIRES ( 6 stars     = 13 exp Y-band 9496-11205 A; 3 bridges + 2 SCI + 1 CTRL)
  - FROZEN_COHORT_D092.csv
  - ORBITAL_CAMPAIGNS_AND_KINEMATICS.json (campaigns #101-#109)
  - PRIOR_EXCLUSION_VERIFICATION.json (0 overlaps vs 492 C001-D091 coordinates & dp_ids)
  - PRIOR_V4_2_PHASES_SNAPSHOT.json (D079-D091 310-star synthesis + Archive Q/P pointers)
  - METHOD_LOCK.json & LOCK_RECEIPT.json (SHA-256 sealing before any science download)
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import io
import json
import math
import sys
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent
ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
if str(WS) not in sys.path:
    sys.path.insert(0, str(WS))

from v5_0_detector import (  # noqa: E402
    BASE_V5_0_CONFIG,
    DETECTOR_NAME,
    compute_ecliptic_lat_deg,
    compute_keplerian_kp_kms,
    compute_planet_orbital_rv_kms,
    compute_ppo_alignment_score,
    compute_sn1987a_ellipsoid_mjd,
)

ARCHIVE_P = ROOT / "archives" / "SETI_D090_V4_1_JWST_SPACE_THERMAL_IR_RESULTS_2026-11-19.zip"
ARCHIVE_P_SHA256 = "2940839e8613b0d388c9b922743ba8244852806411f28586696e59eb8d73841a"
ARCHIVE_P_PREFIX = "work_jwst_thermal_ir_20261119_d090_v4_1_nirspec_miri/"

ARCHIVE_Q = ROOT / "archives" / "SETI_D091_V4_2_ESO_TRIPLE_3ARM_RESULTS_2026-11-20.zip"
ARCHIVE_Q_SHA256 = "9da4739bdb413d675b9bc1f17dc9d60d5abc7944622714017cf1889a097b51d0"
ARCHIVE_Q_PREFIX = "work_eso_triple_3arm_20261120_d091_v4_2_xshooter_feros_giraffe/"

BAD_CAL_TOKENS = ("SKY", "DARK", "BIAS", "FLAT", "STD", "WAVE", "CAL", "THAR", "MOON", "SUN", "SOLAR")

TARGET_SPECS: list[dict[str, Any]] = [
    # ---------------- ESO_HARPS (12 stars x 2 = 24 exp ~ 123 MiB) ----------------
    {
        "instrument": "ESO_HARPS", "canonical_target": "HIP41378", "common_name": "HIP 41378",
        "role": "SCIENCE", "subrole": "PPO_6PLANET_TRANSITING_HARPS", "science_track": "PPO",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 600698184764497664,
        "n_target_exposures": 2, "orbital_campaign": True, "nasa_host": "HIP 41378",
        "teff_lit": 6238.7, "mh_lit": -0.05, "mass_lit": 1.15, "rv_lit": 50.6,
        "j_mag": 7.98, "h_mag": 7.77, "ks_mag": 7.72,
    },
    {
        "instrument": "ESO_HARPS", "canonical_target": "K2138", "common_name": "K2-138",
        "role": "SCIENCE", "subrole": "PPO_6PLANET_CHAIN_HARPS", "science_track": "PPO",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 2413596935442139520,
        "n_target_exposures": 2, "orbital_campaign": True, "nasa_host": "K2-138",
        "teff_lit": 5356.3, "mh_lit": 0.14, "mass_lit": 0.93, "rv_lit": 0.77,
        "j_mag": 10.89, "h_mag": 10.43, "ks_mag": 10.33,
    },
    {
        "instrument": "ESO_HARPS", "canonical_target": "HD3167", "common_name": "HD 3167",
        "role": "SCIENCE", "subrole": "PPO_4PLANET_USP_HARPS", "science_track": "PPO",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 2554032474712538880,
        "n_target_exposures": 2, "orbital_campaign": True, "nasa_host": "HD 3167",
        "teff_lit": 5338.0, "mh_lit": 0.04, "mass_lit": 0.85, "rv_lit": 19.40,
        "j_mag": 7.55, "h_mag": 7.20, "ks_mag": 7.07,
    },
    {
        "instrument": "ESO_HARPS", "canonical_target": "LHS1678", "common_name": "LHS 1678 (TOI-696)",
        "role": "SCIENCE", "subrole": "PPO_3PLANET_MDWARF_19PC_HARPS", "science_track": "PPO",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 4864160624337973248,
        "n_target_exposures": 2, "orbital_campaign": True, "nasa_host": "LHS 1678",
        "teff_lit": 3490.0, "mh_lit": -0.35, "mass_lit": 0.345, "rv_lit": 10.94,
        "j_mag": 9.12, "h_mag": 8.55, "ks_mag": 8.26,
    },
    {
        "instrument": "ESO_HARPS", "canonical_target": "HD28343", "common_name": "HD 28343 (GJ 169)",
        "role": "SCIENCE", "subrole": "ETZ_ECLIPTIC_11PC_HARPS", "science_track": "ETZ",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 145421309108301184,
        "n_target_exposures": 2, "orbital_campaign": False,
        "teff_lit": 3815.0, "mh_lit": 0.0, "mass_lit": 0.56, "rv_lit": -35.74,
        "j_mag": 5.69, "h_mag": 5.04, "ks_mag": 4.88,
    },
    {
        "instrument": "ESO_HARPS", "canonical_target": "HIP95417", "common_name": "HIP 95417 (HD 181938)",
        "role": "SCIENCE", "subrole": "ETZ_ECLIPTIC_NEAR_ZERO_BETA_HARPS", "science_track": "ETZ",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 6772521384023709696,
        "n_target_exposures": 2, "orbital_campaign": False,
        "teff_lit": 3959.2, "mh_lit": 0.0, "mass_lit": 0.58, "rv_lit": 52.39,
        "j_mag": 7.98, "h_mag": 7.36, "ks_mag": 7.15,
    },
    {
        "instrument": "ESO_HARPS", "canonical_target": "HD16160", "common_name": "HD 16160 (HR 753, GJ 105A)",
        "role": "SCIENCE", "subrole": "SN1987A_ELLIPSOID_7PC_HARPS", "science_track": "ELLIPSOID",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 19316224572460416,
        "n_target_exposures": 2, "orbital_campaign": False,
        "teff_lit": 4829.0, "mh_lit": -0.09, "mass_lit": 0.78, "rv_lit": 25.21,
        "j_mag": 4.15, "h_mag": 3.66, "ks_mag": 3.48,
    },
    {
        "instrument": "ESO_HARPS", "canonical_target": "GL250B", "common_name": "Gl 250 B",
        "role": "SCIENCE", "subrole": "SN1987A_ELLIPSOID_8PC_HARPS", "science_track": "ELLIPSOID",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 3101920046552857728,
        "n_target_exposures": 2, "orbital_campaign": False,
        "box_deg": 0.008, "exclude_target_tokens": ("50281", "250A"),
        "teff_lit": 3295.0, "mh_lit": 0.0, "mass_lit": 0.45, "rv_lit": -7.70,
        "j_mag": 6.58, "h_mag": 5.98, "ks_mag": 5.72,
    },
    {
        "instrument": "ESO_HARPS", "canonical_target": "GL465", "common_name": "Gl 465 (LHS 326)",
        "role": "SCIENCE", "subrole": "SN1987A_ELLIPSOID_8PC_HARPS", "science_track": "ELLIPSOID",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 3519785523672576384,
        "n_target_exposures": 2, "orbital_campaign": False,
        "teff_lit": 3218.6, "mh_lit": -0.45, "mass_lit": 0.34, "rv_lit": 51.06,
        "j_mag": 7.73, "h_mag": 7.21, "ks_mag": 6.95,
    },
    {
        "instrument": "ESO_HARPS", "canonical_target": "GJ3379", "common_name": "GJ 3379 (G 99-49)",
        "role": "CONTROL", "subrole": "NULL_5PC_MDWARF_CONTROL_HARPS", "science_track": "CONTROL",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 3316364602541746048,
        "n_target_exposures": 2, "orbital_campaign": False,
        "teff_lit": 3138.2, "mh_lit": 0.0, "mass_lit": 0.22, "rv_lit": 29.96,
        "j_mag": 6.91, "h_mag": 6.31, "ks_mag": 6.04,
    },
    {
        "instrument": "ESO_HARPS", "canonical_target": "GL693", "common_name": "Gl 693 (LHS 454)",
        "role": "CONTROL", "subrole": "NULL_5PC_MDWARF_CONTROL_HARPS", "science_track": "CONTROL",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 5918660719983560192,
        "n_target_exposures": 2, "orbital_campaign": False,
        "teff_lit": 3104.3, "mh_lit": -0.25, "mass_lit": 0.26, "rv_lit": -43.79,
        "j_mag": 6.86, "h_mag": 6.30, "ks_mag": 6.02,
    },
    {
        "instrument": "ESO_HARPS", "canonical_target": "HD43834", "common_name": "alpha Men (HD 43834)",
        "role": "CONTROL", "subrole": "NULL_10PC_GDWARF_CONTROL_HARPS", "science_track": "CONTROL",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 5264749303462961280,
        "n_target_exposures": 2, "orbital_campaign": False,
        "teff_lit": 5495.9, "mh_lit": 0.09, "mass_lit": 0.96, "rv_lit": 36.06,
        "j_mag": 3.87, "h_mag": 3.55, "ks_mag": 3.45,
    },
    # ---------------- ESO_FEROS (10 stars x 2 = 20 exp ~ 60 MiB) ----------------
    {
        "instrument": "ESO_FEROS", "canonical_target": "HD108236", "common_name": "HD 108236 (TOI-1233)",
        "role": "SCIENCE", "subrole": "PPO_5PLANET_TRANSITING_FEROS", "science_track": "PPO",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 6125644402384918784,
        "n_target_exposures": 2, "orbital_campaign": True, "nasa_host": "HD 108236",
        "teff_lit": 5645.6, "mh_lit": -0.28, "mass_lit": 0.87, "rv_lit": 16.91,
        "j_mag": 8.05, "h_mag": 7.72, "ks_mag": 7.64,
    },
    {
        "instrument": "ESO_FEROS", "canonical_target": "TOI5789", "common_name": "HD 191939 (TOI-5789)",
        "role": "SCIENCE", "subrole": "PPO_4PLANET_20PC_FEROS", "science_track": "PPO",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 1809360187275432832,
        "n_target_exposures": 2, "orbital_campaign": True, "nasa_host": "TOI-5789",
        "teff_lit": 5079.1, "mh_lit": -0.15, "mass_lit": 0.81, "rv_lit": -49.37,
        "j_mag": 6.13, "h_mag": 5.80, "ks_mag": 5.71,
    },
    {
        "instrument": "ESO_FEROS", "canonical_target": "TOI1203", "common_name": "HD 97658 / TOI-1203 (HD 96992)",
        "role": "SCIENCE", "subrole": "PPO_4PLANET_SUBGIANT_FEROS", "science_track": "PPO",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 5402390257832925952,
        "n_target_exposures": 2, "orbital_campaign": True, "nasa_host": "TOI-1203",
        "teff_lit": 5700.0, "mh_lit": -0.35, "mass_lit": 0.90, "rv_lit": 72.76,
        "j_mag": 7.42, "h_mag": 7.12, "ks_mag": 7.05,
    },
    {
        "instrument": "ESO_FEROS", "canonical_target": "ESPRI1542", "common_name": "LP 803-27 (ESPRI 1542-1928)",
        "role": "SCIENCE", "subrole": "ETZ_ECLIPTIC_9PC_FEROS", "science_track": "ETZ",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 6254033894121581952,
        "n_target_exposures": 2, "orbital_campaign": False,
        "teff_lit": 3450.0, "mh_lit": 0.0, "mass_lit": 0.42, "rv_lit": 83.18,
        "j_mag": 7.99, "h_mag": 7.40, "ks_mag": 7.13,
    },
    {
        "instrument": "ESO_FEROS", "canonical_target": "HATS521", "common_name": "GJ 3839 (HATS521-001)",
        "role": "SCIENCE", "subrole": "ETZ_ECLIPTIC_15PC_FEROS", "science_track": "ETZ",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 6302909449418261120,
        "n_target_exposures": 2, "orbital_campaign": False,
        "teff_lit": 3350.0, "mh_lit": 0.0, "mass_lit": 0.35, "rv_lit": -36.83,
        "j_mag": 8.42, "h_mag": 7.82, "ks_mag": 7.56,
    },
    {
        "instrument": "ESO_FEROS", "canonical_target": "HD56986", "common_name": "delta Gem (HD 56986)",
        "role": "SCIENCE", "subrole": "ETZ_ECLIPTIC_F_SUBGIANT_FEROS", "science_track": "ETZ",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 866177431955478144,
        "n_target_exposures": 2, "orbital_campaign": False,
        "teff_lit": 6900.0, "mh_lit": -0.05, "mass_lit": 1.65, "rv_lit": 0.15,
        "j_mag": 2.95, "h_mag": 2.75, "ks_mag": 2.68,
    },
    {
        "instrument": "ESO_FEROS", "canonical_target": "V2215OPH", "common_name": "V2215 Oph (HD 156026, 36 Oph C)",
        "role": "SCIENCE", "subrole": "SN1987A_ELLIPSOID_5PC_FEROS", "science_track": "ELLIPSOID",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 4109034455276324608,
        "n_target_exposures": 2, "orbital_campaign": False,
        "teff_lit": 4381.2, "mh_lit": -0.20, "mass_lit": 0.68, "rv_lit": -0.07,
        "j_mag": 4.24, "h_mag": 3.67, "ks_mag": 3.47,
    },
    {
        "instrument": "ESO_FEROS", "canonical_target": "GL618A", "common_name": "Gl 618 A (CNS31)",
        "role": "SCIENCE", "subrole": "SN1987A_ELLIPSOID_8PC_FEROS", "science_track": "ELLIPSOID",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 6021430250773348736,
        "n_target_exposures": 2, "orbital_campaign": False,
        "teff_lit": 3155.9, "mh_lit": -0.05, "mass_lit": 0.25, "rv_lit": 27.96,
        "j_mag": 6.79, "h_mag": 6.19, "ks_mag": 5.95,
    },
    {
        "instrument": "ESO_FEROS", "canonical_target": "HD217357", "common_name": "HD 217357 (GJ 884)",
        "role": "CONTROL", "subrole": "NULL_8PC_KDWARF_CONTROL_FEROS", "science_track": "CONTROL",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 2396530698208685312,
        "n_target_exposures": 2, "orbital_campaign": False,
        "teff_lit": 3828.1, "mh_lit": -0.10, "mass_lit": 0.56, "rv_lit": 15.85,
        "j_mag": 5.34, "h_mag": 4.70, "ks_mag": 4.48,
    },
    {
        "instrument": "ESO_FEROS", "canonical_target": "HD149661", "common_name": "12 Oph (HD 149661)",
        "role": "CONTROL", "subrole": "NULL_9PC_K0V_CONTROL_FEROS", "science_track": "CONTROL",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 4358031335898505472,
        "n_target_exposures": 2, "orbital_campaign": False,
        "teff_lit": 5106.7, "mh_lit": 0.02, "mass_lit": 0.89, "rv_lit": -13.10,
        "j_mag": 4.30, "h_mag": 3.85, "ks_mag": 3.75,
    },
    # ---------------- ESO_CRIRES Y-band (6 stars = 13 exp ~ 31 MiB) ----------------
    {
        "instrument": "ESO_CRIRES", "canonical_target": "TRAPPIST1", "common_name": "TRAPPIST-1",
        "role": "SCIENCE", "subrole": "PPO_7PLANET_YBAND_CRIRES_BRIDGE", "science_track": "PPO_BRIDGE",
        "panchromatic_bridge": True, "radio_mm_id": "", "gaia_source_id": 2635476908753563008,
        "n_target_exposures": 3, "orbital_campaign": True, "nasa_host": "TRAPPIST-1",
        "box_deg": 0.08,
        "teff_lit": 2566.0, "mh_lit": 0.04, "mass_lit": 0.0898, "rv_lit": -51.7,
        "j_mag": 11.35, "h_mag": 10.72, "ks_mag": 10.30,
    },
    {
        "instrument": "ESO_CRIRES", "canonical_target": "K218", "common_name": "K2-18 (EPIC 201912552)",
        "role": "SCIENCE", "subrole": "HYCEAN_ORBITAL_YBAND_CRIRES_BRIDGE", "science_track": "PPO_BRIDGE",
        "panchromatic_bridge": True, "radio_mm_id": "", "gaia_source_id": 3910747531814692736,
        "n_target_exposures": 2, "orbital_campaign": True, "nasa_host": "K2-18",
        "box_deg": 0.08,
        "teff_lit": 3457.0, "mh_lit": 0.12, "mass_lit": 0.495, "rv_lit": 0.02,
        "j_mag": 9.76, "h_mag": 9.14, "ks_mag": 8.90,
    },
    {
        "instrument": "ESO_CRIRES", "canonical_target": "PROXIMACEN", "common_name": "Proxima Centauri (GJ 551)",
        "role": "SCIENCE", "subrole": "NEAREST_1PC_YBAND_CRIRES_BRIDGE", "science_track": "BRIDGE",
        "panchromatic_bridge": True, "radio_mm_id": "", "gaia_source_id": 5853498713190525696,
        "n_target_exposures": 2, "orbital_campaign": False,
        "box_deg": 0.10, "dist_lit": 1.3019,
        "teff_lit": 2829.3, "mh_lit": 0.05, "mass_lit": 0.122, "rv_lit": -21.94,
        "j_mag": 5.36, "h_mag": 4.84, "ks_mag": 4.38,
    },
    {
        "instrument": "ESO_CRIRES", "canonical_target": "J16570570", "common_name": "2MASS J16570570-0420559 (GJ 1207)",
        "role": "SCIENCE", "subrole": "SN1987A_ELLIPSOID_8PC_YBAND_CRIRES", "science_track": "ELLIPSOID",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 4365609170043180416,
        "n_target_exposures": 2, "orbital_campaign": False, "box_deg": 0.06,
        "teff_lit": 3001.3, "mh_lit": 0.0, "mass_lit": 0.24, "rv_lit": -4.18,
        "j_mag": 7.97, "h_mag": 7.44, "ks_mag": 7.12,
    },
    {
        "instrument": "ESO_CRIRES", "canonical_target": "HD101065", "common_name": "Przybylski's Star (HD 101065)",
        "role": "SCIENCE", "subrole": "PRZYBYLSKI_CHEM_PECULIAR_YBAND_CRIRES", "science_track": "RPCA_STRESS",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 5372587514128271232,
        "n_target_exposures": 2, "orbital_campaign": False, "box_deg": 0.06,
        "teff_lit": 6131.2, "mh_lit": 0.0, "mass_lit": 1.45, "rv_lit": 9.8,
        "j_mag": 7.05, "h_mag": 6.80, "ks_mag": 6.72,
    },
    {
        "instrument": "ESO_CRIRES", "canonical_target": "HD201601", "common_name": "gamma Equ (HD 201601)",
        "role": "CONTROL", "subrole": "NULL_35PC_ROAP_CONTROL_YBAND_CRIRES", "science_track": "CONTROL",
        "panchromatic_bridge": False, "radio_mm_id": "", "gaia_source_id": 1744662586614707072,
        "n_target_exposures": 2, "orbital_campaign": False, "box_deg": 0.06,
        "teff_lit": 7404.3, "mh_lit": 0.1, "mass_lit": 1.70, "rv_lit": -16.5,
        "j_mag": 4.28, "h_mag": 4.18, "ks_mag": 4.13,
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


def sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    c = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c)))) * 3600.0


def tap_csv(url_base: str, query: str, param_key: str = "QUERY") -> list[dict[str, str]]:
    params = {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", param_key: query}
    if param_key == "query":
        params = {"query": query, "format": "csv"}
    url = url_base + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-D092/1.0"})
    with urllib.request.urlopen(req, timeout=35) as resp:
        txt = resp.read().decode("utf-8", errors="replace")
    return list(csv.DictReader(io.StringIO(txt)))


def tap_json(url_base: str, query: str) -> dict[str, Any]:
    url = url_base + "?" + urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "json", "QUERY": query})
    req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-D092/1.0"})
    with urllib.request.urlopen(req, timeout=35) as resp:
        return json.loads(resp.read().decode("utf-8"))


def infer_teff_from_bprp(bp_mag: float | None, rp_mag: float | None, fallback: float) -> float:
    """Empirical Mamajek BP-RP main-sequence Teff approximation when Gaia GSP-Phot is absent."""
    if bp_mag is None or rp_mag is None:
        return float(fallback)
    c = float(bp_mag) - float(rp_mag)
    if not (-0.5 <= c <= 4.5):
        return float(fallback)
    # Smooth piecewise relation anchored across F/G/K/M dwarfs
    return float(max(2400.0, min(9500.0, 9600.0 * math.exp(-0.56 * c) + 1200.0)))


def fetch_eso_pool_for_target(
    spec: dict[str, Any],
    ra_deg: float,
    dec_deg: float,
    excluded_dp_ids: set[str],
) -> list[dict[str, Any]]:
    inst = spec["instrument"]
    eso_inst = inst.replace("ESO_", "")
    box = float(spec.get("box_deg") or 0.04)
    extra = " AND em_min BETWEEN 0.00000093 AND 0.00000097" if inst == "ESO_CRIRES" else ""
    adql = (
        "SELECT dp_id, target_name, s_ra, s_dec, t_min, t_max, t_exptime, "
        "em_min, em_max, em_res_power, access_estsize, access_url "
        "FROM ivoa.ObsCore "
        f"WHERE dataproduct_type='spectrum' AND instrument_name='{eso_inst}'{extra} "
        f"AND access_estsize <= 6000 "
        f"AND s_ra BETWEEN {ra_deg - box:.5f} AND {ra_deg + box:.5f} "
        f"AND s_dec BETWEEN {dec_deg - box:.5f} AND {dec_deg + box:.5f}"
    )
    rows = tap_csv("https://archive.eso.org/tap_obs/sync", adql)
    excl_toks = tuple(t.upper() for t in spec.get("exclude_target_tokens", ()))
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in rows:
        dp_id = (r.get("dp_id") or "").strip()
        if not dp_id or dp_id in seen or dp_id in excluded_dp_ids:
            continue
        seen.add(dp_id)
        tn = (r.get("target_name") or "").upper()
        if any(b in tn for b in BAD_CAL_TOKENS):
            continue
        if excl_toks and any(et in tn for et in excl_toks):
            continue
        t_min = float(r["t_min"])
        t_max = float(r.get("t_max") or t_min)
        mjd_obs = 0.5 * (t_min + t_max)
        # Note access_estsize is reported in KiB by ESO TAP; actual download matches ~kb * 1024
        kb = int(round(float(r.get("access_estsize") or 3000)))
        est_bytes = kb * 1024
        url = f"https://dataportal.eso.org/dataPortal/file/{dp_id}"
        assert "dataportal.eso.org/dataPortal/file/" in url
        res_pow = float(r.get("em_res_power") or (115000.0 if inst == "ESO_HARPS" else (86000.0 if inst == "ESO_CRIRES" else 48000.0)))
        grating = "CRIRES_YJ" if inst == "ESO_CRIRES" else ("HARPS" if inst == "ESO_HARPS" else "FEROS")
        out.append({
            "dp_id": dp_id,
            "target_name": r.get("target_name") or "",
            "mjd_obs": mjd_obs,
            "t_exptime": float(r.get("t_exptime") or 60.0),
            "resolving_power": res_pow,
            "grating": grating,
            "f1_id": dp_id,
            "f1_url": url,
            "f1_bytes": est_bytes,
            "f2_id": "",
            "f2_url": "",
            "f2_bytes": 0,
            "f3_id": "",
            "f3_url": "",
            "f3_bytes": 0,
            "total_bytes": est_bytes,
        })
    out.sort(key=lambda x: (x["mjd_obs"], x["dp_id"]))
    return out


def select_exposures(
    spec: dict[str, Any],
    pool: list[dict[str, Any]],
    mjd_ell: float | None = None,
    ppo_planets: list[tuple[float, float]] | None = None,
    ref_planet: tuple[float, float, float] | None = None,
) -> list[dict[str, Any]]:
    k = int(spec["n_target_exposures"])
    if len(pool) < k:
        raise RuntimeError(f"{spec['canonical_target']}: need {k} exposures, found {len(pool)}")
    track = spec["science_track"]

    if "ELLIPSOID" in track and mjd_ell is not None:
        in_win = [p for p in pool if abs(p["mjd_obs"] - mjd_ell) <= 180.0]
        if len(in_win) < k:
            raise RuntimeError(f"{spec['canonical_target']}: only {len(in_win)} exposures within +-180d of {mjd_ell:.1f}")
        # Prefer pair inside +-180d with >=0.5 d baseline when available, minimizing sum |dt|
        if k == 2:
            best_pair = None
            best_key = (1, 1e18)
            for i in range(len(in_win)):
                for j in range(i + 1, len(in_win)):
                    dt_sep = abs(in_win[j]["mjd_obs"] - in_win[i]["mjd_obs"])
                    dt_ell = abs(in_win[i]["mjd_obs"] - mjd_ell) + abs(in_win[j]["mjd_obs"] - mjd_ell)
                    key = (0 if dt_sep >= 0.5 else 1, dt_ell)
                    if key < best_key:
                        best_key = key
                        best_pair = [in_win[i], in_win[j]]
            return sorted(best_pair, key=lambda x: (x["mjd_obs"], x["dp_id"]))
        in_win.sort(key=lambda x: abs(x["mjd_obs"] - mjd_ell))
        return sorted(in_win[:k], key=lambda x: (x["mjd_obs"], x["dp_id"]))

    if "PPO" in track and ref_planet is not None and len(pool) >= k:
        per, t0, kp = ref_planet
        # Precompute orbital RV and PPO alignment per exposure
        for p in pool:
            bjd = p["mjd_obs"] + 2400000.5
            _, v_orb = compute_planet_orbital_rv_kms(bjd, t0, per, kp)
            p["_v_orb"] = v_orb
            p["_ppo"] = compute_ppo_alignment_score(bjd, ppo_planets or [])
        if k == 2:
            # Cap candidate checks for large HARPS pools via extrema + best PPO epochs
            if len(pool) > 80:
                by_v = sorted(pool, key=lambda x: x["_v_orb"])
                by_ppo = sorted(pool, key=lambda x: x["_ppo"])
                sub_ids = {x["dp_id"] for x in by_v[:25] + by_v[-25:] + by_ppo[:30]}
                sub = [x for x in pool if x["dp_id"] in sub_ids]
            else:
                sub = list(pool)
            best_pair = None
            best_key = (2, 2, 1e9, 1e9)
            for i in range(len(sub)):
                for j in range(i + 1, len(sub)):
                    dv = abs(sub[i]["_v_orb"] - sub[j]["_v_orb"])
                    dt = abs(sub[i]["mjd_obs"] - sub[j]["mjd_obs"])
                    ppo_sum = sub[i]["_ppo"] + sub[j]["_ppo"]
                    tier_dv = 0 if dv >= 10.0 else (1 if dv >= 5.0 else 2)
                    tier_dt = 0 if dt >= 0.5 else 1
                    key = (tier_dv, tier_dt, ppo_sum, -dv)
                    if key < best_key:
                        best_key = key
                        best_pair = [sub[i], sub[j]]
            return sorted(best_pair, key=lambda x: (x["mjd_obs"], x["dp_id"]))
        # k == 3 (TRAPPIST-1 CRIRES Y-band): only 3 exist!
        return sorted(pool[:k], key=lambda x: (x["mjd_obs"], x["dp_id"]))

    # ETZ / CONTROL / BRIDGE / RPCA_STRESS: maximize time baseline cleanly
    if k == 2:
        if len(pool) >= 2:
            return [pool[0], pool[-1]]
    idxs = [int(round(i * (len(pool) - 1) / (k - 1))) for i in range(k)]
    return [pool[i] for i in idxs]


def main() -> None:
    inp_dir = ROOT / "inputs_d092_v5_0"
    if inp_dir.exists():
        raise RuntimeError(f"Prospective hygiene violation: {inp_dir} already exists before lock!")

    if sha256_file(ARCHIVE_P) != ARCHIVE_P_SHA256:
        raise RuntimeError("Companion Archive P SHA-256 mismatch!")
    if sha256_file(ARCHIVE_Q) != ARCHIVE_Q_SHA256:
        raise RuntimeError("Companion Archive Q SHA-256 mismatch!")

    print("1. Extracting D091 Archive Q exclusion registry & D079-D091 310-star synthesis...", flush=True)
    with zipfile.ZipFile(ARCHIVE_Q, "r") as zq:
        pe91 = json.loads(zq.read(ARCHIVE_Q_PREFIX + "PRIOR_EXCLUSION_VERIFICATION.json").decode("utf-8"))
        sum91 = json.loads(zq.read(ARCHIVE_Q_PREFIX + "results/SUMMARY.json").decode("utf-8"))
        coh91_rows = list(csv.DictReader(zq.read(ARCHIVE_Q_PREFIX + "FROZEN_COHORT_D091.csv").decode("utf-8").splitlines()))
        u310_rows = list(csv.DictReader(zq.read(ARCHIVE_Q_PREFIX + "results/UNIFIED_PANCHROMATIC_V4_2_SYNTHESIS_310STARS.csv").decode("utf-8").splitlines()))
        br35_rows = list(csv.DictReader(zq.read(ARCHIVE_Q_PREFIX + "results/PANCHROMATIC_BRIDGE_35STARS.csv").decode("utf-8").splitlines()))
        comb_u_rows = list(csv.DictReader(zq.read(ARCHIVE_Q_PREFIX + "results/ALLSKY_COMB_V4_1_UNIFIED_D079_D091.csv").decode("utf-8").splitlines()))
        comb_c_rows = list(csv.DictReader(zq.read(ARCHIVE_Q_PREFIX + "results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D091.csv").decode("utf-8").splitlines()))

    prior_v42_snap = {
        "schema": "D092_PRIOR_V4_2_PHASES_SNAPSHOT",
        "prior_phases": "D079-D091",
        "source_archive_q_name": ARCHIVE_Q.name,
        "source_archive_q_sha256": ARCHIVE_Q_SHA256,
        "source_archive_p_name": ARCHIVE_P.name,
        "source_archive_p_sha256": ARCHIVE_P_SHA256,
        "prior_v42_unique_stars_count": len(u310_rows),
        "prior_v42_within_10pc_count": sum(1 for r in u310_rows if r["within_10pc"] == "True"),
        "prior_v42_total_exposures_count": sum(int(r["n_exposures_total"]) for r in u310_rows),
        "prior_cumulative_integration_hours": sum91["unified_310star_panchromatic_v4_2_synthesis"]["total_integration_hours_d079_d091"],
        "prior_v42_calibration_trials_count": sum91["unified_310star_panchromatic_v4_2_synthesis"]["total_calibration_trials_d079_d091"],
        "prior_v2_false_alarms_eliminated_total": sum91["unified_310star_panchromatic_v4_2_synthesis"]["v2_false_alarms_eliminated_total"],
        "prior_cumulative_orbital_campaigns_count": sum91["unified_310star_panchromatic_v4_2_synthesis"]["cumulative_orbital_campaigns"],
        "d091_summary_headline": sum91,
        "unified_310star_rows": u310_rows,
        "d091_bridge_35star_rows": br35_rows,
        "allsky_comb_unified_d079_d091": comb_u_rows,
        "allsky_comb_candidates_d079_d091": comb_c_rows,
    }
    (WS / "PRIOR_V4_2_PHASES_SNAPSHOT.json").write_text(json.dumps(prior_v42_snap, indent=2) + "\n", encoding="utf-8")

    excluded_dp_ids: set[str] = set(pe91["excluded_dp_ids"])
    for r in coh91_rows:
        for k in ("dp_id", "f1_id", "f2_id", "f3_id"):
            if r.get(k):
                excluded_dp_ids.add(r[k])

    excluded_coords = list(pe91["excluded_targets_coordinate_registry"])
    seen_lbl = {c["label"] for c in excluded_coords}
    for r in coh91_rows:
        if r.get("panchromatic_bridge") == "True":
            continue
        lbl = f"{r['canonical_target']}(D091)"
        if lbl not in seen_lbl:
            excluded_coords.append({"label": lbl, "ra_deg": float(r["s_ra"]), "dec_deg": float(r["s_dec"])})
            seen_lbl.add(lbl)
    # Include D091 bridge targets' coordinates too for strict spatial exclusion check of D092 brand-new stars
    for s in pe91.get("star_separation_verification", []):
        lbl = f"{s['canonical_target']}(D091)"
        if lbl not in seen_lbl:
            excluded_coords.append({"label": lbl, "ra_deg": float(s["ra_deg"]), "dec_deg": float(s["dec_deg"])})
            seen_lbl.add(lbl)

    print("2. Querying Gaia DR3 & NASA Exoplanet Archive pscomppars...", flush=True)
    gids = [s["gaia_source_id"] for s in TARGET_SPECS]
    gd = tap_json(
        "https://gea.esac.esa.int/tap-server/tap/sync",
        f"SELECT source_id,ra,dec,pmra,pmdec,parallax,phot_g_mean_mag,phot_bp_mean_mag,phot_rp_mean_mag,teff_gspphot,mh_gspphot,radial_velocity FROM gaiadr3.gaia_source WHERE source_id IN ({','.join(map(str, gids))})",
    )
    gcols = [m["name"] for m in gd["metadata"]]
    gaia_by_id = {int(row[0]): dict(zip(gcols, row)) for row in gd["data"]}

    nasa_rows = tap_csv(
        "https://exoplanetarchive.ipac.caltech.edu/TAP/sync",
        "SELECT pl_name,hostname,ra,dec,pl_orbper,pl_tranmid,pl_orbeccen,tran_flag,st_mass,st_teff,st_met,st_radv,sy_dist FROM pscomppars WHERE ra IS NOT NULL AND dec IS NOT NULL",
        param_key="query",
    )
    nasa_by_host: dict[str, list[dict[str, str]]] = {}
    for r in nasa_rows:
        if r.get("hostname"):
            nasa_by_host.setdefault(r["hostname"], []).append(r)

    print(f"3. Querying ESO Phase-3 TAP ObsCore across {len(TARGET_SPECS)} targets...", flush=True)
    with ThreadPoolExecutor(max_workers=10) as ex:
        all_pools = list(ex.map(
            lambda sp: fetch_eso_pool_for_target(
                sp,
                float(gaia_by_id[sp["gaia_source_id"]]["ra"]),
                float(gaia_by_id[sp["gaia_source_id"]]["dec"]),
                excluded_dp_ids,
            ),
            TARGET_SPECS,
        ))

    cohort_rows: list[dict[str, Any]] = []
    campaigns_doc: dict[str, Any] = {}
    sep_verif: list[dict[str, Any]] = []
    brand_new_coords: list[dict[str, Any]] = []
    all_star_coords: list[dict[str, Any]] = []
    total_bytes = 0
    camp_num = 100

    for spec, pool in zip(TARGET_SPECS, all_pools):
        st = spec["canonical_target"]
        g = gaia_by_id[spec["gaia_source_id"]]
        ra_deg = float(g["ra"])
        dec_deg = float(g["dec"])
        pmra = float(g["pmra"]) if g.get("pmra") is not None else 0.0
        pmdec = float(g["pmdec"]) if g.get("pmdec") is not None else 0.0
        par_mas = float(g["parallax"])
        par_err = 0.05
        dist_pc = float(spec.get("dist_lit") or (1000.0 / par_mas))
        dist_err_pc = max(0.01, dist_pc * (par_err / max(1.0, par_mas)))
        within_10pc = dist_pc <= 10.0

        phot_g = float(g["phot_g_mean_mag"]) if g.get("phot_g_mean_mag") is not None else 12.0
        phot_bp = float(g["phot_bp_mean_mag"]) if g.get("phot_bp_mean_mag") is not None else None
        phot_rp = float(g["phot_rp_mean_mag"]) if g.get("phot_rp_mean_mag") is not None else None

        nh_list = nasa_by_host.get(spec.get("nasa_host", ""), [])
        nasa_teff = next((float(r["st_teff"]) for r in nh_list if r.get("st_teff")), None)
        nasa_mass = next((float(r["st_mass"]) for r in nh_list if r.get("st_mass")), None)

        if g.get("teff_gspphot") is not None:
            teff_k = float(g["teff_gspphot"])
        elif nasa_teff is not None:
            teff_k = nasa_teff
        elif phot_bp is not None and phot_rp is not None:
            teff_k = infer_teff_from_bprp(phot_bp, phot_rp, float(spec["teff_lit"]))
        else:
            teff_k = float(spec["teff_lit"])

        mh_dex = float(g["mh_gspphot"]) if g.get("mh_gspphot") is not None else float(spec["mh_lit"])
        prior_rv = float(g["radial_velocity"]) if g.get("radial_velocity") is not None else float(spec["rv_lit"])
        mass_msun = float(nasa_mass if nasa_mass is not None else spec["mass_lit"])

        pl_hits = [
            r for r in nasa_rows
            if abs(float(r["dec"]) - dec_deg) < 0.05 and sep_arcsec(ra_deg, dec_deg, float(r["ra"]), float(r["dec"])) < 90.0
        ]
        n_pl = len({r["pl_name"] for r in pl_hits})
        if spec["role"] == "CONTROL":
            assert n_pl == 0, f"CONTROL star {st} has {n_pl} planets in NASA pscomppars!"
        has_tr = any(str(r.get("tran_flag") or "0") == "1" for r in pl_hits)

        beta_ecl = compute_ecliptic_lat_deg(ra_deg, dec_deg)
        mjd_ell, _, mjd_ell_err = compute_sn1987a_ellipsoid_mjd(ra_deg, dec_deg, dist_pc, dist_err_pc)

        if spec["science_track"] == "ETZ":
            assert abs(beta_ecl) <= 0.264, f"ETZ target {st} |beta|={abs(beta_ecl):.3f} > 0.264 deg!"

        ppo_planets: list[tuple[float, float]] = []
        ref_planet: tuple[float, float, float] | None = None
        if spec.get("orbital_campaign"):
            cands: list[tuple[float, str, float, float, float]] = []
            for r in nh_list:
                if r.get("pl_orbper") and r.get("pl_tranmid"):
                    p_d = float(r["pl_orbper"])
                    t0_b = float(r["pl_tranmid"])
                    ecc_v = float(r.get("pl_orbeccen") or 0.0)
                    ppo_planets.append((p_d, t0_b))
                    kp_v = compute_keplerian_kp_kms(mass_msun, p_d, ecc_v)
                    cands.append((kp_v, r["pl_name"], p_d, t0_b, ecc_v))
            cands.sort(reverse=True)
            assert len(cands) >= 1, f"{st}: missing orbital ephemeris in NASA pscomppars!"
            kp, pl_name, p_days, t0_bjd, ecc = cands[0]
            ref_planet = (p_days, t0_bjd, kp)

        picked = select_exposures(spec, pool, mjd_ell=mjd_ell, ppo_planets=ppo_planets, ref_planet=ref_planet)
        assert len(picked) == int(spec["n_target_exposures"]), f"{st}: picked {len(picked)} != {spec['n_target_exposures']}"

        if "ELLIPSOID" in spec["science_track"]:
            assert all(abs(p["mjd_obs"] - mjd_ell) <= 180.0 for p in picked), f"{st}: Ellipsoid dt > 180 d!"

        camp_exps: dict[str, dict[str, Any]] = {}
        if spec.get("orbital_campaign") and ref_planet is not None:
            camp_num += 1
            p_days, t0_bjd, kp = ref_planet
            with_phi = []
            for pr in picked:
                bjd_est = pr["mjd_obs"] + 2400000.5
                phi, dv_orb = compute_planet_orbital_rv_kms(bjd_est, t0_bjd, p_days, kp)
                with_phi.append((pr, bjd_est, phi, dv_orb))
            n_half = max(1, len(picked) // 2)
            ordered_phi = sorted(with_phi, key=lambda x: abs(x[2]))
            in_ids = {x[0]["dp_id"] for x in ordered_phi[:n_half]}
            dvs = [x[3] for x in with_phi]
            dv_span = max(dvs) - min(dvs)
            assert dv_span >= 5.0, f"{st}: orbital dv_span={dv_span:.2f} < 5.0 km/s!"

            camps_exp_list = []
            for pr, bjd_est, phi, dv_orb in with_phi:
                win_lbl = "IN_WINDOW" if pr["dp_id"] in in_ids else "OUT_OF_WINDOW"
                camp_exps[pr["dp_id"]] = {"phase_window": win_lbl, "signed_phase": round(phi, 5), "planet_orbital_rv_kms": round(dv_orb, 4)}
                camps_exp_list.append({
                    "dp_id": pr["dp_id"],
                    "mjd_obs": round(pr["mjd_obs"], 5),
                    "bjd_tdb_est": round(bjd_est, 5),
                    "signed_phase": round(phi, 5),
                    "phase_window": win_lbl,
                    "planet_orbital_rv_kms": round(dv_orb, 4),
                    "ppo_align_score": round(compute_ppo_alignment_score(bjd_est, ppo_planets), 5),
                })

            campaigns_doc[st] = {
                "campaign_index": camp_num,
                "canonical_target": st,
                "common_name": spec["common_name"],
                "instrument": spec["instrument"],
                "role": spec["role"],
                "null_orbital": False,
                "planet_name": pl_name,
                "n_planets_in_system": n_pl,
                "n_transiting_with_t0": len(ppo_planets),
                "stellar_mass_msun": round(mass_msun, 4),
                "orb_per_days": round(p_days, 7),
                "orb_t0_bjd": round(t0_bjd, 6),
                "orb_ecc": round(ecc, 4),
                "kp_kms": round(kp, 3),
                "orbital_dv_span_kms": round(dv_span, 3),
                "min_ppo_align_score": round(min(e["ppo_align_score"] for e in camps_exp_list), 5),
                "exposures": camps_exp_list,
            }

        all_star_coords.append({"canonical_target": st, "ra_deg": ra_deg, "dec_deg": dec_deg, "bridge": spec["panchromatic_bridge"]})
        if not spec["panchromatic_bridge"]:
            nearest = min(
                (sep_arcsec(ra_deg, dec_deg, c["ra_deg"], c["dec_deg"]), c["label"])
                for c in excluded_coords
            )
            assert nearest[0] >= 90.0, f"Brand-new star {st} overlaps prior target {nearest}!"
            brand_new_coords.append({"canonical_target": st, "ra_deg": ra_deg, "dec_deg": dec_deg})
            sep_verif.append({
                "canonical_target": st,
                "instrument": spec["instrument"],
                "science_track": spec["science_track"],
                "ra_deg": round(ra_deg, 6),
                "dec_deg": round(dec_deg, 6),
                "dist_pc": round(dist_pc, 4),
                "within_10pc": within_10pc,
                "nearest_prior_target": nearest[1],
                "min_sky_separation_arcsec": round(nearest[0], 2),
            })

        for rank, pr in enumerate(picked, 1):
            ce = camp_exps.get(pr["dp_id"], {"phase_window": "NONE", "signed_phase": 0.0, "planet_orbital_rv_kms": 0.0})
            total_bytes += pr["total_bytes"]
            bjd_est = pr["mjd_obs"] + 2400000.5
            ppo_score = compute_ppo_alignment_score(bjd_est, ppo_planets) if len(ppo_planets) >= 2 else 1.0
            dt_ell = pr["mjd_obs"] - mjd_ell
            cohort_rows.append({
                "instrument": spec["instrument"],
                "canonical_target": st,
                "common_name": spec["common_name"],
                "role": spec["role"],
                "subrole": spec["subrole"],
                "science_track": spec["science_track"],
                "panchromatic_bridge": spec["panchromatic_bridge"],
                "radio_mm_id": spec["radio_mm_id"],
                "gaia_source_id": spec["gaia_source_id"],
                "s_ra": round(ra_deg, 6),
                "s_dec": round(dec_deg, 6),
                "pmra_mas_yr": round(pmra, 3),
                "pmdec_mas_yr": round(pmdec, 3),
                "dist_pc": round(dist_pc, 5),
                "within_10pc": within_10pc,
                "phot_g_mag": round(phot_g, 4),
                "phot_bp_mag": round(phot_bp, 4) if phot_bp is not None else "",
                "phot_rp_mag": round(phot_rp, 4) if phot_rp is not None else "",
                "j_mag": spec["j_mag"],
                "h_mag": spec["h_mag"],
                "ks_mag": spec["ks_mag"],
                "teff_k": round(teff_k, 1),
                "mh_dex": round(mh_dex, 3),
                "stellar_mass_msun": round(mass_msun, 4),
                "prior_rv_kms": round(prior_rv, 4),
                "n_exoplanets": n_pl,
                "has_transiting_planet": has_tr,
                "ecliptic_lat_deg": round(beta_ecl, 5),
                "sn1987a_mjd_ell": round(mjd_ell, 3),
                "sn1987a_dt_days": round(dt_ell, 3),
                "ppo_align_score": round(ppo_score, 5),
                "epoch_rank": rank,
                "dp_id": pr["dp_id"],
                "grating": pr["grating"],
                "resolving_power": round(pr["resolving_power"], 1),
                "mjd_obs": round(pr["mjd_obs"], 5),
                "t_exptime": round(pr["t_exptime"], 2),
                "phase_window": ce["phase_window"],
                "signed_phase": ce["signed_phase"],
                "planet_orbital_rv_kms": ce["planet_orbital_rv_kms"],
                "f1_id": pr["f1_id"],
                "f1_rel": f"{spec['instrument']}/{st}/{pr['f1_id']}.fits",
                "f1_url": pr["f1_url"],
                "f1_bytes": pr["f1_bytes"],
                "f2_id": "",
                "f2_rel": "",
                "f2_url": "",
                "f2_bytes": 0,
                "f3_id": "",
                "f3_rel": "",
                "f3_url": "",
                "f3_bytes": 0,
                "total_bytes": pr["total_bytes"],
            })

    intra_min = min(
        sep_arcsec(a["ra_deg"], a["dec_deg"], b["ra_deg"], b["dec_deg"])
        for i, a in enumerate(all_star_coords)
        for b in all_star_coords[i + 1 :]
    )
    min_prior_sep = min(s["min_sky_separation_arcsec"] for s in sep_verif)
    d092_dps = {r["dp_id"] for r in cohort_rows}
    overlap_cnt = len(d092_dps & excluded_dp_ids)
    proj_mib = total_bytes / (1024.0 * 1024.0)
    n_new = len(brand_new_coords)
    n_bridges = len({r["canonical_target"] for r in cohort_rows if r["panchromatic_bridge"]})
    n_controls = len({r["canonical_target"] for r in cohort_rows if r["role"] == "CONTROL"})
    n_new_10pc = sum(1 for s in sep_verif if s["within_10pc"])

    assert overlap_cnt == 0, f"dp_id overlap {overlap_cnt}!"
    assert len(all_star_coords) == 28 and n_new == 25 and n_bridges == 3 and n_controls == 6
    assert len(cohort_rows) == 57, len(cohort_rows)
    assert len(campaigns_doc) == 9, len(campaigns_doc)
    assert proj_mib <= 220.0, f"Projected {proj_mib:.2f} MiB > 220 MiB!"
    assert min_prior_sep >= 90.0 and intra_min >= 90.0, (min_prior_sep, intra_min)
    assert not inp_dir.exists(), "inputs_d092_v5_0 must not exist!"

    with (WS / "FROZEN_COHORT_D092.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cohort_rows[0].keys()))
        w.writeheader()
        w.writerows(cohort_rows)

    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(
        json.dumps({"schema": "D092_ORBITAL_CAMPAIGNS_V1", "phase_id": "D092", "n_campaigns": len(campaigns_doc), "campaigns": campaigns_doc}, indent=2) + "\n",
        encoding="utf-8",
    )

    pe92 = {
        "schema": "D092_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D092",
        "verified_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prior_phases_covered": "C001-C037 + D001-D091",
        "n_prior_excluded_coords": len(excluded_coords),
        "n_prior_excluded_dp_ids": len(excluded_dp_ids),
        "d092_total_stars": n_new + n_bridges,
        "d092_brand_new_unique_stars": n_new,
        "d092_panchromatic_bridge_stars": n_bridges,
        "d092_control_stars": n_controls,
        "d092_brand_new_within_10pc": n_new_10pc,
        "d092_total_exposures": len(cohort_rows),
        "d092_total_fits_files": len(cohort_rows),
        "d092_projected_download_bytes": total_bytes,
        "d092_projected_download_gib": round(total_bytes / (1024.0 ** 3), 4),
        "d092_projected_download_mib": round(proj_mib, 2),
        "d092_dp_id_overlap_count": overlap_cnt,
        "min_brand_new_sky_separation_arcsec": round(min_prior_sep, 2),
        "min_intra_d092_separation_arcsec": round(intra_min, 2),
        "star_separation_verification": sep_verif,
        "excluded_dp_ids": sorted(excluded_dp_ids),
        "excluded_targets_coordinate_registry": excluded_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pe92, indent=2) + "\n", encoding="utf-8")

    # Seal Prospective METHOD_LOCK.json and LOCK_RECEIPT.json BEFORE any FITS download!
    lock_files = [
        "v5_0_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D092.csv",
        "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "PRIOR_V4_2_PHASES_SNAPSHOT.json",
    ]
    locked_hashes = {fn: sha256_file(WS / fn) for fn in lock_files}
    locked_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    method_lock = {
        "schema": "D092_METHOD_LOCK_V1",
        "phase_id": "D092",
        "detector": DETECTOR_NAME,
        "locked_utc": locked_utc,
        "instruments": ["ESO_HARPS", "ESO_FEROS", "ESO_CRIRES"],
        "retroactive_reused_bundles": {
            "d091_bundle": {"archive": ARCHIVE_Q.name, "archive_sha256": ARCHIVE_Q_SHA256, "n_exposures": 156},
            "d090_bundle": {"archive": ARCHIVE_P.name, "archive_sha256": ARCHIVE_P_SHA256, "n_miri_exposures": 65},
        },
        "locked_v50_parameters": {
            "rpca_block_len": BASE_V5_0_CONFIG["rpca_block_len"],
            "rpca_overlap": BASE_V5_0_CONFIG["rpca_overlap"],
            "rpca_loso_rank": BASE_V5_0_CONFIG["rpca_loso_rank"],
            "g7_min_z_rpca": BASE_V5_0_CONFIG["g7_min_z_rpca"],
            "g7_min_rarity_score": BASE_V5_0_CONFIG["g7_min_rarity_score"],
            "agnostic_scales_lsf": list(BASE_V5_0_CONFIG["agnostic_scales_lsf"]),
            "agnostic_min_abs_z": BASE_V5_0_CONFIG["agnostic_min_abs_z"],
            "agnostic_min_rarity_score": BASE_V5_0_CONFIG["agnostic_min_rarity_score"],
            "miri_ccf_min_sigma": BASE_V5_0_CONFIG["miri_ccf_min_sigma"],
            "miri_ccf_min_confounder_ratio": BASE_V5_0_CONFIG["miri_ccf_min_confounder_ratio"],
            "etz_max_abs_beta_deg": 0.264,
            "sn1987a_ellipsoid_max_abs_dt_days": 180.0,
        },
        "hard_caps": {
            "max_raw_download_mib": 225.0,
            "min_post_free_gib": 6.5,
            "max_bounded_bundle_mib": 25.0,
            "min_chronology_lag_s": 3.0,
        },
        "locked_file_hashes": locked_hashes,
    }
    ml_path = WS / "METHOD_LOCK.json"
    ml_path.write_text(json.dumps(method_lock, indent=2) + "\n", encoding="utf-8")

    lock_receipt = {
        "schema": "D092_LOCK_RECEIPT_V1",
        "phase_id": "D092",
        "locked_utc": locked_utc,
        "method_lock_sha256": sha256_file(ml_path),
        "inputs_d092_v5_0_exists": inp_dir.exists(),
        "locked_artifact_sha256": locked_hashes,
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lock_receipt, indent=2) + "\n", encoding="utf-8")

    print(
        f"DONE build_cohort: {len(cohort_rows)} exposures ({len(cohort_rows)} FITS), "
        f"{n_new + n_bridges} stars ({n_new} new [{n_new_10pc} <10pc] + {n_bridges} bridges, {n_controls} CTRL), "
        f"{len(campaigns_doc)} orbital campaigns, proj={proj_mib:.2f} MiB, dp_overlap={overlap_cnt}, "
        f"min_prior_sep={min_prior_sep:.1f}\", min_intra_sep={intra_min:.1f}\", locked_utc={locked_utc}",
        flush=True,
    )


if __name__ == "__main__":
    main()
