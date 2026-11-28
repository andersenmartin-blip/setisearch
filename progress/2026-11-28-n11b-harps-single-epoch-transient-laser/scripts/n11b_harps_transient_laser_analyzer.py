#!/usr/bin/env python3
"""Prospective Blind-Locked Analyzer for Spor N11B: Single-Epoch Monochromatic Optical Laser Transients in HARPS."""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import time
from pathlib import Path

from astropy.io import fits
import numpy as np
from scipy.ndimage import gaussian_filter1d, median_filter
from scipy.stats import beta as sp_beta

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n11b_20261128_harps_single_epoch_transient_laser"
INP = ROOT / "inputs_n11b_20261128"
RES = WS / "results"

TARGET_META = {
    "PROXIMACEN": {"common": "Proxima Centauri", "dist_pc": 1.3020, "n_pl": 2, "vmag": 11.13},
    "BARNARDSSTAR": {"common": "Barnard's Star", "dist_pc": 1.8282, "n_pl": 4, "vmag": 9.51},
    "ROSS128": {"common": "Ross 128", "dist_pc": 3.3749, "n_pl": 1, "vmag": 11.15},
    "GJ1061": {"common": "GJ 1061", "dist_pc": 3.6743, "n_pl": 3, "vmag": 13.09},
    "YZCET": {"common": "YZ Cet (GJ 54.1)", "dist_pc": 3.7167, "n_pl": 3, "vmag": 12.07},
    "GJ273": {"common": "Luyten's Star", "dist_pc": 3.7861, "n_pl": 2, "vmag": 9.87},
    "GJ667C": {"common": "GJ 667 C", "dist_pc": 7.2429, "n_pl": 5, "vmag": 10.22},
    "L9859": {"common": "L 98-59", "dist_pc": 10.6194, "n_pl": 5, "vmag": 11.68},
}

LAM = np.linspace(4800.00, 6900.00, 210001, dtype=np.float64)
DLAM = 0.01
HARPS_R = 115000.0
DEC_IDX = np.arange(0, LAM.size, 10, dtype=np.int32)
LAM_DEC = LAM[DEC_IDX]

STATIC_MASK = ((LAM >= 5299.5) & (LAM <= 5343.5)) | (LAM < 4801.0) | (LAM > 6899.0)
BANDS = [
    ("GREEN", 4800.0, 5850.0, 5325.0 / HARPS_R / (2.35482 * DLAM)),  # 1.966 px
    ("RED", 5850.0, 6900.0, 6375.0 / HARPS_R / (2.35482 * DLAM)),    # 2.354 px
]

# Precomputed deterministic 2D PSF grid for fast cutout shape fitting (±9 px core for r_gauss, ±25 px for wings/baseline)
CUT_HALF = 25
CORE_HALF = 9
CORE_DX = np.arange(-CORE_HALF, CORE_HALF + 1, dtype=np.float64)
SIGMA_GRID = np.linspace(0.35, 8.5, 164)
DX0_GRID = np.linspace(-1.5, 1.5, 13)
TEMPLATES: list[tuple[float, float, np.ndarray]] = []
for s in SIGMA_GRID:
    for d0 in DX0_GRID:
        g = np.exp(-0.5 * ((CORE_DX - d0) / s) ** 2)
        g /= math.sqrt(float(np.sum(g * g)))
        TEMPLATES.append((float(s), float(d0), g))


def psf_sigma_px(lam_a: float) -> float:
    return lam_a / HARPS_R / (2.35482 * DLAM)


def fit_cutout_shape(z_cut: np.ndarray, lam_a: float) -> dict[str, float]:
    """Deterministic grid-matched 1D Gaussian shape characterization in ±9 px core with ±25 px wing baseline."""
    wings = np.concatenate([z_cut[:8], z_cut[-8:]])
    base = float(np.median(wings))
    y_core = z_cut[CUT_HALF - CORE_HALF : CUT_HALF + CORE_HALF + 1] - base
    norm_y = float(np.sqrt(np.sum(y_core * y_core))) + 1e-12
    best_r = -1.0
    best_s = 1.0
    for s, _d0, g in TEMPLATES:
        c = float(np.dot(y_core, g)) / norm_y
        if c > best_r:
            best_r = c
            best_s = s
    sig_psf = psf_sigma_px(lam_a)
    fwhm_ratio = best_s / sig_psf
    center_win = z_cut[CUT_HALF - 5 : CUT_HALF + 6]
    n_pix_gt3 = int(np.sum(center_win >= 3.0))
    peak_z = float(np.max(center_win))
    min_neg_ratio = float(np.min(z_cut[CUT_HALF - 10 : CUT_HALF + 11])) / max(peak_z, 1e-6)
    return {
        "fit_sigma_px": round(best_s, 3),
        "psf_sigma_px": round(sig_psf, 3),
        "fwhm_ratio": round(fwhm_ratio, 3),
        "r_gauss": round(best_r, 4),
        "n_pix_gt3": float(n_pix_gt3),
        "min_neg_ratio": round(min_neg_ratio, 3),
        "peak_z_pix": round(peak_z, 2),
    }


def matched_filter_z(z_pix: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Apply R=115,000 unit-variance PSF matched filter across 3 optical bands."""
    zp = np.where(valid, np.clip(z_pix, -25.0, 250.0), 0.0)
    out = np.zeros_like(zp)
    for _bname, l0, l1, spx in BANDS:
        conv = gaussian_filter1d(zp, sigma=spx, mode="constant", cval=0.0)
        conv *= math.sqrt(2.0 * math.sqrt(math.pi) * spx)
        bmask = (LAM >= l0) & (LAM <= l1) & valid
        if np.any(bmask):
            mad = 1.4826 * float(np.median(np.abs(conv[bmask])))
            scale = max(mad, 0.5)
            out[bmask] = conv[bmask] / scale
    return out


def load_and_normalize_spectrum(path: Path) -> tuple[np.ndarray, float]:
    """Load HARPS 1D FITS, interpolate to 0.01 A grid, normalize continuum by decimated rolling median."""
    with fits.open(path, memmap=False) as hdul:
        tab = hdul[1].data
        wave = np.asarray(tab["WAVE"], dtype=np.float64).ravel()
        flux = np.asarray(tab["FLUX"], dtype=np.float64).ravel()
    order = np.argsort(wave)
    wave = wave[order]
    flux = flux[order]
    raw_med = float(np.median(flux[(wave >= 4800.0) & (wave <= 6900.0) & np.isfinite(flux)]))
    f_grid = np.interp(LAM, wave, flux, left=np.nan, right=np.nan)
    bad = STATIC_MASK | (~np.isfinite(f_grid)) | (f_grid <= 0.0)
    f_clean = np.where(bad, np.nan, f_grid)

    f_dec = f_clean[DEC_IDX]
    ok_dec = np.isfinite(f_dec)
    f_dec_fill = np.interp(LAM_DEC, LAM_DEC[ok_dec], f_dec[ok_dec]) if np.any(ok_dec) else np.ones_like(LAM_DEC)
    cont_dec = median_filter(f_dec_fill, size=21, mode="nearest")
    cont_full = np.interp(LAM, LAM_DEC, cont_dec)
    norm = np.where((~bad) & (cont_full > 0), f_clean / np.maximum(cont_full, 1e-6), np.nan)
    return norm.astype(np.float32), raw_med


def detect_peaks(z_mf: np.ndarray, thresh: float = 10.0, min_sep: int = 50) -> list[int]:
    """Non-maximum suppressed local peaks above threshold."""
    cand = np.flatnonzero(z_mf >= thresh)
    if cand.size == 0:
        return []
    order = cand[np.argsort(z_mf[cand])[::-1]]
    kept: list[int] = []
    taken = np.zeros(z_mf.size, dtype=bool)
    for idx in order:
        if taken[idx]:
            continue
        i0 = max(0, int(idx) - min_sep)
        i1 = min(z_mf.size, int(idx) + min_sep + 1)
        taken[i0:i1] = True
        kept.append(int(idx))
    return kept


def compute_beamed_10sig_power_kw(dist_pc: float, vmag: float, sigma_med: float) -> float:
    """10-sigma monochromatic beamed laser power (D_tx = 10 m, 5500 A)."""
    lam_m = 5500e-10
    d_tx = 10.0
    theta = 1.22 * lam_m / d_tx
    omega = math.pi * (theta / 2.0) ** 2
    d_m = dist_pc * 3.0856775814913673e16
    f_lam0 = 3.631e-11  # W / m^2 / A at V = 0
    f_lam = f_lam0 * (10.0 ** (-0.4 * vmag))
    spx = psf_sigma_px(5500.0)
    dlam_eff = math.sqrt(2.0 * math.sqrt(math.pi) * spx) * DLAM
    f_laser = 10.0 * sigma_med * f_lam * dlam_eff
    p_w = f_laser * (d_m ** 2) * omega
    return p_w / 1000.0


def exact_bayes_bounds(n_eff: float) -> dict[str, float]:
    jf = float(sp_beta.ppf(0.95, 0.5, n_eff + 0.5)) * 100.0
    un = float(sp_beta.ppf(0.95, 1.0, n_eff + 1.0)) * 100.0
    return {"n_eff": round(n_eff, 4), "jeffreys_f95_pct": round(jf, 4), "uniform_f95_pct": round(un, 4)}


def main() -> int:
    t0 = time.time()
    RES.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261128)

    epoch_rows: list[dict[str, str]] = []
    with (INP / "n11b_harps_epochs.csv").open("r", encoding="utf-8", newline="") as fh:
        epoch_rows = list(csv.DictReader(fh))
    by_star: dict[str, list[dict[str, str]]] = {k: [] for k in TARGET_META}
    for r in epoch_rows:
        by_star[r["star"]].append(r)

    star_summary: list[dict[str, object]] = []
    peak_diags: list[dict[str, object]] = []
    stage2_triggers: list[dict[str, object]] = []
    inj_rows: list[dict[str, object]] = []
    cutout_arrays: dict[str, np.ndarray] = {}

    stars_order = list(TARGET_META.keys())
    for star in stars_order:
        rows = sorted(by_star[star], key=lambda x: float(x["mjd_obs"]))
        assert len(rows) == 20, f"{star}: expected 20 epochs, got {len(rows)}"
        n_ep = len(rows)
        cube = np.empty((n_ep, LAM.size), dtype=np.float32)
        for ei, er in enumerate(rows):
            norm, _ = load_and_normalize_spectrum(ROOT / er["local_path"])
            cube[ei] = norm

        finite_cnt = np.sum(np.isfinite(cube), axis=0)
        valid_px = (~STATIC_MASK) & (finite_cnt >= 16)
        T_all = np.ones(LAM.size, dtype=np.float32)
        sigma_pix = np.ones(LAM.size, dtype=np.float32)
        if np.any(valid_px):
            T_all[valid_px] = np.nanmedian(cube[:, valid_px], axis=0)
            sigma_pix[valid_px] = 1.4826 * np.nanmedian(np.abs(cube[:, valid_px] - T_all[None, valid_px]), axis=0)
        cube_fill = np.where(valid_px[None, :] & np.isfinite(cube), cube, T_all[None, :])

        # Fast exact 19-epoch LOEO median via sorted cube
        S = np.sort(cube_fill, axis=0)
        T_loeo = np.where(cube_fill <= S[9:10, :], S[10:11, :], S[9:10, :])
        res_cube = cube_fill - T_loeo

        # Local MAD noise scale & matched filter Z_mf per epoch
        sigma_tot_cube = np.empty_like(res_cube)
        z_pix_cube = np.empty_like(res_cube)
        z_mf_cube = np.empty_like(res_cube)

        dec_valid = valid_px[DEC_IDX]
        for ei in range(n_ep):
            med_abs_ei = float(np.median(np.abs(res_cube[ei, valid_px]))) if np.any(valid_px) else 1e-3
            abs_dec = np.where(dec_valid, np.abs(res_cube[ei, DEC_IDX]), med_abs_ei)
            sig_loc_dec = 1.4826 * median_filter(abs_dec, size=21, mode="nearest")
            sig_loc = np.interp(LAM, LAM_DEC, sig_loc_dec)
            sig_tot = np.maximum.reduce([sig_loc, sigma_pix, np.full_like(LAM, 5e-4)])
            sigma_tot_cube[ei] = sig_tot
            zp = np.where(valid_px, res_cube[ei] / sig_tot, 0.0)
            z_pix_cube[ei] = zp
            z_mf_cube[ei] = matched_filter_z(zp, valid_px)

        # Save TiO-forest validation cutout for first star (Proxima Cen) around 6150-6190 A
        if star == "PROXIMACEN":
            c_idx = np.flatnonzero((LAM >= 6155.0) & (LAM <= 6180.0))
            cutout_arrays["TIO_LAM"] = LAM[c_idx]
            cutout_arrays["TIO_EP0_NORM"] = cube_fill[0, c_idx]
            cutout_arrays["TIO_TEMPLATE"] = T_loeo[0, c_idx]
            cutout_arrays["TIO_RESIDUAL"] = res_cube[0, c_idx]

        # Stage 2 peak scan across all 20 epochs
        n_peaks_z10 = 0
        n_ep_triggers = 0
        for ei, er in enumerate(rows):
            z_mf = z_mf_cube[ei]
            z_pix = z_pix_cube[ei]
            peaks = detect_peaks(z_mf, thresh=10.0, min_sep=50)
            for idx in peaks:
                if idx < CUT_HALF or idx >= LAM.size - CUT_HALF:
                    continue
                lam_a = float(LAM[idx])
                z_val = float(z_mf[idx])
                n_peaks_z10 += 1

                # Cross-epoch persistence count in ±0.05 A (±5 px)
                w0, w1 = max(0, idx - 5), min(LAM.size, idx + 6)
                ep_max = np.max(z_mf_cube[:, w0:w1], axis=1)
                n_ep_gt5 = int(np.sum(ep_max >= 5.0))

                sh = fit_cutout_shape(z_pix[idx - CUT_HALF : idx + CUT_HALF + 1], lam_a)
                is_transient = n_ep_gt5 <= 3
                is_psf = (
                    sh["n_pix_gt3"] >= 3
                    and 0.80 <= sh["fwhm_ratio"] <= 1.50
                    and sh["r_gauss"] >= 0.88
                    and sh["min_neg_ratio"] > -0.45
                )
                veto_cat = (
                    "T1_TRANSIENT_LASER_PASS"
                    if (is_transient and is_psf)
                    else ("PERSISTENT_N_GT_3" if not is_transient else ("SHARP_COSMIC_RAY" if sh["fwhm_ratio"] < 0.80 or sh["n_pix_gt3"] < 3 else ("BROAD_OR_DISTORTED" if sh["fwhm_ratio"] > 1.50 or sh["r_gauss"] < 0.88 else "NEGATIVE_DEFECT")))
                )
                diag_row = {
                    "star": star,
                    "epoch_idx": ei,
                    "dp_id": er["dp_id"],
                    "mjd_obs": er["mjd_obs"],
                    "berv_kms": er["berv_kms"],
                    "lam_bary_a": round(lam_a, 4),
                    "z_mf": round(z_val, 3),
                    "n_epochs_gt5": n_ep_gt5,
                    "fit_sigma_px": sh["fit_sigma_px"],
                    "psf_sigma_px": sh["psf_sigma_px"],
                    "fwhm_ratio": sh["fwhm_ratio"],
                    "r_gauss": sh["r_gauss"],
                    "n_pix_gt3": int(sh["n_pix_gt3"]),
                    "min_neg_ratio": sh["min_neg_ratio"],
                    "stage2_status": veto_cat,
                }
                peak_diags.append(diag_row)
                if veto_cat == "T1_TRANSIENT_LASER_PASS":
                    n_ep_triggers += 1
                    stage2_triggers.append(diag_row)

        # Head-to-head real-noise 1,200-trial benchmark: 50 trials x 3 classes x 8 stars = 150 trials/star
        safe_mask = valid_px.copy()
        safe_mask[:300] = False
        safe_mask[-300:] = False
        gap_buf = (LAM >= 5294.0) & (LAM <= 5349.0)
        safe_mask[gap_buf] = False
        safe_indices = np.flatnonzero(safe_mask)

        for cls_name in ("TRANSIENT_PSF_LASER", "COSMIC_RAY_1_2PX", "BROAD_STELLAR_FLARE"):
            for tr in range(50):
                ok_seg = False
                for _retry in range(25):
                    ci = int(rng.choice(safe_indices))
                    ei = int(rng.integers(0, n_ep))
                    s_win = z_mf_cube[:, ci - 15 : ci + 16]
                    if np.max(np.abs(s_win)) < 6.0:
                        ok_seg = True
                        break
                if not ok_seg:
                    ci = int(rng.choice(safe_indices))
                    ei = int(rng.integers(0, n_ep))

                w0, w1 = ci - 200, ci + 201
                lam_sub = LAM[w0:w1]
                lam0 = float(LAM[ci])
                sig_p = psf_sigma_px(lam0)
                seg_cube = cube_fill[:, w0:w1].copy()
                sig_seg = sigma_tot_cube[ei, w0:w1]

                dx = np.arange(-200, 201, dtype=np.float64) - float(rng.uniform(-0.45, 0.45))
                if cls_name == "TRANSIENT_PSF_LASER":
                    s_inj = sig_p * float(rng.uniform(0.88, 1.12))
                    prof = np.exp(-0.5 * (dx / s_inj) ** 2)
                    z_tgt = float(rng.uniform(12.0, 40.0))
                elif cls_name == "COSMIC_RAY_1_2PX":
                    s_inj = float(rng.uniform(0.28, 0.52))
                    prof = np.exp(-0.5 * (dx / s_inj) ** 2)
                    z_tgt = float(rng.uniform(16.0, 45.0))
                else:
                    s_inj = sig_p * float(rng.uniform(2.6, 5.5))
                    prof = np.exp(-0.5 * (dx / s_inj) ** 2)
                    z_tgt = float(rng.uniform(14.0, 40.0))

                # Calibrate injected amplitude to produce target Z_mf in sig_seg noise
                prof_unit = prof / math.sqrt(float(np.sum(gaussian_filter1d(prof, sigma=sig_p) ** 2)) * (2.0 * math.sqrt(math.pi) * sig_p))
                # Use analytical PSF projection gain for clean SNR scaling
                kern = np.exp(-0.5 * (dx / sig_p) ** 2)
                kern /= math.sqrt(float(np.sum(kern * kern)))
                gain = float(np.sum(prof * kern))
                amp_zpix = z_tgt / max(gain, 1e-4)
                inj_flux = amp_zpix * float(sig_seg[200]) * prof
                med_clean = np.median(seg_cube, axis=0)
                seg_cube[ei] += inj_flux.astype(np.float32)

                # Classical comparator: static 20-epoch median stack vs clean stellar template (blinds single-epoch transients!)
                med_stack = np.median(seg_cube, axis=0)
                z_stack_pix = (med_stack - med_clean) / np.maximum(sig_seg, 5e-4)
                z_stack_mf = gaussian_filter1d(z_stack_pix, sigma=sig_p) * math.sqrt(2.0 * math.sqrt(math.pi) * sig_p)
                cls_det = 1 if float(np.max(z_stack_mf[185:216])) >= 10.0 else 0

                # N11B detector: 19-epoch LOEO median + PSF matched filter + shape + transience
                others = np.delete(seg_cube, ei, axis=0)
                t_other = np.median(others, axis=0)
                res_ep = seg_cube[ei] - t_other
                zp = res_ep / sig_seg
                z_mf_loc = gaussian_filter1d(zp, sigma=sig_p) * math.sqrt(2.0 * math.sqrt(math.pi) * sig_p)
                pk_loc = int(np.argmax(z_mf_loc[185:216])) + 185
                z_mf_peak = float(z_mf_loc[pk_loc])

                # Cross-epoch persistence in local cube
                z_all_loc = (seg_cube - t_other[None, :]) / np.maximum(sigma_tot_cube[:, w0:w1], 5e-4)
                n_gt5_loc = int(np.sum(np.max(gaussian_filter1d(z_all_loc, sigma=sig_p, axis=1)[:, pk_loc - 5 : pk_loc + 6], axis=1) * math.sqrt(2.0 * math.sqrt(math.pi) * sig_p) >= 5.0))

                sh_loc = fit_cutout_shape(zp[pk_loc - CUT_HALF : pk_loc + CUT_HALF + 1], float(lam_sub[pk_loc]))
                n11b_det = int(
                    z_mf_peak >= 10.0
                    and n_gt5_loc <= 3
                    and sh_loc["n_pix_gt3"] >= 3
                    and 0.80 <= sh_loc["fwhm_ratio"] <= 1.50
                    and sh_loc["r_gauss"] >= 0.88
                    and sh_loc["min_neg_ratio"] > -0.45
                )

                # Save representative injection cutouts for Fig 02/03 on Proxima Cen first trial
                if star == "PROXIMACEN" and tr == 0:
                    cutout_arrays[f"INJ_{cls_name}_RESZ"] = zp[pk_loc - 25 : pk_loc + 26]
                    cutout_arrays[f"INJ_{cls_name}_ZMF"] = z_mf_loc[pk_loc - 25 : pk_loc + 26]
                    cutout_arrays[f"INJ_{cls_name}_STACKZ"] = z_stack_mf[pk_loc - 25 : pk_loc + 26]

                inj_rows.append({
                    "star": star,
                    "morphology": cls_name,
                    "trial": tr,
                    "lam_a": round(lam0, 3),
                    "z_mf": round(z_mf_peak, 2),
                    "fwhm_ratio": sh_loc["fwhm_ratio"],
                    "r_gauss": sh_loc["r_gauss"],
                    "n_pix_gt3": int(sh_loc["n_pix_gt3"]),
                    "n11b_det": n11b_det,
                    "classical_stack_det": cls_det,
                })

        meta = TARGET_META[star]
        bervs = [float(r["berv_kms"]) for r in rows if r["berv_kms"] != ""]
        mjds = [float(r["mjd_obs"]) for r in rows]
        snrs = [float(r["snr_hdr"]) for r in rows]
        med_sigma = float(np.median(sigma_tot_cube[:, valid_px]))
        p_10sig_kw = compute_beamed_10sig_power_kw(float(meta["dist_pc"]), float(meta["vmag"]), med_sigma)
        star_summary.append({
            "star": star,
            "common_name": meta["common"],
            "dist_pc": meta["dist_pc"],
            "n_exoplanets": meta["n_pl"],
            "vmag": meta["vmag"],
            "epochs": n_ep,
            "mjd_span_days": round(max(mjds) - min(mjds), 1),
            "berv_span_kms": round(max(bervs) - min(bervs), 2) if bervs else 0.0,
            "median_snr_hdr": round(float(np.median(snrs)), 1),
            "median_sigma_frac": round(med_sigma, 5),
            "p_tx_10sig_kw": round(p_10sig_kw, 5),
            "peaks_z10_before_veto": n_peaks_z10,
            "stage2_t1_triggers": n_ep_triggers,
        })
        print(f"[N11B Stage 2] {star}: 20 epochs, ΔBERV={star_summary[-1]['berv_span_kms']} km/s, P10σ={p_10sig_kw:.4f} kW, Z>=10 peaks={n_peaks_z10}, T1 triggers={n_ep_triggers}")

    # Save CSV outputs
    def write_csv(path: Path, rows_out: list[dict[str, object]], cols: list[str]) -> None:
        with path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows_out)

    write_csv(
        RES / "N11B_STAR_SUMMARY.csv",
        star_summary,
        ["star", "common_name", "dist_pc", "n_exoplanets", "vmag", "epochs", "mjd_span_days", "berv_span_kms", "median_snr_hdr", "median_sigma_frac", "p_tx_10sig_kw", "peaks_z10_before_veto", "stage2_t1_triggers"],
    )
    diag_cols = ["star", "epoch_idx", "dp_id", "mjd_obs", "berv_kms", "lam_bary_a", "z_mf", "n_epochs_gt5", "fit_sigma_px", "psf_sigma_px", "fwhm_ratio", "r_gauss", "n_pix_gt3", "min_neg_ratio", "stage2_status"]
    write_csv(RES / "N11B_PEAK_DIAGNOSTICS.csv", peak_diags, diag_cols)
    write_csv(RES / "N11B_STAGE2_TRIGGERS.csv", stage2_triggers, diag_cols)
    write_csv(
        RES / "N11B_INJECTION_BENCHMARK.csv",
        inj_rows,
        ["star", "morphology", "trial", "lam_a", "z_mf", "fwhm_ratio", "r_gauss", "n_pix_gt3", "n11b_det", "classical_stack_det"],
    )
    np.savez_compressed(RES / "n11b_cutouts.npz", **cutout_arrays)

    # Injection summary & Bayesian bounds
    by_cls: dict[str, dict[str, float]] = {}
    for cls_name in ("TRANSIENT_PSF_LASER", "COSMIC_RAY_1_2PX", "BROAD_STELLAR_FLARE"):
        sub = [r for r in inj_rows if r["morphology"] == cls_name]
        n11b_r = sum(int(r["n11b_det"]) for r in sub) / len(sub)
        cls_r = sum(int(r["classical_stack_det"]) for r in sub) / len(sub)
        by_cls[cls_name] = {
            "trials": len(sub),
            "n11b_positive": sum(int(r["n11b_det"]) for r in sub),
            "n11b_rate": round(n11b_r, 4),
            "classical_stack_positive": sum(int(r["classical_stack_det"]) for r in sub),
            "classical_stack_rate": round(cls_r, 4),
        }

    laser_eff = by_cls["TRANSIENT_PSF_LASER"]["n11b_rate"]
    med_p_kw = float(np.median([float(r["p_tx_10sig_kw"]) for r in star_summary]))
    summary = {
        "campaign": "SPOR_N11B_HARPS_SINGLE_EPOCH_TRANSIENT_LASER",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "elapsed_s": round(time.time() - t0, 2),
        "stars_analyzed": len(star_summary),
        "epochs_analyzed": 160,
        "wavelength_band_a": [4800.0, 6900.0],
        "spectral_resolution_r": HARPS_R,
        "median_p_tx_10sig_kw": round(med_p_kw, 5),
        "min_p_tx_10sig_kw": round(min(float(r["p_tx_10sig_kw"]) for r in star_summary), 5),
        "max_p_tx_10sig_kw": round(max(float(r["p_tx_10sig_kw"]) for r in star_summary), 5),
        "peaks_z10_before_shape_veto": len(peak_diags),
        "stage2_t1_triggers_total": len(stage2_triggers),
        "injections": {
            "trials_total": len(inj_rows),
            "laser_completeness": by_cls["TRANSIENT_PSF_LASER"]["n11b_rate"],
            "classical_median_stack_completeness": by_cls["TRANSIENT_PSF_LASER"]["classical_stack_rate"],
            "cosmic_ray_fpr": by_cls["COSMIC_RAY_1_2PX"]["n11b_rate"],
            "broad_flare_fpr": by_cls["BROAD_STELLAR_FLARE"]["n11b_rate"],
            "per_morphology": by_cls,
        },
        "provisional_zero_eti_bayesian_bounds": {
            "stars_raw_8": exact_bayes_bounds(8.0),
            "stars_eff": exact_bayes_bounds(8.0 * laser_eff),
            "epochs_raw_160": exact_bayes_bounds(160.0),
            "epochs_eff": exact_bayes_bounds(160.0 * laser_eff),
        },
        "external_contacts": 0,
    }
    (RES / "N11B_ANALYZER_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"[N11B Stage 2 Complete] elapsed={summary['elapsed_s']}s, Z>=10 peaks={len(peak_diags)}, T1 triggers={len(stage2_triggers)}, Laser={laser_eff*100:.2f}% (CR FPR={summary['injections']['cosmic_ray_fpr']*100:.2f}%, Flare FPR={summary['injections']['broad_flare_fpr']*100:.2f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
