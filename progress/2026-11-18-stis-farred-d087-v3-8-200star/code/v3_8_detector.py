#!/usr/bin/env python3
"""Prospective detector specification for Phase D087 (`SPACE_UV_STIS_AND_FARRED_V3_8`).

Extends D079-D086 (8 spectrographs, 0.305-2.515 um) to 9 spectrographs spanning >4 spectral
octaves (0.1145-2.515 um, 4.46 octaves):
1. Adds space-based NASA/ESA HST STIS E140M (0.1145-0.1710 um vacuum, R=45,800) with
   model-independent direct CALSTIS absolute spectrophotometric flux limits, 12 FUV NIST RV
   anchors (dual emission/absorption fit), geocoronal airglow (Ly-alpha, N I, O I) veto in
   Gate G2, FUV transition-region/chromospheric lines in Gate G3, and CALSTIS DQ + slit
   BACKGROUND/NET subtraction check in Gate G4_V38.
2. Adds VLT UVES Red-Arm (UVES_RED, 0.5655-1.0425 um air, R~42,310-107,200) closing the
   southern 0.786-0.980 um optical-NIR bridge gap via dual Gaia DR3 G_RP (<8500 A) +
   2MASS J (>=8500 A) Planck calibration, 12 far-red NIST RV anchors, and expanded Paranal
   OH Meinel 6-2/7-3/8-4/9-5/3-0 & H2O/O2 masks.
3. Extends ESPRESSO up to Ultra-High-Resolution UHR (R=190,000, FWHM=1.58 km/s) alongside
   HR (R=140,000), anchored to Gaia DR3 G.
4. Upgrades Gate G4_V38 (`FIBER_B_CALIBRATION_BLEED_V38`: peak(Flux_B) / median(Flux_A) >= 1.5
   in CAL/WAVE/FP/THAR mode) reducing D086's 577 simultaneous calibration bleeds 577 -> 0 in
   read-only regression while retaining COMB_V4_1 and Sparse G6_V36.
"""
from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np
from scipy.ndimage import median_filter

C_KMS = 299792.458
C_ANGSTROM_GHZ = 2997924580.0
FWHM_FACTOR = 2.0 * math.sqrt(2.0 * math.log(2.0))
MAD_NORM = 1.4826

# Radiometric constants (SVO Filter Profile Service Vega-system + Cohen et al. 2003)
GAIA_GBP_PIVOT_A = 5109.7121
GAIA_GBP_ZP_FLAM = 4.078518e-9
GAIA_G_PIVOT_A = 6217.6
GAIA_G_ZP_FLAM = 2.50386e-9
GAIA_GRP_PIVOT_A = 7769.0
GAIA_GRP_ZP_FLAM = 1.29303e-9
TWOMASS_J_PIVOT_A = 12350.0
TWOMASS_J_ZP_FLAM = 3.129e-10
RADIOMETRIC_RPJ_SPLIT_A = 8500.0

HC_OVER_K_ANGSTROM_KELVIN = 1.438776877e8
PC_CM = 3.0856775814913673e18
G_SI = 6.67430e-11
M_SUN_KG = 1.98847e30
DAY_S = 86400.0

PARANAL_LAT_DEG = -24.6272
PARANAL_LON_DEG = -70.4042

# 12 locked NIST FUV transitions (vacuum A, 1175-1657 A) for HST_STIS E140M
LOCKED_RV_ANCHORS_STIS_FUV = [
    {"anchor_id": "CIII_1175p711", "species": "C III", "lab_wave_A": 1175.711},
    {"anchor_id": "SiIII_1206p500", "species": "Si III", "lab_wave_A": 1206.500},
    {"anchor_id": "NV_1238p821", "species": "N V", "lab_wave_A": 1238.821},
    {"anchor_id": "NV_1242p804", "species": "N V", "lab_wave_A": 1242.804},
    {"anchor_id": "CII_1334p532", "species": "C II", "lab_wave_A": 1334.532},
    {"anchor_id": "CII_1335p708", "species": "C II", "lab_wave_A": 1335.708},
    {"anchor_id": "SiIV_1393p755", "species": "Si IV", "lab_wave_A": 1393.755},
    {"anchor_id": "SiIV_1402p770", "species": "Si IV", "lab_wave_A": 1402.770},
    {"anchor_id": "CIV_1548p195", "species": "C IV", "lab_wave_A": 1548.195},
    {"anchor_id": "CIV_1550p770", "species": "C IV", "lab_wave_A": 1550.770},
    {"anchor_id": "HeII_1640p420", "species": "He II", "lab_wave_A": 1640.420},
    {"anchor_id": "CI_1656p928", "species": "C I", "lab_wave_A": 1656.928},
]

# 12 isolated NIST red/far-red transitions (air A, 5853-8807 A) for UVES_RED
LOCKED_RV_ANCHORS_FARRED = [
    {"anchor_id": "BaII_5853p675", "species": "Ba II", "lab_wave_A": 5853.675},
    {"anchor_id": "CaI_6122p217", "species": "Ca I", "lab_wave_A": 6122.217},
    {"anchor_id": "FeI_6173p334", "species": "Fe I", "lab_wave_A": 6173.334},
    {"anchor_id": "CaI_6439p075", "species": "Ca I", "lab_wave_A": 6439.075},
    {"anchor_id": "FeI_6498p938", "species": "Fe I", "lab_wave_A": 6498.938},
    {"anchor_id": "CaI_6717p681", "species": "Ca I", "lab_wave_A": 6717.681},
    {"anchor_id": "KI_7698p965", "species": "K I", "lab_wave_A": 7698.965},
    {"anchor_id": "FeI_7780p557", "species": "Fe I", "lab_wave_A": 7780.557},
    {"anchor_id": "NaI_8183p256", "species": "Na I", "lab_wave_A": 8183.256},
    {"anchor_id": "NaI_8194p824", "species": "Na I", "lab_wave_A": 8194.824},
    {"anchor_id": "FeI_8688p625", "species": "Fe I", "lab_wave_A": 8688.625},
    {"anchor_id": "MgI_8806p757", "species": "Mg I", "lab_wave_A": 8806.757},
]

# 14 isolated NIST optical transitions (air A, 4447-6718 A) for ESPRESSO HR/UHR
LOCKED_RV_ANCHORS_OPTICAL = [
    {"anchor_id": "FeI_4447p717", "species": "Fe I", "lab_wave_A": 4447.717},
    {"anchor_id": "TiII_4571p971", "species": "Ti II", "lab_wave_A": 4571.971},
    {"anchor_id": "FeI_4602p941", "species": "Fe I", "lab_wave_A": 4602.941},
    {"anchor_id": "NiI_4829p023", "species": "Ni I", "lab_wave_A": 4829.023},
    {"anchor_id": "FeI_5250p646", "species": "Fe I", "lab_wave_A": 5250.646},
    {"anchor_id": "FeI_5731p762", "species": "Fe I", "lab_wave_A": 5731.762},
    {"anchor_id": "FeI_5732p296", "species": "Fe I", "lab_wave_A": 5732.296},
    {"anchor_id": "CaI_6122p217", "species": "Ca I", "lab_wave_A": 6122.217},
    {"anchor_id": "FeI_6173p334", "species": "Fe I", "lab_wave_A": 6173.334},
    {"anchor_id": "FeI_6200p313", "species": "Fe I", "lab_wave_A": 6200.313},
    {"anchor_id": "CaI_6439p075", "species": "Ca I", "lab_wave_A": 6439.075},
    {"anchor_id": "FeI_6498p938", "species": "Fe I", "lab_wave_A": 6498.938},
    {"anchor_id": "FeI_6546p238", "species": "Fe I", "lab_wave_A": 6546.238},
    {"anchor_id": "CaI_6717p681", "species": "Ca I", "lab_wave_A": 6717.681},
]

# Terrestrial airglow & far-red OH Meinel emission lines (topocentric air A, 3650-10425 A)
TELLURIC_AIRGLOW_LINES_A = [
    {"name": "HgI_3650", "wave_A": 3650.153},
    {"name": "N2p_3914_aurora", "wave_A": 3914.400},
    {"name": "HgI_4046", "wave_A": 4046.563},
    {"name": "HgI_4358", "wave_A": 4358.328},
    {"name": "NaI_5460_HgI", "wave_A": 5460.735},
    {"name": "OI_5577_auroral", "wave_A": 5577.339},
    {"name": "HgI_5769_streetlamp", "wave_A": 5769.598},
    {"name": "HgI_5790_streetlamp", "wave_A": 5790.663},
    {"name": "NaID2_5889", "wave_A": 5889.951},
    {"name": "NaID1_5895", "wave_A": 5895.924},
    {"name": "OH_6287", "wave_A": 6287.434},
    {"name": "OI_6300_nebular", "wave_A": 6300.304},
    {"name": "OH_6306", "wave_A": 6306.869},
    {"name": "OI_6363_nebular", "wave_A": 6363.776},
    {"name": "OH_6498", "wave_A": 6498.729},
    {"name": "OH_6533", "wave_A": 6533.044},
    {"name": "OH_6553", "wave_A": 6553.617},
    {"name": "OH_6828", "wave_A": 6828.520},
    {"name": "OH_6834", "wave_A": 6834.230},
    {"name": "OH_6863", "wave_A": 6863.955},
    {"name": "OH_6923", "wave_A": 6923.220},
    {"name": "OH_6948", "wave_A": 6948.952},
    {"name": "OH_7244", "wave_A": 7244.922},
    {"name": "OH_7316", "wave_A": 7316.282},
    {"name": "OH_7340", "wave_A": 7340.885},
    {"name": "OH_7369", "wave_A": 7369.248},
    {"name": "OH_7524", "wave_A": 7524.082},
    {"name": "OH_7750", "wave_A": 7750.640},
    {"name": "OH_7821", "wave_A": 7821.503},
    {"name": "OH_7913", "wave_A": 7913.708},
    {"name": "OH_7964", "wave_A": 7964.650},
    {"name": "OH_7993", "wave_A": 7993.332},
    {"name": "OH_8344", "wave_A": 8344.602},
    {"name": "OH_8399", "wave_A": 8399.170},
    {"name": "OH_8430", "wave_A": 8430.174},
    {"name": "OH_8465", "wave_A": 8465.208},
    {"name": "OH_8827", "wave_A": 8827.106},
    {"name": "OH_8885", "wave_A": 8885.850},
    {"name": "OH_8919", "wave_A": 8919.633},
    {"name": "OH_9375", "wave_A": 9375.961},
    {"name": "OH_9439", "wave_A": 9439.650},
    {"name": "OH_9791", "wave_A": 9790.980},
    {"name": "OH_9872", "wave_A": 9872.130},
    {"name": "OH_10014", "wave_A": 10014.000},
]

TELLURIC_SATURATED_BANDS_TOPO_A = [
    {"name": "O2_gamma_bandhead", "lo_A": 6276.0, "hi_A": 6284.5},
    {"name": "O2_B_band_core", "lo_A": 6866.0, "hi_A": 6932.0},
    {"name": "O2_A_band_core", "lo_A": 7592.0, "hi_A": 7685.0},
    {"name": "O2_Z_band_core", "lo_A": 8220.0, "hi_A": 8236.0},
    {"name": "H2O_rho_sigma_tau_core", "lo_A": 9310.0, "hi_A": 9620.0},
]

# HST LEO geocoronal emission bands (heliocentric/observatory vacuum A)
STIS_GEOCORONAL_BANDS_VAC_A = [
    {"name": "GEOCORONA_NI_1200", "lo_A": 1199.3, "hi_A": 1201.4},
    {"name": "GEOCORONA_HI_LYALPHA", "lo_A": 1212.5, "hi_A": 1219.0},
    {"name": "GEOCORONA_OI_1302", "lo_A": 1301.2, "hi_A": 1306.9},
    {"name": "GEOCORONA_OI_1356", "lo_A": 1355.2, "hi_A": 1359.0},
]

# Stellar optical & far-red chromospheric / flare transitions (stellar rest air A)
STELLAR_CHROMOSPHERIC_EMISSION_AIR_A = [
    {"name": "H11_3770", "wave_A": 3770.63},
    {"name": "H10_3797", "wave_A": 3797.90},
    {"name": "H9_3835", "wave_A": 3835.39},
    {"name": "HeI_3888", "wave_A": 3888.65},
    {"name": "CaII_K_3933", "wave_A": 3933.663},
    {"name": "CaII_H_3968", "wave_A": 3968.468},
    {"name": "Heps_3970", "wave_A": 3970.072},
    {"name": "HeI_4026", "wave_A": 4026.191},
    {"name": "Hdelta_4101", "wave_A": 4101.734},
    {"name": "CaI_4226", "wave_A": 4226.728},
    {"name": "Hgamma_4340", "wave_A": 4340.464},
    {"name": "HeI_4471", "wave_A": 4471.480},
    {"name": "HeII_4685", "wave_A": 4685.682},
    {"name": "Hbeta_4861", "wave_A": 4861.325},
    {"name": "MgIb4_5167", "wave_A": 5167.321},
    {"name": "MgIb2_5172", "wave_A": 5172.684},
    {"name": "MgIb1_5183", "wave_A": 5183.604},
    {"name": "HeID3_5875", "wave_A": 5875.621},
    {"name": "NaID2_5889", "wave_A": 5889.951},
    {"name": "NaID1_5895", "wave_A": 5895.924},
    {"name": "Halpha_6562", "wave_A": 6562.801},
    {"name": "HeI_6678", "wave_A": 6678.151},
    {"name": "HeI_7065", "wave_A": 7065.190},
    {"name": "KI_7664", "wave_A": 7664.900},
    {"name": "KI_7698", "wave_A": 7698.965},
    {"name": "OI_7771", "wave_A": 7771.944},
    {"name": "OI_7774", "wave_A": 7774.166},
    {"name": "OI_7775", "wave_A": 7775.388},
    {"name": "NaI_8183", "wave_A": 8183.256},
    {"name": "NaI_8194", "wave_A": 8194.824},
    {"name": "OI_8446", "wave_A": 8446.359},
    {"name": "CaII_IRT1_8498", "wave_A": 8498.023},
    {"name": "Pa16_8502", "wave_A": 8502.483},
    {"name": "CaII_IRT2_8542", "wave_A": 8542.091},
    {"name": "Pa15_8545", "wave_A": 8545.383},
    {"name": "Pa14_8598", "wave_A": 8598.392},
    {"name": "CaII_IRT3_8662", "wave_A": 8662.141},
    {"name": "Pa12_8750", "wave_A": 8750.473},
    {"name": "Pa11_8862", "wave_A": 8862.783},
    {"name": "Pa10_9014", "wave_A": 9014.911},
    {"name": "Pa9_9229", "wave_A": 9229.015},
    {"name": "Pa8_9545", "wave_A": 9545.972},
    {"name": "Pa7_10049", "wave_A": 10049.374},
]

# Stellar FUV transition-region & chromospheric emission lines (stellar rest vac A)
STELLAR_FUV_EMISSION_VAC_A = [
    {"name": "CIII_1175p7", "wave_A": 1175.711},
    {"name": "SiIII_1206", "wave_A": 1206.500},
    {"name": "HI_LyA_1215", "wave_A": 1215.670},
    {"name": "NV_1238", "wave_A": 1238.821},
    {"name": "NV_1242", "wave_A": 1242.804},
    {"name": "SiII_1260", "wave_A": 1260.422},
    {"name": "SiII_1264", "wave_A": 1264.738},
    {"name": "OI_1302", "wave_A": 1302.168},
    {"name": "OI_1304", "wave_A": 1304.858},
    {"name": "OI_1306", "wave_A": 1306.029},
    {"name": "CII_1334", "wave_A": 1334.532},
    {"name": "CII_1335", "wave_A": 1335.708},
    {"name": "OV_1371", "wave_A": 1371.296},
    {"name": "SiIV_1393", "wave_A": 1393.755},
    {"name": "OIV_1401", "wave_A": 1401.157},
    {"name": "SiIV_1402", "wave_A": 1402.770},
    {"name": "SiII_1526", "wave_A": 1526.707},
    {"name": "SiII_1533", "wave_A": 1533.431},
    {"name": "CIV_1548", "wave_A": 1548.195},
    {"name": "CIV_1550", "wave_A": 1550.770},
    {"name": "CI_1560", "wave_A": 1560.309},
    {"name": "CI_1561", "wave_A": 1561.438},
    {"name": "HeII_1640", "wave_A": 1640.420},
    {"name": "CI_1656", "wave_A": 1656.928},
    {"name": "OIII_1666", "wave_A": 1666.150},
    {"name": "AlII_1670", "wave_A": 1670.787},
]

# Clean calibration & radiometric upper-limit bands per D087 instrument
CALIBRATION_BANDS_STIS_FUV_A = [
    {"band_id": "F1_FUV_1275", "center_wave_A": 1275.00},
    {"band_id": "F2_FUV_1365", "center_wave_A": 1365.00},
    {"band_id": "F3_FUV_1475", "center_wave_A": 1475.00},
    {"band_id": "F4_FUV_1615", "center_wave_A": 1615.00},
]

CALIBRATION_BANDS_UVES_RED_A = [
    {"band_id": "R2_DEEPRED_7465", "center_wave_A": 7465.10},
    {"band_id": "R3_RBI_NEAR_7954", "center_wave_A": 7954.00},
    {"band_id": "R4_DIODE_8082", "center_wave_A": 8082.00},
    {"band_id": "R5_CSI_D2_8525", "center_wave_A": 8525.00},
    {"band_id": "R6_TISAPPH_8735", "center_wave_A": 8735.00},
    {"band_id": "R7_CSI_D1_8943", "center_wave_A": 8943.50},
]

OPTIONAL_UVES_RED_BANDS_A = [
    {"band_id": "R1_HENE_6328", "center_wave_A": 6328.20, "req_min_le": 6300.0, "req_max_ge": 6360.0},
    {"band_id": "R8_DIODE_9762", "center_wave_A": 9762.00, "req_min_le": 9730.0, "req_max_ge": 9800.0},
]

CALIBRATION_BANDS_ESPRESSO_A = [
    {"band_id": "B1_UVBLUE_3844", "center_wave_A": 3844.75},
    {"band_id": "B2_CAHK_BLUE_3951", "center_wave_A": 3951.50},
    {"band_id": "B3_VIOLET_4244", "center_wave_A": 4244.30},
    {"band_id": "B4_BLUEGRN_4675", "center_wave_A": 4675.80},
    {"band_id": "B5_GREEN_5195", "center_wave_A": 5195.00},
    {"band_id": "B6_YLWGRN_5773", "center_wave_A": 5773.00},
    {"band_id": "B7_HENE_RED_6323", "center_wave_A": 6323.60},
    {"band_id": "B8_FARRED_6825", "center_wave_A": 6825.40},
    {"band_id": "B9_DEEPRED_7465", "center_wave_A": 7465.10},
]

COMB_V4_1_WINDOWS_A: dict[str, list[dict[str, Any]]] = {
    "HST_STIS": [
        {"band": "STIS_FUV_SHORT", "lo_a": 1245.0, "hi_a": 1388.0},
        {"band": "STIS_FUV_LONG", "lo_a": 1412.0, "hi_a": 1635.0},
    ],
    "UVES_RED": [
        {"band": "UVES_RED_OPT", "lo_a": 6580.0, "hi_a": 7560.0},
        {"band": "UVES_FARRED_IZ", "lo_a": 7860.0, "hi_a": 9180.0},
    ],
    "ESPRESSO": [
        {"band": "OPT_BLUE", "lo_a": 4010.0, "hi_a": 4840.0},
        {"band": "OPT_GREEN", "lo_a": 4910.0, "hi_a": 5860.0},
        {"band": "OPT_RED", "lo_a": 5940.0, "hi_a": 6850.0},
    ],
}

BASE_V3_8_CONFIG: dict[str, Any] = {
    "schema": "SPACE_UV_STIS_AND_FARRED_V3_8",
    "knn_atlas_neighbors": 5,
    "knn_teff_scale_k": 380.0,
    "knn_mh_scale_dex": 0.25,
    "fit_phases_bins": [-0.5, -0.25, 0.0, 0.25, 0.5],
    "core_sigma_mult": 3.5,
    "mid_inner_sigma_mult": 6.0,
    "mid_outer_sigma_mult": 30.0,
    "outer_inner_sigma_mult": 30.0,
    "outer_outer_sigma_mult": 60.0,
    "prescreen_local_mad": 3.5,
    "supraphotospheric_min_fn_pk3": 1.008,
    # Channel T
    "channel_t_snr_mid_min": 6.5,
    "channel_t_snr_outer_min": 6.0,
    "channel_t_amp_ratio_min": 0.70,
    "channel_t_amp_ratio_max": 1.35,
    "channel_t_cosine_min": 0.82,
    "channel_t_fwhm_ratio_min": 0.55,
    "channel_t_fwhm_ratio_max": 1.65,
    "channel_t_cross_amp_ratio_min": 0.60,
    "channel_t_cross_snr_min": 4.5,
    # Channel P
    "channel_p_snr_mid_min": 7.0,
    "channel_p_snr_outer_min": 6.5,
    "channel_p_amp_ratio_min": 0.70,
    "channel_p_amp_ratio_max": 1.35,
    "channel_p_cosine_min": 0.85,
    "channel_p_fwhm_ratio_min": 0.60,
    "channel_p_fwhm_ratio_max": 1.45,
    "channel_p_min_epochs_above_3sigma": 3,
    "channel_p_min_epoch_fraction": 0.50,
    # Channel T_DIFF
    "channel_tdiff_snr_mid_min": 6.8,
    "channel_tdiff_snr_outer_min": 6.2,
    "channel_tdiff_amp_ratio_min": 0.70,
    "channel_tdiff_amp_ratio_max": 1.35,
    "channel_tdiff_cosine_min": 0.84,
    "channel_tdiff_fwhm_ratio_min": 0.58,
    "channel_tdiff_fwhm_ratio_max": 1.50,
    "channel_tdiff_min_in_exp_snr": 2.8,
    "channel_tdiff_min_in_exp_fraction": 0.60,
    # Channel K_PLANET
    "channel_kplanet_snr_mid_min": 6.8,
    "channel_kplanet_snr_outer_min": 6.2,
    "channel_kplanet_amp_ratio_min": 0.70,
    "channel_kplanet_amp_ratio_max": 1.35,
    "channel_kplanet_cosine_min": 0.84,
    "channel_kplanet_fwhm_ratio_min": 0.58,
    "channel_kplanet_fwhm_ratio_max": 1.50,
    "channel_kplanet_min_in_exp_snr": 2.5,
    "channel_kplanet_min_in_exp_fraction": 0.60,
    # Gates G2, G3, G4_V38, G5, G6_V36
    "gate_g2_airglow_tol_angstrom": 0.12,
    "gate_g3_native_snr_min": 5.0,
    "gate_g3_max_single_px_fraction": 0.62,
    "gate_g3_min_bilateral_wing_ratio": 0.12,
    "gate_g3_max_template_dip_fraction": 0.55,
    "gate_g3_chromo_tol_angstrom": 0.35,
    "gate_g3_fuv_chromo_tol_angstrom": 0.45,
    "gate_g4_overlap_edge_margin_px": 25,
    "gate_g4_secondary_flux_ratio_min": 0.15,
    "gate_g4_secondary_cont_snr_min": 4.0,
    "gate_g4_secondary_snr_min": 3.0,
    "gate_g4_order_contrast_ratio_min": 0.35,
    "gate_g4_order_contrast_ratio_max": 2.85,
    "gate_g4_fiber_b_wave_bleed_mad_mult": 30.0,
    "gate_g4_fiber_b_wave_over_a_ratio": 10.0,
    "gate_g4_v38_fiber_b_over_a_cont_min": 1.5,
    "gate_g4_fiber_b_sky_ratio_max": 0.35,
    "gate_g4_uves_sky_slit_ratio_max": 0.45,
    "gate_g4_stis_bg_over_net_max": 0.45,
    # Gate G5 1D 11-px native LSF morphology
    "gate_g5_cos11_min": 0.85,
    "gate_g5_ipc_hotpx_max_ratio": 2.35,
    "gate_g5_far_wing_34_max": 0.42,
    # Gate G6 Sparse Non-Local Atlas
    "gate_g6_topo_tol_a": 0.06,
    "gate_g6_native_px_tol": 2,
    "gate_g6_min_distinct_stars": 3,
    "gate_g6_intra_star_berv_sep_kms": 5.0,
    # COMB_V4_1 parameters
    "comb_freq_step_ghz": 0.5,
    "comb_n_teeth": 6,
    "comb_min_qualifying_teeth": 5,
    "comb_tooth_z_min": 2.1,
    "comb_tooth_z_cap": 6.5,
    "comb_tooth_fn_min": 0.85,
    "comb_tooth_recon_min": 0.78,
    "comb_score_min": 8.75,
    "comb_max_tooth_frac": 0.28,
    "comb_topo_anti_ratio_max": 0.45,
    "comb_v41_off_tooth_crowding_max": 0.35,
    "comb_v41_intertooth_max_ratio": 0.60,
    "comb_spacings_ghz": [15.0, 20.0, 25.0, 30.0, 40.0, 50.0, 60.0, 100.0],
    # RV anchors & continuum
    "rv_anchor_window_kms": 28.0,
    "rv_anchor_fuv_window_kms": 45.0,
    "rv_anchor_scan_half_kms": 8.0,
    "rv_anchor_scan_step_kms": 0.05,
    "rv_anchor_photospheric_fwhm_kms": 8.0,
    "rv_anchor_fuv_fwhm_kms": 18.0,
    "rv_anchor_min_rel_depth": 0.12,
    "rv_anchor_fuv_min_snr": 3.5,
    "continuum_block_bins": 100,
    "continuum_blue_cutoff_angstrom": 4050.0,
    "continuum_quantile_blue": 0.90,
    "continuum_quantile": 0.80,
    "continuum_median_blocks": 5,
    "tx_aperture_diameter_m": 10.0,
}


def get_inst_config(instrument: str, resolving_power: float | None = None) -> dict[str, Any]:
    inst = instrument.upper()
    cfg = dict(BASE_V3_8_CONFIG)
    cfg["instrument"] = inst
    if inst == "HST_STIS":
        r_pow = float(resolving_power) if resolving_power else 45800.0
        cfg["resolving_power"] = r_pow
        cfg["fwhm_v_kms"] = C_KMS / r_pow
        cfg["sigma_v_kms"] = cfg["fwhm_v_kms"] / FWHM_FACTOR
        cfg["coadd_step_angstrom"] = 0.015
        cfg["wave_min_angstrom"] = 1145.0
        cfg["wave_max_angstrom"] = 1710.0
        cfg["coadd_rest_min_angstrom"] = 1148.0
        cfg["coadd_rest_max_angstrom"] = 1706.0
        cfg["ext_rest_min_angstrom"] = 1142.0
        cfg["ext_rest_max_angstrom"] = 1712.0
        cfg["observatory"] = "HST_LEO"
        cfg["lat_deg"] = 0.0
        cfg["lon_deg"] = 0.0
        cfg["telescope_diameter_m"] = 2.40
        cfg["radiometric_anchor"] = "HST_CALSTIS_DIRECT_FLAM"
        cfg["rv_anchors"] = LOCKED_RV_ANCHORS_STIS_FUV
        cfg["comb_search_bands"] = ["STIS_FUV_SHORT", "STIS_FUV_LONG"]
        cfg["comb_freq_step_ghz"] = 1.5
    elif inst == "UVES_RED":
        r_pow = float(resolving_power) if resolving_power else 56990.0
        r_pow = max(38000.0, min(115000.0, r_pow))
        cfg["resolving_power"] = r_pow
        cfg["fwhm_v_kms"] = C_KMS / r_pow
        cfg["sigma_v_kms"] = cfg["fwhm_v_kms"] / FWHM_FACTOR
        cfg["coadd_step_angstrom"] = 0.025
        cfg["wave_min_angstrom"] = 5655.0
        cfg["wave_max_angstrom"] = 10425.0
        cfg["coadd_rest_min_angstrom"] = 5660.0
        cfg["coadd_rest_max_angstrom"] = 10415.0
        cfg["ext_rest_min_angstrom"] = 5650.0
        cfg["ext_rest_max_angstrom"] = 10430.0
        cfg["observatory"] = "PARANAL"
        cfg["lat_deg"] = PARANAL_LAT_DEG
        cfg["lon_deg"] = PARANAL_LON_DEG
        cfg["telescope_diameter_m"] = 8.20
        cfg["radiometric_anchor"] = "DUAL_GAIA_GRP_TWOMASS_J"
        cfg["rv_anchors"] = LOCKED_RV_ANCHORS_FARRED
        cfg["comb_search_bands"] = ["UVES_RED_OPT", "UVES_FARRED_IZ"]
    elif inst == "ESPRESSO":
        r_pow = float(resolving_power) if (resolving_power and float(resolving_power) >= 175000.0) else 140000.0
        cfg["resolving_power"] = r_pow
        cfg["fwhm_v_kms"] = C_KMS / r_pow
        cfg["sigma_v_kms"] = cfg["fwhm_v_kms"] / FWHM_FACTOR
        cfg["coadd_step_angstrom"] = 0.01
        cfg["wave_min_angstrom"] = 3790.0
        cfg["wave_max_angstrom"] = 7860.0
        cfg["coadd_rest_min_angstrom"] = 3792.0
        cfg["coadd_rest_max_angstrom"] = 7850.0
        cfg["ext_rest_min_angstrom"] = 3788.0
        cfg["ext_rest_max_angstrom"] = 7864.0
        cfg["observatory"] = "PARANAL"
        cfg["lat_deg"] = PARANAL_LAT_DEG
        cfg["lon_deg"] = PARANAL_LON_DEG
        cfg["telescope_diameter_m"] = 8.20
        cfg["radiometric_anchor"] = "GAIA_DR3_G"
        cfg["rv_anchors"] = LOCKED_RV_ANCHORS_OPTICAL
        cfg["comb_search_bands"] = ["OPT_BLUE", "OPT_GREEN", "OPT_RED"]
    else:
        raise ValueError(f"Unsupported D087 instrument: {instrument}")
    return cfg


def get_calibration_bands(instrument: str) -> list[dict[str, Any]]:
    iu = instrument.upper()
    if iu == "HST_STIS":
        return CALIBRATION_BANDS_STIS_FUV_A
    if iu == "UVES_RED":
        return CALIBRATION_BANDS_UVES_RED_A
    return CALIBRATION_BANDS_ESPRESSO_A


# ---------------------------------------------------------------------------
# Pure-Stdlib Observatory & Earth Heliocentric Velocity + Array Math Helpers
# ---------------------------------------------------------------------------

def stdlib_earth_helio_rv_kms(ra_deg: float, dec_deg: float, mjd_utc: float) -> float:
    """Earth orbital barycentric/heliocentric projection without surface rotation (for HST LEO)."""
    jd = float(mjd_utc) + 2400000.5
    d = jd - 2451545.0
    t_c = d / 36525.0
    g = math.radians((357.5291092 + 35999.0502909 * t_c) % 360.0)
    l0 = math.radians((280.46646 + 36000.76983 * t_c) % 360.0)
    c_eq = math.radians((1.914602 - 0.004817 * t_c) * math.sin(g) + 0.019993 * math.sin(2.0 * g))
    lam_sun = l0 + c_eq
    e_orb = 0.016708634
    v_earth = 29.7847
    eps = math.radians(23.4392911 - 0.0130042 * t_c)
    pi_sun = math.radians((282.937348 + 1.71953 * t_c) % 360.0)
    lam_e = lam_sun + math.pi
    pi_e = pi_sun + math.pi
    v0 = v_earth / math.sqrt(1.0 - e_orb * e_orb)
    vx_ecl = v0 * (-math.sin(lam_e) - e_orb * math.sin(pi_e))
    vy_ecl = v0 * (math.cos(lam_e) + e_orb * math.cos(pi_e))
    vx_eq = vx_ecl
    vy_eq = vy_ecl * math.cos(eps)
    vz_eq = vy_ecl * math.sin(eps)
    ra, dec = math.radians(ra_deg), math.radians(dec_deg)
    return float(vx_eq * math.cos(dec) * math.cos(ra) + vy_eq * math.cos(dec) * math.sin(ra) + vz_eq * math.sin(dec))


def stdlib_observatory_berv_kms(
    ra_deg: float,
    dec_deg: float,
    mjd_utc: float,
    lat_deg: float = PARANAL_LAT_DEG,
    lon_deg: float = PARANAL_LON_DEG,
) -> float:
    """Analytical solar-system barycentric velocity correction (orbital + diurnal)."""
    jd = float(mjd_utc) + 2400000.5
    d = jd - 2451545.0
    t_c = d / 36525.0
    g = math.radians((357.5291092 + 35999.0502909 * t_c) % 360.0)
    l0 = math.radians((280.46646 + 36000.76983 * t_c) % 360.0)
    c_eq = math.radians((1.914602 - 0.004817 * t_c) * math.sin(g) + 0.019993 * math.sin(2.0 * g))
    lam_sun = l0 + c_eq
    e_orb = 0.016708634
    v_earth = 29.7847
    eps = math.radians(23.4392911 - 0.0130042 * t_c)
    pi_sun = math.radians((282.937348 + 1.71953 * t_c) % 360.0)
    lam_true_e = lam_sun + math.pi
    pi_e = pi_sun + math.pi
    v0 = v_earth / math.sqrt(1.0 - e_orb * e_orb)
    vx_eq = v0 * (-math.sin(lam_true_e) - e_orb * math.sin(pi_e))
    vy_ecl = v0 * (math.cos(lam_true_e) + e_orb * math.cos(pi_e))
    vy_eq = vy_ecl * math.cos(eps)
    vz_eq = vy_ecl * math.sin(eps)

    gmst_deg = (280.46061837 + 360.98564736629 * d + 0.000387933 * (t_c * t_c)) % 360.0
    lst = math.radians((gmst_deg + lon_deg) % 360.0)
    v_rot = 0.46510 * math.cos(math.radians(lat_deg))
    vx_eq += -v_rot * math.sin(lst)
    vy_eq += v_rot * math.cos(lst)

    ra, dec = math.radians(ra_deg), math.radians(dec_deg)
    return float(vx_eq * math.cos(dec) * math.cos(ra) + vy_eq * math.cos(dec) * math.sin(ra) + vz_eq * math.sin(dec))


def exact_median_1d(arr: np.ndarray) -> float:
    s = np.sort(np.asarray(arr, dtype=np.float64))
    n = len(s)
    if n == 0:
        return float("nan")
    m = n // 2
    return float(s[m]) if (n % 2 == 1) else float(0.5 * (s[m - 1] + s[m]))


def exact_quantile_1d(arr: np.ndarray, q: float) -> float:
    s = np.sort(np.asarray(arr, dtype=np.float64))
    n = len(s)
    if n == 0:
        return float("nan")
    if n == 1:
        return float(s[0])
    pos = q * (n - 1)
    lo = int(math.floor(pos))
    hi = min(n - 1, lo + 1)
    frac = pos - lo
    return float((1.0 - frac) * s[lo] + frac * s[hi])


def exact_mad_1d(arr: np.ndarray) -> float:
    med = exact_median_1d(arr)
    if not math.isfinite(med):
        return float("nan")
    return float(MAD_NORM * exact_median_1d(np.abs(np.asarray(arr, dtype=np.float64) - med)))


def compute_keplerian_kp_kms(st_mass_msun: float, orbper_days: float, ecc: float = 0.0) -> float:
    e_val = float(ecc) if (ecc is not None and 0.0 <= float(ecc) < 0.95) else 0.0
    v_circ_ms = ((2.0 * math.pi * G_SI * float(st_mass_msun) * M_SUN_KG) / (float(orbper_days) * DAY_S)) ** (1.0 / 3.0)
    return float((v_circ_ms / math.sqrt(1.0 - e_val * e_val)) / 1000.0)


def compute_planet_orbital_rv_kms(bjd_mid: float, t0_bjd: float, orbper_days: float, kp_kms: float) -> tuple[float, float]:
    raw_phi = (float(bjd_mid) - float(t0_bjd)) / float(orbper_days)
    phi_signed = raw_phi - round(raw_phi)
    return float(phi_signed), float(kp_kms * math.sin(2.0 * math.pi * phi_signed))


def planet_rest_to_bary_wave(wave_planet_a: float | np.ndarray, v_star_kms: float, dv_orb_kms: float) -> float | np.ndarray:
    return wave_planet_a * (1.0 + float(v_star_kms) / C_KMS) * (1.0 + float(dv_orb_kms) / C_KMS)


def bary_to_planet_rest_wave(wave_bary_a: float | np.ndarray, v_star_kms: float, dv_orb_kms: float) -> float | np.ndarray:
    return wave_bary_a / ((1.0 + float(v_star_kms) / C_KMS) * (1.0 + float(dv_orb_kms) / C_KMS))


# ---------------------------------------------------------------------------
# Step 1: Photospheric & FUV Transition-Region Stellar RV Anchoring
# ---------------------------------------------------------------------------

def fit_rv_anchor_absorption(
    wave_win: np.ndarray,
    flux_win: np.ndarray,
    lab_wave_a: float,
    prior_rv_kms: float,
    cfg: dict[str, Any] = BASE_V3_8_CONFIG,
) -> dict[str, Any]:
    w = np.asarray(wave_win, dtype=np.float64)
    f = np.asarray(flux_win, dtype=np.float64)
    valid = np.isfinite(w) & np.isfinite(f)
    if cfg.get("instrument") != "HST_STIS":
        valid = valid & (f > 0.0)
    w, f = w[valid], f[valid]
    if len(w) < 12:
        return {
            "status": "INSUFFICIENT_SAMPLES",
            "n_samples": int(len(w)),
            "best_rv_kms": float("nan"),
            "rel_depth": float("nan"),
            "min_sse": float("nan"),
            "boundary_hit": True,
        }

    is_fuv = cfg.get("instrument") == "HST_STIS"
    dv = C_KMS * (w - lab_wave_a) / lab_wave_a
    win_kms = float(cfg["rv_anchor_fuv_window_kms"] if is_fuv else cfg["rv_anchor_window_kms"])
    u = (dv - prior_rv_kms) / win_kms
    fwhm_p = float(cfg["rv_anchor_fuv_fwhm_kms"] if is_fuv else cfg["rv_anchor_photospheric_fwhm_kms"])
    sigma_phot = fwhm_p / FWHM_FACTOR
    half = float(cfg["rv_anchor_scan_half_kms"])
    step = float(cfg["rv_anchor_scan_step_kms"])
    n_grid = int(round(2.0 * half / step)) + 1
    grid = prior_rv_kms - half + step * np.arange(n_grid, dtype=np.float64)
    ones = np.ones_like(u)
    sses = np.full(n_grid, np.inf, dtype=np.float64)
    c0s = np.zeros(n_grid, dtype=np.float64)
    amps = np.zeros(n_grid, dtype=np.float64)
    snrs = np.zeros(n_grid, dtype=np.float64)

    for idx, v_try in enumerate(grid):
        g_core = np.exp(-0.5 * ((dv - v_try) / sigma_phot) ** 2)
        prof = g_core if is_fuv else -g_core
        X = np.column_stack([ones, u, prof])
        try:
            beta = np.linalg.solve(X.T @ X, X.T @ f)
        except np.linalg.LinAlgError:
            continue
        c0, _c1, amp = float(beta[0]), float(beta[1]), float(beta[2])
        if is_fuv:
            # Allow emission (amp > 0) for late-type chromospheric FUV OR absorption (amp < 0) on hot A-stars
            resid = f - (X @ beta)
            sse = float(resid @ resid)
            sb_mask = np.abs(dv - v_try) >= 2.0 * sigma_phot
            sb_mad = max(1e-30, exact_mad_1d(resid[sb_mask]) if int(np.sum(sb_mask)) >= 6 else exact_mad_1d(resid))
            sses[idx] = sse
            c0s[idx] = c0
            amps[idx] = abs(amp)
            snrs[idx] = abs(amp) / sb_mad
        else:
            if amp <= 0.0 or c0 <= 0.0:
                X2 = np.column_stack([ones, u])
                b2 = np.linalg.solve(X2.T @ X2, X2.T @ f)
                resid = f - (X2 @ b2)
                sses[idx] = float(resid @ resid)
                c0s[idx] = float(b2[0])
                amps[idx] = 0.0
                snrs[idx] = 0.0
            else:
                resid = f - (X @ beta)
                sses[idx] = float(resid @ resid)
                c0s[idx] = c0
                amps[idx] = amp
                snrs[idx] = amp / max(1e-30, c0)

    best_idx = int(np.argmin(sses))
    boundary_hit = (best_idx == 0) or (best_idx == n_grid - 1)
    best_v = float(grid[best_idx])
    if not boundary_hit:
        y_m, y_0, y_p = float(sses[best_idx - 1]), float(sses[best_idx]), float(sses[best_idx + 1])
        denom = y_m - 2.0 * y_0 + y_p
        if denom > 1e-30:
            delta = max(-0.5, min(0.5, 0.5 * (y_m - y_p) / denom))
            best_v = float(grid[best_idx] + delta * step)

    if is_fuv:
        metric = float(snrs[best_idx])
        clean = (not boundary_hit) and (metric >= float(cfg["rv_anchor_fuv_min_snr"]))
    else:
        c0_best = float(c0s[best_idx])
        metric = float(amps[best_idx] / c0_best) if c0_best > 0 else 0.0
        clean = (not boundary_hit) and (metric >= float(cfg["rv_anchor_min_rel_depth"]))
    return {
        "status": "CLEAN_ABSORPTION" if clean else ("BOUNDARY_HIT" if boundary_hit else "SHALLOW_OR_BLENDED"),
        "n_samples": int(len(w)),
        "best_rv_kms": best_v,
        "rel_depth": float(metric),
        "min_sse": float(sses[best_idx]),
        "boundary_hit": bool(boundary_hit),
    }


def extract_rv_anchor_window(
    wave: np.ndarray,
    flux: np.ndarray,
    lab_wave_a: float,
    prior_rv_kms: float,
    cfg: dict[str, Any] = BASE_V3_8_CONFIG,
) -> tuple[np.ndarray, np.ndarray]:
    dv = C_KMS * (wave - lab_wave_a) / lab_wave_a
    win_kms = float(cfg["rv_anchor_fuv_window_kms"] if cfg.get("instrument") == "HST_STIS" else cfg["rv_anchor_window_kms"])
    mask = np.abs(dv - prior_rv_kms) <= win_kms
    return wave[mask].copy(), flux[mask].copy()


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
    # Scale HST FUV cgs fluxes (~1e-13) into O(1) units before rounding to 4 decimals in JSON bundle!
    scale_anc = 1.0
    if cfg.get("instrument") == "HST_STIS":
        med_abs = float(np.nanmedian(np.abs(flux[np.isfinite(flux) & (flux != 0)]))) if np.any(np.isfinite(flux) & (flux != 0)) else 1e-14
        scale_anc = 1.0 / max(1e-20, med_abs)
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
        bundle[aid] = {"wave_a": [round(float(x), 6) for x in w_win], "flux": [round(float(y), 4) for y in f_win]}
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
# Step 2: Wavelength-Adaptive Continuum & Instrument-Aware KNN Templates
# ---------------------------------------------------------------------------

def compute_running_continuum(
    wave: np.ndarray,
    flux: np.ndarray,
    cfg: dict[str, Any] = BASE_V3_8_CONFIG,
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
    g_floor = 0.25 * exact_quantile_1d(global_pos, 0.70) if len(global_pos) >= 20 else 1e-15
    if e_arr is not None:
        e_fin = e_arr[np.isfinite(e_arr) & (e_arr > 0.0)]
        if len(e_fin) >= 20:
            g_floor = max(g_floor, 3.0 * exact_median_1d(e_fin))
    g_floor = max(1e-18, float(g_floor))

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
    block_size: int = 2000,
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
            if int(m_b.sum()) >= 30:
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
    cfg: dict[str, Any] = BASE_V3_8_CONFIG,
) -> tuple[dict[str, np.ndarray], dict[str, dict[str, Any]]]:
    k_nn = int(cfg["knn_atlas_neighbors"])
    s_t = float(cfg["knn_teff_scale_k"])
    s_m = float(cfg["knn_mh_scale_dex"])
    matched_templates: dict[str, np.ndarray] = {}
    template_meta: dict[str, dict[str, Any]] = {}

    stars = sorted(star_norm_coadds.keys())
    for st in stars:
        mt = star_meta[st]
        inst_st = mt["instrument"]
        cands = []
        for other in stars:
            if other == st:
                continue
            mo = star_meta[other]
            if mo["instrument"] != inst_st:
                continue
            d2 = ((mt["teff_k"] - mo["teff_k"]) / s_t) ** 2 + ((mt["mh_dex"] - mo["mh_dex"]) / s_m) ** 2
            cands.append((d2, other))
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
# Step 3: Instrument-LSF Matched Filtering across T, P, T_DIFF, K_PLANET
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
    if int(valid.sum()) < 25:
        return {"valid_fit": False}

    step_a = float(exact_median_1d(np.diff(w)))
    sigma_v = float(cfg["sigma_v_kms"])
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
        if int(bg_mid.sum()) < 10 or int(core.sum()) < 3:
            continue

        b0 = exact_median_1d(y[bg_mid])
        yc = y[core] - b0
        g = np.exp(-0.5 * (dv[core] / sigma_v) ** 2)
        gg = float(g @ g)
        if gg <= 0.0:
            continue
        amp = float(yc @ g) / gg
        if amp <= 0.0:
            continue
        yn = float(math.sqrt(max(0.0, float(yc @ yc))))
        gn = float(math.sqrt(gg))
        cosine = (float(yc @ g) / (yn * gn)) if (yn > 0.0 and gn > 0.0) else 0.0
        sig_mid = exact_mad_1d(y[bg_mid])
        sig_out = exact_mad_1d(y[bg_out]) if int(bg_out.sum()) >= 10 else sig_mid
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
                fwhm_a = mu_a / float(cfg["resolving_power"])
                fwhm_ratio = w_span / max(1e-6, fwhm_a)
            else:
                fwhm_ratio = 1.0
            best = {
                "valid_fit": True,
                "fitted_center_a": mu_a,
                "phase_bins": float(ph),
                "amp_mid": float(amp),
                "snr_mid": float(amp / sig_mid),
                "snr_out": float(amp / sig_out) if (math.isfinite(sig_out) and sig_out > 0.0) else float(amp / sig_mid),
                "sig_mid": float(sig_mid),
                "cosine": float(cosine),
                "fwhm_ratio": float(fwhm_ratio),
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
    sl = slice(max(0, k0 - 1), min(len(fn), k0 + 2))
    sub = fn[sl]
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
    if snr_out <= 0.0:
        return False
    ratio = fit["snr_mid"] / snr_out
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
    step_a = float(cfg["coadd_step_angstrom"])
    margin = max(65, int(round(4.5 / step_a)))
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
        if seg_e - seg_s < 2 * margin + 25:
            continue
        vals = y_primary[seg_s:seg_e]
        med = median_filter(vals, size=101, mode="nearest")
        resid = vals - med
        mad = MAD_NORM * median_filter(np.abs(resid), size=101, mode="nearest")
        ok_s = np.isfinite(mad[margin:-margin]) & (mad[margin:-margin] > 0)
        searched_bins += int(ok_s.sum())

        localmax = np.r_[False, (resid[1:-1] > resid[:-2]) & (resid[1:-1] >= resid[2:]), False]
        elig = np.zeros(len(vals), dtype=bool)
        elig[margin:-margin] = ok_s
        seeds = np.flatnonzero(localmax & elig & (resid >= cfg["prescreen_local_mad"] * mad))

        for j in seeds:
            k = seg_s + int(j)
            w0 = float(wave[k])
            win_sl = slice(k - margin, k + margin + 1)
            fit = fit_lsf_on_window(wave[win_sl], y_primary[win_sl], w0, cfg)
            if not check_channel_lsf_gate(fit, channel, cfg):
                continue

            if channel == "T" and y_secondary_check is not None:
                cfit = fit_lsf_on_window(wave[win_sl], y_secondary_check[win_sl], w0, cfg, fixed_phase_bins=fit["phase_bins"])
                if not cfit.get("valid_fit"):
                    continue
                cr = cfit["amp_mid"] / fit["amp_mid"] if fit["amp_mid"] > 0 else 0.0
                if cr < cfg["channel_t_cross_amp_ratio_min"] or cfit["snr_mid"] < cfg["channel_t_cross_snr_min"]:
                    continue
                fit["cross_amp_mid"] = cfit["amp_mid"]
                fit["cross_snr_mid"] = cfit["snr_mid"]
            else:
                fit["cross_amp_mid"] = fit["amp_mid"]
                fit["cross_snr_mid"] = fit["snr_mid"]

            if flux_norm_for_f1 is not None:
                f1 = compute_supraphotospheric_f1_window(wave[win_sl], flux_norm_for_f1[win_sl], fit["fitted_center_a"], min_fn)
                fit["target_fn_pk3"] = f1["fn_pk3"]
                fit["g1_f1_pass"] = f1["f1_supraphotospheric_pass"]
            else:
                fit["target_fn_pk3"] = 1.05
                fit["g1_f1_pass"] = True

            fit["seed_index"] = int(k)
            fit["channel"] = channel
            prelim_pre_f1.append(fit)

    dedup_pre: list[dict[str, Any]] = []
    for h in sorted(prelim_pre_f1, key=lambda x: (-x["snr_mid"], x["seed_index"])):
        fwhm_a = h["fitted_center_a"] / cfg["resolving_power"]
        if any(abs(h["fitted_center_a"] - p["fitted_center_a"]) <= 1.5 * fwhm_a for p in dedup_pre):
            continue
        dedup_pre.append(h)
    dedup_pre.sort(key=lambda x: x["seed_index"])
    accepted = [h for h in dedup_pre if h.get("g1_f1_pass", True)] if enforce_f1_in_g1 else dedup_pre
    return accepted, searched_bins, len(dedup_pre)


def build_multi_epoch_rest_coadd_and_channel_p(
    rest_grid: np.ndarray,
    exp_rest_flux_norm: np.ndarray,
    exp_rest_resids: np.ndarray,
    matched_template: np.ndarray,
    cfg: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]], int, int]:
    n_exp, n_bins = exp_rest_resids.shape
    fin = np.isfinite(exp_rest_resids)
    n_valid = np.sum(fin, axis=0)
    min_req = max(2, min(n_exp, int(cfg["channel_p_min_epochs_above_3sigma"])))

    masked_r = np.where(fin, exp_rest_resids, np.nan)
    masked_fn = np.where(np.isfinite(exp_rest_flux_norm), exp_rest_flux_norm, np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        coadd_r = np.where(n_valid >= min_req, np.nanmedian(masked_r, axis=0), np.nan)
        coadd_fn = np.where(n_valid >= min_req, np.nanmedian(masked_fn, axis=0), np.nan)

    cands, s_bins, pre_f1 = scan_single_exposure_residual_lsf(
        rest_grid, coadd_r, cfg, channel="P", flux_norm_for_f1=coadd_fn, enforce_f1_in_g1=False
    )
    margin = max(65, int(round(4.5 / float(cfg["coadd_step_angstrom"]))))
    kept: list[dict[str, Any]] = []
    for h in cands:
        k = int(h["seed_index"])
        w0 = float(h["fitted_center_a"])
        sl = slice(max(0, k - margin), min(n_bins, k + margin + 1))
        n_hit = 0
        n_cov = 0
        for e_i in range(n_exp):
            ef = fit_lsf_on_window(rest_grid[sl], exp_rest_resids[e_i, sl], w0, cfg, fixed_phase_bins=h["phase_bins"])
            if ef.get("valid_fit"):
                n_cov += 1
                if ef["snr_mid"] >= 2.8:
                    n_hit += 1
        req_e = max(2, min(n_cov, max(min_req, int(math.ceil(cfg["channel_p_min_epoch_fraction"] * n_cov)))))
        h["p_epochs_above_2p8sig"] = n_hit
        h["p_epochs_covered"] = n_cov
        if n_hit >= req_e:
            kept.append(h)
    return coadd_r, coadd_fn, kept, s_bins, pre_f1


def build_and_scan_transit_channels(
    planet_grid: np.ndarray,
    unshifted_resids: np.ndarray,
    unshifted_fn: np.ndarray,
    dedoppler_resids: np.ndarray,
    dedoppler_fn: np.ndarray,
    out_resid_med: np.ndarray,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    with warnings.catch_warnings():
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
    margin = max(65, int(round(4.5 / float(cfg["coadd_step_angstrom"]))))

    def _keep_multi(c_list: list[dict[str, Any]], mat: np.ndarray, min_snr: float, min_frac: float) -> list[dict[str, Any]]:
        out = []
        for h in c_list:
            k = int(h["seed_index"])
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
# Step 4: Automated Physics Vetting Gates G2, G3, G4_V38, G5, G6_V36
# ---------------------------------------------------------------------------

def evaluate_gate_g2_airglow(
    fitted_bary_wave_a: float,
    berv_kms: float,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    topo_a = float(fitted_bary_wave_a / (1.0 + berv_kms / C_KMS))
    if cfg.get("instrument") == "HST_STIS":
        for band in STIS_GEOCORONAL_BANDS_VAC_A:
            if float(band["lo_A"]) <= topo_a <= float(band["hi_A"]):
                return {
                    "topo_wave_a": topo_a,
                    "nearest_airglow_name": band["name"],
                    "nearest_airglow_sep_a": 0.0,
                    "g2_pass": False,
                    "g2_reason": band["name"],
                }
        return {
            "topo_wave_a": topo_a,
            "nearest_airglow_name": "NONE",
            "nearest_airglow_sep_a": 999.0,
            "g2_pass": True,
            "g2_reason": "PASS",
        }

    for band in TELLURIC_SATURATED_BANDS_TOPO_A:
        if float(band["lo_A"]) <= topo_a <= float(band["hi_A"]):
            return {
                "topo_wave_a": topo_a,
                "nearest_airglow_name": band["name"],
                "nearest_airglow_sep_a": 0.0,
                "g2_pass": False,
                "g2_reason": f"TELLURIC_{band['name']}",
            }
    best_line = "NONE"
    best_sep = 1e9
    for item in TELLURIC_AIRGLOW_LINES_A:
        sep = abs(topo_a - float(item["wave_A"]))
        if sep < best_sep:
            best_sep, best_line = sep, item["name"]
    veto = best_sep <= cfg["gate_g2_airglow_tol_angstrom"]
    return {
        "topo_wave_a": topo_a,
        "nearest_airglow_name": best_line,
        "nearest_airglow_sep_a": float(best_sep),
        "g2_pass": not veto,
        "g2_reason": "PASS" if not veto else f"TELLURIC_AIRGLOW_{best_line}",
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
    if len(w) < 41 or not (np.all(np.isfinite(w)) and np.all(np.isfinite(f))):
        return {"usable": False}

    k_loc = int(np.argmin(np.abs(w - target_wave_a)))
    if k_loc < 15 or k_loc >= len(w) - 15:
        return {"usable": False}

    sb_mask = (np.abs(np.arange(len(w)) - k_loc) >= 12) & (np.abs(np.arange(len(w)) - k_loc) <= 70)
    q_cont = float(cfg["continuum_quantile_blue"]) if target_wave_a < float(cfg["continuum_blue_cutoff_angstrom"]) else float(cfg["continuum_quantile"])
    cont_q = exact_quantile_1d(f[sb_mask], q_cont)
    is_stis = cfg.get("instrument") == "HST_STIS"
    if not math.isfinite(cont_q):
        return {"usable": False}

    if is_stis:
        cont_raw = max(0.0, float(cont_q))
        e_floor = 1e-17
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
    else:
        if cont_q <= 0.0:
            return {"usable": False}
        cont_adu = float(cont_q)
        f_norm = f / cont_adu

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
    m_l = (idx >= -70) & (idx <= -12)
    m_r = (idx >= 12) & (idx <= 70)
    slope = (exact_median_1d(y[m_r]) - exact_median_1d(y[m_l])) / (
        exact_median_1d(idx[m_r].astype(np.float64)) - exact_median_1d(idx[m_l].astype(np.float64))
    )
    intercept = exact_median_1d(y[m_l | m_r] - slope * idx[m_l | m_r])
    det = y - (intercept + slope * idx)
    mad_sb = exact_mad_1d(det[m_l | m_r])
    if not math.isfinite(mad_sb) or mad_sb <= 0:
        return {"usable": False}

    sig_a = target_wave_a / (cfg["resolving_power"] * FWHM_FACTOR)
    core_sl = slice(max(0, k_loc - 6), min(len(w), k_loc + 7))
    g = np.exp(-0.5 * ((w[core_sl] - target_wave_a) / sig_a) ** 2)
    gg = float(g @ g)
    amp_rel = max(0.0, float(det[core_sl] @ g) / gg)
    snr_native = amp_rel / mad_sb

    template_dip_frac = 0.0
    if r_ref_clean is not None and amp_rel > 0.0:
        dv = C_KMS * (w - target_wave_a) / target_wave_a
        sig_v = float(cfg["sigma_v_kms"])
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
    step_px_a = float(exact_median_1d(np.diff(w[k_loc - 5 : k_loc + 6])))
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


def evaluate_g4_v38_fiber_b_bleed_record(
    dpr_or_calsel: str,
    fb_pk: float,
    fa_med: float,
    cfg: dict[str, Any] = BASE_V3_8_CONFIG,
) -> dict[str, Any]:
    """Direct G4_V38 Fiber-B simultaneous calibration etalon/lamp bleed test."""
    mode_u = (dpr_or_calsel or "").upper()
    is_cal = any(tok in mode_u for tok in ("WAVE", "FP", "THAR", "CAL"))
    ratio = float(fb_pk) / max(1e-6, float(fa_med))
    veto = bool(is_cal and ratio >= float(cfg["gate_g4_v38_fiber_b_over_a_cont_min"]))
    return {
        "g4_v38_pass": not veto,
        "fb_over_fa_cont": float(ratio),
        "g4_v38_reason": "FIBER_B_CALIBRATION_BLEED_V38" if veto else "PASS",
    }


def evaluate_gates_g3_g4_g5_v38(
    order_patches: list[dict[str, Any]],
    dpr_or_calsel: str,
    channel: str,
    star_rest_a: float | None,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    evaluated = []
    for p in order_patches:
        res = evaluate_native_order_patch(
            np.asarray(p["wave"], dtype=np.float64),
            np.asarray(p["flux_a"], dtype=np.float64),
            np.asarray(p["ref_norm_a"], dtype=np.float64) if p.get("ref_norm_a") is not None else None,
            float(p["target_wave_a"]),
            cfg,
            err_ord_win=np.asarray(p["err_a"], dtype=np.float64) if p.get("err_a") is not None else None,
        )
        if res.get("usable"):
            res["order"] = int(p["order"])
            res["native_pixel"] = int(p["native_pixel"])
            res["active_start_px"] = int(p.get("active_start_px", 0))
            res["active_end_px"] = int(p.get("active_end_px", 4095))
            res["flux_b"] = p.get("flux_b")
            res["bg_flux"] = p.get("bg_flux")
            res["net_a"] = p.get("net_a")
            res["dq"] = p.get("dq")
            res["raw_flux_a"] = p.get("flux_a")
            evaluated.append(res)

    if not evaluated:
        return {
            "g3_pass": False,
            "g3_reason": "NO_USABLE_NATIVE_ORDER",
            "g4_pass": False,
            "g4_reason": "NO_USABLE_NATIVE_ORDER",
            "g5_pass": False,
            "g5_reason": "NO_USABLE_NATIVE_ORDER",
            "n_covering_orders": 0,
        }

    evaluated.sort(key=lambda x: -x["continuum_adu"])
    prim = evaluated[0]

    # Gate G3: Native LSF + Supraphotospheric + Template-Dip + Optical/Far-Red & FUV Chromospheric Lines
    g3_reasons: list[str] = []
    if prim["native_snr"] < cfg["gate_g3_native_snr_min"]:
        g3_reasons.append("S1D_REBIN_OR_LOW_NATIVE_SNR")
    if prim["eta_1px"] > cfg["gate_g3_max_single_px_fraction"]:
        g3_reasons.append("SUB_LSF_SINGLE_PIXEL_SPIKE")
    if prim["min_wing_ratio"] < cfg["gate_g3_min_bilateral_wing_ratio"]:
        g3_reasons.append("ASYMMETRIC_COSMIC_RAY_SPIKE")
    if prim["native_fn_pk3"] < cfg["supraphotospheric_min_fn_pk3"]:
        g3_reasons.append("SUB_CONTINUUM_OR_TELLURIC_DIP_GHOST")
    if prim["template_dip_frac"] > cfg["gate_g3_max_template_dip_fraction"]:
        g3_reasons.append("TEMPLATE_ABSORPTION_DIP_GHOST")

    chromo_name = "NONE"
    chromo_sep = 1e9
    if star_rest_a is not None and math.isfinite(star_rest_a):
        cat = STELLAR_FUV_EMISSION_VAC_A if cfg.get("instrument") == "HST_STIS" else STELLAR_CHROMOSPHERIC_EMISSION_AIR_A
        tol = float(cfg["gate_g3_fuv_chromo_tol_angstrom"] if cfg.get("instrument") == "HST_STIS" else cfg["gate_g3_chromo_tol_angstrom"])
        for ch in cat:
            s = abs(float(star_rest_a) - float(ch["wave_A"]))
            if s < chromo_sep:
                chromo_sep, chromo_name = s, ch["name"]
        if chromo_sep <= tol:
            g3_reasons.append(f"CHROMOSPHERIC_OR_TR_LINE_{chromo_name}")

    # Gate G4_V38: Upgraded Fiber-B Bleed + HST STIS MAMA DQ/Background + UVES Slit-Sky + Adjacent Order
    g4_reasons: list[str] = []
    fiber_ab_tested = False
    fiber_b_ratio = 0.0
    fb = prim.get("flux_b")
    bgf = prim.get("bg_flux")
    dqf = prim.get("dq")

    if dqf is not None and cfg.get("instrument") == "HST_STIS":
        dq_arr = np.asarray(dqf, dtype=np.int64)
        k0 = prim["local_index"]
        sub_dq = dq_arr[max(0, k0 - 1) : min(len(dq_arr), k0 + 2)]
        # Exclude minor small-blemish flag 1024; veto bad pixels, vignetting, saturation, etc.
        if any((int(dv) & ~1024) != 0 for dv in sub_dq):
            g4_reasons.append("STIS_MAMA_DQ_FLAG")

    if fb is not None:
        fb_arr = np.asarray(fb, dtype=np.float64)
        fa_arr = np.asarray(prim["raw_flux_a"], dtype=np.float64)
        if len(fb_arr) >= 41 and np.all(np.isfinite(fb_arr)):
            fiber_ab_tested = True
            k0 = len(fb_arr) // 2
            sb_b = np.r_[fb_arr[max(0, k0 - 60) : max(0, k0 - 10)], fb_arr[min(len(fb_arr), k0 + 11) : min(len(fb_arr), k0 + 61)]]
            if len(sb_b) >= 10:
                med_b = exact_median_1d(sb_b)
                mad_b = max(1e-6, exact_mad_1d(sb_b))
                pk_b_sb = float(np.max(fb_arr[max(0, k0 - 2) : min(len(fb_arr), k0 + 3)]) - med_b)
                pk_b_abs = float(np.max(fb_arr[max(0, k0 - 3) : min(len(fb_arr), k0 + 4)]))
                fa_med = max(1e-6, exact_median_1d(fa_arr[np.isfinite(fa_arr)]))
                fiber_b_ratio = pk_b_sb / max(1e-6, prim["native_amp_adu"])
                mode_u = (dpr_or_calsel or "").upper()
                if any(tok in mode_u for tok in ("WAVE", "FP", "THAR", "CAL")):
                    g4_38 = evaluate_g4_v38_fiber_b_bleed_record(dpr_or_calsel, pk_b_abs, fa_med, cfg)
                    if not g4_38["g4_v38_pass"]:
                        g4_reasons.append("FIBER_B_CALIBRATION_BLEED_V38")
                    elif (pk_b_sb > cfg["gate_g4_fiber_b_wave_bleed_mad_mult"] * mad_b) and (fiber_b_ratio > cfg["gate_g4_fiber_b_wave_over_a_ratio"]):
                        g4_reasons.append("FIBER_B_CALIBRATION_BLEED")
                elif "SKY" in mode_u:
                    if (pk_b_sb / mad_b >= 4.0) and (fiber_b_ratio >= cfg["gate_g4_fiber_b_sky_ratio_max"]):
                        g4_reasons.append("FIBER_B_SKY_EMISSION")
    elif bgf is not None:
        bg_arr = np.asarray(bgf, dtype=np.float64)
        if len(bg_arr) >= 41 and np.all(np.isfinite(bg_arr)):
            fiber_ab_tested = True
            k0 = len(bg_arr) // 2
            sb_g = np.r_[bg_arr[max(0, k0 - 60) : max(0, k0 - 10)], bg_arr[min(len(bg_arr), k0 + 11) : min(len(bg_arr), k0 + 61)]]
            if len(sb_g) >= 10:
                med_g = exact_median_1d(sb_g)
                mad_g = max(1e-9, exact_mad_1d(sb_g))
                pk_g = float(np.max(bg_arr[max(0, k0 - 2) : min(len(bg_arr), k0 + 3)]) - med_g)
                if cfg.get("instrument") == "HST_STIS" and prim.get("net_a") is not None:
                    net_arr = np.asarray(prim["net_a"], dtype=np.float64)
                    sb_n = np.r_[net_arr[max(0, k0 - 60) : max(0, k0 - 10)], net_arr[min(len(net_arr), k0 + 11) : min(len(net_arr), k0 + 61)]]
                    med_n = exact_median_1d(sb_n) if len(sb_n) >= 6 else 0.0
                    pk_net = max(1e-6, float(np.max(net_arr[max(0, k0 - 2) : min(len(net_arr), k0 + 3)]) - med_n))
                    fiber_b_ratio = pk_g / pk_net
                    if (pk_g / mad_g >= 5.0) and (fiber_b_ratio >= cfg["gate_g4_stis_bg_over_net_max"]):
                        g4_reasons.append("STIS_MAMA_SLIT_BACKGROUND")
                else:
                    fiber_b_ratio = pk_g / max(1e-6, prim["native_amp_adu"])
                    if (pk_g / mad_g >= 5.0) and (fiber_b_ratio >= cfg["gate_g4_uves_sky_slit_ratio_max"]):
                        g4_reasons.append("UVES_SLIT_SKY_EMISSION")

    margin_ov = int(cfg["gate_g4_overlap_edge_margin_px"])
    qual_orders = [
        e for e in evaluated
        if ((e["active_start_px"] + margin_ov) <= e["native_pixel"] <= (e["active_end_px"] - margin_ov))
        and (e["continuum_adu"] >= cfg["gate_g4_secondary_flux_ratio_min"] * prim["continuum_adu"])
        and (e["continuum_snr"] >= cfg["gate_g4_secondary_cont_snr_min"])
    ]
    dedup_qual = []
    seen_o = set()
    for qo in qual_orders:
        if qo["order"] not in seen_o:
            dedup_qual.append(qo)
            seen_o.add(qo["order"])
    overlap_tested = len(dedup_qual) >= 2 and (dedup_qual[0]["order"] == prim["order"])
    if overlap_tested:
        sec = dedup_qual[1]
        sc_r = sec["native_amp_rel"] / max(1e-12, prim["native_amp_rel"])
        if sec["native_snr"] < cfg["gate_g4_secondary_snr_min"] or not (cfg["gate_g4_order_contrast_ratio_min"] <= sc_r <= cfg["gate_g4_order_contrast_ratio_max"]):
            g4_reasons.append("SINGLE_ORDER_DETECTOR_ARTIFACT")

    # Gate G5: 1D 11-px native LSF cosine + cosmic hot-px concentration + far-wing plateau
    g5_reasons: list[str] = []
    if prim["cos_1d_11px"] < cfg["gate_g5_cos11_min"]:
        g5_reasons.append("G5_LSF_COSINE_MISMATCH")
    if prim["ipc_hotpx_ratio"] > cfg["gate_g5_ipc_hotpx_max_ratio"]:
        g5_reasons.append("G5_SINGLE_PIXEL_COSMIC_SPIKE")
    if prim["far_wing_34_ratio"] > cfg["gate_g5_far_wing_34_max"]:
        g5_reasons.append("G5_WIDE_WING_PLATEAU")

    return {
        "n_covering_orders": len(seen_o) if seen_o else len(evaluated),
        "primary_order": prim["order"],
        "primary_native_px": prim["native_pixel"],
        "primary_continuum_adu": prim["continuum_adu"],
        "primary_continuum_snr": prim["continuum_snr"],
        "primary_native_fn_pk3": prim["native_fn_pk3"],
        "primary_template_dip_frac": prim["template_dip_frac"],
        "primary_native_snr": prim["native_snr"],
        "primary_eta_1px": prim["eta_1px"],
        "primary_min_wing_ratio": prim["min_wing_ratio"],
        "chromo_line_name": chromo_name,
        "chromo_sep_a": float(chromo_sep) if chromo_sep < 1e8 else 999.0,
        "g3_pass": len(g3_reasons) == 0,
        "g3_reason": "PASS" if not g3_reasons else ";".join(g3_reasons),
        "fiber_ab_tested": fiber_ab_tested,
        "fiber_ab_amp_ratio": float(fiber_b_ratio),
        "overlap_tested": bool(overlap_tested),
        "g4_pass": len(g4_reasons) == 0,
        "g4_reason": "PASS" if not g4_reasons else ";".join(g4_reasons),
        "cos_1d_11px": prim["cos_1d_11px"],
        "ipc_hotpx_ratio": prim["ipc_hotpx_ratio"],
        "far_wing_34_ratio": prim["far_wing_34_ratio"],
        "g5_pass": len(g5_reasons) == 0,
        "g5_reason": "PASS" if not g5_reasons else ";".join(g5_reasons),
    }


def evaluate_gate_g6_v35_dense(
    target_star: str,
    topo_wave_a: float,
    primary_order: int | None,
    primary_px: int | None,
    target_vshift_kms: float,
    dense_atlas: list[dict[str, Any]],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    tol_a = float(cfg["gate_g6_topo_tol_a"])
    tol_px = int(cfg["gate_g6_native_px_tol"])
    min_stars = int(cfg["gate_g6_min_distinct_stars"])

    coin_stars: set[str] = set()
    for p in dense_atlas:
        s2 = p["star"]
        if s2 == target_star:
            continue
        if abs(float(p["topo_wave_a"]) - topo_wave_a) <= tol_a:
            coin_stars.add(s2)
        elif primary_order is not None and primary_px is not None and p.get("order") == primary_order and p.get("px") is not None and abs(int(p["px"]) - int(primary_px)) <= tol_px:
            coin_stars.add(s2)
    pass_d = len(coin_stars) < min_stars
    return {
        "g6_v35_pass": pass_d,
        "g6_v35_coincident_total_stars": len(coin_stars),
        "g6_v35_reason": "PASS" if pass_d else "DENSE_ATLAS_COINCIDENCE",
    }


def evaluate_gate_g6_v36_sparse(
    target_star: str,
    target_dp_id: str,
    target_berv_kms: float,
    topo_wave_a: float,
    primary_order: int | None,
    primary_px: int | None,
    target_vshift_kms: float,
    sparse_atlas: list[dict[str, Any]],
    cfg: dict[str, Any],
    channel: str,
) -> dict[str, Any]:
    tol_a = float(cfg["gate_g6_topo_tol_a"])
    tol_px = int(cfg["gate_g6_native_px_tol"])
    min_stars = int(cfg["gate_g6_min_distinct_stars"])
    berv_sep = float(cfg["gate_g6_intra_star_berv_sep_kms"])

    coin_stars: set[str] = set()
    same_star_hits = 0
    for p in sparse_atlas:
        s2 = p["star"]
        same_t = abs(float(p["topo_wave_a"]) - topo_wave_a) <= tol_a
        same_px = (
            primary_order is not None
            and primary_px is not None
            and p.get("order") == primary_order
            and p.get("px") is not None
            and abs(int(p["px"]) - int(primary_px)) <= tol_px
        )
        if not (same_t or same_px):
            continue
        if s2 == target_star:
            if p.get("dp_id") != target_dp_id and abs(float(p["berv_kms"]) - target_berv_kms) >= berv_sep:
                same_star_hits += 1
        else:
            coin_stars.add(s2)

    veto = (len(coin_stars) >= min_stars) or (same_star_hits >= 1 and channel in ("T", "K_PLANET"))
    if len(coin_stars) >= min_stars:
        rsn = "G6_SPARSE_NONLOCAL_COINCIDENCE"
    elif same_star_hits >= 1 and channel in ("T", "K_PLANET"):
        rsn = "G6_INTRA_STAR_STATIONARY_GHOST"
    else:
        rsn = "PASS"
    return {
        "g6_pass": not veto,
        "g6_coincident_total_stars": len(coin_stars),
        "g6_same_star_stationary_hits": same_star_hits,
        "g6_reason": rsn,
    }


# ---------------------------------------------------------------------------
# Step 5: COMB_V4 and COMB_V4_1 Coherent M=6 Frequency-Comb Scanners
# ---------------------------------------------------------------------------

def _build_freq_band_vectors(
    bary_grid: np.ndarray,
    y_rest: np.ndarray,
    sigma_rest: np.ndarray,
    flux_norm: np.ndarray,
    recon_arr: np.ndarray,
    sky_mask: np.ndarray,
    lo_a: float,
    hi_a: float,
    df_ghz: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    nu_lo = math.ceil((C_ANGSTROM_GHZ / hi_a) / df_ghz) * df_ghz
    nu_hi = math.floor((C_ANGSTROM_GHZ / lo_a) / df_ghz) * df_ghz
    nu_grid = np.arange(nu_lo, nu_hi + 0.1 * df_ghz, df_ghz, dtype=np.float64)
    w_of_nu = C_ANGSTROM_GHZ / nu_grid
    z_raw = np.where(np.isfinite(y_rest) & np.isfinite(sigma_rest) & (sigma_rest > 0.0), y_rest / sigma_rest, -9.0)
    z_nu = np.interp(w_of_nu, bary_grid, z_raw)
    fn_nu = np.interp(w_of_nu, bary_grid, np.where(np.isfinite(flux_norm), flux_norm, 1.0))
    rc_nu = np.interp(w_of_nu, bary_grid, np.where(np.isfinite(recon_arr), recon_arr, 0.0))
    fin_nu = np.interp(w_of_nu, bary_grid, np.isfinite(y_rest).astype(np.float64)) > 0.85
    sky_nu = np.interp(w_of_nu, bary_grid, sky_mask.astype(np.float64)) > 0.25
    clean_nu = fin_nu & (~sky_nu) & (rc_nu >= 0.78)
    z_nu = np.where(clean_nu, z_nu, -9.0)
    return nu_grid, z_nu, fn_nu, rc_nu, clean_nu


def _scan_comb_core(
    bary_grid: np.ndarray,
    y_rest_stack: np.ndarray,
    sigma_rest_stack: np.ndarray,
    flux_norm_stack: np.ndarray,
    recon_stack: np.ndarray,
    sky_mask_bary: np.ndarray,
    y_topo_stack: np.ndarray | None,
    sigma_topo_stack: np.ndarray | None,
    windows_list: list[dict[str, Any]],
    search_bands: list[str],
    cfg: dict[str, Any],
    enable_v41_filters: bool,
) -> tuple[list[dict[str, Any]], int]:
    df_ghz = float(cfg["comb_freq_step_ghz"])
    m_teeth = int(cfg["comb_n_teeth"])
    min_qual = int(cfg["comb_min_qualifying_teeth"])
    z_min = float(cfg["comb_tooth_z_min"])
    z_cap = float(cfg["comb_tooth_z_cap"])
    fn_min = float(cfg["comb_tooth_fn_min"])
    rc_min = float(cfg["comb_tooth_recon_min"])
    s_min = float(cfg["comb_score_min"])
    dom_max = float(cfg["comb_max_tooth_frac"])
    anti_max = float(cfg["comb_topo_anti_ratio_max"])
    off_crowd_max = float(cfg["comb_v41_off_tooth_crowding_max"])
    inter_max_ratio = float(cfg["comb_v41_intertooth_max_ratio"])
    tol_bins = 2

    win_by_name = {w["band"]: w for w in windows_list}
    all_cands: list[dict[str, Any]] = []
    searched_configs = 0

    for bname in search_bands:
        if bname not in win_by_name:
            continue
        win = win_by_name[bname]
        nu_g, z_nu, fn_nu, rc_nu, cln_nu = _build_freq_band_vectors(
            bary_grid, y_rest_stack, sigma_rest_stack, flux_norm_stack, recon_stack, sky_mask_bary,
            float(win["lo_a"]), float(win["hi_a"]), df_ghz,
        )
        if y_topo_stack is not None and sigma_topo_stack is not None:
            _, z_topo_nu, _, _, _ = _build_freq_band_vectors(
                bary_grid, y_topo_stack, sigma_topo_stack, np.ones_like(y_topo_stack), np.ones_like(y_topo_stack),
                np.zeros_like(sky_mask_bary), float(win["lo_a"]), float(win["hi_a"]), df_ghz,
            )
        else:
            z_topo_nu = np.zeros_like(z_nu)

        n_nu = len(nu_g)
        z_max = z_nu.copy()
        fn_max = fn_nu.copy()
        rc_max = rc_nu.copy()
        zt_max = z_topo_nu.copy()
        for sh in range(-tol_bins, tol_bins + 1):
            if sh == 0:
                continue
            z_sh = np.roll(z_nu, sh)
            fn_sh = np.roll(fn_nu, sh)
            rc_sh = np.roll(rc_nu, sh)
            if sh > 0:
                z_sh[:sh] = -9.0
            else:
                z_sh[n_nu + sh :] = -9.0
            better = z_sh > z_max
            z_max = np.where(better, z_sh, z_max)
            fn_max = np.where(better, fn_sh, fn_max)
            rc_max = np.where(better, rc_sh, rc_max)
            zt_max = np.maximum(zt_max, np.roll(z_topo_nu, sh))

        z_cap_arr = np.clip(np.maximum(0.0, z_max), 0.0, z_cap)
        qual_arr = (z_max >= z_min) & (fn_max >= fn_min) & (rc_max >= rc_min)

        for dnu_ghz in cfg["comb_spacings_ghz"]:
            step_idx = int(round(float(dnu_ghz) / df_ghz))
            span = (m_teeth - 1) * step_idx
            if n_nu <= span + 20:
                continue
            m_valid_end = n_nu - span - 10
            idx0 = np.arange(10, m_valid_end, dtype=np.int64)
            searched_configs += len(idx0)

            tooth_z = np.stack([z_cap_arr[idx0 + t * step_idx] for t in range(m_teeth)], axis=0)
            tooth_q = np.stack([qual_arr[idx0 + t * step_idx] for t in range(m_teeth)], axis=0)
            tooth_zt = np.stack([np.clip(np.maximum(0.0, zt_max[idx0 + t * step_idx]), 0.0, z_cap) for t in range(m_teeth)], axis=0)

            sum_z = np.sum(tooth_z, axis=0)
            s_comb = sum_z / math.sqrt(m_teeth)
            n_q = np.sum(tooth_q, axis=0)
            dom_frac = np.max(tooth_z, axis=0) / np.maximum(1e-9, sum_z)
            s_topo = np.sum(tooth_zt, axis=0) / math.sqrt(m_teeth)

            hits = np.flatnonzero((n_q >= min_qual) & (s_comb >= s_min) & (dom_frac <= dom_max))
            for h_i in hits:
                k_start = int(idx0[h_i])
                sc = float(s_comb[h_i])
                st_sc = float(s_topo[h_i])
                anti_ratio = st_sc / max(1e-9, sc)
                if anti_ratio > anti_max:
                    continue

                ks = [k_start + t * step_idx for t in range(m_teeth)]
                off_frac_gt2 = 0.0
                inter_ratio = 0.0
                if enable_v41_filters:
                    lo_b = max(0, k_start - 30)
                    hi_b = min(n_nu, ks[-1] + 31)
                    mask_t = np.zeros(hi_b - lo_b, dtype=bool)
                    for kt in ks:
                        mask_t[max(0, kt - lo_b - 6) : min(hi_b - lo_b, kt - lo_b + 7)] = True
                    off_z = z_nu[lo_b:hi_b][cln_nu[lo_b:hi_b] & (~mask_t)]
                    off_frac_gt2 = float(np.mean(off_z >= 2.2)) if len(off_z) >= 20 else 0.0
                    if off_frac_gt2 > off_crowd_max:
                        continue

                    inter_scores = []
                    for ph in (0.25, 0.50, 0.75):
                        off_st = int(round(ph * step_idx))
                        iks = [kt + off_st for kt in ks if 0 <= kt + off_st < n_nu]
                        if len(iks) == m_teeth:
                            inter_scores.append(float(np.sum(z_cap_arr[iks])) / math.sqrt(m_teeth))
                    inter_ratio = (max(inter_scores) / max(1e-9, sc)) if inter_scores else 0.0
                    if inter_ratio > inter_max_ratio:
                        continue

                nu0 = float(nu_g[k_start])
                w_teeth_a = [round(C_ANGSTROM_GHZ / (nu0 + t * float(dnu_ghz)), 3) for t in range(m_teeth)]
                all_cands.append({
                    "band": bname,
                    "dnu_ghz": float(dnu_ghz),
                    "nu0_ghz": round(nu0, 3),
                    "nu_end_ghz": round(nu0 + (m_teeth - 1) * float(dnu_ghz), 3),
                    "wave0_a": w_teeth_a[0],
                    "wave_end_a": w_teeth_a[-1],
                    "s_comb": round(sc, 4),
                    "s_comb_topo": round(st_sc, 4),
                    "topo_anti_ratio": round(anti_ratio, 4),
                    "n_qualifying_teeth": int(n_q[h_i]),
                    "max_tooth_frac": round(float(dom_frac[h_i]), 4),
                    "off_tooth_crowding": round(off_frac_gt2, 4),
                    "intertooth_ratio": round(inter_ratio, 4),
                    "tooth_z_caps": [round(float(tooth_z[t, h_i]), 3) for t in range(m_teeth)],
                    "teeth_a": w_teeth_a,
                })

    dedup: list[dict[str, Any]] = []
    for c in sorted(all_cands, key=lambda x: (-x["s_comb"], x["dnu_ghz"], x["nu0_ghz"])):
        is_dup = False
        for p in dedup:
            if p["band"] != c["band"]:
                continue
            ovlp = min(p["nu_end_ghz"], c["nu_end_ghz"]) - max(p["nu0_ghz"], c["nu0_ghz"])
            if ovlp >= -0.5 * min(p["dnu_ghz"], c["dnu_ghz"]):
                if abs(p["dnu_ghz"] - c["dnu_ghz"]) < 1e-3 and abs(p["nu0_ghz"] - c["nu0_ghz"]) <= 0.5 * c["dnu_ghz"]:
                    is_dup = True
                    break
                if enable_v41_filters:
                    r_hi = max(p["dnu_ghz"], c["dnu_ghz"]) / max(1e-6, min(p["dnu_ghz"], c["dnu_ghz"]))
                    if abs(r_hi - round(r_hi)) <= 0.02 and round(r_hi) >= 2:
                        is_dup = True
                        break
        if not is_dup:
            dedup.append(c)
    return dedup, searched_configs


def scan_frequency_comb_v4(
    bary_grid: np.ndarray,
    y_rest_stack: np.ndarray,
    sigma_rest_stack: np.ndarray,
    flux_norm_stack: np.ndarray,
    recon_stack: np.ndarray,
    sky_mask_bary: np.ndarray,
    y_topo_stack: np.ndarray | None,
    sigma_topo_stack: np.ndarray | None,
    windows_list: list[dict[str, Any]],
    search_bands: list[str],
    cfg: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    return _scan_comb_core(
        bary_grid, y_rest_stack, sigma_rest_stack, flux_norm_stack, recon_stack,
        sky_mask_bary, y_topo_stack, sigma_topo_stack, windows_list, search_bands,
        cfg, enable_v41_filters=False,
    )


def scan_frequency_comb_v4_1(
    bary_grid: np.ndarray,
    y_rest_stack: np.ndarray,
    sigma_rest_stack: np.ndarray,
    flux_norm_stack: np.ndarray,
    recon_stack: np.ndarray,
    sky_mask_bary: np.ndarray,
    y_topo_stack: np.ndarray | None,
    sigma_topo_stack: np.ndarray | None,
    windows_list: list[dict[str, Any]],
    search_bands: list[str],
    cfg: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    return _scan_comb_core(
        bary_grid, y_rest_stack, sigma_rest_stack, flux_norm_stack, recon_stack,
        sky_mask_bary, y_topo_stack, sigma_topo_stack, windows_list, search_bands,
        cfg, enable_v41_filters=True,
    )


# ---------------------------------------------------------------------------
# Step 6: Direct CALSTIS FUV, Dual G_RP / 2MASS J, & Gaia G Radiometric Limits
# ---------------------------------------------------------------------------

def resolve_band_radiometric_anchor(instrument: str, wave_a: float) -> str:
    iu = instrument.upper()
    if iu == "HST_STIS":
        return "HST_CALSTIS_DIRECT_FLAM"
    if iu == "UVES_RED":
        return "GAIA_DR3_GRP" if float(wave_a) < RADIOMETRIC_RPJ_SPLIT_A else "TWOMASS_J"
    return "GAIA_DR3_G"


def compute_photon_beam_upper_limit(
    wave_a: float,
    amp_rel_8sigma_lim: float,
    teff_k: float,
    dist_pc: float,
    mag: float,
    radiometric_anchor: str,
    resolving_power: float,
    d_tx_m: float = 10.0,
    direct_flam_cgs: float | None = None,
) -> dict[str, float]:
    if radiometric_anchor == "HST_CALSTIS_DIRECT_FLAM":
        if direct_flam_cgs is None or not math.isfinite(direct_flam_cgs) or direct_flam_cgs <= 0.0:
            raise ValueError("HST_CALSTIS_DIRECT_FLAM requires positive direct_flam_cgs")
        flam = float(direct_flam_cgs)
    else:
        if radiometric_anchor == "GAIA_DR3_GRP":
            piv, zp = GAIA_GRP_PIVOT_A, GAIA_GRP_ZP_FLAM
        elif radiometric_anchor == "TWOMASS_J":
            piv, zp = TWOMASS_J_PIVOT_A, TWOMASS_J_ZP_FLAM
        elif radiometric_anchor == "GAIA_DR3_GBP":
            piv, zp = GAIA_GBP_PIVOT_A, GAIA_GBP_ZP_FLAM
        else:
            piv, zp = GAIA_G_PIVOT_A, GAIA_G_ZP_FLAM
        b_rat = ((piv / wave_a) ** 5) * math.expm1(HC_OVER_K_ANGSTROM_KELVIN / (piv * teff_k)) / math.expm1(
            HC_OVER_K_ANGSTROM_KELVIN / (wave_a * teff_k)
        )
        flam = zp * (10.0 ** (-0.4 * mag)) * b_rat

    fwhm_a = wave_a / resolving_power
    ew_a = math.sqrt(math.pi / (4.0 * math.log(2.0))) * amp_rel_8sigma_lim * fwhm_a
    ew_ma = ew_a * 1000.0
    flux_cgs = flam * ew_a
    l_iso_w = 4.0 * math.pi * ((dist_pc * PC_CM) ** 2) * flux_cgs * 1e-7
    theta = (math.pi * d_tx_m) / (wave_a * 1e-10)
    p_beam_w = l_iso_w / (theta * theta)
    return {
        "fwhm_lsf_a": fwhm_a,
        "ew_lim_mA": ew_ma,
        "continuum_flam_cgs": flam,
        "flux_lim_erg_cm2_s": flux_cgs,
        "l_iso_mw": l_iso_w / 1e6,
        "p_beam_10m_w": p_beam_w,
        "p_beam_10m_kw": p_beam_w / 1000.0,
    }
