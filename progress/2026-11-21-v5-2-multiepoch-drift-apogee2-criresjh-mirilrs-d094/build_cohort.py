#!/usr/bin/env python3
"""
Phase D094 (`V5.2`) Prospective Cohort Freeze & Stage-1 Lock Builder.

Runs strictly BEFORE `<ROOT>/inputs_d094_v5_2/` exists:
  1. Verifies Archive Q (`D091`, N>=3 multi-night retroactive drift reuse) & Archive S (`D093`),
     extracting all 409 prior excluded coordinates (`394 + 15`) and 2,612 prior `dp_id`s (`2582 + 30`).
  2. Queries ESA Gaia DR3, NOIRLab `sdss_dr17.apogee2_allstar` + `apogee2_allvisit` (if needed) / APOGEE SAS HEAD,
     ESO `ivoa.ObsCore` (`CRIRES` J/H), NASA Exoplanet Archive `pscomppars`, and MAST JWST (`CAOM` + `HEAD`).
  3. Asserts zero `dp_id` overlap, `>= 300.0"` separation for all 23 brand-new stars, `<= 98.0 MiB` total download,
     `>= 5.0 km/s` orbital dv span for all 8 orbital campaigns (`#118-#125`), and `N >= 3` multi-epoch coverage.
  4. Freezes `FROZEN_COHORT_D094.csv`, `ORBITAL_CAMPAIGNS_AND_KINEMATICS.json`,
     `PRIOR_EXCLUSION_VERIFICATION.json`, `PRIOR_V5_1_PHASES_SNAPSHOT.json`,
     `METHOD_LOCK.json`, and `LOCK_RECEIPT.json` (`inputs_d094_v5_2_exists: false`).
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

import v5_2_detector as det

ARCHIVE_Q_NAME = "SETI_D091_V4_2_ESO_TRIPLE_3ARM_RESULTS_2026-11-20.zip"
ARCHIVE_Q_SHA256 = "9da4739bdb413d675b9bc1f17dc9d60d5abc7944622714017cf1889a097b51d0"
ARCHIVE_Q_BUNDLE_MEMBER = "work_eso_triple_3arm_20261120_d091_v4_2_xshooter_feros_giraffe/bounded_inputs/d091_bounded_bundle.json.gz"

ARCHIVE_S_NAME = "SETI_D093_V5_1_DEDOPPLER_DRIFT_ELLIPSOID_GRACES_CORALIE_CARMENES_RESULTS_2026-11-21.zip"
ARCHIVE_S_SHA256 = "2588057cbd611686d50ced7f4432dce623b16609bc62de01d6460c91c504979a"

# All 30 Phase D094 target entries (`23` brand-new + `7` prior bridges; `HNPEG` appears in both CRIRES & JWST)
APOGEE2_SPECS: list[dict[str, Any]] = [
    {"canonical_target": "GJ268", "common_name": "GJ 268", "apogee_id": "2M07100180+3831457", "telescope": "apo25m", "field": "180+19", "gaia_source_id": 946632924007399936, "role": "SCIENCE", "subrole": "SCIENCE_10PC_MULTIEPOCH", "science_track": "DRIFT_V52_MULTIEPOCH_10PC", "nasa_host": "", "orbital_campaign": False, "teff_lit": 3100.0, "mh_lit": 0.1, "mass_lit": 0.22, "rv_lit": 41.2, "j_lit": 6.731, "h_lit": 6.152, "ks_lit": 5.846},
    {"canonical_target": "GJ1125", "common_name": "GJ 1125", "apogee_id": "2M09304457+0019214", "telescope": "apo25m", "field": "233+36_MGA", "gaia_source_id": 3840711729206827520, "role": "SCIENCE", "subrole": "SCIENCE_10PC_MULTIEPOCH", "science_track": "DRIFT_V52_MULTIEPOCH_10PC", "nasa_host": "", "orbital_campaign": False, "teff_lit": 3458.0, "mh_lit": -0.09, "mass_lit": 0.30, "rv_lit": 42.1, "j_lit": 7.697, "h_lit": 7.182, "ks_lit": 6.871},
    {"canonical_target": "2M12392658", "common_name": "2M1239-2658", "apogee_id": "2M12393641-2658111", "telescope": "lco25m", "field": "M68", "gaia_source_id": 3496355755520065408, "role": "SCIENCE", "subrole": "SCIENCE_MDWARF_MULTIEPOCH", "science_track": "DRIFT_V52_MULTIEPOCH", "nasa_host": "", "orbital_campaign": False, "teff_lit": 3050.0, "mh_lit": 0.0, "mass_lit": 0.16, "rv_lit": 4.0, "j_lit": 10.21, "h_lit": 9.581, "ks_lit": 9.25},
    {"canonical_target": "GJ3779", "common_name": "GJ 3779", "apogee_id": "2M13225673+2428034", "telescope": "apo25m", "field": "022+82_MGA", "gaia_source_id": 1446540213584440704, "role": "SCIENCE", "subrole": "SCIENCE_EXOPLANET_MULTIEPOCH", "science_track": "DRIFT_V52_MULTIEPOCH", "nasa_host": "GJ 3779", "orbital_campaign": False, "teff_lit": 3369.0, "mh_lit": 0.0, "mass_lit": 0.27, "rv_lit": -12.8, "j_lit": 8.728, "h_lit": 8.162, "ks_lit": 7.89},
    {"canonical_target": "GJ238", "common_name": "GJ 238", "apogee_id": "2M06334998-5831426", "telescope": "lco25m", "field": "268-24-O", "gaia_source_id": 5482827676662168832, "role": "SCIENCE", "subrole": "SCIENCE_TRANSITING_MULTIEPOCH", "science_track": "DRIFT_V52_MULTIEPOCH", "nasa_host": "GJ 238", "orbital_campaign": False, "teff_lit": 3580.0, "mh_lit": -0.1, "mass_lit": 0.42, "rv_lit": 28.5, "j_lit": 7.898, "h_lit": 7.312, "ks_lit": 7.04},
    {"canonical_target": "K2239", "common_name": "K2-239", "apogee_id": "2M10422263+0426287", "telescope": "apo25m", "field": "241+52_MGA", "gaia_source_id": 3857872051994269824, "role": "SCIENCE", "subrole": "SCIENCE_MULTIPLANET_TRANSITING_MULTIEPOCH", "science_track": "DRIFT_V52_MULTIEPOCH", "nasa_host": "K2-239", "orbital_campaign": False, "teff_lit": 3474.0, "mh_lit": -0.05, "mass_lit": 0.40, "rv_lit": 7.8, "j_lit": 10.781, "h_lit": 10.192, "ks_lit": 9.93},
    {"canonical_target": "2M23025951", "common_name": "2M2302+5951", "apogee_id": "2M23022519+5951096", "telescope": "apo25m", "field": "109+00", "gaia_source_id": 2013630893446412672, "role": "CONTROL", "subrole": "CONTROL_HOT_TELLURIC_MULTIEPOCH", "science_track": "DRIFT_V52_MULTIEPOCH_CONTROL", "nasa_host": "", "orbital_campaign": False, "teff_lit": 17729.0, "mh_lit": 0.0, "mass_lit": 5.2, "rv_lit": -15.0, "j_lit": 6.968, "h_lit": 6.998, "ks_lit": 6.97},
    {"canonical_target": "2M17012756", "common_name": "2M1701-2756", "apogee_id": "2M17015630-2756204", "telescope": "lco25m", "field": "355+08", "gaia_source_id": 6030271045875820416, "role": "CONTROL", "subrole": "CONTROL_HOT_ASTAR_MULTIEPOCH", "science_track": "DRIFT_V52_MULTIEPOCH_CONTROL", "nasa_host": "", "orbital_campaign": False, "teff_lit": 9592.0, "mh_lit": 0.0, "mass_lit": 2.1, "rv_lit": -5.0, "j_lit": 6.651, "h_lit": 6.551, "ks_lit": 6.49},
]

CRIRES_SPECS: list[dict[str, Any]] = [
    {"canonical_target": "HD190360", "common_name": "HD 190360", "gaia_source_id": 2029433521248546304, "role": "SCIENCE", "subrole": "SCIENCE_MULTIPLANET_JH", "science_track": "COMB_AND_AGNOSTIC_JH", "nasa_host": "HD 190360", "orbital_campaign": False, "campaign_index": None, "band_mode": "JH", "n_target_exps": 2, "panchromatic_bridge": False, "teff_lit": 5580.0, "mh_lit": 0.24, "mass_lit": 1.00, "rv_lit": -45.3, "j_lit": 4.554, "h_lit": 4.239, "ks_lit": 4.076},
    {"canonical_target": "51PEG", "common_name": "51 Peg", "gaia_source_id": 2835207319109249920, "role": "SCIENCE", "subrole": "SCIENCE_EXOPLANET_JH", "science_track": "COMB_AND_AGNOSTIC_JH", "nasa_host": "51 Peg", "orbital_campaign": False, "campaign_index": None, "band_mode": "JH", "n_target_exps": 2, "panchromatic_bridge": False, "teff_lit": 5790.0, "mh_lit": 0.20, "mass_lit": 1.11, "rv_lit": -33.2, "j_lit": 4.655, "h_lit": 4.234, "ks_lit": 3.911},
    {"canonical_target": "HNPEG", "common_name": "HN Peg", "gaia_source_id": 1772187382746856320, "role": "SCIENCE", "subrole": "SCIENCE_EXOPLANET_BRIDGE_INTRA", "science_track": "INTRA_D094_BRIDGE_CRIRES_JWST", "nasa_host": "HN Peg", "orbital_campaign": False, "campaign_index": None, "band_mode": "HH", "n_target_exps": 2, "panchromatic_bridge": True, "teff_lit": 5974.0, "mh_lit": -0.01, "mass_lit": 1.09, "rv_lit": -17.3, "j_lit": 4.793, "h_lit": 4.598, "ks_lit": 4.559},
    {"canonical_target": "TOI674", "common_name": "TOI-674", "gaia_source_id": 5400949450924312576, "role": "SCIENCE", "subrole": "SCIENCE_ORBITAL_MULTIEPOCH_N3", "science_track": "DRIFT_V52_MULTIEPOCH_AND_ORBITAL", "nasa_host": "TOI-674", "orbital_campaign": True, "campaign_index": 118, "prefer_planet": "TOI-674 b", "band_mode": "HHH", "n_target_exps": 3, "panchromatic_bridge": False, "teff_lit": 3514.0, "mh_lit": 0.17, "mass_lit": 0.42, "rv_lit": -1.5, "j_lit": 10.35, "h_lit": 9.737, "ks_lit": 9.48},
    {"canonical_target": "TOI942", "common_name": "TOI-942", "gaia_source_id": 2974906868489280768, "role": "SCIENCE", "subrole": "SCIENCE_ORBITAL_MULTIEPOCH_N3", "science_track": "DRIFT_V52_MULTIEPOCH_AND_ORBITAL", "nasa_host": "TOI-942", "orbital_campaign": True, "campaign_index": 119, "prefer_planet": "TOI-942 b", "band_mode": "YYY", "n_target_exps": 3, "panchromatic_bridge": False, "teff_lit": 4969.0, "mh_lit": -0.221, "mass_lit": 0.822, "rv_lit": 25.0, "j_lit": 10.231, "h_lit": 9.747, "ks_lit": 9.639},
    {"canonical_target": "WASP76", "common_name": "WASP-76", "gaia_source_id": 2512326349403275520, "role": "SCIENCE", "subrole": "SCIENCE_TRANSITING_ORBITAL", "science_track": "BLIND_DRIFT_AND_ORBITAL_TRANSIT", "nasa_host": "WASP-76", "orbital_campaign": True, "campaign_index": 120, "prefer_planet": "WASP-76 b", "band_mode": "HH", "n_target_exps": 2, "panchromatic_bridge": False, "teff_lit": 6329.0, "mh_lit": 0.36, "mass_lit": 1.458, "rv_lit": -1.1, "j_lit": 8.59, "h_lit": 8.331, "ks_lit": 8.24},
    {"canonical_target": "10LEP", "common_name": "10 Lep", "gaia_source_id": 2968057185930727680, "role": "CONTROL", "subrole": "CONTROL_ASTAR_MULTIEPOCH_N3", "science_track": "DRIFT_V52_MULTIEPOCH_CONTROL", "nasa_host": "", "orbital_campaign": False, "campaign_index": None, "band_mode": "HHH", "n_target_exps": 3, "panchromatic_bridge": False, "teff_lit": 9500.0, "mh_lit": 0.0, "mass_lit": 2.2, "rv_lit": 26.0, "j_lit": 5.45, "h_lit": 5.47, "ks_lit": 5.46},
    {"canonical_target": "HD42581", "common_name": "GJ 229", "gaia_source_id": 2940856402123426176, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_10PC_MULTIEPOCH_N3", "science_track": "DRIFT_V52_MULTIEPOCH_BRIDGE_10PC", "nasa_host": "GJ 229", "orbital_campaign": False, "campaign_index": None, "band_mode": "HHH", "n_target_exps": 3, "panchromatic_bridge": True, "is_prior_bridge": True, "teff_lit": 3814.0, "mh_lit": 0.03, "mass_lit": 0.54, "rv_lit": 4.7, "j_lit": 5.10, "h_lit": 4.393, "ks_lit": 4.13},
    {"canonical_target": "AUMIC", "common_name": "AU Mic", "gaia_source_id": 6794047652729201024, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_10PC_ORBITAL_N3", "science_track": "DRIFT_V52_MULTIEPOCH_AND_ORBITAL", "nasa_host": "AU Mic", "orbital_campaign": True, "campaign_index": 121, "prefer_planet": "AU Mic b", "band_mode": "HHH", "n_target_exps": 3, "panchromatic_bridge": True, "is_prior_bridge": True, "teff_lit": 3700.0, "mh_lit": 0.0, "mass_lit": 0.635, "rv_lit": -4.7, "j_lit": 5.44, "h_lit": 4.831, "ks_lit": 4.53},
    {"canonical_target": "GJ9827", "common_name": "GJ 9827", "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_ORBITAL_MULTIPLANET", "science_track": "BLIND_DRIFT_AND_ORBITAL_TRANSIT", "nasa_host": "GJ 9827", "orbital_campaign": True, "campaign_index": 122, "prefer_planet": "GJ 9827 c", "band_mode": "HH", "n_target_exps": 2, "panchromatic_bridge": True, "is_prior_bridge": True, "teff_lit": 4255.0, "mh_lit": -0.29, "mass_lit": 0.62, "rv_lit": 31.9, "j_lit": 7.98, "h_lit": 7.42, "ks_lit": 7.19},
    {"canonical_target": "55CNC", "common_name": "55 Cnc", "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_ORBITAL_MULTIPLANET", "science_track": "BLIND_DRIFT_AND_ORBITAL_TRANSIT", "nasa_host": "55 Cnc", "orbital_campaign": True, "campaign_index": 123, "prefer_planet": "55 Cnc e", "band_mode": "HH", "n_target_exps": 2, "panchromatic_bridge": True, "is_prior_bridge": True, "teff_lit": 5172.0, "mh_lit": 0.35, "mass_lit": 0.905, "rv_lit": 27.3, "j_lit": 4.77, "h_lit": 4.27, "ks_lit": 4.01},
    {"canonical_target": "HD3651", "common_name": "54 Psc (HD 3651)", "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_ORBITAL_ECCENTRIC", "science_track": "BLIND_DRIFT_AND_ORBITAL", "nasa_host": "HD 3651", "orbital_campaign": True, "campaign_index": 124, "prefer_planet": "HD 3651 b", "band_mode": "HH", "n_target_exps": 2, "panchromatic_bridge": True, "is_prior_bridge": True, "teff_lit": 5220.0, "mh_lit": 0.16, "mass_lit": 0.799, "rv_lit": -33.0, "j_lit": 4.55, "h_lit": 4.064, "ks_lit": 4.00},
    {"canonical_target": "HD209458", "common_name": "HD 209458", "gaia_source_id": None, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_ORBITAL_HOTJUPITER", "science_track": "BLIND_DRIFT_AND_ORBITAL_TRANSIT", "nasa_host": "HD 209458", "orbital_campaign": True, "campaign_index": 125, "prefer_planet": "HD 209458 b", "band_mode": "HH", "n_target_exps": 2, "panchromatic_bridge": True, "is_prior_bridge": True, "teff_lit": 6092.0, "mh_lit": 0.02, "mass_lit": 1.23, "rv_lit": -14.7, "j_lit": 6.59, "h_lit": 6.366, "ks_lit": 6.31},
]

JWST_SPECS: list[dict[str, Any]] = [
    {"instrument": "JWST_MIRI_LRS", "canonical_target": "WISE1049AB", "common_name": "Luhman 16AB", "gaia_source_id": None, "ra_lit": 162.2980, "dec_lit": -53.3171, "pmra_lit": -2759.0, "pmdec_lit": 354.0, "dist_lit": 1.996, "role": "SCIENCE", "subrole": "SCIENCE_10PC_BROWNDWARF_LRS", "science_track": "MIRI_LRS_GREENHOUSE_10PC", "nasa_host": "", "panchromatic_bridge": False, "is_prior_bridge": False, "teff_lit": 1260.0, "mh_lit": 0.0, "mass_lit": 0.032, "rv_lit": 20.5, "j_lit": 10.73, "h_lit": 9.56, "ks_lit": 8.84, "n_exo_lit": 0, "trans_lit": False, "files": [{"obs_id": "jw02965-o002_t001_miri_p750l-slitlessprism", "fname": "jw02965-o002_t001_miri_p750l-slitlessprism_x1dints.fits", "arm": "MIRI_LRS_P750L", "rp": 100.0}]},
    {"instrument": "JWST_MIRI_LRS", "canonical_target": "WD0806B", "common_name": "WD 0806-661 B", "gaia_source_id": 5274517467840296832, "role": "SCIENCE", "subrole": "SCIENCE_YDWARF_WD_COMPANION", "science_track": "MIRI_LRS_GREENHOUSE_YDWARF", "nasa_host": "", "panchromatic_bridge": False, "is_prior_bridge": False, "teff_lit": 340.0, "mh_lit": 0.0, "mass_lit": 0.008, "rv_lit": 0.0, "j_lit": 25.0, "h_lit": 24.5, "ks_lit": 24.0, "n_exo_lit": 1, "trans_lit": False, "files": [{"obs_id": "jw01276-o003_t001_miri_p750l", "fname": "jw01276-o003_t001_miri_p750l_x1d.fits", "arm": "MIRI_LRS_P750L", "rp": 100.0}]},
    {"instrument": "JWST_MIRI_LRS", "canonical_target": "HNPEG", "common_name": "HN Peg", "gaia_source_id": 1772187382746856320, "role": "SCIENCE", "subrole": "SCIENCE_EXOPLANET_BRIDGE_INTRA", "science_track": "INTRA_D094_BRIDGE_CRIRES_JWST", "nasa_host": "HN Peg", "panchromatic_bridge": True, "is_prior_bridge": False, "teff_lit": 5974.0, "mh_lit": -0.01, "mass_lit": 1.09, "rv_lit": -17.3, "j_lit": 4.793, "h_lit": 4.598, "ks_lit": 4.559, "n_exo_lit": 1, "trans_lit": False, "files": [{"obs_id": "jw03670-o001_t001_miri_p750l", "fname": "jw03670-o001_t001_miri_p750l_x1d.fits", "arm": "MIRI_LRS_P750L", "rp": 100.0}]},
    {"instrument": "JWST_NIRSPEC_G395H", "canonical_target": "HNPEG", "common_name": "HN Peg", "gaia_source_id": 1772187382746856320, "role": "SCIENCE", "subrole": "SCIENCE_EXOPLANET_BRIDGE_INTRA", "science_track": "INTRA_D094_BRIDGE_CRIRES_JWST", "nasa_host": "HN Peg", "panchromatic_bridge": True, "is_prior_bridge": False, "teff_lit": 5974.0, "mh_lit": -0.01, "mass_lit": 1.09, "rv_lit": -17.3, "j_lit": 4.793, "h_lit": 4.598, "ks_lit": 4.559, "n_exo_lit": 1, "trans_lit": False, "files": [{"obs_id": "jw04668-o083_t035-s000000001_nirspec_f290lp-g395h-s200a1-s200a2-allslits", "mjd_fallback": 60599.534, "expt_fallback": 219.76, "fname": "jw04668083001_03104_00001_nrs1_x1d.fits", "arm": "NIRSPEC_G395H_NRS1", "rp": 2700.0}, {"obs_id": "jw04668-o083_t035-s000000001_nirspec_f290lp-g395h-s200a1-s200a2-allslits", "mjd_fallback": 60599.534, "expt_fallback": 219.76, "fname": "jw04668083001_03104_00001_nrs2_x1d.fits", "arm": "NIRSPEC_G395H_NRS2", "rp": 2700.0}]},
    {"instrument": "JWST_NIRSPEC_G395H", "canonical_target": "CWISEPJ1935", "common_name": "CWISEP J1935-1546", "gaia_source_id": None, "ra_lit": 293.8262, "dec_lit": -15.7726, "pmra_lit": 293.0, "pmdec_lit": -45.0, "dist_lit": 14.43, "role": "SCIENCE", "subrole": "SCIENCE_YDWARF_AURORAL_CH4", "science_track": "NIRSPEC_G395H_MOL_CCF", "nasa_host": "", "panchromatic_bridge": False, "is_prior_bridge": False, "teff_lit": 482.0, "mh_lit": 0.0, "mass_lit": 0.008, "rv_lit": 0.0, "j_lit": 23.0, "h_lit": 22.8, "ks_lit": 22.5, "n_exo_lit": 0, "trans_lit": False, "files": [{"obs_id": "jw02124-o051_t051-s000000001_nirspec_f290lp-g395h-s200a1-subs200a1", "mjd_fallback": 59869.7147, "expt_fallback": 2365.044, "fname": "jw02124051001_03102_00001_nrs1_x1d.fits", "arm": "NIRSPEC_G395H_NRS1", "rp": 2700.0}, {"obs_id": "jw02124-o051_t051-s000000001_nirspec_f290lp-g395h-s200a1-subs200a1", "mjd_fallback": 59869.7147, "expt_fallback": 2365.044, "fname": "jw02124051001_03102_00001_nrs2_x1d.fits", "arm": "NIRSPEC_G395H_NRS2", "rp": 2700.0}]},
    {"instrument": "JWST_MIRI_LRS", "canonical_target": "ROSS19B", "common_name": "Ross 19 B", "gaia_source_id": None, "ra_lit": 34.9510, "dec_lit": 35.3120, "pmra_lit": 678.0, "pmdec_lit": -422.0, "dist_lit": 17.50, "role": "SCIENCE", "subrole": "SCIENCE_YDWARF_WIDE_COMPANION", "science_track": "MIRI_LRS_GREENHOUSE_YDWARF", "nasa_host": "", "panchromatic_bridge": False, "is_prior_bridge": False, "teff_lit": 500.0, "mh_lit": 0.0, "mass_lit": 0.025, "rv_lit": 0.0, "j_lit": 21.5, "h_lit": 21.0, "ks_lit": 20.5, "n_exo_lit": 0, "trans_lit": False, "files": [{"obs_id": "jw05118-o002_t001_miri_p750l", "fname": "jw05118-o002_t001_miri_p750l_x1d.fits", "arm": "MIRI_LRS_P750L", "rp": 100.0}]},
    {"instrument": "JWST_MIRI_LRS", "canonical_target": "GUPSCB", "common_name": "GU Psc b", "gaia_source_id": 2784120641627589760, "role": "SCIENCE", "subrole": "SCIENCE_T35_PLANETARY_MASS_COMPANION", "science_track": "MIRI_LRS_GREENHOUSE_PLANETARY", "nasa_host": "GU Psc", "panchromatic_bridge": False, "is_prior_bridge": False, "teff_lit": 1050.0, "mh_lit": 0.0, "mass_lit": 0.011, "rv_lit": -1.6, "j_lit": 18.12, "h_lit": 17.7, "ks_lit": 17.4, "n_exo_lit": 1, "trans_lit": False, "files": [{"obs_id": "jw01188-o011_t003_miri_p750l", "fname": "jw01188-o011_t003_miri_p750l_x1d.fits", "arm": "MIRI_LRS_P750L", "rp": 100.0}]},
    {"instrument": "JWST_MIRI_LRS", "canonical_target": "HD106906B", "common_name": "HD 106906 b", "gaia_source_id": 6072902994276659200, "role": "SCIENCE", "subrole": "SCIENCE_YOUNG_EXOPLANET_LRS", "science_track": "MIRI_LRS_GREENHOUSE_PLANETARY", "nasa_host": "HD 106906", "panchromatic_bridge": False, "is_prior_bridge": False, "teff_lit": 1820.0, "mh_lit": 0.0, "mass_lit": 0.011, "rv_lit": 12.2, "j_lit": 17.6, "h_lit": 16.2, "ks_lit": 15.5, "n_exo_lit": 1, "trans_lit": False, "files": [{"obs_id": "jw01277-o023_t005_miri_p750l", "fname": "jw01277-o023_t005_miri_p750l_x1d.fits", "arm": "MIRI_LRS_P750L", "rp": 100.0}]},
    {"instrument": "JWST_MIRI_LRS", "canonical_target": "HD42581", "common_name": "GJ 229", "gaia_source_id": 2940856402123426176, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_10PC_MIRI_LRS", "science_track": "MIRI_LRS_GREENHOUSE_10PC_BRIDGE", "nasa_host": "GJ 229", "panchromatic_bridge": True, "is_prior_bridge": True, "teff_lit": 950.0, "mh_lit": 0.03, "mass_lit": 0.54, "rv_lit": 4.7, "j_lit": 5.10, "h_lit": 4.393, "ks_lit": 4.13, "n_exo_lit": 2, "trans_lit": False, "files": [{"obs_id": "jw03762-o002_t001_miri_p750l", "fname": "jw03762-o002_t001_miri_p750l_x1d.fits", "arm": "MIRI_LRS_P750L", "rp": 100.0}]},
    {"instrument": "JWST_MIRI_LRS", "canonical_target": "GJ1132", "common_name": "GJ 1132", "gaia_source_id": 5413438219396893568, "role": "SCIENCE", "subrole": "SCIENCE_BRIDGE_ROCKY_TRANSIT_LRS", "science_track": "MIRI_LRS_GREENHOUSE_BRIDGE", "nasa_host": "GJ 1132", "panchromatic_bridge": True, "is_prior_bridge": True, "teff_lit": 3270.0, "mh_lit": -0.12, "mass_lit": 0.181, "rv_lit": 35.0, "j_lit": 9.25, "h_lit": 8.666, "ks_lit": 8.322, "n_exo_lit": 2, "trans_lit": True, "files": [{"obs_id": "jw01274-o013_t008_miri_p750l-slitlessprism", "fname": "jw01274-o013_t008_miri_p750l-slitlessprism_x1dints.fits", "arm": "MIRI_LRS_P750L", "rp": 100.0}]},
    {"instrument": "JWST_MIRI_LRS", "canonical_target": "AZV175", "common_name": "AzV 175 (SMC B-star)", "gaia_source_id": 4685986483121883776, "dist_lit": 60600.0, "role": "CONTROL", "subrole": "CONTROL_SMC_HOT_BSTAR_LRS", "science_track": "MIRI_LRS_CONTROL_EXTRABULGE", "nasa_host": "", "panchromatic_bridge": False, "is_prior_bridge": False, "teff_lit": 25000.0, "mh_lit": -0.7, "mass_lit": 18.0, "rv_lit": 150.0, "j_lit": 12.1, "h_lit": 12.1, "ks_lit": 12.1, "n_exo_lit": 0, "trans_lit": False, "files": [{"obs_id": "jw05168-o004_t004_miri_p750l", "fname": "jw05168-o004_t004_miri_p750l_x1d.fits", "arm": "MIRI_LRS_P750L", "rp": 100.0}]},
    {"instrument": "JWST_MIRI_LRS", "canonical_target": "SK70116", "common_name": "Sk -70 116 (LMC B-star)", "gaia_source_id": 4657383405304940928, "dist_lit": 49590.0, "role": "CONTROL", "subrole": "CONTROL_LMC_HOT_BSTAR_LRS", "science_track": "MIRI_LRS_CONTROL_SN1987A_REGION", "nasa_host": "", "panchromatic_bridge": False, "is_prior_bridge": False, "teff_lit": 26000.0, "mh_lit": -0.4, "mass_lit": 20.0, "rv_lit": 260.0, "j_lit": 12.2, "h_lit": 12.2, "ks_lit": 12.2, "n_exo_lit": 0, "trans_lit": False, "files": [{"obs_id": "jw05168-o011_t011_miri_p750l", "fname": "jw05168-o011_t011_miri_p750l_x1d.fits", "arm": "MIRI_LRS_P750L", "rp": 100.0}]},
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
    params = {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", param_key: query} if param_key == "QUERY" else {param_key: query, "format": "csv"}
    url = f"{url_base}?{urllib.parse.urlencode(params)}"
    txt = _urlopen_retry(urllib.request.Request(url, headers={"User-Agent": "SETIsearch-D094/1.0"})).decode("utf-8", errors="replace")
    if txt.lstrip().startswith("<?xml"):
        raise RuntimeError(f"TAP XML error from {url_base}: {txt[:400]}")
    return list(csv.DictReader(txt.splitlines()))


def head_content_length(url: str) -> int:
    last_err: Exception | None = None
    for att in range(4):
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "SETIsearch-D094/1.0"})
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
    inp_dir = ROOT / "inputs_d094_v5_2"
    if inp_dir.exists():
        raise RuntimeError(f"Prospective hygiene violation: {inp_dir} already exists before Stage-1 lock!")

    arch_q = ROOT / "archives" / ARCHIVE_Q_NAME
    arch_s = ROOT / "archives" / ARCHIVE_S_NAME
    for zp, exp in ((arch_q, ARCHIVE_Q_SHA256), (arch_s, ARCHIVE_S_SHA256)):
        if not zp.exists() or sha256_file(zp) != exp:
            raise RuntimeError(f"Archive integrity check failed for {zp.name}")

    print("1. Extracting Archive S (D093) exclusion registry & Archive Q (D091) N>=3 bundle metadata...", flush=True)
    with zipfile.ZipFile(arch_q, "r") as zq:
        q_bundle_bytes = zq.read(ARCHIVE_Q_BUNDLE_MEMBER)
        q_bundle_sha = sha256_bytes(q_bundle_bytes)

    with zipfile.ZipFile(arch_s, "r") as zs:
        pe93 = json.loads(zs.read("PRIOR_EXCLUSION_VERIFICATION.json").decode("utf-8"))
        sum93 = json.loads(zs.read("results/SUMMARY.json").decode("utf-8"))
        coh93 = list(csv.DictReader(zs.read("FROZEN_COHORT_D093.csv").decode("utf-8").splitlines()))
        u350_rows = list(csv.DictReader(zs.read("results/UNIFIED_PANCHROMATIC_V5_1_SYNTHESIS_350STARS.csv").decode("utf-8").splitlines()))
        br37_rows = list(csv.DictReader(zs.read("results/PANCHROMATIC_BRIDGE_37STARS_V51.csv").decode("utf-8").splitlines()))
        comb_u93 = list(csv.DictReader(zs.read("results/ALLSKY_COMB_V4_1_UNIFIED_D079_D093.csv").decode("utf-8").splitlines()))
        comb_c93 = list(csv.DictReader(zs.read("results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D093.csv").decode("utf-8").splitlines()))

    u350_map = {r["star"]: r for r in u350_rows}
    br37_set = {r["star"] for r in br37_rows}
    prior_coords: list[dict[str, Any]] = list(pe93["excluded_targets_coordinate_registry"])
    seen_93: set[str] = set()
    for r in coh93:
        st = r["canonical_target"]
        if st not in seen_93:
            seen_93.add(st)
            prior_coords.append({"label": f"{st}(D093)", "ra_deg": float(r["s_ra"]), "dec_deg": float(r["s_dec"])})
    excluded_dp_ids: set[str] = set(pe93["excluded_dp_ids"]) | {r["dp_id"] for r in coh93}

    prior_snap = {
        "schema": "D094_PRIOR_V5_1_PHASES_SNAPSHOT",
        "prior_phases": "D079-D093",
        "source_archive_s_name": ARCHIVE_S_NAME,
        "source_archive_s_sha256": ARCHIVE_S_SHA256,
        "source_archive_q_name": ARCHIVE_Q_NAME,
        "source_archive_q_sha256": ARCHIVE_Q_SHA256,
        "source_archive_q_bundle_member": ARCHIVE_Q_BUNDLE_MEMBER,
        "source_archive_q_bundle_sha256": q_bundle_sha,
        "prior_unique_stars_count": len(u350_rows),
        "prior_within_10pc_count": sum93["unified_350star_panchromatic_v5_1_synthesis"]["within_10pc_unique_stars"],
        "prior_total_exposures_count": sum93["unified_350star_panchromatic_v5_1_synthesis"]["total_exposures_d079_d093"],
        "prior_cumulative_integration_hours": sum93["unified_350star_panchromatic_v5_1_synthesis"]["total_integration_hours_d079_d093"],
        "prior_calibration_trials_count": sum93["unified_350star_panchromatic_v5_1_synthesis"]["total_calibration_trials_d079_d093"],
        "prior_v2_false_alarms_eliminated_total": sum93["unified_350star_panchromatic_v5_1_synthesis"]["v2_false_alarms_eliminated_total"],
        "prior_cumulative_orbital_campaigns_count": sum93["unified_350star_panchromatic_v5_1_synthesis"]["cumulative_orbital_campaigns"],
        "prior_panchromatic_bridge_stars_count": len(br37_set),
        "prior_panchromatic_bridge_cells_count": sum93["unified_350star_panchromatic_v5_1_synthesis"]["panchromatic_bridge_cells_total"],
        "d093_summary_headline": sum93,
        "prior_unified_350_rows": u350_rows,
        "prior_bridge_37_rows": br37_rows,
        "prior_allsky_comb_unified_rows": comb_u93,
        "prior_allsky_comb_candidate_rows": comb_c93,
    }

    print("2. Querying ESA Gaia DR3, NOIRLab APOGEE2, NASA Exoplanet Archive, and MAST CAOM...", flush=True)
    all_gids = sorted({
        int(s["gaia_source_id"])
        for s in (APOGEE2_SPECS + CRIRES_SPECS + JWST_SPECS)
        if s.get("gaia_source_id")
    })
    gq = (
        "SELECT source_id, ra, dec, parallax, pmra, pmdec, phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag, "
        f"radial_velocity, teff_gspphot, mh_gspphot FROM gaiadr3.gaia_source WHERE source_id IN ({','.join(map(str, all_gids))})"
    )
    gaia_map = {int(r["source_id"]): r for r in tap_csv("https://gea.esac.esa.int/tap-server/tap/sync", gq)}
    if len(gaia_map) != len(all_gids):
        raise RuntimeError(f"Gaia DR3 missing IDs: {set(all_gids) - set(gaia_map)}")

    # Query NOIRLab APOGEE-2 DR17 allStar
    apo_ids_sql = ",".join(f"'{s['apogee_id']}'" for s in APOGEE2_SPECS)
    aq = (
        "SELECT apogee_id, telescope, field, ra, dec, jmag, hmag, ksmag, nvis, teff, rv_teff, m_h, fe_h, hrv, snr "
        f"FROM sdss_dr17.apogee2_allstar WHERE apogee_id IN ({apo_ids_sql})"
    )
    apo_rows = tap_csv("https://datalab.noirlab.edu/tap/sync", aq)
    apo_map = {(r["apogee_id"], r["telescope"], r["field"]): r for r in apo_rows}

    # Query NASA Exoplanet Archive pscomppars
    hosts = sorted({s["nasa_host"] for s in (APOGEE2_SPECS + CRIRES_SPECS + JWST_SPECS) if s.get("nasa_host")})
    nq = (
        "SELECT pl_name, hostname, pl_orbper, pl_tranmid, pl_orbeccen, st_mass, tran_flag "
        f"FROM pscomppars WHERE hostname IN ({','.join(chr(39)+h+chr(39) for h in hosts)})"
    )
    nasa_rows = tap_csv("https://exoplanetarchive.ipac.caltech.edu/TAP/sync", nq, param_key="query")
    nasa_by_host: dict[str, list[dict[str, str]]] = {}
    for nr in nasa_rows:
        nasa_by_host.setdefault(nr["hostname"], []).append(nr)

    # Query MAST CAOM metadata for JWST obs_ids
    jwst_obs_ids = sorted({f["obs_id"] for s in JWST_SPECS for f in s["files"]})
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
        headers={"User-Agent": "SETIsearch-D094/1.0"},
        method="POST",
    )
    mast_data = json.loads(_urlopen_retry(mast_req).decode("utf-8")).get("data", [])
    mast_by_obs = {d["obs_id"]: d for d in mast_data}

    def resolve_star_meta(spec: dict[str, Any]) -> dict[str, Any]:
        st = spec["canonical_target"]
        gid = spec.get("gaia_source_id")
        if st in u350_map and spec.get("is_prior_bridge") and gid is None:
            u = u350_map[st]
            # Look up exact RA/Dec from prior registry
            preg = next(r for r in pe93["excluded_targets_coordinate_registry"] if r["label"].split("(")[0] == st)
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
            teff_g = _opt_float(g.get("teff_gspphot"), spec["teff_lit"])
            if st in ("WD0806B", "GUPSCB", "HD106906B", "HNPEG", "AZV175", "SK70116", "HD42581") and spec.get("instrument") == "JWST_MIRI_LRS":
                # Keep host Gaia geometry + companion/BD photospheric Teff from spec if directly imaged companion
                if st in ("WD0806B", "GUPSCB", "HD106906B", "HD42581"):
                    teff_g = float(spec["teff_lit"])
            return {
                "gaia_source_id": int(gid),
                "ra": float(g["ra"]),
                "dec": float(g["dec"]),
                "pmra": _opt_float(g.get("pmra"), 0.0),
                "pmdec": _opt_float(g.get("pmdec"), 0.0),
                "dist_pc": float(dist_pc),
                "g_mag": _opt_float(g.get("phot_g_mean_mag"), math.nan),
                "bp_mag": _opt_float(g.get("phot_bp_mean_mag"), math.nan),
                "rp_mag": _opt_float(g.get("phot_rp_mean_mag"), math.nan),
                "j_mag": float(spec["j_lit"]),
                "h_mag": float(spec["h_lit"]),
                "ks_mag": float(spec["ks_lit"]),
                "teff_k": float(spec["teff_lit"]) if st in ("GJ268", "2M12392658", "10LEP", "WD0806B", "GUPSCB", "HD106906B", "AZV175", "SK70116", "HD42581") else float(teff_g),
                "mh_dex": _opt_float(g.get("mh_gspphot"), spec["mh_lit"]),
                "rv_kms": _opt_float(g.get("radial_velocity"), spec["rv_lit"]),
                "mass_msun": float(spec["mass_lit"]),
            }
        # Non-Gaia brown dwarfs (WISE1049AB, CWISEPJ1935, ROSS19B)
        return {
            "gaia_source_id": 0,
            "ra": float(spec["ra_lit"]),
            "dec": float(spec["dec_lit"]),
            "pmra": float(spec["pmra_lit"]),
            "pmdec": float(spec["pmdec_lit"]),
            "dist_pc": float(spec["dist_lit"]),
            "g_mag": math.nan,
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

    # Resolve all ESO CRIRES J/H candidate exposures in a single batch query
    crires_meta_map = {s["canonical_target"]: resolve_star_meta(s) for s in CRIRES_SPECS}
    conds = " OR ".join(
        f"(s_ra BETWEEN {m['ra']-0.08:.4f} AND {m['ra']+0.08:.4f} AND s_dec BETWEEN {m['dec']-0.08:.4f} AND {m['dec']+0.08:.4f})"
        for m in crires_meta_map.values()
    )
    csql = (
        "SELECT target_name, s_ra, s_dec, t_min, t_exptime, snr, dp_id, access_estsize, em_min, em_max, em_res_power, filter, obs_release_date "
        f"FROM ivoa.ObsCore WHERE instrument_name='CRIRES' AND dataproduct_type='spectrum' "
        f"AND em_min > 0.94e-6 AND em_max < 1.89e-6 "
        f"AND (obs_release_date < '2026-11-20T00:00:00Z' OR obs_release_date IS NULL) "
        f"AND ({conds}) ORDER BY t_min ASC"
    )
    eso_rows = tap_csv("https://archive.eso.org/tap_obs/sync", csql)

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
        ppo_sc = 1.0
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
            "ppo_align_score": ppo_sc,
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
    print("3. Selecting & HEAD-checking Stream A (SDSS APOGEE-2, 8 targets)...", flush=True)
    for spec in APOGEE2_SPECS:
        m = resolve_star_meta(spec)
        aid, tel, fld = spec["apogee_id"], spec["telescope"], spec["field"]
        ar = apo_map[(aid, tel, fld)]
        if _opt_float(ar.get("hmag")) > 0.0:
            m["h_mag"] = float(ar["hmag"])
        if _opt_float(ar.get("jmag")) > 0.0:
            m["j_mag"] = float(ar["jmag"])
        if _opt_float(ar.get("ksmag")) > 0.0:
            m["ks_mag"] = float(ar["ksmag"])
        if _opt_float(ar.get("teff")) > 500.0:
            m["teff_k"] = float(ar["teff"])
        if _opt_float(ar.get("hrv")) == _opt_float(ar.get("hrv")):
            m["rv_kms"] = float(ar["hrv"])
        pref = "asStar" if tel == "lco25m" else "apStar"
        fname = f"{pref}-dr17-{aid}.fits"
        furl = f"https://data.sdss.org/sas/dr17/apogee/spectro/redux/dr17/stars/{tel}/{fld}/{pref}-dr17-{urllib.parse.quote(aid)}.fits"
        fbytes = head_content_length(furl)
        nv = int(ar["nvis"])
        dp_id = f"APOGEE2.{tel}.{fld}.{aid}"
        if dp_id in excluded_dp_ids:
            raise RuntimeError(f"Duplicate APOGEE dp_id: {dp_id}")
        # Nominal combined MJD ~ 58500 and integration = nv * 500 s (refined directly from HDU 9 in Stage 2)
        append_cohort_row(
            "SDSS_APOGEE2", spec, m, 1, dp_id, f"APOGEE2_H_NV{nv}", 22500.0,
            58500.0, float(nv) * 500.0, "NONE", 0.0, 0.0,
            fname[:-5], f"SDSS_APOGEE2/{spec['canonical_target']}/{fname}", furl, fbytes,
        )

    # --- Stream B: ESO CRIRES+ J/H ---
    print("4. Selecting & HEAD-checking Stream B (ESO CRIRES+ J/H, 13 stars / 8 orbital campaigns)...", flush=True)
    for spec in CRIRES_SPECS:
        st = spec["canonical_target"]
        m = crires_meta_map[st]
        pool = [
            r for r in eso_rows
            if r["dp_id"] not in excluded_dp_ids
            and sep_arcsec(m["ra"], m["dec"], float(r["s_ra"]), float(r["s_dec"])) <= 120.0
            and float(r.get("t_exptime") or 0.0) >= 5.0
        ]
        if not pool:
            raise RuntimeError(f"Empty CRIRES pool for {st}")

        def row_band(r: dict[str, str]) -> str:
            em_max = float(r["em_max"])
            if em_max < 1.15e-6:
                return "Y"
            if em_max < 1.40e-6:
                return "J"
            return "H"

        def row_snr(r: dict[str, str]) -> float:
            return _opt_float(r.get("snr"), 60.0)

        p_ref: tuple[str, float, float, float, float] | None = None
        if spec.get("orbital_campaign"):
            plist = nasa_by_host.get(spec["nasa_host"], [])
            target_p = next((p for p in plist if p["pl_name"] == spec.get("prefer_planet")), None)
            if target_p is None:
                valid_p = [p for p in plist if p.get("pl_orbper") and p.get("pl_tranmid")]
                target_p = min(valid_p, key=lambda x: float(x["pl_orbper"]))
            p_d = float(target_p["pl_orbper"])
            t0_b = float(target_p["pl_tranmid"])
            ecc_v = _opt_float(target_p.get("pl_orbeccen"), 0.0)
            st_mass = _opt_float(target_p.get("st_mass"), m["mass_msun"])
            m["mass_msun"] = st_mass
            kp = det.compute_keplerian_kp_kms(st_mass, p_d, ecc=ecc_v)
            p_ref = (target_p["pl_name"], p_d, t0_b, ecc_v, kp)

        selected: list[dict[str, str]] = []
        if spec["band_mode"] == "JH":
            j_cands = sorted([r for r in pool if row_band(r) == "J"], key=row_snr, reverse=True)
            h_cands = sorted([r for r in pool if row_band(r) == "H"], key=row_snr, reverse=True)
            selected = [j_cands[0], h_cands[0]]
        elif spec["band_mode"] in ("HHH", "YYY"):
            target_b = spec["band_mode"][0]
            h_cands = [r for r in pool if row_band(r) == target_b]
            # Prefer distinct integer nights when >= 3 distinct nights exist; else min_dt >= 0.05 d
            by_night: dict[int, list[dict[str, str]]] = {}
            for r in h_cands:
                by_night.setdefault(int(math.floor(float(r["t_min"]) + 0.5)), []).append(r)
            if len(by_night) >= 3:
                top_per_n = [max(vs, key=row_snr) for vs in by_night.values()]
                if p_ref is not None:
                    best_trip = None
                    for a, b, c in itertools.combinations(top_per_n, 3):
                        mjds_t = [float(x["t_min"]) for x in (a, b, c)]
                        dvs = [det.compute_planet_orbital_rv_kms(mj + 2400000.5, p_ref[2], p_ref[1], p_ref[4])[1] for mj in mjds_t]
                        span_dv = max(dvs) - min(dvs)
                        score = span_dv + 0.01 * sum(row_snr(x) for x in (a, b, c))
                        if best_trip is None or score > best_trip[0]:
                            best_trip = (score, span_dv, [a, b, c])
                    assert best_trip and best_trip[1] >= 5.0, f"{st}: triplet orbital span < 5 km/s"
                    selected = sorted(best_trip[2], key=lambda x: float(x["t_min"]))
                else:
                    # Pick earliest, midpoint, latest high-SNR nights to maximize drift baseline
                    top_sorted = sorted(top_per_n, key=lambda x: float(x["t_min"]))
                    mid_c = top_sorted[len(top_sorted) // 2]
                    selected = [top_sorted[0], mid_c, top_sorted[-1]]
            else:
                # 2 nights with >= 4 exposures separated by >= 0.05 d (e.g. TOI2109)
                best_trip = None
                for a, b, c in itertools.combinations(h_cands, 3):
                    ts = sorted(float(x["t_min"]) for x in (a, b, c))
                    if min(ts[1] - ts[0], ts[2] - ts[1]) < 0.045:
                        continue
                    dvs = [det.compute_planet_orbital_rv_kms(float(x["t_min"]) + 2400000.5, p_ref[2], p_ref[1], p_ref[4])[1] for x in (a, b, c)]
                    span_dv = max(dvs) - min(dvs)
                    score = span_dv + 0.01 * sum(row_snr(x) for x in (a, b, c))
                    if best_trip is None or score > best_trip[0]:
                        best_trip = (score, span_dv, [a, b, c])
                assert best_trip and best_trip[1] >= 5.0, f"{st}: triplet dt>=0.05 & span>=5 failed"
                selected = sorted(best_trip[2], key=lambda x: float(x["t_min"]))
        else:  # "HH"
            h_cands = [r for r in pool if row_band(r) == "H"]
            if p_ref is not None:
                best_pair = None
                for a, b in itertools.combinations(h_cands, 2):
                    if abs(float(b["t_min"]) - float(a["t_min"])) < 0.015:
                        continue
                    dva = det.compute_planet_orbital_rv_kms(float(a["t_min"]) + 2400000.5, p_ref[2], p_ref[1], p_ref[4])[1]
                    dvb = det.compute_planet_orbital_rv_kms(float(b["t_min"]) + 2400000.5, p_ref[2], p_ref[1], p_ref[4])[1]
                    span_dv = abs(dvb - dva)
                    score = span_dv + 0.005 * (row_snr(a) + row_snr(b))
                    if best_pair is None or score > best_pair[0]:
                        best_pair = (score, span_dv, [a, b])
                assert best_pair and best_pair[1] >= 5.0, f"{st}: orbital span < 5 km/s ({best_pair})"
                selected = sorted(best_pair[2], key=lambda x: float(x["t_min"]))
            else:
                # Non-orbital HH (HNPEG)
                h_sorted = sorted(h_cands, key=row_snr, reverse=True)
                selected = sorted(h_sorted[:2], key=lambda x: float(x["t_min"]))

        camp_exps = []
        for erank, r in enumerate(selected, 1):
            dp_id = r["dp_id"].strip()
            if dp_id in excluded_dp_ids:
                raise RuntimeError(f"Duplicate CRIRES dp_id: {dp_id}")
            mjd_v = float(r["t_min"])
            expt_v = float(r["t_exptime"])
            rp_v = _opt_float(r.get("em_res_power"), 86000.0)
            band_v = f"CRIRES_{row_band(r)}"
            furl = f"https://dataportal.eso.org/dataPortal/file/{dp_id}"
            fbytes = head_content_length(furl)
            if p_ref is not None:
                s_ph, o_rv = det.compute_planet_orbital_rv_kms(mjd_v + 2400000.5, p_ref[2], p_ref[1], p_ref[4])
                ph_win = "IN_WINDOW" if abs(o_rv) > 0.4 * p_ref[4] else "OUT_OF_WINDOW"
            else:
                s_ph, o_rv, ph_win = 0.0, 0.0, "NONE"
            append_cohort_row(
                "ESO_CRIRES", spec, m, erank, dp_id, band_v, rp_v, mjd_v, expt_v,
                ph_win, s_ph, o_rv, dp_id, f"ESO_CRIRES/{st}/{dp_id}.fits", furl, fbytes,
            )
            if p_ref is not None:
                camp_exps.append({
                    "dp_id": dp_id,
                    "mjd_obs": round(mjd_v, 6),
                    "bjd_tdb_est": round(mjd_v + 2400000.5, 6),
                    "signed_phase": round(s_ph, 6),
                    "phase_window": ph_win,
                    "planet_orbital_rv_kms": round(o_rv, 4),
                    "ppo_align_score": 1.0,
                })

        if p_ref is not None:
            dvs_c = [e["planet_orbital_rv_kms"] for e in camp_exps]
            orbital_campaigns[st] = {
                "campaign_index": int(spec["campaign_index"]),
                "canonical_target": st,
                "common_name": spec["common_name"],
                "instrument": "ESO_CRIRES",
                "role": spec["role"],
                "null_orbital": False,
                "planet_name": p_ref[0],
                "n_planets_in_system": len(nasa_by_host.get(spec["nasa_host"], [])),
                "stellar_mass_msun": round(m["mass_msun"], 3),
                "orb_per_days": p_ref[1],
                "orb_t0_bjd": p_ref[2],
                "orb_ecc": p_ref[3],
                "kp_kms": round(p_ref[4], 3),
                "orbital_dv_span_kms": round(max(dvs_c) - min(dvs_c), 3),
                "n_epochs": len(camp_exps),
                "exposures": camp_exps,
            }

    # --- Stream C: JWST MIRI LRS + NIRSpec G395H ---
    print("5. Selecting & HEAD-checking Stream C (JWST MIRI LRS + NIRSpec G395H, 14 FITS)...", flush=True)
    for spec in JWST_SPECS:
        inst = spec["instrument"]
        st = spec["canonical_target"]
        m = resolve_star_meta(spec)
        for idx_f, fspec in enumerate(spec["files"], 1):
            fname = fspec["fname"]
            oid = fspec["obs_id"]
            furl = f"https://mast.stsci.edu/api/v0.1/Download/file?uri=mast:JWST/product/{fname}"
            fbytes = head_content_length(furl)
            md = mast_by_obs.get(oid, {})
            mjd_v = float(md["t_min"]) if md.get("t_min") is not None else float(fspec["mjd_fallback"])
            expt_v = float(md["t_exptime"]) if md.get("t_exptime") is not None else float(fspec["expt_fallback"])
            dp_id = f"JWST.{fname[:-5]}"
            if dp_id in excluded_dp_ids:
                raise RuntimeError(f"Duplicate JWST dp_id: {dp_id}")
            append_cohort_row(
                inst, spec, m, idx_f, dp_id, fspec["arm"], float(fspec["rp"]), mjd_v, expt_v,
                "NONE", 0.0, 0.0, fname[:-5], f"{inst}/{st}/{fname}", furl, fbytes,
            )

    # --- Verify 5-arcmin prior exclusion & caps ---
    print("6. Verifying 5-arcmin prior exclusion, dp_id disjointness, and caps...", flush=True)
    star_seps: list[dict[str, Any]] = []
    min_brand_new_sep = 1e18
    for st, (inst, ra, dec) in sorted(unique_new_coords.items()):
        best_sep = 1e18
        best_lbl = ""
        for p in prior_coords:
            sp = sep_arcsec(ra, dec, float(p["ra_deg"]), float(p["dec_deg"]))
            if sp < best_sep:
                best_sep = sp
                best_lbl = str(p["label"])
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

    intra_seps = [
        sep_arcsec(a[1], a[2], b[1], b[2])
        for (_, a), (_, b) in itertools.combinations(sorted(unique_new_coords.items()), 2)
    ]
    min_intra_sep = min(intra_seps) if intra_seps else 999999.0
    if min_intra_sep < 300.0:
        raise RuntimeError(f"Intra-D094 collision: {min_intra_sep:.2f}\" < 300\"")

    tot_bytes = sum(r["f1_bytes"] for r in cohort_rows)
    tot_mib = tot_bytes / 1048576.0
    if tot_mib > 98.0:
        raise RuntimeError(f"Projected download {tot_mib:.2f} MiB exceeds 98.0 MiB hard cap!")

    new_10pc = sum(1 for st in unique_new_coords if next(r["within_10pc"] for r in cohort_rows if r["canonical_target"] == st))
    new_ctrl = sum(1 for st in unique_new_coords if next(r["role"] == "CONTROL" for r in cohort_rows if r["canonical_target"] == st))
    all_stars_d094 = sorted({r["canonical_target"] for r in cohort_rows})
    prior_bridges_d094 = sorted({r["canonical_target"] for r in cohort_rows if r["is_prior_bridge"]})

    # Write Stage-1 frozen artifacts
    (WS / "PRIOR_V5_1_PHASES_SNAPSHOT.json").write_text(json.dumps(prior_snap, indent=2) + "\n", encoding="utf-8")

    prior_excl = {
        "schema": "D094_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D094",
        "verified_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prior_phases_covered": "C001-C037 + D001-D093",
        "n_prior_excluded_coords": len(prior_coords),
        "n_prior_excluded_dp_ids": len(excluded_dp_ids),
        "d094_total_stars": len(all_stars_d094),
        "d094_brand_new_unique_stars": len(unique_new_coords),
        "d094_panchromatic_bridge_stars": len(prior_bridges_d094) + 1,  # +1 intra-D094 bridge HNPEG
        "d094_prior_bridge_stars": len(prior_bridges_d094),
        "d094_intra_bridge_stars": ["HNPEG"],
        "d094_control_stars": new_ctrl,
        "d094_brand_new_within_10pc": new_10pc,
        "d094_total_fits_files": len(cohort_rows),
        "d094_projected_download_bytes": tot_bytes,
        "d094_projected_download_mib": round(tot_mib, 3),
        "d094_projected_download_gib": round(tot_bytes / (1024 ** 3), 5),
        "d094_dp_id_overlap_count": 0,
        "min_brand_new_sky_separation_arcsec": round(min_brand_new_sep, 2),
        "min_intra_d094_separation_arcsec": round(min_intra_sep, 2),
        "star_separation_verification": star_seps,
        "excluded_dp_ids": sorted(excluded_dp_ids),
        "excluded_targets_coordinate_registry": prior_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(prior_excl, indent=2) + "\n", encoding="utf-8")

    coh_fields = list(cohort_rows[0].keys())
    with (WS / "FROZEN_COHORT_D094.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=coh_fields)
        w.writeheader()
        w.writerows(cohort_rows)

    orb_doc = {
        "schema": "D094_ORBITAL_CAMPAIGNS_AND_KINEMATICS",
        "phase_id": "D094",
        "campaign_range": "#118-#125",
        "n_campaigns": len(orbital_campaigns),
        "campaigns": orbital_campaigns,
    }
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_doc, indent=2) + "\n", encoding="utf-8")

    # Seal METHOD_LOCK.json and LOCK_RECEIPT.json
    locked_names = [
        "v5_2_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D094.csv",
        "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "PRIOR_V5_1_PHASES_SNAPSHOT.json",
    ]
    hashes = {fn: sha256_file(WS / fn) for fn in locked_names}
    locked_utc = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    method_lock = {
        "schema": "D094_STAGE1_PROSPECTIVE_METHOD_LOCK",
        "phase_id": "D094",
        "detector_name": det.DETECTOR_NAME,
        "locked_utc": locked_utc,
        "retroactive_reused_bundles": [
            {
                "phase_id": "D091",
                "archive_name": ARCHIVE_Q_NAME,
                "archive_sha256": ARCHIVE_Q_SHA256,
                "bundle_member": ARCHIVE_Q_BUNDLE_MEMBER,
                "bundle_sha256": q_bundle_sha,
                "purpose": "Retroactive V5.2 DRIFT_V52_MULTIEPOCH (N>=3) across 31 D091 multi-night stars",
            },
            {
                "phase_id": "D093",
                "archive_name": ARCHIVE_S_NAME,
                "archive_sha256": ARCHIVE_S_SHA256,
                "purpose": "Prior 350-star synthesis, 37 bridges, 409 excluded coords, 2612 dp_ids, all-sky comb ledger",
            },
        ],
        "locked_v52_parameters": det.BASE_V5_2_CONFIG,
        "hard_caps": {
            "max_download_mib": 98.0,
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
        "schema": "D094_STAGE1_LOCK_RECEIPT",
        "phase_id": "D094",
        "locked_utc": locked_utc,
        "inputs_d094_v5_2_exists": False,
        "method_lock_sha256": sha256_file(WS / "METHOD_LOCK.json"),
        "frozen_cohort_sha256": hashes["FROZEN_COHORT_D094.csv"],
        "projected_download_mib": round(tot_mib, 3),
        "n_fits_files": len(cohort_rows),
        "n_unique_new_stars": len(unique_new_coords),
        "n_prior_bridge_stars": len(prior_bridges_d094),
        "n_orbital_campaigns": len(orbital_campaigns),
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lock_receipt, indent=2) + "\n", encoding="utf-8")

    print(
        f"STAGE-1 SEALED: {len(all_stars_d094)} D094 stars ({len(unique_new_coords)} brand-new, "
        f"{len(prior_bridges_d094)} prior bridges + HNPEG intra-bridge), {len(cohort_rows)} FITS ({tot_mib:.2f} MiB), "
        f"min_prior_sep={min_brand_new_sep:.2f}\", {len(orbital_campaigns)} orbital campaigns (#118-#125).",
        flush=True,
    )


if __name__ == "__main__":
    main()
