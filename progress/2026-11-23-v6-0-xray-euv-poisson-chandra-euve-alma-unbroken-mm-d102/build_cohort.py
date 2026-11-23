#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D102 (V6.0) Prospective Stage-1 Cohort Builder & Method Lock:
  TECHNOSIGNATURE_V6_0_XRAY_EUV_POISSON_CHANDRA_EUVE_AND_ALMA_UNBROKEN_MM

CRITICAL PRE-DOWNLOAD INVARIANT:
  - Must run strictly BEFORE `inputs_d102_v6_0/` exists and BEFORE any science pixels
    are downloaded.
  - Enforces 0 dp_id overlap against all 3,261 prior exposures + 19 format/server exclusions
    and >= 300 arcsec sky separation against all 686 prior targets for all brand-new stars.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import urllib.parse
import zipfile
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent
ROOT = WS.parent.parent
WS101 = ROOT / "analysis_workspace" / "work_v5_9_20261123_d101_alma_mm_band1_gap_closure_drifting_comb"
ARCHIVE_AA_NAME = "SETI_D101_V5_9_ALMA_MM_BAND1_GAP_CLOSURE_DRIFTING_COMB_RESULTS_2026-11-23.zip"
ARCHIVE_AA_SHA256 = "848a2ade7fdb46ed4e4f067e729ccf796a5181501f6e0ed18f573ff871fa8b20"
ARCHIVE_AA_BUNDLE_MEMBER = "work_v5_9_20261123_d101_alma_mm_band1_gap_closure_drifting_comb/bounded_inputs/d101_bounded_bundle.json.gz"
ARCHIVE_AA_BUNDLE_SHA256 = "f3735b57ef170c3162fad61a825fad086c768e1a6662d48d3a4637c5eea51ec4"

FORMAT_CHECK_PROBES_D102 = [
    "CHANDRA_OBSID_1099",
    "CHANDRA_OBSID_7432",
    "euve2/1136_1551__9812251330N_vo.fits",
    "member.uid___A001_X1296_Xa93.PG1404p226_sci.spw22.cube.I.manual.image.pbcor.fits",
]

FROZEN_HEADER = [
    "instrument", "canonical_target", "common_name", "role", "subrole", "science_track",
    "panchromatic_bridge", "is_prior_bridge", "gaia_source_id", "s_ra", "s_dec",
    "pmra_mas_yr", "pmdec_mas_yr", "dist_pc", "within_10pc", "phot_g_mag", "phot_bp_mag",
    "phot_rp_mag", "j_mag", "h_mag", "ks_mag", "teff_k", "mh_dex", "stellar_mass_msun",
    "prior_rv_kms", "n_exoplanets", "has_transiting_planet", "ecliptic_lat_deg",
    "sn1987a_dt_days", "gw170817_dt_days", "sn2023ixf_dt_days", "ppo_align_score",
    "epoch_rank", "dp_id", "grating", "resolving_power", "mjd_obs", "t_exptime",
    "phase_window", "signed_phase", "planet_orbital_rv_kms", "f1_id", "f1_rel",
    "f1_url", "f1_bytes", "total_bytes",
]

# ---------------------------------------------------------------------------
# Brand-New Star & Extragalactic Control Metadata (Strictly >= 300" from prior 686)
# ---------------------------------------------------------------------------
NEW_META: dict[str, dict[str, Any]] = {
    # Chandra HETG brand-new science + AGN controls
    "WR6":        {"common_name": "WR 6 (EZ CMa, WN4b Wind Benchmark)", "role": "SCIENCE", "ra": 103.55435, "dec": -23.92834, "dist_pc": 1537.279, "teff_k": 85000.0, "rv": 164.0, "gmag": 6.65, "n_pl": 0, "mass": 23.0},
    "XIPER":      {"common_name": "xi Per (Menkib, O7.5III Wind Star)", "role": "SCIENCE", "ra": 59.74126, "dec": 35.79103, "dist_pc": 408.881, "teff_k": 35000.0, "rv": 65.4, "gmag": 4.02, "n_pl": 0, "mass": 30.0},
    "ZETAORI":    {"common_name": "zeta Ori A (Alnitak, O9.7Ib Wind Benchmark)", "role": "SCIENCE", "ra": 85.18969, "dec": -1.94257, "dist_pc": 225.734, "teff_k": 29500.0, "rv": 18.5, "gmag": 1.77, "n_pl": 0, "mass": 33.0},
    "TTAU":       {"common_name": "T Tauri (Prototype Pre-Main-Sequence Star)", "role": "SCIENCE", "ra": 65.49763, "dec": 19.53512, "dist_pc": 145.136, "teff_k": 5250.0, "rv": 20.106, "gmag": 9.85, "n_pl": 0, "mass": 2.1},
    "VWCEP":      {"common_name": "VW Cep (Active Contact Binary)", "role": "SCIENCE", "ra": 309.34013, "dec": 75.60053, "dist_pc": 26.537, "teff_k": 5100.0, "rv": -7.9, "gmag": 7.23, "n_pl": 0, "mass": 1.0},
    "ERVUL":      {"common_name": "ER Vul (Active RS CVn Binary)", "role": "SCIENCE", "ra": 315.60795, "dec": 27.80735, "dist_pc": 50.502, "teff_k": 5900.0, "rv": -24.6, "gmag": 7.18, "n_pl": 0, "mass": 1.1},
    "MR2251_178": {"common_name": "MR 2251-178 (Quasar z=0.064, X-Ray Control)", "role": "CONTROL", "ra": 343.52452, "dec": -17.58206, "dist_pc": 287000000.0, "teff_k": 15000.0, "rv": 0.0, "gmag": 14.3, "n_pl": 0, "mass": 1.0},
    "NGC3393":    {"common_name": "NGC 3393 (Seyfert 2 z=0.0125, X-Ray Control)", "role": "CONTROL", "ra": 162.09777, "dec": -25.16208, "dist_pc": 53600000.0, "teff_k": 5500.0, "rv": 3746.2, "gmag": 12.2, "n_pl": 0, "mass": 1.0},
    # Chandra LETG + EUVE brand-new stars + AGN controls
    "EPSCMA":     {"common_name": "eps CMa (Adhara, B1.5II EUV-Bright Giant)", "role": "SCIENCE", "ra": 104.65645, "dec": -28.97209, "dist_pc": 124.224, "teff_k": 22200.0, "rv": 27.3, "gmag": 1.50, "n_pl": 0, "mass": 12.6},
    "44BOO":      {"common_name": "44 Boo (i Boo, W UMa Corona Benchmark)", "role": "SCIENCE", "ra": 225.94707, "dec": 47.65406, "dist_pc": 12.508, "teff_k": 5300.0, "rv": -17.89, "gmag": 4.65, "n_pl": 0, "mass": 1.0},
    "BETACET":    {"common_name": "beta Cet (Diphda, G9.5III Active Corona + EUV)", "role": "SCIENCE", "ra": 10.89738, "dec": -17.98661, "dist_pc": 29.533, "teff_k": 4800.0, "rv": 13.257, "gmag": 1.80, "n_pl": 0, "mass": 2.8},
    "ABDOR":      {"common_name": "AB Dor (Young Rapid Rotator K0V)", "role": "SCIENCE", "ra": 82.18696, "dec": -65.44867, "dist_pc": 14.852, "teff_k": 5081.0, "rv": 16.93, "gmag": 6.69, "n_pl": 0, "mass": 0.86},
    "H1821P643":  {"common_name": "H1821+643 (Quasar z=0.297, LETG X-Ray Control)", "role": "CONTROL", "ra": 275.48839, "dec": 64.34339, "dist_pc": 1540000000.0, "teff_k": 15000.0, "rv": 0.0, "gmag": 14.2, "n_pl": 0, "mass": 1.0},
    "NGC5548":    {"common_name": "NGC 5548 (Seyfert 1 z=0.017, LETG X-Ray Control)", "role": "CONTROL", "ra": 214.49808, "dec": 25.13683, "dist_pc": 74500000.0, "teff_k": 6000.0, "rv": 5149.0, "gmag": 13.5, "n_pl": 0, "mass": 1.0},
    # EUVE brand-new
    "EQPEG":      {"common_name": "EQ Peg (M3.5V Flare Binary, 6.18 pc)", "role": "SCIENCE", "ra": 352.96741, "dec": 19.93726, "dist_pc": 6.182, "teff_k": 3250.0, "rv": 1.5, "gmag": 9.10, "n_pl": 0, "mass": 0.39},
    "XIUMA":      {"common_name": "xi UMa (Alula Australis, 8.73 pc Active Quad)", "role": "SCIENCE", "ra": 169.54555, "dec": 31.52929, "dist_pc": 8.730, "teff_k": 5950.0, "rv": -18.2, "gmag": 3.70, "n_pl": 0, "mass": 1.05},
    "IIPEG":      {"common_name": "II Peg (RS CVn Flare Star, EUVE Benchmark)", "role": "SCIENCE", "ra": 358.76688, "dec": 28.63368, "dist_pc": 39.124, "teff_k": 4600.0, "rv": -20.5, "gmag": 7.15, "n_pl": 0, "mass": 0.8},
    "HZ43":       {"common_name": "HZ 43 (Hot DA White Dwarf EUV Calibrator)", "role": "CONTROL", "ra": 199.09106, "dec": 29.09873, "dist_pc": 60.341, "teff_k": 50000.0, "rv": 54.17, "gmag": 12.91, "n_pl": 0, "mass": 0.56},
    "EIERI":      {"common_name": "EI Eri (Rapidly Rotating G5IV BY Dra)", "role": "SCIENCE", "ra": 62.42038, "dec": -7.89283, "dist_pc": 54.408, "teff_k": 5500.0, "rv": 17.6, "gmag": 6.95, "n_pl": 0, "mass": 1.4},
    "MRK421":     {"common_name": "Mrk 421 (Blazar z=0.031, EUVE Control)", "role": "CONTROL", "ra": 166.11381, "dec": 38.20883, "dist_pc": 136000000.0, "teff_k": 12000.0, "rv": 0.0, "gmag": 13.0, "n_pl": 0, "mass": 1.0},
    "3C273":      {"common_name": "3C 273 (Quasar z=0.158, EUVE Control)", "role": "CONTROL", "ra": 187.27792, "dec": 2.05239, "dist_pc": 749000000.0, "teff_k": 15000.0, "rv": 0.0, "gmag": 12.9, "n_pl": 0, "mass": 1.0},
    "PKS2155":    {"common_name": "PKS 2155-304 (Blazar z=0.116, EUVE Control)", "role": "CONTROL", "ra": 329.71694, "dec": -30.22559, "dist_pc": 537000000.0, "teff_k": 12000.0, "rv": 0.0, "gmag": 13.1, "n_pl": 0, "mass": 1.0},
    "NGC4051":    {"common_name": "NGC 4051 (Seyfert 1 z=0.0023, EUVE Control)", "role": "CONTROL", "ra": 180.79004, "dec": 44.53130, "dist_pc": 13500000.0, "teff_k": 5500.0, "rv": 700.0, "gmag": 12.6, "n_pl": 0, "mass": 1.0},
    # ALMA seam-closure + B8 cubes (all extragalactic / ISM molecular controls)
    "JADESGSZ7":  {"common_name": "JADES-GS-z7-01-QU (ALMA B6 214 GHz Seam)", "role": "CONTROL", "ra": 53.15508, "dec": -27.80178, "dist_pc": 2.0e10, "teff_k": 8000.0, "rv": 0.0, "gmag": 24.0, "n_pl": 0, "mass": 1.0},
    "A2744Q":     {"common_name": "Abell 2744 Quintet (ALMA B6 211-215 GHz Seam)", "role": "CONTROL", "ra": 3.60375, "dec": -30.38225, "dist_pc": 1.5e9, "teff_k": 6000.0, "rv": 0.0, "gmag": 19.0, "n_pl": 0, "mass": 1.0},
    "PG0007P106": {"common_name": "PG 0007+106 (Mrk 1501, ALMA B6 211-213 GHz)", "role": "CONTROL", "ra": 2.62919, "dec": 10.97486, "dist_pc": 3.9e8, "teff_k": 6000.0, "rv": 0.0, "gmag": 15.0, "n_pl": 0, "mass": 1.0},
    "HERBS168AB": {"common_name": "HERBS-168 A+B (SMG, ALMA B5 208.9-210.9 GHz Seam)", "role": "CONTROL", "ra": 342.68950, "dec": -30.78897, "dist_pc": 1.0e10, "teff_k": 5500.0, "rv": 0.0, "gmag": 21.0, "n_pl": 0, "mass": 1.0},
    "IRAS17208":  {"common_name": "IRAS 17208-0014 (ULIRG, ALMA B5 163.2-165.1 GHz)", "role": "CONTROL", "ra": 260.84142, "dec": -0.28361, "dist_pc": 1.89e8, "teff_k": 4500.0, "rv": 0.0, "gmag": 15.2, "n_pl": 0, "mass": 1.0},
    "HERBS57":    {"common_name": "HERBS-57 (SMG, ALMA B4 161.4-163.4 GHz Seam)", "role": "CONTROL", "ra": 12.22242, "dec": -30.51942, "dist_pc": 1.0e10, "teff_k": 5500.0, "rv": 0.0, "gmag": 21.0, "n_pl": 0, "mass": 1.0},
    "G0693":      {"common_name": "G+0.693-0.027 (Sgr B2 Complex, 158.9-162.6 GHz)", "role": "CONTROL", "ra": 266.83932, "dec": -28.35705, "dist_pc": 8150.0, "teff_k": 3500.0, "rv": 68.0, "gmag": 18.0, "n_pl": 0, "mass": 1.0},
    "J004157":    {"common_name": "J004157.77-002932.1 (ALMA B4 158.6-160.5 GHz)", "role": "CONTROL", "ra": 10.48750, "dec": -0.49222, "dist_pc": 3.0e9, "teff_k": 5500.0, "rv": 0.0, "gmag": 20.0, "n_pl": 0, "mass": 1.0},
    "DVR2021B":   {"common_name": "DVR2021b RO-1001 (ALMA B4 Low 125.0 GHz Edge)", "role": "CONTROL", "ra": 150.34608, "dec": 2.33469, "dist_pc": 1.0e10, "teff_k": 5500.0, "rv": 0.0, "gmag": 22.0, "n_pl": 0, "mass": 1.0},
    "EIGHTOCLOCK":{"common_name": "Eight O'Clock Arc (Lensed Gal, B3 90.8-94.5 GHz)", "role": "CONTROL", "ra": 5.67083, "dec": 14.52056, "dist_pc": 1.2e10, "teff_k": 6000.0, "rv": 0.0, "gmag": 19.5, "n_pl": 0, "mass": 1.0},
    "AZTEC1":     {"common_name": "AzTEC-1 (z=4.34 SMG, ALMA B3 Low 84.1-87.8 GHz)", "role": "CONTROL", "ra": 334.38337, "dec": 0.29540, "dist_pc": 2.0e10, "teff_k": 6000.0, "rv": 0.0, "gmag": 21.0, "n_pl": 0, "mass": 1.0},
    "NGC7469":    {"common_name": "NGC 7469 (Seyfert 1, ALMA Band 8 482 GHz Frontier)", "role": "CONTROL", "ra": 345.81531, "dec": 8.87369, "dist_pc": 70600000.0, "teff_k": 5500.0, "rv": 4892.0, "gmag": 12.8, "n_pl": 0, "mass": 1.0},
    # ESO Orbits #157-#162 + <10 pc HARPS Control + GJ 203
    "GJ341":      {"common_name": "GJ 341 (TOI-741, Sub-Earth Host ESPRESSO, 10.45 pc)", "role": "SCIENCE", "ra": 140.39938, "dec": -60.28117, "dist_pc": 10.454, "teff_k": 3770.0, "rv": 40.115, "gmag": 8.69, "n_pl": 1, "mass": 0.48, "mh": -0.16},
    "GLIESE12":   {"common_name": "Gliese 12 (Tempered Earth-Sized HZ Host, 12.21 pc)", "role": "SCIENCE", "ra": 3.95791, "dec": 13.55762, "dist_pc": 12.210, "teff_k": 3328.0, "rv": 51.213, "gmag": 11.40, "n_pl": 1, "mass": 0.255, "mh": -0.24},
    "HD90156":    {"common_name": "HD 90156 (G5V 1-pl ESPRESSO R=140k, 21.95 pc)", "role": "SCIENCE", "ra": 155.98011, "dec": -29.64510, "dist_pc": 21.950, "teff_k": 5599.0, "rv": 26.958, "gmag": 6.77, "n_pl": 1, "mass": 0.84, "mh": -0.24},
    "GJ180":      {"common_name": "GJ 180 (3-pl HZ Super-Earth System HARPS, 11.94 pc)", "role": "SCIENCE", "ra": 73.46010, "dec": -17.77619, "dist_pc": 11.941, "teff_k": 3371.0, "rv": -14.478, "gmag": 9.95, "n_pl": 3, "mass": 0.43, "mh": 0.0},
    "GJ163":      {"common_name": "GJ 163 (3-pl M-dwarf Multi-Planet System, 15.13 pc)", "role": "SCIENCE", "ra": 62.32284, "dec": -53.37118, "dist_pc": 15.129, "teff_k": 3500.0, "rv": 36.900, "gmag": 10.74, "n_pl": 3, "mass": 0.40, "mh": 0.10},
    "HD215152":   {"common_name": "HD 215152 (4-pl Compact Super-Earth System, 21.60 pc)", "role": "SCIENCE", "ra": 340.83809, "dec": -6.40207, "dist_pc": 21.597, "teff_k": 4935.0, "rv": -13.753, "gmag": 7.81, "n_pl": 4, "mass": 0.77, "mh": -0.10},
    "GJ203":      {"common_name": "GJ 203 (0-pl M3.5V HARPS Control, 10.22 pc)", "role": "CONTROL", "ra": 82.00063, "dec": 9.64393, "dist_pc": 10.216, "teff_k": 3310.0, "rv": 60.611, "gmag": 11.28, "n_pl": 0, "mass": 0.25},
    "GJ831":      {"common_name": "GJ 831 (0-pl M4.5V <10 pc Control, 7.46 pc)", "role": "CONTROL", "ra": 322.82737, "dec": -9.79069, "dist_pc": 7.458, "teff_k": 3150.0, "rv": -56.334, "gmag": 10.67, "n_pl": 0, "mass": 0.28},
}

# ---------------------------------------------------------------------------
# Exact Locked Inputs (All URLs, SODA IDs, & dp_ids verified in Stage-1 metadata)
# ---------------------------------------------------------------------------
CHANDRA_SPECS = [
    # (canon, is_bridge, obsid, filename, grating, detnam, start_iso, exptime_s, clen_bytes)
    ("TWHYA",      True,  7436,  "acisf07436N004_pha2.fits.gz", "HETG", "ACIS-S", "2007-02-28 15:06:33", 158390.0, 1081143),
    ("IMLUP",      True,  9938,  "acisf09938N003_pha2.fits.gz", "HETG", "ACIS-S", "2009-05-04 20:57:52", 141930.0, 1074762),
    ("ETACAR",     True,  12358, "acisf12358N003_pha2.fits.gz", "HETG", "ACIS-S", "2011-10-20 11:18:34", 102190.0, 1094257),
    ("EVLAC",      True,  1885,  "acisf01885N004_pha2.fits.gz", "HETG", "ACIS-S", "2001-09-19 19:35:19", 100020.0, 1082427),
    ("WR6",        False, 14533, "acisf14533N003_pha2.fits.gz", "HETG", "ACIS-S", "2013-08-19 13:44:02", 174840.0, 1074037),
    ("XIPER",      False, 4512,  "acisf04512N004_pha2.fits.gz", "HETG", "ACIS-S", "2004-03-22 02:09:10", 158800.0, 1072776),
    ("ZETAORI",    False, 13460, "acisf13460N004_pha2.fits.gz", "HETG", "ACIS-S", "2011-11-29 03:41:38", 142900.0, 1076905),
    ("TTAU",       False, 16672, "acisf16672N003_pha2.fits.gz", "HETG", "ACIS-S", "2015-01-01 12:49:47", 127370.0, 1066026),
    ("VWCEP",      False, 3766,  "acisf03766N004_pha2.fits.gz", "HETG", "ACIS-S", "2003-08-29 05:49:11", 116620.0, 1079358),
    ("ERVUL",      False, 1887,  "acisf01887N004_pha2.fits.gz", "HETG", "ACIS-S", "2001-03-29 03:33:39", 112010.0, 1086618),
    ("MR2251_178", False, 12829, "acisf12829N003_pha2.fits.gz", "HETG", "ACIS-S", "2011-09-29 07:03:04", 184590.0, 1118889),
    ("NGC3393",    False, 13967, "acisf13967N003_pha2.fits.gz", "HETG", "ACIS-S", "2012-02-29 17:25:54", 176780.0, 1066590),
    ("61CYGB",     True,  13651, "hrcf13651N004_pha2.fits.gz", "LETG", "HRC-S",  "2012-02-13 20:18:27", 187720.0, 447277),
    ("EPSERI",     True,  1869,  "hrcf01869N005_pha2.fits.gz", "LETG", "HRC-S",  "2001-03-21 07:17:12", 105340.0, 434873),
    ("HD79211",    True,  12325, "hrcf12325N003_pha2.fits.gz", "LETG", "HRC-S",  "2010-12-29 03:09:35",  95600.0, 438858),
    ("HD131156A",  True,  8899,  "hrcf08899N004_pha2.fits.gz", "LETG", "HRC-S",  "2008-05-02 11:19:43",  93280.0, 440925),
    ("ALTAIR",     True,  11015, "hrcf11015N004_pha2.fits.gz", "LETG", "HRC-S",  "2009-08-26 15:19:32",  92870.0, 440964),
    ("HD34029",    True,  1248,  "hrcf01248N005_pha2.fits.gz", "LETG", "HRC-S",  "1999-11-09 13:27:21",  84600.0, 442765),
    ("EPSCMA",     False, 6441,  "hrcf06441N004_pha2.fits.gz", "LETG", "HRC-S",  "2006-07-08 07:07:13", 140380.0, 444734),
    ("44BOO",      False, 3757,  "hrcf03757N004_pha2.fits.gz", "LETG", "HRC-S",  "2003-09-22 00:01:35", 114730.0, 443396),
    ("BETACET",    False, 2547,  "hrcf02547N007_pha2.fits.gz", "LETG", "HRC-S",  "2001-12-25 21:16:31", 106140.0, 441694),
    ("ABDOR",      False, 3762,  "hrcf03762N004_pha2.fits.gz", "LETG", "HRC-S",  "2002-12-10 21:24:14",  85270.0, 433885),
    ("H1821P643",  False, 2186,  "acisf02186N005_pha2.fits.gz", "LETG", "ACIS-S", "2001-01-18 17:26:52", 165050.0, 553384),
    ("NGC5548",    False, 3383,  "hrcf03383N004_pha2.fits.gz", "LETG", "HRC-S",  "2002-01-21 07:33:57", 170110.0, 443545),
]

EUVE_SPECS = [
    # (canon, is_bridge, obs_id, exptime_s, file_bytes)
    ("PROXIMACEN",   True,  "proxima_cen__9305211911D",  145592.2, 40320),
    ("ALPCENA",      True,  "alpha_cen__9703100800N",    121457.6, 43200),
    ("SIRIUS",       True,  "sirius_b__9611270039N",     208884.9, 43200),
    ("EPSERI",       True,  "epsilon_eri__9509051851D",  168292.6, 40320),
    ("PROCYON",      True,  "procyon__9403122334N",      136044.3, 43200),
    ("AUMIC",        True,  "au_mic__9207141227N",        69643.6, 43200),
    ("ADLEO",        True,  "ad_leo__9905061641N",       186879.2, 43200),
    ("WOLF359",      True,  "cn_leo__9501240630N",       188035.3, 43200),
    ("LALANDE21185", True,  "gj_411__9503221134N",       172845.6, 43200),
    ("EVLAC",        True,  "ev_lac__9309091718N",       113156.2, 43200),
    ("HD131156A",    True,  "xi_boo__9704200202N",       270083.3, 43200),
    ("ALTAIR",       True,  "altair__9306270042N",        88663.5, 43200),
    ("HD22468",      True,  "v711_tau__9609011158N",     204964.0, 43200),
    ("GD71",         True,  "gd_71__9612181423N",        125862.0, 43200),
    ("EQPEG",        False, "eq_peg__9610020810N",        71630.6, 43200),
    ("XIUMA",        False, "xi_uma__9705141126N",       315705.0, 43200),
    ("BETACET",      False, "beta_cet__9409301551N",     171624.4, 43200),
    ("IIPEG",        False, "ii_peg__0010100045N",       252547.9, 43200),
    ("EIERI",        False, "ei_eri__9801261302N",       206886.3, 43200),
    ("HZ43",         False, "hz_43__9405202231N",        156740.4, 43200),
    ("MRK421",       False, "mrk_421__9604171230N",      346420.6, 43200),
    ("3C273",        False, "3c_273__9501031243N",       304263.6, 43200),
    ("PKS2155",      False, "pks_2155-304__9307051242N", 151205.3, 43200),
    ("NGC4051",      False, "ngc_4051__9805080109N",     200648.7, 43200),
]

# 22 verified single-pointing ALMA SODA cubes (0 mosaics, excluding uid://A001/X3620/X9b)
ALMA_SPECS = [
    # (canon, is_bridge, inst, soda_id, ra, dec, cutout_rad_deg, exptime_s, approx_ghz, est_bytes)
    ("JADESGSZ7",   False, "ALMA_B6_1MM",  "member.uid___A001_X3621_X2b72.JADES-GS-z7-01-QU_sci.spw25.cube.I.pbcor.fits",       53.15508, -27.80178, 0.0005, 28123.0, 214.0,  7500000),
    ("A2744Q",      False, "ALMA_B6_1MM",  "member.uid___A001_X3621_X3777.A2744-the_quintet_sci.spw25.cube.I.pbcor.fits",       3.60375, -30.38225, 0.0006, 23224.0, 212.4,  7000000),
    ("A2744Q",      False, "ALMA_B6_1MM",  "member.uid___A001_X3621_X3777.A2744-the_quintet_sci.spw27.cube.I.pbcor.fits",       3.60375, -30.38225, 0.0006, 23224.0, 214.2,  7000000),
    ("PG0007P106",  False, "ALMA_B6_1MM",  "member.uid___A001_X1296_Xb53.s9_0.PG0007p106_sci.spw18.cube.I.iter1.image.pbcor.fits", 2.62919,  10.97486, 0.0020,  8891.0, 212.0,  1000000),
    ("HERBS168AB",  False, "ALMA_B5_2MM",  "member.uid___A001_X3621_X3568.HERBS168ApB_sci.spw16.cube.I.pbcor.fits",             342.68950, -30.78897, 0.0012,  9374.0, 209.9,  8000000),
    ("IRAS17208",   False, "ALMA_B5_2MM",  "member.uid___A001_X133d_X26b9.IRAS17208-0014_sci.spw25.cube.I.manual.image.pbcor.fits", 260.84142, -0.28361, 0.0003, 7258.0, 164.2,  2500000),
    ("HERBS57",     False, "ALMA_B4_2MM",  "member.uid___A001_X3621_X3544.HERBS57_sci.spw20.cube.I.selfcal.pbcor.fits",        12.22242, -30.51942, 0.0020, 11794.0, 162.4,  2000000),
    ("G0693",       False, "ALMA_B4_2MM",  "member.uid___A001_X3788_Xb832._Gp0.693__sci.spw24.cube.I.pbcor.fits",             266.83932, -28.35705, 0.0020, 55158.0, 159.9,  2000000),
    ("G0693",       False, "ALMA_B4_2MM",  "member.uid___A001_X3788_Xb832._Gp0.693__sci.spw26.cube.I.pbcor.fits",             266.83932, -28.35705, 0.0020, 55158.0, 161.7,  2000000),
    ("J004157",     False, "ALMA_B4_2MM",  "member.uid___A001_X3788_X57aa._J004157.77-002932.1__sci.spw24.cube.I.pbcor.fits",  10.48750,  -0.49222, 0.0020, 28123.0, 159.5,  2000000),
    ("DVR2021B",    False, "ALMA_B4_2MM",  "member.uid___A001_X3622_X7c0.DVR2021b_RO-1001_sci.spw15.cube.I.pbcor.fits",        150.34608,   2.33469, 0.0020, 52950.0, 126.0,  1000000),
    ("EIGHTOCLOCK", False, "ALMA_B3_3MM",  "member.uid___A001_X3577_X4ff.Eight_Oclock_Arc_sci.spw25.cube.I.selfcal.pbcor.fits",  5.67083,  14.52056, 0.0007, 15785.0,  91.7,  9000000),
    ("EIGHTOCLOCK", False, "ALMA_B3_3MM",  "member.uid___A001_X3577_X4ff.Eight_Oclock_Arc_sci.spw27.cube.I.selfcal.pbcor.fits",  5.67083,  14.52056, 0.0007, 15785.0,  93.6,  9000000),
    ("AZTEC1",      False, "ALMA_B3_3MM",  "member.uid___A001_X2d1f_X503.AzTEC1_sci.spw25.cube.I.pbcor.fits",                  334.38337,   0.29540, 0.0012, 76658.0,  86.9,  5500000),
    ("AZTEC1",      False, "ALMA_B3_3MM",  "member.uid___A001_X2d1f_X503.AzTEC1_sci.spw27.cube.I.pbcor.fits",                  334.38337,   0.29540, 0.0012, 76658.0,  85.0,  5500000),
    ("EPSERI",      True,  "ALMA_B6_1MM",  "member.uid___A001_X879_X29f.Epsilon_Eridani_sci.spw16.cube.I.pbcor.fits",          53.22807,  -9.45821, 0.0020,  3806.0, 230.5,  1000000),
    ("TAUCET",      True,  "ALMA_B6_1MM",  "member.uid___A001_X879_X29b.Tau_Ceti_sci.spw16.cube.I.pbcor.fits",                 26.00863, -15.93352, 0.0020, 20624.0, 230.5,  1000000),
    ("FOMALHAUT",   True,  "ALMA_B7_0P9MM","member.uid___A001_X158f_X7e0.fomalhaut_sci.spw16.cube.I.pbcor.fits",              344.41507, -29.62329, 0.0008, 23926.0, 345.8,  4500000),
    ("AUMIC",       True,  "ALMA_B6_1MM",  "member.uid___A002_X609170_X170.AU_Mic_CO_image.pbcor.fits",                        311.29108, -31.34241, 0.0004,  3710.0, 230.5, 40000000),
    ("HD101584",    True,  "ALMA_B7_0P9MM","member.uid___A001_X3845_Xe4b.HD_101584_sci.spw23.cube.I.selfcal.pbcor.fits",      175.24492, -55.57384, 0.0005,  5201.0, 350.8, 15000000),
    ("HD139614",    True,  "ALMA_B7_0P9MM","member.uid___A001_X3833_X5825.HD139614_sci.spw25.cube.I.selfcal.pbcor.fits",      235.19307, -42.49839, 0.0004,  6169.0, 356.7, 90000000),
    ("NGC7469",     False, "ALMA_B8_0P7MM","member.uid___A001_X1288_X10c0.NGC7469_sci.spw16.cube.I.pbcor.fits",               345.81531,   8.87369, 0.0020, 23950.0, 482.6,  3000000),
]

ESO_ORBIT_SPECS = {
    "GJ341": {
        "campaign_order": 157, "phase_id": "D102", "instrument": "ESO_ESPRESSO",
        "grating": "ESPRESSO_377_790NM", "rp": 140000.0,
        "orb_per_days": 7.57686, "orb_ecc": 0.0, "orb_omega_deg": 0.0,
        "orb_t0_bjd": 2459301.771, "kp_kms": 0.001, "pl_note": "1-pl Sub-Earth ESPRESSO, 10.45 pc",
        "exposures": [
            ("ADP.2021-04-14T17:20:34.245", 58477.360675, 1800.0, 252.2),
            ("ADP.2023-01-09T14:55:28.167", 59928.261023, 1200.0, 236.9),
            ("ADP.2022-02-07T12:59:51.202", 59585.270548,  900.0, 229.2),
            ("ADP.2022-08-04T11:32:52.129", 59763.949336, 1200.0, 228.3),
            ("ADP.2022-12-05T11:56:17.818", 59891.263553, 1200.0, 227.6),
            ("ADP.2022-12-05T12:05:58.596", 59900.338358, 1200.0, 227.1),
        ],
    },
    "GLIESE12": {
        "campaign_order": 158, "phase_id": "D102", "instrument": "ESO_ESPRESSO",
        "grating": "ESPRESSO_377_790NM", "rp": 140000.0,
        "orb_per_days": 12.761418, "orb_ecc": 0.24, "orb_omega_deg": -16.0,
        "orb_t0_bjd": 2460033.16351, "kp_kms": 0.00067, "pl_note": "1-pl HZ Earth-Sized ESPRESSO, 12.21 pc",
        "exposures": [
            ("ADP.2024-10-08T11:25:31.385", 60561.179014, 1200.0, 53.6),
            ("ADP.2024-08-06T10:02:57.297", 60515.373089, 1200.0, 50.6),
            ("ADP.2024-09-04T13:58:04.101", 60530.257071, 1200.0, 49.8),
            ("ADP.2024-07-05T11:12:54.471", 60467.396427, 1200.0, 48.0),
            ("ADP.2024-09-04T14:11:23.953", 60536.193698, 1200.0, 46.8),
        ],
    },
    "HD90156": {
        "campaign_order": 159, "phase_id": "D102", "instrument": "ESO_ESPRESSO",
        "grating": "ESPRESSO_377_790NM", "rp": 140000.0,
        "orb_per_days": 49.77, "orb_ecc": 0.31, "orb_omega_deg": 113.0,
        "orb_t0_bjd": 2455169.3, "kp_kms": 0.00369, "pl_note": "1-pl e=0.31 ESPRESSO R=140k, 21.95 pc",
        "exposures": [
            ("ADP.2025-06-04T07:49:47.780", 60800.028645, 740.0, 600.5),
            ("ADP.2024-03-08T10:45:01.995", 60355.258292, 740.0, 540.4),
            ("ADP.2025-04-07T14:37:05.804", 60745.270377, 740.0, 538.8),
            ("ADP.2024-05-08T08:32:50.773", 60419.164791, 740.0, 519.8),
            ("ADP.2024-05-08T08:25:33.107", 60413.083587, 740.0, 517.9),
        ],
    },
    "GJ180": {
        "campaign_order": 160, "phase_id": "D102", "instrument": "ESO_HARPS",
        "grating": "HARPS_378_691NM", "rp": 115000.0,
        "orb_per_days": 106.3, "orb_ecc": 0.14, "orb_omega_deg": 155.0,
        "orb_t0_bjd": 2456000.0, "kp_kms": 0.00208, "pl_note": "3-pl M-dwarf HZ System HARPS, 11.94 pc",
        "exposures": [
            ("ADP.2014-09-23T11:05:12.257", 55129.330948,  900.0, 35.4),
            ("ADP.2015-12-09T02:01:04.207", 57361.258947, 1200.0, 34.7),
            ("ADP.2014-09-17T11:19:55.397", 54455.042277,  900.0, 34.1),
            ("ADP.2015-11-14T02:00:42.740", 57339.271828, 1200.0, 33.2),
            ("ADP.2014-09-18T12:17:21.363", 54800.270037,  900.0, 33.0),
            ("ADP.2014-09-17T11:21:11.443", 54456.172237,  900.0, 32.8),
        ],
    },
    "GJ163": {
        "campaign_order": 161, "phase_id": "D102", "instrument": "ESO_HARPS",
        "grating": "HARPS_378_691NM", "rp": 115000.0,
        "orb_per_days": 603.95116, "orb_ecc": 0.373, "orb_omega_deg": 118.3,
        "orb_t0_bjd": 2455042.553, "kp_kms": 0.00442, "pl_note": "3-pl e=0.373 Long-Baseline HARPS, 15.13 pc",
        "exposures": [
            ("ADP.2017-10-09T01:02:17.646", 58034.403365,  900.0, 33.4),
            ("ADP.2014-10-01T10:22:15.870", 53007.085079, 3209.9, 30.2),
            ("ADP.2014-10-06T10:05:55.987", 56596.237611, 2724.0, 25.7),
            ("ADP.2014-09-23T11:03:40.530", 55065.402421, 2000.0, 22.7),
            ("ADP.2017-04-13T01:02:35.491", 57854.979980, 2600.0, 22.7),
        ],
    },
    "HD215152": {
        "campaign_order": 162, "phase_id": "D102", "instrument": "ESO_HARPS",
        "grating": "HARPS_378_691NM", "rp": 115000.0,
        "orb_per_days": 25.1967, "orb_ecc": 0.0, "orb_omega_deg": 0.0,
        "orb_t0_bjd": 2455000.0, "kp_kms": 0.000747, "pl_note": "4-pl Compact Super-Earth System HARPS, 21.60 pc",
        "exposures": [
            ("ADP.2014-09-24T09:44:08.397", 55507.003166, 900.0, 167.9),
            ("ADP.2014-10-02T10:00:16.163", 53571.199387, 900.0, 161.0),
            ("ADP.2014-09-18T12:13:54.310", 54801.041437, 900.0, 160.9),
            ("ADP.2014-09-25T15:34:49.717", 55809.208781, 900.0, 156.0),
            ("ADP.2014-09-23T11:01:54.840", 55020.344874, 900.0, 155.5),
        ],
    },
}

ESO_CONTROL_SPECS = [
    ("GJ203", "ESO_HARPS", "ADP.2014-09-17T11:23:21.170", 54344.397282, 900.0, 12.1),
    ("GJ203", "ESO_HARPS", "ADP.2014-09-18T12:17:25.000", 54760.306050, 900.0, 12.0),
    ("GJ203", "ESO_HARPS", "ADP.2014-09-18T12:12:38.243", 54758.304868, 900.0, 10.7),
    ("GJ203", "ESO_HARPS", "ADP.2014-10-01T10:19:57.097", 53336.295132, 900.0, 10.4),
    ("GJ831", "ESO_HARPS", "ADP.2014-09-25T15:33:13.550", 55803.086406, 900.0,  7.3),
]


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _ang_sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    c = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c)))) * 3600.0


def _ecliptic_lat_deg(ra_deg: float, dec_deg: float) -> float:
    eps = math.radians(23.4392911)
    ra_r, dec_r = map(math.radians, (ra_deg, dec_deg))
    s = math.sin(dec_r) * math.cos(eps) - math.cos(dec_r) * math.sin(eps) * math.sin(ra_r)
    return round(math.degrees(math.asin(max(-1.0, min(1.0, s)))), 5)


def _ellipsoid_dt_days(ra_deg: float, dec_deg: float, dist_pc: float, mjd_obs: float, ev_ra: float, ev_dec: float, ev_mjd0: float) -> float:
    ra1, d1, ra2, d2 = map(math.radians, (ra_deg, dec_deg, ev_ra, ev_dec))
    c = max(-1.0, min(1.0, math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(ra1 - ra2)))
    geom = 1192.226 * float(dist_pc) * (1.0 - c)
    return round(float(mjd_obs) - (float(ev_mjd0) + geom), 3)


def _kepler_rv(dt_days: float, per_days: float, ecc: float, omega_deg: float, gamma_kms: float, k_kms: float) -> tuple[float, float]:
    m_anom = (2.0 * math.pi * (dt_days % per_days)) / per_days
    ea = m_anom
    for _ in range(15):
        f = ea - ecc * math.sin(ea) - m_anom
        fp = 1.0 - ecc * math.cos(ea)
        ea -= f / max(1e-12, fp)
    nu = 2.0 * math.atan2(math.sqrt(1.0 + ecc) * math.sin(0.5 * ea), math.sqrt(max(1e-12, 1.0 - ecc)) * math.cos(0.5 * ea))
    w_rad = math.radians(omega_deg)
    rv = gamma_kms + k_kms * (math.cos(nu + w_rad) + ecc * math.cos(w_rad))
    ph = ((dt_days / per_days) % 1.0) - 0.5
    return round(float(rv), 6), round(float(ph), 5)


def _iso_to_mjd(iso_s: str) -> float:
    if not iso_s or iso_s == "?":
        return 55000.0
    t = dt.datetime.strptime(iso_s[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc)
    return round(t.timestamp() / 86400.0 + 40587.0, 6)


def _euve_oid_to_mjd(oid: str) -> float:
    # format e.g. proxima_cen__9305211911D -> YYMMDDHHMM
    tail = oid.split("__")[-1][:10]
    yy = int(tail[:2])
    yr = 1900 + yy if yy >= 90 else 2000 + yy
    mo, dy, hh, mm = int(tail[2:4]), int(tail[4:6]), int(tail[6:8]), int(tail[8:10])
    t = dt.datetime(yr, mo, dy, hh, mm, tzinfo=dt.timezone.utc)
    return round(t.timestamp() / 86400.0 + 40587.0, 6)


def _read_d101_sources(archives_dir: Path | None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    zpath = (archives_dir / ARCHIVE_AA_NAME) if archives_dir else (ROOT / "archives" / ARCHIVE_AA_NAME)
    if WS101.exists() and (WS101 / "results" / "SUMMARY.json").exists():
        summ = json.loads((WS101 / "results" / "SUMMARY.json").read_text())
        pex = json.loads((WS101 / "PRIOR_EXCLUSION_VERIFICATION.json").read_text())
        u613 = list(csv.DictReader((WS101 / "results" / "UNIFIED_PANCHROMATIC_V5_9_SYNTHESIS_613STARS.csv").open()))
        br76 = list(csv.DictReader((WS101 / "results" / "PANCHROMATIC_BRIDGE_76STARS_V59.csv").open()))
        ac_u = list(csv.DictReader((WS101 / "results" / "ALLSKY_COMB_V4_1_UNIFIED_D079_D101.csv").open()))
        ac_c = list(csv.DictReader((WS101 / "results" / "ALLSKY_COMB_V4_1_CANDIDATES_D079_D101.csv").open()))
        ell613 = list(csv.DictReader((WS101 / "results" / "MULTIEVENT_ELLIPSOID_613STARS.csv").open()))
        fc101 = list(csv.DictReader((WS101 / "FROZEN_COHORT_D101.csv").open()))
    elif zpath.exists():
        with zipfile.ZipFile(zpath) as zf:
            names = zf.namelist()
            def _ztxt(sfx: str) -> str:
                m = next(n for n in names if n.endswith(sfx))
                return zf.read(m).decode("utf-8")
            summ = json.loads(_ztxt("/results/SUMMARY.json"))
            pex = json.loads(_ztxt("/PRIOR_EXCLUSION_VERIFICATION.json"))
            u613 = list(csv.DictReader(_ztxt("/results/UNIFIED_PANCHROMATIC_V5_9_SYNTHESIS_613STARS.csv").splitlines()))
            br76 = list(csv.DictReader(_ztxt("/results/PANCHROMATIC_BRIDGE_76STARS_V59.csv").splitlines()))
            ac_u = list(csv.DictReader(_ztxt("/results/ALLSKY_COMB_V4_1_UNIFIED_D079_D101.csv").splitlines()))
            ac_c = list(csv.DictReader(_ztxt("/results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D101.csv").splitlines()))
            ell613 = list(csv.DictReader(_ztxt("/results/MULTIEVENT_ELLIPSOID_613STARS.csv").splitlines()))
            fc101 = list(csv.DictReader(_ztxt("/FROZEN_COHORT_D101.csv").splitlines()))
    else:
        raise FileNotFoundError(f"Neither WS101 nor Archive AA ({zpath}) found.")

    snap_extras = {
        "u613": u613, "br76": br76, "ac_u": ac_u, "ac_c": ac_c, "ell613": ell613, "fc101": fc101,
    }
    ell_map = {r["star"]: r for r in ell613}
    u_map = {r["star"]: {**r, "ra_deg": ell_map[r["star"]]["ra_deg"], "dec_deg": ell_map[r["star"]]["dec_deg"]} for r in u613}
    return summ, pex, snap_extras, u_map


def _star_meta(canon: str, is_bridge: bool, u_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if is_bridge:
        assert canon in u_map, f"Bridge target {canon} not found in UNIFIED_613!"
        u = u_map[canon]
        return {
            "common_name": u["common_name"],
            "role": u["role"],
            "ra": float(u["ra_deg"]),
            "dec": float(u["dec_deg"]),
            "dist_pc": float(u["dist_pc"]),
            "teff_k": float(u["teff_k"] or 5000.0),
            "rv": 0.0,
            "gmag": u.get("phot_g_mag") or "",
            "jmag": u.get("j_mag") or "",
            "hmag": u.get("h_mag") or "",
            "kmag": u.get("ks_mag") or "",
            "n_pl": int(u.get("n_exoplanets") or 0),
            "mass": 1.0,
            "mh": 0.0,
            "gaia": canon,
        }
    m = NEW_META[canon]
    return {
        "common_name": m["common_name"],
        "role": m["role"],
        "ra": float(m["ra"]),
        "dec": float(m["dec"]),
        "dist_pc": float(m["dist_pc"]),
        "teff_k": float(m["teff_k"]),
        "rv": float(m.get("rv", 0.0)),
        "gmag": str(m.get("gmag", "")),
        "jmag": "", "hmag": "", "kmag": "",
        "n_pl": int(m.get("n_pl", 0)),
        "mass": float(m.get("mass", 1.0)),
        "mh": float(m.get("mh", 0.0)),
        "gaia": canon,
    }


def _make_row(
    inst: str, canon: str, sm: dict[str, Any], is_bridge: bool,
    subrole: str, track: str, dp_id: str, grating: str, rp: float,
    mjd: float, expt: float, rel_path: str, url: str, est_bytes: int,
    ep_rank: int = 1, ph_win: str = "NONE", s_ph: float = 0.0, rv_orb: float = 0.0,
) -> dict[str, Any]:
    ra, dec, dist_pc = float(sm["ra"]), float(sm["dec"]), float(sm["dist_pc"])
    return {
        "instrument": inst,
        "canonical_target": canon,
        "common_name": sm["common_name"],
        "role": sm["role"],
        "subrole": subrole,
        "science_track": track,
        "panchromatic_bridge": str(bool(is_bridge)),
        "is_prior_bridge": str(bool(is_bridge)),
        "gaia_source_id": sm["gaia"],
        "s_ra": f"{ra:.7f}",
        "s_dec": f"{dec:.7f}",
        "pmra_mas_yr": "0.0",
        "pmdec_mas_yr": "0.0",
        "dist_pc": f"{dist_pc:.5f}",
        "within_10pc": str(dist_pc <= 10.0 and sm["role"] in ("SCIENCE", "CONTROL") and dist_pc < 100.0),
        "phot_g_mag": str(sm["gmag"]),
        "phot_bp_mag": "", "phot_rp_mag": "",
        "j_mag": str(sm["jmag"]), "h_mag": str(sm["hmag"]), "ks_mag": str(sm["kmag"]),
        "teff_k": f"{float(sm['teff_k']):.1f}",
        "mh_dex": str(sm["mh"]),
        "stellar_mass_msun": str(sm["mass"]),
        "prior_rv_kms": str(sm["rv"]),
        "n_exoplanets": str(int(sm["n_pl"])),
        "has_transiting_planet": "False",
        "ecliptic_lat_deg": str(_ecliptic_lat_deg(ra, dec)),
        "sn1987a_dt_days": str(_ellipsoid_dt_days(ra, dec, dist_pc, mjd, 83.8667, -69.2697, 46849.316)),
        "gw170817_dt_days": str(_ellipsoid_dt_days(ra, dec, dist_pc, mjd, 197.4504, -23.3815, 57982.529)),
        "sn2023ixf_dt_days": str(_ellipsoid_dt_days(ra, dec, dist_pc, mjd, 210.9107, 54.3116, 60083.728)),
        "ppo_align_score": "1.0",
        "epoch_rank": str(ep_rank),
        "dp_id": dp_id,
        "grating": grating,
        "resolving_power": f"{rp:.1f}",
        "mjd_obs": f"{mjd:.6f}",
        "t_exptime": f"{expt:.3f}",
        "phase_window": ph_win,
        "signed_phase": str(s_ph),
        "planet_orbital_rv_kms": str(rv_orb),
        "f1_id": dp_id,
        "f1_rel": rel_path,
        "f1_url": url,
        "f1_bytes": str(est_bytes),
        "total_bytes": str(est_bytes),
    }


def main() -> int:
    raw_dir = ROOT / "inputs_d102_v6_0"
    if raw_dir.exists() and not (WS / "LOCK_RECEIPT.json").exists():
        raise RuntimeError(f"CRITICAL REFUSAL: raw input directory {raw_dir} already exists prior to Stage-1 seal!")

    archives_dir = ROOT / "archives"
    summ101, pex101, sx, u_map = _read_d101_sources(archives_dir)
    uni101 = summ101["unified_613star_panchromatic_v5_9_synthesis"]

    # Build cumulative prior registry: 632 + 53 D101 = 685/686 coords; 3159 + 102 D101 = 3261 dp_ids
    prior_coords = list(pex101["excluded_targets_coordinate_registry"])
    seen_d101 = {c.get("canonical_target", "") for c in prior_coords if c.get("canonical_target")}
    d101_dps = []
    for r in sx["fc101"]:
        d101_dps.append(r["dp_id"])
        if r["is_prior_bridge"] == "False" and r["canonical_target"] not in seen_d101:
            seen_d101.add(r["canonical_target"])
            prior_coords.append({
                "canonical_target": r["canonical_target"],
                "ra_deg": float(r["s_ra"]),
                "dec_deg": float(r["s_dec"]),
            })
    prior_dp_ids = sorted(set(pex101["excluded_dp_ids"]) | set(d101_dps))
    prior_dp_set = set(prior_dp_ids)
    fmt_excl = list(pex101["format_check_excluded_dp_ids"]) + FORMAT_CHECK_PROBES_D102
    fmt_excl_set = set(fmt_excl)

    frozen_rows: list[dict[str, Any]] = []
    brand_new_coords: dict[str, tuple[float, float]] = {}

    # 1. 24 Chandra X-ray gratings (12 HETG + 12 LETG)
    for canon, is_b, obsid, fn, grat, detnam, start_iso, expt, fbytes in CHANDRA_SPECS:
        inst = f"CHANDRA_{grat}"
        dp_id = f"CHANDRA_{obsid}_{fn}"
        assert dp_id not in prior_dp_set and dp_id not in fmt_excl_set
        sm = _star_meta(canon, is_b, u_map)
        if not is_b:
            brand_new_coords[canon] = (sm["ra"], sm["dec"])
        rp = 1000.0 if grat == "HETG" else 500.0
        mjd = _iso_to_mjd(start_iso)
        url = f"https://cxc.cfa.harvard.edu/cdaftp/byobsid/{obsid % 10}/{obsid}/primary/{fn}"
        rel = f"{inst}/{canon}/{obsid}_{fn}"
        frozen_rows.append(_make_row(
            inst, canon, sm, is_b,
            f"{'BRIDGE' if is_b else 'NEW'}_{grat}_{detnam}",
            "CHANDRA_XRAY_POISSON_V60", dp_id, f"{grat}_{detnam}", rp, mjd, expt, rel, url, fbytes,
        ))

    # 2. 24 EUVE Extreme-UV spectra
    for canon, is_b, oid, expt, fbytes in EUVE_SPECS:
        dp_id = f"euve2/{oid}_vo.fits"
        assert dp_id not in prior_dp_set and dp_id not in fmt_excl_set
        sm = _star_meta(canon, is_b, u_map)
        if not is_b:
            brand_new_coords[canon] = (sm["ra"], sm["dec"])
        mjd = _euve_oid_to_mjd(oid)
        url = f"https://archive.stsci.edu/missions/euve/vocontainer/euve2/{oid}_vo.fits"
        rel = f"EUVE_DS_S/{canon}/{oid}_vo.fits"
        frozen_rows.append(_make_row(
            "EUVE_DS_S", canon, sm, is_b,
            f"{'BRIDGE' if is_b else 'NEW'}_EUVE_70_700A",
            "EUVE_EXTREME_UV_V60", dp_id, "EUVE_SW_MW_LW", 200.0, mjd, expt, rel, url, fbytes,
        ))

    # 3. 22 ALMA single-pointing cubes (Seam closure + <10 pc B6/B7 + Repeatability + B8 NGC 7469)
    for canon, is_b, inst, soda_id, s_ra, s_dec, cut_rad, expt, ghz, fbytes in ALMA_SPECS:
        assert soda_id not in prior_dp_set and soda_id not in fmt_excl_set
        sm = _star_meta(canon, is_b, u_map)
        # Keep exact ALMA ObsCore pointing coords in cutout URL so primary beam center matches
        if not is_b:
            brand_new_coords[canon] = (sm["ra"], sm["dec"])
        circle = urllib.parse.quote(f"{s_ra:.6f} {s_dec:.6f} {cut_rad:.4f}")
        url = f"https://almascience.eso.org/soda/sync?ID={urllib.parse.quote(soda_id)}&CIRCLE={circle}"
        rel = f"{inst}/{canon}/{soda_id}"
        frozen_rows.append(_make_row(
            inst, canon, sm, is_b,
            f"{'BRIDGE' if is_b else 'NEW'}_{inst}_CUBEV60",
            "ALMA_UNBROKEN_MM_V60", soda_id, f"{inst}_{ghz:.2f}GHZ", 100000.0, 59000.0, expt, rel, url, fbytes,
        ))

    # 4. 32 ESO Orbits #157-#162 + 5 ESO HARPS Controls
    campaigns_out: dict[str, Any] = {}
    for canon, spec in ESO_ORBIT_SPECS.items():
        sm = _star_meta(canon, False, u_map)
        brand_new_coords[canon] = (sm["ra"], sm["dec"])
        campaigns_out[canon] = {
            "campaign_order": spec["campaign_order"],
            "phase_id": "D102",
            "canonical_target": canon,
            "common_name": sm["common_name"],
            "instrument": spec["instrument"],
            "grating": spec["grating"],
            "orb_per_days": spec["orb_per_days"],
            "orb_ecc": spec["orb_ecc"],
            "orb_omega_deg": spec["orb_omega_deg"],
            "orb_t0_bjd": spec["orb_t0_bjd"],
            "kp_kms": spec["kp_kms"],
            "exposures": [],
        }
        for ep_i, (dp_id, mjd, expt, snr) in enumerate(spec["exposures"], 1):
            assert dp_id not in prior_dp_set and dp_id not in fmt_excl_set
            bjd = mjd + 2400000.5
            rv_orb, s_ph = _kepler_rv(bjd - spec["orb_t0_bjd"], spec["orb_per_days"], spec["orb_ecc"], spec["orb_omega_deg"], 0.0, spec["kp_kms"])
            ph_win = "IN_QUADRATURE" if abs(abs(s_ph) - 0.25) < 0.12 else "IN_WINDOW"
            campaigns_out[canon]["exposures"].append({
                "dp_id": dp_id, "mjd_obs": mjd, "bjd_tdb_est": round(bjd, 6),
                "snr": snr, "signed_phase": s_ph, "phase_window": ph_win, "planet_orbital_rv_kms": rv_orb,
            })
            url = f"https://dataportal.eso.org/dataPortal/file/{urllib.parse.quote(dp_id)}"
            rel = f"{spec['instrument']}/{canon}/{dp_id.replace(':', '_')}.fits"
            frozen_rows.append(_make_row(
                spec["instrument"], canon, sm, False,
                f"ORBIT_CAMPAIGN_{spec['campaign_order']}",
                "KEPLERIAN_DRIFT_OR_COMB_V60", dp_id, spec["grating"], spec["rp"], mjd, expt, rel, url,
                9500000 if spec["instrument"] == "ESO_ESPRESSO" else 7400000,
                ep_rank=ep_i, ph_win=ph_win, s_ph=s_ph, rv_orb=rv_orb,
            ))

    for ck in campaigns_out:
        ex_list = campaigns_out[ck]["exposures"]
        mjds = [e["mjd_obs"] for e in ex_list]
        rvs = [e["planet_orbital_rv_kms"] for e in ex_list]
        campaigns_out[ck]["n_epochs"] = len(mjds)
        campaigns_out[ck]["baseline_days"] = round(max(mjds) - min(mjds), 2)
        campaigns_out[ck]["orbital_dv_span_kms"] = round(max(rvs) - min(rvs), 3)

    ctrl_ep: dict[str, int] = {}
    for canon, inst, dp_id, mjd, expt, snr in ESO_CONTROL_SPECS:
        assert dp_id not in prior_dp_set and dp_id not in fmt_excl_set
        ctrl_ep[canon] = ctrl_ep.get(canon, 0) + 1
        sm = _star_meta(canon, False, u_map)
        brand_new_coords[canon] = (sm["ra"], sm["dec"])
        url = f"https://dataportal.eso.org/dataPortal/file/{urllib.parse.quote(dp_id)}"
        rel = f"{inst}/{canon}/{dp_id.replace(':', '_')}.fits"
        frozen_rows.append(_make_row(
            inst, canon, sm, False,
            "CONTROL_HARPS_0PL", "HARPS_CONTROL_V60", dp_id, "HARPS_378_691NM", 115000.0,
            mjd, expt, rel, url, 7400000, ep_rank=ctrl_ep[canon],
        ))

    # Deduplicate check & strict >= 300" sky separation against all prior coords
    star_sep_verif: list[dict[str, Any]] = []
    min_prior_sep = 1e9
    for st_name, (ra_n, dec_n) in sorted(brand_new_coords.items()):
        best_c = min(prior_coords, key=lambda pc: _ang_sep_arcsec(ra_n, dec_n, pc["ra_deg"], pc["dec_deg"]))
        sep_s = _ang_sep_arcsec(ra_n, dec_n, best_c["ra_deg"], best_c["dec_deg"])
        assert sep_s >= 300.0, f"Brand-new star {st_name} within 300\" of prior {best_c}: {sep_s:.2f}\""
        min_prior_sep = min(min_prior_sep, sep_s)
        star_sep_verif.append({"star": st_name, "min_sep_prior_arcsec": round(sep_s, 2), "nearest_prior": best_c.get("canonical_target", "")})

    bn_items = sorted(brand_new_coords.items())
    min_intra_sep = 1e9
    for i in range(len(bn_items)):
        for j in range(i + 1, len(bn_items)):
            sp = _ang_sep_arcsec(bn_items[i][1][0], bn_items[i][1][1], bn_items[j][1][0], bn_items[j][1][1])
            min_intra_sep = min(min_intra_sep, sp)
            assert sp >= 120.0, f"Intra-D102 collision {bn_items[i][0]} vs {bn_items[j][0]}: {sp}"

    # Guarantee 0 dp_id duplicates within D102
    d102_dps = [r["dp_id"] for r in frozen_rows]
    assert len(d102_dps) == len(set(d102_dps)), "Duplicate dp_id inside D102 frozen cohort!"

    now_utc = dt.datetime.now(tz=dt.timezone.utc)
    now_iso = now_utc.isoformat()
    now_epoch = round(now_utc.timestamp(), 4)

    cohort_csv = WS / "FROZEN_COHORT_D102.csv"
    with cohort_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FROZEN_HEADER)
        w.writeheader()
        w.writerows(frozen_rows)

    n_new_ctrl = sum(1 for k in brand_new_coords if NEW_META[k]["role"] == "CONTROL")
    n_new_10pc = sum(1 for k in brand_new_coords if NEW_META[k]["dist_pc"] <= 10.0)
    n_bridges = len({r["canonical_target"] for r in frozen_rows if r["is_prior_bridge"] == "True"})
    proj_bytes = sum(int(r["total_bytes"]) for r in frozen_rows)

    pex_out = {
        "schema": "D102_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D102",
        "verified_utc": now_iso,
        "prior_phases_covered": "C001-C037 + D001-D101",
        "n_prior_excluded_coords": len(prior_coords),
        "n_prior_excluded_dp_ids": len(prior_dp_ids),
        "n_format_check_excluded_dp_ids": len(fmt_excl),
        "d102_total_stars": len({r["canonical_target"] for r in frozen_rows}),
        "d102_brand_new_unique_stars": len(brand_new_coords),
        "d102_prior_bridge_stars": n_bridges,
        "d102_control_stars": n_new_ctrl,
        "d102_brand_new_within_10pc": n_new_10pc,
        "d102_total_input_files": len(frozen_rows),
        "d102_projected_download_bytes": proj_bytes,
        "d102_projected_download_mib": round(proj_bytes / (1024.0 * 1024.0), 4),
        "d102_dp_id_overlap_count": 0,
        "min_brand_new_sky_separation_arcsec": round(min_prior_sep, 2),
        "min_intra_d102_separation_arcsec": round(min_intra_sep, 2),
        "star_separation_verification": star_sep_verif,
        "format_check_excluded_dp_ids": fmt_excl,
        "excluded_dp_ids": prior_dp_ids,
        "excluded_targets_coordinate_registry": prior_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pex_out, indent=2) + "\n")

    snap_out = {
        "schema": "D102_PRIOR_V5_9_PHASES_SNAPSHOT",
        "prior_phases": "C001-C037 + D001-D101",
        "source_archive_aa_name": ARCHIVE_AA_NAME,
        "source_archive_aa_sha256": ARCHIVE_AA_SHA256,
        "source_archive_aa_bundle_member": ARCHIVE_AA_BUNDLE_MEMBER,
        "source_archive_aa_bundle_sha256": ARCHIVE_AA_BUNDLE_SHA256,
        "prior_unique_stars_count": uni101["unique_stars_total"],
        "prior_science_stars_count": uni101["science_stars_total"],
        "prior_control_stars_count": uni101["control_stars_total"],
        "prior_planet_host_stars_count": uni101["planet_host_stars_total"],
        "prior_confirmed_exoplanets_count": uni101["confirmed_exoplanets_total"],
        "prior_within_10pc_count": uni101["within_10pc_unique_stars"],
        "prior_total_exposures_count": uni101["total_exposures_d079_d101"],
        "prior_cumulative_integration_hours": uni101["total_integration_hours_d079_d101"],
        "prior_calibration_trials_count": uni101["total_calibration_trials_d079_d101"],
        "prior_v2_false_alarms_eliminated_total": uni101["v2_false_alarms_eliminated_total"],
        "prior_cumulative_orbital_campaigns_count": uni101["cumulative_orbital_campaigns"],
        "prior_panchromatic_bridge_stars_count": uni101["panchromatic_bridge_stars_total"],
        "prior_revisited_control_multi_phase_stars": uni101["revisited_control_multi_phase_stars"],
        "prior_multi_phase_targets_total": uni101["multi_phase_targets_total"],
        "prior_panchromatic_bridge_cells_count": uni101["panchromatic_bridge_cells_total"],
        "prior_cumulative_comb_stacks": uni101["cumulative_comb_stacks"],
        "prior_coherent_eccentric_keplerian_campaigns": uni101["coherent_eccentric_keplerian_campaigns"],
        "d101_summary_headline": uni101,
        "prior_unified_613_rows": sx["u613"],
        "prior_bridge_76_rows": sx["br76"],
        "prior_allsky_comb_unified_rows": sx["ac_u"],
        "prior_allsky_comb_candidate_rows": sx["ac_c"],
        "prior_ellipsoid_613_rows": sx["ell613"],
    }
    (WS / "PRIOR_V5_9_PHASES_SNAPSHOT.json").write_text(json.dumps(snap_out, indent=2) + "\n")

    orb_out = {
        "schema": "D102_ORBITAL_CAMPAIGNS_AND_KINEMATICS",
        "phase_id": "D102",
        "campaign_range": "#157-#162 (live D102) + 48 prior from Archives T-Z, AA (54 DRIFT_V60 + COMB_DRIFT_V60 campaigns total)",
        "n_campaigns": len(campaigns_out),
        "campaigns": campaigns_out,
    }
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_out, indent=2) + "\n")

    stage1_files = [
        "v6_0_detector.py", "build_cohort.py", "download_inputs.py",
        "FROZEN_COHORT_D102.csv", "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json",
        "PRIOR_EXCLUSION_VERIFICATION.json", "PRIOR_V5_9_PHASES_SNAPSHOT.json",
    ]
    hashes = {fn: _sha256_file(WS / fn) for fn in stage1_files}

    ml_out = {
        "schema": "D102_PROSPECTIVE_METHOD_LOCK",
        "phase_id": "D102",
        "detector_version": "V6.0",
        "detector": "TECHNOSIGNATURE_V6_0_XRAY_EUV_POISSON_CHANDRA_EUVE_AND_ALMA_UNBROKEN_MM",
        "locked_utc": now_iso,
        "projected_unified_stars": uni101["unique_stars_total"] + len(brand_new_coords),
        "projected_within_10pc_stars": uni101["within_10pc_unique_stars"] + n_new_10pc,
        "d102_brand_new_stars": len(brand_new_coords),
        "d102_prior_bridges": n_bridges,
        "d102_total_files": len(frozen_rows),
        "d102_projected_bytes": proj_bytes,
        "d102_projected_mib": round(proj_bytes / (1024.0 * 1024.0), 4),
        "stage_1_files": hashes,
    }
    ml_path = WS / "METHOD_LOCK.json"
    ml_path.write_text(json.dumps(ml_out, indent=2) + "\n")

    lr_out = {
        "schema": "D102_LOCK_RECEIPT",
        "phase_id": "D102",
        "status": "STAGE-1 SEALED",
        "locked_utc": now_iso,
        "locked_unix_epoch": now_epoch,
        "method_lock_sha256": _sha256_file(ml_path),
        "inputs_dir_exists_at_seal": raw_dir.exists(),
        "locked_files": hashes,
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lr_out, indent=2) + "\n")

    print(
        f"Stage-1 SEALED: {len(brand_new_coords)} brand-new + {n_bridges} bridges = "
        f"{pex_out['d102_total_stars']} D102 targets ({ml_out['projected_unified_stars']} unified, "
        f"{ml_out['projected_within_10pc_stars']} <10pc), {len(frozen_rows)} files, "
        f"min_prior_sep={min_prior_sep:.2f} arcsec, min_intra_sep={min_intra_sep:.2f} arcsec, "
        f"inputs_exists={raw_dir.exists()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
