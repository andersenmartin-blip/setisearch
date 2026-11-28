#!/usr/bin/env python3
"""Spor N11A — Prospective Blind-Locked Fine Water-Hole (2.794 Hz) Gajjar Plasma-Broadening Analyzer.

Operates on aligned 1,048,576-channel (2.9297 MHz, 1422.363-1425.293 MHz,
df = 2.79397 Hz, 16 time steps x 18.25s) ABACAD GBT .0000.h5 Water-Hole slabs
for 9 < 6 pc Milky Way M-dwarfs (54 real 15.7 GB scans sliced via HTTP Range).
Implements 3 fine-frequency detectors + classical 1-bin linear baseline:
  G1: Gajjar plasma-broadened (W in {1,4,16,64,128} bins = 2.8-358 Hz) + moderate drift
  G2: High-curvature orbital/acceleration drift (d2 in +/-{24,36,48} bins)
  G3: Fine spectral harmonic comb (1D FFT autocorrelation, lag 20-4000 bins)
Benchmarked head-to-head against Classical 1-Bin Linear (`turboSETI`-analog) over 1,200 trials.
"""
from __future__ import annotations

import csv
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n11a_20261128_fine_waterhole_gajjar_plasma"
INP = ROOT / "inputs_n11a_20261128"
RES = WS / "results"
MANIFEST_PATH = INP / "n11a_waterhole_manifest.json"
PYDEPS_N10 = ROOT / "analysis_workspace/work_n10_20261127_bl_radio_blindspot_abacad/pydeps"
if str(PYDEPS_N10) not in sys.path:
    sys.path.insert(0, str(PYDEPS_N10))

import numpy as np

BLOCK_CHANS = 16384
N_BLOCKS = 64  # 64 * 16384 = 1,048,576 channels
COARSE_CENTER_BIN = 524288
EDGE_MASK = 64
DC_MASK_HALF = 16
GBT_SEFD_JY = 10.0

G1_WIDTHS = (1, 4, 16, 64, 128)
G1_SHIFTS_FINE = (-48, -40, -32, -24, -16, -8, 0, 8, 16, 24, 32, 40, 48)
G1_SHIFTS_WIDE = (-48, -24, 0, 24, 48)
G1_CURVS = (-12, 0, 12)

G2_WIDTHS = (1, 4)
G2_SHIFTS = (-32, -16, 0, 16, 32)
G2_CURVS = (-48, -36, -24, 24, 36, 48)

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
    """Exact 16-row slice summation for linear+quadratic trajectories at 2.794 Hz resolution."""
    n_t, n_f = z_scan.shape
    bx = boxcar_1d_axis1(z_scan, width)
    pad = 80
    bx_pad = np.pad(bx, ((0, 0), (pad, pad)), mode="constant")
    u = np.linspace(-0.5, 0.5, n_t, dtype=np.float32)
    u2 = (u * u) - (1.0 / 12.0)
    norm_fac = math.sqrt(float(n_t) * float(max(width, 1)))

    # Empirical MAD calibration once on zero-drift trajectory
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


def compute_g3_comb_score(z_scan: np.ndarray) -> tuple[float, int]:
    """Normalized 1D FFT harmonic comb score across lags 20..4000 bins (56 Hz..11.2 kHz)."""
    spec = np.mean(z_scan, axis=0).astype(np.float64)
    n_f = spec.size
    spec -= float(np.mean(spec))
    var = float(np.mean(spec * spec))
    if var <= 1e-6:
        return 0.0, 0
    f1 = np.fft.rfft(spec)
    ac = np.fft.irfft(f1 * np.conj(f1), n=n_f) / (float(n_f) * var)
    max_lag = min(4000, n_f // 3)
    seg = np.abs(ac[20:max_lag])
    if seg.size < 64:
        return 0.0, 0
    med = float(np.median(seg))
    mad = 1.4826 * float(np.median(np.abs(seg - med))) + 1e-6
    pk_i = int(np.argmax(seg))
    score = (float(seg[pk_i]) - med) / mad
    return float(score), int(20 + pk_i)


def evaluate_tile_all(z_tile: list[np.ndarray], include_classical: bool = True) -> dict:
    """Shared detector kernel across G1, G2, G3 + Classical 1-bin linear baseline."""
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

    for w in G2_WIDTHS:
        on_s = [curved_bank_snr(z_tile[si], w, G2_SHIFTS, G2_CURVS)[0] for si in (0, 2, 4)]
        on_st = np.stack(on_s, axis=0)
        min3 = np.min(on_st, axis=0)
        sec = np.sort(on_st, axis=0)[1]
        pk = int(np.argmax(np.maximum(min3, sec * 0.72)))
        s_min3, s_sec = float(min3[pk]), float(sec[pk])
        g2_best = max(g2_best, s_min3, s_sec)
        if s_min3 >= THRESH_ALL3 or s_sec >= THRESH_2OF3:
            off_s = [curved_bank_snr(z_tile[si], w, G2_SHIFTS, G2_CURVS)[0] for si in (1, 3, 5)]
            lo, hi = max(0, pk - w - 32), min(n_f, pk + w + 33)
            if float(np.max(np.stack(off_s, axis=0)[:, lo:hi])) < OFF_VETO:
                g2_hit = True

    comb_on = [compute_g3_comb_score(z_tile[si])[0] for si in (0, 2, 4)]
    comb_off = [compute_g3_comb_score(z_tile[si])[0] for si in (1, 3, 5)]
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
        sig_f = float(rng.uniform(6.0, 45.0))  # FWHM ~40..300 Hz at 2.794 Hz/bin
        d1 = float(rng.uniform(-24.0, 24.0))
        amp = float(rng.uniform(0.75, 1.25))  # 1-bin sums to ~3.0-5.0 sigma (missed!), W=16..128 sums to ~16-40 sigma
        fc = (f0 + d1 * u)[:, None]
        prof = amp * np.exp(-0.5 * ((cols - fc) / sig_f) ** 2).astype(np.float32)
        for si in (0, 2, 4):
            out[si] += prof
        eff = amp * math.sqrt(n_t * math.sqrt(math.pi) * sig_f)
    elif kind == "FINE_CURVED_ORBITAL":
        f0 = float(rng.integers(250, n_f - 250))
        d1 = float(rng.uniform(-24.0, 24.0))
        d2 = float(rng.choice([-1.0, 1.0]) * rng.uniform(24.0, 46.0))
        sig_f = float(rng.uniform(0.7, 1.1))
        amp = float(rng.uniform(2.7, 3.8))  # Linear track smears 24-46 bins (~5 sigma missed), G2 hits ~12-16 sigma
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
        amp = float(rng.uniform(1.6, 2.2))  # Single tooth ~6-8 sigma (<10 missed), 10-tooth comb AC hits >20 sigma
        prof = np.zeros((1, n_f), dtype=np.float32)
        for k in range(n_teeth):
            prof += amp * np.exp(-0.5 * ((cols - (f0 + k * spacing)) / sig_f) ** 2).astype(np.float32)
        for si in (0, 2, 4):
            out[si] += prof
        eff = amp * math.sqrt(n_t * n_teeth * 2.0 * sig_f)
    else:
        raise ValueError(kind)
    return out, float(eff)


def process_one_cadence(cad: dict) -> dict:
    star = cad["target"]
    dist_pc = float(cad["dist_pc"])
    n_exo = int(cad["n_exoplanets"])
    slabs = [np.load(s["local_slab_path"], mmap_mode="r") for s in cad["scans"]]
    n_t = min(int(sl.shape[0]) for sl in slabs)
    foff = float(cad["foff_mhz"])  # ~ -2.79397e-6
    f_start = float(cad["slab_f_hi_mhz"]) if foff < 0 else float(cad["slab_f_lo_mhz"])
    tsamp = float(cad["tsamp_s"])
    df_hz = abs(foff) * 1e6
    t_obs_s = float(n_t) * tsamp

    print(f"[N11A] Scanning {star} ({cad['cadence_id']}, d={dist_pc:.2f}pc, df={df_hz:.3f}Hz) ...", flush=True)
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
                        if cut_n < 10:
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

        # G2
        for w in G2_WIDTHS:
            on_res = [curved_bank_snr(z_scans[si], w, G2_SHIFTS, G2_CURVS) for si in (0, 2, 4)]
            on_st = np.stack([r[0] for r in on_res], axis=0)
            min3 = np.min(on_st, axis=0)
            sec = np.sort(on_st, axis=0)[1]
            cmask = valid_f & ((min3 >= THRESH_ALL3) | (sec >= THRESH_2OF3))
            if np.any(cmask):
                off_st = np.stack([curved_bank_snr(z_scans[si], w, G2_SHIFTS, G2_CURVS)[0] for si in (1, 3, 5)], axis=0)
                idxs = np.where(cmask)[0]
                order = idxs[np.argsort(-np.maximum(min3[idxs], sec[idxs]))]
                taken = []
                for idx in order:
                    if any(abs(int(idx) - t) < 32 for t in taken):
                        continue
                    lo, hi = max(0, int(idx) - w - 32), min(BLOCK_CHANS, int(idx) + w + 33)
                    off_max = float(np.max(off_st[:, lo:hi]))
                    if off_max < OFF_VETO:
                        taken.append(int(idx))
                        triggers.append({
                            "star": star, "block": blk, "dist_pc": dist_pc, "channel": "G2_FINE_CURVED_DRIFT",
                            "global_ch": c0 + int(idx), "freq_mhz": round(float(freqs[idx]), 7),
                            "width_bins": w, "d1_bins": int(on_res[0][1][idx]), "d2_bins": int(on_res[0][2][idx]),
                            "snr_a1": round(float(on_st[0, idx]), 3), "snr_a2": round(float(on_st[1, idx]), 3),
                            "snr_a3": round(float(on_st[2, idx]), 3), "snr_on_min3": round(float(min3[idx]), 3),
                            "snr_on_2nd": round(float(sec[idx]), 3), "snr_off_max": round(off_max, 3),
                            "comb_lag_bins": 0, "cutout_key": "",
                        })

        # G3 Comb
        comb_res = [compute_g3_comb_score(z_scans[si]) for si in range(6)]
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
                "star": star, "block": blk, "dist_pc": dist_pc, "channel": "G3_FINE_SPECTRAL_COMB",
                "global_ch": c0 + BLOCK_CHANS // 2, "freq_mhz": round(fc_mid, 6),
                "width_bins": BLOCK_CHANS, "d1_bins": 0, "d2_bins": 0,
                "snr_a1": round(on_c[0], 3), "snr_a2": round(on_c[1], 3), "snr_a3": round(on_c[2], 3),
                "snr_on_min3": round(min(on_c), 3), "snr_on_2nd": round(c_2nd, 3), "snr_off_max": round(c_off, 3),
                "comb_lag_bins": comb_res[0][1], "cutout_key": "",
            })

        if len(quiet_pool) < 25 and blk % 2 == 1 and rfi_frac < 0.002 and c_2nd < 9.0 and c_off < 9.0 and abs(c0 + BLOCK_CHANS // 2 - COARSE_CENTER_BIN) > 16384:
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
        "star": star, "cadence_id": cad["cadence_id"], "dist_pc": round(dist_pc, 4), "n_exoplanets": n_exo,
        "n_time": n_t, "tsamp_s": round(tsamp, 4), "t_obs_s": round(t_obs_s, 2), "df_hz": round(df_hz, 4),
        "bw_clean_mhz": round(float(valid_tot) * abs(foff), 4), "blocks_clean": len(block_diags),
        "mean_rfi_5sig_pct": round(100.0 * float(np.mean(bp_rfi)), 5) if bp_rfi else 0.0,
        "s_min_10sig_w1_jy": round(s_w1, 4), "eirp_w1_gw": round(eirp_w1 / 1e9, 4),
        "eirp_w16_45hz_gw": round(eirp_w16 / 1e9, 4), "eirp_w64_179hz_gw": round(eirp_w64 / 1e9, 4),
        "g1_triggers": sum(1 for t in triggers if t["channel"] == "G1_GAJJAR_PLASMA_BROADENED"),
        "g2_triggers": sum(1 for t in triggers if t["channel"] == "G2_FINE_CURVED_DRIFT"),
        "g3_triggers": sum(1 for t in triggers if t["channel"] == "G3_FINE_SPECTRAL_COMB"),
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
        st, fq, base = pool[(tr * 5 + len(kind)) % len(pool)]
        inj, eff = inject_fine_signal(base, kind, rng)
        ev = evaluate_tile_all(inj, include_classical=True)
        hit = bool(ev["g1_hit"] or ev["g2_hit"] or ev["g3_hit"])
        if ev["g1_hit"]: g1_h += 1
        if ev["g2_hit"]: g2_h += 1
        if ev["g3_hit"]: g3_h += 1
        if hit: n_hit += 1
        if ev["classical_hit"]: n_cls += 1
        if tr == 5:
            rep = np.stack([s[:, :600] for s in inj], axis=0).astype(np.float32)
        rows.append({
            "trial_id": f"{kind}_{tr:03d}", "morphology": kind, "host_noise": st, "freq_mhz": round(fq, 4),
            "eff_snr_injected": round(eff, 2), "n11a_detected": int(hit), "classical_1bin_detected": int(ev["classical_hit"]),
            "g1_hit": int(ev["g1_hit"]), "g2_hit": int(ev["g2_hit"]), "g3_hit": int(ev["g3_hit"]),
            "g1_snr": ev["g1_snr"], "g2_snr": ev["g2_snr"], "g3_comb": ev["g3_comb_on2"], "classical_snr": ev["classical_snr"],
        })
    b_sum = {
        "trials": n_trials, "n11a_recovered": n_hit, "n11a_rate": round(n_hit / float(n_trials), 4),
        "classical_1bin_recovered": n_cls, "classical_1bin_rate": round(n_cls / float(n_trials), 4),
        "g1_hits": g1_h, "g2_hits": g2_h, "g3_hits": g3_h,
    }
    print(f"  [BENCH {kind:22s}] N11A={n_hit}/{n_trials} ({100*n_hit/n_trials:5.1f}%) vs Classical={n_cls}/{n_trials} ({100*n_cls/n_trials:5.1f}%)", flush=True)
    return kind, b_sum, rows, rep


def main() -> int:
    t0 = time.time()
    RES.mkdir(parents=True, exist_ok=True)
    man = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    cad_sums, triggers, diags, quiet_pool = [], [], [], []
    cutouts: dict[str, np.ndarray] = {}
    with ProcessPoolExecutor(max_workers=4) as ex:
        for res in ex.map(process_one_cadence, man["cadences"]):
            cad_sums.append(res["summary"])
            triggers.extend(res["triggers"])
            diags.extend(res["diags"])
            quiet_pool.extend(res["quiet"])
            cutouts.update(res["cutouts"])

    print(f"[N11A] Running 1,200-trial head-to-head benchmark (pool={len(quiet_pool)}) ...", flush=True)
    if len(quiet_pool) < 10:
        raise RuntimeError(f"Too few quiet tiles: {len(quiet_pool)}")
    classes = ("GAJJAR_PLASMA_10_350HZ", "FINE_CURVED_ORBITAL", "FINE_HARMONIC_COMB")
    bench_summary: dict[str, dict] = {}
    inj_rows: list[dict] = []
    with ProcessPoolExecutor(max_workers=3) as ex:
        for kind, b_sum, rows, rep in ex.map(run_bench_worker, [(k, 400, quiet_pool, 2026112811 + i) for i, k in enumerate(classes)]):
            bench_summary[kind] = b_sum
            inj_rows.extend(rows)
            if rep is not None:
                cutouts[f"INJ_{kind}"] = rep

    with (RES / "N11A_CADENCE_SUMMARY.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cad_sums[0].keys())); w.writeheader(); w.writerows(cad_sums)

    tfields = [
        "star", "block", "dist_pc", "channel", "global_ch", "freq_mhz", "width_bins", "d1_bins", "d2_bins",
        "snr_a1", "snr_a2", "snr_a3", "snr_on_min3", "snr_on_2nd", "snr_off_max", "comb_lag_bins", "cutout_key",
    ]
    with (RES / "N11A_STAGE2_TRIGGERS.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=tfields); w.writeheader(); w.writerows(triggers)

    with (RES / "N11A_INJECTION_BENCHMARK.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(inj_rows[0].keys())); w.writeheader(); w.writerows(inj_rows)

    with (RES / "N11A_BLOCK_DIAGNOSTICS.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(diags[0].keys())); w.writeheader(); w.writerows(diags)

    np.savez_compressed(RES / "n11a_cutouts.npz", **cutouts)

    mean_n11a = sum(b["n11a_rate"] for b in bench_summary.values()) / 3.0
    mean_cls = sum(b["classical_1bin_rate"] for b in bench_summary.values()) / 3.0
    n_stars = len(cad_sums)
    n_eff = float(n_stars) * mean_n11a
    n_blk_tot = sum(c["blocks_clean"] for c in cad_sums)
    n_eff_blk = float(n_blk_tot) * mean_n11a

    summary = {
        "campaign": "SPOR_N11A_FINE_WATERHOLE_GAJJAR_PLASMA",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": round(time.time() - t0, 2),
        "stars_analyzed": n_stars,
        "remote_hdf5_scans_sliced": n_stars * 6,
        "freq_band_mhz": [round(float(man["cadences"][0]["slab_f_lo_mhz"]), 4), round(float(man["cadences"][0]["slab_f_hi_mhz"]), 4)],
        "freq_resolution_hz": round(float(cad_sums[0]["df_hz"]), 4),
        "blocks_clean_total": n_blk_tot,
        "total_clean_bw_mhz": round(sum(c["bw_clean_mhz"] for c in cad_sums), 4),
        "median_eirp_w1_gw": round(float(np.median([c["eirp_w1_gw"] for c in cad_sums])), 3),
        "median_eirp_w16_45hz_gw": round(float(np.median([c["eirp_w16_45hz_gw"] for c in cad_sums])), 3),
        "median_eirp_w64_179hz_gw": round(float(np.median([c["eirp_w64_179hz_gw"] for c in cad_sums])), 3),
        "stage2_triggers_total": len(triggers),
        "stage2_by_channel": {k: sum(1 for t in triggers if t["channel"] == k) for k in ("G1_GAJJAR_PLASMA_BROADENED", "G2_FINE_CURVED_DRIFT", "G3_FINE_SPECTRAL_COMB")},
        "injections": {"trials_total": len(inj_rows), "n11a_mean_completeness": round(mean_n11a, 4), "classical_1bin_completeness": round(mean_cls, 4), "per_morphology": bench_summary},
        "bayesian_zero_eti_bounds": {
            "stars_raw": {"n": n_stars, "jeffreys_f95_pct": round(100.0 * exact_jeffreys_f95(0, n_stars), 4), "uniform_f95_pct": round(100.0 * exact_uniform_f95(0, n_stars), 4)},
            "stars_eff": {"n_eff": round(n_eff, 3), "jeffreys_f95_pct": round(100.0 * exact_jeffreys_f95(0, n_eff), 4), "uniform_f95_pct": round(100.0 * exact_uniform_f95(0, n_eff), 4)},
            "star_blocks_eff": {"n_raw": n_blk_tot, "n_eff": round(n_eff_blk, 2), "jeffreys_f95_pct": round(100.0 * exact_jeffreys_f95(0, n_eff_blk), 4), "uniform_f95_pct": round(100.0 * exact_uniform_f95(0, n_eff_blk), 4)},
        },
        "external_contacts": 0,
    }
    (RES / "N11A_ANALYZER_SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[N11A] Done in {summary['elapsed_s']}s. Triggers={len(triggers)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
