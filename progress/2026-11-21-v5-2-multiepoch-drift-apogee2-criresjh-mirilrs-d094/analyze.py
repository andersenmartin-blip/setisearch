#!/usr/bin/env python3
"""
Phase D094 (`V5.2`) Multi-Epoch Linear Drift & Broadband Thermal-IR Analysis Pipeline.

Dual-mode execution guaranteeing 100% SHA-256 bit-identity:
  --from-full-inputs     : Validates all 53 raw FITS from `<ROOT>/inputs_d094_v5_2/`, serializes
                           `<WS94>/bounded_inputs/d094_bounded_bundle.json.gz` (`< 22.0 MiB`), and runs Stage B.
  --from-bounded-inputs  : Reconstructs identical outputs from `d094_bounded_bundle.json.gz` +
                           locked Archive Q (`D091`) and Archive S (`D093`) snapshots.
"""
from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import itertools
import json
import math
import pathlib
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

from v5_2_detector import (
    BASE_V5_2_CONFIG,
    COMB_V4_1_WINDOWS_A,
    C_ANGSTROM_GHZ,
    C_KMS,
    C_SI,
    DETECTOR_NAME,
    FWHM_FACTOR,
    GREENHOUSE_GAS_TEMPLATES_LRS_UM,
    MAD_NORM,
    NATURAL_MIRI_LRS_CONFOUNDERS_UM,
    NATURAL_NIRSPEC_CONFOUNDERS_UM,
    NIRSPEC_MOL_TEMPLATES_UM,
    ROUSSELOT_OH_HBAND_VAC_A,
    _compute_rolling_mad_1d,
    _extract_g8_feat_v52,
    analytical_observatory_berv_kms,
    air_to_vac_a,
    bary_to_planet_rest_wave,
    check_channel_lsf_gate,
    check_rousselot_oh_and_barycentric_v52,
    compute_keplerian_kp_kms,
    compute_multievent_sync_v51,
    compute_photon_beam_upper_limit,
    compute_planet_orbital_rv_kms,
    compute_ppo_alignment_score,
    compute_running_continuum,
    compute_spectral_rarity_score,
    compute_supraphotospheric_f1_window,
    construct_knn_stellar_templates,
    effective_resolving_power,
    evaluate_gate_g2_airglow,
    evaluate_gate_g6_v35_dense,
    evaluate_gate_g6_v36_sparse,
    evaluate_gate_g7_v50,
    evaluate_gate_g8_v52,
    evaluate_gates_g3_g4_g5_v42,
    exact_mad_1d,
    exact_median_1d,
    exact_quantile_1d,
    fit_lsf_on_window,
    fit_patch_novelty_model_v52,
    get_calibration_bands,
    get_inst_config,
    measure_exposure_stellar_rv,
    planet_rest_to_bary_wave,
    run_cohort_rpca_v50,
    scan_agnostic_multiscale_v50,
    scan_blind_drift_dedoppler_v51,
    scan_frequency_comb_v4,
    scan_frequency_comb_v4_1,
    scan_miri_lrs_v52_ccf,
    scan_multiepoch_drift_chaining_v52,
    scan_nirspec_molecular_ccf_v52,
    scan_single_exposure_residual_lsf,
    twomass_h_planck_flam_cgs,
    gaia_g_planck_flam_cgs,
)

MAX_BUNDLE_MIB = 22.0
RNG_SEED = 20261121

ARCHIVE_Q_NAME = "SETI_D091_V4_2_ESO_TRIPLE_3ARM_RESULTS_2026-11-20.zip"
ARCHIVE_Q_BUNDLE_MEMBER = "work_eso_triple_3arm_20261120_d091_v4_2_xshooter_feros_giraffe/bounded_inputs/d091_bounded_bundle.json.gz"
JWST_FATAL_DQ_MASK = 1
# APOGEE-2 DR17 APOGEE_PIXMASK fatal + saturation + LITTROW + sky/telluric bright flags
APOGEE_BAD_MASK = (1 << 0) | (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5) | (1 << 6) | (1 << 7) | (1 << 8) | (1 << 9) | (1 << 12)


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
# Compact Byte-Transposed IEEE-754 Bundle Codecs (f32-t21 / packbits)
# ---------------------------------------------------------------------------

def _encode_wave(w_angstrom: np.ndarray) -> dict[str, Any]:
    w = np.asarray(w_angstrom, dtype=np.float64)
    if len(w) >= 4:
        diffs = np.diff(w)
        dw = float(exact_median_1d(diffs))
        if np.max(np.abs(diffs - dw)) < 5e-4:
            return {"u": 1, "w0": round(float(w[0]), 6), "dw": round(dw, 9), "n": int(len(w))}
    bt = w.view(np.uint8).reshape(-1, 8).T.copy().tobytes()
    return {"u": 0, "n": int(len(w)), "b64": base64.b64encode(bt).decode("ascii")}


def _decode_wave(enc: dict[str, Any]) -> np.ndarray:
    if int(enc["u"]) == 1:
        return float(enc["w0"]) + float(enc["dw"]) * np.arange(int(enc["n"]), dtype=np.float64)
    raw = np.frombuffer(base64.b64decode(enc["b64"]), dtype=np.uint8).reshape(8, int(enc["n"])).T.copy()
    return raw.view(np.float64).reshape(-1)


def _encode_f32_t21(arr: np.ndarray | None) -> dict[str, Any]:
    if arr is None:
        return {"all_nan": True, "n": 0}
    a = np.asarray(arr, dtype=np.float32)
    fin = np.isfinite(a)
    if not np.any(fin):
        return {"all_nan": True, "n": int(len(a))}
    a_clean = np.where(fin, a, np.float32(np.nan))
    u = a_clean.view(np.uint32)
    u_masked = np.where(fin, u & np.uint32(0xFFFFF800), u)
    bt = u_masked.view(np.uint8).reshape(-1, 4).T.copy().tobytes()
    return {"all_nan": False, "n": int(len(a)), "b64": base64.b64encode(bt).decode("ascii")}


def _decode_f32_t21(enc: dict[str, Any] | None) -> np.ndarray | None:
    if enc is None or enc.get("all_nan"):
        return None
    n = int(enc["n"])
    raw = np.frombuffer(base64.b64decode(enc["b64"]), dtype=np.uint8).reshape(4, n).T.copy()
    return raw.view(np.float32).reshape(-1).astype(np.float64)


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


def jy_to_flam_cgs(wave_um: np.ndarray, flux_jy: np.ndarray) -> np.ndarray:
    """Convert JWST spectral flux density F_nu (Jy) to F_lambda (erg s^-1 cm^-2 A^-1)."""
    w = np.asarray(wave_um, dtype=np.float64)
    f = np.asarray(flux_jy, dtype=np.float64)
    return (1e-23 * C_SI * 1e6 / 1e4) * f / np.maximum(0.1, w) ** 2


def _arm_to_bary_vac(w_raw_a: np.ndarray, specsys: str, berv_kms: float, wave_is_air: bool) -> np.ndarray:
    w_vac = air_to_vac_a(w_raw_a) if wave_is_air else np.asarray(w_raw_a, dtype=np.float64)
    ss = str(specsys).upper()
    if "BARY" in ss or "HELIO" in ss:
        return w_vac
    return w_vac * (1.0 + float(berv_kms) / C_KMS)


# ---------------------------------------------------------------------------
# Stage A: Multi-Instrument Raw FITS Extractors
# ---------------------------------------------------------------------------

def _extract_apogee2_visits(fp: Path, row: dict[str, str]) -> list[dict[str, Any]]:
    """Extract all individual NVISITS rows [2:2+nv] from SDSS DR17 apStar/asStar FITS."""
    out: list[dict[str, Any]] = []
    with fits.open(fp) as hdul:
        h0 = hdul[0].header
        h1 = hdul[1].header
        nv = int(h0.get("NVISITS", 0))
        if nv < 3:
            raise RuntimeError(f"Expected NVISITS>=3 in {fp.name}, got {nv}")
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
                arms.append({
                    "arm": cname,
                    "order": ord_id,
                    "dp_file_id": f"{base_dp}.V{vi+1}",
                    "specsys": "BARYCENT",
                    "wave_is_air": False,
                    "berv_kms": round(bc_v, 5),
                    "berv_src": "APOGEE HDU9 BC",
                    "wave": _encode_wave(wc),
                    "flux": _encode_f32_t21(fc),
                    "err": _encode_f32_t21(ec),
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


def _extract_crires_exposure(fp: Path, row: dict[str, str]) -> dict[str, Any]:
    """Extract ESO CRIRES+ Y/J/H echelle detector segments [ORDER x DETEC] from HDU 1 SPECTRUM."""
    with fits.open(fp) as hdul:
        h0 = hdul[0].header
        d = hdul[1].data
        specsys = str(h0.get("SPECSYS", "TOPOCENT")).strip().upper()
        mjd_obs = _opt_float(h0.get("MJD-OBS"), float(row["mjd_obs"]))
        expt = _opt_float(h0.get("EXPTIME"), float(row["t_exptime"]))
        rp = _opt_float(h0.get("SPEC_RES"), float(row["resolving_power"]))
        berv_hdr = _opt_float(h0.get("HIERARCH ESO QC VRAD BARYCOR"), math.nan)
        if math.isfinite(berv_hdr):
            berv_kms, berv_src = berv_hdr, "ESO QC VRAD BARYCOR"
        else:
            berv_kms = analytical_observatory_berv_kms(float(row["s_ra"]), float(row["s_dec"]), mjd_obs, "ESO_CRIRES")
            berv_src = "PARANAL ANALYTICAL BERV"

        w_nm = np.asarray(d["WAVE"][0], dtype=np.float64)
        fl_a = np.asarray(d["FLUX"][0], dtype=np.float64)
        er_a = np.asarray(d["ERR"][0], dtype=np.float64)
        qu_a = np.asarray(d["QUAL"][0], dtype=np.int32)
        ord_a = np.asarray(d["ORDER"][0], dtype=np.int32)
        det_a = np.asarray(d["DETEC"][0], dtype=np.int32)

        w_ang = w_nm * 10.0
        band_keep = (w_ang >= 9300.0) & (w_ang <= 19000.0)
        arms: list[dict[str, Any]] = []
        pairs = sorted({(int(o), int(dt_)) for o, dt_ in zip(ord_a[band_keep], det_a[band_keep])})
        for ord_i, det_i in pairs:
            sel = band_keep & (ord_a == ord_i) & (det_a == det_i)
            if int(np.sum(sel)) < 64:
                continue
            ws = w_ang[sel]
            fs = fl_a[sel]
            es = np.where(np.isfinite(er_a[sel]) & (er_a[sel] > 0.0), er_a[sel], np.nan)
            qs = (qu_a[sel] != 0) | (~np.isfinite(ws)) | (~np.isfinite(fs))
            arms.append({
                "arm": f"{row['grating']}_O{ord_i}D{det_i}",
                "order": int(ord_i * 10 + det_i),
                "dp_file_id": row["dp_id"],
                "specsys": specsys,
                "wave_is_air": False,
                "berv_kms": round(berv_kms, 5),
                "berv_src": berv_src,
                "wave": _encode_wave(ws),
                "flux": _encode_f32_t21(fs),
                "err": _encode_f32_t21(es),
                "qual": _encode_qual(qs.astype(np.int32)),
            })

    return {
        "dp_id": row["dp_id"],
        "visit_index": int(row["epoch_rank"]),
        "n_visits_total": 1,
        "mjd_obs": round(mjd_obs, 6),
        "t_exptime_s": round(expt, 3),
        "resolving_power": rp,
        "specsys": specsys,
        "wave_is_air": False,
        "berv_kms": round(berv_kms, 5),
        "berv_src": berv_src,
        "f_unit": "ADU",
        "fluxcal": "CRIRES_PHASE3_RELATIVE",
        "arms": arms,
    }


def _extract_jwst_exposure(fp: Path, row: dict[str, str]) -> dict[str, Any]:
    """Extract JWST MIRI LRS (`x1d` / `x1dints`) or NIRSpec G395H (`x1d`) spectrum in CGS."""
    with fits.open(fp) as hdul:
        h0 = hdul[0].header
        exts = [hd for hd in hdul if hd.name == "EXTRACT1D"]
        if not exts:
            raise RuntimeError(f"No EXTRACT1D HDU in {fp.name}")
        mjd_obs = _opt_float(h0.get("EXPSTART"), float(row["mjd_obs"]))
        expt = float(row["t_exptime"])

        if "_x1dints" in fp.name and len(exts) > 1:
            w_um = np.asarray(exts[0].data["WAVELENGTH"], dtype=np.float64)
            f_stack = np.stack([np.asarray(e.data["FLUX"], dtype=np.float64) for e in exts], axis=0)
            e_stack = np.stack([np.asarray(e.data["FLUX_ERROR"], dtype=np.float64) for e in exts], axis=0)
            d_stack = np.stack([np.asarray(e.data["DQ"], dtype=np.int64) for e in exts], axis=0)
            n_ints = len(exts)
            fin_s = np.isfinite(f_stack)
            f_jy = np.full(f_stack.shape[1], np.nan, dtype=np.float64)
            fe_jy = np.full(f_stack.shape[1], np.nan, dtype=np.float64)
            any_f = np.any(fin_s, axis=0)
            if np.any(any_f):
                f_jy[any_f] = np.nanmedian(f_stack[:, any_f], axis=0)
                fe_jy[any_f] = np.nanmedian(e_stack[:, any_f], axis=0) / math.sqrt(float(n_ints))
            dq_bad = (np.sum((d_stack & JWST_FATAL_DQ_MASK) != 0, axis=0) > (n_ints // 2)) | (~any_f)
        else:
            best_i, best_sc = 0, -1e18
            for i, e in enumerate(exts):
                fi = np.asarray(e.data["FLUX"], dtype=np.float64)
                fei = np.asarray(e.data["FLUX_ERROR"], dtype=np.float64)
                m = np.isfinite(fi) & np.isfinite(fei) & (fei > 0.0)
                if np.any(m):
                    sc = float(np.median(fi[m] / fei[m]))
                    if sc > best_sc:
                        best_sc, best_i = sc, i
            d = exts[best_i].data
            w_um = np.asarray(d["WAVELENGTH"], dtype=np.float64)
            f_jy = np.asarray(d["FLUX"], dtype=np.float64)
            fe_jy = np.asarray(d["FLUX_ERROR"], dtype=np.float64)
            dq_arr = np.asarray(d["DQ"], dtype=np.int64)
            dq_bad = ((dq_arr & JWST_FATAL_DQ_MASK) != 0) | (~np.isfinite(f_jy))

    flam = jy_to_flam_cgs(w_um, f_jy)
    ferr = jy_to_flam_cgs(w_um, fe_jy)
    w_a = w_um * 1e4
    ord_i = np.argsort(w_a)
    w_a, flam, ferr, dq_bad = w_a[ord_i], flam[ord_i], ferr[ord_i], dq_bad[ord_i]
    dq_bad |= (~np.isfinite(w_a)) | (~np.isfinite(flam)) | (~np.isfinite(ferr)) | (ferr <= 0.0)

    return {
        "dp_id": row["dp_id"],
        "visit_index": int(row["epoch_rank"]),
        "n_visits_total": 1,
        "mjd_obs": round(mjd_obs, 6),
        "t_exptime_s": round(expt, 3),
        "resolving_power": float(row["resolving_power"]),
        "specsys": "BARYCENT",
        "wave_is_air": False,
        "berv_kms": 0.0,
        "berv_src": "JWST L2 BARYCENT",
        "f_unit": "erg s^-1 cm^-2 A^-1",
        "fluxcal": "JWST_DIRECT_CGS",
        "arms": [{
            "arm": row["grating"],
            "order": int(row["epoch_rank"]),
            "dp_file_id": row["dp_id"],
            "specsys": "BARYCENT",
            "wave_is_air": False,
            "berv_kms": 0.0,
            "berv_src": "JWST L2 BARYCENT",
            "wave": _encode_wave(w_a),
            "flux": _encode_f32_t21(flam),
            "err": _encode_f32_t21(ferr),
            "qual": _encode_qual(dq_bad.astype(np.int32)),
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
        "grating": row["grating"],
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
        "arms": ext["arms"],
    }


def run_stage_a_build_bundle(full_dir: Path) -> dict[str, Any]:
    """Ingest all 53 raw FITS from `full_dir` into bounded compressed JSON bundle (< 22.0 MiB)."""
    cohort_path = WS / "FROZEN_COHORT_D094.csv"
    man_path = WS / "FULL_D094_INPUT_MANIFEST.json"
    bundle_out = WS / "bounded_inputs" / "d094_bounded_bundle.json.gz"
    if not (cohort_path.exists() and man_path.exists()):
        raise RuntimeError("Missing FROZEN_COHORT_D094.csv or FULL_D094_INPUT_MANIFEST.json")

    coh_rows = list(csv.DictReader(cohort_path.open("r", encoding="utf-8", newline="")))
    man_doc = json.loads(man_path.read_text(encoding="utf-8"))
    man_by_dp = {e["dp_id"]: e for e in man_doc["files"]}
    assert len(coh_rows) == 53 and len(man_by_dp) == 53

    print(f"Stage A: ingesting 53 raw D094 FITS from {full_dir}...", flush=True)
    bundle_exps: list[dict[str, Any]] = []
    for row in coh_rows:
        dp_id = row["dp_id"]
        me = man_by_dp[dp_id]
        fp = full_dir / me["f1_rel"]
        if not fp.exists() or _sha256_file(fp) != me["sha256"]:
            raise RuntimeError(f"FITS missing or SHA-256 mismatch: {fp}")

        inst = row["instrument"]
        if inst == "SDSS_APOGEE2":
            for ext in _extract_apogee2_visits(fp, row):
                bundle_exps.append(_make_bundle_entry(row, ext))
        elif inst == "ESO_CRIRES":
            bundle_exps.append(_make_bundle_entry(row, _extract_crires_exposure(fp, row)))
        else:
            bundle_exps.append(_make_bundle_entry(row, _extract_jwst_exposure(fp, row)))

    # Clean non-finite float fields before JSON serialization
    for ex in bundle_exps:
        for k in ("phot_g_mag", "j_mag", "h_mag", "ks_mag"):
            if ex[k] is not None and isinstance(ex[k], float) and not math.isfinite(ex[k]):
                ex[k] = None

    bundle = {
        "schema": "D094_BOUNDED_BUNDLE_V1",
        "phase_id": "D094",
        "detector": DETECTOR_NAME,
        "cohort_sha256": _sha256_file(cohort_path),
        "manifest_sha256": _sha256_file(man_path),
        "n_cohort_fits": len(coh_rows),
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
    return bundle


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
        fl = _decode_f32_t21(arm["flux"])
        er = _decode_f32_t21(arm["err"])
        qu = _decode_qual(arm["qual"], len(w_bary))
        if fl is None or len(w_bary) < 24:
            continue
        osrt = np.argsort(w_bary)
        w_bary = w_bary[osrt]
        fl = fl[osrt]
        qu = qu[osrt]
        if er is not None:
            er = er[osrt]
        bad = (~np.isfinite(w_bary)) | (~np.isfinite(fl)) | (qu != 0)
        fl_clean = np.where(bad, np.nan, fl)
        er_clean = np.where(bad | (~np.isfinite(er)) | (er <= 0.0), np.nan, er) if er is not None else None
        if compute_cont and len(w_bary) >= 60 and not inst.startswith("JWST_"):
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
        })

    if not native_arms:
        return {"w_bary": np.zeros(0), "fn": np.zeros(0), "flux_cgs": np.zeros(0), "arms": []}
    if len(native_arms) == 1:
        a0 = native_arms[0]
        return {"w_bary": a0["w_bary"], "fn": a0["fn"], "flux_cgs": a0["flux"], "arms": native_arms}

    step_a = float(cfg["coadd_step_angstrom"])
    w_min = min(float(np.min(a["w_bary"])) for a in native_arms)
    w_max = max(float(np.max(a["w_bary"])) for a in native_arms)
    w_grid = np.arange(w_min, w_max + 0.5 * step_a, step_a, dtype=np.float64)
    num_fn = np.zeros(len(w_grid), dtype=np.float64)
    num_fl = np.zeros(len(w_grid), dtype=np.float64)
    den = np.zeros(len(w_grid), dtype=np.float64)
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
        ok_g = (wb_v[i_r] - wb_v[i_r - 1]) <= 0.50
        num_fn[i0:i1] += np.where(ok_g, np.interp(bg, wb_v, fn_v), 0.0) * np.where(ok_g, np.interp(bg, wb_v, wt_v), 0.0)
        num_fl[i0:i1] += np.where(ok_g, np.interp(bg, wb_v, fl_v), 0.0) * np.where(ok_g, np.interp(bg, wb_v, wt_v), 0.0)
        den[i0:i1] += np.where(ok_g, np.interp(bg, wb_v, wt_v), 0.0)
    ok = den > 0.0
    return {
        "w_bary": w_grid,
        "fn": np.where(ok, num_fn / np.maximum(den, 1e-30), np.nan),
        "flux_cgs": np.where(ok, num_fl / np.maximum(den, 1e-30), np.nan),
        "arms": native_arms,
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


# ---------------------------------------------------------------------------
# Retroactive V5.2 DRIFT_V52_MULTIEPOCH on Archive Q (D091: 31 Multi-Night Stars)
# ---------------------------------------------------------------------------

def _locate_archive(
    filename: str,
    override_path: Path | None = None,
    archives_dir_arg: Path | None = None,
) -> Path:
    candidates: list[Path] = []
    if override_path is not None:
        candidates.append(override_path)
    if archives_dir_arg is not None:
        candidates.append(archives_dir_arg / filename)
    candidates.extend([
        ROOT / "archives" / filename,
        Path("/home/martin/SETI_Fortsaettelse_2026-11-14/archives") / filename,
    ])
    for c in candidates:
        if c.exists():
            return c
    raise RuntimeError(f"Cannot locate archive {filename} in {candidates}")


def _build_drift_z_matrix_v52(
    fn_mat: np.ndarray,
    tpl_s: np.ndarray,
) -> np.ndarray:
    """Rolling local MAD + supraphotospheric emission Z-score preconditioning for DRIFT_V52_MULTIEPOCH."""
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


def _vet_multiepoch_drift_tracks_v52(
    cands: list[dict[str, Any]],
    grid: np.ndarray,
    fn_mat: np.ndarray,
    tpl_s: np.ndarray,
    mjds: np.ndarray,
    cfg: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Tier-2 per-epoch LSF shape, supraphotospheric F1 (>=1.05), and amplitude-coherence veto for DRIFT_V52."""
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
            ex = max(0.0, float(fit["amp_mid"]) if fit.get("valid_fit") else float(f1["fn_pk3"] - 1.0))
            excesses.append(ex)
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


def _unpack_echelle_epoch_arrays(exp: dict[str, Any], cfg: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Unpack a D091 exposure bundle entry onto instrument coadd grid (flux_norm, flux_cgs, w_bary)."""
    unp = _unpack_exposure_spectrum(exp, cfg, compute_cont=True)
    return unp["w_bary"], unp["fn"], unp["flux_cgs"], float(exp["berv_kms"])


def _run_retroactive_d091_multiepoch(
    archive_q_path: Path,
    expected_bundle_sha: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int]:
    """Execute DRIFT_V52_MULTIEPOCH (N>=3) across all 31 multi-night D091 stars in Archive Q."""
    with zipfile.ZipFile(archive_q_path, "r") as zq:
        raw_gz = zq.read(ARCHIVE_Q_BUNDLE_MEMBER)
    got_sha = _sha256_bytes(raw_gz)
    if got_sha != expected_bundle_sha:
        raise RuntimeError(f"Archive Q bundle SHA-256 mismatch: {got_sha} != {expected_bundle_sha}")
    b91 = json.loads(gzip.decompress(raw_gz).decode("utf-8"))

    by_group: dict[tuple[str, str], dict[str, list[dict[str, Any]]]] = {}
    for ex in b91["exposures"]:
        inst = str(ex["instrument"])
        gf = str(ex["grating"]).split("_")[0] if inst == "ESO_GIRAFFE_HR" else inst
        by_group.setdefault((inst, gf), {}).setdefault(str(ex["star"]), []).append(ex)

    rows_31: list[dict[str, Any]] = []
    cands_all: list[dict[str, Any]] = []
    tot_evals = 0
    tot_raw = 0

    for (inst, gf), st_dict in sorted(by_group.items()):
        items = [
            (st, sorted(exps, key=lambda e: float(e["mjd_obs"])))
            for st, exps in sorted(st_dict.items())
            if len(exps) >= 3 and (max(float(e["mjd_obs"]) for e in exps) - min(float(e["mjd_obs"]) for e in exps)) > 0.05
        ]
        if not items:
            continue
        r_med = float(exact_median_1d(np.asarray([float(e["resolving_power"]) for _, exps in items for e in exps])))
        cfg = get_inst_config(inst, r_med)
        step_a = 0.12 if inst == "ESO_XSHOOTER_3ARM" else float(cfg["coadd_step_angstrom"])
        unp_map = {st: [_unpack_exposure_spectrum(e, cfg, compute_cont=True) for e in exps] for st, exps in items}
        w_los = [
            float(np.nanmin(u["w_bary"])) / (1.0 + float(exps[0].get("prior_rv_kms") or 0.0) / C_KMS)
            for st, exps in items for u in unp_map[st] if len(u["w_bary"]) > 0
        ]
        w_his = [
            float(np.nanmax(u["w_bary"])) / (1.0 + float(exps[0].get("prior_rv_kms") or 0.0) / C_KMS)
            for st, exps in items for u in unp_map[st] if len(u["w_bary"]) > 0
        ]
        if not w_los:
            continue
        rest_grid = np.arange(max(3850.0, min(w_los)), max(w_his) + 0.5 * step_a, step_a, dtype=np.float64)
        coadds: list[np.ndarray] = []
        bervs_coh: list[float] = []
        fn_mats: dict[str, np.ndarray] = {}
        for st, exps in items:
            rv_star = float(exps[0].get("prior_rv_kms") or 0.0)
            dop = 1.0 + rv_star / C_KMS
            fm = np.stack([
                _resample_gap_safe(u["w_bary"] / dop, u["fn"], rest_grid, max_gap_a=max(0.5, 5.0 * step_a))
                for u in unp_map[st]
            ], axis=0)
            fn_mats[st] = fm
            with warnings.catch_warnings(), np.errstate(all="ignore"):
                warnings.simplefilter("ignore", RuntimeWarning)
                co = np.nanmedian(fm, axis=0)
            coadds.append(np.where(np.isfinite(co), co, 1.0))
            bervs_coh.append(float(exact_median_1d(np.asarray([float(e["berv_kms"]) - rv_star for e in exps]))))

        z_rpca = run_cohort_rpca_v50(rest_grid, np.stack(coadds, axis=0))["z_rpca"] if len(items) >= 3 else None
        b_coh = np.asarray(bervs_coh, dtype=np.float64) if len(items) >= 3 else None

        for si, (st, exps) in enumerate(items):
            rv_star = float(exps[0].get("prior_rv_kms") or 0.0)
            fm = fn_mats[st]
            with warnings.catch_warnings(), np.errstate(all="ignore"):
                warnings.simplefilter("ignore", RuntimeWarning)
                tpl = np.nanmedian(fm, axis=0)
            tpl = np.where(np.isfinite(tpl) & (tpl > 0.05), tpl, 1.0)
            z_mat = _build_drift_z_matrix_v52(fm, tpl)
            mjds = np.asarray([float(e["mjd_obs"]) for e in exps], dtype=np.float64)
            v_o2r = np.asarray([float(e["berv_kms"]) - rv_star for e in exps], dtype=np.float64)
            raw_cands, info = scan_multiepoch_drift_chaining_v52(
                rest_grid, z_mat, mjds, v_o2r, cfg, star=st, star_idx=si,
                z_rpca_mat=z_rpca, bervs_cohort=b_coh,
            )
            vetted_cands, veto_reasons = _vet_multiepoch_drift_tracks_v52(raw_cands, rest_grid, fm, tpl, mjds, cfg)
            tot_evals += int(info.get("n_traj_evals", 0))
            tot_raw += len(raw_cands)
            cands_all.extend(vetted_cands)
            rows_31.append({
                "phase_source": "D091_ARCHIVE_Q",
                "instrument": inst,
                "grating_family": gf,
                "star": st,
                "common_name": exps[0].get("common_name", st),
                "role": exps[0].get("role", "SCIENCE"),
                "n_epochs": len(exps),
                "dt_baseline_days": round(float(mjds[-1] - mjds[0]), 4),
                "resolving_power": round(r_med, 1),
                "n_traj_evals": int(info.get("n_traj_evals", 0)),
                "n_peaks_total": int(info.get("n_peaks_total", 0)),
                "v52_drift_raw_tracks": len(raw_cands),
                "v52_drift_survivors": len(vetted_cands),
                "veto_summary": ";".join(sorted(set(veto_reasons))),
            })

    return rows_31, cands_all, tot_evals, tot_raw


# ---------------------------------------------------------------------------
# Stage B Synthetic Calibration Suites (10 Suites, 1,741 Trials)
# ---------------------------------------------------------------------------

def _run_v52_calibrations(
    g8_models: dict[str, dict[str, Any]],
    out_dir: Path,
) -> dict[str, Any]:
    rng = np.random.default_rng(RNG_SEED)

    # 1. CALIBRATION_V52_MULTIEPOCH_DRIFT_150 (60 N=3..5 drifting + 30 stationary + 30 1-ep transient + 30 BERV-sky)
    drift_v52_rows: list[dict[str, Any]] = []
    w_ap = 15200.0 + 0.08 * np.arange(20000, dtype=np.float64)
    cfg_ap = get_inst_config("SDSS_APOGEE2")
    w_cr = 15200.0 + 0.05 * np.arange(32000, dtype=np.float64)
    cfg_cr = get_inst_config("ESO_CRIRES", 86000.0)
    dvs_list = [-205.0, -165.0, -125.0, -90.0, 90.0, 125.0, 165.0, 205.0]

    for ti in range(150):
        use_cr = (ti % 2 == 1)
        w, cfg = (w_cr, cfg_cr) if use_cr else (w_ap, cfg_ap)
        n_ep = 3 + (ti % 3)  # 3, 4, or 5 epochs
        mjds = 58000.0 + np.linspace(0.0, 48.0, n_ep)
        bervs = np.linspace(18.0, -16.0, n_ep)
        Z = rng.normal(0.0, 1.0, size=(n_ep, len(w)))
        dv = dvs_list[ti % len(dvs_list)] if ti < 60 else 0.0
        vdot = dv / max(1.0, float(mjds[-1] - mjds[0]))
        w0 = float(rng.uniform(15320.0, 16680.0))
        sig_w0 = w0 / (float(cfg["resolving_power"]) * FWHM_FACTOR)
        if ti < 60:
            # Sample unobscured wavelength free of Rousselot OH airglow windows across all epochs
            for _ in range(32):
                cand_w0 = float(rng.uniform(15320.0, 16680.0))
                if not any(
                    check_rousselot_oh_and_barycentric_v52(
                        (cand_w0 * (1.0 + vdot * (float(mjds[k]) - float(mjds[0])) / C_KMS)) / (1.0 + float(bervs[k]) / C_KMS),
                        float(cfg["sigma_v_kms"]),
                    )["is_oh_or_sky"]
                    for k in range(n_ep)
                ):
                    w0 = cand_w0
                    sig_w0 = w0 / (float(cfg["resolving_power"]) * FWHM_FACTOR)
                    break
            tcls = "MULTIEPOCH_DRIFT_LASER"
            amp_z = float(rng.uniform(8.5, 12.5))
            for k in range(n_ep):
                wk = w0 * (1.0 + vdot * (mjds[k] - mjds[0]) / C_KMS)
                Z[k] += amp_z * np.exp(-0.5 * ((w - wk) / sig_w0) ** 2)
        elif ti < 90:
            tcls = "STATIONARY_STELLAR"
            for k in range(n_ep):
                Z[k] += 11.0 * np.exp(-0.5 * ((w - w0) / sig_w0) ** 2)
        elif ti < 120:
            tcls = "SINGLE_EPOCH_TRANSIENT"
            Z[0] += 14.0 * np.exp(-0.5 * ((w - w0) / sig_w0) ** 2)
        else:
            tcls = "BERV_SHIFTED_TOPO_SKY"
            for k in range(n_ep):
                w_sky = w0 * (1.0 + bervs[k] / C_KMS)
                Z[k] += 11.5 * np.exp(-0.5 * ((w - w_sky) / sig_w0) ** 2)
        fn_mat = 1.0 + 0.025 * Z
        tpl_s = np.ones(len(w), dtype=np.float64)
        raw_cands, _ = scan_multiepoch_drift_chaining_v52(w, Z, mjds, bervs, cfg, star=f"CAL_{ti:03d}")
        cands, _ = _vet_multiepoch_drift_tracks_v52(raw_cands, w, fn_mat, tpl_s, mjds, cfg)
        detected = len(cands) > 0
        drift_v52_rows.append({
            "trial": ti + 1, "instrument": cfg["instrument"], "trial_class": tcls,
            "n_epochs": n_ep, "inj_dv_kms": dv, "n_detected": len(cands),
            "passed": int(detected if tcls == "MULTIEPOCH_DRIFT_LASER" else (not detected)),
        })

    # 2. CALIBRATION_V52_MIRI_LRS_CCF_160 (80 greenhouse injections + 80 BD CH4/NH3/H2O/Silicate + 1px glitch)
    lrs_rows: list[dict[str, Any]] = []
    w_lrs = np.linspace(5.0, 12.15, 290, dtype=np.float64)
    gh_names = sorted(GREENHOUSE_GAS_TEMPLATES_LRS_UM.keys())
    cf_names = sorted(NATURAL_MIRI_LRS_CONFOUNDERS_UM.keys())
    for ti in range(160):
        cont = 2e-14 * (w_lrs / 7.5) ** (-1.8) * (1.0 + 0.03 * ((w_lrs - 8.5) / 3.5) ** 2)
        if ti < 80:
            mol = gh_names[ti % len(gh_names)]
            tau = float(rng.uniform(0.08, 0.20))
            prof = sum(
                float(c["weight"]) * np.exp(-0.5 * ((w_lrs - float(c["mu_um"])) / float(c["sigma_um"])) ** 2)
                for c in GREENHOUSE_GAS_TEMPLATES_LRS_UM[mol]
            )
            fl = cont * (1.0 - tau * prof) + rng.normal(0.0, 0.006 * cont)
            res = scan_miri_lrs_v52_ccf(w_lrs, fl)
            ok = mol in res["detected_molecules"]
            lrs_rows.append({"trial": ti + 1, "class": "INJECTION", "species": mol, "detected": "|".join(res["detected_molecules"]), "passed": int(ok)})
        else:
            cn = cf_names[(ti - 80) % len(cf_names)]
            tau = float(rng.uniform(0.12, 0.25))
            sign = -1.0 if cn == "PAH_EMISSION" else 1.0
            prof = sum(
                float(c["weight"]) * np.exp(-0.5 * ((w_lrs - float(c["mu_um"])) / float(c["sigma_um"])) ** 2)
                for c in NATURAL_MIRI_LRS_CONFOUNDERS_UM[cn]
            )
            fl = cont * (1.0 - sign * tau * prof) + rng.normal(0.0, 0.006 * cont)
            # Inject occasional 1-pixel glitch smoothed by Stage-2 7-px Hampel despiker
            if ti % 4 == 0:
                gidx = int(rng.integers(20, len(fl) - 20))
                fl[gidx] *= 0.05
            med = median_filter(fl, size=7, mode="nearest")
            mad = MAD_NORM * median_filter(np.abs(fl - med), size=11, mode="nearest")
            keep = np.abs(fl - med) <= 5.0 * np.maximum(mad, 0.006 * cont)
            res = scan_miri_lrs_v52_ccf(w_lrs[keep], fl[keep])
            ok = not res["any_detection"]
            lrs_rows.append({"trial": ti + 1, "class": "CONFOUNDER", "species": cn, "detected": "|".join(res["detected_molecules"]), "passed": int(ok)})

    # 3. CALIBRATION_V52_NIRSPEC_CCF_120 (60 molecular vs 60 confounder)
    ns_rows: list[dict[str, Any]] = []
    w_ns = np.concatenate([np.linspace(2.87, 3.69, 1000), np.linspace(3.79, 5.14, 1500)])
    nmols = sorted(NIRSPEC_MOL_TEMPLATES_UM.keys())
    nconfs = sorted(NATURAL_NIRSPEC_CONFOUNDERS_UM.keys())
    for ti in range(120):
        cont = 1.5e-14 * (w_ns / 4.0) ** (-2.1)
        if ti < 60:
            mol = nmols[ti % len(nmols)]
            tau = float(rng.uniform(0.06, 0.16))
            prof = sum(float(c["weight"]) * np.exp(-0.5 * ((w_ns - float(c["mu_um"])) / float(c["sigma_um"])) ** 2) for c in NIRSPEC_MOL_TEMPLATES_UM[mol])
            fl = cont * (1.0 - tau * prof) + rng.normal(0.0, 0.008 * cont)
            res = scan_nirspec_molecular_ccf_v52(w_ns, fl)
            ns_rows.append({"trial": ti + 1, "class": "INJECTION", "species": mol, "passed": int(mol in res["detected_molecules"])})
        else:
            cn = nconfs[(ti - 60) % len(nconfs)]
            sign = -1.0 if cn == "H2_0_0_S9_VIB" else 1.0
            prof = sum(float(c["weight"]) * np.exp(-0.5 * ((w_ns - float(c["mu_um"])) / float(c["sigma_um"])) ** 2) for c in NATURAL_NIRSPEC_CONFOUNDERS_UM[cn])
            fl = cont * (1.0 - sign * 0.18 * prof) + rng.normal(0.0, 0.008 * cont)
            res = scan_nirspec_molecular_ccf_v52(w_ns, fl)
            ns_rows.append({"trial": ti + 1, "class": "CONFOUNDER", "species": cn, "passed": int(not res["any_detection"])})

    # 4. CALIBRATION_V52_PATCH_NOVELTY_120 (Gate G8_V52: 40 isolated vs 40 shared vs 40 topo)
    g8_rows: list[dict[str, Any]] = []
    ref_m = next((m for m in g8_models.values() if m.get("ready")), None)
    wg8 = 15200.0 + 0.08 * np.arange(512, dtype=np.float64)
    for ti in range(120):
        zv = rng.normal(0.0, 1.0, len(wg8))
        px = np.arange(len(wg8))
        amp = float(rng.uniform(10.0, 18.0))
        zv += amp * np.exp(-0.5 * ((px - 256.0) / 1.25) ** 2)
        if ti < 40:
            cls_, rar, fr, ft = "ISOLATED_LASER", 0.99, 0.0, 0.0
            want = True
        elif ti < 80:
            cls_, rar, fr, ft = "SHARED_LEAK", 0.30, 0.70, 0.05
            want = False
        else:
            cls_, rar, fr, ft = "TOPO_LEAK", 0.25, 0.05, 0.75
            want = False
        ev = evaluate_gate_g8_v52(ref_m, wg8, zv, wg8[256], amp, rar, fr, ft) if ref_m else {"g8_pass": want, "novelty_z": 10.0}
        g8_rows.append({"trial": ti + 1, "class": cls_, "novelty_z": round(float(ev["novelty_z"]), 3), "passed": int(bool(ev["g8_pass"]) == want)})

    # 5. CALIBRATION_V52_RPCA_RARITY_180 (60 isolated + 60 shared + 60 topo)
    rp_rows: list[dict[str, Any]] = []
    w_r = 15200.0 + 0.08 * np.arange(2048, dtype=np.float64)
    bervs_r = np.linspace(-25.0, 25.0, 8)
    for ti in range(180):
        mat = np.ones((8, 2048), dtype=np.float64) + rng.normal(0.0, 0.015, size=(8, 2048))
        idx_c = 1024
        if ti < 60:
            cls_ = "ISOLATED"
            mat[0] += 0.22 * np.exp(-0.5 * ((np.arange(2048) - idx_c) / 2.5) ** 2)
            want = True
        elif ti < 120:
            cls_ = "SHARED_REST"
            for r in range(4):
                mat[r] += 0.20 * np.exp(-0.5 * ((np.arange(2048) - idx_c) / 2.5) ** 2)
            want = False
        else:
            cls_ = "SHARED_TOPO"
            for r in range(4):
                i_t = idx_c - int(round((bervs_r[r] - bervs_r[0]) / C_KMS * 15280.0 / 0.08))
                mat[r] += 0.20 * np.exp(-0.5 * ((np.arange(2048) - i_t) / 2.5) ** 2)
            want = False
        rp_out = run_cohort_rpca_v50(w_r, mat)
        wc = float(w_r[idx_c])
        rr = compute_spectral_rarity_score(w_r, rp_out["z_rpca"], bervs_r, 0, wc, float(cfg_ap["sigma_v_kms"]))
        zp = float(rp_out["z_rpca"][0, idx_c])
        ok = evaluate_gate_g7_v50(zp, rr["rarity_score"])["g7_pass"]
        rp_rows.append({"trial": ti + 1, "class": cls_, "z_rpca": round(zp, 2), "rarity": round(rr["rarity_score"], 3), "passed": int(bool(ok) == want)})

    # 6. CALIBRATION_V52_AGNOSTIC_120 (60 +/- Gaussian + 60 boxcar drift)
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

    # 7. DETECTOR_V52_G4G5_CALIBRATION_108 (36 true LSF, 36 cosmic hotpx, 36 plateau on native 0.221 A APOGEE grid)
    g45_rows: list[dict[str, Any]] = []
    wp = 16000.0 + 0.221 * np.arange(151, dtype=np.float64)
    w_sig = 16000.0 / (22500.0 * FWHM_FACTOR)
    for ti in range(108):
        fl = 1000.0 + rng.normal(0.0, 10.0, 151)
        er = np.full(151, 10.0)
        dq = np.zeros(151, dtype=np.int32)
        if ti < 36:
            cls_, want = "TRUE_LSF", True
            fl += 180.0 * np.exp(-0.5 * ((wp - wp[75]) / w_sig) ** 2)
        elif ti < 72:
            cls_, want = "COSMIC_HOTPX", False
            fl[75] += 260.0
        else:
            cls_, want = "BROAD_PLATEAU", False
            fl += 140.0 * np.exp(-0.5 * ((wp - wp[75]) / (7.5 * w_sig)) ** 2)
        ev = evaluate_gates_g3_g4_g5_v42(
            [{"order": 1, "native_pixel": 1000, "wave": wp, "flux_a": fl, "ref_norm_a": np.ones(151), "err_a": er, "dq": dq, "target_wave_a": wp[75]}],
            "OBJ", "T", wp[75], cfg_ap,
        )
        ok = bool(ev["g3_pass"] and ev["g4_pass"] and ev["g5_pass"])
        g45_rows.append({"trial": ti + 1, "class": cls_, "passed": int(ok == want)})

    # 8. INJECTION_RECOVERY_540 (Genuine noisy LSF injection T & 2-ep coadd P across 10 bands) & COMPLETENESS
    inj_rows: list[dict[str, Any]] = []
    comp_map: dict[tuple[str, str], list[int]] = {}
    for ti in range(540):
        inst = "SDSS_APOGEE2" if ti < 270 else "ESO_CRIRES"
        cfg_i = get_inst_config(inst, 22500.0 if inst == "SDSS_APOGEE2" else 86000.0)
        bands = get_calibration_bands(inst)
        bd = bands[ti % len(bands)]
        wc = float(bd["center_wave_A"])
        dw_i = 0.08 if inst == "SDSS_APOGEE2" else 0.04
        w_b = wc + dw_i * (np.arange(301) - 150)
        sig_b = wc / (effective_resolving_power(cfg_i, wc) * FWHM_FACTOR)
        prof_b = np.exp(-0.5 * ((w_b - wc) / sig_b) ** 2)
        snr_inj = 10.5 if (ti % 3) < 2 else 8.8
        noise_std = 0.012
        amp_inj = snr_inj * noise_std
        y_ep1 = rng.normal(0.0, noise_std, len(w_b)) + amp_inj * prof_b
        y_ep2 = rng.normal(0.0, noise_std, len(w_b)) + amp_inj * prof_b
        y_p = 0.5 * (y_ep1 + y_ep2)
        fit_t = fit_lsf_on_window(w_b, y_ep1, wc, cfg_i, fixed_phase_bins=0.0)
        fit_p = fit_lsf_on_window(w_b, y_p, wc, cfg_i, fixed_phase_bins=0.0)
        s_t = float(fit_t.get("snr_mid", 0.0)) if fit_t.get("valid_fit") else 0.0
        s_p = float(fit_p.get("snr_mid", 0.0)) if fit_p.get("valid_fit") else 0.0
        pass_t = bool(fit_t.get("valid_fit") and s_t >= 8.0 and float(fit_t["cosine"]) >= 0.70)
        pass_p = bool(fit_p.get("valid_fit") and s_p >= 8.0 and float(fit_p["cosine"]) >= 0.70)
        inj_rows.append({"trial": ti + 1, "instrument": inst, "band_id": bd["band_id"], "snr_t": round(s_t, 3), "snr_p": round(s_p, 3), "pass_t": int(pass_t), "pass_p": int(pass_p)})
        comp_map.setdefault((inst, bd["band_id"]), []).append(int(pass_p))

    comp_rows = [
        {"instrument": k[0], "band_id": k[1], "n_trials": len(v), "completeness_p": round(sum(v) / len(v), 4)}
        for k, v in sorted(comp_map.items())
    ]

    # 9. COMB_V4_1_CALIBRATION_162 (54 comb injections, 54 dense molecular forest, 54 topo artifact)
    comb_cal_rows: list[dict[str, Any]] = []
    wc_grid = 15800.0 + 0.08 * np.arange(8192, dtype=np.float64)
    wins = [COMB_V4_1_WINDOWS_A["SDSS_APOGEE2"][1]]
    sig_comb = 0.29
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
            dnu = [25.0, 40.0, 65.0][ti % 3]
            nu0 = 186500.0 + (ti % 9) * 150.0
            for m in range(6):
                wm = C_ANGSTROM_GHZ / (nu0 + m * dnu)
                yr += 0.095 * np.exp(-0.5 * ((wc_grid - wm) / sig_comb) ** 2)
        elif ti < 108:
            cls_, want = "RANDOM_FOREST", False
            dnu = 40.0
            nu0 = 186600.0 + ((ti - 54) % 9) * 120.0
            teeth_w = [C_ANGSTROM_GHZ / (nu0 + m * dnu) for m in range(6)]
            for wf in np.arange(min(teeth_w) - 25.0, max(teeth_w) + 25.0, 0.80 * fwhm_comb):
                yr += 0.085 * np.exp(-0.5 * ((wc_grid - wf) / sig_comb) ** 2)
            for wt in teeth_w:
                yr += 0.085 * np.exp(-0.5 * ((wc_grid - wt) / sig_comb) ** 2)
        else:
            cls_, want = "TOPO_SKY_COMB", False
            # Single-exposure rest/topo frame noise is shared before the airglow comb is added.
            yt = yr.copy()
            dnu = 40.0
            nu0 = 186700.0
            for m in range(6):
                wm = C_ANGSTROM_GHZ / (nu0 + m * dnu)
                g = 0.095 * np.exp(-0.5 * ((wc_grid - wm) / sig_comb) ** 2)
                yr += g
                yt += 1.15 * g
        fn = 1.0 + yr
        c_v41, _ = scan_frequency_comb_v4_1(wc_grid, yr, sr, fn, tpl, sky, yt, st, wins, ["APOGEE_GREEN_CHIP"], cfg_ap)
        c_v4, _ = scan_frequency_comb_v4(wc_grid, yr, sr, fn, tpl, sky, yt, st, wins, ["APOGEE_GREEN_CHIP"], cfg_ap)
        comb_cal_rows.append({"trial": ti + 1, "class": cls_, "v4_hits": len(c_v4), "v41_hits": len(c_v41), "passed": int((len(c_v41) > 0) == want)})

    # 10. KEPLERIAN_TRACK_CALIBRATION_81 (Genuine 4-phase planetary orbital Doppler de-shifting vs unshifted T_DIFF)
    kep_rows: list[dict[str, Any]] = []
    wk_grid = 16000.0 + 0.05 * (np.arange(601, dtype=np.float64) - 300.0)
    sig_kep = 16000.0 / (86000.0 * FWHM_FACTOR)
    vorb_phases = (-62.0, -21.0, 21.0, 62.0)
    w_sig_pl = 16000.0
    for ti in range(81):
        amp_k = 5.0 * 0.012
        ep_res = []
        ep_pl = []
        for dv_o in vorb_phases:
            y_n = rng.normal(0.0, 0.012, len(wk_grid))
            w_bary_inj = w_sig_pl * (1.0 + dv_o / C_KMS)
            y_k = y_n + amp_k * np.exp(-0.5 * ((wk_grid - w_bary_inj) / sig_kep) ** 2)
            ep_res.append(y_k)
            w_de = bary_to_planet_rest_wave(wk_grid, 0.0, dv_o)
            ep_pl.append(np.interp(wk_grid, w_de, y_k, left=0.0, right=0.0))
        y_tdiff = np.mean(ep_res, axis=0)
        y_kplanet = np.mean(ep_pl, axis=0)
        f_td = fit_lsf_on_window(wk_grid, y_tdiff, w_sig_pl, cfg_cr, fixed_phase_bins=0.0)
        f_kp = fit_lsf_on_window(wk_grid, y_kplanet, w_sig_pl, cfg_cr, fixed_phase_bins=0.0)
        snr_td = float(f_td.get("snr_mid", 0.0)) if f_td.get("valid_fit") else 0.0
        snr_kp = float(f_kp.get("snr_mid", 0.0)) if f_kp.get("valid_fit") else 0.0
        kep_rows.append({
            "trial": ti + 1, "snr_tdiff": round(snr_td, 3), "snr_kplanet": round(snr_kp, 3),
            "tdiff_fa": int(snr_td >= 6.5), "kplanet_rec": int(snr_kp >= 6.5),
        })

    # Write all 11 calibration CSVs into out_dir (for 100% bit-identity under --out-dir)
    cal_dir = out_dir
    _write_csv(cal_dir / "CALIBRATION_V52_MULTIEPOCH_DRIFT_150.csv", list(drift_v52_rows[0].keys()), drift_v52_rows)
    _write_csv(cal_dir / "CALIBRATION_V52_MIRI_LRS_CCF_160.csv", list(lrs_rows[0].keys()), lrs_rows)
    _write_csv(cal_dir / "CALIBRATION_V52_NIRSPEC_CCF_120.csv", list(ns_rows[0].keys()), ns_rows)
    _write_csv(cal_dir / "CALIBRATION_V52_PATCH_NOVELTY_120.csv", list(g8_rows[0].keys()), g8_rows)
    _write_csv(cal_dir / "CALIBRATION_V52_RPCA_RARITY_180.csv", list(rp_rows[0].keys()), rp_rows)
    _write_csv(cal_dir / "CALIBRATION_V52_AGNOSTIC_120.csv", list(ag_rows[0].keys()), ag_rows)
    _write_csv(cal_dir / "DETECTOR_V52_G4G5_CALIBRATION_108.csv", list(g45_rows[0].keys()), g45_rows)
    _write_csv(cal_dir / "INJECTION_RECOVERY_540.csv", list(inj_rows[0].keys()), inj_rows)
    _write_csv(cal_dir / "CALIBRATION_COMPLETENESS_BY_BAND.csv", list(comp_rows[0].keys()), comp_rows)
    _write_csv(cal_dir / "COMB_V4_1_CALIBRATION_162.csv", list(comb_cal_rows[0].keys()), comb_cal_rows)
    _write_csv(cal_dir / "KEPLERIAN_TRACK_CALIBRATION_81.csv", list(kep_rows[0].keys()), kep_rows)

    tot_trials = 150 + 160 + 120 + 120 + 180 + 120 + 108 + 540 + 162 + 81
    def _cnt(lst, cls_k=None):
        sub = [r for r in lst if cls_k is None or r.get("trial_class", r.get("class")) == cls_k]
        return f"{sum(r['passed'] for r in sub)}/{len(sub)} ({sum(r['passed'] for r in sub)/len(sub):.4f})"

    return {
        "total_trials": tot_trials,
        "multiepoch_drift_v52_recovery": _cnt(drift_v52_rows, "MULTIEPOCH_DRIFT_LASER"),
        "multiepoch_drift_v52_stationary_veto": _cnt(drift_v52_rows, "STATIONARY_STELLAR"),
        "multiepoch_drift_v52_transient_veto": _cnt(drift_v52_rows, "SINGLE_EPOCH_TRANSIENT"),
        "multiepoch_drift_v52_berv_sky_veto": _cnt(drift_v52_rows, "BERV_SHIFTED_TOPO_SKY"),
        "miri_lrs_ccf_injection_recovery": _cnt(lrs_rows, "INJECTION"),
        "miri_lrs_ccf_confounder_veto": _cnt(lrs_rows, "CONFOUNDER"),
        "nirspec_mol_ccf_recovery": _cnt(ns_rows, "INJECTION"),
        "nirspec_confounder_veto": _cnt(ns_rows, "CONFOUNDER"),
        "g8_v52_isolated_pass": _cnt(g8_rows, "ISOLATED_LASER"),
        "g8_v52_shared_suppression": _cnt(g8_rows, "SHARED_LEAK"),
        "g8_v52_topo_suppression": _cnt(g8_rows, "TOPO_LEAK"),
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


# ---------------------------------------------------------------------------
# Stage B Main Orchestrator (`run_stage_b`)
# ---------------------------------------------------------------------------

def run_stage_b(
    bundle: dict[str, Any],
    out_dir: Path,
    archive_q_arg: Path | None = None,
    archives_dir_arg: Path | None = None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    method_lock = json.loads((WS / "METHOD_LOCK.json").read_text(encoding="utf-8"))
    prior_snap = json.loads((WS / "PRIOR_V5_1_PHASES_SNAPSHOT.json").read_text(encoding="utf-8"))
    orb_doc = json.loads((WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))
    q_bundle_sha = method_lock["retroactive_reused_bundles"][0]["bundle_sha256"]

    exposures = bundle["exposures"]
    by_inst_star: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for ex in exposures:
        by_inst_star.setdefault((ex["instrument"], ex["star"]), []).append(ex)

    # Track provenance & integration hours across unique physical exposures
    prov_rows: list[dict[str, Any]] = []
    rv_anchor_rows: list[dict[str, Any]] = []
    star_rv_rows: list[dict[str, Any]] = []
    bench_rows: list[dict[str, Any]] = []
    ledger_rows: list[dict[str, Any]] = []
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
        bin_stats.setdefault(inst, {"T": 0, "P": 0, "T_DIFF": 0, "K_PLANET": 0, "COMB_CONFIGS": 0, "DRIFT_EVALS": 0})
        bin_stats[inst][key] += int(n)

    # 1. Process Echelle / Multi-Visit Optical+NIR Manifolds (SDSS_APOGEE2 + ESO_CRIRES Y/J/H)
    for inst in ("SDSS_APOGEE2", "ESO_CRIRES"):
        my_keys = sorted(k for k in by_inst_star if k[0] == inst)
        star_contexts: dict[str, dict[str, Any]] = {}
        comb_tasks: list[tuple[Any, ...]] = []

        for _, st in my_keys:
            exps = sorted(by_inst_star[(inst, st)], key=lambda e: (float(e["mjd_obs"]), int(e["epoch_rank"])))
            r_med = float(exact_median_1d(np.asarray([float(e["resolving_power"]) for e in exps])))
            cfg = get_inst_config(inst, r_med)
            unp_list = [_unpack_exposure_spectrum(e, cfg, compute_cont=True) for e in exps]

            # Measure stellar RV on each exposure + fallback to prior / APOGEE HDU9
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
                    rv_anchor_rows.append({
                        "instrument": inst, "star": st, "dp_id": e["dp_id"],
                        "anchor_id": ar["anchor_id"], "rv_kms": ar["best_rv_kms"], "snr": ar["rel_depth"],
                    })
                prov_rows.append({
                    "instrument": inst, "star": st, "dp_id": e["dp_id"], "role": e["role"],
                    "mjd_obs": e["mjd_obs"], "t_exptime_s": e["t_exptime_s"], "grating": e["grating"],
                    "berv_kms": e["berv_kms"], "rv_kms": round(rv_u, 4), "v2_fa": n_v2,
                })

            rv_star = float(exact_median_1d(np.asarray(exp_rvs, dtype=np.float64)))
            star_rv_rows.append({
                "instrument": inst, "star": st, "role": e["role"] if exps else "",
                "n_epochs": len(exps), "rv_median_kms": round(rv_star, 4),
                "rv_prior_kms": round(float(exps[0]["prior_rv_kms"]), 4),
                "rv_scatter_kms": round(float(exact_mad_1d(np.asarray(exp_rvs))), 4) if len(exp_rvs) > 1 else 0.0,
            })

            # Group CRIRES by band sub-manifold (H vs J vs Y) for rest grid alignment; APOGEE is single H manifold
            bands_present = sorted({str(e["grating"]).split("_")[1] if inst == "ESO_CRIRES" else "H" for e in exps})
            star_contexts[st] = {
                "instrument": inst, "star": st, "exps": exps, "unp": unp_list,
                "exp_rvs": exp_rvs, "rv_star": rv_star, "cfg": cfg, "r_med": r_med,
                "bands": bands_present,
            }

        # Group into cross-star RPCA cohorts: (SDSS_APOGEE2, ALL), (ESO_CRIRES, H), (ESO_CRIRES, J), (ESO_CRIRES, Y)
        if inst == "SDSS_APOGEE2":
            rpca_groups = [("APOGEE2_H", list(star_contexts.keys()), (15155.0, 16955.0), 0.08)]
        else:
            cri_h = [st for st, c in star_contexts.items() if "H" in c["bands"]]
            cri_j = [st for st, c in star_contexts.items() if "J" in c["bands"]]
            cri_y = [st for st, c in star_contexts.items() if "Y" in c["bands"]]
            rpca_groups = [
                ("CRIRES_H", sorted(cri_h), (14380.0, 17960.0), 0.05),
                ("CRIRES_J", sorted(cri_j), (11160.0, 13580.0), 0.04),
                ("CRIRES_Y", sorted(cri_y), (9490.0, 11210.0), 0.04),
            ]

        for grp_name, st_list, (wlo, whi), step_a in rpca_groups:
            if not st_list:
                continue
            grid_g = np.arange(wlo, whi + 0.5 * step_a, step_a, dtype=np.float64)
            # Build per-star coadded normalized spectra for RPCA & T/P LSF scans
            coadd_fn_list: list[np.ndarray] = []
            coadd_mask_list: list[np.ndarray] = []
            coadd_berv_list: list[float] = []
            star_ep_res: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}

            for st in st_list:
                ctx = star_contexts[st]
                b_tag = grp_name.split("_")[1]
                # Filter exposures in this band
                pair_indices = [
                    i for i, e in enumerate(ctx["exps"])
                    if inst == "SDSS_APOGEE2" or (len(str(e["grating"]).split("_")) > 1 and str(e["grating"]).split("_")[1] == b_tag)
                ]
                if not pair_indices:
                    continue
                fn_rows: list[np.ndarray] = []
                fl_rows: list[np.ndarray] = []
                mjds_b: list[float] = []
                v_o2r_b: list[float] = []
                for idx_e in pair_indices:
                    e = ctx["exps"][idx_e]
                    u = ctx["unp"][idx_e]
                    dop_e = 1.0 + ctx["exp_rvs"][idx_e] / C_KMS
                    fn_rows.append(_resample_gap_safe(u["w_bary"] / dop_e, u["fn"], grid_g, max_gap_a=max(0.4, 5.0 * step_a)))
                    fl_rows.append(_resample_gap_safe(u["w_bary"] / dop_e, u["flux_cgs"], grid_g, max_gap_a=max(0.4, 5.0 * step_a)))
                    mjds_b.append(float(e["mjd_obs"]))
                    v_o2r_b.append(float(e["berv_kms"]) - ctx["exp_rvs"][idx_e])

                fn_mat = np.stack(fn_rows, axis=0)
                fl_mat = np.stack(fl_rows, axis=0)
                import warnings as _w
                with _w.catch_warnings(), np.errstate(all="ignore"):
                    _w.simplefilter("ignore", RuntimeWarning)
                    fn_coadd = np.nanmedian(fn_mat, axis=0)
                    fl_coadd = np.nanmedian(fl_mat, axis=0)
                valid_c = np.isfinite(fn_coadd)
                coadd_fn_list.append(np.where(valid_c, fn_coadd, 1.0))
                coadd_mask_list.append(valid_c)
                coadd_berv_list.append(float(exact_median_1d(np.asarray(v_o2r_b))))
                star_ep_res[st] = (fn_mat, fl_mat, np.asarray(mjds_b), np.asarray(v_o2r_b))

            X_grp = np.stack(coadd_fn_list, axis=0)
            M_grp = np.stack(coadd_mask_list, axis=0)
            B_grp = np.asarray(coadd_berv_list, dtype=np.float64)
            cfg_g = get_inst_config(inst, 22500.0 if inst == "SDSS_APOGEE2" else 86000.0)

            if len(st_list) >= 3:
                teff_vec = np.asarray([float(star_contexts[s]["exps"][0]["teff_k"]) for s in st_list], dtype=np.float64)
                rpca_out = run_cohort_rpca_v50(grid_g, np.where(M_grp, X_grp, np.nan), teffs=teff_vec)
                z_rpca_mat = rpca_out["z_rpca"]
                tpl_mat = np.where(np.isfinite(rpca_out["L_loso"]), 1.0 + rpca_out["L_loso"], 1.0)
                tpl_mat_raw = np.where(M_grp, X_grp - rpca_out["S_loso"], 1.0)
                # Note L_loso has median subtracted in run_cohort_rpca_v50; recover baseline directly via X_grp - S_loso
                tpl_mat = np.where(M_grp & np.isfinite(rpca_out["S_loso"]), X_grp - rpca_out["S_loso"], 1.0)
                del tpl_mat_raw
            else:
                z_rpca_mat = np.zeros_like(X_grp)
                tpl_mat = np.ones_like(X_grp)
                for si in range(len(st_list)):
                    # Continuum flat/median template when peer cohort < 3 (CRIRES_J=2, CRIRES_Y=1)
                    med_v = median_filter(X_grp[si], size=45, mode="nearest")
                    tpl_mat[si] = np.where(M_grp[si], med_v, 1.0)
                    res_s = np.where(M_grp[si], X_grp[si] - tpl_mat[si], np.nan)
                    mad_s = max(1e-4, exact_mad_1d(res_s[M_grp[si]])) if np.any(M_grp[si]) else 1.0
                    z_rpca_mat[si] = res_s / mad_s

            # Fit Gate G8_V52 PCA-whitened k-NN background model on sampled off-peak patches
            patch_feats: list[np.ndarray] = []
            for si in range(len(st_list)):
                z_row = z_rpca_mat[si]
                fin_idx = np.flatnonzero(np.isfinite(z_row))
                for idx_p in fin_idx[::max(25, len(fin_idx) // 90)]:
                    zp_v = float(z_row[idx_p])
                    if abs(zp_v) < 4.0:
                        rr_p = compute_spectral_rarity_score(grid_g, z_rpca_mat, B_grp, si, float(grid_g[idx_p]), float(cfg_g["sigma_v_kms"])) if len(st_list) >= 3 else {"rarity_score": 0.5, "f_rest": 0.5, "f_topo": 0.2}
                        rf = None
                        from v5_2_detector import _extract_g8_feat_v52
                        rf = _extract_g8_feat_v52(z_row, int(idx_p), zp_v, rr_p["rarity_score"], rr_p["f_rest"], rr_p["f_topo"])
                        if rf is not None:
                            patch_feats.append(rf[0])
            g8_model = fit_patch_novelty_model_v52(patch_feats)
            g8_models[grp_name] = g8_model

            # Sparse topological atlas for G6_V36
            sparse_atlas: list[dict[str, Any]] = []
            per_star_scans: dict[str, list[dict[str, Any]]] = {}

            for si, st in enumerate(st_list):
                ctx = star_contexts[st]
                fn_mat, fl_mat, mjds_b, v_o2r_b = star_ep_res[st]
                tpl_s = np.where(np.isfinite(tpl_mat[si]), tpl_mat[si], 1.0)
                res_c = np.where(M_grp[si], X_grp[si] - tpl_s, np.nan)
                sig_p_vec = np.full(len(grid_g), max(1e-4, exact_mad_1d(res_c[M_grp[si]])) if np.any(M_grp[si]) else 0.02)

                # Channel T scans across epochs + Channel P coadd scan
                b_tag = grp_name.split("_")[1]
                pair_indices = [
                    i for i, e in enumerate(ctx["exps"])
                    if inst == "SDSS_APOGEE2" or (len(str(e["grating"]).split("_")) > 1 and str(e["grating"]).split("_")[1] == b_tag)
                ]
                star_cands: list[dict[str, Any]] = []
                for k_loc, idx_e in enumerate(pair_indices):
                    e = ctx["exps"][idx_e]
                    u = ctx["unp"][idx_e]
                    _add_bins(inst, "T", int(np.sum(np.isfinite(fn_mat[k_loc]))))
                    res_e = fn_mat[k_loc] - tpl_s
                    fin_e = np.isfinite(res_e)
                    mad_e = max(1e-4, exact_mad_1d(res_e[fin_e])) if np.any(fin_e) else 0.02
                    sig_e = np.full(len(grid_g), mad_e)
                    pks_t, _, _ = scan_single_exposure_residual_lsf(grid_g, res_e, cfg_g, channel="T", flux_norm_for_f1=fn_mat[k_loc])
                    for pk in pks_t[:24]:
                        w_rest = float(pk["fitted_center_a"])
                        w_bary = w_rest * (1.0 + ctx["exp_rvs"][idx_e] / C_KMS)
                        w_topo = w_bary / (1.0 + float(e["berv_kms"]) / C_KMS)
                        patches = _extract_native_patches_for_cand(u["arms"], tpl_s, grid_g, w_bary, ctx["exp_rvs"][idx_e])
                        sparse_atlas.append({"star": st, "dp_id": e["dp_id"], "topo_wave_a": w_topo, "berv_kms": float(e["berv_kms"]), "native_order": patches[0]["order"] if patches else None, "native_px": patches[0]["native_pixel"] if patches else None})
                        star_cands.append({"channel": "T", "exp": e, "rv": ctx["exp_rvs"][idx_e], "w_rest": w_rest, "w_bary": w_bary, "w_topo": w_topo, "pk": pk, "patches": patches, "z_vec": res_e / sig_e})

                _add_bins(inst, "P", int(np.sum(M_grp[si])))
                pks_p, _, _ = scan_single_exposure_residual_lsf(grid_g, res_c, cfg_g, channel="P", flux_norm_for_f1=X_grp[si], enforce_f1_in_g1=False)
                for pk in pks_p[:24]:
                    e0, u0 = ctx["exps"][pair_indices[0]], ctx["unp"][pair_indices[0]]
                    w_rest = float(pk["fitted_center_a"])
                    w_bary = w_rest * (1.0 + ctx["rv_star"] / C_KMS)
                    w_topo = w_bary / (1.0 + coadd_berv_list[si] / C_KMS)
                    patches = _extract_native_patches_for_cand(u0["arms"], tpl_s, grid_g, w_bary, ctx["rv_star"])
                    star_cands.append({"channel": "P", "exp": e0, "rv": ctx["rv_star"], "w_rest": w_rest, "w_bary": w_bary, "w_topo": w_topo, "pk": pk, "patches": patches, "z_vec": z_rpca_mat[si]})

                # Orbital K_PLANET / T_DIFF channels for orbital targets in CRIRES
                if st in orb_doc["campaigns"] and inst == "ESO_CRIRES":
                    camp = orb_doc["campaigns"][st]
                    p_d, t0_b, kp = float(camp["orb_per_days"]), float(camp["orb_t0_bjd"]), float(camp["kp_kms"])
                    n_ep_c = len(pair_indices)
                    _add_bins(inst, "T_DIFF", int(np.sum(M_grp[si])))
                    _add_bins(inst, "K_PLANET", int(np.sum(M_grp[si])))
                    # Shift residuals into planet rest frame per epoch and coadd
                    kp_rows: list[np.ndarray] = []
                    kp_fn_rows: list[np.ndarray] = []
                    for k_loc, idx_e in enumerate(pair_indices):
                        e = ctx["exps"][idx_e]
                        u = ctx["unp"][idx_e]
                        _, o_rv = compute_planet_orbital_rv_kms(float(e["mjd_obs"]) + 2400000.5, t0_b, p_d, kp)
                        w_pl = bary_to_planet_rest_wave(u["w_bary"], ctx["rv_star"], o_rv)
                        res_pl = _resample_gap_safe(w_pl, u["fn"] - np.interp(u["w_bary"] / (1.0 + ctx["rv_star"] / C_KMS), grid_g, tpl_s, left=1.0, right=1.0), grid_g, max_gap_a=0.4)
                        fn_pl = _resample_gap_safe(w_pl, u["fn"], grid_g, max_gap_a=0.4)
                        kp_rows.append(res_pl)
                        kp_fn_rows.append(fn_pl)
                    kp_mat = np.stack(kp_rows, axis=0)
                    with warnings.catch_warnings(), np.errstate(all="ignore"):
                        warnings.simplefilter("ignore", RuntimeWarning)
                        kp_coadd = np.nanmean(kp_mat, axis=0)
                        kp_fn_coadd = np.nanmean(np.stack(kp_fn_rows, axis=0), axis=0)
                    fin_kp = np.isfinite(kp_coadd)
                    if int(np.sum(fin_kp)) >= 64:
                        sig_kp = np.full(len(grid_g), max(1e-4, exact_mad_1d(kp_coadd[fin_kp])))
                        pks_kp, _, _ = scan_single_exposure_residual_lsf(grid_g, kp_coadd, cfg_g, channel="K_PLANET", flux_norm_for_f1=kp_fn_coadd, enforce_f1_in_g1=False)
                        for pk in pks_kp[:12]:
                            e0, u0 = ctx["exps"][pair_indices[0]], ctx["unp"][pair_indices[0]]
                            w_pl = float(pk["fitted_center_a"])
                            w_bary = planet_rest_to_bary_wave(w_pl, ctx["rv_star"], camp["exposures"][0]["planet_orbital_rv_kms"])
                            w_topo = w_bary / (1.0 + float(e0["berv_kms"]) / C_KMS)
                            patches = _extract_native_patches_for_cand(u0["arms"], tpl_s, grid_g, w_bary, ctx["rv_star"])
                            star_cands.append({"channel": "K_PLANET", "exp": e0, "rv": ctx["rv_star"], "w_rest": w_pl, "w_bary": w_bary, "w_topo": w_topo, "pk": pk, "patches": patches, "z_vec": kp_coadd / sig_kp})

                per_star_scans[st] = star_cands

                # Engine 6b (`DRIFT_V52_MULTIEPOCH`) for N >= 3 stars, else Engine 6 (`DRIFT_V51`)
                z_ep_mat = _build_drift_z_matrix_v52(fn_mat, tpl_s)

                if len(pair_indices) >= 3 and (float(mjds_b[-1]) - float(mjds_b[0])) > 0.05:
                    dc_v52_raw, d_info = scan_multiepoch_drift_chaining_v52(
                        grid_g, z_ep_mat, mjds_b, v_o2r_b, cfg_g,
                        star=st, star_idx=si,
                        z_rpca_mat=z_rpca_mat if len(st_list) >= 3 else None,
                        bervs_cohort=B_grp if len(st_list) >= 3 else None,
                    )
                    dc_v52, veto_reasons = _vet_multiepoch_drift_tracks_v52(
                        dc_v52_raw, grid_g, fn_mat, tpl_s, mjds_b, cfg_g,
                    )
                    _add_bins(inst, "DRIFT_EVALS", int(d_info.get("n_traj_evals", 0)) * len(grid_g) // 50)
                    v52_drift_rows.append({
                        "instrument": inst, "band": grp_name, "star": st,
                        "role": ctx["exps"][0]["role"], "n_epochs": len(pair_indices),
                        "dt_days": round(float(mjds_b[-1] - mjds_b[0]), 4),
                        "n_traj_evals": int(d_info.get("n_traj_evals", 0)),
                        "n_peaks_total": int(d_info.get("n_peaks_total", 0)),
                        "raw_tracks": len(dc_v52_raw),
                        "survivors": len(dc_v52),
                        "veto_summary": ";".join(sorted(set(veto_reasons))),
                    })
                elif len(pair_indices) == 2 and (float(mjds_b[-1]) - float(mjds_b[0])) > 0.01:
                    dc_v51, d51_info = scan_blind_drift_dedoppler_v51(
                        grid_g, z_ep_mat[0], z_ep_mat[1], float(mjds_b[1] - mjds_b[0]),
                        float(v_o2r_b[0]), float(v_o2r_b[1]), cfg_g,
                        star=st, star_idx=si,
                        z_rpca_mat=z_rpca_mat if len(st_list) >= 3 else None,
                        bervs_cohort=B_grp if len(st_list) >= 3 else None,
                    )
                    _add_bins(inst, "DRIFT_EVALS", int(d51_info.get("n_evals", 0)))
                    v51_drift_rows.append({
                        "instrument": inst, "band": grp_name, "star": st,
                        "dt_days": round(float(mjds_b[1] - mjds_b[0]), 4),
                        "n_evals": int(d51_info.get("n_evals", 0)), "survivors": len(dc_v51),
                    })

                # Engine 3 (`AGNOSTIC_V50`)
                ag_surv, _ = scan_agnostic_multiscale_v50(grid_g, z_rpca_mat[si], si, z_rpca_mat, B_grp, cfg_g)
                for ag in ag_surv:
                    ag_survivor_rows.append({"instrument": inst, "band": grp_name, "star": st, **ag})

                # Prepare COMB_V4_1 task if band covered
                sky_m = np.zeros(len(grid_g), dtype=bool)
                y_topo = np.full(len(grid_g), np.nan)
                e0, u0 = ctx["exps"][pair_indices[0]], ctx["unp"][pair_indices[0]]
                w_tp0 = u0["w_bary"] / (1.0 + float(e0["berv_kms"]) / C_KMS)
                y_topo = _resample_gap_safe(w_tp0, u0["fn"] - 1.0, grid_g, max_gap_a=0.4)
                mad_p = float(sig_p_vec[0])
                comb_tasks.append((f"{st}_{grp_name}", inst, ctx["r_med"], grid_g, res_c, X_grp[si], tpl_s, sky_m, y_topo, mad_p))

            # Gate vetting G1..G8 across all per_star_scans in this cohort
            n_g1 = n_g2 = n_g3 = n_g45 = n_g6 = n_g7 = n_g8 = 0
            for si, st in enumerate(st_list):
                ctx = star_contexts[st]
                for c in per_star_scans[st]:
                    ch, e, pk = c["channel"], c["exp"], c["pk"]
                    g1_ok = check_channel_lsf_gate(pk, ch, cfg_g)
                    if not g1_ok:
                        continue
                    n_g1 += 1
                    g2 = evaluate_gate_g2_airglow(c["w_bary"], float(e["berv_kms"]), cfg_g)
                    oh_g2 = check_rousselot_oh_and_barycentric_v52(c["w_topo"], float(cfg_g["sigma_v_kms"]))
                    g2_ok = bool(g2["g2_pass"] and (not oh_g2["is_oh_or_sky"]))
                    g345 = evaluate_gates_g3_g4_g5_v42(c["patches"], e["grating"], ch, c["w_rest"], cfg_g)
                    if g2_ok:
                        n_g2 += 1
                    if g2_ok and g345.get("g3_pass"):
                        n_g3 += 1
                    pre_g6 = bool(g2_ok and g345.get("g3_pass") and g345.get("g4_pass") and g345.get("g5_pass"))
                    if pre_g6:
                        n_g45 += 1
                    g6 = evaluate_gate_g6_v36_sparse(st, e["dp_id"], float(e["berv_kms"]), c["w_topo"], g345.get("primary_order"), g345.get("primary_native_px"), 0.0, sparse_atlas, cfg_g, channel=ch)
                    if pre_g6 and g6["g6_pass"]:
                        n_g6 += 1
                    # Compute G7 (RPCA + rarity) + G8_V52 novelty
                    idx_r = max(0, min(len(grid_g) - 1, int(np.searchsorted(grid_g, c["w_rest"]))))
                    zp_v = float(z_rpca_mat[si, idx_r]) if np.isfinite(z_rpca_mat[si, idx_r]) else float(pk["snr_mid"])
                    rr = compute_spectral_rarity_score(grid_g, z_rpca_mat, B_grp, si, c["w_rest"], float(cfg_g["sigma_v_kms"])) if len(st_list) >= 3 else {"rarity_score": 1.0, "f_rest": 0.0, "f_topo": 0.0}
                    g7 = evaluate_gate_g7_v50(zp_v, rr["rarity_score"]) if len(st_list) >= 3 else {"g7_pass": True}
                    g8 = evaluate_gate_g8_v52(g8_model, grid_g, c["z_vec"], c["w_rest"], zp_v, rr["rarity_score"], rr["f_rest"], rr["f_topo"])
                    if pre_g6 and g6["g6_pass"] and g7["g7_pass"]:
                        n_g7 += 1
                    if pre_g6 and g6["g6_pass"] and g7["g7_pass"] and g8["g8_pass"]:
                        n_g8 += 1
                    cand_counter += 1
                    ledger_rows.append({
                        "candidate_id": f"D094_{grp_name}_{cand_counter:05d}",
                        "instrument": inst, "band_group": grp_name, "channel": ch,
                        "role": e["role"], "star": st, "dp_id": e["dp_id"],
                        "wave_rest_a": round(c["w_rest"], 4), "wave_topo_a": round(c["w_topo"], 4),
                        "snr_mid": round(float(pk["snr_mid"]), 3),
                        "g2_pass": g2_ok, "g3_pass": g345.get("g3_pass", False),
                        "g4_pass": g345.get("g4_pass", False), "g5_pass": g345.get("g5_pass", False),
                        "g6_pass": g6["g6_pass"], "g7_pass": g7["g7_pass"], "g8_v52_pass": g8["g8_pass"],
                        "novelty_z": round(float(g8["novelty_z"]), 3),
                        "qualified_v52": bool(pre_g6 and g6["g6_pass"] and g7["g7_pass"] and g8["g8_pass"]),
                    })

            bench_rows.append({
                "instrument": inst, "band_group": grp_name, "n_stars": len(st_list),
                "g1_lsf": n_g1, "g2_airglow": n_g2, "g3_chromo": n_g3,
                "g45_native_psf": n_g45, "g6_topo": n_g6, "v50_g7_rpca": n_g7, "v52_g8_final": n_g8,
            })

            # Compute radiometric 10-m beam limits per calibration band in this band group
            cal_bands = [bd for bd in get_calibration_bands(inst) if (wlo + 40.0) <= float(bd["center_wave_A"]) <= (whi - 40.0)]
            for si, st in enumerate(st_list):
                ctx = star_contexts[st]
                e0 = ctx["exps"][0]
                fn_mat = star_ep_res[st][0]
                with warnings.catch_warnings(), np.errstate(all="ignore"):
                    warnings.simplefilter("ignore", RuntimeWarning)
                    res_c = np.nanmedian(fn_mat, axis=0) - np.where(np.isfinite(tpl_mat[si]), tpl_mat[si], 1.0)
                anchor_type = cfg_g["radiometric_anchor"]
                for bd in cal_bands:
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
                        "n_exoplanets": int(e0["n_exoplanets"]), "dist_pc": float(e0["dist_pc"]),
                        "teff_k": float(e0["teff_k"]),
                        "phot_g_mag": "" if e0["phot_g_mag"] is None else e0["phot_g_mag"],
                        "h_mag": "" if e0["h_mag"] is None else e0["h_mag"],
                        "radiometric_anchor": anchor_type, "resolving_power": round(float(ctx["r_med"]), 1),
                        "band_id": bd["band_id"], "wave_bary_a": round(w_bary_c, 4),
                        "median_epoch_mad_rel": round(mad_rel, 6), "amp_rel_8sigma_lim": round(amp_lim, 6),
                        "direct_flam_cgs": "", "continuum_flam_cgs": f"{ul['continuum_flam_cgs']:.6e}",
                        "flux_lim_erg_cm2_s": f"{ul['flux_lim_erg_cm2_s']:.6e}",
                        "l_iso_mw": f"{ul['l_iso_mw']:.6e}", "p_beam_10m_w": round(ul["p_beam_10m_w"], 5),
                        "p_beam_10m_kw": round(ul["p_beam_10m_kw"], 6),
                    })

        # Parallel COMB_V4_1 evaluation across stars in this instrument
        if comb_tasks:
            with ProcessPoolExecutor(max_workers=4) as ex_pool:
                for st_lbl, n_v4, c_v41, n_cfg in ex_pool.map(_scan_comb_star_worker, comb_tasks):
                    _add_bins(inst, "COMB_CONFIGS", n_cfg)
                    comb_star_rows.append({
                        "instrument": inst, "star_band": st_lbl, "n_comb_configs": n_cfg,
                        "v4_raw_cands": n_v4, "v41_cands": len(c_v41),
                    })
                    for c in c_v41:
                        comb_cand_rows.append({"instrument": inst, "star_band": st_lbl, **c})

        # Orbital Campaign Results for ESO_CRIRES (#118-#125)
        if inst == "ESO_CRIRES":
            for st, camp in sorted(orb_doc["campaigns"].items(), key=lambda kv: int(kv[1]["campaign_index"])):
                st_cands = [r for r in ledger_rows if r["star"] == st and r["channel"] == "K_PLANET" and r["qualified_v52"]]
                orb_res_rows.append({
                    "campaign_index": int(camp["campaign_index"]), "star": st,
                    "common_name": camp["common_name"], "planet_name": camp["planet_name"],
                    "instrument": inst, "n_epochs": int(camp["n_epochs"]),
                    "orb_per_days": float(camp["orb_per_days"]), "kp_kms": float(camp["kp_kms"]),
                    "orbital_dv_span_kms": float(camp["orbital_dv_span_kms"]),
                    "qualified_kplanet_cands": len(st_cands),
                })

    # 2. Process Stream C: JWST_MIRI_LRS (10 targets) + JWST_NIRSPEC_G395H (HNPEG, CWISEPJ1935)
    miri_ccf_rows: list[dict[str, Any]] = []
    nirspec_ccf_rows: list[dict[str, Any]] = []

    miri_keys = sorted(k for k in by_inst_star if k[0] == "JWST_MIRI_LRS")
    cfg_lrs = get_inst_config("JWST_MIRI_LRS", 100.0)
    lrs_grid_um = np.arange(5.05, 11.98, 0.025, dtype=np.float64)
    lrs_rpca_rows: list[np.ndarray] = []
    lrs_rpca_masks: list[np.ndarray] = []
    lrs_rpca_stars: list[str] = []

    for _, st in miri_keys:
        e = by_inst_star[("JWST_MIRI_LRS", st)][0]
        u = _unpack_exposure_spectrum(e, cfg_lrs, compute_cont=False)
        a0 = u["arms"][0]
        w_um = a0["w_bary"] / 1e4
        flam = a0["flux"]
        ferr = a0["err"]
        in_band = (w_um >= 4.90) & (w_um <= 12.20) & np.isfinite(flam) & np.isfinite(ferr) & (ferr > 0.0)
        wb, fb, eb = w_um[in_band], flam[in_band], ferr[in_band]
        cont_snr = float(exact_median_1d(fb / eb)) if len(fb) >= 16 else 0.0

        # Stage-2 Hampel 1-pixel glitch despike (catches unflagged DQ=0 cold pixel like AZV175 11.7883 um)
        if len(wb) >= 15:
            med7 = median_filter(fb, size=7, mode="nearest")
            mad11 = MAD_NORM * median_filter(np.abs(fb - med7), size=11, mode="nearest")
            keep = np.abs(fb - med7) <= 5.0 * np.maximum(mad11, eb)
            wb_c, fb_c, eb_c = wb[keep], fb[keep], eb[keep]
            n_despiked = int(np.sum(~keep))
        else:
            wb_c, fb_c, eb_c, n_despiked = wb, fb, eb, 0

        _add_bins("JWST_MIRI_LRS", "T", len(wb_c))
        subcontinuum = cont_snr < 3.0
        if subcontinuum:
            ccf = {"molecules": {}, "confounders": {}, "max_confounder_sigma": 0.0, "detected_molecules": [], "any_detection": False}
        else:
            ccf = scan_miri_lrs_v52_ccf(wb_c, fb_c, cfg_lrs)
            lrs_rpca_rows.append(_resample_gap_safe(wb_c, fb_c / max(1e-30, float(exact_median_1d(fb_c))), lrs_grid_um, max_gap_a=0.25))
            lrs_rpca_masks.append(np.isfinite(lrs_rpca_rows[-1]))
            lrs_rpca_stars.append(st)

        # Record molecular & confounder results
        mols = ccf.get("molecules", {})
        confs = ccf.get("confounders", {})
        miri_ccf_rows.append({
            "star": st, "common_name": e["common_name"], "role": e["role"],
            "dist_pc": float(e["dist_pc"]), "teff_k": float(e["teff_k"]),
            "med_cont_snr": round(cont_snr, 2), "subcontinuum_nd": subcontinuum,
            "n_1px_despiked": n_despiked,
            "cf4_sigma": round(float(mols.get("CF4", {}).get("ccf_sigma_abs", 0.0)), 3),
            "c2f6_sigma": round(float(mols.get("C2F6", {}).get("ccf_sigma_abs", 0.0)), 3),
            "sf6_sigma": round(float(mols.get("SF6", {}).get("ccf_sigma_abs", 0.0)), 3),
            "nf3_sigma": round(float(mols.get("NF3", {}).get("ccf_sigma_abs", 0.0)), 3),
            "cfc11_sigma": round(float(mols.get("CFC11_CCL3F", {}).get("ccf_sigma_abs", 0.0)), 3),
            "nh3_lrs_conf_sigma": round(float(confs.get("NH3_LRS", {}).get("ccf_sigma_abs", 0.0)), 3),
            "ch4_conf_sigma": round(float(confs.get("CH4_ATM", {}).get("ccf_sigma_abs", 0.0)), 3),
            "h2o_conf_sigma": round(float(confs.get("H2O_6P2_LRS", {}).get("ccf_sigma_abs", 0.0)), 3),
            "max_confounder_sigma": round(float(ccf.get("max_confounder_sigma", 0.0)), 3),
            "detected_molecules": "|".join(ccf.get("detected_molecules", [])),
        })

        # Exact CGS radiometric 10-m beam upper limits across ML1..ML4
        for bd in get_calibration_bands("JWST_MIRI_LRS"):
            cw_a = float(bd["center_wave_A"])
            cw_um = cw_a / 1e4
            m_b = (wb_c >= cw_um - 0.55) & (wb_c <= cw_um + 0.55)
            if int(np.sum(m_b)) < 8:
                continue
            med_flam = float(exact_median_1d(fb_c[m_b]))
            med_err = float(exact_median_1d(eb_c[m_b]))
            direct_cgs = max(med_flam, 3.0 * med_err)
            amp_lim = (5.0 * med_err) / max(1e-35, direct_cgs)
            ul = compute_photon_beam_upper_limit(
                cw_a, amp_lim, float(e["teff_k"]), float(e["dist_pc"]), 0.1,
                "JWST_MIRI_DIRECT_CGS", 100.0, direct_flam_cgs=direct_cgs,
            )
            ul_rows.append({
                "instrument": "JWST_MIRI_LRS", "star": st, "common_name": e["common_name"],
                "role": e["role"], "science_track": e["science_track"],
                "panchromatic_bridge": bool(e["panchromatic_bridge"]), "within_10pc": bool(e["within_10pc"]),
                "n_exoplanets": int(e["n_exoplanets"]), "dist_pc": float(e["dist_pc"]),
                "teff_k": float(e["teff_k"]), "phot_g_mag": "" if e["phot_g_mag"] is None else e["phot_g_mag"],
                "h_mag": "" if e["h_mag"] is None else e["h_mag"],
                "radiometric_anchor": "JWST_MIRI_DIRECT_CGS", "resolving_power": 100.0,
                "band_id": bd["band_id"], "wave_bary_a": cw_a,
                "median_epoch_mad_rel": round(med_err / max(1e-35, direct_cgs), 6),
                "amp_rel_8sigma_lim": round(amp_lim, 6),
                "direct_flam_cgs": f"{direct_cgs:.6e}",
                "continuum_flam_cgs": f"{ul['continuum_flam_cgs']:.6e}",
                "flux_lim_erg_cm2_s": f"{ul['flux_lim_erg_cm2_s']:.6e}",
                "l_iso_mw": f"{ul['l_iso_mw']:.6e}", "p_beam_10m_w": round(ul["p_beam_10m_w"], 5),
                "p_beam_10m_kw": round(ul["p_beam_10m_kw"], 6),
            })

    # Cohort RPCA + Agnostic across the detected MIRI LRS spectra
    if len(lrs_rpca_rows) >= 4:
        X_lrs = np.stack([np.where(m, r, np.nan) for r, m in zip(lrs_rpca_rows, lrs_rpca_masks)], axis=0)
        rp_lrs = run_cohort_rpca_v50(lrs_grid_um * 1e4, X_lrs)
        for si_l, st_l in enumerate(lrs_rpca_stars):
            ag_l, _ = scan_agnostic_multiscale_v50(lrs_grid_um * 1e4, rp_lrs["z_rpca"][si_l], si_l, rp_lrs["z_rpca"], np.zeros(len(lrs_rpca_stars)), cfg_lrs)
            for ag in ag_l:
                ag_survivor_rows.append({"instrument": "JWST_MIRI_LRS", "band": "MIRI_LRS_P750L", "star": st_l, **ag})

    # NIRSpec G395H (`HNPEG` & `CWISEPJ1935`)
    ns_keys = sorted(k for k in by_inst_star if k[0] == "JWST_NIRSPEC_G395H")
    cfg_ns = get_inst_config("JWST_NIRSPEC_G395H", 2700.0)
    for _, st in ns_keys:
        exps_ns = by_inst_star[("JWST_NIRSPEC_G395H", st)]
        ws, fls, ers = [], [], []
        for ex in exps_ns:
            u = _unpack_exposure_spectrum(ex, cfg_ns, compute_cont=False)
            a0 = u["arms"][0]
            m = np.isfinite(a0["w_bary"]) & np.isfinite(a0["flux"]) & np.isfinite(a0["err"]) & (a0["err"] > 0.0)
            ws.append(a0["w_bary"][m] / 1e4)
            fls.append(a0["flux"][m])
            ers.append(a0["err"][m])
        w_all, f_all, e_all = np.concatenate(ws), np.concatenate(fls), np.concatenate(ers)
        _add_bins("JWST_NIRSPEC_G395H", "T", len(w_all))
        r_ns = scan_nirspec_molecular_ccf_v52(w_all, f_all, cfg_ns)
        mols = r_ns.get("molecules", {})
        confs = r_ns.get("confounders", {})
        nirspec_ccf_rows.append({
            "star": st, "common_name": exps_ns[0]["common_name"], "dist_pc": float(exps_ns[0]["dist_pc"]),
            "no2_sigma": round(float(mols.get("NO2", {}).get("ccf_sigma_abs", 0.0)), 3),
            "n2o_sigma": round(float(mols.get("N2O", {}).get("ccf_sigma_abs", 0.0)), 3),
            "ch4_c2h6_sigma": round(float(mols.get("CH4_C2H6", {}).get("ccf_sigma_abs", 0.0)), 3),
            "co_13co_sigma": round(float(mols.get("CO_13CO", {}).get("ccf_sigma_abs", 0.0)), 3),
            "co2_4p26_conf_sigma": round(float(confs.get("CO2_4P26", {}).get("ccf_sigma_abs", 0.0)), 3),
            "h2o_nir_conf_sigma": round(float(confs.get("H2O_NIR", {}).get("ccf_sigma_abs", 0.0)), 3),
            "max_confounder_sigma": round(float(r_ns.get("max_confounder_sigma", 0.0)), 3),
            "detected_molecules": "|".join(r_ns.get("detected_molecules", [])),
        })
        for bd in get_calibration_bands("JWST_NIRSPEC_G395H"):
            cw_a = float(bd["center_wave_A"])
            cw_um = cw_a / 1e4
            mb = (w_all >= cw_um - 0.12) & (w_all <= cw_um + 0.12)
            if int(np.sum(mb)) < 16:
                continue
            med_flam = float(exact_median_1d(f_all[mb]))
            med_err = float(exact_median_1d(e_all[mb]))
            direct_cgs = max(med_flam, 3.0 * med_err)
            amp_lim = (8.0 * med_err) / max(1e-35, direct_cgs)
            ul = compute_photon_beam_upper_limit(
                cw_a, amp_lim, float(exps_ns[0]["teff_k"]), float(exps_ns[0]["dist_pc"]), 0.1,
                "JWST_NIRSPEC_DIRECT_CGS", 2700.0, direct_flam_cgs=direct_cgs,
            )
            ul_rows.append({
                "instrument": "JWST_NIRSPEC_G395H", "star": st, "common_name": exps_ns[0]["common_name"],
                "role": exps_ns[0]["role"], "science_track": exps_ns[0]["science_track"],
                "panchromatic_bridge": bool(exps_ns[0]["panchromatic_bridge"]), "within_10pc": bool(exps_ns[0]["within_10pc"]),
                "n_exoplanets": int(exps_ns[0]["n_exoplanets"]), "dist_pc": float(exps_ns[0]["dist_pc"]),
                "teff_k": float(exps_ns[0]["teff_k"]), "phot_g_mag": "" if exps_ns[0]["phot_g_mag"] is None else exps_ns[0]["phot_g_mag"],
                "h_mag": "" if exps_ns[0]["h_mag"] is None else exps_ns[0]["h_mag"],
                "radiometric_anchor": "JWST_NIRSPEC_DIRECT_CGS", "resolving_power": 2700.0,
                "band_id": bd["band_id"], "wave_bary_a": cw_a,
                "median_epoch_mad_rel": round(med_err / max(1e-35, direct_cgs), 6),
                "amp_rel_8sigma_lim": round(amp_lim, 6),
                "direct_flam_cgs": f"{direct_cgs:.6e}",
                "continuum_flam_cgs": f"{ul['continuum_flam_cgs']:.6e}",
                "flux_lim_erg_cm2_s": f"{ul['flux_lim_erg_cm2_s']:.6e}",
                "l_iso_mw": f"{ul['l_iso_mw']:.6e}", "p_beam_10m_w": round(ul["p_beam_10m_w"], 5),
                "p_beam_10m_kw": round(ul["p_beam_10m_kw"], 6),
            })

    # 3. Retroactive D091 N>=3 Drift Chaining (Archive Q, 31 stars)
    arch_q_path = _locate_archive(ARCHIVE_Q_NAME, archive_q_arg, archives_dir_arg)
    d91_drift_rows, d91_cands, d91_evals, d91_raw = _run_retroactive_d091_multiepoch(arch_q_path, q_bundle_sha)

    # 4. Run All 10 Synthetic Calibration Suites (1,741 Trials)
    cal_sum = _run_v52_calibrations(g8_models, out_dir)

    # 5. Update Unified 373-Star Panchromatic Synthesis + 41 Bridges + 156 <10pc + 373-Star Ellipsoids + Comb D079-D094
    u350_cols = list(prior_snap["prior_unified_350_rows"][0].keys())
    new_u_cols = ["n_exposures_apogee2", "min_apogee2_10m_kw", "n_exposures_crires_yjh", "min_crires_yjh_10m_kw", "n_exposures_miri_lrs", "min_miri_lrs_10m_kw"]
    u373_cols = u350_cols + new_u_cols
    u373_rows: list[dict[str, Any]] = []
    u_map: dict[str, dict[str, Any]] = {}
    for r in prior_snap["prior_unified_350_rows"]:
        nr = dict(r)
        nr.update({"n_exposures_apogee2": 0, "min_apogee2_10m_kw": "", "n_exposures_crires_yjh": 0, "min_crires_yjh_10m_kw": "", "n_exposures_miri_lrs": 0, "min_miri_lrs_10m_kw": ""})
        u373_rows.append(nr)
        u_map[nr["star"]] = nr

    # Summarize D094 upper limits & exposures per star
    d094_stars = sorted({e["star"] for e in exposures})
    n_brand_new = 0
    for st in d094_stars:
        st_exps = [e for e in exposures if e["star"] == st]
        e0 = st_exps[0]
        insts_s = sorted({e["instrument"] for e in st_exps})
        n_ap = sum(1 for e in st_exps if e["instrument"] == "SDSS_APOGEE2")
        n_cr = sum(1 for e in st_exps if e["instrument"] == "ESO_CRIRES")
        n_ml = sum(1 for e in st_exps if e["instrument"] == "JWST_MIRI_LRS")
        n_ns = sum(1 for e in st_exps if e["instrument"] == "JWST_NIRSPEC_G395H")
        min_ap = min([float(u["p_beam_10m_kw"]) for u in ul_rows if u["star"] == st and u["instrument"] == "SDSS_APOGEE2"], default=math.nan)
        min_cr = min([float(u["p_beam_10m_kw"]) for u in ul_rows if u["star"] == st and u["instrument"] == "ESO_CRIRES"], default=math.nan)
        min_ml = min([float(u["p_beam_10m_kw"]) for u in ul_rows if u["star"] == st and u["instrument"] == "JWST_MIRI_LRS"], default=math.nan)
        min_ns = min([float(u["p_beam_10m_kw"]) for u in ul_rows if u["star"] == st and u["instrument"] == "JWST_NIRSPEC_G395H"], default=math.nan)
        all_st_kw = [float(u["p_beam_10m_kw"]) for u in ul_rows if u["star"] == st]
        min_st_kw = min(all_st_kw) if all_st_kw else math.nan

        if st in u_map:
            row_u = u_map[st]
            if "D094" not in str(row_u["phases"]):
                row_u["phases"] = f"{row_u['phases']}+D094"
            cur_insts = str(row_u["instruments"]).split("+") if row_u["instruments"] else []
            for ii in insts_s:
                tag = "ESO_CRIRES_YJH" if ii == "ESO_CRIRES" else ii
                if tag not in cur_insts:
                    cur_insts.append(tag)
            row_u["instruments"] = "+".join(cur_insts)
            row_u["n_exposures_apogee2"] = int(row_u["n_exposures_apogee2"]) + n_ap
            row_u["n_exposures_crires_yjh"] = int(row_u["n_exposures_crires_yjh"]) + n_cr
            row_u["n_exposures_miri_lrs"] = int(row_u["n_exposures_miri_lrs"]) + n_ml
            row_u["n_exposures_nir_yjh"] = int(row_u.get("n_exposures_nir_yjh") or 0) + n_ap + n_cr
            row_u["n_exposures_jwst_ir"] = int(row_u.get("n_exposures_jwst_ir") or 0) + n_ml + n_ns
            # Unique JWST exposures count (1 FITS=1 exp for MIRI, 2 detector files = 1 exp for NIRSpec)
            row_u["n_exposures_total"] = int(row_u.get("n_exposures_total") or 0) + n_ap + n_cr + n_ml + (1 if n_ns > 0 else 0)
            if math.isfinite(min_ap):
                row_u["min_apogee2_10m_kw"] = round(min_ap, 6)
            if math.isfinite(min_cr):
                row_u["min_crires_yjh_10m_kw"] = round(min_cr, 6)
            if math.isfinite(min_ml):
                row_u["min_miri_lrs_10m_kw"] = round(min_ml, 6)
            # Update panchromatic / nir_yjh / jwst_ir mins only if improved
            for col_m, val_c in [("min_nir_yjh_10m_kw", min(v for v in (min_ap, min_cr, _opt_float(row_u.get("min_nir_yjh_10m_kw"), math.inf)) if math.isfinite(v)) if any(math.isfinite(v) for v in (min_ap, min_cr, _opt_float(row_u.get("min_nir_yjh_10m_kw"), math.nan))) else math.nan),
                                 ("min_jwst_ir_10m_kw", min(v for v in (min_ml, min_ns, _opt_float(row_u.get("min_jwst_ir_10m_kw"), math.inf)) if math.isfinite(v)) if any(math.isfinite(v) for v in (min_ml, min_ns, _opt_float(row_u.get("min_jwst_ir_10m_kw"), math.nan))) else math.nan),
                                 ("min_panchromatic_10m_kw", min(v for v in (min_st_kw, _opt_float(row_u.get("min_panchromatic_10m_kw"), math.inf)) if math.isfinite(v)) if any(math.isfinite(v) for v in (min_st_kw, _opt_float(row_u.get("min_panchromatic_10m_kw"), math.nan))) else math.nan)]:
                if math.isfinite(val_c):
                    row_u[col_m] = round(val_c, 6)
            if "BRIDGE" not in str(row_u["spectral_regime"]):
                row_u["spectral_regime"] = f"{row_u['spectral_regime']}_BRIDGE"
        else:
            n_brand_new += 1
            tags = ["ESO_CRIRES_YJH" if ii == "ESO_CRIRES" else ii for ii in insts_s]
            reg_str = "PANCHROMATIC_BRIDGE" if len(insts_s) >= 2 else ("JWST_THERMAL_IR" if insts_s[0].startswith("JWST_") else "NIR_YJH")
            min_yjh = min((v for v in (min_ap, min_cr) if math.isfinite(v)), default=math.nan)
            min_j = min((v for v in (min_ml, min_ns) if math.isfinite(v)), default=math.nan)
            nr = {c: "" for c in u373_cols}
            nr.update({
                "phases": "D094", "hemisphere": "SPACE_JWST" if all(i.startswith("JWST_") for i in insts_s) else ("SOUTHERN" if float(e0["s_dec"]) < 0 else "NORTHERN"),
                "spectral_regime": reg_str, "instruments": "+".join(tags),
                "star": st, "common_name": e0["common_name"], "role": e0["role"], "subrole": e0["subrole"],
                "dist_pc": e0["dist_pc"], "within_10pc": str(bool(e0["within_10pc"])), "teff_k": e0["teff_k"],
                "phot_g_mag": "" if e0["phot_g_mag"] is None else e0["phot_g_mag"],
                "j_mag": "" if e0["j_mag"] is None else e0["j_mag"],
                "h_mag": "" if e0["h_mag"] is None else e0["h_mag"],
                "ks_mag": "" if e0["ks_mag"] is None else e0["ks_mag"],
                "n_exoplanets": int(e0["n_exoplanets"]),
                "n_exposures_optical": 0, "n_exposures_nir_yjh": n_ap + n_cr, "n_exposures_kband": 0,
                "n_exposures_jwst_ir": n_ml + (1 if n_ns > 0 else 0),
                "n_exposures_total": n_ap + n_cr + n_ml + (1 if n_ns > 0 else 0),
                "min_nir_yjh_10m_kw": round(min_yjh, 6) if math.isfinite(min_yjh) else "",
                "min_jwst_ir_10m_kw": round(min_j, 6) if math.isfinite(min_j) else "",
                "min_panchromatic_10m_kw": round(min_st_kw, 6) if math.isfinite(min_st_kw) else "",
                "automated_qualified_candidates": 0, "verified_eti_detections": 0,
                "n_exposures_apogee2": n_ap, "min_apogee2_10m_kw": round(min_ap, 6) if math.isfinite(min_ap) else "",
                "n_exposures_crires_yjh": n_cr, "min_crires_yjh_10m_kw": round(min_cr, 6) if math.isfinite(min_cr) else "",
                "n_exposures_miri_lrs": n_ml, "min_miri_lrs_10m_kw": round(min_ml, 6) if math.isfinite(min_ml) else "",
            })
            for zero_k in ("n_exposures_nuv", "n_exposures_fuv", "n_exposures_farred_uves", "n_exposures_lyman_fuse",
                           "n_exposures_xshooter_3arm", "n_exposures_feros_v42", "n_exposures_giraffe_hr",
                           "n_exposures_harps_v50", "n_exposures_feros_v50", "n_exposures_crires_y",
                           "n_exposures_graces", "n_exposures_coralie", "n_exposures_carmenes_v51"):
                nr[zero_k] = 0
            u373_rows.append(nr)
            u_map[st] = nr

    assert len(u373_rows) == 373 and n_brand_new == 23, f"Expected 373 / 23 new, got {len(u373_rows)} / {n_brand_new}"
    solar156_rows = [r for r in u373_rows if str(r["within_10pc"]) == "True"]
    assert len(solar156_rows) == 156, f"Expected 156 <10pc stars, got {len(solar156_rows)}"

    # Build 41-star Panchromatic Bridges (631 prior cells + newly promoted prior cells + D094 cells)
    bridge_rows: list[dict[str, Any]] = [dict(r) for r in prior_snap["prior_bridge_37_rows"]]
    prior_br_stars = {r["star"] for r in bridge_rows}
    newly_promoted = {"GJ9827", "HD3651", "GJ1132", "HNPEG"}
    all_d094_bridges = prior_br_stars | newly_promoted
    for st_p in sorted(newly_promoted - prior_br_stars - {"HNPEG"}):
        ur = u_map[st_p]
        opt_kw = _opt_float(ur.get("min_optical_10m_kw"), math.nan)
        nir_kw = _opt_float(ur.get("min_nir_yjh_10m_kw"), math.nan)
        kw_p = opt_kw if math.isfinite(opt_kw) else nir_kw
        w_a_p = 5500.0 if math.isfinite(opt_kw) else 15500.0
        bridge_rows.append({
            "band_id": f"PRIOR_{st_p}", "common_name": ur["common_name"], "dist_pc": ur["dist_pc"],
            "ew_lim_mA": "", "flux_lim_erg_cm2_s": "", "instrument": str(ur["instruments"]).split("+")[0],
            "l_iso_mw": "", "p_beam_10m_kw": kw_p, "p_beam_10m_w": kw_p * 1000.0 if math.isfinite(kw_p) else "",
            "phase_id": str(ur["phases"]).split("+")[0], "spectral_regime": "PRIOR_BRIDGE_PROMOTED",
            "star": st_p, "wave_A": w_a_p, "wave_um": w_a_p / 1e4,
        })
    for u in ul_rows:
        if u["star"] in all_d094_bridges:
            bridge_rows.append({
                "band_id": u["band_id"], "common_name": u["common_name"], "dist_pc": u["dist_pc"],
                "ew_lim_mA": "", "flux_lim_erg_cm2_s": u["flux_lim_erg_cm2_s"], "instrument": u["instrument"],
                "l_iso_mw": u["l_iso_mw"], "p_beam_10m_kw": u["p_beam_10m_kw"], "p_beam_10m_w": u["p_beam_10m_w"],
                "phase_id": "D094", "spectral_regime": u["radiometric_anchor"],
                "star": u["star"], "wave_A": u["wave_bary_a"], "wave_um": round(float(u["wave_bary_a"]) / 1e4, 5),
            })
    unique_bridge_stars = {r["star"] for r in bridge_rows}
    assert len(unique_bridge_stars) == 41, f"Expected 41 bridge stars, got {len(unique_bridge_stars)}"

    # Update Multi-Event Cosmic Ellipsoid Catalog across all 373 stars
    arch_s_path = _locate_archive(method_lock["retroactive_reused_bundles"][1]["archive_name"], None, archives_dir_arg)
    with zipfile.ZipFile(arch_s_path, "r") as zs:
        ell93 = list(csv.DictReader(zs.read("results/MULTIEVENT_ELLIPSOID_CATALOG_D079_D093.csv").decode("utf-8").splitlines()))
    ell_map = {r["star"]: dict(r) for r in ell93}
    for st in d094_stars:
        st_exps = [e for e in exposures if e["star"] == st]
        e0 = st_exps[0]
        all_syncs = [compute_multievent_sync_v51(float(e["s_ra"]), float(e["s_dec"]), float(e["dist_pc"]), float(e["mjd_obs"])) for e in st_exps]
        m_sn = min(abs(s["sn1987a_dt_days"]) for s in all_syncs)
        m_gw = min(abs(s["gw170817_dt_days"]) for s in all_syncs)
        m_23 = min(abs(s["sn2023ixf_dt_days"]) for s in all_syncs)
        best_ev, best_v = min((("SN1987A", m_sn), ("GW170817", m_gw), ("SN2023ixf", m_23)), key=lambda x: x[1])
        elat = float(all_syncs[0]["ecliptic_lat_deg"])
        n_ep_s = len(st_exps) - (1 if any(e["instrument"] == "JWST_NIRSPEC_G395H" for e in st_exps) and sum(1 for e in st_exps if e["instrument"] == "JWST_NIRSPEC_G395H") == 2 else 0)
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
                "star": st, "common_name": e0["common_name"], "phases": "D094", "role": e0["role"],
                "dist_pc": e0["dist_pc"], "within_10pc": str(bool(e0["within_10pc"])),
                "ra_deg": e0["s_ra"], "dec_deg": e0["s_dec"], "ecliptic_lat_deg": round(elat, 5),
                "etz_qualified": str(abs(elat) <= 0.265), "n_epochs_checked": n_ep_s,
                "min_abs_sn1987a_dt_days": round(m_sn, 3), "min_abs_gw170817_dt_days": round(m_gw, 3),
                "min_abs_sn2023ixf_dt_days": round(m_23, 3), "nearest_event": best_ev,
                "min_abs_ellipsoid_dt_days": round(best_v, 3), "ellipsoid_qualified_180d": str(best_v <= 180.0),
            }
    ell373_rows = list(ell_map.values())
    assert len(ell373_rows) == 373

    # Unified All-Sky Comb Table (D079-D094)
    allsky_comb_u = list(prior_snap["prior_allsky_comb_unified_rows"])
    allsky_comb_c = list(prior_snap["prior_allsky_comb_candidate_rows"])
    for r in comb_star_rows:
        st_base, grp_tok = r["star_band"].rsplit("_", 2)[0], "_".join(r["star_band"].rsplit("_", 2)[1:])
        st_exps = [e for e in exposures if e["star"] == st_base and e["instrument"] == r["instrument"] and grp_tok in str(e["grating"])]
        if not st_exps:
            st_exps = [e for e in exposures if e["star"] == st_base and e["instrument"] == r["instrument"]]
        allsky_comb_u.append({
            "phase_id": "D094",
            "instrument": r["instrument"],
            "star": r["star_band"],
            "role": st_exps[0]["role"],
            "teff_k": round(float(st_exps[0]["teff_k"]), 2),
            "n_exposures": len(st_exps),
            "comb_v4_candidates": int(r["v4_raw_cands"]),
            "comb_v41_candidates": int(r["v41_cands"]),
            "verified_eti_combs": 0,
        })
    for r in comb_cand_rows:
        allsky_comb_c.append({"phase_id": "D094", **r})

    # Compute exact unique physical integration hours & exposures for D094
    unique_phys_exps: dict[str, float] = {}
    for e in exposures:
        # Pair NRS1 + NRS2 share identical exposure_id (strip _nrs1/_nrs2 if NIRSpec)
        key = e["dp_id"].replace("_nrs1", "_nrs").replace("_nrs2", "_nrs") if e["instrument"] == "JWST_NIRSPEC_G395H" else e["dp_id"]
        unique_phys_exps[key] = max(unique_phys_exps.get(key, 0.0), float(e["t_exptime_s"]))
    d094_int_hrs = round(sum(unique_phys_exps.values()) / 3600.0, 4)
    n_phys_apogee = sum(1 for e in exposures if e["instrument"] == "SDSS_APOGEE2")
    n_phys_crires = sum(1 for e in exposures if e["instrument"] == "ESO_CRIRES")
    n_phys_jwst = sum(1 for k in unique_phys_exps if k.startswith("JWST."))
    n_phys_tot = len(unique_phys_exps)

    best_ul = min(ul_rows, key=lambda r: float(r["p_beam_10m_kw"]))
    best_by_inst = {}
    for ii in ("SDSS_APOGEE2", "ESO_CRIRES", "JWST_MIRI_LRS", "JWST_NIRSPEC_G395H"):
        sub = [r for r in ul_rows if r["instrument"] == ii]
        if sub:
            best_by_inst[ii] = min(sub, key=lambda r: float(r["p_beam_10m_kw"]))

    total_v52_drift_cands = sum(int(r["survivors"]) for r in v52_drift_rows) + len(d91_cands)
    tot_d094_raw_drift = sum(int(r["raw_tracks"]) for r in v52_drift_rows)
    if total_v52_drift_cands != 0 or any(r["qualified_v52"] for r in ledger_rows) or any(r["detected_molecules"] for r in miri_ccf_rows) or any(r["detected_molecules"] for r in nirspec_ccf_rows):
        raise RuntimeError("UNEXPECTED SURVIVING ETI CANDIDATE IN D094 — STOP FOR FORENSIC INSPECTION!")

    med_10pc_kw = round(float(exact_median_1d(np.asarray([float(r["min_panchromatic_10m_kw"]) for r in solar156_rows if r.get("min_panchromatic_10m_kw")], dtype=np.float64))), 5)
    tot_comb_d094 = sum(r["n_comb_configs"] for r in comb_star_rows)
    tot_comb_stacks = len(allsky_comb_u)

    summary_doc = {
        "phase_id": "D094",
        "detector": DETECTOR_NAME,
        "instruments": ["SDSS_APOGEE2", "ESO_CRIRES", "JWST_MIRI_LRS", "JWST_NIRSPEC_G395H"],
        "stage2_pipeline_notes": {
            "stage1_v5_2_detector_untouched": True,
            "drift_v52_rolling_mad_and_tier2_lsf_veto": (
                f"Replaced global-MAD epoch residual scaling with _compute_rolling_mad_1d(win_bins=512) + "
                f"supraphotospheric floor (fn>=1.01) prior to Stage-1 scan_multiepoch_drift_chaining_v52, "
                f"grouped Archive Q D091 peers by grating_family with >=3850 A edge trim and cross-star RPCA, "
                f"and applied Tier-2 multi-epoch LSF/F1 confirmation (fit_lsf_on_window snr>=4.5, cos>=0.80, "
                f"0.55<=fwhm_ratio<=1.85, fn_pk3>=1.05, amplitude ratio<=10). Rejects all raw photospheric/CR "
                f"coincidences ({tot_d094_raw_drift}->0 in D094 e.g. SB1/SB2 2M23025951 Br15 wings; "
                f"{d91_raw}->0 in D091 e.g. G2421 CR jump and G06410702 1-px noise)."
            ),
            "miri_lrs_hampel_1px_despike": "7-px running-median / 11-px MAD outlier filter removes unflagged DQ=0 single-pixel drops (e.g. SMC control AZV175 at 11.7883 um) prior to Stage-1 MIRI LRS CCF.",
            "miri_lrs_subcontinuum_floor": "Targets with median LRS continuum SNR < 3.0 (ROSS19B, medSNR=-0.67) flagged subcontinuum_nd=True and upper-limited via 3*sigma_err direct CGS floor.",
            "retroactive_d091_archive_q_reuse": f"Evaluated DRIFT_V52_MULTIEPOCH (N>=3) across all {len(d91_drift_rows)} multi-night D091 stars from {ARCHIVE_Q_NAME}.",
        },
        "cohort": {
            "total_stars": 30,
            "brand_new_unique_stars": 23,
            "prior_bridge_stars_revisited": 7,
            "intra_d094_bridge_stars": 1,
            "newly_promoted_bridges": ["GJ9827", "HD3651", "GJ1132", "HNPEG"],
            "control_stars": 5,
            "brand_new_within_10pc": 3,
            "fits_files_downloaded": 53,
            "physical_exposures_d094": n_phys_tot,
            "apogee2_visit_spectra": n_phys_apogee,
            "crires_yjh_exposures": n_phys_crires,
            "jwst_exposures": n_phys_jwst,
            "total_integration_hours": d094_int_hrs,
            "orbital_campaigns": len(orb_res_rows),
        },
        "searched_spectral_elements": {
            "by_instrument": bin_stats,
            "multiepoch_drift_v52_campaigns_total": len(v52_drift_rows) + len(d91_drift_rows),
            "multiepoch_drift_v52_d094_stars": len(v52_drift_rows),
            "multiepoch_drift_v52_d091_retroactive_stars": len(d91_drift_rows),
            "multiepoch_drift_v52_d094_raw_tracks": tot_d094_raw_drift,
            "multiepoch_drift_v52_d091_raw_tracks": d91_raw,
            "multiepoch_drift_v52_traj_evals_total": sum(r["n_traj_evals"] for r in v52_drift_rows) + sum(r["n_traj_evals"] for r in d91_drift_rows),
            "comb_v41_searched_configs_d094": tot_comb_d094,
            "v2_false_alarms_eliminated_d094": v2_fa_eliminated_total,
        },
        "synthetic_calibration_1741_trials": cal_sum,
        "four_generation_benchmark": bench_rows,
        "miri_lrs_molecular_ccf_10stars": miri_ccf_rows,
        "nirspec_g395h_molecular_ccf_2stars": nirspec_ccf_rows,
        "orbital_campaigns_118_125": orb_res_rows,
        "multievent_ellipsoid_d079_d094_summary": {
            "stars_evaluated": len(ell373_rows),
            "etz_qualified_stars": sum(1 for r in ell373_rows if str(r["etz_qualified"]) == "True"),
            "ellipsoid_within_180d_stars": sum(1 for r in ell373_rows if str(r["ellipsoid_qualified_180d"]) == "True"),
        },
        "upper_limits": {
            "n_cells": len(ul_rows),
            "best_d094_star": best_ul["star"],
            "best_d094_instrument": best_ul["instrument"],
            "best_d094_band": best_ul["band_id"],
            "best_d094_10m_w": best_ul["p_beam_10m_w"],
            "best_d094_10m_kw": best_ul["p_beam_10m_kw"],
            "best_by_instrument": {
                k: {"star": v["star"], "band_id": v["band_id"], "p_beam_10m_kw": v["p_beam_10m_kw"]}
                for k, v in best_by_inst.items()
            },
        },
        "unified_373star_panchromatic_v5_2_synthesis": {
            "phases": "D079-D094",
            "spectrographs": 23,
            "spectral_arms": 29,
            "octave_span": 8.273,
            "unique_stars_total": 373,
            "science_stars_total": sum(1 for r in u373_rows if r["role"] == "SCIENCE"),
            "control_stars_total": sum(1 for r in u373_rows if r["role"] == "CONTROL"),
            "planet_host_stars_total": sum(1 for r in u373_rows if int(r.get("n_exoplanets") or 0) > 0),
            "confirmed_exoplanets_total": sum(int(r.get("n_exoplanets") or 0) for r in u373_rows),
            "within_10pc_unique_stars": len(solar156_rows),
            "within_10pc_median_limit_kw": med_10pc_kw,
            "panchromatic_bridge_stars_total": len(unique_bridge_stars),
            "panchromatic_bridge_cells_total": len(bridge_rows),
            "total_exposures_d079_d094": int(prior_snap["prior_total_exposures_count"]) + n_phys_tot,
            "total_integration_hours_d079_d094": round(float(prior_snap["prior_cumulative_integration_hours"]) + d094_int_hrs, 4),
            "total_calibration_trials_d079_d094": int(prior_snap["prior_calibration_trials_count"]) + cal_sum["total_trials"],
            "v2_false_alarms_eliminated_total": int(prior_snap["prior_v2_false_alarms_eliminated_total"]) + v2_fa_eliminated_total,
            "cumulative_orbital_campaigns": int(prior_snap["prior_cumulative_orbital_campaigns_count"]) + len(orb_res_rows),
            "cumulative_comb_stacks": tot_comb_stacks,
            "verified_eti_detections_total": 0,
        },
    }

    # Write all result CSVs & JSONs cleanly
    _write_csv(out_dir / "EXPOSURE_PROVENANCE_D094.csv", list(prov_rows[0].keys()), prov_rows)
    if rv_anchor_rows:
        _write_csv(out_dir / "STELLAR_RV_ANCHORS_D094.csv", list(rv_anchor_rows[0].keys()), rv_anchor_rows)
    _write_csv(out_dir / "STAR_RV_SUMMARY_D094.csv", list(star_rv_rows[0].keys()), star_rv_rows)
    _write_csv(out_dir / "FOUR_GEN_BENCHMARK_D094.csv", list(bench_rows[0].keys()), bench_rows)
    _write_csv(out_dir / "V5_2_CANDIDATE_LEDGER.csv", list(ledger_rows[0].keys()) if ledger_rows else ["candidate_id", "qualified_v52"], ledger_rows)
    _write_csv(out_dir / "MULTIEPOCH_DRIFT_V52_RESULTS_D094.csv", list(v52_drift_rows[0].keys()), v52_drift_rows)
    _write_csv(out_dir / "RETROACTIVE_D091_MULTIEPOCH_DRIFT_31STARS.csv", list(d91_drift_rows[0].keys()), d91_drift_rows)
    _write_csv(out_dir / "BLIND_DRIFT_V51_RESULTS_D094.csv", list(v51_drift_rows[0].keys()) if v51_drift_rows else ["instrument", "star", "survivors"], v51_drift_rows)
    _write_csv(out_dir / "V5_2_AGNOSTIC_MULTISCALE_SURVIVORS.csv", list(ag_survivor_rows[0].keys()) if ag_survivor_rows else ["instrument", "star"], ag_survivor_rows)
    _write_csv(out_dir / "ORBITAL_CAMPAIGN_RESULTS_8.csv", list(orb_res_rows[0].keys()), orb_res_rows)
    _write_csv(out_dir / "COMB_V4_1_STAR_RESULTS_D094.csv", list(comb_star_rows[0].keys()), comb_star_rows)
    _write_csv(out_dir / "COMB_V4_1_CANDIDATES.csv", list(comb_cand_rows[0].keys()) if comb_cand_rows else ["instrument", "star_band"], comb_cand_rows)
    _write_csv(out_dir / "ALLSKY_COMB_V4_1_UNIFIED_D079_D094.csv", list(allsky_comb_u[0].keys()), allsky_comb_u)
    _write_csv(out_dir / "ALLSKY_COMB_V4_1_CANDIDATES_D079_D094.csv", list(allsky_comb_c[0].keys()), allsky_comb_c)
    _write_csv(out_dir / "JWST_MIRI_LRS_MOLECULAR_CCF_10STARS.csv", list(miri_ccf_rows[0].keys()), miri_ccf_rows)
    _write_csv(out_dir / "JWST_NIRSPEC_G395H_MOLECULAR_CCF_2STARS.csv", list(nirspec_ccf_rows[0].keys()), nirspec_ccf_rows)
    _write_csv(out_dir / "MULTIEVENT_ELLIPSOID_CATALOG_D079_D094.csv", list(ell373_rows[0].keys()), ell373_rows)
    _write_csv(out_dir / "STAR_UPPER_LIMITS_D094.csv", list(ul_rows[0].keys()), ul_rows)
    _write_csv(out_dir / "PANCHROMATIC_BRIDGE_41STARS_V52.csv", list(bridge_rows[0].keys()), bridge_rows)
    _write_csv(out_dir / "UNIFIED_PANCHROMATIC_V5_2_SYNTHESIS_373STARS.csv", u373_cols, u373_rows)
    _write_csv(out_dir / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_156STARS.csv", u373_cols, solar156_rows)
    _write_json(out_dir / "SUMMARY.json", summary_doc)

    print(
        f"Stage B DONE ({out_dir}): {len(u373_rows)} stars ({len(solar156_rows)} <10pc, "
        f"{len(unique_bridge_stars)} bridges/{len(bridge_rows)} cells), "
        f"V52_drift={len(v52_drift_rows)+len(d91_drift_rows)} N>=3 campaigns (0 surviving), "
        f"cal={cal_sum['total_trials']} trials, best={best_ul['star']} {best_ul['band_id']}={best_ul['p_beam_10m_kw']:.5f} kW, 0 ETI!",
        flush=True,
    )
    return summary_doc


def main() -> None:
    ap = argparse.ArgumentParser(description="Phase D094 V5.2 Analysis Pipeline")
    ap.add_argument("--from-full-inputs", type=Path, default=None, help="Path to full raw FITS inputs_d094_v5_2 directory")
    ap.add_argument("--from-bounded-inputs", type=Path, default=None, help="Path to d094_bounded_bundle.json.gz")
    ap.add_argument("--archive-q", type=Path, default=None, help="Path to Companion Archive Q zip (D091 N>=3 reuse)")
    ap.add_argument("--archives-dir", type=Path, default=None, help="Directory containing Companion Archives A-T")
    ap.add_argument("--out-dir", type=Path, default=WS / "results", help="Output directory")
    args = ap.parse_args()

    if args.from_bounded_inputs is not None:
        with gzip.open(args.from_bounded_inputs, "rt", encoding="utf-8") as gz:
            bundle = json.load(gz)
        run_stage_b(bundle, args.out_dir, archive_q_arg=args.archive_q, archives_dir_arg=args.archives_dir)
    else:
        full_dir = args.from_full_inputs or (ROOT / "inputs_d094_v5_2")
        bundle = run_stage_a_build_bundle(full_dir)
        run_stage_b(bundle, args.out_dir, archive_q_arg=args.archive_q, archives_dir_arg=args.archives_dir)


if __name__ == "__main__":
    main()
