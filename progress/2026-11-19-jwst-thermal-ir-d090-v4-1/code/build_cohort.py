#!/usr/bin/env python3
"""
Phase D090 Cohort Builder: `JWST_SPACE_THERMAL_IR_V4_1`

Strictly queries public STScI MAST JWST CAOM metadata, Gaia DR3 TAP, NASA Exoplanet
Archive (`pscomppars`), and verified Companion Archive O (Phase D089) BEFORE
`inputs_d090_v4_1/` exists or any science FITS file is downloaded.

Outputs:
  - FROZEN_COHORT_D090.csv
  - ORBITAL_CAMPAIGNS_AND_KINEMATICS.json
  - PRIOR_EXCLUSION_VERIFICATION.json
  - PRIOR_V4_PHASES_SNAPSHOT.json
  - MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import json
import math
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from v4_1_detector import C_KMS, compute_keplerian_kp_kms, compute_planet_orbital_rv_kms

ROOT = Path(".")
WS = Path(__file__).resolve().parent
ARCHIVE_O = ROOT / "archives" / "SETI_D089_V4_0_SPACE_LYMAN_FUV_NUV_RESULTS_2026-11-19.zip"
ARCHIVE_O_SHA256 = "4864dd3b5c0e958e428e1af815e1a378a37824d6bc87a89de9c223d89bccd723"
ARCHIVE_O_PREFIX = "work_space_lyman_nuv_20261119_d089_v4_0_fuse_cos_stis_nuv/"

FORMAT_CHECK_EXCLUDED = [
    ("10LAC(D090_FMT)", 339.81533, 39.05027),
    ("1808347(D090_FMT)", 272.145, 69.458),
    ("HD-18511-PSF-CALIBRATOR(D090_FMT)", 44.552, -12.006),
]

TARGET_SPECS: list[dict[str, Any]] = [
    # ==================== JWST_MIRI_MRS (15 stars: 3 CTRL + 4 BRIDGE + 8 NEW SCI) ====================
    {
        "instrument": "JWST_MIRI_MRS", "mast_inst": "MIRI/IFU", "mast_filters": ["CH1-SHORT", "CH1-MEDIUM", "CH1-LONG"],
        "mast_names": ["HD163466", "HD163466-WBKG"], "canonical_target": "HD163466", "common_name": "HD 163466",
        "role": "CONTROL", "subrole": "NULL_ORBITAL_CONTROL_MIRI", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 1435190745326633984, "n_target_pairs": 8, "orbital_campaign": True, "null_orbital": True,
        "planet_name": "Null Control (synthetic P=1.31d)", "orb_per_days": 1.3100, "orb_e": 0.0,
        "teff_lit": 8200.0, "mh_lit": 0.0, "mass_lit": 1.70, "rv_lit": -14.0,
        "j_mag": 6.48, "h_mag": 6.40, "ks_mag": 6.37,
    },
    {
        "instrument": "JWST_MIRI_MRS", "mast_inst": "MIRI/IFU", "mast_filters": ["CH1-SHORT", "CH1-MEDIUM", "CH1-LONG"],
        "mast_names": ["HD2811-WBKG"], "canonical_target": "HD2811", "common_name": "HD 2811",
        "role": "CONTROL", "subrole": "NULL_ORBITAL_CONTROL_MIRI", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 4992412432308644224, "n_target_pairs": 8, "orbital_campaign": True, "null_orbital": True,
        "planet_name": "Null Control (synthetic P=1.93d)", "orb_per_days": 1.9300, "orb_e": 0.0,
        "teff_lit": 8150.0, "mh_lit": -0.25, "mass_lit": 1.65, "rv_lit": 6.51,
        "j_mag": 7.12, "h_mag": 7.05, "ks_mag": 7.02,
    },
    {
        "instrument": "JWST_MIRI_MRS", "mast_inst": "MIRI/IFU", "mast_filters": ["CH1-SHORT"],
        "mast_names": ["HD-159222"], "canonical_target": "HD159222", "common_name": "HD 159222",
        "role": "CONTROL", "subrole": "NULL_SOLAR_ANALOG_MIRI", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 1335880415564253312, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 5870.0, "mh_lit": 0.14, "mass_lit": 1.05, "rv_lit": -51.59,
        "j_mag": 5.39, "h_mag": 5.10, "ks_mag": 5.00,
    },
    {
        "instrument": "JWST_MIRI_MRS", "mast_inst": "MIRI/IFU", "mast_filters": ["CH1-SHORT"],
        "mast_names": ["16CYG-B-WBKG"], "canonical_target": "16CYGB", "common_name": "16 Cyg B (HD 186427)",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_RADIO_MIRI_BRIDGE", "panchromatic_bridge": True, "radio_mm_id": "M24_16CYGB",
        "gaia_source_id": 2135550755683405952, "n_target_pairs": 8, "orbital_campaign": True, "null_orbital": False,
        "nasa_pl_name": "16 Cyg B b", "orb_t0_bjd": 2456937.32, "orb_per_days": 798.5, "orb_e": 0.68,
        "teff_lit": 5750.0, "mh_lit": 0.06, "mass_lit": 1.08, "rv_lit": -27.31,
        "j_mag": 4.993, "h_mag": 4.72, "ks_mag": 4.651,
    },
    {
        "instrument": "JWST_MIRI_MRS", "mast_inst": "MIRI/IFU", "mast_filters": ["CH1-SHORT"],
        "mast_names": ["-BET-PIC", "BETA-PIC", "bet-Pic"], "canonical_target": "BETPIC", "common_name": "beta Pictoris (HD 39060)",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_8OCT_LYMAN_MIRI_BRIDGE", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 4792774797545800832, "n_target_pairs": 8, "orbital_campaign": True, "null_orbital": False,
        "nasa_pl_name": "bet Pic c", "orb_t0_bjd": 2458550.0, "orb_per_days": 1202.0, "orb_e": 0.307,
        "teff_lit": 8038.7, "mh_lit": 0.0, "mass_lit": 1.789, "rv_lit": 16.84,
        "j_mag": 3.669, "h_mag": 3.55, "ks_mag": 3.526,
    },
    {
        "instrument": "JWST_MIRI_MRS", "mast_inst": "MIRI/IFU", "mast_filters": ["CH1-SHORT"],
        "mast_names": ["HD-172555"], "canonical_target": "HD172555", "common_name": "HD 172555",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_STIS_MIRI_DEBRIS_BRIDGE", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 6438274350302427776, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 7800.0, "mh_lit": 0.0, "mass_lit": 1.70, "rv_lit": 2.80,
        "j_mag": 4.38, "h_mag": 4.30, "ks_mag": 4.30,
    },
    {
        "instrument": "JWST_MIRI_MRS", "mast_inst": "MIRI/IFU", "mast_filters": ["CH1-SHORT"],
        "mast_names": ["CD-40-8434"], "canonical_target": "PDS70", "common_name": "PDS 70 (CD-40 8434)",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_KBAND_MIRI_PROTOPLANET_BRIDGE", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 6110141563309613056, "n_target_pairs": 3, "orbital_campaign": False,
        "nasa_pl_name": "PDS 70 b", "n_exoplanets_lit": 2,
        "teff_lit": 4138.0, "mh_lit": -0.11, "mass_lit": 0.982, "rv_lit": 3.13,
        "j_mag": 9.553, "h_mag": 8.82, "ks_mag": 8.542,
    },
    {
        "instrument": "JWST_MIRI_MRS", "mast_inst": "MIRI/IFU", "mast_filters": ["CH1-SHORT"],
        "mast_names": ["Object_D"], "canonical_target": "OBJECT_D", "common_name": "Hephaistos Object D (prop 7199)",
        "role": "SCIENCE", "subrole": "PROJECT_HEPHAISTOS_DYSON_MIDIR_MDWARF", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 2660349163149053824, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 3473.5, "mh_lit": -0.57, "mass_lit": 0.35, "rv_lit": 0.0,
        "j_mag": 13.8, "h_mag": 13.2, "ks_mag": 12.9,
    },
    {
        "instrument": "JWST_MIRI_MRS", "mast_inst": "MIRI/IFU", "mast_filters": ["CH1-SHORT"],
        "mast_names": ["Object_E"], "canonical_target": "OBJECT_E", "common_name": "Hephaistos Object E (prop 7199)",
        "role": "SCIENCE", "subrole": "PROJECT_HEPHAISTOS_DYSON_MIDIR_MDWARF", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3190232820489766656, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 3556.7, "mh_lit": -0.97, "mass_lit": 0.40, "rv_lit": 0.0,
        "j_mag": 13.5, "h_mag": 12.9, "ks_mag": 12.6,
    },
    {
        "instrument": "JWST_MIRI_MRS", "mast_inst": "MIRI/IFU", "mast_filters": ["CH1-SHORT"],
        "mast_names": ["WISE0855-0714"], "canonical_target": "WISE0855", "common_name": "WISE J085510.83-071442.5",
        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_MIRI_Y_DWARF_10PC", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": None, "n_target_pairs": 3, "orbital_campaign": False,
        "ra_lit": 133.7660, "dec_lit": -7.2427, "dist_lit": 2.278, "teff_lit": 260.0, "mh_lit": 0.0, "mass_lit": 0.005, "rv_lit": 0.0,
        "j_mag": 25.0, "h_mag": 22.7, "ks_mag": 20.5,
    },
    {
        "instrument": "JWST_MIRI_MRS", "mast_inst": "MIRI/IFU", "mast_filters": ["CH1-SHORT"],
        "mast_names": ["vMa-2"], "canonical_target": "VMA2", "common_name": "van Maanen 2 (WD 0046+051)",
        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_MIRI_WHITE_DWARF_10PC", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 2552928187080872832, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 6220.0, "mh_lit": -0.50, "mass_lit": 0.68, "rv_lit": 26.0,
        "j_mag": 11.69, "h_mag": 11.55, "ks_mag": 11.50,
    },
    {
        "instrument": "JWST_MIRI_MRS", "mast_inst": "MIRI/IFU", "mast_filters": ["CH1-SHORT"],
        "mast_names": ["LAWD-37"], "canonical_target": "LAWD37", "common_name": "LAWD 37 (WD 1142-645)",
        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_MIRI_WHITE_DWARF_10PC", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 5332606522595645952, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 7850.0, "mh_lit": -0.50, "mass_lit": 0.56, "rv_lit": 30.0,
        "j_mag": 11.15, "h_mag": 11.09, "ks_mag": 11.05,
    },
    {
        "instrument": "JWST_MIRI_MRS", "mast_inst": "MIRI/IFU", "mast_filters": ["CH1-SHORT"],
        "mast_names": ["EXZ-ETA-CRV"], "canonical_target": "ETACRV", "common_name": "eta Crv (HD 109085)",
        "role": "SCIENCE", "subrole": "THERMAL_IR_DEBRIS_DISK_HOST", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3526420114274019456, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 6746.5, "mh_lit": -0.10, "mass_lit": 1.39, "rv_lit": -1.16,
        "j_mag": 3.55, "h_mag": 3.40, "ks_mag": 3.37,
    },
    {
        "instrument": "JWST_MIRI_MRS", "mast_inst": "MIRI/IFU", "mast_filters": ["CH1-SHORT"],
        "mast_names": ["-49-CET"], "canonical_target": "49CET", "common_name": "49 Cet (HD 9672)",
        "role": "SCIENCE", "subrole": "THERMAL_IR_CO_GAS_DEBRIS_DISK", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 2451838022871837312, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 8950.1, "mh_lit": 0.0, "mass_lit": 2.0, "rv_lit": 8.76,
        "j_mag": 5.53, "h_mag": 5.53, "ks_mag": 5.46,
    },
    {
        "instrument": "JWST_MIRI_MRS", "mast_inst": "MIRI/IFU", "mast_filters": ["CH1-SHORT"],
        "mast_names": ["V-ZZ-PSC", "V-ZZ-Psc"], "canonical_target": "ZZPSC", "common_name": "ZZ Psc (G29-38)",
        "role": "SCIENCE", "subrole": "POLLUTED_DEBRIS_DISK_WHITE_DWARF", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 2660358032257156736, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 11820.0, "mh_lit": -0.50, "mass_lit": 0.65, "rv_lit": 12.0,
        "j_mag": 13.13, "h_mag": 13.07, "ks_mag": 12.69,
    },

    # ==================== JWST_NIRSPEC_G395H (11 stars: 3 CTRL + 2 BRIDGE + 6 NEW SCI) ====================
    {
        "instrument": "JWST_NIRSPEC_G395H", "mast_inst": "NIRSPEC/SLIT", "mast_filters": ["F290LP;G395H"],
        "mast_names": ["P330E"], "canonical_target": "P330E", "common_name": "GSPC P330-E",
        "role": "CONTROL", "subrole": "NULL_ORBITAL_CONTROL_G395H", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 1312053517554465024, "n_target_pairs": 8, "orbital_campaign": True, "null_orbital": True,
        "planet_name": "Null Control (synthetic P=1.67d)", "orb_per_days": 1.6700, "orb_e": 0.0,
        "prefer_small_pair_bytes": True,
        "teff_lit": 5810.0, "mh_lit": -0.28, "mass_lit": 1.0, "rv_lit": -61.37,
        "j_mag": 11.78, "h_mag": 11.45, "ks_mag": 11.42,
    },
    {
        "instrument": "JWST_NIRSPEC_G395H", "mast_inst": "NIRSPEC/SLIT", "mast_filters": ["F290LP;G395H"],
        "mast_names": ["BD+60-1753"], "canonical_target": "BD601753", "common_name": "BD+60 1753",
        "role": "CONTROL", "subrole": "NULL_FLUX_STANDARD_G395H", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 1435896975388228224, "n_target_pairs": 3, "orbital_campaign": False,
        "prefer_small_pair_bytes": True,
        "teff_lit": 9129.7, "mh_lit": -0.04, "mass_lit": 2.1, "rv_lit": -25.46,
        "j_mag": 9.65, "h_mag": 9.66, "ks_mag": 9.65,
    },
    {
        "instrument": "JWST_NIRSPEC_G395H", "mast_inst": "NIRSPEC/SLIT", "mast_filters": ["F290LP;G395H"],
        "mast_names": ["J1743045"], "canonical_target": "J1743045", "common_name": "2MASS J17430448+6655015",
        "role": "CONTROL", "subrole": "NULL_FLUX_STANDARD_G395H", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 1634280312200704768, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 7862.9, "mh_lit": -0.67, "mass_lit": 1.6, "rv_lit": -30.0,
        "j_mag": 13.10, "h_mag": 13.00, "ks_mag": 12.98,
    },
    {
        "instrument": "JWST_NIRSPEC_G395H", "mast_inst": "NIRSPEC/IFU", "mast_filters": ["F290LP;G395H"],
        "mast_names": ["eps_Eri"], "canonical_target": "EPSERI", "common_name": "eps Eri (HD 22049)",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_5ARM_LYMAN_G395H_BRIDGE", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 5164707970261890560, "n_target_pairs": 8, "orbital_campaign": True, "null_orbital": False,
        "nasa_pl_name": "eps Eri b", "orb_t0_bjd": 2457388.0, "orb_per_days": 2680.0, "orb_e": 0.06,
        "teff_lit": 5020.4, "mh_lit": -0.13, "mass_lit": 0.82, "rv_lit": 16.0,
        "j_mag": 2.228, "h_mag": 1.88, "ks_mag": 1.776,
    },
    {
        "instrument": "JWST_NIRSPEC_G395H", "mast_inst": "NIRSPEC/IFU", "mast_filters": ["F290LP;G395H"],
        "mast_names": ["-eps-Ind-Ab"], "canonical_target": "HD209100", "common_name": "eps Ind A (HD 209100)",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_OPTICAL_G395H_10PC_BRIDGE", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 6412595290592307840, "n_target_pairs": 8, "orbital_campaign": True, "null_orbital": False,
        "nasa_pl_name": "eps Ind A b", "orb_t0_bjd": 2460000.0, "orb_per_days": 25450.0, "orb_e": 0.25,
        "teff_lit": 4700.0, "mh_lit": -0.17, "mass_lit": 0.80, "rv_lit": -40.43,
        "j_mag": 2.894, "h_mag": 2.35, "ks_mag": 2.237,
    },
    {
        "instrument": "JWST_NIRSPEC_G395H", "mast_inst": "NIRSPEC/IFU", "mast_filters": ["F290LP;G395H"],
        "mast_names": ["HD-218396"], "canonical_target": "HR8799", "common_name": "HR 8799 (HD 218396)",
        "role": "SCIENCE", "subrole": "DIRECT_IMAGING_4PLANET_ORBITAL_HOST", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 2832463659640297472, "n_target_pairs": 8, "orbital_campaign": True, "null_orbital": False,
        "nasa_pl_name": "HR 8799 e", "orb_t0_bjd": 2460154.0, "orb_per_days": 20815.6, "orb_e": 0.15, "n_exoplanets_lit": 4,
        "teff_lit": 7400.0, "mh_lit": -0.50, "mass_lit": 1.51, "rv_lit": -10.41,
        "j_mag": 5.383, "h_mag": 5.28, "ks_mag": 5.24,
    },
    {
        "instrument": "JWST_NIRSPEC_G395H", "mast_inst": "NIRSPEC/IFU", "mast_filters": ["F290LP;G395H"],
        "mast_names": ["AF-Lep-b"], "canonical_target": "AFLEP", "common_name": "AF Lep (HD 35850)",
        "role": "SCIENCE", "subrole": "DIRECT_IMAGING_EXOPLANET_ORBITAL", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3009908378049913216, "n_target_pairs": 8, "orbital_campaign": True, "null_orbital": False,
        "nasa_pl_name": "AF Lep b", "orb_t0_bjd": 2456700.0, "orb_per_days": 8905.0, "orb_e": 0.015,
        "teff_lit": 6140.0, "mh_lit": 0.19, "mass_lit": 1.218, "rv_lit": 21.10,
        "j_mag": 5.268, "h_mag": 5.09, "ks_mag": 4.926,
    },
    {
        "instrument": "JWST_NIRSPEC_G395H", "mast_inst": "NIRSPEC/SLIT", "mast_filters": ["F290LP;G395H"],
        "mast_names": ["51-ERI-B"], "canonical_target": "51ERI", "common_name": "51 Eri (HD 29391)",
        "role": "SCIENCE", "subrole": "DIRECT_IMAGING_EXOPLANET_ORBITAL", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3205095125321700480, "n_target_pairs": 8, "orbital_campaign": True, "null_orbital": False,
        "nasa_pl_name": "51 Eri b", "orb_t0_bjd": 2460337.0, "orb_per_days": 9100.0, "orb_e": 0.57,
        "teff_lit": 7422.0, "mh_lit": 0.13, "mass_lit": 1.75, "rv_lit": 17.30,
        "j_mag": 4.744, "h_mag": 4.77, "ks_mag": 4.537,
    },
    {
        "instrument": "JWST_NIRSPEC_G395H", "mast_inst": "NIRSPEC/IFU", "mast_filters": ["F290LP;G395H"],
        "mast_names": ["HD-19467"], "canonical_target": "HD19467", "common_name": "HD 19467",
        "role": "SCIENCE", "subrole": "BENCHMARK_SUBSTELLAR_HOST_G395H", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 5155981730587168384, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 5615.3, "mh_lit": -0.14, "mass_lit": 0.95, "rv_lit": 7.01,
        "j_mag": 5.80, "h_mag": 5.45, "ks_mag": 5.40,
    },
    {
        "instrument": "JWST_NIRSPEC_G395H", "mast_inst": "NIRSPEC/IFU", "mast_filters": ["F290LP;G395H"],
        "mast_names": ["GJ-504-B"], "canonical_target": "GJ504", "common_name": "59 Vir (GJ 504)",
        "role": "SCIENCE", "subrole": "DIRECT_IMAGING_EXOPLANET_HOST_G395H", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3732539683617410816, "n_target_pairs": 3, "orbital_campaign": False,
        "nasa_pl_name": "GJ 504 b", "n_exoplanets_lit": 1,
        "teff_lit": 6234.0, "mh_lit": 0.28, "mass_lit": 1.22, "rv_lit": -27.25,
        "j_mag": 4.392, "h_mag": 4.11, "ks_mag": 4.033,
    },
    {
        "instrument": "JWST_NIRSPEC_G395H", "mast_inst": "NIRSPEC/SLIT", "mast_filters": ["F290LP;G395H"],
        "mast_names": ["2148+4003"], "canonical_target": "J2148", "common_name": "2MASS J21481628+4003593",
        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_G395H_LDWARF_10PC", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 1954170404122975232, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 1700.0, "mh_lit": 0.0, "mass_lit": 0.06, "rv_lit": -15.0,
        "j_mag": 14.15, "h_mag": 12.78, "ks_mag": 11.77,
    },

    # ==================== JWST_NIRSPEC_G235H (11 stars: 3 CTRL + 1 BRIDGE + 7 NEW SCI) ====================
    {
        "instrument": "JWST_NIRSPEC_G235H", "mast_inst": "NIRSPEC/IFU", "mast_filters": ["F170LP;G235H"],
        "mast_names": ["BD+04-3653"], "canonical_target": "BD043653", "common_name": "BD+04 3653 (HD 167241)",
        "role": "CONTROL", "subrole": "NULL_STANDARD_CONTROL_G235H", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 4470791471716487680, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 7760.3, "mh_lit": -0.74, "mass_lit": 1.60, "rv_lit": -27.24,
        "j_mag": 10.02, "h_mag": 9.95, "ks_mag": 9.93,
    },
    {
        "instrument": "JWST_NIRSPEC_G235H", "mast_inst": "NIRSPEC/IFU", "mast_filters": ["F170LP;G235H"],
        "mast_names": ["TYC-3986-834-1"], "canonical_target": "TYC3986", "common_name": "TYC 3986-834-1",
        "role": "CONTROL", "subrole": "NULL_SOLAR_ANALOG_CONTROL_G235H", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 2004901939360968832, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 5581.3, "mh_lit": -0.01, "mass_lit": 0.95, "rv_lit": -4.13,
        "j_mag": 10.75, "h_mag": 10.45, "ks_mag": 10.37,
    },
    {
        "instrument": "JWST_NIRSPEC_G235H", "mast_inst": "NIRSPEC/SLIT", "mast_filters": ["F170LP;G235H"],
        "mast_names": ["1802271"], "canonical_target": "J1802271", "common_name": "2MASS J18022716+6043356 (CAL 1802271)",
        "role": "CONTROL", "subrole": "NULL_FLUX_STANDARD_CONTROL_G235H", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 2158745262705810304, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 9240.4, "mh_lit": -0.72, "mass_lit": 2.0, "rv_lit": 1.98,
        "j_mag": 11.77, "h_mag": 11.70, "ks_mag": 11.68,
    },
    {
        "instrument": "JWST_NIRSPEC_G235H", "mast_inst": "NIRSPEC/IFU", "mast_filters": ["F170LP;G235H"],
        "mast_names": ["HD-42581B-NIRSPEC"], "canonical_target": "HD42581", "common_name": "GJ 229 (HD 42581)",
        "role": "SCIENCE", "subrole": "PANCHROMATIC_HARPS_CRIRES_G235H_10PC_BRIDGE", "panchromatic_bridge": True, "radio_mm_id": "",
        "gaia_source_id": 2940856402123426176, "n_target_pairs": 3, "orbital_campaign": False,
        "nasa_pl_name": "GJ 229 b", "n_exoplanets_lit": 2,
        "teff_lit": 3564.0, "mh_lit": 0.0, "mass_lit": 0.509, "rv_lit": 4.02,
        "j_mag": 5.104, "h_mag": 4.39, "ks_mag": 4.166,
    },
    {
        "instrument": "JWST_NIRSPEC_G235H", "mast_inst": "NIRSPEC/IFU", "mast_filters": ["F170LP;G235H"],
        "mast_names": ["VHS-1256B"], "canonical_target": "VHS1256B", "common_name": "VHS J1256-1257 b",
        "role": "SCIENCE", "subrole": "DIRECT_IMAGING_PLANETARY_COMPANION_G235H", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": None, "n_target_pairs": 3, "orbital_campaign": False,
        "nasa_pl_name": "VHS J125601.92-125723.9 b", "n_exoplanets_lit": 1,
        "ra_lit": 194.0058, "dec_lit": -12.9590, "dist_lit": 12.70, "teff_lit": 2620.0, "mh_lit": 0.0, "mass_lit": 0.07, "rv_lit": -1.4,
        "j_mag": 11.018, "h_mag": 10.473, "ks_mag": 10.044,
    },
    {
        "instrument": "JWST_NIRSPEC_G235H", "mast_inst": "NIRSPEC/IFU", "mast_filters": ["F170LP;G235H"],
        "mast_names": ["TWA-27-AB"], "canonical_target": "TWA27", "common_name": "TWA 27 (2M1207)",
        "role": "SCIENCE", "subrole": "DIRECT_IMAGING_EXOPLANET_HOST_G235H", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3459372646830687104, "n_target_pairs": 3, "orbital_campaign": False,
        "nasa_pl_name": "2MASS J12073346-3932539 b", "n_exoplanets_lit": 1,
        "teff_lit": 2825.0, "mh_lit": 0.0, "mass_lit": 0.188, "rv_lit": 11.0,
        "j_mag": 12.995, "h_mag": 12.388, "ks_mag": 11.945,
    },
    {
        "instrument": "JWST_NIRSPEC_G235H", "mast_inst": "NIRSPEC/IFU", "mast_filters": ["F170LP;G235H"],
        "mast_names": ["TWA-28"], "canonical_target": "TWA28", "common_name": "TWA 28 (SSSPM J1102-3431)",
        "role": "SCIENCE", "subrole": "YOUNG_SUBSTELLAR_DISK_G235H", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 5401822669314874240, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 2650.0, "mh_lit": 0.0, "mass_lit": 0.05, "rv_lit": 12.0,
        "j_mag": 13.03, "h_mag": 12.36, "ks_mag": 11.89,
    },
    {
        "instrument": "JWST_NIRSPEC_G235H", "mast_inst": "NIRSPEC/IFU", "mast_filters": ["F170LP;G235H"],
        "mast_names": ["2MASS-J16090141-3925119"], "canonical_target": "J160901", "common_name": "2MASS J16090141-3925119",
        "role": "SCIENCE", "subrole": "UPPER_SCO_PROTOPLANETARY_DISK_G235H", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 5997015079686716672, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 3100.0, "mh_lit": 0.0, "mass_lit": 0.25, "rv_lit": -5.0,
        "j_mag": 12.82, "h_mag": 12.17, "ks_mag": 11.84,
    },
    {
        "instrument": "JWST_NIRSPEC_G235H", "mast_inst": "NIRSPEC/IFU", "mast_filters": ["F170LP;G235H"],
        "mast_names": ["OPH-163131"], "canonical_target": "OPH1631", "common_name": "SSTc2d J163131.2-242627",
        "role": "SCIENCE", "subrole": "EDGE_ON_PROTOPLANETARY_DISK_G235H", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 6047590415519880192, "dist_lit": 139.0, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 3000.0, "mh_lit": 0.0, "mass_lit": 0.30, "rv_lit": -5.0,
        "j_mag": 13.5, "h_mag": 12.7, "ks_mag": 12.2,
    },
    {
        "instrument": "JWST_NIRSPEC_G235H", "mast_inst": "NIRSPEC/SLIT", "mast_filters": ["F170LP;G235H"],
        "mast_names": ["ROSS458C"], "canonical_target": "ROSS458C", "common_name": "Ross 458 (DT Vir / Ross 458 c)",
        "role": "SCIENCE", "subrole": "NEARBY_EXOPLANET_HOST_G235H", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 3737308025029348608, "n_target_pairs": 3, "orbital_campaign": False,
        "nasa_pl_name": "Ross 458 c", "n_exoplanets_lit": 1,
        "ra_lit": 195.1712, "dec_lit": 12.3539, "dist_lit": 11.5094, "teff_lit": 3965.4, "mh_lit": 0.25, "mass_lit": 0.556, "rv_lit": -11.2,
        "j_mag": 6.437, "h_mag": 5.83, "ks_mag": 5.578,
    },
    {
        "instrument": "JWST_NIRSPEC_G235H", "mast_inst": "NIRSPEC/SLIT", "mast_filters": ["F170LP;G235H"],
        "mast_names": ["CHA1107-7626"], "canonical_target": "CHA1107", "common_name": "Cha 1107-7626",
        "role": "SCIENCE", "subrole": "FREE_FLOATING_PLANETARY_MASS_ACCRETOR_G235H", "panchromatic_bridge": False, "radio_mm_id": "",
        "gaia_source_id": 5201355444434076416, "n_target_pairs": 3, "orbital_campaign": False,
        "teff_lit": 2300.0, "mh_lit": 0.0, "mass_lit": 0.01, "rv_lit": 15.0,
        "j_mag": 14.35, "h_mag": 13.71, "ks_mag": 13.17,
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


def mast_invoke(service: str, params: dict[str, Any], timeout_s: float = 60.0) -> dict[str, Any]:
    import time
    payload = urllib.parse.urlencode({"request": json.dumps({"service": service, "params": params, "format": "json"})}).encode()
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request("https://mast.stsci.edu/api/v0/invoke", data=payload,
                                         headers={"User-Agent": "SETIsearch-D090-Build/1.0"})
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"MAST invoke failed after 3 attempts ({service}): {last_err}")


def tap_json(base_url: str, adql: str, timeout_s: float = 60.0) -> dict[str, Any]:
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "json", "QUERY": adql}).encode()
    req = urllib.request.Request(base_url, data=data, headers={"User-Agent": "SETIsearch-D090-Build/1.0"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    c = math.cos(math.radians(0.5 * (dec1 + dec2)))
    dra = ((ra1 - ra2 + 180.0) % 360.0 - 180.0) * c
    ddec = dec1 - dec2
    return math.hypot(dra, ddec) * 3600.0


def fetch_all_pairs_for_target(spec: dict[str, Any], excluded_dp_ids: set[str]) -> list[dict[str, Any]]:
    inst_m = spec["mast_inst"]
    flts = spec["mast_filters"]
    tns = spec["mast_names"]
    rows = mast_invoke("Mast.Caom.Filtered", {
        "columns": "obsid,obs_id,target_name,instrument_name,filters,dataproduct_type,s_ra,s_dec,t_min,t_max,t_exptime,proposal_id",
        "filters": [
            {"paramName": "obs_collection", "values": ["JWST"]},
            {"paramName": "instrument_name", "values": [inst_m]},
            {"paramName": "filters", "values": flts},
            {"paramName": "target_name", "values": tns},
            {"paramName": "dataRights", "values": ["PUBLIC"]},
            {"paramName": "calib_level", "values": ["3"]},
        ], "pagesize": 200, "page": 1,
    }).get("data", [])
    rows = [r for r in rows if r.get("dataproduct_type") != "timeseries"]
    rows.sort(key=lambda r: float(r.get("t_min") or 0.0))

    # Cap CAOM Products queries cleanly across large programs while preserving start/mid/end baseline
    if len(rows) > 5:
        idxs = sorted({0, 1, len(rows) // 2, len(rows) - 2, len(rows) - 1})
        obs_picks = [rows[i] for i in idxs]
    else:
        obs_picks = rows

    pairs_all: list[dict[str, Any]] = []
    seen_prefs: set[str] = set()
    for obs in obs_picks:
        ps = mast_invoke("Mast.Caom.Products", {"obsid": str(obs["obsid"])}).get("data", [])
        l2 = sorted([p for p in ps if p.get("calib_level") == 2 and p["productFilename"].endswith("_x1d.fits")], key=lambda x: x["productFilename"])
        by_pref: dict[str, dict[str, dict[str, Any]]] = {}
        for p in l2:
            fn = p["productFilename"]
            pref = "_".join(fn.split("_")[:-2])
            det = fn.split("_")[-2]
            by_pref.setdefault(pref, {})[det] = p

        t_min = float(obs.get("t_min") or 0.0)
        t_max = float(obs.get("t_max") or t_min)
        n_prefs_here = max(1, len(by_pref))
        # Assign monotonic MJD estimate across exposures within obs
        for pi, (pref, dets) in enumerate(sorted(by_pref.items())):
            if pref in seen_prefs or pref in excluded_dp_ids:
                continue
            if inst_m == "MIRI/IFU":
                if "mirifushort" not in dets or "mirifulong" not in dets:
                    continue
                p1, p2 = dets["mirifushort"], dets["mirifulong"]
            else:
                if "nrs1" not in dets or "nrs2" not in dets:
                    continue
                p1, p2 = dets["nrs1"], dets["nrs2"]
            seen_prefs.add(pref)
            seq = pref.split("_")[1]
            frac = (pi + 0.5) / n_prefs_here
            mjd_est = t_min + frac * max(0.001, t_max - t_min)
            pairs_all.append({
                "dp_id": pref,
                "obs_id": str(obs["obs_id"]),
                "proposal_id": str(obs.get("proposal_id") or ""),
                "filter_caom": str(obs.get("filters") or ""),
                "seq": seq,
                "s_ra": float(obs["s_ra"]),
                "s_dec": float(obs["s_dec"]),
                "mjd_obs": mjd_est,
                "t_exptime": float(obs.get("t_exptime") or 300.0) / max(1, n_prefs_here // 2),
                "det1_name": p1["productFilename"],
                "det1_url": "https://mast.stsci.edu/api/v0.1/Download/file?uri=" + urllib.parse.quote(p1["dataURI"], safe=""),
                "det1_bytes": int(p1["size"]),
                "det2_name": p2["productFilename"],
                "det2_url": "https://mast.stsci.edu/api/v0.1/Download/file?uri=" + urllib.parse.quote(p2["dataURI"], safe=""),
                "det2_bytes": int(p2["size"]),
                "pair_bytes": int(p1["size"]) + int(p2["size"]),
            })
        if spec.get("n_target_pairs", 3) <= 3 and len(pairs_all) >= 6:
            if inst_m != "MIRI/IFU" or len({p["seq"] for p in pairs_all}) >= 3:
                break
    pairs_all.sort(key=lambda x: (x["mjd_obs"], x["dp_id"]))
    return pairs_all


def select_target_pairs(spec: dict[str, Any], all_pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    k_need = int(spec["n_target_pairs"])
    inst = spec["instrument"]
    pool = list(all_pairs)
    if spec.get("prefer_small_pair_bytes"):
        small = [p for p in pool if p["pair_bytes"] < 1_500_000]
        if len(small) >= k_need:
            pool = small

    if inst == "JWST_MIRI_MRS" and k_need == 3:
        by_seq: dict[str, list[dict[str, Any]]] = {}
        for p in pool:
            by_seq.setdefault(p["seq"], []).append(p)
        seqs = sorted(by_seq.keys())
        if len(seqs) >= 3:
            # First 3 distinct grating sequences in chronological/alphabetical visit block (SHORT/MEDIUM/LONG)
            picks = [by_seq[seqs[0]][0], by_seq[seqs[1]][0], by_seq[seqs[2]][0]]
            return sorted(picks, key=lambda x: x["mjd_obs"])

    if inst == "JWST_MIRI_MRS" and k_need == 8:
        # Spread across earliest & latest MJDs while sampling multiple sequences (SHORT/MEDIUM/LONG)
        if len(pool) >= 8:
            # Ensure both start/end sequences AND early/late epochs
            picks = [pool[int(round(i * (len(pool) - 1) / (k_need - 1)))] for i in range(k_need)]
            if len({p["seq"] for p in picks}) < 2:
                # explicitly diversify by seq within pool
                by_s = {}
                for p in pool:
                    by_s.setdefault(p["seq"], []).append(p)
                picks = []
                seqs = sorted(by_s.keys())
                idx_s = 0
                while len(picks) < k_need:
                    lst = by_s[seqs[idx_s % len(seqs)]]
                    cand = lst.pop(0) if idx_s // len(seqs) % 2 == 0 else lst.pop(-1)
                    picks.append(cand)
                    if not lst:
                        seqs.remove(seqs[idx_s % len(seqs)])
                    idx_s += 1
            return sorted(picks[:k_need], key=lambda x: x["mjd_obs"])

    if len(pool) <= k_need:
        return sorted(pool, key=lambda x: x["mjd_obs"])
    idxs = [int(round(i * (len(pool) - 1) / (k_need - 1))) for i in range(k_need)]
    return sorted([pool[i] for i in idxs], key=lambda x: x["mjd_obs"])


def main() -> None:
    inp_dir = ROOT / "inputs_d090_v4_1"
    if inp_dir.exists():
        raise RuntimeError(f"Prospective hygiene violation: {inp_dir} already exists before cohort build/lock!")

    if sha256_file(ARCHIVE_O) != ARCHIVE_O_SHA256:
        raise RuntimeError("Companion Archive O SHA-256 mismatch!")

    print("1. Extracting D089 Archive O baseline & prior exclusion registry...", flush=True)
    with zipfile.ZipFile(ARCHIVE_O, "r") as zf:
        pe89 = json.loads(zf.read(ARCHIVE_O_PREFIX + "PRIOR_EXCLUSION_VERIFICATION.json").decode("utf-8"))
        mm89 = json.loads(zf.read(ARCHIVE_O_PREFIX + "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").decode("utf-8"))
        sum89 = json.loads(zf.read(ARCHIVE_O_PREFIX + "results/SUMMARY.json").decode("utf-8"))
        u250_txt = zf.read(ARCHIVE_O_PREFIX + "results/UNIFIED_PANCHROMATIC_V4_SYNTHESIS_250STARS.csv").decode("utf-8").splitlines()
        br26_txt = zf.read(ARCHIVE_O_PREFIX + "results/PANCHROMATIC_BRIDGE_26STARS.csv").decode("utf-8").splitlines()
        comb_u_txt = zf.read(ARCHIVE_O_PREFIX + "results/ALLSKY_COMB_V4_1_UNIFIED_D079_D089.csv").decode("utf-8").splitlines()
        comb_c_txt = zf.read(ARCHIVE_O_PREFIX + "results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D089.csv").decode("utf-8").splitlines()

    u250_rows = list(csv.DictReader(u250_txt))
    br26_rows = list(csv.DictReader(br26_txt))
    comb_u_rows = list(csv.DictReader(comb_u_txt))
    comb_c_rows = list(csv.DictReader(comb_c_txt))

    prior_v4_snap = {
        "schema": "D090_PRIOR_V4_PHASES_SNAPSHOT",
        "prior_phases": "D079-D089",
        "source_archive_name": ARCHIVE_O.name,
        "source_archive_sha256": ARCHIVE_O_SHA256,
        "prior_v4_unique_stars_count": len(u250_rows),
        "prior_v4_within_10pc_count": sum(1 for r in u250_rows if r["within_10pc"] == "True"),
        "prior_v4_total_exposures_count": sum(int(r["n_exposures_total"]) for r in u250_rows),
        "prior_cumulative_integration_hours": sum89["unified_250star_panchromatic_v4_synthesis"]["total_integration_hours_d079_d089"],
        "prior_v4_calibration_trials_count": sum89["unified_250star_panchromatic_v4_synthesis"]["total_calibration_trials_d079_d089"],
        "prior_v2_false_alarms_eliminated_total": sum89["unified_250star_panchromatic_v4_synthesis"]["v2_false_alarms_eliminated_total"],
        "prior_cumulative_orbital_campaigns_count": sum89["unified_250star_panchromatic_v4_synthesis"]["cumulative_orbital_campaigns"],
        "d089_summary_headline": sum89,
        "unified_250star_rows": u250_rows,
        "d089_bridge_26star_rows": br26_rows,
        "allsky_comb_unified_d079_d089": comb_u_rows,
        "allsky_comb_candidates_d079_d089": comb_c_rows,
    }
    (WS / "PRIOR_V4_PHASES_SNAPSHOT.json").write_text(json.dumps(prior_v4_snap, indent=2) + "\n", encoding="utf-8")
    (WS / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").write_text(json.dumps({**mm89, "schema": "D090_MULTIMESSENGER_RADIO_TESS_SNAPSHOT"}, indent=2) + "\n", encoding="utf-8")

    # Build prior exclusion registry (263 from D089 + 30 D089 brand-new + 3 D090 format checks)
    excluded_dp_ids = set(pe89["excluded_dp_ids"])
    d089_coh_rows = list(csv.DictReader(zf.open(ARCHIVE_O_PREFIX + "FROZEN_COHORT_D089.csv")) if False else [])
    with zipfile.ZipFile(ARCHIVE_O, "r") as zf:
        d089_coh_rows = list(csv.DictReader(zf.read(ARCHIVE_O_PREFIX + "FROZEN_COHORT_D089.csv").decode("utf-8").splitlines()))
    excluded_dp_ids.update(r["dp_id"] for r in d089_coh_rows)

    excluded_coords = list(pe89["excluded_targets_coordinate_registry"])
    seen_lbl = {c["label"] for c in excluded_coords}
    for s in pe89["star_separation_verification"]:
        lbl = f"{s['canonical_target']}(D089)"
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

    nasa_rows = tap_json(
        "https://exoplanetarchive.ipac.caltech.edu/TAP/sync",
        "SELECT pl_name,hostname,ra,dec,pl_orbper,pl_tranmid,pl_orbeccen,tran_flag,st_mass,st_teff,st_met,st_radv,sy_dist FROM pscomppars",
    )
    nasa_by_pl = {r["pl_name"]: r for r in nasa_rows if r.get("pl_name")}

    print(f"3. Fetching MAST JWST L2 (*_x1d.fits) candidate lists across {len(TARGET_SPECS)} targets...", flush=True)
    with ThreadPoolExecutor(max_workers=12) as ex:
        all_pairs_list = list(ex.map(lambda sp: fetch_all_pairs_for_target(sp, excluded_dp_ids), TARGET_SPECS))

    cohort_rows: list[dict[str, Any]] = []
    campaigns_doc: dict[str, Any] = {}
    sep_verif: list[dict[str, Any]] = []
    total_bytes = 0

    for spec, all_pairs in zip(TARGET_SPECS, all_pairs_list):
        st = spec["canonical_target"]
        picked = select_target_pairs(spec, all_pairs)
        assert len(picked) == spec["n_target_pairs"], f"{st}: expected {spec['n_target_pairs']} pairs, got {len(picked)}"

        g = gaia_by_id.get(spec["gaia_source_id"]) if spec["gaia_source_id"] else None
        ra_deg = float(spec.get("ra_lit") or (g["ra"] if g else picked[0]["s_ra"]))
        dec_deg = float(spec.get("dec_lit") or (g["dec"] if g else picked[0]["s_dec"]))
        pmra = float(g["pmra"]) if (g and g.get("pmra") is not None) else 0.0
        pmdec = float(g["pmdec"]) if (g and g.get("pmdec") is not None) else 0.0
        dist_pc = float(spec.get("dist_lit") or (1000.0 / float(g["parallax"]) if (g and g.get("parallax") and float(g["parallax"]) > 0) else 50.0))
        within_10pc = dist_pc <= 10.0

        phot_g = float(g["phot_g_mean_mag"]) if (g and g.get("phot_g_mean_mag") is not None) else ""
        phot_bp = float(g["phot_bp_mean_mag"]) if (g and g.get("phot_bp_mean_mag") is not None) else ""
        phot_rp = float(g["phot_rp_mean_mag"]) if (g and g.get("phot_rp_mean_mag") is not None) else ""

        teff_k = float(g["teff_gspphot"]) if (g and g.get("teff_gspphot") is not None) else float(spec["teff_lit"])
        mh_dex = float(g["mh_gspphot"]) if (g and g.get("mh_gspphot") is not None) else float(spec["mh_lit"])
        prior_rv = float(g["radial_velocity"]) if (g and g.get("radial_velocity") is not None) else float(spec["rv_lit"])
        mass_msun = float(spec["mass_lit"])

        # Independent NASA pscomppars cross-check within 90"
        pl_hits = [r for r in nasa_rows if r.get("ra") is not None and sep_arcsec(ra_deg, dec_deg, float(r["ra"]), float(r["dec"])) < 90.0]
        n_pl = int(spec.get("n_exoplanets_lit") or len(pl_hits))
        if spec["role"] == "CONTROL":
            assert n_pl == 0, f"CONTROL star {st} has {n_pl} planets in NASA pscomppars!"
        has_tr = any(int(r.get("tran_flag") or 0) == 1 for r in pl_hits)

        # Orbital campaign assignment (#81-#90)
        camp_exps: dict[str, dict[str, Any]] = {}
        if spec["orbital_campaign"]:
            if spec.get("null_orbital"):
                t0_bjd = 2460000.5
                p_days = float(spec["orb_per_days"])
                ecc = float(spec["orb_e"])
                pl_name = spec["planet_name"]
                kp = compute_keplerian_kp_kms(mass_msun, p_days, ecc)
            else:
                nr = nasa_by_pl[spec["nasa_pl_name"]]
                p_days = float(nr["pl_orbper"] or spec["orb_per_days"])
                ecc = float(nr["pl_orbeccen"] if nr.get("pl_orbeccen") is not None else spec["orb_e"])
                t0_bjd = float(nr["pl_tranmid"] if nr.get("pl_tranmid") is not None else spec["orb_t0_bjd"])
                mass_msun = float(nr["st_mass"] if nr.get("st_mass") is not None else mass_msun)
                pl_name = spec["nasa_pl_name"]
                kp = compute_keplerian_kp_kms(mass_msun, p_days, ecc)

            with_phi = []
            for idx_e, pr in enumerate(picked):
                bjd_est = pr["mjd_obs"] + 2400000.5
                phi, dv_orb = compute_planet_orbital_rv_kms(bjd_est, t0_bjd, p_days, kp)
                with_phi.append((idx_e, pr, bjd_est, phi, dv_orb))

            # Assign 4 IN_WINDOW and 4 OUT_OF_WINDOW cleanly: sort by abs(phi) if phases diverge, else chronological alternate/split
            phi_span = max(abs(x[3]) for x in with_phi) - min(abs(x[3]) for x in with_phi)
            if spec.get("null_orbital") or phi_span >= 0.10:
                ordered_phi = sorted(with_phi, key=lambda x: abs(x[3]))
                in_ids = {x[1]["dp_id"] for x in ordered_phi[:4]}
            else:
                # Chronological first 4 = IN_WINDOW, last 4 = OUT_OF_WINDOW (strictly disjoint)
                in_ids = {x[1]["dp_id"] for x in with_phi[:4]}

            in_dvs = [x[4] for x in with_phi if x[1]["dp_id"] in in_ids]
            dv_span = max(in_dvs) - min(in_dvs)
            camps_exp_list = []
            for idx_e, pr, bjd_est, phi, dv_orb in with_phi:
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
                "n_in_window": 4, "n_out_of_window": 4, "exposures": camps_exp_list,
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
            total_bytes += pr["pair_bytes"]
            cohort_rows.append({
                "instrument": spec["instrument"], "canonical_target": st, "common_name": spec["common_name"],
                "role": spec["role"], "subrole": spec["subrole"],
                "panchromatic_bridge": spec["panchromatic_bridge"], "radio_mm_id": spec["radio_mm_id"],
                "gaia_source_id": spec["gaia_source_id"] or "", "s_ra": round(ra_deg, 6), "s_dec": round(dec_deg, 6),
                "pmra_mas_yr": round(pmra, 3), "pmdec_mas_yr": round(pmdec, 3),
                "dist_pc": round(dist_pc, 5), "within_10pc": within_10pc,
                "phot_g_mag": round(phot_g, 4) if phot_g != "" else "",
                "phot_bp_mag": round(phot_bp, 4) if phot_bp != "" else "",
                "phot_rp_mag": round(phot_rp, 4) if phot_rp != "" else "",
                "j_mag": spec["j_mag"], "h_mag": spec["h_mag"], "ks_mag": spec["ks_mag"],
                "teff_k": round(teff_k, 1), "mh_dex": round(mh_dex, 3), "stellar_mass_msun": round(mass_msun, 4),
                "prior_rv_kms": round(prior_rv, 4), "n_exoplanets": n_pl, "has_transiting_planet": has_tr,
                "epoch_rank": rank, "dp_id": pr["dp_id"], "obs_id": pr["obs_id"], "proposal_id": pr["proposal_id"],
                "filter_caom": pr["filter_caom"], "seq_id": pr["seq"], "mjd_obs": round(pr["mjd_obs"], 5),
                "t_exptime": round(pr["t_exptime"], 2), "phase_window": ce["phase_window"],
                "signed_phase": ce["signed_phase"], "planet_orbital_rv_kms": ce["planet_orbital_rv_kms"],
                "det1_rel": f"{inst_dir}/{st}/{pr['det1_name']}", "det1_url": pr["det1_url"], "det1_bytes": pr["det1_bytes"],
                "det2_rel": f"{inst_dir}/{st}/{pr['det2_name']}", "det2_url": pr["det2_url"], "det2_bytes": pr["det2_bytes"],
            })

    # Verify intra-D090 brand-new minimum separation
    intra_min = min(
        sep_arcsec(a["ra_deg"], a["dec_deg"], b["ra_deg"], b["dec_deg"])
        for i, a in enumerate(sep_verif)
        for b in sep_verif[i + 1 :]
    )
    min_prior_sep = min(s["min_sky_separation_arcsec"] for s in sep_verif)
    d090_dps = {r["dp_id"] for r in cohort_rows}
    overlap_cnt = len(d090_dps & excluded_dp_ids)
    proj_mib = total_bytes / (1024.0 * 1024.0)
    n_new = len(sep_verif)
    n_new_10pc = sum(1 for s in sep_verif if s["within_10pc"])
    n_bridges = len({r["canonical_target"] for r in cohort_rows if r["panchromatic_bridge"]})

    assert overlap_cnt == 0, f"dp_id overlap {overlap_cnt}!"
    assert n_new == 30 and n_bridges == 7 and n_new_10pc == 4, (n_new, n_bridges, n_new_10pc)
    assert len(campaigns_doc) == 10, len(campaigns_doc)
    assert proj_mib <= 235.0, f"Projected {proj_mib:.2f} MiB > 235 MiB!"
    assert min_prior_sep >= 600.0 and intra_min >= 300.0, (min_prior_sep, intra_min)
    assert not inp_dir.exists(), "inputs_d090_v4_1 must not exist!"

    with (WS / "FROZEN_COHORT_D090.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cohort_rows[0].keys()))
        w.writeheader()
        w.writerows(cohort_rows)

    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(
        json.dumps({"schema": "D090_ORBITAL_CAMPAIGNS_V1", "phase_id": "D090", "n_campaigns": len(campaigns_doc), "campaigns": campaigns_doc}, indent=2) + "\n",
        encoding="utf-8",
    )

    pe90 = {
        "schema": "D090_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D090",
        "verified_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prior_phases_covered": "C001-C037 + D001-D089",
        "format_check_excluded_targets": [x[0] for x in FORMAT_CHECK_EXCLUDED],
        "n_prior_excluded_coords": len(excluded_coords),
        "n_prior_excluded_dp_ids": len(excluded_dp_ids),
        "d090_total_stars": n_new + n_bridges,
        "d090_brand_new_unique_stars": n_new,
        "d090_panchromatic_bridge_stars": n_bridges,
        "d090_brand_new_within_10pc": n_new_10pc,
        "d090_total_exposures": len(cohort_rows),
        "d090_projected_download_bytes": total_bytes,
        "d090_projected_download_gib": round(total_bytes / (1024.0 ** 3), 4),
        "d090_projected_download_mib": round(proj_mib, 2),
        "d090_dp_id_overlap_count": overlap_cnt,
        "min_brand_new_sky_separation_arcsec": round(min_prior_sep, 2),
        "min_intra_d090_brand_new_separation_arcsec": round(intra_min, 2),
        "star_separation_verification": sep_verif,
        "excluded_dp_ids": sorted(excluded_dp_ids),
        "excluded_targets_coordinate_registry": excluded_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pe90, indent=2) + "\n", encoding="utf-8")

    print(
        f"DONE build_cohort: {len(cohort_rows)} paired exposures ({2*len(cohort_rows)} L2 FITS), "
        f"{n_new + n_bridges} stars ({n_new} new [{n_new_10pc} <10pc] + {n_bridges} bridges), "
        f"{len(campaigns_doc)} orbital campaigns, proj={proj_mib:.2f} MiB, dp_overlap={overlap_cnt}, "
        f"min_prior_sep={min_prior_sep:.1f}\", min_intra_sep={intra_min:.1f}\"",
        flush=True,
    )


if __name__ == "__main__":
    main()
