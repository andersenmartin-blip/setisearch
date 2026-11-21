#!/usr/bin/env python3
"""
Phase D096 (`V5.4`) Prospective Cohort Freeze & Stage-1 Lock Builder.

Runs strictly BEFORE `<ROOT>/inputs_d096_v5_4/` exists:
  1. Verifies Archive U (`D095`) & Archive T (`D094`), extracting all 460 prior excluded
     coordinates and 2,724 prior `dp_id`s plus the unified 401-star / 47-bridge / 441-comb snapshot.
  2. Queries ESA Gaia DR3 & public.hipparcos, NOIRLab `sdss_dr17.apogee2_allstar`, SDSS SkyServer
     `apogeeVisit`, NASA Exoplanet Archive `pscomppars`, IRSA `sofia.observation/plane/artifact`
     (`SOFIA_EXES` _CMB_), GAVO `carmenes.data` (`CARMENES_VIS`), and MAST `Mast.Caom.Filtered`
     (`JWST_NIRISS_SOSS` & `JWST_NIRSPEC_G140H`).
  3. Asserts zero `dp_id` overlap (including format-check exclusions), `>= 300.0"` separation for
     all 24 brand-new stars, `<= 125.0 MiB` total download via HTTP HEAD, and `>= 5.0 km/s` orbital
     `dv_span` across all 5 orbital campaigns (`#134-#138`).
  4. Seals Stage-1 lock (`METHOD_LOCK.json`, `LOCK_RECEIPT.json`, `inputs_d096_v5_4_exists: false`).
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import itertools
import json
import math
import pathlib
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from typing import Any

WS = pathlib.Path(__file__).resolve().parent
ROOT = WS.parent.parent
sys.path.insert(0, str(WS))

import v5_4_detector as det

ARCHIVE_U_NAME = "SETI_D095_V5_3_CURVED_PERIODIC_DRIFT_GHOST_SPITZER_IRS_APOGEE2_RESULTS_2026-11-21.zip"
ARCHIVE_U_SHA256 = "24f5a73a4299d697a198e91e3e15b5b7ddce838f6d055cebe66ddd812520c21d"
ARCHIVE_U_BUNDLE_MEMBER = "bounded_inputs/d095_bounded_bundle.json.gz"

ARCHIVE_T_NAME = "SETI_D094_V5_2_MULTIEPOCH_DRIFT_APOGEE2_CRIRESJH_MIRILRS_RESULTS_2026-11-21.zip"
ARCHIVE_T_SHA256 = "fea863077ae837b6741d5837990fd357158e00f6a5e3d9adde51f0c81e8ccefc"
ARCHIVE_T_BUNDLE_MEMBER = "bounded_inputs/d094_bounded_bundle.json.gz"

# Exclude non-science format-check items inspected during design
FORMAT_CHECK_EXCLUDED_DP_IDS = [
    "F0556_EX_SPE_06014435_EXEELONEXEECHL_CMB_40054-40055.fits",
    "jw01516-o005_t004_niriss_clear-gr700xd-substrip256_x1d.fits",
    "EXES.F0556_EX_SPE_06014435_EXEELONEXEECHL_CMB_40054-40055",
    "JWST.jw01516-o005_t004_niriss_clear-gr700xd-substrip256_x1d",
]

# Stream 1: 17 SOFIA_EXES targets (4 prior bridges + 11 brand-new science + 2 brand-new controls; 19 _CMB_ FITS)
EXES_SPECS: list[dict[str, Any]] = [
    {"canonical_target": "SIRIUS", "common_name": "Sirius (alpha CMa)", "hip": 32349, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_10PC_EXES", "science_track": "SOFIA_EXES_BRIDGE", "is_prior_bridge": True, "panchromatic_bridge": True, "teff_lit": 9940.0, "mh_lit": 0.50, "mass_lit": 2.06, "rv_lit": -5.5, "j_lit": -1.39, "h_lit": -1.39, "ks_lit": -1.35, "n_exo_lit": 0, "trans_lit": False, "fnames": ["F0366_EX_SPE_04007853_EXEELONEXEECHL_CMB_0063-0064.fits"]},
    {"canonical_target": "HD62509", "common_name": "Pollux (beta Gem / HD 62509)", "hip": 37826, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_EXO_EXES", "science_track": "SOFIA_EXES_BRIDGE", "nasa_host": "beta Gem", "is_prior_bridge": True, "panchromatic_bridge": True, "teff_lit": 4892.6, "mh_lit": 0.08, "mass_lit": 1.91, "rv_lit": 3.3, "j_lit": -0.315, "h_lit": -0.845, "ks_lit": -0.936, "n_exo_lit": 1, "trans_lit": False, "fnames": ["F0553_EX_SPE_90008980_EXEELONEXEECHL_CMB_10042-10043.fits"]},
    {"canonical_target": "ARCTURUS", "common_name": "Arcturus (alpha Boo)", "hip": 69673, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_COOL_GIANT_EXES", "science_track": "SOFIA_EXES_BRIDGE", "is_prior_bridge": True, "panchromatic_bridge": True, "teff_lit": 4286.0, "mh_lit": -0.52, "mass_lit": 1.08, "rv_lit": -5.19, "j_lit": -2.252, "h_lit": -2.810, "ks_lit": -2.911, "n_exo_lit": 0, "trans_lit": False, "fnames": ["F0749_EX_SPE_7500601_EXEELONEXEECHL_CMB_70018-70020.fits", "F0194_EX_SPE_86000557_EXEELONEXEECHL_CMB_0099-0102.fits"]},
    {"canonical_target": "ALFTAU", "common_name": "Aldebaran (alpha Tau)", "hip": 21421, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_EXO_EXES", "science_track": "SOFIA_EXES_BRIDGE", "is_prior_bridge": True, "panchromatic_bridge": True, "teff_lit": 4055.0, "mh_lit": -0.22, "mass_lit": 1.16, "rv_lit": 54.26, "j_lit": -2.095, "h_lit": -2.775, "ks_lit": -3.044, "n_exo_lit": 1, "trans_lit": False, "fnames": ["F0194_EX_SPE_86000511_EXEELONEXEECHL_CMB_0048-0049.fits"]},
    {"canonical_target": "HR7957", "common_name": "eta Cep (HR 7957)", "hip": 102422, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_SUBGIANT_EXES", "science_track": "SOFIA_EXES_MIDIR_ECHELLE", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 4950.0, "mh_lit": -0.07, "mass_lit": 1.60, "rv_lit": -87.3, "j_lit": 1.914, "h_lit": 1.504, "ks_lit": 1.393, "n_exo_lit": 0, "trans_lit": False, "fnames": ["F0390_EX_SPE_7100111_EXEELONEXEECHL_CMB_50066-50069.fits"]},
    {"canonical_target": "GAMMADRA", "common_name": "gamma Dra (Eltanin)", "hip": 87833, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_KGIANT_EXES", "science_track": "SOFIA_EXES_MIDIR_ECHELLE", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 3990.0, "mh_lit": -0.14, "mass_lit": 1.72, "rv_lit": -27.6, "j_lit": -0.245, "h_lit": -1.034, "ks_lit": -1.162, "n_exo_lit": 0, "trans_lit": False, "fnames": ["F0197_EX_SPE_86000512_EXEELONEXEECHL_CMB_0133.fits"]},
    {"canonical_target": "DELTAVIR", "common_name": "delta Vir (Auva)", "hip": 63090, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_MGIANT_EXES", "science_track": "SOFIA_EXES_MIDIR_ECHELLE", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 3650.0, "mh_lit": -0.05, "mass_lit": 1.40, "rv_lit": -18.0, "j_lit": -0.113, "h_lit": -1.010, "ks_lit": -1.189, "n_exo_lit": 0, "trans_lit": False, "fnames": ["F0194_EX_SPE_8600056_EXEELONEXEECHL_CMB_0090.fits"]},
    {"canonical_target": "SIGMALIB", "common_name": "sigma Lib (Brachium)", "hip": 73714, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_MGIANT_EXES", "science_track": "SOFIA_EXES_MIDIR_ECHELLE", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 3590.0, "mh_lit": -0.10, "mass_lit": 1.50, "rv_lit": -4.3, "j_lit": -0.321, "h_lit": -1.202, "ks_lit": -1.399, "n_exo_lit": 0, "trans_lit": False, "fnames": ["F0194_EX_SPE_86000510_EXEELONEXEECHL_CMB_0125-0124.fits"]},
    {"canonical_target": "OCETI", "common_name": "Mira (o Ceti)", "hip": 10826, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_AGB_EXES", "science_track": "SOFIA_EXES_MIDIR_ECHELLE", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 3000.0, "mh_lit": 0.00, "mass_lit": 1.18, "rv_lit": 63.8, "j_lit": -0.732, "h_lit": -1.574, "ks_lit": -2.213, "n_exo_lit": 0, "trans_lit": False, "fnames": ["F0661_EX_SPE_0700144_EXEELONEXEECHL_CMB_30008-30009.fits"]},
    {"canonical_target": "ALPHAHER", "common_name": "alpha Her (Rasalgethi)", "hip": 84345, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_MBRIGHTGIANT_EXES", "science_track": "SOFIA_EXES_MIDIR_ECHELLE", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 3280.0, "mh_lit": 0.00, "mass_lit": 2.17, "rv_lit": -33.1, "j_lit": -2.302, "h_lit": -3.224, "ks_lit": -3.511, "n_exo_lit": 0, "trans_lit": False, "fnames": ["F0387_EX_SPE_0500735_EXEELONEXEECHL_CMB_20108-20112.fits"]},
    {"canonical_target": "POLARIS", "common_name": "Polaris (alpha UMi)", "hip": 11767, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_CEPHEID_EXES", "science_track": "SOFIA_EXES_MIDIR_ECHELLE", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 6015.0, "mh_lit": 0.10, "mass_lit": 5.40, "rv_lit": -16.4, "j_lit": 0.795, "h_lit": 0.460, "ks_lit": 0.456, "n_exo_lit": 0, "trans_lit": False, "fnames": ["F0559_EX_SPE_7500262_EXEELONEXEECHL_CMB_70083-70085.fits"]},
    {"canonical_target": "ABAUR", "common_name": "AB Aurigae", "hip": None, "gaia_source_id": 156917493449670656, "role": "SCIENCE", "subrole": "SCIENCE_PROTOPLANET_DISK_EXES", "science_track": "SOFIA_EXES_MIDIR_ECHELLE", "nasa_host": "AB Aur", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 9550.0, "mh_lit": 0.00, "mass_lit": 2.40, "rv_lit": 24.7, "j_lit": 5.936, "h_lit": 5.062, "ks_lit": 4.230, "fnames": ["F0196_EX_SPE_0200791_EXEELONEXEECHL_CMB_0071-0083.fits"]},
    {"canonical_target": "BETELGEUSE", "common_name": "Betelgeuse (alpha Ori)", "hip": 27989, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_RSG_R200K_EXES", "science_track": "SOFIA_EXES_MIDIR_ECHELLE", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 3600.0, "mh_lit": 0.00, "mass_lit": 16.5, "rv_lit": 21.9, "j_lit": -2.989, "h_lit": -4.007, "ks_lit": -4.378, "n_exo_lit": 0, "trans_lit": False, "fnames": ["F0390_EX_SPE_0500731_EXEELONEXEECHL_CMB_50033-50035.fits", "F0835_EX_SPE_0902276_EXEELONEXEECHL_CMB_70036-70037.fits"]},
    {"canonical_target": "ANTARES", "common_name": "Antares (alpha Sco)", "hip": 80763, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_RSG_EXES", "science_track": "SOFIA_EXES_MIDIR_ECHELLE", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 3660.0, "mh_lit": 0.00, "mass_lit": 12.0, "rv_lit": -3.4, "j_lit": -2.850, "h_lit": -3.725, "ks_lit": -4.100, "n_exo_lit": 0, "trans_lit": False, "fnames": ["F0198_EX_SPE_86000537_EXEELONEXEECHL_CMB_5172-5173.fits"]},
    {"canonical_target": "MUGEM", "common_name": "mu Gem (Tejat)", "hip": 30343, "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_MGIANT_EXES", "science_track": "SOFIA_EXES_MIDIR_ECHELLE", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 3650.0, "mh_lit": 0.00, "mass_lit": 2.10, "rv_lit": 54.8, "j_lit": -0.912, "h_lit": -1.608, "ks_lit": -1.862, "n_exo_lit": 0, "trans_lit": False, "fnames": ["F0860_EX_SPE_90008986_EXEELONEXEECHL_CMB_20016.fits"]},
    {"canonical_target": "NGC1068", "common_name": "NGC 1068 (Control Seyfert-2 AGN)", "hip": None, "gaia_source_id": None, "ra_lit": 40.669879, "dec_lit": -0.013294, "dist_lit": 1.44e7, "g_lit": 9.60, "role": "CONTROL", "subrole": "CONTROL_EXTRAGALACTIC_AGN_EXES", "science_track": "SOFIA_EXES_CONTROL", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 4500.0, "mh_lit": 0.00, "mass_lit": 1.0, "rv_lit": 1137.0, "j_lit": 11.381, "h_lit": 8.636, "ks_lit": 8.112, "n_exo_lit": 0, "trans_lit": False, "fnames": ["F0235_EX_SPE_03006516_EXEELONEXEECHL_CMB_0063-0073.fits"]},
    {"canonical_target": "NGC7027", "common_name": "NGC 7027 (Control Planetary Nebula)", "hip": None, "gaia_source_id": None, "ra_lit": 316.757367, "dec_lit": 42.235997, "dist_lit": 920.0, "g_lit": 16.0, "role": "CONTROL", "subrole": "CONTROL_PLANETARY_NEBULA_EXES", "science_track": "SOFIA_EXES_CONTROL", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 30000.0, "mh_lit": 0.00, "mass_lit": 0.7, "rv_lit": 9.0, "j_lit": 9.736, "h_lit": 8.260, "ks_lit": 7.305, "n_exo_lit": 0, "trans_lit": False, "fnames": ["F0400_EX_SPE_05012114_EXEELONEXEECHL_CMB_30048-30052.fits"]},
]

# Stream 2: 3 brand-new <10pc CARMENES_VIS M dwarfs (10 FITS, 2 orbital campaigns #134-#135 + LP73158 N=2)
CARMENES_SPECS: list[dict[str, Any]] = [
    {"canonical_target": "WOLF1069", "common_name": "Wolf 1069 (J20260+585)", "carmenes_id": "J20260+585", "gaia_source_id": 2188318517720321664, "role": "SCIENCE", "subrole": "SCIENCE_10PC_HZ_MDWARF_N4", "science_track": "DRIFT_V54_COHERENT_ORBITAL", "nasa_host": "Wolf 1069", "prefer_planet": "Wolf 1069 b", "t0_lit": 2459499.18, "ecc_lit": 0.0, "orbital_campaign": True, "campaign_index": 134, "n_target_epochs": 4, "teff_lit": 3158.0, "mh_lit": 0.07, "mass_lit": 0.167, "rv_lit": -60.26, "j_lit": 9.029, "h_lit": 8.483, "ks_lit": 8.095},
    {"canonical_target": "HNLIB", "common_name": "HN Lib (GJ 555 / J14342-125)", "carmenes_id": "J14342-125", "gaia_source_id": 6324325225803432320, "role": "SCIENCE", "subrole": "SCIENCE_10PC_HZ_MDWARF_N4", "science_track": "DRIFT_V54_COHERENT_ORBITAL", "nasa_host": "HN Lib", "prefer_planet": "HN Lib b", "t0_lit": 2457436.30, "ecc_lit": 0.079, "orbital_campaign": True, "campaign_index": 135, "n_target_epochs": 4, "teff_lit": 3211.0, "mh_lit": 0.17, "mass_lit": 0.291, "rv_lit": -1.36, "j_lit": 6.838, "h_lit": 6.262, "ks_lit": 5.939},
    {"canonical_target": "LP73158", "common_name": "LP 731-58 (GJ 3622 / J10482-113)", "carmenes_id": "J10482-113", "gaia_source_id": 3757613049856225792, "role": "SCIENCE", "subrole": "SCIENCE_10PC_MDWARF_N2", "science_track": "CARMENES_VIS_10PC", "nasa_host": "", "orbital_campaign": False, "campaign_index": None, "n_target_epochs": 2, "teff_lit": 2950.0, "mh_lit": -0.10, "mass_lit": 0.140, "rv_lit": 1.47, "j_lit": 8.857, "h_lit": 8.263, "ks_lit": 7.926, "n_exo_lit": 0, "trans_lit": False},
]

# Stream 3: 4 brand-new SDSS_APOGEE2 targets (3 high-cadence N=27..28 Kepler orbital campaigns #136-#138 + 1 N=14 hot B-star control)
APOGEE2_SPECS: list[dict[str, Any]] = [
    {"canonical_target": "KEPLER381", "common_name": "Kepler-381", "apogee_id": "2M19004386+4349519", "telescope": "apo25m", "field": "K07_075+17", "gaia_source_id": 2105835281411929728, "role": "SCIENCE", "subrole": "SCIENCE_KEPLER_ORBITAL_N27", "science_track": "DRIFT_V54_COHERENT_ORBITAL", "nasa_host": "Kepler-381", "prefer_planet": "Kepler-381 b", "orbital_campaign": True, "campaign_index": 136, "teff_lit": 6261.4, "mh_lit": -0.20, "mass_lit": 1.144, "rv_lit": -2.845, "j_lit": 9.721, "h_lit": 9.547, "ks_lit": 9.504},
    {"canonical_target": "KEPLER1313", "common_name": "Kepler-1313", "apogee_id": "2M19293325+4213597", "telescope": "apo25m", "field": "K16_075+11", "gaia_source_id": 2125713940547834496, "role": "SCIENCE", "subrole": "SCIENCE_KEPLER_ORBITAL_N27", "science_track": "DRIFT_V54_COHERENT_ORBITAL", "nasa_host": "Kepler-1313", "prefer_planet": "Kepler-1313 b", "orbital_campaign": True, "campaign_index": 137, "teff_lit": 5264.4, "mh_lit": -0.008, "mass_lit": 0.920, "rv_lit": -29.116, "j_lit": 10.522, "h_lit": 10.130, "ks_lit": 10.088},
    {"canonical_target": "KEPLER1002", "common_name": "Kepler-1002", "apogee_id": "2M19321907+4304253", "telescope": "apo25m", "field": "K16_075+11", "gaia_source_id": 2077837115462974080, "role": "SCIENCE", "subrole": "SCIENCE_KEPLER_ORBITAL_N28", "science_track": "DRIFT_V54_COHERENT_ORBITAL", "nasa_host": "Kepler-1002", "prefer_planet": "Kepler-1002 b", "orbital_campaign": True, "campaign_index": 138, "teff_lit": 5982.8, "mh_lit": 0.103, "mass_lit": 1.220, "rv_lit": -45.749, "j_lit": 10.689, "h_lit": 10.449, "ks_lit": 10.374},
    {"canonical_target": "2M20491499", "common_name": "2M2049+6231 (Control Hot B-Star)", "apogee_id": "2M20491499+6231469", "telescope": "apo25m", "field": "100+12", "gaia_source_id": 2196709917449599360, "role": "CONTROL", "subrole": "CONTROL_HOT_BSTAR_N14", "science_track": "DRIFT_V54_COHERENT_CONTROL", "nasa_host": "", "orbital_campaign": False, "teff_lit": 12509.3, "mh_lit": 0.00, "mass_lit": 4.0, "rv_lit": 6.200, "j_lit": 7.886, "h_lit": 7.929, "ks_lit": 7.947, "n_exo_lit": 0, "trans_lit": False},
]

# Stream 4 & 5: 6 JWST targets (2 NIRISS/SOSS + 4 NIRSpec/G140H; 2 prior bridges + 4 brand-new)
JWST_SPECS: list[dict[str, Any]] = [
    {"instrument": "JWST_NIRISS_SOSS", "canonical_target": "SIMP0136", "common_name": "SIMP J013656.5+093347.3", "gaia_source_id": None, "ra_lit": 24.235937, "dec_lit": 9.563146, "dist_lit": 6.130, "g_lit": math.nan, "role": "SCIENCE", "subrole": "SCIENCE_10PC_BROWN_DWARF_SOSS", "science_track": "JWST_NIRISS_SOSS_LASER_BANDS", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 1150.0, "mh_lit": 0.00, "mass_lit": 0.012, "rv_lit": 11.5, "j_lit": 13.455, "h_lit": 12.771, "ks_lit": 12.562, "n_exo_lit": 0, "trans_lit": False, "grating": "GR700XD_SOSS", "resolving_power": 700.0, "obs_id": "jw01209-o001_t001_niriss_clear-gr700xd", "fname": "jw01209-o001_t001_niriss_clear-gr700xd_x1d.fits", "mjd_fallback": 60147.259457, "expt_fallback": 8696.784},
    {"instrument": "JWST_NIRISS_SOSS", "canonical_target": "HD59533", "common_name": "HD 59533 (Control Flux Std SOSS)", "gaia_source_id": 5281573068315516160, "role": "CONTROL", "subrole": "CONTROL_ASTAR_FLUX_STD_SOSS", "science_track": "JWST_NIRISS_SOSS_CONTROL", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 8052.2, "mh_lit": -0.20, "mass_lit": 1.80, "rv_lit": 21.46, "j_lit": 8.630, "h_lit": 8.593, "ks_lit": 8.509, "n_exo_lit": 0, "trans_lit": False, "grating": "GR700XD_SOSS", "resolving_power": 700.0, "obs_id": "jw01516-o004_t004_niriss_clear-gr700xd-substrip256", "fname": "jw01516-o004_t004_niriss_clear-gr700xd-substrip256_x1d.fits", "mjd_fallback": 59769.983743, "expt_fallback": 109.88},
    {"instrument": "JWST_NIRSPEC_G140H", "canonical_target": "VHS1256B", "common_name": "VHS J1256-1257 b", "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_COMPANION_G140H", "science_track": "JWST_NIRSPEC_G140H_BRIDGE", "is_prior_bridge": True, "panchromatic_bridge": True, "teff_lit": 2620.0, "mh_lit": 0.00, "mass_lit": 0.019, "rv_lit": 5.0, "j_lit": 11.018, "h_lit": 10.473, "ks_lit": 10.044, "n_exo_lit": 1, "trans_lit": False, "grating": "G140H_F100LP", "resolving_power": 2700.0, "obs_id": "jw01386-o013_t004_nirspec_g140h-f100lp", "fname": "jw01386-o013_t004_nirspec_g140h-f100lp_x1d.fits", "mjd_fallback": 59765.364241, "expt_fallback": 2450.936},
    {"instrument": "JWST_NIRSPEC_G140H", "canonical_target": "BD601753", "common_name": "BD+60 1753 (Control Bridge)", "gaia_source_id": None, "role": "CONTROL", "subrole": "CONTROL_BRIDGE_FLUX_STD_G140H", "science_track": "JWST_NIRSPEC_G140H_CONTROL_BRIDGE", "is_prior_bridge": True, "panchromatic_bridge": True, "teff_lit": 9129.7, "mh_lit": 0.00, "mass_lit": 2.20, "rv_lit": -15.0, "j_lit": 9.650, "h_lit": 9.660, "ks_lit": 9.650, "n_exo_lit": 0, "trans_lit": False, "grating": "G140H_F100LP", "resolving_power": 2700.0, "obs_id": "jw01539-o003_t001-s000000001_nirspec_f100lp-g140h-s1600a1-sub2048", "fname": "jw01539-o003_t001-s000000001_nirspec_f100lp-g140h-s1600a1-sub2048_x1d.fits", "mjd_fallback": 59779.956557, "expt_fallback": 45.10},
    {"instrument": "JWST_NIRSPEC_G140H", "canonical_target": "HD54306", "common_name": "HD 54306 (Control Hot B-Star G140H)", "gaia_source_id": 3046124607448627712, "role": "CONTROL", "subrole": "CONTROL_HOT_OB_G140H", "science_track": "JWST_NIRSPEC_G140H_CONTROL", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 19317.7, "mh_lit": 0.00, "mass_lit": 6.50, "rv_lit": 25.0, "j_lit": 8.794, "h_lit": 8.864, "ks_lit": 8.844, "n_exo_lit": 0, "trans_lit": False, "grating": "G140H_F100LP", "resolving_power": 2700.0, "obs_id": "jw07929-o009_t017-s000000001_nirspec_f100lp-g140h-s200a1-subs200a1", "fname": "jw07929-o009_t017-s000000001_nirspec_f100lp-g140h-s200a1-subs200a1_x1d.fits", "mjd_fallback": 61134.745319, "expt_fallback": 46.74},
    {"instrument": "JWST_NIRSPEC_G140H", "canonical_target": "GSPCP177D", "common_name": "GSPC P177-D (Solar-Analog G140H)", "gaia_source_id": 1399559249961569792, "role": "SCIENCE", "subrole": "SCIENCE_SOLAR_ANALOG_G140H", "science_track": "JWST_NIRSPEC_G140H_LASER_BANDS", "is_prior_bridge": False, "panchromatic_bridge": False, "teff_lit": 5756.3, "mh_lit": 0.00, "mass_lit": 1.00, "rv_lit": -36.99, "j_lit": 12.245, "h_lit": 11.932, "ks_lit": 11.861, "n_exo_lit": 0, "trans_lit": False, "grating": "G140H_F070LP", "resolving_power": 2700.0, "obs_id": "jw01128-o015_t019-s000000001_nirspec_f070lp-g140h-s1600a1", "fname": "jw01128-o015_t019-s000000001_nirspec_f070lp-g140h-s1600a1_x1d.fits", "mjd_fallback": 59664.316216, "expt_fallback": 175.066},
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


def _urlopen_retry(req: urllib.request.Request, timeout_s: float = 60.0) -> bytes:
    last_err: Exception | None = None
    for att in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as r:
                return r.read()
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (att + 1))
    raise RuntimeError(f"HTTP failure {req.full_url}: {last_err}")


def tap_csv(url_base: str, query: str, param_key: str = "QUERY", timeout_s: float = 90.0) -> list[dict[str, str]]:
    if param_key == "QUERY":
        params = {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query}
    elif param_key == "cmd":
        params = {"cmd": query, "format": "csv"}
    else:
        params = {param_key: query, "format": "csv"}
    url = f"{url_base}?{urllib.parse.urlencode(params)}"
    txt = _urlopen_retry(urllib.request.Request(url, headers={"User-Agent": "SETIsearch-D096/1.0"}), timeout_s=timeout_s).decode("utf-8", errors="replace")
    if txt.lstrip().startswith("<?xml"):
        raise RuntimeError(f"TAP XML error from {url_base}: {txt[:400]}")
    lines = [l for l in txt.splitlines() if not l.startswith("#")]
    return list(csv.DictReader(lines))


def head_content_length(url: str) -> int:
    last_err: Exception | None = None
    for att in range(4):
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "SETIsearch-D096/1.0"})
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
    inp_dir = ROOT / "inputs_d096_v5_4"
    if inp_dir.exists():
        raise RuntimeError(f"Prospective hygiene violation: {inp_dir} already exists before Stage-1 lock!")

    arch_u = ROOT / "archives" / ARCHIVE_U_NAME
    arch_t = ROOT / "archives" / ARCHIVE_T_NAME
    for zp, exp in ((arch_u, ARCHIVE_U_SHA256), (arch_t, ARCHIVE_T_SHA256)):
        if not zp.exists() or sha256_file(zp) != exp:
            raise RuntimeError(f"Archive integrity check failed for {zp.name}")

    print("1. Extracting Archive U (D095) exclusion registry & Archive T (D094) bundle digest...", flush=True)
    with zipfile.ZipFile(arch_t, "r") as zt:
        t_bundle_sha = sha256_bytes(zt.read(ARCHIVE_T_BUNDLE_MEMBER))

    with zipfile.ZipFile(arch_u, "r") as zu:
        u_bundle_sha = sha256_bytes(zu.read(ARCHIVE_U_BUNDLE_MEMBER))
        pe95 = json.loads(zu.read("PRIOR_EXCLUSION_VERIFICATION.json").decode("utf-8"))
        sum95 = json.loads(zu.read("results/SUMMARY.json").decode("utf-8"))
        coh95 = list(csv.DictReader(zu.read("FROZEN_COHORT_D095.csv").decode("utf-8").splitlines()))
        u401_rows = list(csv.DictReader(zu.read("results/UNIFIED_PANCHROMATIC_V5_3_SYNTHESIS_401STARS.csv").decode("utf-8").splitlines()))
        br47_rows = list(csv.DictReader(zu.read("results/PANCHROMATIC_BRIDGE_47STARS_V53.csv").decode("utf-8").splitlines()))
        comb_u95 = list(csv.DictReader(zu.read("results/ALLSKY_COMB_V4_1_UNIFIED_D079_D095.csv").decode("utf-8").splitlines()))
        comb_c95 = list(csv.DictReader(zu.read("results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D095.csv").decode("utf-8").splitlines()))

    u401_map = {r["star"]: r for r in u401_rows}
    br47_set = {r["star"] for r in br47_rows}
    prior_coords: list[dict[str, Any]] = list(pe95["excluded_targets_coordinate_registry"])
    seen_95: set[str] = {r["label"].split("(")[0] for r in prior_coords}
    for r in coh95:
        st = r["canonical_target"]
        if r["is_prior_bridge"] != "True" and st not in seen_95:
            seen_95.add(st)
            prior_coords.append({"label": f"{st}(D095)", "ra_deg": float(r["s_ra"]), "dec_deg": float(r["s_dec"])})
    excluded_dp_ids: set[str] = set(pe95["excluded_dp_ids"]) | {r["dp_id"] for r in coh95} | set(FORMAT_CHECK_EXCLUDED_DP_IDS)

    syn95 = sum95["unified_401star_panchromatic_v5_3_synthesis"]
    prior_snap = {
        "schema": "D096_PRIOR_V5_3_PHASES_SNAPSHOT",
        "prior_phases": "D079-D095",
        "source_archive_u_name": ARCHIVE_U_NAME,
        "source_archive_u_sha256": ARCHIVE_U_SHA256,
        "source_archive_u_bundle_member": ARCHIVE_U_BUNDLE_MEMBER,
        "source_archive_u_bundle_sha256": u_bundle_sha,
        "source_archive_t_name": ARCHIVE_T_NAME,
        "source_archive_t_sha256": ARCHIVE_T_SHA256,
        "source_archive_t_bundle_member": ARCHIVE_T_BUNDLE_MEMBER,
        "source_archive_t_bundle_sha256": t_bundle_sha,
        "prior_unique_stars_count": len(u401_rows),
        "prior_within_10pc_count": syn95["within_10pc_unique_stars"],
        "prior_total_exposures_count": syn95["total_exposures_d079_d095"],
        "prior_cumulative_integration_hours": syn95["total_integration_hours_d079_d095"],
        "prior_calibration_trials_count": syn95["total_calibration_trials_d079_d095"],
        "prior_v2_false_alarms_eliminated_total": syn95["v2_false_alarms_eliminated_total"],
        "prior_cumulative_orbital_campaigns_count": syn95["cumulative_orbital_campaigns"],
        "prior_panchromatic_bridge_stars_count": len(br47_set),
        "prior_panchromatic_bridge_cells_count": syn95["panchromatic_bridge_cells_total"],
        "d095_summary_headline": sum95,
        "prior_unified_401_rows": u401_rows,
        "prior_bridge_47_rows": br47_rows,
        "prior_allsky_comb_unified_rows": comb_u95,
        "prior_allsky_comb_candidate_rows": comb_c95,
    }

    print("2. Querying catalogs...", flush=True)
    all_specs = EXES_SPECS + CARMENES_SPECS + APOGEE2_SPECS + JWST_SPECS
    all_gids = sorted({int(s["gaia_source_id"]) for s in all_specs if s.get("gaia_source_id")})
    gq = (
        "SELECT source_id, ra, dec, parallax, pmra, pmdec, phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag, "
        f"radial_velocity, teff_gspphot, mh_gspphot FROM gaiadr3.gaia_source WHERE source_id IN ({','.join(map(str, all_gids))})"
    )
    print("  2a Gaia DR3...", flush=True)
    gaia_map = {int(r["source_id"]): r for r in tap_csv("https://gea.esac.esa.int/tap-server/tap/sync", gq)}
    if len(gaia_map) != len(all_gids):
        raise RuntimeError(f"Gaia DR3 missing IDs: {set(all_gids) - set(gaia_map)}")

    all_hips = sorted({int(s["hip"]) for s in EXES_SPECS if s.get("hip") and not s.get("is_prior_bridge")})
    hq = f"SELECT hip, ra, de, plx, pmra, pmde, vmag FROM public.hipparcos WHERE hip IN ({','.join(map(str, all_hips))})"
    print("  2b Hipparcos...", flush=True)
    hip_map = {int(r["hip"]): r for r in tap_csv("https://gea.esac.esa.int/tap-server/tap/sync", hq)}
    if len(hip_map) != len(all_hips):
        raise RuntimeError(f"Hipparcos missing IDs: {set(all_hips) - set(hip_map)}")

    apo_ids_sql = ",".join(f"'{s['apogee_id']}'" for s in APOGEE2_SPECS)
    aq = (
        "SELECT s.apogee_id, s.telescope, s.field, s.nvisits AS nvis, s.vhelio_avg AS hrv, s.snr, a.teff, a.m_h "
        f"FROM apogeeStar s LEFT JOIN aspcapStar a ON s.apstar_id = a.apstar_id WHERE s.apogee_id IN ({apo_ids_sql})"
    )
    print("  2c SDSS SkyServer apogeeStar/aspcapStar...", flush=True)
    apo_map = {(r["apogee_id"], r["telescope"], r["field"]): r for r in tap_csv("https://skyserver.sdss.org/dr17/SkyServerWS/SearchTools/SqlSearch", aq, param_key="cmd")}

    av_sql = f"SELECT apogee_id, mjd, jd, snr, vhelio FROM apogeeVisit WHERE apogee_id IN ({apo_ids_sql})"
    print("  2d SDSS apogeeVisit...", flush=True)
    av_rows = tap_csv("https://skyserver.sdss.org/dr17/SkyServerWS/SearchTools/SqlSearch", av_sql, param_key="cmd")
    av_by_id: dict[str, list[dict[str, str]]] = {}
    for vr in av_rows:
        av_by_id.setdefault(vr["apogee_id"], []).append(vr)

    hosts = sorted({s["nasa_host"] for s in all_specs if s.get("nasa_host")})
    nq = (
        "SELECT pl_name, hostname, pl_orbper, pl_tranmid, pl_orbeccen, st_mass, tran_flag "
        f"FROM pscomppars WHERE hostname IN ({','.join(chr(39) + h + chr(39) for h in hosts)})"
    )
    print("  2e NASA Exoplanet Archive...", flush=True)
    nasa_rows = tap_csv("https://exoplanetarchive.ipac.caltech.edu/TAP/sync", nq, param_key="query")
    nasa_by_host: dict[str, list[dict[str, str]]] = {}
    for nr in nasa_rows:
        nasa_by_host.setdefault(nr["hostname"], []).append(nr)

    # IRSA SOFIA EXES CMB metadata
    want_exes_files = {fn for s in EXES_SPECS for fn in s["fnames"]}
    iq = """
    SELECT o.target_name, o.observationid, p.energy_resolvingpower, p.energy_bounds_lower, p.energy_bounds_upper,
           p.time_bounds_lower, p.time_exposure, a.uri, a.contentlength
    FROM sofia.observation o
    JOIN sofia.plane p ON o.obsid = p.obsid
    JOIN sofia.artifact a ON p.planeid = a.planeid
    WHERE o.instrument_name = 'EXES'
      AND p.calibrationlevel >= 2
      AND p.energy_resolvingpower >= 40000
      AND a.producttype = 'science'
      AND a.uri LIKE '%_CMB_%'
      AND o.target_name IN (
        'alpha CMa', 'beta Gem', 'Arcturus', 'alpha Boo', 'alpha Tau',
        'HR 7957', 'gamma Drac', 'delta Vir', 'sigma Lib', 'o Ceti',
        'alpha Her', 'Alpha UMi', 'AB Aur', 'alpha Ori', 'Betelgeuse',
        'alpha Sco', 'mu Gem', 'NGC 1068', 'NGC7027'
      )
    """
    print("  2f IRSA SOFIA EXES...", flush=True)
    exes_rows = tap_csv("https://irsa.ipac.caltech.edu/TAP/sync", iq, timeout_s=120.0)
    exes_by_fname: dict[str, dict[str, str]] = {}
    for er in exes_rows:
        fn = er["uri"].strip().split("/")[-1]
        if fn in want_exes_files and fn not in exes_by_fname:
            exes_by_fname[fn] = er
    if set(exes_by_fname) != want_exes_files:
        raise RuntimeError(f"Missing IRSA EXES files: {want_exes_files - set(exes_by_fname)}")

    # GAVO CARMENES_VIS metadata
    cids_sql = ",".join(f"'{s['carmenes_id']}'" for s in CARMENES_SPECS)
    cq = (
        "SELECT ssa_targname, accref, ssa_dateobs, ssa_timeext, ssa_snr "
        f"FROM carmenes.data WHERE ssa_targname IN ({cids_sql}) AND ssa_specstart < 6e-7 ORDER BY ssa_targname, ssa_dateobs"
    )
    print("  2g GAVO CARMENES...", flush=True)
    carm_rows = tap_csv("https://dc.g-vo.org/tap/sync", cq)
    carm_by_cid: dict[str, list[dict[str, str]]] = {}
    for cr in carm_rows:
        carm_by_cid.setdefault(cr["ssa_targname"], []).append(cr)

    # MAST CAOM metadata for JWST obs_ids
    print("  2h MAST JWST...", flush=True)
    jwst_obs_ids = sorted({s["obs_id"] for s in JWST_SPECS})
    mast_payload = json.dumps({
        "service": "Mast.Caom.Filtered",
        "params": {
            "columns": "obs_id,t_min,t_max,t_exptime,s_ra,s_dec,filters",
            "filters": [{"paramName": "obs_id", "values": jwst_obs_ids}],
        },
        "format": "json",
        "pagesize": 100,
    })
    mast_req = urllib.request.Request(
        "https://mast.stsci.edu/api/v0/invoke",
        data=urllib.parse.urlencode({"request": mast_payload}).encode(),
        headers={"User-Agent": "SETIsearch-D096/1.0"},
        method="POST",
    )
    mast_data = json.loads(_urlopen_retry(mast_req).decode("utf-8")).get("data", [])
    mast_by_obs = {d["obs_id"]: d for d in mast_data}

    def resolve_star_meta(spec: dict[str, Any]) -> dict[str, Any]:
        st = spec["canonical_target"]
        gid = spec.get("gaia_source_id")
        hip_id = spec.get("hip")
        if st in u401_map and spec.get("is_prior_bridge") and gid is None:
            u = u401_map[st]
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
                "teff_k": float(spec["teff_lit"]) if st in ("ABAUR", "WOLF1069", "HNLIB", "LP73158", "2M20491499", "HD54306", "HD59533") else _opt_float(g.get("teff_gspphot"), spec["teff_lit"]),
                "mh_dex": _opt_float(g.get("mh_gspphot"), spec["mh_lit"]),
                "rv_kms": _opt_float(g.get("radial_velocity"), spec["rv_lit"]),
                "mass_msun": float(spec["mass_lit"]),
            }
        if hip_id and int(hip_id) in hip_map:
            h = hip_map[int(hip_id)]
            plx = float(h["plx"])
            return {
                "gaia_source_id": 0,
                "ra": float(h["ra"]),
                "dec": float(h["de"]),
                "pmra": _opt_float(h.get("pmra"), 0.0),
                "pmdec": _opt_float(h.get("pmde"), 0.0),
                "dist_pc": 1000.0 / plx,
                "g_mag": _opt_float(h.get("vmag"), math.nan),
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
        return {
            "gaia_source_id": 0,
            "ra": float(spec["ra_lit"]),
            "dec": float(spec["dec_lit"]),
            "pmra": 0.0,
            "pmdec": 0.0,
            "dist_pc": float(spec["dist_lit"]),
            "g_mag": _opt_float(spec.get("g_lit"), math.nan),
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

    # --- Stream 1: SOFIA_EXES (17 targets, 19 _CMB_ FITS) ---
    print("3. Selecting & HEAD-checking Stream 1 (SOFIA_EXES, 17 targets / 19 FITS)...", flush=True)
    for spec in EXES_SPECS:
        st = spec["canonical_target"]
        m = resolve_star_meta(spec)
        for erank, fname in enumerate(spec["fnames"], 1):
            er = exes_by_fname[fname]
            furl = er["uri"].strip()
            fbytes = head_content_length(furl)
            rp_val = float(er["energy_resolvingpower"])
            mjd_v = float(er["time_bounds_lower"])
            expt_v = _opt_float(er.get("time_exposure"), 300.0)
            w_um = round(0.5 * (float(er["energy_bounds_lower"]) + float(er["energy_bounds_upper"])) * 1e6, 2)
            dp_id = f"EXES.{fname[:-5]}"
            if dp_id in excluded_dp_ids or fname in excluded_dp_ids:
                raise RuntimeError(f"Duplicate EXES dp_id: {dp_id}")
            append_cohort_row(
                "SOFIA_EXES", spec, m, erank, dp_id, f"EXES_{w_um:.1f}UM", rp_val,
                mjd_v, expt_v, "NONE", 0.0, 0.0, fname[:-5], f"SOFIA_EXES/{st}/{fname}", furl, fbytes,
            )

    # --- Stream 2: CARMENES_VIS (3 <10pc targets, 10 FITS, campaigns #134-#135) ---
    print("4. Selecting & HEAD-checking Stream 2 (CARMENES_VIS, 3 <10pc targets / 10 FITS, campaigns #134-#135)...", flush=True)
    for spec in CARMENES_SPECS:
        st = spec["canonical_target"]
        cid = spec["carmenes_id"]
        m = resolve_star_meta(spec)
        raw_pool = carm_by_cid.get(cid, [])
        pool: list[dict[str, Any]] = []
        for r in raw_pool:
            accref = (r.get("accref") or "").strip()
            fname = accref.split("/")[-1]
            if not fname.endswith(".fits"):
                continue
            dp_id = f"CARMENES.{fname[:-5]}"
            if dp_id in excluded_dp_ids:
                continue
            mjd_s = r.get("ssa_dateObs") or r.get("ssa_dateobs")
            snr_s = r.get("ssa_snr")
            if not (mjd_s and snr_s) or float(snr_s) < 15.0:
                continue
            furl = accref.replace("http://dc.g-vo.org/getproduct/carmenes/data/", "https://dc.g-vo.org/carmenes/q/sdl/static/")
            expt_v = _opt_float(r.get("ssa_timeExt") or r.get("ssa_timeext"), 900.0)
            berv_est = det.analytical_observatory_berv_kms(m["ra"], m["dec"], float(mjd_s), "CARMENES_VIS")
            pool.append({
                "dp_id": dp_id,
                "mjd_obs": float(mjd_s),
                "t_exptime": expt_v,
                "snr": float(snr_s),
                "berv_est": berv_est,
                "f1_id": fname[:-5],
                "fname": fname,
                "furl": furl,
            })
        pool.sort(key=lambda x: x["mjd_obs"])
        n_req = int(spec["n_target_epochs"])
        assert len(pool) >= n_req, f"{st}: CARMENES pool too small ({len(pool)})"

        if spec.get("orbital_campaign"):
            plist = nasa_by_host.get(spec["nasa_host"], [])
            tp = next((p for p in plist if p["pl_name"] == spec.get("prefer_planet")), plist[0])
            p_d = float(tp["pl_orbper"])
            t0_b = _opt_float(tp.get("pl_tranmid"), float(spec.get("t0_lit", 2459499.18)))
            ecc_v = _opt_float(tp.get("pl_orbeccen"), float(spec.get("ecc_lit", 0.0)))
            st_mass = _opt_float(tp.get("st_mass"), m["mass_msun"])
            m["mass_msun"] = st_mass
            kp = det.compute_keplerian_kp_kms(st_mass, p_d, ecc=ecc_v)

            # Subsample high-SNR candidates spread across MJD & phase to find best 4-epoch quartet
            top_pool = sorted(pool, key=lambda x: x["snr"], reverse=True)[:min(40, len(pool))]
            top_pool.sort(key=lambda x: x["mjd_obs"])
            if len(top_pool) > 16:
                idxs = sorted({int(round(i * (len(top_pool) - 1) / 15)) for i in range(16)})
                cand_pool = [top_pool[i] for i in idxs]
            else:
                cand_pool = top_pool

            best_q = None
            for quad in itertools.combinations(cand_pool, 4):
                dts = [quad[k + 1]["mjd_obs"] - quad[k]["mjd_obs"] for k in range(3)]
                if min(dts) < 1.0:
                    continue
                dvs = [det.compute_planet_orbital_rv_kms(q["mjd_obs"] + 2400000.5, t0_b, p_d, kp)[1] for q in quad]
                dv_span = max(dvs) - min(dvs)
                berv_span = max(q["berv_est"] for q in quad) - min(q["berv_est"] for q in quad)
                base_days = quad[-1]["mjd_obs"] - quad[0]["mjd_obs"]
                score = dv_span + 0.3 * berv_span + 0.01 * min(base_days, 1200.0)
                if best_q is None or score > best_q[0]:
                    best_q = (score, list(quad))
            assert best_q is not None, f"{st}: failed finding 4 spaced epochs"
            chosen = sorted(best_q[1], key=lambda x: x["mjd_obs"])
            camp_exps = []
            for erank, item in enumerate(chosen, 1):
                s_ph, o_rv = det.compute_planet_orbital_rv_kms(item["mjd_obs"] + 2400000.5, t0_b, p_d, kp)
                ph_win = "IN_WINDOW" if abs(o_rv) > 0.4 * kp else "OUT_OF_WINDOW"
                fbytes = head_content_length(item["furl"])
                append_cohort_row(
                    "CARMENES_VIS", spec, m, erank, item["dp_id"], "CARMENES_VIS", 94600.0,
                    item["mjd_obs"], item["t_exptime"], ph_win, s_ph, o_rv,
                    item["f1_id"], f"CARMENES_VIS/{st}/{item['fname']}", item["furl"], fbytes,
                )
                camp_exps.append({
                    "dp_id": item["dp_id"],
                    "mjd_obs": round(item["mjd_obs"], 6),
                    "bjd_tdb_est": round(item["mjd_obs"] + 2400000.5, 6),
                    "signed_phase": round(s_ph, 6),
                    "phase_window": ph_win,
                    "planet_orbital_rv_kms": round(o_rv, 4),
                    "ppo_align_score": 1.0,
                })
            dvs_c = [e["planet_orbital_rv_kms"] for e in camp_exps]
            dv_span_c = max(dvs_c) - min(dvs_c)
            assert dv_span_c >= 5.0, f"{st}: CARMENES orbital dv_span={dv_span_c} < 5.0 km/s"
            orbital_campaigns[st] = {
                "campaign_index": int(spec["campaign_index"]),
                "canonical_target": st,
                "common_name": spec["common_name"],
                "instrument": "CARMENES_VIS",
                "role": spec["role"],
                "null_orbital": False,
                "planet_name": tp["pl_name"],
                "n_planets_in_system": len(plist),
                "stellar_mass_msun": round(st_mass, 3),
                "orb_per_days": p_d,
                "orb_t0_bjd": t0_b,
                "orb_ecc": ecc_v,
                "kp_kms": round(kp, 3),
                "orbital_dv_span_kms": round(dv_span_c, 3),
                "n_epochs": len(camp_exps),
                "exposures": camp_exps,
            }
        else:
            # Select highest BERV-separation high-SNR pair
            top_pool = sorted(pool, key=lambda x: x["snr"], reverse=True)[:min(30, len(pool))]
            best_p = max(
                itertools.combinations(top_pool, 2),
                key=lambda pr: abs(pr[0]["berv_est"] - pr[1]["berv_est"]) + 0.01 * abs(pr[0]["mjd_obs"] - pr[1]["mjd_obs"]),
            )
            chosen = sorted(best_p, key=lambda x: x["mjd_obs"])
            for erank, item in enumerate(chosen, 1):
                fbytes = head_content_length(item["furl"])
                append_cohort_row(
                    "CARMENES_VIS", spec, m, erank, item["dp_id"], "CARMENES_VIS", 94600.0,
                    item["mjd_obs"], item["t_exptime"], "NONE", 0.0, 0.0,
                    item["f1_id"], f"CARMENES_VIS/{st}/{item['fname']}", item["furl"], fbytes,
                )

    # --- Stream 3: SDSS_APOGEE2 (4 targets, 96 visits, campaigns #136-#138 + N=14 control) ---
    print("5. Selecting & HEAD-checking Stream 3 (SDSS_APOGEE2, 4 targets / 96 visits, campaigns #136-#138)...", flush=True)
    for spec in APOGEE2_SPECS:
        st = spec["canonical_target"]
        m = resolve_star_meta(spec)
        aid, tel, fld = spec["apogee_id"], spec["telescope"], spec["field"]
        ar = apo_map[(aid, tel, fld)]
        for k_in, k_out in (("teff", "teff_k"), ("hrv", "rv_kms"), ("m_h", "mh_dex")):
            v = _opt_float(ar.get(k_in))
            if math.isfinite(v) and v > -50.0 and (k_in != "teff" or v > 500.0):
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

    # --- Stream 4 & 5: JWST_NIRISS_SOSS (2 targets) + JWST_NIRSPEC_G140H (4 targets) ---
    print("6. Selecting & HEAD-checking Streams 4 & 5 (JWST NIRISS SOSS + NIRSpec G140H, 6 targets)...", flush=True)
    for spec in JWST_SPECS:
        inst = spec["instrument"]
        st = spec["canonical_target"]
        m = resolve_star_meta(spec)
        fname = spec["fname"]
        oid = spec["obs_id"]
        furl = f"https://mast.stsci.edu/api/v0.1/Download/file?uri={urllib.parse.quote('mast:JWST/product/' + fname, safe='')}"
        fbytes = head_content_length(furl)
        md = mast_by_obs.get(oid, {})
        mjd_v = float(md["t_min"]) if md.get("t_min") is not None else float(spec["mjd_fallback"])
        expt_v = float(md["t_exptime"]) if md.get("t_exptime") is not None else float(spec["expt_fallback"])
        dp_id = f"JWST.{fname[:-5]}"
        if dp_id in excluded_dp_ids or fname in excluded_dp_ids:
            raise RuntimeError(f"Duplicate JWST dp_id: {dp_id}")
        append_cohort_row(
            inst, spec, m, 1, dp_id, spec["grating"], float(spec["resolving_power"]),
            mjd_v, expt_v, "NONE", 0.0, 0.0, fname[:-5], f"{inst}/{st}/{fname}", furl, fbytes,
        )

    # --- Verify 5-arcmin exclusion, zero dp_id overlap & hard caps ---
    print("7. Verifying 5-arcmin prior exclusion, dp_id disjointness, and caps...", flush=True)
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
        raise RuntimeError(f"Intra-D096 collision: {min_intra_sep:.2f}\" < 300\"")

    tot_bytes = sum(r["f1_bytes"] for r in cohort_rows)
    tot_mib = tot_bytes / 1048576.0
    if tot_mib > 125.0:
        raise RuntimeError(f"Projected download {tot_mib:.2f} MiB exceeds 125.0 MiB hard cap!")

    new_10pc = sum(1 for st in unique_new_coords if next(r["within_10pc"] for r in cohort_rows if r["canonical_target"] == st))
    new_ctrl = sum(1 for st in unique_new_coords if next(r["role"] == "CONTROL" for r in cohort_rows if r["canonical_target"] == st))
    all_stars_d096 = sorted({r["canonical_target"] for r in cohort_rows})
    prior_bridges_d096 = sorted({r["canonical_target"] for r in cohort_rows if r["is_prior_bridge"]})

    (WS / "PRIOR_V5_3_PHASES_SNAPSHOT.json").write_text(json.dumps(prior_snap, indent=2) + "\n", encoding="utf-8")

    prior_excl = {
        "schema": "D096_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D096",
        "verified_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prior_phases_covered": "C001-C037 + D001-D095",
        "n_prior_excluded_coords": len(prior_coords),
        "n_prior_excluded_dp_ids": len(excluded_dp_ids),
        "d096_total_stars": len(all_stars_d096),
        "d096_brand_new_unique_stars": len(unique_new_coords),
        "d096_prior_bridge_stars": len(prior_bridges_d096),
        "d096_control_stars": sum(1 for st in all_stars_d096 if next(r["role"] == "CONTROL" for r in cohort_rows if r["canonical_target"] == st)),
        "d096_brand_new_controls": new_ctrl,
        "d096_brand_new_within_10pc": new_10pc,
        "d096_total_input_files": len(cohort_rows),
        "d096_projected_download_bytes": tot_bytes,
        "d096_projected_download_mib": round(tot_mib, 3),
        "d096_dp_id_overlap_count": 0,
        "min_brand_new_sky_separation_arcsec": round(min_brand_new_sep, 2),
        "min_intra_d096_separation_arcsec": round(min_intra_sep, 2),
        "star_separation_verification": star_seps,
        "excluded_dp_ids": sorted(excluded_dp_ids),
        "excluded_targets_coordinate_registry": prior_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(prior_excl, indent=2) + "\n", encoding="utf-8")

    coh_fields = list(cohort_rows[0].keys())
    with (WS / "FROZEN_COHORT_D096.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=coh_fields)
        w.writeheader()
        w.writerows(cohort_rows)

    orb_doc = {
        "schema": "D096_ORBITAL_CAMPAIGNS_AND_KINEMATICS",
        "phase_id": "D096",
        "campaign_range": "#134-#138",
        "n_campaigns": len(orbital_campaigns),
        "campaigns": orbital_campaigns,
    }
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_doc, indent=2) + "\n", encoding="utf-8")

    locked_names = [
        "v5_4_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D096.csv",
        "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "PRIOR_V5_3_PHASES_SNAPSHOT.json",
    ]
    hashes = {fn: sha256_file(WS / fn) for fn in locked_names}
    locked_utc = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    method_lock = {
        "schema": "D096_STAGE1_PROSPECTIVE_METHOD_LOCK",
        "phase_id": "D096",
        "detector_name": det.DETECTOR_NAME,
        "locked_utc": locked_utc,
        "retroactive_reused_bundles": [
            {
                "phase_id": "D095",
                "archive_name": ARCHIVE_U_NAME,
                "archive_sha256": ARCHIVE_U_SHA256,
                "bundle_member": ARCHIVE_U_BUNDLE_MEMBER,
                "bundle_sha256": u_bundle_sha,
                "purpose": "Prior 401-star synthesis, 47 bridges, 460 excluded coords, 2724 dp_ids, 441 comb stacks, plus retroactive D095 N>=4 APOGEE-2 campaigns (9 stars) for DRIFT_V54_COHERENT_SHIFT_STACK",
            },
            {
                "phase_id": "D094",
                "archive_name": ARCHIVE_T_NAME,
                "archive_sha256": ARCHIVE_T_SHA256,
                "bundle_member": ARCHIVE_T_BUNDLE_MEMBER,
                "bundle_sha256": t_bundle_sha,
                "purpose": "Retroactive D094 N>=4 APOGEE-2 campaigns (5 stars) for DRIFT_V54_COHERENT_SHIFT_STACK",
            },
        ],
        "locked_v54_parameters": det.BASE_V5_4_CONFIG,
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
        "schema": "D096_STAGE1_LOCK_RECEIPT",
        "phase_id": "D096",
        "locked_utc": locked_utc,
        "inputs_d096_v5_4_exists": False,
        "method_lock_sha256": sha256_file(WS / "METHOD_LOCK.json"),
        "frozen_cohort_sha256": hashes["FROZEN_COHORT_D096.csv"],
        "projected_download_mib": round(tot_mib, 3),
        "n_input_files": len(cohort_rows),
        "n_unique_new_stars": len(unique_new_coords),
        "n_prior_bridge_stars": len(prior_bridges_d096),
        "n_orbital_campaigns": len(orbital_campaigns),
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lock_receipt, indent=2) + "\n", encoding="utf-8")

    print(
        f"STAGE-1 SEALED: {len(all_stars_d096)} D096 stars ({len(unique_new_coords)} brand-new, "
        f"{len(prior_bridges_d096)} prior bridges, {new_10pc} new <10pc), {len(cohort_rows)} input files "
        f"({tot_mib:.2f} MiB), min_prior_sep={min_brand_new_sep:.2f}\", {len(orbital_campaigns)} orbital campaigns (#134-#138).",
        flush=True,
    )


if __name__ == "__main__":
    main()
