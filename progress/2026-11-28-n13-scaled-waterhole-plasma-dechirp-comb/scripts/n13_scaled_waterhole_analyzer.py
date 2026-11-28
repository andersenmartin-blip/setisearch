#!/usr/bin/env python3
"""Spor N13 — Prospective Blind-Locked Scaled 33-Star Fine Water-Hole (2.794–2.836 Hz) Analyzer v2.

Scans 24 brand-new < 9.1 pc Milky Way stars (144 remote GBT .0000.h5 scans sliced to 1,536 blocks)
and unites with N11A (9 stars / 576 blocks) into a 33-star / 198-scan / 2,112-block Water-Hole census.
Implements 3 upgraded fine-frequency blind-spot detectors vs Classical 1-bin linear (`turboSETI`-analog):
  G1: Gajjar plasma-broadened (W in {1,4,16,64,128} bins = 2.8-360 Hz)
  G2: Parabolic de-chirp v2 (w=3 bins, fine step d1=3, d2 in ±{24..48}, matched-trajectory OFF veto)
  G3: Fine spectral harmonic comb v2 (3-bin smoothed overlapping 4,096-ch FFT autocorrelation)
Benchmarked head-to-head over 1,400 real-noise trials (400 Gajjar + 400 Curved + 400 Comb + 200 Null FPR).
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n13_20261128_scaled_waterhole_plasma_dechirp_comb"
WS11A = ROOT / "analysis_workspace/work_n11a_20261128_fine_waterhole_gajjar_plasma"
INP = ROOT / "inputs_n13_20261128"
RES = WS / "results"
MANIFEST_PATH = INP / "n13_waterhole_manifest.json"
PYDEPS_N10 = ROOT / "analysis_workspace/work_n10_20261127_bl_radio_blindspot_abacad/pydeps"
if str(PYDEPS_N10) not in sys.path:
    sys.path.insert(0, str(PYDEPS_N10))

import numpy as np

BLOCK_CHANS = 16384
N_BLOCKS = 64  # 64 * 16,384 = 1,048,576 channels per slab
COARSE_CENTER_BIN = 524288
EDGE_MASK = 64
DC_MASK_HALF = 16
GBT_SEFD_JY = 10.0

G1_WIDTHS = (1, 4, 16, 64, 128)
G1_SHIFTS_FINE = (-48, -40, -32, -24, -16, -8, 0, 8, 16, 24, 32, 40, 48)
G1_SHIFTS_WIDE = (-48, -24, 0, 24, 48)
G1_CURVS = (-12, 0, 12)

G2_WIDTH = 3
G2_SHIFTS = tuple(range(-27, 28, 3))
G2_CURVS = (-48, -42, -36, -30, -24, 24, 30, 36, 42, 48)
G2_OFF_VETO = 5.5

THRESH_ALL3 = 10.0
THRESH_2OF3 = 14.0
OFF_VETO = 5.0

G3_COMB_ON_THRESH = 14.0
G3_COMB_OFF_MAX = 10.0
G3_COMB_RATIO = 2.0
CLASSICAL_THRESH = 10.0


def exact_jeffreys_f95(k: int, n_eff: float) -> float:
    from scipy.stats import beta
    if n_eff <= 0:
        return 1.0
    return float(beta.ppf(0.95, k + 0.5, max(n_eff - k + 0.5, 0.5)))


def exact_uniform_f95(k: int, n_eff: float) -> float:
    from scipy.stats import beta
    if n_eff <= 0:
        return 1.0
    return float(beta.ppf(0.95, k + 1.0, max(n_eff - k + 1.0, 1.0)))


def boxcar_1d_axis1(arr: np.ndarray, width: int) -> np.ndarray:
    if width <= 1:
        return arr
    n_t, n_f = arr.shape
    cs = np.empty((n_t, n_f + 1), dtype=np.float32)
    cs[:, 0] = 0.0
    np.cumsum(arr, axis=1, out=cs[:, 1:])
    pad_l = width // 2
    out = np.zeros_like(arr, dtype=np.float32)
    valid_w = n_f - width + 1
    if valid_w > 0:
        out[:, pad_l : pad_l + valid_w] = cs[:, width:] - cs[:, :valid_w]
    return out


def normalize_fine_block(
    raw_scans: list[np.ndarray],
    global_start: int,
) -> tuple[list[np.ndarray], np.ndarray]:
    """256-ch continuum-flattened ON-OFF normalization using B1/C1/D1 baseline."""
    n_t, n_f = raw_scans[0].shape
    idx = global_start + np.arange(n_f, dtype=np.int32)
    valid_f = (idx >= EDGE_MASK) & (idx < (1048576 - EDGE_MASK)) & (np.abs(idx - COARSE_CENTER_BIN) > DC_MASK_HALF)

    n_coarse = n_f // 256
    x_fine = np.arange(n_f, dtype=np.float32)
    flat_scans: list[np.ndarray] = []
    for arr in raw_scans:
        bad_chan = ~np.all(np.isfinite(arr) & (arr > 0.0), axis=0)
        arr_c = np.where(np.isfinite(arr) & (arr > 0.0), arr, 1.0).astype(np.float32)
        if n_coarse >= 2:
            cm = np.median(arr_c[:, : n_coarse * 256].reshape(n_t, n_coarse, 256), axis=2)
            rm = np.median(cm, axis=1, keepdims=True)
            cm = np.where(cm > 0, cm, np.where(rm > 0, rm, 1.0))
            pos = (x_fine - 127.5) / 256.0
            i0 = np.clip(np.floor(pos).astype(np.int32), 0, n_coarse - 2)
            frac = np.clip(pos - i0, 0.0, 1.0).astype(np.float32)[None, :]
            bp = cm[:, i0] * (1.0 - frac) + cm[:, i0 + 1] * frac
            rel = arr_c / np.where(bp > 0, bp, 1.0) - 1.0
        else:
            mt = np.median(arr_c, axis=1, keepdims=True)
            rel = arr_c / np.where(mt > 0, mt, 1.0) - 1.0
        if np.any(bad_chan):
            rel[:, bad_chan] = 0.0
            valid_f &= ~bad_chan
        flat_scans.append(rel)

    off_stack = np.concatenate([flat_scans[1], flat_scans[3], flat_scans[5]], axis=0)
    off_t = np.ascontiguousarray(off_stack.T)
    off_med = np.median(off_t, axis=1)
    off_mad = 1.4826 * np.median(np.abs(off_t - off_med[:, None]), axis=1)

    fin_mads = off_mad[valid_f & np.isfinite(off_mad) & (off_mad > 0)]
    if fin_mads.size < 64:
        return [np.zeros((n_t, n_f), dtype=np.float32) for _ in range(6)], np.zeros(n_f, dtype=bool)
    med_mad_blk = float(np.median(fin_mads))
    valid_f &= np.isfinite(off_med) & np.isfinite(off_mad) & (off_mad > 0.25 * med_mad_blk) & (off_mad < 6.0 * med_mad_blk)
    inv_sig = np.where(valid_f, 1.0 / np.maximum(off_mad, 0.75 * med_mad_blk), 0.0).astype(np.float32)

    z_scans: list[np.ndarray] = []
    for rel in flat_scans:
        z = (rel - off_med[None, :]) * inv_sig[None, :]
        z = np.where(np.isfinite(z) & valid_f[None, :], z, 0.0).astype(np.float32)
        if np.any(valid_f):
            z -= np.median(z[:, valid_f], axis=1, keepdims=True)
            z[:, ~valid_f] = 0.0
        z_scans.append(z)
    return z_scans, valid_f


def curved_bank_snr(
    z_scan: np.ndarray,
    width: int,
    shifts: tuple[int, ...],
    curvs: tuple[int, ...],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Exact 16-row slice summation for linear+quadratic trajectories at ~2.8 Hz resolution."""
    n_t, n_f = z_scan.shape
    bx = boxcar_1d_axis1(z_scan, width)
    pad = 80
    bx_pad = np.pad(bx, ((0, 0), (pad, pad)), mode="constant")
    u = np.linspace(-0.5, 0.5, n_t, dtype=np.float32)
    u2 = (u * u) - (1.0 / 12.0)
    norm_fac = math.sqrt(float(n_t) * float(max(width, 1)))

    acc0 = np.sum(bx_pad[:, pad : pad + n_f], axis=0) / norm_fac
    sub0 = acc0[::max(1, n_f // 512)]
    med0 = float(np.median(sub0))
    mad0 = 1.4826 * float(np.median(np.abs(sub0 - med0)))
    inv_mad0 = (1.0 / mad0) if mad0 > 0.05 else 1.0

    best_snr = np.full(n_f, -1e9, dtype=np.float32)
    best_d1 = np.zeros(n_f, dtype=np.int16)
    best_d2 = np.zeros(n_f, dtype=np.int16)
    lin_only_snr = np.full(n_f, -1e9, dtype=np.float32)

    for d2 in curvs:
        for d1 in shifts:
            df_vec = np.rint(d1 * u + d2 * 4.0 * u2).astype(np.int32)
            acc = bx_pad[0, pad + int(df_vec[0]) : pad + int(df_vec[0]) + n_f].copy()
            for t in range(1, n_t):
                k = int(df_vec[t])
                acc += bx_pad[t, pad + k : pad + k + n_f]
            snr_map = ((acc / norm_fac) - med0) * inv_mad0
            if d2 == 0:
                better_l = snr_map > lin_only_snr
                lin_only_snr = np.where(better_l, snr_map, lin_only_snr)
            better = snr_map > best_snr
            if np.any(better):
                best_snr = np.where(better, snr_map, best_snr)
                best_d1 = np.where(better, d1, best_d1)
                best_d2 = np.where(better, d2, best_d2)
    return best_snr, best_d1, best_d2, lin_only_snr


def compute_g3_comb_score_v2(z_scan: np.ndarray) -> tuple[float, int]:
    """3-bin boxcar-smoothed overlapping 4,096-ch FFT autocorrelation comb score (lags 30..1000)."""
    spec0 = np.mean(z_scan, axis=0).astype(np.float64)
    if spec0.size < 512:
        return 0.0, 0
    spec = (spec0[:-2] + spec0[1:-1] + spec0[2:]) / math.sqrt(3.0)
    n_f = spec.size
    win = min(4096, n_f)
    stride = max(512, win // 2)
    starts = list(range(0, max(1, n_f - win + 1), stride))
    if starts[-1] + win < n_f and n_f >= win:
        starts.append(n_f - win)

    best_sc, best_lag = 0.0, 0
    for st in starts:
        seg_s = spec[st : st + win].copy()
        seg_s -= float(np.mean(seg_s))
        var = float(np.mean(seg_s * seg_s))
        if var <= 1e-6:
            continue
        f1 = np.fft.rfft(seg_s)
        ac = np.fft.irfft(f1 * np.conj(f1), n=win) / (float(win) * var)
        max_lag = min(1000, win // 3)
        seg = np.abs(ac[30:max_lag])
        if seg.size < 64:
            continue
        med = float(np.median(seg))
        mad = 1.4826 * float(np.median(np.abs(seg - med))) + 1e-6
        pk_i = int(np.argmax(seg))
        sc = (float(seg[pk_i]) - med) / mad
        if sc > best_sc:
            best_sc, best_lag = sc, 30 + pk_i
    return float(best_sc), int(best_lag)


def matched_g2_off_max(z_tile: list[np.ndarray], idx: int, d1_pk: int, d2_pk: int, n_f: int) -> float:
    lo, hi = max(0, idx - 32), min(n_f, idx + 33)
    peak_vals: list[float] = []
    for si in (1, 3, 5):
        s_tr = curved_bank_snr(z_tile[si], G2_WIDTH, (d1_pk,), (d2_pk,))[0][lo:hi]
        s_st = curved_bank_snr(z_tile[si], G2_WIDTH, (0,), (0,))[0][lo:hi]
        peak_vals.append(max(float(np.max(s_tr)), float(np.max(s_st))))
    return max(peak_vals)


def evaluate_tile_all(z_tile: list[np.ndarray], include_classical: bool = True) -> dict:
    """Shared detector kernel across G1, upgraded G2 parabolic de-chirp, upgraded G3 comb + Classical 1-bin."""
    n_t, n_f = z_tile[0].shape
    g1_hit = False
    g1_best = 0.0
    g2_hit = False
    g2_best = 0.0
    cls_hit = False
    cls_best = 0.0

    for w in G1_WIDTHS:
        sh = G1_SHIFTS_FINE if w <= 4 else G1_SHIFTS_WIDE
        on_s = []
        lin_on = []
        for si in (0, 2, 4):
            s, _, _, ls = curved_bank_snr(z_tile[si], w, sh, G1_CURVS)
            on_s.append(s)
            if w == 1 and include_classical:
                lin_on.append(ls)
        on_st = np.stack(on_s, axis=0)
        min3 = np.min(on_st, axis=0)
        sec = np.sort(on_st, axis=0)[1]
        pk = int(np.argmax(np.maximum(min3, sec * 0.72)))
        s_min3, s_sec = float(min3[pk]), float(sec[pk])
        g1_best = max(g1_best, s_min3, s_sec)
        if s_min3 >= THRESH_ALL3 or s_sec >= THRESH_2OF3:
            off_s = [curved_bank_snr(z_tile[si], w, sh, G1_CURVS)[0] for si in (1, 3, 5)]
            lo, hi = max(0, pk - w - 32), min(n_f, pk + w + 33)
            if float(np.max(np.stack(off_s, axis=0)[:, lo:hi])) < OFF_VETO:
                g1_hit = True
        if w == 1 and include_classical:
            c_st = np.stack(lin_on, axis=0)
            c_min3 = np.min(c_st, axis=0)
            c_sec = np.sort(c_st, axis=0)[1]
            cpk = int(np.argmax(c_min3))
            cls_best = max(cls_best, float(c_min3[cpk]))
            if float(c_min3[cpk]) >= CLASSICAL_THRESH or float(c_sec[cpk]) >= THRESH_2OF3:
                off_c = [curved_bank_snr(z_tile[si], 1, sh, (0,))[0] for si in (1, 3, 5)]
                lo, hi = max(0, cpk - 32), min(n_f, cpk + 33)
                if float(np.max(np.stack(off_c, axis=0)[:, lo:hi])) < OFF_VETO:
                    cls_hit = True

    on_res_g2 = [curved_bank_snr(z_tile[si], G2_WIDTH, G2_SHIFTS, G2_CURVS) for si in (0, 2, 4)]
    on_st_g2 = np.stack([r[0] for r in on_res_g2], axis=0)
    min3_g2 = np.min(on_st_g2, axis=0)
    sec_g2 = np.sort(on_st_g2, axis=0)[1]
    pk_g2 = int(np.argmax(np.maximum(min3_g2, sec_g2 * 0.72)))
    g2_min3, g2_sec = float(min3_g2[pk_g2]), float(sec_g2[pk_g2])
    g2_best = max(g2_min3, g2_sec)
    if g2_min3 >= THRESH_ALL3 or g2_sec >= THRESH_2OF3:
        d1_pk, d2_pk = int(on_res_g2[0][1][pk_g2]), int(on_res_g2[0][2][pk_g2])
        if matched_g2_off_max(z_tile, pk_g2, d1_pk, d2_pk, n_f) < G2_OFF_VETO:
            g2_hit = True

    comb_on = [compute_g3_comb_score_v2(z_tile[si])[0] for si in (0, 2, 4)]
    comb_off = [compute_g3_comb_score_v2(z_tile[si])[0] for si in (1, 3, 5)]
    c_2nd = float(sorted(comb_on)[1])
    c_off_max = float(max(comb_off))
    g3_hit = (c_2nd >= G3_COMB_ON_THRESH) and (c_off_max < G3_COMB_OFF_MAX) and (c_2nd / max(c_off_max, 1.0) >= G3_COMB_RATIO)

    return {
        "g1_hit": g1_hit, "g1_snr": round(g1_best, 3),
        "g2_hit": g2_hit, "g2_snr": round(g2_best, 3),
        "g3_hit": g3_hit, "g3_comb_on2": round(c_2nd, 3), "g3_comb_off": round(c_off_max, 3),
        "classical_hit": cls_hit, "classical_snr": round(cls_best, 3),
    }


def inject_fine_signal(base: list[np.ndarray], kind: str, rng: np.random.Generator) -> tuple[list[np.ndarray], float]:
    out = [z.copy() for z in base]
    n_t, n_f = out[0].shape
    u = np.linspace(-0.5, 0.5, n_t, dtype=np.float32)
    u2 = (u * u) - (1.0 / 12.0)
    cols = np.arange(n_f, dtype=np.float32)[None, :]

    if kind == "GAJJAR_PLASMA_10_350HZ":
        f0 = float(rng.integers(250, n_f - 250))
        sig_f = float(rng.uniform(6.0, 45.0))
        d1 = float(rng.uniform(-24.0, 24.0))
        amp = float(rng.uniform(0.75, 1.25))
        fc = (f0 + d1 * u)[:, None]
        prof = amp * np.exp(-0.5 * ((cols - fc) / sig_f) ** 2).astype(np.float32)
        for si in (0, 2, 4):
            out[si] += prof
        eff = amp * math.sqrt(n_t * math.sqrt(math.pi) * sig_f)
    elif kind == "FINE_CURVED_ORBITAL":
        f0 = float(rng.integers(250, n_f - 250))
        d1 = float(rng.uniform(-24.0, 24.0))
        d2 = float(rng.choice([-1.0, 1.0]) * rng.uniform(24.0, 46.0))
        sig_f = float(rng.uniform(0.8, 1.2))
        amp = float(rng.uniform(3.8, 5.0))
        fc = (f0 + d1 * u + d2 * 4.0 * u2)[:, None]
        prof = amp * np.exp(-0.5 * ((cols - fc) / sig_f) ** 2).astype(np.float32)
        for si in (0, 2, 4):
            out[si] += prof
        eff = amp * math.sqrt(n_t * max(1.0, sig_f * 1.8))
    elif kind == "FINE_HARMONIC_COMB":
        f0 = float(rng.integers(200, n_f - 2600))
        spacing = int(rng.integers(80, 260))
        n_teeth = 10
        sig_f = 1.4
        amp = float(rng.uniform(1.6, 2.2))
        prof = np.zeros((1, n_f), dtype=np.float32)
        for k in range(n_teeth):
            prof += amp * np.exp(-0.5 * ((cols - (f0 + k * spacing)) / sig_f) ** 2).astype(np.float32)
        for si in (0, 2, 4):
            out[si] += prof
        eff = amp * math.sqrt(n_t * n_teeth * 2.0 * sig_f)
    elif kind == "NULL_NOISE_FPR":
        eff = 0.0
    else:
        raise ValueError(kind)
    return out, float(eff)


def process_one_cadence(cad: dict) -> dict:
    star = cad["target"]
    dist_pc = float(cad["dist_pc"])
    n_exo = int(cad["n_exoplanets"])
    slabs = [np.load(s["local_slab_path"], mmap_mode="r") for s in cad["scans"]]
    n_t = min(int(sl.shape[0]) for sl in slabs)
    foff = float(cad["foff_mhz"])
    f_start = float(cad["slab_f_hi_mhz"]) if foff < 0 else float(cad["slab_f_lo_mhz"])
    tsamp = float(cad["tsamp_s"])
    df_hz = abs(foff) * 1e6
    t_obs_s = float(n_t) * tsamp

    print(f"[N13] Scanning {star} ({cad['cadence_id']}, d={dist_pc:.2f}pc, df={df_hz:.3f}Hz) ...", flush=True)
    triggers: list[dict] = []
    block_diags: list[dict] = []
    quiet_pool: list[tuple[str, float, list[np.ndarray]]] = []
    cutouts: dict[str, np.ndarray] = {}
    bp_freqs: list[float] = []
    bp_rfi: list[float] = []
    valid_tot = 0
    cut_n = 0

    for blk in range(N_BLOCKS):
        c0 = blk * BLOCK_CHANS
        c1 = c0 + BLOCK_CHANS
        raw = [np.asarray(sl[:n_t, c0:c1], dtype=np.float32) for sl in slabs]
        z_scans, valid_f = normalize_fine_block(raw, c0)
        n_val = int(np.sum(valid_f))
        valid_tot += n_val
        if n_val < 512:
            continue
        freqs = f_start + foff * (c0 + np.arange(BLOCK_CHANS, dtype=np.float64))
        fc_mid = float(np.mean(freqs))
        rfi_frac = float(np.mean(np.abs(np.stack(z_scans, axis=0)[:, :, valid_f]) > 5.0))
        bp_freqs.append(fc_mid)
        bp_rfi.append(rfi_frac)

        # G1
        for w in G1_WIDTHS:
            sh = G1_SHIFTS_FINE if w <= 4 else G1_SHIFTS_WIDE
            on_res = [curved_bank_snr(z_scans[si], w, sh, G1_CURVS) for si in (0, 2, 4)]
            on_st = np.stack([r[0] for r in on_res], axis=0)
            min3 = np.min(on_st, axis=0)
            sec = np.sort(on_st, axis=0)[1]
            cmask = valid_f & ((min3 >= THRESH_ALL3) | (sec >= THRESH_2OF3))
            if np.any(cmask):
                off_st = np.stack([curved_bank_snr(z_scans[si], w, sh, G1_CURVS)[0] for si in (1, 3, 5)], axis=0)
                idxs = np.where(cmask)[0]
                order = idxs[np.argsort(-np.maximum(min3[idxs], sec[idxs]))]
                taken: list[int] = []
                sep = max(w, 32)
                for idx in order:
                    if any(abs(int(idx) - t) < sep for t in taken):
                        continue
                    lo, hi = max(0, int(idx) - w - 32), min(BLOCK_CHANS, int(idx) + w + 33)
                    off_max = float(np.max(off_st[:, lo:hi]))
                    if off_max < OFF_VETO:
                        taken.append(int(idx))
                        ck = ""
                        if cut_n < 20:
                            plo = max(0, int(idx) - 128)
                            phi = min(BLOCK_CHANS, plo + 256)
                            plo = phi - 256
                            ck = f"TRIG_{star}_G1_{freqs[idx]:.6f}".replace(".", "_")
                            cutouts[ck] = np.stack([z[:, plo:phi] for z in z_scans], axis=0)
                            cut_n += 1
                        triggers.append({
                            "star": star, "block": blk, "dist_pc": dist_pc, "channel": "G1_GAJJAR_PLASMA_BROADENED",
                            "global_ch": c0 + int(idx), "freq_mhz": round(float(freqs[idx]), 7),
                            "width_bins": w, "d1_bins": int(on_res[0][1][idx]), "d2_bins": int(on_res[0][2][idx]),
                            "snr_a1": round(float(on_st[0, idx]), 3), "snr_a2": round(float(on_st[1, idx]), 3),
                            "snr_a3": round(float(on_st[2, idx]), 3), "snr_on_min3": round(float(min3[idx]), 3),
                            "snr_on_2nd": round(float(sec[idx]), 3), "snr_off_max": round(off_max, 3),
                            "comb_lag_bins": 0, "cutout_key": ck,
                        })

        # G2 upgraded parabolic de-chirp
        on_res_g2 = [curved_bank_snr(z_scans[si], G2_WIDTH, G2_SHIFTS, G2_CURVS) for si in (0, 2, 4)]
        on_st_g2 = np.stack([r[0] for r in on_res_g2], axis=0)
        min3_g2 = np.min(on_st_g2, axis=0)
        sec_g2 = np.sort(on_st_g2, axis=0)[1]
        cmask_g2 = valid_f & ((min3_g2 >= THRESH_ALL3) | (sec_g2 >= THRESH_2OF3))
        if np.any(cmask_g2):
            idxs = np.where(cmask_g2)[0]
            order = idxs[np.argsort(-np.maximum(min3_g2[idxs], sec_g2[idxs]))]
            taken_g2: list[int] = []
            for idx in order:
                if any(abs(int(idx) - t) < 32 for t in taken_g2):
                    continue
                d1_pk, d2_pk = int(on_res_g2[0][1][idx]), int(on_res_g2[0][2][idx])
                off_max = matched_g2_off_max(z_scans, int(idx), d1_pk, d2_pk, BLOCK_CHANS)
                if off_max < G2_OFF_VETO:
                    taken_g2.append(int(idx))
                    ck = ""
                    if cut_n < 20:
                        plo = max(0, int(idx) - 128)
                        phi = min(BLOCK_CHANS, plo + 256)
                        plo = phi - 256
                        ck = f"TRIG_{star}_G2_{freqs[idx]:.6f}".replace(".", "_")
                        cutouts[ck] = np.stack([z[:, plo:phi] for z in z_scans], axis=0)
                        cut_n += 1
                    triggers.append({
                        "star": star, "block": blk, "dist_pc": dist_pc, "channel": "G2_PARABOLIC_DECHIRP",
                        "global_ch": c0 + int(idx), "freq_mhz": round(float(freqs[idx]), 7),
                        "width_bins": G2_WIDTH, "d1_bins": d1_pk, "d2_bins": d2_pk,
                        "snr_a1": round(float(on_st_g2[0, idx]), 3), "snr_a2": round(float(on_st_g2[1, idx]), 3),
                        "snr_a3": round(float(on_st_g2[2, idx]), 3), "snr_on_min3": round(float(min3_g2[idx]), 3),
                        "snr_on_2nd": round(float(sec_g2[idx]), 3), "snr_off_max": round(off_max, 3),
                        "comb_lag_bins": 0, "cutout_key": ck,
                    })

        # G3 upgraded Comb v2
        comb_res = [compute_g3_comb_score_v2(z_scans[si]) for si in range(6)]
        on_c = [comb_res[si][0] for si in (0, 2, 4)]
        off_c = [comb_res[si][0] for si in (1, 3, 5)]
        c_2nd = float(sorted(on_c)[1])
        c_off = float(max(off_c))
        block_diags.append({
            "star": star, "block": blk, "freq_center_mhz": round(fc_mid, 5),
            "rfi_5sig_pct": round(100.0 * rfi_frac, 4),
            "comb_on2": round(c_2nd, 3), "comb_off_max": round(c_off, 3),
        })
        if c_2nd >= G3_COMB_ON_THRESH and c_off < G3_COMB_OFF_MAX and (c_2nd / max(c_off, 1.0) >= G3_COMB_RATIO):
            triggers.append({
                "star": star, "block": blk, "dist_pc": dist_pc, "channel": "G3_FINE_SPECTRAL_COMB_V2",
                "global_ch": c0 + BLOCK_CHANS // 2, "freq_mhz": round(fc_mid, 6),
                "width_bins": BLOCK_CHANS, "d1_bins": 0, "d2_bins": 0,
                "snr_a1": round(on_c[0], 3), "snr_a2": round(on_c[1], 3), "snr_a3": round(on_c[2], 3),
                "snr_on_min3": round(min(on_c), 3), "snr_on_2nd": round(c_2nd, 3), "snr_off_max": round(c_off, 3),
                "comb_lag_bins": comb_res[0][1], "cutout_key": "",
            })

        if len(quiet_pool) < 6 and blk % 3 == 1 and rfi_frac < 0.002 and c_2nd < 8.5 and c_off < 8.5 and abs(c0 + BLOCK_CHANS // 2 - COARSE_CENTER_BIN) > 16384:
            quiet_pool.append((star, fc_mid, [z[:, 4096:8192].copy() for z in z_scans]))

    cutouts[f"BP_FREQ_{star}"] = np.array(bp_freqs, dtype=np.float32)
    cutouts[f"BP_RFI_{star}"] = np.array(bp_rfi, dtype=np.float32)

    d_m = dist_pc * 3.0856775814913673e16
    s_w1 = 10.0 * GBT_SEFD_JY / math.sqrt(2.0 * df_hz * t_obs_s)
    eirp_w1 = 4.0 * math.pi * (d_m ** 2) * (s_w1 * 1e-26) * df_hz
    s_w16 = 10.0 * GBT_SEFD_JY / math.sqrt(2.0 * (df_hz * 16.0) * t_obs_s)
    eirp_w16 = 4.0 * math.pi * (d_m ** 2) * (s_w16 * 1e-26) * (df_hz * 16.0)
    s_w64 = 10.0 * GBT_SEFD_JY / math.sqrt(2.0 * (df_hz * 64.0) * t_obs_s)
    eirp_w64 = 4.0 * math.pi * (d_m ** 2) * (s_w64 * 1e-26) * (df_hz * 64.0)

    c_sum = {
        "star": star, "common_name": cad.get("common_name", star), "sp_type": cad.get("sp_type", ""),
        "cadence_id": cad["cadence_id"], "dist_pc": round(dist_pc, 4), "n_exoplanets": n_exo,
        "bridge_tracks": cad.get("bridge_tracks", ""),
        "n_time": n_t, "tsamp_s": round(tsamp, 4), "t_obs_s": round(t_obs_s, 2), "df_hz": round(df_hz, 4),
        "bw_clean_mhz": round(float(valid_tot) * abs(foff), 4), "blocks_clean": len(block_diags),
        "mean_rfi_5sig_pct": round(100.0 * float(np.mean(bp_rfi)), 5) if bp_rfi else 0.0,
        "s_min_10sig_w1_jy": round(s_w1, 4), "eirp_w1_gw": round(eirp_w1 / 1e9, 4),
        "eirp_w16_45hz_gw": round(eirp_w16 / 1e9, 4), "eirp_w64_179hz_gw": round(eirp_w64 / 1e9, 4),
        "g1_triggers": sum(1 for t in triggers if t["channel"] == "G1_GAJJAR_PLASMA_BROADENED"),
        "g2_triggers": sum(1 for t in triggers if t["channel"] == "G2_PARABOLIC_DECHIRP"),
        "g3_triggers": sum(1 for t in triggers if t["channel"] == "G3_FINE_SPECTRAL_COMB_V2"),
        "total_triggers": len(triggers),
    }
    print(f"  -> {star}: BW={c_sum['bw_clean_mhz']:.3f} MHz, EIRP_w1={c_sum['eirp_w1_gw']:.2f} GW, trig={len(triggers)}", flush=True)
    return {"summary": c_sum, "triggers": triggers, "diags": block_diags, "quiet": quiet_pool, "cutouts": cutouts}


def run_bench_worker(args: tuple[str, int, list, int]) -> tuple[str, dict, list[dict], np.ndarray | None]:
    kind, n_trials, pool, seed = args
    rng = np.random.default_rng(seed)
    n_hit = n_cls = g1_h = g2_h = g3_h = 0
    rows: list[dict] = []
    rep = None
    for tr in range(n_trials):
        st, fq, base = pool[(tr * 7 + len(kind)) % len(pool)]
        inj, eff = inject_fine_signal(base, kind, rng)
        ev = evaluate_tile_all(inj, include_classical=True)
        hit = bool(ev["g1_hit"] or ev["g2_hit"] or ev["g3_hit"])
        if ev["g1_hit"]: g1_h += 1
        if ev["g2_hit"]: g2_h += 1
        if ev["g3_hit"]: g3_h += 1
        if hit: n_hit += 1
        if ev["classical_hit"]: n_cls += 1
        if tr == 5 and kind != "NULL_NOISE_FPR":
            rep = np.stack([s[:, :600] for s in inj], axis=0).astype(np.float32)
        rows.append({
            "trial_id": f"{kind}_{tr:03d}", "morphology": kind, "host_noise": st, "freq_mhz": round(fq, 4),
            "eff_snr_injected": round(eff, 2), "n13_detected": int(hit), "classical_1bin_detected": int(ev["classical_hit"]),
            "g1_hit": int(ev["g1_hit"]), "g2_hit": int(ev["g2_hit"]), "g3_hit": int(ev["g3_hit"]),
            "g1_snr": ev["g1_snr"], "g2_snr": ev["g2_snr"], "g3_comb": ev["g3_comb_on2"], "classical_snr": ev["classical_snr"],
        })
    b_sum = {
        "trials": n_trials, "n13_positive": n_hit, "n13_rate": round(n_hit / float(n_trials), 4),
        "classical_1bin_positive": n_cls, "classical_1bin_rate": round(n_cls / float(n_trials), 4),
        "g1_hits": g1_h, "g2_hits": g2_h, "g3_hits": g3_h,
    }
    print(f"  [BENCH {kind:22s}] N13={n_hit}/{n_trials} ({100*n_hit/n_trials:5.2f}%) vs Classical={n_cls}/{n_trials} ({100*n_cls/n_trials:5.2f}%)", flush=True)
    return kind, b_sum, rows, rep


def main() -> int:
    t0 = time.time()
    RES.mkdir(parents=True, exist_ok=True)
    man = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    s11a = json.loads((WS11A / "results/N11A_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))

    n_workers = min(6, max(2, os.cpu_count() or 4))
    cad_sums, triggers, diags, quiet_pool = [], [], [], []
    cutouts: dict[str, np.ndarray] = {}
    with ProcessPoolExecutor(max_workers=n_workers) as ex:
        for res in ex.map(process_one_cadence, man["cadences"]):
            cad_sums.append(res["summary"])
            triggers.extend(res["triggers"])
            diags.extend(res["diags"])
            quiet_pool.extend(res["quiet"])
            cutouts.update(res["cutouts"])

    print(f"[N13] Running 1,400-trial head-to-head benchmark (pool={len(quiet_pool)}) ...", flush=True)
    if len(quiet_pool) < 16:
        raise RuntimeError(f"Too few quiet tiles: {len(quiet_pool)}")
    specs = [
        ("GAJJAR_PLASMA_10_350HZ", 400, 2026112813),
        ("FINE_CURVED_ORBITAL", 400, 2026112814),
        ("FINE_HARMONIC_COMB", 400, 2026112815),
        ("NULL_NOISE_FPR", 200, 2026112816),
    ]
    bench_summary: dict[str, dict] = {}
    inj_rows: list[dict] = []
    with ProcessPoolExecutor(max_workers=min(4, n_workers)) as ex:
        for kind, b_sum, rows, rep in ex.map(run_bench_worker, [(k, nt, quiet_pool, sd) for k, nt, sd in specs]):
            bench_summary[kind] = b_sum
            inj_rows.extend(rows)
            if rep is not None:
                cutouts[f"INJ_{kind}"] = rep

    with (RES / "N13_CADENCE_SUMMARY.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cad_sums[0].keys())); w.writeheader(); w.writerows(cad_sums)

    tfields = [
        "star", "block", "dist_pc", "channel", "global_ch", "freq_mhz", "width_bins", "d1_bins", "d2_bins",
        "snr_a1", "snr_a2", "snr_a3", "snr_on_min3", "snr_on_2nd", "snr_off_max", "comb_lag_bins", "cutout_key",
    ]
    with (RES / "N13_STAGE2_TRIGGERS.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=tfields); w.writeheader(); w.writerows(triggers)

    with (RES / "N13_INJECTION_BENCHMARK.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(inj_rows[0].keys())); w.writeheader(); w.writerows(inj_rows)

    with (RES / "N13_BLOCK_DIAGNOSTICS.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(diags[0].keys())); w.writeheader(); w.writerows(diags)

    np.savez_compressed(RES / "n13_cutouts.npz", **cutouts)

    sig_classes = ("GAJJAR_PLASMA_10_350HZ", "FINE_CURVED_ORBITAL", "FINE_HARMONIC_COMB")
    mean_n13 = sum(bench_summary[k]["n13_rate"] for k in sig_classes) / 3.0
    mean_cls = sum(bench_summary[k]["classical_1bin_rate"] for k in sig_classes) / 3.0
    null_fpr = bench_summary["NULL_NOISE_FPR"]["n13_rate"]

    n_stars = len(cad_sums)
    n_eff_n13 = float(n_stars) * mean_n13
    n_blk_n13 = sum(c["blocks_clean"] for c in cad_sums)
    n_eff_blk_n13 = float(n_blk_n13) * mean_n13

    n11a_stars = int(s11a["stars_analyzed"])
    n11a_eff_stars = float(s11a["bayesian_zero_eti_bounds"]["stars_eff"]["n_eff"])
    n11a_blks = int(s11a["blocks_clean_total"])
    n11a_eff_blks = float(s11a["bayesian_zero_eti_bounds"]["star_blocks_eff"]["n_eff"])

    uni_stars_raw = n_stars + n11a_stars
    uni_stars_eff = n_eff_n13 + n11a_eff_stars
    uni_blks_raw = n_blk_n13 + n11a_blks
    uni_blks_eff = n_eff_blk_n13 + n11a_eff_blks

    def bounds_dict(n_eff: float) -> dict:
        return {
            "n_eff": round(n_eff, 3),
            "jeffreys_f95_pct": round(100.0 * exact_jeffreys_f95(0, n_eff), 4),
            "uniform_f95_pct": round(100.0 * exact_uniform_f95(0, n_eff), 4),
        }

    summary = {
        "campaign": "SPOR_N13_SCALED_33STAR_WATERHOLE_PLASMA_DECHIRP_COMB",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": round(time.time() - t0, 2),
        "stars_analyzed": n_stars,
        "remote_hdf5_scans_sliced": n_stars * 6,
        "unified_stars_total": uni_stars_raw,
        "unified_scans_total": (n_stars + n11a_stars) * 6,
        "freq_band_mhz": [round(float(min(c["slab_f_lo_mhz"] for c in man["cadences"])), 4), round(float(max(c["slab_f_hi_mhz"] for c in man["cadences"])), 4)],
        "freq_resolution_hz_range": [round(float(min(c["df_hz"] for c in cad_sums)), 4), round(float(max(c["df_hz"] for c in cad_sums)), 4)],
        "blocks_clean_total": n_blk_n13,
        "unified_blocks_clean_total": uni_blks_raw,
        "total_clean_bw_mhz": round(sum(c["bw_clean_mhz"] for c in cad_sums), 4),
        "unified_clean_bw_mhz": round(sum(c["bw_clean_mhz"] for c in cad_sums) + float(s11a["total_clean_bw_mhz"]), 4),
        "min_eirp_w1_gw": round(float(min(c["eirp_w1_gw"] for c in cad_sums)), 4),
        "median_eirp_w1_gw": round(float(np.median([c["eirp_w1_gw"] for c in cad_sums])), 3),
        "median_eirp_w16_45hz_gw": round(float(np.median([c["eirp_w16_45hz_gw"] for c in cad_sums])), 3),
        "median_eirp_w64_179hz_gw": round(float(np.median([c["eirp_w64_179hz_gw"] for c in cad_sums])), 3),
        "stage2_triggers_total": len(triggers),
        "stage2_by_channel": {k: sum(1 for t in triggers if t["channel"] == k) for k in ("G1_GAJJAR_PLASMA_BROADENED", "G2_PARABOLIC_DECHIRP", "G3_FINE_SPECTRAL_COMB_V2")},
        "injections": {
            "trials_total": len(inj_rows),
            "signal_trials": 1200,
            "null_fpr_trials": 200,
            "n13_mean_completeness": round(mean_n13, 4),
            "classical_1bin_completeness": round(mean_cls, 4),
            "null_fpr": round(null_fpr, 4),
            "per_morphology": bench_summary,
        },
        "provisional_zero_eti_bayesian_bounds": {
            "n13_stars_raw_24": bounds_dict(float(n_stars)),
            "n13_stars_eff": bounds_dict(n_eff_n13),
            "n13_blocks_eff": bounds_dict(n_eff_blk_n13),
            "unified_33stars_raw": bounds_dict(float(uni_stars_raw)),
            "unified_33stars_eff": bounds_dict(uni_stars_eff),
            "unified_2112blocks_raw": bounds_dict(float(uni_blks_raw)),
            "unified_2112blocks_eff": bounds_dict(uni_blks_eff),
        },
        "external_contacts": 0,
    }
    (RES / "N13_ANALYZER_SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[N13] Done in {summary['elapsed_s']}s. Triggers={len(triggers)}, Mean={100*mean_n13:.2f}% vs Cls={100*mean_cls:.2f}%", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
