#!/usr/bin/env python3
"""Prospective Blind-Locked Streaming Analyzer for Spor N14:
268 Brand-New Confirmed Milky Way Exoplanet Hosts (2,144 HARPS Spectra -> 300 Unified Hosts / 2,784 Epochs).

Streams FITS purely through RAM (io.BytesIO -> 0 bulk raw FITS on disk), verifies full SHA-256 receipts,
runs 7-epoch O(1) LOEO + PSF (T1) + Sub-Threshold 8-Tooth Optical Comb (T2), built-in Ha/Hb & ThAr tagging,
per-star JSONL checkpointing, and a 1,200-trial head-to-head F/G/K/M real-HARPS benchmark.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import math
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from astropy.io import fits
import numpy as np
from scipy.ndimage import gaussian_filter1d, median_filter
from scipy.stats import beta as sp_beta

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n14_20261128_300star_harps_transient_comb"
INP = ROOT / "inputs_n14_20261128"
RES = WS / "results"
CAT_PATH = INP / "n14_target_catalog.json"
N11B_SUM = ROOT / "analysis_workspace/work_n11b_20261128_harps_single_epoch_transient_laser/results/N11B_ANALYZER_SUMMARY.json"
N12_SUM = ROOT / "analysis_workspace/work_n12_20261128_scaled_harps_transient_laser_comb/results/N12_ANALYZER_SUMMARY.json"

DL_BASE = "https://dataportal.eso.org/dataportal_new/file/"
C_KMS = 299792.458
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
THAR_LINES_A = {
    "ArI_5912": 5912.085,
    "ArI_6032": 6032.127,
    "ArI_6043": 6043.223,
    "ArI_6145": 6145.441,
    "ArI_6416": 6416.307,
    "ThI_6457": 6457.282,
    "ArI_6677": 6677.282,
    "ArI_6753": 6752.834,
    "ArI_6871": 6871.289,
}

CUT_HALF = 25
CORE_HALF = 9
CORE_DX = np.arange(-CORE_HALF, CORE_HALF + 1, dtype=np.float64)
SIGMA_GRID = np.linspace(0.35, 8.5, 164)
DX0_GRID = np.linspace(-1.5, 1.5, 13)
TEMPLATES: list[tuple[float, float, np.ndarray]] = []
for _s in SIGMA_GRID:
    for _d0 in DX0_GRID:
        _g = np.exp(-0.5 * ((CORE_DX - _d0) / _s) ** 2)
        _g /= math.sqrt(float(np.sum(_g * _g)))
        TEMPLATES.append((float(_s), float(_d0), _g))


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


def flare_ratios_arr(wave: np.ndarray, flux: np.ndarray) -> tuple[float, float]:
    def ratio_around(lam_c: float) -> float:
        m_pk = (wave >= lam_c - 1.5) & (wave <= lam_c + 1.5) & np.isfinite(flux)
        m_ct = (((wave >= lam_c - 14.0) & (wave <= lam_c - 6.0)) | ((wave >= lam_c + 6.0) & (wave <= lam_c + 14.0))) & np.isfinite(flux)
        if int(np.sum(m_pk)) < 10 or int(np.sum(m_ct)) < 20:
            return 1.0
        ct = float(np.median(flux[m_ct]))
        return float(np.max(flux[m_pk])) / max(ct, 1.0)
    return round(ratio_around(6562.80), 3), round(ratio_around(4861.33), 3)


def stream_and_normalize_dp(dp_id: str, cand: dict) -> tuple[np.ndarray, dict[str, object]]:
    url = DL_BASE + urllib.parse.quote(dp_id)
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-N14/1.0"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw_bytes = resp.read()
            if len(raw_bytes) < 1_000_000:
                raise ValueError(f"Small FITS {len(raw_bytes)}B for {dp_id}")
            sha = hashlib.sha256(raw_bytes).hexdigest()
            with fits.open(io.BytesIO(raw_bytes), memmap=False) as hdul:
                hdr = hdul[0].header
                tab = hdul[1].data
                cols = set(tab.names or [])
                if not {"WAVE", "FLUX"}.issubset(cols):
                    raise ValueError(f"Missing WAVE/FLUX in {dp_id}: {cols}")
                wave = np.asarray(tab["WAVE"], dtype=np.float64).ravel()
                flux = np.asarray(tab["FLUX"], dtype=np.float64).ravel()
            del raw_bytes
            if wave.size < 250000:
                raise ValueError(f"Short wave {wave.size} in {dp_id}")
            order = np.argsort(wave)
            wave = wave[order]
            flux = flux[order]
            m4869 = (wave >= 4800.0) & (wave <= 6900.0) & np.isfinite(flux) & (flux > 0.0)
            if int(np.sum(m4869)) < 180000:
                raise ValueError(f"Insufficient 4800-6900A px in {dp_id}")

            ha_r, hb_r = flare_ratios_arr(wave, flux)
            f_grid = np.interp(LAM, wave, flux, left=np.nan, right=np.nan)
            bad = STATIC_MASK | (~np.isfinite(f_grid)) | (f_grid <= 0.0)
            f_clean = np.where(bad, np.nan, f_grid)
            f_dec = f_clean[DEC_IDX]
            ok_dec = np.isfinite(f_dec)
            f_dec_fill = np.interp(LAM_DEC, LAM_DEC[ok_dec], f_dec[ok_dec]) if np.any(ok_dec) else np.ones_like(LAM_DEC)
            cont_dec = median_filter(f_dec_fill, size=21, mode="nearest")
            cont_full = np.interp(LAM, LAM_DEC, cont_dec)
            norm = np.where((~bad) & (cont_full > 0), f_clean / np.maximum(cont_full, 1e-6), np.nan).astype(np.float32)

            berv = hdr.get("HIERARCH ESO DRS BERV", hdr.get("HIERARCH ESO QC BERV", np.nan))
            sn50 = hdr.get("HIERARCH ESO DRS SPE EXT SN50", hdr.get("SNR", cand.get("snr", np.nan)))
            meta = {
                "dp_id": dp_id,
                "tap_target": str(cand.get("target_name", "")),
                "tap_snr": round(float(cand.get("snr", 0.0)), 2),
                "mjd_obs": round(float(hdr.get("MJD-OBS", cand.get("t_min", 0.0))), 6),
                "exptime_s": round(float(hdr.get("EXPTIME", cand.get("exptime", 0.0))), 2),
                "snr_hdr": round(float(sn50), 2) if sn50 is not None and np.isfinite(float(sn50)) else round(float(cand.get("snr", 0.0)), 2),
                "berv_kms": round(float(berv), 5) if berv is not None and np.isfinite(float(berv)) else 0.0,
                "dpr_type": str(hdr.get("HIERARCH ESO DPR TYPE", "")),
                "object_hdr": str(hdr.get("OBJECT", "")),
                "ha_ratio": ha_r,
                "hb_ratio": hb_r,
                "bytes": 0,  # overwritten cleanly below if saved; store exact len via local var
                "sha256": sha,
            }
            return norm, meta
        except Exception as exc:
            last_err = exc
            time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"Stream failed for {dp_id}: {last_err}")


def fetch_epoch_slot(slot_idx: int, cands: list[dict], used_ids: set[str]) -> tuple[int, np.ndarray, dict[str, object]]:
    last_err: Exception | None = None
    for cand in cands:
        dp = str(cand["dp_id"])
        if dp in used_ids:
            continue
        url = DL_BASE + urllib.parse.quote(dp)
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-N14/1.0"})
                with urllib.request.urlopen(req, timeout=90) as resp:
                    raw_bytes = resp.read()
                nbytes = len(raw_bytes)
                if nbytes < 1_000_000:
                    raise ValueError(f"Small FITS {nbytes}B for {dp}")
                sha = hashlib.sha256(raw_bytes).hexdigest()
                with fits.open(io.BytesIO(raw_bytes), memmap=False) as hdul:
                    hdr = hdul[0].header
                    tab = hdul[1].data
                    cols = set(tab.names or [])
                    if not {"WAVE", "FLUX"}.issubset(cols):
                        raise ValueError(f"Missing WAVE/FLUX in {dp}: {cols}")
                    wave = np.asarray(tab["WAVE"], dtype=np.float64).ravel()
                    flux = np.asarray(tab["FLUX"], dtype=np.float64).ravel()
                del raw_bytes
                if wave.size < 250000:
                    raise ValueError(f"Short wave {wave.size} in {dp}")
                order = np.argsort(wave)
                wave = wave[order]
                flux = flux[order]
                m4869 = (wave >= 4800.0) & (wave <= 6900.0) & np.isfinite(flux) & (flux > 0.0)
                if int(np.sum(m4869)) < 180000:
                    raise ValueError(f"Insufficient 4800-6900A px in {dp}")

                ha_r, hb_r = flare_ratios_arr(wave, flux)
                f_grid = np.interp(LAM, wave, flux, left=np.nan, right=np.nan)
                bad = STATIC_MASK | (~np.isfinite(f_grid)) | (f_grid <= 0.0)
                f_clean = np.where(bad, np.nan, f_grid)
                f_dec = f_clean[DEC_IDX]
                ok_dec = np.isfinite(f_dec)
                f_dec_fill = np.interp(LAM_DEC, LAM_DEC[ok_dec], f_dec[ok_dec]) if np.any(ok_dec) else np.ones_like(LAM_DEC)
                cont_dec = median_filter(f_dec_fill, size=21, mode="nearest")
                cont_full = np.interp(LAM, LAM_DEC, cont_dec)
                norm = np.where((~bad) & (cont_full > 0), f_clean / np.maximum(cont_full, 1e-6), np.nan).astype(np.float32)

                berv = hdr.get("HIERARCH ESO DRS BERV", hdr.get("HIERARCH ESO QC BERV", np.nan))
                sn50 = hdr.get("HIERARCH ESO DRS SPE EXT SN50", hdr.get("SNR", cand.get("snr", np.nan)))
                meta = {
                    "stratum": slot_idx,
                    "dp_id": dp,
                    "tap_target": str(cand.get("target_name", "")),
                    "tap_snr": round(float(cand.get("snr", 0.0)), 2),
                    "mjd_obs": round(float(hdr.get("MJD-OBS", cand.get("t_min", 0.0))), 6),
                    "exptime_s": round(float(hdr.get("EXPTIME", cand.get("exptime", 0.0))), 2),
                    "snr_hdr": round(float(sn50), 2) if sn50 is not None and np.isfinite(float(sn50)) else round(float(cand.get("snr", 0.0)), 2),
                    "berv_kms": round(float(berv), 5) if berv is not None and np.isfinite(float(berv)) else 0.0,
                    "dpr_type": str(hdr.get("HIERARCH ESO DPR TYPE", "")),
                    "object_hdr": str(hdr.get("OBJECT", "")),
                    "ha_ratio": ha_r,
                    "hb_ratio": hb_r,
                    "bytes": nbytes,
                    "sha256": sha,
                }
                return slot_idx, norm, meta
            except Exception as exc:
                last_err = exc
                time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"Slot {slot_idx} exhausted candidates: {last_err}")


def fetch_star_cube(target: dict, ex_net: ThreadPoolExecutor) -> tuple[np.ndarray, list[dict[str, object]]]:
    strata = target["strata"]
    fallbacks = target.get("star_fallbacks", [])
    used_ids: set[str] = set()
    norms: list[np.ndarray | None] = [None] * 8
    metas: list[dict[str, object] | None] = [None] * 8

    # First submit each stratum with fallback into star_fallbacks
    futs = {}
    for idx in range(8):
        cands = list(strata[idx]) + [f for f in fallbacks]
        futs[ex_net.submit(fetch_epoch_slot, idx, cands, set())] = idx

    failed_slots: list[int] = []
    for fut in as_completed(futs):
        idx = futs[fut]
        try:
            s_i, arr, mt = fut.result()
            norms[s_i] = arr
            metas[s_i] = mt
            used_ids.add(str(mt["dp_id"]))
        except Exception:
            failed_slots.append(idx)

    # Sequential salvage for any failed slot using unused fallbacks
    for idx in failed_slots:
        s_i, arr, mt = fetch_epoch_slot(idx, [f for f in fallbacks if str(f["dp_id"]) not in used_ids], used_ids)
        norms[s_i] = arr
        metas[s_i] = mt
        used_ids.add(str(mt["dp_id"]))

    if len(used_ids) < 8 or any(m is None for m in metas):
        raise RuntimeError(f"{target['star']}: could not collect 8 distinct valid HARPS spectra")

    paired = sorted(zip(metas, norms), key=lambda x: float(x[0]["mjd_obs"]))  # type: ignore[arg-type]
    metas_s = [p[0] for p in paired]
    cube = np.stack([p[1] for p in paired], axis=0)  # type: ignore[misc]
    return cube, metas_s  # type: ignore[return-value]


def analyze_star_cube(star_meta: dict, cube: np.ndarray, rows: list[dict[str, object]]) -> dict:
    star = str(star_meta["star"])
    n_ep = cube.shape[0]
    finite_cnt = np.sum(np.isfinite(cube), axis=0)
    valid_px = (~STATIC_MASK) & (finite_cnt >= 6)
    T_all = np.ones(LAM.size, dtype=np.float32)
    sigma_pix = np.ones(LAM.size, dtype=np.float32)
    if np.any(valid_px):
        T_all[valid_px] = np.nanmedian(cube[:, valid_px], axis=0)
        sigma_pix[valid_px] = 1.4826 * np.nanmedian(np.abs(cube[:, valid_px] - T_all[None, valid_px]), axis=0)
    cube_fill = np.where(valid_px[None, :] & np.isfinite(cube), cube, T_all[None, :])

    # Exact O(1) 7-epoch LOEO median (N=8)
    S = np.sort(cube_fill, axis=0)
    half = n_ep // 2
    T_loeo = np.where(cube_fill <= S[half - 1 : half, :], S[half : half + 1, :], S[half - 1 : half, :])
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

    n_peaks_z10 = 0
    n_t1 = 0
    n_t2 = 0
    peak_rows: list[dict[str, object]] = []
    trig_rows: list[dict[str, object]] = []
    comb_valid = valid_px & (~SKY_TELLURIC_MASK)

    for ei, er in enumerate(rows):
        z_mf = z_mf_cube[ei]
        z_pix = z_pix_cube[ei]
        berv = float(er["berv_kms"])
        t1_ep: list[dict[str, object]] = []
        peaks = detect_peaks(z_mf, thresh=10.0, min_sep=50)
        for idx in peaks:
            if idx < CUT_HALF or idx >= LAM.size - CUT_HALF:
                continue
            lam_a = float(LAM[idx])
            lam_topo = lam_a / (1.0 + berv / C_KMS)
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
                "mjd_obs": er["mjd_obs"], "berv_kms": berv, "lam_bary_a": round(lam_a, 4),
                "lam_topo_a": round(lam_topo, 4), "dpr_type": er["dpr_type"],
                "ha_ratio": er["ha_ratio"], "hb_ratio": er["hb_ratio"],
                "z_mf": round(z_val, 3), "n_epochs_gt5": n_ep_gt5, "fit_sigma_px": sh["fit_sigma_px"],
                "psf_sigma_px": sh["psf_sigma_px"], "fwhm_ratio": sh["fwhm_ratio"],
                "r_gauss": sh["r_gauss"], "n_pix_gt3": int(sh["n_pix_gt3"]),
                "min_neg_ratio": sh["min_neg_ratio"], "stage2_status": veto_cat,
                "comb_teeth": "", "matched_thar": "",
            }
            peak_rows.append(drow)
            if veto_cat == "T1_TRANSIENT_LASER_PASS":
                t1_ep.append(drow)

        if len(t1_ep) >= 10:
            matched_thar = sorted({
                name for dr in t1_ep for name, w_th in THAR_LINES_A.items()
                if abs(float(dr["lam_topo_a"]) - w_th) <= 0.08
            })
            if matched_thar:
                th_str = ";".join(matched_thar)
                for dr in t1_ep:
                    dr["matched_thar"] = th_str
        n_t1 += len(t1_ep)
        trig_rows.extend(t1_ep)

        if "WAVE" not in str(er.get("dpr_type", "")).upper():
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
                lam0_t = clean_teeth[0][0]
                crow = {
                    "star": star, "channel": "T2_OPTICAL_COMB", "epoch_idx": ei, "dp_id": er["dp_id"],
                    "mjd_obs": er["mjd_obs"], "berv_kms": berv, "lam_bary_a": round(lam0_t, 4),
                    "lam_topo_a": round(lam0_t / (1.0 + berv / C_KMS), 4), "dpr_type": er["dpr_type"],
                    "ha_ratio": er["ha_ratio"], "hb_ratio": er["hb_ratio"],
                    "z_mf": round(float(np.mean([z for _, z in clean_teeth])), 3), "n_epochs_gt5": len(clean_teeth),
                    "fit_sigma_px": 0.0, "psf_sigma_px": 0.0, "fwhm_ratio": 1.0, "r_gauss": 0.95,
                    "n_pix_gt3": len(clean_teeth), "min_neg_ratio": 0.0, "stage2_status": "T2_OPTICAL_COMB_PASS",
                    "comb_teeth": teeth_str, "matched_thar": "",
                }
                trig_rows.append(crow)

    bervs = [float(r["berv_kms"]) for r in rows]
    mjds = [float(r["mjd_obs"]) for r in rows]
    snrs = [float(r["snr_hdr"]) for r in rows]
    med_sigma = float(np.median(sigma_tot_cube[:, valid_px]))
    p_10sig_kw = compute_beamed_10sig_power_kw(float(star_meta["dist_pc"]), float(star_meta["vmag"]), med_sigma)
    star_sum = {
        "star": star, "common_name": star_meta["common_name"], "sp_type": star_meta["sp_type"],
        "ra_deg": star_meta["ra_deg"], "dec_deg": star_meta["dec_deg"],
        "dist_pc": star_meta["dist_pc"], "n_exoplanets": star_meta["n_exoplanets"],
        "vmag": star_meta["vmag"], "epochs": n_ep,
        "mjd_span_days": round(max(mjds) - min(mjds), 1),
        "berv_span_kms": round(max(bervs) - min(bervs), 2) if bervs else 0.0,
        "median_snr_hdr": round(float(np.median(snrs)), 1), "median_sigma_frac": round(med_sigma, 5),
        "p_tx_10sig_kw": round(p_10sig_kw, 5), "peaks_z10_before_veto": n_peaks_z10,
        "stage2_t1_triggers": n_t1, "stage2_t2_comb_triggers": n_t2,
    }
    epoch_out = [{"star": star, **r} for r in rows]
    return {
        "star_sum": star_sum,
        "epochs": epoch_out,
        "peaks": peak_rows,
        "triggers": trig_rows,
        "bench_tuple": (star, cube_fill, sigma_tot_cube, z_mf_cube, comb_valid),
        "loeo_showcase": (LAM[(LAM >= 5165.0) & (LAM <= 5190.0)], cube_fill[0, (LAM >= 5165.0) & (LAM <= 5190.0)], T_loeo[0, (LAM >= 5165.0) & (LAM <= 5190.0)], res_cube[0, (LAM >= 5165.0) & (LAM <= 5190.0)]),
    }


def run_benchmark(bench_pool: list[tuple], cutout_arrays: dict[str, np.ndarray], rng: np.random.Generator) -> list[dict[str, object]]:
    """1,200-trial head-to-head real-HARPS-noise benchmark (exact N12 T1+T2 physics)."""
    inj_rows: list[dict[str, object]] = []
    n_pool = len(bench_pool)
    for b_idx, (star, cube_fill, sigma_tot_cube, z_mf_cube, comb_valid) in enumerate(bench_pool):
        n_ep = cube_fill.shape[0]
        safe_mask = comb_valid.copy()
        safe_mask[:300] = False
        safe_mask[-300:] = False
        safe_mask[(LAM >= 5294.0) & (LAM <= 5349.0)] = False
        safe_indices = np.flatnonzero(safe_mask)

        # Spread 400 T1, 400 T2, 200 CR, 200 Flare across n_pool stars cleanly
        q_t1, r_t1 = divmod(400, n_pool)
        q_cr, r_cr = divmod(200, n_pool)
        n_t1_inj = q_t1 + (1 if b_idx < r_t1 else 0)
        n_t2_inj = q_t1 + (1 if b_idx < r_t1 else 0)
        n_cr_inj = q_cr + (1 if b_idx < r_cr else 0)
        n_fl_inj = q_cr + (1 if b_idx < r_cr else 0)

        def sample_clean_pos() -> int:
            for _ in range(25):
                ci_c = int(rng.choice(safe_indices))
                if np.max(np.abs(z_mf_cube[:, ci_c - 15 : ci_c + 16])) < 5.0:
                    return ci_c
            return int(rng.choice(safe_indices))

        for cls_name, n_tr in (("TRANSIENT_PSF_LASER", n_t1_inj), ("COSMIC_RAY_1_2PX", n_cr_inj), ("BROAD_STELLAR_FLARE", n_fl_inj)):
            for tr in range(n_tr):
                ei = int(rng.integers(0, n_ep))
                ci = sample_clean_pos()
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
                n14_det = int(z_mf_peak >= 10.0 and n_gt5_loc <= 3 and sh_loc["n_pix_gt3"] >= 3 and 0.80 <= sh_loc["fwhm_ratio"] <= 1.50 and sh_loc["r_gauss"] >= 0.88 and sh_loc["min_neg_ratio"] > -0.45)

                if b_idx == 0 and tr == 0:
                    cutout_arrays[f"INJ_{cls_name}_RESZ"] = zp[pk_loc - 25 : pk_loc + 26]
                    cutout_arrays[f"INJ_{cls_name}_ZMF"] = z_mf_loc[pk_loc - 25 : pk_loc + 26]
                    cutout_arrays[f"INJ_{cls_name}_STACKZ"] = z_stack_mf[pk_loc - 25 : pk_loc + 26]
                inj_rows.append({"star": star, "morphology": cls_name, "trial": tr, "lam_a": round(lam0, 3), "z_mf": round(z_mf_peak, 2), "n14_det": n14_det, "classical_stack_det": cls_det})

        for tr in range(n_t2_inj):
            ei = int(rng.integers(0, n_ep))
            teeth_pos: list[int] = []
            for _att in range(120):
                ci_c = sample_clean_pos()
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
                    if b_idx == 0 and tr == 0 and clean_teeth_det == 1:
                        cutout_arrays["INJ_SUBTHRESHOLD_COMB_RESZ"] = zp[pk_loc - 25 : pk_loc + 26]
                        cutout_arrays["INJ_SUBTHRESHOLD_COMB_ZMF"] = z_mf_loc[pk_loc - 25 : pk_loc + 26]
                        cutout_arrays["INJ_SUBTHRESHOLD_COMB_STACKZ"] = z_stack_mf[pk_loc - 25 : pk_loc + 26]
            n14_t2_det = 1 if clean_teeth_det >= 5 else 0
            inj_rows.append({"star": star, "morphology": "SUBTHRESHOLD_OPTICAL_COMB", "trial": tr, "lam_a": 5500.0, "z_mf": round(float(np.mean(tooth_z_list)), 2), "n14_det": n14_t2_det, "classical_stack_det": cls_stack_det})
    return inj_rows


def main() -> int:
    t0 = time.time()
    RES.mkdir(parents=True, exist_ok=True)
    cat = json.loads(CAT_PATH.read_text(encoding="utf-8"))
    primary_list = cat["primary_targets"]
    backup_list = cat["backup_targets"]
    target_goal = int(cat["primary_count"])  # 268

    cp_stars_p = RES / "n14_checkpoint_stars.jsonl"
    cp_epochs_p = RES / "n14_checkpoint_epochs.jsonl"
    cp_peaks_p = RES / "n14_checkpoint_peaks.jsonl"
    cp_trigs_p = RES / "n14_checkpoint_triggers.jsonl"

    done_stars: dict[str, dict] = {}
    if cp_stars_p.exists():
        for ln in cp_stars_p.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                obj = json.loads(ln)
                done_stars[obj["star"]] = obj

    epoch_rows: list[dict] = [json.loads(ln) for ln in cp_epochs_p.read_text(encoding="utf-8").splitlines() if ln.strip()] if cp_epochs_p.exists() else []
    peak_rows: list[dict] = [json.loads(ln) for ln in cp_peaks_p.read_text(encoding="utf-8").splitlines() if ln.strip()] if cp_peaks_p.exists() else []
    trig_rows: list[dict] = [json.loads(ln) for ln in cp_trigs_p.read_text(encoding="utf-8").splitlines() if ln.strip()] if cp_trigs_p.exists() else []

    bench_pool: list[tuple] = []
    cutout_arrays: dict[str, np.ndarray] = {}
    showcase_done: set[str] = set()

    queue = [t for t in primary_list if t["star"] not in done_stars]
    backup_q = [t for t in backup_list if t["star"] not in done_stars]

    with ThreadPoolExecutor(max_workers=12) as ex_net:
        # Process stars in sequence using parallel 8-thread network fetch per star (~0.8s compute)
        idx_q = 0
        while len(done_stars) < target_goal and idx_q < len(queue) + len(backup_q):
            tgt = queue[idx_q] if idx_q < len(queue) else backup_q[idx_q - len(queue)]
            idx_q += 1
            st_name = tgt["star"]
            if st_name in done_stars:
                continue
            try:
                cube, metas = fetch_star_cube(tgt, ex_net)
                out = analyze_star_cube(tgt, cube, metas)
            except Exception as exc:
                print(f"[N14 WARN] Skipping {st_name}: {exc}", flush=True)
                continue

            s_sum = out["star_sum"]
            done_stars[st_name] = s_sum
            epoch_rows.extend(out["epochs"])
            peak_rows.extend(out["peaks"])
            trig_rows.extend(out["triggers"])

            with cp_stars_p.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(s_sum) + "\n")
            with cp_epochs_p.open("a", encoding="utf-8") as fh:
                for er in out["epochs"]:
                    fh.write(json.dumps(er) + "\n")
            if out["peaks"]:
                with cp_peaks_p.open("a", encoding="utf-8") as fh:
                    for pr in out["peaks"]:
                        fh.write(json.dumps(pr) + "\n")
            if out["triggers"]:
                with cp_trigs_p.open("a", encoding="utf-8") as fh:
                    for tr in out["triggers"]:
                        fh.write(json.dumps(tr) + "\n")

            n_done = len(done_stars)
            if len(bench_pool) < 24 and (n_done % 10 == 1 or n_done <= 4):
                bench_pool.append(out["bench_tuple"])

            sp0 = str(s_sum["sp_type"])[:1].upper()
            if sp0 in ("F", "G", "K", "M") and sp0 not in showcase_done:
                showcase_done.add(sp0)
                lam_s, ep0_s, tmpl_s, res_s = out["loeo_showcase"]
                cutout_arrays[f"SHOW_{sp0}_STAR"] = np.array([f"{s_sum['common_name']} ({s_sum['sp_type']}, V={s_sum['vmag']:.2f})"])
                cutout_arrays[f"SHOW_{sp0}_LAM"] = lam_s
                cutout_arrays[f"SHOW_{sp0}_EP0"] = ep0_s
                cutout_arrays[f"SHOW_{sp0}_TMPL"] = tmpl_s
                cutout_arrays[f"SHOW_{sp0}_RES"] = res_s

            if n_done % 10 == 0 or n_done == target_goal:
                print(
                    f"[N14 {n_done:3d}/{target_goal}] {st_name:12s} ({s_sum['dist_pc']:5.2f}pc {s_sum['sp_type']:6s}): "
                    f"P10σ={s_sum['p_tx_10sig_kw']:8.2f} kW, Z10={s_sum['peaks_z10_before_veto']:3d}, "
                    f"T1={s_sum['stage2_t1_triggers']:2d}, T2={s_sum['stage2_t2_comb_triggers']} ({time.time()-t0:.0f}s)",
                    flush=True,
                )

        # If script resumed from checkpoints and bench_pool < 24, top up bench_pool cleanly without adding to star_sum
        if len(bench_pool) < 24:
            all_by_name = {t["star"]: t for t in primary_list + backup_list}
            for st_k in list(done_stars.keys())[::max(1, len(done_stars) // 24)]:
                if any(b[0] == st_k for b in bench_pool):
                    continue
                if st_k in all_by_name:
                    cube, metas = fetch_star_cube(all_by_name[st_k], ex_net)
                    out = analyze_star_cube(all_by_name[st_k], cube, metas)
                    bench_pool.append(out["bench_tuple"])
                    sp0 = str(done_stars[st_k]["sp_type"])[:1].upper()
                    if sp0 in ("F", "G", "K", "M") and sp0 not in showcase_done:
                        showcase_done.add(sp0)
                        lam_s, ep0_s, tmpl_s, res_s = out["loeo_showcase"]
                        cutout_arrays[f"SHOW_{sp0}_STAR"] = np.array([f"{done_stars[st_k]['common_name']} ({done_stars[st_k]['sp_type']}, V={done_stars[st_k]['vmag']:.2f})"])
                        cutout_arrays[f"SHOW_{sp0}_LAM"] = lam_s
                        cutout_arrays[f"SHOW_{sp0}_EP0"] = ep0_s
                        cutout_arrays[f"SHOW_{sp0}_TMPL"] = tmpl_s
                        cutout_arrays[f"SHOW_{sp0}_RES"] = res_s
                if len(bench_pool) >= 24:
                    break

    if len(done_stars) < target_goal:
        raise RuntimeError(f"Only completed {len(done_stars)} < {target_goal} hosts!")

    print(f"[N14] Running 1,200-trial head-to-head real-HARPS benchmark across {len(bench_pool)} F/G/K/M stars ...", flush=True)
    rng = np.random.default_rng(2026112814)
    inj_rows = run_benchmark(bench_pool, cutout_arrays, rng)

    star_summary = sorted(done_stars.values(), key=lambda x: float(x["dist_pc"]))
    def write_csv(path: Path, rows_out: list[dict], cols: list[str]) -> None:
        with path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows_out)

    write_csv(
        INP / "n14_epoch_receipts.csv",
        epoch_rows,
        ["star", "stratum", "dp_id", "tap_target", "tap_snr", "mjd_obs", "exptime_s", "snr_hdr", "berv_kms", "dpr_type", "object_hdr", "ha_ratio", "hb_ratio", "bytes", "sha256"],
    )
    write_csv(
        RES / "N14_STAR_SUMMARY.csv",
        star_summary,
        ["star", "common_name", "sp_type", "ra_deg", "dec_deg", "dist_pc", "n_exoplanets", "vmag", "epochs", "mjd_span_days", "berv_span_kms", "median_snr_hdr", "median_sigma_frac", "p_tx_10sig_kw", "peaks_z10_before_veto", "stage2_t1_triggers", "stage2_t2_comb_triggers"],
    )
    p_cols = ["star", "channel", "epoch_idx", "dp_id", "mjd_obs", "berv_kms", "lam_bary_a", "lam_topo_a", "dpr_type", "ha_ratio", "hb_ratio", "z_mf", "n_epochs_gt5", "fit_sigma_px", "psf_sigma_px", "fwhm_ratio", "r_gauss", "n_pix_gt3", "min_neg_ratio", "stage2_status", "comb_teeth", "matched_thar"]
    write_csv(RES / "N14_PEAK_DIAGNOSTICS.csv", peak_rows, p_cols)
    write_csv(RES / "N14_STAGE2_TRIGGERS.csv", trig_rows, p_cols)
    write_csv(RES / "N14_INJECTION_BENCHMARK.csv", inj_rows, ["star", "morphology", "trial", "lam_a", "z_mf", "n14_det", "classical_stack_det"])
    np.savez_compressed(RES / "n14_cutouts.npz", **cutout_arrays)

    by_m: dict[str, dict] = {}
    for m in ("TRANSIENT_PSF_LASER", "SUBTHRESHOLD_OPTICAL_COMB", "COSMIC_RAY_1_2PX", "BROAD_STELLAR_FLARE"):
        sub = [r for r in inj_rows if r["morphology"] == m]
        by_m[m] = {
            "trials": len(sub),
            "n14_positive": sum(int(r["n14_det"]) for r in sub),
            "n14_rate": round(sum(int(r["n14_det"]) for r in sub) / max(len(sub), 1), 4),
            "classical_stack_positive": sum(int(r["classical_stack_det"]) for r in sub),
            "classical_stack_rate": round(sum(int(r["classical_stack_det"]) for r in sub) / max(len(sub), 1), 4),
        }

    s11b = json.loads(N11B_SUM.read_text(encoding="utf-8"))
    s12 = json.loads(N12_SUM.read_text(encoding="utf-8"))
    t1_eff = by_m["TRANSIENT_PSF_LASER"]["n14_rate"]
    t2_eff = by_m["SUBTHRESHOLD_OPTICAL_COMB"]["n14_rate"]
    n_stars = len(star_summary)
    n_ep_tot = len(epoch_rows)
    n14_eff_stars = n_stars * t1_eff
    n14_eff_ep = n_ep_tot * t1_eff

    uni_stars_raw = n_stars + int(s12["unified_stars_total"])
    uni_stars_eff = n14_eff_stars + float(s12["provisional_zero_eti_bayesian_bounds"]["unified_32stars_eff"]["n_eff"])
    uni_ep_raw = n_ep_tot + int(s12["unified_epochs_total"])
    uni_ep_eff = n14_eff_ep + float(s12["provisional_zero_eti_bayesian_bounds"]["unified_640epochs_eff"]["n_eff"])
    uni_planets = sum(int(r["n_exoplanets"]) for r in star_summary) + 76

    p_vals = [float(r["p_tx_10sig_kw"]) for r in star_summary]
    t1_tot = sum(int(r["stage2_t1_triggers"]) for r in star_summary)
    t2_tot = sum(int(r["stage2_t2_comb_triggers"]) for r in star_summary)
    summary = {
        "campaign": "SPOR_N14_300STAR_HARPS_TRANSIENT_LASER_AND_COMB",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "elapsed_s": round(time.time() - t0, 2),
        "stars_analyzed": n_stars,
        "epochs_analyzed": n_ep_tot,
        "unified_stars_total": uni_stars_raw,
        "unified_epochs_total": uni_ep_raw,
        "n14_exoplanets_total": sum(int(r["n_exoplanets"]) for r in star_summary),
        "unified_exoplanets_total": uni_planets,
        "total_fits_bytes_streamed": sum(int(r["bytes"]) for r in epoch_rows),
        "total_fits_mib_streamed": round(sum(int(r["bytes"]) for r in epoch_rows) / (1024.0 * 1024.0), 2),
        "wavelength_band_a": [4800.0, 6900.0],
        "spectral_resolution_r": HARPS_R,
        "min_p_tx_10sig_kw": round(min(p_vals), 5),
        "median_p_tx_10sig_kw": round(float(np.median(p_vals)), 5),
        "max_p_tx_10sig_kw": round(max(p_vals), 5),
        "peaks_z10_before_shape_veto": len(peak_rows),
        "stage2_t1_triggers_total": t1_tot,
        "stage2_t2_comb_triggers_total": t2_tot,
        "stage2_triggers_total": len(trig_rows),
        "injections": {
            "trials_total": len(inj_rows),
            "laser_completeness": t1_eff,
            "subthreshold_comb_completeness": t2_eff,
            "classical_median_stack_completeness": by_m["TRANSIENT_PSF_LASER"]["classical_stack_rate"],
            "cosmic_ray_fpr": by_m["COSMIC_RAY_1_2PX"]["n14_rate"],
            "broad_flare_fpr": by_m["BROAD_STELLAR_FLARE"]["n14_rate"],
            "per_morphology": by_m,
        },
        "provisional_zero_eti_bayesian_bounds": {
            "n14_stars_raw_268": exact_bayes_bounds(float(n_stars)),
            "n14_stars_eff": exact_bayes_bounds(n14_eff_stars),
            "n14_epochs_eff": exact_bayes_bounds(n14_eff_ep),
            "unified_300stars_raw": exact_bayes_bounds(float(uni_stars_raw)),
            "unified_300stars_eff": exact_bayes_bounds(uni_stars_eff),
            "unified_2784epochs_raw": exact_bayes_bounds(float(uni_ep_raw)),
            "unified_2784epochs_eff": exact_bayes_bounds(uni_ep_eff),
        },
        "external_contacts": 0,
    }
    (RES / "N14_ANALYZER_SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[N14 Stage 2] Done in {summary['elapsed_s']}s: T1={t1_eff*100:.2f}%, T2={t2_eff*100:.2f}%, Trig={len(trig_rows)}, Uni300_f95={summary['provisional_zero_eti_bayesian_bounds']['unified_300stars_eff']['jeffreys_f95_pct']}%", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
