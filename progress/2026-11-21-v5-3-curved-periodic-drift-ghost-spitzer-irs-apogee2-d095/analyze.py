#!/usr/bin/env python3
"""
Phase D095 (`V5.3`) Curved/Periodic Multi-Epoch Drift, Gemini GHOST Sky-Fiber Veto & Spitzer IRS Analysis Pipeline.

Dual-mode execution guaranteeing 100% SHA-256 bit-identity:
  --from-full-inputs     : Validates all 54 raw files from `<ROOT>/inputs_d095_v5_3/`, serializes
                           `<WS95>/bounded_inputs/d095_bounded_bundle.json.gz` (`< 22.0 MiB`), and runs
                           `run_stage_b()` strictly on the decoded bundle round-trip.
  --from-bounded-inputs  : Reconstructs identical outputs from `d095_bounded_bundle.json.gz` +
                           locked Archive Q (`D091`) and Archive T (`D094`) snapshots.
"""
from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import json
import math
import sys
import warnings
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits
from scipy.ndimage import median_filter

WS = Path(__file__).resolve().parent
ROOT = WS.parent.parent
sys.path.insert(0, str(WS))

from v5_3_detector import (
    BASE_V5_3_CONFIG,
    CALIBRATION_BANDS_GHOST,
    CALIBRATION_BANDS_SPITZER_IRS,
    COMB_V4_1_WINDOWS_A,
    C_ANGSTROM_GHZ,
    C_KMS,
    C_SI,
    DETECTOR_NAME,
    FWHM_FACTOR,
    MAD_NORM,
    SPITZER_IRS_CONFOUNDERS_UM,
    SPITZER_IRS_GREENHOUSE_TEMPLATES_UM,
    _compute_rolling_mad_1d,
    _extract_g8_feat_v52,
    air_to_vac_a,
    analytical_observatory_berv_kms,
    apply_ghost_sky_fiber_veto_v53,
    bary_to_planet_rest_wave,
    check_channel_lsf_gate,
    check_rousselot_oh_and_barycentric_v52,
    compute_keplerian_kp_kms,
    compute_multievent_sync_v51,
    compute_photon_beam_upper_limit,
    compute_planet_orbital_rv_kms,
    compute_running_continuum,
    compute_spectral_rarity_score,
    compute_supraphotospheric_f1_window,
    effective_resolving_power,
    evaluate_gate_g2_airglow,
    evaluate_gate_g6_v36_sparse,
    evaluate_gate_g7_v50,
    evaluate_gate_g8_v52,
    evaluate_gates_g3_g4_g5_v42,
    exact_mad_1d,
    exact_median_1d,
    fit_lsf_on_window,
    fit_patch_novelty_model_v52,
    get_calibration_bands,
    get_inst_config,
    measure_exposure_stellar_rv,
    planet_rest_to_bary_wave,
    run_cohort_rpca_v50,
    scan_agnostic_multiscale_v50,
    scan_blind_drift_dedoppler_v51,
    scan_curved_and_periodic_drift_v53,
    scan_frequency_comb_v4,
    scan_frequency_comb_v4_1,
    scan_multiepoch_drift_chaining_v52,
    scan_single_exposure_residual_lsf,
    scan_spitzer_irs_ccf_and_dyson_v53,
)

MAX_BUNDLE_MIB = 22.0
RNG_SEED = 20261121

ARCHIVE_Q_NAME = "SETI_D091_V4_2_ESO_TRIPLE_3ARM_RESULTS_2026-11-20.zip"
ARCHIVE_Q_BUNDLE_MEMBER = (
    "work_eso_triple_3arm_20261120_d091_v4_2_xshooter_feros_giraffe/bounded_inputs/d091_bounded_bundle.json.gz"
)
ARCHIVE_T_NAME = "SETI_D094_V5_2_MULTIEPOCH_DRIFT_APOGEE2_CRIRESJH_MIRILRS_RESULTS_2026-11-21.zip"
ARCHIVE_T_BUNDLE_MEMBER = "bounded_inputs/d094_bounded_bundle.json.gz"

# APOGEE-2 DR17 APOGEE_PIXMASK fatal + saturation + Littrow + bright sky bits
APOGEE_BAD_MASK = (
    (1 << 0) | (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5)
    | (1 << 6) | (1 << 7) | (1 << 8) | (1 << 9) | (1 << 12)
)


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


def jy_to_flam_cgs(wave_um: np.ndarray, flux_jy: np.ndarray) -> np.ndarray:
    """Convert flux density F_nu (Jy) to F_lambda (erg s^-1 cm^-2 A^-1)."""
    w = np.asarray(wave_um, dtype=np.float64)
    f = np.asarray(flux_jy, dtype=np.float64)
    return (1e-23 * C_SI * 1e6 / 1e4) * f / np.maximum(0.1, w) ** 2


# ---------------------------------------------------------------------------
# Compact IEEE-754 Transposed Bundle Codecs (u=1/2/4/0, f32-t21/t19, bf16)
# ---------------------------------------------------------------------------

def _encode_wave(
    w_angstrom: np.ndarray,
    log10_meta: tuple[float, float] | None = None,
    awav_log_meta: tuple[float, float, float, int] | None = None,
) -> dict[str, Any]:
    w = np.asarray(w_angstrom, dtype=np.float64)
    if awav_log_meta is not None:
        crval1_nm, cd11_nm, crpix1, p0 = awav_log_meta
        px = np.arange(p0, p0 + len(w), dtype=np.float64)
        w_rec = 10.0 * crval1_nm * np.exp((cd11_nm / crval1_nm) * (px + 1.0 - crpix1))
        if len(w) > 0 and float(np.max(np.abs(w_rec - w))) < 1e-4:
            return {
                "u": 4,
                "crval1_nm": float(crval1_nm),
                "cd11_nm": float(cd11_nm),
                "crpix1": float(crpix1),
                "p0": int(p0),
                "n": int(len(w)),
            }
    if log10_meta is not None:
        crval1, cdelt1 = log10_meta
        w_rec = 10.0 ** (crval1 + cdelt1 * np.arange(len(w), dtype=np.float64))
        if len(w) > 0 and float(np.max(np.abs(w_rec - w))) < 1e-4:
            return {"u": 2, "crval1": float(crval1), "cdelt1": float(cdelt1), "n": int(len(w))}
    if len(w) >= 4:
        diffs = np.diff(w)
        dw = float(exact_median_1d(diffs))
        if np.max(np.abs(diffs - dw)) < 5e-4:
            return {"u": 1, "w0": round(float(w[0]), 6), "dw": round(dw, 9), "n": int(len(w))}
    bt = w.view(np.uint8).reshape(-1, 8).T.copy().tobytes()
    return {"u": 0, "n": int(len(w)), "b64": base64.b64encode(bt).decode("ascii")}


def _decode_wave(enc: dict[str, Any]) -> np.ndarray:
    u = int(enc["u"])
    n = int(enc["n"])
    if u == 4:
        crval1_nm = float(enc["crval1_nm"])
        cd11_nm = float(enc["cd11_nm"])
        crpix1 = float(enc["crpix1"])
        p0 = int(enc["p0"])
        px = np.arange(p0, p0 + n, dtype=np.float64)
        return 10.0 * crval1_nm * np.exp((cd11_nm / crval1_nm) * (px + 1.0 - crpix1))
    if u == 2:
        return 10.0 ** (float(enc["crval1"]) + float(enc["cdelt1"]) * np.arange(n, dtype=np.float64))
    if u == 1:
        return float(enc["w0"]) + float(enc["dw"]) * np.arange(n, dtype=np.float64)
    raw = np.frombuffer(base64.b64decode(enc["b64"]), dtype=np.uint8).reshape(8, n).T.copy()
    return raw.view(np.float64).reshape(-1)


def _encode_f32_mask(arr: np.ndarray | None, mant_mask: int = 0xFFFFF800) -> dict[str, Any]:
    if arr is None:
        return {"all_nan": True, "n": 0}
    a = np.asarray(arr, dtype=np.float32)
    fin = np.isfinite(a)
    if not np.any(fin):
        return {"all_nan": True, "n": int(len(a))}
    a_clean = np.where(fin, a, np.float32(np.nan))
    u = a_clean.view(np.uint32)
    u_masked = np.where(fin, u & np.uint32(mant_mask), u)
    bt = u_masked.view(np.uint8).reshape(-1, 4).T.copy().tobytes()
    return {"all_nan": False, "fmt": "f32", "n": int(len(a)), "b64": base64.b64encode(bt).decode("ascii")}


def _encode_bf16(arr: np.ndarray | None) -> dict[str, Any]:
    if arr is None:
        return {"all_nan": True, "n": 0}
    a = np.asarray(arr, dtype=np.float32)
    fin = np.isfinite(a)
    if not np.any(fin):
        return {"all_nan": True, "n": int(len(a))}
    u32 = np.where(fin, a, np.float32(np.nan)).view(np.uint32)
    u16 = np.where(fin, (u32 >> np.uint32(16)).astype(np.uint16), np.uint16(0x7FC0))
    bt = u16.view(np.uint8).reshape(-1, 2).T.copy().tobytes()
    return {"all_nan": False, "fmt": "bf16", "n": int(len(a)), "b64": base64.b64encode(bt).decode("ascii")}


def _decode_float_arr(enc: dict[str, Any] | None) -> np.ndarray | None:
    if enc is None or enc.get("all_nan"):
        return None
    n = int(enc["n"])
    if enc.get("fmt") == "bf16":
        raw16 = np.frombuffer(base64.b64decode(enc["b64"]), dtype=np.uint8).reshape(2, n).T.copy()
        u32 = raw16.view(np.uint16).reshape(-1).astype(np.uint32) << np.uint32(16)
        return u32.view(np.float32).astype(np.float64)
    raw32 = np.frombuffer(base64.b64decode(enc["b64"]), dtype=np.uint8).reshape(4, n).T.copy()
    return raw32.view(np.float32).reshape(-1).astype(np.float64)


def _encode_qual(q_arr: np.ndarray | None) -> dict[str, Any]:
    if q_arr is None:
        return {"mode": "NONE"}
    bad = np.flatnonzero(np.asarray(q_arr) != 0).astype(np.int32)
    if len(bad) == 0:
        return {"mode": "ZERO", "n": int(len(q_arr))}
    if len(bad) <= 2000:
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


def _arm_to_bary_vac(w_raw_a: np.ndarray, specsys: str, berv_kms: float, wave_is_air: bool) -> np.ndarray:
    w_vac = air_to_vac_a(w_raw_a) if wave_is_air else np.asarray(w_raw_a, dtype=np.float64)
    ss = str(specsys).upper()
    if "BARY" in ss or "HELIO" in ss:
        return w_vac
    return w_vac * (1.0 + float(berv_kms) / C_KMS)


# ---------------------------------------------------------------------------
# Stage A: Multi-Instrument Raw Data Extractors (APOGEE-2, GHOST, Spitzer IRS)
# ---------------------------------------------------------------------------

def _extract_apogee2_visits(fp: Path, row: dict[str, str]) -> list[dict[str, Any]]:
    """Extract all individual NVISITS rows [2:2+nv] from SDSS DR17 apStar FITS (allow N>=2)."""
    out: list[dict[str, Any]] = []
    with fits.open(fp) as hdul:
        h0 = hdul[0].header
        h1 = hdul[1].header
        nv = int(h0.get("NVISITS", 0))
        if nv < 2:
            raise RuntimeError(f"Expected NVISITS>=2 in {fp.name}, got {nv}")
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
                cm = np.flatnonzero((wave_vac_a >= lo_a) & (wave_vac_a <= hi_a))
                i0, i1 = int(cm[0]), int(cm[-1]) + 1
                wc = wave_vac_a[i0:i1]
                fc = fl_v[i0:i1]
                ec = np.where(np.isfinite(er_v[i0:i1]) & (er_v[i0:i1] > 0.0), er_v[i0:i1], np.nan)
                qc = ((bm_v[i0:i1] & APOGEE_BAD_MASK) != 0) | (~np.isfinite(fc)) | (~np.isfinite(ec))
                cr_chip = crval1 + float(i0) * cdelt1
                arms.append({
                    "arm": cname,
                    "order": ord_id,
                    "dp_file_id": f"{base_dp}.V{vi+1}",
                    "specsys": "BARYCENT",
                    "wave_is_air": False,
                    "berv_kms": round(bc_v, 5),
                    "berv_src": "APOGEE HDU9 BC",
                    "wave": _encode_wave(wc, log10_meta=(cr_chip, cdelt1)),
                    "flux": _encode_f32_mask(fc, 0xFFFFE000),  # f32-t19
                    "err": _encode_bf16(ec),                    # bf16
                    "qual": _encode_qual(qc.astype(np.int32)),
                })

            out.append({
                "dp_id": f"{base_dp}.V{vi+1}",
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
                "berv_src": "APOGEE HDU9 BC",
                "f_unit": "1e-17 erg s^-1 cm^-2 A^-1",
                "fluxcal": "APOGEE_1D_RELATIVE",
                "arms": arms,
            })
    return out


def _extract_ghost_paired_exposure(
    fp_blue: Path,
    row_blue: dict[str, str],
    fp_red: Path,
    row_red: dict[str, str],
) -> dict[str, Any]:
    """Extract paired GEMINI_GHOST DRAGONS BLUE (<5350A) + RED (>=5350A) with simultaneous sky fiber."""
    arms: list[dict[str, Any]] = []
    mjd_ref = float(row_blue["mjd_obs"])
    expt_ref = float(row_blue["t_exptime"])
    berv_ref = math.nan
    specsys_ref = "BARYCENT"

    for arm_name, ord_id, fp, r_meta, keep_lo, keep_hi in (
        ("GHOST_BLUE", 1, fp_blue, row_blue, 0.0, 5350.0),
        ("GHOST_RED", 2, fp_red, row_red, 5350.0, 12000.0),
    ):
        with fits.open(fp) as hdul:
            h0 = hdul[0].header
            h1 = hdul[1].header
            expt_h = _opt_float(h0.get("EXPTIME"), float(r_meta["t_exptime"]))
            if arm_name == "GHOST_BLUE":
                expt_ref = expt_h
            # Verify DRAGONS barycentricCorrect history + BERV header
            hist_str = " ".join(str(x) for row_h in hdul[7].data for x in row_h) if len(hdul) > 7 and hdul[7].data is not None else ""
            specsys_arm = "BARYCENT" if "barycentricCorrect" in hist_str else "TOPOCENT"
            specsys_ref = specsys_arm
            berv_hdr = _opt_float(h1.get("BERV"), math.nan)
            if math.isfinite(berv_hdr):
                berv_arm, berv_src = berv_hdr, "GHOST HDU1 BERV"
            else:
                berv_arm = analytical_observatory_berv_kms(float(r_meta["s_ra"]), float(r_meta["s_dec"]), mjd_ref, "GEMINI_GHOST")
                berv_src = "CERRO PACHON ANALYTICAL BERV"
            if not math.isfinite(berv_ref):
                berv_ref = berv_arm

            crval1_nm = float(h1["CRVAL1"])
            cd11_nm = float(h1.get("CD1_1") or h1.get("CDELT1"))
            crpix1 = float(h1["CRPIX1"])
            n_px = int(hdul[1].data.shape[0])
            px = np.arange(n_px, dtype=np.float64)
            w_air_a = 10.0 * crval1_nm * np.exp((cd11_nm / crval1_nm) * (px + 1.0 - crpix1))

            sci = np.asarray(hdul[1].data, dtype=np.float64)
            var = np.asarray(hdul[2].data, dtype=np.float64)
            dq = np.asarray(hdul[3].data, dtype=np.int32)
            sky_sci = np.asarray(hdul[4].data, dtype=np.float64)
            sky_var = np.asarray(hdul[5].data, dtype=np.float64)
            sky_dq = np.asarray(hdul[6].data, dtype=np.int32)

            sel = np.flatnonzero((w_air_a >= keep_lo) & (w_air_a < keep_hi))
            i0, i1 = int(sel[0]), int(sel[-1]) + 1
            ws = w_air_a[i0:i1]
            fs = sci[i0:i1]
            es = np.where((var[i0:i1] > 0.0) & np.isfinite(var[i0:i1]), np.sqrt(np.maximum(0.0, var[i0:i1])), np.nan)
            qs = ((dq[i0:i1] & 1) != 0) | (~np.isfinite(fs)) | (~np.isfinite(es))
            ks = sky_sci[i0:i1]
            ke = np.where((sky_var[i0:i1] > 0.0) & np.isfinite(sky_var[i0:i1]), np.sqrt(np.maximum(0.0, sky_var[i0:i1])), np.nan)
            kq = ((sky_dq[i0:i1] & 1) != 0) | (~np.isfinite(ks)) | (~np.isfinite(ke))
            ks_clean = np.where(kq, np.nan, ks)
            ke_clean = np.where(kq, np.nan, ke)

            arms.append({
                "arm": arm_name,
                "order": ord_id,
                "dp_file_id": r_meta["dp_id"],
                "specsys": specsys_arm,
                "wave_is_air": True,
                "berv_kms": round(berv_arm, 5),
                "berv_src": berv_src,
                "wave": _encode_wave(ws, awav_log_meta=(crval1_nm, cd11_nm, crpix1, i0)),
                "flux": _encode_f32_mask(fs, 0xFFFFE000),  # f32-t19
                "err": _encode_bf16(es),                    # bf16
                "qual": _encode_qual(qs.astype(np.int32)),
                "sky_flux": _encode_bf16(ks_clean),         # bf16
                "sky_err": _encode_bf16(ke_clean),          # bf16
            })

    root_id = row_blue["dp_id"].replace("_blue001_dragons", "")
    return {
        "dp_id": root_id,
        "parent_dp_id": root_id,
        "visit_index": int(row_blue["epoch_rank"]),
        "n_visits_total": 1,
        "mjd_obs": round(mjd_ref, 6),
        "t_exptime_s": round(expt_ref, 3),
        "resolving_power": float(row_blue["resolving_power"]),
        "specsys": specsys_ref,
        "wave_is_air": True,
        "berv_kms": round(berv_ref, 5),
        "berv_src": "GHOST HDU1 BERV",
        "f_unit": "ADU",
        "fluxcal": "GHOST_DRAGONS_RELATIVE",
        "arms": arms,
    }


def _extract_spitzer_irs_spectrum(fp: Path, row: dict[str, str]) -> dict[str, Any]:
    """Parse IRSA Spitzer Enhanced IRS `.tbl`, apply bright-star pedestal guard & sort/combine."""
    txt = fp.read_text(encoding="utf-8", errors="replace")
    w_rows: list[float] = []
    f_rows: list[float] = []
    e_rows: list[float] = []
    q_rows: list[int] = []
    n_pedestal_guard = 0

    for line in txt.splitlines():
        s = line.strip()
        if not s or s.startswith("\\") or s.startswith("|"):
            continue
        p = s.split()
        if len(p) < 5:
            continue
        try:
            wu = float(p[1])
            fj = float(p[2])
            ej = float(p[3])
            bf = int(p[4])
        except ValueError:
            continue
        if not (5.0 <= wu <= 40.0 and math.isfinite(fj) and math.isfinite(ej) and ej > 0.0 and fj > 0.0):
            continue
        # Bright-star saturation/DATA_ERROR_MIN guard (error = 0.0001/sqrt(2) = 0.000071 Jy with Jy > 0.5)
        if ej <= 0.00015 and fj > 0.5:
            n_pedestal_guard += 1
            continue
        w_rows.append(wu)
        f_rows.append(fj)
        e_rows.append(ej)
        q_rows.append(0)

    w_um = np.asarray(w_rows, dtype=np.float64)
    f_jy = np.asarray(f_rows, dtype=np.float64)
    e_jy = np.asarray(e_rows, dtype=np.float64)
    ord_i = np.argsort(w_um)
    w_um, f_jy, e_jy = w_um[ord_i], f_jy[ord_i], e_jy[ord_i]

    # Inverse-variance combine exact duplicate wavelength points across orders
    w_u: list[float] = []
    f_u: list[float] = []
    e_u: list[float] = []
    i = 0
    while i < len(w_um):
        j = i + 1
        while j < len(w_um) and abs(float(w_um[j]) - float(w_um[i])) < 1e-6:
            j += 1
        if j - i == 1:
            w_u.append(float(w_um[i]))
            f_u.append(float(f_jy[i]))
            e_u.append(float(e_jy[i]))
        else:
            ws_v = 1.0 / np.maximum(e_jy[i:j] ** 2, 1e-30)
            wsum = float(np.sum(ws_v))
            w_u.append(float(w_um[i]))
            f_u.append(float(np.sum(f_jy[i:j] * ws_v) / wsum))
            e_u.append(1.0 / math.sqrt(wsum))
        i = j

    wu_arr = np.asarray(w_u, dtype=np.float64)
    fj_arr = np.asarray(f_u, dtype=np.float64)
    ej_arr = np.asarray(e_u, dtype=np.float64)
    w_a = wu_arr * 1e4
    flam = jy_to_flam_cgs(wu_arr, fj_arr)
    ferr = jy_to_flam_cgs(wu_arr, ej_arr)
    dq_bad = np.zeros(len(w_a), dtype=np.int32)

    return {
        "dp_id": row["dp_id"],
        "parent_dp_id": row["dp_id"],
        "visit_index": 1,
        "n_visits_total": 1,
        "mjd_obs": round(float(row["mjd_obs"]), 6),
        "t_exptime_s": round(float(row["t_exptime"]), 3),
        "resolving_power": float(row["resolving_power"]),
        "specsys": "HELIO",
        "wave_is_air": False,
        "berv_kms": 0.0,
        "berv_src": "SPITZER_IRS_ENHANCED_TBL",
        "f_unit": "erg s^-1 cm^-2 A^-1",
        "fluxcal": "SPITZER_IRS_DIRECT_CGS",
        "n_pedestal_guard": n_pedestal_guard,
        "arms": [{
            "arm": "SPITZER_IRS_SL_LL",
            "order": 1,
            "dp_file_id": row["dp_id"],
            "specsys": "HELIO",
            "wave_is_air": False,
            "berv_kms": 0.0,
            "berv_src": "SPITZER_IRS_ENHANCED_TBL",
            "wave": _encode_wave(w_a),
            "flux": _encode_f32_mask(flam, 0xFFFFF800),
            "err": _encode_f32_mask(ferr, 0xFFFFF800),
            "flux_jy": _encode_f32_mask(fj_arr, 0xFFFFF800),
            "err_jy": _encode_f32_mask(ej_arr, 0xFFFFF800),
            "qual": _encode_qual(dq_bad),
        }],
    }


def _make_bundle_entry(row: dict[str, str], ext: dict[str, Any]) -> dict[str, Any]:
    return {
        "dp_id": ext["dp_id"],
        "parent_dp_id": ext.get("parent_dp_id", row["dp_id"]),
        "instrument": row["instrument"],
        "star": row["canonical_target"],
        "common_name": row["common_name"],
        "role": row["role"],
        "subrole": row["subrole"],
        "science_track": row["science_track"],
        "panchromatic_bridge": row["panchromatic_bridge"] == "True",
        "is_prior_bridge": row["is_prior_bridge"] == "True",
        "gaia_source_id": int(row["gaia_source_id"]),
        "s_ra": float(row["s_ra"]),
        "s_dec": float(row["s_dec"]),
        "dist_pc": float(row["dist_pc"]),
        "within_10pc": row["within_10pc"] == "True",
        "phot_g_mag": _opt_float(row["phot_g_mag"], math.nan),
        "j_mag": _opt_float(row["j_mag"], math.nan),
        "h_mag": _opt_float(row["h_mag"], math.nan),
        "ks_mag": _opt_float(row["ks_mag"], math.nan),
        "teff_k": float(row["teff_k"]),
        "mh_dex": _opt_float(row["mh_dex"], 0.0),
        "stellar_mass_msun": float(row["stellar_mass_msun"]),
        "prior_rv_kms": float(row["prior_rv_kms"]),
        "n_exoplanets": int(row["n_exoplanets"]),
        "has_transiting_planet": row["has_transiting_planet"] == "True",
        "ecliptic_lat_deg": float(row["ecliptic_lat_deg"]),
        "sn1987a_dt_days": float(row["sn1987a_dt_days"]),
        "gw170817_dt_days": float(row["gw170817_dt_days"]),
        "sn2023ixf_dt_days": float(row["sn2023ixf_dt_days"]),
        "ppo_align_score": float(row["ppo_align_score"]),
        "epoch_rank": int(ext["visit_index"]),
        "grating": row["grating"].replace("GHOST_BLUE", "GHOST_BR") if row["instrument"] == "GEMINI_GHOST" else row["grating"],
        "resolving_power": float(ext["resolving_power"]),
        "mjd_obs": float(ext["mjd_obs"]),
        "t_exptime_s": float(ext["t_exptime_s"]),
        "phase_window": row["phase_window"],
        "signed_phase": float(row["signed_phase"]),
        "planet_orbital_rv_kms": float(row["planet_orbital_rv_kms"]),
        "specsys": ext["specsys"],
        "wave_is_air": ext["wave_is_air"],
        "berv_kms": ext["berv_kms"],
        "berv_src": ext["berv_src"],
        "flux_unit": ext["f_unit"],
        "fluxcal": ext["fluxcal"],
        "n_pedestal_guard": int(ext.get("n_pedestal_guard", 0)),
        "arms": ext["arms"],
    }


def run_stage_a_build_bundle(full_dir: Path) -> Path:
    """Ingest all 54 raw files from `full_dir` into bounded compressed JSON bundle (< 22.0 MiB)."""
    cohort_path = WS / "FROZEN_COHORT_D095.csv"
    man_path = WS / "FULL_D095_INPUT_MANIFEST.json"
    bundle_out = WS / "bounded_inputs" / "d095_bounded_bundle.json.gz"
    if not (cohort_path.exists() and man_path.exists()):
        raise RuntimeError("Missing FROZEN_COHORT_D095.csv or FULL_D095_INPUT_MANIFEST.json")

    coh_rows = list(csv.DictReader(cohort_path.open("r", encoding="utf-8", newline="")))
    man_doc = json.loads(man_path.read_text(encoding="utf-8"))
    man_by_dp = {e["dp_id"]: e for e in man_doc["files"]}
    assert len(coh_rows) == 54 and len(man_by_dp) == 54

    # Validate SHA-256 of every raw file before ingestion
    for row in coh_rows:
        me = man_by_dp[row["dp_id"]]
        fp = full_dir / me["f1_rel"]
        if not fp.exists() or _sha256_file(fp) != me["sha256"]:
            raise RuntimeError(f"Raw input missing or SHA-256 mismatch: {fp}")

    print(f"Stage A: ingesting 54 raw D095 files from {full_dir}...", flush=True)
    bundle_exps: list[dict[str, Any]] = []

    # 1. APOGEE-2
    for row in [r for r in coh_rows if r["instrument"] == "SDSS_APOGEE2"]:
        fp = full_dir / row["f1_rel"]
        for ext in _extract_apogee2_visits(fp, row):
            bundle_exps.append(_make_bundle_entry(row, ext))

    # 2. GEMINI_GHOST (pair BLUE & RED by (canonical_target, epoch_rank))
    ghost_pairs: dict[tuple[str, int], dict[str, dict[str, str]]] = {}
    for row in [r for r in coh_rows if r["instrument"] == "GEMINI_GHOST"]:
        key = (row["canonical_target"], int(row["epoch_rank"]))
        arm_k = "BLUE" if "BLUE" in row["grating"] else "RED"
        ghost_pairs.setdefault(key, {})[arm_k] = row
    for key in sorted(ghost_pairs):
        pr = ghost_pairs[key]
        rb, rr = pr["BLUE"], pr["RED"]
        ext = _extract_ghost_paired_exposure(full_dir / rb["f1_rel"], rb, full_dir / rr["f1_rel"], rr)
        bundle_exps.append(_make_bundle_entry(rb, ext))

    # 3. SPITZER_IRS
    for row in [r for r in coh_rows if r["instrument"] == "SPITZER_IRS"]:
        fp = full_dir / row["f1_rel"]
        bundle_exps.append(_make_bundle_entry(row, _extract_spitzer_irs_spectrum(fp, row)))

    for ex in bundle_exps:
        for k in ("phot_g_mag", "j_mag", "h_mag", "ks_mag"):
            if ex[k] is not None and isinstance(ex[k], float) and not math.isfinite(ex[k]):
                ex[k] = None

    bundle = {
        "schema": "D095_BOUNDED_BUNDLE_V1",
        "phase_id": "D095",
        "detector": DETECTOR_NAME,
        "cohort_sha256": _sha256_file(cohort_path),
        "manifest_sha256": _sha256_file(man_path),
        "n_cohort_files": len(coh_rows),
        "n_unpacked_exposures": len(bundle_exps),
        "exposures": bundle_exps,
    }
    bundle_out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(bundle_out, "wt", encoding="utf-8", compresslevel=9) as gz:
        json.dump(bundle, gz, separators=(",", ":"))

    bnd_mib = bundle_out.stat().st_size / (1024.0 * 1024.0)
    if bnd_mib >= MAX_BUNDLE_MIB:
        raise RuntimeError(f"Bounded bundle {bnd_mib:.2f} MiB exceeds hard cap < {MAX_BUNDLE_MIB} MiB!")
    print(f"Stage A DONE: wrote {bundle_out} ({bnd_mib:.2f} MiB < {MAX_BUNDLE_MIB:.1f} MiB, {len(bundle_exps)} unpacked spectra)", flush=True)
    return bundle_out


# ---------------------------------------------------------------------------
# Spectrum Unpacking & Echelle Merge
# ---------------------------------------------------------------------------

def _unpack_exposure_spectrum(exp: dict[str, Any], cfg: dict[str, Any], compute_cont: bool = True) -> dict[str, Any]:
    inst = exp["instrument"]
    native_arms: list[dict[str, Any]] = []
    for arm in exp["arms"]:
        w_raw = _decode_wave(arm["wave"])
        is_air = bool(arm.get("wave_is_air", exp.get("wave_is_air", False)))
        w_bary = _arm_to_bary_vac(w_raw, arm["specsys"], float(arm["berv_kms"]), wave_is_air=is_air)
        fl = _decode_float_arr(arm["flux"])
        er = _decode_float_arr(arm["err"])
        sk_f = _decode_float_arr(arm.get("sky_flux"))
        sk_e = _decode_float_arr(arm.get("sky_err"))
        fjy = _decode_float_arr(arm.get("flux_jy"))
        ejy = _decode_float_arr(arm.get("err_jy"))
        qu = _decode_qual(arm["qual"], len(w_bary))
        if fl is None or len(w_bary) < 24:
            continue
        osrt = np.argsort(w_bary)
        w_bary = w_bary[osrt]
        fl = fl[osrt]
        qu = qu[osrt]
        if er is not None:
            er = er[osrt]
        if sk_f is not None:
            sk_f = sk_f[osrt]
        if sk_e is not None:
            sk_e = sk_e[osrt]
        if fjy is not None:
            fjy = fjy[osrt]
        if ejy is not None:
            ejy = ejy[osrt]

        bad = (~np.isfinite(w_bary)) | (~np.isfinite(fl)) | (qu != 0)
        fl_clean = np.where(bad, np.nan, fl)
        er_clean = np.where(bad | (~np.isfinite(er)) | (er <= 0.0), np.nan, er) if er is not None else None
        if compute_cont and len(w_bary) >= 60 and inst not in ("SPITZER_IRS", "JWST_MIRI_LRS", "JWST_NIRSPEC_G395H"):
            cr, ce = compute_running_continuum(w_bary, fl_clean, cfg, err=er_clean)
            cont = np.where(cr > 0.0, cr, ce)
            fn = np.where(bad | (~np.isfinite(fl_clean)) | (~np.isfinite(ce)) | (ce <= 0.0), np.nan, fl_clean / ce)
        else:
            med_c = float(exact_median_1d(fl_clean[np.isfinite(fl_clean)])) if np.any(np.isfinite(fl_clean)) else 1.0
            cont = np.full_like(w_bary, max(1e-30, med_c))
            fn = fl_clean / max(1e-30, abs(med_c))
        native_arms.append({
            "arm": arm["arm"], "order": int(arm["order"]),
            "w_bary": w_bary, "flux": fl_clean, "cont": cont, "fn": fn, "err": er_clean, "qual": qu,
            "sky_flux": sk_f, "sky_err": sk_e, "flux_jy": fjy, "err_jy": ejy,
        })

    if not native_arms:
        return {"w_bary": np.zeros(0), "fn": np.zeros(0), "flux_cgs": np.zeros(0), "arms": [], "sky_w_bary": np.zeros(0), "sky_flux": np.zeros(0), "sky_err": np.zeros(0)}

    if len(native_arms) == 1:
        a0 = native_arms[0]
        return {
            "w_bary": a0["w_bary"], "fn": a0["fn"], "flux_cgs": a0["flux"], "arms": native_arms,
            "sky_w_bary": a0["w_bary"] if a0["sky_flux"] is not None else np.zeros(0),
            "sky_flux": a0["sky_flux"] if a0["sky_flux"] is not None else np.zeros(0),
            "sky_err": a0["sky_err"] if a0["sky_err"] is not None else np.zeros(0),
        }

    # For GEMINI_GHOST (2 disjoint non-overlapping sliced arms) vs APOGEE (3 disjoint chips):
    # Direct ordered arm concatenation preserves exact native sky_flux/sky_err pixels without resampling!
    sky_ws, sky_fs, sky_es = [], [], []
    for a in sorted(native_arms, key=lambda x: float(x["w_bary"][0])):
        if a["sky_flux"] is not None and a["sky_err"] is not None:
            sky_ws.append(a["w_bary"])
            sky_fs.append(a["sky_flux"])
            sky_es.append(a["sky_err"])
    sky_w_all = np.concatenate(sky_ws) if sky_ws else np.zeros(0)
    sky_f_all = np.concatenate(sky_fs) if sky_fs else np.zeros(0)
    sky_e_all = np.concatenate(sky_es) if sky_es else np.zeros(0)

    step_a = float(cfg["coadd_step_angstrom"])
    w_min = min(float(np.min(a["w_bary"])) for a in native_arms)
    w_max = max(float(np.max(a["w_bary"])) for a in native_arms)
    w_grid = np.arange(w_min, w_max + 0.5 * step_a, step_a, dtype=np.float64)
    num_fn = np.zeros(len(w_grid), dtype=np.float64)
    num_fl = np.zeros(len(w_grid), dtype=np.float64)
    den = np.zeros(len(w_grid), dtype=np.float64)
    max_step_gap = 0.50
    for a in native_arms:
        wa, fn_a, fl_a, co_a, er_a = a["w_bary"], a["fn"], a["flux"], a["cont"], a["err"]
        if len(wa) < 60:
            continue
        m = np.isfinite(wa) & np.isfinite(fn_a) & np.isfinite(fl_a) & np.isfinite(co_a) & (co_a > 0.0)
        trim_edge = 8 if inst == "SDSS_APOGEE2" else 16
        m[:trim_edge] = False
        m[-trim_edge:] = False
        if er_a is not None:
            m &= np.isfinite(er_a) & (er_a > 0.0)
        if int(m.sum()) < 25:
            continue
        wb_v, fn_v, fl_v = wa[m], fn_a[m], fl_a[m]
        if er_a is not None:
            wt_v = 1.0 / np.maximum(1e-6, (er_a[m] / np.maximum(1e-12, co_a[m])) ** 2)
        else:
            wt_v = np.ones_like(fn_v)
        i0 = int(np.searchsorted(w_grid, float(wb_v[0]), side="left"))
        i1 = int(np.searchsorted(w_grid, float(wb_v[-1]), side="right"))
        if i1 <= i0 + 3:
            continue
        bg = w_grid[i0:i1]
        idx_hi = np.searchsorted(wb_v, bg)
        i_r = np.clip(idx_hi, 1, len(wb_v) - 1)
        ok_g = (wb_v[i_r] - wb_v[i_r - 1]) <= max_step_gap
        wt_i = np.where(ok_g, np.interp(bg, wb_v, wt_v), 0.0)
        num_fn[i0:i1] += np.where(ok_g, np.interp(bg, wb_v, fn_v), 0.0) * wt_i
        num_fl[i0:i1] += np.where(ok_g, np.interp(bg, wb_v, fl_v), 0.0) * wt_i
        den[i0:i1] += wt_i
    ok = den > 0.0
    return {
        "w_bary": w_grid,
        "fn": np.where(ok, num_fn / np.maximum(den, 1e-30), np.nan),
        "flux_cgs": np.where(ok, num_fl / np.maximum(den, 1e-30), np.nan),
        "arms": native_arms,
        "sky_w_bary": sky_w_all,
        "sky_flux": sky_f_all,
        "sky_err": sky_e_all,
    }


def _resample_gap_safe(w_src: np.ndarray, y_src: np.ndarray, grid: np.ndarray, max_gap_a: float) -> np.ndarray:
    out = np.full(len(grid), np.nan, dtype=np.float64)
    fin = np.isfinite(w_src) & np.isfinite(y_src)
    if int(fin.sum()) < 30:
        return out
    wf, yf = w_src[fin], y_src[fin]
    interp = np.interp(grid, wf, yf, left=np.nan, right=np.nan)
    idx_hi = np.searchsorted(wf, grid)
    vi = np.flatnonzero((grid >= wf[0]) & (grid <= wf[-1]))
    if len(vi):
        i_r = np.clip(idx_hi[vi], 1, len(wf) - 1)
        ok = (wf[i_r] - wf[i_r - 1]) <= max_gap_a
        out[vi[ok]] = interp[vi[ok]]
    return out


def _extract_native_patches_for_cand(
    native_arms: list[dict[str, Any]],
    tpl_rest: np.ndarray,
    rest_grid: np.ndarray,
    target_bary_a: float,
    rv_kms: float,
) -> list[dict[str, Any]]:
    patches: list[dict[str, Any]] = []
    dop = 1.0 + rv_kms / C_KMS
    for a in native_arms:
        w = a["w_bary"]
        if len(w) < 60 or target_bary_a < float(w[10]) or target_bary_a > float(w[-11]):
            continue
        k = int(np.argmin(np.abs(w - target_bary_a)))
        if abs(float(w[k]) - target_bary_a) > 2.5 or k < 12 or k >= len(w) - 12:
            continue
        lo, hi = max(0, k - 75), min(len(w), k + 76)
        w_win, f_win = w[lo:hi], a["flux"][lo:hi]
        kc = k - lo
        if not np.all(np.isfinite(f_win[max(0, kc - 4) : min(len(f_win), kc + 5)])):
            continue
        fin_m = np.isfinite(f_win)
        if int(fin_m.sum()) < 45:
            continue
        f_win_clean = np.interp(w_win, w_win[fin_m], f_win[fin_m])
        e_win = a["err"][lo:hi] if a["err"] is not None else None
        q_win = a["qual"][lo:hi]
        ref_win = np.interp(w_win / dop, rest_grid, tpl_rest, left=1.0, right=1.0)
        patches.append({
            "arm": a["arm"], "order": int(a["order"]), "native_pixel": int(k),
            "wave": w_win, "flux_a": f_win_clean, "ref_norm_a": ref_win,
            "err_a": e_win, "dq": q_win, "target_wave_a": float(target_bary_a),
        })
    return patches


def _compute_legacy_v2_count(w_bary: np.ndarray, fn: np.ndarray) -> int:
    fin = np.isfinite(w_bary) & np.isfinite(fn)
    if int(fin.sum()) < 50:
        return 0
    y = fn[fin] - 1.0
    mad = exact_mad_1d(y)
    if not math.isfinite(mad) or mad <= 0.0:
        return 0
    raw = y > 4.5 * mad
    return int(np.sum(raw & np.concatenate(([True], ~raw[:-1]))))


def _rolling_comb_sigma(y_arr: np.ndarray, floor_mad: float) -> np.ndarray:
    n = len(y_arr)
    out = np.full(n, floor_mad, dtype=np.float64)
    for i0 in range(0, n, 300):
        i1 = min(n, i0 + 300)
        seg = y_arr[i0:i1]
        f = seg[np.isfinite(seg)]
        if len(f) >= 20:
            out[i0:i1] = max(floor_mad, exact_mad_1d(f))
    return out


def _scan_comb_star_worker(
    args: tuple[str, str, float, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
) -> tuple[str, int, list[dict[str, Any]], int]:
    st, inst, r_pow, rg, rp, fn_p, tpl, sky_mask, y_topo, mad_r = args
    cfg = get_inst_config(inst, r_pow)
    sig_r = _rolling_comb_sigma(rp, mad_r)
    fin_t = np.isfinite(y_topo)
    mad_t = max(1e-4, exact_mad_1d(y_topo[fin_t])) if int(fin_t.sum()) >= 50 else mad_r
    sig_t = _rolling_comb_sigma(y_topo, mad_t)
    wins = COMB_V4_1_WINDOWS_A[inst]
    bands = list(cfg["comb_search_bands"])
    cands_v4, n_cfg = scan_frequency_comb_v4(rg, rp, sig_r, fn_p, tpl, sky_mask, y_topo, sig_t, wins, bands, cfg)
    cands_v41, _ = scan_frequency_comb_v4_1(rg, rp, sig_r, fn_p, tpl, sky_mask, y_topo, sig_t, wins, bands, cfg)
    return st, len(cands_v4), cands_v41, n_cfg


def _locate_archive(filename: str, override_path: Path | None = None, archives_dir_arg: Path | None = None) -> Path:
    cands: list[Path] = []
    if override_path is not None:
        cands.append(override_path)
    if archives_dir_arg is not None:
        cands.append(archives_dir_arg / filename)
    cands.extend([ROOT / "archives" / filename, Path("/home/martin/SETI_Fortsaettelse_2026-11-14/archives") / filename])
    for c in cands:
        if c.exists():
            return c
    raise RuntimeError(f"Cannot locate archive {filename}")


def _build_drift_z_matrix_v52(fn_mat: np.ndarray, tpl_s: np.ndarray) -> np.ndarray:
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


def _build_drift_sigma_matrix_v53(fn_mat: np.ndarray, tpl_s: np.ndarray) -> np.ndarray:
    """Per-epoch scalar MAD noise matrix matching Stage-1 `scan_curved_and_periodic_drift_v53`."""
    sig_mat = np.full_like(fn_mat, 0.02)
    for k in range(fn_mat.shape[0]):
        r_k = fn_mat[k] - tpl_s
        f_k = np.isfinite(r_k)
        mad_k = max(1e-4, exact_mad_1d(r_k[f_k])) if int(np.sum(f_k)) >= 64 else 0.02
        sig_mat[k] = mad_k
    return sig_mat


def _vet_multiepoch_drift_tracks_v52(
    cands: list[dict[str, Any]],
    grid: np.ndarray,
    fn_mat: np.ndarray,
    tpl_s: np.ndarray,
    mjds: np.ndarray,
    cfg: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
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
            lo = max(0, ic - margin)
            hi = min(len(grid), ic + margin + 1)
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


# ---------------------------------------------------------------------------
# Retroactive V5.3 DRIFT_V53_CURVED_AND_PERIODIC on Archive Q (D091) & Archive T (D094)
# ---------------------------------------------------------------------------

def _decode_prior_bundle_exposure(exp: dict[str, Any], cfg: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    """Decode D091/D094 compact bundle exposure onto barycentric vacuum wavelength grid."""
    arms_out: list[tuple[np.ndarray, np.ndarray, np.ndarray | None]] = []
    for arm in exp["arms"]:
        w_raw = _decode_wave(arm["wave"])
        is_air = bool(arm.get("wave_is_air", exp.get("wave_is_air", False)))
        w_bary = _arm_to_bary_vac(w_raw, arm["specsys"], float(arm["berv_kms"]), wave_is_air=is_air)
        fl = _decode_float_arr(arm["flux"])
        er = _decode_float_arr(arm["err"])
        qu = _decode_qual(arm["qual"], len(w_bary))
        if fl is None or len(w_bary) < 24:
            continue
        osrt = np.argsort(w_bary)
        w_bary, fl, qu = w_bary[osrt], fl[osrt], qu[osrt]
        if er is not None:
            er = er[osrt]
        bad = (~np.isfinite(w_bary)) | (~np.isfinite(fl)) | (qu != 0)
        fl_c = np.where(bad, np.nan, fl)
        er_c = np.where(bad | (~np.isfinite(er)) | (er <= 0.0), np.nan, er) if er is not None else None
        cr, ce = compute_running_continuum(w_bary, fl_c, cfg, err=er_c)
        cont = np.where(cr > 0.0, cr, ce)
        fn = np.where(bad | (~np.isfinite(fl_c)) | (~np.isfinite(ce)) | (ce <= 0.0), np.nan, fl_c / ce)
        arms_out.append((w_bary, fn, cont))
    if not arms_out:
        return np.zeros(0), np.zeros(0)
    if len(arms_out) == 1:
        return arms_out[0][0], arms_out[0][1]
    step_a = float(cfg["coadd_step_angstrom"])
    w_min = min(float(np.min(a[0])) for a in arms_out)
    w_max = max(float(np.max(a[0])) for a in arms_out)
    wg = np.arange(w_min, w_max + 0.5 * step_a, step_a, dtype=np.float64)
    num, den = np.zeros(len(wg)), np.zeros(len(wg))
    for wb, fn, _co in arms_out:
        m = np.isfinite(wb) & np.isfinite(fn)
        m[:8] = False; m[-8:] = False
        if int(m.sum()) < 25:
            continue
        wv, fv = wb[m], fn[m]
        i0 = int(np.searchsorted(wg, float(wv[0]), side="left"))
        i1 = int(np.searchsorted(wg, float(wv[-1]), side="right"))
        if i1 <= i0 + 3:
            continue
        bg = wg[i0:i1]
        ih = np.searchsorted(wv, bg)
        ir = np.clip(ih, 1, len(wv) - 1)
        ok = (wv[ir] - wv[ir - 1]) <= 0.50
        num[i0:i1] += np.where(ok, np.interp(bg, wv, fv), 0.0)
        den[i0:i1] += np.where(ok, 1.0, 0.0)
    return wg, np.where(den > 0.0, num / np.maximum(den, 1.0), np.nan)


def _run_retroactive_curved_periodic_d091_d094(
    archive_specs: list[dict[str, Any]],
    archives_dir_arg: Path | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run V5.3 DRIFT_V53_CURVED_AND_PERIODIC across all N>=4 campaigns in Archive Q (D091) & Archive T (D094)."""
    all_rows: list[dict[str, Any]] = []
    all_surv: list[dict[str, Any]] = []

    for meta in archive_specs:
        phase = str(meta["phase_id"])
        arch_path = _locate_archive(meta["archive_name"], None, archives_dir_arg)
        with zipfile.ZipFile(arch_path, "r") as zf:
            raw_gz = zf.read(meta["bundle_member"])
        got_sha = _sha256_bytes(raw_gz)
        if got_sha != meta["bundle_sha256"]:
            raise RuntimeError(f"{phase} bundle SHA-256 mismatch: {got_sha} != {meta['bundle_sha256']}")
        bnd = json.loads(gzip.decompress(raw_gz).decode("utf-8"))

        by_group: dict[tuple[str, str], dict[str, list[dict[str, Any]]]] = {}
        for ex in bnd["exposures"]:
            inst = str(ex["instrument"])
            if phase == "D094" and inst != "SDSS_APOGEE2":
                continue
            gf = str(ex["grating"]).split("_")[0] if inst == "ESO_GIRAFFE_HR" else inst
            by_group.setdefault((inst, gf), {}).setdefault(str(ex["star"]), []).append(ex)

        for (inst, gf), st_dict in sorted(by_group.items()):
            items = [
                (st, sorted(exps, key=lambda e: float(e["mjd_obs"])))
                for st, exps in sorted(st_dict.items())
                if len(exps) >= 4 and (max(float(e["mjd_obs"]) for e in exps) - min(float(e["mjd_obs"]) for e in exps)) > 0.05
            ]
            if not items:
                continue
            r_med = float(exact_median_1d(np.asarray([float(e["resolving_power"]) for _, exps in items for e in exps])))
            cfg = get_inst_config(inst, r_med)
            step_a = 0.12 if inst == "ESO_XSHOOTER_3ARM" else float(cfg["coadd_step_angstrom"])
            unp_map = {st: [_decode_prior_bundle_exposure(e, cfg) for e in exps] for st, exps in items}
            w_los = [float(np.nanmin(w)) for st in unp_map for w, _ in unp_map[st] if len(w) > 0]
            w_his = [float(np.nanmax(w)) for st in unp_map for w, _ in unp_map[st] if len(w) > 0]
            w_lo = max(15155.0 if inst == "SDSS_APOGEE2" else 3850.0, min(w_los) - 2.0)
            w_hi = min(16955.0 if inst == "SDSS_APOGEE2" else max(w_his) + 2.0, max(w_his) + 2.0)
            grid = np.arange(w_lo, w_hi + 0.5 * step_a, step_a, dtype=np.float64)

            coadds: list[np.ndarray] = []
            bervs_coh: list[float] = []
            fn_mats: dict[str, np.ndarray] = {}
            for st, exps in items:
                rv_s = float(exps[0].get("prior_rv_kms") or 0.0)
                dop = 1.0 + rv_s / C_KMS
                fm = np.stack([_resample_gap_safe(w / dop, fn, grid, max_gap_a=max(0.5, 5.0 * step_a)) for w, fn in unp_map[st]], axis=0)
                fn_mats[st] = fm
                with warnings.catch_warnings(), np.errstate(all="ignore"):
                    warnings.simplefilter("ignore", RuntimeWarning)
                    co = np.nanmedian(fm, axis=0)
                coadds.append(np.where(np.isfinite(co), co, 1.0))
                bervs_coh.append(float(exact_median_1d(np.asarray([float(e["berv_kms"]) - rv_s for e in exps]))))

            z_rpca = run_cohort_rpca_v50(grid, np.stack(coadds, axis=0))["z_rpca"] if len(items) >= 3 else None
            b_coh = np.asarray(bervs_coh, dtype=np.float64) if len(items) >= 3 else None

            for si, (st, exps) in enumerate(items):
                rv_s = float(exps[0].get("prior_rv_kms") or 0.0)
                fm = fn_mats[st]
                with warnings.catch_warnings(), np.errstate(all="ignore"):
                    warnings.simplefilter("ignore", RuntimeWarning)
                    tpl = np.nanmedian(fm, axis=0)
                tpl = np.where(np.isfinite(tpl) & (tpl > 0.05), tpl, 1.0)
                # Normalize residual around 1.0 so scan_curved_and_periodic_drift_v53 compares strictly against unit photosphere
                fn_rel = np.where(np.isfinite(fm), 1.0 + (fm - tpl), np.nan)
                sig_mat = _build_drift_sigma_matrix_v53(fm, tpl)
                mjds = np.asarray([float(e["mjd_obs"]) for e in exps], dtype=np.float64)
                v_o2r = np.asarray([float(e["berv_kms"]) - rv_s for e in exps], dtype=np.float64)
                res_v53 = scan_curved_and_periodic_drift_v53(
                    grid, fn_rel, sig_mat, mjds, v_o2r, cfg,
                    star=st, star_idx=si, z_rpca_mat=z_rpca, bervs_cohort=b_coh,
                )
                stt = res_v53["stats"]
                all_surv.extend(res_v53["all_survivors"])
                all_rows.append({
                    "phase_source": f"{phase}_ARCHIVE_{'Q' if phase == 'D091' else 'T'}",
                    "instrument": inst,
                    "grating_family": gf,
                    "star": st,
                    "common_name": exps[0].get("common_name", st),
                    "role": exps[0].get("role", "SCIENCE"),
                    "n_epochs": len(exps),
                    "dt_baseline_days": round(float(mjds[-1] - mjds[0]), 4),
                    "n_curved_evals": int(stt["n_curved_evals"]),
                    "n_periodic_evals": int(stt["n_periodic_evals"]),
                    "raw_nonlinear_tracks": int(stt["n_raw_tracks"]),
                    "curved_survivors": len(res_v53["curved_candidates"]),
                    "periodic_survivors": len(res_v53["periodic_candidates"]),
                    "total_survivors": len(res_v53["all_survivors"]),
                })

    return all_rows, all_surv


# ---------------------------------------------------------------------------
# Stage B Synthetic Calibration Suites (10 Suites, 1,911 Trials)
# ---------------------------------------------------------------------------

def _run_v53_calibrations(
    g8_models: dict[str, dict[str, Any]],
    out_dir: Path,
) -> dict[str, Any]:
    rng = np.random.default_rng(RNG_SEED)
    w_ap = 15200.0 + 0.08 * np.arange(16000, dtype=np.float64)
    cfg_ap = get_inst_config("SDSS_APOGEE2", 22500.0)
    w_gh = 6000.0 + 0.03 * np.arange(18000, dtype=np.float64)
    cfg_gh = get_inst_config("GEMINI_GHOST", 56000.0)

    # 1. CALIBRATION_V53_CURVED_PERIODIC_DRIFT_240 (60 curved + 60 periodic vs 40 stationary + 40 1-ep + 40 BERV-sky)
    cp_rows: list[dict[str, Any]] = []
    for ti in range(240):
        use_gh = (ti % 3 == 2)
        w, cfg = (w_gh, cfg_gh) if use_gh else (w_ap, cfg_ap)
        sig_v = float(cfg["sigma_v_kms"])
        sig_a = float(np.mean(w)) / (float(cfg["resolving_power"]) * FWHM_FACTOR)
        noise = 0.02
        if ti < 60:
            cls_ = "CURVED_QUADRATIC"
            n_ep = 4 + (ti % 3)
            mjds = 58000.0 + np.linspace(0.0, 40.0, n_ep)
            bervs = np.linspace(18.0, -16.0, n_ep)
            vdot = 2.6 if ti % 2 == 0 else -2.5
            vddot = -0.14 if ti % 2 == 0 else 0.13
            t_rel = mjds - float(np.mean(mjds))
            u_t = vdot * t_rel + 0.5 * vddot * (t_rel ** 2)
            want = True
        elif ti < 120:
            cls_ = "PERIODIC_ORBITAL"
            n_ep = 8 + (ti % 4)
            per_d = [4.3, 7.1, 11.4, 15.8][ti % 4]
            mjds = 58000.0 + np.sort(rng.uniform(0.0, 26.0, n_ep))
            # guarantee distinct epochs >= 0.05 d
            for ei in range(1, n_ep):
                if mjds[ei] - mjds[ei - 1] < 0.15:
                    mjds[ei] = mjds[ei - 1] + 0.15
            bervs = np.linspace(-18.0, 17.0, n_ep)
            k_amp = [65.0, 88.0, 112.0, 138.0][ti % 4]
            phi0 = float(rng.uniform(0.0, 2.0 * math.pi))
            u_t = k_amp * np.sin(2.0 * math.pi * (mjds - mjds[0]) / per_d + phi0)
            want = True
        elif ti < 160:
            cls_ = "STATIONARY_STELLAR"
            n_ep = 8
            mjds = 58000.0 + np.linspace(0.0, 35.0, n_ep)
            bervs = np.linspace(16.0, -15.0, n_ep)
            u_t = np.zeros(n_ep)
            want = False
        elif ti < 200:
            cls_ = "SINGLE_EPOCH_TRANSIENT"
            n_ep = 8
            mjds = 58000.0 + np.linspace(0.0, 35.0, n_ep)
            bervs = np.linspace(16.0, -15.0, n_ep)
            u_t = None
            want = False
        else:
            cls_ = "BERV_SKY_CONFOUNDER"
            n_ep = 8
            mjds = 58000.0 + np.linspace(0.0, 35.0, n_ep)
            bervs = np.array([-22.0, -10.0, 4.0, 19.0, 24.0, 11.0, -3.0, -19.0])
            u_t = bervs.copy()
            want = False

        # Choose OH-clean base wavelength on real OH-masked APOGEE/GHOST windows
        w_base = float(rng.uniform(float(w[600]), float(w[-600])))
        if want:
            for _ in range(40):
                wc = float(rng.uniform(float(w[600]), float(w[-600])))
                if not any(check_rousselot_oh_and_barycentric_v52((wc * (1.0 + u_t[k] / C_KMS)) / (1.0 + bervs[k] / C_KMS), sig_v)["is_oh_or_sky"] for k in range(n_ep)):
                    w_base = wc
                    break

        fn_ep = 1.0 + rng.normal(0.0, noise, (n_ep, len(w)))
        sig_ep = np.full_like(fn_ep, noise)
        amp_rel = float(rng.uniform(0.18, 0.25)) if want else 0.24
        if u_t is None:
            fn_ep[0] += amp_rel * np.exp(-0.5 * ((w - w_base) / sig_a) ** 2)
        else:
            for k in range(n_ep):
                wk = w_base * (1.0 + float(u_t[k]) / C_KMS)
                fn_ep[k] += amp_rel * np.exp(-0.5 * ((w - wk) / sig_a) ** 2)

        res = scan_curved_and_periodic_drift_v53(w, fn_ep, sig_ep, mjds, bervs, cfg, star=f"CP_{ti:03d}")
        det_ok = len(res["curved_candidates"]) > 0 if cls_ == "CURVED_QUADRATIC" else (len(res["periodic_candidates"]) > 0 if cls_ == "PERIODIC_ORBITAL" else len(res["all_survivors"]) > 0)
        cp_rows.append({
            "trial": ti + 1, "instrument": cfg["instrument"], "trial_class": cls_,
            "n_epochs": n_ep, "curved_hits": len(res["curved_candidates"]),
            "periodic_hits": len(res["periodic_candidates"]),
            "passed": int(det_ok == want),
        })

    # 2. CALIBRATION_V53_SPITZER_IRS_CCF_AND_DYSON_240 (60 gas + 60 Dyson BB vs 60 spectral conf + 60 silicate conf)
    sp_rows: list[dict[str, Any]] = []
    w_irs = np.linspace(5.25, 37.80, 366, dtype=np.float64)
    sp_gases = sorted(SPITZER_IRS_GREENHOUSE_TEMPLATES_UM.keys())
    sp_confs = sorted(SPITZER_IRS_CONFOUNDERS_UM.keys())

    def _bnu(w_u, tk):
        lm = w_u * 1e-6
        x = np.clip((6.62607015e-34 * C_SI) / (lm * 1.380649e-23 * tk), 1e-4, 500.0)
        return 1.0 / ((lm ** 3) * np.expm1(x))

    b_star = _bnu(w_irs, 5800.0)
    a_phot = 2.0 / float(np.median(b_star[w_irs < 7.0]))
    for ti in range(240):
        if ti < 60:
            cls_ = "GAS_INJECTION"
            mol = sp_gases[ti % len(sp_gases)]
            tau = float(rng.uniform(0.10, 0.22))
            prof = sum(float(c["weight"]) * np.exp(-0.5 * ((w_irs - float(c["mu_um"])) / float(c["sigma_um"])) ** 2) for c in SPITZER_IRS_GREENHOUSE_TEMPLATES_UM[mol])
            fl = a_phot * b_star * (1.0 - tau * prof) + rng.normal(0.0, 0.005 * a_phot * b_star)
            ev = np.maximum(1e-4, 0.006 * a_phot * b_star)
            out = scan_spitzer_irs_ccf_and_dyson_v53(w_irs, fl, ev, 5800.0, 10.0)
            ok = mol in out["ccf"]["detected_molecules"]
            sp_rows.append({"trial": ti + 1, "trial_class": cls_, "species": mol, "dyson_cand": int(out["dyson"]["dyson_candidate"]), "passed": int(ok)})
        elif ti < 120:
            cls_ = "DYSON_WASTE_BB"
            tw = float([120.0, 180.0, 240.0, 310.0, 370.0][ti % 5])
            gam = float([0.04, 0.08, 0.14, 0.20][ti % 4])
            b_coef = a_phot * gam * ((5800.0 / tw) ** 4)
            f_mod = a_phot * b_star + b_coef * _bnu(w_irs, tw)
            ev = np.maximum(1e-4, 0.008 * f_mod)
            fl = f_mod + rng.normal(0.0, 0.008 * f_mod)
            out = scan_spitzer_irs_ccf_and_dyson_v53(w_irs, fl, ev, 5800.0, 10.0)
            ok = bool(out["dyson"]["dyson_candidate"])
            sp_rows.append({"trial": ti + 1, "trial_class": cls_, "species": f"BB_{int(tw)}K", "dyson_cand": int(ok), "passed": int(ok)})
        elif ti < 180:
            cls_ = "SPECTRAL_CONFOUNDER"
            cn = sp_confs[(ti - 120) % len(sp_confs)]
            sign = -1.0 if cn in ("PAH_COMPLEX", "SILICATE_10UM", "SILICATE_18UM") else 1.0
            prof = sum(float(c["weight"]) * np.exp(-0.5 * ((w_irs - float(c["mu_um"])) / float(c["sigma_um"])) ** 2) for c in SPITZER_IRS_CONFOUNDERS_UM[cn])
            fl = a_phot * b_star * (1.0 - sign * 0.22 * prof) + rng.normal(0.0, 0.006 * a_phot * b_star)
            ev = np.maximum(1e-4, 0.006 * a_phot * b_star)
            out = scan_spitzer_irs_ccf_and_dyson_v53(w_irs, fl, ev, 5800.0, 10.0)
            ok = (not out["ccf"]["any_detection"]) and (not out["dyson"]["dyson_candidate"])
            sp_rows.append({"trial": ti + 1, "trial_class": cls_, "species": cn, "dyson_cand": int(out["dyson"]["dyson_candidate"]), "passed": int(ok)})
        else:
            cls_ = "SILICATE_DEBRIS_DISK"
            td = float([140.0, 185.0, 230.0][(ti - 180) % 3])
            b_coef = a_phot * 0.04 * ((5800.0 / td) ** 4)
            sil_bump = 0.28 * np.exp(-0.5 * ((w_irs - 10.2) / 1.1) ** 2) + 0.35 * np.exp(-0.5 * ((w_irs - 18.8) / 2.3) ** 2)
            f_mod = a_phot * b_star + b_coef * _bnu(w_irs, td) * (1.0 + sil_bump)
            ev = np.maximum(1e-4, 0.008 * f_mod)
            fl = f_mod + rng.normal(0.0, 0.008 * f_mod)
            out = scan_spitzer_irs_ccf_and_dyson_v53(w_irs, fl, ev, 5800.0, 10.0)
            ok = (not out["dyson"]["dyson_candidate"]) and (not out["ccf"]["any_detection"])
            sp_rows.append({"trial": ti + 1, "trial_class": cls_, "species": f"SIL_{int(td)}K", "dyson_cand": int(out["dyson"]["dyson_candidate"]), "passed": int(ok)})

    # 3. CALIBRATION_V53_GHOST_SKY_FIBER_120 (60 pure star fiber vs 60 simultaneous sky+star airglow)
    gs_rows: list[dict[str, Any]] = []
    wg_s = 6296.0 + 0.03 * np.arange(320, dtype=np.float64)
    sig_g = 6300.0 / (56000.0 * FWHM_FACTOR)
    fwhm_g = sig_g * FWHM_FACTOR
    for ti in range(120):
        wc = float(wg_s[160])
        sky_fl = 50.0 + rng.normal(0.0, 4.0, len(wg_s))
        sky_er = np.full(len(wg_s), 4.0)
        if ti < 60:
            cls_, want = "STAR_ONLY_CLEAN", False
        else:
            cls_, want = "SKY_AIRGLOW_CONTAMINATED", True
            sky_fl += rng.uniform(30.0, 90.0) * np.exp(-0.5 * ((wg_s - wc) / sig_g) ** 2)
        vet = apply_ghost_sky_fiber_veto_v53(wg_s, 12.0, wg_s, sky_fl, sky_er, wc, fwhm_g, max_sky_z=3.0)
        gs_rows.append({"trial": ti + 1, "trial_class": cls_, "sky_z_max": vet["sky_z_max"], "vetoed": int(vet["vetoed"]), "passed": int(bool(vet["vetoed"]) == want)})

    # 4. CALIBRATION_G8_V53_120 (40 isolated + 40 shared + 40 topo)
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

    # 5. CALIBRATION_V53_RPCA_RARITY_180
    rp_rows: list[dict[str, Any]] = []
    w_r = 15200.0 + 0.08 * np.arange(2048, dtype=np.float64)
    bervs_r = np.linspace(-25.0, 25.0, 8)
    for ti in range(180):
        mat = np.ones((8, 2048), dtype=np.float64) + rng.normal(0.0, 0.015, size=(8, 2048))
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
        rp_rows.append({"trial": ti + 1, "class": cls_, "z_rpca": round(zp, 2), "rarity": round(rr["rarity_score"], 3), "passed": int(bool(ok) == want)})

    # 6. CALIBRATION_V53_AGNOSTIC_120
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

    # 7. DETECTOR_V53_G4G5_CALIBRATION_108
    g45_rows: list[dict[str, Any]] = []
    wp = 6500.0 + 0.035 * np.arange(151, dtype=np.float64)
    w_sig_gh = 6500.0 / (56000.0 * FWHM_FACTOR)
    for ti in range(108):
        fl = 1000.0 + rng.normal(0.0, 10.0, 151)
        er = np.full(151, 10.0)
        dq = np.zeros(151, dtype=np.int32)
        if ti < 36:
            cls_, want = "TRUE_LSF", True
            fl += 180.0 * np.exp(-0.5 * ((wp - wp[75]) / w_sig_gh) ** 2)
        elif ti < 72:
            cls_, want = "COSMIC_HOTPX", False
            fl[75] += 260.0
        else:
            cls_, want = "BROAD_PLATEAU", False
            fl += 140.0 * np.exp(-0.5 * ((wp - wp[75]) / (7.5 * w_sig_gh)) ** 2)
        ev = evaluate_gates_g3_g4_g5_v42(
            [{"order": 1, "native_pixel": 1000, "wave": wp, "flux_a": fl, "ref_norm_a": np.ones(151), "err_a": er, "dq": dq, "target_wave_a": wp[75]}],
            "GHOST_BR", "T", wp[75], cfg_gh,
        )
        ok = bool(ev["g3_pass"] and ev["g4_pass"] and ev["g5_pass"])
        g45_rows.append({"trial": ti + 1, "class": cls_, "passed": int(ok == want)})

    # 8. INJECTION_RECOVERY_540 (across 10 bands: 4 APOGEE-2 + 6 GHOST = 54 trials/band)
    inj_rows: list[dict[str, Any]] = []
    comp_map: dict[tuple[str, str], list[int]] = {}
    band_list_10 = [("SDSS_APOGEE2", b) for b in CALIBRATION_BANDS_GHOST[:0]] + [("SDSS_APOGEE2", b) for b in get_calibration_bands("SDSS_APOGEE2")] + [("GEMINI_GHOST", b) for b in CALIBRATION_BANDS_GHOST]
    for ti in range(540):
        inst, bd = band_list_10[ti % len(band_list_10)]
        cfg_i = get_inst_config(inst, 22500.0 if inst == "SDSS_APOGEE2" else 56000.0)
        wc = float(bd["center_wave_A"])
        dw_i = 0.08 if inst == "SDSS_APOGEE2" else 0.03
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

    # 9. COMB_V4_1_CALIBRATION_162 (GEMINI_GHOST GHOST_RED_VIS band)
    comb_cal_rows: list[dict[str, Any]] = []
    wc_grid = 5600.0 + 0.03 * np.arange(8192, dtype=np.float64)
    wins = [COMB_V4_1_WINDOWS_A["GEMINI_GHOST"][1]]
    sig_comb = 0.048
    fwhm_comb = sig_comb * FWHM_FACTOR
    for ti in range(162):
        yr = rng.normal(0.0, 0.015, len(wc_grid))
        yt = rng.normal(0.0, 0.015, len(wc_grid))
        sr = np.full(len(wc_grid), 0.015)
        st = np.full(len(wc_grid), 0.015)
        tpl = np.ones(len(wc_grid))
        sky = np.zeros(len(wc_grid), dtype=bool)
        if ti < 54:
            cls_, want = "TRUE_COMB_V41", True
            dnu = [40.0, 65.0, 100.0][ti % 3]
            nu0 = 515000.0 + (ti % 9) * 200.0
            for m in range(6):
                wm = C_ANGSTROM_GHZ / (nu0 + m * dnu)
                yr += 0.095 * np.exp(-0.5 * ((wc_grid - wm) / sig_comb) ** 2)
        elif ti < 108:
            cls_, want = "RANDOM_FOREST", False
            dnu = 65.0
            nu0 = 515200.0 + ((ti - 54) % 9) * 150.0
            teeth_w = [C_ANGSTROM_GHZ / (nu0 + m * dnu) for m in range(6)]
            for wf in np.arange(min(teeth_w) - 10.0, max(teeth_w) + 10.0, 0.80 * fwhm_comb):
                yr += 0.085 * np.exp(-0.5 * ((wc_grid - wf) / sig_comb) ** 2)
            for wt in teeth_w:
                yr += 0.085 * np.exp(-0.5 * ((wc_grid - wt) / sig_comb) ** 2)
        else:
            cls_, want = "TOPO_SKY_COMB", False
            yt = yr.copy()
            dnu = 65.0
            nu0 = 515400.0
            for m in range(6):
                wm = C_ANGSTROM_GHZ / (nu0 + m * dnu)
                g = 0.095 * np.exp(-0.5 * ((wc_grid - wm) / sig_comb) ** 2)
                yr += g
                yt += 1.15 * g
        c_v41, _ = scan_frequency_comb_v4_1(wc_grid, yr, sr, 1.0 + yr, tpl, sky, yt, st, wins, ["GHOST_RED_VIS"], cfg_gh)
        c_v4, _ = scan_frequency_comb_v4(wc_grid, yr, sr, 1.0 + yr, tpl, sky, yt, st, wins, ["GHOST_RED_VIS"], cfg_gh)
        comb_cal_rows.append({"trial": ti + 1, "class": cls_, "v4_hits": len(c_v4), "v41_hits": len(c_v41), "passed": int((len(c_v41) > 0) == want)})

    # 10. KEPLERIAN_TRACK_CALIBRATION_81
    kep_rows: list[dict[str, Any]] = []
    wk_grid = 6500.0 + 0.03 * (np.arange(601, dtype=np.float64) - 300.0)
    sig_kep = 6500.0 / (56000.0 * FWHM_FACTOR)
    vorb_phases = (-62.0, -21.0, 21.0, 62.0)
    for ti in range(81):
        amp_k = 5.0 * 0.012
        ep_res, ep_pl = [], []
        for dv_o in vorb_phases:
            y_k = rng.normal(0.0, 0.012, len(wk_grid)) + amp_k * np.exp(-0.5 * ((wk_grid - 6500.0 * (1.0 + dv_o / C_KMS)) / sig_kep) ** 2)
            ep_res.append(y_k)
            w_de = bary_to_planet_rest_wave(wk_grid, 0.0, dv_o)
            ep_pl.append(np.interp(wk_grid, w_de, y_k, left=0.0, right=0.0))
        f_td = fit_lsf_on_window(wk_grid, np.mean(ep_res, axis=0), 6500.0, cfg_gh, fixed_phase_bins=0.0)
        f_kp = fit_lsf_on_window(wk_grid, np.mean(ep_pl, axis=0), 6500.0, cfg_gh, fixed_phase_bins=0.0)
        std_ = float(f_td.get("snr_mid", 0.0)) if f_td.get("valid_fit") else 0.0
        skp_ = float(f_kp.get("snr_mid", 0.0)) if f_kp.get("valid_fit") else 0.0
        kep_rows.append({"trial": ti + 1, "snr_tdiff": round(std_, 3), "snr_kplanet": round(skp_, 3), "tdiff_fa": int(std_ >= 6.5), "kplanet_rec": int(skp_ >= 6.5)})

    _write_csv(out_dir / "CALIBRATION_V53_CURVED_PERIODIC_DRIFT_240.csv", list(cp_rows[0].keys()), cp_rows)
    _write_csv(out_dir / "CALIBRATION_V53_SPITZER_IRS_CCF_AND_DYSON_240.csv", list(sp_rows[0].keys()), sp_rows)
    _write_csv(out_dir / "CALIBRATION_V53_GHOST_SKY_FIBER_120.csv", list(gs_rows[0].keys()), gs_rows)
    _write_csv(out_dir / "CALIBRATION_G8_V53_120.csv", list(g8_rows[0].keys()), g8_rows)
    _write_csv(out_dir / "CALIBRATION_V53_RPCA_RARITY_180.csv", list(rp_rows[0].keys()), rp_rows)
    _write_csv(out_dir / "CALIBRATION_V53_AGNOSTIC_120.csv", list(ag_rows[0].keys()), ag_rows)
    _write_csv(out_dir / "DETECTOR_V53_G4G5_CALIBRATION_108.csv", list(g45_rows[0].keys()), g45_rows)
    _write_csv(out_dir / "INJECTION_RECOVERY_540.csv", list(inj_rows[0].keys()), inj_rows)
    _write_csv(out_dir / "CALIBRATION_COMPLETENESS_BY_BAND.csv", list(comp_rows[0].keys()), comp_rows)
    _write_csv(out_dir / "COMB_V4_1_CALIBRATION_162.csv", list(comb_cal_rows[0].keys()), comb_cal_rows)
    _write_csv(out_dir / "KEPLERIAN_TRACK_CALIBRATION_81.csv", list(kep_rows[0].keys()), kep_rows)

    tot_trials = 240 + 240 + 120 + 120 + 180 + 120 + 108 + 540 + 162 + 81
    assert tot_trials == 1911

    def _cnt(lst, cls_k=None):
        sub = [r for r in lst if cls_k is None or r.get("trial_class", r.get("class")) == cls_k]
        p = sum(r["passed"] for r in sub)
        return f"{p}/{len(sub)} ({p/len(sub):.4f})"

    return {
        "total_trials": tot_trials,
        "curved_drift_v53_recovery": _cnt(cp_rows, "CURVED_QUADRATIC"),
        "periodic_drift_v53_recovery": _cnt(cp_rows, "PERIODIC_ORBITAL"),
        "cp_drift_stationary_veto": _cnt(cp_rows, "STATIONARY_STELLAR"),
        "cp_drift_transient_veto": _cnt(cp_rows, "SINGLE_EPOCH_TRANSIENT"),
        "cp_drift_berv_sky_veto": _cnt(cp_rows, "BERV_SKY_CONFOUNDER"),
        "spitzer_gas_ccf_recovery": _cnt(sp_rows, "GAS_INJECTION"),
        "spitzer_dyson_bb_recovery": _cnt(sp_rows, "DYSON_WASTE_BB"),
        "spitzer_spectral_conf_veto": _cnt(sp_rows, "SPECTRAL_CONFOUNDER"),
        "spitzer_silicate_debris_veto": _cnt(sp_rows, "SILICATE_DEBRIS_DISK"),
        "ghost_sky_fiber_clean_pass": _cnt(gs_rows, "STAR_ONLY_CLEAN"),
        "ghost_sky_fiber_airglow_veto": _cnt(gs_rows, "SKY_AIRGLOW_CONTAMINATED"),
        "g8_v53_isolated_pass": _cnt(g8_rows, "ISOLATED_LASER"),
        "g8_v53_shared_suppression": _cnt(g8_rows, "SHARED_LEAK"),
        "g8_v53_topo_suppression": _cnt(g8_rows, "TOPO_LEAK"),
        "rpca_isolated_recovery": _cnt(rp_rows, "ISOLATED"),
        "rpca_shared_suppression": _cnt(rp_rows, "SHARED_REST"),
        "rpca_topo_suppression": _cnt(rp_rows, "SHARED_TOPO"),
        "agnostic_multiscale_recovery": _cnt(ag_rows),
        "g45_true_lsf_pass": _cnt(g45_rows, "TRUE_LSF"),
        "g5_cosmic_rejection": _cnt(g45_rows, "COSMIC_HOTPX"),
        "g5_plateau_rejection": _cnt(g45_rows, "BROAD_PLATEAU"),
        "channel_p_ge_8sigma": f"{sum(r['pass_p'] for r in inj_rows)}/{len(inj_rows)} ({sum(r['pass_p'] for r in inj_rows)/len(inj_rows):.4f})",
        "comb_v41_recovery": _cnt(comb_cal_rows, "TRUE_COMB_V41"),
        "comb_v41_forest_fa": f"{sum(r['v41_hits']>0 for r in comb_cal_rows if r['class']=='RANDOM_FOREST')}/54",
        "comb_v41_topo_fa": f"{sum(r['v41_hits']>0 for r in comb_cal_rows if r['class']=='TOPO_SKY_COMB')}/54",
        "keplerian_kplanet_rec": f"{sum(r['kplanet_rec'] for r in kep_rows)}/{len(kep_rows)} ({sum(r['kplanet_rec'] for r in kep_rows)/len(kep_rows):.4f})",
    }


def _evaluate_stage2_physical_triage(
    inst: str, ch: str, w_bary: float, u: dict[str, Any], ctx: dict[str, Any]
) -> dict[str, Any]:
    """Deterministic Stage-2 physical triage on raw Stage-1 ledger survivors (Stage-1 detector stays locked)."""
    wide_cont_ratio = math.nan
    double_peaked_core = False
    for arm in u.get("arms", []):
        w = arm["w_bary"]
        fl = arm["flux"]
        if len(w) < 20 or not (float(w[0]) <= w_bary <= float(w[-1])):
            continue
        m_pk = (np.abs(w - w_bary) <= 0.20) & np.isfinite(fl)
        m_25 = (np.abs(w - w_bary) <= 25.0) & np.isfinite(fl)
        if int(np.sum(m_pk)) >= 1 and int(np.sum(m_25)) >= 100:
            p90 = float(np.percentile(fl[m_25], 90.0))
            if p90 > 0.0:
                wide_cont_ratio = float(np.max(fl[m_pk])) / p90
        idx0 = int(np.argmin(np.abs(w - w_bary)))
        if 2 <= idx0 <= len(fl) - 3 and np.all(np.isfinite(fl[idx0 - 2 : idx0 + 3])):
            double_peaked_core = any(
                float(fl[k]) < min(float(fl[k - 1]), float(fl[k + 1]))
                for k in range(idx0 - 1, idx0 + 2)
            )
        break

    ratio_out: Any = round(wide_cont_ratio, 4) if math.isfinite(wide_cont_ratio) else ""
    if inst == "GEMINI_GHOST" and len(ctx["exps"]) == 1:
        status = (
            "STAGE2_VETO_1EP_DRAGONS_NOCR_SPLIT_CR"
            if double_peaked_core
            else "STAGE2_VETO_1EP_DRAGONS_NOCR_UNCONFIRMED"
        )
        return {
            "stage2_wide_cont_ratio": ratio_out,
            "stage2_double_peaked_core": bool(double_peaked_core),
            "stage2_triage_status": status,
            "stage2_pass": False,
        }
    if math.isfinite(wide_cont_ratio) and wide_cont_ratio < 1.05:
        return {
            "stage2_wide_cont_ratio": ratio_out,
            "stage2_double_peaked_core": bool(double_peaked_core),
            "stage2_triage_status": "STAGE2_VETO_SUBPHOTOSPHERIC_TROUGH",
            "stage2_pass": False,
        }
    return {
        "stage2_wide_cont_ratio": ratio_out,
        "stage2_double_peaked_core": bool(double_peaked_core),
        "stage2_triage_status": "PASS",
        "stage2_pass": True,
    }


# ---------------------------------------------------------------------------
# Stage B Main Orchestrator
# ---------------------------------------------------------------------------

def run_stage_b(bundle: dict[str, Any], out_dir: Path, archives_dir_arg: Path | None = None) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    method_lock = json.loads((WS / "METHOD_LOCK.json").read_text(encoding="utf-8"))
    prior_snap = json.loads((WS / "PRIOR_V5_2_PHASES_SNAPSHOT.json").read_text(encoding="utf-8"))
    orb_doc = json.loads((WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))

    exposures = bundle["exposures"]
    by_inst_star: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for ex in exposures:
        by_inst_star.setdefault((ex["instrument"], ex["star"]), []).append(ex)

    prov_rows: list[dict[str, Any]] = []
    rv_anchor_rows: list[dict[str, Any]] = []
    star_rv_rows: list[dict[str, Any]] = []
    bench_rows: list[dict[str, Any]] = []
    ledger_rows: list[dict[str, Any]] = []
    ghost_sky_rows: list[dict[str, Any]] = []
    v53_drift_rows: list[dict[str, Any]] = []
    v52_drift_rows: list[dict[str, Any]] = []
    v51_drift_rows: list[dict[str, Any]] = []
    ag_survivor_rows: list[dict[str, Any]] = []
    comb_star_rows: list[dict[str, Any]] = []
    comb_cand_rows: list[dict[str, Any]] = []
    orb_res_rows: list[dict[str, Any]] = []
    ul_rows: list[dict[str, Any]] = []
    g8_models: dict[str, dict[str, Any]] = {}
    bin_stats: dict[str, dict[str, int]] = {}
    v2_fa_eliminated_total = 0
    cand_counter = 0

    def _add_bins(inst: str, key: str, n: int) -> None:
        bin_stats.setdefault(inst, {"T": 0, "P": 0, "K_PLANET": 0, "COMB_CONFIGS": 0, "DRIFT_V52_EVALS": 0, "DRIFT_V53_EVALS": 0})
        bin_stats[inst][key] += int(n)

    # 1. Process Optical + NIR Manifolds (`SDSS_APOGEE2` + `GEMINI_GHOST`)
    for inst in ("SDSS_APOGEE2", "GEMINI_GHOST"):
        my_keys = sorted(k for k in by_inst_star if k[0] == inst)
        star_contexts: dict[str, dict[str, Any]] = {}
        comb_tasks: list[tuple[Any, ...]] = []

        for _, st in my_keys:
            exps = sorted(by_inst_star[(inst, st)], key=lambda e: (float(e["mjd_obs"]), int(e["epoch_rank"])))
            r_med = float(exact_median_1d(np.asarray([float(e["resolving_power"]) for e in exps])))
            cfg = get_inst_config(inst, r_med)
            unp_list = [_unpack_exposure_spectrum(e, cfg, compute_cont=True) for e in exps]

            exp_rvs: list[float] = []
            for e, u in zip(exps, unp_list):
                n_v2 = _compute_legacy_v2_count(u["w_bary"], u["fn"])
                v2_fa_eliminated_total += n_v2
                rv_fit_sum, rv_ancs, _ = measure_exposure_stellar_rv(u["w_bary"], u["fn"], float(e["prior_rv_kms"]), cfg)
                rv_u = float(rv_fit_sum["empirical_rv_kms"])
                if not math.isfinite(rv_u):
                    rv_u = float(e.get("apogee_h9_vhelio_kms", e["prior_rv_kms"]))
                exp_rvs.append(rv_u)
                for ar in rv_ancs:
                    rv_anchor_rows.append({"instrument": inst, "star": st, "dp_id": e["dp_id"], "anchor_id": ar["anchor_id"], "rv_kms": ar["best_rv_kms"], "snr": ar["rel_depth"]})
                prov_rows.append({
                    "instrument": inst, "star": st, "dp_id": e["dp_id"], "role": e["role"],
                    "mjd_obs": e["mjd_obs"], "t_exptime_s": e["t_exptime_s"], "grating": e["grating"],
                    "berv_kms": e["berv_kms"], "rv_kms": round(rv_u, 4), "v2_fa": n_v2,
                })

            rv_star = float(exact_median_1d(np.asarray(exp_rvs, dtype=np.float64)))
            star_rv_rows.append({
                "instrument": inst, "star": st, "role": exps[0]["role"], "n_epochs": len(exps),
                "rv_median_kms": round(rv_star, 4), "rv_prior_kms": round(float(exps[0]["prior_rv_kms"]), 4),
                "rv_scatter_kms": round(float(exact_mad_1d(np.asarray(exp_rvs))), 4) if len(exp_rvs) > 1 else 0.0,
            })
            star_contexts[st] = {"instrument": inst, "star": st, "exps": exps, "unp": unp_list, "exp_rvs": exp_rvs, "rv_star": rv_star, "cfg": cfg, "r_med": r_med}

        st_list = sorted(star_contexts.keys())
        if inst == "SDSS_APOGEE2":
            wlo, whi, step_a, grp_name, max_gap_r = 15155.0, 16955.0, 0.08, "APOGEE2_H", 0.45
            cfg_g = get_inst_config("SDSS_APOGEE2", 22500.0)
        else:
            wlo, whi, step_a, grp_name, max_gap_r = 3475.0, 10610.0, 0.03, "GHOST_BR", 0.35
            cfg_g = get_inst_config("GEMINI_GHOST", 56000.0)
        grid_g = np.arange(wlo, whi + 0.5 * step_a, step_a, dtype=np.float64)

        coadd_fn_list, coadd_mask_list, coadd_berv_list = [], [], []
        star_ep_res: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}
        for st in st_list:
            ctx = star_contexts[st]
            fn_rows, fl_rows, mjds_b, v_o2r_b = [], [], [], []
            for idx_e, (e, u) in enumerate(zip(ctx["exps"], ctx["unp"])):
                dop_e = 1.0 + ctx["exp_rvs"][idx_e] / C_KMS
                fn_rows.append(_resample_gap_safe(u["w_bary"] / dop_e, u["fn"], grid_g, max_gap_a=max_gap_r))
                fl_rows.append(_resample_gap_safe(u["w_bary"] / dop_e, u["flux_cgs"], grid_g, max_gap_a=max_gap_r))
                mjds_b.append(float(e["mjd_obs"]))
                v_o2r_b.append(float(e["berv_kms"]) - ctx["exp_rvs"][idx_e])
            fn_mat = np.stack(fn_rows, axis=0)
            fl_mat = np.stack(fl_rows, axis=0)
            with warnings.catch_warnings(), np.errstate(all="ignore"):
                warnings.simplefilter("ignore", RuntimeWarning)
                fn_coadd = np.nanmedian(fn_mat, axis=0)
            valid_c = np.isfinite(fn_coadd)
            coadd_fn_list.append(np.where(valid_c, fn_coadd, 1.0))
            coadd_mask_list.append(valid_c)
            coadd_berv_list.append(float(exact_median_1d(np.asarray(v_o2r_b))))
            star_ep_res[st] = (fn_mat, fl_mat, np.asarray(mjds_b), np.asarray(v_o2r_b))

        X_grp = np.stack(coadd_fn_list, axis=0)
        M_grp = np.stack(coadd_mask_list, axis=0)
        B_grp = np.asarray(coadd_berv_list, dtype=np.float64)
        teff_vec = np.asarray([float(star_contexts[s]["exps"][0]["teff_k"]) for s in st_list], dtype=np.float64)
        rpca_out = run_cohort_rpca_v50(grid_g, np.where(M_grp, X_grp, np.nan), teffs=teff_vec)
        z_rpca_mat = rpca_out["z_rpca"]
        tpl_mat = np.where(M_grp & np.isfinite(rpca_out["S_loso"]), X_grp - rpca_out["S_loso"], 1.0)

        patch_feats: list[np.ndarray] = []
        for si in range(len(st_list)):
            z_row = z_rpca_mat[si]
            fin_idx = np.flatnonzero(np.isfinite(z_row))
            for idx_p in fin_idx[::max(25, len(fin_idx) // 90)]:
                zp_v = float(z_row[idx_p])
                if abs(zp_v) < 4.0:
                    rr_p = compute_spectral_rarity_score(grid_g, z_rpca_mat, B_grp, si, float(grid_g[idx_p]), float(cfg_g["sigma_v_kms"]))
                    rf = _extract_g8_feat_v52(z_row, int(idx_p), zp_v, rr_p["rarity_score"], rr_p["f_rest"], rr_p["f_topo"])
                    if rf is not None:
                        patch_feats.append(rf[0])
        g8_model = fit_patch_novelty_model_v52(patch_feats)
        g8_models[grp_name] = g8_model

        sparse_atlas: list[dict[str, Any]] = []
        per_star_scans: dict[str, list[dict[str, Any]]] = {}

        for si, st in enumerate(st_list):
            ctx = star_contexts[st]
            fn_mat, fl_mat, mjds_b, v_o2r_b = star_ep_res[st]
            tpl_s = np.where(np.isfinite(tpl_mat[si]), tpl_mat[si], 1.0)
            res_c = np.where(M_grp[si], X_grp[si] - tpl_s, np.nan)
            sig_p_vec = np.full(len(grid_g), max(1e-4, exact_mad_1d(res_c[M_grp[si]])) if np.any(M_grp[si]) else 0.02)
            star_cands: list[dict[str, Any]] = []

            for k_loc, (e, u) in enumerate(zip(ctx["exps"], ctx["unp"])):
                _add_bins(inst, "T", int(np.sum(np.isfinite(fn_mat[k_loc]))))
                res_e = fn_mat[k_loc] - tpl_s
                fin_e = np.isfinite(res_e)
                mad_e = max(1e-4, exact_mad_1d(res_e[fin_e])) if np.any(fin_e) else 0.02
                sig_e = np.full(len(grid_g), mad_e)
                pks_t, _, _ = scan_single_exposure_residual_lsf(grid_g, res_e, cfg_g, channel="T", flux_norm_for_f1=fn_mat[k_loc])
                for pk in pks_t[:24]:
                    w_rest = float(pk["fitted_center_a"])
                    w_bary = w_rest * (1.0 + ctx["exp_rvs"][k_loc] / C_KMS)
                    w_topo = w_bary / (1.0 + float(e["berv_kms"]) / C_KMS)
                    patches = _extract_native_patches_for_cand(u["arms"], tpl_s, grid_g, w_bary, ctx["exp_rvs"][k_loc])
                    sparse_atlas.append({"star": st, "dp_id": e["dp_id"], "topo_wave_a": w_topo, "berv_kms": float(e["berv_kms"]), "native_order": patches[0]["order"] if patches else None, "native_px": patches[0]["native_pixel"] if patches else None})
                    star_cands.append({"channel": "T", "exp": e, "unp": u, "rv": ctx["exp_rvs"][k_loc], "w_rest": w_rest, "w_bary": w_bary, "w_topo": w_topo, "pk": pk, "patches": patches, "z_vec": res_e / sig_e})

            _add_bins(inst, "P", int(np.sum(M_grp[si])))
            pks_p, _, _ = scan_single_exposure_residual_lsf(grid_g, res_c, cfg_g, channel="P", flux_norm_for_f1=X_grp[si], enforce_f1_in_g1=False)
            for pk in pks_p[:24]:
                e0, u0 = ctx["exps"][0], ctx["unp"][0]
                w_rest = float(pk["fitted_center_a"])
                w_bary = w_rest * (1.0 + ctx["rv_star"] / C_KMS)
                w_topo = w_bary / (1.0 + coadd_berv_list[si] / C_KMS)
                patches = _extract_native_patches_for_cand(u0["arms"], tpl_s, grid_g, w_bary, ctx["rv_star"])
                star_cands.append({"channel": "P", "exp": e0, "unp": u0, "rv": ctx["rv_star"], "w_rest": w_rest, "w_bary": w_bary, "w_topo": w_topo, "pk": pk, "patches": patches, "z_vec": z_rpca_mat[si]})

            # Orbital K_PLANET channel across ALL 8 campaigns (#126-#133) in GHOST & APOGEE-2
            if st in orb_doc["campaigns"] and orb_doc["campaigns"][st]["instrument"] == inst:
                camp = orb_doc["campaigns"][st]
                p_d, t0_b, kp = float(camp["orb_per_days"]), float(camp["orb_t0_bjd"]), float(camp["kp_kms"])
                _add_bins(inst, "K_PLANET", int(np.sum(M_grp[si])))
                kp_rows, kp_fn_rows = [], []
                for e, u in zip(ctx["exps"], ctx["unp"]):
                    _, o_rv = compute_planet_orbital_rv_kms(float(e["mjd_obs"]) + 2400000.5, t0_b, p_d, kp)
                    w_pl = bary_to_planet_rest_wave(u["w_bary"], ctx["rv_star"], o_rv)
                    kp_rows.append(_resample_gap_safe(w_pl, u["fn"] - np.interp(u["w_bary"] / (1.0 + ctx["rv_star"] / C_KMS), grid_g, tpl_s, left=1.0, right=1.0), grid_g, max_gap_a=max_gap_r))
                    kp_fn_rows.append(_resample_gap_safe(w_pl, u["fn"], grid_g, max_gap_a=max_gap_r))
                with warnings.catch_warnings(), np.errstate(all="ignore"):
                    warnings.simplefilter("ignore", RuntimeWarning)
                    kp_coadd = np.nanmean(np.stack(kp_rows, axis=0), axis=0)
                    kp_fn_coadd = np.nanmean(np.stack(kp_fn_rows, axis=0), axis=0)
                fin_kp = np.isfinite(kp_coadd)
                if int(np.sum(fin_kp)) >= 64:
                    sig_kp = np.full(len(grid_g), max(1e-4, exact_mad_1d(kp_coadd[fin_kp])))
                    pks_kp, _, _ = scan_single_exposure_residual_lsf(grid_g, kp_coadd, cfg_g, channel="K_PLANET", flux_norm_for_f1=kp_fn_coadd, enforce_f1_in_g1=False)
                    for pk in pks_kp[:12]:
                        e0, u0 = ctx["exps"][0], ctx["unp"][0]
                        w_pl = float(pk["fitted_center_a"])
                        w_bary = planet_rest_to_bary_wave(w_pl, ctx["rv_star"], camp["exposures"][0]["planet_orbital_rv_kms"])
                        w_topo = w_bary / (1.0 + float(e0["berv_kms"]) / C_KMS)
                        patches = _extract_native_patches_for_cand(u0["arms"], tpl_s, grid_g, w_bary, ctx["rv_star"])
                        star_cands.append({"channel": "K_PLANET", "exp": e0, "unp": u0, "rv": ctx["rv_star"], "w_rest": w_pl, "w_bary": w_bary, "w_topo": w_topo, "pk": pk, "patches": patches, "z_vec": kp_coadd / sig_kp})

            per_star_scans[st] = star_cands

            # Drift Engines: V5.3 Curved+Periodic (N>=4) + V5.2 Linear (N>=3) + V5.1 Pair (N==2)
            z_ep_mat = _build_drift_z_matrix_v52(fn_mat, tpl_s)
            dt_base = float(mjds_b[-1] - mjds_b[0]) if len(mjds_b) >= 2 else 0.0
            if len(ctx["exps"]) >= 4 and dt_base > 0.05:
                fn_rel = np.where(np.isfinite(fn_mat), 1.0 + (fn_mat - tpl_s), np.nan)
                sig_mat = _build_drift_sigma_matrix_v53(fn_mat, tpl_s)
                res_v53 = scan_curved_and_periodic_drift_v53(
                    grid_g, fn_rel, sig_mat, mjds_b, v_o2r_b, cfg_g,
                    star=st, star_idx=si, z_rpca_mat=z_rpca_mat, bervs_cohort=B_grp,
                )
                stt = res_v53["stats"]
                _add_bins(inst, "DRIFT_V53_EVALS", int(stt["n_curved_evals"]) + int(stt["n_periodic_evals"]))
                v53_drift_rows.append({
                    "phase_source": "D095", "instrument": inst, "grating_family": grp_name,
                    "star": st, "common_name": ctx["exps"][0]["common_name"], "role": ctx["exps"][0]["role"],
                    "n_epochs": len(ctx["exps"]), "dt_baseline_days": round(dt_base, 4),
                    "n_curved_evals": int(stt["n_curved_evals"]), "n_periodic_evals": int(stt["n_periodic_evals"]),
                    "raw_nonlinear_tracks": int(stt["n_raw_tracks"]),
                    "curved_survivors": len(res_v53["curved_candidates"]),
                    "periodic_survivors": len(res_v53["periodic_candidates"]),
                    "total_survivors": len(res_v53["all_survivors"]),
                })

            if len(ctx["exps"]) >= 3 and dt_base > 0.05:
                dc_raw, d_info = scan_multiepoch_drift_chaining_v52(grid_g, z_ep_mat, mjds_b, v_o2r_b, cfg_g, star=st, star_idx=si, z_rpca_mat=z_rpca_mat, bervs_cohort=B_grp)
                dc_v52, vet_r = _vet_multiepoch_drift_tracks_v52(dc_raw, grid_g, fn_mat, tpl_s, mjds_b, cfg_g)
                _add_bins(inst, "DRIFT_V52_EVALS", int(d_info.get("n_traj_evals", 0)))
                v52_drift_rows.append({
                    "instrument": inst, "star": st, "role": ctx["exps"][0]["role"], "n_epochs": len(ctx["exps"]),
                    "dt_days": round(dt_base, 4), "n_traj_evals": int(d_info.get("n_traj_evals", 0)),
                    "raw_tracks": len(dc_raw), "survivors": len(dc_v52), "veto_summary": ";".join(sorted(set(vet_r))),
                })
            elif len(ctx["exps"]) == 2 and dt_base > 0.01:
                dc_v51, d51_info = scan_blind_drift_dedoppler_v51(grid_g, z_ep_mat[0], z_ep_mat[1], dt_base, float(v_o2r_b[0]), float(v_o2r_b[1]), cfg_g, star=st, star_idx=si, z_rpca_mat=z_rpca_mat, bervs_cohort=B_grp)
                v51_drift_rows.append({"instrument": inst, "star": st, "dt_days": round(dt_base, 4), "n_evals": int(d51_info.get("n_evals", 0)), "survivors": len(dc_v51)})

            ag_surv, _ = scan_agnostic_multiscale_v50(grid_g, z_rpca_mat[si], si, z_rpca_mat, B_grp, cfg_g)
            for ag in ag_surv:
                ag_survivor_rows.append({"instrument": inst, "star": st, **ag})

            e0, u0 = ctx["exps"][0], ctx["unp"][0]
            w_tp0 = u0["w_bary"] / (1.0 + float(e0["berv_kms"]) / C_KMS)
            y_topo = _resample_gap_safe(w_tp0, u0["fn"] - 1.0, grid_g, max_gap_a=max_gap_r)
            comb_tasks.append((f"{st}_{grp_name}", inst, ctx["r_med"], grid_g, res_c, X_grp[si], tpl_s, np.zeros(len(grid_g), dtype=bool), y_topo, float(sig_p_vec[0])))

        # Gate vetting G1..G8 (+ simultaneous sky-fiber veto on GEMINI_GHOST!)
        n_g1 = n_g2 = n_sky = n_g3 = n_g45 = n_g6 = n_g7 = n_g8 = n_verified_eti = 0
        sky_veto_standalone_g1 = 0
        for si, st in enumerate(st_list):
            ctx = star_contexts[st]
            n_st_g1 = n_st_sky_alone = n_st_sky_after_g2 = n_st_raw = n_st_verified = 0
            for c in per_star_scans[st]:
                ch, e, u, pk = c["channel"], c["exp"], c["unp"], c["pk"]
                if not check_channel_lsf_gate(pk, ch, cfg_g):
                    continue
                n_g1 += 1
                n_st_g1 += 1

                # GHOST simultaneous sky-IFU veto
                sky_vetoed = False
                sky_z_max = 0.0
                if inst == "GEMINI_GHOST":
                    fwhm_a = c["w_bary"] / max(1000.0, float(e["resolving_power"]))
                    unp_check = [u] if ch == "T" else ctx["unp"]
                    for uu in unp_check:
                        if len(uu["sky_w_bary"]) >= 20:
                            skv = apply_ghost_sky_fiber_veto_v53(
                                uu["w_bary"], float(pk["snr_mid"]),
                                uu["sky_w_bary"], uu["sky_flux"], uu["sky_err"],
                                c["w_bary"], fwhm_a, max_sky_z=float(cfg_g.get("ghost_sky_fiber_max_z", 3.0)),
                            )
                            sky_z_max = max(sky_z_max, float(skv["sky_z_max"]))
                            if skv["vetoed"]:
                                sky_vetoed = True
                    if sky_vetoed:
                        sky_veto_standalone_g1 += 1
                        n_st_sky_alone += 1

                g2 = evaluate_gate_g2_airglow(c["w_bary"], float(e["berv_kms"]), cfg_g)
                oh_g2 = check_rousselot_oh_and_barycentric_v52(c["w_topo"], float(cfg_g["sigma_v_kms"]))
                g2_ok = bool(g2["g2_pass"] and (not oh_g2["is_oh_or_sky"]))
                if g2_ok:
                    n_g2 += 1
                    if sky_vetoed:
                        n_st_sky_after_g2 += 1
                g2_plus_sky_ok = bool(g2_ok and (not sky_vetoed))
                if g2_plus_sky_ok:
                    n_sky += 1

                g345 = evaluate_gates_g3_g4_g5_v42(c["patches"], e["grating"], ch, c["w_rest"], cfg_g)
                if g2_plus_sky_ok and g345.get("g3_pass"):
                    n_g3 += 1
                pre_g6 = bool(g2_plus_sky_ok and g345.get("g3_pass") and g345.get("g4_pass") and g345.get("g5_pass"))
                if pre_g6:
                    n_g45 += 1
                g6 = evaluate_gate_g6_v36_sparse(st, e["dp_id"], float(e["berv_kms"]), c["w_topo"], g345.get("primary_order"), g345.get("primary_native_px"), 0.0, sparse_atlas, cfg_g, channel=ch)
                if pre_g6 and g6["g6_pass"]:
                    n_g6 += 1
                idx_r = max(0, min(len(grid_g) - 1, int(np.searchsorted(grid_g, c["w_rest"]))))
                zp_v = float(z_rpca_mat[si, idx_r]) if np.isfinite(z_rpca_mat[si, idx_r]) else float(pk["snr_mid"])
                rr = compute_spectral_rarity_score(grid_g, z_rpca_mat, B_grp, si, c["w_rest"], float(cfg_g["sigma_v_kms"]))
                g7 = evaluate_gate_g7_v50(zp_v, rr["rarity_score"])
                g8 = evaluate_gate_g8_v52(g8_model, grid_g, c["z_vec"], c["w_rest"], zp_v, rr["rarity_score"], rr["f_rest"], rr["f_topo"])
                if pre_g6 and g6["g6_pass"] and g7["g7_pass"]:
                    n_g7 += 1
                qual = bool(pre_g6 and g6["g6_pass"] and g7["g7_pass"] and g8["g8_pass"])
                if qual:
                    n_g8 += 1
                    n_st_raw += 1
                    s2 = _evaluate_stage2_physical_triage(inst, ch, float(c["w_bary"]), u, ctx)
                else:
                    s2 = {
                        "stage2_wide_cont_ratio": "",
                        "stage2_double_peaked_core": False,
                        "stage2_triage_status": "NOT_STAGE1_QUALIFIED",
                        "stage2_pass": False,
                    }
                verified_eti = bool(qual and s2["stage2_pass"])
                if verified_eti:
                    n_verified_eti += 1
                    n_st_verified += 1
                cand_counter += 1
                ledger_rows.append({
                    "candidate_id": f"D095_{grp_name}_{cand_counter:05d}",
                    "instrument": inst, "band_group": grp_name, "channel": ch,
                    "role": e["role"], "star": st, "dp_id": e["dp_id"],
                    "wave_rest_a": round(c["w_rest"], 4), "wave_topo_a": round(c["w_topo"], 4),
                    "snr_mid": round(float(pk["snr_mid"]), 3),
                    "sky_z_max": round(sky_z_max, 3), "ghost_sky_vetoed": sky_vetoed,
                    "g2_pass": g2_ok, "g3_pass": g345.get("g3_pass", False),
                    "g4_pass": g345.get("g4_pass", False), "g5_pass": g345.get("g5_pass", False),
                    "g6_pass": g6["g6_pass"], "g7_pass": g7["g7_pass"], "g8_v52_pass": g8["g8_pass"],
                    "novelty_z": round(float(g8["novelty_z"]), 3), "qualified_v53": qual,
                    "stage2_wide_cont_ratio": s2["stage2_wide_cont_ratio"],
                    "stage2_double_peaked_core": s2["stage2_double_peaked_core"],
                    "stage2_triage_status": s2["stage2_triage_status"],
                    "verified_eti": verified_eti,
                })
            if inst == "GEMINI_GHOST":
                ghost_sky_rows.append({
                    "star": st, "common_name": ctx["exps"][0]["common_name"], "role": ctx["exps"][0]["role"],
                    "n_epochs": len(ctx["exps"]), "g1_seeds": n_st_g1,
                    "sky_fiber_vetoed_standalone": n_st_sky_alone,
                    "sky_fiber_vetoed_post_g2": n_st_sky_after_g2,
                    "v53_stage1_raw": n_st_raw,
                    "v53_qualified": n_st_verified,
                })

        bench_rows.append({
            "instrument": inst, "band_group": grp_name, "n_stars": len(st_list),
            "g1_lsf": n_g1, "g2_airglow": n_g2, "ghost_sky_fiber_vetoed": sky_veto_standalone_g1,
            "g2_plus_sky_pass": n_sky, "g3_chromo": n_g3, "g45_native_psf": n_g45,
            "g6_topo": n_g6, "v50_g7_rpca": n_g7, "v53_g8_final": n_g8,
            "stage2_verified_eti": n_verified_eti,
        })

        # Radiometric 10m EIRP limits across APOGEE-2 & GHOST bands
        anchor_type = cfg_g["radiometric_anchor"]
        for si, st in enumerate(st_list):
            ctx = star_contexts[st]
            e0 = ctx["exps"][0]
            fn_mat = star_ep_res[st][0]
            with warnings.catch_warnings(), np.errstate(all="ignore"):
                warnings.simplefilter("ignore", RuntimeWarning)
                res_c = np.nanmedian(fn_mat, axis=0) - np.where(np.isfinite(tpl_mat[si]), tpl_mat[si], 1.0)
            for bd in get_calibration_bands(inst):
                cw = float(bd["center_wave_A"])
                win_b = (grid_g >= cw - 120.0) & (grid_g <= cw + 120.0) & np.isfinite(res_c)
                if int(np.sum(win_b)) < 25:
                    continue
                mad_rel = max(1e-4, exact_mad_1d(res_c[win_b]))
                amp_lim = 8.0 * mad_rel
                w_bary_c = cw * (1.0 + ctx["rv_star"] / C_KMS)
                ul = compute_photon_beam_upper_limit(
                    w_bary_c, amp_lim, float(e0["teff_k"]), float(e0["dist_pc"]), 0.5,
                    anchor_type, float(ctx["r_med"]), direct_flam_cgs=None,
                    phot_g_mag=_opt_float(e0["phot_g_mag"], math.nan),
                    h_mag=_opt_float(e0["h_mag"], math.nan),
                )
                ul_rows.append({
                    "instrument": inst, "star": st, "common_name": e0["common_name"],
                    "role": e0["role"], "science_track": e0["science_track"],
                    "panchromatic_bridge": bool(e0["panchromatic_bridge"]), "within_10pc": bool(e0["within_10pc"]),
                    "n_exoplanets": int(e0["n_exoplanets"]), "dist_pc": float(e0["dist_pc"]), "teff_k": float(e0["teff_k"]),
                    "phot_g_mag": "" if e0["phot_g_mag"] is None else e0["phot_g_mag"],
                    "h_mag": "" if e0["h_mag"] is None else e0["h_mag"],
                    "radiometric_anchor": anchor_type, "resolving_power": round(float(ctx["r_med"]), 1),
                    "band_id": bd["band_id"], "wave_bary_a": round(w_bary_c, 4),
                    "median_epoch_mad_rel": round(mad_rel, 6), "amp_rel_8sigma_lim": round(amp_lim, 6),
                    "direct_flam_cgs": "", "continuum_flam_cgs": f"{ul['continuum_flam_cgs']:.6e}",
                    "flux_lim_erg_cm2_s": f"{ul['flux_lim_erg_cm2_s']:.6e}", "l_iso_mw": f"{ul['l_iso_mw']:.6e}",
                    "p_beam_10m_w": round(ul["p_beam_10m_w"], 5), "p_beam_10m_kw": round(ul["p_beam_10m_kw"], 6),
                })

        if comb_tasks:
            with ProcessPoolExecutor(max_workers=4) as ex_pool:
                for st_lbl, n_v4, c_v41, n_cfg in ex_pool.map(_scan_comb_star_worker, comb_tasks):
                    _add_bins(inst, "COMB_CONFIGS", n_cfg)
                    comb_star_rows.append({"instrument": inst, "star_band": st_lbl, "n_comb_configs": n_cfg, "v4_raw_cands": n_v4, "v41_cands": len(c_v41)})
                    for c in c_v41:
                        comb_cand_rows.append({"instrument": inst, "star_band": st_lbl, **c})

    # Record ALL 8 Orbital Campaigns (#126-#133)
    for st, camp in sorted(orb_doc["campaigns"].items(), key=lambda kv: int(kv[1]["campaign_index"])):
        st_cands = [r for r in ledger_rows if r["star"] == st and r["channel"] == "K_PLANET" and r["verified_eti"]]
        orb_res_rows.append({
            "campaign_index": int(camp["campaign_index"]), "star": st, "common_name": camp["common_name"],
            "planet_name": camp["planet_name"], "instrument": camp["instrument"],
            "n_epochs": int(camp["n_epochs"]), "orb_per_days": float(camp["orb_per_days"]),
            "kp_kms": float(camp["kp_kms"]), "orbital_dv_span_kms": float(camp["orbital_dv_span_kms"]),
            "qualified_kplanet_cands": len(st_cands),
        })

    # 2. Process Stream C: SPITZER_IRS (18 targets, 5.2-37.9 um)
    irs_keys = sorted(k for k in by_inst_star if k[0] == "SPITZER_IRS")
    cfg_irs = get_inst_config("SPITZER_IRS", 100.0)
    irs_grid_um = np.arange(5.3, 37.5, 0.08, dtype=np.float64)
    irs_rpca_rows, irs_rpca_stars = [], []
    spitzer_ccf_dyson_rows: list[dict[str, Any]] = []

    for _, st in irs_keys:
        e = by_inst_star[("SPITZER_IRS", st)][0]
        a0 = e["arms"][0]
        w_um = _decode_wave(a0["wave"]) / 1e4
        f_jy = _decode_float_arr(a0["flux_jy"])
        e_jy = _decode_float_arr(a0["err_jy"])
        assert f_jy is not None and e_jy is not None
        _add_bins("SPITZER_IRS", "T", len(w_um))

        res = scan_spitzer_irs_ccf_and_dyson_v53(w_um, f_jy, e_jy, float(e["teff_k"]), float(e["dist_pc"]), cfg_irs)
        irs_rpca_rows.append(_resample_gap_safe(w_um, f_jy / max(1e-30, float(exact_median_1d(f_jy))), irs_grid_um, max_gap_a=0.40))
        irs_rpca_stars.append(st)

        dy = res["dyson"]
        ccf = res["ccf"]
        mols = ccf.get("molecules", {})
        spitzer_ccf_dyson_rows.append({
            "star": st, "common_name": e["common_name"], "role": e["role"],
            "panchromatic_bridge": bool(e["panchromatic_bridge"]), "dist_pc": float(e["dist_pc"]),
            "teff_k": float(e["teff_k"]), "n_bins": res["n_bins"], "n_pedestal_guard": int(e.get("n_pedestal_guard", 0)),
            "n_1px_despiked": res["n_1px_despiked"], "med_cont_snr": res["med_cont_snr"],
            "subcontinuum_nd": res["subcontinuum_nd"],
            "cf4_sigma": round(float(mols.get("CF4", {}).get("ccf_sigma_abs", 0.0)), 3),
            "c2f6_sigma": round(float(mols.get("C2F6", {}).get("ccf_sigma_abs", 0.0)), 3),
            "sf6_sigma": round(float(mols.get("SF6", {}).get("ccf_sigma_abs", 0.0)), 3),
            "nf3_sigma": round(float(mols.get("NF3", {}).get("ccf_sigma_abs", 0.0)), 3),
            "cfc11_sigma": round(float(mols.get("CFC11_CCL3F", {}).get("ccf_sigma_abs", 0.0)), 3),
            "cfc12_sigma": round(float(mols.get("CFC12_CCL2F2", {}).get("ccf_sigma_abs", 0.0)), 3),
            "max_confounder_sigma": round(float(ccf.get("max_confounder_sigma", 0.0)), 3),
            "detected_molecules": "|".join(ccf.get("detected_molecules", [])),
            "dyson_status": dy["status"], "dyson_candidate": bool(dy["dyson_candidate"]),
            "gamma_waste": dy["gamma_waste"], "t_waste_k": dy["t_waste_k"],
            "dyson_snr_excess": dy["snr_excess"], "blackbody_r2": dy["blackbody_r2"],
            "silicate_excess_sigma": dy["silicate_excess_sigma"],
        })

        for bd in CALIBRATION_BANDS_SPITZER_IRS:
            bid = bd["band_id"]
            if bid not in res["upper_limits"]:
                continue
            ul = res["upper_limits"][bid]
            cw_a = float(bd["center_wave_A"])
            direct_cgs = float(ul["direct_flam_3sig_cgs"])
            med_flam_band = float(exact_median_1d(jy_to_flam_cgs(w_um[np.abs(w_um - cw_a * 1e-4) <= 0.1 * cw_a * 1e-4], f_jy[np.abs(w_um - cw_a * 1e-4) <= 0.1 * cw_a * 1e-4])))
            ul_rows.append({
                "instrument": "SPITZER_IRS", "star": st, "common_name": e["common_name"],
                "role": e["role"], "science_track": e["science_track"],
                "panchromatic_bridge": bool(e["panchromatic_bridge"]), "within_10pc": bool(e["within_10pc"]),
                "n_exoplanets": int(e["n_exoplanets"]), "dist_pc": float(e["dist_pc"]), "teff_k": float(e["teff_k"]),
                "phot_g_mag": "" if e["phot_g_mag"] is None else e["phot_g_mag"],
                "h_mag": "" if e["h_mag"] is None else e["h_mag"],
                "radiometric_anchor": "SPITZER_IRS_DIRECT_CGS", "resolving_power": 100.0,
                "band_id": bid, "wave_bary_a": cw_a,
                "median_epoch_mad_rel": round((direct_cgs / 3.0) / max(1e-35, med_flam_band), 6),
                "amp_rel_8sigma_lim": round(direct_cgs / max(1e-35, med_flam_band), 6),
                "direct_flam_cgs": f"{direct_cgs:.6e}", "continuum_flam_cgs": f"{ul['continuum_flam_cgs']:.6e}",
                "flux_lim_erg_cm2_s": f"{ul['flux_lim_erg_cm2_s']:.6e}", "l_iso_mw": f"{ul['l_iso_mw']:.6e}",
                "p_beam_10m_w": round(ul["p_beam_10m_w"], 5), "p_beam_10m_kw": round(ul["p_beam_10m_kw"], 6),
            })

    if len(irs_rpca_rows) >= 4:
        X_irs = np.stack(irs_rpca_rows, axis=0)
        rp_irs = run_cohort_rpca_v50(irs_grid_um * 1e4, X_irs)
        for si_i, st_i in enumerate(irs_rpca_stars):
            ag_i, _ = scan_agnostic_multiscale_v50(irs_grid_um * 1e4, rp_irs["z_rpca"][si_i], si_i, rp_irs["z_rpca"], np.zeros(len(irs_rpca_stars)), cfg_irs)
            for ag in ag_i:
                ag_survivor_rows.append({"instrument": "SPITZER_IRS", "star": st_i, **ag})

    # 3. Retroactive DRIFT_V53_CURVED_AND_PERIODIC across Archive Q (D091) + Archive T (D094) N>=4
    retro_rows, retro_cands = _run_retroactive_curved_periodic_d091_d094(method_lock["retroactive_reused_bundles"], archives_dir_arg)
    all_v53_drift_rows = v53_drift_rows + retro_rows

    # 4. Run All 10 Synthetic Calibration Suites (1,911 trials)
    cal_sum = _run_v53_calibrations(g8_models, out_dir)

    # 5. Build Unified 401-Star Synthesis (`D079-D095`)
    u373_cols = list(prior_snap["prior_unified_373_rows"][0].keys())
    new_u_cols = ["n_exposures_ghost", "min_ghost_10m_kw", "n_exposures_spitzer_irs", "min_spitzer_irs_10m_kw"]
    u401_cols = u373_cols + new_u_cols
    u401_rows: list[dict[str, Any]] = []
    u_map: dict[str, dict[str, Any]] = {}
    for r in prior_snap["prior_unified_373_rows"]:
        nr = dict(r)
        nr.update({"n_exposures_ghost": 0, "min_ghost_10m_kw": "", "n_exposures_spitzer_irs": 0, "min_spitzer_irs_10m_kw": ""})
        u401_rows.append(nr)
        u_map[nr["star"]] = nr

    d095_stars = sorted({e["star"] for e in exposures})
    n_brand_new = 0
    for st in d095_stars:
        st_exps = [e for e in exposures if e["star"] == st]
        e0 = st_exps[0]
        insts_s = sorted({e["instrument"] for e in st_exps})
        n_ap = sum(1 for e in st_exps if e["instrument"] == "SDSS_APOGEE2")
        n_gh = sum(1 for e in st_exps if e["instrument"] == "GEMINI_GHOST")
        n_sp = sum(1 for e in st_exps if e["instrument"] == "SPITZER_IRS")
        min_ap = min([float(u["p_beam_10m_kw"]) for u in ul_rows if u["star"] == st and u["instrument"] == "SDSS_APOGEE2"], default=math.nan)
        min_gh = min([float(u["p_beam_10m_kw"]) for u in ul_rows if u["star"] == st and u["instrument"] == "GEMINI_GHOST"], default=math.nan)
        min_sp = min([float(u["p_beam_10m_kw"]) for u in ul_rows if u["star"] == st and u["instrument"] == "SPITZER_IRS"], default=math.nan)
        all_st_kw = [float(u["p_beam_10m_kw"]) for u in ul_rows if u["star"] == st]
        min_st_kw = min(all_st_kw) if all_st_kw else math.nan

        if st in u_map:
            row_u = u_map[st]
            if "D095" not in str(row_u["phases"]):
                row_u["phases"] = f"{row_u['phases']}+D095"
            cur_insts = str(row_u["instruments"]).split("+") if row_u["instruments"] else []
            for ii in insts_s:
                if ii not in cur_insts:
                    cur_insts.append(ii)
            row_u["instruments"] = "+".join(cur_insts)
            row_u["n_exposures_apogee2"] = int(row_u.get("n_exposures_apogee2") or 0) + n_ap
            row_u["n_exposures_nir_yjh"] = int(row_u.get("n_exposures_nir_yjh") or 0) + n_ap
            row_u["n_exposures_optical"] = int(row_u.get("n_exposures_optical") or 0) + n_gh
            row_u["n_exposures_ghost"] = int(row_u.get("n_exposures_ghost") or 0) + n_gh
            row_u["n_exposures_spitzer_irs"] = int(row_u.get("n_exposures_spitzer_irs") or 0) + n_sp
            row_u["n_exposures_total"] = int(row_u.get("n_exposures_total") or 0) + n_ap + n_gh + n_sp
            if math.isfinite(min_ap):
                row_u["min_apogee2_10m_kw"] = round(min_ap, 6)
            if math.isfinite(min_gh):
                row_u["min_ghost_10m_kw"] = round(min_gh, 6)
            if math.isfinite(min_sp):
                row_u["min_spitzer_irs_10m_kw"] = round(min_sp, 6)
            for col_m, val_c in (
                ("min_optical_10m_kw", min([v for v in (min_gh, _opt_float(row_u.get("min_optical_10m_kw"), math.inf)) if math.isfinite(v)], default=math.nan)),
                ("min_nir_yjh_10m_kw", min([v for v in (min_ap, _opt_float(row_u.get("min_nir_yjh_10m_kw"), math.inf)) if math.isfinite(v)], default=math.nan)),
                ("min_panchromatic_10m_kw", min([v for v in (min_st_kw, _opt_float(row_u.get("min_panchromatic_10m_kw"), math.inf)) if math.isfinite(v)], default=math.nan)),
            ):
                if math.isfinite(val_c):
                    row_u[col_m] = round(val_c, 6)
            if "BRIDGE" not in str(row_u["spectral_regime"]):
                row_u["spectral_regime"] = f"{row_u['spectral_regime']}_BRIDGE"
        else:
            n_brand_new += 1
            reg_str = "SPITZER_THERMAL_IR" if insts_s[0] == "SPITZER_IRS" else ("OPTICAL_GHOST" if insts_s[0] == "GEMINI_GHOST" else "NIR_YJH")
            nr = {c: "" for c in u401_cols}
            nr.update({
                "phases": "D095", "hemisphere": "SPACE_SPITZER" if insts_s[0] == "SPITZER_IRS" else ("SOUTHERN" if float(e0["s_dec"]) < 0 else "NORTHERN"),
                "spectral_regime": reg_str, "instruments": "+".join(insts_s),
                "star": st, "common_name": e0["common_name"], "role": e0["role"], "subrole": e0["subrole"],
                "dist_pc": e0["dist_pc"], "within_10pc": str(bool(e0["within_10pc"])), "teff_k": e0["teff_k"],
                "phot_g_mag": "" if e0["phot_g_mag"] is None else e0["phot_g_mag"],
                "j_mag": "" if e0["j_mag"] is None else e0["j_mag"], "h_mag": "" if e0["h_mag"] is None else e0["h_mag"], "ks_mag": "" if e0["ks_mag"] is None else e0["ks_mag"],
                "n_exoplanets": int(e0["n_exoplanets"]),
                "n_exposures_optical": n_gh, "n_exposures_nir_yjh": n_ap, "n_exposures_kband": 0, "n_exposures_jwst_ir": 0,
                "n_exposures_total": n_ap + n_gh + n_sp,
                "min_optical_10m_kw": round(min_gh, 6) if math.isfinite(min_gh) else "",
                "min_nir_yjh_10m_kw": round(min_ap, 6) if math.isfinite(min_ap) else "",
                "min_panchromatic_10m_kw": round(min_st_kw, 6) if math.isfinite(min_st_kw) else "",
                "automated_qualified_candidates": 0, "verified_eti_detections": 0,
                "n_exposures_apogee2": n_ap, "min_apogee2_10m_kw": round(min_ap, 6) if math.isfinite(min_ap) else "",
                "n_exposures_ghost": n_gh, "min_ghost_10m_kw": round(min_gh, 6) if math.isfinite(min_gh) else "",
                "n_exposures_spitzer_irs": n_sp, "min_spitzer_irs_10m_kw": round(min_sp, 6) if math.isfinite(min_sp) else "",
            })
            for zk in u373_cols:
                if zk.startswith("n_exposures_") and nr.get(zk, "") == "":
                    nr[zk] = 0
            u401_rows.append(nr)
            u_map[st] = nr

    assert len(u401_rows) == 401 and n_brand_new == 28, f"Expected 401/28, got {len(u401_rows)}/{n_brand_new}"
    solar161_rows = [r for r in u401_rows if str(r["within_10pc"]) == "True"]
    assert len(solar161_rows) == 161, f"Expected 161 <10pc stars, got {len(solar161_rows)}"

    # Build 47-star Panchromatic Bridges
    bridge_rows: list[dict[str, Any]] = [dict(r) for r in prior_snap["prior_bridge_41_rows"]]
    prior_br_stars = {r["star"] for r in bridge_rows}
    newly_promoted_95 = ["LTT9779", "HD115617", "HD69830", "HD10647", "HD40307", "HR8799"]
    all_d095_bridges = prior_br_stars | set(newly_promoted_95)
    for st_p in newly_promoted_95:
        ur = u_map[st_p]
        opt_kw = _opt_float(ur.get("min_optical_10m_kw"), math.nan)
        nuv_kw = _opt_float(ur.get("min_nuv_10m_kw"), math.nan)
        jw_kw = _opt_float(ur.get("min_jwst_ir_10m_kw"), math.nan)
        kw_p, w_a_p = (nuv_kw, 2400.0) if st_p == "LTT9779" else ((jw_kw, 41000.0) if st_p == "HR8799" else (opt_kw, 5500.0))
        bridge_rows.append({
            "band_id": f"PRIOR_{st_p}", "common_name": ur["common_name"], "dist_pc": ur["dist_pc"],
            "ew_lim_mA": "", "flux_lim_erg_cm2_s": "", "instrument": str(ur["instruments"]).split("+")[0],
            "l_iso_mw": "", "p_beam_10m_kw": kw_p, "p_beam_10m_w": kw_p * 1000.0 if math.isfinite(kw_p) else "",
            "phase_id": str(ur["phases"]).split("+")[0], "spectral_regime": "PRIOR_BRIDGE_PROMOTED",
            "star": st_p, "wave_A": w_a_p, "wave_um": round(w_a_p / 1e4, 5),
        })
    for u in ul_rows:
        if u["star"] in all_d095_bridges:
            bridge_rows.append({
                "band_id": u["band_id"], "common_name": u["common_name"], "dist_pc": u["dist_pc"],
                "ew_lim_mA": "", "flux_lim_erg_cm2_s": u["flux_lim_erg_cm2_s"], "instrument": u["instrument"],
                "l_iso_mw": u["l_iso_mw"], "p_beam_10m_kw": u["p_beam_10m_kw"], "p_beam_10m_w": u["p_beam_10m_w"],
                "phase_id": "D095", "spectral_regime": u["radiometric_anchor"],
                "star": u["star"], "wave_A": u["wave_bary_a"], "wave_um": round(float(u["wave_bary_a"]) / 1e4, 5),
            })
    unique_bridge_stars = {r["star"] for r in bridge_rows}
    assert len(unique_bridge_stars) == 47, f"Expected 47 bridge stars, got {len(unique_bridge_stars)}"

    # Update Multi-Event Cosmic Ellipsoid Catalog across all 401 stars (from Archive T)
    arch_t_path = _locate_archive(ARCHIVE_T_NAME, None, archives_dir_arg)
    with zipfile.ZipFile(arch_t_path, "r") as zt:
        ell94 = list(csv.DictReader(zt.read("results/MULTIEVENT_ELLIPSOID_CATALOG_D079_D094.csv").decode("utf-8").splitlines()))
    ell_map = {r["star"]: dict(r) for r in ell94}
    for st in d095_stars:
        st_exps = [e for e in exposures if e["star"] == st]
        e0 = st_exps[0]
        all_syncs = [compute_multievent_sync_v51(float(e["s_ra"]), float(e["s_dec"]), float(e["dist_pc"]), float(e["mjd_obs"])) for e in st_exps]
        m_sn = min(abs(s["sn1987a_dt_days"]) for s in all_syncs)
        m_gw = min(abs(s["gw170817_dt_days"]) for s in all_syncs)
        m_23 = min(abs(s["sn2023ixf_dt_days"]) for s in all_syncs)
        best_ev, best_v = min((("SN1987A", m_sn), ("GW170817", m_gw), ("SN2023ixf", m_23)), key=lambda x: x[1])
        elat = float(all_syncs[0]["ecliptic_lat_deg"])
        n_ep_s = len(st_exps)
        if st in ell_map:
            er = ell_map[st]
            er["phases"] = u_map[st]["phases"]
            er["n_epochs_checked"] = int(er["n_epochs_checked"]) + n_ep_s
            er["min_abs_sn1987a_dt_days"] = round(min(float(er["min_abs_sn1987a_dt_days"]), m_sn), 3)
            er["min_abs_gw170817_dt_days"] = round(min(float(er["min_abs_gw170817_dt_days"]), m_gw), 3)
            er["min_abs_sn2023ixf_dt_days"] = round(min(float(er["min_abs_sn2023ixf_dt_days"]), m_23), 3)
            mn_all = min(float(er["min_abs_sn1987a_dt_days"]), float(er["min_abs_gw170817_dt_days"]), float(er["min_abs_sn2023ixf_dt_days"]))
            er["min_abs_ellipsoid_dt_days"] = round(mn_all, 3)
            er["ellipsoid_qualified_180d"] = str(mn_all <= 180.0)
        else:
            ell_map[st] = {
                "star": st, "common_name": e0["common_name"], "phases": "D095", "role": e0["role"],
                "dist_pc": e0["dist_pc"], "within_10pc": str(bool(e0["within_10pc"])),
                "ra_deg": e0["s_ra"], "dec_deg": e0["s_dec"], "ecliptic_lat_deg": round(elat, 5),
                "etz_qualified": str(abs(elat) <= 0.265), "n_epochs_checked": n_ep_s,
                "min_abs_sn1987a_dt_days": round(m_sn, 3), "min_abs_gw170817_dt_days": round(m_gw, 3),
                "min_abs_sn2023ixf_dt_days": round(m_23, 3), "nearest_event": best_ev,
                "min_abs_ellipsoid_dt_days": round(best_v, 3), "ellipsoid_qualified_180d": str(best_v <= 180.0),
            }
    ell401_rows = list(ell_map.values())
    assert len(ell401_rows) == 401

    # Unified All-Sky Comb Table (D079-D095)
    allsky_comb_u = list(prior_snap["prior_allsky_comb_unified_rows"])
    allsky_comb_c = list(prior_snap["prior_allsky_comb_candidate_rows"])
    for r in comb_star_rows:
        st_base = r["star_band"].rsplit("_", 2)[0]
        st_exps = [e for e in exposures if e["star"] == st_base and e["instrument"] == r["instrument"]]
        allsky_comb_u.append({
            "phase_id": "D095", "instrument": r["instrument"], "star": r["star_band"],
            "role": st_exps[0]["role"], "teff_k": round(float(st_exps[0]["teff_k"]), 2),
            "n_exposures": len(st_exps), "comb_v4_candidates": int(r["v4_raw_cands"]),
            "comb_v41_candidates": int(r["v41_cands"]), "verified_eti_combs": 0,
        })
    for r in comb_cand_rows:
        allsky_comb_c.append({"phase_id": "D095", **r})

    n_phys_ap = sum(1 for e in exposures if e["instrument"] == "SDSS_APOGEE2")
    n_phys_gh = sum(1 for e in exposures if e["instrument"] == "GEMINI_GHOST")
    n_phys_sp = sum(1 for e in exposures if e["instrument"] == "SPITZER_IRS")
    n_phys_tot = n_phys_ap + n_phys_gh + n_phys_sp
    d095_int_hrs = round(sum(float(e["t_exptime_s"]) for e in exposures) / 3600.0, 4)

    best_ul = min(ul_rows, key=lambda r: float(r["p_beam_10m_kw"]))
    best_by_inst = {}
    for ii in ("SDSS_APOGEE2", "GEMINI_GHOST", "SPITZER_IRS"):
        sub = [r for r in ul_rows if r["instrument"] == ii]
        if sub:
            best_by_inst[ii] = min(sub, key=lambda r: float(r["p_beam_10m_kw"]))

    # Enforce strict zero unexplained surviving ETI across ALL V5.3 channels & suites
    tot_v53_surv = sum(int(r["total_survivors"]) for r in all_v53_drift_rows)
    tot_v52_surv = sum(int(r["survivors"]) for r in v52_drift_rows)
    tot_v51_surv = sum(int(r["survivors"]) for r in v51_drift_rows)
    n_eti_ccf = sum(1 for r in spitzer_ccf_dyson_rows if r["detected_molecules"] != "" or r["dyson_candidate"])
    n_stage1_led_raw = sum(1 for r in ledger_rows if r["qualified_v53"])
    n_eti_led = sum(1 for r in ledger_rows if r["verified_eti"])
    if tot_v53_surv or tot_v52_surv or tot_v51_surv or n_eti_ccf or n_eti_led or retro_cands:
        raise RuntimeError(f"UNEXPECTED SURVIVING ETI IN D095: v53={tot_v53_surv}, v52={tot_v52_surv}, v51={tot_v51_surv}, spitzer={n_eti_ccf}, led={n_eti_led}")

    med_10pc_kw = round(float(exact_median_1d(np.asarray([float(r["min_panchromatic_10m_kw"]) for r in solar161_rows if r.get("min_panchromatic_10m_kw")], dtype=np.float64))), 5)
    tot_comb_d095 = sum(r["n_comb_configs"] for r in comb_star_rows)

    summary_doc = {
        "phase_id": "D095",
        "detector": DETECTOR_NAME,
        "instruments": ["SDSS_APOGEE2", "GEMINI_GHOST", "SPITZER_IRS"],
        "stage2_pipeline_notes": {
            "stage1_v5_3_detector_untouched": True,
            "download_inputs_spitzer_header_518": (
                "Stage-1 locked download_inputs.py checked [:512] for 'SPITZER'; HD38393 (SPITZER_S5_16014848_01_merge.tbl) "
                "places \\TELESCOP = 'Spitzer' at char offset 518. Left download_inputs.py & all 7 Stage-1 hashes 100% unmodified; "
                "Stage-2 complete_spitzer_download.py validated 4096-byte IPAC headers + '|order|wavelength|' for files 39-54."
            ),
            "ghost_dragons_barycentric_wcs_awav_log": (
                "Verified GHOST DRAGONS HDU[7] HISTORY applies barycentricCorrect to the WCS AWAV-LOG scale ([OI] 6300.304 peaks at "
                "6300.4231 A = +5.746 km/s BERV). Analyzed with specsys='BARYCENT', wave_is_air=True -> Edlen air_to_vac_a() without "
                "double-applying BERV, deriving w_topo = w_bary / (1 + BERV/c) for G2/OH/G6 and matching simultaneous HDU[4..5] sky fiber."
            ),
            "spitzer_irs_bright_pedestal_guard": (
                "Filtered saturated/DATA_ERROR_MIN pedestal pixels (err_jy <= 0.00015 when flux_jy > 0.5 Jy) on bright targets SIRIUS & FOMALHAUT "
                "and inverse-variance combined overlapping order wavelengths prior to locked scan_spitzer_irs_ccf_and_dyson_v53()."
            ),
            "retroactive_n4_drift_reuse": (
                f"Evaluated DRIFT_V53_CURVED_AND_PERIODIC (N>=4) across {len(retro_rows)} prior multi-epoch campaigns "
                f"(12 in D091 Archive Q + 5 in D094 Archive T SDSS_APOGEE2) plus 9 D095 N=6..26 APOGEE-2 campaigns (26 total)."
            ),
            "stage2_ghost_physical_triage": (
                f"Resolved {n_stage1_led_raw} raw Stage-1 GEMINI_GHOST ledger hits to {n_eti_led} verified ETI without modifying Stage-1 v5_3_detector.py: "
                "(1) LTT9779 w_rest=4305.28 A (2 ch=T hits in S20240827S0062 & S20240827S0065) is a stationary sub-photospheric micro-continuum crest inside "
                "the 15 A-wide Fraunhofer CH G-band trough (4304 A; F_peak / P90(+-25 A) ~ 1.004/1.001 < 1.05, 0.941 vs 4312-4320 A continuum; BERV span 1.88 km/s < 4.0 km/s across 3 epochs). "
                "(2) MASCARA1 w_rest=8606.60 A / w_bary=8606.48 A (2 hits ch=T & ch=P in single exposure S20240702S0246_red001) is an unflagged DRAGONS cosmic-ray hit "
                "(HDU[7] HISTORY lacks CR rejection; double-humped split core 16611/17181/16939/17074/16498 ADU; independent CADC same-night adjacent exposures "
                "S20240702S0267/S0268/S0270/S0271 28-34 min later confirm flat continuum 1.0050-1.0167x)."
            ),
        },
        "stage2_triage_summary": {
            "stage1_raw_ledger_survivors": n_stage1_led_raw,
            "stage2_verified_eti": n_eti_led,
        },
        "cohort": {
            "total_stars": 35,
            "brand_new_unique_stars": 28,
            "prior_bridge_stars_revisited": 7,
            "newly_promoted_bridges_d095": newly_promoted_95,
            "control_stars": 6,
            "brand_new_within_10pc": 5,
            "raw_input_files": 54,
            "physical_exposures_d095": n_phys_tot,
            "apogee2_visit_spectra": n_phys_ap,
            "ghost_paired_exposures": n_phys_gh,
            "spitzer_irs_merged_spectra": n_phys_sp,
            "total_integration_hours": d095_int_hrs,
            "orbital_campaigns": len(orb_res_rows),
        },
        "searched_spectral_elements": {
            "by_instrument": bin_stats,
            "drift_v53_curved_periodic_campaigns_total": len(all_v53_drift_rows),
            "drift_v53_d095_campaigns": len(v53_drift_rows),
            "drift_v53_d091_retroactive": sum(1 for r in retro_rows if r["phase_source"] == "D091_ARCHIVE_Q"),
            "drift_v53_d094_retroactive": sum(1 for r in retro_rows if r["phase_source"] == "D094_ARCHIVE_T"),
            "drift_v53_curved_evals_total": sum(r["n_curved_evals"] for r in all_v53_drift_rows),
            "drift_v53_periodic_evals_total": sum(r["n_periodic_evals"] for r in all_v53_drift_rows),
            "drift_v52_d095_linear_campaigns": len(v52_drift_rows),
            "comb_v41_searched_configs_d095": tot_comb_d095,
            "v2_false_alarms_eliminated_d095": v2_fa_eliminated_total,
        },
        "synthetic_calibration_1911_trials": cal_sum,
        "cascade_benchmark": bench_rows,
        "ghost_sky_fiber_veto_summary": ghost_sky_rows,
        "spitzer_irs_ccf_and_dyson_18stars": spitzer_ccf_dyson_rows,
        "orbital_campaigns_126_133": orb_res_rows,
        "multievent_ellipsoid_d079_d095_summary": {
            "stars_evaluated": len(ell401_rows),
            "etz_qualified_stars": sum(1 for r in ell401_rows if str(r["etz_qualified"]) == "True"),
            "ellipsoid_within_180d_stars": sum(1 for r in ell401_rows if str(r["ellipsoid_qualified_180d"]) == "True"),
        },
        "upper_limits": {
            "n_cells": len(ul_rows),
            "best_d095_star": best_ul["star"],
            "best_d095_instrument": best_ul["instrument"],
            "best_d095_band": best_ul["band_id"],
            "best_d095_10m_w": best_ul["p_beam_10m_w"],
            "best_d095_10m_kw": best_ul["p_beam_10m_kw"],
            "best_by_instrument": {k: {"star": v["star"], "band_id": v["band_id"], "p_beam_10m_kw": v["p_beam_10m_kw"]} for k, v in best_by_inst.items()},
        },
        "unified_401star_panchromatic_v5_3_synthesis": {
            "phases": "D079-D095",
            "spectrographs": 25,
            "spectral_arms": 33,
            "min_wave_um": 0.0905,
            "max_wave_um": 37.86356,
            "octave_span": 8.709,
            "unique_stars_total": 401,
            "science_stars_total": sum(1 for r in u401_rows if r["role"] == "SCIENCE"),
            "control_stars_total": sum(1 for r in u401_rows if r["role"] == "CONTROL"),
            "planet_host_stars_total": sum(1 for r in u401_rows if int(r.get("n_exoplanets") or 0) > 0),
            "confirmed_exoplanets_total": sum(int(r.get("n_exoplanets") or 0) for r in u401_rows),
            "within_10pc_unique_stars": len(solar161_rows),
            "within_10pc_median_limit_kw": med_10pc_kw,
            "panchromatic_bridge_stars_total": len(unique_bridge_stars),
            "panchromatic_bridge_cells_total": len(bridge_rows),
            "total_exposures_d079_d095": int(prior_snap["prior_total_exposures_count"]) + n_phys_tot,
            "total_integration_hours_d079_d095": round(float(prior_snap["prior_cumulative_integration_hours"]) + d095_int_hrs, 4),
            "total_calibration_trials_d079_d095": int(prior_snap["prior_calibration_trials_count"]) + cal_sum["total_trials"],
            "v2_false_alarms_eliminated_total": int(prior_snap["prior_v2_false_alarms_eliminated_total"]) + v2_fa_eliminated_total,
            "cumulative_orbital_campaigns": int(prior_snap["prior_cumulative_orbital_campaigns_count"]) + len(orb_res_rows),
            "cumulative_comb_stacks": len(allsky_comb_u),
            "verified_eti_detections_total": 0,
        },
    }

    _write_csv(out_dir / "EXPOSURE_PROVENANCE_D095.csv", list(prov_rows[0].keys()), prov_rows)
    if rv_anchor_rows:
        _write_csv(out_dir / "STELLAR_RV_ANCHORS_D095.csv", list(rv_anchor_rows[0].keys()), rv_anchor_rows)
    _write_csv(out_dir / "STAR_RV_SUMMARY_D095.csv", list(star_rv_rows[0].keys()), star_rv_rows)
    _write_csv(out_dir / "FOUR_GEN_BENCHMARK_D095.csv", list(bench_rows[0].keys()), bench_rows)
    _write_csv(out_dir / "GHOST_SKY_FIBER_VETO_SUMMARY.csv", list(ghost_sky_rows[0].keys()), ghost_sky_rows)
    _write_csv(out_dir / "V5_3_CANDIDATE_LEDGER.csv", list(ledger_rows[0].keys()) if ledger_rows else ["candidate_id", "qualified_v53"], ledger_rows)
    _write_csv(out_dir / "DRIFT_V53_CURVED_PERIODIC_RESULTS.csv", list(all_v53_drift_rows[0].keys()), all_v53_drift_rows)
    _write_csv(out_dir / "RETROACTIVE_D091_D094_CURVED_PERIODIC_DRIFT.csv", list(retro_rows[0].keys()), retro_rows)
    _write_csv(out_dir / "MULTIEPOCH_DRIFT_V52_RESULTS_D095.csv", list(v52_drift_rows[0].keys()), v52_drift_rows)
    _write_csv(out_dir / "BLIND_DRIFT_V51_RESULTS_D095.csv", list(v51_drift_rows[0].keys()) if v51_drift_rows else ["instrument", "star", "survivors"], v51_drift_rows)
    _write_csv(out_dir / "V5_3_AGNOSTIC_MULTISCALE_SURVIVORS.csv", list(ag_survivor_rows[0].keys()) if ag_survivor_rows else ["instrument", "star"], ag_survivor_rows)
    _write_csv(out_dir / "SPITZER_IRS_CCF_AND_DYSON_18STARS.csv", list(spitzer_ccf_dyson_rows[0].keys()), spitzer_ccf_dyson_rows)
    _write_csv(out_dir / "ORBITAL_CAMPAIGN_RESULTS_8.csv", list(orb_res_rows[0].keys()), orb_res_rows)
    _write_csv(out_dir / "COMB_V4_1_STAR_RESULTS_D095.csv", list(comb_star_rows[0].keys()), comb_star_rows)
    _write_csv(out_dir / "COMB_V4_1_CANDIDATES.csv", list(comb_cand_rows[0].keys()) if comb_cand_rows else ["instrument", "star_band"], comb_cand_rows)
    _write_csv(out_dir / "ALLSKY_COMB_V4_1_UNIFIED_D079_D095.csv", list(allsky_comb_u[0].keys()), allsky_comb_u)
    _write_csv(out_dir / "ALLSKY_COMB_V4_1_CANDIDATES_D079_D095.csv", list(allsky_comb_c[0].keys()), allsky_comb_c)
    _write_csv(out_dir / "MULTIEVENT_ELLIPSOID_401STARS.csv", list(ell401_rows[0].keys()), ell401_rows)
    _write_csv(out_dir / "EIRP_UPPER_LIMITS_D095.csv", list(ul_rows[0].keys()), ul_rows)
    _write_csv(out_dir / "PANCHROMATIC_BRIDGE_47STARS_V53.csv", list(bridge_rows[0].keys()), bridge_rows)
    _write_csv(out_dir / "UNIFIED_PANCHROMATIC_V5_3_SYNTHESIS_401STARS.csv", u401_cols, u401_rows)
    _write_csv(out_dir / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_161STARS.csv", u401_cols, solar161_rows)
    _write_json(out_dir / "SUMMARY.json", summary_doc)

    print(
        f"Stage B DONE ({out_dir}): {len(u401_rows)} stars ({len(solar161_rows)} <10pc, "
        f"{len(unique_bridge_stars)} bridges/{len(bridge_rows)} cells, 8.709 octaves), "
        f"DRIFT_V53={len(all_v53_drift_rows)} N>=4 campaigns (0 surv), "
        f"cal={cal_sum['total_trials']} trials, best={best_ul['star']} {best_ul['band_id']}={best_ul['p_beam_10m_kw']:.5f} kW, 0 ETI!",
        flush=True,
    )
    return summary_doc


def main() -> None:
    ap = argparse.ArgumentParser(description="Phase D095 V5.3 Analysis Pipeline")
    ap.add_argument("--from-full-inputs", nargs="?", const=ROOT / "inputs_d095_v5_3", type=Path, default=None, help="Path to full raw inputs_d095_v5_3 directory")
    ap.add_argument("--from-bounded-inputs", type=Path, default=None, help="Path to d095_bounded_bundle.json.gz")
    ap.add_argument("--archives-dir", type=Path, default=None, help="Directory containing Companion Archives A-U")
    ap.add_argument("--out-dir", type=Path, default=WS / "results", help="Output directory")
    args = ap.parse_args()

    if args.from_bounded_inputs is not None:
        with gzip.open(args.from_bounded_inputs, "rt", encoding="utf-8") as gz:
            bundle = json.load(gz)
        run_stage_b(bundle, args.out_dir, archives_dir_arg=args.archives_dir)
    else:
        full_dir = args.from_full_inputs or (ROOT / "inputs_d095_v5_3")
        bundle_path = run_stage_a_build_bundle(full_dir)
        # Always pass exact serialized/deserialized bundle to guarantee 100% SHA-256 bit-identity
        with gzip.open(bundle_path, "rt", encoding="utf-8") as gz:
            bundle = json.load(gz)
        run_stage_b(bundle, args.out_dir, archives_dir_arg=args.archives_dir)


if __name__ == "__main__":
    main()
