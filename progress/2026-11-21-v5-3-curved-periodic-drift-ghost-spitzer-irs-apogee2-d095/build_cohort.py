#!/usr/bin/env python3
"""
Phase D095 (`V5.3`) Prospective Cohort Freeze & Stage-1 Lock Builder.

Runs strictly BEFORE `<ROOT>/inputs_d095_v5_3/` exists:
  1. Verifies Archive T (`D094`) & Archive Q (`D091`), extracting all 432 prior excluded
     coordinates and 2,665 prior `dp_id`s plus the unified 373-star / 41-bridge / 424-comb snapshot.
  2. Queries ESA Gaia DR3, NOIRLab `sdss_dr17.apogee2_allstar`, SDSS SkyServer `apogeeVisit`,
     CADC `ivoa.ObsCore` + DataLink (`GEMINI_GHOST` BLUE/RED DRAGONS), IRSA `irs_enhv211`
     (`SPITZER_IRS`), and NASA Exoplanet Archive `pscomppars`.
  3. Asserts zero `dp_id` overlap, `>= 300.0"` separation for all 28 brand-new stars,
     `<= 125.0 MiB` total download via HTTP HEAD, and `>= 5.0 km/s` orbital `dv_span`
     across all 8 orbital campaigns (`#126-#133`).
  4. Seals Stage-1 lock (`METHOD_LOCK.json`, `LOCK_RECEIPT.json`, `inputs_d095_v5_3_exists: false`).
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import itertools
import json
import math
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from typing import Any

WS = pathlib.Path(__file__).resolve().parent
ROOT = WS.parent.parent
sys.path.insert(0, str(WS))

import v5_3_detector as det

ARCHIVE_Q_NAME = "SETI_D091_V4_2_ESO_TRIPLE_3ARM_RESULTS_2026-11-20.zip"
ARCHIVE_Q_SHA256 = "9da4739bdb413d675b9bc1f17dc9d60d5abc7944622714017cf1889a097b51d0"
ARCHIVE_Q_BUNDLE_MEMBER = "work_eso_triple_3arm_20261120_d091_v4_2_xshooter_feros_giraffe/bounded_inputs/d091_bounded_bundle.json.gz"

ARCHIVE_T_NAME = "SETI_D094_V5_2_MULTIEPOCH_DRIFT_APOGEE2_CRIRESJH_MIRILRS_RESULTS_2026-11-21.zip"
ARCHIVE_T_SHA256 = "fea863077ae837b6741d5837990fd357158e00f6a5e3d9adde51f0c81e8ccefc"
ARCHIVE_T_BUNDLE_MEMBER = "bounded_inputs/d094_bounded_bundle.json.gz"

# Exclude non-science format-check items inspected during design
FORMAT_CHECK_EXCLUDED_DP_IDS = [
    "GHOST.S20240719S0043_blue001_dragons",
    "GHOST.S20240719S0043_red001_dragons",
    "GHOST.S20240910S0031_blue001_dragons",
    "GHOST.S20240910S0031_red001_dragons",
    "SPITZER_IRS.r18829056",
]

# Stream A: 10 brand-new SDSS_APOGEE2 targets (4 Kepler orbital + 3 ETZ + 1 <10pc + 2 hot controls)
APOGEE2_SPECS: list[dict[str, Any]] = [
    {"canonical_target": "KEPLER37", "common_name": "Kepler-37", "apogee_id": "2M18561431+4431052", "telescope": "apo25m", "field": "K07_075+17", "gaia_source_id": 2106674071344722688, "role": "SCIENCE", "subrole": "SCIENCE_KEPLER_ORBITAL_PERIODIC", "science_track": "DRIFT_V53_PERIODIC_ORBITAL", "nasa_host": "Kepler-37", "orbital_campaign": True, "campaign_index": 130, "prefer_planet": "Kepler-37 b", "teff_lit": 5417.0, "mh_lit": -0.32, "mass_lit": 0.803, "rv_lit": -30.5, "j_lit": 8.356, "h_lit": 8.000, "ks_lit": 7.934},
    {"canonical_target": "KEPLER409", "common_name": "Kepler-409", "apogee_id": "2M19344300+4651099", "telescope": "apo25m", "field": "K10_079+12", "gaia_source_id": 2128215909315876352, "role": "SCIENCE", "subrole": "SCIENCE_KEPLER_ORBITAL_PERIODIC", "science_track": "DRIFT_V53_PERIODIC_ORBITAL", "nasa_host": "Kepler-409", "orbital_campaign": True, "campaign_index": 131, "prefer_planet": "Kepler-409 b", "teff_lit": 5460.0, "mh_lit": 0.08, "mass_lit": 0.920, "rv_lit": -52.5, "j_lit": 8.210, "h_lit": 7.838, "ks_lit": 7.779},
    {"canonical_target": "KEPLER93", "common_name": "Kepler-93", "apogee_id": "2M19254039+3840204", "telescope": "apo25m", "field": "K21_071+10", "gaia_source_id": 2052747119115620352, "role": "SCIENCE", "subrole": "SCIENCE_KEPLER_ORBITAL_PERIODIC", "science_track": "DRIFT_V53_PERIODIC_ORBITAL", "nasa_host": "Kepler-93", "orbital_campaign": True, "campaign_index": 132, "prefer_planet": "Kepler-93 b", "teff_lit": 5669.0, "mh_lit": -0.18, "mass_lit": 0.911, "rv_lit": 26.8, "j_lit": 8.807, "h_lit": 8.445, "ks_lit": 8.374},
    {"canonical_target": "KEPLER1869", "common_name": "Kepler-1869", "apogee_id": "2M19302763+4245513", "telescope": "apo25m", "field": "K16_075+11", "gaia_source_id": 2125751461382627840, "role": "SCIENCE", "subrole": "SCIENCE_KEPLER_ORBITAL_PERIODIC", "science_track": "DRIFT_V53_PERIODIC_ORBITAL", "nasa_host": "Kepler-1869", "orbital_campaign": True, "campaign_index": 133, "prefer_planet": "Kepler-1869 c", "teff_lit": 4844.0, "mh_lit": -0.05, "mass_lit": 0.77, "rv_lit": -15.0, "j_lit": 9.210, "h_lit": 8.764, "ks_lit": 8.650},
    {"canonical_target": "2M00100614", "common_name": "2M0010+0113 (ETZ)", "apogee_id": "2M00100614+0113152", "telescope": "apo25m", "field": "100-60", "gaia_source_id": 2546554416958404864, "role": "SCIENCE", "subrole": "SCIENCE_ETZ_CURVED_PERIODIC", "science_track": "DRIFT_V53_ETZ_PERIODIC", "nasa_host": "", "orbital_campaign": False, "teff_lit": 4903.9, "mh_lit": -0.039, "mass_lit": 0.80, "rv_lit": 20.6665, "j_lit": 10.765, "h_lit": 10.297, "ks_lit": 10.220},
    {"canonical_target": "2M00050730", "common_name": "2M0005+0022 (ETZ)", "apogee_id": "2M00050730+0022104", "telescope": "apo25m", "field": "100-60", "gaia_source_id": 2546106851302477696, "role": "SCIENCE", "subrole": "SCIENCE_ETZ_CURVED_PERIODIC", "science_track": "DRIFT_V53_ETZ_PERIODIC", "nasa_host": "", "orbital_campaign": False, "teff_lit": 6244.1, "mh_lit": -0.175, "mass_lit": 1.15, "rv_lit": -19.594, "j_lit": 10.119, "h_lit": 9.894, "ks_lit": 9.860},
    {"canonical_target": "2M00013563", "common_name": "2M0001+0026 (ETZ)", "apogee_id": "2M00013563+0026413", "telescope": "apo25m", "field": "100-60", "gaia_source_id": 2738227163723846656, "role": "SCIENCE", "subrole": "SCIENCE_ETZ_CURVED_PERIODIC", "science_track": "DRIFT_V53_ETZ_PERIODIC", "nasa_host": "", "orbital_campaign": False, "teff_lit": 6055.3, "mh_lit": -0.228, "mass_lit": 1.08, "rv_lit": -1.6247, "j_lit": 10.928, "h_lit": 10.687, "ks_lit": 10.680},
    {"canonical_target": "GJ3801", "common_name": "GJ 3801 (Ross 1015)", "apogee_id": "2M13424328+3317255", "telescope": "apo25m", "field": "060+78_MGA", "gaia_source_id": 1470462322431834880, "role": "SCIENCE", "subrole": "SCIENCE_10PC_APOGEE2_N2", "science_track": "APOGEE2_10PC_HBAND", "nasa_host": "", "orbital_campaign": False, "teff_lit": 3368.6, "mh_lit": -0.1, "mass_lit": 0.30, "rv_lit": 6.75, "j_lit": 7.787, "h_lit": 7.212, "ks_lit": 6.982},
    {"canonical_target": "2M23032370", "common_name": "2M2303+6026 (Control B)", "apogee_id": "2M23032370+6026433", "telescope": "apo25m", "field": "109+00", "gaia_source_id": 2014431578426474112, "role": "CONTROL", "subrole": "CONTROL_HOT_BSTAR_N6", "science_track": "DRIFT_V53_PERIODIC_CONTROL", "nasa_host": "", "orbital_campaign": False, "teff_lit": 17336.5, "mh_lit": 0.0, "mass_lit": 5.0, "rv_lit": 28.2003, "j_lit": 6.735, "h_lit": 6.806, "ks_lit": 6.819},
    {"canonical_target": "2M01452047", "common_name": "2M0145+3542 (Control B)", "apogee_id": "2M01452047+3542450", "telescope": "apo25m", "field": "135-24_btx", "gaia_source_id": 318404174969644800, "role": "CONTROL", "subrole": "CONTROL_HOT_BSTAR_N6", "science_track": "DRIFT_V53_PERIODIC_CONTROL", "nasa_host": "", "orbital_campaign": False, "teff_lit": 14798.6, "mh_lit": 0.0, "mass_lit": 4.0, "rv_lit": 10.1752, "j_lit": 6.874, "h_lit": 6.815, "ks_lit": 6.758},
]

# Stream B: 7 GEMINI_GHOST targets (6 brand-new + 1 bridge LTT9779; paired BLUE + RED DRAGONS)
GHOST_SPECS: list[dict[str, Any]] = [
    {"canonical_target": "WASP74", "common_name": "WASP-74", "cadc_target": "WASP-74b", "gaia_source_id": 4224062406762625152, "role": "SCIENCE", "subrole": "SCIENCE_TRANSITING_ORBITAL_N3", "science_track": "GHOST_SKYVETO_ORBITAL", "nasa_host": "WASP-74", "orbital_campaign": True, "campaign_index": 126, "prefer_planet": "WASP-74 b", "n_target_epochs": 3, "panchromatic_bridge": False, "is_prior_bridge": False, "teff_lit": 5984.0, "mh_lit": 0.39, "mass_lit": 1.48, "rv_lit": -15.9, "j_lit": 8.55, "h_lit": 8.31, "ks_lit": 8.22},
    {"canonical_target": "WASP178", "common_name": "WASP-178", "cadc_target": "WASP-178", "gaia_source_id": 6003809889735481856, "role": "SCIENCE", "subrole": "SCIENCE_TRANSITING_ORBITAL_HOTJUP", "science_track": "GHOST_SKYVETO_ORBITAL", "nasa_host": "WASP-178", "orbital_campaign": True, "campaign_index": 127, "prefer_planet": "WASP-178 b", "n_target_epochs": 2, "panchromatic_bridge": False, "is_prior_bridge": False, "teff_lit": 9350.0, "mh_lit": 0.21, "mass_lit": 2.07, "rv_lit": -24.5, "j_lit": 9.75, "h_lit": 9.71, "ks_lit": 9.70},
    {"canonical_target": "HD2685", "common_name": "HD 2685", "cadc_target": "HD 2685 b", "gaia_source_id": 4684205720883329920, "role": "SCIENCE", "subrole": "SCIENCE_TRANSITING_ORBITAL_TESS", "science_track": "GHOST_SKYVETO_ORBITAL", "nasa_host": "HD 2685", "orbital_campaign": True, "campaign_index": 128, "prefer_planet": "HD 2685 b", "n_target_epochs": 2, "panchromatic_bridge": False, "is_prior_bridge": False, "teff_lit": 6801.0, "mh_lit": 0.02, "mass_lit": 1.43, "rv_lit": 2.7, "j_lit": 8.85, "h_lit": 8.68, "ks_lit": 8.63},
    {"canonical_target": "LTT9779", "common_name": "LTT 9779", "cadc_target": "LTT 9779 b", "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_ORBITAL_USP", "science_track": "GHOST_SKYVETO_ORBITAL_BRIDGE", "nasa_host": "LTT 9779", "orbital_campaign": True, "campaign_index": 129, "prefer_planet": "LTT 9779 b", "n_target_epochs": 3, "panchromatic_bridge": True, "is_prior_bridge": True, "teff_lit": 5443.0, "mh_lit": 0.27, "mass_lit": 0.77, "rv_lit": 14.3, "j_lit": 8.43, "h_lit": 8.11, "ks_lit": 8.02},
    {"canonical_target": "MASCARA1", "common_name": "MASCARA-1", "cadc_target": "MASCARA-1", "gaia_source_id": 1744911763437512064, "role": "SCIENCE", "subrole": "SCIENCE_TRANSITING_QUADRATURE", "science_track": "GHOST_SKYVETO_COMB_TRANSIT", "nasa_host": "MASCARA-1", "orbital_campaign": False, "campaign_index": None, "n_target_epochs": 1, "panchromatic_bridge": False, "is_prior_bridge": False, "teff_lit": 7554.0, "mh_lit": 0.0, "mass_lit": 1.72, "rv_lit": 9.2, "j_lit": 7.89, "h_lit": 7.82, "ks_lit": 7.77, "n_exo_lit": 1, "trans_lit": True},
    {"canonical_target": "GD71", "common_name": "GD 71 (Control WD)", "cadc_target": "GD 71", "gaia_source_id": 3348071631670500736, "role": "CONTROL", "subrole": "CONTROL_DA_WHITE_DWARF", "science_track": "GHOST_SKYVETO_CONTROL", "nasa_host": "", "orbital_campaign": False, "campaign_index": None, "n_target_epochs": 1, "panchromatic_bridge": False, "is_prior_bridge": False, "teff_lit": 32700.0, "mh_lit": 0.0, "mass_lit": 0.59, "rv_lit": 26.0, "j_lit": 13.73, "h_lit": 13.89, "ks_lit": 14.12, "n_exo_lit": 0, "trans_lit": False},
    {"canonical_target": "NGC3268CE1", "common_name": "NGC 3268-cE1 (Control Extragalactic)", "cadc_target": "NGC3268-cE1", "gaia_source_id": None, "ra_lit": 157.5210, "dec_lit": -35.3420, "dist_lit": 3.5e7, "g_lit": 16.42, "role": "CONTROL", "subrole": "CONTROL_EXTRAGALACTIC_CE", "science_track": "GHOST_SKYVETO_CONTROL", "nasa_host": "", "orbital_campaign": False, "campaign_index": None, "n_target_epochs": 1, "panchromatic_bridge": False, "is_prior_bridge": False, "teff_lit": 4462.0, "mh_lit": -0.3, "mass_lit": 1.0, "rv_lit": 2800.0, "j_lit": 15.0, "h_lit": 14.4, "ks_lit": 14.2, "n_exo_lit": 0, "trans_lit": False},
]

# Stream C: 18 SPITZER_IRS targets (12 brand-new [4 <10pc, 6 exoplanet hosts, 2 hot controls] + 6 bridges)
SPITZER_SPECS: list[dict[str, Any]] = [
    {"canonical_target": "SIRIUS", "common_name": "Sirius (alpha CMa)", "reqkey": 7611392, "gaia_source_id": None, "ra_lit": 101.287155, "dec_lit": -16.716116, "dist_lit": 2.670, "g_lit": -1.46, "role": "SCIENCE", "subrole": "SCIENCE_10PC_STANDARD_IRS", "science_track": "SPITZER_IRS_10PC_THERMAL", "nasa_host": "", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 9940.0, "mh_lit": 0.50, "mass_lit": 2.06, "rv_lit": -5.5, "j_lit": -1.39, "h_lit": -1.39, "ks_lit": -1.35, "n_exo_lit": 0, "trans_lit": False},
    {"canonical_target": "FOMALHAUT", "common_name": "Fomalhaut (alpha PsA)", "reqkey": 6626816, "gaia_source_id": None, "ra_lit": 344.412693, "dec_lit": -29.622237, "dist_lit": 7.704, "g_lit": 1.16, "role": "SCIENCE", "subrole": "SCIENCE_10PC_DEBRIS_DISK", "science_track": "SPITZER_IRS_DEBRIS_VS_DYSON", "nasa_host": "", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 8590.0, "mh_lit": 0.0, "mass_lit": 1.92, "rv_lit": 6.5, "j_lit": 1.03, "h_lit": 0.99, "ks_lit": 0.94, "n_exo_lit": 0, "trans_lit": False},
    {"canonical_target": "HD38393", "common_name": "gamma Lep A (HD 38393)", "reqkey": 16014848, "gaia_source_id": 2964000159821218432, "role": "SCIENCE", "subrole": "SCIENCE_10PC_SOLAR_TYPE", "science_track": "SPITZER_IRS_10PC_THERMAL", "nasa_host": "", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 6350.0, "mh_lit": -0.05, "mass_lit": 1.23, "rv_lit": -9.0, "j_lit": 2.86, "h_lit": 2.55, "ks_lit": 2.51, "n_exo_lit": 0, "trans_lit": False},
    {"canonical_target": "HD151288", "common_name": "GJ 638 (HD 151288)", "reqkey": 16022272, "gaia_source_id": 1314438839310796800, "role": "SCIENCE", "subrole": "SCIENCE_10PC_KDWARF", "science_track": "SPITZER_IRS_10PC_THERMAL", "nasa_host": "", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 4200.0, "mh_lit": -0.1, "mass_lit": 0.65, "rv_lit": -32.1, "j_lit": 5.56, "h_lit": 4.92, "ks_lit": 4.74, "n_exo_lit": 0, "trans_lit": False},
    {"canonical_target": "GJ414A", "common_name": "GJ 414 A", "reqkey": 16008704, "gaia_source_id": 732857558276385664, "role": "SCIENCE", "subrole": "SCIENCE_EXOPLANET_IRS", "science_track": "SPITZER_IRS_EXOPLANET_THERMAL", "nasa_host": "GJ 414 A", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 4120.0, "mh_lit": 0.24, "mass_lit": 0.65, "rv_lit": -16.6, "j_lit": 5.76, "h_lit": 5.14, "ks_lit": 4.98},
    {"canonical_target": "HD177565", "common_name": "HD 177565", "reqkey": 16015104, "gaia_source_id": 6718894388002453120, "role": "SCIENCE", "subrole": "SCIENCE_EXOPLANET_IRS", "science_track": "SPITZER_IRS_EXOPLANET_THERMAL", "nasa_host": "HD 177565", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 5627.0, "mh_lit": 0.08, "mass_lit": 1.00, "rv_lit": 60.0, "j_lit": 4.92, "h_lit": 4.59, "ks_lit": 4.50},
    {"canonical_target": "HD189567", "common_name": "HD 189567", "reqkey": 16027136, "gaia_source_id": 6427244702486210816, "role": "SCIENCE", "subrole": "SCIENCE_EXOPLANET_IRS", "science_track": "SPITZER_IRS_EXOPLANET_THERMAL", "nasa_host": "HD 189567", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 5726.0, "mh_lit": -0.24, "mass_lit": 0.83, "rv_lit": -10.8, "j_lit": 4.86, "h_lit": 4.49, "ks_lit": 4.41},
    {"canonical_target": "HD3765", "common_name": "HD 3765", "reqkey": 16028160, "gaia_source_id": 369092520004831232, "role": "SCIENCE", "subrole": "SCIENCE_EXOPLANET_IRS", "science_track": "SPITZER_IRS_EXOPLANET_THERMAL", "nasa_host": "HD 3765", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 5027.0, "mh_lit": 0.14, "mass_lit": 0.85, "rv_lit": -63.3, "j_lit": 5.69, "h_lit": 5.27, "ks_lit": 5.16},
    {"canonical_target": "HD104067", "common_name": "HD 104067", "reqkey": 14728704, "gaia_source_id": 3494677900774838144, "role": "SCIENCE", "subrole": "SCIENCE_EXOPLANET_IRS", "science_track": "SPITZER_IRS_EXOPLANET_THERMAL", "nasa_host": "HD 104067", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 4956.0, "mh_lit": -0.06, "mass_lit": 0.79, "rv_lit": 14.9, "j_lit": 6.17, "h_lit": 5.71, "ks_lit": 5.60},
    {"canonical_target": "HD168009", "common_name": "HD 168009", "reqkey": 16028928, "gaia_source_id": 2115351387048328832, "role": "SCIENCE", "subrole": "SCIENCE_EXOPLANET_IRS", "science_track": "SPITZER_IRS_EXOPLANET_THERMAL", "nasa_host": "HD 168009", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 5808.0, "mh_lit": -0.01, "mass_lit": 0.99, "rv_lit": -64.5, "j_lit": 5.12, "h_lit": 4.81, "ks_lit": 4.74},
    {"canonical_target": "HD149757", "common_name": "zeta Oph (Control O9.5V)", "reqkey": 27582976, "gaia_source_id": 4337352305320149760, "role": "CONTROL", "subrole": "CONTROL_OSTAR_IRS", "science_track": "SPITZER_IRS_CONTROL", "nasa_host": "", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 34000.0, "mh_lit": 0.0, "mass_lit": 20.0, "rv_lit": -15.0, "j_lit": 2.47, "h_lit": 2.52, "ks_lit": 2.54, "n_exo_lit": 0, "trans_lit": False},
    {"canonical_target": "HD019356", "common_name": "Algol (Control B8V)", "reqkey": 16177920, "gaia_source_id": None, "ra_lit": 47.0422, "dec_lit": 40.9557, "dist_lit": 27.6, "g_lit": 2.12, "role": "CONTROL", "subrole": "CONTROL_BSTAR_IRS", "science_track": "SPITZER_IRS_CONTROL", "nasa_host": "", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 13000.0, "mh_lit": 0.0, "mass_lit": 3.17, "rv_lit": 4.0, "j_lit": 2.28, "h_lit": 2.12, "ks_lit": 2.02, "n_exo_lit": 0, "trans_lit": False},
    # 6 Panchromatic Bridges revisited at 5.2-37.9 um
    {"canonical_target": "TAUCET", "common_name": "tau Ceti", "reqkey": 4932352, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_10PC_IRS", "science_track": "SPITZER_IRS_BRIDGE", "nasa_host": "tau Cet", "is_prior_bridge": True, "panchromatic_bridge": True, "teff_lit": 5344.0, "mh_lit": -0.55, "mass_lit": 0.783, "rv_lit": -16.6, "j_lit": 2.15, "h_lit": 1.80, "ks_lit": 1.70},
    {"canonical_target": "HD115617", "common_name": "61 Vir", "reqkey": 15998976, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_10PC_DEBRIS_IRS", "science_track": "SPITZER_IRS_DEBRIS_BRIDGE", "nasa_host": "61 Vir", "is_prior_bridge": True, "panchromatic_bridge": True, "teff_lit": 5577.0, "mh_lit": -0.02, "mass_lit": 0.942, "rv_lit": -8.1, "j_lit": 3.33, "h_lit": 3.07, "ks_lit": 2.96},
    {"canonical_target": "HD69830", "common_name": "HD 69830 (Warm Silicate Belt)", "reqkey": 22341632, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_SILICATE_BELT", "science_track": "SPITZER_IRS_DEBRIS_BRIDGE", "nasa_host": "HD 69830", "is_prior_bridge": True, "panchromatic_bridge": True, "teff_lit": 5385.0, "mh_lit": -0.03, "mass_lit": 0.86, "rv_lit": 30.2, "j_lit": 4.59, "h_lit": 4.28, "ks_lit": 4.17},
    {"canonical_target": "HD10647", "common_name": "q1 Eri (HD 10647)", "reqkey": 16029952, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_DEBRIS_IRS", "science_track": "SPITZER_IRS_DEBRIS_BRIDGE", "nasa_host": "HD 10647", "is_prior_bridge": True, "panchromatic_bridge": True, "teff_lit": 6218.0, "mh_lit": -0.04, "mass_lit": 1.11, "rv_lit": 27.7, "j_lit": 4.79, "h_lit": 4.49, "ks_lit": 4.34},
    {"canonical_target": "HD40307", "common_name": "HD 40307", "reqkey": 16032000, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_MULTIPLANET_IRS", "science_track": "SPITZER_IRS_BRIDGE", "nasa_host": "HD 40307", "is_prior_bridge": True, "panchromatic_bridge": True, "teff_lit": 4956.0, "mh_lit": -0.31, "mass_lit": 0.77, "rv_lit": 31.3, "j_lit": 5.41, "h_lit": 4.97, "ks_lit": 4.79},
    {"canonical_target": "HR8799", "common_name": "HR 8799", "reqkey": 28889856, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_DEBRIS_IRS", "science_track": "SPITZER_IRS_DEBRIS_BRIDGE", "nasa_host": "HR 8799", "is_prior_bridge": True, "panchromatic_bridge": True, "teff_lit": 7430.0, "mh_lit": -0.47, "mass_lit": 1.47, "rv_lit": -12.6, "j_lit": 5.38, "h_lit": 5.28, "ks_lit": 5.24},
]


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            b = fh.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    c = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c)))) * 3600.0


def _urlopen_retry(req: urllib.request.Request, timeout_s: float = 45.0) -> bytes:
    last_err: Exception | None = None
    for att in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as r:
                return r.read()
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (att + 1))
    raise RuntimeError(f"HTTP failure {req.full_url}: {last_err}")


def tap_csv(url_base: str, query: str, param_key: str = "QUERY") -> list[dict[str, str]]:
    if param_key == "QUERY":
        params = {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query}
    elif param_key == "cmd":
        params = {"cmd": query, "format": "csv"}
    else:
        params = {param_key: query, "format": "csv"}
    url = f"{url_base}?{urllib.parse.urlencode(params)}"
    txt = _urlopen_retry(urllib.request.Request(url, headers={"User-Agent": "SETIsearch-D095/1.0"})).decode("utf-8", errors="replace")
    if txt.lstrip().startswith("<?xml"):
        raise RuntimeError(f"TAP XML error from {url_base}: {txt[:400]}")
    lines = [l for l in txt.splitlines() if not l.startswith("#")]
    return list(csv.DictReader(lines))


def head_content_length(url: str) -> int:
    last_err: Exception | None = None
    for att in range(4):
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "SETIsearch-D095/1.0"})
            with urllib.request.urlopen(req, timeout=30.0) as r:
                cl = r.headers.get("Content-Length")
                if cl and int(cl) > 0:
                    return int(cl)
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (att + 1))
    raise RuntimeError(f"HTTP HEAD failure {url}: {last_err}")


def _opt_float(val: Any, default: float = math.nan) -> float:
    try:
        v = float(val)
        return v if math.isfinite(v) else default
    except Exception:
        return default


def main() -> None:
    inp_dir = ROOT / "inputs_d095_v5_3"
    if inp_dir.exists():
        raise RuntimeError(f"Prospective hygiene violation: {inp_dir} already exists before Stage-1 lock!")

    arch_q = ROOT / "archives" / ARCHIVE_Q_NAME
    arch_t = ROOT / "archives" / ARCHIVE_T_NAME
    for zp, exp in ((arch_q, ARCHIVE_Q_SHA256), (arch_t, ARCHIVE_T_SHA256)):
        if not zp.exists() or sha256_file(zp) != exp:
            raise RuntimeError(f"Archive integrity check failed for {zp.name}")

    print("1. Extracting Archive T (D094) exclusion registry & Archive Q (D091) N>=4 metadata...", flush=True)
    with zipfile.ZipFile(arch_q, "r") as zq:
        q_bundle_sha = sha256_bytes(zq.read(ARCHIVE_Q_BUNDLE_MEMBER))

    with zipfile.ZipFile(arch_t, "r") as zt:
        t_bundle_sha = sha256_bytes(zt.read(ARCHIVE_T_BUNDLE_MEMBER))
        pe94 = json.loads(zt.read("PRIOR_EXCLUSION_VERIFICATION.json").decode("utf-8"))
        sum94 = json.loads(zt.read("results/SUMMARY.json").decode("utf-8"))
        coh94 = list(csv.DictReader(zt.read("FROZEN_COHORT_D094.csv").decode("utf-8").splitlines()))
        u373_rows = list(csv.DictReader(zt.read("results/UNIFIED_PANCHROMATIC_V5_2_SYNTHESIS_373STARS.csv").decode("utf-8").splitlines()))
        br41_rows = list(csv.DictReader(zt.read("results/PANCHROMATIC_BRIDGE_41STARS_V52.csv").decode("utf-8").splitlines()))
        comb_u94 = list(csv.DictReader(zt.read("results/ALLSKY_COMB_V4_1_UNIFIED_D079_D094.csv").decode("utf-8").splitlines()))
        comb_c94 = list(csv.DictReader(zt.read("results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D094.csv").decode("utf-8").splitlines()))

    u373_map = {r["star"]: r for r in u373_rows}
    br41_set = {r["star"] for r in br41_rows}
    prior_coords: list[dict[str, Any]] = list(pe94["excluded_targets_coordinate_registry"])
    seen_94: set[str] = set()
    for r in coh94:
        st = r["canonical_target"]
        if r["is_prior_bridge"] != "True" and st not in seen_94:
            seen_94.add(st)
            prior_coords.append({"label": f"{st}(D094)", "ra_deg": float(r["s_ra"]), "dec_deg": float(r["s_dec"])})
    excluded_dp_ids: set[str] = set(pe94["excluded_dp_ids"]) | {r["dp_id"] for r in coh94} | set(FORMAT_CHECK_EXCLUDED_DP_IDS)

    syn94 = sum94["unified_373star_panchromatic_v5_2_synthesis"]
    prior_snap = {
        "schema": "D095_PRIOR_V5_2_PHASES_SNAPSHOT",
        "prior_phases": "D079-D094",
        "source_archive_t_name": ARCHIVE_T_NAME,
        "source_archive_t_sha256": ARCHIVE_T_SHA256,
        "source_archive_t_bundle_member": ARCHIVE_T_BUNDLE_MEMBER,
        "source_archive_t_bundle_sha256": t_bundle_sha,
        "source_archive_q_name": ARCHIVE_Q_NAME,
        "source_archive_q_sha256": ARCHIVE_Q_SHA256,
        "source_archive_q_bundle_member": ARCHIVE_Q_BUNDLE_MEMBER,
        "source_archive_q_bundle_sha256": q_bundle_sha,
        "prior_unique_stars_count": len(u373_rows),
        "prior_within_10pc_count": syn94["within_10pc_unique_stars"],
        "prior_total_exposures_count": syn94["total_exposures_d079_d094"],
        "prior_cumulative_integration_hours": syn94["total_integration_hours_d079_d094"],
        "prior_calibration_trials_count": syn94["total_calibration_trials_d079_d094"],
        "prior_v2_false_alarms_eliminated_total": syn94["v2_false_alarms_eliminated_total"],
        "prior_cumulative_orbital_campaigns_count": syn94["cumulative_orbital_campaigns"],
        "prior_panchromatic_bridge_stars_count": len(br41_set),
        "prior_panchromatic_bridge_cells_count": syn94["panchromatic_bridge_cells_total"],
        "d094_summary_headline": sum94,
        "prior_unified_373_rows": u373_rows,
        "prior_bridge_41_rows": br41_rows,
        "prior_allsky_comb_unified_rows": comb_u94,
        "prior_allsky_comb_candidate_rows": comb_c94,
    }

    print("2. Querying ESA Gaia DR3, NOIRLab APOGEE2, SDSS apogeeVisit, NASA Exoplanet Archive, CADC GHOST, and IRSA Spitzer IRS...", flush=True)
    all_gids = sorted({int(s["gaia_source_id"]) for s in (APOGEE2_SPECS + GHOST_SPECS + SPITZER_SPECS) if s.get("gaia_source_id")})
    gq = (
        "SELECT source_id, ra, dec, parallax, pmra, pmdec, phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag, "
        f"radial_velocity, teff_gspphot, mh_gspphot FROM gaiadr3.gaia_source WHERE source_id IN ({','.join(map(str, all_gids))})"
    )
    gaia_map = {int(r["source_id"]): r for r in tap_csv("https://gea.esac.esa.int/tap-server/tap/sync", gq)}
    if len(gaia_map) != len(all_gids):
        raise RuntimeError(f"Gaia DR3 missing IDs: {set(all_gids) - set(gaia_map)}")

    apo_ids_sql = ",".join(f"'{s['apogee_id']}'" for s in APOGEE2_SPECS)
    aq = (
        "SELECT apogee_id, telescope, field, ra, dec, jmag, hmag, ksmag, nvis, teff, rv_teff, m_h, fe_h, hrv, snr "
        f"FROM sdss_dr17.apogee2_allstar WHERE apogee_id IN ({apo_ids_sql})"
    )
    apo_map = {(r["apogee_id"], r["telescope"], r["field"]): r for r in tap_csv("https://datalab.noirlab.edu/tap/sync", aq)}

    # Query individual APOGEE visit MJDs for orbital phase span verification of Kepler campaigns
    av_sql = f"SELECT apogee_id, mjd, jd, snr, vhelio FROM apogeeVisit WHERE apogee_id IN ({apo_ids_sql})"
    av_rows = tap_csv("https://skyserver.sdss.org/dr17/SkyServerWS/SearchTools/SqlSearch", av_sql, param_key="cmd")
    av_by_id: dict[str, list[dict[str, str]]] = {}
    for vr in av_rows:
        av_by_id.setdefault(vr["apogee_id"], []).append(vr)

    hosts = sorted({s["nasa_host"] for s in (APOGEE2_SPECS + GHOST_SPECS + SPITZER_SPECS) if s.get("nasa_host")})
    nq = (
        "SELECT pl_name, hostname, pl_orbper, pl_tranmid, pl_orbeccen, st_mass, tran_flag "
        f"FROM pscomppars WHERE hostname IN ({','.join(chr(39) + h + chr(39) for h in hosts)})"
    )
    nasa_rows = tap_csv("https://exoplanetarchive.ipac.caltech.edu/TAP/sync", nq, param_key="query")
    nasa_by_host: dict[str, list[dict[str, str]]] = {}
    for nr in nasa_rows:
        nasa_by_host.setdefault(nr["hostname"], []).append(nr)

    # CADC GHOST ObsCore metadata
    cadc_tgts_sql = ",".join(f"'{s['cadc_target']}'" for s in GHOST_SPECS)
    cq = (
        "SELECT target_name, obs_id, s_ra, s_dec, t_min, t_exptime, obs_publisher_did, obs_release_date "
        f"FROM ivoa.ObsCore WHERE instrument_name='GHOST' AND target_name IN ({cadc_tgts_sql}) "
        "AND obs_release_date < '2026-11-21' ORDER BY target_name, obs_id"
    )
    ghost_raw_rows = tap_csv("https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/argus/sync", cq)

    # IRSA Spitzer IRS irs_enhv211 (tn = 1 primary targets)
    reqs_sql = ",".join(str(s["reqkey"]) for s in SPITZER_SPECS)
    iq = (
        "SELECT reqkey, tn, object, ra, dec, date_obs, wave_min, wave_max, irac8, mips24, mips24_irac8, heritagefilename, progid "
        f"FROM irs_enhv211 WHERE reqkey IN ({reqs_sql}) AND tn = 1"
    )
    irs_by_req = {int(r["reqkey"]): r for r in tap_csv("https://irsa.ipac.caltech.edu/TAP/sync", iq)}

    def resolve_star_meta(spec: dict[str, Any]) -> dict[str, Any]:
        st = spec["canonical_target"]
        gid = spec.get("gaia_source_id")
        if st in u373_map and spec.get("is_prior_bridge") and gid is None:
            u = u373_map[st]
            preg = next(r for r in prior_coords if r["label"].split("(")[0] == st)
            return {
                "gaia_source_id": 0,
                "ra": float(preg["ra_deg"]),
                "dec": float(preg["dec_deg"]),
                "pmra": 0.0,
                "pmdec": 0.0,
                "dist_pc": float(u["dist_pc"]),
                "g_mag": _opt_float(u.get("phot_g_mag"), math.nan),
                "bp_mag": math.nan,
                "rp_mag": math.nan,
                "j_mag": _opt_float(u.get("j_mag"), spec["j_lit"]),
                "h_mag": _opt_float(u.get("h_mag"), spec["h_lit"]),
                "ks_mag": _opt_float(u.get("ks_mag"), spec["ks_lit"]),
                "teff_k": _opt_float(u.get("teff_k"), spec["teff_lit"]),
                "mh_dex": spec["mh_lit"],
                "rv_kms": spec["rv_lit"],
                "mass_msun": spec["mass_lit"],
            }
        if gid and int(gid) in gaia_map:
            g = gaia_map[int(gid)]
            plx = _opt_float(g.get("parallax"), math.nan)
            dist_pc = float(spec["dist_lit"]) if spec.get("dist_lit") else (1000.0 / plx)
            return {
                "gaia_source_id": int(gid),
                "ra": float(g["ra"]),
                "dec": float(g["dec"]),
                "pmra": _opt_float(g.get("pmra"), 0.0),
                "pmdec": _opt_float(g.get("pmdec"), 0.0),
                "dist_pc": float(dist_pc),
                "g_mag": _opt_float(g.get("phot_g_mean_mag"), spec.get("g_lit", math.nan)),
                "bp_mag": _opt_float(g.get("phot_bp_mean_mag"), math.nan),
                "rp_mag": _opt_float(g.get("phot_rp_mean_mag"), math.nan),
                "j_mag": float(spec["j_lit"]),
                "h_mag": float(spec["h_lit"]),
                "ks_mag": float(spec["ks_lit"]),
                "teff_k": float(spec["teff_lit"]) if st in ("GD71", "MASCARA1", "WASP178", "2M23032370", "2M01452047", "HD149757", "HD177565", "GJ3801") else _opt_float(g.get("teff_gspphot"), spec["teff_lit"]),
                "mh_dex": _opt_float(g.get("mh_gspphot"), spec["mh_lit"]),
                "rv_kms": _opt_float(g.get("radial_velocity"), spec["rv_lit"]),
                "mass_msun": float(spec["mass_lit"]),
            }
        return {
            "gaia_source_id": 0,
            "ra": float(spec["ra_lit"]),
            "dec": float(spec["dec_lit"]),
            "pmra": 0.0,
            "pmdec": 0.0,
            "dist_pc": float(spec["dist_lit"]),
            "g_mag": float(spec.get("g_lit", math.nan)),
            "bp_mag": math.nan,
            "rp_mag": math.nan,
            "j_mag": float(spec["j_lit"]),
            "h_mag": float(spec["h_lit"]),
            "ks_mag": float(spec["ks_lit"]),
            "teff_k": float(spec["teff_lit"]),
            "mh_dex": float(spec["mh_lit"]),
            "rv_kms": float(spec["rv_lit"]),
            "mass_msun": float(spec["mass_lit"]),
        }

    cohort_rows: list[dict[str, Any]] = []
    orbital_campaigns: dict[str, Any] = {}
    unique_new_coords: dict[str, tuple[str, float, float]] = {}

    def append_cohort_row(
        inst: str, spec: dict[str, Any], m: dict[str, Any], epoch_rank: int, dp_id: str,
        grating: str, rp: float, mjd_obs: float, t_exptime: float,
        phase_window: str, signed_phase: float, orb_rv: float,
        f1_id: str, f1_rel: str, f1_url: str, f1_bytes: int,
    ) -> None:
        sync = det.compute_multievent_sync_v51(m["ra"], m["dec"], m["dist_pc"], mjd_obs)
        n_pl = spec.get("n_exo_lit")
        has_tr = spec.get("trans_lit")
        if n_pl is None:
            plist = nasa_by_host.get(spec.get("nasa_host", ""), [])
            n_pl = len(plist)
            has_tr = any(str(p.get("tran_flag", "0")) == "1" for p in plist)
        cohort_rows.append({
            "instrument": inst,
            "canonical_target": spec["canonical_target"],
            "common_name": spec["common_name"],
            "role": spec["role"],
            "subrole": spec["subrole"],
            "science_track": spec["science_track"],
            "panchromatic_bridge": bool(spec.get("panchromatic_bridge", False)),
            "is_prior_bridge": bool(spec.get("is_prior_bridge", False)),
            "gaia_source_id": m["gaia_source_id"],
            "s_ra": round(m["ra"], 6),
            "s_dec": round(m["dec"], 6),
            "pmra_mas_yr": round(m["pmra"], 3),
            "pmdec_mas_yr": round(m["pmdec"], 3),
            "dist_pc": round(m["dist_pc"], 5),
            "within_10pc": bool(m["dist_pc"] < 10.0),
            "phot_g_mag": "" if not math.isfinite(m["g_mag"]) else round(m["g_mag"], 4),
            "phot_bp_mag": "" if not math.isfinite(m["bp_mag"]) else round(m["bp_mag"], 4),
            "phot_rp_mag": "" if not math.isfinite(m["rp_mag"]) else round(m["rp_mag"], 4),
            "j_mag": round(m["j_mag"], 3),
            "h_mag": round(m["h_mag"], 3),
            "ks_mag": round(m["ks_mag"], 3),
            "teff_k": round(m["teff_k"], 1),
            "mh_dex": round(m["mh_dex"], 3),
            "stellar_mass_msun": round(m["mass_msun"], 3),
            "prior_rv_kms": round(m["rv_kms"], 4),
            "n_exoplanets": int(n_pl),
            "has_transiting_planet": bool(has_tr),
            "ecliptic_lat_deg": round(sync["ecliptic_lat_deg"], 5),
            "sn1987a_dt_days": round(sync["sn1987a_dt_days"], 3),
            "gw170817_dt_days": round(sync["gw170817_dt_days"], 3),
            "sn2023ixf_dt_days": round(sync["sn2023ixf_dt_days"], 3),
            "ppo_align_score": 1.0,
            "epoch_rank": int(epoch_rank),
            "dp_id": dp_id,
            "grating": grating,
            "resolving_power": float(rp),
            "mjd_obs": round(mjd_obs, 6),
            "t_exptime": round(t_exptime, 3),
            "phase_window": phase_window,
            "signed_phase": round(signed_phase, 6),
            "planet_orbital_rv_kms": round(orb_rv, 4),
            "f1_id": f1_id,
            "f1_rel": f1_rel,
            "f1_url": f1_url,
            "f1_bytes": int(f1_bytes),
            "total_bytes": int(f1_bytes),
        })
        if not spec.get("is_prior_bridge"):
            unique_new_coords[spec["canonical_target"]] = (inst, m["ra"], m["dec"])

    # --- Stream A: SDSS APOGEE-2 ---
    print("3. Selecting & HEAD-checking Stream A (SDSS APOGEE-2, 10 targets / 4 Kepler campaigns)...", flush=True)
    for spec in APOGEE2_SPECS:
        st = spec["canonical_target"]
        m = resolve_star_meta(spec)
        aid, tel, fld = spec["apogee_id"], spec["telescope"], spec["field"]
        ar = apo_map[(aid, tel, fld)]
        for k_in, k_out in (("hmag", "h_mag"), ("jmag", "j_mag"), ("ksmag", "ks_mag"), ("teff", "teff_k"), ("hrv", "rv_kms")):
            v = _opt_float(ar.get(k_in))
            if math.isfinite(v) and (k_in != "teff" or v > 500.0):
                m[k_out] = v
        fname = f"apStar-dr17-{aid}.fits"
        furl = f"https://data.sdss.org/sas/dr17/apogee/spectro/redux/dr17/stars/{tel}/{fld}/{fname}"
        fbytes = head_content_length(furl)
        dp_id = f"APOGEE2.{tel}.{fld}.{aid}"
        if dp_id in excluded_dp_ids:
            raise RuntimeError(f"Duplicate APOGEE dp_id: {dp_id}")
        vis_list = av_by_id.get(aid, [])
        mjds_v = sorted(float(v["mjd"]) for v in vis_list if v.get("mjd"))
        mjd_rep = mjds_v[len(mjds_v) // 2] if mjds_v else 58000.0
        nv = int(ar["nvis"])
        append_cohort_row(
            "SDSS_APOGEE2", spec, m, 1, dp_id, f"APOGEE2_H_NV{nv}", 22500.0,
            mjd_rep, float(nv) * 500.0, "NONE", 0.0, 0.0,
            fname[:-5], f"SDSS_APOGEE2/{st}/{fname}", furl, fbytes,
        )
        if spec.get("orbital_campaign"):
            plist = nasa_by_host.get(spec["nasa_host"], [])
            tp = next((p for p in plist if p["pl_name"] == spec.get("prefer_planet")), plist[0])
            p_d = float(tp["pl_orbper"])
            t0_b = float(tp["pl_tranmid"])
            ecc_v = _opt_float(tp.get("pl_orbeccen"), 0.0)
            st_mass = _opt_float(tp.get("st_mass"), m["mass_msun"])
            m["mass_msun"] = st_mass
            kp = det.compute_keplerian_kp_kms(st_mass, p_d, ecc=ecc_v)
            exps_k = []
            for vi, vr in enumerate(sorted(vis_list, key=lambda x: float(x["jd"])), 1):
                s_ph, o_rv = det.compute_planet_orbital_rv_kms(float(vr["jd"]), t0_b, p_d, kp)
                exps_k.append({
                    "dp_id": f"{dp_id}.V{vi:02d}",
                    "mjd_obs": round(float(vr["mjd"]), 6),
                    "bjd_tdb_est": round(float(vr["jd"]), 6),
                    "signed_phase": round(s_ph, 6),
                    "phase_window": "IN_WINDOW" if abs(o_rv) > 0.4 * kp else "OUT_OF_WINDOW",
                    "planet_orbital_rv_kms": round(o_rv, 4),
                    "ppo_align_score": 1.0,
                })
            dvs = [e["planet_orbital_rv_kms"] for e in exps_k]
            dv_span = max(dvs) - min(dvs)
            assert dv_span >= 5.0, f"{st}: APOGEE orbital dv_span={dv_span} < 5.0 km/s"
            orbital_campaigns[st] = {
                "campaign_index": int(spec["campaign_index"]),
                "canonical_target": st,
                "common_name": spec["common_name"],
                "instrument": "SDSS_APOGEE2",
                "role": spec["role"],
                "null_orbital": False,
                "planet_name": tp["pl_name"],
                "n_planets_in_system": len(plist),
                "stellar_mass_msun": round(st_mass, 3),
                "orb_per_days": p_d,
                "orb_t0_bjd": t0_b,
                "orb_ecc": ecc_v,
                "kp_kms": round(kp, 3),
                "orbital_dv_span_kms": round(dv_span, 3),
                "n_epochs": len(exps_k),
                "exposures": exps_k,
            }

    # --- Stream B: GEMINI_GHOST (paired BLUE + RED DRAGONS FITS) ---
    print("4. Selecting & HEAD-checking Stream B (GEMINI_GHOST, 7 targets paired BLUE+RED DRAGONS)...", flush=True)
    ghost_by_tgt: dict[str, list[dict[str, str]]] = {}
    for r in ghost_raw_rows:
        ghost_by_tgt.setdefault(r["target_name"], []).append(r)

    def _resolve_datalink_fits(pubdid: str) -> str | None:
        dl = "https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/caom2ops/datalink?ID=" + urllib.parse.quote(pubdid, safe="")
        xml = _urlopen_retry(urllib.request.Request(dl, headers={"User-Agent": "SETIsearch-D095/1.0"}), timeout_s=20.0).decode("utf-8", errors="replace")
        fus = [u for u in re.findall(r'https://[^\s<>"]+', xml) if "raven/files" in u and u.endswith("_dragons.fits")]
        return fus[0] if fus else None

    for spec in GHOST_SPECS:
        st = spec["canonical_target"]
        m = resolve_star_meta(spec)
        rows_t = ghost_by_tgt.get(spec["cadc_target"], [])
        roots_meta: dict[str, tuple[float, float]] = {}
        blue_pub: dict[str, str] = {}
        red_pub: dict[str, str] = {}
        for r in rows_t:
            mt_id = re.search(r'(S20\d{6}S\d{4})', r["obs_publisher_did"]) or re.search(r'(S20\d{6}S\d{4})', r["obs_id"])
            if not mt_id:
                continue
            rt = mt_id.group(1)
            if r.get("t_min"):
                roots_meta[rt] = (float(r["t_min"]), _opt_float(r.get("t_exptime"), 180.0))
            if "BLUE001-DRAGONS" in r["obs_id"]:
                blue_pub[rt] = r["obs_publisher_did"]
            elif "RED001-DRAGONS" in r["obs_id"]:
                red_pub[rt] = r["obs_publisher_did"]
        paired_roots = sorted(rt for rt in (set(blue_pub) & set(red_pub)) if rt in roots_meta)
        assert len(paired_roots) >= int(spec["n_target_epochs"]), f"{st}: only {len(paired_roots)} paired B+R DRAGONS roots"

        n_req = int(spec["n_target_epochs"])
        p_ref: tuple[str, float, float, float, float] | None = None
        if spec.get("orbital_campaign"):
            plist = nasa_by_host.get(spec["nasa_host"], [])
            tp = next((p for p in plist if p["pl_name"] == spec.get("prefer_planet")), plist[0])
            p_d, t0_b = float(tp["pl_orbper"]), float(tp["pl_tranmid"])
            ecc_v = _opt_float(tp.get("pl_orbeccen"), 0.0)
            st_mass = _opt_float(tp.get("st_mass"), m["mass_msun"])
            m["mass_msun"] = st_mass
            kp = det.compute_keplerian_kp_kms(st_mass, p_d, ecc=ecc_v)
            p_ref = (tp["pl_name"], p_d, t0_b, ecc_v, kp)

        # Pick widest baseline or widest orbital velocity span
        if n_req == 3 and p_ref is not None:
            rt_sorted = sorted(paired_roots, key=lambda rt: roots_meta[rt][0])
            # Evaluate subsampled grid up to 15 roots evenly spaced if pool is large
            if len(rt_sorted) > 15:
                idxs = sorted({int(round(i * (len(rt_sorted) - 1) / 14)) for i in range(15)})
                pool_r = [rt_sorted[i] for i in idxs]
            else:
                pool_r = rt_sorted
            best_t = None
            for a, b, c in itertools.combinations(pool_r, 3):
                dvs = [det.compute_planet_orbital_rv_kms(roots_meta[x][0] + 2400000.5, p_ref[2], p_ref[1], p_ref[4])[1] for x in (a, b, c)]
                sp = max(dvs) - min(dvs)
                if best_t is None or sp > best_t[0]:
                    best_t = (sp, [a, b, c])
            assert best_t and best_t[0] >= 5.0, f"{st}: GHOST triplet orbital span < 5 km/s"
            chosen_roots = sorted(best_t[1], key=lambda rt: roots_meta[rt][0])
        elif p_ref is not None:
            best_p = None
            for a, b in itertools.combinations(paired_roots, 2):
                dva = det.compute_planet_orbital_rv_kms(roots_meta[a][0] + 2400000.5, p_ref[2], p_ref[1], p_ref[4])[1]
                dvb = det.compute_planet_orbital_rv_kms(roots_meta[b][0] + 2400000.5, p_ref[2], p_ref[1], p_ref[4])[1]
                sp = abs(dvb - dva)
                if best_p is None or sp > best_p[0]:
                    best_p = (sp, [a, b])
            assert best_p and best_p[0] >= 5.0, f"{st}: GHOST pair orbital span < 5 km/s"
            chosen_roots = sorted(best_p[1], key=lambda rt: roots_meta[rt][0])
        else:
            rt_sorted = sorted(paired_roots, key=lambda rt: roots_meta[rt][0])
            if n_req == 1:
                chosen_roots = [rt_sorted[0]]
            elif n_req == 2:
                chosen_roots = [rt_sorted[0], rt_sorted[-1]]
            else:
                chosen_roots = [rt_sorted[0], rt_sorted[len(rt_sorted) // 2], rt_sorted[-1]]

        camp_exps = []
        for erank, rt in enumerate(chosen_roots, 1):
            mjd_v, expt_v = roots_meta[rt]
            if p_ref is not None:
                s_ph, o_rv = det.compute_planet_orbital_rv_kms(mjd_v + 2400000.5, p_ref[2], p_ref[1], p_ref[4])
                ph_win = "IN_WINDOW" if abs(o_rv) > 0.4 * p_ref[4] else "OUT_OF_WINDOW"
            else:
                s_ph, o_rv, ph_win = 0.0, 0.0, "NONE"

            for arm_lbl, pub_d in (("BLUE", blue_pub[rt]), ("RED", red_pub[rt])):
                furl = _resolve_datalink_fits(pub_d)
                assert furl is not None, f"Missing DRAGONS URL for {st} {rt} {arm_lbl}"
                fbytes = head_content_length(furl)
                fname = furl.split("/")[-1]
                dp_id = f"GHOST.{rt}_{arm_lbl.lower()}001_dragons"
                if dp_id in excluded_dp_ids:
                    raise RuntimeError(f"Duplicate GHOST dp_id: {dp_id}")
                append_cohort_row(
                    "GEMINI_GHOST", spec, m, erank, dp_id, f"GHOST_{arm_lbl}", 56000.0, mjd_v, expt_v,
                    ph_win, s_ph, o_rv, fname[:-5], f"GEMINI_GHOST/{st}/{fname}", furl, fbytes,
                )
            if p_ref is not None:
                camp_exps.append({
                    "dp_id": f"GHOST.{rt}",
                    "mjd_obs": round(mjd_v, 6),
                    "bjd_tdb_est": round(mjd_v + 2400000.5, 6),
                    "signed_phase": round(s_ph, 6),
                    "phase_window": ph_win,
                    "planet_orbital_rv_kms": round(o_rv, 4),
                    "ppo_align_score": 1.0,
                })
        if p_ref is not None:
            dvs = [e["planet_orbital_rv_kms"] for e in camp_exps]
            orbital_campaigns[st] = {
                "campaign_index": int(spec["campaign_index"]),
                "canonical_target": st,
                "common_name": spec["common_name"],
                "instrument": "GEMINI_GHOST",
                "role": spec["role"],
                "null_orbital": False,
                "planet_name": p_ref[0],
                "n_planets_in_system": len(nasa_by_host.get(spec["nasa_host"], [])),
                "stellar_mass_msun": round(m["mass_msun"], 3),
                "orb_per_days": p_ref[1],
                "orb_t0_bjd": p_ref[2],
                "orb_ecc": p_ref[3],
                "kp_kms": round(p_ref[4], 3),
                "orbital_dv_span_kms": round(max(dvs) - min(dvs), 3),
                "n_epochs": len(camp_exps),
                "exposures": camp_exps,
            }

    # --- Stream C: SPITZER_IRS (18 Enhanced IRS 5.2-37.9 um .tbl spectra) ---
    print("5. Selecting & HEAD-checking Stream C (SPITZER_IRS, 18 targets)...", flush=True)
    for spec in SPITZER_SPECS:
        st = spec["canonical_target"]
        rk = int(spec["reqkey"])
        ir = irs_by_req[rk]
        m = resolve_star_meta(spec)
        hpath = ir["heritagefilename"].strip()
        rel_proc = hpath.split("/proc/")[-1]
        fname = rel_proc.split("/")[-1]
        furl = f"https://irsa.ipac.caltech.edu/data/SPITZER/Enhanced/IRS/spectra/{rel_proc}"
        fbytes = head_content_length(furl)
        # Convert YYYY-MM-DD HH:MM:SS date_obs to MJD
        t_iso = ir["date_obs"].strip().replace(" ", "T")
        t_dt = dt.datetime.fromisoformat(t_iso).replace(tzinfo=dt.timezone.utc)
        mjd_v = (t_dt - dt.datetime(1858, 11, 17, 0, 0, 0, tzinfo=dt.timezone.utc)).total_seconds() / 86400.0
        dp_id = f"SPITZER_IRS.r{rk}"
        if dp_id in excluded_dp_ids:
            raise RuntimeError(f"Duplicate Spitzer dp_id: {dp_id}")
        append_cohort_row(
            "SPITZER_IRS", spec, m, 1, dp_id, "SPITZER_IRS_SL_LL", 100.0, mjd_v, 120.0,
            "NONE", 0.0, 0.0, fname[:-4], f"SPITZER_IRS/{st}/{fname}", furl, fbytes,
        )

    # --- Verify 5-arcmin exclusion, zero dp_id overlap & hard caps ---
    print("6. Verifying 5-arcmin prior exclusion, dp_id disjointness, and caps...", flush=True)
    star_seps: list[dict[str, Any]] = []
    min_brand_new_sep = 1e18
    for st, (inst, ra, dec) in sorted(unique_new_coords.items()):
        best_sep, best_lbl = 1e18, ""
        for p in prior_coords:
            sp = sep_arcsec(ra, dec, float(p["ra_deg"]), float(p["dec_deg"]))
            if sp < best_sep:
                best_sep, best_lbl = sp, str(p["label"])
        if best_sep < 300.0:
            raise RuntimeError(f"5-arcmin exclusion FAILED for {st}: {best_sep:.2f}\" from {best_lbl}")
        min_brand_new_sep = min(min_brand_new_sep, best_sep)
        star_seps.append({
            "canonical_target": st,
            "instrument": inst,
            "ra_deg": round(ra, 6),
            "dec_deg": round(dec, 6),
            "nearest_prior_target": best_lbl,
            "separation_arcsec": round(best_sep, 2),
        })

    intra_seps = [sep_arcsec(a[1], a[2], b[1], b[2]) for (_, a), (_, b) in itertools.combinations(sorted(unique_new_coords.items()), 2)]
    min_intra_sep = min(intra_seps) if intra_seps else 999999.0
    if min_intra_sep < 300.0:
        raise RuntimeError(f"Intra-D095 collision: {min_intra_sep:.2f}\" < 300\"")

    tot_bytes = sum(r["f1_bytes"] for r in cohort_rows)
    tot_mib = tot_bytes / 1048576.0
    if tot_mib > 125.0:
        raise RuntimeError(f"Projected download {tot_mib:.2f} MiB exceeds 125.0 MiB hard cap!")

    new_10pc = sum(1 for st in unique_new_coords if next(r["within_10pc"] for r in cohort_rows if r["canonical_target"] == st))
    new_ctrl = sum(1 for st in unique_new_coords if next(r["role"] == "CONTROL" for r in cohort_rows if r["canonical_target"] == st))
    all_stars_d095 = sorted({r["canonical_target"] for r in cohort_rows})
    prior_bridges_d095 = sorted({r["canonical_target"] for r in cohort_rows if r["is_prior_bridge"]})

    (WS / "PRIOR_V5_2_PHASES_SNAPSHOT.json").write_text(json.dumps(prior_snap, indent=2) + "\n", encoding="utf-8")

    prior_excl = {
        "schema": "D095_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D095",
        "verified_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prior_phases_covered": "C001-C037 + D001-D094",
        "n_prior_excluded_coords": len(prior_coords),
        "n_prior_excluded_dp_ids": len(excluded_dp_ids),
        "d095_total_stars": len(all_stars_d095),
        "d095_brand_new_unique_stars": len(unique_new_coords),
        "d095_prior_bridge_stars": len(prior_bridges_d095),
        "d095_control_stars": new_ctrl,
        "d095_brand_new_within_10pc": new_10pc,
        "d095_total_input_files": len(cohort_rows),
        "d095_projected_download_bytes": tot_bytes,
        "d095_projected_download_mib": round(tot_mib, 3),
        "d095_dp_id_overlap_count": 0,
        "min_brand_new_sky_separation_arcsec": round(min_brand_new_sep, 2),
        "min_intra_d095_separation_arcsec": round(min_intra_sep, 2),
        "star_separation_verification": star_seps,
        "excluded_dp_ids": sorted(excluded_dp_ids),
        "excluded_targets_coordinate_registry": prior_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(prior_excl, indent=2) + "\n", encoding="utf-8")

    coh_fields = list(cohort_rows[0].keys())
    with (WS / "FROZEN_COHORT_D095.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=coh_fields)
        w.writeheader()
        w.writerows(cohort_rows)

    orb_doc = {
        "schema": "D095_ORBITAL_CAMPAIGNS_AND_KINEMATICS",
        "phase_id": "D095",
        "campaign_range": "#126-#133",
        "n_campaigns": len(orbital_campaigns),
        "campaigns": orbital_campaigns,
    }
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_doc, indent=2) + "\n", encoding="utf-8")

    locked_names = [
        "v5_3_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D095.csv",
        "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "PRIOR_V5_2_PHASES_SNAPSHOT.json",
    ]
    hashes = {fn: sha256_file(WS / fn) for fn in locked_names}
    locked_utc = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    method_lock = {
        "schema": "D095_STAGE1_PROSPECTIVE_METHOD_LOCK",
        "phase_id": "D095",
        "detector_name": det.DETECTOR_NAME,
        "locked_utc": locked_utc,
        "retroactive_reused_bundles": [
            {
                "phase_id": "D091",
                "archive_name": ARCHIVE_Q_NAME,
                "archive_sha256": ARCHIVE_Q_SHA256,
                "bundle_member": ARCHIVE_Q_BUNDLE_MEMBER,
                "bundle_sha256": q_bundle_sha,
                "purpose": "Retroactive V5.3 DRIFT_V53_CURVED_AND_PERIODIC (N>=4) across D091 multi-night stars",
            },
            {
                "phase_id": "D094",
                "archive_name": ARCHIVE_T_NAME,
                "archive_sha256": ARCHIVE_T_SHA256,
                "bundle_member": ARCHIVE_T_BUNDLE_MEMBER,
                "bundle_sha256": t_bundle_sha,
                "purpose": "Prior 373-star synthesis, 41 bridges, 432 excluded coords, 2665 dp_ids, 424-stack comb ledger, plus retroactive D094 N>=4 APOGEE-2 drift",
            },
        ],
        "locked_v53_parameters": det.BASE_V5_3_CONFIG,
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
    (WS / "METHOD_LOCK.json").write_text(json.dumps(method_lock, indent=2) + "\n", encoding="utf-8")

    lock_receipt = {
        "schema": "D095_STAGE1_LOCK_RECEIPT",
        "phase_id": "D095",
        "locked_utc": locked_utc,
        "inputs_d095_v5_3_exists": False,
        "method_lock_sha256": sha256_file(WS / "METHOD_LOCK.json"),
        "frozen_cohort_sha256": hashes["FROZEN_COHORT_D095.csv"],
        "projected_download_mib": round(tot_mib, 3),
        "n_input_files": len(cohort_rows),
        "n_unique_new_stars": len(unique_new_coords),
        "n_prior_bridge_stars": len(prior_bridges_d095),
        "n_orbital_campaigns": len(orbital_campaigns),
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lock_receipt, indent=2) + "\n", encoding="utf-8")

    print(
        f"STAGE-1 SEALED: {len(all_stars_d095)} D095 stars ({len(unique_new_coords)} brand-new, "
        f"{len(prior_bridges_d095)} prior bridges), {len(cohort_rows)} input files ({tot_mib:.2f} MiB), "
        f"min_prior_sep={min_brand_new_sep:.2f}\", {len(orbital_campaigns)} orbital campaigns (#126-#133).",
        flush=True,
    )


if __name__ == "__main__":
    main()
