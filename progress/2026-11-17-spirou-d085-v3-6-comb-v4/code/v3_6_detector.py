#!/usr/bin/env python3
"""SPIROU_V3_6_AND_COMB_V4: Single-Line (V3.6) & Coherent Frequency-Comb (V4) NIR YJHK Detector (Phase D085).

Designed for CFHT 3.6 m SPIRou APERO 0.7.295 (`*t.fits`, 0.955-2.515 um YJHK across 49 x 4088 echelle
orders on a cryogenic Teledyne Hawaii-4RG detector at Maunakea, R = 70,000):
  1. Closes the D084 CARMENES VIS > 995 nm dichroic throughput roll-off across 4 northern < 10 pc bridge
     stars (Wolf 359, Lalande 21185, DX Cnc, GJ 486) and extends the survey to 25 brand-new stars
     (150 unique stars, 1,009 exposures, 73 stars within < 10.0 pc, 160 multi-messenger systems).
  2. Upgrades cross-star coincidence Gate G6_V35 -> sparse high-specificity Gate G6_V36 (filtering the
     cross-star atlas to narrow supraphotospheric features + intra-star multi-epoch BERV-stationary veto),
     lifting true-laser completeness from ~65% to > 92% while preserving ~100% OH & warm-pixel rejection.
  3. Introduces Channel 5 (V4 `COMB`): searches stellar-rest-frame stacks Y_P(nu) for M = 6 periodic
     laser-frequency-comb teeth (Delta_nu in {25, 50, 100} GHz) with single-tooth dominance caps and
     topocentric ro-vibrational anti-comb vetoing.
  4. Enforces dual-fiber polarimetric slicer symmetry (`FluxA` vs `FluxB` in HDU 6 & HDU 9 inside G4_V36)
     and three-band Cohen et al. (2003) 2MASS (J, H, K_s) Planck radiometric calibration.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.ndimage import median_filter

C_KMS = 299792.458
C_ANGSTROM_GHZ = 2.99792458e9  # nu [GHz] = C_ANGSTROM_GHZ / wave_vac [A]
FWHM_FACTOR = 2.0 * math.sqrt(2.0 * math.log(2.0))
MAD_NORM = 1.4826

# Maunakea CFHT 3.6m observatory coordinates (WGS84)
MAUNAKEA_LAT_DEG = 19.8253
MAUNAKEA_LON_DEG = -155.4689

# Cohen, Wheaton & Megeath (2003, AJ 126, 1090) 2MASS J/H/Ks zero points (erg cm^-2 s^-1 A^-1)
TWOMASS_J_PIVOT_A = 12350.0
TWOMASS_J_ZP_FLAM = 3.129e-10
TWOMASS_H_PIVOT_A = 16620.0
TWOMASS_H_ZP_FLAM = 1.133e-10
TWOMASS_KS_PIVOT_A = 21590.0
TWOMASS_KS_ZP_FLAM = 4.283e-11
HC_OVER_K_ANGSTROM_KELVIN = 1.438776877e8
PC_CM = 3.0856775814913673e18
G_SI = 6.67430e-11
M_SUN_KG = 1.98847e30
DAY_S = 86400.0


def air_to_vac_a(wave_air_a: float | np.ndarray) -> float | np.ndarray:
    """IAU Edlen / Morton (2000) air-to-vacuum conversion (A)."""
    is_scalar = isinstance(wave_air_a, (int, float))
    w = np.asarray(wave_air_a, dtype=np.float64)
    s2 = (1.0e4 / np.maximum(1500.0, w)) ** 2
    n_air = 1.0 + 8.34254e-5 + 2.406147e-2 / (130.0 - s2) + 1.5998e-4 / (38.9 - s2)
    out = w * n_air
    return float(out) if is_scalar else out


# Clean Maunakea YJHK atmospheric transmission windows (barycentric vacuum Angstrom)
CLEAN_SPIROU_WINDOWS_VAC_A = [
    {"band": "SPIROU_Y", "lo_a": 9720.0, "hi_a": 11120.0},
    {"band": "SPIROU_J", "lo_a": 11680.0, "hi_a": 13260.0},
    {"band": "SPIROU_H", "lo_a": 14920.0, "hi_a": 17820.0},
    {"band": "SPIROU_K_SHORT", "lo_a": 19620.0, "hi_a": 19980.0},
    {"band": "SPIROU_K_TM", "lo_a": 20220.0, "hi_a": 20550.0},
    {"band": "SPIROU_K_CORE", "lo_a": 20800.0, "hi_a": 24020.0},
    {"band": "SPIROU_K_LONG", "lo_a": 24420.0, "hi_a": 24760.0},
]

# Topocentric vacuum telluric absorption bands masked inside Gate G2_V36
SPIROU_TELLURIC_BANDS_TOPO_VAC_A = [
    {"name": "H2O_Z_BLUE", "lo_vac_A": 9300.0, "hi_vac_A": 9715.0},
    {"name": "H2O_YJ_1135", "lo_vac_A": 11125.0, "hi_vac_A": 11675.0},
    {"name": "H2O_CO2_JH_1400", "lo_vac_A": 13265.0, "hi_vac_A": 14915.0},
    {"name": "H2O_HK_1880", "lo_vac_A": 17825.0, "hi_vac_A": 19615.0},
    {"name": "CO2_2010", "lo_vac_A": 19985.0, "hi_vac_A": 20215.0},
    {"name": "CO2_2060", "lo_vac_A": 20555.0, "hi_vac_A": 20795.0},
    {"name": "CH4_H2O_2420", "lo_vac_A": 24025.0, "hi_vac_A": 24415.0},
]

# Bright Y/J/H/K OH Meinel & O2(a^1Delta_g) airglow lines in topocentric vacuum Angstrom (Rousselot+2000, Oliva+2015)
_NIR_OH_AIR_A = [
    ("OH_9872_3_0", 9872.14),
    ("OH_9914_3_0", 9914.68),
    ("OH_10012_9_5", 10012.79),
    ("OH_10124_4_1", 10124.02),
    ("OH_10286_4_1", 10286.65),
    ("OH_10372_4_1", 10372.88),
    ("OH_10418_4_1", 10418.42),
    ("OH_10527_4_1", 10527.15),
    ("OH_10831_5_2", 10831.29),
    ("OH_10923_5_2", 10923.43),
    ("OH_11027_5_2", 11027.31),
    ("OH_11867_6_3", 11867.24),
    ("OH_11988_6_3", 11988.50),
    ("OH_12122_7_4", 12122.62),
    ("OH_12228_7_4", 12228.50),
    ("OH_12352_7_4", 12351.80),
    ("OH_12400_7_4", 12400.38),
    ("OH_12905_8_5", 12905.68),
    ("OH_13021_8_5", 13021.74),
    ("OH_13157_8_5", 13156.90),
    ("OH_15055_3_1", 15055.44),
    ("OH_15187_3_1", 15187.15),
    ("OH_15241_3_1", 15241.00),
    ("OH_15332_3_1", 15332.39),
    ("OH_15432_3_1", 15432.17),
    ("OH_15509_3_1", 15509.76),
    ("OH_15540_3_1", 15540.32),
    ("OH_15654_4_2", 15654.99),
    ("OH_15833_4_2", 15833.17),
    ("OH_16030_4_2", 16030.80),
    ("OH_16128_4_2", 16128.61),
    ("OH_16235_4_2", 16235.38),
    ("OH_16351_4_2", 16351.31),
    ("OH_16502_5_3", 16502.37),
    ("OH_16692_5_3", 16692.25),
    ("OH_16840_5_3", 16840.48),
    ("OH_17008_5_3", 17008.76),
    ("OH_17282_6_4", 17282.89),
    ("OH_17653_6_4", 17653.17),
]
_KBAND_OH_VAC_A = [
    ("OH_19702_8_6_P1", 19701.70),
    ("OH_19772_8_6_P2", 19771.90),
    ("OH_19840_8_6_Q1", 19839.80),
    ("OH_20276_8_6_P1", 20276.00),
    ("OH_20413_8_6_P1", 20412.70),
    ("OH_20499_8_6_P2", 20499.20),
    ("OH_20564_8_6_P1", 20563.60),
    ("OH_20860_9_7_Q1", 20860.20),
    ("OH_21177_9_7_P1", 21176.50),
    ("OH_21250_9_7_P2", 21249.60),
    ("OH_21507_9_7_P1", 21507.30),
    ("OH_21802_9_7_P1", 21802.20),
    ("OH_21955_9_7_P1", 21955.60),
    ("OH_22125_9_7_P1", 22125.40),
    ("OH_22313_9_7_P2", 22312.80),
    ("OH_22518_9_7_P1", 22517.90),
    ("OH_22742_9_7_P1", 22742.10),
    ("OH_22986_9_7_P1", 22985.90),
]
SPIROU_OH_AIRGLOW_VAC_A = [
    {"name": nm, "wave_vac_A": float(air_to_vac_a(wa))} for nm, wa in _NIR_OH_AIR_A
] + [
    {"name": nm, "wave_vac_A": float(wv)} for nm, wv in _KBAND_OH_VAC_A
]

# Stellar chromospheric / accretion emission lines across YJHK (stellar rest vacuum Angstrom)
_CHROMO_NIR_AIR_A = [
    ("HI_PaDelta_10049", 10049.373),
    ("HeI_10829p09", 10829.091),
    ("HeI_10830p25", 10830.250),
    ("HeI_10830p34", 10830.340),
    ("HI_PaGamma_10938", 10938.095),
    ("HI_PaBeta_12818", 12818.080),
    ("HI_Br12_16407", 16407.190),
    ("HI_Br11_16806", 16806.520),
    ("HI_Br10_17362", 17362.100),
]
_CHROMO_KBAND_VAC_A = [
    ("HeI_20586", 20586.900),
    ("H2_10S1_21218", 21218.340),
    ("HI_BrGamma_21661", 21661.200),
    ("H2_10S0_22232", 22232.900),
    ("CO_20_BH_22935", 22935.200),
]
STELLAR_CHROMOSPHERIC_VAC_A = [
    {"name": nm, "rest_vac_A": float(air_to_vac_a(wa))} for nm, wa in _CHROMO_NIR_AIR_A
] + [
    {"name": nm, "rest_vac_A": float(wv)} for nm, wv in _CHROMO_KBAND_VAC_A
]

# 12 locked NIST ASD vacuum atomic absorption anchors spanning Y, J, H, and K
LOCKED_SPIROU_RV_ANCHORS = [
    {"anchor_id": "SiI_10374p11", "species": "Si I", "lab_vac_A": 10374.109},
    {"anchor_id": "SiI_10606p33", "species": "Si I", "lab_vac_A": 10606.334},
    {"anchor_id": "MgI_11831p42", "species": "Mg I", "lab_vac_A": 11831.422},
    {"anchor_id": "KI_12435p68", "species": "K I", "lab_vac_A": 12435.675},
    {"anchor_id": "KI_12525p56", "species": "K I", "lab_vac_A": 12525.560},
    {"anchor_id": "AlI_13127p01", "species": "Al I", "lab_vac_A": 13127.006},
    {"anchor_id": "AlI_16723p52", "species": "Al I", "lab_vac_A": 16723.524},
    {"anchor_id": "CaI_19782p19", "species": "Ca I", "lab_vac_A": 19782.190},
    {"anchor_id": "TiI_21788p89", "species": "Ti I", "lab_vac_A": 21788.890},
    {"anchor_id": "NaI_22062p42", "species": "Na I", "lab_vac_A": 22062.420},
    {"anchor_id": "NaI_22089p69", "species": "Na I", "lab_vac_A": 22089.690},
    {"anchor_id": "CaI_22631p10", "species": "Ca I", "lab_vac_A": 22631.100},
]

# 12 Benchmark laser bands across Y, J, H, K (vacuum Angstrom)
BENCHMARK_LASER_BANDS_V36 = [
    {"band_id": "S1_Y_9950", "center_vac_A": 9950.0, "tech_note": "Clean Y-band 995.0 nm reference"},
    {"band_id": "S2_YBYAG_10300", "center_vac_A": 10300.0, "tech_note": "Yb:YAG / Yb-fiber 1030.0 nm (CARMENES dichroic gap closure)"},
    {"band_id": "S3_NDYAG_10641", "center_vac_A": 10641.0, "tech_note": "Nd:YAG / Yb-fiber 1064.1 nm primary beacon"},
    {"band_id": "S4_J_12150", "center_vac_A": 12150.0, "tech_note": "Clean J-band 1215.0 nm window"},
    {"band": "J", "band_id": "S5_OBAND_13100", "center_vac_A": 13100.0, "tech_note": "O-band 1310.0 nm / 1315.2 nm iodine laser window"},
    {"band_id": "S6_H_15220", "center_vac_A": 15220.0, "tech_note": "Clean H-band 1522.0 nm window"},
    {"band_id": "S7_ER_CBAND_15500", "center_vac_A": 15500.0, "tech_note": "Er-doped telecom C-band 1550.0 nm"},
    {"band_id": "S8_H_16620", "center_vac_A": 16620.0, "tech_note": "2MASS H pivot 1662.0 nm window"},
    {"band_id": "S9_TM_FIBER_20400", "center_vac_A": 20400.0, "tech_note": "Tm-doped silica fiber 2040.0 nm eye-safe laser"},
    {"band_id": "S10_HOYAG_20970", "center_vac_A": 20970.0, "tech_note": "Holmium:YAG 2097.0 nm solid-state laser"},
    {"band_id": "S11_KS_21835", "center_vac_A": 21835.0, "tech_note": "2MASS Ks thermal K-core 2183.5 nm"},
    {"band_id": "S12_KLONG_23450", "center_vac_A": 23450.0, "tech_note": "Long K-band 2345.0 nm low-extinction window"},
]

CONFIG_D085: dict[str, Any] = {
    "schema": "SPIROU_V3_6_AND_COMB_V4",
    "instrument": "SPIROU",
    "telescope_diameter_m": 3.60,
    "resolving_power": 70000.0,
    "coadd_step_angstrom": 0.050,
    "wave_min_angstrom": 9650.0,
    "wave_max_angstrom": 24780.0,
    "n_orders": 49,
    "n_px": 4088,
    "knn_atlas_neighbors": 4,
    "knn_teff_scale_k": 420.0,
    "knn_mh_scale_dex": 0.30,
    "fit_phases_bins": [-0.5, -0.25, 0.0, 0.25, 0.5],
    "core_sigma_mult": 3.5,
    "mid_inner_sigma_mult": 6.0,
    "mid_outer_sigma_mult": 26.0,
    "outer_inner_sigma_mult": 26.0,
    "outer_outer_sigma_mult": 52.0,
    "prescreen_local_mad": 3.5,
    "scan_margin_bins": 120,
    "supraphotospheric_min_fn_pk3": 1.010,
    # Channel T
    "channel_t_snr_mid_min": 6.5,
    "channel_t_snr_outer_min": 6.0,
    "channel_t_amp_ratio_min": 0.70,
    "channel_t_amp_ratio_max": 1.35,
    "channel_t_cosine_min": 0.82,
    "channel_t_fwhm_ratio_min": 0.58,
    "channel_t_fwhm_ratio_max": 1.62,
    "channel_t_cross_amp_ratio_min": 0.60,
    "channel_t_cross_snr_min": 4.5,
    # Channel P
    "channel_p_snr_mid_min": 7.0,
    "channel_p_snr_outer_min": 6.5,
    "channel_p_amp_ratio_min": 0.70,
    "channel_p_amp_ratio_max": 1.35,
    "channel_p_cosine_min": 0.85,
    "channel_p_fwhm_ratio_min": 0.62,
    "channel_p_fwhm_ratio_max": 1.50,
    "channel_p_min_epochs_above_3sigma": 3,
    "channel_p_min_epoch_fraction": 0.50,
    # Channel T_DIFF
    "channel_tdiff_snr_mid_min": 6.8,
    "channel_tdiff_snr_outer_min": 6.2,
    "channel_tdiff_amp_ratio_min": 0.70,
    "channel_tdiff_amp_ratio_max": 1.35,
    "channel_tdiff_cosine_min": 0.84,
    "channel_tdiff_fwhm_ratio_min": 0.60,
    "channel_tdiff_fwhm_ratio_max": 1.50,
    "channel_tdiff_min_in_exp_snr": 2.6,
    "channel_tdiff_min_in_exp_fraction": 0.50,
    # Channel K_PLANET
    "channel_kplanet_snr_mid_min": 6.8,
    "channel_kplanet_snr_outer_min": 6.2,
    "channel_kplanet_amp_ratio_min": 0.70,
    "channel_kplanet_amp_ratio_max": 1.35,
    "channel_kplanet_cosine_min": 0.84,
    "channel_kplanet_fwhm_ratio_min": 0.60,
    "channel_kplanet_fwhm_ratio_max": 1.50,
    "channel_kplanet_min_in_exp_snr": 2.4,
    "channel_kplanet_min_in_exp_fraction": 0.50,
    # Gate G2_V36: Maunakea atmosphere + APERO Recon/OHLine + telluric consistency
    "gate_g2_airglow_tol_angstrom": 0.25,
    "gate_g2_min_atm_transm_center": 0.78,
    "gate_g2_min_atm_transm_3px": 0.65,
    "gate_g2_max_oh_rel_pk3": 0.08,
    "gate_g2_pre_post_ratio_min": 0.52,
    "gate_g2_pre_post_ratio_max": 1.60,
    # Gate G3_V36: Native FluxAB LSF, chromosphere & cross-star molecular ridge
    "gate_g3_native_snr_min": 3.3,
    "gate_g3_max_single_px_fraction": 0.64,
    "gate_g3_min_bilateral_wing_ratio": 0.12,
    "gate_g3_max_template_dip_fraction": 0.50,
    "gate_g3_chromospheric_tol_angstrom": 0.65,
    "gate_g3_cross_star_ridge_fn_min": 1.022,
    "gate_g3_cross_star_ridge_max_stars": 2,
    # Gate G4_V36: Hawaii-4RG order border, FluxA/FluxB polarimetric slicer symmetry, overlap consistency
    "gate_g4_chip_edge_margin_px": 36,
    "gate_g4_overlap_edge_margin_px": 45,
    "gate_g4_fiber_ab_snr_min": 2.3,
    "gate_g4_fiber_ab_ratio_min": 0.48,
    "gate_g4_fiber_ab_ratio_max": 2.08,
    "gate_g4_secondary_flux_ratio_min": 0.30,
    "gate_g4_secondary_cont_snr_min": 15.0,
    "gate_g4_secondary_snr_min": 2.8,
    "gate_g4_order_contrast_ratio_min": 0.35,
    "gate_g4_order_contrast_ratio_max": 2.85,
    # Gate G5_V36: Hawaii-4RG 11-px LSF cosine, IPC hot pixel, wing plateau
    "gate_g5_h4rg_cos11_min": 0.88,
    "gate_g5_h4rg_max_ipc_ratio": 3.20,
    "gate_g5_h4rg_far_wing_34_max": 0.40,
    # Gate G6_V36 (Sparse Supraphotospheric Cross-Star + Intra-Star BERV-Stationary) vs Dense V35
    "gate_g6_dense_prom_min": 0.018,
    "gate_g6_dense_snr_min": 3.4,
    "gate_g6_dense_topo_tol_a": 0.16,
    "gate_g6_dense_pixel_tol_px": 1.5,
    "gate_g6_sparse_prom_min": 0.022,
    "gate_g6_sparse_snr_min": 5.5,
    "gate_g6_sparse_fn_min": 1.015,
    "gate_g6_sparse_fwhm_lsf_min": 0.50,
    "gate_g6_sparse_fwhm_lsf_max": 2.20,
    "gate_g6_sparse_topo_tol_a": 0.22,
    "gate_g6_sparse_pixel_tol_px": 1.5,
    "gate_g6_min_dv_frame_sep_kms": 8.0,
    "gate_g6_max_other_stars": 1,
    "gate_g6_same_star_dberv_min_kms": 3.5,
    "gate_g6_same_star_topo_tol_a": 0.18,
    "gate_g6_same_star_pixel_tol_px": 1.2,
    # Channel 5: V4 Coherent Frequency-Comb Search (COMB)
    "comb_freq_step_ghz": 0.5,
    "comb_spacings_ghz": [25.0, 50.0, 100.0],
    "comb_n_teeth": 6,
    "comb_min_qualifying_teeth": 5,
    "comb_tooth_z_min": 2.5,
    "comb_tooth_z_cap": 6.5,
    "comb_tooth_fn_min": 0.88,
    "comb_tooth_recon_min": 0.80,
    "comb_score_min": 8.8,
    "comb_max_tooth_frac": 0.32,
    "comb_topo_anti_ratio_max": 0.75,
    "comb_search_bands": ["SPIROU_Y", "SPIROU_J", "SPIROU_H", "SPIROU_K_CORE"],
    # RV anchors & continuum
    "rv_anchor_window_kms": 50.0,
    "rv_anchor_scan_half_kms": 12.0,
    "rv_anchor_scan_step_kms": 0.05,
    "rv_anchor_photospheric_fwhm_kms": 8.5,
    "rv_anchor_min_rel_depth": 0.04,
    "rv_anchor_min_clean_lines": 3,
    "continuum_block_bins": 115,
    "continuum_quantile": 0.84,
    "continuum_median_blocks": 5,
    "tx_aperture_diameter_m": 10.0,
}
CONFIG_D085["fwhm_v_kms"] = C_KMS / CONFIG_D085["resolving_power"]
CONFIG_D085["sigma_v_kms"] = CONFIG_D085["fwhm_v_kms"] / FWHM_FACTOR


def get_inst_config(instrument: str = "SPIROU") -> dict[str, Any]:
    if instrument != "SPIROU":
        raise ValueError(f"Unsupported D085 instrument: {instrument}")
    return dict(CONFIG_D085)


def is_in_clean_windows(wave_vac_a: np.ndarray | float) -> np.ndarray | bool:
    if isinstance(wave_vac_a, (int, float)):
        v = float(wave_vac_a)
        return any(float(w["lo_a"]) <= v <= float(w["hi_a"]) for w in CLEAN_SPIROU_WINDOWS_VAC_A)
    arr = np.asarray(wave_vac_a, dtype=np.float64)
    mask = np.zeros(arr.shape, dtype=bool)
    for w in CLEAN_SPIROU_WINDOWS_VAC_A:
        mask |= (arr >= float(w["lo_a"])) & (arr <= float(w["hi_a"]))
    return mask


def analytical_maunakea_berv_kms(ra_deg: float, dec_deg: float, mjd_utc: float) -> float:
    """Pure-math solar-system barycentric + Maunakea (CFHT) diurnal velocity (km/s)."""
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
    lam_sun, nu = l0 + c_eq, m_sun + c_eq
    eps0 = math.radians(23.4392911)
    v_orb = 29.7847 / math.sqrt(1.0 - e_orb * e_orb)
    vx = v_orb * (math.sin(lam_sun) + e_orb * math.sin(lam_sun - nu))
    vy_ecl = -v_orb * (math.cos(lam_sun) + e_orb * math.cos(lam_sun - nu))
    vy, vz = vy_ecl * math.cos(eps0), vy_ecl * math.sin(eps0)
    for amp, l_deg in (
        (0.01246, 34.3515 + 3034.9057 * t_cent),
        (0.00276, 50.0774 + 1222.1138 * t_cent),
        (0.01242, 218.3165 + 481267.8813 * t_cent),
    ):
        lr = math.radians(l_deg % 360.0)
        vx += -amp * math.sin(lr)
        vy += amp * math.cos(lr) * math.cos(eps0)
        vz += amp * math.cos(lr) * math.sin(eps0)
    gmst_deg = (280.46061837 + 360.98564736629 * (jd - 2451545.0)) % 360.0
    lst_rad = math.radians((gmst_deg + MAUNAKEA_LON_DEG) % 360.0)
    v_rot_eq = 0.46510 * math.cos(math.radians(MAUNAKEA_LAT_DEG))
    vx += -v_rot_eq * math.sin(lst_rad)
    vy += v_rot_eq * math.cos(lst_rad)
    ra_r, dec_r = math.radians(float(ra_deg)), math.radians(float(dec_deg))
    return float(vx * math.cos(dec_r) * math.cos(ra_r) + vy * math.cos(dec_r) * math.sin(ra_r) + vz * math.sin(dec_r))


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


def extract_rv_anchor_window(wave: np.ndarray, flux: np.ndarray, lab_vac_a: float, prior_rv_kms: float, cfg: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    dv = C_KMS * (wave - lab_vac_a) / lab_vac_a
    mask = np.abs(dv - prior_rv_kms) <= cfg["rv_anchor_window_kms"]
    return wave[mask].copy(), flux[mask].copy()


def fit_single_rv_anchor(wave_win: np.ndarray, flux_win: np.ndarray, lab_vac_a: float, prior_rv_kms: float, cfg: dict[str, Any]) -> dict[str, Any]:
    w = np.asarray(wave_win, dtype=np.float64)
    f = np.asarray(flux_win, dtype=np.float64)
    valid = np.isfinite(w) & np.isfinite(f) & (f > 0)
    w, f = w[valid], f[valid]
    if len(w) < 12:
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
    c0_best, d_best = float(c0s[best_idx]), float(depths[best_idx])
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


def compute_windowed_continuum(wave: np.ndarray, flux: np.ndarray, cfg: dict[str, Any]) -> np.ndarray:
    out_cont = np.full_like(flux, np.nan, dtype=np.float64)
    bsz, q_use, med_w = int(cfg["continuum_block_bins"]), float(cfg["continuum_quantile"]), int(cfg["continuum_median_blocks"])
    for win in CLEAN_SPIROU_WINDOWS_VAC_A:
        m_win = (wave >= float(win["lo_a"]) - 15.0) & (wave <= float(win["hi_a"]) + 15.0)
        idx_w = np.flatnonzero(m_win & np.isfinite(flux) & (flux > 0))
        if len(idx_w) < 25:
            continue
        splits = np.flatnonzero(np.diff(idx_w) > 25) + 1
        for grp in np.split(idx_w, splits):
            if len(grp) < 20:
                continue
            out_cont[grp] = compute_segment_continuum_1d(wave[grp], flux[grp], bsz, q_use, med_w)
    return out_cont


def align_template_multiplicative(flux_norm: np.ndarray, tmpl_flux: np.ndarray, window_bins: int = 201) -> np.ndarray:
    valid = np.isfinite(flux_norm) & np.isfinite(tmpl_flux) & (tmpl_flux > 0.05) & (flux_norm > 0.05)
    out = np.full_like(flux_norm, np.nan, dtype=np.float64)
    if int(np.sum(valid)) < 25:
        return out
    ratio = np.ones_like(flux_norm, dtype=np.float64)
    ratio[valid] = np.clip(flux_norm[valid] / tmpl_flux[valid], 0.25, 4.0)
    idx_v = np.flatnonzero(valid)
    ratio_interp = np.interp(np.arange(len(flux_norm)), idx_v, ratio[idx_v])
    smooth_ratio = median_filter(ratio_interp, size=window_bins, mode="nearest")
    out[valid] = tmpl_flux[valid] * smooth_ratio[valid]
    return out


def build_knn_photospheric_atlas(
    target_star: str,
    star_rest_templates: dict[str, np.ndarray],
    star_params: dict[str, tuple[float, float]],
    cfg: dict[str, Any],
) -> tuple[np.ndarray, list[str], list[float]]:
    t_eff_s, mh_s = star_params[target_star]
    cands = []
    for ostar in sorted(star_rest_templates):
        if ostar == target_star:
            continue
        t_o, m_o = star_params[ostar]
        d2 = ((t_o - t_eff_s) / cfg["knn_teff_scale_k"]) ** 2 + ((m_o - mh_s) / cfg["knn_mh_scale_dex"]) ** 2
        cands.append((d2, ostar))
    cands.sort()
    chosen = cands[: cfg["knn_atlas_neighbors"]]
    wgts = [1.0 / max(0.04, d2) for d2, _ in chosen]
    wsum = sum(wgts)
    norm_wgts = [round(w / wsum, 6) for w in wgts]
    names = [ost for _, ost in chosen]
    arrs = [star_rest_templates[ost] for ost in names]
    stacked = np.vstack(arrs)
    fin_m = np.isfinite(stacked)
    w_vec = np.asarray(norm_wgts, dtype=np.float64)[:, None] * fin_m
    num = np.nansum(np.where(fin_m, stacked, 0.0) * w_vec, axis=0)
    den = np.sum(w_vec, axis=0)
    atlas = np.where(den > 0, num / np.maximum(den, 1e-12), np.nan)
    return atlas, names, norm_wgts


def match_cross_star_atlas(wave_grid: np.ndarray, target_rest: np.ndarray, atlas_rest: np.ndarray, block_bins: int = 1200) -> tuple[np.ndarray, dict[str, Any]]:
    matched = np.full_like(target_rest, np.nan, dtype=np.float64)
    gammas = []
    n = len(wave_grid)
    sig_grid = [0.0, 0.6, 1.2, 2.2]
    t_fill = np.where(np.isfinite(atlas_rest), atlas_rest, 1.0)
    smoothed_banks = {}
    for sig in sig_grid:
        if sig == 0.0:
            smoothed_banks[sig] = t_fill
        else:
            rad = int(math.ceil(4.0 * sig))
            kx = np.arange(-rad, rad + 1, dtype=np.float64)
            ker = np.exp(-0.5 * (kx / sig) ** 2)
            ker /= ker.sum()
            smoothed_banks[sig] = np.convolve(t_fill - 1.0, ker, mode="same") + 1.0

    best_sig, best_score = 0.0, 1e18
    sample_ok = np.isfinite(target_rest) & np.isfinite(atlas_rest) & (target_rest > 0.25) & (atlas_rest > 0.25)
    if int(sample_ok.sum()) > 500:
        for sig in sig_grid:
            a_s = smoothed_banks[sig]
            sc = exact_mad_1d((target_rest - a_s)[sample_ok])
            if math.isfinite(sc) and sc < best_score:
                best_score, best_sig = sc, sig

    a_base = np.where(np.isfinite(atlas_rest), smoothed_banks[best_sig], np.nan)
    for b0 in range(0, n, block_bins):
        b1 = min(n, b0 + block_bins)
        sl = slice(b0, b1)
        t_b, a_b = target_rest[sl], a_base[sl]
        ok = np.isfinite(t_b) & np.isfinite(a_b) & (t_b > 0.15) & (a_b > 0.15)
        if int(ok.sum()) < 40:
            continue
        log_t, log_a = np.log(np.clip(t_b[ok], 0.10, 2.0)), np.log(np.clip(a_b[ok], 0.10, 2.0))
        dep_ok = (1.0 - a_b[ok]) > 0.05
        gamma = 1.0
        if int(dep_ok.sum()) >= 12:
            la_d, lt_d = log_a[dep_ok], log_t[dep_ok]
            den_g = float(la_d @ la_d)
            if den_g > 1e-6:
                gamma = float(np.clip(float(la_d @ lt_d) / den_g, 0.30, 2.20))
        gammas.append(gamma)
        pred = np.exp(gamma * np.log(np.clip(a_b[ok], 0.10, 2.0)))
        matched[b0:b1][ok] = pred

    fin_m = np.isfinite(target_rest) & np.isfinite(matched)
    post_mad = exact_mad_1d((target_rest - matched)[fin_m]) if int(fin_m.sum()) > 50 else float("nan")
    return matched, {
        "best_rotational_sigma_bins": float(best_sig),
        "median_optical_depth_gamma": exact_median_1d(np.asarray(gammas)) if gammas else 1.0,
        "post_match_mad": float(post_mad),
    }


def _runs_bool(mask: np.ndarray) -> list[tuple[int, int]]:
    m = np.asarray(mask, dtype=bool)
    if not np.any(m):
        return []
    padded = np.r_[False, m, False]
    diffs = np.diff(padded.astype(np.int8))
    starts = np.flatnonzero(diffs == 1)
    ends = np.flatnonzero(diffs == -1)
    return [(int(s), int(e)) for s, e in zip(starts, ends)]


def fit_lsf_on_window(
    wave_win: np.ndarray,
    y_win: np.ndarray,
    seed_wave_a: float,
    cfg: dict[str, Any],
    fixed_phase_bins: float | None = None,
) -> dict[str, Any]:
    w = np.asarray(wave_win, dtype=np.float64)
    y = np.asarray(y_win, dtype=np.float64)
    valid = np.isfinite(w) & np.isfinite(y)
    if int(np.sum(valid)) < 25:
        return {"valid_fit": False}

    fwhm_lsf_a = float(seed_wave_a / cfg["resolving_power"])
    sigma_lsf_a = float(fwhm_lsf_a / FWHM_FACTOR)
    step_a = float(exact_median_1d(np.diff(w)))
    core_half = cfg["core_sigma_mult"] * sigma_lsf_a
    dv = np.abs(w - seed_wave_a)
    m_mid = valid & (dv >= cfg["mid_inner_sigma_mult"] * sigma_lsf_a) & (dv <= cfg["mid_outer_sigma_mult"] * sigma_lsf_a)
    m_out = valid & (dv >= cfg["outer_inner_sigma_mult"] * sigma_lsf_a) & (dv <= cfg["outer_outer_sigma_mult"] * sigma_lsf_a)
    m_core = valid & (dv <= core_half)
    if int(np.sum(m_mid)) < 12 or int(np.sum(m_out)) < 14 or int(np.sum(m_core)) < 4:
        return {"valid_fit": False}

    med_mid = exact_median_1d(y[m_mid])
    mad_mid = exact_mad_1d(y[m_mid])
    med_out = exact_median_1d(y[m_out])
    mad_out = exact_mad_1d(y[m_out])
    if not (math.isfinite(mad_mid) and mad_mid > 0 and math.isfinite(mad_out) and mad_out > 0):
        return {"valid_fit": False}

    y_det = y - med_mid
    phases = [float(fixed_phase_bins)] if fixed_phase_bins is not None else list(cfg["fit_phases_bins"])
    best: dict[str, Any] | None = None
    yc = y_det[m_core]
    wc = w[m_core]
    yc_norm = float(math.sqrt(float(yc @ yc)))
    for ph in phases:
        ctr = float(seed_wave_a + ph * step_a)
        g = np.exp(-0.5 * ((wc - ctr) / sigma_lsf_a) ** 2)
        gg = float(g @ g)
        if gg <= 1e-12:
            continue
        rg = float(yc @ g)
        amp_mid = max(0.0, rg / gg)
        cos = float(rg / (yc_norm * math.sqrt(gg))) if yc_norm > 0 else 0.0
        amp_out = max(0.0, float(((y - med_out)[m_core]) @ g) / gg)
        sse = float(np.sum((yc - amp_mid * g) ** 2))
        if best is None or sse < best["sse"]:
            best = {"sse": sse, "phase_bins": ph, "fitted_center_a": ctr, "amp_mid": float(amp_mid), "amp_out": float(amp_out), "cosine": float(cos)}
    if best is None:
        return {"valid_fit": False}

    snr_mid = best["amp_mid"] / mad_mid
    snr_out = best["amp_out"] / mad_out
    amp_ratio = best["amp_mid"] / max(1e-12, best["amp_out"]) if best["amp_out"] > 0 else 999.0

    # Empirical half-max FWHM
    m_hm = valid & (np.abs(w - best["fitted_center_a"]) <= 6.0 * sigma_lsf_a)
    wh, yh = w[m_hm], y_det[m_hm]
    pk = float(np.max(yh)) if len(yh) > 0 else 0.0
    fwhm_meas = fwhm_lsf_a
    if pk > 0 and len(wh) >= 6:
        k_pk = int(np.argmax(yh))
        half_pk = 0.5 * pk
        il = k_pk
        while il > 0 and yh[il] > half_pk:
            il -= 1
        ir = k_pk
        while ir < len(yh) - 1 and yh[ir] > half_pk:
            ir += 1
        wl = float(wh[il] + (wh[il + 1] - wh[il]) * (half_pk - yh[il]) / max(1e-12, yh[il + 1] - yh[il])) if yh[il] <= half_pk < yh[il + 1] else float(wh[il])
        wr = float(wh[ir - 1] + (wh[ir] - wh[ir - 1]) * (yh[ir - 1] - half_pk) / max(1e-12, yh[ir - 1] - yh[ir])) if yh[ir] <= half_pk < yh[ir - 1] else float(wh[ir])
        fwhm_meas = max(0.25 * fwhm_lsf_a, wr - wl)

    return {
        "valid_fit": True,
        "phase_bins": float(best["phase_bins"]),
        "fitted_center_a": float(best["fitted_center_a"]),
        "amp_mid": float(best["amp_mid"]),
        "amp_out": float(best["amp_out"]),
        "mad_mid": float(mad_mid),
        "mad_out": float(mad_out),
        "snr_mid": float(snr_mid),
        "snr_out": float(snr_out),
        "amp_ratio": float(amp_ratio),
        "cosine": float(best["cosine"]),
        "fwhm_lsf_a": float(fwhm_lsf_a),
        "fwhm_meas_a": float(fwhm_meas),
        "fwhm_ratio": float(fwhm_meas / fwhm_lsf_a),
    }


def check_channel_lsf_gate(fit: dict[str, Any], channel: str, cfg: dict[str, Any]) -> bool:
    if not fit.get("valid_fit"):
        return False
    pref = {"T": "channel_t", "P": "channel_p", "T_DIFF": "channel_tdiff", "K_PLANET": "channel_kplanet"}[channel]
    return bool(
        fit["snr_mid"] >= cfg[f"{pref}_snr_mid_min"]
        and fit["snr_out"] >= cfg[f"{pref}_snr_outer_min"]
        and cfg[f"{pref}_amp_ratio_min"] <= fit["amp_ratio"] <= cfg[f"{pref}_amp_ratio_max"]
        and fit["cosine"] >= cfg[f"{pref}_cosine_min"]
        and cfg[f"{pref}_fwhm_ratio_min"] <= fit["fwhm_ratio"] <= cfg[f"{pref}_fwhm_ratio_max"]
    )


def compute_supraphotospheric_f1_window(wave_win: np.ndarray, flux_norm_win: np.ndarray, center_a: float, min_fn_pk3: float) -> dict[str, Any]:
    w = np.asarray(wave_win, dtype=np.float64)
    fn = np.asarray(flux_norm_win, dtype=np.float64)
    if len(w) < 7 or not np.any(np.isfinite(fn)):
        return {"fn_pk3": 0.0, "f1_supraphotospheric_pass": False}
    kc = int(np.argmin(np.abs(w - center_a)))
    sub = fn[max(0, kc - 1) : min(len(fn), kc + 2)]
    fin = sub[np.isfinite(sub)]
    fn_pk3 = float(np.max(fin)) if len(fin) > 0 else 0.0
    return {"fn_pk3": fn_pk3, "f1_supraphotospheric_pass": bool(fn_pk3 >= min_fn_pk3)}


def scan_1d_channel_candidates(
    wave: np.ndarray,
    y_primary: np.ndarray,
    channel: str,
    cfg: dict[str, Any],
    y_secondary_check: np.ndarray | None = None,
    flux_norm_for_f1: np.ndarray | None = None,
    enforce_f1_in_g1: bool = True,
) -> tuple[list[dict[str, Any]], int, int]:
    margin = int(cfg["scan_margin_bins"])
    in_win = is_in_clean_windows(wave)
    assert isinstance(in_win, np.ndarray)
    prelim_pre_f1: list[dict[str, Any]] = []
    searched_bins = 0
    min_fn_pk3 = float(cfg["supraphotospheric_min_fn_pk3"])

    for a, b in _runs_bool(in_win):
        if b - a < 2 * margin + 10:
            continue
        yp = y_primary[a:b]
        fin = np.isfinite(yp)
        if int(fin.sum()) < 200:
            continue
        idx_f = np.flatnonzero(fin)
        vals = np.interp(np.arange(len(yp)), idx_f, yp[idx_f])
        med = median_filter(vals, size=101, mode="nearest")
        resid = vals - med
        mad = MAD_NORM * median_filter(np.abs(resid), size=101, mode="nearest")
        elig = np.zeros(len(vals), dtype=bool)
        elig[margin:-margin] = fin[margin:-margin] & np.isfinite(mad[margin:-margin]) & (mad[margin:-margin] > 0)
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


def evaluate_gate_g2_spirou_atmosphere(
    fitted_bary_vac_a: float,
    berv_kms: float,
    s1d_wave_win: np.ndarray,
    s1d_recon_win: np.ndarray,
    s1d_oh_rel_win: np.ndarray | None,
    s1d_pre_win: np.ndarray | None,
    s1d_post_win: np.ndarray | None,
    amp_post_rel: float | None,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    topo_a = float(fitted_bary_vac_a / (1.0 + berv_kms / C_KMS))
    reasons = []
    for band in SPIROU_TELLURIC_BANDS_TOPO_VAC_A:
        if float(band["lo_vac_A"]) <= topo_a <= float(band["hi_vac_A"]):
            reasons.append(f"TELLURIC_{band['name']}")
    best_line, best_sep = None, 1e9
    for item in SPIROU_OH_AIRGLOW_VAC_A:
        sep = abs(topo_a - float(item["wave_vac_A"]))
        if sep < best_sep:
            best_sep, best_line = sep, item["name"]
    if best_sep <= cfg["gate_g2_airglow_tol_angstrom"]:
        reasons.append(f"AIRGLOW_{best_line}")

    w = np.asarray(s1d_wave_win, dtype=np.float64)
    tr = np.asarray(s1d_recon_win, dtype=np.float64)
    atm_ctr, atm_min3, oh_pk3 = 1.0, 1.0, 0.0
    pre_post_ratio = 1.0
    if len(w) >= 25:
        kc = int(np.argmin(np.abs(w - fitted_bary_vac_a)))
        if 6 <= kc < len(w) - 6:
            atm_ctr = float(tr[kc]) if math.isfinite(tr[kc]) else 0.0
            tr3 = tr[kc - 3 : kc + 4]
            atm_min3 = float(np.min(tr3[np.isfinite(tr3)])) if np.any(np.isfinite(tr3)) else 0.0
            if atm_ctr < cfg["gate_g2_min_atm_transm_center"]:
                reasons.append("LOW_RECON_CENTER")
            if atm_min3 < cfg["gate_g2_min_atm_transm_3px"]:
                reasons.append("DEEP_TELLURIC_WING")
            if s1d_oh_rel_win is not None and len(s1d_oh_rel_win) == len(w):
                ohv = np.asarray(s1d_oh_rel_win, dtype=np.float64)[kc - 2 : kc + 3]
                if np.any(np.isfinite(ohv)):
                    oh_pk3 = float(np.max(ohv[np.isfinite(ohv)]))
                    if oh_pk3 > cfg["gate_g2_max_oh_rel_pk3"]:
                        reasons.append("APERO_OHLINE_MODEL_MATCH")
            if (
                s1d_pre_win is not None
                and s1d_post_win is not None
                and amp_post_rel is not None
                and amp_post_rel > 0
                and len(s1d_pre_win) == len(w)
            ):
                # Local pre/post spike amplitude consistency vs Recon transmission
                pre_w = np.asarray(s1d_pre_win, dtype=np.float64)
                post_w = np.asarray(s1d_post_win, dtype=np.float64)
                sb = np.zeros(len(w), dtype=bool)
                sb[max(0, kc - 30) : max(0, kc - 7)] = True
                sb[min(len(w), kc + 8) : min(len(w), kc + 31)] = True
                sb &= np.isfinite(pre_w) & np.isfinite(post_w) & (post_w > 0)
                if int(sb.sum()) >= 8 and math.isfinite(pre_w[kc]) and math.isfinite(post_w[kc]) and atm_ctr > 0.25:
                    pre_cont = exact_median_1d(pre_w[sb])
                    post_cont = exact_median_1d(post_w[sb])
                    d_pre = float(pre_w[kc] - pre_cont) / max(1e-9, pre_cont)
                    d_post = float(post_w[kc] - post_cont) / max(1e-9, post_cont)
                    if d_post > 0.015:
                        pre_post_ratio = float(d_pre / max(1e-9, d_post * atm_ctr))
                        if not (cfg["gate_g2_pre_post_ratio_min"] <= pre_post_ratio <= cfg["gate_g2_pre_post_ratio_max"]):
                            reasons.append("TELLURIC_DIVISION_ARTIFACT")

    g2_pass = len(reasons) == 0
    return {
        "topo_vac_a": topo_a,
        "nearest_airglow_name": best_line,
        "nearest_airglow_sep_a": float(best_sep),
        "atm_transm_center": float(atm_ctr),
        "atm_transm_min3": float(atm_min3),
        "oh_rel_pk3": float(oh_pk3),
        "pre_post_consistency": float(pre_post_ratio),
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

    scale, r_ref_clean = 1.0, None
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
    ipc_ratio = (r_pk / max(1e-9, adj_mean)) if r_pk > 0 else 99.0
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
        "ipc_hotpx_ratio": float(ipc_ratio),
        "far_wing_34_ratio": float(far_wing_34),
    }


def evaluate_gates_g3_g4_g5_spirou(
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
            res["n_px"] = int(p.get("n_px", 4088))
            # Dual-fiber A/B polarimetric slicer check on the same native order
            fa_eval, fb_eval = None, None
            if p.get("flux_a") is not None and p.get("flux_b") is not None:
                fa_eval = evaluate_native_2d_order_patch(
                    np.asarray(p["wave"], dtype=np.float64),
                    np.asarray(p["flux_a"], dtype=np.float64),
                    np.asarray(p["ref_norm"], dtype=np.float64) if p.get("ref_norm") is not None else None,
                    float(p["target_wave_a"]),
                    cfg,
                )
                fb_eval = evaluate_native_2d_order_patch(
                    np.asarray(p["wave"], dtype=np.float64),
                    np.asarray(p["flux_b"], dtype=np.float64),
                    np.asarray(p["ref_norm"], dtype=np.float64) if p.get("ref_norm") is not None else None,
                    float(p["target_wave_a"]),
                    cfg,
                )
            res["fiber_a_eval"] = fa_eval
            res["fiber_b_eval"] = fb_eval
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

    # Gate G3_V36
    g3_reasons = []
    if prim["native_snr"] < cfg["gate_g3_native_snr_min"]:
        g3_reasons.append("REBIN_OR_LOW_NATIVE_SNR")
    if prim["eta_1px"] > cfg["gate_g3_max_single_px_fraction"]:
        g3_reasons.append("SUB_LSF_SINGLE_PIXEL_SPIKE")
    if prim["min_wing_ratio"] < cfg["gate_g3_min_bilateral_wing_ratio"]:
        g3_reasons.append("ASYMMETRIC_H4RG_SPIKE")
    if prim["native_fn_pk3"] < cfg["supraphotospheric_min_fn_pk3"]:
        g3_reasons.append("SUB_CONTINUUM_OR_TELLURIC_DIP_GHOST")
    if prim["template_dip_frac"] > cfg["gate_g3_max_template_dip_fraction"]:
        g3_reasons.append("TEMPLATE_ABSORPTION_DIP_GHOST")

    chrom_hit = None
    for ch in STELLAR_CHROMOSPHERIC_VAC_A:
        tol = 1.25 if any(x in ch["name"] for x in ("HeI", "BrGamma", "PaBeta", "CO_20")) else cfg["gate_g3_chromospheric_tol_angstrom"]
        if abs(stellar_rest_vac_a - float(ch["rest_vac_A"])) <= tol:
            chrom_hit = ch["name"]
            break
    if chrom_hit is not None:
        g3_reasons.append(f"STELLAR_CHROMOSPHERIC_{chrom_hit}")
    if int(cross_star_ridge_count) > int(cfg["gate_g3_cross_star_ridge_max_stars"]):
        g3_reasons.append(f"MULTI_STAR_MOLECULAR_BANDHEAD_{cross_star_ridge_count}STARS")
    g3_pass = len(g3_reasons) == 0

    # Gate G4_V36: H4RG border + Dual-Fiber FluxA/FluxB symmetry + overlap consistency
    g4_reasons = []
    margin = int(cfg["gate_g4_chip_edge_margin_px"])
    if not (margin <= prim["native_px"] <= (prim["n_px"] - 1 - margin)):
        g4_reasons.append("H4RG_ORDER_BORDER_DROOP")

    fiber_ab_tested = False
    fiber_ab_ratio = None
    snr_a, snr_b = None, None
    fa_e, fb_e = prim.get("fiber_a_eval"), prim.get("fiber_b_eval")
    if fa_e and fb_e and fa_e.get("usable") and fb_e.get("usable"):
        fiber_ab_tested = True
        snr_a, snr_b = float(fa_e["native_snr"]), float(fb_e["native_snr"])
        fiber_ab_ratio = float(fa_e["native_amp_rel"] / max(1e-12, fb_e["native_amp_rel"])) if fb_e["native_amp_rel"] > 0 else 99.0
        if snr_a < cfg["gate_g4_fiber_ab_snr_min"] or snr_b < cfg["gate_g4_fiber_ab_snr_min"] or not (cfg["gate_g4_fiber_ab_ratio_min"] <= fiber_ab_ratio <= cfg["gate_g4_fiber_ab_ratio_max"]):
            g4_reasons.append("SINGLE_FIBER_POLAR_A_OR_B_DEFECT")

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
            g4_reasons.append("SINGLE_ORDER_H4RG_ARTIFACT")
    g4_pass = len(g4_reasons) == 0

    # Gate G5_V36: H4RG 11-px LSF morphology
    g5_reasons = []
    if prim["cos_1d_11px"] < cfg["gate_g5_h4rg_cos11_min"]:
        g5_reasons.append("H4RG_11PX_LSF_COSINE_MISMATCH")
    if prim["ipc_hotpx_ratio"] > cfg["gate_g5_h4rg_max_ipc_ratio"]:
        g5_reasons.append("H4RG_IPC_HOT_PIXEL")
    if prim["far_wing_34_ratio"] > cfg["gate_g5_h4rg_far_wing_34_max"]:
        g5_reasons.append("H4RG_PERSISTENCE_OR_BANDHEAD_PLATEAU")
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
        "fiber_ab_tested": bool(fiber_ab_tested),
        "fiber_a_snr": float(snr_a) if snr_a is not None else None,
        "fiber_b_snr": float(snr_b) if snr_b is not None else None,
        "fiber_ab_amp_ratio": float(fiber_ab_ratio) if fiber_ab_ratio is not None else None,
        "overlap_tested": bool(overlap_tested),
        "secondary_order": dedup_q[1]["order"] if overlap_tested else None,
        "secondary_native_snr": float(sec_snr) if sec_snr is not None else None,
        "secondary_over_primary_contrast": float(sec_contrast) if sec_contrast is not None else None,
        "g4_pass": g4_pass,
        "g4_reason": "PASS" if g4_pass else ";".join(g4_reasons),
        "cos_1d_11px": prim["cos_1d_11px"],
        "ipc_hotpx_ratio": prim["ipc_hotpx_ratio"],
        "far_wing_34_ratio": prim["far_wing_34_ratio"],
        "g5_pass": g5_pass,
        "g5_reason": "PASS" if g5_pass else ";".join(g5_reasons),
    }


def evaluate_gate_g6_v35_dense(
    target_star: str,
    cand_topo_vac_a: float,
    cand_order: int | None,
    cand_px: int | None,
    target_vshift_kms: float,
    dense_atlas: list[dict[str, Any]],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    topo_tol = float(cfg["gate_g6_dense_topo_tol_a"])
    px_tol = float(cfg["gate_g6_dense_pixel_tol_px"])
    min_dv = float(cfg["gate_g6_min_dv_frame_sep_kms"])
    prom_min = float(cfg["gate_g6_dense_prom_min"])
    snr_min = float(cfg["gate_g6_dense_snr_min"])
    topo_stars, pixel_stars, all_stars = set(), set(), set()
    for rec in dense_atlas:
        other = rec["star"]
        if other == target_star:
            continue
        if abs(float(rec["vshift_kms"]) - float(target_vshift_kms)) < min_dv:
            continue
        if float(rec["prom_rel"]) < prom_min or float(rec["snr_local"]) < snr_min:
            continue
        matched = False
        if abs(float(rec["topo_vac_a"]) - float(cand_topo_vac_a)) <= topo_tol:
            topo_stars.add(other)
            matched = True
        if cand_order is not None and cand_px is not None and rec.get("order") is not None and rec.get("px") is not None:
            if int(rec["order"]) == int(cand_order) and abs(float(rec["px"]) - float(cand_px)) <= px_tol:
                pixel_stars.add(other)
                matched = True
        if matched:
            all_stars.add(other)
    n_c = len(all_stars)
    g6_pass = n_c <= int(cfg["gate_g6_max_other_stars"])
    return {
        "g6_v35_coincident_topo_stars": len(topo_stars),
        "g6_v35_coincident_pixel_stars": len(pixel_stars),
        "g6_v35_coincident_total_stars": n_c,
        "g6_v35_pass": bool(g6_pass),
        "g6_v35_reason": "PASS" if g6_pass else f"DENSE_V35_CROSS_STAR_{n_c}STARS",
    }


def evaluate_gate_g6_v36_sparse(
    target_star: str,
    target_dp_id: str,
    target_berv_kms: float,
    cand_topo_vac_a: float,
    cand_order: int | None,
    cand_px: int | None,
    target_vshift_kms: float,
    sparse_atlas: list[dict[str, Any]],
    cfg: dict[str, Any],
    channel: str = "T",
) -> dict[str, Any]:
    """V3.6 Sparse Supraphotospheric Cross-Star + Intra-Star BERV-Stationary Coincidence Gate."""
    topo_tol = float(cfg["gate_g6_sparse_topo_tol_a"])
    px_tol = float(cfg["gate_g6_sparse_pixel_tol_px"])
    min_dv = float(cfg["gate_g6_min_dv_frame_sep_kms"])
    prom_min = float(cfg["gate_g6_sparse_prom_min"])
    snr_min = float(cfg["gate_g6_sparse_snr_min"])
    fn_min = float(cfg["gate_g6_sparse_fn_min"])
    fw_lo, fw_hi = float(cfg["gate_g6_sparse_fwhm_lsf_min"]), float(cfg["gate_g6_sparse_fwhm_lsf_max"])
    same_dberv = float(cfg["gate_g6_same_star_dberv_min_kms"])
    same_topo_tol = float(cfg["gate_g6_same_star_topo_tol_a"])
    same_px_tol = float(cfg["gate_g6_same_star_pixel_tol_px"])

    topo_stars, pixel_stars, all_stars = set(), set(), set()
    same_star_stationary_hits = 0

    for rec in sparse_atlas:
        if float(rec["prom_rel"]) < prom_min or float(rec["snr_local"]) < snr_min:
            continue
        if float(rec.get("f_norm_pk3", 1.0)) < fn_min:
            continue
        fw_rat = float(rec.get("fwhm_over_lsf", 1.0))
        if not (fw_lo <= fw_rat <= fw_hi):
            continue

        other = rec["star"]
        if other == target_star:
            # Intra-star multi-epoch BERV-stationary repeat veto (catches repeat sky/detector lines like HD219134 6269 A in D084)
            if rec.get("dp_id") != target_dp_id and channel == "T":
                if abs(float(rec.get("berv_kms", target_berv_kms)) - float(target_berv_kms)) >= same_dberv:
                    hit_t = abs(float(rec["topo_vac_a"]) - float(cand_topo_vac_a)) <= same_topo_tol
                    hit_p = (
                        cand_order is not None
                        and cand_px is not None
                        and rec.get("order") is not None
                        and rec.get("px") is not None
                        and int(rec["order"]) == int(cand_order)
                        and abs(float(rec["px"]) - float(cand_px)) <= same_px_tol
                    )
                    if hit_t or hit_p:
                        same_star_stationary_hits += 1
            continue

        if abs(float(rec["vshift_kms"]) - float(target_vshift_kms)) < min_dv:
            continue
        matched = False
        if abs(float(rec["topo_vac_a"]) - float(cand_topo_vac_a)) <= topo_tol:
            topo_stars.add(other)
            matched = True
        if cand_order is not None and cand_px is not None and rec.get("order") is not None and rec.get("px") is not None:
            if int(rec["order"]) == int(cand_order) and abs(float(rec["px"]) - float(cand_px)) <= px_tol:
                pixel_stars.add(other)
                matched = True
        if matched:
            all_stars.add(other)

    n_c = len(all_stars)
    cross_fail = n_c > int(cfg["gate_g6_max_other_stars"])
    intra_fail = same_star_stationary_hits >= 1
    g6_pass = (not cross_fail) and (not intra_fail)
    if g6_pass:
        reason = "PASS"
    elif cross_fail and len(pixel_stars) > len(topo_stars):
        reason = f"SPARSE_G6_FIXED_PIXEL_{n_c}STARS"
    elif cross_fail:
        reason = f"SPARSE_G6_CROSS_STAR_TOPO_{n_c}STARS"
    else:
        reason = f"SPARSE_G6_INTRA_STAR_BERV_STATIONARY_{same_star_stationary_hits}EPOCHS"

    return {
        "g6_coincident_topo_stars": len(topo_stars),
        "g6_coincident_pixel_stars": len(pixel_stars),
        "g6_coincident_total_stars": n_c,
        "g6_same_star_stationary_hits": int(same_star_stationary_hits),
        "g6_coincident_star_list": sorted(all_stars)[:12],
        "g6_pass": bool(g6_pass),
        "g6_reason": reason,
    }


def _build_freq_band_vectors(
    bary_grid: np.ndarray,
    y_rest_stack: np.ndarray,
    sigma_rest_stack: np.ndarray,
    flux_norm_stack: np.ndarray,
    recon_stack: np.ndarray,
    sky_mask_bary: np.ndarray,
    lo_a: float,
    hi_a: float,
    df_ghz: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Resample one clean window onto a descending-wavelength = ascending-frequency 0.5 GHz grid."""
    nu_min = C_ANGSTROM_GHZ / float(hi_a)
    nu_max = C_ANGSTROM_GHZ / float(lo_a)
    nu_grid = np.arange(nu_min, nu_max + 0.5 * df_ghz, df_ghz, dtype=np.float64)
    w_of_nu = C_ANGSTROM_GHZ / nu_grid
    # bary_grid is ascending; sample directly at w_of_nu
    z_raw = np.where(np.isfinite(y_rest_stack) & np.isfinite(sigma_rest_stack) & (sigma_rest_stack > 0), y_rest_stack / sigma_rest_stack, 0.0)
    z_nu = np.interp(w_of_nu, bary_grid, z_raw)
    fn_fill = np.where(np.isfinite(flux_norm_stack), flux_norm_stack, 1.0)
    fn_nu = np.interp(w_of_nu, bary_grid, fn_fill)
    rc_fill = np.where(np.isfinite(recon_stack), recon_stack, 0.0)
    rc_nu = np.interp(w_of_nu, bary_grid, rc_fill)
    fin_nu = np.interp(w_of_nu, bary_grid, np.isfinite(y_rest_stack).astype(np.float64)) > 0.85
    sky_nu = np.interp(w_of_nu, bary_grid, sky_mask_bary.astype(np.float64)) > 0.25
    clean_nu = fin_nu & (~sky_nu) & (rc_nu >= 0.78)
    z_nu = np.where(clean_nu, z_nu, -9.0)
    return nu_grid, z_nu, fn_nu, rc_nu, clean_nu


def scan_frequency_comb_v4(
    bary_grid: np.ndarray,
    y_rest_stack: np.ndarray,
    sigma_rest_stack: np.ndarray,
    flux_norm_stack: np.ndarray,
    recon_stack: np.ndarray,
    sky_mask_bary: np.ndarray,
    y_topo_stack: np.ndarray | None,
    sigma_topo_stack: np.ndarray | None,
    median_berv_kms: float,
    v_star_kms: float,
    cfg: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    """V4 `COMB` Channel: Coherent M = 6 equally-spaced frequency-comb matched search across Y/J/H/K_core."""
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
    tol_bins = 2  # +/- 1.0 GHz LSF jitter tolerance per tooth

    win_by_name = {w["band"]: w for w in CLEAN_SPIROU_WINDOWS_VAC_A}
    all_cands: list[dict[str, Any]] = []
    searched_configs = 0

    for bname in cfg["comb_search_bands"]:
        win = win_by_name[bname]
        nu_g, z_nu, fn_nu, rc_nu, cln_nu = _build_freq_band_vectors(
            bary_grid, y_rest_stack, sigma_rest_stack, flux_norm_stack, recon_stack, sky_mask_bary,
            float(win["lo_a"]), float(win["hi_a"]), df_ghz,
        )
        if y_topo_stack is not None and sigma_topo_stack is not None:
            # Evaluate topocentric stack over the same nu grid for ro-vibrational anti-comb check
            _, z_topo_nu, _, _, _ = _build_freq_band_vectors(
                bary_grid, y_topo_stack, sigma_topo_stack, np.ones_like(y_topo_stack), np.ones_like(y_topo_stack),
                np.zeros_like(sky_mask_bary), float(win["lo_a"]), float(win["hi_a"]), df_ghz,
            )
        else:
            z_topo_nu = np.zeros_like(z_nu)

        # Max-pool +-tol_bins around each frequency bin to absorb 1 GHz dispersion/calibration jitter
        n_nu = len(nu_g)
        z_max = z_nu.copy()
        fn_max = fn_nu.copy()
        rc_max = rc_nu.copy()
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

        zt_max = z_topo_nu.copy()
        for sh in range(-tol_bins, tol_bins + 1):
            if sh == 0:
                continue
            zt_sh = np.roll(z_topo_nu, sh)
            zt_max = np.maximum(zt_max, zt_sh)

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
            max_z = np.max(tooth_z, axis=0)
            dom_frac = max_z / np.maximum(1e-9, sum_z)
            s_topo = np.sum(tooth_zt, axis=0) / math.sqrt(m_teeth)

            hits = np.flatnonzero((n_q >= min_qual) & (s_comb >= s_min) & (dom_frac <= dom_max))
            for h_i in hits:
                k_start = int(idx0[h_i])
                sc = float(s_comb[h_i])
                st_sc = float(s_topo[h_i])
                anti_ratio = st_sc / max(1e-9, sc)
                if anti_ratio > anti_max:
                    continue
                zs = [round(float(tooth_z[t, h_i]), 3) for t in range(m_teeth)]
                nu0 = float(nu_g[k_start])
                w_teeth_a = [round(C_ANGSTROM_GHZ / (nu0 + t * float(dnu_ghz)), 3) for t in range(m_teeth)]
                all_cands.append({
                    "band": bname,
                    "dnu_ghz": float(dnu_ghz),
                    "nu0_ghz": round(nu0, 3),
                    "nu_end_ghz": round(nu0 + (m_teeth - 1) * float(dnu_ghz), 3),
                    "wave0_vac_a": w_teeth_a[0],
                    "wave_end_vac_a": w_teeth_a[-1],
                    "s_comb": round(sc, 4),
                    "s_comb_topo": round(st_sc, 4),
                    "topo_anti_ratio": round(anti_ratio, 4),
                    "n_qualifying_teeth": int(n_q[h_i]),
                    "max_tooth_frac": round(float(dom_frac[h_i]), 4),
                    "tooth_z_caps": zs,
                    "teeth_vac_a": w_teeth_a,
                })

    # Deduplicate overlapping combs across offsets within same (band, dnu_ghz)
    dedup = []
    for c in sorted(all_cands, key=lambda x: -x["s_comb"]):
        if any(p["band"] == c["band"] and abs(p["dnu_ghz"] - c["dnu_ghz"]) < 1e-3 and abs(p["nu0_ghz"] - c["nu0_ghz"]) <= 0.5 * c["dnu_ghz"] for p in dedup):
            continue
        dedup.append(c)
    return dedup, searched_configs


def stellar_spirou_continuum_flam_earth(
    wave_vac_a: float,
    j_mag: float,
    h_mag: float,
    ks_mag: float,
    teff_k: float,
) -> tuple[str, float]:
    """Piecewise 3-band Cohen et al. (2003) 2MASS J (< 14,200 A), H (14,200-18,800 A), and Ks (>= 18,800 A)
    Planck-sloped continuum flux density F_lambda in erg cm^-2 s^-1 A^-1."""
    w = float(wave_vac_a)
    if w < 14200.0:
        band_used, piv_a, zp, mag = "2MASS_J", TWOMASS_J_PIVOT_A, TWOMASS_J_ZP_FLAM, float(j_mag)
    elif w < 18800.0:
        band_used, piv_a, zp, mag = "2MASS_H", TWOMASS_H_PIVOT_A, TWOMASS_H_ZP_FLAM, float(h_mag)
    else:
        band_used, piv_a, zp, mag = "2MASS_Ks", TWOMASS_KS_PIVOT_A, TWOMASS_KS_ZP_FLAM, float(ks_mag)
    xw = HC_OVER_K_ANGSTROM_KELVIN / (w * float(teff_k))
    xp = HC_OVER_K_ANGSTROM_KELVIN / (piv_a * float(teff_k))
    b_ratio = ((piv_a / w) ** 5) * math.expm1(xp) / math.expm1(xw)
    return band_used, float(zp * (10.0 ** (-0.4 * mag)) * b_ratio)


def compute_spirou_laser_power_limits(
    wave_vac_a: float,
    amp_rel_lim: float,
    j_mag: float,
    h_mag: float,
    ks_mag: float,
    teff_k: float,
    dist_pc: float,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    fwhm_a = float(wave_vac_a) / float(cfg["resolving_power"])
    gauss_area = math.sqrt(math.pi / (4.0 * math.log(2.0)))
    ew_a = gauss_area * float(amp_rel_lim) * fwhm_a
    phot_band, flam = stellar_spirou_continuum_flam_earth(wave_vac_a, j_mag, h_mag, ks_mag, teff_k)
    f_line_cgs = flam * ew_a
    d_cm = float(dist_pc) * PC_CM
    l_iso_w = 4.0 * math.pi * (d_cm ** 2) * f_line_cgs * 1.0e-7
    lam_m = float(wave_vac_a) * 1.0e-10
    d_tx_m = float(cfg["tx_aperture_diameter_m"])
    airy_gain = (math.pi * d_tx_m / lam_m) ** 2
    p_beam_10m_w = l_iso_w / airy_gain
    return {
        "phot_anchor_band": phot_band,
        "fwhm_lsf_a": float(fwhm_a),
        "ew_lim_mA": float(ew_a * 1000.0),
        "continuum_flam_cgs": float(flam),
        "flux_lim_erg_cm2_s": float(f_line_cgs),
        "l_iso_mw": float(l_iso_w * 1.0e-6),
        "p_beam_10m_w": float(p_beam_10m_w),
        "p_beam_10m_kw": float(p_beam_10m_w * 1.0e-3),
    }


def run_legacy_v2_spirou_benchmark(wave: np.ndarray, flux: np.ndarray, cfg: dict[str, Any]) -> dict[str, Any]:
    w = np.asarray(wave, dtype=np.float64)
    f = np.asarray(flux, dtype=np.float64)
    in_win = is_in_clean_windows(w)
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
        mad = MAD_NORM * median_filter(np.abs(resid), size=101, mode="nearest")
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
            noise = float(MAD_NORM * np.median(np.abs((side - icp - slope * x_sb) - np.median(side - icp - slope * x_sb))))
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
