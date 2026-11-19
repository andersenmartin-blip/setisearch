#!/usr/bin/env python3
"""
Phase D090 Detector Module: `JWST_SPACE_THERMAL_IR_V4_1`

Prospectively locked physics & radiometric detector for JWST thermal-infrared
spectroscopy across:
  - JWST_NIRSPEC_G235H (1.655-3.072 um, R = 2,700)
  - JWST_NIRSPEC_G395H (2.862-5.179 um, R = 2,700)
  - JWST_MIRI_MRS      (4.900-28.000 um, R ~ 1,450-3,550; wavelength-dependent LSF)

Key D090 thermal-IR architecture:
  1. Direct-Jy to CGS FLAM calibration (`flam = flux_jy * 2.99792458e-5 / wave_A^2`)
     covering 15 bands including the canonical Townes (1983) 10.60 um CO2 laser.
  2. Wavelength-dependent MIRI MRS resolving power `effective_resolving_power()` and
     dynamic velocity-scaled fitting/background annuli out to 28.00 um.
  3. Sun-Earth L2 pure-stdlib Earth heliocentric RV and Römer delay (`1.010 * earth_roemer_s`)
     audits (`stdlib_earth_helio_rv_kms`, `stdlib_earth_roemer_s`).
  4. Gate G2_V41: zero telluric/geocoronal emission at L2; masks NIRSpec NRS1/NRS2 physical
     detector gaps & fatal JWST DQ flags (`DO_NOT_USE | SATURATED | JUMP_DET | DROPOUT`).
  5. Gate G3_V41: HI Brackett/Pfund/Humphreys, H2 pure-rotational S(0)..S(7) & 1-0 S(1),
     [Ar II], [Ne II], [Ne III], [Fe II], [S III], [S I], and CO2 Q-branch nebular/stellar lines.
  6. Gate G4_V41: JWST MIRI MRS sub-band & cross-detector (`SHORT`/`MEDIUM`/`LONG`,
     `MIRIFUSHORT`/`MIRIFULONG`) multi-segment coincidence enforcement in overlap zones.
  7. COMB_V4_1: LSF-resolved frequency-comb grids (45-560 GHz) with L2 sky/emission masking
     and barycentric-vs-rest-frame consistency.
"""
from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np
from scipy.ndimage import median_filter

DETECTOR_NAME = "JWST_SPACE_THERMAL_IR_V4_1"

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

# JWST Pipeline DQ bitmask: bit 0=DO_NOT_USE(1), bit 1=SATURATED(2), bit 2=JUMP_DET(4), bit 3=DROPOUT(8)
JWST_FATAL_DQ_MASK = 1 | 2 | 4 | 8

# ---------------------------------------------------------------------------
# Gate G1/G2_V41: NIRSpec Detector Gaps (no telluric/geocoronal lines at L2)
# ---------------------------------------------------------------------------

JWST_AIRGLOW_BANDS_VAC_A: list[dict[str, Any]] = []

NIRSPEC_DETECTOR_GAPS_A: dict[str, tuple[float, float]] = {
    "JWST_NIRSPEC_G235H": (22040.0, 22650.0),
    "JWST_NIRSPEC_G395H": (37200.0, 38220.0),
}

# ---------------------------------------------------------------------------
# Gate G3_V41: Infrared Atomic, H2, & Fine-Structure Emission Lines (Vac A)
# ---------------------------------------------------------------------------

STELLAR_IR_EMISSION_VAC_A = [
    {"name": "HI_Br10_17366", "wave_A": 17366.85},
    {"name": "FeII_17936", "wave_A": 17936.00},
    {"name": "HI_Br9_18179", "wave_A": 18179.09},
    {"name": "HI_PaA_18756", "wave_A": 18756.13},
    {"name": "HI_BrD_19451", "wave_A": 19450.87},
    {"name": "H2_1_0_S1_21218", "wave_A": 21218.30},
    {"name": "HI_BrG_21661", "wave_A": 21661.20},
    {"name": "HI_PfG_37406", "wave_A": 37405.60},
    {"name": "HI_BrA_40523", "wave_A": 40522.60},
    {"name": "H2_0_0_S9_46946", "wave_A": 46946.10},
    {"name": "H2_0_0_S7_55112", "wave_A": 55111.60},
    {"name": "H2_0_0_S6_61086", "wave_A": 61085.60},
    {"name": "H2_0_0_S5_69095", "wave_A": 69095.20},
    {"name": "ArII_69853", "wave_A": 69852.74},
    {"name": "HI_PfA_74599", "wave_A": 74598.60},
    {"name": "H2_0_0_S4_80251", "wave_A": 80250.50},
    {"name": "ArIII_89914", "wave_A": 89913.80},
    {"name": "H2_0_0_S3_96649", "wave_A": 96649.10},
    {"name": "SIV_105105", "wave_A": 105105.00},
    {"name": "H2_0_0_S2_122786", "wave_A": 122786.10},
    {"name": "HI_HuA_123719", "wave_A": 123719.00},
    {"name": "NeII_128135", "wave_A": 128135.50},
    {"name": "CO2_Q_149800", "wave_A": 149800.00},
    {"name": "NeIII_155551", "wave_A": 155551.00},
    {"name": "H2_0_0_S1_170348", "wave_A": 170348.30},
    {"name": "SIII_187130", "wave_A": 187130.30},
    {"name": "SI_252490", "wave_A": 252490.00},
    {"name": "FeII_259884", "wave_A": 259883.90},
    {"name": "H2_0_0_S0_282188", "wave_A": 282188.30},
]

# ---------------------------------------------------------------------------
# NIST / HITRAN Thermal-IR Photospheric & Circumstellar RV Anchors (Vac A)
# ---------------------------------------------------------------------------

LOCKED_RV_ANCHORS_G235H = [
    {"anchor_id": "HI_BR10_17367", "species": "H I Br10", "lab_wave_A": 17366.85},
    {"anchor_id": "HI_BR9_18179", "species": "H I Br9", "lab_wave_A": 18179.09},
    {"anchor_id": "HI_PAA_18756", "species": "H I Pa-a", "lab_wave_A": 18756.13},
    {"anchor_id": "HI_BRD_19451", "species": "H I Br-d", "lab_wave_A": 19450.87},
    {"anchor_id": "HI_BRG_21661", "species": "H I Br-g", "lab_wave_A": 21661.20},
    {"anchor_id": "NAI_22062", "species": "Na I", "lab_wave_A": 22062.42},
    {"anchor_id": "CO_20_22935", "species": "CO (2-0)", "lab_wave_A": 22935.30},
    {"anchor_id": "HI_PFG_26259", "species": "H I Pf-g", "lab_wave_A": 26258.70},
]

LOCKED_RV_ANCHORS_G395H = [
    {"anchor_id": "HI_PFD_32970", "species": "H I Pf-d", "lab_wave_A": 32969.90},
    {"anchor_id": "HI_PFG_37406", "species": "H I Pf-g", "lab_wave_A": 37405.60},
    {"anchor_id": "HI_BRA_40523", "species": "H I Br-a", "lab_wave_A": 40522.60},
    {"anchor_id": "HI_PFB_46538", "species": "H I Pf-b", "lab_wave_A": 46537.80},
    {"anchor_id": "CO_10_46575", "species": "CO (1-0) R", "lab_wave_A": 46574.90},
]

LOCKED_RV_ANCHORS_MIRI_MRS = [
    {"anchor_id": "HI_PFA_74599", "species": "H I Pf-a", "lab_wave_A": 74598.60},
    {"anchor_id": "HI_HUB_75025", "species": "H I Hu-b", "lab_wave_A": 75024.90},
    {"anchor_id": "H2_S2_122786", "species": "H2 0-0 S(2)", "lab_wave_A": 122786.10},
    {"anchor_id": "HI_HUA_123719", "species": "H I Hu-a", "lab_wave_A": 123719.00},
    {"anchor_id": "NEII_128135", "species": "[Ne II]", "lab_wave_A": 128135.50},
]

# ---------------------------------------------------------------------------
# Direct-Jy Thermal-IR Calibration & Radiometric Upper-Limit Bands (15 total)
# ---------------------------------------------------------------------------

CALIBRATION_BANDS_G235H = [
    {"band_id": "G2_17500", "center_wave_A": 17500.0},
    {"band_id": "G2_20400", "center_wave_A": 20400.0},
    {"band_id": "G2_21200", "center_wave_A": 21200.0},
    {"band_id": "G2_24500", "center_wave_A": 24500.0},
    {"band_id": "G2_29000", "center_wave_A": 29000.0},
]

CALIBRATION_BANDS_G395H = [
    {"band_id": "G3_30500", "center_wave_A": 30500.0},
    {"band_id": "G3_34500", "center_wave_A": 34500.0},
    {"band_id": "G3_41000", "center_wave_A": 41000.0},
    {"band_id": "G3_45500", "center_wave_A": 45500.0},
    {"band_id": "G3_50000", "center_wave_A": 50000.0},
]

CALIBRATION_BANDS_MIRI_MRS = [
    {"band_id": "M1_58000", "center_wave_A": 58000.0},
    {"band_id": "M2_82000", "center_wave_A": 82000.0},
    {"band_id": "M3_106000", "center_wave_A": 106000.0},
    {"band_id": "M4_165000", "center_wave_A": 165000.0},
    {"band_id": "M5_235000", "center_wave_A": 235000.0},
]

COMB_V4_1_WINDOWS_A: dict[str, list[dict[str, Any]]] = {
    "JWST_NIRSPEC_G235H": [
        {"band": "G235H_NRS1", "lo_a": 16800.0, "hi_a": 21800.0},
        {"band": "G235H_NRS2", "lo_a": 22900.0, "hi_a": 30500.0},
    ],
    "JWST_NIRSPEC_G395H": [
        {"band": "G395H_NRS1", "lo_a": 28900.0, "hi_a": 36900.0},
        {"band": "G395H_NRS2", "lo_a": 38500.0, "hi_a": 51400.0},
    ],
    "JWST_MIRI_MRS": [
        {"band": "MIRI_CH12", "lo_a": 50000.0, "hi_a": 115000.0},
        {"band": "MIRI_CH34", "lo_a": 120000.0, "hi_a": 275000.0},
    ],
}

# ---------------------------------------------------------------------------
# Prospectively Locked Detector Configuration
# ---------------------------------------------------------------------------

BASE_V4_1_CONFIG: dict[str, Any] = {
    "detector_name": DETECTOR_NAME,
    "instrument": "JWST_MIRI_MRS",
    "resolving_power": 2500.0,
    "sigma_v_kms": C_KMS / (2500.0 * FWHM_FACTOR),
    "wave_range_a": (49000.0, 280000.0),
    "coadd_rest_min_angstrom": 49000.0,
    "coadd_rest_max_angstrom": 280000.0,
    "coadd_step_angstrom": 5.0,
    "radiometric_anchor": "JWST_MIRI_MRS_DIRECT_JY",
    # Step 1: IR RV anchors
    "rv_anchor_window_kms": 650.0,
    "rv_anchor_fwhm_kms": 115.0,
    "rv_anchor_scan_half_kms": 160.0,
    "rv_anchor_scan_step_kms": 2.0,
    "rv_anchor_min_snr": 4.0,
    # Step 2: Continuum & overlap-aware KNN
    "continuum_block_bins": 40,
    "continuum_median_blocks": 5,
    "continuum_quantile": 0.72,
    "continuum_quantile_blue": 0.72,
    "continuum_blue_cutoff_angstrom": 18000.0,
    "knn_atlas_neighbors": 4,
    "knn_teff_scale_k": 1500.0,
    "knn_mh_scale_dex": 0.50,
    "knn_min_wave_overlap_frac": 0.55,
    # Step 3: Matched LSF scan (annuli expressed cleanly in velocity sigma units)
    "fit_phases_bins": [-0.35, -0.15, 0.0, 0.15, 0.35],
    "core_sigma_mult": 2.8,
    "mid_inner_sigma_mult": 4.0,
    "mid_outer_sigma_mult": 16.0,
    "outer_inner_sigma_mult": 6.0,
    "outer_outer_sigma_mult": 22.0,
    "supraphotospheric_min_fn_pk3": 1.005,
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
    # Step 4: V4.1 Physics Vetting Gates (G3, G4_V41, G5, G6)
    "g4_min_continuum_snr": 1.2,
    "g4_max_template_dip_frac": 0.35,
    "miri_dual_min_snr": 4.0,
    "g5_min_native_snr": 4.0,
    "g5_eta_1px_max": 0.74,
    "g5_min_wing_ratio": 0.14,
    "g5_ipc_hotpx_ratio_max": 2.20,
    "g5_far_wing_34_max": 0.42,
    "g5_cos_1d_11px_min": 0.72,
    "g6_topo_tol_kms": 20.0,
    "g6_px_tol": 1.0,
    "g6_min_berv_shift_kms": 4.0,
    "g6_min_diff_stars": 2,
    # Step 5: COMB_V4_1
    "comb_spacings_ghz": [45.0, 65.0, 95.0, 140.0, 200.0],
    "comb_step_ghz": 4.5,
    "comb_n_teeth": 6,
    "comb_tooth_snr_min": 2.2,
    "comb_sum_snr_min": 20.5,
    "comb_min_qualifying_teeth": 5,
    "comb_max_off_tooth_crowding": 0.38,
    "comb_min_intertooth_ratio": 1.85,
    "comb_min_topo_anti_ratio": 1.08,
    "comb_min_fn_pk3": 1.005,
    "comb_search_bands": ["MIRI_CH12", "MIRI_CH34"],
}


def effective_resolving_power(cfg: dict[str, Any], wave_a: float) -> float:
    """Return local resolving power R(lambda); captures MIRI MRS CH1-CH4 gradient."""
    if cfg.get("instrument") == "JWST_MIRI_MRS" and math.isfinite(float(wave_a)) and float(wave_a) > 0.0:
        w_um = float(wave_a) / 10000.0
        return float(max(1450.0, min(3550.0, 3950.0 - 95.0 * w_um)))
    return float(cfg.get("resolving_power", 2700.0))


def _scan_margin_bins(wave_a: float, cfg: dict[str, Any], min_bins: int = 45, max_bins: int = 340) -> int:
    step_a = float(cfg["coadd_step_angstrom"])
    r_eff = effective_resolving_power(cfg, wave_a)
    sig_a = float(wave_a) / (r_eff * FWHM_FACTOR)
    m = int(math.ceil(15.0 * sig_a / max(1e-6, step_a)))
    return int(max(min_bins, min(max_bins, m)))


def get_inst_config(instrument: str, resolving_power: float | None = None) -> dict[str, Any]:
    cfg = dict(BASE_V4_1_CONFIG)
    cfg["instrument"] = instrument
    if instrument == "JWST_NIRSPEC_G235H":
        r_val = float(resolving_power) if resolving_power is not None else 2700.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (16550.0, 30720.0),
            "coadd_rest_min_angstrom": 16550.0,
            "coadd_rest_max_angstrom": 30720.0,
            "coadd_step_angstrom": 2.0,
            "scan_nms_min_sep_bins": 18,
            "radiometric_anchor": "JWST_NIRSPEC_G235H_DIRECT_JY",
            "rv_anchors": LOCKED_RV_ANCHORS_G235H,
            "comb_spacings_ghz": [180.0, 240.0, 320.0, 420.0, 560.0],
            "comb_step_ghz": 16.0,
            "comb_search_bands": ["G235H_NRS1", "G235H_NRS2"],
            "g6_topo_tol_kms": max(20.0, 0.35 * (C_KMS / r_val)),
        })
    elif instrument == "JWST_NIRSPEC_G395H":
        r_val = float(resolving_power) if resolving_power is not None else 2700.0
        cfg.update({
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (28620.0, 51790.0),
            "coadd_rest_min_angstrom": 28620.0,
            "coadd_rest_max_angstrom": 51790.0,
            "coadd_step_angstrom": 3.5,
            "scan_nms_min_sep_bins": 18,
            "radiometric_anchor": "JWST_NIRSPEC_G395H_DIRECT_JY",
            "rv_anchors": LOCKED_RV_ANCHORS_G395H,
            "comb_spacings_ghz": [100.0, 140.0, 190.0, 260.0, 350.0],
            "comb_step_ghz": 10.0,
            "comb_search_bands": ["G395H_NRS1", "G395H_NRS2"],
            "g6_topo_tol_kms": max(20.0, 0.35 * (C_KMS / r_val)),
        })
    else:
        r_val = float(resolving_power) if resolving_power is not None else 2500.0
        cfg.update({
            "instrument": "JWST_MIRI_MRS",
            "resolving_power": r_val,
            "sigma_v_kms": C_KMS / (r_val * FWHM_FACTOR),
            "wave_range_a": (49000.0, 280000.0),
            "coadd_rest_min_angstrom": 49000.0,
            "coadd_rest_max_angstrom": 280000.0,
            "coadd_step_angstrom": 5.0,
            "scan_nms_min_sep_bins": 28,
            "radiometric_anchor": "JWST_MIRI_MRS_DIRECT_JY",
            "rv_anchors": LOCKED_RV_ANCHORS_MIRI_MRS,
            "comb_spacings_ghz": [45.0, 65.0, 95.0, 140.0, 200.0],
            "comb_step_ghz": 4.5,
            "comb_search_bands": ["MIRI_CH12", "MIRI_CH34"],
            "g6_topo_tol_kms": max(22.0, 0.35 * (C_KMS / r_val)),
        })
    return cfg


def get_calibration_bands(instrument: str) -> list[dict[str, Any]]:
    if instrument == "JWST_NIRSPEC_G235H":
        return list(CALIBRATION_BANDS_G235H)
    if instrument == "JWST_NIRSPEC_G395H":
        return list(CALIBRATION_BANDS_G395H)
    return list(CALIBRATION_BANDS_MIRI_MRS)


def resolve_band_radiometric_anchor(instrument: str) -> str:
    return str(get_inst_config(instrument)["radiometric_anchor"])


def jy_to_flam_cgs(flux_jy: np.ndarray | float, wave_a: np.ndarray | float) -> np.ndarray | float:
    """Exact spectral flux density conversion Jy -> erg s^-1 cm^-2 A^-1."""
    return flux_jy * 2.99792458e-5 / (wave_a * wave_a)


# ---------------------------------------------------------------------------
# Pure-Stdlib Earth Heliocentric Ephemeris & Sun-Earth L2 Roemer Delay
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

    # Sun->Earth position is minus geocentric Sun position
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


def stdlib_earth_roemer_s(ra_deg: float, dec_deg: float, mjd_mid: float) -> float:
    ex, ey, ez, _, _, _ = _earth_sun_state_equatorial(mjd_mid)
    ra_r = math.radians(float(ra_deg))
    dec_r = math.radians(float(dec_deg))
    ux = math.cos(dec_r) * math.cos(ra_r)
    uy = math.cos(dec_r) * math.sin(ra_r)
    uz = math.sin(dec_r)
    return float(((ex * ux + ey * uy + ez * uz) * AU_M) / C_SI)


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
# Step 1: Thermal-IR RV Anchoring
# ---------------------------------------------------------------------------

def extract_rv_anchor_window(
    wave: np.ndarray,
    flux: np.ndarray,
    lab_wave_a: float,
    prior_rv_kms: float,
    cfg: dict[str, Any] = BASE_V4_1_CONFIG,
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
    cfg: dict[str, Any] = BASE_V4_1_CONFIG,
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
    anchors = cfg.get("rv_anchors", LOCKED_RV_ANCHORS_MIRI_MRS)
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
    cfg: dict[str, Any] = BASE_V4_1_CONFIG,
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
    cfg: dict[str, Any] = BASE_V4_1_CONFIG,
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
# Step 3: Wavelength-Adaptive Instrument-LSF Matched Filtering (T, P, T_DIFF, K_PLANET)
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
# Step 4: Automated Physics Vetting Gates G2_V41, G3_V41, G4_V41, G5, G6
# ---------------------------------------------------------------------------

def evaluate_gate_g2_airglow(
    fitted_bary_wave_a: float,
    berv_kms: float,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """L2 spacecraft gate: zero airglow; masks only physical NIRSpec detector chip gaps."""
    topo_a = float(fitted_bary_wave_a / (1.0 + berv_kms / C_KMS))
    inst = cfg.get("instrument", "")
    if inst in NIRSPEC_DETECTOR_GAPS_A:
        lo_g, hi_g = NIRSPEC_DETECTOR_GAPS_A[inst]
        if lo_g <= topo_a <= hi_g:
            return {
                "topo_wave_a": topo_a,
                "nearest_airglow_name": f"{inst}_DETECTOR_GAP",
                "nearest_airglow_sep_a": 0.0,
                "g2_pass": False,
                "g2_reason": f"{inst}_DETECTOR_GAP",
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


def evaluate_gates_g3_g4_g5_v41(
    order_patches: list[dict[str, Any]],
    dpr_or_calsel: str,
    channel: str,
    star_rest_a: float | None,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    inst = cfg.get("instrument", "")
    # Gate G3_V41: Infrared nebular/stellar emission rejection
    if star_rest_a is not None:
        r_eff = effective_resolving_power(cfg, float(star_rest_a))
        tol_a = 1.5 * (float(star_rest_a) / r_eff)
        best_line = min(STELLAR_IR_EMISSION_VAC_A, key=lambda ch: abs(float(star_rest_a) - float(ch["wave_A"])))
        if abs(float(star_rest_a) - float(best_line["wave_A"])) <= tol_a:
            return {
                "g3_pass": False,
                "g4_pass": False,
                "g5_pass": False,
                "g3_reason": f"IR_EMISSION_{best_line['name']}",
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
        return {**common_meta, "g3_pass": True, "g4_pass": False, "g5_pass": False, "g3_reason": "PASS", "g4_reason": "G3_V41_TEMPLATE_ABSORPTION_LEAK", "g5_reason": "SKIPPED"}

    # G4_V41 DQ flag check & MIRI MRS multi-subband / cross-detector coincidence in overlap zones
    dq = p_meta.get("dq")
    if dq is not None:
        kl = int(prim["local_index"])
        core_dq = 0
        for dq_val in dq[max(0, kl - 1) : min(len(dq), kl + 2)]:
            core_dq |= int(dq_val)
        if (core_dq & JWST_FATAL_DQ_MASK) != 0:
            return {**common_meta, "g3_pass": True, "g4_pass": False, "g5_pass": False, "g3_reason": "PASS", "g4_reason": "JWST_FATAL_DQ_FLAG_ARTIFACT", "g5_reason": "SKIPPED"}

    if inst == "JWST_MIRI_MRS" and len(order_patches) >= 2:
        p_amp = max(1e-30, prim["native_amp_adu"])
        coinc = [
            e for e in usable
            if e["native_snr"] >= cfg["miri_dual_min_snr"] and 0.22 <= (e["native_amp_adu"] / p_amp) <= 4.5
        ]
        if len(coinc) < 2:
            return {**common_meta, "g3_pass": True, "g4_pass": False, "g5_pass": False, "g3_reason": "PASS", "g4_reason": "MIRI_SINGLE_SUBBAND_DETECTOR_ARTIFACT", "g5_reason": "SKIPPED"}

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


evaluate_gates_g3_g4_g5_v40 = evaluate_gates_g3_g4_g5_v41


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
# Step 5: IR Frequency-Comb Search (COMB_V4 and COMB_V4_1)
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
# Step 6: Direct-Jy / FLAM Space Thermal-IR Photon-Beam Upper Limits
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
) -> dict[str, float]:
    r_eff = float(resolving_power)
    if direct_flam_cgs is not None and math.isfinite(float(direct_flam_cgs)) and float(direct_flam_cgs) > 0.0:
        cont_flam_cgs = float(direct_flam_cgs)
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
