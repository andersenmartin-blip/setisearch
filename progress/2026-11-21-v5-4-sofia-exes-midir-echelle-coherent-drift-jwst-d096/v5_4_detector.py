#!/usr/bin/env python3
"""
Phase D096 Detector Module: `TECHNOSIGNATURE_V5_4_SOFIA_EXES_MIDIR_ECHELLE_COHERENT_DRIFT_AND_JWST_NIRISS`

Prospectively locked V5.4 stratospheric high-res mid-IR echelle, coherent sub-threshold
shift-and-stack multi-epoch drift, and space optical-to-NIR technosignature detector suite:
  - `SOFIA_EXES_STRATOSPHERIC_V54`: Stratospheric R = 50,000-200,000 mid-IR echelle search
    with ATRAN telluric gate (`G2_EXES_ATRAN`), RP-matched LSF + CR/broad-band veto, cross-star
    topocentric `G6_EXES` veto, mid-IR fine-structure/molecular line atlas, and direct Jy CGS bounds.
  - `DRIFT_V54_COHERENT_SHIFT_STACK`: Full 2D `(N_epochs, N_wave)` coherent matched-filter
    shift-and-stack integrator over linear, quadratic curved, and periodic/Keplerian orbits,
    recovering sub-threshold `2.8-3.8 sigma/epoch` beacons via sqrt(N) gain with Leave-One-Out
    jackknife persistence, stationary veto, and BERV-sky topocentric alignment veto.
  - `JWST_NIRISS_SOSS` & `JWST_NIRSPEC_G140H`: Zero-telluric space optical-to-NIR search
    spanning `1064/1310/1550 nm` laser windows anchored to 2MASS H / Gaia G Planck CGS.
"""
from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np
from scipy.ndimage import convolve1d, median_filter

DETECTOR_NAME = "TECHNOSIGNATURE_V5_4_SOFIA_EXES_MIDIR_ECHELLE_COHERENT_DRIFT_AND_JWST_NIRISS"

# Exact physical constants (SI / CGS / IAU)
C_KMS = 299792.458
C_SI = 299792458.0
C_ANGSTROM_GHZ = 2.99792458e9
H_PLANCK = 6.62607015e-34
K_BOLTZ = 1.380649e-23
PC_CM = 3.085677581491367e18
G_SI = 6.67430e-11
M_SUN_KG = 1.98847e30
DAY_S = 86400.0
AU_M = 149597870700.0
SOLAR_RADIUS_CM = 6.957e10
FWHM_FACTOR = 2.0 * math.sqrt(2.0 * math.log(2.0))
MAD_NORM = 1.482602218505602

# Gaia G Vega zero-point flux density (lambda_eff = 6217.59 A, erg s^-1 cm^-2 A^-1)
GAIA_G_EFF_WAVE_A = 6217.59
GAIA_G_FLAM0_CGS = 2.500e-9

# 2MASS H Vega zero-point flux density (Cohen, Wheaton & Megeath 2003, lambda_eff = 16620 A)
TWOMASS_H_EFF_WAVE_A = 16620.0
TWOMASS_H_FLAM0_CGS = 1.133e-10

# Prominent APOGEE/H-band OH Meinel sky-emission vacuum wavelengths (Rousselot et al. 2000; A)
ROUSSELOT_OH_HBAND_VAC_A: tuple[float, ...] = (
    15055.4, 15088.2, 15187.1, 15241.0, 15287.8, 15332.4, 15395.3, 15432.1,
    15462.2, 15509.7, 15540.3, 15597.7, 15654.9, 15702.5, 15760.3, 15830.2,
    15869.5, 15972.6, 16030.8, 16079.7, 16128.6, 16194.7, 16235.4, 16317.2,
    16351.3, 16388.5, 16442.2, 16502.4, 16553.8, 16610.6, 16692.4, 16708.9,
    16732.7, 16840.5, 16903.7, 16955.1,
)

# X-shooter NIR telluric water-vapor opaque absorption blackout windows (A)
XSHOOTER_TELLURIC_BLACKOUT_A: list[tuple[float, float]] = [
    (13450.0, 14500.0),
    (18000.0, 19450.0),
]

# ---------------------------------------------------------------------------
# Gate G2_V42: Paranal / La Silla Sky Airglow & Telluric Lines (A)
# ---------------------------------------------------------------------------

GROUND_AIRGLOW_AND_TELLURIC_A: list[dict[str, Any]] = [
    {"name": "OI_5577", "wave_A": 5577.34, "half_width_kms": 55.0},
    {"name": "NaI_D2_5890", "wave_A": 5889.95, "half_width_kms": 45.0},
    {"name": "NaI_D1_5896", "wave_A": 5895.92, "half_width_kms": 45.0},
    {"name": "OI_6300", "wave_A": 6300.30, "half_width_kms": 55.0},
    {"name": "OI_6364", "wave_A": 6363.78, "half_width_kms": 55.0},
    {"name": "O2_B_6870", "wave_A": 6875.00, "half_width_kms": 450.0},
    {"name": "OH_7276", "wave_A": 7276.40, "half_width_kms": 55.0},
    {"name": "OH_7316", "wave_A": 7316.28, "half_width_kms": 55.0},
    {"name": "OH_7341", "wave_A": 7340.89, "half_width_kms": 55.0},
    {"name": "O2_A_7605", "wave_A": 7606.00, "half_width_kms": 650.0},
    {"name": "OH_7751", "wave_A": 7750.64, "half_width_kms": 55.0},
    {"name": "OH_7913", "wave_A": 7913.71, "half_width_kms": 55.0},
    {"name": "OH_8344", "wave_A": 8344.60, "half_width_kms": 55.0},
    {"name": "O2_8645", "wave_A": 8645.00, "half_width_kms": 200.0},
    {"name": "OH_8827", "wave_A": 8827.10, "half_width_kms": 60.0},
    {"name": "OH_9376", "wave_A": 9375.96, "half_width_kms": 70.0},
    {"name": "OH_9872", "wave_A": 9872.10, "half_width_kms": 70.0},
    {"name": "OH_10832", "wave_A": 10832.10, "half_width_kms": 80.0},
    {"name": "OH_11438", "wave_A": 11438.00, "half_width_kms": 80.0},
    {"name": "O2_IR_12680", "wave_A": 12685.00, "half_width_kms": 350.0},
    {"name": "H2O_13950", "wave_A": 13975.00, "half_width_kms": 11500.0},
    {"name": "OH_15055", "wave_A": 15055.00, "half_width_kms": 80.0},
    {"name": "OH_15830", "wave_A": 15830.00, "half_width_kms": 80.0},
    {"name": "OH_16904", "wave_A": 16904.00, "half_width_kms": 80.0},
    {"name": "H2O_18725", "wave_A": 18725.00, "half_width_kms": 12000.0},
    {"name": "CO2_20080", "wave_A": 20080.00, "half_width_kms": 450.0},
    {"name": "OH_21240", "wave_A": 21240.00, "half_width_kms": 85.0},
]

# ---------------------------------------------------------------------------
# Gate G3_V42: Optical & NIR Stellar Chromospheric / Nebular Emission (A)
# ---------------------------------------------------------------------------

STELLAR_OPT_NIR_EMISSION_A: list[dict[str, Any]] = [
    {"name": "CaII_K_3934", "wave_A": 3934.78},
    {"name": "CaII_H_3969", "wave_A": 3969.59},
    {"name": "HI_Heps_3970", "wave_A": 3970.07},
    {"name": "HI_Hdelta_4102", "wave_A": 4102.89},
    {"name": "HI_Hgamma_4341", "wave_A": 4341.68},
    {"name": "HI_Hbeta_4862", "wave_A": 4862.68},
    {"name": "OIII_5007", "wave_A": 5008.24},
    {"name": "HeI_5876", "wave_A": 5877.25},
    {"name": "HI_Halpha_6564", "wave_A": 6564.61},
    {"name": "NII_6583", "wave_A": 6585.27},
    {"name": "SII_6716", "wave_A": 6718.29},
    {"name": "CaII_IRT1_8500", "wave_A": 8500.35},
    {"name": "CaII_IRT2_8544", "wave_A": 8544.44},
    {"name": "CaII_IRT3_8664", "wave_A": 8664.52},
    {"name": "HeI_10833", "wave_A": 10833.20},
    {"name": "HI_PaG_10941", "wave_A": 10941.10},
    {"name": "HI_PaB_12822", "wave_A": 12821.60},
    {"name": "FeII_16440", "wave_A": 16440.00},
    {"name": "HI_PaA_18756", "wave_A": 18756.13},
    {"name": "H2_1_0_S1_21218", "wave_A": 21218.30},
    {"name": "HI_BrG_21661", "wave_A": 21661.20},
]

# ---------------------------------------------------------------------------
# Optical / NIR Photospheric RV Anchors (A)
# ---------------------------------------------------------------------------

LOCKED_RV_ANCHORS_OPTICAL: list[dict[str, Any]] = [
    {"anchor_id": "CAII_K_3934", "species": "Ca II K", "lab_wave_A": 3934.78},
    {"anchor_id": "MGI_5173", "species": "Mg I b1", "lab_wave_A": 5174.13},
    {"anchor_id": "MGI_5184", "species": "Mg I b0", "lab_wave_A": 5185.05},
    {"anchor_id": "FEI_5270", "species": "Fe I 5270", "lab_wave_A": 5270.36},
    {"anchor_id": "FEI_5328", "species": "Fe I 5328", "lab_wave_A": 5328.04},
    {"anchor_id": "NAI_D2_5890", "species": "Na I D2", "lab_wave_A": 5891.58},
    {"anchor_id": "CAII_6162", "species": "Ca I 6162", "lab_wave_A": 6163.88},
    {"anchor_id": "HI_HA_6565", "species": "H-alpha", "lab_wave_A": 6564.61},
    {"anchor_id": "CAII_IRT2", "species": "Ca II IRT2", "lab_wave_A": 8544.44},
]

LOCKED_RV_ANCHORS_XSHOOTER: list[dict[str, Any]] = LOCKED_RV_ANCHORS_OPTICAL + [
    {"anchor_id": "NAI_8195", "species": "Na I 8195", "lab_wave_A": 8197.07},
    {"anchor_id": "HI_PAG_10941", "species": "H I Pa-g", "lab_wave_A": 10941.10},
    {"anchor_id": "HI_PAB_12822", "species": "H I Pa-b", "lab_wave_A": 12821.60},
    {"anchor_id": "FEI_15648", "species": "Fe I 15648", "lab_wave_A": 15652.87},
    {"anchor_id": "HI_BRG_21661", "species": "H I Br-g", "lab_wave_A": 21661.20},
]

LOCKED_RV_ANCHORS_APOGEE2: list[dict[str, Any]] = [
    {"anchor_id": "HI_BR18_15346", "species": "H I Br-18", "lab_wave_A": 15345.98},
    {"anchor_id": "FEI_15652", "species": "Fe I 15652", "lab_wave_A": 15652.87},
    {"anchor_id": "MGI_15745", "species": "Mg I 15745", "lab_wave_A": 15745.02},
    {"anchor_id": "SII_15892", "species": "Si I 15892", "lab_wave_A": 15892.77},
    {"anchor_id": "HI_BR13_16114", "species": "H I Br-13", "lab_wave_A": 16113.71},
    {"anchor_id": "FEI_16320", "species": "Fe I 16320", "lab_wave_A": 16320.77},
    {"anchor_id": "HI_BR11_16811", "species": "H I Br-11", "lab_wave_A": 16811.11},
]

# ---------------------------------------------------------------------------
# Calibration & Radiometric Upper-Limit Bands
# ---------------------------------------------------------------------------

CALIBRATION_BANDS_XSHOOTER = [
    {"band_id": "X1_3600", "center_wave_A": 3600.0},
    {"band_id": "X2_5450", "center_wave_A": 5450.0},
    {"band_id": "X3_6800", "center_wave_A": 6800.0},
    {"band_id": "X4_10070", "center_wave_A": 10070.0},
    {"band_id": "X5_15500", "center_wave_A": 15500.0},
    {"band_id": "X6_20970", "center_wave_A": 20970.0},
]

CALIBRATION_BANDS_FEROS = [
    {"band_id": "F1_4100", "center_wave_A": 4100.0},
    {"band_id": "F2_5320", "center_wave_A": 5320.0},
    {"band_id": "F3_6328", "center_wave_A": 6328.0},
    {"band_id": "F4_7800", "center_wave_A": 7800.0},
    {"band_id": "F5_8800", "center_wave_A": 8800.0},
]

CALIBRATION_BANDS_HARPS = [
    {"band_id": "H1_4100", "center_wave_A": 4100.0},
    {"band_id": "H2_5320", "center_wave_A": 5320.0},
    {"band_id": "H3_5800", "center_wave_A": 5800.0},
    {"band_id": "H4_6328", "center_wave_A": 6328.0},
    {"band_id": "H5_6750", "center_wave_A": 6750.0},
]

CALIBRATION_BANDS_UVES = [
    {"band_id": "U1_4100", "center_wave_A": 4100.0},
    {"band_id": "U2_5320", "center_wave_A": 5320.0},
    {"band_id": "U3_6800", "center_wave_A": 6800.0},
    {"band_id": "U4_7800", "center_wave_A": 7800.0},
    {"band_id": "U5_8800", "center_wave_A": 8800.0},
]

CALIBRATION_BANDS_CRIRES = [
    {"band_id": "C1_10070", "center_wave_A": 10070.0},
    {"band_id": "C2_10700", "center_wave_A": 10700.0},
    {"band_id": "C2J_12400", "center_wave_A": 12400.0},
    {"band_id": "C3_15500", "center_wave_A": 15500.0},
    {"band_id": "C3H_16800", "center_wave_A": 16800.0},
    {"band_id": "C4_20970", "center_wave_A": 20970.0},
]

CALIBRATION_BANDS_APOGEE2 = [
    {"band_id": "A1_15350", "center_wave_A": 15350.0},
    {"band_id": "A2_15700", "center_wave_A": 15700.0},
    {"band_id": "A3_16200", "center_wave_A": 16200.0},
    {"band_id": "A4_16750", "center_wave_A": 16750.0},
]

CALIBRATION_BANDS_MIRI_LRS = [
    {"band_id": "ML1_58000", "center_wave_A": 58000.0},
    {"band_id": "ML2_78000", "center_wave_A": 78000.0},
    {"band_id": "ML3_95000", "center_wave_A": 95000.0},
    {"band_id": "ML4_112000", "center_wave_A": 112000.0},
]

CALIBRATION_BANDS_GHOST = [
    {"band_id": "G1_4000", "center_wave_A": 4000.0},
    {"band_id": "G2_4800", "center_wave_A": 4800.0},
    {"band_id": "G3_5500", "center_wave_A": 5500.0},
    {"band_id": "G4_6500", "center_wave_A": 6500.0},
    {"band_id": "G5_7800", "center_wave_A": 7800.0},
    {"band_id": "G6_9200", "center_wave_A": 9200.0},
]

CALIBRATION_BANDS_SPITZER_IRS = [
    {"band_id": "S1_65000", "center_wave_A": 65000.0},
    {"band_id": "S2_106000", "center_wave_A": 106000.0},
    {"band_id": "S3_180000", "center_wave_A": 180000.0},
    {"band_id": "S4_260000", "center_wave_A": 260000.0},
    {"band_id": "S5_345000", "center_wave_A": 345000.0},
]

CALIBRATION_BANDS_SOFIA_EXES = [
    {"band_id": "EXES_6UM", "center_wave_A": 61000.0},
    {"band_id": "EXES_7UM", "center_wave_A": 71000.0},
    {"band_id": "EXES_8UM", "center_wave_A": 79000.0},
    {"band_id": "EXES_14UM", "center_wave_A": 139000.0},
    {"band_id": "EXES_18UM", "center_wave_A": 183000.0},
    {"band_id": "EXES_26UM", "center_wave_A": 260000.0},
]

CALIBRATION_BANDS_JWST_NIRISS_SOSS = [
    {"band_id": "SOSS_8500", "center_wave_A": 8500.0},
    {"band_id": "SOSS_10640_NDYAG", "center_wave_A": 10640.0},
    {"band_id": "SOSS_13100_TELECOM", "center_wave_A": 13100.0},
    {"band_id": "SOSS_15500_TELECOM", "center_wave_A": 15500.0},
    {"band_id": "SOSS_21500_KBAND", "center_wave_A": 21500.0},
]

CALIBRATION_BANDS_JWST_NIRSPEC_G140H = [
    {"band_id": "G140H_8500", "center_wave_A": 8500.0},
    {"band_id": "G140H_10640_NDYAG", "center_wave_A": 10640.0},
    {"band_id": "G140H_13100_TELECOM", "center_wave_A": 13100.0},
    {"band_id": "G140H_15500_TELECOM", "center_wave_A": 15500.0},
]

CALIBRATION_BANDS_GIRAFFE = [
    {"band_id": "G1_5250", "center_wave_A": 5250.0},
    {"band_id": "G2_5480", "center_wave_A": 5480.0},
    {"band_id": "G3_5715", "center_wave_A": 5715.0},
    {"band_id": "G4_6260", "center_wave_A": 6260.0},
]

GIRAFFE_EXTRA_BANDS = CALIBRATION_BANDS_GIRAFFE + [
    {"band_id": "G5_8750", "center_wave_A": 8750.0},
]

CALIBRATION_BANDS_GRACES = [
    {"band_id": "R1_4675", "center_wave_A": 4675.8},
    {"band_id": "R2_5320", "center_wave_A": 5320.5},
    {"band_id": "R3_6328", "center_wave_A": 6328.2},
    {"band_id": "R4_8521", "center_wave_A": 8521.1},
]

CALIBRATION_BANDS_CORALIE = [
    {"band_id": "L1_4100", "center_wave_A": 4100.0},
    {"band_id": "L2_5320", "center_wave_A": 5320.5},
    {"band_id": "L3_5800", "center_wave_A": 5800.0},
    {"band_id": "L4_6328", "center_wave_A": 6328.2},
]

CALIBRATION_BANDS_CARMENES_VIS = [
    {"band_id": "M1_5320", "center_wave_A": 5320.5},
    {"band_id": "M2_6328", "center_wave_A": 6328.2},
    {"band_id": "M3_8082", "center_wave_A": 8082.0},
    {"band_id": "M4_8800", "center_wave_A": 8800.0},
]

CALIBRATION_BANDS_ESPADONS = [
    {"band_id": "E1_4675", "center_wave_A": 4675.8},
    {"band_id": "E2_5320", "center_wave_A": 5320.5},
    {"band_id": "E3_6328", "center_wave_A": 6328.2},
    {"band_id": "E4_8521", "center_wave_A": 8521.1},
]

CALIBRATION_BANDS_SOPHIE = [
    {"band_id": "S1_4244", "center_wave_A": 4244.3},
    {"band_id": "S2_5320", "center_wave_A": 5320.5},
    {"band_id": "S3_6328", "center_wave_A": 6328.2},
]

CALIBRATION_BANDS_ELODIE = [
    {"band_id": "O1_4244", "center_wave_A": 4244.3},
    {"band_id": "O2_5320", "center_wave_A": 5320.5},
    {"band_id": "O3_6328", "center_wave_A": 6328.2},
]

CALIBRATION_BANDS_NIRSPEC = [
    {"band_id": "N1_33200", "center_wave_A": 33200.0},
    {"band_id": "N2_34400", "center_wave_A": 34400.0},
    {"band_id": "N3_45000", "center_wave_A": 45000.0},
    {"band_id": "N4_47250", "center_wave_A": 47250.0},
]

CALIBRATION_BANDS_MIRI = [
    {"band_id": "M1_78000", "center_wave_A": 78000.0},
    {"band_id": "M2_89600", "center_wave_A": 89600.0},
    {"band_id": "M3_105500", "center_wave_A": 105500.0},
    {"band_id": "M4_110200", "center_wave_A": 110200.0},
]

COMB_V4_1_WINDOWS_A: dict[str, list[dict[str, Any]]] = {
    "ESO_XSHOOTER_3ARM": [
        {"band": "XSH_UVB", "lo_a": 3200.0, "hi_a": 5300.0},
        {"band": "XSH_VIS", "lo_a": 5600.0, "hi_a": 9850.0},
        {"band": "XSH_NIR", "lo_a": 10250.0, "hi_a": 23500.0},
    ],
    "ESO_FEROS": [
        {"band": "FEROS_BLUE", "lo_a": 3800.0, "hi_a": 5800.0},
        {"band": "FEROS_RED", "lo_a": 6000.0, "hi_a": 9050.0},
    ],
    "ESO_HARPS": [
        {"band": "HARPS_BLUE", "lo_a": 3820.0, "hi_a": 5280.0},
        {"band": "HARPS_RED", "lo_a": 5380.0, "hi_a": 6840.0},
    ],
    "ESO_UVES": [
        {"band": "UVES_BLUE", "lo_a": 3800.0, "hi_a": 4980.0},
        {"band": "UVES_REDL", "lo_a": 5800.0, "hi_a": 7400.0},
        {"band": "UVES_REDU", "lo_a": 7700.0, "hi_a": 9800.0},
    ],
    "ESO_CRIRES": [
        {"band": "CRIRES_Y", "lo_a": 9550.0, "hi_a": 11150.0},
        {"band": "CRIRES_J", "lo_a": 11500.0, "hi_a": 13350.0},
        {"band": "CRIRES_H", "lo_a": 14800.0, "hi_a": 17800.0},
        {"band": "CRIRES_K", "lo_a": 19600.0, "hi_a": 24500.0},
    ],
    "ESO_GIRAFFE_HR": [
        {"band": "GIRAFFE_HR09B", "lo_a": 5145.0, "hi_a": 5350.0},
        {"band": "GIRAFFE_HR10", "lo_a": 5340.0, "hi_a": 5610.0},
        {"band": "GIRAFFE_HR11", "lo_a": 5600.0, "hi_a": 5830.0},
        {"band": "GIRAFFE_HR13", "lo_a": 6120.0, "hi_a": 6395.0},
        {"band": "GIRAFFE_HR21", "lo_a": 8490.0, "hi_a": 8985.0},
    ],
    "GEMINI_GRACES": [
        {"band": "GRACES_OPT", "lo_a": 5150.0, "hi_a": 5550.0},
        {"band": "GRACES_RED", "lo_a": 6050.0, "hi_a": 6450.0},
        {"band": "GRACES_FARRED", "lo_a": 8550.0, "hi_a": 8850.0},
    ],
    "ESO_CORALIE": [
        {"band": "CORALIE_BLUE", "lo_a": 4050.0, "hi_a": 5450.0},
        {"band": "CORALIE_RED", "lo_a": 5650.0, "hi_a": 6840.0},
    ],
    "CARMENES_VIS": [
        {"band": "CARM_GREEN", "lo_a": 5400.0, "hi_a": 5860.0},
        {"band": "CARM_RED", "lo_a": 5940.0, "hi_a": 6840.0},
        {"band": "CARM_FARRED", "lo_a": 7860.0, "hi_a": 8850.0},
    ],
    "CFHT_ESPADONS": [
        {"band": "ESPADONS_OPT", "lo_a": 5150.0, "hi_a": 5550.0},
        {"band": "ESPADONS_FARRED", "lo_a": 8550.0, "hi_a": 8820.0},
    ],
    "OHP_SOPHIE": [
        {"band": "SOPHIE_BLUE", "lo_a": 4450.0, "hi_a": 4750.0},
        {"band": "SOPHIE_RED", "lo_a": 6050.0, "hi_a": 6450.0},
    ],
    "OHP_ELODIE": [
        {"band": "ELODIE_BLUE", "lo_a": 4450.0, "hi_a": 4750.0},
        {"band": "ELODIE_RED", "lo_a": 6050.0, "hi_a": 6450.0},
    ],
    "SDSS_APOGEE2": [
        {"band": "APOGEE_BLUE_CHIP", "lo_a": 15155.0, "hi_a": 15795.0},
        {"band": "APOGEE_GREEN_CHIP", "lo_a": 15870.0, "hi_a": 16420.0},
        {"band": "APOGEE_RED_CHIP", "lo_a": 16490.0, "hi_a": 16945.0},
    ],
    "GEMINI_GHOST": [
        {"band": "GHOST_BLUE", "lo_a": 3600.0, "hi_a": 5250.0},
        {"band": "GHOST_RED_VIS", "lo_a": 5450.0, "hi_a": 7400.0},
        {"band": "GHOST_RED_NIR", "lo_a": 7650.0, "hi_a": 9800.0},
    ],
}

# ---------------------------------------------------------------------------
# Prospectively Locked Detector Configuration
# ---------------------------------------------------------------------------

BASE_V4_2_CONFIG: dict[str, Any] = {
    "detector_name": DETECTOR_NAME,
    "instrument": "ESO_FEROS",
    "resolving_power": 48000.0,
    "sigma_v_kms": C_KMS / (48000.0 * FWHM_FACTOR),
    "wave_range_a": (3527.0, 9216.0),
    "coadd_rest_min_angstrom": 3527.0,
    "coadd_rest_max_angstrom": 9216.0,
    "coadd_step_angstrom": 0.03,
    "radiometric_anchor": "GAIA_G_PLANCK_CGS",
    # Step 1: Optical/NIR RV anchors
    "rv_anchor_window_kms": 280.0,
    "rv_anchor_fwhm_kms": 16.0,
    "rv_anchor_scan_half_kms": 150.0,
    "rv_anchor_scan_step_kms": 1.0,
    "rv_anchor_min_snr": 3.8,
    # Step 2: Continuum & overlap-aware KNN
    "continuum_block_bins": 60,
    "continuum_median_blocks": 5,
    "continuum_quantile": 0.72,
    "continuum_quantile_blue": 0.75,
    "continuum_blue_cutoff_angstrom": 4500.0,
    "knn_atlas_neighbors": 4,
    "knn_teff_scale_k": 1500.0,
    "knn_mh_scale_dex": 0.50,
    "knn_min_wave_overlap_frac": 0.55,
    # Step 3: Matched LSF scan (annuli in velocity sigma units)
    "fit_phases_bins": [-0.35, -0.15, 0.0, 0.15, 0.35],
    "core_sigma_mult": 2.8,
    "mid_inner_sigma_mult": 4.0,
    "mid_outer_sigma_mult": 16.0,
    "outer_inner_sigma_mult": 6.0,
    "outer_outer_sigma_mult": 22.0,
    "supraphotospheric_min_fn_pk3": 1.01,
    "scan_seed_sigma_mult": 4.2,
    "scan_nms_min_sep_bins": 18,
    "channel_t_snr_mid_min": 6.5,
    "channel_t_snr_outer_min": 6.0,
    "channel_t_amp_ratio_min": 0.70,
    "channel_t_amp_ratio_max": 1.45,
    "channel_t_cosine_min": 0.78,
    "channel_t_fwhm_ratio_min": 0.50,
    "channel_t_fwhm_ratio_max": 1.65,
    "channel_p_snr_mid_min": 6.5,
    "channel_p_snr_outer_min": 6.0,
    "channel_p_amp_ratio_min": 0.70,
    "channel_p_amp_ratio_max": 1.45,
    "channel_p_cosine_min": 0.78,
    "channel_p_fwhm_ratio_min": 0.50,
    "channel_p_fwhm_ratio_max": 1.65,
    "channel_tdiff_snr_mid_min": 6.0,
    "channel_tdiff_snr_outer_min": 5.5,
    "channel_tdiff_amp_ratio_min": 0.70,
    "channel_tdiff_amp_ratio_max": 1.45,
    "channel_tdiff_cosine_min": 0.75,
    "channel_tdiff_fwhm_ratio_min": 0.50,
    "channel_tdiff_fwhm_ratio_max": 1.65,
    "channel_tdiff_min_in_exp_snr": 3.5,
    "channel_tdiff_min_in_exp_fraction": 0.50,
    "channel_kplanet_snr_mid_min": 6.0,
    "channel_kplanet_snr_outer_min": 5.5,
    "channel_kplanet_amp_ratio_min": 0.70,
    "channel_kplanet_amp_ratio_max": 1.45,
    "channel_kplanet_cosine_min": 0.75,
    "channel_kplanet_fwhm_ratio_min": 0.50,
    "channel_kplanet_fwhm_ratio_max": 1.65,
    "channel_kplanet_min_in_exp_snr": 3.5,
    "channel_kplanet_min_in_exp_fraction": 0.50,
    # Step 4: V4.2 Physics Vetting Gates (G2_V42, G3_V42, G4_V42, G5, G6)
    "g4_min_continuum_snr": 1.2,
    "g4_max_template_dip_frac": 0.35,
    "xshooter_dual_min_snr": 4.0,
    "g5_min_native_snr": 4.0,
    "g5_eta_1px_max": 0.74,
    "g5_min_wing_ratio": 0.14,
    "g5_ipc_hotpx_ratio_max": 2.20,
    "g5_far_wing_34_max": 0.42,
    "g5_cos_1d_11px_min": 0.72,
    "g6_topo_tol_kms": 6.0,
    "g6_px_tol": 1.0,
    "g6_min_berv_shift_kms": 4.0,
    "g6_min_diff_stars": 2,
    # Step 5: COMB_V4_1
    "comb_spacings_ghz": [25.0, 40.0, 65.0, 100.0],
    "comb_step_ghz": 2.5,
    "comb_n_teeth": 6,
    "comb_tooth_snr_min": 2.2,
    "comb_sum_snr_min": 20.5,
    "comb_min_qualifying_teeth": 5,
    "comb_max_off_tooth_crowding": 0.38,
    "comb_min_intertooth_ratio": 1.85,
    "comb_min_topo_anti_ratio": 1.08,
    "comb_min_fn_pk3": 1.005,
    "comb_search_bands": ["FEROS_BLUE", "FEROS_RED"],
    # V5.0 Unsupervised RPCA + Rarity + Agnostic + MIRI Greenhouse CCF
    "rpca_block_len": 2048,
    "rpca_overlap": 128,
    "rpca_loso_rank": 8,
    "g7_min_z_rpca": 6.0,
    "g7_min_rarity_score": 0.65,
    "agnostic_scales_lsf": (2.0, 4.0, 8.0, 14.0),
    "agnostic_min_abs_z": 7.5,
    "agnostic_min_rarity_score": 0.70,
    "miri_ccf_min_sigma": 5.0,
    "miri_ccf_min_confounder_ratio": 1.5,
    "drift_v51_n_offsets": 41,
    "drift_v51_min_abs_dv_kms": 5.0,
    "drift_v51_max_abs_dv_kms": 250.0,
    "drift_v51_stat_veto_dv_kms": 3.0,
    "drift_v51_stat_max_z": 4.0,
    "drift_v51_epoch_min_z": 5.0,
    "drift_v51_comb_min_z": 7.5,
    "g8_patch_half_px": 8,
    "g8_pca_dim": 8,
    "g8_knn_k": 7,
    "g8_min_novelty_z": 3.5,
    "nirspec_edge_trim_um": 0.06,
    "nirspec_ccf_min_sigma": 5.0,
    "nirspec_ccf_min_confounder_ratio": 1.5,
    # V5.2 Multi-epoch N>=3 drift chaining & MIRI LRS broadband CCF
    "drift_v52_min_abs_dv_kms": 3.0,
    "drift_v52_max_abs_dv_kms": 250.0,
    "drift_v52_epoch_min_z": 4.5,
    "drift_v52_chain_min_z": 8.0,
    "drift_v52_stat_veto_dv_kms": 3.0,
    "drift_v52_stat_max_z": 4.0,
    "drift_v52_min_matched_epochs": 3,
    "drift_v52_min_dt_days": 0.01,
    "miri_lrs_ccf_min_sigma": 5.0,
    "miri_lrs_ccf_min_confounder_ratio": 1.5,
    "miri_lrs_min_core_bins": 4,
    "miri_lrs_min_sb_bins": 6,
    # V5.3 Curved + Periodic Multi-Epoch Drift, GHOST Sky-Fiber Veto, Spitzer IRS CCF & Dyson
    "drift_v53_curved_min_epochs": 4,
    "drift_v53_periodic_min_epochs": 6,
    "drift_v53_epoch_min_z": 4.2,
    "drift_v53_chain_min_z": 8.0,
    "drift_v53_min_dt_days": 0.01,
    "drift_v53_periodic_min_baseline_days": 2.0,
    "drift_v53_periodic_min_p_days": 0.5,
    "drift_v53_periodic_max_p_days": 100.0,
    "drift_v53_periodic_min_k_kms": 10.0,
    "drift_v53_periodic_max_k_kms": 220.0,
    "ghost_sky_fiber_max_z": 3.0,
    "spitzer_irs_ccf_min_sigma": 5.0,
    "spitzer_irs_ccf_min_confounder_ratio": 1.5,
    "spitzer_irs_ccf_min_margin_sigma": 2.0,
    "dyson_waste_min_gamma": 0.01,
    "dyson_waste_min_r2": 0.90,
    "dyson_waste_min_snr": 6.0,
    "dyson_waste_max_silicate_sigma": 3.0,
    # V5.4 SOFIA EXES, Coherent Shift-Stack Drift, & JWST NIRISS SOSS / NIRSpec G140H
    "exes_min_atran": 0.70,
    "exes_min_atran_15kms": 0.40,
    "exes_max_atran_grad_kms": 0.08,
    "exes_min_z_seed": 5.5,
    "exes_min_snr_mid": 6.5,
    "exes_min_snr_outer": 6.0,
    "exes_eta_1px_min": 0.22,
    "exes_far_wing_max": 0.52,
    "exes_g6_topo_tol_kms": 15.0,
    "drift_v54_min_epochs": 4,
    "drift_v54_min_snr_stack": 7.5,
    "drift_v54_min_snr_loo": 5.2,
    "drift_v54_max_single_epoch_frac": 0.45,
    "drift_v54_min_pos_frac": 0.60,
    "drift_v54_min_dv_span_kms": 12.0,
    "drift_v54_stat_margin_sigma": 2.2,
    "drift_v54_sky_margin_sigma": 1.5,
    "drift_v54_max_masked_frac": 0.30,
    "jwst_soss_min_z_seed": 5.5,
    "jwst_soss_min_snr_mid": 6.5,
    "jwst_soss_min_snr_outer": 6.0,
}

BASE_V5_0_CONFIG = BASE_V4_2_CONFIG
BASE_V5_1_CONFIG = BASE_V4_2_CONFIG
BASE_V5_2_CONFIG = BASE_V4_2_CONFIG
BASE_V5_3_CONFIG = BASE_V4_2_CONFIG
BASE_V5_4_CONFIG = BASE_V4_2_CONFIG


def effective_resolving_power(cfg: dict[str, Any], wave_a: float) -> float:
    """Return local resolving power R(lambda); captures X-shooter UVB/VIS/NIR arms."""
    if cfg.get("instrument") == "ESO_XSHOOTER_3ARM" and math.isfinite(float(wave_a)) and float(wave_a) > 0.0:
        wa = float(wave_a)
        if wa < 5350.0:
            return 9860.0
        if wa <= 10050.0:
            return 18340.0
        return 11420.0
    if cfg.get("instrument") == "ESO_GIRAFFE_HR" and math.isfinite(float(wave_a)) and float(wave_a) > 0.0:
        wa = float(wave_a)
        if wa >= 8400.0:
            return 18000.0
        if wa >= 6050.0:
            return 24000.0
        if wa >= 5580.0:
            return 27000.0
        if wa >= 5340.0:
            return 20000.0
        return 29000.0
    return float(cfg.get("resolving_power", 48000.0))


def _scan_margin_bins(wave_a: float, cfg: dict[str, Any], min_bins: int = 45, max_bins: int = 340) -> int:
    step_a = float(cfg["coadd_step_angstrom"])
    r_eff = effective_resolving_power(cfg, wave_a)
    sig_a = float(wave_a) / (r_eff * FWHM_FACTOR)
    m = int(math.ceil(15.0 * sig_a / max(1e-6, step_a)))
    return int(max(min_bins, min(max_bins, m)))


def get_inst_config(instrument: str, resolving_power: float | None = None) -> dict[str, Any]:
    cfg = dict(BASE_V5_0_CONFIG)
    cfg["instrument"] = instrument
    if instrument == "ESO_XSHOOTER_3ARM":
        r_val = float(resolving_power) if resolving_power is not None else 18340.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (2989.0, 24790.0),
            "coadd_rest_min_angstrom": 2990.0,
            "coadd_rest_max_angstrom": 24780.0,
            "coadd_step_angstrom": 0.25,
            "rv_anchor_fwhm_kms": 22.0,
            "scan_nms_min_sep_bins": 16,
            "radiometric_anchor": "ESO_XSHOOTER_DIRECT_CGS",
            "rv_anchors": LOCKED_RV_ANCHORS_XSHOOTER,
            "comb_spacings_ghz": [40.0, 60.0, 90.0, 130.0],
            "comb_step_ghz": 4.0,
            "comb_search_bands": ["XSH_UVB", "XSH_VIS", "XSH_NIR"],
            "g6_topo_tol_kms": 12.0,
        })
    elif instrument == "ESO_GIRAFFE_HR":
        r_val = float(resolving_power) if resolving_power is not None else 26000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (5139.0, 8994.0),
            "coadd_rest_min_angstrom": 5139.0,
            "coadd_rest_max_angstrom": 8994.0,
            "coadd_step_angstrom": 0.05,
            "rv_anchor_fwhm_kms": 14.0,
            "scan_nms_min_sep_bins": 18,
            "radiometric_anchor": "GAIA_G_PLANCK_CGS",
            "rv_anchors": LOCKED_RV_ANCHORS_OPTICAL,
            "comb_spacings_ghz": [30.0, 50.0, 80.0, 120.0],
            "comb_step_ghz": 3.0,
            "comb_search_bands": ["GIRAFFE_HR09B", "GIRAFFE_HR10", "GIRAFFE_HR11", "GIRAFFE_HR13", "GIRAFFE_HR21"],
            "g6_topo_tol_kms": 8.0,
        })
    elif instrument == "ESO_HARPS":
        r_val = float(resolving_power) if resolving_power is not None else 115000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (3780.0, 6915.0),
            "coadd_rest_min_angstrom": 3780.0,
            "coadd_rest_max_angstrom": 6915.0,
            "coadd_step_angstrom": 0.02,
            "rv_anchor_fwhm_kms": 8.0,
            "scan_nms_min_sep_bins": 22,
            "radiometric_anchor": "GAIA_G_PLANCK_CGS",
            "rv_anchors": LOCKED_RV_ANCHORS_OPTICAL,
            "comb_spacings_ghz": [25.0, 40.0, 65.0, 100.0],
            "comb_step_ghz": 2.5,
            "comb_search_bands": ["HARPS_BLUE", "HARPS_RED"],
            "g6_topo_tol_kms": 4.0,
        })
    elif instrument == "ESO_UVES":
        r_val = float(resolving_power) if resolving_power is not None else 51690.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (3280.0, 10260.0),
            "coadd_rest_min_angstrom": 3280.0,
            "coadd_rest_max_angstrom": 10260.0,
            "coadd_step_angstrom": 0.03,
            "rv_anchor_fwhm_kms": 10.0,
            "scan_nms_min_sep_bins": 20,
            "radiometric_anchor": "GAIA_G_PLANCK_CGS",
            "rv_anchors": LOCKED_RV_ANCHORS_XSHOOTER,
            "comb_spacings_ghz": [25.0, 40.0, 65.0, 100.0],
            "comb_step_ghz": 2.5,
            "comb_search_bands": ["UVES_BLUE", "UVES_REDL", "UVES_REDU"],
            "g6_topo_tol_kms": 6.0,
        })
    elif instrument == "ESO_CRIRES":
        r_val = float(resolving_power) if resolving_power is not None else 86000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (9450.0, 25000.0),
            "coadd_rest_min_angstrom": 9450.0,
            "coadd_rest_max_angstrom": 25000.0,
            "coadd_step_angstrom": 0.05,
            "rv_anchor_fwhm_kms": 10.0,
            "scan_nms_min_sep_bins": 20,
            "radiometric_anchor": "GAIA_G_PLANCK_CGS",
            "rv_anchors": LOCKED_RV_ANCHORS_XSHOOTER,
            "comb_spacings_ghz": [25.0, 40.0, 65.0, 100.0],
            "comb_step_ghz": 2.5,
            "comb_search_bands": ["CRIRES_Y", "CRIRES_J", "CRIRES_H", "CRIRES_K"],
            "g6_topo_tol_kms": 5.0,
        })
    elif instrument == "GEMINI_GRACES":
        r_val = float(resolving_power) if resolving_power is not None else 67500.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (4000.0, 10000.0),
            "coadd_rest_min_angstrom": 4000.0,
            "coadd_rest_max_angstrom": 10000.0,
            "coadd_step_angstrom": 0.03,
            "rv_anchor_fwhm_kms": 10.0,
            "scan_nms_min_sep_bins": 20,
            "radiometric_anchor": "GAIA_G_PLANCK_CGS",
            "rv_anchors": LOCKED_RV_ANCHORS_OPTICAL,
            "comb_spacings_ghz": [25.0, 40.0, 65.0, 100.0],
            "comb_step_ghz": 2.5,
            "comb_search_bands": ["GRACES_OPT", "GRACES_RED", "GRACES_FARRED"],
            "g6_topo_tol_kms": 5.0,
        })
    elif instrument == "ESO_CORALIE":
        r_val = float(resolving_power) if resolving_power is not None else 60000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (3860.0, 6905.0),
            "coadd_rest_min_angstrom": 3860.0,
            "coadd_rest_max_angstrom": 6905.0,
            "coadd_step_angstrom": 0.025,
            "rv_anchor_fwhm_kms": 10.0,
            "scan_nms_min_sep_bins": 20,
            "radiometric_anchor": "GAIA_G_PLANCK_CGS",
            "rv_anchors": LOCKED_RV_ANCHORS_OPTICAL,
            "comb_spacings_ghz": [25.0, 40.0, 65.0, 100.0],
            "comb_step_ghz": 2.5,
            "comb_search_bands": ["CORALIE_BLUE", "CORALIE_RED"],
            "g6_topo_tol_kms": 5.0,
        })
    elif instrument == "CARMENES_VIS":
        r_val = float(resolving_power) if resolving_power is not None else 94600.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (5200.0, 9600.0),
            "coadd_rest_min_angstrom": 5210.0,
            "coadd_rest_max_angstrom": 9580.0,
            "coadd_step_angstrom": 0.02,
            "rv_anchor_fwhm_kms": 8.0,
            "scan_nms_min_sep_bins": 22,
            "radiometric_anchor": "GAIA_G_PLANCK_CGS",
            "rv_anchors": LOCKED_RV_ANCHORS_OPTICAL,
            "comb_spacings_ghz": [25.0, 40.0, 65.0, 100.0],
            "comb_step_ghz": 2.5,
            "comb_search_bands": ["CARM_GREEN", "CARM_RED", "CARM_FARRED"],
            "g6_topo_tol_kms": 4.5,
        })
    elif instrument == "CFHT_ESPADONS":
        r_val = float(resolving_power) if resolving_power is not None else 68000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (3700.0, 10480.0),
            "coadd_rest_min_angstrom": 3700.0,
            "coadd_rest_max_angstrom": 10480.0,
            "coadd_step_angstrom": 0.03,
            "rv_anchor_fwhm_kms": 10.0,
            "scan_nms_min_sep_bins": 20,
            "radiometric_anchor": "GAIA_G_PLANCK_CGS",
            "rv_anchors": LOCKED_RV_ANCHORS_OPTICAL,
            "comb_spacings_ghz": [25.0, 40.0, 65.0, 100.0],
            "comb_step_ghz": 2.5,
            "comb_search_bands": ["ESPADONS_OPT", "ESPADONS_FARRED"],
            "g6_topo_tol_kms": 5.0,
        })
    elif instrument == "OHP_SOPHIE":
        r_val = float(resolving_power) if resolving_power is not None else 75000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (3870.0, 6940.0),
            "coadd_rest_min_angstrom": 3870.0,
            "coadd_rest_max_angstrom": 6940.0,
            "coadd_step_angstrom": 0.02,
            "rv_anchor_fwhm_kms": 9.0,
            "scan_nms_min_sep_bins": 20,
            "radiometric_anchor": "GAIA_G_PLANCK_CGS",
            "rv_anchors": LOCKED_RV_ANCHORS_OPTICAL,
            "comb_spacings_ghz": [25.0, 40.0, 65.0, 100.0],
            "comb_step_ghz": 2.5,
            "comb_search_bands": ["SOPHIE_BLUE", "SOPHIE_RED"],
            "g6_topo_tol_kms": 5.0,
        })
    elif instrument == "OHP_ELODIE":
        r_val = float(resolving_power) if resolving_power is not None else 42000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (3890.0, 6815.0),
            "coadd_rest_min_angstrom": 3890.0,
            "coadd_rest_max_angstrom": 6815.0,
            "coadd_step_angstrom": 0.03,
            "rv_anchor_fwhm_kms": 12.0,
            "scan_nms_min_sep_bins": 18,
            "radiometric_anchor": "GAIA_G_PLANCK_CGS",
            "rv_anchors": LOCKED_RV_ANCHORS_OPTICAL,
            "comb_spacings_ghz": [25.0, 40.0, 65.0, 100.0],
            "comb_step_ghz": 2.5,
            "comb_search_bands": ["ELODIE_BLUE", "ELODIE_RED"],
            "g6_topo_tol_kms": 7.0,
        })
    elif instrument == "JWST_NIRSPEC_G395H":
        r_val = float(resolving_power) if resolving_power is not None else 2700.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (28620.0, 51790.0),
            "coadd_rest_min_angstrom": 28620.0,
            "coadd_rest_max_angstrom": 51790.0,
            "coadd_step_angstrom": 5.0,
            "rv_anchor_fwhm_kms": 110.0,
            "scan_nms_min_sep_bins": 14,
            "radiometric_anchor": "JWST_NIRSPEC_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 35.0,
        })
    elif instrument == "JWST_MIRI_MRS":
        r_val = float(resolving_power) if resolving_power is not None else 2500.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (49000.0, 286300.0),
            "coadd_rest_min_angstrom": 49000.0,
            "coadd_rest_max_angstrom": 286300.0,
            "coadd_step_angstrom": 8.0,
            "rv_anchor_fwhm_kms": 120.0,
            "scan_nms_min_sep_bins": 14,
            "radiometric_anchor": "JWST_MIRI_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 35.0,
        })
    elif instrument == "SDSS_APOGEE2":
        r_val = float(resolving_power) if resolving_power is not None else 22500.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (15140.0, 16960.0),
            "coadd_rest_min_angstrom": 15140.0,
            "coadd_rest_max_angstrom": 16960.0,
            "coadd_step_angstrom": 0.08,
            "rv_anchor_fwhm_kms": 16.0,
            "scan_nms_min_sep_bins": 18,
            "radiometric_anchor": "2MASS_H_PLANCK_CGS",
            "rv_anchors": LOCKED_RV_ANCHORS_APOGEE2,
            "comb_spacings_ghz": [25.0, 40.0, 65.0, 100.0],
            "comb_step_ghz": 2.5,
            "comb_search_bands": ["APOGEE_BLUE_CHIP", "APOGEE_GREEN_CHIP", "APOGEE_RED_CHIP"],
            "g6_topo_tol_kms": 8.0,
        })
    elif instrument == "GEMINI_GHOST":
        r_val = float(resolving_power) if resolving_power is not None else 56000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (3475.0, 10610.0),
            "coadd_rest_min_angstrom": 3475.0,
            "coadd_rest_max_angstrom": 10610.0,
            "coadd_step_angstrom": 0.03,
            "rv_anchor_fwhm_kms": 10.0,
            "scan_nms_min_sep_bins": 20,
            "radiometric_anchor": "GAIA_G_PLANCK_CGS",
            "rv_anchors": LOCKED_RV_ANCHORS_OPTICAL,
            "comb_spacings_ghz": [25.0, 40.0, 65.0, 100.0],
            "comb_step_ghz": 2.5,
            "comb_search_bands": ["GHOST_BLUE", "GHOST_RED_VIS", "GHOST_RED_NIR"],
            "g6_topo_tol_kms": 5.0,
        })
    elif instrument == "SPITZER_IRS":
        r_val = float(resolving_power) if resolving_power is not None else 100.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (52000.0, 380000.0),
            "coadd_rest_min_angstrom": 52000.0,
            "coadd_rest_max_angstrom": 380000.0,
            "coadd_step_angstrom": 50.0,
            "rv_anchor_fwhm_kms": 3000.0,
            "scan_nms_min_sep_bins": 10,
            "radiometric_anchor": "SPITZER_IRS_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 150.0,
        })
    elif instrument == "SOFIA_EXES":
        r_val = float(resolving_power) if resolving_power is not None else 66667.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (45000.0, 290000.0),
            "coadd_rest_min_angstrom": 45000.0,
            "coadd_rest_max_angstrom": 290000.0,
            "coadd_step_angstrom": 0.20,
            "rv_anchor_fwhm_kms": 10.0,
            "scan_nms_min_sep_bins": 16,
            "radiometric_anchor": "SOFIA_EXES_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 15.0,
        })
    elif instrument == "JWST_NIRISS_SOSS":
        r_val = float(resolving_power) if resolving_power is not None else 700.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (5900.0, 28300.0),
            "coadd_rest_min_angstrom": 5900.0,
            "coadd_rest_max_angstrom": 28300.0,
            "coadd_step_angstrom": 4.0,
            "rv_anchor_fwhm_kms": 430.0,
            "scan_nms_min_sep_bins": 10,
            "radiometric_anchor": "2MASS_H_PLANCK_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 150.0,
        })
    elif instrument == "JWST_NIRSPEC_G140H":
        r_val = float(resolving_power) if resolving_power is not None else 2700.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (7000.0, 18900.0),
            "coadd_rest_min_angstrom": 7000.0,
            "coadd_rest_max_angstrom": 18900.0,
            "coadd_step_angstrom": 2.0,
            "rv_anchor_fwhm_kms": 110.0,
            "scan_nms_min_sep_bins": 12,
            "radiometric_anchor": "2MASS_H_PLANCK_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 35.0,
        })
    elif instrument == "JWST_MIRI_LRS":
        r_val = float(resolving_power) if resolving_power is not None else 100.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (49500.0, 125000.0),
            "coadd_rest_min_angstrom": 49500.0,
            "coadd_rest_max_angstrom": 125000.0,
            "coadd_step_angstrom": 20.0,
            "rv_anchor_fwhm_kms": 3000.0,
            "scan_nms_min_sep_bins": 10,
            "radiometric_anchor": "JWST_MIRI_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 150.0,
        })
    else:
        r_val = float(resolving_power) if resolving_power is not None else 48000.0
        cfg.update({
            "instrument": "ESO_FEROS",
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (3527.0, 9216.0),
            "coadd_rest_min_angstrom": 3527.0,
            "coadd_rest_max_angstrom": 9216.0,
            "coadd_step_angstrom": 0.03,
            "rv_anchor_fwhm_kms": 10.0,
            "scan_nms_min_sep_bins": 20,
            "radiometric_anchor": "GAIA_G_PLANCK_CGS",
            "rv_anchors": LOCKED_RV_ANCHORS_OPTICAL,
            "comb_spacings_ghz": [25.0, 40.0, 65.0, 100.0],
            "comb_step_ghz": 2.5,
            "comb_search_bands": ["FEROS_BLUE", "FEROS_RED"],
            "g6_topo_tol_kms": 6.0,
        })
    return cfg


def get_calibration_bands(instrument: str) -> list[dict[str, Any]]:
    if instrument == "ESO_XSHOOTER_3ARM":
        return list(CALIBRATION_BANDS_XSHOOTER)
    if instrument == "ESO_GIRAFFE_HR":
        return list(CALIBRATION_BANDS_GIRAFFE)
    if instrument == "ESO_HARPS":
        return list(CALIBRATION_BANDS_HARPS)
    if instrument == "ESO_UVES":
        return list(CALIBRATION_BANDS_UVES)
    if instrument == "ESO_CRIRES":
        return list(CALIBRATION_BANDS_CRIRES)
    if instrument == "GEMINI_GRACES":
        return list(CALIBRATION_BANDS_GRACES)
    if instrument == "ESO_CORALIE":
        return list(CALIBRATION_BANDS_CORALIE)
    if instrument == "CARMENES_VIS":
        return list(CALIBRATION_BANDS_CARMENES_VIS)
    if instrument == "CFHT_ESPADONS":
        return list(CALIBRATION_BANDS_ESPADONS)
    if instrument == "OHP_SOPHIE":
        return list(CALIBRATION_BANDS_SOPHIE)
    if instrument == "OHP_ELODIE":
        return list(CALIBRATION_BANDS_ELODIE)
    if instrument == "JWST_NIRSPEC_G395H":
        return list(CALIBRATION_BANDS_NIRSPEC)
    if instrument == "JWST_MIRI_MRS":
        return list(CALIBRATION_BANDS_MIRI)
    if instrument == "SDSS_APOGEE2":
        return list(CALIBRATION_BANDS_APOGEE2)
    if instrument == "GEMINI_GHOST":
        return list(CALIBRATION_BANDS_GHOST)
    if instrument == "SPITZER_IRS":
        return list(CALIBRATION_BANDS_SPITZER_IRS)
    if instrument == "JWST_MIRI_LRS":
        return list(CALIBRATION_BANDS_MIRI_LRS)
    if instrument == "SOFIA_EXES":
        return list(CALIBRATION_BANDS_SOFIA_EXES)
    if instrument == "JWST_NIRISS_SOSS":
        return list(CALIBRATION_BANDS_JWST_NIRISS_SOSS)
    if instrument == "JWST_NIRSPEC_G140H":
        return list(CALIBRATION_BANDS_JWST_NIRSPEC_G140H)
    return list(CALIBRATION_BANDS_FEROS)


def resolve_band_radiometric_anchor(instrument: str) -> str:
    return str(get_inst_config(instrument)["radiometric_anchor"])


def gaia_g_planck_flam_cgs(wave_a: float, phot_g_mag: float, teff_k: float) -> float:
    """Closed-form Gaia G Planck extrapolation in erg s^-1 cm^-2 A^-1."""
    lam_w = float(wave_a) * 1e-10
    lam_g = GAIA_G_EFF_WAVE_A * 1e-10
    teff = max(1200.0, float(teff_k))
    xw = min(700.0, (H_PLANCK * C_SI) / (lam_w * K_BOLTZ * teff))
    xg = min(700.0, (H_PLANCK * C_SI) / (lam_g * K_BOLTZ * teff))
    bw = (2.0 * H_PLANCK * C_SI * C_SI) / ((lam_w ** 5) * math.expm1(xw))
    bg = (2.0 * H_PLANCK * C_SI * C_SI) / ((lam_g ** 5) * math.expm1(xg))
    fg = GAIA_G_FLAM0_CGS * (10.0 ** (-0.4 * float(phot_g_mag)))
    return float(fg * (bw / max(1e-30, bg)))


def twomass_h_planck_flam_cgs(wave_a: float, h_mag: float, teff_k: float) -> float:
    """Closed-form 2MASS H-band (Cohen+2003 zero point) Planck extrapolation in erg s^-1 cm^-2 A^-1."""
    lam_w = float(wave_a) * 1e-10
    lam_h = TWOMASS_H_EFF_WAVE_A * 1e-10
    teff = max(800.0, float(teff_k))
    xw = min(700.0, (H_PLANCK * C_SI) / (lam_w * K_BOLTZ * teff))
    xh = min(700.0, (H_PLANCK * C_SI) / (lam_h * K_BOLTZ * teff))
    bw = (2.0 * H_PLANCK * C_SI * C_SI) / ((lam_w ** 5) * math.expm1(xw))
    bh = (2.0 * H_PLANCK * C_SI * C_SI) / ((lam_h ** 5) * math.expm1(xh))
    fh = TWOMASS_H_FLAM0_CGS * (10.0 ** (-0.4 * float(h_mag)))
    return float(fh * (bw / max(1e-30, bh)))


# ---------------------------------------------------------------------------
# Pure-Stdlib Earth Heliocentric Ephemeris
# ---------------------------------------------------------------------------

def _earth_sun_state_equatorial(mjd_mid: float) -> tuple[float, float, float, float, float, float]:
    """Return Earth's heliocentric equatorial position (AU) and velocity (km/s)."""
    n = float(mjd_mid) - 51544.5
    L = math.radians((280.460 + 0.9856474 * n) % 360.0)
    g = math.radians((357.528 + 0.9856003 * n) % 360.0)
    lam_sun = L + math.radians(1.915) * math.sin(g) + math.radians(0.020) * math.sin(2.0 * g)
    r_au = 1.00014 - 0.01671 * math.cos(g) - 0.00014 * math.cos(2.0 * g)
    eps = math.radians(23.439 - 0.0000004 * n)

    c_eps = math.cos(eps)
    s_eps = math.sin(eps)
    s_lam = math.sin(lam_sun)
    c_lam = math.cos(lam_sun)

    ex = -r_au * c_lam
    ey = -r_au * c_eps * s_lam
    ez = -r_au * s_eps * s_lam

    g_dot = math.radians(0.9856003)
    d_lam = math.radians(0.9856474) + (math.radians(1.915) * math.cos(g) + 2.0 * math.radians(0.020) * math.cos(2.0 * g)) * g_dot
    d_r = (0.01671 * math.sin(g) + 0.00028 * math.sin(2.0 * g)) * g_dot
    au_per_day_to_kms = AU_M / (DAY_S * 1000.0)

    vx = -(d_r * c_lam - r_au * s_lam * d_lam) * au_per_day_to_kms
    vy = -c_eps * (d_r * s_lam + r_au * c_lam * d_lam) * au_per_day_to_kms
    vz = -s_eps * (d_r * s_lam + r_au * c_lam * d_lam) * au_per_day_to_kms
    return ex, ey, ez, vx, vy, vz


def stdlib_earth_helio_rv_kms(ra_deg: float, dec_deg: float, mjd_mid: float) -> float:
    _, _, _, vx, vy, vz = _earth_sun_state_equatorial(mjd_mid)
    ra_r = math.radians(float(ra_deg))
    dec_r = math.radians(float(dec_deg))
    ux = math.cos(dec_r) * math.cos(ra_r)
    uy = math.cos(dec_r) * math.sin(ra_r)
    uz = math.sin(dec_r)
    return float(vx * ux + vy * uy + vz * uz)


# ---------------------------------------------------------------------------
# Pure Array & Orbital Helpers
# ---------------------------------------------------------------------------

def exact_median_1d(arr: np.ndarray) -> float:
    s = np.sort(np.asarray(arr, dtype=np.float64))
    n = len(s)
    if n == 0:
        return float("nan")
    m = n // 2
    return float(s[m]) if (n % 2 == 1) else float(0.5 * (s[m - 1] + s[m]))


def exact_mad_1d(arr: np.ndarray) -> float:
    a = np.asarray(arr, dtype=np.float64)
    if len(a) == 0:
        return float("nan")
    med = exact_median_1d(a)
    return float(MAD_NORM * exact_median_1d(np.abs(a - med)))


def exact_quantile_1d(arr: np.ndarray, q: float) -> float:
    s = np.sort(np.asarray(arr, dtype=np.float64))
    n = len(s)
    if n == 0:
        return float("nan")
    if n == 1:
        return float(s[0])
    pos = float(q) * (n - 1)
    lo = int(math.floor(pos))
    hi = min(n - 1, lo + 1)
    frac = pos - lo
    return float(s[lo] + frac * (s[hi] - s[lo]))


def compute_keplerian_kp_kms(st_mass_msun: float, orbper_days: float, ecc: float = 0.0) -> float:
    v_circ = ((2.0 * math.pi * G_SI * float(st_mass_msun) * M_SUN_KG) / (float(orbper_days) * DAY_S)) ** (1.0 / 3.0)
    return float((v_circ / math.sqrt(max(1e-6, 1.0 - float(ecc) ** 2))) / 1000.0)


def compute_planet_orbital_rv_kms(bjd_mid: float, t0_bjd: float, orbper_days: float, kp_kms: float) -> tuple[float, float]:
    raw_phi = (float(bjd_mid) - float(t0_bjd)) / float(orbper_days)
    phi_signed = raw_phi - round(raw_phi)
    return float(phi_signed), float(kp_kms * math.sin(2.0 * math.pi * phi_signed))


def planet_rest_to_bary_wave(wave_planet_a: float | np.ndarray, v_star_kms: float, dv_orb_kms: float) -> float | np.ndarray:
    return wave_planet_a * (1.0 + float(v_star_kms) / C_KMS) * (1.0 + float(dv_orb_kms) / C_KMS)


def bary_to_planet_rest_wave(wave_bary_a: float | np.ndarray, v_star_kms: float, dv_orb_kms: float) -> float | np.ndarray:
    return wave_bary_a / ((1.0 + float(v_star_kms) / C_KMS) * (1.0 + float(dv_orb_kms) / C_KMS))


# ---------------------------------------------------------------------------
# Step 1: Optical/NIR RV Anchoring
# ---------------------------------------------------------------------------

def extract_rv_anchor_window(
    wave: np.ndarray,
    flux: np.ndarray,
    lab_wave_a: float,
    prior_rv_kms: float,
    cfg: dict[str, Any] = BASE_V4_2_CONFIG,
) -> tuple[np.ndarray, np.ndarray]:
    dv = C_KMS * (wave - lab_wave_a) / lab_wave_a
    win_kms = float(cfg["rv_anchor_window_kms"])
    mask = np.abs(dv - prior_rv_kms) <= win_kms
    return wave[mask].copy(), flux[mask].copy()


def fit_rv_anchor_absorption(
    wave_win: np.ndarray,
    flux_win: np.ndarray,
    lab_wave_a: float,
    prior_rv_kms: float,
    cfg: dict[str, Any] = BASE_V4_2_CONFIG,
) -> dict[str, Any]:
    w = np.asarray(wave_win, dtype=np.float64)
    f = np.asarray(flux_win, dtype=np.float64)
    valid = np.isfinite(w) & np.isfinite(f)
    w, f = w[valid], f[valid]
    if len(w) < 8:
        return {
            "status": "INSUFFICIENT_SAMPLES",
            "n_samples": int(len(w)),
            "best_rv_kms": float("nan"),
            "rel_depth": float("nan"),
            "min_sse": float("nan"),
            "boundary_hit": True,
        }

    dv = C_KMS * (w - lab_wave_a) / lab_wave_a
    win_kms = float(cfg["rv_anchor_window_kms"])
    u = (dv - prior_rv_kms) / max(1.0, win_kms)
    fwhm_p = max(float(cfg["rv_anchor_fwhm_kms"]), C_KMS / effective_resolving_power(cfg, lab_wave_a))
    sigma_phot = fwhm_p / FWHM_FACTOR
    half = float(cfg["rv_anchor_scan_half_kms"])
    step = float(cfg["rv_anchor_scan_step_kms"])
    n_grid = int(round(2.0 * half / step)) + 1
    grid = prior_rv_kms - half + step * np.arange(n_grid, dtype=np.float64)
    ones = np.ones_like(u)
    sses = np.full(n_grid, np.inf, dtype=np.float64)
    snrs = np.zeros(n_grid, dtype=np.float64)

    for idx, v_try in enumerate(grid):
        prof = np.exp(-0.5 * ((dv - v_try) / sigma_phot) ** 2)
        X = np.column_stack([ones, u, prof])
        try:
            beta = np.linalg.solve(X.T @ X, X.T @ f)
        except np.linalg.LinAlgError:
            continue
        amp = float(beta[2])
        resid = f - (X @ beta)
        sse = float(resid @ resid)
        sb_mask = np.abs(dv - v_try) >= 1.8 * sigma_phot
        sb_mad = max(1e-30, exact_mad_1d(resid[sb_mask]) if int(np.sum(sb_mask)) >= 5 else exact_mad_1d(resid))
        sses[idx] = sse
        snrs[idx] = abs(amp) / sb_mad

    best_idx = int(np.argmin(sses))
    boundary_hit = (best_idx == 0) or (best_idx == n_grid - 1)
    best_v = float(grid[best_idx])
    if not boundary_hit:
        y_m, y_0, y_p = float(sses[best_idx - 1]), float(sses[best_idx]), float(sses[best_idx + 1])
        denom = y_m - 2.0 * y_0 + y_p
        if denom > 1e-30:
            delta = max(-0.5, min(0.5, 0.5 * (y_m - y_p) / denom))
            best_v = float(grid[best_idx] + delta * step)

    metric = float(snrs[best_idx])
    clean = (not boundary_hit) and (metric >= float(cfg["rv_anchor_min_snr"]))
    return {
        "status": "CLEAN_ABSORPTION" if clean else ("BOUNDARY_HIT" if boundary_hit else "SHALLOW_OR_BLENDED"),
        "n_samples": int(len(w)),
        "best_rv_kms": best_v,
        "rel_depth": float(metric),
        "min_sse": float(sses[best_idx]),
        "boundary_hit": bool(boundary_hit),
    }


def measure_exposure_stellar_rv(
    wave: np.ndarray,
    flux: np.ndarray,
    prior_rv_kms: float,
    cfg: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, list[float]]]]:
    anchors = cfg.get("rv_anchors", LOCKED_RV_ANCHORS_OPTICAL)
    anchor_rows: list[dict[str, Any]] = []
    bundle: dict[str, dict[str, list[float]]] = {}
    clean_rvs: list[float] = []
    fin_nz = np.isfinite(flux) & (flux != 0)
    med_abs = float(np.nanmedian(np.abs(flux[fin_nz]))) if np.any(fin_nz) else 1e-17
    scale_anc = 1.0 / max(1e-26, med_abs)
    for anc in anchors:
        aid = anc["anchor_id"]
        lab_a = float(anc["lab_wave_A"])
        w_win, f_win = extract_rv_anchor_window(wave, flux * scale_anc, lab_a, prior_rv_kms, cfg)
        res = fit_rv_anchor_absorption(w_win, f_win, lab_a, prior_rv_kms, cfg)
        anchor_rows.append({
            "anchor_id": aid,
            "species": anc["species"],
            "lab_wave_A": lab_a,
            "status": res["status"],
            "n_samples": res["n_samples"],
            "best_rv_kms": res["best_rv_kms"],
            "rel_depth": res["rel_depth"],
            "min_sse": res["min_sse"],
        })
        bundle[aid] = {"wave_a": [round(float(x), 4) for x in w_win], "flux": [round(float(y), 4) for y in f_win]}
        if res["status"] == "CLEAN_ABSORPTION":
            clean_rvs.append(float(res["best_rv_kms"]))

    if clean_rvs:
        emp_rv = exact_median_1d(np.asarray(clean_rvs, dtype=np.float64))
        emp_mad = exact_mad_1d(np.asarray(clean_rvs, dtype=np.float64)) if len(clean_rvs) >= 2 else 0.0
    else:
        emp_rv = float(prior_rv_kms)
        emp_mad = 0.0

    summary = {
        "empirical_rv_kms": float(emp_rv),
        "anchor_mad_kms": float(emp_mad),
        "n_clean_anchors": len(clean_rvs),
        "used_fallback_prior_rv": len(clean_rvs) == 0,
    }
    return summary, anchor_rows, bundle


# ---------------------------------------------------------------------------
# Step 2: Running Continuum & Overlap-Aware KNN Templates
# ---------------------------------------------------------------------------

def compute_running_continuum(
    wave: np.ndarray,
    flux: np.ndarray,
    cfg: dict[str, Any] = BASE_V4_2_CONFIG,
    err: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (raw_continuum, strictly_positive_effective_scale)."""
    w = np.asarray(wave, dtype=np.float64)
    f = np.asarray(flux, dtype=np.float64)
    n = len(f)
    blk = int(cfg["continuum_block_bins"])
    m = (n + blk - 1) // blk
    bx = np.empty(m, dtype=np.float64)
    by_raw = np.empty(m, dtype=np.float64)
    by_eff = np.empty(m, dtype=np.float64)
    q_blue = float(cfg["continuum_quantile_blue"])
    q_red = float(cfg["continuum_quantile"])
    blue_cut = float(cfg["continuum_blue_cutoff_angstrom"])

    e_arr = np.asarray(err, dtype=np.float64) if err is not None else None
    global_pos = f[np.isfinite(f) & (f > 0.0)]
    g_floor = 0.25 * exact_quantile_1d(global_pos, 0.70) if len(global_pos) >= 20 else 1e-22
    if e_arr is not None:
        e_fin = e_arr[np.isfinite(e_arr) & (e_arr > 0.0)]
        if len(e_fin) >= 20:
            g_floor = max(g_floor, 3.0 * exact_median_1d(e_fin))
    g_floor = max(1e-26, float(g_floor))

    for i in range(m):
        s, e = i * blk, min(n, (i + 1) * blk)
        bx[i] = 0.5 * (w[s] + w[e - 1])
        seg = f[s:e]
        fin_s = seg[np.isfinite(seg)]
        q_use = q_blue if bx[i] < blue_cut else q_red
        if len(fin_s) >= 8:
            c_q = exact_quantile_1d(fin_s, q_use)
            c_raw = max(0.0, float(c_q)) if math.isfinite(c_q) else 0.0
            if e_arr is not None:
                eseg = e_arr[s:e]
                ef = eseg[np.isfinite(eseg) & (eseg > 0.0)]
                efloor = 3.0 * exact_median_1d(ef) if len(ef) >= 4 else g_floor
            else:
                efloor = g_floor
            by_raw[i] = c_raw
            by_eff[i] = max(c_raw, efloor, g_floor)
        else:
            by_raw[i] = float("nan")
            by_eff[i] = float("nan")

    fin = np.isfinite(by_eff) & (by_eff > 0.0)
    if int(fin.sum()) < 2:
        return np.zeros(n, dtype=np.float64), np.full(n, g_floor, dtype=np.float64)
    iraw = np.interp(bx, bx[fin], np.where(np.isfinite(by_raw[fin]), by_raw[fin], 0.0))
    ieff = np.interp(bx, bx[fin], by_eff[fin])
    sm_k = int(cfg["continuum_median_blocks"])
    c_raw_full = np.interp(w, bx, median_filter(iraw, size=sm_k, mode="nearest"))
    c_eff_full = np.maximum(g_floor, np.interp(w, bx, median_filter(ieff, size=sm_k, mode="nearest")))
    return c_raw_full, c_eff_full


def fit_optical_depth_and_continuum_gamma(
    target_flux: np.ndarray,
    template_flux: np.ndarray,
    block_size: int = 800,
) -> tuple[np.ndarray, float, float]:
    t = np.asarray(target_flux, dtype=np.float64)
    r = np.asarray(template_flux, dtype=np.float64)
    fin = np.isfinite(t) & np.isfinite(r) & (t > 0.05) & (r > 0.05) & (t < 1.35) & (r < 1.35)
    t_clip = np.clip(t, 0.05, 1.35)
    r_clip = np.clip(r, 0.05, 1.35)

    gammas = [1.0]
    if int(fin.sum()) >= 50:
        for s in range(0, len(t), block_size):
            e = min(len(t), s + block_size)
            m_b = fin[s:e] & (t[s:e] < 0.92) & (r[s:e] < 0.92)
            if int(m_b.sum()) >= 25:
                num = float(np.sum((t_clip[s:e][m_b] - 1.0) * (r_clip[s:e][m_b] - 1.0)))
                den = float(np.sum((r_clip[s:e][m_b] - 1.0) ** 2))
                if den > 1e-9:
                    gammas.append(max(0.55, min(1.80, num / den)))
    gamma_best = exact_median_1d(np.asarray(gammas, dtype=np.float64))
    pred = r_clip ** gamma_best

    ratio_blocks = np.ones(max(1, (len(t) + block_size - 1) // block_size), dtype=np.float64)
    bx = np.zeros(len(ratio_blocks), dtype=np.float64)
    idx_arr = np.arange(len(t), dtype=np.float64)
    for b_i in range(len(ratio_blocks)):
        s, e = b_i * block_size, min(len(t), (b_i + 1) * block_size)
        bx[b_i] = 0.5 * (s + e - 1)
        mb = fin[s:e] & (pred[s:e] > 0.25)
        if int(mb.sum()) >= 20:
            ratio_blocks[b_i] = max(0.75, min(1.30, exact_median_1d(t[s:e][mb] / pred[s:e][mb])))
    scale_smooth = np.interp(idx_arr, bx, ratio_blocks)
    matched = np.where(np.isfinite(pred), scale_smooth * pred, np.nan)
    resid = np.where(np.isfinite(t) & np.isfinite(matched), t - matched, np.nan)
    post_mad = exact_mad_1d(resid[np.isfinite(resid)]) if int(np.sum(np.isfinite(resid))) >= 50 else 0.05
    return matched, float(gamma_best), float(post_mad)


def construct_knn_stellar_templates(
    star_meta: dict[str, dict[str, Any]],
    star_norm_coadds: dict[str, np.ndarray],
    cfg: dict[str, Any] = BASE_V4_2_CONFIG,
) -> tuple[dict[str, np.ndarray], dict[str, dict[str, Any]]]:
    k_nn = int(cfg["knn_atlas_neighbors"])
    s_t = float(cfg["knn_teff_scale_k"])
    s_m = float(cfg["knn_mh_scale_dex"])
    min_ov = float(cfg["knn_min_wave_overlap_frac"])
    matched_templates: dict[str, np.ndarray] = {}
    template_meta: dict[str, dict[str, Any]] = {}

    stars = sorted(star_norm_coadds.keys())
    fin_by_star = {s: np.isfinite(star_norm_coadds[s]) for s in stars}

    for st in stars:
        mt = star_meta[st]
        inst_st = mt["instrument"]
        ft = fin_by_star[st]
        n_ft = max(1, int(ft.sum()))

        ov_cands, all_cands = [], []
        for other in stars:
            if other == st:
                continue
            mo = star_meta[other]
            if mo["instrument"] != inst_st:
                continue
            d2 = ((mt["teff_k"] - mo["teff_k"]) / s_t) ** 2 + ((mt["mh_dex"] - mo["mh_dex"]) / s_m) ** 2
            ov_frac = int(np.sum(ft & fin_by_star[other])) / n_ft
            all_cands.append((d2, other))
            if ov_frac >= min_ov:
                ov_cands.append((d2, other))

        cands = ov_cands if len(ov_cands) >= 2 else all_cands
        cands.sort(key=lambda x: (x[0], x[1]))
        nbrs = cands[: min(k_nn, len(cands))]
        if not nbrs:
            matched_templates[st] = np.ones_like(star_norm_coadds[st])
            template_meta[st] = {"knn_neighbors": "", "optical_depth_gamma": 1.0, "post_match_mad": 0.05}
            continue
        weights = [1.0 / (d2 + 0.05) for d2, _ in nbrs]
        stack = np.vstack([star_norm_coadds[o] for _, o in nbrs])
        w_arr = np.asarray(weights, dtype=np.float64)[:, None]
        fin_m = np.isfinite(stack)
        num = np.sum(np.where(fin_m, stack, 0.0) * w_arr, axis=0)
        den = np.sum(np.where(fin_m, w_arr, 0.0), axis=0)
        raw_t = np.where(den > 0.0, num / np.where(den > 0.0, den, 1.0), np.nan)
        matched, gamma, pmad = fit_optical_depth_and_continuum_gamma(star_norm_coadds[st], raw_t)
        matched_templates[st] = matched
        template_meta[st] = {
            "knn_neighbors": ",".join(o for _, o in nbrs),
            "optical_depth_gamma": round(gamma, 4),
            "post_match_mad": round(pmad, 6),
        }
    return matched_templates, template_meta


# ---------------------------------------------------------------------------
# Step 3: Wavelength-Adaptive Instrument-LSF Matched Filtering
# ---------------------------------------------------------------------------

def fit_lsf_on_window(
    wave_win: np.ndarray,
    resid_win: np.ndarray,
    seed_wave_a: float,
    cfg: dict[str, Any],
    fixed_phase_bins: float | None = None,
) -> dict[str, Any]:
    w = np.asarray(wave_win, dtype=np.float64)
    y = np.asarray(resid_win, dtype=np.float64)
    valid = np.isfinite(w) & np.isfinite(y)
    if int(valid.sum()) < 20:
        return {"valid_fit": False}

    step_a = float(exact_median_1d(np.diff(w)))
    r_eff = effective_resolving_power(cfg, seed_wave_a)
    sigma_v = C_KMS / (r_eff * FWHM_FACTOR)
    phases = [fixed_phase_bins] if fixed_phase_bins is not None else cfg["fit_phases_bins"]

    best: dict[str, Any] | None = None
    best_energy = -1.0
    for ph in phases:
        assert ph is not None
        mu_a = float(seed_wave_a + ph * step_a)
        dv = C_KMS * (w - mu_a) / mu_a
        abs_dv = np.abs(dv)
        bg_mid = valid & (abs_dv >= cfg["mid_inner_sigma_mult"] * sigma_v) & (abs_dv <= cfg["mid_outer_sigma_mult"] * sigma_v)
        bg_out = valid & (abs_dv >= cfg["outer_inner_sigma_mult"] * sigma_v) & (abs_dv <= cfg["outer_outer_sigma_mult"] * sigma_v)
        core = valid & (abs_dv <= cfg["core_sigma_mult"] * sigma_v)
        if int(bg_mid.sum()) < 8 or int(core.sum()) < 3:
            continue

        b0 = exact_median_1d(y[bg_mid])
        b0_out = exact_median_1d(y[bg_out]) if int(bg_out.sum()) >= 8 else b0
        yc = y[core] - b0
        yc_out = y[core] - b0_out
        g = np.exp(-0.5 * (dv[core] / sigma_v) ** 2)
        gg = float(g @ g)
        if gg <= 0.0:
            continue
        amp = float(yc @ g) / gg
        amp_out = float(yc_out @ g) / gg
        if amp <= 0.0:
            continue
        yn = float(math.sqrt(max(0.0, float(yc @ yc))))
        gn = float(math.sqrt(gg))
        cosine = (float(yc @ g) / (yn * gn)) if (yn > 0.0 and gn > 0.0) else 0.0
        sig_mid = exact_mad_1d(y[bg_mid])
        sig_out = exact_mad_1d(y[bg_out]) if int(bg_out.sum()) >= 8 else sig_mid
        if not (math.isfinite(sig_mid) and sig_mid > 0.0):
            continue
        energy = amp * amp * gg
        if energy > best_energy:
            best_energy = energy
            half_lv = 0.5 * amp
            sub_c = valid & (abs_dv <= 8.0 * sigma_v)
            ws, ys = w[sub_c], y[sub_c] - b0
            above = np.flatnonzero(ys >= half_lv)
            if len(above) >= 2:
                w_span = float(ws[above[-1]] - ws[above[0]] + step_a)
                fwhm_a = mu_a / r_eff
                fwhm_ratio = w_span / max(1e-6, fwhm_a)
            else:
                fwhm_ratio = 1.0
            best = {
                "valid_fit": True,
                "fitted_center_a": mu_a,
                "phase_bins": float(ph),
                "amp_mid": float(amp),
                "amp_out": float(amp_out),
                "snr_mid": float(amp / sig_mid),
                "snr_out": float(amp / sig_out) if (math.isfinite(sig_out) and sig_out > 0.0) else float(amp / sig_mid),
                "sig_mid": float(sig_mid),
                "cosine": float(cosine),
                "fwhm_ratio": float(fwhm_ratio),
                "effective_resolving_power": float(r_eff),
            }
    return best if best is not None else {"valid_fit": False}


def compute_supraphotospheric_f1_window(
    wave_win: np.ndarray,
    flux_norm_win: np.ndarray,
    center_a: float,
    min_fn_pk3: float,
) -> dict[str, Any]:
    w = np.asarray(wave_win, dtype=np.float64)
    fn = np.asarray(flux_norm_win, dtype=np.float64)
    k0 = int(np.argmin(np.abs(w - center_a)))
    sub = fn[max(0, k0 - 1) : min(len(fn), k0 + 2)]
    fin = sub[np.isfinite(sub)]
    if len(fin) == 0:
        return {"fn_pk3": 0.0, "f1_supraphotospheric_pass": False}
    fn_pk3 = float(np.max(fin))
    return {"fn_pk3": fn_pk3, "f1_supraphotospheric_pass": fn_pk3 >= min_fn_pk3}


def check_channel_lsf_gate(fit: dict[str, Any], channel: str, cfg: dict[str, Any]) -> bool:
    if not fit.get("valid_fit"):
        return False
    ch = channel.lower()
    if ch == "t":
        pref = "channel_t"
    elif ch == "p":
        pref = "channel_p"
    elif ch == "t_diff":
        pref = "channel_tdiff"
    else:
        pref = "channel_kplanet"
    snr_out = fit["snr_out"]
    amp_out = float(fit.get("amp_out", fit["amp_mid"]))
    if snr_out <= 0.0 or amp_out <= 0.0:
        return False
    ratio = float(fit["amp_mid"]) / amp_out
    return bool(
        fit["snr_mid"] >= cfg[f"{pref}_snr_mid_min"]
        and snr_out >= cfg[f"{pref}_snr_outer_min"]
        and cfg[f"{pref}_amp_ratio_min"] <= ratio <= cfg[f"{pref}_amp_ratio_max"]
        and fit["cosine"] >= cfg[f"{pref}_cosine_min"]
        and cfg[f"{pref}_fwhm_ratio_min"] <= fit["fwhm_ratio"] <= cfg[f"{pref}_fwhm_ratio_max"]
    )


def scan_single_exposure_residual_lsf(
    wave: np.ndarray,
    y_primary: np.ndarray,
    cfg: dict[str, Any],
    channel: str = "T",
    y_secondary_check: np.ndarray | None = None,
    flux_norm_for_f1: np.ndarray | None = None,
    enforce_f1_in_g1: bool = True,
) -> tuple[list[dict[str, Any]], int, int]:
    n = len(wave)
    finite = np.isfinite(y_primary)
    diffs = np.diff(finite.astype(np.int8))
    starts = list(np.flatnonzero(diffs == 1) + 1)
    if finite[0]:
        starts.insert(0, 0)
    ends = list(np.flatnonzero(diffs == -1) + 1)
    if finite[-1]:
        ends.append(n)

    min_fn = float(cfg["supraphotospheric_min_fn_pk3"])
    prelim_pre_f1: list[dict[str, Any]] = []
    searched_bins = 0

    for seg_s, seg_e in zip(starts, ends):
        if seg_e - seg_s < 120:
            continue
        vals = y_primary[seg_s:seg_e]
        mad = exact_mad_1d(vals)
        if not (math.isfinite(mad) and mad > 0.0):
            continue
        searched_bins += int(seg_e - seg_s)

        med = exact_median_1d(vals)
        thresh = med + float(cfg["scan_seed_sigma_mult"]) * mad
        is_pk = (vals[1:-1] > vals[:-2]) & (vals[1:-1] >= vals[2:]) & (vals[1:-1] > thresh)
        cand_locs = sorted(
            [seg_s + 1 + int(i) for i in np.flatnonzero(is_pk)],
            key=lambda k: float(y_primary[k]),
            reverse=True,
        )
        kept_locs: list[int] = []
        min_sep = int(cfg["scan_nms_min_sep_bins"])
        for k in cand_locs:
            margin = _scan_margin_bins(float(wave[k]), cfg)
            if k < seg_s + margin or k >= seg_e - margin:
                continue
            if any(abs(k - prev) < min_sep for prev in kept_locs):
                continue
            kept_locs.append(k)
            sl = slice(k - margin, k + margin + 1)
            fit = fit_lsf_on_window(wave[sl], y_primary[sl], float(wave[k]), cfg)
            if not check_channel_lsf_gate(fit, channel, cfg):
                continue
            f1 = (
                compute_supraphotospheric_f1_window(wave[sl], flux_norm_for_f1[sl], float(fit["fitted_center_a"]), min_fn)
                if flux_norm_for_f1 is not None
                else {"fn_pk3": 1.5, "f1_supraphotospheric_pass": True}
            )
            fit["seed_index"] = int(k)
            fit["fn_pk3"] = float(f1["fn_pk3"])
            fit["f1_pass"] = bool(f1["f1_supraphotospheric_pass"])
            if enforce_f1_in_g1 and not fit["f1_pass"]:
                continue
            prelim_pre_f1.append(fit)

    if y_secondary_check is not None:
        final = []
        for c in prelim_pre_f1:
            k = c["seed_index"]
            margin = _scan_margin_bins(float(wave[k]), cfg)
            sl = slice(max(0, k - margin), min(n, k + margin + 1))
            f_opp = fit_lsf_on_window(wave[sl], y_secondary_check[sl], c["fitted_center_a"], cfg, fixed_phase_bins=c["phase_bins"])
            c["opp_snr_mid"] = float(f_opp.get("snr_mid", 0.0))
            final.append(c)
    else:
        final = prelim_pre_f1
    return final, searched_bins, len(final)


def build_multi_epoch_rest_coadd_and_channel_p(
    rest_grid: np.ndarray,
    exp_rest_norm_mat: np.ndarray,
    exp_rest_resid_mat: np.ndarray,
    matched_template: np.ndarray,
    cfg: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]], int, int]:
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)
        coadd_resid = np.nanmedian(exp_rest_resid_mat, axis=0)
        coadd_fn = np.nanmedian(exp_rest_norm_mat, axis=0)
    cands, searched_bins, _ = scan_single_exposure_residual_lsf(
        rest_grid, coadd_resid, cfg, channel="P", flux_norm_for_f1=coadd_fn, enforce_f1_in_g1=False
    )
    return coadd_resid, coadd_fn, cands, searched_bins, len(cands)


def build_and_scan_transit_channels(
    planet_grid: np.ndarray,
    unshifted_resids: np.ndarray,
    unshifted_fn: np.ndarray,
    dedoppler_resids: np.ndarray,
    dedoppler_fn: np.ndarray,
    out_resid_med: np.ndarray,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)
        in_unsh = np.nanmedian(unshifted_resids, axis=0) - out_resid_med
        in_unsh_fn = np.nanmedian(unshifted_fn, axis=0)
        y_kp = np.nanmedian(dedoppler_resids, axis=0) - out_resid_med
        kp_fn = np.nanmedian(dedoppler_fn, axis=0)

    td_cands, td_bins, _ = scan_single_exposure_residual_lsf(
        planet_grid, in_unsh, cfg, channel="T_DIFF", flux_norm_for_f1=in_unsh_fn, enforce_f1_in_g1=False
    )
    kp_cands, kp_bins, _ = scan_single_exposure_residual_lsf(
        planet_grid, y_kp, cfg, channel="K_PLANET", flux_norm_for_f1=kp_fn, enforce_f1_in_g1=False
    )

    def _keep_multi(c_list: list[dict[str, Any]], mat: np.ndarray, min_snr: float, min_frac: float) -> list[dict[str, Any]]:
        out = []
        for h in c_list:
            k = int(h["seed_index"])
            margin = _scan_margin_bins(float(h["fitted_center_a"]), cfg)
            sl = slice(max(0, k - margin), min(len(planet_grid), k + margin + 1))
            nhit, ncov = 0, 0
            for j in range(mat.shape[0]):
                ef = fit_lsf_on_window(planet_grid[sl], mat[j, sl], h["fitted_center_a"], cfg, fixed_phase_bins=h["phase_bins"])
                if ef.get("valid_fit"):
                    ncov += 1
                    if ef["snr_mid"] >= min_snr:
                        nhit += 1
            if ncov >= 2 and nhit >= max(2, int(math.ceil(min_frac * ncov))):
                h["in_epochs_hit"] = nhit
                out.append(h)
        return out

    return {
        "y_tdiff": in_unsh,
        "u_tdiff_fn": in_unsh_fn,
        "y_kplanet": y_kp,
        "f_kplanet_fn": kp_fn,
        "tdiff_cands": _keep_multi(td_cands, unshifted_resids - out_resid_med[None, :], cfg["channel_tdiff_min_in_exp_snr"], cfg["channel_tdiff_min_in_exp_fraction"]),
        "kplanet_cands": _keep_multi(kp_cands, dedoppler_resids - out_resid_med[None, :], cfg["channel_kplanet_min_in_exp_snr"], cfg["channel_kplanet_min_in_exp_fraction"]),
        "tdiff_searched_bins": td_bins,
        "kplanet_searched_bins": kp_bins,
    }


# ---------------------------------------------------------------------------
# Step 4: Automated Physics Vetting Gates G2_V42, G3_V42, G4_V42, G5, G6
# ---------------------------------------------------------------------------

def evaluate_gate_g2_airglow(
    fitted_bary_wave_a: float,
    berv_kms: float,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """Paranal/La Silla ground sky airglow + telluric O2/H2O absorption gate."""
    topo_a = float(fitted_bary_wave_a / (1.0 + berv_kms / C_KMS))
    best_line = min(GROUND_AIRGLOW_AND_TELLURIC_A, key=lambda x: abs(topo_a - float(x["wave_A"])))
    dv = abs(C_KMS * (topo_a - float(best_line["wave_A"])) / max(1.0, float(best_line["wave_A"])))
    sep_a = abs(topo_a - float(best_line["wave_A"]))
    if dv <= float(best_line["half_width_kms"]):
        return {
            "topo_wave_a": topo_a,
            "nearest_airglow_name": best_line["name"],
            "nearest_airglow_sep_a": round(sep_a, 4),
            "g2_pass": False,
            "g2_reason": f"GROUND_SKY_{best_line['name']}",
        }
    return {
        "topo_wave_a": topo_a,
        "nearest_airglow_name": best_line["name"],
        "nearest_airglow_sep_a": round(sep_a, 4),
        "g2_pass": True,
        "g2_reason": "PASS",
    }


def evaluate_native_order_patch(
    wave_ord_win: np.ndarray,
    flux_ord_win: np.ndarray,
    ref_ord_win: np.ndarray | None,
    target_wave_a: float,
    cfg: dict[str, Any],
    err_ord_win: np.ndarray | None = None,
) -> dict[str, Any]:
    w = np.asarray(wave_ord_win, dtype=np.float64)
    f = np.asarray(flux_ord_win, dtype=np.float64)
    if len(w) < 35 or not (np.all(np.isfinite(w)) and np.all(np.isfinite(f))):
        return {"usable": False}

    k_loc = int(np.argmin(np.abs(w - target_wave_a)))
    if k_loc < 12 or k_loc >= len(w) - 12:
        return {"usable": False}

    idx_rel = np.abs(np.arange(len(w)) - k_loc)
    sb_mask = (idx_rel >= 10) & (idx_rel <= min(70, len(w) // 2))
    if int(sb_mask.sum()) < 12:
        return {"usable": False}

    q_cont = float(cfg["continuum_quantile_blue"]) if target_wave_a < float(cfg["continuum_blue_cutoff_angstrom"]) else float(cfg["continuum_quantile"])
    cont_q = exact_quantile_1d(f[sb_mask], q_cont)
    if not math.isfinite(cont_q):
        return {"usable": False}

    cont_raw = max(0.0, float(cont_q))
    e_floor = 1e-26
    if err_ord_win is not None:
        ea = np.asarray(err_ord_win, dtype=np.float64)
        esb = ea[sb_mask]
        ef = esb[np.isfinite(esb) & (esb > 0.0)]
        if len(ef) >= 5:
            e_floor = max(e_floor, 3.0 * exact_median_1d(ef))
    sb_mad_f = exact_mad_1d(f[sb_mask])
    if math.isfinite(sb_mad_f) and sb_mad_f > 0.0:
        e_floor = max(e_floor, 3.0 * sb_mad_f)
    cont_adu = max(cont_raw, e_floor)
    if cont_raw >= e_floor:
        f_norm = f / cont_adu
    else:
        f_norm = 1.0 + (f - cont_raw) / cont_adu

    native_fn_pk3 = float(np.max(f_norm[k_loc - 1 : k_loc + 2]))

    scale = 1.0
    r_ref_clean = None
    if ref_ord_win is not None:
        r_ref = np.asarray(ref_ord_win, dtype=np.float64)
        valid_sb = sb_mask & np.isfinite(r_ref) & (r_ref > 0.05)
        scale = exact_median_1d(f_norm[valid_sb] / r_ref[valid_sb]) if int(valid_sb.sum()) >= 10 else 1.0
        scale = max(0.5, min(2.0, scale))
        r_ref_clean = np.where(np.isfinite(r_ref), r_ref, 1.0)
        y = f_norm - scale * r_ref_clean
    else:
        y = f_norm - 1.0

    idx = np.arange(len(w)) - k_loc
    max_sb = min(70, len(w) // 2)
    m_l = (idx >= -max_sb) & (idx <= -10)
    m_r = (idx >= 10) & (idx <= max_sb)
    slope = (exact_median_1d(y[m_r]) - exact_median_1d(y[m_l])) / (
        exact_median_1d(idx[m_r].astype(np.float64)) - exact_median_1d(idx[m_l].astype(np.float64))
    )
    intercept = exact_median_1d(y[m_l | m_r] - slope * idx[m_l | m_r])
    det = y - (intercept + slope * idx)
    mad_sb = exact_mad_1d(det[m_l | m_r])
    if not math.isfinite(mad_sb) or mad_sb <= 0:
        return {"usable": False}

    r_eff = effective_resolving_power(cfg, target_wave_a)
    sig_a = target_wave_a / (r_eff * FWHM_FACTOR)
    core_sl = slice(max(0, k_loc - 6), min(len(w), k_loc + 7))
    g = np.exp(-0.5 * ((w[core_sl] - target_wave_a) / sig_a) ** 2)
    gg = float(g @ g)
    amp_rel = max(0.0, float(det[core_sl] @ g) / gg)
    snr_native = amp_rel / mad_sb

    template_dip_frac = 0.0
    if r_ref_clean is not None and amp_rel > 0.0:
        dv = C_KMS * (w - target_wave_a) / target_wave_a
        sig_v = C_KMS / (r_eff * FWHM_FACTOR)
        ns_l = (dv >= -10.0 * sig_v) & (dv <= -4.0 * sig_v)
        ns_r = (dv >= 4.0 * sig_v) & (dv <= 10.0 * sig_v)
        if int(ns_l.sum()) >= 2 and int(ns_r.sum()) >= 2:
            neg_t = -scale * r_ref_clean
            slp_nt = (exact_median_1d(neg_t[ns_r]) - exact_median_1d(neg_t[ns_l])) / (
                exact_median_1d(dv[ns_r]) - exact_median_1d(dv[ns_l])
            )
            icp_nt = exact_median_1d(neg_t[ns_l | ns_r] - slp_nt * dv[ns_l | ns_r])
            det_nt = neg_t - (icp_nt + slp_nt * dv)
            c_nt = np.abs(dv) <= 3.0 * sig_v
            g_nt = np.exp(-0.5 * (dv[c_nt] / sig_v) ** 2)
            gg_nt = float(g_nt @ g_nt)
            amp_nt = max(0.0, float(det_nt[c_nt] @ g_nt) / gg_nt) if gg_nt > 0.0 else 0.0
            template_dip_frac = float(amp_nt / max(1e-12, amp_rel))

    search_sl = slice(k_loc - 2, k_loc + 3)
    k_pk = (k_loc - 2) + int(np.argmax(det[search_sl]))
    r_pk = float(det[k_pk])
    pos_7 = float(np.sum(np.maximum(0.0, det[k_pk - 3 : k_pk + 4])))
    eta_1px = (r_pk / pos_7) if (r_pk > 0 and pos_7 > 0) else 1.0
    left_w = float(det[k_pk - 1]) / r_pk if r_pk > 0 else -1.0
    right_w = float(det[k_pk + 1]) / r_pk if r_pk > 0 else -1.0
    min_wing = min(left_w, right_w)
    cont_snr = 1.0 / mad_sb if mad_sb > 0 else 0.0

    w11 = w[k_pk - 5 : k_pk + 6]
    d11 = det[k_pk - 5 : k_pk + 6]
    step_px_a = abs(float(exact_median_1d(np.diff(w[k_loc - 5 : k_loc + 6]))))
    best_cos11 = -1.0
    for iph in range(-4, 5):
        w_try = float(w[k_pk]) + (0.25 * iph) * step_px_a
        m11 = np.exp(-0.5 * ((w11 - w_try) / sig_a) ** 2)
        d_n = float(math.sqrt(max(0.0, float(d11 @ d11))))
        m_n = float(math.sqrt(float(m11 @ m11)))
        if d_n > 0.0 and m_n > 0.0:
            c11 = float(d11 @ m11) / (d_n * m_n)
            if c11 > best_cos11:
                best_cos11 = c11

    side_avg = 0.5 * (max(0.0, float(det[k_pk - 1])) + max(0.0, float(det[k_pk + 1])))
    expected_side_1 = float(math.exp(-0.5 * (step_px_a / sig_a) ** 2))
    obs_hot_ratio = (r_pk / max(1e-6 * abs(r_pk) + 1e-12, side_avg)) if (r_pk > 0 and side_avg > 0) else 99.0
    ipc_hotpx_ratio = obs_hot_ratio * expected_side_1
    far_wing_ratio = (
        0.25 * float(det[k_pk - 4] + det[k_pk - 3] + det[k_pk + 3] + det[k_pk + 4]) / r_pk
        if r_pk > 0
        else 99.0
    )

    return {
        "usable": True,
        "local_index": k_loc,
        "peak_local_index": k_pk,
        "continuum_adu": float(cont_adu),
        "continuum_snr": float(cont_snr),
        "native_fn_pk3": native_fn_pk3,
        "template_dip_frac": float(template_dip_frac),
        "native_amp_rel": float(amp_rel),
        "native_amp_adu": float(amp_rel * cont_adu),
        "native_snr": float(snr_native),
        "eta_1px": float(eta_1px),
        "min_wing_ratio": float(min_wing),
        "cos_1d_11px": float(best_cos11),
        "ipc_hotpx_ratio": float(ipc_hotpx_ratio),
        "far_wing_34_ratio": float(far_wing_ratio),
    }


def evaluate_gates_g3_g4_g5_v42(
    order_patches: list[dict[str, Any]],
    dpr_or_calsel: str,
    channel: str,
    star_rest_a: float | None,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    inst = cfg.get("instrument", "")
    # Gate G3_V42: Optical/NIR stellar chromospheric or nebular emission rejection
    if star_rest_a is not None:
        r_eff = effective_resolving_power(cfg, float(star_rest_a))
        tol_a = max(1.0, 2.5 * (float(star_rest_a) / r_eff))
        best_line = min(STELLAR_OPT_NIR_EMISSION_A, key=lambda ch: abs(float(star_rest_a) - float(ch["wave_A"])))
        if abs(float(star_rest_a) - float(best_line["wave_A"])) <= tol_a:
            return {
                "g3_pass": False,
                "g4_pass": False,
                "g5_pass": False,
                "g3_reason": f"CHROMO_EMISSION_{best_line['name']}",
                "g4_reason": "SKIPPED",
                "g5_reason": "SKIPPED",
            }

    if not order_patches:
        return {
            "g3_pass": False,
            "g4_pass": False,
            "g5_pass": False,
            "g3_reason": "NO_ORDER_PATCHES",
            "g4_reason": "NO_ORDER_PATCHES",
            "g5_reason": "NO_ORDER_PATCHES",
        }

    evs = []
    for p in order_patches:
        ev = evaluate_native_order_patch(
            np.asarray(p["wave"], dtype=np.float64),
            np.asarray(p["flux_a"], dtype=np.float64),
            np.asarray(p["ref_norm_a"], dtype=np.float64) if p.get("ref_norm_a") is not None else None,
            float(p["target_wave_a"]),
            cfg,
            err_ord_win=np.asarray(p["err_a"], dtype=np.float64) if p.get("err_a") is not None else None,
        )
        ev["patch"] = p
        evs.append(ev)

    usable = [e for e in evs if e.get("usable")]
    if not usable:
        return {
            "g3_pass": True,
            "g4_pass": False,
            "g5_pass": False,
            "g3_reason": "PASS",
            "g4_reason": "NO_USABLE_PATCH",
            "g5_reason": "SKIPPED",
        }

    prim = max(usable, key=lambda e: e["native_snr"])
    p_meta = prim["patch"]
    kp_abs = int(p_meta["native_pixel"]) + (int(prim["peak_local_index"]) - int(prim["local_index"]))
    common_meta = {
        "primary_order": int(p_meta["order"]),
        "primary_native_px": kp_abs,
        "primary_native_fn_pk3": float(prim["native_fn_pk3"]),
        "primary_eta_1px": float(prim["eta_1px"]),
        "cos_1d_11px": float(prim["cos_1d_11px"]),
        "ipc_hotpx_ratio": float(prim["ipc_hotpx_ratio"]),
        "far_wing_34_ratio": float(prim["far_wing_34_ratio"]),
    }

    if prim["native_fn_pk3"] < cfg["supraphotospheric_min_fn_pk3"]:
        return {**common_meta, "g3_pass": True, "g4_pass": False, "g5_pass": False, "g3_reason": "PASS", "g4_reason": "G1_NATIVE_SUBCONTINUUM", "g5_reason": "SKIPPED"}

    if prim["continuum_snr"] < cfg["g4_min_continuum_snr"]:
        return {**common_meta, "g3_pass": True, "g4_pass": False, "g5_pass": False, "g3_reason": "PASS", "g4_reason": "LOW_CONTINUUM_SNR", "g5_reason": "SKIPPED"}

    if prim["template_dip_frac"] > cfg["g4_max_template_dip_frac"]:
        return {**common_meta, "g3_pass": True, "g4_pass": False, "g5_pass": False, "g3_reason": "PASS", "g4_reason": "G3_V42_TEMPLATE_ABSORPTION_LEAK", "g5_reason": "SKIPPED"}

    # G4_V42: ESO fatal QUAL check + X-shooter simultaneous multi-arm dichroic coincidence
    dq = p_meta.get("dq")
    if dq is not None:
        kl = int(prim["local_index"])
        core_dq = 0
        for dq_val in dq[max(0, kl - 1) : min(len(dq), kl + 2)]:
            core_dq |= int(dq_val)
        if core_dq != 0:
            return {**common_meta, "g3_pass": True, "g4_pass": False, "g5_pass": False, "g3_reason": "PASS", "g4_reason": "ESO_FATAL_QUAL_ARTIFACT", "g5_reason": "SKIPPED"}

    if inst == "ESO_XSHOOTER_3ARM" and len(order_patches) >= 2:
        p_amp = max(1e-30, prim["native_amp_adu"])
        coinc = [
            e for e in usable
            if e["native_snr"] >= cfg["xshooter_dual_min_snr"] and 0.22 <= (e["native_amp_adu"] / p_amp) <= 4.5
        ]
        if len(coinc) < 2:
            return {**common_meta, "g3_pass": True, "g4_pass": False, "g5_pass": False, "g3_reason": "PASS", "g4_reason": "XSHOOTER_SINGLE_ARM_DETECTOR_ARTIFACT", "g5_reason": "SKIPPED"}

    # G5 morphological & PSF verification
    g5_ok = (
        prim["native_snr"] >= cfg["g5_min_native_snr"]
        and prim["eta_1px"] <= cfg["g5_eta_1px_max"]
        and prim["min_wing_ratio"] >= cfg["g5_min_wing_ratio"]
        and prim["ipc_hotpx_ratio"] <= cfg["g5_ipc_hotpx_ratio_max"]
        and prim["far_wing_34_ratio"] <= cfg["g5_far_wing_34_max"]
        and prim["cos_1d_11px"] >= cfg["g5_cos_1d_11px_min"]
    )
    if not g5_ok:
        if prim["ipc_hotpx_ratio"] > cfg["g5_ipc_hotpx_ratio_max"] or prim["eta_1px"] > cfg["g5_eta_1px_max"] or prim["min_wing_ratio"] < cfg["g5_min_wing_ratio"]:
            r5 = "G5_HOT_PIXEL_OR_COSMIC_RAY"
        elif prim["far_wing_34_ratio"] > cfg["g5_far_wing_34_max"]:
            r5 = "G5_BROAD_EMISSION_PLATEAU"
        else:
            r5 = "G5_LSF_SHAPE_MISMATCH"
        return {**common_meta, "g3_pass": True, "g4_pass": True, "g5_pass": False, "g3_reason": "PASS", "g4_reason": "PASS", "g5_reason": r5}

    return {**common_meta, "g3_pass": True, "g4_pass": True, "g5_pass": True, "g3_reason": "PASS", "g4_reason": "PASS", "g5_reason": "PASS"}


def evaluate_gate_g6_v35_dense(
    target_star: str,
    topo_wave_a: float,
    primary_order: int | None,
    primary_native_px: int | None,
    target_vshift_kms: float,
    dense_atlas: list[dict[str, Any]],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    tol_kms = float(cfg["g6_topo_tol_kms"])
    min_bs = float(cfg["g6_min_berv_shift_kms"])
    coincident_stars = set()
    same_star_hits = 0
    for rec in dense_atlas:
        dv = abs(C_KMS * (topo_wave_a - float(rec["topo_wave_a"])) / max(1.0, topo_wave_a))
        if dv <= tol_kms:
            st_r = rec["star"]
            if st_r == target_star:
                same_star_hits += 1
            elif target_vshift_kms >= min_bs:
                coincident_stars.add(st_r)
    g6_pass = (len(coincident_stars) < int(cfg["g6_min_diff_stars"])) and (same_star_hits == 0)
    return {
        "g6_v35_pass": bool(g6_pass),
        "g6_v35_coincident_total_stars": len(coincident_stars),
        "g6_v35_same_star_hits": same_star_hits,
    }


def evaluate_gate_g6_v36_sparse(
    target_star: str,
    target_dp_id: str,
    target_berv_kms: float,
    topo_wave_a: float,
    primary_order: int | None,
    primary_native_px: int | None,
    target_vshift_kms: float,
    sparse_atlas: list[dict[str, Any]],
    cfg: dict[str, Any],
    channel: str = "T",
) -> dict[str, Any]:
    tol_kms = float(cfg["g6_topo_tol_kms"])
    px_tol = float(cfg["g6_px_tol"])
    diff_stars: set[str] = set()
    same_star_hits = 0
    for rec in sparse_atlas:
        if rec["dp_id"] == target_dp_id:
            continue
        dv = abs(C_KMS * (topo_wave_a - float(rec["topo_wave_a"])) / max(1.0, topo_wave_a))
        px_match = (
            primary_order is not None
            and primary_native_px is not None
            and rec.get("native_order") == primary_order
            and abs(float(rec.get("native_px", -9999)) - float(primary_native_px)) <= px_tol
        )
        if dv <= tol_kms or px_match:
            if rec["star"] == target_star:
                if abs(target_berv_kms - float(rec["berv_kms"])) >= float(cfg["g6_min_berv_shift_kms"]):
                    same_star_hits += 1
            else:
                diff_stars.add(rec["star"])

    if len(diff_stars) >= int(cfg["g6_min_diff_stars"]):
        reason, ok = "STATIONARY_TOPO_MULTI_STAR", False
    elif same_star_hits >= 1 and channel in ("T", "P"):
        reason, ok = "SAME_STAR_STATIONARY_ACROSS_BERV", False
    else:
        reason, ok = "PASS", True
    return {
        "g6_pass": ok,
        "g6_coincident_total_stars": len(diff_stars),
        "g6_same_star_stationary_hits": same_star_hits,
        "g6_reason": reason,
    }


# ---------------------------------------------------------------------------
# Step 5: Frequency-Comb Search (COMB_V4 and COMB_V4_1)
# ---------------------------------------------------------------------------

def _scan_comb_core(
    wave_rest: np.ndarray,
    y_rest: np.ndarray,
    sigma_rest: np.ndarray,
    fn_rest: np.ndarray,
    recon_rest: np.ndarray,
    sky_mask: np.ndarray,
    y_topo: np.ndarray,
    sigma_topo: np.ndarray,
    windows: list[dict[str, Any]],
    allowed_bands: list[str],
    cfg: dict[str, Any],
    enforce_v41_vetoes: bool,
) -> tuple[list[dict[str, Any]], int]:
    from scipy.ndimage import maximum_filter1d

    w = np.asarray(wave_rest, dtype=np.float64)
    yr = np.asarray(y_rest, dtype=np.float64)
    sr = np.maximum(1e-5, np.asarray(sigma_rest, dtype=np.float64))
    fn = np.where(np.isfinite(fn_rest), np.asarray(fn_rest, dtype=np.float64), 1.0)
    rc = np.where(np.isfinite(recon_rest), np.asarray(recon_rest, dtype=np.float64), 1.0)
    yt = np.asarray(y_topo, dtype=np.float64)
    st = np.maximum(1e-5, np.asarray(sigma_topo, dtype=np.float64))

    fin_r = np.isfinite(w) & np.isfinite(yr) & (~sky_mask)
    if int(fin_r.sum()) < 80:
        return [], 0

    step_a = float(exact_median_1d(np.diff(w)))
    snr_r = np.where(fin_r, yr / sr, 0.0)
    snr_t = np.where(np.isfinite(yt), yt / st, 0.0)
    n_teeth = int(cfg["comb_n_teeth"])
    t_min = float(cfg["comb_tooth_snr_min"])
    s_min = float(cfg["comb_sum_snr_min"])
    min_q = int(cfg["comb_min_qualifying_teeth"])
    max_crowd = float(cfg["comb_max_off_tooth_crowding"])
    min_it = float(cfg["comb_min_intertooth_ratio"])
    min_anti = float(cfg["comb_min_topo_anti_ratio"])
    min_fn = float(cfg["comb_min_fn_pk3"])
    k_idx = np.arange(n_teeth, dtype=np.float64)

    raw_hits: list[dict[str, Any]] = []
    searched_configs = 0

    for win in windows:
        if win["band"] not in allowed_bands:
            continue
        w_lo, w_hi = float(win["lo_a"]), float(win["hi_a"])
        nu_hi = C_ANGSTROM_GHZ / w_lo
        nu_lo = C_ANGSTROM_GHZ / w_hi
        in_w = (w >= w_lo) & (w <= w_hi)
        if int(np.sum(fin_r & in_w)) < 80:
            continue

        w_mid = 0.5 * (w_lo + w_hi)
        sig_a_mid = w_mid / (effective_resolving_power(cfg, w_mid) * FWHM_FACTOR)
        hw_core = max(1, int(round(0.8 * sig_a_mid / max(1e-6, step_a))))
        hw_excl = max(3, int(round(2.8 * sig_a_mid / max(1e-6, step_a))))
        win_margin_a = max(3.0, 4.0 * sig_a_mid)

        snr_cmax = maximum_filter1d(snr_r, size=2 * hw_core + 1, mode="constant", cval=0.0)
        fn_cmax = maximum_filter1d(fn, size=2 * hw_core + 1, mode="constant", cval=1.0)
        topo_cmax = maximum_filter1d(snr_t, size=2 * (hw_core + 1) + 1, mode="constant", cval=0.0)
        rc_cmin = -maximum_filter1d(-rc, size=2 * hw_core + 1, mode="constant", cval=-1.0)
        fin_any = maximum_filter1d(fin_r.astype(np.int8), size=2 * hw_core + 1, mode="constant", cval=0) > 0

        for dnu in cfg["comb_spacings_ghz"]:
            span_nu = (n_teeth - 1) * float(dnu)
            step_nu = min(0.25 * float(dnu), float(cfg.get("comb_step_ghz", 10.0)))
            nu_starts = np.arange(nu_lo, nu_hi - span_nu + 1e-6, step_nu, dtype=np.float64)
            searched_configs += int(len(nu_starts))
            if len(nu_starts) == 0:
                continue

            nu_mat = nu_starts[:, None] + float(dnu) * k_idx[None, :]
            w_mat = C_ANGSTROM_GHZ / nu_mat
            idx_mat = np.searchsorted(w, w_mat)
            in_b = np.all((idx_mat > hw_excl + 2) & (idx_mat < len(w) - hw_excl - 3), axis=1)
            safe_idx = np.where(in_b[:, None], idx_mat, hw_excl + 2)
            ok_fin = in_b & np.all(fin_any[safe_idx], axis=1)

            t_snrs_mat = snr_cmax[safe_idx]
            n_q_arr = (t_snrs_mat >= t_min).sum(axis=1)
            s_comb_arr = np.maximum(0.0, t_snrs_mat).sum(axis=1)
            pass_prelim = ok_fin & (n_q_arr >= min_q) & (s_comb_arr >= s_min)

            for row_i in np.flatnonzero(pass_prelim):
                nu0 = float(nu_starts[row_i])
                idxs = idx_mat[row_i]
                w_teeth = w_mat[row_i]
                t_snrs = t_snrs_mat[row_i]
                s_comb = float(s_comb_arr[row_i])
                n_q = int(n_q_arr[row_i])

                w_a_lo, w_a_hi = float(np.min(w_teeth)) - win_margin_a, float(np.max(w_teeth)) + win_margin_a
                m_win = (w >= w_a_lo) & (w <= w_a_hi) & fin_r
                nu_mids = nu0 + float(dnu) * (0.5 + np.arange(n_teeth - 1, dtype=np.float64))
                w_mids = C_ANGSTROM_GHZ / nu_mids
                mid_idxs = np.clip(np.searchsorted(w, w_mids), hw_excl + 1, len(w) - hw_excl - 2)
                mid_snrs = snr_cmax[mid_idxs]
                mean_t = float(np.mean(t_snrs))
                mean_mid = max(0.25, float(np.mean(mid_snrs))) if len(mid_snrs) else 0.5
                intertooth_ratio = mean_t / mean_mid

                m_bg = m_win.copy()
                for idx_t in idxs:
                    m_bg[max(0, int(idx_t) - hw_excl) : min(len(m_bg), int(idx_t) + hw_excl + 1)] = False
                off_crowd = float(np.mean(snr_r[m_bg] >= 2.0)) if int(m_bg.sum()) >= 10 else 0.0

                s_topo = max(1.0, float(np.maximum(0.0, topo_cmax[idxs]).sum()))
                topo_anti = s_comb / s_topo
                n_sup = int((fn_cmax[idxs] >= min_fn).sum())

                if enforce_v41_vetoes:
                    n_absorb = int((rc_cmin[idxs] < 0.85).sum())
                    if n_absorb >= 2:
                        continue
                    if n_sup < min_q or off_crowd > max_crowd or intertooth_ratio < min_it or topo_anti < min_anti:
                        continue

                raw_hits.append({
                    "band": win["band"],
                    "dnu_ghz": round(float(dnu), 3),
                    "nu0_ghz": round(float(nu0), 3),
                    "wave0_a": round(float(w_teeth[0]), 4),
                    "wave_end_a": round(float(w_teeth[-1]), 4),
                    "s_comb": round(s_comb, 3),
                    "topo_anti_ratio": round(topo_anti, 3),
                    "n_qualifying_teeth": n_q,
                    "off_tooth_crowding": round(off_crowd, 4),
                    "intertooth_ratio": round(intertooth_ratio, 3),
                })

    raw_hits.sort(key=lambda r: float(r["s_comb"]), reverse=True)
    dedup: list[dict[str, Any]] = []
    for h in raw_hits:
        if any(
            p["band"] == h["band"] and abs(p["dnu_ghz"] - h["dnu_ghz"]) < 1e-3 and abs(p["nu0_ghz"] - h["nu0_ghz"]) <= 0.6 * h["dnu_ghz"]
            for p in dedup
        ):
            continue
        dedup.append(h)
    return dedup, searched_configs


def scan_frequency_comb_v4(
    wave_rest: np.ndarray,
    y_rest: np.ndarray,
    sigma_rest: np.ndarray,
    fn_rest: np.ndarray,
    recon_rest: np.ndarray,
    sky_mask: np.ndarray,
    y_topo: np.ndarray,
    sigma_topo: np.ndarray,
    windows: list[dict[str, Any]],
    allowed_bands: list[str],
    cfg: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    return _scan_comb_core(wave_rest, y_rest, sigma_rest, fn_rest, recon_rest, sky_mask, y_topo, sigma_topo, windows, allowed_bands, cfg, False)


def scan_frequency_comb_v4_1(
    wave_rest: np.ndarray,
    y_rest: np.ndarray,
    sigma_rest: np.ndarray,
    fn_rest: np.ndarray,
    recon_rest: np.ndarray,
    sky_mask: np.ndarray,
    y_topo: np.ndarray,
    sigma_topo: np.ndarray,
    windows: list[dict[str, Any]],
    allowed_bands: list[str],
    cfg: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    return _scan_comb_core(wave_rest, y_rest, sigma_rest, fn_rest, recon_rest, sky_mask, y_topo, sigma_topo, windows, allowed_bands, cfg, True)


# ---------------------------------------------------------------------------
# Step 6: 10-Meter Transmitter Optical-Beam Upper Limits
# ---------------------------------------------------------------------------

def compute_photon_beam_upper_limit(
    wave_a: float,
    amp_rel_lim: float,
    teff_k: float,
    dist_pc: float,
    stellar_radius_rsun: float,
    radiometric_anchor: str,
    resolving_power: float,
    direct_flam_cgs: float | None = None,
    phot_g_mag: float | None = None,
    h_mag: float | None = None,
) -> dict[str, float]:
    r_eff = float(resolving_power)
    if direct_flam_cgs is not None and math.isfinite(float(direct_flam_cgs)) and float(direct_flam_cgs) > 0.0:
        cont_flam_cgs = float(direct_flam_cgs)
    elif radiometric_anchor == "2MASS_H_PLANCK_CGS" and h_mag is not None and math.isfinite(float(h_mag)):
        cont_flam_cgs = twomass_h_planck_flam_cgs(float(wave_a), float(h_mag), float(teff_k))
    elif phot_g_mag is not None and math.isfinite(float(phot_g_mag)):
        cont_flam_cgs = gaia_g_planck_flam_cgs(float(wave_a), float(phot_g_mag), float(teff_k))
    else:
        lam_m = float(wave_a) * 1e-10
        x = (H_PLANCK * C_SI) / (lam_m * K_BOLTZ * float(teff_k))
        b_lam_si = (2.0 * H_PLANCK * C_SI * C_SI) / ((lam_m ** 5) * math.expm1(min(700.0, x)))
        f_surf_cgs_a = math.pi * b_lam_si * 1e-7
        dil = (float(stellar_radius_rsun) * SOLAR_RADIUS_CM / (float(dist_pc) * PC_CM)) ** 2
        cont_flam_cgs = f_surf_cgs_a * dil

    fwhm_a = float(wave_a) / r_eff
    ew_a = math.sqrt(math.pi / (4.0 * math.log(2.0))) * float(amp_rel_lim) * fwhm_a
    flux_cgs = cont_flam_cgs * ew_a
    d_cm = float(dist_pc) * PC_CM
    l_iso_w = 4.0 * math.pi * (d_cm * d_cm) * flux_cgs * 1e-7
    theta = (math.pi * 10.0) / (float(wave_a) * 1e-10)
    p_w = l_iso_w / (theta * theta)
    return {
        "fwhm_lsf_a": fwhm_a,
        "ew_lim_mA": ew_a * 1000.0,
        "continuum_flam_cgs": cont_flam_cgs,
        "flux_lim_erg_cm2_s": flux_cgs,
        "l_iso_mw": l_iso_w / 1e6,
        "p_beam_10m_w": p_w,
        "p_beam_10m_kw": p_w / 1000.0,
    }


# ===========================================================================
# TECHNOSIGNATURE V5.0 ENGINES
# ===========================================================================


# ---------------------------------------------------------------------------
# Engine 1: Masked Inexact-ALM Robust PCA + Leave-One-Star-Out (LOSO)
# ---------------------------------------------------------------------------

def decompose_rpca_block(
    X: np.ndarray,
    mask_obs: np.ndarray,
    lam: float | None = None,
    max_iter: int = 35,
    tol: float = 1e-5,
) -> tuple[np.ndarray, np.ndarray]:
    """Decompose observed-masked spectral block ``X`` into ``L + S`` via Inexact ALM RPCA."""
    X_arr = np.asarray(X, dtype=np.float64)
    mask = np.asarray(mask_obs, dtype=bool) & np.isfinite(X_arr)
    n_rows, n_cols = X_arr.shape
    if n_rows == 0 or n_cols == 0 or not np.any(mask):
        zeros = np.zeros_like(X_arr, dtype=np.float64)
        return zeros, zeros.copy()

    lam_eff = float(lam) if lam is not None else 1.0 / math.sqrt(float(max(n_rows, n_cols)))
    X_zero = np.where(mask, X_arr, 0.0)

    # Spectral & infinity norms for Candes+2011 / Lin+2010 ALM step scaling
    try:
        s_top = float(np.linalg.svd(X_zero, compute_uv=False)[0])
    except np.linalg.LinAlgError:
        s_top = float(np.linalg.norm(X_zero))
    norm_inf = float(np.max(np.abs(X_zero))) / max(lam_eff, 1e-12)
    norm_dual = max(s_top, norm_inf, 1e-12)
    norm_x = max(float(np.linalg.norm(X_zero)), 1e-12)

    Y = X_zero / norm_dual
    mu = 1.25 / max(s_top, 1e-12)
    mu_bar = mu * 1e7
    rho = 1.5

    L = np.zeros_like(X_zero)
    S = np.zeros_like(X_zero)

    for _ in range(int(max_iter)):
        # Matrix completion at missing entries keeps incomplete coverage out of S
        D_cur = np.where(mask, X_zero, L + S)

        inv_mu = 1.0 / mu
        try:
            U, sig, Vt = np.linalg.svd(D_cur - S + inv_mu * Y, full_matrices=False)
            sig_thr = np.maximum(0.0, sig - inv_mu)
            L = (U * sig_thr[None, :]) @ Vt
        except np.linalg.LinAlgError:
            pass

        temp_S = D_cur - L + inv_mu * Y
        thr_S = lam_eff * inv_mu
        S_raw = np.sign(temp_S) * np.maximum(0.0, np.abs(temp_S) - thr_S)
        S = np.where(mask, S_raw, 0.0)

        Z = np.where(mask, X_zero - L - S, 0.0)
        Y = Y + mu * Z
        mu = min(mu * rho, mu_bar)

        if float(np.linalg.norm(Z)) / norm_x < tol:
            break

    return L, S


def _compute_rolling_mad_1d(vals: np.ndarray, valid_mask: np.ndarray, win_bins: int = 512) -> np.ndarray:
    """Compute rolling local robust MAD noise scale with global floor across 1D residuals."""
    n = len(vals)
    out = np.full(n, np.nan, dtype=np.float64)
    v_idx = np.where(valid_mask & np.isfinite(vals))[0]
    if len(v_idx) < 8:
        return out
    global_med = float(np.median(vals[v_idx]))
    global_mad = max(1e-6, MAD_NORM * float(np.median(np.abs(vals[v_idx] - global_med))))

    half = max(32, int(win_bins) // 2)
    step = max(16, half // 2)
    centers: list[float] = []
    mads: list[float] = []
    for c in range(0, n, step):
        lo = max(0, c - half)
        hi = min(n, c + half + 1)
        m_sub = valid_mask[lo:hi] & np.isfinite(vals[lo:hi])
        if np.sum(m_sub) >= 16:
            seg = vals[lo:hi][m_sub]
            med = float(np.median(seg))
            mad = MAD_NORM * float(np.median(np.abs(seg - med)))
            centers.append(float(c))
            mads.append(max(0.25 * global_mad, mad, 1e-6))
    if not centers:
        out[v_idx] = global_mad
        return out
    if len(centers) == 1:
        out[v_idx] = mads[0]
        return out
    grid_x = np.arange(n, dtype=np.float64)
    interp_mad = np.interp(grid_x, np.asarray(centers, dtype=np.float64), np.asarray(mads, dtype=np.float64))
    out[v_idx] = np.maximum(0.25 * global_mad, interp_mad[v_idx])
    return out


def run_cohort_rpca_v50(
    wave_rest: np.ndarray,
    star_norm_matrix: np.ndarray,
    teffs: np.ndarray | None = None,
    block_len: int = 2048,
    overlap: int = 128,
    loso_rank: int = 8,
) -> dict[str, np.ndarray]:
    """
    Run overlapping-block masked RPCA + Leave-One-Star-Out (LOSO) projection on a cohort.

    Inputs:
      wave_rest: shape ``(n_wave,)`` uniform rest-frame wavelength grid (A).
      star_norm_matrix: shape ``(n_stars, n_wave)`` continuum-normalized spectra (~1.0 or ~0.0;
          ``NaN`` where a star lacks spectral coverage).
      teffs: optional shape ``(n_stars,)`` effective temperatures (K) used for mild peer weighting
          in the LOSO manifold basis without isolating outlier spectral types.
    Returns dict with ``L_mat``, ``S_mat``, ``L_loso``, ``S_loso``, ``z_rpca``, ``coverage_count``.
    """
    wave = np.asarray(wave_rest, dtype=np.float64)
    M = np.asarray(star_norm_matrix, dtype=np.float64)
    if M.ndim != 2:
        raise ValueError("star_norm_matrix must be 2D (n_stars, n_wave)")
    n_stars, n_wave = M.shape
    mask_obs = np.isfinite(M)
    cov_count = np.sum(mask_obs, axis=0).astype(np.int32)
    valid_cohort = mask_obs & (cov_count[None, :] >= 2)

    # Subtract per-star median baseline so matrix completion around gaps stays centered at 0
    row_base = np.zeros(n_stars, dtype=np.float64)
    M_centered = np.zeros_like(M, dtype=np.float64)
    for i in range(n_stars):
        vi = mask_obs[i]
        if np.any(vi):
            med_i = float(np.median(M[i, vi]))
            row_base[i] = med_i
            M_centered[i, vi] = M[i, vi] - med_i

    teff_arr: np.ndarray | None = None
    if teffs is not None and len(teffs) == n_stars:
        teff_arr = np.asarray(teffs, dtype=np.float64)

    blk = max(64, int(block_len))
    ov = max(0, min(blk // 2, int(overlap)))
    if n_wave <= blk:
        starts = [0]
        eff_blks = [n_wave]
    else:
        stride = max(32, blk - ov)
        starts = list(range(0, n_wave - blk, stride))
        starts.append(n_wave - blk)
        eff_blks = [blk] * len(starts)

    L_acc = np.zeros_like(M_centered)
    S_acc = np.zeros_like(M_centered)
    L_loso_acc = np.zeros_like(M_centered)
    S_loso_acc = np.zeros_like(M_centered)
    W_acc = np.zeros_like(M_centered)

    for b_idx, (st, bl) in enumerate(zip(starts, eff_blks)):
        ed = st + bl
        X_b = M_centered[:, st:ed]
        m_b = mask_obs[:, st:ed]

        # Smooth triangular tent blend on interior overlaps, flat 1 at outer survey edges
        w_1d = np.ones(bl, dtype=np.float64)
        if ov > 0 and len(starts) > 1:
            ramp = np.linspace(0.05, 1.0, ov, dtype=np.float64)
            if b_idx > 0:
                w_1d[:ov] = np.minimum(w_1d[:ov], ramp)
            if b_idx < len(starts) - 1:
                w_1d[-ov:] = np.minimum(w_1d[-ov:], ramp[::-1])

        L_b, S_b = decompose_rpca_block(X_b, m_b)
        L_loso_b = np.zeros_like(X_b)
        S_loso_b = np.zeros_like(X_b)

        for i in range(n_stars):
            m_i = m_b[i]
            if not np.any(m_i):
                continue
            if n_stars < 2:
                S_loso_b[i, m_i] = X_b[i, m_i]
                continue

            other_rows = np.arange(n_stars) != i
            L_oth = L_b[other_rows]
            m_oth = m_b[other_rows]
            col_has_other = np.any(m_oth, axis=0)
            use_i = m_i & col_has_other
            if int(np.sum(use_i)) < 4:
                continue

            if teff_arr is not None and math.isfinite(float(teff_arr[i])):
                dT = teff_arr[other_rows] - float(teff_arr[i])
                w_t = np.where(
                    np.isfinite(dT),
                    0.25 + 0.75 * np.exp(-0.5 * (dT / 1500.0) ** 2),
                    0.5,
                )
            else:
                w_t = np.ones(n_stars - 1, dtype=np.float64)

            L_weighted = L_oth * w_t[:, None]
            try:
                _, _, Vt_oth = np.linalg.svd(L_weighted, full_matrices=False)
            except np.linalg.LinAlgError:
                S_loso_b[i, use_i] = X_b[i, use_i]
                continue

            k_eff = max(1, min(int(loso_rank), Vt_oth.shape[0]))
            V_k = Vt_oth[:k_eff, :]
            V_obs = V_k[:, use_i]
            # Masked ridge solve avoids edge distortion across instrument gaps
            gram = V_obs @ V_obs.T + 1e-4 * np.eye(k_eff, dtype=np.float64)
            rhs = V_obs @ X_b[i, use_i]
            try:
                alpha = np.linalg.solve(gram, rhs)
                recon = alpha @ V_k
            except np.linalg.LinAlgError:
                recon = np.zeros(bl, dtype=np.float64)

            L_loso_b[i, use_i] = recon[use_i]
            S_loso_b[i, use_i] = X_b[i, use_i] - recon[use_i]

        w_b = w_1d[None, :] * m_b
        L_acc[:, st:ed] += L_b * w_b
        S_acc[:, st:ed] += S_b * w_b
        L_loso_acc[:, st:ed] += L_loso_b * w_b
        S_loso_acc[:, st:ed] += S_loso_b * w_b
        W_acc[:, st:ed] += w_b

    safe_w = W_acc > 0.0
    L_out = np.full_like(M, np.nan)
    S_out = np.full_like(M, np.nan)
    L_loso_out = np.full_like(M, np.nan)
    S_loso_out = np.full_like(M, np.nan)
    z_rpca = np.full_like(M, np.nan)

    L_out[safe_w] = L_acc[safe_w] / W_acc[safe_w]
    S_out[safe_w] = S_acc[safe_w] / W_acc[safe_w]
    L_loso_out[safe_w] = L_loso_acc[safe_w] / W_acc[safe_w]
    S_loso_out[safe_w] = S_loso_acc[safe_w] / W_acc[safe_w]

    # Restore baseline into L so M ~= L + S holds on observed bins
    L_out[mask_obs] += np.broadcast_to(row_base[:, None], M.shape)[mask_obs]
    L_loso_out[valid_cohort] += np.broadcast_to(row_base[:, None], M.shape)[valid_cohort]
    L_loso_out[~valid_cohort] = np.nan
    S_loso_out[~valid_cohort] = np.nan
    S_out[~mask_obs] = np.nan

    for i in range(n_stars):
        vi = valid_cohort[i] & np.isfinite(S_loso_out[i])
        if int(np.sum(vi)) < 8:
            continue
        mad_arr = _compute_rolling_mad_1d(S_loso_out[i], vi, win_bins=max(128, min(1024, n_wave // 8)))
        ok_m = vi & np.isfinite(mad_arr) & (mad_arr > 0.0)
        z_rpca[i, ok_m] = S_loso_out[i, ok_m] / mad_arr[ok_m]

    return {
        "wave_rest": wave,
        "L_mat": L_out,
        "S_mat": S_out,
        "L_loso": L_loso_out,
        "S_loso": S_loso_out,
        "z_rpca": z_rpca,
        "coverage_count": cov_count,
    }


# ---------------------------------------------------------------------------
# Engine 2: Spectral Rarity Score & Gate G7_V50
# ---------------------------------------------------------------------------

def compute_spectral_rarity_score(
    wave_rest: np.ndarray,
    z_mat: np.ndarray,
    bervs: np.ndarray,
    star_idx: int,
    center_wave_a: float,
    sigma_v_kms: float,
    polarity: float = 1.0,
) -> dict[str, float]:
    """
    Compute empirical cohort spectral uniqueness across rest and topocentric frames.

    Inputs:
      bervs: effective observatory-to-rest velocity offset (``BERV - RV_star``, km/s)
          for each star row in ``z_mat``.
      polarity: ``+1.0`` for emission, ``-1.0`` for absorption, or ``0.0`` for unsigned ``|z|``.
    Formula:
      ``rarity_score = exp(-4.0 * f_rest) * exp(-6.0 * f_topo)`` where peer repeats are
      counted via matched-width unit-L2 Gaussian projection (preserving ``N(0, 1)`` scaling
      across ``1x..14x LSF``) with ``+-1.5 sigma`` local alignment tolerance at ``>= 3.5 sigma``.
    """
    w = np.asarray(wave_rest, dtype=np.float64)
    Z = np.asarray(z_mat, dtype=np.float64)
    v_arr = np.asarray(bervs, dtype=np.float64)
    n_stars = Z.shape[0]
    w0 = float(center_wave_a)
    sig_v = max(0.5, float(sigma_v_kms))

    diffs = np.diff(w)
    pos_diffs = diffs[diffs > 0.0]
    dw = float(np.median(pos_diffs)) if len(pos_diffs) > 0 else 0.03
    sig_a = max(dw, w0 * sig_v / C_KMS)
    half_win_a = 4.0 * sig_a
    offsets_a = (-1.5 * sig_a, -0.75 * sig_a, 0.0, 0.75 * sig_a, 1.5 * sig_a)

    def _peer_matched_z(row_j: int, wc0: float) -> tuple[bool, float]:
        lo = int(np.searchsorted(w, wc0 - half_win_a, side="left"))
        hi = int(np.searchsorted(w, wc0 + half_win_a, side="right"))
        if hi <= lo:
            return False, 0.0
        z_win = Z[row_j, lo:hi]
        w_win = w[lo:hi]
        fin = np.isfinite(z_win)
        if not np.any(np.abs(w_win[fin] - wc0) <= 2.5 * sig_a):
            return False, 0.0
        wf = w_win[fin]
        zf = z_win[fin]
        best_val = -1e9 if polarity != 0.0 else 0.0
        for off in offsets_a:
            g = np.exp(-0.5 * ((wf - (wc0 + off)) / sig_a) ** 2)
            ng = float(np.linalg.norm(g))
            if ng <= 1e-12:
                continue
            zm = float(np.dot(g, zf) / ng)
            score = abs(zm) if polarity == 0.0 else float(polarity) * zm
            if score > best_val:
                best_val = score
        return True, float(best_val)

    n_cover_rest = 0
    n_repeat_rest = 0
    n_cover_topo = 0
    n_repeat_topo = 0
    v_i = float(v_arr[star_idx]) if star_idx < len(v_arr) and math.isfinite(float(v_arr[star_idx])) else 0.0

    for j in range(n_stars):
        if j == star_idx:
            continue
        cov_r, z_r = _peer_matched_z(j, w0)
        if cov_r:
            n_cover_rest += 1
            if z_r >= 3.5:
                n_repeat_rest += 1

        v_j = float(v_arr[j]) if j < len(v_arr) and math.isfinite(float(v_arr[j])) else v_i
        if abs(v_j - v_i) >= 1.5:
            w_topo_j = w0 * (1.0 + (v_j - v_i) / C_KMS)
            cov_t, z_t = _peer_matched_z(j, w_topo_j)
            if cov_t:
                n_cover_topo += 1
                if z_t >= 3.5:
                    n_repeat_topo += 1

    f_rest = (n_repeat_rest / n_cover_rest) if n_cover_rest > 0 else 1.0
    f_topo = (n_repeat_topo / n_cover_topo) if n_cover_topo > 0 else 0.0
    rarity_score = math.exp(-4.0 * f_rest) * math.exp(-6.0 * f_topo)
    return {
        "f_rest": float(f_rest),
        "f_topo": float(f_topo),
        "rarity_score": float(rarity_score),
        "n_cover_rest": int(n_cover_rest),
        "n_repeat_rest": int(n_repeat_rest),
        "n_cover_topo": int(n_cover_topo),
        "n_repeat_topo": int(n_repeat_topo),
    }


def evaluate_gate_g7_v50(
    z_rpca: float,
    rarity_score: float,
    abs_mode: bool = False,
) -> dict[str, Any]:
    """V5.0 Gate G7: requires ``z_rpca >= 6.0`` (or ``|z|`` in agnostic mode) and ``rarity >= 0.65``."""
    z_raw = float(z_rpca)
    z_val = abs(z_raw) if abs_mode else z_raw
    r_val = float(rarity_score)
    z_ok = math.isfinite(z_val) and z_val >= float(BASE_V5_0_CONFIG["g7_min_z_rpca"])
    r_ok = math.isfinite(r_val) and r_val >= float(BASE_V5_0_CONFIG["g7_min_rarity_score"])
    passed = bool(z_ok and r_ok)
    if passed:
        reason = "PASS"
    elif not z_ok:
        reason = "G7_LOW_Z_RPCA"
    else:
        reason = "G7_LOW_RARITY"
    return {
        "g7_pass": passed,
        "z_rpca": z_raw,
        "rarity_score": r_val,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Engine 3: Dual-Polarity Agnostic Multi-Scale Matched Filter
# ---------------------------------------------------------------------------

def _is_masked_static_v50(
    wave_rest_arr: np.ndarray,
    cfg: dict[str, Any],
    v_obs_to_rest_kms: float,
) -> np.ndarray:
    """Mask static Paranal/La Silla/APO/LCO sky emission, OH lines, blackout windows, and chromospheric lines."""
    masked = np.zeros(len(wave_rest_arr), dtype=bool)
    shift_obs_to_rest = 1.0 + float(v_obs_to_rest_kms) / C_KMS
    inst = str(cfg.get("instrument", ""))
    if not inst.startswith("JWST_"):
        for line in GROUND_AIRGLOW_AND_TELLURIC_A:
            w_c = float(line["wave_A"]) * shift_obs_to_rest
            hw = max(0.8, w_c * float(line["half_width_kms"]) / C_KMS)
            masked |= np.abs(wave_rest_arr - w_c) <= hw
        for oh_vac_a in ROUSSELOT_OH_HBAND_VAC_A:
            w_c = float(oh_vac_a) * shift_obs_to_rest
            hw = max(1.0, w_c * 35.0 / C_KMS)
            masked |= np.abs(wave_rest_arr - w_c) <= hw
        for lo_a, hi_a in XSHOOTER_TELLURIC_BLACKOUT_A:
            masked |= (wave_rest_arr >= lo_a * shift_obs_to_rest) & (wave_rest_arr <= hi_a * shift_obs_to_rest)
    for ch in STELLAR_OPT_NIR_EMISSION_A:
        wc = float(ch["wave_A"])
        r_eff = effective_resolving_power(cfg, wc)
        tol_a = max(1.0, 2.5 * (wc / max(500.0, r_eff)))
        masked |= np.abs(wave_rest_arr - wc) <= tol_a
    return masked


def scan_agnostic_multiscale_v50(
    wave_rest: np.ndarray,
    resid_s: np.ndarray,
    star_idx: int,
    z_mat: np.ndarray,
    bervs: np.ndarray,
    cfg: dict[str, Any],
    scales_lsf: tuple[float, ...] = (2.0, 4.0, 8.0, 14.0),
) -> tuple[list[dict[str, Any]], int]:
    """
    Scan residuals with dual-polarity (+/-) Gaussian and flat-top boxcar-drift kernels.

    Scales span ``2, 4, 8, 14 x LSF``, vetoing known sky/telluric/chromospheric masks and
    requiring calibrated matched-filter ``|z_multi| >= 7.5`` and ``rarity_score >= 0.70``.
    """
    wave = np.asarray(wave_rest, dtype=np.float64)
    res = np.asarray(resid_s, dtype=np.float64)
    n_wave = len(wave)
    valid = np.isfinite(wave) & np.isfinite(res)
    if int(np.sum(valid)) < 128 or n_wave < 128:
        return [], 0

    dw = float(np.median(np.diff(wave)))
    if not math.isfinite(dw) or dw <= 0.0:
        return [], 0

    v_off = float(bervs[star_idx]) if star_idx < len(bervs) and math.isfinite(float(bervs[star_idx])) else 0.0
    static_veto = _is_masked_static_v50(wave, cfg, v_off)

    res_clean = np.where(valid, res, 0.0)
    mask_f = valid.astype(np.float64)

    min_abs_z = float(cfg.get("agnostic_min_abs_z", 7.5))
    min_rarity = float(cfg.get("agnostic_min_rarity_score", 0.70))

    # Process across smooth octave windows so LSF pixel width stays well calibrated across broad SEDs
    w_min = float(wave[valid][0])
    w_max = float(wave[valid][-1])
    octaves: list[tuple[float, float]] = []
    cur_lo = w_min
    while cur_lo < w_max:
        cur_hi = min(w_max + 1e-6, cur_lo * 1.55)
        octaves.append((cur_lo, cur_hi))
        cur_lo = cur_hi

    raw_peaks: list[dict[str, Any]] = []
    n_evals = 0

    for oct_lo, oct_hi in octaves:
        oct_sel = valid & (wave >= oct_lo) & (wave < oct_hi)
        if int(np.sum(oct_sel)) < 64:
            continue
        ref_w = 0.5 * (oct_lo + oct_hi)
        r_eff = effective_resolving_power(cfg, ref_w)
        lsf_sigma_a = ref_w / (max(500.0, r_eff) * FWHM_FACTOR)
        lsf_sigma_px = max(0.8, lsf_sigma_a / dw)

        i0 = max(0, int(np.searchsorted(wave, oct_lo, side="left")) - 160)
        i1 = min(n_wave, int(np.searchsorted(wave, oct_hi, side="right")) + 160)
        sub_res = res_clean[i0:i1]
        sub_mask = mask_f[i0:i1]
        sub_wave = wave[i0:i1]
        sub_valid = valid[i0:i1]

        for scale_lsf in scales_lsf:
            sig_px = float(scale_lsf) * lsf_sigma_px
            for kernel_name in ("gaussian", "boxcar_drift"):
                if kernel_name == "gaussian":
                    half_w = int(max(4, min(400, math.ceil(3.5 * sig_px))))
                    kx = np.arange(-half_w, half_w + 1, dtype=np.float64)
                    kern = np.exp(-0.5 * (kx / max(0.75, sig_px)) ** 2)
                    width_px = FWHM_FACTOR * sig_px
                else:
                    full_w = int(max(5, min(601, round(FWHM_FACTOR * sig_px))))
                    if full_w % 2 == 0:
                        full_w += 1
                    kern = np.ones(full_w, dtype=np.float64)
                    width_px = float(full_w)

                kern /= max(1e-12, float(np.linalg.norm(kern)))
                k_sq = kern * kern

                num = convolve1d(sub_res, kern, mode="constant", cval=0.0)
                den = np.sqrt(np.maximum(0.0, convolve1d(sub_mask, k_sq, mode="constant", cval=0.0)))
                resp = np.full_like(num, np.nan)
                ok_d = sub_valid & (den >= 0.45)
                resp[ok_d] = num[ok_d] / den[ok_d]

                if int(np.sum(ok_d)) < 32:
                    continue

                mad_loc = _compute_rolling_mad_1d(resp, ok_d, win_bins=max(256, 20 * len(kern)))
                z_loc = np.full_like(resp, np.nan)
                ok_z = ok_d & np.isfinite(mad_loc) & (mad_loc > 0.0)
                z_loc[ok_z] = resp[ok_z] / mad_loc[ok_z]

                cand_idx = np.where(
                    ok_z
                    & (sub_wave >= oct_lo)
                    & (sub_wave < oct_hi)
                    & (~static_veto[i0:i1])
                    & (np.abs(z_loc) >= min_abs_z)
                )[0]
                if len(cand_idx) == 0:
                    continue

                # Non-maximum suppression within +/- max(16, 3 * kernel width) bins
                nms_sep = max(16, int(round(3.0 * width_px)))
                order_idx = cand_idx[np.argsort(np.abs(z_loc[cand_idx]))[::-1]]
                taken = np.zeros(len(sub_wave), dtype=bool)
                for idx in order_idx:
                    if taken[idx]:
                        continue
                    n_evals += 1
                    lo_t = max(0, idx - nms_sep)
                    hi_t = min(len(sub_wave), idx + nms_sep + 1)
                    taken[lo_t:hi_t] = True

                    w_pk = float(sub_wave[idx])
                    z_pk = float(z_loc[idx])
                    fwhm_a = max(dw, width_px * dw)
                    raw_peaks.append({
                        "wave_rest_a": w_pk,
                        "z_multi": z_pk,
                        "polarity": "+" if z_pk >= 0.0 else "-",
                        "scale_lsf": float(scale_lsf),
                        "kernel": kernel_name,
                        "fwhm_a": fwhm_a,
                        "sigma_v_kms": (C_KMS / max(500.0, effective_resolving_power(cfg, w_pk) * FWHM_FACTOR)) * float(scale_lsf),
                    })

    # Deduplicate overlapping peaks across scales/kernels keeping strongest |z_multi|
    raw_peaks.sort(key=lambda d: abs(float(d["z_multi"])), reverse=True)
    dedup: list[dict[str, Any]] = []
    for pk in raw_peaks:
        w_p = float(pk["wave_rest_a"])
        tol_dedup = max(0.5, 0.75 * float(pk["fwhm_a"]))
        if any(abs(w_p - float(d["wave_rest_a"])) <= tol_dedup for d in dedup):
            continue
        dedup.append(pk)

    survivors: list[dict[str, Any]] = []
    for pk in dedup:
        pol_val = 1.0 if pk["polarity"] == "+" else -1.0
        rar = compute_spectral_rarity_score(
            wave,
            z_mat,
            bervs,
            star_idx,
            float(pk["wave_rest_a"]),
            float(pk["sigma_v_kms"]),
            polarity=pol_val,
        )
        if rar["rarity_score"] >= min_rarity:
            survivors.append({
                **pk,
                "rarity_score": float(rar["rarity_score"]),
                "f_rest": float(rar["f_rest"]),
                "f_topo": float(rar["f_topo"]),
            })

    return survivors, int(n_evals)


# ---------------------------------------------------------------------------
# Engine 4: JWST MIRI MRS Techno-Atmosphere Greenhouse Gas CCF
# ---------------------------------------------------------------------------

GREENHOUSE_GAS_TEMPLATES_UM: dict[str, list[dict[str, float]]] = {
    "CF4": [{"mu_um": 7.80, "sigma_um": 0.14, "weight": 1.0}],
    "C2F6": [
        {"mu_um": 8.00, "sigma_um": 0.18, "weight": 0.55},
        {"mu_um": 8.96, "sigma_um": 0.22, "weight": 0.45},
    ],
    "SF6": [{"mu_um": 10.55, "sigma_um": 0.16, "weight": 1.0}],
    "NF3": [
        {"mu_um": 11.02, "sigma_um": 0.25, "weight": 0.65},
        {"mu_um": 9.70, "sigma_um": 0.18, "weight": 0.35},
    ],
}

NATURAL_MIRI_CONFOUNDER_TEMPLATES_UM: dict[str, list[dict[str, float]]] = {
    "CH4_ATM": [{"mu_um": 7.66, "sigma_um": 0.28, "weight": 1.0}],
    "O3_ATM": [{"mu_um": 9.59, "sigma_um": 0.26, "weight": 1.0}],
    "SILICATE_BROAD": [{"mu_um": 9.75, "sigma_um": 0.85, "weight": 1.0}],
    "PAH_EMISSION": [
        {"mu_um": 7.70, "sigma_um": 0.25, "weight": 0.50},
        {"mu_um": 8.60, "sigma_um": 0.20, "weight": 0.20},
        {"mu_um": 11.30, "sigma_um": 0.22, "weight": 0.30},
    ],
}


def _fit_miri_loglog_continuum(
    w_seg: np.ndarray,
    f_seg: np.ndarray,
    win_mask: np.ndarray,
    sb_mask: np.ndarray,
    mu_center: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None:
    """Fit smooth power-law continuum in ``(log(w), log(F))`` space + design matrices for leverage error."""
    w_sb = w_seg[sb_mask]
    f_sb = f_seg[sb_mask]
    w_win = w_seg[win_mask]
    if len(w_sb) < 20 or len(w_win) < 12 or (float(np.max(w_sb)) - float(np.min(w_sb))) < 0.20:
        return None
    mu_sb = float(np.mean(w_sb))
    has_two_sides = int(np.sum(w_sb < mu_center)) >= 8 and int(np.sum(w_sb > mu_center)) >= 8

    if np.all(f_sb > 0.0) and np.all(w_sb > 0.0) and np.all(w_win > 0.0):
        lw_sb = np.log(w_sb)
        lw_mid = float(np.mean(lw_sb))
        x_sb = lw_sb - lw_mid
        x_win = np.log(w_win) - lw_mid
        deg = 2 if (has_two_sides and len(x_sb) >= 24) else 1
        try:
            coeffs = np.polyfit(x_sb, np.log(f_sb), deg)
            cont_sb = np.exp(np.clip(np.polyval(coeffs, x_sb), -120.0, 120.0))
            cont_win = np.exp(np.clip(np.polyval(coeffs, x_win), -120.0, 120.0))
            X_sb = np.vander(x_sb, deg + 1)
            X_win = np.vander(x_win, deg + 1)
            return cont_win, cont_sb, X_win, X_sb
        except (np.linalg.LinAlgError, ValueError):
            pass

    deg_lin = 2 if (has_two_sides and len(w_sb) >= 24) else 1
    try:
        x_lin_sb = w_sb - mu_sb
        x_lin_win = w_win - mu_sb
        coeffs = np.polyfit(x_lin_sb, f_sb, deg_lin)
        X_sb = np.vander(x_lin_sb, deg_lin + 1)
        X_win = np.vander(x_lin_win, deg_lin + 1)
        return np.polyval(coeffs, x_lin_win), np.polyval(coeffs, x_lin_sb), X_win, X_sb
    except (np.linalg.LinAlgError, ValueError):
        return None


def _sideband_noise_sigma(r_sb: np.ndarray) -> float:
    """Compute robust sideband noise scale with conservative lag-1 fringing adjustment."""
    sb_med = float(np.median(r_sb))
    sigma_sb = max(1e-5, MAD_NORM * float(np.median(np.abs(r_sb - sb_med))))
    if len(r_sb) >= 16:
        rc = r_sb - np.mean(r_sb)
        denom = float(np.dot(rc, rc))
        if denom > 1e-20:
            rho1 = float(np.dot(rc[:-1], rc[1:]) / denom)
            if rho1 > 0.15:
                sigma_sb *= min(2.5, math.sqrt((1.0 + rho1) / max(0.10, 1.0 - rho1)))
    return float(sigma_sb)


def _fit_miri_sideband_template(
    segments: list[tuple[np.ndarray, np.ndarray]],
    components: list[dict[str, float]],
) -> dict[str, float]:
    """Evaluate weighted Gaussian template CCF across contiguous MIRI MRS sub-channels."""
    num_sum = 0.0
    t2_sum = 0.0
    var_sum = 0.0
    n_cov = 0
    w_sum_cov = 0.0

    for comp in components:
        mu = float(comp["mu_um"])
        sig = float(comp["sigma_um"])
        wt = float(comp["weight"])

        best_seg: tuple[np.ndarray, np.ndarray] | None = None
        best_n = 0
        for w_seg, f_seg in segments:
            in_core = np.abs(w_seg - mu) <= 2.2 * sig
            n_core = int(np.sum(in_core))
            if n_core >= 12 and n_core > best_n:
                best_n = n_core
                best_seg = (w_seg, f_seg)
        if best_seg is None:
            continue

        w_seg, f_seg = best_seg
        win_mask = np.abs(w_seg - mu) <= 5.0 * sig
        sb_mask = (np.abs(w_seg - mu) >= 2.0 * sig) & (np.abs(w_seg - mu) <= 5.0 * sig)
        if int(np.sum(sb_mask)) < 14:
            sb_mask = (np.abs(w_seg - mu) >= 1.6 * sig) & (np.abs(w_seg - mu) <= 6.0 * sig)
            win_mask = np.abs(w_seg - mu) <= 6.0 * sig
        # Avoid degenerate one-sided extrapolation when a broad line has no two-sided continuum unless narrow core covered cleanly
        n_left_core = int(np.sum((w_seg[win_mask] >= mu - 2.0 * sig) & (w_seg[win_mask] < mu)))
        n_right_core = int(np.sum((w_seg[win_mask] > mu) & (w_seg[win_mask] <= mu + 2.0 * sig)))
        if n_left_core < 4 or n_right_core < 4:
            continue

        fit_c = _fit_miri_loglog_continuum(w_seg, f_seg, win_mask, sb_mask, mu)
        if fit_c is None:
            continue
        cont_win, cont_sb, X_win, X_sb = fit_c

        f_sb = f_seg[sb_mask]
        safe_sb = np.abs(cont_sb) > 1e-30
        safe_win = np.abs(cont_win) > 1e-30
        if int(np.sum(safe_sb)) < 10 or int(np.sum(safe_win)) < 12:
            continue

        r_sb = (f_sb[safe_sb] - cont_sb[safe_sb]) / np.abs(cont_sb[safe_sb])
        r_win = (f_seg[win_mask][safe_win] - cont_win[safe_win]) / np.abs(cont_win[safe_win])
        w_win = w_seg[win_mask][safe_win]
        w_sb_safe = w_seg[sb_mask][safe_sb]

        sigma_sb = _sideband_noise_sigma(r_sb)
        T_vec = wt * np.exp(-0.5 * ((w_win - mu) / sig) ** 2)
        T_sb = wt * np.exp(-0.5 * ((w_sb_safe - mu) / sig) ** 2)
        T_vec = T_vec - float(np.median(T_sb))

        t2 = float(np.dot(T_vec, T_vec))
        if t2 <= 1e-12:
            continue

        # Propagate continuum-fit estimation leverage uncertainty into template projection variance
        var_cont = 0.0
        try:
            X_sb_s = X_sb[safe_sb]
            X_win_s = X_win[safe_win]
            g_proj = X_win_s.T @ T_vec
            xt_x = X_sb_s.T @ X_sb_s
            var_cont = max(0.0, float(g_proj.T @ np.linalg.solve(xt_x + 1e-9 * np.eye(xt_x.shape[0]), g_proj)))
        except np.linalg.LinAlgError:
            var_cont = 0.0

        num_sum += float(np.dot(T_vec, r_win))
        t2_sum += t2
        var_sum += (sigma_sb ** 2) * (t2 + var_cont)
        n_cov += 1
        w_sum_cov += wt

    if n_cov == 0 or t2_sum <= 1e-12 or var_sum <= 1e-30:
        return {
            "covered": False,
            "n_components": 0,
            "depth": 0.0,
            "sigma_depth": math.nan,
            "ccf_sigma_abs": 0.0,
            "max_abs_ccf_sigma": 0.0,
            "delta_min_5sigma": math.nan,
            "ppm_equiv_10pct_ref": math.nan,
        }

    w_scale = max(1e-6, w_sum_cov / float(n_cov))
    amp_raw = num_sum / t2_sum
    depth = -amp_raw * w_scale
    sigma_depth = (math.sqrt(var_sum) / t2_sum) * w_scale
    ccf_sigma_abs = depth / max(1e-12, sigma_depth)
    delta_min_5sigma = min(1.0, 5.0 * sigma_depth)
    ppm_equiv = 10.0 * (delta_min_5sigma / 0.10)
    return {
        "covered": True,
        "n_components": int(n_cov),
        "depth": float(depth),
        "sigma_depth": float(sigma_depth),
        "ccf_sigma_abs": float(ccf_sigma_abs),
        "max_abs_ccf_sigma": float(abs(ccf_sigma_abs)),
        "delta_min_5sigma": float(delta_min_5sigma),
        "ppm_equiv_10pct_ref": float(ppm_equiv),
    }


def _joint_miri_confounder_test(
    segments: list[tuple[np.ndarray, np.ndarray]],
    mol_comps: list[dict[str, float]],
    conf_comps: list[dict[str, float]],
    conf_is_emission: bool = False,
) -> dict[str, Any]:
    """Simultaneously fit overlapping target molecule + natural confounder templates via 2-param OLS."""
    pairs: list[tuple[dict[str, float], dict[str, float]]] = []
    for mc in mol_comps:
        for cc in conf_comps:
            if abs(float(mc["mu_um"]) - float(cc["mu_um"])) <= 2.2 * (float(mc["sigma_um"]) + float(cc["sigma_um"])):
                pairs.append((mc, cc))
    if not pairs:
        return {"overlaps": False}

    # Evaluate joint linear model across overlapping component windows
    xtx_tot = np.zeros((2, 2), dtype=np.float64)
    xty_tot = np.zeros(2, dtype=np.float64)
    cov_num = np.zeros((2, 2), dtype=np.float64)
    n_pairs_used = 0

    for mc, cc in pairs:
        mu_m, sig_m = float(mc["mu_um"]), float(mc["sigma_um"])
        mu_c, sig_c = float(cc["mu_um"]), float(cc["sigma_um"])
        lo_core = min(mu_m - 2.0 * sig_m, mu_c - 2.0 * sig_c)
        hi_core = max(mu_m + 2.0 * sig_m, mu_c + 2.0 * sig_c)
        span = max(0.6, hi_core - lo_core)
        lo_win = lo_core - 1.25 * span
        hi_win = hi_core + 1.25 * span

        best_seg: tuple[np.ndarray, np.ndarray] | None = None
        best_n = 0
        for w_seg, f_seg in segments:
            if not (w_seg[0] + 0.05 < mu_m < w_seg[-1] - 0.05 and w_seg[0] + 0.05 < mu_c < w_seg[-1] - 0.05):
                continue
            in_m = int(np.sum(np.abs(w_seg - mu_m) <= 2.0 * sig_m))
            if in_m >= 12 and in_m > best_n:
                best_n = in_m
                best_seg = (w_seg, f_seg)
        if best_seg is None:
            continue
        w_seg, f_seg = best_seg

        win_mask = (w_seg >= lo_win) & (w_seg <= hi_win)
        sb_mask = win_mask & ((w_seg < lo_core) | (w_seg > hi_core))
        if int(np.sum(sb_mask)) < 20:
            sb_mask = (np.abs(w_seg - mu_m) >= 1.8 * sig_m) & ((w_seg < mu_c - 1.5 * sig_c) | (w_seg > mu_c + 1.5 * sig_c))
            sb_mask &= (w_seg >= lo_win - 1.0) & (w_seg <= hi_win + 1.0)
            win_mask |= sb_mask

        fit_c = _fit_miri_loglog_continuum(w_seg, f_seg, win_mask, sb_mask, 0.5 * (mu_m + mu_c))
        if fit_c is None:
            continue
        cont_win, cont_sb, X_win, X_sb = fit_c
        safe_sb = np.abs(cont_sb) > 1e-30
        safe_win = np.abs(cont_win) > 1e-30
        if int(np.sum(safe_sb)) < 16 or int(np.sum(safe_win)) < 16:
            continue

        r_sb = (f_seg[sb_mask][safe_sb] - cont_sb[safe_sb]) / np.abs(cont_sb[safe_sb])
        y_abs_depth = -(f_seg[win_mask][safe_win] - cont_win[safe_win]) / np.abs(cont_win[safe_win])
        w_win = w_seg[win_mask][safe_win]
        sigma_sb = _sideband_noise_sigma(r_sb)

        tm = float(mc["weight"]) * np.exp(-0.5 * ((w_win - mu_m) / sig_m) ** 2)
        tc = float(cc["weight"]) * np.exp(-0.5 * ((w_win - mu_c) / sig_c) ** 2)
        X = np.column_stack([tm, tc])
        xtx = X.T @ X
        # Propagate continuum-fit leverage matrix G = (X_win^T X)^T inv(X_sb^T X_sb) (X_win^T X)
        cov_c = np.zeros((2, 2), dtype=np.float64)
        try:
            X_sb_s = X_sb[safe_sb]
            X_win_s = X_win[safe_win]
            G = X_win_s.T @ X  # (deg+1, 2)
            xt_x_sb = X_sb_s.T @ X_sb_s + 1e-9 * np.eye(X_sb_s.shape[1])
            cov_c = G.T @ np.linalg.solve(xt_x_sb, G)
        except np.linalg.LinAlgError:
            cov_c = np.zeros((2, 2), dtype=np.float64)

        xtx_tot += xtx
        xty_tot += X.T @ y_abs_depth
        cov_num += (sigma_sb ** 2) * (xtx + cov_c)
        n_pairs_used += 1

    if n_pairs_used == 0 or np.linalg.cond(xtx_tot + 1e-9 * np.eye(2)) > 1e4:
        return {"overlaps": False}

    try:
        inv_xtx = np.linalg.inv(xtx_tot + 1e-9 * np.eye(2))
        beta = inv_xtx @ xty_tot
        var_beta = inv_xtx @ cov_num @ inv_xtx
    except np.linalg.LinAlgError:
        return {"overlaps": False}

    se_m = max(1e-12, math.sqrt(max(0.0, float(var_beta[0, 0]))))
    se_c = max(1e-12, math.sqrt(max(0.0, float(var_beta[1, 1]))))
    z_m = float(beta[0] / se_m)
    z_c_raw = float(beta[1] / se_c)
    z_c_phys = (-z_c_raw) if conf_is_emission else z_c_raw
    return {
        "overlaps": True,
        "ccf_mol_given_conf": float(z_m),
        "ccf_conf_given_mol": float(z_c_phys),
    }


def scan_miri_greenhouse_ccf_v50(
    wave_um: np.ndarray,
    flux_norm_or_flam: np.ndarray,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Scan JWST MIRI MRS spectra for industrial greenhouse technosignature absorption bands.

    Evaluates ``CF4``, ``C2F6``, ``SF6``, and ``NF3`` against natural atmospheric/dust
    confounders (``CH4_ATM``, ``O3_ATM``, ``SILICATE_BROAD``, ``PAH_EMISSION``) using
    power-law ``log-log`` sideband continuum normalization and 2-parameter joint OLS
    confounder separation for overlapping bands (e.g. ``CF4`` vs ``CH4_ATM``).
    """
    cfg_eff = cfg or BASE_V5_0_CONFIG
    min_sigma = float(cfg_eff.get("miri_ccf_min_sigma", 5.0))
    min_conf_ratio = float(cfg_eff.get("miri_ccf_min_confounder_ratio", 1.5))

    w = np.asarray(wave_um, dtype=np.float64)
    f = np.asarray(flux_norm_or_flam, dtype=np.float64)
    valid = np.isfinite(w) & np.isfinite(f) & (w > 0.0)
    if int(np.sum(valid)) < 32:
        return {
            "molecules": {},
            "confounders": {},
            "max_confounder_sigma": 0.0,
            "detected_molecules": [],
            "any_detection": False,
        }

    w_v = w[valid]
    f_v = f[valid]
    order = np.argsort(w_v)
    w_v = w_v[order]
    f_v = f_v[order]

    split_idx = np.where((np.diff(w_v) > 0.05) | (np.diff(w_v) < 0.0))[0] + 1
    bounds = [0] + list(split_idx) + [len(w_v)]
    segments: list[tuple[np.ndarray, np.ndarray]] = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        if (b - a) >= 20 and (w_v[b - 1] - w_v[a]) >= 0.30:
            segments.append((w_v[a:b], f_v[a:b]))

    conf_res: dict[str, dict[str, float]] = {}
    max_conf = 0.0
    for cname, comps in NATURAL_MIRI_CONFOUNDER_TEMPLATES_UM.items():
        cres = _fit_miri_sideband_template(segments, comps)
        # Physical sign: CH4/O3/Silicate act as absorption confounders, PAH as emission
        raw_s = float(cres["ccf_sigma_abs"])
        phys_s = max(0.0, -raw_s if cname == "PAH_EMISSION" else raw_s)
        cres["physical_confounder_sigma"] = float(phys_s)
        conf_res[cname] = cres
        if cres["covered"]:
            max_conf = max(max_conf, phys_s)

    mol_res: dict[str, dict[str, Any]] = {}
    detected: list[str] = []
    for mname, comps in GREENHOUSE_GAS_TEMPLATES_UM.items():
        mres = _fit_miri_sideband_template(segments, comps)
        ccf_s = float(mres["ccf_sigma_abs"])
        joint_vetoes: dict[str, Any] = {}
        passes = bool(mres["covered"] and ccf_s >= min_sigma)

        if mres["covered"]:
            for cname, ccomps in NATURAL_MIRI_CONFOUNDER_TEMPLATES_UM.items():
                is_em = cname == "PAH_EMISSION"
                jres = _joint_miri_confounder_test(segments, comps, ccomps, conf_is_emission=is_em)
                joint_vetoes[cname] = jres
                if jres.get("overlaps"):
                    zm = float(jres["ccf_mol_given_conf"])
                    zc = max(0.0, float(jres["ccf_conf_given_mol"]))
                    if not (zm >= min_sigma and zm > min_conf_ratio * zc):
                        passes = False
                else:
                    min_dist_um = min(
                        abs(float(mc["mu_um"]) - float(cc["mu_um"]))
                        for mc in comps
                        for cc in ccomps
                    )
                    if min_dist_um <= 1.2 and conf_res[cname]["covered"]:
                        c_phys = float(conf_res[cname]["physical_confounder_sigma"])
                        if not (ccf_s > min_conf_ratio * c_phys):
                            passes = False

        mres["joint_confounder_checks"] = joint_vetoes
        mres["passes_ccf"] = passes
        mol_res[mname] = mres
        if passes:
            detected.append(mname)

    return {
        "molecules": mol_res,
        "confounders": conf_res,
        "max_confounder_sigma": float(max_conf),
        "detected_molecules": detected,
        "any_detection": len(detected) > 0,
    }


# ---------------------------------------------------------------------------
# Engine 5: Exact Geometric Synchronization (SN 1987A Ellipsoid, ETZ, PPO)
# ---------------------------------------------------------------------------

SN1987A_RA_DEG = 83.86675
SN1987A_DEC_DEG = -69.26974
SN1987A_DIST_PC = 49590.0
SN1987A_MJD0 = 46849.316
_PC_PER_DAY = (C_SI * DAY_S) / (PC_CM * 1e-2)  # parsecs traveled by light per day
_DAYS_PER_PC = 1.0 / _PC_PER_DAY


def compute_sn1987a_ellipsoid_mjd(
    ra_deg: float,
    dec_deg: float,
    dist_pc: float,
    dist_err_pc: float = 0.0,
) -> tuple[float, float, float]:
    """
    Compute exact SN 1987A SETI Ellipsoid synchronization epoch at Earth.

    Returns ``(mjd_ellipsoid, dt_days_since_sn, mjd_err_days)`` where
    ``dt = (d_* + |r_* - r_SN| - d_SN) / c``.
    """
    ra1 = math.radians(SN1987A_RA_DEG)
    dec1 = math.radians(SN1987A_DEC_DEG)
    ra2 = math.radians(float(ra_deg))
    dec2 = math.radians(float(dec_deg))

    cos_theta = (
        math.cos(dec1) * math.cos(dec2) * math.cos(ra1 - ra2)
        + math.sin(dec1) * math.sin(dec2)
    )
    cos_theta = max(-1.0, min(1.0, cos_theta))

    d_sn = SN1987A_DIST_PC
    d_star = max(0.0, float(dist_pc))
    d_between = math.sqrt(max(1e-12, d_sn * d_sn + d_star * d_star - 2.0 * d_sn * d_star * cos_theta))
    path_diff_pc = d_star + d_between - d_sn
    dt_days = path_diff_pc * _DAYS_PER_PC
    mjd_ell = SN1987A_MJD0 + dt_days

    deriv_d = 1.0 + (d_star - d_sn * cos_theta) / d_between
    mjd_err_days = abs(deriv_d) * max(0.0, float(dist_err_pc)) * _DAYS_PER_PC
    return float(mjd_ell), float(dt_days), float(mjd_err_days)


def compute_ecliptic_lat_deg(ra_deg: float, dec_deg: float) -> float:
    """Compute J2000 ecliptic latitude beta (deg) from equatorial ICRS (RA, Dec)."""
    eps = math.radians(23.4392911)
    ra_r = math.radians(float(ra_deg))
    dec_r = math.radians(float(dec_deg))
    sin_beta = math.sin(dec_r) * math.cos(eps) - math.cos(dec_r) * math.sin(eps) * math.sin(ra_r)
    sin_beta = max(-1.0, min(1.0, sin_beta))
    return float(math.degrees(math.asin(sin_beta)))


def compute_ppo_alignment_score(
    bjd_obs: float,
    planets: list[tuple[float, float]],
) -> float:
    """
    Compute minimum pairwise Planet-Planet Occultation (PPO) syzygy phase offset [0.0, 0.25].

    Each entry in ``planets`` is ``(orbper_days, t0_bjd)``. A score of ``0.0`` denotes exact
    pairwise phase conjunction (``|dphi| = 0``) or opposition (``|dphi| = 0.5``).
    Returns ``1.0`` when fewer than two valid planets are supplied.
    """
    if not math.isfinite(float(bjd_obs)):
        return 1.0
    phases: list[float] = []
    for p_days, t0 in planets:
        if math.isfinite(float(p_days)) and float(p_days) > 0.0 and math.isfinite(float(t0)):
            phi = ((float(bjd_obs) - float(t0)) / float(p_days)) % 1.0
            phases.append(phi)
    if len(phases) < 2:
        return 1.0

    best = 1.0
    for i in range(len(phases)):
        for j in range(i + 1, len(phases)):
            dp = abs(phases[i] - phases[j])
            dp_wrap = min(dp, 1.0 - dp)
            align = min(dp_wrap, abs(0.5 - dp_wrap))
            if align < best:
                best = align
    return float(best)


# ===========================================================================
# TECHNOSIGNATURE V5.1 ENGINES (PHASE D093)
# ===========================================================================

OBSERVATORY_GEODETIC = {
    "GEMINI_GRACES": (19.8238, -155.4690),   # Maunakea, Hawaii
    "ESO_CORALIE": (-29.2543, -70.7346),     # La Silla, Chile
    "CARMENES_VIS": (37.2236, -2.5462),      # Calar Alto, Spain
    "CFHT_ESPADONS": (19.8253, -155.4688),   # Maunakea, Hawaii
    "OHP_SOPHIE": (43.9308, 5.7133),         # Haute-Provence
    "OHP_ELODIE": (43.9308, 5.7133),         # Haute-Provence
    "ESO_HARPS": (-29.2543, -70.7346),
    "ESO_FEROS": (-29.2543, -70.7346),
    "ESO_CRIRES": (-24.6272, -70.4042),
    "SDSS_APOGEE2": (32.7803, -105.8204),    # Apache Point Observatory, NM
    "SDSS_APOGEE2_LCO": (-29.0146, -70.6926),  # Las Campanas Observatory, Chile
    "JWST_MIRI_LRS": (0.0, 0.0),             # L2 Halo Orbit (BC ~ 0 relative to Earth-L2 vector)
    "SOFIA_EXES": (34.6290, -118.0840),      # NASA Armstrong Palmdale stratospheric base
    "JWST_NIRISS_SOSS": (0.0, 0.0),          # L2 Halo Orbit
    "JWST_NIRSPEC_G140H": (0.0, 0.0),        # L2 Halo Orbit
}


def analytical_observatory_berv_kms(
    ra_deg: float,
    dec_deg: float,
    mjd_mid: float,
    instrument: str,
) -> float:
    """Pure-stdlib barycentric/heliocentric RV + diurnal Earth rotation correction (km/s)."""
    v_helio = stdlib_earth_helio_rv_kms(ra_deg, dec_deg, mjd_mid)
    lat_deg, lon_deg = OBSERVATORY_GEODETIC.get(instrument, (-29.2543, -70.7346))
    gmst_deg = (280.46061837 + 360.98564736629 * (float(mjd_mid) - 51544.5)) % 360.0
    lst_rad = math.radians((gmst_deg + lon_deg) % 360.0)
    ha_rad = lst_rad - math.radians(float(ra_deg))
    lat_rad = math.radians(lat_deg)
    dec_rad = math.radians(float(dec_deg))
    v_diurnal = -0.4651 * math.cos(lat_rad) * math.cos(dec_rad) * math.sin(ha_rad)
    return float(v_helio + v_diurnal)


def air_to_vac_a(wave_air_a: np.ndarray) -> np.ndarray:
    """IAU standard (Morton 2000) air-to-vacuum wavelength conversion in Angstrom."""
    w = np.asarray(wave_air_a, dtype=np.float64)
    s2 = (1e4 / np.maximum(w, 100.0)) ** 2
    n = 1.0 + 0.0000834254 + 0.02406147 / (130.0 - s2) + 0.00015998 / (38.9 - s2)
    return np.where(w >= 2000.0, w * n, w)


# ---------------------------------------------------------------------------
# Engine 6 (V5.1): Blind Linear Drift-Rate (v_0, v_dot) De-Doppler Search
# ---------------------------------------------------------------------------

DRIFT_V51_SHIFTS_KMS: tuple[float, ...] = (
    -250.0, -220.0, -190.0, -165.0, -140.0, -120.0, -100.0, -85.0, -70.0, -58.0,
    -46.0, -36.0, -28.0, -22.0, -17.0, -13.0, -10.0, -7.5, -5.5, -5.0,
    5.0, 6.0, 8.0, 10.0, 13.0, 17.0, 22.0, 28.0, 36.0, 46.0,
    58.0, 70.0, 85.0, 100.0, 120.0, 140.0, 165.0, 190.0, 220.0, 240.0, 250.0,
)


def scan_blind_drift_dedoppler_v51(
    wave_rest: np.ndarray,
    z1: np.ndarray,
    z2: np.ndarray,
    dt_days: float,
    berv1_kms: float,
    berv2_kms: float,
    cfg: dict[str, Any],
    star: str = "",
    star_idx: int = 0,
    z_rpca_mat: np.ndarray | None = None,
    bervs_cohort: np.ndarray | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """
    Scan paired epochs `(z1, z2)` for linearly drifting narrowband signals `w_2 = w_1 * (1 + dv/c)`
    across 41 non-zero drift shifts spanning `[-250, -5] U [+5, +250] km/s`, plus fine continuous
    peak matching inside adjacent drift corridors after stationary `|dv| < 3.0 km/s` veto.
    """
    w = np.asarray(wave_rest, dtype=np.float64)
    a1 = np.asarray(z1, dtype=np.float64)
    a2 = np.asarray(z2, dtype=np.float64)
    n_wave = len(w)
    if n_wave < 128 or not math.isfinite(float(dt_days)) or float(dt_days) <= 0.0:
        return [], {"n_shifts": len(DRIFT_V51_SHIFTS_KMS), "n_evals": 0}

    fin1 = np.isfinite(a1)
    fin2 = np.isfinite(a2)
    mask_stat = _is_masked_static_v50(w, cfg, 0.5 * (float(berv1_kms) + float(berv2_kms)))
    epoch_min_z = float(cfg.get("drift_v51_epoch_min_z", 5.0))
    comb_min_z = float(cfg.get("drift_v51_comb_min_z", 7.5))
    stat_max_z = float(cfg.get("drift_v51_stat_max_z", 4.0))
    dv_min_abs = float(cfg.get("drift_v51_min_abs_dv_kms", 5.0))
    dv_max_abs = float(cfg.get("drift_v51_max_abs_dv_kms", 250.0))
    min_rarity = float(cfg.get("g7_min_rarity_score", 0.65))
    sig_v = float(cfg.get("sigma_v_kms", 2.0))

    dw = float(np.median(np.diff(w)))
    z2_safe = np.where(fin2, a2, 0.0)
    a1_safe = np.where(fin1 & (~mask_stat), a1, 0.0)

    pk_idx_raw = np.where(a1_safe >= epoch_min_z)[0]
    if len(pk_idx_raw) == 0:
        return [], {"n_shifts": len(DRIFT_V51_SHIFTS_KMS), "n_evals": int(n_wave * len(DRIFT_V51_SHIFTS_KMS))}

    peaks1: list[int] = []
    order_pk = pk_idx_raw[np.argsort(a1_safe[pk_idx_raw])[::-1]]
    taken = np.zeros(n_wave, dtype=bool)
    for idx in order_pk:
        if taken[idx]:
            continue
        lo_n = max(0, idx - 5)
        hi_n = min(n_wave, idx + 6)
        if float(a1_safe[idx]) >= float(np.max(a1_safe[lo_n:hi_n])) - 1e-12:
            peaks1.append(int(idx))
            taken[lo_n:hi_n] = True

    cands: list[dict[str, Any]] = []
    min_sep_a = max(0.3, 4.0 * dw * 10.0)
    kept_waves: list[float] = []

    for idx1 in sorted(peaks1):
        w1 = float(w[idx1])
        z1_pk = float(a1_safe[idx1])
        stat_hw_a = w1 * (3.0 / C_KMS) + 1.5 * dw
        s_lo = int(np.searchsorted(w, w1 - stat_hw_a, side="left"))
        s_hi = int(np.searchsorted(w, w1 + stat_hw_a, side="right"))
        z_stat2 = float(np.max(z2_safe[s_lo:s_hi])) if s_hi > s_lo else 0.0
        if z_stat2 >= stat_max_z:
            continue

        # Search epoch-2 shifted corridor spanning [-250,-5] U [+5,+250] via the 41 drift channels
        best_dv = 0.0
        best_z2 = -1e9
        best_comb = -1e9
        for dv_c in DRIFT_V51_SHIFTS_KMS:
            w2_c = w1 * (1.0 + dv_c / C_KMS)
            tol_kms = max(5.0, 0.14 * abs(dv_c))
            tol_a = max(2.0 * dw, w1 * (tol_kms / C_KMS))
            j0 = int(np.searchsorted(w, w2_c - tol_a, side="left"))
            j1 = int(np.searchsorted(w, w2_c + tol_a, side="right"))
            if j1 <= j0 or not np.any(fin2[j0:j1]):
                continue
            jmax = j0 + int(np.argmax(z2_safe[j0:j1]))
            z2_v = float(z2_safe[jmax])
            if z2_v >= epoch_min_z:
                dv_exact = C_KMS * (float(w[jmax]) - w1) / w1
                if dv_min_abs <= abs(dv_exact) <= dv_max_abs:
                    comb = (z1_pk + z2_v) / math.sqrt(2.0)
                    if comb > best_comb:
                        best_comb = comb
                        best_z2 = z2_v
                        best_dv = dv_exact

        if best_comb < comb_min_z or best_z2 < epoch_min_z:
            continue

        lo_p = max(0, idx1 - 5)
        hi_p = min(n_wave, idx1 + 6)
        win1 = a1[lo_p:hi_p]
        if len(win1) >= 7 and np.all(np.isfinite(win1)):
            c_idx = idx1 - lo_p
            wing_max = max(float(win1[max(0, c_idx - 1)]), float(win1[min(len(win1) - 1, c_idx + 1)]))
            eta_1px = wing_max / max(1e-6, z1_pk)
            sig_px = (w1 * sig_v / C_KMS) / max(1e-6, dw)
            if sig_px >= 0.7 and eta_1px < 0.08:
                continue
            far_wing = max(float(win1[0]), float(win1[-1])) / max(1e-6, z1_pk)
            if far_wing > 0.55:
                continue

        w2_best = w1 * (1.0 + best_dv / C_KMS)
        i2_best = min(n_wave - 1, max(0, int(np.searchsorted(w, w2_best))))
        if bool(mask_stat[i2_best]):
            continue

        rarity_1 = 1.0
        rarity_2 = 1.0
        if z_rpca_mat is not None and bervs_cohort is not None and z_rpca_mat.shape[0] >= 2:
            r1_d = compute_spectral_rarity_score(w, z_rpca_mat, bervs_cohort, star_idx, w1, sig_v, polarity=1.0)
            r2_d = compute_spectral_rarity_score(w, z_rpca_mat, bervs_cohort, star_idx, w2_best, sig_v, polarity=1.0)
            rarity_1 = float(r1_d["rarity_score"])
            rarity_2 = float(r2_d["rarity_score"])
            if rarity_1 < min_rarity or rarity_2 < min_rarity:
                continue

        if any(abs(w1 - kw) < min_sep_a for kw in kept_waves):
            continue
        kept_waves.append(w1)

        vdot_kms_day = float(best_dv) / float(dt_days)
        vdot_ms_h = (vdot_kms_day * 1000.0) / 24.0
        cands.append({
            "star": star,
            "wave1_rest_a": round(w1, 5),
            "wave2_rest_a": round(w2_best, 5),
            "dv_kms": round(best_dv, 4),
            "dt_days": round(float(dt_days), 6),
            "vdot_kms_day": round(vdot_kms_day, 5),
            "vdot_ms_h": round(vdot_ms_h, 3),
            "z1": round(z1_pk, 4),
            "z2": round(best_z2, 4),
            "z_stat2": round(z_stat2, 4),
            "z_drift_comb": round(best_comb, 4),
            "rarity1": round(rarity_1, 4),
            "rarity2": round(rarity_2, 4),
        })

    return cands, {
        "n_shifts": len(DRIFT_V51_SHIFTS_KMS),
        "n_evals": int(n_wave * len(DRIFT_V51_SHIFTS_KMS)),
        "n_peaks1": len(peaks1),
    }


# ---------------------------------------------------------------------------
# Engine 7 (V5.1): Non-Linear Spectral-Patch Intrinsic Novelty (G8_V51)
# ---------------------------------------------------------------------------

def _extract_patch_feature_vector(
    wave_rest: np.ndarray,
    z_vec: np.ndarray,
    idx: int,
    z_rpca: float,
    rarity_score: float,
    f_rest: float,
    f_topo: float,
    half_px: int = 8,
) -> np.ndarray | None:
    n = len(z_vec)
    if idx < half_px or idx + half_px >= n:
        return None
    sub = np.asarray(z_vec[idx - half_px : idx + half_px + 1], dtype=np.float64)
    if not np.all(np.isfinite(sub)):
        return None
    nm = float(np.linalg.norm(sub))
    if nm <= 1e-8:
        return None
    patch_u = sub / nm
    scalars = np.asarray([
        max(-2.0, min(2.0, float(z_rpca) / 15.0)),
        max(0.0, min(1.0, float(rarity_score))),
        max(0.0, min(1.0, float(f_rest))),
        max(0.0, min(1.0, float(f_topo))),
    ], dtype=np.float64)
    return np.concatenate([patch_u, scalars])


def fit_patch_novelty_model_v51(
    patch_features: list[np.ndarray] | np.ndarray,
    pca_dim: int = 8,
    knn_k: int = 7,
    min_novelty_z: float = 3.5,
) -> dict[str, Any]:
    """Fit PCA-whitened reference manifold on background spectral residual patches for Gate G8_V51."""
    arr = np.asarray(patch_features, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[0] < max(24, knn_k + 4):
        return {
            "ready": False,
            "n_ref": int(arr.shape[0]) if arr.ndim == 2 else 0,
            "pca_dim": int(pca_dim),
            "knn_k": int(knn_k),
            "min_novelty_z": float(min_novelty_z),
        }
    mu = np.mean(arr, axis=0)
    xc = arr - mu[None, :]
    cov = (xc.T @ xc) / max(1.0, float(arr.shape[0] - 1))
    evals, evecs = np.linalg.eigh(cov)
    ord_idx = np.argsort(evals)[::-1]
    k_pca = min(int(pca_dim), arr.shape[1])
    evals_k = np.maximum(1e-5, evals[ord_idx[:k_pca]])
    basis_k = evecs[:, ord_idx[:k_pca]]
    proj = (xc @ basis_k) / np.sqrt(evals_k)[None, :]

    diff2 = np.sum(proj * proj, axis=1, keepdims=True) + np.sum(proj * proj, axis=1)[None, :] - 2.0 * (proj @ proj.T)
    np.fill_diagonal(diff2, 1e18)
    k_eff = min(int(knn_k), arr.shape[0] - 1)
    kth_d2 = np.partition(np.maximum(0.0, diff2), k_eff - 1, axis=1)[:, k_eff - 1]
    kth_d = np.sqrt(kth_d2)
    ref_med = float(np.median(kth_d))
    ref_mad = max(0.08, MAD_NORM * float(np.median(np.abs(kth_d - ref_med))))

    return {
        "ready": True,
        "n_ref": int(arr.shape[0]),
        "pca_dim": int(k_pca),
        "knn_k": int(k_eff),
        "min_novelty_z": float(min_novelty_z),
        "mu": mu,
        "basis_k": basis_k,
        "inv_sqrt_evals": 1.0 / np.sqrt(evals_k),
        "proj_ref": proj,
        "ref_med": ref_med,
        "ref_mad": ref_mad,
    }


def evaluate_gate_g8_v51(
    model: dict[str, Any],
    wave_rest: np.ndarray,
    z_vec: np.ndarray,
    center_wave_a: float,
    z_rpca: float,
    rarity_score: float,
    f_rest: float = 0.0,
    f_topo: float = 0.0,
) -> dict[str, Any]:
    """Score non-linear local patch novelty against the PCA-whitened k-NN background library."""
    if not model.get("ready"):
        return {"g8_pass": True, "novelty_z": 99.0, "knn_dist": 0.0, "reason": "NO_REF_PASS"}

    w = np.asarray(wave_rest, dtype=np.float64)
    idx = int(np.searchsorted(w, float(center_wave_a)))
    idx = max(0, min(len(w) - 1, idx))
    half_px = int((len(model["mu"]) - 4 - 1) // 2)
    vec = _extract_patch_feature_vector(
        w, z_vec, idx, float(z_rpca), float(rarity_score), float(f_rest), float(f_topo), half_px=half_px
    )
    if vec is None:
        return {"g8_pass": False, "novelty_z": 0.0, "knn_dist": 0.0, "reason": "G8_EDGE_NAN"}

    p = ((vec - model["mu"]) @ model["basis_k"]) * model["inv_sqrt_evals"]
    d2 = np.sum((model["proj_ref"] - p[None, :]) ** 2, axis=1)
    k_eff = min(int(model["knn_k"]), len(d2) - 1)
    d_k = math.sqrt(max(0.0, float(np.partition(d2, k_eff - 1)[k_eff - 1])))
    novelty_z = (d_k - float(model["ref_med"])) / max(1e-6, float(model["ref_mad"]))
    thr = float(model.get("min_novelty_z", 3.5))
    passed = bool(math.isfinite(novelty_z) and novelty_z >= thr)
    return {
        "g8_pass": passed,
        "novelty_z": float(novelty_z),
        "knn_dist": float(d_k),
        "reason": "PASS" if passed else "G8_LOW_PATCH_NOVELTY",
    }


# ---------------------------------------------------------------------------
# Engine 8 (V5.1): Multi-Event Cosmic Schelling-Point Ellipsoids
# ---------------------------------------------------------------------------

COSMIC_BEACON_EVENTS: dict[str, dict[str, Any]] = {
    "SN1987A": {
        "label": "SN 1987A (LMC)",
        "ra_deg": 83.86675,
        "dec_deg": -69.26974,
        "dist_pc": 49590.0,
        "mjd0": 46849.316,
    },
    "GW170817": {
        "label": "GW170817 / NGC 4993",
        "ra_deg": 197.45037,
        "dec_deg": -23.38149,
        "dist_pc": 4.07e7,
        "mjd0": 57982.528,
    },
    "SN2023ixf": {
        "label": "SN 2023ixf (M101)",
        "ra_deg": 210.91067,
        "dec_deg": 54.31165,
        "dist_pc": 6.85e6,
        "mjd0": 60083.727,
    },
}


def compute_event_ellipsoid_mjd(
    ra_deg: float,
    dec_deg: float,
    dist_pc: float,
    ev_ra_deg: float,
    ev_dec_deg: float,
    ev_dist_pc: float,
    ev_mjd0: float,
    dist_err_pc: float = 0.0,
) -> tuple[float, float, float]:
    """Unified 3D triangle SETI Ellipsoid crossing MJD for Galactic/LMC/Extragalactic beacons."""
    ra1, dec1 = math.radians(float(ev_ra_deg)), math.radians(float(ev_dec_deg))
    ra2, dec2 = math.radians(float(ra_deg)), math.radians(float(dec_deg))
    cos_t = max(-1.0, min(1.0, math.cos(dec1) * math.cos(dec2) * math.cos(ra1 - ra2) + math.sin(dec1) * math.sin(dec2)))
    d_ev = max(1.0, float(ev_dist_pc))
    d_st = max(0.0, float(dist_pc))
    if d_ev > 1e5 * max(1.0, d_st):
        path_diff_pc = d_st * (1.0 - cos_t) + (d_st * d_st * (1.0 - cos_t * cos_t)) / (2.0 * d_ev)
        deriv_d = 1.0 - cos_t
    else:
        d_between = math.sqrt(max(1e-12, d_ev * d_ev + d_st * d_st - 2.0 * d_ev * d_st * cos_t))
        path_diff_pc = d_st + d_between - d_ev
        deriv_d = 1.0 + (d_st - d_ev * cos_t) / d_between
    dt_days = path_diff_pc * _DAYS_PER_PC
    return float(ev_mjd0 + dt_days), float(dt_days), float(abs(deriv_d) * max(0.0, float(dist_err_pc)) * _DAYS_PER_PC)


def compute_multievent_sync_v51(
    ra_deg: float,
    dec_deg: float,
    dist_pc: float,
    mjd_obs: float,
    dist_err_pc: float = 0.0,
) -> dict[str, Any]:
    """Evaluate all three cosmic beacon ellipsoids + ETZ latitude for `(ra, dec, dist_pc, mjd_obs)`."""
    out: dict[str, Any] = {"ecliptic_lat_deg": compute_ecliptic_lat_deg(ra_deg, dec_deg)}
    best_abs = 1e18
    best_ev = "NONE"
    for key, ev in COSMIC_BEACON_EVENTS.items():
        mjd_ell, _, err_d = compute_event_ellipsoid_mjd(
            ra_deg, dec_deg, dist_pc, ev["ra_deg"], ev["dec_deg"], ev["dist_pc"], ev["mjd0"], dist_err_pc=dist_err_pc
        )
        dt_obs = float(mjd_obs) - mjd_ell
        out[f"{key.lower()}_mjd_ell"] = float(mjd_ell)
        out[f"{key.lower()}_dt_days"] = float(dt_obs)
        out[f"{key.lower()}_err_days"] = float(err_d)
        if abs(dt_obs) < best_abs:
            best_abs = abs(dt_obs)
            best_ev = key
    out["nearest_event"] = best_ev
    out["min_abs_ellipsoid_dt_days"] = float(best_abs)
    return out


# ---------------------------------------------------------------------------
# Engine 9 (V5.1): JWST NIRSpec G395H (2.86-5.18 um) Molecular & Isotopologue CCF
# ---------------------------------------------------------------------------

NIRSPEC_MOL_TEMPLATES_UM: dict[str, list[dict[str, float]]] = {
    "NO2": [{"mu_um": 3.44, "sigma_um": 0.045, "weight": 1.00}],
    "N2O": [{"mu_um": 4.50, "sigma_um": 0.055, "weight": 1.00}],
    "CH4_C2H6": [{"mu_um": 3.32, "sigma_um": 0.050, "weight": 1.00}],
    "CO_13CO": [
        {"mu_um": 4.67, "sigma_um": 0.045, "weight": 0.60},
        {"mu_um": 4.78, "sigma_um": 0.045, "weight": 0.40},
    ],
}

NATURAL_NIRSPEC_CONFOUNDERS_UM: dict[str, list[dict[str, float]]] = {
    "H2O_NIR": [
        {"mu_um": 3.08, "sigma_um": 0.070, "weight": 0.50},
        {"mu_um": 5.00, "sigma_um": 0.070, "weight": 0.50},
    ],
    "CO2_4P26": [{"mu_um": 4.26, "sigma_um": 0.060, "weight": 1.00}],
    "H2_0_0_S9_VIB": [{"mu_um": 4.69, "sigma_um": 0.035, "weight": 1.00}],
    "DUST_SIL_SLOPE": [
        {"mu_um": 3.40, "sigma_um": 0.160, "weight": 0.45},
        {"mu_um": 4.45, "sigma_um": 0.180, "weight": 0.55},
    ],
}


def scan_nirspec_molecular_ccf_v51(
    wave_um: np.ndarray,
    flux_norm_or_flam: np.ndarray,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Scan JWST NIRSpec G395H (`2.86-5.18 um`) spectra for industrial/biosignature molecular bands
    (`NO2`, `N2O`, `CH4_C2H6`, `CO_13CO`) vs natural atmospheric/ISM confounders (`H2O_NIR`,
    `CO2_4P26`, `H2_0_0_S9_VIB`, `DUST_SIL_SLOPE`) after trimming `0.06 um` around NRS1/NRS2 edges.
    """
    cfg_eff = cfg or BASE_V5_1_CONFIG
    min_sigma = float(cfg_eff.get("nirspec_ccf_min_sigma", 5.0))
    min_conf_ratio = float(cfg_eff.get("nirspec_ccf_min_confounder_ratio", 1.5))
    trim_um = float(cfg_eff.get("nirspec_edge_trim_um", 0.06))

    w = np.asarray(wave_um, dtype=np.float64)
    f = np.asarray(flux_norm_or_flam, dtype=np.float64)
    valid = np.isfinite(w) & np.isfinite(f) & (w > 2.5) & (w < 5.5)
    if int(np.sum(valid)) < 48:
        return {"molecules": {}, "confounders": {}, "max_confounder_sigma": 0.0, "detected_molecules": [], "any_detection": False}

    w_v = w[valid]
    f_v = f[valid]
    order = np.argsort(w_v)
    w_v = w_v[order]
    f_v = f_v[order]

    split_idx = np.where((np.diff(w_v) > 0.02) | (np.diff(w_v) < 0.0))[0] + 1
    bounds = [0] + list(split_idx) + [len(w_v)]
    segments: list[tuple[np.ndarray, np.ndarray]] = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        if (b - a) < 30:
            continue
        wa, fa = w_v[a:b], f_v[a:b]
        keep = (wa >= wa[0] + trim_um) & (wa <= wa[-1] - trim_um)
        if int(np.sum(keep)) >= 30 and (wa[keep][-1] - wa[keep][0]) >= 0.30:
            segments.append((wa[keep], fa[keep]))

    conf_res: dict[str, dict[str, float]] = {}
    max_conf = 0.0
    for cname, comps in NATURAL_NIRSPEC_CONFOUNDERS_UM.items():
        cres = _fit_miri_sideband_template(segments, comps)
        raw_s = float(cres["ccf_sigma_abs"])
        phys_s = max(0.0, abs(raw_s) if cname == "H2_0_0_S9_VIB" else raw_s)
        cres["physical_confounder_sigma"] = float(phys_s)
        conf_res[cname] = cres
        if cres["covered"]:
            max_conf = max(max_conf, phys_s)

    mol_res: dict[str, dict[str, Any]] = {}
    detected: list[str] = []
    for mname, comps in NIRSPEC_MOL_TEMPLATES_UM.items():
        mres = _fit_miri_sideband_template(segments, comps)
        ccf_s = float(mres["ccf_sigma_abs"])
        joint_vetoes: dict[str, Any] = {}
        passes = bool(mres["covered"] and ccf_s >= min_sigma)

        if mres["covered"]:
            for cname, ccomps in NATURAL_NIRSPEC_CONFOUNDERS_UM.items():
                is_em = cname == "H2_0_0_S9_VIB" and float(conf_res[cname]["ccf_sigma_abs"]) < 0.0
                jres = _joint_miri_confounder_test(segments, comps, ccomps, conf_is_emission=is_em)
                joint_vetoes[cname] = jres
                if jres.get("overlaps"):
                    zm = float(jres["ccf_mol_given_conf"])
                    zc = max(0.0, float(jres["ccf_conf_given_mol"]))
                    if not (zm >= min_sigma and zm > min_conf_ratio * zc):
                        passes = False
                else:
                    min_dist_um = min(abs(float(mc["mu_um"]) - float(cc["mu_um"])) for mc in comps for cc in ccomps)
                    if min_dist_um <= 0.35 and conf_res[cname]["covered"]:
                        c_phys = float(conf_res[cname]["physical_confounder_sigma"])
                        if not (ccf_s > min_conf_ratio * c_phys):
                            passes = False

        mres["joint_confounder_checks"] = joint_vetoes
        mres["passes_ccf"] = passes
        mol_res[mname] = mres
        if passes:
            detected.append(mname)

    return {
        "molecules": mol_res,
        "confounders": conf_res,
        "max_confounder_sigma": float(max_conf),
        "detected_molecules": detected,
        "any_detection": len(detected) > 0,
    }


# ===========================================================================
# TECHNOSIGNATURE V5.2 ENGINES (PHASE D094)
# ===========================================================================


def check_rousselot_oh_and_barycentric_v52(
    wave_obs_a: float,
    sigma_v_kms: float,
) -> dict[str, Any]:
    """Check whether topocentric wavelength falls on a Rousselot (2000) OH line or ground telluric/airglow line."""
    w = float(wave_obs_a)
    min_oh_kms = 1e18
    nearest_oh = math.nan
    for oh_a in ROUSSELOT_OH_HBAND_VAC_A:
        dv = abs(C_KMS * (w - float(oh_a)) / max(1.0, float(oh_a)))
        if dv < min_oh_kms:
            min_oh_kms = dv
            nearest_oh = float(oh_a)

    oh_tol_kms = max(25.0, 3.0 * float(sigma_v_kms))
    oh_hit = min_oh_kms <= oh_tol_kms

    ground_hit = False
    nearest_g = ""
    for line in GROUND_AIRGLOW_AND_TELLURIC_A:
        w_l = float(line["wave_A"])
        dv_g = abs(C_KMS * (w - w_l) / max(1.0, w_l))
        if dv_g <= max(float(line["half_width_kms"]), 3.0 * float(sigma_v_kms)):
            ground_hit = True
            nearest_g = str(line["name"])
            break

    return {
        "is_oh_or_sky": bool(oh_hit or ground_hit),
        "oh_hit": bool(oh_hit),
        "nearest_oh_a": float(nearest_oh),
        "oh_dv_kms": float(min_oh_kms),
        "ground_hit": bool(ground_hit),
        "nearest_ground": nearest_g,
    }


def scan_multiepoch_drift_chaining_v52(
    wave_rest: np.ndarray,
    z_epochs: np.ndarray,
    mjd_epochs: np.ndarray,
    v_obs_to_rest_epochs_kms: np.ndarray,
    cfg: dict[str, Any],
    star: str = "",
    star_idx: int = 0,
    z_rpca_mat: np.ndarray | None = None,
    bervs_cohort: np.ndarray | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """
    Engine 6b (`DRIFT_V52_MULTIEPOCH`): N >= 3 multi-epoch linear velocity-drift trajectory chaining.

    Searches for narrowband emission lines following `w_k = w_0 * (1 + [v_0 + v_dot * (t_k - t_0)] / c)`
    across `M_hit >= 3` distinct observation epochs (`dt > 0.01 d`), enforcing:
      1. Combined trajectory significance `Z_chain = sum(z_k) / sqrt(M_hit) >= 8.0` (`z_k >= 4.5` each),
      2. Linear velocity track residual `rms_resid_kms <= max(4.0, 1.8 * sigma_v_kms)` across `M_hit >= 3`,
      3. Non-stationary total drift excursion `3.0 <= |dv_span| <= 250.0 km/s` and stationary veto `< 2` epochs,
      4. Topocentric stationary veto (`obs_span_kms >= 2.5`) + Rousselot (2000) OH airglow veto at every epoch,
      5. Resolved PSF wing morphology check and leave-one-star-out RPCA spectral rarity `>= 0.65`.
    """
    w = np.asarray(wave_rest, dtype=np.float64)
    Z = np.asarray(z_epochs, dtype=np.float64)
    mjds = np.asarray(v := mjd_epochs, dtype=np.float64)
    del v
    v_o2r = np.asarray(v_obs_to_rest_epochs_kms, dtype=np.float64)

    if Z.ndim != 2 or Z.shape[0] < 3 or len(w) < 128:
        return [], {"n_epochs": int(Z.shape[0]) if Z.ndim == 2 else 0, "n_traj_evals": 0}

    ord_t = np.argsort(mjds)
    mjds = mjds[ord_t]
    Z = Z[ord_t]
    v_o2r = v_o2r[ord_t]
    n_ep, n_wave = Z.shape
    min_dt_days = float(cfg.get("drift_v52_min_dt_days", 0.01))
    if float(mjds[-1] - mjds[0]) <= 2.0 * min_dt_days:
        return [], {"n_epochs": int(n_ep), "n_traj_evals": 0}

    dw = float(np.median(np.diff(w)))
    if not math.isfinite(dw) or dw <= 0.0:
        return [], {"n_epochs": int(n_ep), "n_traj_evals": 0}

    dv_min_abs = float(cfg.get("drift_v52_min_abs_dv_kms", 3.0))
    dv_max_abs = float(cfg.get("drift_v52_max_abs_dv_kms", 250.0))
    epoch_min_z = float(cfg.get("drift_v52_epoch_min_z", 4.5))
    chain_min_z = float(cfg.get("drift_v52_chain_min_z", 8.0))
    stat_veto_dv = float(cfg.get("drift_v52_stat_veto_dv_kms", 3.0))
    stat_max_z = float(cfg.get("drift_v52_stat_max_z", 4.0))
    min_matched = int(cfg.get("drift_v52_min_matched_epochs", 3))
    min_rarity = float(cfg.get("g7_min_rarity_score", 0.65))
    sig_v = float(cfg.get("sigma_v_kms", 2.0))
    tol_kms = max(4.5, 2.2 * sig_v)
    lin_rms_max = max(4.0, 1.8 * sig_v)
    inst_name = str(cfg.get("instrument", ""))

    # Build per-epoch unmasked safe score arrays and NMS peak lists
    static_masks = [_is_masked_static_v50(w, cfg, float(v_o2r[k])) for k in range(n_ep)]
    z_safe = [np.where(np.isfinite(Z[k]) & (~static_masks[k]), Z[k], 0.0) for k in range(n_ep)]
    z_fin = [np.where(np.isfinite(Z[k]), Z[k], 0.0) for k in range(n_ep)]

    ep_peaks: list[list[int]] = []
    for k in range(n_ep):
        idx_raw = np.where(z_safe[k] >= epoch_min_z)[0]
        if len(idx_raw) == 0:
            ep_peaks.append([])
            continue
        order_pk = idx_raw[np.argsort(z_safe[k][idx_raw])[::-1]]
        taken = np.zeros(n_wave, dtype=bool)
        pks: list[int] = []
        for idx in order_pk:
            if taken[idx]:
                continue
            lo_n, hi_n = max(0, idx - 5), min(n_wave, idx + 6)
            if float(z_safe[k][idx]) >= float(np.max(z_safe[k][lo_n:hi_n])) - 1e-12:
                pks.append(int(idx))
                taken[lo_n:hi_n] = True
                if len(pks) >= 96:
                    break
        ep_peaks.append(pks)

    n_traj_evals = 0
    raw_cands: list[dict[str, Any]] = []
    seen_tracks: set[tuple[int, int, int]] = set()

    for e_i in range(n_ep):
        if not ep_peaks[e_i]:
            continue
        for e_j in range(e_i + 1, n_ep):
            dt_ij = float(mjds[e_j] - mjds[e_i])
            if dt_ij < min_dt_days or not ep_peaks[e_j]:
                continue
            for idx_i in ep_peaks[e_i]:
                wi = float(w[idx_i])
                tol_w_pair = wi * (1.25 * dv_max_abs / C_KMS)
                for idx_j in ep_peaks[e_j]:
                    wj = float(w[idx_j])
                    if abs(wj - wi) > tol_w_pair:
                        continue
                    n_traj_evals += 1
                    dv_ij = C_KMS * (wj - wi) / wi
                    vdot_pair = dv_ij / dt_ij

                    matched: list[tuple[int, int, float, float, float]] = []
                    for k in range(n_ep):
                        w_pred = wi * (1.0 + vdot_pair * (float(mjds[k]) - float(mjds[e_i])) / C_KMS)
                        if w_pred < w[0] or w_pred > w[-1]:
                            continue
                        tol_a = max(2.0 * dw, w_pred * (tol_kms / C_KMS))
                        j0 = int(np.searchsorted(w, w_pred - tol_a, side="left"))
                        j1 = int(np.searchsorted(w, w_pred + tol_a, side="right"))
                        if j1 <= j0 or not np.any(z_safe[k][j0:j1] >= epoch_min_z):
                            continue
                        jm = j0 + int(np.argmax(z_safe[k][j0:j1]))
                        matched.append((k, jm, float(mjds[k]), float(w[jm]), float(z_safe[k][jm])))

                    if len(matched) < min_matched:
                        continue
                    m_t = np.asarray([m[2] for m in matched], dtype=np.float64)
                    if float(m_t[-1] - m_t[0]) < 2.0 * min_dt_days:
                        continue
                    # Require at least 3 matched epochs separated by min_dt_days
                    distinct_t = [float(m_t[0])]
                    for tk in m_t[1:]:
                        if float(tk) - distinct_t[-1] >= min_dt_days:
                            distinct_t.append(float(tk))
                    if len(distinct_t) < min_matched:
                        continue

                    m_w = np.asarray([m[3] for m in matched], dtype=np.float64)
                    m_z = np.asarray([m[4] for m in matched], dtype=np.float64)
                    z_chain = float(np.sum(m_z) / math.sqrt(float(len(matched))))
                    if z_chain < chain_min_z:
                        continue

                    # Refit 2-param linear velocity trajectory u(t) = a + vdot * (t - t_mean)
                    w_ref = float(np.mean(m_w))
                    u_m = C_KMS * (m_w - w_ref) / w_ref
                    t_c = m_t - float(np.mean(m_t))
                    denom_t = float(np.dot(t_c, t_c))
                    if denom_t <= 1e-12:
                        continue
                    vdot_fit = float(np.dot(t_c, u_m) / denom_t)
                    u_hat = vdot_fit * t_c + float(np.mean(u_m))
                    rms_resid_kms = float(np.sqrt(np.mean((u_m - u_hat) ** 2)))
                    if rms_resid_kms > lin_rms_max:
                        continue

                    dv_span_kms = abs(vdot_fit) * float(m_t[-1] - m_t[0])
                    eff_dv_min = max(dv_min_abs, 1.5 * sig_v)
                    if dv_span_kms < eff_dv_min or dv_span_kms > dv_max_abs:
                        continue

                    # Track deduplication before expensive vetoes
                    t_key = (int(round(m_w[0] * 10.0)), int(round(m_w[-1] * 10.0)), len(matched))
                    if t_key in seen_tracks:
                        continue
                    seen_tracks.add(t_key)

                    # Rest-frame stationary veto: check well-separated distant epochs (>= max(stat_veto_dv, 2.2 * sigma_v))
                    # plus opposite-endpoint comparison when total span is in [1.5*sigma_v, 2.2*sigma_v)
                    stationary_veto = False
                    sep_clear_kms = max(stat_veto_dv, 2.2 * sig_v)
                    t_mean_m = float(np.mean(m_t))
                    u_mean_m = float(np.mean(u_m))
                    ep_first, ep_last = int(matched[0][0]), int(matched[-1][0])
                    for qi, mw in enumerate(m_w):
                        stat_hw_a = float(mw) * (stat_veto_dv / C_KMS) + 1.5 * dw
                        s0 = int(np.searchsorted(w, float(mw) - stat_hw_a, side="left"))
                        s1 = int(np.searchsorted(w, float(mw) + stat_hw_a, side="right"))
                        if s1 <= s0:
                            continue
                        n_dist_stat = 0
                        for k in range(n_ep):
                            u_pred_k = u_mean_m + vdot_fit * (float(mjds[k]) - t_mean_m)
                            w_pred_k = w_ref * (1.0 + u_pred_k / C_KMS)
                            dv_from_mw = abs(C_KMS * (w_pred_k - float(mw)) / max(1.0, float(mw)))
                            z_here = float(np.max(z_fin[k][s0:s1]))
                            if dv_from_mw >= sep_clear_kms and z_here >= stat_max_z:
                                n_dist_stat += 1
                            elif (qi == 0 and k == ep_last) or (qi == len(matched) - 1 and k == ep_first):
                                if z_here >= max(stat_max_z, 0.72 * float(m_z[qi])):
                                    n_dist_stat += 1
                        if n_dist_stat >= 1:
                            stationary_veto = True
                            break
                    if stationary_veto:
                        continue

                    # Topocentric frame shift + Rousselot (2000) OH veto
                    w_obs_m = np.asarray(
                        [float(m_w[q]) / (1.0 + float(v_o2r[matched[q][0]]) / C_KMS) for q in range(len(matched))],
                        dtype=np.float64,
                    )
                    obs_span_kms = float(C_KMS * (np.max(w_obs_m) - np.min(w_obs_m)) / max(1.0, float(np.mean(w_obs_m))))
                    if obs_span_kms < max(2.5, 0.75 * eff_dv_min):
                        continue
                    if not inst_name.startswith("JWST_"):
                        if any(check_rousselot_oh_and_barycentric_v52(float(wo), sig_v)["is_oh_or_sky"] for wo in w_obs_m):
                            continue

                    # Resolution-scaled single-epoch PSF morphology veto on matched peaks
                    morph_bad = False
                    for ep_k, idx_k, _, wk, zpk in matched:
                        sig_px = (wk * sig_v / C_KMS) / max(1e-6, dw)
                        hw_far = max(5, int(math.ceil(3.2 * sig_px)))
                        lo_p, hi_p = max(0, idx_k - hw_far), min(n_wave, idx_k + hw_far + 1)
                        win_k = Z[ep_k, lo_p:hi_p]
                        if len(win_k) >= 7 and np.all(np.isfinite(win_k)):
                            c_i = idx_k - lo_p
                            wing_max = max(float(win_k[max(0, c_i - 1)]), float(win_k[min(len(win_k) - 1, c_i + 1)]))
                            eta_1 = wing_max / max(1e-6, zpk)
                            if sig_px >= 0.7 and eta_1 < 0.08:
                                morph_bad = True
                                break
                            if (idx_k - lo_p) >= hw_far and (hi_p - 1 - idx_k) >= hw_far:
                                if max(float(win_k[0]), float(win_k[-1])) / max(1e-6, zpk) > 0.55:
                                    morph_bad = True
                                    break
                    if morph_bad:
                        continue

                    # Cross-star RPCA rarity score across matched endpoints & midpoint
                    rarity_min = 1.0
                    if z_rpca_mat is not None and bervs_cohort is not None and z_rpca_mat.shape[0] >= 2:
                        r_vals = [
                            float(compute_spectral_rarity_score(w, z_rpca_mat, bervs_cohort, star_idx, float(mw), sig_v, polarity=1.0)["rarity_score"])
                            for mw in m_w
                        ]
                        rarity_min = float(min(r_vals))
                        if rarity_min < min_rarity:
                            continue

                    vdot_ms_h = (vdot_fit * 1000.0) / 24.0
                    raw_cands.append({
                        "star": star,
                        "n_epochs_total": int(n_ep),
                        "n_epochs_matched": int(len(matched)),
                        "matched_epochs": [int(m[0]) for m in matched],
                        "wave_start_rest_a": round(float(m_w[0]), 5),
                        "wave_end_rest_a": round(float(m_w[-1]), 5),
                        "dv_span_kms": round(float(dv_span_kms), 4),
                        "obs_span_kms": round(float(obs_span_kms), 4),
                        "dt_days": round(float(m_t[-1] - m_t[0]), 6),
                        "vdot_kms_day": round(float(vdot_fit), 6),
                        "vdot_ms_h": round(float(vdot_ms_h), 4),
                        "rms_lin_resid_kms": round(float(rms_resid_kms), 4),
                        "z_min_epoch": round(float(np.min(m_z)), 4),
                        "z_mean_epoch": round(float(np.mean(m_z)), 4),
                        "z_drift_chain": round(float(z_chain), 4),
                        "rarity_min": round(float(rarity_min), 4),
                    })

    # Deduplicate overlapping tracks keeping highest Z_chain
    raw_cands.sort(key=lambda d: float(d["z_drift_chain"]), reverse=True)
    kept: list[dict[str, Any]] = []
    min_sep_a = max(0.4, 4.0 * dw * 10.0)
    for rc in raw_cands:
        if any(
            abs(float(rc["wave_start_rest_a"]) - float(k["wave_start_rest_a"])) < min_sep_a
            and abs(float(rc["wave_end_rest_a"]) - float(k["wave_end_rest_a"])) < min_sep_a
            for k in kept
        ):
            continue
        kept.append(rc)

    return kept, {
        "n_epochs": int(n_ep),
        "n_traj_evals": int(n_traj_evals),
        "n_peaks_total": int(sum(len(p) for p in ep_peaks)),
    }


def _extract_g8_feat_v52(
    z_vec: np.ndarray,
    idx: int,
    z_rpca: float,
    rarity: float,
    f_rest: float,
    f_topo: float,
    half_px: int = 8,
) -> tuple[np.ndarray, dict[str, float]] | None:
    """Standardized 13-pixel arcsinh patch + 8 morphological/RPCA/sparsity features for Gate G8_V52."""
    n = len(z_vec)
    if idx < half_px or idx + half_px >= n:
        return None
    sub = np.asarray(z_vec[idx - half_px : idx + half_px + 1], dtype=np.float64)
    if not np.all(np.isfinite(sub)):
        return None
    core = sub[half_px - 2 : half_px + 3]
    wings = np.concatenate([sub[: half_px - 3], sub[half_px + 4 :]])
    pk = float(np.max(core))
    wing_rms = float(np.sqrt(np.mean(wings ** 2)))
    wing_min = float(np.min(sub))
    e_conc = float(np.sum(np.maximum(0.0, core) ** 2) / max(1e-6, float(np.sum(sub ** 2))))
    patch_comp = np.arcsinh(sub[half_px - 6 : half_px + 7] / 2.5)
    meta = np.asarray([
        math.asinh(float(z_rpca) / 3.0),
        float(rarity),
        float(f_rest),
        float(f_topo),
        e_conc,
        math.log1p(max(0.0, wing_rms)),
        max(-3.0, min(3.0, wing_min / 3.0)),
        max(0.0, pk / max(1.0, wing_rms + 0.5)) / 5.0,
    ], dtype=np.float64)
    return np.concatenate([patch_comp, meta]), {
        "e_conc": e_conc,
        "wing_rms": wing_rms,
        "wing_min": wing_min,
        "pk": pk,
    }


def fit_patch_novelty_model_v52(
    feats: list[np.ndarray] | np.ndarray,
    pca_dim: int = 8,
    knn_k: int = 7,
    min_novelty_z: float = 3.5,
) -> dict[str, Any]:
    """Fit standardized PCA-whitened k-NN + reconstruction-residual novelty model for Gate G8_V52."""
    arr = np.asarray(feats, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[0] < max(24, int(knn_k) + 4):
        return {
            "ready": False,
            "n_ref": int(arr.shape[0]) if arr.ndim == 2 else 0,
            "min_novelty_z": float(min_novelty_z),
        }
    mu = np.mean(arr, axis=0)
    sd = np.maximum(0.08, np.std(arr, axis=0))
    xs = (arr - mu[None, :]) / sd[None, :]
    evals, evecs = np.linalg.eigh((xs.T @ xs) / max(1.0, float(arr.shape[0] - 1)))
    ord_idx = np.argsort(evals)[::-1]
    k_pca = min(int(pca_dim), arr.shape[1])
    evals_k = np.maximum(0.05, evals[ord_idx[:k_pca]])
    basis_k = evecs[:, ord_idx[:k_pca]]
    proj = (xs @ basis_k) / np.sqrt(evals_k)[None, :]
    rec_err = np.linalg.norm(xs - (xs @ basis_k) @ basis_k.T, axis=1)
    diff2 = np.sum(proj * proj, axis=1, keepdims=True) + np.sum(proj * proj, axis=1)[None, :] - 2.0 * (proj @ proj.T)
    np.fill_diagonal(diff2, 1e18)
    k_eff = min(int(knn_k), arr.shape[0] - 1)
    kth_d = np.sqrt(np.partition(np.maximum(0.0, diff2), k_eff - 1, axis=1)[:, k_eff - 1])
    score = np.hypot(kth_d, rec_err)
    ref_med = float(np.median(score))
    ref_mad = max(0.10, MAD_NORM * float(np.median(np.abs(score - ref_med))))
    return {
        "ready": True,
        "n_ref": int(arr.shape[0]),
        "pca_dim": int(k_pca),
        "knn_k": int(k_eff),
        "min_novelty_z": float(min_novelty_z),
        "mu": mu,
        "sd": sd,
        "basis_k": basis_k,
        "inv_sqrt_evals": 1.0 / np.sqrt(evals_k),
        "proj_ref": proj,
        "ref_med": ref_med,
        "ref_mad": ref_mad,
    }


def evaluate_gate_g8_v52(
    model: dict[str, Any],
    wave_rest: np.ndarray,
    z_vec: np.ndarray,
    center_wave_a: float,
    z_rpca: float,
    rarity_score: float,
    f_rest: float = 0.0,
    f_topo: float = 0.0,
) -> dict[str, Any]:
    """Evaluate Gate G8_V52 local patch novelty with clean PSF concentration/wing morphological guards."""
    if not model.get("ready"):
        return {"g8_pass": True, "novelty_z": 99.0, "knn_dist": 0.0, "reason": "NO_REF_PASS"}
    w = np.asarray(wave_rest, dtype=np.float64)
    idx = max(0, min(len(w) - 1, int(np.searchsorted(w, float(center_wave_a)))))
    res_f = _extract_g8_feat_v52(z_vec, idx, float(z_rpca), float(rarity_score), float(f_rest), float(f_topo))
    if res_f is None:
        return {"g8_pass": False, "novelty_z": 0.0, "knn_dist": 0.0, "reason": "G8_EDGE_NAN"}
    vec, info = res_f
    xs = (vec - model["mu"]) / model["sd"]
    p = (xs @ model["basis_k"]) * model["inv_sqrt_evals"]
    rec_err = float(np.linalg.norm(xs - (xs @ model["basis_k"]) @ model["basis_k"].T))
    d2 = np.sum((model["proj_ref"] - p[None, :]) ** 2, axis=1)
    k_eff = min(int(model["knn_k"]), len(d2) - 1)
    d_k = math.sqrt(max(0.0, float(np.partition(d2, k_eff - 1)[k_eff - 1])))
    nov_z = (math.hypot(d_k, rec_err) - float(model["ref_med"])) / max(1e-6, float(model["ref_mad"]))
    clean_morph = (
        float(z_rpca) >= 6.0
        and float(rarity_score) >= 0.65
        and float(f_rest) <= 0.30
        and float(f_topo) <= 0.30
        and info["e_conc"] >= 0.85
        and info["wing_rms"] <= 1.35
        and info["wing_min"] >= -2.5
    )
    passed = bool(clean_morph and math.isfinite(nov_z) and nov_z >= float(model.get("min_novelty_z", 3.5)))
    return {
        "g8_pass": passed,
        "novelty_z": float(nov_z),
        "knn_dist": float(d_k),
        "reason": "PASS" if passed else ("G8_MORPH_CONTAMINATED" if not clean_morph else "G8_LOW_PATCH_NOVELTY"),
    }


# ---------------------------------------------------------------------------
# Engine 9b / 10 (V5.2): Unified Union-Excluded IR Molecular CCF (NIRSpec + MIRI LRS)
# ---------------------------------------------------------------------------

GREENHOUSE_GAS_TEMPLATES_LRS_UM: dict[str, list[dict[str, float]]] = {
    **GREENHOUSE_GAS_TEMPLATES_UM,
    "CFC11_CCL3F": [
        {"mu_um": 9.22, "sigma_um": 0.18, "weight": 0.55},
        {"mu_um": 11.82, "sigma_um": 0.22, "weight": 0.45},
    ],
}

NATURAL_MIRI_LRS_CONFOUNDERS_UM: dict[str, list[dict[str, float]]] = {
    "H2O_6P2_LRS": [{"mu_um": 6.25, "sigma_um": 0.32, "weight": 1.0}],
    "CH4_ATM": NATURAL_MIRI_CONFOUNDER_TEMPLATES_UM["CH4_ATM"],
    "NH3_LRS": [
        {"mu_um": 10.35, "sigma_um": 0.22, "weight": 0.55},
        {"mu_um": 10.72, "sigma_um": 0.22, "weight": 0.45},
    ],
    "O3_ATM": NATURAL_MIRI_CONFOUNDER_TEMPLATES_UM["O3_ATM"],
    "SILICATE_BROAD": NATURAL_MIRI_CONFOUNDER_TEMPLATES_UM["SILICATE_BROAD"],
    "PAH_EMISSION": NATURAL_MIRI_CONFOUNDER_TEMPLATES_UM["PAH_EMISSION"],
}


def _fit_ir_loglog_continuum_v52(
    w_seg: np.ndarray,
    f_seg: np.ndarray,
    win_mask: np.ndarray,
    sb_mask: np.ndarray,
    mu_center: float,
    min_sb_bins: int = 8,
    min_win_bins: int = 6,
    min_side_bins: int = 3,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None:
    """Parameterized power-law continuum fitter for both NIRSpec (R~2700) and MIRI LRS (R~100)."""
    w_sb = w_seg[sb_mask]
    f_sb = f_seg[sb_mask]
    w_win = w_seg[win_mask]
    if len(w_sb) < int(min_sb_bins) or len(w_win) < int(min_win_bins) or (float(np.max(w_sb)) - float(np.min(w_sb))) < 0.20:
        return None
    mu_sb = float(np.mean(w_sb))
    has_two_sides = int(np.sum(w_sb < mu_center)) >= int(min_side_bins) and int(np.sum(w_sb > mu_center)) >= int(min_side_bins)
    deg = 2 if (has_two_sides and len(w_sb) >= max(12, int(min_sb_bins) + 4)) else 1

    if np.all(f_sb > 0.0) and np.all(w_sb > 0.0) and np.all(w_win > 0.0):
        lw_sb = np.log(w_sb)
        lw_mid = float(np.mean(lw_sb))
        x_sb = lw_sb - lw_mid
        x_win = np.log(w_win) - lw_mid
        try:
            coeffs = np.polyfit(x_sb, np.log(f_sb), deg)
            cont_sb = np.exp(np.clip(np.polyval(coeffs, x_sb), -120.0, 120.0))
            cont_win = np.exp(np.clip(np.polyval(coeffs, x_win), -120.0, 120.0))
            return cont_win, cont_sb, np.vander(x_win, deg + 1), np.vander(x_sb, deg + 1)
        except (np.linalg.LinAlgError, ValueError):
            pass

    try:
        x_lin_sb = w_sb - mu_sb
        x_lin_win = w_win - mu_sb
        coeffs = np.polyfit(x_lin_sb, f_sb, deg)
        return np.polyval(coeffs, x_lin_win), np.polyval(coeffs, x_lin_sb), np.vander(x_lin_win, deg + 1), np.vander(x_lin_sb, deg + 1)
    except (np.linalg.LinAlgError, ValueError):
        return None


def _fit_ir_mol_template_v52(
    segments: list[tuple[np.ndarray, np.ndarray]],
    comps: list[dict[str, float]],
    min_core_bins: int = 12,
    min_sb_bins: int = 16,
    min_win_bins: int = 12,
    min_side_bins: int = 6,
    sb_pad_mult: float = 3.0,
) -> dict[str, Any]:
    """Union-excluded sideband CCF for single- or multi-component IR templates."""
    num_sum = t2_sum = var_sum = w_sum_cov = 0.0
    n_cov = 0
    seg_to_comps: dict[int, list[dict[str, float]]] = {}
    for comp in comps:
        mu, sig = float(comp["mu_um"]), float(comp["sigma_um"])
        best_si: int | None = None
        best_n = 0
        for si, (w_seg, _) in enumerate(segments):
            nc = int(np.sum(np.abs(w_seg - mu) <= 2.2 * sig))
            if nc >= int(min_core_bins) and nc > best_n:
                best_n, best_si = nc, si
        if best_si is not None:
            seg_to_comps.setdefault(best_si, []).append(comp)

    for si, sc in seg_to_comps.items():
        w_seg, f_seg = segments[si]
        lo_core = min(float(c["mu_um"]) - 2.0 * float(c["sigma_um"]) for c in sc)
        hi_core = max(float(c["mu_um"]) + 2.0 * float(c["sigma_um"]) for c in sc)
        sig_max = max(float(c["sigma_um"]) for c in sc)
        core_mask = np.zeros(len(w_seg), dtype=bool)
        for c in sc:
            core_mask |= np.abs(w_seg - float(c["mu_um"])) < 2.0 * float(c["sigma_um"])
        win_mask = (w_seg >= lo_core - sb_pad_mult * sig_max) & (w_seg <= hi_core + sb_pad_mult * sig_max)
        sb_mask = win_mask & (~core_mask)
        if int(np.sum(sb_mask)) < int(min_sb_bins):
            win_mask = (w_seg >= lo_core - (sb_pad_mult + 1.5) * sig_max) & (w_seg <= hi_core + (sb_pad_mult + 1.5) * sig_max)
            sb_mask = win_mask & (~core_mask)
        fit_c = _fit_ir_loglog_continuum_v52(
            w_seg, f_seg, win_mask, sb_mask, 0.5 * (lo_core + hi_core),
            min_sb_bins=max(6, int(min_sb_bins) - 4), min_win_bins=min_win_bins, min_side_bins=min_side_bins,
        )
        if fit_c is None:
            continue
        cont_win, cont_sb, X_win, X_sb = fit_c
        safe_sb = np.abs(cont_sb) > 1e-30
        safe_win = np.abs(cont_win) > 1e-30
        if int(np.sum(safe_sb)) < max(6, int(min_sb_bins) - 4) or int(np.sum(safe_win)) < int(min_win_bins):
            continue
        r_sb = (f_seg[sb_mask][safe_sb] - cont_sb[safe_sb]) / np.abs(cont_sb[safe_sb])
        r_win = (f_seg[win_mask][safe_win] - cont_win[safe_win]) / np.abs(cont_win[safe_win])
        w_win = w_seg[win_mask][safe_win]
        w_sb_safe = w_seg[sb_mask][safe_sb]
        sigma_sb = _sideband_noise_sigma(r_sb)

        T_vec = np.zeros_like(w_win)
        T_sb = np.zeros_like(w_sb_safe)
        for c in sc:
            T_vec += float(c["weight"]) * np.exp(-0.5 * ((w_win - float(c["mu_um"])) / float(c["sigma_um"])) ** 2)
            T_sb += float(c["weight"]) * np.exp(-0.5 * ((w_sb_safe - float(c["mu_um"])) / float(c["sigma_um"])) ** 2)
        T_vec = T_vec - float(np.median(T_sb))
        t2 = float(np.dot(T_vec, T_vec))
        if t2 <= 1e-12:
            continue
        X_sb_s = X_sb[safe_sb]
        X_win_s = X_win[safe_win]
        g_proj = X_win_s.T @ T_vec
        try:
            var_cont = max(0.0, float(g_proj.T @ np.linalg.solve(X_sb_s.T @ X_sb_s + 1e-9 * np.eye(X_sb_s.shape[1]), g_proj)))
        except np.linalg.LinAlgError:
            var_cont = 0.0
        num_sum += float(np.dot(T_vec, r_win))
        t2_sum += t2
        var_sum += (sigma_sb ** 2) * (t2 + var_cont)
        n_cov += len(sc)
        w_sum_cov += sum(float(c["weight"]) for c in sc)

    if n_cov == 0 or t2_sum <= 1e-12 or var_sum <= 1e-30:
        return {
            "covered": False, "n_components": 0, "depth": 0.0, "sigma_depth": math.nan,
            "ccf_sigma_abs": 0.0, "delta_min_5sigma": math.nan, "ppm_equiv_10pct_ref": math.nan,
        }
    w_scale = max(1e-6, w_sum_cov / float(n_cov))
    depth = -(num_sum / t2_sum) * w_scale
    sigma_depth = (math.sqrt(var_sum) / t2_sum) * w_scale
    ccf_s = depth / max(1e-12, sigma_depth)
    d5 = min(1.0, 5.0 * sigma_depth)
    return {
        "covered": True, "n_components": int(n_cov), "depth": float(depth), "sigma_depth": float(sigma_depth),
        "ccf_sigma_abs": float(ccf_s), "delta_min_5sigma": float(d5),
        "ppm_equiv_10pct_ref": float(10.0 * (d5 / 0.10)),
    }


def _joint_ir_confounder_v52(
    segments: list[tuple[np.ndarray, np.ndarray]],
    mol_comps: list[dict[str, float]],
    conf_comps: list[dict[str, float]],
    conf_is_emission: bool = False,
    min_sb_bins: int = 16,
    min_win_bins: int = 12,
    min_side_bins: int = 6,
    sb_pad_mult: float = 3.0,
) -> dict[str, Any]:
    """Joint 2-parameter OLS of multi-component molecule vs natural confounder across IR segments."""
    overlaps = any(
        abs(float(mc["mu_um"]) - float(cc["mu_um"])) <= 2.5 * (float(mc["sigma_um"]) + float(cc["sigma_um"]))
        for mc in mol_comps for cc in conf_comps
    )
    if not overlaps:
        return {"overlaps": False}

    xtx_tot = np.zeros((2, 2), dtype=np.float64)
    xty_tot = np.zeros(2, dtype=np.float64)
    cov_num = np.zeros((2, 2), dtype=np.float64)
    n_seg_used = 0

    for w_seg, f_seg in segments:
        mc_in = [c for c in mol_comps if w_seg[0] + 0.02 < float(c["mu_um"]) < w_seg[-1] - 0.02]
        cc_in = [c for c in conf_comps if w_seg[0] + 0.02 < float(c["mu_um"]) < w_seg[-1] - 0.02]
        if not mc_in or not cc_in:
            continue
        all_c = mc_in + cc_in
        lo_core = min(float(c["mu_um"]) - 2.0 * float(c["sigma_um"]) for c in all_c)
        hi_core = max(float(c["mu_um"]) + 2.0 * float(c["sigma_um"]) for c in all_c)
        sig_max = max(float(c["sigma_um"]) for c in all_c)
        core_mask = np.zeros(len(w_seg), dtype=bool)
        for c in all_c:
            core_mask |= np.abs(w_seg - float(c["mu_um"])) < 2.0 * float(c["sigma_um"])
        win_mask = (w_seg >= lo_core - sb_pad_mult * sig_max) & (w_seg <= hi_core + sb_pad_mult * sig_max)
        sb_mask = win_mask & (~core_mask)
        if int(np.sum(sb_mask)) < int(min_sb_bins):
            win_mask = (w_seg >= lo_core - (sb_pad_mult + 1.5) * sig_max) & (w_seg <= hi_core + (sb_pad_mult + 1.5) * sig_max)
            sb_mask = win_mask & (~core_mask)
        fit_c = _fit_ir_loglog_continuum_v52(
            w_seg, f_seg, win_mask, sb_mask, 0.5 * (lo_core + hi_core),
            min_sb_bins=max(6, int(min_sb_bins) - 4), min_win_bins=min_win_bins, min_side_bins=min_side_bins,
        )
        if fit_c is None:
            continue
        cont_win, cont_sb, X_win, X_sb = fit_c
        safe_sb = np.abs(cont_sb) > 1e-30
        safe_win = np.abs(cont_win) > 1e-30
        if int(np.sum(safe_sb)) < max(6, int(min_sb_bins) - 4) or int(np.sum(safe_win)) < int(min_win_bins):
            continue
        r_sb = (f_seg[sb_mask][safe_sb] - cont_sb[safe_sb]) / np.abs(cont_sb[safe_sb])
        y_abs = -(f_seg[win_mask][safe_win] - cont_win[safe_win]) / np.abs(cont_win[safe_win])
        w_win = w_seg[win_mask][safe_win]
        sigma_sb = _sideband_noise_sigma(r_sb)
        tm = sum(float(c["weight"]) * np.exp(-0.5 * ((w_win - float(c["mu_um"])) / float(c["sigma_um"])) ** 2) for c in mc_in)
        tc = sum(float(c["weight"]) * np.exp(-0.5 * ((w_win - float(c["mu_um"])) / float(c["sigma_um"])) ** 2) for c in cc_in)
        X = np.column_stack([tm, tc])
        xtx = X.T @ X
        X_sb_s, X_win_s = X_sb[safe_sb], X_win[safe_win]
        G = X_win_s.T @ X
        try:
            cov_c = G.T @ np.linalg.solve(X_sb_s.T @ X_sb_s + 1e-9 * np.eye(X_sb_s.shape[1]), G)
        except np.linalg.LinAlgError:
            cov_c = np.zeros((2, 2), dtype=np.float64)
        xtx_tot += xtx
        xty_tot += X.T @ y_abs
        cov_num += (sigma_sb ** 2) * (xtx + cov_c)
        n_seg_used += 1

    if n_seg_used == 0 or np.linalg.cond(xtx_tot + 1e-9 * np.eye(2)) > 1e4:
        return {"overlaps": False}
    try:
        inv_xtx = np.linalg.inv(xtx_tot + 1e-9 * np.eye(2))
        beta = inv_xtx @ xty_tot
        var_beta = inv_xtx @ cov_num @ inv_xtx
    except np.linalg.LinAlgError:
        return {"overlaps": False}
    z_m = float(beta[0] / max(1e-12, math.sqrt(max(0.0, float(var_beta[0, 0])))))
    z_c = float(beta[1] / max(1e-12, math.sqrt(max(0.0, float(var_beta[1, 1])))))
    return {"overlaps": True, "ccf_mol_given_conf": z_m, "ccf_conf_given_mol": (-z_c if conf_is_emission else z_c)}


def _run_ir_ccf_suite_v52(
    segments: list[tuple[np.ndarray, np.ndarray]],
    mol_templates: dict[str, list[dict[str, float]]],
    conf_templates: dict[str, list[dict[str, float]]],
    emission_conf_names: set[str],
    min_sigma: float,
    min_conf_ratio: float,
    prox_dist_um: float,
    min_core_bins: int,
    min_sb_bins: int,
    min_win_bins: int,
    min_side_bins: int,
    sb_pad_mult: float,
) -> dict[str, Any]:
    """Shared IR molecular CCF evaluator for NIRSpec G395H and MIRI LRS P750L."""
    if not segments:
        return {"molecules": {}, "confounders": {}, "max_confounder_sigma": 0.0, "detected_molecules": [], "any_detection": False}

    conf_res: dict[str, dict[str, Any]] = {}
    max_conf = 0.0
    for cn, cc in conf_templates.items():
        cr = _fit_ir_mol_template_v52(
            segments, cc, min_core_bins=min_core_bins, min_sb_bins=min_sb_bins,
            min_win_bins=min_win_bins, min_side_bins=min_side_bins, sb_pad_mult=sb_pad_mult,
        )
        raw_s = float(cr["ccf_sigma_abs"])
        if cn in emission_conf_names:
            phys_s = max(0.0, -raw_s if cn == "PAH_EMISSION" else abs(raw_s))
        else:
            phys_s = max(0.0, raw_s)
        cr["physical_confounder_sigma"] = float(phys_s)
        conf_res[cn] = cr
        if cr["covered"]:
            max_conf = max(max_conf, phys_s)

    mol_res: dict[str, dict[str, Any]] = {}
    dets: list[str] = []
    for mn, mc in mol_templates.items():
        mr = _fit_ir_mol_template_v52(
            segments, mc, min_core_bins=min_core_bins, min_sb_bins=min_sb_bins,
            min_win_bins=min_win_bins, min_side_bins=min_side_bins, sb_pad_mult=sb_pad_mult,
        )
        s = float(mr["ccf_sigma_abs"])
        ok = bool(mr["covered"] and s >= float(min_sigma))
        joint_vetoes: dict[str, Any] = {}
        if mr["covered"]:
            for cn, cc in conf_templates.items():
                is_em = cn in emission_conf_names and float(conf_res[cn]["ccf_sigma_abs"]) < 0.0
                jr = _joint_ir_confounder_v52(
                    segments, mc, cc, conf_is_emission=is_em, min_sb_bins=min_sb_bins,
                    min_win_bins=min_win_bins, min_side_bins=min_side_bins, sb_pad_mult=sb_pad_mult,
                )
                joint_vetoes[cn] = jr
                if jr.get("overlaps"):
                    zm = float(jr["ccf_mol_given_conf"])
                    zc = max(0.0, float(jr["ccf_conf_given_mol"]))
                    if not (zm >= float(min_sigma) and zm > float(min_conf_ratio) * zc):
                        ok = False
                else:
                    md = min(abs(float(a["mu_um"]) - float(b["mu_um"])) for a in mc for b in cc)
                    if md <= float(prox_dist_um) and conf_res[cn]["covered"]:
                        if not (s > float(min_conf_ratio) * float(conf_res[cn]["physical_confounder_sigma"])):
                            ok = False
        mr["joint_confounder_checks"] = joint_vetoes
        mr["passes_ccf"] = ok
        mol_res[mn] = mr
        if ok:
            dets.append(mn)
    return {
        "molecules": mol_res,
        "confounders": conf_res,
        "max_confounder_sigma": float(max_conf),
        "detected_molecules": dets,
        "any_detection": len(dets) > 0,
    }


def scan_nirspec_molecular_ccf_v52(
    wave_um: np.ndarray,
    flux_norm_or_flam: np.ndarray,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stage-1 baked union-excluded JWST NIRSpec G395H (`2.86-5.27 um`) molecular CCF."""
    cfg_eff = cfg or BASE_V5_2_CONFIG
    min_sigma = float(cfg_eff.get("nirspec_ccf_min_sigma", 5.0))
    min_conf_ratio = float(cfg_eff.get("nirspec_ccf_min_confounder_ratio", 1.5))
    trim_um = float(cfg_eff.get("nirspec_edge_trim_um", 0.06))

    w = np.asarray(wave_um, dtype=np.float64)
    f = np.asarray(flux_norm_or_flam, dtype=np.float64)
    valid = np.isfinite(w) & np.isfinite(f) & (w > 2.5) & (w < 5.6)
    if int(np.sum(valid)) < 48:
        return {"molecules": {}, "confounders": {}, "max_confounder_sigma": 0.0, "detected_molecules": [], "any_detection": False}

    w_v, f_v = w[valid], f[valid]
    order = np.argsort(w_v)
    w_v, f_v = w_v[order], f_v[order]
    split_idx = np.where((np.diff(w_v) > 0.02) | (np.diff(w_v) < 0.0))[0] + 1
    bounds = [0] + list(split_idx) + [len(w_v)]
    segments: list[tuple[np.ndarray, np.ndarray]] = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        if (b - a) < 30:
            continue
        wa, fa = w_v[a:b], f_v[a:b]
        keep = (wa >= wa[0] + trim_um) & (wa <= wa[-1] - trim_um)
        if int(np.sum(keep)) >= 30 and (wa[keep][-1] - wa[keep][0]) >= 0.30:
            segments.append((wa[keep], fa[keep]))

    return _run_ir_ccf_suite_v52(
        segments, NIRSPEC_MOL_TEMPLATES_UM, NATURAL_NIRSPEC_CONFOUNDERS_UM,
        emission_conf_names={"H2_0_0_S9_VIB"}, min_sigma=min_sigma, min_conf_ratio=min_conf_ratio,
        prox_dist_um=0.35, min_core_bins=12, min_sb_bins=16, min_win_bins=12, min_side_bins=6, sb_pad_mult=3.0,
    )


def scan_miri_lrs_v52_ccf(
    wave_um: np.ndarray,
    flux_norm_or_flam: np.ndarray,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Engine 10 (`MIRI_LRS_CCF_V52`): JWST MIRI LRS (`5.0-12.0 um`, R~100) union-excluded molecular CCF."""
    cfg_eff = cfg or BASE_V5_2_CONFIG
    min_sigma = float(cfg_eff.get("miri_lrs_ccf_min_sigma", 5.0))
    min_conf_ratio = float(cfg_eff.get("miri_lrs_ccf_min_confounder_ratio", 1.5))
    min_core = int(cfg_eff.get("miri_lrs_min_core_bins", 4))
    min_sb = int(cfg_eff.get("miri_lrs_min_sb_bins", 8))

    w = np.asarray(wave_um, dtype=np.float64)
    f = np.asarray(flux_norm_or_flam, dtype=np.float64)
    valid = np.isfinite(w) & np.isfinite(f) & (w >= 4.90) & (w <= 12.20)
    if int(np.sum(valid)) < 24:
        return {"molecules": {}, "confounders": {}, "max_confounder_sigma": 0.0, "detected_molecules": [], "any_detection": False}

    w_v, f_v = w[valid], f[valid]
    order = np.argsort(w_v)
    w_v, f_v = w_v[order], f_v[order]
    split_idx = np.where((np.diff(w_v) > 0.35) | (np.diff(w_v) < 0.0))[0] + 1
    bounds = [0] + list(split_idx) + [len(w_v)]
    segments: list[tuple[np.ndarray, np.ndarray]] = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        if (b - a) >= 20 and (w_v[b - 1] - w_v[a]) >= 0.60:
            segments.append((w_v[a:b], f_v[a:b]))

    return _run_ir_ccf_suite_v52(
        segments, GREENHOUSE_GAS_TEMPLATES_LRS_UM, NATURAL_MIRI_LRS_CONFOUNDERS_UM,
        emission_conf_names={"PAH_EMISSION"}, min_sigma=min_sigma, min_conf_ratio=min_conf_ratio,
        prox_dist_um=1.2, min_core_bins=min_core, min_sb_bins=min_sb, min_win_bins=6, min_side_bins=3, sb_pad_mult=4.0,
    )


# ===========================================================================
# TECHNOSIGNATURE V5.3 ENGINES
# ===========================================================================


SPITZER_IRS_GREENHOUSE_TEMPLATES_UM: dict[str, list[dict[str, float]]] = {
    **GREENHOUSE_GAS_TEMPLATES_LRS_UM,
    "CFC12_CCL2F2": [
        {"mu_um": 8.68, "sigma_um": 0.18, "weight": 0.45},
        {"mu_um": 10.84, "sigma_um": 0.20, "weight": 0.30},
        {"mu_um": 11.30, "sigma_um": 0.20, "weight": 0.25},
    ],
}

SPITZER_IRS_CONFOUNDERS_UM: dict[str, list[dict[str, float]]] = {
    "H2O_6P2_LRS": [{"mu_um": 6.25, "sigma_um": 0.32, "weight": 1.0}],
    "CH4_ATM": [{"mu_um": 7.66, "sigma_um": 0.28, "weight": 1.0}],
    "NH3_10P5UM": [
        {"mu_um": 10.35, "sigma_um": 0.22, "weight": 0.55},
        {"mu_um": 10.72, "sigma_um": 0.22, "weight": 0.45},
    ],
    "SILICATE_10UM": [{"mu_um": 9.85, "sigma_um": 0.95, "weight": 1.0}],
    "SILICATE_18UM": [{"mu_um": 18.20, "sigma_um": 1.65, "weight": 1.0}],
    "PAH_COMPLEX": [
        {"mu_um": 7.70, "sigma_um": 0.25, "weight": 0.40},
        {"mu_um": 8.60, "sigma_um": 0.20, "weight": 0.20},
        {"mu_um": 11.30, "sigma_um": 0.22, "weight": 0.40},
    ],
    "CO2_15UM": [{"mu_um": 14.98, "sigma_um": 0.35, "weight": 1.0}],
}


def apply_ghost_sky_fiber_veto_v53(
    star_wave_a: np.ndarray,
    star_z: float,
    sky_wave_a: np.ndarray,
    sky_flux: np.ndarray,
    sky_err: np.ndarray,
    cand_wave_a: float,
    fwhm_a: float,
    max_sky_z: float = 3.0,
) -> dict[str, Any]:
    """
    Engine 11 (`GHOST_SKY_FIBER_VETO_V53`): simultaneous Gemini/GHOST sky-IFU confirmation/veto.

    Evaluates HDU[4] SCI & HDU[5] VAR in the same topocentric air-wavelength frame (`AWAV-LOG`)
    within +/- 1.5 * FWHM around `cand_wave_a`. Any feature present at |sky_z| > `max_sky_z` (3.0)
    is rejected as sky airglow or telluric emission (`GHOST_SKY_FIBER_VETO`).
    """
    del star_wave_a
    sw = np.asarray(sky_wave_a, dtype=np.float64)
    sf = np.asarray(sky_flux, dtype=np.float64)
    se = np.asarray(sky_err, dtype=np.float64)
    hw = max(0.35, 1.5 * float(fwhm_a))
    # Compute local sky continuum + MAD on a clean flanking annulus and peak within core
    bg_m = np.isfinite(sw) & np.isfinite(sf) & np.isfinite(se) & (np.abs(sw - float(cand_wave_a)) <= max(3.5, 12.0 * float(fwhm_a)))
    core_m = np.isfinite(sw) & np.isfinite(sf) & np.isfinite(se) & (np.abs(sw - float(cand_wave_a)) <= hw)
    if int(np.sum(core_m)) < 1 or int(np.sum(bg_m)) < 8:
        return {"vetoed": False, "sky_z_max": 0.0, "star_z": float(star_z), "sky_star_ratio": 0.0, "reason": "SKY_NO_COVERAGE_PASS"}
    bg_vals = sf[bg_m]
    med_bg = exact_median_1d(bg_vals)
    mad_bg = max(1e-12, exact_mad_1d(bg_vals))
    eff_sig = np.maximum(mad_bg, np.where(se[core_m] > 0.0, se[core_m], mad_bg))
    sky_z_vals = np.abs(sf[core_m] - med_bg) / eff_sig
    sky_z_max = float(np.max(sky_z_vals))
    vetoed = bool(sky_z_max > float(max_sky_z))
    return {
        "vetoed": vetoed,
        "sky_z_max": round(sky_z_max, 4),
        "star_z": round(float(star_z), 4),
        "sky_star_ratio": round(sky_z_max / max(1e-6, abs(float(star_z))), 4),
        "reason": "GHOST_SKY_FIBER_VETO" if vetoed else "PASS",
    }


def _tier2_multiepoch_lsf_check_v53(
    wave_rest: np.ndarray,
    fn_epochs: np.ndarray,
    sig_epochs: np.ndarray,
    ep_peaks: list[tuple[int, int, float, float, float]],
    cfg: dict[str, Any],
) -> tuple[bool, dict[str, float]]:
    """Tier-2 multi-epoch LSF/F1 shape confirmation guarding curved & periodic drift tracks."""
    del sig_epochs
    amps: list[float] = []
    snrs: list[float] = []
    coss: list[float] = []
    fw_ratios: list[float] = []
    fn_pks: list[float] = []
    for ep_k, _, _, w_pk, _ in ep_peaks:
        w0 = float(w_pk)
        hw_a = max(2.5, w0 * (30.0 * float(cfg.get("sigma_v_kms", 5.0)) / C_KMS))
        i0 = int(np.searchsorted(wave_rest, w0 - hw_a, side="left"))
        i1 = int(np.searchsorted(wave_rest, w0 + hw_a, side="right"))
        if i1 - i0 < 20:
            return False, {"reason_fail": 1.0}
        w_sub = wave_rest[i0:i1]
        fn_sub = fn_epochs[ep_k, i0:i1]
        fit = fit_lsf_on_window(w_sub, fn_sub - 1.0, w0, cfg)
        if not bool(fit.get("valid_fit")):
            return False, {"reason_fail": 1.0}
        snr_k = float(fit["snr_mid"])
        cos_k = float(fit["cosine"])
        fwr_k = float(fit["fwhm_ratio"])
        amp_k = float(fit["amp_mid"])
        f1 = compute_supraphotospheric_f1_window(w_sub, fn_sub, w0, 1.05)
        fn_pk3 = float(f1.get("fn_pk3", 1.0))
        if not (snr_k >= 4.5 and cos_k >= 0.80 and 0.55 <= fwr_k <= 1.85 and fn_pk3 >= 1.05 and amp_k > 0.0):
            return False, {"min_snr": snr_k, "min_cos": cos_k, "fwhm_ratio": fwr_k, "min_fn_pk3": fn_pk3}
        amps.append(amp_k)
        snrs.append(snr_k)
        coss.append(cos_k)
        fw_ratios.append(fwr_k)
        fn_pks.append(fn_pk3)
    amp_ratio = max(amps) / max(1e-9, min(amps))
    if amp_ratio > 10.0:
        return False, {"amp_ratio": amp_ratio}
    return True, {
        "min_tier2_snr": round(min(snrs), 4),
        "min_tier2_cos": round(min(coss), 4),
        "min_fn_pk3": round(min(fn_pks), 4),
        "amp_ratio": round(amp_ratio, 4),
    }


def _track_stationary_and_topocentric_ok_v53(
    w: np.ndarray,
    z_fin: list[np.ndarray],
    mjds: np.ndarray,
    v_o2r: np.ndarray,
    matched: list[tuple[int, int, float, float, float]],
    u_pred_all_epochs: np.ndarray,
    w_ref: float,
    cfg: dict[str, Any],
    inst_name: str,
    sig_v: float,
    dw: float,
) -> tuple[bool, float, str]:
    """Shared stationary rest-frame, topocentric/BERV-sky, and OH airglow vetoes for curved & periodic tracks."""
    n_ep = len(z_fin)
    m_w = np.asarray([m[3] for m in matched], dtype=np.float64)
    m_z = np.asarray([m[4] for m in matched], dtype=np.float64)
    stat_veto_dv = float(cfg.get("drift_v52_stat_veto_dv_kms", 3.0))
    stat_max_z = float(cfg.get("drift_v52_stat_max_z", 4.0))
    sep_clear_kms = max(8.0, 6.0 * sig_v)
    ep_first, ep_last = int(matched[0][0]), int(matched[-1][0])

    for qi, mw in enumerate(m_w):
        stat_hw_a = float(mw) * (stat_veto_dv / C_KMS) + 1.5 * dw
        s0 = int(np.searchsorted(w, float(mw) - stat_hw_a, side="left"))
        s1 = int(np.searchsorted(w, float(mw) + stat_hw_a, side="right"))
        if s1 <= s0:
            continue
        n_stat = 0
        for k in range(n_ep):
            w_pred_k = w_ref * (1.0 + float(u_pred_all_epochs[k]) / C_KMS)
            dv_from_mw = abs(C_KMS * (w_pred_k - float(mw)) / max(1.0, float(mw)))
            z_here = float(np.max(z_fin[k][s0:s1]))
            if dv_from_mw >= sep_clear_kms and z_here >= stat_max_z:
                n_stat += 1
            elif (qi == 0 and k == ep_last) or (qi == len(matched) - 1 and k == ep_first):
                if z_here >= max(stat_max_z, 0.72 * float(m_z[qi])):
                    n_stat += 1
        if n_stat >= 1:
            return False, 0.0, "STATIONARY_VETO"

    w_obs_m = np.asarray(
        [float(m_w[q]) / (1.0 + float(v_o2r[matched[q][0]]) / C_KMS) for q in range(len(matched))],
        dtype=np.float64,
    )
    obs_span_kms = float(C_KMS * (np.max(w_obs_m) - np.min(w_obs_m)) / max(1.0, float(np.mean(w_obs_m))))
    if obs_span_kms < max(2.5, 1.0 * sig_v):
        return False, obs_span_kms, "TOPO_STATIONARY_VETO"
    # Direct BERV anti-correlation veto: stationary topocentric sky feature shifted by -BERV(t)
    u_m = np.asarray([C_KMS * (float(mw) - w_ref) / w_ref for mw in m_w], dtype=np.float64)
    v_match = np.asarray([float(v_o2r[m[0]]) for m in matched], dtype=np.float64)
    if np.std(u_m) > 1.0 and np.std(v_match) > 1.0:
        w_obs_rms = float(np.std(w_obs_m) / max(1e-6, float(np.mean(w_obs_m))) * C_KMS)
        if w_obs_rms <= max(2.0, 0.65 * FWHM_FACTOR * sig_v):
            return False, obs_span_kms, "BERV_SKY_VETO"
    if not inst_name.startswith("JWST_"):
        if any(check_rousselot_oh_and_barycentric_v52(float(wo), sig_v)["is_oh_or_sky"] for wo in w_obs_m):
            return False, obs_span_kms, "ROUSSELOT_OH_VETO"
    return True, obs_span_kms, "PASS"


def scan_curved_and_periodic_drift_v53(
    wave_rest: np.ndarray,
    fn_epochs: np.ndarray,
    sig_epochs: np.ndarray,
    mjd_epochs: np.ndarray,
    v_obs_to_rest_epochs_kms: np.ndarray,
    cfg: dict[str, Any],
    star: str = "",
    star_idx: int = 0,
    z_rpca_mat: np.ndarray | None = None,
    bervs_cohort: np.ndarray | None = None,
) -> dict[str, Any]:
    """
    Engine 6c (`DRIFT_V53_CURVED_AND_PERIODIC`): Multi-epoch non-linear velocity trajectory chaining.

    Evaluates rolling-MAD scaled (`win_bins=512`, `fn >= 1.01`) epoch residuals across TWO Stage-1
    physically distinct trajectory branches with shared stationary, BERV-sky, OH, RPCA, and
    Tier-2 multi-epoch LSF/F1 confirmation:
      - Branch 1 (`CURVED_QUADRATIC_V53`, `N >= 4`): Quadratic acceleration/jerk trajectories
        `u(t) = u_0 + v_dot * dt + 0.5 * v_ddot * dt^2` recovering strongly curved tracks missed
        by linear chaining (`rms_quad <= 0.35 * fwhm_kms`, non-linear sag >= `max(1.2, 0.8*fwhm_kms)`).
      - Branch 2 (`PERIODIC_ORBITAL_V53`, `N >= 6`): Coherent blind sinusoidal orbital trajectories
        `u(t) = v_0 + K * sin(2*pi*(t - t_0)/P + phi)` over `P in [0.5, 100.0] d` and
        `K in [10, 220] km/s` using analytic 3-parameter harmonic OLS within bounded wavelength zones.
    """
    w = np.asarray(wave_rest, dtype=np.float64)
    fn_e = np.asarray(fn_epochs, dtype=np.float64)
    sig_e = np.asarray(sig_epochs, dtype=np.float64)
    mjds = np.asarray(mjd_epochs, dtype=np.float64)
    v_o2r = np.asarray(v_obs_to_rest_epochs_kms, dtype=np.float64)

    n_ep_in = int(fn_e.shape[0]) if fn_e.ndim == 2 else 0
    empty = {"curved_candidates": [], "periodic_candidates": [], "all_survivors": [], "stats": {"n_epochs": n_ep_in, "n_curved_evals": 0, "n_periodic_evals": 0, "n_raw_tracks": 0}}
    if fn_e.ndim != 2 or n_ep_in < 4 or len(w) < 128:
        return empty

    ord_t = np.argsort(mjds)
    mjds = mjds[ord_t]
    fn_e = fn_e[ord_t]
    sig_e = sig_e[ord_t]
    v_o2r = v_o2r[ord_t]
    n_ep, n_wave = fn_e.shape
    dw = float(np.median(np.diff(w)))
    if not math.isfinite(dw) or dw <= 0.0:
        return empty

    min_dt_days = float(cfg.get("drift_v53_min_dt_days", 0.01))
    # Count distinct epochs separated by min_dt_days
    distinct_mjd = [float(mjds[0])]
    for tk in mjds[1:]:
        if float(tk) - distinct_mjd[-1] >= min_dt_days:
            distinct_mjd.append(float(tk))
    if len(distinct_mjd) < 4:
        return empty

    sig_v = float(cfg.get("sigma_v_kms", 2.0))
    fwhm_kms = FWHM_FACTOR * sig_v
    inst_name = str(cfg.get("instrument", ""))
    epoch_min_z = float(cfg.get("drift_v53_epoch_min_z", 4.2))
    chain_min_z = float(cfg.get("drift_v53_chain_min_z", 8.0))
    dv_max_abs = float(cfg.get("drift_v52_max_abs_dv_kms", 250.0))
    min_rarity = float(cfg.get("g7_min_rarity_score", 0.65))

    # Build rolling-MAD scaled z-scores with supraphotospheric floor (fn >= 1.01)
    static_masks = [_is_masked_static_v50(w, cfg, float(v_o2r[k])) for k in range(n_ep)]
    Z = np.zeros_like(fn_e, dtype=np.float64)
    z_safe: list[np.ndarray] = []
    z_fin: list[np.ndarray] = []
    for k in range(n_ep):
        fin_k = np.isfinite(fn_e[k]) & np.isfinite(sig_e[k]) & (sig_e[k] > 0.0)
        raw_r = np.where(fin_k, (fn_e[k] - 1.0) / np.maximum(sig_e[k], 1e-6), 0.0)
        rmad = _compute_rolling_mad_1d(raw_r, fin_k & (~static_masks[k]), win_bins=512)
        z_k = np.where(fin_k, raw_r / np.maximum(1.0, rmad), 0.0)
        Z[k] = z_k
        # Enforce supraphotospheric emission floor fn >= 1.01 on search seeds
        z_s = np.where(fin_k & (~static_masks[k]) & (fn_e[k] >= 1.01), z_k, 0.0)
        z_safe.append(z_s)
        z_fin.append(np.where(fin_k, z_k, 0.0))

    # Collect per-epoch NMS peaks (z >= epoch_min_z)
    ep_peaks: list[list[tuple[int, float, float]]] = []
    for k in range(n_ep):
        idx_raw = np.where(z_safe[k] >= epoch_min_z)[0]
        if len(idx_raw) == 0:
            ep_peaks.append([])
            continue
        ord_pk = idx_raw[np.argsort(z_safe[k][idx_raw])[::-1]]
        taken = np.zeros(n_wave, dtype=bool)
        pks: list[tuple[int, float, float]] = []
        for idx in ord_pk:
            if taken[idx]:
                continue
            lo_n, hi_n = max(0, idx - 5), min(n_wave, idx + 6)
            if float(z_safe[k][idx]) >= float(np.max(z_safe[k][lo_n:hi_n])) - 1e-12:
                pks.append((int(idx), float(w[idx]), float(z_safe[k][idx])))
                taken[lo_n:hi_n] = True
                if len(pks) >= 64:
                    break
        ep_peaks.append(pks)

    # Flatten all peaks and form candidate wavelength clusters where >= 4 distinct epochs appear within +/- 250 km/s
    all_pks: list[tuple[int, int, float, float, float]] = []
    for k in range(n_ep):
        for idx, wk, zk in ep_peaks[k]:
            all_pks.append((k, idx, float(mjds[k]), wk, zk))
    all_pks.sort(key=lambda x: x[3])

    def _cluster_epoch_count(pks_sub: list[tuple[int, int, float, float, float]]) -> int:
        if not pks_sub:
            return 0
        ts = sorted(p[2] for p in pks_sub)
        cnt = 1
        last = ts[0]
        for t in ts[1:]:
            if t - last >= min_dt_days:
                cnt += 1
                last = t
        return cnt

    # Build deduplicated spatial neighborhoods
    clusters: list[list[tuple[int, int, float, float, float]]] = []
    for i, pk in enumerate(all_pks):
        w0 = pk[3]
        win_a = w0 * (dv_max_abs / C_KMS)
        sub = [pk]
        j = i + 1
        while j < len(all_pks) and all_pks[j][3] <= w0 + 2.0 * win_a:
            sub.append(all_pks[j])
            j += 1
        if _cluster_epoch_count(sub) >= 4:
            if not clusters or (w0 - clusters[-1][0][3]) > 0.5 * win_a:
                clusters.append(sub)
            elif len(sub) > len(clusters[-1]):
                clusters[-1] = sub

    n_curved_evals = 0
    n_periodic_evals = 0
    n_raw_tracks = 0
    curved_cands: list[dict[str, Any]] = []
    periodic_cands: list[dict[str, Any]] = []
    seen_curved: set[tuple[int, int, int]] = set()
    seen_per: set[tuple[int, int, int]] = set()
    quad_rms_max = max(3.5, 0.38 * fwhm_kms)
    per_rms_max = max(3.8, 0.42 * fwhm_kms)
    tol_kms = max(4.5, 0.90 * fwhm_kms)

    # ---- Branch 1: Curved Quadratic Acceleration (N >= 4) ----
    for sub in clusters:
        by_ep: dict[int, list[tuple[int, int, float, float, float]]] = {}
        for p in sub:
            by_ep.setdefault(p[0], []).append(p)
        ep_ids = sorted(by_ep.keys())
        if len(ep_ids) < 4:
            continue
        e0_list = ep_ids[: max(1, len(ep_ids) // 2)]
        e2_list = ep_ids[max(1, len(ep_ids) // 2) :]
        for e0 in e0_list:
            for e2 in e2_list:
                if float(mjds[e2] - mjds[e0]) < 3.0 * min_dt_days:
                    continue
                mid_eps = [ek for ek in ep_ids if e0 < ek < e2 and float(mjds[ek] - mjds[e0]) >= min_dt_days and float(mjds[e2] - mjds[ek]) >= min_dt_days]
                if not mid_eps:
                    continue
                e1 = mid_eps[len(mid_eps) // 2]
                for p0 in by_ep[e0]:
                    w0_ref = p0[3]
                    u0 = 0.0
                    for p1 in by_ep[e1]:
                        u1 = C_KMS * (p1[3] - w0_ref) / w0_ref
                        if abs(u1) > 2.2 * dv_max_abs:
                            continue
                        for p2 in by_ep[e2]:
                            u2 = C_KMS * (p2[3] - w0_ref) / w0_ref
                            if abs(u2) > 2.2 * dv_max_abs:
                                continue
                            n_curved_evals += 1
                            ts3 = np.array([0.0, float(mjds[e1] - mjds[e0]), float(mjds[e2] - mjds[e0])], dtype=np.float64)
                            us3 = np.array([u0, u1, u2], dtype=np.float64)
                            # Vandermonde [1, t, 0.5 t^2]
                            A3 = np.column_stack([np.ones(3), ts3, 0.5 * ts3 * ts3])
                            try:
                                c0, c1, c2 = np.linalg.solve(A3, us3)
                            except np.linalg.LinAlgError:
                                continue
                            # Require non-trivial curvature so linear-only tracks stay on V5.2
                            u_pred_all = c0 + c1 * (mjds - float(mjds[e0])) + 0.5 * c2 * ((mjds - float(mjds[e0])) ** 2)
                            if float(np.max(np.abs(u_pred_all))) > 2.2 * dv_max_abs:
                                continue

                            matched: list[tuple[int, int, float, float, float]] = []
                            for k in range(n_ep):
                                w_pred = w0_ref * (1.0 + float(u_pred_all[k]) / C_KMS)
                                if w_pred < w[0] or w_pred > w[-1]:
                                    continue
                                tol_a = max(2.0 * dw, w_pred * (tol_kms / C_KMS))
                                j0 = int(np.searchsorted(w, w_pred - tol_a, side="left"))
                                j1 = int(np.searchsorted(w, w_pred + tol_a, side="right"))
                                if j1 <= j0 or not np.any(z_safe[k][j0:j1] >= epoch_min_z):
                                    continue
                                jm = j0 + int(np.argmax(z_safe[k][j0:j1]))
                                matched.append((k, jm, float(mjds[k]), float(w[jm]), float(z_safe[k][jm])))

                            if len(matched) < 4:
                                continue
                            m_t = np.asarray([m[2] for m in matched], dtype=np.float64)
                            # Distinct epochs
                            dist_t = [float(m_t[0])]
                            for tk in m_t[1:]:
                                if float(tk) - dist_t[-1] >= min_dt_days:
                                    dist_t.append(float(tk))
                            if len(dist_t) < 4:
                                continue

                            m_w = np.asarray([m[3] for m in matched], dtype=np.float64)
                            m_z = np.asarray([m[4] for m in matched], dtype=np.float64)
                            z_chain = float(np.sum(m_z) / math.sqrt(float(len(matched))))
                            if z_chain < chain_min_z:
                                continue

                            w_ref = float(np.mean(m_w))
                            u_m = C_KMS * (m_w - w_ref) / w_ref
                            t_rel = m_t - float(np.mean(m_t))
                            X_q = np.column_stack([np.ones_like(t_rel), t_rel, 0.5 * t_rel * t_rel])
                            try:
                                beta_q, *_ = np.linalg.lstsq(X_q, u_m, rcond=None)
                            except np.linalg.LinAlgError:
                                continue
                            u_q_hat = X_q @ beta_q
                            rms_q = float(np.sqrt(np.mean((u_m - u_q_hat) ** 2)))
                            if rms_q > quad_rms_max:
                                continue

                            X_l = np.column_stack([np.ones_like(t_rel), t_rel])
                            beta_l, *_ = np.linalg.lstsq(X_l, u_m, rcond=None)
                            rms_l = float(np.sqrt(np.mean((u_m - X_l @ beta_l) ** 2)))
                            nl_sag_kms = float(np.max(np.abs(u_q_hat - X_l @ beta_l)))
                            dv_span = float(np.max(u_q_hat) - np.min(u_q_hat))
                            if nl_sag_kms < max(1.2, 0.65 * fwhm_kms) or rms_l < max(2.0, 0.45 * fwhm_kms):
                                continue
                            if rms_q > 0.72 * rms_l:
                                continue
                            if dv_span < max(3.0, 1.5 * fwhm_kms) or dv_span > dv_max_abs:
                                continue

                            t_key = (int(round(m_w[0] * 10.0)), int(round(m_w[-1] * 10.0)), len(matched))
                            if t_key in seen_curved:
                                continue
                            seen_curved.add(t_key)
                            n_raw_tracks += 1

                            t_all_rel = mjds - float(np.mean(m_t))
                            u_all = beta_q[0] + beta_q[1] * t_all_rel + 0.5 * beta_q[2] * (t_all_rel ** 2)
                            ok_st, obs_span, vet_r = _track_stationary_and_topocentric_ok_v53(
                                w, z_fin, mjds, v_o2r, matched, u_all, w_ref, cfg, inst_name, sig_v, dw,
                            )
                            if not ok_st:
                                continue

                            # RPCA rarity check
                            rarity_min = 1.0
                            if z_rpca_mat is not None and bervs_cohort is not None and z_rpca_mat.shape[0] >= 2:
                                r_vals = [float(compute_spectral_rarity_score(w, z_rpca_mat, bervs_cohort, star_idx, float(mw), sig_v, polarity=1.0)["rarity_score"]) for mw in m_w]
                                rarity_min = float(min(r_vals))
                                if rarity_min < min_rarity:
                                    continue

                            t2_ok, t2_info = _tier2_multiepoch_lsf_check_v53(w, fn_e, sig_e, matched, cfg)
                            if not t2_ok:
                                continue

                            curved_cands.append({
                                "star": star,
                                "branch": "CURVED_QUADRATIC_V53",
                                "n_epochs_total": int(n_ep),
                                "n_epochs_matched": int(len(matched)),
                                "matched_epochs": [int(m[0]) for m in matched],
                                "wave_mean_rest_a": round(w_ref, 5),
                                "dv_span_kms": round(dv_span, 4),
                                "obs_span_kms": round(obs_span, 4),
                                "dt_days": round(float(m_t[-1] - m_t[0]), 6),
                                "vdot_kms_day": round(float(beta_q[1]), 6),
                                "vddot_kms_day2": round(float(beta_q[2]), 6),
                                "nl_sag_kms": round(nl_sag_kms, 4),
                                "rms_lin_kms": round(rms_l, 4),
                                "rms_quad_kms": round(rms_q, 4),
                                "z_min_epoch": round(float(np.min(m_z)), 4),
                                "z_drift_chain": round(z_chain, 4),
                                "rarity_min": round(rarity_min, 4),
                                **t2_info,
                            })

    # ---- Branch 2: Blind Coherent Periodic Orbital Chaining (N >= 6) ----
    baseline_d = float(mjds[-1] - mjds[0])
    min_per_epochs = int(cfg.get("drift_v53_periodic_min_epochs", 6))
    min_p_d = float(cfg.get("drift_v53_periodic_min_p_days", 0.5))
    max_p_d = float(cfg.get("drift_v53_periodic_max_p_days", 100.0))
    min_k_kms = float(cfg.get("drift_v53_periodic_min_k_kms", 10.0))
    max_k_kms = float(cfg.get("drift_v53_periodic_max_k_kms", 220.0))

    if len(distinct_mjd) >= min_per_epochs and baseline_d >= float(cfg.get("drift_v53_periodic_min_baseline_days", 2.0)):
        p_max_eff = min(max_p_d, max(min_p_d * 1.5, 2.0 * baseline_d))
        f_min = 1.0 / p_max_eff
        f_max = 1.0 / min_p_d
        df_ray = 0.22 / max(baseline_d, 5.0)
        n_freqs = min(650, max(140, int(math.ceil((f_max - f_min) / df_ray)) + 1))
        p_grid = 1.0 / np.linspace(f_min, f_max, n_freqs)
        t_ref = float(mjds[0])
        for sub in clusters:
            if _cluster_epoch_count(sub) < 5:
                continue
            p_arr_t = np.asarray([p[2] for p in sub], dtype=np.float64)
            p_arr_w = np.asarray([p[3] for p in sub], dtype=np.float64)
            w_med = float(np.median(p_arr_w))
            u_arr = C_KMS * (p_arr_w - w_med) / w_med
            p_arr_z = np.asarray([p[4] for p in sub], dtype=np.float64)

            # For each epoch, take the strongest peak in cluster to seed Lomb-Scargle / harmonic scan
            ep_best: dict[int, tuple[float, float, float, int]] = {}
            for k, idx, tk, wk, zk in sub:
                if k not in ep_best or zk > ep_best[k][2]:
                    ep_best[k] = (tk, C_KMS * (wk - w_med) / w_med, zk, idx)
            if len(ep_best) < 5:
                continue
            ts_b = np.asarray([v[0] for v in ep_best.values()], dtype=np.float64) - t_ref
            us_b = np.asarray([v[1] for v in ep_best.values()], dtype=np.float64)

            # Evaluate fast 3x3 harmonic OLS across uniform Rayleigh frequency grid
            best_fits: list[tuple[int, float, float]] = []
            for p_try in p_grid:
                n_periodic_evals += 1
                om = 2.0 * math.pi / float(p_try)
                X_h = np.column_stack([np.ones_like(ts_b), np.cos(om * ts_b), np.sin(om * ts_b)])
                try:
                    c_h, *_ = np.linalg.lstsq(X_h, us_b, rcond=None)
                except np.linalg.LinAlgError:
                    continue
                k_amp = math.hypot(float(c_h[1]), float(c_h[2]))
                if k_amp < min_k_kms or k_amp > max_k_kms:
                    continue
                resid = np.abs(us_b - X_h @ c_h)
                in_m = resid <= tol_kms
                n_in = int(np.sum(in_m))
                if n_in >= 5:
                    rms_in = float(np.sqrt(np.mean(resid[in_m] ** 2)))
                    best_fits.append((n_in, -rms_in, float(p_try)))

            # Inspect top 8 trial periods + refined local neighbor grid
            best_fits.sort(reverse=True)
            cand_periods: list[float] = []
            for _, _, pt in best_fits[:8]:
                for fac in np.linspace(0.96, 1.04, 9):
                    cand_periods.append(float(pt * fac))

            for p_try in cand_periods:
                if p_try < min_p_d or p_try > max_p_d or abs(p_try - 365.25) < 25.0:
                    continue
                om = 2.0 * math.pi / p_try
                # Iterative RANSAC/IRLS starting from closest sub-peaks on initial harmonic fit
                X_b = np.column_stack([np.ones_like(ts_b), np.cos(om * ts_b), np.sin(om * ts_b)])
                try:
                    beta, *_ = np.linalg.lstsq(X_b, us_b, rcond=None)
                except np.linalg.LinAlgError:
                    continue
                for _it in range(2):
                    u_all = beta[0] + beta[1] * np.cos(om * (mjds - t_ref)) + beta[2] * np.sin(om * (mjds - t_ref))
                    matched = []
                    for k in range(n_ep):
                        w_pred = w_med * (1.0 + float(u_all[k]) / C_KMS)
                        if w_pred < w[0] or w_pred > w[-1]:
                            continue
                        tol_a = max(2.0 * dw, w_pred * (tol_kms / C_KMS))
                        j0 = int(np.searchsorted(w, w_pred - tol_a, side="left"))
                        j1 = int(np.searchsorted(w, w_pred + tol_a, side="right"))
                        if j1 <= j0 or not np.any(z_safe[k][j0:j1] >= epoch_min_z):
                            continue
                        jm = j0 + int(np.argmax(z_safe[k][j0:j1]))
                        matched.append((k, jm, float(mjds[k]), float(w[jm]), float(z_safe[k][jm])))
                    if len(matched) < 5:
                        break
                    mt = np.asarray([m[2] for m in matched], dtype=np.float64) - t_ref
                    mu = np.asarray([C_KMS * (m[3] - w_med) / w_med for m in matched], dtype=np.float64)
                    Xm = np.column_stack([np.ones_like(mt), np.cos(om * mt), np.sin(om * mt)])
                    try:
                        beta, *_ = np.linalg.lstsq(Xm, mu, rcond=None)
                    except np.linalg.LinAlgError:
                        break

                if len(matched) < 5:
                    continue
                m_t = np.asarray([m[2] for m in matched], dtype=np.float64)
                dist_t = [float(m_t[0])]
                for tk in m_t[1:]:
                    if float(tk) - dist_t[-1] >= min_dt_days:
                        dist_t.append(float(tk))
                if len(dist_t) < 5:
                    continue
                # Require orbital phase spread across >= 3 distinct phase bins [0..1)
                phases = np.mod((m_t - t_ref) / p_try, 1.0)
                if len({int(ph * 4.0) % 4 for ph in phases}) < 3:
                    continue

                m_w = np.asarray([m[3] for m in matched], dtype=np.float64)
                m_z = np.asarray([m[4] for m in matched], dtype=np.float64)
                z_chain = float(np.sum(m_z) / math.sqrt(float(len(matched))))
                if z_chain < chain_min_z:
                    continue

                k_amp = math.hypot(float(beta[1]), float(beta[2]))
                if k_amp < max(min_k_kms, 2.0 * fwhm_kms) or k_amp > max_k_kms:
                    continue
                u_m = C_KMS * (m_w - w_med) / w_med
                u_hat = beta[0] + beta[1] * np.cos(om * (m_t - t_ref)) + beta[2] * np.sin(om * (m_t - t_ref))
                rms_p = float(np.sqrt(np.mean((u_m - u_hat) ** 2)))
                if rms_p > per_rms_max:
                    continue
                # Must beat pure linear fit convincingly (periodic oscillation, not simple straight drift)
                t_c = m_t - float(np.mean(m_t))
                Xl = np.column_stack([np.ones_like(t_c), t_c])
                bl, *_ = np.linalg.lstsq(Xl, u_m, rcond=None)
                rms_lin = float(np.sqrt(np.mean((u_m - Xl @ bl) ** 2)))
                if rms_lin < max(3.0, 0.8 * fwhm_kms) or rms_p > 0.65 * rms_lin:
                    continue

                t_key = (int(round(w_med * 10.0)), int(round(p_try * 20.0)), len(matched))
                if t_key in seen_per:
                    continue
                seen_per.add(t_key)
                n_raw_tracks += 1

                u_all = beta[0] + beta[1] * np.cos(om * (mjds - t_ref)) + beta[2] * np.sin(om * (mjds - t_ref))
                ok_st, obs_span, _ = _track_stationary_and_topocentric_ok_v53(
                    w, z_fin, mjds, v_o2r, matched, u_all, w_med, cfg, inst_name, sig_v, dw,
                )
                if not ok_st:
                    continue

                rarity_min = 1.0
                if z_rpca_mat is not None and bervs_cohort is not None and z_rpca_mat.shape[0] >= 2:
                    r_vals = [float(compute_spectral_rarity_score(w, z_rpca_mat, bervs_cohort, star_idx, float(mw), sig_v, polarity=1.0)["rarity_score"]) for mw in m_w]
                    rarity_min = float(min(r_vals))
                    if rarity_min < min_rarity:
                        continue

                t2_ok, t2_info = _tier2_multiepoch_lsf_check_v53(w, fn_e, sig_e, matched, cfg)
                if not t2_ok:
                    continue

                phi0 = math.atan2(-float(beta[2]), float(beta[1]))
                periodic_cands.append({
                    "star": star,
                    "branch": "PERIODIC_ORBITAL_V53",
                    "n_epochs_total": int(n_ep),
                    "n_epochs_matched": int(len(matched)),
                    "matched_epochs": [int(m[0]) for m in matched],
                    "wave_center_rest_a": round(w_med, 5),
                    "period_days": round(p_try, 6),
                    "k_kms": round(k_amp, 4),
                    "v0_kms": round(float(beta[0]), 4),
                    "phi0_rad": round(phi0, 4),
                    "obs_span_kms": round(obs_span, 4),
                    "rms_per_kms": round(rms_p, 4),
                    "rms_lin_kms": round(rms_lin, 4),
                    "z_min_epoch": round(float(np.min(m_z)), 4),
                    "z_drift_chain": round(z_chain, 4),
                    "rarity_min": round(rarity_min, 4),
                    **t2_info,
                })

    # Deduplicate keeping highest Z_drift_chain per branch
    def _dedup(cands: list[dict[str, Any]], wkey: str) -> list[dict[str, Any]]:
        cands.sort(key=lambda d: float(d["z_drift_chain"]), reverse=True)
        out: list[dict[str, Any]] = []
        min_sa = max(0.8, 8.0 * dw * 10.0)
        for c in cands:
            if any(abs(float(c[wkey]) - float(k[wkey])) < min_sa for k in out):
                continue
            out.append(c)
        return out

    curved_cands = _dedup(curved_cands, "wave_mean_rest_a")
    periodic_cands = _dedup(periodic_cands, "wave_center_rest_a")
    return {
        "curved_candidates": curved_cands,
        "periodic_candidates": periodic_cands,
        "all_survivors": curved_cands + periodic_cands,
        "stats": {
            "n_epochs": int(n_ep),
            "n_distinct_epochs": len(distinct_mjd),
            "n_curved_evals": int(n_curved_evals),
            "n_periodic_evals": int(n_periodic_evals),
            "n_raw_tracks": int(n_raw_tracks),
        },
    }


def _hampel_despike_1d_v53(flux: np.ndarray, n_sig: float = 4.5) -> tuple[np.ndarray, int]:
    """Single-pixel Hampel outlier despiker (7-px median / 11-px MAD) before broadband IR CCF."""
    f = np.asarray(flux, dtype=np.float64).copy()
    if len(f) < 15:
        return f, 0
    rmed = median_filter(f, size=7, mode="nearest")
    resid = f - rmed
    rmad = MAD_NORM * median_filter(np.abs(resid), size=11, mode="nearest")
    mad_floor = max(1e-30, exact_mad_1d(resid))
    loc_sig = np.maximum(rmad, 0.35 * mad_floor)
    n_rem = 0
    for j in range(2, len(f) - 2):
        r0 = abs(resid[j])
        if r0 > float(n_sig) * loc_sig[j]:
            nb = max(abs(resid[j - 1]), abs(resid[j + 1]))
            if nb < 0.35 * r0:
                f[j] = rmed[j]
                n_rem += 1
    return f, n_rem


def _planck_bnu_rel_v53(wave_um: np.ndarray, teff_k: float) -> np.ndarray:
    """Dimensionless Planck B_nu(lambda, T) shape (proportional to lam^-3 / (exp(hc/lkT) - 1))."""
    lam_m = np.maximum(1e-7, np.asarray(wave_um, dtype=np.float64) * 1e-6)
    x = np.clip((H_PLANCK * C_SI) / (lam_m * K_BOLTZ * max(60.0, float(teff_k))), 1e-4, 500.0)
    return 1.0 / ((lam_m ** 3) * np.expm1(x))


def scan_spitzer_irs_ccf_and_dyson_v53(
    wave_um: np.ndarray,
    flux_jy: np.ndarray,
    err_jy: np.ndarray,
    teff_k: float,
    dist_pc: float,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Engine 12 (`SPITZER_IRS_CCF_AND_DYSON_V53`): Far-thermal-IR (`5.2-37.9 um`) suite combining:
      A. Union-excluded 6-gas industrial greenhouse CCF (`CF4`, `C2F6`, `SF6`, `NF3`, `CFC-11`,
         `CFC-12`) against 7 natural confounders (`Silicate 10/18 um`, `PAH`, `CO2 15 um`,
         `NH3`, `CH4`, `H2O`) with margin + ratio veto.
      B. Dyson waste-heat blackbody (`100-400 K`) decomposition over `8.5-37.9 um` anchored to
         the `5.2-8.5 um` photosphere (`L_waste / L_star`), explicitly vetoing natural crystalline/
         amorphous silicate debris belts (`10/18/23 um` excess bands or non-blackbody SED shape).
      C. Direct 5-band (`6.5, 10.6, 18.0, 26.0, 34.5 um`) 10 m EIRP laser upper limits from `err_jy`.
    """
    cfg_eff = cfg or BASE_V5_3_CONFIG
    w = np.asarray(wave_um, dtype=np.float64)
    f = np.asarray(flux_jy, dtype=np.float64)
    e = np.asarray(err_jy, dtype=np.float64)
    valid = np.isfinite(w) & np.isfinite(f) & np.isfinite(e) & (w >= 5.0) & (w <= 40.0) & (e > 0.0)
    if int(np.sum(valid)) < 40:
        return {
            "n_bins": int(np.sum(valid)),
            "n_1px_despiked": 0,
            "subcontinuum_nd": True,
            "ccf": {"molecules": {}, "confounders": {}, "max_confounder_sigma": 0.0, "detected_molecules": [], "any_detection": False},
            "dyson": {"dyson_candidate": False, "gamma_waste": 0.0, "t_waste_k": 0.0, "snr_excess": 0.0, "blackbody_r2": 0.0, "silicate_excess_sigma": 0.0, "status": "INSUFFICIENT_DATA"},
            "upper_limits": {},
        }

    wv, fv, ev = w[valid], f[valid], e[valid]
    ord_w = np.argsort(wv)
    wv, fv, ev = wv[ord_w], fv[ord_w], ev[ord_w]
    f_clean, n_desp = _hampel_despike_1d_v53(fv)

    med_cont_snr = float(np.median(f_clean / np.maximum(ev, 1e-12)))
    subcontinuum_nd = bool(med_cont_snr < 3.0)

    # A. Union-excluded Spitzer IRS industrial-gas CCF over continuous merged segments (split only on large gaps > 0.6 um)
    splits = np.where(np.diff(wv) > 0.60)[0] + 1
    bounds = [0] + list(splits) + [len(wv)]
    segments = [(wv[a:b], f_clean[a:b]) for a, b in zip(bounds[:-1], bounds[1:]) if (b - a) >= 24]
    ccf_raw = _run_ir_ccf_suite_v52(
        segments,
        SPITZER_IRS_GREENHOUSE_TEMPLATES_UM,
        SPITZER_IRS_CONFOUNDERS_UM,
        emission_conf_names={"PAH_COMPLEX", "SILICATE_10UM", "SILICATE_18UM"},
        min_sigma=float(cfg_eff.get("spitzer_irs_ccf_min_sigma", 5.0)),
        min_conf_ratio=float(cfg_eff.get("spitzer_irs_ccf_min_confounder_ratio", 1.5)),
        prox_dist_um=1.5,
        min_core_bins=4,
        min_sb_bins=6,
        min_win_bins=6,
        min_side_bins=3,
        sb_pad_mult=4.0,
    )
    # Enforce extra V5.3 absolute SNR margin against max confounder & low-SNR guard
    min_sig = float(cfg_eff.get("spitzer_irs_ccf_min_sigma", 5.0))
    min_margin = float(cfg_eff.get("spitzer_irs_ccf_min_margin_sigma", 2.0))
    max_conf_s = float(ccf_raw.get("max_confounder_sigma", 0.0))
    final_dets: list[str] = []
    for mn, mr in ccf_raw.get("molecules", {}).items():
        s_gas = float(mr.get("ccf_sigma_abs", 0.0))
        ok = bool(mr.get("passes_ccf")) and (not subcontinuum_nd) and (s_gas >= min_sig) and ((s_gas - max_conf_s) >= min_margin)
        mr["passes_ccf_v53"] = ok
        if ok:
            final_dets.append(mn)
    ccf_raw["detected_molecules"] = final_dets
    ccf_raw["any_detection"] = len(final_dets) > 0

    # B. Dyson waste-heat blackbody (100-400 K) vs natural silicate debris belt decomposition
    dyson_res: dict[str, Any] = {
        "dyson_candidate": False,
        "gamma_waste": 0.0,
        "t_waste_k": 0.0,
        "snr_excess": 0.0,
        "blackbody_r2": 0.0,
        "silicate_excess_sigma": 0.0,
        "status": "NO_EXCESS",
    }
    anc_m = ((wv >= 5.3) & (wv <= 7.2)) | ((wv >= 8.0) & (wv <= 8.5))
    long_m = (wv >= 8.6) & (wv <= 37.9)
    # Clean continuum-fitting mask excludes silicate dust band cores (9-12.2 um and 16.5-24.5 um) when solving joint 2-BB
    full_m = (wv >= 5.2) & (wv <= 37.9)
    cont_fit_m = full_m & (~((wv >= 7.3) & (wv <= 8.1))) & (~((wv >= 9.0) & (wv <= 12.2))) & (~((wv >= 16.5) & (wv <= 24.5)))
    if (not subcontinuum_nd) and int(np.sum(anc_m)) >= 8 and int(np.sum(long_m)) >= 30 and int(np.sum(cont_fit_m)) >= 30:
        b_star_all = _planck_bnu_rel_v53(wv, max(1500.0, float(teff_k)))
        eff_e_cf = np.maximum(ev[cont_fit_m], 0.015 * np.maximum(f_clean[cont_fit_m], 1e-12))
        w_cf = 1.0 / eff_e_cf
        w_long_r = 1.0 / np.maximum(ev[long_m] * ev[long_m], 1e-24)

        def _fit_2bb(tw_val: float) -> tuple[float, float, float]:
            bw_cf = _planck_bnu_rel_v53(wv[cont_fit_m], tw_val)
            X2 = np.column_stack([b_star_all[cont_fit_m] * w_cf, bw_cf * w_cf])
            y2 = f_clean[cont_fit_m] * w_cf
            ab, *_ = np.linalg.lstsq(X2, y2, rcond=None)
            a_t, b_t = float(ab[0]), float(ab[1])
            if a_t < 0.0:
                a_t = 0.0
                b_t = max(0.0, float(np.dot(bw_cf * w_cf, y2) / max(1e-30, float(np.dot(bw_cf * w_cf, bw_cf * w_cf)))))
            if b_t < 0.0:
                b_t = 0.0
                bs_w = b_star_all[cont_fit_m] * w_cf
                a_t = max(0.0, float(np.dot(bs_w, y2) / max(1e-30, float(np.dot(bs_w, bs_w)))))
            mod_cf = a_t * b_star_all[cont_fit_m] + b_t * bw_cf
            c2 = float(np.mean(((f_clean[cont_fit_m] - mod_cf) * w_cf) ** 2))
            return c2, a_t, b_t

        best_chi2_red = 1e30
        best_tw = 200.0
        best_a = 0.0
        best_b = 0.0
        for tw_try in range(90, 421, 15):
            try:
                chi2_r, a_try, b_try = _fit_2bb(float(tw_try))
                if chi2_r < best_chi2_red:
                    best_chi2_red, best_tw, best_a, best_b = chi2_r, float(tw_try), a_try, b_try
            except np.linalg.LinAlgError:
                continue
        for tw_try in np.arange(max(80.0, best_tw - 14.0), min(430.0, best_tw + 14.5), 2.0):
            try:
                chi2_r, a_try, b_try = _fit_2bb(float(tw_try))
                if chi2_r < best_chi2_red:
                    best_chi2_red, best_tw, best_a, best_b = chi2_r, float(tw_try), a_try, b_try
            except np.linalg.LinAlgError:
                continue

        f_phot_all = best_a * b_star_all
        f_exc = f_clean[long_m] - f_phot_all[long_m]
        e_long = ev[long_m]
        w_long = wv[long_m]
        best_model = best_b * _planck_bnu_rel_v53(w_long, best_tw)

        # Weighted excess SNR across 8.6-37.9 um + full-long-band R^2 against pure smooth blackbody
        mod_norm = float(np.sum(w_long_r * best_model * best_model))
        snr_exc = math.sqrt(max(0.0, mod_norm)) if best_b > 0.0 else 0.0
        sse_mod = float(np.sum(w_long_r * ((f_exc - best_model) ** 2)))
        sse_null = float(np.sum(w_long_r * ((f_exc - float(np.average(f_exc, weights=w_long_r))) ** 2)))
        bb_r2 = 1.0 - (sse_mod / max(1e-30, sse_null)) if sse_null > 0.0 else 0.0

        # Stefan-Boltzmann bolometric excess fraction L_waste / L_star = (b * T_waste^4) / (a * Teff^4)
        teff_eff = max(1500.0, float(teff_k))
        a_ref = best_a if best_a > 0.0 else max(1e-30, exact_median_1d(f_clean[anc_m] / np.maximum(b_star_all[anc_m], 1e-30)))
        gamma_w = (best_b * (best_tw ** 4)) / max(1e-30, a_ref * (teff_eff ** 4))

        # Local flanking-continuum silicate emission bump test (10 um & 18-24 um)
        res_abs = f_exc - best_model
        sil_sig = 0.0
        for lo_c, hi_c, lo_sb, hi_sb in ((9.0, 12.2, 8.2, 13.8), (16.5, 24.5, 14.5, 27.5)):
            cm = (w_long >= lo_c) & (w_long <= hi_c)
            sbm = (w_long >= lo_sb) & (w_long <= hi_sb) & (~cm)
            if int(np.sum(cm)) >= 6 and int(np.sum(sbm)) >= 6:
                sb_w, sb_r = w_long[sbm], res_abs[sbm]
                c_lin = np.polyfit(sb_w, sb_r, 1)
                bump = res_abs[cm] - np.polyval(c_lin, w_long[cm])
                sb_scat = max(exact_mad_1d(sb_r - np.polyval(c_lin, sb_w)), 1e-12)
                eff_sig_c = np.maximum(e_long[cm], sb_scat)
                z_b = float(np.sum(bump / eff_sig_c) / math.sqrt(float(len(bump))))
                frac_b = float(np.median(bump) / max(1e-12, float(np.median(f_clean[long_m][cm]))))
                if frac_b >= 0.025:
                    sil_sig = max(sil_sig, z_b)
        sil_comb_sig = float(sil_sig)

        has_exc = snr_exc >= float(cfg_eff.get("dyson_waste_min_snr", 6.0)) and gamma_w >= float(cfg_eff.get("dyson_waste_min_gamma", 0.01))
        is_bb = bb_r2 >= float(cfg_eff.get("dyson_waste_min_r2", 0.90))
        is_sil = sil_comb_sig >= float(cfg_eff.get("dyson_waste_max_silicate_sigma", 3.0))
        dyson_ok = bool(has_exc and is_bb and (not is_sil))
        if not has_exc:
            st_lbl = "NO_SIGNIFICANT_EXCESS"
        elif is_sil or (not is_bb):
            st_lbl = "NATURAL_SILICATE_OR_DEBRIS_EXCESS"
        else:
            st_lbl = "ARTIFICIAL_DYSON_BLACKBODY_CANDIDATE"
        dyson_res = {
            "dyson_candidate": dyson_ok,
            "gamma_waste": round(float(gamma_w), 6),
            "t_waste_k": round(float(best_tw), 1),
            "snr_excess": round(float(snr_exc), 3),
            "blackbody_r2": round(float(bb_r2), 4),
            "silicate_excess_sigma": round(float(sil_comb_sig), 3),
            "status": st_lbl,
        }

    # C. 5-band direct CGS radiometric 10m EIRP limits from Spitzer IRS err_jy
    c_a_s = C_SI * 1e10
    ul_out: dict[str, dict[str, float]] = {}
    for band in CALIBRATION_BANDS_SPITZER_IRS:
        lam_a = float(band["center_wave_A"])
        lam_um = lam_a * 1e-4
        m_b = np.abs(wv - lam_um) <= 0.10 * lam_um
        if int(np.sum(m_b)) < 3:
            continue
        med_err_jy = exact_median_1d(ev[m_b])
        sig_flam_cgs = 1e-23 * med_err_jy * c_a_s / (lam_a * lam_a)
        ul = compute_photon_beam_upper_limit(
            wave_a=lam_a,
            amp_rel_lim=1.0,
            teff_k=float(teff_k),
            dist_pc=float(dist_pc),
            stellar_radius_rsun=1.0,
            radiometric_anchor="SPITZER_IRS_DIRECT_CGS",
            resolving_power=100.0,
            direct_flam_cgs=3.0 * sig_flam_cgs,
        )
        ul["direct_flam_3sig_cgs"] = float(3.0 * sig_flam_cgs)
        ul_out[band["band_id"]] = ul

    return {
        "n_bins": int(len(wv)),
        "n_1px_despiked": int(n_desp),
        "med_cont_snr": round(med_cont_snr, 3),
        "subcontinuum_nd": subcontinuum_nd,
        "ccf": ccf_raw,
        "dyson": dyson_res,
        "upper_limits": ul_out,
    }


# ===========================================================================
# TECHNOSIGNATURE V5.4 ENGINES
# ===========================================================================

# Known mid-IR atomic fine-structure, H I recombination, and H2 pure-rotational lines (um)
EXES_NATURAL_LINES_UM: tuple[tuple[str, float], ...] = (
    ("FeII_5.340", 5.34017),
    ("H2_S7_5.511", 5.51120),
    ("MgV_5.610", 5.60980),
    ("HI_6_19_5.908", 5.90820),
    ("H2_S6_6.109", 6.10860),
    ("H2_S5_6.910", 6.90950),
    ("ArII_6.985", 6.98527),
    ("HI_PfA_7.460", 7.45990),
    ("HI_HuB_7.503", 7.50250),
    ("NeVI_7.652", 7.65240),
    ("H2_S4_8.025", 8.02510),
    ("ArIII_8.991", 8.99140),
    ("H2_S3_9.665", 9.66490),
    ("SIV_10.511", 10.51050),
    ("H2_S2_12.279", 12.27860),
    ("HI_HuA_12.372", 12.37190),
    ("NeII_12.814", 12.81350),
    ("NeV_14.322", 14.32170),
    ("NeIII_15.555", 15.55510),
    ("H2_S1_17.035", 17.03480),
    ("SIII_18.713", 18.71300),
    ("FeIII_22.925", 22.92500),
    ("OIV_25.890", 25.89030),
    ("FeII_25.988", 25.98840),
)

# Known NIR H I & He I stellar/nebular emission lines for JWST SOSS / G140H (um)
JWST_NIR_ATOMIC_LINES_UM: tuple[tuple[str, float], ...] = (
    ("HI_PaEps_0.955", 0.95486),
    ("HI_PaDel_1.005", 1.00521),
    ("HeI_1.083", 1.08333),
    ("HI_PaGam_1.094", 1.09411),
    ("HI_PaBet_1.282", 1.28216),
    ("HI_PaAlp_1.876", 1.87561),
    ("HI_BrGam_2.166", 2.16612),
    ("H2_10S1_2.122", 2.12183),
    ("HI_PfGam_3.741", 3.74056),
)


def _robust_sliding_cont_and_mad_v54(
    wave: np.ndarray,
    flux: np.ndarray,
    err: np.ndarray,
    clean_mask: np.ndarray,
    win_cont_px: int = 41,
    win_mad_px: int = 128,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Two-pass sigma-clipped continuum and rolling-MAD noise estimator shared across
    SOFIA_EXES, JWST_NIRISS_SOSS, and JWST_NIRSPEC_G140H.
    """
    n = len(wave)
    w_c = max(15, int(win_cont_px) | 1)
    y = np.asarray(flux, dtype=np.float64).copy()
    good = np.asarray(clean_mask, dtype=bool) & np.isfinite(y)
    if int(np.sum(good)) < 12:
        med_y = float(np.nanmedian(y)) if np.any(np.isfinite(y)) else 0.0
        cont = np.full(n, med_y, dtype=np.float64)
        sig = np.maximum(np.asarray(err, dtype=np.float64), 1e-12)
        z = np.where(good, (y - cont) / sig, 0.0)
        return cont, y - cont, sig, z

    # Interpolate masked/missing pixels for continuous baseline estimation
    idx_all = np.arange(n, dtype=np.float64)
    y_interp = np.interp(idx_all, idx_all[good], y[good])
    cont0 = median_filter(y_interp, size=min(w_c, max(7, n // 2)), mode="nearest")
    res0 = y_interp - cont0
    mad0 = max(exact_mad_1d(res0[good]), 1e-12)

    # Second pass clips narrow emission/absorption spikes (> 2.5 sigma) before final median filter
    cont_mask = good & (np.abs(res0) <= 2.5 * mad0)
    if int(np.sum(cont_mask)) >= 8:
        y_interp2 = np.interp(idx_all, idx_all[cont_mask], y[cont_mask])
    else:
        y_interp2 = y_interp
    cont = median_filter(y_interp2, size=min(w_c, max(7, n // 2)), mode="nearest")
    res = y - cont

    rmad = _compute_rolling_mad_1d(res, good, win_bins=max(24, int(win_mad_px)))
    err_arr = np.asarray(err, dtype=np.float64)
    err_pos = np.where(np.isfinite(err_arr) & (err_arr > 0.0), err_arr, mad0)
    med_err = max(1e-12, float(np.median(err_pos[good])))
    sig = np.maximum(rmad, np.maximum(0.65 * err_pos, 0.45 * med_err))
    z = np.where(good & np.isfinite(res) & (sig > 0.0), res / sig, 0.0)
    return cont, res, sig, z


def _fit_1d_lsf_annuli_v54(
    wave: np.ndarray,
    res: np.ndarray,
    sig: np.ndarray,
    z: np.ndarray,
    idx: int,
    resolving_power: float,
    eta_1px_min: float = 0.22,
    far_wing_max: float = 0.55,
    min_snr_mid: float = 6.5,
    min_snr_outer: float = 6.0,
) -> dict[str, Any]:
    """Evaluate matched Gaussian LSF shape, spike concentration eta_1px, and broad-wing veto."""
    n = len(wave)
    w0 = float(wave[idx])
    dw = max(1e-12, float(np.median(np.diff(wave[max(0, idx - 8) : min(n, idx + 9)]))))
    sig_kms = C_KMS / (max(100.0, float(resolving_power)) * FWHM_FACTOR)
    sig_a = max(0.35 * dw, w0 * (sig_kms / C_KMS))
    sig_px = sig_a / dw

    hw = max(8, min(36, int(math.ceil(5.5 * sig_px)) + 3))
    i0 = max(0, idx - hw)
    i1 = min(n, idx + hw + 1)
    w_loc = wave[i0:i1]
    r_loc = res[i0:i1]
    s_loc = np.maximum(sig[i0:i1], 1e-12)
    z_loc = z[i0:i1]

    vel = C_KMS * (w_loc - w0) / max(1e-9, w0)
    abs_v = np.abs(vel)
    core_m = abs_v <= 3.0 * sig_kms
    mid_sb = (abs_v >= 3.5 * sig_kms) & (abs_v <= 16.0 * sig_kms)
    out_sb = (abs_v >= 5.5 * sig_kms) & (abs_v <= 24.0 * sig_kms)

    sig_mid = exact_mad_1d(r_loc[mid_sb]) if int(np.sum(mid_sb)) >= 4 else float(s_loc[idx - i0])
    sig_out = exact_mad_1d(r_loc[out_sb]) if int(np.sum(out_sb)) >= 4 else sig_mid
    sig_mid = max(sig_mid, 0.7 * float(s_loc[idx - i0]), 1e-12)
    sig_out = max(sig_out, 0.7 * float(s_loc[idx - i0]), 1e-12)

    # Optimal Gaussian weighted matched-filter amplitude
    g_core = np.exp(-0.5 * ((w_loc[core_m] - w0) / sig_a) ** 2)
    den_g = max(1e-12, float(np.sum(g_core * g_core)))
    amp = float(np.sum(g_core * r_loc[core_m]) / den_g) if int(np.sum(core_m)) >= 3 else float(res[idx])
    rms_core = amp * math.sqrt(den_g)
    snr_mid = rms_core / sig_mid
    snr_outer = rms_core / sig_out

    c_mod = amp * g_core
    c_vec = r_loc[core_m]
    c_norm = math.sqrt(max(1e-24, float(np.sum(c_mod * c_mod)))) * math.sqrt(max(1e-24, float(np.sum(c_vec * c_vec))))
    cosine = float(np.sum(c_mod * c_vec) / c_norm) if c_norm > 0.0 else 0.0

    # Empirical FWHM ratio relative to instrumental FWHM = 2.3548 * sig_kms
    half_h = 0.5 * max(1e-12, float(r_loc[idx - i0]))
    above_half = np.where(c_vec >= half_h)[0]
    if len(above_half) >= 2:
        dv_emp = float(vel[core_m][above_half[-1]] - vel[core_m][above_half[0]]) + (dw / w0 * C_KMS)
    else:
        dv_emp = dw / w0 * C_KMS
    fwhm_inst_kms = C_KMS / max(100.0, float(resolving_power))
    fwhm_ratio = dv_emp / max(1e-6, fwhm_inst_kms)

    # 1-pixel cosmic ray test & broad-band wing test
    z_pk = float(z[idx])
    wing1 = max(float(z[max(0, idx - 1)]), float(z[min(n - 1, idx + 1)]))
    eta_1px = wing1 / max(1e-6, z_pk)
    is_cr = bool(sig_px >= 0.65 and eta_1px < eta_1px_min)

    w3_idx = [j for j in range(max(0, idx - 6), min(n, idx + 7)) if abs(j - idx) >= 4]
    far_wing = max([float(z[j]) for j in w3_idx], default=0.0) / max(1e-6, z_pk) if z_pk > 0.0 else 0.0
    is_broad = bool(fwhm_ratio > 1.85 or far_wing > far_wing_max)

    passes = bool(
        (amp > 0.0)
        and (snr_mid >= min_snr_mid)
        and (snr_outer >= min_snr_outer)
        and (cosine >= 0.72)
        and (not is_cr)
        and (not is_broad)
        and (0.28 <= fwhm_ratio <= 1.85)
    )
    return {
        "snr_mid": float(snr_mid),
        "snr_outer": float(snr_outer),
        "amp": float(amp),
        "cosine": float(cosine),
        "fwhm_ratio": float(fwhm_ratio),
        "sig_px": float(sig_px),
        "eta_1px": float(eta_1px),
        "far_wing": float(far_wing),
        "is_cr": is_cr,
        "is_broad": is_broad,
        "passes_lsf": passes,
    }


def scan_sofia_exes_midir_echelle_v54(
    orders: list[dict[str, Any]],
    cfg: dict[str, Any],
    star: str = "",
    dist_pc: float = 10.0,
    teff_k: float = 5000.0,
    bary_corr_kms: float = 0.0,
    star_rv_kms: float = 0.0,
    cohort_topo_peaks_um: list[float] | None = None,
) -> dict[str, Any]:
    """
    Engine V5.4 (`SOFIA_EXES_STRATOSPHERIC_V54`): R = 50,000-200,000 stratospheric mid-IR
    echelle laser & emission-line search with ATRAN telluric vetting (`G2_EXES_ATRAN`),
    RP-matched LSF + CR/broad-band gating (`G4_G5_EXES`), mid-IR atomic/H2 atlas veto,
    cross-star topocentric coincidence veto (`G6_EXES`), and direct Jy CGS EIRP bounds.
    """
    min_atran = float(cfg.get("exes_min_atran", 0.70))
    min_atran_15 = float(cfg.get("exes_min_atran_15kms", 0.40))
    max_atran_grad = float(cfg.get("exes_max_atran_grad_kms", 0.08))
    min_z_seed = float(cfg.get("exes_min_z_seed", 5.5))
    min_snr_mid = float(cfg.get("exes_min_snr_mid", 6.5))
    min_snr_outer = float(cfg.get("exes_min_snr_outer", 6.0))
    eta_1px_min = float(cfg.get("exes_eta_1px_min", 0.22))
    far_wing_max = float(cfg.get("exes_far_wing_max", 0.52))
    g6_tol_kms = float(cfg.get("exes_g6_topo_tol_kms", 15.0))
    topo_peers = list(cohort_topo_peaks_um or [])

    raw_topo_peaks_um: list[float] = []
    candidates: list[dict[str, Any]] = []
    n_g1_raw = 0
    n_g2_atran_vetoed = 0
    n_g3_atlas_vetoed = 0
    n_g45_vetoed = 0
    n_g6_topo_vetoed = 0
    n_qualified = 0

    order_summaries: list[dict[str, Any]] = []
    band_best_ul: dict[str, dict[str, float]] = {}
    c_a_s = C_SI * 1e10

    for oi, od in enumerate(orders):
        w_um = np.asarray(od["wave_um"], dtype=np.float64)
        flx = np.asarray(od["flux_jy"], dtype=np.float64)
        err = np.asarray(od["err_jy"], dtype=np.float64)
        atr = np.asarray(od.get("atran", np.ones_like(w_um)), dtype=np.float64)
        wt = np.asarray(od.get("weight", np.ones_like(w_um)), dtype=np.float64)
        rp = float(od.get("rp", cfg.get("resolving_power", 66667.0)))
        if rp < 1000.0:
            rp = float(cfg.get("resolving_power", 66667.0))

        # Sort ascending in wavelength
        sidx = np.argsort(w_um)
        w_um, flx, err, atr, wt = w_um[sidx], flx[sidx], err[sidx], atr[sidx], wt[sidx]
        w_a = w_um * 1e4
        n_px = len(w_a)
        if n_px < 48:
            continue

        # Quality + edge trim
        trim = max(6, int(round(0.025 * n_px)))
        in_trim = np.zeros(n_px, dtype=bool)
        in_trim[trim : n_px - trim] = True
        fin_m = in_trim & np.isfinite(w_um) & np.isfinite(flx) & np.isfinite(err) & np.isfinite(atr) & (w_um > 0.0) & (err > 0.0) & (wt > 0.0)
        if int(np.sum(fin_m)) < 24:
            continue

        # G2_EXES_ATRAN telluric gradient & deep-trough +-15 km/s proximity check
        dv_px = np.maximum(1e-3, C_KMS * np.gradient(w_um) / np.maximum(1e-6, w_um))
        atran_grad = np.abs(np.gradient(atr)) / dv_px
        hw_15 = max(1, int(round(15.0 / max(0.2, float(np.median(dv_px[fin_m]))))))
        min_atr_15 = -(-atr)
        # Fast sliding minimum over 2*hw_15+1
        from scipy.ndimage import minimum_filter1d
        min_atr_15 = minimum_filter1d(np.where(np.isfinite(atr), atr, 1.0), size=2 * hw_15 + 1, mode="nearest")

        atran_clean = (atr >= min_atran) & (min_atr_15 >= min_atran_15) & (atran_grad <= max_atran_grad)
        clean_mask = fin_m & atran_clean
        clean_frac = float(np.sum(clean_mask)) / max(1.0, float(np.sum(fin_m)))
        if int(np.sum(clean_mask)) < 20:
            # Fallback if extreme telluric block leaves too few pixels
            clean_mask = fin_m & (atr >= 0.45)
        if int(np.sum(clean_mask)) < 16:
            continue

        cont, res, sig, z = _robust_sliding_cont_and_mad_v54(w_a, flx, err, clean_mask, win_cont_px=45, win_mad_px=128)
        z_raw = np.where(fin_m & (sig > 0.0), res / sig, 0.0)

        # Direct Jy CGS 10 m laser limit for this order
        med_cont_jy = float(np.median(flx[clean_mask]))
        med_sig_jy = float(np.median(sig[clean_mask]))
        lam_c_um = float(np.median(w_um[clean_mask]))
        lam_c_a = lam_c_um * 1e4
        sig_flam_cgs = 1e-23 * med_sig_jy * c_a_s / (lam_c_a * lam_c_a)
        ul = compute_photon_beam_upper_limit(
            wave_a=lam_c_a,
            amp_rel_lim=1.0,
            teff_k=float(teff_k),
            dist_pc=float(dist_pc),
            stellar_radius_rsun=1.0,
            radiometric_anchor="SOFIA_EXES_DIRECT_CGS",
            resolving_power=rp,
            direct_flam_cgs=8.0 * sig_flam_cgs,
        )
        ul["direct_flam_8sig_cgs"] = float(8.0 * sig_flam_cgs)
        ul["med_sigma_mad_jy"] = float(med_sig_jy)
        ul["med_cont_jy"] = float(med_cont_jy)
        ul["center_wave_um"] = float(lam_c_um)
        ul["resolving_power"] = float(rp)
        band_key = f"EXES_O{oi:02d}_{int(round(lam_c_um * 10)):03d}"
        order_summaries.append({
            "order_idx": oi,
            "lam_min_um": round(float(w_um[clean_mask].min()), 5),
            "lam_max_um": round(float(w_um[clean_mask].max()), 5),
            "lam_center_um": round(lam_c_um, 5),
            "rp": round(rp, 1),
            "clean_frac": round(clean_frac, 4),
            "med_cont_jy": round(med_cont_jy, 4),
            "med_sig_jy": round(med_sig_jy, 4),
            "p_beam_10m_kw": round(float(ul["p_beam_10m_kw"]), 6),
        })

        # Map into closest canonical EXES band or dynamic best
        best_canon = min(CALIBRATION_BANDS_SOFIA_EXES, key=lambda b: abs(b["center_wave_A"] - lam_c_a))
        if abs(best_canon["center_wave_A"] - lam_c_a) <= 0.25 * best_canon["center_wave_A"]:
            bid = best_canon["band_id"]
        else:
            bid = band_key
        if bid not in band_best_ul or ul["p_beam_10m_kw"] < band_best_ul[bid]["p_beam_10m_kw"]:
            band_best_ul[bid] = ul

        # NMS peak scan across raw finite mask (so we also count telluric-edge vetoes!)
        pk_idx = np.where(z_raw >= min_z_seed)[0]
        if len(pk_idx) == 0:
            continue
        ord_pk = pk_idx[np.argsort(z_raw[pk_idx])[::-1]]
        taken = np.zeros(n_px, dtype=bool)
        for idx in ord_pk:
            if taken[idx]:
                continue
            lo_n, hi_n = max(0, idx - 6), min(n_px, idx + 7)
            if float(z_raw[idx]) < float(np.max(z_raw[lo_n:hi_n])) - 1e-12:
                continue
            taken[lo_n:hi_n] = True
            n_g1_raw += 1

            w_obs_um = float(w_um[idx])
            raw_topo_peaks_um.append(w_obs_um)
            is_atran_ok = bool(atran_clean[idx])
            if not is_atran_ok:
                n_g2_atran_vetoed += 1
                candidates.append({
                    "star": star,
                    "order_idx": oi,
                    "wave_obs_um": round(w_obs_um, 6),
                    "wave_rest_um": round(w_obs_um * (1.0 + (bary_corr_kms - star_rv_kms) / C_KMS), 6),
                    "z_peak": round(float(z_raw[idx]), 3),
                    "atran": round(float(atr[idx]), 4),
                    "rp": round(rp, 1),
                    "g2_atran_pass": False,
                    "g45_lsf_pass": False,
                    "g3_atlas_match": "",
                    "g6_topo_vetoed": False,
                    "qualified_v54": False,
                    "veto_reason": "G2_EXES_ATRAN_TELLURIC",
                })
                continue

            lsf = _fit_1d_lsf_annuli_v54(
                w_a, res, sig, z, int(idx), rp,
                eta_1px_min=eta_1px_min, far_wing_max=far_wing_max,
                min_snr_mid=min_snr_mid, min_snr_outer=min_snr_outer,
            )
            if not lsf["passes_lsf"]:
                n_g45_vetoed += 1
                reason = "G5_EXES_1PX_CR" if lsf["is_cr"] else ("G5_EXES_BROAD_FEATURE" if lsf["is_broad"] else "G4_EXES_LSF_FAIL")
                candidates.append({
                    "star": star,
                    "order_idx": oi,
                    "wave_obs_um": round(w_obs_um, 6),
                    "wave_rest_um": round(w_obs_um * (1.0 + (bary_corr_kms - star_rv_kms) / C_KMS), 6),
                    "z_peak": round(float(z_raw[idx]), 3),
                    "atran": round(float(atr[idx]), 4),
                    "rp": round(rp, 1),
                    "g2_atran_pass": True,
                    "g45_lsf_pass": False,
                    "g3_atlas_match": "",
                    "g6_topo_vetoed": False,
                    "qualified_v54": False,
                    "veto_reason": reason,
                    "eta_1px": round(lsf["eta_1px"], 3),
                    "fwhm_ratio": round(lsf["fwhm_ratio"], 3),
                })
                continue

            # Stellar rest-frame natural emission atlas check
            w_rest_um = w_obs_um * (1.0 + (float(bary_corr_kms) - float(star_rv_kms)) / C_KMS)
            atlas_hit = ""
            for lname, l_um in EXES_NATURAL_LINES_UM:
                if abs(C_KMS * (w_rest_um - l_um) / l_um) <= 180.0:
                    atlas_hit = lname
                    break
            if atlas_hit:
                n_g3_atlas_vetoed += 1
                candidates.append({
                    "star": star,
                    "order_idx": oi,
                    "wave_obs_um": round(w_obs_um, 6),
                    "wave_rest_um": round(w_rest_um, 6),
                    "z_peak": round(float(z_raw[idx]), 3),
                    "atran": round(float(atr[idx]), 4),
                    "rp": round(rp, 1),
                    "g2_atran_pass": True,
                    "g45_lsf_pass": True,
                    "g3_atlas_match": atlas_hit,
                    "g6_topo_vetoed": False,
                    "qualified_v54": False,
                    "veto_reason": f"G3_EXES_NATURAL_LINE:{atlas_hit}",
                })
                continue

            # Cross-star topocentric telluric coincidence check
            g6_hit = any(abs(C_KMS * (w_obs_um - pw) / max(1e-6, w_obs_um)) <= g6_tol_kms for pw in topo_peers)
            if g6_hit:
                n_g6_topo_vetoed += 1
                candidates.append({
                    "star": star,
                    "order_idx": oi,
                    "wave_obs_um": round(w_obs_um, 6),
                    "wave_rest_um": round(w_rest_um, 6),
                    "z_peak": round(float(z_raw[idx]), 3),
                    "atran": round(float(atr[idx]), 4),
                    "rp": round(rp, 1),
                    "g2_atran_pass": True,
                    "g45_lsf_pass": True,
                    "g3_atlas_match": "",
                    "g6_topo_vetoed": True,
                    "qualified_v54": False,
                    "veto_reason": "G6_EXES_CROSS_STAR_TOPO",
                })
                continue

            n_qualified += 1
            candidates.append({
                "star": star,
                "order_idx": oi,
                "wave_obs_um": round(w_obs_um, 6),
                "wave_rest_um": round(w_rest_um, 6),
                "z_peak": round(float(z_raw[idx]), 3),
                "atran": round(float(atr[idx]), 4),
                "rp": round(rp, 1),
                "g2_atran_pass": True,
                "g45_lsf_pass": True,
                "g3_atlas_match": "",
                "g6_topo_vetoed": False,
                "qualified_v54": True,
                "veto_reason": "STAGE1_QUALIFIED",
                "snr_mid": round(lsf["snr_mid"], 3),
                "snr_outer": round(lsf["snr_outer"], 3),
                "eta_1px": round(lsf["eta_1px"], 3),
                "fwhm_ratio": round(lsf["fwhm_ratio"], 3),
            })

    best_ul = min(band_best_ul.items(), key=lambda kv: kv[1]["p_beam_10m_kw"]) if band_best_ul else None
    return {
        "star": star,
        "n_orders_scanned": len(order_summaries),
        "n_g1_raw": n_g1_raw,
        "n_g2_atran_vetoed": n_g2_atran_vetoed,
        "n_g45_vetoed": n_g45_vetoed,
        "n_g3_atlas_vetoed": n_g3_atlas_vetoed,
        "n_g6_topo_vetoed": n_g6_topo_vetoed,
        "n_qualified_v54": n_qualified,
        "candidates": candidates,
        "raw_topo_peaks_um": raw_topo_peaks_um,
        "order_summaries": order_summaries,
        "upper_limits": band_best_ul,
        "best_band": best_ul[0] if best_ul else "",
        "best_p_beam_10m_kw": round(float(best_ul[1]["p_beam_10m_kw"]), 6) if best_ul else math.nan,
    }


def run_sofia_exes_calibration_v54(seed: int = 9601) -> dict[str, Any]:
    """
    `CALIBRATION_V54_SOFIA_EXES_180`: 180 synthetic stratospheric EXES mid-IR trials:
      - 60 clean unresolved R=66,667 narrowband lasers (ATRAN >= 0.80, clean windows) -> PASS
      - 40 telluric-edge ATRAN artifact spikes (ATRAN in [0.18, 0.58] or steep gradient) -> VETO
      - 40 single-pixel mid-IR Si:As IBC cosmic rays -> VETO
      - 40 natural fine-structure/H2 emission lines (Ne II, O IV, S III, H2) -> VETO
    """
    rng = np.random.default_rng(seed)
    cfg = get_inst_config("SOFIA_EXES", resolving_power=66667.0)
    n_px = 960
    lam_c = 13.90
    rp = 66667.0
    sig_um = lam_c / (rp * FWHM_FACTOR)
    w_um = np.linspace(lam_c - 0.045, lam_c + 0.045, n_px)
    # Build two simulated ATRAN telluric troughs away from the clean injection window
    atr_base = np.ones(n_px, dtype=np.float64) * 0.94
    trough1_c = lam_c - 0.025
    trough2_c = lam_c + 0.026
    atr_base -= 0.72 * np.exp(-0.5 * ((w_um - trough1_c) / 0.00045) ** 2)
    atr_base -= 0.65 * np.exp(-0.5 * ((w_um - trough2_c) / 0.00050) ** 2)

    trials: list[dict[str, Any]] = []
    # 1. 60 Clean Laser Injections
    laser_rec = 0
    for i in range(60):
        cont = 25.0 + 1.5 * np.sin(2.0 * math.pi * np.linspace(0, 1.5, n_px))
        noise_sig = 0.25
        flx = cont + rng.normal(0.0, noise_sig, n_px)
        err = np.full(n_px, noise_sig)
        w_inj = float(rng.uniform(lam_c - 0.012, lam_c + 0.012))
        snr_inj = float(rng.uniform(8.5, 13.0))
        flx += (snr_inj * noise_sig) * np.exp(-0.5 * ((w_um - w_inj) / sig_um) ** 2)
        res = scan_sofia_exes_midir_echelle_v54([{"wave_um": w_um, "flux_jy": flx, "err_jy": err, "atran": atr_base, "weight": np.ones(n_px), "rp": rp}], cfg, star=f"SIM_EXES_LASER_{i}")
        ok = res["n_qualified_v54"] >= 1
        laser_rec += int(ok)
        trials.append({"suite": "CALIBRATION_V54_SOFIA_EXES_180", "class": "CLEAN_LASER", "trial": i, "expected": 1, "observed": int(ok)})

    # 2. 40 ATRAN Telluric Artifacts
    atran_veto = 0
    for i in range(40):
        cont = np.full(n_px, 20.0)
        noise_sig = 0.25
        flx = cont + rng.normal(0.0, noise_sig, n_px)
        err = np.full(n_px, noise_sig)
        w_bad = trough1_c if (i % 2 == 0) else trough2_c + float(rng.uniform(-0.0002, 0.0002))
        flx += float(rng.uniform(9.0, 16.0)) * noise_sig * np.exp(-0.5 * ((w_um - w_bad) / sig_um) ** 2)
        res = scan_sofia_exes_midir_echelle_v54([{"wave_um": w_um, "flux_jy": flx, "err_jy": err, "atran": atr_base, "weight": np.ones(n_px), "rp": rp}], cfg, star=f"SIM_EXES_ATRAN_{i}")
        ok = res["n_qualified_v54"] == 0
        atran_veto += int(ok)
        trials.append({"suite": "CALIBRATION_V54_SOFIA_EXES_180", "class": "ATRAN_ARTIFACT", "trial": i, "expected": 0, "observed": int(res["n_qualified_v54"] > 0)})

    # 3. 40 1-Pixel Detector Cosmic Rays
    cr_veto = 0
    for i in range(40):
        noise_sig = 0.25
        flx = 22.0 + rng.normal(0.0, noise_sig, n_px)
        err = np.full(n_px, noise_sig)
        idx_c = int(rng.integers(250, 700))
        flx[idx_c] += float(rng.uniform(10.0, 22.0)) * noise_sig
        res = scan_sofia_exes_midir_echelle_v54([{"wave_um": w_um, "flux_jy": flx, "err_jy": err, "atran": atr_base, "weight": np.ones(n_px), "rp": rp}], cfg, star=f"SIM_EXES_CR_{i}")
        ok = res["n_qualified_v54"] == 0
        cr_veto += int(ok)
        trials.append({"suite": "CALIBRATION_V54_SOFIA_EXES_180", "class": "COSMIC_RAY_1PX", "trial": i, "expected": 0, "observed": int(res["n_qualified_v54"] > 0)})

    # 4. 40 Natural Atomic Fine-Structure / H2 Lines ([Ne II], [S III], [O IV], H2 S(2))
    nat_veto = 0
    nat_lines = [12.8135, 18.7130, 25.8903, 12.2786]
    for i in range(40):
        lc = nat_lines[i % len(nat_lines)]
        wn = np.linspace(lc - 0.04, lc + 0.04, n_px)
        an = np.full(n_px, 0.94)
        noise_sig = 0.25
        flx = 18.0 + rng.normal(0.0, noise_sig, n_px)
        err = np.full(n_px, noise_sig)
        sig_nat = lc / (rp * FWHM_FACTOR) * float(rng.uniform(1.0, 2.5))
        flx += float(rng.uniform(9.0, 18.0)) * noise_sig * np.exp(-0.5 * ((wn - lc) / sig_nat) ** 2)
        res = scan_sofia_exes_midir_echelle_v54([{"wave_um": wn, "flux_jy": flx, "err_jy": err, "atran": an, "weight": np.ones(n_px), "rp": rp}], cfg, star=f"SIM_EXES_NAT_{i}")
        ok = res["n_qualified_v54"] == 0
        nat_veto += int(ok)
        trials.append({"suite": "CALIBRATION_V54_SOFIA_EXES_180", "class": "NATURAL_ATLAS_LINE", "trial": i, "expected": 0, "observed": int(res["n_qualified_v54"] > 0)})

    return {
        "n_trials": 180,
        "laser_recovery": f"{laser_rec}/60 ({laser_rec/60.0:.4f})",
        "atran_veto": f"{atran_veto}/40 ({atran_veto/40.0:.4f})",
        "cr_veto": f"{cr_veto}/40 ({cr_veto/40.0:.4f})",
        "natural_line_veto": f"{nat_veto}/40 ({nat_veto/40.0:.4f})",
        "laser_rec_count": laser_rec,
        "veto_count": atran_veto + cr_veto + nat_veto,
        "trials": trials,
    }


# ---------------------------------------------------------------------------
# Engine V5.4-B: Coherent Sub-Threshold 2D Shift-and-Stack (`DRIFT_V54`)
# ---------------------------------------------------------------------------

def scan_coherent_shift_stack_drift_v54(
    wave_rest: np.ndarray,
    fn_epochs: np.ndarray,
    sig_epochs: np.ndarray,
    mjd_epochs: np.ndarray,
    v_obs_to_rest_epochs_kms: np.ndarray,
    cfg: dict[str, Any],
    star: str = "",
    star_idx: int = 0,
    z_rpca_mat: np.ndarray | None = None,
    bervs_cohort: np.ndarray | None = None,
    known_orb_period_days: float | None = None,
    known_orb_t0_bjd: float | None = None,
    known_orb_kp_kms: float | None = None,
) -> dict[str, Any]:
    """
    Engine `DRIFT_V54_COHERENT_SHIFT_STACK`: Vectorized coherent inverse-variance matched-filter
    shift-and-stack across the full 2D `(N_epochs, N_wave)` residual waterfall for `N >= 4` campaigns.

    Uniquely recovers faint `2.8-3.8 sigma/epoch` drifting and orbiting beacons invisible to all
    single-epoch peak-chaining algorithms (`V5.1/V5.2/V5.3`) via `sqrt(N)` coherent integration,
    subject to Jackknife Leave-One-Out (`LOO`) persistence, zero-drift stationary veto, and
    BERV-sky topocentric coincidence veto.
    """
    w = np.asarray(wave_rest, dtype=np.float64)
    fn_e = np.asarray(fn_epochs, dtype=np.float64)
    sig_e = np.asarray(sig_epochs, dtype=np.float64)
    mjds = np.asarray(mjd_epochs, dtype=np.float64)
    v_o2r = np.asarray(v_obs_to_rest_epochs_kms, dtype=np.float64)

    n_ep_in = int(fn_e.shape[0]) if fn_e.ndim == 2 else 0
    empty = {
        "star": star,
        "n_epochs": n_ep_in,
        "n_distinct_epochs": 0,
        "n_trajectories_evaluated": 0,
        "n_raw_candidates": 0,
        "candidates": [],
    }
    if fn_e.ndim != 2 or n_ep_in < 4 or len(w) < 256:
        return empty

    ord_t = np.argsort(mjds)
    mjds = mjds[ord_t]
    fn_e = fn_e[ord_t]
    sig_e = sig_e[ord_t]
    v_o2r = v_o2r[ord_t]
    n_ep, n_wave = fn_e.shape

    min_dt_days = float(cfg.get("drift_v53_min_dt_days", 0.01))
    distinct_mjd = [float(mjds[0])]
    for tk in mjds[1:]:
        if float(tk) - distinct_mjd[-1] >= min_dt_days:
            distinct_mjd.append(float(tk))
    if len(distinct_mjd) < int(cfg.get("drift_v54_min_epochs", 4)):
        return empty

    sig_v = max(0.8, float(cfg.get("sigma_v_kms", 2.0)))
    min_snr_stack = float(cfg.get("drift_v54_min_snr_stack", 7.5))
    min_snr_loo = float(cfg.get("drift_v54_min_snr_loo", 5.2))
    max_single_frac = float(cfg.get("drift_v54_max_single_epoch_frac", 0.45))
    min_pos_frac = float(cfg.get("drift_v54_min_pos_frac", 0.60))
    min_dv_span = float(cfg.get("drift_v54_min_dv_span_kms", 12.0))
    stat_margin = float(cfg.get("drift_v54_stat_margin_sigma", 2.2))
    sky_margin = float(cfg.get("drift_v54_sky_margin_sigma", 1.5))
    max_masked_frac = float(cfg.get("drift_v54_max_masked_frac", 0.30))

    # Build static telluric/OH masks and rolling-MAD scaled 2D Z matrix (common-mode stellar median removed)
    static_masks = np.array([_is_masked_static_v50(w, cfg, float(v_o2r[k])) for k in range(n_ep)], dtype=bool)
    raw_res = np.where(np.isfinite(fn_e) & np.isfinite(sig_e) & (sig_e > 0.0), (fn_e - 1.0) / np.maximum(sig_e, 1e-6), np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        med_tmpl = np.nanmedian(raw_res, axis=0)
    med_tmpl = np.where(np.isfinite(med_tmpl), med_tmpl, 0.0)

    Z = np.zeros_like(fn_e, dtype=np.float64)
    V = np.zeros_like(fn_e, dtype=bool)
    for k in range(n_ep):
        fin_k = np.isfinite(fn_e[k]) & np.isfinite(sig_e[k]) & (sig_e[k] > 0.0)
        rk = np.where(fin_k, raw_res[k] - med_tmpl, 0.0)
        good_k = fin_k & (~static_masks[k])
        rmad = _compute_rolling_mad_1d(rk, good_k, win_bins=512)
        Z[k] = np.where(good_k, rk / np.maximum(1.0, rmad), 0.0)
        V[k] = good_k

    # Guard against sparse bad columns where >50% of epochs are masked
    col_ok = np.sum(V, axis=0) >= max(4, int(math.ceil(0.55 * n_ep)))
    Z[:, ~col_ok] = 0.0
    V[:, ~col_ok] = False

    # Uniform log-lambda resampling where Doppler shifts are exact array shifts!
    ln_w0 = math.log(float(w[0]))
    ln_w1 = math.log(float(w[-1]))
    dv_grid_kms = max(1.2, min(4.5, 0.70 * sig_v))
    dln = dv_grid_kms / C_KMS
    n_log = int(math.floor((ln_w1 - ln_w0) / dln)) + 1
    if n_log > 160000:
        # Preserve optical Nyquist while bounding vector memory on huge stitched echelles
        dln = (ln_w1 - ln_w0) / 160000.0
        dv_grid_kms = dln * C_KMS
        n_log = 160001
    ln_grid = ln_w0 + dln * np.arange(n_log, dtype=np.float64)
    w_log = np.exp(ln_grid)
    ln_w_native = np.log(w)

    # Resample per-epoch Z and mask V onto log-lambda grid, then convolve with unit-L2 Gaussian PSF kernel
    sig_log_px = max(0.55, sig_v / dv_grid_kms)
    k_half = max(3, int(math.ceil(3.2 * sig_log_px)))
    kx = np.arange(-k_half, k_half + 1, dtype=np.float64)
    g_kern = np.exp(-0.5 * (kx / sig_log_px) ** 2)
    g_kern /= math.sqrt(float(np.sum(g_kern * g_kern)))

    M_log = np.zeros((n_ep, n_log), dtype=np.float64)
    V_log = np.zeros((n_ep, n_log), dtype=bool)
    for k in range(n_ep):
        z_l = np.interp(ln_grid, ln_w_native, Z[k], left=0.0, right=0.0)
        v_l = np.interp(ln_grid, ln_w_native, V[k].astype(np.float64), left=0.0, right=0.0) >= 0.7
        M_log[k] = convolve1d(z_l, g_kern, mode="constant", cval=0.0)
        V_log[k] = v_l

    # Standardize M_log robustly along valid pixels so matched noise std == 1.000
    for k in range(n_ep):
        mk = M_log[k, V_log[k]]
        if len(mk) >= 64:
            mad_m = exact_mad_1d(mk)
            if mad_m > 0.2:
                M_log[k] /= mad_m

    # Precompute integer shifts around each pixel for stationary & BERV-sky checks
    pad = int(math.ceil(260.0 / dv_grid_kms)) + 4
    n_core = n_log - 2 * pad
    if n_core < 64:
        return empty
    base_idx = np.arange(pad, n_log - pad, dtype=np.int64)

    t_mid = 0.5 * (float(mjds[0]) + float(mjds[-1]))
    dt_half = max(1e-3, 0.5 * (float(mjds[-1]) - float(mjds[0])))
    tau = (mjds - t_mid) / dt_half  # normalized time in [-1, +1]

    M_z = np.ascontiguousarray(np.where(V_log, M_log, 0.0), dtype=np.float64)
    V_u8 = np.ascontiguousarray(V_log.astype(np.uint8))
    inv_sqrt_nv = np.zeros(n_ep + 1, dtype=np.float64)
    for k_nv in range(4, n_ep + 1):
        inv_sqrt_nv[k_nv] = 1.0 / math.sqrt(float(k_nv))

    def _eval_trajectory_vectorized(v_ep_kms: np.ndarray, branch: str, meta: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
        """Integrate M_log via zero-copy contiguous epoch slices along v_ep_kms."""
        dv_sp = float(np.max(v_ep_kms) - np.min(v_ep_kms))
        if dv_sp < min_dv_span or np.max(np.abs(v_ep_kms)) > 250.0:
            return [], 0
        sh = np.rint(v_ep_kms / dv_grid_kms).astype(np.int64)
        s_sum = M_z[0, pad + int(sh[0]) : pad + n_core + int(sh[0])].copy()
        nv = V_u8[0, pad + int(sh[0]) : pad + n_core + int(sh[0])].astype(np.int32)
        for k in range(1, n_ep):
            sk = int(sh[k])
            s_sum += M_z[k, pad + sk : pad + n_core + sk]
            nv += V_u8[k, pad + sk : pad + n_core + sk]

        max_pos_masked = int(math.floor(max_masked_frac * float(n_ep)))
        min_req_ep = max(4, n_ep - max_pos_masked)
        snr_stack = s_sum * inv_sqrt_nv[nv]
        hits_i = np.where((nv >= min_req_ep) & (snr_stack >= min_snr_stack))[0]
        if len(hits_i) == 0:
            return [], 1

        # Greedy NMS over core pixels
        ord_h = hits_i[np.argsort(snr_stack[hits_i])[::-1]]
        out_h: list[dict[str, Any]] = []
        used = np.zeros(n_core, dtype=bool)
        nms_r = max(4, int(round(8.0 * sig_log_px)))

        for ci in ord_h:
            if used[ci]:
                continue
            used[max(0, ci - nms_r) : min(n_core, ci + nms_r + 1)] = True
            c_glob = int(base_idx[ci])
            idxs_c = c_glob + sh
            vm_c = V_log[np.arange(n_ep), idxs_c]
            s_act = M_z[np.arange(n_ep), idxs_c][vm_c]
            n_val = len(s_act)
            if n_val < 4:
                continue
            s_max = float(np.max(s_act))
            sum_act = float(np.sum(s_act))
            snr_st = sum_act / math.sqrt(float(n_val))
            snr_loo = (sum_act - s_max) / math.sqrt(float(n_val - 1))
            if snr_loo < min_snr_loo:
                continue
            sum_pos = float(np.sum(np.maximum(s_act, 0.0)))
            single_frac = s_max / max(1e-6, sum_pos)
            if single_frac > max_single_frac:
                continue
            pos_frac = float(np.sum(s_act >= 1.5)) / float(n_val)
            if pos_frac < min_pos_frac:
                continue

            # Stationary stack check at fixed rest wavelength over [min(sh)-2, max(sh)+2]
            s_lo = max(0, int(np.min(sh)) - 2)
            s_hi = min(n_log - c_glob - 1, int(np.max(sh)) + 2)
            best_stat = -1e9
            for ds in range(s_lo, s_hi + 1):
                c_test = c_glob + ds
                if 0 <= c_test < n_log:
                    m_st = V_log[:, c_test]
                    if int(np.sum(m_st)) >= 4:
                        st_v = float(np.sum(M_z[m_st, c_test]) / math.sqrt(float(np.sum(m_st))))
                        if st_v > best_stat:
                            best_stat = st_v
            if (snr_st - best_stat) < stat_margin:
                continue

            # BERV-sky topocentric coincidence check
            v_sky_kms = v_ep_kms - v_o2r
            w_0 = float(w_log[c_glob])
            best_sky = -1e9
            for sk_ref in v_sky_kms[:: max(1, n_ep // 6)]:
                sh_sky = np.rint((sk_ref + v_o2r) / dv_grid_kms).astype(np.int64)
                idx_sky = np.clip(c_glob + sh_sky, 0, n_log - 1)
                m_sk = V_log[np.arange(n_ep), idx_sky]
                if int(np.sum(m_sk)) >= 4:
                    sk_v = float(np.sum(M_z[np.arange(n_ep)[m_sk], idx_sky[m_sk]]) / math.sqrt(float(np.sum(m_sk))))
                    if sk_v > best_sky:
                        best_sky = sk_v
            if (snr_st - best_sky) < sky_margin:
                continue

            # Optional cohort rarity check on endpoint & mid epochs
            rarity_min = 1.0
            if z_rpca_mat is not None and bervs_cohort is not None and z_rpca_mat.shape[0] >= 2:
                r_mid = compute_spectral_rarity_score(w, z_rpca_mat, bervs_cohort, star_idx, w_0, sig_v, polarity=1.0)
                rarity_min = float(r_mid["rarity_score"])
                if rarity_min < float(cfg.get("g7_min_rarity_score", 0.65)):
                    continue

            out_h.append({
                "star": star,
                "branch": branch,
                "wave0_rest_a": round(w_0, 5),
                "n_valid_epochs": n_val,
                "dv_span_kms": round(dv_sp, 3),
                "snr_stack": round(snr_st, 4),
                "snr_loo": round(snr_loo, 4),
                "snr_stationary": round(best_stat, 4),
                "snr_sky": round(best_sky, 4),
                "max_single_epoch_frac": round(single_frac, 4),
                "pos_epoch_frac": round(pos_frac, 4),
                "rarity_score": round(rarity_min, 4),
                **meta,
            })
        return out_h, 1

    # 1. Vectorized Linear + Curved Acceleration Grid (`v_ep = half_slope * tau + sag * (tau^2 - 0.3333)`)
    slopes = np.linspace(-180.0, 180.0, 41)
    sags = np.linspace(-60.0, 60.0, 9)
    raw_cands: list[dict[str, Any]] = []
    n_eval = 0

    for hs in slopes:
        for sg in sags:
            if abs(hs) < 6.0 and abs(sg) < 8.0:
                continue
            v_curve = float(hs) * tau + float(sg) * (tau * tau - 1.0 / 3.0)
            br = "CURVED_STACK_V54" if abs(sg) >= 8.0 else "LINEAR_STACK_V54"
            hits, cnt = _eval_trajectory_vectorized(v_curve, br, {"half_slope_kms": round(float(hs), 2), "quad_sag_kms": round(float(sg), 2)})
            n_eval += cnt
            raw_cands.extend(hits)

    # 2. Vectorized Periodic / Keplerian Sinusoidal Grid (`v_ep = K * sin(2*pi*(t - t0)/P + phi)`)
    t_rel = mjds - float(mjds[0])
    p_grid_blind = list(np.geomspace(1.2, 60.0, 10))
    phi_grid_blind = np.linspace(0.0, 2.0 * math.pi, 10, endpoint=False)
    k_grid_blind = np.array([35.0, 70.0, 115.0, 175.0])

    if (float(mjds[-1]) - float(mjds[0])) >= 1.0 and n_ep >= 6:
        for p_d in p_grid_blind:
            for phi in phi_grid_blind:
                sin_v = np.sin(2.0 * math.pi * t_rel / float(p_d) + float(phi))
                for k_amp in k_grid_blind:
                    v_orb = float(k_amp) * sin_v
                    hits, cnt = _eval_trajectory_vectorized(v_orb, "PERIODIC_STACK_V54", {"period_d": round(float(p_d), 4), "k_amp_kms": round(float(k_amp), 2), "phi_rad": round(float(phi), 3)})
                    n_eval += cnt
                    raw_cands.extend(hits)
        if known_orb_period_days is not None and math.isfinite(float(known_orb_period_days)) and float(known_orb_period_days) > 0.3:
            p_k = float(known_orb_period_days)
            phi_k_grid = np.linspace(0.0, 2.0 * math.pi, 24, endpoint=False)
            k_k_grid = np.array([35.0, 70.0, 110.0, 155.0, 195.0])
            if known_orb_kp_kms is not None and math.isfinite(float(known_orb_kp_kms)) and float(known_orb_kp_kms) >= 12.0:
                k_k_grid = np.unique(np.append(k_k_grid, float(known_orb_kp_kms)))
            for phi in phi_k_grid:
                sin_v = np.sin(2.0 * math.pi * t_rel / p_k + float(phi))
                for k_amp in k_k_grid:
                    v_orb = float(k_amp) * sin_v
                    hits, cnt = _eval_trajectory_vectorized(v_orb, "KEPLERIAN_COHERENT_STACK_V54", {"period_d": round(p_k, 4), "k_amp_kms": round(float(k_amp), 2), "phi_rad": round(float(phi), 3)})
                    n_eval += cnt
                    raw_cands.extend(hits)

    # Deduplicate overlapping wavelength detections keeping highest SNR_stack
    raw_cands.sort(key=lambda c: -c["snr_stack"])
    final_cands: list[dict[str, Any]] = []
    for c in raw_cands:
        w0 = c["wave0_rest_a"]
        if any(abs(C_KMS * (w0 - kc["wave0_rest_a"]) / max(1e-6, w0)) < 25.0 for kc in final_cands):
            continue
        final_cands.append(c)

    return {
        "star": star,
        "n_epochs": n_ep,
        "n_distinct_epochs": len(distinct_mjd),
        "n_trajectories_evaluated": n_eval,
        "n_pixel_trajectory_integrals": int(n_eval * n_core),
        "n_raw_candidates": len(final_cands),
        "candidates": final_cands,
    }


def run_coherent_shift_stack_calibration_v54(seed: int = 9602) -> dict[str, Any]:
    """
    `CALIBRATION_V54_COHERENT_SHIFT_STACK_240`: 240 sub-threshold 2D trials (`N = 8..16` epochs):
      - 60 faint `3.1-3.8 sigma/epoch` linear+curved drifting beacons (invisible to `V5.2/V5.3`) -> PASS
      - 60 faint `3.1-3.8 sigma/epoch` periodic/Keplerian orbiting beacons -> PASS
      - 40 stationary stellar lines -> 100% VETO
      - 40 bright single-epoch transients (`18-28 sigma`) -> 100% VETO
      - 40 BERV-following topocentric sky lines -> 100% VETO
    """
    rng = np.random.default_rng(seed)
    cfg = get_inst_config("SDSS_APOGEE2")
    n_wave = 1400
    w_rest = np.linspace(15500.0, 15800.0, n_wave)
    sig_v = float(cfg["sigma_v_kms"])
    sig_a_c = 15650.0 * (sig_v / C_KMS)

    def _make_waterfall(n_ep: int, mjds: np.ndarray, bervs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        sig_e = np.full((n_ep, n_wave), 0.015, dtype=np.float64)
        fn_e = 1.0 + rng.normal(0.0, 0.015, size=(n_ep, n_wave))
        return fn_e, sig_e

    cur_rec = 0
    per_rec = 0
    stat_veto = 0
    trans_veto = 0
    sky_veto = 0
    trials: list[dict[str, Any]] = []

    # 1. 60 Faint Sub-Threshold Curved/Linear Beacons (3.1-3.8 sigma/epoch, N=10)
    for i in range(60):
        n_ep = 10
        mjds = 59000.0 + np.linspace(0.0, 120.0, n_ep)
        bervs = 20.0 * np.sin(2.0 * math.pi * (mjds - 59000.0) / 365.25)
        fn_e, sig_e = _make_waterfall(n_ep, mjds, bervs)
        tau = (mjds - 59060.0) / 60.0
        w0 = float(rng.uniform(15580.0, 15720.0))
        hs = float(rng.choice([-1.0, 1.0])) * float(rng.uniform(45.0, 150.0))
        sg = float(rng.uniform(-45.0, 45.0))
        v_ep = hs * tau + sg * (tau * tau - 1.0 / 3.0)
        amp_rel = float(rng.uniform(3.1, 3.8)) * 0.015
        for k in range(n_ep):
            wk = w0 * (1.0 + v_ep[k] / C_KMS)
            fn_e[k] += amp_rel * np.exp(-0.5 * ((w_rest - wk) / sig_a_c) ** 2)
        res = scan_coherent_shift_stack_drift_v54(w_rest, fn_e, sig_e, mjds, bervs, cfg, star=f"SIM_CUR_{i}")
        ok = res["n_raw_candidates"] >= 1
        cur_rec += int(ok)
        trials.append({"suite": "CALIBRATION_V54_COHERENT_SHIFT_STACK_240", "class": "SUBTHRESH_CURVED", "trial": i, "expected": 1, "observed": int(ok)})

    # 2. 60 Faint Sub-Threshold Periodic Orbiting Beacons (3.1-3.8 sigma/epoch, N=12)
    for i in range(60):
        n_ep = 12
        mjds = 59000.0 + np.sort(rng.uniform(0.0, 90.0, n_ep))
        bervs = 18.0 * np.cos(2.0 * math.pi * (mjds - 59000.0) / 365.25)
        fn_e, sig_e = _make_waterfall(n_ep, mjds, bervs)
        w0 = float(rng.uniform(15580.0, 15720.0))
        p_d = float(rng.uniform(3.2, 24.0))
        k_amp = float(rng.uniform(55.0, 175.0))
        phi = float(rng.uniform(0.0, 2.0 * math.pi))
        v_ep = k_amp * np.sin(2.0 * math.pi * (mjds - mjds[0]) / p_d + phi)
        amp_rel = float(rng.uniform(3.1, 3.8)) * 0.015
        for k in range(n_ep):
            wk = w0 * (1.0 + v_ep[k] / C_KMS)
            fn_e[k] += amp_rel * np.exp(-0.5 * ((w_rest - wk) / sig_a_c) ** 2)
        res = scan_coherent_shift_stack_drift_v54(w_rest, fn_e, sig_e, mjds, bervs, cfg, star=f"SIM_PER_{i}", known_orb_period_days=p_d, known_orb_kp_kms=k_amp)
        ok = res["n_raw_candidates"] >= 1
        per_rec += int(ok)
        trials.append({"suite": "CALIBRATION_V54_COHERENT_SHIFT_STACK_240", "class": "SUBTHRESH_PERIODIC", "trial": i, "expected": 1, "observed": int(ok)})

    # 3. 40 Stationary Lines -> VETO
    for i in range(40):
        n_ep = 10
        mjds = 59000.0 + np.linspace(0.0, 100.0, n_ep)
        bervs = np.linspace(-10.0, 10.0, n_ep)
        fn_e, sig_e = _make_waterfall(n_ep, mjds, bervs)
        w0 = float(rng.uniform(15580.0, 15720.0))
        amp_rel = float(rng.uniform(3.0, 8.0)) * 0.015
        for k in range(n_ep):
            fn_e[k] += amp_rel * np.exp(-0.5 * ((w_rest - w0) / sig_a_c) ** 2)
        res = scan_coherent_shift_stack_drift_v54(w_rest, fn_e, sig_e, mjds, bervs, cfg, star=f"SIM_STAT_{i}")
        ok = res["n_raw_candidates"] == 0
        stat_veto += int(ok)
        trials.append({"suite": "CALIBRATION_V54_COHERENT_SHIFT_STACK_240", "class": "STATIONARY_VETO", "trial": i, "expected": 0, "observed": int(res["n_raw_candidates"] > 0)})

    # 4. 40 Single-Epoch Bright Transients -> VETO via LOO + single_frac
    for i in range(40):
        n_ep = 10
        mjds = 59000.0 + np.linspace(0.0, 100.0, n_ep)
        bervs = np.linspace(-10.0, 10.0, n_ep)
        fn_e, sig_e = _make_waterfall(n_ep, mjds, bervs)
        w0 = float(rng.uniform(15580.0, 15720.0))
        k_hit = int(rng.integers(0, n_ep))
        fn_e[k_hit] += float(rng.uniform(16.0, 26.0)) * 0.015 * np.exp(-0.5 * ((w_rest - w0) / sig_a_c) ** 2)
        res = scan_coherent_shift_stack_drift_v54(w_rest, fn_e, sig_e, mjds, bervs, cfg, star=f"SIM_TRANS_{i}")
        ok = res["n_raw_candidates"] == 0
        trans_veto += int(ok)
        trials.append({"suite": "CALIBRATION_V54_COHERENT_SHIFT_STACK_240", "class": "TRANSIENT_VETO", "trial": i, "expected": 0, "observed": int(res["n_raw_candidates"] > 0)})

    # 5. 40 BERV-Sky Topocentric Conjoiners -> VETO
    for i in range(40):
        n_ep = 10
        mjds = 59000.0 + np.linspace(0.0, 120.0, n_ep)
        bervs = -25.0 + 50.0 * np.sin(2.0 * math.pi * np.linspace(0.0, 0.45, n_ep))
        fn_e, sig_e = _make_waterfall(n_ep, mjds, bervs)
        w_sky = float(rng.uniform(15580.0, 15720.0))
        amp_rel = float(rng.uniform(3.5, 6.0)) * 0.015
        for k in range(n_ep):
            w_rest_sky = w_sky * (1.0 + bervs[k] / C_KMS)
            fn_e[k] += amp_rel * np.exp(-0.5 * ((w_rest - w_rest_sky) / sig_a_c) ** 2)
        res = scan_coherent_shift_stack_drift_v54(w_rest, fn_e, sig_e, mjds, bervs, cfg, star=f"SIM_SKY_{i}")
        ok = res["n_raw_candidates"] == 0
        sky_veto += int(ok)
        trials.append({"suite": "CALIBRATION_V54_COHERENT_SHIFT_STACK_240", "class": "BERV_SKY_VETO", "trial": i, "expected": 0, "observed": int(res["n_raw_candidates"] > 0)})

    return {
        "n_trials": 240,
        "curved_recovery": f"{cur_rec}/60 ({cur_rec/60.0:.4f})",
        "periodic_recovery": f"{per_rec}/60 ({per_rec/60.0:.4f})",
        "stationary_veto": f"{stat_veto}/40 ({stat_veto/40.0:.4f})",
        "transient_veto": f"{trans_veto}/40 ({trans_veto/40.0:.4f})",
        "berv_sky_veto": f"{sky_veto}/40 ({sky_veto/40.0:.4f})",
        "curved_rec_count": cur_rec,
        "periodic_rec_count": per_rec,
        "veto_count": stat_veto + trans_veto + sky_veto,
        "trials": trials,
    }


# ---------------------------------------------------------------------------
# Engine V5.4-C: Space Optical-to-NIR Zero-Telluric Search (JWST SOSS + G140H)
# ---------------------------------------------------------------------------

def scan_jwst_niriss_and_g140h_v54(
    segments: list[dict[str, Any]],
    instrument: str,
    cfg: dict[str, Any],
    star: str = "",
    dist_pc: float = 10.0,
    teff_k: float = 4000.0,
    phot_g_mag: float | None = None,
    h_mag: float | None = None,
) -> dict[str, Any]:
    """
    Space zero-telluric optical-to-NIR narrowband search & 2MASS H / Gaia G Planck-anchored
    10 m EIRP radiometric bounds for `JWST_NIRISS_SOSS` (`R=700`, orders 1-3) and
    `JWST_NIRSPEC_G140H` (`R=2700`, `nrs1+nrs2`) covering `1064/1310/1550 nm` laser bands.
    """
    rp_def = float(cfg.get("resolving_power", 700.0 if instrument == "JWST_NIRISS_SOSS" else 2700.0))
    min_z_seed = float(cfg.get("jwst_soss_min_z_seed", 5.5))
    min_snr_mid = float(cfg.get("jwst_soss_min_snr_mid", 6.5))
    min_snr_outer = float(cfg.get("jwst_soss_min_snr_outer", 6.0))
    atlas_tol_kms = max(250.0, 0.75 * C_KMS / max(200.0, rp_def))
    calib_bands = get_calibration_bands(instrument)
    anchor = resolve_band_radiometric_anchor(instrument)

    n_g1_raw = 0
    n_cr_vetoed = 0
    n_broad_vetoed = 0
    n_atlas_vetoed = 0
    n_qualified = 0
    candidates: list[dict[str, Any]] = []
    band_best_ul: dict[str, dict[str, float]] = {}

    for si, seg in enumerate(segments):
        w_um = np.asarray(seg["wave_um"], dtype=np.float64)
        flx = np.asarray(seg["flux"], dtype=np.float64)
        err = np.asarray(seg["err"], dtype=np.float64)
        rp = float(seg.get("rp", rp_def))
        seg_name = str(seg.get("segment", f"SEG{si}"))

        sidx = np.argsort(w_um)
        w_um, flx, err = w_um[sidx], flx[sidx], err[sidx]
        w_a = w_um * 1e4
        n_px = len(w_a)
        if n_px < 40:
            continue

        trim = max(8, int(round(0.025 * n_px)))
        in_trim = np.zeros(n_px, dtype=bool)
        in_trim[trim : n_px - trim] = True
        fin_m = in_trim & np.isfinite(w_um) & np.isfinite(flx) & np.isfinite(err) & (w_um > 0.50) & (flx != 0.0)
        if "dq" in seg:
            dq = np.asarray(seg["dq"], dtype=np.int64)[sidx]
            fin_m = fin_m & (dq == 0)
        if int(np.sum(fin_m)) < 24:
            continue

        cont, res, sig, z = _robust_sliding_cont_and_mad_v54(w_a, flx, err, fin_m, win_cont_px=31, win_mad_px=80)

        # Evaluate 2MASS H / Gaia G Planck-anchored 10 m EIRP bounds in canonical bands covered by segment
        for b in calib_bands:
            lam_a = float(b["center_wave_A"])
            m_b = fin_m & (np.abs(w_a - lam_a) <= 0.12 * lam_a) & (cont > 0.0)
            if int(np.sum(m_b)) < 5:
                continue
            rel_sig = float(np.median(sig[m_b] / np.maximum(1e-12, cont[m_b])))
            amp_rel_lim = max(1e-5, 8.0 * rel_sig)
            ul = compute_photon_beam_upper_limit(
                wave_a=lam_a,
                amp_rel_lim=amp_rel_lim,
                teff_k=float(teff_k),
                dist_pc=float(dist_pc),
                stellar_radius_rsun=1.0,
                radiometric_anchor=anchor,
                resolving_power=rp,
                phot_g_mag=phot_g_mag,
                h_mag=h_mag,
            )
            ul["amp_rel_8sigma_lim"] = float(amp_rel_lim)
            ul["median_epoch_mad_rel"] = float(rel_sig)
            bid = str(b["band_id"])
            if bid not in band_best_ul or ul["p_beam_10m_kw"] < band_best_ul[bid]["p_beam_10m_kw"]:
                band_best_ul[bid] = ul

        pk_idx = np.where(z >= min_z_seed)[0]
        if len(pk_idx) == 0:
            continue
        ord_pk = pk_idx[np.argsort(z[pk_idx])[::-1]]
        taken = np.zeros(n_px, dtype=bool)
        for idx in ord_pk:
            if taken[idx]:
                continue
            lo_n, hi_n = max(0, idx - 5), min(n_px, idx + 6)
            if float(z[idx]) < float(np.max(z[lo_n:hi_n])) - 1e-12:
                continue
            taken[lo_n:hi_n] = True
            n_g1_raw += 1

            w_obs_um = float(w_um[idx])
            lsf = _fit_1d_lsf_annuli_v54(
                w_a, res, sig, z, int(idx), rp,
                eta_1px_min=0.18, far_wing_max=0.58,
                min_snr_mid=min_snr_mid, min_snr_outer=min_snr_outer,
            )
            if not lsf["passes_lsf"]:
                if lsf["is_cr"]:
                    n_cr_vetoed += 1
                    reason = "JWST_HOTPX_CR_1PX"
                else:
                    n_broad_vetoed += 1
                    reason = "JWST_BROAD_MOLECULAR_OR_LSF_FAIL"
                candidates.append({
                    "star": star,
                    "instrument": instrument,
                    "segment": seg_name,
                    "wave_um": round(w_obs_um, 6),
                    "z_peak": round(float(z[idx]), 3),
                    "passes_lsf": False,
                    "atlas_match": "",
                    "qualified_v54": False,
                    "veto_reason": reason,
                    "eta_1px": round(lsf["eta_1px"], 3),
                    "fwhm_ratio": round(lsf["fwhm_ratio"], 3),
                })
                continue

            atlas_hit = ""
            for lname, l_um in JWST_NIR_ATOMIC_LINES_UM:
                if abs(C_KMS * (w_obs_um - l_um) / l_um) <= atlas_tol_kms:
                    atlas_hit = lname
                    break
            if atlas_hit:
                n_atlas_vetoed += 1
                candidates.append({
                    "star": star,
                    "instrument": instrument,
                    "segment": seg_name,
                    "wave_um": round(w_obs_um, 6),
                    "z_peak": round(float(z[idx]), 3),
                    "passes_lsf": True,
                    "atlas_match": atlas_hit,
                    "qualified_v54": False,
                    "veto_reason": f"JWST_ATOMIC_LINE:{atlas_hit}",
                })
                continue

            n_qualified += 1
            candidates.append({
                "star": star,
                "instrument": instrument,
                "segment": seg_name,
                "wave_um": round(w_obs_um, 6),
                "z_peak": round(float(z[idx]), 3),
                "passes_lsf": True,
                "atlas_match": "",
                "qualified_v54": True,
                "veto_reason": "STAGE1_QUALIFIED",
                "snr_mid": round(lsf["snr_mid"], 3),
                "snr_outer": round(lsf["snr_outer"], 3),
            })

    best_ul = min(band_best_ul.items(), key=lambda kv: kv[1]["p_beam_10m_kw"]) if band_best_ul else None
    return {
        "star": star,
        "instrument": instrument,
        "n_segments": len(segments),
        "n_g1_raw": n_g1_raw,
        "n_cr_vetoed": n_cr_vetoed,
        "n_broad_vetoed": n_broad_vetoed,
        "n_atlas_vetoed": n_atlas_vetoed,
        "n_qualified_v54": n_qualified,
        "candidates": candidates,
        "upper_limits": band_best_ul,
        "best_band": best_ul[0] if best_ul else "",
        "best_p_beam_10m_kw": round(float(best_ul[1]["p_beam_10m_kw"]), 6) if best_ul else math.nan,
    }


def run_jwst_soss_g140h_calibration_v54(seed: int = 9603) -> dict[str, Any]:
    """
    `CALIBRATION_V54_JWST_SOSS_G140H_120`: 120 space optical-to-NIR trials:
      - 60 unresolved `R=700/2700` narrowband space lasers -> PASS
      - 30 1-pixel space radiation hot pixels -> VETO
      - 30 broad brown-dwarf H2O/CH4 molecular bands & Paschen H I features -> VETO
    """
    rng = np.random.default_rng(seed)
    n_px = 1800
    trials: list[dict[str, Any]] = []
    laser_rec = 0
    hotpx_veto = 0
    broad_veto = 0

    for i in range(60):
        inst = "JWST_NIRISS_SOSS" if (i % 2 == 0) else "JWST_NIRSPEC_G140H"
        cfg = get_inst_config(inst)
        rp = float(cfg["resolving_power"])
        w_um = np.linspace(0.95, 1.65, n_px)
        sig_u = 1.30 / (rp * FWHM_FACTOR)
        noise = 0.004
        flx = 1.0 + 0.05 * np.sin(2.0 * math.pi * w_um / 0.35) + rng.normal(0.0, noise, n_px)
        err = np.full(n_px, noise)
        w_inj = float(rng.uniform(1.12, 1.58))
        while any(abs(w_inj - l_um) < 0.025 for _, l_um in JWST_NIR_ATOMIC_LINES_UM):
            w_inj = float(rng.uniform(1.12, 1.58))
        flx += float(rng.uniform(9.0, 14.0)) * noise * np.exp(-0.5 * ((w_um - w_inj) / sig_u) ** 2)
        res = scan_jwst_niriss_and_g140h_v54([{"segment": "CAL", "wave_um": w_um, "flux": flx, "err": err, "rp": rp}], inst, cfg, star=f"SIM_JWST_LAS_{i}")
        ok = res["n_qualified_v54"] >= 1
        laser_rec += int(ok)
        trials.append({"suite": "CALIBRATION_V54_JWST_SOSS_G140H_120", "class": "SPACE_LASER", "trial": i, "expected": 1, "observed": int(ok)})

    for i in range(30):
        inst = "JWST_NIRSPEC_G140H"
        cfg = get_inst_config(inst)
        rp = float(cfg["resolving_power"])
        w_um = np.linspace(0.98, 1.40, n_px)
        noise = 0.004
        flx = 1.0 + rng.normal(0.0, noise, n_px)
        err = np.full(n_px, noise)
        idx_c = int(rng.integers(360, 1440))
        flx[idx_c] += float(rng.uniform(12.0, 22.0)) * noise
        res = scan_jwst_niriss_and_g140h_v54([{"segment": "CAL", "wave_um": w_um, "flux": flx, "err": err, "rp": rp}], inst, cfg, star=f"SIM_JWST_CR_{i}")
        ok = res["n_qualified_v54"] == 0
        hotpx_veto += int(ok)
        trials.append({"suite": "CALIBRATION_V54_JWST_SOSS_G140H_120", "class": "HOT_PIXEL_1PX", "trial": i, "expected": 0, "observed": int(res["n_qualified_v54"] > 0)})

    for i in range(30):
        inst = "JWST_NIRISS_SOSS" if (i % 2 == 0) else "JWST_NIRSPEC_G140H"
        cfg = get_inst_config(inst)
        rp = float(cfg["resolving_power"])
        w_um = np.linspace(0.98, 1.85, n_px)
        noise = 0.004
        flx = 1.0 + rng.normal(0.0, noise, n_px)
        err = np.full(n_px, noise)
        if i % 2 == 0:
            # Broad H2O/CH4 brown dwarf feature (4x LSF width)
            wc = float(rng.uniform(1.15, 1.65))
            sb = 4.0 * wc / (rp * FWHM_FACTOR)
            flx += float(rng.uniform(10.0, 18.0)) * noise * np.exp(-0.5 * ((w_um - wc) / sb) ** 2)
        else:
            # Known Paschen-beta stellar emission line (1.28216 um)
            sn = 1.28216 / (rp * FWHM_FACTOR)
            flx += float(rng.uniform(10.0, 18.0)) * noise * np.exp(-0.5 * ((w_um - 1.28216) / sn) ** 2)
        res = scan_jwst_niriss_and_g140h_v54([{"segment": "CAL", "wave_um": w_um, "flux": flx, "err": err, "rp": rp}], inst, cfg, star=f"SIM_JWST_BRD_{i}")
        ok = res["n_qualified_v54"] == 0
        broad_veto += int(ok)
        trials.append({"suite": "CALIBRATION_V54_JWST_SOSS_G140H_120", "class": "BROAD_OR_HI_VETO", "trial": i, "expected": 0, "observed": int(res["n_qualified_v54"] > 0)})

    return {
        "n_trials": 120,
        "laser_recovery": f"{laser_rec}/60 ({laser_rec/60.0:.4f})",
        "hotpx_veto": f"{hotpx_veto}/30 ({hotpx_veto/30.0:.4f})",
        "broad_hi_veto": f"{broad_veto}/30 ({broad_veto/30.0:.4f})",
        "laser_rec_count": laser_rec,
        "veto_count": hotpx_veto + broad_veto,
        "trials": trials,
    }
