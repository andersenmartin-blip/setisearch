#!/usr/bin/env python3
"""NORTHERN_V3_5: Dual-Observatory Four-Channel Optical/Far-Red SETI Detector (Phase D084).

Supports Northern Hemisphere stabilized & high-resolution echelle archives:
  1. Telescopio Nazionale Galileo (TNG 3.58 m, La Palma) HARPS-N:
       R = 115,000, [3880.0, 6900.0] A barycentric vacuum, 69 x 4096 native e2ds orders
  2. Calar Alto (3.50 m, Spain) CARMENES VIS:
       R = 94,600, [5150.0, 10615.0] A barycentric vacuum, 61 x 4096 native order arrays

Key Prospective Architectural Upgrade Over D083 CRIRES_V3_4 -> NORTHERN_V3_5:
  - Standardized Vacuum Frame Everywhere (IAU Edlen / Morton air-to-vacuum for HARPS-N;
    CARACAL native vacuum for CARMENES_VIS) with independent pure-math La Palma &
    Calar Alto BERV verification and 12 locked NIST vacuum atomic RV anchors per instrument.
  - Four Matched-Filter Search Channels (T, P, T_DIFF, K_PLANET) across 10 northern
    orbital campaigns (2 null controls + 8 exoplanet campaigns incl. transiting
    HD 219134 b and GJ 486 b) and 25 brand-new northern stars (18 within < 10 pc).
  - Five Established Physical Gates (G1_V35..G5_V35) Adapted for Northern Tellurics,
    OH Nightglow Forests (5577-10615 A), M-Dwarf Chromospheric Flare Cores, Multi-Order
    Overlap Consistencies, and 11-px CCD LSF Morphology.
  - NEW Gate G6_V35 (Automated Cross-Star Topocentric & Native Order-Pixel Coincidence
    Gate — motivated directly by the D083 empirical discovery):
    Veto any candidate whose topocentric vacuum wavelength (|d_lambda| <= 0.16 A) OR
    native detector coordinate (same instrument, order, |d_px| <= 1.5 px) also
    exhibits a narrow supraphotospheric excess in >= 2 OTHER unrelated cohort stars
    separated in relative Doppler frame by |(v* - BERV)_other - (v* - BERV)_target| >= 8 km/s,
    automatically eliminating unlisted OH Meinel airglow and fixed CCD warm/fringe pixels.
  - Dual-Band Radiometric Calibration (Gaia DR3 G < 8500 A; 2MASS J >= 8500 A up to
    the 1030-1061 nm Yb/Nd:YAG far-red edge) for 8-sigma 10 m CW laser power limits.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.ndimage import median_filter

C_KMS = 299792.458
FWHM_FACTOR = 2.0 * math.sqrt(2.0 * math.log(2.0))
MAD_NORM = 1.4826

# Continuity radiometric constants matching D079-D083
GAIA_G_PIVOT_A = 6217.6
GAIA_G_ZP_FLAM = 2.50386e-9
TWOMASS_J_PIVOT_A = 12350.0
TWOMASS_J_ZP_FLAM = 3.129e-10
RADIOMETRIC_GJ_SPLIT_A = 8500.0
HC_OVER_K_ANGSTROM_KELVIN = 1.438776877e8
PC_CM = 3.0856775814913673e18
G_SI = 6.67430e-11
M_SUN_KG = 1.98847e30
DAY_S = 86400.0

# Observatory coordinates
LAPALMA_LAT_DEG = 28.7540
LAPALMA_LON_DEG = -17.8891
CALAR_ALTO_LAT_DEG = 37.2236
CALAR_ALTO_LON_DEG = -2.5463

# Resolved physical visual binary pairs within D084 (excluded from cross-star G6 & self-kNN checks)
RESOLVED_BINARY_PARTNERS: dict[str, set[str]] = {
    "61CYGA": {"61CYGB"},
    "61CYGB": {"61CYGA"},
    "STRUVE2398A": {"STRUVE2398B"},
    "STRUVE2398B": {"STRUVE2398A"},
}


def air_to_vac_a(wave_air_a: float | np.ndarray) -> float | np.ndarray:
    """IAU Edlen (1966) / Morton (2000, ApJS 130, 403) standard air-to-vacuum conversion (A)."""
    is_scalar = isinstance(wave_air_a, (int, float))
    w = np.asarray(wave_air_a, dtype=np.float64)
    s2 = (1.0e4 / np.maximum(1500.0, w)) ** 2
    n_air = 1.0 + 8.34254e-5 + 2.406147e-2 / (130.0 - s2) + 1.5998e-4 / (38.9 - s2)
    out = w * n_air
    return float(out) if is_scalar else out


def vac_to_air_a(wave_vac_a: float | np.ndarray) -> float | np.ndarray:
    """Inverse Morton (2000) vacuum-to-air conversion (A)."""
    is_scalar = isinstance(wave_vac_a, (int, float))
    w = np.asarray(wave_vac_a, dtype=np.float64)
    s2 = (1.0e4 / np.maximum(1500.0, w)) ** 2
    n_air = 1.0 + 8.34254e-5 + 2.406147e-2 / (130.0 - s2) + 1.5998e-4 / (38.9 - s2)
    out = w / n_air
    return float(out) if is_scalar else out


# Clean search windows per instrument (barycentric vacuum Angstrom)
CLEAN_HARPSN_WINDOWS_VAC_A = [
    {"band": "HARPSN_OPTICAL", "lo_a": 3880.0, "hi_a": 6862.0},  # stops cleanly before O2 B bandhead at 6867 A
]

CLEAN_CARMENES_WINDOWS_VAC_A = [
    {"band": "CARM_GREEN_RED", "lo_a": 5150.0, "hi_a": 6862.0},
    {"band": "CARM_IZ_CORE", "lo_a": 6950.0, "hi_a": 7162.0},
    {"band": "CARM_I_O2A_PRE", "lo_a": 7340.0, "hi_a": 7585.0},
    {"band": "CARM_I_POST_O2A", "lo_a": 7718.0, "hi_a": 8125.0},
    {"band": "CARM_Z_852_893", "lo_a": 8360.0, "hi_a": 8935.0},
    {"band": "CARM_Y_1UM", "lo_a": 9865.0, "hi_a": 10615.0},
]

# Topocentric vacuum telluric absorption bands masked inside Gate G2_V35
NORTHERN_TELLURIC_BANDS_TOPO_VAC_A = [
    {"name": "O2_GAMMA", "lo_vac_A": 6275.0, "hi_vac_A": 6330.0},
    {"name": "O2_B_BAND", "lo_vac_A": 6865.0, "hi_vac_A": 6948.0},
    {"name": "H2O_720NM", "lo_vac_A": 7162.0, "hi_vac_A": 7338.0},
    {"name": "O2_A_BAND", "lo_vac_A": 7588.0, "hi_vac_A": 7716.0},
    {"name": "H2O_820NM", "lo_vac_A": 8128.0, "hi_vac_A": 8358.0},
    {"name": "H2O_930NM", "lo_vac_A": 8938.0, "hi_vac_A": 9862.0},
]

# Principal optical + far-red terrestrial airglow & streetlamp lines (air -> exact vacuum A via air_to_vac_a)
_AIRGLOW_AIR_A = [
    ("HgI_4046", 4046.563),
    ("HgI_4358", 4358.328),
    ("HgI_5460", 5460.735),
    ("OI_5577_AURORAL", 5577.339),
    ("HgI_5769", 5769.598),
    ("HgI_5790", 5790.663),
    ("NaID2_AIRGLOW", 5889.951),
    ("NaID1_AIRGLOW", 5895.924),
    ("OH_6287", 6287.434),
    ("OI_6300", 6300.304),
    ("OH_6306", 6306.869),
    ("OI_6363", 6363.776),
    ("OH_6498", 6498.729),
    ("OH_6533", 6533.044),
    ("OH_6553", 6553.617),
    ("OH_6828", 6828.520),
    ("OH_6834", 6834.230),
    ("OH_6948", 6948.952),
    ("OH_7316", 7316.282),
    ("OH_7340", 7340.885),
    ("OH_7358", 7358.662),
    ("OH_7392", 7392.198),
    ("OH_7401", 7401.688),
    ("OH_7524", 7524.082),
    ("OH_7571", 7571.748),
    ("OH_7750", 7750.640),
    ("OH_7794", 7794.112),
    ("OH_7808", 7808.463),
    ("OH_7821", 7821.503),
    ("OH_7853", 7853.470),
    ("OH_7913", 7913.708),
    ("OH_7949", 7949.204),
    ("OH_7964", 7964.650),
    ("OH_7993", 7993.332),
    ("OH_8025", 8025.668),
    ("OH_8062", 8062.067),
    ("OH_8344", 8344.602),
    ("OH_8399", 8399.170),
    ("OH_8430", 8430.174),
    ("OH_8465", 8465.208),
    ("OH_8504", 8504.628),
    ("O2_8645", 8645.100),
    ("O2_8659", 8659.220),
    ("OH_8761", 8761.340),
    ("OH_8778", 8778.320),
    ("OH_8827", 8827.106),
    ("OH_8850", 8850.690),
    ("OH_8885", 8885.850),
    ("OH_8919", 8919.616),
    ("OH_9872", 9872.140),
    ("OH_9914", 9914.680),
    ("OH_10012", 10012.790),
    ("OH_10124", 10124.020),
    ("OH_10286", 10286.650),
    ("OH_10372", 10372.880),
    ("OH_10418", 10418.420),
]
NORTHERN_AIRGLOW_LINES_TOPO_VAC_A = [
    {"name": nm, "wave_air_A": wa, "wave_vac_A": float(air_to_vac_a(wa))}
    for nm, wa in _AIRGLOW_AIR_A
]

# Active K/M-dwarf stellar chromospheric & flare lines in stellar rest vacuum A
_CHROMO_AIR_A = [
    ("CaII_K_3933", 3933.663),
    ("CaII_H_3968", 3968.469),
    ("HI_Heps_3970", 3970.075),
    ("HI_Hdelta_4101", 4101.734),
    ("HI_Hgamma_4340", 4340.472),
    ("HeI_4471", 4471.479),
    ("HI_Hbeta_4861", 4861.350),
    ("MgIb1_5183", 5183.604),
    ("HeI_D3_5875", 5875.621),
    ("NaID2_5889", 5889.951),
    ("NaID1_5895", 5895.924),
    ("OI_6300_STELLAR", 6300.304),
    ("HI_Halpha_6562", 6562.801),
    ("HeI_6678", 6678.151),
    ("HeI_7065", 7065.190),
    ("KI_7664", 7664.899),
    ("KI_7698", 7698.965),
    ("NaI_8183", 8183.256),
    ("NaI_8194", 8194.824),
    ("CaII_IRT1_8498", 8498.023),
    ("CaII_IRT2_8542", 8542.091),
    ("CaII_IRT3_8662", 8662.141),
    ("FeII_8490", 8490.079),
    ("HI_PaDelta_10049", 10049.373),
]
STELLAR_CHROMOSPHERIC_VAC_A = [
    {"name": nm, "rest_air_A": wa, "rest_vac_A": float(air_to_vac_a(wa))}
    for nm, wa in _CHROMO_AIR_A
]

# 12 locked NIST ASD atomic absorption anchors per instrument (air -> exact vacuum Ritz A)
_HARPSN_RV_AIR_A = [
    ("FeI_4447", "Fe I", 4447.717),
    ("TiII_4571", "Ti II", 4571.971),
    ("FeI_4602", "Fe I", 4602.941),
    ("FeI_5250", "Fe I", 5250.646),
    ("FeI_5328", "Fe I", 5328.039),
    ("FeI_5405", "Fe I", 5405.775),
    ("CaI_6122", "Ca I", 6122.217),
    ("CaI_6162", "Ca I", 6162.173),
    ("FeI_6173", "Fe I", 6173.334),
    ("CaI_6439", "Ca I", 6439.075),
    ("CaI_6462", "Ca I", 6462.567),
    ("CaI_6717", "Ca I", 6717.681),
]
LOCKED_HARPSN_RV_ANCHORS = [
    {"anchor_id": aid, "species": sp, "lab_air_A": wa, "lab_vac_A": float(air_to_vac_a(wa))}
    for aid, sp, wa in _HARPSN_RV_AIR_A
]

_CARMENES_RV_AIR_A = [
    ("FeI_5328", "Fe I", 5328.039),
    ("FeI_5405", "Fe I", 5405.775),
    ("CaI_6122", "Ca I", 6122.217),
    ("CaI_6162", "Ca I", 6162.173),
    ("CaI_6439", "Ca I", 6439.075),
    ("CaI_6717", "Ca I", 6717.681),
    ("KI_7698", "K I", 7698.965),
    ("NaI_8183", "Na I", 8183.256),
    ("NaI_8194", "Na I", 8194.824),
    ("TiI_8426", "Ti I", 8426.507),
    ("TiI_8435", "Ti I", 8434.960),
    ("FeI_8688", "Fe I", 8688.624),
]
LOCKED_CARMENES_RV_ANCHORS = [
    {"anchor_id": aid, "species": sp, "lab_air_A": wa, "lab_vac_A": float(air_to_vac_a(wa))}
    for aid, sp, wa in _CARMENES_RV_AIR_A
]

# Locked 9 benchmark laser bands per instrument (0.405 - 1.059 um vacuum)
HARPSN_BENCHMARK_BANDS_V35 = [
    {"band_id": "H1_GAN_4050", "center_vac_A": 4050.0, "tech_note": "GaN/violet diode 405.0 nm"},
    {"band_id": "H2_BLUE_4450", "center_vac_A": 4450.0, "tech_note": "High-power InGaN blue 445.0 nm"},
    {"band_id": "H3_ARGON_4880", "center_vac_A": 4880.0, "tech_note": "Ar+ blue-green 488.0 nm"},
    {"band_id": "H4_AR_GREEN_5147", "center_vac_A": 5146.7, "tech_note": "Ar+ 514.5 nm (vac 5146.7 A)"},
    {"band_id": "H5_NDYAG2X_5321", "center_vac_A": 5321.5, "tech_note": "Doubled Nd:YAG 532.0 nm (vac 5321.5 A)"},
    {"band_id": "H6_YELLOW_5800", "center_vac_A": 5800.0, "tech_note": "Clean yellow-orange 580.0 nm window"},
    {"band_id": "H7_CONT_6100", "center_vac_A": 6100.0, "tech_note": "Clean red 610.0 nm continuum"},
    {"band_id": "H8_HENE_6329", "center_vac_A": 6329.9, "tech_note": "HeNe 632.8 nm reference (vac 6329.9 A)"},
    {"band_id": "H9_RED_6702", "center_vac_A": 6702.0, "tech_note": "Red AlGaInP diode 670.0 nm"},
]

CARMENES_BENCHMARK_BANDS_V35 = [
    {"band_id": "C1_NDYAG2X_5321", "center_vac_A": 5321.5, "tech_note": "Doubled Nd:YAG 532.0 nm (vac 5321.5 A)"},
    {"band_id": "C2_CONT_6100", "center_vac_A": 6100.0, "tech_note": "Clean red 610.0 nm continuum"},
    {"band_id": "C3_HENE_6329", "center_vac_A": 6329.9, "tech_note": "HeNe 632.8 nm reference (vac 6329.9 A)"},
    {"band_id": "C4_RED_6702", "center_vac_A": 6702.0, "tech_note": "Red AlGaInP diode 670.0 nm"},
    {"band_id": "C5_DEEPRED_7050", "center_vac_A": 7050.0, "tech_note": "Deep-red 705.0 nm clean window"},
    {"band_id": "C6_RUBIDIUM_7802", "center_vac_A": 7802.4, "tech_note": "Rb D2 / GaAlAs 780.2 nm"},
    {"band_id": "C7_CESIUM_8523", "center_vac_A": 8523.5, "tech_note": "Cs D2 / GaAs 852.3 nm"},
    {"band_id": "C8_YBYAG_10300", "center_vac_A": 10300.0, "tech_note": "Yb:YAG / Yb-fiber 1030.0 nm"},
    {"band_id": "C9_ND_EDGE_10590", "center_vac_A": 10590.0, "tech_note": "Far-red 1.059 um silicon-edge / Nd:glass window"},
]

BENCHMARK_LASER_BANDS_V35 = {
    "HARPS_N": HARPSN_BENCHMARK_BANDS_V35,
    "CARMENES_VIS": CARMENES_BENCHMARK_BANDS_V35,
}

BASE_V3_5_CONFIG: dict[str, Any] = {
    "schema": "NORTHERN_V3_5",
    "knn_atlas_neighbors": 4,
    "knn_teff_scale_k": 450.0,
    "knn_mh_scale_dex": 0.30,
    "fit_phases_bins": [-0.5, -0.25, 0.0, 0.25, 0.5],
    "core_sigma_mult": 3.5,
    "mid_inner_sigma_mult": 6.0,
    "mid_outer_sigma_mult": 30.0,
    "outer_inner_sigma_mult": 30.0,
    "outer_outer_sigma_mult": 60.0,
    "prescreen_local_mad": 3.5,
    "scan_margin_bins": 145,
    "supraphotospheric_min_fn_pk3": 1.010,
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
    "channel_tdiff_min_in_exp_snr": 2.6,
    "channel_tdiff_min_in_exp_fraction": 0.60,
    # Channel K_PLANET
    "channel_kplanet_snr_mid_min": 6.8,
    "channel_kplanet_snr_outer_min": 6.2,
    "channel_kplanet_amp_ratio_min": 0.70,
    "channel_kplanet_amp_ratio_max": 1.35,
    "channel_kplanet_cosine_min": 0.84,
    "channel_kplanet_fwhm_ratio_min": 0.58,
    "channel_kplanet_fwhm_ratio_max": 1.50,
    "channel_kplanet_min_in_exp_snr": 2.4,
    "channel_kplanet_min_in_exp_fraction": 0.60,
    # Gate G2_V35: Northern tellurics + airglow
    "gate_g2_airglow_tol_angstrom": 0.30,
    "gate_g2_min_atm_transm_center": 0.80,
    "gate_g2_min_atm_transm_3px": 0.65,
    # Gate G3_V35: Native 2D LSF, chromosphere, cross-star stellar ridge
    "gate_g3_native_snr_min": 5.0,
    "gate_g3_max_single_px_fraction": 0.62,
    "gate_g3_min_bilateral_wing_ratio": 0.12,
    "gate_g3_max_template_dip_fraction": 0.50,
    "gate_g3_chromospheric_tol_angstrom": 0.65,
    "gate_g3_cross_star_ridge_fn_min": 1.022,
    "gate_g3_cross_star_ridge_max_stars": 2,
    # Gate G4_V35: CCD edge border & multi-order overlap consistency
    "gate_g4_chip_edge_margin_px": 36,
    "gate_g4_overlap_edge_margin_px": 45,
    "gate_g4_secondary_flux_ratio_min": 0.18,
    "gate_g4_secondary_cont_snr_min": 18.0,
    "gate_g4_secondary_snr_min": 2.8,
    "gate_g4_order_contrast_ratio_min": 0.35,
    "gate_g4_order_contrast_ratio_max": 2.85,
    # Gate G5_V35: 11-px CCD LSF cosine, cosmic-ray hot-px ratio, wing plateau
    "gate_g5_ccd_cos11_min": 0.86,
    "gate_g5_ccd_max_hotpx_ratio": 2.45,
    "gate_g5_ccd_far_wing_34_max": 0.42,
    # Gate G6_V35: Automated Cross-Star Topocentric Wavelength & Native Order-Pixel Coincidence Gate
    "gate_g6_topo_tol_angstrom": 0.16,
    "gate_g6_pixel_tol_px": 1.5,
    "gate_g6_min_dv_frame_sep_kms": 8.0,
    "gate_g6_other_prom_min": 0.018,
    "gate_g6_other_snr_min": 3.4,
    "gate_g6_max_other_stars": 1,
    # RV anchors & continuum
    "rv_anchor_window_kms": 45.0,
    "rv_anchor_scan_half_kms": 12.0,
    "rv_anchor_scan_step_kms": 0.05,
    "rv_anchor_photospheric_fwhm_kms": 7.5,
    "rv_anchor_min_rel_depth": 0.05,
    "rv_anchor_min_clean_lines": 3,
    "continuum_block_bins": 115,
    "continuum_quantile": 0.84,
    "continuum_median_blocks": 5,
    "tx_aperture_diameter_m": 10.0,
}


def get_inst_config(instrument: str) -> dict[str, Any]:
    cfg = dict(BASE_V3_5_CONFIG)
    cfg["instrument"] = instrument
    if instrument == "HARPS_N":
        cfg["telescope_diameter_m"] = 3.58
        cfg["resolving_power"] = 115000.0
        cfg["coadd_step_angstrom"] = 0.025
        cfg["wave_min_angstrom"] = 3880.0
        cfg["wave_max_angstrom"] = 6862.0
        cfg["n_orders"] = 69
        cfg["n_px"] = 4096
        cfg["rv_anchors"] = LOCKED_HARPSN_RV_ANCHORS
    elif instrument == "CARMENES_VIS":
        cfg["telescope_diameter_m"] = 3.50
        cfg["resolving_power"] = 94600.0
        cfg["coadd_step_angstrom"] = 0.030
        cfg["wave_min_angstrom"] = 5150.0
        cfg["wave_max_angstrom"] = 10615.0
        cfg["n_orders"] = 61
        cfg["n_px"] = 4096
        cfg["rv_anchors"] = LOCKED_CARMENES_RV_ANCHORS
    else:
        raise ValueError(f"Unsupported D084 instrument: {instrument}")
    cfg["fwhm_v_kms"] = C_KMS / cfg["resolving_power"]
    cfg["sigma_v_kms"] = cfg["fwhm_v_kms"] / FWHM_FACTOR
    return cfg


def is_in_clean_windows(wave_vac_a: np.ndarray | float, instrument: str) -> np.ndarray | bool:
    wins = CLEAN_HARPSN_WINDOWS_VAC_A if instrument == "HARPS_N" else CLEAN_CARMENES_WINDOWS_VAC_A
    if isinstance(wave_vac_a, (int, float)):
        v = float(wave_vac_a)
        return any(float(w["lo_a"]) <= v <= float(w["hi_a"]) for w in wins)
    arr = np.asarray(wave_vac_a, dtype=np.float64)
    mask = np.zeros(arr.shape, dtype=bool)
    for w in wins:
        mask |= (arr >= float(w["lo_a"])) & (arr <= float(w["hi_a"]))
    return mask


def analytical_observatory_berv_kms(ra_deg: float, dec_deg: float, mjd_utc: float, instrument: str) -> float:
    """Pure-math solar-system barycentric + Northern observatory diurnal velocity (km/s)."""
    lat_deg = LAPALMA_LAT_DEG if instrument == "HARPS_N" else CALAR_ALTO_LAT_DEG
    lon_deg = LAPALMA_LON_DEG if instrument == "HARPS_N" else CALAR_ALTO_LON_DEG
    jd = float(mjd_utc) + 2400000.5
    t_cent = (jd - 2451545.0) / 36525.0
    l0 = math.radians((280.46646 + (36000.76983 - 1.396971) * t_cent) % 360.0)
    m_sun = math.radians((357.52911 + 35999.05029 * t_cent) % 360.0)
    e_orb = 0.016708634 - 0.000042037 * t_cent
    c_eq = math.radians(
        (1.914602 - 0.004817 * t_cent) * math.sin(m_sun)
        + 0.019993 * math.sin(2.0 * m_sun)
        + 0.000289 * math.sin(3.0 * m_sun)
    )
    lam_sun = l0 + c_eq
    nu = m_sun + c_eq
    eps0 = math.radians(23.4392911)
    v_orb = 29.7847 / math.sqrt(1.0 - e_orb * e_orb)
    vx_ecl = v_orb * (math.sin(lam_sun) + e_orb * math.sin(lam_sun - nu))
    vy_ecl = -v_orb * (math.cos(lam_sun) + e_orb * math.cos(lam_sun - nu))
    vx = vx_ecl
    vy = vy_ecl * math.cos(eps0)
    vz = vy_ecl * math.sin(eps0)
    l_jup = math.radians((34.3515 + 3034.9057 * t_cent) % 360.0)
    vx += -0.01246 * math.sin(l_jup)
    vy += 0.01246 * math.cos(l_jup) * math.cos(eps0)
    vz += 0.01246 * math.cos(l_jup) * math.sin(eps0)
    l_sat = math.radians((50.0774 + 1222.1138 * t_cent) % 360.0)
    vx += -0.00276 * math.sin(l_sat)
    vy += 0.00276 * math.cos(l_sat) * math.cos(eps0)
    vz += 0.00276 * math.cos(l_sat) * math.sin(eps0)
    l_moon = math.radians((218.3165 + 481267.8813 * t_cent) % 360.0)
    vx += -0.01242 * math.sin(l_moon)
    vy += 0.01242 * math.cos(l_moon) * math.cos(eps0)
    vz += 0.01242 * math.cos(l_moon) * math.sin(eps0)
    gmst_deg = (280.46061837 + 360.98564736629 * (jd - 2451545.0)) % 360.0
    lst_rad = math.radians((gmst_deg + lon_deg) % 360.0)
    v_rot_eq = 0.46510 * math.cos(math.radians(lat_deg))
    vx += -v_rot_eq * math.sin(lst_rad)
    vy += v_rot_eq * math.cos(lst_rad)
    ra_r, dec_r = math.radians(float(ra_deg)), math.radians(float(dec_deg))
    sx = math.cos(dec_r) * math.cos(ra_r)
    sy = math.cos(dec_r) * math.sin(ra_r)
    sz = math.sin(dec_r)
    return float(vx * sx + vy * sy + vz * sz)


def exact_median_1d(arr: np.ndarray) -> float:
    s = np.sort(np.asarray(arr, dtype=np.float64))
    n = len(s)
    if n == 0:
        return float("nan")
    mid = n // 2
    return float(s[mid]) if n % 2 == 1 else float(0.5 * (s[mid - 1] + s[mid]))


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
    return float((1.0 - (pos - lo)) * s[lo] + (pos - lo) * s[hi])


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


def fit_single_rv_anchor(
    wave_win: np.ndarray,
    flux_win: np.ndarray,
    lab_vac_a: float,
    prior_rv_kms: float,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    w = np.asarray(wave_win, dtype=np.float64)
    f = np.asarray(flux_win, dtype=np.float64)
    valid = np.isfinite(w) & np.isfinite(f) & (f > 0)
    w, f = w[valid], f[valid]
    if len(w) < 15:
        return {"status": "INSUFFICIENT_SAMPLES", "n_samples": int(len(w)), "best_rv_kms": float("nan"), "rel_depth": float("nan"), "min_sse": float("nan"), "boundary_hit": True}

    dv = C_KMS * (w - lab_vac_a) / lab_vac_a
    u = (dv - prior_rv_kms) / cfg["rv_anchor_window_kms"]
    sigma_phot = cfg["rv_anchor_photospheric_fwhm_kms"] / FWHM_FACTOR
    half = cfg["rv_anchor_scan_half_kms"]
    step = cfg["rv_anchor_scan_step_kms"]
    n_grid = int(round(2.0 * half / step)) + 1
    grid = prior_rv_kms - half + step * np.arange(n_grid, dtype=np.float64)
    ones = np.ones_like(u)
    sses = np.full(n_grid, np.inf, dtype=np.float64)
    c0s = np.zeros(n_grid, dtype=np.float64)
    depths = np.zeros(n_grid, dtype=np.float64)

    for idx, v_try in enumerate(grid):
        prof = -np.exp(-0.5 * ((dv - v_try) / sigma_phot) ** 2)
        X = np.column_stack([ones, u, prof])
        try:
            beta = np.linalg.solve(X.T @ X, X.T @ f)
        except np.linalg.LinAlgError:
            continue
        c0, _c1, depth = float(beta[0]), float(beta[1]), float(beta[2])
        if depth <= 0.0 or c0 <= 0.0:
            X2 = np.column_stack([ones, u])
            b2 = np.linalg.solve(X2.T @ X2, X2.T @ f)
            res = f - (X2 @ b2)
            sses[idx], c0s[idx], depths[idx] = float(res @ res), float(b2[0]), 0.0
        else:
            res = f - (X @ beta)
            sses[idx], c0s[idx], depths[idx] = float(res @ res), c0, depth

    best_idx = int(np.argmin(sses))
    boundary_hit = (best_idx == 0) or (best_idx == n_grid - 1)
    best_v = float(grid[best_idx])
    if not boundary_hit:
        ym, y0, yp = float(sses[best_idx - 1]), float(sses[best_idx]), float(sses[best_idx + 1])
        denom = ym - 2.0 * y0 + yp
        if denom > 1e-18:
            best_v = float(grid[best_idx] + max(-0.5, min(0.5, 0.5 * (ym - yp) / denom)) * step)

    c0_best = float(c0s[best_idx])
    d_best = float(depths[best_idx])
    rel_depth = d_best / c0_best if c0_best > 0 else 0.0
    clean = (not boundary_hit) and (rel_depth >= cfg["rv_anchor_min_rel_depth"])
    return {
        "status": "CLEAN_ABSORPTION" if clean else ("BOUNDARY_HIT" if boundary_hit else "SHALLOW_OR_BLENDED"),
        "n_samples": int(len(w)),
        "grid_index": best_idx,
        "grid_points": n_grid,
        "best_rv_kms": best_v,
        "continuum_c0": c0_best,
        "depth_adu": d_best,
        "rel_depth": float(rel_depth),
        "min_sse": float(sses[best_idx]),
        "boundary_hit": bool(boundary_hit),
    }


def extract_rv_anchor_window(wave: np.ndarray, flux: np.ndarray, lab_vac_a: float, prior_rv_kms: float, cfg: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    dv = C_KMS * (wave - lab_vac_a) / lab_vac_a
    mask = np.abs(dv - prior_rv_kms) <= cfg["rv_anchor_window_kms"]
    return wave[mask].copy(), flux[mask].copy()


def compute_segment_continuum_1d(wave_seg: np.ndarray, flux_seg: np.ndarray, block_bins: int = 115, quantile_q: float = 0.84, median_blocks: int = 5) -> np.ndarray:
    n = len(wave_seg)
    if n < 12:
        return np.ones(n, dtype=np.float64)
    n_blocks = max(1, (n + block_bins - 1) // block_bins)
    centers = np.zeros(n_blocks, dtype=np.float64)
    p_quants = np.full(n_blocks, np.nan, dtype=np.float64)
    for b in range(n_blocks):
        i0, i1 = b * block_bins, min(n, (b + 1) * block_bins)
        w_sub, f_sub = wave_seg[i0:i1], flux_seg[i0:i1]
        fin_w = w_sub[np.isfinite(w_sub)]
        centers[b] = 0.5 * (float(fin_w[0]) + float(fin_w[-1])) if len(fin_w) > 0 else float(b)
        fin_f = f_sub[np.isfinite(f_sub) & (f_sub > 0)]
        if len(fin_f) >= 5:
            p_quants[b] = exact_quantile_1d(fin_f, quantile_q)
    valid_idx = np.flatnonzero(np.isfinite(p_quants) & (p_quants > 0))
    if len(valid_idx) == 0:
        return np.ones(n, dtype=np.float64)
    for b in range(n_blocks):
        if not (math.isfinite(p_quants[b]) and p_quants[b] > 0):
            p_quants[b] = p_quants[valid_idx[int(np.argmin(np.abs(valid_idx - b)))]]
    half_m = median_blocks // 2
    smoothed = np.array([exact_median_1d(p_quants[max(0, b - half_m) : min(n_blocks, b + half_m + 1)]) for b in range(n_blocks)], dtype=np.float64)
    return np.maximum(np.interp(wave_seg, centers, smoothed), 1e-12)


def compute_windowed_continuum(wave: np.ndarray, flux: np.ndarray, instrument: str, cfg: dict[str, Any]) -> np.ndarray:
    out_cont = np.full_like(flux, np.nan, dtype=np.float64)
    bsz, q_use, med_w = int(cfg["continuum_block_bins"]), float(cfg["continuum_quantile"]), int(cfg["continuum_median_blocks"])
    wins = CLEAN_HARPSN_WINDOWS_VAC_A if instrument == "HARPS_N" else CLEAN_CARMENES_WINDOWS_VAC_A
    for win in wins:
        m_win = (wave >= float(win["lo_a"]) - 15.0) & (wave <= float(win["hi_a"]) + 15.0)
        idx_w = np.flatnonzero(m_win & np.isfinite(flux) & (flux > 0))
        if len(idx_w) < 25:
            continue
        splits = np.flatnonzero(np.diff(idx_w) > 25) + 1
        for grp in np.split(idx_w, splits):
            if len(grp) < 20:
                continue
            s0, s1 = int(grp[0]), int(grp[-1]) + 1
            out_cont[s0:s1] = compute_segment_continuum_1d(wave[s0:s1], flux[s0:s1], bsz, q_use, med_w)
    return out_cont


def align_template_multiplicative(f_norm: np.ndarray, tmpl_norm: np.ndarray, window_bins: int = 201) -> np.ndarray:
    denom = np.where(np.isfinite(tmpl_norm) & (tmpl_norm > 0.05), tmpl_norm, np.nan)
    ratio = np.where(np.isfinite(f_norm) & np.isfinite(denom), f_norm / denom, 1.0)
    alpha = median_filter(ratio, size=window_bins, mode="nearest")
    return np.where(np.isfinite(tmpl_norm), alpha * tmpl_norm, np.nan)


def _convolve_discrete_gaussian_31(arr: np.ndarray, sigma_bins: float) -> np.ndarray:
    if sigma_bins <= 0.15:
        return arr.copy()
    ks = np.arange(-15, 16, dtype=np.float64)
    kern = np.exp(-0.5 * (ks / sigma_bins) ** 2)
    kern /= float(np.sum(kern))
    valid_fill = np.where(np.isfinite(arr), arr, 1.0)
    out = np.convolve(np.pad(valid_fill, (15, 15), mode="edge"), kern, mode="valid")
    return np.where(np.isfinite(arr), out, np.nan)


def build_knn_photospheric_atlas(
    target_star: str,
    star_c_ext: dict[str, np.ndarray],
    star_params: dict[str, tuple[float, float]],
    cfg: dict[str, Any],
) -> tuple[np.ndarray, list[str], list[float]]:
    t0, m0 = star_params[target_star]
    t_scl, m_scl, k_nn = float(cfg["knn_teff_scale_k"]), float(cfg["knn_mh_scale_dex"]), int(cfg["knn_atlas_neighbors"])
    dists = []
    for st, (tj, mj) in star_params.items():
        if st == target_star:
            continue
        d2 = ((t0 - tj) / t_scl) ** 2 + ((m0 - mj) / m_scl) ** 2
        dists.append((d2, st))
    dists.sort(key=lambda x: (x[0], x[1]))
    chosen = dists[: min(k_nn, len(dists))]
    nbr_names = [st for _d2, st in chosen]
    raw_w = np.array([math.exp(-0.5 * min(12.0, d2)) for d2, _st in chosen], dtype=np.float64)
    if float(np.sum(raw_w)) <= 1e-12:
        raw_w = np.ones(len(chosen), dtype=np.float64)
    weights = raw_w / float(np.sum(raw_w))
    stk = np.vstack([star_c_ext[st] for st in nbr_names])
    valid = np.isfinite(stk)
    w_col = weights[:, None]
    num = np.sum(np.where(valid, stk * w_col, 0.0), axis=0)
    den = np.sum(np.where(valid, w_col, 0.0), axis=0)
    atlas = np.where(den > 0.12, num / np.maximum(den, 1e-12), np.nan)
    return atlas, nbr_names, [round(float(w), 5) for w in weights]


def match_cross_star_atlas(wave_grid: np.ndarray, target_norm: np.ndarray, atlas_norm: np.ndarray, block_bins: int = 1000) -> tuple[np.ndarray, dict[str, float]]:
    n = len(wave_grid)
    n_blocks = max(1, (n + block_bins - 1) // block_bins)
    centers = np.zeros(n_blocks, dtype=np.float64)
    gammas = np.ones(n_blocks, dtype=np.float64)
    for b in range(n_blocks):
        i0, i1 = b * block_bins, min(n, (b + 1) * block_bins)
        centers[b] = 0.5 * (float(wave_grid[i0]) + float(wave_grid[i1 - 1]))
        t_sub, a_sub = target_norm[i0:i1], atlas_norm[i0:i1]
        cont_m = np.isfinite(t_sub) & np.isfinite(a_sub) & (a_sub >= 0.90) & (t_sub > 0.2)
        c_scl = exact_median_1d(t_sub[cont_m] / a_sub[cont_m]) if int(cont_m.sum()) >= 15 else 1.0
        t_adj = t_sub / max(0.2, c_scl)
        abs_m = np.isfinite(t_adj) & np.isfinite(a_sub) & (a_sub >= 0.10) & (a_sub <= 0.88) & (t_adj >= 0.05) & (t_adj <= 0.96)
        if int(abs_m.sum()) >= 15:
            g_val = exact_median_1d(np.log(t_adj[abs_m]) / np.log(a_sub[abs_m]))
            if math.isfinite(g_val):
                gammas[b] = min(2.40, max(0.30, g_val))
    g_smooth = np.array([exact_median_1d(gammas[max(0, b - 1) : min(n_blocks, b + 2)]) for b in range(n_blocks)], dtype=np.float64)
    gamma_vec = np.interp(wave_grid, centers, g_smooth)
    m_depth = np.where(np.isfinite(atlas_norm), np.power(np.clip(np.nan_to_num(atlas_norm, nan=1.0), 1e-4, 4.0), gamma_vec), np.nan)
    valid_all = np.isfinite(target_norm) & np.isfinite(m_depth)
    best_sig_bins, best_mad, best_full = 0.0, float("inf"), m_depth
    for sig_b in [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]:
        cand_m = _convolve_discrete_gaussian_31(m_depth, sig_b)
        diff_v = (target_norm - cand_m)[valid_all]
        mad_val = exact_mad_1d(diff_v) if len(diff_v) >= 200 else float("inf")
        if mad_val < best_mad:
            best_mad, best_sig_bins, best_full = mad_val, sig_b, cand_m
    aligned = align_template_multiplicative(target_norm, best_full, window_bins=201)
    return aligned, {"median_optical_depth_gamma": exact_median_1d(g_smooth), "best_rotational_sigma_bins": float(best_sig_bins), "post_match_mad": float(best_mad)}


def select_clean_control_injection_center(
    wave_grid: np.ndarray,
    y_primary: np.ndarray,
    atm_transm: np.ndarray,
    nominal_vac_a: float,
    berv_kms: float,
    instrument: str,
) -> float | None:
    w = np.asarray(wave_grid, dtype=np.float64)
    y = np.asarray(y_primary, dtype=np.float64)
    tr = np.asarray(atm_transm, dtype=np.float64)
    in_w = is_in_clean_windows(w, instrument)
    assert isinstance(in_w, np.ndarray)
    fin = np.isfinite(y) & np.isfinite(tr) & in_w

    def is_clean(k: int) -> bool:
        if k < 145 or k >= len(w) - 145 or not fin[k]:
            return False
        if not np.all(np.isfinite(y[k - 12 : k + 13])):
            return False
        if int(np.sum(np.isfinite(y[k - 120 : k - 12]))) < 45 or int(np.sum(np.isfinite(y[k + 13 : k + 121]))) < 45:
            return False
        if float(tr[k]) < 0.84 or float(np.min(tr[k - 4 : k + 5])) < 0.74:
            return False
        topo_a = float(w[k] / (1.0 + berv_kms / C_KMS))
        for bnd in NORTHERN_TELLURIC_BANDS_TOPO_VAC_A:
            if bnd["lo_vac_A"] - 2.5 <= topo_a <= bnd["hi_vac_A"] + 2.5:
                return False
        for ag in NORTHERN_AIRGLOW_LINES_TOPO_VAC_A:
            if abs(topo_a - ag["wave_vac_A"]) <= 1.2:
                return False
        for ch in STELLAR_CHROMOSPHERIC_VAC_A:
            if abs(float(w[k]) - ch["rest_vac_A"]) <= 1.8:
                return False
        return True

    k0 = int(np.argmin(np.abs(w - float(nominal_vac_a))))
    if is_clean(k0):
        return float(w[k0])
    for dk in range(4, 10000, 4):
        for ck in (k0 - dk, k0 + dk):
            if 145 <= ck < len(w) - 145 and is_clean(ck):
                return float(w[ck])
    return None


def _observed_fwhm_kms(dv: np.ndarray, resid: np.ndarray, peak_local_idx: int) -> float | None:
    pk = float(resid[peak_local_idx])
    if not math.isfinite(pk) or pk <= 0.0:
        return None
    half = 0.5 * pk
    left, right = peak_local_idx, peak_local_idx
    while left > 0 and resid[left] > half:
        left -= 1
    while right < len(resid) - 1 and resid[right] > half:
        right += 1
    if resid[left] > half or resid[right] > half:
        return None
    def ic(ia: int, ib: int) -> float:
        ya, yb = float(resid[ia]), float(resid[ib])
        return float(dv[ia]) if yb == ya else float(dv[ia] + (half - ya) * (dv[ib] - dv[ia]) / (yb - ya))
    width = ic(right - 1, right) - ic(left, left + 1)
    return float(width) if width > 0 else None


def fit_lsf_on_window(
    w_win: np.ndarray,
    y_win: np.ndarray,
    seed_center_wave_a: float,
    cfg: dict[str, Any],
    fixed_phase_bins: float | None = None,
) -> dict[str, Any]:
    w = np.asarray(w_win, dtype=np.float64)
    y = np.asarray(y_win, dtype=np.float64)
    if len(w) < 41 or not np.all(np.isfinite(w)):
        return {"valid_fit": False}
    fin_y = np.isfinite(y)
    dv = C_KMS * (w - seed_center_wave_a) / seed_center_wave_a
    sig_v = float(cfg["sigma_v_kms"])
    core_mask = fin_y & (np.abs(dv) <= cfg["core_sigma_mult"] * sig_v)
    mid_mask = fin_y & (np.abs(dv) > cfg["mid_inner_sigma_mult"] * sig_v) & (np.abs(dv) <= cfg["mid_outer_sigma_mult"] * sig_v)
    out_mask = fin_y & (np.abs(dv) > cfg["outer_inner_sigma_mult"] * sig_v) & (np.abs(dv) <= cfg["outer_outer_sigma_mult"] * sig_v)
    raw_core = np.abs(dv) <= cfg["core_sigma_mult"] * sig_v
    if int(raw_core.sum()) < 5 or int(core_mask.sum()) < max(5, int(raw_core.sum()) - 1):
        return {"valid_fit": False}

    def sb_stats(mask: np.ndarray) -> tuple[float, float, float, bool]:
        ml, mr = mask & (dv < 0), mask & (dv > 0)
        if int(ml.sum()) < 6 or int(mr.sum()) < 6:
            return 0.0, 0.0, float("nan"), False
        slp = (exact_median_1d(y[mr]) - exact_median_1d(y[ml])) / (exact_median_1d(dv[mr]) - exact_median_1d(dv[ml]))
        icp = exact_median_1d(y[mask] - slp * dv[mask])
        mad_v = exact_mad_1d(y[mask] - (icp + slp * dv[mask]))
        return float(icp), float(slp), float(mad_v), bool(math.isfinite(mad_v) and mad_v > 0.0)

    b_mid, s_mid, mad_mid, ok_m = sb_stats(mid_mask)
    b_out, s_out, mad_out, ok_o = sb_stats(out_mask)
    if (not ok_m) or (not ok_o):
        return {"valid_fit": False}

    step_a = float(exact_median_1d(np.diff(w)))
    dv_core = dv[core_mask]
    r_mid = y[core_mask] - (b_mid + s_mid * dv_core)
    r_out = y[core_mask] - (b_out + s_out * dv_core)
    phases = [fixed_phase_bins] if fixed_phase_bins is not None else cfg["fit_phases_bins"]
    best = None
    for ph in phases:
        ctr = float(seed_center_wave_a + float(ph) * step_a)
        v_ph = C_KMS * (ctr - seed_center_wave_a) / seed_center_wave_a
        g = np.exp(-0.5 * ((dv_core - v_ph) / sig_v) ** 2)
        gg = float(g @ g)
        rg_m, rg_o = float(r_mid @ g), float(r_out @ g)
        amp_m, amp_o = max(0.0, rg_m / gg), max(0.0, rg_o / gg)
        exp_sq = amp_m * amp_m * gg
        rr_m = float(r_mid @ r_mid)
        cos_m = rg_m / math.sqrt(gg * rr_m) if rr_m > 0.0 else 0.0
        cand = {"phase_bins": float(ph), "fitted_center_a": ctr, "amp_mid": float(amp_m), "amp_outer": float(amp_o), "explained_mid": float(exp_sq), "cosine_mid": float(cos_m)}
        if best is None or exp_sq > best["explained_mid"]:
            best = cand
    assert best is not None
    y_cln = np.where(fin_y, y - (b_mid + s_mid * dv), 0.0)
    c_idx = np.flatnonzero(core_mask)
    pk_idx = int(c_idx[int(np.argmax(y_cln[c_idx]))])
    fwhm_obs = _observed_fwhm_kms(dv, y_cln, pk_idx)
    snr_mid = best["amp_mid"] / mad_mid
    snr_out = best["amp_outer"] / mad_out
    amp_rat = best["amp_outer"] / best["amp_mid"] if best["amp_mid"] > 0 else 0.0
    return {
        "valid_fit": True,
        "seed_wave_a": float(seed_center_wave_a),
        "step_a": step_a,
        "phase_bins": best["phase_bins"],
        "fitted_center_a": best["fitted_center_a"],
        "amp_mid": best["amp_mid"],
        "amp_outer": best["amp_outer"],
        "mad_mid": mad_mid,
        "mad_outer": mad_out,
        "snr_mid": float(snr_mid),
        "snr_outer": float(snr_out),
        "amp_outer_over_mid": float(amp_rat),
        "cosine_mid": best["cosine_mid"],
        "fwhm_obs_kms": fwhm_obs,
        "fwhm_over_lsf": float(fwhm_obs / cfg["fwhm_v_kms"]) if fwhm_obs is not None else None,
        "b_mid": b_mid,
        "s_mid": s_mid,
        "b_outer": b_out,
        "s_outer": s_out,
    }


def compute_supraphotospheric_f1_window(wave_win: np.ndarray, flux_norm_win: np.ndarray, target_wave_a: float, min_fn_pk3: float = 1.010) -> dict[str, Any]:
    w, f = np.asarray(wave_win, dtype=np.float64), np.asarray(flux_norm_win, dtype=np.float64)
    if len(w) < 41:
        return {"c80": 0.0, "fn_kl": 0.0, "fn_pk3": 0.0, "f1_supraphotospheric_pass": False}
    kl = int(np.argmin(np.abs(w - target_wave_a)))
    if kl < 15 or kl >= len(w) - 15 or not np.all(np.isfinite(f[kl - 1 : kl + 2])):
        return {"c80": 0.0, "fn_kl": 0.0, "fn_pk3": 0.0, "f1_supraphotospheric_pass": False}
    idx = np.abs(np.arange(len(w)) - kl)
    sb = (idx >= 12) & (idx <= 70) & np.isfinite(f)
    if int(sb.sum()) < 15:
        return {"c80": 0.0, "fn_kl": 0.0, "fn_pk3": 0.0, "f1_supraphotospheric_pass": False}
    c80 = exact_quantile_1d(f[sb], 0.80)
    if not math.isfinite(c80) or c80 <= 0.0:
        return {"c80": 0.0, "fn_kl": 0.0, "fn_pk3": 0.0, "f1_supraphotospheric_pass": False}
    fn = f / c80
    fn_pk3 = float(np.max(fn[kl - 1 : kl + 2]))
    return {"c80": float(c80), "fn_kl": float(fn[kl]), "fn_pk3": fn_pk3, "f1_supraphotospheric_pass": bool(fn_pk3 >= min_fn_pk3)}


def _runs_bool(mask: np.ndarray) -> list[tuple[int, int]]:
    d = np.diff(np.r_[False, np.asarray(mask, dtype=bool), False].astype(int))
    return list(zip(np.flatnonzero(d == 1).tolist(), np.flatnonzero(d == -1).tolist()))


def check_channel_lsf_gate(fit: dict[str, Any], channel: str, cfg: dict[str, Any]) -> bool:
    if not fit.get("valid_fit"):
        return False
    pfx = {"T": "channel_t", "P": "channel_p", "T_DIFF": "channel_tdiff", "K_PLANET": "channel_kplanet"}[channel]
    if fit["snr_mid"] < cfg[f"{pfx}_snr_mid_min"] or fit["snr_outer"] < cfg[f"{pfx}_snr_outer_min"]:
        return False
    if not (cfg[f"{pfx}_amp_ratio_min"] <= fit["amp_outer_over_mid"] <= cfg[f"{pfx}_amp_ratio_max"]):
        return False
    if fit["cosine_mid"] < cfg[f"{pfx}_cosine_min"]:
        return False
    if fit["fwhm_over_lsf"] is None or not (cfg[f"{pfx}_fwhm_ratio_min"] <= fit["fwhm_over_lsf"] <= cfg[f"{pfx}_fwhm_ratio_max"]):
        return False
    return True


def scan_residual_spectrum_g1(
    wave: np.ndarray,
    y_primary: np.ndarray,
    y_secondary_check: np.ndarray | None,
    channel: str,
    cfg: dict[str, Any],
    flux_norm_for_f1: np.ndarray | None = None,
    enforce_f1_in_g1: bool = True,
) -> tuple[list[dict[str, Any]], int, int]:
    in_win = is_in_clean_windows(wave, cfg["instrument"])
    assert isinstance(in_win, np.ndarray)
    margin = int(cfg["scan_margin_bins"])
    prelim_pre_f1 = []
    searched_bins = 0
    min_fn_pk3 = float(cfg["supraphotospheric_min_fn_pk3"])

    for a, b in _runs_bool(in_win):
        if b - a < 2 * margin + 1:
            continue
        y_seg = y_primary[a:b]
        fin_seg = np.isfinite(y_seg)
        if y_secondary_check is not None:
            fin_seg &= np.isfinite(y_secondary_check[a:b])
        if flux_norm_for_f1 is not None:
            fin_seg &= np.isfinite(flux_norm_for_f1[a:b])
        if int(fin_seg.sum()) < 200:
            continue
        idx_f = np.flatnonzero(fin_seg)
        vals_fill = np.interp(np.arange(len(y_seg)), idx_f, y_seg[idx_f])
        med = median_filter(vals_fill, size=101, mode="nearest")
        resid = vals_fill - med
        mad = MAD_NORM * median_filter(np.abs(resid), size=101, mode="nearest")
        elig = np.zeros(len(y_seg), dtype=bool)
        elig[margin:-margin] = fin_seg[margin:-margin] & np.isfinite(mad[margin:-margin]) & (mad[margin:-margin] > 0)
        searched_bins += int(elig.sum())
        localmax = np.r_[False, (resid[1:-1] > resid[:-2]) & (resid[1:-1] >= resid[2:]), False]
        seeds = np.flatnonzero(localmax & elig & (resid >= cfg["prescreen_local_mad"] * mad))
        for j in seeds:
            k = a + int(j)
            w0 = float(wave[k])
            ws = slice(k - margin, k + margin + 1)
            fit = fit_lsf_on_window(wave[ws], y_primary[ws], w0, cfg)
            if not check_channel_lsf_gate(fit, channel, cfg):
                continue
            if channel == "T":
                assert y_secondary_check is not None
                cf = fit_lsf_on_window(wave[ws], y_secondary_check[ws], w0, cfg, fixed_phase_bins=fit["phase_bins"])
                if not cf.get("valid_fit"):
                    continue
                crat = cf["amp_mid"] / fit["amp_mid"] if fit["amp_mid"] > 0 else 0.0
                if crat < cfg["channel_t_cross_amp_ratio_min"] or cf["snr_mid"] < cfg["channel_t_cross_snr_min"]:
                    continue
                fit["cross_amp_mid"], fit["cross_snr_mid"], fit["cross_over_self_amp_ratio"] = cf["amp_mid"], cf["snr_mid"], float(crat)
            else:
                fit["cross_amp_mid"], fit["cross_snr_mid"], fit["cross_over_self_amp_ratio"] = fit["amp_mid"], fit["snr_mid"], 1.0

            if flux_norm_for_f1 is not None:
                f1r = compute_supraphotospheric_f1_window(wave[ws], flux_norm_for_f1[ws], fit["fitted_center_a"], min_fn_pk3)
                fit["target_fn_pk3"], fit["g1_f1_pass"] = f1r["fn_pk3"], f1r["f1_supraphotospheric_pass"]
            else:
                fit["target_fn_pk3"], fit["g1_f1_pass"] = None, True
            fit["seed_index"], fit["channel"] = int(k), channel
            prelim_pre_f1.append(fit)

    dedup = []
    for h in sorted(prelim_pre_f1, key=lambda x: (-x["snr_mid"], x["seed_index"])):
        fwhm_a = h["fitted_center_a"] / cfg["resolving_power"]
        if any(abs(h["fitted_center_a"] - p["fitted_center_a"]) <= 1.5 * fwhm_a for p in dedup):
            continue
        dedup.append(h)
    dedup.sort(key=lambda x: x["seed_index"])
    acc = [h for h in dedup if h.get("g1_f1_pass", True)] if enforce_f1_in_g1 else dedup
    return acc, searched_bins, len(dedup)


def evaluate_gate_g2_northern_atmosphere(
    fitted_bary_vac_a: float,
    berv_kms: float,
    s1d_wave_win: np.ndarray,
    s1d_atm_transm_win: np.ndarray,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    topo_a = float(fitted_bary_vac_a / (1.0 + berv_kms / C_KMS))
    reasons = []
    for band in NORTHERN_TELLURIC_BANDS_TOPO_VAC_A:
        if float(band["lo_vac_A"]) <= topo_a <= float(band["hi_vac_A"]):
            reasons.append(f"TELLURIC_{band['name']}")
    best_line, best_sep = None, 1e9
    for item in NORTHERN_AIRGLOW_LINES_TOPO_VAC_A:
        sep = abs(topo_a - float(item["wave_vac_A"]))
        if sep < best_sep:
            best_sep, best_line = sep, item["name"]
    if best_sep <= cfg["gate_g2_airglow_tol_angstrom"]:
        reasons.append(f"AIRGLOW_{best_line}")

    w = np.asarray(s1d_wave_win, dtype=np.float64)
    tr = np.asarray(s1d_atm_transm_win, dtype=np.float64)
    atm_ctr, atm_min3 = 1.0, 1.0
    if len(w) >= 25:
        kc = int(np.argmin(np.abs(w - fitted_bary_vac_a)))
        if 6 <= kc < len(w) - 6:
            atm_ctr = float(tr[kc]) if math.isfinite(tr[kc]) else 0.0
            tr3 = tr[kc - 3 : kc + 4]
            atm_min3 = float(np.min(tr3[np.isfinite(tr3)])) if np.any(np.isfinite(tr3)) else 0.0
            if atm_ctr < cfg["gate_g2_min_atm_transm_center"]:
                reasons.append("LOW_ATM_TRANSM_CENTER")
            if atm_min3 < cfg["gate_g2_min_atm_transm_3px"]:
                reasons.append("DEEP_TELLURIC_WING_ADJACENCY")
    g2_pass = len(reasons) == 0
    return {
        "topo_vac_a": topo_a,
        "nearest_airglow_name": best_line,
        "nearest_airglow_sep_a": float(best_sep),
        "atm_transm_center": float(atm_ctr),
        "atm_transm_min3": float(atm_min3),
        "g2_pass": g2_pass,
        "g2_reason": "PASS" if g2_pass else ";".join(reasons),
    }


def evaluate_native_2d_order_patch(
    wave_ord_win: np.ndarray,
    flux_ord_win: np.ndarray,
    ref_ord_win: np.ndarray | None,
    target_bary_vac_a: float,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    w = np.asarray(wave_ord_win, dtype=np.float64)
    f = np.asarray(flux_ord_win, dtype=np.float64)
    if len(w) < 41 or not np.all(np.isfinite(w)):
        return {"usable": False}
    k_loc = int(np.argmin(np.abs(w - target_bary_vac_a)))
    if k_loc < 15 or k_loc >= len(w) - 15 or not np.all(np.isfinite(f[k_loc - 5 : k_loc + 6])):
        return {"usable": False}
    idx = np.arange(len(w)) - k_loc
    sb = (np.abs(idx) >= 12) & (np.abs(idx) <= 70) & np.isfinite(f) & (f > 0)
    if int(sb.sum()) < 20:
        return {"usable": False}
    cont_adu = exact_quantile_1d(f[sb], 0.80)
    if not math.isfinite(cont_adu) or cont_adu <= 0.0:
        return {"usable": False}
    f_norm = f / cont_adu
    native_fn_pk3 = float(np.max(f_norm[k_loc - 1 : k_loc + 2]))

    scale = 1.0
    r_ref_clean = None
    if ref_ord_win is not None:
        r_ref = np.asarray(ref_ord_win, dtype=np.float64)
        vsb = sb & np.isfinite(r_ref) & (r_ref > 0.05)
        scale = exact_median_1d(f_norm[vsb] / r_ref[vsb]) if int(vsb.sum()) >= 10 else 1.0
        r_ref_clean = np.where(np.isfinite(r_ref), r_ref, 1.0)
        y = np.where(np.isfinite(f_norm), f_norm - scale * r_ref_clean, np.nan)
    else:
        y = np.where(np.isfinite(f_norm), f_norm - 1.0, np.nan)

    ml, mr = (idx >= -70) & (idx <= -12) & np.isfinite(y), (idx >= 12) & (idx <= 70) & np.isfinite(y)
    if int(ml.sum()) < 6 or int(mr.sum()) < 6:
        return {"usable": False}
    slope = (exact_median_1d(y[mr]) - exact_median_1d(y[ml])) / (exact_median_1d(idx[mr].astype(np.float64)) - exact_median_1d(idx[ml].astype(np.float64)))
    intercept = exact_median_1d(y[ml | mr] - slope * idx[ml | mr])
    det = np.where(np.isfinite(y), y - (intercept + slope * idx), 0.0)
    mad_sb = exact_mad_1d((y - (intercept + slope * idx))[ml | mr])
    if not math.isfinite(mad_sb) or mad_sb <= 0:
        return {"usable": False}

    sig_a = target_bary_vac_a / (cfg["resolving_power"] * FWHM_FACTOR)
    c_sl = slice(max(0, k_loc - 6), min(len(w), k_loc + 7))
    g = np.exp(-0.5 * ((w[c_sl] - target_bary_vac_a) / sig_a) ** 2)
    gg = float(g @ g)
    amp_rel = max(0.0, float(det[c_sl] @ g) / gg)
    snr_native = amp_rel / mad_sb

    template_dip_frac = 0.0
    if r_ref_clean is not None and amp_rel > 0.0:
        dv = C_KMS * (w - target_bary_vac_a) / target_bary_vac_a
        sig_v = float(cfg["sigma_v_kms"])
        nsl, nsr = (dv >= -10.0 * sig_v) & (dv <= -4.0 * sig_v), (dv >= 4.0 * sig_v) & (dv <= 10.0 * sig_v)
        if int(nsl.sum()) >= 2 and int(nsr.sum()) >= 2:
            nt = -scale * r_ref_clean
            slp_nt = (exact_median_1d(nt[nsr]) - exact_median_1d(nt[nsl])) / (exact_median_1d(dv[nsr]) - exact_median_1d(dv[nsl]))
            icp_nt = exact_median_1d(nt[nsl | nsr] - slp_nt * dv[nsl | nsr])
            det_nt = nt - (icp_nt + slp_nt * dv)
            cnt = np.abs(dv) <= 3.0 * sig_v
            gnt = np.exp(-0.5 * (dv[cnt] / sig_v) ** 2)
            gg_nt = float(gnt @ gnt)
            amp_nt = max(0.0, float(det_nt[cnt] @ gnt) / gg_nt) if gg_nt > 0 else 0.0
            template_dip_frac = float(amp_nt / max(1e-12, amp_rel))

    k_pk = (k_loc - 2) + int(np.argmax(det[k_loc - 2 : k_loc + 3]))
    r_pk = float(det[k_pk])
    pos7 = float(np.sum(np.maximum(0.0, det[k_pk - 3 : k_pk + 4])))
    eta_1px = (r_pk / pos7) if (r_pk > 0 and pos7 > 0) else 1.0
    lw = float(det[k_pk - 1]) / r_pk if r_pk > 0 else -1.0
    rw = float(det[k_pk + 1]) / r_pk if r_pk > 0 else -1.0
    min_wing = min(lw, rw)

    w11, d11 = w[k_loc - 5 : k_loc + 6], det[k_loc - 5 : k_loc + 6]
    d11_norm = float(math.sqrt(float(d11 @ d11)))
    step_px_a = float(exact_median_1d(np.diff(w11)))
    best_cos11 = -1.0
    for iph in range(-12, 13):
        w_try = float(w[k_loc]) + (0.125 * iph) * step_px_a
        g11 = np.exp(-0.5 * ((w11 - w_try) / sig_a) ** 2)
        g11n = float(math.sqrt(float(g11 @ g11)))
        if d11_norm > 0 and g11n > 0:
            c11 = float(d11 @ g11) / (d11_norm * g11n)
            if c11 > best_cos11:
                best_cos11 = c11

    adj_mean = 0.5 * (max(0.0, float(det[k_pk - 1])) + max(0.0, float(det[k_pk + 1])))
    hotpx_ratio = (r_pk / max(1e-9, adj_mean)) if r_pk > 0 else 99.0
    far_wing_34 = 0.25 * float(det[k_pk - 4] + det[k_pk - 3] + det[k_pk + 3] + det[k_pk + 4]) / r_pk if r_pk > 0 else 99.0
    return {
        "usable": True,
        "continuum_adu": float(cont_adu),
        "continuum_snr": float(1.0 / mad_sb),
        "native_fn_pk3": native_fn_pk3,
        "template_dip_frac": float(template_dip_frac),
        "native_amp_rel": float(amp_rel),
        "native_snr": float(snr_native),
        "eta_1px": float(eta_1px),
        "min_wing_ratio": float(min_wing),
        "cos_1d_11px": float(best_cos11),
        "hotpx_ratio": float(hotpx_ratio),
        "far_wing_34_ratio": float(far_wing_34),
    }


def evaluate_gates_g3_g4_g5_northern(
    order_patches: list[dict[str, Any]],
    stellar_rest_vac_a: float,
    cross_star_ridge_count: int,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    evaluated = []
    for p in order_patches:
        res = evaluate_native_2d_order_patch(
            np.asarray(p["wave"], dtype=np.float64),
            np.asarray(p["flux"], dtype=np.float64),
            np.asarray(p["ref_norm"], dtype=np.float64) if p.get("ref_norm") is not None else None,
            float(p["target_wave_a"]),
            cfg,
        )
        if res.get("usable"):
            res["order"] = int(p["order"])
            res["native_px"] = int(p["native_px"])
            res["n_px"] = int(p.get("n_px", 4096))
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

    # Gate G3_V35
    g3_reasons = []
    if prim["native_snr"] < cfg["gate_g3_native_snr_min"]:
        g3_reasons.append("REBIN_OR_LOW_NATIVE_SNR")
    if prim["eta_1px"] > cfg["gate_g3_max_single_px_fraction"]:
        g3_reasons.append("SUB_LSF_SINGLE_PIXEL_SPIKE")
    if prim["min_wing_ratio"] < cfg["gate_g3_min_bilateral_wing_ratio"]:
        g3_reasons.append("ASYMMETRIC_CCD_COSMIC_SPIKE")
    if prim["native_fn_pk3"] < cfg["supraphotospheric_min_fn_pk3"]:
        g3_reasons.append("SUB_CONTINUUM_OR_TELLURIC_DIP_GHOST")
    if prim["template_dip_frac"] > cfg["gate_g3_max_template_dip_fraction"]:
        g3_reasons.append("TEMPLATE_ABSORPTION_DIP_GHOST")

    chrom_hit = None
    for ch in STELLAR_CHROMOSPHERIC_VAC_A:
        tol = 1.25 if any(x in ch["name"] for x in ("Halpha", "Hbeta", "CaII", "NaID", "HeI")) else cfg["gate_g3_chromospheric_tol_angstrom"]
        if abs(stellar_rest_vac_a - float(ch["rest_vac_A"])) <= tol:
            chrom_hit = ch["name"]
            break
    if chrom_hit is not None:
        g3_reasons.append(f"STELLAR_CHROMOSPHERIC_{chrom_hit}")

    if int(cross_star_ridge_count) > int(cfg["gate_g3_cross_star_ridge_max_stars"]):
        g3_reasons.append(f"MULTI_STAR_MOLECULAR_BANDHEAD_{cross_star_ridge_count}STARS")
    g3_pass = len(g3_reasons) == 0

    # Gate G4_V35: CCD border & multi-order overlap consistency
    g4_reasons = []
    margin = int(cfg["gate_g4_chip_edge_margin_px"])
    if not (margin <= prim["native_px"] <= (prim["n_px"] - 1 - margin)):
        g4_reasons.append("CCD_ORDER_BORDER_DROOP")
    ov_m = int(cfg["gate_g4_overlap_edge_margin_px"])
    qual_orders = [
        e for e in evaluated
        if (ov_m <= e["native_px"] <= (e["n_px"] - 1 - ov_m))
        and (e["continuum_adu"] >= cfg["gate_g4_secondary_flux_ratio_min"] * prim["continuum_adu"])
        and (e["continuum_snr"] >= cfg["gate_g4_secondary_cont_snr_min"])
    ]
    dedup_q, seen_o = [], set()
    for qo in qual_orders:
        if qo["order"] not in seen_o:
            dedup_q.append(qo)
            seen_o.add(qo["order"])
    overlap_tested = len(dedup_q) >= 2 and dedup_q[0]["order"] == prim["order"]
    sec_snr, sec_contrast = None, None
    if overlap_tested:
        sec = dedup_q[1]
        sec_snr = sec["native_snr"]
        sec_contrast = sec["native_amp_rel"] / max(1e-12, prim["native_amp_rel"])
        if sec_snr < cfg["gate_g4_secondary_snr_min"] or not (cfg["gate_g4_order_contrast_ratio_min"] <= sec_contrast <= cfg["gate_g4_order_contrast_ratio_max"]):
            g4_reasons.append("SINGLE_ORDER_CCD_ARTIFACT")
    g4_pass = len(g4_reasons) == 0

    # Gate G5_V35: 11-px CCD LSF morphology
    g5_reasons = []
    if prim["cos_1d_11px"] < cfg["gate_g5_ccd_cos11_min"]:
        g5_reasons.append("CCD_11PX_LSF_COSINE_MISMATCH")
    if prim["hotpx_ratio"] > cfg["gate_g5_ccd_max_hotpx_ratio"]:
        g5_reasons.append("CCD_COSMIC_RAY_OR_HOT_PIXEL")
    if prim["far_wing_34_ratio"] > cfg["gate_g5_ccd_far_wing_34_max"]:
        g5_reasons.append("BROAD_BANDHEAD_OR_FLATFIELD_PLATEAU")
    g5_pass = len(g5_reasons) == 0

    return {
        "n_covering_orders": len(seen_o) if seen_o else len(evaluated),
        "primary_order": prim["order"],
        "primary_native_px": prim["native_px"],
        "primary_continuum_adu": prim["continuum_adu"],
        "primary_native_fn_pk3": prim["native_fn_pk3"],
        "primary_template_dip_frac": prim["template_dip_frac"],
        "primary_native_snr": prim["native_snr"],
        "primary_eta_1px": prim["eta_1px"],
        "primary_min_wing_ratio": prim["min_wing_ratio"],
        "chromospheric_match": chrom_hit,
        "cross_star_ridge_count": int(cross_star_ridge_count),
        "g3_pass": g3_pass,
        "g3_reason": "PASS" if g3_pass else ";".join(g3_reasons),
        "overlap_tested": bool(overlap_tested),
        "secondary_order": dedup_q[1]["order"] if overlap_tested else None,
        "secondary_native_snr": float(sec_snr) if sec_snr is not None else None,
        "secondary_over_primary_contrast": float(sec_contrast) if sec_contrast is not None else None,
        "g4_pass": g4_pass,
        "g4_reason": "PASS" if g4_pass else ";".join(g4_reasons),
        "cos_1d_11px": prim["cos_1d_11px"],
        "hotpx_ratio": prim["hotpx_ratio"],
        "far_wing_34_ratio": prim["far_wing_34_ratio"],
        "g5_pass": g5_pass,
        "g5_reason": "PASS" if g5_pass else ";".join(g5_reasons),
    }


def evaluate_gate_g6_cross_star_coincidence(
    target_star: str,
    instrument: str,
    cand_topo_vac_a: float,
    cand_order: int | None,
    cand_px: int | None,
    target_vshift_kms: float,
    topo_excess_atlas: list[dict[str, Any]],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """V3.5 Automated Cross-Star Topocentric Wavelength & Native (order, pixel) Coincidence Gate.

    `topo_excess_atlas` contains narrow local topocentric emission/warm-pixel detections
    extracted per exposure across the same instrument's cohort after subtracting each star's
    k-NN photospheric template in the topocentric frame:
      {"star", "vshift_kms", "topo_vac_a", "order", "px", "prom_rel", "snr_local"}
    where vshift_kms = rv_star_kms - berv_kms.
    """
    partners = RESOLVED_BINARY_PARTNERS.get(target_star, set())
    topo_tol = float(cfg["gate_g6_topo_tol_angstrom"])
    px_tol = float(cfg["gate_g6_pixel_tol_px"])
    min_dv = float(cfg["gate_g6_min_dv_frame_sep_kms"])
    prom_min = float(cfg["gate_g6_other_prom_min"])
    snr_min = float(cfg["gate_g6_other_snr_min"])

    topo_stars: set[str] = set()
    pixel_stars: set[str] = set()
    all_stars: set[str] = set()

    for rec in topo_excess_atlas:
        other = rec["star"]
        if other == target_star or other in partners:
            continue
        if abs(float(rec["vshift_kms"]) - float(target_vshift_kms)) < min_dv:
            continue
        if float(rec["prom_rel"]) < prom_min or float(rec["snr_local"]) < snr_min:
            continue
        matched = False
        if abs(float(rec["topo_vac_a"]) - float(cand_topo_vac_a)) <= topo_tol:
            topo_stars.add(other)
            matched = True
        if (
            cand_order is not None
            and cand_px is not None
            and rec.get("order") is not None
            and rec.get("px") is not None
            and int(rec["order"]) == int(cand_order)
            and abs(float(rec["px"]) - float(cand_px)) <= px_tol
        ):
            pixel_stars.add(other)
            matched = True
        if matched:
            all_stars.add(other)

    n_coinc = len(all_stars)
    g6_pass = n_coinc <= int(cfg["gate_g6_max_other_stars"])
    if g6_pass:
        reason = "PASS"
    elif len(pixel_stars) > len(topo_stars):
        reason = f"CROSS_STAR_FIXED_ORDER_PIXEL_{n_coinc}STARS"
    else:
        reason = f"CROSS_STAR_TOPO_AIRGLOW_OR_PIXEL_{n_coinc}STARS"

    return {
        "g6_coincident_topo_stars": len(topo_stars),
        "g6_coincident_pixel_stars": len(pixel_stars),
        "g6_coincident_total_stars": n_coinc,
        "g6_coincident_star_list": sorted(all_stars)[:12],
        "g6_pass": bool(g6_pass),
        "g6_reason": reason,
    }


def stellar_northern_continuum_flam_earth(
    wave_vac_a: float,
    phot_g_mag: float,
    j_mag: float,
    teff_k: float,
) -> float:
    """Piecewise continuous Gaia DR3 G (< 8500 A, matching D079-D081) and 2MASS J (>= 8500 A,
    matching D082) Planck-sloped continuum flux density F_lambda in erg cm^-2 s^-1 A^-1."""
    if float(wave_vac_a) < RADIOMETRIC_GJ_SPLIT_A:
        piv_a, zp, mag = GAIA_G_PIVOT_A, GAIA_G_ZP_FLAM, float(phot_g_mag)
    else:
        piv_a, zp, mag = TWOMASS_J_PIVOT_A, TWOMASS_J_ZP_FLAM, float(j_mag)
    xw = HC_OVER_K_ANGSTROM_KELVIN / (float(wave_vac_a) * float(teff_k))
    xp = HC_OVER_K_ANGSTROM_KELVIN / (piv_a * float(teff_k))
    b_ratio = ((piv_a / float(wave_vac_a)) ** 5) * math.expm1(xp) / math.expm1(xw)
    return float(zp * (10.0 ** (-0.4 * mag)) * b_ratio)


def compute_northern_laser_power_limits(
    wave_vac_a: float,
    amp_rel_lim: float,
    phot_g_mag: float,
    j_mag: float,
    teff_k: float,
    dist_pc: float,
    cfg: dict[str, Any],
) -> dict[str, float]:
    fwhm_a = float(wave_vac_a) / float(cfg["resolving_power"])
    gauss_area = math.sqrt(math.pi / (4.0 * math.log(2.0)))
    ew_a = gauss_area * float(amp_rel_lim) * fwhm_a
    flam = stellar_northern_continuum_flam_earth(wave_vac_a, phot_g_mag, j_mag, teff_k)
    f_line_cgs = flam * ew_a
    d_cm = float(dist_pc) * PC_CM
    l_iso_w = 4.0 * math.pi * (d_cm ** 2) * f_line_cgs * 1.0e-7
    lam_m = float(wave_vac_a) * 1.0e-10
    d_tx_m = float(cfg["tx_aperture_diameter_m"])
    airy_gain = (math.pi * d_tx_m / lam_m) ** 2
    p_beam_10m_w = l_iso_w / airy_gain
    return {
        "fwhm_lsf_a": float(fwhm_a),
        "ew_lim_mA": float(ew_a * 1000.0),
        "continuum_flam_cgs": float(flam),
        "flux_lim_erg_cm2_s": float(f_line_cgs),
        "l_iso_mw": float(l_iso_w * 1.0e-6),
        "p_beam_10m_w": float(p_beam_10m_w),
        "p_beam_10m_kw": float(p_beam_10m_w * 1.0e-3),
    }


def run_legacy_v2_northern_benchmark(wave: np.ndarray, flux: np.ndarray, cfg: dict[str, Any]) -> dict[str, Any]:
    w = np.asarray(wave, dtype=np.float64)
    f = np.asarray(flux, dtype=np.float64)
    in_win = is_in_clean_windows(w, cfg["instrument"])
    assert isinstance(in_win, np.ndarray)
    margin = 100
    prelim, screened, searched = [], 0, 0
    for a, b in _runs_bool(in_win):
        if b - a < 2 * margin + 1:
            continue
        f_seg = f[a:b]
        fin = np.isfinite(f_seg) & (f_seg > 0)
        if int(fin.sum()) < 200:
            continue
        idx_f = np.flatnonzero(fin)
        vals = np.interp(np.arange(len(f_seg)), idx_f, f_seg[idx_f])
        med = median_filter(vals, size=101, mode="nearest")
        resid = vals - med
        mad = 1.4826 * median_filter(np.abs(resid), size=101, mode="nearest")
        elig = np.zeros(len(vals), dtype=bool)
        elig[margin:-margin] = fin[margin:-margin] & np.isfinite(mad[margin:-margin]) & (mad[margin:-margin] > 0)
        searched += int(elig.sum())
        localmax = np.r_[False, (resid[1:-1] > resid[:-2]) & (resid[1:-1] >= resid[2:]), False]
        seeds = np.flatnonzero(localmax & elig & (resid >= 3.0 * mad))
        screened += len(seeds)
        offsets = np.r_[np.arange(-50, -12), np.arange(13, 51)]
        x_sb = offsets.astype(np.float64)
        left, right = x_sb < 0, x_sb > 0
        core = np.arange(-12, 13)
        for j in seeds:
            k = a + int(j)
            side = f[k + offsets]
            if not np.all(np.isfinite(side)) or not np.all(np.isfinite(f[k + core])):
                continue
            slope = (np.median(side[right]) - np.median(side[left])) / (np.median(x_sb[right]) - np.median(x_sb[left]))
            icp = float(np.median(side - slope * x_sb))
            noise = float(1.4826 * np.median(np.abs((side - icp - slope * x_sb) - np.median(side - icp - slope * x_sb))))
            if not math.isfinite(noise) or noise <= 0:
                continue
            r_core = f[k + core] - icp - slope * core
            loc_step = float(np.median(np.diff(w[k - 50 : k + 51])))
            fwhm = float(w[k] / cfg["resolving_power"])
            sigma = fwhm / FWHM_FACTOR
            best = None
            for ph in (-0.5, -0.25, 0.0, 0.25, 0.5):
                ctr = float(w[k] + ph * loc_step)
                g = np.exp(-0.5 * ((w[k + core] - ctr) / sigma) ** 2)
                gg, rg = float(g @ g), float(r_core @ g)
                amp = max(0.0, rg / gg)
                cos = rg / math.sqrt(gg * float(r_core @ r_core)) if float(r_core @ r_core) > 0 else 0.0
                cnd = (amp * amp * gg, ctr, amp, cos, fwhm)
                if best is None or cnd[0] > best[0]:
                    best = cnd
            assert best is not None
            snr_v2 = best[2] / noise
            if snr_v2 >= 6.0 and best[3] >= 0.80:
                prelim.append({"seed_index": k, "center_a": best[1], "snr": snr_v2, "fwhm": best[4]})
    accepted = []
    for e in sorted(prelim, key=lambda x: (-x["snr"], x["seed_index"])):
        if any(abs(e["center_a"] - p["center_a"]) <= max(e["fwhm"], p["fwhm"]) for p in accepted):
            continue
        accepted.append(e)
    return {"searched_samples": searched, "screened_events": screened, "accepted_hits": len(accepted)}
