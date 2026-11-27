#!/usr/bin/env python3
"""Prospectively locked TESS 2-min Milky Way megastructure & optical-beacon analyzer (Spor N7)."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits
from scipy.ndimage import median_filter
from scipy.special import betaincinv

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n7_20261127_tess_milky_way_megastructures"
INP = ROOT / "inputs_n7_20261127"
RES = WS / "results"

DT_DAY = 2.0 / 1440.0  # 2-minute TESS SPOC cadence in days

# Locked prospective thresholds (must match METHOD_LOCK.json)
MIN_VALID_CADENCES = 2000
GAP_THRESHOLD_DAYS = 0.5
GAP_EDGE_MASK_DAYS = 0.15
DETREND_WINDOW_HOURS = 72  # 3.0 days in 1-hour bins

# Channel A: Asymmetric / Deep Megastructure Transits (Arnold 2005 / Boyajian)
A_BOX_WIDTHS_CAD = (36, 180, 720)  # 1.2 h, 6.0 h, 24.0 h
A_MIN_DEPTH = 0.005
A_MIN_SNR = 12.0
A_MIN_IN_DIP_PTS = 5

# Channel B: Coherent Narrow-Band Optical Beacons (Fourier 2-300 cyc/day)
B_FMIN_CPD = 2.0
B_FMAX_CPD = 300.0
B_MIN_FFT_SNR = 15.0
B_MIN_NARROW_Q = 4.0
B_MIN_AMP_PPM = 300.0
B_MIN_SAP_SNR = 8.0

# Channel C: Symmetric Optical Light-Sail Flashes (anti-FRED filter)
C_MIN_AMP = 0.010
C_MIN_SNR = 15.0
C_MIN_PTS = 2
C_MAX_FRED_RATIO = 1.8

INJECTION_SEED = 20261127


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _f(v: Any, default: float = float("nan")) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def jeffreys_f95(n_eff: float) -> float:
    return float(betaincinv(0.5, float(n_eff) + 0.5, 0.95)) if n_eff > 0 else 1.0


def uniform_f95(n_eff: float) -> float:
    return 1.0 - (0.05 ** (1.0 / (float(n_eff) + 1.0))) if n_eff > 0 else 1.0


def clopper_pearson_f95(n_eff: float) -> float:
    return 1.0 - (0.05 ** (1.0 / float(n_eff))) if n_eff > 0 else 1.0


def load_and_clean_tess_fits(fits_path: Path) -> dict[str, Any] | None:
    with fits.open(fits_path, memmap=False) as hdul:
        h0 = hdul[0].header
        tab = hdul[1].data
        t = np.asarray(tab["TIME"], dtype=np.float64)
        pdc = np.asarray(tab["PDCSAP_FLUX"], dtype=np.float64)
        sap = np.asarray(tab["SAP_FLUX"], dtype=np.float64)
        qual = np.asarray(tab["QUALITY"], dtype=np.int64)
        cx = np.asarray(tab["MOM_CENTR1"], dtype=np.float64)
        cy = np.asarray(tab["MOM_CENTR2"], dtype=np.float64)
        crowdsap = _f(hdul[1].header.get("CROWDSAP"), _f(h0.get("CROWDSAP"), 1.0))

    m = (qual == 0) & np.isfinite(t) & np.isfinite(pdc) & (pdc > 0.0) & np.isfinite(sap) & (sap > 0.0)
    if int(np.sum(m)) < MIN_VALID_CADENCES:
        return None

    t = t[m]
    pdc = pdc[m]
    sap = sap[m]
    cx = cx[m]
    cy = cy[m]

    order = np.argsort(t)
    t, pdc, sap, cx, cy = t[order], pdc[order], sap[order], cx[order], cy[order]

    # Mask points within +-GAP_EDGE_MASK_DAYS of large telemetry/orbit gaps (> GAP_THRESHOLD_DAYS)
    dt = np.diff(t)
    gap_idx = np.where(dt > GAP_THRESHOLD_DAYS)[0]
    if len(gap_idx) > 0:
        keep = np.ones(len(t), dtype=bool)
        for gi in gap_idx:
            t_left, t_right = t[gi], t[gi + 1]
            keep &= ~((t >= t_left - GAP_EDGE_MASK_DAYS) & (t <= t_left))
            keep &= ~((t >= t_right) & (t <= t_right + GAP_EDGE_MASK_DAYS))
        t, pdc, sap, cx, cy = t[keep], pdc[keep], sap[keep], cx[keep], cy[keep]

    if len(t) < MIN_VALID_CADENCES:
        return None

    pdc_med = float(np.nanmedian(pdc))
    sap_med = float(np.nanmedian(sap))
    if not (pdc_med > 0 and sap_med > 0):
        return None
    f_pdc = pdc / pdc_med
    f_sap = sap / sap_med

    base_pdc = _rolling_hourly_median_baseline(t, f_pdc)
    base_sap = _rolling_hourly_median_baseline(t, f_sap)

    r_pdc = (f_pdc / base_pdc) - 1.0
    r_sap = (f_sap / base_sap) - 1.0

    med_r = float(np.median(r_pdc))
    r_pdc = r_pdc - med_r
    r_sap = r_sap - float(np.median(r_sap))
    sigma_mad = 1.4826 * float(np.median(np.abs(r_pdc)))
    if not (sigma_mad > 0):
        return None

    # Uniform 2-min grid mapping
    t0 = float(t[0])
    idx = np.rint((t - t0) / DT_DAY).astype(np.int64)
    n_grid = int(idx[-1]) + 1
    # Guard against pathologically huge multi-year span inside one file
    if n_grid > 120000:
        n_grid = 120000
        keep_g = idx < n_grid
        t, idx, r_pdc, r_sap, cx, cy = t[keep_g], idx[keep_g], r_pdc[keep_g], r_sap[keep_g], cx[keep_g], cy[keep_g]

    return {
        "t": t,
        "t0": t0,
        "idx": idx,
        "n_grid": n_grid,
        "r_pdc": r_pdc,
        "r_sap": r_sap,
        "cx": cx,
        "cy": cy,
        "sigma_mad": sigma_mad,
        "crowdsap": crowdsap,
        "baseline_days": float(t[-1] - t[0]),
        "n_valid": int(len(t)),
    }


def _rolling_hourly_median_baseline(t: np.ndarray, f: np.ndarray) -> np.ndarray:
    t0, t1 = float(t[0]), float(t[-1])
    hour_day = 1.0 / 24.0
    n_bins = max(3, int(math.ceil((t1 - t0) / hour_day)) + 1)
    bin_idx = np.clip(((t - t0) / hour_day).astype(np.int64), 0, n_bins - 1)
    bin_t = t0 + (np.arange(n_bins) + 0.5) * hour_day
    bin_med = np.full(n_bins, np.nan, dtype=np.float64)
    for b in np.unique(bin_idx):
        bin_med[b] = float(np.median(f[bin_idx == b]))

    # Interpolate empty hourly bins linearly before median filtering
    good = np.isfinite(bin_med)
    if np.sum(good) < 2:
        return np.ones_like(f)
    bin_filled = np.interp(bin_t, bin_t[good], bin_med[good])
    smooth = median_filter(bin_filled, size=min(DETREND_WINDOW_HOURS, len(bin_filled)), mode="nearest")
    return np.interp(t, bin_t, smooth)


def analyze_residuals(
    idx: np.ndarray,
    n_grid: int,
    t: np.ndarray,
    r_pdc: np.ndarray,
    r_sap: np.ndarray,
    sigma_mad: float,
    cx: np.ndarray | None = None,
    cy: np.ndarray | None = None,
) -> dict[str, Any]:
    grid_r = np.zeros(n_grid, dtype=np.float64)
    grid_sap = np.zeros(n_grid, dtype=np.float64)
    grid_v = np.zeros(n_grid, dtype=np.float64)
    grid_r[idx] = r_pdc
    grid_sap[idx] = r_sap
    grid_v[idx] = 1.0

    # --- Channel A: Sliding boxcar megadips ---
    cs_r = np.concatenate(([0.0], np.cumsum(grid_r)))
    cs_v = np.concatenate(([0.0], np.cumsum(grid_v)))
    best_depth = 0.0
    best_snr = 0.0
    best_center_g = 0
    best_w = A_BOX_WIDTHS_CAD[0]
    best_n_in_dip = 0

    for w in A_BOX_WIDTHS_CAD:
        if n_grid <= w:
            continue
        win_v = cs_v[w:] - cs_v[:-w]
        ok = win_v >= 0.5 * w
        if not np.any(ok):
            continue
        win_sum = cs_r[w:] - cs_r[:-w]
        means = np.zeros_like(win_sum)
        means[ok] = win_sum[ok] / win_v[ok]
        depths = -means
        snrs = np.zeros_like(depths)
        snrs[ok] = depths[ok] / (sigma_mad / np.sqrt(win_v[ok]))
        j = int(np.argmax(snrs))
        if snrs[j] > best_snr:
            best_snr = float(snrs[j])
            best_depth = float(depths[j])
            best_center_g = j + w // 2
            best_w = w

    # Measure points below -3*sigma_mad and ingress/egress asymmetry around deepest trough
    dip_asym = 0.0
    centroid_dip_shift = 0.0
    half_win_g = max(best_w, 90)
    win_mask = (idx >= best_center_g - half_win_g) & (idx <= best_center_g + half_win_g)
    if np.any(win_mask):
        r_loc = r_pdc[win_mask]
        idx_loc = idx[win_mask]
        n_below = r_loc < -3.0 * sigma_mad
        best_n_in_dip = int(np.sum(n_below))
        if best_n_in_dip >= 2 and best_depth > 0:
            kmin = int(np.argmin(r_loc))
            g_min = int(idx_loc[kmin])
            half_lvl = 0.5 * float(r_loc[kmin])  # negative
            left_pts = np.where((np.arange(len(r_loc)) <= kmin) & (r_loc > half_lvl))[0]
            right_pts = np.where((np.arange(len(r_loc)) >= kmin) & (r_loc > half_lvl))[0]
            g_l = int(idx_loc[left_pts[-1]]) if len(left_pts) else int(idx_loc[0])
            g_r = int(idx_loc[right_pts[0]]) if len(right_pts) else int(idx_loc[-1])
            t_ing = max((g_min - g_l) * DT_DAY, DT_DAY)
            t_egr = max((g_r - g_min) * DT_DAY, DT_DAY)
            dip_asym = abs(t_egr - t_ing) / max(t_egr + t_ing, 1e-4)

        if cx is not None and cy is not None:
            in_core = win_mask & (r_pdc < -2.5 * sigma_mad)
            out_core = ~win_mask
            if np.sum(in_core) >= 3 and np.sum(out_core) >= 20:
                dcx = float(np.nanmedian(cx[in_core]) - np.nanmedian(cx[out_core]))
                dcy = float(np.nanmedian(cy[in_core]) - np.nanmedian(cy[out_core]))
                if math.isfinite(dcx) and math.isfinite(dcy):
                    centroid_dip_shift = math.hypot(dcx, dcy)

    trig_a = (best_depth >= A_MIN_DEPTH) and (best_snr >= A_MIN_SNR) and (best_n_in_dip >= A_MIN_IN_DIP_PTS)

    # --- Channel B: Coherent Narrow-Band Optical Periodic Beacons ---
    n_valid = max(1, len(r_pdc))
    hann = np.hanning(n_grid)
    hann_scale = 2.0 / max(1.0, float(np.sum(hann) * (n_valid / float(n_grid))))
    spec_pdc = np.abs(np.fft.rfft(grid_r * hann)) * hann_scale
    freqs = np.fft.rfftfreq(n_grid, d=DT_DAY)
    band = (freqs >= B_FMIN_CPD) & (freqs <= B_FMAX_CPD)

    fft_snr = 0.0
    narrow_q = 0.0
    amp_ppm = 0.0
    f_peak_cpd = 0.0
    sap_fft_snr = 0.0

    if np.sum(band) > 120:
        b_idx = np.where(band)[0]
        p_band = spec_pdc[b_idx]
        noise_floor = median_filter(p_band, size=101, mode="nearest")
        snr_band = np.where(noise_floor > 0, p_band / noise_floor, 0.0)
        pk_local = int(np.argmax(snr_band))
        fft_snr = float(snr_band[pk_local])
        f_peak_cpd = float(freqs[b_idx[pk_local]])
        amp_ppm = float(p_band[pk_local] * 1e6)

        w0, w1 = max(0, pk_local - 15), min(len(p_band), pk_local + 16)
        wings = [p_band[k] for k in range(w0, w1) if abs(k - pk_local) >= 3]
        if wings:
            w_med = float(np.median(wings))
            narrow_q = float(p_band[pk_local] / w_med) if w_med > 0 else 0.0

        # SAP consistency check (only compute SAP FFT when PDC beacon passes/is near threshold)
        if fft_snr >= 10.0:
            spec_sap = np.abs(np.fft.rfft(grid_sap * hann)) * hann_scale
            ps_band = spec_sap[b_idx]
            nf_sap = median_filter(ps_band, size=101, mode="nearest")
            sap_val = float(ps_band[pk_local])
            sap_nf = float(nf_sap[pk_local])
            sap_fft_snr = sap_val / sap_nf if sap_nf > 0 else 0.0

    trig_b = (
        (fft_snr >= B_MIN_FFT_SNR)
        and (narrow_q >= B_MIN_NARROW_Q)
        and (amp_ppm >= B_MIN_AMP_PPM)
        and (sap_fft_snr >= B_MIN_SAP_SNR)
    )

    # --- Channel C: Symmetric Optical Light-Sail Flashes (anti-FRED) ---
    flash_amp = 0.0
    flash_snr = 0.0
    flash_n_pts = 0
    fred_ratio = 99.0
    centroid_flash_shift = 0.0

    above = (grid_v > 0.5) & (grid_r > 5.0 * sigma_mad)
    if np.any(above):
        diff_ab = np.diff(above.astype(np.int8), prepend=0, append=0)
        starts = np.where(diff_ab == 1)[0]
        ends = np.where(diff_ab == -1)[0]
        best_sym_score = -1.0
        for st, en in zip(starts, ends):
            if int(np.sum(grid_v[st:en])) < C_MIN_PTS:
                continue
            seg = grid_r[st:en]
            pk_rel = int(np.argmax(seg))
            pk_g = st + pk_rel
            amp = float(grid_r[pk_g])
            snr = amp / sigma_mad
            if amp < C_MIN_AMP or snr < C_MIN_SNR:
                continue

            # Measure half-max rise and decay times
            half_lvl = 0.5 * amp
            g_l = pk_g
            while g_l > max(0, st - 30) and (grid_v[g_l] < 0.5 or grid_r[g_l] > half_lvl):
                g_l -= 1
            g_r = pk_g
            while g_r < min(n_grid - 1, en + 60) and (grid_v[g_r] < 0.5 or grid_r[g_r] > half_lvl):
                g_r += 1

            # Linear sub-cadence half-max crossing when both neighbors are valid
            t_r = max((pk_g - g_l) * DT_DAY, 0.5 * DT_DAY)
            t_d = max((g_r - pk_g) * DT_DAY, 0.5 * DT_DAY)
            fr = t_d / max(t_r, 0.5 * DT_DAY)

            if fr <= C_MAX_FRED_RATIO and snr > best_sym_score:
                best_sym_score = snr
                flash_amp = amp
                flash_snr = snr
                flash_n_pts = int(np.sum(grid_v[st:en]))
                fred_ratio = fr
            elif best_sym_score < 0 and snr > flash_snr:
                flash_amp = amp
                flash_snr = snr
                flash_n_pts = int(np.sum(grid_v[st:en]))
                fred_ratio = fr

        if cx is not None and cy is not None and flash_snr >= C_MIN_SNR:
            in_fl = r_pdc > 5.0 * sigma_mad
            out_fl = ~in_fl
            if np.sum(in_fl) >= 2 and np.sum(out_fl) >= 20:
                dcx = float(np.nanmedian(cx[in_fl]) - np.nanmedian(cx[out_fl]))
                dcy = float(np.nanmedian(cy[in_fl]) - np.nanmedian(cy[out_fl]))
                if math.isfinite(dcx) and math.isfinite(dcy):
                    centroid_flash_shift = math.hypot(dcx, dcy)

    trig_c = (
        (flash_amp >= C_MIN_AMP)
        and (flash_snr >= C_MIN_SNR)
        and (flash_n_pts >= C_MIN_PTS)
        and (fred_ratio <= C_MAX_FRED_RATIO)
    )

    reasons = []
    if trig_a:
        reasons.append("N7_MEGADIP")
    if trig_b:
        reasons.append("N7_COHERENT_BEACON")
    if trig_c:
        reasons.append("N7_SYMMETRIC_FLASH")

    return {
        "dip_depth": round(best_depth, 6),
        "dip_snr": round(best_snr, 3),
        "dip_width_hr": round(best_w * DT_DAY * 24.0, 2),
        "dip_n_pts": best_n_in_dip,
        "dip_asym": round(dip_asym, 4),
        "centroid_dip_shift_px": round(centroid_dip_shift, 4),
        "fft_snr": round(fft_snr, 3),
        "narrow_q": round(narrow_q, 3),
        "beacon_amp_ppm": round(amp_ppm, 2),
        "beacon_freq_cpd": round(f_peak_cpd, 5),
        "sap_fft_snr": round(sap_fft_snr, 3),
        "flash_amp": round(flash_amp, 6),
        "flash_snr": round(flash_snr, 3),
        "flash_n_pts": flash_n_pts,
        "fred_ratio": round(fred_ratio, 4),
        "centroid_flash_shift_px": round(centroid_flash_shift, 4),
        "trig_a": trig_a,
        "trig_b": trig_b,
        "trig_c": trig_c,
        "triggered": bool(reasons),
        "trigger_reasons": "|".join(reasons),
    }


def run_injections(quiet_pool: list[dict[str, Any]]) -> dict[str, Any]:
    rng = np.random.default_rng(INJECTION_SEED)
    if not quiet_pool:
        return {"trials_total": 0}

    grid_a: dict[str, dict[str, Any]] = {}
    for depth in (0.002, 0.005, 0.010, 0.025):
        rec = 0
        for _ in range(100):
            base = quiet_pool[int(rng.integers(0, len(quiet_pool)))]
            t = base["t"]
            r_p = base["r_pdc"].copy()
            r_s = base["r_sap"].copy()
            t_mid = float(rng.uniform(t[0] + 2.0, t[-1] - 2.0))
            dur = float(rng.uniform(3.0 / 24.0, 12.0 / 24.0))
            t_ing = 0.275 * dur
            t_egr = 0.725 * dur  # asym = 0.45 Arnold louvered silhouette
            dt = t - t_mid
            prof = np.zeros_like(t)
            m1 = (dt >= -t_ing) & (dt < 0.0)
            m2 = (dt >= 0.0) & (dt <= t_egr)
            prof[m1] = 1.0 + dt[m1] / t_ing
            prof[m2] = 1.0 - dt[m2] / t_egr
            r_p -= depth * prof
            r_s -= depth * prof
            out = analyze_residuals(base["idx"], base["n_grid"], t, r_p, r_s, base["sigma_mad"])
            if out["trig_a"]:
                rec += 1
        grid_a[str(depth)] = {"trials": 100, "recovered": rec, "completeness": round(rec / 100.0, 4)}

    grid_b: dict[str, dict[str, Any]] = {}
    for amp_ppm in (200, 500, 1000, 2500):
        rec = 0
        amp = amp_ppm * 1e-6
        for _ in range(100):
            base = quiet_pool[int(rng.integers(0, len(quiet_pool)))]
            t = base["t"]
            f_cpd = float(rng.uniform(3.0, 200.0))
            phi = float(rng.uniform(0.0, 2.0 * math.pi))
            sig = amp * np.sin(2.0 * math.pi * f_cpd * t + phi)
            out = analyze_residuals(base["idx"], base["n_grid"], t, base["r_pdc"] + sig, base["r_sap"] + sig, base["sigma_mad"])
            if out["trig_b"]:
                rec += 1
        grid_b[str(amp_ppm)] = {"trials": 100, "recovered": rec, "completeness": round(rec / 100.0, 4)}

    grid_c: dict[str, dict[str, Any]] = {}
    for amp in (0.005, 0.010, 0.025, 0.050):
        rec = 0
        for _ in range(100):
            base = quiet_pool[int(rng.integers(0, len(quiet_pool)))]
            t = base["t"]
            t_mid = float(rng.uniform(t[0] + 2.0, t[-1] - 2.0))
            fwhm = float(rng.uniform(8.0 / 1440.0, 20.0 / 1440.0))
            sig_t = fwhm / 2.35482
            sig = amp * np.exp(-0.5 * ((t - t_mid) / sig_t) ** 2)
            out = analyze_residuals(base["idx"], base["n_grid"], t, base["r_pdc"] + sig, base["r_sap"] + sig, base["sigma_mad"])
            if out["trig_c"]:
                rec += 1
        grid_c[str(amp)] = {"trials": 100, "recovered": rec, "completeness": round(rec / 100.0, 4)}

    comp_a = sum(grid_a[k]["recovered"] for k in ("0.005", "0.01", "0.025")) / 300.0
    comp_b = sum(grid_b[k]["recovered"] for k in ("500", "1000", "2500")) / 300.0
    comp_c = sum(grid_c[k]["recovered"] for k in ("0.01", "0.025", "0.05")) / 300.0
    comp_mean = (comp_a + comp_b + comp_c) / 3.0

    return {
        "trials_total": 1200,
        "channel_a_megadip": grid_a,
        "channel_b_beacon": grid_b,
        "channel_c_flash": grid_c,
        "completeness_a_ge_5000ppm": round(comp_a, 4),
        "completeness_b_ge_500ppm": round(comp_b, 4),
        "completeness_c_ge_1pct": round(comp_c, 4),
        "completeness_overall_supra_threshold": round(comp_mean, 4),
    }


def main() -> int:
    RES.mkdir(parents=True, exist_ok=True)
    man_path = INP / "catalogs/n7_milky_way_tess_manifest.csv"
    manifest = list(csv.DictReader(man_path.open("r", encoding="utf-8")))

    catalog_rows: list[dict[str, Any]] = []
    trigger_rows: list[dict[str, Any]] = []
    quiet_pool: list[dict[str, Any]] = []

    for m in manifest:
        fp = INP / "tess_lc" / m["primary_fits_file"]
        if not fp.exists():
            continue
        lc = load_and_clean_tess_fits(fp)
        if lc is None:
            continue
        met = analyze_residuals(lc["idx"], lc["n_grid"], lc["t"], lc["r_pdc"], lc["r_sap"], lc["sigma_mad"], lc["cx"], lc["cy"])
        row = {
            "star": m["star"],
            "common_name": m["common_name"],
            "cohort_tags": m["cohort_tags"],
            "is_benchmark": m["is_benchmark"],
            "ra_j2000": m["ra_j2000"],
            "dec_j2000": m["dec_j2000"],
            "dist_pc": m["dist_pc"],
            "within_10pc": m["within_10pc"],
            "etz_qualified": m["etz_qualified"],
            "ellipsoid_180d": m["ellipsoid_180d"],
            "n_exoplanets": m["n_exoplanets"],
            "tic_id": m["tic_id"],
            "tmag": m["tmag"],
            "teff": m["teff"],
            "rad_rsun": m["rad_rsun"],
            "mass_msun": m["mass_msun"],
            "n_spoc_sectors": m["n_spoc_sectors"],
            "primary_sector": m["primary_sector"],
            "primary_fits_file": m["primary_fits_file"],
            "n_valid_cadences": lc["n_valid"],
            "baseline_days": round(lc["baseline_days"], 4),
            "crowdsap": round(lc["crowdsap"], 4),
            "sigma_mad_ppm": round(lc["sigma_mad"] * 1e6, 2),
            **met,
        }
        catalog_rows.append(row)
        if met["triggered"]:
            trigger_rows.append(row)
        elif m["is_benchmark"] == "False" and lc["sigma_mad"] < 0.002 and len(quiet_pool) < 80:
            quiet_pool.append(lc)

    # Sort triggers by priority (science non-benchmarks first, then max SNR)
    trigger_rows.sort(key=lambda r: (0 if r["is_benchmark"] == "False" else 1, -max(r["dip_snr"], r["fft_snr"], r["flash_snr"])))

    if catalog_rows:
        with (RES / "N7_TESS_MILKY_WAY_CATALOG.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(catalog_rows[0].keys()))
            w.writeheader()
            w.writerows(catalog_rows)

        t_fields = list(catalog_rows[0].keys())
        with (RES / "N7_STAGE2_TRIGGERS.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=t_fields)
            w.writeheader()
            w.writerows(trigger_rows)

    inj = run_injections(quiet_pool)

    # Cohorts excluding the 4 external non-master benchmarks for fair prevalence limits
    master_rows = [r for r in catalog_rows if "EXTERNAL_BENCHMARK" not in r["cohort_tags"]]
    n_master = len(master_rows)
    n_10pc = sum(1 for r in master_rows if r["within_10pc"] == "True")
    n_etz = sum(1 for r in master_rows if r["etz_qualified"] == "True")
    n_hosts = sum(1 for r in master_rows if int(r["n_exoplanets"] or 0) > 0)
    n_ell = sum(1 for r in master_rows if r["ellipsoid_180d"] == "True")
    comp_all = max(0.5, inj.get("completeness_overall_supra_threshold", 0.9))
    n_eff_master = n_master * comp_all

    def limits_dict(n_val: float) -> dict[str, float]:
        return {
            "n_eff": round(float(n_val), 4),
            "jeffreys_f95_pct": round(jeffreys_f95(n_val) * 100.0, 4),
            "uniform_f95_pct": round(uniform_f95(n_val) * 100.0, 4),
            "clopper_pearson_f95_pct": round(clopper_pearson_f95(n_val) * 100.0, 4),
        }

    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "analyzer_sha256": sha256_file(Path(__file__)),
        "stars_analyzed_total": len(catalog_rows),
        "priority_master_stars_analyzed": n_master,
        "external_benchmarks_analyzed": sum(1 for r in catalog_rows if "EXTERNAL_BENCHMARK" in r["cohort_tags"]),
        "total_valid_cadences": int(sum(r["n_valid_cadences"] for r in catalog_rows)),
        "total_sector_days": round(sum(r["baseline_days"] for r in catalog_rows), 2),
        "median_sigma_mad_ppm": round(float(np.median([r["sigma_mad_ppm"] for r in catalog_rows])), 2) if catalog_rows else 0.0,
        "cohort_counts": {
            "within_10pc": n_10pc,
            "etz_qualified": n_etz,
            "exoplanet_hosts": n_hosts,
            "ellipsoid_180d": n_ell,
        },
        "stage2_triggers_total": len(trigger_rows),
        "stage2_triggers_master": sum(1 for r in trigger_rows if "EXTERNAL_BENCHMARK" not in r["cohort_tags"]),
        "stage2_channel_counts": {
            "N7_MEGADIP": sum(1 for r in trigger_rows if r["trig_a"]),
            "N7_COHERENT_BEACON": sum(1 for r in trigger_rows if r["trig_b"]),
            "N7_SYMMETRIC_FLASH": sum(1 for r in trigger_rows if r["trig_c"]),
        },
        "injections": inj,
        "bayesian_limits_zero_eti_preliminary": {
            "all_priority_milky_way_raw": limits_dict(n_master),
            "all_priority_milky_way_eff": limits_dict(n_eff_master),
            "within_10pc": limits_dict(n_10pc),
            "etz_qualified": limits_dict(n_etz),
            "exoplanet_hosts": limits_dict(n_hosts),
            "ellipsoid_180d": limits_dict(n_ell),
        },
    }
    (RES / "N7_ANALYZER_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
