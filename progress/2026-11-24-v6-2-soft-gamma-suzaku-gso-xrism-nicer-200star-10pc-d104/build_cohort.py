#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D104 (`V6.2`) Stage-1 Prospective Method Lock & Cohort Builder.
Locks:
  - 18 Suzaku HXD-GSO soft gamma-ray (50-600 keV) event files
  - 20 XRISM Resolve microcalorimeter (1.70-12.00 keV, FILTER=OPEN, PIXEL!=12) event files
  - 20 NICER XTI (0.35-10.00 keV) event files
  - 16 brand-new <10 pc CARMENES VIS (R=94,600) M-dwarf spectra
  - 30 ESO ESPRESSO/HARPS spectra forming 6 N>=5 orbital campaigns (#169-#174)
Verifies 0 overlap with 3,472 prior dp_ids and 30 format-check probes, >=300" sky separation
from 782 prior stars, >=120" intra-D104 separation, HTTP 200 URLs, and absence of $RAW104
before writing METHOD_LOCK.json and LOCK_RECEIPT.json.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent
ROOT = WS.parent.parent
RAW_DIR = ROOT / "inputs_d104_v6_2"
WS103 = ROOT / "analysis_workspace/work_v6_1_20261123_d103_hard_xray_nustar_xmm_rgs_alma_b9b10_700star"
ARCHIVE_AC = ROOT / "archives/SETI_D103_V6_1_HARD_XRAY_NUSTAR_XMM_RGS_ALMA_B9B10_700STAR_RESULTS_2026-11-23.zip"
BUNDLE_103 = WS103 / "bounded_inputs/d103_bounded_bundle.json.gz"

if str(WS) not in sys.path:
    sys.path.insert(0, str(WS))
import v6_2_detector as det  # noqa: E402

C_KMS = det.C_KMS
ARCHIVE_AC_SHA256 = "d0155c0b3c98625c0e8f9cff5f55ccb89d7477e6ada6b3fd18a0ba8cc6615de4"
BUNDLE_103_SHA256 = "3246933c707dd7780049f575ffe4514c82d28aa7563e7d72904437bd879f590f"

FORMAT_CHECK_EXTRA_D104 = [
    "XRISM_000100000",
    "SUZAKU_401022010",
    "SUZAKU_404075110",
    "NICER_1012010101",
]

# Brand-new D104 target metadata (verified via Gaia DR3, MAST TIC v8.2, HyperLEDA, NASA Exoplanet Archive)
NEW_META: dict[str, dict[str, Any]] = {
    # --- 16 CARMENES < 10 pc Northern/Equatorial M dwarfs ---
    "J12189+111": {"common_name": "GJ 1156 (GL Vir)", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "3907283967108054528", "ra": 184.74175, "dec": 11.12695, "pmra": -1269.77, "pmdec": 203.44, "d": 6.464, "g": 11.9261, "bp": 14.1005, "rp": 10.5672, "j": 8.525, "h": 7.880, "k": 7.570, "teff": 2948.0, "mass": 0.1425, "rv": 5.0, "n_pl": 0, "tr": False},
    "J18482+076": {"common_name": "G 141-36", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "4286249341336984576", "ra": 282.07476, "dec": 7.69032, "pmra": 376.04, "pmdec": 248.72, "d": 7.617, "g": 12.2969, "bp": 14.4584, "rp": 10.9455, "j": 8.853, "h": 8.261, "k": 7.913, "teff": 2957.0, "mass": 0.1432, "rv": -34.6381, "n_pl": 0, "tr": False},
    "J18189+661": {"common_name": "LP 71-82", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "2257597439718033536", "ra": 274.74326, "dec": 66.19062, "pmra": 434.81, "pmdec": -442.79, "d": 7.642, "g": 11.9117, "bp": 13.7527, "rp": 10.6238, "j": 8.740, "h": 8.264, "k": 7.948, "teff": 3120.0, "mass": 0.1415, "rv": 5.4681, "n_pl": 0, "tr": False},
    "J02442+255": {"common_name": "GJ 109 (VX Ari)", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "114207651462714880", "ra": 41.06888, "dec": 25.52175, "pmra": 864.53, "pmdec": -363.20, "d": 7.681, "g": 9.4673, "bp": 10.8165, "rp": 8.3163, "j": 6.752, "h": 6.197, "k": 5.961, "teff": 3430.0, "mass": 0.3558, "rv": 30.2549, "n_pl": 0, "tr": False},
    "J18022+642": {"common_name": "LP 70-182", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "2161121135533953536", "ra": 270.57119, "dec": 64.26058, "pmra": 196.39, "pmdec": -383.79, "d": 7.794, "g": 11.7581, "bp": 13.7073, "rp": 10.4484, "j": 8.541, "h": 7.962, "k": 7.652, "teff": 3062.0, "mass": 0.1641, "rv": 0.0, "n_pl": 0, "tr": False},
    "J20305+654": {"common_name": "GJ 793", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "2246206567973292160", "ra": 307.63826, "dec": 65.45082, "pmra": 443.26, "pmdec": 283.35, "d": 8.087, "g": 9.4353, "bp": 10.7697, "rp": 8.2856, "j": 6.735, "h": 6.136, "k": 5.933, "teff": 3437.0, "mass": 0.3771, "rv": 10.1803, "n_pl": 0, "tr": False},
    "J18224+620": {"common_name": "GJ 1227", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "2159844052779000064", "ra": 275.60384, "dec": 62.04499, "pmra": -955.10, "pmdec": -1235.61, "d": 8.351, "g": 11.8240, "bp": 13.6844, "rp": 10.5253, "j": 8.642, "h": 8.055, "k": 7.742, "teff": 3072.0, "mass": 0.1700, "rv": -15.0430, "n_pl": 0, "tr": False},
    "J13005+056": {"common_name": "GJ 493.1 (FN Vir)", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "3705324881045028992", "ra": 195.13547, "dec": 5.68657, "pmra": -940.63, "pmdec": 227.75, "d": 8.545, "g": 11.7729, "bp": 13.6556, "rp": 10.4682, "j": 8.553, "h": 7.966, "k": 7.660, "teff": 3092.0, "mass": 0.1799, "rv": -27.4927, "n_pl": 0, "tr": False},
    "J15305+094": {"common_name": "NLTT 40406", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "1165479168642900992", "ra": 232.62556, "dec": 9.43455, "pmra": -178.85, "pmdec": 183.90, "d": 8.618, "g": 13.0703, "bp": 15.3960, "rp": 11.6908, "j": 9.575, "h": 8.952, "k": 8.605, "teff": 2880.0, "mass": 0.1200, "rv": 2.7889, "n_pl": 0, "tr": False},
    "J11511+352": {"common_name": "GJ 450", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "4031586157514097024", "ra": 177.77908, "dec": 35.27314, "pmra": -273.16, "pmdec": 253.40, "d": 8.765, "g": 8.8540, "bp": 9.9673, "rp": 7.8048, "j": 6.419, "h": 5.828, "k": 5.606, "teff": 3640.0, "mass": 0.4577, "rv": -0.3498, "n_pl": 0, "tr": False},
    "J22012+283": {"common_name": "GJ 4247 (V374 Peg)", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "1893189736896880640", "ra": 330.30657, "dec": 28.30711, "pmra": 372.80, "pmdec": 42.80, "d": 9.103, "g": 10.6348, "bp": 12.2698, "rp": 9.3960, "j": 7.635, "h": 7.035, "k": 6.777, "teff": 3240.0, "mass": 0.2914, "rv": -6.4375, "n_pl": 0, "tr": False},
    "J13582+125": {"common_name": "GJ 3817", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "3727748630418376704", "ra": 209.55651, "dec": 12.58206, "pmra": -329.60, "pmdec": 720.34, "d": 9.360, "g": 11.0512, "bp": 12.5237, "rp": 9.8632, "j": 8.269, "h": 7.687, "k": 7.439, "teff": 3342.0, "mass": 0.2188, "rv": 0.0, "n_pl": 0, "tr": False},
    "J06103+821": {"common_name": "GJ 226", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "1143321672882274560", "ra": 92.58432, "dec": 82.10082, "pmra": 50.26, "pmdec": -1336.25, "d": 9.462, "g": 9.4701, "bp": 10.7199, "rp": 8.3569, "j": 6.869, "h": 6.295, "k": 6.061, "teff": 3506.0, "mass": 0.4111, "rv": -2.0165, "n_pl": 0, "tr": False},
    "J20405+154": {"common_name": "GJ 1256", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "1810616448010879488", "ra": 310.14719, "dec": 15.50259, "pmra": 1320.68, "pmdec": 662.15, "d": 9.531, "g": 11.8374, "bp": 13.6851, "rp": 10.5430, "j": 8.641, "h": 8.075, "k": 7.752, "teff": 3085.0, "mass": 0.1800, "rv": -59.2992, "n_pl": 0, "tr": False},
    "J01048-181": {"common_name": "GJ 1028", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "2358022227591374336", "ra": 16.23022, "dec": -18.12245, "pmra": 1292.19, "pmdec": 488.10, "d": 9.777, "g": 12.6972, "bp": 14.7776, "rp": 11.3576, "j": 9.387, "h": 8.753, "k": 8.453, "teff": 2960.0, "mass": 0.1390, "rv": 12.4903, "n_pl": 0, "tr": False},
    "J04376+528": {"common_name": "GJ 172", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_M_DWARF", "sid": "272855565763652480", "ra": 69.42278, "dec": 52.89150, "pmra": 304.13, "pmdec": -475.15, "d": 9.909, "g": 7.9525, "bp": 8.8299, "rp": 7.0314, "j": 5.869, "h": 5.280, "k": 5.058, "teff": 3760.6, "mass": 0.5600, "rv": 33.7258, "n_pl": 0, "tr": False},

    # --- 10 Brand-New NICER XTI Stellar Targets (incl. 2 new <10 pc) ---
    "WOLF424":      {"common_name": "Wolf 424 (FL Vir, 4.33 pc)", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_FLARE", "sid": "3902874650602495232", "ra": 188.31449, "dec": 9.02209, "pmra": -1795.66, "pmdec": 217.79, "d": 4.327, "g": 11.2351, "bp": 12.9160, "rp": 9.3818, "j": 6.995, "h": 6.397, "k": 6.042, "teff": 2900.0, "mass": 0.1946, "rv": 0.0, "n_pl": 0, "tr": False},
    "APCOL":        {"common_name": "AP Columbae (8.67 pc Pre-MS Flare)", "role": "SCIENCE", "subrole": "SOLAR_NEIGHBORHOOD_10PC_FLARE", "sid": "2886233695250041216", "ra": 91.21743, "dec": -34.55841, "pmra": 25.79, "pmdec": 343.02, "d": 8.666, "g": 11.1121, "bp": 13.1743, "rp": 9.7740, "j": 7.742, "h": 7.183, "k": 6.866, "teff": 2998.0, "mass": 0.2658, "rv": 23.9118, "n_pl": 0, "tr": False},
    "DGCVN":        {"common_name": "DG CVn (Superflare Binary)", "role": "SCIENCE", "subrole": "ACTIVE_FLARE_M_DWARF", "sid": "1450067137649449728", "ra": 202.94423, "dec": 29.27689, "pmra": -234.26, "pmdec": -157.06, "d": 15.588, "g": 10.6074, "bp": None, "rp": None, "j": 7.561, "h": 7.002, "k": 6.720, "teff": 3229.0, "mass": 0.5351, "rv": -8.9358, "n_pl": 0, "tr": False},
    "GJ1243":       {"common_name": "GJ 1243 (Kepler Flare M4V)", "role": "SCIENCE", "subrole": "ACTIVE_FLARE_M_DWARF", "sid": "2080285727861817088", "ra": 297.79002, "dec": 46.48457, "pmra": 183.24, "pmdec": 265.70, "d": 11.977, "g": 11.5439, "bp": 13.1524, "rp": 10.3170, "j": 8.586, "h": 8.045, "k": 7.773, "teff": 3261.0, "mass": 0.2412, "rv": -13.3995, "n_pl": 0, "tr": False},
    "CRDRA":        {"common_name": "CR Dra (BY Dra Flare Binary)", "role": "SCIENCE", "subrole": "ACTIVE_FLARE_M_DWARF", "sid": "1429437378934511616", "ra": 244.27299, "dec": 55.26719, "pmra": 87.97, "pmdec": -430.96, "d": 20.149, "g": 9.0784, "bp": 10.1844, "rp": 8.0149, "j": 6.640, "h": 6.060, "k": 5.830, "teff": 3550.0, "mass": 0.5800, "rv": -32.8097, "n_pl": 0, "tr": False},
    "TIC167344043": {"common_name": "TIC 167344043 (TESS CVZ Flare)", "role": "SCIENCE", "subrole": "ACTIVE_SOLAR_ANALOG", "sid": "5278895306528592000", "ra": 98.67103, "dec": -69.88488, "pmra": 18.54, "pmdec": 37.59, "d": 72.148, "g": 9.0597, "bp": 9.3871, "rp": 8.5302, "j": 8.000, "h": 7.700, "k": 7.620, "teff": 5693.5, "mass": 0.9800, "rv": 16.2722, "n_pl": 0, "tr": False},
    "TIC364588501": {"common_name": "TIC 364588501 (TESS CVZ Flare)", "role": "SCIENCE", "subrole": "ACTIVE_SOLAR_ANALOG", "sid": "4648371640502768896", "ra": 85.40315, "dec": -76.07237, "pmra": 37.18, "pmdec": 99.62, "d": 109.751, "g": 9.6751, "bp": 10.0390, "rp": 9.1362, "j": 8.454, "h": 8.110, "k": 8.006, "teff": 5791.8, "mass": 0.9900, "rv": 3.7464, "n_pl": 0, "tr": False},
    "RULUP":        {"common_name": "RU Lupi (Classical T Tauri)", "role": "CONTROL", "subrole": "CLASSICAL_TTAU_ACCRETOR", "sid": "6010114558131195392", "ra": 239.17623, "dec": -37.82107, "pmra": -11.46, "pmdec": -23.21, "d": 157.508, "g": 10.7102, "bp": 11.2891, "rp": 9.9705, "j": 8.732, "h": 7.824, "k": 7.138, "teff": 4857.0, "mass": 0.9000, "rv": 0.0, "n_pl": 0, "tr": False},
    "GMAUR":        {"common_name": "GM Aur (Transition Disk CTTS)", "role": "CONTROL", "subrole": "CLASSICAL_TTAU_ACCRETOR", "sid": "156907907082740480", "ra": 73.79576, "dec": 30.36649, "pmra": 3.90, "pmdec": -24.45, "d": 158.951, "g": 11.7000, "bp": None, "rp": None, "j": 9.341, "h": 8.603, "k": 8.283, "teff": 4189.0, "mass": 1.0000, "rv": -1.1212, "n_pl": 0, "tr": False},
    "WR133":        {"common_name": "WR 133 (WN5o+O9I Colliding Wind)", "role": "CONTROL", "subrole": "COLLIDING_WIND_WR_BINARY", "sid": "2059076148587289728", "ra": 301.48883, "dec": 35.78835, "pmra": -3.18, "pmdec": -6.54, "d": 1858.614, "g": 6.7464, "bp": 6.8112, "rp": 6.5612, "j": 6.319, "h": 6.315, "k": 6.247, "teff": 40000.0, "mass": 15.0000, "rv": 0.0, "n_pl": 0, "tr": False},

    # --- 4 Intra-D104 Shared Suzaku + XRISM Brand-New Targets ---
    "NGC4945":      {"common_name": "NGC 4945 (Compton-Thick Seyfert 2)", "role": "CONTROL", "subrole": "AGN_EXTRAGALACTIC_CAL", "sid": "NGC4945", "ra": 196.36449, "dec": -49.46817, "pmra": 0.0, "pmdec": 0.0, "d": 3470000.0, "g": 9.30, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 5200.0, "mass": 1.0, "rv": 564.0, "n_pl": 0, "tr": False},
    "CENA":         {"common_name": "Centaurus A / NGC 5128 (Radio AGN)", "role": "CONTROL", "subrole": "AGN_EXTRAGALACTIC_CAL", "sid": "CENA", "ra": 201.36506, "dec": -43.01911, "pmra": 0.0, "pmdec": 0.0, "d": 3680000.0, "g": 7.84, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 5000.0, "mass": 1.0, "rv": 552.0, "n_pl": 0, "tr": False},
    "IC4329A":      {"common_name": "IC 4329A (Seyfert 1.2AGN Fe-K Cal)", "role": "CONTROL", "subrole": "AGN_EXTRAGALACTIC_CAL", "sid": "IC4329A", "ra": 207.33026, "dec": -30.30951, "pmra": 0.0, "pmdec": 0.0, "d": 69500000.0, "g": 13.50, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 6000.0, "mass": 1.0, "rv": 4818.0, "n_pl": 0, "tr": False},
    "SSCYG":        {"common_name": "SS Cygni (Dwarf Nova Cataclysmic Var)", "role": "SCIENCE", "subrole": "CATACLYSMIC_XRAY_BINARY", "sid": "1972957892448494592", "ra": 325.67835, "dec": 43.58607, "pmra": 112.37, "pmdec": 33.59, "d": 112.942, "g": 11.6712, "bp": 12.1249, "rp": 10.9482, "j": 8.516, "h": 8.356, "k": 8.299, "teff": 4597.7, "mass": 0.7270, "rv": 0.0, "n_pl": 0, "tr": False},

    # --- 4 Suzaku-Only Brand-New Targets ---
    "HD162020":     {"common_name": "HD 162020 (bd-host K2V)", "role": "SCIENCE", "subrole": "PLANET_HOST_HARD_XRAY", "sid": "5957920668132624256", "ra": 267.65981, "dec": -40.31836, "pmra": 20.28, "pmdec": -25.32, "d": 30.825, "g": 8.7659, "bp": 9.3175, "rp": 8.0547, "j": 7.175, "h": 6.649, "k": 6.539, "teff": 4723.0, "mass": 0.7700, "rv": 0.0, "n_pl": 1, "tr": False, "mh": -0.10},
    "AEAQR":        {"common_name": "AE Aquarii (Magnetic Propeller)", "role": "CONTROL", "subrole": "MAGNETIC_PROPELLER_CV", "sid": "4226332451596335616", "ra": 310.03817, "dec": -0.87085, "pmra": 70.56, "pmdec": 13.12, "d": 90.956, "g": 10.9525, "bp": None, "rp": None, "j": 9.459, "h": 8.917, "k": 8.773, "teff": 4770.0, "mass": 0.7700, "rv": 0.0, "n_pl": 0, "tr": False},
    "CHCYG":        {"common_name": "CH Cygni (Symbiotic Giant+WD)", "role": "SCIENCE", "subrole": "SYMBIOTIC_BINARY", "sid": "2130088038314195200", "ra": 291.13779, "dec": 50.24140, "pmra": -8.31, "pmdec": -11.42, "d": 182.552, "g": 5.3688, "bp": 7.8958, "rp": 3.9776, "j": 1.073, "h": 0.051, "k": -0.419, "teff": 3084.0, "mass": 1.5000, "rv": -59.4098, "n_pl": 0, "tr": False},
    "BETALYR":      {"common_name": "Beta Lyrae (Sheliak Eclipsing Binary)", "role": "CONTROL", "subrole": "INTERACTING_ECLIPSING_BINARY", "sid": "2090687795056051328", "ra": 282.51999, "dec": 33.36267, "pmra": 2.05, "pmdec": -3.68, "d": 277.913, "g": 3.6049, "bp": 3.6659, "rp": 3.4552, "j": 3.367, "h": 3.351, "k": 3.192, "teff": 17700.2, "mass": 3.0000, "rv": -29.4825, "n_pl": 0, "tr": False},

    # --- 6 XRISM-Only Brand-New Targets ---
    "GTMUS":        {"common_name": "GT Muscae (Quadruple RS CVn System)", "role": "SCIENCE", "subrole": "ACTIVE_RSCVN_MICROCAL", "sid": "5236523877939131008", "ra": 174.87320, "dec": -65.39776, "pmra": -29.76, "pmdec": 5.78, "d": 119.088, "g": 4.9186, "bp": 5.4320, "rp": 4.2254, "j": 3.359, "h": 2.710, "k": 2.472, "teff": 5954.6, "mass": 1.4000, "rv": 1.1906, "n_pl": 0, "tr": False},
    "EXHYA":        {"common_name": "EX Hydrae (Intermediate Polar CV)", "role": "CONTROL", "subrole": "MAGNETIC_CV_INTERMEDIATE_POLAR", "sid": "6185040879503491584", "ra": 193.10093, "dec": -29.24889, "pmra": -119.47, "pmdec": 30.33, "d": 56.910, "g": 13.2463, "bp": 13.3451, "rp": 12.9291, "j": 12.274, "h": 11.950, "k": 11.687, "teff": 5000.0, "mass": 0.7800, "rv": 0.0, "n_pl": 0, "tr": False},
    "PIAQR":        {"common_name": "Pi Aquarii (Gamma Cas-Type Be Star)", "role": "SCIENCE", "subrole": "GAMMA_CAS_BE_STAR", "sid": "2702544403629124224", "ra": 336.31926, "dec": 1.37740, "pmra": 17.52, "pmdec": 2.56, "d": 289.358, "g": 4.5251, "bp": 4.5195, "rp": 4.4579, "j": 5.305, "h": 5.365, "k": 5.351, "teff": 25000.0, "mass": 11.0000, "rv": 0.0, "n_pl": 0, "tr": False},
    "AMHER":        {"common_name": "AM Herculis (Prototype Polar CV)", "role": "CONTROL", "subrole": "MAGNETIC_CV_POLAR", "sid": "2123837555230207744", "ra": 274.05521, "dec": 49.86802, "pmra": -45.97, "pmdec": 28.05, "d": 88.118, "g": 13.5800, "bp": None, "rp": None, "j": 11.703, "h": 11.195, "k": 11.002, "teff": 4200.0, "mass": 0.7800, "rv": 0.0, "n_pl": 0, "tr": False},
    "GAMMACAS":     {"common_name": "Gamma Cassiopeiae (Prototype Be X-Ray)", "role": "SCIENCE", "subrole": "GAMMA_CAS_BE_STAR", "sid": "426558460877467776", "ra": 14.17722, "dec": 60.71674, "pmra": 24.95, "pmdec": -3.89, "d": 168.400, "g": 2.0646, "bp": None, "rp": None, "j": 2.039, "h": 1.993, "k": 1.756, "teff": 25000.0, "mass": 13.0000, "rv": 0.0, "n_pl": 0, "tr": False},
    "V2400OPH":     {"common_name": "V2400 Ophiuchi (Diskless Polar CV)", "role": "CONTROL", "subrole": "MAGNETIC_CV_INTERMEDIATE_POLAR", "sid": "4112610784274894208", "ra": 258.15176, "dec": -24.24577, "pmra": -1.64, "pmdec": 2.63, "d": 701.082, "g": 14.0558, "bp": None, "rp": None, "j": 13.482, "h": 13.209, "k": 13.025, "teff": 7952.0, "mass": 0.8000, "rv": 0.0, "n_pl": 0, "tr": False},

    # --- 6 ESO Orbits #169-#174 Brand-New Exoplanet Hosts ---
    "HD210277":     {"common_name": "HD 210277", "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "2619706544757416192", "ra": 332.37482, "dec": -7.55066, "pmra": 85.0, "pmdec": -450.0, "d": 21.344, "g": 6.3590, "bp": None, "rp": None, "j": 5.275, "h": 4.957, "k": 4.799, "teff": 5538.0, "mass": 1.0100, "rv": -20.7780, "n_pl": 1, "tr": False, "mh": 0.22},
    "L168_9":       {"common_name": "L 168-9 (TOI-134)", "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "6491962300492857472", "ra": 350.02850, "dec": -60.06575, "pmra": 254.0, "pmdec": -503.0, "d": 25.182, "g": 10.2373, "bp": None, "rp": None, "j": 7.941, "h": 7.320, "k": 7.082, "teff": 3842.0, "mass": 0.6140, "rv": 29.4385, "n_pl": 1, "tr": True, "mh": -0.03},
    "TOI836":       {"common_name": "TOI-836 (HIP 73427)", "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "6230733559097425152", "ra": 225.07985, "dec": -24.45421, "pmra": -186.0, "pmdec": -178.0, "d": 27.508, "g": 9.4071, "bp": None, "rp": None, "j": 7.580, "h": 6.983, "k": 6.804, "teff": 4552.0, "mass": 0.6780, "rv": -26.5638, "n_pl": 2, "tr": True, "mh": -0.284},
    "HD95338":      {"common_name": "HD 95338", "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "5340648488081462528", "ra": 164.85623, "dec": -56.62357, "pmra": -185.0, "pmdec": 115.0, "d": 36.966, "g": 8.3923, "bp": None, "rp": None, "j": 7.099, "h": 6.729, "k": 6.591, "teff": 5097.0, "mass": 0.8480, "rv": 96.5239, "n_pl": 1, "tr": True, "mh": 0.08},
    "HD86226":      {"common_name": "HD 86226", "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "5660492297395345408", "ra": 149.12349, "dec": -24.09918, "pmra": -177.0, "pmdec": 62.0, "d": 45.599, "g": 7.7838, "bp": None, "rp": None, "j": 6.839, "h": 6.577, "k": 6.463, "teff": 5863.0, "mass": 1.0190, "rv": 19.6199, "n_pl": 2, "tr": True, "mh": 0.018},
    "TOI500":       {"common_name": "TOI-500 (HIP 34269)", "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "5509620021956148736", "ra": 106.55913, "dec": -47.58784, "pmra": -33.0, "pmdec": 163.0, "d": 47.410, "g": 10.1038, "bp": None, "rp": None, "j": 8.403, "h": 7.848, "k": 7.715, "teff": 4440.0, "mass": 0.7400, "rv": 55.8376, "n_pl": 4, "tr": True, "mh": 0.12},
}

# 18 Suzaku HXD-GSO observations (10 prior bridges + 8 brand-new)
SUZAKU_OBS: list[tuple[str, str, bool, float, float, int]] = [
    ("401031020", "ABDOR",    True,  54108.0648, 44961.1, 115480689),
    ("403037010", "ETACAR",   True,  54856.1332, 17453.9,  51023197),
    ("100008010", "NGC4945",  False, 53604.7788, 13806.7,  22447868),
    ("708036010", "CENA",     False, 56519.1824, 10064.7,  25118763),
    ("406037030", "HD162020", False, 55824.6499, 13378.4,  39216500),
    ("702113050", "IC4329A",  False, 54332.9766, 18825.6,  49835337),
    ("102020010", "PKS2155",  True,  54212.5209, 10572.0,  26670200),
    ("400001020", "AEAQR",    False, 54033.2320, 45538.4, 113949800),
    ("701039010", "NGC1068",  True,  54141.0038, 41802.4, 104740206),
    ("107013010", "3C273",    True,  56124.3395, 35778.3,  94833007),
    ("400016020", "CHCYG",    False, 53739.5736, 28461.5,  60420409),
    ("702042060", "NGC5548",  True,  54303.4447, 24818.1,  65447920),
    ("401043010", "TCRB",     True,  53984.9475, 45431.4,  98703562),
    ("401036020", "BETALYR",  False, 53867.1260, 19164.2,  46830771),
    ("400006010", "SSCYG",    False, 53676.0504, 32047.2,  65006852),
    ("403033010", "WR140",    True,  54565.2314, 18605.5,  49925689),
    ("402032010", "EVLAC",    True,  54432.9692, 65011.3, 177320365),
    ("703023020", "NGC4051",  True,  54793.7000, 62760.4, 182340521),
]

# 20 XRISM Resolve p0px1000 FILTER=OPEN observations (10 prior bridges + 4 intra-D104 + 6 new)
XRISM_OBS: list[tuple[str, str, bool, float, float, int]] = [
    ("300000010", "GTMUS",       False, 60535.0859, 198614.42,  6210204),
    ("000162000", "CIRCINUSGAL", True,  60348.5025, 308697.60,  8398302),
    ("300067010", "ETACAR",      True,  60470.0535, 295982.68, 24964813),
    ("201094010", "NGC4945",     False, 60849.1141, 291188.29,  3731261),
    ("300019010", "CENA",        False, 60526.8356, 225138.86, 31758995),
    ("201044010", "IC4329A",     False, 60894.9825, 146288.44, 12870069),
    ("000127000", "PKS2155",     True,  60285.0578, 101167.00,  3505104),
    ("201058010", "EXHYA",       False, 60868.8102,  83009.36,  7456039),
    ("201116010", "NGC1068",     True,  60714.1109, 114990.14,  1483010),
    ("000145000", "3C273",       True,  60315.0367, 101827.97,  6193632),
    ("201081010", "NGC5548",     True,  60858.7997, 301394.14, 12718351),
    ("300008010", "TCRB",        True,  60492.4307,  93113.88,  2321742),
    ("202063010", "SIGMAGEM",    True,  60986.0100, 109075.61,  3085721),
    ("300042010", "SSCYG",       False, 60465.4827, 266716.16,  9581747),
    ("201107010", "WR140",       True,  60636.8758, 232151.53,  5804634),
    ("201066010", "NGC4051",     True,  60811.7455, 164355.52,  6595943),
    ("201035010", "AMHER",       False, 60605.0126, 184460.12, 17468742),
    ("201004010", "GAMMACAS",    False, 60721.2144,  59292.30, 11471046),
    ("201111010", "V2400OPH",    False, 60902.6217, 237744.29, 15628645),
    ("201103010", "PIAQR",       False, 60631.5752,  57604.00,  1013186),
]

# 20 NICER XTI observations (10 prior bridges + 10 brand-new non-compact stellar targets)
NICER_OBS: list[tuple[str, str, str, bool, float, float, int]] = [
    ("2100410125", "ADLEO",        "2019_12", True,  58838.0164, 23408.0, 11833433),
    ("3644020103", "BPTAU",        "2021_09", True,  59469.4594, 10908.0,   451904),
    ("7674010401", "EKDRA",        "2024_03", True,  60387.0071, 21550.0,  3647183),
    ("2110010202", "ETACAR",       "2019_03", True,  58548.0231, 11600.0,  6037117),
    ("1100420110", "EVLAC",        "2018_05", True,  58258.0525, 15321.0, 10619639),
    ("5671020102", "GJ729",        "2022_09", True,  59839.0429,  6561.0,  2002727),
    ("2300020128", "HD20630",      "2020_01", True,  58857.2206,  8959.0,  2453338),
    ("1112010115", "NGC4051",      "2018_01", True,  58133.0376, 14077.0,  9372501),
    ("7204280215", "TCRB",         "2024_09", True,  60556.9891, 16653.0,   519484),
    ("3660060201", "YZCET",        "2020_10", True,  59139.0465, 22880.0,  4430991),
    ("3660030104", "WOLF424",      "2020_04", False, 58947.1817, 20800.0,  6953242),
    ("3660040103", "APCOL",        "2020_12", False, 59189.9873, 24521.0,  2318708),
    ("3660020103", "DGCVN",        "2020_04", False, 58945.0522, 23311.0,  2033032),
    ("7555020101", "CRDRA",        "2024_03", False, 60386.3655, 14729.0,  4762869),
    ("7555010104", "GJ1243",       "2024_11", False, 60628.0548,  8465.0,  6213688),
    ("3644030109", "GMAUR",        "2021_10", False, 59509.3801, 16407.0,   516381),
    ("3644040301", "RULUP",        "2021_08", False, 59438.4996,  9750.0,   389246),
    ("5707010201", "TIC167344043", "2023_04", False, 60054.0134, 12585.0,  1773846),
    ("5707020401", "TIC364588501", "2023_04", False, 60060.0141,  9522.0,  2338311),
    ("8585010401", "WR133",        "2025_05", False, 60821.1084,  4919.0,   332621),
]

# 16 brand-new < 10 pc CARMENES VIS spectra (R=94,600)
CARMENES_OBS: list[tuple[str, float, float, int, str]] = [
    ("J12189+111", 57814.10255, 1801.5, 5057280, "car-20170302T02h27m40s-sci-gtoc-vis_A.fits"),
    ("J18482+076", 57881.12414, 1800.8, 5051520, "car-20170508T02h58m46s-sci-gtoc-vis_A.fits"),
    ("J18189+661", 57814.20491, 1801.4, 5057280, "car-20170302T04h55m04s-sci-gtoc-vis_A.fits"),
    ("J02442+255", 58092.05809,  854.6, 5074560, "car-20171205T01h23m39s-sci-gtoc-vis_A.fits"),
    ("J18022+642", 58382.79447, 1801.1, 5100480, "car-20180921T19h04m02s-sci-gtoc-vis_A.fits"),
    ("J20305+654", 57543.15225,  800.0, 5051520, "car-20160604T03h39m14s-sci-gtoc-vis_A.fits"),
    ("J18224+620", 58664.93075, 1801.5, 5097600, "car-20190630T22h20m17s-sci-gtoc-vis_A.fits"),
    ("J13005+056", 58283.85781, 1801.5, 5097600, "car-20180614T20h35m15s-sci-gtoc-vis_A.fits"),
    ("J15305+094", 57822.17037, 1801.9, 5057280, "car-20170310T04h05m20s-sci-gtoc-vis_A.fits"),
    ("J11511+352", 58554.22420,  726.9, 5068800, "car-20190312T05h22m51s-sci-gtoc-vis_A.fits"),
    ("J22012+283", 57586.09845, 1400.0, 5048640, "car-20160717T02h21m46s-sci-gtoc-vis_A.fits"),
    ("J13582+125", 57911.94839, 1801.4, 5057280, "car-20170607T22h45m41s-sci-gtoc-vis_A.fits"),
    ("J06103+821", 58727.14222,  857.9, 5074560, "car-20190901T03h24m48s-sci-gtoc-vis_A.fits"),
    ("J20405+154", 58683.00142, 1801.2, 5097600, "car-20190719T00h02m03s-sci-gtoc-vis_A.fits"),
    ("J01048-181", 57692.95446, 1801.8, 5051520, "car-20161031T22h54m25s-sci-gtoc-vis_A.fits"),
    ("J04376+528", 57409.93993,  900.1, 5051520, "car-20160122T22h33m30s-sci-gtoc-vis_A.fits"),
]

# 6 brand-new ESO Orbits #169-#174 (5 distinct-night spectra each = 30 spectra)
ESO_ORBIT_CAMPAIGNS: list[dict[str, Any]] = [
    {
        "campaign_order": 169, "star": "HD210277", "instrument": "ESO_ESPRESSO", "grating": "ESPRESSO_377_790NM", "r": 140000.0,
        "orb_per_days": 442.19, "orb_ecc": 0.480, "orb_omega_deg": -55.0, "orb_t0_bjd": 2457177.69, "kp_kms": 0.0389,
        "exposures": [
            ("ADP.2023-11-03T15:26:37.072", 60239.047594, 696.0, 514.1, 17818560),
            ("ADP.2024-08-06T10:07:12.768", 60519.302629, 696.0, 554.7, 17818560),
            ("ADP.2024-09-04T13:52:06.402", 60526.109718, 696.0, 414.9, 17818560),
            ("ADP.2024-11-05T09:55:19.281", 60602.057591, 696.0, 572.2, 17818560),
            ("ADP.2025-06-30T14:50:22.138", 60852.413750, 696.0, 299.3, 17821440),
        ],
    },
    {
        "campaign_order": 170, "star": "L168_9", "instrument": "ESO_ESPRESSO", "grating": "ESPRESSO_377_790NM", "r": 140000.0,
        "orb_per_days": 1.40152604, "orb_ecc": 0.000, "orb_omega_deg": 90.0, "orb_t0_bjd": 2459082.85679, "kp_kms": 0.0032,
        "exposures": [
            ("ADP.2021-04-13T12:52:06.137", 58416.028183, 900.0, 63.6, 55108800),
            ("ADP.2021-04-20T09:09:16.417", 58624.360694, 900.0, 38.7, 55108800),
            ("ADP.2021-04-27T14:21:26.879", 58725.284506, 900.0, 77.0, 55108800),
            ("ADP.2021-04-27T16:42:50.553", 58777.184378, 900.0, 83.4, 55108800),
            ("ADP.2021-04-27T17:36:23.679", 58858.058912, 900.0, 54.5, 55108800),
        ],
    },
    {
        "campaign_order": 171, "star": "TOI836", "instrument": "ESO_HARPS", "grating": "HARPS_378_691NM", "r": 115000.0,
        "orb_per_days": 8.59545, "orb_ecc": 0.078, "orb_omega_deg": -28.0, "orb_t0_bjd": 2458599.7623, "kp_kms": 0.00386,
        "exposures": [
            ("ADP.2019-07-07T01:09:21.133", 58670.147363, 1500.0, 48.5, 5264640),
            ("ADP.2021-01-27T01:03:42.760", 59240.359201, 1500.0, 64.8, 5264640),
            ("ADP.2021-02-21T01:16:39.415", 59265.358702, 1500.0, 48.6, 5264640),
            ("ADP.2023-05-15T01:01:10.478", 60078.036474,  900.0, 47.5, 5261760),
            ("ADP.2023-07-06T01:01:51.050", 60130.092647,  900.0, 41.2, 5261760),
        ],
    },
    {
        "campaign_order": 172, "star": "HD95338", "instrument": "ESO_HARPS", "grating": "HARPS_378_691NM", "r": 115000.0,
        "orb_per_days": 55.082694, "orb_ecc": 0.197, "orb_omega_deg": 23.42, "orb_t0_bjd": 2458585.28087, "kp_kms": 0.00817,
        "exposures": [
            ("ADP.2018-05-25T01:05:15.076", 58262.014652, 900.0,  62.6, 5264640),
            ("ADP.2018-05-28T01:02:22.773", 58265.094372, 900.0,  83.7, 5264640),
            ("ADP.2019-04-11T03:42:03.277", 58576.188422, 900.0,  59.1, 5264640),
            ("ADP.2019-04-11T03:42:03.539", 58580.212284, 900.0, 103.3, 5264640),
            ("ADP.2019-04-11T03:42:02.533", 58583.200595, 900.0,  93.5, 5264640),
        ],
    },
    {
        "campaign_order": 173, "star": "HD86226", "instrument": "ESO_HARPS", "grating": "HARPS_378_691NM", "r": 115000.0,
        "orb_per_days": 3.98442, "orb_ecc": 0.075, "orb_omega_deg": 196.0, "orb_t0_bjd": 2458543.2539, "kp_kms": 0.00289,
        "exposures": [
            ("ADP.2021-11-20T01:06:26.541", 59537.351154, 900.0, 154.3, 5264640),
            ("ADP.2022-02-08T01:08:33.250", 59617.179929, 900.0, 114.7, 5264640),
            ("ADP.2022-11-03T01:04:15.917", 59885.356917, 900.0, 105.5, 5264640),
            ("ADP.2023-03-23T01:02:04.823", 60025.144995, 900.0, 136.1, 5261760),
            ("ADP.2023-06-10T01:02:03.041", 60104.025506, 900.0, 128.6, 5261760),
        ],
    },
    {
        "campaign_order": 174, "star": "TOI500", "instrument": "ESO_HARPS", "grating": "HARPS_378_691NM", "r": 115000.0,
        "orb_per_days": 26.233, "orb_ecc": 0.016, "orb_omega_deg": 189.6, "orb_t0_bjd": 2458587.22, "kp_kms": 0.00872,
        "exposures": [
            ("ADP.2019-05-24T01:50:46.356", 58564.105951, 1800.0, 57.3, 5264640),
            ("ADP.2019-04-11T03:42:02.499", 58582.974719, 1800.0, 60.0, 5264640),
            ("ADP.2019-05-06T01:11:17.328", 58607.985175, 1800.0, 45.8, 5264640),
            ("ADP.2019-05-18T01:11:11.963", 58620.002665, 1800.0, 36.0, 5264640),
            ("ADP.2019-12-14T01:15:27.655", 58830.125458, 1800.0, 69.0, 5264640),
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
        e_anom = e_anom - (e_anom - ecc * math.sin(e_anom) - m_anom) / max(1e-8, 1.0 - ecc * math.cos(e_anom))
    nu = 2.0 * math.atan2(math.sqrt(1.0 + ecc) * math.sin(0.5 * e_anom), math.sqrt(1.0 - ecc) * math.cos(0.5 * e_anom))
    w_rad = math.radians(omega_deg)
    rv_kms = k_kms * (math.cos(nu + w_rad) + ecc * math.cos(w_rad))
    abs_p = abs(signed_phi)
    win = "IN_WINDOW" if abs_p <= 0.12 or abs(0.5 - abs_p) <= 0.12 else "IN_QUADRATURE"
    return round(signed_phi, 5), round(rv_kms, 6), win


def _http_head(url: str) -> tuple[int, int]:
    import time
    last_exc: Exception | None = None
    for attempt in range(6):
        method = "HEAD" if attempt % 2 == 0 else "GET"
        headers = {"User-Agent": "SETI-V6.2-D104-Lock/1.0", "Connection": "close"}
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
            print(f"  [{method} retry {attempt+1}] {url}: {exc}", flush=True)
            time.sleep(1.5 * (attempt + 1))
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
        "total_bytes": str(f1_bytes),
        "extra_files": "[]",
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    if RAW_DIR.exists():
        raise RuntimeError(f"Chronology violation: {RAW_DIR} must NOT exist before Stage-1 seal!")

    ac_sha = _sha256_file(ARCHIVE_AC)
    b103_sha = _sha256_file(BUNDLE_103)
    if ac_sha != ARCHIVE_AC_SHA256 or b103_sha != BUNDLE_103_SHA256:
        raise RuntimeError(f"Archive AC or d103 bundle SHA mismatch ({ac_sha}, {b103_sha})")

    pe103 = json.loads((WS103 / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    d103_cohort = _read_csv(WS103 / "FROZEN_COHORT_D103.csv")
    u709_rows = _read_csv(WS103 / "results/UNIFIED_PANCHROMATIC_V6_1_SYNTHESIS_709STARS.csv")
    br1016_rows = _read_csv(WS103 / "results/PANCHROMATIC_BRIDGE_87STARS_V61.csv")
    comb_u501_rows = _read_csv(WS103 / "results/ALLSKY_COMB_V4_1_UNIFIED_D079_D103.csv")
    comb_c_rows = _read_csv(WS103 / "results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D103.csv")
    ell709_rows = _read_csv(WS103 / "results/MULTIEVENT_ELLIPSOID_709STARS.csv")
    s103 = json.loads((WS103 / "results/SUMMARY.json").read_text(encoding="utf-8"))

    u_map = {r["star"]: r for r in u709_rows}
    coord_by_star: dict[str, tuple[float, float]] = {
        r["star"]: (float(r["ra_deg"]), float(r["dec_deg"])) for r in ell709_rows
    }
    for t in pe103["excluded_targets_coordinate_registry"]:
        nm = str(t.get("canonical_target") or "").strip()
        if nm and nm not in coord_by_star:
            coord_by_star[nm] = (float(t["ra_deg"]), float(t["dec_deg"]))
    for r in d103_cohort:
        nm = r["canonical_target"]
        if nm not in coord_by_star:
            coord_by_star[nm] = (float(r["s_ra"]), float(r["s_dec"]))

    prior_coords: list[dict[str, Any]] = list(pe103["excluded_targets_coordinate_registry"])
    seen_d103_new = set()
    for r in d103_cohort:
        if str(r["is_prior_bridge"]).lower() not in ("true", "1", "yes"):
            nm = r["canonical_target"]
            if nm not in seen_d103_new:
                seen_d103_new.add(nm)
                prior_coords.append({"canonical_target": nm, "ra_deg": float(r["s_ra"]), "dec_deg": float(r["s_dec"])})

    prior_dp_ids = sorted(set(pe103["excluded_dp_ids"]) | {r["dp_id"] for r in d103_cohort})
    format_probes = sorted(set(pe103["format_check_excluded_dp_ids"]) | set(FORMAT_CHECK_EXTRA_D104))
    assert len(prior_coords) == 782, f"Expected 782 prior coords, got {len(prior_coords)}"
    assert len(prior_dp_ids) == 3472, f"Expected 3472 prior dp_ids, got {len(prior_dp_ids)}"
    assert len(format_probes) == 30, f"Expected 30 format probes, got {len(format_probes)}"

    # Build all 104 rows
    rows: list[dict[str, Any]] = []

    for ob, canon, is_b, mjd, exp_s, sz in SUZAKU_OBS:
        if is_b:
            assert canon in u_map, f"Missing Suzaku bridge {canon} in u_map"
        meta = _star_meta(canon, is_b, u_map, coord_by_star)
        url = f"https://heasarc.gsfc.nasa.gov/FTP/suzaku/data/obs/{ob[0]}/{ob}/hxd/event_cl/ae{ob}hxd_0_gsono_cl.evt.gz"
        rows.append(_make_row(
            inst="SUZAKU_HXD_GSO", canon=canon, meta=meta, is_prior_bridge=is_b, panchromatic_bridge=True,
            science_track="SUZAKU_SOFT_GAMMA_V62", epoch_rank=1, dp_id=f"SUZAKU_{ob}", grating="HXD_GSO_50_600KEV",
            resolving_power=8.0, mjd_obs=mjd, t_exptime=exp_s, phase_window="NONE", signed_phase=0.0,
            planet_orbital_rv_kms=0.0, f1_rel=f"SUZAKU_HXD_GSO/{canon}/ae{ob}hxd_0_gsono_cl.evt.gz",
            f1_url=url, f1_bytes=sz,
        ))

    suz_new = {canon for _, canon, is_b, *_ in SUZAKU_OBS if not is_b}
    for ob, canon, is_b, mjd, exp_s, sz in XRISM_OBS:
        if is_b:
            assert canon in u_map, f"Missing XRISM bridge {canon} in u_map"
        meta = _star_meta(canon, is_b, u_map, coord_by_star)
        url = f"https://heasarc.gsfc.nasa.gov/FTP/xrism/data/obs/{ob[0]}/{ob}/resolve/event_cl/xa{ob}rsl_p0px1000_cl.evt.gz"
        rows.append(_make_row(
            inst="XRISM_RESOLVE", canon=canon, meta=meta, is_prior_bridge=is_b,
            panchromatic_bridge=bool(is_b or canon in suz_new),
            science_track="XRISM_MICROCAL_V62", epoch_rank=1, dp_id=f"XRISM_{ob}", grating="RESOLVE_OPEN_1P7_12KEV",
            resolving_power=1350.0, mjd_obs=mjd, t_exptime=exp_s, phase_window="NONE", signed_phase=0.0,
            planet_orbital_rv_kms=0.0, f1_rel=f"XRISM_RESOLVE/{canon}/xa{ob}rsl_p0px1000_cl.evt.gz",
            f1_url=url, f1_bytes=sz,
        ))

    for ob, canon, ym, is_b, mjd, exp_s, sz in NICER_OBS:
        if is_b:
            assert canon in u_map, f"Missing NICER bridge {canon} in u_map"
        meta = _star_meta(canon, is_b, u_map, coord_by_star)
        url = f"https://heasarc.gsfc.nasa.gov/FTP/nicer/data/obs/{ym}/{ob}/xti/event_cl/ni{ob}_0mpu7_cl.evt.gz"
        rows.append(_make_row(
            inst="NICER_XTI", canon=canon, meta=meta, is_prior_bridge=is_b, panchromatic_bridge=is_b,
            science_track="NICER_XTI_V62", epoch_rank=1, dp_id=f"NICER_{ob}", grating="XTI_0P35_10KEV",
            resolving_power=40.0, mjd_obs=mjd, t_exptime=exp_s, phase_window="NONE", signed_phase=0.0,
            planet_orbital_rv_kms=0.0, f1_rel=f"NICER_XTI/{canon}/ni{ob}_0mpu7_cl.evt.gz",
            f1_url=url, f1_bytes=sz,
        ))

    for canon, mjd, exp_s, sz, fn in CARMENES_OBS:
        meta = _star_meta(canon, False, u_map, coord_by_star)
        url = f"https://dc.g-vo.org/carmenes/q/sdl/static/{canon}/{fn}"
        rows.append(_make_row(
            inst="CARMENES_VIS", canon=canon, meta=meta, is_prior_bridge=False, panchromatic_bridge=False,
            science_track="SOLAR_NEIGHBORHOOD_10PC_V62", epoch_rank=1, dp_id=f"CARM_{fn}", grating="CARMENES_VIS_520_960NM",
            resolving_power=94600.0, mjd_obs=mjd, t_exptime=exp_s, phase_window="NONE", signed_phase=0.0,
            planet_orbital_rv_kms=0.0, f1_rel=f"CARMENES_VIS/{canon}/{fn}",
            f1_url=url, f1_bytes=sz,
        ))

    orbital_campaigns: dict[str, Any] = {}
    for camp in ESO_ORBIT_CAMPAIGNS:
        canon = camp["star"]
        meta = _star_meta(canon, False, u_map, coord_by_star)
        inst = camp["instrument"]
        camp_exps = []
        mjs = []
        rvs = []
        for idx, (dp_id, mjd, exp_s, snr, sz) in enumerate(camp["exposures"], 1):
            sphi, rv_orb, win = _kepler_rv(mjd, camp["orb_per_days"], camp["orb_ecc"], camp["orb_omega_deg"], camp["orb_t0_bjd"], camp["kp_kms"])
            url = f"https://dataportal.eso.org/dataportal_new/file/{dp_id}"
            rows.append(_make_row(
                inst=inst, canon=canon, meta=meta, is_prior_bridge=False, panchromatic_bridge=False,
                science_track=f"ORBITAL_CAMPAIGN_V62_{camp['campaign_order']}", epoch_rank=idx, dp_id=dp_id,
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
            "campaign_order": camp["campaign_order"],
            "phase_id": "D104",
            "canonical_target": canon,
            "common_name": meta["common_name"],
            "instrument": inst,
            "grating": camp["grating"],
            "orb_per_days": camp["orb_per_days"],
            "orb_ecc": camp["orb_ecc"],
            "orb_omega_deg": camp["orb_omega_deg"],
            "orb_t0_bjd": camp["orb_t0_bjd"],
            "kp_kms": camp["kp_kms"],
            "exposures": camp_exps,
            "n_epochs": len(camp_exps),
            "baseline_days": round(max(mjs) - min(mjs), 4),
            "orbital_dv_span_kms": round(max(rvs) - min(rvs), 6),
        }

    # Strict Stage-1 exclusions & uniqueness checks
    dp_set = {r["dp_id"] for r in rows}
    assert len(rows) == 104 and len(dp_set) == 104, f"Expected 104 unique obs, got {len(rows)}/{len(dp_set)}"
    overlap_dp = dp_set & (set(prior_dp_ids) | set(format_probes))
    assert not overlap_dp, f"dp_id overlap detected: {overlap_dp}"

    brand_new_stars = sorted({r["canonical_target"] for r in rows if r["is_prior_bridge"] == "False"})
    bridge_stars = sorted({r["canonical_target"] for r in rows if r["is_prior_bridge"] == "True"})
    assert len(brand_new_stars) == 46, f"Expected 46 brand-new stars, got {len(brand_new_stars)}"
    assert len(bridge_stars) == 18, f"Expected 18 unique prior bridges, got {len(bridge_stars)}"

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
            assert sp >= 120.0, f"Intra-D104 overlap {s1}/{s2}: {sp:.2f}'' < 120''"

    # Live HTTP 200 verification on all 104 URLs BEFORE sealing
    print(f"Verifying HTTP 200 on all {len(rows)} D104 URLs...", flush=True)
    with ThreadPoolExecutor(max_workers=4) as ex:
        head_res = []
        for idx, res in enumerate(ex.map(lambda r: (r["dp_id"], r["f1_url"], *_http_head(r["f1_url"]), int(r["f1_bytes"])), rows), 1):
            head_res.append(res)
            if idx % 20 == 0 or idx == len(rows):
                print(f"  verified {idx}/{len(rows)} URLs...", flush=True)
    for dp, u, st, b, exp_b in head_res:
        assert st == 200, f"HEAD failed {dp} ({u}): HTTP {st}"
        if exp_b > 0 and b > 0:
            assert b == exp_b, f"HEAD bytes mismatch {dp}: got {b}, expected {exp_b}"
    print("All 104/104 URLs verified HTTP 200 with exact byte lengths.")

    with open(WS / "FROZEN_COHORT_D104.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COHORT_COLS)
        w.writeheader()
        w.writerows(rows)

    tot_bytes = sum(int(r["f1_bytes"]) for r in rows)
    n_new_10pc = sum(1 for s in brand_new_stars if NEW_META[s]["d"] < 10.0)
    assert n_new_10pc == 18, f"Expected +18 new <10 pc stars (188 -> 206), got {n_new_10pc}"

    now_utc = datetime.now(timezone.utc)
    locked_utc = now_utc.isoformat()
    locked_epoch = now_utc.timestamp()

    pe_out = {
        "schema": "D104_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D104",
        "verified_utc": locked_utc,
        "prior_phases_covered": "C001-C037 + D001-D103",
        "n_prior_excluded_coords": len(prior_coords),
        "n_prior_excluded_dp_ids": len(prior_dp_ids),
        "n_format_check_excluded_dp_ids": len(format_probes),
        "d104_total_stars": len(brand_new_stars) + len(bridge_stars),
        "d104_brand_new_unique_stars": len(brand_new_stars),
        "d104_prior_bridge_stars": len(bridge_stars),
        "d104_control_stars": sum(1 for s in brand_new_stars if NEW_META[s]["role"] == "CONTROL") + sum(1 for s in bridge_stars if u_map[s]["role"] == "CONTROL"),
        "d104_brand_new_within_10pc": n_new_10pc,
        "d104_total_observations": len(rows),
        "d104_total_physical_files": len(rows),
        "d104_projected_download_bytes": tot_bytes,
        "d104_projected_download_mib": round(tot_bytes / (1024.0 * 1024.0), 3),
        "d104_dp_id_overlap_count": 0,
        "min_brand_new_sky_separation_arcsec": round(min_prior_sep, 2),
        "min_intra_d104_separation_arcsec": round(min_intra_sep, 2),
        "star_separation_verification": sep_verif,
        "format_check_excluded_dp_ids": format_probes,
        "excluded_dp_ids": prior_dp_ids,
        "excluded_targets_coordinate_registry": prior_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pe_out, indent=2) + "\n", encoding="utf-8")

    uni103 = s103["unified_709star_panchromatic_v6_1_synthesis"]
    snap_out = {
        "schema": "D104_PRIOR_V6_1_PHASES_SNAPSHOT",
        "prior_phases": "C001-C037 + D001-D103",
        "source_archive_ac_name": ARCHIVE_AC.name,
        "source_archive_ac_sha256": ARCHIVE_AC_SHA256,
        "source_archive_ac_bundle_member": "work_v6_1_20261123_d103_hard_xray_nustar_xmm_rgs_alma_b9b10_700star/bounded_inputs/d103_bounded_bundle.json.gz",
        "source_archive_ac_bundle_sha256": BUNDLE_103_SHA256,
        "prior_unique_stars_count": len(u709_rows),
        "prior_science_stars_count": int(uni103["science_stars_total"]),
        "prior_control_stars_count": int(uni103["control_stars_total"]),
        "prior_planet_host_stars_count": int(uni103["planet_host_stars_total"]),
        "prior_confirmed_exoplanets_count": int(uni103["confirmed_exoplanets_total"]),
        "prior_within_10pc_count": int(uni103["within_10pc_unique_stars"]),
        "prior_total_exposures_count": int(uni103["total_exposures_d079_d103"]),
        "prior_cumulative_integration_hours": float(uni103["total_integration_hours_d079_d103"]),
        "prior_calibration_trials_count": int(uni103["total_calibration_trials_d079_d103"]),
        "prior_v2_false_alarms_eliminated_total": int(uni103["v2_false_alarms_eliminated_total"]),
        "prior_cumulative_orbital_campaigns_count": int(uni103["cumulative_orbital_campaigns"]),
        "prior_panchromatic_bridge_stars_count": int(uni103["panchromatic_bridge_stars_total"]),
        "prior_revisited_control_multi_phase_stars": int(uni103["revisited_control_multi_phase_stars"]),
        "prior_multi_phase_targets_total": int(uni103["multi_phase_targets_total"]),
        "prior_panchromatic_bridge_cells_count": int(uni103["panchromatic_bridge_cells_total"]),
        "prior_cumulative_comb_stacks": int(uni103["cumulative_comb_stacks"]),
        "prior_coherent_eccentric_keplerian_campaigns": int(uni103["coherent_eccentric_keplerian_campaigns"]),
        "d103_summary_headline": uni103,
        "prior_unified_709_rows": u709_rows,
        "prior_bridge_87_rows": br1016_rows,
        "prior_allsky_comb_unified_rows": comb_u501_rows,
        "prior_allsky_comb_candidate_rows": comb_c_rows,
        "prior_ellipsoid_709_rows": ell709_rows,
    }
    (WS / "PRIOR_V6_1_PHASES_SNAPSHOT.json").write_text(json.dumps(snap_out, indent=2) + "\n", encoding="utf-8")

    orb_out = {
        "schema": "D104_ORBITAL_CAMPAIGNS_AND_KINEMATICS",
        "phase_id": "D104",
        "campaign_range": [169, 174],
        "campaigns": orbital_campaigns,
    }
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_out, indent=2) + "\n", encoding="utf-8")

    stage1_names = [
        "v6_2_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D104.csv",
        "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "PRIOR_V6_1_PHASES_SNAPSHOT.json",
    ]
    stage1_hashes = {fn: _sha256_file(WS / fn) for fn in stage1_names}

    ml = {
        "schema": "D104_PROSPECTIVE_METHOD_LOCK",
        "phase_id": "D104",
        "detector_version": "V6.2",
        "detector": det.DETECTOR_NAME,
        "locked_utc": locked_utc,
        "projected_unified_stars": 709 + len(brand_new_stars),
        "projected_within_10pc_stars": 188 + n_new_10pc,
        "d104_brand_new_stars": len(brand_new_stars),
        "d104_prior_bridges": len(bridge_stars),
        "d104_total_observations": len(rows),
        "d104_total_physical_files": len(rows),
        "d104_projected_bytes": tot_bytes,
        "d104_projected_mib": round(tot_bytes / (1024.0 * 1024.0), 3),
        "stage_1_files": stage1_hashes,
    }
    (WS / "METHOD_LOCK.json").write_text(json.dumps(ml, indent=2) + "\n", encoding="utf-8")
    ml_sha = _sha256_file(WS / "METHOD_LOCK.json")

    lr = {
        "schema": "D104_LOCK_RECEIPT",
        "phase_id": "D104",
        "status": "STAGE-1 SEALED",
        "locked_utc": locked_utc,
        "locked_unix_epoch": round(locked_epoch, 4),
        "method_lock_sha256": ml_sha,
        "inputs_dir_exists_at_seal": RAW_DIR.exists(),
        "locked_files": stage1_hashes,
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lr, indent=2) + "\n", encoding="utf-8")
    print(f"STAGE-1 SEALED: obs={len(rows)}, brand_new={len(brand_new_stars)} (+{n_new_10pc} <10pc -> {188+n_new_10pc}), unified={709+len(brand_new_stars)}, min_prior_sep={min_prior_sep:.1f}'', min_intra_sep={min_intra_sep:.1f}'', raw_dir_exists={RAW_DIR.exists()}, proj_mib={ml['d104_projected_mib']}")


if __name__ == "__main__":
    main()
