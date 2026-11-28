#!/usr/bin/env python3
"""Prospective Blind-Locked Analyzer for Spor N12: Scaled 24-Star (32 Unified) HARPS Single-Epoch Transient Laser (T1) & Multi-Line Sub-Threshold Optical Comb (T2)."""
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
WS = ROOT / "analysis_workspace/work_n12_20261128_scaled_harps_transient_laser_comb"
INP = ROOT / "inputs_n12_20261128"
RES = WS / "results"
N11B_SUM = ROOT / "analysis_workspace/work_n11b_20261128_harps_single_epoch_transient_laser/results/N11B_ANALYZER_SUMMARY.json"

TARGET_META = {
    "EPSERI": {"common": "eps Eri", "dist_pc": 3.2026, "n_pl": 1, "vmag": 3.72, "sp": "K2V"},
    "HD217987": {"common": "Lacaille 9352", "dist_pc": 3.2868, "n_pl": 4, "vmag": 7.56, "sp": "M1V"},
    "TAUCET": {"common": "tau Cet", "dist_pc": 3.6030, "n_pl": 3, "vmag": 3.50, "sp": "G8.5V"},
    "HD209100": {"common": "eps Ind A", "dist_pc": 3.6386, "n_pl": 1, "vmag": 4.69, "sp": "K5V"},
    "GJ191": {"common": "Kapteyn's Star", "dist_pc": 3.9331, "n_pl": 1, "vmag": 8.86, "sp": "M2.0V"},
    "WOLF1061": {"common": "Wolf 1061", "dist_pc": 4.3059, "n_pl": 3, "vmag": 10.10, "sp": "M3.5V"},
    "GJ9066": {"common": "GJ 9066", "dist_pc": 4.4710, "n_pl": 1, "vmag": 12.71, "sp": "M5.0V"},
    "GJ674": {"common": "GJ 674", "dist_pc": 4.5490, "n_pl": 1, "vmag": 9.38, "sp": "M2.5V"},
    "GJ876": {"common": "GJ 876", "dist_pc": 4.6752, "n_pl": 4, "vmag": 10.16, "sp": "M2.5V"},
    "GJ832": {"common": "GJ 832", "dist_pc": 4.9644, "n_pl": 1, "vmag": 8.66, "sp": "M2V"},
    "GJ682": {"common": "GJ 682", "dist_pc": 5.0067, "n_pl": 2, "vmag": 10.94, "sp": "M3.5V"},
    "GJ3323": {"common": "GJ 3323", "dist_pc": 5.3748, "n_pl": 2, "vmag": 12.57, "sp": "M4V"},
    "HD42581": {"common": "GJ 229 A", "dist_pc": 5.7562, "n_pl": 2, "vmag": 8.15, "sp": "M1.5V"},
    "GJ752A": {"common": "Wolf 1055", "dist_pc": 5.9106, "n_pl": 1, "vmag": 9.12, "sp": "M2.5V"},
    "HD20794": {"common": "82 G. Eridani", "dist_pc": 6.0028, "n_pl": 4, "vmag": 4.26, "sp": "G8V"},
    "GJ581": {"common": "GJ 581", "dist_pc": 6.2981, "n_pl": 3, "vmag": 10.57, "sp": "M3.0V"},
    "LTT1445A": {"common": "LTT 1445 A", "dist_pc": 6.8693, "n_pl": 2, "vmag": 10.59, "sp": "M3.0V"},
    "GJ393": {"common": "GJ 393", "dist_pc": 7.0315, "n_pl": 1, "vmag": 9.65, "sp": "M2.0V"},
    "GJ514": {"common": "GJ 514", "dist_pc": 7.6178, "n_pl": 1, "vmag": 9.05, "sp": "M1.0V"},
    "HD115617": {"common": "61 Virginis", "dist_pc": 8.5033, "n_pl": 3, "vmag": 4.70, "sp": "G5V"},
    "GJ849": {"common": "GJ 849", "dist_pc": 8.8006, "n_pl": 2, "vmag": 10.41, "sp": "M3.5V"},
    "HD192310": {"common": "HD 192310", "dist_pc": 8.7969, "n_pl": 2, "vmag": 5.73, "sp": "K3V"},
    "GJ433": {"common": "GJ 433", "dist_pc": 9.0646, "n_pl": 3, "vmag": 9.81, "sp": "M2V"},
    "GJ367": {"common": "GJ 367", "dist_pc": 9.4126, "n_pl": 3, "vmag": 10.15, "sp": "M1.0V"},
}

LAM = np.linspace(4800.00, 6900.00, 210001, dtype=np.float64)
DLAM = 0.01
HARPS_R = 115000.0
DEC_IDX = np.arange(0, LAM.size, 10, dtype=np.int32)
LAM_DEC = LAM[DEC_IDX]

STATIC_MASK = ((LAM >= 5299.5) & (LAM <= 5343.5)) | (LAM < 4801.0) | (LAM > 6899.0)
SKY_TELLURIC_MASK = (
    ((LAM >= 5576.0) & (LAM <= 5578.5))
    | ((LAM >= 5875.0) & (LAM <= 5965.0))
    | ((LAM >= 6270.0) & (LAM <= 6370.0))
    | ((LAM >= 6465.0) & (LAM <= 6600.0))
    | ((LAM >= 6845.0) & (LAM <= 6900.0))
)
BANDS = [
    ("GREEN", 4800.0, 5850.0, 5325.0 / HARPS_R / (2.35482 * DLAM)),
    ("RED", 5850.0, 6900.0, 6375.0 / HARPS_R / (2.35482 * DLAM)),
]

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
    n_pix_gt2 = int(np.sum(center_win >= 2.0))
    peak_z = float(np.max(center_win))
    min_neg_ratio = float(np.min(z_cut[CUT_HALF - 10 : CUT_HALF + 11])) / max(peak_z, 1e-6)
    return {
        "fit_sigma_px": round(best_s, 3),
        "psf_sigma_px": round(sig_psf, 3),
        "fwhm_ratio": round(fwhm_ratio, 3),
        "r_gauss": round(best_r, 4),
        "n_pix_gt3": float(n_pix_gt3),
        "n_pix_gt2": float(n_pix_gt2),
        "min_neg_ratio": round(min_neg_ratio, 3),
    }


def matched_filter_z(z_pix: np.ndarray, valid: np.ndarray) -> np.ndarray:
    zp = np.where(valid, np.clip(z_pix, -25.0, 250.0), 0.0)
    out = np.zeros_like(zp)
    for _bname, l0, l1, spx in BANDS:
        conv = gaussian_filter1d(zp, sigma=spx, mode="constant", cval=0.0)
        conv *= math.sqrt(2.0 * math.sqrt(math.pi) * spx)
        bmask = (LAM >= l0) & (LAM <= l1) & valid
        if np.any(bmask):
            mad = 1.4826 * float(np.median(np.abs(conv[bmask])))
            out[bmask] = conv[bmask] / max(mad, 0.5)
    return out


def load_and_normalize_spectrum(path: Path) -> np.ndarray:
    with fits.open(path, memmap=False) as hdul:
        tab = hdul[1].data
        wave = np.asarray(tab["WAVE"], dtype=np.float64).ravel()
        flux = np.asarray(tab["FLUX"], dtype=np.float64).ravel()
    order = np.argsort(wave)
    wave = wave[order]
    flux = flux[order]
    f_grid = np.interp(LAM, wave, flux, left=np.nan, right=np.nan)
    bad = STATIC_MASK | (~np.isfinite(f_grid)) | (f_grid <= 0.0)
    f_clean = np.where(bad, np.nan, f_grid)

    f_dec = f_clean[DEC_IDX]
    ok_dec = np.isfinite(f_dec)
    f_dec_fill = np.interp(LAM_DEC, LAM_DEC[ok_dec], f_dec[ok_dec]) if np.any(ok_dec) else np.ones_like(LAM_DEC)
    cont_dec = median_filter(f_dec_fill, size=21, mode="nearest")
    cont_full = np.interp(LAM, LAM_DEC, cont_dec)
    norm = np.where((~bad) & (cont_full > 0), f_clean / np.maximum(cont_full, 1e-6), np.nan)
    return norm.astype(np.float32)


def detect_peaks(z_mf: np.ndarray, thresh: float = 10.0, min_sep: int = 50, mask: np.ndarray | None = None) -> list[int]:
    arr = np.where(mask, z_mf, -1e9) if mask is not None else z_mf
    cand = np.flatnonzero(arr >= thresh)
    if cand.size == 0:
        return []
    order = cand[np.argsort(arr[cand])[::-1]]
    kept: list[int] = []
    taken = np.zeros(arr.size, dtype=bool)
    for idx in order:
        if taken[idx]:
            continue
        i0 = max(0, int(idx) - min_sep)
        i1 = min(arr.size, int(idx) + min_sep + 1)
        taken[i0:i1] = True
        kept.append(int(idx))
    return kept


def compute_beamed_10sig_power_kw(dist_pc: float, vmag: float, sigma_med: float) -> float:
    lam_m = 5500e-10
    d_tx = 10.0
    omega = math.pi * (1.22 * lam_m / d_tx / 2.0) ** 2
    d_m = dist_pc * 3.0856775814913673e16
    f_lam = 3.631e-11 * (10.0 ** (-0.4 * vmag))
    spx = psf_sigma_px(5500.0)
    dlam_eff = math.sqrt(2.0 * math.sqrt(math.pi) * spx) * DLAM
    f_laser = 10.0 * sigma_med * f_lam * dlam_eff
    return (f_laser * (d_m ** 2) * omega) / 1000.0


def exact_bayes_bounds(n_eff: float) -> dict[str, float]:
    return {
        "n_eff": round(n_eff, 4),
        "jeffreys_f95_pct": round(float(sp_beta.ppf(0.95, 0.5, n_eff + 0.5)) * 100.0, 4),
        "uniform_f95_pct": round(float(sp_beta.ppf(0.95, 1.0, n_eff + 1.0)) * 100.0, 4),
    }


def main() -> int:
    t0 = time.time()
    RES.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(2026112812)

    with (INP / "n12_harps_epochs.csv").open("r", encoding="utf-8", newline="") as fh:
        epoch_rows = list(csv.DictReader(fh))
    by_star: dict[str, list[dict[str, str]]] = {k: [] for k in TARGET_META}
    for r in epoch_rows:
        by_star[r["star"]].append(r)

    star_summary: list[dict[str, object]] = []
    peak_diags: list[dict[str, object]] = []
    stage2_triggers: list[dict[str, object]] = []
    comb_triggers: list[dict[str, object]] = []
    inj_rows: list[dict[str, object]] = []
    cutout_arrays: dict[str, np.ndarray] = {}

    stars_order = list(TARGET_META.keys())
    for s_idx_star, star in enumerate(stars_order):
        rows = sorted(by_star[star], key=lambda x: float(x["mjd_obs"]))
        assert len(rows) == 20, f"{star}: expected 20 epochs, got {len(rows)}"
        n_ep = len(rows)
        cube = np.empty((n_ep, LAM.size), dtype=np.float32)
        for ei, er in enumerate(rows):
            cube[ei] = load_and_normalize_spectrum(ROOT / er["local_path"])

        finite_cnt = np.sum(np.isfinite(cube), axis=0)
        valid_px = (~STATIC_MASK) & (finite_cnt >= 16)
        T_all = np.ones(LAM.size, dtype=np.float32)
        sigma_pix = np.ones(LAM.size, dtype=np.float32)
        if np.any(valid_px):
            T_all[valid_px] = np.nanmedian(cube[:, valid_px], axis=0)
            sigma_pix[valid_px] = 1.4826 * np.nanmedian(np.abs(cube[:, valid_px] - T_all[None, valid_px]), axis=0)
        cube_fill = np.where(valid_px[None, :] & np.isfinite(cube), cube, T_all[None, :])

        S = np.sort(cube_fill, axis=0)
        T_loeo = np.where(cube_fill <= S[9:10, :], S[10:11, :], S[9:10, :])
        res_cube = cube_fill - T_loeo

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

        if star == "TAUCET":
            c_idx = np.flatnonzero((LAM >= 5165.0) & (LAM <= 5190.0))
            cutout_arrays["TAUCET_LAM"] = LAM[c_idx]
            cutout_arrays["TAUCET_EP0_NORM"] = cube_fill[0, c_idx]
            cutout_arrays["TAUCET_TEMPLATE"] = T_loeo[0, c_idx]
            cutout_arrays["TAUCET_RESIDUAL"] = res_cube[0, c_idx]
        elif star == "HD217987":
            c_idx = np.flatnonzero((LAM >= 6155.0) & (LAM <= 6180.0))
            cutout_arrays["GJ887_LAM"] = LAM[c_idx]
            cutout_arrays["GJ887_EP0_NORM"] = cube_fill[0, c_idx]
            cutout_arrays["GJ887_TEMPLATE"] = T_loeo[0, c_idx]
            cutout_arrays["GJ887_RESIDUAL"] = res_cube[0, c_idx]

        # Channel T1 & Channel T2 scans across 20 epochs
        n_peaks_z10 = 0
        n_t1 = 0
        n_t2 = 0
        comb_valid = valid_px & (~SKY_TELLURIC_MASK)
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
                w0, w1 = max(0, idx - 5), min(LAM.size, idx + 6)
                n_ep_gt5 = int(np.sum(np.max(z_mf_cube[:, w0:w1], axis=1) >= 5.0))
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
                drow = {
                    "star": star, "channel": "T1_SINGLE_LINE", "epoch_idx": ei, "dp_id": er["dp_id"],
                    "mjd_obs": er["mjd_obs"], "berv_kms": er["berv_kms"], "lam_bary_a": round(lam_a, 4),
                    "z_mf": round(z_val, 3), "n_epochs_gt5": n_ep_gt5, "fit_sigma_px": sh["fit_sigma_px"],
                    "psf_sigma_px": sh["psf_sigma_px"], "fwhm_ratio": sh["fwhm_ratio"],
                    "r_gauss": sh["r_gauss"], "n_pix_gt3": int(sh["n_pix_gt3"]),
                    "min_neg_ratio": sh["min_neg_ratio"], "stage2_status": veto_cat,
                }
                peak_diags.append(drow)
                if veto_cat == "T1_TRANSIENT_LASER_PASS":
                    n_t1 += 1
                    stage2_triggers.append(drow)

            # Channel T2: Multi-line sub-threshold comb (6.0 <= Z_mf < 10.0) on non-WAVE epochs
            if "WAVE" not in er.get("dpr_type", "").upper():
                sub_pks = [
                    i for i in detect_peaks(z_mf, thresh=6.0, min_sep=2500, mask=comb_valid)
                    if 6.0 <= float(z_mf[i]) < 10.0 and CUT_HALF <= i < LAM.size - CUT_HALF
                ]
                clean_teeth: list[tuple[float, float]] = []
                for idx in sub_pks:
                    w0, w1 = max(0, idx - 5), min(LAM.size, idx + 6)
                    if int(np.sum(np.max(z_mf_cube[:, w0:w1], axis=1) >= 4.0)) > 2:
                        continue
                    sh = fit_cutout_shape(z_pix[idx - CUT_HALF : idx + CUT_HALF + 1], float(LAM[idx]))
                    if sh["n_pix_gt2"] >= 3 and 0.65 <= sh["fwhm_ratio"] <= 1.75 and sh["r_gauss"] >= 0.80 and sh["min_neg_ratio"] > -0.75:
                        clean_teeth.append((float(LAM[idx]), float(z_mf[idx])))
                if len(clean_teeth) >= 5:
                    n_t2 += 1
                    teeth_str = ";".join(f"{l:.2f}@{z:.1f}" for l, z in clean_teeth[:8])
                    crow = {
                        "star": star, "channel": "T2_OPTICAL_COMB", "epoch_idx": ei, "dp_id": er["dp_id"],
                        "mjd_obs": er["mjd_obs"], "berv_kms": er["berv_kms"], "lam_bary_a": round(clean_teeth[0][0], 4),
                        "z_mf": round(float(np.mean([z for _, z in clean_teeth])), 3), "n_epochs_gt5": len(clean_teeth),
                        "fit_sigma_px": 0.0, "psf_sigma_px": 0.0, "fwhm_ratio": 1.0, "r_gauss": 0.95,
                        "n_pix_gt3": len(clean_teeth), "min_neg_ratio": 0.0, "stage2_status": "T2_OPTICAL_COMB_PASS",
                        "comb_teeth": teeth_str,
                    }
                    comb_triggers.append(crow)

        # Head-to-head real-noise 1,200-trial benchmark (exact counts across 24 stars: 50/star -> 400 T1, 400 T2 comb, 200 CR, 200 Flare)
        safe_mask = comb_valid.copy()
        safe_mask[:300] = False
        safe_mask[-300:] = False
        safe_mask[(LAM >= 5294.0) & (LAM <= 5349.0)] = False
        safe_indices = np.flatnonzero(safe_mask)

        n_t1_inj = 17 if s_idx_star < 16 else 16
        n_t2_inj = 17 if s_idx_star < 16 else 16
        n_cr_inj = 8 if s_idx_star < 16 else 9
        n_fl_inj = 8 if s_idx_star < 16 else 9

        def sample_clean_pos(ei_tgt: int) -> int:
            for _ in range(25):
                ci_c = int(rng.choice(safe_indices))
                if np.max(np.abs(z_mf_cube[:, ci_c - 15 : ci_c + 16])) < 5.0:
                    return ci_c
            return int(rng.choice(safe_indices))

        for cls_name, n_tr in (("TRANSIENT_PSF_LASER", n_t1_inj), ("COSMIC_RAY_1_2PX", n_cr_inj), ("BROAD_STELLAR_FLARE", n_fl_inj)):
            for tr in range(n_tr):
                ei = int(rng.integers(0, n_ep))
                ci = sample_clean_pos(ei)
                w0, w1 = ci - 200, ci + 201
                lam_sub = LAM[w0:w1]
                lam0 = float(LAM[ci])
                sig_p = psf_sigma_px(lam0)
                seg_cube = cube_fill[:, w0:w1].copy()
                sig_seg = sigma_tot_cube[ei, w0:w1]
                dx = np.arange(-200, 201, dtype=np.float64) - float(rng.uniform(-0.45, 0.45))
                if cls_name == "TRANSIENT_PSF_LASER":
                    s_inj, z_tgt = sig_p * float(rng.uniform(0.88, 1.12)), float(rng.uniform(12.0, 40.0))
                elif cls_name == "COSMIC_RAY_1_2PX":
                    s_inj, z_tgt = float(rng.uniform(0.28, 0.52)), float(rng.uniform(16.0, 45.0))
                else:
                    s_inj, z_tgt = sig_p * float(rng.uniform(2.6, 5.5)), float(rng.uniform(14.0, 40.0))
                prof = np.exp(-0.5 * (dx / s_inj) ** 2)
                kern = np.exp(-0.5 * (dx / sig_p) ** 2)
                kern /= math.sqrt(float(np.sum(kern * kern)))
                amp_zpix = z_tgt / max(float(np.sum(prof * kern)), 1e-4)
                med_clean = np.median(seg_cube, axis=0)
                seg_cube[ei] += (amp_zpix * float(sig_seg[200]) * prof).astype(np.float32)
                med_stack = np.median(seg_cube, axis=0)
                z_stack_mf = gaussian_filter1d((med_stack - med_clean) / np.maximum(sig_seg, 5e-4), sigma=sig_p) * math.sqrt(2.0 * math.sqrt(math.pi) * sig_p)
                cls_det = 1 if float(np.max(z_stack_mf[185:216])) >= 10.0 else 0

                t_other = np.median(np.delete(seg_cube, ei, axis=0), axis=0)
                zp = (seg_cube[ei] - t_other) / sig_seg
                z_mf_loc = gaussian_filter1d(zp, sigma=sig_p) * math.sqrt(2.0 * math.sqrt(math.pi) * sig_p)
                pk_loc = int(np.argmax(z_mf_loc[185:216])) + 185
                z_mf_peak = float(z_mf_loc[pk_loc])
                z_all_loc = (seg_cube - t_other[None, :]) / np.maximum(sigma_tot_cube[:, w0:w1], 5e-4)
                n_gt5_loc = int(np.sum(np.max(gaussian_filter1d(z_all_loc, sigma=sig_p, axis=1)[:, pk_loc - 5 : pk_loc + 6], axis=1) * math.sqrt(2.0 * math.sqrt(math.pi) * sig_p) >= 5.0))
                sh_loc = fit_cutout_shape(zp[pk_loc - CUT_HALF : pk_loc + CUT_HALF + 1], float(lam_sub[pk_loc]))
                n12_det = int(z_mf_peak >= 10.0 and n_gt5_loc <= 3 and sh_loc["n_pix_gt3"] >= 3 and 0.80 <= sh_loc["fwhm_ratio"] <= 1.50 and sh_loc["r_gauss"] >= 0.88 and sh_loc["min_neg_ratio"] > -0.45)

                if star == "TAUCET" and tr == 0:
                    cutout_arrays[f"INJ_{cls_name}_RESZ"] = zp[pk_loc - 25 : pk_loc + 26]
                    cutout_arrays[f"INJ_{cls_name}_ZMF"] = z_mf_loc[pk_loc - 25 : pk_loc + 26]
                    cutout_arrays[f"INJ_{cls_name}_STACKZ"] = z_stack_mf[pk_loc - 25 : pk_loc + 26]

                inj_rows.append({"star": star, "morphology": cls_name, "trial": tr, "lam_a": round(lam0, 3), "z_mf": round(z_mf_peak, 2), "n12_det": n12_det, "classical_stack_det": cls_det})

        # Sub-threshold 8-tooth optical comb benchmark (T2): 8 teeth >= 25 A apart @ Z = 7.0-9.0 in 1 random epoch
        for tr in range(n_t2_inj):
            ei = int(rng.integers(0, n_ep))
            teeth_pos: list[int] = []
            for _att in range(120):
                ci_c = sample_clean_pos(ei)
                if all(abs(ci_c - p) >= 2600 for p in teeth_pos):
                    teeth_pos.append(ci_c)
                    if len(teeth_pos) == 8:
                        break
            clean_teeth_det = 0
            cls_stack_det = 0
            tooth_z_list: list[float] = []
            for ci in teeth_pos:
                w0, w1 = ci - 200, ci + 201
                lam_sub = LAM[w0:w1]
                lam0 = float(LAM[ci])
                sig_p = psf_sigma_px(lam0)
                seg_cube = cube_fill[:, w0:w1].copy()
                sig_seg = sigma_tot_cube[ei, w0:w1]
                dx = np.arange(-200, 201, dtype=np.float64) - float(rng.uniform(-0.45, 0.45))
                s_inj = sig_p * float(rng.uniform(0.90, 1.10))
                z_tgt = float(rng.uniform(7.0, 9.0))
                prof = np.exp(-0.5 * (dx / s_inj) ** 2)
                kern = np.exp(-0.5 * (dx / sig_p) ** 2)
                kern /= math.sqrt(float(np.sum(kern * kern)))
                amp_zpix = z_tgt / max(float(np.sum(prof * kern)), 1e-4)
                med_clean = np.median(seg_cube, axis=0)
                seg_cube[ei] += (amp_zpix * float(sig_seg[200]) * prof).astype(np.float32)
                med_stack = np.median(seg_cube, axis=0)
                z_stack_mf = gaussian_filter1d((med_stack - med_clean) / np.maximum(sig_seg, 5e-4), sigma=sig_p) * math.sqrt(2.0 * math.sqrt(math.pi) * sig_p)
                if float(np.max(z_stack_mf[185:216])) >= 10.0:
                    cls_stack_det = 1
                t_other = np.median(np.delete(seg_cube, ei, axis=0), axis=0)
                zp = (seg_cube[ei] - t_other) / sig_seg
                z_mf_loc = gaussian_filter1d(zp, sigma=sig_p) * math.sqrt(2.0 * math.sqrt(math.pi) * sig_p)
                pk_loc = int(np.argmax(z_mf_loc[185:216])) + 185
                z_mf_peak = float(z_mf_loc[pk_loc])
                tooth_z_list.append(z_mf_peak)
                z_all_loc = (seg_cube - t_other[None, :]) / np.maximum(sigma_tot_cube[:, w0:w1], 5e-4)
                n_gt4_loc = int(np.sum(np.max(gaussian_filter1d(z_all_loc, sigma=sig_p, axis=1)[:, pk_loc - 5 : pk_loc + 6], axis=1) * math.sqrt(2.0 * math.sqrt(math.pi) * sig_p) >= 4.0))
                sh_loc = fit_cutout_shape(zp[pk_loc - CUT_HALF : pk_loc + CUT_HALF + 1], float(lam_sub[pk_loc]))
                if z_mf_peak >= 6.0 and n_gt4_loc <= 2 and sh_loc["n_pix_gt2"] >= 3 and 0.65 <= sh_loc["fwhm_ratio"] <= 1.75 and sh_loc["r_gauss"] >= 0.80 and sh_loc["min_neg_ratio"] > -0.75:
                    clean_teeth_det += 1
                    if star == "TAUCET" and tr == 0 and clean_teeth_det == 1:
                        cutout_arrays["INJ_SUBTHRESHOLD_COMB_RESZ"] = zp[pk_loc - 25 : pk_loc + 26]
                        cutout_arrays["INJ_SUBTHRESHOLD_COMB_ZMF"] = z_mf_loc[pk_loc - 25 : pk_loc + 26]
                        cutout_arrays["INJ_SUBTHRESHOLD_COMB_STACKZ"] = z_stack_mf[pk_loc - 25 : pk_loc + 26]

            n12_t2_det = 1 if clean_teeth_det >= 5 else 0
            inj_rows.append({"star": star, "morphology": "SUBTHRESHOLD_OPTICAL_COMB", "trial": tr, "lam_a": 5500.0, "z_mf": round(float(np.mean(tooth_z_list)), 2), "n12_det": n12_t2_det, "classical_stack_det": cls_stack_det})

        meta = TARGET_META[star]
        bervs = [float(r["berv_kms"]) for r in rows if r["berv_kms"] != ""]
        mjds = [float(r["mjd_obs"]) for r in rows]
        snrs = [float(r["snr_hdr"]) for r in rows]
        med_sigma = float(np.median(sigma_tot_cube[:, valid_px]))
        p_10sig_kw = compute_beamed_10sig_power_kw(float(meta["dist_pc"]), float(meta["vmag"]), med_sigma)
        star_summary.append({
            "star": star, "common_name": meta["common"], "sp_type": meta["sp"], "dist_pc": meta["dist_pc"],
            "n_exoplanets": meta["n_pl"], "vmag": meta["vmag"], "epochs": n_ep,
            "mjd_span_days": round(max(mjds) - min(mjds), 1), "berv_span_kms": round(max(bervs) - min(bervs), 2) if bervs else 0.0,
            "median_snr_hdr": round(float(np.median(snrs)), 1), "median_sigma_frac": round(med_sigma, 5),
            "p_tx_10sig_kw": round(p_10sig_kw, 5), "peaks_z10_before_veto": n_peaks_z10,
            "stage2_t1_triggers": n_t1, "stage2_t2_comb_triggers": n_t2,
        })
        print(f"[N12 Stage 2] {star:10s} ({meta['sp']:5s}): ΔBERV={star_summary[-1]['berv_span_kms']:5.1f} km/s, P10σ={p_10sig_kw:7.4f} kW, Z>=10={n_peaks_z10:3d}, T1={n_t1:2d}, T2_comb={n_t2}")

    def write_csv(path: Path, rows_out: list[dict[str, object]], cols: list[str]) -> None:
        with path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows_out)

    write_csv(RES / "N12_STAR_SUMMARY.csv", star_summary, ["star", "common_name", "sp_type", "dist_pc", "n_exoplanets", "vmag", "epochs", "mjd_span_days", "berv_span_kms", "median_snr_hdr", "median_sigma_frac", "p_tx_10sig_kw", "peaks_z10_before_veto", "stage2_t1_triggers", "stage2_t2_comb_triggers"])
    diag_cols = ["star", "channel", "epoch_idx", "dp_id", "mjd_obs", "berv_kms", "lam_bary_a", "z_mf", "n_epochs_gt5", "fit_sigma_px", "psf_sigma_px", "fwhm_ratio", "r_gauss", "n_pix_gt3", "min_neg_ratio", "stage2_status"]
    write_csv(RES / "N12_PEAK_DIAGNOSTICS.csv", peak_diags, diag_cols)
    all_trig = stage2_triggers + comb_triggers
    write_csv(RES / "N12_STAGE2_TRIGGERS.csv", all_trig, diag_cols + ["comb_teeth"])
    write_csv(RES / "N12_INJECTION_BENCHMARK.csv", inj_rows, ["star", "morphology", "trial", "lam_a", "z_mf", "n12_det", "classical_stack_det"])
    np.savez_compressed(RES / "n12_cutouts.npz", **cutout_arrays)

    by_cls: dict[str, dict[str, float]] = {}
    for cls_name in ("TRANSIENT_PSF_LASER", "SUBTHRESHOLD_OPTICAL_COMB", "COSMIC_RAY_1_2PX", "BROAD_STELLAR_FLARE"):
        sub = [r for r in inj_rows if r["morphology"] == cls_name]
        by_cls[cls_name] = {
            "trials": len(sub),
            "n12_positive": sum(int(r["n12_det"]) for r in sub),
            "n12_rate": round(sum(int(r["n12_det"]) for r in sub) / len(sub), 4),
            "classical_stack_positive": sum(int(r["classical_stack_det"]) for r in sub),
            "classical_stack_rate": round(sum(int(r["classical_stack_det"]) for r in sub) / len(sub), 4),
        }

    t1_eff = by_cls["TRANSIENT_PSF_LASER"]["n12_rate"]
    t2_eff = by_cls["SUBTHRESHOLD_OPTICAL_COMB"]["n12_rate"]
    n11b = json.loads(N11B_SUM.read_text(encoding="utf-8"))
    n11b_eff = float(n11b["injections"]["laser_completeness"])
    unified_stars_eff = 8.0 * n11b_eff + 24.0 * t1_eff
    unified_epochs_eff = 160.0 * n11b_eff + 480.0 * t1_eff

    summary = {
        "campaign": "SPOR_N12_SCALED_32STAR_HARPS_TRANSIENT_LASER_AND_COMB",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "elapsed_s": round(time.time() - t0, 2),
        "stars_analyzed": len(star_summary),
        "epochs_analyzed": 480,
        "unified_stars_total": 32,
        "unified_epochs_total": 640,
        "wavelength_band_a": [4800.0, 6900.0],
        "spectral_resolution_r": HARPS_R,
        "median_p_tx_10sig_kw": round(float(np.median([float(r["p_tx_10sig_kw"]) for r in star_summary])), 5),
        "min_p_tx_10sig_kw": round(min(float(r["p_tx_10sig_kw"]) for r in star_summary), 5),
        "max_p_tx_10sig_kw": round(max(float(r["p_tx_10sig_kw"]) for r in star_summary), 5),
        "peaks_z10_before_shape_veto": len(peak_diags),
        "stage2_t1_triggers_total": len(stage2_triggers),
        "stage2_t2_comb_triggers_total": len(comb_triggers),
        "stage2_triggers_total": len(all_trig),
        "injections": {
            "trials_total": len(inj_rows),
            "laser_completeness": t1_eff,
            "subthreshold_comb_completeness": t2_eff,
            "classical_median_stack_completeness": by_cls["TRANSIENT_PSF_LASER"]["classical_stack_rate"],
            "cosmic_ray_fpr": by_cls["COSMIC_RAY_1_2PX"]["n12_rate"],
            "broad_flare_fpr": by_cls["BROAD_STELLAR_FLARE"]["n12_rate"],
            "per_morphology": by_cls,
        },
        "provisional_zero_eti_bayesian_bounds": {
            "n12_stars_raw_24": exact_bayes_bounds(24.0),
            "n12_stars_eff": exact_bayes_bounds(24.0 * t1_eff),
            "n12_epochs_eff": exact_bayes_bounds(480.0 * t1_eff),
            "unified_32stars_raw": exact_bayes_bounds(32.0),
            "unified_32stars_eff": exact_bayes_bounds(unified_stars_eff),
            "unified_640epochs_raw": exact_bayes_bounds(640.0),
            "unified_640epochs_eff": exact_bayes_bounds(unified_epochs_eff),
        },
        "external_contacts": 0,
    }
    (RES / "N12_ANALYZER_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"[N12 Stage 2 Complete] elapsed={summary['elapsed_s']}s, Z>=10={len(peak_diags)}, T1={len(stage2_triggers)}, T2={len(comb_triggers)}, T1_eff={t1_eff*100:.2f}%, T2_eff={t2_eff*100:.2f}%, CR_FPR={summary['injections']['cosmic_ray_fpr']*100:.2f}%, Flare_FPR={summary['injections']['broad_flare_fpr']*100:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
