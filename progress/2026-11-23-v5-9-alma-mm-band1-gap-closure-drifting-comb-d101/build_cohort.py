#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D101 Stage-1 Cohort Lock Builder (`V5.9`)
Builds and cryptographically seals:
  - PRIOR_V5_8_PHASES_SNAPSHOT.json (Archives Z-T + 560-star D100 baseline)
  - PRIOR_EXCLUSION_VERIFICATION.json (632 prior coords, 3,159 dp_ids, 16 format-excluded dp_ids)
  - ORBITAL_CAMPAIGNS_AND_KINEMATICS.json (Orbits #151-#156)
  - FROZEN_COHORT_D101.csv (102 files: 63 ALMA SODA cubes B1/B3/B4/B5 + 39 ESO ESPRESSO/HARPS spectra)
  - METHOD_LOCK.json & LOCK_RECEIPT.json (strictly before inputs_d101_v5_9 exists)
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import urllib.parse
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_v5_9_20261123_d101_alma_mm_band1_gap_closure_drifting_comb"
WS_D100 = ROOT / "analysis_workspace/work_v5_8_20261122_d100_jcmt_3mm_sofia_fifils_iue_eccentric_keplerian"

STAR_META: dict[str, dict[str, Any]] = {'AS209': {'common_name': 'AS 209 (T Tauri Ringed Disk)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 4326521359869384576', 'ra_deg': 252.3137308, 'dec_deg': -14.3691727, 'pmra': -7.3658, 'pmdec': -23.658, 'dist_pc': 121.24547, 'within_10pc': False, 'phot_g_mag': 10.985, 'phot_bp_mag': 11.9684, 'phot_rp_mag': 9.9851, 'teff_k': 5520.6, 'mh_dex': -0.5976, 'stellar_mass_msun': 0.83, 'prior_rv_kms': -7.0, 'n_exoplanets': 0}, 'ELIAS224': {'common_name': 'Elias 2-24 (1-pl Protoplanetary Disk Host)', 'role': 'SCIENCE', 'subrole': 'PLANET_HOST_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 6049168008547148416', 'ra_deg': 246.6003304, 'dec_deg': -24.2705123, 'pmra': -7.9711, 'pmdec': -24.7251, 'dist_pc': 139.25854, 'within_10pc': False, 'phot_g_mag': 15.8834, 'phot_bp_mag': 18.5173, 'phot_rp_mag': 14.4111, 'teff_k': 6062.4, 'mh_dex': 0.0009, 'stellar_mass_msun': 0.78, 'prior_rv_kms': -3.5, 'n_exoplanets': 1}, 'RXJ1852': {'common_name': 'RX J1852.3-3700 (CrA Transition Disk)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 6731011315385156224', 'ra_deg': 283.0721053, 'dec_deg': -37.003445, 'pmra': 2.9404, 'pmdec': -28.324, 'dist_pc': 147.08928, 'within_10pc': False, 'phot_g_mag': 11.7156, 'phot_bp_mag': 12.3829, 'phot_rp_mag': 10.8888, 'teff_k': 4725.7, 'mh_dex': -0.7753, 'stellar_mass_msun': 1.05, 'prior_rv_kms': 0.0, 'n_exoplanets': 0}, 'HD34282': {'common_name': 'HD 34282 (Herbig Ae Disk)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 3014390365402220544', 'ra_deg': 79.0019868, 'dec_deg': -9.8098362, 'pmra': 0.279, 'pmdec': -1.0378, 'dist_pc': 308.61076, 'within_10pc': False, 'phot_g_mag': 9.8597, 'phot_bp_mag': 9.9381, 'phot_rp_mag': 9.6804, 'teff_k': 8700.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.59, 'prior_rv_kms': 10.9523, 'n_exoplanets': 0}, 'SZ90': {'common_name': 'Sz 90 (Lupus T Tauri Disk)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 5997077167735183872', 'ra_deg': 241.7919024, 'dec_deg': -39.1843515, 'pmra': -9.3534, 'pmdec': -25.295, 'dist_pc': 160.36593, 'within_10pc': False, 'phot_g_mag': 13.6043, 'phot_bp_mag': 14.841, 'phot_rp_mag': 12.4788, 'teff_k': 4050.0, 'mh_dex': 0.0, 'stellar_mass_msun': 0.78, 'prior_rv_kms': 4.0, 'n_exoplanets': 0}, 'TCRB': {'common_name': 'T CrB (Symbiotic Recurrent Nova, Band 1 SiO spw17)', 'role': 'SCIENCE', 'subrole': 'SYMBIOTIC_NOVA_ALMA_B1', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 1220110705972528512', 'ra_deg': 239.8756539, 'dec_deg': 25.9202238, 'pmra': -4.4605, 'pmdec': 12.0159, 'dist_pc': 915.79026, 'within_10pc': False, 'phot_g_mag': 8.7245, 'phot_bp_mag': 9.9107, 'phot_rp_mag': 7.6198, 'teff_k': 3400.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.1, 'prior_rv_kms': -4.4618, 'n_exoplanets': 0}, 'CIRCINUSGAL': {'common_name': 'Circinus Galaxy (Seyfert 2, 4.2 Mpc, Band 1 8.56 mm Frontier)', 'role': 'CONTROL', 'subrole': 'EXTRAGALACTIC_SEYFERT2_CONTROL', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'CIRCINUSGAL', 'ra_deg': 213.2914583, 'dec_deg': -65.3392222, 'pmra': 0.0, 'pmdec': 0.0, 'dist_pc': 4200000.0, 'within_10pc': False, 'phot_g_mag': 14.0194, 'phot_bp_mag': None, 'phot_rp_mag': None, 'teff_k': 4500.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.0, 'prior_rv_kms': 434.0, 'n_exoplanets': 0}, 'SPIDERWEBGAL': {'common_name': 'Spiderweb Protocluster (z=2.16, Control)', 'role': 'CONTROL', 'subrole': 'EXTRAGALACTIC_HIGHZ_CONTROL', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'SPIDERWEBGAL', 'ra_deg': 175.20142, 'dec_deg': -26.48571, 'pmra': 0.0, 'pmdec': 0.0, 'dist_pc': 17200000000.0, 'within_10pc': False, 'phot_g_mag': 16.0, 'phot_bp_mag': None, 'phot_rp_mag': None, 'teff_k': 5500.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.0, 'prior_rv_kms': 245000.0, 'n_exoplanets': 0}, 'HDFSMUSE': {'common_name': 'HDF-S MUSE Extragalactic Field (Control)', 'role': 'CONTROL', 'subrole': 'EXTRAGALACTIC_FIELD_CONTROL', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'HDFSMUSE', 'ra_deg': 338.2318333, 'dec_deg': -60.5630556, 'pmra': 0.0, 'pmdec': 0.0, 'dist_pc': 6700000000.0, 'within_10pc': False, 'phot_g_mag': 18.1608, 'phot_bp_mag': None, 'phot_rp_mag': None, 'teff_k': 5500.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.0, 'prior_rv_kms': 180000.0, 'n_exoplanets': 0}, 'TWHYA': {'common_name': 'TW Hya (Closest Face-on Protoplanetary Disk, 60.1 pc)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 5401795662560500352', 'ra_deg': 165.4659029, 'dec_deg': -34.7047932, 'pmra': -68.3094, 'pmdec': -13.9001, 'dist_pc': 60.13634, 'within_10pc': False, 'phot_g_mag': 10.4509, 'phot_bp_mag': 11.1786, 'phot_rp_mag': 9.5335, 'teff_k': 3848.3, 'mh_dex': -0.5077, 'stellar_mass_msun': 0.88, 'prior_rv_kms': 2.9, 'n_exoplanets': 0}, 'V4046SGR': {'common_name': 'V4046 Sgr (Circumbinary Protoplanetary Disk, 71.5 pc)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 4045698423617983488', 'ra_deg': 273.543693, 'dec_deg': -32.7931557, 'pmra': 3.5098, 'pmdec': -52.7206, 'dist_pc': 71.48327, 'within_10pc': False, 'phot_g_mag': 9.9276, 'phot_bp_mag': 10.6167, 'phot_rp_mag': 9.0989, 'teff_k': 4694.1, 'mh_dex': -0.3548, 'stellar_mass_msun': 1.75, 'prior_rv_kms': -19.7276, 'n_exoplanets': 0}, 'HD97048': {'common_name': 'HD 97048 (1-pl Herbig Ae/Be Disk Host)', 'role': 'SCIENCE', 'subrole': 'PLANET_HOST_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 5201128124701636864', 'ra_deg': 167.0133275, 'dec_deg': -77.6548528, 'pmra': -22.5255, 'pmdec': 1.2907, 'dist_pc': 184.40624, 'within_10pc': False, 'phot_g_mag': 8.3522, 'phot_bp_mag': 8.556, 'phot_rp_mag': 7.9559, 'teff_k': 10000.0, 'mh_dex': 0.0, 'stellar_mass_msun': 2.4, 'prior_rv_kms': 12.0, 'n_exoplanets': 1}, 'HD179218': {'common_name': 'HD 179218 (Herbig Ae/Be Disk)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 4512807594894454912', 'ra_deg': 287.7969159, 'dec_deg': 15.7875829, 'pmra': 5.3428, 'pmdec': -21.088, 'dist_pc': 260.09217, 'within_10pc': False, 'phot_g_mag': 7.3722, 'phot_bp_mag': 7.4037, 'phot_rp_mag': 7.2649, 'teff_k': 9600.0, 'mh_dex': 0.0, 'stellar_mass_msun': 2.6, 'prior_rv_kms': 16.2165, 'n_exoplanets': 0}, 'V644SCO': {'common_name': 'V644 Sco (Evolved Red Giant/AGB)', 'role': 'SCIENCE', 'subrole': 'AGB_STAR_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 5960377015828717952', 'ra_deg': 261.5789513, 'dec_deg': -40.0311743, 'pmra': 1.4995, 'pmdec': -0.8324, 'dist_pc': 1352.58066, 'within_10pc': False, 'phot_g_mag': 7.8039, 'phot_bp_mag': 9.9086, 'phot_rp_mag': 6.5211, 'teff_k': 3100.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.5, 'prior_rv_kms': -20.0, 'n_exoplanets': 0}, 'DRSER': {'common_name': 'DR Ser (Carbon AGB Star)', 'role': 'SCIENCE', 'subrole': 'AGB_CARBON_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 4285226383221001088', 'ra_deg': 281.8376052, 'dec_deg': 5.4551738, 'pmra': 1.9132, 'pmdec': 1.2142, 'dist_pc': 1102.55352, 'within_10pc': False, 'phot_g_mag': 7.7418, 'phot_bp_mag': 9.8107, 'phot_rp_mag': 6.4549, 'teff_k': 2650.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.5, 'prior_rv_kms': 5.0, 'n_exoplanets': 0}, 'TMIC': {'common_name': 'T Mic (Semiregular M6e AGB Star)', 'role': 'SCIENCE', 'subrole': 'AGB_MIRA_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 6797890896841285376', 'ra_deg': 306.9799224, 'dec_deg': -28.2609992, 'pmra': -6.9462, 'pmdec': 12.5438, 'dist_pc': 185.55523, 'within_10pc': False, 'phot_g_mag': 4.2328, 'phot_bp_mag': 7.6515, 'phot_rp_mag': 2.8671, 'teff_k': 3200.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.4, 'prior_rv_kms': 25.0, 'n_exoplanets': 0}, 'GY92_274': {'common_name': 'GY92 274 (Ophiuchus Embedded YSO, 138 pc)', 'role': 'SCIENCE', 'subrole': 'EMBEDDED_YSO_ALMA_B3', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'GY92_274', 'ra_deg': 246.8725875, 'dec_deg': -24.6545972, 'pmra': 0.0, 'pmdec': 0.0, 'dist_pc': 138.4, 'within_10pc': False, 'phot_g_mag': 16.0, 'phot_bp_mag': None, 'phot_rp_mag': None, 'teff_k': 3500.0, 'mh_dex': 0.0, 'stellar_mass_msun': 0.4, 'prior_rv_kms': 3.8, 'n_exoplanets': 0}, 'GOTAU': {'common_name': 'GO Tau (Taurus Extended YSO Disk)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 148106316500918272', 'ra_deg': 70.7628407, 'dec_deg': 25.3384403, 'pmra': 4.7361, 'pmdec': -20.1089, 'dist_pc': 142.38226, 'within_10pc': False, 'phot_g_mag': 13.8283, 'phot_bp_mag': 15.2486, 'phot_rp_mag': 12.6224, 'teff_k': 3622.3, 'mh_dex': -0.4295, 'stellar_mass_msun': 0.48, 'prior_rv_kms': -18.5493, 'n_exoplanets': 0}, 'CLOVERLEAF': {'common_name': 'Cloverleaf Quasar H1413+117 (z=2.558, Control)', 'role': 'CONTROL', 'subrole': 'EXTRAGALACTIC_LENSED_QSO_CONTROL', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'CLOVERLEAF', 'ra_deg': 213.9427083, 'dec_deg': 11.4953889, 'pmra': 0.0, 'pmdec': 0.0, 'dist_pc': 21000000000.0, 'within_10pc': False, 'phot_g_mag': 17.5725, 'phot_bp_mag': None, 'phot_rp_mag': None, 'teff_k': 6000.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.0, 'prior_rv_kms': 256000.0, 'n_exoplanets': 0}, 'CYTAU': {'common_name': 'CY Tau (Taurus T Tauri Disk)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 164698634160139264', 'ra_deg': 64.3905803, 'dec_deg': 28.3462226, 'pmra': 8.8863, 'pmdec': -25.6785, 'dist_pc': 126.32891, 'within_10pc': False, 'phot_g_mag': 12.4795, 'phot_bp_mag': 13.5995, 'phot_rp_mag': 11.3884, 'teff_k': 3715.3, 'mh_dex': 0.1662, 'stellar_mass_msun': 0.42, 'prior_rv_kms': 7.0, 'n_exoplanets': 0}, 'DOAR25': {'common_name': 'DoAr 25 (Ophiuchus YSO Disk)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA_B1_B3', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 6049118388788178816', 'ra_deg': 246.5986747, 'dec_deg': -24.720641, 'pmra': -7.8306, 'pmdec': -26.1879, 'dist_pc': 138.1609, 'within_10pc': False, 'phot_g_mag': 12.7653, 'phot_bp_mag': 14.1476, 'phot_rp_mag': 11.5644, 'teff_k': 4250.0, 'mh_dex': 0.0, 'stellar_mass_msun': 0.9, 'prior_rv_kms': -12.61, 'n_exoplanets': 0}, 'TPYX': {'common_name': 'T Pyx (Recurrent Nova Shell)', 'role': 'SCIENCE', 'subrole': 'NOVA_SHELL_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 5628258258606113792', 'ra_deg': 136.1728692, 'dec_deg': -32.3833154, 'pmra': -2.4949, 'pmdec': 0.3319, 'dist_pc': 2730.85795, 'within_10pc': False, 'phot_g_mag': 15.6189, 'phot_bp_mag': 16.0329, 'phot_rp_mag': 15.025, 'teff_k': 6500.0, 'mh_dex': -0.4942, 'stellar_mass_msun': 1.1, 'prior_rv_kms': 50.0, 'n_exoplanets': 0}, 'CKVUL': {'common_name': 'CK Vul (Nova 1670 Merger Remnant)', 'role': 'SCIENCE', 'subrole': 'NOVA_REMNANT_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 2027981238207987584', 'ra_deg': 296.9097315, 'dec_deg': 27.3196373, 'pmra': -1.4794, 'pmdec': -4.9413, 'dist_pc': 1400.39617, 'within_10pc': False, 'phot_g_mag': 13.8767, 'phot_bp_mag': 14.3092, 'phot_rp_mag': 13.2636, 'teff_k': 5000.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.2, 'prior_rv_kms': -10.0, 'n_exoplanets': 0}, 'MPMUS': {'common_name': 'MP Mus (Lower Cen Crux Disk)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 5844296281847839232', 'ra_deg': 200.5309359, 'dec_deg': -69.6368165, 'pmra': -38.353, 'pmdec': -20.0037, 'dist_pc': 97.89364, 'within_10pc': False, 'phot_g_mag': 9.9729, 'phot_bp_mag': 10.5432, 'phot_rp_mag': 9.2341, 'teff_k': 5110.0, 'mh_dex': -0.578, 'stellar_mass_msun': 1.3, 'prior_rv_kms': 7.2049, 'n_exoplanets': 0}, 'HD135344B': {'common_name': 'HD 135344B (SAO 206462 Spiral Transition Disk)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 6199395656645840384', 'ra_deg': 228.9538383, 'dec_deg': -37.148921, 'pmra': -18.7377, 'pmdec': -24.0078, 'dist_pc': 134.94275, 'within_10pc': False, 'phot_g_mag': 7.7482, 'phot_bp_mag': 7.7688, 'phot_rp_mag': 7.6795, 'teff_k': 6600.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.6, 'prior_rv_kms': 29.3063, 'n_exoplanets': 0}, 'GXMON': {'common_name': 'GX Mon (Mira/AGB Envelope)', 'role': 'SCIENCE', 'subrole': 'AGB_OHIR_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 3157390786124423168', 'ra_deg': 103.1960057, 'dec_deg': 8.4219171, 'pmra': -0.9221, 'pmdec': -12.2821, 'dist_pc': 568.637, 'within_10pc': False, 'phot_g_mag': 8.934, 'phot_bp_mag': 14.2791, 'phot_rp_mag': 7.2851, 'teff_k': 2600.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.5, 'prior_rv_kms': -9.0, 'n_exoplanets': 0}, 'GWORI': {'common_name': 'GW Ori (Triple T Tauri Circumtriple Disk)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 3340856533286969600', 'ra_deg': 82.2849596, 'dec_deg': 11.8701834, 'pmra': -2.3512, 'pmdec': -0.3955, 'dist_pc': 407.99601, 'within_10pc': False, 'phot_g_mag': 9.4459, 'phot_bp_mag': 9.9961, 'phot_rp_mag': 8.691, 'teff_k': 5500.0, 'mh_dex': 0.0, 'stellar_mass_msun': 2.5, 'prior_rv_kms': 22.0, 'n_exoplanets': 0}, 'GHZ2GAL': {'common_name': 'GHZ2 / GLASS-z12 Galaxy (z=12.33, Control)', 'role': 'CONTROL', 'subrole': 'EXTRAGALACTIC_HIGHZ_CONTROL', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'GHZ2GAL', 'ra_deg': 3.4989854, 'dec_deg': -30.3247528, 'pmra': 0.0, 'pmdec': 0.0, 'dist_pc': 129000000000.0, 'within_10pc': False, 'phot_g_mag': 16.0, 'phot_bp_mag': None, 'phot_rp_mag': None, 'teff_k': 8000.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.0, 'prior_rv_kms': 296000.0, 'n_exoplanets': 0}, 'MWC480': {'common_name': 'MWC 480 (Taurus Herbig Ae Disk)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 156728858488206080', 'ra_deg': 74.6927971, 'dec_deg': 29.8434958, 'pmra': 4.6608, 'pmdec': -25.1683, 'dist_pc': 156.21483, 'within_10pc': False, 'phot_g_mag': 7.654, 'phot_bp_mag': 7.7396, 'phot_rp_mag': 7.4562, 'teff_k': 8250.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.97, 'prior_rv_kms': 5.1, 'n_exoplanets': 0}, 'HD101584': {'common_name': 'HD 101584 (Post-AGB Common Envelope Binary)', 'role': 'SCIENCE', 'subrole': 'POST_AGB_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 5343168568718268800', 'ra_deg': 175.2449591, 'dec_deg': -55.5738385, 'pmra': -7.9352, 'pmdec': -0.2432, 'dist_pc': 1834.17362, 'within_10pc': False, 'phot_g_mag': 6.9196, 'phot_bp_mag': 7.1032, 'phot_rp_mag': 6.4736, 'teff_k': 8500.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.0, 'prior_rv_kms': 41.0, 'n_exoplanets': 0}, 'WLY248': {'common_name': 'WLY 2-48 / Oph IRS 48 (Dust Trap Disk)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 6049145880875631744', 'ra_deg': 246.9049184, 'dec_deg': -24.5098377, 'pmra': -8.7214, 'pmdec': -24.408, 'dist_pc': 136.31875, 'within_10pc': False, 'phot_g_mag': 16.2681, 'phot_bp_mag': 19.189, 'phot_rp_mag': 14.6999, 'teff_k': 9000.0, 'mh_dex': 0.0, 'stellar_mass_msun': 2.0, 'prior_rv_kms': 4.5, 'n_exoplanets': 0}, 'HD121617': {'common_name': 'HD 121617 (Gas-rich Debris Disk)', 'role': 'SCIENCE', 'subrole': 'DEBRIS_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 6095178206488363264', 'ra_deg': 209.4211734, 'dec_deg': -47.0096165, 'pmra': -28.3713, 'pmdec': -22.9758, 'dist_pc': 117.89028, 'within_10pc': False, 'phot_g_mag': 7.2918, 'phot_bp_mag': 7.306, 'phot_rp_mag': 7.2386, 'teff_k': 9651.7, 'mh_dex': -0.9737, 'stellar_mass_msun': 1.9, 'prior_rv_kms': 5.934, 'n_exoplanets': 0}, 'HD131488': {'common_name': 'HD 131488 (Upper Sco CO-rich Debris Disk)', 'role': 'SCIENCE', 'subrole': 'DEBRIS_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 6101164531905526528', 'ra_deg': 223.7833449, 'dec_deg': -41.1204883, 'pmra': -18.3987, 'pmdec': -22.2762, 'dist_pc': 152.24462, 'within_10pc': False, 'phot_g_mag': 8.0051, 'phot_bp_mag': 8.0336, 'phot_rp_mag': 7.9224, 'teff_k': 8800.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.88, 'prior_rv_kms': 0.9268, 'n_exoplanets': 0}, 'HD131835': {'common_name': 'HD 131835 (Sco-Cen Shielded CO Debris Disk)', 'role': 'SCIENCE', 'subrole': 'DEBRIS_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 6202242567124829312', 'ra_deg': 224.2268209, 'dec_deg': -35.6955718, 'pmra': -23.4084, 'pmdec': -24.9794, 'dist_pc': 129.73941, 'within_10pc': False, 'phot_g_mag': 7.8813, 'phot_bp_mag': 7.9387, 'phot_rp_mag': 7.7488, 'teff_k': 8408.5, 'mh_dex': -0.6016, 'stellar_mass_msun': 1.77, 'prior_rv_kms': -1.971, 'n_exoplanets': 0}, 'HD21997': {'common_name': 'HD 21997 (Columba Cold Gas Debris Disk)', 'role': 'SCIENCE', 'subrole': 'DEBRIS_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 5084963312478488960', 'ra_deg': 52.9737954, 'dec_deg': -25.6142164, 'pmra': 53.9977, 'pmdec': -14.9424, 'dist_pc': 69.68575, 'within_10pc': False, 'phot_g_mag': 6.3719, 'phot_bp_mag': 6.415, 'phot_rp_mag': 6.2649, 'teff_k': 8300.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.85, 'prior_rv_kms': 16.0372, 'n_exoplanets': 0}, 'HD100453': {'common_name': 'HD 100453 (Binary Herbig Ae Disk)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 5345011040956367104', 'ra_deg': 173.2729544, 'dec_deg': -54.3246225, 'pmra': -36.9616, 'pmdec': -5.8598, 'dist_pc': 103.78236, 'within_10pc': False, 'phot_g_mag': 7.7354, 'phot_bp_mag': 7.8711, 'phot_rp_mag': 7.4582, 'teff_k': 7160.9, 'mh_dex': -0.7877, 'stellar_mass_msun': 1.66, 'prior_rv_kms': 14.5972, 'n_exoplanets': 0}, 'HD139614': {'common_name': 'HD 139614 (Herbig Ae Ringed Disk)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 6001669793442284416', 'ra_deg': 235.1931493, 'dec_deg': -42.4983179, 'pmra': -18.0997, 'pmdec': -25.3554, 'dist_pc': 133.61918, 'within_10pc': False, 'phot_g_mag': 8.219, 'phot_bp_mag': 8.3297, 'phot_rp_mag': 7.9906, 'teff_k': 7513.0, 'mh_dex': -0.7848, 'stellar_mass_msun': 1.5, 'prior_rv_kms': 3.4982, 'n_exoplanets': 0}, 'HD145718': {'common_name': 'HD 145718 (UX Ori YSO Disk)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 6242664222334854784', 'ra_deg': 243.298258, 'dec_deg': -22.4852773, 'pmra': -8.5875, 'pmdec': -23.5259, 'dist_pc': 154.73223, 'within_10pc': False, 'phot_g_mag': 8.7582, 'phot_bp_mag': 9.0112, 'phot_rp_mag': 8.3154, 'teff_k': 8054.2, 'mh_dex': -1.0448, 'stellar_mass_msun': 1.62, 'prior_rv_kms': 23.8987, 'n_exoplanets': 0}, 'SZ65J1608': {'common_name': 'Sz 65 (Lupus Wide Binary YSO Disk)', 'role': 'SCIENCE', 'subrole': 'YSO_DISK_ALMA', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 5997033290348155136', 'ra_deg': 242.2217817, 'dec_deg': -39.2445948, 'pmra': -10.514, 'pmdec': -23.7987, 'dist_pc': 163.00158, 'within_10pc': False, 'phot_g_mag': 15.0221, 'phot_bp_mag': 17.0248, 'phot_rp_mag': 13.6966, 'teff_k': 3833.9, 'mh_dex': 0.3832, 'stellar_mass_msun': 0.7, 'prior_rv_kms': 25.7832, 'n_exoplanets': 0}, 'NGC3256GAL': {'common_name': 'NGC 3256 (LIRG Merger Control, 44 Mpc)', 'role': 'CONTROL', 'subrole': 'EXTRAGALACTIC_LIRG_CONTROL', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'NGC3256GAL', 'ra_deg': 156.9634583, 'dec_deg': -43.9046111, 'pmra': 0.0, 'pmdec': 0.0, 'dist_pc': 44000000.0, 'within_10pc': False, 'phot_g_mag': 15.4134, 'phot_bp_mag': None, 'phot_rp_mag': None, 'teff_k': 5500.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.0, 'prior_rv_kms': 2804.0, 'n_exoplanets': 0}, 'PKS0023GAL': {'common_name': 'PKS 0023-26 (GPS Radio Galaxy z=0.322, Band 1)', 'role': 'CONTROL', 'subrole': 'EXTRAGALACTIC_AGN_CONTROL', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'PKS0023GAL', 'ra_deg': 6.4548179, 'dec_deg': -26.0368381, 'pmra': 0.0, 'pmdec': 0.0, 'dist_pc': 1690000000.0, 'within_10pc': False, 'phot_g_mag': 20.0843, 'phot_bp_mag': None, 'phot_rp_mag': None, 'teff_k': 5500.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.0, 'prior_rv_kms': 81300.0, 'n_exoplanets': 0}, '3C218GAL': {'common_name': '3C 218 / Hydra A (Radio Galaxy z=0.0549, Band 1)', 'role': 'CONTROL', 'subrole': 'EXTRAGALACTIC_AGN_CONTROL', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': '3C218GAL', 'ra_deg': 139.5235458, 'dec_deg': -12.0955528, 'pmra': 0.0, 'pmdec': 0.0, 'dist_pc': 245000000.0, 'within_10pc': False, 'phot_g_mag': 19.556, 'phot_bp_mag': None, 'phot_rp_mag': None, 'teff_k': 4800.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.0, 'prior_rv_kms': 16459.0, 'n_exoplanets': 0}, 'Q0152GAL': {'common_name': 'Q0152+0023 (Quasar Host z=0.4814)', 'role': 'CONTROL', 'subrole': 'EXTRAGALACTIC_QSO_CONTROL', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Q0152GAL', 'ra_deg': 28.2116667, 'dec_deg': 0.3864056, 'pmra': 0.0, 'pmdec': 0.0, 'dist_pc': 2710000000.0, 'within_10pc': False, 'phot_g_mag': 18.3117, 'phot_bp_mag': None, 'phot_rp_mag': None, 'teff_k': 6000.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.0, 'prior_rv_kms': 111000.0, 'n_exoplanets': 0}, 'M83GAL': {'common_name': 'M83 Nucleus (Spiral Control, 4.66 Mpc)', 'role': 'CONTROL', 'subrole': 'EXTRAGALACTIC_SPIRAL_CONTROL', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'M83GAL', 'ra_deg': 204.2212648, 'dec_deg': -29.8780483, 'pmra': 0.0, 'pmdec': 0.0, 'dist_pc': 4660000.0, 'within_10pc': False, 'phot_g_mag': 16.1912, 'phot_bp_mag': None, 'phot_rp_mag': None, 'teff_k': 5000.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.0, 'prior_rv_kms': 513.0, 'n_exoplanets': 0}, 'NGC4038GAL': {'common_name': 'NGC 4038 Antennae (Control, 22 Mpc)', 'role': 'CONTROL', 'subrole': 'EXTRAGALACTIC_MERGER_CONTROL', 'science_track': 'ALMA_MM_V59', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'NGC4038GAL', 'ra_deg': 180.4765079, 'dec_deg': -18.88453, 'pmra': 0.0, 'pmdec': 0.0, 'dist_pc': 22000000.0, 'within_10pc': False, 'phot_g_mag': 17.8762, 'phot_bp_mag': None, 'phot_rp_mag': None, 'teff_k': 5500.0, 'mh_dex': 0.0, 'stellar_mass_msun': 1.0, 'prior_rv_kms': 1642.0, 'n_exoplanets': 0}, 'HIP56998': {'common_name': 'HD 101581 / HIP 56998 (2-pl ESPRESSO R=140k, 12.78 pc)', 'role': 'SCIENCE', 'subrole': 'ORBITAL_ESPRESSO_2PL', 'science_track': 'COMB_DRIFT_V59_ORBIT', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 5378886891123024512', 'ra_deg': 175.2561754, 'dec_deg': -44.4041148, 'pmra': -660.6341, 'pmdec': 242.0965, 'dist_pc': 12.78335, 'within_10pc': False, 'phot_g_mag': 7.3942, 'phot_bp_mag': 7.9795, 'phot_rp_mag': 6.6657, 'teff_k': 4675.0, 'mh_dex': 0.0, 'stellar_mass_msun': 0.653, 'prior_rv_kms': 13.5495, 'n_exoplanets': 2}, 'HD140901': {'common_name': 'HD 140901 (2-pl e=0.77, 21.6 yr HARPS, 15.25 pc)', 'role': 'SCIENCE', 'subrole': 'ORBITAL_ECCENTRIC_2PL', 'science_track': 'COMB_DRIFT_V59_ORBIT', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 6009538585839374336', 'ra_deg': 236.8689134, 'dec_deg': -37.917263, 'pmra': -415.5066, 'pmdec': -213.9909, 'dist_pc': 15.24648, 'within_10pc': False, 'phot_g_mag': 5.8338, 'phot_bp_mag': 6.1896, 'phot_rp_mag': 5.3106, 'teff_k': 5540.1, 'mh_dex': -0.3561, 'stellar_mass_msun': 1.06, 'prior_rv_kms': -6.9189, 'n_exoplanets': 2}, 'GJ3222': {'common_name': 'GJ 3222 (1-pl e=0.929 Extreme Eccentric, 17.68 pc)', 'role': 'SCIENCE', 'subrole': 'ORBITAL_EXTREME_ECC_1PL', 'science_track': 'COMB_DRIFT_V59_ORBIT', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 4852870701505115904', 'ra_deg': 50.8972694, 'dec_deg': -40.0762227, 'pmra': 63.9855, 'pmdec': 35.1747, 'dist_pc': 17.68129, 'within_10pc': False, 'phot_g_mag': 6.7038, 'phot_bp_mag': 7.1206, 'phot_rp_mag': 6.1157, 'teff_k': 5304.4, 'mh_dex': 0.1026, 'stellar_mass_msun': 0.89, 'prior_rv_kms': 12.132, 'n_exoplanets': 1}, 'GJ676A': {'common_name': 'GJ 676 A (4-pl M-dwarf Multi-Planet System, 15.98 pc)', 'role': 'SCIENCE', 'subrole': 'ORBITAL_MULTI_4PL', 'science_track': 'COMB_DRIFT_V59_ORBIT', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 5925209583053212800', 'ra_deg': 262.5448323, 'dec_deg': -51.6378034, 'pmra': -258.7586, 'pmdec': -185.1191, 'dist_pc': 15.97991, 'within_10pc': False, 'phot_g_mag': 8.8669, 'phot_bp_mag': 9.8094, 'phot_rp_mag': 7.9065, 'teff_k': 3734.0, 'mh_dex': 0.0, 'stellar_mass_msun': 0.626, 'prior_rv_kms': -39.8228, 'n_exoplanets': 4}, 'HR810': {'common_name': 'HR 810 / iot Hor (1-pl Giant Host, 17.36 pc)', 'role': 'SCIENCE', 'subrole': 'ORBITAL_GIANT_1PL', 'science_track': 'COMB_DRIFT_V59_ORBIT', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 4745373133284418816', 'ra_deg': 40.6417912, 'dec_deg': -50.7993179, 'pmra': 333.7156, 'pmdec': 219.4233, 'dist_pc': 17.35715, 'within_10pc': False, 'phot_g_mag': 5.2563, 'phot_bp_mag': 5.542, 'phot_rp_mag': 4.8156, 'teff_k': 6006.5, 'mh_dex': -0.2154, 'stellar_mass_msun': 1.34, 'prior_rv_kms': 16.9353, 'n_exoplanets': 1}, 'GL479': {'common_name': 'GJ 479 (0-pl <10 pc M3V Control, 9.49 pc)', 'role': 'CONTROL', 'subrole': 'SUB_10PC_ORBIT_CONTROL', 'science_track': 'COMB_DRIFT_V59_ORBIT', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 6078114541943893888', 'ra_deg': 189.4600973, 'dec_deg': -52.0013463, 'pmra': -1034.7101, 'pmdec': 29.7923, 'dist_pc': 9.49247, 'within_10pc': True, 'phot_g_mag': 9.565, 'phot_bp_mag': 10.906, 'phot_rp_mag': 8.4166, 'teff_k': 3163.6, 'mh_dex': -0.7917, 'stellar_mass_msun': 0.43, 'prior_rv_kms': -5.9254, 'n_exoplanets': 0}, 'HIP31293': {'common_name': 'HIP 31293 / L 34-26 (0-pl <10 pc M3V, 8.84 pc)', 'role': 'CONTROL', 'subrole': 'SUB_10PC_CONTROL', 'science_track': 'SUB_10PC_OPTICAL_CONTROL', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 5260759175761501696', 'ra_deg': 98.4249869, 'dec_deg': -75.6287409, 'pmra': -297.9547, 'pmdec': 280.5873, 'dist_pc': 8.83935, 'within_10pc': True, 'phot_g_mag': 9.3847, 'phot_bp_mag': 10.6943, 'phot_rp_mag': 8.2456, 'teff_k': 3244.4, 'mh_dex': -0.5281, 'stellar_mass_msun': 0.35, 'prior_rv_kms': 11.729, 'n_exoplanets': 0}, 'GL358': {'common_name': 'GJ 358 (0-pl <10 pc M2V Control, 9.61 pc)', 'role': 'CONTROL', 'subrole': 'SUB_10PC_CONTROL', 'science_track': 'SUB_10PC_OPTICAL_CONTROL', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 5425628298649940608', 'ra_deg': 144.9400958, 'dec_deg': -41.06597, 'pmra': -527.1472, 'pmdec': 357.0394, 'dist_pc': 9.60654, 'within_10pc': True, 'phot_g_mag': 9.6314, 'phot_bp_mag': 11.0035, 'phot_rp_mag': 8.471, 'teff_k': 3193.7, 'mh_dex': -1.1669, 'stellar_mass_msun': 0.42, 'prior_rv_kms': 18.0582, 'n_exoplanets': 0}, 'GL569A': {'common_name': 'GJ 569 A (0-pl <10 pc M2V Control, 9.95 pc)', 'role': 'CONTROL', 'subrole': 'SUB_10PC_CONTROL', 'science_track': 'SUB_10PC_OPTICAL_CONTROL', 'panchromatic_bridge': False, 'is_prior_bridge': False, 'gaia_source_id': 'Gaia DR3 1187851653287128576', 'ra_deg': 223.6231086, 'dec_deg': 16.100531, 'pmra': 279.1174, 'pmdec': -117.9082, 'dist_pc': 9.94785, 'within_10pc': True, 'phot_g_mag': 9.1234, 'phot_bp_mag': 10.3159, 'phot_rp_mag': 8.0342, 'teff_k': 3268.8, 'mh_dex': -0.8972, 'stellar_mass_msun': 0.49, 'prior_rv_kms': -7.9659, 'n_exoplanets': 0}}

ALMA_63_SPECS: list[dict[str, Any]] = [{'band': 1, 'canon': 'ABAUR', 'alma_target': 'AB_Aurigae', 'mous': 'uid://A001/X37dc/X27', 'role': 'SCIENCE', 'ra': 73.94105989580467, 'dec': 30.55102106008176, 'sep_prior': 0.23, 'prior_ref': 'ABAUR', 'freq_ghz': 37.2065166106932, 'um_min': 7859.551644544492, 'um_max': 8265.730669317074, 'rp': 37142.2659999488, 'res_arcsec': 0.16998611140409062, 'expt': 1378.944, 'mjd': 60922.443627, 'soda_id': 'member.uid___A001_X37dc_X27.AB_Aurigae_sci.spw21.cube.I.selfcal.pbcor.fits', 'obs_id': 'uid://A001/X37dc/X27.source.AB_Aurigae.spw.21'}, {'band': 1, 'canon': 'PDS70', 'alma_target': 'PDS_70', 'mous': 'uid://A001/X3788/X7eab', 'role': 'SCIENCE', 'ra': 212.0420259070681, 'dec': -41.39810727999901, 'sep_prior': 2.06, 'prior_ref': '', 'freq_ghz': 43.10779611590816, 'um_min': 6806.4580456577905, 'um_max': 7109.090601597104, 'rp': 37352.51557088996, 'res_arcsec': 0.13200452184165087, 'expt': 25310.476, 'mjd': 60881.068177, 'soda_id': 'member.uid___A001_X3788_X7eab.PDS_70_sci.spw27.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X3788/X7eab.source.PDS_70.spw.27'}, {'band': 1, 'canon': 'HD169142', 'alma_target': 'HD169142', 'mous': 'uid://A001/X37dc/X1f', 'role': 'SCIENCE', 'ra': 276.1240619756941, 'dec': -29.780638708052017, 'sep_prior': 0.37, 'prior_ref': 'HD169142', 'freq_ghz': 37.21060971807328, 'um_min': 7858.5859500727, 'um_max': 8264.933337181012, 'rp': 37142.2659999488, 'res_arcsec': 0.13182910546575485, 'expt': 5624.457, 'mjd': 60894.199955, 'soda_id': 'member.uid___A001_X37dc_X1f.HD169142_sci.spw21.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X37dc/X1f.source.HD169142.spw.21'}, {'band': 1, 'canon': 'HLTAU', 'alma_target': 'HL_Tau', 'mous': 'uid://A001/X362b/X50f', 'role': 'SCIENCE', 'ra': 67.91049083226049, 'dec': 18.23263734375253, 'sep_prior': 0.28, 'prior_ref': 'HLTAU', 'freq_ghz': 39.17680308326474, 'um_min': 7467.801339161654, 'um_max': 7846.1356844058055, 'rp': 33901.8304497827, 'res_arcsec': 0.2936081176306792, 'expt': 14043.199, 'mjd': 60231.337979, 'soda_id': 'member.uid___A001_X362b_X50f.HL_Tau_sci.spw23.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X362b/X50f.source.HL_Tau.spw.23'}, {'band': 1, 'canon': 'AS209', 'alma_target': 'AS_209', 'mous': 'uid://A001/X37dc/X2d', 'role': 'SCIENCE', 'ra': 252.31370792549973, 'dec': -14.369236280518754, 'sep_prior': 17329.14, 'prior_ref': '', 'freq_ghz': 37.210932136442885, 'um_min': 7858.61901397936, 'um_max': 8264.749840713363, 'rp': 37142.2659999488, 'res_arcsec': 0.15644650430936513, 'expt': 2086.56, 'mjd': 60932.954621, 'soda_id': 'member.uid___A001_X37dc_X2d.AS_209_sci.spw21.cube.I.selfcal.pbcor.fits', 'obs_id': 'uid://A001/X37dc/X2d.source.AS_209.spw.21'}, {'band': 1, 'canon': 'ELIAS224', 'alma_target': 'Elias_2-24', 'mous': 'uid://A001/X37dc/X33', 'role': 'SCIENCE', 'ra': 246.60030488310142, 'dec': -24.270578168460922, 'sep_prior': 4242.31, 'prior_ref': '', 'freq_ghz': 37.21122814665121, 'um_min': 7858.531981851994, 'um_max': 8264.711213465114, 'rp': 37142.2659999488, 'res_arcsec': 0.12907933332262275, 'expt': 5660.832, 'mjd': 60895.080629, 'soda_id': 'member.uid___A001_X37dc_X33.Elias_2-24_sci.spw21.cube.I.selfcal.pbcor.fits', 'obs_id': 'uid://A001/X37dc/X33.source.Elias_2-24.spw.21'}, {'band': 1, 'canon': 'RXJ1852', 'alma_target': 'RXJ1852.3-3700', 'mous': 'uid://A001/X3788/X781b', 'role': 'SCIENCE', 'ra': 283.07211302683385, 'dec': -37.003521674586224, 'sep_prior': 10822.56, 'prior_ref': '', 'freq_ghz': 43.107347093846066, 'um_min': 6806.590446481129, 'um_max': 7109.097560832617, 'rp': 37352.51557088996, 'res_arcsec': 0.14596968159766643, 'expt': 5152.893, 'mjd': 60931.067754, 'soda_id': 'member.uid___A001_X3788_X781b._RXJ1852.3-3700__sci.spw27.cube.I.selfcal.pbcor.fits', 'obs_id': 'uid://A001/X3788/X781b.source.RXJ1852.3-3700.spw.27'}, {'band': 1, 'canon': 'HD34282', 'alma_target': 'HD34282', 'mous': 'uid://A001/X3788/X7db4', 'role': 'SCIENCE', 'ra': 79.00198841461409, 'dec': -9.809838867027569, 'sep_prior': 12346.73, 'prior_ref': '', 'freq_ghz': 37.208222218604746, 'um_min': 7859.18356090983, 'um_max': 8265.360404998446, 'rp': 37142.2659999488, 'res_arcsec': 0.11622229197415054, 'expt': 8273.661, 'mjd': 60920.341017, 'soda_id': 'member.uid___A001_X3788_X7db4.HD34282_sci.spw21.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X3788/X7db4.source.HD34282.spw.21'}, {'band': 1, 'canon': 'SZ90', 'alma_target': 'Sz90', 'mous': 'uid://A001/X3645/X230', 'role': 'SCIENCE', 'ra': 241.79187334211034, 'dec': -39.184411274475, 'sep_prior': 1023.27, 'prior_ref': 'HD144668', 'freq_ghz': 41.166416645553, 'um_min': 7120.0772121345035, 'um_max': 7452.405845956277, 'rp': 35636.252595111415, 'res_arcsec': 0.8958846004744503, 'expt': 1814.276, 'mjd': 60432.282873, 'soda_id': 'member.uid___A001_X3645_X230.Sz90_sci.spw25.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X3645/X230.source.Sz90.spw.25'}, {'band': 1, 'canon': 'TCRB', 'alma_target': 'T_CrB', 'mous': 'uid://A001/X3789/X9a', 'role': 'SCIENCE', 'ra': 239.8756416321544, 'dec': 25.920253223780637, 'sep_prior': 25974.6, 'prior_ref': 'BD332642', 'freq_ghz': 42.82192757355961, 'um_min': 6996.133780974365, 'um_max': 7005.692606016342, 'rp': 303271.27156647353, 'res_arcsec': 5.532329689072155, 'expt': 1330.56, 'mjd': 60606.765877, 'soda_id': 'member.uid___A001_X3789_X9a.T_CrB_sci.spw17.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X3789/X9a.source.T_CrB.spw.17'}, {'band': 1, 'canon': 'CIRCINUSGAL', 'alma_target': 'Circinus_galaxy', 'mous': 'uid://A001/X3788/Xae83', 'role': 'CONTROL', 'ra': 213.29145833338953, 'dec': -65.33922222223883, 'sep_prior': 11556.2, 'prior_ref': '', 'freq_ghz': 35.27133898515544, 'um_min': 8443.512749882611, 'um_max': 8556.44800833779, 'rp': 143509.8564, 'res_arcsec': 7.991971645773067, 'expt': 1058.4, 'mjd': 60638.708913, 'soda_id': 'member.uid___A001_X3788_Xae83.Circinus_galaxy_sci.spw25.cube.I.selfcal.pbcor.fits', 'obs_id': 'uid://A001/X3788/Xae83.source.Circinus_galaxy.spw.25'}, {'band': 1, 'canon': 'SPIDERWEBGAL', 'alma_target': 'Spiderweb_Galaxy', 'mous': 'uid://A001/X3621/X1f9d', 'role': 'CONTROL', 'ra': 175.2014199999998, 'dec': -26.485710000012425, 'sep_prior': 16383.87, 'prior_ref': 'HD98800', 'freq_ghz': 35.62506998610929, 'um_min': 8305.965940428136, 'um_max': 8527.366757923946, 'rp': 62283.240845121145, 'res_arcsec': 1.6081383864954637, 'expt': 36469.44, 'mjd': 60522.916003, 'soda_id': 'member.uid___A001_X3621_X1f9d.Spiderweb_Galaxy_sci.spw23.cube.I.selfcal.pbcor.fits', 'obs_id': 'uid://A001/X3621/X1f9d.source.Spiderweb_Galaxy.spw.23'}, {'band': 1, 'canon': 'HDFSMUSE', 'alma_target': 'HDF-S_MUSE_pointing', 'mous': 'uid://A001/X3827/X4be', 'role': 'CONTROL', 'ra': 338.2318333333416, 'dec': -60.56305555556281, 'sep_prior': 2850.56, 'prior_ref': '', 'freq_ghz': 42.12819702501481, 'um_min': 6961.122137264145, 'um_max': 7278.334048704488, 'rp': 36486.46712802768, 'res_arcsec': 0.11769689819767058, 'expt': 64665.216, 'mjd': 60872.347869, 'soda_id': 'member.uid___A001_X3827_X4be.HDF-S_MUSE_pointing_sci.spw31.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X3827/X4be.source.HDF-S_MUSE_pointing.spw.31'}, {'band': 3, 'canon': 'AUMIC', 'alma_target': 'AU_Mic', 'mous': 'uid://A001/X3788/X9d8c', 'role': 'SCIENCE', 'ra': 311.2920721645331, 'dec': -31.34343663436951, 'sep_prior': 12.53, 'prior_ref': '', 'freq_ghz': 114.8766062453021, 'um_min': 2588.578930618153, 'um_max': 2631.150497487807, 'rp': 100940.42883334216, 'res_arcsec': 0.20908549499153828, 'expt': 23064.926, 'mjd': 60812.339463, 'soda_id': 'member.uid___A001_X3788_X9d8c.AU_Mic_sci.spw23.cube.I.selfcal.pbcor.fits', 'obs_id': 'uid://A001/X3788/X9d8c.source.AU_Mic.spw.23'}, {'band': 3, 'canon': 'BETPIC', 'alma_target': 'Beta_Pic', 'mous': 'uid://A001/X158f/X7c3', 'role': 'SCIENCE', 'ra': 86.8212338409578, 'dec': -51.06599102676566, 'sep_prior': 0.52, 'prior_ref': '', 'freq_ghz': 115.27069353041082, 'um_min': 2590.237732178842, 'um_max': 2611.386456408844, 'rp': 235097.4233544688, 'res_arcsec': 0.9579418014405752, 'expt': 11820.781, 'mjd': 59588.136334, 'soda_id': 'member.uid___A001_X158f_X7c3.Beta_Pic_sci.spw19.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X158f/X7c3.source.Beta_Pic.spw.19'}, {'band': 3, 'canon': 'ABAUR', 'alma_target': 'AB_Aur', 'mous': 'uid://A001/X3788/Xb510', 'role': 'SCIENCE', 'ra': 73.94105946900402, 'dec': 30.55102030578353, 'sep_prior': 0.24, 'prior_ref': 'ABAUR', 'freq_ghz': 97.9810898172635, 'um_min': 3058.7834729486067, 'um_max': 3060.6113063141415, 'rp': 1389160.9350630715, 'res_arcsec': 0.166025146248079, 'expt': 5370.59, 'mjd': 60969.264739, 'soda_id': 'member.uid___A001_X3788_Xb510.AB_Aur_sci.spw25.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X3788/Xb510.source.AB_Aur.spw.25'}, {'band': 3, 'canon': 'HD163296', 'alma_target': 'HD163296', 'mous': 'uid://A001/X133d/X19ab', 'role': 'SCIENCE', 'ra': 269.0886502634, 'dec': -21.956436933258033, 'sep_prior': 0.67, 'prior_ref': 'HD163296', 'freq_ghz': 101.33108968200906, 'um_min': 2957.6891317241902, 'um_max': 2959.3987821312103, 'rp': 1435742.2927228233, 'res_arcsec': 0.23367209449948828, 'expt': 12771.655, 'mjd': 58718.134824, 'soda_id': 'member.uid___A001_X133d_X19ab.HD163296_sci.spw39.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X133d/X19ab.source.HD163296.spw.39'}, {'band': 3, 'canon': 'HD36112', 'alma_target': 'HD_36112', 'mous': 'uid://A001/X3788/Xb515', 'role': 'SCIENCE', 'ra': 82.61473005995195, 'dec': 25.33233527406175, 'sep_prior': 0.25, 'prior_ref': 'HD36112', 'freq_ghz': 99.29791805961744, 'um_min': 3018.231540332484, 'um_max': 3020.011555003038, 'rp': 1407647.4908098304, 'res_arcsec': 0.3598311343546147, 'expt': 5025.773, 'mjd': 60803.772191, 'soda_id': 'member.uid___A001_X3788_Xb515.HD_36112_sci.spw27.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X3788/Xb515.source.HD_36112.spw.27'}, {'band': 3, 'canon': 'RDOR', 'alma_target': 'R_Dor', 'mous': 'uid://A001/X1284/X22bf', 'role': 'SCIENCE', 'ra': 69.18921852449108, 'dec': -62.07754919494924, 'sep_prior': 0.27, 'prior_ref': 'RDOR', 'freq_ghz': 94.00294923807125, 'um_min': 3185.214450528997, 'um_max': 3193.1582587638104, 'rp': 388400.99254585744, 'res_arcsec': 0.3456161180134163, 'expt': 5080.266, 'mjd': 58116.050736, 'soda_id': 'member.uid___A001_X1284_X22bf.R_Dor_sci.spw25.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X1284/X22bf.source.R_Dor.spw.25'}, {'band': 3, 'canon': 'TWHYA', 'alma_target': 'TW_Hya', 'mous': 'uid://A001/X1465/X2474', 'role': 'SCIENCE', 'ra': 165.46578054261886, 'dec': -34.70481607683011, 'sep_prior': 735.75, 'prior_ref': '', 'freq_ghz': 109.1760937048154, 'um_min': 2745.2169891675535, 'um_max': 2746.6900647573957, 'rp': 1788211.2444353218, 'res_arcsec': 0.6175856234860336, 'expt': 19473.332, 'mjd': 59295.068512, 'soda_id': 'member.uid___A001_X1465_X2474.TW_Hya_sci.spw33.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X1465/X2474.source.TW_Hya.spw.33'}, {'band': 3, 'canon': 'V4046SGR', 'alma_target': 'V4046_Sgr', 'mous': 'uid://A001/X158f/X56', 'role': 'SCIENCE', 'ra': 273.5436987494966, 'dec': -32.793244301502135, 'sep_prior': 12971.81, 'prior_ref': 'HD165185', 'freq_ghz': 98.51155349277258, 'um_min': 3042.31626592135, 'um_max': 3044.126875031579, 'rp': 1614543.1009972205, 'res_arcsec': 0.25203435082067815, 'expt': 43085.832, 'mjd': 59542.709295, 'soda_id': 'member.uid___A001_X158f_X56.V4046_Sgr_sci.spw23.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X158f/X56.source.V4046_Sgr.spw.23'}, {'band': 3, 'canon': 'HD97048', 'alma_target': 'HD_97048', 'mous': 'uid://A001/X3788/Xb524', 'role': 'SCIENCE', 'ra': 167.0130454083838, 'dec': -77.65484953215673, 'sep_prior': 4410.82, 'prior_ref': '', 'freq_ghz': 97.97331840563734, 'um_min': 3059.0259576208364, 'um_max': 3060.854222700991, 'rp': 1388935.0164956062, 'res_arcsec': 0.2847044637005002, 'expt': 5515.701, 'mjd': 60823.818143, 'soda_id': 'member.uid___A001_X3788_Xb524.HD_97048_sci.spw25.cube.I.selfcal.pbcor.fits', 'obs_id': 'uid://A001/X3788/Xb524.source.HD_97048.spw.25'}, {'band': 3, 'canon': 'HD179218', 'alma_target': 'HD_179218', 'mous': 'uid://A001/X158f/X5b9', 'role': 'SCIENCE', 'ra': 287.79692335486, 'dec': 15.787548946423648, 'sep_prior': 26799.34, 'prior_ref': 'HMSGE', 'freq_ghz': 100.34937038838225, 'um_min': 2959.849162384936, 'um_max': 3015.646219593745, 'rp': 89719.95673958804, 'res_arcsec': 0.11346518547067169, 'expt': 10305.462, 'mjd': 59511.901423, 'soda_id': 'member.uid___A001_X158f_X5b9.HD_179218_sci.spw29.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X158f/X5b9.source.HD_179218.spw.29'}, {'band': 3, 'canon': 'V644SCO', 'alma_target': 'V644_Sco', 'mous': 'uid://A001/X1590/X29fe', 'role': 'SCIENCE', 'ra': 261.57894999999803, 'dec': -40.03110833001386, 'sep_prior': 13758.81, 'prior_ref': 'NGC6302', 'freq_ghz': 101.00786506649526, 'um_min': 2954.3080039102483, 'um_max': 2981.841773805645, 'rp': 179779.18132358257, 'res_arcsec': 0.31826286140025056, 'expt': 10523.52, 'mjd': 59552.598197, 'soda_id': 'member.uid___A001_X1590_X29fe.V644_Sco_sci.spw23.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X1590/X29fe.source.V644_Sco.spw.23'}, {'band': 3, 'canon': 'DRSER', 'alma_target': 'DR_Ser', 'mous': 'uid://A001/X1590/X2a02', 'role': 'SCIENCE', 'ra': 281.83760237791506, 'dec': 5.455182458704054, 'sep_prior': 16058.73, 'prior_ref': 'G34P3', 'freq_ghz': 100.999009047366, 'um_min': 2954.565776708242, 'um_max': 2982.104531506344, 'rp': 179765.45706990475, 'res_arcsec': 0.34263717144915584, 'expt': 8799.83, 'mjd': 59551.838221, 'soda_id': 'member.uid___A001_X1590_X2a02.DR_Ser_sci.spw23.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X1590/X2a02.source.DR_Ser.spw.23'}, {'band': 3, 'canon': 'TMIC', 'alma_target': 'T_Mic', 'mous': 'uid://A001/X1465/X3718', 'role': 'SCIENCE', 'ra': 306.97991594089524, 'dec': -28.260986033610074, 'sep_prior': 10986.37, 'prior_ref': '', 'freq_ghz': 112.19039677894045, 'um_min': 2666.2368834229046, 'um_max': 2678.1411386734317, 'rp': 396606.0058681647, 'res_arcsec': 11.052288081788383, 'expt': 4959.353, 'mjd': 58796.95016, 'soda_id': 'member.uid___A001_X1465_X3718.T_Mic_sci.spw16.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X1465/X3718.source.T_Mic.spw.16'}, {'band': 3, 'canon': 'GY92_274', 'alma_target': 'gy92_274', 'mous': 'uid://A001/X1284/X20fe', 'role': 'SCIENCE', 'ra': 246.8725875000085, 'dec': -24.654597222229928, 'sep_prior': 3387.8, 'prior_ref': '', 'freq_ghz': 93.97908978531471, 'um_min': 3188.0028849429855, 'um_max': 3191.9817538839775, 'rp': 1332953.0043825593, 'res_arcsec': 0.5344602754185641, 'expt': 16148.16, 'mjd': 58143.614385, 'soda_id': 'member.uid___A001_X1284_X20fe.gy92_274_sci.spw25.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X1284/X20fe.source.gy92_274.spw.25'}, {'band': 3, 'canon': 'GOTAU', 'alma_target': 'GO_Tau', 'mous': 'uid://A001/X13d5/X18c', 'role': 'SCIENCE', 'ra': 70.76289583332681, 'dec': 25.338541666671567, 'sep_prior': 11190.58, 'prior_ref': 'LKCA15', 'freq_ghz': 109.7805012704082, 'um_min': 2727.9262853593223, 'um_max': 2733.7503407336408, 'rp': 388579.5263277712, 'res_arcsec': 0.10414299349342881, 'expt': 4862.592, 'mjd': 58682.588383, 'soda_id': 'member.uid___A001_X13d5_X18c.GO_Tau_sci.spw25.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X13d5/X18c.source.GO_Tau.spw.25'}, {'band': 3, 'canon': 'CLOVERLEAF', 'alma_target': 'Cloverleaf', 'mous': 'uid://A001/X1288/X6c2', 'role': 'CONTROL', 'ra': 213.9427083333471, 'dec': 11.495388888893952, 'sep_prior': 13404.96, 'prior_ref': '', 'freq_ghz': 99.696362494516, 'um_min': 2979.0523027135423, 'um_max': 3035.589395238928, 'rp': 101142.6230163721, 'res_arcsec': 0.43684304069678725, 'expt': 26822.88, 'mjd': 58130.396541, 'soda_id': 'member.uid___A001_X1288_X6c2.Cloverleaf_sci.spw22.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X1288/X6c2.source.Cloverleaf.spw.22'}, {'band': 4, 'canon': 'PDS70', 'alma_target': 'PDS_70', 'mous': 'uid://A001/X3577/X8fd', 'role': 'SCIENCE', 'ra': 212.04204893611796, 'dec': -41.39809373798219, 'sep_prior': 2.08, 'prior_ref': '', 'freq_ghz': 151.99086907154845, 'um_min': 1960.348553037894, 'um_max': 1984.67604689974, 'rp': 133794.97923866578, 'res_arcsec': 0.03545354755985155, 'expt': 10305.672, 'mjd': 60134.934603, 'soda_id': 'member.uid___A001_X3577_X8fd.PDS_70_sci.spw23.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X3577/X8fd.source.PDS_70.spw.23'}, {'band': 4, 'canon': 'HD163296', 'alma_target': 'HD_163296', 'mous': 'uid://A001/X133d/X7b8', 'role': 'SCIENCE', 'ra': 269.0886546138804, 'dec': -21.95629182427942, 'sep_prior': 0.15, 'prior_ref': 'HD163296', 'freq_ghz': 131.61543706829832, 'um_min': 2277.2844406271706, 'um_max': 2278.2977845495716, 'rp': 1078582.1201213514, 'res_arcsec': 0.7644754090498814, 'expt': 11961.039, 'mjd': 58574.497707, 'soda_id': 'member.uid___A001_X133d_X7b8.HD_163296_sci.spw25.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X133d/X7b8.source.HD_163296.spw.25'}, {'band': 4, 'canon': 'VYCMA', 'alma_target': 'VY_CMa', 'mous': 'uid://A001/X3621/X4474', 'role': 'SCIENCE', 'ra': 110.74307726686504, 'dec': -25.767609777523827, 'sep_prior': 0.32, 'prior_ref': 'VYCMA', 'freq_ghz': 139.99167957347743, 'um_min': 2127.2698344349697, 'um_max': 2155.9258295005015, 'rp': 62418.30510273705, 'res_arcsec': 0.08013325330473443, 'expt': 5225.471, 'mjd': 60241.313334, 'soda_id': 'member.uid___A001_X3621_X4474.VY_CMa_sci.spw21.cube.I.manual.pbcor.fits', 'obs_id': 'uid://A001/X3621/X4474.source.VY_CMa.spw.22'}, {'band': 4, 'canon': 'CYTAU', 'alma_target': 'CY_Tau', 'mous': 'uid://A001/X2d1f/X2aa', 'role': 'SCIENCE', 'ra': 64.3906040184298, 'dec': 28.346168547113002, 'sep_prior': 11095.21, 'prior_ref': 'DGTAU', 'freq_ghz': 127.10730535636034, 'um_min': 2341.3190279860564, 'um_max': 2376.092733984843, 'rp': 113430.62920994306, 'res_arcsec': 0.04189387004998181, 'expt': 4245.678, 'mjd': 60164.457726, 'soda_id': 'member.uid___A001_X2d1f_X2aa.CY_Tau_sci.spw25.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X2d1f/X2aa.source.CY_Tau.spw.25'}, {'band': 4, 'canon': 'DOAR25', 'alma_target': 'DoAr25', 'mous': 'uid://A001/X2d1f/X2b0', 'role': 'SCIENCE', 'ra': 246.5986545503191, 'dec': -24.72069598378678, 'sep_prior': 4314.42, 'prior_ref': '', 'freq_ghz': 127.11144834979706, 'um_min': 2341.241258724354, 'um_max': 2376.0167904137274, 'rp': 113420.84205734445, 'res_arcsec': 0.033074587971375385, 'expt': 2467.584, 'mjd': 60162.035627, 'soda_id': 'member.uid___A001_X2d1f_X2b0.DoAr25_sci.spw25.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X2d1f/X2b0.source.DoAr25.spw.25'}, {'band': 4, 'canon': 'TPYX', 'alma_target': 'T_Pyx', 'mous': 'uid://A001/X14c3/X46', 'role': 'SCIENCE', 'ra': 136.1729256923345, 'dec': -32.379861096879765, 'sep_prior': 22603.61, 'prior_ref': '', 'freq_ghz': 132.0000234624266, 'um_min': 2254.081168883543, 'um_max': 2288.4886106894082, 'rp': 136184.09095385735, 'res_arcsec': 8.31790444555857, 'expt': 3810.231, 'mjd': 58905.120902, 'soda_id': 'member.uid___A001_X14c3_X46.T_Pyx_sci.spw18.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X14c3/X46.source.T_Pyx.spw.18'}, {'band': 4, 'canon': 'CKVUL', 'alma_target': 'CK_Vul', 'mous': 'uid://A001/X129e/X23a', 'role': 'SCIENCE', 'ra': 296.90862500002044, 'dec': 27.31254444444594, 'sep_prior': 8847.02, 'prior_ref': 'HD339034', 'freq_ghz': 133.02944015358224, 'um_min': 2237.817631249332, 'um_max': 2269.5655695854766, 'rp': 118670.93029165933, 'res_arcsec': 0.23136437939570345, 'expt': 1209.6, 'mjd': 58098.845397, 'soda_id': 'member.uid___A001_X129e_X23a.CK_Vul_sci.spw27.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X129e/X23a.source.CK_Vul.spw.27'}, {'band': 4, 'canon': 'MPMUS', 'alma_target': 'MP_Mus', 'mous': 'uid://A001/X129e/X28b', 'role': 'SCIENCE', 'ra': 200.5308609665521, 'dec': -69.63683730418592, 'sep_prior': 11559.05, 'prior_ref': '', 'freq_ghz': 144.87795155665628, 'um_min': 2055.9754594249716, 'um_max': 2082.7496080797555, 'rp': 147397.58657689687, 'res_arcsec': 0.28018826959738424, 'expt': 1149.12, 'mjd': 58114.474773, 'soda_id': 'member.uid___A001_X129e_X28b.MP_Mus_sci.spw27.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X129e/X28b.source.MP_Mus.spw.27'}, {'band': 4, 'canon': 'HD135344B', 'alma_target': 'HD_135344B', 'mous': 'uid://A001/X12a3/X448', 'role': 'SCIENCE', 'ra': 228.9517069360791, 'dec': -37.154571967798375, 'sep_prior': 18730.48, 'prior_ref': '', 'freq_ghz': 149.9483482249684, 'um_min': 1986.8966041538667, 'um_max': 2011.8690246681003, 'rp': 77844.36071694996, 'res_arcsec': 0.3802960446899904, 'expt': 1391.04, 'mjd': 58135.501904, 'soda_id': 'member.uid___A001_X12a3_X448.HD_135344B_sci.spw29.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X12a3/X448.source.HD_135344B.spw.29'}, {'band': 4, 'canon': 'GXMON', 'alma_target': 'GX_Mon', 'mous': 'uid://A001/X1288/Xda9', 'role': 'SCIENCE', 'ra': 103.19600833331373, 'dec': 8.421983333330353, 'sep_prior': 19081.12, 'prior_ref': '', 'freq_ghz': 157.95475784446216, 'um_min': 1886.777773916443, 'um_max': 1909.2838369135761, 'rp': 81004.54541312139, 'res_arcsec': 0.031382807128207964, 'expt': 4427.136, 'mjd': 58032.419466, 'soda_id': 'member.uid___A001_X1288_Xda9.GX_Mon_sci.spw25.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X1288/Xda9.source.GX_Mon.spw.25'}, {'band': 4, 'canon': 'GWORI', 'alma_target': 'GW_Ori', 'mous': 'uid://A001/X1590/X383', 'role': 'SCIENCE', 'ra': 82.28495833332457, 'dec': 11.87018361111239, 'sep_prior': 11691.12, 'prior_ref': '', 'freq_ghz': 138.0266887031069, 'um_min': 2157.3483120289748, 'um_max': 2186.829885524103, 'rp': 61539.66215025599, 'res_arcsec': 0.4566599204702513, 'expt': 11491.2, 'mjd': 59755.622248, 'soda_id': 'member.uid___A001_X1590_X383.GW_Ori_sci.spw17.cube.IQUV.manual.pbcor.fits', 'obs_id': 'uid://A001/X1590/X383.source.GW_Ori.spw.18'}, {'band': 4, 'canon': 'GHZ2GAL', 'alma_target': 'GHZ2', 'mous': 'uid://A001/X3788/X8cfc', 'role': 'CONTROL', 'ra': 3.498985416642488, 'dec': -30.32475277778756, 'sep_prior': 7263.43, 'prior_ref': 'GJ1009', 'freq_ghz': 144.30275970256085, 'um_min': 2064.1199057217177, 'um_max': 2091.103481447224, 'rp': 128663.12924209083, 'res_arcsec': 0.21966899443003413, 'expt': 29937.6, 'mjd': 60701.721832, 'soda_id': 'member.uid___A001_X3788_X8cfc.GHZ2_sci.spw27.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X3788/X8cfc.source.GHZ2.spw.27'}, {'band': 5, 'canon': 'HD100546', 'alma_target': 'HD_100546', 'mous': 'uid://A001/X3622/X3fa', 'role': 'SCIENCE', 'ra': 173.35521901710027, 'dec': -70.19478889990485, 'sep_prior': 0.34, 'prior_ref': 'HD100546', 'freq_ghz': 171.98250438830547, 'um_min': 1733.7077895675584, 'um_max': 1752.7092077182078, 'rp': 177057.21679626833, 'res_arcsec': 0.22536832928188547, 'expt': 8436.86, 'mjd': 60491.887943, 'soda_id': 'member.uid___A001_X3622_X3fa.HD_100546_sci.spw25.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X3622/X3fa.source.HD_100546.spw.25'}, {'band': 5, 'canon': 'HD163296', 'alma_target': 'HD_163296', 'mous': 'uid://A001/X158f/X4e7', 'role': 'SCIENCE', 'ra': 269.0886476223307, 'dec': -21.95632282364929, 'sep_prior': 0.26, 'prior_ref': 'HD163296', 'freq_ghz': 195.14136725164127, 'um_min': 1535.8227214683034, 'um_max': 1536.7445071464194, 'rp': 1383257.748283629, 'res_arcsec': 0.2775390511991299, 'expt': 6622.5, 'mjd': 59791.022218, 'soda_id': 'member.uid___A001_X158f_X4e7.HD_163296_sci.spw27.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X158f/X4e7.source.HD_163296.spw.27'}, {'band': 5, 'canon': 'HD141569', 'alma_target': 'HD_141569', 'mous': 'uid://A001/X1284/X478', 'role': 'SCIENCE', 'ra': 237.490519609167, 'dec': -3.9213044916369886, 'sep_prior': 3.33, 'prior_ref': '', 'freq_ghz': 177.1956629565916, 'um_min': 1689.6398460635198, 'um_max': 1694.1109345022944, 'rp': 314332.5518642185, 'res_arcsec': 1.4035790608951055, 'expt': 1481.76, 'mjd': 58303.07164, 'soda_id': 'member.uid___A001_X1284_X478.HD_141569_sci.spw29.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X1284/X478.source.HD_141569.spw.29'}, {'band': 5, 'canon': 'MWC480', 'alma_target': 'MWC_480', 'mous': 'uid://A001/X158f/X4ea', 'role': 'SCIENCE', 'ra': 74.69280863302018, 'dec': 29.843449523838725, 'sep_prior': 3458.45, 'prior_ref': 'ABAUR', 'freq_ghz': 209.23024525490425, 'um_min': 1432.4344133822108, 'um_max': 1433.2361889022739, 'rp': 1482372.8022336906, 'res_arcsec': 0.27537606008580645, 'expt': 9796.299, 'mjd': 59765.629312, 'soda_id': 'member.uid___A001_X158f_X4ea.MWC_480_sci.spw33.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X158f/X4ea.source.MWC_480.spw.33'}, {'band': 5, 'canon': 'HD101584', 'alma_target': 'HD101584', 'mous': 'uid://A001/X2d20/X5e6', 'role': 'SCIENCE', 'ra': 175.24493013197235, 'dec': -55.57383933740885, 'sep_prior': 14272.44, 'prior_ref': 'GJ422', 'freq_ghz': 163.8770411801828, 'um_min': 1824.1589951272763, 'um_max': 1834.619640627578, 'rp': 291142.7489277409, 'res_arcsec': 0.18624371375272475, 'expt': 9676.78, 'mjd': 60076.946384, 'soda_id': 'member.uid___A001_X2d20_X5e6.HD101584_sci.spw25.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X2d20/X5e6.source.HD101584.spw.25'}, {'band': 5, 'canon': 'WLY248', 'alma_target': 'WLY_2-48', 'mous': 'uid://A001/X3788/X729e', 'role': 'SCIENCE', 'ra': 246.90489573426544, 'dec': -24.50990068826952, 'sep_prior': 3205.17, 'prior_ref': '', 'freq_ghz': 168.75435521981353, 'um_min': 1776.1940494390942, 'um_max': 1776.810157463051, 'rp': 2392461.3826392824, 'res_arcsec': 0.35813833777912113, 'expt': 2056.32, 'mjd': 60763.417104, 'soda_id': 'member.uid___A001_X3788_X729e.WLY_2-48_sci.spw27.cube.I.selfcal.pbcor.fits', 'obs_id': 'uid://A001/X3788/X729e.source.WLY_2-48.spw.27'}, {'band': 5, 'canon': 'HD121617', 'alma_target': 'HD_121617', 'mous': 'uid://A001/X1284/X470', 'role': 'SCIENCE', 'ra': 209.42114116560606, 'dec': -47.00960895125361, 'sep_prior': 19553.4, 'prior_ref': '', 'freq_ghz': 178.19650794769075, 'um_min': 1680.1622505304492, 'um_max': 1684.583547003981, 'rp': 316084.85685633525, 'res_arcsec': 1.0240852816666883, 'expt': 2812.32, 'mjd': 58348.943732, 'soda_id': 'member.uid___A001_X1284_X470.HD_121617_sci.spw27.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X1284/X470.source.HD_121617.spw.27'}, {'band': 5, 'canon': 'HD131488', 'alma_target': 'HD_131488', 'mous': 'uid://A001/X1284/X460', 'role': 'SCIENCE', 'ra': 223.78331053391227, 'dec': -41.120506815499056, 'sep_prior': 10944.04, 'prior_ref': '', 'freq_ghz': 178.19561371327845, 'um_min': 1680.1706813024857, 'um_max': 1684.5920014521548, 'rp': 316090.37199115905, 'res_arcsec': 1.3715105627766637, 'expt': 2116.741, 'mjd': 58308.135124, 'soda_id': 'member.uid___A001_X1284_X460.HD_131488_sci.spw27.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X1284/X460.source.HD_131488.spw.27'}, {'band': 5, 'canon': 'HD131835', 'alma_target': 'HD_131835', 'mous': 'uid://A001/X1284/X460', 'role': 'SCIENCE', 'ra': 224.22680213114802, 'dec': -35.6955882402758, 'sep_prior': 26618.79, 'prior_ref': '', 'freq_ghz': 174.95539056982832, 'um_min': 1708.9598604786167, 'um_max': 1718.1378374413305, 'rp': 310765.8553900412, 'res_arcsec': 1.3528458752632795, 'expt': 2056.25, 'mjd': 58308.137707, 'soda_id': 'member.uid___A001_X1284_X460.HD_131835_sci.spw25.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X1284/X460.source.HD_131835.spw.25'}, {'band': 5, 'canon': 'HD21997', 'alma_target': 'HD_21997', 'mous': 'uid://A001/X133d/X30af', 'role': 'SCIENCE', 'ra': 52.97384451934573, 'dec': -25.614227623886595, 'sep_prior': 15020.45, 'prior_ref': 'HD20782', 'freq_ghz': 174.9596016944647, 'um_min': 1708.9186981324294, 'um_max': 1718.0965128566495, 'rp': 310760.2132696975, 'res_arcsec': 1.525626128190561, 'expt': 2026.08, 'mjd': 58562.923579, 'soda_id': 'member.uid___A001_X133d_X30af.HD_21997_sci.spw25.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X133d/X30af.source.HD_21997.spw.25'}, {'band': 5, 'canon': 'HD100453', 'alma_target': 'HD_100453', 'mous': 'uid://A001/X133d/X30d3', 'role': 'SCIENCE', 'ra': 173.27290672436536, 'dec': -54.32462747272777, 'sep_prior': 14445.12, 'prior_ref': 'GJ422', 'freq_ghz': 174.95570804180613, 'um_min': 1708.957194298583, 'um_max': 1718.1342801785004, 'rp': 310791.7255466671, 'res_arcsec': 0.6025124664992081, 'expt': 1602.72, 'mjd': 58458.38057, 'soda_id': 'member.uid___A001_X133d_X30d3.HD_100453_sci.spw25.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X133d/X30d3.source.HD_100453.spw.25'}, {'band': 5, 'canon': 'HD139614', 'alma_target': 'HD_139614', 'mous': 'uid://A001/X1284/X488', 'role': 'SCIENCE', 'ra': 235.19312601801138, 'dec': -42.498339340099164, 'sep_prior': 7236.19, 'prior_ref': '', 'freq_ghz': 174.95558734217948, 'um_min': 1708.9579250404586, 'um_max': 1718.1359185706094, 'rp': 310761.2863887133, 'res_arcsec': 1.0470142714224369, 'expt': 1481.76, 'mjd': 58354.036128, 'soda_id': 'member.uid___A001_X1284_X488.HD_139614_sci.spw25.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X1284/X488.source.HD_139614.spw.25'}, {'band': 5, 'canon': 'HD145718', 'alma_target': 'HD_145718', 'mous': 'uid://A001/X1284/X480', 'role': 'SCIENCE', 'ra': 243.29825416388934, 'dec': -22.48532001518039, 'sep_prior': 11662.47, 'prior_ref': '', 'freq_ghz': 178.19292571372972, 'um_min': 1680.1961231816028, 'um_max': 1684.6173157383296, 'rp': 316098.6224988704, 'res_arcsec': 1.3661795108445445, 'expt': 1421.28, 'mjd': 58303.108049, 'soda_id': 'member.uid___A001_X1284_X480.HD_145718_sci.spw27.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X1284/X480.source.HD_145718.spw.27'}, {'band': 5, 'canon': 'SZ65J1608', 'alma_target': '2MASS_J16085324-3914401', 'mous': 'uid://A001/X2d1f/X5dc', 'role': 'SCIENCE', 'ra': 242.2217538169362, 'dec': -39.24464419621644, 'sep_prior': 547.72, 'prior_ref': 'HD144668', 'freq_ghz': 209.9741399661452, 'um_min': 1421.3877014918617, 'um_max': 1434.1875766282665, 'rp': 185172.14186842355, 'res_arcsec': 0.12921410865321067, 'expt': 1088.472, 'mjd': 60078.227246, 'soda_id': 'member.uid___A001_X2d1f_X5dc.2MASS_J16085324-3914401_sci.spw23.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X2d1f/X5dc.source.2MASS_J16085324-3914401.spw.23'}, {'band': 5, 'canon': 'NGC3256GAL', 'alma_target': 'ngc_3256', 'mous': 'uid://A001/X1273/Xb55', 'role': 'CONTROL', 'ra': 156.9634583333403, 'dec': -43.90461111112062, 'sep_prior': 14307.66, 'prior_ref': '', 'freq_ghz': 165.4691172367054, 'um_min': 1800.8981246657474, 'um_max': 1822.7797547280363, 'rp': 85870.36556179522, 'res_arcsec': 7.009892554600654, 'expt': 28455.84, 'mjd': 58259.008702, 'soda_id': 'member.uid___A001_X1273_Xb55.ngc_3256_sci.spw20.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X1273/Xb55.source.ngc_3256.spw.20'}, {'band': 5, 'canon': 'PKS0023GAL', 'alma_target': 'PKS0023-26', 'mous': 'uid://A001/X133d/X3f5a', 'role': 'CONTROL', 'ra': 6.454817916640013, 'dec': -26.036838055572044, 'sep_prior': 15135.37, 'prior_ref': '', 'freq_ghz': 174.43935043295468, 'um_min': 1709.423062081855, 'um_max': 1727.887479002259, 'rp': 153685.44138046363, 'res_arcsec': 0.18496106205564258, 'expt': 10644.48, 'mjd': 58753.096451, 'soda_id': 'member.uid___A001_X133d_X3f5a.PKS0023-26_sci.spw22.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X133d/X3f5a.source.PKS0023-26.spw.22'}, {'band': 5, 'canon': '3C218GAL', 'alma_target': '3c218', 'mous': 'uid://A001/X133d/X318f', 'role': 'CONTROL', 'ra': 139.52354583335207, 'dec': -12.0955527777837, 'sep_prior': 26877.96, 'prior_ref': '', 'freq_ghz': 208.65075367535482, 'um_min': 1430.38518881, 'um_max': 1443.3021563297555, 'rp': 212706.17956332298, 'res_arcsec': 0.5070743339341458, 'expt': 12852.0, 'mjd': 58464.30606, 'soda_id': 'member.uid___A001_X133d_X318f.3c218_sci.spw25.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X133d/X318f.source.3c218.spw.25'}, {'band': 4, 'canon': 'IRC10216', 'alma_target': 'irc+10216', 'mous': 'uid://A001/X888/X42', 'role': 'SCIENCE', 'ra': 146.98952568673928, 'dec': 13.280326313606793, 'sep_prior': 5.69, 'prior_ref': 'IRC10216', 'freq_ghz': 143.95425936303315, 'um_min': 2068.189011768376, 'um_max': 2097.119078776363, 'rp': 296879.930445061, 'res_arcsec': 8.42691060879384, 'expt': 936.864, 'mjd': 57663.628375, 'soda_id': 'member.uid___A001_X888_X42.ircp10216_sci.spw16.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X888/X42.source.irc+10216.spw.16'}, {'band': 4, 'canon': 'Q0152GAL', 'alma_target': 'Q0152+0023_z0.4814_CO_2-1', 'mous': 'uid://A001/X2d1f/X4df', 'role': 'CONTROL', 'ra': 28.211666666646057, 'dec': 0.38640555555567824, 'sep_prior': 10083.03, 'prior_ref': '', 'freq_ghz': 155.6258249041747, 'um_min': 1913.8338333039771, 'um_max': 1939.0654605686, 'rp': 39612.57410644251, 'res_arcsec': 7.076942023436512, 'expt': 77414.399, 'mjd': 60041.740305, 'soda_id': 'member.uid___A001_X2d1f_X4df._Q0152p0023_z0.4814_CO_2-1__sci.spw18.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X2d1f/X4df.source.Q0152+0023_z0.4814_CO_2-1.spw.18'}, {'band': 5, 'canon': 'OH231P8', 'alma_target': 'OH231.8+4.2', 'mous': 'uid://A001/X2d20/X5e2', 'role': 'SCIENCE', 'ra': 115.57061300001021, 'dec': -14.713944000002357, 'sep_prior': 1.15, 'prior_ref': 'OH231P8', 'freq_ghz': 165.18072849933972, 'um_min': 1809.8020867765701, 'um_max': 1820.0992124800823, 'rp': 293430.0656507803, 'res_arcsec': 0.1500858993167643, 'expt': 14061.6, 'mjd': 60076.880859, 'soda_id': 'member.uid___A001_X2d20_X5e2._OH231.8p4.2__sci.spw27.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X2d20/X5e2.source.OH231.8+4.2.spw.27'}, {'band': 3, 'canon': 'M83GAL', 'alma_target': 'M83', 'mous': 'uid://A001/X1590/Xd6b', 'role': 'CONTROL', 'ra': 204.22126479520244, 'dec': -29.878048338783664, 'sep_prior': 6769.01, 'prior_ref': 'NGC5253', 'freq_ghz': 104.75147445297172, 'um_min': 2834.874993958255, 'um_max': 2889.5272269731795, 'rp': 91911.90895495964, 'res_arcsec': 7.506706403181707, 'expt': 34472.482, 'mjd': 59492.776215, 'soda_id': 'member.uid___A001_X1590_Xd6b.M83_sci.spw22.cube.I.pbcor.fits', 'obs_id': 'uid://A001/X1590/Xd6b.source.M83.spw.22'}, {'band': 3, 'canon': 'NGC4038GAL', 'alma_target': 'ngc4038', 'mous': 'uid://A001/X3620/X9b', 'role': 'CONTROL', 'ra': 180.4765079166617, 'dec': -18.88453000000804, 'sep_prior': 5781.87, 'prior_ref': '', 'freq_ghz': 112.76679783069207, 'um_min': 2636.6189731273867, 'um_max': 2680.781975521862, 'rp': 57693.544864629424, 'res_arcsec': 0.06090183923661916, 'expt': 60452.366, 'mjd': 60192.638581, 'soda_id': 'member.uid___A001_X3620_X9b.ngc4038_North_sci.spw25.cube.I.manual.pbcor.fits', 'obs_id': 'uid://A001/X3620/X9b.source.ngc4038.spw.25'}]

ESO_39_SPECS: list[tuple[str, str, float, str, str, float, float]] = [('HIP56998', 'ESO_ESPRESSO', 140000.0, 'ADP.2024-03-08T10:58:16.389', 'ESPRESSO_377_790NM', 60360.227187, 1800.0), ('HIP56998', 'ESO_ESPRESSO', 140000.0, 'ADP.2024-04-09T10:09:00.557', 'ESPRESSO_377_790NM', 60399.998339, 1800.0), ('HIP56998', 'ESO_ESPRESSO', 140000.0, 'ADP.2025-06-04T11:44:43.529', 'ESPRESSO_377_790NM', 60806.078266, 1200.0), ('HIP56998', 'ESO_ESPRESSO', 140000.0, 'ADP.2025-06-05T06:35:34.145', 'ESPRESSO_377_790NM', 60821.162993, 1200.0), ('HIP56998', 'ESO_ESPRESSO', 140000.0, 'ADP.2025-06-25T08:13:22.642', 'ESPRESSO_377_790NM', 60849.105634, 1200.0), ('HIP56998', 'ESO_ESPRESSO', 140000.0, 'ADP.2025-07-31T08:46:28.594', 'ESPRESSO_377_790NM', 60882.015476, 1200.0), ('HD140901', 'ESO_HARPS', 115000.0, 'ADP.2014-10-01T10:21:20.073', 'HARPS_378_691NM', 53050.392754, 89.198), ('HD140901', 'ESO_HARPS', 115000.0, 'ADP.2014-09-17T11:21:05.933', 'HARPS_378_691NM', 54234.232263, 199.998), ('HD140901', 'ESO_HARPS', 115000.0, 'ADP.2014-09-17T11:21:40.503', 'HARPS_378_691NM', 54259.141811, 119.999), ('HD140901', 'ESO_HARPS', 115000.0, 'ADP.2014-09-17T11:20:36.220', 'HARPS_378_691NM', 54296.151303, 419.999), ('HD140901', 'ESO_HARPS', 115000.0, 'ADP.2014-09-17T11:20:48.307', 'HARPS_378_691NM', 54342.991341, 150.001), ('HD140901', 'ESO_HARPS', 115000.0, 'ADP.2025-10-02T01:06:32.991', 'HARPS_378_691NM', 60941.007106, 299.996), ('GJ3222', 'ESO_HARPS', 115000.0, 'ADP.2014-10-06T10:06:38.140', 'HARPS_378_691NM', 56568.347913, 179.999), ('GJ3222', 'ESO_HARPS', 115000.0, 'ADP.2014-10-06T10:06:38.853', 'HARPS_378_691NM', 56584.197084, 300.001), ('GJ3222', 'ESO_HARPS', 115000.0, 'ADP.2014-10-06T10:07:41.143', 'HARPS_378_691NM', 56600.21947, 300.0), ('GJ3222', 'ESO_HARPS', 115000.0, 'ADP.2014-10-07T08:35:31.093', 'HARPS_378_691NM', 56697.018073, 300.001), ('GJ3222', 'ESO_HARPS', 115000.0, 'ADP.2014-11-27T19:01:17.747', 'HARPS_378_691NM', 56988.178851, 200.001), ('GJ3222', 'ESO_HARPS', 115000.0, 'ADP.2017-10-10T01:14:12.981', 'HARPS_378_691NM', 58035.149118, 442.318), ('GJ676A', 'ESO_HARPS', 115000.0, 'ADP.2014-09-16T11:06:04.847', 'HARPS_378_691NM', 53917.24041, 446.902), ('GJ676A', 'ESO_HARPS', 115000.0, 'ADP.2014-09-18T12:10:34.940', 'HARPS_378_691NM', 54658.189534, 900.0), ('GJ676A', 'ESO_HARPS', 115000.0, 'ADP.2014-09-23T11:03:31.873', 'HARPS_378_691NM', 54921.38988, 296.3), ('GJ676A', 'ESO_HARPS', 115000.0, 'ADP.2014-09-23T11:04:07.057', 'HARPS_378_691NM', 55112.994609, 899.999), ('GJ676A', 'ESO_HARPS', 115000.0, 'ADP.2014-09-24T09:44:39.187', 'HARPS_378_691NM', 55340.198743, 900.005), ('GJ676A', 'ESO_HARPS', 115000.0, 'ADP.2014-09-25T15:34:15.737', 'HARPS_378_691NM', 55662.414753, 900.004), ('HR810', 'ESO_HARPS', 115000.0, 'ADP.2014-09-29T13:27:22.250', 'HARPS_378_691NM', 52949.188227, 39.996), ('HR810', 'ESO_HARPS', 115000.0, 'ADP.2014-10-01T10:19:40.923', 'HARPS_378_691NM', 53287.265584, 59.982), ('HR810', 'ESO_HARPS', 115000.0, 'ADP.2014-10-01T10:21:56.103', 'HARPS_378_691NM', 53309.255857, 100.002), ('HR810', 'ESO_HARPS', 115000.0, 'ADP.2014-10-02T10:01:02.190', 'HARPS_378_691NM', 53600.418448, 100.0), ('HR810', 'ESO_HARPS', 115000.0, 'ADP.2014-09-16T11:04:00.057', 'HARPS_378_691NM', 53930.431466, 120.0), ('HR810', 'ESO_HARPS', 115000.0, 'ADP.2014-09-16T11:05:44.353', 'HARPS_378_691NM', 53973.35038, 119.999), ('GL479', 'ESO_HARPS', 115000.0, 'ADP.2014-10-01T10:23:39.810', 'HARPS_378_691NM', 53158.036509, 899.995), ('GL479', 'ESO_HARPS', 115000.0, 'ADP.2014-09-16T11:03:48.083', 'HARPS_378_691NM', 53883.102111, 1199.999), ('GL479', 'ESO_HARPS', 115000.0, 'ADP.2014-09-17T11:23:34.197', 'HARPS_378_691NM', 54173.284318, 899.995), ('GL479', 'ESO_HARPS', 115000.0, 'ADP.2014-09-18T12:15:02.100', 'HARPS_378_691NM', 54480.289512, 900.0), ('GL479', 'ESO_HARPS', 115000.0, 'ADP.2014-09-18T12:10:38.070', 'HARPS_378_691NM', 54527.355431, 900.0), ('GL479', 'ESO_HARPS', 115000.0, 'ADP.2014-09-18T12:12:51.853', 'HARPS_378_691NM', 54571.188966, 900.0), ('HIP31293', 'ESO_HARPS', 115000.0, 'ADP.2014-09-16T11:05:36.077', 'HARPS_378_691NM', 53785.078992, 900.0), ('GL358', 'ESO_HARPS', 115000.0, 'ADP.2014-09-16T11:07:31.237', 'HARPS_378_691NM', 53866.990316, 900.0), ('GL569A', 'ESO_HARPS', 115000.0, 'ADP.2014-09-16T11:04:22.300', 'HARPS_378_691NM', 53813.306649, 900.0)]

# Archive T-Z metadata (D094-D100)
PRIOR_ARCHIVES_TZ: list[tuple[str, str, str, str, str]] = [
    ("Z", "SETI_D100_V5_8_JCMT_3MM_SOFIA_FIFILS_IUE_ECCENTRIC_KEPLERIAN_RESULTS_2026-11-22.zip",
     "f8900c1aee6db352b6317c1dd6bf308d286bab2c0c0b367e8863383438446bd2",
     "work_v5_8_20261122_d100_jcmt_3mm_sofia_fifils_iue_eccentric_keplerian/bounded_inputs/d100_bounded_bundle.json.gz",
     "4923b95a95da48ce036e1adbfa0402f0023afa23db32e874c3079083077b036d"),
    ("Y", "SETI_D099_V5_7_JCMT_MM_SOFIA_EXES_IRTF_SPEX_KEPLERIAN_DRIFT_RESULTS_2026-11-22.zip",
     "77b187f3509a704978096c14b97f83a13d3eebb6b2fc9d53a8c3b296b362df0b",
     "work_v5_7_20261122_d099_jcmt_mm_sofia_exes_irtf_spex_keplerian_drift/bounded_inputs/d099_bounded_bundle.json.gz",
     "abbc808357061ae63a084b2e11b4f61771845d85117f4e712fd4316a8b87c8b4"),
    ("X", "SETI_D098_V5_6_SOFIA_GREAT_ISO_SWS_FORCAST_OPTICAL_JERK_RESULTS_2026-11-22.zip",
     "f57f48355df2b92257f39d76e83f2d850ae6d9164ea10ef1539bede1ca8fb838",
     "work_v5_6_20261122_d098_sofia_great_iso_sws_forcast_optical_jerk/bounded_inputs/d098_bounded_bundle.json.gz",
     "468c3416778f37f335e990147dc3fecd41ae3281f64b6bbf9873dbe9b3396938"),
    ("W", "SETI_D097_V5_5_HERSCHEL_THZ_FARIR_STIS_E140H_OPTICAL_JERK_RESULTS_2026-11-22.zip",
     "aa296f9c72faefcacbd4f4fedb73c7c3f2b1377823fad3e308fd6a9844f6fed8",
     "work_v5_5_20261122_d097_herschel_thz_farir_stis_e140h_optical_jerk/bounded_inputs/d097_bounded_bundle.json.gz",
     "05b9d096a76082f9b2bca30ab73a01329a20c1b40c651ce2a76bf0647626f41a"),
    ("V", "SETI_D096_V5_4_SOFIA_EXES_MIDIR_ECHELLE_COHERENT_DRIFT_JWST_RESULTS_2026-11-21.zip",
     "a134e4d5d0b6e0cb4e17763dc729203218cac9265c7db75db719135cb01c5158",
     "work_v5_4_20261121_d096_sofia_exes_midir_echelle_coherent_drift_jwst/bounded_inputs/d096_bounded_bundle.json.gz",
     "319f4cd7b6fe1bcc24f5bb74fc6a432019c0ed30a55d04f075b1c78fc9057e91"),
    ("U", "SETI_D095_V5_3_CURVED_PERIODIC_DRIFT_GHOST_SPITZER_IRS_APOGEE2_RESULTS_2026-11-21.zip",
     "24f5a73a4299d697a198e91e3e15b5b7ddce838f6d055cebe66ddd812520c21d",
     "bounded_inputs/d095_bounded_bundle.json.gz",
     "db0ab9adc9f3067909af2cefafb9e0b56095d87107a9510a6cce0a9406ca59b8"),
    ("T", "SETI_D094_V5_2_MULTIEPOCH_DRIFT_APOGEE2_CRIRESJH_MIRILRS_RESULTS_2026-11-21.zip",
     "fea863077ae837b6741d5837990fd357158e00f6a5e3d9adde51f0c81e8ccefc",
     "bounded_inputs/d094_bounded_bundle.json.gz",
     "d6601113eec302bfb393874ffb48d32aa90d073f4bae7b6b37e256ad0cb89c42"),
]

ORBITAL_SPECS: dict[str, dict[str, Any]] = {
    "HIP56998": {
        "campaign_index": 151, "instrument": "ESO_ESPRESSO", "role": "SCIENCE", "null_orbital": False,
        "planet_name": "HD 101581 b / c", "n_planets_in_system": 2, "stellar_mass_msun": 0.653,
        "orb_per_days": 4.46569, "orb_periods_days": [4.46569, 6.20401], "orb_t0_bjd": 2460014.8496,
        "orb_ecc": 0.0, "orb_omega_deg": 90.0, "a_au": 0.046, "kp_kms": 94.3,
    },
    "HD140901": {
        "campaign_index": 152, "instrument": "ESO_HARPS", "role": "SCIENCE", "null_orbital": False,
        "planet_name": "HD 140901 c / b", "n_planets_in_system": 2, "stellar_mass_msun": 1.06,
        "orb_per_days": 14386.0, "orb_periods_days": [14386.0, 9.02378], "orb_t0_bjd": 2453050.0,
        "orb_ecc": 0.77, "orb_omega_deg": 299.0, "a_au": 11.8, "kp_kms": 8.95,
    },
    "GJ3222": {
        "campaign_index": 153, "instrument": "ESO_HARPS", "role": "SCIENCE", "null_orbital": False,
        "planet_name": "GJ 3222 b", "n_planets_in_system": 1, "stellar_mass_msun": 0.89,
        "orb_per_days": 10.66669, "orb_periods_days": [10.66669], "orb_t0_bjd": 2456568.0,
        "orb_ecc": 0.929, "orb_omega_deg": 290.895, "a_au": 0.091, "kp_kms": 91.5,
    },
    "GJ676A": {
        "campaign_index": 154, "instrument": "ESO_HARPS", "role": "SCIENCE", "null_orbital": False,
        "planet_name": "GJ 676 A b / c / d / e", "n_planets_in_system": 4, "stellar_mass_msun": 0.626,
        "orb_per_days": 1051.44521, "orb_periods_days": [1051.44521, 35.47358, 3.60076, 13921.42302],
        "orb_t0_bjd": 2453917.0, "orb_ecc": 0.319, "orb_omega_deg": 87.073, "a_au": 1.735, "kp_kms": 17.9,
    },
    "HR810": {
        "campaign_index": 155, "instrument": "ESO_HARPS", "role": "SCIENCE", "null_orbital": False,
        "planet_name": "HR 810 b", "n_planets_in_system": 1, "stellar_mass_msun": 1.34,
        "orb_per_days": 302.79999, "orb_periods_days": [302.79999], "orb_t0_bjd": 2451908.6,
        "orb_ecc": 0.14, "orb_omega_deg": 309.0, "a_au": 0.92, "kp_kms": 35.9,
    },
    "GL479": {
        "campaign_index": 156, "instrument": "ESO_HARPS", "role": "CONTROL", "null_orbital": True,
        "planet_name": "CONTROL_NULL_SUB10PC", "n_planets_in_system": 0, "stellar_mass_msun": 0.43,
        "orb_per_days": 11.3, "orb_periods_days": [], "orb_t0_bjd": 2453158.0,
        "orb_ecc": 0.0, "orb_omega_deg": 0.0, "a_au": 0.075, "kp_kms": 60.2,
    },
}

FROZEN_HEADER = [
    "instrument", "canonical_target", "common_name", "role", "subrole", "science_track",
    "panchromatic_bridge", "is_prior_bridge", "gaia_source_id", "s_ra", "s_dec",
    "pmra_mas_yr", "pmdec_mas_yr", "dist_pc", "within_10pc", "phot_g_mag",
    "phot_bp_mag", "phot_rp_mag", "j_mag", "h_mag", "ks_mag", "teff_k",
    "mh_dex", "stellar_mass_msun", "prior_rv_kms", "n_exoplanets", "has_transiting_planet",
    "ecliptic_lat_deg", "sn1987a_dt_days", "gw170817_dt_days", "sn2023ixf_dt_days",
    "ppo_align_score", "epoch_rank", "dp_id", "grating", "resolving_power",
    "mjd_obs", "t_exptime", "phase_window", "signed_phase", "planet_orbital_rv_kms",
    "f1_id", "f1_rel", "f1_url", "f1_bytes", "total_bytes",
]


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _ang_sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    cs = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cs)))) * 3600.0


def _ecliptic_lat_deg(ra_deg: float, dec_deg: float) -> float:
    eps = math.radians(23.4392911)
    ra_r, dec_r = math.radians(ra_deg), math.radians(dec_deg)
    sin_b = math.sin(dec_r) * math.cos(eps) - math.cos(dec_r) * math.sin(eps) * math.sin(ra_r)
    return round(math.degrees(math.asin(max(-1.0, min(1.0, sin_b)))), 5)


def _ellipsoid_dt_days(ra_deg: float, dec_deg: float, dist_pc: float, mjd_obs: float, ra_e: float, dec_e: float, mjd_e: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra_deg, dec_deg, ra_e, dec_e))
    theta = math.acos(max(-1.0, min(1.0, math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2))))
    d_days = dist_pc * 3.261563777 * 365.25
    t_arr = mjd_obs - d_days * (1.0 - math.cos(theta)) - mjd_e
    return round(t_arr, 3)


def _kepler_rv(t_rel: float, period_days: float, ecc: float, omega_deg: float, m0: float, k_kms: float) -> tuple[float, float]:
    e_v = max(0.0, min(0.95, ecc))
    w_r = math.radians(omega_deg)
    mean_a = (2.0 * math.pi * t_rel / period_days + m0) % (2.0 * math.pi)
    e_anom = mean_a
    for _ in range(12):
        f = e_anom - e_v * math.sin(e_anom) - mean_a
        fp = 1.0 - e_v * math.cos(e_anom)
        e_anom -= f / max(1e-10, fp)
    nu = 2.0 * math.atan2(math.sqrt(1.0 + e_v) * math.sin(0.5 * e_anom), math.sqrt(1.0 - e_v) * math.cos(0.5 * e_anom))
    rv = k_kms * (math.cos(nu + w_r) + e_v * math.cos(w_r))
    s_phase = ((t_rel / period_days) % 1.0) - 0.5
    return round(rv, 4), round(s_phase, 6)


def _read_d100_sources(archives_dir: Path | None) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Read D100 summary, prior_exclusion, prior_snapshot, and unified 560 from WS_D100 or Archive Z."""
    z_name = PRIOR_ARCHIVES_TZ[0][1]
    z_path = (archives_dir / z_name) if archives_dir else (ROOT / "archives" / z_name)
    if WS_D100.exists() and (WS_D100 / "results/SUMMARY.json").exists():
        summ100 = json.loads((WS_D100 / "results/SUMMARY.json").read_text())
        pex100 = json.loads((WS_D100 / "PRIOR_EXCLUSION_VERIFICATION.json").read_text())
        with (WS_D100 / "results/UNIFIED_PANCHROMATIC_V5_8_SYNTHESIS_560STARS.csv").open() as f:
            u560 = list(csv.DictReader(f))
        with (WS_D100 / "results/PANCHROMATIC_BRIDGE_74STARS_V58.csv").open() as f:
            br74 = list(csv.DictReader(f))
        with (WS_D100 / "results/ALLSKY_COMB_V4_1_UNIFIED_D079_D100.csv").open() as f:
            ac_u = list(csv.DictReader(f))
        with (WS_D100 / "results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D100.csv").open() as f:
            ac_c = list(csv.DictReader(f))
        with (WS_D100 / "results/MULTIEVENT_ELLIPSOID_560STARS.csv").open() as f:
            ell560 = list(csv.DictReader(f))
        with (WS_D100 / "FROZEN_COHORT_D100.csv").open() as f:
            fc100 = list(csv.DictReader(f))
    elif z_path.exists():
        with zipfile.ZipFile(z_path) as zf:
            def _ztxt(suffix: str) -> str:
                m = next(n for n in zf.namelist() if n.endswith(suffix))
                return zf.read(m).decode("utf-8")
            summ100 = json.loads(_ztxt("/results/SUMMARY.json"))
            pex100 = json.loads(_ztxt("/PRIOR_EXCLUSION_VERIFICATION.json"))
            u560 = list(csv.DictReader(_ztxt("/results/UNIFIED_PANCHROMATIC_V5_8_SYNTHESIS_560STARS.csv").splitlines()))
            br74 = list(csv.DictReader(_ztxt("/results/PANCHROMATIC_BRIDGE_74STARS_V58.csv").splitlines()))
            ac_u = list(csv.DictReader(_ztxt("/results/ALLSKY_COMB_V4_1_UNIFIED_D079_D100.csv").splitlines()))
            ac_c = list(csv.DictReader(_ztxt("/results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D100.csv").splitlines()))
            ell560 = list(csv.DictReader(_ztxt("/results/MULTIEVENT_ELLIPSOID_560STARS.csv").splitlines()))
            fc100 = list(csv.DictReader(_ztxt("/FROZEN_COHORT_D100.csv").splitlines()))
    else:
        raise FileNotFoundError(f"Neither WS_D100 nor Archive Z found for Stage-1 snapshot build.")

    snap_extras = {
        "u560": u560, "br74": br74, "ac_u": ac_u, "ac_c": ac_c, "ell560": ell560, "fc100": fc100,
    }
    u560_map = {r["star"]: r for r in u560}
    return summ100, pex100, snap_extras, u560_map


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archives-dir", default="", help="Optional archives dir for clean-room builds")
    args = ap.parse_args()
    archives_dir = Path(args.archives_dir) if args.archives_dir else None

    raw_dir = ROOT / "inputs_d101_v5_9"
    if raw_dir.exists() and not (WS / "LOCK_RECEIPT.json").exists():
        raise RuntimeError(f"CRITICAL REFUSAL: raw input directory {raw_dir} already exists before Stage-1 seal!")

    summ100, pex100, sx, u560_map = _read_d100_sources(archives_dir)
    uni100 = summ100["unified_560star_panchromatic_v5_8_synthesis"]

    # Build cumulative prior coordinates (588 + 44 D100 = 632) & dp_ids (3080 + 79 D100 = 3159)
    prior_coords = list(pex100["excluded_targets_coordinate_registry"])
    seen_d100 = set()
    d100_dps = []
    for r in sx["fc100"]:
        d100_dps.append(r["dp_id"])
        if r["is_prior_bridge"] == "False" and r["canonical_target"] not in seen_d100:
            seen_d100.add(r["canonical_target"])
            prior_coords.append({
                "canonical_target": r["canonical_target"],
                "ra_deg": float(r["s_ra"]),
                "dec_deg": float(r["s_dec"]),
            })
    prior_dp_ids = sorted(set(pex100["excluded_dp_ids"]) | set(d100_dps))
    prior_dp_set = set(prior_dp_ids)
    fmt_excl = list(pex100["format_check_excluded_dp_ids"]) + [
        "member.uid___A001_X1284_X16be.cnd_cs21_sci.spw23.cube.I.pbcor.fits"
    ]

    # Assemble FROZEN_COHORT_D101 rows
    frozen_rows: list[dict[str, Any]] = []
    brand_new_check: dict[str, tuple[float, float]] = {}

    # 1. 63 ALMA SODA spectral cube entries
    alma_band_map = {1: "ALMA_B1_7MM", 3: "ALMA_B3_3MM", 4: "ALMA_B4_2MM", 5: "ALMA_B5_2MM"}
    for ci, x in enumerate(ALMA_63_SPECS, 1):
        canon = x["canon"]
        is_bridge = x["sep_prior"] < 120.0
        inst = alma_band_map[int(x["band"])]
        if is_bridge:
            u = u560_map.get(canon) or u560_map[x["prior_ref"]]
            canon_use = u["star"]
            meta_row = {
                "common_name": u["common_name"],
                "role": u["role"],
                "subrole": f"BRIDGE_ALMA_B{x['band']}",
                "science_track": "ALMA_MM_BRIDGE_V59",
                "panchromatic_bridge": True,
                "is_prior_bridge": True,
                "gaia_source_id": u.get("gaia_source_id") or canon_use,
                "ra_deg": round(float(x["ra"]), 7),
                "dec_deg": round(float(x["dec"]), 7),
                "pmra": 0.0, "pmdec": 0.0,
                "dist_pc": float(u["dist_pc"]),
                "within_10pc": float(u["dist_pc"]) <= 10.0,
                "phot_g_mag": float(u.get("phot_g_mag") or 10.0),
                "phot_bp_mag": "", "phot_rp_mag": "",
                "teff_k": float(u["teff_k"]),
                "mh_dex": 0.0, "stellar_mass_msun": 1.0,
                "prior_rv_kms": float(u.get("star_rv_kms") or 0.0),
                "n_exoplanets": int(u.get("n_exoplanets") or 0),
            }
        else:
            canon_use = canon
            meta_row = STAR_META[canon]
            brand_new_check[canon_use] = (meta_row["ra_deg"], meta_row["dec_deg"])

        dp_id = x["soda_id"]
        assert dp_id not in prior_dp_set, f"DP ID overlap with prior phases: {dp_id}"
        res_a = float(x["res_arcsec"])
        rad_arcsec = max(3.5 * res_a, 1.5) if (res_a > 5.0 or canon_use == "GWORI") else max(4.2 * res_a, 1.5)
        r_deg = round(rad_arcsec / 3600.0, 7)
        ra_q, dec_q = float(x["ra"]), float(x["dec"])
        soda_url = f"https://almascience.eso.org/soda/sync?ID={urllib.parse.quote(dp_id)}&CIRCLE={ra_q:.6f}%20{dec_q:.6f}%20{r_deg:.7f}"
        rel_path = f"{inst}/{canon_use}/{dp_id}"
        mjd = float(x["mjd"])
        dist_pc = float(meta_row["dist_pc"])

        frozen_rows.append({
            "instrument": inst,
            "canonical_target": canon_use,
            "common_name": meta_row["common_name"],
            "role": meta_row["role"],
            "subrole": meta_row["subrole"],
            "science_track": meta_row["science_track"],
            "panchromatic_bridge": str(bool(meta_row["panchromatic_bridge"])),
            "is_prior_bridge": str(bool(meta_row["is_prior_bridge"])),
            "gaia_source_id": meta_row["gaia_source_id"],
            "s_ra": f"{ra_q:.7f}",
            "s_dec": f"{dec_q:.7f}",
            "pmra_mas_yr": str(meta_row["pmra"]),
            "pmdec_mas_yr": str(meta_row["pmdec"]),
            "dist_pc": f"{dist_pc:.5f}",
            "within_10pc": str(bool(meta_row["within_10pc"])),
            "phot_g_mag": str(meta_row["phot_g_mag"]),
            "phot_bp_mag": "" if meta_row.get("phot_bp_mag") in (None, "") else str(meta_row["phot_bp_mag"]),
            "phot_rp_mag": "" if meta_row.get("phot_rp_mag") in (None, "") else str(meta_row["phot_rp_mag"]),
            "j_mag": "", "h_mag": "", "ks_mag": "",
            "teff_k": str(meta_row["teff_k"]),
            "mh_dex": str(meta_row["mh_dex"]),
            "stellar_mass_msun": str(meta_row["stellar_mass_msun"]),
            "prior_rv_kms": str(meta_row["prior_rv_kms"]),
            "n_exoplanets": str(meta_row["n_exoplanets"]),
            "has_transiting_planet": "True" if canon_use == "AUMIC" else "False",
            "ecliptic_lat_deg": str(_ecliptic_lat_deg(ra_q, dec_q)),
            "sn1987a_dt_days": str(_ellipsoid_dt_days(ra_q, dec_q, dist_pc, mjd, 83.8667, -69.2697, 46849.316)),
            "gw170817_dt_days": str(_ellipsoid_dt_days(ra_q, dec_q, dist_pc, mjd, 197.4504, -23.3815, 57982.529)),
            "sn2023ixf_dt_days": str(_ellipsoid_dt_days(ra_q, dec_q, dist_pc, mjd, 210.9107, 54.3116, 60083.728)),
            "ppo_align_score": "1.0",
            "epoch_rank": "1",
            "dp_id": dp_id,
            "grating": f"ALMA_B{x['band']}_{round(x['freq_ghz'],2)}GHZ",
            "resolving_power": f"{float(x['rp']):.1f}",
            "mjd_obs": f"{mjd:.6f}",
            "t_exptime": f"{float(x['expt']):.2f}",
            "phase_window": "NONE",
            "signed_phase": "0.0",
            "planet_orbital_rv_kms": "0.0",
            "f1_id": dp_id,
            "f1_rel": rel_path,
            "f1_url": soda_url,
            "f1_bytes": "2800000",
            "total_bytes": "2800000",
        })

    # 2. 39 ESO high-res exposures (9 brand-new stars)
    ep_counters: dict[str, int] = {}
    campaigns_out: dict[str, Any] = {}
    for canon, inst, rp_v, dp_id, grating, mjd, expt in ESO_39_SPECS:
        assert dp_id not in prior_dp_set, f"ESO DP ID overlap with prior: {dp_id}"
        ep_counters[canon] = ep_counters.get(canon, 0) + 1
        ep_idx = ep_counters[canon]
        meta_row = STAR_META[canon]
        brand_new_check[canon] = (meta_row["ra_deg"], meta_row["dec_deg"])
        ra_q, dec_q, dist_pc = float(meta_row["ra_deg"]), float(meta_row["dec_deg"]), float(meta_row["dist_pc"])
        bjd_tdb = mjd + 2400000.5
        ospec = ORBITAL_SPECS.get(canon)
        if ospec:
            rv_orb, s_ph = _kepler_rv(bjd_tdb - ospec["orb_t0_bjd"], ospec["orb_per_days"], ospec["orb_ecc"], ospec["orb_omega_deg"], 0.0, ospec["kp_kms"])
            ph_win = "IN_QUADRATURE" if abs(abs(s_ph) - 0.25) < 0.12 else "IN_WINDOW"
            if canon not in campaigns_out:
                campaigns_out[canon] = dict(ospec)
                campaigns_out[canon].update({"canonical_target": canon, "common_name": meta_row["common_name"], "exposures": []})
            campaigns_out[canon]["exposures"].append({
                "dp_id": dp_id, "mjd_obs": mjd, "bjd_tdb_est": round(bjd_tdb, 6),
                "signed_phase": s_ph, "phase_window": ph_win, "planet_orbital_rv_kms": rv_orb, "ppo_align_score": 1.0,
            })
        else:
            rv_orb, s_ph, ph_win = 0.0, 0.0, "NONE"

        safe_dp = dp_id.replace(":", "_")
        rel_path = f"{inst}/{canon}/{safe_dp}.fits"
        eso_url = f"https://dataportal.eso.org/dataPortal/file/{urllib.parse.quote(dp_id)}"
        exp_bytes = 9500000 if inst == "ESO_ESPRESSO" else 7400000
        frozen_rows.append({
            "instrument": inst,
            "canonical_target": canon,
            "common_name": meta_row["common_name"],
            "role": meta_row["role"],
            "subrole": meta_row["subrole"],
            "science_track": meta_row["science_track"],
            "panchromatic_bridge": "False",
            "is_prior_bridge": "False",
            "gaia_source_id": meta_row["gaia_source_id"],
            "s_ra": f"{ra_q:.7f}",
            "s_dec": f"{dec_q:.7f}",
            "pmra_mas_yr": str(meta_row["pmra"]),
            "pmdec_mas_yr": str(meta_row["pmdec"]),
            "dist_pc": f"{dist_pc:.5f}",
            "within_10pc": str(bool(meta_row["within_10pc"])),
            "phot_g_mag": str(meta_row["phot_g_mag"]),
            "phot_bp_mag": "" if meta_row.get("phot_bp_mag") is None else str(meta_row["phot_bp_mag"]),
            "phot_rp_mag": "" if meta_row.get("phot_rp_mag") is None else str(meta_row["phot_rp_mag"]),
            "j_mag": "", "h_mag": "", "ks_mag": "",
            "teff_k": str(meta_row["teff_k"]),
            "mh_dex": str(meta_row["mh_dex"]),
            "stellar_mass_msun": str(meta_row["stellar_mass_msun"]),
            "prior_rv_kms": str(meta_row["prior_rv_kms"]),
            "n_exoplanets": str(meta_row["n_exoplanets"]),
            "has_transiting_planet": "False",
            "ecliptic_lat_deg": str(_ecliptic_lat_deg(ra_q, dec_q)),
            "sn1987a_dt_days": str(_ellipsoid_dt_days(ra_q, dec_q, dist_pc, mjd, 83.8667, -69.2697, 46849.316)),
            "gw170817_dt_days": str(_ellipsoid_dt_days(ra_q, dec_q, dist_pc, mjd, 197.4504, -23.3815, 57982.529)),
            "sn2023ixf_dt_days": str(_ellipsoid_dt_days(ra_q, dec_q, dist_pc, mjd, 210.9107, 54.3116, 60083.728)),
            "ppo_align_score": "1.0",
            "epoch_rank": str(ep_idx),
            "dp_id": dp_id,
            "grating": grating,
            "resolving_power": f"{rp_v:.1f}",
            "mjd_obs": f"{mjd:.6f}",
            "t_exptime": f"{expt:.3f}",
            "phase_window": ph_win,
            "signed_phase": str(s_ph),
            "planet_orbital_rv_kms": str(rv_orb),
            "f1_id": dp_id,
            "f1_rel": rel_path,
            "f1_url": eso_url,
            "f1_bytes": str(exp_bytes),
            "total_bytes": str(exp_bytes),
        })

    for c_k, c_v in campaigns_out.items():
        mjds = [e["mjd_obs"] for e in c_v["exposures"]]
        rvs = [e["planet_orbital_rv_kms"] for e in c_v["exposures"]]
        c_v["n_epochs"] = len(mjds)
        c_v["baseline_days"] = round(max(mjds) - min(mjds), 2)
        c_v["orbital_dv_span_kms"] = round(max(rvs) - min(rvs), 3)

    # Verify strict 0-overlap against all 632 prior coordinates & intra-D101 separation
    star_sep_verif: list[dict[str, Any]] = []
    min_prior_sep = 1e9
    for st_name, (ra_n, dec_n) in sorted(brand_new_check.items()):
        best_c = min(prior_coords, key=lambda pc: _ang_sep_arcsec(ra_n, dec_n, pc["ra_deg"], pc["dec_deg"]))
        sep_s = _ang_sep_arcsec(ra_n, dec_n, best_c["ra_deg"], best_c["dec_deg"])
        assert sep_s >= 120.0, f"Brand-new star {st_name} too close to prior {best_c}: {sep_s}"
        min_prior_sep = min(min_prior_sep, sep_s)
        star_sep_verif.append({"star": st_name, "min_sep_prior_arcsec": round(sep_s, 2), "nearest_prior": best_c["canonical_target"]})

    bn_items = sorted(brand_new_check.items())
    min_intra_sep = 1e9
    for i in range(len(bn_items)):
        for j in range(i + 1, len(bn_items)):
            sp = _ang_sep_arcsec(bn_items[i][1][0], bn_items[i][1][1], bn_items[j][1][0], bn_items[j][1][1])
            min_intra_sep = min(min_intra_sep, sp)
            assert sp >= 120.0, f"Intra-D101 collision {bn_items[i][0]} vs {bn_items[j][0]}: {sp}"

    now_utc = dt.datetime.now(tz=dt.timezone.utc)
    now_iso = now_utc.isoformat()
    now_epoch = round(now_utc.timestamp(), 4)

    # Write Stage-1 outputs
    cohort_csv = WS / "FROZEN_COHORT_D101.csv"
    with cohort_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FROZEN_HEADER)
        w.writeheader()
        w.writerows(frozen_rows)

    n_new_ctrl = sum(1 for k in brand_new_check if STAR_META[k]["role"] == "CONTROL")
    n_new_10pc = sum(1 for k in brand_new_check if STAR_META[k]["within_10pc"])
    proj_bytes = sum(int(r["total_bytes"]) for r in frozen_rows)

    pex_out = {
        "schema": "D101_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D101",
        "verified_utc": now_iso,
        "prior_phases_covered": "C001-C037 + D001-D100",
        "n_prior_excluded_coords": len(prior_coords),
        "n_prior_excluded_dp_ids": len(prior_dp_ids),
        "n_format_check_excluded_dp_ids": len(fmt_excl),
        "d101_total_stars": len({r["canonical_target"] for r in frozen_rows}),
        "d101_brand_new_unique_stars": len(brand_new_check),
        "d101_prior_bridge_stars": len({r["canonical_target"] for r in frozen_rows if r["is_prior_bridge"] == "True"}),
        "d101_control_stars": n_new_ctrl,
        "d101_brand_new_controls": n_new_ctrl,
        "d101_brand_new_within_10pc": n_new_10pc,
        "d101_total_input_files": len(frozen_rows),
        "d101_projected_download_bytes": proj_bytes,
        "d101_projected_download_mib": round(proj_bytes / (1024.0 * 1024.0), 4),
        "d101_dp_id_overlap_count": 0,
        "min_brand_new_sky_separation_arcsec": round(min_prior_sep, 2),
        "min_intra_d101_separation_arcsec": round(min_intra_sep, 2),
        "star_separation_verification": star_sep_verif,
        "format_check_excluded_dp_ids": fmt_excl,
        "excluded_dp_ids": prior_dp_ids,
        "excluded_targets_coordinate_registry": prior_coords,
    }
    pex_path = WS / "PRIOR_EXCLUSION_VERIFICATION.json"
    pex_path.write_text(json.dumps(pex_out, indent=2) + "\n")

    snap_out: dict[str, Any] = {
        "schema": "D101_PRIOR_V5_8_PHASES_SNAPSHOT",
        "prior_phases": "C001-C037 + D001-D100",
    }
    for ch, zn, zsha, bmem, bsha in PRIOR_ARCHIVES_TZ:
        k_low = ch.lower()
        snap_out[f"source_archive_{k_low}_name"] = zn
        snap_out[f"source_archive_{k_low}_sha256"] = zsha
        snap_out[f"source_archive_{k_low}_bundle_member"] = bmem
        snap_out[f"source_archive_{k_low}_bundle_sha256"] = bsha
    snap_out.update({
        "prior_unique_stars_count": uni100["unique_stars_total"],
        "prior_science_stars_count": uni100["science_stars_total"],
        "prior_control_stars_count": uni100["control_stars_total"],
        "prior_planet_host_stars_count": uni100["planet_host_stars_total"],
        "prior_confirmed_exoplanets_count": uni100["confirmed_exoplanets_total"],
        "prior_within_10pc_count": uni100["within_10pc_unique_stars"],
        "prior_total_exposures_count": uni100["total_exposures_d079_d100"],
        "prior_cumulative_integration_hours": uni100["total_integration_hours_d079_d100"],
        "prior_calibration_trials_count": uni100["total_calibration_trials_d079_d100"],
        "prior_v2_false_alarms_eliminated_total": uni100["v2_false_alarms_eliminated_total"],
        "prior_cumulative_orbital_campaigns_count": uni100["cumulative_orbital_campaigns"],
        "prior_panchromatic_bridge_stars_count": uni100["panchromatic_bridge_stars_total"],
        "prior_revisited_control_multi_phase_stars": uni100["revisited_control_multi_phase_stars"],
        "prior_multi_phase_targets_total": uni100["multi_phase_targets_total"],
        "prior_panchromatic_bridge_cells_count": uni100["panchromatic_bridge_cells_total"],
        "prior_cumulative_comb_stacks": uni100["cumulative_comb_stacks"],
        "prior_coherent_eccentric_keplerian_campaigns": uni100["coherent_eccentric_keplerian_campaigns"],
        "d100_summary_headline": uni100,
        "prior_unified_560_rows": sx["u560"],
        "prior_bridge_74_rows": sx["br74"],
        "prior_allsky_comb_unified_rows": sx["ac_u"],
        "prior_allsky_comb_candidate_rows": sx["ac_c"],
        "prior_ellipsoid_560_rows": sx["ell560"],
    })
    snap_path = WS / "PRIOR_V5_8_PHASES_SNAPSHOT.json"
    snap_path.write_text(json.dumps(snap_out, indent=2) + "\n")

    orb_out = {
        "schema": "D101_ORBITAL_CAMPAIGNS_AND_KINEMATICS",
        "phase_id": "D101",
        "campaign_range": "#151-#156 (live D101) + #1-#42 retroactive (48 DRIFT_V59 + COMB_DRIFT_V59 campaigns total)",
        "n_campaigns": len(campaigns_out),
        "campaigns": campaigns_out,
    }
    orb_path = WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json"
    orb_path.write_text(json.dumps(orb_out, indent=2) + "\n")

    stage1_files = [
        "v5_9_detector.py", "build_cohort.py", "download_inputs.py",
        "FROZEN_COHORT_D101.csv", "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json",
        "PRIOR_EXCLUSION_VERIFICATION.json", "PRIOR_V5_8_PHASES_SNAPSHOT.json",
    ]
    hashes = {fn: _sha256_file(WS / fn) for fn in stage1_files}

    ml_out = {
        "schema": "D101_PROSPECTIVE_METHOD_LOCK",
        "phase_id": "D101",
        "detector_version": "V5.9",
        "detector": "TECHNOSIGNATURE_V5_9_ALMA_MM_BAND1_GAP_CLOSURE_AND_COHERENT_DRIFTING_COMB",
        "locked_utc": now_iso,
        "projected_unified_stars": uni100["unique_stars_total"] + len(brand_new_check),
        "projected_within_10pc_stars": uni100["within_10pc_unique_stars"] + n_new_10pc,
        "d101_brand_new_stars": len(brand_new_check),
        "d101_prior_bridges": pex_out["d101_prior_bridge_stars"],
        "d101_total_files": len(frozen_rows),
        "d101_projected_bytes": proj_bytes,
        "d101_projected_mib": round(proj_bytes / (1024.0 * 1024.0), 4),
        "stage_1_files": hashes,
    }
    ml_path = WS / "METHOD_LOCK.json"
    ml_path.write_text(json.dumps(ml_out, indent=2) + "\n")

    lr_out = {
        "schema": "D101_LOCK_RECEIPT",
        "phase_id": "D101",
        "status": "STAGE-1 SEALED",
        "locked_utc": now_iso,
        "locked_unix_epoch": now_epoch,
        "method_lock_sha256": _sha256_file(ml_path),
        "inputs_dir_exists_at_seal": raw_dir.exists(),
        "locked_files": hashes,
    }
    lr_path = WS / "LOCK_RECEIPT.json"
    lr_path.write_text(json.dumps(lr_out, indent=2) + "\n")

    print(
        f"Stage-1 SEALED: {len(brand_new_check)} brand-new + {pex_out['d101_prior_bridge_stars']} bridges = "
        f"{pex_out['d101_total_stars']} D101 targets ({ml_out['projected_unified_stars']} unified, "
        f"{ml_out['projected_within_10pc_stars']} <10pc), {len(frozen_rows)} files, "
        f"min_prior_sep={min_prior_sep:.2f} arcsec, inputs_exists={raw_dir.exists()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
