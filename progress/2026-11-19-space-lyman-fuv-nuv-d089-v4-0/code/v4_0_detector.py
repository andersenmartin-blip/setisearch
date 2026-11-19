#!/usr/bin/env python3
"""Prospective detector specification for Phase D089 (`SPACE_LYMAN_FUV_NUV_V4_0`).

Extends the D079-D088 V3.9/COMB_V4_1 survey (12 spectrographs / 13 arms,
0.1145-2.515 um, 4.457 octaves) to 14 spectrographs / 16 arms spanning
4.797 spectral octaves (0.0905-2.515 um vacuum) by adding 3 space-UV arms:

1. `FUSE_FUV` (0.0905-0.1187 um vacuum, R=20,000): breaks the 0.10 um Lyman
   limit across CalFUSE 8-channel spectra (`1ALIF..2ASIC`), enforcing
   dual-telescope optical-channel coincidence (`LiF1<->LiF2`, `SiC1<->SiC2`)
   in Gate G4_V40 alongside direct `FUSE_CALFUSE_DIRECT_FLAM` radiometry.
2. `HST_COS_FUV` (G130M, 0.1125-0.1450 um vacuum, R=18,000): deep space-FUV
   survey of transiting exoplanet hosts & solar-neighborhood targets with
   COS/FUV `DQ` + `DQ_WGT` + `BACKGROUND/NET` gating in Gate G4_V40 and
   direct `HST_CALCOS_DIRECT_FLAM` radiometry.
3. `HST_STIS_NUV` (E230M R=30,000 / E230H R=114,000, 0.1605-0.3150 um vac):
   100% closes the final UV gap (0.1710-0.3050 um) between HST_STIS E140M
   (D087) and VLT UVES_NUV (D086) with CALSTIS MAMA `DQ`/`BACKGROUND/NET`
   gating, echelle order-overlap checks, and `HST_CALSTIS_DIRECT_FLAM` limits.
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

# Radiometric constants (used for pure-stdlib chains & ground/space conversions)
GAIA_GBP_PIVOT_A = 5109.7121
GAIA_GBP_ZP_FLAM = 4.078518e-9
GAIA_G_PIVOT_A = 6217.6
GAIA_G_ZP_FLAM = 2.50386e-9
GAIA_GRP_PIVOT_A = 7769.0
GAIA_GRP_ZP_FLAM = 1.29303e-9
TWOMASS_J_PIVOT_A = 12350.0
TWOMASS_J_ZP_FLAM = 3.129e-10
JOHNSON_V_PIVOT_A = 5450.0
JOHNSON_V_ZP_FLAM = 3.631e-9

HC_OVER_K_ANGSTROM_KELVIN = 1.438776877e8
PC_CM = 3.0856775814913673e18
G_SI = 6.67430e-11
M_SUN_KG = 1.98847e30
DAY_S = 86400.0

# Severe COS FUV DQ bitmask: fatal/gain-sag/dead/burst/bad-time bits
# Allow bit 0 (good), 1024 (small blemish), 16384 (pixel in glow/gain-sag buffer when DQ_WGT>0)
COS_FATAL_DQ_MASK = 2 | 4 | 8 | 16 | 32 | 64 | 128 | 256 | 512 | 2048 | 4096 | 8192 | 32768
STIS_FATAL_DQ_MASK = ~1024

# ---------------------------------------------------------------------------
# Locked NIST Vacuum Wavelengths for RV Anchors (FUSE, COS, STIS NUV)
# ---------------------------------------------------------------------------

LOCKED_RV_ANCHORS_FUSE = [
    {"anchor_id": "CIII_977p020", "species": "C III", "lab_wave_A": 977.020},
    {"anchor_id": "NIII_989p799", "species": "N III", "lab_wave_A": 989.799},
    {"anchor_id": "OVI_1031p926", "species": "O VI", "lab_wave_A": 1031.926},
    {"anchor_id": "CII_1036p337", "species": "C II", "lab_wave_A": 1036.337},
    {"anchor_id": "OVI_1037p617", "species": "O VI", "lab_wave_A": 1037.617},
    {"anchor_id": "SiIII_1113p230", "species": "Si III", "lab_wave_A": 1113.230},
    {"anchor_id": "FeIII_1122p526", "species": "Fe III", "lab_wave_A": 1122.526},
    {"anchor_id": "CIII_1175p711", "species": "C III", "lab_wave_A": 1175.711},
]

LOCKED_RV_ANCHORS_COS_FUV = [
    {"anchor_id": "CIII_1175p711", "species": "C III", "lab_wave_A": 1175.711},
    {"anchor_id": "SiIII_1206p500", "species": "Si III", "lab_wave_A": 1206.500},
    {"anchor_id": "NV_1238p821", "species": "N V", "lab_wave_A": 1238.821},
    {"anchor_id": "NV_1242p804", "species": "N V", "lab_wave_A": 1242.804},
    {"anchor_id": "SiII_1264p738", "species": "Si II", "lab_wave_A": 1264.738},
    {"anchor_id": "CII_1334p532", "species": "C II", "lab_wave_A": 1334.532},
    {"anchor_id": "CII_1335p708", "species": "C II", "lab_wave_A": 1335.708},
    {"anchor_id": "SiIV_1393p755", "species": "Si IV", "lab_wave_A": 1393.755},
    {"anchor_id": "SiIV_1402p770", "species": "Si IV", "lab_wave_A": 1402.770},
]

LOCKED_RV_ANCHORS_STIS_NUV = [
    {"anchor_id": "AlII_1670p787", "species": "Al II", "lab_wave_A": 1670.787},
    {"anchor_id": "SiII_1808p013", "species": "Si II", "lab_wave_A": 1808.013},
    {"anchor_id": "AlIII_1854p716", "species": "Al III", "lab_wave_A": 1854.716},
    {"anchor_id": "FeII_2344p214", "species": "Fe II", "lab_wave_A": 2344.214},
    {"anchor_id": "FeII_2382p765", "species": "Fe II", "lab_wave_A": 2382.765},
    {"anchor_id": "FeII_2586p650", "species": "Fe II", "lab_wave_A": 2586.650},
    {"anchor_id": "FeII_2600p173", "species": "Fe II", "lab_wave_A": 2600.173},
    {"anchor_id": "MgII_2796p352", "species": "Mg II", "lab_wave_A": 2796.352},
    {"anchor_id": "MgII_2803p531", "species": "Mg II", "lab_wave_A": 2803.531},
    {"anchor_id": "MgI_2852p964", "species": "Mg I", "lab_wave_A": 2852.964},
]

# ---------------------------------------------------------------------------
# Gate G2_V40: Space-LEO Geocoronal Airglow Bands (Observatory Vacuum A)
# ---------------------------------------------------------------------------

FUSE_GEOCORONAL_BANDS_VAC_A = [
    {"name": "GEOCORONA_HI_LyEps_937", "lo_A": 937.0, "hi_A": 938.5},
    {"name": "GEOCORONA_HI_LyDel_949", "lo_A": 949.0, "hi_A": 950.5},
    {"name": "GEOCORONA_HI_LyGam_972", "lo_A": 971.5, "hi_A": 973.5},
    {"name": "GEOCORONA_OI_989", "lo_A": 987.5, "hi_A": 991.5},
    {"name": "GEOCORONA_HI_LyBeta_1025", "lo_A": 1024.0, "hi_A": 1027.5},
    {"name": "GEOCORONA_OI_1040", "lo_A": 1038.5, "hi_A": 1042.5},
    {"name": "GEOCORONA_NI_1134", "lo_A": 1133.5, "hi_A": 1136.0},
    {"name": "GEOCORONA_HeI_NI_1168", "lo_A": 1167.0, "hi_A": 1170.0},
]

COS_GEOCORONAL_BANDS_VAC_A = [
    {"name": "GEOCORONA_NI_1134", "lo_A": 1133.5, "hi_A": 1136.0},
    {"name": "GEOCORONA_NI_1200", "lo_A": 1199.0, "hi_A": 1201.5},
    {"name": "GEOCORONA_HI_LyAlpha", "lo_A": 1205.5, "hi_A": 1225.5},
    {"name": "GEOCORONA_OI_1302", "lo_A": 1300.5, "hi_A": 1307.5},
    {"name": "GEOCORONA_OI_1356", "lo_A": 1354.5, "hi_A": 1359.5},
]

STIS_NUV_GEOCORONAL_BANDS_VAC_A = [
    {"name": "GEOCORONA_OII_2471", "lo_A": 2469.5, "hi_A": 2472.5},
]

# Keep airglow tables from D088 for singleline forensic continuity if needed
TELLURIC_AIRGLOW_LINES_A: list[dict[str, Any]] = []
TELLURIC_SATURATED_BANDS_TOPO_A: list[dict[str, Any]] = []

# ---------------------------------------------------------------------------
# Gate G3_V40: Stellar Chromospheric & Transition-Region Emission (Vac A)
# ---------------------------------------------------------------------------

STELLAR_UV_EMISSION_VAC_A = [
    # FUSE Lyman / TR / Coronal (0.0905-0.1187 um)
    {"name": "CIII_977", "wave_A": 977.020},
    {"name": "NIII_989", "wave_A": 989.799},
    {"name": "NIII_991", "wave_A": 991.577},
    {"name": "HI_LyBeta_1025", "wave_A": 1025.722},
    {"name": "OVI_1031", "wave_A": 1031.926},
    {"name": "CII_1036", "wave_A": 1036.337},
    {"name": "CII_1037", "wave_A": 1037.018},
    {"name": "OVI_1037", "wave_A": 1037.617},
    {"name": "SIV_1062", "wave_A": 1062.662},
    {"name": "SIV_1073", "wave_A": 1072.973},
    {"name": "SiIII_1113", "wave_A": 1113.230},
    {"name": "FeIII_1122", "wave_A": 1122.526},
    {"name": "CIII_1175", "wave_A": 1175.711},
    # COS / STIS FUV (0.1125-0.1710 um)
    {"name": "SiIII_1206", "wave_A": 1206.500},
    {"name": "HI_LyA_1215", "wave_A": 1215.670},
    {"name": "OV_1218", "wave_A": 1218.344},
    {"name": "NV_1238", "wave_A": 1238.821},
    {"name": "NV_1242", "wave_A": 1242.804},
    {"name": "SiII_1260", "wave_A": 1260.422},
    {"name": "SiII_1264", "wave_A": 1264.738},
    {"name": "OI_1302", "wave_A": 1302.168},
    {"name": "OI_1304", "wave_A": 1304.858},
    {"name": "OI_1306", "wave_A": 1306.029},
    {"name": "CII_1334", "wave_A": 1334.532},
    {"name": "CII_1335", "wave_A": 1335.708},
    {"name": "ClI_1351", "wave_A": 1351.656},
    {"name": "OI_1355", "wave_A": 1355.598},
    {"name": "OV_1371", "wave_A": 1371.296},
    {"name": "SiIV_1393", "wave_A": 1393.755},
    {"name": "OIV_1401", "wave_A": 1401.157},
    {"name": "SiIV_1402", "wave_A": 1402.770},
    {"name": "SiII_1526", "wave_A": 1526.707},
    {"name": "SiII_1533", "wave_A": 1533.431},
    {"name": "CIV_1548", "wave_A": 1548.195},
    {"name": "CIV_1550", "wave_A": 1550.770},
    {"name": "HeII_1640", "wave_A": 1640.420},
    {"name": "CI_1656", "wave_A": 1656.928},
    {"name": "OIII_1660", "wave_A": 1660.809},
    {"name": "OIII_1666", "wave_A": 1666.150},
    {"name": "AlII_1670", "wave_A": 1670.787},
    # STIS NUV (0.1605-0.3150 um)
    {"name": "SiII_1808", "wave_A": 1808.013},
    {"name": "SiII_1816", "wave_A": 1816.928},
    {"name": "AlIII_1854", "wave_A": 1854.716},
    {"name": "AlIII_1862", "wave_A": 1862.790},
    {"name": "SiIII_1892", "wave_A": 1892.030},
    {"name": "CIII_1908", "wave_A": 1908.734},
    {"name": "CII_2325", "wave_A": 2325.403},
    {"name": "CII_2326", "wave_A": 2326.930},
    {"name": "CII_2328", "wave_A": 2328.122},
    {"name": "FeII_2344", "wave_A": 2344.214},
    {"name": "FeII_2382", "wave_A": 2382.765},
    {"name": "FeII_2586", "wave_A": 2586.650},
    {"name": "FeII_2600", "wave_A": 2600.173},
    {"name": "FeII_2626", "wave_A": 2626.451},
    {"name": "MgII_k_2796", "wave_A": 2796.352},
    {"name": "MgII_h_2803", "wave_A": 2803.531},
    {"name": "MgI_2852", "wave_A": 2852.964},
]

# ---------------------------------------------------------------------------
# Calibration Bands & COMB_V4_1 Windows
# ---------------------------------------------------------------------------

CALIBRATION_BANDS_FUSE_FUV_A = [
    {"band_id": "L1_FUSE_960", "center_wave_A": 960.0},
    {"band_id": "L2_FUSE_1005", "center_wave_A": 1005.0},
    {"band_id": "L3_FUSE_1065", "center_wave_A": 1065.0},
    {"band_id": "L4_FUSE_1115", "center_wave_A": 1115.0},
    {"band_id": "L5_FUSE_1160", "center_wave_A": 1160.0},
]

CALIBRATION_BANDS_COS_FUV_A = [
    {"band_id": "C1_COS_1165", "center_wave_A": 1165.0},
    {"band_id": "C2_COS_1255", "center_wave_A": 1255.0},
    {"band_id": "C3_COS_1280", "center_wave_A": 1280.0},
    {"band_id": "C4_COS_1350", "center_wave_A": 1350.0},
    {"band_id": "C5_COS_1415", "center_wave_A": 1415.0},
]

CALIBRATION_BANDS_STIS_NUV_A = [
    {"band_id": "N1_STIS_1750", "center_wave_A": 1750.0},
    {"band_id": "N2_STIS_1950", "center_wave_A": 1950.0},
    {"band_id": "N3_STIS_2100", "center_wave_A": 2100.0},
    {"band_id": "N4_STIS_2400", "center_wave_A": 2400.0},
    {"band_id": "N5_STIS_2650", "center_wave_A": 2650.0},
    {"band_id": "N6_STIS_2950", "center_wave_A": 2950.0},
]

COMB_V4_1_WINDOWS_A: dict[str, list[dict[str, Any]]] = {
    "FUSE_FUV": [
        {"band": "FUSE_SHORT", "lo_a": 912.0, "hi_a": 1018.0},
        {"band": "FUSE_LONG", "lo_a": 1044.0, "hi_a": 1180.0},
    ],
    "HST_COS_FUV": [
        {"band": "COS_FUVB", "lo_a": 1142.0, "hi_a": 1204.0},
        {"band": "COS_FUVA", "lo_a": 1228.0, "hi_a": 1428.0},
    ],
    "HST_STIS_NUV": [
        {"band": "STIS_NUV_BLUE", "lo_a": 1640.0, "hi_a": 2280.0},
        {"band": "STIS_NUV_RED", "lo_a": 2310.0, "hi_a": 3080.0},
    ],
}

BASE_V4_0_CONFIG: dict[str, Any] = {
    "schema": "SPACE_LYMAN_FUV_NUV_V4_0",
    "knn_atlas_neighbors": 5,
    "knn_teff_scale_k": 420.0,
    "knn_mh_scale_dex": 0.40,
    "knn_min_wave_overlap_frac": 0.25,
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
    # Gates G2_V40, G3_V40, G4_V40, G5_V40, G6_V36
    "gate_g2_airglow_tol_angstrom": 0.12,
    "gate_g3_native_snr_min": 5.0,
    "gate_g3_max_single_px_fraction": 0.62,
    "gate_g3_min_bilateral_wing_ratio": 0.12,
    "gate_g3_max_template_dip_fraction": 0.55,
    "gate_g3_fuv_chromo_tol_angstrom": 0.45,
    "gate_g3_nuv_chromo_tol_angstrom": 0.35,
    "gate_g4_overlap_edge_margin_px": 25,
    "gate_g4_secondary_flux_ratio_min": 0.15,
    "gate_g4_secondary_cont_snr_min": 4.0,
    "gate_g4_secondary_snr_min": 3.0,
    "gate_g4_order_contrast_ratio_min": 0.35,
    "gate_g4_order_contrast_ratio_max": 2.85,
    "gate_g4_uv_bg_over_net_max": 0.45,
    # Gate G5 1D 11-px native LSF morphology
    "gate_g5_cos11_min": 0.85,
    "gate_g5_ipc_hotpx_max_ratio": 2.35,
    "gate_g5_far_wing_34_max": 0.42,
    # Gate G6 Sparse Non-Local Atlas
    "gate_g6_topo_tol_a": 0.08,
    "gate_g6_native_px_tol": 2,
    "gate_g6_min_distinct_stars": 3,
    "gate_g6_intra_star_berv_sep_kms": 5.0,
    # COMB_V4_1 parameters
    "comb_freq_step_ghz": 2.0,
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
    "comb_spacings_ghz": [30.0, 40.0, 50.0, 60.0, 80.0, 100.0, 120.0, 150.0],
    # RV anchors & continuum
    "rv_anchor_fuv_window_kms": 45.0,
    "rv_anchor_nuv_window_kms": 35.0,
    "rv_anchor_scan_half_kms": 10.0,
    "rv_anchor_scan_step_kms": 0.05,
    "rv_anchor_fuv_fwhm_kms": 18.0,
    "rv_anchor_nuv_fwhm_kms": 12.0,
    "rv_anchor_min_snr": 3.5,
    "continuum_block_bins": 100,
    "continuum_blue_cutoff_angstrom": 4050.0,
    "continuum_quantile_blue": 0.90,
    "continuum_quantile": 0.80,
    "continuum_median_blocks": 5,
    "tx_aperture_diameter_m": 10.0,
}


def get_inst_config(instrument: str, resolving_power: float | None = None) -> dict[str, Any]:
    inst = instrument.upper()
    cfg = dict(BASE_V4_0_CONFIG)
    cfg["instrument"] = inst
    if inst == "FUSE_FUV":
        r_pow = float(resolving_power) if resolving_power else 20000.0
        cfg["resolving_power"] = r_pow
        cfg["fwhm_v_kms"] = C_KMS / r_pow
        cfg["sigma_v_kms"] = cfg["fwhm_v_kms"] / FWHM_FACTOR
        cfg["coadd_step_angstrom"] = 0.020
        cfg["wave_min_angstrom"] = 905.0
        cfg["wave_max_angstrom"] = 1187.0
        cfg["coadd_rest_min_angstrom"] = 907.0
        cfg["coadd_rest_max_angstrom"] = 1185.0
        cfg["ext_rest_min_angstrom"] = 903.0
        cfg["ext_rest_max_angstrom"] = 1189.0
        cfg["observatory"] = "FUSE_LEO"
        cfg["telescope_diameter_m"] = 0.39
        cfg["radiometric_anchor"] = "FUSE_CALFUSE_DIRECT_FLAM"
        cfg["rv_anchors"] = LOCKED_RV_ANCHORS_FUSE
        cfg["comb_search_bands"] = ["FUSE_SHORT", "FUSE_LONG"]
        cfg["comb_freq_step_ghz"] = 45.0
        cfg["comb_spacings_ghz"] = [360.0, 450.0, 540.0, 630.0, 720.0, 900.0, 1080.0, 1350.0]
        cfg["gate_g4_secondary_cont_snr_min"] = 1.5
    elif inst == "HST_COS_FUV":
        r_pow = float(resolving_power) if resolving_power else 18000.0
        cfg["resolving_power"] = r_pow
        cfg["fwhm_v_kms"] = C_KMS / r_pow
        cfg["sigma_v_kms"] = cfg["fwhm_v_kms"] / FWHM_FACTOR
        cfg["coadd_step_angstrom"] = 0.020
        cfg["wave_min_angstrom"] = 1125.0
        cfg["wave_max_angstrom"] = 1450.0
        cfg["coadd_rest_min_angstrom"] = 1128.0
        cfg["coadd_rest_max_angstrom"] = 1448.0
        cfg["ext_rest_min_angstrom"] = 1123.0
        cfg["ext_rest_max_angstrom"] = 1452.0
        cfg["observatory"] = "HST_LEO"
        cfg["telescope_diameter_m"] = 2.40
        cfg["radiometric_anchor"] = "HST_CALCOS_DIRECT_FLAM"
        cfg["rv_anchors"] = LOCKED_RV_ANCHORS_COS_FUV
        cfg["comb_search_bands"] = ["COS_FUVB", "COS_FUVA"]
        cfg["comb_freq_step_ghz"] = 40.0
        cfg["comb_spacings_ghz"] = [320.0, 400.0, 480.0, 560.0, 640.0, 800.0, 960.0, 1200.0]
    elif inst == "HST_STIS_NUV":
        r_pow = float(resolving_power) if (resolving_power and float(resolving_power) >= 70000.0) else 30000.0
        cfg["resolving_power"] = r_pow
        cfg["fwhm_v_kms"] = C_KMS / r_pow
        cfg["sigma_v_kms"] = cfg["fwhm_v_kms"] / FWHM_FACTOR
        cfg["coadd_step_angstrom"] = 0.006 if r_pow >= 70000.0 else 0.025
        cfg["wave_min_angstrom"] = 1605.0
        cfg["wave_max_angstrom"] = 3150.0
        cfg["coadd_rest_min_angstrom"] = 1610.0
        cfg["coadd_rest_max_angstrom"] = 3145.0
        cfg["ext_rest_min_angstrom"] = 1602.0
        cfg["ext_rest_max_angstrom"] = 3152.0
        cfg["observatory"] = "HST_LEO"
        cfg["telescope_diameter_m"] = 2.40
        cfg["radiometric_anchor"] = "HST_CALSTIS_DIRECT_FLAM"
        cfg["rv_anchors"] = LOCKED_RV_ANCHORS_STIS_NUV
        cfg["comb_search_bands"] = ["STIS_NUV_BLUE", "STIS_NUV_RED"]
        if r_pow >= 70000.0:
            cfg["comb_freq_step_ghz"] = 4.0
            cfg["comb_spacings_ghz"] = [32.0, 40.0, 48.0, 60.0, 80.0, 100.0, 120.0, 160.0]
        else:
            cfg["comb_freq_step_ghz"] = 15.0
            cfg["comb_spacings_ghz"] = [120.0, 150.0, 180.0, 210.0, 240.0, 300.0, 360.0, 450.0]
    else:
        raise ValueError(f"Unsupported D089 instrument: {instrument}")
    return cfg


def get_calibration_bands(instrument: str) -> list[dict[str, Any]]:
    iu = instrument.upper()
    if iu == "FUSE_FUV":
        return CALIBRATION_BANDS_FUSE_FUV_A
    if iu == "HST_COS_FUV":
        return CALIBRATION_BANDS_COS_FUV_A
    if iu == "HST_STIS_NUV":
        return CALIBRATION_BANDS_STIS_NUV_A
    raise ValueError(f"Unknown D089 instrument: {instrument}")


# ---------------------------------------------------------------------------
# Pure-Stdlib Earth Orbital Heliocentric RV + Array Helpers
# ---------------------------------------------------------------------------

def stdlib_earth_helio_rv_kms(ra_deg: float, dec_deg: float, mjd_utc: float) -> float:
    """Earth orbital heliocentric projection (no surface rotation; validates LEO spacecraft within <=8.5 km/s)."""
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
    vx_eq = v0 * (-math.sin(lam_e) - e_orb * math.sin(pi_e))
    vy_ecl = v0 * (math.cos(lam_e) + e_orb * math.cos(pi_e))
    vy_eq = vy_ecl * math.cos(eps)
    vz_eq = vy_ecl * math.sin(eps)
    ra, dec = math.radians(ra_deg), math.radians(dec_deg)
    return float(vx_eq * math.cos(dec) * math.cos(ra) + vy_eq * math.cos(dec) * math.sin(ra) + vz_eq * math.sin(dec))


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
# Step 1: Space-UV Chromospheric/TR & Photospheric RV Anchoring
# ---------------------------------------------------------------------------

def extract_rv_anchor_window(
    wave: np.ndarray,
    flux: np.ndarray,
    lab_wave_a: float,
    prior_rv_kms: float,
    cfg: dict[str, Any] = BASE_V4_0_CONFIG,
) -> tuple[np.ndarray, np.ndarray]:
    dv = C_KMS * (wave - lab_wave_a) / lab_wave_a
    is_nuv = cfg.get("instrument") == "HST_STIS_NUV"
    win_kms = float(cfg["rv_anchor_nuv_window_kms"] if is_nuv else cfg["rv_anchor_fuv_window_kms"])
    mask = np.abs(dv - prior_rv_kms) <= win_kms
    return wave[mask].copy(), flux[mask].copy()


def fit_rv_anchor_absorption(
    wave_win: np.ndarray,
    flux_win: np.ndarray,
    lab_wave_a: float,
    prior_rv_kms: float,
    cfg: dict[str, Any] = BASE_V4_0_CONFIG,
) -> dict[str, Any]:
    w = np.asarray(wave_win, dtype=np.float64)
    f = np.asarray(flux_win, dtype=np.float64)
    valid = np.isfinite(w) & np.isfinite(f)
    w, f = w[valid], f[valid]
    if len(w) < 10:
        return {
            "status": "INSUFFICIENT_SAMPLES",
            "n_samples": int(len(w)),
            "best_rv_kms": float("nan"),
            "rel_depth": float("nan"),
            "min_sse": float("nan"),
            "boundary_hit": True,
        }

    is_nuv = cfg.get("instrument") == "HST_STIS_NUV"
    dv = C_KMS * (w - lab_wave_a) / lab_wave_a
    win_kms = float(cfg["rv_anchor_nuv_window_kms"] if is_nuv else cfg["rv_anchor_fuv_window_kms"])
    u = (dv - prior_rv_kms) / win_kms
    fwhm_p = float(cfg["rv_anchor_nuv_fwhm_kms"] if is_nuv else cfg["rv_anchor_fuv_fwhm_kms"])
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
        sb_mask = np.abs(dv - v_try) >= 2.0 * sigma_phot
        sb_mad = max(1e-30, exact_mad_1d(resid[sb_mask]) if int(np.sum(sb_mask)) >= 6 else exact_mad_1d(resid))
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
    anchors = cfg.get("rv_anchors", LOCKED_RV_ANCHORS_COS_FUV)
    anchor_rows: list[dict[str, Any]] = []
    bundle: dict[str, dict[str, list[float]]] = {}
    clean_rvs: list[float] = []
    # Scale space-UV cgs FLAM (~1e-16..1e-10) into O(1) units before rounding into bounded JSON
    fin_nz = np.isfinite(flux) & (flux != 0)
    med_abs = float(np.nanmedian(np.abs(flux[fin_nz]))) if np.any(fin_nz) else 1e-14
    scale_anc = 1.0 / max(1e-22, med_abs)
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
        bundle[aid] = {"wave_a": [round(float(x), 5) for x in w_win], "flux": [round(float(y), 4) for y in f_win]}
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
    cfg: dict[str, Any] = BASE_V4_0_CONFIG,
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
    g_floor = 0.25 * exact_quantile_1d(global_pos, 0.70) if len(global_pos) >= 20 else 1e-17
    if e_arr is not None:
        e_fin = e_arr[np.isfinite(e_arr) & (e_arr > 0.0)]
        if len(e_fin) >= 20:
            g_floor = max(g_floor, 3.0 * exact_median_1d(e_fin))
    g_floor = max(1e-21, float(g_floor))

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
    cfg: dict[str, Any] = BASE_V4_0_CONFIG,
) -> tuple[dict[str, np.ndarray], dict[str, dict[str, Any]]]:
    """Leave-star-out KNN stellar templates, preferring overlapping CENWAVE neighbors in STIS_NUV."""
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

        ov_cands = []
        all_cands = []
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
    margin = max(65, int(round((1.5 if float(cfg["resolving_power"]) >= 70000.0 else 4.5) / step_a)))
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
    margin = max(65, int(round((1.5 if float(cfg["resolving_power"]) >= 70000.0 else 4.5) / float(cfg["coadd_step_angstrom"]))))
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
    margin = max(65, int(round((1.5 if float(cfg["resolving_power"]) >= 70000.0 else 4.5) / float(cfg["coadd_step_angstrom"]))))

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
# Step 4: Automated Physics Vetting Gates G2_V40, G3_V40, G4_V40, G5_V40, G6_V36
# ---------------------------------------------------------------------------

def evaluate_gate_g2_airglow(
    fitted_bary_wave_a: float,
    berv_kms: float,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    topo_a = float(fitted_bary_wave_a / (1.0 + berv_kms / C_KMS))
    inst = cfg.get("instrument", "")
    if inst == "FUSE_FUV":
        bands = FUSE_GEOCORONAL_BANDS_VAC_A
    elif inst == "HST_COS_FUV":
        bands = COS_GEOCORONAL_BANDS_VAC_A
    else:
        bands = STIS_NUV_GEOCORONAL_BANDS_VAC_A

    for band in bands:
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
    if not math.isfinite(cont_q):
        return {"usable": False}

    cont_raw = max(0.0, float(cont_q))
    e_floor = 1e-20
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


def evaluate_gates_g3_g4_g5_v40(
    order_patches: list[dict[str, Any]],
    dpr_or_calsel: str,
    channel: str,
    star_rest_a: float | None,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    inst = cfg.get("instrument", "")
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
            res["bg_flux"] = p.get("bg_flux")
            res["net_a"] = p.get("net_a")
            res["dq"] = p.get("dq")
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

    evaluated.sort(key=lambda x: (-x["native_snr"], -x["continuum_adu"]))
    prim = evaluated[0]

    # Gate G3_V40: Native LSF + Supraphotospheric + Template-Dip + UV Chromospheric/TR Emission
    g3_reasons: list[str] = []
    if prim["native_snr"] < cfg["gate_g3_native_snr_min"]:
        g3_reasons.append("S1D_REBIN_OR_LOW_NATIVE_SNR")
    if prim["eta_1px"] > cfg["gate_g3_max_single_px_fraction"]:
        g3_reasons.append("SUB_LSF_SINGLE_PIXEL_SPIKE")
    if prim["min_wing_ratio"] < cfg["gate_g3_min_bilateral_wing_ratio"]:
        g3_reasons.append("ASYMMETRIC_COSMIC_RAY_SPIKE")
    if prim["native_fn_pk3"] < cfg["supraphotospheric_min_fn_pk3"]:
        g3_reasons.append("SUB_CONTINUUM_OR_ABSORPTION_GHOST")
    if prim["template_dip_frac"] > cfg["gate_g3_max_template_dip_fraction"]:
        g3_reasons.append("TEMPLATE_ABSORPTION_DIP_GHOST")

    chromo_name = "NONE"
    chromo_sep = 1e9
    if star_rest_a is not None and math.isfinite(star_rest_a):
        tol = float(cfg["gate_g3_nuv_chromo_tol_angstrom"] if inst == "HST_STIS_NUV" else cfg["gate_g3_fuv_chromo_tol_angstrom"])
        for ch in STELLAR_UV_EMISSION_VAC_A:
            s = abs(float(star_rest_a) - float(ch["wave_A"]))
            if s < chromo_sep:
                chromo_sep, chromo_name = s, ch["name"]
        if chromo_sep <= tol:
            g3_reasons.append(f"CHROMOSPHERIC_OR_TR_LINE_{chromo_name}")

    # Gate G4_V40: FUSE dual-telescope LiF/SiC coincidence + COS/STIS DQ & BACKGROUND/NET + Echelle overlap
    g4_reasons: list[str] = []
    bg_tested = False
    bg_ratio = 0.0
    bgf = prim.get("bg_flux")
    dqf = prim.get("dq")

    if dqf is not None:
        dq_arr = np.asarray(dqf, dtype=np.int64)
        k0 = prim["local_index"]
        sub_dq = dq_arr[max(0, k0 - 1) : min(len(dq_arr), k0 + 2)]
        if inst == "HST_COS_FUV":
            if any((int(dv) & COS_FATAL_DQ_MASK) != 0 for dv in sub_dq):
                g4_reasons.append("COS_FUV_DQ_FLAG")
        elif inst == "HST_STIS_NUV":
            if any((int(dv) & STIS_FATAL_DQ_MASK) != 0 for dv in sub_dq):
                g4_reasons.append("STIS_NUV_MAMA_DQ_FLAG")
        elif inst == "FUSE_FUV":
            if any(int(dv) != 0 for dv in sub_dq):
                g4_reasons.append("FUSE_DETECTOR_DQ_FLAG")

    if bgf is not None and prim.get("net_a") is not None:
        bg_arr = np.asarray(bgf, dtype=np.float64)
        net_arr = np.asarray(prim["net_a"], dtype=np.float64)
        if len(bg_arr) >= 41 and np.all(np.isfinite(bg_arr)) and np.all(np.isfinite(net_arr)):
            bg_tested = True
            k0 = len(bg_arr) // 2
            sb_g = np.r_[bg_arr[max(0, k0 - 60) : max(0, k0 - 10)], bg_arr[min(len(bg_arr), k0 + 11) : min(len(bg_arr), k0 + 61)]]
            sb_n = np.r_[net_arr[max(0, k0 - 60) : max(0, k0 - 10)], net_arr[min(len(net_arr), k0 + 11) : min(len(net_arr), k0 + 61)]]
            if len(sb_g) >= 10 and len(sb_n) >= 6:
                med_g = exact_median_1d(sb_g)
                mad_g = max(1e-9, exact_mad_1d(sb_g))
                pk_g = float(np.max(bg_arr[max(0, k0 - 2) : min(len(bg_arr), k0 + 3)]) - med_g)
                med_n = exact_median_1d(sb_n)
                pk_net = max(1e-6, float(np.max(net_arr[max(0, k0 - 2) : min(len(net_arr), k0 + 3)]) - med_n))
                bg_ratio = pk_g / pk_net
                if (pk_g / mad_g >= 5.0) and (bg_ratio >= cfg["gate_g4_uv_bg_over_net_max"]):
                    g4_reasons.append("COS_FUV_SLIT_BACKGROUND" if inst == "HST_COS_FUV" else "STIS_MAMA_SLIT_BACKGROUND")

    # Multi-channel (FUSE LiF1<->LiF2 / SiC1<->SiC2) or Multi-order (STIS E230M/H) coincidence
    margin_ov = int(cfg["gate_g4_overlap_edge_margin_px"])
    qual_orders = [
        e for e in evaluated
        if ((e["active_start_px"] + margin_ov) <= e["native_pixel"] <= (e["active_end_px"] - margin_ov))
        and (
            (cfg["gate_g4_secondary_flux_ratio_min"] * prim["continuum_adu"] <= e["continuum_adu"] <= 4.0 * prim["continuum_adu"])
            if inst == "FUSE_FUV"
            else (e["continuum_adu"] >= cfg["gate_g4_secondary_flux_ratio_min"] * prim["continuum_adu"])
        )
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
        sc_r = (
            sec["native_amp_adu"] / max(1e-30, prim["native_amp_adu"])
            if inst == "FUSE_FUV"
            else sec["native_amp_rel"] / max(1e-12, prim["native_amp_rel"])
        )
        if sec["native_snr"] < cfg["gate_g4_secondary_snr_min"] or not (cfg["gate_g4_order_contrast_ratio_min"] <= sc_r <= cfg["gate_g4_order_contrast_ratio_max"]):
            if inst == "FUSE_FUV":
                g4_reasons.append("FUSE_SINGLE_CHANNEL_DETECTOR_ARTIFACT")
            else:
                g4_reasons.append("SINGLE_ORDER_DETECTOR_ARTIFACT")

    # Gate G5_V40: 1D 11-px native LSF cosine + cosmic hot-px concentration + far-wing plateau
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
        "bg_tested": bg_tested,
        "bg_over_net_ratio": float(bg_ratio),
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

        if len(nu_g) < 30:
            continue

        z_clip = np.clip(np.where(cln_nu, z_nu, -9.0), -9.0, z_cap)
        z_tclip = np.clip(np.where(cln_nu, z_topo_nu, -9.0), -9.0, z_cap)
        n_g = len(nu_g)
        z_dil = np.full(n_g, -9.0, dtype=np.float64)
        zt_dil = np.full(n_g, -9.0, dtype=np.float64)
        fn_dil = np.zeros(n_g, dtype=np.float64)
        rc_dil = np.zeros(n_g, dtype=np.float64)
        for sh in range(-tol_bins, tol_bins + 1):
            src_z = np.roll(z_clip, sh)
            src_zt = np.roll(z_tclip, sh)
            src_fn = np.roll(fn_nu, sh)
            src_rc = np.roll(rc_nu, sh)
            if sh > 0:
                src_z[:sh], src_zt[:sh], src_fn[:sh], src_rc[:sh] = -9.0, -9.0, 0.0, 0.0
            elif sh < 0:
                src_z[sh:], src_zt[sh:], src_fn[sh:], src_rc[sh:] = -9.0, -9.0, 0.0, 0.0
            z_dil = np.maximum(z_dil, src_z)
            zt_dil = np.maximum(zt_dil, src_zt)
            fn_dil = np.maximum(fn_dil, src_fn)
            rc_dil = np.maximum(rc_dil, src_rc)

        qual_tooth = cln_nu & (z_dil >= z_min) & (fn_dil >= fn_min) & (rc_dil >= rc_min)
        z_pos = np.where(qual_tooth, np.maximum(0.0, z_dil), 0.0)
        zt_pos = np.where(cln_nu, np.maximum(0.0, zt_dil), 0.0)

        for dnu_ghz in cfg["comb_spacings_ghz"]:
            step_idx = max(4, int(round(float(dnu_ghz) / df_ghz)))
            span_idx = (m_teeth - 1) * step_idx
            if span_idx + 1 >= n_g:
                continue
            n_starts = n_g - span_idx
            searched_configs += n_starts

            q_cols = [qual_tooth[t * step_idx : t * step_idx + n_starts] for t in range(m_teeth)]
            n_q = np.sum(q_cols, axis=0)
            z_mat = np.vstack([z_pos[t * step_idx : t * step_idx + n_starts] for t in range(m_teeth)])
            tooth_z = z_mat
            s_comb = np.sum(z_mat, axis=0) / math.sqrt(float(m_teeth))
            dom_frac = np.max(z_mat, axis=0) / np.maximum(1e-9, np.sum(z_mat, axis=0))

            hits = np.flatnonzero((n_q >= min_qual) & (s_comb >= s_min) & (dom_frac <= dom_max))
            for h_i in hits:
                zt_vec = np.asarray([zt_pos[h_i + t * step_idx] for t in range(m_teeth)], dtype=np.float64)
                st_sc = float(np.sum(zt_vec) / math.sqrt(float(m_teeth)))
                anti_ratio = st_sc / max(1e-9, float(s_comb[h_i]))
                if anti_ratio > anti_max:
                    continue

                if enable_v41_filters:
                    q_vec = np.asarray([bool(qual_tooth[h_i + t * step_idx]) for t in range(m_teeth)])
                    # V4.1 Check 1: Half-integer intertooth valley must be below inter_max_ratio
                    half_idx = step_idx // 2
                    inter_vals = [float(z_dil[min(n_g - 1, h_i + t * step_idx + half_idx)]) for t in range(m_teeth - 1)]
                    med_tooth = float(exact_median_1d(tooth_z[q_vec, h_i])) if np.any(q_vec) else 3.0
                    med_inter = float(exact_median_1d(np.asarray(inter_vals, dtype=np.float64)))
                    inter_ratio = med_inter / max(1e-9, med_tooth)
                    if inter_ratio > inter_max_ratio:
                        continue

                    # V4.1 Check 2: Off-tooth crowding density (> 2 sigma outside +/- 2 bins of comb teeth)
                    sl_win = slice(h_i, h_i + span_idx + 1)
                    off_mask = cln_nu[sl_win].copy()
                    for t in range(m_teeth):
                        c_loc = t * step_idx
                        lo_m = max(0, c_loc - (tol_bins + 1))
                        hi_m = min(len(off_mask), c_loc + tol_bins + 2)
                        off_mask[lo_m:hi_m] = False
                    n_off = int(np.sum(off_mask))
                    off_frac_gt2 = float(np.sum(z_nu[sl_win][off_mask] >= 2.0)) / n_off if n_off >= 10 else 0.0
                    if off_frac_gt2 > off_crowd_max:
                        continue
                else:
                    inter_ratio = 0.0
                    off_frac_gt2 = 0.0

                nu0 = float(nu_g[h_i])
                nu_end = float(nu_g[h_i + (m_teeth - 1) * step_idx])
                w0_a = C_ANGSTROM_GHZ / nu0
                wend_a = C_ANGSTROM_GHZ / nu_end
                w_teeth_a = [round(C_ANGSTROM_GHZ / (nu0 + t * float(dnu_ghz)), 4) for t in range(m_teeth)]
                all_cands.append({
                    "band": bname,
                    "dnu_ghz": float(dnu_ghz),
                    "nu0_ghz": round(nu0, 3),
                    "nu_end_ghz": round(nu_end, 3),
                    "wave0_a": round(w0_a, 4),
                    "wave_end_a": round(wend_a, 4),
                    "s_comb": round(float(s_comb[h_i]), 4),
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
# Step 6: Direct Absolute Space-UV Spectrophotometric Upper Limits
# ---------------------------------------------------------------------------

def resolve_band_radiometric_anchor(instrument: str) -> str:
    iu = instrument.upper()
    if iu == "FUSE_FUV":
        return "FUSE_CALFUSE_DIRECT_FLAM"
    if iu == "HST_COS_FUV":
        return "HST_CALCOS_DIRECT_FLAM"
    if iu == "HST_STIS_NUV":
        return "HST_CALSTIS_DIRECT_FLAM"
    raise ValueError(f"Unsupported instrument for D089 radiometric anchor: {instrument}")


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
    if radiometric_anchor in ("FUSE_CALFUSE_DIRECT_FLAM", "HST_CALCOS_DIRECT_FLAM", "HST_CALSTIS_DIRECT_FLAM"):
        if direct_flam_cgs is None or not math.isfinite(direct_flam_cgs) or direct_flam_cgs <= 0.0:
            raise ValueError(f"{radiometric_anchor} requires positive direct_flam_cgs")
        flam = float(direct_flam_cgs)
    else:
        if radiometric_anchor == "GAIA_DR3_GRP":
            piv, zp = GAIA_GRP_PIVOT_A, GAIA_GRP_ZP_FLAM
        elif radiometric_anchor == "TWOMASS_J":
            piv, zp = TWOMASS_J_PIVOT_A, TWOMASS_J_ZP_FLAM
        elif radiometric_anchor == "JOHNSON_V":
            piv, zp = JOHNSON_V_PIVOT_A, JOHNSON_V_ZP_FLAM
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
