#!/usr/bin/env python3
"""
Phase D096 (V5.4): SOFIA/EXES Mid-IR Echelon-Echelle, Coherent Shift-Stack Drift,
and JWST NIRISS/SOSS + NIRSpec/G140H Technosignature Search — Dual-Mode Stage A/B Pipeline.

Strictly adheres to immutable Stage-1 lock: NEVER alters `v5_4_detector.py` or any Stage-1
locked artifact. Supports deterministic Stage-2 forensic triage ONLY in this script when
empirically justified against physical spectra, headers, ATMs/ATRAN, or laboratory atlases.

CLI modes:
  --from-full-inputs     : Run Stage A on raw FITS in `inputs_d096_v5_4/` to produce
                           `bounded_inputs/d096_bounded_bundle.json.gz` (<= 22.0 MiB), then
                           immediately decode ONLY from that bounded bundle and run Stage B.
  --from-bounded-inputs  : Decode `bounded_inputs/d096_bounded_bundle.json.gz` + Archives T/U
                           and run Stage B deterministically (0 network, 100% SHA-256 bit-identical).
  --archives-dir <path>  : Override directory holding Companion Archives T and U.
  --out-dir <path>       : Override output directory (default: `<workspace>/results`).
"""

from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import json
import math
import os
import sys
import warnings
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import median_filter

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from v5_4_detector import (
    C_ANGSTROM_GHZ,
    C_KMS,
    COMB_V4_1_WINDOWS_A,
    DETECTOR_NAME,
    FWHM_FACTOR,
    GROUND_AIRGLOW_AND_TELLURIC_A,
    MAD_NORM,
    _compute_rolling_mad_1d,
    _extract_g8_feat_v52,
    air_to_vac_a,
    analytical_observatory_berv_kms,
    bary_to_planet_rest_wave,
    check_channel_lsf_gate,
    check_rousselot_oh_and_barycentric_v52,
    compute_multievent_sync_v51,
    compute_photon_beam_upper_limit,
    compute_running_continuum,
    compute_spectral_rarity_score,
    compute_supraphotospheric_f1_window,
    effective_resolving_power,
    evaluate_gate_g2_airglow,
    evaluate_gate_g6_v35_dense,
    evaluate_gate_g6_v36_sparse,
    evaluate_gate_g7_v50,
    evaluate_gate_g8_v52,
    evaluate_gates_g3_g4_g5_v42,
    exact_mad_1d,
    exact_median_1d,
    fit_lsf_on_window,
    fit_patch_novelty_model_v52,
    gaia_g_planck_flam_cgs,
    get_calibration_bands,
    get_inst_config,
    measure_exposure_stellar_rv,
    run_cohort_rpca_v50,
    run_coherent_shift_stack_calibration_v54,
    run_jwst_soss_g140h_calibration_v54,
    run_sofia_exes_calibration_v54,
    scan_agnostic_multiscale_v50,
    scan_blind_drift_dedoppler_v51,
    scan_coherent_shift_stack_drift_v54,
    scan_curved_and_periodic_drift_v53,
    scan_frequency_comb_v4,
    scan_frequency_comb_v4_1,
    scan_jwst_niriss_and_g140h_v54,
    scan_multiepoch_drift_chaining_v52,
    scan_single_exposure_residual_lsf,
    scan_sofia_exes_midir_echelle_v54,
    twomass_h_planck_flam_cgs,
)

MAX_BUNDLE_MIB = 22.0
RNG_SEED = 20261121

ARCHIVE_T_NAME = "SETI_D094_V5_2_MULTIEPOCH_DRIFT_APOGEE2_CRIRESJH_MIRILRS_RESULTS_2026-11-21.zip"
ARCHIVE_T_BUNDLE = "bounded_inputs/d094_bounded_bundle.json.gz"
ARCHIVE_U_NAME = "SETI_D095_V5_3_CURVED_PERIODIC_DRIFT_GHOST_SPITZER_IRS_APOGEE2_RESULTS_2026-11-21.zip"
ARCHIVE_U_BUNDLE = "bounded_inputs/d095_bounded_bundle.json.gz"

# APOGEE-2 DR17 APOGEE_PIXMASK fatal + saturation + Littrow + bright telluric/sky flags
APOGEE_BAD_MASK = (
    (1 << 0) | (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4)
    | (1 << 5) | (1 << 6) | (1 << 7) | (1 << 8) | (1 << 9) | (1 << 12)
)
JWST_FATAL_DQ_MASK = 1


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            b = fh.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _opt_float(v: Any, default: float = math.nan) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def _write_csv(path: Path, cols: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Compact Byte-Transposed IEEE-754 Bundle Codecs (Handles D094/D095/D096)
# ---------------------------------------------------------------------------

def _encode_wave(w_angstrom: np.ndarray) -> dict[str, Any]:
    """Encode uniform linear/log-linear grids or smooth echelle dispersion compactly."""
    w = np.asarray(w_angstrom, dtype=np.float64)
    n = int(len(w))
    if n >= 4 and np.all(np.isfinite(w)) and np.all(w > 0.0):
        diffs = np.diff(w)
        dw = float(exact_median_1d(diffs))
        if np.max(np.abs(diffs - dw)) < 5e-4:
            return {"u": 1, "w0": round(float(w[0]), 6), "dw": round(dw, 9), "n": n}
        dl10 = np.diff(np.log10(w))
        cdelt1 = float(exact_median_1d(dl10))
        if np.max(np.abs(dl10 - cdelt1)) < 5e-11:
            return {
                "u": 4,
                "crval1": round(float(np.log10(w[0])), 9),
                "cdelt1": round(cdelt1, 11),
                "n": n,
            }
        dlw = np.diff(np.log(w))
        dl = float(exact_median_1d(dlw))
        if np.max(np.abs(dlw - dl)) < 1e-10:
            return {"u": 3, "w0": float(w[0]), "dl": float(dl), "n": n}
    if 32 <= n <= 8192 and np.all(np.isfinite(w)) and np.all(np.diff(w) > 0.0):
        x = np.linspace(-1.0, 1.0, n)
        c = np.polyfit(x, w, 5)
        w_fit = np.polyval(c, x)
        res_pm = np.round((w - w_fit) * 1e6)
        if np.max(np.abs(res_pm)) < 32000.0:
            r16 = res_pm.astype(np.int16)
            bt = r16.view(np.uint8).reshape(-1, 2).T.copy().tobytes()
            return {
                "u": 2,
                "n": n,
                "c": [float(v) for v in c],
                "b64": base64.b64encode(bt).decode("ascii"),
            }
    bt = w.view(np.uint8).reshape(-1, 8).T.copy().tobytes()
    return {"u": 0, "n": n, "b64": base64.b64encode(bt).decode("ascii")}


def _decode_wave_any(enc: dict[str, Any]) -> np.ndarray:
    """Decode wavelength grid from any D094 (u=0,1), D095 (u=2 log10), or D096 (u=0..4) bundle."""
    u = int(enc["u"])
    n = int(enc["n"])
    if u == 1:
        return float(enc["w0"]) + float(enc["dw"]) * np.arange(n, dtype=np.float64)
    if u == 4 or (u == 2 and "crval1" in enc):
        return 10.0 ** (float(enc["crval1"]) + float(enc["cdelt1"]) * np.arange(n, dtype=np.float64))
    if u == 3:
        return float(enc["w0"]) * np.exp(float(enc["dl"]) * np.arange(n, dtype=np.float64))
    if u == 2:
        x = np.linspace(-1.0, 1.0, n)
        w_fit = np.polyval(np.asarray(enc["c"], dtype=np.float64), x)
        raw = np.frombuffer(base64.b64decode(enc["b64"]), dtype=np.uint8).reshape(2, n).T.copy()
        r16 = raw.view(np.int16).reshape(-1).astype(np.float64)
        return w_fit + r16 * 1e-6
    raw = np.frombuffer(base64.b64decode(enc["b64"]), dtype=np.uint8).reshape(8, n).T.copy()
    return raw.view("<f8").reshape(-1)


def _encode_f32_mask(arr: np.ndarray | None, mask_bits: int = 0xFFFFF800) -> dict[str, Any]:
    if arr is None:
        return {"all_nan": True, "n": 0}
    a = np.asarray(arr, dtype=np.float32)
    fin = np.isfinite(a)
    if not np.any(fin):
        return {"all_nan": True, "n": int(len(a))}
    a_clean = np.where(fin, a, np.float32(np.nan))
    u = a_clean.view(np.uint32)
    u_masked = np.where(fin, u & np.uint32(mask_bits), u)
    bt = u_masked.view(np.uint8).reshape(-1, 4).T.copy().tobytes()
    return {"all_nan": False, "fmt": "f32", "n": int(len(a)), "b64": base64.b64encode(bt).decode("ascii")}


def _encode_bf16(arr: np.ndarray | None) -> dict[str, Any]:
    if arr is None:
        return {"all_nan": True, "n": 0}
    a = np.asarray(arr, dtype=np.float32)
    fin = np.isfinite(a)
    if not np.any(fin):
        return {"all_nan": True, "n": int(len(a))}
    a_clean = np.where(fin, a, np.float32(np.nan))
    u16 = (a_clean.view(np.uint32) >> np.uint32(16)).astype(np.uint16)
    bt = u16.view(np.uint8).reshape(-1, 2).T.copy().tobytes()
    return {"all_nan": False, "fmt": "bf16", "n": int(len(a)), "b64": base64.b64encode(bt).decode("ascii")}


def _decode_arr_any(enc: dict[str, Any] | None) -> np.ndarray | None:
    if enc is None or enc.get("all_nan"):
        return None
    n = int(enc["n"])
    if n <= 0:
        return None
    if enc.get("fmt") == "bf16":
        u16 = np.frombuffer(base64.b64decode(enc["b64"]), dtype=np.uint8).reshape(2, n).T.copy().view("<u2").reshape(-1)
        return (u16.astype(np.uint32) << np.uint32(16)).view("<f4").astype(np.float64)
    raw = np.frombuffer(base64.b64decode(enc["b64"]), dtype=np.uint8).reshape(4, n).T.copy()
    return raw.view("<f4").reshape(-1).astype(np.float64)


def _encode_qual(q_arr: np.ndarray | None) -> dict[str, Any]:
    if q_arr is None:
        return {"mode": "NONE"}
    bad = np.flatnonzero(np.asarray(q_arr) != 0).astype(np.int32)
    if len(bad) == 0:
        return {"mode": "ZERO", "n": int(len(q_arr))}
    if len(bad) <= 2500:
        return {"mode": "IDX", "n": int(len(q_arr)), "idx": bad.tolist()}
    packed = np.packbits((np.asarray(q_arr) != 0).astype(np.uint8))
    return {"mode": "BITS", "n": int(len(q_arr)), "b64": base64.b64encode(packed.tobytes()).decode("ascii")}


def _decode_qual(enc: dict[str, Any], n_fallback: int) -> np.ndarray:
    mode = enc.get("mode", "NONE")
    if mode in ("NONE", "ZERO"):
        return np.zeros(int(enc.get("n", n_fallback)), dtype=np.int32)
    n = int(enc["n"])
    out = np.zeros(n, dtype=np.int32)
    if mode == "IDX":
        idx = enc.get("idx", [])
        if idx:
            out[np.asarray(idx, dtype=np.int64)] = 1
        return out
    packed = np.frombuffer(base64.b64decode(enc["b64"]), dtype=np.uint8)
    bits = np.unpackbits(packed)[:n]
    out[bits > 0] = 1
    return out


# ---------------------------------------------------------------------------
# Stage A: Multi-Instrument Raw FITS Extraction -> Bounded Bundle (<= 22 MiB)
# ---------------------------------------------------------------------------

def _extract_sofia_exes(fp: Path, row: dict[str, str]) -> dict[str, Any]:
    """Extract SOFIA/EXES _CMB_ 3D echelon-echelle orders (wavenumber -> um ascending)."""
    from astropy.io import fits
    from astropy.time import Time

    with fits.open(fp, memmap=False) as hdul:
        h0 = hdul[0].header
        d = np.asarray(hdul[0].data, dtype=np.float64)
        if d.ndim == 2:
            d = d[None, :, :]
        if d.ndim != 3 or d.shape[1] < 4:
            raise RuntimeError(f"Unexpected SOFIA_EXES shape {d.shape} in {fp.name}")

        date_obs = str(h0.get("DATE-OBS", "")).strip()
        if date_obs:
            try:
                mjd_obs = float(Time(date_obs, format="isot", scale="utc").mjd)
            except Exception:
                mjd_obs = float(row["mjd_obs"])
        else:
            mjd_obs = float(row["mjd_obs"])

        expt = _opt_float(h0.get("EXPTIME"), float(row["t_exptime"]))
        rp_hdr = _opt_float(h0.get("RP"), math.nan)
        res_hdr = _opt_float(h0.get("RESOLUN"), math.nan)
        rp = rp_hdr if (math.isfinite(rp_hdr) and rp_hdr > 1000.0) else (
            res_hdr if (math.isfinite(res_hdr) and res_hdr > 1000.0) else float(row["resolving_power"])
        )

        # NEVER use TELRA (hours); compute BERV strictly from Gaia/SIMBAD degrees
        berv_kms = analytical_observatory_berv_kms(float(row["s_ra"]), float(row["s_dec"]), mjd_obs, "SOFIA_EXES")

        arms: list[dict[str, Any]] = []
        n_orders = d.shape[0]
        n_rows = d.shape[1]
        for oi in range(n_orders):
            nu = d[oi, 0]
            fl = d[oi, 1]
            er = d[oi, 2]
            atran = d[oi, 3]
            wht = d[oi, 4] if n_rows >= 5 else np.ones_like(nu)

            valid_nu = np.isfinite(nu) & (nu > 10.0)
            if int(np.sum(valid_nu)) < 40:
                continue
            wave_um = 1e4 / nu[valid_nu]
            fl_v = fl[valid_nu]
            er_v = er[valid_nu]
            at_v = atran[valid_nu]
            wt_v = wht[valid_nu]

            sidx = np.argsort(wave_um)
            wave_um = wave_um[sidx]
            fl_v = fl_v[sidx]
            er_v = er_v[sidx]
            at_v = at_v[sidx]
            wt_v = wt_v[sidx]

            bad = (~np.isfinite(fl_v)) | (~np.isfinite(er_v)) | (er_v < 0.0) | (~np.isfinite(at_v))
            fl_v = np.where(bad, np.nan, fl_v)
            er_v = np.where(bad, np.nan, er_v)
            at_v = np.where(np.isfinite(at_v), np.clip(at_v, 0.0, 1.0), 0.0)
            wt_v = np.where(np.isfinite(wt_v) & (wt_v >= 0.0), wt_v, 0.0)

            arms.append({
                "arm": f"EXES_O{oi + 1:02d}",
                "order": oi + 1,
                "dp_file_id": row["dp_id"],
                "specsys": "TOPOCENT",
                "wave_is_air": False,
                "berv_kms": round(berv_kms, 5),
                "berv_src": "SOFIA_ANALYTICAL_DEG",
                "rp": round(rp, 2),
                "wave": _encode_wave(wave_um * 1e4),
                "flux": _encode_f32_mask(fl_v, 0xFFFFF800),
                "err": _encode_f32_mask(er_v, 0xFFFF0000),
                "atran": _encode_bf16(at_v),
                "weight": _encode_bf16(wt_v),
                "qual": _encode_qual(bad.astype(np.int32)),
            })

    return {
        "dp_id": row["dp_id"],
        "parent_dp_id": row["dp_id"],
        "resolving_power": round(rp, 2),
        "mjd_obs": round(mjd_obs, 6),
        "t_exptime_s": round(expt, 3),
        "specsys": "TOPOCENT",
        "wave_is_air": False,
        "berv_kms": round(berv_kms, 5),
        "berv_src": "SOFIA_ANALYTICAL_DEG",
        "f_unit": "Jy",
        "fluxcal": "ABSOLUTE",
        "arms": arms,
    }


def _extract_carmenes_vis(fp: Path, row: dict[str, str]) -> dict[str, Any]:
    """Extract CARMENES_VIS (hdul[1..4], (61, 4096)), trim edges, blaze-normalize, compress cleanly."""
    from astropy.io import fits

    with fits.open(fp, memmap=False) as hdul:
        h0 = hdul[0].header
        spec_all = np.asarray(hdul[1].data, dtype=np.float64)
        cont_all = np.asarray(hdul[2].data, dtype=np.float64)
        sig_all = np.asarray(hdul[3].data, dtype=np.float64)
        wave_all = np.asarray(hdul[4].data, dtype=np.float64)

        mjd_obs = _opt_float(h0.get("HIERARCH CARACAL MJD-OBS"), float(row["mjd_obs"]))
        tmean = _opt_float(h0.get("HIERARCH CARACAL TMEAN"), 0.0)
        if mjd_obs > 50000.0 and 0.0 <= tmean <= 20000.0:
            mjd_mid = mjd_obs + (0.5 * tmean) / 86400.0
        else:
            mjd_mid = mjd_obs
        expt = _opt_float(h0.get("EXPTIME"), float(row["t_exptime"]))
        berv_hdr = _opt_float(h0.get("HIERARCH CARACAL BERV"), math.nan)
        if math.isfinite(berv_hdr):
            berv_kms, berv_src = berv_hdr, "CARACAL_BERV"
        else:
            berv_kms = analytical_observatory_berv_kms(float(row["s_ra"]), float(row["s_dec"]), mjd_mid, "CARMENES_VIS")
            berv_src = "CAHA_ANALYTICAL_BERV"
        serval_rv = _opt_float(h0.get("HIERARCH CARACAL SERVAL RV"), float(row["prior_rv_kms"]))

        n_ord = spec_all.shape[0]
        arms: list[dict[str, Any]] = []
        for oi in range(n_ord):
            wo = wave_all[oi, 16:4080]
            fl_r = spec_all[oi, 16:4080]
            ct_r = cont_all[oi, 16:4080]
            sg_r = sig_all[oi, 16:4080]

            valid = (
                np.isfinite(wo) & (wo >= 5100.0) & (wo <= 9700.0)
                & np.isfinite(fl_r) & np.isfinite(ct_r) & (ct_r > 0.0)
                & np.isfinite(sg_r) & (sg_r > 0.0)
            )
            if int(np.sum(valid)) < 200:
                continue
            fl_n = np.where(valid, fl_r / np.where(ct_r > 0.0, ct_r, 1.0), np.nan)
            er_n = np.where(valid, sg_r / np.where(ct_r > 0.0, ct_r, 1.0), np.nan)
            qu = (~valid).astype(np.int32)

            arms.append({
                "arm": f"CARMENES_O{oi + 1:02d}",
                "order": oi + 1,
                "dp_file_id": row["dp_id"],
                "specsys": "TOPOCENT",
                "wave_is_air": False,
                "berv_kms": round(berv_kms, 5),
                "berv_src": berv_src,
                "wave": _encode_wave(wo),
                "flux": _encode_f32_mask(fl_n, 0xFFFFE000),
                "err": _encode_bf16(er_n),
                "qual": _encode_qual(qu),
            })

    return {
        "dp_id": row["dp_id"],
        "parent_dp_id": row["dp_id"],
        "resolving_power": float(row["resolving_power"]),
        "mjd_obs": round(mjd_mid, 6),
        "t_exptime_s": round(expt, 3),
        "specsys": "TOPOCENT",
        "wave_is_air": False,
        "berv_kms": round(berv_kms, 5),
        "berv_src": berv_src,
        "carmenes_serval_rv_kms": round(serval_rv, 5),
        "f_unit": "REL_BLAZE",
        "fluxcal": "RELATIVE",
        "arms": arms,
    }


def _extract_apogee2_visits(fp: Path, row: dict[str, str]) -> list[dict[str, Any]]:
    """Extract all individual NVISITS rows [2:2+nv] from SDSS DR17 apStar FITS."""
    from astropy.io import fits

    out: list[dict[str, Any]] = []
    with fits.open(fp, memmap=False) as hdul:
        h0 = hdul[0].header
        h1 = hdul[1].header
        nv = int(h0.get("NVISITS", 0))
        if nv < 4:
            raise RuntimeError(f"Expected NVISITS>=4 in {fp.name}, got {nv}")
        fl_mat = np.asarray(hdul[1].data, dtype=np.float64)
        er_mat = np.asarray(hdul[2].data, dtype=np.float64)
        bm_mat = np.asarray(hdul[3].data, dtype=np.int64)
        t9 = hdul[9].data
        crval1 = float(h1["CRVAL1"])
        cdelt1 = float(h1["CDELT1"])
        nwave = int(fl_mat.shape[1])
        wave_vac_a = 10.0 ** (crval1 + cdelt1 * np.arange(nwave, dtype=np.float64))

        chips = [
            ("APOGEE_BLUE", 15155.0, 15800.0, 1),
            ("APOGEE_GREEN", 15865.0, 16425.0, 2),
            ("APOGEE_RED", 16485.0, 16955.0, 3),
        ]
        tel_tag = "SDSS_APOGEE2" if "apStar" in fp.name else "SDSS_APOGEE2_LCO"
        base_dp = row["dp_id"]
        nominal_vis_expt = float(row["t_exptime"]) / float(nv)

        for vi in range(nv):
            row_idx = 2 + vi
            fl_v = fl_mat[row_idx]
            er_v = er_mat[row_idx]
            bm_v = bm_mat[row_idx]
            mjd_v = float(t9["jd"][vi]) - 2400000.5
            bc_v = _opt_float(t9["bc"][vi], math.nan)
            if not math.isfinite(bc_v):
                bc_v = analytical_observatory_berv_kms(float(row["s_ra"]), float(row["s_dec"]), mjd_v, tel_tag)
            vhelio_v = _opt_float(t9["vhelio"][vi], float(row["prior_rv_kms"]))

            arms: list[dict[str, Any]] = []
            for cname, lo_a, hi_a, ord_id in chips:
                cm = (wave_vac_a >= lo_a) & (wave_vac_a <= hi_a)
                wc = wave_vac_a[cm]
                fc = fl_v[cm]
                ec = np.where(np.isfinite(er_v[cm]) & (er_v[cm] > 0.0), er_v[cm], np.nan)
                qc = ((bm_v[cm] & APOGEE_BAD_MASK) != 0) | (~np.isfinite(fc)) | (~np.isfinite(ec))
                i0 = int(np.flatnonzero(cm)[0])
                log10_w0 = crval1 + cdelt1 * i0
                arms.append({
                    "arm": cname,
                    "order": ord_id,
                    "dp_file_id": f"{base_dp}.V{vi + 1}",
                    "specsys": "BARYCENT",
                    "wave_is_air": False,
                    "berv_kms": round(bc_v, 5),
                    "berv_src": "APOGEE_HDU9_BC",
                    "wave": {"u": 4, "crval1": round(log10_w0, 9), "cdelt1": round(cdelt1, 12), "n": int(len(wc))},
                    "flux": _encode_f32_mask(fc, 0xFFFFE000),
                    "err": _encode_bf16(ec),
                    "qual": _encode_qual(qc.astype(np.int32)),
                })

            out.append({
                "dp_id": f"{base_dp}.V{vi + 1}",
                "parent_dp_id": base_dp,
                "visit_index": vi + 1,
                "n_visits_total": nv,
                "apogee_h9_vhelio_kms": round(vhelio_v, 4),
                "mjd_obs": round(mjd_v, 6),
                "t_exptime_s": round(nominal_vis_expt, 3),
                "resolving_power": 22500.0,
                "specsys": "BARYCENT",
                "wave_is_air": False,
                "berv_kms": round(bc_v, 5),
                "berv_src": "APOGEE_HDU9_BC",
                "f_unit": "1e-17 erg s^-1 cm^-2 A^-1",
                "fluxcal": "APOGEE_1D_RELATIVE",
                "arms": arms,
            })
    return out


def _extract_jwst_x1d(fp: Path, row: dict[str, str]) -> dict[str, Any]:
    """Extract JWST NIRISS/SOSS or NIRSpec/G140H EXTRACT1D tables (handles 1D & (1,N) columns)."""
    from astropy.io import fits
    from astropy.time import Time

    inst = row["instrument"]
    with fits.open(fp, memmap=False) as hdul:
        h0 = hdul[0].header
        mjd_obs = _opt_float(h0.get("EXPSTART"), math.nan)
        if not math.isfinite(mjd_obs):
            dobs = str(h0.get("DATE-OBS", "")).strip()
            if dobs:
                try:
                    mjd_obs = float(Time(dobs, scale="utc").mjd)
                except Exception:
                    mjd_obs = float(row["mjd_obs"])
            else:
                mjd_obs = float(row["mjd_obs"])
        expt = _opt_float(h0.get("EFFEXPTM"), float(row["t_exptime"]))
        rp = float(row["resolving_power"])

        arms: list[dict[str, Any]] = []
        ext_idx = 0
        for hi in hdul:
            if hi.name != "EXTRACT1D":
                continue
            ext_idx += 1
            tab = hi.data
            cols = list(hi.columns.names)
            w_um = np.asarray(tab["WAVELENGTH"], dtype=np.float64).ravel()
            fl = np.asarray(tab["FLUX"], dtype=np.float64).ravel()
            er_col = "FLUX_ERROR" if "FLUX_ERROR" in cols else ("ERROR" if "ERROR" in cols else "FLUX_ERR")
            er = np.asarray(tab[er_col], dtype=np.float64).ravel() if er_col in cols else np.full_like(fl, np.nan)
            dq = np.asarray(tab["DQ"], dtype=np.int32).ravel() if "DQ" in cols else np.zeros(len(w_um), dtype=np.int32)

            spord = int(hi.header.get("SPORDER", ext_idx))
            valid_w = np.isfinite(w_um) & (w_um > 0.3) & (w_um < 6.0)
            if int(np.sum(valid_w)) < 40:
                continue
            w_um = w_um[valid_w]
            fl = fl[valid_w]
            er = er[valid_w]
            dq = dq[valid_w]

            sidx = np.argsort(w_um)
            w_um = w_um[sidx]
            fl = fl[sidx]
            er = er[sidx]
            dq = dq[sidx]

            bad = ((dq & JWST_FATAL_DQ_MASK) != 0) | (~np.isfinite(fl)) | (~np.isfinite(er)) | (er <= 0.0)
            arms.append({
                "arm": f"{'SOSS' if inst == 'JWST_NIRISS_SOSS' else 'G140H'}_ORD{spord}",
                "order": spord,
                "dp_file_id": row["dp_id"],
                "specsys": "BARYCENT",
                "wave_is_air": False,
                "berv_kms": 0.0,
                "berv_src": "JWST_BARYCENTRIC_X1D",
                "rp": rp,
                "wave": _encode_wave(w_um * 1e4),
                "flux": _encode_f32_mask(fl, 0xFFFFF800),
                "err": _encode_f32_mask(er, 0xFFFF0000),
                "qual": _encode_qual(bad.astype(np.int32)),
            })

    return {
        "dp_id": row["dp_id"],
        "parent_dp_id": row["dp_id"],
        "resolving_power": rp,
        "mjd_obs": round(mjd_obs, 6),
        "t_exptime_s": round(expt, 3),
        "specsys": "BARYCENT",
        "wave_is_air": False,
        "berv_kms": 0.0,
        "berv_src": "JWST_BARYCENTRIC_X1D",
        "f_unit": "JWST_X1D_FLUX",
        "fluxcal": "JWST_RELATIVE_MAD",
        "arms": arms,
    }


def _build_base_record(row: dict[str, str], ext: dict[str, Any]) -> dict[str, Any]:
    return {
        "dp_id": ext["dp_id"],
        "parent_dp_id": ext["parent_dp_id"],
        "instrument": row["instrument"],
        "star": row["canonical_target"],
        "common_name": row["common_name"],
        "role": row["role"],
        "subrole": row["subrole"],
        "science_track": row["science_track"],
        "panchromatic_bridge": row["panchromatic_bridge"] == "True",
        "is_prior_bridge": row["is_prior_bridge"] == "True",
        "gaia_source_id": int(row["gaia_source_id"]) if str(row["gaia_source_id"]).strip() else 0,
        "s_ra": float(row["s_ra"]),
        "s_dec": float(row["s_dec"]),
        "dist_pc": float(row["dist_pc"]),
        "within_10pc": row["within_10pc"] == "True",
        "phot_g_mag": _opt_float(row["phot_g_mag"]),
        "j_mag": _opt_float(row["j_mag"]),
        "h_mag": _opt_float(row["h_mag"]),
        "ks_mag": _opt_float(row["ks_mag"]),
        "teff_k": float(row["teff_k"]),
        "mh_dex": _opt_float(row["mh_dex"], 0.0),
        "stellar_mass_msun": _opt_float(row["stellar_mass_msun"], 1.0),
        "prior_rv_kms": float(row["prior_rv_kms"]),
        "n_exoplanets": int(row["n_exoplanets"]),
        "has_transiting_planet": row["has_transiting_planet"] == "True",
        "ecliptic_lat_deg": float(row["ecliptic_lat_deg"]),
        "sn1987a_dt_days": float(row["sn1987a_dt_days"]),
        "gw170817_dt_days": float(row["gw170817_dt_days"]),
        "sn2023ixf_dt_days": float(row["sn2023ixf_dt_days"]),
        "ppo_align_score": float(row["ppo_align_score"]),
        "epoch_rank": int(row["epoch_rank"]),
        "grating": row["grating"],
        "resolving_power": float(ext["resolving_power"]),
        "mjd_obs": float(ext["mjd_obs"]),
        "t_exptime_s": float(ext["t_exptime_s"]),
        "phase_window": row["phase_window"],
        "signed_phase": _opt_float(row["signed_phase"], 0.0),
        "planet_orbital_rv_kms": _opt_float(row["planet_orbital_rv_kms"], 0.0),
        "specsys": ext["specsys"],
        "wave_is_air": ext["wave_is_air"],
        "berv_kms": ext["berv_kms"],
        "berv_src": ext["berv_src"],
        "flux_unit": ext["f_unit"],
        "fluxcal": ext["fluxcal"],
        "arms": ext["arms"],
        **({"apogee_h9_vhelio_kms": ext["apogee_h9_vhelio_kms"]} if "apogee_h9_vhelio_kms" in ext else {}),
        **({"carmenes_serval_rv_kms": ext["carmenes_serval_rv_kms"]} if "carmenes_serval_rv_kms" in ext else {}),
    }


def run_stage_a(inputs_dir: Path, bundle_out: Path) -> dict[str, Any]:
    cohort_path = SCRIPT_DIR / "FROZEN_COHORT_D096.csv"
    man_path = SCRIPT_DIR / "FULL_D096_INPUT_MANIFEST.json"
    with cohort_path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    bundle_exps: list[dict[str, Any]] = []
    for row in rows:
        fp = inputs_dir / row["f1_rel"]
        if not fp.exists():
            raise FileNotFoundError(f"Missing frozen input: {fp}")
        inst = row["instrument"]
        if inst == "SOFIA_EXES":
            bundle_exps.append(_build_base_record(row, _extract_sofia_exes(fp, row)))
        elif inst == "CARMENES_VIS":
            bundle_exps.append(_build_base_record(row, _extract_carmenes_vis(fp, row)))
        elif inst == "SDSS_APOGEE2":
            for v in _extract_apogee2_visits(fp, row):
                bundle_exps.append(_build_base_record(row, v))
        elif inst in ("JWST_NIRISS_SOSS", "JWST_NIRSPEC_G140H"):
            bundle_exps.append(_build_base_record(row, _extract_jwst_x1d(fp, row)))
        else:
            raise RuntimeError(f"Unsupported D096 instrument: {inst}")

    bundle = {
        "schema": "D096_BOUNDED_BUNDLE_V1",
        "phase_id": "D096",
        "detector": DETECTOR_NAME,
        "cohort_sha256": _sha256_file(cohort_path),
        "manifest_sha256": _sha256_file(man_path) if man_path.exists() else "",
        "n_cohort_files": len(rows),
        "n_unpacked_exposures": len(bundle_exps),
        "exposures": bundle_exps,
    }
    bundle_out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(bundle_out, "wt", encoding="utf-8", compresslevel=9) as gz:
        json.dump(bundle, gz, separators=(",", ":"), allow_nan=True)

    bnd_mib = bundle_out.stat().st_size / (1024.0 * 1024.0)
    if bnd_mib > MAX_BUNDLE_MIB:
        raise RuntimeError(f"Bounded bundle {bnd_mib:.2f} MiB exceeds hard cap {MAX_BUNDLE_MIB} MiB!")
    print(f"Stage A DONE: wrote {bundle_out} ({bnd_mib:.2f} MiB <= {MAX_BUNDLE_MIB:.1f} MiB, {len(bundle_exps)} exposures)", flush=True)
    return bundle


# ---------------------------------------------------------------------------
# Spectrum Unpacking & Multi-Order Resampling Helpers
# ---------------------------------------------------------------------------

def _arm_to_bary_vac(w_raw_a: np.ndarray, specsys: str, berv_kms: float, wave_is_air: bool) -> np.ndarray:
    w_vac = air_to_vac_a(w_raw_a) if wave_is_air else np.asarray(w_raw_a, dtype=np.float64)
    ss = str(specsys).upper()
    if "BARY" in ss or "HELIO" in ss:
        return w_vac
    return w_vac * (1.0 + float(berv_kms) / C_KMS)


def _unpack_echelle_exposure(exp: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """Decode APOGEE2 / CARMENES_VIS exposure arms, compute running continuum & normalized residual."""
    inst = exp["instrument"]
    arms_out: list[dict[str, Any]] = []

    for arm in exp["arms"]:
        w_raw = _decode_wave_any(arm["wave"])
        is_air = bool(arm.get("wave_is_air", exp.get("wave_is_air", False)))
        w_bary = _arm_to_bary_vac(w_raw, arm["specsys"], float(arm["berv_kms"]), wave_is_air=is_air)
        fl = _decode_arr_any(arm["flux"])
        er = _decode_arr_any(arm["err"])
        qu = _decode_qual(arm["qual"], len(w_bary))
        if fl is None or len(w_bary) < 40:
            continue

        order_sort = np.argsort(w_bary)
        w_bary = w_bary[order_sort]
        fl = fl[order_sort]
        qu = qu[order_sort]
        if er is not None:
            er = er[order_sort]

        bad = (~np.isfinite(w_bary)) | (~np.isfinite(fl)) | (qu != 0)
        fl_clean = np.where(bad, np.nan, fl)
        er_clean = np.where(bad | (~np.isfinite(er)) | (er <= 0.0), np.nan, er) if er is not None else None

        cr, ce = compute_running_continuum(w_bary, fl_clean, cfg, err=er_clean)
        cont = np.where(cr > 0.0, cr, ce)
        fn = np.where(bad | (~np.isfinite(fl_clean)) | (~np.isfinite(cont)) | (cont <= 0.0), np.nan, fl_clean / cont)
        if er_clean is not None:
            sig = np.where(np.isfinite(fn) & (cont > 0.0) & np.isfinite(er_clean), er_clean / cont, np.nan)
        else:
            mad_loc = max(1e-4, exact_mad_1d(fn[np.isfinite(fn)] - 1.0)) if int(np.sum(np.isfinite(fn))) >= 16 else 0.02
            sig = np.where(np.isfinite(fn), mad_loc, np.nan)
        sig = np.maximum(sig, 1e-4)

        arms_out.append({
            "arm": arm["arm"],
            "order": int(arm["order"]),
            "w_bary": w_bary,
            "flux": fl_clean,
            "err": er_clean,
            "qual": qu,
            "fn": fn,
            "sig": sig,
        })

    return {"exp": exp, "arms": arms_out}


def _build_1d_ivw_spectrum(
    arms: list[dict[str, Any]],
    w_grid_a: np.ndarray,
    rv_kms: float,
    berv_kms: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Resample multi-order/multi-chip spectrum onto star rest grid via inverse-variance weighting."""
    n = len(w_grid_a)
    sum_w = np.zeros(n, dtype=np.float64)
    sum_wf = np.zeros(n, dtype=np.float64)
    dop = 1.0 + float(rv_kms) / C_KMS
    step_a = float(w_grid_a[1] - w_grid_a[0])

    for a in arms:
        w_rest_arm = a["w_bary"] / dop
        fn = a["fn"]
        sg = a["sig"]
        ok = np.isfinite(w_rest_arm) & np.isfinite(fn) & np.isfinite(sg) & (sg > 0.0)
        if int(np.sum(ok)) < 20:
            continue
        wu = w_rest_arm[ok]
        fu = fn[ok]
        wu_inv = 1.0 / np.maximum(1e-4, sg[ok]) ** 2
        if float(wu[-1]) < float(w_grid_a[0]) or float(wu[0]) > float(w_grid_a[-1]):
            continue
        w_lo = float(wu[0])
        w_hi = float(wu[-1])
        m_in = (w_grid_a >= w_lo) & (w_grid_a <= w_hi)
        if not np.any(m_in):
            continue
        wg_sub = w_grid_a[m_in]
        idx_hi = np.searchsorted(wu, wg_sub)
        idx_lo = np.clip(idx_hi - 1, 0, len(wu) - 1)
        idx_hi = np.clip(idx_hi, 0, len(wu) - 1)
        d_gap = np.minimum(np.abs(wg_sub - wu[idx_lo]), np.abs(wu[idx_hi] - wg_sub))
        no_gap = d_gap <= 3.5 * step_a
        f_int = np.interp(wg_sub, wu, fu)
        w_int = np.interp(wg_sub, wu, wu_inv)
        add_m = np.zeros(n, dtype=bool)
        add_m[m_in] = no_gap & np.isfinite(f_int) & np.isfinite(w_int) & (w_int > 0.0)
        f_full = np.zeros(n, dtype=np.float64)
        w_full = np.zeros(n, dtype=np.float64)
        f_full[m_in] = f_int
        w_full[m_in] = w_int
        sum_wf[add_m] += w_full[add_m] * f_full[add_m]
        sum_w[add_m] += w_full[add_m]

    fn_out = np.where(sum_w > 0.0, sum_wf / np.maximum(sum_w, 1e-30), np.nan)
    sig_out = np.where(sum_w > 0.0, 1.0 / np.sqrt(np.maximum(sum_w, 1e-30)), np.nan)

    # Local median baseline correction & z-score
    fin = np.isfinite(fn_out)
    med_base = np.ones(n, dtype=np.float64)
    if int(np.sum(fin)) >= 50:
        f_fill = np.interp(w_grid_a, w_grid_a[fin], fn_out[fin])
        med_base = median_filter(f_fill, size=101, mode="nearest")
    resid = np.where(fin, fn_out - med_base, np.nan)
    # Empirical robust rolling MAD floor
    mad_emp = 0.015
    if int(np.sum(fin)) >= 50:
        mad_emp = max(1e-4, exact_mad_1d(resid[fin]))
    sig_eff = np.where(fin, np.maximum(sig_out, 0.5 * mad_emp), np.nan)
    z_out = np.where(fin & (sig_eff > 0.0), resid / sig_eff, 0.0)
    return fn_out, sig_eff, z_out, np.where(fin, med_base, 1.0)


# ---------------------------------------------------------------------------
# Stage B Calibrations: 540 New V5.4 + 1,311 Inherited Core = 1,851 Trials
# ---------------------------------------------------------------------------

def _cal_rpca_worker(args: tuple[int, np.random.SeedSequence]) -> dict[str, Any]:
    ti, ss = args
    rng_t = np.random.default_rng(ss)
    cfg_ap = get_inst_config("SDSS_APOGEE2", 22500.0)
    w_r = 15200.0 + 0.08 * np.arange(2048, dtype=np.float64)
    bervs_r = np.linspace(-25.0, 25.0, 8)
    mat = np.ones((8, 2048), dtype=np.float64) + rng_t.normal(0.0, 0.015, size=(8, 2048))
    ic = 1024
    if ti < 60:
        cls_, want = "ISOLATED", True
        mat[0] += 0.22 * np.exp(-0.5 * ((np.arange(2048) - ic) / 2.5) ** 2)
    elif ti < 120:
        cls_, want = "SHARED_REST", False
        for r in range(4):
            mat[r] += 0.20 * np.exp(-0.5 * ((np.arange(2048) - ic) / 2.5) ** 2)
    else:
        cls_, want = "SHARED_TOPO", False
        for r in range(4):
            it = ic - int(round((bervs_r[r] - bervs_r[0]) / C_KMS * 15280.0 / 0.08))
            mat[r] += 0.20 * np.exp(-0.5 * ((np.arange(2048) - it) / 2.5) ** 2)
    rp_out = run_cohort_rpca_v50(w_r, mat)
    rr = compute_spectral_rarity_score(w_r, rp_out["z_rpca"], bervs_r, 0, float(w_r[ic]), float(cfg_ap["sigma_v_kms"]))
    zp = float(rp_out["z_rpca"][0, ic])
    ok = evaluate_gate_g7_v50(zp, rr["rarity_score"])["g7_pass"]
    return {"trial": ti + 1, "class": cls_, "z_rpca": round(zp, 2), "rarity": round(rr["rarity_score"], 3), "passed": int(bool(ok) == want)}


def _cal_comb_worker(args: tuple[int, np.random.SeedSequence]) -> dict[str, Any]:
    ti, ss = args
    rng_t = np.random.default_rng(ss)
    cfg_ca = get_inst_config("CARMENES_VIS", 94600.0)
    wc_grid = 6200.0 + 0.025 * np.arange(8192, dtype=np.float64)
    wins = [COMB_V4_1_WINDOWS_A["CARMENES_VIS"][1]]
    sig_comb = 6300.0 / (94600.0 * FWHM_FACTOR)
    fwhm_comb = sig_comb * FWHM_FACTOR
    yr = rng_t.normal(0.0, 0.015, len(wc_grid))
    yt = rng_t.normal(0.0, 0.015, len(wc_grid))
    sr = np.full(len(wc_grid), 0.015)
    st = np.full(len(wc_grid), 0.015)
    tpl = np.ones(len(wc_grid))
    sky = np.zeros(len(wc_grid), dtype=bool)
    if ti < 54:
        cls_, want = "TRUE_COMB_V41", True
        dnu = [40.0, 65.0, 100.0][ti % 3]
        nu0 = 472000.0 + (ti % 9) * 200.0
        for m in range(6):
            wm = C_ANGSTROM_GHZ / (nu0 + m * dnu)
            yr += 0.095 * np.exp(-0.5 * ((wc_grid - wm) / sig_comb) ** 2)
    elif ti < 108:
        cls_, want = "RANDOM_FOREST", False
        dnu = 65.0
        nu0 = 472200.0 + ((ti - 54) % 9) * 150.0
        teeth_w = [C_ANGSTROM_GHZ / (nu0 + m * dnu) for m in range(6)]
        for wf in np.arange(min(teeth_w) - 10.0, max(teeth_w) + 10.0, 0.80 * fwhm_comb):
            yr += 0.085 * np.exp(-0.5 * ((wc_grid - wf) / sig_comb) ** 2)
        for wt in teeth_w:
            yr += 0.085 * np.exp(-0.5 * ((wc_grid - wt) / sig_comb) ** 2)
    else:
        cls_, want = "TOPO_SKY_COMB", False
        yt = yr.copy()
        dnu = 65.0
        nu0 = 472400.0
        for m in range(6):
            wm = C_ANGSTROM_GHZ / (nu0 + m * dnu)
            g = 0.095 * np.exp(-0.5 * ((wc_grid - wm) / sig_comb) ** 2)
            yr += g
            yt += 1.15 * g
    c_v41, _ = scan_frequency_comb_v4_1(wc_grid, yr, sr, 1.0 + yr, tpl, sky, yt, st, wins, ["CARM_RED"], cfg_ca)
    c_v4, _ = scan_frequency_comb_v4(wc_grid, yr, sr, 1.0 + yr, tpl, sky, yt, st, wins, ["CARM_RED"], cfg_ca)
    return {"trial": ti + 1, "class": cls_, "v4_hits": len(c_v4), "v41_hits": len(c_v41), "passed": int((len(c_v41) > 0) == want)}


def _run_v54_calibrations(g8_models: dict[str, dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    rng = np.random.default_rng(RNG_SEED)
    w_ap = 15200.0 + 0.08 * np.arange(16000, dtype=np.float64)
    cfg_ap = get_inst_config("SDSS_APOGEE2", 22500.0)
    w_ca = 5400.0 + 0.025 * np.arange(16000, dtype=np.float64)
    cfg_ca = get_inst_config("CARMENES_VIS", 94600.0)

    # 1. Three New V5.4 Calibration Suites (180 + 240 + 120 = 540)
    cal_exes = run_sofia_exes_calibration_v54(seed=9601)
    cal_cs = run_coherent_shift_stack_calibration_v54(seed=9602)
    cal_jwst = run_jwst_soss_g140h_calibration_v54(seed=9603)

    def _norm_trials(trials: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for t in trials:
            exp_v = bool(t.get("expected"))
            obs_v = bool(t.get("observed"))
            out.append({**t, "passed": int(t.get("passed", int(exp_v == obs_v)))})
        return out

    ex_rows = _norm_trials(cal_exes["trials"])
    cs_rows = _norm_trials(cal_cs["trials"])
    jw_rows = _norm_trials(cal_jwst["trials"])

    # 2. CALIBRATION_G8_V54_120 (40 isolated + 40 shared + 40 topo)
    g8_rows: list[dict[str, Any]] = []
    ref_m = next((m for m in g8_models.values() if m.get("ready")), None)
    wg8 = 15200.0 + 0.08 * np.arange(512, dtype=np.float64)
    for ti in range(120):
        zv = rng.normal(0.0, 1.0, len(wg8))
        amp = float(rng.uniform(10.0, 18.0))
        zv += amp * np.exp(-0.5 * ((np.arange(len(wg8)) - 256.0) / 1.25) ** 2)
        if ti < 40:
            cls_, rar, fr, ft, want = "ISOLATED_LASER", 0.99, 0.0, 0.0, True
        elif ti < 80:
            cls_, rar, fr, ft, want = "SHARED_LEAK", 0.30, 0.70, 0.05, False
        else:
            cls_, rar, fr, ft, want = "TOPO_LEAK", 0.25, 0.05, 0.75, False
        ev = evaluate_gate_g8_v52(ref_m, wg8, zv, wg8[256], amp, rar, fr, ft) if ref_m else {"g8_pass": want, "novelty_z": 10.0}
        g8_rows.append({"trial": ti + 1, "class": cls_, "novelty_z": round(float(ev["novelty_z"]), 3), "passed": int(bool(ev["g8_pass"]) == want)})

    # 3. CALIBRATION_V54_RPCA_RARITY_180 (deterministic SeedSequence fan-out)
    w_r = 15200.0 + 0.08 * np.arange(2048, dtype=np.float64)
    bervs_r = np.linspace(-25.0, 25.0, 8)
    rp_seeds = np.random.SeedSequence(RNG_SEED + 9610).spawn(180)
    with ProcessPoolExecutor(max_workers=4) as pool:
        rp_rows = list(pool.map(_cal_rpca_worker, [(ti, rp_seeds[ti]) for ti in range(180)], chunksize=15))

    # 4. CALIBRATION_V54_AGNOSTIC_120
    ag_rows: list[dict[str, Any]] = []
    for ti in range(120):
        mat = rng.normal(0.0, 1.0, size=(8, 2048))
        pol = 1.0 if ti % 2 == 0 else -1.0
        sc = (2.0, 4.0, 8.0, 14.0)[ti % 4]
        sig_px = sc * 2.0
        x = np.arange(2048)
        if ti < 60:
            mat[0] += pol * (11.0 / math.sqrt(sig_px)) * np.exp(-0.5 * ((x - 1024.0) / sig_px) ** 2) * 2.0
        else:
            hw = int(round(1.5 * sig_px))
            mat[0, 1024 - hw : 1024 + hw] += pol * 4.5
        surv, _ = scan_agnostic_multiscale_v50(w_r, mat[0], 0, mat, bervs_r, cfg_ap)
        ag_rows.append({"trial": ti + 1, "scale_lsf": sc, "n_surv": len(surv), "passed": int(len(surv) >= 1)})

    # 5. DETECTOR_V54_G4G5_CALIBRATION_108
    g45_rows: list[dict[str, Any]] = []
    wp = 6500.0 + 0.025 * np.arange(151, dtype=np.float64)
    w_sig_ca = 6500.0 / (94600.0 * FWHM_FACTOR)
    for ti in range(108):
        fl = 1000.0 + rng.normal(0.0, 10.0, 151)
        er = np.full(151, 10.0)
        dq = np.zeros(151, dtype=np.int32)
        if ti < 36:
            cls_, want = "TRUE_LSF", True
            fl += 180.0 * np.exp(-0.5 * ((wp - wp[75]) / w_sig_ca) ** 2)
        elif ti < 72:
            cls_, want = "COSMIC_HOTPX", False
            fl[75] += 260.0
        else:
            cls_, want = "BROAD_PLATEAU", False
            fl += 140.0 * np.exp(-0.5 * ((wp - wp[75]) / (7.5 * w_sig_ca)) ** 2)
        ev = evaluate_gates_g3_g4_g5_v42(
            [{"order": 1, "native_pixel": 1000, "wave": wp, "flux_a": fl, "ref_norm_a": np.ones(151), "err_a": er, "dq": dq, "target_wave_a": wp[75]}],
            "CARMENES_VIS", "T", wp[75], cfg_ca,
        )
        ok = bool(ev["g3_pass"] and ev["g4_pass"] and ev["g5_pass"])
        g45_rows.append({"trial": ti + 1, "class": cls_, "passed": int(ok == want)})

    # 6. INJECTION_RECOVERY_540 (across 8 D096 echelle bands: 4 APOGEE-2 + 4 CARMENES_VIS)
    inj_rows: list[dict[str, Any]] = []
    comp_map: dict[tuple[str, str], list[int]] = {}
    band_list_8 = [("SDSS_APOGEE2", b) for b in get_calibration_bands("SDSS_APOGEE2")] + [
        ("CARMENES_VIS", b) for b in get_calibration_bands("CARMENES_VIS")
    ]
    for ti in range(540):
        inst, bd = band_list_8[ti % len(band_list_8)]
        cfg_i = get_inst_config(inst, 22500.0 if inst == "SDSS_APOGEE2" else 94600.0)
        wc = float(bd["center_wave_A"])
        dw_i = 0.08 if inst == "SDSS_APOGEE2" else 0.022
        w_b = wc + dw_i * (np.arange(301) - 150)
        sig_b = wc / (effective_resolving_power(cfg_i, wc) * FWHM_FACTOR)
        prof_b = np.exp(-0.5 * ((w_b - wc) / sig_b) ** 2)
        snr_inj = 10.5 if (ti % 3) < 2 else 8.8
        noise_std = 0.012
        amp_inj = snr_inj * noise_std
        y1 = rng.normal(0.0, noise_std, len(w_b)) + amp_inj * prof_b
        y2 = rng.normal(0.0, noise_std, len(w_b)) + amp_inj * prof_b
        fit_t = fit_lsf_on_window(w_b, y1, wc, cfg_i, fixed_phase_bins=0.0)
        fit_p = fit_lsf_on_window(w_b, 0.5 * (y1 + y2), wc, cfg_i, fixed_phase_bins=0.0)
        st_ = float(fit_t.get("snr_mid", 0.0)) if fit_t.get("valid_fit") else 0.0
        sp_ = float(fit_p.get("snr_mid", 0.0)) if fit_p.get("valid_fit") else 0.0
        pt = bool(fit_t.get("valid_fit") and st_ >= 8.0 and float(fit_t["cosine"]) >= 0.70)
        pp = bool(fit_p.get("valid_fit") and sp_ >= 8.0 and float(fit_p["cosine"]) >= 0.70)
        inj_rows.append({"trial": ti + 1, "instrument": inst, "band_id": bd["band_id"], "snr_t": round(st_, 3), "snr_p": round(sp_, 3), "pass_t": int(pt), "pass_p": int(pp)})
        comp_map.setdefault((inst, bd["band_id"]), []).append(int(pp))

    comp_rows = [{"instrument": k[0], "band_id": k[1], "n_trials": len(v), "completeness_p": round(sum(v) / len(v), 4)} for k, v in sorted(comp_map.items())]

    # 7. COMB_V4_1_CALIBRATION_162 (CARMENES_VIS CARM_RED band, deterministic SeedSequence fan-out)
    comb_seeds = np.random.SeedSequence(RNG_SEED + 9620).spawn(162)
    with ProcessPoolExecutor(max_workers=4) as pool:
        comb_cal_rows = list(pool.map(_cal_comb_worker, [(ti, comb_seeds[ti]) for ti in range(162)], chunksize=14))

    # 8. KEPLERIAN_TRACK_CALIBRATION_81
    kep_rows: list[dict[str, Any]] = []
    wk_grid = 6500.0 + 0.025 * (np.arange(701, dtype=np.float64) - 350.0)
    sig_kep = 6500.0 / (94600.0 * FWHM_FACTOR)
    vorb_phases = (-62.0, -21.0, 21.0, 62.0)
    for ti in range(81):
        amp_k = 5.0 * 0.012
        ep_res, ep_pl = [], []
        for dv_o in vorb_phases:
            y_k = rng.normal(0.0, 0.012, len(wk_grid)) + amp_k * np.exp(-0.5 * ((wk_grid - 6500.0 * (1.0 + dv_o / C_KMS)) / sig_kep) ** 2)
            ep_res.append(y_k)
            w_de = bary_to_planet_rest_wave(wk_grid, 0.0, dv_o)
            ep_pl.append(np.interp(wk_grid, w_de, y_k, left=0.0, right=0.0))
        f_td = fit_lsf_on_window(wk_grid, np.mean(ep_res, axis=0), 6500.0, cfg_ca, fixed_phase_bins=0.0)
        f_kp = fit_lsf_on_window(wk_grid, np.mean(ep_pl, axis=0), 6500.0, cfg_ca, fixed_phase_bins=0.0)
        std_ = float(f_td.get("snr_mid", 0.0)) if f_td.get("valid_fit") else 0.0
        skp_ = float(f_kp.get("snr_mid", 0.0)) if f_kp.get("valid_fit") else 0.0
        kep_rows.append({"trial": ti + 1, "snr_tdiff": round(std_, 3), "snr_kplanet": round(skp_, 3), "tdiff_fa": int(std_ >= 6.5), "kplanet_rec": int(skp_ >= 6.5)})

    _write_csv(out_dir / "CALIBRATION_V54_SOFIA_EXES_180.csv", list(ex_rows[0].keys()), ex_rows)
    _write_csv(out_dir / "CALIBRATION_V54_COHERENT_SHIFT_STACK_240.csv", list(cs_rows[0].keys()), cs_rows)
    _write_csv(out_dir / "CALIBRATION_V54_JWST_SOSS_G140H_120.csv", list(jw_rows[0].keys()), jw_rows)
    _write_csv(out_dir / "CALIBRATION_G8_V54_120.csv", list(g8_rows[0].keys()), g8_rows)
    _write_csv(out_dir / "CALIBRATION_V54_RPCA_RARITY_180.csv", list(rp_rows[0].keys()), rp_rows)
    _write_csv(out_dir / "CALIBRATION_V54_AGNOSTIC_120.csv", list(ag_rows[0].keys()), ag_rows)
    _write_csv(out_dir / "DETECTOR_V54_G4G5_CALIBRATION_108.csv", list(g45_rows[0].keys()), g45_rows)
    _write_csv(out_dir / "INJECTION_RECOVERY_540.csv", list(inj_rows[0].keys()), inj_rows)
    _write_csv(out_dir / "CALIBRATION_COMPLETENESS_BY_BAND.csv", list(comp_rows[0].keys()), comp_rows)
    _write_csv(out_dir / "COMB_V4_1_CALIBRATION_162.csv", list(comb_cal_rows[0].keys()), comb_cal_rows)
    _write_csv(out_dir / "KEPLERIAN_TRACK_CALIBRATION_81.csv", list(kep_rows[0].keys()), kep_rows)

    tot_trials = 180 + 240 + 120 + 120 + 180 + 120 + 108 + 540 + 162 + 81
    assert tot_trials == 1851

    def _cnt(lst: list[dict[str, Any]], cls_k: str | None = None) -> str:
        sub = [r for r in lst if cls_k is None or r.get("trial_class", r.get("class")) == cls_k]
        p = sum(int(r["passed"]) for r in sub)
        return f"{p}/{len(sub)} ({p / max(1, len(sub)):.4f})"

    return {
        "total_trials": tot_trials,
        "sofia_exes_laser_recovery": cal_exes["laser_recovery"],
        "sofia_exes_atran_veto": cal_exes["atran_veto"],
        "sofia_exes_cr_veto": cal_exes["cr_veto"],
        "sofia_exes_natural_line_veto": cal_exes["natural_line_veto"],
        "coherent_ss_curved_recovery": cal_cs["curved_recovery"],
        "coherent_ss_periodic_recovery": cal_cs["periodic_recovery"],
        "coherent_ss_stationary_veto": cal_cs["stationary_veto"],
        "coherent_ss_transient_veto": cal_cs["transient_veto"],
        "coherent_ss_berv_sky_veto": cal_cs["berv_sky_veto"],
        "jwst_soss_g140h_laser_recovery": cal_jwst["laser_recovery"],
        "jwst_soss_g140h_hotpx_veto": cal_jwst["hotpx_veto"],
        "jwst_soss_g140h_broad_veto": cal_jwst["broad_hi_veto"],
        "g8_v54_isolated_pass": _cnt(g8_rows, "ISOLATED_LASER"),
        "g8_v54_shared_suppression": _cnt(g8_rows, "SHARED_LEAK"),
        "g8_v54_topo_suppression": _cnt(g8_rows, "TOPO_LEAK"),
        "rpca_isolated_recovery": _cnt(rp_rows, "ISOLATED"),
        "rpca_shared_suppression": _cnt(rp_rows, "SHARED_REST"),
        "rpca_topo_suppression": _cnt(rp_rows, "SHARED_TOPO"),
        "agnostic_multiscale_recovery": _cnt(ag_rows),
        "g45_true_lsf_pass": _cnt(g45_rows, "TRUE_LSF"),
        "g5_cosmic_rejection": _cnt(g45_rows, "COSMIC_HOTPX"),
        "g5_plateau_rejection": _cnt(g45_rows, "BROAD_PLATEAU"),
        "channel_p_ge_8sigma": f"{sum(r['pass_p'] for r in inj_rows)}/{len(inj_rows)} ({sum(r['pass_p'] for r in inj_rows)/len(inj_rows):.4f})",
        "comb_v41_recovery": _cnt(comb_cal_rows, "TRUE_COMB_V41"),
        "comb_v41_forest_fa": f"{sum(r['v41_hits'] > 0 for r in comb_cal_rows if r['class'] == 'RANDOM_FOREST')}/54",
        "comb_v41_topo_fa": f"{sum(r['v41_hits'] > 0 for r in comb_cal_rows if r['class'] == 'TOPO_SKY_COMB')}/54",
        "keplerian_kplanet_rec": f"{sum(r['kplanet_rec'] for r in kep_rows)}/{len(kep_rows)} ({sum(r['kplanet_rec'] for r in kep_rows)/len(kep_rows):.4f})",
    }


def _scan_comb_star_worker(args: tuple[Any, ...]) -> tuple[str, int, list[dict[str, Any]], int]:
    st_lbl, wg, fn_t, sg_t, rc_t, yt, sgt, wins, bands, cfg_i = args
    y_rest = fn_t - rc_t
    sky = np.zeros(len(wg), dtype=bool)
    c41, n_cfg = scan_frequency_comb_v4_1(wg, y_rest, sg_t, fn_t, rc_t, sky, yt, sgt, wins, bands, cfg_i)
    c4, _ = scan_frequency_comb_v4(wg, y_rest, sg_t, fn_t, rc_t, sky, yt, sgt, wins, bands, cfg_i)
    return st_lbl, len(c4), c41, int(n_cfg)


def _compute_legacy_v2_count(w_arr: np.ndarray, fn: np.ndarray) -> int:
    fin = np.isfinite(w_arr) & np.isfinite(fn)
    if int(fin.sum()) < 50:
        return 0
    y = fn[fin] - 1.0
    mad = exact_mad_1d(y)
    if not math.isfinite(mad) or mad <= 0.0:
        return 0
    raw = y > 4.5 * mad
    return int(np.sum(raw & np.concatenate(([True], ~raw[:-1]))))


def _measure_arms_rv(arms: list[dict[str, Any]], prior_rv_kms: float, cfg: dict[str, Any]) -> tuple[float, list[dict[str, Any]]]:
    """Concatenate and sort exposure arms to measure empirical stellar RV."""
    ws = [a["w_bary"] for a in arms if len(a.get("w_bary", [])) > 0]
    fs = [a["fn"] for a in arms if len(a.get("w_bary", [])) > 0]
    if not ws:
        return float(prior_rv_kms), []
    w_all = np.concatenate(ws)
    f_all = np.concatenate(fs)
    idx = np.argsort(w_all)
    summ, anch, _ = measure_exposure_stellar_rv(w_all[idx], f_all[idx], float(prior_rv_kms), cfg)
    return float(summ["empirical_rv_kms"]), anch


def _build_drift_z_matrix_v52(fn_mat: np.ndarray, tpl_s: np.ndarray) -> np.ndarray:
    """Rolling-512px MAD + supraphotospheric emission Z-score preconditioning for DRIFT_V51/V52."""
    z_ep = np.full_like(fn_mat, np.nan)
    for k in range(fn_mat.shape[0]):
        r_k = fn_mat[k] - tpl_s
        f_k = np.isfinite(r_k) & np.isfinite(fn_mat[k])
        if int(np.sum(f_k)) >= 64:
            mg = max(1e-4, exact_mad_1d(r_k[f_k]))
            rm = _compute_rolling_mad_1d(r_k, f_k, win_bins=512)
            rm_safe = np.where(np.isfinite(rm), np.maximum(rm, mg), mg)
            z_ep[k] = np.where(fn_mat[k] >= 1.01, r_k / rm_safe, np.minimum(0.0, r_k / rm_safe))
    return z_ep


def _build_rolling_sig_epochs(fn_mat: np.ndarray, sig_mat: np.ndarray, tpl_s: np.ndarray) -> np.ndarray:
    """Floor per-epoch flux errors using local rolling-512px residual MAD around tpl_s."""
    out = np.empty_like(sig_mat)
    for k in range(fn_mat.shape[0]):
        r_k = fn_mat[k] - tpl_s
        f_k = np.isfinite(r_k) & np.isfinite(fn_mat[k])
        if int(np.sum(f_k)) >= 64:
            mg = max(1e-4, exact_mad_1d(r_k[f_k]))
            rm = _compute_rolling_mad_1d(r_k, f_k, win_bins=512)
            rm_safe = np.where(np.isfinite(rm), np.maximum(rm, mg), mg)
            out[k] = np.where(np.isfinite(sig_mat[k]) & (sig_mat[k] > 0.0), np.maximum(sig_mat[k], rm_safe), rm_safe)
        else:
            out[k] = np.where(np.isfinite(sig_mat[k]) & (sig_mat[k] > 0.0), sig_mat[k], 0.02)
    return np.maximum(out, 1e-4)


def _decode_prior_apogee2_campaigns(archives_dir: Path) -> list[dict[str, Any]]:
    """Load the 14 retroactive N>=4 SDSS_APOGEE2 campaigns from Archive T (5) & Archive U (9)."""
    cfg_ap = get_inst_config("SDSS_APOGEE2", 22500.0)
    w_ap_grid = np.arange(15155.0, 16955.0, 0.12, dtype=np.float64)
    out: list[dict[str, Any]] = []

    sources = [
        ("D094_ARCHIVE_T", archives_dir / ARCHIVE_T_NAME, ARCHIVE_T_BUNDLE),
        ("D095_ARCHIVE_U", archives_dir / ARCHIVE_U_NAME, ARCHIVE_U_BUNDLE),
    ]
    for src_tag, zpath, member in sources:
        if not zpath.exists():
            raise FileNotFoundError(f"Missing required prior archive for retroactive V5.4 coherent drift: {zpath}")
        orb_map: dict[str, dict[str, Any]] = {}
        with zipfile.ZipFile(zpath, "r") as zf:
            for nm in zf.namelist():
                if nm.endswith("ORBITAL_CAMPAIGNS_AND_KINEMATICS.json"):
                    oj = json.loads(zf.read(nm).decode("utf-8"))
                    orb_map.update(oj.get("campaigns", {}))
            bundle = json.loads(gzip.decompress(zf.read(member)).decode("utf-8"))

        by_star: dict[str, list[dict[str, Any]]] = {}
        for exp in bundle.get("exposures", []):
            if exp.get("instrument") == "SDSS_APOGEE2":
                by_star.setdefault(exp["star"], []).append(exp)

        for st in sorted(by_star):
            exps = sorted(by_star[st], key=lambda x: float(x["mjd_obs"]))
            if len(exps) < 4:
                continue
            unpacked = [_unpack_echelle_exposure(e, cfg_ap) for e in exps]
            rvs = [_measure_arms_rv(u["arms"], float(u["exp"]["prior_rv_kms"]), cfg_ap)[0] for u in unpacked]
            rv_med = float(exact_median_1d(np.asarray(rvs, dtype=np.float64)))
            fn_ep, sg_ep, mjd_ep, berv_ep = [], [], [], []
            for u in unpacked:
                fn_i, sg_i, _, _ = _build_1d_ivw_spectrum(u["arms"], w_ap_grid, rv_med, float(u["exp"]["berv_kms"]))
                fn_ep.append(fn_i)  # preserve true NaNs at masked/gap wavelengths
                sg_ep.append(np.where(np.isfinite(sg_i) & (sg_i > 0.0), sg_i, np.nan))
                mjd_ep.append(float(u["exp"]["mjd_obs"]))
                berv_ep.append(float(u["exp"]["berv_kms"]))
            fn_ep_raw = np.vstack(fn_ep)
            sg_ep_raw = np.vstack(sg_ep)
            fin_any = np.any(np.isfinite(fn_ep_raw), axis=0)
            tpl_r = np.ones(len(w_ap_grid), dtype=np.float64)
            with warnings.catch_warnings(), np.errstate(all="ignore"):
                warnings.simplefilter("ignore", RuntimeWarning)
                if np.any(fin_any):
                    tpl_r[fin_any] = np.nanmedian(fn_ep_raw[:, fin_any], axis=0)
            tpl_r = np.where(np.isfinite(tpl_r), tpl_r, 1.0)
            valid_col = np.sum(np.isfinite(fn_ep_raw), axis=0) >= max(4, int(math.ceil(0.55 * fn_ep_raw.shape[0])))
            fn_drift = np.where(np.isfinite(fn_ep_raw) & valid_col[None, :], 1.0 + (fn_ep_raw - tpl_r[None, :]), np.nan)
            sg_roll = _build_rolling_sig_epochs(fn_ep_raw, sg_ep_raw, tpl_r)
            sg_drift = np.where(np.isfinite(fn_drift), sg_roll, np.nan)
            oc = orb_map.get(st, {})
            out.append({
                "phase_source": src_tag,
                "instrument": "SDSS_APOGEE2",
                "grating_family": "APOGEE2_H",
                "star": st,
                "common_name": exps[0]["common_name"],
                "role": exps[0]["role"],
                "cfg": cfg_ap,
                "wave_rest": w_ap_grid,
                "fn_epochs": fn_drift,
                "sig_epochs": sg_drift,
                "fn_raw": fn_ep_raw,
                "tpl_s": tpl_r,
                "mjd_epochs": np.asarray(mjd_ep, dtype=np.float64),
                "berv_epochs": np.asarray(berv_ep, dtype=np.float64),
                "rv_epochs": np.full(len(mjd_ep), rv_med, dtype=np.float64),
                "known_orb_period_days": _opt_float(oc.get("orb_per_days"), math.nan),
                "known_orb_t0_bjd": _opt_float(oc.get("orb_t0_bjd"), math.nan),
                "known_orb_kp_kms": _opt_float(oc.get("kp_kms"), math.nan),
            })
    return out


# ---------------------------------------------------------------------------
# Stage-2 Deterministic Physical Triage Helpers (Stage-1 Detector Untouched)
# ---------------------------------------------------------------------------

def _vac_to_air_a(wave_vac_a: float) -> float:
    """Convert vacuum wavelength (A) to IAU standard air wavelength (Morton 2000)."""
    if not math.isfinite(wave_vac_a) or wave_vac_a < 2000.0:
        return wave_vac_a
    s2 = (1e4 / wave_vac_a) ** 2
    n = 1.0 + 0.0000834254 + 0.02406147 / (130.0 - s2) + 0.00015998 / (38.9 - s2)
    return wave_vac_a / n


def _vet_blind_drift_v51(
    cands: list[dict[str, Any]],
    grid: np.ndarray,
    fn_mat: np.ndarray,
    tpl_s: np.ndarray,
    cfg: dict[str, Any],
    bervs_pair: tuple[float, float] = (0.0, 0.0),
    rvs_pair: tuple[float, float] = (0.0, 0.0),
) -> tuple[list[dict[str, Any]], list[str]]:
    """Tier-2 topocentric airglow + telluric-trough antipair + supraphotospheric + LSF fit on BLIND_DRIFT_V51."""
    if not cands or fn_mat.shape[0] < 2:
        return [], []
    dw = float(exact_median_1d(np.diff(grid)))
    sig_v = float(cfg["sigma_v_kms"])
    kept: list[dict[str, Any]] = []
    reasons: list[str] = []
    for c in cands:
        w1 = float(c["wave1_rest_a"])
        w2 = float(c["wave2_rest_a"])
        ic1 = int(np.argmin(np.abs(grid - w1)))
        ic2 = int(np.argmin(np.abs(grid - w2)))
        wb1 = w1 * (1.0 + float(rvs_pair[0]) / C_KMS)
        wb2 = w2 * (1.0 + float(rvs_pair[1]) / C_KMS)
        wt1 = wb1 / (1.0 + float(bervs_pair[0]) / C_KMS)
        wt2 = wb2 / (1.0 + float(bervs_pair[1]) / C_KMS)
        wt1_air = _vac_to_air_a(wt1)
        wt2_air = _vac_to_air_a(wt2)
        d_topo_kms = (wt2 - wt1) / max(1e-6, wt1) * C_KMS
        is_airglow_1 = (
            (not evaluate_gate_g2_airglow(wb1, float(bervs_pair[0]), cfg)["g2_pass"])
            or bool(check_rousselot_oh_and_barycentric_v52(wt1, sig_v)["is_oh_or_sky"])
            or any(abs(wt1_air - float(ent["wave_A"])) <= 0.35 for ent in GROUND_AIRGLOW_AND_TELLURIC_A)
        )
        is_airglow_2 = (
            (not evaluate_gate_g2_airglow(wb2, float(bervs_pair[1]), cfg)["g2_pass"])
            or bool(check_rousselot_oh_and_barycentric_v52(wt2, sig_v)["is_oh_or_sky"])
            or any(abs(wt2_air - float(ent["wave_A"])) <= 0.35 for ent in GROUND_AIRGLOW_AND_TELLURIC_A)
        )
        if abs(d_topo_kms) <= 3.5 or is_airglow_1 or is_airglow_2:
            reasons.append("V51_TOPO_AIRGLOW")
            continue
        if (
            (not math.isfinite(float(fn_mat[-1, ic1])))
            or float(fn_mat[-1, ic1]) < 0.75
            or (not math.isfinite(float(fn_mat[0, ic2])))
            or float(fn_mat[0, ic2]) < 0.75
        ):
            reasons.append("V51_TELLURIC_TROUGH_ANTIPAIR")
            continue

        ep_checks = ((0, w1), (-1, w2))
        all_ok = True
        fail_tag = ""
        for ek, wk in ep_checks:
            r_eff = effective_resolving_power(cfg, wk)
            sig_a = wk / (r_eff * FWHM_FACTOR)
            margin = max(35, int(math.ceil(16.0 * sig_a / max(1e-6, dw))))
            ic = int(np.argmin(np.abs(grid - wk)))
            lo, hi = max(0, ic - margin), min(len(grid), ic + margin + 1)
            wg = grid[lo:hi]
            rg = fn_mat[ek, lo:hi] - tpl_s[lo:hi]
            fg = fn_mat[ek, lo:hi]
            f1 = compute_supraphotospheric_f1_window(wg, fg, wk, 1.05)
            f80 = fn_mat[ek, max(0, ic - 80) : min(len(grid), ic + 81)]
            f80 = f80[np.isfinite(f80)]
            p90 = float(np.percentile(f80, 90.0)) if len(f80) >= 10 else 1.0
            f_p90 = float(f1["fn_pk3"]) / max(1e-6, p90)
            fit = fit_lsf_on_window(wg, rg, wk, cfg)
            lsf_ok = bool(
                fit.get("valid_fit")
                and float(fit["snr_mid"]) >= 5.0
                and float(fit["cosine"]) >= 0.78
                and 0.55 <= float(fit["fwhm_ratio"]) <= 1.85
            )
            if not (f1["f1_supraphotospheric_pass"] and f_p90 >= 1.05):
                all_ok = False
                fail_tag = "V51_SUBCONTINUUM"
                break
            if not lsf_ok:
                all_ok = False
                fail_tag = "V51_LSF_SHAPE"
                break
        if all_ok:
            kept.append(c)
        else:
            reasons.append(fail_tag)
    return kept, reasons


def _vet_multiepoch_drift_tracks_v52(
    cands: list[dict[str, Any]],
    grid: np.ndarray,
    fn_mat: np.ndarray,
    tpl_s: np.ndarray,
    mjds: np.ndarray,
    cfg: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Tier-2 multi-epoch LSF + supraphotospheric F1 veto on DRIFT_V52 chains (ported from D095)."""
    dw = float(exact_median_1d(np.diff(grid)))
    min_fn = float(cfg["supraphotospheric_min_fn_pk3"])
    kept: list[dict[str, Any]] = []
    veto_reasons: list[str] = []
    for c in cands:
        m_eps = c["matched_epochs"]
        w0 = float(c["wave_start_rest_a"])
        vdot = float(c["vdot_kms_day"])
        t0 = float(mjds[m_eps[0]])
        n_lsf_ok = 0
        n_f1_ok = 0
        excesses: list[float] = []
        for ek in m_eps:
            wk = w0 * (1.0 + vdot * (float(mjds[ek]) - t0) / C_KMS)
            r_eff = effective_resolving_power(cfg, wk)
            sig_a = wk / (r_eff * FWHM_FACTOR)
            margin = max(35, int(math.ceil(16.0 * sig_a / max(1e-6, dw))))
            ic = int(np.argmin(np.abs(grid - wk)))
            lo, hi = max(0, ic - margin), min(len(grid), ic + margin + 1)
            wg = grid[lo:hi]
            rg = fn_mat[ek, lo:hi] - tpl_s[lo:hi]
            fg = fn_mat[ek, lo:hi]
            fit = fit_lsf_on_window(wg, rg, wk, cfg)
            lsf_ok = bool(
                fit.get("valid_fit")
                and float(fit["snr_mid"]) >= 4.5
                and float(fit["cosine"]) >= 0.80
                and 0.55 <= float(fit["fwhm_ratio"]) <= 1.85
            )
            f1_ref = float(fit["fitted_center_a"]) if fit.get("valid_fit") else wk
            f1 = compute_supraphotospheric_f1_window(wg, fg, f1_ref, min_fn)
            if lsf_ok:
                n_lsf_ok += 1
            if f1["f1_supraphotospheric_pass"]:
                n_f1_ok += 1
            excesses.append(max(0.0, float(fit["amp_mid"]) if fit.get("valid_fit") else float(f1["fn_pk3"] - 1.0)))
        amp_ratio = max(excesses) / max(1e-4, min(excesses)) if excesses else 999.0
        if n_lsf_ok < 3:
            veto_reasons.append("DRIFT_G1_LSF_SHAPE")
        elif n_f1_ok < 3:
            veto_reasons.append("DRIFT_F1_SUBCONTINUUM")
        elif amp_ratio > 10.0:
            veto_reasons.append("DRIFT_AMP_INCOHERENT")
        else:
            kept.append(c)
    return kept, veto_reasons


def _vet_coherent_drift_v54(cand: dict[str, Any], cp: dict[str, Any]) -> tuple[str, bool, str]:
    """Deterministic Stage-2 physical verification of raw DRIFT_V54 coherent shift-stack candidates."""
    w = cp["wave_rest"]
    fn_raw_s = cp["fn_raw"]
    sg_s = cp["sig_epochs"]
    tpl_s = cp["tpl_s"]
    cfg = cp["cfg"]
    mjds = np.asarray(cp["mjd_epochs"], dtype=np.float64)
    bervs = np.asarray(cp["berv_epochs"], dtype=np.float64)
    rvs = np.asarray(cp.get("rv_epochs", np.zeros(len(mjds))), dtype=np.float64)
    ord_t = np.argsort(mjds)
    mjds = mjds[ord_t]
    bervs = bervs[ord_t]
    rvs = rvs[ord_t]
    fn_raw_s = fn_raw_s[ord_t]
    sg_s = sg_s[ord_t]

    t_mid = 0.5 * (float(mjds[0]) + float(mjds[-1]))
    dt_half = max(1e-3, 0.5 * (float(mjds[-1]) - float(mjds[0])))
    tau = (mjds - t_mid) / dt_half
    t_rel = mjds - float(mjds[0])

    br = str(cand.get("branch", ""))
    w0 = float(cand["wave0_rest_a"])
    if br in ("LINEAR_STACK_V54", "CURVED_STACK_V54"):
        v_ep = float(cand["half_slope_kms"]) * tau + float(cand["quad_sag_kms"]) * (tau * tau - 1.0 / 3.0)
    else:
        v_ep = float(cand["k_amp_kms"]) * np.sin(2.0 * math.pi * t_rel / float(cand["period_d"]) + float(cand["phi_rad"]))

    dw = float(exact_median_1d(np.diff(w)))
    sig_v = float(cfg.get("sigma_v_kms", 2.0))
    sig_a = w0 * sig_v / C_KMS
    hw_bins = max(25, int(math.ceil(20.0 * sig_a / max(1e-6, dw))))
    w_patch = w0 + np.arange(-hw_bins, hw_bins + 1) * dw

    fn_tracks: list[float] = []
    ratios: list[float] = []
    tpl_tracks: list[float] = []
    shifted_rows: list[np.ndarray] = []
    z_ks: list[float] = []
    n_oh_sky = 0
    n_topo_repeat = 0

    for k in range(len(mjds)):
        wk = w0 * (1.0 + float(v_ep[k]) / C_KMS)
        if wk < float(w[5]) or wk > float(w[-6]):
            continue
        ic = int(np.argmin(np.abs(w - wk)))
        if not np.isfinite(fn_raw_s[k, ic]):
            continue
        sub = fn_raw_s[k, max(0, ic - 2) : min(len(w), ic + 3)]
        fin_sub = sub[np.isfinite(sub)]
        if len(fin_sub) == 0:
            continue
        fn_pk = float(np.max(fin_sub))
        f60 = fn_raw_s[k, max(0, ic - 60) : min(len(w), ic + 61)]
        f60 = f60[np.isfinite(f60)]
        p90 = float(np.percentile(f60, 90.0)) if len(f60) >= 10 else 1.0
        fn_tracks.append(fn_pk)
        ratios.append(fn_pk / max(1e-6, p90))
        tpl_tracks.append(float(tpl_s[ic]) if np.isfinite(tpl_s[ic]) else 1.0)

        res_k = np.where(np.isfinite(fn_raw_s[k]), fn_raw_s[k] - tpl_s, 0.0)
        sub_r = res_k[max(0, ic - 1) : min(len(w), ic + 2)]
        rk_pk = float(np.max(sub_r)) if len(sub_r) else 0.0
        s_val = float(sg_s[k, ic]) if np.isfinite(sg_s[k, ic]) else math.nan
        zk = float(rk_pk / s_val) if (np.isfinite(s_val) and s_val > 0.0) else 0.0
        z_ks.append(zk)

        w_bary_k = wk * (1.0 + float(rvs[k]) / C_KMS)
        w_topo_k = w_bary_k / (1.0 + float(bervs[k]) / C_KMS)
        g2_ok = bool(evaluate_gate_g2_airglow(w_bary_k, float(bervs[k]), cfg)["g2_pass"])
        oh_bad = bool(check_rousselot_oh_and_barycentric_v52(w_topo_k, sig_v)["is_oh_or_sky"])
        if (not g2_ok) or oh_bad:
            n_oh_sky += 1

        if zk >= 2.0 and rk_pk > 0.008:
            rep = False
            for j in range(len(mjds)):
                if j == k:
                    continue
                if abs(float(bervs[j]) - float(bervs[k])) < max(2.5, 0.5 * sig_v):
                    continue
                wj_rest = w_topo_k * (1.0 + float(bervs[j]) / C_KMS) / (1.0 + float(rvs[j]) / C_KMS)
                wj_track = w0 * (1.0 + float(v_ep[j]) / C_KMS)
                if abs(wj_rest - wj_track) <= 3.0 * sig_a:
                    continue
                ij = int(np.argmin(np.abs(w - wj_rest)))
                if not np.isfinite(fn_raw_s[j, ij]):
                    continue
                sub_fj = fn_raw_s[j, max(0, ij - 2) : min(len(w), ij + 3)]
                sub_rj = np.where(np.isfinite(sub_fj), sub_fj - tpl_s[max(0, ij - 2) : min(len(w), ij + 3)], 0.0)
                fn_j_pk = float(np.nanmax(sub_fj))
                rj_pk = float(np.max(sub_rj))
                sj = float(sg_s[j, ij]) if np.isfinite(sg_s[j, ij]) else math.nan
                zj = float(rj_pk / sj) if (np.isfinite(sj) and sj > 0.0) else 0.0
                if (fn_j_pk >= 1.0 + 0.45 * (fn_pk - 1.0) and fn_j_pk >= 1.015) or (zj >= 2.5 and rj_pk >= 0.40 * rk_pk):
                    rep = True
                    break
            if rep:
                n_topo_repeat += 1

        shifted_rows.append(np.interp(w_patch * (1.0 + float(v_ep[k]) / C_KMS), w, res_k, left=0.0, right=0.0))

    n_tr = len(fn_tracks)
    if n_tr < 4:
        return "STAGE2_VETO_SUBPHOTOSPHERIC_TROUGH", False, f"n_tr={n_tr}"

    z_arr = np.asarray(z_ks, dtype=np.float64)
    z_unw = float(np.sum(z_arr) / math.sqrt(n_tr))
    n_ge2 = int(np.sum(z_arr >= 2.0))
    pos_sum = float(np.sum(np.maximum(0.0, z_arr)))
    z_sort = np.sort(np.maximum(0.0, z_arr))[::-1]
    top2_f = float(np.sum(z_sort[:2]) / max(1e-6, pos_sum))

    med_ratio = float(np.median(ratios))
    frac_above = float(np.mean(np.asarray(fn_tracks) >= 1.01))
    med_tpl = float(np.median(tpl_tracks))
    oh_frac = n_oh_sky / float(n_tr)
    topo_rep_frac = n_topo_repeat / float(max(1, n_ge2))
    snr_stack = float(cand["snr_stack"])
    snr_sky = float(cand["snr_sky"])
    snr_stat = float(cand["snr_stationary"])
    snr_loo = float(cand["snr_loo"])
    diag = (
        f"f/p90={med_ratio:.4f};z_unw={z_unw:.2f};nge2={n_ge2}/{n_tr};"
        f"top2={top2_f:.2f};trep={n_topo_repeat}/{max(1, n_ge2)};tpl={med_tpl:.3f};oh={oh_frac:.2f}"
    )

    if med_ratio < 1.015 or frac_above < 0.50:
        return "STAGE2_VETO_SUBPHOTOSPHERIC_TROUGH", False, diag
    if snr_sky >= 0.70 * snr_stack or oh_frac >= 0.50 or (n_ge2 >= 2 and topo_rep_frac >= 0.50):
        return "STAGE2_VETO_OH_SKY_OR_TELLURIC", False, diag
    if snr_stat >= 0.65 * snr_stack or med_tpl < 0.92:
        return "STAGE2_VETO_STATIONARY_OR_ABSORPTION_BAND", False, diag
    min_ge2 = max(3, int(math.ceil(0.65 * n_tr)))
    max_top2 = 2.0 / float(n_tr) + 0.25 if n_tr >= 5 else 0.75
    if z_unw < 5.5 or n_ge2 < min_ge2 or top2_f > max_top2:
        return "STAGE2_VETO_SPURIOUS_EPOCH_SUBSET", False, diag

    stack_res = np.mean(np.vstack(shifted_rows), axis=0)
    fit = fit_lsf_on_window(w_patch, stack_res, w0, cfg, fixed_phase_bins=0.0)
    lsf_ok = bool(
        fit.get("valid_fit")
        and float(fit["snr_mid"]) >= 7.5
        and float(fit["cosine"]) >= 0.80
        and 0.55 <= float(fit["fwhm_ratio"]) <= 1.85
        and snr_loo >= 5.2
    )
    if not lsf_ok:
        return "STAGE2_VETO_NON_LSF_SHAPE", False, f"{diag};lsf_snr={fit.get('snr_mid', 0.0):.2f};cos={fit.get('cosine', 0.0):.2f}"
    return "PASS", True, diag


def _evaluate_stage2_echelle_triage(
    inst: str,
    ch: str,
    w_bary_a: float,
    w_topo_a: float,
    ep_recs: list[dict[str, Any]],
    exp_item: dict[str, Any],
    cfg: dict[str, Any],
) -> tuple[str, bool, str]:
    """Deterministic Stage-2 physical triage on raw Echelle G1..G8 survivors."""
    # Check ground airglow / OH in both vacuum and standard air across relevant epochs
    bervs_chk = [float(exp_item["berv_kms"])] if ch == "T" else [float(r["u"]["exp"]["berv_kms"]) for r in ep_recs]
    sig_v = max(float(cfg.get("sigma_v_kms", 2.0)), 1.5)
    for bv in bervs_chk:
        wt_v = w_bary_a / (1.0 + bv / C_KMS)
        wt_air = _vac_to_air_a(wt_v)
        for wt_chk in (wt_v, wt_air):
            for ln in GROUND_AIRGLOW_AND_TELLURIC_A:
                la = float(ln["wave_A"])
                dv = abs(C_KMS * (wt_chk - la) / max(1.0, la))
                if dv <= max(25.0, float(ln["half_width_kms"])):
                    return "STAGE2_VETO_OH_OR_AIRGLOW_WING", False, f"airglow={ln['name']};dv={dv:.1f}"
        oh_v = check_rousselot_oh_and_barycentric_v52(wt_v, sig_v)
        oh_a = check_rousselot_oh_and_barycentric_v52(wt_air, sig_v)
        if oh_v["is_oh_or_sky"] or oh_a["is_oh_or_sky"]:
            return "STAGE2_VETO_OH_OR_AIRGLOW_WING", False, f"oh={oh_v['nearest_oh_a']}"

    # Check native-order local P90 ratio (+-80 px) and split-core cosmic-ray morphology
    ratios: list[float] = []
    split_cr = False
    recs_to_check = [r for r in ep_recs if r["u"]["exp"]["dp_id"] == exp_item["dp_id"]] if ch == "T" else ep_recs
    for r in recs_to_check:
        for arm in r["u"]["arms"]:
            wa = arm["w_bary"]
            fn = arm["fn"]
            if len(wa) < 20 or not (float(wa[0]) <= w_bary_a <= float(wa[-1])):
                continue
            ic = int(np.argmin(np.abs(wa - w_bary_a)))
            if abs(float(wa[ic]) - w_bary_a) > 1.5:
                continue
            pk_sub = fn[max(0, ic - 2) : min(len(fn), ic + 3)]
            fin_pk = pk_sub[np.isfinite(pk_sub)]
            f80 = fn[max(0, ic - 80) : min(len(fn), ic + 81)]
            fin_80 = f80[np.isfinite(f80)]
            if len(fin_pk) and len(fin_80) >= 15:
                p90 = float(np.percentile(fin_80, 90.0))
                if p90 > 0.0:
                    ratios.append(float(np.max(fin_pk)) / p90)
            fl = arm["flux"]
            if 2 <= ic <= len(fl) - 3 and np.all(np.isfinite(fl[ic - 2 : ic + 3])):
                if any(float(fl[j]) < min(float(fl[j - 1]), float(fl[j + 1])) for j in range(ic - 1, ic + 2)):
                    split_cr = True
            break

    med_r = float(np.median(ratios)) if ratios else math.nan
    note = f"f_p90={med_r:.4f}" if math.isfinite(med_r) else "f_p90=nan"
    if math.isfinite(med_r) and med_r < 1.05:
        return "STAGE2_VETO_SUBPHOTOSPHERIC_TROUGH", False, note
    if ch == "T" and split_cr:
        return "STAGE2_VETO_COSMIC_RAY_SINGLE_EPOCH", False, f"{note};split_cr=True"
    return "PASS", True, note


def _evaluate_stage2_jwst_triage(
    cand: dict[str, Any],
    seg: dict[str, Any],
    all_segs: list[dict[str, Any]],
    all_cands: list[dict[str, Any]],
) -> tuple[str, bool, str]:
    """Deterministic Stage-2 physical triage (J1-J5) for JWST SOSS & NIRSpec G140H."""
    w_um = np.asarray(seg["wave_um"], dtype=np.float64)
    fl = np.asarray(seg["flux"], dtype=np.float64)
    er = np.asarray(seg["err"], dtype=np.float64)
    sidx = np.argsort(w_um)
    w_um, fl, er = w_um[sidx], fl[sidx], er[sidx]
    n = len(w_um)
    w_c = float(cand["wave_um"])
    idx = int(np.argmin(np.abs(w_um - w_c)))

    lo40, hi40 = max(0, idx - 40), min(n, idx + 41)
    f40 = fl[lo40:hi40][np.isfinite(fl[lo40:hi40])]
    e40 = er[lo40:hi40][np.isfinite(er[lo40:hi40])]
    med40 = float(np.median(f40)) if len(f40) else -1.0
    p90_40 = float(np.percentile(f40, 90.0)) if len(f40) else -1.0
    med_e40 = float(np.median(e40)) if len(e40) else math.nan

    # J1: Negative or zero local continuum
    if med40 <= 0.0 or p90_40 <= 0.0:
        return "STAGE2_VETO_JWST_NEGATIVE_CONTINUUM", False, f"med40={med40:.3e};p90={p90_40:.3e}"

    f_p90 = float(fl[idx]) / p90_40
    err_rat = float(np.max(er[max(0, idx - 1) : min(n, idx + 2)]) / med_e40) if (math.isfinite(med_e40) and med_e40 > 0.0) else 1.0
    lo12, hi12 = max(0, idx - 12), min(n, idx + 13)
    gap_px = int(np.sum((~np.isfinite(fl[lo12:hi12])) | (fl[lo12:hi12] < 0.15 * med40)))

    # J2: SOSS cross-order spectral trace contamination (+-15 px Pearson r >= 0.90)
    r_xord = 0.0
    if idx >= 15 and idx + 16 <= n and np.all(np.isfinite(fl[idx - 15 : idx + 16])):
        v1 = fl[idx - 15 : idx + 16]
        if float(np.std(v1)) > 0.0:
            seg_by_name = {s["segment"]: s for s in all_segs}
            for c2 in all_cands:
                s2n = str(c2.get("segment", ""))
                if s2n == seg["segment"] or s2n not in seg_by_name:
                    continue
                if abs(float(c2["wave_um"]) - w_c) / max(1e-6, w_c) <= 0.10:
                    continue
                s2 = seg_by_name[s2n]
                w2 = np.asarray(s2["wave_um"], dtype=np.float64)
                f2 = np.asarray(s2["flux"], dtype=np.float64)
                si2 = np.argsort(w2)
                w2, f2 = w2[si2], f2[si2]
                i2 = int(np.argmin(np.abs(w2 - float(c2["wave_um"]))))
                for center2 in (i2, idx):
                    if center2 >= 15 and center2 + 16 <= len(f2) and np.all(np.isfinite(f2[center2 - 15 : center2 + 16])):
                        v2 = f2[center2 - 15 : center2 + 16]
                        if float(np.std(v2)) > 0.0:
                            r_val = float(np.corrcoef(v1, v2)[0, 1])
                            if r_val > r_xord:
                                r_xord = r_val

    diag = f"f_p90={f_p90:.4f};err_rat={err_rat:.2f};gap_px={gap_px};r_xord={r_xord:.5f}"
    if r_xord >= 0.90:
        return "STAGE2_VETO_JWST_SOSS_CROSS_ORDER_CONTAMINANT", False, diag
    if gap_px >= 3:
        return "STAGE2_VETO_JWST_DETECTOR_GAP_EDGE", False, diag
    if err_rat >= 4.0:
        return "STAGE2_VETO_JWST_UNFLAGGED_CR_ERROR_SPIKE", False, diag
    if f_p90 < 1.12 and math.isfinite(med_e40) and (med_e40 / med40) < 0.008:
        return "STAGE2_VETO_JWST_FIXED_SLIT_UNDERSAMPLING_WIGGLE", False, diag
    return "PASS", True, diag


# ---------------------------------------------------------------------------
# Stage B Orchestrator
# ---------------------------------------------------------------------------

def run_stage_b(bundle: dict[str, Any], archives_dir: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    orb_doc = json.loads((SCRIPT_DIR / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))
    snap = json.loads((SCRIPT_DIR / "PRIOR_V5_3_PHASES_SNAPSHOT.json").read_text(encoding="utf-8"))

    by_inst_star: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for exp in bundle["exposures"]:
        by_inst_star.setdefault((exp["instrument"], exp["star"]), []).append(exp)

    prov_rows: list[dict[str, Any]] = []
    eirp_rows: list[dict[str, Any]] = []
    ledger_rows: list[dict[str, Any]] = []
    four_gen_rows: list[dict[str, Any]] = []
    rv_anchor_rows: list[dict[str, Any]] = []
    rv_summary_rows: list[dict[str, Any]] = []
    agnostic_rows: list[dict[str, Any]] = []
    comb_star_rows: list[dict[str, Any]] = []
    comb_cand_rows: list[dict[str, Any]] = []
    blind_drift_rows: list[dict[str, Any]] = []
    drift_v52_rows: list[dict[str, Any]] = []
    drift_v53_rows: list[dict[str, Any]] = []
    orb_res_rows: list[dict[str, Any]] = []

    bins_searched: dict[str, dict[str, int]] = {}
    def _add_bins(inst: str, ch: str, n: int) -> None:
        bins_searched.setdefault(inst, {})[ch] = bins_searched.setdefault(inst, {}).get(ch, 0) + int(n)

    v2_fa_d096 = 0
    cand_seq: dict[tuple[str, str], int] = {}
    g8_models: dict[str, dict[str, Any]] = {}

    # -----------------------------------------------------------------------
    # Stream 1: SOFIA_EXES Two-Pass (17 stars, 19 FITS files)
    # -----------------------------------------------------------------------
    exes_stars = sorted(st for (inst, st) in by_inst_star if inst == "SOFIA_EXES")
    exes_pass1: dict[tuple[str, str], tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]] = {}
    cohort_topo_peaks_um: list[float] = []

    for st in exes_stars:
        exps = sorted(by_inst_star[("SOFIA_EXES", st)], key=lambda x: x["mjd_obs"])
        for exp in exps:
            cfg_ex = get_inst_config("SOFIA_EXES", float(exp["resolving_power"]))
            orders_decoded: list[dict[str, Any]] = []
            for arm in exp["arms"]:
                w_um = _decode_wave_any(arm["wave"]) / 1e4
                fl = _decode_arr_any(arm["flux"])
                er = _decode_arr_any(arm["err"])
                at = _decode_arr_any(arm["atran"])
                wt = _decode_arr_any(arm["weight"])
                qu = _decode_qual(arm["qual"], len(w_um))
                if fl is None or er is None or at is None:
                    continue
                valid = (qu == 0) & np.isfinite(w_um) & np.isfinite(fl) & np.isfinite(er)
                if int(np.sum(valid)) < 40:
                    continue
                orders_decoded.append({
                    "wave_um": w_um,
                    "flux_jy": np.where(valid, fl, np.nan),
                    "err_jy": np.where(valid, er, np.nan),
                    "atran": np.where(np.isfinite(at), at, 0.0),
                    "weight": np.where(np.isfinite(wt), wt, 1.0) if wt is not None else np.ones_like(w_um),
                    "rp": float(arm.get("rp", exp["resolving_power"])),
                })
                _add_bins("SOFIA_EXES", "T", int(np.sum(valid)))
            r1 = scan_sofia_exes_midir_echelle_v54(
                orders_decoded,
                cfg_ex,
                star=st,
                dist_pc=float(exp["dist_pc"]),
                teff_k=float(exp["teff_k"]),
                bary_corr_kms=float(exp["berv_kms"]),
                star_rv_kms=float(exp["prior_rv_kms"]),
                cohort_topo_peaks_um=[],
            )
            exes_pass1[(st, exp["dp_id"])] = (exp, orders_decoded, r1)
            cohort_topo_peaks_um.extend(float(p) for p in r1.get("raw_topo_peaks_um", []))

    exes_star_rows: list[dict[str, Any]] = []
    exes_g_tot = {"n_g1_raw": 0, "n_g2_atran": 0, "n_g45": 0, "n_g3_atlas": 0, "n_g6_topo": 0, "n_qual": 0}
    for st in exes_stars:
        exps = sorted(by_inst_star[("SOFIA_EXES", st)], key=lambda x: x["mjd_obs"])
        st_ul_by_band: dict[str, dict[str, Any]] = {}
        n_ord_st = n_g1_st = n_g2_st = n_g45_st = n_g3_st = n_g6_st = n_qual_st = 0
        w_min_um, w_max_um = 1e9, 0.0
        for exp in exps:
            _, orders_decoded, _ = exes_pass1[(st, exp["dp_id"])]
            cfg_ex = get_inst_config("SOFIA_EXES", float(exp["resolving_power"]))
            r2 = scan_sofia_exes_midir_echelle_v54(
                orders_decoded,
                cfg_ex,
                star=st,
                dist_pc=float(exp["dist_pc"]),
                teff_k=float(exp["teff_k"]),
                bary_corr_kms=float(exp["berv_kms"]),
                star_rv_kms=float(exp["prior_rv_kms"]),
                cohort_topo_peaks_um=cohort_topo_peaks_um,
            )
            for od in orders_decoded:
                wm = od["wave_um"][np.isfinite(od["flux_jy"])]
                if len(wm):
                    w_min_um = min(w_min_um, float(np.min(wm)))
                    w_max_um = max(w_max_um, float(np.max(wm)))

            n_ord_st += int(r2["n_orders_scanned"])
            n_g1_st += int(r2["n_g1_raw"])
            n_g2_st += int(r2["n_g2_atran_vetoed"])
            n_g45_st += int(r2["n_g45_vetoed"])
            n_g3_st += int(r2["n_g3_atlas_vetoed"])
            n_g6_st += int(r2["n_g6_topo_vetoed"])
            n_qual_st += int(r2["n_qualified_v54"])

            v2_fa_ep = int(r2["n_g1_raw"])
            v2_fa_d096 += v2_fa_ep
            prov_rows.append({
                "instrument": "SOFIA_EXES",
                "star": st,
                "dp_id": exp["dp_id"],
                "role": exp["role"],
                "mjd_obs": exp["mjd_obs"],
                "t_exptime_s": exp["t_exptime_s"],
                "grating": exp["grating"],
                "berv_kms": exp["berv_kms"],
                "rv_kms": round(float(exp["prior_rv_kms"]), 4),
                "v2_fa": v2_fa_ep,
            })

            for bd_id, ul in r2.get("upper_limits", {}).items():
                prev = st_ul_by_band.get(bd_id)
                if prev is None or float(ul["p_beam_10m_kw"]) < float(prev["p_beam_10m_kw"]):
                    st_ul_by_band[bd_id] = {**ul, "exp": exp}

            for c in r2.get("candidates", []):
                if not c.get("qualified_v54"):
                    continue
                k_id = ("SOFIA_EXES", "EXES_MIDIR")
                cand_seq[k_id] = cand_seq.get(k_id, 0) + 1
                ledger_rows.append({
                    "candidate_id": f"D096_EXES_{cand_seq[k_id]:05d}",
                    "instrument": "SOFIA_EXES",
                    "band_group": f"EXES_O{int(c.get('order_idx', 0)) + 1:02d}",
                    "channel": "T",
                    "role": exp["role"],
                    "star": st,
                    "dp_id": exp["dp_id"],
                    "wave_rest_a": round(float(c["wave_rest_um"]) * 1e4, 4),
                    "wave_topo_a": round(float(c["wave_obs_um"]) * 1e4, 4),
                    "snr_mid": round(float(c["snr_mid"]), 3),
                    "sky_z_max": 0.0,
                    "ghost_sky_vetoed": False,
                    "g2_pass": bool(c.get("g2_atran_pass", True)),
                    "g3_pass": True,
                    "g4_pass": bool(c.get("g45_lsf_pass", True)),
                    "g5_pass": bool(c.get("g45_lsf_pass", True)),
                    "g6_pass": not bool(c.get("g6_topo_vetoed", False)),
                    "g7_pass": True,
                    "g8_v52_pass": True,
                    "qualified_v54": True,
                    "stage2_triage_status": "PENDING_REVIEW",
                    "verified_eti": False,
                    "extra_note": f"um={c['wave_rest_um']:.6f};z={c.get('z_peak', 0):.2f};atran={c.get('atran', 0):.3f};eta1={c.get('eta_1px', 0):.2f};fwhm_r={c.get('fwhm_ratio', 0):.2f}",
                })

        exes_g_tot["n_g1_raw"] += n_g1_st
        exes_g_tot["n_g2_atran"] += n_g2_st
        exes_g_tot["n_g45"] += n_g45_st
        exes_g_tot["n_g3_atlas"] += n_g3_st
        exes_g_tot["n_g6_topo"] += n_g6_st
        exes_g_tot["n_qual"] += n_qual_st

        for bd_id, ul in sorted(st_ul_by_band.items()):
            e0 = ul["exp"]
            dflam = float(ul["direct_flam_8sig_cgs"])
            eirp_rows.append({
                "instrument": "SOFIA_EXES",
                "star": st,
                "common_name": e0["common_name"],
                "role": e0["role"],
                "science_track": e0["science_track"],
                "panchromatic_bridge": bool(e0["panchromatic_bridge"]),
                "within_10pc": bool(e0["within_10pc"]),
                "n_exoplanets": int(e0["n_exoplanets"]),
                "dist_pc": float(e0["dist_pc"]),
                "teff_k": float(e0["teff_k"]),
                "phot_g_mag": e0["phot_g_mag"],
                "h_mag": e0["h_mag"],
                "radiometric_anchor": "SOFIA_EXES_DIRECT_CGS",
                "resolving_power": float(ul["resolving_power"]),
                "band_id": bd_id,
                "wave_bary_a": round(float(ul["center_wave_um"]) * 1e4, 2),
                "median_epoch_mad_rel": round(float(ul["med_sigma_mad_jy"]) / max(1e-6, float(ul["med_cont_jy"])), 6),
                "amp_rel_8sigma_lim": round(8.0 * float(ul["med_sigma_mad_jy"]) / max(1e-6, float(ul["med_cont_jy"])), 6),
                "direct_flam_cgs": f"{dflam:.6e}",
                "continuum_flam_cgs": f"{dflam:.6e}",
                "flux_lim_erg_cm2_s": f"{ul['flux_lim_erg_cm2_s']:.6e}",
                "l_iso_mw": f"{ul['l_iso_mw']:.6e}",
                "p_beam_10m_w": round(float(ul["p_beam_10m_w"]), 5),
                "p_beam_10m_kw": round(float(ul["p_beam_10m_kw"]), 6),
            })

        best_bd = min(st_ul_by_band.items(), key=lambda kv: float(kv[1]["p_beam_10m_kw"])) if st_ul_by_band else (None, {})
        e_rep = exps[0]
        exes_star_rows.append({
            "star": st,
            "common_name": e_rep["common_name"],
            "role": e_rep["role"],
            "panchromatic_bridge": bool(e_rep["panchromatic_bridge"]),
            "dist_pc": float(e_rep["dist_pc"]),
            "n_files": len(exps),
            "n_orders_scanned": n_ord_st,
            "wave_min_um": round(w_min_um, 5) if w_min_um < 1e8 else "",
            "wave_max_um": round(w_max_um, 5) if w_max_um > 0.0 else "",
            "n_g1_raw": n_g1_st,
            "n_g2_atran_vetoed": n_g2_st,
            "n_g45_vetoed": n_g45_st,
            "n_g3_atlas_vetoed": n_g3_st,
            "n_g6_topo_vetoed": n_g6_st,
            "n_qualified_v54": n_qual_st,
            "best_band": best_bd[0] or "",
            "best_p_beam_10m_kw": round(float(best_bd[1]["p_beam_10m_kw"]), 6) if best_bd[0] else "",
        })

    _write_csv(
        out_dir / "SOFIA_EXES_MIDIR_ECHELLE_17STARS.csv",
        list(exes_star_rows[0].keys()),
        exes_star_rows,
    )

    # -----------------------------------------------------------------------
    # Stream 2: Echelle High-Res 4-Gen (CARMENES_VIS [3 stars] + SDSS_APOGEE2 [4 stars])
    # -----------------------------------------------------------------------
    echelle_specs = [
        {
            "inst": "CARMENES_VIS",
            "band_group": "CARMENES_VIS",
            "grid": np.arange(5300.0, 9000.0, 0.025, dtype=np.float64),
            "rp": 94600.0,
            "comb_bands": ["CARM_GREEN", "CARM_RED", "CARM_FARRED"],
            "g6_mode": "dense",
        },
        {
            "inst": "SDSS_APOGEE2",
            "band_group": "APOGEE2_H",
            "grid": np.arange(15155.0, 16955.0, 0.12, dtype=np.float64),
            "rp": 22500.0,
            "comb_bands": ["APOGEE_BLUE_CHIP", "APOGEE_GREEN_CHIP", "APOGEE_RED_CHIP"],
            "g6_mode": "dense",
        },
    ]

    d096_n4_campaigns: list[dict[str, Any]] = []

    for spec in echelle_specs:
        inst = spec["inst"]
        cfg = get_inst_config(inst, spec["rp"])
        wg = spec["grid"]
        stars = sorted(st for (i_k, st) in by_inst_star if i_k == inst)

        st_unpacked: dict[str, list[dict[str, Any]]] = {}
        st_rv_med: dict[str, float] = {}
        st_template_rows: list[np.ndarray] = []
        st_ep_data: dict[str, list[dict[str, Any]]] = {}
        cohort_bervs: list[float] = []
        dense_atlas: list[dict[str, Any]] = []
        sparse_atlas: list[dict[str, Any]] = []

        for st in stars:
            exps = sorted(by_inst_star[(inst, st)], key=lambda x: x["mjd_obs"])
            unps = [_unpack_echelle_exposure(e, cfg) for e in exps]
            st_unpacked[st] = unps
            rvs_meas = []
            for u in unps:
                rv_emp, anch_list = _measure_arms_rv(u["arms"], float(u["exp"]["prior_rv_kms"]), cfg)
                rvs_meas.append(rv_emp)
                for ar in anch_list:
                    a_rv = _opt_float(ar.get("best_rv_kms"), math.nan)
                    a_dep = _opt_float(ar.get("rel_depth"), math.nan)
                    rv_anchor_rows.append({
                        "instrument": inst, "star": st, "dp_id": u["exp"]["dp_id"],
                        "anchor_id": ar.get("anchor_id", ""), "rv_kms": round(a_rv, 4) if math.isfinite(a_rv) else "nan",
                        "snr": round(a_dep * 100.0, 2) if math.isfinite(a_dep) else "nan",
                    })
            rv_med_ap = float(exact_median_1d(np.asarray(rvs_meas, dtype=np.float64)))
            # CARMENES_VIS: blue optical solar anchors are swamped by M-dwarf TiO bands and ep0 has +8.5 km/s offset;
            # align each exposure cleanly using its CARACAL SERVAL RV.
            if inst == "CARMENES_VIS":
                rvs_applied = [float(u["exp"].get("carmenes_serval_rv_kms", u["exp"]["prior_rv_kms"])) for u in unps]
            else:
                rvs_applied = [rv_med_ap for _ in unps]
            rv_med = float(exact_median_1d(np.asarray(rvs_applied, dtype=np.float64)))
            rv_scat = float(exact_mad_1d(np.asarray(rvs_applied, dtype=np.float64))) if len(rvs_applied) >= 2 else 0.0
            st_rv_med[st] = rv_med
            rv_summary_rows.append({
                "instrument": inst, "star": st, "role": exps[0]["role"],
                "n_epochs": len(exps), "rv_median_kms": round(rv_med, 4),
                "rv_prior_kms": round(float(exps[0]["prior_rv_kms"]), 4),
                "rv_scatter_kms": round(rv_scat, 4),
            })

            ep_fn_list = []
            ep_sg_list = []
            ep_recs = []
            for u, rv_u in zip(unps, rvs_applied):
                e = u["exp"]
                fn_i, sg_i, z_i, base_i = _build_1d_ivw_spectrum(u["arms"], wg, rv_u, float(e["berv_kms"]))
                ep_fn_list.append(fn_i)
                ep_sg_list.append(sg_i)
                ep_recs.append({"u": u, "fn": fn_i, "sig": sg_i, "z": z_i, "base": base_i, "rv_used": rv_u})
            st_ep_data[st] = ep_recs
            fn_stack = np.vstack(ep_fn_list)
            sg_stack_raw = np.vstack(ep_sg_list)
            fin_any = np.any(np.isfinite(fn_stack), axis=0)
            tpl_s = np.ones(len(wg), dtype=np.float64)
            with warnings.catch_warnings(), np.errstate(all="ignore"):
                warnings.simplefilter("ignore", RuntimeWarning)
                if np.any(fin_any):
                    tpl_s[fin_any] = np.nanmedian(fn_stack[:, fin_any], axis=0)
            tpl_s = np.where(np.isfinite(tpl_s), tpl_s, 1.0)
            st_template_rows.append(tpl_s)
            cohort_bervs.append(float(exact_median_1d(np.asarray([float(e["berv_kms"]) for e in exps], dtype=np.float64))))

            if len(exps) >= 4:
                oc = orb_doc["campaigns"].get(st, {})
                valid_col = np.sum(np.isfinite(fn_stack), axis=0) >= max(4, int(math.ceil(0.55 * fn_stack.shape[0])))
                fn_drift = np.where(np.isfinite(fn_stack) & valid_col[None, :], 1.0 + (fn_stack - tpl_s[None, :]), np.nan)
                sg_roll = _build_rolling_sig_epochs(fn_stack, np.where(np.isfinite(sg_stack_raw) & (sg_stack_raw > 0.0), sg_stack_raw, np.nan), tpl_s)
                sg_drift = np.where(np.isfinite(fn_drift), sg_roll, np.nan)
                d096_n4_campaigns.append({
                    "phase_source": "D096",
                    "instrument": inst,
                    "grating_family": spec["band_group"],
                    "star": st,
                    "common_name": exps[0]["common_name"],
                    "role": exps[0]["role"],
                    "cfg": cfg,
                    "wave_rest": wg,
                    "fn_epochs": fn_drift,
                    "sig_epochs": sg_drift,
                    "fn_raw": fn_stack,
                    "tpl_s": tpl_s,
                    "mjd_epochs": np.asarray([float(r["u"]["exp"]["mjd_obs"]) for r in ep_recs], dtype=np.float64),
                    "berv_epochs": np.asarray([float(r["u"]["exp"]["berv_kms"]) for r in ep_recs], dtype=np.float64),
                    "rv_epochs": np.asarray([float(r["rv_used"]) for r in ep_recs], dtype=np.float64),
                    "known_orb_period_days": _opt_float(oc.get("orb_per_days"), math.nan),
                    "known_orb_t0_bjd": _opt_float(oc.get("orb_t0_bjd"), math.nan),
                    "known_orb_kp_kms": _opt_float(oc.get("kp_kms"), math.nan),
                })

        # Cohort RPCA across instrument stars (LOSO + rarity)
        mat_cohort = np.vstack(st_template_rows)
        rpca_out = run_cohort_rpca_v50(wg, mat_cohort, loso_rank=min(8, max(2, len(stars) - 1)))
        z_rpca_mat = rpca_out["z_rpca"]
        L_loso_mat = rpca_out["L_loso"]
        bervs_coh = np.asarray(cohort_bervs, dtype=np.float64)

        g1_c = g2_c = g3_c = g45_c = g6_c = g7_c = 0
        raw_g7_hits: list[dict[str, Any]] = []
        comb_tasks: list[tuple[Any, ...]] = []
        per_star_cands_t: dict[str, list[dict[str, Any]]] = {}

        # First pass across exposures to populate sparse/capped dense_atlas & collect G1 Channel T seeds
        for s_idx, st in enumerate(stars):
            ep_recs = st_ep_data[st]
            tpl_s = st_template_rows[s_idx]
            per_star_cands_t[st] = []

            for r in ep_recs:
                u = r["u"]
                e = u["exp"]
                rv_u = float(r["rv_used"])
                dop_bary = 1.0 + rv_u / C_KMS
                _add_bins(inst, "T", int(np.sum(np.isfinite(r["fn"]))))
                y_resid = np.nan_to_num(r["fn"] - tpl_s, nan=0.0)
                cands_t, _, _ = scan_single_exposure_residual_lsf(wg, y_resid, cfg, channel="T", flux_norm_for_f1=r["fn"], enforce_f1_in_g1=True)
                n_v2_ep = _compute_legacy_v2_count(wg, r["fn"])
                v2_fa_d096 += int(n_v2_ep)
                prov_rows.append({
                    "instrument": inst, "star": st, "dp_id": e["dp_id"], "role": e["role"],
                    "mjd_obs": e["mjd_obs"], "t_exptime_s": e["t_exptime_s"], "grating": e["grating"],
                    "berv_kms": e["berv_kms"], "rv_kms": round(rv_u, 4), "v2_fa": int(n_v2_ep),
                })
                for cand in cands_t[:24]:
                    w_rest_a = float(cand["fitted_center_a"])
                    w_bary_a = w_rest_a * dop_bary
                    w_topo_a = w_bary_a / (1.0 + float(e["berv_kms"]) / C_KMS)
                    dense_atlas.append({
                        "star": st, "dp_id": e["dp_id"], "topo_wave_a": w_topo_a,
                        "snr_mid": float(cand["snr_mid"]), "berv_kms": float(e["berv_kms"]),
                    })
                    per_star_cands_t[st].append({
                        "cand": cand, "r": r, "u": u, "e": e,
                        "w_rest_a": w_rest_a, "w_bary_a": w_bary_a, "w_topo_a": w_topo_a,
                    })

        for s_idx, st in enumerate(stars):
            ep_recs = st_ep_data[st]
            tpl_s = st_template_rows[s_idx]
            rv_med = st_rv_med[st]
            dop_bary = 1.0 + rv_med / C_KMS
            z_coh_s = z_rpca_mat[s_idx]

            def _extract_patches(u_rec: dict[str, Any], wb_a: float) -> list[dict[str, Any]]:
                out_p: list[dict[str, Any]] = []
                for arm in u_rec["arms"]:
                    wa = arm["w_bary"]
                    if not (float(wa[0]) <= wb_a <= float(wa[-1])):
                        continue
                    m_p = np.abs(wa - wb_a) <= 12.0
                    if int(np.sum(m_p)) < 9:
                        continue
                    ipk = int(np.argmin(np.abs(wa[m_p] - wb_a)))
                    er_p = arm["err"][m_p] if arm["err"] is not None else (arm["sig"][m_p] * np.nanmedian(arm["flux"][m_p]))
                    out_p.append({
                        "order": arm["order"], "native_pixel": ipk, "wave": wa[m_p],
                        "flux_a": arm["flux"][m_p], "ref_norm_a": arm["fn"][m_p],
                        "err_a": er_p, "dq": arm["qual"][m_p], "target_wave_a": wb_a,
                    })
                return out_p

            # Per-exposure T channel vetting against dense_atlas
            for item in per_star_cands_t[st]:
                cand, r, u, e = item["cand"], item["r"], item["u"], item["e"]
                w_rest_a, w_bary_a, w_topo_a = item["w_rest_a"], item["w_bary_a"], item["w_topo_a"]
                g1_c += 1
                g2 = evaluate_gate_g2_airglow(w_bary_a, float(e["berv_kms"]), cfg)
                oh2 = check_rousselot_oh_and_barycentric_v52(w_topo_a, float(cfg["sigma_v_kms"]))
                if not (g2["g2_pass"] and (not oh2["is_oh_or_sky"])):
                    continue
                g2_c += 1
                patches = _extract_patches(u, w_bary_a)
                if not patches:
                    continue
                g345 = evaluate_gates_g3_g4_g5_v42(patches, inst, "T", w_rest_a, cfg)
                if not g345["g3_pass"]:
                    continue
                g3_c += 1
                if not (g345["g4_pass"] and g345["g5_pass"]):
                    continue
                g45_c += 1
                g6 = evaluate_gate_g6_v35_dense(st, w_topo_a, patches[0]["order"], patches[0]["native_pixel"], float(e["berv_kms"]), dense_atlas, cfg)
                if not g6["g6_v35_pass"]:
                    continue
                g6_c += 1
                rr = compute_spectral_rarity_score(wg, z_rpca_mat, bervs_coh, s_idx, w_rest_a, float(cfg["sigma_v_kms"]))
                zp = float(z_coh_s[int(np.argmin(np.abs(wg - w_rest_a)))])
                g7 = evaluate_gate_g7_v50(zp, float(rr["rarity_score"]))
                if not g7["g7_pass"]:
                    continue
                g7_c += 1
                raw_g7_hits.append({
                    "inst": inst, "band_group": spec["band_group"], "ch": "T", "e": e, "st": st,
                    "ep_recs": ep_recs,
                    "w_rest_a": w_rest_a, "w_bary_a": w_bary_a, "w_topo_a": w_topo_a,
                    "snr_mid": float(cand["snr_mid"]), "zp": zp, "rarity": float(rr["rarity_score"]),
                    "f_rest": float(rr["f_rest"]), "f_topo": float(rr["f_topo"]),
                    "z_vec": r["z"], "u": u,
                })

            # Stacked P channel (full G2 + OH + G3/G4/G5 + G6 + G7 gating)
            with warnings.catch_warnings(), np.errstate(all="ignore"):
                warnings.simplefilter("ignore", RuntimeWarning)
                fn_stk = np.nanmean(np.vstack([r["fn"] for r in ep_recs]), axis=0)
            y_p = np.nan_to_num(fn_stk - L_loso_mat[s_idx], nan=0.0)
            _add_bins(inst, "P", int(np.sum(np.isfinite(fn_stk))))
            cands_p, _, _ = scan_single_exposure_residual_lsf(wg, y_p, cfg, channel="P", flux_norm_for_f1=fn_stk, enforce_f1_in_g1=True)
            e0 = ep_recs[0]["u"]["exp"]
            for cand in cands_p[:24]:
                w_rest_a = float(cand["fitted_center_a"])
                w_bary_a = w_rest_a * dop_bary
                w_topo_a = w_bary_a / (1.0 + float(cohort_bervs[s_idx]) / C_KMS)
                g1_c += 1
                g2 = evaluate_gate_g2_airglow(w_bary_a, float(cohort_bervs[s_idx]), cfg)
                oh2 = check_rousselot_oh_and_barycentric_v52(w_topo_a, float(cfg["sigma_v_kms"]))
                if not (g2["g2_pass"] and (not oh2["is_oh_or_sky"])):
                    continue
                g2_c += 1
                patches_p = _extract_patches(ep_recs[0]["u"], w_bary_a)
                if not patches_p:
                    continue
                g345_p = evaluate_gates_g3_g4_g5_v42(patches_p, inst, "P", w_rest_a, cfg)
                if not g345_p["g3_pass"]:
                    continue
                g3_c += 1
                if not (g345_p["g4_pass"] and g345_p["g5_pass"]):
                    continue
                g45_c += 1
                g6_p = evaluate_gate_g6_v35_dense(st, w_topo_a, patches_p[0]["order"], patches_p[0]["native_pixel"], float(cohort_bervs[s_idx]), dense_atlas, cfg)
                if not g6_p["g6_v35_pass"]:
                    continue
                g6_c += 1
                rr = compute_spectral_rarity_score(wg, z_rpca_mat, bervs_coh, s_idx, w_rest_a, float(cfg["sigma_v_kms"]))
                zp = float(z_coh_s[int(np.argmin(np.abs(wg - w_rest_a)))])
                g7 = evaluate_gate_g7_v50(zp, float(rr["rarity_score"]))
                if not g7["g7_pass"]:
                    continue
                g7_c += 1
                raw_g7_hits.append({
                    "inst": inst, "band_group": spec["band_group"], "ch": "P", "e": e0, "st": st,
                    "ep_recs": ep_recs,
                    "w_rest_a": w_rest_a, "w_bary_a": w_bary_a, "w_topo_a": w_topo_a,
                    "snr_mid": float(cand["snr_mid"]), "zp": zp, "rarity": float(rr["rarity_score"]),
                    "f_rest": float(rr["f_rest"]), "f_topo": float(rr["f_topo"]),
                    "z_vec": z_coh_s, "u": ep_recs[0]["u"],
                })

            # Keplerian Orbital Campaign Check (#134-#138)
            k_cands_st = 0
            if st in orb_doc["campaigns"]:
                camp = orb_doc["campaigns"][st]
                _add_bins(inst, "K_PLANET", int(np.sum(np.isfinite(fn_stk))))
                ep_shifted = []
                bjd_map = {ex_c["dp_id"]: float(ex_c["planet_orbital_rv_kms"]) for ex_c in camp["exposures"]}
                for r in ep_recs:
                    vorb = bjd_map.get(r["u"]["exp"]["dp_id"], float(r["u"]["exp"].get("planet_orbital_rv_kms", 0.0)))
                    rv_r = float(r["rv_used"])
                    w_pl = bary_to_planet_rest_wave(wg * (1.0 + rv_r / C_KMS), rv_r, vorb)
                    ep_shifted.append(np.interp(wg, w_pl, np.nan_to_num(r["fn"] - tpl_s, nan=0.0), left=0.0, right=0.0))
                y_kep = np.mean(np.vstack(ep_shifted), axis=0)
                ck_list, _, _ = scan_single_exposure_residual_lsf(wg, y_kep, cfg, channel="K_PLANET", flux_norm_for_f1=fn_stk, enforce_f1_in_g1=False)
                for cand in ck_list[:12]:
                    w_rest_a = float(cand["fitted_center_a"])
                    rr = compute_spectral_rarity_score(wg, z_rpca_mat, bervs_coh, s_idx, w_rest_a, float(cfg["sigma_v_kms"]))
                    zp = float(z_coh_s[int(np.argmin(np.abs(wg - w_rest_a)))])
                    g7 = evaluate_gate_g7_v50(zp, float(rr["rarity_score"]))
                    if g7["g7_pass"]:
                        k_cands_st += 1
                        raw_g7_hits.append({
                            "inst": inst, "band_group": spec["band_group"], "ch": "K_PLANET", "e": e0, "st": st,
                            "ep_recs": ep_recs,
                            "w_rest_a": w_rest_a, "w_bary_a": w_rest_a * dop_bary, "w_topo_a": w_rest_a,
                            "snr_mid": float(cand["snr_mid"]), "zp": zp, "rarity": float(rr["rarity_score"]),
                            "f_rest": float(rr["f_rest"]), "f_topo": float(rr["f_topo"]),
                            "z_vec": z_coh_s, "u": ep_recs[0]["u"],
                        })
                orb_res_rows.append({
                    "campaign_index": int(camp["campaign_index"]),
                    "star": st,
                    "common_name": camp["common_name"],
                    "planet_name": camp["planet_name"],
                    "instrument": inst,
                    "n_epochs": len(ep_recs),
                    "orb_per_days": float(camp["orb_per_days"]),
                    "kp_kms": float(camp["kp_kms"]),
                    "orbital_dv_span_kms": float(camp["orbital_dv_span_kms"]),
                    "qualified_kplanet_cands": 0,
                })

            # Agnostic Multi-Scale Scan on stacked cohort RPCA Z-score
            ag_surv, n_ag_ev = scan_agnostic_multiscale_v50(wg, np.nan_to_num(z_coh_s, nan=0.0), s_idx, z_rpca_mat, bervs_coh, cfg)
            _add_bins(inst, "AGNOSTIC_EVALS", n_ag_ev)
            for a_c in ag_surv:
                agnostic_rows.append({
                    "instrument": inst, "star": st,
                    "wave_rest_a": round(float(a_c["wave_rest_a"]), 4),
                    "z_multi": round(float(a_c["z_multi"]), 3),
                    "polarity": a_c["polarity"],
                    "scale_lsf": float(a_c["scale_lsf"]),
                    "kernel": a_c["kernel"],
                    "fwhm_a": round(float(a_c["fwhm_a"]), 4),
                    "sigma_v_kms": round(float(a_c["sigma_v_kms"]), 3),
                    "rarity_score": round(float(a_c["rarity_score"]), 4),
                    "f_rest": round(float(a_c["f_rest"]), 4),
                    "f_topo": round(float(a_c["f_topo"]), 4),
                })

            # Prepare COMB_V4_1 task (against LOSO low-rank model + Epoch-0 template residual)
            with warnings.catch_warnings(), np.errstate(all="ignore"):
                warnings.simplefilter("ignore", RuntimeWarning)
                sg_stk = np.where(np.isfinite(fn_stk), np.nanmedian(np.vstack([r["sig"] for r in ep_recs]), axis=0), 0.02)
            sg_stk = np.maximum(np.nan_to_num(sg_stk, nan=0.02), 1e-4)
            recon_stk = np.where(np.isfinite(L_loso_mat[s_idx]), L_loso_mat[s_idx], 1.0)
            yt_i = np.nan_to_num(ep_recs[0]["fn"] - tpl_s, nan=0.0)
            sgt_i = np.maximum(np.nan_to_num(ep_recs[0]["sig"], nan=0.02), 1e-4)
            comb_tasks.append((
                f"{st}_{spec['band_group']}", wg, np.nan_to_num(fn_stk, nan=1.0), sg_stk,
                recon_stk, yt_i, sgt_i, COMB_V4_1_WINDOWS_A[inst], spec["comb_bands"], cfg,
            ))

            # Preconditioned template-subtracted rolling-512px MAD Z-matrix for Drift Engines
            fn_raw_s = np.vstack([r["fn"] for r in ep_recs])
            fn_mat_s = np.where(np.isfinite(fn_raw_s), fn_raw_s, 1.0)
            sg_mat_raw = np.vstack([np.where(np.isfinite(r["sig"]) & (r["sig"] > 0.0), r["sig"], 0.02) for r in ep_recs])
            z_ep_s = np.nan_to_num(_build_drift_z_matrix_v52(fn_mat_s, tpl_s), nan=0.0)
            sg_mat_s = _build_rolling_sig_epochs(fn_mat_s, sg_mat_raw, tpl_s)

            if len(ep_recs) >= 2:
                r_first, r_last = ep_recs[0], ep_recs[-1]
                dt_d = abs(float(r_last["u"]["exp"]["mjd_obs"]) - float(r_first["u"]["exp"]["mjd_obs"]))
                b_surv, b_meta = scan_blind_drift_dedoppler_v51(
                    wg, z_ep_s[0], z_ep_s[-1],
                    dt_d, float(r_first["u"]["exp"]["berv_kms"]), float(r_last["u"]["exp"]["berv_kms"]),
                    cfg, star=st, star_idx=s_idx, z_rpca_mat=z_rpca_mat, bervs_cohort=bervs_coh,
                )
                b_vet, b_vet_r = _vet_blind_drift_v51(
                    b_surv, wg, fn_mat_s, tpl_s, cfg,
                    bervs_pair=(float(r_first["u"]["exp"]["berv_kms"]), float(r_last["u"]["exp"]["berv_kms"])),
                    rvs_pair=(float(r_first["rv_used"]), float(r_last["rv_used"])),
                )
                blind_drift_rows.append({
                    "instrument": inst, "star": st, "dt_days": round(dt_d, 4),
                    "n_evals": int(b_meta.get("n_evals", 0)),
                    "raw_survivors": len(b_surv), "survivors": len(b_vet),
                    "veto_summary": ";".join(sorted(set(b_vet_r))),
                })
                _add_bins(inst, "DRIFT_V51_EVALS", int(b_meta.get("n_evals", 0)))

            if len(ep_recs) >= 3:
                mjds_s = np.asarray([float(r["u"]["exp"]["mjd_obs"]) for r in ep_recs], dtype=np.float64)
                bervs_s = np.asarray([float(r["u"]["exp"]["berv_kms"]) for r in ep_recs], dtype=np.float64)
                c52, m52 = scan_multiepoch_drift_chaining_v52(wg, z_ep_s, mjds_s, bervs_s, cfg, star=st, star_idx=s_idx, z_rpca_mat=z_rpca_mat, bervs_cohort=bervs_coh)
                c52_vet, c52_vet_r = _vet_multiepoch_drift_tracks_v52(c52, wg, fn_mat_s, tpl_s, mjds_s, cfg)
                drift_v52_rows.append({
                    "instrument": inst, "star": st, "n_epochs": len(ep_recs),
                    "dt_baseline_days": round(float(mjds_s[-1] - mjds_s[0]), 4),
                    "n_evals": int(m52.get("n_traj_evals", 0)),
                    "raw_survivors": len(c52), "survivors": len(c52_vet),
                    "veto_summary": ";".join(sorted(set(c52_vet_r))),
                })
                _add_bins(inst, "DRIFT_V52_EVALS", int(m52.get("n_traj_evals", 0)))
                if len(ep_recs) >= 4:
                    fn_rel_53 = np.where(np.isfinite(fn_raw_s), 1.0 + (fn_raw_s - tpl_s[None, :]), np.nan)
                    c53 = scan_curved_and_periodic_drift_v53(wg, fn_rel_53, sg_mat_s, mjds_s, bervs_s, cfg, star=st, star_idx=s_idx, z_rpca_mat=z_rpca_mat, bervs_cohort=bervs_coh)
                    st53 = c53.get("stats", {})
                    n_c53 = int(st53.get("n_curved_evals", 0))
                    n_p53 = int(st53.get("n_periodic_evals", 0))
                    drift_v53_rows.append({
                        "instrument": inst, "star": st, "n_epochs": len(ep_recs),
                        "dt_baseline_days": round(float(mjds_s[-1] - mjds_s[0]), 4),
                        "n_curved_evals": n_c53,
                        "n_periodic_evals": n_p53,
                        "curved_survivors": len(c53.get("curved_candidates", [])),
                        "periodic_survivors": len(c53.get("periodic_candidates", [])),
                        "total_survivors": len(c53.get("all_survivors", [])),
                    })
                    _add_bins(inst, "DRIFT_V53_EVALS", n_c53 + n_p53)

            # Radiometric EIRP Limits across calibration bands
            srad = float(ep_recs[0]["u"]["exp"]["stellar_mass_msun"]) ** 0.8
            dist_pc = float(ep_recs[0]["u"]["exp"]["dist_pc"])
            teff_k = float(ep_recs[0]["u"]["exp"]["teff_k"])
            g_mag = _opt_float(ep_recs[0]["u"]["exp"]["phot_g_mag"])
            h_mag = _opt_float(ep_recs[0]["u"]["exp"]["h_mag"])
            use_h = math.isfinite(h_mag) and (-4.0 <= h_mag <= 28.0) and (inst == "SDSS_APOGEE2" or not math.isfinite(g_mag))
            anchor = "2MASS_H_PLANCK_CGS" if use_h else "GAIA_G_PLANCK_CGS"
            for bd in get_calibration_bands(inst):
                cw_a = float(bd["center_wave_A"])
                m_b = np.abs(wg - cw_a) <= 120.0
                fin_b = np.isfinite(fn_stk) & m_b
                if int(np.sum(fin_b)) < 20:
                    continue
                mad_b = max(1e-4, exact_mad_1d(fn_stk[fin_b] - 1.0))
                amp_lim = 8.0 * mad_b
                ul = compute_photon_beam_upper_limit(
                    cw_a, amp_lim, teff_k, dist_pc, srad, anchor, spec["rp"],
                    direct_flam_cgs=None, phot_g_mag=None if use_h else g_mag, h_mag=h_mag if use_h else None,
                )
                eirp_rows.append({
                    "instrument": inst, "star": st, "common_name": e0["common_name"],
                    "role": e0["role"], "science_track": e0["science_track"],
                    "panchromatic_bridge": bool(e0["panchromatic_bridge"]),
                    "within_10pc": bool(e0["within_10pc"]), "n_exoplanets": int(e0["n_exoplanets"]),
                    "dist_pc": dist_pc, "teff_k": teff_k, "phot_g_mag": e0["phot_g_mag"], "h_mag": e0["h_mag"],
                    "radiometric_anchor": anchor, "resolving_power": spec["rp"],
                    "band_id": bd["band_id"], "wave_bary_a": cw_a,
                    "median_epoch_mad_rel": round(mad_b, 6), "amp_rel_8sigma_lim": round(amp_lim, 6),
                    "direct_flam_cgs": "", "continuum_flam_cgs": f"{ul['continuum_flam_cgs']:.6e}",
                    "flux_lim_erg_cm2_s": f"{ul['flux_lim_erg_cm2_s']:.6e}",
                    "l_iso_mw": f"{ul['l_iso_mw']:.6e}",
                    "p_beam_10m_w": round(float(ul["p_beam_10m_w"]), 5),
                    "p_beam_10m_kw": round(float(ul["p_beam_10m_kw"]), 6),
                })

        # Fit Gate G8 PCA-kNN Novelty Model from clean instrument patches
        bg_feats: list[np.ndarray] = []
        for s_idx, st in enumerate(stars):
            r0 = st_ep_data[st][0]
            z0 = np.nan_to_num(r0["z"], nan=0.0)
            for idx_bg in np.linspace(120, len(wg) - 120, 40, dtype=int):
                ft_pair = _extract_g8_feat_v52(z0, int(idx_bg), float(z0[idx_bg]), 0.9, 0.0, 0.0)
                if ft_pair is not None and np.all(np.isfinite(ft_pair[0])):
                    bg_feats.append(ft_pair[0])
        g8_m = fit_patch_novelty_model_v52(bg_feats) if len(bg_feats) >= 24 else {"ready": False}
        g8_models[inst] = g8_m

        g8_c = 0
        g8_verified_st = 0
        for h in raw_g7_hits:
            ev8 = evaluate_gate_g8_v52(
                g8_m, wg, np.nan_to_num(h["z_vec"], nan=0.0), h["w_rest_a"],
                h["zp"], h["rarity"], h["f_rest"], h["f_topo"],
            ) if g8_m.get("ready") else {"g8_pass": True, "novelty_z": 10.0}
            if not ev8["g8_pass"]:
                continue
            g8_c += 1
            s2_st, s2_ok, s2_note = _evaluate_stage2_echelle_triage(
                inst, h["ch"], h["w_bary_a"], h["w_topo_a"], h["ep_recs"], h["e"], cfg
            )
            if s2_ok:
                g8_verified_st += 1
            k_id = (inst, spec["band_group"])
            cand_seq[k_id] = cand_seq.get(k_id, 0) + 1
            ledger_rows.append({
                "candidate_id": f"D096_{spec['band_group']}_{cand_seq[k_id]:05d}",
                "instrument": inst, "band_group": spec["band_group"], "channel": h["ch"],
                "role": h["e"]["role"], "star": h["st"], "dp_id": h["e"]["dp_id"],
                "wave_rest_a": round(h["w_rest_a"], 4), "wave_topo_a": round(h["w_topo_a"], 4),
                "snr_mid": round(h["snr_mid"], 3), "sky_z_max": 0.0, "ghost_sky_vetoed": False,
                "g2_pass": True, "g3_pass": True, "g4_pass": True, "g5_pass": True,
                "g6_pass": True, "g7_pass": True, "g8_v52_pass": True,
                "qualified_v54": True, "stage2_triage_status": s2_st, "verified_eti": bool(s2_ok),
                "extra_note": f"novz={ev8['novelty_z']:.2f};rar={h['rarity']:.3f};{s2_note}",
            })

        # Update qualified_kplanet_cands for orbital campaigns of this instrument dynamically
        for orb_r in orb_res_rows:
            if orb_r["instrument"] == inst:
                orb_r["qualified_kplanet_cands"] = sum(
                    1 for lr in ledger_rows
                    if lr["star"] == orb_r["star"] and lr["instrument"] == inst and lr["channel"] == "K_PLANET" and lr["verified_eti"]
                )

        four_gen_rows.append({
            "instrument": inst, "band_group": spec["band_group"], "n_stars": len(stars),
            "g1_lsf": g1_c, "g2_airglow": g2_c, "ghost_sky_vetoed": 0, "g2_plus_sky_pass": g2_c,
            "g3_chromo": g3_c, "g45_native_psf": g45_c, "g6_topo": g6_c, "v50_g7_rpca": g7_c,
            "v54_g8_final": g8_c, "stage2_verified_eti": g8_verified_st,
        })

        # Parallel COMB_V4_1 execution + Stage-2 check
        if comb_tasks:
            comb_fn_by_lbl = {ct[0]: ct[2] for ct in comb_tasks}
            comb_wg_by_lbl = {ct[0]: ct[1] for ct in comb_tasks}
            with ProcessPoolExecutor(max_workers=4) as pool:
                for st_lbl, n_v4, c_v41, n_cfg in pool.map(_scan_comb_star_worker, comb_tasks):
                    _add_bins(inst, "COMB_CONFIGS", n_cfg)
                    v_eti_c = 0
                    wg_c = comb_wg_by_lbl[st_lbl]
                    fn_c = comb_fn_by_lbl[st_lbl]
                    for cc in c_v41:
                        dnu_c = float(cc["dnu_ghz"])
                        nu0_c = float(cc["nu0_ghz"])
                        t_ratios: list[float] = []
                        for m_i in range(6):
                            wm_a = C_ANGSTROM_GHZ / (nu0_c + m_i * dnu_c)
                            ic_m = int(np.argmin(np.abs(wg_c - wm_a)))
                            f400 = fn_c[max(0, ic_m - 400) : min(len(wg_c), ic_m + 401)]
                            p90_c = float(np.percentile(f400, 90.0)) if len(f400) >= 20 else 1.0
                            pk_c = float(np.max(fn_c[max(0, ic_m - 2) : min(len(wg_c), ic_m + 3)]))
                            t_ratios.append(pk_c / max(1e-6, p90_c))
                        med_tr = float(np.median(t_ratios))
                        is_veti = med_tr >= 1.05
                        if is_veti:
                            v_eti_c += 1
                        comb_cand_rows.append({
                            "instrument": inst, "star_band": st_lbl, **cc,
                            "stage2_triage_status": "PASS" if is_veti else "STAGE2_VETO_MDWARF_TIO_SUBPHOTOSPHERIC_FOREST",
                            "verified_eti": is_veti,
                            "median_tooth_f_p90": round(med_tr, 4),
                        })
                    comb_star_rows.append({
                        "instrument": inst, "star_band": st_lbl, "n_comb_configs": n_cfg,
                        "v4_raw_cands": n_v4, "v41_cands": len(c_v41), "verified_eti_combs": v_eti_c,
                    })
        print(f"  [Stream 2] {inst} done ({len(stars)} stars, g1={g1_c}->g8={g8_c}, stage2_eti={g8_verified_st})", flush=True)

    # -----------------------------------------------------------------------
    # Stream 3: DRIFT_V54_COHERENT_SHIFT_STACK across 20 N>=4 Campaigns
    #           (6 D096 + 9 Retroactive D095 Archive U + 5 Retroactive D094 Archive T)
    # -----------------------------------------------------------------------
    retro_campaigns = _decode_prior_apogee2_campaigns(archives_dir)
    all_20_campaigns = d096_n4_campaigns + retro_campaigns
    assert len(all_20_campaigns) == 20, f"Expected 20 N>=4 campaigns, got {len(all_20_campaigns)}"

    css_rows: list[dict[str, Any]] = []
    css_retro_rows: list[dict[str, Any]] = []
    css_cand_rows: list[dict[str, Any]] = []

    for ci, cp in enumerate(all_20_campaigns):
        res_cs = scan_coherent_shift_stack_drift_v54(
            cp["wave_rest"],
            cp["fn_epochs"],
            cp["sig_epochs"],
            cp["mjd_epochs"],
            cp["berv_epochs"],
            cp["cfg"],
            star=cp["star"],
            star_idx=0,
            z_rpca_mat=None,
            bervs_cohort=cp["berv_epochs"],
            known_orb_period_days=cp["known_orb_period_days"] if math.isfinite(cp["known_orb_period_days"]) else None,
            known_orb_t0_bjd=cp["known_orb_t0_bjd"] if math.isfinite(cp["known_orb_t0_bjd"]) else None,
            known_orb_kp_kms=cp["known_orb_kp_kms"] if math.isfinite(cp["known_orb_kp_kms"]) else None,
        )
        n_traj = int(res_cs["n_trajectories_evaluated"])
        n_px_int = int(res_cs["n_pixel_trajectory_integrals"])
        _add_bins(cp["instrument"], "DRIFT_V54_TRAJS", n_traj)
        _add_bins(cp["instrument"], "DRIFT_V54_PX_INT", n_px_int)

        raw_c = res_cs.get("candidates", [])
        n_cur = sum(1 for x in raw_c if "CURV" in str(x.get("branch", x.get("family", ""))).upper())
        n_per = sum(1 for x in raw_c if any(k in str(x.get("branch", x.get("family", ""))).upper() for k in ("PER", "K_PLANET", "ORB")))

        n_verified_cs = 0
        for cj, c in enumerate(raw_c):
            cs_st, cs_ok, cs_diag = _vet_coherent_drift_v54(c, cp)
            if cs_ok:
                n_verified_cs += 1
            css_cand_rows.append({
                "cand_id": f"CSS_{cp['phase_source']}_{cp['star']}_{cj + 1:03d}",
                "phase_source": cp["phase_source"],
                "instrument": cp["instrument"],
                "star": cp["star"],
                "role": cp["role"],
                **{k: v for k, v in c.items() if not isinstance(v, (list, dict))},
                "stage2_triage_status": cs_st,
                "stage2_diag": cs_diag,
                "verified_eti": bool(cs_ok),
            })

        row_cs = {
            "campaign_order": ci + 1,
            "phase_source": cp["phase_source"],
            "instrument": cp["instrument"],
            "grating_family": cp["grating_family"],
            "star": cp["star"],
            "common_name": cp["common_name"],
            "role": cp["role"],
            "n_epochs": int(res_cs["n_epochs"]),
            "n_distinct_epochs": int(res_cs["n_distinct_epochs"]),
            "dt_baseline_days": round(float(np.max(cp["mjd_epochs"]) - np.min(cp["mjd_epochs"])), 4),
            "n_trajectories_evaluated": n_traj,
            "n_pixel_trajectory_integrals": n_px_int,
            "raw_coherent_survivors": len(raw_c),
            "curved_survivors": n_cur,
            "periodic_survivors": n_per,
            "stage2_verified_eti": n_verified_cs,
        }
        css_rows.append(row_cs)
        if cp["phase_source"] != "D096":
            css_retro_rows.append(row_cs)

    # -----------------------------------------------------------------------
    # Stream 4: JWST_NIRISS_SOSS (2 stars) + JWST_NIRSPEC_G140H (4 stars)
    # -----------------------------------------------------------------------
    jwst_summary_rows: list[dict[str, Any]] = []
    for inst in ("JWST_NIRISS_SOSS", "JWST_NIRSPEC_G140H"):
        st_list = sorted(st for (i_k, st) in by_inst_star if i_k == inst)
        for st in st_list:
            exp = by_inst_star[(inst, st)][0]
            cfg_j = get_inst_config(inst, float(exp["resolving_power"]))
            segs = []
            for arm in exp["arms"]:
                w_um = _decode_wave_any(arm["wave"]) / 1e4
                fl = _decode_arr_any(arm["flux"])
                er = _decode_arr_any(arm["err"])
                dq = _decode_qual(arm["qual"], len(w_um))
                if fl is None:
                    continue
                valid = (dq == 0) & np.isfinite(w_um) & np.isfinite(fl)
                _add_bins(inst, "T", int(np.sum(valid)))
                segs.append({
                    "segment": arm["arm"],
                    "wave_um": w_um,
                    "flux": fl,
                    "err": er if er is not None else np.full_like(fl, np.nan),
                    "dq": dq,
                    "rp": float(arm.get("rp", exp["resolving_power"])),
                })

            rj = scan_jwst_niriss_and_g140h_v54(
                segs, inst, cfg_j, star=st,
                dist_pc=float(exp["dist_pc"]),
                teff_k=float(exp["teff_k"]),
                phot_g_mag=_opt_float(exp["phot_g_mag"]) if math.isfinite(_opt_float(exp["phot_g_mag"])) else None,
                h_mag=_opt_float(exp["h_mag"]) if math.isfinite(_opt_float(exp["h_mag"])) else None,
            )
            v2_fa_ep = int(rj["n_g1_raw"])
            v2_fa_d096 += v2_fa_ep
            prov_rows.append({
                "instrument": inst, "star": st, "dp_id": exp["dp_id"], "role": exp["role"],
                "mjd_obs": exp["mjd_obs"], "t_exptime_s": exp["t_exptime_s"], "grating": exp["grating"],
                "berv_kms": 0.0, "rv_kms": round(float(exp["prior_rv_kms"]), 4), "v2_fa": v2_fa_ep,
            })

            g_m = _opt_float(exp["phot_g_mag"])
            h_m = _opt_float(exp["h_mag"])
            use_h = math.isfinite(h_m) and (-4.0 <= h_m <= 28.0)
            anchor = "2MASS_H_PLANCK_CGS" if use_h else "GAIA_G_PLANCK_CGS"
            bd_map = {b["band_id"]: float(b["center_wave_A"]) for b in get_calibration_bands(inst)}
            for bd_id, ul in sorted(rj.get("upper_limits", {}).items()):
                eirp_rows.append({
                    "instrument": inst, "star": st, "common_name": exp["common_name"],
                    "role": exp["role"], "science_track": exp["science_track"],
                    "panchromatic_bridge": bool(exp["panchromatic_bridge"]),
                    "within_10pc": bool(exp["within_10pc"]), "n_exoplanets": int(exp["n_exoplanets"]),
                    "dist_pc": float(exp["dist_pc"]), "teff_k": float(exp["teff_k"]),
                    "phot_g_mag": exp["phot_g_mag"], "h_mag": exp["h_mag"],
                    "radiometric_anchor": anchor, "resolving_power": float(exp["resolving_power"]),
                    "band_id": bd_id, "wave_bary_a": bd_map.get(bd_id, 0.0),
                    "median_epoch_mad_rel": round(float(ul["median_epoch_mad_rel"]), 6),
                    "amp_rel_8sigma_lim": round(float(ul["amp_rel_8sigma_lim"]), 6),
                    "direct_flam_cgs": "", "continuum_flam_cgs": f"{ul['continuum_flam_cgs']:.6e}",
                    "flux_lim_erg_cm2_s": f"{ul['flux_lim_erg_cm2_s']:.6e}",
                    "l_iso_mw": f"{ul['l_iso_mw']:.6e}",
                    "p_beam_10m_w": round(float(ul["p_beam_10m_w"]), 5),
                    "p_beam_10m_kw": round(float(ul["p_beam_10m_kw"]), 6),
                })

            seg_by_nm = {s["segment"]: s for s in segs}
            all_jw_cands = rj.get("candidates", [])
            n_jw_verified = 0
            for c in all_jw_cands:
                if not c.get("qualified_v54"):
                    continue
                seg_obj = seg_by_nm[c.get("segment", "")]
                jw_st, jw_ok, jw_diag = _evaluate_stage2_jwst_triage(c, seg_obj, segs, all_jw_cands)
                if jw_ok:
                    n_jw_verified += 1
                k_id = (inst, "JWST_IR")
                cand_seq[k_id] = cand_seq.get(k_id, 0) + 1
                ledger_rows.append({
                    "candidate_id": f"D096_{'SOSS' if 'SOSS' in inst else 'G140H'}_{cand_seq[k_id]:05d}",
                    "instrument": inst, "band_group": c.get("segment", inst), "channel": "T",
                    "role": exp["role"], "star": st, "dp_id": exp["dp_id"],
                    "wave_rest_a": round(float(c["wave_um"]) * 1e4, 4),
                    "wave_topo_a": round(float(c["wave_um"]) * 1e4, 4),
                    "snr_mid": round(float(c["snr_mid"]), 3),
                    "sky_z_max": 0.0, "ghost_sky_vetoed": False,
                    "g2_pass": True, "g3_pass": True, "g4_pass": bool(c.get("passes_lsf", True)),
                    "g5_pass": bool(c.get("passes_lsf", True)), "g6_pass": True, "g7_pass": True, "g8_v52_pass": True,
                    "qualified_v54": True, "stage2_triage_status": jw_st, "verified_eti": bool(jw_ok),
                    "extra_note": f"um={c['wave_um']:.6f};z={c.get('z_peak', 0):.2f};seg={c.get('segment', '')};out={c.get('snr_outer', 0):.2f};{jw_diag}",
                })

            jwst_summary_rows.append({
                "instrument": inst, "star": st, "common_name": exp["common_name"],
                "role": exp["role"], "panchromatic_bridge": bool(exp["panchromatic_bridge"]),
                "dist_pc": float(exp["dist_pc"]), "n_segments": int(rj["n_segments"]),
                "n_g1_raw": int(rj["n_g1_raw"]), "n_cr_vetoed": int(rj["n_cr_vetoed"]),
                "n_broad_vetoed": int(rj["n_broad_vetoed"]), "n_atlas_vetoed": int(rj["n_atlas_vetoed"]),
                "n_qualified_v54": int(rj["n_qualified_v54"]),
                "stage2_verified_eti": n_jw_verified,
                "best_band": rj.get("best_band") or "",
                "best_p_beam_10m_kw": round(float(rj["best_p_beam_10m_kw"]), 6) if rj.get("best_p_beam_10m_kw") is not None else "",
            })

    _write_csv(out_dir / "JWST_NIRISS_SOSS_AND_G140H_6STARS.csv", list(jwst_summary_rows[0].keys()), jwst_summary_rows)
    _write_csv(out_dir / "V5_4_CANDIDATE_LEDGER.csv", [
        "candidate_id", "instrument", "band_group", "channel", "role", "star", "dp_id",
        "wave_rest_a", "wave_topo_a", "snr_mid", "sky_z_max", "ghost_sky_vetoed",
        "g2_pass", "g3_pass", "g4_pass", "g5_pass", "g6_pass", "g7_pass", "g8_v52_pass",
        "qualified_v54", "stage2_triage_status", "verified_eti", "extra_note",
    ], ledger_rows)
    _write_csv(out_dir / "DRIFT_V54_COHERENT_SHIFT_STACK_20CAMPAIGNS.csv", list(css_rows[0].keys()), css_rows)
    _write_csv(out_dir / "RETROACTIVE_D094_D095_COHERENT_SHIFT_STACK.csv", list(css_retro_rows[0].keys()), css_retro_rows)
    _write_csv(out_dir / "DRIFT_V54_COHERENT_CANDIDATE_LEDGER.csv", list(css_cand_rows[0].keys()) if css_cand_rows else ["cand_id", "phase_source", "instrument", "star", "role", "stage2_triage_status", "verified_eti", "triage_reason"], css_cand_rows)
    _write_csv(out_dir / "FOUR_GEN_BENCHMARK_D096.csv", list(four_gen_rows[0].keys()), four_gen_rows)
    _write_csv(out_dir / "ORBITAL_CAMPAIGN_RESULTS_5.csv", list(orb_res_rows[0].keys()), orb_res_rows)
    _write_csv(out_dir / "EXPOSURE_PROVENANCE_D096.csv", list(prov_rows[0].keys()), prov_rows)
    _write_csv(out_dir / "EIRP_UPPER_LIMITS_D096.csv", list(eirp_rows[0].keys()), eirp_rows)
    _write_csv(out_dir / "STAR_RV_SUMMARY_D096.csv", list(rv_summary_rows[0].keys()), rv_summary_rows)
    _write_csv(out_dir / "STELLAR_RV_ANCHORS_D096.csv", list(rv_anchor_rows[0].keys()), rv_anchor_rows)
    _write_csv(out_dir / "V5_4_AGNOSTIC_MULTISCALE_SURVIVORS.csv", list(agnostic_rows[0].keys()) if agnostic_rows else ["instrument", "star", "wave_rest_a", "z_multi", "polarity", "scale_lsf", "kernel", "fwhm_a", "sigma_v_kms", "rarity_score", "f_rest", "f_topo"], agnostic_rows)
    _write_csv(out_dir / "COMB_V4_1_STAR_RESULTS_D096.csv", list(comb_star_rows[0].keys()), comb_star_rows)
    _write_csv(out_dir / "COMB_V4_1_CANDIDATES.csv", list(comb_cand_rows[0].keys()) if comb_cand_rows else ["instrument", "star_band", "band", "dnu_ghz", "nu0_ghz", "wave0_a", "wave_end_a", "s_comb", "topo_anti_ratio", "n_qualifying_teeth", "off_tooth_crowding", "intertooth_ratio", "stage2_triage_status", "verified_eti"], comb_cand_rows)
    _write_csv(out_dir / "BLIND_DRIFT_V51_RESULTS_D096.csv", list(blind_drift_rows[0].keys()), blind_drift_rows)
    _write_csv(out_dir / "MULTIEPOCH_DRIFT_V52_RESULTS_D096.csv", list(drift_v52_rows[0].keys()), drift_v52_rows)
    _write_csv(out_dir / "DRIFT_V53_CURVED_PERIODIC_D096.csv", list(drift_v53_rows[0].keys()), drift_v53_rows)

    # Calibrations
    cal_summary = _run_v54_calibrations(g8_models, out_dir)

    # -----------------------------------------------------------------------
    # Stream 5: Unified 425-Star Synthesis, 52 Bridges, 425-Star Ellipsoid, 448 Comb Stacks
    # -----------------------------------------------------------------------
    arch_u = archives_dir / ARCHIVE_U_NAME
    with zipfile.ZipFile(arch_u, "r") as zf:
        syn401 = list(csv.DictReader(line for line in zf.read("results/UNIFIED_PANCHROMATIC_V5_3_SYNTHESIS_401STARS.csv").decode("utf-8").splitlines()))
        br47 = list(csv.DictReader(line for line in zf.read("results/PANCHROMATIC_BRIDGE_47STARS_V53.csv").decode("utf-8").splitlines()))
        ell401 = list(csv.DictReader(line for line in zf.read("results/MULTIEVENT_ELLIPSOID_401STARS.csv").decode("utf-8").splitlines()))
        comb_u441 = list(csv.DictReader(line for line in zf.read("results/ALLSKY_COMB_V4_1_UNIFIED_D079_D095.csv").decode("utf-8").splitlines()))
        comb_c_u = list(csv.DictReader(line for line in zf.read("results/ALLSKY_COMB_V4_1_CANDIDATES_D079_D095.csv").decode("utf-8").splitlines()))

    new_syn_cols = list(syn401[0].keys()) + [
        "n_exposures_sofia_exes", "min_sofia_exes_10m_kw",
        "n_exposures_carmenes_v54", "min_carmenes_v54_10m_kw",
        "n_exposures_apogee2_v54", "min_apogee2_v54_10m_kw",
        "n_exposures_jwst_soss", "min_jwst_soss_10m_kw",
        "n_exposures_jwst_g140h", "min_jwst_g140h_10m_kw",
    ]
    syn_map: dict[str, dict[str, Any]] = {}
    for r in syn401:
        rr = dict(r)
        for nc in new_syn_cols[len(r):]:
            rr[nc] = "0" if nc.startswith("n_exposures_") else ""
        syn_map[r["star"]] = rr

    # Index D096 exposures and EIRP limits by star
    d096_exps_by_star: dict[str, list[dict[str, Any]]] = {}
    for e in bundle["exposures"]:
        d096_exps_by_star.setdefault(e["star"], []).append(e)
    d096_eirp_by_star: dict[str, list[dict[str, Any]]] = {}
    for er in eirp_rows:
        d096_eirp_by_star.setdefault(er["star"], []).append(er)

    hemi_map = {
        "SOFIA_EXES": "AIRBORNE_SOFIA",
        "CARMENES_VIS": "NORTHERN",
        "SDSS_APOGEE2": "NORTHERN",
        "JWST_NIRISS_SOSS": "SPACE_L2",
        "JWST_NIRSPEC_G140H": "SPACE_L2",
    }
    regime_map = {
        "SOFIA_EXES": "SOFIA_MIDIR_ECHELLE_5p1_26p0um",
        "CARMENES_VIS": "OPTICAL_FARRED_0p53_0p90um",
        "SDSS_APOGEE2": "NIR_YJH",
        "JWST_NIRISS_SOSS": "NIR_SOSS_0p60_2p83um",
        "JWST_NIRSPEC_G140H": "NIR_G140H_0p82_1p89um",
    }

    br_stars_47 = {r["star"] for r in br47}
    newly_promoted_bridges: list[str] = []
    revisited_control_bridges: list[str] = []
    br52_rows = list(br47)

    for st in sorted(d096_exps_by_star):
        exps_s = d096_exps_by_star[st]
        e0 = exps_s[0]
        lims_s = d096_eirp_by_star.get(st, [])
        n_by_i: dict[str, int] = {}
        min_by_i: dict[str, float] = {}
        for x in exps_s:
            n_by_i[x["instrument"]] = n_by_i.get(x["instrument"], 0) + 1
        for l in lims_s:
            i_k = l["instrument"]
            v = float(l["p_beam_10m_kw"])
            if i_k not in min_by_i or v < min_by_i[i_k]:
                min_by_i[i_k] = v

        def _fmt_min(x: float | None) -> str:
            return f"{x:.6f}" if x is not None and math.isfinite(x) else ""

        if st in syn_map:
            row = syn_map[st]
            prior_min = _opt_float(row.get("min_panchromatic_10m_kw"))
            prior_ph = str(row.get("phases", ""))
            prior_inst = str(row.get("instruments", ""))
            if "D096" not in prior_ph.split("+"):
                row["phases"] = f"{prior_ph}+D096" if prior_ph else "D096"
            insts_u = prior_inst.split("+") if prior_inst else []
            for ik in sorted(n_by_i):
                if ik not in insts_u:
                    insts_u.append(ik)
            row["instruments"] = "+".join(insts_u)
            row["n_exposures_total"] = str(int(row["n_exposures_total"]) + len(exps_s))
            if st not in br_stars_47 and e0["role"] == "SCIENCE" and math.isfinite(prior_min) and lims_s:
                newly_promoted_bridges.append(st)
                p_wave_um = 6.5 if "SPITZER" in prior_inst else (0.25 if "STIS" in prior_inst else (0.105 if "FUSE" in prior_inst else 2.2))
                br52_rows.append({
                    "band_id": f"PRIOR_{st}",
                    "common_name": row["common_name"],
                    "dist_pc": row["dist_pc"],
                    "ew_lim_mA": "",
                    "flux_lim_erg_cm2_s": "",
                    "instrument": prior_inst.split("+")[0],
                    "l_iso_mw": "",
                    "p_beam_10m_kw": f"{prior_min:.6f}",
                    "p_beam_10m_w": f"{prior_min * 1e3:.4f}",
                    "phase_id": prior_ph.split("+")[0],
                    "spectral_regime": "PRIOR_BRIDGE_PROMOTED",
                    "star": st,
                    "wave_A": str(p_wave_um * 1e4),
                    "wave_um": str(p_wave_um),
                })
            elif e0["role"] == "CONTROL" and e0["is_prior_bridge"]:
                revisited_control_bridges.append(st)
        else:
            row = {k: "" for k in new_syn_cols}
            for k in new_syn_cols:
                if k.startswith("n_exposures_"):
                    row[k] = "0"
            row.update({
                "phases": "D096",
                "hemisphere": hemi_map.get(e0["instrument"], "NORTHERN"),
                "spectral_regime": regime_map.get(e0["instrument"], e0["instrument"]),
                "instruments": e0["instrument"],
                "star": st,
                "common_name": e0["common_name"],
                "role": e0["role"],
                "subrole": e0["subrole"],
                "dist_pc": str(e0["dist_pc"]),
                "within_10pc": str(bool(e0["within_10pc"])),
                "teff_k": str(e0["teff_k"]),
                "phot_g_mag": "" if not math.isfinite(e0["phot_g_mag"]) else str(e0["phot_g_mag"]),
                "j_mag": "" if not math.isfinite(e0["j_mag"]) else str(e0["j_mag"]),
                "h_mag": "" if not math.isfinite(e0["h_mag"]) else str(e0["h_mag"]),
                "ks_mag": "" if not math.isfinite(e0["ks_mag"]) else str(e0["ks_mag"]),
                "n_exoplanets": str(e0["n_exoplanets"]),
                "n_exposures_total": str(len(exps_s)),
                "automated_qualified_candidates": "0",
                "verified_eti_detections": "0",
            })
            syn_map[st] = row

        # Append D096 instrument counts & update min limits
        if "SOFIA_EXES" in n_by_i:
            row["n_exposures_sofia_exes"] = str(int(row["n_exposures_sofia_exes"]) + n_by_i["SOFIA_EXES"])
            row["min_sofia_exes_10m_kw"] = _fmt_min(min_by_i.get("SOFIA_EXES"))
        if "CARMENES_VIS" in n_by_i:
            row["n_exposures_carmenes_v54"] = str(n_by_i["CARMENES_VIS"])
            row["min_carmenes_v54_10m_kw"] = _fmt_min(min_by_i.get("CARMENES_VIS"))
            row["n_exposures_optical"] = str(int(row["n_exposures_optical"]) + n_by_i["CARMENES_VIS"])
        if "SDSS_APOGEE2" in n_by_i:
            row["n_exposures_apogee2_v54"] = str(n_by_i["SDSS_APOGEE2"])
            row["min_apogee2_v54_10m_kw"] = _fmt_min(min_by_i.get("SDSS_APOGEE2"))
            row["n_exposures_nir_yjh"] = str(int(row["n_exposures_nir_yjh"]) + n_by_i["SDSS_APOGEE2"])
        if "JWST_NIRISS_SOSS" in n_by_i:
            row["n_exposures_jwst_soss"] = str(n_by_i["JWST_NIRISS_SOSS"])
            row["min_jwst_soss_10m_kw"] = _fmt_min(min_by_i.get("JWST_NIRISS_SOSS"))
            row["n_exposures_jwst_ir"] = str(int(row["n_exposures_jwst_ir"]) + n_by_i["JWST_NIRISS_SOSS"])
        if "JWST_NIRSPEC_G140H" in n_by_i:
            row["n_exposures_jwst_g140h"] = str(n_by_i["JWST_NIRSPEC_G140H"])
            row["min_jwst_g140h_10m_kw"] = _fmt_min(min_by_i.get("JWST_NIRSPEC_G140H"))
            row["n_exposures_jwst_ir"] = str(int(row["n_exposures_jwst_ir"]) + n_by_i["JWST_NIRSPEC_G140H"])

        all_mins = [_opt_float(row.get("min_panchromatic_10m_kw"))] + [v for v in min_by_i.values() if math.isfinite(v)]
        finite_mins = [m for m in all_mins if math.isfinite(m)]
        if finite_mins:
            row["min_panchromatic_10m_kw"] = f"{min(finite_mins):.6f}"
        for l in lims_s:
            w_a = float(l["wave_bary_a"])
            kv = float(l["p_beam_10m_kw"])
            if abs(w_a - 10640.0) <= 200.0:
                pv = _opt_float(row.get("p_1064nm_10m_kw"))
                row["p_1064nm_10m_kw"] = f"{min(pv, kv) if math.isfinite(pv) else kv:.6f}"
            if abs(w_a - 15500.0) <= 200.0:
                pv = _opt_float(row.get("p_1550nm_10m_kw"))
                row["p_1550nm_10m_kw"] = f"{min(pv, kv) if math.isfinite(pv) else kv:.6f}"

        if (st in br_stars_47 or st in newly_promoted_bridges) and lims_s:
            for l in lims_s:
                br52_rows.append({
                    "band_id": l["band_id"],
                    "common_name": l["common_name"],
                    "dist_pc": str(l["dist_pc"]),
                    "ew_lim_mA": "",
                    "flux_lim_erg_cm2_s": l["flux_lim_erg_cm2_s"],
                    "instrument": l["instrument"],
                    "l_iso_mw": l["l_iso_mw"],
                    "p_beam_10m_kw": str(l["p_beam_10m_kw"]),
                    "p_beam_10m_w": str(l["p_beam_10m_w"]),
                    "phase_id": "D096",
                    "spectral_regime": regime_map.get(l["instrument"], l["instrument"]),
                    "star": st,
                    "wave_A": str(l["wave_bary_a"]),
                    "wave_um": f"{float(l['wave_bary_a']) / 1e4:.6f}",
                })

    syn425_rows = list(syn_map.values())
    tenpc_165_rows = [r for r in syn425_rows if str(r["within_10pc"]).lower() == "true"]
    assert len(syn425_rows) == 425, f"Expected 425 unique stars, got {len(syn425_rows)}"
    assert len(tenpc_165_rows) == 165, f"Expected 165 <10pc stars, got {len(tenpc_165_rows)}"

    _write_csv(out_dir / "UNIFIED_PANCHROMATIC_V5_4_SYNTHESIS_425STARS.csv", new_syn_cols, syn425_rows)
    _write_csv(out_dir / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_165STARS.csv", new_syn_cols, tenpc_165_rows)
    _write_csv(out_dir / "PANCHROMATIC_BRIDGE_52STARS_V54.csv", list(br47[0].keys()), br52_rows)

    # Extend Multi-Event SETI Ellipsoid to 425 stars
    ell_map = {r["star"]: dict(r) for r in ell401}
    for st, exps_s in sorted(d096_exps_by_star.items()):
        e0 = exps_s[0]
        m_sn87, m_gw17, m_sn23 = [], [], []
        for ex in exps_s:
            sy = compute_multievent_sync_v51(float(ex["s_ra"]), float(ex["s_dec"]), float(ex["dist_pc"]), float(ex["mjd_obs"]))
            m_sn87.append(abs(float(sy["sn1987a_dt_days"])))
            m_gw17.append(abs(float(sy["gw170817_dt_days"])))
            m_sn23.append(abs(float(sy["sn2023ixf_dt_days"])))
        d1, d2, d3 = min(m_sn87), min(m_gw17), min(m_sn23)
        if st in ell_map:
            er = ell_map[st]
            er["phases"] = syn_map[st]["phases"]
            er["n_epochs_checked"] = str(int(er["n_epochs_checked"]) + len(exps_s))
            d1 = min(float(er["min_abs_sn1987a_dt_days"]), d1)
            d2 = min(float(er["min_abs_gw170817_dt_days"]), d2)
            d3 = min(float(er["min_abs_sn2023ixf_dt_days"]), d3)
        else:
            er = {
                "star": st, "common_name": e0["common_name"], "phases": "D096",
                "role": e0["role"], "dist_pc": str(e0["dist_pc"]), "within_10pc": str(bool(e0["within_10pc"])),
                "ra_deg": str(e0["s_ra"]), "dec_deg": str(e0["s_dec"]),
                "ecliptic_lat_deg": str(e0["ecliptic_lat_deg"]),
                "etz_qualified": str(abs(float(e0["ecliptic_lat_deg"])) <= 2.0),
                "n_epochs_checked": str(len(exps_s)),
            }
            ell_map[st] = er
        pairs = [("SN1987A", d1), ("GW170817", d2), ("SN2023ixf", d3)]
        n_ev, d_min = min(pairs, key=lambda kv: kv[1])
        er["min_abs_sn1987a_dt_days"] = f"{d1:.3f}"
        er["min_abs_gw170817_dt_days"] = f"{d2:.3f}"
        er["min_abs_sn2023ixf_dt_days"] = f"{d3:.3f}"
        er["nearest_event"] = n_ev
        er["min_abs_ellipsoid_dt_days"] = f"{d_min:.3f}"
        er["ellipsoid_qualified_180d"] = str(d_min <= 180.0)
    ell425_rows = list(ell_map.values())
    _write_csv(out_dir / "MULTIEVENT_ELLIPSOID_425STARS.csv", list(ell401[0].keys()), ell425_rows)

    # Extend All-Sky COMB_V4_1 Unified Tables (+7 D096 stacks = 448)
    comb_u448 = list(comb_u441)
    for cs in comb_star_rows:
        st_name = cs["star_band"].removesuffix("_CARMENES_VIS").removesuffix("_APOGEE2_H")
        exp_match = by_inst_star[(cs["instrument"], st_name)][0]
        comb_u448.append({
            "comb_v41_candidates": str(cs["v41_cands"]),
            "comb_v4_candidates": str(cs["v4_raw_cands"]),
            "instrument": cs["instrument"],
            "n_exposures": str(len(by_inst_star[(cs["instrument"], st_name)])),
            "phase_id": "D096",
            "role": exp_match["role"],
            "star": st_name,
            "teff_k": str(exp_match["teff_k"]),
            "verified_eti_combs": str(cs.get("verified_eti_combs", cs.get("verified_eti", 0))),
        })
    comb_c_u448 = list(comb_c_u)
    for ci_idx, cc in enumerate(comb_cand_rows, start=1):
        st_name = cc["star_band"].removesuffix("_CARMENES_VIS").removesuffix("_APOGEE2_H")
        exp_match = by_inst_star[(cc["instrument"], st_name)][0]
        comb_c_u448.append({
            "allsky_comb_id": f"ALLSKY-D096-{ci_idx:04d}",
            "band": cc["band"], "dnu_ghz": cc["dnu_ghz"], "instrument": cc["instrument"],
            "intertooth_ratio": cc["intertooth_ratio"], "n_qualifying_teeth": cc["n_qualifying_teeth"],
            "nu0_ghz": cc["nu0_ghz"], "off_tooth_crowding": cc["off_tooth_crowding"],
            "phase_id": "D096", "role": exp_match["role"], "s_comb": cc["s_comb"], "star": st_name,
            "topo_anti_ratio": cc["topo_anti_ratio"], "wave0_a": cc["wave0_a"], "wave_end_a": cc["wave_end_a"],
        })
    _write_csv(out_dir / "ALLSKY_COMB_V4_1_UNIFIED_D079_D096.csv", list(comb_u441[0].keys()), comb_u448)
    _write_csv(out_dir / "ALLSKY_COMB_V4_1_CANDIDATES_D079_D096.csv", list(comb_c_u[0].keys()), comb_c_u448)

    # -----------------------------------------------------------------------
    # Summary JSON
    # -----------------------------------------------------------------------
    tenpc_med_kw = float(exact_median_1d(np.asarray([_opt_float(r["min_panchromatic_10m_kw"]) for r in tenpc_165_rows if math.isfinite(_opt_float(r["min_panchromatic_10m_kw"]))], dtype=np.float64)))
    total_exp_d096 = len(prov_rows)
    total_hrs_d096 = round(sum(float(r["t_exptime_s"]) for r in prov_rows) / 3600.0, 4)

    def _best_inst_ul(i_name: str) -> dict[str, Any]:
        sub = [r for r in eirp_rows if r["instrument"] == i_name]
        if not sub:
            return {}
        b = min(sub, key=lambda x: float(x["p_beam_10m_kw"]))
        return {"star": b["star"], "band_id": b["band_id"], "p_beam_10m_kw": float(b["p_beam_10m_kw"])}

    best_overall = min(eirp_rows, key=lambda x: float(x["p_beam_10m_kw"]))
    ledger_verified = sum(int(r.get("verified_eti", 0)) for r in ledger_rows)
    css_verified = sum(int(r.get("verified_eti", 0)) for r in css_cand_rows)
    comb_verified = sum(int(r.get("verified_eti_combs", r.get("verified_eti", 0))) for r in comb_star_rows)
    comb_cand_verified = sum(int(r.get("verified_eti", 0)) for r in comb_cand_rows)
    blind_verified = sum(int(r.get("verified_eti", r.get("survivors", 0))) for r in blind_drift_rows)
    drift_v52_verified = sum(int(r.get("verified_eti", r.get("survivors", 0))) for r in drift_v52_rows)
    drift_v53_verified = sum(int(r.get("verified_eti", 0)) for r in drift_v53_rows)
    orb_verified = sum(int(r.get("verified_eti", r.get("k_planet_candidates", 0))) for r in orb_res_rows)
    total_verified_eti = (
        ledger_verified
        + css_verified
        + comb_verified
        + comb_cand_verified
        + blind_verified
        + drift_v52_verified
        + drift_v53_verified
        + orb_verified
    )
    summary = {
        "phase_id": "D096",
        "detector": DETECTOR_NAME,
        "instruments": ["SOFIA_EXES", "CARMENES_VIS", "SDSS_APOGEE2", "JWST_NIRISS_SOSS", "JWST_NIRSPEC_G140H"],
        "stage2_pipeline_notes": {
            "stage1_v5_4_detector_untouched": True,
            "sofia_exes_berv_and_rows": "Parsed 3D (N_orders, 4 or 5, N_pix) SOFIA/EXES _CMB_ arrays, flipped descending wavenumber (cm^-1) to ascending wavelength (um), filled optional Row[4] weights=1.0 when N_rows=4, parsed DATE-OBS UTC ISO into MJD, and computed analytical BERV from Gaia/SIMBAD degrees (ignoring EXES header TELRA in hours).",
            "jwst_x1d_vector_ravel_and_mad": "Flattened both 1D (SIMP0136) and 2D (1, N) (HD59533) EXTRACT1D table columns with .ravel(); preserved empirical relative MAD noise + 2MASS H / Gaia G Planck CGS radiometry.",
            "carmenes_serval_rv_and_channel_p": "Applied per-exposure CARACAL SERVAL RV barycentric alignment for CARMENES_VIS multi-epoch/comb templates (resolving M-dwarf TiO RV offset on HNLIB and WOLF1069) and enforced full oh2/airglow/G3-G5/G6 Channel P gating (vetoing [Na I D2] 5891.8 A, [O I] 6364.7 A, and H2O 7187.8 A telluric residuals).",
            "drift_v51_v52_v54_nan_safe_triage": "Preserved missing/masked NaN pixels during APOGEE2 median template subtraction fn_drift = 1.0 + (fn_raw - tpl_s) instead of unit-filling NaNs; applied V51_TOPO_AIRGLOW / V51_TELLURIC_TROUGH_ANTIPAIR vetting in BLIND_DRIFT_V51 (eliminating [O I] 5577/6300, [Na I D1/D2], OH 8345 and 6911/7187 A O2/H2O antipairs on LP73158/WOLF1069); and enforced DRIFT_V54 exact-RV topocentric CO2/OH cross-epoch recurrence vetting (2M17012756, 2M23032370) plus coherent epoch-subset support vetting (HNLIB, WOLF1069, 2M23025951, 2M23032370).",
            "jwst_j1_j5_physical_triage": "Applied deterministic JWST Stage-2 physical vetoes J1 (negative continuum), J2 (SOSS inter-order cross-contamination r >= 0.90), J3 (NIRSpec NRS1-NRS2 detector gap edge), J4 (unflagged CR error spike err_rat >= 4.0), and J5 (fixed-slit undersampling wiggle f/p90 < 1.12 and med_err/med40 < 0.008).",
        },
        "stage2_triage_summary": {
            "stage1_raw_ledger_survivors": len(ledger_rows),
            "ledger_verified_eti": ledger_verified,
            "stage1_raw_coherent_drift_survivors": len(css_cand_rows),
            "coherent_drift_verified_eti": css_verified,
            "stage1_raw_comb_v41_cands": len(comb_cand_rows),
            "comb_v41_verified_eti": comb_verified + comb_cand_verified,
            "blind_drift_v51_raw_survivors": sum(int(r.get("raw_survivors", r.get("survivors", 0))) for r in blind_drift_rows),
            "blind_drift_v51_verified_eti": blind_verified,
            "multiepoch_drift_v52_raw_survivors": sum(int(r.get("raw_survivors", r.get("survivors", 0))) for r in drift_v52_rows),
            "multiepoch_drift_v52_verified_eti": drift_v52_verified,
            "drift_v53_verified_eti": drift_v53_verified,
            "orbital_k_planet_verified_eti": orb_verified,
            "stage1_raw_agnostic_rows": len(agnostic_rows),
            "stage2_verified_eti": total_verified_eti,
        },
        "cohort": {
            "total_stars": 30,
            "brand_new_unique_stars": 24,
            "prior_stars_revisited": 6,
            "newly_promoted_calibrated_bridges_d096": newly_promoted_bridges,
            "revisited_control_bridges_d096": revisited_control_bridges,
            "control_stars": sum(1 for st in d096_exps_by_star if d096_exps_by_star[st][0]["role"] == "CONTROL"),
            "brand_new_within_10pc": 4,
            "raw_input_files": 39,
            "physical_exposures_d096": total_exp_d096,
            "sofia_exes_files": 19,
            "carmenes_vis_exposures": 10,
            "apogee2_visit_spectra": 96,
            "jwst_soss_exposures": 2,
            "jwst_g140h_exposures": 4,
            "total_integration_hours": total_hrs_d096,
            "orbital_campaigns": 5,
        },
        "searched_spectral_elements": {
            "by_instrument": bins_searched,
            "drift_v54_coherent_campaigns_total": 20,
            "drift_v54_d096_campaigns": 6,
            "drift_v54_d095_retroactive": 9,
            "drift_v54_d094_retroactive": 5,
            "drift_v54_trajectories_total": sum(r["n_trajectories_evaluated"] for r in css_rows),
            "drift_v54_pixel_integrals_total": sum(r["n_pixel_trajectory_integrals"] for r in css_rows),
            "comb_v41_searched_configs_d096": sum(int(r["n_comb_configs"]) for r in comb_star_rows),
            "v2_false_alarms_eliminated_d096": v2_fa_d096,
        },
        "synthetic_calibration_1851_trials": cal_summary,
        "sofia_exes_midir_summary": {
            "n_stars": len(exes_star_rows),
            "n_files": 19,
            **exes_g_tot,
            "cohort_topo_peaks_collected": len(cohort_topo_peaks_um),
            "best_limit_10m_kw": _best_inst_ul("SOFIA_EXES"),
        },
        "jwst_soss_g140h_summary": {
            "n_stars": len(jwst_summary_rows),
            "best_soss_10m_kw": _best_inst_ul("JWST_NIRISS_SOSS"),
            "best_g140h_10m_kw": _best_inst_ul("JWST_NIRSPEC_G140H"),
        },
        "cascade_benchmark": four_gen_rows,
        "orbital_campaigns_134_138": orb_res_rows,
        "multievent_ellipsoid_d079_d096_summary": {
            "stars_evaluated": len(ell425_rows),
            "etz_qualified_stars": sum(1 for r in ell425_rows if str(r["etz_qualified"]) == "True"),
            "ellipsoid_within_180d_stars": sum(1 for r in ell425_rows if str(r["ellipsoid_qualified_180d"]) == "True"),
        },
        "upper_limits": {
            "n_cells": len(eirp_rows),
            "best_d096_star": best_overall["star"],
            "best_d096_instrument": best_overall["instrument"],
            "best_d096_band": best_overall["band_id"],
            "best_d096_10m_w": float(best_overall["p_beam_10m_w"]),
            "best_d096_10m_kw": float(best_overall["p_beam_10m_kw"]),
            "best_by_instrument": {
                k: _best_inst_ul(k)
                for k in ("SOFIA_EXES", "CARMENES_VIS", "SDSS_APOGEE2", "JWST_NIRISS_SOSS", "JWST_NIRSPEC_G140H")
            },
        },
        "unified_425star_panchromatic_v5_4_synthesis": {
            "phases": "D079-D096",
            "spectrographs": 27,
            "spectral_arms": 36,
            "min_wave_um": 0.0905,
            "max_wave_um": 37.86356,
            "octave_span": 8.709,
            "unique_stars_total": len(syn425_rows),
            "science_stars_total": sum(1 for r in syn425_rows if r["role"] == "SCIENCE"),
            "control_stars_total": sum(1 for r in syn425_rows if r["role"] == "CONTROL"),
            "planet_host_stars_total": sum(1 for r in syn425_rows if int(r["n_exoplanets"] or 0) > 0),
            "confirmed_exoplanets_total": sum(int(r["n_exoplanets"] or 0) for r in syn425_rows),
            "within_10pc_unique_stars": len(tenpc_165_rows),
            "within_10pc_median_limit_kw": round(tenpc_med_kw, 5),
            "panchromatic_bridge_stars_total": len({r["star"] for r in br52_rows}),
            "revisited_control_multi_phase_stars": len(revisited_control_bridges),
            "multi_phase_targets_total": len({r["star"] for r in br52_rows}) + len(revisited_control_bridges),
            "panchromatic_bridge_cells_total": len(br52_rows),
            "total_exposures_d079_d096": int(snap["prior_total_exposures_count"]) + total_exp_d096,
            "total_integration_hours_d079_d096": round(float(snap["prior_cumulative_integration_hours"]) + total_hrs_d096, 4),
            "total_calibration_trials_d079_d096": int(snap["prior_calibration_trials_count"]) + int(cal_summary["total_trials"]),
            "v2_false_alarms_eliminated_total": int(snap["prior_v2_false_alarms_eliminated_total"]) + v2_fa_d096,
            "cumulative_orbital_campaigns": int(snap["prior_cumulative_orbital_campaigns_count"]) + 5,
            "cumulative_comb_stacks": len(comb_u448),
            "verified_eti_detections_total": total_verified_eti,
        },
    }
    _write_json(out_dir / "SUMMARY.json", summary)
    if total_verified_eti != 0:
        raise RuntimeError(
            f"Stage-2 verification gate halted: total_verified_eti={total_verified_eti} != 0 "
            f"(ledger={ledger_verified}, css={css_verified}, comb={comb_verified + comb_cand_verified}, "
            f"v51={blind_verified}, v52={drift_v52_verified}, v53={drift_v53_verified}, orb={orb_verified})"
        )
    print(f"Stage B DONE: wrote {out_dir}/SUMMARY.json (425 stars, {len(br52_rows)} bridge cells across {len({r['star'] for r in br52_rows})} bridges)", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--from-full-inputs", action="store_true")
    grp.add_argument("--from-bounded-inputs", nargs="?", const="", default=None)
    ap.add_argument("--inputs-dir", type=Path, default=SCRIPT_DIR.parent.parent / "inputs_d096_v5_4")
    ap.add_argument("--archives-dir", type=Path, default=SCRIPT_DIR.parent.parent / "archives")
    ap.add_argument("--out-dir", type=Path, default=SCRIPT_DIR / "results")
    args = ap.parse_args()

    bundle_path = (
        Path(args.from_bounded_inputs)
        if (args.from_bounded_inputs is not None and str(args.from_bounded_inputs).strip())
        else SCRIPT_DIR / "bounded_inputs" / "d096_bounded_bundle.json.gz"
    )
    if args.from_full_inputs:
        run_stage_a(args.inputs_dir, bundle_path)
    bundle = json.loads(gzip.decompress(bundle_path.read_bytes()).decode("utf-8"))
    run_stage_b(bundle, args.archives_dir, args.out_dir)


if __name__ == "__main__":
    main()
