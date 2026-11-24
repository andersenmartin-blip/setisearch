#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D105 (`V6.3`) Stage-1 Prospective Method Lock & Cohort Builder.
Locks 126 target-instrument observations (82 unique physical files) across 77 targets:
  - 26 CGRO OSSE soft-to-medium gamma-ray spectra (50 keV - 9.09 MeV; 20 new CTRL + 6 bridges)
  - 20 CGRO COMPTEL Compton MeV targets across 8 viewing-period EVPs (0.75 - 30.0 MeV)
  - 40 Fermi LAT Pass-8 P305 targets across 8 weekly all-sky photon files (30 MeV - 300 GeV)
  - 10 brand-new < 10 pc optical echelle stars (1 CARMENES VIS + 4 ESO HARPS + 5 ESO FEROS)
  - 30 ESO ESPRESSO/HARPS spectra forming 6 N>=5 orbital campaigns (#175-#180)
Verifies 0 overlap with 3,576 prior dp_ids and 33 format-check probes, >=300" sky separation
from 828 prior coordinates, >=120" intra-D105 separation, HTTP 200 URLs, and absence of $RAW105
before sealing METHOD_LOCK.json and LOCK_RECEIPT.json.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent
ROOT = WS.parent.parent
RAW_DIR = ROOT / "inputs_d105_v6_3"
WS104 = ROOT / "analysis_workspace/work_v6_2_20261124_d104_soft_gamma_suzaku_gso_xrism_nicer_200star_10pc"
ARCHIVE_AD = ROOT / "archives/SETI_D104_V6_2_SOFT_GAMMA_SUZAKU_GSO_XRISM_NICER_200STAR_10PC_RESULTS_2026-11-24.zip"
BUNDLE_104 = WS104 / "bounded_inputs/d104_bounded_bundle.json.gz"

if str(WS) not in sys.path:
    sys.path.insert(0, str(WS))
import v6_3_detector as det  # noqa: E402

C_KMS = det.C_KMS
ARCHIVE_AD_SHA256 = "08169d98eb4313ea15610b8c4367f85a717cacdc10263ebd0a21e2a503cfad06"
BUNDLE_104_SHA256 = "508aa73dc61896fc1d0fec5208de9c9006a498e480a01ae7ea95115c91023c16"

FORMAT_CHECK_EXTRA_D105 = [
    "crabpulsar_1_xspec.tar.gz",
    "m16992_evp.fits.gz",
    "lat_photon_weekly_w009_p305_v001.fits",
]

# 51 Brand-new D105 target metadata (verified via Gaia DR3, NASA Exoplanet Archive, NED, CDS Sesame)
NEW_META: dict[str, dict[str, Any]] = {
    # --- 21 High-Energy Gamma-Ray Control Targets (20 OSSE + Vela Pulsar) ---
    "SN1987A":  {"common_name": "SN 1987A (LMC Supernova Remnant)",   "role": "CONTROL", "subrole": "SUPERNOVA_REMNANT_GAMMA_CAL", "sid": "SN1987A",  "ra":  83.86662, "dec": -69.26975, "pmra": 0.0, "pmdec": 0.0, "d":      51400.0, "g": 15.0, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 10000.0, "mass":  18.0, "rv":   286.5, "n_pl": 0, "tr": False, "z": 0.000956},
    "M31":      {"common_name": "M31 (Andromeda Galaxy)",             "role": "CONTROL", "subrole": "LOCAL_GROUP_GALAXY_CAL",      "sid": "M31",      "ra":  10.68479, "dec": +41.26907, "pmra": 0.0, "pmdec": 0.0, "d":     785000.0, "g":  3.4, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff":  5000.0, "mass":   1.0, "rv":  -300.0, "n_pl": 0, "tr": False, "z": -0.000991},
    "M82":      {"common_name": "M82 (Cigar Starburst Galaxy)",       "role": "CONTROL", "subrole": "STARBURST_GALAXY_GAMMA_CAL",  "sid": "M82",      "ra": 148.97050, "dec": +69.67948, "pmra": 0.0, "pmdec": 0.0, "d":    3530000.0, "g":  8.4, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff":  5500.0, "mass":   1.0, "rv":   183.0, "n_pl": 0, "tr": False, "z": 0.000610},
    "M51":      {"common_name": "M51a (Whirlpool Seyfert 2 Galaxy)",  "role": "CONTROL", "subrole": "AGN_EXTRAGALACTIC_CAL",       "sid": "M51",      "ra": 202.46963, "dec": +47.19521, "pmra": 0.0, "pmdec": 0.0, "d":    8580000.0, "g":  8.4, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff":  5200.0, "mass":   1.0, "rv":   472.0, "n_pl": 0, "tr": False, "z": 0.001573},
    "CASA":     {"common_name": "Cassiopeia A (44Ti Gamma SNR)",     "role": "CONTROL", "subrole": "SUPERNOVA_REMNANT_GAMMA_CAL", "sid": "CASA",     "ra": 350.85840, "dec": +58.81130, "pmra": 0.0, "pmdec": 0.0, "d":       3400.0, "g": 16.0, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 20000.0, "mass":  15.0, "rv":     0.0, "n_pl": 0, "tr": False},
    "CYGX1":    {"common_name": "Cygnus X-1 (Black Hole HMXB)",       "role": "CONTROL", "subrole": "BH_MICROQUASAR_GAMMA_CAL",    "sid": "2059383668236814720", "ra": 299.59032, "dec": +35.20161, "pmra": -3.8, "pmdec": -6.2, "d": 2220.0, "g": 8.5, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 31000.0, "mass": 40.0, "rv": -7.0, "n_pl": 0, "tr": False},
    "CYGX3":    {"common_name": "Cygnus X-3 (WR+Compact HMXB)",       "role": "CONTROL", "subrole": "GAMMA_MICROQUASAR_CAL",       "sid": "CYGX3",    "ra": 308.10742, "dec": +40.95775, "pmra": 0.0, "pmdec": 0.0, "d":       9700.0, "g": 15.0, "bp": None, "rp": None, "j": 12.9, "h": 12.1, "k": 11.4, "teff": 45000.0, "mass": 12.0, "rv": 0.0, "n_pl": 0, "tr": False},
    "GEMINGA":  {"common_name": "Geminga (PSR J0633+1746 Gamma PSR)", "role": "CONTROL", "subrole": "GAMMA_RAY_PULSAR_CAL",        "sid": "GEMINGA",  "ra":  98.47564, "dec": +17.77025, "pmra": 140.0, "pmdec": 110.0, "d": 250.0, "g": 25.0, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 500000.0, "mass": 1.4, "rv": 0.0, "n_pl": 0, "tr": False},
    "HERX1":    {"common_name": "Hercules X-1 (Accreting X-Ray PSR)","role": "CONTROL", "subrole": "ACCRETING_PULSAR_CAL",        "sid": "HERX1",    "ra": 254.45755, "dec": +35.34236, "pmra": 0.0, "pmdec": 0.0, "d":       6600.0, "g": 13.0, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff":  8500.0, "mass":   2.2, "rv":  -65.0, "n_pl": 0, "tr": False},
    "SCOX1":    {"common_name": "Scorpius X-1 (Prototype LMXB)",      "role": "CONTROL", "subrole": "GAMMA_LMXB_CAL",              "sid": "SCOX1",    "ra": 244.97946, "dec": -15.64028, "pmra": -7.0, "pmdec": -12.0, "d": 2130.0, "g": 12.2, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 18000.0, "mass": 1.4, "rv": -114.0, "n_pl": 0, "tr": False},
    "PSRB1957": {"common_name": "PSR B1957+20 (Black Widow Pulsar)",  "role": "CONTROL", "subrole": "MILLISECOND_GAMMA_PULSAR_CAL","sid": "PSRB1957", "ra": 299.90318, "dec": +20.80414, "pmra": -16.0, "pmdec": -25.8, "d": 1730.0, "g": 20.0, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 8000.0, "mass": 2.4, "rv": 0.0, "n_pl": 0, "tr": False},
    "PSRB1259": {"common_name": "PSR B1259-63 (Gamma Be/Pulsar)",     "role": "CONTROL", "subrole": "GAMMA_BINARY_PULSAR_CAL",     "sid": "5862299960127967488", "ra": 195.69856, "dec": -63.83573, "pmra": -7.0, "pmdec": -0.4, "d": 2600.0, "g": 9.6, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 30000.0, "mass": 15.0, "rv": 0.0, "n_pl": 0, "tr": False},
    "VELAX1":   {"common_name": "Vela X-1 (Eclipsing HMXB Pulsar)",   "role": "CONTROL", "subrole": "GAMMA_HMXB_PULSAR_CAL",       "sid": "VELAX1",   "ra": 135.52859, "dec": -40.55469, "pmra": -4.8, "pmdec":  9.3, "d": 1990.0, "g":  6.7, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 25000.0, "mass": 24.0, "rv": 0.0, "n_pl": 0, "tr": False},
    "VELAPSR":  {"common_name": "Vela Pulsar (PSR B0833-45)",         "role": "CONTROL", "subrole": "GAMMA_RAY_PULSAR_CAL",        "sid": "VELAPSR",  "ra": 128.83606, "dec": -45.17643, "pmra": -49.7, "pmdec": 29.9, "d": 287.0, "g": 23.6, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 650000.0, "mass": 1.4, "rv": 0.0, "n_pl": 0, "tr": False},
    "LMCX3":    {"common_name": "LMC X-3 (Extragalactic BH Binary)",  "role": "CONTROL", "subrole": "BH_XRAY_BINARY_CAL",          "sid": "LMCX3",    "ra":  84.73597, "dec": -64.08425, "pmra": 0.0, "pmdec": 0.0, "d":      48100.0, "g": 17.0, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 15000.0, "mass":   7.0, "rv":   310.0, "n_pl": 0, "tr": False},
    "SMCX1":    {"common_name": "SMC X-1 (Super-Eddington HMXB PSR)", "role": "CONTROL", "subrole": "GAMMA_HMXB_PULSAR_CAL",       "sid": "SMCX1",    "ra":  19.27144, "dec": -73.44334, "pmra": 0.0, "pmdec": 0.0, "d":      65000.0, "g": 13.1, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 30000.0, "mass":  17.0, "rv":   180.0, "n_pl": 0, "tr": False},
    "3C111":    {"common_name": "3C 111 (Broad-Line Radio Galaxy)",   "role": "CONTROL", "subrole": "AGN_EXTRAGALACTIC_CAL",       "sid": "3C111",    "ra":  64.58866, "dec": +38.02661, "pmra": 0.0, "pmdec": 0.0, "d":  209000000.0, "g": 18.0, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff":  6000.0, "mass":   1.0, "rv": 14390.0, "n_pl": 0, "tr": False, "z": 0.04800},
    "3C120":    {"common_name": "3C 120 (Seyfert 1 Radio Galaxy)",    "role": "CONTROL", "subrole": "AGN_EXTRAGALACTIC_CAL",       "sid": "3C120",    "ra":  68.29623, "dec":  +5.35434, "pmra": 0.0, "pmdec": 0.0, "d":  143000000.0, "g": 14.2, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff":  6000.0, "mass":   1.0, "rv":  9896.0, "n_pl": 0, "tr": False, "z": 0.03301},
    "FAIRALL9": {"common_name": "Fairall 9 (Bare Seyfert 1 AGN)",     "role": "CONTROL", "subrole": "AGN_EXTRAGALACTIC_CAL",       "sid": "FAIRALL9", "ra":  20.94072, "dec": -58.80578, "pmra": 0.0, "pmdec": 0.0, "d":  201000000.0, "g": 13.5, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff":  6000.0, "mass":   1.0, "rv": 13834.0, "n_pl": 0, "tr": False, "z": 0.046145},
    "MRK509":   {"common_name": "Mrk 509 (luminous Seyfert 1.2 AGN)", "role": "CONTROL", "subrole": "AGN_EXTRAGALACTIC_CAL",       "sid": "MRK509",   "ra": 311.04064, "dec": -10.72354, "pmra": 0.0, "pmdec": 0.0, "d":  149000000.0, "g": 13.1, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff":  6000.0, "mass":   1.0, "rv": 10312.0, "n_pl": 0, "tr": False, "z": 0.034397},
    "OJ287":    {"common_name": "OJ 287 (Binary SMBH BL Lac Blazar)", "role": "CONTROL", "subrole": "BLAZAR_EXTRAGALACTIC_CAL",    "sid": "OJ287",    "ra": 133.70365, "dec": +20.10851, "pmra": 0.0, "pmdec": 0.0, "d": 1580000000.0, "g": 14.5, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff":  6000.0, "mass":   1.0, "rv": 91616.0, "n_pl": 0, "tr": False, "z": 0.30560},

    # --- 14 Brand-New < 10 pc Fermi LAT All-Sky Targets (Gaia DR3 disjoint) ---
    "GJ1116B":      {"common_name": "GJ 1116 B (LDS 3836B, 5.10 pc)",         "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "660597997697274752",  "ra": 134.55869, "dec": +19.76258, "pmra":  -937.13, "pmdec":   -34.56, "d": 5.095, "g": 12.4856, "bp": 15.0630, "rp": 11.0246, "j": None, "h": None, "k": None, "teff": 2950.0, "mass": 0.11, "rv":  15.2604, "n_pl": 0, "tr": False},
    "SCR1540_5101": {"common_name": "SCR J1540-5101 (M5.5V, 5.33 pc)",        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "5985290231327158144", "ra": 235.19518, "dec": -51.02810, "pmra":  1949.46, "pmdec":  -324.79, "d": 5.327, "g": 12.7359, "bp": 15.5150, "rp": 11.2888, "j": None, "h": None, "k": None, "teff": 2900.0, "mass": 0.11, "rv":  85.6718, "n_pl": 0, "tr": False},
    "GJ1221":       {"common_name": "GJ 1221 (EGGR 372 White Dwarf, 6.21 pc)", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_WD",      "sid": "1638979384378696704", "ra": 267.01612, "dec": +70.88157, "pmra": -1266.39, "pmdec":  1108.80, "d": 6.211, "g": 13.7782, "bp": 14.1791, "rp": 13.1762, "j": None, "h": None, "k": None, "teff": 6500.0, "mass": 0.65, "rv":   0.0,    "n_pl": 0, "tr": False},
    "LHS2090":      {"common_name": "LHS 2090 (LP 368-128, 6.36 pc)",         "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "685103912857072640",  "ra": 135.09564, "dec": +21.83206, "pmra":  -514.94, "pmdec":  -592.25, "d": 6.359, "g": 13.4131, "bp": 16.3512, "rp": 11.9516, "j": None, "h": None, "k": None, "teff": 2800.0, "mass": 0.10, "rv":   0.0,    "n_pl": 0, "tr": False},
    "GL829":        {"common_name": "GJ 829 (Ross 775, 6.78 pc)",             "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "1784473016438653056", "ra": 322.40808, "dec": +17.64498, "pmra":  1007.04, "pmdec":   378.40, "d": 6.780, "g":  9.1085, "bp": 10.5719, "rp":  7.9174, "j": None, "h": None, "k": None, "teff": 3400.0, "mass": 0.37, "rv":   0.0,    "n_pl": 0, "tr": False},
    "GL661":        {"common_name": "GJ 661 (HD 155876, 7.60 pc)",            "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "1355264565043431040", "ra": 257.38347, "dec": +43.68011, "pmra":   332.03, "pmdec":  -274.50, "d": 7.599, "g": 10.4532, "bp": 12.0840, "rp":  9.2067, "j": None, "h": None, "k": None, "teff": 3300.0, "mass": 0.34, "rv": -21.9982, "n_pl": 0, "tr": False},
    "GJ2005":       {"common_name": "GJ 2005 (LHS 1070 Triple M, 7.73 pc)",   "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "2322561156529549440", "ra":   6.18361, "dec": -27.13726, "pmra":   -92.74, "pmdec":   695.96, "d": 7.733, "g": 13.1426, "bp": 15.5533, "rp": 11.5869, "j": None, "h": None, "k": None, "teff": 2850.0, "mass": 0.12, "rv": -28.9832, "n_pl": 0, "tr": False},
    "EGGR290":      {"common_name": "EGGR 290 (G 99-47 White Dwarf, 8.12 pc)","role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_WD",      "sid": "3320184202856435840", "ra":  89.10410, "dec":  +5.35934, "pmra":  -444.68, "pmdec":  -925.14, "d": 8.117, "g": 13.9694, "bp": 14.2963, "rp": 13.4654, "j": None, "h": None, "k": None, "teff": 5800.0, "mass": 0.71, "rv": 0.0,      "n_pl": 0, "tr": False},
    "LAWD26":       {"common_name": "LAWD 26 (BPM 4729 White Dwarf, 8.17 pc)","role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_WD",      "sid": "5273943488410008832", "ra": 118.30118, "dec": -67.79867, "pmra":  1467.12, "pmdec": -1489.72, "d": 8.169, "g": 13.7775, "bp": 14.1209, "rp": 13.2616, "j": None, "h": None, "k": None, "teff": 5700.0, "mass": 0.62, "rv": 0.0,      "n_pl": 0, "tr": False},
    "WT135":        {"common_name": "L 173-19 (WT 135, 8.22 pc)",             "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "4719430087707860736", "ra":  30.16044, "dec": -55.96826, "pmra":   113.39, "pmdec":   -69.56, "d": 8.216, "g": 10.5571, "bp": 12.1216, "rp":  9.3359, "j": None, "h": None, "k": None, "teff": 3350.0, "mass": 0.35, "rv":   1.3142, "n_pl": 0, "tr": False},
    "LAWD96":       {"common_name": "LAWD 96 (WD 2359-434, 8.33 pc)",         "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_WD",      "sid": "4994877094997259264", "ra":   0.54842, "dec": -43.16844, "pmra":   613.79, "pmdec":  -686.99, "d": 8.332, "g": 12.8952, "bp": 13.0023, "rp": 12.6928, "j": None, "h": None, "k": None, "teff": 8500.0, "mass": 0.85, "rv":   0.0,    "n_pl": 0, "tr": False},
    "SCR1138_7721": {"common_name": "SCR J1138-7721 (8.38 pc)",               "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "5224460173763882496", "ra": 174.52797, "dec": -77.36076, "pmra": -2063.83, "pmdec":   616.59, "d": 8.379, "g": 12.8162, "bp": 15.0453, "rp": 11.4569, "j": None, "h": None, "k": None, "teff": 3000.0, "mass": 0.14, "rv": -18.7367, "n_pl": 0, "tr": False},
    "LAWD28":       {"common_name": "LAWD 28 (CD-32 5613 WD, 8.52 pc)",       "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_WD",      "sid": "5639391810273308416", "ra": 130.37950, "dec": -32.93649, "pmra": -1061.16, "pmdec":  1345.90, "d": 8.518, "g": 11.8224, "bp": 11.9007, "rp": 11.6703, "j": None, "h": None, "k": None, "teff": 9100.0, "mass": 0.60, "rv":   0.0,    "n_pl": 0, "tr": False},
    "LP991_84":     {"common_name": "LP 991-84 (LHS 1289, 8.73 pc)",          "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "4960651016012601856", "ra":  24.84137, "dec": -39.60351, "pmra":   143.63, "pmdec":  -228.78, "d": 8.726, "g": 12.5684, "bp": 14.6911, "rp": 11.2238, "j": None, "h": None, "k": None, "teff": 3050.0, "mass": 0.16, "rv":  28.0106, "n_pl": 0, "tr": False},

    # --- 10 Brand-New < 10 pc Optical Echelle Stars (1 CARMENES VIS + 9 ESO HARPS/FEROS) ---
    "J07403-174":   {"common_name": "GJ 283 B (LP 783-2, 9.15 pc)",           "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "5717278911884264576", "ra": 115.08608, "dec": -17.41514, "pmra":  1152.24, "pmdec":  -536.41, "d": 9.153, "g": 13.9569, "bp": 16.8854, "rp": 12.5060, "j": None, "h": None, "k": None, "teff": 2800.0, "mass": 0.10, "rv":   0.0,    "n_pl": 0, "tr": False},
    "GJ1068":       {"common_name": "GJ 1068 (LHS 22, 7.11 pc)",              "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "4780100658292046592", "ra":  62.61100, "dec": -53.61300, "pmra":  -825.18, "pmdec": -2415.58, "d": 7.108, "g": 11.9029, "bp": 13.8092, "rp": 10.6055, "j": None, "h": None, "k": None, "teff": 3050.0, "mass": 0.14, "rv":  -0.5059, "n_pl": 0, "tr": False},
    "GJ871P1A":     {"common_name": "Fomalhaut C (LP 876-10, 7.68 pc)",       "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "6623351805412369024", "ra": 342.02034, "dec": -24.36963, "pmra":   331.61, "pmdec":  -183.80, "d": 7.676, "g": 11.1292, "bp": 12.8778, "rp":  9.8631, "j": None, "h": None, "k": None, "teff": 3130.0, "mass": 0.20, "rv":   5.7733, "n_pl": 0, "tr": False},
    "J0740118":     {"common_name": "SCR J0740-4257 (7.98 pc)",               "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "5535361753834861312", "ra": 115.04626, "dec": -42.95895, "pmra":  -483.46, "pmdec":   504.77, "d": 7.981, "g": 12.0308, "bp": 14.0734, "rp": 10.6999, "j": None, "h": None, "k": None, "teff": 2960.4, "mass": 0.15, "rv":  27.5059, "n_pl": 0, "tr": False},
    "GJ1154A":      {"common_name": "GJ 1154 (G 13-22, 8.09 pc)",             "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "3698534434669937024", "ra": 183.56473, "dec":  +0.62273, "pmra":  -951.34, "pmdec":  -284.05, "d": 8.088, "g": 11.8287, "bp": 13.8594, "rp": 10.4906, "j": None, "h": None, "k": None, "teff": 2980.0, "mass": 0.14, "rv":   0.0,    "n_pl": 0, "tr": False},
    "GL190":        {"common_name": "GJ 190 (LHS 200, 9.23 pc)",              "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "2976507997939000064", "ra":  77.14837, "dec": -18.17827, "pmra":   503.59, "pmdec": -1399.63, "d": 9.231, "g":  9.0549, "bp": 10.5505, "rp":  7.8417, "j": None, "h": None, "k": None, "teff": 3400.0, "mass": 0.44, "rv":   0.0,    "n_pl": 0, "tr": False},
    "GL84":         {"common_name": "GJ 84 (LHS 150, 9.32 pc)",               "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "5138510181584617856", "ra":  31.27628, "dec": -17.61540, "pmra":  1275.22, "pmdec":  -169.70, "d": 9.320, "g":  9.1705, "bp": 10.4362, "rp":  8.0407, "j": None, "h": None, "k": None, "teff": 3500.0, "mass": 0.45, "rv":  25.9596, "n_pl": 0, "tr": False},
    "GJ3135":       {"common_name": "GJ 3135 (LHS 1339, 9.38 pc)",            "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "5020179503252128768", "ra":  31.44961, "dec": -30.17618, "pmra":  -525.19, "pmdec":   103.98, "d": 9.380, "g": 11.0507, "bp": 12.4391, "rp":  9.8912, "j": None, "h": None, "k": None, "teff": 3121.0, "mass": 0.23, "rv":  39.8926, "n_pl": 0, "tr": False},
    "GJ1123":       {"common_name": "GJ 1123 (LHS 263, 9.52 pc)",             "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "5203276810942065536", "ra": 139.28559, "dec": -77.82675, "pmra":  -994.00, "pmdec":   362.00, "d": 9.521, "g": 11.5566, "bp": None,    "rp": None,    "j": None, "h": None, "k": None, "teff": 3020.0, "mass": 0.16, "rv":  44.2198, "n_pl": 0, "tr": False},
    "LHS1610":      {"common_name": "LHS 1610 (GJ 3253, 9.66 pc)",            "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "43574131143039104",   "ra":  58.17598, "dec": +17.01496, "pmra":   433.18, "pmdec":  -645.37, "d": 9.662, "g": 12.1761, "bp": 14.0732, "rp": 10.8709, "j": None, "h": None, "k": None, "teff": 3100.0, "mass": 0.17, "rv":  35.9639, "n_pl": 0, "tr": False},

    # --- 6 Brand-New ESO Orbits #175-#180 Exoplanet Hosts ---
    "HD22496":      {"common_name": "HD 22496",   "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "4833654227548585856", "ra":  53.75662, "dec": -48.41777, "pmra":  404.44, "pmdec":   307.50, "d": 13.5956, "g": 8.0210, "bp": 8.8026, "rp": 7.1598, "j": 6.122, "h": 5.493, "k": 5.338, "teff": 4385.0, "mass": 0.6840, "rv":  21.3826, "n_pl": 1, "tr": False, "mh": -0.08},
    "HD154088":     {"common_name": "HD 154088",  "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "6029992663310612096", "ra": 256.11643, "dec": -28.58387, "pmra":   83.31, "pmdec":  -268.61, "d": 18.2692, "g": 6.3801, "bp": 6.7774, "rp": 5.8141, "j": 5.225, "h": 4.955, "k": 4.758, "teff": 5374.0, "mass": 0.9100, "rv":  14.0823, "n_pl": 1, "tr": False, "mh":  0.28},
    "GJ740":        {"common_name": "GJ 740",     "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "4282578724832056576", "ra": 284.49969, "dec":  +5.90270, "pmra": -196.33, "pmdec": -1220.61, "d": 11.1017, "g": 8.4605, "bp": 9.4503, "rp": 7.4720, "j": 6.239, "h": 5.587, "k": 5.357, "teff": 3913.0, "mass": 0.5800, "rv":   9.9614, "n_pl": 1, "tr": False, "mh":  0.08},
    "GJ724":        {"common_name": "GJ 724",     "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "4105386688016878336", "ra": 280.23835, "dec": -13.38259, "pmra":  -94.29, "pmdec":  -671.27, "d": 16.9658, "g": 9.7722, "bp": 10.8615, "rp": 8.7370, "j": 7.397, "h": 6.728, "k": 6.546, "teff": 3799.0, "mass": 0.5271, "rv": -33.3556, "n_pl": 1, "tr": False, "mh": -0.02},
    "GJ3998":       {"common_name": "GJ 3998",    "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "4540061704989418240", "ra": 259.00203, "dec": +11.05613, "pmra": -137.43, "pmdec":  -347.46, "d": 18.1459, "g": 9.9888, "bp": 11.0733, "rp": 8.9533, "j": 7.634, "h": 7.020, "k": 6.816, "teff": 3726.0, "mass": 0.5200, "rv": -45.6179, "n_pl": 3, "tr": False, "mh": -0.13},
    "BD061339":     {"common_name": "BD-06 1339", "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "3022099969137163904", "ra":  88.25118, "dec":  -5.99639, "pmra":   -1.17, "pmdec":  -346.76, "d": 20.2695, "g": 9.1100, "bp": 9.9251, "rp": 8.2262, "j": 7.128, "h": 6.517, "k": 6.305, "teff": 4324.0, "mass": 0.7000, "rv":  22.9698, "n_pl": 2, "tr": False, "mh": -0.14},
}

# 26 CGRO OSSE *_xspec.tar.gz pointings (20 brand-new CONTROL + 6 prior bridges)
OSSE_OBS: list[tuple[str, bool, str, int, float]] = [
    ("SN1987A",  False, "phase01/vp0006_0/hilevspec/sn1987a/sn1987a_6_xspec.tar.gz",       286113, 48440.0),
    ("M31",      False, "phase02/vp0216_0/hilevspec/m31/m31_216_xspec.tar.gz",               318604, 49100.0),
    ("M82",      False, "phase01/vp0007_0/hilevspec/m82/m82_7_xspec.tar.gz",                 276480, 48460.0),
    ("M51",      False, "phase04/vp0401_0/hilevspec/m51/m51_401_xspec.tar.gz",               344423, 49680.0),
    ("CASA",     False, "phase04/vp0411_1/hilevspec/casa/casa_411_1_xspec.tar.gz",           321600, 49760.0),
    ("CYGX1",    False, "phase01/vp0002_0/hilevspec/cygx-1/cygx-1_2_xspec.tar.gz",           432388, 48400.0),
    ("CYGX3",    False, "phase01/vp0002_0/hilevspec/cygx-3/cygx-3_2_xspec.tar.gz",           432231, 48400.0),
    ("GEMINGA",  False, "phase03/vp0310_0/hilevspec/geminga/geminga_310_xspec.tar.gz",       337739, 49340.0),
    ("HERX1",    False, "phase01/vp0009_5/hilevspec/herx-1/herx-1_9_5_xspec.tar.gz",         276173, 48515.0),
    ("SCOX1",    False, "phase01/vp0005_0/hilevspec/scox-1/scox-1_5_xspec.tar.gz",           326194, 48450.0),
    ("PSRB1957", False, "phase01/vp0001_0/hilevspec/psr1957_20/psr1957_20_1_xspec.tar.gz",   341461, 48395.0),
    ("PSRB1259", False, "phase05/vp0509_0/hilevspec/psr1259-63/psr1259-63_509_xspec.tar.gz", 341410, 50060.0),
    ("VELAX1",   False, "phase01/vp0008_0/hilevspec/velax-1/velax-1_8_xspec.tar.gz",         333712, 48490.0),
    ("LMCX3",    False, "phase02/vp0215_0/hilevspec/lmcx-3/lmcx-3_215_xspec.tar.gz",         271307, 49080.0),
    ("SMCX1",    False, "phase02/vp0211_0/hilevspec/smcx-1/smcx-1_211_xspec.tar.gz",         336350, 49020.0),
    ("3C111",    False, "phase01/vp0004_0/hilevspec/3c111/3c111_4_xspec.tar.gz",             344294, 48430.0),
    ("3C120",    False, "phase01/vp0033_0/hilevspec/3c120/3c120_33_xspec.tar.gz",            344396, 48800.0),
    ("FAIRALL9", False, "phase02/vp0212_0/hilevspec/fairall9/fairall9_212_xspec.tar.gz",     341611, 49040.0),
    ("MRK509",   False, "phase02/vp0213_0/hilevspec/mrk509/mrk509_213_xspec.tar.gz",         315523, 49055.0),
    ("OJ287",    False, "phase04/vp0403_5/hilevspec/oj287/oj287_403_5_xspec.tar.gz",         318557, 49700.0),
    ("3C273",    True,  "phase01/vp0003_0/hilevspec/3c273/3c273_3_xspec.tar.gz",             507708, 48420.0),
    ("3C279",    True,  "phase01/vp0010_0/hilevspec/3c279/3c279_10_xspec.tar.gz",            528462, 48525.0),
    ("CENA",     True,  "phase01/vp0012_0/hilevspec/cena/cena_12_xspec.tar.gz",              531486, 48550.0),
    ("ETACAR",   True,  "phase01/vp0014_0/hilevspec/etacar/etacar_14_xspec.tar.gz",          345044, 48570.0),
    ("MRK421",   True,  "phase01/vp0005_0/hilevspec/mrk421/mrk421_5_xspec.tar.gz",           341325, 48450.0),
    ("WR140",    True,  "phase02/vp0212_0/hilevspec/wr140/wr140_212_xspec.tar.gz",           344756, 49040.0),
]

# 8 COMPTEL Viewing Period EVP files & 20 target assignments (off-axis <= 19.14 deg)
COMPTEL_VPS: dict[str, tuple[str, int, float]] = {
    "vp0002_0": ("phase01/vp0002_0/m16994_evp.fits.gz", 44374925, 48400.0),
    "vp0003_0": ("phase01/vp0003_0/m16897_evp.fits.gz", 62039373, 48420.0),
    "vp0004_0": ("phase01/vp0004_0/m16988_evp.fits.gz", 58846578, 48430.0),
    "vp0006_0": ("phase01/vp0006_0/m17000_evp.fits.gz", 53355215, 48440.0),
    "vp0008_0": ("phase01/vp0008_0/m17001_evp.fits.gz", 60490565, 48490.0),
    "vp0009_5": ("phase01/vp0009_5/m17015_evp.fits.gz", 37778781, 48515.0),
    "vp0012_0": ("phase01/vp0012_0/m26342_evp.fits.gz", 63457889, 48550.0),
    "vp0014_0": ("phase01/vp0014_0/m28830_evp.fits.gz", 71061835, 48570.0),
}

# (star, vp, is_prior_bridge, panchromatic_bridge)
COMPTEL_TARGETS: list[tuple[str, str, bool, bool]] = [
    # 8 shared intra-D105 controls
    ("CYGX1",      "vp0002_0", False, True),
    ("CYGX3",      "vp0002_0", False, True),
    ("SN1987A",    "vp0006_0", False, True),
    ("LMCX3",      "vp0006_0", False, False),
    ("VELAPSR",    "vp0008_0", False, True),
    ("VELAX1",     "vp0008_0", False, False),
    ("HERX1",      "vp0009_5", False, False),
    ("PSRB1259",   "vp0014_0", False, True),
    # 8 newly promoted single-phase SCIENCE bridges -> 101 SCIENCE bridges
    ("WOLF424",    "vp0003_0", True,  True),
    ("J13005+056", "vp0003_0", True,  True),
    ("HD103095",   "vp0004_0", True,  True),
    ("61UMA",      "vp0004_0", True,  True),
    ("14HER",      "vp0009_5", True,  True),
    ("GJ341",      "vp0014_0", True,  True),
    ("GJ422",      "vp0014_0", True,  True),
    ("GJ1243",     "vp0002_0", True,  True),
    # 4 super-bridges
    ("WR140",      "vp0002_0", True,  True),
    ("3C273",      "vp0003_0", True,  True),
    ("CENA",       "vp0012_0", True,  True),
    ("ETACAR",     "vp0014_0", True,  True),
]

# 8 Fermi LAT weekly P305 Pass-8 all-sky photon files (w010..w017) & 40 target extractions
FERMI_WEEKLY: list[tuple[int, str, int]] = [
    (10, "lat_photon_weekly_w010_p305_v001.fits", 57559680),
    (11, "lat_photon_weekly_w011_p305_v001.fits", 56157120),
    (12, "lat_photon_weekly_w012_p305_v001.fits", 61041600),
    (13, "lat_photon_weekly_w013_p305_v001.fits", 58394880),
    (14, "lat_photon_weekly_w014_p305_v001.fits", 58213440),
    (15, "lat_photon_weekly_w015_p305_v001.fits", 56427840),
    (16, "lat_photon_weekly_w016_p305_v001.fits", 55589760),
    (17, "lat_photon_weekly_w017_p305_v001.fits", 83966400),
]

FERMI_TARGETS: list[tuple[str, bool, bool]] = [
    # 14 brand-new < 10 pc stars (SCIENCE)
    ("GJ1116B",      False, False),
    ("SCR1540_5101", False, False),
    ("GJ1221",       False, False),
    ("LHS2090",      False, False),
    ("GL829",        False, False),
    ("GL661",        False, False),
    ("GJ2005",       False, False),
    ("EGGR290",      False, False),
    ("LAWD26",       False, False),
    ("WT135",        False, False),
    ("LAWD96",       False, False),
    ("SCR1138_7721", False, False),
    ("LAWD28",       False, False),
    ("LP991_84",     False, False),
    # 10 shared intra-D105 high-energy CONTROL targets
    ("VELAPSR",      False, True),
    ("GEMINGA",      False, False),
    ("SN1987A",      False, True),
    ("M31",          False, False),
    ("M82",          False, False),
    ("CASA",         False, False),
    ("CYGX1",        False, True),
    ("CYGX3",        False, True),
    ("PSRB1259",     False, True),
    ("PSRB1957",     False, False),
    # 6 newly promoted single-phase SCIENCE bridges -> 107 SCIENCE bridges
    ("EZAQR",        True,  True),
    ("LP73158",      True,  True),
    ("EQPEG",        True,  True),
    ("HNLIB",        True,  True),
    ("GJ4274",       True,  True),
    ("GLIESE12",     True,  True),
    # 10 super-bridges
    ("PROXIMACEN",   True,  True),
    ("ALPCENA",      True,  True),
    ("BARNARDSSTAR", True,  True),
    ("TRAPPIST1",    True,  True),
    ("TAUCET",       True,  True),
    ("EPSERI",       True,  True),
    ("WR140",        True,  True),
    ("ETACAR",       True,  True),
    ("3C273",        True,  True),
    ("CENA",         True,  True),
]

# 10 Brand-new < 10 pc optical echelle targets (1 CARMENES VIS + 4 ESO HARPS + 5 ESO FEROS)
OPTICAL_10PC_OBS: list[tuple[str, str, str, float, float, int, float]] = [
    ("J07403-174", "CARMENES_VIS", "car-20170108T00h36m40s-sci-gtoc-vis_A.fits", 57761.025463, 1800.0, 5051520, 94600.0),
    ("GJ1068",     "ESO_HARPS",    "ADP.2014-09-24T09:42:30.030",                55549.165593,  900.0,       0, 115000.0),
    ("GJ871P1A",   "ESO_FEROS",    "ADP.2023-11-09T10:41:36.485",                60243.068307,  900.0, 3081600, 48000.0),
    ("J0740118",   "ESO_FEROS",    "ADP.2016-09-23T12:25:48.366",                55527.339274, 1800.0,       0, 48000.0),
    ("GJ1154A",    "ESO_HARPS",    "ADP.2014-09-17T11:22:04.273",                54122.344656,  900.0,       0, 115000.0),
    ("GL190",      "ESO_FEROS",    "ADP.2016-09-23T09:05:28.278",                54939.982223,  800.0,       0, 48000.0),
    ("GL84",       "ESO_FEROS",    "ADP.2016-09-27T09:50:45.181",                56612.226875, 1000.0,       0, 48000.0),
    ("GJ3135",     "ESO_HARPS",    "ADP.2015-08-23T23:55:47.167",                57257.360258,  900.0,       0, 115000.0),
    ("GJ1123",     "ESO_HARPS",    "ADP.2014-10-01T10:21:00.983",                53366.324105,  900.0,       0, 115000.0),
    ("LHS1610",    "ESO_FEROS",    "ADP.2016-09-27T09:50:38.561",                56295.124748, 1600.0,       0, 48000.0),
]

# 6 brand-new ESO Orbits #175-#180 (5 distinct-night spectra each = 30 spectra)
ESO_ORBIT_CAMPAIGNS: list[dict[str, Any]] = [
    {
        "campaign_order": 175, "star": "HD22496", "instrument": "ESO_ESPRESSO", "grating": "ESPRESSO_377_790NM", "r": 140000.0,
        "orb_per_days": 5.09071, "orb_ecc": 0.000, "orb_omega_deg": 90.0, "orb_t0_bjd": 2458602.56, "kp_kms": 0.00262,
        "exposures": [
            ("ADP.2021-04-13T12:52:06.154", 58416.089162, 900.0, 205.9, 37379520),
            ("ADP.2021-09-03T08:21:56.549", 59207.096460, 900.0, 229.7, 37382400),
            ("ADP.2021-09-17T12:11:11.691", 59435.281664, 900.0, 225.2, 37382400),
            ("ADP.2024-01-04T15:42:31.597", 60304.123644, 900.0, 216.1, 37382400),
            ("ADP.2024-10-08T11:23:35.540", 60560.203601, 900.0, 167.1, 37382400),
        ],
    },
    {
        "campaign_order": 176, "star": "HD154088", "instrument": "ESO_ESPRESSO", "grating": "ESPRESSO_377_790NM", "r": 140000.0,
        "orb_per_days": 18.56, "orb_ecc": 0.344, "orb_omega_deg": 90.0, "orb_t0_bjd": 2458500.00, "kp_kms": 0.00170,
        "exposures": [
            ("ADP.2021-04-15T09:00:13.172", 58524.365482,  900.0, 567.1, 17812800),
            ("ADP.2021-04-27T18:50:32.272", 58908.348942,  900.0, 746.6, 17812800),
            ("ADP.2021-09-17T12:21:15.551", 59436.985304,  900.0, 747.7, 17815680),
            ("ADP.2023-03-03T13:17:07.164", 60000.339361, 1200.0, 791.3, 17818560),
            ("ADP.2023-05-30T10:48:22.774", 60076.125705, 1200.0, 573.8, 17818560),
        ],
    },
    {
        "campaign_order": 177, "star": "GJ740", "instrument": "ESO_HARPS", "grating": "HARPS_378_691NM", "r": 115000.0,
        "orb_per_days": 2.37756, "orb_ecc": 0.240, "orb_omega_deg": -41.0, "orb_t0_bjd": 2458500.00, "kp_kms": 0.00213,
        "exposures": [
            ("ADP.2014-09-18T12:12:09.093", 54647.198413, 300.0, 34.1, 0),
            ("ADP.2014-09-23T11:00:42.097", 54941.370752, 900.0, 74.9, 0),
            ("ADP.2014-09-25T15:35:25.580", 55654.411646, 900.0, 56.5, 0),
            ("ADP.2014-09-25T15:36:11.537", 55835.989121, 900.0, 62.4, 0),
            ("ADP.2018-04-10T14:59:42.583", 58217.411419, 900.0, 43.1, 5264640),
        ],
    },
    {
        "campaign_order": 178, "star": "GJ724", "instrument": "ESO_HARPS", "grating": "HARPS_378_691NM", "r": 115000.0,
        "orb_per_days": 5.101284, "orb_ecc": 0.577, "orb_omega_deg": 33.2, "orb_t0_bjd": 2458500.00, "kp_kms": 0.00748,
        "exposures": [
            ("ADP.2014-09-18T12:10:00.250", 54565.416373, 300.0, 16.5, 0),
            ("ADP.2014-09-18T12:12:28.847", 54675.160548, 900.0, 20.5, 0),
            ("ADP.2014-09-18T12:17:28.830", 54745.049350, 900.0, 24.0, 0),
            ("ADP.2014-09-18T12:11:23.977", 54767.999244, 900.0, 32.1, 0),
            ("ADP.2014-09-26T16:53:22.587", 55989.394959, 900.0, 26.5, 0),
        ],
    },
    {
        "campaign_order": 179, "star": "GJ3998", "instrument": "ESO_HARPS", "grating": "HARPS_378_691NM", "r": 115000.0,
        "orb_per_days": 13.727, "orb_ecc": 0.000, "orb_omega_deg": 90.0, "orb_t0_bjd": 2460196.96, "kp_kms": 0.00286,
        "exposures": [
            ("ADP.2014-09-18T12:10:11.070", 54570.375303, 300.0, 14.3, 0),
            ("ADP.2014-09-18T12:12:04.417", 54661.176220, 900.0, 28.1, 0),
            ("ADP.2014-09-18T12:12:47.877", 54662.179117, 900.0, 18.8, 0),
            ("ADP.2014-09-18T12:10:32.173", 54664.145740, 900.0, 20.8, 0),
            ("ADP.2014-09-18T12:17:18.717", 54665.176336, 900.0, 20.0, 0),
        ],
    },
    {
        "campaign_order": 180, "star": "BD061339", "instrument": "ESO_HARPS", "grating": "HARPS_378_691NM", "r": 115000.0,
        "orb_per_days": 125.94, "orb_ecc": 0.310, "orb_omega_deg": 41.0, "orb_t0_bjd": 2458500.00, "kp_kms": 0.00910,
        "exposures": [
            ("ADP.2014-10-01T10:23:23.147", 53288.371279, 400.0, 44.6, 0),
            ("ADP.2014-09-17T11:22:08.517", 54227.964491, 400.0, 11.0, 0),
            ("ADP.2014-09-24T09:43:05.857", 55229.095701, 900.0, 47.4, 0),
            ("ADP.2014-09-26T16:51:37.390", 56166.407718, 900.0, 36.1, 0),
            ("ADP.2014-09-26T16:54:17.617", 56259.182220, 900.0, 42.9, 0),
        ],
    },
]

COHORT_COLS = [
    "instrument", "canonical_target", "common_name", "role", "subrole", "science_track",
    "panchromatic_bridge", "is_prior_bridge", "gaia_source_id", "s_ra", "s_dec",
    "pmra_mas_yr", "pmdec_mas_yr", "dist_pc", "within_10pc", "phot_g_mag", "phot_bp_mag",
    "phot_rp_mag", "j_mag", "h_mag", "ks_mag", "teff_k", "mh_dex", "stellar_mass_msun",
    "prior_rv_kms", "n_exoplanets", "has_transiting_planet", "ecliptic_lat_deg",
    "sn1987a_dt_days", "gw170817_dt_days", "sn2023ixf_dt_days", "ppo_align_score",
    "epoch_rank", "dp_id", "grating", "resolving_power", "mjd_obs", "t_exptime",
    "phase_window", "signed_phase", "planet_orbital_rv_kms", "f1_id", "f1_rel",
    "f1_url", "f1_bytes", "total_bytes", "extra_files",
]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _ang_sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    c = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c)))) * 3600.0


def _kepler_rv(mjd_obs: float, per_d: float, ecc: float, omega_deg: float, t0_bjd: float, k_kms: float) -> tuple[float, float, str]:
    bjd = float(mjd_obs) + 2400000.5
    phi = ((bjd - t0_bjd) / per_d) % 1.0
    signed_phi = phi - 1.0 if phi > 0.5 else phi
    m_anom = 2.0 * math.pi * phi
    e_anom = m_anom
    for _ in range(12):
        e_anom = m_anom + ecc * math.sin(e_anom)
    nu = 2.0 * math.atan2(math.sqrt(1.0 + ecc) * math.sin(0.5 * e_anom), math.sqrt(max(1e-9, 1.0 - ecc)) * math.cos(0.5 * e_anom))
    w_rad = math.radians(omega_deg)
    rv_kms = float(k_kms) * (math.cos(nu + w_rad) + ecc * math.cos(w_rad))
    win = "QUAD" if 0.15 <= abs(signed_phi) <= 0.35 else ("CONJ" if abs(signed_phi) <= 0.10 or abs(signed_phi) >= 0.40 else "INTM")
    return round(signed_phi, 5), round(rv_kms, 6), win


def _http_head(url: str) -> tuple[int, int]:
    last_exc: Exception | None = None
    for attempt in range(6):
        method = "HEAD" if attempt % 2 == 0 else "GET"
        headers = {"User-Agent": "SETI-V6.3-D105-Lock/1.0", "Connection": "close"}
        if method == "GET":
            headers["Range"] = "bytes=0-0"
        try:
            req = urllib.request.Request(url, method=method, headers=headers)
            with urllib.request.urlopen(req, timeout=45) as resp:
                status = int(resp.status)
                cr = resp.headers.get("Content-Range", "")
                if "/" in cr:
                    tail = cr.rsplit("/", 1)[-1].strip()
                    if tail.isdigit():
                        return (200 if status == 206 else status), int(tail)
                cl = resp.headers.get("Content-Length", "0")
                return (200 if status == 206 else status), int(cl) if cl and cl.isdigit() else 0
        except Exception as exc:
            last_exc = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"HEAD/Range check failed after retries ({url}): {last_exc}")


def _star_meta(canon: str, is_prior: bool, u_map: dict[str, dict[str, str]], coord_by_star: dict[str, tuple[float, float]]) -> dict[str, Any]:
    if is_prior:
        u = u_map[canon]
        ra, dec = coord_by_star[canon]
        d = float(u["dist_pc"])
        return {
            "common_name": u["common_name"],
            "role": u["role"],
            "subrole": u["subrole"],
            "sid": canon,
            "ra": ra,
            "dec": dec,
            "pmra": 0.0,
            "pmdec": 0.0,
            "d": d,
            "within_10pc": str(u["within_10pc"]).lower() == "true",
            "g": u.get("phot_g_mag") or "",
            "bp": "",
            "rp": "",
            "j": u.get("j_mag") or "",
            "h": u.get("h_mag") or "",
            "k": u.get("ks_mag") or "",
            "teff": float(u["teff_k"]) if u.get("teff_k") else 5000.0,
            "mh": 0.0,
            "mass": 1.0,
            "rv": 0.0,
            "n_pl": int(float(u.get("n_exoplanets") or 0)),
            "tr": False,
        }
    m = NEW_META[canon]
    return {
        "common_name": m["common_name"],
        "role": m["role"],
        "subrole": m["subrole"],
        "sid": m["sid"],
        "ra": float(m["ra"]),
        "dec": float(m["dec"]),
        "pmra": float(m["pmra"]),
        "pmdec": float(m["pmdec"]),
        "d": float(m["d"]),
        "within_10pc": float(m["d"]) < 10.0,
        "g": "" if m["g"] is None else f"{float(m['g']):.4f}",
        "bp": "" if m["bp"] is None else f"{float(m['bp']):.4f}",
        "rp": "" if m["rp"] is None else f"{float(m['rp']):.4f}",
        "j": "" if m["j"] is None else f"{float(m['j']):.3f}",
        "h": "" if m["h"] is None else f"{float(m['h']):.3f}",
        "k": "" if m["k"] is None else f"{float(m['k']):.3f}",
        "teff": float(m["teff"]),
        "mh": float(m.get("mh", 0.0)),
        "mass": float(m["mass"]),
        "rv": float(m["rv"]),
        "n_pl": int(m["n_pl"]),
        "tr": bool(m["tr"]),
    }


def _make_row(
    *,
    inst: str,
    canon: str,
    meta: dict[str, Any],
    is_prior_bridge: bool,
    panchromatic_bridge: bool,
    science_track: str,
    epoch_rank: int,
    dp_id: str,
    grating: str,
    resolving_power: float,
    mjd_obs: float,
    t_exptime: float,
    phase_window: str,
    signed_phase: float,
    planet_orbital_rv_kms: float,
    f1_rel: str,
    f1_url: str,
    f1_bytes: int,
    total_bytes: int | None = None,
    extra_files_json: str = "[]",
) -> dict[str, Any]:
    sync = det.compute_multievent_sync_v51(meta["ra"], meta["dec"], meta["d"], mjd_obs)
    return {
        "instrument": inst,
        "canonical_target": canon,
        "common_name": meta["common_name"],
        "role": meta["role"],
        "subrole": meta["subrole"],
        "science_track": science_track,
        "panchromatic_bridge": str(panchromatic_bridge),
        "is_prior_bridge": str(is_prior_bridge),
        "gaia_source_id": meta["sid"],
        "s_ra": f"{meta['ra']:.7f}",
        "s_dec": f"{meta['dec']:.7f}",
        "pmra_mas_yr": f"{meta['pmra']:.3f}",
        "pmdec_mas_yr": f"{meta['pmdec']:.3f}",
        "dist_pc": f"{meta['d']:.5f}",
        "within_10pc": str(meta["within_10pc"]),
        "phot_g_mag": meta["g"],
        "phot_bp_mag": meta["bp"],
        "phot_rp_mag": meta["rp"],
        "j_mag": meta["j"],
        "h_mag": meta["h"],
        "ks_mag": meta["k"],
        "teff_k": f"{meta['teff']:.1f}",
        "mh_dex": f"{meta['mh']:.3f}",
        "stellar_mass_msun": f"{meta['mass']:.4f}",
        "prior_rv_kms": f"{meta['rv']:.4f}",
        "n_exoplanets": str(meta["n_pl"]),
        "has_transiting_planet": str(meta["tr"]),
        "ecliptic_lat_deg": f"{sync['ecliptic_lat_deg']:.5f}",
        "sn1987a_dt_days": f"{sync['sn1987a_dt_days']:.3f}",
        "gw170817_dt_days": f"{sync['gw170817_dt_days']:.3f}",
        "sn2023ixf_dt_days": f"{sync['sn2023ixf_dt_days']:.3f}",
        "ppo_align_score": "1.0",
        "epoch_rank": str(epoch_rank),
        "dp_id": dp_id,
        "grating": grating,
        "resolving_power": f"{resolving_power:.1f}",
        "mjd_obs": f"{mjd_obs:.6f}",
        "t_exptime": f"{t_exptime:.3f}",
        "phase_window": phase_window,
        "signed_phase": f"{signed_phase:.5f}",
        "planet_orbital_rv_kms": f"{planet_orbital_rv_kms:.6f}",
        "f1_id": dp_id,
        "f1_rel": f1_rel,
        "f1_url": f1_url,
        "f1_bytes": str(f1_bytes),
        "total_bytes": str(f1_bytes if total_bytes is None else total_bytes),
        "extra_files": extra_files_json,
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    if RAW_DIR.exists():
        raise RuntimeError(f"Chronology violation: {RAW_DIR} must NOT exist before Stage-1 seal!")

    ad_sha = _sha256_file(ARCHIVE_AD)
    b104_sha = _sha256_file(BUNDLE_104)
    if ad_sha != ARCHIVE_AD_SHA256 or b104_sha != BUNDLE_104_SHA256:
        raise RuntimeError(f"Archive AD or d104 bundle SHA mismatch ({ad_sha}, {b104_sha})")

    pe104 = json.loads((WS104 / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    d104_cohort = _read_csv(WS104 / "FROZEN_COHORT_D104.csv")
    u755_rows = _read_csv(WS104 / "results/UNIFIED_PANCHROMATIC_V6_2_SYNTHESIS_755STARS.csv")
    br1184_rows = _read_csv(WS104 / "results/PANCHROMATIC_BRIDGE_93STARS_V62.csv")
    comb_u523_rows = _read_csv(WS104 / "results/ALLSKY_COMB_V4_1_UNIFIED_D079_D104.csv")
    comb_c_rows = _read_csv(WS104 / "results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D104.csv")
    ell755_rows = _read_csv(WS104 / "results/MULTIEVENT_ELLIPSOID_755STARS.csv")
    s104 = json.loads((WS104 / "results/SUMMARY.json").read_text(encoding="utf-8"))

    u_map = {r["star"]: r for r in u755_rows}
    coord_by_star: dict[str, tuple[float, float]] = {
        r["star"]: (float(r["ra_deg"]), float(r["dec_deg"])) for r in ell755_rows
    }
    for t in pe104["excluded_targets_coordinate_registry"]:
        nm = str(t.get("canonical_target") or "").strip()
        if nm and nm not in coord_by_star:
            coord_by_star[nm] = (float(t["ra_deg"]), float(t["dec_deg"]))
    for r in d104_cohort:
        nm = r["canonical_target"]
        if nm not in coord_by_star:
            coord_by_star[nm] = (float(r["s_ra"]), float(r["s_dec"]))

    prior_coords: list[dict[str, Any]] = list(pe104["excluded_targets_coordinate_registry"])
    seen_d104_new = set()
    for r in d104_cohort:
        if str(r["is_prior_bridge"]).lower() not in ("true", "1", "yes"):
            nm = r["canonical_target"]
            if nm not in seen_d104_new:
                seen_d104_new.add(nm)
                prior_coords.append({"canonical_target": nm, "ra_deg": float(r["s_ra"]), "dec_deg": float(r["s_dec"])})

    prior_dp_ids = sorted(set(pe104["excluded_dp_ids"]) | {r["dp_id"] for r in d104_cohort})
    format_probes = sorted(set(pe104["format_check_excluded_dp_ids"]) | set(FORMAT_CHECK_EXTRA_D105))
    assert len(prior_coords) == 828, f"Expected 828 prior coords, got {len(prior_coords)}"
    assert len(prior_dp_ids) == 3576, f"Expected 3576 prior dp_ids, got {len(prior_dp_ids)}"
    assert len(format_probes) == 33, f"Expected 33 format probes, got {len(format_probes)}"

    rows: list[dict[str, Any]] = []

    # 1. 26 CGRO OSSE observations
    for canon, is_b, rel, sz, mjd in OSSE_OBS:
        if is_b:
            assert canon in u_map, f"Missing OSSE bridge {canon}"
        meta = _star_meta(canon, is_b, u_map, coord_by_star)
        url = f"https://heasarc.gsfc.nasa.gov/FTP/compton/data/osse/{rel}"
        tar_name = rel.rsplit("/", 1)[-1]
        rows.append(_make_row(
            inst="CGRO_OSSE", canon=canon, meta=meta, is_prior_bridge=is_b, panchromatic_bridge=True,
            science_track="CGRO_OSSE_MEV_GAMMA_V63", epoch_rank=1, dp_id=f"OSSE_{tar_name}", grating="OSSE_50KEV_9MEV",
            resolving_power=15.0, mjd_obs=mjd, t_exptime=200000.0, phase_window="NONE", signed_phase=0.0,
            planet_orbital_rv_kms=0.0, f1_rel=f"CGRO_OSSE/{canon}/{tar_name}",
            f1_url=url, f1_bytes=sz,
        ))

    # 2. 20 CGRO COMPTEL target extractions across 8 VP EVP files
    for canon, vp, is_b, is_pb in COMPTEL_TARGETS:
        if is_b:
            assert canon in u_map, f"Missing COMPTEL bridge {canon}"
        meta = _star_meta(canon, is_b, u_map, coord_by_star)
        rel_vp, sz_vp, mjd_vp = COMPTEL_VPS[vp]
        evp_name = rel_vp.rsplit("/", 1)[-1]
        url = f"https://heasarc.gsfc.nasa.gov/FTP/compton/data/comptel/{rel_vp}"
        rows.append(_make_row(
            inst="CGRO_COMPTEL", canon=canon, meta=meta, is_prior_bridge=is_b, panchromatic_bridge=bool(is_b or is_pb),
            science_track="CGRO_COMPTEL_MEV_V63", epoch_rank=1, dp_id=f"CGRO_COMPTEL_{vp}_{canon}", grating="COMPTEL_0P75_30MEV",
            resolving_power=14.0, mjd_obs=mjd_vp, t_exptime=400000.0, phase_window="NONE", signed_phase=0.0,
            planet_orbital_rv_kms=0.0, f1_rel=f"CGRO_COMPTEL/{vp}/{evp_name}",
            f1_url=url, f1_bytes=sz_vp,
        ))

    # 3. 40 Fermi LAT Pass-8 target extractions across 8 weekly all-sky photon files
    fermi_base_url = "https://heasarc.gsfc.nasa.gov/FTP/fermi/data/lat/weekly/photon/"
    w0_num, w0_fn, w0_sz = FERMI_WEEKLY[0]
    extra_fermi = json.dumps([
        {"rel": f"FERMI_LAT/weekly/{fn}", "url": f"{fermi_base_url}{fn}", "bytes": sz}
        for _, fn, sz in FERMI_WEEKLY[1:]
    ])
    fermi_tot_sz = sum(sz for _, _, sz in FERMI_WEEKLY)
    for canon, is_b, is_pb in FERMI_TARGETS:
        if is_b:
            assert canon in u_map, f"Missing Fermi LAT bridge {canon}"
        meta = _star_meta(canon, is_b, u_map, coord_by_star)
        rows.append(_make_row(
            inst="FERMI_LAT", canon=canon, meta=meta, is_prior_bridge=is_b, panchromatic_bridge=bool(is_b or is_pb),
            science_track="FERMI_LAT_PASS8_GEV_V63", epoch_rank=1, dp_id=f"FERMI_LAT_W010_W017_{canon}", grating="LAT_30MEV_300GEV",
            resolving_power=6.0, mjd_obs=54720.0, t_exptime=700000.0, phase_window="NONE", signed_phase=0.0,
            planet_orbital_rv_kms=0.0, f1_rel=f"FERMI_LAT/weekly/{w0_fn}",
            f1_url=f"{fermi_base_url}{w0_fn}", f1_bytes=w0_sz, total_bytes=fermi_tot_sz, extra_files_json=extra_fermi,
        ))

    # 4. 10 brand-new < 10 pc optical echelle spectra (CARMENES_VIS, ESO_HARPS, ESO_FEROS)
    for canon, inst, ref_id, mjd, exp_s, sz, r_pow in OPTICAL_10PC_OBS:
        meta = _star_meta(canon, False, u_map, coord_by_star)
        if inst == "CARMENES_VIS":
            url = f"https://dc.g-vo.org/carmenes/q/sdl/static/{canon}/{ref_id}"
            dp_id = f"CARM_{ref_id}"
            gr = "CARMENES_VIS_520_960NM"
            frel = f"CARMENES_VIS/{canon}/{ref_id}"
        else:
            url = f"https://dataportal.eso.org/dataportal_new/file/{ref_id}"
            dp_id = ref_id
            gr = "HARPS_378_691NM" if inst == "ESO_HARPS" else "FEROS_352_921NM"
            frel = f"{inst}/{canon}/{ref_id}.fits"
        rows.append(_make_row(
            inst=inst, canon=canon, meta=meta, is_prior_bridge=False, panchromatic_bridge=False,
            science_track="SOLAR_NEIGHBORHOOD_10PC_V63", epoch_rank=1, dp_id=dp_id,
            grating=gr, resolving_power=r_pow, mjd_obs=mjd, t_exptime=exp_s,
            phase_window="NONE", signed_phase=0.0, planet_orbital_rv_kms=0.0,
            f1_rel=frel, f1_url=url, f1_bytes=sz,
        ))

    # 5. 6 brand-new ESO Orbits #175-#180 (30 spectra)
    orbital_campaigns: dict[str, Any] = {}
    for camp in ESO_ORBIT_CAMPAIGNS:
        canon = camp["star"]
        meta = _star_meta(canon, False, u_map, coord_by_star)
        inst = camp["instrument"]
        camp_exps = []
        mjs, rvs = [], []
        for idx, (dp_id, mjd, exp_s, snr, sz) in enumerate(camp["exposures"], 1):
            sphi, rv_orb, win = _kepler_rv(mjd, camp["orb_per_days"], camp["orb_ecc"], camp["orb_omega_deg"], camp["orb_t0_bjd"], camp["kp_kms"])
            url = f"https://dataportal.eso.org/dataportal_new/file/{dp_id}"
            rows.append(_make_row(
                inst=inst, canon=canon, meta=meta, is_prior_bridge=False, panchromatic_bridge=False,
                science_track=f"ORBITAL_CAMPAIGN_V63_{camp['campaign_order']}", epoch_rank=idx, dp_id=dp_id,
                grating=camp["grating"], resolving_power=camp["r"], mjd_obs=mjd, t_exptime=exp_s,
                phase_window=win, signed_phase=sphi, planet_orbital_rv_kms=rv_orb,
                f1_rel=f"{inst}/{canon}/{dp_id}.fits", f1_url=url, f1_bytes=sz,
            ))
            camp_exps.append({
                "dp_id": dp_id, "mjd_obs": mjd, "bjd_tdb_est": round(mjd + 2400000.5, 6),
                "snr": snr, "signed_phase": sphi, "phase_window": win, "planet_orbital_rv_kms": rv_orb,
            })
            mjs.append(mjd)
            rvs.append(rv_orb)
        orbital_campaigns[canon] = {
            "campaign_order": camp["campaign_order"], "phase_id": "D105",
            "canonical_target": canon, "common_name": meta["common_name"],
            "instrument": inst, "grating": camp["grating"],
            "orb_per_days": camp["orb_per_days"], "orb_ecc": camp["orb_ecc"],
            "orb_omega_deg": camp["orb_omega_deg"], "orb_t0_bjd": camp["orb_t0_bjd"],
            "kp_kms": camp["kp_kms"], "exposures": camp_exps, "n_epochs": len(camp_exps),
            "baseline_days": round(max(mjs) - min(mjs), 4),
            "orbital_dv_span_kms": round(max(rvs) - min(rvs), 6),
        }

    # Strict exclusions, separations & HTTP 200 verification
    dp_set = {r["dp_id"] for r in rows}
    assert len(rows) == 126 and len(dp_set) == 126, f"Expected 126 unique obs, got {len(rows)}/{len(dp_set)}"
    overlap_dp = dp_set & (set(prior_dp_ids) | set(format_probes))
    assert not overlap_dp, f"dp_id overlap detected: {overlap_dp}"

    # Verify unique physical files count == 82 and check no physical file overlaps format_probes
    phys_urls: dict[str, tuple[str, int]] = {}
    for r in rows:
        phys_urls[r["f1_rel"]] = (r["f1_url"], int(r["f1_bytes"]))
        for ex in json.loads(r["extra_files"]):
            phys_urls[ex["rel"]] = (ex["url"], int(ex["bytes"]))
    assert len(phys_urls) == 82, f"Expected 82 physical files, got {len(phys_urls)}"
    for rel in phys_urls:
        bn = rel.rsplit("/", 1)[-1]
        assert bn not in set(format_probes), f"Format check probe leaked into cohort: {bn}"

    brand_new_stars = sorted({r["canonical_target"] for r in rows if r["is_prior_bridge"] == "False"})
    bridge_stars = sorted({r["canonical_target"] for r in rows if r["is_prior_bridge"] == "True"})
    assert len(brand_new_stars) == 51, f"Expected 51 brand-new stars, got {len(brand_new_stars)}"
    assert len(bridge_stars) == 26, f"Expected 26 prior bridges, got {len(bridge_stars)}"

    bn_coords = {s: (NEW_META[s]["ra"], NEW_META[s]["dec"]) for s in brand_new_stars}
    sep_verif = []
    min_prior_sep = 1e9
    for s, (ra, dec) in bn_coords.items():
        best_p, best_nm = 1e9, ""
        for t in prior_coords:
            sp = _ang_sep_arcsec(ra, dec, float(t["ra_deg"]), float(t["dec_deg"]))
            if sp < best_p:
                best_p, best_nm = sp, str(t.get("canonical_target") or "")
        min_prior_sep = min(min_prior_sep, best_p)
        sep_verif.append({"star": s, "min_prior_sep_arcsec": round(best_p, 2), "nearest_prior": best_nm})
        assert best_p >= 300.0, f"Brand-new star {s} too close to prior {best_nm}: {best_p:.2f}'' < 300''"

    min_intra_sep = 1e9
    for i, s1 in enumerate(brand_new_stars):
        for s2 in brand_new_stars[i + 1:]:
            sp = _ang_sep_arcsec(bn_coords[s1][0], bn_coords[s1][1], bn_coords[s2][0], bn_coords[s2][1])
            min_intra_sep = min(min_intra_sep, sp)
            assert sp >= 120.0, f"Intra-D105 overlap {s1}/{s2}: {sp:.2f}'' < 120''"

    # Live HTTP 200 verification on all 82 unique physical URLs BEFORE sealing
    phys_list = sorted(phys_urls.items())
    print(f"Verifying HTTP 200 on all {len(phys_list)} unique D105 physical URLs...", flush=True)
    with ThreadPoolExecutor(max_workers=4) as ex:
        head_res = []
        for idx, res in enumerate(ex.map(lambda it: (it[0], it[1][0], *_http_head(it[1][0]), it[1][1]), phys_list), 1):
            head_res.append(res)
            if idx % 20 == 0 or idx == len(phys_list):
                print(f"  verified {idx}/{len(phys_list)} URLs...", flush=True)
    for rel, u, st, b, exp_b in head_res:
        assert st == 200, f"HEAD failed {rel} ({u}): HTTP {st}"
        if exp_b > 0 and b > 0:
            assert b == exp_b, f"HEAD bytes mismatch {rel}: got {b}, expected {exp_b}"
    print("All 82/82 physical URLs verified HTTP 200.")

    with open(WS / "FROZEN_COHORT_D105.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COHORT_COLS)
        w.writeheader()
        w.writerows(rows)

    tot_bytes = sum(sz for _, (_, sz) in phys_list)
    n_new_10pc = sum(1 for s in brand_new_stars if NEW_META[s]["d"] < 10.0)
    assert n_new_10pc == 24, f"Expected +24 new <10 pc stars (206 -> 230), got {n_new_10pc}"

    now_utc = datetime.now(timezone.utc)
    locked_utc = now_utc.isoformat()
    locked_epoch = now_utc.timestamp()

    pe_out = {
        "schema": "D105_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D105",
        "verified_utc": locked_utc,
        "prior_phases_covered": "C001-C037 + D001-D104",
        "n_prior_excluded_coords": len(prior_coords),
        "n_prior_excluded_dp_ids": len(prior_dp_ids),
        "n_format_check_excluded_dp_ids": len(format_probes),
        "d105_total_stars": len(brand_new_stars) + len(bridge_stars),
        "d105_brand_new_unique_stars": len(brand_new_stars),
        "d105_prior_bridge_stars": len(bridge_stars),
        "d105_control_stars": sum(1 for s in brand_new_stars if NEW_META[s]["role"] == "CONTROL") + sum(1 for s in bridge_stars if u_map[s]["role"] == "CONTROL"),
        "d105_brand_new_within_10pc": n_new_10pc,
        "d105_total_observations": len(rows),
        "d105_total_physical_files": len(phys_urls),
        "d105_projected_download_bytes": tot_bytes,
        "d105_projected_download_mib": round(tot_bytes / (1024.0 * 1024.0), 3),
        "d105_dp_id_overlap_count": 0,
        "min_brand_new_sky_separation_arcsec": round(min_prior_sep, 2),
        "min_intra_d105_separation_arcsec": round(min_intra_sep, 2),
        "star_separation_verification": sep_verif,
        "format_check_excluded_dp_ids": format_probes,
        "excluded_dp_ids": prior_dp_ids,
        "excluded_targets_coordinate_registry": prior_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pe_out, indent=2) + "\n", encoding="utf-8")

    uni104 = s104["unified_755star_panchromatic_v6_2_synthesis"]
    snap_out = {
        "schema": "D105_PRIOR_V6_2_PHASES_SNAPSHOT",
        "prior_phases": "C001-C037 + D001-D104",
        "source_archive_ad_name": ARCHIVE_AD.name,
        "source_archive_ad_sha256": ARCHIVE_AD_SHA256,
        "source_archive_ad_bundle_member": "work_v6_2_20261124_d104_soft_gamma_suzaku_gso_xrism_nicer_200star_10pc/bounded_inputs/d104_bounded_bundle.json.gz",
        "source_archive_ad_bundle_sha256": BUNDLE_104_SHA256,
        "prior_unique_stars_count": len(u755_rows),
        "prior_science_stars_count": int(uni104["science_stars_total"]),
        "prior_control_stars_count": int(uni104["control_stars_total"]),
        "prior_planet_host_stars_count": int(uni104["planet_host_stars_total"]),
        "prior_confirmed_exoplanets_count": int(uni104["confirmed_exoplanets_total"]),
        "prior_within_10pc_count": int(uni104["within_10pc_unique_stars"]),
        "prior_total_exposures_count": int(uni104["total_exposures_d079_d104"]),
        "prior_cumulative_integration_hours": float(uni104["total_integration_hours_d079_d104"]),
        "prior_calibration_trials_count": int(uni104["total_calibration_trials_d079_d104"]),
        "prior_v2_false_alarms_eliminated_total": int(uni104["v2_false_alarms_eliminated_total"]),
        "prior_cumulative_orbital_campaigns_count": int(uni104["cumulative_orbital_campaigns"]),
        "prior_panchromatic_bridge_stars_count": int(uni104["panchromatic_bridge_stars_total"]),
        "prior_revisited_control_multi_phase_stars": int(uni104["revisited_control_multi_phase_stars"]),
        "prior_multi_phase_targets_total": int(uni104["multi_phase_targets_total"]),
        "prior_panchromatic_bridge_cells_count": int(uni104["panchromatic_bridge_cells_total"]),
        "prior_cumulative_comb_stacks": int(uni104["cumulative_comb_stacks"]),
        "prior_coherent_eccentric_keplerian_campaigns": int(uni104["coherent_eccentric_keplerian_campaigns"]),
        "d104_summary_headline": uni104,
        "prior_unified_755_rows": u755_rows,
        "prior_bridge_93_rows": br1184_rows,
        "prior_allsky_comb_unified_rows": comb_u523_rows,
        "prior_allsky_comb_candidate_rows": comb_c_rows,
        "prior_ellipsoid_755_rows": ell755_rows,
    }
    (WS / "PRIOR_V6_2_PHASES_SNAPSHOT.json").write_text(json.dumps(snap_out, indent=2) + "\n", encoding="utf-8")

    orb_out = {
        "schema": "D105_ORBITAL_CAMPAIGNS_AND_KINEMATICS",
        "phase_id": "D105",
        "campaign_range": [175, 180],
        "campaigns": orbital_campaigns,
    }
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_out, indent=2) + "\n", encoding="utf-8")

    stage1_names = [
        "v6_3_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D105.csv",
        "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "PRIOR_V6_2_PHASES_SNAPSHOT.json",
    ]
    stage1_hashes = {fn: _sha256_file(WS / fn) for fn in stage1_names}

    ml = {
        "schema": "D105_PROSPECTIVE_METHOD_LOCK",
        "phase_id": "D105",
        "detector_version": "V6.3",
        "detector": det.DETECTOR_NAME,
        "locked_utc": locked_utc,
        "projected_unified_stars": 755 + len(brand_new_stars),
        "projected_within_10pc_stars": 206 + n_new_10pc,
        "d105_brand_new_stars": len(brand_new_stars),
        "d105_prior_bridges": len(bridge_stars),
        "d105_total_observations": len(rows),
        "d105_total_physical_files": len(phys_urls),
        "d105_projected_bytes": tot_bytes,
        "d105_projected_mib": round(tot_bytes / (1024.0 * 1024.0), 3),
        "stage_1_files": stage1_hashes,
    }
    (WS / "METHOD_LOCK.json").write_text(json.dumps(ml, indent=2) + "\n", encoding="utf-8")
    ml_sha = _sha256_file(WS / "METHOD_LOCK.json")

    lr = {
        "schema": "D105_LOCK_RECEIPT",
        "phase_id": "D105",
        "status": "STAGE-1 SEALED",
        "locked_utc": locked_utc,
        "locked_unix_epoch": round(locked_epoch, 4),
        "method_lock_sha256": ml_sha,
        "inputs_dir_exists_at_seal": RAW_DIR.exists(),
        "locked_files": stage1_hashes,
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lr, indent=2) + "\n", encoding="utf-8")
    print(f"STAGE-1 SEALED: obs={len(rows)}, files={len(phys_urls)}, brand_new={len(brand_new_stars)} (+{n_new_10pc} <10pc -> {206+n_new_10pc}), unified={755+len(brand_new_stars)}, min_prior_sep={min_prior_sep:.1f}'', min_intra_sep={min_intra_sep:.1f}'', raw_dir_exists={RAW_DIR.exists()}, proj_mib={ml['d105_projected_mib']}")


if __name__ == "__main__":
    main()
