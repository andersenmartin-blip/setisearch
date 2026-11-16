#!/usr/bin/env python3
"""Phase D084 Deterministic Execution Pipeline: NORTHERN_V3_5 Dual-Observatory
High-Resolution Northern Echelle Survey (HARPS-N R=115k + CARMENES_VIS R=94.6k),
Automated Cross-Star Topocentric Coincidence Gate (G6_V35), and
125-Star Panchromatic / 136-System Multi-Messenger SETI Synthesis.

Modes:
  1. --from-full-inputs <inputs_dir>: Reads verified raw CARMENES_VIS (.fits) and
     HARPS-N (_s1d_A.fits.gz + _e2ds_A.fits.gz) archival spectra, constructs the
     bounded offline bundle `bounded_inputs/d084_bounded_bundle.json.gz`, and writes
     all D084 + unified 125-star / 136-system synthesis deliverables.
  2. --from-bounded-inputs: Recomputes all deliverables strictly offline from
     `bounded_inputs/d084_bounded_bundle.json.gz` and locked cohort/snapshot files.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gc
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any
import warnings

import numpy as np
from scipy.ndimage import median_filter

from v3_5_detector import (
    BENCHMARK_LASER_BANDS_V35,
    C_KMS,
    FWHM_FACTOR,
    LOCKED_CARMENES_RV_ANCHORS,
    LOCKED_HARPSN_RV_ANCHORS,
    MAD_NORM,
    NORTHERN_AIRGLOW_LINES_TOPO_VAC_A,
    NORTHERN_TELLURIC_BANDS_TOPO_VAC_A,
    STELLAR_CHROMOSPHERIC_VAC_A,
    air_to_vac_a,
    align_template_multiplicative,
    analytical_observatory_berv_kms,
    build_knn_photospheric_atlas,
    check_channel_lsf_gate,
    compute_northern_laser_power_limits,
    compute_segment_continuum_1d,
    compute_supraphotospheric_f1_window,
    compute_windowed_continuum,
    evaluate_gate_g2_northern_atmosphere,
    evaluate_gate_g6_cross_star_coincidence,
    evaluate_gates_g3_g4_g5_northern,
    exact_mad_1d,
    exact_median_1d,
    exact_quantile_1d,
    extract_rv_anchor_window,
    fit_lsf_on_window,
    fit_single_rv_anchor,
    get_inst_config,
    is_in_clean_windows,
    match_cross_star_atlas,
    run_legacy_v2_northern_benchmark,
    scan_residual_spectrum_g1,
    select_clean_control_injection_center,
)

HERE = Path(__file__).resolve().parent
DEFAULT_INPUTS_DIR = HERE.parent.parent / "inputs_d084_v3_5"

TRANSIENT_INJECTION_PHASES = [-0.35, 0.0, 0.35]
TRANSIENT_INJECTION_SIGMAS = [4.0, 6.0, 8.0, 12.0, 20.0]
PERSISTENT_INJECTION_PHASES = [-0.35, 0.0, 0.35]
PERSISTENT_INJECTION_SIGMAS = [5.0, 7.0, 9.0, 12.0, 20.0]
KEPLERIAN_INJECTION_PHASES = [-0.35, 0.0, 0.35]
KEPLERIAN_EXP_SIGMAS = [3.5, 5.0, 6.5, 9.0, 14.0]
G6_CALIBRATION_SIGMAS = [6.0, 10.0, 16.0]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _clean_json_floats(arr: np.ndarray | list[float]) -> list[float]:
    a = np.asarray(arr, dtype=np.float64)
    return np.where(np.isfinite(a), np.round(a, 7), 0.0).tolist()


def _clean_json_floats_with_nan_sentinel(arr: np.ndarray | list[float]) -> list[float | None]:
    a = np.asarray(arr, dtype=np.float64)
    return [round(float(v), 7) if math.isfinite(float(v)) else None for v in a]


def _arr_from_nullable(seq: list[float | None]) -> np.ndarray:
    return np.array([float("nan") if v is None else float(v) for v in seq], dtype=np.float64)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            out = {}
            for k in fieldnames:
                v = r.get(k)
                if isinstance(v, float):
                    if not math.isfinite(v):
                        raise ValueError(f"Non-finite float in {path.name} col {k}: {v}")
                    out[k] = f"{v:.10g}"
                elif v is None:
                    out[k] = ""
                else:
                    out[k] = v
            w.writerow(out)


def verify_prospective_lock(require_download_receipt: bool) -> dict[str, Any]:
    mlock = json.loads((HERE / "METHOD_LOCK.json").read_text(encoding="utf-8"))
    lrcpt = json.loads((HERE / "LOCK_RECEIPT.json").read_text(encoding="utf-8"))
    if sha256_file(HERE / "METHOD_LOCK.json") != lrcpt["method_lock_sha256"]:
        raise RuntimeError("METHOD_LOCK.json SHA-256 mismatch vs LOCK_RECEIPT.json")

    ilock_path = HERE / "IMPLEMENTATION_LOCK.json"
    amended_hashes: dict[str, str] = {}
    if ilock_path.is_file():
        ilock = json.loads(ilock_path.read_text(encoding="utf-8"))
        if ilock.get("parent_method_lock_sha256") != lrcpt["method_lock_sha256"]:
            raise RuntimeError("IMPLEMENTATION_LOCK.json parent hash mismatch")
        amended_hashes = dict(ilock.get("amended_file_hashes", {}))

    for fname, locked_sha in mlock["locked_file_hashes"].items():
        fpath = HERE / fname
        if not fpath.is_file():
            raise RuntimeError(f"Missing locked file: {fname}")
        cur_sha = sha256_file(fpath)
        if cur_sha != locked_sha:
            if fname in amended_hashes and cur_sha == amended_hashes[fname]:
                if fname in ("v3_5_detector.py", "FROZEN_COHORT_D084.csv", "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json"):
                    raise RuntimeError(f"Scientific pipeline/cohort {fname} cannot be amended post-lock!")
            else:
                raise RuntimeError(f"Locked file modified without amendment lock: {fname}")

    lock_t = dt.datetime.fromisoformat(lrcpt["lock_utc"].replace("Z", "+00:00"))
    dl_path = HERE / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json"
    if require_download_receipt:
        dl = json.loads(dl_path.read_text(encoding="utf-8"))
        dl_t = dt.datetime.fromisoformat(dl["first_download_utc"].replace("Z", "+00:00"))
        if dl_t <= lock_t:
            raise RuntimeError(f"Prospective timing violated: first_download={dl_t} <= lock={lock_t}")
        return {"method_lock": mlock, "lock_receipt": lrcpt, "download_receipt": dl}
    return {"method_lock": mlock, "lock_receipt": lrcpt}


def _safe_header_dict(hdr: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for card in hdr.cards:
        try:
            k = card.keyword
            if not k or k in ("COMMENT", "HISTORY", ""):
                continue
            v = card.value
            if isinstance(v, (str, int, float, bool)):
                out[k] = v
                if not k.startswith("HIERARCH ") and (" " in k or len(k) > 8):
                    out[f"HIERARCH {k}"] = v
        except Exception:
            continue
    return out


def load_carmenes_vis_fits(path: Path, row: dict[str, str]) -> dict[str, Any]:
    from astropy.io import fits

    with fits.open(path, memmap=False) as hdul:
        hdr = _safe_header_dict(hdul[0].header)
        spec = np.asarray(hdul[1].data, dtype=np.float64).copy()
        cont = np.asarray(hdul[2].data, dtype=np.float64).copy()
        sig = np.asarray(hdul[3].data, dtype=np.float64).copy()
        wave = np.asarray(hdul[4].data, dtype=np.float64).copy()

    if spec.shape != (61, 4096) or wave.shape != (61, 4096):
        raise RuntimeError(f"Unexpected CARMENES shape on {row['dp_id']}: {spec.shape}")

    expt = float(hdr.get("EXPTIME", float(row["t_exptime"])))
    mjd_obs = float(hdr.get("HIERARCH CARACAL MJD-OBS", float(row["mjd_obs"])))
    tmean_s = float(hdr.get("HIERARCH CARACAL TMEAN", 0.5 * expt))
    if not (math.isfinite(tmean_s) and 0.0 <= tmean_s <= expt * 1.5):
        tmean_s = 0.5 * expt
    mjd_mid = mjd_obs + tmean_s / 86400.0
    bjd_raw = float(hdr.get("HIERARCH CARACAL BJD", mjd_mid + 2400000.5))
    bjd_tdb = bjd_raw + 2400000.0 if bjd_raw < 100000.0 else bjd_raw
    berv_hdr = float(hdr["HIERARCH CARACAL BERV"])
    berv_analyt = analytical_observatory_berv_kms(float(row["s_ra"]), float(row["s_dec"]), mjd_mid, "CARMENES_VIS")
    if abs(berv_hdr - berv_analyt) > 0.60:
        raise RuntimeError(f"CARMENES BERV mismatch on {row['dp_id']}: hdr={berv_hdr:.4f}, analyt={berv_analyt:.4f}")

    airmass = float(hdr.get("AIRMASS", 1.15))
    airmass = min(3.0, max(1.0, airmass if math.isfinite(airmass) and airmass >= 1.0 else 1.15))
    snr_vals = [float(hdr[k]) for k in hdr.keys() if k.startswith("HIERARCH CARACAL FOX SNR") and isinstance(hdr[k], (int, float)) and math.isfinite(float(hdr[k])) and float(hdr[k]) > 0]
    snr_obs = float(np.median(snr_vals)) if snr_vals else float(row["snr"])

    segments: list[dict[str, Any]] = []
    for o in range(61):
        w_o = wave[o]
        s_o = spec[o]
        c_o = cont[o]
        e_o = sig[o]
        valid_c = np.isfinite(w_o) & np.isfinite(s_o) & np.isfinite(c_o) & (c_o > 0) & (s_o > 0)
        if int(valid_c.sum()) < 100:
            continue
        med_c = exact_median_1d(c_o[valid_c])
        # Blaze-flattened ADU-equivalent flux preserves true photon counts across overlapping orders
        f_flat = np.where((c_o > 0) & np.isfinite(s_o) & np.isfinite(c_o), (s_o / c_o) * med_c, np.nan)
        sig_flat = np.where((c_o > 0) & np.isfinite(e_o) & (e_o > 0), (e_o / c_o) * med_c, np.nan)
        segments.append({
            "order": o + 1,
            "px": np.arange(4096, dtype=np.int32),
            "wave_topo_a": w_o,  # CARMENES HDU 4 WAVE is already topocentric vacuum A
            "flux_raw": f_flat,
            "sig_raw": sig_flat,
            "cont_med": med_c,
            "n_px": 4096,
        })

    return {
        "instrument": "CARMENES_VIS",
        "fits_sha256": sha256_file(path),
        "raw_progenitor": path.name,
        "date_obs": str(hdr.get("DATE-OBS", row["obs_release_date"])).strip(),
        "mjd_obs": mjd_obs,
        "mjd_mid": mjd_mid,
        "bjd_tdb": bjd_tdb,
        "exptime_s": expt,
        "snr_obs": snr_obs,
        "airmass_eff": airmass,
        "berv_kms": berv_hdr,
        "berv_analytical_kms": berv_analyt,
        "s1d_wave_bary_vac_a": None,
        "s1d_flux": None,
        "segments": segments,
    }


def load_harpsn_fits_pair(s1d_path: Path, e2ds_path: Path, row: dict[str, str]) -> dict[str, Any]:
    from astropy.io import fits

    with fits.open(s1d_path, memmap=False) as h1:
        hdr1 = _safe_header_dict(h1[0].header)
        s1d_f = np.asarray(h1[0].data, dtype=np.float64).ravel().copy()
        crval1 = float(hdr1["CRVAL1"])
        cdelt1 = float(hdr1["CDELT1"])
        s1d_bary_air = crval1 + cdelt1 * np.arange(len(s1d_f), dtype=np.float64)
        s1d_bary_vac = air_to_vac_a(s1d_bary_air)

    with fits.open(e2ds_path, memmap=False) as h2:
        hdr2 = _safe_header_dict(h2[0].header)
        e2ds_f = np.asarray(h2[0].data, dtype=np.float64).copy()

    if e2ds_f.ndim != 2 or e2ds_f.shape[1] != 4096 or e2ds_f.shape[0] < 35:
        raise RuntimeError(f"Unexpected HARPS-N e2ds shape on {row['dp_id']}: {e2ds_f.shape}")
    n_ord = int(e2ds_f.shape[0])

    mjd_obs = float(hdr2.get("MJD-OBS", hdr1.get("MJD-OBS", float(row["mjd_obs"]))))
    expt = float(hdr2.get("EXPTIME", hdr1.get("EXPTIME", float(row["t_exptime"]))))
    tmmean = float(hdr2.get("HIERARCH TNG DRS TMMEAN", hdr1.get("HIERARCH TNG DRS TMMEAN", 0.5)))
    if not (math.isfinite(tmmean) and 0.0 <= tmmean <= 1.2):
        tmmean = 0.5
    mjd_mid = mjd_obs + tmmean * expt / 86400.0
    bjd_tdb = float(hdr2.get("HIERARCH TNG DRS BJD", hdr1.get("HIERARCH TNG DRS BJD", mjd_mid + 2400000.5)))
    berv_hdr = float(hdr2.get("HIERARCH TNG DRS BERV", hdr1["HIERARCH TNG DRS BERV"]))
    berv_analyt = analytical_observatory_berv_kms(float(row["s_ra"]), float(row["s_dec"]), mjd_mid, "HARPS_N")
    if abs(berv_hdr - berv_analyt) > 0.60:
        raise RuntimeError(f"HARPS-N BERV mismatch on {row['dp_id']}: hdr={berv_hdr:.4f}, analyt={berv_analyt:.4f}")

    airmass = float(hdr2.get("AIRMASS", hdr1.get("AIRMASS", 1.15)))
    airmass = min(3.0, max(1.0, airmass if math.isfinite(airmass) and airmass >= 1.0 else 1.15))
    sn50 = hdr2.get("HIERARCH TNG DRS SPE EXT SN50", hdr1.get("HIERARCH TNG DRS SPE EXT SN50"))
    if sn50 is None:
        sn_vals = [float(hdr2[k]) for k in hdr2.keys() if k.startswith("TNG DRS SPE EXT SN") and isinstance(hdr2[k], (int, float)) and math.isfinite(float(hdr2[k])) and float(hdr2[k]) > 0]
        snr_obs = float(np.median(sn_vals)) if sn_vals else 80.0
    else:
        snr_obs = float(sn50)
    if not (math.isfinite(snr_obs) and snr_obs > 0):
        snr_obs = 60.0

    deg = int(hdr2["HIERARCH TNG DRS CAL TH DEG LL"])
    x_px = np.arange(4096, dtype=np.float64)
    segments: list[dict[str, Any]] = []
    for o in range(n_ord):
        coeffs = [float(hdr2[f"HIERARCH TNG DRS CAL TH COEFF LL{o * (deg + 1) + k}"]) for k in range(deg + 1)]
        w_air = np.zeros_like(x_px)
        for k, c_val in enumerate(coeffs):
            w_air += c_val * (x_px ** k)
        w_topo_vac = air_to_vac_a(w_air)
        f_o = e2ds_f[o]
        segments.append({
            "order": o + 1,
            "px": np.arange(4096, dtype=np.int32),
            "wave_topo_a": w_topo_vac,
            "flux_raw": f_o,
            "sig_raw": None,
            "cont_med": exact_quantile_1d(f_o[np.isfinite(f_o) & (f_o > 0)], 0.80) if np.sum(f_o > 0) > 20 else 1.0,
            "n_px": 4096,
        })

    return {
        "instrument": "HARPS_N",
        "fits_sha256": sha256_file(e2ds_path),  # combined or primary s1d+e2ds digest recorded
        "s1d_sha256": sha256_file(s1d_path),
        "raw_progenitor": f"{s1d_path.name}+{e2ds_path.name}",
        "date_obs": str(hdr1.get("DATE-OBS", row["obs_release_date"])).strip(),
        "mjd_obs": mjd_obs,
        "mjd_mid": mjd_mid,
        "bjd_tdb": bjd_tdb,
        "exptime_s": expt,
        "snr_obs": snr_obs,
        "airmass_eff": airmass,
        "berv_kms": berv_hdr,
        "berv_analytical_kms": berv_analyt,
        "s1d_wave_bary_vac_a": s1d_bary_vac,
        "s1d_flux": s1d_f,
        "segments": segments,
    }


def build_leave_star_out_tellurics_for_inst(
    inst: str,
    raw_exposures: dict[str, dict[str, Any]],
    by_star_inst: dict[str, list[str]],
) -> tuple[np.ndarray, dict[str, np.ndarray], np.ndarray]:
    cfg = get_inst_config(inst)
    topo_grid = np.round(np.arange(cfg["wave_min_angstrom"] - 10.0, cfg["wave_max_angstrom"] + 25.0, 0.04), 4)
    star_zen_med: dict[str, np.ndarray] = {}

    for star, dps in sorted(by_star_inst.items()):
        exp_vecs = []
        for dp_id in dps:
            re = raw_exposures[dp_id]
            airm = float(re["airmass_eff"])
            if inst == "HARPS_N":
                wb = re["s1d_wave_bary_vac_a"]
                wt = wb / (1.0 + float(re["berv_kms"]) / C_KMS)
                fl = re["s1d_flux"]
                fin = np.isfinite(fl) & (fl > 0)
                c_seg = compute_segment_continuum_1d(wt[fin], fl[fin], block_bins=220, quantile_q=0.88, median_blocks=5)
                norm = np.clip(fl[fin] / c_seg, 0.02, 1.25)
                zen = np.where(norm < 1.0, np.power(np.maximum(0.02, norm), 1.0 / airm), norm)
                vec = np.interp(topo_grid, wt[fin], zen, left=np.nan, right=np.nan)
                # HARPS-N has deep stellar lines in blue (< 5800 A); only trust broad/coherent telluric windows
                vec = np.where((topo_grid >= 5850.0), vec, 1.0)
            else:
                vec = np.full(len(topo_grid), np.nan, dtype=np.float64)
                for seg in re["segments"]:
                    px = seg["px"]
                    w_s = seg["wave_topo_a"]
                    f_s = seg["flux_raw"]
                    m_in = (px >= 32) & (px <= 4063) & np.isfinite(f_s) & (f_s > 0)
                    if int(m_in.sum()) < 100:
                        continue
                    wv, fv = w_s[m_in], f_s[m_in]
                    c_seg = compute_segment_continuum_1d(wv, fv, block_bins=120, quantile_q=0.88, median_blocks=5)
                    norm = np.clip(fv / c_seg, 0.02, 1.25)
                    zen = np.where(norm < 1.0, np.power(np.maximum(0.02, norm), 1.0 / airm), norm)
                    i0, i1 = int(np.searchsorted(topo_grid, float(wv[0]))), int(np.searchsorted(topo_grid, float(wv[-1]), side="right"))
                    if i1 <= i0 + 5:
                        continue
                    tgs = topo_grid[i0:i1]
                    interp_v = np.interp(tgs, wv, zen)
                    vec[i0:i1] = np.where(np.isfinite(interp_v), interp_v, vec[i0:i1])
            exp_vecs.append(vec)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            star_zen_med[star] = np.asarray(np.nanmedian(np.vstack(exp_vecs), axis=0), dtype=np.float64)

    all_s = sorted(by_star_inst.keys())
    leave_out: dict[str, np.ndarray] = {}
    for ts in all_s:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            raw_t = np.asarray(np.nanmedian(np.vstack([star_zen_med[s2] for s2 in all_s if s2 != ts]), axis=0), dtype=np.float64)
        fin = np.isfinite(raw_t) & (raw_t > 0)
        if int(fin.sum()) >= 500:
            env = np.ones_like(raw_t)
            idx_f = np.flatnonzero(fin)
            for grp in np.split(idx_f, np.flatnonzero(np.diff(idx_f) > 40) + 1):
                if len(grp) >= 50:
                    s0, s1 = int(grp[0]), int(grp[-1]) + 1
                    env[s0:s1] = compute_segment_continuum_1d(topo_grid[s0:s1], raw_t[s0:s1], block_bins=260, quantile_q=0.88, median_blocks=5)
            leveled = np.where(fin, np.clip(raw_t / np.maximum(0.30, env), 0.05, 1.0), 1.0)
        else:
            leveled = np.ones_like(topo_grid)
        # Keep non-telluric blue region (< 5850 A) identically 1.0 so deep Fe/Ca photosphere of neighbor stars never enters T_tell
        leveled = np.where(topo_grid < 5850.0, 1.0, leveled)
        leave_out[ts] = leveled

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        glob_t = np.asarray(np.nanmedian(np.vstack([star_zen_med[s] for s in all_s]), axis=0), dtype=np.float64)
    glob_t = np.where(topo_grid < 5850.0, 1.0, np.where(np.isfinite(glob_t), np.clip(glob_t, 0.05, 1.0), 1.0))
    return topo_grid, leave_out, glob_t


def apply_telluric_and_build_bary_s1d(
    re: dict[str, Any],
    topo_grid: np.ndarray,
    tell_zen: np.ndarray,
    bary_grid: np.ndarray,
    cfg: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float, list[dict[str, Any]]]:
    inst = re["instrument"]
    berv = float(re["berv_kms"])

    # Fit Beer-Lambert beta_e on clean red/far-red moderate telluric region (> 5900 A)
    s_norms, s_tzens = [], []
    if inst == "HARPS_N":
        wt = re["s1d_wave_bary_vac_a"] / (1.0 + berv / C_KMS)
        fl = re["s1d_flux"]
        fin = (wt >= 5900.0) & np.isfinite(fl) & (fl > 0)
        if int(fin.sum()) >= 500:
            wv, fv = wt[fin], fl[fin]
            cs = compute_segment_continuum_1d(wv, fv, block_bins=180, quantile_q=0.88, median_blocks=5)
            nv = fv / cs
            tzv = np.interp(wv, topo_grid, tell_zen)
            m = (nv > 0.2) & (nv < 1.3) & (tzv >= 0.55) & (tzv <= 0.92)
            if int(m.sum()) >= 30:
                s_norms.append(nv[m])
                s_tzens.append(tzv[m])
    else:
        for seg in re["segments"]:
            m_in = (seg["px"] >= 32) & (seg["px"] <= 4063) & np.isfinite(seg["flux_raw"]) & (seg["flux_raw"] > 0) & (seg["wave_topo_a"] >= 5900.0)
            if int(m_in.sum()) < 100:
                continue
            wv, fv = seg["wave_topo_a"][m_in], seg["flux_raw"][m_in]
            cs = compute_segment_continuum_1d(wv, fv, block_bins=120, quantile_q=0.88, median_blocks=5)
            nv = fv / cs
            tzv = np.interp(wv, topo_grid, tell_zen)
            m = (nv > 0.2) & (nv < 1.3) & (tzv >= 0.55) & (tzv <= 0.92)
            if int(m.sum()) >= 20:
                s_norms.append(nv[m])
                s_tzens.append(tzv[m])

    if s_norms and sum(len(x) for x in s_norms) >= 80:
        sn, stz = np.concatenate(s_norms), np.concatenate(s_tzens)
        betas = np.linspace(0.35, 2.40, 42)
        mads = np.array([exact_mad_1d((sn / np.power(stz, b)) - median_filter(sn / np.power(stz, b), size=31, mode="nearest")) for b in betas], dtype=np.float64)
        beta_e = float(betas[int(np.argmin(mads))])
    else:
        beta_e = float(re["airmass_eff"])

    proc_segments: list[dict[str, Any]] = []
    if inst == "HARPS_N":
        wb_raw = re["s1d_wave_bary_vac_a"]
        wt_raw = wb_raw / (1.0 + berv / C_KMS)
        tr_raw = np.power(np.clip(np.interp(wt_raw, topo_grid, tell_zen), 0.05, 1.0), beta_e)
        fl_raw = re["s1d_flux"]
        ok = np.isfinite(fl_raw) & (fl_raw > 0)
        f_post_raw = np.where(ok & (tr_raw >= 0.50), fl_raw / tr_raw, np.nan)
        fin_p = np.isfinite(f_post_raw)
        f_post_1d = np.interp(bary_grid, wb_raw[fin_p], f_post_raw[fin_p], left=np.nan, right=np.nan)
        f_pre_1d = np.interp(bary_grid, wb_raw[ok], fl_raw[ok], left=np.nan, right=np.nan)
        atm_tr_1d = np.interp(bary_grid, wb_raw, tr_raw, left=1.0, right=1.0)
        for seg in re["segments"]:
            w_b = seg["wave_topo_a"] * (1.0 + berv / C_KMS)
            tr_s = np.power(np.clip(np.interp(seg["wave_topo_a"], topo_grid, tell_zen), 0.05, 1.0), beta_e)
            ok_s = np.isfinite(seg["flux_raw"]) & (seg["flux_raw"] > 0) & (tr_s >= 0.45)
            proc_segments.append({
                "order": seg["order"],
                "px": seg["px"],
                "n_px": seg["n_px"],
                "wave_bary_a": w_b,
                "wave_topo_a": seg["wave_topo_a"],
                "flux_post": np.where(ok_s, seg["flux_raw"] / tr_s, np.nan),
                "tell": tr_s,
                "cont_med": seg["cont_med"],
            })
    else:
        # Inverse-variance weighted order merge for CARMENES_VIS onto 0.030 A grid
        num = np.zeros(len(bary_grid), dtype=np.float64)
        den = np.zeros(len(bary_grid), dtype=np.float64)
        pre_num = np.zeros(len(bary_grid), dtype=np.float64)
        tr_num = np.zeros(len(bary_grid), dtype=np.float64)

        for seg in re["segments"]:
            w_t = seg["wave_topo_a"]
            w_b = w_t * (1.0 + berv / C_KMS)
            tr_s = np.power(np.clip(np.interp(w_t, topo_grid, tell_zen), 0.05, 1.0), beta_e)
            ok_s = np.isfinite(seg["flux_raw"]) & (seg["flux_raw"] > 0) & (tr_s >= 0.45)
            fp_s = np.where(ok_s, seg["flux_raw"] / tr_s, np.nan)
            proc_segments.append({
                "order": seg["order"],
                "px": seg["px"],
                "n_px": seg["n_px"],
                "wave_bary_a": w_b,
                "wave_topo_a": w_t,
                "flux_post": fp_s,
                "tell": tr_s,
                "cont_med": seg["cont_med"],
            })
            # Blaze-weight by flux / sigma^2 across interior px [32..4063]
            m1 = (seg["px"] >= 32) & (seg["px"] <= 4063) & ok_s & np.isfinite(fp_s)
            if int(m1.sum()) < 80:
                continue
            wb_v = w_b[m1]
            fp_v = fp_s[m1]
            fr_v = seg["flux_raw"][m1]
            tr_v = tr_s[m1]
            sig_v = seg["sig_raw"][m1] if seg["sig_raw"] is not None else np.maximum(1.0, np.sqrt(np.maximum(1.0, fp_v)))
            wt_v = 1.0 / np.maximum(1e-6, sig_v ** 2)
            i0, i1 = int(np.searchsorted(bary_grid, float(wb_v[0]))), int(np.searchsorted(bary_grid, float(wb_v[-1]), side="right"))
            if i1 <= i0 + 5:
                continue
            bg = bary_grid[i0:i1]
            fp_i = np.interp(bg, wb_v, fp_v)
            fr_i = np.interp(bg, wb_v, fr_v)
            tr_i = np.interp(bg, wb_v, tr_v)
            wt_i = np.interp(bg, wb_v, wt_v)
            num[i0:i1] += fp_i * wt_i
            pre_num[i0:i1] += fr_i * wt_i
            tr_num[i0:i1] += tr_i * wt_i
            den[i0:i1] += wt_i

        ok_d = den > 0
        f_post_1d = np.where(ok_d, num / np.maximum(den, 1e-30), np.nan)
        f_pre_1d = np.where(ok_d, pre_num / np.maximum(den, 1e-30), np.nan)
        atm_tr_1d = np.where(ok_d, tr_num / np.maximum(den, 1e-30), 1.0)

    in_c = is_in_clean_windows(bary_grid, inst)
    assert isinstance(in_c, np.ndarray)
    flux_clean = np.where(in_c & np.isfinite(f_post_1d) & (f_post_1d > 0) & (atm_tr_1d >= 0.72), f_post_1d, np.nan)
    return flux_clean, f_post_1d, f_pre_1d, atm_tr_1d, beta_e, proc_segments


def build_order_patches_for_wave(
    target_bary_a: float,
    segments: list[dict[str, Any]],
    rest_template_grid: tuple[np.ndarray, np.ndarray],
    v_star_kms: float,
    half_px: int = 80,
) -> list[dict[str, Any]]:
    lam_grid, tmpl_rest = rest_template_grid
    patches = []
    for seg in segments:
        wb = seg["wave_bary_a"]
        if len(wb) < 80 or not (float(wb[0]) < target_bary_a < float(wb[-1])):
            continue
        ka = int(np.argmin(np.abs(wb - target_bary_a)))
        if ka < 18 or ka >= len(wb) - 18:
            continue
        i0, i1 = max(0, ka - half_px), min(len(wb), ka + half_px + 1)
        kl = ka - i0
        if kl < 16 or kl >= (i1 - i0) - 16:
            continue
        wa_w = wb[i0:i1].copy()
        fa_w = seg["flux_post"][i0:i1].copy()
        if not np.all(np.isfinite(fa_w[kl - 6 : kl + 7])):
            continue
        bad = ~np.isfinite(fa_w) | (fa_w <= 0)
        if int(bad.sum()) > 0 and int((~bad).sum()) >= int(0.80 * len(fa_w)):
            ia = np.arange(len(fa_w))
            fa_w[bad] = np.interp(ia[bad], ia[~bad], fa_w[~bad])
        if int(np.sum(np.isfinite(fa_w) & (fa_w > 0))) < 40:
            continue
        wa_rest = wa_w / (1.0 + v_star_kms / C_KMS)
        ref_a = np.interp(wa_rest, lam_grid, tmpl_rest)
        patches.append({
            "order": int(seg["order"]),
            "native_px": int(seg["px"][ka]),
            "n_px": int(seg["n_px"]),
            "target_wave_a": float(target_bary_a),
            "wave": _clean_json_floats(wa_w),
            "flux": _clean_json_floats_with_nan_sentinel(fa_w),
            "ref_norm": _clean_json_floats(ref_a),
        })
    return patches


def find_primary_order_px_for_bary(target_bary_a: float, segments: list[dict[str, Any]]) -> tuple[int | None, int | None]:
    best_ord, best_px, best_flux = None, None, -1.0
    for seg in segments:
        wb = seg["wave_bary_a"]
        if len(wb) < 40 or not (float(wb[0]) <= target_bary_a <= float(wb[-1])):
            continue
        ka = int(np.argmin(np.abs(wb - target_bary_a)))
        px = int(seg["px"][ka])
        if px < 25 or px > seg["n_px"] - 26:
            continue
        c_est = float(seg["cont_med"])
        if c_est > best_flux and math.isfinite(float(seg["flux_post"][ka])):
            best_flux, best_ord, best_px = c_est, int(seg["order"]), px
    return best_ord, best_px


def compute_other_stars_fn_max_pm0p16(
    target_star: str,
    stellar_rest_a: float,
    coadd_grid: np.ndarray,
    star_c_sub_inst: dict[str, np.ndarray],
) -> dict[str, float]:
    k0 = int(np.argmin(np.abs(coadd_grid - stellar_rest_a)))
    sl = slice(max(0, k0 - 85), min(len(coadd_grid), k0 + 86))
    w_sub = coadd_grid[sl]
    out: dict[str, float] = {}
    for st, carr in sorted(star_c_sub_inst.items()):
        if st == target_star:
            continue
        f_sub = carr[sl]
        bf = 0.0
        for da in (-0.10, 0.0, 0.10):
            r = compute_supraphotospheric_f1_window(w_sub, f_sub, stellar_rest_a + da, 1.022)
            if r["fn_pk3"] > bf:
                bf = float(r["fn_pk3"])
        out[st] = round(bf, 6)
    return out


def measure_band_mad_clean(wave: np.ndarray, resid: np.ndarray, nominal_vac_a: float, instrument: str) -> float:
    for rad in (12.0, 35.0, 85.0, 180.0, 420.0):
        m = (np.abs(wave - nominal_vac_a) <= rad) & np.isfinite(resid) & is_in_clean_windows(wave, instrument)
        if int(m.sum()) >= 25:
            md = exact_mad_1d(resid[m])
            if math.isfinite(md) and md > 0.0:
                return float(md)
    fin = np.isfinite(resid)
    return float(exact_mad_1d(resid[fin]))


def _topo_airglow_safe(topo_a: float, min_sep: float = 0.50) -> bool:
    for bnd in NORTHERN_TELLURIC_BANDS_TOPO_VAC_A:
        if (bnd["lo_vac_A"] - 2.0) <= topo_a <= (bnd["hi_vac_A"] + 2.0):
            return False
    return all(abs(topo_a - ag["wave_vac_A"]) >= min_sep for ag in NORTHERN_AIRGLOW_LINES_TOPO_VAC_A)


def _rest_chromo_safe(rest_a: float, min_sep: float = 1.40) -> bool:
    return all(abs(rest_a - ch["rest_vac_A"]) >= min_sep for ch in STELLAR_CHROMOSPHERIC_VAC_A)


def _native_order_interior_ok(segments: list[dict[str, Any]], bary_a: float) -> bool:
    for seg in segments:
        wb = seg["wave_bary_a"]
        if len(wb) < 100 or not (float(wb[0]) < bary_a < float(wb[-1])):
            continue
        ka = int(np.argmin(np.abs(wb - bary_a)))
        if not (65 <= ka < len(wb) - 65):
            continue
        px = int(seg["px"][ka])
        if not (60 <= px <= seg["n_px"] - 61):
            continue
        if np.all(np.isfinite(seg["flux_post"][ka - 10 : ka + 11])) and int(np.isfinite(seg["flux_post"][ka - 70 : ka + 71]).sum()) >= 95:
            if float(np.min(seg["tell"][ka - 4 : ka + 5])) >= 0.84:
                return True
    return False


def select_clean_rest_wave_for_inst(
    nominal_rest_a: float,
    target_star: str,
    instrument: str,
    coadd_grid: np.ndarray,
    c_sub: np.ndarray,
    star_c_sub_inst: dict[str, np.ndarray],
    bervs: list[float],
    v_star: float,
    step_c: float,
    rep_segments: list[dict[str, Any]],
    extra_bary_checks: list[tuple[np.ndarray, np.ndarray, np.ndarray]] | None = None,
) -> int:
    k_nom = int(np.argmin(np.abs(coadd_grid - nominal_rest_a)))
    for span in (20.0, 60.0, 140.0, 320.0, 480.0, 725.0):
        hb = int(round(span / step_c))
        lo, hi = max(180, k_nom - hb), min(len(coadd_grid) - 181, k_nom + hb)
        best_k, best_sc = None, -1e9
        for k in range(lo, hi + 1, 2 if span <= 70 else 6):
            wr = float(coadd_grid[k])
            if not is_in_clean_windows(wr, instrument) or not _rest_chromo_safe(wr):
                continue
            if not np.all(np.isfinite(c_sub[k - 10 : k + 11])):
                continue
            if int(np.isfinite(c_sub[k - 140 : k - 10]).sum()) < 45 or int(np.isfinite(c_sub[k + 11 : k + 141]).sum()) < 45:
                continue
            bw = wr * (1.0 + v_star / C_KMS)
            if not _native_order_interior_ok(rep_segments, bw):
                continue
            if not all(_topo_airglow_safe(bw / (1.0 + bv / C_KMS)) for bv in bervs):
                continue
            mv = float(np.min(c_sub[k - 3 : k + 4]))
            if extra_bary_checks:
                ok_x = True
                for wep, fep, tep in extra_bary_checks:
                    ke = int(np.argmin(np.abs(wep - bw)))
                    if ke < 165 or ke >= len(wep) - 165 or not np.all(np.isfinite(fep[ke - 8 : ke + 9])):
                        ok_x = False
                        break
                    if int(np.isfinite(fep[ke - 140 : ke - 10]).sum()) < 40 or int(np.isfinite(fep[ke + 11 : ke + 141]).sum()) < 40:
                        ok_x = False
                        break
                    if float(np.min(tep[ke - 4 : ke + 5])) < 0.84:
                        ok_x = False
                        break
                    mv = min(mv, float(np.min(fep[ke - 2 : ke + 3])))
                if not ok_x:
                    continue
            oth = compute_other_stars_fn_max_pm0p16(target_star, wr, coadd_grid, star_c_sub_inst)
            if sum(1 for v in oth.values() if v >= 1.022) > (2 if span <= 320.0 else 6):
                continue
            sc = mv - 0.0012 * abs(wr - nominal_rest_a)
            if sc > best_sc:
                best_sc, best_k = sc, k
        if best_k is not None:
            return best_k
    raise RuntimeError(f"Could not find clean continuum near {nominal_rest_a} A for {target_star} ({instrument})")


# ---------------------------------------------------------------------------
# Stage A: Build Bounded Reproducible Bundle from Full Raw Archives
# ---------------------------------------------------------------------------

def build_bounded_bundle_from_full_inputs(
    cohort_rows: list[dict[str, str]],
    kin_catalog: dict[str, Any],
    excl_verif: dict[str, Any],
    full_inputs_dir: Path,
) -> dict[str, Any]:
    man = json.loads((full_inputs_dir / "FULL_NORTHERN_INPUT_MANIFEST.json").read_text(encoding="utf-8"))
    man_by_dp = {x["dp_id"]: x for x in man["exposures"]}
    excl_dps = set(excl_verif["excluded_dp_ids"]) | set(excl_verif["format_check_excluded_dp_ids"])
    ov = sorted({r["dp_id"] for r in cohort_rows} & excl_dps)
    if ov:
        raise RuntimeError(f"Exclusion overlap detected: {ov}")

    print("[Stage A.1] Loading & SHA-256 verifying 183 Northern archival spectra (64 HARPS-N + 119 CARMENES_VIS)...", flush=True)
    raw_exposures: dict[str, dict[str, Any]] = {}
    by_star: dict[str, list[str]] = {}
    by_inst_star: dict[str, dict[str, list[str]]] = {"HARPS_N": {}, "CARMENES_VIS": {}}
    rows_by_dp: dict[str, dict[str, str]] = {}
    for idx, r in enumerate(cohort_rows, start=1):
        dp = r["dp_id"]
        inst = r["instrument"]
        st = r["canonical_target"]
        mitem = man_by_dp[dp]
        by_star.setdefault(st, []).append(dp)
        by_inst_star[inst].setdefault(st, []).append(dp)
        rows_by_dp[dp] = r
        if inst == "CARMENES_VIS":
            fpath = full_inputs_dir / mitem["fits_relpath"]
            if sha256_file(fpath) != mitem["fits_sha256"]:
                raise RuntimeError(f"SHA-256 mismatch on CARMENES {dp}")
            raw_exposures[dp] = load_carmenes_vis_fits(fpath, r)
        else:
            s1d_p = full_inputs_dir / mitem["s1d_relpath"]
            e2d_p = full_inputs_dir / mitem["e2ds_relpath"]
            if sha256_file(s1d_p) != mitem["s1d_sha256"] or sha256_file(e2d_p) != mitem["e2ds_sha256"]:
                raise RuntimeError(f"SHA-256 mismatch on HARPS-N {dp}")
            raw_exposures[dp] = load_harpsn_fits_pair(s1d_p, e2d_p, r)
        if idx % 35 == 0 or idx == len(cohort_rows):
            print(f"  [Stage A.1] Loaded {idx}/{len(cohort_rows)} exposures ({inst} {dp})", flush=True)

    print("[Stage A.2] Building per-instrument leave-star-out northern telluric templates...", flush=True)
    tell_by_inst: dict[str, tuple[np.ndarray, dict[str, np.ndarray], np.ndarray]] = {}
    bary_grids: dict[str, np.ndarray] = {}
    for inst in ("HARPS_N", "CARMENES_VIS"):
        cfg = get_inst_config(inst)
        bary_grids[inst] = np.round(np.arange(cfg["wave_min_angstrom"], cfg["wave_max_angstrom"] + 1e-6, cfg["coadd_step_angstrom"]), 4)
        tell_by_inst[inst] = build_leave_star_out_tellurics_for_inst(inst, raw_exposures, by_inst_star[inst])

    # Downsampled telluric summary profiles for visual Figure 2
    emp_tell_profiles = {}
    for inst in ("HARPS_N", "CARMENES_VIS"):
        tg, _, gt = tell_by_inst[inst]
        vtg = np.round(np.arange(float(tg[0]) + 15.0, float(tg[-1]) - 15.0, 0.50), 2)
        emp_tell_profiles[inst] = {
            "wave_topo_vac_A": _clean_json_floats(vtg),
            "zenith_transmission": _clean_json_floats(np.interp(vtg, tg, gt)),
        }

    print("[Stage A.3] Fitting Beer-Lambert tellurics, 2,196 NIST RV anchors, & continuum normalization...", flush=True)
    exp_records: dict[str, dict[str, Any]] = {}
    provenance_rows = []
    rv_anchor_bundle = {}

    for idx_e, row in enumerate(cohort_rows, start=1):
        dp = row["dp_id"]
        st = row["canonical_target"]
        inst = row["instrument"]
        re = raw_exposures[dp]
        cfg = get_inst_config(inst)
        bgrid = bary_grids[inst]
        tg, lo_t, _ = tell_by_inst[inst]
        flux_clean, f_post, f_pre, atm_tr, beta_e, proc_segs = apply_telluric_and_build_bary_s1d(re, tg, lo_t[st], bgrid, cfg)
        re["segments"] = []
        re["s1d_flux"] = None

        prior_rv = float(row["prior_rv_kms"])
        rv_wins = {}
        clean_rvs = []
        for anc in cfg["rv_anchors"]:
            lab = float(anc["lab_vac_A"])
            ww, fw = extract_rv_anchor_window(bgrid, flux_clean, lab, prior_rv, cfg)
            ww_r = np.asarray(_clean_json_floats(ww), dtype=np.float64)
            fw_r = _arr_from_nullable(_clean_json_floats_with_nan_sentinel(fw))
            fa = fit_single_rv_anchor(ww_r, fw_r, lab, prior_rv, cfg)
            if fa["status"] == "CLEAN_ABSORPTION":
                clean_rvs.append(fa["best_rv_kms"])
            rv_wins[anc["anchor_id"]] = {"wave": ww_r.tolist(), "flux": _clean_json_floats_with_nan_sentinel(fw)}

        if len(clean_rvs) >= int(cfg["rv_anchor_min_clean_lines"]):
            c_arr = np.asarray(clean_rvs, dtype=np.float64)
            v_star = exact_median_1d(c_arr)
            se_rv = exact_mad_1d(c_arr) / math.sqrt(len(c_arr))
        else:
            v_star = prior_rv
            se_rv = 0.0

        rv_anchor_bundle[dp] = {"instrument": inst, "prior_rv_kms": round(prior_rv, 7), "windows": rv_wins}
        cont = compute_windowed_continuum(bgrid, flux_clean, inst, cfg)
        f_norm = flux_clean / cont
        w_rest = bgrid / (1.0 + v_star / C_KMS)
        fin_r = np.isfinite(f_norm)
        u_ext = np.full(len(bgrid), np.nan, dtype=np.float64)
        if int(fin_r.sum()) >= 400:
            u_raw = np.interp(bgrid, w_rest[fin_r], f_norm[fin_r], left=np.nan, right=np.nan)
            wf = w_rest[fin_r]
            idx_n = np.searchsorted(wf, bgrid)
            dl = np.abs(bgrid - wf[np.clip(idx_n - 1, 0, len(wf) - 1)])
            dr = np.abs(bgrid - wf[np.clip(idx_n, 0, len(wf) - 1)])
            u_ext = np.where((np.minimum(dl, dr) > 0.14) | (~is_in_clean_windows(bgrid, inst)), np.nan, u_raw)

        v2_res = run_legacy_v2_northern_benchmark(bgrid, flux_clean, cfg)
        exp_records[dp] = {
            "dp_id": dp,
            "star": st,
            "inst": inst,
            "row": row,
            "berv_kms": float(re["berv_kms"]),
            "berv_analytical_kms": float(re["berv_analytical_kms"]),
            "v_star_kms": float(v_star),
            "vshift_kms": float(v_star - re["berv_kms"]),
            "bary_grid": bgrid,
            "flux_clean": flux_clean,
            "f_post": f_post,
            "atm_tr": atm_tr,
            "cont": cont,
            "f_norm": f_norm,
            "u_ext": u_ext,
            "segments": proc_segs,
            "v2_res": v2_res,
        }
        provenance_rows.append({
            "cohort_index": int(row["cohort_index"]),
            "instrument": inst,
            "role": row["role"],
            "subrole": row["subrole"],
            "radio_mm_id": row["radio_mm_id"],
            "star": st,
            "common_name": row["common_name"],
            "epoch_rank": int(row["epoch_rank"]),
            "phase_window": row["phase_window"],
            "orbital_phase_signed": float(row["orbital_phase_signed"]),
            "planet_orbital_rv_kms": float(row["planet_orbital_rv_kms"]),
            "dp_id": dp,
            "raw_progenitor": re["raw_progenitor"],
            "date_obs": re["date_obs"],
            "mjd_obs": float(re["mjd_obs"]),
            "mjd_mid": float(re["mjd_mid"]),
            "bjd_tdb": float(re["bjd_tdb"]),
            "exptime_s": float(re["exptime_s"]),
            "snr_obs": float(re["snr_obs"]),
            "airmass_eff": float(re["airmass_eff"]),
            "telluric_beta": float(beta_e),
            "s_ra_deg": float(row["s_ra"]),
            "s_dec_deg": float(row["s_dec"]),
            "berv_kms": float(re["berv_kms"]),
            "berv_analytical_kms": float(re["berv_analytical_kms"]),
            "prior_rv_kms": prior_rv,
            "empirical_rv_kms": float(v_star),
            "empirical_rv_se_kms": se_rv,
            "n_clean_rv_anchors": len(clean_rvs),
            "fits_sha256": re["fits_sha256"],
            "header_gate": "PASS",
        })

    print("[Stage A.4] Constructing per-instrument C_s, leave-one-epoch-out T_{s,-e}, & k-NN atlases...", flush=True)
    star_c_sub: dict[str, np.ndarray] = {}
    star_matched_atlas: dict[str, np.ndarray] = {}
    star_atlas_meta: dict[str, dict[str, Any]] = {}
    star_inst: dict[str, str] = {}

    for inst in ("HARPS_N", "CARMENES_VIS"):
        cfg = get_inst_config(inst)
        bgrid = bary_grids[inst]
        s_dict = by_inst_star[inst]
        star_params = {
            st: (float(exp_records[dps[0]]["row"]["teff_k"]), float(exp_records[dps[0]]["row"]["mh_dex"]))
            for st, dps in s_dict.items()
        }
        c_sub_inst: dict[str, np.ndarray] = {}
        for st, dps in s_dict.items():
            star_inst[st] = inst
            stk = np.vstack([exp_records[d]["u_ext"] for d in dps])
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                cs = np.asarray(np.nanmedian(stk, axis=0), dtype=np.float64)
            c_sub_inst[st] = cs
            star_c_sub[st] = cs

            # Leave-one-epoch-out self template T_{s,-e}
            for i_e, d_e in enumerate(dps):
                re = exp_records[d_e]
                oth_u = np.vstack([exp_records[dps[j]]["u_ext"] for j in range(len(dps)) if j != i_e])
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    t_rest = np.asarray(np.nanmedian(oth_u, axis=0), dtype=np.float64)
                re["t_ext"] = t_rest
                ft = np.isfinite(t_rest)
                wr_b = bgrid / (1.0 + re["v_star_kms"] / C_KMS)
                tb = np.interp(wr_b, bgrid[ft], t_rest[ft], left=np.nan, right=np.nan) if int(ft.sum()) >= 200 else np.ones_like(bgrid)
                tb_al = align_template_multiplicative(re["f_norm"], tb, window_bins=201)
                re["y_self"] = np.where(np.isfinite(re["f_norm"]) & np.isfinite(tb_al), re["f_norm"] - tb_al, np.nan)

        for st, dps in s_dict.items():
            atlas_r, nbrs, nwgts = build_knn_photospheric_atlas(st, c_sub_inst, star_params, cfg)
            m_matched, mm_meta = match_cross_star_atlas(bgrid, c_sub_inst[st], atlas_r, block_bins=1200)
            star_matched_atlas[st] = m_matched
            star_atlas_meta[st] = {
                "knn_neighbors": ",".join(nbrs),
                "knn_weights": ",".join(str(x) for x in nwgts),
                "median_optical_depth_gamma": round(float(mm_meta["median_optical_depth_gamma"]), 5),
                "best_rotational_sigma_bins": float(mm_meta["best_rotational_sigma_bins"]),
                "post_match_mad": round(float(mm_meta["post_match_mad"]), 6),
            }
            fm = np.isfinite(m_matched)
            for d_e in dps:
                re = exp_records[d_e]
                wr_b = bgrid / (1.0 + re["v_star_kms"] / C_KMS)
                mb = np.interp(wr_b, bgrid[fm], m_matched[fm], left=np.nan, right=np.nan) if int(fm.sum()) >= 200 else np.ones_like(bgrid)
                mb_al = align_template_multiplicative(re["f_norm"], mb, window_bins=201)
                re["y_cross"] = np.where(np.isfinite(re["f_norm"]) & np.isfinite(mb_al), re["f_norm"] - mb_al, np.nan)

    print("[Stage A.5] Building NORTHERN_V3_5 Cross-Star Topocentric & Order-Pixel Excess Atlas (Gate G6_V35)...", flush=True)
    topo_excess_atlas_by_inst: dict[str, list[dict[str, Any]]] = {"HARPS_N": [], "CARMENES_VIS": []}
    for inst in ("HARPS_N", "CARMENES_VIS"):
        cfg = get_inst_config(inst)
        margin = int(cfg["scan_margin_bins"])
        fwhm_lsf_bins = (6000.0 / cfg["resolving_power"]) / cfg["coadd_step_angstrom"]
        for st, dps in sorted(by_inst_star[inst].items()):
            for dp in dps:
                re = exp_records[dp]
                yc = re["y_cross"]
                bg = re["bary_grid"]
                fin = np.isfinite(yc)
                if int(fin.sum()) < 500:
                    continue
                idx_f = np.flatnonzero(fin)
                v_fill = np.interp(np.arange(len(yc)), idx_f, yc[idx_f])
                med = median_filter(v_fill, size=101, mode="nearest")
                res = v_fill - med
                mad = MAD_NORM * median_filter(np.abs(res), size=101, mode="nearest")
                lmax = np.r_[False, (res[1:-1] > res[:-2]) & (res[1:-1] >= res[2:]), False]
                pks = np.flatnonzero(lmax & fin & (mad > 0) & (res >= cfg["gate_g6_other_prom_min"]) & (res >= cfg["gate_g6_other_snr_min"] * mad))
                for k in pks:
                    if k < margin or k >= len(bg) - margin:
                        continue
                    # Quick local half-max width check so broad stellar continuum bands never enter topocentric sky atlas
                    pk_v = float(res[k])
                    hm = 0.5 * pk_v
                    ll = k
                    while ll > max(0, k - 30) and res[ll] > hm:
                        ll -= 1
                    rr = k
                    while rr < min(len(res) - 1, k + 30) and res[rr] > hm:
                        rr += 1
                    if (rr - ll) > max(8, int(round(4.8 * fwhm_lsf_bins))):
                        continue
                    bary_k = float(bg[k])
                    rest_k = bary_k / (1.0 + re["v_star_kms"] / C_KMS)
                    if not _rest_chromo_safe(rest_k, 1.0):
                        continue
                    topo_k = bary_k / (1.0 + re["berv_kms"] / C_KMS)
                    ord_p, px_p = find_primary_order_px_for_bary(bary_k, re["segments"])
                    topo_excess_atlas_by_inst[inst].append({
                        "star": st,
                        "dp_id": dp,
                        "vshift_kms": round(float(re["vshift_kms"]), 4),
                        "topo_vac_a": round(topo_k, 5),
                        "order": ord_p,
                        "px": px_p,
                        "prom_rel": round(pk_v, 5),
                        "snr_local": round(float(pk_v / mad[k]), 3),
                    })
    print(f"  [G6_V35 Atlas] HARPS_N topo excess peaks: {len(topo_excess_atlas_by_inst['HARPS_N'])}, CARMENES_VIS: {len(topo_excess_atlas_by_inst['CARMENES_VIS'])}", flush=True)

    print("[Stage A.6] Scanning Channel T across all 183 exposures & computing band noise...", flush=True)
    channel_t_candidates_bundle = []
    searched_summary_by_dp = {}
    band_noise_rows = []

    for row in cohort_rows:
        dp = row["dp_id"]
        st = row["canonical_target"]
        inst = row["instrument"]
        re = exp_records[dp]
        cfg = get_inst_config(inst)
        bgrid = re["bary_grid"]
        margin = int(cfg["scan_margin_bins"])

        hits_t, srch_t, pre_f1_t = scan_residual_spectrum_g1(
            bgrid, re["y_self"], re["y_cross"], channel="T", cfg=cfg, flux_norm_for_f1=re["f_norm"], enforce_f1_in_g1=True
        )
        _, _, v31_pre_f1 = scan_residual_spectrum_g1(
            bgrid, re["y_self"], re["y_cross"], channel="T", cfg=cfg, flux_norm_for_f1=re["f_norm"], enforce_f1_in_g1=False
        )
        searched_summary_by_dp[dp] = {
            "v2_searched_bins": re["v2_res"]["searched_samples"],
            "v2_screened_events": re["v2_res"]["screened_events"],
            "v2_accepted_hits": re["v2_res"]["accepted_hits"],
            "v31_pre_f1_channel_t_g1_hits": v31_pre_f1,
            "v35_channel_t_searched_bins": srch_t,
        }

        for bnd in BENCHMARK_LASER_BANDS_V35[inst]:
            md_b = measure_band_mad_clean(bgrid, re["y_self"], float(bnd["center_vac_A"]), inst)
            band_noise_rows.append({"instrument": inst, "star": st, "dp_id": dp, "band_id": bnd["band_id"], "empirical_resid_mad_t": round(md_b, 8)})

        fm_s = np.isfinite(re["t_ext"])
        for h in hits_t:
            k = h["seed_index"]
            sl = slice(k - margin, k + margin + 1)
            bary_a = float(h["fitted_center_a"])
            rest_a = bary_a / (1.0 + re["v_star_kms"] / C_KMS)
            kc = max(45, min(len(bgrid) - 46, int(np.argmin(np.abs(bgrid - bary_a)))))
            slg = slice(kc - 45, kc + 46)
            oth_fn = compute_other_stars_fn_max_pm0p16(st, rest_a, bgrid, {s2: star_c_sub[s2] for s2 in by_inst_star[inst]})
            g2_pre = evaluate_gate_g2_northern_atmosphere(bary_a, re["berv_kms"], bgrid[slg], re["atm_tr"][slg], cfg)
            ord_patches = build_order_patches_for_wave(bary_a, re["segments"], (bgrid[fm_s], re["t_ext"][fm_s]), re["v_star_kms"]) if g2_pre["g2_pass"] else []
            channel_t_candidates_bundle.append({
                "channel": "T",
                "instrument": inst,
                "dp_id": dp,
                "star": st,
                "role": row["role"],
                "berv_kms": re["berv_kms"],
                "v_star_kms": re["v_star_kms"],
                "vshift_kms": re["vshift_kms"],
                "dv_orb_kms": 0.0,
                "seed_wave_a": float(bgrid[k]),
                "wave_win": _clean_json_floats(bgrid[sl]),
                "y_primary_win": _clean_json_floats_with_nan_sentinel(re["y_self"][sl]),
                "y_secondary_win": _clean_json_floats_with_nan_sentinel(re["y_cross"][sl]),
                "f_norm_win": _clean_json_floats_with_nan_sentinel(re["f_norm"][sl]),
                "s1d_wave_win": _clean_json_floats(bgrid[slg]),
                "s1d_atm_transm_win": _clean_json_floats_with_nan_sentinel(re["atm_tr"][slg]),
                "other_stars_fn_max_pm0p16": oth_fn,
                "order_patches": ord_patches,
            })

    print("[Stage A.7] Scanning 10 Orbital Campaigns (T_DIFF & K_PLANET) & Extracting 135 Keplerian Patches...", flush=True)
    channel_tdiff_candidates_bundle = []
    channel_kplanet_candidates_bundle = []
    orbital_campaign_meta_by_star = {}
    calib_keplerian_patches = []

    for ostar, ke in sorted(kin_catalog["campaigns"].items()):
        inst = ke["instrument"]
        cfg = get_inst_config(inst)
        bgrid = bary_grids[inst]
        step_c = float(cfg["coadd_step_angstrom"])
        margin = int(cfg["scan_margin_bins"])
        role = ke["role"]
        dps_in = [e["dp_id"] for e in ke["exposures"] if e["phase_window"] == "IN_WINDOW"]
        dps_out = [e["dp_id"] for e in ke["exposures"] if e["phase_window"] == "OUT_OF_WINDOW"]
        dv_map = {e["dp_id"]: float(e["planet_orbital_rv_kms"]) for e in ke["exposures"]}

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            c_out = np.asarray(np.nanmedian(np.vstack([exp_records[d]["u_ext"] for d in dps_out]), axis=0), dtype=np.float64)
            c_in = np.asarray(np.nanmedian(np.vstack([exp_records[d]["u_ext"] for d in dps_in]), axis=0), dtype=np.float64)
        y_td = np.where(np.isfinite(c_in) & np.isfinite(c_out), c_in - c_out, np.nan)

        r_in_list, u_in_list, y_kp_in, f_kp_in = [], [], [], []
        fo = np.isfinite(c_out)
        for dp_in in dps_in:
            re = exp_records[dp_in]
            rj = np.where(np.isfinite(re["u_ext"]) & np.isfinite(c_out), re["u_ext"] - c_out, np.nan)
            r_in_list.append(rj)
            u_in_list.append(re["u_ext"])
            w_sh = bgrid * (1.0 + dv_map[dp_in] / C_KMS)
            y_kp_in.append(np.interp(w_sh, bgrid, rj, left=np.nan, right=np.nan))
            f_kp_in.append(np.interp(w_sh, bgrid, re["u_ext"], left=np.nan, right=np.nan))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            y_kp = np.asarray(np.nanmedian(np.vstack(y_kp_in), axis=0), dtype=np.float64)
            f_kp = np.asarray(np.nanmedian(np.vstack(f_kp_in), axis=0), dtype=np.float64)

        hits_td, srch_td, pre_f1_td = scan_residual_spectrum_g1(bgrid, y_td, None, "T_DIFF", cfg, flux_norm_for_f1=c_in, enforce_f1_in_g1=True)
        req_td = max(2, int(math.ceil(cfg["channel_tdiff_min_in_exp_fraction"] * len(dps_in))))
        td_g1_cnt = 0
        for h in hits_td:
            k = h["seed_index"]
            sl = slice(k - margin, k + margin + 1)
            ra_c = float(h["fitted_center_a"])
            best_dp, best_s, n_ok = dps_in[0], -1e9, 0
            for j_i, dp_i in enumerate(dps_in):
                ef = fit_lsf_on_window(bgrid[sl], r_in_list[j_i][sl], float(bgrid[k]), cfg)
                es = float(ef["snr_mid"]) if ef.get("valid_fit") else 0.0
                if es >= cfg["channel_tdiff_min_in_exp_snr"]:
                    n_ok += 1
                if es > best_s:
                    best_s, best_dp = es, dp_i
            if n_ok < req_td:
                continue
            td_g1_cnt += 1
            rb = exp_records[best_dp]
            bb = float(ra_c * (1.0 + rb["v_star_kms"] / C_KMS))
            kc = max(45, min(len(bgrid) - 46, int(np.argmin(np.abs(bgrid - bb)))))
            slg = slice(kc - 45, kc + 46)
            g2p = evaluate_gate_g2_northern_atmosphere(bb, rb["berv_kms"], bgrid[slg], rb["atm_tr"][slg], cfg)
            oth = compute_other_stars_fn_max_pm0p16(ostar, ra_c, bgrid, {s2: star_c_sub[s2] for s2 in by_inst_star[inst]})
            channel_tdiff_candidates_bundle.append({
                "channel": "T_DIFF",
                "instrument": inst,
                "dp_id": best_dp,
                "star": ostar,
                "role": role,
                "berv_kms": rb["berv_kms"],
                "v_star_kms": rb["v_star_kms"],
                "vshift_kms": rb["vshift_kms"],
                "dv_orb_kms": 0.0,
                "seed_wave_a": float(bgrid[k]),
                "wave_win": _clean_json_floats(bgrid[sl]),
                "y_primary_win": _clean_json_floats_with_nan_sentinel(y_td[sl]),
                "f_norm_win": _clean_json_floats_with_nan_sentinel(c_in[sl]),
                "s1d_wave_win": _clean_json_floats(bgrid[slg]),
                "s1d_atm_transm_win": _clean_json_floats_with_nan_sentinel(rb["atm_tr"][slg]),
                "other_stars_fn_max_pm0p16": oth,
                "order_patches": build_order_patches_for_wave(bb, rb["segments"], (bgrid[fo], c_out[fo]), rb["v_star_kms"]) if g2p["g2_pass"] else [],
            })

        hits_kp, srch_kp, pre_f1_kp = scan_residual_spectrum_g1(bgrid, y_kp, None, "K_PLANET", cfg, flux_norm_for_f1=f_kp, enforce_f1_in_g1=True)
        req_kp = max(2, int(math.ceil(cfg["channel_kplanet_min_in_exp_fraction"] * len(dps_in))))
        kp_g1_cnt = 0
        for h in hits_kp:
            k = h["seed_index"]
            sl = slice(k - margin, k + margin + 1)
            pl_a = float(h["fitted_center_a"])
            best_dp, best_s, n_ok = dps_in[0], -1e9, 0
            for j_i, dp_i in enumerate(dps_in):
                ef = fit_lsf_on_window(bgrid[sl], y_kp_in[j_i][sl], float(bgrid[k]), cfg)
                es = float(ef["snr_mid"]) if ef.get("valid_fit") else 0.0
                if es >= cfg["channel_kplanet_min_in_exp_snr"]:
                    n_ok += 1
                if es > best_s:
                    best_s, best_dp = es, dp_i
            if n_ok < req_kp:
                continue
            kp_g1_cnt += 1
            rb = exp_records[best_dp]
            dvb = dv_map[best_dp]
            bb = float(pl_a * (1.0 + rb["v_star_kms"] / C_KMS) * (1.0 + dvb / C_KMS))
            rest_b = bb / (1.0 + rb["v_star_kms"] / C_KMS)
            kc = max(45, min(len(bgrid) - 46, int(np.argmin(np.abs(bgrid - bb)))))
            slg = slice(kc - 45, kc + 46)
            g2p = evaluate_gate_g2_northern_atmosphere(bb, rb["berv_kms"], bgrid[slg], rb["atm_tr"][slg], cfg)
            oth = compute_other_stars_fn_max_pm0p16(ostar, rest_b, bgrid, {s2: star_c_sub[s2] for s2 in by_inst_star[inst]})
            channel_kplanet_candidates_bundle.append({
                "channel": "K_PLANET",
                "instrument": inst,
                "dp_id": best_dp,
                "star": ostar,
                "role": role,
                "berv_kms": rb["berv_kms"],
                "v_star_kms": rb["v_star_kms"],
                "vshift_kms": rb["vshift_kms"],
                "dv_orb_kms": dvb,
                "seed_wave_a": float(bgrid[k]),
                "wave_win": _clean_json_floats(bgrid[sl]),
                "y_primary_win": _clean_json_floats_with_nan_sentinel(y_kp[sl]),
                "f_norm_win": _clean_json_floats_with_nan_sentinel(f_kp[sl]),
                "s1d_wave_win": _clean_json_floats(bgrid[slg]),
                "s1d_atm_transm_win": _clean_json_floats_with_nan_sentinel(rb["atm_tr"][slg]),
                "other_stars_fn_max_pm0p16": oth,
                "order_patches": build_order_patches_for_wave(bb, rb["segments"], (bgrid[fo], c_out[fo]), rb["v_star_kms"]) if g2p["g2_pass"] else [],
            })

        orbital_campaign_meta_by_star[ostar] = {
            "instrument": inst,
            "role": role,
            "subrole": ke["subrole"],
            "window_mode": ke["window_mode"],
            "planet_name": ke["planet_name"],
            "orbper_days": ke["orbper_days"],
            "kp_kms": ke["kp_kms"],
            "orbital_dv_span_kms": ke["orbital_dv_span_kms"],
            "n_in_window": len(dps_in),
            "n_out_of_window": len(dps_out),
            "tdiff_searched_bins": srch_td,
            "tdiff_v35_g1_hits": td_g1_cnt,
            "kplanet_searched_bins": srch_kp,
            "kplanet_v35_g1_hits": kp_g1_cnt,
            "band_mads_tdiff": {b["band_id"]: round(measure_band_mad_clean(bgrid, y_td, float(b["center_vac_A"]), inst), 8) for b in BENCHMARK_LASER_BANDS_V35[inst]},
            "band_mads_kplanet": {b["band_id"]: round(measure_band_mad_clean(bgrid, y_kp, float(b["center_vac_A"]), inst), 8) for b in BENCHMARK_LASER_BANDS_V35[inst]},
        }

        if role == "CONTROL":
            # Select 5 bands for HD185144 (HARPS_N) + 4 bands for ROSS248 (CARMENES_VIS) = 9 patches -> 135 paired Keplerian trials
            bnd_list = BENCHMARK_LASER_BANDS_V35[inst][:5] if inst == "HARPS_N" else BENCHMARK_LASER_BANDS_V35[inst][2:6]
            in_dvs = [dv_map[d] for d in dps_in]
            in_bervs = [exp_records[d]["berv_kms"] for d in dps_in]
            rep_idx = min(range(len(dps_in)), key=lambda j: abs(in_dvs[j]))
            full_in_idxs = [j for j, d_i in enumerate(dps_in) if len(exp_records[d_i]["segments"]) >= 60 or inst != "HARPS_N"]
            if full_in_idxs and len(exp_records[dps_in[rep_idx]]["segments"]) < 60 and inst == "HARPS_N":
                rep_idx = full_in_idxs[0]
            rep_dp = dps_in[rep_idx]
            re_rep = exp_records[rep_dp]
            for bnd in bnd_list:
                kc = select_clean_rest_wave_for_inst(
                    float(bnd["center_vac_A"]),
                    ostar,
                    inst,
                    bgrid,
                    c_out,
                    {s2: star_c_sub[s2] for s2 in by_inst_star[inst]},
                    in_bervs,
                    re_rep["v_star_kms"],
                    step_c,
                    re_rep["segments"],
                )
                wp0 = float(bgrid[kc])
                slk = slice(kc - margin - 35, kc + margin + 36)
                smads = [exact_mad_1d(y_kp_in[j][slk][np.isfinite(y_kp_in[j][slk])]) for j in range(len(dps_in)) if int(np.isfinite(y_kp_in[j][slk]).sum()) >= 30]
                med_sin = exact_median_1d(np.asarray(smads, dtype=np.float64))
                bary_r0 = float(wp0 * (1.0 + re_rep["v_star_kms"] / C_KMS) * (1.0 + in_dvs[rep_idx] / C_KMS))
                kr0 = max(45, min(len(bgrid) - 46, int(np.argmin(np.abs(bgrid - bary_r0)))))
                slg0 = slice(kr0 - 45, kr0 + 46)
                calib_keplerian_patches.append({
                    "instrument": inst,
                    "star": ostar,
                    "rep_dp_id": rep_dp,
                    "rep_dv_orb_kms": in_dvs[rep_idx],
                    "rep_berv_kms": re_rep["berv_kms"],
                    "rep_v_star_kms": re_rep["v_star_kms"],
                    "rep_vshift_kms": re_rep["vshift_kms"],
                    "band_id": bnd["band_id"],
                    "target_planet_a": wp0,
                    "kp_kms": ke["kp_kms"],
                    "dv_span_kms": ke["orbital_dv_span_kms"],
                    "single_in_exp_mad": med_sin,
                    "planet_wave_win": _clean_json_floats(bgrid[slk]),
                    "in_exp_tracks": [
                        {
                            "dp_id": d_i,
                            "dv_orb_kms": in_dvs[j],
                            "berv_kms": in_bervs[j],
                            "v_star_kms": exp_records[d_i]["v_star_kms"],
                            "r_star_unshifted_win": _clean_json_floats_with_nan_sentinel(r_in_list[j][slk]),
                            "u_star_unshifted_win": _clean_json_floats_with_nan_sentinel(u_in_list[j][slk]),
                            "y_kp_dedoppler_win": _clean_json_floats_with_nan_sentinel(y_kp_in[j][slk]),
                            "f_kp_dedoppler_win": _clean_json_floats_with_nan_sentinel(f_kp_in[j][slk]),
                        }
                        for j, d_i in enumerate(dps_in)
                    ],
                    "s1d_wave_win": _clean_json_floats(bgrid[slg0]),
                    "s1d_atm_transm_win": _clean_json_floats_with_nan_sentinel(re_rep["atm_tr"][slg0]),
                    "other_stars_fn_max_pm0p16": compute_other_stars_fn_max_pm0p16(ostar, bary_r0 / (1.0 + re_rep["v_star_kms"] / C_KMS), bgrid, {s2: star_c_sub[s2] for s2 in by_inst_star[inst]}),
                    "order_patches": build_order_patches_for_wave(bary_r0, re_rep["segments"], (bgrid[fo], c_out[fo]), re_rep["v_star_kms"]),
                })

    print("[Stage A.8] Scanning Channel P across all 25 stars & Extracting 2,016 Control Calibration Patches (T+P+G5+G6)...", flush=True)
    channel_p_candidates_bundle = []
    channel_p_searched_by_star = {}
    calib_transient_patches = []
    calib_persistent_patches = []
    calib_g5_2d_patches = []
    calib_g6_patches = []

    for st in sorted(by_star.keys()):
        dps = by_star[st]
        inst = star_inst[st]
        cfg = get_inst_config(inst)
        bgrid = bary_grids[inst]
        margin = int(cfg["scan_margin_bins"])
        cs = star_c_sub[st]
        mm = star_matched_atlas[st]
        yp = np.where(np.isfinite(cs) & np.isfinite(mm), cs - mm, np.nan)
        hits_p, srch_p, _ = scan_residual_spectrum_g1(bgrid, yp, None, "P", cfg, flux_norm_for_f1=cs, enforce_f1_in_g1=True)

        p_g1_cnt = 0
        fm_m = np.isfinite(mm)
        for h in hits_p:
            k = h["seed_index"]
            sl = slice(k - margin, k + margin + 1)
            ra_c = float(h["fitted_center_a"])
            ep_snrs, best_dp, best_s, n_cov = [], dps[0], -1e9, 0
            for dp_i in dps:
                re = exp_records[dp_i]
                ba = ra_c * (1.0 + re["v_star_kms"] / C_KMS)
                ke_i = int(np.argmin(np.abs(bgrid - ba)))
                if margin <= ke_i < len(bgrid) - margin and np.all(np.isfinite(re["y_cross"][ke_i - 4 : ke_i + 5])):
                    n_cov += 1
                    ef = fit_lsf_on_window(bgrid[ke_i - margin : ke_i + margin + 1], re["y_cross"][ke_i - margin : ke_i + margin + 1], float(bgrid[ke_i]), cfg)
                    es = float(ef["snr_mid"]) if ef.get("valid_fit") else 0.0
                    ep_snrs.append({"dp_id": dp_i, "covered": True, "snr_cross": es})
                    if es > best_s:
                        best_s, best_dp = es, dp_i
                else:
                    ep_snrs.append({"dp_id": dp_i, "covered": False, "snr_cross": 0.0})
            if n_cov < 2:
                continue
            min_req = max(min(int(cfg["channel_p_min_epochs_above_3sigma"]), n_cov), int(math.ceil(cfg["channel_p_min_epoch_fraction"] * n_cov)))
            n_ab3 = sum(1 for x in ep_snrs if x["covered"] and x["snr_cross"] >= 3.0)
            if n_ab3 < min_req:
                continue
            p_g1_cnt += 1
            rb = exp_records[best_dp]
            bb = ra_c * (1.0 + rb["v_star_kms"] / C_KMS)
            kc = max(45, min(len(bgrid) - 46, int(np.argmin(np.abs(bgrid - bb)))))
            slg = slice(kc - 45, kc + 46)
            g2p = evaluate_gate_g2_northern_atmosphere(bb, rb["berv_kms"], bgrid[slg], rb["atm_tr"][slg], cfg)
            oth = compute_other_stars_fn_max_pm0p16(st, ra_c, bgrid, {s2: star_c_sub[s2] for s2 in by_inst_star[inst]})
            channel_p_candidates_bundle.append({
                "channel": "P",
                "instrument": inst,
                "dp_id": best_dp,
                "star": st,
                "role": rb["row"]["role"],
                "berv_kms": rb["berv_kms"],
                "v_star_kms": rb["v_star_kms"],
                "vshift_kms": rb["vshift_kms"],
                "dv_orb_kms": 0.0,
                "seed_wave_a": float(bgrid[k]),
                "wave_win": _clean_json_floats(bgrid[sl]),
                "y_primary_win": _clean_json_floats_with_nan_sentinel(yp[sl]),
                "c_sub_win": _clean_json_floats_with_nan_sentinel(cs[sl]),
                "s1d_wave_win": _clean_json_floats(bgrid[slg]),
                "s1d_atm_transm_win": _clean_json_floats_with_nan_sentinel(rb["atm_tr"][slg]),
                "other_stars_fn_max_pm0p16": oth,
                "order_patches": build_order_patches_for_wave(bb, rb["segments"], (bgrid[fm_m], mm[fm_m]), rb["v_star_kms"]) if g2p["g2_pass"] else [],
            })

        channel_p_searched_by_star[st] = {
            "instrument": inst,
            "role": exp_records[dps[0]]["row"]["role"],
            "searched_bins": srch_p,
            "v35_persistent_g1_hits": p_g1_cnt,
            **star_atlas_meta[st],
        }

        if exp_records[dps[0]]["row"]["role"] == "CONTROL":
            full_cov_dps = [d for d in dps if len(exp_records[d]["segments"]) >= 60 or inst != "HARPS_N"]
            eval_dps = [full_cov_dps[0], full_cov_dps[-1]]
            s_inst_csub = {s2: star_c_sub[s2] for s2 in by_inst_star[inst]}
            # Other distinct stars on this instrument with >= 10 km/s frame shift separation for Suite E G6 tests
            re0 = exp_records[eval_dps[0]]
            other_inst_stars = [
                (s2, float(exp_records[by_inst_star[inst][s2][0]]["vshift_kms"]))
                for s2 in sorted(by_inst_star[inst].keys())
                if s2 != st and abs(float(exp_records[by_inst_star[inst][s2][0]]["vshift_kms"]) - re0["vshift_kms"]) >= 8.5
            ]

            for d_i in eval_dps:
                re = exp_records[d_i]
                ft = np.isfinite(re["t_ext"])
                for idx_b, bnd in enumerate(BENCHMARK_LASER_BANDS_V35[inst]):
                    kc_r = select_clean_rest_wave_for_inst(
                        float(bnd["center_vac_A"]), st, inst, bgrid, cs, s_inst_csub,
                        [re["berv_kms"]], re["v_star_kms"], float(cfg["coadd_step_angstrom"]), re["segments"],
                        extra_bary_checks=[(bgrid, re["f_norm"], re["atm_tr"])],
                    )
                    rc = float(bgrid[kc_r])
                    bc_t = rc * (1.0 + re["v_star_kms"] / C_KMS)
                    k0 = int(np.argmin(np.abs(bgrid - bc_t)))
                    sl = slice(k0 - margin - 5, k0 + margin + 6)
                    bc = float(bgrid[k0])
                    rest_bc = bc / (1.0 + re["v_star_kms"] / C_KMS)
                    kc_g = max(45, min(len(bgrid) - 46, k0))
                    slg = slice(kc_g - 45, kc_g + 46)
                    ord_p = build_order_patches_for_wave(bc, re["segments"], (bgrid[ft], re["t_ext"][ft]), re["v_star_kms"])
                    oth_fn = compute_other_stars_fn_max_pm0p16(st, rest_bc, bgrid, s_inst_csub)

                    calib_g5_2d_patches.append({
                        "instrument": inst,
                        "star": st,
                        "dp_id": d_i,
                        "band_id": bnd["band_id"],
                        "target_bary_a": bc,
                        "stellar_rest_wave_a": rest_bc,
                        "other_stars_fn_max_pm0p16": oth_fn,
                        "order_patches": ord_p,
                    })
                    calib_transient_patches.append({
                        "instrument": inst,
                        "star": st,
                        "dp_id": d_i,
                        "band_id": bnd["band_id"],
                        "target_bary_a": bc,
                        "berv_kms": re["berv_kms"],
                        "v_star_kms": re["v_star_kms"],
                        "wave_win": _clean_json_floats(bgrid[sl]),
                        "y_self_win": _clean_json_floats_with_nan_sentinel(re["y_self"][sl]),
                        "y_cross_win": _clean_json_floats_with_nan_sentinel(re["y_cross"][sl]),
                        "f_norm_win": _clean_json_floats_with_nan_sentinel(re["f_norm"][sl]),
                        "s1d_wave_win": _clean_json_floats(bgrid[slg]),
                        "s1d_atm_transm_win": _clean_json_floats_with_nan_sentinel(re["atm_tr"][slg]),
                        "other_stars_fn_max_pm0p16": oth_fn,
                        "order_patches": ord_p,
                    })

                    # Suite E G6 Cross-Star Topocentric Coincidence Patches: 5 bands x 1 exposure or 4 controls x 5 bands?
                    # Use dps[0] across 5 bands (idx_b < 5) -> 4 controls x 5 bands = 20 patches x 3 sigmas x 3 classes = 180 trials!
                    if d_i == eval_dps[0] and idx_b < 5:
                        topo_c = bc / (1.0 + re["berv_kms"] / C_KMS)
                        prim_ord, prim_px = find_primary_order_px_for_bary(bc, re["segments"])
                        local_topo_neighbors = [
                            rec_a for rec_a in topo_excess_atlas_by_inst[inst]
                            if abs(float(rec_a["topo_vac_a"]) - topo_c) <= 1.0
                            or (prim_ord is not None and rec_a["order"] == prim_ord and prim_px is not None and abs(float(rec_a["px"]) - prim_px) <= 8.0)
                        ]
                        calib_g6_patches.append({
                            "instrument": inst,
                            "star": st,
                            "dp_id": d_i,
                            "band_id": bnd["band_id"],
                            "cand_topo_vac_a": round(topo_c, 6),
                            "cand_order": prim_ord,
                            "cand_px": prim_px,
                            "target_vshift_kms": round(float(re["vshift_kms"]), 4),
                            "local_real_atlas_records": local_topo_neighbors,
                            "synthetic_other_stars": other_inst_stars[:3],
                        })

            # Channel P 5-epoch control stack (9 bands x 3 phases x 5 sigmas = 135 trials per control -> 540 total)
            p_idxs = [int(round(i * (len(dps) - 1) / 4)) for i in range(5)]
            dps_p = [dps[j] for j in p_idxs]
            p0_candidates = [d for d in dps_p if len(exp_records[d]["segments"]) >= 60 or inst != "HARPS_N"]
            p0_dp = p0_candidates[0] if p0_candidates else eval_dps[0]
            re_p0 = exp_records[p0_dp]
            ep_bervs = [exp_records[d]["berv_kms"] for d in dps_p]
            for bnd in BENCHMARK_LASER_BANDS_V35[inst]:
                kc = select_clean_rest_wave_for_inst(
                    float(bnd["center_vac_A"]), st, inst, bgrid, cs, s_inst_csub,
                    ep_bervs, re_p0["v_star_kms"], float(cfg["coadd_step_angstrom"]), re_p0["segments"],
                )
                rc = float(bgrid[kc])
                sl = slice(kc - margin - 5, kc + margin + 6)
                ep_wins, sc_mads, n_cov_p = [], [], 0
                for d_i in dps_p:
                    r_i = exp_records[d_i]
                    ba_i = rc * (1.0 + r_i["v_star_kms"] / C_KMS)
                    ke_i = int(np.argmin(np.abs(bgrid - ba_i)))
                    sle = slice(ke_i - margin - 5, ke_i + margin + 6)
                    yc_w = r_i["y_cross"][sle]
                    cov = bool(np.all(np.isfinite(r_i["y_cross"][ke_i - 4 : ke_i + 5])) and int(np.isfinite(yc_w).sum()) >= 100)
                    if cov:
                        n_cov_p += 1
                        sc_mads.append(exact_mad_1d(yc_w[np.isfinite(yc_w)]))
                    ep_wins.append({
                        "dp_id": d_i,
                        "covered": cov,
                        "v_star_kms": r_i["v_star_kms"],
                        "wave_win": _clean_json_floats(bgrid[sle]),
                        "y_cross_win": _clean_json_floats_with_nan_sentinel(yc_w),
                    })
                b0 = rc * (1.0 + re_p0["v_star_kms"] / C_KMS)
                kc0 = max(45, min(len(bgrid) - 46, int(np.argmin(np.abs(bgrid - b0)))))
                slg0 = slice(kc0 - 45, kc0 + 46)
                emp_mad = max(exact_mad_1d(yp[sl][np.isfinite(yp[sl])]), 0.55 * exact_median_1d(np.asarray(sc_mads, dtype=np.float64)))
                calib_persistent_patches.append({
                    "instrument": inst,
                    "star": st,
                    "rep_dp_id": p0_dp,
                    "band_id": bnd["band_id"],
                    "target_rest_a": rc,
                    "berv_kms": re_p0["berv_kms"],
                    "v_star_kms": re_p0["v_star_kms"],
                    "n_covering_epochs": n_cov_p,
                    "min_req_epochs": max(min(int(cfg["channel_p_min_epochs_above_3sigma"]), n_cov_p), int(math.ceil(cfg["channel_p_min_epoch_fraction"] * n_cov_p))),
                    "coadd_wave_win": _clean_json_floats(bgrid[sl]),
                    "y_p_win": _clean_json_floats_with_nan_sentinel(yp[sl]),
                    "c_sub_win": _clean_json_floats_with_nan_sentinel(cs[sl]),
                    "epoch_windows": ep_wins,
                    "s1d_wave_win": _clean_json_floats(bgrid[slg0]),
                    "s1d_atm_transm_win": _clean_json_floats_with_nan_sentinel(re_p0["atm_tr"][slg0]),
                    "other_stars_fn_max_pm0p16": compute_other_stars_fn_max_pm0p16(st, rc, bgrid, s_inst_csub),
                    "order_patches": build_order_patches_for_wave(b0, re_p0["segments"], (bgrid[fm_m], mm[fm_m]), re_p0["v_star_kms"]),
                    "coadd_empirical_mad": emp_mad,
                })

    exp_records.clear()
    gc.collect()
    print("[Stage A] Bounded D084 bundle assembled cleanly in memory.", flush=True)
    return {
        "schema": "SETI_D084_BOUNDED_REPRODUCIBLE_BUNDLE_V1",
        "empirical_northern_telluric_profiles": emp_tell_profiles,
        "provenance_rows": provenance_rows,
        "rv_anchor_bundle": rv_anchor_bundle,
        "band_noise_rows": band_noise_rows,
        "searched_summary_by_dp": searched_summary_by_dp,
        "channel_p_searched_by_star": channel_p_searched_by_star,
        "orbital_campaign_meta_by_star": orbital_campaign_meta_by_star,
        "topo_excess_atlas_by_inst": topo_excess_atlas_by_inst,
        "channel_t_candidates_bundle": channel_t_candidates_bundle,
        "channel_p_candidates_bundle": channel_p_candidates_bundle,
        "channel_tdiff_candidates_bundle": channel_tdiff_candidates_bundle,
        "channel_kplanet_candidates_bundle": channel_kplanet_candidates_bundle,
        "calib_transient_patches": calib_transient_patches,
        "calib_persistent_patches": calib_persistent_patches,
        "calib_keplerian_patches": calib_keplerian_patches,
        "calib_g5_2d_patches": calib_g5_2d_patches,
        "calib_g6_patches": calib_g6_patches,
    }


def _unpack_order_patches(patches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**p, "flux": _arr_from_nullable(p["flux"])} for p in patches]


# ---------------------------------------------------------------------------
# Stage B: Deterministic Evaluation from Bounded Bundle
# ---------------------------------------------------------------------------

def evaluate_bundle_and_write_outputs(
    cohort_rows: list[dict[str, str]],
    kin_catalog: dict[str, Any],
    prior_snapshot: dict[str, Any],
    mm_snapshot: dict[str, Any],
    bundle: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    res_dir = out_dir / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    prov_by_dp = {r["dp_id"]: r for r in bundle["provenance_rows"]}

    # 1. Recompute 2,196 RV anchor fits + 25 star RV summaries
    rv_anchor_rows = []
    exp_rv_map = {}
    by_star_rows: dict[str, list[dict[str, str]]] = {}
    for r in cohort_rows:
        by_star_rows.setdefault(r["canonical_target"], []).append(r)

    for r in cohort_rows:
        dp = r["dp_id"]
        inst = r["instrument"]
        cfg = get_inst_config(inst)
        item = bundle["rv_anchor_bundle"][dp]
        prior_rv = float(item["prior_rv_kms"])
        exp_clean = []
        for anc in cfg["rv_anchors"]:
            aid = anc["anchor_id"]
            lab = float(anc["lab_vac_A"])
            win = item["windows"][aid]
            fit = fit_single_rv_anchor(np.asarray(win["wave"], dtype=np.float64), _arr_from_nullable(win["flux"]), lab, prior_rv, cfg)
            if fit["status"] == "CLEAN_ABSORPTION":
                exp_clean.append(fit["best_rv_kms"])
            rv_anchor_rows.append({
                "instrument": inst,
                "star": r["canonical_target"],
                "role": r["role"],
                "dp_id": dp,
                "anchor_id": aid,
                "species": anc["species"],
                "lab_vac_A": lab,
                "prior_rv_kms": prior_rv,
                "status": fit["status"],
                "n_samples": fit["n_samples"],
                "best_rv_kms": fit["best_rv_kms"] if math.isfinite(float(fit["best_rv_kms"])) else None,
                "rel_depth": fit["rel_depth"] if math.isfinite(float(fit["rel_depth"])) else None,
                "min_sse": fit["min_sse"] if math.isfinite(float(fit["min_sse"])) else None,
                "boundary_hit": fit["boundary_hit"],
            })
        med_rv = exact_median_1d(np.asarray(exp_clean, dtype=np.float64)) if len(exp_clean) >= int(cfg["rv_anchor_min_clean_lines"]) else prior_rv
        exp_rv_map[dp] = (med_rv, len(exp_clean))

    star_rv_summary = []
    for st in sorted(by_star_rows.keys()):
        srows = by_star_rows[st]
        inst = srows[0]["instrument"]
        rvs = np.array([exp_rv_map[x["dp_id"]][0] for x in srows], dtype=np.float64)
        pmeta = bundle["channel_p_searched_by_star"][st]
        star_rv_summary.append({
            "instrument": inst,
            "star": st,
            "common_name": srows[0]["common_name"],
            "role": srows[0]["role"],
            "subrole": srows[0]["subrole"],
            "radio_mm_id": srows[0]["radio_mm_id"],
            "dist_pc": float(srows[0]["dist_pc"]),
            "within_10pc": srows[0]["within_10pc"] == "True",
            "teff_k": float(srows[0]["teff_k"]),
            "mh_dex": float(srows[0]["mh_dex"]),
            "phot_g_mag": float(srows[0]["phot_g_mag"]),
            "phot_rp_mag": float(srows[0]["phot_rp_mag"]),
            "j_mag": float(srows[0]["j_mag"]),
            "h_mag": float(srows[0]["h_mag"]),
            "ks_mag": float(srows[0]["ks_mag"]),
            "n_exoplanets": int(srows[0]["n_exoplanets"]),
            "n_epochs": len(srows),
            "empirical_mean_bary_rv_kms": float(np.mean(rvs)),
            "epoch_rms_kms": float(np.std(rvs, ddof=1)) if len(rvs) > 1 else 0.0,
            "prior_rv_kms": float(srows[0]["prior_rv_kms"]),
            "empirical_minus_prior_kms": float(np.mean(rvs)) - float(srows[0]["prior_rv_kms"]),
            "knn_neighbors": pmeta["knn_neighbors"],
            "optical_depth_gamma": pmeta["median_optical_depth_gamma"],
            "post_match_mad": pmeta["post_match_mad"],
        })

    # 2. Prospective Control Calibration (1,080 T + 540 P + 135 Keplerian + 216 G5 + 180 G6 = 2,151 Trials)
    inj_rows = []
    for p in bundle["calib_transient_patches"]:
        inst = p["instrument"]
        cfg = get_inst_config(inst)
        sig_v, margin = float(cfg["sigma_v_kms"]), int(cfg["scan_margin_bins"])
        wb = np.asarray(p["wave_win"], dtype=np.float64)
        ys = _arr_from_nullable(p["y_self_win"])
        yc = _arr_from_nullable(p["y_cross_win"])
        fn = _arr_from_nullable(p["f_norm_win"])
        wg2 = np.asarray(p["s1d_wave_win"], dtype=np.float64)
        trg2 = _arr_from_nullable(p["s1d_atm_transm_win"])
        n_ridge = sum(1 for v in p["other_stars_fn_max_pm0p16"].values() if float(v) >= cfg["gate_g3_cross_star_ridge_fn_min"])
        base_ops = _unpack_order_patches(p["order_patches"])
        loc_mad = exact_mad_1d(ys[np.isfinite(ys)])
        step_a = float(exact_median_1d(np.diff(wb)))
        kc = len(wb) // 2
        w0 = float(wb[kc])
        for ph in TRANSIENT_INJECTION_PHASES:
            inj_b = w0 + ph * step_a
            ptol = 0.75 * (inj_b / cfg["resolving_power"])
            prof = np.exp(-0.5 * ((C_KMS * (wb - inj_b) / inj_b) / sig_v) ** 2)
            snat = inj_b / (cfg["resolving_power"] * FWHM_FACTOR)
            for mult in TRANSIENT_INJECTION_SIGMAS:
                amp = mult * loc_mad
                ysi, yci, fni = ys + amp * prof, yc + amp * prof, fn + amp * prof
                kpk = (kc - 2) + int(np.argmax(np.where(np.isfinite(ysi[kc - 2 : kc + 3]), ysi[kc - 2 : kc + 3], -1e9)))
                sl = slice(kpk - margin, kpk + margin + 1)
                ft = fit_lsf_on_window(wb[sl], ysi[sl], float(wb[kpk]), cfg)
                fc = fit_lsf_on_window(wb[sl], yci[sl], float(wb[kpk]), cfg, fixed_phase_bins=ft["phase_bins"]) if ft.get("valid_fit") else {"valid_fit": False}
                f1 = compute_supraphotospheric_f1_window(wb[sl], fni[sl], ft["fitted_center_a"], cfg["supraphotospheric_min_fn_pk3"]) if ft.get("valid_fit") else {"f1_supraphotospheric_pass": False}
                g1_ok = bool(check_channel_lsf_gate(ft, "T", cfg) and fc.get("valid_fit") and f1["f1_supraphotospheric_pass"] and (fc["amp_mid"] / max(1e-12, ft["amp_mid"]) >= cfg["channel_t_cross_amp_ratio_min"]) and (fc["snr_mid"] >= cfg["channel_t_cross_snr_min"]) and abs(ft["fitted_center_a"] - inj_b) <= ptol)
                fb = ft.get("fitted_center_a", inj_b)
                g2 = evaluate_gate_g2_northern_atmosphere(fb, float(p["berv_kms"]), wg2, trg2, cfg)
                i_ops = [{**op, "target_wave_a": float(fb), "flux": op["flux"] + amp * (exact_quantile_1d(op["flux"][np.isfinite(op["flux"]) & (op["flux"] > 0)], 0.80) if np.sum(op["flux"] > 0) > 10 else 1.0) * np.exp(-0.5 * ((np.asarray(op["wave"]) - inj_b) / snat) ** 2)} for op in base_ops]
                g345 = evaluate_gates_g3_g4_g5_northern(i_ops, fb / (1.0 + float(p["v_star_kms"]) / C_KMS), n_ridge, cfg)
                rec_ok = bool(g1_ok and g2["g2_pass"] and g345["g3_pass"] and g345["g4_pass"])
                inj_rows.append({"instrument": inst, "mode": "CHANNEL_T_TRANSIENT_1EPOCH", "star": p["star"], "dp_id": p["dp_id"], "band_id": p["band_id"], "injected_wave_a": inj_b, "phase_bins": ph, "sigma_mult": mult, "injected_amp_rel": amp, "fitted_snr_mid": ft.get("snr_mid", 0.0), "fitted_cosine": ft.get("cosine_mid", 0.0), "fitted_fwhm_ratio": ft.get("fwhm_over_lsf"), "g1_pass": g1_ok, "g2_pass": g2["g2_pass"], "g3_pass": g345["g3_pass"], "g4_pass": g345["g4_pass"], "recovered": rec_ok})

    for p in bundle["calib_persistent_patches"]:
        inst = p["instrument"]
        cfg = get_inst_config(inst)
        sig_v, margin, step_c = float(cfg["sigma_v_kms"]), int(cfg["scan_margin_bins"]), float(cfg["coadd_step_angstrom"])
        wb = np.asarray(p["coadd_wave_win"], dtype=np.float64)
        ypb, csb = _arr_from_nullable(p["y_p_win"]), _arr_from_nullable(p["c_sub_win"])
        wg2, trg2 = np.asarray(p["s1d_wave_win"], dtype=np.float64), _arr_from_nullable(p["s1d_atm_transm_win"])
        n_ridge = sum(1 for v in p["other_stars_fn_max_pm0p16"].values() if float(v) >= cfg["gate_g3_cross_star_ridge_fn_min"])
        base_ops = _unpack_order_patches(p["order_patches"])
        loc_mad = float(p["coadd_empirical_mad"])
        kc = len(wb) // 2
        w0 = float(wb[kc])
        for ph in PERSISTENT_INJECTION_PHASES:
            inj_r = w0 + ph * step_c
            ptol = 0.75 * (inj_r / cfg["resolving_power"])
            profc = np.exp(-0.5 * ((C_KMS * (wb - inj_r) / inj_r) / sig_v) ** 2)
            inj_b0 = inj_r * (1.0 + float(p["v_star_kms"]) / C_KMS)
            snat = inj_b0 / (cfg["resolving_power"] * FWHM_FACTOR)
            for mult in PERSISTENT_INJECTION_SIGMAS:
                amp = mult * loc_mad
                ypi, csi = ypb + amp * profc, csb + amp * profc
                kpk = (kc - 2) + int(np.argmax(np.where(np.isfinite(ypi[kc - 2 : kc + 3]), ypi[kc - 2 : kc + 3], -1e9)))
                sl = slice(kpk - margin, kpk + margin + 1)
                fp = fit_lsf_on_window(wb[sl], ypi[sl], float(wb[kpk]), cfg)
                f1 = compute_supraphotospheric_f1_window(wb[sl], csi[sl], fp["fitted_center_a"], cfg["supraphotospheric_min_fn_pk3"]) if fp.get("valid_fit") else {"f1_supraphotospheric_pass": False}
                n_ok_e = 0
                for ew in p["epoch_windows"]:
                    if not ew.get("covered", True):
                        continue
                    we, ye = np.asarray(ew["wave_win"], dtype=np.float64), _arr_from_nullable(ew["y_cross_win"])
                    be = inj_r * (1.0 + float(ew["v_star_kms"]) / C_KMS)
                    yei = ye + amp * np.exp(-0.5 * ((C_KMS * (we - be) / be) / sig_v) ** 2)
                    ce = len(we) // 2
                    ke = (ce - 2) + int(np.argmax(np.where(np.isfinite(yei[ce - 2 : ce + 3]), yei[ce - 2 : ce + 3], -1e9)))
                    ef = fit_lsf_on_window(we[ke - margin : ke + margin + 1], yei[ke - margin : ke + margin + 1], float(we[ke]), cfg)
                    if ef.get("valid_fit") and ef["snr_mid"] >= 3.0:
                        n_ok_e += 1
                g1_ok = bool(check_channel_lsf_gate(fp, "P", cfg) and f1["f1_supraphotospheric_pass"] and n_ok_e >= int(p["min_req_epochs"]) and abs(fp["fitted_center_a"] - inj_r) <= ptol)
                fr = fp.get("fitted_center_a", inj_r)
                b0 = fr * (1.0 + float(p["v_star_kms"]) / C_KMS)
                g2 = evaluate_gate_g2_northern_atmosphere(b0, float(p["berv_kms"]), wg2, trg2, cfg)
                i_ops = [{**op, "target_wave_a": float(b0), "flux": op["flux"] + amp * (exact_quantile_1d(op["flux"][np.isfinite(op["flux"]) & (op["flux"] > 0)], 0.80) if np.sum(op["flux"] > 0) > 10 else 1.0) * np.exp(-0.5 * ((np.asarray(op["wave"]) - inj_b0) / snat) ** 2)} for op in base_ops]
                g345 = evaluate_gates_g3_g4_g5_northern(i_ops, fr, n_ridge, cfg)
                rec_ok = bool(g1_ok and g2["g2_pass"] and g345["g3_pass"] and g345["g4_pass"])
                inj_rows.append({"instrument": inst, "mode": "CHANNEL_P_PERSISTENT_5EPOCH", "star": p["star"], "dp_id": p["rep_dp_id"], "band_id": p["band_id"], "injected_wave_a": inj_r, "phase_bins": ph, "sigma_mult": mult, "injected_amp_rel": amp, "fitted_snr_mid": fp.get("snr_mid", 0.0), "fitted_cosine": fp.get("cosine_mid", 0.0), "fitted_fwhm_ratio": fp.get("fwhm_over_lsf"), "g1_pass": g1_ok, "g2_pass": g2["g2_pass"], "g3_pass": g345["g3_pass"], "g4_pass": g345["g4_pass"], "recovered": rec_ok})

    kep_rows = []
    for kp in bundle["calib_keplerian_patches"]:
        inst = kp["instrument"]
        cfg = get_inst_config(inst)
        sig_v, margin, step_c = float(cfg["sigma_v_kms"]), int(cfg["scan_margin_bins"]), float(cfg["coadd_step_angstrom"])
        wpl = np.asarray(kp["planet_wave_win"], dtype=np.float64)
        smad = float(kp["single_in_exp_mad"])
        kc = len(wpl) // 2
        w0 = float(wpl[kc])
        tracks = kp["in_exp_tracks"]
        req_td = max(2, int(math.ceil(cfg["channel_tdiff_min_in_exp_fraction"] * len(tracks))))
        req_kp = max(2, int(math.ceil(cfg["channel_kplanet_min_in_exp_fraction"] * len(tracks))))
        wg2, trg2 = np.asarray(kp["s1d_wave_win"], dtype=np.float64), _arr_from_nullable(kp["s1d_atm_transm_win"])
        n_ridge = sum(1 for v in kp["other_stars_fn_max_pm0p16"].values() if float(v) >= cfg["gate_g3_cross_star_ridge_fn_min"])
        base_ops = _unpack_order_patches(kp["order_patches"])
        for ph in KEPLERIAN_INJECTION_PHASES:
            inj_p = w0 + ph * step_c
            ptol = 0.75 * (inj_p / cfg["resolving_power"])
            profd = np.exp(-0.5 * ((C_KMS * (wpl - inj_p) / inj_p) / sig_v) ** 2)
            unsh_profs = [np.exp(-0.5 * ((C_KMS * (wpl - inj_p * (1.0 + float(trk["dv_orb_kms"]) / C_KMS)) / (inj_p * (1.0 + float(trk["dv_orb_kms"]) / C_KMS))) / sig_v) ** 2) for trk in tracks]
            ib_rep = inj_p * (1.0 + float(kp["rep_v_star_kms"]) / C_KMS) * (1.0 + float(kp["rep_dv_orb_kms"]) / C_KMS)
            snat = ib_rep / (cfg["resolving_power"] * FWHM_FACTOR)
            for me in KEPLERIAN_EXP_SIGMAS:
                amp = me * smad
                runl = [_arr_from_nullable(t["r_star_unshifted_win"]) + amp * unsh_profs[j] for j, t in enumerate(tracks)]
                uunl = [_arr_from_nullable(t["u_star_unshifted_win"]) + amp * unsh_profs[j] for j, t in enumerate(tracks)]
                r_a, u_a = np.vstack(runl), np.vstack(uunl)
                ytd = np.array([exact_median_1d(r_a[:, c][np.isfinite(r_a[:, c])]) for c in range(r_a.shape[1])], dtype=np.float64)
                utd = np.array([exact_median_1d(u_a[:, c][np.isfinite(u_a[:, c])]) for c in range(u_a.shape[1])], dtype=np.float64)
                ktpk = max(margin, min(len(wpl) - margin - 1, (kc - 30) + int(np.argmax(np.where(np.isfinite(ytd[kc - 30 : kc + 31]), ytd[kc - 30 : kc + 31], -1e9)))))
                sltd = slice(ktpk - margin, ktpk + margin + 1)
                ftd = fit_lsf_on_window(wpl[sltd], ytd[sltd], float(wpl[ktpk]), cfg)
                f1td = compute_supraphotospheric_f1_window(wpl[sltd], utd[sltd], ftd["fitted_center_a"], cfg["supraphotospheric_min_fn_pk3"]) if ftd.get("valid_fit") else {"f1_supraphotospheric_pass": False}
                ntdok = sum(1 for j in range(len(tracks)) if fit_lsf_on_window(wpl[sltd], runl[j][sltd], float(wpl[ktpk]), cfg).get("snr_mid", 0.0) >= cfg["channel_tdiff_min_in_exp_snr"]) if ftd.get("valid_fit") else 0
                td_rec = bool(check_channel_lsf_gate(ftd, "T_DIFF", cfg) and f1td["f1_supraphotospheric_pass"] and ntdok >= req_td)

                ykpl = [_arr_from_nullable(t["y_kp_dedoppler_win"]) + amp * profd for t in tracks]
                fkpl = [_arr_from_nullable(t["f_kp_dedoppler_win"]) + amp * profd for t in tracks]
                n_kpok = 0
                for ykj in ykpl:
                    sbj = np.where(np.isfinite(ykj[kc - 2 : kc + 3]), ykj[kc - 2 : kc + 3], -1e9)
                    if float(np.max(sbj)) > -1e8:
                        kj = (kc - 2) + int(np.argmax(sbj))
                        efk = fit_lsf_on_window(wpl[kj - margin : kj + margin + 1], ykj[kj - margin : kj + margin + 1], float(wpl[kj]), cfg)
                        if efk.get("valid_fit") and efk["snr_mid"] >= cfg["channel_kplanet_min_in_exp_snr"]:
                            n_kpok += 1
                yka, fka = np.vstack(ykpl), np.vstack(fkpl)
                ykpm = np.array([exact_median_1d(yka[:, c][np.isfinite(yka[:, c])]) for c in range(yka.shape[1])], dtype=np.float64)
                fkpm = np.array([exact_median_1d(fka[:, c][np.isfinite(fka[:, c])]) for c in range(fka.shape[1])], dtype=np.float64)
                kkpk = (kc - 2) + int(np.argmax(np.where(np.isfinite(ykpm[kc - 2 : kc + 3]), ykpm[kc - 2 : kc + 3], -1e9)))
                slkp = slice(kkpk - margin, kkpk + margin + 1)
                fkp = fit_lsf_on_window(wpl[slkp], ykpm[slkp], float(wpl[kkpk]), cfg)
                f1kp = compute_supraphotospheric_f1_window(wpl[slkp], fkpm[slkp], fkp["fitted_center_a"], cfg["supraphotospheric_min_fn_pk3"]) if fkp.get("valid_fit") else {"f1_supraphotospheric_pass": False}
                kpg1 = bool(check_channel_lsf_gate(fkp, "K_PLANET", cfg) and f1kp["f1_supraphotospheric_pass"] and n_kpok >= req_kp and abs(fkp["fitted_center_a"] - inj_p) <= ptol)
                fpa = fkp.get("fitted_center_a", inj_p)
                brep = fpa * (1.0 + float(kp["rep_v_star_kms"]) / C_KMS) * (1.0 + float(kp["rep_dv_orb_kms"]) / C_KMS)
                rrep = brep / (1.0 + float(kp["rep_v_star_kms"]) / C_KMS)
                g2kp = evaluate_gate_g2_northern_atmosphere(brep, float(kp["rep_berv_kms"]), wg2, trg2, cfg)
                i_ops = [{**op, "target_wave_a": float(brep), "flux": op["flux"] + amp * (exact_quantile_1d(op["flux"][np.isfinite(op["flux"]) & (op["flux"] > 0)], 0.80) if np.sum(op["flux"] > 0) > 10 else 1.0) * np.exp(-0.5 * ((np.asarray(op["wave"]) - ib_rep) / snat) ** 2)} for op in base_ops]
                g345kp = evaluate_gates_g3_g4_g5_northern(i_ops, rrep, n_ridge, cfg)
                kprec = bool(kpg1 and g2kp["g2_pass"] and g345kp["g3_pass"] and g345kp["g4_pass"])
                kep_rows.append({"instrument": inst, "star": kp["star"], "rep_dp_id": kp["rep_dp_id"], "band_id": kp["band_id"], "dv_span_kms": kp["dv_span_kms"], "injected_planet_wave_a": inj_p, "phase_bins": ph, "exp_sigma_mult": me, "injected_amp_rel": amp, "tdiff_uncomp_snr_mid": ftd.get("snr_mid", 0.0), "tdiff_uncomp_recovered": td_rec, "kplanet_dedop_snr_mid": fkp.get("snr_mid", 0.0), "kplanet_dedop_cosine": fkp.get("cosine_mid", 0.0), "kplanet_dedop_fwhm_ratio": fkp.get("fwhm_over_lsf"), "kplanet_g1_pass": kpg1, "kplanet_g2_pass": g2kp["g2_pass"], "kplanet_g3_pass": g345kp["g3_pass"], "kplanet_g4_pass": g345kp["g4_pass"], "kplanet_dedop_recovered": kprec})

    # 2D: 216 Gate G5_V35 CCD Physics Trials (72 Patches x 3 Classes)
    det2d_rows = []
    for rp in bundle["calib_g5_2d_patches"]:
        inst = rp["instrument"]
        cfg = get_inst_config(inst)
        base_ops = _unpack_order_patches(rp["order_patches"])
        tgt, rw = float(rp["target_bary_a"]), float(rp["stellar_rest_wave_a"])
        n_ridge = sum(1 for v in rp["other_stars_fn_max_pm0p16"].values() if float(v) >= cfg["gate_g3_cross_star_ridge_fn_min"])
        sig_a = tgt / (cfg["resolving_power"] * FWHM_FACTOR)
        ol, oi, opl = [], [], []
        for op in base_ops:
            wo, fo_a = np.asarray(op["wave"], dtype=np.float64), op["flux"]
            c80 = exact_quantile_1d(fo_a[np.isfinite(fo_a) & (fo_a > 0)], 0.80) if np.sum(fo_a > 0) >= 10 else 1.0
            kt = int(np.argmin(np.abs(wo - tgt)))
            ol.append({**op, "flux": fo_a + 0.25 * c80 * np.exp(-0.5 * ((wo - tgt) / sig_a) ** 2)})
            pc = np.zeros_like(fo_a)
            pc[kt] = 0.70 * c80
            if kt > 0:
                pc[kt - 1] = 0.02 * 0.70 * c80
            if kt + 1 < len(pc):
                pc[kt + 1] = 0.02 * 0.70 * c80
            oi.append({**op, "flux": fo_a + pc})
            opl.append({**op, "flux": fo_a + 0.35 * c80 * np.exp(-0.5 * ((wo - tgt) / (3.2 * sig_a)) ** 2)})
        for tcls, exp_p, rs in (
            ("TRUE_FIBER_LASER", True, evaluate_gates_g3_g4_g5_northern(ol, rw, n_ridge, cfg)),
            ("CCD_COSMIC_HOT_PIXEL", False, evaluate_gates_g3_g4_g5_northern(oi, rw, n_ridge, cfg)),
            ("BROAD_BANDHEAD_PLATEAU", False, evaluate_gates_g3_g4_g5_northern(opl, rw, n_ridge, cfg)),
        ):
            det2d_rows.append({"instrument": inst, "star": rp["star"], "dp_id": rp["dp_id"], "band_id": rp["band_id"], "primary_order": rs.get("primary_order"), "primary_native_px": rs.get("primary_native_px"), "trial_class": tcls, "expected_g5_pass": exp_p, "g5_pass": rs["g5_pass"], "cos_1d_11px": rs.get("cos_1d_11px"), "hotpx_ratio": rs.get("hotpx_ratio"), "far_wing_34_ratio": rs.get("far_wing_34_ratio"), "g5_reason": rs["g5_reason"]})

    # 2E: 180 Gate G6_V35 Cross-Star Topocentric & Order-Pixel Coincidence Trials (20 Patches x 3 Sigmas x 3 Classes)
    g6_cal_rows = []
    for gp in bundle["calib_g6_patches"]:
        inst = gp["instrument"]
        cfg = get_inst_config(inst)
        tc, co, cpx, tvs = float(gp["cand_topo_vac_a"]), gp["cand_order"], gp["cand_px"], float(gp["target_vshift_kms"])
        real_locs = list(gp["local_real_atlas_records"])
        oth_stars = gp["synthetic_other_stars"]
        for sg in G6_CALIBRATION_SIGMAS:
            prom_inj = round(0.015 * (sg / 3.0), 4)
            # Class 1: True Barycentric Stellar-Frame Laser (no synthetic other-star topocentric coincidence)
            r_true = evaluate_gate_g6_cross_star_coincidence(gp["star"], inst, tc, co, cpx, tvs, real_locs, cfg)
            # Class 2: Unlisted Stationary Sky OH Meinel Line (3 other stars at identical topocentric wavelength, different pixel)
            oh_atlas = list(real_locs) + [{"star": s2, "vshift_kms": vs2, "topo_vac_a": tc + 0.015 * (idx - 1), "order": (co + 1 if co else None), "px": (cpx + 120 if cpx else None), "prom_rel": prom_inj, "snr_local": sg} for idx, (s2, vs2) in enumerate(oth_stars)]
            r_oh = evaluate_gate_g6_cross_star_coincidence(gp["star"], inst, tc, co, cpx, tvs, oh_atlas, cfg)
            # Class 3: Stationary CCD Warm Pixel / Fringe Defect (3 other stars at identical native (order, px), distant topo wave)
            px_atlas = list(real_locs) + [{"star": s2, "vshift_kms": vs2, "topo_vac_a": tc + 1.25 + 0.1 * idx, "order": co, "px": cpx, "prom_rel": prom_inj, "snr_local": sg} for idx, (s2, vs2) in enumerate(oth_stars)]
            r_px = evaluate_gate_g6_cross_star_coincidence(gp["star"], inst, tc, co, cpx, tvs, px_atlas, cfg)
            for tcls, exp_g6, res in (
                ("TRUE_BARYCENTRIC_STELLAR_LASER", True, r_true),
                ("UNLISTED_STATIONARY_SKY_OH_LINE", False, r_oh),
                ("STATIONARY_CCD_WARM_PIXEL_DEFECT", False, r_px),
            ):
                g6_cal_rows.append({"instrument": inst, "star": gp["star"], "dp_id": gp["dp_id"], "band_id": gp["band_id"], "sigma_inj": sg, "trial_class": tcls, "expected_g6_pass": exp_g6, "g6_pass": res["g6_pass"], "coincident_topo_stars": res["g6_coincident_topo_stars"], "coincident_pixel_stars": res["g6_coincident_pixel_stars"], "coincident_total_stars": res["g6_coincident_total_stars"], "g6_reason": res["g6_reason"]})

    # Completeness Summary Table
    calib_band_rows = []
    for inst in ("HARPS_N", "CARMENES_VIS"):
        for mode, s_list in (("CHANNEL_T_TRANSIENT_1EPOCH", TRANSIENT_INJECTION_SIGMAS), ("CHANNEL_P_PERSISTENT_5EPOCH", PERSISTENT_INJECTION_SIGMAS)):
            for bnd in BENCHMARK_LASER_BANDS_V35[inst]:
                for sm in s_list:
                    sub = [r for r in inj_rows if r["instrument"] == inst and r["mode"] == mode and r["band_id"] == bnd["band_id"] and r["sigma_mult"] == sm]
                    nt, nr = len(sub), sum(1 for r in sub if r["recovered"])
                    calib_band_rows.append({"instrument": inst, "mode": mode, "band_id": bnd["band_id"], "center_vac_A": bnd["center_vac_A"], "sigma_mult": sm, "n_trials": nt, "n_recovered": nr, "completeness": nr / nt if nt > 0 else 0.0})

    # 3. Evaluate All Uninjected V3.5 Candidates Across All 4 Channels + Gates G1..G6!
    v35_ledger = []
    cand_idx = 0
    topo_atlas_by_inst = bundle["topo_excess_atlas_by_inst"]

    def _eval_cand(item: dict[str, Any], channel: str) -> None:
        nonlocal cand_idx
        cand_idx += 1
        inst = item["instrument"]
        cfg = get_inst_config(inst)
        cid = f"V35-{channel}-{cand_idx:04d}"
        ww = np.asarray(item["wave_win"], dtype=np.float64)
        ypw = _arr_from_nullable(item["y_primary_win"])
        fit1 = fit_lsf_on_window(ww, ypw, float(item["seed_wave_a"]), cfg)
        fc_a = float(fit1.get("fitted_center_a", float(item["seed_wave_a"])))
        if channel == "T":
            f1c = compute_supraphotospheric_f1_window(ww, _arr_from_nullable(item["f_norm_win"]), fc_a, cfg["supraphotospheric_min_fn_pk3"])
            bary_a = fc_a
            rest_a = bary_a / (1.0 + float(item["v_star_kms"]) / C_KMS)
        elif channel == "P":
            f1c = compute_supraphotospheric_f1_window(ww, _arr_from_nullable(item["c_sub_win"]), fc_a, cfg["supraphotospheric_min_fn_pk3"])
            rest_a = fc_a
            bary_a = rest_a * (1.0 + float(item["v_star_kms"]) / C_KMS)
        elif channel == "T_DIFF":
            f1c = compute_supraphotospheric_f1_window(ww, _arr_from_nullable(item["f_norm_win"]), fc_a, cfg["supraphotospheric_min_fn_pk3"])
            rest_a = fc_a
            bary_a = rest_a * (1.0 + float(item["v_star_kms"]) / C_KMS)
        else:
            f1c = compute_supraphotospheric_f1_window(ww, _arr_from_nullable(item["f_norm_win"]), fc_a, cfg["supraphotospheric_min_fn_pk3"])
            bary_a = fc_a * (1.0 + float(item["v_star_kms"]) / C_KMS) * (1.0 + float(item["dv_orb_kms"]) / C_KMS)
            rest_a = bary_a / (1.0 + float(item["v_star_kms"]) / C_KMS)

        g2 = evaluate_gate_g2_northern_atmosphere(bary_a, float(item["berv_kms"]), np.asarray(item["s1d_wave_win"], dtype=np.float64), _arr_from_nullable(item["s1d_atm_transm_win"]), cfg)
        n_ridge = sum(1 for v in item["other_stars_fn_max_pm0p16"].values() if float(v) >= cfg["gate_g3_cross_star_ridge_fn_min"])
        if g2["g2_pass"] and item["order_patches"]:
            g345 = evaluate_gates_g3_g4_g5_northern(_unpack_order_patches(item["order_patches"]), rest_a, n_ridge, cfg)
        else:
            g345 = {"g3_pass": False, "g3_reason": "NOT_EVALUATED", "g4_pass": False, "g4_reason": "NOT_EVALUATED", "g5_pass": False, "g5_reason": "NOT_EVALUATED"}

        g6 = evaluate_gate_g6_cross_star_coincidence(item["star"], inst, g2["topo_vac_a"], g345.get("primary_order"), g345.get("primary_native_px"), float(item["vshift_kms"]), topo_atlas_by_inst[inst], cfg)
        pre_g6 = bool(f1c["f1_supraphotospheric_pass"] and g2["g2_pass"] and g345["g3_pass"] and g345["g4_pass"] and g345["g5_pass"])
        qual_v35 = bool(pre_g6 and g6["g6_pass"])

        if not f1c["f1_supraphotospheric_pass"]:
            disp = "G1_V35_SUBCONTINUUM_VETO"
        elif not g2["g2_pass"]:
            disp = g2["g2_reason"]
        elif not g345["g3_pass"]:
            disp = g345["g3_reason"]
        elif not g345["g4_pass"]:
            disp = g345["g4_reason"]
        elif not g345["g5_pass"]:
            disp = g345["g5_reason"]
        elif not g6["g6_pass"]:
            disp = g6["g6_reason"]
        else:
            disp = "QUALIFIED_V3_5_LASER_CANDIDATE"

        v35_ledger.append({
            "candidate_id": cid,
            "instrument": inst,
            "channel": channel,
            "role": item["role"],
            "star": item["star"],
            "dp_id": item["dp_id"],
            "fitted_wave_a": fc_a,
            "stellar_rest_wave_a": rest_a,
            "bary_wave_a": bary_a,
            "topo_wave_a": g2["topo_vac_a"],
            "snr_mid": fit1.get("snr_mid", 0.0),
            "snr_outer": fit1.get("snr_outer", 0.0),
            "cosine_mid": fit1.get("cosine_mid", 0.0),
            "fwhm_over_lsf": fit1.get("fwhm_over_lsf"),
            "target_fn_pk3": f1c["fn_pk3"],
            "atm_transm_center": g2["atm_transm_center"],
            "cross_star_ridge_count": n_ridge,
            "g1_v35_pass": f1c["f1_supraphotospheric_pass"],
            "g2_pass": g2["g2_pass"],
            "g3_pass": g345["g3_pass"],
            "primary_order": g345.get("primary_order"),
            "primary_native_px": g345.get("primary_native_px"),
            "primary_native_fn_pk3": g345.get("primary_native_fn_pk3"),
            "primary_template_dip_frac": g345.get("primary_template_dip_frac"),
            "primary_eta_1px": g345.get("primary_eta_1px"),
            "g4_pass": g345["g4_pass"],
            "overlap_tested": g345.get("overlap_tested"),
            "g5_pass": g345["g5_pass"],
            "g5_cos11": g345.get("cos_1d_11px"),
            "g5_hotpx_ratio": g345.get("hotpx_ratio"),
            "g5_far_wing_ratio": g345.get("far_wing_34_ratio"),
            "pre_g6_qualified": pre_g6,
            "g6_pass": g6["g6_pass"],
            "g6_coincident_topo_stars": g6["g6_coincident_topo_stars"],
            "g6_coincident_pixel_stars": g6["g6_coincident_pixel_stars"],
            "g6_coincident_total_stars": g6["g6_coincident_total_stars"],
            "g6_reason": g6["g6_reason"],
            "qualified_v35_laser": qual_v35,
            "final_disposition": disp,
        })

    for ch_key, b_key in (("T", "channel_t_candidates_bundle"), ("P", "channel_p_candidates_bundle"), ("T_DIFF", "channel_tdiff_candidates_bundle"), ("K_PLANET", "channel_kplanet_candidates_bundle")):
        for item in bundle[b_key]:
            _eval_cand(item, ch_key)

    # 4. Per-exposure Benchmark Table (183 Northern Exposures)
    bench_rows = []
    for r in cohort_rows:
        dp = r["dp_id"]
        ss = bundle["searched_summary_by_dp"][dp]
        cd = [c for c in v35_ledger if c["channel"] == "T" and c["dp_id"] == dp]
        bench_rows.append({
            "cohort_index": int(r["cohort_index"]),
            "instrument": r["instrument"],
            "role": r["role"],
            "subrole": r["subrole"],
            "star": r["canonical_target"],
            "epoch_rank": int(r["epoch_rank"]),
            "phase_window": r["phase_window"],
            "dp_id": dp,
            "snr_obs": float(prov_by_dp[dp]["snr_obs"]),
            "v2_searched_bins": ss["v2_searched_bins"],
            "v2_screened_events": ss["v2_screened_events"],
            "v2_accepted_false_alarms": ss["v2_accepted_hits"],
            "v31_pre_f1_g1_hits": ss["v31_pre_f1_g1_hits"] if "v31_pre_f1_g1_hits" in ss else ss["v31_pre_f1_channel_t_g1_hits"],
            "v35_searched_bins": ss["v35_channel_t_searched_bins"],
            "v35_g1_hits": len(cd),
            "v35_after_g2": sum(1 for c in cd if c["g2_pass"]),
            "v35_after_g3": sum(1 for c in cd if c["g2_pass"] and c["g3_pass"]),
            "v35_after_g4": sum(1 for c in cd if c["g2_pass"] and c["g3_pass"] and c["g4_pass"]),
            "v35_after_g5_pre_g6": sum(1 for c in cd if c["pre_g6_qualified"]),
            "v35_qualified_lasers": sum(1 for c in cd if c["qualified_v35_laser"]),
        })

    # 5. Orbital Campaign Summary Table (10 Northern Campaigns)
    orbital_rows = []
    for ostar, om in sorted(bundle["orbital_campaign_meta_by_star"].items()):
        s0 = by_star_rows[ostar][0]
        inst = om["instrument"]
        cfg = get_inst_config(inst)
        best_td_kw, best_kp_kw = float("inf"), float("inf")
        td_mads, kp_mads = [], []
        for bnd in BENCHMARK_LASER_BANDS_V35[inst]:
            mtd, mkp = float(om["band_mads_tdiff"][bnd["band_id"]]), float(om["band_mads_kplanet"][bnd["band_id"]])
            td_mads.append(mtd)
            kp_mads.append(mkp)
            ltd = compute_northern_laser_power_limits(float(bnd["center_vac_A"]), 8.0 * mtd, float(s0["phot_g_mag"]), float(s0["j_mag"]), float(s0["teff_k"]), float(s0["dist_pc"]), cfg)
            lkp = compute_northern_laser_power_limits(float(bnd["center_vac_A"]), 8.0 * mkp, float(s0["phot_g_mag"]), float(s0["j_mag"]), float(s0["teff_k"]), float(s0["dist_pc"]), cfg)
            best_td_kw = min(best_td_kw, ltd["p_beam_10m_kw"])
            best_kp_kw = min(best_kp_kw, lkp["p_beam_10m_kw"])
        td_c = [c for c in v35_ledger if c["channel"] == "T_DIFF" and c["star"] == ostar]
        kp_c = [c for c in v35_ledger if c["channel"] == "K_PLANET" and c["star"] == ostar]
        orbital_rows.append({
            "instrument": inst,
            "role": om["role"],
            "subrole": om["subrole"],
            "window_mode": om["window_mode"],
            "star": ostar,
            "common_name": s0["common_name"],
            "planet_name": om["planet_name"],
            "dist_pc": float(s0["dist_pc"]),
            "orbper_days": om["orbper_days"],
            "kp_kms": om["kp_kms"],
            "orbital_dv_span_kms": om["orbital_dv_span_kms"],
            "n_in_window": om["n_in_window"],
            "n_out_of_window": om["n_out_of_window"],
            "median_tdiff_mad_rel": exact_median_1d(np.asarray(td_mads)),
            "median_kplanet_mad_rel": exact_median_1d(np.asarray(kp_mads)),
            "tdiff_v35_g1_hits": len(td_c),
            "tdiff_qualified_v35": sum(1 for c in td_c if c["qualified_v35_laser"]),
            "kplanet_v35_g1_hits": len(kp_c),
            "kplanet_qualified_v35": sum(1 for c in kp_c if c["qualified_v35_laser"]),
            "best_tdiff_8sigma_10m_kw": best_td_kw,
            "best_kplanet_8sigma_10m_kw": best_kp_kw,
        })

    # 6. Physical 8-Sigma 10m Laser Power Upper Limits (21 Science Stars x 9 Bands = 189 Cells, 0 NaNs)
    upper_limit_rows = []
    bn_map: dict[tuple[str, str], list[float]] = {}
    for bnr in bundle["band_noise_rows"]:
        bn_map.setdefault((bnr["star"], bnr["band_id"]), []).append(float(bnr["empirical_resid_mad_t"]))
    for st in sorted([s for s in by_star_rows if by_star_rows[s][0]["role"] == "SCIENCE"]):
        s0 = by_star_rows[st][0]
        inst = s0["instrument"]
        cfg = get_inst_config(inst)
        for bnd in BENCHMARK_LASER_BANDS_V35[inst]:
            bid, bc = bnd["band_id"], float(bnd["center_vac_A"])
            med_mad = exact_median_1d(np.asarray(bn_map[(st, bid)], dtype=np.float64))
            amp_lim = 8.0 * med_mad
            lim = compute_northern_laser_power_limits(bc, amp_lim, float(s0["phot_g_mag"]), float(s0["j_mag"]), float(s0["teff_k"]), float(s0["dist_pc"]), cfg)
            upper_limit_rows.append({
                "instrument": inst,
                "star": st,
                "common_name": s0["common_name"],
                "subrole": s0["subrole"],
                "radio_mm_id": s0["radio_mm_id"],
                "within_10pc": s0["within_10pc"] == "True",
                "n_exoplanets": int(s0["n_exoplanets"]),
                "has_transiting_planet": s0["has_transiting_planet"] == "True",
                "dist_pc": float(s0["dist_pc"]),
                "teff_k": float(s0["teff_k"]),
                "phot_g_mag": float(s0["phot_g_mag"]),
                "j_mag": float(s0["j_mag"]),
                "band_id": bid,
                "wave_bary_vac_A": bc,
                "radiometric_anchor": "GAIA_DR3_G" if bc < 8500.0 else "TWOMASS_J",
                "median_epoch_mad_rel": med_mad,
                "amp_rel_8sigma_lim": amp_lim,
                **lim,
            })

    # 7. Unified 125-Star Panchromatic V3 Synthesis (D079-D083 100 Southern + D084 25 Northern = 125 Unique Stars!)
    def _f_none(v: Any) -> float | None:
        if v is None or v == "":
            return None
        fv = float(v)
        return fv if math.isfinite(fv) else None

    ul_by_star: dict[str, list[dict[str, Any]]] = {}
    for u in upper_limit_rows:
        ul_by_star.setdefault(u["star"], []).append(u)

    unified_125: list[dict[str, Any]] = []
    for pr in prior_snapshot["unified_100star_rows"]:
        unified_125.append({
            "phases": pr["phases"],
            "hemisphere": "SOUTHERN",
            "spectral_regime": pr["spectral_regime"],
            "instruments": pr["instruments"],
            "star": pr["star"],
            "common_name": pr["common_name"],
            "role": pr["role"],
            "subrole": pr["subrole"],
            "dist_pc": float(pr["dist_pc"]),
            "within_10pc": str(pr["within_10pc"]) == "True",
            "teff_k": float(pr["teff_k"]),
            "phot_g_mag": float(pr["phot_g_mag"]),
            "j_mag": _f_none(pr.get("j_mag")),
            "h_mag": _f_none(pr.get("h_mag")),
            "ks_mag": _f_none(pr.get("ks_mag")),
            "n_exoplanets": int(pr["n_exoplanets"]),
            "n_exposures_optical": int(pr["n_exposures_optical"]),
            "n_exposures_nir_yjh": int(pr["n_exposures_nir_yjh"]),
            "n_exposures_kband": int(pr["n_exposures_kband"]),
            "n_exposures_total": int(pr["n_exposures_total"]),
            "min_optical_10m_kw": _f_none(pr.get("min_optical_10m_kw")),
            "min_nir_yjh_10m_kw": _f_none(pr.get("min_nir_yjh_10m_kw")),
            "min_kband_10m_kw": _f_none(pr.get("min_kband_10m_kw")),
            "p_1064nm_10m_kw": _f_none(pr.get("p_1064nm_10m_kw")),
            "p_1550nm_10m_kw": _f_none(pr.get("p_1550nm_10m_kw")),
            "p_2040nm_tm_10m_kw": _f_none(pr.get("p_2040nm_tm_10m_kw")),
            "p_2097nm_hoyag_10m_kw": _f_none(pr.get("p_2097nm_hoyag_10m_kw")),
            "min_panchromatic_10m_kw": _f_none(pr.get("min_panchromatic_10m_kw")),
            "automated_qualified_candidates": int(pr["automated_qualified_candidates"]),
            "verified_eti_detections": 0,
        })

    for rvs in star_rv_summary:
        st = rvs["star"]
        inst = rvs["instrument"]
        uls = ul_by_star.get(st, [])
        p_all = [float(x["p_beam_10m_kw"]) for x in uls]
        p_opt = [float(x["p_beam_10m_kw"]) for x in uls if float(x["wave_bary_vac_A"]) < 8500.0]
        p_far = [float(x["p_beam_10m_kw"]) for x in uls if float(x["wave_bary_vac_A"]) >= 8500.0]
        q_v35 = sum(1 for c in v35_ledger if c["star"] == st and c["qualified_v35_laser"])
        unified_125.append({
            "phases": "D084",
            "hemisphere": "NORTHERN",
            "spectral_regime": "OPTICAL_0p39_0p69um" if inst == "HARPS_N" else "OPTICAL_FARRED_0p52_1p06um",
            "instruments": inst,
            "star": st,
            "common_name": rvs["common_name"],
            "role": rvs["role"],
            "subrole": rvs["subrole"],
            "dist_pc": rvs["dist_pc"],
            "within_10pc": rvs["within_10pc"],
            "teff_k": rvs["teff_k"],
            "phot_g_mag": rvs["phot_g_mag"],
            "j_mag": rvs["j_mag"],
            "h_mag": rvs["h_mag"],
            "ks_mag": rvs["ks_mag"],
            "n_exoplanets": rvs["n_exoplanets"],
            "n_exposures_optical": rvs["n_epochs"],
            "n_exposures_nir_yjh": 0,
            "n_exposures_kband": 0,
            "n_exposures_total": rvs["n_epochs"],
            "min_optical_10m_kw": min(p_opt) if p_opt else None,
            "min_nir_yjh_10m_kw": min(p_far) if p_far else None,
            "min_kband_10m_kw": None,
            "p_1064nm_10m_kw": None,
            "p_1550nm_10m_kw": None,
            "p_2040nm_tm_10m_kw": None,
            "p_2097nm_hoyag_10m_kw": None,
            "min_panchromatic_10m_kw": min(p_all) if p_all else None,
            "automated_qualified_candidates": q_v35,
            "verified_eti_detections": 0,  # Forensic verification overrides post-audit
        })

    unified_125.sort(key=lambda x: (float(x["dist_pc"]), x["star"]))
    if len(unified_125) != 125:
        raise RuntimeError(f"Expected 125 unique V3 stars, got {len(unified_125)}")
    solar_10pc_53 = [x for x in unified_125 if bool(x["within_10pc"])]

    # 8. Unified 136-System Multi-Messenger Synthesis (125 Echelle + 24 Radio/TESS - 13 Direct Overlap Hosts = 136 Systems!)
    mm_by_v3: dict[str, list[dict[str, Any]]] = {}
    radio_only = []
    for ms in mm_snapshot["systems"]:
        cv3 = str(ms.get("canonical_v3_star") or "").strip()
        if cv3:
            mm_by_v3.setdefault(cv3, []).append(ms)
        else:
            radio_only.append(ms)

    mm_136 = []
    for sr in unified_125:
        st = sr["star"]
        exm = mm_by_v3.get(st, [])
        rads = [m for m in exm if "RADIO" in m["modality"]]
        lss = [m for m in exm if "LIGHTSAIL" in m["modality"] or "PHOTOMETRIC" in m["modality"]]
        mods = ["ECHELLE_SPECTROSCOPY"]
        if rads:
            mods.append("RADIO_1p4GHZ_PLANET_FRAME")
        if lss:
            mods.append("TESS_SPECULAR_LIGHTSAIL")
        mm_136.append({
            "system_id": st,
            "host_name": sr["common_name"],
            "hemisphere": sr["hemisphere"],
            "role": sr["role"],
            "dist_pc": sr["dist_pc"],
            "within_10pc": sr["within_10pc"],
            "n_exoplanets": sr["n_exoplanets"],
            "modalities_searched": "+".join(mods),
            "n_modalities": len(mods),
            "multimessenger_overlap": len(mods) >= 2,
            "echelle_phases": sr["phases"],
            "echelle_instruments": sr["instruments"],
            "echelle_exposures": sr["n_exposures_total"],
            "min_echelle_10m_kw": sr["min_panchromatic_10m_kw"],
            "radio_milestone": "+".join(m["milestone"] for m in rads) if rads else "",
            "radio_facility": "+".join(m["facility"] for m in rads) if rads else "",
            "radio_snr40_recovery": rads[0]["snr40_recovery_fraction"] if rads else None,
            "lightsail_milestone": "+".join(m["milestone"] for m in lss) if lss else "",
            "verified_eti_detections": 0,
        })

    for rs in radio_only:
        mm_136.append({
            "system_id": rs["mm_id"],
            "host_name": rs["host_name"],
            "hemisphere": "NORTHERN" if "Green Bank" in rs["facility"] else "SOUTHERN",
            "role": "SCIENCE",
            "dist_pc": None,
            "within_10pc": None,
            "n_exoplanets": 1,
            "modalities_searched": "RADIO_1p4GHZ_PLANET_FRAME",
            "n_modalities": 1,
            "multimessenger_overlap": False,
            "echelle_phases": "",
            "echelle_instruments": "",
            "echelle_exposures": 0,
            "min_echelle_10m_kw": None,
            "radio_milestone": rs["milestone"],
            "radio_facility": rs["facility"],
            "radio_snr40_recovery": rs["snr40_recovery_fraction"],
            "lightsail_milestone": "",
            "verified_eti_detections": int(rs["verified_eti"]),
        })

    # Write all CSV deliverables
    write_csv(res_dir / "EXPOSURE_PROVENANCE_183.csv", bundle["provenance_rows"])
    write_csv(res_dir / "STELLAR_RV_ANCHORS_2196.csv", rv_anchor_rows)
    write_csv(res_dir / "STAR_RV_SUMMARY_25.csv", star_rv_summary)
    write_csv(res_dir / "INJECTION_RECOVERY_1620.csv", inj_rows)
    write_csv(res_dir / "KEPLERIAN_TRACK_CALIBRATION_135.csv", kep_rows)
    write_csv(res_dir / "DETECTOR_CCD_CALIBRATION_216.csv", det2d_rows)
    write_csv(res_dir / "G6_TOPO_COINCIDENCE_CALIBRATION_180.csv", g6_cal_rows)
    write_csv(res_dir / "CALIBRATION_COMPLETENESS_BY_BAND.csv", calib_band_rows)
    write_csv(res_dir / "V3_5_CANDIDATE_LEDGER.csv", v35_ledger)
    write_csv(res_dir / "FOUR_GEN_BENCHMARK_183.csv", bench_rows)
    write_csv(res_dir / "ORBITAL_CAMPAIGN_RESULTS_10.csv", orbital_rows)
    write_csv(res_dir / "STAR_UPPER_LIMITS_189.csv", upper_limit_rows)
    write_csv(res_dir / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_53STARS.csv", solar_10pc_53)
    write_csv(res_dir / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_125STARS.csv", unified_125)
    write_csv(res_dir / "MULTIMESSENGER_ECHELLE_RADIO_TESS_136SYSTEMS.csv", mm_136)

    # Compute Summary Metrics
    t_8 = [r for r in inj_rows if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH" and r["sigma_mult"] >= 8.0]
    t_8_hn = [r for r in t_8 if r["instrument"] == "HARPS_N"]
    t_8_ca = [r for r in t_8 if r["instrument"] == "CARMENES_VIS"]
    p_9 = [r for r in inj_rows if r["mode"] == "CHANNEL_P_PERSISTENT_5EPOCH" and r["sigma_mult"] >= 9.0]
    p_12 = [r for r in inj_rows if r["mode"] == "CHANNEL_P_PERSISTENT_5EPOCH" and r["sigma_mult"] >= 12.0]
    kep_6p5 = [r for r in kep_rows if r["exp_sigma_mult"] >= 6.5]
    g5_l = [r for r in det2d_rows if r["trial_class"] == "TRUE_FIBER_LASER"]
    g5_i = [r for r in det2d_rows if r["trial_class"] == "CCD_COSMIC_HOT_PIXEL"]
    g5_p = [r for r in det2d_rows if r["trial_class"] == "BROAD_BANDHEAD_PLATEAU"]
    g6_t = [r for r in g6_cal_rows if r["trial_class"] == "TRUE_BARYCENTRIC_STELLAR_LASER"]
    g6_oh = [r for r in g6_cal_rows if r["trial_class"] == "UNLISTED_STATIONARY_SKY_OH_LINE"]
    g6_px = [r for r in g6_cal_rows if r["trial_class"] == "STATIONARY_CCD_WARM_PIXEL_DEFECT"]

    # Forensic inspection helper data for every pre_g6 or qualified_v35 candidate
    forensic_cands = [c for c in v35_ledger if c["pre_g6_qualified"] or c["qualified_v35_laser"]]
    v35_qual_ctrl = sum(1 for c in v35_ledger if c["role"] == "CONTROL" and c["qualified_v35_laser"])
    v35_qual_sci = sum(1 for c in v35_ledger if c["role"] == "SCIENCE" and c["qualified_v35_laser"])

    best_u = min(upper_limit_rows, key=lambda x: float(x["p_beam_10m_w"]))
    best_10pc = [float(x["min_panchromatic_10m_kw"]) for x in solar_10pc_53 if x["min_panchromatic_10m_kw"] is not None]
    n_ovlp = sum(1 for r in mm_136 if r["multimessenger_overlap"])

    summary = {
        "phase_id": "D084",
        "detector": "NORTHERN_V3_5",
        "instruments": ["HARPS_N", "CARMENES_VIS"],
        "cohort": {
            "total_stars": len(by_star_rows),
            "control_stars": sum(1 for s in by_star_rows if by_star_rows[s][0]["role"] == "CONTROL"),
            "science_stars": sum(1 for s in by_star_rows if by_star_rows[s][0]["role"] == "SCIENCE"),
            "within_10pc_stars_d084": sum(1 for s in by_star_rows if by_star_rows[s][0]["within_10pc"] == "True"),
            "total_exposures": len(cohort_rows),
            "harpsn_exposures": sum(1 for r in cohort_rows if r["instrument"] == "HARPS_N"),
            "carmenes_exposures": sum(1 for r in cohort_rows if r["instrument"] == "CARMENES_VIS"),
            "total_integration_hours": round(sum(float(r["exptime_s"]) for r in bundle["provenance_rows"]) / 3600.0, 4),
            "orbital_campaigns": len(orbital_rows),
        },
        "searched_spectral_elements": {
            "channel_t_1d_bins": sum(int(r["v35_searched_bins"]) for r in bench_rows),
            "channel_p_coadd_bins": sum(int(v["searched_bins"]) for v in bundle["channel_p_searched_by_star"].values()),
            "channel_tdiff_bins": sum(int(v["tdiff_searched_bins"]) for v in bundle["orbital_campaign_meta_by_star"].values()),
            "channel_kplanet_bins": sum(int(v["kplanet_searched_bins"]) for v in bundle["orbital_campaign_meta_by_star"].values()),
        },
        "rv_anchoring": {
            "total_anchor_fits": len(rv_anchor_rows),
            "clean_absorption_fits": sum(1 for r in rv_anchor_rows if r["status"] == "CLEAN_ABSORPTION"),
            "median_abs_empirical_minus_prior_kms": round(exact_median_1d(np.array([abs(r["empirical_minus_prior_kms"]) for r in star_rv_summary])), 4),
            "max_pure_stdlib_berv_diff_kms": round(max(abs(float(r["berv_kms"]) - float(r["berv_analytical_kms"])) for r in bundle["provenance_rows"]), 4),
        },
        "synthetic_calibration_2151_trials": {
            "total_trials": len(inj_rows) + len(kep_rows) + len(det2d_rows) + len(g6_cal_rows),
            "channel_t_trials": sum(1 for r in inj_rows if "CHANNEL_T" in r["mode"]),
            "channel_p_trials": sum(1 for r in inj_rows if "CHANNEL_P" in r["mode"]),
            "keplerian_paired_trials": len(kep_rows),
            "ccd_g5_trials": len(det2d_rows),
            "g6_topo_coincidence_trials": len(g6_cal_rows),
            "channel_t_harpsn_ge_8sigma": round(sum(1 for r in t_8_hn if r["recovered"]) / max(1, len(t_8_hn)), 5),
            "channel_t_carmenes_ge_8sigma": round(sum(1 for r in t_8_ca if r["recovered"]) / max(1, len(t_8_ca)), 5),
            "channel_p_ge_9sigma": round(sum(1 for r in p_9 if r["recovered"]) / max(1, len(p_9)), 5),
            "channel_p_ge_12sigma": round(sum(1 for r in p_12 if r["recovered"]) / max(1, len(p_12)), 5),
            "keplerian_tdiff_ge_6p5sigma": round(sum(1 for r in kep_6p5 if r["tdiff_uncomp_recovered"]) / max(1, len(kep_6p5)), 5),
            "keplerian_kplanet_ge_6p5sigma": round(sum(1 for r in kep_6p5 if r["kplanet_dedop_recovered"]) / max(1, len(kep_6p5)), 5),
            "g5_true_laser_pass": round(sum(1 for r in g5_l if r["g5_pass"]) / max(1, len(g5_l)), 5),
            "g5_cosmic_hotpx_rejection": round(sum(1 for r in g5_i if not r["g5_pass"]) / max(1, len(g5_i)), 5),
            "g5_plateau_rejection": round(sum(1 for r in g5_p if not r["g5_pass"]) / max(1, len(g5_p)), 5),
            "g6_true_bary_laser_pass": round(sum(1 for r in g6_t if r["g6_pass"]) / max(1, len(g6_t)), 5),
            "g6_sky_oh_rejection": round(sum(1 for r in g6_oh if not r["g6_pass"]) / max(1, len(g6_oh)), 5),
            "g6_warm_pixel_rejection": round(sum(1 for r in g6_px if not r["g6_pass"]) / max(1, len(g6_px)), 5),
        },
        "false_alarm_cascade": {
            "v2_legacy_false_alarms": sum(int(r["v2_accepted_false_alarms"]) for r in bench_rows),
            "v35_total_ledger_g1_candidates": len(v35_ledger),
            "v35_after_g2": sum(1 for c in v35_ledger if c["g2_pass"]),
            "v35_after_g3": sum(1 for c in v35_ledger if c["g2_pass"] and c["g3_pass"]),
            "v35_after_g4": sum(1 for c in v35_ledger if c["g2_pass"] and c["g3_pass"] and c["g4_pass"]),
            "v35_pre_g6_passed_g1_to_g5": sum(1 for c in v35_ledger if c["pre_g6_qualified"]),
            "v35_vetoed_by_g6_coincidence_gate": sum(1 for c in v35_ledger if c["pre_g6_qualified"] and not c["g6_pass"]),
            "v35_orbital_candidates": sum(1 for c in v35_ledger if c["channel"] in ("T_DIFF", "K_PLANET") and c["qualified_v35_laser"]),
            "automated_qualified_control": v35_qual_ctrl,
            "automated_qualified_science": v35_qual_sci,
            "verified_eti_detections": 0,
        },
        "upper_limits_189_cells": {
            "n_cells": len(upper_limit_rows),
            "best_overall_star": best_u["star"],
            "best_overall_common_name": best_u["common_name"],
            "best_overall_band": best_u["band_id"],
            "best_overall_10m_w": round(float(best_u["p_beam_10m_w"]), 3),
        },
        "unified_125star_panchromatic_v3_synthesis": {
            "phases": "D079-D084",
            "unique_stars_total": len(unified_125),
            "southern_stars": sum(1 for x in unified_125 if x["hemisphere"] == "SOUTHERN"),
            "northern_stars": sum(1 for x in unified_125 if x["hemisphere"] == "NORTHERN"),
            "within_10pc_unique_stars": len(solar_10pc_53),
            "within_10pc_median_limit_kw": round(exact_median_1d(np.asarray(best_10pc, dtype=np.float64)), 4),
            "total_exposures_d079_d084": 649 + len(cohort_rows),
            "total_calibration_trials_d079_d084": 8541 + len(inj_rows) + len(kep_rows) + len(det2d_rows) + len(g6_cal_rows),
            "v2_false_alarms_eliminated_total": 6893 + sum(int(r["v2_accepted_false_alarms"]) for r in bench_rows),
            "verified_eti_detections_total": 0,
        },
        "multimessenger_136system_synthesis": {
            "distinct_stellar_systems_total": len(mm_136),
            "direct_multimessenger_overlap_count": n_ovlp,
            "direct_multimessenger_overlap_stars": [r["system_id"] for r in mm_136 if r["multimessenger_overlap"]],
            "verified_eti_detections_all_modalities": 0,
        },
    }
    summary["searched_spectral_elements"]["total_searched_1d_bins"] = (
        summary["searched_spectral_elements"]["channel_t_1d_bins"]
        + summary["searched_spectral_elements"]["channel_p_coadd_bins"]
        + summary["searched_spectral_elements"]["channel_tdiff_bins"]
        + summary["searched_spectral_elements"]["channel_kplanet_bins"]
    )
    (res_dir / "SUMMARY.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    forensic_doc = {
        "schema": "D084_FORENSIC_NORTHERN_CASCADE_DIAGNOSIS",
        "pre_g6_count": len(forensic_cands),
        "vetoed_by_g6": [c for c in forensic_cands if not c["g6_pass"]],
        "post_g6_qualified": [c for c in forensic_cands if c["qualified_v35_laser"]],
    }
    (res_dir / "FORENSIC_NORTHERN_CASCADE_DIAGNOSIS.json").write_text(json.dumps(forensic_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    print(
        f"[Stage B DONE] 2,151 trials ({summary['synthetic_calibration_2151_trials']['g6_sky_oh_rejection']*100:.1f}% OH rej, "
        f"{summary['synthetic_calibration_2151_trials']['g6_warm_pixel_rejection']*100:.1f}% px rej), "
        f"V2={summary['false_alarm_cascade']['v2_legacy_false_alarms']} -> preG6={summary['false_alarm_cascade']['v35_pre_g6_passed_g1_to_g5']} "
        f"-> G6 vetoed={summary['false_alarm_cascade']['v35_vetoed_by_g6_coincidence_gate']} -> qual={v35_qual_ctrl + v35_qual_sci}, "
        f"125 stars / {len(solar_10pc_53)} <10pc / {len(mm_136)} MM systems ({n_ovlp} overlap).",
        flush=True,
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--from-full-inputs", nargs="?", const=str(DEFAULT_INPUTS_DIR), help="Run full FITS ingestion and export bounded bundle.")
    group.add_argument("--from-bounded-inputs", action="store_true", help="Recompute strictly offline from bounded_inputs/d084_bounded_bundle.json.gz.")
    args = parser.parse_args()

    cohort_rows = list(csv.DictReader((HERE / "FROZEN_COHORT_D084.csv").open("r", encoding="utf-8")))
    kin_catalog = json.loads((HERE / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))
    excl_verif = json.loads((HERE / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    prior_snapshot = json.loads((HERE / "PRIOR_V3_PHASES_SNAPSHOT.json").read_text(encoding="utf-8"))
    mm_snapshot = json.loads((HERE / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").read_text(encoding="utf-8"))
    bundle_path = HERE / "bounded_inputs" / "d084_bounded_bundle.json.gz"

    if args.from_full_inputs is not None:
        verify_prospective_lock(require_download_receipt=True)
        bundle = build_bounded_bundle_from_full_inputs(cohort_rows, kin_catalog, excl_verif, Path(args.from_full_inputs))
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.GzipFile(filename=str(bundle_path), mode="wb", mtime=0) as gz:
            gz.write(json.dumps(bundle, separators=(",", ":"), allow_nan=False).encode("utf-8"))
        print(f"Wrote {bundle_path} ({bundle_path.stat().st_size / (1024*1024):.2f} MiB)", flush=True)
    else:
        verify_prospective_lock(require_download_receipt=True)
        with gzip.open(bundle_path, "rt", encoding="utf-8") as gz:
            bundle = json.load(gz)

    evaluate_bundle_and_write_outputs(cohort_rows, kin_catalog, prior_snapshot, mm_snapshot, bundle, HERE)


if __name__ == "__main__":
    main()
