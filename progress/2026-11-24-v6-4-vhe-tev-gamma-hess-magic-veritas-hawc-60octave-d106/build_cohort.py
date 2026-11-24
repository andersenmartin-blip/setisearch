#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D106 (`V6.4`) Stage-1 Prospective Method Lock & Cohort Builder.
Locks 99 target-instrument observations across 70 unique targets (46 brand-new + 24 prior bridges,
116 unique physical files):
  - 38 H.E.S.S. Phase-I DL3 DR1 VHE TeV targets (0.15 - 105 TeV across 38 blind runs)
  - 4 MAGIC Stereo AODR VHE TeV targets (0.04 - 55 TeV across 16 blind dark/Moon runs)
  - 1 VERITAS DL3 Crab Nebula VHE TeV target (0.10 - 18 TeV across 3 blind runs 64081-64083)
  - 7 HAWC Pass-4 blind GP reconstruction targets (1.5 - 315 TeV / 0.315 PeV across 5 fHitbin5GP-9GP cubes)
  - 14 brand-new < 10 pc optical/NIR echelle targets + 5 Fermi-LAT->Optical/NIR < 10 pc bridge follow-ups
  - 30 ESO NIRPS/HARPS spectra forming 6 N=5 orbital campaigns (#181-#186)
Verifies 0 overlap with 3,705 prior dp_ids and 45 format-check probes, >=300" sky separation
from 879 prior coordinates, >=120" intra-D106 separation, HTTP 200 URLs, and absence of $RAW106
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
RAW_DIR = ROOT / "inputs_d106_v6_4"
WS105 = ROOT / "analysis_workspace/work_v6_3_20261124_d105_mev_gev_gamma_osse_comptel_fermi_lat_800star"
ARCHIVE_AE = ROOT / "archives/SETI_D105_V6_3_MEV_GEV_GAMMA_OSSE_COMPTEL_FERMI_LAT_800STAR_RESULTS_2026-11-24.zip"
BUNDLE_105 = WS105 / "bounded_inputs/d105_bounded_bundle.json.gz"

if str(WS) not in sys.path:
    sys.path.insert(0, str(WS))
import v6_4_detector as det  # noqa: E402

C_KMS = det.C_KMS
ARCHIVE_AE_SHA256 = "74ee4b760a0b585ba6b6d7a2e0edbfe623258aa170a507fe577189247749778a"
BUNDLE_105_SHA256 = "1f17bef5850d7cf545dc42a19ae93093d40218f2fcbd03c4905326acdce3d994"

FORMAT_CHECK_EXTRA_D106 = [
    "hess_dl3_dr1_obs_id_023523.fits.gz",
    "64080.fits.gz",
    "20131004_05029747_DL3_CrabNebula-W0.40+035.fits",
    "MAGIC_OBS_5029747",
    "MAGIC_OBS_5071624",
    "EventList_Crab_fHitbin5NN.fits.gz",
    "EventList_Crab_fHitbin6NN.fits.gz",
    "EventList_Crab_fHitbin7NN.fits.gz",
    "EventList_Crab_fHitbin8NN.fits.gz",
    "EventList_Crab_fHitbin9NN.fits.gz",
    "ADP.2020-06-29T05:49:53.478",
    "CARM_car-20160410T20h36m09s-sci-gtoc-vis_A.fits",
    "ADP.2025-04-15T13:07:27.753",
]

# Exact GitHub raw sizes for locked H.E.S.S. DR1 runs (run 023523 excluded!)
HESS_RUN_BYTES: dict[int, int] = {
    23526: 524967, 23559: 526028, 23592: 517549,
    20136: 630275, 20137: 514852,
    20326: 727305, 20327: 729323, 20349: 712857,
    26850: 575620, 26964: 568294, 27044: 579864,
    20734: 632200,
    26791: 456067, 26827: 501570,
    22022: 479333, 23040: 597077, 29683: 500322, 22593: 566251, 23143: 599612,
    20275: 617436, 20915: 619874, 25345: 574222,
    20339: 721226,
    33787: 504999, 33788: 539227, 33789: 585867,
    26077: 510164, 23736: 510540,
    29024: 554693, 29072: 516059, 29118: 504442,
    22997: 589811, 23077: 536721,
    23246: 516177, 23635: 575723, 23651: 566669,
    21807: 595843, 27987: 568566, 20561: 634331,
}

# 46 Brand-new D106 target metadata (verified via Gaia DR3, NASA Exoplanet Archive, NED, SIMBAD)
NEW_META: dict[str, dict[str, Any]] = {
    # --- 12 Brand-new CONTROL VHE TeV Benchmarks (H.E.S.S. DR1 + MAGIC AODR) ---
    "CRABNEBULA":  {"common_name": "Crab Nebula / PSR B0531+21 (TeV Standard Candle)", "role": "CONTROL", "subrole": "TEV_PWN_STANDARD_CANDLE",     "sid": "3403818172572314624", "ra":  83.63308, "dec": +22.01450, "pmra":  -11.8, "pmdec":   4.4, "d":   2000.0, "g": 16.4, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 100000.0, "mass":  1.4, "rv":   0.0, "n_pl": 0, "tr": False},
    "MSH1552":     {"common_name": "MSH 15-5-02 / PSR B1509-58 (TeV PWN)",            "role": "CONTROL", "subrole": "TEV_PWN_CAL",                 "sid": "MSH1552",             "ra": 228.48100, "dec": -59.13600, "pmra":    0.0, "pmdec":   0.0, "d":   5200.0, "g": 20.0, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 100000.0, "mass":  1.4, "rv":   0.0, "n_pl": 0, "tr": False},
    "RXJ1713":     {"common_name": "RX J1713.7-3946 / G347.3-0.5 (TeV Shell SNR)",    "role": "CONTROL", "subrole": "TEV_SNR_SHELL_CAL",           "sid": "RXJ1713",             "ra": 258.38800, "dec": -39.76200, "pmra":    0.0, "pmdec":   0.0, "d":   1000.0, "g": 18.0, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff":  50000.0, "mass":  1.4, "rv":   0.0, "n_pl": 0, "tr": False},
    "KEPLERSNR":   {"common_name": "Kepler SNR / SN 1604 (HESS J1731-212 field)",     "role": "CONTROL", "subrole": "SUPERNOVA_REMNANT_TEV_CAL",   "sid": "KEPLERSNR",           "ra": 262.67100, "dec": -21.48600, "pmra":    0.0, "pmdec":   0.0, "d":   5100.0, "g": 18.0, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff":  30000.0, "mass":  1.4, "rv":   0.0, "n_pl": 0, "tr": False},
    "SN1006":      {"common_name": "SN 1006 Type-Ia Shell SNR (TeV Rim)",             "role": "CONTROL", "subrole": "SUPERNOVA_REMNANT_TEV_CAL",   "sid": "SN1006",              "ra": 225.70200, "dec": -41.91200, "pmra":    0.0, "pmdec":   0.0, "d":   2180.0, "g": 17.5, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff":  25000.0, "mass":  1.4, "rv":   0.0, "n_pl": 0, "tr": False},
    "ARP220":      {"common_name": "Arp 220 (ULIRG Starburst TeV Limit)",             "role": "CONTROL", "subrole": "ULIRG_STARBURST_TEV_CAL",     "sid": "ARP220",              "ra": 233.73843, "dec": +23.50318, "pmra":    0.0, "pmdec":   0.0, "d": 79900000.0, "g": 13.8, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff":   5500.0, "mass":  1.0, "rv": 5434.0, "n_pl": 0, "tr": False},
    "GX339_4":     {"common_name": "GX 339-4 (Transient Black Hole LMXB)",            "role": "CONTROL", "subrole": "BH_XRAY_BINARY_TEV_CAL",      "sid": "5938700394025461248", "ra": 255.70580, "dec": -48.78972, "pmra":   -4.0, "pmdec":  -4.8, "d":   8400.0, "g": 16.5, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff":  20000.0, "mass":  8.0, "rv":  26.0, "n_pl": 0, "tr": False},
    "PSRJ0437":    {"common_name": "PSR J0437-4715 (Closest Millisecond Pulsar)",    "role": "CONTROL", "subrole": "MILLISECOND_TEV_PULSAR_CAL",  "sid": "PSRJ0437",            "ra":  69.31618, "dec": -47.25251, "pmra":  121.4, "pmdec": -71.5, "d":    156.8, "g": 20.9, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 120000.0, "mass":  1.4, "rv":   0.0, "n_pl": 0, "tr": False},
    "TUC47NW":     {"common_name": "47 Tucanae (NGC 104 Globular Cluster TeV)",       "role": "CONTROL", "subrole": "GLOBULAR_CLUSTER_TEV_CAL",    "sid": "TUC47NW",             "ra":   6.02363, "dec": -72.08128, "pmra":    5.2, "pmdec":  -2.5, "d":   4520.0, "g":  4.0, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff":   5200.0, "mass":  1.0, "rv": -17.2, "n_pl": 0, "tr": False},
    "PICTORA":     {"common_name": "Pictor A (FR-II Radio Galaxy AGN)",               "role": "CONTROL", "subrole": "AGN_EXTRAGALACTIC_TEV_CAL",   "sid": "PICTORA",             "ra":  79.95717, "dec": -45.77885, "pmra":    0.0, "pmdec":   0.0, "d": 152000000.0, "g": 15.8, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 6000.0, "mass": 1.0, "rv": 10511.0, "n_pl": 0, "tr": False},
    "PKS0548_322": {"common_name": "PKS 0548-322 (TeV HBL Blazar)",                   "role": "CONTROL", "subrole": "BLAZAR_EXTRAGALACTIC_TEV_CAL","sid": "PKS0548_322",         "ra":  87.66917, "dec": -32.27125, "pmra":    0.0, "pmdec":   0.0, "d": 308000000.0, "g": 15.5, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 6000.0, "mass": 1.0, "rv": 20700.0, "n_pl": 0, "tr": False},
    "1ES1218_304": {"common_name": "1ES 1218+304 (MAGIC AODR TeV Blazar)",            "role": "CONTROL", "subrole": "BLAZAR_EXTRAGALACTIC_TEV_CAL","sid": "1ES1218_304",         "ra": 185.34143, "dec": +30.17699, "pmra":    0.0, "pmdec":   0.0, "d": 882000000.0, "g": 16.2, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 6000.0, "mass": 1.0, "rv": 54600.0, "n_pl": 0, "tr": False},

    # --- 14 Brand-new SCIENCE Confirmed Exoplanet Hosts in H.E.S.S. & HAWC VHE FoVs ---
    "TOI2443":  {"common_name": "TOI-2443 (HD 16813, 23.93 pc)",     "role": "SCIENCE", "subrole": "VHE_TEV_EXOPLANET_HOST", "sid": "2501948402746099456", "ra":  40.17986, "dec":  +1.19968, "pmra":  283.92, "pmdec":  231.75, "d":  23.9258, "g":  9.0378, "bp":  9.7283, "rp":  8.2339, "j":  7.260, "h":  6.692, "k":  6.500, "teff": 4375.0, "mass": 0.642, "rv":  72.926, "n_pl": 1, "tr": True,  "mh": -0.29},
    "HD39194":  {"common_name": "HD 39194 (3-Planet Super-Earth)",   "role": "SCIENCE", "subrole": "VHE_TEV_EXOPLANET_HOST", "sid": "4657193606465368704", "ra":  86.12907, "dec": -70.13824, "pmra": -309.27, "pmdec": 1238.86, "d":  26.4131, "g":  7.8646, "bp":  8.2614, "rp":  7.2910, "j":  6.598, "h":  6.212, "k":  6.094, "teff": 5205.0, "mass": 0.860, "rv":  13.989, "n_pl": 3, "tr": False, "mh": -0.61},
    "HD37124":  {"common_name": "HD 37124 (3-Planet System, HESS+HAWC)","role": "SCIENCE", "subrole": "VHE_TEV_EXOPLANET_HOST", "sid": "3402798414192387328", "ra":  84.25999, "dec": +20.72898, "pmra":  -79.55, "pmdec": -420.04, "d":  31.6634, "g":  7.4871, "bp":  7.8257, "rp":  6.9690, "j":  6.359, "h":  6.021, "k":  5.952, "teff": 5698.6, "mass": 0.850, "rv": -23.078, "n_pl": 3, "tr": False, "mh": -0.44},
    "HD216770": {"common_name": "HD 216770 (Eccentric Giant Host)",  "role": "SCIENCE", "subrole": "VHE_TEV_EXOPLANET_HOST", "sid": "6610107504955838336", "ra": 343.97488, "dec": -26.65953, "pmra":  226.24, "pmdec": -177.98, "d":  36.6625, "g":  7.9284, "bp":  8.3173, "rp":  7.3694, "j":  6.752, "h":  6.429, "k":  6.311, "teff": 5399.0, "mass": 0.740, "rv":  31.004, "n_pl": 1, "tr": False, "mh": +0.27},
    "HIP21152": {"common_name": "HIP 21152 (Hyades BD/Planet Host)","role": "SCIENCE", "subrole": "VHE_TEV_EXOPLANET_HOST", "sid": "3285426613077584384", "ra":  68.02052, "dec":  +5.41007, "pmra":  112.17, "pmdec":    7.76, "d":  43.4073, "g":  6.2678, "bp":  6.4708, "rp":  5.9109, "j":  5.593, "h":  5.385, "k":  5.333, "teff": 6655.0, "mass": 1.400, "rv":  41.031, "n_pl": 1, "tr": False, "mh": +0.13},
    "HD4732":   {"common_name": "HD 4732 (2-Planet K0IV Host)",      "role": "SCIENCE", "subrole": "VHE_TEV_EXOPLANET_HOST", "sid": "2345744256122307584", "ra":  12.30851, "dec": -24.13691, "pmra":   83.15, "pmdec":  -54.54, "d":  54.7841, "g":  5.9000, "bp":  None,   "rp":  None,   "j":  4.338, "h":  3.717, "k":  3.691, "teff": 4898.0, "mass": 1.390, "rv":   0.000, "n_pl": 2, "tr": False, "mh": -0.01},
    "HD35843":  {"common_name": "HD 35843 (2-Planet G2V Host)",      "role": "SCIENCE", "subrole": "VHE_TEV_EXOPLANET_HOST", "sid": "4799563663371481344", "ra":  81.34889, "dec": -44.43128, "pmra":  -43.94, "pmdec": -110.24, "d":  69.6026, "g":  9.2036, "bp":  9.5270, "rp":  8.7059, "j":  8.151, "h":  7.859, "k":  7.782, "teff": 5666.0, "mass": 0.940, "rv":  13.714, "n_pl": 2, "tr": True,  "mh": -0.27},
    "WASP130":  {"common_name": "WASP-130 (Hot Jupiter Host)",       "role": "SCIENCE", "subrole": "VHE_TEV_EXOPLANET_HOST", "sid": "6112606840179716096", "ra": 203.10602, "dec": -42.47527, "pmra":    6.08, "pmdec":   -1.27, "d": 172.2560, "g": 10.9740, "bp": 11.3412, "rp": 10.4359, "j":  9.896, "h":  9.547, "k":  9.461, "teff": 5625.0, "mass": 1.040, "rv":   1.514, "n_pl": 1, "tr": True,  "mh": +0.26},
    "HD28678":  {"common_name": "HD 28678 (Subgiant Exoplanet Host)","role": "SCIENCE", "subrole": "VHE_TEV_EXOPLANET_HOST", "sid": "3282351760091020672", "ra":  67.85606, "dec":  +4.57525, "pmra":    1.40, "pmdec":  -10.49, "d": 189.9080, "g":  8.0656, "bp":  8.6206, "rp":  7.3496, "j":  6.447, "h":  5.942, "k":  5.775, "teff": 4972.0, "mass": 1.530, "rv":  61.606, "n_pl": 1, "tr": False, "mh": -0.11},
    "TOI4603":  {"common_name": "TOI-4603 (Massive BD/Planet, HESS+HAWC)", "role": "SCIENCE", "subrole": "VHE_TEV_EXOPLANET_HOST", "sid": "3402980516507429888", "ra": 83.86593, "dec": +21.29424, "pmra": 0.10, "pmdec": -22.87, "d": 225.6430, "g": 9.0832, "bp": 9.3914, "rp": 8.6033, "j": 8.089, "h": 7.788, "k": 7.786, "teff": 6264.0, "mass": 1.765, "rv": -3.592, "n_pl": 1, "tr": True, "mh": +0.342},
    "K2_289":   {"common_name": "K2-289 (Sco X-1 TeV FoV Host)",     "role": "SCIENCE", "subrole": "VHE_TEV_EXOPLANET_HOST", "sid": "K2_289",              "ra": 246.64294, "dec": -15.79254, "pmra":    0.00, "pmdec":    0.00, "d": 274.3000, "g": 14.8100, "bp":  None,   "rp":  None,   "j": 11.435, "h": 10.847, "k": 10.641, "teff": 5529.0, "mass": 0.953, "rv":   0.000, "n_pl": 1, "tr": True,  "mh": +0.162},
    "NGTS4":    {"common_name": "NGTS-4 (Neptunian Desert Host)",   "role": "SCIENCE", "subrole": "VHE_TEV_EXOPLANET_HOST", "sid": "NGTS4",               "ra":  89.59889, "dec": -30.81180, "pmra":    0.00, "pmdec":    0.00, "d": 280.5550, "g": 13.1380, "bp":  None,   "rp":  None,   "j": 11.584, "h": 11.139, "k": 11.073, "teff": 5143.0, "mass": 0.750, "rv":   0.000, "n_pl": 1, "tr": True,  "mh": -0.28},
    "K2_397":   {"common_name": "K2-397 (HAWC Crab FoV Host)",       "role": "SCIENCE", "subrole": "HAWC_PEV_EXOPLANET_HOST","sid": "3414370975935397888", "ra":  79.95166, "dec": +21.25916, "pmra":   24.45, "pmdec":   -8.74, "d": 199.3540, "g": 11.6363, "bp": 12.0312, "rp": 11.0695, "j": 10.402, "h": 10.029, "k": 9.950, "teff": 5387.0, "mass": 0.937, "rv": -33.011, "n_pl": 1, "tr": True, "mh": +0.11},
    "TOI5422":  {"common_name": "TOI-5422 (HAWC Crab FoV Host)",      "role": "SCIENCE", "subrole": "HAWC_PEV_EXOPLANET_HOST","sid": "3429057191403928960", "ra":  86.84362, "dec": +25.62603, "pmra":    1.50, "pmdec":   -7.97, "d": 346.1410, "g": 11.4990, "bp":  None,   "rp":  None,   "j": 10.579, "h": 10.246, "k": 10.161, "teff": 5820.0, "mass": 1.066, "rv":   0.000, "n_pl": 1, "tr": True, "mh": -0.012},

    # --- 14 Brand-new < 10 pc Optical/NIR Echelle Targets ---
    "DENISJ1048":   {"common_name": "DENIS J1048-3956 (M9V, 4.05 pc)",         "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "5393446658454453632", "ra": 162.05389, "dec": -39.93963, "pmra": -1179.31, "pmdec":  -988.12, "d": 4.045, "g": 14.006, "bp": 17.617, "rp": 12.463, "j":  9.538, "h": 8.905, "k": 8.447, "teff": 2350.0, "mass": 0.08, "rv":   0.0,   "n_pl": 0, "tr": False},
    "LSRJ1835":     {"common_name": "LSR J1835+3259 (M8.5V, 5.69 pc)",         "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "2091177593123254016", "ra": 278.90783, "dec": +32.99630, "pmra":   -72.60, "pmdec":  -755.10, "d": 5.689, "g": 14.851, "bp": 18.456, "rp": 13.306, "j": 10.270, "h": 9.617, "k": 9.171, "teff": 2500.0, "mass": 0.08, "rv":   0.0,   "n_pl": 0, "tr": False},
    "WD0552_041":   {"common_name": "WD 0552-041 (EGGR 45 DZ WD, 6.44 pc)",    "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_WD",      "sid": "3022956969731332096", "ra":  88.79210, "dec":  -4.17893, "pmra":   535.25, "pmdec": -2317.01, "d": 6.442, "g": 14.237, "bp": 14.727, "rp": 13.593, "j": None,   "h": None,  "k": None,  "teff": 5050.0, "mass": 0.81, "rv":   0.0,   "n_pl": 0, "tr": False},
    "GJ3877":       {"common_name": "GJ 3877 (LP 914-54 M7V, 7.05 pc)",        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "6224387727748521344", "ra": 224.15696, "dec": -28.16725, "pmra":  -490.29, "pmdec":  -843.48, "d": 7.053, "g": 14.061, "bp": 17.335, "rp": 12.566, "j": None,   "h": None,  "k": None,  "teff": 2650.0, "mass": 0.09, "rv":   0.0,   "n_pl": 0, "tr": False},
    "SIP1259_4336": {"common_name": "SIPS J1259-4336 (M7.5V, 7.73 pc)",        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "6135947032490329472", "ra": 194.77664, "dec": -43.60796, "pmra":  1102.92, "pmdec":  -264.54, "d": 7.726, "g": 14.830, "bp": None,   "rp": None,   "j": None,   "h": None,  "k": None,  "teff": 2550.0, "mass": 0.09, "rv":   0.0,   "n_pl": 0, "tr": False},
    "WD1334_039":   {"common_name": "WD 1334+039 (Wolf 489 WD, 8.35 pc)",      "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_WD",      "sid": "3713594960831605760", "ra": 204.11608, "dec":  +3.67448, "pmra": -3735.84, "pmdec": -1113.58, "d": 8.350, "g": 14.376, "bp": 14.870, "rp": 13.722, "j": None,   "h": None,  "k": None,  "teff": 5000.0, "mass": 0.56, "rv":   0.0,   "n_pl": 0, "tr": False},
    "WD2251_070":   {"common_name": "WD 2251-070 (DZ Metal-Polluted WD, 8.54 pc)", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_WD",  "sid": "2611561706216413696", "ra": 343.48356, "dec":  -6.78483, "pmra":  2485.80, "pmdec":  -681.25, "d": 8.537, "g": 15.420, "bp": None,   "rp": None,   "j": None,   "h": None,  "k": None,  "teff": 4000.0, "mass": 0.58, "rv":   0.0,   "n_pl": 0, "tr": False},
    "LHS2065":      {"common_name": "LHS 2065 (LP 666-9 M9V, 8.66 pc)",        "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "5761985432616501376", "ra": 133.40067, "dec":  -3.49316, "pmra":  -516.61, "pmdec":  -199.65, "d": 8.659, "g": 15.889, "bp": 19.110, "rp": 14.352, "j": 11.212, "h": 10.469,"k": 9.942, "teff": 2400.0, "mass": 0.08, "rv":   0.0,   "n_pl": 0, "tr": False},
    "GJ3146":       {"common_name": "GJ 3146 (LHS 1378 M5.5V, 9.10 pc)",       "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "74203982469858816",   "ra":  34.12669, "dec": +13.58496, "pmra":   504.22, "pmdec":  -433.14, "d": 9.095, "g": 13.556, "bp": 16.086, "rp": 12.149, "j": None,   "h": None,  "k": None,  "teff": 2950.0, "mass": 0.12, "rv":  18.895,"n_pl": 0, "tr": False},
    "WD0038_226":   {"common_name": "WD 0038-226 (LHS 1126 DQpec WD, 9.10 pc)","role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_WD",      "sid": "2349916559152267008", "ra":  10.35622, "dec": -22.35233, "pmra":  -463.21, "pmdec":  -381.78, "d": 9.097, "g": 14.297, "bp": 14.665, "rp": 13.754, "j": None,   "h": None,  "k": None,  "teff": 5200.0, "mass": 0.61, "rv":   0.0,   "n_pl": 0, "tr": False},
    "WT460":        {"common_name": "WT 460 (M5.5V + L1 Binary, 9.11 pc)",     "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "6109949904687424640", "ra": 212.99540, "dec": -41.53972, "pmra":  -704.22, "pmdec":   -67.65, "d": 9.113, "g": 13.419, "bp": 15.922, "rp": 11.991, "j":  9.670, "h": 9.043, "k": 8.618, "teff": 2950.0, "mass": 0.13, "rv": -13.185,"n_pl": 0, "tr": False},
    "GJ3128":       {"common_name": "GJ 3128 (LHS 1326 M5.5V, 9.24 pc)",       "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "2571094283835172736", "ra":  30.56464, "dec": +10.33596, "pmra":  -673.64, "pmdec":  -280.59, "d": 9.237, "g": 13.435, "bp": 15.908, "rp": 12.035, "j": None,   "h": None,  "k": None,  "teff": 2950.0, "mass": 0.12, "rv":  23.085,"n_pl": 0, "tr": False},
    "UCAC4_379":    {"common_name": "UCAC4 379-100760 (9.48 pc ESPRESSO)",    "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "4147112604476417792", "ra": 271.43447, "dec": -14.37836, "pmra":  -344.87, "pmdec":    24.87, "d": 9.477, "g": 13.255, "bp": 15.561, "rp": 11.882, "j": None,   "h": None,  "k": None,  "teff": 2883.7, "mass": 0.12, "rv":   0.0,   "n_pl": 0, "tr": False},
    "WD0141_675":   {"common_name": "WD 0141-675 (LAWD 10 WD, 9.72 pc)",       "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_WD",      "sid": "4698424845771339520", "ra":  25.75030, "dec": -67.31296, "pmra":  -329.26, "pmdec": -1018.51, "d": 9.717, "g": 13.697, "bp": 13.943, "rp": 13.289, "j": None,   "h": None,  "k": None,  "teff": 6300.0, "mass": 0.62, "rv":   0.0,   "n_pl": 0, "tr": False},

    # --- 6 Brand-new ESO NIRPS/HARPS Orbits #181-#186 Exoplanet Hosts ---
    "HD115404A": {"common_name": "HD 115404 A (NIRPS Orbit #181)", "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "3936909723803146368", "ra": 199.21567, "dec": +17.01600, "pmra":  636.28, "pmdec": -264.68, "d": 10.9816, "g":  6.2977, "bp":  6.7635, "rp": 5.6626, "j": 4.950, "h": 4.500, "k": 4.420, "teff": 5019.2, "mass": 0.8300, "rv":  7.6243, "n_pl": 2, "tr": False, "mh": -0.157},
    "HD211970":  {"common_name": "HD 211970 (HARPS Orbit #182)",   "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "6508401923473282432", "ra": 335.56611, "dec": -54.55957, "pmra": -184.20, "pmdec":  234.97, "d": 13.1277, "g":  8.4100, "bp":  9.2039, "rp": 7.5403, "j": 6.462, "h": 5.842, "k": 5.663, "teff": 4127.0, "mass": 0.6100, "rv": -5.4895, "n_pl": 1, "tr": False, "mh":  0.000},
    "GJ480":     {"common_name": "GJ 480 (HARPS Orbit #183)",      "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "3928391218812375808", "ra": 189.71326, "dec": +11.69504, "pmra": -1155.76,"pmdec": -250.86, "d": 14.2358, "g": 10.3357, "bp": 11.7504, "rp": 9.1597, "j": 7.581, "h": 6.939, "k": 6.691, "teff": 3509.0, "mass": 0.4500, "rv": -4.3397, "n_pl": 1, "tr": False, "mh": +0.260},
    "HIP79431":  {"common_name": "HIP 79431 (HARPS Orbit #184)",   "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "6245870673116518784", "ra": 243.17425, "dec": -18.87645, "pmra":   36.45, "pmdec": -214.02, "d": 14.5324, "g": 10.2506, "bp": 11.6122, "rp": 9.0945, "j": 7.555, "h": 6.855, "k": 6.589, "teff": 3191.0, "mass": 0.4900, "rv": -4.9285, "n_pl": 1, "tr": False, "mh": +0.400},
    "HIP38594":  {"common_name": "HIP 38594 (HARPS Orbit #185)",   "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "5602386058511578368", "ra": 118.54387, "dec": -25.30228, "pmra": -300.86, "pmdec":  201.04, "d": 17.7886, "g":  9.0898, "bp":  9.9609, "rp": 8.1718, "j": 7.021, "h": 6.372, "k": 6.169, "teff": 4086.3, "mass": 0.6100, "rv": 63.0761, "n_pl": 2, "tr": False, "mh":  0.000},
    "HIP54373":  {"common_name": "HIP 54373 (HARPS Orbit #186)",   "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "3552000252294347392", "ra": 166.86432, "dec": -19.29169, "pmra": -235.05, "pmdec":  -45.88, "d": 18.7168, "g":  9.6442, "bp": 10.6028, "rp": 8.6741, "j": 7.449, "h": 6.853, "k": 6.620, "teff": 4021.0, "mass": 0.5700, "rv": -4.4851, "n_pl": 2, "tr": False, "mh":  0.000},
}

# 38 H.E.S.S. DR1 Targets: (canon, is_prior_bridge, panchrom_bridge, mjd_rep, run_ids)
HESS_TARGETS: list[tuple[str, bool, bool, float, list[int]]] = [
    # 15 Prior Bridges (7 SCIENCE + 8 CONTROL)
    ("GJ191",     True, True, 53268.0, [22593]),
    ("LP94420",   True, True, 53595.0, [27987]),
    ("HD134060",  True, True, 53090.0, [20136, 20137]),
    ("HD131488",  True, True, 53138.0, [20734]),
    ("WASP178",   True, True, 53138.0, [20734]),
    ("V644SCO",   True, True, 53112.0, [20326, 20327, 20349]),
    ("FOMALHAUT", True, True, 53210.0, [21807]),
    ("3C273",     True, True, 53109.0, [20275, 20915, 25345]),
    ("CENA",      True, True, 53112.0, [20339]),
    ("PKS2155",   True, True, 53945.0, [33787, 33788, 33789]),
    ("SCOX1",     True, True, 53525.0, [26077]),
    ("SN1987A",   True, True, 53373.0, [23736]),
    ("NGC253",    True, True, 53645.0, [29024, 29072, 29118]),
    ("NGC1068",   True, True, 53289.0, [22997, 23077]),
    ("3C120",     True, True, 53316.0, [23246, 23635, 23651]),
    # 12 Brand-new SCIENCE Exoplanet Hosts in H.E.S.S. DR1 FoV
    ("TOI2443",   False, False, 53289.0, [22997, 23077]),
    ("HD39194",   False, False, 53373.0, [23736]),
    ("HD37124",   False, False, 53343.0, [23526, 23559, 23592]),
    ("HD216770",  False, False, 53210.0, [21807]),
    ("HIP21152",  False, False, 53316.0, [23246, 23635, 23651]),
    ("HD4732",    False, False, 53645.0, [29024, 29072, 29118]),
    ("HD35843",   False, False, 53268.0, [22593]),
    ("WASP130",   False, False, 53112.0, [20339]),
    ("HD28678",   False, False, 53316.0, [23246, 23635, 23651]),
    ("TOI4603",   False, False, 53343.0, [23526, 23559, 23592]),
    ("K2_289",    False, False, 53525.0, [26077]),
    ("NGTS4",     False, False, 53299.0, [23143]),
    # 11 Brand-new CONTROL TeV Calibration Benchmarks
    ("CRABNEBULA",  False, False, 53343.0, [23526, 23559, 23592]),
    ("MSH1552",     False, False, 53090.0, [20136, 20137]),
    ("RXJ1713",     False, False, 53112.0, [20326, 20327, 20349]),
    ("KEPLERSNR",   False, False, 53551.0, [26850, 26964, 27044]),
    ("SN1006",      False, False, 53138.0, [20734]),
    ("ARP220",      False, False, 53548.0, [26791, 26827]),
    ("GX339_4",     False, False, 53230.0, [22022]),
    ("PSRJ0437",    False, False, 53292.0, [23040]),
    ("TUC47NW",     False, False, 53694.0, [29683]),
    ("PICTORA",     False, False, 53268.0, [22593]),
    ("PKS0548_322", False, False, 53299.0, [23143]),
]

# 4 MAGIC AODR Targets (16 blind runs, excluding 5029747 and 5071624!)
MAGIC_AODR_URL = "https://zenodo.org/api/records/17064461/files/acme_magic_odas_data.zip/content"
MAGIC_TARGETS: list[tuple[str, bool, bool, float, list[tuple[str, int]]]] = [
    ("CRABNEBULA", False, False, 56625.0, [
        ("acme_magic_odas_data/data/CrabNebula/20140102_05032062_DL3_CrabNebula-W0.40+035.fits", 299520),
        ("acme_magic_odas_data/data/CrabNebula/20131225_05031794_DL3_CrabNebula-W0.40+215.fits", 230400),
        ("acme_magic_odas_data/data/CrabNebula/20131205_05031445_DL3_CrabNebula-W0.40+215.fits", 446400),
        ("acme_magic_odas_data/data/CrabNebula/20131113_05030915_DL3_CrabNebula-W0.40+035.fits", 230400),
    ]),
    ("MRK421", True, True, 56395.0, [
        ("acme_magic_odas_data/data/Mrk421/20130415_05025130_DL3_Mrk421-W0.40+090.fits", 731520),
        ("acme_magic_odas_data/data/Mrk421/20130411_05024978_DL3_Mrk421-W0.40+090.fits", 417600),
        ("acme_magic_odas_data/data/Mrk421/20130401_05024673_DL3_Mrk421-W0.40+180.fits", 734400),
        ("acme_magic_odas_data/data/Mrk421/20130414_05025085_DL3_Mrk421-W0.40+000.fits", 711360),
    ]),
    ("GEMINGA", True, True, 57800.0, [
        ("acme_magic_odas_data/data/Geminga/20170125_05060083_DL3_Geminga-W0.40+000.fits", 2779200),
        ("acme_magic_odas_data/data/Geminga/20170227_05061566_DL3_Geminga-W0.40+270.fits", 3548160),
        ("acme_magic_odas_data/data/Geminga/20190227_05080203_DL3_Geminga-W0.40+034.fits", 2652480),
        ("acme_magic_odas_data/data/Geminga/20170127_05060187_DL3_Geminga-W0.40+270.fits", 3818880),
    ]),
    ("1ES1218_304", False, False, 58490.0, [
        ("acme_magic_odas_data/data/1ES1218+304/point_like/20190102_05078248_DL3_1ES1218+304-W0.40+270.fits", 334080),
        ("acme_magic_odas_data/data/1ES1218+304/point_like/20190113_05078784_DL3_1ES1218+304-W0.40+090.fits", 155520),
        ("acme_magic_odas_data/data/1ES1218+304/point_like/20181231_05078154_DL3_1ES1218+304-W0.40+270.fits", 276480),
        ("acme_magic_odas_data/data/1ES1218+304/point_like/20190115_05078887_DL3_1ES1218+304-W0.40+090.fits", 357120),
    ]),
]

# VERITAS 3 blind Crab runs (64080 format-check excluded!)
VERITAS_RUNS: list[tuple[str, int]] = [
    ("64081.fits.gz", 74713),
    ("64082.fits.gz", 69973),
    ("64083.fits.gz", 75170),
]

# HAWC Pass-4 blind GP reconstruction bins fHitbin5GP..9GP
HAWC_GP_FILES: list[tuple[str, str, int]] = [
    ("HAWC_TEV/events/EventList_Crab_fHitbin5GP.fits.gz", "https://raw.githubusercontent.com/gammapy/gammapy-data/main/hawc/crab_events_pass4/events/EventList_Crab_fHitbin5GP.fits.gz", 1975502),
    ("HAWC_TEV/events/EventList_Crab_fHitbin6GP.fits.gz", "https://raw.githubusercontent.com/gammapy/gammapy-data/main/hawc/crab_events_pass4/events/EventList_Crab_fHitbin6GP.fits.gz", 783839),
    ("HAWC_TEV/events/EventList_Crab_fHitbin7GP.fits.gz", "https://raw.githubusercontent.com/gammapy/gammapy-data/main/hawc/crab_events_pass4/events/EventList_Crab_fHitbin7GP.fits.gz", 503250),
    ("HAWC_TEV/events/EventList_Crab_fHitbin8GP.fits.gz", "https://raw.githubusercontent.com/gammapy/gammapy-data/main/hawc/crab_events_pass4/events/EventList_Crab_fHitbin8GP.fits.gz", 397999),
    ("HAWC_TEV/events/EventList_Crab_fHitbin9GP.fits.gz", "https://raw.githubusercontent.com/gammapy/gammapy-data/main/hawc/crab_events_pass4/events/EventList_Crab_fHitbin9GP.fits.gz", 385909),
    ("HAWC_TEV/irfs/EffectiveAreaMap_Crab_fHitbin5GP.fits.gz", "https://raw.githubusercontent.com/gammapy/gammapy-data/main/hawc/crab_events_pass4/irfs/EffectiveAreaMap_Crab_fHitbin5GP.fits.gz", 36780),
    ("HAWC_TEV/irfs/EffectiveAreaMap_Crab_fHitbin6GP.fits.gz", "https://raw.githubusercontent.com/gammapy/gammapy-data/main/hawc/crab_events_pass4/irfs/EffectiveAreaMap_Crab_fHitbin6GP.fits.gz", 33998),
    ("HAWC_TEV/irfs/EffectiveAreaMap_Crab_fHitbin7GP.fits.gz", "https://raw.githubusercontent.com/gammapy/gammapy-data/main/hawc/crab_events_pass4/irfs/EffectiveAreaMap_Crab_fHitbin7GP.fits.gz", 32411),
    ("HAWC_TEV/irfs/EffectiveAreaMap_Crab_fHitbin8GP.fits.gz", "https://raw.githubusercontent.com/gammapy/gammapy-data/main/hawc/crab_events_pass4/irfs/EffectiveAreaMap_Crab_fHitbin8GP.fits.gz", 29998),
    ("HAWC_TEV/irfs/EffectiveAreaMap_Crab_fHitbin9GP.fits.gz", "https://raw.githubusercontent.com/gammapy/gammapy-data/main/hawc/crab_events_pass4/irfs/EffectiveAreaMap_Crab_fHitbin9GP.fits.gz", 32027),
]

HAWC_TARGETS: list[tuple[str, bool, bool]] = [
    ("CRABNEBULA", False, False),
    ("HD36112",    True,  True),
    ("CETAU",      True,  True),
    ("HD37124",    False, False),
    ("TOI4603",    False, False),
    ("K2_397",     False, False),
    ("TOI5422",    False, False),
]

# 14 Brand-new < 10 pc + 5 Fermi-LAT -> Optical/NIR < 10 pc Bridges (canon, is_prior_bridge, inst, ref_id, mjd, exp_s, sz, r_pow, carm_dir)
OPTICAL_10PC_AND_BRIDGES: list[tuple[str, bool, str, str, float, float, int, float, str]] = [
    # 14 Brand-new < 10 pc
    ("DENISJ1048",   False, "ESO_NIRPS",    "ADP.2025-04-15T13:07:26.802",                      60273.288919,  601.916, 47111040,  70000.0, ""),
    ("LSRJ1835",     False, "CARMENES_VIS", "car-20160520T03h10m13s-sci-gtoc-vis_A.fits",     57528.132095, 1801.000,        0,  94600.0, "J18356%2B329"),
    ("WD0552_041",   False, "ESO_UVES",     "ADP.2020-08-04T16:14:23.247",                      52719.018725,  600.001,  1189440,  51690.0, ""),
    ("GJ3877",       False, "ESO_FEROS",    "ADP.2016-11-02T09:07:59.550",                      54268.016384,  599.999,        0,  48000.0, ""),
    ("SIP1259_4336", False, "ESO_UVES",     "ADP.2020-06-23T07:54:14.379",                      54925.092922, 2550.004,        0,  51690.0, ""),
    ("WD1334_039",   False, "ESO_UVES",     "ADP.2020-09-11T06:09:16.797",                      51755.017358,  300.000,        0,  51690.0, ""),
    ("WD2251_070",   False, "ESO_UVES",     "ADP.2021-08-29T17:14:32.348",                      52541.247982,  600.000,        0,  51690.0, ""),
    ("LHS2065",      False, "CARMENES_VIS", "car-20160202T23h54m34s-sci-gtoc-vis_A.fits",     57420.996227, 1800.100,        0,  94600.0, "J08536-034"),
    ("GJ3146",       False, "ESO_UVES",     "ADP.2020-06-09T07:23:59.947",                      56131.391451,  599.999,        0,  51690.0, ""),
    ("WD0038_226",   False, "ESO_UVES",     "ADP.2020-06-10T09:34:10.251",                      57663.144506, 1840.003,        0,  51690.0, ""),
    ("WT460",        False, "ESO_NIRPS",    "ADP.2025-09-03T14:06:42.841",                      60797.130345,  300.958, 47111040,  70000.0, ""),
    ("GJ3128",       False, "ESO_UVES",     "ADP.2020-06-09T07:23:59.897",                      56131.339199,  599.999,  3372480,  51690.0, ""),
    ("UCAC4_379",    False, "ESO_ESPRESSO", "ADP.2022-07-07T12:17:07.374",                      59730.120913,  900.000, 55111680, 140000.0, ""),
    ("WD0141_675",   False, "ESO_ESPRESSO", "ADP.2023-11-03T15:22:47.060",                      60237.134604, 3144.000,        0, 140000.0, ""),
    # 5 Fermi-LAT -> Optical/NIR < 10 pc Multi-Phase Bridges (promotes 5 D105 Fermi-only stars!)
    ("GJ1116B",      True,  "ESO_UVES",     "ADP.2020-08-12T09:10:41.428",                      52348.089438, 3600.055,  4884480,  51690.0, ""),
    ("GL829",        True,  "ESO_UVES",     "ADP.2020-06-10T07:47:47.248",                      57531.311798,  799.996,  9581760,  51690.0, ""),
    ("GJ2005",       True,  "ESO_UVES",     "ADP.2020-06-29T05:52:02.185",                      54397.058860,  299.997,  3421440,  51690.0, ""),
    ("LAWD28",       True,  "ESO_UVES",     "ADP.2020-09-14T19:08:09.976",                      51652.981511,   10.002,   708480,  51690.0, ""),
    ("LP991_84",     True,  "ESO_NIRPS",    "ADP.2025-02-21T16:30:20.899",                      60644.026666,  601.916, 47111040,  70000.0, ""),
]

# 6 brand-new ESO NIRPS/HARPS Orbits #181-#186 (30 spectra, N=5 each)
ESO_ORBIT_CAMPAIGNS: list[dict[str, Any]] = [
    {
        "campaign_order": 181, "star": "HD115404A", "instrument": "ESO_NIRPS", "grating": "NIRPS_YJH_966_1923NM", "r": 70000.0,
        "orb_per_days": 10.49488, "orb_ecc": 0.232, "orb_omega_deg": 259.222, "orb_t0_bjd": 2459500.00, "kp_kms": 0.010507,
        "exposures": [
            ("ADP.2025-04-11T12:47:16.575", 60064.146333, 601.916, 180.0, 47111040),
            ("ADP.2025-04-11T14:43:25.102", 60073.166344, 300.958, 130.0, 47111040),
            ("ADP.2025-04-10T15:19:32.141", 60753.335334, 501.597, 165.0, 47111040),
            ("ADP.2025-04-10T15:19:32.232", 60766.225883, 351.117, 145.0, 47111040),
            ("ADP.2025-09-03T15:41:30.738", 60849.018214, 300.958, 125.0, 47111040),
        ],
    },
    {
        "campaign_order": 182, "star": "HD211970", "instrument": "ESO_HARPS", "grating": "HARPS_378_691NM", "r": 115000.0,
        "orb_per_days": 25.201, "orb_ecc": 0.150, "orb_omega_deg": 97.830, "orb_t0_bjd": 2455000.00, "kp_kms": 0.00402,
        "exposures": [
            ("ADP.2014-09-23T11:01:03.470", 55090.170312, 342.800, 45.0, 0),
            ("ADP.2014-09-24T09:43:32.597", 55429.329558, 171.400, 32.0, 0),
            ("ADP.2014-09-25T15:35:33.217", 55877.062589, 900.005, 78.0, 0),
            ("ADP.2014-09-26T16:52:05.330", 56088.416505, 240.005, 42.0, 0),
            ("ADP.2014-09-26T16:55:04.027", 56207.178407, 749.999, 71.0, 0),
        ],
    },
    {
        "campaign_order": 183, "star": "GJ480", "instrument": "ESO_HARPS", "grating": "HARPS_378_691NM", "r": 115000.0,
        "orb_per_days": 9.5536, "orb_ecc": 0.000, "orb_omega_deg": 151.0, "orb_t0_bjd": 2458446.00, "kp_kms": 0.00450,
        "exposures": [
            ("ADP.2014-09-18T12:16:59.240", 54566.205633, 300.000, 22.0, 0),
            ("ADP.2014-09-18T12:13:38.930", 54661.994505, 900.000, 38.0, 0),
            ("ADP.2014-09-18T12:13:07.113", 54662.986893, 900.000, 39.0, 0),
            ("ADP.2014-09-18T12:14:33.700", 54663.993674, 900.000, 37.0, 0),
            ("ADP.2014-09-18T12:12:43.093", 54665.009753, 900.000, 35.0, 0),
        ],
    },
    {
        "campaign_order": 184, "star": "HIP79431", "instrument": "ESO_HARPS", "grating": "HARPS_378_691NM", "r": 115000.0,
        "orb_per_days": 111.7, "orb_ecc": 0.290, "orb_omega_deg": 287.4, "orb_t0_bjd": 2458500.00, "kp_kms": 0.14950,
        "exposures": [
            ("ADP.2019-07-28T01:08:01.363", 58691.139259, 899.998, 41.0, 0),
            ("ADP.2023-05-04T12:38:49.630", 60037.388412, 899.996, 44.0, 0),
            ("ADP.2023-05-04T15:16:14.161", 60041.385117, 899.996, 43.0, 0),
            ("ADP.2023-05-05T07:10:27.169", 60044.385590, 899.996, 42.0, 0),
            ("ADP.2023-05-05T07:42:07.025", 60046.294719, 899.996, 45.0, 0),
        ],
    },
    {
        "campaign_order": 185, "star": "HIP38594", "instrument": "ESO_HARPS", "grating": "HARPS_378_691NM", "r": 115000.0,
        "orb_per_days": 60.722, "orb_ecc": 0.170, "orb_omega_deg": 125.0, "orb_t0_bjd": 2453000.00, "kp_kms": 0.00189,
        "exposures": [
            ("ADP.2014-09-29T13:27:18.297", 52989.285983, 226.795, 26.0, 0),
            ("ADP.2014-09-29T13:27:20.970", 52991.263333, 226.796, 25.0, 0),
            ("ADP.2014-10-01T10:20:00.843", 53054.148556, 226.796, 27.0, 0),
            ("ADP.2014-10-01T10:21:24.777", 53358.269204, 348.381, 31.0, 0),
            ("ADP.2014-10-01T10:19:48.243", 53359.264406, 346.482, 30.0, 0),
        ],
    },
    {
        "campaign_order": 186, "star": "HIP54373", "instrument": "ESO_HARPS", "grating": "HARPS_378_691NM", "r": 115000.0,
        "orb_per_days": 7.760, "orb_ecc": 0.200, "orb_omega_deg": 72.340, "orb_t0_bjd": 2453000.00, "kp_kms": 0.00419,
        "exposures": [
            ("ADP.2014-10-01T10:21:27.810", 53062.266279, 899.995, 42.0, 0),
            ("ADP.2014-10-02T09:59:32.777", 53484.129760, 622.382, 36.0, 0),
            ("ADP.2014-09-16T11:05:08.290", 53785.240721, 622.402, 35.0, 0),
            ("ADP.2014-09-24T09:44:17.457", 55314.083808, 900.007, 46.0, 0),
            ("ADP.2014-09-25T15:37:05.490", 55683.022558, 622.400, 38.0, 0),
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
    base_url = url.split("#", 1)[0]
    last_exc: Exception | None = None
    for attempt in range(6):
        method = "HEAD" if attempt % 2 == 0 else "GET"
        headers = {"User-Agent": "SETI-V6.4-D106-Lock/1.0", "Connection": "close"}
        if method == "GET":
            headers["Range"] = "bytes=0-0"
        try:
            req = urllib.request.Request(base_url, method=method, headers=headers)
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

    ae_sha = _sha256_file(ARCHIVE_AE)
    b105_sha = _sha256_file(BUNDLE_105)
    if ae_sha != ARCHIVE_AE_SHA256 or b105_sha != BUNDLE_105_SHA256:
        raise RuntimeError(f"Archive AE or d105 bundle SHA mismatch ({ae_sha}, {b105_sha})")

    pe105 = json.loads((WS105 / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    d105_cohort = _read_csv(WS105 / "FROZEN_COHORT_D105.csv")
    u806_rows = _read_csv(WS105 / "results/UNIFIED_PANCHROMATIC_V6_3_SYNTHESIS_806STARS.csv")
    br1504_rows = _read_csv(WS105 / "results/PANCHROMATIC_BRIDGE_107STARS_V63.csv")
    comb_u539_rows = _read_csv(WS105 / "results/ALLSKY_COMB_V4_1_UNIFIED_D079_D105.csv")
    comb_c_rows = _read_csv(WS105 / "results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D105.csv")
    ell806_rows = _read_csv(WS105 / "results/MULTIEVENT_ELLIPSOID_806STARS.csv")
    s105 = json.loads((WS105 / "results/SUMMARY.json").read_text(encoding="utf-8"))

    u_map = {r["star"]: r for r in u806_rows}
    coord_by_star: dict[str, tuple[float, float]] = {
        r["star"]: (float(r["ra_deg"]), float(r["dec_deg"])) for r in ell806_rows
    }
    for t in pe105["excluded_targets_coordinate_registry"]:
        nm = str(t.get("canonical_target") or "").strip()
        if nm and nm not in coord_by_star:
            coord_by_star[nm] = (float(t["ra_deg"]), float(t["dec_deg"]))
    for r in d105_cohort:
        nm = r["canonical_target"]
        if nm not in coord_by_star:
            coord_by_star[nm] = (float(r["s_ra"]), float(r["s_dec"]))

    prior_coords: list[dict[str, Any]] = list(pe105["excluded_targets_coordinate_registry"])
    seen_d105_new = set()
    for r in d105_cohort:
        if str(r["is_prior_bridge"]).lower() not in ("true", "1", "yes"):
            nm = r["canonical_target"]
            if nm not in seen_d105_new:
                seen_d105_new.add(nm)
                prior_coords.append({"canonical_target": nm, "ra_deg": float(r["s_ra"]), "dec_deg": float(r["s_dec"])})

    prior_dp_ids = sorted(set(pe105["excluded_dp_ids"]) | {r["dp_id"] for r in d105_cohort})
    format_probes = sorted(set(pe105["format_check_excluded_dp_ids"]) | set(FORMAT_CHECK_EXTRA_D106))
    assert len(prior_coords) == 879, f"Expected 879 prior coords, got {len(prior_coords)}"
    assert len(prior_dp_ids) == 3702, f"Expected 3702 prior dp_ids, got {len(prior_dp_ids)}"
    assert len(format_probes) == 46, f"Expected 46 format probes, got {len(format_probes)}"

    rows: list[dict[str, Any]] = []

    # 1. 38 H.E.S.S. DR1 targets
    hess_base = "https://raw.githubusercontent.com/gammapy/gammapy-data/main/hess-dl3-dr1/data/"
    for canon, is_b, is_pb, mjd, rids in HESS_TARGETS:
        if is_b:
            assert canon in u_map, f"Missing HESS bridge {canon}"
        meta = _star_meta(canon, is_b, u_map, coord_by_star)
        fnames = [f"hess_dl3_dr1_obs_id_{oid:06d}.fits.gz" for oid in rids]
        extras = [
            {"rel": f"HESS_TEV/runs/{fn}", "url": f"{hess_base}{fn}", "bytes": HESS_RUN_BYTES[oid]}
            for fn, oid in zip(fnames[1:], rids[1:])
        ]
        tot_sz = sum(HESS_RUN_BYTES[oid] for oid in rids)
        rows.append(_make_row(
            inst="HESS_TEV", canon=canon, meta=meta, is_prior_bridge=is_b, panchromatic_bridge=bool(is_b or is_pb),
            science_track="HESS_DL3_DR1_TEV_V64", epoch_rank=1, dp_id=f"HESS_DR1_{canon}",
            grating="HESS_0P15_105TEV", resolving_power=6.7, mjd_obs=mjd, t_exptime=1550.0 * len(rids),
            phase_window="NONE", signed_phase=0.0, planet_orbital_rv_kms=0.0,
            f1_rel=f"HESS_TEV/runs/{fnames[0]}", f1_url=f"{hess_base}{fnames[0]}",
            f1_bytes=HESS_RUN_BYTES[rids[0]], total_bytes=tot_sz, extra_files_json=json.dumps(extras),
        ))

    # 2. 4 MAGIC AODR targets (16 blind runs from Zenodo 17064461)
    for canon, is_b, is_pb, mjd, mems in MAGIC_TARGETS:
        if is_b:
            assert canon in u_map, f"Missing MAGIC bridge {canon}"
        meta = _star_meta(canon, is_b, u_map, coord_by_star)
        m0_path, m0_sz = mems[0]
        extras = [
            {"rel": f"MAGIC_TEV/{canon}/{mp.rsplit('/', 1)[-1]}", "url": f"{MAGIC_AODR_URL}#{mp}", "bytes": sz}
            for mp, sz in mems[1:]
        ]
        tot_sz = sum(sz for _, sz in mems)
        rows.append(_make_row(
            inst="MAGIC_TEV", canon=canon, meta=meta, is_prior_bridge=is_b, panchromatic_bridge=bool(is_b or is_pb),
            science_track="MAGIC_AODR_TEV_V64", epoch_rank=1, dp_id=f"MAGIC_AODR_{canon}",
            grating="MAGIC_0P04_55TEV", resolving_power=5.9, mjd_obs=mjd, t_exptime=950.0 * len(mems),
            phase_window="NONE", signed_phase=0.0, planet_orbital_rv_kms=0.0,
            f1_rel=f"MAGIC_TEV/{canon}/{m0_path.rsplit('/', 1)[-1]}",
            f1_url=f"{MAGIC_AODR_URL}#{m0_path}", f1_bytes=m0_sz,
            total_bytes=tot_sz, extra_files_json=json.dumps(extras),
        ))

    # 3. 1 VERITAS DL3 Crab Nebula target (3 blind runs 64081-64083)
    ver_base = "https://raw.githubusercontent.com/gammapy/gammapy-data/main/veritas/crab-point-like-ED/"
    v0_fn, v0_sz = VERITAS_RUNS[0]
    v_extras = [{"rel": f"VERITAS_TEV/{fn}", "url": f"{ver_base}{fn}", "bytes": sz} for fn, sz in VERITAS_RUNS[1:]]
    meta_crab = _star_meta("CRABNEBULA", False, u_map, coord_by_star)
    rows.append(_make_row(
        inst="VERITAS_TEV", canon="CRABNEBULA", meta=meta_crab, is_prior_bridge=False, panchromatic_bridge=True,
        science_track="VERITAS_DL3_TEV_V64", epoch_rank=1, dp_id="VERITAS_CRAB_64081_64083",
        grating="VERITAS_0P10_18TEV", resolving_power=6.7, mjd_obs=56213.47, t_exptime=3034.1,
        phase_window="NONE", signed_phase=0.0, planet_orbital_rv_kms=0.0,
        f1_rel=f"VERITAS_TEV/{v0_fn}", f1_url=f"{ver_base}{v0_fn}", f1_bytes=v0_sz,
        total_bytes=sum(sz for _, sz in VERITAS_RUNS), extra_files_json=json.dumps(v_extras),
    ))

    # 4. 7 HAWC Pass-4 blind GP targets across fHitbin5GP..9GP
    h0_rel, h0_url, h0_sz = HAWC_GP_FILES[0]
    h_extras = [{"rel": rel, "url": u, "bytes": sz} for rel, u, sz in HAWC_GP_FILES[1:]]
    h_tot = sum(sz for _, _, sz in HAWC_GP_FILES)
    for canon, is_b, is_pb in HAWC_TARGETS:
        if is_b:
            assert canon in u_map, f"Missing HAWC bridge {canon}"
        meta = _star_meta(canon, is_b, u_map, coord_by_star)
        rows.append(_make_row(
            inst="HAWC_TEV", canon=canon, meta=meta, is_prior_bridge=is_b, panchromatic_bridge=bool(is_b or is_pb or canon in ("HD37124", "TOI4603")),
            science_track="HAWC_PASS4_GP_PEV_V64", epoch_rank=1, dp_id=f"HAWC_GP5_9_{canon}",
            grating="HAWC_1P5_315TEV", resolving_power=4.5, mjd_obs=57400.0, t_exptime=4884384.67,
            phase_window="NONE", signed_phase=0.0, planet_orbital_rv_kms=0.0,
            f1_rel=h0_rel, f1_url=h0_url, f1_bytes=h0_sz, total_bytes=h_tot, extra_files_json=json.dumps(h_extras),
        ))

    # 5. 14 brand-new < 10 pc + 5 Fermi-LAT -> Optical/NIR < 10 pc Multi-Phase Bridges
    for canon, is_b, inst, ref_id, mjd, exp_s, sz, r_pow, carm_dir in OPTICAL_10PC_AND_BRIDGES:
        if is_b:
            assert canon in u_map, f"Missing Fermi-bridge target {canon}"
        meta = _star_meta(canon, is_b, u_map, coord_by_star)
        if inst == "CARMENES_VIS":
            url = f"https://dc.g-vo.org/carmenes/q/sdl/static/{carm_dir}/{ref_id}"
            dp_id = f"CARM_{ref_id}"
            gr = "CARMENES_VIS_520_960NM"
            frel = f"CARMENES_VIS/{canon}/{ref_id}"
        else:
            url = f"https://dataportal.eso.org/dataportal_new/file/{ref_id}"
            dp_id = ref_id
            gr = {"ESO_ESPRESSO": "ESPRESSO_377_790NM", "ESO_NIRPS": "NIRPS_YJH_966_1923NM", "ESO_UVES": "UVES_328_1026NM", "ESO_FEROS": "FEROS_352_921NM"}[inst]
            frel = f"{inst}/{canon}/{ref_id}.fits"
        rows.append(_make_row(
            inst=inst, canon=canon, meta=meta, is_prior_bridge=is_b, panchromatic_bridge=bool(is_b),
            science_track="SOLAR_NEIGHBORHOOD_10PC_V64" if not is_b else "FERMI_TO_OPTICAL_10PC_BRIDGE_V64",
            epoch_rank=1, dp_id=dp_id, grating=gr, resolving_power=r_pow, mjd_obs=mjd, t_exptime=exp_s,
            phase_window="NONE", signed_phase=0.0, planet_orbital_rv_kms=0.0,
            f1_rel=frel, f1_url=url, f1_bytes=sz,
        ))

    # 6. 6 brand-new ESO Orbits #181-#186 (30 spectra)
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
                science_track=f"ORBITAL_CAMPAIGN_V64_{camp['campaign_order']}", epoch_rank=idx, dp_id=dp_id,
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
            "campaign_order": camp["campaign_order"], "phase_id": "D106",
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
    assert len(rows) == 99 and len(dp_set) == 99, f"Expected 99 unique obs, got {len(rows)}/{len(dp_set)}"
    overlap_dp = dp_set & (set(prior_dp_ids) | set(format_probes))
    assert not overlap_dp, f"dp_id overlap detected: {overlap_dp}"

    phys_urls: dict[str, tuple[str, int]] = {}
    for r in rows:
        phys_urls[r["f1_rel"]] = (r["f1_url"], int(r["f1_bytes"]))
        for ex in json.loads(r["extra_files"]):
            phys_urls[ex["rel"]] = (ex["url"], int(ex["bytes"]))
    assert len(phys_urls) == 116, f"Expected 116 physical files, got {len(phys_urls)}"
    for rel in phys_urls:
        bn = rel.rsplit("/", 1)[-1]
        assert bn not in set(format_probes), f"Format check probe leaked into cohort: {bn}"

    brand_new_stars = sorted({r["canonical_target"] for r in rows if r["is_prior_bridge"] == "False"})
    bridge_stars = sorted({r["canonical_target"] for r in rows if r["is_prior_bridge"] == "True"})
    assert len(brand_new_stars) == 46, f"Expected 46 brand-new stars, got {len(brand_new_stars)}"
    assert len(bridge_stars) == 24, f"Expected 24 prior bridges, got {len(bridge_stars)}"

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
            assert sp >= 120.0, f"Intra-D106 overlap {s1}/{s2}: {sp:.2f}'' < 120''"

    # Live HTTP 200 verification on unique physical URLs BEFORE sealing
    # Group Zenodo URLs sharing MAGIC_AODR_URL so we check Zenodo once and direct URLs individually
    unique_http_checks: dict[str, tuple[str, int]] = {}
    for rel, (u, sz) in sorted(phys_urls.items()):
        base_u = u.split("#", 1)[0]
        if base_u == MAGIC_AODR_URL:
            unique_http_checks["MAGIC_AODR_ZIP"] = (base_u, 767092865)
        else:
            unique_http_checks[rel] = (base_u, sz)

    check_list = sorted(unique_http_checks.items())
    print(f"Verifying HTTP 200 on all {len(check_list)} unique upstream URLs (covering {len(phys_urls)} files)...", flush=True)
    with ThreadPoolExecutor(max_workers=4) as ex:
        head_res = []
        for idx, res in enumerate(ex.map(lambda it: (it[0], it[1][0], *_http_head(it[1][0]), it[1][1]), check_list), 1):
            head_res.append(res)
            if idx % 25 == 0 or idx == len(check_list):
                print(f"  verified {idx}/{len(check_list)} URLs...", flush=True)
    for rel, u, st, b, exp_b in head_res:
        assert st == 200, f"HEAD failed {rel} ({u}): HTTP {st}"
        if exp_b > 0 and b > 0:
            assert b == exp_b, f"HEAD bytes mismatch {rel}: got {b}, expected {exp_b}"
    print("All upstream HTTP 200 checks passed.")

    with open(WS / "FROZEN_COHORT_D106.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COHORT_COLS)
        w.writeheader()
        w.writerows(rows)

    tot_bytes = sum(sz for _, (_, sz) in phys_urls.items() if sz > 0)
    n_new_10pc = sum(1 for s in brand_new_stars if NEW_META[s]["d"] < 10.0)
    assert n_new_10pc == 14, f"Expected +14 new <10 pc stars (230 -> 244), got {n_new_10pc}"

    now_utc = datetime.now(timezone.utc)
    locked_utc = now_utc.isoformat()
    locked_epoch = now_utc.timestamp()

    pe_out = {
        "schema": "D106_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D106",
        "verified_utc": locked_utc,
        "prior_phases_covered": "C001-C037 + D001-D105",
        "n_prior_excluded_coords": len(prior_coords),
        "n_prior_excluded_dp_ids": len(prior_dp_ids),
        "n_format_check_excluded_dp_ids": len(format_probes),
        "d106_total_stars": len(brand_new_stars) + len(bridge_stars),
        "d106_brand_new_unique_stars": len(brand_new_stars),
        "d106_prior_bridge_stars": len(bridge_stars),
        "d106_control_stars": sum(1 for s in brand_new_stars if NEW_META[s]["role"] == "CONTROL") + sum(1 for s in bridge_stars if u_map[s]["role"] == "CONTROL"),
        "d106_brand_new_within_10pc": n_new_10pc,
        "d106_total_observations": len(rows),
        "d106_total_physical_files": len(phys_urls),
        "d106_projected_download_bytes": tot_bytes,
        "d106_projected_download_mib": round(tot_bytes / (1024.0 * 1024.0), 3),
        "d106_dp_id_overlap_count": 0,
        "min_brand_new_sky_separation_arcsec": round(min_prior_sep, 2),
        "min_intra_d106_separation_arcsec": round(min_intra_sep, 2),
        "star_separation_verification": sep_verif,
        "format_check_excluded_dp_ids": format_probes,
        "excluded_dp_ids": prior_dp_ids,
        "excluded_targets_coordinate_registry": prior_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pe_out, indent=2) + "\n", encoding="utf-8")

    uni105 = s105["unified_806star_panchromatic_v6_3_synthesis"]
    snap_out = {
        "schema": "D106_PRIOR_V6_3_PHASES_SNAPSHOT",
        "prior_phases": "C001-C037 + D001-D105",
        "source_archive_ae_name": ARCHIVE_AE.name,
        "source_archive_ae_sha256": ARCHIVE_AE_SHA256,
        "source_archive_ae_bundle_member": "work_v6_3_20261124_d105_mev_gev_gamma_osse_comptel_fermi_lat_800star/bounded_inputs/d105_bounded_bundle.json.gz",
        "source_archive_ae_bundle_sha256": BUNDLE_105_SHA256,
        "prior_unique_stars_count": len(u806_rows),
        "prior_science_stars_count": int(uni105["science_stars_total"]),
        "prior_control_stars_count": int(uni105["control_stars_total"]),
        "prior_planet_host_stars_count": int(uni105["planet_host_stars_total"]),
        "prior_confirmed_exoplanets_count": int(uni105["confirmed_exoplanets_total"]),
        "prior_within_10pc_count": int(uni105["within_10pc_unique_stars"]),
        "prior_total_exposures_count": int(uni105["total_exposures_d079_d105"]),
        "prior_cumulative_integration_hours": float(uni105["total_integration_hours_d079_d105"]),
        "prior_calibration_trials_count": int(uni105["total_calibration_trials_d079_d105"]),
        "prior_v2_false_alarms_eliminated_total": int(uni105["v2_false_alarms_eliminated_total"]),
        "prior_cumulative_orbital_campaigns_count": int(uni105["cumulative_orbital_campaigns"]),
        "prior_panchromatic_bridge_stars_count": int(uni105["panchromatic_bridge_stars_total"]),
        "prior_revisited_control_multi_phase_stars": int(uni105["revisited_control_multi_phase_stars"]),
        "prior_multi_phase_targets_total": int(uni105["multi_phase_targets_total"]),
        "prior_panchromatic_bridge_cells_count": int(uni105["panchromatic_bridge_cells_total"]),
        "prior_cumulative_comb_stacks": int(uni105["cumulative_comb_stacks"]),
        "prior_coherent_eccentric_keplerian_campaigns": int(uni105["coherent_eccentric_keplerian_campaigns"]),
        "d105_summary_headline": uni105,
        "prior_unified_806_rows": u806_rows,
        "prior_bridge_107_rows": br1504_rows,
        "prior_allsky_comb_unified_rows": comb_u539_rows,
        "prior_allsky_comb_candidate_rows": comb_c_rows,
        "prior_ellipsoid_806_rows": ell806_rows,
    }
    (WS / "PRIOR_V6_3_PHASES_SNAPSHOT.json").write_text(json.dumps(snap_out, indent=2) + "\n", encoding="utf-8")

    orb_out = {
        "schema": "D106_ORBITAL_CAMPAIGNS_AND_KINEMATICS",
        "phase_id": "D106",
        "campaign_range": [181, 186],
        "campaigns": orbital_campaigns,
    }
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_out, indent=2) + "\n", encoding="utf-8")

    stage1_names = [
        "v6_4_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D106.csv",
        "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "PRIOR_V6_3_PHASES_SNAPSHOT.json",
    ]
    stage1_hashes = {fn: _sha256_file(WS / fn) for fn in stage1_names}

    ml = {
        "schema": "D106_PROSPECTIVE_METHOD_LOCK",
        "phase_id": "D106",
        "detector_version": "V6.4",
        "detector": det.DETECTOR_NAME,
        "locked_utc": locked_utc,
        "projected_unified_stars": 806 + len(brand_new_stars),
        "projected_within_10pc_stars": 230 + n_new_10pc,
        "d106_brand_new_stars": len(brand_new_stars),
        "d106_prior_bridges": len(bridge_stars),
        "d106_total_observations": len(rows),
        "d106_total_physical_files": len(phys_urls),
        "d106_projected_bytes": tot_bytes,
        "d106_projected_mib": round(tot_bytes / (1024.0 * 1024.0), 3),
        "stage_1_files": stage1_hashes,
    }
    (WS / "METHOD_LOCK.json").write_text(json.dumps(ml, indent=2) + "\n", encoding="utf-8")
    ml_sha = _sha256_file(WS / "METHOD_LOCK.json")

    lr = {
        "schema": "D106_LOCK_RECEIPT",
        "phase_id": "D106",
        "status": "STAGE-1 SEALED",
        "locked_utc": locked_utc,
        "locked_unix_epoch": round(locked_epoch, 4),
        "method_lock_sha256": ml_sha,
        "inputs_dir_exists_at_seal": RAW_DIR.exists(),
        "locked_files": stage1_hashes,
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lr, indent=2) + "\n", encoding="utf-8")
    print(f"STAGE-1 SEALED: obs={len(rows)}, files={len(phys_urls)}, brand_new={len(brand_new_stars)} (+{n_new_10pc} <10pc -> {230+n_new_10pc}), unified={806+len(brand_new_stars)}, min_prior_sep={min_prior_sep:.1f}'', min_intra_sep={min_intra_sep:.1f}'', raw_dir_exists={RAW_DIR.exists()}, proj_mib={ml['d106_projected_mib']}")


if __name__ == "__main__":
    main()
