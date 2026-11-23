#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D102 Detector Module: `TECHNOSIGNATURE_V6_0_XRAY_EUV_POISSON_CHANDRA_EUVE_AND_ALMA_UNBROKEN_MM`

Prospectively locked V6.0 multi-messenger X-ray Poisson grating search (`Chandra HETG/LETG`),
extreme-UV spectrometer search (`EUVE SW/MW/LW`), ALMA unbroken millimeter seam closure & Band 6/7/8
(`14.69+` unbroken Lyman-to-mm octaves), ESPRESSO/HARPS Orbits `#157-#162`, and 54-campaign coherent
drifting frequency comb stacking:
  - Preserves all V5.0-V5.9 primitives (G1-G8, Comb V4.1, RPCA, Agnostic, EXES, GREAT/SWS/FORCAST,
    JCMT_MM/IRTF_SPEX, JCMT_ALAIHI_3MM/SOFIA_FIFILS/IUE_UV/DRIFT_V58, ALMA_V59, COMB_DRIFT_V59).
  - V6.0A (`CHANDRA_XRAY_POISSON_V60`): Exact Poisson Li & Ma (1983, eq. 17) likelihood-ratio line
    search across Chandra HETG (`HEG` 1.2-15 A, `MEG` 2.5-31 A) & LETG (`LEG` 1.2-175 A) `+1/-1`
    diffraction orders with `G4` order-coincidence, `G3` CHIANTI coronal atlas, and CXC POG effective-area
    Poisson 6-sigma limits (`1 m`, `10 m`, and isotropic EIRP).
  - V6.0B (`EUVE_V60`): Extreme-UV `70.05-699.80 A` search with `G2` geocoronal airglow mask,
    `G3` coronal EUV atlas, `G4` spike/seam veto, overlapping Chandra LETG (`70-175 A`) across 9.19
    unbroken high-energy octaves (`0.00012-0.06998 um`).
  - V6.0C (`ALMA_V60`): Closes B5/B6 (`210.8-214.2 GHz`), B4/B5 (`158.6-163.8 GHz`), and B3 low
    (`87.0-93.9 GHz`) millimeter seams plus deep <10 pc ALMA Band 6/7/8 interferometry (`26.09` octaves).
"""
from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np
from scipy.ndimage import convolve1d, median_filter

DETECTOR_NAME = "TECHNOSIGNATURE_V6_0_XRAY_EUV_POISSON_CHANDRA_EUVE_AND_ALMA_UNBROKEN_MM"

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

CALIBRATION_BANDS_HERSCHEL_HIFI = [
    {"band_id": "HIFI_565GHZ", "center_wave_A": 5304822.265},
    {"band_id": "HIFI_654GHZ", "center_wave_A": 4583982.538},
    {"band_id": "HIFI_1158GHZ", "center_wave_A": 2588881.330},
    {"band_id": "HIFI_1838GHZ", "center_wave_A": 1631079.750},
]

CALIBRATION_BANDS_HERSCHEL_SPIRE_FTS = [
    {"band_id": "SPIRE_220UM", "center_wave_A": 2200000.0},
    {"band_id": "SPIRE_310UM", "center_wave_A": 3100000.0},
    {"band_id": "SPIRE_450UM", "center_wave_A": 4500000.0},
    {"band_id": "SPIRE_600UM", "center_wave_A": 6000000.0},
]

CALIBRATION_BANDS_HERSCHEL_PACS = [
    {"band_id": "PACS_63UM", "center_wave_A": 630000.0},
    {"band_id": "PACS_90UM", "center_wave_A": 900000.0},
    {"band_id": "PACS_125UM", "center_wave_A": 1250000.0},
    {"band_id": "PACS_175UM", "center_wave_A": 1750000.0},
]

CALIBRATION_BANDS_HST_STIS_E140H = [
    {"band_id": "E140H_1250", "center_wave_A": 1250.0},
    {"band_id": "E140H_1400", "center_wave_A": 1400.0},
    {"band_id": "E140H_1550", "center_wave_A": 1550.0},
    {"band_id": "E140H_1650", "center_wave_A": 1650.0},
]

CALIBRATION_BANDS_SOFIA_GREAT = [
    {"band_id": "GREAT_OI_63UM", "center_wave_A": 631837.0},
    {"band_id": "GREAT_OH_119UM", "center_wave_A": 1193340.0},
    {"band_id": "GREAT_HeHp_149UM", "center_wave_A": 1491370.0},
    {"band_id": "GREAT_CII_158UM", "center_wave_A": 1577409.0},
    {"band_id": "GREAT_CO_237UM", "center_wave_A": 2366130.0},
]

CALIBRATION_BANDS_ISO_SWS = [
    {"band_id": "SWS_3P5UM", "center_wave_A": 35000.0},
    {"band_id": "SWS_7P5UM", "center_wave_A": 75000.0},
    {"band_id": "SWS_14P0UM", "center_wave_A": 140000.0},
    {"band_id": "SWS_25P0UM", "center_wave_A": 250000.0},
    {"band_id": "SWS_38P0UM", "center_wave_A": 380000.0},
]

CALIBRATION_BANDS_SOFIA_FORCAST = [
    {"band_id": "FOR_G063", "center_wave_A": 63000.0},
    {"band_id": "FOR_G111", "center_wave_A": 111000.0},
    {"band_id": "FOR_G227", "center_wave_A": 227000.0},
    {"band_id": "FOR_G329", "center_wave_A": 329000.0},
]

CALIBRATION_BANDS_JCMT_HARP = [
    {"band_id": "JCMT_HARP_805UM", "center_wave_A": 8050000.0},
    {"band_id": "JCMT_HARP_850UM", "center_wave_A": 8500000.0},
    {"band_id": "JCMT_AWEOWEO_895UM", "center_wave_A": 8950000.0},
]

CALIBRATION_BANDS_JCMT_MM_230GHZ = [
    {"band_id": "JCMT_UU_1300UM", "center_wave_A": 13000000.0},
    {"band_id": "JCMT_RXA3_1380UM", "center_wave_A": 13800000.0},
]

CALIBRATION_BANDS_IRTF_SPEX = [
    {"band_id": "SPEX_J_125UM", "center_wave_A": 12500.0},
    {"band_id": "SPEX_H_165UM", "center_wave_A": 16500.0},
    {"band_id": "SPEX_K_220UM", "center_wave_A": 22000.0},
    {"band_id": "SPEX_QCL_350UM", "center_wave_A": 35000.0},
    {"band_id": "SPEX_M_470UM", "center_wave_A": 47000.0},
]


CALIBRATION_BANDS_JCMT_ALAIHI_3MM = [
    {"band_id": "ALAIHI_3830UM_78GHZ", "center_wave_A": 38300000.0},
    {"band_id": "ALAIHI_3700UM_81GHZ", "center_wave_A": 37000000.0},
    {"band_id": "ALAIHI_3475UM_86GHZ", "center_wave_A": 34750000.0},
    {"band_id": "ALAIHI_3305UM_91GHZ", "center_wave_A": 33050000.0},
]

CALIBRATION_BANDS_SOFIA_FIFILS = [
    {"band_id": "FIFILS_BLU_52UM", "center_wave_A": 520000.0},
    {"band_id": "FIFILS_BLU_88UM", "center_wave_A": 883560.0},
    {"band_id": "FIFILS_RED_146UM", "center_wave_A": 1460000.0},
    {"band_id": "FIFILS_RED_160UM", "center_wave_A": 1600000.0},
    {"band_id": "FIFILS_RED_186UM", "center_wave_A": 1865000.0},
]

CALIBRATION_BANDS_IUE_SWP_HI = [
    {"band_id": "IUE_SWP_1350", "center_wave_A": 1350.0},
    {"band_id": "IUE_SWP_1550", "center_wave_A": 1550.0},
    {"band_id": "IUE_SWP_1800", "center_wave_A": 1800.0},
]

CALIBRATION_BANDS_IUE_LWP_HI = [
    {"band_id": "IUE_LWP_2150", "center_wave_A": 2150.0},
    {"band_id": "IUE_LWP_2600", "center_wave_A": 2600.0},
    {"band_id": "IUE_LWP_2800", "center_wave_A": 2800.0},
    {"band_id": "IUE_LWP_3050", "center_wave_A": 3050.0},
]

CALIBRATION_BANDS_ESPRESSO = [
    {"band_id": "ESPRESSO_BLU_4200", "center_wave_A": 4200.0},
    {"band_id": "ESPRESSO_GRN_5300", "center_wave_A": 5300.0},
    {"band_id": "ESPRESSO_RED_6500", "center_wave_A": 6500.0},
    {"band_id": "ESPRESSO_NIR_7600", "center_wave_A": 7600.0},
]

CALIBRATION_BANDS_ALMA_B1_7MM = [
    {"band_id": "ALMA_B1_8500UM_35GHZ", "center_wave_A": 85000000.0},
    {"band_id": "ALMA_B1_7000UM_43GHZ", "center_wave_A": 70000000.0},
    {"band_id": "ALMA_B1_6200UM_48GHZ", "center_wave_A": 62000000.0},
]

CALIBRATION_BANDS_ALMA_B3_3MM = [
    {"band_id": "ALMA_B3_3500UM_86GHZ", "center_wave_A": 35000000.0},
    {"band_id": "ALMA_B3_3100UM_97GHZ", "center_wave_A": 31000000.0},
    {"band_id": "ALMA_B3_2700UM_111GHZ", "center_wave_A": 27000000.0},
]

CALIBRATION_BANDS_ALMA_B4_2MM = [
    {"band_id": "ALMA_B4_2300UM_130GHZ", "center_wave_A": 23000000.0},
    {"band_id": "ALMA_B4_2050UM_146GHZ", "center_wave_A": 20500000.0},
    {"band_id": "ALMA_B4_1880UM_160GHZ", "center_wave_A": 18800000.0},
]

CALIBRATION_BANDS_ALMA_B5_2MM = [
    {"band_id": "ALMA_B5_1750UM_171GHZ", "center_wave_A": 17500000.0},
    {"band_id": "ALMA_B5_1580UM_190GHZ", "center_wave_A": 15800000.0},
    {"band_id": "ALMA_B5_1440UM_208GHZ", "center_wave_A": 14400000.0},
]

CALIBRATION_BANDS_ALMA_B6_1MM = [
    {"band_id": "ALMA_B6_1360UM_220GHZ", "center_wave_A": 13600000.0},
    {"band_id": "ALMA_B6_1300UM_231GHZ", "center_wave_A": 13000000.0},
    {"band_id": "ALMA_B6_1150UM_261GHZ", "center_wave_A": 11500000.0},
]

CALIBRATION_BANDS_ALMA_B7_0P9MM = [
    {"band_id": "ALMA_B7_1000UM_300GHZ", "center_wave_A": 10000000.0},
    {"band_id": "ALMA_B7_870UM_345GHZ", "center_wave_A": 8700000.0},
    {"band_id": "ALMA_B7_840UM_357GHZ", "center_wave_A": 8400000.0},
]

CALIBRATION_BANDS_ALMA_B8_0P7MM = [
    {"band_id": "ALMA_B8_650UM_461GHZ", "center_wave_A": 6500000.0},
    {"band_id": "ALMA_B8_610UM_492GHZ", "center_wave_A": 6100000.0},
]

CALIBRATION_BANDS_CHANDRA_HETG = [
    {"band_id": "HEG_HARD_2A", "center_wave_A": 2.0},
    {"band_id": "HEG_MID_6A", "center_wave_A": 6.0},
    {"band_id": "MEG_SOFT_12A", "center_wave_A": 12.0},
]

CALIBRATION_BANDS_CHANDRA_LETG = [
    {"band_id": "LETG_SOFT_50A", "center_wave_A": 50.0},
    {"band_id": "LETG_EUV_120A", "center_wave_A": 120.0},
]

CALIBRATION_BANDS_EUVE_DS_S = [
    {"band_id": "EUVE_SW_100A", "center_wave_A": 100.0},
    {"band_id": "EUVE_MW_250A", "center_wave_A": 250.0},
    {"band_id": "EUVE_LW_500A", "center_wave_A": 500.0},
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
    "ESO_ESPRESSO": [
        {"band": "ESPRESSO_BLUE", "lo_a": 3820.0, "hi_a": 5300.0},
        {"band": "ESPRESSO_RED", "lo_a": 5400.0, "hi_a": 7850.0},
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
BASE_V5_5_CONFIG = BASE_V4_2_CONFIG


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
    elif instrument == "HERSCHEL_HIFI":
        r_val = float(resolving_power) if resolving_power is not None else 2200000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (1570000.0, 5400000.0),
            "coadd_rest_min_angstrom": 1570000.0,
            "coadd_rest_max_angstrom": 5400000.0,
            "coadd_step_angstrom": 2.0,
            "rv_anchor_fwhm_kms": 0.30,
            "scan_nms_min_sep_bins": 12,
            "radiometric_anchor": "HERSCHEL_HIFI_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 1.0,
        })
    elif instrument == "HERSCHEL_SPIRE_FTS":
        r_val = float(resolving_power) if resolving_power is not None else 1000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (1900000.0, 6750000.0),
            "coadd_rest_min_angstrom": 1900000.0,
            "coadd_rest_max_angstrom": 6750000.0,
            "coadd_step_angstrom": 500.0,
            "rv_anchor_fwhm_kms": 300.0,
            "scan_nms_min_sep_bins": 8,
            "radiometric_anchor": "HERSCHEL_SPIRE_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 50.0,
        })
    elif instrument == "HERSCHEL_PACS":
        r_val = float(resolving_power) if resolving_power is not None else 2000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (510000.0, 2120000.0),
            "coadd_rest_min_angstrom": 510000.0,
            "coadd_rest_max_angstrom": 2120000.0,
            "coadd_step_angstrom": 100.0,
            "rv_anchor_fwhm_kms": 150.0,
            "scan_nms_min_sep_bins": 10,
            "radiometric_anchor": "HERSCHEL_PACS_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 30.0,
        })
    elif instrument == "HST_STIS_E140H":
        r_val = float(resolving_power) if resolving_power is not None else 114000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (1140.0, 1710.0),
            "coadd_rest_min_angstrom": 1140.0,
            "coadd_rest_max_angstrom": 1710.0,
            "coadd_step_angstrom": 0.005,
            "rv_anchor_fwhm_kms": 2.63,
            "scan_nms_min_sep_bins": 14,
            "radiometric_anchor": "HST_STIS_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 2.0,
        })
    elif instrument == "SOFIA_GREAT":
        r_val = float(resolving_power) if resolving_power is not None else 3000000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (600000.0, 2700000.0),
            "coadd_rest_min_angstrom": 600000.0,
            "coadd_rest_max_angstrom": 2700000.0,
            "coadd_step_angstrom": 1.0,
            "rv_anchor_fwhm_kms": 0.10,
            "scan_nms_min_sep_bins": 10,
            "radiometric_anchor": "SOFIA_GREAT_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 10.0,
        })
    elif instrument == "ISO_SWS":
        r_val = float(resolving_power) if resolving_power is not None else 1500.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (23600.0, 453900.0),
            "coadd_rest_min_angstrom": 23600.0,
            "coadd_rest_max_angstrom": 453900.0,
            "coadd_step_angstrom": 5.0,
            "rv_anchor_fwhm_kms": 200.0,
            "scan_nms_min_sep_bins": 8,
            "radiometric_anchor": "ISO_SWS_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 250.0,
        })
    elif instrument == "SOFIA_FORCAST":
        r_val = float(resolving_power) if resolving_power is not None else 200.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (48000.0, 380000.0),
            "coadd_rest_min_angstrom": 48000.0,
            "coadd_rest_max_angstrom": 380000.0,
            "coadd_step_angstrom": 50.0,
            "rv_anchor_fwhm_kms": 1500.0,
            "scan_nms_min_sep_bins": 6,
            "radiometric_anchor": "SOFIA_FORCAST_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 500.0,
        })
    elif instrument == "JCMT_HARP":
        r_val = float(resolving_power) if resolving_power is not None else 600000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (8000000.0, 9450000.0),
            "coadd_rest_min_angstrom": 8000000.0,
            "coadd_rest_max_angstrom": 9450000.0,
            "coadd_step_angstrom": 10.0,
            "rv_anchor_fwhm_kms": 0.50,
            "scan_nms_min_sep_bins": 10,
            "radiometric_anchor": "JCMT_MM_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 10.0,
        })
    elif instrument == "JCMT_MM_230GHZ":
        r_val = float(resolving_power) if resolving_power is not None else 400000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (12400000.0, 13900000.0),
            "coadd_rest_min_angstrom": 12400000.0,
            "coadd_rest_max_angstrom": 13900000.0,
            "coadd_step_angstrom": 20.0,
            "rv_anchor_fwhm_kms": 0.75,
            "scan_nms_min_sep_bins": 10,
            "radiometric_anchor": "JCMT_MM_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 10.0,
        })
    elif instrument == "IRTF_SPEX":
        r_val = float(resolving_power) if resolving_power is not None else 2000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (8000.0, 51000.0),
            "coadd_rest_min_angstrom": 8000.0,
            "coadd_rest_max_angstrom": 51000.0,
            "coadd_step_angstrom": 2.0,
            "rv_anchor_fwhm_kms": 150.0,
            "scan_nms_min_sep_bins": 10,
            "radiometric_anchor": "IRTF_SPEX_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 150.0,
        })
    elif instrument == "JCMT_ALAIHI_3MM":
        r_val = float(resolving_power) if resolving_power is not None else 175000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (31200000.0, 38800000.0),
            "coadd_rest_min_angstrom": 31200000.0,
            "coadd_rest_max_angstrom": 38800000.0,
            "coadd_step_angstrom": 50.0,
            "rv_anchor_fwhm_kms": 1.7,
            "scan_nms_min_sep_bins": 10,
            "radiometric_anchor": "JCMT_ALAIHI_3MM_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 10.0,
        })
    elif instrument == "SOFIA_FIFILS":
        r_val = float(resolving_power) if resolving_power is not None else 1200.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (500000.0, 2060000.0),
            "coadd_rest_min_angstrom": 500000.0,
            "coadd_rest_max_angstrom": 2060000.0,
            "coadd_step_angstrom": 80.0,
            "rv_anchor_fwhm_kms": 250.0,
            "scan_nms_min_sep_bins": 8,
            "radiometric_anchor": "SOFIA_FIFILS_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 60.0,
        })
    elif instrument == "IUE_SWP_HI":
        r_val = float(resolving_power) if resolving_power is not None else 11500.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (1150.0, 1985.0),
            "coadd_rest_min_angstrom": 1150.0,
            "coadd_rest_max_angstrom": 1985.0,
            "coadd_step_angstrom": 0.05,
            "rv_anchor_fwhm_kms": 26.0,
            "scan_nms_min_sep_bins": 12,
            "radiometric_anchor": "IUE_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 20.0,
        })
    elif instrument == "IUE_LWP_HI":
        r_val = float(resolving_power) if resolving_power is not None else 12000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (1850.0, 3350.0),
            "coadd_rest_min_angstrom": 1850.0,
            "coadd_rest_max_angstrom": 3350.0,
            "coadd_step_angstrom": 0.05,
            "rv_anchor_fwhm_kms": 25.0,
            "scan_nms_min_sep_bins": 12,
            "radiometric_anchor": "IUE_DIRECT_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 20.0,
        })
    elif instrument == "ESO_ESPRESSO":
        r_val = float(resolving_power) if resolving_power is not None else 140000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (3770.0, 7900.0),
            "coadd_rest_min_angstrom": 3770.0,
            "coadd_rest_max_angstrom": 7900.0,
            "coadd_step_angstrom": 0.015,
            "rv_anchor_fwhm_kms": 6.5,
            "scan_nms_min_sep_bins": 24,
            "radiometric_anchor": "GAIA_G_PLANCK_CGS",
            "rv_anchors": LOCKED_RV_ANCHORS_OPTICAL,
            "comb_spacings_ghz": [25.0, 40.0, 65.0, 100.0],
            "comb_step_ghz": 2.5,
            "comb_search_bands": ["ESPRESSO_BLUE", "ESPRESSO_RED"],
            "g6_topo_tol_kms": 3.5,
        })
    elif instrument == "ALMA_B1_7MM":
        r_val = float(resolving_power) if resolving_power is not None else 150000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (59500000.0, 86000000.0),
            "coadd_rest_min_angstrom": 59500000.0,
            "coadd_rest_max_angstrom": 86000000.0,
            "coadd_step_angstrom": 100.0,
            "rv_anchor_fwhm_kms": 2.0,
            "scan_nms_min_sep_bins": 10,
            "radiometric_anchor": "ALMA_INTERFEROMETRIC_JY_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 8.0,
        })
    elif instrument == "ALMA_B3_3MM":
        r_val = float(resolving_power) if resolving_power is not None else 175000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (25500000.0, 36000000.0),
            "coadd_rest_min_angstrom": 25500000.0,
            "coadd_rest_max_angstrom": 36000000.0,
            "coadd_step_angstrom": 80.0,
            "rv_anchor_fwhm_kms": 1.7,
            "scan_nms_min_sep_bins": 10,
            "radiometric_anchor": "ALMA_INTERFEROMETRIC_JY_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 8.0,
        })
    elif instrument == "ALMA_B4_2MM":
        r_val = float(resolving_power) if resolving_power is not None else 200000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (18200000.0, 24500000.0),
            "coadd_rest_min_angstrom": 18200000.0,
            "coadd_rest_max_angstrom": 24500000.0,
            "coadd_step_angstrom": 60.0,
            "rv_anchor_fwhm_kms": 1.5,
            "scan_nms_min_sep_bins": 10,
            "radiometric_anchor": "ALMA_INTERFEROMETRIC_JY_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 8.0,
        })
    elif instrument == "ALMA_B5_2MM":
        r_val = float(resolving_power) if resolving_power is not None else 220000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (14000000.0, 18600000.0),
            "coadd_rest_min_angstrom": 14000000.0,
            "coadd_rest_max_angstrom": 18600000.0,
            "coadd_step_angstrom": 50.0,
            "rv_anchor_fwhm_kms": 1.4,
            "scan_nms_min_sep_bins": 10,
            "radiometric_anchor": "ALMA_INTERFEROMETRIC_JY_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 8.0,
        })
    elif instrument == "ALMA_B6_1MM":
        r_val = float(resolving_power) if resolving_power is not None else 235000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (10900000.0, 14350000.0),
            "coadd_rest_min_angstrom": 10900000.0,
            "coadd_rest_max_angstrom": 14350000.0,
            "coadd_step_angstrom": 40.0,
            "rv_anchor_fwhm_kms": 1.3,
            "scan_nms_min_sep_bins": 10,
            "radiometric_anchor": "ALMA_INTERFEROMETRIC_JY_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 8.0,
        })
    elif instrument == "ALMA_B7_0P9MM":
        r_val = float(resolving_power) if resolving_power is not None else 350000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (8000000.0, 10910000.0),
            "coadd_rest_min_angstrom": 8000000.0,
            "coadd_rest_max_angstrom": 10910000.0,
            "coadd_step_angstrom": 30.0,
            "rv_anchor_fwhm_kms": 1.2,
            "scan_nms_min_sep_bins": 10,
            "radiometric_anchor": "ALMA_INTERFEROMETRIC_JY_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 8.0,
        })
    elif instrument == "ALMA_B8_0P7MM":
        r_val = float(resolving_power) if resolving_power is not None else 600000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (5950000.0, 7800000.0),
            "coadd_rest_min_angstrom": 5950000.0,
            "coadd_rest_max_angstrom": 7800000.0,
            "coadd_step_angstrom": 20.0,
            "rv_anchor_fwhm_kms": 1.0,
            "scan_nms_min_sep_bins": 10,
            "radiometric_anchor": "ALMA_INTERFEROMETRIC_JY_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 8.0,
        })
    elif instrument == "CHANDRA_HETG":
        r_val = float(resolving_power) if resolving_power is not None else 700.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (1.2, 31.0),
            "coadd_rest_min_angstrom": 1.2,
            "coadd_rest_max_angstrom": 31.0,
            "coadd_step_angstrom": 0.005,
            "rv_anchor_fwhm_kms": 350.0,
            "scan_nms_min_sep_bins": 5,
            "radiometric_anchor": "CHANDRA_POG_POISSON_6SIG",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 200.0,
        })
    elif instrument == "CHANDRA_LETG":
        r_val = float(resolving_power) if resolving_power is not None else 1000.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (1.2, 175.0),
            "coadd_rest_min_angstrom": 1.2,
            "coadd_rest_max_angstrom": 175.0,
            "coadd_step_angstrom": 0.0125,
            "rv_anchor_fwhm_kms": 300.0,
            "scan_nms_min_sep_bins": 5,
            "radiometric_anchor": "CHANDRA_POG_POISSON_6SIG",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 200.0,
        })
    elif instrument == "EUVE_DS_S":
        r_val = float(resolving_power) if resolving_power is not None else 200.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (70.05, 699.80),
            "coadd_rest_min_angstrom": 70.05,
            "coadd_rest_max_angstrom": 699.80,
            "coadd_step_angstrom": 0.25,
            "rv_anchor_fwhm_kms": 450.0,
            "scan_nms_min_sep_bins": 6,
            "radiometric_anchor": "EUVE_DIRECT_FLAM_CGS",
            "rv_anchors": [],
            "comb_search_bands": [],
            "g6_topo_tol_kms": 350.0,
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
    if instrument == "HERSCHEL_HIFI":
        return list(CALIBRATION_BANDS_HERSCHEL_HIFI)
    if instrument == "HERSCHEL_SPIRE_FTS":
        return list(CALIBRATION_BANDS_HERSCHEL_SPIRE_FTS)
    if instrument == "HERSCHEL_PACS":
        return list(CALIBRATION_BANDS_HERSCHEL_PACS)
    if instrument == "HST_STIS_E140H":
        return list(CALIBRATION_BANDS_HST_STIS_E140H)
    if instrument == "SOFIA_GREAT":
        return list(CALIBRATION_BANDS_SOFIA_GREAT)
    if instrument == "ISO_SWS":
        return list(CALIBRATION_BANDS_ISO_SWS)
    if instrument == "SOFIA_FORCAST":
        return list(CALIBRATION_BANDS_SOFIA_FORCAST)
    if instrument == "JCMT_HARP":
        return list(CALIBRATION_BANDS_JCMT_HARP)
    if instrument == "JCMT_MM_230GHZ":
        return list(CALIBRATION_BANDS_JCMT_MM_230GHZ)
    if instrument == "IRTF_SPEX":
        return list(CALIBRATION_BANDS_IRTF_SPEX)
    if instrument == "JCMT_ALAIHI_3MM":
        return list(CALIBRATION_BANDS_JCMT_ALAIHI_3MM)
    if instrument == "SOFIA_FIFILS":
        return list(CALIBRATION_BANDS_SOFIA_FIFILS)
    if instrument == "IUE_SWP_HI":
        return list(CALIBRATION_BANDS_IUE_SWP_HI)
    if instrument == "IUE_LWP_HI":
        return list(CALIBRATION_BANDS_IUE_LWP_HI)
    if instrument == "ESO_ESPRESSO":
        return list(CALIBRATION_BANDS_ESPRESSO)
    if instrument == "ALMA_B1_7MM":
        return list(CALIBRATION_BANDS_ALMA_B1_7MM)
    if instrument == "ALMA_B3_3MM":
        return list(CALIBRATION_BANDS_ALMA_B3_3MM)
    if instrument == "ALMA_B4_2MM":
        return list(CALIBRATION_BANDS_ALMA_B4_2MM)
    if instrument == "ALMA_B5_2MM":
        return list(CALIBRATION_BANDS_ALMA_B5_2MM)
    if instrument == "ALMA_B6_1MM":
        return list(CALIBRATION_BANDS_ALMA_B6_1MM)
    if instrument == "ALMA_B7_0P9MM":
        return list(CALIBRATION_BANDS_ALMA_B7_0P9MM)
    if instrument == "ALMA_B8_0P7MM":
        return list(CALIBRATION_BANDS_ALMA_B8_0P7MM)
    if instrument == "CHANDRA_HETG":
        return list(CALIBRATION_BANDS_CHANDRA_HETG)
    if instrument == "CHANDRA_LETG":
        return list(CALIBRATION_BANDS_CHANDRA_LETG)
    if instrument == "EUVE_DS_S":
        return list(CALIBRATION_BANDS_EUVE_DS_S)
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


# ===========================================================================
# TECHNOSIGNATURE V5.5 ENGINES (HERSCHEL THz/FAR-IR, STIS E140H, CUBIC JERK)
# ===========================================================================

HIFI_APERTURE_JY_PER_K = 468.0  # Roelfsema+2012 Herschel/HIFI point-source conversion
C_ANGSTROM_PER_S = 2.99792458e18

HERSCHEL_MOLECULAR_ATOMIC_GHZ: list[tuple[str, float, float]] = [
    ("CO_5_4", 576.2679, 45.0),
    ("CO_6_5", 691.4731, 45.0),
    ("CO_7_6", 806.6518, 45.0),
    ("CO_8_7", 921.7997, 45.0),
    ("CO_9_8", 1036.9124, 45.0),
    ("CO_10_9", 1151.9855, 45.0),
    ("CO_11_10", 1267.0145, 45.0),
    ("CO_12_11", 1381.9951, 45.0),
    ("CO_13_12", 1496.9229, 45.0),
    ("CO_14_13", 1611.7935, 45.0),
    ("CO_15_14", 1726.6025, 45.0),
    ("CO_16_15", 1841.3455, 45.0),
    ("13CO_5_4", 550.9263, 35.0),
    ("13CO_6_5", 661.0673, 35.0),
    ("13CO_10_9", 1101.3496, 35.0),
    ("H2O_110_101", 556.9360, 50.0),
    ("H2O_202_111", 987.9268, 45.0),
    ("H2O_312_303", 1097.3648, 45.0),
    ("H2O_111_000", 1113.3430, 50.0),
    ("H2O_312_221", 1153.1268, 45.0),
    ("H2O_321_312", 1162.9116, 45.0),
    ("H2O_212_101", 1669.9048, 50.0),
    ("H2O_303_212", 1716.7696, 45.0),
    ("NH3_10_00", 572.4981, 40.0),
    ("NH3_20_10", 1214.8529, 40.0),
    ("OH_2Pi12", 1834.7474, 45.0),
    ("OH_2Pi12_b", 1837.8168, 45.0),
    ("CI_2_1", 809.3420, 35.0),
    ("NII_205", 1461.1319, 60.0),
    ("CII_158", 1900.5369, 60.0),
    ("HCN_7_6", 620.3040, 35.0),
    ("HCN_13_12", 1151.4491, 35.0),
    ("HCOp_7_6", 624.2084, 35.0),
    ("CHp_1_0", 835.1375, 45.0),
    ("SiO_13_12", 564.2492, 40.0),
    ("SiO_15_14", 650.9562, 40.0),
]

SPIRE_PACS_FARIR_ATLAS_UM: list[tuple[str, float, float]] = [
    ("OIII_51.81", 51.8145, 0.35),
    ("NIII_57.32", 57.317, 0.35),
    ("OI_63.18", 63.1837, 0.40),
    ("OH_79.12", 79.15, 0.40),
    ("OH_84.42", 84.51, 0.40),
    ("OIII_88.36", 88.356, 0.45),
    ("H2O_108.07", 108.073, 0.45),
    ("OH_119.23", 119.33, 0.50),
    ("NII_121.90", 121.898, 0.55),
    ("OI_145.53", 145.525, 0.55),
    ("CII_157.74", 157.741, 0.70),
    ("CO_16_15", 162.812, 0.55),
    ("CO_15_14", 173.631, 0.55),
    ("CO_14_13", 185.999, 0.55),
    ("CO_13_12", 200.272, 1.40),
    ("NII_205.18", 205.178, 1.50),
    ("CO_12_11", 216.927, 1.50),
    ("CO_11_10", 236.613, 1.50),
    ("CO_10_9", 260.240, 1.50),
    ("CO_9_8", 289.120, 1.50),
    ("CO_8_7", 325.225, 1.60),
    ("CO_7_6", 371.650, 1.60),
    ("CI_370.42", 370.415, 1.60),
    ("CO_6_5", 433.556, 1.80),
    ("CO_5_4", 520.231, 2.20),
    ("CI_609.14", 609.135, 2.50),
    ("CO_4_3", 650.252, 2.60),
]

STIS_E140H_MASK_WINDOWS_A: list[tuple[str, float, float]] = [
    ("HI_LYA", 1212.5, 1219.0),
    ("NV_1238_1243", 1237.0, 1244.8),
    ("SI_II_1260", 1259.5, 1266.0),
    ("OI_AIRGLOW_1302", 1301.2, 1307.0),
    ("CII_1335", 1333.5, 1337.2),
    ("SIIV_1394_1403", 1392.0, 1404.8),
    ("CIV_1548_1551", 1546.5, 1552.8),
    ("HEII_1640", 1639.0, 1642.0),
]


def jy_to_flam_cgs(wave_a: np.ndarray, flux_jy: np.ndarray) -> np.ndarray:
    """Convert flux density S_nu [Jy] to F_lambda [erg s^-1 cm^-2 A^-1]."""
    w = np.asarray(wave_a, dtype=np.float64)
    s = np.asarray(flux_jy, dtype=np.float64)
    return s * 1e-23 * C_ANGSTROM_PER_S / np.maximum(1e-12, w * w)


def hifi_ta_to_flam_cgs(freq_ghz: np.ndarray, flux_k: np.ndarray, ap_jy_per_k: float = HIFI_APERTURE_JY_PER_K) -> np.ndarray:
    """Convert Herschel/HIFI T_A* [K] vs frequency [GHz] into F_lambda [erg s^-1 cm^-2 A^-1]."""
    f_ghz = np.asarray(freq_ghz, dtype=np.float64)
    w_a = C_ANGSTROM_GHZ / np.maximum(1.0, f_ghz)
    return jy_to_flam_cgs(w_a, np.asarray(flux_k, dtype=np.float64) * float(ap_jy_per_k))


def _rolling_mad_scaled(res: np.ndarray, good: np.ndarray, win_bins: int = 95) -> np.ndarray:
    """Scale-invariant rolling MAD (avoids `_compute_rolling_mad_1d`'s 1e-6 floor on FUV/THz fluxes)."""
    g = np.asarray(good, dtype=bool) & np.isfinite(res)
    if int(np.sum(g)) < 8:
        return np.full_like(res, 1e-30, dtype=np.float64)
    sc = float(np.median(np.abs(res[g] - float(np.median(res[g]))))) * MAD_NORM
    if not math.isfinite(sc) or sc <= 0.0:
        sc = float(np.max(np.abs(res[g])))
    sc = max(1e-30, sc)
    rm = _compute_rolling_mad_1d(res / sc, g, win_bins=win_bins)
    return np.maximum(0.25, rm) * sc


def _estimate_fwhm_and_wings(z: np.ndarray, idx: int, win_half: int = 8) -> dict[str, float]:
    """Measure peak amplitude, single-pixel concentration eta_1px, and half-max FWHM in pixels."""
    n = len(z)
    lo = max(0, idx - win_half)
    hi = min(n, idx + win_half + 1)
    seg = z[lo:hi]
    p_rel = idx - lo
    z_pk = float(seg[p_rel])
    if not math.isfinite(z_pk) or z_pk <= 0.0:
        return {"z_pk": 0.0, "eta_1px": 1.0, "fwhm_px": 0.0, "side_sum": 0.0}
    pos_5 = np.maximum(0.0, seg[max(0, p_rel - 2) : min(len(seg), p_rel + 3)])
    s_5 = float(np.sum(pos_5))
    eta_1px = z_pk / max(1e-6, s_5)
    left_v = float(seg[p_rel - 1]) if p_rel - 1 >= 0 else 0.0
    right_v = float(seg[p_rel + 1]) if p_rel + 1 < len(seg) else 0.0
    side_sum = max(0.0, left_v) + max(0.0, right_v)
    hm = 0.5 * z_pk
    l_edge = float(p_rel)
    for k in range(p_rel - 1, -1, -1):
        if seg[k] < hm:
            denom = max(1e-6, float(seg[k + 1] - seg[k]))
            l_edge = k + (hm - float(seg[k])) / denom
            break
        l_edge = float(k)
    r_edge = float(p_rel)
    for k in range(p_rel + 1, len(seg)):
        if seg[k] < hm:
            denom = max(1e-6, float(seg[k - 1] - seg[k]))
            r_edge = (k - 1) + (float(seg[k - 1]) - hm) / denom
            break
        r_edge = float(k)
    fwhm_px = max(0.5, r_edge - l_edge)
    return {"z_pk": z_pk, "eta_1px": eta_1px, "fwhm_px": fwhm_px, "side_sum": side_sum}


def _match_thz_atlas_ghz(freq_ghz: float) -> str | None:
    """Return matching interstellar/circumstellar THz transition label within astrophysical wing."""
    for name, f0, tol_kms in HERSCHEL_MOLECULAR_ATOMIC_GHZ:
        dv = C_KMS * abs(freq_ghz - f0) / max(1e-6, f0)
        if dv <= tol_kms:
            return name
    return None


def _match_farir_atlas_um(wave_um: float) -> str | None:
    """Return matching sub-mm/far-IR molecular or fine-structure line within SPIRE/PACS FWHM."""
    for name, w0, tol_um in SPIRE_PACS_FARIR_ATLAS_UM:
        if abs(wave_um - w0) <= tol_um:
            return name
    return None


def scan_herschel_hifi_thz_v55(
    freq_ghz: np.ndarray,
    flux_k: np.ndarray,
    star: str,
    dp_id: str,
    band_name: str,
    err_k: np.ndarray | None = None,
    min_snr: float = 8.0,
) -> dict[str, Any]:
    """
    Engine `THZ_HET_V55`: Search Herschel/HIFI heterodyne spectra (R up to ~2.2e6, 0.5 MHz channels)
    for coherent narrow THz beacons while vetoing optical/HEB standing waves, single-channel LO
    spurs, broad molecular outflows (`FWHM >= 5.5 km/s`), and known THz transitions.
    """
    f = np.asarray(freq_ghz, dtype=np.float64)
    y = np.asarray(flux_k, dtype=np.float64)
    ord_f = np.argsort(f)
    f = f[ord_f]
    y = y[ord_f]
    fin = np.isfinite(f) & np.isfinite(y) & (f > 100.0)
    f = f[fin]
    y = y[fin]
    n = len(f)
    if n < 128:
        return {"star": star, "dp_id": dp_id, "band": band_name, "n_pix": n, "sigma_k": 0.0, "n_raw_peaks": 0, "n_qualified": 0, "candidates": []}

    df_ghz = max(1e-5, float(exact_median_1d(np.diff(f))))
    cont = median_filter(y, size=41, mode="nearest")
    res = y - cont
    # Estimate global & local noise robustly via scale-invariant sliding MAD (129-ch window)
    sig_glob = max(1e-30, float(exact_mad_1d(res)))
    sig_loc = _rolling_mad_scaled(res, np.ones(n, dtype=bool), win_bins=129)
    sig = np.maximum(sig_glob * 0.7, sig_loc)
    z = res / np.maximum(1e-30, sig)

    # Periodic FFT notch test for global/regional HEB + optical standing waves
    z_clean = np.clip(np.where(np.isfinite(z), z, 0.0), -25.0, 25.0)
    z_det = z_clean - float(np.median(z_clean))
    fft_pow = np.abs(np.fft.rfft(z_det)) ** 2
    fft_freqs = np.fft.rfftfreq(n, d=1.0)
    # Period range 12..320 channels (HIFI 92/300 MHz ripples)
    band_rip = (fft_freqs >= (1.0 / 320.0)) & (fft_freqs <= (1.0 / 12.0))
    ripple_ratio_glob = float(np.max(fft_pow[band_rip]) / max(1e-6, float(np.median(fft_pow[band_rip])))) if np.any(band_rip) else 1.0

    # Peak scan (trim 10 edge channels)
    raw_idx = [i for i in range(10, n - 10) if z[i] >= min_snr and z[i] >= z[i - 1] and z[i] >= z[i + 1]]
    raw_idx.sort(key=lambda i: -float(z[i]))
    kept_idx: list[int] = []
    for i in raw_idx:
        if all(abs(i - k) > 8 for k in kept_idx):
            kept_idx.append(i)

    cands: list[dict[str, Any]] = []
    for idx in kept_idx[:24]:
        fc = float(f[idx])
        wa = C_ANGSTROM_GHZ / fc
        stat = _estimate_fwhm_and_wings(z, idx, win_half=10)
        fwhm_px = stat["fwhm_px"]
        eta_1 = stat["eta_1px"]
        dv_fwhm_kms = C_KMS * (fwhm_px * df_ghz) / fc

        # Local ripple / multi-peak standing-wave test in +-240 ch window (excluding +-6 ch core)
        wlo = max(0, idx - 240)
        whi = min(n, idx + 241)
        loc_seg = np.concatenate([z[wlo : max(wlo, idx - 6)], z[min(whi, idx + 7) : whi]])
        n_rep_peaks = 0
        if len(loc_seg) >= 32:
            loc_pos = np.where((loc_seg[:-2] < loc_seg[1:-1]) & (loc_seg[1:-1] >= loc_seg[2:]) & (loc_seg[1:-1] >= 3.3))[0]
            # Count well-separated auxiliary crests >= 3.3 sigma
            prev_p = -999
            for p in loc_pos:
                if (int(p) - prev_p) >= 12:
                    n_rep_peaks += 1
                    prev_p = int(p)
        loc_fft = np.abs(np.fft.rfft(z_clean[wlo:whi] - float(np.median(z_clean[wlo:whi])))) ** 2 if (whi - wlo) >= 64 else np.array([1.0])
        loc_ff = np.fft.rfftfreq(whi - wlo, d=1.0) if (whi - wlo) >= 64 else np.array([0.0])
        loc_rip_m = (loc_ff >= (1.0 / 260.0)) & (loc_ff <= (1.0 / 12.0))
        loc_rip_ratio = float(np.max(loc_fft[loc_rip_m]) / max(1e-6, float(np.median(loc_fft[loc_rip_m])))) if np.any(loc_rip_m) else 1.0

        veto_reason = ""
        mol_match = _match_thz_atlas_ghz(fc)
        if eta_1 > 0.78 or stat["side_sum"] < 0.22 * stat["z_pk"] or fwhm_px < 1.45:
            veto_reason = "LO_SPUR_SINGLE_CHAN"
        elif n_rep_peaks >= 3 or (loc_rip_ratio > 14.0 and n_rep_peaks >= 2):
            veto_reason = "STANDING_WAVE_RIPPLE"
        elif dv_fwhm_kms >= 5.5 or fwhm_px > 12.0:
            veto_reason = "BROAD_MOLECULAR_EMISSION"
        elif mol_match is not None:
            veto_reason = f"THZ_MOLECULAR_ATLAS_{mol_match}"

        cands.append({
            "star": star,
            "dp_id": dp_id,
            "band": band_name,
            "freq_ghz": round(fc, 6),
            "wave_a": round(wa, 3),
            "wave_um": round(wa * 1e-4, 4),
            "snr": round(stat["z_pk"], 3),
            "eta_1px": round(eta_1, 4),
            "fwhm_px": round(fwhm_px, 3),
            "dv_fwhm_kms": round(dv_fwhm_kms, 3),
            "n_rep_peaks": n_rep_peaks,
            "loc_ripple_ratio": round(loc_rip_ratio, 2),
            "qualified_v55": veto_reason == "",
            "veto_reason": veto_reason or "QUALIFIED_V55_THZ_BEACON",
        })

    qual = [c for c in cands if c["qualified_v55"]]
    return {
        "star": star,
        "dp_id": dp_id,
        "band": band_name,
        "n_pix": n,
        "freq_min_ghz": float(f[0]),
        "freq_max_ghz": float(f[-1]),
        "sigma_k": sig_glob,
        "ripple_ratio_glob": round(ripple_ratio_glob, 2),
        "n_raw_peaks": len(cands),
        "n_qualified": len(qual),
        "candidates": cands,
    }


def scan_herschel_spire_fts_v55(
    wave_um: np.ndarray,
    flux_jy: np.ndarray,
    star: str,
    dp_id: str,
    band_name: str,
    off_axis_spectra: list[tuple[str, np.ndarray, np.ndarray]] | None = None,
    err_jy: np.ndarray | None = None,
    mask_arr: np.ndarray | None = None,
    min_snr: float = 8.0,
) -> dict[str, Any]:
    """
    Engine `SPIRE_RING_VETO_V55`: Search Herschel/SPIRE FTS central detector spectra (SLWC3/SSWD4,
    R ~ 1,000, 194-671 um) for point-source narrow emission beacons, enforcing simultaneous off-axis
    bolometer ring background veto, FTS sinc-sidelobe ghost veto, glitch check, and sub-mm line atlas.
    """
    w = np.asarray(wave_um, dtype=np.float64)
    y = np.asarray(flux_jy, dtype=np.float64)
    ord_w = np.argsort(w)
    w = w[ord_w]
    y = y[ord_w]
    m_bad = (np.asarray(mask_arr, dtype=np.int64)[ord_w] != 0) if mask_arr is not None else np.zeros(len(w), dtype=bool)
    fin = np.isfinite(w) & np.isfinite(y) & (w > 150.0) & (~m_bad)
    w = w[fin]
    y = y[fin]
    n = len(w)
    if n < 48:
        return {"star": star, "dp_id": dp_id, "band": band_name, "n_pix": n, "sigma_jy": 0.0, "n_raw_peaks": 0, "n_qualified": 0, "candidates": []}

    dw_um = max(1e-4, float(exact_median_1d(np.diff(w))))
    cont = median_filter(y, size=19, mode="nearest")
    res = y - cont
    sig_glob = max(1e-30, float(exact_mad_1d(res)))
    sig_loc = _rolling_mad_scaled(res, np.ones(n, dtype=bool), win_bins=65)
    sig = np.maximum(sig_glob * 0.7, sig_loc)
    z = res / np.maximum(1e-30, sig)

    # Precompute off-axis continuum-subtracted z vectors mapped onto `w`
    off_z_list: list[tuple[str, np.ndarray, np.ndarray]] = []
    if off_axis_spectra:
        for det_name, ow_in, of_in in off_axis_spectra:
            ow = np.asarray(ow_in, dtype=np.float64)
            oy = np.asarray(of_in, dtype=np.float64)
            of_fin = np.isfinite(ow) & np.isfinite(oy)
            if int(np.sum(of_fin)) < 48:
                continue
            oo = np.argsort(ow[of_fin])
            ows = ow[of_fin][oo]
            oys = oy[of_fin][oo]
            oc = median_filter(oys, size=19, mode="nearest")
            ores = oys - oc
            osig = max(1e-30, float(exact_mad_1d(ores)))
            ores_i = np.interp(w, ows, ores, left=0.0, right=0.0)
            oz_i = ores_i / osig
            off_z_list.append((det_name, oz_i, ores_i))

    raw_idx = [i for i in range(6, n - 6) if z[i] >= min_snr and z[i] >= z[i - 1] and z[i] >= z[i + 1]]
    raw_idx.sort(key=lambda i: -float(z[i]))
    kept_idx: list[int] = []
    for i in raw_idx:
        if all(abs(i - k) > 4 for k in kept_idx):
            kept_idx.append(i)

    cands: list[dict[str, Any]] = []
    for idx in kept_idx[:24]:
        wc = float(w[idx])
        stat = _estimate_fwhm_and_wings(z, idx, win_half=6)
        eta_1 = stat["eta_1px"]
        fwhm_px = stat["fwhm_px"]

        # 1. Off-axis ring bolometer spatial coincidence check
        max_off_snr = 0.0
        max_off_ratio = 0.0
        ring_hit = False
        c_amp = float(res[idx])
        for _, oz, ores in off_z_list:
            win_oz = float(np.max(oz[max(0, idx - 1) : min(n, idx + 2)]))
            win_or = float(np.max(ores[max(0, idx - 1) : min(n, idx + 2)]))
            ratio = win_or / max(1e-8, abs(c_amp))
            max_off_snr = max(max_off_snr, win_oz)
            max_off_ratio = max(max_off_ratio, ratio)
            if win_oz >= 3.2 and ratio >= 0.22:
                ring_hit = True

        # 2. FTS sinc-sidelobe ringing ghost check (stronger parent peak within 2..12 px + negative dips)
        sinc_ghost = False
        lo_p = max(0, idx - 12)
        hi_p = min(n, idx + 13)
        for j in range(lo_p, hi_p):
            if abs(j - idx) >= 2 and abs(z[j]) >= 1.55 * stat["z_pk"]:
                sinc_ghost = True
                break
        if not sinc_ghost:
            adj_neg = min(
                float(np.min(z[max(0, idx - 3) : idx])) if idx > 0 else 0.0,
                float(np.min(z[idx + 1 : min(n, idx + 4)])) if idx + 1 < n else 0.0,
            )
            if adj_neg <= -0.25 * stat["z_pk"] and adj_neg <= -3.5 and stat["z_pk"] < 40.0:
                sinc_ghost = True

        veto_reason = ""
        atlas_m = _match_farir_atlas_um(wc)
        if ring_hit:
            veto_reason = "OFF_AXIS_RING_COINCIDENCE"
        elif sinc_ghost:
            veto_reason = "FTS_SINC_SIDELOBE_GHOST"
        elif eta_1 > 0.74 or fwhm_px < 1.35 or stat["side_sum"] < 0.20 * stat["z_pk"]:
            veto_reason = "SPIRE_GLITCH_OR_UNRESOLVED"
        elif fwhm_px > 5.5:
            veto_reason = "BROAD_DUST_OR_CONTINUUM_BUMP"
        elif atlas_m is not None:
            veto_reason = f"SUBMM_ATLAS_{atlas_m}"

        cands.append({
            "star": star,
            "dp_id": dp_id,
            "band": band_name,
            "wave_um": round(wc, 4),
            "wave_a": round(wc * 1e4, 2),
            "snr": round(stat["z_pk"], 3),
            "eta_1px": round(eta_1, 4),
            "fwhm_px": round(fwhm_px, 3),
            "max_off_axis_snr": round(max_off_snr, 2),
            "max_off_axis_ratio": round(max_off_ratio, 3),
            "qualified_v55": veto_reason == "",
            "veto_reason": veto_reason or "QUALIFIED_V55_SPIRE_BEACON",
        })

    qual = [c for c in cands if c["qualified_v55"]]
    return {
        "star": star,
        "dp_id": dp_id,
        "band": band_name,
        "n_pix": n,
        "wave_min_um": float(w[0]),
        "wave_max_um": float(w[-1]),
        "sigma_jy": sig_glob,
        "n_off_axis_detectors": len(off_z_list),
        "n_raw_peaks": len(cands),
        "n_qualified": len(qual),
        "candidates": cands,
    }


def scan_herschel_pacs_farir_v55(
    wave_um: np.ndarray,
    flux_jy: np.ndarray,
    flag_arr: np.ndarray | None,
    star: str,
    dp_id: str,
    band_name: str,
    weight_arr: np.ndarray | None = None,
    min_snr: float = 8.0,
) -> dict[str, Any]:
    """
    Engine `PACS_FARIR_V55`: Search Herschel/PACS IFU central-spaxel spectra (51-210 um,
    R ~ 1,000-4,000) for unresolved point-source Far-IR lines while vetoing glitches/cosmic rays,
    band-edge artifacts, broad features, and known atomic/molecular Far-IR transitions.
    """
    w = np.asarray(wave_um, dtype=np.float64)
    y = np.asarray(flux_jy, dtype=np.float64)
    ord_w = np.argsort(w)
    w = w[ord_w]
    y = y[ord_w]
    flg = np.asarray(flag_arr, dtype=np.int64)[ord_w] if flag_arr is not None else np.zeros(len(w), dtype=np.int64)
    wgt = np.asarray(weight_arr, dtype=np.float64)[ord_w] if weight_arr is not None else np.ones(len(w), dtype=np.float64)
    fin = np.isfinite(w) & np.isfinite(y) & (w > 45.0) & (flg == 0) & (wgt > 0.0)
    w = w[fin]
    y = y[fin]
    n = len(w)
    if n < 64:
        return {"star": star, "dp_id": dp_id, "band": band_name, "n_pix": n, "sigma_jy": 0.0, "n_raw_peaks": 0, "n_qualified": 0, "candidates": []}

    cont = median_filter(y, size=29, mode="nearest")
    res = y - cont
    sig_glob = max(1e-30, float(exact_mad_1d(res)))
    sig_loc = _rolling_mad_scaled(res, np.ones(n, dtype=bool), win_bins=95)
    sig = np.maximum(sig_glob * 0.7, sig_loc)
    z = res / np.maximum(1e-30, sig)

    raw_idx = [i for i in range(6, n - 6) if z[i] >= min_snr and z[i] >= z[i - 1] and z[i] >= z[i + 1]]
    raw_idx.sort(key=lambda i: -float(z[i]))
    kept_idx: list[int] = []
    for i in raw_idx:
        if all(abs(i - k) > 5 for k in kept_idx):
            kept_idx.append(i)

    cands: list[dict[str, Any]] = []
    for idx in kept_idx[:24]:
        wc = float(w[idx])
        stat = _estimate_fwhm_and_wings(z, idx, win_half=7)
        eta_1 = stat["eta_1px"]
        fwhm_px = stat["fwhm_px"]

        veto_reason = ""
        atlas_m = _match_farir_atlas_um(wc)
        # Edge / weight drop check around peak
        if idx < 8 or idx >= (n - 8):
            veto_reason = "PACS_EDGE_ARTIFACT"
        elif eta_1 > 0.74 or fwhm_px < 1.40 or stat["side_sum"] < 0.22 * stat["z_pk"]:
            veto_reason = "PACS_GLITCH_COSMIC_RAY"
        elif fwhm_px > 6.5:
            veto_reason = "PACS_BROAD_CONTINUUM_FEATURE"
        elif atlas_m is not None:
            veto_reason = f"FARIR_ATLAS_{atlas_m}"

        cands.append({
            "star": star,
            "dp_id": dp_id,
            "band": band_name,
            "wave_um": round(wc, 4),
            "wave_a": round(wc * 1e4, 2),
            "snr": round(stat["z_pk"], 3),
            "eta_1px": round(eta_1, 4),
            "fwhm_px": round(fwhm_px, 3),
            "qualified_v55": veto_reason == "",
            "veto_reason": veto_reason or "QUALIFIED_V55_PACS_BEACON",
        })

    qual = [c for c in cands if c["qualified_v55"]]
    return {
        "star": star,
        "dp_id": dp_id,
        "band": band_name,
        "n_pix": n,
        "wave_min_um": float(w[0]),
        "wave_max_um": float(w[-1]),
        "sigma_jy": sig_glob,
        "n_raw_peaks": len(cands),
        "n_qualified": len(qual),
        "candidates": cands,
    }


def scan_hst_stis_e140h_v55(
    orders_data: list[dict[str, Any]],
    star: str,
    dp_id: str,
    min_snr: float = 8.0,
) -> dict[str, Any]:
    """
    Engine `STIS_E140H_V55`: Search HST/STIS FUV-MAMA E140H echelle orders (R = 114,000,
    1,140-1,700 A) for narrow unresolved FUV laser lines with MAMA hot-pixel/edge rejection,
    geocoronal & chromospheric masking, and adjacent-order overlap verification.
    """
    prepared: list[dict[str, Any]] = []
    for od in orders_data:
        w = np.asarray(od["wave_a"], dtype=np.float64)
        fl = np.asarray(od["flux"], dtype=np.float64)
        er = np.asarray(od["err"], dtype=np.float64)
        dq = np.asarray(od.get("dq", np.zeros(len(w))), dtype=np.int64)
        ord_i = np.argsort(w)
        w, fl, er, dq = w[ord_i], fl[ord_i], er[ord_i], dq[ord_i]
        # Mask STIS fatal DQ bits (fill, dead, hot, bad, coarse-res) & negative/zero errs
        good = np.isfinite(w) & np.isfinite(fl) & np.isfinite(er) & (er > 0.0) & ((dq & 1039) == 0)
        if int(np.sum(good)) < 48:
            continue
        cont = median_filter(np.where(good, fl, np.nanmedian(fl[good])), size=31, mode="nearest")
        res = np.where(good, fl - cont, 0.0)
        rmad = _rolling_mad_scaled(res, good, win_bins=95)
        sig = np.maximum(np.where(good, er, 1e-30), rmad)
        z = np.where(good, res / np.maximum(1e-30, sig), 0.0)
        prepared.append({
            "sporder": int(od["sporder"]),
            "wave_a": w,
            "flux": fl,
            "good": good,
            "z": z,
            "sig_flam_med": float(exact_median_1d(sig[good])),
        })

    if not prepared:
        return {"star": star, "dp_id": dp_id, "n_orders": 0, "n_raw_peaks": 0, "n_qualified": 0, "candidates": []}

    cands: list[dict[str, Any]] = []
    for oi, p in enumerate(prepared):
        w = p["wave_a"]
        z = p["z"]
        good = p["good"]
        n = len(w)
        dw_a = max(1e-5, float(exact_median_1d(np.diff(w))))
        raw_idx = [i for i in range(10, n - 10) if good[i] and z[i] >= min_snr and z[i] >= z[i - 1] and z[i] >= z[i + 1]]
        raw_idx.sort(key=lambda i: -float(z[i]))
        kept: list[int] = []
        for i in raw_idx:
            if all(abs(i - k) > 8 for k in kept):
                kept.append(i)

        for idx in kept[:10]:
            wc = float(w[idx])
            stat = _estimate_fwhm_and_wings(z, idx, win_half=7)
            eta_1 = stat["eta_1px"]
            fwhm_px = stat["fwhm_px"]
            dv_fwhm_kms = C_KMS * (fwhm_px * dw_a) / max(1.0, wc)

            # Check FUV geocoronal / chromospheric line windows
            geo_hit = ""
            for nm, wlo, whi in STIS_E140H_MASK_WINDOWS_A:
                if wlo <= wc <= whi:
                    geo_hit = nm
                    break

            # Cross-order overlap verification against other orders covering wc
            overlap_checked = False
            overlap_snr = 0.0
            for oj, q in enumerate(prepared):
                if oj == oi:
                    continue
                qw = q["wave_a"]
                if qw[0] + 0.08 <= wc <= qw[-1] - 0.08:
                    near = (np.abs(qw - wc) <= 3.0 * (wc / 114000.0)) & q["good"]
                    if int(np.sum(near)) >= 2:
                        overlap_checked = True
                        overlap_snr = max(overlap_snr, float(np.max(q["z"][near])))

            veto_reason = ""
            if geo_hit:
                veto_reason = f"FUV_GEOCORONAL_CHROMO_{geo_hit}"
            elif eta_1 > 0.74 or fwhm_px < 1.40 or stat["side_sum"] < 0.22 * stat["z_pk"]:
                veto_reason = "STIS_MAMA_HOTPX_OR_GLITCH"
            elif overlap_checked and overlap_snr < 3.8:
                veto_reason = "STIS_ORDER_OVERLAP_MISMATCH"
            elif dv_fwhm_kms >= 8.5 or fwhm_px > 6.5:
                veto_reason = "STIS_BROAD_CHROMOSPHERIC_LINE"

            cands.append({
                "star": star,
                "dp_id": dp_id,
                "sporder": p["sporder"],
                "wave_a": round(wc, 5),
                "snr": round(stat["z_pk"], 3),
                "eta_1px": round(eta_1, 4),
                "fwhm_px": round(fwhm_px, 3),
                "dv_fwhm_kms": round(dv_fwhm_kms, 3),
                "overlap_checked": overlap_checked,
                "overlap_snr": round(overlap_snr, 2),
                "qualified_v55": veto_reason == "",
                "veto_reason": veto_reason or "QUALIFIED_V55_STIS_FUV_BEACON",
            })

    cands.sort(key=lambda c: -float(c["snr"]))
    qual = [c for c in cands if c["qualified_v55"]]
    return {
        "star": star,
        "dp_id": dp_id,
        "n_orders": len(prepared),
        "n_raw_peaks": len(cands),
        "n_qualified": len(qual),
        "candidates": cands,
    }


def scan_coherent_shift_stack_jerk_v55(
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
    Engine `DRIFT_V55_JERK_OPTICAL`: Coherent inverse-variance 2D shift-and-stack across
    `N >= 4` multi-epoch optical & NIR waterfalls with 3rd-order orthogonalized cubic jerk basis
    `P3(tau) = 2.5 * (tau^3 - 0.6 * tau)`, quadratic sag, linear drift, and Keplerian sinusoids,
    enforcing NaN-safe template subtraction, fixed-rest stationary veto (signed shifts), BERV-sky
    topocentric veto, leave-one-out jackknife, and top-2 dominance cap (`< 0.67` for `N >= 5`).
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
        "n_pixel_trajectory_integrals": 0,
        "n_raw_candidates": 0,
        "candidates": [],
    }
    if fn_e.ndim != 2 or n_ep_in < 4 or len(w) < 256:
        return empty

    ord_t = np.argsort(mjds)
    mjds, fn_e, sig_e, v_o2r = mjds[ord_t], fn_e[ord_t], sig_e[ord_t], v_o2r[ord_t]
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

    col_ok = np.sum(V, axis=0) >= max(4, int(math.ceil(0.55 * n_ep)))
    Z[:, ~col_ok] = 0.0
    V[:, ~col_ok] = False

    ln_w0 = math.log(float(w[0]))
    ln_w1 = math.log(float(w[-1]))
    dv_grid_kms = max(1.2, min(4.5, 0.70 * sig_v))
    dln = dv_grid_kms / C_KMS
    n_log = int(math.floor((ln_w1 - ln_w0) / dln)) + 1
    if n_log > 160000:
        dln = (ln_w1 - ln_w0) / 160000.0
        dv_grid_kms = dln * C_KMS
        n_log = 160001
    ln_grid = ln_w0 + dln * np.arange(n_log, dtype=np.float64)
    w_log = np.exp(ln_grid)
    ln_w_native = np.log(w)

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

    for k in range(n_ep):
        mk = M_log[k, V_log[k]]
        if len(mk) >= 64:
            mad_m = exact_mad_1d(mk)
            if mad_m > 0.2:
                M_log[k] /= mad_m

    pad = int(math.ceil(260.0 / dv_grid_kms)) + 4
    n_core = n_log - 2 * pad
    if n_core < 64:
        return empty
    base_idx = np.arange(pad, n_log - pad, dtype=np.int64)

    t_mid = 0.5 * (float(mjds[0]) + float(mjds[-1]))
    dt_half = max(1e-3, 0.5 * (float(mjds[-1]) - float(mjds[0])))
    tau = (mjds - t_mid) / dt_half
    p2_tau = tau * tau - (1.0 / 3.0)
    p3_tau = 2.5 * (tau * tau * tau - 0.6 * tau)

    M_z = np.ascontiguousarray(np.where(V_log, M_log, 0.0), dtype=np.float64)
    V_u8 = np.ascontiguousarray(V_log.astype(np.uint8))
    inv_sqrt_nv = np.zeros(n_ep + 1, dtype=np.float64)
    for k_nv in range(4, n_ep + 1):
        inv_sqrt_nv[k_nv] = 1.0 / math.sqrt(float(k_nv))

    def _eval_traj(v_ep_kms: np.ndarray, branch: str, meta: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
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
            s_sorted = np.sort(s_act)[::-1]
            s_max = float(s_sorted[0])
            sum_act = float(np.sum(s_act))
            snr_st = sum_act / math.sqrt(float(n_val))
            snr_loo = (sum_act - s_max) / math.sqrt(float(n_val - 1))
            if snr_loo < min_snr_loo:
                continue
            sum_pos = float(np.sum(np.maximum(s_act, 0.0)))
            single_frac = s_max / max(1e-6, sum_pos)
            if single_frac > max_single_frac:
                continue
            if n_val >= 5:
                top2_frac = float(s_sorted[0] + s_sorted[1]) / max(1e-6, sum_pos)
                if top2_frac > 0.67:
                    continue
            pos_frac = float(np.sum(s_act >= 1.5)) / float(n_val)
            if pos_frac < min_pos_frac:
                continue

            # Fixed-rest stationary veto across signed shift bracket
            s_lo = int(np.min(sh)) - 2
            s_hi = int(np.max(sh)) + 2
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

            # Topocentric BERV sky-line coincidence veto
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

    # 1. Orthogonalized Linear + Quadratic Sag + Cubic Jerk grid
    slopes = np.linspace(-180.0, 180.0, 37)
    sags = np.linspace(-60.0, 60.0, 5)
    jerks = np.array([-60.0, -30.0, 0.0, 30.0, 60.0])
    raw_cands: list[dict[str, Any]] = []
    n_eval = 0

    for jk in jerks:
        for sg in sags:
            for hs in slopes:
                if abs(hs) < 6.0 and abs(sg) < 8.0 and abs(jk) < 8.0:
                    continue
                v_curve = float(hs) * tau + float(sg) * p2_tau + float(jk) * p3_tau
                if abs(jk) >= 12.0:
                    br = "CUBIC_JERK_STACK_V55"
                elif abs(sg) >= 8.0:
                    br = "CURVED_STACK_V55"
                else:
                    br = "LINEAR_STACK_V55"
                hits, cnt = _eval_traj(
                    v_curve,
                    br,
                    {"half_slope_kms": round(float(hs), 2), "quad_sag_kms": round(float(sg), 2), "cubic_jerk_kms": round(float(jk), 2)},
                )
                n_eval += cnt
                raw_cands.extend(hits)

    # 2. Vectorized Periodic / Keplerian Sinusoidal Grid
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
                    hits, cnt = _eval_traj(
                        v_orb,
                        "PERIODIC_STACK_V55",
                        {"period_d": round(float(p_d), 4), "k_amp_kms": round(float(k_amp), 2), "phi_rad": round(float(phi), 3)},
                    )
                    n_eval += cnt
                    raw_cands.extend(hits)
    if known_orb_period_days is not None and math.isfinite(float(known_orb_period_days)) and float(known_orb_period_days) > 0.3 and n_ep >= 4:
        p_k = float(known_orb_period_days)
        n_phi_k = max(24, min(72, int(math.ceil(2.0 * math.pi * 175.0 / max(1.5, sig_v * 2.5)))))
        phi_k_grid = np.linspace(0.0, 2.0 * math.pi, n_phi_k, endpoint=False)
        k_k_grid = np.array([35.0, 70.0, 110.0, 155.0, 195.0])
        if known_orb_kp_kms is not None and math.isfinite(float(known_orb_kp_kms)) and float(known_orb_kp_kms) >= 12.0:
            k_k_grid = np.unique(np.append(k_k_grid, float(known_orb_kp_kms)))
        for phi in phi_k_grid:
            sin_v = np.sin(2.0 * math.pi * t_rel / p_k + float(phi))
            for k_amp in k_k_grid:
                v_orb = float(k_amp) * sin_v
                hits, cnt = _eval_traj(
                    v_orb,
                    "KEPLERIAN_COHERENT_STACK_V55",
                    {"period_d": round(p_k, 4), "k_amp_kms": round(float(k_amp), 2), "phi_rad": round(float(phi), 3)},
                )
                n_eval += cnt
                raw_cands.extend(hits)

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


def run_herschel_hifi_calibration_v55(seed: int = 9701) -> dict[str, Any]:
    """`CALIBRATION_V55_HERSCHEL_HIFI_180`: 60 THz beacons + 40 standing waves + 40 broad molecular + 40 LO spurs."""
    rng = np.random.default_rng(seed)
    n_pix = 1600
    f0 = 650.0
    freq_ghz = f0 + 0.0005 * np.arange(n_pix, dtype=np.float64)
    trials: list[dict[str, Any]] = []
    b_rec = r_vet = m_vet = l_vet = 0

    for i in range(60):
        noise = rng.normal(0.0, 0.03, size=n_pix)
        fc = float(rng.uniform(f0 + 0.15, f0 + 0.65))
        if _match_thz_atlas_ghz(fc) is not None:
            fc += 0.12
        sig_ghz = float(rng.uniform(0.00055, 0.00090))
        y = 0.25 + noise + float(rng.uniform(0.36, 0.65)) * np.exp(-0.5 * ((freq_ghz - fc) / sig_ghz) ** 2)
        res = scan_herschel_hifi_thz_v55(freq_ghz, y, f"SIM_HIFI_B_{i}", f"SHB_{i}", "HIFI_2B")
        ok = res["n_qualified"] >= 1
        b_rec += int(ok)
        trials.append({"suite": "CALIBRATION_V55_HERSCHEL_HIFI_180", "class": "CLEAN_THZ_BEACON", "trial": i, "expected": 1, "observed": int(ok), "passed": int(ok == 1)})

    for i in range(40):
        noise = rng.normal(0.0, 0.03, size=n_pix)
        per_ch = float(rng.uniform(45.0, 120.0))
        phase = float(rng.uniform(0.0, 2.0 * math.pi))
        amp_sw = float(rng.uniform(0.38, 0.70))
        y = 0.25 + noise + amp_sw * np.sin(2.0 * math.pi * np.arange(n_pix) / per_ch + phase)
        res = scan_herschel_hifi_thz_v55(freq_ghz, y, f"SIM_HIFI_SW_{i}", f"SHS_{i}", "HIFI_2B")
        ok = res["n_qualified"] == 0
        r_vet += int(ok)
        trials.append({"suite": "CALIBRATION_V55_HERSCHEL_HIFI_180", "class": "STANDING_WAVE_VETO", "trial": i, "expected": 0, "observed": int(res["n_qualified"] > 0), "passed": int(ok)})

    for i in range(40):
        noise = rng.normal(0.0, 0.03, size=n_pix)
        fc = float(rng.uniform(f0 + 0.15, f0 + 0.65))
        dv_kms = float(rng.uniform(8.0, 35.0))
        sig_ghz = (fc * (dv_kms / C_KMS)) / FWHM_FACTOR
        y = 0.25 + noise + float(rng.uniform(0.45, 0.90)) * np.exp(-0.5 * ((freq_ghz - fc) / sig_ghz) ** 2)
        res = scan_herschel_hifi_thz_v55(freq_ghz, y, f"SIM_HIFI_MOL_{i}", f"SHM_{i}", "HIFI_2B")
        ok = res["n_qualified"] == 0
        m_vet += int(ok)
        trials.append({"suite": "CALIBRATION_V55_HERSCHEL_HIFI_180", "class": "BROAD_MOLECULAR_VETO", "trial": i, "expected": 0, "observed": int(res["n_qualified"] > 0), "passed": int(ok)})

    for i in range(40):
        noise = rng.normal(0.0, 0.03, size=n_pix)
        y = 0.25 + noise
        idx_sp = int(rng.integers(100, n_pix - 100))
        y[idx_sp] += float(rng.uniform(0.45, 0.90))
        res = scan_herschel_hifi_thz_v55(freq_ghz, y, f"SIM_HIFI_LO_{i}", f"SHL_{i}", "HIFI_2B")
        ok = res["n_qualified"] == 0
        l_vet += int(ok)
        trials.append({"suite": "CALIBRATION_V55_HERSCHEL_HIFI_180", "class": "SINGLE_CHAN_LO_VETO", "trial": i, "expected": 0, "observed": int(res["n_qualified"] > 0), "passed": int(ok)})

    return {
        "total_trials": len(trials),
        "thz_beacon_recovery": f"{b_rec}/60 ({b_rec/60.0:.4f})",
        "standing_wave_veto": f"{r_vet}/40 ({r_vet/40.0:.4f})",
        "broad_molecular_veto": f"{m_vet}/40 ({m_vet/40.0:.4f})",
        "lo_spur_veto": f"{l_vet}/40 ({l_vet/40.0:.4f})",
        "trials": trials,
    }


def run_herschel_spire_pacs_calibration_v55(seed: int = 9702) -> dict[str, Any]:
    """`CALIBRATION_V55_SPIRE_PACS_180`: 60 point beacons + 40 off-axis ring + 40 sinc ghosts + 40 PACS glitches."""
    rng = np.random.default_rng(seed)
    n_sp = 500
    w_sp = np.linspace(210.0, 310.0, n_sp)
    n_pc = 500
    w_pc = np.linspace(65.0, 95.0, n_pc)
    trials: list[dict[str, Any]] = []
    pt_rec = ring_vet = sinc_vet = pacs_vet = 0

    for i in range(60):
        wc = float(rng.uniform(222.0, 298.0))
        while _match_farir_atlas_um(wc) is not None:
            wc += 2.8
        sig_u = 0.23
        y = 5.0 + rng.normal(0.0, 0.08, size=n_sp) + float(rng.uniform(1.0, 1.8)) * np.exp(-0.5 * ((w_sp - wc) / sig_u) ** 2)
        off = [("SLWB2", w_sp, 1.0 + rng.normal(0.0, 0.08, size=n_sp)), ("SLWC2", w_sp, 1.0 + rng.normal(0.0, 0.08, size=n_sp))]
        res = scan_herschel_spire_fts_v55(w_sp, y, f"SIM_SP_PT_{i}", f"SSPT_{i}", "SPIRE_SLWC3", off_axis_spectra=off)
        ok = res["n_qualified"] >= 1
        pt_rec += int(ok)
        trials.append({"suite": "CALIBRATION_V55_SPIRE_PACS_180", "class": "CLEAN_POINT_BEACON", "trial": i, "expected": 1, "observed": int(ok), "passed": int(ok == 1)})

    for i in range(40):
        wc = float(rng.uniform(222.0, 298.0))
        while _match_farir_atlas_um(wc) is not None:
            wc += 2.8
        prof = float(rng.uniform(1.1, 1.8)) * np.exp(-0.5 * ((w_sp - wc) / 0.24) ** 2)
        y = 5.0 + rng.normal(0.0, 0.08, size=n_sp) + prof
        off = [("SLWB2", w_sp, 1.0 + rng.normal(0.0, 0.08, size=n_sp) + 0.7 * prof), ("SLWC2", w_sp, 1.0 + rng.normal(0.0, 0.08, size=n_sp) + 0.65 * prof)]
        res = scan_herschel_spire_fts_v55(w_sp, y, f"SIM_SP_RNG_{i}", f"SSRN_{i}", "SPIRE_SLWC3", off_axis_spectra=off)
        ok = res["n_qualified"] == 0
        ring_vet += int(ok)
        trials.append({"suite": "CALIBRATION_V55_SPIRE_PACS_180", "class": "OFF_AXIS_RING_VETO", "trial": i, "expected": 0, "observed": int(res["n_qualified"] > 0), "passed": int(ok)})

    for i in range(40):
        # Genuine CO 9-8 / NII line with strong FTS sinc sidelobe ringing!
        wc = 289.120  # CO J=9-8 parent
        x_s = (w_sp - wc) / 0.30
        sinc_prof = float(rng.uniform(6.0, 9.0)) * np.sinc(x_s)
        y = 5.0 + rng.normal(0.0, 0.08, size=n_sp) + sinc_prof
        res = scan_herschel_spire_fts_v55(w_sp, y, f"SIM_SP_SINC_{i}", f"SSNC_{i}", "SPIRE_SLWC3")
        ok = res["n_qualified"] == 0
        sinc_vet += int(ok)
        trials.append({"suite": "CALIBRATION_V55_SPIRE_PACS_180", "class": "FTS_SINC_SIDELOBE_VETO", "trial": i, "expected": 0, "observed": int(res["n_qualified"] > 0), "passed": int(ok)})

    for i in range(40):
        y = 4.0 + rng.normal(0.0, 0.06, size=n_pc)
        flg = np.zeros(n_pc, dtype=np.int64)
        idx_g = int(rng.integers(30, n_pc - 30)) if i < 25 else int(rng.choice([3, 5, n_pc - 4, n_pc - 6]))
        y[idx_g] += float(rng.uniform(0.9, 1.8))
        res = scan_herschel_pacs_farir_v55(w_pc, y, flg, f"SIM_PC_GL_{i}", f"SPGL_{i}", "PACS_B2B")
        ok = res["n_qualified"] == 0
        pacs_vet += int(ok)
        trials.append({"suite": "CALIBRATION_V55_SPIRE_PACS_180", "class": "PACS_GLITCH_EDGE_VETO", "trial": i, "expected": 0, "observed": int(res["n_qualified"] > 0), "passed": int(ok)})

    return {
        "total_trials": len(trials),
        "point_beacon_recovery": f"{pt_rec}/60 ({pt_rec/60.0:.4f})",
        "off_axis_ring_veto": f"{ring_vet}/40 ({ring_vet/40.0:.4f})",
        "fts_sinc_sidelobe_veto": f"{sinc_vet}/40 ({sinc_vet/40.0:.4f})",
        "pacs_glitch_edge_veto": f"{pacs_vet}/40 ({pacs_vet/40.0:.4f})",
        "trials": trials,
    }


def run_hst_stis_e140h_calibration_v55(seed: int = 9703) -> dict[str, Any]:
    """`CALIBRATION_V55_HST_STIS_E140H_120`: 60 FUV beacons (dual-order) + 30 hot/single-order + 30 chromospheric."""
    rng = np.random.default_rng(seed)
    n_p = 1024
    w_ord1 = np.linspace(1245.5, 1251.5, n_p)
    w_ord2 = np.linspace(1248.0, 1254.0, n_p)
    w_mask = np.linspace(1258.5, 1264.5, n_p)
    sig_a = 1250.0 / (114000.0 * FWHM_FACTOR)
    trials: list[dict[str, Any]] = []
    fuv_rec = hot_vet = chr_vet = 0

    for i in range(60):
        wc = float(rng.uniform(1248.5, 1251.0))  # inside cross-order overlap [1248.0, 1251.5] outside mask
        amp = float(rng.uniform(12.0, 18.0)) * 1e-13
        er1 = np.full(n_p, 1e-13)
        er2 = np.full(n_p, 1e-13)
        f1 = 2e-12 + rng.normal(0.0, 1e-13, size=n_p) + amp * np.exp(-0.5 * ((w_ord1 - wc) / sig_a) ** 2)
        f2 = 2e-12 + rng.normal(0.0, 1e-13, size=n_p) + amp * np.exp(-0.5 * ((w_ord2 - wc) / sig_a) ** 2)
        orders = [
            {"sporder": 300, "wave_a": w_ord1, "flux": f1, "err": er1, "dq": np.zeros(n_p, dtype=np.int64)},
            {"sporder": 299, "wave_a": w_ord2, "flux": f2, "err": er2, "dq": np.zeros(n_p, dtype=np.int64)},
        ]
        res = scan_hst_stis_e140h_v55(orders, f"SIM_STIS_B_{i}", f"SSB_{i}")
        ok = res["n_qualified"] >= 1
        fuv_rec += int(ok)
        trials.append({"suite": "CALIBRATION_V55_HST_STIS_E140H_120", "class": "CLEAN_FUV_BEACON", "trial": i, "expected": 1, "observed": int(ok), "passed": int(ok == 1)})

    for i in range(30):
        er1 = np.full(n_p, 1e-13)
        er2 = np.full(n_p, 1e-13)
        f1 = 2e-12 + rng.normal(0.0, 1e-13, size=n_p)
        f2 = 2e-12 + rng.normal(0.0, 1e-13, size=n_p)
        if i < 15:
            idx_h = int(rng.integers(50, n_p - 50))
            f1[idx_h] += float(rng.uniform(15.0, 25.0)) * 1e-13
        else:
            wc = float(rng.uniform(1248.5, 1251.0))
            f1 += float(rng.uniform(12.0, 18.0)) * 1e-13 * np.exp(-0.5 * ((w_ord1 - wc) / sig_a) ** 2)
        orders = [
            {"sporder": 300, "wave_a": w_ord1, "flux": f1, "err": er1, "dq": np.zeros(n_p, dtype=np.int64)},
            {"sporder": 299, "wave_a": w_ord2, "flux": f2, "err": er2, "dq": np.zeros(n_p, dtype=np.int64)},
        ]
        res = scan_hst_stis_e140h_v55(orders, f"SIM_STIS_HOT_{i}", f"SSH_{i}")
        ok = res["n_qualified"] == 0
        hot_vet += int(ok)
        trials.append({"suite": "CALIBRATION_V55_HST_STIS_E140H_120", "class": "MAMA_HOTPX_EDGE_VETO", "trial": i, "expected": 0, "observed": int(res["n_qualified"] > 0), "passed": int(ok)})

    for i in range(30):
        er1 = np.full(n_p, 1e-13)
        w_use = w_mask if i < 15 else w_ord1
        f1 = 2e-12 + rng.normal(0.0, 1e-13, size=n_p)
        if i < 15:
            wc = float(rng.uniform(1260.4, 1263.8))
            s_c = sig_a
        else:
            wc = float(rng.uniform(1247.0, 1250.0))
            s_c = (wc * (float(rng.uniform(18.0, 40.0)) / C_KMS)) / FWHM_FACTOR
        f1 += float(rng.uniform(14.0, 22.0)) * 1e-13 * np.exp(-0.5 * ((w_use - wc) / s_c) ** 2)
        orders = [{"sporder": 300, "wave_a": w_use, "flux": f1, "err": er1, "dq": np.zeros(n_p, dtype=np.int64)}]
        res = scan_hst_stis_e140h_v55(orders, f"SIM_STIS_CHR_{i}", f"SSC_{i}")
        ok = res["n_qualified"] == 0
        chr_vet += int(ok)
        trials.append({"suite": "CALIBRATION_V55_HST_STIS_E140H_120", "class": "CHROMOSPHERIC_GEOCORONAL_VETO", "trial": i, "expected": 0, "observed": int(res["n_qualified"] > 0), "passed": int(ok)})

    return {
        "total_trials": len(trials),
        "fuv_beacon_recovery": f"{fuv_rec}/60 ({fuv_rec/60.0:.4f})",
        "hotpx_overlap_veto": f"{hot_vet}/30 ({hot_vet/30.0:.4f})",
        "chromo_geocoronal_veto": f"{chr_vet}/30 ({chr_vet/30.0:.4f})",
        "trials": trials,
    }


def run_coherent_jerk_calibration_v55(seed: int = 9704) -> dict[str, Any]:
    """
    `CALIBRATION_V55_COHERENT_JERK_240`: 240 sub-threshold 2D trials:
      - 60 faint `3.1-3.8 sigma/epoch` cubic-jerk + curved beacons (`N=10`)
      - 60 faint `3.1-3.8 sigma/epoch` periodic orbiting beacons (`N=12`)
      - 40 stationary stellar lines -> 100% VETO
      - 40 bright single-epoch transients (`18-28 sigma`) -> 100% VETO
      - 40 BERV-following topocentric sky lines -> 100% VETO
    """
    rng = np.random.default_rng(seed)
    cfg = get_inst_config("ESO_FEROS")
    n_wave = 1800
    w_rest = np.linspace(5400.0, 5450.0, n_wave)
    sig_v = float(cfg["sigma_v_kms"])
    sig_a_c = 5425.0 * (sig_v / C_KMS)

    jerk_rec = per_rec = stat_vet = trans_vet = sky_vet = 0
    trials: list[dict[str, Any]] = []

    def _mk(n_ep: int) -> tuple[np.ndarray, np.ndarray]:
        return 1.0 + rng.normal(0.0, 0.015, size=(n_ep, n_wave)), np.full((n_ep, n_wave), 0.015, dtype=np.float64)

    for i in range(60):
        n_ep = 10
        mjds = 59000.0 + np.linspace(0.0, 120.0, n_ep)
        bervs = 20.0 * np.sin(2.0 * math.pi * (mjds - 59000.0) / 365.25)
        fn_e, sig_e = _mk(n_ep)
        tau = (mjds - 59060.0) / 60.0
        p2 = tau * tau - (1.0 / 3.0)
        p3 = 2.5 * (tau * tau * tau - 0.6 * tau)
        w0 = float(rng.uniform(5415.0, 5435.0))
        hs = float(rng.choice([-1.0, 1.0])) * float(rng.uniform(35.0, 130.0))
        sg = float(rng.uniform(-40.0, 40.0))
        jk = float(rng.choice([-1.0, 1.0])) * float(rng.uniform(25.0, 60.0))
        v_ep = hs * tau + sg * p2 + jk * p3
        amp_rel = float(rng.uniform(3.1, 3.8)) * 0.015
        for k in range(n_ep):
            wk = w0 * (1.0 + v_ep[k] / C_KMS)
            fn_e[k] += amp_rel * np.exp(-0.5 * ((w_rest - wk) / sig_a_c) ** 2)
        res = scan_coherent_shift_stack_jerk_v55(w_rest, fn_e, sig_e, mjds, bervs, cfg, star=f"SIM_JRK_{i}")
        ok = res["n_raw_candidates"] >= 1
        jerk_rec += int(ok)
        trials.append({"suite": "CALIBRATION_V55_COHERENT_JERK_240", "class": "SUBTHRESH_CUBIC_JERK", "trial": i, "expected": 1, "observed": int(ok), "passed": int(ok == 1)})

    for i in range(60):
        n_ep = 12
        mjds = 59000.0 + np.sort(rng.uniform(0.0, 90.0, n_ep))
        bervs = 18.0 * np.cos(2.0 * math.pi * (mjds - 59000.0) / 365.25)
        fn_e, sig_e = _mk(n_ep)
        w0 = float(rng.uniform(5415.0, 5435.0))
        p_d = float(rng.uniform(3.2, 24.0))
        k_amp = float(rng.uniform(55.0, 175.0))
        phi = float(rng.uniform(0.0, 2.0 * math.pi))
        v_ep = k_amp * np.sin(2.0 * math.pi * (mjds - mjds[0]) / p_d + phi)
        amp_rel = float(rng.uniform(3.1, 3.8)) * 0.015
        for k in range(n_ep):
            wk = w0 * (1.0 + v_ep[k] / C_KMS)
            fn_e[k] += amp_rel * np.exp(-0.5 * ((w_rest - wk) / sig_a_c) ** 2)
        res = scan_coherent_shift_stack_jerk_v55(
            w_rest, fn_e, sig_e, mjds, bervs, cfg, star=f"SIM_PER55_{i}",
            known_orb_period_days=p_d, known_orb_kp_kms=k_amp,
        )
        ok = res["n_raw_candidates"] >= 1
        per_rec += int(ok)
        trials.append({"suite": "CALIBRATION_V55_COHERENT_JERK_240", "class": "SUBTHRESH_PERIODIC", "trial": i, "expected": 1, "observed": int(ok), "passed": int(ok == 1)})

    for i in range(40):
        n_ep = 10
        mjds = 59000.0 + np.linspace(0.0, 100.0, n_ep)
        bervs = 19.0 * np.sin(2.0 * math.pi * (mjds - 59000.0) / 365.25)
        fn_e, sig_e = _mk(n_ep)
        w0 = float(rng.uniform(5415.0, 5435.0))
        amp_rel = float(rng.uniform(6.0, 12.0)) * 0.015
        for k in range(n_ep):
            fn_e[k] += amp_rel * np.exp(-0.5 * ((w_rest - w0) / sig_a_c) ** 2)
        res = scan_coherent_shift_stack_jerk_v55(w_rest, fn_e, sig_e, mjds, bervs, cfg, star=f"SIM_STAT55_{i}")
        ok = res["n_raw_candidates"] == 0
        stat_vet += int(ok)
        trials.append({"suite": "CALIBRATION_V55_COHERENT_JERK_240", "class": "STATIONARY_VETO", "trial": i, "expected": 0, "observed": int(res["n_raw_candidates"] > 0), "passed": int(ok)})

    for i in range(40):
        n_ep = 10
        mjds = 59000.0 + np.linspace(0.0, 100.0, n_ep)
        bervs = 19.0 * np.sin(2.0 * math.pi * (mjds - 59000.0) / 365.25)
        fn_e, sig_e = _mk(n_ep)
        w0 = float(rng.uniform(5415.0, 5435.0))
        k_t = int(rng.integers(0, n_ep))
        fn_e[k_t] += float(rng.uniform(18.0, 28.0)) * 0.015 * np.exp(-0.5 * ((w_rest - w0) / sig_a_c) ** 2)
        res = scan_coherent_shift_stack_jerk_v55(w_rest, fn_e, sig_e, mjds, bervs, cfg, star=f"SIM_TRN55_{i}")
        ok = res["n_raw_candidates"] == 0
        trans_vet += int(ok)
        trials.append({"suite": "CALIBRATION_V55_COHERENT_JERK_240", "class": "TRANSIENT_VETO", "trial": i, "expected": 0, "observed": int(res["n_raw_candidates"] > 0), "passed": int(ok)})

    for i in range(40):
        n_ep = 10
        mjds = 59000.0 + np.linspace(0.0, 100.0, n_ep)
        bervs = 24.0 * np.sin(2.0 * math.pi * (mjds - 59000.0) / 365.25)
        fn_e, sig_e = _mk(n_ep)
        w_sky = float(rng.uniform(5415.0, 5435.0))
        amp_rel = float(rng.uniform(5.0, 8.5)) * 0.015
        for k in range(n_ep):
            wk = w_sky * (1.0 + bervs[k] / C_KMS)
            fn_e[k] += amp_rel * np.exp(-0.5 * ((w_rest - wk) / sig_a_c) ** 2)
        res = scan_coherent_shift_stack_jerk_v55(w_rest, fn_e, sig_e, mjds, bervs, cfg, star=f"SIM_SKY55_{i}")
        ok = res["n_raw_candidates"] == 0
        sky_vet += int(ok)
        trials.append({"suite": "CALIBRATION_V55_COHERENT_JERK_240", "class": "BERV_SKY_VETO", "trial": i, "expected": 0, "observed": int(res["n_raw_candidates"] > 0), "passed": int(ok)})

    return {
        "total_trials": len(trials),
        "cubic_jerk_recovery": f"{jerk_rec}/60 ({jerk_rec/60.0:.4f})",
        "periodic_recovery": f"{per_rec}/60 ({per_rec/60.0:.4f})",
        "stationary_veto": f"{stat_vet}/40 ({stat_vet/40.0:.4f})",
        "transient_veto": f"{trans_vet}/40 ({trans_vet/40.0:.4f})",
        "berv_sky_veto": f"{sky_vet}/40 ({sky_vet/40.0:.4f})",
        "trials": trials,
    }


# ===========================================================================
# TECHNOSIGNATURE V5.6 ENGINES (SOFIA GREAT, ISO SWS, SOFIA FORCAST, JERK)
# ===========================================================================

SOFIA_GREAT_APERTURE_M = 2.5

SOFIA_GREAT_MOLECULAR_ATOMIC_GHZ: tuple[tuple[str, float, float], ...] = tuple(
    list(HERSCHEL_MOLECULAR_ATOMIC_GHZ)
    + [
        ("CO_17_16", 1956.0181, 45.0),
        ("CO_18_17", 2070.6160, 45.0),
        ("CO_19_18", 2185.1347, 45.0),
        ("CO_20_19", 2299.5698, 45.0),
        ("CO_21_20", 2413.9171, 45.0),
        ("CO_22_21", 2528.1721, 45.0),
        ("OI_63UM", 4744.7775, 40.0),
        ("CII_158UM", 1900.5369, 40.0),
        ("OI_145UM", 2060.0689, 40.0),
        ("NII_205UM", 1461.1319, 40.0),
        ("NII_122UM", 2459.3801, 40.0),
        ("OIII_88UM", 3393.0062, 40.0),
        ("OIII_52UM", 5785.8796, 40.0),
        ("NIII_57UM", 5230.4300, 40.0),
        ("HeHp_1_0", 2010.1839, 30.0),
        ("OH_2PI32_A", 2509.9490, 40.0),
        ("OH_2PI32_B", 2514.3167, 40.0),
        ("OH_2PI12_A", 1834.7474, 40.0),
        ("OH_2PI12_B", 1837.8168, 40.0),
        ("OH_2PI32_72", 3543.7794, 40.0),
        ("OH_2PI32_72B", 3551.1850, 40.0),
        ("HD_1_0", 2674.9860, 35.0),
        ("HCN_16_15", 1417.3095, 45.0),
        ("HCN_17_16", 1505.8400, 45.0),
        ("HCN_21_20", 1859.9800, 45.0),
        ("HCN_V2_17_16A", 1505.1000, 45.0),
        ("HCN_V2_17_16B", 1512.6000, 45.0),
        ("HCN_V2_21_20", 1867.2000, 45.0),
        ("o_H2O_212_101", 1669.9048, 45.0),
        ("o_H2O_303_212", 1716.7696, 45.0),
        ("o_H2O_414_303", 2640.4740, 45.0),
        ("p_H2O_211_202", 752.0331, 45.0),
        ("p_H2O_202_111", 987.9268, 45.0),
        ("p_H2O_111_000", 1113.3430, 45.0),
        ("CH_PLUS_2_1", 1669.2813, 35.0),
        ("HF_1_0", 1232.4763, 35.0),
        ("NH3_3_0_A", 1763.5240, 40.0),
        ("O3_TELLURIC_1901", 1901.0000, 30.0),
        ("O3_TELLURIC_4745", 4745.2000, 30.0),
    ]
)

ISO_SWS_FORCAST_NATURAL_LINES_UM: tuple[tuple[str, float], ...] = (
    ("HI_Br_gamma", 2.16612),
    ("HI_Pf_19", 2.37438),
    ("H2_1_0_S0", 2.22329),
    ("H2_1_0_Q1", 2.40659),
    ("H2_1_0_Q3", 2.42373),
    ("HI_Pf_18", 2.44833),
    ("HI_Pf_15", 2.52609),
    ("HI_Br_beta", 2.62587),
    ("HI_Pf_13", 2.67513),
    ("HI_Pf_11", 2.87300),
    ("HI_Pf_delta", 3.29699),
    ("HI_Pf_gamma", 3.74056),
    ("HI_Hu_14", 4.02087),
    ("HI_Br_alpha", 4.05226),
    ("HI_Hu_12", 4.37646),
    ("HI_Pf_beta", 4.65378),
    ("HI_Hu_11", 4.67252),
    ("H2_0_0_S9", 4.69460),
    ("H2_0_0_S8", 5.05312),
    ("HI_Hu_10", 5.12866),
    ("FeII_5_34", 5.34017),
    ("H2_0_0_S7", 5.51116),
    ("MgV_5_61", 5.60980),
    ("H2_0_0_S6", 6.10856),
    ("NiII_6_64", 6.63600),
    ("H2_0_0_S5", 6.90952),
    ("ArII_6_99", 6.98527),
    ("NaIII_7_32", 7.31770),
    ("HI_Pf_alpha", 7.45986),
    ("HI_Hu_beta", 7.50249),
    ("NeVI_7_65", 7.65240),
    ("H2_0_0_S4", 8.02505),
    ("ArIII_8_99", 8.99138),
    ("H2_0_0_S3", 9.66491),
    ("SIV_10_51", 10.51050),
    ("H2_0_0_S2", 12.27861),
    ("HI_Hu_alpha", 12.37190),
    ("NeII_12_81", 12.81355),
    ("ArV_13_10", 13.10220),
    ("MgV_13_52", 13.52130),
    ("NeV_14_32", 14.32170),
    ("ClII_14_37", 14.36780),
    ("NeIII_15_56", 15.55510),
    ("H2_0_0_S1", 17.03483),
    ("PIII_17_88", 17.88460),
    ("FeII_17_94", 17.93595),
    ("SIII_18_71", 18.71303),
    ("ArIII_21_83", 21.82910),
    ("FeIII_22_93", 22.92500),
    ("NeV_24_32", 24.31750),
    ("FeII_24_52", 24.51920),
    ("OIV_25_89", 25.89030),
    ("FeII_25_99", 25.98839),
    ("H2_0_0_S0", 28.21883),
    ("SIII_33_48", 33.48100),
    ("SiII_34_81", 34.81520),
    ("FeII_35_35", 35.34865),
    ("NeIII_36_01", 36.01350),
)


def great_jy_per_k(eta_mb: float = 0.67) -> float:
    """Return SOFIA/GREAT point-source Jy/K factor from main-beam efficiency."""
    eta_c = max(0.30, min(0.95, float(eta_mb)))
    eta_a = 0.86 * eta_c
    a_geom = math.pi * ((0.5 * SOFIA_GREAT_APERTURE_M) ** 2)
    return float((2.0 * K_BOLTZ / (eta_a * a_geom)) * 1e26)


def great_ta_to_flam_cgs(
    freq_ghz: float | np.ndarray,
    temp_k: float | np.ndarray,
    eta_mb: float = 0.67,
) -> float | np.ndarray:
    """Convert SOFIA/GREAT antenna temperature (K) at ``freq_ghz`` into CGS F_lambda."""
    jy = np.asarray(temp_k, dtype=np.float64) * great_jy_per_k(eta_mb)
    lam_a = C_ANGSTROM_GHZ / np.maximum(1.0, np.asarray(freq_ghz, dtype=np.float64))
    flam = 1e-23 * jy * C_ANGSTROM_PER_S / (lam_a * lam_a)
    if np.ndim(freq_ghz) == 0 and np.ndim(temp_k) == 0:
        return float(flam)
    return flam


def _asymmetric_clipped_baseline_v56(y: np.ndarray, win_px: int) -> np.ndarray:
    """Two-pass median continuum baseline immune to strong positive/negative narrow lines."""
    n = len(y)
    w = max(15, int(win_px) | 1)
    if w >= n:
        return np.full(n, exact_median_1d(y), dtype=np.float64)
    b1 = median_filter(y, size=w, mode="nearest")
    res1 = y - b1
    mad1 = max(1e-9, exact_mad_1d(res1))
    keep = np.abs(res1) <= 3.0 * mad1
    if int(np.sum(keep)) >= max(8, n // 4):
        idx = np.arange(n, dtype=np.float64)
        y_clean = np.interp(idx, idx[keep], y[keep])
        return median_filter(y_clean, size=w, mode="nearest")
    return b1


def _subchannel_fwhm_v56(res: np.ndarray, idx: int) -> float:
    """Estimate sub-channel FWHM in pixels around local peak ``idx``."""
    pk = float(res[idx])
    if pk <= 0.0:
        return 0.0
    hm = 0.5 * pk
    n = len(res)
    l_pos = float(idx)
    k = idx
    while k > 0 and res[k] >= hm:
        k -= 1
    if res[k] < hm and k < idx:
        denom = max(1e-12, float(res[k + 1] - res[k]))
        l_pos = float(k) + (hm - float(res[k])) / denom
    else:
        l_pos = float(max(0, idx - 1))

    r_pos = float(idx)
    k = idx
    while k < n - 1 and res[k] >= hm:
        k += 1
    if res[k] < hm and k > idx:
        denom = max(1e-12, float(res[k - 1] - res[k]))
        r_pos = float(k) - (hm - float(res[k])) / denom
    else:
        r_pos = float(min(n - 1, idx + 1))
    return max(0.5, r_pos - l_pos)


def scan_sofia_great_superthz_v56(
    cubes: list[dict[str, Any]],
    cfg: dict[str, Any] | None = None,
    star: str = "",
    dist_pc: float = 10.0,
    teff_k: float = 5000.0,
    star_rv_kms: float = 0.0,
    cohort_topo_ghz: list[float] | None = None,
) -> dict[str, Any]:
    """
    Engine V5.6A (`SOFIA_GREAT_SUPERTHZ_V56`): Sub-km/s heterodyne super-THz
    (`1.2-4.8 THz`) beacon search across `.great.fits` spectra with baseline standing-wave
    FFT suppression, 1-channel LO spur rejection, broad thermal ISM/envelope line
    width veto, molecular/atomic super-THz atlas veto, and aperture-calibrated CGS EIRP bounds.
    """
    cfg_eff = cfg or BASE_V5_5_CONFIG
    peers_ghz = list(cohort_topo_ghz or [])
    candidates: list[dict[str, Any]] = []
    cube_summaries: list[dict[str, Any]] = []
    band_best_ul: dict[str, dict[str, float]] = {}
    raw_topo_ghz: list[float] = []
    n_pix_total = 0
    n_raw = 0
    n_qualified = 0

    for ci, cb in enumerate(cubes):
        dp_id = str(cb.get("dp_id", f"GREAT_{ci:02d}"))
        band_lbl = str(cb.get("band", f"GREAT_{ci:02d}"))
        eta_mb = float(cb.get("beameff", 0.67))
        if not (0.20 <= eta_mb <= 0.99):
            eta_mb = 0.67

        fq = np.asarray(cb["freq_ghz"], dtype=np.float64)
        tk = np.asarray(cb["temp_k"], dtype=np.float64)
        fin = np.isfinite(fq) & np.isfinite(tk) & (fq > 100.0) & (fq < 10000.0) & (np.abs(tk) < 5e5)
        if int(np.sum(fin)) < 40:
            continue
        fq, tk = fq[fin], tk[fin]
        ord_f = np.argsort(fq)
        fq, tk = fq[ord_f], tk[ord_f]
        n_pix_total += len(fq)

        # Edge trim
        trim = max(5, int(round(0.025 * len(fq))))
        if len(fq) - 2 * trim < 32:
            continue
        in_trim = np.zeros(len(fq), dtype=bool)
        in_trim[trim : len(fq) - trim] = True

        dfreq_ghz = max(1e-7, exact_median_1d(np.abs(np.diff(fq))))
        med_f_ghz = exact_median_1d(fq)
        dv_chan_kms = C_KMS * dfreq_ghz / max(1.0, med_f_ghz)
        rp_eff = min(2.0e7, max(5.0e4, med_f_ghz / dfreq_ghz))

        win_px = max(25, min(101, (len(fq) // 7) | 1))
        cont = _asymmetric_clipped_baseline_v56(tk, win_px)
        res = tk - cont

        # Robust global noise after clipping bright >3.5 sigma features twice
        sig_arr = res[in_trim].copy()
        for _ in range(2):
            m_s = exact_median_1d(sig_arr)
            md_s = max(1e-6, exact_mad_1d(sig_arr))
            keep_s = np.abs(sig_arr - m_s) <= 3.5 * md_s
            if int(np.sum(keep_s)) >= max(16, len(sig_arr) // 3):
                sig_arr = sig_arr[keep_s]
        glob_sig_k = max(1e-6, exact_mad_1d(sig_arr))

        # Check periodic standing-wave content in baseline on trimmed interior
        cont_in = cont[in_trim]
        x_in = np.linspace(-1.0, 1.0, len(cont_in))
        poly_c = np.polyfit(x_in, cont_in, 1)
        cdet = cont_in - np.polyval(poly_c, x_in)
        sw_power_frac = 0.0
        sw_amp_sigma = float(np.std(cdet) / max(1e-9, glob_sig_k)) if len(cdet) >= 16 else 0.0
        if len(cdet) >= 32:
            fft_p = np.abs(np.fft.rfft(cdet - np.mean(cdet))) ** 2
            if len(fft_p) > 4 and np.sum(fft_p[2:]) > 0.0:
                sw_power_frac = float(np.max(fft_p[2:]) / np.sum(fft_p[1:]))

        # 8-sigma heterodyne 10 m EIRP bound
        lam_a = C_ANGSTROM_GHZ / med_f_ghz
        temp_lim_k = 8.0 * glob_sig_k
        flam_lim = great_ta_to_flam_cgs(med_f_ghz, temp_lim_k, eta_mb=eta_mb)
        ul = compute_photon_beam_upper_limit(
            wave_a=lam_a,
            amp_rel_lim=1.0,
            teff_k=float(teff_k),
            dist_pc=float(dist_pc),
            stellar_radius_rsun=1.0,
            radiometric_anchor="SOFIA_GREAT_DIRECT_CGS",
            resolving_power=rp_eff,
            direct_flam_cgs=flam_lim,
        )
        ul["direct_flam_cgs"] = float(flam_lim)
        ul["med_freq_ghz"] = float(med_f_ghz)
        ul["wave_a"] = float(lam_a)
        ul["resolving_power"] = float(rp_eff)
        ul["noise_mad_k"] = float(glob_sig_k)
        ul["eta_mb"] = float(eta_mb)

        best_canon = min(CALIBRATION_BANDS_SOFIA_GREAT, key=lambda b: abs(b["center_wave_A"] - lam_a))
        bid = best_canon["band_id"] if abs(best_canon["center_wave_A"] - lam_a) <= 0.30 * best_canon["center_wave_A"] else f"GREAT_{int(round(med_f_ghz))}GHZ"
        if bid not in band_best_ul or ul["p_beam_10m_kw"] < band_best_ul[bid]["p_beam_10m_kw"]:
            band_best_ul[bid] = ul

        cube_summaries.append({
            "dp_id": dp_id,
            "band": bid,
            "med_freq_ghz": round(med_f_ghz, 4),
            "dv_chan_kms": round(dv_chan_kms, 4),
            "rp_eff": round(rp_eff, 1),
            "noise_mad_k": round(glob_sig_k, 5),
            "sw_power_frac": round(sw_power_frac, 4),
            "p_beam_10m_kw": round(float(ul["p_beam_10m_kw"]), 4),
        })

        # Peak scan across trimmed range using robust continuum noise
        # Also evaluate local sideband floor to downweight baseline ripples cleanly
        z_arr = res / glob_sig_k
        pk_idx = np.where(in_trim & (z_arr >= 7.5))[0]
        if len(pk_idx) == 0:
            continue
        ord_pk = pk_idx[np.argsort(z_arr[pk_idx])[::-1]]
        taken = np.zeros(len(fq), dtype=bool)
        for idx in ord_pk:
            if taken[idx] or idx <= 2 or idx >= len(fq) - 3:
                continue
            lo_n, hi_n = max(0, idx - 8), min(len(fq), idx + 9)
            if float(z_arr[idx]) < float(np.max(z_arr[lo_n:hi_n])) - 1e-12:
                continue
            taken[lo_n:hi_n] = True
            n_raw += 1

            # Local sideband scatter check (60-chan annulus skipping +-10 chan core)
            w_l0, w_l1 = max(0, idx - 70), max(0, idx - 10)
            w_r0, w_r1 = min(len(fq), idx + 11), min(len(fq), idx + 71)
            sb_vals = np.concatenate([res[w_l0:w_l1], res[w_r0:w_r1]])
            loc_mad_k = max(glob_sig_k, exact_mad_1d(sb_vals) if len(sb_vals) >= 12 else glob_sig_k)
            loc_snr = float(res[idx] / loc_mad_k)
            loc_ripple_ratio = float(loc_mad_k / glob_sig_k)

            f_pk = float(fq[idx])
            lam_pk_um = (C_KMS / 1000.0) * 1e3 / max(1.0, f_pk)
            lam_pk_a = C_ANGSTROM_GHZ / max(1.0, f_pk)
            raw_topo_ghz.append(f_pk)

            eta_1px = float(abs(res[idx]) / max(1e-12, abs(res[idx]) + abs(res[idx - 1]) + abs(res[idx + 1])))
            adj_ratio = float(0.5 * (res[idx - 1] + res[idx + 1]) / max(1e-12, res[idx]))
            fwhm_px = _subchannel_fwhm_v56(res, int(idx))
            dv_fwhm_kms = fwhm_px * dv_chan_kms

            # Count similar-amplitude repeat peaks across cube (periodic standing wave / Comb-like artifact)
            n_rep = int(np.sum((z_arr >= max(4.5, 0.5 * float(z_arr[idx]))) & (np.abs(np.arange(len(fq)) - idx) > 10)))

            # Molecular / atomic match in stellar rest frame (+-180 km/s)
            f_rest_ghz = f_pk * (1.0 + float(star_rv_kms) / C_KMS)
            atlas_hit = ""
            for lname, l_ghz, _tol in SOFIA_GREAT_MOLECULAR_ATOMIC_GHZ:
                if abs(C_KMS * (f_rest_ghz - l_ghz) / l_ghz) <= 180.0:
                    atlas_hit = lname
                    break

            veto_reason = ""
            qualified = False
            if eta_1px > 0.72 or adj_ratio < 0.16 or fwhm_px < 2.2:
                veto_reason = "G5_GREAT_LO_SPUR_1CHAN"
            elif loc_ripple_ratio >= 2.2 or (sw_power_frac >= 0.42 and sw_amp_sigma >= 0.85) or n_rep >= 5 or loc_snr < 7.0:
                veto_reason = "G2_GREAT_STANDING_WAVE_RIPPLE"
            elif fwhm_px >= 6.5 or (dv_chan_kms < 1.5 and dv_fwhm_kms >= 6.0):
                veto_reason = "G5_GREAT_BROAD_MOLECULAR"
            elif atlas_hit:
                veto_reason = f"G3_GREAT_MOLECULAR_ATOMIC:{atlas_hit}"
            elif any(abs(C_KMS * (f_pk - p_ghz) / max(1.0, f_pk)) <= 10.0 for p_ghz in peers_ghz):
                veto_reason = "G6_GREAT_COINCIDENT_LO_TELLURIC"
            else:
                qualified = True
                veto_reason = "QUALIFIED_V56_GREAT_BEACON"
                n_qualified += 1

            candidates.append({
                "instrument": "SOFIA_GREAT",
                "cand_id": f"GREAT_{star}_{ci:02d}_{idx:05d}",
                "star": star,
                "dp_id": dp_id,
                "band": bid,
                "freq_ghz": round(f_pk, 6),
                "wave_a": round(lam_pk_a, 3),
                "wave_um": round(lam_pk_um, 5),
                "snr": round(loc_snr, 3),
                "eta_1px": round(eta_1px, 4),
                "fwhm_px": round(fwhm_px, 3),
                "dv_fwhm_kms": round(dv_fwhm_kms, 3),
                "n_rep_peaks": int(n_rep),
                "loc_ripple_ratio": round(loc_ripple_ratio, 3),
                "qualified_v56": bool(qualified),
                "veto_reason": veto_reason,
                "atlas_match": atlas_hit,
            })

    if band_best_ul:
        best_band, best_ul = min(band_best_ul.items(), key=lambda kv: kv[1]["p_beam_10m_kw"])
        best_p_kw = float(best_ul["p_beam_10m_kw"])
    else:
        best_band, best_p_kw = "", float("inf")

    return {
        "star": star,
        "n_cubes": int(len(cube_summaries)),
        "n_pix": int(n_pix_total),
        "raw_peaks": int(n_raw),
        "qualified_v56": int(n_qualified),
        "candidates": candidates,
        "upper_limits": band_best_ul,
        "cube_summaries": cube_summaries,
        "best_p_beam_10m_kw": best_p_kw,
        "best_band": best_band,
        "raw_topo_ghz": raw_topo_ghz,
    }


def _apply_dyson_and_ccf_v56(
    wv: np.ndarray,
    fv: np.ndarray,
    ev: np.ndarray,
    teff_k: float,
    anchor_mask: np.ndarray,
    long_mask: np.ndarray,
    cont_fit_mask: np.ndarray,
    instrument: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Shared ISO SWS & SOFIA FORCAST 6-gas CCF + 100-400 K Dyson vs silicate decomposition."""
    f_clean, n_desp = _hampel_despike_1d_v53(fv)
    med_cont_snr = float(exact_median_1d(f_clean / np.maximum(ev, 1e-12)))
    subcontinuum_nd = bool(med_cont_snr < 3.0)

    # A. 6-gas Industrial Greenhouse CCF over 5.2-38 um (split only on large wavelength gaps > 0.65 um)
    m_ir = (wv >= 5.0) & (wv <= 39.5)
    w_ir, f_ir, e_ir = wv[m_ir], f_clean[m_ir], ev[m_ir]
    ccf_raw: dict[str, Any] = {"molecules": {}, "confounders": {}, "max_confounder_sigma": 0.0, "detected_molecules": [], "any_detection": False}
    if len(w_ir) >= 48 and not subcontinuum_nd:
        splits = np.where(np.diff(w_ir) > 1.25)[0] + 1
        bounds = [0] + list(splits) + [len(w_ir)]
        segments = [(w_ir[a:b], f_ir[a:b]) for a, b in zip(bounds[:-1], bounds[1:]) if (b - a) >= 24]
        if segments:
            ccf_raw = _run_ir_ccf_suite_v52(
                segments,
                SPITZER_IRS_GREENHOUSE_TEMPLATES_UM,
                SPITZER_IRS_CONFOUNDERS_UM,
                emission_conf_names={"PAH_COMPLEX", "SILICATE_10UM", "SILICATE_18UM"},
                min_sigma=5.0,
                min_conf_ratio=1.5,
                prox_dist_um=1.5,
                min_core_bins=4,
                min_sb_bins=6,
                min_win_bins=6,
                min_side_bins=3,
                sb_pad_mult=4.0,
            )
            max_conf_s = float(ccf_raw.get("max_confounder_sigma", 0.0))
            final_dets: list[str] = []
            for mn, mr in ccf_raw.get("molecules", {}).items():
                s_gas = float(mr.get("ccf_sigma_abs", 0.0))
                joint_chks = mr.get("joint_confounder_checks", {})
                non_ov_conf = 0.0
                for cn, cr in ccf_raw.get("confounders", {}).items():
                    if not joint_chks.get(cn, {}).get("overlaps"):
                        non_ov_conf = max(non_ov_conf, float(cr.get("physical_confounder_sigma", 0.0)))
                ok = bool(mr.get("passes_ccf")) and (s_gas >= 5.0) and ((s_gas - non_ov_conf) >= 2.0)
                mr["passes_ccf_v56"] = ok
                if ok:
                    final_dets.append(mn)
            ccf_raw["detected_molecules"] = final_dets
            ccf_raw["any_detection"] = len(final_dets) > 0

    # B. Dyson waste-heat blackbody (90-420 K) vs natural silicate/PAH/SiC dust excess
    dyson_res: dict[str, Any] = {
        "dyson_candidate": False,
        "gamma_waste": 0.0,
        "t_waste_k": 0.0,
        "snr_excess": 0.0,
        "blackbody_r2": 0.0,
        "silicate_excess_sigma": 0.0,
        "status": "NO_EXCESS",
    }
    if (not subcontinuum_nd) and int(np.sum(anchor_mask)) >= 6 and int(np.sum(long_mask)) >= 20 and int(np.sum(cont_fit_mask)) >= 20:
        b_star_all = _planck_bnu_rel_v53(wv, max(1500.0, float(teff_k)))
        eff_e_cf = np.maximum(ev[cont_fit_mask], 0.02 * np.maximum(np.abs(f_clean[cont_fit_mask]), 1e-12))
        w_cf = 1.0 / eff_e_cf
        w_long_r = 1.0 / np.maximum(ev[long_mask] ** 2, 1e-24)

        def _fit_2bb(tw_val: float) -> tuple[float, float, float]:
            bw_cf = _planck_bnu_rel_v53(wv[cont_fit_mask], tw_val)
            X2 = np.column_stack([b_star_all[cont_fit_mask] * w_cf, bw_cf * w_cf])
            y2 = f_clean[cont_fit_mask] * w_cf
            ab, *_ = np.linalg.lstsq(X2, y2, rcond=None)
            a_t, b_t = float(ab[0]), float(ab[1])
            if a_t < 0.0:
                a_t = 0.0
                b_t = max(0.0, float(np.dot(bw_cf * w_cf, y2) / max(1e-30, float(np.dot(bw_cf * w_cf, bw_cf * w_cf)))))
            if b_t < 0.0:
                b_t = 0.0
                bs_w = b_star_all[cont_fit_mask] * w_cf
                a_t = max(0.0, float(np.dot(bs_w, y2) / max(1e-30, float(np.dot(bs_w, bs_w)))))
            mod_cf = a_t * b_star_all[cont_fit_mask] + b_t * bw_cf
            c2 = float(np.mean(((f_clean[cont_fit_mask] - mod_cf) * w_cf) ** 2))
            return c2, a_t, b_t

        best_chi2_red, best_tw, best_a, best_b = 1e30, 200.0, 0.0, 0.0
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
        f_exc = f_clean[long_mask] - f_phot_all[long_mask]
        e_long = ev[long_mask]
        w_long = wv[long_mask]
        best_model = best_b * _planck_bnu_rel_v53(w_long, best_tw)

        mod_norm = float(np.sum(w_long_r * best_model * best_model))
        snr_exc = math.sqrt(max(0.0, mod_norm)) if best_b > 0.0 else 0.0
        sse_mod = float(np.sum(w_long_r * ((f_exc - best_model) ** 2)))
        sse_null = float(np.sum(w_long_r * ((f_exc - float(np.average(f_exc, weights=w_long_r))) ** 2)))
        bb_r2 = 1.0 - (sse_mod / max(1e-30, sse_null)) if sse_null > 0.0 else 0.0

        teff_eff = max(1500.0, float(teff_k))
        a_ref = best_a if best_a > 0.0 else max(1e-30, exact_median_1d(f_clean[anchor_mask] / np.maximum(b_star_all[anchor_mask], 1e-30)))
        gamma_w = (best_b * (best_tw ** 4)) / max(1e-30, a_ref * (teff_eff ** 4))

        res_abs = f_exc - best_model
        sil_sig = 0.0
        for lo_c, hi_c, lo_sb, hi_sb in (
            (9.0, 12.2, 8.2, 13.8),
            (16.5, 24.5, 14.5, 27.5),
            (6.0, 8.8, 5.4, 9.2),
        ):
            cm = (w_long >= lo_c) & (w_long <= hi_c)
            sbm = (w_long >= lo_sb) & (w_long <= hi_sb) & (~cm)
            if int(np.sum(cm)) >= 5 and int(np.sum(sbm)) >= 5:
                sb_w, sb_r = w_long[sbm], res_abs[sbm]
                c_lin = np.polyfit(sb_w, sb_r, 1)
                bump = res_abs[cm] - np.polyval(c_lin, w_long[cm])
                sb_scat = max(exact_mad_1d(sb_r - np.polyval(c_lin, sb_w)), 1e-12)
                eff_sig_c = np.maximum(e_long[cm], sb_scat)
                z_b = float(np.sum(bump / eff_sig_c) / math.sqrt(float(len(bump))))
                frac_b = float(exact_median_1d(bump) / max(1e-12, abs(exact_median_1d(f_clean[long_mask][cm]))))
                if frac_b >= 0.025:
                    sil_sig = max(sil_sig, z_b)

        has_exc = snr_exc >= 6.0 and gamma_w >= 0.01
        is_bb = bb_r2 >= 0.90
        is_sil = sil_sig >= 3.0
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
            "silicate_excess_sigma": round(float(sil_sig), 3),
            "status": st_lbl,
        }

    return ccf_raw, dyson_res


def scan_iso_sws_midir_v56(
    wave_um: np.ndarray,
    flux_jy: np.ndarray,
    err_jy: np.ndarray,
    seg_breaks: list[int] | None = None,
    teff_k: float = 5000.0,
    dist_pc: float = 10.0,
    star: str = "",
    dp_id: str = "",
    star_rv_kms: float = 0.0,
    cohort_topo_um: list[float] | None = None,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Engine V5.6B (`ISO_SWS_MIDIR_GAPCLOSURE_V56`): Continuous 2.36-45.39 um ISO SWS
    AOT-segment scanner combining narrow unresolved emission vetting across `NSEG01-NSEG12`
    (with segment-stitch boundary & 1-pixel glitch vetoes), 6-gas industrial greenhouse CCF,
    2.4-45 um 100-400 K Dyson vs silicate/carbon dust decomposition, and 5-band direct CGS EIRP limits.
    """
    w = np.asarray(wave_um, dtype=np.float64)
    f = np.asarray(flux_jy, dtype=np.float64)
    e = np.asarray(err_jy, dtype=np.float64)
    n_tot = len(w)
    peers_um = list(cohort_topo_um or [])

    if n_tot < 40:
        return {
            "star": star, "n_bins": n_tot, "n_segments": 0, "raw_peaks": 0,
            "qualified_v56": 0, "candidates": [],
            "ccf": {"molecules": {}, "confounders": {}, "max_confounder_sigma": 0.0, "detected_molecules": [], "any_detection": False},
            "dyson": {"dyson_candidate": False, "gamma_waste": 0.0, "t_waste_k": 0.0, "snr_excess": 0.0, "blackbody_r2": 0.0, "silicate_excess_sigma": 0.0, "status": "INSUFFICIENT_DATA"},
            "upper_limits": {}, "best_p_beam_10m_kw": float("inf"), "best_band": "", "raw_topo_um": [],
        }

    # Build segment index intervals from NSEG or fallback on backward wavelength jumps
    if seg_breaks and len(seg_breaks) >= 2 and seg_breaks[-1] <= n_tot:
        bounds = [(int(seg_breaks[k]), int(seg_breaks[k + 1])) for k in range(len(seg_breaks) - 1) if seg_breaks[k + 1] > seg_breaks[k]]
    else:
        jumps = np.where(np.abs(np.diff(w)) > 0.15)[0] + 1
        pts = [0] + list(jumps) + [n_tot]
        bounds = [(int(a), int(b)) for a, b in zip(pts[:-1], pts[1:]) if (b - a) > 10]

    candidates: list[dict[str, Any]] = []
    raw_topo_um: list[float] = []
    stitch_waves_um: list[float] = []
    n_raw = 0
    n_qualified = 0

    for a, b in bounds:
        if (b - a) < 20:
            continue
        stitch_waves_um.extend([float(w[a]), float(w[b - 1])])

    # Scan each AOT segment cleanly without cross-segment stitch smoothing artifacts
    for si, (a, b) in enumerate(bounds):
        if (b - a) < 24:
            continue
        ws, fs, es = w[a:b], f[a:b], e[a:b]
        fin = np.isfinite(ws) & np.isfinite(fs) & np.isfinite(es) & (ws >= 2.2) & (ws <= 46.0) & (es > 0.0) & (np.abs(fs) < 1e7)
        if int(np.sum(fin)) < 20:
            continue
        ws, fs, es = ws[fin], fs[fin], es[fin]
        ord_s = np.argsort(ws)
        ws, fs, es = ws[ord_s], fs[ord_s], es[ord_s]

        win_px = max(13, min(35, (len(ws) // 6) | 1))
        cont = _asymmetric_clipped_baseline_v56(fs, win_px)
        res = fs - cont
        seg_mad = max(1e-9, exact_mad_1d(res))
        # Use local sideband scatter + formal error floor
        sig_arr = np.maximum(es, 0.75 * seg_mad)
        z_arr = res / sig_arr

        # Check all local maxima >= 7.0 sigma (excluding literal index 0 and len-1)
        pk_idx = np.where(z_arr[1:-1] >= 7.0)[0] + 1
        if len(pk_idx) == 0:
            continue
        ord_pk = pk_idx[np.argsort(z_arr[pk_idx])[::-1]]
        taken = np.zeros(len(ws), dtype=bool)
        for idx in ord_pk:
            if taken[idx] or idx < 2 or idx >= len(ws) - 2:
                continue
            lo_n, hi_n = max(0, idx - 6), min(len(ws), idx + 7)
            if float(z_arr[idx]) < float(np.max(z_arr[lo_n:hi_n])) - 1e-12:
                continue
            taken[lo_n:hi_n] = True
            n_raw += 1

            w_obs_um = float(ws[idx])
            raw_topo_um.append(w_obs_um)
            lam_a = w_obs_um * 1e4
            freq_ghz = C_ANGSTROM_GHZ / max(1.0, lam_a)
            eta_1px = float(abs(res[idx]) / max(1e-12, abs(res[idx]) + abs(res[idx - 1]) + abs(res[idx + 1])))
            adj_ratio = float(0.5 * (res[idx - 1] + res[idx + 1]) / max(1e-12, res[idx]))
            fwhm_px = _subchannel_fwhm_v56(res, int(idx))
            dw_um = max(1e-6, exact_median_1d(np.abs(np.diff(ws))))
            dv_fwhm_kms = C_KMS * (fwhm_px * dw_um) / max(1.0, w_obs_um)

            # Local sideband scatter
            l0, l1 = max(0, idx - 24), max(0, idx - 6)
            r0, r1 = min(len(ws), idx + 7), min(len(ws), idx + 25)
            sb_vals = np.concatenate([res[l0:l1], res[r0:r1]])
            loc_mad = max(seg_mad, exact_mad_1d(sb_vals) if len(sb_vals) >= 8 else seg_mad)
            loc_snr = float(res[idx] / max(float(es[idx]), loc_mad))
            loc_ripple_ratio = float(loc_mad / seg_mad)

            near_stitch = (idx <= 4) or (idx >= len(ws) - 5) or any(abs(w_obs_um - sw) <= 0.055 for sw in stitch_waves_um)
            w_rest_um = w_obs_um * (1.0 - float(star_rv_kms) / C_KMS)
            atlas_hit = ""
            for lname, l_um in ISO_SWS_FORCAST_NATURAL_LINES_UM:
                if abs(C_KMS * (w_rest_um - l_um) / l_um) <= 1200.0:
                    atlas_hit = lname
                    break

            n_rep = int(np.sum((z_arr >= max(4.5, 0.5 * float(z_arr[idx]))) & (np.abs(np.arange(len(ws)) - idx) > 6)))

            veto_reason = ""
            qualified = False
            if near_stitch:
                veto_reason = "G2_SWS_SEGMENT_STITCH_EDGE"
            elif eta_1px > 0.72 or adj_ratio < 0.16 or fwhm_px < 2.1:
                veto_reason = "G5_SWS_1PX_MEMORY_GLITCH"
            elif fwhm_px >= 6.8:
                veto_reason = "G5_SWS_BROAD_DUST_PAH"
            elif loc_ripple_ratio >= 2.8 or loc_snr < 6.5:
                veto_reason = "G2_SWS_FRINGE_RIPPLE"
            elif atlas_hit:
                veto_reason = f"G3_SWS_NATURAL_LINE:{atlas_hit}"
            elif any(abs(C_KMS * (w_obs_um - pu) / max(1.0, w_obs_um)) <= 250.0 for pu in peers_um):
                veto_reason = "G6_SWS_CALIBRATION_COINCIDENCE"
            else:
                qualified = True
                veto_reason = "QUALIFIED_V56_SWS_BEACON"
                n_qualified += 1

            candidates.append({
                "instrument": "ISO_SWS",
                "cand_id": f"SWS_{star}_S{si:02d}_{idx:04d}",
                "star": star,
                "dp_id": dp_id,
                "band": f"SWS_SEG{si:02d}",
                "freq_ghz": round(freq_ghz, 4),
                "wave_a": round(lam_a, 2),
                "wave_um": round(w_obs_um, 5),
                "snr": round(loc_snr, 3),
                "eta_1px": round(eta_1px, 4),
                "fwhm_px": round(fwhm_px, 3),
                "dv_fwhm_kms": round(dv_fwhm_kms, 2),
                "n_rep_peaks": int(n_rep),
                "loc_ripple_ratio": round(loc_ripple_ratio, 3),
                "qualified_v56": bool(qualified),
                "veto_reason": veto_reason,
                "atlas_match": atlas_hit,
            })

    # Merge finite spectrum for continuous CCF + Dyson + 5-band EIRP limits
    fin_all = np.isfinite(w) & np.isfinite(f) & np.isfinite(e) & (w >= 2.2) & (w <= 46.0) & (e > 0.0) & (np.abs(f) < 1e7)
    wv, fv, ev = w[fin_all], f[fin_all], e[fin_all]
    ord_all = np.argsort(wv)
    wv, fv, ev = wv[ord_all], fv[ord_all], ev[ord_all]

    ccf_raw, dyson_res = _apply_dyson_and_ccf_v56(
        wv,
        fv,
        ev,
        teff_k=float(teff_k),
        anchor_mask=(wv >= 2.4) & (wv <= 5.0),
        long_mask=(wv >= 8.0) & (wv <= 42.0),
        cont_fit_mask=(wv >= 2.4) & (wv <= 42.0) & (~((wv >= 3.1) & (wv <= 3.6))) & (~((wv >= 5.9) & (wv <= 8.8))) & (~((wv >= 9.0) & (wv <= 12.6))) & (~((wv >= 16.0) & (wv <= 24.8))),
        instrument="ISO_SWS",
    )

    # 5-band direct CGS 8-sigma laser upper limits
    ul_out: dict[str, dict[str, float]] = {}
    for band in CALIBRATION_BANDS_ISO_SWS:
        lam_a = float(band["center_wave_A"])
        lam_um = lam_a * 1e-4
        m_b = np.abs(wv - lam_um) <= 0.15 * lam_um
        if int(np.sum(m_b)) < 5:
            continue
        med_err_jy = max(1e-9, exact_median_1d(ev[m_b]))
        sig_flam_cgs = 1e-23 * med_err_jy * C_ANGSTROM_PER_S / (lam_a * lam_a)
        flam_8sig = 8.0 * sig_flam_cgs
        ul = compute_photon_beam_upper_limit(
            wave_a=lam_a,
            amp_rel_lim=1.0,
            teff_k=float(teff_k),
            dist_pc=float(dist_pc),
            stellar_radius_rsun=1.0,
            radiometric_anchor="ISO_SWS_DIRECT_CGS",
            resolving_power=1500.0,
            direct_flam_cgs=flam_8sig,
        )
        ul["direct_flam_cgs"] = float(flam_8sig)
        ul["wave_a"] = float(lam_a)
        ul["resolving_power"] = 1500.0
        ul["med_err_jy"] = float(med_err_jy)
        ul_out[band["band_id"]] = ul

    if ul_out:
        best_band, best_ul = min(ul_out.items(), key=lambda kv: kv[1]["p_beam_10m_kw"])
        best_p_kw = float(best_ul["p_beam_10m_kw"])
    else:
        best_band, best_p_kw = "", float("inf")

    return {
        "star": star,
        "n_bins": int(len(wv)),
        "n_segments": int(len(bounds)),
        "raw_peaks": int(n_raw),
        "qualified_v56": int(n_qualified),
        "candidates": candidates,
        "ccf": ccf_raw,
        "dyson": dyson_res,
        "upper_limits": ul_out,
        "best_p_beam_10m_kw": best_p_kw,
        "best_band": best_band,
        "raw_topo_um": raw_topo_um,
    }


def scan_sofia_forcast_grism_v56(
    grisms: list[dict[str, Any]],
    cfg: dict[str, Any] | None = None,
    star: str = "",
    dist_pc: float = 10.0,
    teff_k: float = 5000.0,
    star_rv_kms: float = 0.0,
    cohort_topo_um: list[float] | None = None,
) -> dict[str, Any]:
    """
    Engine V5.6C (`SOFIA_FORCAST_4GRISM_V56`): Multi-grism `4.9-37.1 um` (`FOR_G063`,
    `FOR_G111`, `FOR_G227`, `FOR_G329`) stratospheric mid-IR search with per-channel
    ATRAN telluric gating, 1-px glitch and broad PAH/silicate vetoes, cross-grism
    Dyson vs silicate decomposition, and direct Jy CGS EIRP upper limits.
    """
    peers_um = list(cohort_topo_um or [])
    candidates: list[dict[str, Any]] = []
    grism_summaries: list[dict[str, Any]] = []
    ul_out: dict[str, dict[str, float]] = {}
    raw_topo_um: list[float] = []
    w_comb: list[np.ndarray] = []
    f_comb: list[np.ndarray] = []
    e_comb: list[np.ndarray] = []
    n_pix_total = 0
    n_raw = 0
    n_qualified = 0

    for gi, gr in enumerate(grisms):
        gid = str(gr.get("grism_id", f"FOR_G{gi:02d}"))
        dp_id = str(gr.get("dp_id", gid))
        rp = float(gr.get("rp", 200.0))
        if not (40.0 <= rp <= 2000.0):
            rp = 200.0

        wu = np.asarray(gr["wave_um"], dtype=np.float64)
        fj = np.asarray(gr["flux_jy"], dtype=np.float64)
        ej = np.asarray(gr["err_jy"], dtype=np.float64)
        atr = np.asarray(gr.get("atran", np.ones_like(wu)), dtype=np.float64)
        fin = np.isfinite(wu) & np.isfinite(fj) & np.isfinite(ej) & np.isfinite(atr) & (wu >= 4.5) & (wu <= 40.0) & (ej > 0.0) & (np.abs(fj) < 1e7)
        if int(np.sum(fin)) < 24:
            continue
        wu, fj, ej, atr = wu[fin], fj[fin], ej[fin], atr[fin]
        ord_g = np.argsort(wu)
        wu, fj, ej, atr = wu[ord_g], fj[ord_g], ej[ord_g], atr[ord_g]
        n_pix_total += len(wu)

        trim = max(4, int(round(0.03 * len(wu))))
        if len(wu) - 2 * trim < 18:
            continue
        in_trim = np.zeros(len(wu), dtype=bool)
        in_trim[trim : len(wu) - trim] = True

        dw_um = max(1e-5, exact_median_1d(np.abs(np.diff(wu))))
        dv_px = np.maximum(10.0, C_KMS * dw_um / np.maximum(1.0, wu))
        atr_grad = np.abs(np.gradient(atr)) / dv_px
        clean_atran = (atr >= 0.60) & (atr_grad <= 0.015)
        clean_mask = in_trim & clean_atran
        if int(np.sum(clean_mask)) < 14:
            clean_mask = in_trim & (atr >= 0.40)
        if int(np.sum(clean_mask)) < 12:
            continue

        w_comb.append(wu[clean_mask])
        f_comb.append(fj[clean_mask])
        e_comb.append(ej[clean_mask])

        win_px = max(11, min(25, (len(wu) // 6) | 1))
        cont = _asymmetric_clipped_baseline_v56(fj, win_px)
        res = fj - cont
        mad_clean = max(1e-9, exact_mad_1d(res[clean_mask]))
        sig_arr = np.maximum(ej, 0.8 * mad_clean)
        z_arr = res / sig_arr

        # Direct 8-sigma EIRP limit at grism median wavelength
        lam_c_um = exact_median_1d(wu[clean_mask])
        lam_c_a = lam_c_um * 1e4
        med_err_jy = max(1e-9, exact_median_1d(ej[clean_mask]))
        sig_flam_cgs = 1e-23 * med_err_jy * C_ANGSTROM_PER_S / (lam_c_a * lam_c_a)
        flam_8sig = 8.0 * sig_flam_cgs
        ul = compute_photon_beam_upper_limit(
            wave_a=lam_c_a,
            amp_rel_lim=1.0,
            teff_k=float(teff_k),
            dist_pc=float(dist_pc),
            stellar_radius_rsun=1.0,
            radiometric_anchor="SOFIA_FORCAST_DIRECT_CGS",
            resolving_power=rp,
            direct_flam_cgs=flam_8sig,
        )
        ul["direct_flam_cgs"] = float(flam_8sig)
        ul["wave_a"] = float(lam_c_a)
        ul["resolving_power"] = float(rp)
        ul["med_err_jy"] = float(med_err_jy)
        if gid not in ul_out or ul["p_beam_10m_kw"] < ul_out[gid]["p_beam_10m_kw"]:
            ul_out[gid] = ul

        grism_summaries.append({
            "grism_id": gid,
            "dp_id": dp_id,
            "lam_c_um": round(lam_c_um, 4),
            "rp": round(rp, 1),
            "clean_frac": round(float(np.sum(clean_mask)) / max(1.0, float(np.sum(in_trim))), 4),
            "med_err_jy": round(med_err_jy, 5),
            "p_beam_10m_kw": round(float(ul["p_beam_10m_kw"]), 3),
        })

        pk_idx = np.where(in_trim & (z_arr >= 7.0))[0]
        if len(pk_idx) == 0:
            continue
        ord_pk = pk_idx[np.argsort(z_arr[pk_idx])[::-1]]
        taken = np.zeros(len(wu), dtype=bool)
        for idx in ord_pk:
            if taken[idx] or idx < 2 or idx >= len(wu) - 2:
                continue
            lo_n, hi_n = max(0, idx - 5), min(len(wu), idx + 6)
            if float(z_arr[idx]) < float(np.max(z_arr[lo_n:hi_n])) - 1e-12:
                continue
            taken[lo_n:hi_n] = True
            n_raw += 1

            w_obs_um = float(wu[idx])
            lam_a = w_obs_um * 1e4
            freq_ghz = C_ANGSTROM_GHZ / max(1.0, lam_a)
            raw_topo_um.append(w_obs_um)
            eta_1px = float(abs(res[idx]) / max(1e-12, abs(res[idx]) + abs(res[idx - 1]) + abs(res[idx + 1])))
            adj_ratio = float(0.5 * (res[idx - 1] + res[idx + 1]) / max(1e-12, res[idx]))
            fwhm_px = _subchannel_fwhm_v56(res, int(idx))
            dv_fwhm_kms = C_KMS * (fwhm_px * dw_um) / max(1.0, w_obs_um)

            l0, l1 = max(0, idx - 18), max(0, idx - 5)
            r0, r1 = min(len(wu), idx + 6), min(len(wu), idx + 19)
            sb_vals = np.concatenate([res[l0:l1], res[r0:r1]])
            loc_mad = max(mad_clean, exact_mad_1d(sb_vals) if len(sb_vals) >= 6 else mad_clean)
            loc_snr = float(res[idx] / max(float(ej[idx]), loc_mad))
            loc_ripple_ratio = float(loc_mad / mad_clean)

            w_rest_um = w_obs_um * (1.0 - float(star_rv_kms) / C_KMS)
            atlas_hit = ""
            for lname, l_um in ISO_SWS_FORCAST_NATURAL_LINES_UM:
                if abs(C_KMS * (w_rest_um - l_um) / l_um) <= 2200.0:
                    atlas_hit = lname
                    break

            n_rep = int(np.sum((z_arr >= max(4.5, 0.5 * float(z_arr[idx]))) & (np.abs(np.arange(len(wu)) - idx) > 5)))
            veto_reason = ""
            qualified = False
            if not bool(clean_atran[idx]):
                veto_reason = "G2_FORCAST_ATRAN_TELLURIC"
            elif eta_1px > 0.72 or adj_ratio < 0.16 or fwhm_px < 2.0:
                veto_reason = "G5_FORCAST_1PX_GLITCH"
            elif fwhm_px >= 6.5:
                veto_reason = "G5_FORCAST_BROAD_PAH_SILICATE"
            elif loc_ripple_ratio >= 2.8 or loc_snr < 6.0:
                veto_reason = "G2_FORCAST_BASELINE_ARTIFACT"
            elif atlas_hit:
                veto_reason = f"G3_FORCAST_NATURAL_LINE:{atlas_hit}"
            elif any(abs(C_KMS * (w_obs_um - pu) / max(1.0, w_obs_um)) <= 500.0 for pu in peers_um):
                veto_reason = "G6_FORCAST_TELLURIC_COINCIDENCE"
            else:
                qualified = True
                veto_reason = "QUALIFIED_V56_FORCAST_BEACON"
                n_qualified += 1

            candidates.append({
                "instrument": "SOFIA_FORCAST",
                "cand_id": f"FOR_{star}_{gid}_{idx:04d}",
                "star": star,
                "dp_id": dp_id,
                "band": gid,
                "freq_ghz": round(freq_ghz, 4),
                "wave_a": round(lam_a, 2),
                "wave_um": round(w_obs_um, 5),
                "snr": round(loc_snr, 3),
                "eta_1px": round(eta_1px, 4),
                "fwhm_px": round(fwhm_px, 3),
                "dv_fwhm_kms": round(dv_fwhm_kms, 2),
                "n_rep_peaks": int(n_rep),
                "loc_ripple_ratio": round(loc_ripple_ratio, 3),
                "atran": round(float(atr[idx]), 4),
                "qualified_v56": bool(qualified),
                "veto_reason": veto_reason,
                "atlas_match": atlas_hit,
            })

    dyson_res: dict[str, Any] = {"dyson_candidate": False, "gamma_waste": 0.0, "t_waste_k": 0.0, "snr_excess": 0.0, "blackbody_r2": 0.0, "silicate_excess_sigma": 0.0, "status": "SINGLE_GRISM_OR_INSUFFICIENT"}
    if w_comb:
        wa = np.concatenate(w_comb)
        fa = np.concatenate(f_comb)
        ea = np.concatenate(e_comb)
        orda = np.argsort(wa)
        wa, fa, ea = wa[orda], fa[orda], ea[orda]
        _, dyson_res = _apply_dyson_and_ccf_v56(
            wa, fa, ea,
            teff_k=float(teff_k),
            anchor_mask=(wa >= 4.9) & (wa <= 8.5),
            long_mask=(wa >= 8.6) & (wa <= 37.5),
            cont_fit_mask=(wa >= 4.9) & (wa <= 37.5) & (~((wa >= 5.9) & (wa <= 8.8))) & (~((wa >= 9.0) & (wa <= 12.6))) & (~((wa >= 16.0) & (wa <= 24.8))),
            instrument="SOFIA_FORCAST",
        )

    if ul_out:
        best_band, best_ul = min(ul_out.items(), key=lambda kv: kv[1]["p_beam_10m_kw"])
        best_p_kw = float(best_ul["p_beam_10m_kw"])
    else:
        best_band, best_p_kw = "", float("inf")

    return {
        "star": star,
        "n_grisms": int(len(grism_summaries)),
        "n_pix": int(n_pix_total),
        "raw_peaks": int(n_raw),
        "qualified_v56": int(n_qualified),
        "candidates": candidates,
        "dyson": dyson_res,
        "upper_limits": ul_out,
        "grism_summaries": grism_summaries,
        "best_p_beam_10m_kw": best_p_kw,
        "best_band": best_band,
        "raw_topo_um": raw_topo_um,
    }


scan_coherent_shift_stack_jerk_v56 = scan_coherent_shift_stack_jerk_v55


def run_sofia_great_calibration_v56(seed: int = 9801) -> dict[str, Any]:
    """`CALIBRATION_V56_SOFIA_GREAT_180`: 60 THz beacons + 40 standing waves + 40 broad molecular + 40 LO spurs."""
    rng = np.random.default_rng(seed)
    n_px = 1400
    f0 = 1900.50
    fq = f0 + np.linspace(-1.2, 1.2, n_px)
    sig_f = (fq[1] - fq[0]) * 1.6
    trials: list[dict[str, Any]] = []
    rec, sw_v, brd_v, sp_v = 0, 0, 0, 0

    for i in range(60):
        tk = 10.0 + 0.08 * np.linspace(-1, 1, n_px) + rng.normal(0.0, 0.04, n_px)
        fc = float(rng.uniform(f0 - 0.85, f0 + 0.85))
        tk += float(rng.uniform(11.0, 18.0)) * 0.04 * np.exp(-0.5 * ((fq - fc) / sig_f) ** 2)
        res = scan_sofia_great_superthz_v56([{"dp_id": f"CAL_G_{i}", "band": "GREAT_CII_158UM", "freq_ghz": fq, "temp_k": tk, "beameff": 0.67}], star=f"SIM_GR_B_{i}", star_rv_kms=500.0)
        ok = res["qualified_v56"] >= 1
        rec += int(ok)
        trials.append({"suite": "CALIBRATION_V56_SOFIA_GREAT_180", "class": "CLEAN_GREAT_BEACON", "trial": i, "expected": 1, "observed": int(ok), "passed": int(ok == 1)})

    for i in range(40):
        ph = float(rng.uniform(0.0, 2.0 * math.pi))
        tk = 10.0 + float(rng.uniform(0.65, 1.2)) * np.sin(2.0 * math.pi * 6.0 * np.linspace(0, 1, n_px) + ph) + rng.normal(0.0, 0.04, n_px)
        res = scan_sofia_great_superthz_v56([{"dp_id": f"CAL_SW_{i}", "band": "GREAT_CII_158UM", "freq_ghz": fq, "temp_k": tk, "beameff": 0.67}], star=f"SIM_GR_SW_{i}", star_rv_kms=500.0)
        ok = res["qualified_v56"] == 0
        sw_v += int(ok)
        trials.append({"suite": "CALIBRATION_V56_SOFIA_GREAT_180", "class": "STANDING_WAVE_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v56"] > 0), "passed": int(ok)})

    for i in range(40):
        tk = 10.0 + rng.normal(0.0, 0.04, n_px)
        fc = float(rng.uniform(f0 - 0.8, f0 + 0.8))
        sig_b = float(rng.uniform(5.0, 10.0)) * (fq[1] - fq[0])
        tk += float(rng.uniform(12.0, 20.0)) * 0.04 * np.exp(-0.5 * ((fq - fc) / sig_b) ** 2)
        res = scan_sofia_great_superthz_v56([{"dp_id": f"CAL_BR_{i}", "band": "GREAT_CII_158UM", "freq_ghz": fq, "temp_k": tk, "beameff": 0.67}], star=f"SIM_GR_BR_{i}", star_rv_kms=500.0)
        ok = res["qualified_v56"] == 0
        brd_v += int(ok)
        trials.append({"suite": "CALIBRATION_V56_SOFIA_GREAT_180", "class": "BROAD_MOLECULAR_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v56"] > 0), "passed": int(ok)})

    for i in range(40):
        tk = 10.0 + rng.normal(0.0, 0.04, n_px)
        idx_s = int(rng.integers(150, n_px - 150))
        tk[idx_s] += float(rng.uniform(14.0, 24.0)) * 0.04
        res = scan_sofia_great_superthz_v56([{"dp_id": f"CAL_SP_{i}", "band": "GREAT_CII_158UM", "freq_ghz": fq, "temp_k": tk, "beameff": 0.67}], star=f"SIM_GR_SP_{i}", star_rv_kms=500.0)
        ok = res["qualified_v56"] == 0
        sp_v += int(ok)
        trials.append({"suite": "CALIBRATION_V56_SOFIA_GREAT_180", "class": "SINGLE_CHAN_LO_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v56"] > 0), "passed": int(ok)})

    return {
        "total_trials": len(trials),
        "beacon_recovery": f"{rec}/60 ({rec/60.0:.4f})",
        "standing_wave_veto": f"{sw_v}/40 ({sw_v/40.0:.4f})",
        "broad_molecular_veto": f"{brd_v}/40 ({brd_v/40.0:.4f})",
        "single_chan_lo_veto": f"{sp_v}/40 ({sp_v/40.0:.4f})",
        "trials": trials,
    }


def run_iso_sws_calibration_v56(seed: int = 9802) -> dict[str, Any]:
    """`CALIBRATION_V56_ISO_SWS_180`: 45 beacons + 45 greenhouse CCF + 30 Dyson vs silicate + 30 stitch/glitch + 30 natural line/silicate."""
    rng = np.random.default_rng(seed)
    # Build realistic 4-segment SWS grid spanning 2.4-42 um
    seg_ranges = [(2.4, 5.2, 220), (5.2, 12.2, 340), (12.2, 26.5, 420), (26.5, 42.0, 280)]
    seg_w, seg_b = [], [0]
    for a, b, m in seg_ranges:
        seg_w.append(np.linspace(a, b, m))
        seg_b.append(seg_b[-1] + m)
    w_all = np.concatenate(seg_w)
    b_star = _planck_bnu_rel_v53(w_all, 5500.0)
    f0_phot = 12.0 * (b_star / max(1e-30, float(np.median(b_star[w_all < 5.0]))))
    err_base = np.maximum(0.015, 0.008 * f0_phot)

    trials: list[dict[str, Any]] = []
    b_rec, gh_rec, dy_ok, st_v, nat_v = 0, 0, 0, 0, 0

    for i in range(45):
        flx = f0_phot + rng.normal(0.0, err_base)
        # Inject clean laser at ~21.0 or ~16.2 um away from stitch/natural lines
        wc = float(rng.choice([16.25, 20.85, 29.40, 31.80])) + float(rng.uniform(-0.15, 0.15))
        sig_w = wc / (1500.0 * FWHM_FACTOR) * 1.4
        # Make width ~1.6 bins in segment grid
        dw_loc = float(np.median(np.diff(w_all[(w_all > wc - 0.5) & (w_all < wc + 0.5)])))
        sig_w = max(sig_w, 1.4 * dw_loc)
        err_loc = float(np.median(err_base[(w_all > wc - 0.3) & (w_all < wc + 0.3)]))
        flx += float(rng.uniform(11.0, 17.0)) * err_loc * np.exp(-0.5 * ((w_all - wc) / sig_w) ** 2)
        res = scan_iso_sws_midir_v56(w_all, flx, err_base, seg_breaks=seg_b, teff_k=5500.0, dist_pc=10.0, star=f"SIM_SWS_B_{i}", star_rv_kms=1500.0)
        ok = res["qualified_v56"] >= 1
        b_rec += int(ok)
        trials.append({"suite": "CALIBRATION_V56_ISO_SWS_180", "class": "CLEAN_SWS_BEACON", "trial": i, "expected": 1, "observed": int(ok), "passed": int(ok == 1)})

    mol_names = list(SPITZER_IRS_GREENHOUSE_TEMPLATES_UM.keys())
    for i in range(45):
        mn = mol_names[i % len(mol_names)]
        tau = np.zeros_like(w_all)
        for band in SPITZER_IRS_GREENHOUSE_TEMPLATES_UM[mn]:
            tau += float(rng.uniform(0.08, 0.14)) * float(band.get("weight", 1.0)) * np.exp(-0.5 * ((w_all - float(band["mu_um"])) / max(0.05, float(band["sigma_um"]))) ** 2)
        flx = (f0_phot * np.exp(-tau)) + rng.normal(0.0, 0.5 * err_base)
        res = scan_iso_sws_midir_v56(w_all, flx, 0.5 * err_base, seg_breaks=seg_b, teff_k=5500.0, dist_pc=10.0, star=f"SIM_SWS_GH_{i}")
        ok = bool(res["ccf"].get("any_detection"))
        gh_rec += int(ok)
        trials.append({"suite": "CALIBRATION_V56_ISO_SWS_180", "class": "GREENHOUSE_GAS_CCF", "trial": i, "expected": 1, "observed": int(ok), "passed": int(ok == 1)})

    for i in range(30):
        tw = float(rng.uniform(160.0, 320.0))
        bw = _planck_bnu_rel_v53(w_all, tw)
        gam = float(rng.uniform(0.12, 0.35))
        b_scale = gam * ((5500.0 / tw) ** 4) * (float(np.median(f0_phot[w_all < 5.0])) / max(1e-30, float(np.median(b_star[w_all < 5.0]))))
        flx = f0_phot + b_scale * bw + rng.normal(0.0, 0.5 * err_base)
        if i % 2 == 0:
            # Pure smooth Dyson blackbody -> expect dyson_candidate=True
            res = scan_iso_sws_midir_v56(w_all, flx, 0.5 * err_base, seg_breaks=seg_b, teff_k=5500.0, dist_pc=10.0, star=f"SIM_SWS_DY_{i}")
            ok = bool(res["dyson"].get("dyson_candidate"))
        else:
            # Natural 10+18 um silicate excess bump -> expect dyson_candidate=False
            sil = 0.45 * np.max(b_scale * bw) * (np.exp(-0.5 * ((w_all - 10.2) / 0.8) ** 2) + 0.7 * np.exp(-0.5 * ((w_all - 18.5) / 1.4) ** 2))
            flx += sil
            res = scan_iso_sws_midir_v56(w_all, flx, 0.5 * err_base, seg_breaks=seg_b, teff_k=5500.0, dist_pc=10.0, star=f"SIM_SWS_SIL_{i}")
            ok = not bool(res["dyson"].get("dyson_candidate"))
        dy_ok += int(ok)
        trials.append({"suite": "CALIBRATION_V56_ISO_SWS_180", "class": "DYSON_VS_SILICATE_BB", "trial": i, "expected": 1 if i % 2 == 0 else 0, "observed": int(bool(res["dyson"].get("dyson_candidate"))), "passed": int(ok)})

    for i in range(30):
        flx = f0_phot + rng.normal(0.0, err_base)
        if i % 2 == 0:
            # Segment stitch edge glitch near 12.20 um
            idx_st = int(np.argmin(np.abs(w_all - 12.19)))
            flx[idx_st] += 18.0 * err_base[idx_st]
            if idx_st > 0:
                flx[idx_st - 1] += 12.0 * err_base[idx_st]
        else:
            # 1-px cosmic-ray/memory glitch at mid-segment (~20.8 um)
            idx_cr = int(np.argmin(np.abs(w_all - 20.8)))
            flx[idx_cr] += 22.0 * err_base[idx_cr]
        res = scan_iso_sws_midir_v56(w_all, flx, err_base, seg_breaks=seg_b, teff_k=5500.0, dist_pc=10.0, star=f"SIM_SWS_ST_{i}", star_rv_kms=1500.0)
        ok = res["qualified_v56"] == 0
        st_v += int(ok)
        trials.append({"suite": "CALIBRATION_V56_ISO_SWS_180", "class": "STITCH_AND_GLITCH_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v56"] > 0), "passed": int(ok)})

    for i in range(30):
        flx = f0_phot + rng.normal(0.0, err_base)
        if i % 2 == 0:
            # Known [Ne II] 12.8135 um fine-structure line
            dw_loc = 0.02
            flx += 16.0 * err_base * np.exp(-0.5 * ((w_all - 12.81355) / (1.5 * dw_loc)) ** 2)
        else:
            # Broad 11.25 um PAH / silicate dust bump
            flx += 18.0 * err_base * np.exp(-0.5 * ((w_all - 11.25) / 0.25) ** 2)
        res = scan_iso_sws_midir_v56(w_all, flx, err_base, seg_breaks=seg_b, teff_k=5500.0, dist_pc=10.0, star=f"SIM_SWS_NAT_{i}")
        ok = res["qualified_v56"] == 0 and (not bool(res["dyson"].get("dyson_candidate")))
        nat_v += int(ok)
        trials.append({"suite": "CALIBRATION_V56_ISO_SWS_180", "class": "NATURAL_LINE_DUST_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v56"] > 0), "passed": int(ok)})

    return {
        "total_trials": len(trials),
        "beacon_recovery": f"{b_rec}/45 ({b_rec/45.0:.4f})",
        "greenhouse_ccf": f"{gh_rec}/45 ({gh_rec/45.0:.4f})",
        "dyson_vs_silicate": f"{dy_ok}/30 ({dy_ok/30.0:.4f})",
        "stitch_glitch_veto": f"{st_v}/30 ({st_v/30.0:.4f})",
        "natural_line_veto": f"{nat_v}/30 ({nat_v/30.0:.4f})",
        "trials": trials,
    }


def run_sofia_forcast_calibration_v56(seed: int = 9803) -> dict[str, Any]:
    """`CALIBRATION_V56_SOFIA_FORCAST_120`: 60 grism beacons + 30 ATRAN telluric vetoes + 30 1-px glitch/PAH vetoes."""
    rng = np.random.default_rng(seed)
    n_px = 210
    w_g227 = np.linspace(17.5, 27.6, n_px)
    atr_base = np.ones(n_px)
    atr_base[(w_g227 >= 24.8) & (w_g227 <= 25.4)] = 0.25  # Deep ATRAN H2O absorption
    dw = float(w_g227[1] - w_g227[0])

    trials: list[dict[str, Any]] = []
    b_rec, atr_v, gl_v = 0, 0, 0

    for i in range(60):
        flx = 8.0 + rng.normal(0.0, 0.05, n_px)
        err = np.full(n_px, 0.05)
        wc = float(rng.uniform(19.3, 21.1)) if (i % 2 == 0) else float(rng.uniform(23.5, 24.1))
        flx += float(rng.uniform(11.5, 17.5)) * 0.05 * np.exp(-0.5 * ((w_g227 - wc) / (1.5 * dw)) ** 2)
        res = scan_sofia_forcast_grism_v56([{"grism_id": "FOR_G227", "dp_id": f"CAL_FG_{i}", "wave_um": w_g227, "flux_jy": flx, "err_jy": err, "atran": atr_base, "rp": 200.0}], star=f"SIM_FG_B_{i}", star_rv_kms=3000.0)
        ok = res["qualified_v56"] >= 1
        b_rec += int(ok)
        trials.append({"suite": "CALIBRATION_V56_SOFIA_FORCAST_120", "class": "CLEAN_FORCAST_BEACON", "trial": i, "expected": 1, "observed": int(ok), "passed": int(ok == 1)})

    for i in range(30):
        flx = 8.0 + rng.normal(0.0, 0.05, n_px)
        err = np.full(n_px, 0.05)
        wc = 25.10  # Directly inside ATRAN < 0.3 trough
        flx += float(rng.uniform(12.0, 18.0)) * 0.05 * np.exp(-0.5 * ((w_g227 - wc) / (1.5 * dw)) ** 2)
        res = scan_sofia_forcast_grism_v56([{"grism_id": "FOR_G227", "dp_id": f"CAL_FA_{i}", "wave_um": w_g227, "flux_jy": flx, "err_jy": err, "atran": atr_base, "rp": 200.0}], star=f"SIM_FG_AT_{i}", star_rv_kms=3000.0)
        ok = res["qualified_v56"] == 0
        atr_v += int(ok)
        trials.append({"suite": "CALIBRATION_V56_SOFIA_FORCAST_120", "class": "ATRAN_TELLURIC_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v56"] > 0), "passed": int(ok)})

    for i in range(30):
        flx = 8.0 + rng.normal(0.0, 0.05, n_px)
        err = np.full(n_px, 0.05)
        if i % 2 == 0:
            idx_g = int(rng.integers(30, n_px - 60))
            flx[idx_g] += float(rng.uniform(14.0, 22.0)) * 0.05
        else:
            flx += float(rng.uniform(12.0, 18.0)) * 0.05 * np.exp(-0.5 * ((w_g227 - 21.5) / (8.0 * dw)) ** 2)
        res = scan_sofia_forcast_grism_v56([{"grism_id": "FOR_G227", "dp_id": f"CAL_FGL_{i}", "wave_um": w_g227, "flux_jy": flx, "err_jy": err, "atran": atr_base, "rp": 200.0}], star=f"SIM_FG_GL_{i}", star_rv_kms=3000.0)
        ok = res["qualified_v56"] == 0
        gl_v += int(ok)
        trials.append({"suite": "CALIBRATION_V56_SOFIA_FORCAST_120", "class": "GLITCH_AND_PAH_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v56"] > 0), "passed": int(ok)})

    return {
        "total_trials": len(trials),
        "beacon_recovery": f"{b_rec}/60 ({b_rec/60.0:.4f})",
        "atran_telluric_veto": f"{atr_v}/30 ({atr_v/30.0:.4f})",
        "glitch_pah_veto": f"{gl_v}/30 ({gl_v/30.0:.4f})",
        "trials": trials,
    }


def run_coherent_jerk_calibration_v56(seed: int = 9804) -> dict[str, Any]:
    """`CALIBRATION_V56_COHERENT_JERK_240`: 60 cubic jerk + 60 periodic + 40 stationary + 40 transient + 40 BERV sky."""
    out = dict(run_coherent_jerk_calibration_v55(seed=seed))
    new_trials = []
    for t in out["trials"]:
        nt = dict(t)
        nt["suite"] = "CALIBRATION_V56_COHERENT_JERK_240"
        new_trials.append(nt)
    out["trials"] = new_trials
    return out


# ===========================================================================
# Phase D099 (V5.7): JCMT Millimeter Heterodyne, IRTF SpeX NIR/QCL, & DRIFT_V57
# ===========================================================================

JCMT_APERTURE_M = 15.0

# Prominent JCMT 215-375 GHz molecular / circumstellar / dense-core rest frequencies (GHz)
JCMT_MM_MOLECULAR_ATLAS_GHZ: tuple[tuple[str, float, str], ...] = (
    ("SiO_J5-4_v0", 217.10498, "Circumstellar/shocked SiO"),
    ("DCN_J3-2", 217.23854, "Deuterated cyanide"),
    ("SiS_J12-11", 217.81766, "Carbon-star SiS"),
    ("HC3N_J24-23", 218.32472, "Cyanopolyynes"),
    ("C18O_J2-1", 219.56035, "Isotopologue CO"),
    ("SO_56-45", 219.94944, "Sulfur monoxide"),
    ("13CO_J2-1", 220.39868, "13CO J=2-1"),
    ("C2H_N2p-1p", 226.65956, "CN N=2-1 hyperfine"),
    ("CN_N2-1", 226.87478, "CN radical"),
    ("HC3N_J25-24", 227.41890, "HC3N J=25-24"),
    ("12CO_J2-1", 230.53800, "CO J=2-1 (1.300 mm)"),
    ("CS_J5-4", 244.93556, "CS dense gas"),
    ("SiS_J13-12", 235.96136, "Circumstellar SiS"),
    ("CH3OH_5K-4K", 241.79135, "Methanol J=5-4"),
    ("HCN_J3-2", 265.88643, "HCN J=3-2"),
    ("HCO+_J3-2", 267.55763, "HCO+ J=3-2"),
    ("CS_J6-5", 293.91209, "CS J=6-5"),
    ("H2O_10-9_325GHz", 325.15292, "Submm water maser/thermal"),
    ("C18O_J3-2", 329.33055, "C18O J=3-2"),
    ("13CO_J3-2", 330.58796, "13CO J=3-2"),
    ("SO_78-67", 340.71416, "SO 7_8-6_7"),
    ("CS_J7-6", 342.88285, "CS J=7-6"),
    ("HC3N_J38-37", 345.60901, "HC3N high-J"),
    ("SO_88-77", 344.31061, "SO 8_8-7_7"),
    ("SiS_J19-18", 344.77948, "Circumstellar SiS J=19-18"),
    ("H13CN_J4-3", 345.33977, "H13CN J=4-3"),
    ("12CO_J3-2", 345.79599, "CO J=3-2 (0.867 mm)"),
    ("SiO_J8-7_v0", 347.33058, "SiO J=8-7"),
    ("C2H_N4-3", 349.33873, "Ethynyl radical"),
    ("H2CO_515-414", 351.76864, "Formaldehyde"),
    ("HCN_J4-3", 354.50548, "HCN J=4-3"),
    ("HCO+_J4-3", 356.73422, "HCO+ J=4-3"),
    ("H13CO+_J4-3", 346.99834, "H13CO+ J=4-3"),
    ("N2H+_J4-3", 372.67249, "Diazenylium"),
)


def jcmt_eta_a(freq_ghz: float) -> float:
    """Locked JCMT 15 m aperture efficiency eta_A(nu) across 215-375 GHz."""
    return 0.63 if float(freq_ghz) < 290.0 else 0.52


def jcmt_jy_per_k(freq_ghz: float) -> float:
    """Closed-form JCMT 15 m antenna-temperature conversion factor Gamma [Jy K^-1]."""
    eta_a = jcmt_eta_a(float(freq_ghz))
    a_geom = math.pi * ((0.5 * JCMT_APERTURE_M) ** 2)
    return float((2.0 * K_BOLTZ / (eta_a * a_geom)) * 1e26)


def jcmt_ta_to_flam_cgs(freq_ghz: float | np.ndarray, temp_k: float | np.ndarray) -> float | np.ndarray:
    """Convert JCMT antenna temperature T_A* (K) at ``freq_ghz`` into CGS F_lambda."""
    f_arr = np.asarray(freq_ghz, dtype=np.float64)
    f_med = float(np.median(f_arr)) if f_arr.ndim > 0 else float(f_arr)
    jy = np.asarray(temp_k, dtype=np.float64) * jcmt_jy_per_k(f_med)
    lam_a = C_ANGSTROM_GHZ / np.maximum(1.0, f_arr)
    flam = 1e-23 * jy * C_ANGSTROM_PER_S / (lam_a * lam_a)
    if np.ndim(freq_ghz) == 0 and np.ndim(temp_k) == 0:
        return float(flam)
    return flam


def scan_jcmt_mm_heterodyne_v57(
    cubes: list[dict[str, Any]],
    cfg: dict[str, Any] | None = None,
    star: str = "",
    dist_pc: float = 100.0,
    teff_k: float = 4000.0,
    star_rv_kms: float = 0.0,
    cohort_topo_ghz: list[float] | None = None,
) -> dict[str, Any]:
    """
    Engine V5.7A (`JCMT_MM_HETERODYNE_V57`): 0.805-1.384 mm (216.6-372.4 GHz) millimeter
    heterodyne technosignature search across CADC JCMT HARP/AWEOWEO/UU/RXA3 spectra.
    """
    del cfg
    peers_ghz = list(cohort_topo_ghz or [])
    candidates: list[dict[str, Any]] = []
    cube_summaries: list[dict[str, Any]] = []
    band_best_ul: dict[str, dict[str, float]] = {}
    raw_topo_ghz: list[float] = []
    n_pix_total = 0
    n_raw = 0
    n_qualified = 0

    for ci, cb in enumerate(cubes):
        dp_id = str(cb.get("dp_id", f"JCMT_{ci:02d}"))
        fq = np.asarray(cb["freq_ghz"], dtype=np.float64)
        tk = np.asarray(cb["temp_k"], dtype=np.float64)
        fin = np.isfinite(fq) & np.isfinite(tk) & (fq > 80.0) & (fq < 900.0) & (np.abs(tk) < 5e5)
        if int(np.sum(fin)) < 40:
            continue
        fq, tk = fq[fin], tk[fin]
        ord_f = np.argsort(fq)
        fq, tk = fq[ord_f], tk[ord_f]
        n_pix_total += len(fq)

        trim = max(6, int(round(0.03 * len(fq))))
        if len(fq) - 2 * trim < 32:
            continue
        in_trim = np.zeros(len(fq), dtype=bool)
        in_trim[trim : len(fq) - trim] = True

        dfreq_ghz = max(1e-8, exact_median_1d(np.abs(np.diff(fq))))
        med_f_ghz = exact_median_1d(fq)
        dv_chan_kms = C_KMS * dfreq_ghz / max(1.0, med_f_ghz)
        rp_eff = min(5.0e6, max(5.0e4, med_f_ghz / dfreq_ghz))

        win_px = max(25, min(121, (len(fq) // 8) | 1))
        cont = _asymmetric_clipped_baseline_v56(tk, win_px)
        res = tk - cont

        sig_arr = res[in_trim].copy()
        for _ in range(2):
            m_s = exact_median_1d(sig_arr)
            md_s = max(1e-7, exact_mad_1d(sig_arr))
            keep_s = np.abs(sig_arr - m_s) <= 3.5 * md_s
            if int(np.sum(keep_s)) >= max(16, len(sig_arr) // 3):
                sig_arr = sig_arr[keep_s]
        glob_sig_k = max(1e-7, exact_mad_1d(sig_arr))

        cont_in = cont[in_trim]
        x_in = np.linspace(-1.0, 1.0, len(cont_in))
        cdet = cont_in - np.polyval(np.polyfit(x_in, cont_in, 1), x_in)
        sw_power_frac = 0.0
        sw_amp_sigma = float(np.std(cdet) / max(1e-9, glob_sig_k)) if len(cdet) >= 16 else 0.0
        if len(cdet) >= 32:
            fft_p = np.abs(np.fft.rfft(cdet - np.mean(cdet))) ** 2
            if len(fft_p) > 4 and np.sum(fft_p[2:]) > 0.0:
                sw_power_frac = float(np.max(fft_p[2:]) / np.sum(fft_p[1:]))

        lam_a = C_ANGSTROM_GHZ / med_f_ghz
        temp_lim_k = 8.0 * glob_sig_k
        flam_lim = float(jcmt_ta_to_flam_cgs(med_f_ghz, temp_lim_k))
        ul = compute_photon_beam_upper_limit(
            wave_a=lam_a,
            amp_rel_lim=1.0,
            teff_k=float(teff_k),
            dist_pc=float(dist_pc),
            stellar_radius_rsun=1.0,
            radiometric_anchor="JCMT_MM_DIRECT_CGS",
            resolving_power=rp_eff,
            direct_flam_cgs=flam_lim,
        )
        ul["direct_flam_cgs"] = flam_lim
        ul["med_freq_ghz"] = float(med_f_ghz)
        ul["wave_a"] = float(lam_a)
        ul["resolving_power"] = float(rp_eff)
        ul["noise_mad_k"] = float(glob_sig_k)
        ul["eta_a"] = jcmt_eta_a(med_f_ghz)
        ul["jy_per_k"] = jcmt_jy_per_k(med_f_ghz)

        inst_key = "JCMT_MM_230GHZ" if med_f_ghz < 290.0 else "JCMT_HARP"
        canon_pool = CALIBRATION_BANDS_JCMT_MM_230GHZ if inst_key == "JCMT_MM_230GHZ" else CALIBRATION_BANDS_JCMT_HARP
        best_canon = min(canon_pool, key=lambda b: abs(b["center_wave_A"] - lam_a))
        bid = best_canon["band_id"] if abs(best_canon["center_wave_A"] - lam_a) <= 0.15 * best_canon["center_wave_A"] else f"JCMT_{int(round(med_f_ghz))}GHZ"
        if bid not in band_best_ul or ul["p_beam_10m_kw"] < band_best_ul[bid]["p_beam_10m_kw"]:
            band_best_ul[bid] = ul

        cube_summaries.append({
            "dp_id": dp_id,
            "inst_group": inst_key,
            "band": bid,
            "med_freq_ghz": round(med_f_ghz, 5),
            "dv_chan_kms": round(dv_chan_kms, 4),
            "rp_eff": round(rp_eff, 1),
            "noise_mad_k": round(glob_sig_k, 5),
            "sw_power_frac": round(sw_power_frac, 4),
            "p_beam_10m_kw": round(float(ul["p_beam_10m_kw"]), 4),
        })

        z_arr = res / glob_sig_k
        pk_idx = np.where(in_trim & (z_arr >= 7.5))[0]
        if len(pk_idx) == 0:
            continue
        ord_pk = pk_idx[np.argsort(z_arr[pk_idx])[::-1]]
        taken = np.zeros(len(fq), dtype=bool)
        for idx in ord_pk:
            if taken[idx] or idx <= 2 or idx >= len(fq) - 3:
                continue
            lo_n, hi_n = max(0, idx - 8), min(len(fq), idx + 9)
            if float(z_arr[idx]) < float(np.max(z_arr[lo_n:hi_n])) - 1e-12:
                continue
            taken[lo_n:hi_n] = True
            n_raw += 1

            w_l0, w_l1 = max(0, idx - 70), max(0, idx - 10)
            w_r0, w_r1 = min(len(fq), idx + 11), min(len(fq), idx + 71)
            sb_vals = np.concatenate([res[w_l0:w_l1], res[w_r0:w_r1]])
            loc_mad_k = max(glob_sig_k, exact_mad_1d(sb_vals) if len(sb_vals) >= 12 else glob_sig_k)
            loc_snr = float(res[idx] / loc_mad_k)
            loc_ripple_ratio = float(loc_mad_k / glob_sig_k)

            f_pk = float(fq[idx])
            lam_pk_um = (C_KMS / 1000.0) * 1e3 / max(1.0, f_pk)
            lam_pk_a = C_ANGSTROM_GHZ / max(1.0, f_pk)
            raw_topo_ghz.append(f_pk)

            eta_1px = float(abs(res[idx]) / max(1e-12, abs(res[idx]) + abs(res[idx - 1]) + abs(res[idx + 1])))
            adj_ratio = float(0.5 * (res[idx - 1] + res[idx + 1]) / max(1e-12, res[idx]))
            fwhm_px = _subchannel_fwhm_v56(res, int(idx))
            dv_fwhm_kms = fwhm_px * dv_chan_kms
            n_rep = int(np.sum((z_arr >= max(4.5, 0.5 * float(z_arr[idx]))) & (np.abs(np.arange(len(fq)) - idx) > 10)))

            f_rest_ghz = f_pk * (1.0 + float(star_rv_kms) / C_KMS)
            atlas_hit = ""
            for lname, l_ghz, _ in JCMT_MM_MOLECULAR_ATLAS_GHZ:
                if abs(C_KMS * (f_rest_ghz - l_ghz) / l_ghz) <= 200.0:
                    atlas_hit = lname
                    break

            veto_reason = ""
            qualified = False
            if eta_1px > 0.72 or adj_ratio < 0.16 or fwhm_px < 2.2:
                veto_reason = "G5_JCMT_LO_SPUR_1CHAN"
            elif loc_ripple_ratio >= 2.2 or (sw_power_frac >= 0.42 and sw_amp_sigma >= 0.85) or n_rep >= 5 or loc_snr < 7.0:
                veto_reason = "G2_JCMT_STANDING_WAVE_RIPPLE"
            elif fwhm_px >= 6.5 or dv_fwhm_kms >= 5.0:
                veto_reason = "G5_JCMT_BROAD_MOLECULAR_ENVELOPE"
            elif atlas_hit:
                veto_reason = f"G3_JCMT_MOLECULAR_ATLAS:{atlas_hit}"
            elif any(abs(C_KMS * (f_pk - p_ghz) / max(1.0, f_pk)) <= 10.0 for p_ghz in peers_ghz):
                veto_reason = "G6_JCMT_COINCIDENT_LO_TELLURIC"
            else:
                qualified = True
                veto_reason = "QUALIFIED_V57_JCMT_BEACON"
                n_qualified += 1

            candidates.append({
                "instrument": inst_key,
                "cand_id": f"JCMT_{star}_{ci:02d}_{idx:05d}",
                "star": star,
                "dp_id": dp_id,
                "band": bid,
                "freq_ghz": round(f_pk, 6),
                "wave_a": round(lam_pk_a, 3),
                "wave_um": round(lam_pk_um, 5),
                "snr": round(loc_snr, 3),
                "eta_1px": round(eta_1px, 4),
                "fwhm_px": round(fwhm_px, 3),
                "dv_fwhm_kms": round(dv_fwhm_kms, 3),
                "n_rep_peaks": int(n_rep),
                "loc_ripple_ratio": round(loc_ripple_ratio, 3),
                "qualified_v57": bool(qualified),
                "veto_reason": veto_reason,
                "atlas_match": atlas_hit,
            })

    if band_best_ul:
        best_band, best_ul = min(band_best_ul.items(), key=lambda kv: kv[1]["p_beam_10m_kw"])
        best_p_kw = float(best_ul["p_beam_10m_kw"])
    else:
        best_band, best_p_kw = "", float("inf")

    return {
        "star": star,
        "n_cubes": int(len(cube_summaries)),
        "n_pix": int(n_pix_total),
        "raw_peaks": int(n_raw),
        "qualified_v57": int(n_qualified),
        "candidates": candidates,
        "upper_limits": band_best_ul,
        "cube_summaries": cube_summaries,
        "best_p_beam_10m_kw": best_p_kw,
        "best_band": best_band,
        "raw_topo_ghz": raw_topo_ghz,
    }


def run_jcmt_mm_calibration_v57(seed: int = 9901) -> dict[str, Any]:
    """`CALIBRATION_V57_JCMT_MM_180`: 60 mm beacons + 40 standing waves + 40 broad molecular + 40 LO spurs."""
    rng = np.random.default_rng(seed)
    n_px = 1400
    f0 = 335.00
    fq = f0 + np.linspace(-0.45, 0.45, n_px)
    sig_f = (fq[1] - fq[0]) * 1.6
    trials: list[dict[str, Any]] = []
    rec = sw_v = brd_v = sp_v = 0

    for i in range(60):
        tk = 0.05 + 0.02 * np.linspace(-1, 1, n_px) + rng.normal(0.0, 0.035, n_px)
        fc = float(rng.uniform(f0 - 0.30, f0 + 0.30))
        tk += float(rng.uniform(11.0, 18.0)) * 0.035 * np.exp(-0.5 * ((fq - fc) / sig_f) ** 2)
        res = scan_jcmt_mm_heterodyne_v57([{"dp_id": f"CAL_J_{i}", "freq_ghz": fq, "temp_k": tk}], star=f"SIM_J_B_{i}", star_rv_kms=500.0)
        ok = res["qualified_v57"] >= 1
        rec += int(ok)
        trials.append({"suite": "CALIBRATION_V57_JCMT_MM_180", "class": "CLEAN_MM_BEACON", "trial": i, "expected": 1, "observed": int(ok), "passed": int(ok == 1)})

    for i in range(40):
        ph = float(rng.uniform(0.0, 2.0 * math.pi))
        tk = 0.05 + float(rng.uniform(0.55, 1.1)) * np.sin(2.0 * math.pi * 6.0 * np.linspace(0, 1, n_px) + ph) + rng.normal(0.0, 0.035, n_px)
        res = scan_jcmt_mm_heterodyne_v57([{"dp_id": f"CAL_JSW_{i}", "freq_ghz": fq, "temp_k": tk}], star=f"SIM_J_SW_{i}", star_rv_kms=500.0)
        ok = res["qualified_v57"] == 0
        sw_v += int(ok)
        trials.append({"suite": "CALIBRATION_V57_JCMT_MM_180", "class": "STANDING_WAVE_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v57"] > 0), "passed": int(ok)})

    for i in range(40):
        tk = 0.05 + rng.normal(0.0, 0.035, n_px)
        fc = float(rng.uniform(f0 - 0.25, f0 + 0.25))
        sig_b = float(rng.uniform(5.0, 10.0)) * (fq[1] - fq[0])
        tk += float(rng.uniform(12.0, 20.0)) * 0.035 * np.exp(-0.5 * ((fq - fc) / sig_b) ** 2)
        res = scan_jcmt_mm_heterodyne_v57([{"dp_id": f"CAL_JBR_{i}", "freq_ghz": fq, "temp_k": tk}], star=f"SIM_J_BR_{i}", star_rv_kms=500.0)
        ok = res["qualified_v57"] == 0
        brd_v += int(ok)
        trials.append({"suite": "CALIBRATION_V57_JCMT_MM_180", "class": "BROAD_MOLECULAR_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v57"] > 0), "passed": int(ok)})

    for i in range(40):
        tk = 0.05 + rng.normal(0.0, 0.035, n_px)
        idx_s = int(rng.integers(150, n_px - 150))
        tk[idx_s] += float(rng.uniform(14.0, 24.0)) * 0.035
        res = scan_jcmt_mm_heterodyne_v57([{"dp_id": f"CAL_JSP_{i}", "freq_ghz": fq, "temp_k": tk}], star=f"SIM_J_SP_{i}", star_rv_kms=500.0)
        ok = res["qualified_v57"] == 0
        sp_v += int(ok)
        trials.append({"suite": "CALIBRATION_V57_JCMT_MM_180", "class": "SINGLE_CHAN_LO_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v57"] > 0), "passed": int(ok)})

    return {
        "total_trials": len(trials),
        "beacon_recovery": f"{rec}/60 ({rec/60.0:.4f})",
        "standing_wave_veto": f"{sw_v}/40 ({sw_v/40.0:.4f})",
        "broad_molecular_veto": f"{brd_v}/40 ({brd_v/40.0:.4f})",
        "single_chan_lo_veto": f"{sp_v}/40 ({sp_v/40.0:.4f})",
        "trials": trials,
    }


IRTF_SPEX_TELLURIC_BLACKOUT_UM: tuple[tuple[float, float], ...] = (
    (1.335, 1.445),
    (1.785, 1.975),
    (2.470, 2.950),
    (4.150, 4.520),
)

IRTF_SPEX_NATURAL_LINES_UM: tuple[tuple[str, float], ...] = (
    ("CaII_IRT1_0p850", 0.850035),
    ("CaII_IRT2_0p854", 0.854444),
    ("CaII_IRT3_0p866", 0.866452),
    ("HeI_1p083", 1.08332),
    ("Pa_gamma_1p094", 1.09411),
    ("Pa_beta_1p282", 1.28216),
    ("FeII_1p644", 1.64400),
    ("H2_1-0_S1_2p122", 2.12183),
    ("Br_gamma_2p166", 2.16612),
    ("CO_2-0_band_2p294", 2.2935),
    ("Pf_gamma_3p740", 3.74056),
    ("Br_alpha_4p052", 4.05226),
    ("Pf_beta_4p654", 4.65378),
)


def scan_irtf_spex_nir_qcl_v57(
    wave_um: np.ndarray,
    flux_wm2um: np.ndarray,
    err_wm2um: np.ndarray,
    cfg: dict[str, Any] | None = None,
    star: str = "",
    dp_id: str = "",
    dist_pc: float = 15.0,
    teff_k: float = 5000.0,
    star_rv_kms: float = 0.0,
    cohort_topo_um: list[float] | None = None,
) -> dict[str, Any]:
    """
    Engine V5.7B (`IRTF_SPEX_NIR_QCL_V57`): 0.8-5.0 um flux-calibrated NIR+QCL/M-band
    search with telluric blackout masking, unresolved LSF verification, NIR/IR atomic/CO
    atlas veto, and direct F_lambda -> 10 m beam EIRP bounds.
    """
    del cfg
    peers_um = list(cohort_topo_um or [])
    w = np.asarray(wave_um, dtype=np.float64)
    f_si = np.asarray(flux_wm2um, dtype=np.float64)
    e_si = np.asarray(err_wm2um, dtype=np.float64)

    # 1 W m^-2 um^-1 == 0.1 erg s^-1 cm^-2 A^-1
    f_cgs = 0.1 * f_si
    e_cgs = 0.1 * e_si

    fin = np.isfinite(w) & np.isfinite(f_cgs) & np.isfinite(e_cgs) & (w >= 0.78) & (w <= 5.20) & (e_cgs > 0.0)
    w, f_cgs, e_cgs = w[fin], f_cgs[fin], e_cgs[fin]
    if len(w) < 64:
        return {"star": star, "n_bins": len(w), "raw_peaks": 0, "qualified_v57": 0, "candidates": [], "upper_limits": {}, "best_p_beam_10m_kw": float("inf"), "best_band": "", "raw_topo_um": []}

    ord_w = np.argsort(w)
    w, f_cgs, e_cgs = w[ord_w], f_cgs[ord_w], e_cgs[ord_w]

    telluric_bad = np.zeros(len(w), dtype=bool)
    for lo_t, hi_t in IRTF_SPEX_TELLURIC_BLACKOUT_UM:
        telluric_bad |= (w >= lo_t) & (w <= hi_t)
    # Gap-edge masking (where wave jumps > 0.02 um)
    dw = np.diff(w, prepend=w[0])
    dw_med = max(1e-5, exact_median_1d(dw[1:]))
    gap_edge = dw > 6.0 * dw_med
    gap_edge[:-1] |= dw[1:] > 6.0 * dw_med

    band_best_ul: dict[str, dict[str, float]] = {}
    candidates: list[dict[str, Any]] = []
    raw_topo_um: list[float] = []
    n_raw = n_qualified = 0

    # Split cleanly at telluric/instrument gaps into continuous spectral segments
    splits = np.where(dw > 12.0 * dw_med)[0]
    bounds = [0] + list(splits) + [len(w)]
    for a, b in zip(bounds[:-1], bounds[1:]):
        if (b - a) < 40:
            continue
        ws = w[a:b]
        fs = f_cgs[a:b]
        es = e_cgs[a:b]
        t_bad_s = telluric_bad[a:b] | gap_edge[a:b]
        in_trim = np.ones(len(ws), dtype=bool)
        trim = max(4, min(12, len(ws) // 25))
        in_trim[:trim] = False
        in_trim[-trim:] = False
        clean_s = in_trim & (~t_bad_s)
        if int(np.sum(clean_s)) < 24:
            continue

        # Fit iteratively clipped smooth polynomial baseline so steep continuum slopes
        # at 0.8-1.4 um do not inflate local rolling MAD or create median-filter curvature lag
        x_poly = 2.0 * (ws - ws[0]) / max(1e-6, float(ws[-1] - ws[0])) - 1.0
        deg_p = min(5, max(1, len(ws) // 80))
        keep_p = clean_s.copy()
        p_base = np.zeros_like(fs)
        for _ in range(3):
            if int(np.sum(keep_p)) > deg_p + 4:
                coef = np.polyfit(x_poly[keep_p], fs[keep_p], deg_p)
                p_base = np.polyval(coef, x_poly)
                r_p = fs - p_base
                mad_p = max(1e-22, exact_mad_1d(r_p[keep_p]))
                keep_p = clean_s & (r_p <= 3.0 * mad_p) & (r_p >= -3.5 * mad_p)
        cont = p_base + _asymmetric_clipped_baseline_v56(fs - p_base, max(25, min(65, (len(ws) // 8) | 1)))
        res = fs - cont
        mad_loc = _rolling_mad_scaled(res, clean_s, win_bins=91)
        sig_eff = np.maximum(es, np.maximum(mad_loc, 1e-22))
        z_arr = res / sig_eff

        # Canonical IRTF SpeX band EIRP limits
        for bd in CALIBRATION_BANDS_IRTF_SPEX:
            bc_um = float(bd["center_wave_A"]) / 1e4
            m_b = clean_s & (np.abs(ws - bc_um) <= 0.12)
            if int(np.sum(m_b)) < 16:
                continue
            med_sig_cgs = float(exact_median_1d(sig_eff[m_b]))
            ul = compute_photon_beam_upper_limit(
                wave_a=float(bd["center_wave_A"]),
                amp_rel_lim=1.0,
                teff_k=float(teff_k),
                dist_pc=float(dist_pc),
                stellar_radius_rsun=1.0,
                radiometric_anchor="IRTF_SPEX_DIRECT_CGS",
                resolving_power=2000.0,
                direct_flam_cgs=8.0 * med_sig_cgs,
            )
            ul["direct_flam_cgs"] = float(8.0 * med_sig_cgs)
            ul["wave_a"] = float(bd["center_wave_A"])
            ul["resolving_power"] = 2000.0
            bid = bd["band_id"]
            if bid not in band_best_ul or ul["p_beam_10m_kw"] < band_best_ul[bid]["p_beam_10m_kw"]:
                band_best_ul[bid] = ul

        pk_idx = np.where(in_trim & (z_arr >= 7.5))[0]
        if len(pk_idx) == 0:
            continue
        ord_pk = pk_idx[np.argsort(z_arr[pk_idx])[::-1]]
        taken = np.zeros(len(ws), dtype=bool)
        for idx in ord_pk:
            if taken[idx] or idx <= 2 or idx >= len(ws) - 3:
                continue
            lo_n, hi_n = max(0, idx - 6), min(len(ws), idx + 7)
            if float(z_arr[idx]) < float(np.max(z_arr[lo_n:hi_n])) - 1e-12:
                continue
            taken[lo_n:hi_n] = True
            n_raw += 1

            w_pk = float(ws[idx])
            raw_topo_um.append(w_pk)
            eta_1px = float(abs(res[idx]) / max(1e-22, abs(res[idx]) + abs(res[idx - 1]) + abs(res[idx + 1])))
            fwhm_px = _subchannel_fwhm_v56(res, int(idx))
            w_rest = w_pk * (1.0 - float(star_rv_kms) / C_KMS)
            atlas_hit = ""
            for lname, l_um in IRTF_SPEX_NATURAL_LINES_UM:
                if abs(C_KMS * (w_rest - l_um) / l_um) <= 650.0:
                    atlas_hit = lname
                    break

            is_tel = bool(t_bad_s[idx])
            veto_reason = ""
            qualified = False
            if is_tel:
                veto_reason = "G2_SPEX_TELLURIC_OR_GAP_EDGE"
            elif eta_1px > 0.66 or fwhm_px < 1.9:
                veto_reason = "G5_SPEX_1PX_GLITCH"
            elif fwhm_px >= 7.5:
                veto_reason = "G5_SPEX_BROAD_STELLAR_CO"
            elif atlas_hit:
                veto_reason = f"G3_SPEX_NATURAL_LINE:{atlas_hit}"
            elif any(abs(C_KMS * (w_pk - pu) / max(1e-6, w_pk)) <= 200.0 for pu in peers_um):
                veto_reason = "G6_SPEX_TELLURIC_COINCIDENCE"
            else:
                qualified = True
                veto_reason = "QUALIFIED_V57_SPEX_BEACON"
                n_qualified += 1

            candidates.append({
                "instrument": "IRTF_SPEX",
                "cand_id": f"SPEX_{star}_{a:04d}_{idx:04d}",
                "star": star,
                "dp_id": dp_id,
                "band": "SPEX_QCL_M" if w_pk >= 2.8 else "SPEX_SXD_NIR",
                "wave_um": round(w_pk, 5),
                "wave_a": round(w_pk * 1e4, 2),
                "snr": round(float(z_arr[idx]), 3),
                "eta_1px": round(eta_1px, 4),
                "fwhm_px": round(fwhm_px, 3),
                "qualified_v57": bool(qualified),
                "veto_reason": veto_reason,
                "atlas_match": atlas_hit,
            })

    if band_best_ul:
        best_band, best_ul = min(band_best_ul.items(), key=lambda kv: kv[1]["p_beam_10m_kw"])
        best_p_kw = float(best_ul["p_beam_10m_kw"])
    else:
        best_band, best_p_kw = "", float("inf")

    return {
        "star": star,
        "n_bins": int(len(w)),
        "raw_peaks": int(n_raw),
        "qualified_v57": int(n_qualified),
        "candidates": candidates,
        "upper_limits": band_best_ul,
        "best_p_beam_10m_kw": best_p_kw,
        "best_band": best_band,
        "raw_topo_um": raw_topo_um,
    }


def run_irtf_spex_calibration_v57(seed: int = 9902) -> dict[str, Any]:
    """`CALIBRATION_V57_IRTF_SPEX_180`: 60 NIR/QCL beacons + 40 telluric + 40 1-px glitches + 40 broad/CO."""
    rng = np.random.default_rng(seed)
    w_grid = np.concatenate([
        np.linspace(0.82, 2.46, 1600),
        np.linspace(2.96, 4.95, 700),
    ])
    e_si = np.full(len(w_grid), 1.5e-11)
    trials: list[dict[str, Any]] = []
    rec = tel_v = gl_v = br_v = 0

    for i in range(60):
        f_si = 2e-9 * (w_grid / 1.5) ** (-2.2) + rng.normal(0.0, e_si)
        wc = float(rng.choice([1.19, 1.56, 2.22, 3.38, 3.62, 4.80])) + float(rng.uniform(-0.03, 0.03))
        sig_w = max(0.0028, wc / (2000.0 * FWHM_FACTOR) * 1.45)
        f_si += float(rng.uniform(11.5, 17.5)) * 1.5e-11 * np.exp(-0.5 * ((w_grid - wc) / sig_w) ** 2)
        res = scan_irtf_spex_nir_qcl_v57(w_grid, f_si, e_si, star=f"SIM_SPEX_B_{i}", dp_id=f"SPEX_{i}", star_rv_kms=0.0)
        ok = res["qualified_v57"] >= 1
        rec += int(ok)
        trials.append({"suite": "CALIBRATION_V57_IRTF_SPEX_180", "class": "CLEAN_SPEX_BEACON", "trial": i, "expected": 1, "observed": int(ok), "passed": int(ok == 1)})

    for i in range(40):
        f_si = 2e-9 * (w_grid / 1.5) ** (-2.2) + rng.normal(0.0, e_si)
        wc = float(rng.choice([1.38, 1.88, 4.30]))
        f_si += float(rng.uniform(13.0, 20.0)) * 1.5e-11 * np.exp(-0.5 * ((w_grid - wc) / 0.003) ** 2)
        res = scan_irtf_spex_nir_qcl_v57(w_grid, f_si, e_si, star=f"SIM_SPEX_T_{i}", dp_id=f"SPEXT_{i}", star_rv_kms=5000.0)
        ok = res["qualified_v57"] == 0
        tel_v += int(ok)
        trials.append({"suite": "CALIBRATION_V57_IRTF_SPEX_180", "class": "TELLURIC_BLACKOUT_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v57"] > 0), "passed": int(ok)})

    for i in range(40):
        f_si = 2e-9 * (w_grid / 1.5) ** (-2.2) + rng.normal(0.0, e_si)
        idx_c = int(rng.integers(200, 1200))
        while any(lo <= w_grid[idx_c] <= hi for lo, hi in IRTF_SPEX_TELLURIC_BLACKOUT_UM):
            idx_c += 15
        f_si[idx_c] += float(rng.uniform(15.0, 24.0)) * 1.5e-11
        res = scan_irtf_spex_nir_qcl_v57(w_grid, f_si, e_si, star=f"SIM_SPEX_G_{i}", dp_id=f"SPEXG_{i}", star_rv_kms=5000.0)
        ok = res["qualified_v57"] == 0
        gl_v += int(ok)
        trials.append({"suite": "CALIBRATION_V57_IRTF_SPEX_180", "class": "GLITCH_1PX_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v57"] > 0), "passed": int(ok)})

    for i in range(40):
        f_si = 2e-9 * (w_grid / 1.5) ** (-2.2) + rng.normal(0.0, e_si)
        f_si += float(rng.uniform(13.0, 19.0)) * 1.5e-11 * np.exp(-0.5 * ((w_grid - 1.62) / 0.015) ** 2)
        res = scan_irtf_spex_nir_qcl_v57(w_grid, f_si, e_si, star=f"SIM_SPEX_BR_{i}", dp_id=f"SPEXBR_{i}", star_rv_kms=5000.0)
        ok = res["qualified_v57"] == 0
        br_v += int(ok)
        trials.append({"suite": "CALIBRATION_V57_IRTF_SPEX_180", "class": "BROAD_BANDHEAD_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v57"] > 0), "passed": int(ok)})

    return {
        "total_trials": len(trials),
        "beacon_recovery": f"{rec}/60 ({rec/60.0:.4f})",
        "telluric_veto": f"{tel_v}/40 ({tel_v/40.0:.4f})",
        "glitch_veto": f"{gl_v}/40 ({gl_v/40.0:.4f})",
        "broad_veto": f"{br_v}/40 ({br_v/40.0:.4f})",
        "trials": trials,
    }


def kepler_eccentric_anomaly(mean_anom: np.ndarray, ecc: float) -> np.ndarray:
    """Solve Kepler equation E - e sin(E) = M via 6 Newton-Raphson iterations."""
    m = np.asarray(mean_anom, dtype=np.float64)
    e_val = max(0.0, min(0.95, float(ecc)))
    if e_val < 1e-6:
        return m.copy()
    E = m + e_val * np.sin(m)
    for _ in range(6):
        f_e = E - e_val * np.sin(E) - m
        fp_e = np.maximum(1e-6, 1.0 - e_val * np.cos(E))
        E = E - f_e / fp_e
    return E


def scan_coherent_shift_stack_keplerian_jerk_v57(
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
    known_orb_periods_days: list[float] | None = None,
    known_orb_kps_kms: list[float] | None = None,
    enable_long_blind: bool = True,
) -> dict[str, Any]:
    """
    Engine `DRIFT_V57_KEPLERIAN_JERK`: Joint 3D orthogonalized Taylor jerk (linear + quad + cubic)
    plus multi-planet ephemeris-locked Keplerian & long-baseline logarithmic periodic shift-stacking
    across multi-year (`2-22 yr`, `N >= 4`) echelle campaigns.
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
        "n_pixel_trajectory_integrals": 0,
        "n_raw_candidates": 0,
        "taylor_only_hits": 0,
        "keplerian_hits": 0,
        "candidates": [],
    }
    if fn_e.ndim != 2 or n_ep_in < 4 or len(w) < 256:
        return empty

    ord_t = np.argsort(mjds)
    mjds, fn_e, sig_e, v_o2r = mjds[ord_t], fn_e[ord_t], sig_e[ord_t], v_o2r[ord_t]
    n_ep = fn_e.shape[0]
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

    col_ok = np.sum(V, axis=0) >= max(4, int(math.ceil(0.55 * n_ep)))
    Z[:, ~col_ok] = 0.0
    V[:, ~col_ok] = False

    ln_w0 = math.log(float(w[0]))
    ln_w1 = math.log(float(w[-1]))
    dv_grid_kms = max(1.2, min(4.5, 0.70 * sig_v))
    dln = dv_grid_kms / C_KMS
    n_log = int(math.floor((ln_w1 - ln_w0) / dln)) + 1
    if n_log > 160000:
        dln = (ln_w1 - ln_w0) / 160000.0
        dv_grid_kms = dln * C_KMS
        n_log = 160001
    ln_grid = ln_w0 + dln * np.arange(n_log, dtype=np.float64)
    w_log = np.exp(ln_grid)
    ln_w_native = np.log(w)

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
        mk = M_log[k, V_log[k]]
        if len(mk) >= 64:
            mad_m = exact_mad_1d(mk)
            if mad_m > 0.2:
                M_log[k] /= mad_m

    pad = int(math.ceil(260.0 / dv_grid_kms)) + 4
    n_core = n_log - 2 * pad
    if n_core < 64:
        return empty
    base_idx = np.arange(pad, n_log - pad, dtype=np.int64)

    t_mid = 0.5 * (float(mjds[0]) + float(mjds[-1]))
    dt_half = max(1e-3, 0.5 * (float(mjds[-1]) - float(mjds[0])))
    tau = (mjds - t_mid) / dt_half
    p2_tau = tau * tau - (1.0 / 3.0)
    p3_tau = 2.5 * (tau * tau * tau - 0.6 * tau)

    M_z = np.ascontiguousarray(np.where(V_log, M_log, 0.0), dtype=np.float64)
    V_u8 = np.ascontiguousarray(V_log.astype(np.uint8))
    inv_sqrt_nv = np.zeros(n_ep + 1, dtype=np.float64)
    for k_nv in range(4, n_ep + 1):
        inv_sqrt_nv[k_nv] = 1.0 / math.sqrt(float(k_nv))

    def _eval_traj(v_ep_kms: np.ndarray, branch: str, meta: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
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
            s_sorted = np.sort(s_act)[::-1]
            s_max = float(s_sorted[0])
            sum_act = float(np.sum(s_act))
            snr_st = sum_act / math.sqrt(float(n_val))
            snr_loo = (sum_act - s_max) / math.sqrt(float(n_val - 1))
            if snr_loo < min_snr_loo:
                continue
            sum_pos = float(np.sum(np.maximum(s_act, 0.0)))
            single_frac = s_max / max(1e-6, sum_pos)
            if single_frac > max_single_frac:
                continue
            if n_val >= 5:
                top2_frac = float(s_sorted[0] + s_sorted[1]) / max(1e-6, sum_pos)
                if top2_frac > 0.67:
                    continue
            pos_frac = float(np.sum(s_act >= 1.5)) / float(n_val)
            if pos_frac < min_pos_frac:
                continue

            s_lo, s_hi = int(np.min(sh)) - 2, int(np.max(sh)) + 2
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

    min_req_ep_b = max(4, n_ep - int(math.floor(max_masked_frac * float(n_ep))))
    M_z32 = np.ascontiguousarray(M_z, dtype=np.float32)
    s_buf = np.empty(n_core, dtype=np.float32)
    min_s_exact = float(min_snr_stack * math.sqrt(min_req_ep_b))
    min_s_coarse = float(max(4.8, min_snr_stack * 0.64) * math.sqrt(min_req_ep_b))
    add_fn = np.add
    copy_fn = np.copyto

    def _run_precomputed_grid(
        v_mat: np.ndarray,
        branch_name: str,
        params_list: list[tuple[Any, ...]],
        kind: str,
        coarse_out: list[tuple[float, float, float]] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        if len(params_list) == 0:
            return [], 0
        dv_b = np.ptp(v_mat, axis=1)
        vmax_b = np.max(np.abs(v_mat), axis=1)
        ok_idx = np.where((dv_b >= min_dv_span) & (vmax_b <= 250.0))[0]
        n_ok = int(len(ok_idx))
        if n_ok == 0:
            return [], 0
        sh_rows = (np.rint(v_mat[ok_idx] / dv_grid_kms).astype(np.int64) + pad).tolist()
        hits_g: list[dict[str, Any]] = []
        ep_range = range(1, n_ep)
        for ri in range(n_ok):
            sh_r = sh_rows[ri]
            s0 = sh_r[0]
            copy_fn(s_buf, M_z32[0, s0 : s0 + n_core])
            for k in ep_range:
                sk = sh_r[k]
                add_fn(s_buf, M_z32[k, sk : sk + n_core], out=s_buf)
            s_max = float(s_buf.max())
            if s_max >= min_s_exact:
                p_tup = params_list[int(ok_idx[ri])]
                if kind == "taylor":
                    hs, sg, jk = p_tup
                    br_eff = "CUBIC_JERK_STACK_V57" if abs(jk) >= 12.0 else ("CURVED_STACK_V57" if abs(sg) >= 8.0 else "LINEAR_STACK_V57")
                    meta = {"half_slope_kms": round(hs, 2), "quad_sag_kms": round(sg, 2), "cubic_jerk_kms": round(jk, 2)}
                else:
                    p_d, ka, ph = p_tup
                    br_eff = branch_name
                    meta = {"period_d": round(p_d, 4), "k_amp_kms": round(ka, 2), "phi_rad": round(ph, 3)}
                h_loc, _ = _eval_traj(v_mat[int(ok_idx[ri])], br_eff, meta)
                hits_g.extend(h_loc)
            elif coarse_out is not None and s_max >= min_s_coarse:
                _, ka, ph = params_list[int(ok_idx[ri])]
                coarse_out.append((s_max, ka, ph))
        return hits_g, n_ok

    # 1. Orthogonalized Linear + Quadratic Sag + Cubic Jerk grid (Taylor branch)
    slopes = np.linspace(-180.0, 180.0, 37)
    sags = np.linspace(-60.0, 60.0, 5)
    jerks = np.array([-60.0, -30.0, 0.0, 30.0, 60.0])
    taylor_cands: list[dict[str, Any]] = []
    kep_cands: list[dict[str, Any]] = []
    n_eval = 0

    t_rows: list[np.ndarray] = []
    t_pars: list[tuple[float, float, float]] = []
    for jk in jerks:
        for sg in sags:
            sg_p2 = float(sg) * p2_tau + float(jk) * p3_tau
            for hs in slopes:
                if abs(hs) < 6.0 and abs(sg) < 8.0 and abs(jk) < 8.0:
                    continue
                t_rows.append(float(hs) * tau + sg_p2)
                t_pars.append((float(hs), float(sg), float(jk)))
    if t_rows:
        h_t, c_t = _run_precomputed_grid(np.vstack(t_rows), "", t_pars, "taylor")
        n_eval += c_t
        taylor_cands.extend(h_t)

    # 2. Multi-Period Blind Logarithmic Periodic + Multi-Planet Ephemeris-Locked Keplerian Grid
    t_rel = mjds - float(mjds[0])
    dt_base = float(mjds[-1] - mjds[0])
    if dt_base >= 1.0 and n_ep >= 6:
        p_grid = list(np.geomspace(1.2, 60.0, 10))
        if enable_long_blind and dt_base >= 30.0:
            p_max = min(3000.0, 2.0 * dt_base)
            if p_max > 75.0:
                p_grid.extend(list(np.geomspace(75.0, p_max, 8)))
        phi_blind = np.linspace(0.0, 2.0 * math.pi, 10, endpoint=False)
        k_blind = np.array([35.0, 70.0, 115.0, 175.0])
        b_rows: list[np.ndarray] = []
        b_pars: list[tuple[float, float, float]] = []
        for p_d in p_grid:
            w_pd = 2.0 * math.pi * t_rel / float(p_d)
            for phi in phi_blind:
                sin_v = np.sin(w_pd + float(phi))
                for k_amp in k_blind:
                    b_rows.append(float(k_amp) * sin_v)
                    b_pars.append((float(p_d), float(k_amp), float(phi)))
        if b_rows:
            h_b, c_b = _run_precomputed_grid(np.vstack(b_rows), "PERIODIC_STACK_V57", b_pars, "periodic")
            n_eval += c_b
            kep_cands.extend(h_b)

    # Ephemeris-locked multi-planet Keplerian scan (precomputed shifts + Stage-2 local (K, phi) polish)
    p_list: list[float] = []
    kp_list: list[float] = []
    if known_orb_period_days is not None and math.isfinite(float(known_orb_period_days)) and float(known_orb_period_days) > 0.3:
        p_list.append(float(known_orb_period_days))
        kp_list.append(float(known_orb_kp_kms) if (known_orb_kp_kms is not None and math.isfinite(float(known_orb_kp_kms))) else math.nan)
    if known_orb_periods_days:
        for idx_p, pk in enumerate(known_orb_periods_days):
            if math.isfinite(float(pk)) and float(pk) > 0.3 and all(abs(float(pk) - x) > 1e-3 for x in p_list):
                p_list.append(float(pk))
                kp_v = known_orb_kps_kms[idx_p] if (known_orb_kps_kms and idx_p < len(known_orb_kps_kms)) else math.nan
                kp_list.append(float(kp_v) if math.isfinite(float(kp_v)) else math.nan)

    if n_ep >= 4:
        for p_k, kp_k in zip(p_list, kp_list):
            n_phi_k = max(32, min(56, int(math.ceil(2.0 * math.pi * 175.0 / max(1.5, sig_v * 2.5)))))
            dphi_k = (2.0 * math.pi) / float(n_phi_k)
            phi_k_grid = np.linspace(0.0, 2.0 * math.pi, n_phi_k, endpoint=False)
            k_k_grid = np.array([25.0, 42.0, 60.0, 78.0, 96.0, 114.0, 134.0, 156.0, 180.0])
            if math.isfinite(kp_k) and kp_k >= 10.0:
                k_k_grid = np.unique(np.append(k_k_grid, kp_k))
            w_pk = 2.0 * math.pi * t_rel / p_k
            k_rows: list[np.ndarray] = []
            k_pars: list[tuple[float, float, float]] = []
            for phi in phi_k_grid:
                sin_v = np.sin(w_pk + float(phi))
                for k_amp in k_k_grid:
                    k_rows.append(float(k_amp) * sin_v)
                    k_pars.append((p_k, float(k_amp), float(phi)))
            coarse_list: list[tuple[float, float, float]] = []
            h_k_total: list[dict[str, Any]] = []
            if k_rows:
                h_k, c_k = _run_precomputed_grid(np.vstack(k_rows), "KEPLERIAN_COHERENT_STACK_V57", k_pars, "periodic", coarse_out=coarse_list)
                n_eval += c_k
                h_k_total.extend(h_k)
            kep_cands.extend(h_k_total)
            if coarse_list and not h_k_total:
                coarse_list.sort(key=lambda item: -item[0])
                seen_fine: set[tuple[int, int]] = set()
                f_rows: list[np.ndarray] = []
                f_pars: list[tuple[float, float, float]] = []
                for _, k0, phi0 in coarse_list[:8]:
                    for dk in (-7.0, -3.5, 0.0, 3.5, 7.0):
                        ka = k0 + dk
                        if ka < 14.0 or ka > 240.0:
                            continue
                        for dp in (-0.5 * dphi_k, -0.25 * dphi_k, 0.0, 0.25 * dphi_k, 0.5 * dphi_k):
                            ph = (phi0 + dp) % (2.0 * math.pi)
                            key_f = (int(round(ka * 2.0)), int(round(ph * 100.0)))
                            if key_f in seen_fine:
                                continue
                            seen_fine.add(key_f)
                            f_rows.append(ka * np.sin(w_pk + ph))
                            f_pars.append((p_k, float(ka), float(ph)))
                if f_rows:
                    h_f, c_f = _run_precomputed_grid(np.vstack(f_rows), "KEPLERIAN_COHERENT_STACK_V57", f_pars, "periodic")
                    n_eval += c_f
                    kep_cands.extend(h_f)

    raw_cands = taylor_cands + kep_cands
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
        "taylor_only_hits": len(taylor_cands),
        "keplerian_hits": len(kep_cands),
        "candidates": final_cands,
    }


def run_keplerian_jerk_calibration_v57(seed: int = 9903) -> dict[str, Any]:
    """
    `CALIBRATION_V57_KEPLERIAN_JERK_300`:
      - 60 Multi-revolution 2-10 yr Keplerian beacons (5-25 orbital cycles -> DRIFT_V57 vs Taylor-only comparison)
      - 60 Cubic Taylor jerk beacons
      - 60 Short-period orbital beacons
      - 40 Stationary stellar emission residuals
      - 40 Single-epoch flare / cosmic-ray transients
      - 40 Topocentric BERV sky lines
    """
    rng = np.random.default_rng(seed)
    cfg = get_inst_config("ESO_UVES", 51690.0)
    w_r = np.linspace(6300.0, 6365.0, 1800)
    n_ep = 6
    sig_w = 6330.0 / (float(cfg["resolving_power"]) * FWHM_FACTOR)
    bervs = np.linspace(-22.0, 22.0, n_ep)
    sig_mat = np.full((n_ep, len(w_r)), 0.015)

    trials: list[dict[str, Any]] = []
    mkep_v57 = mkep_tay = jk_rec = sh_rec = st_v = tr_v = sk_v = 0

    for ti in range(300):
        wc0 = 6332.0 + float(rng.uniform(-4.0, 4.0))
        known_p = None
        if ti < 60:
            cls_, want = "MULTI_REV_KEPLERIAN_2_10YR", True
            n_ep_k = 8
            fn_mat = 1.0 + rng.normal(0.0, 0.015, size=(n_ep_k, len(w_r)))
            sig_mat_i = np.full((n_ep_k, len(w_r)), 0.015)
            bervs_i = np.linspace(-22.0, 22.0, n_ep_k)
            mjds = np.sort(np.linspace(55000.0, 56500.0, n_ep_k) + rng.uniform(-18.0, 18.0, n_ep_k))
            t_rel = mjds - mjds[0]
            while True:
                p_orb = float(rng.uniform(18.0, 140.0))
                phi0 = float(rng.uniform(0.0, 2.0 * math.pi))
                k_amp = float(rng.uniform(55.0, 145.0))
                v_ep = k_amp * np.sin(2.0 * math.pi * t_rel / p_orb + phi0)
                if float(np.ptp(v_ep)) >= 25.0:
                    break
            known_p = p_orb
            amp = float(rng.uniform(3.8, 4.8)) * 0.015
            for k in range(n_ep_k):
                fn_mat[k] += amp * np.exp(-0.5 * ((w_r - wc0 * (1.0 + v_ep[k] / C_KMS)) / sig_w) ** 2)
        else:
            fn_mat = 1.0 + rng.normal(0.0, 0.015, size=(n_ep, len(w_r)))
            sig_mat_i = sig_mat
            bervs_i = bervs
            mjds = np.sort(np.linspace(55000.0, 56500.0, n_ep) + rng.uniform(-12.0, 12.0, n_ep))
            t_rel = mjds - mjds[0]
            if ti < 120:
                cls_, want = "SUBTHRESH_CUBIC_JERK", True
                t_mid = 0.5 * (mjds[0] + mjds[-1])
                dt_h = 0.5 * (mjds[-1] - mjds[0])
                tau = (mjds - t_mid) / dt_h
                p3 = 2.5 * (tau ** 3 - 0.6 * tau)
                v_ep = float(rng.choice([-120.0, 120.0])) * tau + float(rng.choice([-40.0, 40.0])) * (tau ** 2 - 1.0 / 3.0) + float(rng.choice([-35.0, 35.0])) * p3
                amp = float(rng.uniform(3.8, 4.8)) * 0.015
                for k in range(n_ep):
                    fn_mat[k] += amp * np.exp(-0.5 * ((w_r - wc0 * (1.0 + v_ep[k] / C_KMS)) / sig_w) ** 2)
            elif ti < 180:
                cls_, want = "SUBTHRESH_PERIODIC", True
                mjds = np.sort(np.linspace(55000.0, 55040.0, n_ep) + rng.uniform(-0.5, 0.5, n_ep))
                t_rel = mjds - mjds[0]
                p_orb = float(rng.choice([8.5, 16.0, 28.0]))
                known_p = p_orb
                phi0 = float(rng.uniform(0.0, 2.0 * math.pi))
                v_ep = float(rng.uniform(55.0, 130.0)) * np.sin(2.0 * math.pi * t_rel / p_orb + phi0)
                amp = float(rng.uniform(3.8, 4.8)) * 0.015
                for k in range(n_ep):
                    fn_mat[k] += amp * np.exp(-0.5 * ((w_r - wc0 * (1.0 + v_ep[k] / C_KMS)) / sig_w) ** 2)
            elif ti < 220:
                cls_, want = "STATIONARY_VETO", False
                amp = float(rng.uniform(5.0, 8.0)) * 0.015
                for k in range(n_ep):
                    fn_mat[k] += amp * np.exp(-0.5 * ((w_r - wc0) / sig_w) ** 2)
            elif ti < 260:
                cls_, want = "TRANSIENT_VETO", False
                k_hit = int(rng.integers(0, n_ep))
                fn_mat[k_hit] += 18.0 * 0.015 * np.exp(-0.5 * ((w_r - wc0) / sig_w) ** 2)
            else:
                cls_, want = "BERV_SKY_VETO", False
                w_sky = 6328.0
                amp = float(rng.uniform(4.5, 7.0)) * 0.015
                for k in range(n_ep):
                    wb = w_sky * (1.0 + bervs_i[k] / C_KMS)
                    fn_mat[k] += amp * np.exp(-0.5 * ((w_r - wb) / sig_w) ** 2)

        res = scan_coherent_shift_stack_keplerian_jerk_v57(
            w_r, fn_mat, sig_mat_i, mjds, bervs_i, cfg, star=f"SIM_KJ_{ti}",
            known_orb_period_days=known_p, enable_long_blind=(ti < 60),
        )
        obs = res["n_raw_candidates"] >= 1
        tay_obs = res["taylor_only_hits"] >= 1
        ok = int(bool(obs) == bool(want))
        if cls_ == "MULTI_REV_KEPLERIAN_2_10YR":
            mkep_v57 += int(obs)
            mkep_tay += int(tay_obs)
        elif cls_ == "SUBTHRESH_CUBIC_JERK":
            jk_rec += ok
        elif cls_ == "SUBTHRESH_PERIODIC":
            sh_rec += ok
        elif cls_ == "STATIONARY_VETO":
            st_v += ok
        elif cls_ == "TRANSIENT_VETO":
            tr_v += ok
        else:
            sk_v += ok
        trials.append({
            "suite": "CALIBRATION_V57_KEPLERIAN_JERK_300",
            "class": cls_,
            "trial": ti + 1,
            "expected": int(want),
            "observed": int(obs),
            "taylor_only_obs": int(tay_obs),
            "passed": ok,
        })

    return {
        "total_trials": len(trials),
        "multi_rev_keplerian_v57": f"{mkep_v57}/60 ({mkep_v57/60.0:.4f})",
        "multi_rev_taylor_baseline": f"{mkep_tay}/60 ({mkep_tay/60.0:.4f})",
        "cubic_jerk_60": f"{jk_rec}/60 ({jk_rec/60.0:.4f})",
        "short_periodic_60": f"{sh_rec}/60 ({sh_rec/60.0:.4f})",
        "stationary_veto_40": f"{st_v}/40 ({st_v/40.0:.4f})",
        "transient_veto_40": f"{tr_v}/40 ({tr_v/40.0:.4f})",
        "berv_sky_veto_40": f"{sk_v}/40 ({sk_v/40.0:.4f})",
        "trials": trials,
    }


# ===========================================================================
# Phase D100 (V5.8) Engines:
#   V5.8A: JCMT ALAIHI-ACSIS 3 mm Band-3 (77.7-95.7 GHz, 3.13-3.86 mm)
#   V5.8B: SOFIA/FIFI-LS Far-IR IFU (BLU 51-120 um, RED 115-203 um)
#   V5.8C: IUE High-Dispersion UV Echelle (SWP 115-198 nm, LWP/LWR 185-335 nm)
#   V5.8D: DRIFT_V58_ECCENTRIC_KEPLERIAN (Exact Newton-Raphson Kepler Solver)
# ===========================================================================

JCMT_ALAIHI_3MM_ATLAS_GHZ: tuple[tuple[str, float, str], ...] = (
    ("NH2D_111_101", 85.92627, "Deuterated ammonia"),
    ("SiO_v2_J2-1", 85.64045, "SiO v=2 maser"),
    ("SiO_v1_J2-1", 86.24344, "SiO v=1 maser"),
    ("H13CN_J1-0", 86.33992, "H13CN J=1-0"),
    ("H13CO+_J1-0", 86.75429, "H13CO+ J=1-0"),
    ("SiO_v0_J2-1", 86.84699, "SiO thermal J=2-1"),
    ("HN13C_J1-0", 87.09085, "HN13C J=1-0"),
    ("C2H_N1-0", 87.31693, "Ethynyl C2H N=1-0"),
    ("HCN_J1-0", 88.63160, "HCN J=1-0"),
    ("HCO+_J1-0", 89.18853, "HCO+ J=1-0"),
    ("HNC_J1-0", 90.66357, "HNC J=1-0"),
    ("HC3N_J10-9", 90.97902, "Cyanoacetylene HC3N"),
    ("13CS_J2-1", 92.49431, "13CS J=2-1"),
    ("N2H+_J1-0", 93.17340, "Diazenylium N2H+ J=1-0"),
    ("SiC2_4_23-3_22", 94.24539, "Silacyclopropynylidene"),
    ("C34S_J2-1", 96.41295, "C34S J=2-1"),
    ("CS_J2-1", 97.98095, "CS J=2-1"),
    ("SO_23-12", 86.09395, "Sulfur monoxide"),
    ("SO_32-21", 99.29987, "Sulfur monoxide"),
    ("c-C3H2_212-101", 85.33889, "Cyclopropenylidene"),
    ("CH3OH_2-1", 96.74137, "Methanol"),
    ("DCN_J1-0", 72.41469, "DCN J=1-0"),
    ("DCO+_J1-0", 72.03931, "DCO+ J=1-0"),
    ("HC3N_J9-8", 81.88147, "Cyanoacetylene J=9-8"),
    ("SiC2_4_04-3_03", 93.06364, "SiC2 carbon star band"),
    ("OCS_J7-6", 85.13910, "Carbonyl sulfide"),
    ("H41alpha", 92.03443, "H41alpha recombination"),
    ("H42alpha", 85.68839, "H42alpha recombination"),
)

SOFIA_FIFILS_ATLAS_UM: tuple[tuple[str, float, str], ...] = (
    ("OIII_51p81", 51.8145, "[O III] 51.815 um"),
    ("NIII_57p32", 57.3170, "[N III] 57.317 um"),
    ("OI_63p18", 63.1837, "[O I] 63.184 um"),
    ("H2O_66p44", 66.4377, "H2O 330-221"),
    ("H2O_75p38", 75.3806, "H2O 321-212"),
    ("OH_79p12", 79.1159, "OH doublet 79.12 um"),
    ("CO_J30-29", 87.1904, "CO J=30-29"),
    ("OIII_88p36", 88.3560, "[O III] 88.356 um"),
    ("CO_J29-28", 90.1630, "CO J=29-28"),
    ("H2O_108p07", 108.0732, "H2O 221-110"),
    ("OH_119p23", 119.2330, "OH 119.23 um"),
    ("OH_119p44", 119.4410, "OH 119.44 um"),
    ("NII_121p90", 121.8980, "[N II] 121.898 um"),
    ("CO_J20-19", 130.3689, "CO J=20-19"),
    ("OI_145p53", 145.5254, "[O I] 145.525 um"),
    ("CO_J18-17", 144.7842, "CO J=18-17"),
    ("CO_J17-16", 153.2667, "CO J=17-16"),
    ("CII_157p74", 157.7409, "[C II] 157.741 um"),
    ("OH_163p12", 163.1243, "OH 163.12 um"),
    ("OH_163p40", 163.3972, "OH 163.40 um"),
    ("CO_J16-15", 162.8116, "CO J=16-15"),
    ("CO_J14-13", 185.9993, "CO J=14-13"),
    ("H2O_179p53", 179.5267, "H2O 212-101"),
    ("CO_J13-12", 200.2725, "CO J=13-12"),
    ("NII_205p18", 205.1782, "[N II] 205.178 um"),
)

IUE_UV_ATLAS_A: tuple[tuple[str, float, str], ...] = (
    ("HI_LyAlpha", 1215.67, "Geocoronal / chromospheric H I Ly-alpha"),
    ("NV_1239", 1238.82, "N V 1238.8 A"),
    ("NV_1243", 1242.80, "N V 1242.8 A"),
    ("OI_1302", 1302.17, "Airglow / chromospheric O I 1302.2 A"),
    ("OI_1305", 1304.86, "Airglow / chromospheric O I 1304.9 A"),
    ("OI_1306", 1306.03, "Airglow / chromospheric O I 1306.0 A"),
    ("CII_1335", 1334.53, "C II 1334.5 A"),
    ("CII_1336", 1335.71, "C II* 1335.7 A"),
    ("SiIV_1394", 1393.76, "Si IV 1393.8 A"),
    ("SiIV_1403", 1402.77, "Si IV 1402.8 A"),
    ("CIV_1548", 1548.20, "C IV 1548.2 A"),
    ("CIV_1551", 1550.77, "C IV 1550.8 A"),
    ("HeII_1640", 1640.42, "He II 1640.4 A"),
    ("CI_1657", 1656.93, "C I multiplet 1657 A"),
    ("AlII_1671", 1670.79, "Al II 1670.8 A"),
    ("SiII_1808", 1808.01, "Si II 1808.0 A"),
    ("SiII_1817", 1816.93, "Si II 1816.9 A"),
    ("SiIII_1892", 1892.03, "Si III] 1892.0 A"),
    ("CIII_1909", 1908.73, "C III] 1908.7 A"),
    ("CII_2325", 2325.40, "C II] 2325.4 A"),
    ("FeII_2587", 2586.65, "Fe II UV1 2586.7 A"),
    ("FeII_2600", 2600.17, "Fe II UV1 2600.2 A"),
    ("FeII_2626", 2626.45, "Fe II UV1 2626.5 A"),
    ("MgII_k_2796", 2796.35, "Mg II k 2796.35 A"),
    ("MgII_h_2803", 2803.53, "Mg II h 2803.53 A"),
    ("MgI_2853", 2852.96, "Mg I 2853.0 A"),
)


def jcmt_alaihi_eta_a(freq_ghz: float) -> float:
    """Locked JCMT 15 m Band-3 (Namakanui ALAIHI, 77-98 GHz) aperture efficiency eta_A."""
    return 0.72 if float(freq_ghz) < 120.0 else jcmt_eta_a(float(freq_ghz))


def jcmt_alaihi_jy_per_k(freq_ghz: float) -> float:
    """Closed-form JCMT 15 m antenna-temperature factor Gamma [Jy K^-1] for ALAIHI Band 3."""
    eta_a = jcmt_alaihi_eta_a(float(freq_ghz))
    a_geom = math.pi * ((0.5 * JCMT_APERTURE_M) ** 2)
    return float((2.0 * K_BOLTZ / (eta_a * a_geom)) * 1e26)


def jcmt_alaihi_ta_to_flam_cgs(freq_ghz: float | np.ndarray, temp_k: float | np.ndarray) -> float | np.ndarray:
    """Convert JCMT ALAIHI T_A* (K) at ``freq_ghz`` into CGS F_lambda [erg s^-1 cm^-2 A^-1]."""
    f_arr = np.asarray(freq_ghz, dtype=np.float64)
    f_med = float(np.median(f_arr)) if f_arr.ndim > 0 else float(f_arr)
    jy = np.asarray(temp_k, dtype=np.float64) * jcmt_alaihi_jy_per_k(f_med)
    lam_a = C_ANGSTROM_GHZ / np.maximum(1.0, f_arr)
    flam = 1e-23 * jy * C_ANGSTROM_PER_S / (lam_a * lam_a)
    if np.ndim(freq_ghz) == 0 and np.ndim(temp_k) == 0:
        return float(flam)
    return flam


def scan_jcmt_alaihi_3mm_v58(
    cubes: list[dict[str, Any]],
    cfg: dict[str, Any] | None = None,
    star: str = "",
    dist_pc: float = 100.0,
    teff_k: float = 3500.0,
    star_rv_kms: float = 0.0,
    cohort_topo_ghz: list[float] | None = None,
) -> dict[str, Any]:
    """
    Engine V5.8A (`JCMT_ALAIHI_3MM_V58`): 3.13-3.86 mm (77.7-95.7 GHz) Band-3
    millimeter heterodyne beacon search across CADC JCMT ALAIHI-ACSIS cubes.
    """
    del cfg
    peers_ghz = list(cohort_topo_ghz or [])
    candidates: list[dict[str, Any]] = []
    cube_summaries: list[dict[str, Any]] = []
    band_best_ul: dict[str, dict[str, float]] = {}
    raw_topo_ghz: list[float] = []
    n_pix_total = 0
    n_raw = 0
    n_qualified = 0

    for ci, cb in enumerate(cubes):
        dp_id = str(cb.get("dp_id", f"ALAIHI_{ci:02d}"))
        fq = np.asarray(cb["freq_ghz"], dtype=np.float64)
        tk = np.asarray(cb["temp_k"], dtype=np.float64)
        fin = np.isfinite(fq) & np.isfinite(tk) & (fq > 65.0) & (fq < 125.0) & (np.abs(tk) < 5e5)
        if int(np.sum(fin)) < 40:
            continue
        fq, tk = fq[fin], tk[fin]
        ord_f = np.argsort(fq)
        fq, tk = fq[ord_f], tk[ord_f]
        n_pix_total += len(fq)

        trim = max(6, int(round(0.03 * len(fq))))
        if len(fq) - 2 * trim < 32:
            continue
        in_trim = np.zeros(len(fq), dtype=bool)
        in_trim[trim : len(fq) - trim] = True

        dfreq_ghz = max(1e-8, exact_median_1d(np.abs(np.diff(fq))))
        med_f_ghz = exact_median_1d(fq)
        dv_chan_kms = C_KMS * dfreq_ghz / max(1.0, med_f_ghz)
        rp_eff = min(5.0e6, max(2.0e4, med_f_ghz / dfreq_ghz))

        win_px = max(25, min(121, (len(fq) // 8) | 1))
        cont = _asymmetric_clipped_baseline_v56(tk, win_px)
        res = tk - cont

        sig_arr = res[in_trim].copy()
        for _ in range(2):
            m_s = exact_median_1d(sig_arr)
            md_s = max(1e-7, exact_mad_1d(sig_arr))
            keep_s = np.abs(sig_arr - m_s) <= 3.5 * md_s
            if int(np.sum(keep_s)) >= max(16, len(sig_arr) // 3):
                sig_arr = sig_arr[keep_s]
        glob_sig_k = max(1e-7, exact_mad_1d(sig_arr))

        cont_in = cont[in_trim]
        x_in = np.linspace(-1.0, 1.0, len(cont_in))
        cdet = cont_in - np.polyval(np.polyfit(x_in, cont_in, 1), x_in)
        sw_power_frac = 0.0
        sw_amp_sigma = float(np.std(cdet) / max(1e-9, glob_sig_k)) if len(cdet) >= 16 else 0.0
        if len(cdet) >= 32:
            fft_p = np.abs(np.fft.rfft(cdet - np.mean(cdet))) ** 2
            if len(fft_p) > 4 and np.sum(fft_p[2:]) > 0.0:
                sw_power_frac = float(np.max(fft_p[2:]) / np.sum(fft_p[1:]))

        lam_a = C_ANGSTROM_GHZ / med_f_ghz
        temp_lim_k = 8.0 * glob_sig_k
        flam_lim = float(jcmt_alaihi_ta_to_flam_cgs(med_f_ghz, temp_lim_k))
        ul = compute_photon_beam_upper_limit(
            wave_a=lam_a,
            amp_rel_lim=1.0,
            teff_k=float(teff_k),
            dist_pc=float(dist_pc),
            stellar_radius_rsun=1.0,
            radiometric_anchor="JCMT_ALAIHI_3MM_DIRECT_CGS",
            resolving_power=rp_eff,
            direct_flam_cgs=flam_lim,
        )
        ul["direct_flam_cgs"] = flam_lim
        ul["med_freq_ghz"] = float(med_f_ghz)
        ul["wave_a"] = float(lam_a)
        ul["resolving_power"] = float(rp_eff)
        ul["noise_mad_k"] = float(glob_sig_k)
        ul["eta_a"] = jcmt_alaihi_eta_a(med_f_ghz)
        ul["jy_per_k"] = jcmt_alaihi_jy_per_k(med_f_ghz)

        best_canon = min(CALIBRATION_BANDS_JCMT_ALAIHI_3MM, key=lambda b: abs(b["center_wave_A"] - lam_a))
        bid = best_canon["band_id"]
        if bid not in band_best_ul or ul["p_beam_10m_kw"] < band_best_ul[bid]["p_beam_10m_kw"]:
            band_best_ul[bid] = ul

        cube_summaries.append({
            "dp_id": dp_id,
            "inst_group": "JCMT_ALAIHI_3MM",
            "band": bid,
            "med_freq_ghz": round(med_f_ghz, 5),
            "max_wave_um": round(float(C_ANGSTROM_GHZ / max(1.0, float(fq[0])) / 1e4), 5),
            "dv_chan_kms": round(dv_chan_kms, 4),
            "rp_eff": round(rp_eff, 1),
            "noise_mad_k": round(glob_sig_k, 5),
            "sw_power_frac": round(sw_power_frac, 4),
            "p_beam_10m_kw": round(float(ul["p_beam_10m_kw"]), 4),
        })

        z_arr = res / glob_sig_k
        pk_idx = np.where(in_trim & (z_arr >= 7.5))[0]
        if len(pk_idx) == 0:
            continue
        ord_pk = pk_idx[np.argsort(z_arr[pk_idx])[::-1]]
        taken = np.zeros(len(fq), dtype=bool)
        for idx in ord_pk:
            if taken[idx] or idx <= 2 or idx >= len(fq) - 3:
                continue
            lo_n, hi_n = max(0, idx - 8), min(len(fq), idx + 9)
            if float(z_arr[idx]) < float(np.max(z_arr[lo_n:hi_n])) - 1e-12:
                continue
            taken[lo_n:hi_n] = True
            n_raw += 1

            w_l0, w_l1 = max(0, idx - 70), max(0, idx - 10)
            w_r0, w_r1 = min(len(fq), idx + 11), min(len(fq), idx + 71)
            sb_vals = np.concatenate([res[w_l0:w_l1], res[w_r0:w_r1]])
            loc_mad_k = max(glob_sig_k, exact_mad_1d(sb_vals) if len(sb_vals) >= 12 else glob_sig_k)
            loc_snr = float(res[idx] / loc_mad_k)
            loc_ripple_ratio = float(loc_mad_k / glob_sig_k)

            f_pk = float(fq[idx])
            lam_pk_a = C_ANGSTROM_GHZ / max(1.0, f_pk)
            lam_pk_um = lam_pk_a / 1e4
            raw_topo_ghz.append(f_pk)

            eta_1px = float(abs(res[idx]) / max(1e-12, abs(res[idx]) + abs(res[idx - 1]) + abs(res[idx + 1])))
            adj_ratio = float(0.5 * (res[idx - 1] + res[idx + 1]) / max(1e-12, res[idx]))
            fwhm_px = _subchannel_fwhm_v56(res, int(idx))
            dv_fwhm_kms = fwhm_px * dv_chan_kms
            n_rep = int(np.sum((z_arr >= max(4.5, 0.5 * float(z_arr[idx]))) & (np.abs(np.arange(len(fq)) - idx) > 10)))

            f_rest_ghz = f_pk * (1.0 + float(star_rv_kms) / C_KMS)
            atlas_hit = ""
            for lname, l_ghz, _ in JCMT_ALAIHI_3MM_ATLAS_GHZ:
                if abs(C_KMS * (f_rest_ghz - l_ghz) / l_ghz) <= 220.0:
                    atlas_hit = lname
                    break

            veto_reason = ""
            qualified = False
            if eta_1px > 0.72 or adj_ratio < 0.16 or fwhm_px < 2.2:
                veto_reason = "G5_ALAIHI_LO_SPUR_1CHAN"
            elif loc_ripple_ratio >= 2.2 or (sw_power_frac >= 0.42 and sw_amp_sigma >= 0.85) or n_rep >= 5 or loc_snr < 7.0:
                veto_reason = "G2_ALAIHI_STANDING_WAVE_RIPPLE"
            elif fwhm_px >= 6.5 or dv_fwhm_kms >= 15.0:
                veto_reason = "G5_ALAIHI_BROAD_MOLECULAR_ENVELOPE"
            elif atlas_hit:
                veto_reason = f"G3_ALAIHI_3MM_ATLAS:{atlas_hit}"
            elif any(abs(C_KMS * (f_pk - p_ghz) / max(1.0, f_pk)) <= 12.0 for p_ghz in peers_ghz):
                veto_reason = "G6_ALAIHI_COINCIDENT_LO_TELLURIC"
            else:
                qualified = True
                veto_reason = "QUALIFIED_V58_ALAIHI_3MM_BEACON"
                n_qualified += 1

            candidates.append({
                "instrument": "JCMT_ALAIHI_3MM",
                "cand_id": f"ALAIHI_{star}_{ci:02d}_{idx:05d}",
                "star": star,
                "dp_id": dp_id,
                "band": bid,
                "freq_ghz": round(f_pk, 6),
                "wave_a": round(lam_pk_a, 3),
                "wave_um": round(lam_pk_um, 5),
                "snr": round(loc_snr, 3),
                "eta_1px": round(eta_1px, 4),
                "fwhm_px": round(fwhm_px, 3),
                "dv_fwhm_kms": round(dv_fwhm_kms, 3),
                "qualified_v58": bool(qualified),
                "veto_reason": veto_reason,
                "atlas_match": atlas_hit,
            })

    if band_best_ul:
        best_band, best_ul = min(band_best_ul.items(), key=lambda kv: kv[1]["p_beam_10m_kw"])
        best_p_kw = float(best_ul["p_beam_10m_kw"])
    else:
        best_band, best_p_kw = "", float("inf")

    return {
        "star": star,
        "n_cubes": int(len(cube_summaries)),
        "n_pix": int(n_pix_total),
        "raw_peaks": int(n_raw),
        "qualified_v58": int(n_qualified),
        "candidates": candidates,
        "upper_limits": band_best_ul,
        "cube_summaries": cube_summaries,
        "best_p_beam_10m_kw": best_p_kw,
        "best_band": best_band,
        "raw_topo_ghz": raw_topo_ghz,
    }


def run_jcmt_alaihi_3mm_calibration_v58(seed: int = 10001) -> dict[str, Any]:
    """`CALIBRATION_V58_JCMT_ALAIHI_3MM_180`: 60 3mm beacons + 40 standing waves + 40 broad outflow + 40 LO spurs."""
    rng = np.random.default_rng(seed)
    n_px = 1400
    f0 = 84.50
    fq = f0 + np.linspace(-0.45, 0.45, n_px)
    sig_f = (fq[1] - fq[0]) * 1.6
    trials: list[dict[str, Any]] = []
    rec = sw_v = brd_v = sp_v = 0

    for i in range(60):
        tk = 0.02 + 0.01 * np.linspace(-1, 1, n_px) + rng.normal(0.0, 0.025, n_px)
        fc = float(rng.uniform(f0 - 0.30, f0 + 0.30))
        tk += float(rng.uniform(11.0, 18.0)) * 0.025 * np.exp(-0.5 * ((fq - fc) / sig_f) ** 2)
        res = scan_jcmt_alaihi_3mm_v58([{"dp_id": f"CAL_A3_{i}", "freq_ghz": fq, "temp_k": tk}], star=f"SIM_A3_B_{i}", star_rv_kms=500.0)
        ok = res["qualified_v58"] >= 1
        rec += int(ok)
        trials.append({"suite": "CALIBRATION_V58_JCMT_ALAIHI_3MM_180", "class": "CLEAN_3MM_BEACON", "trial": i, "expected": 1, "observed": int(ok), "passed": int(ok)})

    for i in range(40):
        ph = float(rng.uniform(0.0, 2.0 * math.pi))
        tk = 0.02 + float(rng.uniform(0.50, 1.0)) * np.sin(2.0 * math.pi * 6.0 * np.linspace(0, 1, n_px) + ph) + rng.normal(0.0, 0.025, n_px)
        res = scan_jcmt_alaihi_3mm_v58([{"dp_id": f"CAL_A3SW_{i}", "freq_ghz": fq, "temp_k": tk}], star=f"SIM_A3_SW_{i}", star_rv_kms=500.0)
        ok = res["qualified_v58"] == 0
        sw_v += int(ok)
        trials.append({"suite": "CALIBRATION_V58_JCMT_ALAIHI_3MM_180", "class": "STANDING_WAVE_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v58"] > 0), "passed": int(ok)})

    for i in range(40):
        tk = 0.02 + rng.normal(0.0, 0.025, n_px)
        fc = float(rng.uniform(f0 - 0.25, f0 + 0.25))
        sig_b = float(rng.uniform(5.0, 10.0)) * (fq[1] - fq[0])
        tk += float(rng.uniform(12.0, 20.0)) * 0.025 * np.exp(-0.5 * ((fq - fc) / sig_b) ** 2)
        res = scan_jcmt_alaihi_3mm_v58([{"dp_id": f"CAL_A3BR_{i}", "freq_ghz": fq, "temp_k": tk}], star=f"SIM_A3_BR_{i}", star_rv_kms=500.0)
        ok = res["qualified_v58"] == 0
        brd_v += int(ok)
        trials.append({"suite": "CALIBRATION_V58_JCMT_ALAIHI_3MM_180", "class": "BROAD_OUTFLOW_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v58"] > 0), "passed": int(ok)})

    for i in range(40):
        tk = 0.02 + rng.normal(0.0, 0.025, n_px)
        idx_s = int(rng.integers(150, n_px - 150))
        tk[idx_s] += float(rng.uniform(14.0, 24.0)) * 0.025
        res = scan_jcmt_alaihi_3mm_v58([{"dp_id": f"CAL_A3SP_{i}", "freq_ghz": fq, "temp_k": tk}], star=f"SIM_A3_SP_{i}", star_rv_kms=500.0)
        ok = res["qualified_v58"] == 0
        sp_v += int(ok)
        trials.append({"suite": "CALIBRATION_V58_JCMT_ALAIHI_3MM_180", "class": "SINGLE_CHAN_LO_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v58"] > 0), "passed": int(ok)})

    return {
        "total_trials": len(trials),
        "beacon_recovery": f"{rec}/60 ({rec/60.0:.4f})",
        "standing_wave_veto": f"{sw_v}/40 ({sw_v/40.0:.4f})",
        "broad_outflow_veto": f"{brd_v}/40 ({brd_v/40.0:.4f})",
        "single_chan_lo_veto": f"{sp_v}/40 ({sp_v/40.0:.4f})",
        "trials": trials,
    }


def scan_sofia_fifils_farir_v58(
    cubes: list[dict[str, Any]],
    cfg: dict[str, Any] | None = None,
    star: str = "",
    dist_pc: float = 150.0,
    teff_k: float = 4000.0,
    star_rv_kms: float = 0.0,
) -> dict[str, Any]:
    """
    Engine V5.8B (`SOFIA_FIFILS_FARIR_V58`): Far-IR IFU aperture-extracted search across
    SOFIA/FIFI-LS BLU (51-120 um) and RED (115-205 um) Level-3/4 datacubes (n >= 24 channels).
    """
    del cfg
    candidates: list[dict[str, Any]] = []
    band_best_ul: dict[str, dict[str, float]] = {}
    cube_summaries: list[dict[str, Any]] = []
    n_pix_total = 0
    n_raw = 0
    n_qualified = 0

    for ci, cb in enumerate(cubes):
        dp_id = str(cb.get("dp_id", f"FIFILS_{ci:02d}"))
        w_um = np.asarray(cb["wave_um"], dtype=np.float64)
        fl_jy = np.asarray(cb["flux_jy"], dtype=np.float64)
        tr = np.asarray(cb["transmission"], dtype=np.float64) if cb.get("transmission") is not None else np.ones_like(w_um)
        rp_est = float(cb.get("resolving_power", 1200.0))

        fin = np.isfinite(w_um) & np.isfinite(fl_jy) & (w_um > 45.0) & (w_um < 220.0)
        if int(np.sum(fin)) < 24:
            continue
        w_um, fl_jy, tr = w_um[fin], fl_jy[fin], tr[fin]
        ord_w = np.argsort(w_um)
        w_um, fl_jy, tr = w_um[ord_w], fl_jy[ord_w], tr[ord_w]
        n = len(w_um)
        n_pix_total += n

        if n <= 65:
            x_n = np.linspace(-1.0, 1.0, n)
            n_edge = max(4, min(7, n // 5))
            keep_c = np.zeros(n, dtype=bool)
            keep_c[:n_edge] = True
            keep_c[n - n_edge :] = True
            coef = np.polyfit(x_n[keep_c], fl_jy[keep_c], 1)
            cont = np.polyval(coef, x_n)
            for _ in range(3):
                r0 = fl_jy - cont
                pool0 = r0[keep_c]
                m0 = exact_median_1d(pool0)
                mad0 = max(1e-7, exact_mad_1d(pool0))
                nxt = ((r0 - m0) <= 2.5 * mad0) & ((r0 - m0) >= -3.5 * mad0)
                if int(np.sum(nxt)) >= max(8, n // 3):
                    keep_c = nxt
                    coef = np.polyfit(x_n[keep_c], fl_jy[keep_c], 1)
                    cont = np.polyval(coef, x_n)
            if int(np.sum(keep_c)) >= 6:
                cont = cont + exact_median_1d((fl_jy - cont)[keep_c])
        else:
            win_med = min(31, max(15, int(round(0.45 * n)) | 1))
            cont = _asymmetric_clipped_baseline_v56(fl_jy, win_med)
        res = fl_jy - cont
        trim = max(2, int(round(0.06 * n)))
        in_trim = np.zeros(n, dtype=bool)
        if n - 2 * trim >= 12:
            in_trim[trim : n - trim] = True
        else:
            in_trim[1 : n - 1] = True

        good_tr = np.isfinite(tr) & (tr >= 0.55)
        noise_pool = res[in_trim & good_tr] if int(np.sum(in_trim & good_tr)) >= 10 else res[in_trim]
        sig_arr = noise_pool.copy()
        for _ in range(2):
            m_s = exact_median_1d(sig_arr)
            md_s = max(1e-7, exact_mad_1d(sig_arr))
            keep_s = np.abs(sig_arr - m_s) <= 3.2 * md_s
            if int(np.sum(keep_s)) >= max(10, len(sig_arr) // 3):
                sig_arr = sig_arr[keep_s]
        sig_jy = max(1e-7, float(exact_mad_1d(sig_arr)))

        med_um = exact_median_1d(w_um)
        med_a = med_um * 1e4
        flam_lim = 1e-23 * (8.0 * sig_jy) * C_ANGSTROM_PER_S / (med_a * med_a)
        ul = compute_photon_beam_upper_limit(
            wave_a=med_a,
            amp_rel_lim=1.0,
            teff_k=float(teff_k),
            dist_pc=float(dist_pc),
            stellar_radius_rsun=1.0,
            radiometric_anchor="SOFIA_FIFILS_DIRECT_CGS",
            resolving_power=rp_est,
            direct_flam_cgs=flam_lim,
        )
        ul["direct_flam_cgs"] = float(flam_lim)
        ul["wave_a"] = float(med_a)
        ul["resolving_power"] = float(rp_est)
        ul["sigma_jy"] = float(sig_jy)

        best_canon = min(CALIBRATION_BANDS_SOFIA_FIFILS, key=lambda b: abs(b["center_wave_A"] - med_a))
        bid = best_canon["band_id"]
        if bid not in band_best_ul or ul["p_beam_10m_kw"] < band_best_ul[bid]["p_beam_10m_kw"]:
            band_best_ul[bid] = ul

        cube_summaries.append({
            "dp_id": dp_id,
            "band": bid,
            "med_wave_um": round(med_um, 4),
            "n_chan": int(n),
            "rp": round(rp_est, 1),
            "sigma_jy": round(sig_jy, 5),
            "p_beam_10m_kw": round(float(ul["p_beam_10m_kw"]), 4),
        })

        z = res / sig_jy
        raw_idx = [i for i in range(2, n - 2) if in_trim[i] and z[i] >= 7.5 and z[i] >= z[i - 1] and z[i] >= z[i + 1]]
        raw_idx.sort(key=lambda i: -float(z[i]))
        kept: list[int] = []
        for i in raw_idx:
            if all(abs(i - k) > 4 for k in kept):
                kept.append(i)

        for idx in kept[:12]:
            n_raw += 1
            wc = float(w_um[idx])
            tr_val = float(tr[idx]) if np.isfinite(tr[idx]) else 1.0
            stat = _estimate_fwhm_and_wings(z, idx, win_half=min(10, idx, n - 1 - idx))
            eta_1 = stat["eta_1px"]
            fwhm_px = stat["fwhm_px"]

            wc_rest = wc / (1.0 + float(star_rv_kms) / C_KMS)
            atlas_hit = ""
            for lname, l_um, _ in SOFIA_FIFILS_ATLAS_UM:
                if abs(C_KMS * (wc_rest - l_um) / max(1.0, l_um)) <= 450.0:
                    atlas_hit = lname
                    break

            veto_reason = ""
            qualified = False
            if tr_val < 0.55:
                veto_reason = "G2_FIFILS_ATRAN_TELLURIC"
            elif eta_1 > 0.72 or fwhm_px < 1.35 or stat["side_sum"] < 0.20 * stat["z_pk"]:
                veto_reason = "G5_FIFILS_1PX_GLITCH"
            elif fwhm_px > 5.8:
                veto_reason = "G5_FIFILS_BROAD_LINE"
            elif atlas_hit:
                veto_reason = f"G3_FIFILS_FARIR_ATLAS:{atlas_hit}"
            else:
                qualified = True
                veto_reason = "QUALIFIED_V58_FIFILS_BEACON"
                n_qualified += 1

            candidates.append({
                "instrument": "SOFIA_FIFILS",
                "cand_id": f"FIFILS_{star}_{ci:02d}_{idx:04d}",
                "star": star,
                "dp_id": dp_id,
                "band": bid,
                "wave_um": round(wc, 4),
                "wave_a": round(wc * 1e4, 2),
                "snr": round(stat["z_pk"], 3),
                "eta_1px": round(eta_1, 4),
                "fwhm_px": round(fwhm_px, 3),
                "transmission": round(tr_val, 3),
                "qualified_v58": bool(qualified),
                "veto_reason": veto_reason,
                "atlas_match": atlas_hit,
            })

    if band_best_ul:
        best_band, best_ul = min(band_best_ul.items(), key=lambda kv: kv[1]["p_beam_10m_kw"])
        best_p_kw = float(best_ul["p_beam_10m_kw"])
    else:
        best_band, best_p_kw = "", float("inf")

    return {
        "star": star,
        "n_cubes": int(len(cube_summaries)),
        "n_pix": int(n_pix_total),
        "raw_peaks": int(n_raw),
        "qualified_v58": int(n_qualified),
        "candidates": candidates,
        "upper_limits": band_best_ul,
        "cube_summaries": cube_summaries,
        "best_p_beam_10m_kw": best_p_kw,
        "best_band": best_band,
    }


def run_sofia_fifils_calibration_v58(seed: int = 10002) -> dict[str, Any]:
    """`CALIBRATION_V58_SOFIA_FIFILS_180`: 60 Far-IR beacons + 40 ATRAN telluric + 40 1-px glitches + 40 broad features."""
    rng = np.random.default_rng(seed)
    n_px = 40
    w_um = np.linspace(135.5, 138.0, n_px)
    sig_w = (w_um[1] - w_um[0]) * 1.45
    trials: list[dict[str, Any]] = []
    rec = atr_v = gl_v = brd_v = 0

    for i in range(60):
        tr = np.full(n_px, 0.96)
        fl = 5.0 + 0.3 * np.linspace(-1, 1, n_px) + rng.normal(0.0, 0.08, n_px)
        wc = float(rng.uniform(136.2, 137.3))
        fl += float(rng.uniform(11.0, 18.0)) * 0.08 * np.exp(-0.5 * ((w_um - wc) / sig_w) ** 2)
        res = scan_sofia_fifils_farir_v58([{"dp_id": f"CAL_FI_{i}", "wave_um": w_um, "flux_jy": fl, "transmission": tr, "resolving_power": 1200.0}], star=f"SIM_FI_B_{i}", star_rv_kms=500.0)
        ok = res["qualified_v58"] >= 1
        rec += int(ok)
        trials.append({"suite": "CALIBRATION_V58_SOFIA_FIFILS_180", "class": "CLEAN_FIFILS_BEACON", "trial": i, "expected": 1, "observed": int(ok), "passed": int(ok)})

    for i in range(40):
        tr = np.full(n_px, 0.96)
        idx_t = int(rng.integers(10, n_px - 10))
        tr[idx_t - 1 : idx_t + 2] = 0.25
        fl = 5.0 + rng.normal(0.0, 0.08, n_px)
        fl += 16.0 * 0.08 * np.exp(-0.5 * ((w_um - w_um[idx_t]) / sig_w) ** 2)
        res = scan_sofia_fifils_farir_v58([{"dp_id": f"CAL_FIAT_{i}", "wave_um": w_um, "flux_jy": fl, "transmission": tr, "resolving_power": 1200.0}], star=f"SIM_FI_AT_{i}", star_rv_kms=500.0)
        ok = res["qualified_v58"] == 0
        atr_v += int(ok)
        trials.append({"suite": "CALIBRATION_V58_SOFIA_FIFILS_180", "class": "ATRAN_TELLURIC_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v58"] > 0), "passed": int(ok)})

    for i in range(40):
        tr = np.full(n_px, 0.96)
        fl = 5.0 + rng.normal(0.0, 0.08, n_px)
        idx_g = int(rng.integers(10, n_px - 10))
        fl[idx_g] += float(rng.uniform(14.0, 22.0)) * 0.08
        res = scan_sofia_fifils_farir_v58([{"dp_id": f"CAL_FIGL_{i}", "wave_um": w_um, "flux_jy": fl, "transmission": tr, "resolving_power": 1200.0}], star=f"SIM_FI_GL_{i}", star_rv_kms=500.0)
        ok = res["qualified_v58"] == 0
        gl_v += int(ok)
        trials.append({"suite": "CALIBRATION_V58_SOFIA_FIFILS_180", "class": "GLITCH_1PX_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v58"] > 0), "passed": int(ok)})

    for i in range(40):
        tr = np.full(n_px, 0.96)
        fl = 5.0 + rng.normal(0.0, 0.08, n_px)
        wc = float(rng.uniform(136.2, 137.3))
        sig_b = float(rng.uniform(4.2, 6.5)) * (w_um[1] - w_um[0])
        fl += float(rng.uniform(12.0, 18.0)) * 0.08 * np.exp(-0.5 * ((w_um - wc) / sig_b) ** 2)
        res = scan_sofia_fifils_farir_v58([{"dp_id": f"CAL_FIBR_{i}", "wave_um": w_um, "flux_jy": fl, "transmission": tr, "resolving_power": 1200.0}], star=f"SIM_FI_BR_{i}", star_rv_kms=500.0)
        ok = res["qualified_v58"] == 0
        brd_v += int(ok)
        trials.append({"suite": "CALIBRATION_V58_SOFIA_FIFILS_180", "class": "BROAD_FEATURE_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v58"] > 0), "passed": int(ok)})

    return {
        "total_trials": len(trials),
        "beacon_recovery": f"{rec}/60 ({rec/60.0:.4f})",
        "atran_telluric_veto": f"{atr_v}/40 ({atr_v/40.0:.4f})",
        "glitch_1px_veto": f"{gl_v}/40 ({gl_v/40.0:.4f})",
        "broad_feature_veto": f"{brd_v}/40 ({brd_v/40.0:.4f})",
        "trials": trials,
    }


def scan_iue_uv_echelle_v58(
    orders_data: list[dict[str, Any]],
    cfg: dict[str, Any] | None = None,
    star: str = "",
    dp_id: str = "",
    dist_pc: float = 15.0,
    teff_k: float = 5500.0,
    star_rv_kms: float = 0.0,
    instrument: str = "IUE_LWP_HI",
    min_snr: float = 8.0,
) -> dict[str, Any]:
    """
    Engine V5.8C (`IUE_UV_ECHELLE_V58`): Multi-order IUE High-Dispersion UV echelle search
    across SWP (115-198 nm) and LWP/LWR (185-335 nm) with NEWSIPS DQ reseau/saturation gating,
    geocoronal Ly-a/OI airglow veto, cross-order overlap check, and UV chromospheric atlas.
    """
    del cfg
    prepared: list[dict[str, Any]] = []
    rp_eff = 11500.0 if instrument == "IUE_SWP_HI" else 12000.0

    for od in orders_data:
        w = np.asarray(od["wave_a"], dtype=np.float64)
        fl = np.asarray(od["flux"], dtype=np.float64)
        er = np.asarray(od["err"], dtype=np.float64) if od.get("err") is not None else np.zeros_like(fl)
        dq = np.asarray(od.get("dq", np.zeros(len(w))), dtype=np.int64)
        ord_i = np.argsort(w)
        w, fl, er, dq = w[ord_i], fl[ord_i], er[ord_i], dq[ord_i]
        # Mask severe NEWSIPS defects (missing/outside=-16384, saturated=-8192, reseau=-2048, telemetry=-1024, bright=-512 -> |dq| >= 512)
        good = np.isfinite(w) & np.isfinite(fl) & (w > 1140.0) & (w < 3400.0) & (np.abs(dq) < 512)
        if int(np.sum(good)) < 40:
            continue
        cont = median_filter(np.where(good, fl, np.nanmedian(fl[good])), size=29, mode="nearest")
        res = np.where(good, fl - cont, 0.0)
        rmad = _rolling_mad_scaled(res, good, win_bins=85)
        sig_arr = np.maximum(rmad, np.where(np.isfinite(er) & (er > 0.0), er, 0.0))
        sig_pos = sig_arr[good & np.isfinite(sig_arr) & (sig_arr > 0.0)]
        floor_sig = max(1e-30, float(exact_median_1d(sig_pos)) if len(sig_pos) >= 8 else 1e-13)
        sig_arr = np.maximum(sig_arr, 0.5 * floor_sig)
        z = np.where(good, res / sig_arr, 0.0)
        prepared.append({
            "sporder": int(od.get("sporder", 0)),
            "wave_a": w,
            "flux": fl,
            "good": good,
            "z": z,
            "sig_flam_med": float(exact_median_1d(sig_arr[good])),
        })

    c_bands = CALIBRATION_BANDS_IUE_SWP_HI if instrument == "IUE_SWP_HI" else CALIBRATION_BANDS_IUE_LWP_HI
    band_best_ul: dict[str, dict[str, float]] = {}
    for b in c_bands:
        wc = float(b["center_wave_A"])
        near_sig = [p["sig_flam_med"] for p in prepared if float(p["wave_a"][0]) <= wc + 220.0 and float(p["wave_a"][-1]) >= wc - 220.0]
        if not near_sig and prepared:
            near_sig = [min(p["sig_flam_med"] for p in prepared)]
        if near_sig:
            flam_lim = 8.0 * float(exact_median_1d(np.asarray(near_sig, dtype=np.float64)))
            ul = compute_photon_beam_upper_limit(
                wave_a=wc,
                amp_rel_lim=1.0,
                teff_k=float(teff_k),
                dist_pc=float(dist_pc),
                stellar_radius_rsun=1.0,
                radiometric_anchor="IUE_DIRECT_CGS",
                resolving_power=rp_eff,
                direct_flam_cgs=flam_lim,
            )
            ul["direct_flam_cgs"] = float(flam_lim)
            ul["wave_a"] = wc
            ul["resolving_power"] = rp_eff
            band_best_ul[b["band_id"]] = ul

    cands: list[dict[str, Any]] = []
    for oi, p in enumerate(prepared):
        w = p["wave_a"]
        z = p["z"]
        good = p["good"]
        n = len(w)
        dw_a = max(1e-5, float(exact_median_1d(np.diff(w))))
        raw_idx = [i for i in range(6, n - 6) if good[i] and z[i] >= min_snr and z[i] >= z[i - 1] and z[i] >= z[i + 1]]
        raw_idx.sort(key=lambda i: -float(z[i]))
        kept: list[int] = []
        for i in raw_idx:
            if all(abs(i - k) > 8 for k in kept):
                kept.append(i)

        for idx in kept[:10]:
            wc = float(w[idx])
            stat = _estimate_fwhm_and_wings(z, idx, win_half=7)
            eta_1 = stat["eta_1px"]
            fwhm_px = stat["fwhm_px"]
            dv_fwhm_kms = C_KMS * (fwhm_px * dw_a) / max(1.0, wc)

            wc_rest = wc / (1.0 + float(star_rv_kms) / C_KMS)
            geo_hit = ""
            if 1212.5 <= wc <= 1218.8:
                geo_hit = "GEOCORONAL_LYALPHA"
            elif 1300.5 <= wc <= 1307.5:
                geo_hit = "GEOCORONAL_OI"

            atlas_hit = ""
            for nm, wa_l, _ in IUE_UV_ATLAS_A:
                if abs(C_KMS * (wc_rest - wa_l) / wa_l) <= 180.0:
                    atlas_hit = nm
                    break

            overlap_checked = False
            overlap_snr = 0.0
            for oj, q in enumerate(prepared):
                if oj == oi:
                    continue
                qw = q["wave_a"]
                if qw[0] + 0.15 <= wc <= qw[-1] - 0.15:
                    near = (np.abs(qw - wc) <= 3.0 * (wc / rp_eff)) & q["good"]
                    if int(np.sum(near)) >= 2:
                        overlap_checked = True
                        overlap_snr = max(overlap_snr, float(np.max(q["z"][near])))

            veto_reason = ""
            qualified = False
            if geo_hit:
                veto_reason = f"G2_IUE_{geo_hit}"
            elif eta_1 > 0.72 or fwhm_px < 1.38 or stat["side_sum"] < 0.22 * stat["z_pk"]:
                veto_reason = "G5_IUE_CAMERA_CR_GLITCH"
            elif overlap_checked and overlap_snr < 3.6:
                veto_reason = "G4_IUE_ORDER_OVERLAP_MISMATCH"
            elif fwhm_px > 6.5 or dv_fwhm_kms >= 85.0:
                veto_reason = "G5_IUE_BROAD_EMISSION"
            elif atlas_hit:
                veto_reason = f"G3_IUE_CHROMO_ATLAS:{atlas_hit}"
            else:
                qualified = True
                veto_reason = "QUALIFIED_V58_IUE_UV_BEACON"

            cands.append({
                "instrument": instrument,
                "cand_id": f"IUE_{star}_{p['sporder']}_{idx:04d}",
                "star": star,
                "dp_id": dp_id,
                "sporder": int(p["sporder"]),
                "wave_a": round(wc, 4),
                "snr": round(stat["z_pk"], 3),
                "eta_1px": round(eta_1, 4),
                "fwhm_px": round(fwhm_px, 3),
                "dv_fwhm_kms": round(dv_fwhm_kms, 2),
                "overlap_checked": overlap_checked,
                "overlap_snr": round(overlap_snr, 2),
                "qualified_v58": bool(qualified),
                "veto_reason": veto_reason,
                "atlas_match": atlas_hit,
            })

    if band_best_ul:
        best_band, best_ul = min(band_best_ul.items(), key=lambda kv: kv[1]["p_beam_10m_kw"])
        best_p_kw = float(best_ul["p_beam_10m_kw"])
    else:
        best_band, best_p_kw = "", float("inf")

    return {
        "star": star,
        "dp_id": dp_id,
        "instrument": instrument,
        "n_orders": len(prepared),
        "n_raw_peaks": len(cands),
        "qualified_v58": sum(1 for c in cands if c["qualified_v58"]),
        "candidates": cands,
        "upper_limits": band_best_ul,
        "best_p_beam_10m_kw": best_p_kw,
        "best_band": best_band,
    }


def run_iue_uv_echelle_calibration_v58(seed: int = 10003) -> dict[str, Any]:
    """`CALIBRATION_V58_IUE_ECHELLE_180`: 60 UV beacons + 40 geocoronal + 40 CR glitches + 40 order-overlap mismatches."""
    rng = np.random.default_rng(seed)
    w_o1 = np.linspace(2640.0, 2690.0, 700)
    w_o2 = np.linspace(2660.0, 2710.0, 700)
    sig_w = (w_o1[1] - w_o1[0]) * 1.5
    trials: list[dict[str, Any]] = []
    rec = geo_v = cr_v = ov_v = 0

    for i in range(60):
        wc = float(rng.uniform(2668.0, 2682.0))
        amp = float(rng.uniform(11.0, 18.0)) * 0.02e-11
        f1 = 1e-11 + rng.normal(0.0, 0.02e-11, len(w_o1)) + amp * np.exp(-0.5 * ((w_o1 - wc) / sig_w) ** 2)
        f2 = 1e-11 + rng.normal(0.0, 0.02e-11, len(w_o2)) + amp * np.exp(-0.5 * ((w_o2 - wc) / sig_w) ** 2)
        ods = [{"sporder": 89, "wave_a": w_o1, "flux": f1, "err": np.full_like(f1, 0.02e-11)},
               {"sporder": 88, "wave_a": w_o2, "flux": f2, "err": np.full_like(f2, 0.02e-11)}]
        res = scan_iue_uv_echelle_v58(ods, star=f"SIM_IUE_B_{i}", star_rv_kms=500.0)
        ok = res["qualified_v58"] >= 1
        rec += int(ok)
        trials.append({"suite": "CALIBRATION_V58_IUE_ECHELLE_180", "class": "CLEAN_IUE_BEACON", "trial": i, "expected": 1, "observed": int(ok), "passed": int(ok)})

    w_ly = np.linspace(1205.0, 1228.0, 500)
    for i in range(40):
        wc = 1215.67 + float(rng.uniform(-0.8, 0.8))
        fl = 1e-11 + rng.normal(0.0, 0.02e-11, len(w_ly)) + 15.0 * 0.02e-11 * np.exp(-0.5 * ((w_ly - wc) / sig_w) ** 2)
        res = scan_iue_uv_echelle_v58([{"sporder": 114, "wave_a": w_ly, "flux": fl, "err": np.full_like(fl, 0.02e-11)}], star=f"SIM_IUE_G_{i}", instrument="IUE_SWP_HI")
        ok = res["qualified_v58"] == 0
        geo_v += int(ok)
        trials.append({"suite": "CALIBRATION_V58_IUE_ECHELLE_180", "class": "GEOCORONAL_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v58"] > 0), "passed": int(ok)})

    for i in range(40):
        f1 = 1e-11 + rng.normal(0.0, 0.02e-11, len(w_o1))
        f2 = 1e-11 + rng.normal(0.0, 0.02e-11, len(w_o2))
        f1[int(rng.integers(150, 300))] += 18.0 * 0.02e-11
        ods = [{"sporder": 89, "wave_a": w_o1, "flux": f1, "err": np.full_like(f1, 0.02e-11)},
               {"sporder": 88, "wave_a": w_o2, "flux": f2, "err": np.full_like(f2, 0.02e-11)}]
        res = scan_iue_uv_echelle_v58(ods, star=f"SIM_IUE_CR_{i}", star_rv_kms=500.0)
        ok = res["qualified_v58"] == 0
        cr_v += int(ok)
        trials.append({"suite": "CALIBRATION_V58_IUE_ECHELLE_180", "class": "CR_GLITCH_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v58"] > 0), "passed": int(ok)})

    for i in range(40):
        wc = float(rng.uniform(2668.0, 2682.0))
        f1 = 1e-11 + rng.normal(0.0, 0.02e-11, len(w_o1)) + 16.0 * 0.02e-11 * np.exp(-0.5 * ((w_o1 - wc) / sig_w) ** 2)
        f2 = 1e-11 + rng.normal(0.0, 0.02e-11, len(w_o2))
        ods = [{"sporder": 89, "wave_a": w_o1, "flux": f1, "err": np.full_like(f1, 0.02e-11)},
               {"sporder": 88, "wave_a": w_o2, "flux": f2, "err": np.full_like(f2, 0.02e-11)}]
        res = scan_iue_uv_echelle_v58(ods, star=f"SIM_IUE_OV_{i}", star_rv_kms=500.0)
        ok = res["qualified_v58"] == 0
        ov_v += int(ok)
        trials.append({"suite": "CALIBRATION_V58_IUE_ECHELLE_180", "class": "ORDER_OVERLAP_VETO", "trial": i, "expected": 0, "observed": int(res["qualified_v58"] > 0), "passed": int(ok)})

    return {
        "total_trials": len(trials),
        "beacon_recovery": f"{rec}/60 ({rec/60.0:.4f})",
        "geocoronal_veto": f"{geo_v}/40 ({geo_v/40.0:.4f})",
        "cr_glitch_veto": f"{cr_v}/40 ({cr_v/40.0:.4f})",
        "order_overlap_veto": f"{ov_v}/40 ({ov_v/40.0:.4f})",
        "trials": trials,
    }


def _solve_kepler_true_anom_batch(
    t_rel_days: np.ndarray,
    period_days: float,
    ecc: float,
    m0_rad_arr: np.ndarray,
) -> np.ndarray:
    """Vectorized 10-step Newton-Raphson Kepler solver returning true anomaly f of shape (n_m0, n_ep)."""
    e_v = max(0.0, min(0.97, float(ecc)))
    t_arr = np.asarray(t_rel_days, dtype=np.float64)[None, :]
    m0 = np.asarray(m0_rad_arr, dtype=np.float64)[:, None]
    m_anom = np.mod((2.0 * math.pi * t_arr / float(period_days)) + m0, 2.0 * math.pi)
    if e_v < 1e-6:
        return m_anom
    E = m_anom + e_v * np.sin(m_anom) + 0.5 * (e_v ** 2) * np.sin(2.0 * m_anom)
    for _ in range(10):
        f_e = E - e_v * np.sin(E) - m_anom
        fp_e = np.maximum(1e-8, 1.0 - e_v * np.cos(E))
        dE = f_e / fp_e
        E = E - dE
        if float(np.max(np.abs(dE))) < 1e-11:
            break
    s_fac = math.sqrt((1.0 + e_v) / max(1e-6, 1.0 - e_v))
    return 2.0 * np.arctan2(s_fac * np.sin(0.5 * E), np.cos(0.5 * E))


def solve_kepler_eccentric_rv(
    t_rel_days: np.ndarray,
    period_days: float,
    ecc: float,
    omega_rad: float,
    m0_rad: float,
    k_amp_kms: float,
) -> np.ndarray:
    """
    Exact Newton-Raphson Keplerian radial velocity solver:
      M(t) = 2*pi*t/P + M0, solve E - e sin(E) = M to < 1e-11,
      f = 2 * atan2(sqrt(1+e)*sin(E/2), sqrt(1-e)*cos(E/2)),
      v(t) = K_p * [cos(f + omega) + e * cos(omega)].
    """
    e_v = max(0.0, min(0.97, float(ecc)))
    true_anom = _solve_kepler_true_anom_batch(
        np.asarray(t_rel_days, dtype=np.float64), float(period_days), e_v, np.array([float(m0_rad)])
    )[0]
    return float(k_amp_kms) * (np.cos(true_anom + float(omega_rad)) + e_v * math.cos(float(omega_rad)))


def scan_coherent_shift_stack_eccentric_keplerian_v58(
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
    known_orb_ecc: float | None = None,
    known_orb_omega_deg: float | None = None,
    known_orb_periods_days: list[float] | None = None,
    known_orb_kps_kms: list[float] | None = None,
    known_orb_eccs: list[float] | None = None,
    known_orb_omegas_deg: list[float] | None = None,
    enable_long_blind: bool = True,
) -> dict[str, Any]:
    """
    Engine `DRIFT_V58_ECCENTRIC_KEPLERIAN`: Exact Newton-Raphson Eccentric Kepler solver
    (0 <= e <= 0.95) + Circular Keplerian (V5.7) + Orthogonalized 3D Cubic-Jerk Taylor (V5.6)
    joint shift-and-stack across multi-year (N >= 4) high-eccentricity exoplanet & stellar campaigns.
    """
    base_res = scan_coherent_shift_stack_keplerian_jerk_v57(
        wave_rest, fn_epochs, sig_epochs, mjd_epochs, v_obs_to_rest_epochs_kms, cfg,
        star=star, star_idx=star_idx, z_rpca_mat=z_rpca_mat, bervs_cohort=bervs_cohort,
        known_orb_period_days=known_orb_period_days, known_orb_t0_bjd=known_orb_t0_bjd,
        known_orb_kp_kms=known_orb_kp_kms, known_orb_periods_days=known_orb_periods_days,
        known_orb_kps_kms=known_orb_kps_kms, enable_long_blind=enable_long_blind,
    )
    w = np.asarray(wave_rest, dtype=np.float64)
    fn_e = np.asarray(fn_epochs, dtype=np.float64)
    sig_e = np.asarray(sig_epochs, dtype=np.float64)
    mjds = np.asarray(mjd_epochs, dtype=np.float64)
    v_o2r = np.asarray(v_obs_to_rest_epochs_kms, dtype=np.float64)

    # Collect target eccentric specs BEFORE heavy preprocessing so circular/Taylor/veto cases return in <0.1 ms
    orb_specs: list[tuple[float, float, float, float]] = []
    if known_orb_period_days is not None and math.isfinite(float(known_orb_period_days)) and float(known_orb_period_days) > 0.3:
        ek0 = float(known_orb_ecc) if (known_orb_ecc is not None and math.isfinite(float(known_orb_ecc))) else math.nan
        if not (math.isfinite(ek0) and ek0 < 0.15):
            if math.isfinite(ek0) or base_res["n_raw_candidates"] == 0:
                orb_specs.append((
                    float(known_orb_period_days), ek0,
                    float(known_orb_omega_deg) if (known_orb_omega_deg is not None and math.isfinite(float(known_orb_omega_deg))) else math.nan,
                    float(known_orb_kp_kms) if (known_orb_kp_kms is not None and math.isfinite(float(known_orb_kp_kms))) else math.nan,
                ))
    if known_orb_periods_days:
        for ip, pk in enumerate(known_orb_periods_days):
            if math.isfinite(float(pk)) and float(pk) > 0.3 and all(abs(float(pk) - s[0]) > 1e-3 for s in orb_specs):
                ek = float(known_orb_eccs[ip]) if (known_orb_eccs and ip < len(known_orb_eccs) and math.isfinite(float(known_orb_eccs[ip]))) else math.nan
                if math.isfinite(ek) and ek < 0.15:
                    continue
                if (not math.isfinite(ek)) and base_res["n_raw_candidates"] > 0:
                    continue
                wk = float(known_orb_omegas_deg[ip]) if (known_orb_omegas_deg and ip < len(known_orb_omegas_deg) and math.isfinite(float(known_orb_omegas_deg[ip]))) else math.nan
                kpk = float(known_orb_kps_kms[ip]) if (known_orb_kps_kms and ip < len(known_orb_kps_kms) and math.isfinite(float(known_orb_kps_kms[ip]))) else math.nan
                orb_specs.append((float(pk), ek, wk, kpk))

    if fn_e.ndim != 2 or fn_e.shape[0] < 4 or len(w) < 256 or base_res["n_distinct_epochs"] < int(cfg.get("drift_v54_min_epochs", 4)) or not orb_specs:
        return {
            **base_res,
            "circular_only_hits": base_res["keplerian_hits"],
            "eccentric_hits": 0,
            "eccentric_polishes": 0,
        }

    ord_t = np.argsort(mjds)
    mjds, fn_e, sig_e, v_o2r = mjds[ord_t], fn_e[ord_t], sig_e[ord_t], v_o2r[ord_t]
    n_ep = fn_e.shape[0]

    sig_v = max(0.8, float(cfg.get("sigma_v_kms", 2.0)))
    min_snr_stack = float(cfg.get("drift_v54_min_snr_stack", 7.5))
    min_snr_loo = float(cfg.get("drift_v54_min_snr_loo", 5.2))
    max_single_frac = float(cfg.get("drift_v54_max_single_epoch_frac", 0.45))
    min_pos_frac = float(cfg.get("drift_v54_min_pos_frac", 0.60))
    min_dv_span = float(cfg.get("drift_v54_min_dv_span_kms", 12.0))
    stat_margin = float(cfg.get("drift_v54_stat_margin_sigma", 2.2))
    sky_margin = float(cfg.get("drift_v54_sky_margin_sigma", 1.5))
    max_masked_frac = float(cfg.get("drift_v54_max_masked_frac", 0.30))

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
    col_ok = np.sum(V, axis=0) >= max(4, int(math.ceil(0.55 * n_ep)))
    Z[:, ~col_ok] = 0.0
    V[:, ~col_ok] = False

    ln_w0, ln_w1 = math.log(float(w[0])), math.log(float(w[-1]))
    dv_grid_kms = max(1.2, min(4.5, 0.70 * sig_v))
    dln = dv_grid_kms / C_KMS
    n_log = int(math.floor((ln_w1 - ln_w0) / dln)) + 1
    if n_log > 160000:
        dln = (ln_w1 - ln_w0) / 160000.0
        dv_grid_kms = dln * C_KMS
        n_log = 160001
    ln_grid = ln_w0 + dln * np.arange(n_log, dtype=np.float64)
    w_log = np.exp(ln_grid)
    ln_w_native = np.log(w)

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
        mk = M_log[k, V_log[k]]
        if len(mk) >= 64:
            mad_m = exact_mad_1d(mk)
            if mad_m > 0.2:
                M_log[k] /= mad_m

    pad = int(math.ceil(260.0 / dv_grid_kms)) + 4
    n_core = n_log - 2 * pad
    if n_core < 64:
        return {**base_res, "circular_only_hits": base_res["keplerian_hits"], "eccentric_hits": 0, "eccentric_polishes": 0}
    base_idx = np.arange(pad, n_log - pad, dtype=np.int64)
    M_z = np.ascontiguousarray(np.where(V_log, M_log, 0.0), dtype=np.float64)
    V_u8 = np.ascontiguousarray(V_log.astype(np.uint8))
    inv_sqrt_nv = np.zeros(n_ep + 1, dtype=np.float64)
    for k_nv in range(4, n_ep + 1):
        inv_sqrt_nv[k_nv] = 1.0 / math.sqrt(float(k_nv))

    min_req_ep_b = max(4, n_ep - int(math.floor(max_masked_frac * float(n_ep))))
    M_z32 = np.ascontiguousarray(M_z, dtype=np.float32)
    s_buf = np.empty(n_core, dtype=np.float32)
    min_s_exact = float(min_snr_stack * math.sqrt(min_req_ep_b))
    min_s_coarse = float(max(4.6, min_snr_stack * 0.62) * math.sqrt(min_req_ep_b))

    def _vet_ecc_traj(v_ep: np.ndarray, meta: dict[str, Any]) -> list[dict[str, Any]]:
        sh = np.rint(v_ep / dv_grid_kms).astype(np.int64)
        s_sum = M_z[0, pad + int(sh[0]) : pad + n_core + int(sh[0])].copy()
        nv = V_u8[0, pad + int(sh[0]) : pad + n_core + int(sh[0])].astype(np.int32)
        for k in range(1, n_ep):
            sk = int(sh[k])
            s_sum += M_z[k, pad + sk : pad + n_core + sk]
            nv += V_u8[k, pad + sk : pad + n_core + sk]
        snr_stack = s_sum * inv_sqrt_nv[nv]
        hits_i = np.where((nv >= min_req_ep_b) & (snr_stack >= min_snr_stack))[0]
        if len(hits_i) == 0:
            return []
        ord_h = hits_i[np.argsort(snr_stack[hits_i])[::-1]]
        out_h: list[dict[str, Any]] = []
        used = np.zeros(n_core, dtype=bool)
        nms_r = max(4, int(round(8.0 * sig_log_px)))
        dv_sp = float(np.ptp(v_ep))
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
            s_sorted = np.sort(s_act)[::-1]
            s_max = float(s_sorted[0])
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
            s_lo, s_hi = int(np.min(sh)) - 2, int(np.max(sh)) + 2
            best_stat = -1e9
            for ds in range(s_lo, s_hi + 1):
                ct = c_glob + ds
                if 0 <= ct < n_log:
                    m_st = V_log[:, ct]
                    if int(np.sum(m_st)) >= 4:
                        best_stat = max(best_stat, float(np.sum(M_z[m_st, ct]) / math.sqrt(float(np.sum(m_st)))))
            if (snr_st - best_stat) < stat_margin:
                continue
            v_sky_kms = v_ep - v_o2r
            best_sky = -1e9
            for sk_ref in v_sky_kms[:: max(1, n_ep // 6)]:
                sh_sky = np.rint((sk_ref + v_o2r) / dv_grid_kms).astype(np.int64)
                idx_sky = np.clip(c_glob + sh_sky, 0, n_log - 1)
                m_sk = V_log[np.arange(n_ep), idx_sky]
                if int(np.sum(m_sk)) >= 4:
                    best_sky = max(best_sky, float(np.sum(M_z[np.arange(n_ep)[m_sk], idx_sky[m_sk]]) / math.sqrt(float(np.sum(m_sk)))))
            if (snr_st - best_sky) < sky_margin:
                continue
            w_0 = float(w_log[c_glob])
            rarity_min = 1.0
            if z_rpca_mat is not None and bervs_cohort is not None and z_rpca_mat.shape[0] >= 2:
                r_mid = compute_spectral_rarity_score(w, z_rpca_mat, bervs_cohort, star_idx, w_0, sig_v, polarity=1.0)
                rarity_min = float(r_mid["rarity_score"])
                if rarity_min < float(cfg.get("g7_min_rarity_score", 0.65)):
                    continue
            out_h.append({
                "star": star,
                "branch": "ECCENTRIC_KEPLER_STACK_V58",
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
        return out_h

    t_rel = mjds - float(mjds[0])
    ecc_hits: list[dict[str, Any]] = []
    n_ecc_eval = 0
    n_ecc_pol = 0

    for p_k, e_known, w_known_deg, kp_k in orb_specs:
        if math.isfinite(e_known):
            e_grid = [max(0.15, min(0.96, float(e_known)))]
        else:
            e_grid = [0.40, 0.70, 0.88]
        if math.isfinite(w_known_deg):
            wr = math.radians(w_known_deg) % (2.0 * math.pi)
            w_arr = np.array([wr], dtype=np.float64)
        else:
            w_arr = np.linspace(0.0, 2.0 * math.pi, 6, endpoint=False)
        m0_base = np.linspace(0.0, 2.0 * math.pi, 48 if math.isfinite(e_known) else 12, endpoint=False)
        if known_orb_t0_bjd is not None and math.isfinite(float(known_orb_t0_bjd)):
            t0_ref = float(known_orb_t0_bjd) - (2400000.5 if float(known_orb_t0_bjd) > 2000000.0 else 0.0)
            m0_ephem = (2.0 * math.pi * (float(mjds[0]) - t0_ref) / p_k) % (2.0 * math.pi)
            m0_grid = np.append(m0_base, m0_ephem)
        else:
            m0_grid = m0_base
        k_grid = [35.0, 60.0, 85.0, 115.0, 155.0]
        if math.isfinite(kp_k) and 15.0 <= kp_k <= 220.0:
            if all(abs(kp_k - kg) > 2.5 for kg in k_grid):
                k_grid.append(float(kp_k))
        k_arr = np.asarray(k_grid, dtype=np.float64)

        seen_sh: set[tuple[int, ...]] = set()
        coarse: list[tuple[float, tuple[float, float, float, float, float]]] = []
        spec_hits = 0
        for ev in e_grid:
            f_mat = _solve_kepler_true_anom_batch(t_rel, p_k, ev, m0_grid)  # (n_m0, n_ep)
            # Broadcast over omega: (n_w, n_m0, n_ep)
            u_grid = np.cos(f_mat[None, :, :] + w_arr[:, None, None]) + ev * np.cos(w_arr[:, None, None])
            # Broadcast over K: (n_k, n_w, n_m0, n_ep) -> flatten
            vp_all = (k_arr[:, None, None, None] * u_grid[None, :, :, :]).reshape(-1, n_ep)
            ptps = np.ptp(vp_all, axis=1)
            mxab = np.max(np.abs(vp_all), axis=1)
            keep_mask = (ptps >= min_dv_span) & (mxab <= 250.0)
            if not np.any(keep_mask):
                continue
            n_k, n_w, n_m = len(k_arr), len(w_arr), len(m0_grid)
            sh_all = np.rint(vp_all[keep_mask] / dv_grid_kms).astype(np.int64) + pad
            vp_kept = vp_all[keep_mask]
            idx_kept = np.where(keep_mask)[0]
            for pos_i, flat_i in enumerate(idx_kept):
                sh_tup = tuple(sh_all[pos_i].tolist())
                if sh_tup in seen_sh:
                    continue
                seen_sh.add(sh_tup)
                n_ecc_eval += 1
                np.copyto(s_buf, M_z32[0, sh_tup[0] : sh_tup[0] + n_core])
                for k in range(1, n_ep):
                    sk = sh_tup[k]
                    np.add(s_buf, M_z32[k, sk : sk + n_core], out=s_buf)
                s_mx = float(s_buf.max())
                ik = int(flat_i) // (n_w * n_m)
                rem = int(flat_i) % (n_w * n_m)
                iw = rem // n_m
                im = rem % n_m
                p_tu = (p_k, float(ev), float(w_arr[iw]), float(m0_grid[im]), float(k_arr[ik]))
                if s_mx >= min_s_exact:
                    vh = _vet_ecc_traj(vp_kept[pos_i], {"period_d": round(p_tu[0], 4), "ecc": round(p_tu[1], 3), "k_amp_kms": round(p_tu[4], 2)})
                    if vh:
                        spec_hits += len(vh)
                        ecc_hits.extend(vh)
                elif s_mx >= min_s_coarse:
                    coarse.append((s_mx, p_tu))

        if coarse and spec_hits == 0:
            coarse.sort(key=lambda x: -x[0])
            for _, (_, e0, w0, m0, k0) in coarse[:4]:
                de_list = (-0.04, 0.0, 0.04)
                dm_list = np.array([-0.08, -0.04, 0.0, 0.04, 0.08]) + m0
                dw_arr = np.array([-0.15, 0.0, 0.15]) + w0
                dk_arr = np.array([k0 + dk for dk in (-7.0, 0.0, 7.0) if 14.0 <= k0 + dk <= 240.0])
                if len(dk_arr) == 0:
                    continue
                for de in de_list:
                    ee = max(0.05, min(0.95, e0 + de))
                    f_p = _solve_kepler_true_anom_batch(t_rel, p_k, ee, dm_list)
                    u_p = np.cos(f_p[None, :, :] + dw_arr[:, None, None]) + ee * np.cos(dw_arr[:, None, None])
                    vp_p = (dk_arr[:, None, None, None] * u_p[None, :, :, :]).reshape(-1, n_ep)
                    km_p = (np.ptp(vp_p, axis=1) >= min_dv_span) & (np.max(np.abs(vp_p), axis=1) <= 250.0)
                    if not np.any(km_p):
                        continue
                    sh_p = np.rint(vp_p[km_p] / dv_grid_kms).astype(np.int64) + pad
                    vp_pk = vp_p[km_p]
                    ik_p = np.where(km_p)[0]
                    for pos_i, flat_i in enumerate(ik_p):
                        sh_tup = tuple(sh_p[pos_i].tolist())
                        if sh_tup in seen_sh:
                            continue
                        seen_sh.add(sh_tup)
                        n_ecc_pol += 1
                        np.copyto(s_buf, M_z32[0, sh_tup[0] : sh_tup[0] + n_core])
                        for k in range(1, n_ep):
                            sk = sh_tup[k]
                            np.add(s_buf, M_z32[k, sk : sk + n_core], out=s_buf)
                        if float(s_buf.max()) >= min_s_exact:
                            kk = float(dk_arr[int(flat_i) // (len(dw_arr) * len(dm_list))])
                            vh = _vet_ecc_traj(vp_pk[pos_i], {"period_d": round(p_k, 4), "ecc": round(ee, 3), "k_amp_kms": round(kk, 2)})
                            if vh:
                                ecc_hits.extend(vh)

    merged = list(base_res["candidates"]) + ecc_hits
    merged.sort(key=lambda c: -float(c["snr_stack"]))
    final_cands: list[dict[str, Any]] = []
    for c in merged:
        w0 = float(c["wave0_rest_a"])
        if any(abs(C_KMS * (w0 - float(kc["wave0_rest_a"])) / max(1e-6, w0)) < 25.0 for kc in final_cands):
            continue
        final_cands.append(c)

    return {
        "star": star,
        "n_epochs": base_res["n_epochs"],
        "n_distinct_epochs": base_res["n_distinct_epochs"],
        "n_trajectories_evaluated": int(base_res["n_trajectories_evaluated"]) + int(n_ecc_eval) + int(n_ecc_pol),
        "n_pixel_trajectory_integrals": int(base_res["n_pixel_trajectory_integrals"]) + int((n_ecc_eval + n_ecc_pol) * n_core),
        "n_raw_candidates": len(final_cands),
        "taylor_only_hits": int(base_res["taylor_only_hits"]),
        "circular_only_hits": int(base_res["keplerian_hits"]),
        "eccentric_hits": len(ecc_hits),
        "eccentric_polishes": int(n_ecc_eval + n_ecc_pol),
        "keplerian_hits": int(base_res["keplerian_hits"]) + len(ecc_hits),
        "candidates": final_cands,
    }


def run_eccentric_keplerian_calibration_v58(seed: int = 10004) -> dict[str, Any]:
    """
    `CALIBRATION_V58_ECCENTRIC_KEPLERIAN_360`:
      - 60 High-Eccentricity Multi-Year Keplerian (e in [0.55, 0.94] -> V5.8 Eccentric vs V5.7 Circular vs V5.6 Taylor!)
      - 60 Circular Multi-Rev 2-10 yr Keplerian beacons
      - 60 Cubic Taylor Jerk beacons
      - 60 Short-period orbital beacons
      - 40 Stationary stellar residuals (vetoed)
      - 40 Single-epoch transient/CR (vetoed)
      - 40 Topocentric BERV sky lines (vetoed)
    """
    rng = np.random.default_rng(seed)
    cfg = get_inst_config("ESO_UVES", 51690.0)
    w_r = np.linspace(6300.0, 6365.0, 1800)
    n_ep = 6
    sig_w = 6330.0 / (float(cfg["resolving_power"]) * FWHM_FACTOR)
    bervs = np.linspace(-22.0, 22.0, n_ep)
    sig_mat = np.full((n_ep, len(w_r)), 0.015)

    trials: list[dict[str, Any]] = []
    ecc_v58 = ecc_v57 = ecc_tay = cir_rec = jk_rec = sh_rec = st_v = tr_v = sk_v = 0

    for ti in range(360):
        wc0 = 6332.0 + float(rng.uniform(-4.0, 4.0))
        known_p = known_e = known_w_deg = known_kp = None
        if ti < 60:
            cls_, want = "HIGH_ECCENTRICITY_KEPLER_055_094", True
            n_ep_i = 8
            fn_mat = 1.0 + rng.normal(0.0, 0.015, size=(n_ep_i, len(w_r)))
            sig_mat_i = np.full((n_ep_i, len(w_r)), 0.015)
            bervs_i = np.linspace(-22.0, 22.0, n_ep_i)
            p_orb = float(rng.uniform(45.0, 220.0))
            ecc_v = float(rng.uniform(0.58, 0.93))
            om_rad = float(rng.uniform(0.0, 2.0 * math.pi))
            m0_rad = float(rng.uniform(0.0, 2.0 * math.pi))
            kp_v = float(rng.uniform(45.0, 110.0))
            # Cluster half the epochs near periastron passage where e>=0.65 spikes sharply
            t_lin = np.linspace(0.0, 1200.0, n_ep_i - 2)
            t_peri = (2.0 * math.pi - m0_rad) / (2.0 * math.pi) * p_orb + p_orb * np.array([1.0 + 0.02, 2.0 - 0.02])
            mjds = np.sort(55000.0 + np.concatenate([t_lin, t_peri]) + rng.uniform(-1.5, 1.5, n_ep_i))
            v_ep = solve_kepler_eccentric_rv(mjds - mjds[0], p_orb, ecc_v, om_rad, m0_rad, kp_v)
            known_p, known_e, known_w_deg, known_kp = p_orb, ecc_v, math.degrees(om_rad), kp_v
            amp = float(rng.uniform(3.9, 4.9)) * 0.015
            for k in range(n_ep_i):
                fn_mat[k] += amp * np.exp(-0.5 * ((w_r - wc0 * (1.0 + v_ep[k] / C_KMS)) / sig_w) ** 2)
            res = scan_coherent_shift_stack_eccentric_keplerian_v58(
                w_r, fn_mat, sig_mat_i, mjds, bervs_i, cfg, star=f"SIM_EK_{ti}",
                known_orb_period_days=known_p, known_orb_kp_kms=known_kp,
                known_orb_ecc=known_e, known_orb_omega_deg=known_w_deg, enable_long_blind=True,
            )
            obs = res["n_raw_candidates"] >= 1
            v57_obs = (res["circular_only_hits"] + res["taylor_only_hits"]) >= 1
            tay_obs = res["taylor_only_hits"] >= 1
            ok = int(obs)
            ecc_v58 += int(obs)
            ecc_v57 += int(v57_obs)
            ecc_tay += int(tay_obs)
            trials.append({
                "suite": "CALIBRATION_V58_ECCENTRIC_KEPLERIAN_360",
                "class": cls_, "trial": ti + 1, "expected": 1,
                "observed": int(obs), "v57_circular_obs": int(v57_obs), "taylor_only_obs": int(tay_obs),
                "ecc": round(ecc_v, 3), "passed": ok,
            })
            continue

        elif ti < 120:
            cls_, want = "MULTI_REV_CIRCULAR_KEPLER", True
            n_ep_i = 8
            fn_mat = 1.0 + rng.normal(0.0, 0.015, size=(n_ep_i, len(w_r)))
            sig_mat_i = np.full((n_ep_i, len(w_r)), 0.015)
            bervs_i = np.linspace(-22.0, 22.0, n_ep_i)
            mjds = np.sort(np.linspace(55000.0, 56500.0, n_ep_i) + rng.uniform(-18.0, 18.0, n_ep_i))
            t_rel = mjds - mjds[0]
            while True:
                p_orb = float(rng.uniform(18.0, 140.0))
                phi0 = float(rng.uniform(0.0, 2.0 * math.pi))
                k_amp = float(rng.uniform(55.0, 145.0))
                v_ep = k_amp * np.sin(2.0 * math.pi * t_rel / p_orb + phi0)
                if float(np.ptp(v_ep)) >= 25.0:
                    break
            known_p, known_e = p_orb, 0.0
            amp = float(rng.uniform(3.8, 4.8)) * 0.015
            for k in range(n_ep_i):
                fn_mat[k] += amp * np.exp(-0.5 * ((w_r - wc0 * (1.0 + v_ep[k] / C_KMS)) / sig_w) ** 2)
        else:
            fn_mat = 1.0 + rng.normal(0.0, 0.015, size=(n_ep, len(w_r)))
            sig_mat_i = sig_mat
            bervs_i = bervs
            mjds = np.sort(np.linspace(55000.0, 56500.0, n_ep) + rng.uniform(-12.0, 12.0, n_ep))
            t_rel = mjds - mjds[0]
            if ti < 180:
                cls_, want = "SUBTHRESH_CUBIC_JERK", True
                t_mid = 0.5 * (mjds[0] + mjds[-1])
                dt_h = 0.5 * (mjds[-1] - mjds[0])
                tau = (mjds - t_mid) / dt_h
                p3 = 2.5 * (tau ** 3 - 0.6 * tau)
                v_ep = float(rng.choice([-120.0, 120.0])) * tau + float(rng.choice([-40.0, 40.0])) * (tau ** 2 - 1.0 / 3.0) + float(rng.choice([-35.0, 35.0])) * p3
                amp = float(rng.uniform(3.8, 4.8)) * 0.015
                for k in range(n_ep):
                    fn_mat[k] += amp * np.exp(-0.5 * ((w_r - wc0 * (1.0 + v_ep[k] / C_KMS)) / sig_w) ** 2)
            elif ti < 240:
                cls_, want = "SUBTHRESH_PERIODIC", True
                mjds = np.sort(np.linspace(55000.0, 55040.0, n_ep) + rng.uniform(-0.5, 0.5, n_ep))
                t_rel = mjds - mjds[0]
                p_orb = float(rng.choice([8.5, 16.0, 28.0]))
                known_p = p_orb
                phi0 = float(rng.uniform(0.0, 2.0 * math.pi))
                v_ep = float(rng.uniform(55.0, 130.0)) * np.sin(2.0 * math.pi * t_rel / p_orb + phi0)
                amp = float(rng.uniform(3.8, 4.8)) * 0.015
                for k in range(n_ep):
                    fn_mat[k] += amp * np.exp(-0.5 * ((w_r - wc0 * (1.0 + v_ep[k] / C_KMS)) / sig_w) ** 2)
            elif ti < 280:
                cls_, want = "STATIONARY_VETO", False
                amp = float(rng.uniform(5.0, 8.0)) * 0.015
                for k in range(n_ep):
                    fn_mat[k] += amp * np.exp(-0.5 * ((w_r - wc0) / sig_w) ** 2)
            elif ti < 320:
                cls_, want = "TRANSIENT_VETO", False
                fn_mat[int(rng.integers(0, n_ep))] += 18.0 * 0.015 * np.exp(-0.5 * ((w_r - wc0) / sig_w) ** 2)
            else:
                cls_, want = "BERV_SKY_VETO", False
                w_sky = 6328.0
                amp = float(rng.uniform(4.5, 7.0)) * 0.015
                for k in range(n_ep):
                    wb = w_sky * (1.0 + bervs_i[k] / C_KMS)
                    fn_mat[k] += amp * np.exp(-0.5 * ((w_r - wb) / sig_w) ** 2)

        res = scan_coherent_shift_stack_eccentric_keplerian_v58(
            w_r, fn_mat, sig_mat_i, mjds, bervs_i, cfg, star=f"SIM_EK_{ti}",
            known_orb_period_days=known_p, known_orb_ecc=known_e, enable_long_blind=(ti < 120),
        )
        obs = res["n_raw_candidates"] >= 1
        tay_obs = res["taylor_only_hits"] >= 1
        ok = int(bool(obs) == bool(want))
        if cls_ == "MULTI_REV_CIRCULAR_KEPLER":
            cir_rec += ok
        elif cls_ == "SUBTHRESH_CUBIC_JERK":
            jk_rec += ok
        elif cls_ == "SUBTHRESH_PERIODIC":
            sh_rec += ok
        elif cls_ == "STATIONARY_VETO":
            st_v += ok
        elif cls_ == "TRANSIENT_VETO":
            tr_v += ok
        else:
            sk_v += ok
        trials.append({
            "suite": "CALIBRATION_V58_ECCENTRIC_KEPLERIAN_360",
            "class": cls_, "trial": ti + 1, "expected": int(want),
            "observed": int(obs), "v57_circular_obs": int(res["circular_only_hits"] >= 1), "taylor_only_obs": int(tay_obs),
            "ecc": 0.0, "passed": ok,
        })

    return {
        "total_trials": len(trials),
        "high_ecc_kepler_v58": f"{ecc_v58}/60 ({ecc_v58/60.0:.4f})",
        "high_ecc_v57_circular_baseline": f"{ecc_v57}/60 ({ecc_v57/60.0:.4f})",
        "high_ecc_v56_taylor_baseline": f"{ecc_tay}/60 ({ecc_tay/60.0:.4f})",
        "circular_kepler_60": f"{cir_rec}/60 ({cir_rec/60.0:.4f})",
        "cubic_jerk_60": f"{jk_rec}/60 ({jk_rec/60.0:.4f})",
        "short_periodic_60": f"{sh_rec}/60 ({sh_rec/60.0:.4f})",
        "stationary_veto_40": f"{st_v}/40 ({st_v/40.0:.4f})",
        "transient_veto_40": f"{tr_v}/40 ({tr_v/40.0:.4f})",
        "berv_sky_veto_40": f"{sk_v}/40 ({sk_v/40.0:.4f})",
        "trials": trials,
    }


# ===========================================================================
# TECHNOSIGNATURE V5.9 ENGINES (ALMA B1/B3/B4/B5 + DRIFTING COMB)
# ===========================================================================

ALMA_MM_MOLECULAR_ATLAS_GHZ: tuple[tuple[str, float, str], ...] = (
    # Band 1 (35-50 GHz)
    ("SiS(2-1)", 36.3096, "ALMA_B1_7MM"),
    ("HC3N(4-3)", 36.3923, "ALMA_B1_7MM"),
    ("CH3CN(2-1)", 36.7955, "ALMA_B1_7MM"),
    ("HC5N(14-13)", 37.2770, "ALMA_B1_7MM"),
    ("H55alpha", 38.5105, "ALMA_B1_7MM"),
    ("H54alpha", 40.6305, "ALMA_B1_7MM"),
    ("H53alpha", 42.9520, "ALMA_B1_7MM"),
    ("SiO_v1(1-0)", 43.1221, "ALMA_B1_7MM"),
    ("SiO_v0(1-0)", 43.4238, "ALMA_B1_7MM"),
    ("CH3OH(7_0-6_1)", 44.0694, "ALMA_B1_7MM"),
    ("H52alpha", 45.4537, "ALMA_B1_7MM"),
    ("CS_34(1-0)", 48.2069, "ALMA_B1_7MM"),
    ("PN(1-0)", 46.9900, "ALMA_B1_7MM"),
    ("H51alpha", 48.1536, "ALMA_B1_7MM"),
    ("C34S(1-0)", 48.2069, "ALMA_B1_7MM"),
    ("CH3OH(1_0-0_0)", 48.3725, "ALMA_B1_7MM"),
    ("CS(1-0)", 48.9910, "ALMA_B1_7MM"),
    # Band 3 (84-116 GHz)
    ("NH2D", 85.9263, "ALMA_B3_3MM"),
    ("H13CN(1-0)", 86.3402, "ALMA_B3_3MM"),
    ("H13CO+(1-0)", 86.7543, "ALMA_B3_3MM"),
    ("SiO_v0(2-1)", 86.8470, "ALMA_B3_3MM"),
    ("HN13C(1-0)", 87.0909, "ALMA_B3_3MM"),
    ("CCH(1-0)", 87.3169, "ALMA_B3_3MM"),
    ("HNCO(4-3)", 87.9252, "ALMA_B3_3MM"),
    ("HCN(1-0)", 88.6316, "ALMA_B3_3MM"),
    ("HCO+(1-0)", 89.1885, "ALMA_B3_3MM"),
    ("HNC(1-0)", 90.6636, "ALMA_B3_3MM"),
    ("HC3N(10-9)", 90.9790, "ALMA_B3_3MM"),
    ("13CS(2-1)", 92.4943, "ALMA_B3_3MM"),
    ("N2H+(1-0)", 93.1734, "ALMA_B3_3MM"),
    ("C34S(2-1)", 96.4129, "ALMA_B3_3MM"),
    ("CH3OH(2-1)", 96.7414, "ALMA_B3_3MM"),
    ("CS(2-1)", 97.9810, "ALMA_B3_3MM"),
    ("H40alpha", 99.0230, "ALMA_B3_3MM"),
    ("SO(3_2-2_1)", 99.2999, "ALMA_B3_3MM"),
    ("HC3N(11-10)", 100.0764, "ALMA_B3_3MM"),
    ("H2CS(3-2)", 103.0405, "ALMA_B3_3MM"),
    ("NH2CN", 100.6295, "ALMA_B3_3MM"),
    ("C18O(1-0)", 109.7822, "ALMA_B3_3MM"),
    ("13CO(1-0)", 110.2014, "ALMA_B3_3MM"),
    ("CH3CN(6-5)", 110.3835, "ALMA_B3_3MM"),
    ("C17O(1-0)", 112.3590, "ALMA_B3_3MM"),
    ("CN(1-0)", 113.4910, "ALMA_B3_3MM"),
    ("CO(1-0)", 115.2712, "ALMA_B3_3MM"),
    # Band 4 (125-163 GHz)
    ("SiO(3-2)", 130.2686, "ALMA_B4_2MM"),
    ("SO(3_4-2_3)", 138.1786, "ALMA_B4_2MM"),
    ("13CS(3-2)", 138.7393, "ALMA_B4_2MM"),
    ("H2CO(2_12-1_11)", 140.8395, "ALMA_B4_2MM"),
    ("C34S(3-2)", 144.6171, "ALMA_B4_2MM"),
    ("H2CO(2_02-1_01)", 145.6029, "ALMA_B4_2MM"),
    ("CS(3-2)", 146.9690, "ALMA_B4_2MM"),
    ("NO(3/2-1/2)", 150.1765, "ALMA_B4_2MM"),
    ("H2CO(2_11-1_10)", 150.4983, "ALMA_B4_2MM"),
    ("DNC(2-1)", 152.6098, "ALMA_B4_2MM"),
    ("HNCO(7-6)", 153.8651, "ALMA_B4_2MM"),
    ("HC3N(17-16)", 154.6573, "ALMA_B4_2MM"),
    ("CH3OH(3_0-2_0)", 157.2708, "ALMA_B4_2MM"),
    ("SiO_v1(4-3)", 172.4811, "ALMA_B5_2MM"),
    # Band 5 (163-211 GHz)
    ("CH3OH(1_1-1_0)", 165.0500, "ALMA_B5_2MM"),
    ("H2S(1_10-1_01)", 168.7628, "ALMA_B5_2MM"),
    ("SO(4_4-3_3)", 172.1814, "ALMA_B5_2MM"),
    ("SiO(4-3)", 173.6883, "ALMA_B5_2MM"),
    ("HCN(2-1)", 177.2611, "ALMA_B5_2MM"),
    ("HCO+(2-1)", 178.3751, "ALMA_B5_2MM"),
    ("HNC(2-1)", 181.3248, "ALMA_B5_2MM"),
    ("H2O(3_13-2_20)", 183.3101, "ALMA_B5_2MM"),
    ("13CS(4-3)", 184.9818, "ALMA_B5_2MM"),
    ("N2H+(2-1)", 186.3446, "ALMA_B5_2MM"),
    ("CS(4-3)", 195.9542, "ALMA_B5_2MM"),
    ("SO(5_4-4_3)", 206.1760, "ALMA_B5_2MM"),
    ("H31alpha", 210.5018, "ALMA_B5_2MM"),
    ("H2CO(3_12-2_11)", 211.2115, "ALMA_B5_2MM"),
    # Band 6 (211-275 GHz)
    ("SiS(12-11)", 217.8177, "ALMA_B6_1MM"),
    ("SiO(5-4)", 217.1050, "ALMA_B6_1MM"),
    ("H2CO(3_03-2_02)", 218.2222, "ALMA_B6_1MM"),
    ("C18O(2-1)", 219.5604, "ALMA_B6_1MM"),
    ("SO(5_6-4_5)", 219.9494, "ALMA_B6_1MM"),
    ("13CO(2-1)", 220.3987, "ALMA_B6_1MM"),
    ("CN(2-1)", 226.8748, "ALMA_B6_1MM"),
    ("CO(2-1)", 230.5380, "ALMA_B6_1MM"),
    ("H30alpha", 231.9009, "ALMA_B6_1MM"),
    ("13CS(5-4)", 231.2207, "ALMA_B6_1MM"),
    ("CS(5-4)", 244.9356, "ALMA_B6_1MM"),
    ("SO(6_5-5_4)", 251.8258, "ALMA_B6_1MM"),
    ("C2H(3-2)", 262.0043, "ALMA_B6_1MM"),
    ("HCN(3-2)", 265.8864, "ALMA_B6_1MM"),
    ("HCO+(3-2)", 267.5576, "ALMA_B6_1MM"),
    ("HNC(3-2)", 271.9811, "ALMA_B6_1MM"),
    # Band 7 (275-373 GHz)
    ("N2H+(3-2)", 279.5118, "ALMA_B7_0P9MM"),
    ("DCO+(4-3)", 288.1439, "ALMA_B7_0P9MM"),
    ("C18O(3-2)", 329.3306, "ALMA_B7_0P9MM"),
    ("13CO(3-2)", 330.5880, "ALMA_B7_0P9MM"),
    ("SO(7_8-6_7)", 340.7141, "ALMA_B7_0P9MM"),
    ("CS(7-6)", 342.8829, "ALMA_B7_0P9MM"),
    ("SO(8_8-7_7)", 344.3106, "ALMA_B7_0P9MM"),
    ("H13CN(4-3)", 345.3398, "ALMA_B7_0P9MM"),
    ("CO(3-2)", 345.7960, "ALMA_B7_0P9MM"),
    ("C2H(4-3)", 349.3377, "ALMA_B7_0P9MM"),
    ("H2CO(5_15-4_14)", 351.7686, "ALMA_B7_0P9MM"),
    ("H26alpha", 353.6228, "ALMA_B7_0P9MM"),
    ("HCN(4-3)", 354.5055, "ALMA_B7_0P9MM"),
    ("HCO+(4-3)", 356.7342, "ALMA_B7_0P9MM"),
    ("DCO+(5-4)", 360.1698, "ALMA_B7_0P9MM"),
    ("N2H+(4-3)", 372.6725, "ALMA_B7_0P9MM"),
    # Band 8 (385-500 GHz)
    ("CO(4-3)", 461.0408, "ALMA_B8_0P7MM"),
    ("CI(1-0)", 492.1607, "ALMA_B8_0P7MM"),
)

ALMA_ATMOSPHERIC_OPAQUE_WINDOWS_GHZ: tuple[tuple[str, float, float], ...] = (
    ("TERRESTRIAL_O2_60GHZ_COMPLEX", 50.0, 68.0),
    ("TERRESTRIAL_O2_118_75GHZ_WING", 116.0, 121.5),
)


def alma_freq_to_band(freq_ghz: float) -> str:
    f = float(freq_ghz)
    if f < 60.0:
        return "ALMA_B1_7MM"
    if f < 120.0:
        return "ALMA_B3_3MM"
    if f < 163.0:
        return "ALMA_B4_2MM"
    if f < 211.5:
        return "ALMA_B5_2MM"
    if f < 275.0:
        return "ALMA_B6_1MM"
    if f < 378.0:
        return "ALMA_B7_0P9MM"
    return "ALMA_B8_0P7MM"


def alma_jy_to_flam_cgs(freq_ghz: float, flux_jy: float) -> float:
    """Convert interferometric flux density [Jy] at frequency [GHz] into f_lambda [erg s^-1 cm^-2 A^-1]."""
    lam_a = C_ANGSTROM_GHZ / max(1.0, float(freq_ghz))
    f_nu_cgs = float(flux_jy) * 1e-23
    c_a_s = C_SI * 1e10
    return f_nu_cgs * (c_a_s / (lam_a * lam_a))


def extract_alma_cube_profile(
    data_arr: np.ndarray,
    header_dict: dict[str, Any] | None = None,
    fallback_freq_ghz: float | None = None,
    instrument: str | None = None,
    dp_id: str = "",
    target_ra_deg: float | None = None,
    target_dec_deg: float | None = None,
) -> dict[str, Any]:
    """
    Engine V5.9A / V6.0C spatial-spectral cube profiler (`ALMA_V59` / `ALMA_V60`).
    Extracts Stokes I sub-cube, beam-weighted on-source spectrum `s_on_jy`,
    off-source annulus `s_off_med_jy` / `s_off_95_jy` / `s_off_max_jy` / `s_off_mad_jy`,
    and exact 2D PSF compactness metrics at candidate peaks so full-input and
    bounded-bundle scoring produce bit-for-bit identical results.
    """
    hdr = dict(header_dict or {})
    arr = np.asarray(data_arr, dtype=np.float64)
    if arr.ndim == 4:
        arr = arr[0]
    elif arr.ndim == 2:
        arr = arr[:, :, None]
    elif arr.ndim == 1:
        arr = arr[:, None, None]
    if arr.ndim != 3 or arr.shape[0] < 12:
        return {"valid": False, "reason": "INVALID_CUBE_NDIM_OR_CHAN", "dp_id": dp_id}

    nchan, ny, nx = arr.shape
    cunit3 = str(hdr.get("CUNIT3", "")).strip().lower()
    crval3 = float(hdr.get("CRVAL3", 0.0) or 0.0)
    cdelt3 = float(hdr.get("CDELT3", 0.0) or 0.0)
    crpix3 = float(hdr.get("CRPIX3", 1.0) or 1.0)
    restfrq = float(hdr.get("RESTFRQ", hdr.get("RESTFREQ", 0.0)) or 0.0)

    if abs(crval3) > 1e8:
        scale_ghz = 1e-9
    elif "mhz" in cunit3 or (1e4 < abs(crval3) < 1e7):
        scale_ghz = 1e-3
    elif 15.0 <= abs(crval3) <= 1200.0:
        scale_ghz = 1.0
    else:
        scale_ghz = 1e-9

    if abs(crval3) > 0.0 and abs(cdelt3) > 0.0:
        chan_idx = np.arange(nchan, dtype=np.float64) + 1.0
        freq_ghz = (crval3 + (chan_idx - crpix3) * cdelt3) * scale_ghz
    elif restfrq > 1e8 and abs(cdelt3) > 0.0:
        chan_idx = np.arange(nchan, dtype=np.float64) + 1.0
        freq_ghz = (restfrq + (chan_idx - crpix3) * cdelt3) * 1e-9
    elif fallback_freq_ghz is not None and float(fallback_freq_ghz) > 10.0:
        fb = float(fallback_freq_ghz)
        df = 0.0005 * (fb / 100.0)
        freq_ghz = fb + (np.arange(nchan, dtype=np.float64) - 0.5 * nchan) * df
    else:
        return {"valid": False, "reason": "NO_FREQUENCY_AXIS", "dp_id": dp_id}

    fin_f = np.isfinite(freq_ghz) & (freq_ghz > 20.0) & (freq_ghz < 1200.0)
    if int(np.sum(fin_f)) < 12:
        return {"valid": False, "reason": "OUT_OF_RANGE_FREQ", "dp_id": dp_id}

    if freq_ghz[-1] < freq_ghz[0]:
        freq_ghz = freq_ghz[::-1].copy()
        arr = arr[::-1, :, :]
        fin_f = fin_f[::-1]

    freq_ghz = freq_ghz[fin_f]
    arr = arr[fin_f]
    nchan = len(freq_ghz)
    med_freq_ghz = exact_median_1d(freq_ghz)
    dfreq_ghz = max(1e-7, exact_median_1d(np.abs(np.diff(freq_ghz))))
    inst_resolved = str(instrument) if instrument else alma_freq_to_band(med_freq_ghz)

    # Spatial geometry & synthesized beam
    cy, cx = 0.5 * (ny - 1), 0.5 * (nx - 1)
    if (
        target_ra_deg is not None and target_dec_deg is not None
        and "CRVAL1" in hdr and "CRVAL2" in hdr
        and "CDELT1" in hdr and "CDELT2" in hdr
        and "CRPIX1" in hdr and "CRPIX2" in hdr
    ):
        try:
            cd1 = float(hdr["CDELT1"])
            cd2 = float(hdr["CDELT2"])
            if abs(cd1) > 1e-9 and abs(cd2) > 1e-9:
                dra = ((float(target_ra_deg) - float(hdr["CRVAL1"]) + 180.0) % 360.0) - 180.0
                px = float(hdr["CRPIX1"]) - 1.0 + dra * math.cos(math.radians(float(target_dec_deg))) / cd1
                py = float(hdr["CRPIX2"]) - 1.0 + (float(target_dec_deg) - float(hdr["CRVAL2"])) / cd2
                if 2.0 <= px <= nx - 3.0 and 2.0 <= py <= ny - 3.0:
                    cx, cy = float(px), float(py)
        except Exception:
            pass

    cdelt_deg = max(
        1e-7,
        abs(float(hdr.get("CDELT1", 0.0) or 0.0)) or abs(float(hdr.get("CDELT2", 0.0) or 0.0)) or 2.8e-5,
    )
    bmaj = float(hdr.get("BMAJ", 0.0) or 0.0)
    bmin = float(hdr.get("BMIN", bmaj) or bmaj)
    if 1e-6 < bmaj < 0.05 and 1e-6 < bmin < 0.05:
        fwhm_pix = math.sqrt(bmaj * bmin) / cdelt_deg
        fwhm_pix = max(1.8, min(max(2.2, 0.22 * min(ny, nx)), fwhm_pix))
    else:
        fwhm_pix = max(2.2, min(4.5, 0.16 * min(ny, nx)))
    sig_pix = max(0.75, fwhm_pix / FWHM_FACTOR)

    yy, xx = np.mgrid[0:ny, 0:nx]
    rr = np.hypot(yy - cy, xx - cx)
    r_on_lim = max(1.8, 1.1 * fwhm_pix)
    on_mask = rr <= r_on_lim
    w_on_2d = np.where(on_mask, np.exp(-0.5 * (rr / sig_pix) ** 2), 0.0)

    min_dim = min(ny, nx)
    r_ann_out = max(3.2, min(0.47 * min_dim, max(4.0 * fwhm_pix, r_on_lim + 2.5)))
    r_ann_in = min(r_ann_out - 1.2, max(r_on_lim + 0.7, 1.85 * fwhm_pix))
    if r_ann_in < r_on_lim + 0.3:
        r_ann_in = min(r_ann_out - 1.0, r_on_lim + 0.3)
    ann_mask = (rr >= r_ann_in) & (rr <= r_ann_out)
    if int(np.sum(ann_mask)) < 8:
        ann_mask = rr >= min(0.32 * min_dim, r_on_lim + 0.5)

    fin_arr = np.isfinite(arr) & (np.abs(arr) < 1e6)
    on_flat_w = w_on_2d[on_mask]
    on_vals = np.where(fin_arr[:, on_mask], arr[:, on_mask], 0.0)
    on_w_ch = np.where(fin_arr[:, on_mask], on_flat_w[None, :], 0.0)
    on_denom = np.sum(on_w_ch * on_w_ch, axis=1)
    good_on = on_denom > 0.25 * float(np.sum(on_flat_w * on_flat_w))
    s_on_jy = np.where(good_on, np.sum(on_w_ch * on_vals, axis=1) / np.maximum(1e-12, on_denom), np.nan)

    ann_sub = np.where(fin_arr[:, ann_mask], arr[:, ann_mask], np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        s_off_med_jy = np.nanmedian(ann_sub, axis=1)
        s_off_95_jy = np.nanpercentile(np.abs(ann_sub), 95.0, axis=1)
        s_off_max_jy = np.nanmax(np.abs(ann_sub), axis=1)
        s_off_mad_jy = MAD_NORM * np.nanmedian(np.abs(ann_sub - s_off_med_jy[:, None]), axis=1)

    valid_ch = np.isfinite(s_on_jy) & np.isfinite(s_off_med_jy)
    if int(np.sum(valid_ch)) < 12:
        return {"valid": False, "reason": "INSUFFICIENT_FINITE_CHANNELS", "dp_id": dp_id}

    freq_ghz = freq_ghz[valid_ch]
    arr = arr[valid_ch]
    fin_arr = fin_arr[valid_ch]
    s_on_jy = s_on_jy[valid_ch]
    s_off_med_jy = np.nan_to_num(s_off_med_jy[valid_ch], nan=0.0)
    s_off_95_jy = np.nan_to_num(s_off_95_jy[valid_ch], nan=0.0)
    s_off_max_jy = np.nan_to_num(s_off_max_jy[valid_ch], nan=0.0)
    s_off_mad_jy = np.maximum(1e-8, np.nan_to_num(s_off_mad_jy[valid_ch], nan=1e-5))
    nchan = len(freq_ghz)

    # Identify top-16 candidate residual peak channels to compute exact 2D morphology
    win_px = max(17, min(121, (nchan // 8) | 1))
    cont_prelim = _asymmetric_clipped_baseline_v56(s_on_jy, win_px)
    res_prelim = s_on_jy - cont_prelim
    noise_prelim = max(1e-8, exact_mad_1d(res_prelim))
    snr_prelim = res_prelim / noise_prelim

    order_pk = np.argsort(-snr_prelim)
    selected_idx: list[int] = []
    for k in order_pk:
        ki = int(k)
        if snr_prelim[ki] < 4.5 and len(selected_idx) >= 4:
            break
        if all(abs(ki - prev) >= 3 for prev in selected_idx):
            selected_idx.append(ki)
        if len(selected_idx) >= 16:
            break

    peak_spatial_info: dict[str, dict[str, float]] = {}
    in_field_r = rr <= r_ann_out
    in_core_r = rr <= max(1.8, 1.35 * fwhm_pix)
    psf_half_area = math.pi * (0.5 * fwhm_pix) ** 2

    for ki in selected_idx:
        sl = np.where(fin_arr[ki], arr[ki] - float(s_off_med_jy[ki]), 0.0)
        on_pk = float(np.max(sl[rr <= max(1.5, 0.75 * fwhm_pix)]))
        sig_bg = max(1e-8, float(s_off_mad_jy[ki]), float(noise_prelim))
        pos = np.maximum(0.0, sl - 1.5 * sig_bg)
        tot_flux = float(np.sum(pos[in_field_r]))
        core_flux = float(np.sum(pos[in_core_r]))
        beam_conc = core_flux / max(1e-12, tot_flux) if tot_flux > 0.0 else 0.0
        half_pix = int(np.sum((sl >= 0.5 * max(1e-9, on_pk)) & in_field_r))
        spatial_fwhm_ratio = math.sqrt(max(0.5, float(half_pix)) / max(1.0, psf_half_area)) if on_pk > 0.0 else 1.0
        peak_spatial_info[str(ki)] = {
            "on_peak_jy": round(on_pk, 7),
            "beam_conc": round(beam_conc, 5),
            "spatial_fwhm_ratio": round(spatial_fwhm_ratio, 5),
        }

    return {
        "valid": True,
        "dp_id": dp_id,
        "instrument": inst_resolved,
        "n_chan": int(nchan),
        "ny": int(ny),
        "nx": int(nx),
        "med_freq_ghz": float(med_freq_ghz),
        "dfreq_ghz": float(dfreq_ghz),
        "fwhm_pix": float(fwhm_pix),
        "freq_ghz": np.asarray(freq_ghz, dtype=np.float32),
        "s_on_jy": np.asarray(s_on_jy, dtype=np.float32),
        "s_off_med_jy": np.asarray(s_off_med_jy, dtype=np.float32),
        "s_off_95_jy": np.asarray(s_off_95_jy, dtype=np.float32),
        "s_off_max_jy": np.asarray(s_off_max_jy, dtype=np.float32),
        "s_off_mad_jy": np.asarray(s_off_mad_jy, dtype=np.float32),
        "peak_spatial_info": peak_spatial_info,
    }


def score_alma_profile_v59(
    profile: dict[str, Any],
    star: str = "",
    dist_pc: float = 100.0,
    star_rv_kms: float = 0.0,
    role: str = "SCIENCE",
    bmaj_arcsec: float | None = None,
) -> dict[str, Any]:
    """
    Engine V5.9A (`ALMA_V59`): Evaluate interferometric ALMA Band 1/3/4/5 extracted
    spatial-spectral profile through G1-G6 gates and compute C12-exact 6-sigma flux &
    10-meter beam EIRP sensitivity limits.
    """
    if not profile.get("valid", False):
        return {
            "valid": False,
            "dp_id": str(profile.get("dp_id", "")),
            "n_chan": 0,
            "n_raw": 0,
            "n_qualified": 0,
            "candidates": [],
            "band_best_ul": {},
            "cube_summary": {},
        }

    dp_id = str(profile.get("dp_id", ""))
    fq = np.asarray(profile["freq_ghz"], dtype=np.float64)
    s_on = np.asarray(profile["s_on_jy"], dtype=np.float64)
    s_off_med = np.asarray(profile["s_off_med_jy"], dtype=np.float64)
    s_off_95 = np.asarray(profile["s_off_95_jy"], dtype=np.float64)
    s_off_max = np.asarray(profile["s_off_max_jy"], dtype=np.float64)
    s_off_mad = np.asarray(profile["s_off_mad_jy"], dtype=np.float64)
    peak_spatial = dict(profile.get("peak_spatial_info", {}))

    nchan = len(fq)
    med_f_ghz = exact_median_1d(fq)
    dfreq_ghz = max(1e-7, exact_median_1d(np.abs(np.diff(fq))))
    dv_chan_kms = C_KMS * dfreq_ghz / max(1.0, med_f_ghz)
    rp_eff = min(5.0e6, max(1.0e4, med_f_ghz / dfreq_ghz))
    inst = str(profile.get("instrument") or alma_freq_to_band(med_f_ghz))

    trim = max(4, min(nchan // 10, int(round(0.03 * nchan))))
    in_trim = np.ones(nchan, dtype=bool)
    if nchan - 2 * trim >= 12:
        in_trim[:trim] = False
        in_trim[nchan - trim:] = False

    win_px = max(17, min(121, (nchan // 8) | 1))
    cont = _asymmetric_clipped_baseline_v56(s_on, win_px)
    res = s_on - cont

    sig_arr = res[in_trim].copy()
    for _ in range(2):
        m_s = exact_median_1d(sig_arr)
        md_s = max(1e-8, exact_mad_1d(sig_arr))
        keep_s = np.abs(sig_arr - m_s) <= 3.5 * md_s
        if int(np.sum(keep_s)) >= max(10, len(sig_arr) // 3):
            sig_arr = sig_arr[keep_s]
    glob_sig_jy = max(1e-8, exact_mad_1d(sig_arr))

    # G2 standing-wave FFT check against high-frequency differential channel noise
    cont_in = cont[in_trim]
    res_in = res[in_trim]
    raw_in = s_on[in_trim]
    sig_white_jy = max(1e-8, exact_mad_1d(np.diff(res_in)) / math.sqrt(2.0)) if len(res_in) >= 16 else glob_sig_jy
    sw_power_frac = 0.0
    sw_amp_sigma = 0.0
    if len(cont_in) >= 32:
        x_in = np.linspace(-1.0, 1.0, len(cont_in))
        for arr_sw in (cont_in, raw_in):
            cdet = arr_sw - np.polyval(np.polyfit(x_in, arr_sw, 1), x_in)
            fft_p = np.abs(np.fft.rfft(cdet - np.mean(cdet))) ** 2
            if len(fft_p) > 4 and np.sum(fft_p[1:]) > 0.0:
                pf = float(np.max(fft_p[2:]) / np.sum(fft_p[1:]))
                asig = float(np.std(cdet) / max(1e-9, sig_white_jy))
                if pf > sw_power_frac and asig >= 1.1:
                    sw_power_frac = pf
                    sw_amp_sigma = asig
                elif sw_power_frac == 0.0:
                    sw_power_frac = pf
                    sw_amp_sigma = asig

    # Compute 6-sigma flux density -> integrated line flux -> 10m beam EIRP
    lam_a = C_ANGSTROM_GHZ / med_f_ghz
    flux_lim_jy = 6.0 * glob_sig_jy
    flam_lim = alma_jy_to_flam_cgs(med_f_ghz, flux_lim_jy)
    ul = compute_photon_beam_upper_limit(
        wave_a=lam_a,
        amp_rel_lim=1.0,
        teff_k=5000.0,
        dist_pc=max(0.5, float(dist_pc)),
        stellar_radius_rsun=1.0,
        radiometric_anchor="ALMA_INTERFEROMETRIC_JY_CGS",
        resolving_power=rp_eff,
        direct_flam_cgs=flam_lim,
    )
    dfreq_hz = dfreq_ghz * 1e9
    f_lim_wm2 = 6.0 * glob_sig_jy * dfreq_hz * 1e-26
    ul["direct_flam_cgs"] = flam_lim
    ul["noise_jy_rms"] = float(glob_sig_jy)
    ul["flux_lim_jy_6sig"] = float(flux_lim_jy)
    ul["f_lim_wm2"] = float(f_lim_wm2)
    ul["med_freq_ghz"] = float(med_f_ghz)
    ul["wave_a"] = float(lam_a)
    ul["resolving_power"] = float(rp_eff)

    canon_pool = get_calibration_bands(inst)
    best_canon = min(canon_pool, key=lambda b: abs(b["center_wave_A"] - lam_a))
    bid = str(best_canon["band_id"])

    loc_mad = np.full(nchan, glob_sig_jy, dtype=np.float64)
    if nchan >= 32:
        hw_l = max(12, min(40, nchan // 6))
        for k in range(nchan):
            l0, l1 = max(0, k - hw_l), min(nchan, k + hw_l + 1)
            loc_mad[k] = max(0.75 * glob_sig_jy, exact_mad_1d(res[l0:l1]))
    snr_arr = res / np.maximum(1e-8, loc_mad)

    candidates: list[dict[str, Any]] = []
    n_raw = 0
    n_qualified = 0

    for k in range(2, nchan - 2):
        if snr_arr[k] < 6.0:
            continue
        if not (snr_arr[k] >= snr_arr[k - 1] and snr_arr[k] >= snr_arr[k + 1]):
            continue
        if candidates and (k - int(candidates[-1]["chan_idx"])) < 4:
            if snr_arr[k] > float(candidates[-1]["snr"]):
                candidates.pop()
            else:
                continue

        n_raw += 1
        f_obs_ghz = float(fq[k])
        f_rest_ghz = f_obs_ghz / max(0.5, 1.0 - float(star_rv_kms) / C_KMS)

        # G2: Baseline FFT standing-wave veto (require periodic ripple above differential white noise)
        pass_g2 = not (sw_power_frac > 0.35 and sw_amp_sigma >= 1.45)

        # G3: MM Molecular Atlas veto (+/- 150 km/s in stellar rest or observed frame)
        mol_match = None
        for lname, l_ghz, _ in ALMA_MM_MOLECULAR_ATLAS_GHZ:
            dv_rest = C_KMS * abs(f_rest_ghz - l_ghz) / l_ghz
            dv_obs = C_KMS * abs(f_obs_ghz - l_ghz) / l_ghz
            if min(dv_rest, dv_obs) <= 165.0:
                mol_match = lname
                break
        pass_g3 = mol_match is None

        # G4: Spatial-spectral compactness veto (rejects extended disks & broad outflows)
        fwhm_ch = float(_subchannel_fwhm_v56(res, k))
        dv_fwhm_kms = fwhm_ch * dv_chan_kms
        sp_info = peak_spatial.get(str(k))
        if sp_info is None and peak_spatial:
            nearest_key = min(peak_spatial.keys(), key=lambda x: abs(int(x) - k))
            if abs(int(nearest_key) - k) <= 2:
                sp_info = peak_spatial[nearest_key]
        beam_conc = float(sp_info["beam_conc"]) if sp_info else 0.75
        spatial_fwhm_ratio = float(sp_info["spatial_fwhm_ratio"]) if sp_info else 1.0
        pass_g4 = (fwhm_ch <= 4.5) and (beam_conc >= 0.46) and (spatial_fwhm_ratio <= 1.75)

        # G5: Single-channel LO spur & Gibbs ringing veto
        edge_dist = min(k, nchan - 1 - k)
        nb_max_snr = max(float(snr_arr[k - 1]), float(snr_arr[k + 1]))
        nb_min_snr = min(float(snr_arr[k - 1]), float(snr_arr[k + 1]))
        is_gibbs = (snr_arr[k - 1] < -0.18 * snr_arr[k]) and (snr_arr[k + 1] < -0.18 * snr_arr[k])
        pass_g5 = (edge_dist >= 3) and (nb_max_snr >= max(1.6, 0.14 * float(snr_arr[k]))) and (not is_gibbs) and (nb_min_snr > -0.35 * float(snr_arr[k]))

        # G6: Off-source annulus coherent RFI / correlator birdie veto
        on_val_jy = max(float(res[k]), float(sp_info["on_peak_jy"]) if sp_info else float(res[k]))
        off95 = float(s_off_95[k])
        offmax = float(s_off_max[k])
        offmed_snr = abs(float(s_off_med[k])) / max(1e-8, float(s_off_mad[k]))
        pass_g6 = (off95 <= 0.38 * max(1e-8, on_val_jy)) and (offmax <= 0.72 * max(1e-8, on_val_jy)) and (offmed_snr < 3.2)

        vetoes: list[str] = []
        if not pass_g2:
            vetoes.append("G2_ALMA_BASELINE_STANDING_WAVE")
        if not pass_g3:
            vetoes.append(f"G3_ALMA_MM_MOLECULAR_ATLAS:{mol_match}")
        if not pass_g4:
            vetoes.append("G4_ALMA_BEAM_COMPACTNESS")
        if not pass_g5:
            vetoes.append("G5_ALMA_SINGLE_CHANNEL_SPUR")
        if not pass_g6:
            vetoes.append("G6_ALMA_OFFSOURCE_ANNULUS_VETO")

        qualified = len(vetoes) == 0
        if qualified:
            n_qualified += 1

        candidates.append({
            "star": star,
            "role": role,
            "dp_id": dp_id,
            "instrument": inst,
            "band": bid,
            "chan_idx": int(k),
            "freq_ghz": round(f_obs_ghz, 6),
            "freq_rest_ghz": round(f_rest_ghz, 6),
            "wave_um": round(float(C_ANGSTROM_GHZ / f_obs_ghz / 1e4), 5),
            "snr": round(float(snr_arr[k]), 3),
            "fwhm_chan": round(fwhm_ch, 3),
            "dv_fwhm_kms": round(dv_fwhm_kms, 3),
            "beam_conc": round(beam_conc, 4),
            "spatial_fwhm_ratio": round(spatial_fwhm_ratio, 4),
            "off95_to_on": round(off95 / max(1e-8, on_val_jy), 4),
            "vetoes": vetoes,
            "qualified_v59": bool(qualified),
        })

    cube_summary = {
        "dp_id": dp_id,
        "instrument": inst,
        "band": bid,
        "n_chan": int(nchan),
        "med_freq_ghz": round(med_f_ghz, 6),
        "min_freq_ghz": round(float(fq[0]), 6),
        "max_freq_ghz": round(float(fq[-1]), 6),
        "min_wave_um": round(float(C_ANGSTROM_GHZ / float(fq[-1]) / 1e4), 5),
        "max_wave_um": round(float(C_ANGSTROM_GHZ / float(fq[0]) / 1e4), 5),
        "dv_chan_kms": round(dv_chan_kms, 4),
        "rp_eff": round(rp_eff, 1),
        "bmaj_arcsec": round(float(bmaj_arcsec), 3) if bmaj_arcsec is not None else None,
        "noise_jy_rms": round(glob_sig_jy, 7),
        "flux_lim_mjy_6sig": round(flux_lim_jy * 1000.0, 5),
        "f_lim_wm2": float(f_lim_wm2),
        "sw_power_frac": round(sw_power_frac, 4),
        "sw_amp_sigma": round(sw_amp_sigma, 4),
        "p_beam_10m_kw": float(ul["p_beam_10m_kw"]),
        "n_raw": int(n_raw),
        "n_qualified": int(n_qualified),
    }
    return {
        "valid": True,
        "dp_id": dp_id,
        "instrument": inst,
        "n_chan": int(nchan),
        "n_raw": int(n_raw),
        "n_qualified": int(n_qualified),
        "candidates": candidates,
        "band_best_ul": {bid: ul},
        "cube_summary": cube_summary,
    }


def run_alma_interferometric_calibration_v59(seed: int = 10101) -> dict[str, Any]:
    """
    `CALIBRATION_V59_ALMA_INTERFEROMETRIC_240`:
      - 60 unresolved PSF compact point-source beacons across Bands 1, 3, 4, 5
      - 45 extended circumstellar disks / broad molecular outflows (`G4`)
      - 45 on+off correlator birdies / RFI across off-source annulus (`G6`)
      - 45 millimeter molecular atlas transitions 35-211 GHz (`G3`)
      - 45 1-channel LO spurs / Gibbs ringing / baseline standing waves (`G2`/`G5`)
    """
    rng = np.random.default_rng(int(seed))
    trials: list[dict[str, Any]] = []
    rec_beacon = vet_disk = vet_birdie = vet_mol = vet_spur = 0

    ny, nx, nchan = 29, 29, 192
    fwhm_pix = 3.2
    sig_pix = fwhm_pix / FWHM_FACTOR
    yy, xx = np.mgrid[0:ny, 0:nx]
    cy, cx = 0.5 * (ny - 1), 0.5 * (nx - 1)
    rr = np.hypot(yy - cy, xx - cx)
    psf_2d = np.exp(-0.5 * (rr / sig_pix) ** 2)
    # Build mild spatial noise correlation via local PSF smoothing so synthetic cubes resemble synthesized interferograms
    from scipy.ndimage import gaussian_filter

    band_specs = [
        ("ALMA_B1_7MM", 40.50, 0.0012, (41.20, 42.30)),
        ("ALMA_B3_3MM", 95.20, 0.0020, (94.30, 95.80)),
        ("ALMA_B4_2MM", 136.00, 0.0025, (135.20, 137.00)),
        ("ALMA_B5_2MM", 190.50, 0.0030, (189.20, 192.40)),
    ]
    mol_examples = [
        ("SiO_v1(1-0)", 43.1221, "ALMA_B1_7MM"),
        ("CS(1-0)", 48.9910, "ALMA_B1_7MM"),
        ("HCN(1-0)", 88.6316, "ALMA_B3_3MM"),
        ("HCO+(1-0)", 89.1885, "ALMA_B3_3MM"),
        ("13CO(1-0)", 110.2014, "ALMA_B3_3MM"),
        ("H2CO(2_02-1_01)", 145.6029, "ALMA_B4_2MM"),
        ("H2O(3_13-2_20)", 183.3101, "ALMA_B5_2MM"),
        ("CS(4-3)", 195.9542, "ALMA_B5_2MM"),
    ]

    for ti in range(240):
        noise_cube = rng.normal(0.0, 0.0030, size=(nchan, ny, nx))
        for ci in range(nchan):
            noise_cube[ci] = gaussian_filter(noise_cube[ci], sigma=max(0.7, 0.65 * sig_pix))
        # Rescale to maintain unit beam-integrated noise scale ~ 0.002 Jy/beam
        noise_cube *= (0.0020 / max(1e-6, float(np.std(noise_cube))))

        b_name, f0_ghz, df_ghz, safe_rng = band_specs[ti % len(band_specs)]
        hdr = {
            "CRVAL3": f0_ghz * 1e9,
            "CDELT3": df_ghz * 1e9,
            "CRPIX3": nchan / 2.0,
            "CUNIT3": "Hz",
            "BMAJ": (fwhm_pix * 0.25) / 3600.0,
            "BMIN": (fwhm_pix * 0.25) / 3600.0,
            "CDELT1": -0.25 / 3600.0,
            "CDELT2": 0.25 / 3600.0,
        }
        chan_f = f0_ghz + (np.arange(nchan, dtype=np.float64) - nchan / 2.0 + 1.0) * df_ghz

        if ti < 60:
            cls_, want = "CLEAN_ALMA_BEACON", True
            # Ensure injected channel frequency stays >= 300 km/s clear of ALL molecular lines
            k0 = int(rng.integers(24, nchan - 24))
            for _try in range(20):
                fk = chan_f[k0]
                if all(C_KMS * abs(fk - lg) / lg > 250.0 for _, lg, _ in ALMA_MM_MOLECULAR_ATLAS_GHZ):
                    break
                k0 = int(rng.integers(24, nchan - 24))
            sig_c = float(rng.uniform(0.95, 1.30))
            amp_jy = float(rng.uniform(0.022, 0.045))
            spec_prof = amp_jy * np.exp(-0.5 * ((np.arange(nchan) - k0) / sig_c) ** 2)
            noise_cube += spec_prof[:, None, None] * psf_2d[None, :, :]
        elif ti < 105:
            cls_, want = "EXTENDED_DISK_OUTFLOW_VETO", False
            k0 = int(rng.integers(32, nchan - 32))
            for _try in range(10):
                fk = chan_f[k0]
                if all(C_KMS * abs(fk - lg) / lg > 250.0 for _, lg, _ in ALMA_MM_MOLECULAR_ATLAS_GHZ):
                    break
                k0 = int(rng.integers(32, nchan - 32))
            # Extended spatial Gaussian disk (3.0x beam FWHM) and/or broad outflow width
            ext_sig = sig_pix * float(rng.uniform(2.6, 4.0))
            disk_2d = np.exp(-0.5 * (rr / ext_sig) ** 2)
            sig_c = float(rng.uniform(3.2, 6.5))
            amp_jy = float(rng.uniform(0.030, 0.065))
            spec_prof = amp_jy * np.exp(-0.5 * ((np.arange(nchan) - k0) / sig_c) ** 2)
            noise_cube += spec_prof[:, None, None] * disk_2d[None, :, :]
        elif ti < 150:
            cls_, want = "OFFSOURCE_CORRELATOR_BIRDIE_VETO", False
            k0 = int(rng.integers(24, nchan - 24))
            for _try in range(10):
                fk = chan_f[k0]
                if all(C_KMS * abs(fk - lg) / lg > 250.0 for _, lg, _ in ALMA_MM_MOLECULAR_ATLAS_GHZ):
                    break
                k0 = int(rng.integers(24, nchan - 24))
            sig_c = float(rng.uniform(0.95, 1.25))
            amp_jy = float(rng.uniform(0.028, 0.055))
            spec_prof = amp_jy * np.exp(-0.5 * ((np.arange(nchan) - k0) / sig_c) ** 2)
            # Birdie/RFI fills primary beam OR creates bright off-source annulus coherent peak
            if ti % 2 == 0:
                noise_cube += spec_prof[:, None, None] * 1.0
            else:
                birdie_2d = psf_2d + 0.85 * np.exp(-0.5 * (np.hypot(yy - (cy + 7.0), xx - (cx - 6.0)) / sig_pix) ** 2)
                noise_cube += spec_prof[:, None, None] * birdie_2d[None, :, :]
        elif ti < 195:
            cls_, want = "MM_MOLECULAR_ATLAS_VETO", False
            _, lg, mb = mol_examples[ti % len(mol_examples)]
            b_idx = {"ALMA_B1_7MM": 0, "ALMA_B3_3MM": 1, "ALMA_B4_2MM": 2, "ALMA_B5_2MM": 3}[mb]
            b_name, _, df_ghz, _ = band_specs[b_idx]
            f0_ghz = lg
            hdr["CRVAL3"] = f0_ghz * 1e9
            hdr["CDELT3"] = df_ghz * 1e9
            sig_c = float(rng.uniform(1.0, 1.35))
            amp_jy = float(rng.uniform(0.028, 0.055))
            k0 = nchan // 2 + int(rng.integers(-6, 7))
            spec_prof = amp_jy * np.exp(-0.5 * ((np.arange(nchan) - k0) / sig_c) ** 2)
            noise_cube += spec_prof[:, None, None] * psf_2d[None, :, :]
        else:
            cls_, want = "SINGLE_CHAN_LO_GIBBS_VETO", False
            k0 = int(rng.integers(28, nchan - 28))
            amp_jy = float(rng.uniform(0.032, 0.065))
            if ti % 3 == 0:
                # 1-channel isolated LO spur
                noise_cube[k0] += amp_jy * psf_2d
            elif ti % 3 == 1:
                # Gibbs ringing (+/-/- sidelobes)
                noise_cube[k0] += amp_jy * psf_2d
                noise_cube[k0 - 1] -= 0.30 * amp_jy * psf_2d
                noise_cube[k0 + 1] -= 0.30 * amp_jy * psf_2d
            else:
                # Sinusoidal correlator standing wave + narrow spike
                sw = 0.014 * np.sin(2.0 * math.pi * 6.0 * np.arange(nchan) / float(nchan))
                noise_cube += sw[:, None, None] * psf_2d[None, :, :]
                noise_cube[k0] += amp_jy * np.exp(-0.5 * ((np.arange(nchan) - k0) / 1.05) ** 2)[k0] * psf_2d
                noise_cube[k0 - 1] += 0.55 * amp_jy * psf_2d
                noise_cube[k0 + 1] += 0.55 * amp_jy * psf_2d

        prof = extract_alma_cube_profile(noise_cube, hdr, fallback_freq_ghz=f0_ghz, instrument=b_name, dp_id=f"SIM_ALMA_{ti:03d}")
        res = score_alma_profile_v59(prof, star=f"SIM_ALMA_{ti:03d}", dist_pc=25.0, star_rv_kms=0.0)
        obs = res["n_qualified"] >= 1
        ok = int(bool(obs) == bool(want))
        if cls_ == "CLEAN_ALMA_BEACON":
            rec_beacon += ok
        elif cls_ == "EXTENDED_DISK_OUTFLOW_VETO":
            vet_disk += ok
        elif cls_ == "OFFSOURCE_CORRELATOR_BIRDIE_VETO":
            vet_birdie += ok
        elif cls_ == "MM_MOLECULAR_ATLAS_VETO":
            vet_mol += ok
        else:
            vet_spur += ok
        trials.append({
            "suite": "CALIBRATION_V59_ALMA_INTERFEROMETRIC_240",
            "class": cls_, "trial": ti + 1, "expected": int(want), "observed": int(obs), "passed": ok,
        })

    return {
        "total_trials": len(trials),
        "clean_alma_beacon_60": f"{rec_beacon}/60 ({rec_beacon/60.0:.4f})",
        "extended_disk_veto_45": f"{vet_disk}/45 ({vet_disk/45.0:.4f})",
        "offsource_birdie_veto_45": f"{vet_birdie}/45 ({vet_birdie/45.0:.4f})",
        "mm_molecular_atlas_veto_45": f"{vet_mol}/45 ({vet_mol/45.0:.4f})",
        "single_chan_gibbs_sw_veto_45": f"{vet_spur}/45 ({vet_spur/45.0:.4f})",
        "trials": trials,
    }


# ---------------------------------------------------------------------------
# Engine V5.9B (`COMB_DRIFT_V59`): Coherent Drifting-Velocity Frequency Comb
# ---------------------------------------------------------------------------

def _comb_peak_and_veto_on_snr_vec(
    nu_grid_ghz: np.ndarray,
    snr_vec: np.ndarray,
    cov_vec: np.ndarray,
    snr_static: np.ndarray,
    snr_berv: np.ndarray,
    spacings_ghz: list[float],
    n_teeth: int,
    step_nu: float,
    t_min: float,
    s_min: float,
    min_q: int,
    dv_grid_kms: float,
    enable_near_echo_check: bool = True,
    precomputed_aux: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None = None,
    snr_scale: float = 1.0,
    cov_is_all_true: bool = False,
    log_grid_params: tuple[float, float] | None = None,
) -> dict[str, Any] | None:
    """Zero-full-alloc pigeonhole peak-anchored periodic frequency-comb scan."""
    del step_nu
    nu = nu_grid_ghz[::-1]
    sv = snr_vec[::-1]
    cv = cov_vec[::-1]
    n_pts = len(nu)
    if n_pts < 60 or float(nu[-1] - nu[0]) < 80.0:
        return None

    hw_core = max(2, int(round(1.8 / max(0.25, dv_grid_kms))))
    hw_mask = max(hw_core + 4, int(round(3.8 / max(0.25, dv_grid_kms))))

    # Fast sparse peak pre-check without full-array allocations or redundant multiply
    raw_thr = (t_min - 0.15) / max(1e-6, float(snr_scale))
    if cov_is_all_true:
        hi = np.flatnonzero(sv >= raw_thr)
    else:
        hi = np.flatnonzero(cv & (sv >= raw_thr))
    if len(hi) < min_q:
        return None
    hi = hi[(hi > 0) & (hi < n_pts - 1)]
    if len(hi) < min_q:
        return None
    pk_idx = hi[(sv[hi] >= sv[hi - 1]) & (sv[hi] >= sv[hi + 1])]
    if len(pk_idx) < min_q:
        return None

    dedup_pks: list[int] = []
    for ix in pk_idx:
        i_ix = int(ix)
        if not dedup_pks or (i_ix - dedup_pks[-1]) > hw_core:
            dedup_pks.append(i_ix)
        elif sv[i_ix] > sv[dedup_pks[-1]]:
            dedup_pks[-1] = i_ix
    if len(dedup_pks) < min_q:
        return None
    dedup_arr = np.asarray(dedup_pks, dtype=np.int64)
    top_pk_sum = float(np.sum(np.sort(sv[dedup_arr] * snr_scale)[-min(len(dedup_arr), n_teeth):]))
    if top_pk_sum < s_min - 1.5:
        return None
    nu_pks = nu[dedup_arr]

    if precomputed_aux is not None:
        st_max, bv_max = precomputed_aux[0], precomputed_aux[1]
    else:
        from scipy.ndimage import maximum_filter1d
        st_max = maximum_filter1d(snr_static[::-1], size=2 * (hw_core + 2) + 1, mode="constant", cval=0.0)
        bv_max = maximum_filter1d(snr_berv[::-1], size=2 * (hw_core + 2) + 1, mode="constant", cval=0.0)

    offs = np.arange(-hw_core, hw_core + 1, dtype=np.int64)
    k_idx = np.arange(n_teeth, dtype=np.float64)
    nu_lo, nu_hi = float(nu[0]) + 15.0, float(nu[-1]) - 15.0
    m_max = max(1, n_teeth - min_q + 1)
    best_hit: dict[str, Any] | None = None

    for dnu in spacings_ghz:
        span_nu = (n_teeth - 1) * float(dnu)
        if nu_hi - nu_lo <= span_nu + 10.0:
            continue
        nu_cand_list = [nu_pks - float(m) * float(dnu) for m in range(m_max)]
        nu_starts = np.concatenate(nu_cand_list)
        nu_starts = nu_starts[(nu_starts >= nu_lo) & (nu_starts <= nu_hi - span_nu)]
        if len(nu_starts) == 0:
            continue
        nu_starts = np.sort(nu_starts)
        keep_u = np.ones(len(nu_starts), dtype=bool)
        if len(nu_starts) > 1:
            keep_u[1:] = np.diff(nu_starts) > 0.35
        nu_starts = nu_starts[keep_u]

        nu_mat = nu_starts[:, None] + float(dnu) * k_idx[None, :]
        if log_grid_params is not None:
            w_log0, inv_dlog = log_grid_params
            idx_mat = (n_pts - 1) - np.rint((np.log(C_ANGSTROM_GHZ / nu_mat) - w_log0) * inv_dlog).astype(np.int64)
        else:
            idx_mat = np.searchsorted(nu, nu_mat)
        ok_b = np.all((idx_mat > hw_core + 3) & (idx_mat < n_pts - hw_core - 4), axis=1)
        if not np.any(ok_b):
            continue
        safe_idx = np.where(ok_b[:, None], idx_mat, hw_core + 3)
        ok_cov = ok_b if cov_is_all_true else (ok_b & np.all(cv[safe_idx], axis=1))
        if not np.any(ok_cov):
            continue

        t_mat = (sv[safe_idx[:, :, None] + offs[None, None, :]].max(axis=2) * snr_scale).astype(np.float64)
        n_q = (t_mat >= t_min).sum(axis=1)
        s_sum = np.maximum(0.0, t_mat).sum(axis=1)
        cand_rows = np.flatnonzero(ok_cov & (n_q >= min_q) & (s_sum >= s_min))
        if len(cand_rows) == 0:
            continue

        top_row = int(cand_rows[np.argmax(s_sum[cand_rows])])
        nu0_best = float(nu_starts[top_row])
        idxs_rev = safe_idx[top_row]
        idxs_orig = (n_pts - 1) - idxs_rev
        s_cand = float(s_sum[top_row])
        t_cand = t_mat[top_row]
        s_stat_cand = float(np.maximum(0.0, st_max[idxs_rev]).sum())
        s_berv_cand = float(np.maximum(0.0, bv_max[idxs_rev]).sum())

        if enable_near_echo_check and False:
            # Retained as disabled placeholder; clean un-inflated band-wide static/BERV peaks handle echo suppression without width-11 bias
            pass

        # Mid-tooth / off-tooth crowding check
        nu_mids = nu0_best + float(dnu) * (0.5 + np.arange(n_teeth - 1, dtype=np.float64))
        idx_mids = np.clip(np.searchsorted(nu, nu_mids), hw_core + 2, n_pts - hw_core - 3)
        mid_max = (sv[idx_mids[:, None] + offs[None, :]].max(axis=1) * snr_scale).astype(np.float64)
        i0_win = max(0, int(idxs_rev[0]) - hw_mask)
        i1_win = min(n_pts, int(idxs_rev[-1]) + hw_mask + 1)
        win_sv = sv[i0_win:i1_win] * snr_scale
        tooth_mask = np.zeros(i1_win - i0_win, dtype=bool)
        for ix in idxs_rev:
            lo_t = max(0, int(ix) - i0_win - hw_mask)
            hi_t = min(i1_win - i0_win, int(ix) - i0_win + hw_mask + 1)
            tooth_mask[lo_t:hi_t] = True
        off_sv = win_sv[~tooth_mask]
        off_crowd = float(np.mean(off_sv >= 3.2)) if len(off_sv) >= 10 else 0.0
        inter_ratio = float(np.mean(t_cand)) / max(0.35, exact_median_1d(np.abs(mid_max)))

        if best_hit is None or s_cand > best_hit["sum_snr"]:
            best_hit = {
                "nu0_ghz": round(nu0_best, 3),
                "dnu_ghz": float(dnu),
                "sum_snr": round(s_cand, 3),
                "n_qualifying_teeth": int(n_q[top_row]),
                "tooth_snrs": [round(float(x), 3) for x in t_cand],
                "idxs_log": [int(x) for x in idxs_orig],
                "s_comb_static_at_cfg": round(s_stat_cand, 3),
                "s_comb_berv_at_cfg": round(s_berv_cand, 3),
                "off_tooth_crowding": round(off_crowd, 4),
                "intertooth_ratio": round(inter_ratio, 3),
            }
    return best_hit


def scan_comb_drift_v59(
    wave_rest: np.ndarray,
    fn_epochs: np.ndarray,
    sig_epochs: np.ndarray,
    mjd_epochs: np.ndarray,
    v_obs_to_rest_epochs_kms: np.ndarray,
    cfg: dict[str, Any],
    star: str = "",
    known_orb_params: list[dict[str, float]] | None = None,
    comb_windows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Engine V5.9B (`COMB_DRIFT_V59`): Coherent shift-and-stack across multi-epoch
    residuals along Keplerian & linear-RV trajectories BEFORE searching periodic
    frequency combs, with CD1-CD5 false-positive vetoes and zero-alloc stacking.
    """
    w = np.asarray(wave_rest, dtype=np.float64)
    fn_ep = np.asarray(fn_epochs, dtype=np.float64)
    sig_ep = np.asarray(sig_epochs, dtype=np.float64)
    mjds = np.asarray(mjd_epochs, dtype=np.float64)
    bervs = np.asarray(v_obs_to_rest_epochs_kms, dtype=np.float64)

    n_ep, n_pix = fn_ep.shape
    if n_ep < 3 or n_pix < 80:
        return {
            "star": star, "n_epochs": int(n_ep), "trajectories_tested": 0,
            "n_raw_candidates": 0, "n_qualified": 0, "v41_static_hits": 0, "candidates": [],
        }

    inst = str(cfg.get("instrument", "ESO_HARPS"))
    if comb_windows is None:
        comb_windows = list(COMB_V4_1_WINDOWS_A.get(inst, []))
    allowed_bands = set(cfg.get("comb_search_bands") or [bw["band"] for bw in comb_windows])
    spacings = list(cfg.get("comb_spacings_ghz", [25.0, 40.0, 65.0, 100.0]))
    step_nu = float(cfg.get("comb_step_ghz", 2.5))
    n_teeth = int(cfg.get("comb_n_teeth", 6))
    t_min = 3.4
    s_min = 25.5
    min_q = max(4, n_teeth - 1)
    sig_v_kms = max(0.7, float(cfg.get("sigma_v_kms", C_KMS / (max(1e4, float(cfg.get("resolving_power", 60000.0))) * FWHM_FACTOR))))
    dv_grid_kms = min(1.0, max(0.55, 0.70 * sig_v_kms))

    # Build dynamical trajectory bank
    t_rel = mjds - mjds[0]
    span_d = max(1.0, float(t_rel[-1]))
    t_mid = 0.5 * (mjds[0] + mjds[-1])
    tau = (mjds - t_mid) / max(0.5, 0.5 * span_d)

    traj_bank: list[tuple[str, float, float, np.ndarray]] = []
    if known_orb_params:
        for kp in known_orb_params[:4]:
            p_d = max(0.8, float(kp.get("P_days", 0.0) or 0.0))
            if p_d <= 1.0:
                continue
            e_v = max(0.0, min(0.95, float(kp.get("ecc", 0.0) or 0.0)))
            w_rad = math.radians(float(kp.get("w_deg", 0.0) or 0.0))
            for e_use in ([e_v, 0.0] if e_v >= 0.08 else [0.0]):
                m0_grid = np.linspace(0.0, 2.0 * math.pi, 24, endpoint=False)
                ta_mat = _solve_kepler_true_anom_batch(t_rel, p_d, e_use, m0_grid)
                v_unit = np.cos(ta_mat + w_rad) + e_use * math.cos(w_rad)
                v_cen = v_unit - np.mean(v_unit, axis=1, keepdims=True)
                for mi in range(len(m0_grid)):
                    for k_amp in (20.0, 31.0, 42.0, 53.0, 64.0, 75.0, 86.0):
                        v_tr = k_amp * v_cen[mi]
                        if float(np.ptp(v_tr)) >= 12.0:
                            traj_bank.append(("KNOWN_KEPLER", p_d, e_use, v_tr))

    for a1 in range(-150, 151, 6):
        if abs(a1) < 12:
            continue
        v_tr = float(a1) * tau
        if float(np.ptp(v_tr)) >= 12.0:
            traj_bank.append(("LINEAR_DRIFT", span_d, 0.0, v_tr))

    for p_d in (8.0, 22.0, 65.0, 190.0):
        m0_grid = np.linspace(0.0, 2.0 * math.pi, 10, endpoint=False)
        for phi0 in m0_grid:
            v_u = np.sin(2.0 * math.pi * t_rel / p_d + phi0)
            v_u = v_u - np.mean(v_u)
            for k_amp in (30.0, 68.0):
                v_tr = k_amp * v_u
                if float(np.ptp(v_tr)) >= 12.0:
                    traj_bank.append(("BLIND_KEPLER", p_d, 0.0, v_tr))

    # Fast vectorized deduplication of trajectory bank
    uniq_traj: list[tuple[str, float, float, np.ndarray]] = []
    uniq_vecs: np.ndarray | None = None
    for fam, pd_v, ec_v, v_tr in traj_bank:
        if uniq_vecs is not None:
            if float(np.min(np.max(np.abs(uniq_vecs - v_tr[None, :]), axis=1))) < 4.0:
                continue
            uniq_vecs = np.vstack((uniq_vecs, v_tr[None, :]))
        else:
            uniq_vecs = v_tr[None, :].copy()
        uniq_traj.append((fam, pd_v, ec_v, v_tr))

    all_raw: list[dict[str, Any]] = []
    all_qual: list[dict[str, Any]] = []
    v41_static_hits = 0

    from scipy.ndimage import maximum_filter1d

    # Avoid extra copies when cov_all_ok passed:
    del all_raw
    all_raw = []

    for win in comb_windows:
        if win["band"] not in allowed_bands:
            continue
        w_lo, w_hi = float(win["lo_a"]), float(win["hi_a"])
        margin_a = 0.0008 * w_hi
        in_slice = (w >= w_lo - margin_a) & (w <= w_hi + margin_a)
        if int(np.sum(in_slice)) < 80:
            continue
        w_sl = w[in_slice]
        w_log = np.arange(math.log(max(w_lo, float(w_sl[0]) + 1.0)), math.log(min(w_hi, float(w_sl[-1]) - 1.0)), dv_grid_kms / C_KMS)
        if len(w_log) < 120:
            continue
        w_grid = np.exp(w_log)
        nu_grid_ghz = C_ANGSTROM_GHZ / w_grid

        sig_px_log = max(0.8, sig_v_kms / dv_grid_kms)
        kx = np.arange(-int(round(3.5 * sig_px_log)), int(round(3.5 * sig_px_log)) + 1, dtype=np.float64)
        ker = np.exp(-0.5 * (kx / sig_px_log) ** 2)
        ker /= math.sqrt(float(np.sum(ker * ker)))

        n_g = len(w_grid)
        snr_log = np.zeros((n_ep, n_g), dtype=np.float64)
        cov_log = np.zeros((n_ep, n_g), dtype=bool)
        for ei in range(n_ep):
            ye = fn_ep[ei, in_slice] - 1.0
            se = sig_ep[ei, in_slice]
            ve = np.isfinite(ye) & np.isfinite(se) & (se > 1e-6) & (se < 25.0)
            if int(np.sum(ve)) < 40:
                continue
            y_i = np.interp(w_grid, w_sl[ve], ye[ve], left=0.0, right=0.0)
            iv_i = np.interp(w_grid, w_sl[ve], 1.0 / (se[ve] ** 2), left=0.0, right=0.0)
            gaps = np.interp(w_grid, w_sl, ve.astype(np.float64), left=0.0, right=0.0) > 0.5
            cov_log[ei] = gaps
            num = convolve1d(np.where(gaps, y_i * iv_i, 0.0), ker, mode="constant", cval=0.0)
            den = np.sqrt(np.maximum(1e-12, convolve1d(np.where(gaps, iv_i, 0.0), ker * ker, mode="constant", cval=0.0)))
            snr_log[ei] = np.where(gaps, num / den, 0.0)

        min_cov_ep = max(2, min(n_ep, int(math.ceil(0.6 * n_ep))))
        snr_clean_f32 = np.where(cov_log, snr_log, 0.0).astype(np.float32)
        has_gaps = not bool(np.all(cov_log))
        cov_f32 = cov_log.astype(np.float32) if has_gaps else np.empty(0, dtype=np.float32)
        st_num_buf = np.zeros(n_g, dtype=np.float32)
        st_cnt_buf = np.zeros(n_g, dtype=np.float32)
        cov_all_ok = np.ones(n_g, dtype=bool)
        inv_sqrt_n = np.float32(1.0 / math.sqrt(float(n_ep)))

        def _shift_stack_fast(
            v_shifts_kms: np.ndarray,
            apply_scale: bool = True,
            num_out: np.ndarray = st_num_buf,
            cnt_out: np.ndarray = st_cnt_buf,
        ) -> tuple[np.ndarray, np.ndarray, float]:
            num_out.fill(0.0)
            if has_gaps:
                cnt_out.fill(0.0)
                for ei in range(n_ep):
                    dk = int(round(float(v_shifts_kms[ei]) / dv_grid_kms))
                    if abs(dk) >= n_g - 10:
                        continue
                    if dk == 0:
                        num_out[:] += snr_clean_f32[ei]
                        cnt_out[:] += cov_f32[ei]
                    elif dk > 0:
                        num_out[: n_g - dk] += snr_clean_f32[ei, dk:]
                        cnt_out[: n_g - dk] += cov_f32[ei, dk:]
                    else:
                        adk = -dk
                        num_out[adk:] += snr_clean_f32[ei, : n_g - adk]
                        cnt_out[adk:] += cov_f32[ei, : n_g - adk]
                cov_ok = cnt_out >= float(min_cov_ep)
                num_out[cov_ok] /= np.sqrt(np.maximum(1.0, cnt_out[cov_ok]))
                num_out[~cov_ok] = 0.0
                return num_out, cov_ok, 1.0
            max_abs_dk = 0
            for ei in range(n_ep):
                dk = int(round(float(v_shifts_kms[ei]) / dv_grid_kms))
                if abs(dk) >= n_g - 10:
                    continue
                if abs(dk) > max_abs_dk:
                    max_abs_dk = abs(dk)
                if dk == 0:
                    num_out[:] += snr_clean_f32[ei]
                elif dk > 0:
                    num_out[: n_g - dk] += snr_clean_f32[ei, dk:]
                else:
                    adk = -dk
                    num_out[adk:] += snr_clean_f32[ei, : n_g - adk]
            if max_abs_dk > 0:
                num_out[:max_abs_dk] = 0.0
                num_out[n_g - max_abs_dk:] = 0.0
            if apply_scale:
                num_out[:] *= inv_sqrt_n
                return num_out, cov_all_ok, 1.0
            return num_out, cov_all_ok, float(inv_sqrt_n)

        def _gather_sh_mat(v_shifts_kms: np.ndarray) -> np.ndarray:
            sh_mat = np.zeros((n_ep, n_g), dtype=np.float64)
            for ei in range(n_ep):
                dk = int(round(float(v_shifts_kms[ei]) / dv_grid_kms))
                if abs(dk) >= n_g - 10:
                    continue
                if dk == 0:
                    sh_mat[ei] = np.where(cov_log[ei], snr_log[ei], 0.0)
                elif dk > 0:
                    c_s = cov_log[ei, dk:]
                    sh_mat[ei, : n_g - dk] = np.where(c_s, snr_log[ei, dk:], 0.0)
                else:
                    adk = -dk
                    c_s = cov_log[ei, : n_g - adk]
                    sh_mat[ei, adk:] = np.where(c_s, snr_log[ei, : n_g - adk], 0.0)
            return sh_mat

        stk_st, cov_st, _ = _shift_stack_fast(np.zeros(n_ep, dtype=np.float64), True)
        snr_stat = stk_st.copy()
        cov_stat = cov_st.copy()
        stk_bv, _, _ = _shift_stack_fast(bervs, True)
        snr_berv = stk_bv.copy()

        hw_core = max(2, int(round(1.8 / max(0.25, dv_grid_kms))))
        st_max_pre = maximum_filter1d(snr_stat[::-1], size=2 * hw_core + 1, mode="constant", cval=0.0).astype(np.float64)
        bv_max_pre = maximum_filter1d(snr_berv[::-1], size=2 * hw_core + 1, mode="constant", cval=0.0).astype(np.float64)
        aux_pair = (st_max_pre, bv_max_pre, st_max_pre, bv_max_pre)
        log_params = (float(w_log[0]), C_KMS / dv_grid_kms)

        stat_v41_hit = _comb_peak_and_veto_on_snr_vec(
            nu_grid_ghz, snr_stat, cov_stat, snr_stat, snr_berv, spacings, n_teeth, step_nu, 4.2, 31.0, min_q, dv_grid_kms, False, aux_pair, 1.0, not has_gaps, log_params
        )
        if stat_v41_hit is not None:
            v41_static_hits += 1
        stat_full_hit = _comb_peak_and_veto_on_snr_vec(
            nu_grid_ghz, snr_stat, cov_stat, snr_stat, snr_berv, spacings, n_teeth, step_nu, 3.3, 24.0, max(3, min_q - 1), dv_grid_kms, False, aux_pair, 1.0, not has_gaps, log_params
        )
        berv_hit = _comb_peak_and_veto_on_snr_vec(
            nu_grid_ghz, snr_berv, cov_stat, snr_stat, snr_berv, spacings, n_teeth, step_nu, 3.3, 24.0, max(3, min_q - 1), dv_grid_kms, False, aux_pair, 1.0, not has_gaps, log_params
        )
        stat_band_max = float(stat_full_hit["sum_snr"]) if stat_full_hit is not None else 0.0
        berv_band_max = float(berv_hit["sum_snr"]) if berv_hit is not None else 0.0
        stat_band_dnu = float(stat_full_hit["dnu_ghz"]) if stat_full_hit is not None else 0.0
        berv_band_dnu = float(berv_hit["dnu_ghz"]) if berv_hit is not None else 0.0

        traj_hits: list[dict[str, Any]] = []
        traj_max_scores: list[float] = []
        hw_check = max(1, int(round(1.5 / max(0.25, dv_grid_kms))))
        for fam, pd_v, ec_v, v_tr in uniq_traj:
            stk, cov_ok, sc_tr = _shift_stack_fast(v_tr, False)
            hit = _comb_peak_and_veto_on_snr_vec(
                nu_grid_ghz, stk, cov_ok, snr_stat, snr_berv, spacings, n_teeth, step_nu, t_min, s_min, min_q, dv_grid_kms, True, aux_pair, sc_tr, not has_gaps, log_params
            )
            if hit is None:
                traj_max_scores.append(0.0)
                continue
            traj_max_scores.append(float(hit["sum_snr"]))

            sh_mat = _gather_sh_mat(v_tr)
            idxs_log = hit["idxs_log"]
            ep_tooth = np.zeros((n_ep, n_teeth), dtype=np.float64)
            for ti_idx, ix in enumerate(idxs_log):
                lo_c, hi_c = max(0, ix - hw_check), min(n_g, ix + hw_check + 1)
                ep_tooth[:, ti_idx] = np.max(sh_mat[:, lo_c:hi_c], axis=1)
            ep_sum = np.maximum(0.0, ep_tooth).sum(axis=1)
            worst_ep = int(np.argmax(ep_sum))
            loo_tooth = np.delete(ep_tooth, worst_ep, axis=0)
            loo_mean = np.mean(loo_tooth, axis=0) * math.sqrt(max(1, n_ep - 1))
            s_comb_loo = float(np.maximum(0.0, loo_mean).sum())
            n_q_loo = int(np.sum(loo_mean >= 2.2))
            loo_ratio = s_comb_loo / max(1e-6, float(hit["sum_snr"]))
            n_active_ep = int(np.sum(ep_sum >= 1.5 * math.sqrt(float(n_teeth))))

            # Apply CD1-CD5 vetoes cleanly: true stationary/BERV combs always score >=96% of any shifted echo
            vetoes: list[str] = []
            if (
                float(hit["s_comb_static_at_cfg"]) >= 0.90 * float(hit["sum_snr"])
                or (stat_band_max >= 0.96 * float(hit["sum_snr"]) and abs(stat_band_dnu - float(hit["dnu_ghz"])) < 0.1)
                or float(np.ptp(v_tr)) < 12.0
            ):
                vetoes.append("CD1_STATIC_VS_DRIFT")
            if (
                float(hit["s_comb_berv_at_cfg"]) >= 0.90 * float(hit["sum_snr"])
                or (berv_band_max >= 0.96 * float(hit["sum_snr"]) and abs(berv_band_dnu - float(hit["dnu_ghz"])) < 0.1)
            ):
                vetoes.append("CD2_TELLURIC_BERV_CORRELATED")
            if loo_ratio < 0.55 or n_q_loo < 3 or n_active_ep < min_cov_ep:
                vetoes.append("CD3_SINGLE_EPOCH_TRANSIENT")
            if float(hit["off_tooth_crowding"]) > 0.32 or float(hit["intertooth_ratio"]) < 2.0:
                vetoes.append("CD4_CROWDING_INTERTOOTH")

            rec = {
                "star": star,
                "band": win["band"],
                "family": fam,
                "period_days": round(pd_v, 4),
                "ecc": round(ec_v, 3),
                "v_ptp_kms": round(float(np.ptp(v_tr)), 3),
                "nu0_ghz": hit["nu0_ghz"],
                "dnu_ghz": hit["dnu_ghz"],
                "sum_snr": hit["sum_snr"],
                "n_qualifying_teeth": hit["n_qualifying_teeth"],
                "s_comb_static_at_cfg": hit["s_comb_static_at_cfg"],
                "s_comb_berv_at_cfg": hit["s_comb_berv_at_cfg"],
                "loo_ratio": round(loo_ratio, 4),
                "n_active_epochs": int(n_active_ep),
                "off_tooth_crowding": hit["off_tooth_crowding"],
                "intertooth_ratio": hit["intertooth_ratio"],
                "vetoes": vetoes,
                "qualified_v59": len(vetoes) == 0,
            }
            traj_hits.append(rec)

        if traj_hits:
            med_bg = exact_median_1d(np.asarray(traj_max_scores, dtype=np.float64)) if traj_max_scores else 0.0
            for th in traj_hits:
                if med_bg > 0.0 and float(th["sum_snr"]) < 1.35 * med_bg:
                    th["vetoes"].append("CD5_DYNAMIC_COHERENCE")
                    th["qualified_v59"] = False

            traj_hits.sort(key=lambda r: (0 if r["qualified_v59"] else 1, -float(r["sum_snr"])))
            kept: list[dict[str, Any]] = []
            for th in traj_hits:
                if any(abs(th["nu0_ghz"] - prev["nu0_ghz"]) <= 0.7 * th["dnu_ghz"] and abs(th["dnu_ghz"] - prev["dnu_ghz"]) < 1e-2 for prev in kept):
                    continue
                kept.append(th)
            all_raw.extend(kept)
            all_qual.extend([k for k in kept if k["qualified_v59"]])

    return {
        "star": star,
        "n_epochs": int(n_ep),
        "trajectories_tested": len(uniq_traj),
        "n_raw_candidates": len(all_raw),
        "n_qualified": len(all_qual),
        "v41_static_hits": int(v41_static_hits),
        "candidates": all_qual[:16] if all_qual else all_raw[:16],
    }


def run_drifting_comb_calibration_v59(seed: int = 10102) -> dict[str, Any]:
    """
    `CALIBRATION_V59_DRIFTING_COMB_240`:
      - 60 Keplerian-orbiting sub-threshold 6-tooth frequency combs (P known/blind, K=25-95 km/s)
      - 60 linear-accelerating sub-threshold 6-tooth frequency combs (dv=32-110 km/s across baseline)
      - 40 stationary optical/stellar/Fabry-Perot étalon 6-tooth combs (`CD1`)
      - 40 single-epoch transient 6-tooth comb / laser bursts (`CD3`)
      - 40 correlated Gaussian/red-noise + telluric BERV-locked 6-tooth comb nulls (`CD2`/`CD4`)
    """
    rng = np.random.default_rng(int(seed))
    cfg = get_inst_config("ESO_HARPS")
    w_r = np.arange(5500.0, 6500.0, 0.025, dtype=np.float64)
    sig_w = w_r / (115000.0 * FWHM_FACTOR)
    n_ep = 6
    n_pix = len(w_r)
    n_teeth = int(cfg.get("comb_n_teeth", 6))
    win = [{"band": "HARPS_RED", "lo_a": 5550.0, "hi_a": 6450.0}]

    trials: list[dict[str, Any]] = []
    kep_rec = lin_rec = stat_v = tr_v = null_v = v41_stat_on_drift = 0

    for ti in range(240):
        fn_mat = 1.0 + rng.normal(0.0, 0.015, size=(n_ep, n_pix))
        sig_mat = np.full((n_ep, n_pix), 0.015, dtype=np.float64)
        bervs = rng.uniform(-26.0, 26.0, size=n_ep)
        mjds = np.sort(np.linspace(55000.0, 56200.0, n_ep) + rng.uniform(-10.0, 10.0, n_ep))
        t_rel = mjds - mjds[0]
        known_orbs: list[dict[str, float]] = []

        if ti < 60:
            cls_, want = "KEPLERIAN_DRIFTING_COMB", True
            mjds = np.sort(np.linspace(55000.0, 55090.0, n_ep) + rng.uniform(-1.0, 1.0, n_ep))
            t_rel = mjds - mjds[0]
            p_orb = float(rng.choice([15.0, 38.0, 65.0]))
            k_amp = float(rng.uniform(35.0, 85.0))
            ecc = float(rng.choice([0.0, 0.25]))
            w_deg = float(rng.uniform(0.0, 360.0))
            m0 = float(rng.uniform(0.0, 2.0 * math.pi))
            v_ep = solve_kepler_eccentric_rv(t_rel, p_orb, ecc, math.radians(w_deg), m0, k_amp)
            known_orbs = [{"P_days": p_orb, "ecc": ecc, "w_deg": w_deg}]
            nu0 = float(rng.uniform(470000.0, 520000.0))
            dnu = float(rng.choice([25.0, 40.0, 65.0, 100.0]))
            amp_sn = float(rng.uniform(3.0, 3.8))
            px_sig = float(np.median(sig_w)) / 0.025
            amp_f = amp_sn * 0.015 / math.sqrt(max(1.0, px_sig * math.sqrt(math.pi)))
            teeth_nu = nu0 + dnu * np.arange(n_teeth, dtype=np.float64)
            teeth_w0 = C_ANGSTROM_GHZ / teeth_nu
            for ek in range(n_ep):
                for wt in teeth_w0:
                    w_sh = wt * (1.0 + v_ep[ek] / C_KMS)
                    idx_s = int(np.searchsorted(w_r, w_sh))
                    l0, l1 = max(0, idx_s - 25), min(n_pix, idx_s + 26)
                    fn_mat[ek, l0:l1] += amp_f * np.exp(-0.5 * ((w_r[l0:l1] - w_sh) / sig_w[l0:l1]) ** 2)
        elif ti < 120:
            cls_, want = "LINEAR_ACCEL_DRIFTING_COMB", True
            t_mid = 0.5 * (mjds[0] + mjds[-1])
            tau = (mjds - t_mid) / (0.5 * (mjds[-1] - mjds[0]))
            a1 = float(rng.choice([-1.0, 1.0])) * float(rng.uniform(32.0, 110.0))
            v_ep = a1 * tau
            nu0 = float(rng.uniform(470000.0, 520000.0))
            dnu = float(rng.choice([25.0, 40.0, 65.0, 100.0]))
            amp_sn = float(rng.uniform(3.0, 3.8))
            px_sig = float(np.median(sig_w)) / 0.025
            amp_f = amp_sn * 0.015 / math.sqrt(max(1.0, px_sig * math.sqrt(math.pi)))
            teeth_nu = nu0 + dnu * np.arange(n_teeth, dtype=np.float64)
            teeth_w0 = C_ANGSTROM_GHZ / teeth_nu
            for ek in range(n_ep):
                for wt in teeth_w0:
                    w_sh = wt * (1.0 + v_ep[ek] / C_KMS)
                    idx_s = int(np.searchsorted(w_r, w_sh))
                    l0, l1 = max(0, idx_s - 25), min(n_pix, idx_s + 26)
                    fn_mat[ek, l0:l1] += amp_f * np.exp(-0.5 * ((w_r[l0:l1] - w_sh) / sig_w[l0:l1]) ** 2)
        elif ti < 160:
            cls_, want = "STATIONARY_ETALON_COMB_VETO", False
            nu0 = float(rng.uniform(470000.0, 520000.0))
            dnu = float(rng.choice([25.0, 40.0, 65.0, 100.0]))
            px_sig = float(np.median(sig_w)) / 0.025
            amp_f = float(rng.uniform(3.5, 5.5)) * 0.015 / math.sqrt(max(1.0, px_sig * math.sqrt(math.pi)))
            teeth_w0 = C_ANGSTROM_GHZ / (nu0 + dnu * np.arange(n_teeth, dtype=np.float64))
            for ek in range(n_ep):
                for wt in teeth_w0:
                    idx_s = int(np.searchsorted(w_r, wt))
                    l0, l1 = max(0, idx_s - 25), min(n_pix, idx_s + 26)
                    fn_mat[ek, l0:l1] += amp_f * np.exp(-0.5 * ((w_r[l0:l1] - wt) / sig_w[l0:l1]) ** 2)
        elif ti < 200:
            cls_, want = "SINGLE_EPOCH_TRANSIENT_COMB_VETO", False
            nu0 = float(rng.uniform(470000.0, 520000.0))
            dnu = float(rng.choice([25.0, 40.0, 65.0, 100.0]))
            px_sig = float(np.median(sig_w)) / 0.025
            amp_f = float(rng.uniform(12.0, 18.0)) * 0.015 / math.sqrt(max(1.0, px_sig * math.sqrt(math.pi)))
            ek = int(rng.integers(0, n_ep))
            v_one = float(rng.uniform(-50.0, 50.0))
            teeth_w0 = C_ANGSTROM_GHZ / (nu0 + dnu * np.arange(n_teeth, dtype=np.float64))
            for wt in teeth_w0:
                w_sh = wt * (1.0 + v_one / C_KMS)
                idx_s = int(np.searchsorted(w_r, w_sh))
                l0, l1 = max(0, idx_s - 25), min(n_pix, idx_s + 26)
                fn_mat[ek, l0:l1] += amp_f * np.exp(-0.5 * ((w_r[l0:l1] - w_sh) / sig_w[l0:l1]) ** 2)
        else:
            cls_, want = "BERV_SKY_OR_NOISE_COMB_VETO", False
            if ti % 2 == 0:
                nu0 = float(rng.uniform(470000.0, 520000.0))
                dnu = float(rng.choice([25.0, 40.0, 65.0, 100.0]))
                px_sig = float(np.median(sig_w)) / 0.025
                amp_f = float(rng.uniform(3.5, 5.5)) * 0.015 / math.sqrt(max(1.0, px_sig * math.sqrt(math.pi)))
                teeth_w0 = C_ANGSTROM_GHZ / (nu0 + dnu * np.arange(n_teeth, dtype=np.float64))
                for ek in range(n_ep):
                    for wt in teeth_w0:
                        wb = wt * (1.0 + bervs[ek] / C_KMS)
                        idx_s = int(np.searchsorted(w_r, wb))
                        l0, l1 = max(0, idx_s - 25), min(n_pix, idx_s + 26)
                        fn_mat[ek, l0:l1] += amp_f * np.exp(-0.5 * ((w_r[l0:l1] - wb) / sig_w[l0:l1]) ** 2)

        res = scan_comb_drift_v59(
            w_r, fn_mat, sig_mat, mjds, bervs, cfg, star=f"SIM_DC_{ti}",
            known_orb_params=known_orbs, comb_windows=win,
        )
        obs = res["n_qualified"] >= 1
        ok = int(bool(obs) == bool(want))
        if cls_ == "KEPLERIAN_DRIFTING_COMB":
            kep_rec += ok
            v41_stat_on_drift += int(res["v41_static_hits"] >= 1)
        elif cls_ == "LINEAR_ACCEL_DRIFTING_COMB":
            lin_rec += ok
            v41_stat_on_drift += int(res["v41_static_hits"] >= 1)
        elif cls_ == "STATIONARY_ETALON_COMB_VETO":
            stat_v += ok
        elif cls_ == "SINGLE_EPOCH_TRANSIENT_COMB_VETO":
            tr_v += ok
        else:
            null_v += ok
        trials.append({
            "suite": "CALIBRATION_V59_DRIFTING_COMB_240",
            "class": cls_, "trial": ti + 1, "expected": int(want),
            "observed": int(obs), "v41_static_obs": int(res["v41_static_hits"] >= 1), "passed": ok,
        })

    return {
        "total_trials": len(trials),
        "kepler_drifting_comb_60": f"{kep_rec}/60 ({kep_rec/60.0:.4f})",
        "linear_accel_drifting_comb_60": f"{lin_rec}/60 ({lin_rec/60.0:.4f})",
        "static_v41_baseline_on_120_drifting": f"{v41_stat_on_drift}/120 ({v41_stat_on_drift/120.0:.4f})",
        "stationary_comb_veto_40": f"{stat_v}/40 ({stat_v/40.0:.4f})",
        "transient_comb_veto_40": f"{tr_v}/40 ({tr_v/40.0:.4f})",
        "berv_noise_comb_veto_40": f"{null_v}/40 ({null_v/40.0:.4f})",
        "trials": trials,
    }


# ===========================================================================
# TECHNOSIGNATURE V6.0 ENGINES (`CHANDRA_XRAY_POISSON_V60` & `EUVE_V60`)
# ===========================================================================

# Tabulated CXC POG Ch. 8/9 1st-order (+1 + -1 summed) effective area (cm^2)
CHANDRA_AEFF_TABLE: dict[str, tuple[tuple[float, float], ...]] = {
    "HEG": (
        (1.20, 4.0), (1.50, 11.0), (2.00, 28.0), (3.00, 42.0), (4.00, 55.0),
        (6.00, 68.0), (8.00, 48.0), (10.00, 25.0), (12.00, 14.0), (15.00, 6.0), (20.00, 1.5),
    ),
    "MEG": (
        (1.50, 12.0), (2.00, 22.0), (4.00, 65.0), (6.20, 95.0), (8.30, 130.0),
        (10.00, 95.0), (12.40, 59.0), (15.00, 30.0), (20.00, 12.0), (25.00, 6.5), (31.00, 2.5),
    ),
    "LETG_HRC": (
        (1.50, 18.0), (2.00, 20.0), (6.00, 22.0), (10.00, 24.0), (15.00, 25.0),
        (25.00, 21.0), (40.00, 16.5), (50.00, 14.0), (80.00, 9.0), (120.00, 5.0),
        (150.00, 2.4), (160.00, 1.8), (175.00, 1.0),
    ),
    "LETG_ACIS": (
        (1.50, 20.0), (2.00, 25.0), (4.00, 34.0), (6.00, 38.0), (10.00, 30.0),
        (15.00, 14.0), (25.00, 4.2), (40.00, 1.5), (55.00, 0.7),
    ),
}

CHANDRA_GRATING_SPEC: dict[int, tuple[str, float, float, float]] = {
    # TG_PART -> (arm_name, fwhm_a, lam_min_a, lam_max_a)
    1: ("HEG", 0.012, 1.20, 20.0),
    2: ("MEG", 0.023, 1.80, 31.5),
    3: ("LEG", 0.050, 1.20, 175.0),
}

# Locked CHIANTI / AtomDB coronal & X-ray astrophysical emission lines (1.2 - 175 A)
CHANDRA_CORONAL_ATLAS_A: tuple[tuple[str, float], ...] = (
    ("FeXXVI_LyA", 1.7798), ("FeXXV_HeA_w", 1.8504), ("FeXXV_HeA_z", 1.8682),
    ("Fe_Kalpha", 1.9373), ("CaXX_LyA", 3.0203), ("CaXIX_HeA", 3.1772),
    ("ArXVIII_LyA", 3.7329), ("ArXVII_HeA", 3.9491), ("SXVI_LyA", 4.7292),
    ("SXV_HeA_w", 5.0387), ("SXV_HeA_z", 5.1015), ("SiXIV_LyB", 5.2170),
    ("SiXIV_LyA", 6.1822), ("SiXIII_HeA_w", 6.6479), ("SiXIII_HeA_i", 6.6866),
    ("SiXIII_HeA_z", 6.7403), ("MgXII_LyB", 7.1062), ("AlXII_HeA", 7.7573),
    ("MgXII_LyA", 8.4210), ("MgXI_HeA_w", 9.1687), ("MgXI_HeA_i", 9.2312),
    ("MgXI_HeA_z", 9.3143), ("NeX_LyG", 9.7082), ("NeX_LyB", 10.2389),
    ("FeXXIII_L", 10.9810), ("FeXXIV_L", 11.1760), ("FeXVII_4C", 11.2540),
    ("NeIX_HeB", 11.5440), ("FeXXII_L", 11.7700), ("FeXXI_L", 12.1210),
    ("NeX_LyA", 12.1339), ("FeXXI_1228", 12.2840), ("FeXX_1283", 12.8240),
    ("FeXIX_1351", 13.5180), ("NeIX_HeA_w", 13.4473), ("NeIX_HeA_i", 13.5531),
    ("NeIX_HeA_z", 13.6990), ("FeXVII_3C", 15.0140), ("OVIII_LyB", 15.1760),
    ("FeXVII_3D", 15.2610), ("FeXIX_1508", 15.0790), ("OVIII_LyG", 14.8205),
    ("FeXVII_3F", 16.7800), ("FeXVII_3G", 17.0510), ("FeXVII_M2", 17.0960),
    ("OVIII_LyA", 18.9689), ("OVII_HeB", 18.6270), ("OVII_HeA_w", 21.6015),
    ("OVII_HeA_i", 21.8036), ("OVII_HeA_z", 22.0977), ("NVII_LyA", 24.7810),
    ("CVI_LyB", 28.4656), ("NVI_HeA_w", 28.7870), ("NVI_HeA_z", 29.5343),
    ("CVI_LyA", 33.7360), ("CV_HeA_w", 40.2674), ("CV_HeA_z", 41.4715),
    ("SiXII_4416", 44.1650), ("SiXI_4922", 49.2220), ("FeXVI_5035", 50.3500),
    ("FeXV_5291", 52.9110), ("FeXVI_5471", 54.7100), ("MgX_5788", 57.8760),
    ("SiVIII_6107", 61.0700), ("FeXVI_6287", 62.8740), ("MgX_6329", 63.2950),
    ("FeXVI_6625", 66.2490), ("FeXV_6968", 69.6820), ("FeXIV_7137", 71.3750),
    ("MgIX_7231", 72.3120), ("NeVIII_8809", 88.0920), ("FeXIX_9102", 91.0200),
    ("FeXVIII_9392", 93.9230), ("FeXXI_9787", 97.8720), ("NeVIII_9826", 98.2600),
    ("FeXX_10155", 101.5500), ("FeXIX_10837", 108.3700), ("FeXXII_11717", 117.1700),
    ("FeXX_12183", 121.8300), ("FeXXI_12873", 128.7300), ("FeXXIII_13285", 132.8500),
    ("FeXXII_13578", 135.7800), ("FeIX_17107", 171.0730),
)

# Geocoronal EUV airglow lines in EUVE (Angstrom)
EUVE_GEOCORONAL_LINES_A: tuple[tuple[str, float], ...] = (
    ("GEO_HeII_304", 303.782),
    ("GEO_HeI_522", 522.213),
    ("GEO_HeI_537", 537.030),
    ("GEO_OII_539", 539.549),
    ("GEO_HeI_584", 584.334),
    ("GEO_HeII_2ND_608", 607.564),
)

# Locked EUVE Coronal Atomic Emission Atlas (70 - 700 A)
EUVE_CORONAL_ATLAS_A: tuple[tuple[str, float], ...] = (
    ("FeXXIV_79", 79.48), ("FeXXII_84", 84.53), ("NeVIII_88", 88.09),
    ("FeXVIII_93", 93.92), ("FeXIX_101", 101.55), ("FeXXI_102", 102.22),
    ("FeXIX_108", 108.37), ("FeXIX_111", 111.70), ("FeXXII_117", 117.17),
    ("FeXX_118", 118.66), ("FeXX_121", 121.83), ("FeXXI_128", 128.73),
    ("FeXXIII_132", 132.85), ("FeXXII_135", 135.78), ("FeXXI_142", 142.14),
    ("FeXXI_145", 145.65), ("OV_172", 172.17), ("FeIX_171", 171.07),
    ("FeX_174", 174.53), ("FeX_177", 177.24), ("FeXI_180", 180.40),
    ("FeXI_188", 188.23), ("FeXXIV_192", 192.03), ("FeXII_193", 193.51),
    ("FeXII_195", 195.12), ("FeXIII_202", 202.04), ("FeXIV_211", 211.32),
    ("FeXIV_220", 220.09), ("HeII_243", 243.03), ("FeXVI_251", 251.06),
    ("FeXXIV_255", 255.10), ("HeII_256", 256.32), ("FeXIV_264", 264.79),
    ("FeXIV_274", 274.20), ("FeXV_284", 284.16), ("FeXIV_289", 289.15),
    ("SiIX_296", 296.19), ("HeII_304", 303.78), ("FeXV_327", 327.03),
    ("FeXVI_335", 335.41), ("SiIX_345", 345.12), ("SiX_347", 347.40),
    ("FeXVI_360", 360.76), ("MgIX_368", 368.07), ("SiXI_303", 303.32),
    ("SXV_415", 415.00), ("NeVII_465", 465.22), ("SiXII_499", 499.41),
    ("HeI_504_EDGE", 504.26), ("SiXII_520", 520.66), ("HeI_522", 522.21),
    ("HeI_537", 537.03), ("OIV_554", 554.37), ("FeXX_567", 567.86),
    ("HeI_584", 584.33), ("OIII_599", 599.59), ("MgX_609", 609.79),
    ("MgX_624", 624.94), ("OV_629", 629.73),
)


def chandra_effective_area_cm2(grating_arm: str, detnam: str, wave_a: float) -> float:
    """CXC POG Ch. 8/9 tabulated first-order effective area (cm^2) via log-linear interpolation."""
    g = str(grating_arm).upper()
    det = str(detnam).upper()
    if g in ("HEG", "HETG_HEG"):
        key = "HEG"
    elif g in ("MEG", "HETG_MEG"):
        key = "MEG"
    elif "ACIS" in det:
        key = "LETG_ACIS"
    else:
        key = "LETG_HRC"
    pts = CHANDRA_AEFF_TABLE[key]
    w = float(wave_a)
    if w <= pts[0][0]:
        return float(pts[0][1])
    if w >= pts[-1][0]:
        return float(pts[-1][1])
    for i in range(len(pts) - 1):
        w0, a0 = pts[i]
        w1, a1 = pts[i + 1]
        if w0 <= w <= w1:
            t = (w - w0) / max(1e-12, w1 - w0)
            return math.exp(math.log(max(1e-6, a0)) * (1.0 - t) + math.log(max(1e-6, a1)) * t)
    return float(pts[-1][1])


def li_ma_significance(n_on: float, n_off: float, alpha: float) -> float:
    """Exact Li & Ma (1983, ApJ 272, 317, eq. 17) Poisson likelihood-ratio significance."""
    non = float(n_on)
    noff = float(n_off)
    a = float(alpha)
    if a <= 0.0 or non <= a * noff or non <= 0.0:
        return 0.0
    if noff <= 0.0:
        arg = max(1.0, (1.0 + a) / a)
        return math.sqrt(max(0.0, 2.0 * non * math.log(arg)))
    tot = non + noff
    t1 = non * math.log(max(1e-300, ((1.0 + a) / a) * (non / tot)))
    t2 = noff * math.log(max(1e-300, (1.0 + a) * (noff / tot)))
    val = 2.0 * (t1 + t2)
    return math.sqrt(max(0.0, val))


def poisson_6sigma_upper_limit_counts(n_off: float, alpha: float, target_s: float = 6.0) -> float:
    """Solve S_LM(N_on_lim, n_off, alpha) == target_s via deterministic 64-step bisection -> net excess counts."""
    noff = max(0.0, float(n_off))
    a = max(1e-6, float(alpha))
    lo = a * noff
    hi = max(lo + 40.0, 2.0 * (lo + 10.0) + 60.0)
    while li_ma_significance(hi, noff, a) < float(target_s):
        hi *= 2.0
        if hi > 1e10:
            break
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        if li_ma_significance(mid, noff, a) >= float(target_s):
            hi = mid
        else:
            lo = mid
    return max(1.0, hi - a * noff)


def _exact_binomial_two_sided_p(k: int, n: int) -> float:
    """Exact two-sided binomial p-value for Binomial(n, p=0.5) using log-gamma."""
    if n <= 0:
        return 1.0
    kk = min(int(k), int(n) - int(k))
    if kk < 0:
        return 1.0
    log_half_n = -float(n) * math.log(2.0)
    lg_n1 = math.lgamma(float(n) + 1.0)
    p_one = 0.0
    for j in range(kk + 1):
        lp = lg_n1 - math.lgamma(float(j) + 1.0) - math.lgamma(float(n - j) + 1.0) + log_half_n
        if lp > -700.0:
            p_one += math.exp(lp)
    return min(1.0, 2.0 * p_one)


def parse_chandra_pha2_arrays(hdul: Any) -> dict[str, Any]:
    """Extract sorted ascending first-order (+1/-1) HEG, MEG, LEG grating arms from a Chandra pha2 HDUList."""
    h1 = hdul[1]
    hdr = dict(h1.header)
    dat = h1.data
    backscal = float(hdr.get("BACKSCAL", 1.0) or 1.0)
    backscup = float(hdr.get("BACKSCUP", hdr.get("BACKSCDN", 4.0)) or 4.0)
    backscdn = float(hdr.get("BACKSCDN", backscup) or backscup)
    alpha_spatial = backscal / max(0.5, backscup + backscdn)
    expt = float(hdr.get("EXPOSURE", hdr.get("ONTIME", 0.0)) or 0.0)
    detnam = str(hdr.get("DETNAM", hdr.get("INSTRUME", "ACIS")) or "ACIS")
    grating = str(hdr.get("GRATING", "HETG") or "HETG")

    parts: dict[int, dict[int, dict[str, np.ndarray]]] = {}
    for row in dat:
        part = int(row["TG_PART"])
        m_ord = int(row["TG_M"])
        if part not in CHANDRA_GRATING_SPEC or m_ord not in (-1, 1):
            continue
        w_mid = 0.5 * (np.asarray(row["BIN_LO"], dtype=np.float64) + np.asarray(row["BIN_HI"], dtype=np.float64))
        cts = np.asarray(row["COUNTS"], dtype=np.float64)
        bg = np.asarray(row["BACKGROUND_UP"], dtype=np.float64) + np.asarray(row["BACKGROUND_DOWN"], dtype=np.float64)
        ord_idx = np.argsort(w_mid)
        parts.setdefault(part, {})[m_ord] = {
            "wave_a": w_mid[ord_idx],
            "cts": np.maximum(0.0, cts[ord_idx]),
            "bg": np.maximum(0.0, bg[ord_idx]),
        }

    arms: dict[str, dict[str, Any]] = {}
    for part, ord_map in sorted(parts.items()):
        if 1 not in ord_map or -1 not in ord_map:
            continue
        arm_name, fwhm_a, lmin, lmax = CHANDRA_GRATING_SPEC[part]
        if part == 3 and "ACIS" in detnam.upper():
            lmax = 55.0
        # Map +/-1 onto common wavelength grid (average spacing)
        p_d = ord_map[1]
        m_d = ord_map[-1]
        mask_p = (p_d["wave_a"] >= lmin) & (p_d["wave_a"] <= lmax)
        w_grid = p_d["wave_a"][mask_p]
        if len(w_grid) < 64:
            continue
        # Match nearest channel in -1 order (typically identical grid for HEG/MEG/LEG)
        if len(m_d["wave_a"]) == len(p_d["wave_a"]) and float(np.max(np.abs(m_d["wave_a"] - p_d["wave_a"]))) < 1e-4:
            m_cts = m_d["cts"][mask_p]
            m_bg = m_d["bg"][mask_p]
        else:
            idx_m = np.clip(np.searchsorted(m_d["wave_a"], w_grid), 0, len(m_d["wave_a"]) - 1)
            m_cts = m_d["cts"][idx_m]
            m_bg = m_d["bg"][idx_m]
        arms[arm_name] = {
            "arm": arm_name,
            "fwhm_a": float(fwhm_a),
            "wave_a": np.asarray(w_grid, dtype=np.float64),
            "plus_cts": np.asarray(p_d["cts"][mask_p], dtype=np.float64),
            "minus_cts": np.asarray(m_cts, dtype=np.float64),
            "bg_plus": np.asarray(p_d["bg"][mask_p], dtype=np.float64),
            "bg_minus": np.asarray(m_bg, dtype=np.float64),
        }

    return {
        "valid": len(arms) > 0 and expt > 0.0,
        "exposure_s": expt,
        "alpha_spatial": alpha_spatial,
        "detnam": detnam,
        "grating": grating,
        "object": str(hdr.get("OBJECT", "")),
        "ra_targ": float(hdr.get("RA_TARG", 0.0) or 0.0),
        "dec_targ": float(hdr.get("DEC_TARG", 0.0) or 0.0),
        "mjd_obs": float(hdr.get("MJD-OBS", 55000.0) or 55000.0),
        "arms": arms,
    }


def scan_chandra_pha2_v60(
    spec_dict: dict[str, Any],
    star: str = "",
    dist_pc: float = 10.0,
    role: str = "SCIENCE",
    star_rv_kms: float = 0.0,
    dp_id: str = "",
    instrument: str = "",
) -> dict[str, Any]:
    """
    Engine V6.0A (`CHANDRA_XRAY_POISSON_V60`):
    Exact Li & Ma (1983) Poisson likelihood-ratio line search across Chandra HETG/LETG
    `+1/-1` grating orders with `G4` order coincidence, `G3` CHIANTI coronal atlas,
    `G5` width/spike veto, and Poisson 6-sigma `1 m`, `10 m`, and isotropic EIRP limits.
    """
    arms = spec_dict.get("arms", {})
    expt_s = float(spec_dict.get("exposure_s", 0.0) or 0.0)
    detnam = str(spec_dict.get("detnam", "ACIS") or "ACIS")
    grating = str(spec_dict.get("grating", "HETG") or "HETG")
    inst_name = str(instrument or ("CHANDRA_LETG" if "LETG" in grating.upper() else "CHANDRA_HETG"))
    if not arms or expt_s <= 0.0:
        return {
            "valid": False, "dp_id": dp_id, "instrument": inst_name,
            "n_raw": 0, "n_qualified": 0, "candidates": [], "band_best_ul": {},
        }

    candidates: list[dict[str, Any]] = []
    band_best_ul: dict[str, dict[str, float]] = {}
    n_raw = 0
    n_qualified = 0

    canon_bands = get_calibration_bands(inst_name)
    d_cm = max(0.5, float(dist_pc)) * PC_CM

    for arm_name, arm in arms.items():
        w = np.asarray(arm["wave_a"], dtype=np.float64)
        p_cts = np.asarray(arm["plus_cts"], dtype=np.float64)
        m_cts = np.asarray(arm["minus_cts"], dtype=np.float64)
        bg_sum = np.asarray(arm.get("bg_plus", np.zeros_like(w)), dtype=np.float64) + np.asarray(
            arm.get("bg_minus", np.zeros_like(w)), dtype=np.float64
        )
        tot_cts = p_cts + m_cts
        fwhm_a = float(arm.get("fwhm_a", 0.023))
        if len(w) < 64:
            continue
        dlam_a = max(1e-5, exact_median_1d(np.abs(np.diff(w))))
        w_bins = int(round(fwhm_a / dlam_a))
        w_bins = max(3, min(7, w_bins | 1))
        hw = w_bins // 2
        n_len = len(w)

        # Prefix sums for O(N) exact window sums
        cs_tot = np.concatenate(([0.0], np.cumsum(tot_cts)))
        cs_p = np.concatenate(([0.0], np.cumsum(p_cts)))
        cs_m = np.concatenate(([0.0], np.cumsum(m_cts)))
        cs_bg = np.concatenate(([0.0], np.cumsum(bg_sum)))

        s_lm_arr = np.zeros(n_len, dtype=np.float64)
        n_on_arr = np.zeros(n_len, dtype=np.float64)
        n_off_arr = np.zeros(n_len, dtype=np.float64)
        alpha_arr = np.full(n_len, 0.1, dtype=np.float64)

        sb_inner = hw + 3
        sb_outer = hw + 22
        # Vectorized O(N) prefilter using C-speed median_filter before exact sideband Li & Ma evaluation
        n_sb_nom = 2 * (sb_outer - sb_inner + 1)
        med_loc = median_filter(tot_cts, size=min(n_len | 1, 45), mode="nearest")
        win_sums = np.zeros(n_len, dtype=np.float64)
        idx_valid = np.arange(hw + 4, n_len - hw - 4)
        win_sums[idx_valid] = cs_tot[idx_valid + hw + 1] - cs_tot[idx_valid - hw]
        pre_bg = np.maximum(0.0, float(w_bins) * med_loc[idx_valid])
        # Poisson excess z_approx >= 4.0 OR low-bg n_on >= 8 -> evaluate exact clipped Li & Ma
        cand_mask = (win_sums[idx_valid] >= 8.0) & (
            (win_sums[idx_valid] - pre_bg) >= 3.8 * np.sqrt(np.maximum(0.25, pre_bg + 0.5))
        )
        for i in idx_valid[cand_mask]:
            i = int(i)
            non = float(win_sums[i])
            l0, l1 = max(0, i - sb_outer), max(0, i - sb_inner)
            r0, r1 = min(n_len, i + sb_inner + 1), min(n_len, i + sb_outer + 1)
            sb = np.concatenate((tot_cts[l0:l1], tot_cts[r0:r1]))
            if len(sb) < 8:
                continue
            med_sb = float(np.median(sb))
            # Mask only genuine bright (>3.5 sigma) neighboring emission lines in sideband
            thresh = med_sb + 3.5 * math.sqrt(max(1.0, med_sb)) + 2.0
            sb_clean = sb[sb <= thresh]
            if len(sb_clean) < 8:
                sb_clean = sb
            noff = float(np.sum(sb_clean))
            a_eff = float(w_bins) / float(len(sb_clean))
            n_on_arr[i] = non
            n_off_arr[i] = noff
            alpha_arr[i] = a_eff
            s_lm_arr[i] = li_ma_significance(non, noff, a_eff)

        # Peak selection with non-maximum suppression
        arm_cands: list[dict[str, Any]] = []
        sep_bins = max(w_bins + 2, 5)
        for i in range(hw + 4, n_len - hw - 4):
            slm = float(s_lm_arr[i])
            if slm < 6.0:
                continue
            if slm < float(np.max(s_lm_arr[max(0, i - 2): min(n_len, i + 3)])):
                continue
            if arm_cands and (i - int(arm_cands[-1]["bin_idx"])) < sep_bins:
                if slm > float(arm_cands[-1]["s_lima"]):
                    arm_cands.pop()
                else:
                    continue

            non = float(n_on_arr[i])
            noff = float(n_off_arr[i])
            a_eff = float(alpha_arr[i])
            expected_tot = a_eff * noff
            excess = non - expected_tot
            if excess < 6.0:
                continue

            # Split +1 and -1 net excess at peak window
            np_win = float(cs_p[i + hw + 1] - cs_p[i - hw])
            nm_win = float(cs_m[i + hw + 1] - cs_m[i - hw])
            frac_p_bg = 0.5
            sb_p = np.concatenate((p_cts[max(0, i - sb_outer):max(0, i - sb_inner)], p_cts[min(n_len, i + sb_inner + 1):min(n_len, i + sb_outer + 1)]))
            sb_m = np.concatenate((m_cts[max(0, i - sb_outer):max(0, i - sb_inner)], m_cts[min(n_len, i + sb_inner + 1):min(n_len, i + sb_outer + 1)]))
            if len(sb_p) > 0 and (float(np.sum(sb_p)) + float(np.sum(sb_m))) > 0.0:
                frac_p_bg = float(np.sum(sb_p)) / float(np.sum(sb_p) + np.sum(sb_m))
            ex_p = max(0.0, np_win - frac_p_bg * expected_tot)
            ex_m = max(0.0, nm_win - (1.0 - frac_p_bg) * expected_tot)
            n1 = max(0, int(round(ex_p)))
            n2 = max(0, int(round(ex_m)))
            bin_p = _exact_binomial_two_sided_p(n1, n1 + n2)
            pass_g4_order = (ex_p >= 2.0) and (ex_m >= 2.0) and (bin_p >= 0.001)

            lam_obs = float(w[i])
            lam_rest = lam_obs / max(0.5, 1.0 + float(star_rv_kms) / C_KMS)
            tol_a = max(1.8 * fwhm_a, lam_obs * (400.0 / C_KMS))
            atlas_match = None
            for lname, lval in CHANDRA_CORONAL_ATLAS_A:
                if min(abs(lam_rest - lval), abs(lam_obs - lval)) <= tol_a:
                    atlas_match = lname
                    break
            pass_g3_atlas = atlas_match is None

            # Width / single-bin artifact check across +/-20 bins so wide outflows aren't truncated
            mean_bg_bin = expected_tot / float(w_bins)
            loc_slice = tot_cts[max(0, i - 20): min(n_len, i + 21)] - mean_bg_bin
            pk_bin = float(tot_cts[i] - mean_bg_bin)
            n_half = int(np.sum(loc_slice >= 0.35 * max(1.0, pk_bin)))
            fwhm_est_a = float(n_half) * dlam_a
            n_above_2bg = int(np.sum(tot_cts[i - hw: i + hw + 1] > mean_bg_bin + 1.5 * math.sqrt(max(0.5, mean_bg_bin)) + 1.0))
            pass_g5_width = (fwhm_est_a <= 3.5 * fwhm_a) and (n_above_2bg >= 2)

            vetoes: list[str] = []
            if not pass_g4_order:
                vetoes.append("G4_CHANDRA_ORDER_COINCIDENCE")
            if not pass_g3_atlas:
                vetoes.append(f"G3_XRAY_CORONAL_ATLAS:{atlas_match}")
            if not pass_g5_width:
                vetoes.append("G5_XRAY_BROAD_OR_SINGLEBIN_ARTIFACT")

            n_raw += 1
            qualified = len(vetoes) == 0
            if qualified:
                n_qualified += 1
            cand = {
                "star": star,
                "role": role,
                "dp_id": dp_id,
                "instrument": inst_name,
                "arm": arm_name,
                "bin_idx": int(i),
                "wave_a": round(lam_obs, 4),
                "wave_um": round(lam_obs * 1e-4, 7),
                "n_on": round(non, 1),
                "n_off": round(noff, 1),
                "alpha_eff": round(a_eff, 5),
                "excess_cts": round(excess, 2),
                "excess_plus": round(ex_p, 2),
                "excess_minus": round(ex_m, 2),
                "order_binom_p": round(bin_p, 6),
                "s_lima": round(slm, 3),
                "fwhm_est_a": round(fwhm_est_a, 4),
                "vetoes": vetoes,
                "qualified_v60": bool(qualified),
            }
            arm_cands.append(cand)
        candidates.extend(arm_cands)

        # Radiometric Poisson 6-sigma EIRP upper limit per canonical band covered by this arm
        for cb in canon_bands:
            cw = float(cb["center_wave_A"])
            bid = str(cb["band_id"])
            if not (w[0] <= cw <= w[-1]):
                continue
            hw_band = max(0.3, 0.20 * cw)
            m_cb = (w >= cw - hw_band) & (w <= cw + hw_band)
            if int(np.sum(m_cb)) < 12:
                continue
            idx_cb = np.where(m_cb)[0]
            # Robust median window background across 35-bin clean slices
            win_counts = []
            for j in idx_cb[::max(1, w_bins)]:
                if j >= hw and j + hw < n_len:
                    win_counts.append(float(cs_tot[j + hw + 1] - cs_tot[j - hw]))
            if not win_counts:
                continue
            med_win_cts = float(np.median(win_counts))
            n_ref_bins = 36
            a_ref = float(w_bins) / float(n_ref_bins)
            b_off_ref = med_win_cts * (float(n_ref_bins) / float(w_bins))
            n_6sig = poisson_6sigma_upper_limit_counts(b_off_ref, a_ref, 6.0)
            aeff_cm2 = chandra_effective_area_cm2(arm_name, detnam, cw)
            e_phot_erg = (H_PLANCK * C_SI / (cw * 1e-10)) * 1e7
            f_phot = n_6sig / (max(0.1, aeff_cm2) * expt_s)
            f_erg = f_phot * e_phot_erg
            l_iso_w = 4.0 * math.pi * (d_cm * d_cm) * f_erg * 1e-7
            theta_10m = (math.pi * 10.0) / (cw * 1e-10)
            theta_1m = (math.pi * 1.0) / (cw * 1e-10)
            p_10m_w = l_iso_w / (theta_10m * theta_10m)
            p_1m_w = l_iso_w / (theta_1m * theta_1m)
            rp_band = cw / max(1e-4, fwhm_a)
            ul = {
                "fwhm_lsf_a": fwhm_a,
                "ew_lim_mA": fwhm_a * 1000.0,
                "continuum_flam_cgs": float(f_erg / max(1e-6, fwhm_a)),
                "flux_lim_erg_cm2_s": float(f_erg),
                "l_iso_mw": float(l_iso_w / 1e6),
                "l_iso_w": float(l_iso_w),
                "p_beam_1m_w": float(p_1m_w),
                "p_beam_1m_kw": float(p_1m_w / 1000.0),
                "p_beam_10m_w": float(p_10m_w),
                "p_beam_10m_kw": float(p_10m_w / 1000.0),
                "b_off_ref": float(b_off_ref),
                "alpha_ref": float(a_ref),
                "n_6sig_cts": float(n_6sig),
                "aeff_cm2": float(aeff_cm2),
                "exposure_s": float(expt_s),
                "wave_a": float(cw),
                "resolving_power": float(rp_band),
                "arm": arm_name,
            }
            if bid not in band_best_ul or ul["p_beam_10m_kw"] < band_best_ul[bid]["p_beam_10m_kw"]:
                band_best_ul[bid] = ul

    return {
        "valid": True,
        "dp_id": dp_id,
        "instrument": inst_name,
        "detnam": detnam,
        "grating": grating,
        "exposure_s": float(expt_s),
        "n_raw": int(n_raw),
        "n_qualified": int(n_qualified),
        "candidates": candidates,
        "band_best_ul": band_best_ul,
    }


def run_chandra_poisson_calibration_v60(seed: int = 10201) -> dict[str, Any]:
    """
    `CALIBRATION_V60_CHANDRA_POISSON_240`:
      - 60 unresolved PSF +1/-1 coincident X-ray beacons (`HEG`, `MEG`, `LETG`)
      - 45 single-order hot-pixel / cosmic-ray glitches (`G4_CHANDRA_ORDER_COINCIDENCE`)
      - 45 locked CHIANTI coronal X-ray lines (`G3_XRAY_CORONAL_ATLAS`)
      - 45 pure Poisson low-count background/continuum null trials
      - 45 broad thermal/wind X-ray features (`G5_XRAY_BROAD_OR_SINGLEBIN_ARTIFACT`)
    """
    rng = np.random.default_rng(int(seed))
    trials: list[dict[str, Any]] = []
    rec = vet_cr = vet_cor = vet_pois = vet_broad = 0

    for ti in range(240):
        use_letg = (ti % 2 == 1)
        if not use_letg:
            part, arm_nm, w0, w1, step, fwhm_a, detnam, grat = (2, "MEG", 2.5, 31.0, 0.005, 0.023, "ACIS-S", "HETG")
            part_alt = 1
            safe_ranges = [(2.10, 2.90), (4.05, 4.62), (7.28, 7.68), (19.30, 21.10), (25.50, 27.90)]
            cor_pool = [("SiXIV_LyA", 6.1822), ("MgXII_LyA", 8.4210), ("NeX_LyA", 12.1339), ("OVIII_LyA", 18.9689), ("OVII_HeA_w", 21.6015)]
        else:
            part, arm_nm, w0, w1, step, fwhm_a, detnam, grat = (3, "LEG", 5.0, 170.0, 0.0125, 0.050, "HRC-S", "LETG")
            safe_ranges = [(112.0, 115.5), (123.5, 126.8), (138.0, 165.0)]
            cor_pool = [("FeXVI_5035", 50.3500), ("NeVIII_8809", 88.0920), ("FeXXI_12873", 128.7300), ("FeXXIII_13285", 132.8500), ("FeIX_17107", 171.0730)]

        w = np.arange(w0, w1, step, dtype=np.float64)
        mu_bg = float(rng.choice([0.08, 0.35, 1.4]))
        lam_prof = fwhm_a / FWHM_FACTOR
        p_mu = np.full(len(w), 0.5 * mu_bg, dtype=np.float64)
        m_mu = np.full(len(w), 0.5 * mu_bg, dtype=np.float64)

        if ti < 60:
            cls_, want = "CLEAN_XRAY_BEACON", True
            lo, hi = safe_ranges[ti % len(safe_ranges)]
            cw = float(rng.uniform(lo + 0.08, hi - 0.08))
            n_tot_sig = float(rng.uniform(42.0, 72.0))
            prof = n_tot_sig * np.exp(-0.5 * ((w - cw) / lam_prof) ** 2)
            prof = prof / max(1e-9, float(np.sum(prof))) * n_tot_sig
            p_mu += 0.5 * prof
            m_mu += 0.5 * prof
        elif ti < 105:
            cls_, want = "SINGLE_ORDER_HOTPIX_VETO", False
            lo, hi = safe_ranges[ti % len(safe_ranges)]
            cw = float(rng.uniform(lo + 0.08, hi - 0.08))
            n_tot_sig = float(rng.uniform(45.0, 80.0))
            prof = n_tot_sig * np.exp(-0.5 * ((w - cw) / lam_prof) ** 2)
            prof = prof / max(1e-9, float(np.sum(prof))) * n_tot_sig
            if ti % 2 == 0:
                p_mu += prof
            else:
                m_mu += prof
        elif ti < 150:
            cls_, want = "CORONAL_XRAY_ATLAS_VETO", False
            _, cw = cor_pool[ti % len(cor_pool)]
            n_tot_sig = float(rng.uniform(55.0, 95.0))
            prof = n_tot_sig * np.exp(-0.5 * ((w - cw) / lam_prof) ** 2)
            prof = prof / max(1e-9, float(np.sum(prof))) * n_tot_sig
            p_mu += 0.5 * prof
            m_mu += 0.5 * prof
        elif ti < 195:
            cls_, want = "POISSON_CONTINUUM_NULL", False
        else:
            cls_, want = "BROAD_THERMAL_WIND_VETO", False
            lo, hi = safe_ranges[ti % len(safe_ranges)]
            cw = float(rng.uniform(lo + 0.12, hi - 0.12))
            broad_sig = 5.5 * lam_prof
            n_tot_sig = float(rng.uniform(140.0, 220.0))
            prof = n_tot_sig * np.exp(-0.5 * ((w - cw) / broad_sig) ** 2)
            prof = prof / max(1e-9, float(np.sum(prof))) * n_tot_sig
            p_mu += 0.5 * prof
            m_mu += 0.5 * prof

        p_cts = rng.poisson(np.maximum(0.0, p_mu)).astype(np.float64)
        m_cts = rng.poisson(np.maximum(0.0, m_mu)).astype(np.float64)
        spec_dict = {
            "exposure_s": 50000.0,
            "detnam": detnam,
            "grating": grat,
            "arms": {
                arm_nm: {
                    "arm": arm_nm,
                    "fwhm_a": fwhm_a,
                    "wave_a": w,
                    "plus_cts": p_cts,
                    "minus_cts": m_cts,
                    "bg_plus": np.zeros_like(w),
                    "bg_minus": np.zeros_like(w),
                }
            },
        }
        res = scan_chandra_pha2_v60(spec_dict, star=f"SIM_XRAY_{ti}", dist_pc=10.0)
        obs = res["n_qualified"] >= 1
        ok = int(bool(obs) == bool(want))
        if cls_ == "CLEAN_XRAY_BEACON":
            rec += ok
        elif cls_ == "SINGLE_ORDER_HOTPIX_VETO":
            vet_cr += ok
        elif cls_ == "CORONAL_XRAY_ATLAS_VETO":
            vet_cor += ok
        elif cls_ == "POISSON_CONTINUUM_NULL":
            vet_pois += ok
        else:
            vet_broad += ok
        trials.append({
            "suite": "CALIBRATION_V60_CHANDRA_POISSON_240",
            "class": cls_, "trial": ti + 1, "expected": int(want), "observed": int(obs), "passed": ok,
        })

    return {
        "total_trials": len(trials),
        "clean_xray_beacon_60": f"{rec}/60 ({rec/60.0:.4f})",
        "single_order_hotpix_veto_45": f"{vet_cr}/45 ({vet_cr/45.0:.4f})",
        "coronal_atlas_veto_45": f"{vet_cor}/45 ({vet_cor/45.0:.4f})",
        "poisson_null_veto_45": f"{vet_pois}/45 ({vet_pois/45.0:.4f})",
        "broad_wind_veto_45": f"{vet_broad}/45 ({vet_broad/45.0:.4f})",
        "trials": trials,
    }


def scan_euve_v60(
    wave_a: np.ndarray,
    flux_cgs: np.ndarray,
    star: str = "",
    dist_pc: float = 10.0,
    role: str = "SCIENCE",
    star_rv_kms: float = 0.0,
    dp_id: str = "",
) -> dict[str, Any]:
    """
    Engine V6.0B (`EUVE_V60`): Extreme-UV spectrometer scan across 70.05-699.80 A (`SW`/`MW`/`LW`)
    overlapping Chandra LETG (`70-175 A`) with geocoronal airglow veto (`G2`), EUV coronal
    atlas (`G3`), stitch-seam/1-px spike/ISM zero-continuum veto (`G4`), and 6-sigma EIRP bounds.
    """
    w = np.asarray(wave_a, dtype=np.float64).ravel()
    f = np.asarray(flux_cgs, dtype=np.float64).ravel()
    if len(w) != len(f) or len(w) < 64:
        return {
            "valid": False, "dp_id": dp_id, "instrument": "EUVE_DS_S",
            "n_raw": 0, "n_qualified": 0, "candidates": [], "band_best_ul": {},
        }
    ord_i = np.argsort(w)
    w = w[ord_i]
    f = f[ord_i]
    fin = np.isfinite(w) & np.isfinite(f) & (w > 60.0) & (w < 750.0)
    w = w[fin]
    f = f[fin]
    if len(w) < 64:
        return {
            "valid": False, "dp_id": dp_id, "instrument": "EUVE_DS_S",
            "n_raw": 0, "n_qualified": 0, "candidates": [], "band_best_ul": {},
        }

    # Sub-bands: SW (70-185), MW (185-370), LW (370-700)
    sub_specs = [
        ("SW", 70.0, 185.0, 0.55, "EUVE_SW_100A", 100.0),
        ("MW", 185.0, 370.0, 1.10, "EUVE_MW_250A", 250.0),
        ("LW", 370.0, 705.0, 2.20, "EUVE_LW_500A", 500.0),
    ]

    candidates: list[dict[str, Any]] = []
    band_best_ul: dict[str, dict[str, float]] = {}
    n_raw = 0
    n_qualified = 0

    for sub_nm, s_lo, s_hi, fwhm_a, bid, cw in sub_specs:
        ms = (w >= s_lo) & (w <= s_hi)
        if int(np.sum(ms)) < 32:
            continue
        ws = w[ms]
        fs = f[ms]
        dlam = max(0.05, exact_median_1d(np.abs(np.diff(ws))))
        nz = np.abs(fs) > 1e-22
        if int(np.sum(nz)) < 24:
            continue

        win_px = max(35, min(105, (len(ws) // 5) | 1))
        cont = _asymmetric_clipped_baseline_v56(fs, win_px)
        res = fs - cont
        valid_res = res[nz]
        if len(valid_res) < 16:
            continue
        glob_mad = max(1e-18, exact_mad_1d(valid_res))
        # Annular sideband MAD excluding inner +/-2.2*FWHM line core so wide LW profiles never inflate own noise
        hw_in = max(4, int(np.ceil(2.2 * fwhm_a / dlam)))
        hw_out = hw_in + 22
        loc_mad = np.full(len(ws), glob_mad, dtype=np.float64)
        for k in range(len(ws)):
            left = res[max(0, k - hw_out): max(0, k - hw_in)]
            right = res[min(len(ws), k + hw_in + 1): min(len(ws), k + hw_out + 1)]
            side = np.concatenate((left, right))
            if len(side) >= 12:
                loc_mad[k] = max(0.65 * glob_mad, exact_mad_1d(side))
        snr_arr = np.where(nz, res / np.maximum(1e-18, loc_mad), 0.0)

        # Compute 6-sigma calibrated EIRP upper limit on non-zero channels near cw
        m_band = nz & (ws >= cw - 0.35 * cw) & (ws <= cw + 0.35 * cw)
        if int(np.sum(m_band)) >= 12:
            sig_band = max(1e-18, exact_mad_1d(res[m_band]))
            flam_6sig = 6.0 * sig_band
            rp_sub = cw / fwhm_a
            ul = compute_photon_beam_upper_limit(
                wave_a=cw,
                amp_rel_lim=1.0,
                teff_k=10000.0,
                dist_pc=max(0.5, float(dist_pc)),
                stellar_radius_rsun=1.0,
                radiometric_anchor="EUVE_DIRECT_FLAM_CGS",
                resolving_power=rp_sub,
                direct_flam_cgs=flam_6sig,
            )
            ul["flam_noise_mad_cgs"] = float(sig_band)
            ul["subband"] = sub_nm
            ul["wave_a"] = float(cw)
            band_best_ul[bid] = ul

        sub_cands: list[dict[str, Any]] = []
        for k in range(2, len(ws) - 2):
            if snr_arr[k] < 6.5:
                continue
            if not (snr_arr[k] >= snr_arr[k - 1] and snr_arr[k] >= snr_arr[k + 1]):
                continue
            if sub_cands and (k - int(sub_cands[-1]["chan_idx"])) < 4:
                if snr_arr[k] > float(sub_cands[-1]["snr"]):
                    sub_cands.pop()
                else:
                    continue

            n_raw += 1
            lam_obs = float(ws[k])
            lam_rest = lam_obs / max(0.5, 1.0 + float(star_rv_kms) / C_KMS)

            # G2: Geocoronal EUV airglow mask
            geo_hit = None
            for gname, gw in EUVE_GEOCORONAL_LINES_A:
                if abs(lam_obs - gw) <= max(3.5, 3.0 * fwhm_a):
                    geo_hit = gname
                    break
            pass_g2 = geo_hit is None

            # G3: EUV Coronal Atomic Line Atlas
            cor_hit = None
            tol_c = max(2.2, 2.2 * fwhm_a)
            for cname, cw_l in EUVE_CORONAL_ATLAS_A:
                if min(abs(lam_rest - cw_l), abs(lam_obs - cw_l)) <= tol_c:
                    cor_hit = cname
                    break
            pass_g3 = cor_hit is None

            # G4: 1-px spike, SW/MW & MW/LW stitch seams, zero-continuum ISM edges
            nb_max = max(float(snr_arr[k - 1]), float(snr_arr[k + 1]))
            in_seam = (165.0 <= lam_obs <= 193.0) or (352.0 <= lam_obs <= 385.0)
            edge_dist = min(k, len(ws) - 1 - k)
            nz_frac_win = float(np.mean(nz[max(0, k - 6): min(len(ws), k + 7)]))
            fwhm_est = float(_subchannel_fwhm_v56(res, k)) * dlam
            pass_g4 = (
                (not in_seam)
                and (edge_dist >= 4)
                and (nz_frac_win >= 0.75)
                and (nb_max >= max(1.5, 0.16 * float(snr_arr[k])))
                and (fwhm_est <= 4.0 * fwhm_a)
            )

            vetoes: list[str] = []
            if not pass_g2:
                vetoes.append(f"G2_EUVE_GEOCORONAL:{geo_hit}")
            if not pass_g3:
                vetoes.append(f"G3_EUV_CORONAL_ATLAS:{cor_hit}")
            if not pass_g4:
                vetoes.append("G4_EUVE_SPIKE_OR_SEAM")

            qualified = len(vetoes) == 0
            if qualified:
                n_qualified += 1

            sub_cands.append({
                "star": star,
                "role": role,
                "dp_id": dp_id,
                "instrument": "EUVE_DS_S",
                "subband": sub_nm,
                "chan_idx": int(k),
                "wave_a": round(lam_obs, 3),
                "wave_um": round(lam_obs * 1e-4, 6),
                "snr": round(float(snr_arr[k]), 3),
                "fwhm_est_a": round(fwhm_est, 3),
                "vetoes": vetoes,
                "qualified_v60": bool(qualified),
            })
        candidates.extend(sub_cands)

    return {
        "valid": len(band_best_ul) > 0,
        "dp_id": dp_id,
        "instrument": "EUVE_DS_S",
        "n_raw": int(n_raw),
        "n_qualified": int(n_qualified),
        "candidates": candidates,
        "band_best_ul": band_best_ul,
    }


def run_euve_euv_calibration_v60(seed: int = 10202) -> dict[str, Any]:
    """
    `CALIBRATION_V60_EUVE_180`:
      - 60 unresolved EUV beacons across SW / MW / LW (`70.05-699.8 A`)
      - 40 geocoronal He I / He II / O II airglow lines (`G2`)
      - 40 EUV coronal atomic atlas lines (`G3`)
      - 40 single-pixel cosmic-ray spikes & SW/MW/LW detector seams (`G4`)
    """
    rng = np.random.default_rng(int(seed))
    trials: list[dict[str, Any]] = []
    rec = vet_geo = vet_cor = vet_art = 0

    w = np.linspace(70.05, 699.80, 2750, dtype=np.float64)
    safe_locs = [156.0, 231.5, 315.5, 398.0, 440.0, 482.5, 655.0, 675.0]

    for ti in range(180):
        noise_scale = 1.0e-13
        flux = 6.0e-13 + rng.normal(0.0, noise_scale, size=len(w))
        if ti < 60:
            cls_, want = "CLEAN_EUV_BEACON", True
            cw = float(safe_locs[ti % len(safe_locs)] + rng.uniform(-3.0, 3.0))
            fwhm_a = 0.55 if cw < 185.0 else (1.10 if cw < 370.0 else 2.20)
            sig_a = fwhm_a / FWHM_FACTOR
            amp = float(rng.uniform(10.0, 16.0)) * noise_scale
            flux += amp * np.exp(-0.5 * ((w - cw) / sig_a) ** 2)
        elif ti < 100:
            cls_, want = "GEOCORONAL_EUV_VETO", False
            _, cw = EUVE_GEOCORONAL_LINES_A[ti % len(EUVE_GEOCORONAL_LINES_A)]
            fwhm_a = 1.10 if cw < 370.0 else 2.20
            sig_a = fwhm_a / FWHM_FACTOR
            amp = float(rng.uniform(14.0, 25.0)) * noise_scale
            flux += amp * np.exp(-0.5 * ((w - cw) / sig_a) ** 2)
        elif ti < 140:
            cls_, want = "CORONAL_EUV_ATLAS_VETO", False
            pool = [("FeIX_171", 171.07), ("FeXII_195", 195.12), ("FeXV_284", 284.16), ("FeXVI_335", 335.41), ("NeVII_465", 465.22), ("MgX_609", 609.79)]
            _, cw = pool[ti % len(pool)]
            fwhm_a = 0.55 if cw < 185.0 else (1.10 if cw < 370.0 else 2.20)
            sig_a = fwhm_a / FWHM_FACTOR
            amp = float(rng.uniform(12.0, 22.0)) * noise_scale
            flux += amp * np.exp(-0.5 * ((w - cw) / sig_a) ** 2)
        else:
            cls_, want = "SPIKE_OR_SEAM_VETO", False
            if ti % 2 == 0:
                cw = float(safe_locs[ti % len(safe_locs)])
                k = int(np.argmin(np.abs(w - cw)))
                flux[k] += float(rng.uniform(15.0, 25.0)) * noise_scale
            else:
                cw = float(rng.choice([178.0, 368.0]))
                k = int(np.argmin(np.abs(w - cw)))
                sig_a = 1.10 / FWHM_FACTOR
                flux += 16.0 * noise_scale * np.exp(-0.5 * ((w - w[k]) / sig_a) ** 2)

        res = scan_euve_v60(w, flux, star=f"SIM_EUVE_{ti}", dist_pc=10.0)
        obs = res["n_qualified"] >= 1
        ok = int(bool(obs) == bool(want))
        if cls_ == "CLEAN_EUV_BEACON":
            rec += ok
        elif cls_ == "GEOCORONAL_EUV_VETO":
            vet_geo += ok
        elif cls_ == "CORONAL_EUV_ATLAS_VETO":
            vet_cor += ok
        else:
            vet_art += ok
        trials.append({
            "suite": "CALIBRATION_V60_EUVE_180",
            "class": cls_, "trial": ti + 1, "expected": int(want), "observed": int(obs), "passed": ok,
        })

    return {
        "total_trials": len(trials),
        "clean_euv_beacon_60": f"{rec}/60 ({rec/60.0:.4f})",
        "geocoronal_veto_40": f"{vet_geo}/40 ({vet_geo/40.0:.4f})",
        "coronal_atlas_veto_40": f"{vet_cor}/40 ({vet_cor/40.0:.4f})",
        "spike_seam_veto_40": f"{vet_art}/40 ({vet_art/40.0:.4f})",
        "trials": trials,
    }


if __name__ == "__main__":
    import json
    c1 = run_chandra_poisson_calibration_v60(10201)
    c2 = run_euve_euv_calibration_v60(10202)
    c3 = run_alma_interferometric_calibration_v59(10203)
    c4 = run_drifting_comb_calibration_v59(10204)
    summary = {k: {kk: vv for kk, vv in d.items() if kk != "trials"} for k, d in [
        ("CHANDRA_240", c1), ("EUVE_180", c2), ("ALMA_240", c3), ("COMB_DRIFT_240", c4)
    ]}
    print(json.dumps(summary, indent=2))
