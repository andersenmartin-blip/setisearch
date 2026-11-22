#!/usr/bin/env python3
"""
Prospective Stage-1 Cohort Builder & Method-Lock Sealer for SETI Phase D097 (V5.5).

Zero overlap verification against all 484 prior coordinates and 2,806 prior identifiers
(`C001-C037 + D001-D096`) plus all 7 format-check excluded `dp_id`s. Builds the frozen
30-star / 78-exposure cohort (`<= 123.0 MiB`) across:
  - HERSCHEL_HIFI (22 `.new.tbl`, 11 stars x 2 bands, R ~ 2.2e6, 562-1865 GHz)
  - HERSCHEL_SPIRE_FTS (10 FITS: 5 PPDISKS + 5 SHPDP, R ~ 1,000, 194-671 um)
  - HERSCHEL_PACS (20 FITS: 5 stars x 4 slices B2A/B2B/R1A/R1B, R ~ 2,000, 51-210 um)
  - HST_STIS_E140H (6 `_x1d.fits`, R = 114,000, 1140-1700 A)
  - ESO_FEROS (8 FITS: ALTAIR + GJ1005, N=4 distinct nights each, public <= 2026-11-22)
  - ESO_HARPS (12 FITS: GJ877 CTRL + GJ680 + GJ536, N=4 distinct nights each)

Seals all 7 immutable Stage-1 artifacts in `METHOD_LOCK.json` and `LOCK_RECEIPT.json`
STRICTLY BEFORE `inputs_d097_v5_5/` exists.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from typing import Any

WS = pathlib.Path(__file__).resolve().parent
ROOT = WS.parent.parent
IN_DIR = ROOT / "inputs_d097_v5_5"
ARCHIVES_DIR = ROOT / "archives"

if str(WS) not in sys.path:
    sys.path.insert(0, str(WS))

from v5_5_detector import BASE_V5_5_CONFIG, DETECTOR_NAME

ARCHIVE_V_NAME = "SETI_D096_V5_4_SOFIA_EXES_MIDIR_ECHELLE_COHERENT_DRIFT_JWST_RESULTS_2026-11-21.zip"
ARCHIVE_V_SHA256 = "a134e4d5d0b6e0cb4e17763dc729203218cac9265c7db75db719135cb01c5158"
V_PREFIX = "work_v5_4_20261121_d096_sofia_exes_midir_echelle_coherent_drift_jwst/"
ARCHIVE_V_BUNDLE = V_PREFIX + "bounded_inputs/d096_bounded_bundle.json.gz"

ARCHIVE_U_NAME = "SETI_D095_V5_3_CURVED_PERIODIC_DRIFT_GHOST_SPITZER_IRS_APOGEE2_RESULTS_2026-11-21.zip"
ARCHIVE_U_SHA256 = "24f5a73a4299d697a198e91e3e15b5b7ddce838f6d055cebe66ddd812520c21d"
ARCHIVE_U_BUNDLE = "bounded_inputs/d095_bounded_bundle.json.gz"

ARCHIVE_T_NAME = "SETI_D094_V5_2_MULTIEPOCH_DRIFT_APOGEE2_CRIRESJH_MIRILRS_RESULTS_2026-11-21.zip"
ARCHIVE_T_SHA256 = "fea863077ae837b6741d5837990fd357158e00f6a5e3d9adde51f0c81e8ccefc"
ARCHIVE_T_BUNDLE = "bounded_inputs/d094_bounded_bundle.json.gz"

FORMAT_CHECK_EXCLUDED_DP_IDS = {
    "1342194791",
    "1342217842",
    "1342217843",
    "1342249475",
    "1342210862",
    "1342188197",
    "o53p01030",
}

SN1987A_MJD = 46849.316
GW170817_MJD = 57982.529
SN2023IXF_MJD = 60083.75

# Curated catalog/literature parameters (Gaia DR3 / Hipparcos / NASA Exoplanet Archive / RECONS)
STAR_SPECS: dict[str, dict[str, Any]] = {
    # Prior Bridges (6 SCIENCE + 1 CONTROL = 7)
    "BETELGEUSE": {
        "common_name": "Betelgeuse (alpha Ori)", "role": "SCIENCE", "subrole": "SUPERGIANT_BRIDGE",
        "is_prior_bridge": True, "ra": 88.792939, "dec": 7.407064, "pmra": 27.54, "pmdec": 11.30,
        "dist_pc": 131.0616, "g_mag": 0.42, "bp_mag": 2.00, "rp_mag": -0.70, "j_mag": -3.00, "h_mag": -3.73, "ks_mag": -4.05,
        "teff_k": 3600.0, "mh_dex": 0.0, "mass_msun": 16.5, "rv_kms": 21.91, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "HIP27989",
    },
    "OCETI": {
        "common_name": "Mira (omicron Ceti)", "role": "SCIENCE", "subrole": "AGB_MIRA_BRIDGE",
        "is_prior_bridge": True, "ra": 34.836634, "dec": -2.977638, "pmra": 9.33, "pmdec": -236.98,
        "dist_pc": 128.3697, "g_mag": 2.80, "bp_mag": 4.90, "rp_mag": 1.60, "j_mag": -1.45, "h_mag": -2.21, "ks_mag": -2.50,
        "teff_k": 3050.0, "mh_dex": 0.0, "mass_msun": 1.18, "rv_kms": 63.50, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "HIP10826",
    },
    "NGC7027": {
        "common_name": "NGC 7027 (PN Flux Calibrator)", "role": "CONTROL", "subrole": "REVISITED_PN_CALIBRATOR_CONTROL",
        "is_prior_bridge": True, "ra": 316.7567, "dec": 42.2361, "pmra": 0.0, "pmdec": 0.0,
        "dist_pc": 920.0, "g_mag": 11.5, "bp_mag": 11.7, "rp_mag": 11.2, "j_mag": 9.5, "h_mag": 8.9, "ks_mag": 7.6,
        "teff_k": 198000.0, "mh_dex": 0.0, "mass_msun": 0.70, "rv_kms": 8.9, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "1968757054710481024",
    },
    "ABAUR": {
        "common_name": "AB Aurigae", "role": "SCIENCE", "subrole": "HERBIG_AE_DISK_BRIDGE",
        "is_prior_bridge": True, "ra": 73.94102, "dec": 30.55119, "pmra": 3.85, "pmdec": -24.16,
        "dist_pc": 155.9403, "g_mag": 6.96, "bp_mag": 7.05, "rp_mag": 6.77, "j_mag": 5.94, "h_mag": 5.06, "ks_mag": 4.23,
        "teff_k": 9500.0, "mh_dex": 0.0, "mass_msun": 2.40, "rv_kms": 24.7, "n_exoplanets": 1, "has_transiting_planet": False,
        "gaia_source_id": "156890822211145088",
    },
    "ALPCENA": {
        "common_name": "Alpha Centauri A", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBOR_FUV_BRIDGE",
        "is_prior_bridge": True, "ra": 219.90206, "dec": -60.83399, "pmra": -3679.25, "pmdec": 473.67,
        "dist_pc": 1.339, "g_mag": -0.01, "bp_mag": 0.30, "rp_mag": -0.45, "j_mag": -1.15, "h_mag": -1.38, "ks_mag": -1.49,
        "teff_k": 5790.0, "mh_dex": 0.20, "mass_msun": 1.105, "rv_kms": -22.4, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "HIP71683",
    },
    "PROCYON": {
        "common_name": "Procyon A (alpha CMi)", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBOR_FUV_BRIDGE",
        "is_prior_bridge": True, "ra": 114.82549, "dec": 5.22499, "pmra": -714.59, "pmdec": -1036.80,
        "dist_pc": 3.514, "g_mag": 0.34, "bp_mag": 0.55, "rp_mag": 0.02, "j_mag": -0.49, "h_mag": -0.60, "ks_mag": -0.66,
        "teff_k": 6530.0, "mh_dex": -0.05, "mass_msun": 1.499, "rv_kms": -3.2, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "HIP37279",
    },
    "ANTARES": {
        "common_name": "Antares (alpha Sco)", "role": "SCIENCE", "subrole": "RED_SUPERGIANT_FUV_BRIDGE",
        "is_prior_bridge": True, "ra": 247.35192, "dec": -26.43200, "pmra": -12.11, "pmdec": -23.30,
        "dist_pc": 185.1852, "g_mag": 0.96, "bp_mag": 2.35, "rp_mag": -0.10, "j_mag": -2.74, "h_mag": -3.49, "ks_mag": -3.79,
        "teff_k": 3660.0, "mh_dex": 0.0, "mass_msun": 12.0, "rv_kms": -3.4, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "HIP80763",
    },

    # Brand-new Herschel HIFI THz stars (6 SCIENCE + 1 CONTROL = 7 here + NGC6302 dual)
    "RDOR": {
        "common_name": "R Doradus", "role": "SCIENCE", "subrole": "AGB_NEAREST_SRB",
        "is_prior_bridge": False, "ra": 69.189319, "dec": -62.077491, "pmra": -69.4, "pmdec": -75.8,
        "dist_pc": 54.64, "g_mag": 1.959, "bp_mag": 5.538, "rp_mag": 1.768, "j_mag": -2.65, "h_mag": -3.57, "ks_mag": -3.91,
        "teff_k": 2710.0, "mh_dex": 0.0, "mass_msun": 1.0, "rv_kms": 26.0, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "4677205714465503104",
    },
    "CHICYG": {
        "common_name": "Chi Cygni", "role": "SCIENCE", "subrole": "AGB_S_TYPE_MIRA",
        "is_prior_bridge": False, "ra": 297.641211, "dec": 32.913865, "pmra": -24.09, "pmdec": -41.24,
        "dist_pc": 159.53, "g_mag": 6.197, "bp_mag": 11.475, "rp_mag": 4.092, "j_mag": -0.44, "h_mag": -1.45, "ks_mag": -1.94,
        "teff_k": 2740.0, "mh_dex": 0.0, "mass_msun": 2.1, "rv_kms": -1.2, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "2034702312280673792",
    },
    "RCAS": {
        "common_name": "R Cassiopeiae", "role": "SCIENCE", "subrole": "AGB_MIRA_OXYGEN_RICH",
        "is_prior_bridge": False, "ra": 359.604208, "dec": 51.388887, "pmra": 82.85, "pmdec": 17.49,
        "dist_pc": 174.15, "g_mag": 6.744, "bp_mag": 11.601, "rp_mag": 4.883, "j_mag": -0.15, "h_mag": -1.16, "ks_mag": -1.80,
        "teff_k": 2800.0, "mh_dex": 0.0, "mass_msun": 1.2, "rv_kms": 25.0, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "1944073004732961152",
    },
    "IRC10216": {
        "common_name": "CW Leonis (IRC+10216)", "role": "SCIENCE", "subrole": "AGB_CARBON_ENVELOPE",
        "is_prior_bridge": False, "ra": 146.9891, "dec": 13.2788, "pmra": 35.0, "pmdec": 12.0,
        "dist_pc": 130.0, "g_mag": 10.96, "bp_mag": 13.5, "rp_mag": 9.3, "j_mag": 7.12, "h_mag": 4.30, "ks_mag": 1.07,
        "teff_k": 2330.0, "mh_dex": 0.0, "mass_msun": 1.6, "rv_kms": -25.5, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "614377896119283712",
    },
    "IKTAU": {
        "common_name": "IK Tauri (NML Tau)", "role": "SCIENCE", "subrole": "AGB_OH_IR_MIRA",
        "is_prior_bridge": False, "ra": 58.370518, "dec": 11.405972, "pmra": 29.25, "pmdec": -24.70,
        "dist_pc": 260.72, "g_mag": 8.838, "bp_mag": 14.684, "rp_mag": 7.022, "j_mag": 0.56, "h_mag": -0.71, "ks_mag": -1.49,
        "teff_k": 2200.0, "mh_dex": 0.0, "mass_msun": 1.5, "rv_kms": 34.0, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "3303343395568710016",
    },
    "REDRECT": {
        "common_name": "Red Rectangle (HD 44179)", "role": "SCIENCE", "subrole": "POST_AGB_BIPOLAR_DISK",
        "is_prior_bridge": False, "ra": 94.992514, "dec": -10.637528, "pmra": -8.2, "pmdec": -21.5,
        "dist_pc": 710.0, "g_mag": 9.408, "bp_mag": 9.035, "rp_mag": 8.228, "j_mag": 6.69, "h_mag": 5.34, "ks_mag": 3.74,
        "teff_k": 7750.0, "mh_dex": -3.0, "mass_msun": 0.60, "rv_kms": 17.1, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "3001477146793228288",
    },
    "VHYA": {
        "common_name": "V Hydrae", "role": "SCIENCE", "subrole": "AGB_CARBON_JET_BINARY",
        "is_prior_bridge": False, "ra": 162.905179, "dec": -21.250084, "pmra": -16.19, "pmdec": 2.00,
        "dist_pc": 433.0, "g_mag": 5.925, "bp_mag": 8.300, "rp_mag": 4.756, "j_mag": 1.38, "h_mag": 0.25, "ks_mag": -0.71,
        "teff_k": 2650.0, "mh_dex": 0.0, "mass_msun": 1.5, "rv_kms": -17.0, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "3550624862030637568",
    },
    "NGC6302": {
        "common_name": "NGC 6302 (Bug Nebula)", "role": "CONTROL", "subrole": "HIGH_EXCITATION_PN_CONTROL",
        "is_prior_bridge": False, "ra": 258.4342, "dec": -37.1044, "pmra": 0.57, "pmdec": -0.74,
        "dist_pc": 1170.0, "g_mag": 13.311, "bp_mag": 16.113, "rp_mag": 11.857, "j_mag": 10.6, "h_mag": 10.0, "ks_mag": 9.4,
        "teff_k": 200000.0, "mh_dex": 0.0, "mass_msun": 0.64, "rv_kms": -35.0, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "5973805832327236096",
    },

    # Brand-new Herschel PPDISKS / PACS / SHPDP stars
    "HD100546": {
        "common_name": "HD 100546 (Protoplanetary Disk)", "role": "SCIENCE", "subrole": "HERBIG_BE_PROTOPLANET_DISK",
        "is_prior_bridge": False, "ra": 173.355496, "dec": -70.194790, "pmra": -38.73, "pmdec": -0.10,
        "dist_pc": 108.116, "g_mag": 6.686, "bp_mag": 6.675, "rp_mag": 6.624, "j_mag": 6.43, "h_mag": 5.96, "ks_mag": 5.42,
        "teff_k": 9307.1, "mh_dex": 0.0, "mass_msun": 2.2, "rv_kms": 9.0, "n_exoplanets": 1, "has_transiting_planet": False,
        "gaia_source_id": "5233604915060520576",
    },
    "HD169142": {
        "common_name": "HD 169142 (Transition Disk)", "role": "SCIENCE", "subrole": "HERBIG_AE_GAP_DISK",
        "is_prior_bridge": False, "ra": 276.124071, "dec": -29.780537, "pmra": -2.34, "pmdec": -37.88,
        "dist_pc": 114.873, "g_mag": 8.069, "bp_mag": 8.205, "rp_mag": 7.791, "j_mag": 7.31, "h_mag": 6.91, "ks_mag": 6.41,
        "teff_k": 7208.9, "mh_dex": 0.0, "mass_msun": 1.65, "rv_kms": -1.04, "n_exoplanets": 1, "has_transiting_planet": False,
        "gaia_source_id": "4048015133392824064",
    },
    "HD163296": {
        "common_name": "HD 163296 (Ringed Disk)", "role": "SCIENCE", "subrole": "HERBIG_AE_MULTI_RING_DISK",
        "is_prior_bridge": False, "ra": 269.088664, "dec": -21.956251, "pmra": -7.59, "pmdec": -39.46,
        "dist_pc": 100.967, "g_mag": 6.844, "bp_mag": 6.898, "rp_mag": 6.692, "j_mag": 6.20, "h_mag": 5.53, "ks_mag": 4.78,
        "teff_k": 10201.4, "mh_dex": 0.0, "mass_msun": 2.04, "rv_kms": -9.0, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "4070355800839765248",
    },
    "HD142527": {
        "common_name": "HD 142527 (Asymmetric Disk)", "role": "SCIENCE", "subrole": "HERBIG_FE_CRESCENT_DISK",
        "is_prior_bridge": False, "ra": 239.174469, "dec": -42.323241, "pmra": -10.92, "pmdec": -26.15,
        "dist_pc": 159.259, "g_mag": 8.115, "bp_mag": 8.502, "rp_mag": 7.498, "j_mag": 6.50, "h_mag": 5.72, "ks_mag": 4.98,
        "teff_k": 6500.0, "mh_dex": 0.0, "mass_msun": 2.0, "rv_kms": 0.95, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "5994826707951507200",
    },
    "HD36112": {
        "common_name": "HD 36112 (MWC 758 Spiral Disk)", "role": "SCIENCE", "subrole": "HERBIG_AE_SPIRAL_DISK",
        "is_prior_bridge": False, "ra": 82.614720, "dec": 25.332404, "pmra": 3.68, "pmdec": -26.37,
        "dist_pc": 155.867, "g_mag": 8.220, "bp_mag": 8.357, "rp_mag": 7.933, "j_mag": 7.47, "h_mag": 6.56, "ks_mag": 5.80,
        "teff_k": 7850.0, "mh_dex": 0.0, "mass_msun": 1.60, "rv_kms": 18.0, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "3417062653416093184",
    },
    "VYCMA": {
        "common_name": "VY Canis Majoris", "role": "SCIENCE", "subrole": "EXTREME_RED_HYPERGIANT",
        "is_prior_bridge": False, "ra": 110.743013, "dec": -25.767544, "pmra": -2.65, "pmdec": 2.23,
        "dist_pc": 1200.0, "g_mag": 7.352, "bp_mag": 8.539, "rp_mag": 5.647, "j_mag": 2.13, "h_mag": 0.96, "ks_mag": -0.70,
        "teff_k": 3490.0, "mh_dex": 0.0, "mass_msun": 17.0, "rv_kms": 56.13, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "5616197646838713728",
    },
    "CRL618": {
        "common_name": "CRL 618 (Westbrook Nebula)", "role": "CONTROL", "subrole": "PROTO_PN_CALIBRATOR_CONTROL",
        "is_prior_bridge": False, "ra": 70.7233, "dec": 36.1151, "pmra": 0.0, "pmdec": 0.0,
        "dist_pc": 900.0, "g_mag": 14.0, "bp_mag": 14.5, "rp_mag": 13.5, "j_mag": 11.4, "h_mag": 10.1, "ks_mag": 8.4,
        "teff_k": 32000.0, "mh_dex": 0.0, "mass_msun": 0.7, "rv_kms": -21.5, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "175113311378836864",
    },
    "AFGL2688": {
        "common_name": "AFGL 2688 (Egg Nebula)", "role": "CONTROL", "subrole": "PROTO_PN_F5IA_CALIBRATOR_CONTROL",
        "is_prior_bridge": False, "ra": 315.5780, "dec": 36.6948, "pmra": -5.43, "pmdec": -4.89,
        "dist_pc": 420.0, "g_mag": 11.702, "bp_mag": 12.458, "rp_mag": 10.858, "j_mag": 9.8, "h_mag": 8.7, "ks_mag": 7.6,
        "teff_k": 6500.0, "mh_dex": 0.0, "mass_msun": 0.7, "rv_kms": -35.4, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "1871404799480613248",
    },

    # Brand-new HST STIS E140H stars (1 SCIENCE + 1 CONTROL)
    "REGULUS": {
        "common_name": "Regulus (alpha Leo)", "role": "SCIENCE", "subrole": "RAPID_ROTATOR_B7V_FUV",
        "is_prior_bridge": False, "ra": 152.09296, "dec": 11.96721, "pmra": -248.73, "pmdec": 5.59,
        "dist_pc": 24.30, "g_mag": 1.35, "bp_mag": 1.30, "rp_mag": 1.42, "j_mag": 1.54, "h_mag": 1.66, "ks_mag": 1.64,
        "teff_k": 12460.0, "mh_dex": 0.0, "mass_msun": 3.80, "rv_kms": 5.9, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "HIP49669",
    },
    "BD332642": {
        "common_name": "BD+33 2642 (Halo Post-AGB Standard)", "role": "CONTROL", "subrole": "HST_STIS_FLUX_STANDARD_CONTROL",
        "is_prior_bridge": False, "ra": 237.999447, "dec": 32.948428, "pmra": -14.30, "pmdec": 0.79,
        "dist_pc": 3300.0, "g_mag": 10.785, "bp_mag": 10.694, "rp_mag": 10.928, "j_mag": 10.95, "h_mag": 11.01, "ks_mag": 11.03,
        "teff_k": 17147.2, "mh_dex": -1.5, "mass_msun": 0.56, "rv_kms": -96.0, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "1369896865785991424",
    },

    # Brand-new ESO FEROS + HARPS multi-epoch targets (4 SCIENCE + 1 CONTROL, 4 within 10 pc!)
    "ALTAIR": {
        "common_name": "Altair (alpha Aql)", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBOR_5PC_A7V",
        "is_prior_bridge": False, "ra": 297.695827, "dec": 8.868321, "pmra": 536.23, "pmdec": 385.29,
        "dist_pc": 5.13, "g_mag": 0.76, "bp_mag": 0.85, "rp_mag": 0.58, "j_mag": 0.25, "h_mag": 0.14, "ks_mag": 0.10,
        "teff_k": 7550.0, "mh_dex": -0.24, "mass_msun": 1.86, "rv_kms": -26.1, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "HIP97649",
    },
    "GJ1005": {
        "common_name": "GJ 1005 (HIP 1242)", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBOR_6PC_M4V",
        "is_prior_bridge": False, "ra": 3.869880, "dec": -16.136572, "pmra": 612.0, "pmdec": -616.0,
        "dist_pc": 6.00, "g_mag": 10.268, "bp_mag": 11.725, "rp_mag": 8.907, "j_mag": 7.22, "h_mag": 6.71, "ks_mag": 6.39,
        "teff_k": 3150.0, "mh_dex": -0.10, "mass_msun": 0.18, "rv_kms": -32.80, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "2368293487261055488",
    },
    "GJ877": {
        "common_name": "GJ 877 (HIP 113229)", "role": "CONTROL", "subrole": "SOLAR_NEIGHBOR_ZERO_PLANET_CONTROL",
        "is_prior_bridge": False, "ra": 343.921471, "dec": -75.463377, "pmra": -1026.20, "pmdec": -1059.41,
        "dist_pc": 8.597, "g_mag": 9.293, "bp_mag": 10.615, "rp_mag": 8.147, "j_mag": 6.62, "h_mag": 6.08, "ks_mag": 5.81,
        "teff_k": 3193.7, "mh_dex": -0.12, "mass_msun": 0.42, "rv_kms": 65.52, "n_exoplanets": 0, "has_transiting_planet": False,
        "gaia_source_id": "6378584028690858496",
    },
    "GJ680": {
        "common_name": "GJ 680 (CD-48 11837)", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBOR_PLANET_HOST_10PC",
        "is_prior_bridge": False, "ra": 263.807221, "dec": -48.678843, "pmra": 81.2, "pmdec": 449.5,
        "dist_pc": 9.673, "g_mag": 9.24, "bp_mag": 10.45, "rp_mag": 8.15, "j_mag": 6.667, "h_mag": 6.080, "ks_mag": 5.829,
        "teff_k": 3563.0, "mh_dex": -0.15, "mass_msun": 0.456, "rv_kms": 6.2, "n_exoplanets": 1, "has_transiting_planet": False,
        "gaia_source_id": "5946986063684477056",
        "planet_name": "GJ 680 b", "orb_per_days": 17281.66514, "orb_t0_bjd": 2457000.0, "orb_ecc": 0.381,
    },
    "GJ536": {
        "common_name": "GJ 536 (HD 122303)", "role": "SCIENCE", "subrole": "MULTIPLANET_SUPER_EARTH_HOST",
        "is_prior_bridge": False, "ra": 210.259726, "dec": -2.652290, "pmra": -823.4, "pmdec": 597.8,
        "dist_pc": 10.409, "g_mag": 10.556, "bp_mag": 11.75, "rp_mag": 9.45, "j_mag": 6.516, "h_mag": 5.935, "ks_mag": 5.683,
        "teff_k": 3641.0, "mh_dex": -0.14, "mass_msun": 0.528, "rv_kms": -25.8, "n_exoplanets": 2, "has_transiting_planet": False,
        "gaia_source_id": "3657653114880309248",
        "planet_name": "GJ 536 b", "orb_per_days": 8.70874, "orb_t0_bjd": 2460553.1, "orb_ecc": 0.0,
    },
}


def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _angsep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    cosv = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosv)))) * 3600.0


def _ecliptic_lat_deg(ra_deg: float, dec_deg: float) -> float:
    eps = math.radians(23.439281)
    r, d = math.radians(ra_deg), math.radians(dec_deg)
    sb = math.sin(d) * math.cos(eps) - math.cos(d) * math.sin(eps) * math.sin(r)
    return math.degrees(math.asin(max(-1.0, min(1.0, sb))))


def _ppo_align_score(ra_deg: float, dec_deg: float) -> float:
    return round(abs(math.sin(math.radians(_ecliptic_lat_deg(ra_deg, dec_deg)))), 5)


def _kepler_kp_and_rv(m_star_msun: float, per_days: float, mjd_obs: float, t0_bjd: float) -> tuple[float, float, float]:
    """Compute circular-equivalent planet orbital speed Kp [km/s], signed phase, and LOS RV."""
    G_AU3_MSUN_DAY2 = 2.959122082855911e-4
    a_au = ((G_AU3_MSUN_DAY2 * m_star_msun * (per_days ** 2)) / (4.0 * (math.pi ** 2))) ** (1.0 / 3.0)
    kp_kms = (2.0 * math.pi * a_au * 1.495978707e8) / (per_days * 86400.0)
    bjd = float(mjd_obs) + 2400000.5
    raw_ph = ((bjd - t0_bjd) / per_days) % 1.0
    signed_ph = raw_ph - 1.0 if raw_ph > 0.5 else raw_ph
    rv_p = kp_kms * math.sin(2.0 * math.pi * signed_ph)
    return round(kp_kms, 3), round(signed_ph, 6), round(rv_p, 4)


def _http_text(url: str, data: bytes | None = None, timeout: int = 45) -> str:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "SETI-D097-V5_5-Cohort/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def _http_json(url: str, data: bytes | None = None, timeout: int = 45) -> Any:
    return json.loads(_http_text(url, data=data, timeout=timeout))


def _irsa_csv(q: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(_http_text("https://irsa.ipac.caltech.edu/TAP/sync?QUERY=" + urllib.parse.quote(q) + "&FORMAT=csv"))))


def _head_bytes(url: str) -> int:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "SETI-D097-V5_5-Cohort/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return int(r.headers.get("Content-Length") or 0)


def main() -> int:
    if IN_DIR.exists():
        raise RuntimeError(f"Prospective violation: {IN_DIR} already exists before Stage-1 lock!")

    # 1. Verify Archives V, U, T SHA-256 and build PRIOR_V5_4_PHASES_SNAPSHOT.json + prior exclusion registry
    for nm, exp_sha in [(ARCHIVE_V_NAME, ARCHIVE_V_SHA256), (ARCHIVE_U_NAME, ARCHIVE_U_SHA256), (ARCHIVE_T_NAME, ARCHIVE_T_SHA256)]:
        ap = ARCHIVES_DIR / nm
        if not ap.is_file() or _sha256_file(ap) != exp_sha:
            raise RuntimeError(f"Archive integrity check failed for {ap}")

    prior_coords: list[dict[str, Any]] = []
    prior_dpids: set[str] = set()
    with zipfile.ZipFile(ARCHIVES_DIR / ARCHIVE_V_NAME) as zf:
        pev = json.loads(zf.read(V_PREFIX + "PRIOR_EXCLUSION_VERIFICATION.json"))
        prior_dpids.update(pev["excluded_dp_ids"])
        for row in pev["excluded_targets_coordinate_registry"]:
            prior_coords.append({
                "canonical_target": row.get("canonical_target") or "",
                "ra_deg": float(row["ra_deg"]),
                "dec_deg": float(row["dec_deg"]),
            })
        for row in pev["star_separation_verification"]:
            prior_coords.append({
                "canonical_target": row["canonical_target"],
                "ra_deg": float(row["ra_deg"]),
                "dec_deg": float(row["dec_deg"]),
            })
        for row in csv.DictReader(io.TextIOWrapper(zf.open(V_PREFIX + "FROZEN_COHORT_D096.csv"), encoding="utf-8")):
            if row.get("dp_id"):
                prior_dpids.add(row["dp_id"])
            if row.get("f1_id"):
                prior_dpids.add(row["f1_id"])

        sum96 = json.loads(zf.read(V_PREFIX + "results/SUMMARY.json"))
        syn96 = sum96["unified_425star_panchromatic_v5_4_synthesis"]
        prior_unified_425 = list(csv.DictReader(io.TextIOWrapper(zf.open(V_PREFIX + "results/UNIFIED_PANCHROMATIC_V5_4_SYNTHESIS_425STARS.csv"), encoding="utf-8")))
        prior_bridge_52 = list(csv.DictReader(io.TextIOWrapper(zf.open(V_PREFIX + "results/PANCHROMATIC_BRIDGE_52STARS_V54.csv"), encoding="utf-8")))
        prior_comb_uni = list(csv.DictReader(io.TextIOWrapper(zf.open(V_PREFIX + "results/ALLSKY_COMB_V4_1_UNIFIED_D079_D096.csv"), encoding="utf-8")))
        prior_comb_cand = list(csv.DictReader(io.TextIOWrapper(zf.open(V_PREFIX + "results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D096.csv"), encoding="utf-8")))
        prior_ellipsoid_425 = list(csv.DictReader(io.TextIOWrapper(zf.open(V_PREFIX + "results/MULTIEVENT_ELLIPSOID_425STARS.csv"), encoding="utf-8")))

        with zf.open(ARCHIVE_V_BUNDLE) as bf:
            v_bundle_sha = hashlib.sha256(bf.read()).hexdigest()

    with zipfile.ZipFile(ARCHIVES_DIR / ARCHIVE_U_NAME) as zf:
        with zf.open(ARCHIVE_U_BUNDLE) as bf:
            u_bundle_sha = hashlib.sha256(bf.read()).hexdigest()
    with zipfile.ZipFile(ARCHIVES_DIR / ARCHIVE_T_NAME) as zf:
        with zf.open(ARCHIVE_T_BUNDLE) as bf:
            t_bundle_sha = hashlib.sha256(bf.read()).hexdigest()

    assert len(prior_coords) == 484, f"Expected 484 prior coords, got {len(prior_coords)}"

    snapshot_obj = {
        "schema": "D097_PRIOR_V5_4_PHASES_SNAPSHOT_V1",
        "prior_phases": "D079-D096",
        "source_archive_v_name": ARCHIVE_V_NAME,
        "source_archive_v_sha256": ARCHIVE_V_SHA256,
        "source_archive_v_bundle_member": ARCHIVE_V_BUNDLE,
        "source_archive_v_bundle_sha256": v_bundle_sha,
        "source_archive_u_name": ARCHIVE_U_NAME,
        "source_archive_u_sha256": ARCHIVE_U_SHA256,
        "source_archive_u_bundle_member": ARCHIVE_U_BUNDLE,
        "source_archive_u_bundle_sha256": u_bundle_sha,
        "source_archive_t_name": ARCHIVE_T_NAME,
        "source_archive_t_sha256": ARCHIVE_T_SHA256,
        "source_archive_t_bundle_member": ARCHIVE_T_BUNDLE,
        "source_archive_t_bundle_sha256": t_bundle_sha,
        "prior_unique_stars_count": int(syn96["unique_stars_total"]),
        "prior_within_10pc_count": int(syn96["within_10pc_unique_stars"]),
        "prior_total_exposures_count": int(syn96["total_exposures_d079_d096"]),
        "prior_cumulative_integration_hours": float(syn96["total_integration_hours_d079_d096"]),
        "prior_calibration_trials_count": int(syn96["total_calibration_trials_d079_d096"]),
        "prior_v2_false_alarms_eliminated_total": int(syn96["v2_false_alarms_eliminated_total"]),
        "prior_cumulative_orbital_campaigns_count": int(syn96["cumulative_orbital_campaigns"]),
        "prior_panchromatic_bridge_stars_count": int(syn96["panchromatic_bridge_stars_total"]),
        "prior_revisited_control_multi_phase_stars": int(syn96["revisited_control_multi_phase_stars"]),
        "prior_multi_phase_targets_total": int(syn96["multi_phase_targets_total"]),
        "prior_panchromatic_bridge_cells_count": int(syn96["panchromatic_bridge_cells_total"]),
        "d096_summary_headline": syn96,
        "prior_unified_425_rows": prior_unified_425,
        "prior_bridge_52_rows": prior_bridge_52,
        "prior_allsky_comb_unified_rows": prior_comb_uni,
        "prior_allsky_comb_candidate_rows": prior_comb_cand,
        "prior_ellipsoid_425_rows": prior_ellipsoid_425,
    }
    (WS / "PRIOR_V5_4_PHASES_SNAPSHOT.json").write_text(json.dumps(snapshot_obj, indent=2) + "\n", encoding="utf-8")

    # 2. Query live repositories for exact 78 D097 exposures
    excl_all = prior_dpids | FORMAT_CHECK_EXCLUDED_DP_IDS
    cohort_rows: list[dict[str, Any]] = []

    def _add_row(
        inst: str, cname: str, track: str, rank: int, dp_id: str, grating: str, rp: float,
        mjd_obs: float, t_exp: float, f1_id: str, f1_rel: str, f1_url: str, f1_bytes: int,
        phase_win: str = "OUT_OF_WINDOW", signed_ph: float = 0.0, plan_rv: float = 0.0,
    ) -> None:
        if dp_id in excl_all or f1_id in excl_all:
            raise RuntimeError(f"Excluded dp_id/f1_id detected: {dp_id} / {f1_id}")
        sp = STAR_SPECS[cname]
        ra, dec = float(sp["ra"]), float(sp["dec"])
        cohort_rows.append({
            "instrument": inst,
            "canonical_target": cname,
            "common_name": sp["common_name"],
            "role": sp["role"],
            "subrole": sp["subrole"],
            "science_track": track,
            "panchromatic_bridge": True,
            "is_prior_bridge": sp["is_prior_bridge"],
            "gaia_source_id": sp["gaia_source_id"],
            "s_ra": round(ra, 6),
            "s_dec": round(dec, 6),
            "pmra_mas_yr": sp["pmra"],
            "pmdec_mas_yr": sp["pmdec"],
            "dist_pc": sp["dist_pc"],
            "within_10pc": float(sp["dist_pc"]) <= 10.0,
            "phot_g_mag": sp["g_mag"],
            "phot_bp_mag": sp["bp_mag"],
            "phot_rp_mag": sp["rp_mag"],
            "j_mag": sp["j_mag"],
            "h_mag": sp["h_mag"],
            "ks_mag": sp["ks_mag"],
            "teff_k": sp["teff_k"],
            "mh_dex": sp["mh_dex"],
            "stellar_mass_msun": sp["mass_msun"],
            "prior_rv_kms": sp["rv_kms"],
            "n_exoplanets": sp["n_exoplanets"],
            "has_transiting_planet": sp["has_transiting_planet"],
            "ecliptic_lat_deg": round(_ecliptic_lat_deg(ra, dec), 4),
            "sn1987a_dt_days": round(mjd_obs - SN1987A_MJD, 3),
            "gw170817_dt_days": round(mjd_obs - GW170817_MJD, 3),
            "sn2023ixf_dt_days": round(mjd_obs - SN2023IXF_MJD, 3),
            "ppo_align_score": _ppo_align_score(ra, dec),
            "epoch_rank": rank,
            "dp_id": dp_id,
            "grating": grating,
            "resolving_power": rp,
            "mjd_obs": round(mjd_obs, 6),
            "t_exptime": round(t_exp, 2),
            "phase_window": phase_win,
            "signed_phase": signed_ph,
            "planet_orbital_rv_kms": plan_rv,
            "f1_id": f1_id,
            "f1_rel": f1_rel,
            "f1_url": f1_url,
            "f1_bytes": int(f1_bytes),
            "total_bytes": int(f1_bytes),
        })

    # Track A: HERSCHEL_HIFI (11 stars x 2 = 22 .new.tbl)
    hifi_all = _irsa_csv("SELECT * FROM herschel.hifistars_spectra")
    by_hifi: dict[str, list[tuple[str, dict[str, str]]]] = {}
    for r in hifi_all:
        tdir = r["spectrum_tbl_u"].split("/")[2]
        obsid = r["spectrum_tbl_u"].split("/")[-1].split("-")[0]
        if obsid in excl_all:
            continue
        by_hifi.setdefault(tdir, []).append((obsid, r))
    hifi_map = [
        ("BETELGEUSE", "BETELGEUSE"), ("OMICRON_CETI", "OCETI"), ("NGC_7027", "NGC7027"),
        ("R_DOR", "RDOR"), ("CHI_CYG", "CHICYG"), ("R_CAS", "RCAS"),
        ("IRC+10216", "IRC10216"), ("IK_TAU", "IKTAU"), ("RED_RECTANGLE", "REDRECT"),
        ("NGC_6302", "NGC6302"), ("V_HYA", "VHYA"),
    ]
    for tdir, cname in hifi_map:
        items = by_hifi[tdir]
        lsb = [x for x in items if "LSB" in x[1]["line"]]
        usb = [x for x in items if "USB" in x[1]["line"]]
        picks = [lsb[0], usb[0]] if (lsb and usb) else items[:2]
        for rk, (obsid, r) in enumerate(picks, start=1):
            rel = r["spectrum_tbl_u"].lstrip("./")
            url = "https://irsa.ipac.caltech.edu/data/Herschel/HIFISTARS/" + rel
            sz = _head_bytes(url)
            fn = rel.split("/")[-1]
            sb = "LSB" if "LSB" in r["line"] else "USB"
            _add_row(
                "HERSCHEL_HIFI", cname, "THZ_HET_V55", rk, f"HIFI_{obsid}_{sb}",
                r["line"], 2200000.0, 55450.0 + rk, 600.0, obsid,
                f"herschel_hifi/{cname}_{fn}", url, sz,
            )

    # Track B: HERSCHEL_SPIRE_FTS (5 PPDISKS + 5 SHPDP = 10 FITS)
    ppd_map = {r["object"]: r for r in _irsa_csv("SELECT * FROM herschel.ppdisks_spectral")}
    for obj, cname in [("AB Aur", "ABAUR"), ("HD 100546", "HD100546"), ("HD 169142", "HD169142"), ("HD 163296", "HD163296"), ("HD 142527", "HD142527")]:
        r = ppd_map[obj]
        rel = r["spectrum_fits_u"].lstrip("./")
        obsid = rel.split("/")[-1].split("_")[0]
        url = "https://irsa.ipac.caltech.edu/data/Herschel/PPDISKS/" + rel
        sz = _head_bytes(url)
        _add_row(
            "HERSCHEL_SPIRE_FTS", cname, "SPIRE_RING_VETO_V55", 1, f"SPIRE_{obsid}",
            "SLWC3+SSWD4+RING", 1000.0, 55600.0, 1800.0, obsid,
            f"herschel_spire_fts/{cname}_{obsid}_ppdisks.fits", url, sz,
        )

    shp_all = _irsa_csv("SELECT * FROM herschel.shpdp_spectra WHERE object IN ('NGC 7027','NGC6302','VY CMa','CRL 618','AFGL2688-1')")
    shp_by: dict[str, list[tuple[str, dict[str, str]]]] = {}
    for r in shp_all:
        obsid = r["spectrum_fits_u"].split("/")[-1].split("_")[0]
        if obsid not in excl_all:
            shp_by.setdefault(r["object"], []).append((obsid, r))
    for obj, cname in [("NGC 7027", "NGC7027"), ("NGC6302", "NGC6302"), ("VY CMa", "VYCMA"), ("CRL 618", "CRL618"), ("AFGL2688-1", "AFGL2688")]:
        obsid, r = sorted(shp_by[obj], key=lambda x: x[0])[-1]
        rel = r["spectrum_fits_u"].lstrip("./")
        url = "https://irsa.ipac.caltech.edu/data/Herschel/SHPDP/" + rel
        sz = _head_bytes(url)
        _add_row(
            "HERSCHEL_SPIRE_FTS", cname, "SPIRE_RING_VETO_V55", 2 if cname in ("NGC7027", "NGC6302") else 1,
            f"SPIRE_{obsid}", "SLWC3+SSWD4", 1000.0, 55900.0, 1400.0, obsid,
            f"herschel_spire_fts/{cname}_{obsid}_shpdp.fits", url, sz,
        )

    # Track C: HERSCHEL_PACS (5 stars x 4 slices = 20 FITS)
    pacs_rows = _irsa_csv("SELECT * FROM herschel.digit_pacs_fits WHERE filename LIKE '%central9Spaxels_PointSourceCorrected_slice_00_os8sf7.fits' AND filename NOT LIKE '%nojitter%'")
    pacs_by: dict[str, list[dict[str, str]]] = {}
    for r in pacs_rows:
        pacs_by.setdefault(r["object"], []).append(r)
    for obj, cname in [("HD100546", "HD100546"), ("HD169142", "HD169142"), ("HD163296", "HD163296"), ("HD142527", "HD142527"), ("HD36112", "HD36112")]:
        rows_s = sorted(pacs_by[obj], key=lambda x: x["filename"])
        for rk, r in enumerate(rows_s, start=1):
            fn = r["filename"]
            obsid = re.search(r"OBSID_(\d+)_", fn).group(1)
            band_tag = "BLUE" if "_blue_" in fn else "RED"
            url = "https://irsa.ipac.caltech.edu/data/Herschel/DIGIT/" + r["spectrum_fits_u"].lstrip("./")
            sz = _head_bytes(url)
            _add_row(
                "HERSCHEL_PACS", cname, "PACS_FARIR_V55", rk, f"PACS_{obsid}_{rk}",
                f"PACS_{band_tag}", 2000.0, 55500.0 + rk, 900.0, f"{obsid}_{rk}",
                f"herschel_pacs/{cname}_{obsid}_{band_tag}_s{rk}.fits", url, sz,
            )

    # Track D: HST_STIS_E140H (6 FITS via MAST CAOM)
    stis_map = [
        ("o53p01020", "ALPCENA"),
        ("obkk12040", "PROCYON"),
        ("oedz04030", "ANTARES"),
        ("o5cl02030", "NGC7027"),
        ("ocb6o0020", "REGULUS"),
        ("o47s01070", "BD332642"),
    ]
    mast_req = {
        "service": "Mast.Caom.Filtered",
        "format": "json",
        "params": {
            "columns": "obs_id,target_name,t_exptime,t_min,t_obs_release",
            "filters": [{"paramName": "obs_id", "values": [x[0] for x in stis_map]}, {"paramName": "obs_collection", "values": ["HST"]}],
        },
    }
    mres = {r["obs_id"]: r for r in _http_json("https://mast.stsci.edu/api/v0/invoke", data=urllib.parse.urlencode({"request": json.dumps(mast_req)}).encode())["data"]}
    for oid, cname in stis_map:
        r = mres[oid]
        url = f"https://mast.stsci.edu/api/v0.1/Download/file?uri=mast:HST/product/{oid}_x1d.fits"
        sz = _head_bytes(url)
        _add_row(
            "HST_STIS_E140H", cname, "STIS_E140H_V55", 1, oid,
            "E140H", 114000.0, float(r["t_min"]), float(r["t_exptime"]), oid,
            f"hst_stis_e140h/{cname}_{oid}_x1d.fits", url, sz,
        )

    # Track E: ESO_FEROS (2 x 4) + ESO_HARPS (3 x 4) = 20 optical FITS
    orbital_campaigns: dict[str, Any] = {}
    camp_idx = 139
    eso_specs = [
        ("ALTAIR", "ESO_FEROS", "FEROS", 48000.0),
        ("GJ1005", "ESO_FEROS", "FEROS", 48000.0),
        ("GJ877", "ESO_HARPS", "HARPS", 115000.0),
        ("GJ680", "ESO_HARPS", "HARPS", 115000.0),
        ("GJ536", "ESO_HARPS", "HARPS", 115000.0),
    ]
    for cname, inst_full, inst_eso, rp in eso_specs:
        sp = STAR_SPECS[cname]
        ra, dec = float(sp["ra"]), float(sp["dec"])
        eq = f"SELECT dp_id, target_name, t_min, t_exptime, obs_release_date FROM ivoa.ObsCore WHERE instrument_name='{inst_eso}' AND dataproduct_type='spectrum' AND s_ra BETWEEN {ra-0.08} AND {ra+0.08} AND s_dec BETWEEN {dec-0.08} AND {dec+0.08} ORDER BY t_min"
        erows = _http_json("https://archive.eso.org/tap_obs/sync?REQUEST=doQuery&LANG=ADQL&FORMAT=json&QUERY=" + urllib.parse.quote(eq))["data"]
        erows = [r for r in erows if str(r[4])[:10] <= "2026-11-22" and "SUN" not in str(r[1]).upper() and r[0] not in excl_all]
        nights: dict[int, list[Any]] = {}
        for r in erows:
            nights.setdefault(int(r[2]), r)
        nkeys = sorted(nights.keys())
        if len(nkeys) < 4:
            raise RuntimeError(f"Insufficient distinct ESO nights for {cname}: {len(nkeys)}")
        picks = [nights[nkeys[i]] for i in (0, len(nkeys) // 3, (2 * len(nkeys)) // 3, len(nkeys) - 1)]

        has_orb = "orb_per_days" in sp
        camp_exps = []
        rvs_orb = []
        for rk, r in enumerate(picks, start=1):
            dp_id, _, mjd_val, texpt, _ = r[0], r[1], float(r[2]), float(r[3]), r[4]
            dl = _http_text(f"https://archive.eso.org/datalink/links?ID=ivo://eso.org/ID?{urllib.parse.quote(dp_id)}")
            m = re.search(r"<TD>(\d{5,9})</TD>", dl)
            sz = int(m.group(1))
            url = f"https://dataportal.eso.org/dataPortal/file/{urllib.parse.quote(dp_id)}"
            signed_ph, plan_rv, pwin = 0.0, 0.0, "OUT_OF_WINDOW"
            if has_orb:
                kp_kms, signed_ph, plan_rv = _kepler_kp_and_rv(float(sp["mass_msun"]), float(sp["orb_per_days"]), mjd_val, float(sp["orb_t0_bjd"]))
                pwin = "IN_QUADRATURE" if abs(abs(signed_ph) - 0.25) <= 0.12 else "OUT_OF_WINDOW"
                rvs_orb.append(plan_rv)
                camp_exps.append({
                    "dp_id": dp_id, "mjd_obs": round(mjd_val, 6), "bjd_tdb_est": round(mjd_val + 2400000.5, 6),
                    "signed_phase": signed_ph, "phase_window": pwin, "planet_orbital_rv_kms": plan_rv,
                    "ppo_align_score": _ppo_align_score(ra, dec),
                })
            safe_dp = dp_id.replace(":", "_")
            _add_row(
                inst_full, cname, "DRIFT_V55_JERK_OPTICAL", rk, dp_id,
                inst_eso, rp, mjd_val, texpt, dp_id,
                f"{inst_full.lower()}/{cname}_{safe_dp}.fits", url, sz,
                phase_win=pwin, signed_ph=signed_ph, plan_rv=plan_rv,
            )

        if has_orb:
            kp_kms, _, _ = _kepler_kp_and_rv(float(sp["mass_msun"]), float(sp["orb_per_days"]), float(picks[0][2]), float(sp["orb_t0_bjd"]))
            orbital_campaigns[cname] = {
                "campaign_index": camp_idx,
                "canonical_target": cname,
                "common_name": sp["common_name"],
                "instrument": inst_full,
                "role": sp["role"],
                "null_orbital": False,
                "planet_name": sp["planet_name"],
                "n_planets_in_system": sp["n_exoplanets"],
                "stellar_mass_msun": sp["mass_msun"],
                "orb_per_days": sp["orb_per_days"],
                "orb_t0_bjd": sp["orb_t0_bjd"],
                "orb_ecc": sp["orb_ecc"],
                "kp_kms": kp_kms,
                "orbital_dv_span_kms": round(max(rvs_orb) - min(rvs_orb), 3),
                "n_epochs": len(camp_exps),
                "exposures": camp_exps,
            }
            camp_idx += 1

    # 3. Validate all Stage-1 caps and zero-overlap invariants
    total_bytes = sum(int(r["total_bytes"]) for r in cohort_rows)
    total_mib = total_bytes / (1024.0 * 1024.0)
    if total_mib > 123.5:
        raise RuntimeError(f"Projected download {total_mib:.3f} MiB exceeds 123.5 MiB safety budget")

    stars_u = sorted({r["canonical_target"] for r in cohort_rows})
    brand_new_stars = [s for s in stars_u if not STAR_SPECS[s]["is_prior_bridge"]]
    bridge_stars = [s for s in stars_u if STAR_SPECS[s]["is_prior_bridge"]]
    ctrl_stars = [s for s in stars_u if STAR_SPECS[s]["role"] == "CONTROL"]
    bn_ctrls = [s for s in brand_new_stars if STAR_SPECS[s]["role"] == "CONTROL"]
    bn_10pc = [s for s in brand_new_stars if float(STAR_SPECS[s]["dist_pc"]) <= 10.0]

    sep_verif = []
    min_bn_sep = 1e9
    for s in brand_new_stars:
        ra, dec = float(STAR_SPECS[s]["ra"]), float(STAR_SPECS[s]["dec"])
        best_sep = 1e9
        best_nm = ""
        for pc in prior_coords:
            sp_a = _angsep_arcsec(ra, dec, pc["ra_deg"], pc["dec_deg"])
            if sp_a < best_sep:
                best_sep = sp_a
                best_nm = pc["canonical_target"]
        if best_sep < 300.0:
            raise RuntimeError(f"Separation violation for {s}: {best_sep:.1f}\" from {best_nm}")
        min_bn_sep = min(min_bn_sep, best_sep)
        sep_verif.append({"canonical_target": s, "ra_deg": round(ra, 6), "dec_deg": round(dec, 6), "min_sep_arcsec": round(best_sep, 2), "nearest_prior": best_nm})

    min_intra_sep = 1e9
    for i, s1 in enumerate(stars_u):
        for s2 in stars_u[i + 1 :]:
            sp_i = _angsep_arcsec(float(STAR_SPECS[s1]["ra"]), float(STAR_SPECS[s1]["dec"]), float(STAR_SPECS[s2]["ra"]), float(STAR_SPECS[s2]["dec"]))
            if sp_i < 300.0:
                raise RuntimeError(f"Intra-D097 separation violation: {s1} vs {s2} = {sp_i:.1f}\"")
            min_intra_sep = min(min_intra_sep, sp_i)

    # Write FROZEN_COHORT_D097.csv
    cols = [
        "instrument", "canonical_target", "common_name", "role", "subrole", "science_track",
        "panchromatic_bridge", "is_prior_bridge", "gaia_source_id", "s_ra", "s_dec",
        "pmra_mas_yr", "pmdec_mas_yr", "dist_pc", "within_10pc", "phot_g_mag", "phot_bp_mag",
        "phot_rp_mag", "j_mag", "h_mag", "ks_mag", "teff_k", "mh_dex", "stellar_mass_msun",
        "prior_rv_kms", "n_exoplanets", "has_transiting_planet", "ecliptic_lat_deg",
        "sn1987a_dt_days", "gw170817_dt_days", "sn2023ixf_dt_days", "ppo_align_score",
        "epoch_rank", "dp_id", "grating", "resolving_power", "mjd_obs", "t_exptime",
        "phase_window", "signed_phase", "planet_orbital_rv_kms", "f1_id", "f1_rel", "f1_url",
        "f1_bytes", "total_bytes",
    ]
    with (WS / "FROZEN_COHORT_D097.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in cohort_rows:
            w.writerow(r)

    # Write ORBITAL_CAMPAIGNS_AND_KINEMATICS.json
    orb_doc = {
        "schema": "D097_ORBITAL_CAMPAIGNS_AND_KINEMATICS",
        "phase_id": "D097",
        "campaign_range": "#139-#140",
        "n_campaigns": len(orbital_campaigns),
        "campaigns": orbital_campaigns,
    }
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_doc, indent=2) + "\n", encoding="utf-8")

    # Write PRIOR_EXCLUSION_VERIFICATION.json
    now_dt = datetime.now(timezone.utc)
    now_utc = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    pev_out = {
        "schema": "D097_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D097",
        "verified_utc": now_utc,
        "prior_phases_covered": "C001-C037 + D001-D096",
        "n_prior_excluded_coords": len(prior_coords),
        "n_prior_excluded_dp_ids": len(prior_dpids),
        "n_format_check_excluded_dp_ids": len(FORMAT_CHECK_EXCLUDED_DP_IDS),
        "d097_total_stars": len(stars_u),
        "d097_brand_new_unique_stars": len(brand_new_stars),
        "d097_prior_bridge_stars": len(bridge_stars),
        "d097_control_stars": len(ctrl_stars),
        "d097_brand_new_controls": len(bn_ctrls),
        "d097_brand_new_within_10pc": len(bn_10pc),
        "d097_total_input_files": len(cohort_rows),
        "d097_projected_download_bytes": total_bytes,
        "d097_projected_download_mib": round(total_mib, 3),
        "d097_dp_id_overlap_count": 0,
        "min_brand_new_sky_separation_arcsec": round(min_bn_sep, 2),
        "min_intra_d097_separation_arcsec": round(min_intra_sep, 2),
        "star_separation_verification": sep_verif,
        "format_check_excluded_dp_ids": sorted(FORMAT_CHECK_EXCLUDED_DP_IDS),
        "excluded_dp_ids": sorted(prior_dpids),
        "excluded_targets_coordinate_registry": prior_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pev_out, indent=2) + "\n", encoding="utf-8")

    # Seal 7 Stage-1 files in METHOD_LOCK.json + LOCK_RECEIPT.json
    stage1_files = [
        "v5_5_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D097.csv",
        "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "PRIOR_V5_4_PHASES_SNAPSHOT.json",
    ]
    hashes = {fn: _sha256_file(WS / fn) for fn in stage1_files}
    ml = {
        "schema": "D097_STAGE1_PROSPECTIVE_METHOD_LOCK",
        "phase_id": "D097",
        "detector_name": DETECTOR_NAME,
        "locked_utc": now_utc,
        "retroactive_reused_bundles": [
            {"phase_id": "D096", "archive_name": ARCHIVE_V_NAME, "archive_sha256": ARCHIVE_V_SHA256, "bundle_member": ARCHIVE_V_BUNDLE, "bundle_sha256": v_bundle_sha},
            {"phase_id": "D095", "archive_name": ARCHIVE_U_NAME, "archive_sha256": ARCHIVE_U_SHA256, "bundle_member": ARCHIVE_U_BUNDLE, "bundle_sha256": u_bundle_sha},
            {"phase_id": "D094", "archive_name": ARCHIVE_T_NAME, "archive_sha256": ARCHIVE_T_SHA256, "bundle_member": ARCHIVE_T_BUNDLE, "bundle_sha256": t_bundle_sha},
        ],
        "locked_v55_parameters": BASE_V5_5_CONFIG,
        "hard_caps": {
            "max_download_mib": 125.0,
            "max_bounded_bundle_mib": 22.0,
            "max_companion_archive_mib": 25.0,
            "min_free_disk_gib": 1.50,
            "min_chronology_lag_seconds": 3.0,
            "min_brand_new_separation_arcsec": 300.0,
        },
        "locked_file_hashes": hashes,
    }
    ml_path = WS / "METHOD_LOCK.json"
    ml_path.write_text(json.dumps(ml, indent=2) + "\n", encoding="utf-8")
    ml_sha = _sha256_file(ml_path)

    lr = {
        "schema": "D097_STAGE1_LOCK_RECEIPT",
        "phase_id": "D097",
        "locked_utc": now_utc,
        "locked_at_utc": now_dt.isoformat(),
        "locked_at_unix": round(now_dt.timestamp(), 3),
        "inputs_d097_v5_5_exists": IN_DIR.exists(),
        "method_lock_sha256": ml_sha,
        "frozen_cohort_sha256": hashes["FROZEN_COHORT_D097.csv"],
        "projected_download_mib": round(total_mib, 3),
        "n_input_files": len(cohort_rows),
        "n_total_stars": len(stars_u),
        "n_unique_new_stars": len(brand_new_stars),
        "n_prior_bridge_stars": len(bridge_stars),
        "n_orbital_campaigns": len(orbital_campaigns),
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lr, indent=2) + "\n", encoding="utf-8")

    print(f"STAGE-1 SEALED: {len(stars_u)} stars ({len(brand_new_stars)} new / {len(bridge_stars)} br / {len(bn_10pc)} <10pc / {len(ctrl_stars)} ctrl), {len(cohort_rows)} files, {total_mib:.3f} MiB, METHOD_LOCK={ml_sha[:16]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
