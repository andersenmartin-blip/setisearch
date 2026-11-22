#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D099 (`V5.7`) Prospective Method Lock & Cohort Builder.

Builds all 7 Stage-1 prospective artifacts in WS99 BEFORE any FITS file is
downloaded (`inputs_d099_v5_7` MUST NOT exist):
  1. `PRIOR_V5_6_PHASES_SNAPSHOT.json` (verifies `Archives X/W/V/U/T` & 473-star baseline)
  2. `PRIOR_EXCLUSION_VERIFICATION.json` (checks 0 `dp_id` overlap against 2,983+ prior `dp_id`s
     and >= 300" sky separation against all 532+ prior coordinates)
  3. `FROZEN_COHORT_D099.csv` (exact 46 columns; 97 pre-committed FITS across 60 targets)
  4. `ORBITAL_CAMPAIGNS_AND_KINEMATICS.json` (Orbital `#144–#145` + 6 multi-year DRIFT_V57 sets)
  5. `METHOD_LOCK.json`
  6. `LOCK_RECEIPT.json` (seals all 7 Stage-1 SHA-256s including `v5_7_detector.py`, `build_cohort.py`, `download_inputs.py`)
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import pathlib
import time
import zipfile
from typing import Any

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_v5_7_20261122_d099_jcmt_mm_sofia_exes_irtf_spex_keplerian_drift"
WS98 = ROOT / "analysis_workspace/work_v5_6_20261122_d098_sofia_great_iso_sws_forcast_optical_jerk"
ARCHIVES = ROOT / "archives"
IN_DIR = ROOT / "inputs_d099_v5_7"

C_KMS = 299792.458
G_CGS = 6.67430e-8
MSUN_G = 1.98847e33
DAY_S = 86400.0

FROZEN_HEADER = [
    "instrument", "canonical_target", "common_name", "role", "subrole", "science_track",
    "panchromatic_bridge", "is_prior_bridge", "gaia_source_id", "s_ra", "s_dec",
    "pmra_mas_yr", "pmdec_mas_yr", "dist_pc", "within_10pc",
    "phot_g_mag", "phot_bp_mag", "phot_rp_mag", "j_mag", "h_mag", "ks_mag",
    "teff_k", "mh_dex", "stellar_mass_msun", "prior_rv_kms", "n_exoplanets",
    "has_transiting_planet", "ecliptic_lat_deg", "sn1987a_dt_days", "gw170817_dt_days",
    "sn2023ixf_dt_days", "ppo_align_score", "epoch_rank", "dp_id", "grating",
    "resolving_power", "mjd_obs", "t_exptime", "phase_window", "signed_phase",
    "planet_orbital_rv_kms", "f1_id", "f1_rel", "f1_url", "f1_bytes", "total_bytes",
]
nan = math.nan

STAR_SPECS: dict[str, dict[str, Any]] = {'DMTAU': {'sim': 'V* DM Tau', 'common': 'DM Tauri (Protoplanetary Disk)', 'role': 'SCIENCE', 'sub': 'PROTOPLANETARY_DISK_JCMT', 'teff': 3720.0, 'mass': 0.53, 'npl': 0, 'dist': None}, 'DRTAU': {'sim': 'DR Tau', 'common': 'DR Tauri (Classical T Tauri)', 'role': 'SCIENCE', 'sub': 'TTS_ACCRETION_DISK_JCMT', 'teff': 4200.0, 'mass': 0.9, 'npl': 0, 'dist': None}, 'IMLUP': {'sim': 'IM Lup', 'common': 'IM Lupi (ALMA Giant Disk)', 'role': 'SCIENCE', 'sub': 'PROTOPLANETARY_DISK_JCMT', 'teff': 3900.0, 'mass': 1.0, 'npl': 0, 'dist': None}, 'LKCA15': {'sim': 'LkCa 15', 'common': 'LkCa 15 (Transition Disk)', 'role': 'SCIENCE', 'sub': 'TRANSITION_DISK_JCMT', 'teff': 4350.0, 'mass': 1.01, 'npl': 0, 'dist': None}, 'RLEO': {'sim': 'R Leo', 'common': 'R Leonis (Mira AGB + EXES/JCMT)', 'role': 'SCIENCE', 'sub': 'AGB_MM_MIDIR_BRIDGE_V57', 'teff': 2900.0, 'mass': 1.2, 'npl': 0, 'dist': None}, 'TXCAM': {'sim': 'TX Cam', 'common': 'TX Camelopardalis (OH/IR + EXES/JCMT)', 'role': 'SCIENCE', 'sub': 'AGB_MM_MIDIR_BRIDGE_V57', 'teff': 2700.0, 'mass': 1.3, 'npl': 0, 'dist': None}, 'RAQL': {'sim': 'R Aql', 'common': 'R Aquilae (M6.5-9e Mira)', 'role': 'SCIENCE', 'sub': 'AGB_MIRA_MM_JCMT', 'teff': 2900.0, 'mass': 1.1, 'npl': 0, 'dist': None}, 'NGC253': {'sim': 'NGC 253', 'common': 'Sculptor Galaxy (NGC 253 Starburst Control)', 'role': 'CONTROL', 'sub': 'CONTROL_EXTRAGALACTIC_STARBURST_MM', 'teff': 4500.0, 'mass': 1.0, 'npl': 0, 'dist': 3500000.0}, 'MUUMA': {'sim': 'mu UMa', 'common': 'mu UMa (Tania Australis, M0III)', 'role': 'SCIENCE', 'sub': 'BRIGHT_MGIANT_EXES_MRD', 'teff': 3850.0, 'mass': 2.2, 'npl': 0, 'dist': None}, 'GHER': {'sim': 'g Her', 'common': 'g Herculis (30 Her, M6-III)', 'role': 'SCIENCE', 'sub': 'AGB_SRB_EXES_MRD', 'teff': 3250.0, 'mass': 1.5, 'npl': 0, 'dist': None}, '40COM': {'sim': '40 Com', 'common': '40 Comae Berenices (FS Com, M5III)', 'role': 'SCIENCE', 'sub': 'MGIANT_EXES_MRD', 'teff': 3400.0, 'mass': 1.4, 'npl': 0, 'dist': None}, 'EUDEL': {'sim': 'EU Del', 'common': 'EU Delphini (M6III SRB Giant)', 'role': 'SCIENCE', 'sub': 'AGB_SRB_EXES_MRD', 'teff': 3240.0, 'mass': 1.2, 'npl': 0, 'dist': None}, 'UUAUR': {'sim': 'UU Aur', 'common': 'UU Aurigae (Carbon Star C-N5)', 'role': 'SCIENCE', 'sub': 'CARBON_AGB_EXES_MRD', 'teff': 2800.0, 'mass': 1.5, 'npl': 0, 'dist': None}, 'VCRB': {'sim': 'V CrB', 'common': 'V Coronae Borealis (Carbon Mira)', 'role': 'SCIENCE', 'sub': 'CARBON_MIRA_EXES_MRD', 'teff': 2800.0, 'mass': 1.3, 'npl': 0, 'dist': None}, 'V883ORI': {'sim': 'V883 Ori', 'common': 'V883 Orionis (FU Ori Protostar)', 'role': 'SCIENCE', 'sub': 'FUOR_SNOWLINE_EXES_MRD', 'teff': 6200.0, 'mass': 1.3, 'npl': 0, 'dist': None}, 'HMSGE': {'sim': 'HM Sge', 'common': 'HM Sagittae (Symbiotic Nova Control)', 'role': 'CONTROL', 'sub': 'CONTROL_SYMBIOTIC_NOVA_EXES', 'teff': 3000.0, 'mass': 1.0, 'npl': 0, 'dist': None}, 'AFGL2591': {'sim': 'AFGL 2591', 'common': 'AFGL 2591 (Massive YSO Control)', 'role': 'CONTROL', 'sub': 'CONTROL_MYSO_LINE_FOREST_EXES', 'teff': 10000.0, 'mass': 16.0, 'npl': 0, 'dist': 3333.33}, 'AFGL2136': {'sim': 'AFGL 2136', 'common': 'AFGL 2136 (Massive YSO Control)', 'role': 'CONTROL', 'sub': 'CONTROL_MYSO_LINE_FOREST_EXES', 'teff': 4500.0, 'mass': 15.0, 'npl': 0, 'dist': 2000.0}, 'EZAQR': {'sim': 'GJ 866', 'common': 'EZ Aquarii (GJ 866 ABC, 3.41 pc)', 'role': 'SCIENCE', 'sub': 'NEARBY_5PC_MDWARF_SPEX', 'teff': 3050.0, 'mass': 0.118, 'npl': 0, 'dist': None}, '61UMA': {'sim': '61 UMa', 'common': '61 Ursae Majoris (9.58 pc, G8V)', 'role': 'SCIENCE', 'sub': 'SOLAR_ANALOG_10PC_SPEX', 'teff': 5490.0, 'mass': 0.94, 'npl': 0, 'dist': None}, 'HD209290': {'sim': 'HD 209290', 'common': 'HD 209290 (Gl 846, M0.5V, 10.57 pc)', 'role': 'SCIENCE', 'sub': 'NEARBY_15PC_MDWARF_SPEX', 'teff': 3820.0, 'mass': 0.59, 'npl': 0, 'dist': None}, 'BETVIR': {'sim': 'bet Vir', 'common': 'Zavijava (beta Vir, 11.00 pc, F9V)', 'role': 'SCIENCE', 'sub': 'NEARBY_FSTAR_SPEX', 'teff': 6080.0, 'mass': 1.34, 'npl': 0, 'dist': None}, '36UMAB': {'sim': 'HD 237903', 'common': '36 UMa B (Gl 397, K7V, 12.92 pc)', 'role': 'SCIENCE', 'sub': 'NEARBY_KDWARF_SPEX', 'teff': 4100.0, 'mass': 0.65, 'npl': 0, 'dist': None}, 'TETBOO': {'sim': 'tet Boo', 'common': 'Asellus Primus (theta Boo, 14.48 pc)', 'role': 'SCIENCE', 'sub': 'NEARBY_FSTAR_SPEX', 'teff': 6250.0, 'mass': 1.25, 'npl': 0, 'dist': None}, 'HD10307': {'sim': 'HD 10307', 'common': 'HD 10307 (HR 483, G1V, 14.70 pc)', 'role': 'SCIENCE', 'sub': 'SOLAR_ANALOG_15PC_SPEX', 'teff': 5880.0, 'mass': 1.07, 'npl': 0, 'dist': None}, 'HD19305': {'sim': 'HD 19305', 'common': 'HD 19305 (Gl 123, M0V, 14.72 pc)', 'role': 'SCIENCE', 'sub': 'NEARBY_15PC_MDWARF_SPEX', 'teff': 3850.0, 'mass': 0.58, 'npl': 0, 'dist': None}, 'HD176051': {'sim': 'HD 176051', 'common': 'HD 176051 (1-pl, F9V+K1V, 14.87 pc)', 'role': 'SCIENCE', 'sub': 'EXOPLANET_HOST_SPEX', 'teff': 6000.0, 'mass': 1.07, 'npl': 1, 'dist': None}, 'XIPEG': {'sim': 'xi Peg', 'common': 'Homam companion (xi Peg, 16.42 pc)', 'role': 'SCIENCE', 'sub': 'NEARBY_FSTAR_SPEX', 'teff': 6180.0, 'mass': 1.17, 'npl': 0, 'dist': None}, 'HD165185': {'sim': 'HD 165185', 'common': 'HD 165185 (G1V Young, 17.11 pc)', 'role': 'SCIENCE', 'sub': 'SOLAR_ANALOG_SPEX', 'teff': 5890.0, 'mass': 1.04, 'npl': 0, 'dist': None}, '14HER': {'sim': '14 Her', 'common': '14 Herculis (2-pl, K0V, 17.90 pc)', 'role': 'SCIENCE', 'sub': 'MULTIPLANET_HOST_SPEX', 'teff': 5338.0, 'mass': 0.97, 'npl': 2, 'dist': None}, 'HD219623': {'sim': 'HD 219623', 'common': 'HD 219623 (F8V, 20.61 pc)', 'role': 'SCIENCE', 'sub': 'NEARBY_FSTAR_SPEX', 'teff': 6150.0, 'mass': 1.14, 'npl': 0, 'dist': None}, 'HD20619': {'sim': 'HD 20619', 'common': 'HD 20619 (G1.5V, 24.00 pc)', 'role': 'SCIENCE', 'sub': 'SOLAR_ANALOG_SPEX', 'teff': 5720.0, 'mass': 0.96, 'npl': 0, 'dist': None}, 'HD45977': {'sim': 'HD 45977', 'common': 'HD 45977 (K4V, 26.98 pc)', 'role': 'SCIENCE', 'sub': 'NEARBY_KDWARF_SPEX', 'teff': 4600.0, 'mass': 0.75, 'npl': 0, 'dist': None}, 'HD218804': {'sim': 'HD 218804', 'common': 'HD 218804 (F5V, 28.13 pc)', 'role': 'SCIENCE', 'sub': 'NEARBY_FSTAR_SPEX', 'teff': 6450.0, 'mass': 1.25, 'npl': 0, 'dist': None}, 'HD26015': {'sim': 'HD 26015', 'common': 'HD 26015 (Hyades F3V Binary, 43.76 pc)', 'role': 'SCIENCE', 'sub': 'OPEN_CLUSTER_HYADES_SPEX', 'teff': 6750.0, 'mass': 1.38, 'npl': 0, 'dist': None}, 'HD213893': {'sim': 'HD 213893', 'common': 'HD 213893 (M0IIIb Halo Giant Control)', 'role': 'CONTROL', 'sub': 'CONTROL_EVOLVED_MGIANT_SPEX', 'teff': 3800.0, 'mass': 1.3, 'npl': 0, 'dist': None}, 'HD339034': {'sim': 'HD 339034', 'common': 'HD 339034 (M1Ia Supergiant Control)', 'role': 'CONTROL', 'sub': 'CONTROL_SUPERGIANT_CO_SPEX', 'teff': 3550.0, 'mass': 14.0, 'npl': 0, 'dist': None}, 'GJ1046': {'sim': 'GJ 1046', 'common': 'GJ 1046 (M2.5V BD Companion Host)', 'role': 'SCIENCE', 'sub': 'DRIFT_V57_UVES_RED_2YR', 'teff': 3500.0, 'mass': 0.398, 'npl': 0, 'dist': None, 'camp_idx': 0}, 'GJ1009': {'sim': 'GJ 1009', 'common': 'GJ 1009 (M1.5V, 18.03 pc)', 'role': 'SCIENCE', 'sub': 'DRIFT_V57_UVES_RED_3YR', 'teff': 3630.0, 'mass': 0.49, 'npl': 0, 'dist': None, 'camp_idx': 0}, 'GJ422': {'sim': 'GJ 422', 'common': "GJ 422 (Innes' Star, 1-pl, 10.8 yr UVES)", 'role': 'SCIENCE', 'sub': 'ORBITAL_CAMPAIGN_144_DRIFT_V57', 'teff': 3323.0, 'mass': 0.35, 'npl': 1, 'dist': None, 'camp_idx': 144, 'pl_name': 'GJ 422 b', 'orb_p': 20.129, 'orb_e': 0.11, 'orb_kp_msun': 0.35}, 'GJ3082': {'sim': 'GJ 3082', 'common': 'GJ 3082 (M3V, 16.64 pc)', 'role': 'SCIENCE', 'sub': 'DRIFT_V57_UVES_RED_2YR', 'teff': 3420.0, 'mass': 0.38, 'npl': 0, 'dist': None, 'camp_idx': 0}, 'HD98800': {'sim': 'HD 98800', 'common': 'HD 98800 (TV Crt Quadruple Disk Control)', 'role': 'CONTROL', 'sub': 'CONTROL_QUADRUPLE_DEBRIS_UVES_BLUE', 'teff': 4250.0, 'mass': 0.7, 'npl': 0, 'dist': None, 'camp_idx': 0}, 'HD113538': {'sim': 'HD 113538', 'common': 'HD 113538 (2-pl, 21.1 yr HARPS)', 'role': 'SCIENCE', 'sub': 'ORBITAL_CAMPAIGN_145_DRIFT_V57_21YR', 'teff': 4462.0, 'mass': 0.585, 'npl': 2, 'dist': None, 'camp_idx': 145, 'pl_name': 'HD 113538 b', 'orb_p': 663.2, 'orb_e': 0.14, 'orb_p2': 1818.0}, 'IRC10216': {'sim': 'IRC+10216', 'is_bridge': True, 'sub': 'BRIDGE_SCIENCE_AGB_MM_1384UM'}, 'OCETI': {'sim': '* omi Cet', 'is_bridge': True, 'sub': 'BRIDGE_SCIENCE_MIRA_MM_1401UM'}, 'ABAUR': {'sim': 'AB Aur', 'is_bridge': True, 'sub': 'BRIDGE_SCIENCE_HAEBE_HARP_EXES'}, 'BETELGEUSE': {'sim': 'Betelgeuse', 'is_bridge': True, 'sub': 'BRIDGE_SCIENCE_RSG_JCMT_MM'}, 'VYCMA': {'sim': 'VY CMa', 'is_bridge': True, 'sub': 'BRIDGE_SCIENCE_RSG_JCMT_MM'}, 'HD163296': {'sim': 'HD 163296', 'is_bridge': True, 'sub': 'BRIDGE_SCIENCE_HAEBE_JCMT_MM'}, 'RCAS': {'sim': 'R Cas', 'is_bridge': True, 'sub': 'BRIDGE_SCIENCE_MIRA_JCMT_MM'}, 'NGC7027': {'sim': 'NGC 7027', 'is_bridge': True, 'sub': 'CONTROL_BRIDGE_PN_JCMT_MM'}, 'AFGL2688': {'sim': 'AFGL 2688', 'is_bridge': True, 'sub': 'CONTROL_BRIDGE_PPN_JCMT_MM'}, 'CRL618': {'sim': 'CRL 618', 'is_bridge': True, 'sub': 'CONTROL_BRIDGE_PPN_JCMT_MM'}, '55CNC': {'sim': '55 Cnc', 'is_bridge': True, 'sub': 'BRIDGE_SCIENCE_5PL_IRTF_SPEX'}, 'HD219134': {'sim': 'HD 219134', 'is_bridge': True, 'sub': 'BRIDGE_SCIENCE_6PL_IRTF_SPEX'}, 'HD115617': {'sim': '61 Vir', 'is_bridge': True, 'sub': 'BRIDGE_SCIENCE_3PL_IRTF_SPEX'}, 'HD109358': {'sim': 'bet CVn', 'is_bridge': True, 'sub': 'CONTROL_BRIDGE_SOLAR_IRTF_SPEX'}, 'HD114710': {'sim': 'bet Com', 'is_bridge': True, 'sub': 'CONTROL_BRIDGE_SOLAR_IRTF_SPEX'}, '61CYGB': {'sim': '61 Cyg B', 'is_bridge': True, 'sub': 'BRIDGE_SCIENCE_10PC_IRTF_SPEX'}, 'DXCNC': {'sim': 'GJ 1111', 'is_bridge': True, 'sub': 'BRIDGE_SCIENCE_10PC_IRTF_SPEX'}}
SIMBAD_DATA: dict[str, dict[str, Any]] = {'* omi Cet': {'main_id': '* omi Cet', 'ra': 34.83663375759996, 'dec': -2.9776376730729166, 'pmra': 9.33, 'pmdec': -237.36, 'dist_pc': 91.6590284142988, 'rv_kms': 63.5, 'sp_type': 'M5/6IIIe', 'g_mag': 3.568147, 'j_mag': -0.73, 'h_mag': -1.57, 'ks_mag': -2.21}, '14 Her': {'main_id': '* 14 Her', 'ra': 242.60131531625294, 'dec': 43.817640946335835, 'pmra': 131.745, 'pmdec': -297.025, 'dist_pc': 17.900071063282123, 'rv_kms': -13.75, 'sp_type': 'K0V', 'g_mag': 6.39524, 'j_mag': 5.158, 'h_mag': 4.803, 'ks_mag': 4.714}, '40 Com': {'main_id': '* 40 Com', 'ra': 196.59417511078996, 'dec': 22.61618697203, 'pmra': 28.883, 'pmdec': -43.94, 'dist_pc': 183.03620456126222, 'rv_kms': -5.15, 'sp_type': 'M5III:', 'g_mag': 4.051477, 'j_mag': 0.92, 'h_mag': 0.03, 'ks_mag': -0.23}, '55 Cnc': {'main_id': '* rho01 Cnc', 'ra': 133.14921293501794, 'dec': 28.330820831797222, 'pmra': -485.681, 'pmdec': -233.517, 'dist_pc': 12.58681757421817, 'rv_kms': 27.394, 'sp_type': 'K0IV-V', 'g_mag': 5.732681, 'j_mag': 4.59, 'h_mag': 4.14, 'ks_mag': 4.015}, '61 Cyg B': {'main_id': '* 61 Cyg B', 'ra': 316.7302660185276, 'dec': 38.74204403329556, 'pmra': 4105.976, 'pmdec': 3155.942, 'dist_pc': 3.496437479851779, 'rv_kms': -64.248, 'sp_type': 'K7V', 'g_mag': 5.450645, 'j_mag': 3.55, 'h_mag': 2.86, 'ks_mag': 2.32}, '61 UMa': {'main_id': '* 61 UMa', 'ra': 175.262567794255, 'dec': 34.20163377929139, 'pmra': -12.522, 'pmdec': -381.196, 'dist_pc': 9.576232556892398, 'rv_kms': -13.7, 'sp_type': 'G8V', 'g_mag': 5.110995, 'j_mag': 4.01, 'h_mag': 3.61, 'ks_mag': 3.588}, '61 Vir': {'main_id': '* 61 Vir', 'ra': 199.60130827686294, 'dec': -18.311193819050562, 'pmra': -1070.202, 'pmdec': -1063.849, 'dist_pc': 8.534418456191977, 'rv_kms': -7.824, 'sp_type': 'G6.5V', 'g_mag': 4.532528, 'j_mag': 3.334, 'h_mag': 2.974, 'ks_mag': 2.956}, 'AB Aur': {'main_id': 'V* AB Aur', 'ra': 73.94102455509, 'dec': 30.55119224362, 'pmra': 4.018, 'pmdec': -24.027, 'dist_pc': 155.94055546025854, 'rv_kms': 8.9, 'sp_type': 'A0Ve', 'g_mag': 7.111234, 'j_mag': 5.936, 'h_mag': 5.062, 'ks_mag': 4.23}, 'AFGL 2136': {'main_id': 'RAFGL 2136', 'ra': 275.610537, 'dec': -13.5039, 'pmra': 0.0, 'pmdec': 0.0, 'dist_pc': nan, 'rv_kms': 0.0, 'sp_type': '', 'g_mag': nan, 'j_mag': nan, 'h_mag': nan, 'ks_mag': nan}, 'AFGL 2591': {'main_id': 'RAFGL 2591', 'ra': 307.35342916666673, 'dec': 40.188775, 'pmra': -1.2, 'pmdec': -4.8, 'dist_pc': 3333.3333333333335, 'rv_kms': 0.0, 'sp_type': '', 'g_mag': nan, 'j_mag': nan, 'h_mag': 10.771, 'ks_mag': 6.575}, 'AFGL 2688': {'main_id': 'V* V1610 Cyg', 'ra': 315.576125, 'dec': 36.69361111111111, 'pmra': 0.0, 'pmdec': 0.0, 'dist_pc': nan, 'rv_kms': 0.0, 'sp_type': 'F5Iae', 'g_mag': nan, 'j_mag': nan, 'h_mag': nan, 'ks_mag': nan}, 'Betelgeuse': {'main_id': '* alf Ori', 'ra': 88.79293899077537, 'dec': 7.407063995272694, 'pmra': 27.54, 'pmdec': 11.3, 'dist_pc': 152.67175572519085, 'rv_kms': 21.91, 'sp_type': 'M1-M2Ia-Iab', 'g_mag': nan, 'j_mag': -3.0, 'h_mag': -3.73, 'ks_mag': -4.05}, 'CRL 618': {'main_id': 'RAFGL 618', 'ra': 70.72343418025, 'dec': 36.11483358395, 'pmra': 0.0, 'pmdec': 0.0, 'dist_pc': nan, 'rv_kms': 0.0, 'sp_type': 'C-rich', 'g_mag': 18.261955, 'j_mag': 13.51, 'h_mag': 11.41, 'ks_mag': 8.807}, 'DR Tau': {'main_id': 'V* DR Tau', 'ra': 71.77589648386, 'dec': 16.97855940905, 'pmra': 5.207, 'pmdec': -13.889, 'dist_pc': 192.96451382590743, 'rv_kms': 21.1, 'sp_type': 'K5Ve', 'g_mag': 11.651405, 'j_mag': 8.845, 'h_mag': 7.8, 'ks_mag': 6.874}, 'EU Del': {'main_id': 'V* EU Del', 'ra': 309.47803207124, 'dec': 18.26858187279, 'pmra': 35.347, 'pmdec': 61.883, 'dist_pc': 118.60285832888573, 'rv_kms': -84.7, 'sp_type': 'M6III', 'g_mag': 3.792551, 'j_mag': 0.12, 'h_mag': -0.77, 'ks_mag': -1.11}, 'GJ 1009': {'main_id': 'BPM 46239', 'ra': 5.48351938803, 'dec': -31.40605845575999, 'pmra': 63.399, 'pmdec': -194.004, 'dist_pc': 18.025910443671734, 'rv_kms': 16.93, 'sp_type': 'M1.5', 'g_mag': 10.188374, 'j_mag': 7.674, 'h_mag': 7.052, 'ks_mag': 6.785}, 'GJ 1046': {'main_id': 'L 440-30', 'ra': 34.79198206791833, 'dec': -36.778099369500275, 'pmra': 1392.334, 'pmdec': 544.645, 'dist_pc': 15.247365636402172, 'rv_kms': 45.4, 'sp_type': 'M2.5+V', 'g_mag': 10.53407, 'j_mag': 7.924, 'h_mag': 7.317, 'ks_mag': 7.031}, 'GJ 1111': {'main_id': 'G 51-15', 'ra': 127.45563663413579, 'dec': 26.77600670640528, 'pmra': -1113.694, 'pmdec': -612.191, 'dist_pc': 3.581025720359134, 'rv_kms': 10.62, 'sp_type': 'M6.5Ve', 'g_mag': 12.167455, 'j_mag': 8.235, 'h_mag': 7.617, 'ks_mag': 7.26}, 'GJ 3082': {'main_id': 'CD-54 269', 'ra': 18.642485796015418, 'dec': -53.94211409389694, 'pmra': 103.454, 'pmdec': 310.993, 'dist_pc': 16.639378086604637, 'rv_kms': 6.931, 'sp_type': 'M3V', 'g_mag': 10.206263, 'j_mag': 7.805, 'h_mag': 7.242, 'ks_mag': 6.966}, 'GJ 422': {'main_id': 'HD 304043', 'ra': 169.00085188535294, 'dec': -57.547659747396665, 'pmra': -2468.407, 'pmdec': 1184.175, 'dist_pc': 12.675524323063623, 'rv_kms': -50.524, 'sp_type': 'M3.5V', 'g_mag': 10.486478, 'j_mag': 7.811, 'h_mag': 7.304, 'ks_mag': 7.035}, 'GJ 866': {'main_id': 'V* EZ Aqr', 'ra': 339.6399, 'dec': -15.2999325, 'pmra': 2314.8, 'pmdec': 2295.3, 'dist_pc': 3.4059945504087192, 'rv_kms': -60.1, 'sp_type': 'M5V', 'g_mag': 10.840448, 'j_mag': 6.553, 'h_mag': 5.954, 'ks_mag': 5.537}, 'HD 10307': {'main_id': 'HD 10307', 'ra': 25.446361892124575, 'dec': 42.61339487994944, 'pmra': 824.761, 'pmdec': -156.423, 'dist_pc': 14.700607429098971, 'rv_kms': 3.33, 'sp_type': 'G1V', 'g_mag': 4.800438, 'j_mag': 4.0, 'h_mag': 3.703, 'ks_mag': 3.577}, 'HD 113538': {'main_id': 'HD 113538', 'ra': 196.23948556729414, 'dec': -52.442923860276665, 'pmra': -786.098, 'pmdec': -795.745, 'dist_pc': 16.307839830920315, 'rv_kms': 39.047, 'sp_type': 'K9Vk:', 'g_mag': 8.445794, 'j_mag': 6.438, 'h_mag': 5.835, 'ks_mag': 5.637}, 'HD 163296': {'main_id': 'HD 163296', 'ra': 269.08870077132, 'dec': -21.95607550528, 'pmra': -7.586, 'pmdec': -39.458, 'dist_pc': 100.96624698363338, 'rv_kms': -4.0, 'sp_type': 'A3VaekA1mA1', 'g_mag': 6.844196, 'j_mag': 6.195, 'h_mag': 5.531, 'ks_mag': 4.779}, 'HD 165185': {'main_id': 'HD 165185', 'ra': 271.59883132989, 'dec': -36.01978627702001, 'pmra': 106.02, 'pmdec': 8.812, 'dist_pc': 17.114613141284554, 'rv_kms': 14.99, 'sp_type': 'G1V', 'g_mag': 5.805398, 'j_mag': 4.835, 'h_mag': 4.614, 'ks_mag': 4.469}, 'HD 176051': {'main_id': 'HD 176051', 'ra': 284.2567077179583, 'dec': 32.90127007002849, 'pmra': 201.96, 'pmdec': -145.46, 'dist_pc': 14.872099940511601, 'rv_kms': -45.82, 'sp_type': 'F9V+K1V', 'g_mag': nan, 'j_mag': 3.847, 'h_mag': 3.611, 'ks_mag': 3.655}, 'HD 19305': {'main_id': 'HD 19305', 'ra': 46.61140439245542, 'dec': 1.9651751474955548, 'pmra': 389.253, 'pmdec': -925.026, 'dist_pc': 14.720277918847108, 'rv_kms': -31.67, 'sp_type': 'M0V', 'g_mag': 8.457596, 'j_mag': 6.492, 'h_mag': 5.843, 'ks_mag': 5.646}, 'HD 20619': {'main_id': 'HD 20619', 'ra': 49.75789307795, 'dec': -2.84319253022, 'pmra': 253.735, 'pmdec': -100.736, 'dist_pc': 23.997504259557008, 'rv_kms': 22.719, 'sp_type': 'G1.5V', 'g_mag': 6.88856, 'j_mag': 5.876, 'h_mag': 5.552, 'ks_mag': 5.469}, 'HD 209290': {'main_id': 'HD 209290', 'ra': 330.5428129076162, 'dec': 1.4002311550194444, 'pmra': -452.372, 'pmdec': -278.725, 'dist_pc': 10.574882327996896, 'rv_kms': 18.25, 'sp_type': 'M0.5V', 'g_mag': 8.403359, 'j_mag': 6.196, 'h_mag': 5.562, 'ks_mag': 5.322}, 'HD 213893': {'main_id': 'HD 213893', 'ra': 338.64974544027, 'dec': 0.5951781387700001, 'pmra': -24.819, 'pmdec': -75.188, 'dist_pc': 265.5689815429558, 'rv_kms': -85.36, 'sp_type': 'M0IIIb', 'g_mag': 6.057933, 'j_mag': 4.009, 'h_mag': 3.092, 'ks_mag': 2.869}, 'HD 218804': {'main_id': '* 6 And', 'ra': 347.61350499924, 'dec': 43.54403723212, 'pmra': -211.689, 'pmdec': -144.535, 'dist_pc': 28.127971016938663, 'rv_kms': -32.22, 'sp_type': 'F5V', 'g_mag': 5.78713, 'j_mag': 5.147, 'h_mag': 4.738, 'ks_mag': 4.674}, 'HD 219134': {'main_id': 'HD 219134', 'ra': 348.3207290015033, 'dec': 57.16835661767194, 'pmra': 2074.414, 'pmdec': 294.452, 'dist_pc': 6.541762612518316, 'rv_kms': -18.475, 'sp_type': 'K3V', 'g_mag': 5.231896, 'j_mag': 3.86, 'h_mag': 3.4, 'ks_mag': 3.25}, 'HD 219623': {'main_id': 'HD 219623', 'ra': 349.1762648346, 'dec': 53.21347481835, 'pmra': 112.461, 'pmdec': -236.554, 'dist_pc': 20.610185141293123, 'rv_kms': -27.006, 'sp_type': 'F8V', 'g_mag': 5.446386, 'j_mag': 4.871, 'h_mag': 4.599, 'ks_mag': 4.306}, 'HD 237903': {'main_id': '* 36 UMa B', 'ra': 157.60545366878, 'dec': 55.99912650252, 'pmra': -182.443, 'pmdec': -32.034, 'dist_pc': 12.918694901766244, 'rv_kms': 8.985, 'sp_type': 'K7Ve', 'g_mag': 8.08446, 'j_mag': 6.119, 'h_mag': 5.499, 'ks_mag': 5.361}, 'HD 26015': {'main_id': 'HD 26015', 'ra': 61.92493284212001, 'dec': 15.162789190199996, 'pmra': 127.744, 'pmdec': -23.239, 'dist_pc': 43.76271854007571, 'rv_kms': 36.3151, 'sp_type': 'F3V', 'g_mag': 5.984928, 'j_mag': nan, 'h_mag': 5.055, 'ks_mag': 5.03}, 'HD 339034': {'main_id': 'V* NR Vul', 'ra': 297.54969848142, 'dec': 24.92338352403, 'pmra': -2.023, 'pmdec': -6.024, 'dist_pc': 3100.7751937984494, 'rv_kms': 11.58, 'sp_type': 'M1Ia:', 'g_mag': 7.082869, 'j_mag': 3.13, 'h_mag': 2.14, 'ks_mag': 1.66}, 'HD 45977': {'main_id': 'HD 45977', 'ra': 97.53043108653002, 'dec': -11.808942239369998, 'pmra': -153.137, 'pmdec': 78.929, 'dist_pc': 26.976500770179097, 'rv_kms': 43.38, 'sp_type': 'K4+Vk:', 'g_mag': 8.705418, 'j_mag': 7.079, 'h_mag': 6.601, 'ks_mag': 6.406}, 'HD 98800': {'main_id': 'HD 98800', 'ra': 170.52204061475314, 'dec': -24.777710311067032, 'pmra': -85.4, 'pmdec': -33.1, 'dist_pc': 44.9034575662326, 'rv_kms': 11.695, 'sp_type': 'K5V(e)', 'g_mag': nan, 'j_mag': 6.397, 'h_mag': 5.759, 'ks_mag': 5.587}, 'HM Sge': {'main_id': 'V* HM Sge', 'ra': 295.48783161872, 'dec': 16.74439051773, 'pmra': -0.443, 'pmdec': -7.104, 'dist_pc': 1027.221366204417, 'rv_kms': 0.0, 'sp_type': 'M7', 'g_mag': 11.945307, 'j_mag': 7.62, 'h_mag': 6.02, 'ks_mag': 4.654}, 'IM Lup': {'main_id': 'THA 15-12', 'ra': 239.03836110288, 'dec': -37.935035032970006, 'pmra': -12.059, 'pmdec': -23.727, 'dist_pc': 155.82391897156214, 'rv_kms': -0.5, 'sp_type': 'M0e', 'g_mag': 11.186081, 'j_mag': 8.783, 'h_mag': 8.089, 'ks_mag': 7.739}, 'IRC+10216': {'main_id': 'IRC +10216', 'ra': 146.989193, 'dec': 13.278768, 'pmra': 33.84, 'pmdec': 10.0, 'dist_pc': 92.67840593141798, 'rv_kms': 0.0, 'sp_type': 'C9,5e', 'g_mag': 16.83244, 'j_mag': 6.928, 'h_mag': 2.839, 'ks_mag': 0.382}, 'LkCa 15': {'main_id': 'EM* LkCa 15', 'ra': 69.82412984284, 'dec': 22.35094169194, 'pmra': 10.573, 'pmdec': -17.527, 'dist_pc': 157.18574639651675, 'rv_kms': 17.65, 'sp_type': 'K5:Ve', 'g_mag': 11.591105, 'j_mag': 9.424, 'h_mag': 8.6, 'ks_mag': 8.163}, 'NGC 253': {'main_id': 'NGC 253', 'ra': 11.888058333333333, 'dec': -25.288800000000002, 'pmra': 0.0, 'pmdec': 0.0, 'dist_pc': nan, 'rv_kms': 258.8, 'sp_type': '', 'g_mag': nan, 'j_mag': 4.814, 'h_mag': 4.088, 'ks_mag': 3.772}, 'NGC 7027': {'main_id': 'NGC 7027', 'ra': 316.75654979999996, 'dec': 42.236242000000004, 'pmra': -22.7, 'pmdec': -4.4, 'dist_pc': nan, 'rv_kms': 8.9, 'sp_type': '', 'g_mag': nan, 'j_mag': nan, 'h_mag': nan, 'ks_mag': nan}, 'R Aql': {'main_id': 'V* R Aql', 'ra': 286.59271288433, 'dec': 8.230003517160002, 'pmra': 4.311, 'pmdec': -68.766, 'dist_pc': 233.75955492180745, 'rv_kms': 33.84, 'sp_type': 'M6.5-9e', 'g_mag': 5.58387, 'j_mag': 0.68, 'h_mag': -0.35, 'ks_mag': -0.83}, 'R Cas': {'main_id': 'V* R Cas', 'ra': 359.6036178271, 'dec': 51.38880917483, 'pmra': 82.847, 'pmdec': 17.485, 'dist_pc': 174.1462480190864, 'rv_kms': -22.94, 'sp_type': 'M6.5-9e', 'g_mag': 6.743756, 'j_mag': -0.4, 'h_mag': -1.4, 'ks_mag': -1.92}, 'R Leo': {'main_id': 'V* R Leo', 'ra': 146.8895165870019, 'dec': 11.4288398010358, 'pmra': 6.132, 'pmdec': -53.097, 'dist_pc': 71.14095869555938, 'rv_kms': 14.1, 'sp_type': 'M7-9e', 'g_mag': 5.14398, 'j_mag': -1.18, 'h_mag': -1.85, 'ks_mag': -2.51}, 'TX Cam': {'main_id': 'V* TX Cam', 'ra': 75.21317830642, 'dec': 56.18167818394999, 'pmra': 8.406, 'pmdec': -17.983, 'dist_pc': 287.3480647107842, 'rv_kms': 11.0, 'sp_type': 'M9-9.5', 'g_mag': 8.249581, 'j_mag': 2.21, 'h_mag': 0.82, 'ks_mag': -0.01}, 'UU Aur': {'main_id': 'V* UU Aur', 'ra': 99.13682126541002, 'dec': 38.44550528378, 'pmra': 0.5, 'pmdec': -19.758, 'dist_pc': 490.5086574778045, 'rv_kms': 14.089, 'sp_type': 'C-N5-', 'g_mag': 4.140064, 'j_mag': 1.07, 'h_mag': -0.01, 'ks_mag': -0.44}, 'V CrB': {'main_id': 'V* V CrB', 'ra': 237.38046749095, 'dec': 39.57163684146, 'pmra': 5.905, 'pmdec': -15.089, 'dist_pc': 878.8890841975743, 'rv_kms': -115.0, 'sp_type': 'C6,2e_MS3', 'g_mag': 7.025564, 'j_mag': 3.25, 'h_mag': 1.98, 'ks_mag': 1.46}, 'V* DM Tau': {'main_id': 'V* DM Tau', 'ra': 68.45305698489, 'dec': 18.169437072300003, 'pmra': 11.691, 'pmdec': -18.292, 'dist_pc': 144.0486308177641, 'rv_kms': 18.3115, 'sp_type': 'M2Ve', 'g_mag': 13.095755, 'j_mag': 10.442, 'h_mag': 9.757, 'ks_mag': 9.522}, 'V883 Ori': {'main_id': 'V* V883 Ori', 'ra': 84.57542427558, 'dec': -7.040560474200001, 'pmra': -0.938, 'pmdec': 1.49, 'dist_pc': 655.3509404285995, 'rv_kms': 0.0, 'sp_type': 'F:I:', 'g_mag': 16.824081, 'j_mag': 9.253, 'h_mag': 6.762, 'ks_mag': 5.154}, 'VY CMa': {'main_id': 'V* VY CMa', 'ra': 110.74302556341208, 'dec': -25.76755399738722, 'pmra': -2.645, 'pmdec': 2.232, 'dist_pc': 2385.4961832061067, 'rv_kms': 56.13, 'sp_type': 'M5Iae', 'g_mag': 7.352249, 'j_mag': 2.821, 'h_mag': 1.576, 'ks_mag': 0.291}, 'bet CVn': {'main_id': '* bet CVn', 'ra': 188.43560104856124, 'dec': 41.35747815357195, 'pmra': -704.702, 'pmdec': 292.155, 'dist_pc': 8.47266633114908, 'rv_kms': 6.268, 'sp_type': 'G0V', 'g_mag': 4.094672, 'j_mag': 3.2, 'h_mag': 2.88, 'ks_mag': 2.72}, 'bet Com': {'main_id': '* bet Com', 'ra': 197.96830761169252, 'dec': 27.878183974850003, 'pmra': -800.72, 'pmdec': 882.301, 'dist_pc': 9.197516670498965, 'rv_kms': 5.297, 'sp_type': 'F9.5V', 'g_mag': 4.093279, 'j_mag': 3.2, 'h_mag': 2.91, 'ks_mag': 2.87}, 'bet Vir': {'main_id': '* bet Vir', 'ra': 177.67382714942332, 'dec': 1.7647226497586115, 'pmra': 740.746, 'pmdec': -270.927, 'dist_pc': 11.001765783408239, 'rv_kms': 4.455, 'sp_type': 'F9V', 'g_mag': 3.468565, 'j_mag': 2.63, 'h_mag': 2.363, 'ks_mag': 2.33}, 'g Her': {'main_id': '* g Her', 'ra': 247.16062326666164, 'dec': 41.88167914303528, 'pmra': 28.56, 'pmdec': -6.402, 'dist_pc': 117.83281879669127, 'rv_kms': 1.49, 'sp_type': 'M6-III', 'g_mag': 2.72367, 'j_mag': -0.81, 'h_mag': -1.85, 'ks_mag': -2.05}, 'mu UMa': {'main_id': '* mu. UMa', 'ra': 155.5821986521946, 'dec': 41.499538262575555, 'pmra': -73.749, 'pmdec': 28.259, 'dist_pc': 56.18387859787512, 'rv_kms': -21.3, 'sp_type': 'M0III', 'g_mag': 2.32451, 'j_mag': 0.1, 'h_mag': -0.68, 'ks_mag': -0.86}, 'tet Boo': {'main_id': '* tet Boo', 'ra': 216.2991539590004, 'dec': 51.85074367335807, 'pmra': -235.97, 'pmdec': -399.696, 'dist_pc': 14.478359196508977, 'rv_kms': -10.627, 'sp_type': 'F7V', 'g_mag': 3.917229, 'j_mag': 3.179, 'h_mag': 2.98, 'ks_mag': 2.739}, 'xi Peg': {'main_id': '* ksi Peg', 'ra': 341.67324939263915, 'dec': 12.172885794474443, 'pmra': 233.354, 'pmdec': -493.133, 'dist_pc': 16.416021380226244, 'rv_kms': -5.853, 'sp_type': 'F6V', 'g_mag': 4.069358, 'j_mag': 3.22, 'h_mag': 3.078, 'ks_mag': 2.87}}
JCMT_SPECS: dict[str, list[dict[str, Any]]] = {'DMTAU': [{'obs_id': '20070102-5aaf8f80c48c2ca063c100bf2724dd39', 'inst': 'HARP-ACSIS', 't_min': 54102.4515741, 't_exptime': 2400.0, 'lmin_mm': 0.9065762666310831, 'lmax_mm': 0.9071893525712861, 'sep_arcsec': 21.3, 'release': '2008-02-01T05:48:50.000', 'dp_id': 'CADC.JCMT.jcmth20070102_00060_01_reduced001_nit_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20070102_00060_01_reduced001_nit_000.fits', 'bytes': 1146240, 'fname': 'jcmth20070102_00060_01_reduced001_nit_000.fits'}], 'DRTAU': [{'obs_id': 'acsis_00049_20081224T125624', 'inst': 'RXA3-ACSIS', 't_min': 54824.5402907, 't_exptime': 600.0, 'lmin_mm': 1.3224211753207051, 'lmax_mm': 1.3250876175359891, 'sep_arcsec': 0.2, 'release': '2010-02-01T23:59:59.000', 'dp_id': 'CADC.JCMT.jcmth20081224_00049_01_reduced001_obs_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20081224_00049_01_reduced001_obs_000.fits', 'bytes': 316800, 'fname': 'jcmth20081224_00049_01_reduced001_obs_000.fits'}], 'IMLUP': [{'obs_id': 'acsis_00029_20090529T100033', 'inst': 'HARP-ACSIS', 't_min': 54980.4177068, 't_exptime': 30.0, 'lmin_mm': 0.866684, 'lmax_mm': 0.867238, 'sep_arcsec': 5.3, 'release': '2010-08-01T23:59:59.000', 'dp_id': 'CADC.JCMT.jcmth20090529_00029_01_reduced001_obs_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20090529_00029_01_reduced001_obs_000.fits', 'bytes': 7683840, 'fname': 'jcmth20090529_00029_01_reduced001_obs_000.fits'}], 'LKCA15': [{'obs_id': 'acsis_00039_20120111T080000', 'inst': 'HARP-ACSIS', 't_min': 55937.3333, 't_exptime': 600.0, 'lmin_mm': 0.84, 'lmax_mm': 0.8407, 'sep_arcsec': 5.3, 'release': '2013-02-01T23:59:59.000', 'dp_id': 'CADC.JCMT.jcmth20120111_00039_01_reduced001_obs_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20120111_00039_01_reduced001_obs_000.fits', 'bytes': 1293120, 'fname': 'jcmth20120111_00039_01_reduced001_obs_000.fits'}], 'RLEO': [{'obs_id': '20240403-5394cfc169d28c3c3787fb5aed3ae6c8', 'inst': 'UU-ACSIS', 't_min': 60403.23751662037, 't_exptime': 3.99999976158142, 'lmin_mm': 1.3938271177232673, 'lmax_mm': 1.3999550066732014, 'sep_arcsec': 1.33, 'release': '2025-08-01T23:59:59.000', 'dp_id': 'CADC.JCMT.jcmth20240403_00021_02_reduced001_nit_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20240403_00021_02_reduced001_nit_000.fits', 'bytes': 247680, 'fname': 'jcmth20240403_00021_02_reduced001_nit_000.fits'}], 'TXCAM': [{'obs_id': '20101030-352367b968196e93d954a205f568c92f', 'inst': 'RXA3-ACSIS', 't_min': 55499.5825347, 't_exptime': 960.0, 'lmin_mm': 1.3573740548001099, 'lmax_mm': 1.363209020692102, 'sep_arcsec': 6.53, 'release': '2012-02-01T23:59:59.000', 'dp_id': 'CADC.JCMT.jcmth20101030_00091_01_reduced001_nit_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20101030_00091_01_reduced001_nit_000.fits', 'bytes': 267840, 'fname': 'jcmth20101030_00091_01_reduced001_nit_000.fits'}], 'RAQL': [{'obs_id': 'acsis_00043_20100707T093532', 'inst': 'RXA3-ACSIS', 't_min': 55384.4007048, 't_exptime': 600.0, 'lmin_mm': 1.399683798491891, 'lmax_mm': 1.4012296811473341, 'sep_arcsec': 0.77, 'release': '2011-08-01T23:59:59.000', 'dp_id': 'CADC.JCMT.jcmth20100707_00043_01_reduced001_obs_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20100707_00043_01_reduced001_obs_000.fits', 'bytes': 302400, 'fname': 'jcmth20100707_00043_01_reduced001_obs_000.fits'}], 'NGC253': [{'obs_id': 'acsis_00049_20150703T142337', 'inst': 'RXA3-ACSIS', 't_min': 57206.6003531, 't_exptime': 1200.0, 'lmin_mm': 1.2912156566422517, 'lmax_mm': 1.2964940690288447, 'sep_arcsec': 1.08, 'release': '2016-08-01T23:59:59.000', 'dp_id': 'CADC.JCMT.jcmth20150703_00049_01_reduced001_obs_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20150703_00049_01_reduced001_obs_000.fits', 'bytes': 262080, 'fname': 'jcmth20150703_00049_01_reduced001_obs_000.fits'}], 'IRC10216': [{'obs_id': 'acsis_00012_20230623T234932', 'inst': 'UU-ACSIS', 't_min': 60118.99327366898, 't_exptime': 480.0, 'lmin_mm': 1.3632556556258675, 'lmax_mm': 1.3843219220166953, 'sep_arcsec': 0.29, 'release': '2023-06-23T00:00:00.000', 'dp_id': 'CADC.JCMT.jcmth20230623_00012_01_reduced001_obs_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20230623_00012_01_reduced001_obs_000.fits', 'bytes': 322560, 'fname': 'jcmth20230623_00012_01_reduced001_obs_000.fits'}, {'obs_id': 'acsis_00014_20110501T063019', 'inst': 'RXA3-ACSIS', 't_min': 55682.2718358, 't_exptime': 580.0, 'lmin_mm': 1.3780927279907236, 'lmax_mm': 1.3841065538116464, 'sep_arcsec': 0.16, 'release': '2012-08-01T23:59:59.000', 'dp_id': 'CADC.JCMT.jcmth20110501_00014_02_reduced001_obs_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20110501_00014_02_reduced001_obs_000.fits', 'bytes': 270720, 'fname': 'jcmth20110501_00014_02_reduced001_obs_000.fits'}, {'obs_id': 'acsis_00021_20180330T042437', 'inst': 'RXA3M-ACSIS', 't_min': 58207.1843583719, 't_exptime': 120.0, 'lmin_mm': 1.370741062288213, 'lmax_mm': 1.3766911924280927, 'sep_arcsec': 0.41, 'release': '2018-03-29T00:00:00.000', 'dp_id': 'CADC.JCMT.jcmth20180330_00021_01_reduced001_obs_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20180330_00021_01_reduced001_obs_000.fits', 'bytes': 299520, 'fname': 'jcmth20180330_00021_01_reduced001_obs_000.fits'}, {'obs_id': '20230623-0d9241f66458769ff8718820831f2547', 'inst': 'UU-ACSIS', 't_min': 60118.99327366898, 't_exptime': 480.0, 'lmin_mm': 1.3632556556258675, 'lmax_mm': 1.3843219220166953, 'sep_arcsec': 0.41, 'release': '2023-06-23T00:00:00.000', 'dp_id': 'CADC.JCMT.jcmth20230623_00012_01_reduced001_nit_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20230623_00012_01_reduced001_nit_000.fits', 'bytes': 334080, 'fname': 'jcmth20230623_00012_01_reduced001_nit_000.fits'}], 'OCETI': [{'obs_id': 'acsis_00074_20100706T144405', 'inst': 'RXA3-ACSIS', 't_min': 55383.6149394, 't_exptime': 600.0, 'lmin_mm': 1.3998149784986007, 'lmax_mm': 1.401360991607626, 'sep_arcsec': 0.14, 'release': '2011-08-01T23:59:59.000', 'dp_id': 'CADC.JCMT.jcmth20100706_00074_01_reduced001_obs_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20100706_00074_01_reduced001_obs_000.fits', 'bytes': 302400, 'fname': 'jcmth20100706_00074_01_reduced001_obs_000.fits'}, {'obs_id': 'acsis_00034_20131109T090000', 'inst': 'RXA3-ACSIS', 't_min': 56605.375, 't_exptime': 600.0, 'lmin_mm': 1.298, 'lmax_mm': 1.3033, 'sep_arcsec': 4.0, 'release': '2015-02-01T23:59:59.000', 'dp_id': 'CADC.JCMT.jcmth20131109_00034_01_reduced001_obs_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20131109_00034_01_reduced001_obs_000.fits', 'bytes': 264960, 'fname': 'jcmth20131109_00034_01_reduced001_obs_000.fits'}], 'ABAUR': [{'obs_id': 'acsis_00014_20090122T065400', 'inst': 'RXWD2-ACSIS', 't_min': 54853.2875, 't_exptime': 600.0, 'lmin_mm': 0.4329, 'lmax_mm': 0.4337, 'sep_arcsec': 1.0, 'release': '2010-02-01T23:59:59.000', 'dp_id': 'CADC.JCMT.jcmth20090122_00014_01_reduced001_obs_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20090122_00014_01_reduced001_obs_000.fits', 'bytes': 302400, 'fname': 'jcmth20090122_00014_01_reduced001_obs_000.fits'}], 'BETELGEUSE': [{'obs_id': '20141020-3f5ca2eb90fd4f07ad89ad71e5ae1c8a', 'inst': 'RXA3-ACSIS', 't_min': 56950.6116898, 't_exptime': 1428.0, 'lmin_mm': 1.3574088294395428, 'lmax_mm': 1.3632431816595503, 'sep_arcsec': 0.09, 'release': '2016-03-01T00:00:00.000', 'dp_id': 'CADC.JCMT.jcmth20141020_00053_01_reduced001_nit_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20141020_00053_01_reduced001_nit_000.fits', 'bytes': 259200, 'fname': 'jcmth20141020_00053_01_reduced001_nit_000.fits'}, {'obs_id': 'acsis_00019_20181005T132051', 'inst': 'HARP-ACSIS', 't_min': 58396.5570949, 't_exptime': 640.0, 'lmin_mm': 0.9056162852501997, 'lmax_mm': 0.908102052792273, 'sep_arcsec': 21.19, 'release': '2020-02-01T23:59:59.000', 'dp_id': 'CADC.JCMT.jcmth20181005_00019_01_reduced001_obs_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20181005_00019_01_reduced001_obs_000.fits', 'bytes': 547200, 'fname': 'jcmth20181005_00019_01_reduced001_obs_000.fits'}], 'VYCMA': [{'obs_id': 'acsis_00012_20240411T023229', 'inst': 'UU-ACSIS', 't_min': 60411.106159814815, 't_exptime': 3.99999976158142, 'lmin_mm': 1.3938360262207246, 'lmax_mm': 1.3999639543364073, 'sep_arcsec': 0.22, 'release': '2025-08-01T23:59:59.000', 'dp_id': 'CADC.JCMT.jcmth20240411_00012_02_reduced001_obs_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20240411_00012_02_reduced001_obs_000.fits', 'bytes': 247680, 'fname': 'jcmth20240411_00012_02_reduced001_obs_000.fits'}], 'HD163296': [{'obs_id': 'acsis_00035_20110617T131646', 'inst': 'RXA3-ACSIS', 't_min': 55729.5544085, 't_exptime': 600.0, 'lmin_mm': 1.2407807303706715, 'lmax_mm': 1.2431283055314684, 'sep_arcsec': 0.39, 'release': '2012-08-01T23:59:59.000', 'dp_id': 'CADC.JCMT.jcmth20110617_00035_03_reduced001_obs_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20110617_00035_03_reduced001_obs_000.fits', 'bytes': 336960, 'fname': 'jcmth20110617_00035_03_reduced001_obs_000.fits'}], 'RCAS': [{'obs_id': 'acsis_00054_20100706T120858', 'inst': 'RXA3-ACSIS', 't_min': 55383.5072399, 't_exptime': 600.0, 'lmin_mm': 1.3996313152887188, 'lmax_mm': 1.4011770741613567, 'sep_arcsec': 0.15, 'release': '2011-08-01T23:59:59.000', 'dp_id': 'CADC.JCMT.jcmth20100706_00054_01_reduced001_obs_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20100706_00054_01_reduced001_obs_000.fits', 'bytes': 302400, 'fname': 'jcmth20100706_00054_01_reduced001_obs_000.fits'}], 'NGC7027': [{'obs_id': 'acsis_00080_20210707T125730', 'inst': 'UU-ACSIS', 't_min': 59402.5408768054, 't_exptime': 480.0, 'lmin_mm': 1.3708753731407999, 'lmax_mm': 1.3768275735654096, 'sep_arcsec': 0.24, 'release': '2021-07-07T00:00:00.000', 'dp_id': 'CADC.JCMT.jcmth20210707_00080_02_reduced001_obs_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20210707_00080_02_reduced001_obs_000.fits', 'bytes': 270720, 'fname': 'jcmth20210707_00080_02_reduced001_obs_000.fits'}], 'AFGL2688': [{'obs_id': 'acsis_00053_20240523T114851', 'inst': 'UU-ACSIS', 't_min': 60453.49320246528, 't_exptime': 480.0, 'lmin_mm': 1.370594678374327, 'lmax_mm': 1.376544450343778, 'sep_arcsec': 6.4, 'release': '2024-05-23T00:00:00.000', 'dp_id': 'CADC.JCMT.jcmth20240523_00053_02_reduced001_obs_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20240523_00053_02_reduced001_obs_000.fits', 'bytes': 276480, 'fname': 'jcmth20240523_00053_02_reduced001_obs_000.fits'}], 'CRL618': [{'obs_id': 'acsis_00012_20200123T035725', 'inst': 'UU-ACSIS', 't_min': 58871.1653046504, 't_exptime': 4.0, 'lmin_mm': 1.3907163574662267, 'lmax_mm': 1.3968416944014335, 'sep_arcsec': 1.32, 'release': '2020-01-23T00:00:00.000', 'dp_id': 'CADC.JCMT.jcmth20200123_00012_02_reduced001_obs_000.fits', 'url': 'https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20200123_00012_02_reduced001_obs_000.fits', 'bytes': 276480, 'fname': 'jcmth20200123_00012_02_reduced001_obs_000.fits'}]}
EXES_SPECS: dict[str, list[dict[str, Any]]] = {'MUUMA': [{'target_name': 'mu Uma', 'rp': 85714.3, 'w_lo_um': 7.0, 'w_hi_um': 7.0, 'mjd': 57078.150535, 'exptime': 4224.0, 'url': 'https://irsa.ipac.caltech.edu/data/SOFIA/EXES/OC2I/20150225_F195/proc/p977/data/g8/F0195_EX_SPE_8600057_EXEELONEXEECHL_MRD_0024-0021.fits', 'bytes': 221760, 'fname': 'F0195_EX_SPE_8600057_EXEELONEXEECHL_MRD_0024-0021.fits', 'dp_id': 'EXES.F0195_EX_SPE_8600057_EXEELONEXEECHL_MRD_0024-0021', 'sep_arcsec': 0.0}], 'GHER': [{'target_name': 'g Her', 'rp': 50000.0, 'w_lo_um': 25.0, 'w_hi_um': 25.0, 'mjd': 57463.303682, 'exptime': 2304.0, 'url': 'https://irsa.ipac.caltech.edu/data/SOFIA/EXES/OC4C/20160316_F288/proc/p1871/data/gher_himed_396cm-1/F0288_EX_SPE_04013603_EXEELONEXEECHL_MRD_0062-0064.fits', 'bytes': 190080, 'fname': 'F0288_EX_SPE_04013603_EXEELONEXEECHL_MRD_0062-0064.fits', 'dp_id': 'EXES.F0288_EX_SPE_04013603_EXEELONEXEECHL_MRD_0062-0064', 'sep_arcsec': 0.0}], '40COM': [{'target_name': '40 Com', 'rp': 50000.0, 'w_lo_um': 7.0, 'w_hi_um': 7.0, 'mjd': 58593.306115, 'exptime': 768.0, 'url': 'https://irsa.ipac.caltech.edu/data/SOFIA/EXES/OC6S/20190420_F556/proc/p12563/data/g3/F0556_EX_SPE_0600566_EXEELONEXEECHL_MRD_40046-40048.fits', 'bytes': 334080, 'fname': 'F0556_EX_SPE_0600566_EXEELONEXEECHL_MRD_40046-40048.fits', 'dp_id': 'EXES.F0556_EX_SPE_0600566_EXEELONEXEECHL_MRD_40046-40048', 'sep_arcsec': 0.0}], 'EUDEL': [{'target_name': 'EU Del', 'rp': 50000.0, 'w_lo_um': 7.0, 'w_hi_um': 7.0, 'mjd': 58592.457133, 'exptime': 512.0, 'url': 'https://irsa.ipac.caltech.edu/data/SOFIA/EXES/OC6S/20190419_F555/proc/p12562/data/g8/F0555_EX_SPE_06005613_EXEELONEXEECHL_MRD_30079-30080.fits', 'bytes': 331200, 'fname': 'F0555_EX_SPE_06005613_EXEELONEXEECHL_MRD_30079-30080.fits', 'dp_id': 'EXES.F0555_EX_SPE_06005613_EXEELONEXEECHL_MRD_30079-30080', 'sep_arcsec': 0.0}], 'UUAUR': [{'target_name': 'UU Aur', 'rp': 66666.7, 'w_lo_um': 14.0, 'w_hi_um': 14.0, 'mjd': 57773.523353, 'exptime': 3780.0, 'url': 'https://irsa.ipac.caltech.edu/data/SOFIA/EXES/OC4M/20170120_F362/proc/p3533/data/uuaur_himed_730cm-1/F0362_EX_SPE_86000718_EXEELONEXEECHL_MRD_0116-0118.fits', 'bytes': 236160, 'fname': 'F0362_EX_SPE_86000718_EXEELONEXEECHL_MRD_0116-0118.fits', 'dp_id': 'EXES.F0362_EX_SPE_86000718_EXEELONEXEECHL_MRD_0116-0118', 'sep_arcsec': 0.0}], 'VCRB': [{'target_name': 'V CrB', 'rp': 50000.0, 'w_lo_um': 14.0, 'w_hi_um': 14.0, 'mjd': 59380.311011, 'exptime': 1088.0, 'url': 'https://irsa.ipac.caltech.edu/data/SOFIA/EXES/OC8N/20210615_F747/proc/p13094/data/g3/F0747_EX_SPE_08019453_EXEELONEXEECHL_MRD_50030-50033.fits', 'bytes': 285120, 'fname': 'F0747_EX_SPE_08019453_EXEELONEXEECHL_MRD_50030-50033.fits', 'dp_id': 'EXES.F0747_EX_SPE_08019453_EXEELONEXEECHL_MRD_50030-50033', 'sep_arcsec': 0.0}], 'V883ORI': [{'target_name': 'V883 Ori', 'rp': 13600.0, 'w_lo_um': 6.0, 'w_hi_um': 6.0, 'mjd': 59641.247125, 'exptime': 3840.0, 'url': 'https://irsa.ipac.caltech.edu/data/SOFIA/EXES/OC9K/20220303_F833/proc/p12946/data/g2/F0833_EX_SPE_0900035_NONEEXEECHL_MRD_50017-50024.fits', 'bytes': 86400, 'fname': 'F0833_EX_SPE_0900035_NONEEXEECHL_MRD_50017-50024.fits', 'dp_id': 'EXES.F0833_EX_SPE_0900035_NONEEXEECHL_MRD_50017-50024', 'sep_arcsec': 0.0}], 'HMSGE': [{'target_name': 'HM Sge', 'rp': 50000.0, 'w_lo_um': 6.0, 'w_hi_um': 6.0, 'mjd': 59639.465249, 'exptime': 2432.0, 'url': 'https://irsa.ipac.caltech.edu/data/SOFIA/EXES/OC9K/20220301_F832/proc/p12945/data/g10/F0832_EX_SPE_7500571_EXEELONEXEECHL_MRD_40089-40093.fits', 'bytes': 270720, 'fname': 'F0832_EX_SPE_7500571_EXEELONEXEECHL_MRD_40089-40093.fits', 'dp_id': 'EXES.F0832_EX_SPE_7500571_EXEELONEXEECHL_MRD_40089-40093', 'sep_arcsec': 0.0}], 'AFGL2591': [{'target_name': 'AFGL 2591', 'rp': 85714.3, 'w_lo_um': 6.0, 'w_hi_um': 6.0, 'mjd': 57471.372215, 'exptime': 442.0, 'url': 'https://irsa.ipac.caltech.edu/data/SOFIA/EXES/OC4C/20160324_F291/proc/p1877/data/afgl2591_himed_1748cm-1/F0291_EX_SPE_0401204_EXEELONEXEECHL_MRD_0056-0059.fits', 'bytes': 236160, 'fname': 'F0291_EX_SPE_0401204_EXEELONEXEECHL_MRD_0056-0059.fits', 'dp_id': 'EXES.F0291_EX_SPE_0401204_EXEELONEXEECHL_MRD_0056-0059', 'sep_arcsec': 0.0}], 'AFGL2136': [{'target_name': 'AFGL 2136', 'rp': 85714.3, 'w_lo_um': 6.0, 'w_hi_um': 6.0, 'mjd': 57471.400745, 'exptime': 416.0, 'url': 'https://irsa.ipac.caltech.edu/data/SOFIA/EXES/OC4C/20160324_F291/proc/p1877/data/afgl2136_himed_1748cm-1/F0291_EX_SPE_0401201_EXEELONEXEECHL_MRD_0062-0064.fits', 'bytes': 218880, 'fname': 'F0291_EX_SPE_0401201_EXEELONEXEECHL_MRD_0062-0064.fits', 'dp_id': 'EXES.F0291_EX_SPE_0401201_EXEELONEXEECHL_MRD_0062-0064', 'sep_arcsec': 0.0}], 'RLEO': [{'target_name': 'R Leo', 'rp': 66666.7, 'w_lo_um': 7.0, 'w_hi_um': 8.0, 'mjd': 58423.49161, 'exptime': 192.0, 'url': 'https://irsa.ipac.caltech.edu/data/SOFIA/EXES/OC6L/20181101_F523/proc/p12537/data/g5/F0523_EX_SPE_0601443_EXEELONEXEECHL_MRD_0574.fits', 'bytes': 1195200, 'fname': 'F0523_EX_SPE_0601443_EXEELONEXEECHL_MRD_0574.fits', 'dp_id': 'EXES.F0523_EX_SPE_0601443_EXEELONEXEECHL_MRD_0574', 'sep_arcsec': 0.0}], 'TXCAM': [{'target_name': 'TX Cam', 'rp': 66666.7, 'w_lo_um': 7.0, 'w_hi_um': 7.0, 'mjd': 59697.233454, 'exptime': 128.0, 'url': 'https://irsa.ipac.caltech.edu/data/SOFIA/EXES/OC9O/20220428_F861/proc/p13072/data/g4/F0861_EX_SPE_09022755_EXEELONEXEECHL_MRD_30041.fits', 'bytes': 1316160, 'fname': 'F0861_EX_SPE_09022755_EXEELONEXEECHL_MRD_30041.fits', 'dp_id': 'EXES.F0861_EX_SPE_09022755_EXEELONEXEECHL_MRD_30041', 'sep_arcsec': 0.0}], 'ABAUR': [{'target_name': 'AB Aur', 'rp': 50000.0, 'w_lo_um': 18.0, 'w_hi_um': 18.0, 'mjd': 57080.302605, 'exptime': 8112.0, 'url': 'https://irsa.ipac.caltech.edu/data/SOFIA/EXES/OC2I/20150227_F196/proc/p978/data/g8/F0196_EX_SPE_0200791_EXEELONEXEECHL_MRD_0071-0083.fits', 'bytes': 181440, 'fname': 'F0196_EX_SPE_0200791_EXEELONEXEECHL_MRD_0071-0083.fits', 'dp_id': 'EXES.F0196_EX_SPE_0200791_EXEELONEXEECHL_MRD_0071-0083', 'sep_arcsec': 0.0}]}
SPEX_LIST: list[str] = ['EZAQR', '61UMA', 'HD209290', 'BETVIR', '36UMAB', 'TETBOO', 'HD10307', 'HD19305', 'HD176051', 'XIPEG', 'HD165185', '14HER', 'HD219623', 'HD20619', 'HD45977', 'HD218804', 'HD26015', 'HD213893', 'HD339034', '55CNC', 'HD219134', 'HD115617', 'HD109358', 'HD114710', '61CYGB', 'DXCNC']
SPEX_SPECS: dict[str, dict[str, Any]] = {'EZAQR': {'filename': 'M5V_Gl866ABC_ext.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/M5V_Gl866ABC_ext.fits', 'http': 200, 'bytes': 89280}, '61UMA': {'filename': 'G8V_HD101501.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/G8V_HD101501.fits', 'http': 200, 'bytes': 97920}, 'HD209290': {'filename': 'M0.5V_HD209290.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/M0.5V_HD209290.fits', 'http': 200, 'bytes': 103680}, 'BETVIR': {'filename': 'F8.5IV-V_HD102870.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/F8.5IV-V_HD102870.fits', 'http': 200, 'bytes': 89280}, '36UMAB': {'filename': 'K7V_HD237903.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/K7V_HD237903.fits', 'http': 200, 'bytes': 97920}, 'TETBOO': {'filename': 'F7V_HD126660.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/F7V_HD126660.fits', 'http': 200, 'bytes': 97920}, 'HD10307': {'filename': 'G1V_HD10307.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/G1V_HD10307.fits', 'http': 200, 'bytes': 97920}, 'HD19305': {'filename': 'M0V_HD19305.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/M0V_HD19305.fits', 'http': 200, 'bytes': 103680}, 'HD176051': {'filename': 'F9V_HD176051.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/F9V_HD176051.fits', 'http': 200, 'bytes': 89280}, 'XIPEG': {'filename': 'F6V_HD215648.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/F6V_HD215648.fits', 'http': 200, 'bytes': 57600}, 'HD165185': {'filename': 'G5V_HD165185.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/G5V_HD165185.fits', 'http': 200, 'bytes': 97920}, '14HER': {'filename': 'K0V_HD145675.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/K0V_HD145675.fits', 'http': 200, 'bytes': 97920}, 'HD219623': {'filename': 'F8V_HD219623.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/F8V_HD219623.fits', 'http': 200, 'bytes': 89280}, 'HD20619': {'filename': 'G1.5V_HD20619.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/G1.5V_HD20619.fits', 'http': 200, 'bytes': 103680}, 'HD45977': {'filename': 'K4V_HD45977_ext.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/K4V_HD45977_ext.fits', 'http': 200, 'bytes': 57600}, 'HD218804': {'filename': 'F5V_HD218804.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/F5V_HD218804.fits', 'http': 200, 'bytes': 89280}, 'HD26015': {'filename': 'F3V_HD26015.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/F3V_HD26015.fits', 'http': 200, 'bytes': 97920}, 'HD213893': {'filename': 'M0IIIb_HD213893.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/M0IIIb_HD213893.fits', 'http': 200, 'bytes': 97920}, 'HD339034': {'filename': 'M1Ia_HD339034_ext.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/M1Ia_HD339034_ext.fits', 'http': 200, 'bytes': 97920}, '55CNC': {'filename': 'G8V_HD75732_ext.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/G8V_HD75732_ext.fits', 'http': 200, 'bytes': 103680}, 'HD219134': {'filename': 'K3V_HD219134.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/K3V_HD219134.fits', 'http': 200, 'bytes': 97920}, 'HD115617': {'filename': 'G6.5V_HD115617.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/G6.5V_HD115617.fits', 'http': 200, 'bytes': 97920}, 'HD109358': {'filename': 'G0V_HD109358.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/G0V_HD109358.fits', 'http': 200, 'bytes': 89280}, 'HD114710': {'filename': 'F9.5V_HD114710.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/F9.5V_HD114710.fits', 'http': 200, 'bytes': 97920}, '61CYGB': {'filename': 'K7V_HD201092.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/K7V_HD201092.fits', 'http': 200, 'bytes': 57600}, 'DXCNC': {'filename': 'M6.5V_GJ1111.fits', 'url': 'https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/M6.5V_GJ1111.fits', 'http': 200, 'bytes': 103680}}
ESO_SPECS: dict[str, list[dict[str, Any]]] = {'GJ1046': [{'dp_id': 'ADP.2020-07-17T10:10:40.322', 'inst': 'ESO_UVES', 'mjd': 53281.32399631, 'exptime': 900.0, 'w_min_um': 0.495946, 'w_max_um': 0.707063, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-17T10%3A10%3A40.322', 'bytes': 2116800}, {'dp_id': 'ADP.2020-07-14T11:04:59.345', 'inst': 'ESO_UVES', 'mjd': 53578.40444275, 'exptime': 900.0, 'w_min_um': 0.495943, 'w_max_um': 0.707056, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-14T11%3A04%3A59.345', 'bytes': 2116800}, {'dp_id': 'ADP.2020-07-14T12:12:08.427', 'inst': 'ESO_UVES', 'mjd': 53632.21302786, 'exptime': 899.999, 'w_min_um': 0.495946, 'w_max_um': 0.707059, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-14T12%3A12%3A08.427', 'bytes': 2116800}, {'dp_id': 'ADP.2021-09-14T08:40:02.917', 'inst': 'ESO_UVES', 'mjd': 53750.0982783, 'exptime': 899.999, 'w_min_um': 0.495946, 'w_max_um': 0.7070599999999999, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2021-09-14T08%3A40%3A02.917', 'bytes': 2116800}, {'dp_id': 'ADP.2020-07-06T18:46:44.341', 'inst': 'ESO_UVES', 'mjd': 54013.29114021, 'exptime': 899.999, 'w_min_um': 0.495947, 'w_max_um': 0.707063, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-06T18%3A46%3A44.341', 'bytes': 2119680}, {'dp_id': 'ADP.2020-07-06T19:14:14.507', 'inst': 'ESO_UVES', 'mjd': 54047.14539832, 'exptime': 899.999, 'w_min_um': 0.495943, 'w_max_um': 0.707062, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-06T19%3A14%3A14.507', 'bytes': 2119680}], 'GJ1009': [{'dp_id': 'ADP.2020-08-04T19:41:39.204', 'inst': 'ESO_UVES', 'mjd': 52808.37177756, 'exptime': 2025.0, 'w_min_um': 0.49594000000000005, 'w_max_um': 0.707058, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-08-04T19%3A41%3A39.204', 'bytes': 5149440}, {'dp_id': 'ADP.2020-07-20T13:47:18.351', 'inst': 'ESO_UVES', 'mjd': 53192.33782466, 'exptime': 900.0, 'w_min_um': 0.495949, 'w_max_um': 0.707056, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-20T13%3A47%3A18.351', 'bytes': 2113920}, {'dp_id': 'ADP.2020-07-17T10:28:23.717', 'inst': 'ESO_UVES', 'mjd': 53320.10264721, 'exptime': 900.0, 'w_min_um': 0.49594799999999994, 'w_max_um': 0.707066, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-17T10%3A28%3A23.717', 'bytes': 2113920}, {'dp_id': 'ADP.2020-07-10T20:06:56.272', 'inst': 'ESO_UVES', 'mjd': 53645.27018985, 'exptime': 899.999, 'w_min_um': 0.49594499999999997, 'w_max_um': 0.707056, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-10T20%3A06%3A56.272', 'bytes': 2116800}, {'dp_id': 'ADP.2021-09-14T08:40:02.913', 'inst': 'ESO_UVES', 'mjd': 53750.06742236, 'exptime': 899.999, 'w_min_um': 0.495946, 'w_max_um': 0.7070599999999999, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2021-09-14T08%3A40%3A02.913', 'bytes': 2116800}, {'dp_id': 'ADP.2020-07-06T19:08:49.469', 'inst': 'ESO_UVES', 'mjd': 54040.04062178, 'exptime': 899.999, 'w_min_um': 0.49594400000000005, 'w_max_um': 0.707062, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-06T19%3A08%3A49.469', 'bytes': 2119680}], 'GJ422': [{'dp_id': 'ADP.2020-07-23T15:23:46.133', 'inst': 'ESO_UVES', 'mjd': 53076.22891265, 'exptime': 2700.0, 'w_min_um': 0.49594799999999994, 'w_max_um': 0.707061, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-23T15%3A23%3A46.133', 'bytes': 5126400}, {'dp_id': 'ADP.2020-07-17T12:10:13.937', 'inst': 'ESO_UVES', 'mjd': 53374.31412171, 'exptime': 900.0, 'w_min_um': 0.49595200000000006, 'w_max_um': 0.707058, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-17T12%3A10%3A13.937', 'bytes': 2113920}, {'dp_id': 'ADP.2020-07-17T13:14:07.050', 'inst': 'ESO_UVES', 'mjd': 53453.07959639, 'exptime': 899.999, 'w_min_um': 0.495947, 'w_max_um': 0.707061, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-17T13%3A14%3A07.050', 'bytes': 2113920}, {'dp_id': 'ADP.2021-09-14T08:31:56.096', 'inst': 'ESO_UVES', 'mjd': 53747.34092236, 'exptime': 899.999, 'w_min_um': 0.49594499999999997, 'w_max_um': 0.707059, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2021-09-14T08%3A31%3A56.096', 'bytes': 2113920}, {'dp_id': 'ADP.2020-07-06T20:26:18.809', 'inst': 'ESO_UVES', 'mjd': 54170.3175205, 'exptime': 899.999, 'w_min_um': 0.49594499999999997, 'w_max_um': 0.7070639999999999, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-06T20%3A26%3A18.809', 'bytes': 2116800}, {'dp_id': 'ADP.2020-06-12T18:20:32.216', 'inst': 'ESO_UVES', 'mjd': 57012.26641336, 'exptime': 1499.999, 'w_min_um': 0.47262499999999996, 'w_max_um': 0.683528, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-06-12T18%3A20%3A32.216', 'bytes': 3260160}], 'GJ3082': [{'dp_id': 'ADP.2020-07-17T10:10:40.326', 'inst': 'ESO_UVES', 'mjd': 53281.29723383, 'exptime': 900.0, 'w_min_um': 0.495946, 'w_max_um': 0.707063, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-17T10%3A10%3A40.326', 'bytes': 2116800}, {'dp_id': 'ADP.2020-07-14T11:04:59.341', 'inst': 'ESO_UVES', 'mjd': 53578.390253, 'exptime': 899.999, 'w_min_um': 0.49594499999999997, 'w_max_um': 0.707056, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-14T11%3A04%3A59.341', 'bytes': 2116800}, {'dp_id': 'ADP.2020-07-14T12:05:43.291', 'inst': 'ESO_UVES', 'mjd': 53629.06917244, 'exptime': 899.999, 'w_min_um': 0.49594400000000005, 'w_max_um': 0.7070529999999999, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-14T12%3A05%3A43.291', 'bytes': 2113920}, {'dp_id': 'ADP.2020-07-14T12:12:08.474', 'inst': 'ESO_UVES', 'mjd': 53632.19976407, 'exptime': 899.999, 'w_min_um': 0.495946, 'w_max_um': 0.707059, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-14T12%3A12%3A08.474', 'bytes': 2116800}, {'dp_id': 'ADP.2020-07-11T04:16:50.455', 'inst': 'ESO_UVES', 'mjd': 53993.30627217, 'exptime': 899.999, 'w_min_um': 0.495946, 'w_max_um': 0.707063, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-11T04%3A16%3A50.455', 'bytes': 2116800}, {'dp_id': 'ADP.2020-07-06T19:10:18.412', 'inst': 'ESO_UVES', 'mjd': 54042.09989537, 'exptime': 899.999, 'w_min_um': 0.49594400000000005, 'w_max_um': 0.707061, 'rp': 107200.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2020-07-06T19%3A10%3A18.412', 'bytes': 2119680}], 'HD98800': [{'dp_id': 'ADP.2024-03-09T06:44:09.456', 'inst': 'ESO_UVES', 'mjd': 60260.33629355, 'exptime': 700.0, 'w_min_um': 0.373218, 'w_max_um': 0.49998000000000004, 'rp': 71050.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2024-03-09T06%3A44%3A09.456', 'bytes': 2462400}, {'dp_id': 'ADP.2024-03-12T09:10:55.417', 'inst': 'ESO_UVES', 'mjd': 60354.18356197, 'exptime': 700.001, 'w_min_um': 0.37321899999999997, 'w_max_um': 0.499981, 'rp': 71050.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2024-03-12T09%3A10%3A55.417', 'bytes': 2453760}, {'dp_id': 'ADP.2024-05-02T13:33:35.880', 'inst': 'ESO_UVES', 'mjd': 60425.14230332, 'exptime': 699.998, 'w_min_um': 0.37321899999999997, 'w_max_um': 0.499981, 'rp': 71050.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2024-05-02T13%3A33%3A35.880', 'bytes': 2459520}, {'dp_id': 'ADP.2024-08-19T13:09:23.995', 'inst': 'ESO_UVES', 'mjd': 60507.01741091, 'exptime': 699.998, 'w_min_um': 0.37321699999999997, 'w_max_um': 0.499981, 'rp': 71050.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2024-08-19T13%3A09%3A23.995', 'bytes': 2462400}, {'dp_id': 'ADP.2025-04-16T09:37:21.158', 'inst': 'ESO_UVES', 'mjd': 60744.05048163, 'exptime': 700.0, 'w_min_um': 0.373218, 'w_max_um': 0.499981, 'rp': 71050.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2025-04-16T09%3A37%3A21.158', 'bytes': 2456640}, {'dp_id': 'ADP.2025-08-26T13:48:13.942', 'inst': 'ESO_UVES', 'mjd': 60875.98296856, 'exptime': 700.0, 'w_min_um': 0.373216, 'w_max_um': 0.49998000000000004, 'rp': 71050.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2025-08-26T13%3A48%3A13.942', 'bytes': 2468160}], 'HD113538': [{'dp_id': 'ADP.2014-10-01T10:22:07.523', 'inst': 'ESO_HARPS', 'mjd': 53047.37962146, 'exptime': 198.796, 'w_min_um': 0.378183, 'w_max_um': 0.691337, 'rp': 115000.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2014-10-01T10%3A22%3A07.523', 'bytes': 5261760}, {'dp_id': 'ADP.2014-09-24T09:41:48.680', 'inst': 'ESO_HARPS', 'mjd': 55334.1384702, 'exptime': 180.506, 'w_min_um': 0.378147, 'w_max_um': 0.691271, 'rp': 115000.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2014-09-24T09%3A41%3A48.680', 'bytes': 5264640}, {'dp_id': 'ADP.2014-10-06T10:06:57.610', 'inst': 'ESO_HARPS', 'mjd': 56311.32843754, 'exptime': 336.54, 'w_min_um': 0.378189, 'w_max_um': 0.6913379999999999, 'rp': 115000.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2014-10-06T10%3A06%3A57.610', 'bytes': 5264640}, {'dp_id': 'ADP.2021-03-05T01:11:43.835', 'inst': 'ESO_HARPS', 'mjd': 59277.39230321, 'exptime': 289.831, 'w_min_um': 0.37822, 'w_max_um': 0.6913239999999999, 'rp': 115000.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2021-03-05T01%3A11%3A43.835', 'bytes': 5264640}, {'dp_id': 'ADP.2025-03-27T01:01:10.744', 'inst': 'ESO_HARPS', 'mjd': 60760.30390663, 'exptime': 289.83, 'w_min_um': 0.378328, 'w_max_um': 0.691309, 'rp': 115000.0, 'url': 'https://dataportal.eso.org/dataPortal/file/ADP.2025-03-27T01%3A01%3A10.744', 'bytes': 5261760}]}

def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _ang_sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    c = max(-1.0, min(1.0, math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)))
    return math.degrees(math.acos(c)) * 3600.0


def _ecliptic_lat_deg(ra_deg: float, dec_deg: float) -> float:
    eps = math.radians(23.4392911)
    a, d = math.radians(ra_deg), math.radians(dec_deg)
    sb = max(-1.0, min(1.0, math.sin(d) * math.cos(eps) - math.cos(d) * math.sin(eps) * math.sin(a)))
    return math.degrees(math.asin(sb))


def _event_delays_days(ra_deg: float, dec_deg: float, dist_pc: float) -> tuple[float, float, float]:
    # Light travel projection (unit vector dot event direction) * D / c
    # Events: SN1987A (83.866,-69.270), GW170817 (197.450,-23.381), SN2023ixf (210.911,+54.312)
    r, d = math.radians(ra_deg), math.radians(dec_deg)
    ux, uy, uz = math.cos(d) * math.cos(r), math.cos(d) * math.sin(r), math.sin(d)
    d_lt_days = dist_pc * 3.26156378 * 365.25
    out = []
    for era, edec in ((83.866, -69.270), (197.450, -23.381), (210.911, 54.312)):
        er, ed = math.radians(era), math.radians(edec)
        vx, vy, vz = math.cos(ed) * math.cos(er), math.cos(ed) * math.sin(er), math.sin(ed)
        dot = ux * vx + uy * vy + uz * vz
        out.append(round(d_lt_days * (dot - 1.0), 3))
    return out[0], out[1], out[2]


def _kepler_kp_and_rv(m_msun: float, per_days: float, mjd_obs: float, t0_bjd: float) -> tuple[float, float, float]:
    p_s = max(1e3, per_days * DAY_S)
    m_g = max(0.05, m_msun) * MSUN_G
    a_cm = (G_CGS * m_g * (p_s / (2.0 * math.pi)) ** 2) ** (1.0 / 3.0)
    kp_kms = (2.0 * math.pi * a_cm / p_s) / 1e5
    bjd_obs = mjd_obs + 2400000.5
    ph = ((bjd_obs - t0_bjd) / per_days) % 1.0
    signed_ph = ph - 1.0 if ph > 0.5 else ph
    rv_kms = kp_kms * math.sin(2.0 * math.pi * ph)
    return kp_kms, signed_ph, rv_kms


def _fmt_num(x: Any, prec: int = 6) -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return ""
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, int):
        return str(x)
    return str(round(float(x), prec))


def main() -> None:
    if IN_DIR.exists():
        raise RuntimeError(f"STRICT LOCK VIOLATION: {IN_DIR} already exists before Stage-1 seal!")

    # 1. Build PRIOR_V5_6_PHASES_SNAPSHOT.json from WS98 + Companion Archives X/W/V/U/T
    ws98_sum = json.loads((WS98 / "results/SUMMARY.json").read_text(encoding="utf-8"))
    syn98 = ws98_sum["unified_473star_panchromatic_v5_6_synthesis"]
    ws98_ps = json.loads((WS98 / "PRIOR_V5_5_PHASES_SNAPSHOT.json").read_text(encoding="utf-8"))
    with (WS98 / "results/UNIFIED_PANCHROMATIC_V5_6_SYNTHESIS_473STARS.csv").open(newline="", encoding="utf-8") as fh:
        u473_rows = list(csv.DictReader(fh))
    with (WS98 / "results/PANCHROMATIC_BRIDGE_66STARS_V56.csv").open(newline="", encoding="utf-8") as fh:
        b66_rows = list(csv.DictReader(fh))
    with (WS98 / "results/ALLSKY_COMB_V4_1_UNIFIED_D079_D098.csv").open(newline="", encoding="utf-8") as fh:
        comb_u_rows = list(csv.DictReader(fh))
    with (WS98 / "results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D098.csv").open(newline="", encoding="utf-8") as fh:
        comb_c_rows = list(csv.DictReader(fh))
    with (WS98 / "results/MULTIEVENT_ELLIPSOID_473STARS.csv").open(newline="", encoding="utf-8") as fh:
        ell_rows = list(csv.DictReader(fh))

    u473_map = {r["star"]: r for r in u473_rows}

    arch_x_name = "SETI_D098_V5_6_SOFIA_GREAT_ISO_SWS_FORCAST_OPTICAL_JERK_RESULTS_2026-11-22.zip"
    arch_x_path = ARCHIVES / arch_x_name
    if not arch_x_path.exists():
        raise FileNotFoundError(f"Missing Archive X: {arch_x_path}")
    arch_x_sha = _sha256_file(arch_x_path)
    with zipfile.ZipFile(arch_x_path) as zf:
        mem_x = [n for n in zf.namelist() if n.endswith("d098_bounded_bundle.json.gz")][0]
        bun_x_sha = hashlib.sha256(zf.read(mem_x)).hexdigest()

    prior_snap = {
        "schema": "D099_PRIOR_V5_6_PHASES_SNAPSHOT",
        "prior_phases": "C001-C037 + D001-D098",
        "source_archive_x_name": arch_x_name,
        "source_archive_x_sha256": arch_x_sha,
        "source_archive_x_bundle_member": mem_x,
        "source_archive_x_bundle_sha256": bun_x_sha,
        "source_archive_w_name": ws98_ps["source_archive_w_name"],
        "source_archive_w_sha256": ws98_ps["source_archive_w_sha256"],
        "source_archive_w_bundle_member": ws98_ps["source_archive_w_bundle_member"],
        "source_archive_w_bundle_sha256": ws98_ps["source_archive_w_bundle_sha256"],
        "source_archive_v_name": ws98_ps["source_archive_v_name"],
        "source_archive_v_sha256": ws98_ps["source_archive_v_sha256"],
        "source_archive_v_bundle_member": ws98_ps["source_archive_v_bundle_member"],
        "source_archive_v_bundle_sha256": ws98_ps["source_archive_v_bundle_sha256"],
        "source_archive_u_name": ws98_ps["source_archive_u_name"],
        "source_archive_u_sha256": ws98_ps["source_archive_u_sha256"],
        "source_archive_u_bundle_member": ws98_ps["source_archive_u_bundle_member"],
        "source_archive_u_bundle_sha256": ws98_ps["source_archive_u_bundle_sha256"],
        "source_archive_t_name": ws98_ps["source_archive_t_name"],
        "source_archive_t_sha256": ws98_ps["source_archive_t_sha256"],
        "source_archive_t_bundle_member": ws98_ps["source_archive_t_bundle_member"],
        "source_archive_t_bundle_sha256": ws98_ps["source_archive_t_bundle_sha256"],
        "prior_unique_stars_count": int(syn98["unique_stars_total"]),
        "prior_science_stars_count": int(syn98["science_stars_total"]),
        "prior_control_stars_count": int(syn98["control_stars_total"]),
        "prior_planet_host_stars_count": int(syn98["planet_host_stars_total"]),
        "prior_confirmed_exoplanets_count": int(syn98["confirmed_exoplanets_total"]),
        "prior_within_10pc_count": int(syn98["within_10pc_unique_stars"]),
        "prior_total_exposures_count": int(syn98["total_exposures_d079_d098"]),
        "prior_cumulative_integration_hours": float(syn98["total_integration_hours_d079_d098"]),
        "prior_calibration_trials_count": int(syn98["total_calibration_trials_d079_d098"]),
        "prior_v2_false_alarms_eliminated_total": int(syn98["v2_false_alarms_eliminated_total"]),
        "prior_cumulative_orbital_campaigns_count": int(syn98["cumulative_orbital_campaigns"]),
        "prior_panchromatic_bridge_stars_count": int(syn98["panchromatic_bridge_stars_total"]),
        "prior_revisited_control_multi_phase_stars": int(syn98["revisited_control_multi_phase_stars"]),
        "prior_multi_phase_targets_total": int(syn98["multi_phase_targets_total"]),
        "prior_panchromatic_bridge_cells_count": int(syn98["panchromatic_bridge_cells_total"]),
        "prior_cumulative_comb_stacks": int(syn98["cumulative_comb_stacks"]),
        "prior_coherent_3d_drift_campaigns": int(syn98["coherent_3d_drift_campaigns"]),
        "d098_summary_headline": syn98,
        "prior_unified_473_rows": u473_rows,
        "prior_bridge_66_rows": b66_rows,
        "prior_allsky_comb_unified_rows": comb_u_rows,
        "prior_allsky_comb_candidate_rows": comb_c_rows,
        "prior_ellipsoid_473_rows": ell_rows,
    }
    (WS / "PRIOR_V5_6_PHASES_SNAPSHOT.json").write_text(json.dumps(prior_snap), encoding="utf-8")

    # 2. Load Prior Exclusion Registry (507 + D098 = 532+ unique coords, 2884 + 99 = 2983+ dp_ids)
    pe98 = json.loads((WS98 / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    excl_dps = set(pe98["excluded_dp_ids"])
    fmt_dps = set(pe98.get("format_check_excluded_dp_ids", []))
    fmt_dps.add("CADC.JCMT.jcmth20161118_00029_01_rimg_obs_000.fits")
    coord_reg = list(pe98["excluded_targets_coordinate_registry"])
    seen_st = {c.get("canonical_target", "") for c in coord_reg if c.get("canonical_target")}
    with (WS98 / "FROZEN_COHORT_D098.csv").open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            excl_dps.add(r["dp_id"])
            st = r["canonical_target"]
            if st not in seen_st:
                coord_reg.append({"canonical_target": st, "ra_deg": float(r["s_ra"]), "dec_deg": float(r["s_dec"])})
                seen_st.add(st)

    # 3. Verify separations and build FROZEN_COHORT_D099.csv + ORBITAL_CAMPAIGNS_AND_KINEMATICS.json
    def resolve_star_fields(st: str) -> dict[str, Any]:
        spec = STAR_SPECS[st]
        sim = SIMBAD_DATA[spec["sim"]]
        is_br = bool(spec.get("is_bridge", False))
        ra, dec = float(sim["ra"]), float(sim["dec"])
        dist_pc = spec.get("dist")
        if is_br and st in u473_map:
            u = u473_map[st]
            dist_pc = float(u["dist_pc"]) if u.get("dist_pc") else (float(sim["dist_pc"]) if math.isfinite(sim["dist_pc"]) else 500.0)
            return {
                "common_name": u["common_name"],
                "role": u["role"],
                "subrole": spec["sub"],
                "is_bridge": True,
                "ra": ra, "dec": dec,
                "pmra": float(sim["pmra"]), "pmdec": float(sim["pmdec"]),
                "dist_pc": dist_pc,
                "within_10pc": dist_pc <= 10.0,
                "g_mag": float(sim["g_mag"]) if math.isfinite(sim["g_mag"]) else (float(u["phot_g_mag"]) if u.get("phot_g_mag") else math.nan),
                "j_mag": float(sim["j_mag"]) if math.isfinite(sim["j_mag"]) else (float(u["j_mag"]) if u.get("j_mag") else math.nan),
                "h_mag": float(sim["h_mag"]) if math.isfinite(sim["h_mag"]) else (float(u["h_mag"]) if u.get("h_mag") else math.nan),
                "ks_mag": float(sim["ks_mag"]) if math.isfinite(sim["ks_mag"]) else (float(u["ks_mag"]) if u.get("ks_mag") else math.nan),
                "teff_k": float(u["teff_k"]) if u.get("teff_k") else 4500.0,
                "mh_dex": 0.0,
                "mass_msun": 1.0,
                "rv_kms": float(sim["rv_kms"]),
                "n_pl": int(u["n_exoplanets"]),
                "has_tr": False,
                "gaia_id": f"PRIOR_{st}",
            }
        if dist_pc is None:
            dist_pc = float(sim["dist_pc"]) if math.isfinite(sim["dist_pc"]) else 500.0
        return {
            "common_name": spec["common"],
            "role": spec["role"],
            "subrole": spec["sub"],
            "is_bridge": False,
            "ra": ra, "dec": dec,
            "pmra": float(sim["pmra"]), "pmdec": float(sim["pmdec"]),
            "dist_pc": dist_pc,
            "within_10pc": dist_pc <= 10.0,
            "g_mag": float(sim["g_mag"]),
            "j_mag": float(sim["j_mag"]),
            "h_mag": float(sim["h_mag"]),
            "ks_mag": float(sim["ks_mag"]),
            "teff_k": float(spec["teff"]),
            "mh_dex": 0.0,
            "mass_msun": float(spec["mass"]),
            "rv_kms": float(sim["rv_kms"]),
            "n_pl": int(spec["npl"]),
            "has_tr": False,
            "gaia_id": sim["main_id"],
        }

    sep_checks: list[dict[str, Any]] = []
    min_bn_sep = 1e9
    bn_targets = [st for st, sp in STAR_SPECS.items() if not sp.get("is_bridge")]
    for st in bn_targets:
        sf = resolve_star_fields(st)
        b_sep, b_ref = min((_ang_sep_arcsec(sf["ra"], sf["dec"], c["ra_deg"], c["dec_deg"]), c.get("canonical_target") or str(round(c["ra_deg"], 3))) for c in coord_reg)
        min_bn_sep = min(min_bn_sep, b_sep)
        if b_sep < 300.0:
            raise RuntimeError(f"Prior coordinate collision on brand-new {st}: sep={b_sep:.1f} arcsec from {b_ref}")
        sep_checks.append({"star": st, "min_sep_prior_arcsec": round(b_sep, 2), "nearest_prior": b_ref})

    br_targets = [st for st, sp in STAR_SPECS.items() if sp.get("is_bridge")]
    for st in br_targets:
        sf = resolve_star_fields(st)
        if st not in u473_map:
            raise RuntimeError(f"Prior bridge {st} missing from UNIFIED_473!")
        sp_b = min(_ang_sep_arcsec(sf["ra"], sf["dec"], c["ra_deg"], c["dec_deg"]) for c in coord_reg)
        if sp_b > 60.0:
            raise RuntimeError(f"Bridge {st} separation {sp_b:.1f} arcsec exceeds 60 arcsec")

    # Intra-D099 min separation between distinct canonical targets
    all_sf = {st: resolve_star_fields(st) for st in STAR_SPECS}
    sts_sorted = sorted(all_sf.keys())
    min_intra = 1e9
    for i, a in enumerate(sts_sorted):
        for b in sts_sorted[i + 1 :]:
            d_ab = _ang_sep_arcsec(all_sf[a]["ra"], all_sf[a]["dec"], all_sf[b]["ra"], all_sf[b]["dec"])
            if d_ab < min_intra:
                min_intra = d_ab
    if min_intra < 60.0:
        raise RuntimeError(f"Duplicate/near-duplicate intra-D099 target! min_sep={min_intra:.1f} arcsec")

    frozen_rows: list[dict[str, str]] = []
    d099_dps: set[str] = set()
    campaigns_dict: dict[str, Any] = {}

    def add_row(inst: str, st: str, track: str, erank: int, dp_id: str, grating: str, rp: float, mjd: float, expt: float, pwin: str, sph: float, orb_rv: float, f1_id: str, f1_rel: str, f1_url: str, f1_bytes: int) -> None:
        if dp_id in excl_dps or dp_id in fmt_dps or dp_id in d099_dps:
            raise RuntimeError(f"dp_id exclusion/duplicate violation: {dp_id}")
        d099_dps.add(dp_id)
        sf = all_sf[st]
        elat = _ecliptic_lat_deg(sf["ra"], sf["dec"])
        sn87, gw17, sn23 = _event_delays_days(sf["ra"], sf["dec"], sf["dist_pc"])
        has_pan = sf["is_bridge"] or (st in {"RLEO", "TXCAM"})
        frozen_rows.append({
            "instrument": inst,
            "canonical_target": st,
            "common_name": sf["common_name"],
            "role": sf["role"],
            "subrole": sf["subrole"],
            "science_track": track,
            "panchromatic_bridge": str(has_pan),
            "is_prior_bridge": str(sf["is_bridge"]),
            "gaia_source_id": sf["gaia_id"],
            "s_ra": _fmt_num(sf["ra"], 7),
            "s_dec": _fmt_num(sf["dec"], 7),
            "pmra_mas_yr": _fmt_num(sf["pmra"], 3),
            "pmdec_mas_yr": _fmt_num(sf["pmdec"], 3),
            "dist_pc": _fmt_num(sf["dist_pc"], 4),
            "within_10pc": str(sf["within_10pc"]),
            "phot_g_mag": _fmt_num(sf["g_mag"], 4),
            "phot_bp_mag": "",
            "phot_rp_mag": "",
            "j_mag": _fmt_num(sf["j_mag"], 3),
            "h_mag": _fmt_num(sf["h_mag"], 3),
            "ks_mag": _fmt_num(sf["ks_mag"], 3),
            "teff_k": _fmt_num(sf["teff_k"], 1),
            "mh_dex": _fmt_num(sf["mh_dex"], 2),
            "stellar_mass_msun": _fmt_num(sf["mass_msun"], 3),
            "prior_rv_kms": _fmt_num(sf["rv_kms"], 4),
            "n_exoplanets": str(sf["n_pl"]),
            "has_transiting_planet": "False",
            "ecliptic_lat_deg": _fmt_num(elat, 5),
            "sn1987a_dt_days": _fmt_num(sn87, 3),
            "gw170817_dt_days": _fmt_num(gw17, 3),
            "sn2023ixf_dt_days": _fmt_num(sn23, 3),
            "ppo_align_score": "1.0",
            "epoch_rank": str(erank),
            "dp_id": dp_id,
            "grating": grating,
            "resolving_power": _fmt_num(rp, 2),
            "mjd_obs": _fmt_num(mjd, 6),
            "t_exptime": _fmt_num(expt, 2),
            "phase_window": pwin,
            "signed_phase": _fmt_num(sph, 6),
            "planet_orbital_rv_kms": _fmt_num(orb_rv, 4),
            "f1_id": f1_id,
            "f1_rel": f1_rel,
            "f1_url": f1_url,
            "f1_bytes": str(int(f1_bytes)),
            "total_bytes": str(int(f1_bytes)),
        })

    # Stream 1: JCMT (HARP-ACSIS -> JCMT_HARP; RXA3/RXA3M/UU-ACSIS -> JCMT_MM_230GHZ)
    for st, recs in sorted(JCMT_SPECS.items()):
        for rk, g in enumerate(recs, 1):
            inst = "JCMT_HARP" if ("HARP" in g["inst"] or "RXW" in g["inst"]) else "JCMT_MM_230GHZ"
            grating = g["inst"].replace("-", "_")
            rp_est = 3.0e6 if inst == "JCMT_MM_230GHZ" else 5.0e6
            add_row(inst, st, "JCMT_SUBMM_MM_V57", rk, g["dp_id"], grating, rp_est, g["t_min"], g["t_exptime"], "NONE", 0.0, 0.0, g["fname"][:-5], f"{inst}/{st}/{g['fname']}", g["url"], g["bytes"])

    # Stream 2: SOFIA_EXES MRD
    for st, recs in sorted(EXES_SPECS.items()):
        for rk, g in enumerate(recs, 1):
            w_um = 0.5 * (float(g["w_lo_um"]) + float(g["w_hi_um"]))
            add_row("SOFIA_EXES", st, "SOFIA_EXES_MRD_V57", rk, g["dp_id"], f"EXES_MRD_{w_um:.1f}UM", float(g["rp"]), g["mjd"], g["exptime"], "NONE", 0.0, 0.0, g["fname"][:-5], f"SOFIA_EXES/{st}/{g['fname']}", g["url"], g["bytes"])

    # Stream 3: IRTF_SPEX
    for st in SPEX_LIST:
        g = SPEX_SPECS[st]
        fn = g["filename"]
        add_row("IRTF_SPEX", st, "IRTF_SPEX_NIR_QCL_V57", 1, f"IRTF_SPEX.{fn[:-5]}", "SPEX_SXD_LXD", 2000.0, 52800.0, 120.0, "NONE", 0.0, 0.0, fn[:-5], f"IRTF_SPEX/{st}/{fn}", g["url"], g["bytes"])

    # Stream 4: ESO UVES & HARPS (DRIFT_V57 + Orbital #144, #145)
    for st, eps in sorted(ESO_SPECS.items()):
        sp = STAR_SPECS[st]
        has_orb = "orb_p" in sp
        camp_exps = []
        kp_kms = 0.0
        orb_rvs = []
        for rk, g in enumerate(eps, 1):
            inst = g["inst"]
            sph, orb_rv, pwin = 0.0, 0.0, "NONE"
            if has_orb:
                kp_kms, sph, orb_rv = _kepler_kp_and_rv(float(sp["mass"]), float(sp["orb_p"]), float(g["mjd"]), 2456000.0)
                pwin = "IN_QUADRATURE" if abs(abs(sph) - 0.25) <= 0.14 else "IN_WINDOW"
                orb_rvs.append(orb_rv)
            gr = "HARPS_380_690" if inst == "ESO_HARPS" else ("UVES_BLUE_373_500" if float(g["w_max_um"]) < 0.55 else "UVES_RED_500_710")
            fn_clean = g["dp_id"].replace(":", "_") + ".fits"
            add_row(inst, st, "DRIFT_V57_KEPLERIAN_JERK", rk, g["dp_id"], gr, float(g["rp"]), float(g["mjd"]), float(g["exptime"]), pwin, sph, orb_rv, g["dp_id"], f"{inst}/{st}/{fn_clean}", g["url"], g["bytes"])
            camp_exps.append({
                "dp_id": g["dp_id"], "mjd_obs": round(float(g["mjd"]), 6),
                "bjd_tdb_est": round(float(g["mjd"]) + 2400000.5, 6),
                "signed_phase": round(sph, 6), "phase_window": pwin,
                "planet_orbital_rv_kms": round(orb_rv, 4), "ppo_align_score": 1.0,
            })
        if sp.get("camp_idx"):
            periods_all = [float(sp["orb_p"])]
            if "orb_p2" in sp:
                periods_all.append(float(sp["orb_p2"]))
            campaigns_dict[st] = {
                "campaign_index": int(sp["camp_idx"]),
                "canonical_target": st,
                "common_name": sp["common"],
                "instrument": eps[0]["inst"],
                "role": sp["role"],
                "null_orbital": False,
                "planet_name": sp["pl_name"],
                "n_planets_in_system": int(sp["npl"]),
                "stellar_mass_msun": float(sp["mass"]),
                "orb_per_days": float(sp["orb_p"]),
                "orb_periods_days": periods_all,
                "orb_t0_bjd": 2456000.0,
                "orb_ecc": float(sp["orb_e"]),
                "kp_kms": round(kp_kms, 3),
                "orbital_dv_span_kms": round(max(orb_rvs) - min(orb_rvs), 3) if orb_rvs else 0.0,
                "n_epochs": len(eps),
                "baseline_days": round(max(e["mjd"] for e in eps) - min(e["mjd"] for e in eps), 2),
                "exposures": camp_exps,
            }

    cohort_csv = WS / "FROZEN_COHORT_D099.csv"
    with cohort_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FROZEN_HEADER)
        w.writeheader()
        w.writerows(frozen_rows)

    tot_bytes = sum(int(r["f1_bytes"]) for r in frozen_rows)
    tot_mib = tot_bytes / float(1 << 20)
    if tot_mib > 125.0:
        raise RuntimeError(f"Projected total {tot_mib:.3f} MiB exceeds 125.0 MiB!")

    # Write PRIOR_EXCLUSION_VERIFICATION.json
    n_bn_10pc = sum(1 for st in bn_targets if all_sf[st]["within_10pc"])
    n_bn_ctrl = sum(1 for st in bn_targets if all_sf[st]["role"] == "CONTROL")
    pe_out = {
        "schema": "D099_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D099",
        "verified_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "prior_phases_covered": "C001-C037 + D001-D098",
        "n_prior_excluded_coords": len(coord_reg),
        "n_prior_excluded_dp_ids": len(excl_dps),
        "n_format_check_excluded_dp_ids": len(fmt_dps),
        "d099_total_stars": len(STAR_SPECS),
        "d099_brand_new_unique_stars": len(bn_targets),
        "d099_prior_bridge_stars": len(br_targets),
        "d099_control_stars": sum(1 for st in STAR_SPECS if all_sf[st]["role"] == "CONTROL"),
        "d099_brand_new_controls": n_bn_ctrl,
        "d099_brand_new_within_10pc": n_bn_10pc,
        "d099_total_input_files": len(frozen_rows),
        "d099_projected_download_bytes": tot_bytes,
        "d099_projected_download_mib": round(tot_mib, 4),
        "d099_dp_id_overlap_count": 0,
        "min_brand_new_sky_separation_arcsec": round(min_bn_sep, 2),
        "min_intra_d099_separation_arcsec": round(min_intra, 2),
        "star_separation_verification": sep_checks,
        "format_check_excluded_dp_ids": sorted(fmt_dps),
        "excluded_dp_ids": sorted(excl_dps),
        "excluded_targets_coordinate_registry": coord_reg,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pe_out), encoding="utf-8")

    # Write ORBITAL_CAMPAIGNS_AND_KINEMATICS.json
    orb_out = {
        "schema": "D099_ORBITAL_CAMPAIGNS_AND_KINEMATICS",
        "phase_id": "D099",
        "campaign_range": "#144-#145",
        "n_campaigns": len(campaigns_dict),
        "campaigns": campaigns_dict,
    }
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_out, indent=2), encoding="utf-8")

    # Seal all 7 Stage-1 files into METHOD_LOCK.json and LOCK_RECEIPT.json
    stage1_names = [
        "v5_7_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D099.csv",
        "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "PRIOR_V5_6_PHASES_SNAPSHOT.json",
    ]
    hashes = {nm: _sha256_file(WS / nm) for nm in stage1_names}
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
    ml_out = {
        "schema": "D099_PROSPECTIVE_METHOD_LOCK",
        "phase_id": "D099",
        "detector_version": "V5.7",
        "detector": "TECHNOSIGNATURE_V5_7_JCMT_MM_SOFIA_EXES_IRTF_SPEX_KEPLERIAN_DRIFT",
        "locked_utc": now_iso,
        "projected_unified_stars": int(syn98["unique_stars_total"]) + len(bn_targets),
        "d099_brand_new_stars": len(bn_targets),
        "d099_prior_bridges": len(br_targets),
        "d099_total_files": len(frozen_rows),
        "d099_projected_bytes": tot_bytes,
        "d099_projected_mib": round(tot_mib, 4),
        "stage_1_files": hashes,
    }
    ml_p = WS / "METHOD_LOCK.json"
    ml_p.write_text(json.dumps(ml_out, indent=2), encoding="utf-8")
    ml_sha = _sha256_file(ml_p)

    now_epoch = time.time()
    lr_out = {
        "schema": "D099_LOCK_RECEIPT",
        "phase_id": "D099",
        "status": "STAGE-1 SEALED",
        "locked_utc": now_iso,
        "locked_unix_epoch": round(now_epoch, 3),
        "method_lock_sha256": ml_sha,
        "inputs_dir_exists_at_seal": IN_DIR.exists(),
        "locked_files": hashes,
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lr_out, indent=2), encoding="utf-8")
    print(f"STAGE-1 SEALED: {ml_out['projected_unified_stars']} projected unified stars (473 + {len(bn_targets)}), {len(frozen_rows)} FITS ({tot_mib:.3f} MiB <= 125.0 MiB), 7/7 Stage-1 files locked.", flush=True)


if __name__ == "__main__":
    main()
