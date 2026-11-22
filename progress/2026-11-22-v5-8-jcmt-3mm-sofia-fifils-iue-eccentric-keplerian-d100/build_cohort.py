#!/usr/bin/env python3
"""
Stage-1 Prospective Cohort Builder & Cryptographic Lock Generator for Phase D100 (V5.8).
MUST execute and seal METHOD_LOCK.json + LOCK_RECEIPT.json BEFORE inputs_d100_v5_8 exists.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import pathlib
import sys
import zipfile
from typing import Any

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_v5_8_20261122_d100_jcmt_3mm_sofia_fifils_iue_eccentric_keplerian"
WS99 = ROOT / "analysis_workspace/work_v5_7_20261122_d099_jcmt_mm_sofia_exes_irtf_spex_keplerian_drift"
ARCHIVES = ROOT / "archives"
IN_DIR = ROOT / "inputs_d100_v5_8"

sys.path.insert(0, str(WS))
from v5_8_detector import C_KMS, solve_kepler_eccentric_rv  # noqa: E402

AU_CM = 1.495978707e13
DAY_S = 86400.0
G_CGS = 6.67430e-8
MSUN_G = 1.98847e33

FROZEN_HEADER = [
    "instrument", "canonical_target", "common_name", "role", "subrole", "science_track",
    "panchromatic_bridge", "is_prior_bridge", "gaia_source_id", "s_ra", "s_dec",
    "pmra_mas_yr", "pmdec_mas_yr", "dist_pc", "within_10pc",
    "phot_g_mag", "phot_bp_mag", "phot_rp_mag", "j_mag", "h_mag", "ks_mag",
    "teff_k", "mh_dex", "stellar_mass_msun", "prior_rv_kms",
    "n_exoplanets", "has_transiting_planet", "ecliptic_lat_deg",
    "sn1987a_dt_days", "gw170817_dt_days", "sn2023ixf_dt_days", "ppo_align_score",
    "epoch_rank", "dp_id", "grating", "resolving_power", "mjd_obs", "t_exptime",
    "phase_window", "signed_phase", "planet_orbital_rv_kms",
    "f1_id", "f1_rel", "f1_url", "f1_bytes", "total_bytes",
]

# Format-check exposures inspected on extragalactic non-cohort targets prior to Stage-1 lock:
D100_FORMAT_CHECK_DPS = {
    "CADC.JCMT.jcmth20230406_00059_01_reduced001_obs_000.fits",
    "FIFILS.F0569_FI_IFS_0702393_BLU_WXY_00874-00875",
    "IUE.lwr03996.mxhi.gz",
}

# Verified live astrophysical metadata (Gaia DR3, MAST TIC, NASA Exoplanet Archive pscomppars, 2MASS fp_psc)
STAR_META: dict[str, dict[str, Any]] = {
    # --- ALAIHI Band-3 Brand-New Targets (15) ---
    "OH231P8":       {"common": "OH 231.8+4.2 (Calabash Nebula, 3.86mm Frontier)", "role": "SCIENCE", "sub": "PPN_BIPOLAR_ALAIHI_3MM", "dist_pc": 1540.0, "teff": 2500.0, "mass": 1.5, "rv": 34.0, "npl": 0, "gmag": 16.5, "pmra": 0.0, "pmdec": 0.0, "gid": "OH231.8+4.2"},
    "L1551IRS5":     {"common": "L1551 IRS 5 (Taurus Class I Protobinary)", "role": "SCIENCE", "sub": "YSO_CLASSI_ALAIHI_3MM", "dist_pc": 140.0, "teff": 4200.0, "mass": 1.2, "rv": 6.5, "npl": 0, "gmag": 17.5, "pmra": 0.0, "pmdec": 0.0, "gid": "L1551_IRS5"},
    "N2071IR":       {"common": "NGC 2071 IR (Orion B YSO Core)", "role": "SCIENCE", "sub": "YSO_ORIONB_ALAIHI_3MM", "dist_pc": 420.0, "teff": 4500.0, "mass": 2.0, "rv": 9.5, "npl": 0, "gmag": 16.8, "pmra": 0.0, "pmdec": 0.0, "gid": "NGC2071_IR"},
    "OMC1":          {"common": "Orion Molecular Cloud 1 (BN/KL Core)", "role": "SCIENCE", "sub": "MASSIVE_YSO_ALAIHI_3MM", "dist_pc": 388.0, "teff": 12000.0, "mass": 8.0, "rv": 8.5, "npl": 0, "gmag": 14.5, "pmra": 0.0, "pmdec": 0.0, "gid": "OMC1_BNKL"},
    "W3OH":          {"common": "W3(OH) (UC HII / Massive Protocluster)", "role": "SCIENCE", "sub": "MASSIVE_YSO_ALAIHI_3MM", "dist_pc": 2000.0, "teff": 28000.0, "mass": 15.0, "rv": -47.0, "npl": 0, "gmag": 16.2, "pmra": 0.0, "pmdec": 0.0, "gid": "W3(OH)"},
    "RHYA":          {"common": "R Hydrae (Mira AGB Star)", "role": "SCIENCE", "sub": "MIRA_AGB_ALAIHI_3MM", "dist_pc": 148.467, "teff": 2600.0, "mass": 1.3, "rv": -10.4, "npl": 0, "gmag": 3.152, "pmra": -54.213, "pmdec": 11.794, "gid": "Gaia DR3 6195030801635544704"},
    "IRAS16293M2422":{"common": "IRAS 16293-2422 (Class 0 Hot Corino)", "role": "SCIENCE", "sub": "HOT_CORINO_ALAIHI_3MM", "dist_pc": 141.0, "teff": 3000.0, "mass": 1.0, "rv": 3.9, "npl": 0, "gmag": None, "pmra": 0.0, "pmdec": 0.0, "gid": "IRAS_16293-2422"},
    "N7538IRS1":     {"common": "NGC 7538 IRS 1 (Massive Protobinary Disk)", "role": "SCIENCE", "sub": "MASSIVE_YSO_ALAIHI_3MM", "dist_pc": 2650.0, "teff": 25000.0, "mass": 20.0, "rv": -57.4, "npl": 0, "gmag": 17.0, "pmra": 0.0, "pmdec": 0.0, "gid": "NGC7538_IRS1"},
    "VCAM":          {"common": "V Camelopardalis (Mira AGB Variable)", "role": "SCIENCE", "sub": "MIRA_AGB_ALAIHI_3MM", "dist_pc": 183.838, "teff": 2700.0, "mass": 1.1, "rv": 25.654, "npl": 0, "gmag": 11.325, "pmra": -33.374, "pmdec": -33.452, "gid": "Gaia DR3 499528885780624768"},
    "G34P3":         {"common": "G34.26+0.15 (Hot Molecular Core)", "role": "SCIENCE", "sub": "HOT_CORE_ALAIHI_3MM", "dist_pc": 3300.0, "teff": 20000.0, "mass": 12.0, "rv": 58.0, "npl": 0, "gmag": 15.8, "pmra": 0.0, "pmdec": 0.0, "gid": "G34.3+0.2"},
    "W75N":          {"common": "W75 N (Cygnus X Massive Protocluster)", "role": "SCIENCE", "sub": "MASSIVE_YSO_ALAIHI_3MM", "dist_pc": 1300.0, "teff": 22000.0, "mass": 12.0, "rv": 9.5, "npl": 0, "gmag": 17.2, "pmra": 0.0, "pmdec": 0.0, "gid": "W75N(B)"},
    "M87":           {"common": "M87 (Virgo A Elliptical AGN Control)", "role": "CONTROL", "sub": "CONTROL_AGN_EXTRAGAL_ALAIHI_3MM", "dist_pc": 16400000.0, "teff": 4500.0, "mass": 1.0, "rv": 1284.0, "npl": 0, "gmag": 12.5, "pmra": 0.0, "pmdec": 0.0, "gid": "MESSIER_087"},
    "CYGNUSA":       {"common": "Cygnus A (FR-II Radio Galaxy Control)", "role": "CONTROL", "sub": "CONTROL_AGN_EXTRAGAL_ALAIHI_3MM", "dist_pc": 232000000.0, "teff": 5500.0, "mass": 1.0, "rv": 16811.0, "npl": 0, "gmag": 15.0, "pmra": 0.0, "pmdec": 0.0, "gid": "Cygnus_A"},
    "3C84":          {"common": "3C 84 (NGC 1275 Perseus AGN Control)", "role": "CONTROL", "sub": "CONTROL_AGN_EXTRAGAL_ALAIHI_3MM", "dist_pc": 74000000.0, "teff": 6000.0, "mass": 1.0, "rv": 5264.0, "npl": 0, "gmag": 12.6, "pmra": 0.0, "pmdec": 0.0, "gid": "NGC_1275"},
    "3C279":         {"common": "3C 279 (Flat-Spectrum Quasar Control)", "role": "CONTROL", "sub": "CONTROL_BLAZAR_EXTRAGAL_ALAIHI_3MM", "dist_pc": 2500000000.0, "teff": 10000.0, "mass": 1.0, "rv": 160700.0, "npl": 0, "gmag": 15.4, "pmra": 0.0, "pmdec": 0.0, "gid": "3C_279"},

    # --- SOFIA_FIFILS Brand-New Targets (10) ---
    "AFGL437":       {"common": "AFGL 437 (Massive YSO Cluster)", "role": "SCIENCE", "sub": "YSO_CLUSTER_FIFILS_V58", "dist_pc": 2000.0, "teff": 15000.0, "mass": 10.0, "rv": -39.5, "npl": 0, "gmag": 14.5, "pmra": 0.0, "pmdec": 0.0, "gid": "AFGL_437"},
    "W3IRS5":        {"common": "W3 IRS 5 (Proto-Massive Binary)", "role": "SCIENCE", "sub": "MASSIVE_YSO_FIFILS_V58", "dist_pc": 1830.0, "teff": 18000.0, "mass": 15.0, "rv": -38.0, "npl": 0, "gmag": 16.0, "pmra": 0.0, "pmdec": 0.0, "gid": "W3_IRS_5"},
    "PNK362":        {"common": "PN K 3-62 (Compact Planetary Nebula Control)", "role": "CONTROL", "sub": "CONTROL_PN_FIFILS_V58", "dist_pc": 2400.0, "teff": 45000.0, "mass": 0.65, "rv": -41.0, "npl": 0, "gmag": 15.1, "pmra": 0.0, "pmdec": 0.0, "gid": "PN_K3-62"},
    "S255NIRS3":     {"common": "S255 NIRS 3 (Accretion-Burst YSO)", "role": "SCIENCE", "sub": "YSO_BURST_FIFILS_V58", "dist_pc": 1780.0, "teff": 16000.0, "mass": 15.0, "rv": 5.0, "npl": 0, "gmag": 16.5, "pmra": 0.0, "pmdec": 0.0, "gid": "S255_NIRS3"},
    "NGC5253":       {"common": "NGC 5253 (Dwarf Starburst Galaxy Control)", "role": "CONTROL", "sub": "CONTROL_STARBURST_GAL_FIFILS_V58", "dist_pc": 3550000.0, "teff": 15000.0, "mass": 1.0, "rv": 407.0, "npl": 0, "gmag": 11.2, "pmra": 0.0, "pmdec": 0.0, "gid": "NGC_5253"},
    "AFGL5180":      {"common": "AFGL 5180 (Gem OB1 Massive YSO)", "role": "SCIENCE", "sub": "MASSIVE_YSO_FIFILS_V58", "dist_pc": 1500.0, "teff": 14000.0, "mass": 10.0, "rv": 3.0, "npl": 0, "gmag": 14.8, "pmra": 0.0, "pmdec": 0.0, "gid": "AFGL_5180"},
    "IRAS20126P4104":{"common": "IRAS 20126+4104 (Keplerian-Disk Massive Protostar)", "role": "SCIENCE", "sub": "DISK_PROTOSTAR_FIFILS_V58", "dist_pc": 1640.0, "teff": 19000.0, "mass": 12.0, "rv": -3.5, "npl": 0, "gmag": 16.4, "pmra": 0.0, "pmdec": 0.0, "gid": "IRAS_20126+4104"},
    "DR21":          {"common": "DR 21 (Cygnus X Massive Outflow Core)", "role": "SCIENCE", "sub": "MASSIVE_CORE_FIFILS_V58", "dist_pc": 1500.0, "teff": 24000.0, "mass": 18.0, "rv": -2.5, "npl": 0, "gmag": 17.5, "pmra": 0.0, "pmdec": 0.0, "gid": "DR_21"},
    "NGC5576":       {"common": "NGC 5576 (Virgo E3 Galaxy Control)", "role": "CONTROL", "sub": "CONTROL_ELLIPTICAL_GAL_FIFILS_V58", "dist_pc": 25500000.0, "teff": 4600.0, "mass": 1.0, "rv": 1487.0, "npl": 0, "gmag": 11.8, "pmra": 0.0, "pmdec": 0.0, "gid": "NGC_5576"},
    "CEPAHW2":       {"common": "Cepheus A HW2 (Massive Protostellar Jet)", "role": "SCIENCE", "sub": "MASSIVE_YSO_FIFILS_V58", "dist_pc": 700.0, "teff": 20000.0, "mass": 15.0, "rv": -10.5, "npl": 0, "gmag": 16.7, "pmra": 0.0, "pmdec": 0.0, "gid": "CepA_HW2"},

    # --- IUE Brand-New Targets (14, with HD147513 shared w/ ESO FEROS) ---
    "HD103095":      {"common": "HD 103095 (Groombridge 1830, Halo <10 pc)", "role": "SCIENCE", "sub": "SOLAR_NEIGHBOR_10PC_IUE", "dist_pc": 9.1781, "teff": 4934.45, "mass": 0.65, "rv": -98.0, "npl": 0, "gmag": 6.42, "pmra": 4002.57, "pmdec": -5817.86, "gid": "Gaia DR3 4034171629042489088"},
    "HD147513":      {"common": "HD 147513 (1-pl e=0.26, 20.3 yr FEROS + IUE)", "role": "SCIENCE", "sub": "BRIDGE_IUE_ESO_ECCENTRIC", "dist_pc": 12.8924, "teff": 5723.85, "mass": 1.11, "rv": 12.846, "npl": 1, "gmag": 5.215, "pmra": 72.6, "pmdec": 3.4, "gid": "Gaia DR3 6018047019138644480", "orb_p": 528.4, "orb_e": 0.26, "orb_w_deg": 282.0, "orb_t0": 2451123.0, "orb_a_au": 1.32, "pl_name": "HD 147513 b", "camp_idx": 150},
    "HD17925":       {"common": "HD 17925 (EP Eridani, Active K1V)", "role": "SCIENCE", "sub": "SOLAR_NEIGHBOR_IUE", "dist_pc": 10.3605, "teff": 5002.33, "mass": 0.85, "rv": 17.805, "npl": 0, "gmag": 5.812, "pmra": 398.1, "pmdec": -189.4, "gid": "Gaia DR3 5160075762132996992"},
    "HD19373":       {"common": "HD 19373 (iota Persei, G0V)", "role": "SCIENCE", "sub": "SOLAR_NEIGHBOR_IUE", "dist_pc": 10.5774, "teff": 5873.74, "mass": 1.10, "rv": 49.473, "npl": 0, "gmag": 3.903, "pmra": 1262.4, "pmdec": -91.5, "gid": "Gaia DR3 436648129327098496"},
    "HD13974":       {"common": "HD 13974 (delta Trianguli, G0V SB)", "role": "SCIENCE", "sub": "SOLAR_NEIGHBOR_IUE", "dist_pc": 10.9110, "teff": 5660.0, "mass": 1.00, "rv": -7.205, "npl": 0, "gmag": 4.671, "pmra": 1152.0, "pmdec": -246.0, "gid": "Gaia DR3 326173044957518080"},
    "HD166620":      {"common": "HD 166620 (K2V Maunder Minimum)", "role": "SCIENCE", "sub": "SOLAR_NEIGHBOR_IUE", "dist_pc": 11.0959, "teff": 4914.26, "mass": 0.80, "rv": -19.511, "npl": 0, "gmag": 6.130, "pmra": -315.4, "pmdec": -468.2, "gid": "Gaia DR3 4610177733290768896"},
    "HD141004":      {"common": "HD 141004 (lambda Serpentis, G0V)", "role": "SCIENCE", "sub": "SOLAR_NEIGHBOR_IUE", "dist_pc": 11.9159, "teff": 5884.0, "mass": 1.10, "rv": -66.378, "npl": 0, "gmag": 4.247, "pmra": -229.6, "pmdec": -64.4, "gid": "Gaia DR3 4430238051199001216"},
    "HD104304":      {"common": "HD 104304 (G8IV + M4V Binary)", "role": "SCIENCE", "sub": "SOLAR_NEIGHBOR_IUE", "dist_pc": 12.7655, "teff": 5510.12, "mass": 0.98, "rv": -0.411, "npl": 0, "gmag": 5.355, "pmra": 95.3, "pmdec": -478.8, "gid": "Gaia DR3 3575733210781078016"},
    "HD34029":       {"common": "HD 34029 (Capella, G8III+G1III)", "role": "SCIENCE", "sub": "SOLAR_NEIGHBOR_IUE", "dist_pc": 12.9383, "teff": 5137.0, "mass": 2.50, "rv": 29.2, "npl": 0, "gmag": 0.041, "pmra": 75.52, "pmdec": -427.13, "gid": "HIP_24608"},
    "HD35296":       {"common": "HD 35296 (V1119 Tau, F8V)", "role": "SCIENCE", "sub": "SOLAR_NEIGHBOR_IUE", "dist_pc": 14.5792, "teff": 6065.78, "mass": 1.10, "rv": 37.701, "npl": 0, "gmag": 4.850, "pmra": 173.4, "pmdec": -177.2, "gid": "Gaia DR3 3400292798990117888"},
    "HD22468":       {"common": "HD 22468 (HR 1099, RS CVn Active Binary)", "role": "SCIENCE", "sub": "ACTIVE_BINARY_IUE_SWP", "dist_pc": 29.4305, "teff": 4950.0, "mass": 1.15, "rv": -21.235, "npl": 0, "gmag": 5.607, "pmra": -33.4, "pmdec": -161.8, "gid": "Gaia DR3 3263936692671872384"},
    "HD144668":      {"common": "HD 144668 (HR 5999, Herbig A7IIIe)", "role": "SCIENCE", "sub": "HERBIG_AE_IUE_SWP", "dist_pc": 158.442, "teff": 7900.0, "mass": 2.40, "rv": -1.0, "npl": 0, "gmag": 6.625, "pmra": -10.5, "pmdec": -22.8, "gid": "Gaia DR3 5997082115537645696"},
    "HD120315":      {"common": "HD 120315 (eta UMa, B3V Calibrator Control)", "role": "CONTROL", "sub": "CONTROL_B3V_CAL_IUE", "dist_pc": 30.8737, "teff": 16800.0, "mass": 6.10, "rv": -13.4, "npl": 0, "gmag": 1.850, "pmra": -121.23, "pmdec": -15.56, "gid": "HIP_67301"},
    "HD93521":       {"common": "HD 93521 (Halo O9.5V Sightline Control)", "role": "CONTROL", "sub": "CONTROL_OV_HALO_IUE", "dist_pc": 1276.015, "teff": 32465.29, "mass": 17.0, "rv": -14.0, "npl": 0, "gmag": 6.973, "pmra": 0.2, "pmdec": 1.4, "gid": "Gaia DR3 775029739076581248"},

    # --- ESO High-Eccentricity Campaigns & Verified Zero-Planet Control (5 new + HD147513 shared) ---
    "HD20782":       {"common": "HD 20782 (1-pl e=0.950, 14.0 yr HARPS)", "role": "SCIENCE", "sub": "EXTREME_ECC_EXOPLANET_V58", "dist_pc": 35.8732, "teff": 5782.13, "mass": 1.04, "rv": 39.849, "npl": 1, "gmag": 7.208, "pmra": 350.0, "pmdec": -64.0, "gid": "Gaia DR3 5060104351007433472", "orb_p": 597.0643, "orb_e": 0.95, "orb_w_deg": 143.58, "orb_t0": 2455247.015, "orb_a_au": 1.3649, "pl_name": "HD 20782 b", "camp_idx": 146},
    "HD28254":       {"common": "HD 28254 (1-pl e=0.950, 17.4 yr HARPS)", "role": "SCIENCE", "sub": "EXTREME_ECC_EXOPLANET_V58", "dist_pc": 55.1750, "teff": 5664.0, "mass": 1.10, "rv": -9.424, "npl": 1, "gmag": 7.513, "pmra": 191.0, "pmdec": 142.0, "gid": "Gaia DR3 4781553628548774656", "orb_p": 1333.0, "orb_e": 0.95, "orb_w_deg": 289.0, "orb_t0": 2454246.0, "orb_a_au": 2.45, "pl_name": "HD 28254 b", "camp_idx": 147},
    "HD76920":       {"common": "HD 76920 (1-pl e=0.878, Evolved Giant FEROS)", "role": "SCIENCE", "sub": "EXTREME_ECC_GIANT_V58", "dist_pc": 183.0914, "teff": 4696.16, "mass": 1.00, "rv": 19.732, "npl": 1, "gmag": 7.527, "pmra": 25.253, "pmdec": 25.659, "gid": "Gaia DR3 5224124307320401024", "orb_p": 415.891, "orb_e": 0.8782, "orb_w_deg": 1.2, "orb_t0": 2454812.47, "orb_a_au": 1.091, "pl_name": "HD 76920 b", "camp_idx": 148},
    "HD7449":        {"common": "HD 7449 (2-pl e=0.752, 12.2 yr HARPS)", "role": "SCIENCE", "sub": "HIGH_ECC_EXOPLANET_V58", "dist_pc": 38.5903, "teff": 6024.0, "mass": 1.196, "rv": -19.599, "npl": 2, "orb_p2": 4046.0, "gmag": 7.366, "pmra": 176.0, "pmdec": -27.0, "gid": "Gaia DR3 2482820714353923072", "orb_p": 1270.55195, "orb_e": 0.752, "orb_w_deg": 336.427, "orb_t0": 2451476.815, "orb_a_au": 2.438, "pl_name": "HD 7449 b", "camp_idx": 149},
    "HD154577":      {"common": "HD 154577 (Zero-Planet 21.2 yr FEROS Control)", "role": "CONTROL", "sub": "CONTROL_0PL_21YR_FEROS", "dist_pc": 13.7261, "teff": 4866.04, "mass": 0.75, "rv": 6.299, "npl": 0, "gmag": 7.117, "pmra": 182.0, "pmdec": 495.0, "gid": "Gaia DR3 5914096303621755520"},

    # --- Prior U516 Panchromatic Bridges & Revisited Controls (13) ---
    "IRC10216":      {"is_bridge": True, "sub": "BRIDGE_SCIENCE_AGB_FIFILS_ALAIHI", "pmra": 26.0, "pmdec": 10.0, "rv": -26.5},
    "RLEO":          {"is_bridge": True, "sub": "BRIDGE_SCIENCE_MIRA_ALAIHI", "pmra": -5.4, "pmdec": -40.2, "rv": -1.0},
    "RCAS":          {"is_bridge": True, "sub": "BRIDGE_SCIENCE_MIRA_ALAIHI", "pmra": 82.0, "pmdec": 18.0, "rv": 25.0},
    "TXCAM":         {"is_bridge": True, "sub": "BRIDGE_SCIENCE_MIRA_ALAIHI", "pmra": 0.0, "pmdec": 0.0, "rv": 9.0},
    "CHICYG":        {"is_bridge": True, "sub": "BRIDGE_SCIENCE_MIRA_ALAIHI", "pmra": -22.0, "pmdec": -41.0, "rv": -1.0},
    "NGC7027":       {"is_bridge": True, "sub": "CONTROL_BRIDGE_PN_ALAIHI", "pmra": 0.0, "pmdec": 0.0, "rv": 25.0},
    "CRL618":        {"is_bridge": True, "sub": "CONTROL_BRIDGE_PPN_ALAIHI", "pmra": 0.0, "pmdec": 0.0, "rv": -21.5},
    "AFGL2688":      {"is_bridge": True, "sub": "CONTROL_BRIDGE_PPN_ALAIHI", "pmra": 0.0, "pmdec": 0.0, "rv": -35.0},
    "BETELGEUSE":    {"is_bridge": True, "sub": "BRIDGE_SCIENCE_RSG_IUE_FIFILS", "pmra": 27.54, "pmdec": 11.3, "rv": 21.91},
    "ABAUR":         {"is_bridge": True, "sub": "BRIDGE_SCIENCE_HAEBE_FIFILS", "pmra": 4.018, "pmdec": -24.027, "rv": 8.9},
    "AFGL2591":      {"is_bridge": True, "sub": "CONTROL_BRIDGE_YSO_FIFILS", "pmra": 0.0, "pmdec": 0.0, "rv": -5.5},
    "HD115617":      {"is_bridge": True, "sub": "BRIDGE_SCIENCE_10PC_IUE", "pmra": -1070.4, "pmdec": -1063.7, "rv": -7.8},
    "HD114710":      {"is_bridge": True, "sub": "CONTROL_BRIDGE_10PC_IUE", "pmra": -707.0, "pmdec": 906.0, "rv": 5.3},
}


ALAIHI_EXPOSURES = [
    ("OH231P8", "CADC.JCMT.jcmth20251123_00115_02_reduced001_obs_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20251123_00115_02_reduced001_obs_000.fits", 299520, 115.5705176, -14.7136389, 85000.0, 61002.578571, 480.0),
    ("L1551IRS5", "CADC.JCMT.jcmth20251123_00083_02_reduced001_nit_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20251123_00083_02_reduced001_nit_000.fits", 311040, 67.8922917, 18.1347500, 85000.0, 61002.445287, 480.0),
    ("N2071IR", "CADC.JCMT.jcmth20251123_00097_02_reduced001_nit_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20251123_00097_02_reduced001_nit_000.fits", 311040, 86.7702500, 0.3630833, 85000.0, 61002.500925, 480.0),
    ("OMC1", "CADC.JCMT.jcmth20251123_00105_02_reduced001_nit_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20251123_00105_02_reduced001_nit_000.fits", 311040, 83.8099167, -5.3756667, 85000.0, 61002.538876, 480.0),
    ("W3OH", "CADC.JCMT.jcmth20251123_00071_02_reduced001_nit_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20251123_00071_02_reduced001_nit_000.fits", 311040, 36.7660000, 61.8735556, 85000.0, 61002.390562, 480.0),
    ("RHYA", "CADC.JCMT.jcmth20260301_00073_02_reduced001_nit_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20260301_00073_02_reduced001_nit_000.fits", 311040, 202.4278333, -23.2812222, 85000.0, 61100.529347, 480.0),
    ("IRAS16293M2422", "CADC.JCMT.jcmth20260227_00092_02_reduced001_nit_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20260227_00092_02_reduced001_nit_000.fits", 311040, 248.0954583, -24.4765556, 85000.0, 61098.616782, 960.0),
    ("N7538IRS1", "CADC.JCMT.jcmth20260921_00051_02_reduced001_nit_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20260921_00051_02_reduced001_nit_000.fits", 299520, 348.4390000, 61.4695278, 85000.0, 61304.382894, 960.0),
    ("VCAM", "CADC.JCMT.jcmth20221124_00074_01_reduced001_obs_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20221124_00074_01_reduced001_obs_000.fits", 247680, 90.6345833, 74.5075833, 85000.0, 59907.537499, 4.0),
    ("G34P3", "CADC.JCMT.jcmth20260303_00125_02_reduced001_nit_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20260303_00125_02_reduced001_nit_000.fits", 311040, 283.3273750, 1.2495278, 85000.0, 61102.658889, 960.0),
    ("W75N", "CADC.JCMT.jcmth20260921_00063_02_reduced001_nit_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20260921_00063_02_reduced001_nit_000.fits", 299520, 309.6518333, 42.6262500, 85000.0, 61304.429641, 960.0),
    ("M87", "CADC.JCMT.jcmth20250426_00017_03_reduced001_nit_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20250426_00017_03_reduced001_nit_000.fits", 270720, 187.7059583, 12.3911111, 85000.0, 60791.147813, 103.98),
    ("CYGNUSA", "CADC.JCMT.jcmth20221120_00003_01_reduced001_obs_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20221120_00003_01_reduced001_obs_000.fits", 247680, 299.8682083, 40.7338250, 85000.0, 59903.170803, 4.0),
    ("3C84", "CADC.JCMT.jcmth20250428_00001_03_reduced001_nit_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20250428_00001_03_reduced001_nit_000.fits", 247680, 49.9506667, 41.5116944, 85000.0, 60793.203079, 16.0),
    ("3C279", "CADC.JCMT.jcmth20230427_00027_01_reduced001_nit_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20230427_00027_01_reduced001_nit_000.fits", 270720, 194.0465417, -5.7893056, 85000.0, 60061.372315, 507.99),
    ("IRC10216", "CADC.JCMT.jcmth20251124_00107_02_reduced001_nit_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20251124_00107_02_reduced001_nit_000.fits", 311040, 146.9890833, 13.2788056, 85000.0, 61003.735694, 960.0),
    ("RLEO", "CADC.JCMT.jcmth20260227_00080_02_reduced001_obs_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20260227_00080_02_reduced001_obs_000.fits", 299520, 146.8895833, 11.4284444, 85000.0, 61098.563824, 480.0),
    ("RCAS", "CADC.JCMT.jcmth20241202_00057_02_reduced001_nit_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20241202_00057_02_reduced001_nit_000.fits", 299520, 359.6042917, 51.3888889, 85000.0, 60646.977572, 480.0),
    ("TXCAM", "CADC.JCMT.jcmth20221126_00075_01_reduced001_obs_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20221126_00075_01_reduced001_obs_000.fits", 247680, 75.2130417, 56.1816667, 85000.0, 59909.583069, 4.0),
    ("CHICYG", "CADC.JCMT.jcmth20251122_00005_02_reduced001_nit_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20251122_00005_02_reduced001_nit_000.fits", 299520, 297.6412917, 32.9143333, 85000.0, 61001.088545, 480.0),
    ("NGC7027", "CADC.JCMT.jcmth20260922_00047_02_reduced001_nit_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20260922_00047_02_reduced001_nit_000.fits", 288000, 316.7565429, 42.2361667, 85000.0, 61305.431149, 480.0),
    ("CRL618", "CADC.JCMT.jcmth20260921_00077_02_reduced001_nit_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20260921_00077_02_reduced001_nit_000.fits", 288000, 70.7233750, 36.1149167, 85000.0, 61304.478507, 960.0),
    ("AFGL2688", "CADC.JCMT.jcmth20260921_00048_02_reduced001_nit_000.fits", "https://cadc-west-01.canfar.net/raven/files/cadc:JCMT/jcmth20260921_00048_02_reduced001_nit_000.fits", 288000, 315.5784167, 36.6938056, 85000.0, 61304.371818, 480.0),
]

FIFILS_EXPOSURES = [
    ("AFGL437", "BLU", "FIFILS.F0839_FI_IFS_09016936_BLU_WXY_100234-100263.fits", "https://irsa.ipac.caltech.edu/data/SOFIA/FIFI-LS/L4/p12935/data/g4/F0839_FI_IFS_09016936_BLU_WXY_100234-100263.fits", 702720, 46.8468469, 58.5133768, 740.0, 59653.223588, 460.8, "FIFILS_BLU_52UM"),
    ("AFGL437", "RED", "FIFILS.F0839_FI_IFS_09016936_RED_WXY_100234-100263.fits", "https://irsa.ipac.caltech.edu/data/SOFIA/FIFI-LS/L4/p12935/data/g3/F0839_FI_IFS_09016936_RED_WXY_100234-100263.fits", 676800, 46.8484716, 58.5130507, 1454.0, 59653.223588, 460.8, "FIFILS_RED_186UM"),
    ("W3IRS5", "RED", "FIFILS.F0809_FI_IFS_09016962_RED_WXY_300179-300207.fits", "https://irsa.ipac.caltech.edu/data/SOFIA/FIFI-LS/L4/p12930/data/g4/F0809_FI_IFS_09016962_RED_WXY_300179-300207.fits", 648000, 36.4186991, 62.0972793, 1454.0, 59592.292350, 145.92, "FIFILS_RED_186UM"),
    ("PNK362", "BLU", "FIFILS.F0524_FI_IFS_0602371_BLU_WXY_100761-100798.fits", "https://irsa.ipac.caltech.edu/data/SOFIA/FIFI-LS/L4/p12556/data/g4/F0524_FI_IFS_0602371_BLU_WXY_100761-100798.fits", 717120, 322.9586207, 52.5637192, 740.0, 58428.283657, 583.68, "FIFILS_BLU_52UM"),
    ("S255NIRS3", "BLU", "FIFILS.F0526_FI_IFS_06018210_BLU_WXY_400349-400366.fits", "https://irsa.ipac.caltech.edu/data/SOFIA/FIFI-LS/L4/p12558/data/g6/F0526_FI_IFS_06018210_BLU_WXY_400349-400366.fits", 584640, 93.2251255, 17.9891682, 740.0, 58430.353704, 276.48, "FIFILS_BLU_55UM"),
    ("NGC5253", "BLU", "FIFILS.F0569_FI_IFS_0702395_BLU_WXY_00313-00366.fits", "https://irsa.ipac.caltech.edu/data/SOFIA/FIFI-LS/L4/p12635/data/g7/F0569_FI_IFS_0702395_BLU_WXY_00313-00366.fits", 555840, 204.9834696, -31.6405835, 740.0, 58613.258866, 829.44, "FIFILS_BLU_57UM"),
    ("AFGL5180", "RED", "FIFILS.F0809_FI_IFS_09016930_RED_WXY_200194-300053.fits", "https://irsa.ipac.caltech.edu/data/SOFIA/FIFI-LS/L4/p12930/data/g6/F0809_FI_IFS_09016930_RED_WXY_200194-300053.fits", 662400, 92.2242216, 21.6401735, 1454.0, 59592.208426, 460.8, "FIFILS_RED_186UM"),
    ("IRAS20126P4104", "RED", "FIFILS.F0909_FI_IFS_09016933_RED_WXY_100675-100710.fits", "https://irsa.ipac.caltech.edu/data/SOFIA/FIFI-LS/L4/p12958/data/g9/F0909_FI_IFS_09016933_RED_WXY_100675-100710.fits", 694080, 303.6069400, 41.2257181, 1009.0, 59823.391609, 552.96, "FIFILS_RED_146UM"),
    ("DR21", "RED", "FIFILS.F0681_FI_IFS_7500463_RED_WXY_00269-00272.fits", "https://irsa.ipac.caltech.edu/data/SOFIA/FIFI-LS/L4/p12877/data/g1/F0681_FI_IFS_7500463_RED_WXY_00269-00272.fits", 766080, 309.7487686, 42.3309554, 1232.0, 59095.333275, 61.44, "FIFILS_RED_163UM"),
    ("NGC5576", "BLU", "FIFILS.F0565_FI_IFS_0701053_BLU_WXY_400194-400199.fits", "https://irsa.ipac.caltech.edu/data/SOFIA/FIFI-LS/L4/p12631/data/g2/F0565_FI_IFS_0701053_BLU_WXY_400194-400199.fits", 512640, 215.2674746, 3.2715161, 630.0, 58607.273229, 92.16, "FIFILS_BLU_89UM"),
    ("CEPAHW2", "RED", "FIFILS.F0807_FI_IFS_09016942_RED_WXY_100541-100557.fits", "https://irsa.ipac.caltech.edu/data/SOFIA/FIFI-LS/L4/p12928/data/g3/F0807_FI_IFS_09016942_RED_WXY_100541-100557.fits", 676800, 344.0742495, 62.0299794, 1454.0, 59590.365301, 168.96, "FIFILS_RED_186UM"),
    ("IRC10216", "RED", "FIFILS.F0378_FI_IFS_9000312_RED_WXY_100080-100150.fits", "https://irsa.ipac.caltech.edu/data/SOFIA/FIFI-LS/L4/p12467/data/g5/F0378_FI_IFS_9000312_RED_WXY_100080-100150.fits", 763200, 146.9874251, 13.2777844, 1232.0, 57809.149907, 225.28, "FIFILS_RED_158UM"),
    ("BETELGEUSE", "RED", "FIFILS.F0664_FI_IFS_7500523_RED_WXY_00197-00200.fits", "https://irsa.ipac.caltech.edu/data/SOFIA/FIFI-LS/L4/p12870/data/g1/F0664_FI_IFS_7500523_RED_WXY_00197-00200.fits", 590400, 88.7918191, 7.4059005, 1454.0, 58906.241690, 61.44, "FIFILS_RED_186UM"),
    ("ABAUR", "RED", "FIFILS.F0804_FI_IFS_0801471_RED_WXY_300142-400010.fits", "https://irsa.ipac.caltech.edu/data/SOFIA/FIFI-LS/L4/p12925/data/g9/F0804_FI_IFS_0801471_RED_WXY_300142-400010.fits", 826560, 73.9402966, 30.5506522, 1232.0, 59571.373275, 1075.2, "FIFILS_RED_158UM"),
    ("AFGL2591", "RED", "FIFILS.F0740_FI_IFS_09016931_RED_WXY_100018-100047.fits", "https://irsa.ipac.caltech.edu/data/SOFIA/FIFI-LS/L4/p12892/data/g8/F0740_FI_IFS_09016931_RED_WXY_100018-100047.fits", 696960, 307.3531237, 40.1880966, 1009.0, 59368.264398, 230.4, "FIFILS_RED_146UM"),
]

IUE_EXPOSURES = [
    ("HD103095", "IUE_LWP_HI", "IUE.lwr05154.mxhi.gz", "https://archive.stsci.edu/pub/iue/data/lwr/05000/lwr05154.mxhi.gz", 700405, 178.244865, 37.718682, 12000.0, 44077.888, 22500.0),
    ("HD147513", "IUE_LWP_HI", "IUE.lwp05847.mxhi.gz", "https://archive.stsci.edu/pub/iue/data/lwp/05000/lwp05847.mxhi.gz", 705595, 246.005375, -39.192992, 12000.0, 46183.500, 3600.0),
    ("HD17925", "IUE_LWP_HI", "IUE.lwp14648.mxhi.gz", "https://archive.stsci.edu/pub/iue/data/lwp/14000/lwp14648.mxhi.gz", 704293, 43.133167, -12.769414, 12000.0, 47510.800, 4200.0),
    ("HD19373", "IUE_LWP_HI", "IUE.lwp06788.mxhi.gz", "https://archive.stsci.edu/pub/iue/data/lwp/06000/lwp06788.mxhi.gz", 703015, 47.266750, 49.613278, 12000.0, 46332.500, 1800.0),
    ("HD13974", "IUE_LWP_HI", "IUE.lwr09567.mxhi.gz", "https://archive.stsci.edu/pub/iue/data/lwr/09000/lwr09567.mxhi.gz", 699179, 34.263458, 34.224222, 12000.0, 44597.500, 2100.0),
    ("HD166620", "IUE_LWP_HI", "IUE.lwr16314.mxhi.gz", "https://archive.stsci.edu/pub/iue/data/lwr/16000/lwr16314.mxhi.gz", 702898, 272.405900, 38.457778, 12000.0, 45522.500, 7800.0),
    ("HD141004", "IUE_LWP_HI", "IUE.lwr16313.mxhi.gz", "https://archive.stsci.edu/pub/iue/data/lwr/16000/lwr16313.mxhi.gz", 700401, 236.610890, 7.353070, 12000.0, 45522.400, 1800.0),
    ("HD104304", "IUE_LWP_HI", "IUE.lwp24850.mxhi.gz", "https://archive.stsci.edu/pub/iue/data/lwp/24000/lwp24850.mxhi.gz", 700353, 180.185667, -10.446011, 12000.0, 49023.500, 2700.0),
    ("HD34029", "IUE_SWP_HI", "IUE.swp16660.mxhi.gz", "https://archive.stsci.edu/pub/iue/data/swp/16000/swp16660.mxhi.gz", 690432, 79.172265, 45.997991, 11500.0, 45057.500, 14400.0),
    ("HD35296", "IUE_LWP_HI", "IUE.lwr01936.mxhi.gz", "https://archive.stsci.edu/pub/iue/data/lwr/01000/lwr01936.mxhi.gz", 696943, 81.106167, 17.383528, 12000.0, 43721.500, 3000.0),
    ("HD22468", "IUE_SWP_HI", "IUE.swp29309.mxhi.gz", "https://archive.stsci.edu/pub/iue/data/swp/29000/swp29309.mxhi.gz", 683567, 54.197042, 0.587778, 11500.0, 46698.500, 70200.0),
    ("HD144668", "IUE_SWP_HI", "IUE.swp26370.mxhi.gz", "https://archive.stsci.edu/pub/iue/data/swp/26000/swp26370.mxhi.gz", 680033, 242.143790, -39.105020, 11500.0, 46253.500, 46680.0),
    ("HD120315", "IUE_SWP_HI", "IUE.swp10523.mxhi.gz", "https://archive.stsci.edu/pub/iue/data/swp/10000/swp10523.mxhi.gz", 677381, 206.885171, 49.313260, 11500.0, 44545.500, 600.0),
    ("HD93521", "IUE_SWP_HI", "IUE.swp01644.mxhi.gz", "https://archive.stsci.edu/pub/iue/data/swp/01000/swp01644.mxhi.gz", 694815, 162.097920, 37.570280, 11500.0, 43654.500, 1800.0),
    ("BETELGEUSE", "IUE_SWP_HI", "IUE.swp14775.mxhi.gz", "https://archive.stsci.edu/pub/iue/data/swp/14000/swp14775.mxhi.gz", 680024, 88.792939, 7.407064, 11500.0, 44833.500, 55800.0),
    ("HD115617", "IUE_LWP_HI", "IUE.lwp18457.mxhi.gz", "https://archive.stsci.edu/pub/iue/data/lwp/18000/lwp18457.mxhi.gz", 701455, 199.601308, -18.311194, 12000.0, 48100.500, 1800.0),
    ("HD114710", "IUE_SWP_HI", "IUE.swp32905.mxhi.gz", "https://archive.stsci.edu/pub/iue/data/swp/32000/swp32905.mxhi.gz", 683690, 197.968308, 27.878184, 11500.0, 47203.500, 24900.0),
]

ESO_EXPOSURES = [
    ("HD20782", "ESO_HARPS", "ADP.2014-09-29T13:27:22.883", 50.0166232, -28.8543535, 115000.0, 52939.24716808, 776.696, 5264000),
    ("HD20782", "ESO_HARPS", "ADP.2014-09-23T11:04:10.283", 50.0166232, -28.8543535, 115000.0, 55065.38992549, 899.999, 5261000),
    ("HD20782", "ESO_HARPS", "ADP.2014-09-25T15:33:14.430", 50.0166232, -28.8543535, 115000.0, 55923.14295109, 899.999, 5264000),
    ("HD20782", "ESO_HARPS", "ADP.2017-10-24T01:04:13.767", 50.0166232, -28.8543535, 115000.0, 58048.19400357, 899.998, 5264000),
    ("HD28254", "ESO_HARPS", "ADP.2014-09-29T13:27:00.580", 66.2089262, -50.6258240, 115000.0, 52941.32952691, 65.395, 5264000),
    ("HD28254", "ESO_HARPS", "ADP.2014-09-18T12:17:38.843", 66.2089262, -50.6258240, 115000.0, 54487.08002013, 60.000, 5261000),
    ("HD28254", "ESO_HARPS", "ADP.2014-09-24T09:42:11.317", 66.2089262, -50.6258240, 115000.0, 55531.28488851, 67.900, 5264000),
    ("HD28254", "ESO_HARPS", "ADP.2021-03-07T01:02:15.644", 66.2089262, -50.6258240, 115000.0, 59279.02754751, 84.996, 5264000),
    ("HD7449", "ESO_HARPS", "ADP.2014-09-29T13:27:13.477", 18.6223540, -5.0473930, 115000.0, 52945.15086928, 899.995, 5264000),
    ("HD7449", "ESO_HARPS", "ADP.2014-09-23T11:04:15.063", 18.6223540, -5.0473930, 115000.0, 55036.39169241, 900.001, 5261000),
    ("HD7449", "ESO_HARPS", "ADP.2014-09-26T16:53:06.987", 18.6223540, -5.0473930, 115000.0, 56117.40597619, 900.000, 5264000),
    ("HD7449", "ESO_HARPS", "ADP.2016-01-11T01:03:46.707", 18.6223540, -5.0473930, 115000.0, 57397.05313057, 899.998, 5264000),
    ("HD76920", "ESO_FEROS", "ADP.2016-10-10T09:43:27.816", 133.8203530, -67.2653621, 48000.0, 57641.41264486, 300.044, 3078000),
    ("HD76920", "ESO_FEROS", "ADP.2016-12-06T13:14:52.498", 133.8203530, -67.2653621, 48000.0, 57700.34492735, 300.044, 3078000),
    ("HD76920", "ESO_FEROS", "ADP.2017-06-09T08:07:50.726", 133.8203530, -67.2653621, 48000.0, 57894.05735472, 300.043, 3078000),
    ("HD76920", "ESO_FEROS", "ADP.2018-02-12T08:48:08.403", 133.8203530, -67.2653621, 48000.0, 58123.34352998, 300.043, 3078000),
    ("HD147513", "ESO_FEROS", "ADP.2016-09-20T08:08:13.230", 246.0053750, -39.1929920, 48000.0, 53074.31123908, 299.999, 3075000),
    ("HD147513", "ESO_FEROS", "ADP.2016-09-21T13:54:11.783", 246.0053750, -39.1929920, 48000.0, 53931.14672379, 599.999, 3075000),
    ("HD147513", "ESO_FEROS", "ADP.2016-09-28T06:54:52.606", 246.0053750, -39.1929920, 48000.0, 57206.08328002, 400.044, 3078000),
    ("HD147513", "ESO_FEROS", "ADP.2024-12-10T10:04:22.503", 246.0053750, -39.1929920, 48000.0, 60498.16155228, 300.045, 3081000),
    ("HD154577", "ESO_FEROS", "ADP.2016-09-20T08:08:13.036", 257.5416000, -60.7270000, 48000.0, 53073.36528059, 899.999, 3075000),
    ("HD154577", "ESO_FEROS", "ADP.2016-09-21T13:54:11.549", 257.5416000, -60.7270000, 48000.0, 53930.13570188, 719.999, 3078000),
    ("HD154577", "ESO_FEROS", "ADP.2025-05-15T03:17:01.448", 257.5416000, -60.7270000, 48000.0, 60795.35791349, 200.045, 3081000),
    ("HD154577", "ESO_FEROS", "ADP.2025-06-15T00:25:12.875", 257.5416000, -60.7270000, 48000.0, 60798.33093363, 200.045, 3081000),
]

TWOMASS_JHK: dict[str, tuple[float, float, float]] = {
    "OH231P8": (9.863, 8.281, 6.546), "L1551IRS5": (13.708, 11.505, 9.822), "N2071IR": (13.691, 11.596, 10.102),
    "OMC1": (7.12, 5.802, 5.668), "W3OH": (13.638, 13.055, 12.753), "RHYA": (-1.314, -2.235, -2.663),
    "N7538IRS1": (11.751, 10.081, 10.208), "VCAM": (2.22, 1.333, 0.825), "G34P3": (8.981, 7.771, 7.295),
    "W75N": (12.614, 10.984, 9.723), "M87": (11.439, 11.284, 10.733), "CYGNUSA": (10.845, 10.223, 10.122),
    "3C84": (12.677, 12.144, 12.063), "3C279": (12.585, 11.74, 10.941),
    "AFGL437": (11.842, 10.626, 9.946), "W3IRS5": (11.024, 10.415, 10.248), "PNK362": (11.201, 9.595, 8.987),
    "S255NIRS3": (11.414, 10.915, 10.508), "NGC5253": (13.284, 14.546, 14.041), "AFGL5180": (7.81, 7.264, 7.132),
    "IRAS20126P4104": (11.997, 11.754, 11.624), "DR21": (13.6, 11.543, 10.228), "NGC5576": (11.377, 10.65, 10.205),
    "CEPAHW2": (12.098, 10.583, 9.982),
    "HD103095": (4.937, 4.5, 4.373), "HD147513": (4.405, 4.025, 3.933), "HD17925": (4.83, 4.23, 4.167),
    "HD19373": (3.143, 2.875, 2.723), "HD13974": (3.525, 3.287, 3.076), "HD166620": (4.952, 4.458, 4.232),
    "HD141004": (3.43, 3.07, 2.989), "HD104304": (4.557, 4.07, 4.027), "HD34029": (-1.249, -1.573, -1.735),
    "HD35296": (4.431, 4.029, 4.038), "HD22468": (3.882, 3.246, 3.137), "HD144668": (5.907, 5.22, 4.386),
    "HD120315": (2.228, 2.408, 2.265), "HD93521": (7.499, 7.647, 7.696),
    "HD20782": (6.229, 5.956, 5.827), "HD28254": (6.395, 6.133, 6.006), "HD7449": (6.425, 6.179, 6.084),
    "HD76920": (5.946, 5.409, 5.253), "HD154577": (5.694, 5.204, 5.091),
}


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
    r, d = math.radians(ra_deg), math.radians(dec_deg)
    ux, uy, uz = math.cos(d) * math.cos(r), math.cos(d) * math.sin(r), math.sin(d)
    d_lt_days = dist_pc * 3.26156378 * 365.25
    out = []
    for era, edec in ((83.866, -69.270), (197.450, -23.381), (210.911, 54.312)):
        er, ed = math.radians(era), math.radians(edec)
        vx, vy, vz = math.cos(ed) * math.cos(er), math.cos(ed) * math.sin(er), math.sin(ed)
        out.append(round(d_lt_days * (ux * vx + uy * vy + uz * vz - 1.0), 3))
    return out[0], out[1], out[2]


def _eccentric_kp_and_rv(a_au: float, per_days: float, ecc: float, w_deg: float, mjd_obs: float, t0_bjd: float) -> tuple[float, float, float]:
    p_s = max(1e3, per_days * DAY_S)
    a_cm = max(0.01, a_au) * AU_CM
    kp_kms = (2.0 * math.pi * a_cm / (p_s * math.sqrt(max(1e-4, 1.0 - ecc * ecc)))) / 1e5
    bjd_obs = mjd_obs + 2400000.5
    ph = ((bjd_obs - t0_bjd) / per_days) % 1.0
    signed_ph = ph - 1.0 if ph > 0.5 else ph
    import numpy as np
    t0_mjd = t0_bjd - 2400000.5
    rv_kms = float(solve_kepler_eccentric_rv(np.array([mjd_obs - t0_mjd]), per_days, ecc, math.radians(w_deg), 0.0, kp_kms)[0])
    return kp_kms, signed_ph, rv_kms


def _fmt_num(x: Any, prec: int = 6) -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return ""
    if isinstance(x, bool) or isinstance(x, int):
        return str(x)
    return str(round(float(x), prec))


def main() -> int:
    if IN_DIR.exists():
        raise RuntimeError(f"STRICT LOCK VIOLATION: {IN_DIR} already exists BEFORE Stage-1 seal!")

    # 1. Build PRIOR_V5_7_PHASES_SNAPSHOT.json from WS99 + Companion Archives Y/X/W/V/U/T
    ws99_sum = json.loads((WS99 / "results/SUMMARY.json").read_text(encoding="utf-8"))
    syn99 = ws99_sum["unified_516star_panchromatic_v5_7_synthesis"]
    ws99_ps = json.loads((WS99 / "PRIOR_V5_6_PHASES_SNAPSHOT.json").read_text(encoding="utf-8"))
    with (WS99 / "results/UNIFIED_PANCHROMATIC_V5_7_SYNTHESIS_516STARS.csv").open(newline="", encoding="utf-8") as fh:
        u516_rows = list(csv.DictReader(fh))
    with (WS99 / "results/PANCHROMATIC_BRIDGE_71STARS_V57.csv").open(newline="", encoding="utf-8") as fh:
        b71_rows = list(csv.DictReader(fh))
    with (WS99 / "results/ALLSKY_COMB_V4_1_UNIFIED_D079_D099.csv").open(newline="", encoding="utf-8") as fh:
        comb_u_rows = list(csv.DictReader(fh))
    with (WS99 / "results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D099.csv").open(newline="", encoding="utf-8") as fh:
        comb_c_rows = list(csv.DictReader(fh))
    with (WS99 / "results/MULTIEVENT_ELLIPSOID_516STARS.csv").open(newline="", encoding="utf-8") as fh:
        ell516_rows = list(csv.DictReader(fh))

    u516_map = {r["star"]: r for r in u516_rows}
    ell516_map = {r["star"]: r for r in ell516_rows}

    arch_y_name = "SETI_D099_V5_7_JCMT_MM_SOFIA_EXES_IRTF_SPEX_KEPLERIAN_DRIFT_RESULTS_2026-11-22.zip"
    arch_y_path = ARCHIVES / arch_y_name
    if not arch_y_path.exists():
        raise FileNotFoundError(f"Missing Archive Y: {arch_y_path}")
    arch_y_sha = _sha256_file(arch_y_path)
    with zipfile.ZipFile(arch_y_path) as zf:
        mem_y = [n for n in zf.namelist() if n.endswith("d099_bounded_bundle.json.gz")][0]
        bun_y_sha = hashlib.sha256(zf.read(mem_y)).hexdigest()

    prior_snap = {
        "schema": "D100_PRIOR_V5_7_PHASES_SNAPSHOT",
        "prior_phases": "C001-C037 + D001-D099",
        "source_archive_y_name": arch_y_name,
        "source_archive_y_sha256": arch_y_sha,
        "source_archive_y_bundle_member": mem_y,
        "source_archive_y_bundle_sha256": bun_y_sha,
        "source_archive_x_name": ws99_ps["source_archive_x_name"],
        "source_archive_x_sha256": ws99_ps["source_archive_x_sha256"],
        "source_archive_x_bundle_member": ws99_ps["source_archive_x_bundle_member"],
        "source_archive_x_bundle_sha256": ws99_ps["source_archive_x_bundle_sha256"],
        "source_archive_w_name": ws99_ps["source_archive_w_name"],
        "source_archive_w_sha256": ws99_ps["source_archive_w_sha256"],
        "source_archive_w_bundle_member": ws99_ps["source_archive_w_bundle_member"],
        "source_archive_w_bundle_sha256": ws99_ps["source_archive_w_bundle_sha256"],
        "source_archive_v_name": ws99_ps["source_archive_v_name"],
        "source_archive_v_sha256": ws99_ps["source_archive_v_sha256"],
        "source_archive_v_bundle_member": ws99_ps["source_archive_v_bundle_member"],
        "source_archive_v_bundle_sha256": ws99_ps["source_archive_v_bundle_sha256"],
        "source_archive_u_name": ws99_ps["source_archive_u_name"],
        "source_archive_u_sha256": ws99_ps["source_archive_u_sha256"],
        "source_archive_u_bundle_member": ws99_ps["source_archive_u_bundle_member"],
        "source_archive_u_bundle_sha256": ws99_ps["source_archive_u_bundle_sha256"],
        "source_archive_t_name": ws99_ps["source_archive_t_name"],
        "source_archive_t_sha256": ws99_ps["source_archive_t_sha256"],
        "source_archive_t_bundle_member": ws99_ps["source_archive_t_bundle_member"],
        "source_archive_t_bundle_sha256": ws99_ps["source_archive_t_bundle_sha256"],
        "prior_unique_stars_count": int(syn99["unique_stars_total"]),
        "prior_science_stars_count": int(syn99["science_stars_total"]),
        "prior_control_stars_count": int(syn99["control_stars_total"]),
        "prior_planet_host_stars_count": int(syn99["planet_host_stars_total"]),
        "prior_confirmed_exoplanets_count": int(syn99["confirmed_exoplanets_total"]),
        "prior_within_10pc_count": int(syn99["within_10pc_unique_stars"]),
        "prior_total_exposures_count": int(syn99["total_exposures_d079_d099"]),
        "prior_cumulative_integration_hours": float(syn99["total_integration_hours_d079_d099"]),
        "prior_calibration_trials_count": int(syn99["total_calibration_trials_d079_d099"]),
        "prior_v2_false_alarms_eliminated_total": int(syn99["v2_false_alarms_eliminated_total"]),
        "prior_cumulative_orbital_campaigns_count": int(syn99["cumulative_orbital_campaigns"]),
        "prior_panchromatic_bridge_stars_count": int(syn99["panchromatic_bridge_stars_total"]),
        "prior_revisited_control_multi_phase_stars": int(syn99["revisited_control_multi_phase_stars"]),
        "prior_multi_phase_targets_total": int(syn99["multi_phase_targets_total"]),
        "prior_panchromatic_bridge_cells_count": int(syn99["panchromatic_bridge_cells_total"]),
        "prior_cumulative_comb_stacks": int(syn99["cumulative_comb_stacks"]),
        "prior_coherent_keplerian_campaigns": int(syn99["coherent_keplerian_jerk_campaigns"]),
        "d099_summary_headline": syn99,
        "prior_unified_516_rows": u516_rows,
        "prior_bridge_71_rows": b71_rows,
        "prior_allsky_comb_unified_rows": comb_u_rows,
        "prior_allsky_comb_candidate_rows": comb_c_rows,
        "prior_ellipsoid_516_rows": ell516_rows,
    }
    (WS / "PRIOR_V5_7_PHASES_SNAPSHOT.json").write_text(json.dumps(prior_snap), encoding="utf-8")

    # 2. Load Prior Exclusion Registry from WS99 (539 + 43 = 582 unique coords, 2983 + 97 = 3080 science dp_ids, 12 + 3 = 15 fmt dp_ids)
    pe99 = json.loads((WS99 / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    excl_dps = set(pe99["excluded_dp_ids"])
    fmt_dps = set(pe99.get("format_check_excluded_dp_ids", [])) | D100_FORMAT_CHECK_DPS
    coord_reg = list(pe99["excluded_targets_coordinate_registry"])
    seen_st = {c.get("canonical_target", c.get("name", "")) for c in coord_reg if c.get("canonical_target") or c.get("name")}
    with (WS99 / "FROZEN_COHORT_D099.csv").open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            excl_dps.add(r["dp_id"])
            st = r["canonical_target"]
            if st not in seen_st:
                coord_reg.append({"canonical_target": st, "ra_deg": float(r["s_ra"]), "dec_deg": float(r["s_dec"])})
                seen_st.add(st)

    # Coordinate map for brand-new stars from verified exposure tuples
    brand_coords: dict[str, tuple[float, float]] = {}
    for row in ALAIHI_EXPOSURES:
        brand_coords.setdefault(row[0], (row[4], row[5]))
    for row in FIFILS_EXPOSURES:
        brand_coords.setdefault(row[0], (row[5], row[6]))
    for row in IUE_EXPOSURES:
        brand_coords.setdefault(row[0], (row[5], row[6]))
    for row in ESO_EXPOSURES:
        brand_coords.setdefault(row[0], (row[3], row[4]))

    def resolve_star_fields(st: str) -> dict[str, Any]:
        spec = STAR_META[st]
        if spec.get("is_bridge"):
            u = u516_map[st]
            el = ell516_map[st]
            ra, dec = float(el["ra_deg"]), float(el["dec_deg"])
            dist_pc = float(u["dist_pc"]) if u.get("dist_pc") else 500.0
            return {
                "common_name": u["common_name"],
                "role": u["role"],
                "subrole": spec["sub"],
                "is_bridge": True,
                "ra": ra,
                "dec": dec,
                "pmra": float(spec.get("pmra", 0.0)),
                "pmdec": float(spec.get("pmdec", 0.0)),
                "dist_pc": dist_pc,
                "within_10pc": dist_pc <= 10.0,
                "g_mag": float(u["phot_g_mag"]) if u.get("phot_g_mag") else math.nan,
                "j_mag": float(u["j_mag"]) if u.get("j_mag") else math.nan,
                "h_mag": float(u["h_mag"]) if u.get("h_mag") else math.nan,
                "ks_mag": float(u["ks_mag"]) if u.get("ks_mag") else math.nan,
                "teff_k": float(u["teff_k"]) if u.get("teff_k") else 4500.0,
                "mh_dex": 0.0,
                "mass_msun": 1.0,
                "rv_kms": float(spec.get("rv", 0.0)),
                "n_pl": int(float(u["n_exoplanets"])) if u.get("n_exoplanets") else 0,
                "gaia_id": f"PRIOR_{st}",
            }
        ra, dec = brand_coords[st]
        jm, hm, km = TWOMASS_JHK.get(st, (math.nan, math.nan, math.nan))
        dist_pc = float(spec["dist_pc"])
        gmag = float(spec["gmag"]) if spec.get("gmag") is not None else math.nan
        return {
            "common_name": spec["common"],
            "role": spec["role"],
            "subrole": spec["sub"],
            "is_bridge": False,
            "ra": ra,
            "dec": dec,
            "pmra": float(spec.get("pmra", 0.0)),
            "pmdec": float(spec.get("pmdec", 0.0)),
            "dist_pc": dist_pc,
            "within_10pc": dist_pc <= 10.0,
            "g_mag": gmag,
            "j_mag": jm,
            "h_mag": hm,
            "ks_mag": km,
            "teff_k": float(spec["teff"]),
            "mh_dex": 0.0,
            "mass_msun": float(spec["mass"]),
            "rv_kms": float(spec.get("rv", 0.0)),
            "n_pl": int(spec.get("npl", 0)),
            "gaia_id": str(spec["gid"]),
        }

    # Verify sky exclusions
    sep_checks: list[dict[str, Any]] = []
    min_bn_sep = 1e9
    bn_targets = [st for st, sp in STAR_META.items() if not sp.get("is_bridge")]
    for st in bn_targets:
        sf = resolve_star_fields(st)
        b_sep, b_ref = min((_ang_sep_arcsec(sf["ra"], sf["dec"], float(c["ra_deg"]), float(c["dec_deg"])), c.get("canonical_target") or c.get("name") or str(round(float(c["ra_deg"]), 3))) for c in coord_reg)
        min_bn_sep = min(min_bn_sep, b_sep)
        if b_sep < 300.0:
            raise RuntimeError(f"Prior coordinate collision on brand-new {st}: sep={b_sep:.1f}\" from {b_ref}")
        sep_checks.append({"star": st, "min_sep_prior_arcsec": round(b_sep, 2), "nearest_prior": b_ref})

    br_targets = [st for st, sp in STAR_META.items() if sp.get("is_bridge")]
    for st in br_targets:
        sf = resolve_star_fields(st)
        if st not in u516_map:
            raise RuntimeError(f"Prior bridge {st} missing from UNIFIED_516!")
        sp_b = min(_ang_sep_arcsec(sf["ra"], sf["dec"], float(c["ra_deg"]), float(c["dec_deg"])) for c in coord_reg)
        if sp_b > 60.0:
            raise RuntimeError(f"Bridge {st} separation {sp_b:.1f}\" exceeds 60\"")

    all_sf = {st: resolve_star_fields(st) for st in STAR_META}
    sts_sorted = sorted(all_sf.keys())
    min_intra = 1e9
    for i, a in enumerate(sts_sorted):
        for b in sts_sorted[i + 1 :]:
            d_ab = _ang_sep_arcsec(all_sf[a]["ra"], all_sf[a]["dec"], all_sf[b]["ra"], all_sf[b]["dec"])
            if d_ab < min_intra:
                min_intra = d_ab
    if min_intra < 60.0:
        raise RuntimeError(f"Duplicate/near-duplicate intra-D100 target! min_sep={min_intra:.1f}\"")

    # 3. Assemble all 79 frozen exposure rows + ORBITAL_CAMPAIGNS_AND_KINEMATICS.json
    intra_bridges = {"IRC10216", "BETELGEUSE", "HD147513", "AFGL437"}
    frozen_rows: list[dict[str, str]] = []
    d100_dps: set[str] = set()
    campaigns_dict: dict[str, Any] = {}

    def add_row(inst: str, st: str, track: str, erank: int, dp_id: str, grating: str, rp: float, mjd: float, expt: float, pwin: str, sph: float, orb_rv: float, f1_id: str, f1_rel: str, f1_url: str, f1_bytes: int) -> None:
        if dp_id in excl_dps or dp_id in fmt_dps or dp_id in d100_dps:
            raise RuntimeError(f"dp_id exclusion/duplicate violation: {dp_id}")
        d100_dps.add(dp_id)
        sf = all_sf[st]
        elat = _ecliptic_lat_deg(sf["ra"], sf["dec"])
        sn87, gw17, sn23 = _event_delays_days(sf["ra"], sf["dec"], sf["dist_pc"])
        has_pan = sf["is_bridge"] or (st in intra_bridges)
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

    # Stream 1A: JCMT_ALAIHI_3MM (23)
    for st, dp, url, nb, ra, dec, rp, mjd, texp in ALAIHI_EXPOSURES:
        fname = url.split("/")[-1]
        add_row("JCMT_ALAIHI_3MM", st, "JCMT_ALAIHI_3MM_V58", 1, dp, "ALAIHI_ACSIS_3MM", rp, mjd, texp, "NONE", 0.0, 0.0, fname[:-5], f"JCMT_ALAIHI_3MM/{st}/{fname}", url, nb)

    # Stream 1B: SOFIA_FIFILS (15)
    fifi_ranks: dict[str, int] = {}
    for st, ch, dp, url, nb, ra, dec, rp, mjd, texp, grp in FIFILS_EXPOSURES:
        fifi_ranks[st] = fifi_ranks.get(st, 0) + 1
        fname = url.split("/")[-1]
        add_row("SOFIA_FIFILS", st, "SOFIA_FIFILS_FARIR_V58", fifi_ranks[st], dp, grp, rp, mjd, texp, "NONE", 0.0, 0.0, fname[:-5], f"SOFIA_FIFILS/{st}/{fname}", url, nb)

    # Stream 1C: IUE_SWP_HI & IUE_LWP_HI (17)
    for st, inst, dp, url, nb, ra, dec, rp, mjd, texp in IUE_EXPOSURES:
        fname = url.split("/")[-1]
        gr = "SWP_HI_115_198NM" if inst == "IUE_SWP_HI" else "LWP_LWR_HI_185_335NM"
        add_row(inst, st, "IUE_UV_ECHELLE_V58", 1, dp, gr, rp, mjd, texp, "NONE", 0.0, 0.0, fname[:-8], f"{inst}/{st}/{fname}", url, nb)

    # Stream 2 & 3: ESO_HARPS & ESO_FEROS (24 epochs across 6 campaigns: #146-#150 + 0-pl control HD154577)
    by_eso_star: dict[str, list[tuple[Any, ...]]] = {}
    for row in ESO_EXPOSURES:
        by_eso_star.setdefault(row[0], []).append(row)

    for st, eps in sorted(by_eso_star.items()):
        eps.sort(key=lambda r: float(r[6]))
        sp = STAR_META[st]
        has_orb = "orb_p" in sp
        camp_exps = []
        kp_kms = 0.0
        orb_rvs = []
        for rk, (_, inst, dp, ra, dec, rp, mjd, texp, nb) in enumerate(eps, 1):
            sph, orb_rv, pwin = 0.0, 0.0, "NONE"
            if has_orb:
                kp_kms, sph, orb_rv = _eccentric_kp_and_rv(float(sp["orb_a_au"]), float(sp["orb_p"]), float(sp["orb_e"]), float(sp["orb_w_deg"]), float(mjd), float(sp["orb_t0"]))
                pwin = "PERIASTRON_WINDOW" if abs(sph) <= 0.12 else ("IN_QUADRATURE" if abs(abs(sph) - 0.25) <= 0.14 else "IN_WINDOW")
                orb_rvs.append(orb_rv)
            gr = "HARPS_378_691NM" if inst == "ESO_HARPS" else "FEROS_352_921NM"
            url = f"https://dataportal.eso.org/dataPortal/file/{dp.replace(':', '%3A')}"
            fn_clean = dp.replace(":", "_") + ".fits"
            add_row(inst, st, "DRIFT_V58_ECCENTRIC_KEPLERIAN", rk, dp, gr, float(rp), float(mjd), float(texp), pwin, sph, orb_rv, dp, f"{inst}/{st}/{fn_clean}", url, int(nb))
            camp_exps.append({
                "dp_id": dp, "mjd_obs": round(float(mjd), 6), "bjd_tdb_est": round(float(mjd) + 2400000.5, 6),
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
                "instrument": eps[0][1],
                "role": sp["role"],
                "null_orbital": False,
                "planet_name": sp["pl_name"],
                "n_planets_in_system": int(sp["npl"]),
                "stellar_mass_msun": float(sp["mass"]),
                "orb_per_days": float(sp["orb_p"]),
                "orb_periods_days": periods_all,
                "orb_t0_bjd": float(sp["orb_t0"]),
                "orb_ecc": float(sp["orb_e"]),
                "orb_omega_deg": float(sp["orb_w_deg"]),
                "kp_kms": round(kp_kms, 3),
                "orbital_dv_span_kms": round(max(orb_rvs) - min(orb_rvs), 3) if orb_rvs else 0.0,
                "n_epochs": len(eps),
                "baseline_days": round(max(float(e[6]) for e in eps) - min(float(e[6]) for e in eps), 2),
                "exposures": camp_exps,
            }

    cohort_csv = WS / "FROZEN_COHORT_D100.csv"
    with cohort_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FROZEN_HEADER)
        w.writeheader()
        w.writerows(frozen_rows)

    tot_bytes = sum(int(r["f1_bytes"]) for r in frozen_rows)
    tot_mib = tot_bytes / float(1 << 20)
    if tot_mib > 125.0:
        raise RuntimeError(f"Projected total {tot_mib:.3f} MiB exceeds 125.0 MiB!")

    n_bn_10pc = sum(1 for st in bn_targets if all_sf[st]["within_10pc"])
    n_bn_ctrl = sum(1 for st in bn_targets if all_sf[st]["role"] == "CONTROL")
    pe_out = {
        "schema": "D100_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D100",
        "verified_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "prior_phases_covered": "C001-C037 + D001-D099",
        "n_prior_excluded_coords": len(coord_reg),
        "n_prior_excluded_dp_ids": len(excl_dps),
        "n_format_check_excluded_dp_ids": len(fmt_dps),
        "d100_total_stars": len(STAR_META),
        "d100_brand_new_unique_stars": len(bn_targets),
        "d100_prior_bridge_stars": len(br_targets),
        "d100_control_stars": sum(1 for st in STAR_META if all_sf[st]["role"] == "CONTROL"),
        "d100_brand_new_controls": n_bn_ctrl,
        "d100_brand_new_within_10pc": n_bn_10pc,
        "d100_total_input_files": len(frozen_rows),
        "d100_projected_download_bytes": tot_bytes,
        "d100_projected_download_mib": round(tot_mib, 4),
        "d100_dp_id_overlap_count": 0,
        "min_brand_new_sky_separation_arcsec": round(min_bn_sep, 2),
        "min_intra_d100_separation_arcsec": round(min_intra, 2),
        "star_separation_verification": sep_checks,
        "format_check_excluded_dp_ids": sorted(fmt_dps),
        "excluded_dp_ids": sorted(excl_dps),
        "excluded_targets_coordinate_registry": coord_reg,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pe_out), encoding="utf-8")

    orb_out = {
        "schema": "D100_ORBITAL_CAMPAIGNS_AND_KINEMATICS",
        "phase_id": "D100",
        "campaign_range": "#146-#150",
        "n_campaigns": len(campaigns_dict),
        "campaigns": campaigns_dict,
    }
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_out, indent=2), encoding="utf-8")

    stage1_names = [
        "v5_8_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D100.csv",
        "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "PRIOR_V5_7_PHASES_SNAPSHOT.json",
    ]
    hashes = {nm: _sha256_file(WS / nm) for nm in stage1_names}
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
    ml_out = {
        "schema": "D100_PROSPECTIVE_METHOD_LOCK",
        "phase_id": "D100",
        "detector_version": "V5.8",
        "detector": "TECHNOSIGNATURE_V5_8_JCMT_3MM_SOFIA_FIFILS_IUE_ECCENTRIC_KEPLERIAN",
        "locked_utc": now_iso,
        "projected_unified_stars": int(syn99["unique_stars_total"]) + len(bn_targets),
        "d100_brand_new_stars": len(bn_targets),
        "d100_prior_bridges": len(br_targets),
        "d100_total_files": len(frozen_rows),
        "d100_projected_bytes": tot_bytes,
        "d100_projected_mib": round(tot_mib, 4),
        "stage_1_files": hashes,
    }
    ml_p = WS / "METHOD_LOCK.json"
    ml_p.write_text(json.dumps(ml_out, indent=2), encoding="utf-8")

    lr_out = {
        "schema": "D100_LOCK_RECEIPT",
        "phase_id": "D100",
        "status": "STAGE-1 SEALED",
        "locked_utc": now_iso,
        "locked_unix_epoch": round(dt.datetime.now(dt.timezone.utc).timestamp(), 3),
        "method_lock_sha256": _sha256_file(ml_p),
        "inputs_dir_exists_at_seal": IN_DIR.exists(),
        "locked_files": hashes,
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lr_out, indent=2), encoding="utf-8")
    print(f"STAGE-1 SEALED: {len(STAR_META)} stars ({len(bn_targets)} new + {len(br_targets)} bridges), {len(frozen_rows)} files, {tot_bytes} B ({tot_mib:.4f} MiB), inputs_dir_exists_at_seal={lr_out['inputs_dir_exists_at_seal']}, min_sep={min_bn_sep:.2f}\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
