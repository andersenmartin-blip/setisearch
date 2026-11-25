#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D107 (`V6.5`) Prospective Cohort Builder & Stage-1 Lock Sealer.
Locks 134 archival observations (59 unique physical files) across 99 targets
(52 brand-new + 47 prior bridges):
  1. 54 IceCube 10-Yr All-Sky Point-Source Neutrino (IC40-IC86_VII, 0.1 TeV-10 PeV) targets:
     - 20 prior bridges (`16CYGB` Quad-Messenger exoplanet bridge + 17 single-phase northern SCIENCE + NGC 1068 + Mrk 421)
     - 18 brand-new <10 pc Gaia DR3 stars (`dec >= -5 deg`, expanding <10 pc census 244 -> 262)
     - 15 brand-new northern NEA exoplanet hosts (`dec >= 0 deg`)
     - 1 brand-new astrophysical neutrino blazar control (`TXS 0506+056`)
  2. 30 NASA Swift-BAT 157-Month Hard X-Ray (14-195 keV) targets (`bs157mon`):
     - 18 prior bridges (7 SCIENCE [`OMC1, GTMUS, CHCYG, V648CAR, SSCYG, TCRB, GAMMACAS`] + 11 CONTROL)
     - 12 brand-new Galactic symbiotics/novae/CVs (2 SCIENCE [`RTCRU, GKPER`] + 10 CONTROL)
  3. 20 NASA Swift-XRT (0.3-10 keV PC/WT CCD + CALDB RMF/ARF) targets:
     - 15 prior bridges (11 SCIENCE [`PROXIMACEN..IIPEG`] + 4 CONTROL [`NGC1068, MRK421, 3C273, CENA`])
     - 5 brand-new dual-instrument D107 targets (`RTCRU, GKPER, V1223SGR, V709CAS, TXS0506`)
  4. 30 brand-new ESO ESPRESSO/HARPS/NIRPS distinct-night spectra across Orbits #187-#192 (`N=5` each):
     `L 363-38`, `GJ 27.1`, `GJ 328`, `TOI-771`, `HIP 12961`, `GJ 3634`.

Zero overlap against 925 prior sky coordinates (min_prior_sep >= 1000''), zero overlap
against 3,801 prior dp_ids + 46 format-check probes, live HTTP 200 verification on every
upstream URL, and atomic Stage-1 sealing BEFORE `$RAW107` exists.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent
ROOT = WS.parent.parent
WS106 = ROOT / "analysis_workspace/work_v6_4_20261124_d106_vhe_tev_gamma_hess_magic_veritas_hawc_60octave"
RAW_DIR = ROOT / "inputs_d107_v6_5"
ARCHIVE_AF = ROOT / "archives/SETI_D106_V6_4_VHE_TEV_GAMMA_HESS_MAGIC_VERITAS_HAWC_60OCTAVE_RESULTS_2026-11-24.zip"
ARCHIVE_AF_SHA256 = "5a5a04924333472d1775f5d6fd843e4712e1d39da824f2a8c6555741a09e0553"
BUNDLE_106 = WS106 / "bounded_inputs/d106_bounded_bundle.json.gz"
BUNDLE_106_SHA256 = "053e8cdaad3313043d4ce62dfceba1693d0bfee00dd83114b3c1c30986eb2427"

if str(WS) not in sys.path:
    sys.path.insert(0, str(WS))
import v6_5_detector as det  # noqa: E402

ICECUBE_ZIP_URL = "https://icecube.wisc.edu/data-releases/20210126_PS-IC40-IC86_VII.zip"
ICECUBE_ZIP_REL = "ICECUBE_10YR/20210126_PS-IC40-IC86_VII.zip"
ICECUBE_ZIP_BYTES = 39848048

BAT_BASE = "https://swift.gsfc.nasa.gov/bat_survey/bs157mon/data/"
BAT_FILES: list[tuple[str, str, int]] = [
    ("SWIFT_BAT/BAT_157m_catalog_20250525.txt", BAT_BASE + "BAT_157m_catalog_20250525.txt", 470669),
    ("SWIFT_BAT/BAT_157m_spectra_2025.tar.gz", BAT_BASE + "BAT_157m_spectra_2025.tar.gz", 453973),
    ("SWIFT_BAT/BAT_157m_swiftbat_survey_full_157m.rsp", BAT_BASE + "BAT_157m_swiftbat_survey_full_157m.rsp", 31680),
    ("SWIFT_BAT/BAT_157m_eight_band_monthly_light_curve_2025.tar.gz", BAT_BASE + "BAT_157m_eight_band_monthly_light_curve_2025.tar.gz", 41455214),
]

XRT_CALDB: dict[str, tuple[str, str, int]] = {
    "PC_ARF": ("SWIFT_XRT/caldb/swxpc0to12s6_20010101v013.arf", "https://heasarc.gsfc.nasa.gov/FTP/caldb/data/swift/xrt/cpf/arf/swxpc0to12s6_20010101v013.arf", 37440),
    "PC_RMF": ("SWIFT_XRT/caldb/swxpc0to12s6_20130101v014.rmf", "https://heasarc.gsfc.nasa.gov/FTP/caldb/data/swift/xrt/cpf/rmf/swxpc0to12s6_20130101v014.rmf", 9892800),
    "WT_ARF": ("SWIFT_XRT/caldb/swxwt0to2s6_20010101v014.arf", "https://heasarc.gsfc.nasa.gov/FTP/caldb/data/swift/xrt/cpf/arf/swxwt0to2s6_20010101v014.arf", 37440),
    "WT_RMF": ("SWIFT_XRT/caldb/swxwt0to2s6_20131212v015.rmf", "https://heasarc.gsfc.nasa.gov/FTP/caldb/data/swift/xrt/cpf/rmf/swxwt0to2s6_20131212v015.rmf", 9892800),
}

# Verified metadata for all 52 brand-new D107 stars (18 Gaia <10 pc + 15 NEA north + 12 BAT CVs/symbiotics + 1 TXS0506 + 6 ESO orbits)
NEW_META: dict[str, dict[str, Any]] = {
    # --- 18 Brand-new <10 pc Gaia DR3 Northern/Equatorial Stars (dec >= -5 deg, sep >= 1700'' from prior) ---
    "GAIA_990720": {"common_name": "Gaia DR3 1695191332232990720 (Ursa Minor, 5.16 pc)", "role": "SCIENCE", "subrole": "ICECUBE_NORTHERN_10PC", "sid": "1695191332232990720", "ra": 226.702636, "dec": 70.461619, "pmra": -1194.179, "pmdec": 1042.194, "d": 5.15620, "g": 20.1995, "bp": 21.7720, "rp": 18.3319, "j": None, "h": None, "k": None, "teff": 2500.0, "mass": 0.08, "rv": 0.0, "n_pl": 0, "tr": False, "mh": 0.0},
    "GAIA_665088": {"common_name": "Gaia DR3 1267906854386665088 (Bootes, 6.42 pc)",     "role": "SCIENCE", "subrole": "ICECUBE_NORTHERN_10PC", "sid": "1267906854386665088", "ra": 225.832142, "dec": 25.424644, "pmra":    87.414, "pmdec":  557.780, "d": 6.41948, "g": 20.2746, "bp": 21.8056, "rp": 18.5233, "j": None, "h": None, "k": None, "teff": 2450.0, "mass": 0.08, "rv": 0.0, "n_pl": 0, "tr": False, "mh": 0.0},
    "GAIA_940608": {"common_name": "Gaia DR3 2019802555283940608 (Vulpecula, 6.83 pc)",  "role": "SCIENCE", "subrole": "ICECUBE_NORTHERN_10PC", "sid": "2019802555283940608", "ra": 292.171753, "dec": 23.935005, "pmra":  -246.999, "pmdec":  240.430, "d": 6.83029, "g": 20.6377, "bp": 21.9866, "rp": 18.5078, "j": None, "h": None, "k": None, "teff": 2400.0, "mass": 0.08, "rv": 0.0, "n_pl": 0, "tr": False, "mh": 0.0},
    "GAIA_539840": {"common_name": "Gaia DR3 3426333598021539840 (Gemini, 7.24 pc)",     "role": "SCIENCE", "subrole": "ICECUBE_NORTHERN_10PC", "sid": "3426333598021539840", "ra":  91.910273, "dec": 24.497694, "pmra":  -472.871, "pmdec": -318.464, "d": 7.24314, "g": 19.5203, "bp": 22.1018, "rp": 17.8544, "j": None, "h": None, "k": None, "teff": 2500.0, "mass": 0.08, "rv": 0.0, "n_pl": 0, "tr": False, "mh": 0.0},
    "GAIA_160000": {"common_name": "Gaia DR3 4468009917744160000 (Ophiuchus, 7.81 pc)",  "role": "SCIENCE", "subrole": "ICECUBE_NORTHERN_10PC", "sid": "4468009917744160000", "ra": 270.111145, "dec":  1.580764, "pmra":   183.734, "pmdec": -384.108, "d": 7.80917, "g": 19.5494, "bp": 21.6124, "rp": 17.8759, "j": None, "h": None, "k": None, "teff": 2500.0, "mass": 0.08, "rv": 0.0, "n_pl": 0, "tr": False, "mh": 0.0},
    "GAIA_790464": {"common_name": "Gaia DR3 4479498508613790464 (Aquila, 8.20 pc)",     "role": "SCIENCE", "subrole": "ICECUBE_NORTHERN_10PC", "sid": "4479498508613790464", "ra": 279.881739, "dec":  9.028625, "pmra":   -19.860, "pmdec":  -21.528, "d": 8.19815, "g": 19.0899, "bp": 19.5722, "rp": 17.1556, "j": None, "h": None, "k": None, "teff": 2600.0, "mass": 0.08, "rv": 0.0, "n_pl": 0, "tr": False, "mh": 0.0},
    "GAIA_536000": {"common_name": "Gaia DR3 2202703050401536000 (Cepheus, 8.46 pc)",    "role": "SCIENCE", "subrole": "ICECUBE_NORTHERN_10PC", "sid": "2202703050401536000", "ra": 327.916360, "dec": 59.292930, "pmra":   -86.742, "pmdec":  -19.237, "d": 8.46345, "g": 14.3731, "bp": 14.8135, "rp": 13.7629, "j": None, "h": None, "k": None, "teff": 2900.0, "mass": 0.12, "rv": 0.0, "n_pl": 0, "tr": False, "mh": 0.0},
    "GAIA_871360": {"common_name": "Gaia DR3 2794735086363871360 (Andromeda, 8.74 pc)",  "role": "SCIENCE", "subrole": "ICECUBE_NORTHERN_10PC", "sid": "2794735086363871360", "ra":   9.071355, "dec": 18.353410, "pmra":   901.582, "pmdec":  124.354, "d": 8.73565, "g": 17.4956, "bp": 20.4429, "rp": 15.9091, "j": None, "h": None, "k": None, "teff": 2700.0, "mass": 0.09, "rv": 0.0, "n_pl": 0, "tr": False, "mh": 0.0},
    "GAIA_374336": {"common_name": "Gaia DR3 981548637301374336 (Lynx, 9.02 pc)",        "role": "SCIENCE", "subrole": "ICECUBE_NORTHERN_10PC", "sid": "981548637301374336",  "ra": 105.987163, "dec": 52.697727, "pmra":   675.775, "pmdec": -921.880, "d": 9.02313, "g": 11.6991, "bp": 13.5980, "rp": 10.3877, "j": None, "h": None, "k": None, "teff": 2900.0, "mass": 0.16, "rv": 25.2043, "n_pl": 0, "tr": False, "mh": 0.0},
    "GAIA_596096": {"common_name": "Gaia DR3 1057318835428596096 (Ursa Major, 9.07 pc)", "role": "SCIENCE", "subrole": "ICECUBE_NORTHERN_10PC", "sid": "1057318835428596096", "ra": 169.988104, "dec": 65.847298, "pmra": -2946.718, "pmdec":  181.947, "d": 9.07190, "g":  8.5276, "bp":  9.4977, "rp":  7.5461, "j": None, "h": None, "k": None, "teff": 3550.7, "mass": 0.42, "rv": 60.2854, "n_pl": 0, "tr": False, "mh": -0.817},
    "GAIA_639744": {"common_name": "Gaia DR3 3085716990368639744 (Monoceros, 9.27 pc)",  "role": "SCIENCE", "subrole": "ICECUBE_NORTHERN_10PC", "sid": "3085716990368639744", "ra": 117.978968, "dec": -0.006769, "pmra":   263.543, "pmdec": -756.863, "d": 9.27224, "g": 11.6535, "bp": 13.4792, "rp": 10.3634, "j": None, "h": None, "k": None, "teff": 3074.9, "mass": 0.16, "rv": 39.1976, "n_pl": 0, "tr": False, "mh": -0.053},
    "GAIA_576576": {"common_name": "Gaia DR3 423027104407576576 (Cassiopeia, 9.31 pc)",  "role": "SCIENCE", "subrole": "ICECUBE_NORTHERN_10PC", "sid": "423027104407576576",  "ra":   2.874735, "dec": 59.139227, "pmra":  -905.722, "pmdec":-1166.826, "d": 9.31209, "g": 13.4680, "bp": 15.9015, "rp": 12.0799, "j": None, "h": None, "k": None, "teff": 2900.0, "mass": 0.11, "rv": 0.0, "n_pl": 0, "tr": False, "mh": 0.0},
    "GAIA_994560": {"common_name": "Gaia DR3 1349047857580994560 (Hercules, 9.53 pc)",   "role": "SCIENCE", "subrole": "ICECUBE_NORTHERN_10PC", "sid": "1349047857580994560", "ra": 265.983242, "dec": 43.375930, "pmra":    10.337, "pmdec": -603.198, "d": 9.53155, "g":  9.4501, "bp": 10.7263, "rp":  8.3285, "j": None, "h": None, "k": None, "teff": 3275.0, "mass": 0.31, "rv": -14.5311, "n_pl": 0, "tr": False, "mh": -0.585},
    "GAIA_611520": {"common_name": "Gaia DR3 628080246633611520 (Leo, 9.55 pc)",         "role": "SCIENCE", "subrole": "ICECUBE_NORTHERN_10PC", "sid": "628080246633611520",  "ra": 148.478240, "dec": 20.948079, "pmra":  -345.973, "pmdec":  393.249, "d": 9.54528, "g": 12.3635, "bp": 14.2604, "rp": 11.0620, "j": None, "h": None, "k": None, "teff": 3006.5, "mass": 0.14, "rv": -11.3322, "n_pl": 0, "tr": False, "mh": -0.635},
    "GAIA_847104": {"common_name": "Gaia DR3 750586216906847104 (Leo Minor, 9.73 pc)",   "role": "SCIENCE", "subrole": "ICECUBE_NORTHERN_10PC", "sid": "750586216906847104",  "ra": 162.436287, "dec": 35.542870, "pmra":  -700.864, "pmdec":-1048.669, "d": 9.73216, "g": 11.6253, "bp": 13.2896, "rp": 10.3235, "j": None, "h": None, "k": None, "teff": 2900.0, "mass": 0.17, "rv": 64.6142, "n_pl": 0, "tr": False, "mh": 0.0},
    "GAIA_229632": {"common_name": "Gaia DR3 527956488340229632 (Cassiopeia, 9.89 pc)",  "role": "SCIENCE", "subrole": "ICECUBE_NORTHERN_10PC", "sid": "527956488340229632",  "ra":   8.143031, "dec": 67.234328, "pmra":  1748.319, "pmdec": -347.589, "d": 9.89252, "g":  9.5666, "bp": 10.7255, "rp":  8.4210, "j": None, "h": None, "k": None, "teff": 3350.0, "mass": 0.34, "rv": -3.3741, "n_pl": 0, "tr": False, "mh": 0.0},
    "GAIA_540416": {"common_name": "Gaia DR3 4535928365908540416 (Hercules, 9.93 pc)",   "role": "SCIENCE", "subrole": "ICECUBE_NORTHERN_10PC", "sid": "4535928365908540416", "ra": 280.293134, "dec": 24.787728, "pmra":   505.344, "pmdec":   87.045, "d": 9.93197, "g": 10.7255, "bp": 12.5397, "rp":  9.4415, "j": None, "h": None, "k": None, "teff": 3100.0, "mass": 0.22, "rv": 0.0, "n_pl": 0, "tr": False, "mh": 0.0},
    "GAIA_026560": {"common_name": "Gaia DR3 1618010323247026560 (Draco, 9.97 pc)",      "role": "SCIENCE", "subrole": "ICECUBE_NORTHERN_10PC", "sid": "1618010323247026560", "ra": 217.650336, "dec": 59.724274, "pmra":  -808.202, "pmdec":  157.397, "d": 9.96900, "g": 14.8437, "bp": 18.1480, "rp": 13.3511, "j": None, "h": None, "k": None, "teff": 2800.0, "mass": 0.10, "rv": 0.0, "n_pl": 0, "tr": False, "mh": 0.0},

    # --- 15 Brand-new Northern NEA Exoplanet Hosts in IceCube Up-Going FoV (dec >= 0 deg) ---
    "G261_6":     {"common_name": "G 261-6 (M5V Host, 10.63 pc)",        "role": "SCIENCE", "subrole": "ICECUBE_EXOPLANET_HOST", "sid": "2289304297045379456", "ra": 291.074320, "dec": 75.555841, "pmra":  369.422, "pmdec":  592.282, "d": 10.6267, "g": 13.4037, "bp": 15.6733, "rp": 12.0110, "j":  9.908, "h":  9.280, "k":  8.963, "teff": 2907.0, "mass": 0.118, "rv": -19.3317, "n_pl": 1, "tr": False, "mh":  0.000},
    "HD147379":   {"common_name": "HD 147379 (GJ 617 A, 10.76 pc)",     "role": "SCIENCE", "subrole": "ICECUBE_EXOPLANET_HOST", "sid": "1642641410934267008", "ra": 244.172569, "dec": 67.239204, "pmra": -497.915, "pmdec":   84.047, "d": 10.7643, "g":  7.9005, "bp":  8.7999, "rp":  6.9672, "j":  5.779, "h":  5.136, "k":  4.953, "teff": 4090.0, "mass": 0.580, "rv": -19.6198, "n_pl": 1, "tr": False, "mh": +0.160},
    "GJ1148":     {"common_name": "GJ 1148 (2-Planet M4V, 11.01 pc)",   "role": "SCIENCE", "subrole": "ICECUBE_EXOPLANET_HOST", "sid": "772430527947893632",  "ra": 175.432608, "dec": 42.751586, "pmra": -575.528, "pmdec":  -89.799, "d": 11.0143, "g": 10.5769, "bp": 12.1394, "rp":  9.3610, "j":  7.608, "h":  7.069, "k":  6.822, "teff": 3287.0, "mass": 0.344, "rv":  -8.9656, "n_pl": 2, "tr": False, "mh": +0.160},
    "ROSS508":    {"common_name": "Ross 508 (HZ Super-Earth, 11.21 pc)","role": "SCIENCE", "subrole": "ICECUBE_EXOPLANET_HOST", "sid": "1208695640675619584", "ra": 230.961302, "dec": 17.460535, "pmra": -391.919, "pmdec":-1259.296, "d": 11.2103, "g": 12.2066, "bp": 13.9882, "rp": 10.9204, "j":  9.105, "h":  8.620, "k":  8.279, "teff": 3071.0, "mass": 0.177, "rv":  42.1353, "n_pl": 1, "tr": False, "mh": -0.200},
    "GJ96":       {"common_name": "GJ 96 (Super-Neptune M0V, 11.93 pc)","role": "SCIENCE", "subrole": "ICECUBE_EXOPLANET_HOST", "sid": "354077348697687424",  "ra":  35.562403, "dec": 47.880207, "pmra":  216.134, "pmdec":   41.436, "d": 11.9315, "g":  8.6319, "bp":  9.6284, "rp":  7.6471, "j":  6.377, "h":  5.770, "k":  5.554, "teff": 3785.0, "mass": 0.600, "rv": -38.6053, "n_pl": 1, "tr": False, "mh": +0.140},
    "GL410":      {"common_name": "Gl 410 (DS Leo M0V Host, 11.93 pc)","role": "SCIENCE", "subrole": "ICECUBE_EXOPLANET_HOST", "sid": "3988689609004982912", "ra": 165.660421, "dec": 21.966916, "pmra":  142.771, "pmdec":  -51.661, "d": 11.9324, "g":  8.8070, "bp":  9.8196, "rp":  7.8139, "j":  6.522, "h":  5.899, "k":  5.688, "teff": 3842.0, "mass": 0.550, "rv": -14.4146, "n_pl": 1, "tr": False, "mh": +0.050},
    "GJ179":      {"common_name": "GJ 179 (Cold Jupiter M4V, 12.36 pc)","role": "SCIENCE", "subrole": "ICECUBE_EXOPLANET_HOST", "sid": "3288082758293929472", "ra":  73.024550, "dec":  6.475235, "pmra":    1.499, "pmdec":    8.825, "d": 12.3560, "g": 10.7055, "bp": 11.0654, "rp":  9.8189, "j":  7.814, "h":  7.209, "k":  6.942, "teff": 3370.0, "mass": 0.357, "rv":  78.1262, "n_pl": 1, "tr": False, "mh": +0.300},
    "GAMCEP":     {"common_name": "gamma Cephei (Binary Subgiant Host)","role": "SCIENCE", "subrole": "ICECUBE_EXOPLANET_HOST", "sid": "2281778105594488192", "ra": 354.835823, "dec": 77.633101, "pmra":  -64.860, "pmdec":  171.159, "d": 14.1024, "g":  2.9263, "bp":  3.6605, "rp":  2.4036, "j":  1.661, "h":  1.190, "k":  1.038, "teff": 4775.0, "mass": 1.260, "rv":   0.0000, "n_pl": 1, "tr": False, "mh": +0.200},
    "GJ685":      {"common_name": "GJ 685 (Super-Earth M0V, 14.32 pc)", "role": "SCIENCE", "subrole": "ICECUBE_EXOPLANET_HOST", "sid": "1439069444391326208", "ra": 263.896038, "dec": 61.679348, "pmra":  261.923, "pmdec": -514.499, "d": 14.3155, "g":  9.1671, "bp": 10.1906, "rp":  8.1746, "j":  6.884, "h":  6.271, "k":  6.066, "teff": 3816.0, "mass": 0.550, "rv": -15.5298, "n_pl": 1, "tr": False, "mh": -0.150},
    "HD86728":    {"common_name": "HD 86728 (20 LMi G3Va Host, 14.92 pc)","role": "SCIENCE", "subrole": "ICECUBE_EXOPLANET_HOST", "sid": "746545172372256384",  "ra": 150.250054, "dec": 31.921822, "pmra": -528.871, "pmdec": -429.376, "d": 14.9202, "g":  5.2094, "bp":  5.5445, "rp":  4.7039, "j":  4.267, "h":  4.040, "k":  3.821, "teff": 5610.0, "mass": 0.967, "rv":  55.9889, "n_pl": 1, "tr": False, "mh": +0.200},
    "GL378":      {"common_name": "Gl 378 (Warm Neptune M1V, 14.95 pc)", "role": "SCIENCE", "subrole": "ICECUBE_EXOPLANET_HOST", "sid": "823228721067307392",  "ra": 150.586551, "dec": 48.082451, "pmra": -633.074, "pmdec":-1474.827, "d": 14.9545, "g":  9.2652, "bp": 10.2876, "rp":  8.2623, "j":  6.949, "h":  6.355, "k":  6.160, "teff": 3879.0, "mass": 0.560, "rv": -10.1836, "n_pl": 1, "tr": False, "mh": +0.060},
    "HD238090":   {"common_name": "HD 238090 (Super-Earth M0V, 15.24 pc)","role": "SCIENCE", "subrole": "ICECUBE_EXOPLANET_HOST", "sid": "1573086442800134272", "ra": 183.088638, "dec": 54.486153, "pmra":  232.525, "pmdec":   92.148, "d": 15.2354, "g":  9.0379, "bp":  9.9761, "rp":  8.0876, "j":  6.875, "h":  6.245, "k":  6.059, "teff": 3933.0, "mass": 0.578, "rv": -17.4602, "n_pl": 1, "tr": False, "mh": -0.030},
    "TYC2187":    {"common_name": "TYC 2187-512-1 (Cold Sub-Jovian, 15.47 pc)","role": "SCIENCE", "subrole": "ICECUBE_EXOPLANET_HOST", "sid": "1791995119082190848", "ra": 320.526683, "dec": 22.931935, "pmra":  108.770, "pmdec":  117.794, "d": 15.4744, "g":  9.7703, "bp": 10.8307, "rp":  8.7556, "j":  7.400, "h":  6.800, "k":  6.595, "teff": 3734.0, "mass": 0.498, "rv":   5.4483, "n_pl": 1, "tr": False, "mh": +0.080},
    "GJ720A":     {"common_name": "GJ 720 A (Super-Earth M0V, 15.56 pc)","role": "SCIENCE", "subrole": "ICECUBE_EXOPLANET_HOST", "sid": "2118424350249708800", "ra": 278.829417, "dec": 45.745604, "pmra":  452.362, "pmdec":  363.466, "d": 15.5575, "g":  9.1050, "bp": 10.0665, "rp":  8.1371, "j":  6.881, "h":  6.260, "k":  6.082, "teff": 3837.0, "mass": 0.570, "rv": -32.0705, "n_pl": 1, "tr": False, "mh": -0.140},
    "LHS3154":    {"common_name": "LHS 3154 (High-Mass Planet M6V, 15.76 pc)","role": "SCIENCE", "subrole": "ICECUBE_EXOPLANET_HOST", "sid": "1380293126183384448", "ra": 241.636731, "dec": 40.906822, "pmra":   -6.622, "pmdec":    7.301, "d": 15.7606, "g": 14.8561, "bp": 13.3179, "rp": 12.3289, "j": 11.050, "h": 10.423, "k": 10.072, "teff": 2861.0, "mass": 0.112, "rv": -41.2386, "n_pl": 1, "tr": False, "mh":  0.000},

    # --- 1 Brand-new IceCube + Swift-XRT Astrophysical Neutrino Blazar Control ---
    "TXS0506":    {"common_name": "TXS 0506+056 (IceCube-170922A Blazar, z=0.3365)", "role": "CONTROL", "subrole": "ICECUBE_NEUTRINO_BLAZAR_CAL", "sid": "TXS0506", "ra": 77.358185, "dec": 5.693148, "pmra": 0.0, "pmdec": 0.0, "d": 1.775e9, "g": 14.6, "bp": None, "rp": None, "j": None, "h": None, "k": None, "teff": 6000.0, "mass": 1.0, "rv": 100950.0, "n_pl": 0, "tr": False, "mh": 0.0},

    # --- 12 Brand-new Galactic Symbiotics / Classical Novae / Magnetic CVs from Swift-BAT 157m ---
    "RTCRU":      {"common_name": "RT Cru (Hard-X Symbiotic Giant+WD, BAT+XRT)", "role": "SCIENCE", "subrole": "BAT_SYMBIOTIC_STAR",        "sid": "5861308338109134208", "ra": 188.72390, "dec": -64.56560, "pmra":  -9.546, "pmdec":  -1.161, "d": 2520.025, "g": 10.3768, "bp": 12.4667, "rp":  9.0394, "j": None, "h": None, "k": None, "teff": 3400.0, "mass": 1.2, "rv": 0.0,     "n_pl": 0, "tr": False, "mh": 0.0},
    "GKPER":      {"common_name": "GK Per (Nova Persei 1901 / IP, BAT+XRT)",    "role": "SCIENCE", "subrole": "BAT_CLASSICAL_NOVA_IP",     "sid": "238540495056450048",  "ra":  52.79930, "dec":  43.90470, "pmra":  -6.878, "pmdec": -17.348, "d":  433.592, "g": 12.5566, "bp": 13.1741, "rp": 11.7806, "j": None, "h": None, "k": None, "teff": 4800.0, "mass": 0.9, "rv": 0.0,     "n_pl": 0, "tr": False, "mh": 0.0},
    "V1223SGR":   {"common_name": "V1223 Sgr (Bright IP Control, BAT+XRT)",      "role": "CONTROL", "subrole": "MAGNETIC_CV_BAT_CAL",       "sid": "6760253239457454592", "ra": 283.75930, "dec": -31.16350, "pmra":   2.927, "pmdec": -24.636, "d":  573.006, "g": 13.0291, "bp": 13.0522, "rp": 12.9176, "j": None, "h": None, "k": None, "teff": 5500.0, "mass": 0.8, "rv": 0.0,     "n_pl": 0, "tr": False, "mh": 0.0},
    "V709CAS":    {"common_name": "V709 Cas (Intermediate Polar Control, BAT+XRT)","role": "CONTROL", "subrole": "MAGNETIC_CV_BAT_CAL",      "sid": "428101969045877504",  "ra":   7.20360, "dec":  59.28940, "pmra":   0.587, "pmdec":  -2.760, "d":  742.411, "g": 14.3939, "bp": 14.6741, "rp": 13.9046, "j": None, "h": None, "k": None, "teff": 5200.0, "mass": 0.8, "rv": 0.0,     "n_pl": 0, "tr": False, "mh": 0.0},
    "TVCOL":      {"common_name": "TV Col (DQ Her IP Control, BAT 157m)",       "role": "CONTROL", "subrole": "MAGNETIC_CV_BAT_CAL",       "sid": "2901783160488793728", "ra":  82.35600, "dec": -32.81790, "pmra":   8.718, "pmdec":  22.361, "d":  512.647, "g": 13.9807, "bp": 14.1109, "rp": 13.6551, "j": None, "h": None, "k": None, "teff": 5200.0, "mass": 0.8, "rv": 0.0,     "n_pl": 0, "tr": False, "mh": 0.0},
    "NYLUP":      {"common_name": "NY Lup (Hard-X IP Control, BAT 157m)",       "role": "CONTROL", "subrole": "MAGNETIC_CV_BAT_CAL",       "sid": "5988071475990738944", "ra": 237.06080, "dec": -45.47780, "pmra":  -1.321, "pmdec":  -2.507, "d":  790.114, "g": 12.8412, "bp": 13.0780, "rp": 12.2544, "j": None, "h": None, "k": None, "teff": 5000.0, "mass": 0.8, "rv": -23.4202,"n_pl": 0, "tr": False, "mh": 0.0},
    "RXJ2133":    {"common_name": "RX J2133.7+5107 (IP Control, BAT 157m)",     "role": "CONTROL", "subrole": "MAGNETIC_CV_BAT_CAL",       "sid": "2171623842411290368", "ra": 323.43200, "dec":  51.12360, "pmra": -13.499, "pmdec": -14.742, "d": 1145.296, "g": 14.5184, "bp": 15.2238, "rp": 13.6766, "j": None, "h": None, "k": None, "teff": 5000.0, "mass": 0.8, "rv": -22.2706,"n_pl": 0, "tr": False, "mh": 0.0},
    "FOAQR":      {"common_name": "FO Aqr (King of IPs Control, BAT 157m)",     "role": "CONTROL", "subrole": "MAGNETIC_CV_BAT_CAL",       "sid": "2616360833953395456", "ra": 334.48100, "dec":  -8.35130, "pmra":   2.276, "pmdec":   4.512, "d":  542.992, "g": 13.8577, "bp": 13.7258, "rp": 13.3935, "j": None, "h": None, "k": None, "teff": 5200.0, "mass": 0.8, "rv": 0.0,     "n_pl": 0, "tr": False, "mh": 0.0},
    "BYCAM":      {"common_name": "BY Cam (Asynchronous Polar Control, BAT 157m)","role": "CONTROL", "subrole": "MAGNETIC_CV_BAT_CAL",      "sid": "283187642167998720",  "ra":  85.70380, "dec":  60.85880, "pmra": -39.216, "pmdec":  -2.263, "d":  266.710, "g": 15.0166, "bp": 15.3341, "rp": 14.4413, "j": None, "h": None, "k": None, "teff": 4600.0, "mass": 0.8, "rv": 0.0,     "n_pl": 0, "tr": False, "mh": 0.0},
    "AOPSC":      {"common_name": "AO Psc (H2252-035 IP Control, BAT 157m)",    "role": "CONTROL", "subrole": "MAGNETIC_CV_BAT_CAL",       "sid": "2648391016419660032", "ra": 343.82490, "dec":  -3.17790, "pmra":   9.552, "pmdec": -17.548, "d":  470.581, "g": 13.2022, "bp": 13.2341, "rp": 13.1167, "j": None, "h": None, "k": None, "teff": 5200.0, "mass": 0.8, "rv": 0.0,     "n_pl": 0, "tr": False, "mh": 0.0},
    "V405AUR":    {"common_name": "V405 Aur (Hard-X IP Control, BAT 157m)",     "role": "CONTROL", "subrole": "MAGNETIC_CV_BAT_CAL",       "sid": "216146054533959552",  "ra":  89.49700, "dec":  53.89580, "pmra":   4.758, "pmdec":  -5.823, "d": 1090.552, "g": 13.3398, "bp": 13.6509, "rp": 12.8626, "j": None, "h": None, "k": None, "teff": 5200.0, "mass": 0.8, "rv": 0.1140,  "n_pl": 0, "tr": False, "mh": 0.0},
    "PQGEM":      {"common_name": "PQ Gem (RE 0751+144 IP Control, BAT 157m)",  "role": "CONTROL", "subrole": "MAGNETIC_CV_BAT_CAL",       "sid": "3164551664840579200", "ra": 117.82250, "dec":  14.74020, "pmra":  -9.450, "pmdec":   9.024, "d":  754.878, "g": 14.0604, "bp": 14.2041, "rp": 13.7440, "j": None, "h": None, "k": None, "teff": 5200.0, "mass": 0.8, "rv": 0.0,     "n_pl": 0, "tr": False, "mh": 0.0},

    # --- 6 Brand-new ESO Orbits #187-#192 Exoplanet Hosts (N=5 Distinct Nights Each) ---
    "L363_38":    {"common_name": "L 363-38 (ESPRESSO Orbit #187)",  "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "4999067471248893952", "ra":  10.8555443, "dec": -41.2952926, "pmra": -488.487, "pmdec":  -582.314, "d": 10.2295, "g": 11.5607, "bp": 13.2495, "rp": 10.3050, "j":  8.572, "h": 8.026, "k": 7.710, "teff": 3129.0, "mass": 0.210, "rv": -28.3061, "n_pl": 1, "tr": False, "mh":  0.000},
    "GJ27_1":     {"common_name": "GJ 27.1 (HARPS Orbit #188)",      "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "4980466929965023104", "ra":   9.9980016, "dec": -44.2541679, "pmra":  483.002, "pmdec":  -221.111, "d": 23.6062, "g": 10.5790, "bp": 11.6520, "rp":  9.5541, "j":  8.225, "h": 7.609, "k": 7.394, "teff": 3542.0, "mass": 0.530, "rv":  11.9444, "n_pl": 1, "tr": False, "mh":  0.000},
    "GJ328":      {"common_name": "GJ 328 (NIRPS Orbit #189)",       "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "577602496345490176",  "ra": 133.7819507, "dec":   1.5420011, "pmra":   44.944, "pmdec": -1045.876, "d": 20.5266, "g":  9.2861, "bp": 10.1863, "rp":  8.3539, "j":  7.191, "h": 6.523, "k": 6.352, "teff": 3897.0, "mass": 0.650, "rv":  -4.2677, "n_pl": 2, "tr": False, "mh": -0.060},
    "TOI771":     {"common_name": "TOI-771 (ESPRESSO Orbit #190)",   "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "5229384920706190208", "ra": 164.1138903, "dec": -72.9851736, "pmra":   -8.323, "pmdec":     4.133, "d": 25.2788, "g": 13.3671, "bp": 14.1080, "rp": 12.3617, "j": 10.507, "h": 9.955, "k": 9.664, "teff": 3370.0, "mass": 0.220, "rv":   6.4713, "n_pl": 2, "tr": True,  "mh": -0.130},
    "HIP12961":   {"common_name": "HIP 12961 (HARPS Orbit #191)",    "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "5077642283022422656", "ra":  41.6800749, "dec": -23.0860048, "pmra":  294.717, "pmdec":   140.966, "d": 23.3710, "g":  9.5989, "bp": 10.4729, "rp":  8.6867, "j":  7.558, "h": 6.927, "k": 6.736, "teff": 3901.0, "mass": 0.690, "rv":  32.4914, "n_pl": 1, "tr": False, "mh": -0.140},
    "GJ3634":     {"common_name": "GJ 3634 (HARPS Orbit #192)",      "role": "SCIENCE", "subrole": "KEPLERIAN_ORBIT_CAMPAIGN", "sid": "5452743423618768000", "ra": 164.6433493, "dec": -31.1443383, "pmra": -566.980, "pmdec":   -91.397, "d": 20.3779, "g": 10.9233, "bp": 12.1718, "rp":  9.8246, "j":  8.361, "h": 7.762, "k": 7.470, "teff": 3517.0, "mass": 0.450, "rv":   4.9287, "n_pl": 1, "tr": False, "mh":  0.000},
}

# 54 IceCube 10-Yr Neutrino Targets: (canon, is_prior_bridge, panchrom_bridge, track_label)
ICECUBE_TARGETS: list[tuple[str, bool, bool, str]] = [
    # 20 Prior Bridges (16 Cyg B Quad-Messenger + 17 Single-Phase Northern SCIENCE + NGC 1068 + Mrk 421)
    ("16CYGB",     True,  True,  "QUAD_MESSENGER_EXOPLANET_BRIDGE"),
    ("NGC1068",    True,  True,  "ICECUBE_SEYFERT2_NEUTRINO_BENCHMARK"),
    ("MRK421",     True,  True,  "ICECUBE_BLAZAR_CONTROL_BRIDGE"),
    ("ROSS128",    True,  True,  "ICECUBE_NORTHERN_BRIDGE_UPGRADE"),
    ("STRUVE2398A",True,  True,  "ICECUBE_NORTHERN_BRIDGE_UPGRADE"),
    ("STRUVE2398B",True,  True,  "ICECUBE_NORTHERN_BRIDGE_UPGRADE"),
    ("GJ273",      True,  True,  "ICECUBE_NORTHERN_BRIDGE_UPGRADE"),
    ("TEEGARDEN",  True,  True,  "ICECUBE_NORTHERN_BRIDGE_UPGRADE"),
    ("VMA2",       True,  True,  "ICECUBE_NORTHERN_BRIDGE_UPGRADE"),
    ("GJ9066",     True,  True,  "ICECUBE_NORTHERN_BRIDGE_UPGRADE"),
    ("GJ1245B",    True,  True,  "ICECUBE_NORTHERN_BRIDGE_UPGRADE"),
    ("HD165341",   True,  True,  "ICECUBE_NORTHERN_BRIDGE_UPGRADE"),
    ("GJ445",      True,  True,  "ICECUBE_NORTHERN_BRIDGE_UPGRADE"),
    ("HD119850",   True,  True,  "ICECUBE_NORTHERN_BRIDGE_UPGRADE"),
    ("GJ251",      True,  True,  "ICECUBE_NORTHERN_BRIDGE_UPGRADE"),
    ("LSRJ1835",   True,  True,  "ICECUBE_NORTHERN_BRIDGE_UPGRADE"),
    ("SIMP0136",   True,  True,  "ICECUBE_NORTHERN_BRIDGE_UPGRADE"),
    ("47UMA",      True,  True,  "ICECUBE_NORTHERN_BRIDGE_UPGRADE"),
    ("51PEG",      True,  True,  "ICECUBE_NORTHERN_BRIDGE_UPGRADE"),
    ("70VIR",      True,  True,  "ICECUBE_NORTHERN_BRIDGE_UPGRADE"),
    # 18 Brand-New <10 pc Gaia DR3 Northern/Equatorial Stars
    ("GAIA_990720",False, False, "SOLAR_NEIGHBORHOOD_10PC_V65_ICECUBE"),
    ("GAIA_665088",False, False, "SOLAR_NEIGHBORHOOD_10PC_V65_ICECUBE"),
    ("GAIA_940608",False, False, "SOLAR_NEIGHBORHOOD_10PC_V65_ICECUBE"),
    ("GAIA_539840",False, False, "SOLAR_NEIGHBORHOOD_10PC_V65_ICECUBE"),
    ("GAIA_160000",False, False, "SOLAR_NEIGHBORHOOD_10PC_V65_ICECUBE"),
    ("GAIA_790464",False, False, "SOLAR_NEIGHBORHOOD_10PC_V65_ICECUBE"),
    ("GAIA_536000",False, False, "SOLAR_NEIGHBORHOOD_10PC_V65_ICECUBE"),
    ("GAIA_871360",False, False, "SOLAR_NEIGHBORHOOD_10PC_V65_ICECUBE"),
    ("GAIA_374336",False, False, "SOLAR_NEIGHBORHOOD_10PC_V65_ICECUBE"),
    ("GAIA_596096",False, False, "SOLAR_NEIGHBORHOOD_10PC_V65_ICECUBE"),
    ("GAIA_639744",False, False, "SOLAR_NEIGHBORHOOD_10PC_V65_ICECUBE"),
    ("GAIA_576576",False, False, "SOLAR_NEIGHBORHOOD_10PC_V65_ICECUBE"),
    ("GAIA_994560",False, False, "SOLAR_NEIGHBORHOOD_10PC_V65_ICECUBE"),
    ("GAIA_611520",False, False, "SOLAR_NEIGHBORHOOD_10PC_V65_ICECUBE"),
    ("GAIA_847104",False, False, "SOLAR_NEIGHBORHOOD_10PC_V65_ICECUBE"),
    ("GAIA_229632",False, False, "SOLAR_NEIGHBORHOOD_10PC_V65_ICECUBE"),
    ("GAIA_540416",False, False, "SOLAR_NEIGHBORHOOD_10PC_V65_ICECUBE"),
    ("GAIA_026560",False, False, "SOLAR_NEIGHBORHOOD_10PC_V65_ICECUBE"),
    # 15 Brand-New Northern NEA Exoplanet Hosts
    ("G261_6",     False, False, "ICECUBE_NORTHERN_EXOPLANET_V65"),
    ("HD147379",   False, False, "ICECUBE_NORTHERN_EXOPLANET_V65"),
    ("GJ1148",     False, False, "ICECUBE_NORTHERN_EXOPLANET_V65"),
    ("ROSS508",    False, False, "ICECUBE_NORTHERN_EXOPLANET_V65"),
    ("GJ96",       False, False, "ICECUBE_NORTHERN_EXOPLANET_V65"),
    ("GL410",      False, False, "ICECUBE_NORTHERN_EXOPLANET_V65"),
    ("GJ179",      False, False, "ICECUBE_NORTHERN_EXOPLANET_V65"),
    ("GAMCEP",     False, False, "ICECUBE_NORTHERN_EXOPLANET_V65"),
    ("GJ685",      False, False, "ICECUBE_NORTHERN_EXOPLANET_V65"),
    ("HD86728",    False, False, "ICECUBE_NORTHERN_EXOPLANET_V65"),
    ("GL378",      False, False, "ICECUBE_NORTHERN_EXOPLANET_V65"),
    ("HD238090",   False, False, "ICECUBE_NORTHERN_EXOPLANET_V65"),
    ("TYC2187",    False, False, "ICECUBE_NORTHERN_EXOPLANET_V65"),
    ("GJ720A",     False, False, "ICECUBE_NORTHERN_EXOPLANET_V65"),
    ("LHS3154",    False, False, "ICECUBE_NORTHERN_EXOPLANET_V65"),
    # 1 Brand-New Neutrino Blazar Control (also Swift-XRT)
    ("TXS0506",    False, True,  "ICECUBE_170922A_BLAZAR_CONTROL"),
]

# 30 NASA Swift-BAT 157-Month Hard X-Ray Targets: (canon, bat_name, is_prior_bridge, panchrom_bridge)
BAT_TARGETS: list[tuple[str, str, bool, bool]] = [
    # 18 Prior Bridges (7 SCIENCE + 11 CONTROL)
    ("OMC1",       "SWIFT J0535.3-0520", True,  True),
    ("GTMUS",      "SWIFT J1139.5-6526", True,  True),
    ("CHCYG",      "SWIFT J1924.5+5014", True,  True),
    ("V648CAR",    "SWIFT J1010.1-5747", True,  True),
    ("SSCYG",      "SWIFT J2142.7+4337", True,  True),
    ("TCRB",       "SWIFT J1559.6+2554", True,  True),
    ("GAMMACAS",   "SWIFT J0056.7+6043", True,  True),
    ("NGC1068",    "SWIFT J0242.6+0000", True,  True),
    ("NGC7469",    "SWIFT J2303.3+0852", True,  True),
    ("MRK421",     "SWIFT J1104.4+3812", True,  True),
    ("3C273",      "SWIFT J1229.1+0202", True,  True),
    ("CENA",       "SWIFT J1325.4-4301", True,  True),
    ("HERX1",      "SWIFT J1657.7+3518", True,  True),
    ("CYGX3",      "SWIFT J2032.5+4055", True,  True),
    ("VELAX1",     "SWIFT J0902.1-4034", True,  True),
    ("SCOX1",      "SWIFT J1620.1-1539", True,  True),
    ("CYGX1",      "SWIFT J1958.4+3510", True,  True),
    ("CRABNEBULA", "SWIFT J0534.6+2204", True,  True),
    # 12 Brand-New Galactic Symbiotics / Novae / Magnetic CVs (4 also in Swift-XRT!)
    ("RTCRU",      "SWIFT J1234.7-6433", False, True),
    ("GKPER",      "SWIFT J0331.1+4355", False, True),
    ("V1223SGR",   "SWIFT J1855.0-3110", False, True),
    ("V709CAS",    "SWIFT J0028.9+5917", False, True),
    ("TVCOL",      "SWIFT J0529.2-3247", False, False),
    ("NYLUP",      "SWIFT J1548.0-4529", False, False),
    ("RXJ2133",    "SWIFT J2133.6+5105", False, False),
    ("FOAQR",      "SWIFT J2217.5-0812", False, False),
    ("BYCAM",      "SWIFT J0542.6+6051", False, False),
    ("AOPSC",      "SWIFT J2255.4-0309", False, False),
    ("V405AUR",    "SWIFT J0558.0+5352", False, False),
    ("PQGEM",      "SWIFT J0750.9+1439", False, False),
]

# 20 NASA Swift-XRT Targets: (canon, is_prior_bridge, panchrom_bridge, obsid, ym, fname, mode, exp_s, bytes)
XRT_TARGETS: list[tuple[str, bool, bool, str, str, str, str, float, int]] = [
    ("PROXIMACEN",   True,  True, "03000372002", "2026_01", "sw03000372002xpcw3po_cl.evt.gz", "PC",  8090.0,   74801),
    ("BARNARDSSTAR", True,  True, "00096725002", "2022_09", "sw00096725002xwtw2po_cl.evt.gz", "WT", 10943.0,  154072),
    ("AUMIC",        True,  True, "03400165001", "2025_06", "sw03400165001xpcw3po_cl.evt.gz", "PC",  9432.4,  129901),
    ("EVLAC",        True,  True, "00310125000", "2008_04", "sw00310125000xpcw2po_cl.evt.gz", "PC", 18019.1,  346645),
    ("EPSERI",       True,  True, "00016804004", "2024_11", "sw00016804004xwtw2po_cl.evt.gz", "WT",  5446.1,  106554),
    ("YZCET",        True,  True, "00094143003", "2018_10", "sw00094143003xpcw3po_cl.evt.gz", "PC",  4922.6,   38545),
    ("TRAPPIST1",    True,  True, "00010283023", "2018_06", "sw00010283023xpcw3po_cl.evt.gz", "PC", 19473.9,   96433),
    ("ABDOR",        True,  True, "00050500004", "2005_02", "sw00050500004xpcw4po_cl.evt.gz", "PC", 21182.1,  450099),
    ("DGCVN",        True,  True, "00596958001", "2014_04", "sw00596958001xpcw3po_cl.evt.gz", "PC",  8780.0,  261478),
    ("CRDRA",        True,  True, "00096752008", "2022_04", "sw00096752008xpcw3po_cl.evt.gz", "PC",  1256.2,  120692),
    ("IIPEG",        True,  True, "00172969000", "2005_12", "sw00172969000xwtw2po_cl.evt.gz", "WT",  4596.9, 8655021),
    ("NGC1068",      True,  True, "00037216004", "2011_07", "sw00037216004xpcw3po_cl.evt.gz", "PC",  6171.8,  100448),
    ("MRK421",       True,  True, "00030352011", "2006_06", "sw00030352011xwtw2po_cl.evt.gz", "WT", 33288.9,19180533),
    ("3C273",        True,  True, "00050900025", "2018_07", "sw00050900025xwtw2po_cl.evt.gz", "WT", 17097.2, 1307732),
    ("CENA",         True,  True, "00034314002", "2016_02", "sw00034314002xpcw3po_cl.evt.gz", "PC",  9721.6,  277097),
    # 5 Brand-New Dual-Instrument Targets
    ("RTCRU",        False, True, "00030840010", "2015_11", "sw00030840010xpcw3po_cl.evt.gz", "PC",  4094.4,   62166),
    ("GKPER",        False, True, "00031653031", "2010_03", "sw00031653031xpcw3po_cl.evt.gz", "PC",  1774.8,   53015),
    ("V1223SGR",     False, True, "00034154002", "2015_11", "sw00034154002xpcw3po_cl.evt.gz", "PC",  1776.0,   45164),
    ("V709CAS",      False, True, "00037151011", "2008_04", "sw00037151011xpcw2po_cl.evt.gz", "PC",  6708.7,  101433),
    ("TXS0506",      False, True, "00095333005", "2019_10", "sw00095333005xpcw3po_cl.evt.gz", "PC",  5322.5,   46257),
]

# 6 Brand-new ESO Planet-Host Orbital Campaigns #187-#192 (N=5 Distinct Nights Each)
ESO_ORBIT_CAMPAIGNS: list[dict[str, Any]] = [
    {
        "campaign_order": 187, "star": "L363_38", "planet_name": "L 363-38 b",
        "instrument": "ESO_ESPRESSO", "grating": "ESPRESSO_377_790NM", "r": 140000.0,
        "orb_per_days": 8.781, "orb_ecc": 0.0, "orb_omega_deg": 0.0, "orb_t0_bjd": 2458500.0, "kp_kms": 0.00412,
        "exposures": [
            ("ADP.2021-12-09T15:19:50.139", 59528.066850, 900.0, 39.7, 55111680),
            ("ADP.2021-12-09T16:13:09.637", 59534.020670, 900.0, 37.5, 55111680),
            ("ADP.2021-12-10T10:24:27.226", 59543.021589, 900.0, 39.0, 55111680),
            ("ADP.2021-12-10T10:28:14.690", 59544.033880, 900.0, 41.6, 55111680),
            ("ADP.2022-12-05T12:38:52.521", 59913.128189, 900.0, 42.4, 55111680),
        ],
    },
    {
        "campaign_order": 188, "star": "GJ27_1", "planet_name": "GJ 27.1 b",
        "instrument": "ESO_HARPS", "grating": "HARPS_378_691NM", "r": 115000.0,
        "orb_per_days": 15.819, "orb_ecc": 0.08, "orb_omega_deg": 150.0, "orb_t0_bjd": 2455000.0, "kp_kms": 0.00490,
        "exposures": [
            ("ADP.2014-09-17T11:22:26.170", 54398.008178, 899.995, 24.1, 0),
            ("ADP.2014-09-17T11:20:31.737", 54428.106999, 900.000, 26.3, 0),
            ("ADP.2014-09-17T11:19:52.830", 54454.112177, 900.000, 28.0, 0),
            ("ADP.2014-09-17T11:20:52.313", 54458.035283, 900.000, 25.6, 0),
            ("ADP.2014-09-18T12:09:51.333", 54481.029615, 900.000, 24.6, 0),
        ],
    },
    {
        "campaign_order": 189, "star": "GJ328", "planet_name": "GJ 328 b",
        "instrument": "ESO_NIRPS", "grating": "NIRPS_YJH_966_1923NM", "r": 70000.0,
        "orb_per_days": 3771.0, "orb_ecc": 0.227, "orb_omega_deg": -76.2, "orb_t0_bjd": 2454500.0, "kp_kms": 0.04260,
        "exposures": [
            ("ADP.2025-04-16T07:51:27.467", 60321.188325, 451.437, 131.3, 47111040),
            ("ADP.2025-04-16T09:42:09.664", 60351.177530, 451.437, 135.9, 47111040),
            ("ADP.2025-02-24T11:22:23.108", 60696.127385, 451.437, 129.2, 47111040),
            ("ADP.2025-09-03T12:22:27.535", 60797.999202, 451.437, 141.5, 47111040),
            ("ADP.2025-09-03T12:22:28.204", 60817.985637, 451.437, 138.0, 47111040),
        ],
    },
    {
        "campaign_order": 190, "star": "TOI771", "planet_name": "TOI-771 b",
        "instrument": "ESO_ESPRESSO", "grating": "ESPRESSO_377_790NM", "r": 140000.0,
        "orb_per_days": 2.3260155, "orb_ecc": 0.055, "orb_omega_deg": -130.0, "orb_t0_bjd": 2458572.4191, "kp_kms": 0.00329,
        "exposures": [
            ("ADP.2024-01-04T15:02:12.625", 60284.315429, 1800.0, 23.0, 55111680),
            ("ADP.2024-01-04T15:35:19.352", 60300.248932, 1800.0, 21.3, 55111680),
            ("ADP.2024-03-08T10:10:19.387", 60343.283859, 1800.0, 20.6, 55111680),
            ("ADP.2024-04-09T09:00:56.091", 60374.142171, 1800.0, 24.8, 55111680),
            ("ADP.2024-04-09T09:10:52.303", 60378.321631, 1800.0, 21.9, 55111680),
        ],
    },
    {
        "campaign_order": 191, "star": "HIP12961", "planet_name": "HIP 12961 b",
        "instrument": "ESO_HARPS", "grating": "HARPS_378_691NM", "r": 115000.0,
        "orb_per_days": 57.435, "orb_ecc": 0.17, "orb_omega_deg": 272.0, "orb_t0_bjd": 2454000.0, "kp_kms": 0.02470,
        "exposures": [
            ("ADP.2014-10-02T10:02:16.987", 53722.152127,  900.001, 53.4, 0),
            ("ADP.2014-09-18T12:14:34.143", 54720.297436,  828.300, 43.5, 0),
            ("ADP.2014-09-18T12:14:48.587", 54752.276029, 1200.000, 48.2, 0),
            ("ADP.2014-09-23T11:04:56.497", 55090.311455,  900.000, 41.4, 0),
            ("ADP.2014-09-23T11:03:17.983", 55109.277835,  900.000, 45.2, 0),
        ],
    },
    {
        "campaign_order": 192, "star": "GJ3634", "planet_name": "GJ 3634 b",
        "instrument": "ESO_HARPS", "grating": "HARPS_378_691NM", "r": 115000.0,
        "orb_per_days": 2.64561, "orb_ecc": 0.08, "orb_omega_deg": 84.0, "orb_t0_bjd": 2454917.04, "kp_kms": 0.00559,
        "exposures": [
            ("ADP.2014-09-23T11:01:24.363", 54933.086371, 900.000, 18.0, 0),
            ("ADP.2014-09-23T11:03:04.617", 54941.083715, 900.000, 21.2, 0),
            ("ADP.2014-09-24T09:42:04.797", 55238.328024, 900.001, 18.3, 0),
            ("ADP.2014-09-24T09:44:52.797", 55239.282757, 899.999, 17.6, 0),
            ("ADP.2014-09-24T09:44:21.240", 55244.352589, 899.999, 19.0, 0),
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
    is_eso = "dataportal.eso.org" in base_url
    last_exc: Exception | None = None
    for attempt in range(6):
        if is_eso:
            time.sleep(0.35 + 0.25 * attempt)
        # Try Range GET first (handles ESO FITS sizes + ICECUBE + HEASARC), fall back to HEAD on HTTP 416 (dynamic HARPS)
        headers = {"User-Agent": "SETI-V6.5-D107-Lock/1.0", "Connection": "close", "Range": "bytes=0-63"}
        try:
            req = urllib.request.Request(base_url, method="GET", headers=headers)
            with urllib.request.urlopen(req, timeout=45) as resp:
                head_b = resp.read(64)
                if is_eso and not head_b.startswith(b"SIMPLE"):
                    raise IOError(f"ESO rate-limit/XML response on Range GET: {head_b[:40]!r}")
                status = int(resp.status)
                cr = resp.headers.get("Content-Range", "")
                if "/" in cr:
                    tail = cr.rsplit("/", 1)[-1].strip()
                    if tail.isdigit():
                        return (200 if status == 206 else status), int(tail)
                cl = resp.headers.get("Content-Length", "0")
                return (200 if status == 206 else status), int(cl) if cl and cl.isdigit() else 0
        except urllib.error.HTTPError as he:
            if he.code == 416:
                req_h = urllib.request.Request(base_url, method="HEAD", headers={"User-Agent": "SETI-V6.5-D107-Lock/1.0", "Connection": "close"})
                with urllib.request.urlopen(req_h, timeout=45) as rh:
                    return int(rh.status), 0
            last_exc = he
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
            "common_name": u["common_name"], "role": u["role"], "subrole": u["subrole"], "sid": canon,
            "ra": ra, "dec": dec, "pmra": 0.0, "pmdec": 0.0, "d": d,
            "within_10pc": str(u["within_10pc"]).lower() == "true",
            "g": u.get("phot_g_mag") or "", "bp": "", "rp": "",
            "j": u.get("j_mag") or "", "h": u.get("h_mag") or "", "k": u.get("ks_mag") or "",
            "teff": float(u["teff_k"]) if u.get("teff_k") else 5000.0, "mh": 0.0, "mass": 1.0,
            "rv": 0.0, "n_pl": int(float(u.get("n_exoplanets") or 0)), "tr": False,
        }
    m = NEW_META[canon]
    return {
        "common_name": m["common_name"], "role": m["role"], "subrole": m["subrole"], "sid": m["sid"],
        "ra": float(m["ra"]), "dec": float(m["dec"]), "pmra": float(m["pmra"]), "pmdec": float(m["pmdec"]),
        "d": float(m["d"]), "within_10pc": float(m["d"]) < 10.0,
        "g": "" if m["g"] is None else f"{float(m['g']):.4f}",
        "bp": "" if m["bp"] is None else f"{float(m['bp']):.4f}",
        "rp": "" if m["rp"] is None else f"{float(m['rp']):.4f}",
        "j": "" if m["j"] is None else f"{float(m['j']):.3f}",
        "h": "" if m["h"] is None else f"{float(m['h']):.3f}",
        "k": "" if m["k"] is None else f"{float(m['k']):.3f}",
        "teff": float(m["teff"]), "mh": float(m.get("mh", 0.0)), "mass": float(m["mass"]),
        "rv": float(m["rv"]), "n_pl": int(m["n_pl"]), "tr": bool(m["tr"]),
    }


def _make_row(
    *, inst: str, canon: str, meta: dict[str, Any], is_prior_bridge: bool, panchromatic_bridge: bool,
    science_track: str, epoch_rank: int, dp_id: str, grating: str, resolving_power: float,
    mjd_obs: float, t_exptime: float, phase_window: str, signed_phase: float, planet_orbital_rv_kms: float,
    f1_rel: str, f1_url: str, f1_bytes: int, total_bytes: int | None = None, extra_files_json: str = "[]",
) -> dict[str, Any]:
    sync = det.compute_multievent_sync_v51(meta["ra"], meta["dec"], meta["d"], mjd_obs)
    return {
        "instrument": inst, "canonical_target": canon, "common_name": meta["common_name"],
        "role": meta["role"], "subrole": meta["subrole"], "science_track": science_track,
        "panchromatic_bridge": str(panchromatic_bridge), "is_prior_bridge": str(is_prior_bridge),
        "gaia_source_id": meta["sid"], "s_ra": f"{meta['ra']:.7f}", "s_dec": f"{meta['dec']:.7f}",
        "pmra_mas_yr": f"{meta['pmra']:.3f}", "pmdec_mas_yr": f"{meta['pmdec']:.3f}",
        "dist_pc": f"{meta['d']:.5f}", "within_10pc": str(meta["within_10pc"]),
        "phot_g_mag": meta["g"], "phot_bp_mag": meta["bp"], "phot_rp_mag": meta["rp"],
        "j_mag": meta["j"], "h_mag": meta["h"], "ks_mag": meta["k"],
        "teff_k": f"{meta['teff']:.1f}", "mh_dex": f"{meta['mh']:.3f}",
        "stellar_mass_msun": f"{meta['mass']:.4f}", "prior_rv_kms": f"{meta['rv']:.4f}",
        "n_exoplanets": str(meta["n_pl"]), "has_transiting_planet": str(meta["tr"]),
        "ecliptic_lat_deg": f"{sync['ecliptic_lat_deg']:.5f}",
        "sn1987a_dt_days": f"{sync['sn1987a_dt_days']:.3f}",
        "gw170817_dt_days": f"{sync['gw170817_dt_days']:.3f}",
        "sn2023ixf_dt_days": f"{sync['sn2023ixf_dt_days']:.3f}",
        "ppo_align_score": "1.0", "epoch_rank": str(epoch_rank), "dp_id": dp_id,
        "grating": grating, "resolving_power": f"{resolving_power:.1f}",
        "mjd_obs": f"{mjd_obs:.6f}", "t_exptime": f"{t_exptime:.3f}",
        "phase_window": phase_window, "signed_phase": f"{signed_phase:.5f}",
        "planet_orbital_rv_kms": f"{planet_orbital_rv_kms:.6f}",
        "f1_id": dp_id, "f1_rel": f1_rel, "f1_url": f1_url,
        "f1_bytes": str(f1_bytes), "total_bytes": str(f1_bytes if total_bytes is None else total_bytes),
        "extra_files": extra_files_json,
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    if RAW_DIR.exists():
        raise RuntimeError(f"Chronology violation: {RAW_DIR} must NOT exist before Stage-1 seal!")

    af_sha = _sha256_file(ARCHIVE_AF)
    b106_sha = _sha256_file(BUNDLE_106)
    if af_sha != ARCHIVE_AF_SHA256 or b106_sha != BUNDLE_106_SHA256:
        raise RuntimeError(f"Archive AF or d106 bundle SHA mismatch ({af_sha}, {b106_sha})")

    pe106 = json.loads((WS106 / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    d106_cohort = _read_csv(WS106 / "FROZEN_COHORT_D106.csv")
    u852_rows = _read_csv(WS106 / "results/UNIFIED_PANCHROMATIC_V6_4_SYNTHESIS_852STARS.csv")
    br1665_rows = _read_csv(WS106 / "results/PANCHROMATIC_BRIDGE_119STARS_V64.csv")
    comb_u564_rows = _read_csv(WS106 / "results/ALLSKY_COMB_V4_1_UNIFIED_D079_D106.csv")
    comb_c_rows = _read_csv(WS106 / "results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D106.csv")
    ell852_rows = _read_csv(WS106 / "results/MULTIEVENT_ELLIPSOID_852STARS.csv")
    s106 = json.loads((WS106 / "results/SUMMARY.json").read_text(encoding="utf-8"))

    u_map = {r["star"]: r for r in u852_rows}
    coord_by_star: dict[str, tuple[float, float]] = {
        r["star"]: (float(r["ra_deg"]), float(r["dec_deg"])) for r in ell852_rows
    }
    for t in pe106["excluded_targets_coordinate_registry"]:
        nm = str(t.get("canonical_target") or "").strip()
        if nm and nm not in coord_by_star:
            coord_by_star[nm] = (float(t["ra_deg"]), float(t["dec_deg"]))
    for r in d106_cohort:
        nm = r["canonical_target"]
        if nm not in coord_by_star:
            coord_by_star[nm] = (float(r["s_ra"]), float(r["s_dec"]))

    prior_coords: list[dict[str, Any]] = list(pe106["excluded_targets_coordinate_registry"])
    seen_d106_new = set()
    for r in d106_cohort:
        if str(r["is_prior_bridge"]).lower() not in ("true", "1", "yes"):
            nm = r["canonical_target"]
            if nm not in seen_d106_new:
                seen_d106_new.add(nm)
                prior_coords.append({"canonical_target": nm, "ra_deg": float(r["s_ra"]), "dec_deg": float(r["s_dec"])})

    prior_dp_ids = sorted(set(pe106["excluded_dp_ids"]) | {r["dp_id"] for r in d106_cohort})
    format_probes = sorted(set(pe106["format_check_excluded_dp_ids"]))
    assert len(prior_coords) == 925, f"Expected 925 prior coords, got {len(prior_coords)}"
    assert len(prior_dp_ids) == 3801, f"Expected 3801 prior dp_ids, got {len(prior_dp_ids)}"
    assert len(format_probes) == 46, f"Expected 46 format probes, got {len(format_probes)}"

    rows: list[dict[str, Any]] = []

    # 1. 54 IceCube 10-Yr Neutrino Targets
    for canon, is_b, is_pb, trk in ICECUBE_TARGETS:
        if is_b:
            assert canon in u_map, f"Missing IceCube bridge {canon}"
        meta = _star_meta(canon, is_b, u_map, coord_by_star)
        rows.append(_make_row(
            inst="ICECUBE_10YR", canon=canon, meta=meta, is_prior_bridge=is_b, panchromatic_bridge=bool(is_b or is_pb),
            science_track=trk, epoch_rank=1, dp_id=f"ICECUBE_10YR_{canon}", grating="ICECUBE_0P1TEV_10PEV",
            resolving_power=1.5, mjd_obs=56450.0, t_exptime=270600000.0,
            phase_window="NONE", signed_phase=0.0, planet_orbital_rv_kms=0.0,
            f1_rel=ICECUBE_ZIP_REL, f1_url=ICECUBE_ZIP_URL, f1_bytes=ICECUBE_ZIP_BYTES,
        ))

    # 2. 30 NASA Swift-BAT 157-Month Hard X-Ray Targets
    bat0_rel, bat0_url, bat0_sz = BAT_FILES[0]
    bat_extras = [{"rel": rel, "url": url, "bytes": sz} for rel, url, sz in BAT_FILES[1:]]
    bat_tot_sz = sum(sz for _, _, sz in BAT_FILES)
    for canon, bat_name, is_b, is_pb in BAT_TARGETS:
        if is_b:
            assert canon in u_map, f"Missing BAT bridge {canon}"
        meta = _star_meta(canon, is_b, u_map, coord_by_star)
        rows.append(_make_row(
            inst="SWIFT_BAT", canon=canon, meta=meta, is_prior_bridge=is_b, panchromatic_bridge=bool(is_b or is_pb),
            science_track="SWIFT_BAT_157M_14_195KEV_V65", epoch_rank=1, dp_id=f"BAT157M_{canon}",
            grating=bat_name, resolving_power=5.0, mjd_obs=55650.0, t_exptime=412905600.0,
            phase_window="NONE", signed_phase=0.0, planet_orbital_rv_kms=0.0,
            f1_rel=bat0_rel, f1_url=bat0_url, f1_bytes=bat0_sz, total_bytes=bat_tot_sz,
            extra_files_json=json.dumps(bat_extras),
        ))

    # 3. 20 NASA Swift-XRT (0.3-10 keV PC/WT CCD + CALDB RMF/ARF) Targets
    for canon, is_b, is_pb, obsid, ym, fname, mode, exp_s, f_bytes in XRT_TARGETS:
        if is_b:
            assert canon in u_map, f"Missing XRT bridge {canon}"
        meta = _star_meta(canon, is_b, u_map, coord_by_star)
        ev_rel = f"SWIFT_XRT/events/{fname}"
        ev_url = f"https://heasarc.gsfc.nasa.gov/FTP/swift/data/obs/{ym}/{obsid}/xrt/event/{fname}"
        arf_k = "PC_ARF" if mode == "PC" else "WT_ARF"
        rmf_k = "PC_RMF" if mode == "PC" else "WT_RMF"
        x_extras = [
            {"rel": XRT_CALDB[arf_k][0], "url": XRT_CALDB[arf_k][1], "bytes": XRT_CALDB[arf_k][2]},
            {"rel": XRT_CALDB[rmf_k][0], "url": XRT_CALDB[rmf_k][1], "bytes": XRT_CALDB[rmf_k][2]},
        ]
        tot_x = f_bytes + XRT_CALDB[arf_k][2] + XRT_CALDB[rmf_k][2]
        rows.append(_make_row(
            inst="SWIFT_XRT", canon=canon, meta=meta, is_prior_bridge=is_b, panchromatic_bridge=bool(is_b or is_pb),
            science_track="SWIFT_XRT_0P3_10KEV_V65", epoch_rank=1, dp_id=f"XRT_{obsid}_{canon}",
            grating=f"XRT_{mode}_0P3_10KEV", resolving_power=25.0, mjd_obs=57500.0, t_exptime=exp_s,
            phase_window="NONE", signed_phase=0.0, planet_orbital_rv_kms=0.0,
            f1_rel=ev_rel, f1_url=ev_url, f1_bytes=f_bytes, total_bytes=tot_x,
            extra_files_json=json.dumps(x_extras),
        ))

    # 4. 6 Brand-New ESO Orbits #187-#192 (30 Distinct-Night Spectra)
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
                science_track=f"ORBITAL_CAMPAIGN_V65_{camp['campaign_order']}", epoch_rank=idx, dp_id=dp_id,
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
            "campaign_order": camp["campaign_order"], "phase_id": "D107",
            "canonical_target": canon, "common_name": meta["common_name"],
            "instrument": inst, "grating": camp["grating"],
            "resolving_power": camp["r"], "planet_name": camp["planet_name"],
            "orb_per_days": camp["orb_per_days"], "orb_ecc": camp["orb_ecc"],
            "orb_omega_deg": camp["orb_omega_deg"], "orb_t0_bjd": camp["orb_t0_bjd"],
            "kp_kms": camp["kp_kms"], "exposures": camp_exps, "n_epochs": len(camp_exps),
            "baseline_days": round(max(mjs) - min(mjs), 4),
            "orbital_dv_span_kms": round(max(rvs) - min(rvs), 6),
        }

    # Strict exclusions, separations & HTTP 200 verification
    dp_set = {r["dp_id"] for r in rows}
    assert len(rows) == 134 and len(dp_set) == 134, f"Expected 134 unique obs, got {len(rows)}/{len(dp_set)}"
    overlap_dp = dp_set & (set(prior_dp_ids) | set(format_probes))
    assert not overlap_dp, f"dp_id overlap detected: {overlap_dp}"

    phys_urls: dict[str, tuple[str, int]] = {}
    for r in rows:
        phys_urls[r["f1_rel"]] = (r["f1_url"], int(r["f1_bytes"]))
        for ex in json.loads(r["extra_files"]):
            phys_urls[ex["rel"]] = (ex["url"], int(ex["bytes"]))
    assert len(phys_urls) == 59, f"Expected 59 physical files, got {len(phys_urls)}"
    for rel in phys_urls:
        bn = rel.rsplit("/", 1)[-1]
        assert bn not in set(format_probes), f"Format check probe leaked into cohort: {bn}"

    brand_new_stars = sorted({r["canonical_target"] for r in rows if r["is_prior_bridge"] == "False"})
    bridge_stars = sorted({r["canonical_target"] for r in rows if r["is_prior_bridge"] == "True"})
    assert len(brand_new_stars) == 52, f"Expected 52 brand-new stars, got {len(brand_new_stars)}"

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
            assert sp >= 120.0, f"Intra-D107 overlap {s1}/{s2}: {sp:.2f}'' < 120''"

    # Live HTTP 200 verification across all 59 unique physical upstream URLs
    non_eso_checks = sorted((rel, u, sz) for rel, (u, sz) in phys_urls.items() if "dataportal.eso.org" not in u)
    eso_checks = sorted((rel, u, sz) for rel, (u, sz) in phys_urls.items() if "dataportal.eso.org" in u)
    print(f"Verifying HTTP 200 on {len(non_eso_checks)} IceCube/Swift + {len(eso_checks)} ESO URLs (59 physical files)...", flush=True)
    head_res = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for res in ex.map(lambda it: (it[0], it[1], *_http_head(it[1]), it[2]), non_eso_checks):
            head_res.append(res)
    with ThreadPoolExecutor(max_workers=2) as ex:
        for idx, res in enumerate(ex.map(lambda it: (it[0], it[1], *_http_head(it[1]), it[2]), eso_checks), 1):
            head_res.append(res)
            if idx % 10 == 0 or idx == len(eso_checks):
                print(f"  verified {idx}/{len(eso_checks)} ESO URLs...", flush=True)
    for rel, u, st, b, exp_b in head_res:
        assert st == 200, f"HEAD/Range failed {rel} ({u}): HTTP {st}"
        if exp_b > 0 and b > 0:
            assert b == exp_b, f"HEAD/Range bytes mismatch {rel}: got {b}, expected {exp_b}"
    print("All 59 upstream HTTP 200 checks passed.")

    with open(WS / "FROZEN_COHORT_D107.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COHORT_COLS)
        w.writeheader()
        w.writerows(rows)

    tot_bytes = sum(sz for _, (_, sz) in phys_urls.items() if sz > 0)
    n_new_10pc = sum(1 for s in brand_new_stars if NEW_META[s]["d"] < 10.0)
    assert n_new_10pc == 18, f"Expected +18 new <10 pc stars (244 -> 262), got {n_new_10pc}"

    now_utc = datetime.now(timezone.utc)
    locked_utc = now_utc.isoformat()
    locked_epoch = now_utc.timestamp()

    pe_out = {
        "schema": "D107_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D107",
        "verified_utc": locked_utc,
        "prior_phases_covered": "C001-C037 + D001-D106",
        "n_prior_excluded_coords": len(prior_coords),
        "n_prior_excluded_dp_ids": len(prior_dp_ids),
        "n_format_check_excluded_dp_ids": len(format_probes),
        "d107_total_stars": len(brand_new_stars) + len(bridge_stars),
        "d107_brand_new_unique_stars": len(brand_new_stars),
        "d107_prior_bridge_stars": len(bridge_stars),
        "d107_control_stars": sum(1 for s in brand_new_stars if NEW_META[s]["role"] == "CONTROL") + sum(1 for s in bridge_stars if u_map[s]["role"] == "CONTROL"),
        "d107_brand_new_within_10pc": n_new_10pc,
        "d107_total_observations": len(rows),
        "d107_total_physical_files": len(phys_urls),
        "d107_projected_download_bytes": tot_bytes,
        "d107_projected_download_mib": round(tot_bytes / (1024.0 * 1024.0), 3),
        "d107_dp_id_overlap_count": 0,
        "min_brand_new_sky_separation_arcsec": round(min_prior_sep, 2),
        "min_intra_d107_separation_arcsec": round(min_intra_sep, 2),
        "star_separation_verification": sep_verif,
        "format_check_excluded_dp_ids": format_probes,
        "excluded_dp_ids": prior_dp_ids,
        "excluded_targets_coordinate_registry": prior_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pe_out, indent=2) + "\n", encoding="utf-8")

    uni106 = s106["unified_852star_panchromatic_v6_4_synthesis"]
    snap_out = {
        "schema": "D107_PRIOR_V6_4_PHASES_SNAPSHOT",
        "prior_phases": "C001-C037 + D001-D106",
        "source_archive_af_name": ARCHIVE_AF.name,
        "source_archive_af_sha256": ARCHIVE_AF_SHA256,
        "source_archive_af_bundle_member": "work_v6_4_20261124_d106_vhe_tev_gamma_hess_magic_veritas_hawc_60octave/bounded_inputs/d106_bounded_bundle.json.gz",
        "source_archive_af_bundle_sha256": BUNDLE_106_SHA256,
        "prior_unique_stars_count": len(u852_rows),
        "prior_science_stars_count": int(uni106["science_stars_total"]),
        "prior_control_stars_count": int(uni106["control_stars_total"]),
        "prior_planet_host_stars_count": int(uni106["planet_host_stars_total"]),
        "prior_confirmed_exoplanets_count": int(uni106["confirmed_exoplanets_total"]),
        "prior_within_10pc_count": int(uni106["within_10pc_unique_stars"]),
        "prior_total_exposures_count": int(uni106["total_exposures_d079_d106"]),
        "prior_cumulative_integration_hours": float(uni106["total_integration_hours_d079_d106"]),
        "prior_calibration_trials_count": int(uni106["total_calibration_trials_d079_d106"]),
        "prior_v2_false_alarms_eliminated_total": int(uni106["v2_false_alarms_eliminated_total"]),
        "prior_cumulative_orbital_campaigns_count": int(uni106["cumulative_orbital_campaigns"]),
        "prior_panchromatic_bridge_stars_count": int(uni106["panchromatic_bridge_stars_total"]),
        "prior_revisited_control_multi_phase_stars": int(uni106["revisited_control_multi_phase_stars"]),
        "prior_multi_phase_targets_total": int(uni106["multi_phase_targets_total"]),
        "prior_panchromatic_bridge_cells_count": int(uni106["panchromatic_bridge_cells_total"]),
        "prior_cumulative_comb_stacks": int(uni106["cumulative_comb_stacks"]),
        "prior_coherent_eccentric_keplerian_campaigns": int(uni106["coherent_eccentric_keplerian_campaigns"]),
        "d106_summary_headline": uni106,
        "prior_unified_852_rows": u852_rows,
        "prior_bridge_119_rows": br1665_rows,
        "prior_allsky_comb_unified_rows": comb_u564_rows,
        "prior_allsky_comb_candidate_rows": comb_c_rows,
        "prior_ellipsoid_852_rows": ell852_rows,
    }
    (WS / "PRIOR_V6_4_PHASES_SNAPSHOT.json").write_text(json.dumps(snap_out, indent=2) + "\n", encoding="utf-8")

    orb_out = {
        "schema": "D107_ORBITAL_CAMPAIGNS_AND_KINEMATICS",
        "phase_id": "D107",
        "campaign_range": [187, 192],
        "campaigns": orbital_campaigns,
    }
    (WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").write_text(json.dumps(orb_out, indent=2) + "\n", encoding="utf-8")

    stage1_names = [
        "v6_5_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D107.csv",
        "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "PRIOR_V6_4_PHASES_SNAPSHOT.json",
    ]
    stage1_hashes = {fn: _sha256_file(WS / fn) for fn in stage1_names}

    ml = {
        "schema": "D107_PROSPECTIVE_METHOD_LOCK",
        "phase_id": "D107",
        "detector_version": "V6.5",
        "detector": det.DETECTOR_NAME,
        "locked_utc": locked_utc,
        "projected_unified_stars": 852 + len(brand_new_stars),
        "projected_within_10pc_stars": 244 + n_new_10pc,
        "d107_brand_new_stars": len(brand_new_stars),
        "d107_prior_bridges": len(bridge_stars),
        "d107_total_observations": len(rows),
        "d107_total_physical_files": len(phys_urls),
        "d107_projected_bytes": tot_bytes,
        "d107_projected_mib": round(tot_bytes / (1024.0 * 1024.0), 3),
        "stage_1_files": stage1_hashes,
    }
    (WS / "METHOD_LOCK.json").write_text(json.dumps(ml, indent=2) + "\n", encoding="utf-8")
    ml_sha = _sha256_file(WS / "METHOD_LOCK.json")

    lr = {
        "schema": "D107_LOCK_RECEIPT",
        "phase_id": "D107",
        "status": "STAGE-1 SEALED",
        "locked_utc": locked_utc,
        "locked_unix_epoch": round(locked_epoch, 4),
        "method_lock_sha256": ml_sha,
        "inputs_dir_exists_at_seal": RAW_DIR.exists(),
        "locked_files": stage1_hashes,
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lr, indent=2) + "\n", encoding="utf-8")
    print(f"STAGE-1 SEALED: obs={len(rows)}, files={len(phys_urls)}, brand_new={len(brand_new_stars)} (+{n_new_10pc} <10pc -> {244+n_new_10pc}), prior_bridges={len(bridge_stars)}, unified={852+len(brand_new_stars)}, min_prior_sep={min_prior_sep:.1f}'', min_intra_sep={min_intra_sep:.1f}'', raw_dir_exists={RAW_DIR.exists()}, proj_mib={ml['d107_projected_mib']}")


if __name__ == "__main__":
    main()
