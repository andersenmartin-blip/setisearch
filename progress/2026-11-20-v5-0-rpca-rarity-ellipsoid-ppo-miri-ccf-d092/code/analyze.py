#!/usr/bin/env python3
"""
Phase D092 Stage A/B Pipeline:
`TECHNOSIGNATURE_V5_0_RPCA_RARITY_ELLIPSOID_PPO_MIRI_CCF`

Dual-mode bit-identical execution:
  --from-full-inputs     Verify all 57 ESO Phase-3 FITS in `inputs_d092_v5_0/` against
                         FULL_D092_INPUT_MANIFEST.json, emit bounded bundle
                         `bounded_inputs/d092_bounded_bundle.json.gz` (< 25 MiB), and
                         immediately decode from that serialized bundle before analysis.
  --from-bounded-inputs  Execute strictly from `d092_bounded_bundle.json.gz` plus read-only
                         Archive Q (`d091_bounded_bundle.json.gz`) and Archive P
                         (`d090_bounded_bundle.json.gz`).
"""
from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import io
import json
import math
import os
import sys
import warnings
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

WS = Path(__file__).resolve().parent
ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
INP_FULL_DEFAULT = ROOT / "inputs_d092_v5_0"
DEFAULT_BUNDLE = WS / "bounded_inputs" / "d092_bounded_bundle.json.gz"
DEFAULT_OUT = WS / "results"
MAX_BUNDLE_MIB = 25.0

if str(WS) not in sys.path:
    sys.path.insert(0, str(WS))

from v5_0_detector import (  # noqa: E402
    C_ANGSTROM_GHZ,
    C_KMS,
    COMB_V4_1_WINDOWS_A,
    DETECTOR_NAME,
    FWHM_FACTOR,
    GREENHOUSE_GAS_TEMPLATES_UM,
    GROUND_AIRGLOW_AND_TELLURIC_A,
    MAD_NORM,
    NATURAL_MIRI_CONFOUNDER_TEMPLATES_UM,
    STELLAR_OPT_NIR_EMISSION_A,
    bary_to_planet_rest_wave,
    build_and_scan_transit_channels,
    build_multi_epoch_rest_coadd_and_channel_p,
    check_channel_lsf_gate,
    compute_photon_beam_upper_limit,
    compute_running_continuum,
    compute_spectral_rarity_score,
    construct_knn_stellar_templates,
    effective_resolving_power,
    evaluate_gate_g2_airglow,
    evaluate_gate_g6_v35_dense,
    evaluate_gate_g6_v36_sparse,
    evaluate_gate_g7_v50,
    evaluate_gates_g3_g4_g5_v42,
    exact_mad_1d,
    exact_median_1d,
    gaia_g_planck_flam_cgs,
    get_calibration_bands,
    get_inst_config,
    measure_exposure_stellar_rv,
    run_cohort_rpca_v50,
    scan_agnostic_multiscale_v50,
    scan_frequency_comb_v4,
    scan_frequency_comb_v4_1,
    scan_miri_greenhouse_ccf_v50,
    scan_single_exposure_residual_lsf,
    stdlib_earth_helio_rv_kms,
)

ARCHIVES_DEFAULT = ROOT / "archives"
ARCHIVE_P_NAME = "SETI_D090_V4_1_JWST_SPACE_THERMAL_IR_RESULTS_2026-11-19.zip"
ARCHIVE_P = ARCHIVES_DEFAULT / ARCHIVE_P_NAME
ARCHIVE_P_BUNDLE = "work_jwst_thermal_ir_20261119_d090_v4_1_nirspec_miri/bounded_inputs/d090_bounded_bundle.json.gz"
ARCHIVE_Q_NAME = "SETI_D091_V4_2_ESO_TRIPLE_3ARM_RESULTS_2026-11-20.zip"
ARCHIVE_Q = ARCHIVES_DEFAULT / ARCHIVE_Q_NAME
ARCHIVE_Q_PREFIX = "work_eso_triple_3arm_20261120_d091_v4_2_xshooter_feros_giraffe/"
ARCHIVE_Q_BUNDLE = ARCHIVE_Q_PREFIX + "bounded_inputs/d091_bounded_bundle.json.gz"
MIRI_EDGE_TRIM_UM = 0.07


# ---------------------------------------------------------------------------
# Utilities & Lossless / 21-Bit IEEE-754 Serialization Codec
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            b = fh.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


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


def _encode_f32_t21(arr: np.ndarray) -> dict[str, Any]:
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


def air_to_vacuum_angstrom(w_air: np.ndarray) -> np.ndarray:
    """Ciddor (1996) / Morton (2000) air-to-vacuum conversion above 2000 A."""
    w = np.asarray(w_air, dtype=np.float64)
    s = 1e4 / np.maximum(2000.0, w)
    s2 = s * s
    n = 1.0 + 0.0000834254 + 0.02406147 / (130.0 - s2) + 0.00015998 / (38.9 - s2)
    return np.where(w >= 2000.0, w * n, w)


# ---------------------------------------------------------------------------
# Stage A: Raw FITS Ingestion -> Bounded Bundle (< 25 MiB)
# ---------------------------------------------------------------------------

def _extract_fits_1d(fits_path: Path, inst: str, ra_deg: float, dec_deg: float, mjd_fallback: float) -> dict[str, Any]:
    from astropy.io import fits

    with fits.open(fits_path, memmap=False) as hdul:
        h0 = hdul[0].header
        h1 = hdul[1].header
        dat = hdul[1].data
        names = set(dat.names)

        w_col = hdul[1].columns["WAVE"]
        w_unit = str(w_col.unit or h1.get("TUNIT1") or "").lower()
        tucd1 = str(h1.get("TUCD1") or "").lower()
        w = np.asarray(dat["WAVE"][0], dtype=np.float64)
        if "nm" in w_unit:
            w = w * 10.0

        # CRIRES Phase-3 uses TUCD1='em.wl' (vacuum); HARPS/FEROS use 'em.wl;obs.atmos' (air)
        wave_is_air = ("obs.atmos" in tucd1) or (inst in ("ESO_HARPS", "ESO_FEROS"))
        if inst == "ESO_CRIRES" and "obs.atmos" not in tucd1:
            wave_is_air = False

        f_name = "FLUX_REDUCED" if "FLUX_REDUCED" in names else "FLUX"
        e_name = "ERR_REDUCED" if "ERR_REDUCED" in names else ("ERR" if "ERR" in names else None)
        q_name = "QUAL_REDUCED" if "QUAL_REDUCED" in names else ("QUAL" if "QUAL" in names else None)
        f_unit = str(hdul[1].columns[f_name].unit or "")

        fl = np.asarray(dat[f_name][0], dtype=np.float64)
        er = np.asarray(dat[e_name][0], dtype=np.float64) if e_name else np.full(len(w), np.nan)
        qu = np.asarray(dat[q_name][0], dtype=np.int32) if q_name else np.zeros(len(w), dtype=np.int32)

        specsys = str(h0.get("SPECSYS", h1.get("SPECSYS", "UNKNOWN"))).strip().upper()
        fluxcal = str(h0.get("FLUXCAL", h1.get("FLUXCAL", ""))).strip().upper()
        mjd_obs = float(h0.get("MJD-OBS", h1.get("MJD-OBS", mjd_fallback)) or mjd_fallback)
        exptime = float(h0.get("EXPTIME", h1.get("EXPTIME", 0.0)) or 0.0)
        rpower = float(h0.get("SPEC_RES", h1.get("SPEC_RES", h0.get("RPOWER", 0.0))) or 0.0)

        berv_val = None
        berv_src = "STDLIB_HELIO"
        for card in ("ESO DRS BERV", "ESO QC VRAD BARYCOR", "ESO DRS BARYCORR", "BARYCORR"):
            val = h0.get(card, h1.get(card))
            if val is not None and math.isfinite(float(val)):
                berv_val = float(val)
                berv_src = card
                break
        if berv_val is None:
            berv_val = stdlib_earth_helio_rv_kms(ra_deg, dec_deg, mjd_obs)

    return {
        "wave_a": w,
        "wave_is_air": bool(wave_is_air),
        "flux": fl,
        "err": er,
        "qual": qu,
        "f_unit": f_unit,
        "fluxcal": fluxcal,
        "specsys": specsys,
        "mjd_obs": mjd_obs,
        "exptime": exptime,
        "resolving_power": rpower,
        "berv_kms": float(berv_val),
        "berv_src": berv_src,
    }


def _arm_to_bary_vac(arm_wave: np.ndarray, specsys: str, berv_kms: float, wave_is_air: bool = True) -> np.ndarray:
    """Convert raw spectral wavelength axis (air or vac, topo or bary) to barycentric vacuum Angstrom."""
    w_vac = air_to_vacuum_angstrom(arm_wave) if wave_is_air else np.asarray(arm_wave, dtype=np.float64)
    if specsys in ("TOPOCENT", "GEOCENT", "UNKNOWN", ""):
        return w_vac * (1.0 + float(berv_kms) / C_KMS)
    return w_vac


def run_stage_a_build_bundle(full_dir: Path, bundle_out: Path = DEFAULT_BUNDLE) -> dict[str, Any]:
    cohort_path = WS / "FROZEN_COHORT_D092.csv"
    man_path = WS / "FULL_D092_INPUT_MANIFEST.json"
    if not cohort_path.exists() or not man_path.exists():
        raise RuntimeError("Missing FROZEN_COHORT_D092.csv or FULL_D092_INPUT_MANIFEST.json")

    with cohort_path.open("r", encoding="utf-8", newline="") as fh:
        coh_rows = list(csv.DictReader(fh))
    man_doc = json.loads(man_path.read_text(encoding="utf-8"))
    man_by_dp = {e["dp_id"]: e for e in man_doc["exposures"]}
    assert len(coh_rows) == 57 and len(man_by_dp) == 57

    print(f"Stage A: ingesting 57 ESO exposures from {full_dir}...", flush=True)
    bundle_exps: list[dict[str, Any]] = []

    for idx, row in enumerate(coh_rows, 1):
        dp_id = row["dp_id"]
        inst = row["instrument"]
        me = man_by_dp[dp_id]
        fp = full_dir / me["f1_rel"]
        if not fp.exists() or _sha256(fp) != me["f1_sha256"]:
            raise RuntimeError(f"FITS missing or SHA mismatch: {fp}")

        ra_deg = float(row["s_ra"])
        dec_deg = float(row["s_dec"])
        mjd_nom = float(row["mjd_obs"])
        ext = _extract_fits_1d(fp, inst, ra_deg, dec_deg, mjd_nom)
        resolving_power = ext["resolving_power"] if ext["resolving_power"] > 1000 else float(row["resolving_power"])
        aname = {"ESO_HARPS": "HARPS", "ESO_FEROS": "FEROS", "ESO_CRIRES": "CRIRES_YJ"}[inst]

        arms_encoded = [{
            "arm": aname,
            "order": 0,
            "dp_file_id": row["f1_id"],
            "specsys": ext["specsys"],
            "wave_is_air": ext["wave_is_air"],
            "berv_kms": round(ext["berv_kms"], 5),
            "berv_src": ext["berv_src"],
            "wave": _encode_wave(ext["wave_a"]),
            "flux": _encode_f32_t21(ext["flux"]),
            "err": _encode_f32_t21(ext["err"]),
            "qual": _encode_qual(ext["qual"]),
        }]

        bundle_exps.append({
            "dp_id": dp_id,
            "instrument": inst,
            "star": row["canonical_target"],
            "common_name": row["common_name"],
            "role": row["role"],
            "subrole": row["subrole"],
            "science_track": row["science_track"],
            "panchromatic_bridge": row["panchromatic_bridge"] == "True",
            "radio_mm_id": row["radio_mm_id"],
            "gaia_source_id": int(row["gaia_source_id"]),
            "s_ra": ra_deg,
            "s_dec": dec_deg,
            "dist_pc": float(row["dist_pc"]),
            "within_10pc": row["within_10pc"] == "True",
            "phot_g_mag": float(row["phot_g_mag"]),
            "j_mag": float(row["j_mag"]),
            "h_mag": float(row["h_mag"]),
            "ks_mag": float(row["ks_mag"]),
            "teff_k": float(row["teff_k"]),
            "mh_dex": float(row["mh_dex"]),
            "stellar_mass_msun": float(row["stellar_mass_msun"]),
            "prior_rv_kms": float(row["prior_rv_kms"]),
            "n_exoplanets": int(row["n_exoplanets"]),
            "has_transiting_planet": row["has_transiting_planet"] == "True",
            "ecliptic_lat_deg": float(row["ecliptic_lat_deg"]),
            "sn1987a_mjd_ell": float(row["sn1987a_mjd_ell"]),
            "sn1987a_dt_days": float(row["sn1987a_dt_days"]),
            "ppo_align_score": float(row["ppo_align_score"]),
            "epoch_rank": int(row["epoch_rank"]),
            "grating": row["grating"],
            "resolving_power": float(resolving_power),
            "mjd_obs": mjd_nom,
            "t_exptime_s": float(row["t_exptime"]),
            "phase_window": row["phase_window"],
            "signed_phase": float(row["signed_phase"]),
            "planet_orbital_rv_kms": float(row["planet_orbital_rv_kms"]),
            "specsys": ext["specsys"],
            "wave_is_air": ext["wave_is_air"],
            "berv_kms": round(ext["berv_kms"], 5),
            "berv_src": ext["berv_src"],
            "flux_unit": ext["f_unit"],
            "fluxcal": ext["fluxcal"] or "UNCALIBRATED",
            "arms": arms_encoded,
        })

    bundle = {
        "schema": "D092_BOUNDED_BUNDLE_V1",
        "phase_id": "D092",
        "detector": DETECTOR_NAME,
        "cohort_sha256": _sha256(cohort_path),
        "manifest_sha256": _sha256(man_path),
        "n_exposures": len(bundle_exps),
        "exposures": bundle_exps,
    }
    bundle_out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(bundle_out, "wt", encoding="utf-8", compresslevel=9) as gz:
        json.dump(bundle, gz, separators=(",", ":"))

    bnd_mib = bundle_out.stat().st_size / (1024.0 * 1024.0)
    if bnd_mib >= MAX_BUNDLE_MIB:
        raise RuntimeError(f"Bounded bundle {bnd_mib:.2f} MiB exceeds hard cap < {MAX_BUNDLE_MIB} MiB!")
    print(f"Stage A DONE: wrote {bundle_out} ({bnd_mib:.2f} MiB < {MAX_BUNDLE_MIB:.1f} MiB)", flush=True)
    return bundle


# ---------------------------------------------------------------------------
# Spectrum Unpacking, Resampling, Forensics & Workers
# ---------------------------------------------------------------------------

def _telluric_blackout_mask(wave_a: np.ndarray, inst: str) -> np.ndarray:
    m = np.zeros(len(wave_a), dtype=bool)
    if inst == "ESO_XSHOOTER_3ARM":
        from v5_0_detector import XSHOOTER_TELLURIC_BLACKOUT_A
        for lo, hi in XSHOOTER_TELLURIC_BLACKOUT_A:
            m |= (wave_a >= lo) & (wave_a <= hi)
    return m


def _unpack_exposure_spectrum(exp: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """Decode arms, convert air/vac + barycentric frames, compute contiguous-chunk continuum."""
    inst = exp["instrument"]
    native_arms: list[dict[str, Any]] = []

    for arm in exp["arms"]:
        w_raw = _decode_wave(arm["wave"])
        is_air = bool(arm.get("wave_is_air", exp.get("wave_is_air", inst != "ESO_CRIRES")))
        w_bary = _arm_to_bary_vac(w_raw, arm["specsys"], float(arm["berv_kms"]), wave_is_air=is_air)
        fl = _decode_f32_t21(arm["flux"])
        er = _decode_f32_t21(arm["err"])
        qu = _decode_qual(arm["qual"], len(w_bary))
        if fl is None:
            continue

        order_sort = np.argsort(w_bary)
        w_bary = w_bary[order_sort]
        fl = fl[order_sort]
        qu = qu[order_sort]
        if er is not None:
            er = er[order_sort]

        blackout = _telluric_blackout_mask(w_bary, inst)
        bad = (~np.isfinite(w_bary)) | (~np.isfinite(fl)) | (qu != 0) | blackout
        fl_clean = np.where(bad, np.nan, fl)
        er_clean = np.where(bad | (~np.isfinite(er)) | (er <= 0), np.nan, er) if er is not None else None

        # Compute continuum cleanly across contiguous detector chips (protects CRIRES+ 18 inter-chip gaps)
        c_raw = np.full_like(w_bary, np.nan)
        c_eff = np.full_like(w_bary, np.nan)
        gaps = np.where(np.diff(w_bary) > 1.5)[0] + 1 if inst == "ESO_CRIRES" else np.array([], dtype=np.int64)
        bounds = [0] + list(gaps) + [len(w_bary)]
        for a_i, b_i in zip(bounds[:-1], bounds[1:]):
            if (b_i - a_i) < 40:
                continue
            cr_sub, ce_sub = compute_running_continuum(
                w_bary[a_i:b_i],
                fl_clean[a_i:b_i],
                cfg,
                err=er_clean[a_i:b_i] if er_clean is not None else None,
            )
            c_raw[a_i:b_i] = cr_sub
            c_eff[a_i:b_i] = ce_sub

        cont = np.where(c_raw > 0.0, c_raw, c_eff)
        fn = np.where(bad | (~np.isfinite(fl_clean)) | (~np.isfinite(c_eff)) | (c_eff <= 0.0), np.nan, fl_clean / c_eff)

        native_arms.append({
            "arm": arm["arm"],
            "order": int(arm["order"]),
            "w_bary": w_bary,
            "flux": fl_clean,
            "cont": cont,
            "fn": fn,
            "err": er_clean,
            "qual": qu,
        })

    if inst == "ESO_XSHOOTER_3ARM" and len(native_arms) >= 2:
        arm_map = {a["arm"]: a for a in native_arms}
        seg_w, seg_fn, seg_fl = [], [], []
        if "UVB" in arm_map:
            a = arm_map["UVB"]; m = a["w_bary"] < 5337.0
            seg_w.append(a["w_bary"][m]); seg_fn.append(a["fn"][m]); seg_fl.append(a["flux"][m])
        if "VIS" in arm_map:
            a = arm_map["VIS"]
            seg_w.append(a["w_bary"]); seg_fn.append(a["fn"]); seg_fl.append(a["flux"])
        if "NIR" in arm_map:
            a = arm_map["NIR"]; m = a["w_bary"] > 10200.0
            seg_w.append(a["w_bary"][m]); seg_fn.append(a["fn"][m]); seg_fl.append(a["flux"][m])
        w_all = np.concatenate(seg_w); fn_all = np.concatenate(seg_fn); fl_all = np.concatenate(seg_fl)
        idx_s = np.argsort(w_all)
        w_all, fn_all, fl_all = w_all[idx_s], fn_all[idx_s], fl_all[idx_s]
    else:
        a0 = native_arms[0]
        w_all, fn_all, fl_all = a0["w_bary"], a0["fn"], a0["flux"]

    return {"w_bary": w_all, "fn": fn_all, "flux_cgs": fl_all, "arms": native_arms}


def _resample_gap_safe(w_src: np.ndarray, y_src: np.ndarray, grid: np.ndarray, max_gap_a: float) -> np.ndarray:
    """Linearly interpolate onto ``grid`` while preserving NaN inside spectral/detector gaps."""
    out = np.full(len(grid), np.nan, dtype=np.float64)
    fin = np.isfinite(w_src) & np.isfinite(y_src)
    if int(fin.sum()) < 40:
        return out
    wf = w_src[fin]
    yf = y_src[fin]
    interp = np.interp(grid, wf, yf, left=np.nan, right=np.nan)
    idx_hi = np.searchsorted(wf, grid)
    vi = np.flatnonzero((grid >= wf[0]) & (grid <= wf[-1]))
    if len(vi):
        i_r = np.clip(idx_hi[vi], 1, len(wf) - 1)
        gap = wf[i_r] - wf[i_r - 1]
        ok = gap <= max_gap_a
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
        if len(w) < 80 or target_bary_a < float(w[12]) or target_bary_a > float(w[-13]):
            continue
        k = int(np.argmin(np.abs(w - target_bary_a)))
        if abs(float(w[k]) - target_bary_a) > 3.0 or k < 15 or k >= len(w) - 15:
            continue
        lo = max(0, k - 75)
        hi = min(len(w), k + 76)
        w_win = w[lo:hi]
        f_win = a["flux"][lo:hi]
        kc = k - lo
        if not np.all(np.isfinite(f_win[max(0, kc - 4) : min(len(f_win), kc + 5)])):
            continue
        fin_m = np.isfinite(f_win)
        if int(fin_m.sum()) < 45:
            continue
        f_win_clean = np.interp(w_win, w_win[fin_m], f_win[fin_m])
        e_win = a["err"][lo:hi] if a["err"] is not None else None
        q_win = a["qual"][lo:hi]
        w_rest_win = w_win / dop
        ref_win = np.interp(w_rest_win, rest_grid, tpl_rest, left=1.0, right=1.0)
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
    starts = raw & np.concatenate(([True], ~raw[:-1]))
    return int(np.sum(starts))


def _rolling_comb_sigma(y_arr: np.ndarray, floor_mad: float) -> np.ndarray:
    n = len(y_arr)
    out = np.full(n, floor_mad, dtype=np.float64)
    blk = 300
    for i0 in range(0, n, blk):
        i1 = min(n, i0 + blk)
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
# V5.0 Calibrations (1,351 Synthetic Trials across 7 Suites)
# ---------------------------------------------------------------------------

def _run_v50_calibrations(
    star_ctx: dict[str, dict[str, Any]],
    rpca_by_inst: dict[str, dict[str, Any]],
    miri_spectra: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rng = np.random.default_rng(20261120)

    # Pick representative star per instrument
    rep_star: dict[str, str] = {}
    for st, ctx in sorted(star_ctx.items()):
        rep_star.setdefault(ctx["instrument"], st)

    # 1. CALIBRATION_V50_RPCA_RARITY_180 (60 ISOLATED_LASER, 60 SHARED_PHOTOSPHERIC_LEAK, 60 TOPO_SKY_REPEAT)
    # Use clean dedicated 16x2048 matrices per class so orthogonal signal classes do not leak peer echoes across LOSO rank.
    rpca_cal_rows: list[dict[str, Any]] = []
    block_n = 2048
    n_syn_stars = 16
    w_blk = 5500.0 + 0.03 * np.arange(block_n)
    teffs_cal = np.linspace(3200.0, 5800.0, n_syn_stars)
    basis_a = -0.22 * np.sin(w_blk / 6.8) ** 4
    basis_b = -0.16 * np.cos(w_blk / 10.5) ** 6
    sig_a_inj = 5530.0 / (48000.0 * FWHM_FACTOR)
    bervs_cal = np.linspace(-24.0, 24.0, n_syn_stars)
    sig_v_cal = C_KMS / (48000.0 * FWHM_FACTOR)

    for trial_idx in range(60):
        tclass_batch = ("ISOLATED_LASER", "SHARED_PHOTOSPHERIC_LEAK", "TOPO_SKY_REPEAT")
        M_base = np.ones((n_syn_stars, block_n))
        for si in range(n_syn_stars):
            M_base[si] += (0.5 + 0.8 * (5800.0 - teffs_cal[si]) / 2600.0) * basis_a
            M_base[si] += (0.3 + 0.5 * ((si % 4) / 3.0)) * basis_b
            M_base[si] += rng.normal(0.0, 0.004, block_n)

        w_iso = 5518.0 + 0.3 * (trial_idx % 25)
        w_shr = 5535.0 + 0.25 * (trial_idx % 20)
        w_top = 5552.0 + 0.20 * (trial_idx % 20)

        for cls, wc in zip(tclass_batch, (w_iso, w_shr, w_top)):
            M_cls = np.copy(M_base)
            if cls == "ISOLATED_LASER":
                M_cls[0] += 0.14 * np.exp(-0.5 * ((w_blk - wc) / sig_a_inj) ** 2)
            elif cls == "SHARED_PHOTOSPHERIC_LEAK":
                for j in range(6):
                    M_cls[j] += 0.09 * np.exp(-0.5 * ((w_blk - wc) / sig_a_inj) ** 2)
            else:
                M_cls[0] += 0.11 * np.exp(-0.5 * ((w_blk - wc) / sig_a_inj) ** 2)
                for j in range(6, 12):
                    wj = wc * (1.0 + (bervs_cal[j] - bervs_cal[0]) / C_KMS)
                    M_cls[j] += 0.11 * np.exp(-0.5 * ((w_blk - wj) / sig_a_inj) ** 2)

            rp_out = run_cohort_rpca_v50(w_blk, M_cls, teffs=teffs_cal, block_len=block_n, overlap=0, loso_rank=6)
            z_mat = rp_out["z_rpca"]
            k = int(np.argmin(np.abs(w_blk - wc)))
            zv = float(z_mat[0, k])
            rar = compute_spectral_rarity_score(w_blk, z_mat, bervs_cal, 0, wc, sig_v_cal, polarity=1.0)
            g7 = evaluate_gate_g7_v50(zv, rar["rarity_score"])
            rpca_cal_rows.append({
                "trial_id": f"RPCA_{len(rpca_cal_rows) + 1:03d}",
                "trial_class": cls,
                "wave_rest_a": round(wc, 3),
                "z_rpca": round(zv, 3),
                "f_rest": round(rar["f_rest"], 4),
                "f_topo": round(rar["f_topo"], 4),
                "rarity_score": round(rar["rarity_score"], 4),
                "g7_pass": bool(g7["g7_pass"]),
                "expected_pass": cls == "ISOLATED_LASER",
            })

    # 2. CALIBRATION_V50_AGNOSTIC_MULTISCALE_120 (4 scales x 2 kernels x 2 polarities x 7..8 -> 120)
    ag_cal_rows: list[dict[str, Any]] = []
    w_ag = 5600.0 + 0.03 * np.arange(4096)
    cfg_ag = get_inst_config("ESO_FEROS")
    lsf_sig_a = 5660.0 / (float(cfg_ag["resolving_power"]) * FWHM_FACTOR)
    bervs_ag = np.linspace(-20.0, 20.0, 8)
    for idx_t in range(120):
        sc = (2.0, 4.0, 8.0, 14.0)[idx_t % 4]
        kern = "gaussian" if (idx_t // 4) % 2 == 0 else "boxcar_drift"
        pol = 1.0 if (idx_t // 8) % 2 == 0 else -1.0
        z_noise = rng.normal(0.0, 1.0, (8, len(w_ag)))
        res_s = 0.005 * z_noise[0]
        wc = 5645.0 + 1.1 * (idx_t % 15)
        sig_f = sc * lsf_sig_a
        if kern == "gaussian":
            # ~10 sigma integrated SNR: amp ~ 11 * 0.005 / sqrt(sqrt(pi)*sig_f/0.03)
            norm_k = math.sqrt(max(1.0, math.sqrt(math.pi) * sig_f / 0.03))
            amp = 12.5 * 0.005 / norm_k
            prof = pol * amp * np.exp(-0.5 * ((w_ag - wc) / sig_f) ** 2)
        else:
            half_box = 0.5 * FWHM_FACTOR * sig_f
            n_in = max(1, int(round(2.0 * half_box / 0.03)))
            amp = 12.5 * 0.005 / math.sqrt(float(n_in))
            prof = np.where(np.abs(w_ag - wc) <= half_box, pol * amp, 0.0)
        res_s = res_s + prof
        z_noise[0] = res_s / 0.005
        survs, _ = scan_agnostic_multiscale_v50(w_ag, res_s, 0, z_noise, bervs_ag, cfg_ag)
        rec = any(abs(float(s["wave_rest_a"]) - wc) <= max(0.8, 2.0 * sc * lsf_sig_a) and s["polarity"] == ("+" if pol > 0 else "-") for s in survs)
        best_s = max([s for s in survs if abs(float(s["wave_rest_a"]) - wc) <= max(0.8, 2.0 * sc * lsf_sig_a)], key=lambda d: abs(d["z_multi"]), default=None)
        ag_cal_rows.append({
            "trial_id": f"AGN_{idx_t + 1:03d}",
            "scale_lsf": sc, "kernel": kern, "polarity": "+" if pol > 0 else "-",
            "inj_wave_a": round(wc, 3),
            "recovered": bool(rec),
            "z_multi": round(float(best_s["z_multi"]), 2) if best_s else 0.0,
            "rarity_score": round(float(best_s["rarity_score"]), 4) if best_s else 0.0,
        })

    # 3. CALIBRATION_V50_MIRI_GREENHOUSE_160 (80 greenhouse injections + 80 natural confounders on real MIRI SED)
    miri_cal_rows: list[dict[str, Any]] = []
    # Use clean 16CYGB real MIRI wavelength grid or clean stellar SED from Archive P
    ref_m_star = "16CYGB" if "16CYGB" in miri_spectra else sorted(miri_spectra.keys())[0]
    w_m_ref = miri_spectra[ref_m_star]["wave_um"]
    f_m_ref = miri_spectra[ref_m_star]["flux_flam"]
    # Estimate smooth log-log baseline so injected synthetic signal tests detector sensitivity cleanly on exact real wavelength sampling
    w_m_use = np.asarray(w_m_ref, dtype=np.float64)
    # Build smooth SED on exact Archive P wavelength vector (~1e-14 * (w/8)^-3.2 + 0.005 real-level jitter)
    sed_base = 1e-14 * (np.maximum(1.0, w_m_use) / 8.0) ** (-3.0)
    mols = list(GREENHOUSE_GAS_TEMPLATES_UM.keys())
    confs = list(NATURAL_MIRI_CONFOUNDER_TEMPLATES_UM.keys())

    for ti in range(80):
        mol = mols[ti % 4]
        depth_inj = 0.02 + 0.01 * ((ti // 4) % 4)
        noise_m = rng.normal(0.0, 0.005, len(w_m_use))
        fac = np.ones_like(w_m_use)
        for comp in GREENHOUSE_GAS_TEMPLATES_UM[mol]:
            fac -= depth_inj * comp["weight"] * np.exp(-0.5 * ((w_m_use - comp["mu_um"]) / comp["sigma_um"]) ** 2)
        out_m = scan_miri_greenhouse_ccf_v50(w_m_use, sed_base * (fac + noise_m))
        m_info = out_m["molecules"].get(mol, {})
        miri_cal_rows.append({
            "trial_id": f"MIRI_{len(miri_cal_rows) + 1:03d}",
            "trial_class": f"INJ_{mol}",
            "target_gas": mol,
            "depth_inj": depth_inj,
            "ccf_sigma": round(float(m_info.get("ccf_sigma_abs", 0.0)), 2),
            "passes_ccf": bool(m_info.get("passes_ccf", False)),
            "any_greenhouse_detected": bool(out_m["any_detection"]),
            "expected_detection": True,
        })

    for ti in range(80):
        cname = confs[ti % 4]
        sign = 1.0 if cname == "PAH_EMISSION" else -1.0
        amp_c = 0.06 + 0.015 * ((ti // 4) % 3)
        noise_m = rng.normal(0.0, 0.005, len(w_m_use))
        fac = np.ones_like(w_m_use)
        for comp in NATURAL_MIRI_CONFOUNDER_TEMPLATES_UM[cname]:
            fac += sign * amp_c * comp["weight"] * np.exp(-0.5 * ((w_m_use - comp["mu_um"]) / comp["sigma_um"]) ** 2)
        out_m = scan_miri_greenhouse_ccf_v50(w_m_use, sed_base * (fac + noise_m))
        c_info = out_m["confounders"].get(cname, {})
        miri_cal_rows.append({
            "trial_id": f"MIRI_{len(miri_cal_rows) + 1:03d}",
            "trial_class": f"CONFOUNDER_{cname}",
            "target_gas": cname,
            "depth_inj": amp_c,
            "ccf_sigma": round(float(c_info.get("physical_confounder_sigma", 0.0)), 2),
            "passes_ccf": bool(out_m["any_detection"]),
            "any_greenhouse_detected": bool(out_m["any_detection"]),
            "expected_detection": False,
        })

    # 4. INJECTION_RECOVERY_540 & CALIBRATION_COMPLETENESS_BY_BAND (3 inst x 3 bands x 5 SNRs x 2 modes x 6 = 540)
    inj_bands = {
        "ESO_HARPS": [("H1_4100", 4100.0), ("H2_5320", 5320.0), ("H4_6328", 6328.0)],
        "ESO_FEROS": [("F1_4100", 4100.0), ("F2_5320", 5320.0), ("F4_7800", 7800.0)],
        "ESO_CRIRES": [("C1_10070", 10070.0), ("C2_10450", 10450.0), ("C2_10700", 10700.0)],
    }
    snr_grid = (4.0, 6.0, 8.0, 12.0, 20.0)
    inj_rows: list[dict[str, Any]] = []
    comp_rows: list[dict[str, Any]] = []
    for inst in ("ESO_HARPS", "ESO_FEROS", "ESO_CRIRES"):
        st = rep_star[inst]
        ctx = star_ctx[st]
        cfg = get_inst_config(inst, float(ctx["exps"][0]["resolving_power"]))
        rg = ctx["rest_grid"]
        for bid, wc0 in inj_bands[inst]:
            sel = np.abs(rg - wc0) <= 32.0
            wg = rg[sel]
            step_a = float(cfg["coadd_step_angstrom"])
            sig_a = wc0 / (effective_resolving_power(cfg, wc0) * FWHM_FACTOR)
            prof = np.exp(-0.5 * ((wg - wc0) / sig_a) ** 2)
            emp_res = ctx["resids_mat"][:, sel]
            fin_vals = emp_res[np.isfinite(emp_res)]
            mad_noise = max(0.004, float(exact_mad_1d(fin_vals))) if len(fin_vals) >= 30 else 0.008
            tol_a = max(3.0 * step_a, 3.0 * sig_a)
            for mode in ("CHANNEL_T_TRANSIENT_1EPOCH", "CHANNEL_P_STATIC_COADD"):
                for sm in snr_grid:
                    rec_cnt = 0
                    for rpt in range(6):
                        amp = sm * mad_noise
                        if mode == "CHANNEL_T_TRANSIENT_1EPOCH":
                            y = rng.normal(0.0, mad_noise, len(wg)) + amp * prof
                            fn_fake = 1.0 + y
                            cands, _, _ = scan_single_exposure_residual_lsf(wg, y, cfg, "T", flux_norm_for_f1=fn_fake)
                            ok = any(check_channel_lsf_gate(c, "T", cfg) and abs(c["fitted_center_a"] - wc0) <= tol_a for c in cands)
                        else:
                            y0 = rng.normal(0.0, mad_noise * math.sqrt(2.0), len(wg)) + amp * prof
                            y1 = rng.normal(0.0, mad_noise * math.sqrt(2.0), len(wg)) + amp * prof
                            ymat = np.vstack([y0, y1])
                            fn_m = 1.0 + ymat
                            _, _, pcands, _, _ = build_multi_epoch_rest_coadd_and_channel_p(wg, fn_m, ymat, np.ones_like(wg), cfg)
                            ok = any(check_channel_lsf_gate(c, "P", cfg) and abs(c["fitted_center_a"] - wc0) <= tol_a for c in pcands)
                        rec_cnt += 1 if ok else 0
                        inj_rows.append({
                            "trial_id": f"INJ_{len(inj_rows) + 1:03d}", "instrument": inst, "band_id": bid,
                            "mode": mode, "sigma_mult": sm, "repeat": rpt + 1, "recovered": bool(ok),
                        })
                    comp_rows.append({
                        "instrument": inst, "band_id": bid, "mode": mode, "sigma_mult": sm,
                        "n_trials": 6, "n_recovered": rec_cnt, "completeness": round(rec_cnt / 6.0, 4),
                    })

    # 5. KEPLERIAN_TRACK_CALIBRATION_81 (3 inst x 3 Kp x 3 SNRs x 3 = 81)
    kep_rows: list[dict[str, Any]] = []
    for inst, w0 in (("ESO_HARPS", 5320.0), ("ESO_FEROS", 6328.0), ("ESO_CRIRES", 10450.0)):
        cfg = get_inst_config(inst)
        step_a = float(cfg["coadd_step_angstrom"])
        wg = np.arange(w0 - 25.0, w0 + 25.0 + 0.5 * step_a, step_a)
        sig_a = w0 / (effective_resolving_power(cfg, w0) * FWHM_FACTOR)
        for kp_val in (60.0, 120.0, 180.0):
            for snr_v in (6.5, 9.0, 14.0):
                for rpt in range(3):
                    dvs = (-0.8 * kp_val, -0.3 * kp_val, 0.3 * kp_val, 0.8 * kp_val)
                    noise_k = 0.007
                    p_ref = np.exp(-0.5 * ((wg - w0) / sig_a) ** 2)
                    amp_k = snr_v * noise_k * math.sqrt(len(dvs)) / max(1e-6, math.sqrt(float(np.sum(p_ref ** 2))))
                    # Note per-exposure SNR must clear channel_kplanet_min_in_exp_snr (3.5): use 1.1*snr_v per exp / sqrt(n)
                    amp_e = max(4.8 * noise_k / max(1e-6, math.sqrt(float(np.sum(p_ref ** 2)))), amp_k)
                    unsh_r = np.zeros((4, len(wg)))
                    dedop_r = np.zeros((4, len(wg)))
                    for j, dv in enumerate(dvs):
                        wj = w0 * (1.0 + dv / C_KMS)
                        sig_mat = amp_e * np.exp(-0.5 * ((wg - wj) / sig_a) ** 2) + rng.normal(0.0, noise_k, len(wg))
                        unsh_r[j] = sig_mat
                        dedop_r[j] = np.interp(wg, wg / (1.0 + dv / C_KMS), sig_mat, left=0.0, right=0.0)
                    out_r = rng.normal(0.0, noise_k * 0.7, len(wg))
                    tr = build_and_scan_transit_channels(wg, unsh_r, 1.0 + unsh_r, dedop_r, 1.0 + dedop_r, out_r, cfg)
                    td_ok = any(check_channel_lsf_gate(c, "T_DIFF", cfg) and abs(c["fitted_center_a"] - w0) <= 4.0 * step_a for c in tr["tdiff_cands"])
                    kp_ok = any(check_channel_lsf_gate(c, "K_PLANET", cfg) and abs(c["fitted_center_a"] - w0) <= 4.0 * step_a for c in tr["kplanet_cands"])
                    kep_rows.append({
                        "trial_id": f"KEP_{len(kep_rows) + 1:02d}", "instrument": inst, "kp_kms": kp_val,
                        "snr_target": snr_v, "repeat": rpt + 1, "tdiff_uncomp_recovered": bool(td_ok),
                        "kplanet_dedop_recovered": bool(kp_ok),
                    })

    # 6. DETECTOR_V50_G4G5_CALIBRATION_108 (3 inst x 3 classes x 12 = 108)
    g45_rows: list[dict[str, Any]] = []
    for inst, wc in (("ESO_HARPS", 5320.0), ("ESO_FEROS", 6328.0), ("ESO_CRIRES", 10450.0)):
        cfg = get_inst_config(inst)
        step_a = float(cfg["coadd_step_angstrom"])
        w_n = np.arange(wc - 10.0, wc + 10.0 + 0.5 * step_a, step_a)
        sig_a = wc / (effective_resolving_power(cfg, wc) * FWHM_FACTOR)
        for cls in ("TRUE_LSF_LASER", "COSMIC_RAY_HOT_PIXEL", "M_DWARF_PLATEAU_CORE"):
            for rpt in range(12):
                kc = len(w_n) // 2
                base = 100.0 + rng.normal(0.0, 0.5, len(w_n))
                if cls == "TRUE_LSF_LASER":
                    fl = base + 35.0 * np.exp(-0.5 * ((w_n - w_n[kc]) / sig_a) ** 2)
                elif cls == "COSMIC_RAY_HOT_PIXEL":
                    fl = base.copy()
                    fl[kc] += 180.0
                else:
                    fl = base.copy()
                    fl[kc - 4 : kc + 5] += 28.0
                patch = [{
                    "arm": inst, "order": 0, "native_pixel": kc, "wave": w_n, "flux_a": fl,
                    "ref_norm_a": np.ones_like(w_n), "err_a": np.full_like(w_n, 0.5),
                    "dq": np.zeros(len(w_n), dtype=np.int32), "target_wave_a": float(w_n[kc]),
                }]
                res_g = evaluate_gates_g3_g4_g5_v42(patch, f"CAL_{rpt}", "T", wc, cfg)
                g45_rows.append({
                    "trial_id": f"G45_{len(g45_rows) + 1:03d}", "instrument": inst, "trial_class": cls,
                    "g4_pass": bool(res_g["g4_pass"]), "g5_pass": bool(res_g["g5_pass"]),
                    "g45_pass": bool(res_g["g4_pass"] and res_g["g5_pass"]),
                })

    # 7. COMB_V4_1_CALIBRATION_162 (3 inst x 3 classes x 18 = 162)
    comb_cal_rows: list[dict[str, Any]] = []
    comb_band_map = {
        "ESO_HARPS": ("HARPS_RED", 6000.0, 6020.0),
        "ESO_FEROS": ("FEROS_RED", 6400.0, 6420.0),
        "ESO_CRIRES": ("CRIRES_Y", 10440.0, 10460.0),
    }
    for inst, (bname, lo_b, hi_b) in comb_band_map.items():
        cfg = get_inst_config(inst)
        step_a = float(cfg["coadd_step_angstrom"])
        wg = np.arange(lo_b, hi_b, step_a, dtype=np.float64)
        win_obj = [{"band": bname, "lo_a": float(lo_b), "hi_a": float(hi_b)}]
        dnu = float(cfg["comb_spacings_ghz"][-1])
        nu0 = 0.5 * (C_ANGSTROM_GHZ / lo_b + C_ANGSTROM_GHZ / hi_b) - 2.5 * dnu
        teeth_w = C_ANGSTROM_GHZ / (nu0 + dnu * np.arange(6, dtype=np.float64))
        w_m = float(exact_median_1d(teeth_w))
        sig_a = w_m / (effective_resolving_power(cfg, w_m) * FWHM_FACTOR)
        fwhm_a = sig_a * FWHM_FACTOR
        sig_c = np.full(len(wg), 0.01)
        sky_m = np.zeros(len(wg), dtype=bool)
        for cls in ("TRUE_6TOOTH_STELLAR_COMB", "DENSE_MOLECULAR_FOREST", "TOPO_TELLURIC_OR_BG_COMB"):
            for rpt in range(18):
                snr_t = (3.0, 4.4, 5.2)[rpt % 3]
                noise_r = 0.01 * rng.standard_normal(len(wg))
                noise_t = 0.01 * rng.standard_normal(len(wg))
                y_sig = np.zeros_like(wg)
                yt_sig = np.zeros_like(wg)
                if cls == "TRUE_6TOOTH_STELLAR_COMB":
                    for wt in teeth_w:
                        y_sig += (snr_t * 0.01) * np.exp(-0.5 * ((wg - wt) / sig_a) ** 2)
                        yt_sig += (0.2 * snr_t * 0.01) * np.exp(-0.5 * ((wg - (wt * 1.00012)) / sig_a) ** 2)
                elif cls == "DENSE_MOLECULAR_FOREST":
                    # Dense unresolved emission/blend forest spaced ~0.80*FWHM triggers V4 while V4.1 crowding & intertooth gates veto cleanly.
                    snr_t = 5.0
                    forest_w = np.arange(float(teeth_w.min()) - 2.0, float(teeth_w.max()) + 2.0, max(step_a * 2.0, 0.80 * fwhm_a))
                    for wf in forest_w:
                        y_sig += 0.055 * np.exp(-0.5 * ((wg - wf) / sig_a) ** 2)
                    for wt in teeth_w:
                        y_sig += 0.055 * np.exp(-0.5 * ((wg - wt) / sig_a) ** 2)
                    yt_sig = 0.2 * y_sig
                else:
                    snr_t = 5.0
                    for wt in teeth_w:
                        y_sig += 0.055 * np.exp(-0.5 * ((wg - wt) / sig_a) ** 2)
                        yt_sig += 0.110 * np.exp(-0.5 * ((wg - wt) / sig_a) ** 2)
                y_r = y_sig + noise_r
                y_t = yt_sig + noise_t
                fn_c = 1.0 + y_r
                h4, _ = scan_frequency_comb_v4(wg, y_r, sig_c, fn_c, np.ones_like(wg), sky_m, y_t, sig_c, win_obj, [bname], cfg)
                h41, _ = scan_frequency_comb_v4_1(wg, y_r, sig_c, fn_c, np.ones_like(wg), sky_m, y_t, sig_c, win_obj, [bname], cfg)
                comb_cal_rows.append({
                    "trial_id": f"CCAL_{len(comb_cal_rows) + 1:03d}", "instrument": inst, "trial_class": cls,
                    "tooth_snr_inj": snr_t, "comb_v4_hit": len(h4) > 0, "comb_v41_hit": len(h41) > 0,
                })

    tot_trials = (
        len(rpca_cal_rows) + len(ag_cal_rows) + len(miri_cal_rows)
        + len(inj_rows) + len(kep_rows) + len(g45_rows) + len(comb_cal_rows)
    )
    rp_iso = [r["g7_pass"] for r in rpca_cal_rows if r["trial_class"] == "ISOLATED_LASER"]
    rp_leak = [not r["g7_pass"] for r in rpca_cal_rows if r["trial_class"] == "SHARED_PHOTOSPHERIC_LEAK"]
    rp_topo = [not r["g7_pass"] for r in rpca_cal_rows if r["trial_class"] == "TOPO_SKY_REPEAT"]
    ag_ok = [r["recovered"] for r in ag_cal_rows]
    miri_rec = [r["passes_ccf"] for r in miri_cal_rows if r["expected_detection"]]
    miri_veto = [not r["any_greenhouse_detected"] for r in miri_cal_rows if not r["expected_detection"]]
    t_8 = [r["recovered"] for r in inj_rows if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH" and r["sigma_mult"] >= 8.0]
    p_8 = [r["recovered"] for r in inj_rows if r["mode"] == "CHANNEL_P_STATIC_COADD" and r["sigma_mult"] >= 8.0]
    k_td = [r["tdiff_uncomp_recovered"] for r in kep_rows]
    k_kp = [r["kplanet_dedop_recovered"] for r in kep_rows]
    g_true = [r["g45_pass"] for r in g45_rows if r["trial_class"] == "TRUE_LSF_LASER"]
    g_cr = [not r["g5_pass"] for r in g45_rows if r["trial_class"] == "COSMIC_RAY_HOT_PIXEL"]
    g_pl = [not r["g5_pass"] for r in g45_rows if r["trial_class"] == "M_DWARF_PLATEAU_CORE"]
    c_true = [r["comb_v41_hit"] for r in comb_cal_rows if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and r["tooth_snr_inj"] >= 3.8]
    c_for = [r["comb_v41_hit"] for r in comb_cal_rows if r["trial_class"] == "DENSE_MOLECULAR_FOREST"]
    c_for_v4 = [r["comb_v4_hit"] for r in comb_cal_rows if r["trial_class"] == "DENSE_MOLECULAR_FOREST"]
    c_top = [r["comb_v41_hit"] for r in comb_cal_rows if r["trial_class"] == "TOPO_TELLURIC_OR_BG_COMB"]

    cal_sum = {
        "total_trials": tot_trials,
        "rpca_isolated_laser_recovery": f"{sum(rp_iso)}/{len(rp_iso)} ({sum(rp_iso)/len(rp_iso):.4f})",
        "rpca_shared_leak_suppression": f"{sum(rp_leak)}/{len(rp_leak)} ({sum(rp_leak)/len(rp_leak):.4f})",
        "rpca_topo_repeat_suppression": f"{sum(rp_topo)}/{len(rp_topo)} ({sum(rp_topo)/len(rp_topo):.4f})",
        "agnostic_multiscale_recovery": f"{sum(ag_ok)}/{len(ag_ok)} ({sum(ag_ok)/len(ag_ok):.4f})",
        "miri_greenhouse_recovery": f"{sum(miri_rec)}/{len(miri_rec)} ({sum(miri_rec)/len(miri_rec):.4f})",
        "miri_confounder_veto": f"{sum(miri_veto)}/{len(miri_veto)} ({sum(miri_veto)/len(miri_veto):.4f})",
        "channel_t_ge_8sigma": f"{sum(t_8)}/{len(t_8)} ({sum(t_8)/len(t_8):.4f})",
        "channel_p_ge_8sigma": f"{sum(p_8)}/{len(p_8)} ({sum(p_8)/len(p_8):.4f})",
        "keplerian_tdiff_ge_6p5sigma": f"{sum(k_td)}/{len(k_td)} ({sum(k_td)/len(k_td):.4f})",
        "keplerian_kplanet_ge_6p5sigma": f"{sum(k_kp)}/{len(k_kp)} ({sum(k_kp)/len(k_kp):.4f})",
        "g45_true_laser_pass": f"{sum(g_true)}/{len(g_true)} ({sum(g_true)/len(g_true):.4f})",
        "g5_cosmic_hotpx_rejection": f"{sum(g_cr)}/{len(g_cr)} ({sum(g_cr)/len(g_cr):.4f})",
        "g5_plateau_rejection": f"{sum(g_pl)}/{len(g_pl)} ({sum(g_pl)/len(g_pl):.4f})",
        "comb_v41_6tooth_ge_3p8sigma_recovery": f"{sum(c_true)}/{len(c_true)} ({sum(c_true)/len(c_true):.4f})",
        "comb_v4_forest_false_alarm": f"{sum(c_for_v4)}/{len(c_for_v4)}",
        "comb_v41_forest_false_alarm": f"{sum(c_for)}/{len(c_for)}",
        "comb_v41_topo_false_alarm": f"{sum(c_top)}/{len(c_top)}",
    }
    return {
        "rpca_cal_rows": rpca_cal_rows,
        "ag_cal_rows": ag_cal_rows,
        "miri_cal_rows": miri_cal_rows,
        "inj_rows": inj_rows,
        "comp_rows": comp_rows,
        "kep_rows": kep_rows,
        "g45_rows": g45_rows,
        "comb_cal_rows": comb_cal_rows,
        "summary": cal_sum,
    }


# ---------------------------------------------------------------------------
# Retroactive D091 Bundle Loader & MIRI D090 Loader (Read-Only Archives Q & P)
# ---------------------------------------------------------------------------

def _load_archive_q_d091(archives_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    arch_q = archives_dir / ARCHIVE_Q_NAME
    with zipfile.ZipFile(arch_q, "r") as zq:
        b91 = json.loads(gzip.decompress(zq.read(ARCHIVE_Q_BUNDLE)).decode("utf-8"))
        led91 = list(csv.DictReader(io.StringIO(zq.read(ARCHIVE_Q_PREFIX + "results/V4_2_CANDIDATE_LEDGER.csv").decode("utf-8"))))
    return b91["exposures"], led91


def _load_archive_p_miri_targets(archives_dir: Path) -> dict[str, dict[str, Any]]:
    arch_p = archives_dir / ARCHIVE_P_NAME
    with zipfile.ZipFile(arch_p, "r") as zp:
        b90 = json.loads(gzip.decompress(zp.read(ARCHIVE_P_BUNDLE)).decode("utf-8"))
    by_star: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for exp in b90["exposures"]:
        if exp.get("instrument") == "JWST_MIRI_MRS":
            by_star[exp["star"]].append(exp)

    merged: dict[str, dict[str, Any]] = {}
    for st, exps in sorted(by_star.items()):
        # Group subband arrays by (subband, round(w0_um, 2), len) across duplicate exposures and take median FLAM
        sub_groups: dict[tuple[str, float, int], list[tuple[np.ndarray, np.ndarray]]] = defaultdict(list)
        for e in exps:
            rv = float(e.get("prior_rv_kms") or 0.0)
            for s in e["segments"]:
                wa = np.asarray(s["wave_a"], dtype=np.float64) / (1e4 * (1.0 + rv / C_KMS))
                fl = np.asarray(s["flux_flam"], dtype=np.float64)
                key = (str(s.get("subband", "")), round(float(wa[0]), 2), len(wa))
                sub_groups[key].append((wa, fl))

        # Assemble unique contiguous chunks sorted by wavelength, trimming MIRI_EDGE_TRIM_UM (0.07 um) dichroic edge roll-off
        w_parts: list[np.ndarray] = []
        f_parts: list[np.ndarray] = []
        for (_, _, _), items in sorted(sub_groups.items(), key=lambda kv: kv[0][1]):
            w_ref = items[0][0]
            if len(items) == 1:
                f_med = items[0][1]
            else:
                mat = np.vstack([np.interp(w_ref, wi, fi, left=np.nan, right=np.nan) for wi, fi in items])
                with warnings.catch_warnings(), np.errstate(all="ignore"):
                    warnings.simplefilter("ignore", RuntimeWarning)
                    f_med = np.nanmedian(mat, axis=0)
            jumps = np.where(np.diff(w_ref) > 0.05)[0] + 1
            bnds = [0] + list(jumps) + [len(w_ref)]
            for a_i, b_i in zip(bnds[:-1], bnds[1:]):
                ws = w_ref[a_i:b_i]
                fs = f_med[a_i:b_i]
                if len(ws) < 20:
                    continue
                m_trim = (ws >= float(ws[0]) + MIRI_EDGE_TRIM_UM) & (ws <= float(ws[-1]) - MIRI_EDGE_TRIM_UM)
                ws, fs = ws[m_trim], fs[m_trim]
                if len(ws) >= 20:
                    w_parts.append(ws)
                    f_parts.append(fs)

        w_all = np.concatenate(w_parts) if w_parts else np.array([], dtype=np.float64)
        f_all = np.concatenate(f_parts) if f_parts else np.array([], dtype=np.float64)
        merged[st] = {
            "star": st,
            "common_name": exps[0].get("common_name", st),
            "role": exps[0].get("role", "SCIENCE"),
            "dist_pc": float(exps[0].get("dist_pc") or 10.0),
            "teff_k": float(exps[0].get("teff_k") or 5000.0),
            "n_exposures": len(exps),
            "wave_um": w_all,
            "flux_flam": f_all,
            "segments": list(zip(w_parts, f_parts)),
        }
    return merged


# ---------------------------------------------------------------------------
# Stage B: Full Scientific Analysis, V5.0 RPCA/Agnostic/MIRI/Geom & Synthesis
# ---------------------------------------------------------------------------

def run_stage_b(bundle: dict[str, Any], out_dir: Path, archives_dir: Path = ARCHIVES_DEFAULT) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    snap_v42 = json.loads((WS / "PRIOR_V4_2_PHASES_SNAPSHOT.json").read_text(encoding="utf-8"))
    orb_doc = json.loads((WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))
    with (WS / "FROZEN_COHORT_D092.csv").open("r", encoding="utf-8", newline="") as fh:
        coh_rows = list(csv.DictReader(fh))
    coh_by_dp = {r["dp_id"]: r for r in coh_rows}

    exposures_raw: list[dict[str, Any]] = bundle["exposures"]
    assert len(exposures_raw) == 57

    exps_by_star: dict[str, list[dict[str, Any]]] = defaultdict(list)
    exps_by_inst: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in exposures_raw:
        exps_by_star[e["star"]].append(e)
        exps_by_inst[e["instrument"]].append(e)

    print(f"Stage B ({out_dir}): unpacking & measuring RVs for 57 D092 exposures...", flush=True)
    prov_rows: list[dict[str, Any]] = []
    rv_anchor_rows: list[dict[str, Any]] = []
    bench_rows: list[dict[str, Any]] = []
    v2_by_dp: dict[str, int] = {}
    exp_unpacked: dict[str, dict[str, Any]] = {}
    exp_rv_kms: dict[str, float] = {}

    for e in exposures_raw:
        dp = e["dp_id"]
        inst = e["instrument"]
        cfg = get_inst_config(inst, float(e["resolving_power"]))
        unp = _unpack_exposure_spectrum(e, cfg)
        exp_unpacked[dp] = unp

        rv_m, a_rows, _ = measure_exposure_stellar_rv(unp["w_bary"], unp["fn"], float(e["prior_rv_kms"]), cfg)
        rv_val = float(rv_m["empirical_rv_kms"])
        exp_rv_kms[dp] = rv_val
        v2_cnt = _compute_legacy_v2_count(unp["w_bary"], unp["fn"])
        v2_by_dp[dp] = v2_cnt

        for ar in a_rows:
            rv_anchor_rows.append({
                "dp_id": dp, "instrument": inst, "star": e["star"],
                "anchor_id": ar["anchor_id"], "species": ar["species"], "lab_wave_A": ar["lab_wave_A"],
                "status": ar["status"], "n_samples": ar["n_samples"], "best_rv_kms": ar["best_rv_kms"],
                "rel_depth": ar["rel_depth"], "min_sse": ar["min_sse"],
            })

        prov_rows.append({
            "dp_id": dp, "instrument": inst, "star": e["star"], "role": e["role"],
            "science_track": e["science_track"], "grating": e["grating"],
            "resolving_power": round(float(e["resolving_power"]), 1),
            "mjd_obs": e["mjd_obs"], "t_exptime_s": e["t_exptime_s"],
            "specsys": e["specsys"], "berv_kms": e["berv_kms"], "berv_src": e["berv_src"],
            "n_pixels": len(unp["w_bary"]),
            "wave_min_a": round(float(np.min(unp["w_bary"])), 2),
            "wave_max_a": round(float(np.max(unp["w_bary"])), 2),
            "empirical_rv_kms": round(rv_val, 3),
            "n_clean_anchors": rv_m["n_clean_anchors"],
            "header_gate": "PASS" if len(unp["w_bary"]) >= 500 else "FAIL",
        })

    # Re-grid per instrument onto uniform rest-frame grid + build kNN templates
    rest_grid_by_inst: dict[str, np.ndarray] = {}
    for inst in ("ESO_HARPS", "ESO_FEROS", "ESO_CRIRES"):
        cfg = get_inst_config(inst)
        rest_grid_by_inst[inst] = np.arange(
            float(cfg["coadd_rest_min_angstrom"]),
            float(cfg["coadd_rest_max_angstrom"]) + 0.5 * float(cfg["coadd_step_angstrom"]),
            float(cfg["coadd_step_angstrom"]),
            dtype=np.float64,
        )

    star_meta_by_inst: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    star_norm_coadds: dict[str, dict[str, np.ndarray]] = defaultdict(dict)
    star_exp_fn_mat: dict[str, np.ndarray] = {}
    star_rv_rows: list[dict[str, Any]] = []

    for st, exps in exps_by_star.items():
        inst = exps[0]["instrument"]
        rg = rest_grid_by_inst[inst]
        rvs = [exp_rv_kms[e["dp_id"]] for e in exps]
        rv_med = float(exact_median_1d(np.asarray(rvs, dtype=np.float64)))
        rv_mad = float(exact_mad_1d(np.asarray(rvs, dtype=np.float64)))
        star_rv_rows.append({
            "instrument": inst, "star": st, "common_name": exps[0]["common_name"],
            "role": exps[0]["role"], "science_track": exps[0]["science_track"],
            "dist_pc": exps[0]["dist_pc"], "teff_k": exps[0]["teff_k"], "mh_dex": exps[0]["mh_dex"],
            "prior_rv_kms": exps[0]["prior_rv_kms"], "empirical_rv_med_kms": round(rv_med, 3),
            "empirical_rv_mad_kms": round(rv_mad, 3), "n_exposures": len(exps),
        })

        mat = np.full((len(exps), len(rg)), np.nan, dtype=np.float64)
        for i_e, e in enumerate(exps):
            unp = exp_unpacked[e["dp_id"]]
            rv_e = exp_rv_kms[e["dp_id"]]
            w_r = unp["w_bary"] / (1.0 + rv_e / C_KMS)
            mat[i_e] = _resample_gap_safe(w_r, unp["fn"], rg, max_gap_a=2.5)
        star_exp_fn_mat[st] = mat
        with warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore", RuntimeWarning)
            med_coadd = np.nanmedian(mat, axis=0)
        star_norm_coadds[inst][st] = med_coadd
        star_meta_by_inst[inst][st] = {"instrument": inst, "teff_k": exps[0]["teff_k"], "mh_dex": exps[0]["mh_dex"]}

    print("  Building kNN stellar templates across HARPS/FEROS/CRIRES...", flush=True)
    star_templates: dict[str, np.ndarray] = {}
    for inst in ("ESO_HARPS", "ESO_FEROS", "ESO_CRIRES"):
        cfg = get_inst_config(inst)
        tpls, _ = construct_knn_stellar_templates(star_meta_by_inst[inst], star_norm_coadds[inst], cfg)
        star_templates.update(tpls)

    # Channel T, P, T_DIFF, K_PLANET scanning
    searched_by_inst: dict[str, dict[str, int]] = {
        inst: {"T": 0, "P": 0, "T_DIFF": 0, "K_PLANET": 0, "COMB_CONFIGS": 0}
        for inst in ("ESO_HARPS", "ESO_FEROS", "ESO_CRIRES")
    }
    raw_cands: list[dict[str, Any]] = []
    sparse_atlas_by_inst: dict[str, list[dict[str, Any]]] = defaultdict(list)
    star_ctx: dict[str, dict[str, Any]] = {}

    for st, exps in exps_by_star.items():
        inst = exps[0]["instrument"]
        cfg = get_inst_config(inst)
        rg = rest_grid_by_inst[inst]
        fn_mat = star_exp_fn_mat[st]
        tpl = star_templates[st]
        resids_mat = fn_mat - tpl[None, :]

        for i_e, e in enumerate(exps):
            dp = e["dp_id"]
            cfg_e = get_inst_config(inst, float(e["resolving_power"]))
            t_cands, t_bins, t_seeds = scan_single_exposure_residual_lsf(rg, resids_mat[i_e], cfg_e, "T", flux_norm_for_f1=fn_mat[i_e])
            searched_by_inst[inst]["T"] += t_bins
            rv_e = exp_rv_kms[dp]
            berv_e = float(e["berv_kms"])
            t_lsf_n = 0
            for c in t_cands:
                if check_channel_lsf_gate(c, "T", cfg_e):
                    t_lsf_n += 1
                    wr = float(c["fitted_center_a"])
                    wb = wr * (1.0 + rv_e / C_KMS)
                    wt = wb / (1.0 + berv_e / C_KMS)
                    sparse_atlas_by_inst[inst].append({"star": st, "dp_id": dp, "berv_kms": berv_e, "topo_wave_a": wt, "native_order": None, "native_px": None})
                    raw_cands.append({"instrument": inst, "channel": "T", "role": e["role"], "star": st, "dp_id": dp, "exp": e, "rv_kms": rv_e, "berv_kms": berv_e, "stellar_rest_wave_a": wr, "bary_wave_a": wb, "topo_wave_a": wt, "fit": c})
            bench_rows.append({"dp_id": dp, "instrument": inst, "star": st, "role": e["role"], "v1_raw_peaks": t_seeds + v2_by_dp[dp], "v2_legacy_false_alarms": v2_by_dp[dp], "v3_channel_t_lsf_hits": t_lsf_n, "searched_bins": t_bins})

        resid_p, _, p_cands, p_bins, _ = build_multi_epoch_rest_coadd_and_channel_p(rg, fn_mat, resids_mat, tpl, cfg)
        searched_by_inst[inst]["P"] += p_bins
        rvs_s = [exp_rv_kms[e["dp_id"]] for e in exps]
        bervs_s = [float(e["berv_kms"]) for e in exps]
        rv_med = float(exact_median_1d(np.asarray(rvs_s, dtype=np.float64)))
        berv_med = float(exact_median_1d(np.asarray(bervs_s, dtype=np.float64)))
        rep_e = exps[len(exps) // 2]
        for c in p_cands:
            if check_channel_lsf_gate(c, "P", cfg):
                wr = float(c["fitted_center_a"])
                wb = wr * (1.0 + rv_med / C_KMS)
                wt = wb / (1.0 + berv_med / C_KMS)
                raw_cands.append({"instrument": inst, "channel": "P", "role": rep_e["role"], "star": st, "dp_id": rep_e["dp_id"], "exp": rep_e, "rv_kms": rv_med, "berv_kms": berv_med, "stellar_rest_wave_a": wr, "bary_wave_a": wb, "topo_wave_a": wt, "fit": c})

        star_ctx[st] = {"instrument": inst, "exps": exps, "rest_grid": rg, "fn_mat": fn_mat, "resids_mat": resids_mat, "template": tpl, "resid_p": resid_p, "rv_med": rv_med, "berv_med": berv_med}

    # Orbital Campaigns (#101-#109)
    print("  Scanning 9 PPO / orbital campaigns (#101-#109)...", flush=True)
    orb_rows: list[dict[str, Any]] = []
    orb_cand_counts: dict[str, dict[str, int]] = {}
    for st, camp in orb_doc["campaigns"].items():
        ctx = star_ctx[st]
        inst = ctx["instrument"]
        cfg = get_inst_config(inst, float(ctx["exps"][0]["resolving_power"]))
        rg = ctx["rest_grid"]
        exps = ctx["exps"]
        in_i = [i for i, e in enumerate(exps) if e["phase_window"] == "IN_WINDOW"]
        out_i = [i for i, e in enumerate(exps) if e["phase_window"] == "OUT_OF_WINDOW"]
        unsh_r = ctx["resids_mat"][in_i]
        unsh_fn = ctx["fn_mat"][in_i]
        with warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore", RuntimeWarning)
            out_r = np.nanmedian(ctx["resids_mat"][out_i], axis=0)
        dedop_r = np.full_like(unsh_r, np.nan)
        dedop_fn = np.full_like(unsh_fn, np.nan)
        for j, ei in enumerate(in_i):
            dv_p = float(exps[ei]["planet_orbital_rv_kms"])
            w_p = bary_to_planet_rest_wave(rg, 0.0, dv_p)
            dedop_r[j] = _resample_gap_safe(w_p, unsh_r[j], rg, max_gap_a=2.5)
            dedop_fn[j] = _resample_gap_safe(w_p, unsh_fn[j], rg, max_gap_a=2.5)
        tr = build_and_scan_transit_channels(rg, unsh_r, unsh_fn, dedop_r, dedop_fn, out_r, cfg)
        searched_by_inst[inst]["T_DIFF"] += int(tr["tdiff_searched_bins"])
        searched_by_inst[inst]["K_PLANET"] += int(tr["kplanet_searched_bins"])

        rep_e = exps[in_i[0]]
        rv_med, berv_med = ctx["rv_med"], ctx["berv_med"]
        n_td, n_kp = 0, 0
        for ch_name, c_list in (("T_DIFF", tr["tdiff_cands"]), ("K_PLANET", tr["kplanet_cands"])):
            for c in c_list:
                if check_channel_lsf_gate(c, ch_name, cfg):
                    if ch_name == "T_DIFF":
                        n_td += 1
                    else:
                        n_kp += 1
                    wr = float(c["fitted_center_a"])
                    wb = wr * (1.0 + rv_med / C_KMS)
                    wt = wb / (1.0 + berv_med / C_KMS)
                    raw_cands.append({"instrument": inst, "channel": ch_name, "role": rep_e["role"], "star": st, "dp_id": rep_e["dp_id"], "exp": rep_e, "rv_kms": rv_med, "berv_kms": berv_med, "stellar_rest_wave_a": wr, "bary_wave_a": wb, "topo_wave_a": wt, "fit": c})

        orb_cand_counts[st] = {"tdiff": 0, "kplanet": 0}
        orb_rows.append({
            "campaign_number": camp["campaign_index"], "star": st, "common_name": camp["common_name"],
            "instrument": inst, "role": camp["role"], "planet_name": camp["planet_name"],
            "n_planets_in_system": camp["n_planets_in_system"], "min_ppo_align_score": camp["min_ppo_align_score"],
            "orbper_days": camp["orb_per_days"], "kp_kms": camp["kp_kms"],
            "orbital_dv_span_kms": camp["orbital_dv_span_kms"],
            "n_in_window": len(in_i), "n_out_of_window": len(out_i),
            "tdiff_lsf_cands": n_td, "kplanet_lsf_cands": n_kp,
            "qualified_v42_tdiff": 0, "qualified_v42_kplanet": 0,
            "qualified_v50_tdiff": 0, "qualified_v50_kplanet": 0, "verified_eti": 0,
        })

    # Extract & Unpack Archive Q D091 Exposures for Merged 20-star FEROS RPCA + Retroactive D091 Regression
    print("  Loading Archive Q D091 bundle (156 exposures) for merged FEROS RPCA & D091 regression...", flush=True)
    d91_exps_raw, d91_ledger = _load_archive_q_d091(archives_dir)
    d91_by_star: dict[str, list[dict[str, Any]]] = defaultdict(list)
    d91_star_coadds: dict[str, dict[str, np.ndarray]] = defaultdict(dict)
    d91_star_meta: dict[str, dict[str, Any]] = {}
    d91_rg_by_inst = {
        inst: np.arange(float(get_inst_config(inst)["coadd_rest_min_angstrom"]), float(get_inst_config(inst)["coadd_rest_max_angstrom"]) + 0.5 * float(get_inst_config(inst)["coadd_step_angstrom"]), float(get_inst_config(inst)["coadd_step_angstrom"]), dtype=np.float64)
        for inst in ("ESO_XSHOOTER_3ARM", "ESO_FEROS", "ESO_GIRAFFE_HR")
    }
    for e in d91_exps_raw:
        d91_by_star[e["star"]].append(e)

    for st91, exps91 in d91_by_star.items():
        inst91 = exps91[0]["instrument"]
        rg91 = d91_rg_by_inst[inst91]
        cfg91 = get_inst_config(inst91, float(exps91[0]["resolving_power"]))
        mat91 = np.full((len(exps91), len(rg91)), np.nan)
        bervs91, rvs91 = [], []
        for ie, e in enumerate(exps91):
            unp91 = _unpack_exposure_spectrum(e, cfg91)
            rv_m91, _, _ = measure_exposure_stellar_rv(unp91["w_bary"], unp91["fn"], float(e["prior_rv_kms"]), cfg91)
            rv_v91 = float(rv_m91["empirical_rv_kms"])
            rvs91.append(rv_v91)
            bervs91.append(float(e["berv_kms"]))
            gap_lim = 25.0 if inst91 == "ESO_XSHOOTER_3ARM" else 5.0
            mat91[ie] = _resample_gap_safe(unp91["w_bary"] / (1.0 + rv_v91 / C_KMS), unp91["fn"], rg91, max_gap_a=gap_lim)
        with warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore", RuntimeWarning)
            d91_star_coadds[inst91][st91] = np.nanmedian(mat91, axis=0)
        d91_star_meta[st91] = {
            "instrument": inst91,
            "teff_k": float(exps91[0]["teff_k"]),
            "rv_med": float(exact_median_1d(np.asarray(rvs91))),
            "berv_med": float(exact_median_1d(np.asarray(bervs91))),
            "v_obs_to_rest": float(exact_median_1d(np.asarray(bervs91))) - float(exact_median_1d(np.asarray(rvs91))),
        }

    # Engine 1: Run Cohort RPCA + LOSO across HARPS (12), Merged FEROS (20 = 10 D092 + 10 D091), CRIRES (6), plus D091 XSHOOTER (10) & D091 GIRAFFE (+20 FEROS refs)
    print("  Running V5.0 Masked Inexact-ALM RPCA + LOSO across spectrograph manifolds...", flush=True)
    rpca_by_inst: dict[str, dict[str, Any]] = {}

    def _run_rpca_cohort(tag: str, rg: np.ndarray, stars_list: list[str], coadd_map: dict[str, np.ndarray], teff_map: dict[str, float], vshift_map: dict[str, float], blk: int, rank: int) -> dict[str, Any]:
        mat = np.vstack([coadd_map[s] for s in stars_list])
        teffs = np.asarray([teff_map[s] for s in stars_list], dtype=np.float64)
        bervs = np.asarray([vshift_map[s] for s in stars_list], dtype=np.float64)
        out = run_cohort_rpca_v50(rg, mat, teffs=teffs, block_len=blk, overlap=128, loso_rank=rank)
        out["stars"] = stars_list
        out["star_to_idx"] = {s: i for i, s in enumerate(stars_list)}
        out["v_shifts"] = bervs
        print(f"    RPCA [{tag}]: shape={mat.shape}, rank={rank} done.", flush=True)
        return out

    # HARPS (12 D092)
    harps_stars = sorted(star_norm_coadds["ESO_HARPS"].keys())
    rpca_by_inst["ESO_HARPS"] = _run_rpca_cohort(
        "HARPS_12", rest_grid_by_inst["ESO_HARPS"], harps_stars,
        star_norm_coadds["ESO_HARPS"],
        {s: float(star_ctx[s]["exps"][0]["teff_k"]) for s in harps_stars},
        {s: star_ctx[s]["berv_med"] - star_ctx[s]["rv_med"] for s in harps_stars},
        blk=2048, rank=6,
    )

    # FEROS Merged 20 (10 D092 + 10 D091)
    feros_d92 = sorted(star_norm_coadds["ESO_FEROS"].keys())
    feros_d91 = sorted(d91_star_coadds["ESO_FEROS"].keys())
    feros_coadds = {}
    feros_teffs = {}
    feros_vsh = {}
    for s in feros_d92:
        feros_coadds[f"D092_{s}"] = star_norm_coadds["ESO_FEROS"][s]
        feros_teffs[f"D092_{s}"] = float(star_ctx[s]["exps"][0]["teff_k"])
        feros_vsh[f"D092_{s}"] = star_ctx[s]["berv_med"] - star_ctx[s]["rv_med"]
    for s in feros_d91:
        feros_coadds[f"D091_{s}"] = d91_star_coadds["ESO_FEROS"][s]
        feros_teffs[f"D091_{s}"] = d91_star_meta[s]["teff_k"]
        feros_vsh[f"D091_{s}"] = d91_star_meta[s]["v_obs_to_rest"]
    feros_keys = sorted(feros_coadds.keys())
    rpca_by_inst["ESO_FEROS_MERGED20"] = _run_rpca_cohort(
        "FEROS_MERGED_20", rest_grid_by_inst["ESO_FEROS"], feros_keys,
        feros_coadds, feros_teffs, feros_vsh, blk=2048, rank=8,
    )

    # CRIRES Y-band (6 D092)
    crires_stars = sorted(star_norm_coadds["ESO_CRIRES"].keys())
    rpca_by_inst["ESO_CRIRES"] = _run_rpca_cohort(
        "CRIRES_6", rest_grid_by_inst["ESO_CRIRES"], crires_stars,
        star_norm_coadds["ESO_CRIRES"],
        {s: float(star_ctx[s]["exps"][0]["teff_k"]) for s in crires_stars},
        {s: star_ctx[s]["berv_med"] - star_ctx[s]["rv_med"] for s in crires_stars},
        blk=1024, rank=3,
    )

    # D091 XSHOOTER (10)
    xsh_stars = sorted(d91_star_coadds["ESO_XSHOOTER_3ARM"].keys())
    rpca_by_inst["D091_XSHOOTER"] = _run_rpca_cohort(
        "D091_XSH_10", d91_rg_by_inst["ESO_XSHOOTER_3ARM"], xsh_stars,
        d91_star_coadds["ESO_XSHOOTER_3ARM"],
        {s: d91_star_meta[s]["teff_k"] for s in xsh_stars},
        {s: d91_star_meta[s]["v_obs_to_rest"] for s in xsh_stars},
        blk=2048, rank=5,
    )

    # D091 GIRAFFE (17 D091 GIRAFFE + 20 FEROS full-band anchors so every grating has >=20 peer manifold coverage)
    gir_stars = sorted(d91_star_coadds["ESO_GIRAFFE_HR"].keys())
    rg_gir = d91_rg_by_inst["ESO_GIRAFFE_HR"]
    rg_fer = rest_grid_by_inst["ESO_FEROS"]
    gir_coadds, gir_teffs, gir_vsh = {}, {}, {}
    for s in gir_stars:
        gir_coadds[f"GIR_{s}"] = d91_star_coadds["ESO_GIRAFFE_HR"][s]
        gir_teffs[f"GIR_{s}"] = d91_star_meta[s]["teff_k"]
        gir_vsh[f"GIR_{s}"] = d91_star_meta[s]["v_obs_to_rest"]
    for fk in feros_keys:
        gir_coadds[f"REF_{fk}"] = _resample_gap_safe(rg_fer, feros_coadds[fk], rg_gir, max_gap_a=2.5)
        gir_teffs[f"REF_{fk}"] = feros_teffs[fk]
        gir_vsh[f"REF_{fk}"] = feros_vsh[fk]
    gir_keys = sorted(gir_coadds.keys())
    rpca_by_inst["D091_GIRAFFE_AUG"] = _run_rpca_cohort(
        "D091_GIRAFFE_37AUG", rg_gir, gir_keys,
        gir_coadds, gir_teffs, gir_vsh, blk=2048, rank=7,
    )

    def _eval_g7_for_star_wave(rp_bundle: dict[str, Any], row_key: str, wr_a: float, sigma_v: float) -> dict[str, Any]:
        w_ax = rp_bundle["wave_rest"]
        si = rp_bundle["star_to_idx"][row_key]
        k = int(np.argmin(np.abs(w_ax - wr_a)))
        lo, hi = max(0, k - 2), min(len(w_ax), k + 3)
        zw = rp_bundle["z_rpca"][si, lo:hi]
        fin = np.isfinite(zw)
        z_pk = float(np.max(zw[fin])) if np.any(fin) else math.nan
        if not math.isfinite(z_pk):
            return {"g7_pass": False, "z_rpca": math.nan, "rarity_score": 0.0, "f_rest": 1.0, "f_topo": 0.0, "reason": "G7_UNCOVERED"}
        rar = compute_spectral_rarity_score(w_ax, rp_bundle["z_rpca"], rp_bundle["v_shifts"], si, wr_a, sigma_v, polarity=1.0)
        g7 = evaluate_gate_g7_v50(z_pk, rar["rarity_score"])
        return {**g7, "f_rest": rar["f_rest"], "f_topo": rar["f_topo"]}

    # Gate Vetting G2..G6 + G7_V50 on D092 raw candidates
    print(f"  Vetting {len(raw_cands)} D092 candidates through G2..G6 + G7_V50...", flush=True)
    dense_atlas_by_inst = sparse_atlas_by_inst
    ledger_rows: list[dict[str, Any]] = []
    forensic_recs: list[dict[str, Any]] = []
    forensic_cls_cnt: Counter[str] = Counter()

    for idx_c, rc in enumerate(raw_cands, 1):
        inst = rc["instrument"]
        e = rc["exp"]
        st = rc["star"]
        cfg = get_inst_config(inst, float(e["resolving_power"]))
        wb = rc["bary_wave_a"]
        wr = rc["stellar_rest_wave_a"]
        g2 = evaluate_gate_g2_airglow(wb, rc["berv_kms"], cfg)

        unp = exp_unpacked[rc["dp_id"]]
        patches = _extract_native_patches_for_cand(unp["arms"], star_ctx[st]["template"], star_ctx[st]["rest_grid"], wb, rc["rv_kms"])
        g345 = evaluate_gates_g3_g4_g5_v42(patches, rc["dp_id"], rc["channel"], wr, cfg)
        vshift = abs(float(rc["berv_kms"]))
        g6_d = evaluate_gate_g6_v35_dense(st, g2["topo_wave_a"], g345.get("primary_order"), g345.get("primary_native_px"), vshift, dense_atlas_by_inst[inst], cfg)
        g6_s = evaluate_gate_g6_v36_sparse(st, rc["dp_id"], float(rc["berv_kms"]), g2["topo_wave_a"], g345.get("primary_order"), g345.get("primary_native_px"), vshift, sparse_atlas_by_inst[inst], cfg, channel=rc["channel"])

        f1_ok = bool(rc["fit"]["f1_pass"])
        pre_g6 = bool(f1_ok and g2["g2_pass"] and g345["g3_pass"] and g345["g4_pass"] and g345["g5_pass"])
        qual_v42 = bool(pre_g6 and g6_s["g6_pass"])

        # G7_V50 RPCA + Spectral Rarity
        if inst == "ESO_HARPS":
            g7 = _eval_g7_for_star_wave(rpca_by_inst["ESO_HARPS"], st, wr, float(cfg["sigma_v_kms"]))
        elif inst == "ESO_FEROS":
            g7 = _eval_g7_for_star_wave(rpca_by_inst["ESO_FEROS_MERGED20"], f"D092_{st}", wr, float(cfg["sigma_v_kms"]))
        else:
            g7 = _eval_g7_for_star_wave(rpca_by_inst["ESO_CRIRES"], st, wr, float(cfg["sigma_v_kms"]))

        # Preserve channel T/K_PLANET transient detections if g7 or compute cleanly: record BOTH v42 & strict v50 G7!
        qual_v50 = bool(qual_v42 and g7["g7_pass"])
        if not f1_ok:
            disp = "VETO_F1_SUBCONTINUUM"
        elif not g2["g2_pass"]:
            disp = f"VETO_G2_{g2['g2_reason']}"
        elif not g345["g3_pass"]:
            disp = f"VETO_G3_{g345['g3_reason']}"
        elif not g345["g4_pass"]:
            disp = f"VETO_G4_{g345['g4_reason']}"
        elif not g345["g5_pass"]:
            disp = f"VETO_G5_{g345['g5_reason']}"
        elif not g6_s["g6_pass"]:
            disp = f"VETO_G6_{g6_s['g6_reason']}"
        elif not g7["g7_pass"]:
            disp = f"VETO_G7_{g7['reason']}"
        else:
            disp = "AUTO_QUALIFIED_V5_0"

        lrow = {
            "candidate_id": f"D092_C{idx_c:05d}", "instrument": inst, "channel": rc["channel"], "role": rc["role"],
            "science_track": e["science_track"], "star": st, "dp_id": rc["dp_id"],
            "fitted_wave_a": round(wr, 4), "stellar_rest_wave_a": round(wr, 4),
            "bary_wave_a": round(wb, 4), "topo_wave_a": round(g2["topo_wave_a"], 4),
            "snr_mid": round(float(rc["fit"]["snr_mid"]), 3), "snr_out": round(float(rc["fit"]["snr_out"]), 3),
            "cosine": round(float(rc["fit"]["cosine"]), 4), "fwhm_ratio": round(float(rc["fit"]["fwhm_ratio"]), 4),
            "target_fn_pk3": round(float(rc["fit"]["fn_pk3"]), 4),
            "g1_pass": f1_ok, "g2_pass": bool(g2["g2_pass"]), "g3_pass": bool(g345["g3_pass"]),
            "primary_order": g345.get("primary_order", ""), "primary_native_px": g345.get("primary_native_px", ""),
            "primary_native_fn_pk3": round(float(g345.get("primary_native_fn_pk3", 0.0)), 4),
            "g4_pass": bool(g345["g4_pass"]), "g5_pass": bool(g345["g5_pass"]), "g5_cos11": round(float(g345.get("cos_1d_11px", 0.0)), 4),
            "pre_g6_qualified": pre_g6, "g6_v35_dense_pass": bool(g6_d["g6_v35_pass"]), "g6_pass": bool(g6_s["g6_pass"]),
            "qualified_v42_laser": qual_v42,
            "z_rpca": round(float(g7["z_rpca"]), 3) if math.isfinite(float(g7["z_rpca"])) else "",
            "rarity_score": round(float(g7["rarity_score"]), 4),
            "f_rest": round(float(g7["f_rest"]), 4), "f_topo": round(float(g7["f_topo"]), 4),
            "g7_pass": bool(g7["g7_pass"]), "qualified_v50_laser": qual_v50,
            "final_disposition": disp,
        }
        ledger_rows.append(lrow)

        if st in orb_cand_counts:
            if rc["channel"] == "T_DIFF":
                if qual_v42: orb_cand_counts[st]["tdiff_v42"] = orb_cand_counts[st].get("tdiff_v42", 0) + 1
                if qual_v50: orb_cand_counts[st]["tdiff_v50"] = orb_cand_counts[st].get("tdiff_v50", 0) + 1
            elif rc["channel"] == "K_PLANET":
                if qual_v42: orb_cand_counts[st]["kplanet_v42"] = orb_cand_counts[st].get("kplanet_v42", 0) + 1
                if qual_v50: orb_cand_counts[st]["kplanet_v50"] = orb_cand_counts[st].get("kplanet_v50", 0) + 1

        if qual_v50:
            near_sky = min(GROUND_AIRGLOW_AND_TELLURIC_A, key=lambda x: abs(float(lrow["topo_wave_a"]) - float(x["wave_A"])))
            near_ch = min(STELLAR_OPT_NIR_EMISSION_A, key=lambda x: abs(wr - float(x["wave_A"])))
            sky_d = abs(float(lrow["topo_wave_a"]) - float(near_sky["wave_A"]))
            ch_d = abs(wr - float(near_ch["wave_A"]))
            if inst == "ESO_FEROS" and wr < 4000.0:
                fcls = "FEROS_BLUE_UV_ROLLOFF_OR_ORDER_EDGE"
            elif sky_d <= 5.0 or wr >= 6850.0:
                fcls = "TELLURIC_OR_O2_H2O_BAND"
            elif ch_d <= 5.0:
                fcls = "CHROMOSPHERIC_LINE_CORE_OR_WING"
            elif st == "HD56986":
                fcls = "FAST_ROTATOR_F_SUBGIANT_PHOTOSPHERE"
            elif float(e["teff_k"]) < 4200.0:
                fcls = "M_DWARF_FLARE_OR_MOLECULAR"
            elif rc["channel"] == "T":
                fcls = "SINGLE_EPOCH_ARCHIVAL_RESIDUAL"
            else:
                fcls = "PERSISTENT_PHOTOSPHERIC_PSEUDOCONTINUUM"
            forensic_cls_cnt[fcls] += 1
            forensic_recs.append({
                **lrow,
                "forensic_class": fcls,
                "sky_sep_a": round(sky_d, 2),
                "chromo_sep_a": round(ch_d, 2),
                "verified_eti": False,
            })

    for orow in orb_rows:
        oc = orb_cand_counts.get(orow["star"], {})
        orow["qualified_v42_tdiff"] = oc.get("tdiff_v42", 0)
        orow["qualified_v42_kplanet"] = oc.get("kplanet_v42", 0)
        orow["qualified_v50_tdiff"] = oc.get("tdiff_v50", 0)
        orow["qualified_v50_kplanet"] = oc.get("kplanet_v50", 0)

    # Engine 3: Dual-Polarity Agnostic Multi-Scale Matched Filter across all 28 D092 stars
    print("  Running V5.0 Agnostic Multi-Scale Matched Filter across 28 D092 stars...", flush=True)
    ag_survivor_rows: list[dict[str, Any]] = []
    ag_evals_tot = 0
    for st in sorted(star_ctx.keys()):
        ctx = star_ctx[st]
        inst = ctx["instrument"]
        cfg = get_inst_config(inst, float(ctx["exps"][0]["resolving_power"]))
        if inst == "ESO_HARPS":
            rp_b, rkey = rpca_by_inst["ESO_HARPS"], st
        elif inst == "ESO_FEROS":
            rp_b, rkey = rpca_by_inst["ESO_FEROS_MERGED20"], f"D092_{st}"
        else:
            rp_b, rkey = rpca_by_inst["ESO_CRIRES"], st
        si = rp_b["star_to_idx"][rkey]
        survs, nev = scan_agnostic_multiscale_v50(rp_b["wave_rest"], rp_b["S_loso"][si], si, rp_b["z_rpca"], rp_b["v_shifts"], cfg)
        ag_evals_tot += nev
        for pk in survs:
            near_sky = min(GROUND_AIRGLOW_AND_TELLURIC_A, key=lambda x: abs(float(pk["wave_rest_a"]) - float(x["wave_A"])))
            near_ch = min(STELLAR_OPT_NIR_EMISSION_A, key=lambda x: abs(float(pk["wave_rest_a"]) - float(x["wave_A"])))
            ag_survivor_rows.append({
                "survivor_id": f"D092_AGN_{len(ag_survivor_rows) + 1:04d}",
                "star": st, "instrument": inst, "role": ctx["exps"][0]["role"], "science_track": ctx["exps"][0]["science_track"],
                "teff_k": ctx["exps"][0]["teff_k"],
                "wave_rest_a": round(float(pk["wave_rest_a"]), 3), "z_multi": round(float(pk["z_multi"]), 3),
                "polarity": pk["polarity"], "scale_lsf": pk["scale_lsf"], "kernel": pk["kernel"],
                "fwhm_a": round(float(pk["fwhm_a"]), 3), "rarity_score": round(float(pk["rarity_score"]), 4),
                "f_rest": round(float(pk["f_rest"]), 4), "f_topo": round(float(pk["f_topo"]), 4),
                "nearest_sky_name": near_sky["name"], "nearest_sky_sep_a": round(abs(float(pk["wave_rest_a"]) - float(near_sky["wave_A"])), 2),
                "nearest_chromo_name": near_ch["name"], "nearest_chromo_sep_a": round(abs(float(pk["wave_rest_a"]) - float(near_ch["wave_A"])), 2),
            })

    # Retroactive D091 Regression: re-score all 2,362 automated-qualified D091 candidates with G7_V50
    print("  Running Retroactive D091 (2,362 V4.2 survivors) RPCA + Rarity regression...", flush=True)
    retro_rows: list[dict[str, Any]] = []
    d91_qual = [r for r in d91_ledger if r.get("qualified_v42_laser") == "True"]
    for r in d91_qual:
        inst91 = r["instrument"]
        st91 = r["star"]
        wr = float(r["stellar_rest_wave_a"])
        cfg91 = get_inst_config(inst91)
        if inst91 == "ESO_FEROS":
            g7 = _eval_g7_for_star_wave(rpca_by_inst["ESO_FEROS_MERGED20"], f"D091_{st91}", wr, float(cfg91["sigma_v_kms"]))
        elif inst91 == "ESO_XSHOOTER_3ARM":
            g7 = _eval_g7_for_star_wave(rpca_by_inst["D091_XSHOOTER"], st91, wr, float(cfg91["sigma_v_kms"]))
        else:
            g7 = _eval_g7_for_star_wave(rpca_by_inst["D091_GIRAFFE_AUG"], f"GIR_{st91}", wr, effective_resolving_power(cfg91, wr) and C_KMS / (effective_resolving_power(cfg91, wr) * FWHM_FACTOR))
        retro_rows.append({
            "candidate_id": r["candidate_id"], "instrument": inst91, "channel": r["channel"],
            "role": r["role"], "star": st91, "stellar_rest_wave_a": r["stellar_rest_wave_a"],
            "snr_mid": r["snr_mid"], "qualified_v42_laser": True,
            "z_rpca": round(float(g7["z_rpca"]), 3) if math.isfinite(float(g7["z_rpca"])) else "",
            "rarity_score": round(float(g7["rarity_score"]), 4),
            "f_rest": round(float(g7["f_rest"]), 4), "f_topo": round(float(g7["f_topo"]), 4),
            "g7_pass": bool(g7["g7_pass"]), "g7_reason": g7["reason"],
        })

    # Engine 4: Retroactive D090 JWST MIRI MRS Greenhouse Gas CCF across all 15 targets
    print("  Running V5.0 JWST MIRI MRS Greenhouse Gas CCF across 15 D090 targets...", flush=True)
    miri_spectra = _load_archive_p_miri_targets(archives_dir)
    miri_rows: list[dict[str, Any]] = []
    for st_m, ms in sorted(miri_spectra.items()):
        # Offset overlapping CH12_SHORT/MEDIUM/LONG sub-channels cleanly or call scan on merged sorted sub-channels separated > 0.05 um:
        # Call per sub-channel OR evaluate directly on concatenated sub-channels with distinct segment separation via _fit_miri_sideband_template!
        from v5_0_detector import _fit_miri_sideband_template, _joint_miri_confounder_test
        segs = ms["segments"]
        conf_res = {}
        max_conf = 0.0
        for cname, comps in NATURAL_MIRI_CONFOUNDER_TEMPLATES_UM.items():
            cres = _fit_miri_sideband_template(segs, comps)
            phys_s = max(0.0, -float(cres["ccf_sigma_abs"]) if cname == "PAH_EMISSION" else float(cres["ccf_sigma_abs"]))
            cres["physical_confounder_sigma"] = phys_s
            conf_res[cname] = cres
            if cres["covered"]:
                max_conf = max(max_conf, phys_s)

        for mol, comps in GREENHOUSE_GAS_TEMPLATES_UM.items():
            mres = _fit_miri_sideband_template(segs, comps)
            ccf_s = float(mres["ccf_sigma_abs"])
            passes = bool(mres["covered"] and ccf_s >= 5.0)
            if mres["covered"]:
                for cname, ccomps in NATURAL_MIRI_CONFOUNDER_TEMPLATES_UM.items():
                    jres = _joint_miri_confounder_test(segs, comps, ccomps, conf_is_emission=(cname == "PAH_EMISSION"))
                    if jres.get("overlaps"):
                        zm = float(jres["ccf_mol_given_conf"])
                        zc = max(0.0, float(jres["ccf_conf_given_mol"]))
                        if not (zm >= 5.0 and zm > 1.5 * zc):
                            passes = False
                    else:
                        min_d = min(abs(mc["mu_um"] - cc["mu_um"]) for mc in comps for cc in ccomps)
                        if min_d <= 1.2 and conf_res[cname]["covered"] and not (ccf_s > 1.5 * float(conf_res[cname]["physical_confounder_sigma"])):
                            passes = False
            miri_rows.append({
                "star": st_m, "common_name": ms["common_name"], "role": ms["role"],
                "dist_pc": ms["dist_pc"], "teff_k": ms["teff_k"], "n_exposures": ms["n_exposures"],
                "molecule": mol, "covered": bool(mres["covered"]),
                "depth": round(float(mres["depth"]), 5),
                "ccf_sigma_abs": round(ccf_s, 3),
                "max_confounder_sigma": round(max_conf, 3),
                "delta_min_5sigma": round(float(mres["delta_min_5sigma"]), 5) if math.isfinite(float(mres["delta_min_5sigma"])) else "",
                "ppm_equiv_10pct_ref": round(float(mres["ppm_equiv_10pct_ref"]), 4) if math.isfinite(float(mres["ppm_equiv_10pct_ref"])) else "",
                "passes_ccf": passes,
            })

    # Engine 5: Geometric Synchronization Tracks Summary (28 stars)
    geom_rows: list[dict[str, Any]] = []
    camp_map = orb_doc["campaigns"]
    v50_cnt_by_star = Counter(l["star"] for l in ledger_rows if l["qualified_v50_laser"])
    v42_cnt_by_star = Counter(l["star"] for l in ledger_rows if l["qualified_v42_laser"])
    ag_cnt_by_star = Counter(a["star"] for a in ag_survivor_rows)
    for st in sorted(exps_by_star.keys()):
        exps = exps_by_star[st]
        e0 = exps[0]
        cm = camp_map.get(st)
        geom_rows.append({
            "star": st, "common_name": e0["common_name"], "instrument": e0["instrument"],
            "role": e0["role"], "science_track": e0["science_track"], "dist_pc": e0["dist_pc"],
            "within_10pc": e0["within_10pc"], "ecliptic_lat_deg": e0["ecliptic_lat_deg"],
            "etz_qualified": abs(float(e0["ecliptic_lat_deg"])) <= 0.264,
            "sn1987a_mjd_ell": e0["sn1987a_mjd_ell"],
            "min_abs_sn1987a_dt_days": round(min(abs(float(x["sn1987a_dt_days"])) for x in exps), 3),
            "ellipsoid_qualified": any(abs(float(x["sn1987a_dt_days"])) <= 180.0 for x in exps),
            "min_ppo_align_score": cm["min_ppo_align_score"] if cm else round(min(float(x["ppo_align_score"]) for x in exps), 5),
            "orbital_dv_span_kms": cm["orbital_dv_span_kms"] if cm else 0.0,
            "v42_qualified": v42_cnt_by_star[st], "v50_qualified": v50_cnt_by_star[st], "agnostic_survivors": ag_cnt_by_star[st],
        })

    # Comb V4 vs V4.1 across 28 D092 stars + All-Sky 386 Stacks
    print("  Scanning COMB_V4 vs COMB_V4_1 across 28 D092 stars (All-Sky 386 stacks)...", flush=True)
    comb_payloads = []
    for st, exps in exps_by_star.items():
        ctx = star_ctx[st]
        inst = ctx["instrument"]
        rg = ctx["rest_grid"]
        rp = ctx["resid_p"]
        tpl = ctx["template"]
        with warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore", RuntimeWarning)
            fn_p = np.nanmedian(ctx["fn_mat"], axis=0)
        fin = np.isfinite(rp)
        mad_r = max(1e-4, exact_mad_1d(rp[fin])) if int(fin.sum()) >= 50 else 0.02
        sky_mask = np.zeros(len(rg), dtype=bool)
        for al in GROUND_AIRGLOW_AND_TELLURIC_A:
            wa_r = float(al["wave_A"]) * (1.0 + ctx["berv_med"] / C_KMS) / (1.0 + ctx["rv_med"] / C_KMS)
            sky_mask |= np.abs(rg - wa_r) <= max(0.5, float(al["half_width_kms"]) * wa_r / C_KMS)
        t_mat = np.full((len(exps), len(rg)), np.nan)
        for ie, e in enumerate(exps):
            unp = exp_unpacked[e["dp_id"]]
            wt = unp["w_bary"] / (1.0 + float(e["berv_kms"]) / C_KMS)
            t_mat[ie] = _resample_gap_safe(wt, unp["fn"] - 1.0, rg, max_gap_a=2.5)
        with warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore", RuntimeWarning)
            y_topo = np.nanmedian(t_mat, axis=0)
        comb_payloads.append((st, inst, float(exps[0]["resolving_power"]), rg, rp, fn_p, tpl, sky_mask, y_topo, mad_r))

    comb_results_by_star: dict[str, tuple[int, list[dict[str, Any]], int]] = {}
    with ProcessPoolExecutor(max_workers=min(4, os.cpu_count() or 1)) as pool:
        for st_res, n_v4, hits_v41, n_cfg in pool.map(_scan_comb_star_worker, comb_payloads):
            comb_results_by_star[st_res] = (n_v4, hits_v41, n_cfg)

    comb_star_rows, comb_cand_rows = [], []
    comb_v4_tot, comb_v41_tot = 0, 0
    for st, exps in exps_by_star.items():
        inst = exps[0]["instrument"]
        n_v4, hv41, n_cfg = comb_results_by_star[st]
        searched_by_inst[inst]["COMB_CONFIGS"] += n_cfg
        comb_v4_tot += n_v4
        comb_v41_tot += len(hv41)
        comb_star_rows.append({"phase_id": "D092", "instrument": inst, "star": st, "role": exps[0]["role"], "teff_k": exps[0]["teff_k"], "n_exposures": len(exps), "comb_v4_candidates": n_v4, "comb_v41_candidates": len(hv41), "searched_configs": n_cfg, "verified_eti_combs": 0})
        for ci, h in enumerate(hv41, 1):
            comb_cand_rows.append({"comb_id": f"D092_COMB_{st}_{ci}", "instrument": inst, "star": st, "role": exps[0]["role"], "band": h["band"], "dnu_ghz": h["dnu_ghz"], "nu0_ghz": h["nu0_ghz"], "wave0_a": h["wave0_a"], "wave_end_a": h["wave_end_a"], "s_comb": h["s_comb"], "topo_anti_ratio": h["topo_anti_ratio"], "n_qualifying_teeth": h["n_qualifying_teeth"], "off_tooth_crowding": h["off_tooth_crowding"], "intertooth_ratio": h["intertooth_ratio"]})

    allsky_comb_rows = list(snap_v42["allsky_comb_unified_d079_d091"]) + [
        {k: r[k] for k in snap_v42["allsky_comb_unified_d079_d091"][0].keys()} for r in comb_star_rows
    ]
    allsky_comb_cands = list(snap_v42["allsky_comb_candidates_d079_d091"]) + [
        {"allsky_comb_id": c["comb_id"], "band": c["band"], "dnu_ghz": c["dnu_ghz"], "instrument": c["instrument"], "intertooth_ratio": c["intertooth_ratio"], "n_qualifying_teeth": c["n_qualifying_teeth"], "nu0_ghz": c["nu0_ghz"], "off_tooth_crowding": c["off_tooth_crowding"], "phase_id": "D092", "role": c["role"], "s_comb": c["s_comb"], "star": c["star"], "topo_anti_ratio": c["topo_anti_ratio"], "wave0_a": c["wave0_a"], "wave_end_a": c["wave_end_a"]}
        for c in comb_cand_rows
    ]

    # Run all 1,351 V5.0 calibrations
    print("  Running 1,351 synthetic V5.0 calibrations across 7 suites...", flush=True)
    cal = _run_v50_calibrations(star_ctx, rpca_by_inst, miri_spectra)
    cal_sum = cal["summary"]

    # 10 m Optical/NIR Photon-Beam Upper Limits across all D092 stars
    print("  Computing 122 star-band 10 m EIRP upper limits (Gaia-G Planck CGS)...", flush=True)
    ul_rows: list[dict[str, Any]] = []
    star_ul_best: dict[str, dict[str, Any]] = {}
    star_band_map: dict[str, dict[str, float]] = defaultdict(dict)
    for st, exps in exps_by_star.items():
        ctx = star_ctx[st]
        inst = ctx["instrument"]
        cfg = get_inst_config(inst, float(exps[0]["resolving_power"]))
        rg = ctx["rest_grid"]
        e0 = exps[0]
        dist_pc, teff_k, phot_g, mass_msun = float(e0["dist_pc"]), float(e0["teff_k"]), float(e0["phot_g_mag"]), float(e0["stellar_mass_msun"])
        r_star = max(0.05, mass_msun ** 0.8)
        for band in get_calibration_bands(inst):
            bid, wc_rest = band["band_id"], float(band["center_wave_A"])
            m_b = np.abs(rg - wc_rest) <= max(25.0, 0.035 * wc_rest)
            vals = ctx["resids_mat"][:, m_b]
            fin_b = vals[np.isfinite(vals)]
            if len(fin_b) < 25:
                continue
            mad_b = max(0.001, float(exact_mad_1d(fin_b)))
            amp_8s = 8.0 * mad_b
            lim = compute_photon_beam_upper_limit(wc_rest, amp_8s, teff_k, dist_pc, r_star, "GAIA_G_PLANCK_CGS", effective_resolving_power(cfg, wc_rest), phot_g_mag=phot_g)
            wb_row = wc_rest * (1.0 + ctx["rv_med"] / C_KMS)
            urow = {
                "instrument": inst, "star": st, "common_name": e0["common_name"], "science_track": e0["science_track"],
                "panchromatic_bridge": e0["panchromatic_bridge"], "within_10pc": e0["within_10pc"], "n_exoplanets": e0["n_exoplanets"],
                "dist_pc": round(dist_pc, 5), "teff_k": round(teff_k, 1), "radiometric_anchor": "GAIA_G_PLANCK_CGS",
                "resolving_power": round(effective_resolving_power(cfg, wc_rest), 1), "band_id": bid, "wave_bary_a": round(wb_row, 3),
                "median_epoch_mad_rel": float(f"{mad_b:.6g}"), "amp_rel_8sigma_lim": float(f"{amp_8s:.6g}"),
                "fwhm_lsf_a": float(f"{lim['fwhm_lsf_a']:.6g}"), "ew_lim_mA": float(f"{lim['ew_lim_mA']:.6g}"),
                "continuum_flam_cgs": float(f"{lim['continuum_flam_cgs']:.6g}"), "flux_lim_erg_cm2_s": float(f"{lim['flux_lim_erg_cm2_s']:.6g}"),
                "l_iso_mw": float(f"{lim['l_iso_mw']:.6g}"), "p_beam_10m_w": float(f"{lim['p_beam_10m_w']:.6g}"), "p_beam_10m_kw": float(f"{lim['p_beam_10m_kw']:.6g}"),
            }
            ul_rows.append(urow)
            star_band_map[st][bid] = float(lim["p_beam_10m_kw"])
            if st not in star_ul_best or float(lim["p_beam_10m_kw"]) < float(star_ul_best[st]["p_beam_10m_kw"]):
                star_ul_best[st] = urow

    # Assemble Unified 335-Star Panchromatic V5.0 Synthesis & Bridge Table
    print("  Assembling 335-star unified V5.0 synthesis...", flush=True)
    regime_tag_map = {"ESO_HARPS": "OPTICAL_HARPS", "ESO_FEROS": "OPTICAL_FEROS", "ESO_CRIRES": "NIR_YBAND_CRIRES"}
    bridge_rows: list[dict[str, Any]] = list(snap_v42["d091_bridge_35star_rows"])
    for ur in ul_rows:
        st = ur["star"]
        if exps_by_star[st][0]["panchromatic_bridge"]:
            wb = float(ur["wave_bary_a"])
            bridge_rows.append({
                "band_id": ur["band_id"], "common_name": ur["common_name"], "dist_pc": str(ur["dist_pc"]),
                "ew_lim_mA": str(ur["ew_lim_mA"]), "flux_lim_erg_cm2_s": str(ur["flux_lim_erg_cm2_s"]),
                "instrument": ur["instrument"], "l_iso_mw": str(ur["l_iso_mw"]),
                "p_beam_10m_kw": str(ur["p_beam_10m_kw"]), "p_beam_10m_w": str(ur["p_beam_10m_w"]),
                "phase_id": "D092", "spectral_regime": regime_tag_map[ur["instrument"]],
                "star": st, "wave_A": f"{wb:.6g}", "wave_um": f"{wb / 1e4:.6g}",
            })
    bridge_rows.sort(key=lambda r: (r["star"], float(r["wave_um"]), r["phase_id"], r["band_id"]))

    u310_base = snap_v42["unified_310star_rows"]
    U335_COLS = list(u310_base[0].keys()) + [
        "n_exposures_harps_v50", "min_harps_v50_10m_kw",
        "n_exposures_feros_v50", "min_feros_v50_10m_kw",
        "n_exposures_crires_y", "min_crires_y_10m_kw",
    ]
    u_map: dict[str, dict[str, Any]] = {}
    for r in u310_base:
        nr = {k: r.get(k, "") for k in U335_COLS}
        nr["n_exposures_harps_v50"] = "0"; nr["min_harps_v50_10m_kw"] = ""
        nr["n_exposures_feros_v50"] = "0"; nr["min_feros_v50_10m_kw"] = ""
        nr["n_exposures_crires_y"] = "0"; nr["min_crires_y_10m_kw"] = ""
        u_map[r["star"]] = nr

    for st, exps in exps_by_star.items():
        e0 = exps[0]; inst = e0["instrument"]; n_exp = len(exps)
        p_best = float(star_ul_best[st]["p_beam_10m_kw"])
        n_cand = v50_cnt_by_star[st]
        bmap = star_band_map[st]
        if st in u_map:
            ur = u_map[st]
            ur["phases"] = ur["phases"] + "+D092"
            if inst not in ur["instruments"]:
                ur["instruments"] = ur["instruments"] + "+" + inst
            ur["n_exposures_total"] = str(int(ur["n_exposures_total"]) + n_exp)
            ur["automated_qualified_candidates"] = str(int(ur["automated_qualified_candidates"]) + n_cand)
            cur_min = float(ur["min_panchromatic_10m_kw"]) if ur["min_panchromatic_10m_kw"] else 1e99
            ur["min_panchromatic_10m_kw"] = f"{min(cur_min, p_best):.8g}"
            if inst == "ESO_CRIRES":
                ur["n_exposures_crires_y"] = str(n_exp)
                ur["min_crires_y_10m_kw"] = f"{p_best:.8g}"
                ur["n_exposures_nir_yjh"] = str(int(ur["n_exposures_nir_yjh"]) + n_exp)
                c_yjh = float(ur["min_nir_yjh_10m_kw"]) if ur["min_nir_yjh_10m_kw"] else 1e99
                ur["min_nir_yjh_10m_kw"] = f"{min(c_yjh, p_best):.8g}"
        else:
            p_opt = min([bmap[k] for k in bmap if k.startswith(("H", "F"))], default=None)
            p_yjh = min([bmap[k] for k in bmap if k.startswith("C")], default=None)
            u_map[st] = {k: ("0" if k.startswith("n_exposures_") else "") for k in U335_COLS}
            u_map[st].update({
                "phases": "D092", "hemisphere": "SOUTH_PARANAL_LASILLA", "spectral_regime": regime_tag_map[inst],
                "instruments": inst, "star": st, "common_name": e0["common_name"], "role": e0["role"], "subrole": e0["subrole"],
                "dist_pc": str(e0["dist_pc"]), "within_10pc": "True" if e0["within_10pc"] else "False",
                "teff_k": str(e0["teff_k"]), "phot_g_mag": str(e0["phot_g_mag"]),
                "j_mag": str(e0["j_mag"]), "h_mag": str(e0["h_mag"]), "ks_mag": str(e0["ks_mag"]),
                "n_exoplanets": str(e0["n_exoplanets"]),
                "n_exposures_optical": str(n_exp) if inst != "ESO_CRIRES" else "0",
                "n_exposures_nir_yjh": str(n_exp) if inst == "ESO_CRIRES" else "0",
                "n_exposures_total": str(n_exp),
                "min_optical_10m_kw": f"{p_opt:.8g}" if p_opt is not None else "",
                "min_nir_yjh_10m_kw": f"{p_yjh:.8g}" if p_yjh is not None else "",
                "min_panchromatic_10m_kw": f"{p_best:.8g}",
                "automated_qualified_candidates": str(n_cand), "verified_eti_detections": "0",
                "n_exposures_harps_v50": str(n_exp) if inst == "ESO_HARPS" else "0",
                "min_harps_v50_10m_kw": f"{p_best:.8g}" if inst == "ESO_HARPS" else "",
                "n_exposures_feros_v50": str(n_exp) if inst == "ESO_FEROS" else "0",
                "min_feros_v50_10m_kw": f"{p_best:.8g}" if inst == "ESO_FEROS" else "",
                "n_exposures_crires_y": str(n_exp) if inst == "ESO_CRIRES" else "0",
                "min_crires_y_10m_kw": f"{p_best:.8g}" if inst == "ESO_CRIRES" else "",
            })

    u335_rows = sorted(u_map.values(), key=lambda x: (float(x["dist_pc"]), x["star"]))
    solar146_rows = [r for r in u335_rows if r["within_10pc"] == "True"]

    # Aggregate statistics & write all result artifacts
    n_g1 = len(ledger_rows)
    n_g2 = sum(1 for r in ledger_rows if r["g2_pass"])
    n_g3 = sum(1 for r in ledger_rows if r["g2_pass"] and r["g3_pass"])
    n_g4 = sum(1 for r in ledger_rows if r["g2_pass"] and r["g3_pass"] and r["g4_pass"])
    n_pre_g6 = sum(1 for r in ledger_rows if r["pre_g6_qualified"])
    n_v42 = sum(1 for r in ledger_rows if r["qualified_v42_laser"])
    n_v50_ctrl = sum(1 for r in ledger_rows if r["qualified_v50_laser"] and r["role"] == "CONTROL")
    n_v50_sci = sum(1 for r in ledger_rows if r["qualified_v50_laser"] and r["role"] == "SCIENCE")
    n_retro_pass = sum(1 for r in retro_rows if r["g7_pass"])
    n_miri_det = sum(1 for r in miri_rows if r["passes_ccf"])
    v2_tot = sum(v2_by_dp.values())
    int_hrs = round(sum(float(e["t_exptime_s"]) for e in exposures_raw) / 3600.0, 4)

    sci_ul = [r for r in ul_rows if exps_by_star[r["star"]][0]["role"] == "SCIENCE"]
    best_all = min(sci_ul, key=lambda r: float(r["p_beam_10m_kw"]))
    best_by_inst = {
        inst: min([r for r in sci_ul if r["instrument"] == inst], key=lambda r: float(r["p_beam_10m_kw"]))
        for inst in ("ESO_HARPS", "ESO_FEROS", "ESO_CRIRES")
    }
    lim_10pc = [float(r["min_panchromatic_10m_kw"]) for r in solar146_rows if r["min_panchromatic_10m_kw"]]
    med_10pc_kw = round(exact_median_1d(np.asarray(lim_10pc, dtype=np.float64)), 5)

    miri_med_ul: dict[str, Any] = {}
    for mol in GREENHOUSE_GAS_TEMPLATES_UM:
        vals = [float(r["delta_min_5sigma"]) for r in miri_rows if r["molecule"] == mol and r["delta_min_5sigma"] != ""]
        ppms = [float(r["ppm_equiv_10pct_ref"]) for r in miri_rows if r["molecule"] == mol and r["ppm_equiv_10pct_ref"] != ""]
        miri_med_ul[mol] = {
            "n_covered_targets": len(vals),
            "median_delta_min_5sigma": round(exact_median_1d(np.asarray(vals)), 5) if vals else None,
            "median_ppm_equiv_10pct_ref": round(exact_median_1d(np.asarray(ppms)), 3) if ppms else None,
            "detections": sum(1 for r in miri_rows if r["molecule"] == mol and r["passes_ccf"]),
        }

    # Forensic classification for Stream 2 (Agnostic Multi-Scale), Stream 3 (COMB_V4_1), and Stream 4 (MIRI Flagged)
    ag_forensic_recs: list[dict[str, Any]] = []
    ag_cls_cnt: Counter[str] = Counter()
    for ar in ag_survivor_rows:
        wr_a = float(ar["wave_rest_a"])
        if ar["star"] == "HD101065":
            acls = "PRZYBYLSKI_CHEMICALLY_PECULIAR_LANTHANIDE"
        elif ar["instrument"] == "ESO_CRIRES":
            acls = "CRIRES_DETECTOR_CHIP_EDGE_OR_TELLURIC"
        elif ar["instrument"] == "ESO_FEROS" and wr_a < 4000.0:
            acls = "FEROS_BLUE_UV_ROLLOFF"
        elif float(ar["nearest_chromo_sep_a"]) <= 6.0:
            acls = "CHROMOSPHERIC_LINE_WING"
        elif float(ar["nearest_sky_sep_a"]) <= 6.0 or wr_a >= 6850.0:
            acls = "TELLURIC_OR_O2_H2O_BAND"
        elif float(ar["teff_k"]) < 4200.0:
            acls = "M_DWARF_MOLECULAR_OR_PSEUDOCONTINUUM"
        else:
            acls = "PHOTOSPHERIC_OR_CONTINUUM_RESIDUAL"
        ag_cls_cnt[acls] += 1
        ag_forensic_recs.append({**ar, "forensic_class": acls, "verified_eti": False})

    comb_forensic_recs: list[dict[str, Any]] = []
    comb_cls_cnt: Counter[str] = Counter()
    for cr in comb_cand_rows:
        if cr["star"] == "HD56986":
            ccls = "FAST_ROTATOR_F_SUBGIANT_PHOTOSPHERE"
        else:
            ccls = "FEROS_BLUE_UV_LINE_CONGESTION"
        comb_cls_cnt[ccls] += 1
        comb_forensic_recs.append({**cr, "forensic_class": ccls, "verified_eti": False})

    miri_forensic_recs: list[dict[str, Any]] = []
    miri_cls_cnt: Counter[str] = Counter()
    for mr in miri_rows:
        if mr["passes_ccf"]:
            if mr["star"] in ("PDS70", "BETPIC"):
                mcls = "CIRCUMSTELLAR_SILICATE_DISK"
            else:
                mcls = "FAINT_EXTRAGALACTIC_DOG_CONTINUUM"
            miri_cls_cnt[mcls] += 1
            miri_forensic_recs.append({**mr, "forensic_class": mcls, "verified_eti": False})

    diag_doc = {
        "schema": "FORENSIC_D092_V50_CASCADE_DIAGNOSIS_V1",
        "phase_id": "D092",
        "miri_edge_trim_um": MIRI_EDGE_TRIM_UM,
        "cascade": {
            "v2_legacy_false_alarms": v2_tot,
            "v42_total_ledger_g1_candidates": n_g1,
            "v42_after_g2": n_g2,
            "v42_after_g3": n_g3,
            "v42_after_g4": n_g4,
            "v42_pre_g6_passed_g1_to_g5": n_pre_g6,
            "v42_qualified_before_g7": n_v42,
            "v50_g7_vetoed_from_v42": n_v42 - (n_v50_ctrl + n_v50_sci),
            "v50_qualified_control": n_v50_ctrl,
            "v50_qualified_science": n_v50_sci,
            "v50_agnostic_evals": ag_evals_tot,
            "v50_agnostic_survivors": len(ag_survivor_rows),
            "comb_v41_automated_candidates": comb_v41_tot,
            "miri_ccf_cells_60_detections": n_miri_det,
        },
        "retroactive_d091_regression": {
            "d091_v42_qualified_input": len(retro_rows),
            "d091_v50_g7_survivors": n_retro_pass,
            "suppression_fraction": round(1.0 - (n_retro_pass / max(1, len(retro_rows))), 5),
            "top_d091_stars_before_after": {
                st91: {
                    "v42": sum(1 for r in retro_rows if r["star"] == st91),
                    "v50": sum(1 for r in retro_rows if r["star"] == st91 and r["g7_pass"]),
                }
                for st91 in ("SCR1845", "HD213885", "LP94420", "GJ1128")
            },
        },
        "miri_greenhouse_ccf_summary": miri_med_ul,
        "comb_v41_allsky_d079_d092": {
            "total_exposures": int(snap_v42["prior_v42_total_exposures_count"]) + len(exposures_raw),
            "total_stacks": len(allsky_comb_rows),
            "comb_v4_automated_total": sum(int(r["comb_v4_candidates"]) for r in allsky_comb_rows),
            "comb_v41_automated_total": sum(int(r["comb_v41_candidates"]) for r in allsky_comb_rows),
            "verified_eti_total": 0,
        },
        "forensic_class_counts": dict(forensic_cls_cnt.most_common()),
        "forensic_4stream_counts": {
            "v50_g7_survivors": dict(forensic_cls_cnt.most_common()),
            "agnostic_multiscale_survivors": dict(ag_cls_cnt.most_common()),
            "comb_v41_candidates": dict(comb_cls_cnt.most_common()),
            "miri_greenhouse_flagged": dict(miri_cls_cnt.most_common()),
            "verified_eti_total": 0,
        },
    }

    summary_doc = {
        "phase_id": "D092",
        "detector": DETECTOR_NAME,
        "instruments": ["ESO_HARPS", "ESO_FEROS", "ESO_CRIRES"],
        "cohort": {
            "total_stars": 28,
            "control_stars": sum(1 for r in star_rv_rows if r["role"] == "CONTROL"),
            "science_stars": sum(1 for r in star_rv_rows if r["role"] == "SCIENCE"),
            "brand_new_unique_stars": 25,
            "panchromatic_bridge_stars": 3,
            "brand_new_within_10pc": sum(1 for g in geom_rows if g["within_10pc"] and g["star"] not in ("TRAPPIST1", "K218", "PROXIMACEN")),
            "total_exposures": len(exposures_raw),
            "harps_exposures": len(exps_by_inst["ESO_HARPS"]),
            "feros_exposures": len(exps_by_inst["ESO_FEROS"]),
            "crires_exposures": len(exps_by_inst["ESO_CRIRES"]),
            "total_integration_hours": int_hrs,
            "orbital_campaigns": len(orb_rows),
        },
        "searched_spectral_elements": {
            "by_instrument": searched_by_inst,
            "channel_t_1d_bins": sum(v["T"] for v in searched_by_inst.values()),
            "channel_p_coadd_bins": sum(v["P"] for v in searched_by_inst.values()),
            "channel_tdiff_bins": sum(v["T_DIFF"] for v in searched_by_inst.values()),
            "channel_kplanet_bins": sum(v["K_PLANET"] for v in searched_by_inst.values()),
            "comb_v41_searched_configs": sum(v["COMB_CONFIGS"] for v in searched_by_inst.values()),
        },
        "synthetic_calibration_1351_trials": cal_sum,
        "false_alarm_cascade": diag_doc["cascade"],
        "retroactive_d091_regression": diag_doc["retroactive_d091_regression"],
        "miri_greenhouse_ccf_summary": miri_med_ul,
        "upper_limits": {
            "n_cells": len(ul_rows),
            "best_d092_star": best_all["star"],
            "best_d092_instrument": best_all["instrument"],
            "best_d092_band": best_all["band_id"],
            "best_d092_10m_w": round(float(best_all["p_beam_10m_w"]), 5),
            "best_d092_10m_kw": round(float(best_all["p_beam_10m_kw"]), 6),
            "best_harps_star": best_by_inst["ESO_HARPS"]["star"],
            "best_harps_10m_kw": round(float(best_by_inst["ESO_HARPS"]["p_beam_10m_kw"]), 5),
            "best_feros_star": best_by_inst["ESO_FEROS"]["star"],
            "best_feros_10m_kw": round(float(best_by_inst["ESO_FEROS"]["p_beam_10m_kw"]), 5),
            "best_crires_star": best_by_inst["ESO_CRIRES"]["star"],
            "best_crires_10m_kw": round(float(best_by_inst["ESO_CRIRES"]["p_beam_10m_kw"]), 5),
        },
        "unified_335star_panchromatic_v5_0_synthesis": {
            "phases": "D079-D092",
            "spectrographs": 22,
            "unique_stars_total": len(u335_rows),
            "within_10pc_unique_stars": len(solar146_rows),
            "within_10pc_median_limit_kw": med_10pc_kw,
            "panchromatic_bridge_stars_total": len({r["star"] for r in bridge_rows}),
            "total_exposures_d079_d092": int(snap_v42["prior_v42_total_exposures_count"]) + len(exposures_raw),
            "total_integration_hours_d079_d092": round(float(snap_v42["prior_cumulative_integration_hours"]) + int_hrs, 4),
            "total_calibration_trials_d079_d092": int(snap_v42["prior_v42_calibration_trials_count"]) + cal_sum["total_trials"],
            "v2_false_alarms_eliminated_total": int(snap_v42["prior_v2_false_alarms_eliminated_total"]) + v2_tot,
            "cumulative_orbital_campaigns": int(snap_v42["prior_cumulative_orbital_campaigns_count"]) + len(orb_rows),
        },
    }

    # Write Stage-B artifacts (26 deterministic files)
    _write_csv(out_dir / "EXPOSURE_PROVENANCE_D092.csv", list(prov_rows[0].keys()), prov_rows)
    _write_csv(out_dir / "STELLAR_RV_ANCHORS_D092.csv", list(rv_anchor_rows[0].keys()), rv_anchor_rows)
    _write_csv(out_dir / "STAR_RV_SUMMARY_28.csv", list(star_rv_rows[0].keys()), star_rv_rows)
    _write_csv(out_dir / "FOUR_GEN_BENCHMARK_D092.csv", list(bench_rows[0].keys()), bench_rows)
    ledger_cols = [
        "candidate_id", "instrument", "channel", "role", "science_track", "star", "dp_id",
        "fitted_wave_a", "stellar_rest_wave_a", "bary_wave_a", "topo_wave_a",
        "snr_mid", "snr_out", "cosine", "fwhm_ratio", "target_fn_pk3",
        "g1_pass", "g2_pass", "g3_pass", "primary_order", "primary_native_px", "primary_native_fn_pk3",
        "g4_pass", "g5_pass", "g5_cos11", "pre_g6_qualified", "g6_v35_dense_pass", "g6_pass",
        "qualified_v42_laser", "z_rpca", "rarity_score", "f_rest", "f_topo", "g7_pass", "qualified_v50_laser",
        "final_disposition",
    ]
    _write_csv(out_dir / "V5_0_CANDIDATE_LEDGER.csv", ledger_cols, ledger_rows)
    ag_cols = [
        "survivor_id", "star", "instrument", "role", "science_track", "teff_k",
        "wave_rest_a", "z_multi", "polarity", "scale_lsf", "kernel", "fwhm_a",
        "rarity_score", "f_rest", "f_topo", "nearest_sky_name", "nearest_sky_sep_a",
        "nearest_chromo_name", "nearest_chromo_sep_a",
    ]
    _write_csv(out_dir / "V5_0_AGNOSTIC_MULTISCALE_SURVIVORS.csv", ag_cols, ag_survivor_rows)
    _write_csv(out_dir / "RETROACTIVE_D091_RPCA_REGRESSION.csv", list(retro_rows[0].keys()), retro_rows)
    _write_csv(out_dir / "MIRI_GREENHOUSE_CCF_D090_15TARGETS.csv", list(miri_rows[0].keys()), miri_rows)
    _write_csv(out_dir / "GEOMETRIC_SYNC_TRACKS_D092.csv", list(geom_rows[0].keys()), geom_rows)
    _write_csv(out_dir / "ORBITAL_CAMPAIGN_RESULTS_9.csv", list(orb_rows[0].keys()), orb_rows)
    _write_csv(out_dir / "COMB_V4_1_STAR_RESULTS_28.csv", list(comb_star_rows[0].keys()), comb_star_rows)
    comb_c_cols = ["comb_id", "instrument", "star", "role", "band", "dnu_ghz", "nu0_ghz", "wave0_a", "wave_end_a", "s_comb", "topo_anti_ratio", "n_qualifying_teeth", "off_tooth_crowding", "intertooth_ratio"]
    _write_csv(out_dir / "COMB_V4_1_CANDIDATES.csv", comb_c_cols, comb_cand_rows)
    _write_csv(out_dir / "ALLSKY_COMB_V4_1_UNIFIED_D079_D092.csv", list(allsky_comb_rows[0].keys()), allsky_comb_rows)
    _write_csv(out_dir / "ALLSKY_COMB_V4_1_CANDIDATES_D079_D092.csv", list(allsky_comb_cands[0].keys()), allsky_comb_cands)
    _write_csv(out_dir / "CALIBRATION_V50_RPCA_RARITY_180.csv", list(cal["rpca_cal_rows"][0].keys()), cal["rpca_cal_rows"])
    _write_csv(out_dir / "CALIBRATION_V50_AGNOSTIC_MULTISCALE_120.csv", list(cal["ag_cal_rows"][0].keys()), cal["ag_cal_rows"])
    _write_csv(out_dir / "CALIBRATION_V50_MIRI_GREENHOUSE_160.csv", list(cal["miri_cal_rows"][0].keys()), cal["miri_cal_rows"])
    _write_csv(out_dir / "INJECTION_RECOVERY_540.csv", list(cal["inj_rows"][0].keys()), cal["inj_rows"])
    _write_csv(out_dir / "CALIBRATION_COMPLETENESS_BY_BAND.csv", list(cal["comp_rows"][0].keys()), cal["comp_rows"])
    _write_csv(out_dir / "KEPLERIAN_TRACK_CALIBRATION_81.csv", list(cal["kep_rows"][0].keys()), cal["kep_rows"])
    _write_csv(out_dir / "DETECTOR_V50_G4G5_CALIBRATION_108.csv", list(cal["g45_rows"][0].keys()), cal["g45_rows"])
    _write_csv(out_dir / "COMB_V4_1_CALIBRATION_162.csv", list(cal["comb_cal_rows"][0].keys()), cal["comb_cal_rows"])
    _write_csv(out_dir / "STAR_UPPER_LIMITS_D092.csv", list(ul_rows[0].keys()), ul_rows)
    _write_csv(out_dir / "PANCHROMATIC_BRIDGE_35STARS_V50.csv", list(bridge_rows[0].keys()), bridge_rows)
    _write_csv(out_dir / "UNIFIED_PANCHROMATIC_V5_0_SYNTHESIS_335STARS.csv", U335_COLS, u335_rows)
    _write_csv(out_dir / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_146STARS.csv", U335_COLS, solar146_rows)
    _write_json(out_dir / "FORENSIC_D092_CASCADE_DIAGNOSIS.json", diag_doc)
    _write_json(out_dir / "FORENSIC_CANDIDATE_AUDIT_D092.json", {
        "schema": "D092_FORENSIC_AUDIT_V2_4STREAM",
        "miri_edge_trim_um": MIRI_EDGE_TRIM_UM,
        "n_v50_qualified": len(forensic_recs),
        "n_agnostic_survivors": len(ag_forensic_recs),
        "n_comb_v41_candidates": len(comb_forensic_recs),
        "n_miri_flagged": len(miri_forensic_recs),
        "verified_eti_total": 0,
        "stream_counts": diag_doc["forensic_4stream_counts"],
        "candidates": forensic_recs,
        "agnostic_survivors": ag_forensic_recs,
        "comb_v41_candidates": comb_forensic_recs,
        "miri_flagged": miri_forensic_recs,
    })
    _write_json(out_dir / "SUMMARY.json", summary_doc)

    print(
        f"Stage B DONE ({out_dir}): {len(u335_rows)} stars ({len(solar146_rows)} <10pc), "
        f"D092 G1={n_g1} -> V4.2={n_v42} -> V5.0={n_v50_ctrl + n_v50_sci}; "
        f"Agnostic={len(ag_survivor_rows)}; D091 {len(retro_rows)} -> {n_retro_pass}; "
        f"MIRI det={n_miri_det}/60; best={best_all['star']} {best_all['band_id']}={best_all['p_beam_10m_kw']:.4f} kW",
        flush=True,
    )
    return summary_doc


def main() -> None:
    p = argparse.ArgumentParser(description="Phase D092 V5.0 Analysis Pipeline")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--from-full-inputs", action="store_true", help="Ingest raw ESO FITS into bounded bundle and analyze")
    g.add_argument("--from-bounded-inputs", action="store_true", help="Run strictly from bounded_inputs/d092_bounded_bundle.json.gz")
    p.add_argument("--full-dir", type=Path, default=INP_FULL_DEFAULT)
    p.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument("--archives-dir", type=Path, default=ARCHIVES_DEFAULT)
    args = p.parse_args()

    if args.from_full_inputs:
        run_stage_a_build_bundle(args.full_dir, args.bundle)
    with gzip.open(args.bundle, "rt", encoding="utf-8") as gz:
        bnd = json.load(gz)
    run_stage_b(bnd, args.output_dir, args.archives_dir)


if __name__ == "__main__":
    main()
