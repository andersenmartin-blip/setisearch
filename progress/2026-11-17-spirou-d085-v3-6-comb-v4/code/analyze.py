#!/usr/bin/env python3
"""Phase D085 Deterministic Execution Pipeline: SPIROU_V3_6_AND_COMB_V4.

CFHT 3.6 m SPIRou APERO 0.7.295 (`*t.fits`, 0.955-2.515 um YJHK across 49 x 4088 orders,
R = 70,000, Maunakea) survey across 29 stars (25 brand-new + 4 northern < 10 pc bridge stars,
177 exposures), upgrading G6_V35 -> sparse supraphotospheric Gate G6_V36, adding Channel 5
coherent multi-line frequency-comb search V4 `COMB`, and synthesizing:
  - 150 unique stars (1,009 exposures, 73 stars < 10 pc, 8 optical-to-K bridge stars)
  - 160 distinct multi-messenger systems (14 direct overlaps including rho CrB / M20)

Modes:
  1. --from-full-inputs <inputs_dir>: Reads SHA-256 verified CFHT SPIRou APERO `*t.fits`,
     builds `bounded_inputs/d085_bounded_bundle.json.gz` (< 25 MiB), runs Stage B, writes results.
  2. --from-bounded-inputs: Deterministically recomputes all results & 2,592 calibration trials
     strictly offline from `bounded_inputs/d085_bounded_bundle.json.gz`.
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

from v3_6_detector import (
    BENCHMARK_LASER_BANDS_V36,
    C_ANGSTROM_GHZ,
    C_KMS,
    CLEAN_SPIROU_WINDOWS_VAC_A,
    FWHM_FACTOR,
    LOCKED_SPIROU_RV_ANCHORS,
    MAD_NORM,
    SPIROU_OH_AIRGLOW_VAC_A,
    SPIROU_TELLURIC_BANDS_TOPO_VAC_A,
    STELLAR_CHROMOSPHERIC_VAC_A,
    analytical_maunakea_berv_kms,
    build_knn_photospheric_atlas,
    check_channel_lsf_gate,
    compute_segment_continuum_1d,
    compute_spirou_laser_power_limits,
    compute_supraphotospheric_f1_window,
    compute_windowed_continuum,
    evaluate_gate_g2_spirou_atmosphere,
    evaluate_gate_g6_v35_dense,
    evaluate_gate_g6_v36_sparse,
    evaluate_gates_g3_g4_g5_spirou,
    exact_mad_1d,
    exact_median_1d,
    exact_quantile_1d,
    extract_rv_anchor_window,
    fit_lsf_on_window,
    fit_single_rv_anchor,
    get_inst_config,
    is_in_clean_windows,
    match_cross_star_atlas,
    run_legacy_v2_spirou_benchmark,
    scan_1d_channel_candidates,
    scan_frequency_comb_v4,
)

HERE = Path(__file__).resolve().parent
DEFAULT_INPUTS_DIR = HERE.parent.parent / "inputs_d085_v3_6"

# Calibration grid dimensions (1,080 T + 540 P + 135 Kep + 216 H4RG + 240 G6 + 381 COMB = 2,592 trials)
TRANSIENT_INJECTION_PHASES = [-0.40, 0.0, 0.40]
TRANSIENT_INJECTION_SIGMAS = [4.0, 6.0, 8.0, 12.0, 18.0]  # 72 patches x 3 x 5 = 1,080
PERSISTENT_INJECTION_PHASES = [-0.40, 0.0, 0.40]
PERSISTENT_INJECTION_SIGMAS = [5.0, 7.0, 9.0, 12.0, 16.0]  # 36 patches x 3 x 5 = 540
KEPLERIAN_INJECTION_PHASES = [-0.40, 0.0, 0.40]
KEPLERIAN_EXP_SIGMAS = [3.5, 5.0, 6.5, 9.0, 12.0]  # 9 patches x 3 x 5 = 135
G6_CALIBRATION_SIGMAS = [6.0, 10.0, 16.0]  # 20 patches x 3 x 4 classes = 240
COMB_CALIBRATION_SPACINGS = [25.0, 50.0, 100.0]
COMB_CALIBRATION_SIGMAS = [1.8, 2.4, 3.0, 3.8, 4.8, 6.0]  # 16x3x6=288 + 16x3=48 + 15x3=45 = 381

# 9 evenly-spaced calibration bands per control star for Suite A/B/C (72 T + 36 P + 72 H4RG)
CALIB_9_BANDS = BENCHMARK_LASER_BANDS_V36[:9]
# 5 wide-YJHK bands per control star for Suite E G6 (4 controls x 5 = 20 patches)
CALIB_5_G6_BANDS = [
    BENCHMARK_LASER_BANDS_V36[1],  # S2_YBYAG_10300
    BENCHMARK_LASER_BANDS_V36[2],  # S3_NDYAG_10641
    BENCHMARK_LASER_BANDS_V36[4],  # S5_OBAND_13100
    BENCHMARK_LASER_BANDS_V36[6],  # S7_ER_CBAND_15500
    BENCHMARK_LASER_BANDS_V36[9],  # S10_HOYAG_20970
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def verify_prospective_lock(require_download_receipt: bool = True) -> None:
    mlock_p = HERE / "METHOD_LOCK.json"
    lrcpt_p = HERE / "LOCK_RECEIPT.json"
    if not (mlock_p.is_file() and lrcpt_p.is_file()):
        raise RuntimeError("Missing METHOD_LOCK.json or LOCK_RECEIPT.json")
    mlock = json.loads(mlock_p.read_text(encoding="utf-8"))
    lrcpt = json.loads(lrcpt_p.read_text(encoding="utf-8"))
    ml_sha = sha256_file(mlock_p)
    if ml_sha != lrcpt.get("method_lock_sha256"):
        raise RuntimeError("METHOD_LOCK.json SHA-256 does not match LOCK_RECEIPT.json")

    amended: dict[str, str] = {}
    ilock_p = HERE / "IMPLEMENTATION_LOCK.json"
    if ilock_p.is_file():
        ilock = json.loads(ilock_p.read_text(encoding="utf-8"))
        if ilock.get("parent_method_lock_sha256") != ml_sha:
            raise RuntimeError("IMPLEMENTATION_LOCK.json parent hash mismatch")
        amended = dict(ilock.get("amended_file_hashes", {}))

    for fn, expected_sha in mlock["locked_file_hashes"].items():
        fp = HERE / fn
        cur = sha256_file(fp) if fp.is_file() else "MISSING"
        if cur != expected_sha:
            if fn in amended and cur == amended[fn] and fn not in ("FROZEN_COHORT_D085.csv", "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json"):
                continue
            raise RuntimeError(f"Prospective lock violation on {fn}: expected {expected_sha}, got {cur}")

    if require_download_receipt:
        dl_p = HERE / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json"
        if not dl_p.is_file():
            raise RuntimeError("Missing FIRST_SCIENCE_DOWNLOAD_RECEIPT.json")
        dl = json.loads(dl_p.read_text(encoding="utf-8"))
        t_lock = dt.datetime.fromisoformat(lrcpt["lock_utc"].replace("Z", "+00:00"))
        t_dl = dt.datetime.fromisoformat(dl["first_download_utc"].replace("Z", "+00:00"))
        if t_dl <= t_lock:
            raise RuntimeError(f"Non-monotonic lock chronology: lock={lrcpt['lock_utc']} >= first_dl={dl['first_download_utc']}")


def _clean_json_floats(arr: np.ndarray, decimals: int = 6) -> list[float]:
    return [round(float(x), decimals) for x in arr]


def _clean_json_floats_with_nan_sentinel(arr: np.ndarray, decimals: int = 6) -> list[float | None]:
    out: list[float | None] = []
    for x in arr:
        v = float(x)
        out.append(round(v, decimals) if math.isfinite(v) else None)
    return out


def _arr_from_nullable(vals: list[float | None]) -> np.ndarray:
    return np.array([float("nan") if v is None else float(v) for v in vals], dtype=np.float64)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            clean = {}
            for k, v in r.items():
                if v is None:
                    clean[k] = ""
                elif isinstance(v, float):
                    if not math.isfinite(v):
                        raise ValueError(f"Non-finite float in {path.name} col {k}: {v}")
                    clean[k] = f"{v:.10g}"
                else:
                    clean[k] = v
            w.writerow(clean)


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
        except Exception:
            continue
    return out


def load_spirou_t_fits(path: Path, row: dict[str, str], bgrid: np.ndarray) -> dict[str, Any]:
    from astropy.io import fits

    with fits.open(path, memmap=False) as hdul:
        by_name = {hdu.name.upper(): hdu for hdu in hdul if getattr(hdu, "name", "")}
        hdr = _safe_header_dict(hdul[0].header)
        hdr.update(_safe_header_dict(hdul[1].header))
        fab = np.asarray((by_name.get("FLUXAB") or hdul[1]).data, dtype=np.float64)
        wab_nm = np.asarray((by_name.get("WAVEAB") or hdul[2]).data, dtype=np.float64)
        bab = np.asarray((by_name.get("BLAZEAB") or hdul[3]).data, dtype=np.float64)
        rec = np.asarray((by_name.get("RECON") or hdul[4]).data, dtype=np.float64)
        ohl_hdu = by_name.get("OHLINE") if "OHLINE" in by_name else (hdul[5] if len(hdul) > 5 else None)
        ohl = np.asarray(ohl_hdu.data, dtype=np.float64) if ohl_hdu is not None and ohl_hdu.data is not None else np.zeros_like(fab)
        fa_hdu = by_name.get("FLUXA") if "FLUXA" in by_name else (hdul[6] if len(hdul) > 6 else None)
        ba_hdu = by_name.get("BLAZEA") if "BLAZEA" in by_name else (hdul[8] if len(hdul) > 8 else None)
        fb_hdu = by_name.get("FLUXB") if "FLUXB" in by_name else (hdul[9] if len(hdul) > 9 else None)
        bb_hdu = by_name.get("BLAZEB") if "BLAZEB" in by_name else (hdul[11] if len(hdul) > 11 else None)
        fa = np.asarray(fa_hdu.data, dtype=np.float64) if fa_hdu is not None and fa_hdu.data is not None else None
        ba = np.asarray(ba_hdu.data, dtype=np.float64) if ba_hdu is not None and ba_hdu.data is not None else None
        fb = np.asarray(fb_hdu.data, dtype=np.float64) if fb_hdu is not None and fb_hdu.data is not None else None
        bb = np.asarray(bb_hdu.data, dtype=np.float64) if bb_hdu is not None and bb_hdu.data is not None else None

    if fab.shape != (49, 4088) or wab_nm.shape != (49, 4088):
        raise RuntimeError(f"Unexpected SPIRou *t shape on {row['dp_id']}: {fab.shape}")

    expt = float(hdr["EXPTIME"]) if hdr.get("EXPTIME") is not None else float(row["t_exptime"])
    mjd_obs = float(hdr["MJD-OBS"]) if hdr.get("MJD-OBS") is not None else float(row["mjd_obs"])
    mjd_mid = float(hdr["MJDMID"]) if hdr.get("MJDMID") is not None else float(row["mjd_mid"])
    bjd_tdb = float(hdr["BJD"]) if hdr.get("BJD") is not None else (mjd_mid + 2400000.5)
    berv_hdr = float(hdr["BERV"])
    berv_analyt = analytical_maunakea_berv_kms(float(row["s_ra"]), float(row["s_dec"]), mjd_mid)
    if abs(berv_hdr - berv_analyt) > 0.50:
        raise RuntimeError(f"Maunakea BERV mismatch on {row['dp_id']}: hdr={berv_hdr:.4f}, analyt={berv_analyt:.4f}")

    airm_raw = hdr.get("AIRMASS", 1.15)
    airmass = min(3.5, max(1.0, float(airm_raw) if isinstance(airm_raw, (int, float)) and math.isfinite(float(airm_raw)) else 1.15))
    snr_raw = hdr.get("EXTSN035", hdr.get("SPEMSNR", 60.0))
    snr_obs = float(snr_raw) if isinstance(snr_raw, (int, float)) and math.isfinite(float(snr_raw)) and float(snr_raw) > 0 else 60.0

    # Stitch 49 x 4088 orders onto uniform 0.050 A barycentric grid + topocentric flux grid
    nb = len(bgrid)
    num_post = np.zeros(nb, dtype=np.float64)
    den_post = np.zeros(nb, dtype=np.float64)
    num_pre = np.zeros(nb, dtype=np.float64)
    num_rec = np.zeros(nb, dtype=np.float64)
    num_oh = np.zeros(nb, dtype=np.float64)
    den_meta = np.zeros(nb, dtype=np.float64)
    num_topo = np.zeros(nb, dtype=np.float64)
    den_topo = np.zeros(nb, dtype=np.float64)

    segments: list[dict[str, Any]] = []
    bary_fac = 1.0 + berv_hdr / C_KMS
    px_all = np.arange(4088, dtype=np.int16)

    for o in range(49):
        wt_o = wab_nm[o] * 10.0  # topocentric vacuum Angstrom
        bl_o = bab[o]
        fl_o = fab[o]
        rc_o = np.clip(np.where(np.isfinite(rec[o]), rec[o], 1.0), 0.0, 1.0)
        oh_o = np.maximum(0.0, np.where(np.isfinite(ohl[o]), ohl[o], 0.0))

        m_blz = np.isfinite(wt_o) & np.isfinite(bl_o) & (bl_o > 0) & (wt_o >= 9550.0) & (wt_o <= 25200.0)
        if int(m_blz.sum()) < 250:
            continue
        blz_max = float(np.max(bl_o[m_blz]))
        m_blz &= bl_o >= 0.12 * blz_max
        if int(m_blz.sum()) < 200:
            continue
        med_b = exact_median_1d(bl_o[m_blz])
        scale_b = np.where(m_blz, bl_o / max(1e-12, med_b), np.nan)

        m_fl = m_blz & np.isfinite(fl_o) & (fl_o > 0)
        if int(m_fl.sum()) < 150:
            continue

        f_flat = np.full(4088, np.nan, dtype=np.float64)
        f_flat[m_fl] = fl_o[m_fl] / scale_b[m_fl]
        cont_est = exact_quantile_1d(f_flat[m_fl], 0.80)
        pre_flat = np.full(4088, np.nan, dtype=np.float64)
        pre_flat[m_fl] = (fl_o[m_fl] * np.clip(rc_o[m_fl], 0.05, 1.05) + oh_o[m_fl]) / scale_b[m_fl]
        oh_rel = np.full(4088, 0.0, dtype=np.float64)
        oh_rel[m_blz] = np.clip((oh_o[m_blz] / scale_b[m_blz]) / max(50.0, cont_est), 0.0, 20.0)

        # Dual polarimetric fiber fluxes (FluxA, FluxB) flattened by BlazeA, BlazeB
        fa_flat = np.full(4088, np.nan, dtype=np.float64)
        if fa is not None and ba is not None:
            m_a = m_blz & np.isfinite(fa[o]) & (fa[o] > 0) & np.isfinite(ba[o]) & (ba[o] > 0.12 * blz_max * 0.3)
            if int(m_a.sum()) >= 120:
                med_ba = exact_median_1d(ba[o][m_a])
                fa_flat[m_a] = fa[o][m_a] / (ba[o][m_a] / max(1e-12, med_ba))

        fb_flat = np.full(4088, np.nan, dtype=np.float64)
        if fb is not None and bb is not None:
            m_b = m_blz & np.isfinite(fb[o]) & (fb[o] > 0) & np.isfinite(bb[o]) & (bb[o] > 0.12 * blz_max * 0.3)
            if int(m_b.sum()) >= 120:
                med_bb = exact_median_1d(bb[o][m_b])
                fb_flat[m_b] = fb[o][m_b] / (bb[o][m_b] / max(1e-12, med_bb))

        wb_o = wt_o * bary_fac
        m_post = m_fl & (rc_o >= 0.25)
        idx_m = np.flatnonzero(m_blz)
        w_b_sub = wb_o[idx_m]
        if not np.all(np.diff(w_b_sub) > 0):
            ord_s = np.argsort(w_b_sub)
            idx_m = idx_m[ord_s]
            w_b_sub = w_b_sub[ord_s]

        # Stitch onto uniform barycentric grid inside [w_b_sub[0], w_b_sub[-1]]
        i0 = int(np.searchsorted(bgrid, float(w_b_sub[0]), side="left"))
        i1 = int(np.searchsorted(bgrid, float(w_b_sub[-1]), side="right"))
        if i1 > i0 + 5:
            bg_s = bgrid[i0:i1]
            wt_rel = np.interp(bg_s, w_b_sub, np.maximum(0.0, scale_b[idx_m]))
            rc_s = np.interp(bg_s, w_b_sub, rc_o[idx_m])
            oh_s = np.interp(bg_s, w_b_sub, oh_rel[idx_m])
            num_rec[i0:i1] += wt_rel * rc_s
            num_oh[i0:i1] += wt_rel * oh_s
            den_meta[i0:i1] += wt_rel

            m_ps = m_post[idx_m]
            if int(m_ps.sum()) >= 100:
                w_ps = w_b_sub[m_ps]
                fp_s = np.interp(bg_s, w_ps, f_flat[idx_m][m_ps])
                pr_s = np.interp(bg_s, w_ps, pre_flat[idx_m][m_ps])
                ok_g = (bg_s >= w_ps[0]) & (bg_s <= w_ps[-1]) & (rc_s >= 0.25)
                # Mask tiny telluric holes inside w_ps
                in_hole = np.interp(bg_s, w_b_sub, (~m_post[idx_m]).astype(np.float64)) > 0.45
                ok_g &= (~in_hole) & np.isfinite(fp_s) & (fp_s > 0)
                wg = np.where(ok_g, wt_rel * np.clip(rc_s, 0.25, 1.0), 0.0)
                num_post[i0:i1] += np.where(ok_g, wg * fp_s, 0.0)
                num_pre[i0:i1] += np.where(ok_g, wg * pr_s, 0.0)
                den_post[i0:i1] += wg

        # Topocentric 1D stitch for V4 COMB anti-comb veto
        w_t_sub = wt_o[idx_m]
        j0 = int(np.searchsorted(bgrid, float(w_t_sub[0]), side="left"))
        j1 = int(np.searchsorted(bgrid, float(w_t_sub[-1]), side="right"))
        if j1 > j0 + 5 and int(m_post[idx_m].sum()) >= 100:
            tg_s = bgrid[j0:j1]
            m_ps = m_post[idx_m]
            w_ps_t = w_t_sub[m_ps]
            fp_t = np.interp(tg_s, w_ps_t, f_flat[idx_m][m_ps])
            wt_t = np.interp(tg_s, w_t_sub, np.maximum(0.0, scale_b[idx_m]))
            rc_t = np.interp(tg_s, w_t_sub, rc_o[idx_m])
            in_h = np.interp(tg_s, w_t_sub, (~m_post[idx_m]).astype(np.float64)) > 0.45
            ok_t = (tg_s >= w_ps_t[0]) & (tg_s <= w_ps_t[-1]) & (rc_t >= 0.25) & (~in_h) & np.isfinite(fp_t) & (fp_t > 0)
            wgt = np.where(ok_t, wt_t * np.clip(rc_t, 0.25, 1.0), 0.0)
            num_topo[j0:j1] += np.where(ok_t, wgt * fp_t, 0.0)
            den_topo[j0:j1] += wgt

        # Store native order segment clipped to [m_blz] range for fast binary/patch slicing
        i_min, i_max = int(np.flatnonzero(m_blz)[0]), int(np.flatnonzero(m_blz)[-1]) + 1
        segments.append({
            "order": o,
            "n_px": 4088,
            "px": px_all[i_min:i_max],
            "wave_bary_a": wb_o[i_min:i_max].astype(np.float64),
            "flux_post": np.where(rc_o[i_min:i_max] >= 0.20, f_flat[i_min:i_max], np.nan).astype(np.float32),
            "flux_a": np.where(rc_o[i_min:i_max] >= 0.20, fa_flat[i_min:i_max], np.nan).astype(np.float32),
            "flux_b": np.where(rc_o[i_min:i_max] >= 0.20, fb_flat[i_min:i_max], np.nan).astype(np.float32),
        })

    s1d_post = np.where(den_post > 0, num_post / np.maximum(den_post, 1e-12), np.nan)
    s1d_pre = np.where(den_post > 0, num_pre / np.maximum(den_post, 1e-12), np.nan)
    s1d_recon = np.where(den_meta > 0, num_rec / np.maximum(den_meta, 1e-12), 0.0)
    s1d_oh_rel = np.where(den_meta > 0, num_oh / np.maximum(den_meta, 1e-12), 0.0)
    s1d_topo = np.where(den_topo > 0, num_topo / np.maximum(den_topo, 1e-12), np.nan)

    return {
        "row": row,
        "dp_id": row["dp_id"],
        "star": row["canonical_target"],
        "exptime_s": expt,
        "airmass_eff": airmass,
        "snr_obs": snr_obs,
        "mjd_obs": mjd_obs,
        "mjd_mid": mjd_mid,
        "bjd_tdb": bjd_tdb,
        "berv_hdr_kms": berv_hdr,
        "berv_analytical_kms": berv_analyt,
        "s1d_post": s1d_post,
        "s1d_pre": s1d_pre,
        "s1d_recon": s1d_recon,
        "s1d_oh_rel": s1d_oh_rel,
        "s1d_topo": s1d_topo,
        "segments": segments,
    }


def build_order_patches_for_wave(
    bary_vac_a: float,
    segments: list[dict[str, Any]],
    ref_bary_pair: tuple[np.ndarray, np.ndarray] | None,
    v_star_kms: float,
    half_win: int = 75,
) -> list[dict[str, Any]]:
    patches = []
    for seg in segments:
        wb = seg["wave_bary_a"]
        if len(wb) < 40 or not (float(wb[0]) <= bary_vac_a <= float(wb[-1])):
            continue
        k = int(np.argmin(np.abs(wb - bary_vac_a)))
        if k < 15 or k >= len(wb) - 15:
            continue
        i0, i1 = max(0, k - half_win), min(len(wb), k + half_win + 1)
        w_sl = wb[i0:i1]
        f_sl = np.asarray(seg["flux_post"][i0:i1], dtype=np.float64)
        if int(np.sum(np.isfinite(f_sl) & (f_sl > 0))) < 25:
            continue
        ref_sl = None
        if ref_bary_pair is not None:
            rw, rf = ref_bary_pair
            if len(rw) > 10:
                ref_raw = np.interp(w_sl, rw, rf, left=1.0, right=1.0)
                ref_sl = _clean_json_floats_with_nan_sentinel(ref_raw, 5)
        fa_sl = np.asarray(seg["flux_a"][i0:i1], dtype=np.float64)
        fb_sl = np.asarray(seg["flux_b"][i0:i1], dtype=np.float64)
        patches.append({
            "order": int(seg["order"]),
            "native_px": int(seg["px"][k]),
            "n_px": int(seg["n_px"]),
            "target_wave_a": float(bary_vac_a),
            "wave": _clean_json_floats(w_sl, 5),
            "flux": _clean_json_floats_with_nan_sentinel(f_sl, 3),
            "flux_a": _clean_json_floats_with_nan_sentinel(fa_sl, 3) if int(np.sum(np.isfinite(fa_sl) & (fa_sl > 0))) >= 25 else None,
            "flux_b": _clean_json_floats_with_nan_sentinel(fb_sl, 3) if int(np.sum(np.isfinite(fb_sl) & (fb_sl > 0))) >= 25 else None,
            "ref_norm": ref_sl,
        })
    return patches


def find_primary_order_px_for_bary(bary_vac_a: float, segments: list[dict[str, Any]]) -> tuple[int | None, int | None]:
    best = None
    best_med = -1.0
    for seg in segments:
        wb = seg["wave_bary_a"]
        if len(wb) < 30 or not (float(wb[0]) <= bary_vac_a <= float(wb[-1])):
            continue
        k = int(np.argmin(np.abs(wb - bary_vac_a)))
        if 12 <= k < len(wb) - 12:
            sub = np.asarray(seg["flux_post"][max(0, k - 25) : min(len(wb), k + 26)], dtype=np.float64)
            fin = sub[np.isfinite(sub) & (sub > 0)]
            if len(fin) >= 12:
                mv = exact_median_1d(fin)
                if mv > best_med:
                    best_med, best = mv, (int(seg["order"]), int(seg["px"][k]))
    return best if best is not None else (None, None)


def _topo_airglow_safe(topo_a: float, min_sep: float = 0.60) -> bool:
    for bnd in SPIROU_TELLURIC_BANDS_TOPO_VAC_A:
        if (float(bnd["lo_vac_A"]) - 5.0) <= topo_a <= (float(bnd["hi_vac_A"]) + 5.0):
            return False
    return all(abs(topo_a - float(ag["wave_vac_A"])) >= min_sep for ag in SPIROU_OH_AIRGLOW_VAC_A)


def _rest_chromo_safe(rest_a: float, min_sep: float = 1.50) -> bool:
    return all(abs(rest_a - float(ch["rest_vac_A"])) >= min_sep for ch in STELLAR_CHROMOSPHERIC_VAC_A)


def _native_order_interior_ok(segments: list[dict[str, Any]], bary_a: float) -> bool:
    for seg in segments:
        wb = seg["wave_bary_a"]
        if len(wb) < 120 or not (float(wb[0]) < bary_a < float(wb[-1])):
            continue
        k = int(np.argmin(np.abs(wb - bary_a)))
        if not (65 <= k < len(wb) - 65):
            continue
        px = int(seg["px"][k])
        if not (65 <= px <= seg["n_px"] - 66):
            continue
        fl = np.asarray(seg["flux_post"][k - 70 : k + 71], dtype=np.float64)
        fa = np.asarray(seg["flux_a"][k - 10 : k + 11], dtype=np.float64)
        fb = np.asarray(seg["flux_b"][k - 10 : k + 11], dtype=np.float64)
        if np.all(np.isfinite(fl[60:81])) and int(np.isfinite(fl).sum()) >= 95:
            if np.all(np.isfinite(fa)) and np.all(np.isfinite(fb)):
                return True
    return False


def compute_other_stars_fn_max_pm0p16(target_star: str, rest_wave_a: float, bgrid: np.ndarray, star_c_sub: dict[str, np.ndarray]) -> dict[str, float]:
    out: dict[str, float] = {}
    i0 = max(0, int(np.searchsorted(bgrid, rest_wave_a - 0.16, side="left")))
    i1 = min(len(bgrid), int(np.searchsorted(bgrid, rest_wave_a + 0.16, side="right")))
    if i1 <= i0:
        return out
    for ost, arr in star_c_sub.items():
        if ost == target_star:
            continue
        sub = arr[i0:i1]
        fin = sub[np.isfinite(sub)]
        if len(fin) > 0:
            out[ost] = round(float(np.max(fin)), 5)
    return out


def measure_band_mad_clean(wave: np.ndarray, resid: np.ndarray, nominal_vac_a: float) -> float:
    for rad in (15.0, 45.0, 120.0, 280.0, 600.0):
        m = (np.abs(wave - nominal_vac_a) <= rad) & np.isfinite(resid) & is_in_clean_windows(wave)
        if int(m.sum()) >= 25:
            md = exact_mad_1d(resid[m])
            if math.isfinite(md) and md > 0.0:
                return float(md)
    fin = np.isfinite(resid) & is_in_clean_windows(wave)
    return float(exact_mad_1d(resid[fin])) if int(fin.sum()) > 10 else 0.02


def select_clean_rest_wave_spirou(
    nominal_rest_a: float,
    target_star: str,
    bgrid: np.ndarray,
    c_sub: np.ndarray,
    star_c_sub: dict[str, np.ndarray],
    bervs: list[float],
    v_star: float,
    step_c: float,
    rep_segments: list[dict[str, Any]],
    recon_rep: np.ndarray,
    oh_rep: np.ndarray,
    extra_bary_checks: list[tuple[np.ndarray, np.ndarray]] | None = None,
) -> int:
    k_nom = int(np.argmin(np.abs(bgrid - nominal_rest_a)))
    for span in (25.0, 75.0, 180.0, 420.0, 800.0):
        hb = int(round(span / step_c))
        lo, hi = max(180, k_nom - hb), min(len(bgrid) - 181, k_nom + hb)
        best_k, best_sc = None, -1e9
        for k in range(lo, hi + 1, 2 if span <= 90 else 6):
            wr = float(bgrid[k])
            if not is_in_clean_windows(wr) or not _rest_chromo_safe(wr):
                continue
            if not np.all(np.isfinite(c_sub[k - 10 : k + 11])):
                continue
            if int(np.isfinite(c_sub[k - 140 : k - 10]).sum()) < 45 or int(np.isfinite(c_sub[k + 11 : k + 141]).sum()) < 45:
                continue
            bw = wr * (1.0 + v_star / C_KMS)
            kb = int(np.argmin(np.abs(bgrid - bw)))
            if kb < 165 or kb >= len(bgrid) - 165:
                continue
            if float(np.min(recon_rep[kb - 4 : kb + 5])) < 0.86 or float(np.max(oh_rep[kb - 2 : kb + 3])) > 0.03:
                continue
            if not _native_order_interior_ok(rep_segments, bw):
                continue
            if not all(_topo_airglow_safe(bw / (1.0 + bv / C_KMS)) for bv in bervs):
                continue
            mv = float(np.min(c_sub[k - 3 : k + 4]))
            if extra_bary_checks:
                ok_x = True
                for fep, rep in extra_bary_checks:
                    if not np.all(np.isfinite(fep[kb - 8 : kb + 9])):
                        ok_x = False
                        break
                    if int(np.isfinite(fep[kb - 140 : kb - 10]).sum()) < 40 or int(np.isfinite(fep[kb + 11 : kb + 141]).sum()) < 40:
                        ok_x = False
                        break
                    if float(np.min(rep[kb - 4 : kb + 5])) < 0.86:
                        ok_x = False
                        break
                    mv = min(mv, float(np.min(fep[kb - 2 : kb + 3])))
                if not ok_x:
                    continue
            oth = compute_other_stars_fn_max_pm0p16(target_star, wr, bgrid, star_c_sub)
            if sum(1 for v in oth.values() if v >= 1.022) > (2 if span <= 250.0 else 6):
                continue
            sc = mv - 0.0010 * abs(wr - nominal_rest_a)
            if sc > best_sc:
                best_sc, best_k = sc, k
        if best_k is not None:
            return best_k
    raise RuntimeError(f"No clean continuum patch near {nominal_rest_a} A for {target_star}")


def _rolling_local_sigma(bgrid: np.ndarray, y: np.ndarray, block_bins: int = 400) -> np.ndarray:
    """Fast local MAD uncertainty across clean windows for Comb Z-scoring."""
    out = np.full(len(bgrid), np.nan, dtype=np.float64)
    in_w = is_in_clean_windows(bgrid)
    assert isinstance(in_w, np.ndarray)
    n = len(bgrid)
    for b0 in range(0, n, block_bins):
        b1 = min(n, b0 + block_bins)
        m = in_w[b0:b1] & np.isfinite(y[b0:b1])
        if int(m.sum()) >= 30:
            md = exact_mad_1d(y[b0:b1][m])
            if math.isfinite(md) and md > 1e-6:
                out[b0:b1][m] = md
    # Fallback fill inside any thin edge blocks
    fin = np.isfinite(out)
    if np.any(fin):
        glob = exact_median_1d(out[fin])
        out = np.where(in_w & np.isfinite(y), np.where(np.isfinite(out), out, glob), np.nan)
    return out


# ---------------------------------------------------------------------------
# Stage A: Build Bounded Bundle from 177 Full SPIRou APERO `*t.fits` Spectra
# ---------------------------------------------------------------------------

def build_bounded_bundle_from_full_inputs(
    cohort_rows: list[dict[str, str]],
    kin_catalog: dict[str, Any],
    excl_verif: dict[str, Any],
    full_inputs_dir: Path,
) -> dict[str, Any]:
    man = json.loads((full_inputs_dir / "FULL_SPIROU_INPUT_MANIFEST.json").read_text(encoding="utf-8"))
    man_by_dp = {x["dp_id"]: x for x in man["exposures"]}
    excl_dps = set(excl_verif["excluded_dp_ids"]) | set(excl_verif["format_check_excluded_dp_ids"])
    ov = sorted({r["dp_id"] for r in cohort_rows} & excl_dps)
    if ov:
        raise RuntimeError(f"Exclusion overlap detected: {ov}")

    cfg = get_inst_config("SPIROU")
    step_c = float(cfg["coadd_step_angstrom"])
    bgrid = np.round(np.arange(cfg["wave_min_angstrom"], cfg["wave_max_angstrom"] + 0.5 * step_c, step_c), 5)

    print(f"[Stage A.1] Loading & SHA-256 verifying {len(cohort_rows)} CFHT SPIRou APERO `*t.fits` spectra...", flush=True)
    raw_exps: dict[str, dict[str, Any]] = {}
    by_star: dict[str, list[str]] = {}
    rows_by_dp: dict[str, dict[str, str]] = {}

    for idx, r in enumerate(cohort_rows, start=1):
        dp = r["dp_id"]
        st = r["canonical_target"]
        mitem = man_by_dp[dp]
        fpath = full_inputs_dir / mitem["fits_relpath"]
        if sha256_file(fpath) != mitem["fits_sha256"]:
            raise RuntimeError(f"SHA-256 mismatch on SPIRou {dp}")
        rec = load_spirou_t_fits(fpath, r, bgrid)
        raw_exps[dp] = rec
        by_star.setdefault(st, []).append(dp)
        rows_by_dp[dp] = r
        if idx % 35 == 0 or idx == len(cohort_rows):
            print(f"    Loaded {idx}/{len(cohort_rows)} SPIRou *t.fits...", flush=True)

    print("[Stage A.2] Fitting 2,124 NIST YJHK RV anchors, continuum-normalizing, & building self/KNN templates...", flush=True)
    provenance_rows: list[dict[str, Any]] = []
    rv_anchor_bundle: dict[str, Any] = {}
    exp_records: dict[str, dict[str, Any]] = {}
    star_rest_vecs: dict[str, list[np.ndarray]] = {}
    star_recon_rest_vecs: dict[str, list[np.ndarray]] = {}
    star_oh_rest_vecs: dict[str, list[np.ndarray]] = {}
    star_params: dict[str, tuple[float, float]] = {}

    for dp, rec in raw_exps.items():
        r = rec["row"]
        st = r["canonical_target"]
        prior_rv = float(r["prior_rv_kms"])
        s1d_post = rec["s1d_post"]
        cont = compute_windowed_continuum(bgrid, s1d_post, cfg)
        f_norm = np.where(np.isfinite(cont) & (cont > 0), s1d_post / cont, np.nan)

        win_bundle: dict[str, Any] = {}
        clean_rvs: list[float] = []
        for anc in LOCKED_SPIROU_RV_ANCHORS:
            aid = anc["anchor_id"]
            lab = float(anc["lab_vac_A"])
            wv, fv = extract_rv_anchor_window(bgrid, s1d_post, lab, prior_rv, cfg)
            fit = fit_single_rv_anchor(wv, fv, lab, prior_rv, cfg)
            if fit["status"] == "CLEAN_ABSORPTION":
                clean_rvs.append(fit["best_rv_kms"])
            win_bundle[aid] = {"wave": _clean_json_floats(wv, 5), "flux": _clean_json_floats_with_nan_sentinel(fv, 2)}

        n_clean = len(clean_rvs)
        if n_clean >= int(cfg["rv_anchor_min_clean_lines"]):
            v_star = exact_median_1d(np.asarray(clean_rvs, dtype=np.float64))
            rv_src = "EMPIRICAL_NIST_ANCHORS"
        else:
            v_star = prior_rv
            rv_src = "PRIOR_FALLBACK"

        rv_anchor_bundle[dp] = {"prior_rv_kms": prior_rv, "rv_source": rv_src, "n_clean_anchors": n_clean, "windows": win_bundle}
        provenance_rows.append({
            "phase_id": "D085",
            "instrument": "SPIROU",
            "star": st,
            "common_name": r["common_name"],
            "role": r["role"],
            "subrole": r["subrole"],
            "radio_mm_id": r["radio_mm_id"],
            "dp_id": dp,
            "obs_id": r["obs_id"],
            "s_ra_deg": float(r["s_ra"]),
            "s_dec_deg": float(r["s_dec"]),
            "mjd_obs": rec["mjd_obs"],
            "mjd_mid": rec["mjd_mid"],
            "bjd_tdb": rec["bjd_tdb"],
            "exptime_s": rec["exptime_s"],
            "airmass_eff": rec["airmass_eff"],
            "snr_obs": rec["snr_obs"],
            "berv_kms": rec["berv_hdr_kms"],
            "berv_analytical_kms": rec["berv_analytical_kms"],
            "n_clean_rv_anchors": n_clean,
            "rv_source": rv_src,
            "v_star_est_kms": v_star,
            "vshift_kms": rec["berv_hdr_kms"] - v_star,
            "header_gate": "PASS",
        })

        # Stellar rest-frame shift
        w_rest_of_bary = bgrid * (1.0 + v_star / C_KMS)
        fn_rest = np.interp(w_rest_of_bary, bgrid, f_norm, left=np.nan, right=np.nan)
        rc_rest = np.interp(w_rest_of_bary, bgrid, rec["s1d_recon"], left=0.0, right=0.0)
        oh_rest = np.interp(w_rest_of_bary, bgrid, rec["s1d_oh_rel"], left=0.0, right=0.0)
        star_rest_vecs.setdefault(st, []).append(fn_rest)
        star_recon_rest_vecs.setdefault(st, []).append(rc_rest)
        star_oh_rest_vecs.setdefault(st, []).append(oh_rest)
        star_params[st] = (float(r["teff_k"]), float(r["mh_dex"]))

        v2_res = run_legacy_v2_spirou_benchmark(bgrid, s1d_post, cfg)

        exp_records[dp] = {
            "row": r,
            "dp_id": dp,
            "star": st,
            "snr_obs": float(rec["snr_obs"]),
            "berv_kms": rec["berv_hdr_kms"],
            "v_star_kms": v_star,
            "vshift_kms": rec["berv_hdr_kms"] - v_star,
            "f_norm": f_norm.astype(np.float32),
            "fn_rest": fn_rest.astype(np.float32),
            "s1d_pre": rec["s1d_pre"].astype(np.float32),
            "s1d_post": s1d_post.astype(np.float32),
            "s1d_recon": rec["s1d_recon"].astype(np.float32),
            "s1d_oh_rel": rec["s1d_oh_rel"].astype(np.float32),
            "segments": rec["segments"],
            "v2_res": v2_res,
        }

    raw_exps.clear()
    gc.collect()

    print("[Stage A.3] Computing leave-one-out self templates, KNN cross-star photospheric atlases & YJHK residuals...", flush=True)
    star_c_sub: dict[str, np.ndarray] = {}
    star_matched_atlas: dict[str, np.ndarray] = {}
    star_atlas_meta: dict[str, dict[str, Any]] = {}
    star_recon_rest: dict[str, np.ndarray] = {}
    star_oh_rest: dict[str, np.ndarray] = {}
    star_y_topo: dict[str, np.ndarray] = {}
    star_sigma_topo: dict[str, np.ndarray] = {}

    for st in sorted(by_star.keys()):
        dps = by_star[st]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            star_c_sub[st] = np.asarray(np.nanmedian(np.vstack(star_rest_vecs[st]), axis=0), dtype=np.float64)
            star_recon_rest[st] = np.asarray(np.nanmedian(np.vstack(star_recon_rest_vecs[st]), axis=0), dtype=np.float64)
            star_oh_rest[st] = np.asarray(np.nanmedian(np.vstack(star_oh_rest_vecs[st]), axis=0), dtype=np.float64)

    star_rest_vecs.clear()
    star_recon_rest_vecs.clear()
    star_oh_rest_vecs.clear()
    gc.collect()

    for st in sorted(by_star.keys()):
        raw_atl, knn_names, knn_w = build_knn_photospheric_atlas(st, star_c_sub, star_params, cfg)
        matched_atl, mmeta = match_cross_star_atlas(bgrid, star_c_sub[st], raw_atl)
        star_matched_atlas[st] = matched_atl
        star_atlas_meta[st] = {
            "knn_neighbors": knn_names,
            "knn_weights": knn_w,
            **mmeta,
        }

    def _interp_gap_safe(x_eval: np.ndarray, x_src: np.ndarray, y_src: np.ndarray, max_gap: float = 0.14) -> np.ndarray:
        fin = np.isfinite(y_src)
        if int(fin.sum()) < 50:
            return np.full(len(x_eval), np.nan, dtype=np.float64)
        xf, yf = x_src[fin], y_src[fin]
        yr = np.interp(x_eval, xf, yf, left=np.nan, right=np.nan)
        ix = np.searchsorted(xf, x_eval)
        dl = np.abs(x_eval - xf[np.clip(ix - 1, 0, len(xf) - 1)])
        dr = np.abs(x_eval - xf[np.clip(ix, 0, len(xf) - 1)])
        return np.where(np.minimum(dl, dr) > max_gap, np.nan, yr)

    # Build per-exposure self template, cross template, y_self, y_cross, u_ext & photosphere-subtracted topocentric stack
    for st, dps in sorted(by_star.items()):
        n_e = len(dps)
        mat_rest = np.vstack([np.asarray(exp_records[d]["fn_rest"], dtype=np.float64) for d in dps])
        mm = star_matched_atlas[st]
        topo_res_list: list[np.ndarray] = []
        bervs_st: list[float] = []
        for idx_d, d in enumerate(dps):
            re = exp_records[d]
            others = [j for j in range(n_e) if j != idx_d]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                self_rest = np.asarray(np.nanmedian(mat_rest[others, :], axis=0), dtype=np.float64)
            w_bary_of_rest = bgrid / (1.0 + re["v_star_kms"] / C_KMS)
            t_self_raw = np.interp(w_bary_of_bary := w_bary_of_rest, bgrid, self_rest, left=np.nan, right=np.nan)
            t_cross_raw = np.interp(w_bary_of_bary, bgrid, mm, left=np.nan, right=np.nan)
            fn = np.asarray(re["f_norm"], dtype=np.float64)
            from v3_6_detector import align_template_multiplicative
            t_self = align_template_multiplicative(fn, t_self_raw)
            t_cross = align_template_multiplicative(fn, t_cross_raw)
            t_ext = np.where(np.isfinite(t_cross), t_cross, t_self)
            y_self = np.where(np.isfinite(fn) & np.isfinite(t_self), fn - t_self, np.nan)
            y_cross = np.where(np.isfinite(fn) & np.isfinite(t_cross), fn - t_cross, np.nan)
            res_bary = np.where(np.isfinite(fn) & np.isfinite(t_ext), fn - t_ext, np.nan)
            u_bary = np.where(np.isfinite(res_bary), 1.0 + res_bary, np.nan)
            w_rest_b = bgrid * (1.0 + re["v_star_kms"] / C_KMS)
            re["t_self"] = t_self.astype(np.float32)
            re["t_ext"] = t_ext.astype(np.float32)
            re["y_self"] = y_self.astype(np.float32)
            re["y_cross"] = y_cross.astype(np.float32)
            re["u_ext"] = _interp_gap_safe(w_rest_b, bgrid, u_bary).astype(np.float32)

            w_bary_of_topo = bgrid * (1.0 + float(re["berv_kms"]) / C_KMS)
            topo_res_list.append(_interp_gap_safe(w_bary_of_topo, bgrid, res_bary).astype(np.float32))
            bervs_st.append(float(re["berv_kms"]))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            yt = np.asarray(np.nanmedian(np.vstack([v.astype(np.float64) for v in topo_res_list]), axis=0), dtype=np.float64)
        fin_t = np.isfinite(yt)
        if int(fin_t.sum()) > 100:
            yt_f = np.interp(np.arange(len(bgrid)), np.flatnonzero(fin_t), yt[fin_t])
            yt_hp = np.where(fin_t, yt - median_filter(yt_f, size=101, mode="nearest"), np.nan)
        else:
            yt_hp = yt
        med_berv_s = exact_median_1d(np.asarray(bervs_st, dtype=np.float64))
        v_star_s = float(exp_records[dps[0]]["v_star_kms"])
        w_topo_for_rest = bgrid * (1.0 + v_star_s / C_KMS) / (1.0 + med_berv_s / C_KMS)
        yt_rest_idx = _interp_gap_safe(w_topo_for_rest, bgrid, yt_hp)
        star_y_topo[st] = yt_rest_idx
        star_sigma_topo[st] = _rolling_local_sigma(bgrid, yt_rest_idx)

    print("[Stage A.4] Extracting Dense (V3.5) and Sparse Supraphotospheric (V3.6) Topocentric Coincidence Atlases...", flush=True)
    dense_atlas: list[dict[str, Any]] = []
    sparse_atlas: list[dict[str, Any]] = []
    in_win_mask = is_in_clean_windows(bgrid)
    assert isinstance(in_win_mask, np.ndarray)
    step_a = float(cfg["coadd_step_angstrom"])

    for r in cohort_rows:
        dp = r["dp_id"]
        st = r["canonical_target"]
        re = exp_records[dp]
        ys = np.asarray(re["y_self"], dtype=np.float64)
        fn = np.asarray(re["f_norm"], dtype=np.float64)
        margin = int(cfg["scan_margin_bins"])
        fwhm_lsf_bins = (16500.0 / cfg["resolving_power"]) / step_a
        # Fast contiguous clean window iteration
        padded = np.r_[False, in_win_mask, False]
        diffs = np.diff(padded.astype(np.int8))
        for a, b in zip(np.flatnonzero(diffs == 1), np.flatnonzero(diffs == -1)):
            if b - a < 2 * margin + 10:
                continue
            yp = ys[a:b]
            fin = np.isfinite(yp)
            if int(fin.sum()) < 200:
                continue
            idx_f = np.flatnonzero(fin)
            vals = np.interp(np.arange(len(yp)), idx_f, yp[idx_f])
            med = median_filter(vals, size=101, mode="nearest")
            res = vals - med
            mad = MAD_NORM * median_filter(np.abs(res), size=101, mode="nearest")
            lmax = np.r_[False, (res[1:-1] > res[:-2]) & (res[1:-1] >= res[2:]), False]
            ok_idx = lmax & fin & (mad > 0) & (res >= float(cfg["gate_g6_dense_prom_min"])) & (res >= float(cfg["gate_g6_dense_snr_min"]) * mad)
            ok_idx[:margin] = False
            ok_idx[-margin:] = False
            for j in np.flatnonzero(ok_idx):
                k = a + int(j)
                pk_v = float(res[j])
                snr_l = float(pk_v / mad[j])
                hm = 0.5 * pk_v
                ll = int(j)
                while ll > max(0, j - 30) and res[ll] > hm:
                    ll -= 1
                rr = int(j)
                while rr < min(len(res) - 1, j + 30) and res[rr] > hm:
                    rr += 1
                fwhm_meas_bins = max(1.0, float(rr - ll))
                fwhm_ratio = fwhm_meas_bins / fwhm_lsf_bins
                if fwhm_ratio > 4.8:
                    continue
                bary_k = float(bgrid[k])
                rest_k = bary_k / (1.0 + re["v_star_kms"] / C_KMS)
                if not _rest_chromo_safe(rest_k, 1.0):
                    continue
                topo_k = bary_k / (1.0 + re["berv_kms"] / C_KMS)
                ord_p, px_p = find_primary_order_px_for_bary(bary_k, re["segments"])
                fn_sub = fn[max(0, k - 1) : min(len(fn), k + 2)]
                fn_pk3 = float(np.max(fn_sub[np.isfinite(fn_sub)])) if np.any(np.isfinite(fn_sub)) else 1.0
                rec_entry = {
                    "star": st,
                    "dp_id": dp,
                    "berv_kms": round(float(re["berv_kms"]), 4),
                    "vshift_kms": round(float(re["vshift_kms"]), 4),
                    "topo_vac_a": round(topo_k, 5),
                    "order": ord_p,
                    "px": px_p,
                    "prom_rel": round(pk_v, 5),
                    "snr_local": round(snr_l, 3),
                    "f_norm_pk3": round(fn_pk3, 5),
                    "fwhm_over_lsf": round(fwhm_ratio, 3),
                }
                dense_atlas.append(rec_entry)
                if (
                    pk_v >= float(cfg["gate_g6_sparse_prom_min"])
                    and snr_l >= float(cfg["gate_g6_sparse_snr_min"])
                    and fn_pk3 >= float(cfg["gate_g6_sparse_fn_min"])
                    and float(cfg["gate_g6_sparse_fwhm_lsf_min"]) <= fwhm_ratio <= float(cfg["gate_g6_sparse_fwhm_lsf_max"])
                ):
                    sparse_atlas.append(rec_entry)

    print(f"  [G6 Atlas Comparison] Dense V3.5 peaks = {len(dense_atlas):,} vs Sparse V3.6 peaks = {len(sparse_atlas):,} ({len(dense_atlas)/max(1,len(sparse_atlas)):.1f}x sparsity ratio)", flush=True)

    print("[Stage A.5] Scanning Channel T across all 177 exposures & measuring 12-band YJHK noise...", flush=True)
    channel_t_candidates_bundle = []
    searched_summary_by_dp = {}
    band_noise_rows = []

    for row in cohort_rows:
        dp = row["dp_id"]
        st = row["canonical_target"]
        re = exp_records[dp]
        margin = int(cfg["scan_margin_bins"])
        ys = np.asarray(re["y_self"], dtype=np.float64)
        yc = np.asarray(re["y_cross"], dtype=np.float64)
        fn = np.asarray(re["f_norm"], dtype=np.float64)
        tr = np.asarray(re["s1d_recon"], dtype=np.float64)
        oh = np.asarray(re["s1d_oh_rel"], dtype=np.float64)
        pr = np.asarray(re["s1d_pre"], dtype=np.float64)
        po = np.asarray(re["s1d_post"], dtype=np.float64)
        te = np.asarray(re["t_ext"], dtype=np.float64)

        hits_t, srch_t, _ = scan_1d_channel_candidates(bgrid, ys, "T", cfg, y_secondary_check=yc, flux_norm_for_f1=fn, enforce_f1_in_g1=True)
        _, _, v31_pre = scan_1d_channel_candidates(bgrid, ys, "T", cfg, y_secondary_check=yc, flux_norm_for_f1=fn, enforce_f1_in_g1=False)
        searched_summary_by_dp[dp] = {
            "v2_searched_bins": re["v2_res"]["searched_samples"],
            "v2_screened_events": re["v2_res"]["screened_events"],
            "v2_accepted_hits": re["v2_res"]["accepted_hits"],
            "v31_pre_f1_g1_hits": v31_pre,
            "v36_channel_t_searched_bins": srch_t,
        }
        for bnd in BENCHMARK_LASER_BANDS_V36:
            md_b = measure_band_mad_clean(bgrid, ys, float(bnd["center_vac_A"]))
            band_noise_rows.append({"star": st, "dp_id": dp, "band_id": bnd["band_id"], "empirical_resid_mad_t": round(md_b, 8)})

        fm_s = np.isfinite(te)
        for h in hits_t:
            k = h["seed_index"]
            sl = slice(k - margin, k + margin + 1)
            bary_a = float(h["fitted_center_a"])
            rest_a = bary_a / (1.0 + re["v_star_kms"] / C_KMS)
            kc = max(45, min(len(bgrid) - 46, int(np.argmin(np.abs(bgrid - bary_a)))))
            slg = slice(kc - 45, kc + 46)
            oth_fn = compute_other_stars_fn_max_pm0p16(st, rest_a, bgrid, star_c_sub)
            g2_pre = evaluate_gate_g2_spirou_atmosphere(bary_a, re["berv_kms"], bgrid[slg], tr[slg], oh[slg], pr[slg], po[slg], h["amp_mid"], cfg)
            ord_patches = build_order_patches_for_wave(bary_a, re["segments"], (bgrid[fm_s], te[fm_s]), re["v_star_kms"]) if g2_pre["g2_pass"] else []
            channel_t_candidates_bundle.append({
                "channel": "T",
                "dp_id": dp,
                "star": st,
                "role": row["role"],
                "berv_kms": re["berv_kms"],
                "v_star_kms": re["v_star_kms"],
                "vshift_kms": re["vshift_kms"],
                "dv_orb_kms": 0.0,
                "seed_wave_a": float(bgrid[k]),
                "wave_win": _clean_json_floats(bgrid[sl]),
                "y_primary_win": _clean_json_floats_with_nan_sentinel(ys[sl]),
                "y_secondary_win": _clean_json_floats_with_nan_sentinel(yc[sl]),
                "f_norm_win": _clean_json_floats_with_nan_sentinel(fn[sl]),
                "s1d_wave_win": _clean_json_floats(bgrid[slg]),
                "s1d_recon_win": _clean_json_floats_with_nan_sentinel(tr[slg], 5),
                "s1d_oh_rel_win": _clean_json_floats_with_nan_sentinel(oh[slg], 5),
                "s1d_pre_win": _clean_json_floats_with_nan_sentinel(pr[slg], 3),
                "s1d_post_win": _clean_json_floats_with_nan_sentinel(po[slg], 3),
                "other_stars_fn_max_pm0p16": oth_fn,
                "order_patches": ord_patches,
            })

    print("[Stage A.6] Scanning 10 Orbital Campaigns (T_DIFF & K_PLANET) & Extracting 9 Keplerian Patches...", flush=True)
    channel_tdiff_candidates_bundle = []
    channel_kplanet_candidates_bundle = []
    orbital_campaign_meta_by_star = {}
    calib_keplerian_patches = []

    for ostar, ke in sorted(kin_catalog["campaigns"].items()):
        margin = int(cfg["scan_margin_bins"])
        role = ke["role"]
        dps_in = [e["dp_id"] for e in ke["exposures"] if e["phase_window"] == "IN_WINDOW"]
        dps_out = [e["dp_id"] for e in ke["exposures"] if e["phase_window"] == "OUT_OF_WINDOW"]
        dv_map = {e["dp_id"]: float(e["planet_orbital_rv_kms"]) for e in ke["exposures"]}

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            c_out = np.asarray(np.nanmedian(np.vstack([exp_records[d]["u_ext"].astype(np.float64) for d in dps_out]), axis=0), dtype=np.float64)
            c_in = np.asarray(np.nanmedian(np.vstack([exp_records[d]["u_ext"].astype(np.float64) for d in dps_in]), axis=0), dtype=np.float64)
        y_td = np.where(np.isfinite(c_in) & np.isfinite(c_out), c_in - c_out, np.nan)

        r_in_list, u_in_list, y_kp_in, f_kp_in = [], [], [], []
        fo = np.isfinite(c_out)
        for dp_in in dps_in:
            re = exp_records[dp_in]
            ue = re["u_ext"].astype(np.float64)
            rj = np.where(np.isfinite(ue) & fo, ue - c_out, np.nan)
            r_in_list.append(rj)
            u_in_list.append(ue)
            w_sh = bgrid * (1.0 + dv_map[dp_in] / C_KMS)
            y_kp_in.append(np.interp(w_sh, bgrid, rj, left=np.nan, right=np.nan))
            f_kp_in.append(np.interp(w_sh, bgrid, ue, left=np.nan, right=np.nan))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            y_kp = np.asarray(np.nanmedian(np.vstack(y_kp_in), axis=0), dtype=np.float64)
            f_kp = np.asarray(np.nanmedian(np.vstack(f_kp_in), axis=0), dtype=np.float64)

        hits_td, srch_td, _ = scan_1d_channel_candidates(bgrid, y_td, "T_DIFF", cfg, flux_norm_for_f1=c_in, enforce_f1_in_g1=True)
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
            tr, oh, pr, po = [rb[k2].astype(np.float64) for k2 in ("s1d_recon", "s1d_oh_rel", "s1d_pre", "s1d_post")]
            g2p = evaluate_gate_g2_spirou_atmosphere(bb, rb["berv_kms"], bgrid[slg], tr[slg], oh[slg], pr[slg], po[slg], h["amp_mid"], cfg)
            oth = compute_other_stars_fn_max_pm0p16(ostar, ra_c, bgrid, star_c_sub)
            channel_tdiff_candidates_bundle.append({
                "channel": "T_DIFF",
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
                "s1d_recon_win": _clean_json_floats_with_nan_sentinel(tr[slg], 5),
                "s1d_oh_rel_win": _clean_json_floats_with_nan_sentinel(oh[slg], 5),
                "s1d_pre_win": _clean_json_floats_with_nan_sentinel(pr[slg], 3),
                "s1d_post_win": _clean_json_floats_with_nan_sentinel(po[slg], 3),
                "other_stars_fn_max_pm0p16": oth,
                "order_patches": build_order_patches_for_wave(bb, rb["segments"], (bgrid[fo] * (1.0 + rb["v_star_kms"] / C_KMS), c_out[fo]), rb["v_star_kms"]) if g2p["g2_pass"] else [],
            })

        hits_kp, srch_kp, _ = scan_1d_channel_candidates(bgrid, y_kp, "K_PLANET", cfg, flux_norm_for_f1=f_kp, enforce_f1_in_g1=True)
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
            tr, oh, pr, po = [rb[k2].astype(np.float64) for k2 in ("s1d_recon", "s1d_oh_rel", "s1d_pre", "s1d_post")]
            g2p = evaluate_gate_g2_spirou_atmosphere(bb, rb["berv_kms"], bgrid[slg], tr[slg], oh[slg], pr[slg], po[slg], h["amp_mid"], cfg)
            oth = compute_other_stars_fn_max_pm0p16(ostar, rest_b, bgrid, star_c_sub)
            channel_kplanet_candidates_bundle.append({
                "channel": "K_PLANET",
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
                "s1d_recon_win": _clean_json_floats_with_nan_sentinel(tr[slg], 5),
                "s1d_oh_rel_win": _clean_json_floats_with_nan_sentinel(oh[slg], 5),
                "s1d_pre_win": _clean_json_floats_with_nan_sentinel(pr[slg], 3),
                "s1d_post_win": _clean_json_floats_with_nan_sentinel(po[slg], 3),
                "other_stars_fn_max_pm0p16": oth,
                "order_patches": build_order_patches_for_wave(bb, rb["segments"], (bgrid[fo] * (1.0 + rb["v_star_kms"] / C_KMS), c_out[fo]), rb["v_star_kms"]) if g2p["g2_pass"] else [],
            })

        orbital_campaign_meta_by_star[ostar] = {
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
            "tdiff_v36_g1_hits": td_g1_cnt,
            "kplanet_searched_bins": srch_kp,
            "kplanet_v36_g1_hits": kp_g1_cnt,
            "band_mads_tdiff": {b["band_id"]: round(measure_band_mad_clean(bgrid, y_td, float(b["center_vac_A"])), 8) for b in BENCHMARK_LASER_BANDS_V36},
            "band_mads_kplanet": {b["band_id"]: round(measure_band_mad_clean(bgrid, y_kp, float(b["center_vac_A"])), 8) for b in BENCHMARK_LASER_BANDS_V36},
        }

        if role == "CONTROL":
            # 5 bands on EVLAC + 4 bands on HD36395 = 9 patches -> 135 paired Keplerian trials
            sel_idx = [1, 2, 4, 6, 9] if ostar == "EVLAC" else [0, 3, 7, 10]
            in_dvs = [dv_map[d] for d in dps_in]
            in_bervs = [exp_records[d]["berv_kms"] for d in dps_in]
            rep_idx = min(range(len(dps_in)), key=lambda j: abs(in_dvs[j]))
            rep_dp = dps_in[rep_idx]
            re_rep = exp_records[rep_dp]
            for ib in sel_idx:
                bnd = BENCHMARK_LASER_BANDS_V36[ib]
                kc = select_clean_rest_wave_spirou(
                    float(bnd["center_vac_A"]), ostar, bgrid, c_out, star_c_sub, in_bervs,
                    re_rep["v_star_kms"], step_c, re_rep["segments"],
                    re_rep["s1d_recon"].astype(np.float64), re_rep["s1d_oh_rel"].astype(np.float64),
                )
                wp0 = float(bgrid[kc])
                slk = slice(kc - margin - 40, kc + margin + 41)
                smads = [exact_mad_1d(y_kp_in[j][slk][np.isfinite(y_kp_in[j][slk])]) for j in range(len(dps_in)) if int(np.isfinite(y_kp_in[j][slk]).sum()) >= 30]
                med_sin = exact_median_1d(np.asarray(smads, dtype=np.float64))
                bary_r0 = float(wp0 * (1.0 + re_rep["v_star_kms"] / C_KMS) * (1.0 + in_dvs[rep_idx] / C_KMS))
                kr0 = max(45, min(len(bgrid) - 46, int(np.argmin(np.abs(bgrid - bary_r0)))))
                slg0 = slice(kr0 - 45, kr0 + 46)
                calib_keplerian_patches.append({
                    "star": ostar,
                    "rep_dp_id": rep_dp,
                    "rep_dv_orb_kms": in_dvs[rep_idx],
                    "rep_berv_kms": re_rep["berv_kms"],
                    "rep_v_star_kms": re_rep["v_star_kms"],
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
                            "r_star_unshifted_win": _clean_json_floats_with_nan_sentinel(r_in_list[j][slk]),
                            "u_star_unshifted_win": _clean_json_floats_with_nan_sentinel(u_in_list[j][slk]),
                            "y_kp_dedoppler_win": _clean_json_floats_with_nan_sentinel(y_kp_in[j][slk]),
                            "f_kp_dedoppler_win": _clean_json_floats_with_nan_sentinel(f_kp_in[j][slk]),
                        }
                        for j, d_i in enumerate(dps_in)
                    ],
                    "s1d_wave_win": _clean_json_floats(bgrid[slg0]),
                    "s1d_recon_win": _clean_json_floats_with_nan_sentinel(re_rep["s1d_recon"].astype(np.float64)[slg0], 5),
                    "s1d_oh_rel_win": _clean_json_floats_with_nan_sentinel(re_rep["s1d_oh_rel"].astype(np.float64)[slg0], 5),
                    "s1d_pre_win": _clean_json_floats_with_nan_sentinel(re_rep["s1d_pre"].astype(np.float64)[slg0], 3),
                    "s1d_post_win": _clean_json_floats_with_nan_sentinel(re_rep["s1d_post"].astype(np.float64)[slg0], 3),
                    "other_stars_fn_max_pm0p16": compute_other_stars_fn_max_pm0p16(ostar, bary_r0 / (1.0 + re_rep["v_star_kms"] / C_KMS), bgrid, star_c_sub),
                    "order_patches": build_order_patches_for_wave(bary_r0, re_rep["segments"], (bgrid[fo] * (1.0 + re_rep["v_star_kms"] / C_KMS), c_out[fo]), re_rep["v_star_kms"]),
                })

    print("[Stage A.7] Scanning Channel P & V4 COMB across 29 stars & extracting T+P+H4RG+G6+COMB calibration patches...", flush=True)
    channel_p_candidates_bundle = []
    channel_p_searched_by_star = {}
    comb_real_summary_by_star = {}
    comb_real_candidates_bundle = []
    calib_transient_patches = []
    calib_persistent_patches = []
    calib_h4rg_2d_patches = []
    calib_g6_patches = []
    calib_comb_patches = []

    for st in sorted(by_star.keys()):
        dps = by_star[st]
        role = exp_records[dps[0]]["row"]["role"]
        margin = int(cfg["scan_margin_bins"])
        cs = star_c_sub[st]
        mm = star_matched_atlas[st]
        yp = np.where(np.isfinite(cs) & np.isfinite(mm), cs - mm, np.nan)
        hits_p, srch_p, _ = scan_1d_channel_candidates(bgrid, yp, "P", cfg, flux_norm_for_f1=cs, enforce_f1_in_g1=True)

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
                    ef = fit_lsf_on_window(bgrid[ke_i - margin : ke_i + margin + 1], np.asarray(re["y_cross"][ke_i - margin : ke_i + margin + 1], dtype=np.float64), float(bgrid[ke_i]), cfg)
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
            tr, oh, pr, po = [rb[k2].astype(np.float64) for k2 in ("s1d_recon", "s1d_oh_rel", "s1d_pre", "s1d_post")]
            g2p = evaluate_gate_g2_spirou_atmosphere(bb, rb["berv_kms"], bgrid[slg], tr[slg], oh[slg], pr[slg], po[slg], h["amp_mid"], cfg)
            oth = compute_other_stars_fn_max_pm0p16(st, ra_c, bgrid, star_c_sub)
            channel_p_candidates_bundle.append({
                "channel": "P",
                "dp_id": best_dp,
                "star": st,
                "role": role,
                "berv_kms": rb["berv_kms"],
                "v_star_kms": rb["v_star_kms"],
                "vshift_kms": rb["vshift_kms"],
                "dv_orb_kms": 0.0,
                "seed_wave_a": float(bgrid[k]),
                "wave_win": _clean_json_floats(bgrid[sl]),
                "y_primary_win": _clean_json_floats_with_nan_sentinel(yp[sl]),
                "c_sub_win": _clean_json_floats_with_nan_sentinel(cs[sl]),
                "s1d_wave_win": _clean_json_floats(bgrid[slg]),
                "s1d_recon_win": _clean_json_floats_with_nan_sentinel(tr[slg], 5),
                "s1d_oh_rel_win": _clean_json_floats_with_nan_sentinel(oh[slg], 5),
                "s1d_pre_win": _clean_json_floats_with_nan_sentinel(pr[slg], 3),
                "s1d_post_win": _clean_json_floats_with_nan_sentinel(po[slg], 3),
                "other_stars_fn_max_pm0p16": oth,
                "order_patches": build_order_patches_for_wave(bb, rb["segments"], (bgrid[fm_m] * (1.0 + rb["v_star_kms"] / C_KMS), mm[fm_m]), rb["v_star_kms"]) if g2p["g2_pass"] else [],
            })

        channel_p_searched_by_star[st] = {"role": role, "searched_bins": srch_p, "v36_persistent_g1_hits": p_g1_cnt, **star_atlas_meta[st]}

        # Channel 5: V4 COMB Real Scan on full 302,601-bin stellar-rest stack & topocentric anti-comb veto
        sigma_rest = _rolling_local_sigma(bgrid, yp)
        rc_r = star_recon_rest[st]
        oh_r = star_oh_rest[st]
        sky_mask_r = (oh_r > float(cfg["gate_g2_max_oh_rel_pk3"])) | (rc_r < float(cfg["comb_tooth_recon_min"]))
        bervs_s = [float(exp_records[d]["berv_kms"]) for d in dps]
        v_star_s = float(exp_records[dps[0]]["v_star_kms"])
        comb_cands, comb_configs = scan_frequency_comb_v4(
            bgrid, yp, sigma_rest, cs, rc_r, sky_mask_r,
            star_y_topo[st], star_sigma_topo[st], exact_median_1d(np.asarray(bervs_s)), v_star_s, cfg,
        )
        # Also evaluate max unconstrained comb S/N in the CLEAN 4 bands for continuous telemetry
        comb_real_summary_by_star[st] = {
            "role": role,
            "n_epochs": len(dps),
            "berv_span_kms": round(float(max(bervs_s) - min(bervs_s)), 3),
            "searched_comb_configs": comb_configs,
            "n_comb_hits": len(comb_cands),
            "median_sigma_rest_yjh_k": round(exact_median_1d(sigma_rest[np.isfinite(sigma_rest)]), 6),
            "max_comb_score": round(max((c["s_comb"] for c in comb_cands), default=0.0), 4),
        }
        for cc in comb_cands:
            w_lo = min(cc["wave0_vac_a"], cc["wave_end_vac_a"]) - 80.0
            w_hi = max(cc["wave0_vac_a"], cc["wave_end_vac_a"]) + 80.0
            i0 = max(0, int(np.searchsorted(bgrid, w_lo, side="left")))
            i1 = min(len(bgrid), int(np.searchsorted(bgrid, w_hi, side="right")))
            comb_real_candidates_bundle.append({
                "star": st,
                "role": role,
                "median_berv_kms": exact_median_1d(np.asarray(bervs_s)),
                "v_star_kms": v_star_s,
                "band": cc["band"],
                "dnu_ghz": cc["dnu_ghz"],
                "nu0_ghz_stage_a": cc["nu0_ghz"],
                "s_comb_stage_a": cc["s_comb"],
                "s_comb_topo_stage_a": cc["s_comb_topo"],
                "wave_win": _clean_json_floats(bgrid[i0:i1], 4),
                "y_rest_win": _clean_json_floats_with_nan_sentinel(yp[i0:i1], 5),
                "sigma_rest_win": _clean_json_floats_with_nan_sentinel(sigma_rest[i0:i1], 5),
                "fn_win": _clean_json_floats_with_nan_sentinel(cs[i0:i1], 5),
                "recon_win": _clean_json_floats_with_nan_sentinel(rc_r[i0:i1], 4),
                "sky_mask_win": [bool(x) for x in sky_mask_r[i0:i1]],
                "y_topo_win": _clean_json_floats_with_nan_sentinel(star_y_topo[st][i0:i1], 5),
                "sigma_topo_win": _clean_json_floats_with_nan_sentinel(star_sigma_topo[st][i0:i1], 5),
            })

        if role == "CONTROL":
            eval_dps = [dps[0], dps[-1]]
            re0 = exp_records[eval_dps[0]]
            other_stars_d = [
                (s2, float(exp_records[by_star[s2][0]]["vshift_kms"]))
                for s2 in sorted(by_star.keys())
                if s2 != st and abs(float(exp_records[by_star[s2][0]]["vshift_kms"]) - re0["vshift_kms"]) >= 8.5
            ]

            for d_i in eval_dps:
                re = exp_records[d_i]
                te = re["t_ext"].astype(np.float64)
                ft = np.isfinite(te)
                tr, oh, pr, po = [re[k2].astype(np.float64) for k2 in ("s1d_recon", "s1d_oh_rel", "s1d_pre", "s1d_post")]
                for bnd in CALIB_9_BANDS:
                    kc_r = select_clean_rest_wave_spirou(
                        float(bnd["center_vac_A"]), st, bgrid, cs, star_c_sub,
                        [re["berv_kms"]], re["v_star_kms"], step_c, re["segments"], tr, oh,
                        extra_bary_checks=[(re["f_norm"].astype(np.float64), tr)],
                    )
                    rc_w = float(bgrid[kc_r])
                    bc_t = rc_w * (1.0 + re["v_star_kms"] / C_KMS)
                    k0 = int(np.argmin(np.abs(bgrid - bc_t)))
                    sl = slice(k0 - margin - 5, k0 + margin + 6)
                    bc = float(bgrid[k0])
                    rest_bc = bc / (1.0 + re["v_star_kms"] / C_KMS)
                    kc_g = max(45, min(len(bgrid) - 46, k0))
                    slg = slice(kc_g - 45, kc_g + 46)
                    ord_p = build_order_patches_for_wave(bc, re["segments"], (bgrid[ft], te[ft]), re["v_star_kms"])
                    oth_fn = compute_other_stars_fn_max_pm0p16(st, rest_bc, bgrid, star_c_sub)

                    calib_h4rg_2d_patches.append({
                        "star": st, "dp_id": d_i, "band_id": bnd["band_id"],
                        "target_bary_a": bc, "stellar_rest_wave_a": rest_bc,
                        "other_stars_fn_max_pm0p16": oth_fn, "order_patches": ord_p,
                    })
                    calib_transient_patches.append({
                        "star": st, "dp_id": d_i, "band_id": bnd["band_id"],
                        "target_bary_a": bc, "berv_kms": re["berv_kms"], "v_star_kms": re["v_star_kms"],
                        "wave_win": _clean_json_floats(bgrid[sl]),
                        "y_self_win": _clean_json_floats_with_nan_sentinel(re["y_self"].astype(np.float64)[sl]),
                        "y_cross_win": _clean_json_floats_with_nan_sentinel(re["y_cross"].astype(np.float64)[sl]),
                        "f_norm_win": _clean_json_floats_with_nan_sentinel(re["f_norm"].astype(np.float64)[sl]),
                        "s1d_wave_win": _clean_json_floats(bgrid[slg]),
                        "s1d_recon_win": _clean_json_floats_with_nan_sentinel(tr[slg], 5),
                        "s1d_oh_rel_win": _clean_json_floats_with_nan_sentinel(oh[slg], 5),
                        "s1d_pre_win": _clean_json_floats_with_nan_sentinel(pr[slg], 3),
                        "s1d_post_win": _clean_json_floats_with_nan_sentinel(po[slg], 3),
                        "other_stars_fn_max_pm0p16": oth_fn, "order_patches": ord_p,
                    })

            # Suite E G6 (20 patches = 4 controls x 5 wide YJHK bands) + intra-star opposite-BERV epoch
            dp_opp = max(dps, key=lambda d2: abs(float(exp_records[d2]["berv_kms"]) - re0["berv_kms"]))
            tr0, oh0 = re0["s1d_recon"].astype(np.float64), re0["s1d_oh_rel"].astype(np.float64)
            for bnd in CALIB_5_G6_BANDS:
                kc_r = select_clean_rest_wave_spirou(
                    float(bnd["center_vac_A"]), st, bgrid, cs, star_c_sub,
                    [re0["berv_kms"], exp_records[dp_opp]["berv_kms"]], re0["v_star_kms"], step_c,
                    re0["segments"], tr0, oh0, extra_bary_checks=[(re0["f_norm"].astype(np.float64), tr0)],
                )
                bc = float(bgrid[kc_r]) * (1.0 + re0["v_star_kms"] / C_KMS)
                topo_c = bc / (1.0 + re0["berv_kms"] / C_KMS)
                prim_ord, prim_px = find_primary_order_px_for_bary(bc, re0["segments"])
                loc_dense = [a for a in dense_atlas if abs(a["topo_vac_a"] - topo_c) <= 1.5 or (prim_ord is not None and a["order"] == prim_ord and prim_px is not None and abs(float(a["px"]) - prim_px) <= 8.0)]
                loc_sparse = [a for a in sparse_atlas if abs(a["topo_vac_a"] - topo_c) <= 1.5 or (prim_ord is not None and a["order"] == prim_ord and prim_px is not None and abs(float(a["px"]) - prim_px) <= 8.0)]
                calib_g6_patches.append({
                    "star": st,
                    "dp_id": eval_dps[0],
                    "opp_dp_id": dp_opp,
                    "opp_berv_kms": round(float(exp_records[dp_opp]["berv_kms"]), 4),
                    "band_id": bnd["band_id"],
                    "cand_topo_vac_a": round(topo_c, 6),
                    "cand_order": prim_ord,
                    "cand_px": prim_px,
                    "target_berv_kms": round(float(re0["berv_kms"]), 4),
                    "target_vshift_kms": round(float(re0["vshift_kms"]), 4),
                    "local_dense_atlas": loc_dense,
                    "local_sparse_atlas": loc_sparse,
                    "synthetic_other_stars": other_stars_d[:3],
                })

            # Channel P 5-epoch control patches (4 controls x 9 bands = 36 patches -> 540 trials)
            dps_p = [dps[int(round(i * (len(dps) - 1) / 4))] for i in range(5)]
            rep_dp_p = max(dps, key=lambda d: float(exp_records[d]["snr_obs"]))
            re_p0 = exp_records[rep_dp_p]
            te_p0 = re_p0["t_ext"].astype(np.float64)
            fte_p0 = np.isfinite(te_p0)
            trp0, ohp0, prp0, pop0 = [re_p0[k2].astype(np.float64) for k2 in ("s1d_recon", "s1d_oh_rel", "s1d_pre", "s1d_post")]
            ep_bervs = [exp_records[d]["berv_kms"] for d in dps_p]
            for bnd in CALIB_9_BANDS:
                kc = select_clean_rest_wave_spirou(
                    float(bnd["center_vac_A"]), st, bgrid, cs, star_c_sub,
                    ep_bervs, re_p0["v_star_kms"], step_c, re_p0["segments"], trp0, ohp0,
                    extra_bary_checks=[(re_p0["f_norm"].astype(np.float64), trp0)],
                )
                rc = float(bgrid[kc])
                sl = slice(kc - margin - 5, kc + margin + 6)
                ep_wins, sc_mads, n_cov_p = [], [], 0
                for d_i in dps_p:
                    r_i = exp_records[d_i]
                    ba_i = rc * (1.0 + r_i["v_star_kms"] / C_KMS)
                    ke_i = int(np.argmin(np.abs(bgrid - ba_i)))
                    sle = slice(ke_i - margin - 5, ke_i + margin + 6)
                    yc_w = r_i["y_cross"].astype(np.float64)[sle]
                    cov = bool(np.all(np.isfinite(r_i["y_cross"][ke_i - 4 : ke_i + 5])) and int(np.isfinite(yc_w).sum()) >= 100)
                    if cov:
                        n_cov_p += 1
                        sc_mads.append(exact_mad_1d(yc_w[np.isfinite(yc_w)]))
                    ep_wins.append({
                        "dp_id": d_i, "covered": cov, "v_star_kms": r_i["v_star_kms"],
                        "wave_win": _clean_json_floats(bgrid[sle]), "y_cross_win": _clean_json_floats_with_nan_sentinel(yc_w),
                    })
                b0 = rc * (1.0 + re_p0["v_star_kms"] / C_KMS)
                kc0 = max(45, min(len(bgrid) - 46, int(np.argmin(np.abs(bgrid - b0)))))
                slg0 = slice(kc0 - 45, kc0 + 46)
                emp_mad = max(exact_mad_1d(yp[sl][np.isfinite(yp[sl])]), 0.75 * exact_median_1d(np.asarray(sc_mads, dtype=np.float64)))
                calib_persistent_patches.append({
                    "star": st, "rep_dp_id": rep_dp_p, "band_id": bnd["band_id"],
                    "target_rest_a": rc, "berv_kms": re_p0["berv_kms"], "v_star_kms": re_p0["v_star_kms"],
                    "n_covering_epochs": n_cov_p,
                    "min_req_epochs": max(min(int(cfg["channel_p_min_epochs_above_3sigma"]), n_cov_p), int(math.ceil(cfg["channel_p_min_epoch_fraction"] * n_cov_p))),
                    "coadd_wave_win": _clean_json_floats(bgrid[sl]),
                    "y_p_win": _clean_json_floats_with_nan_sentinel(yp[sl]),
                    "c_sub_win": _clean_json_floats_with_nan_sentinel(cs[sl]),
                    "epoch_windows": ep_wins,
                    "s1d_wave_win": _clean_json_floats(bgrid[slg0]),
                    "s1d_recon_win": _clean_json_floats_with_nan_sentinel(trp0[slg0], 5),
                    "s1d_oh_rel_win": _clean_json_floats_with_nan_sentinel(ohp0[slg0], 5),
                    "s1d_pre_win": _clean_json_floats_with_nan_sentinel(prp0[slg0], 3),
                    "s1d_post_win": _clean_json_floats_with_nan_sentinel(pop0[slg0], 3),
                    "other_stars_fn_max_pm0p16": compute_other_stars_fn_max_pm0p16(st, rc, bgrid, star_c_sub),
                    "order_patches": build_order_patches_for_wave(b0, re_p0["segments"], (bgrid[fte_p0], te_p0[fte_p0]), re_p0["v_star_kms"]),
                    "coadd_empirical_mad": emp_mad,
                })

            # V4 COMB Calibration Patches: 4 CONTROL stars x 4 bands (Y, J, H, K_core) = 16 wide patches (~650 GHz each)
            for bname in cfg["comb_search_bands"]:
                win_d = [w for w in CLEAN_SPIROU_WINDOWS_VAC_A if w["band"] == bname][0]
                lo_a, hi_a = float(win_d["lo_a"]), float(win_d["hi_a"])
                # Pick cleanest ~680 GHz sub-window near band center where recon>=0.85 & !sky_mask is abundant
                mid_nu = 0.5 * (C_ANGSTROM_GHZ / hi_a + C_ANGSTROM_GHZ / lo_a)
                best_sub = None
                best_frac = -1.0
                for nu_off in (-1500.0, -700.0, 0.0, 700.0, 1500.0):
                    nu_lo_s = mid_nu + nu_off - 320.0
                    nu_hi_s = mid_nu + nu_off + 360.0
                    w_sub_lo = C_ANGSTROM_GHZ / nu_hi_s
                    w_sub_hi = C_ANGSTROM_GHZ / nu_lo_s
                    if w_sub_lo < lo_a + 15.0 or w_sub_hi > hi_a - 15.0:
                        continue
                    i0 = int(np.searchsorted(bgrid, w_sub_lo, side="left"))
                    i1 = int(np.searchsorted(bgrid, w_sub_hi, side="right"))
                    ok_frac = float(np.mean(np.isfinite(yp[i0:i1]) & np.isfinite(sigma_rest[i0:i1]) & (rc_r[i0:i1] >= 0.85) & (~sky_mask_r[i0:i1])))
                    if ok_frac > best_frac:
                        best_frac, best_sub = ok_frac, (i0, i1, nu_lo_s, nu_hi_s)
                assert best_sub is not None
                i0, i1, nu_lo_s, nu_hi_s = best_sub
                calib_comb_patches.append({
                    "star": st,
                    "band": bname,
                    "berv_span_kms": round(float(max(bervs_s) - min(bervs_s)), 3),
                    "median_berv_kms": round(exact_median_1d(np.asarray(bervs_s)), 4),
                    "v_star_kms": round(v_star_s, 4),
                    "nu_lo_ghz": round(nu_lo_s, 3),
                    "nu_hi_ghz": round(nu_hi_s, 3),
                    "wave_win": _clean_json_floats(bgrid[i0:i1], 4),
                    "y_rest_win": _clean_json_floats_with_nan_sentinel(yp[i0:i1], 5),
                    "sigma_rest_win": _clean_json_floats_with_nan_sentinel(sigma_rest[i0:i1], 5),
                    "fn_win": _clean_json_floats_with_nan_sentinel(cs[i0:i1], 5),
                    "recon_win": _clean_json_floats_with_nan_sentinel(rc_r[i0:i1], 4),
                    "sky_mask_win": [bool(x) for x in sky_mask_r[i0:i1]],
                    "y_topo_win": _clean_json_floats_with_nan_sentinel(star_y_topo[st][i0:i1], 5),
                    "sigma_topo_win": _clean_json_floats_with_nan_sentinel(star_sigma_topo[st][i0:i1], 5),
                })

    exp_records.clear()
    gc.collect()
    print("[Stage A] Bounded D085 SPIRou bundle assembled cleanly in memory.", flush=True)
    return {
        "schema": "SETI_D085_BOUNDED_REPRODUCIBLE_BUNDLE_V1",
        "provenance_rows": provenance_rows,
        "rv_anchor_bundle": rv_anchor_bundle,
        "band_noise_rows": band_noise_rows,
        "searched_summary_by_dp": searched_summary_by_dp,
        "channel_p_searched_by_star": channel_p_searched_by_star,
        "orbital_campaign_meta_by_star": orbital_campaign_meta_by_star,
        "comb_real_summary_by_star": comb_real_summary_by_star,
        "comb_real_candidates_bundle": comb_real_candidates_bundle,
        "dense_atlas": dense_atlas,
        "sparse_atlas": sparse_atlas,
        "channel_t_candidates_bundle": channel_t_candidates_bundle,
        "channel_p_candidates_bundle": channel_p_candidates_bundle,
        "channel_tdiff_candidates_bundle": channel_tdiff_candidates_bundle,
        "channel_kplanet_candidates_bundle": channel_kplanet_candidates_bundle,
        "calib_transient_patches": calib_transient_patches,
        "calib_persistent_patches": calib_persistent_patches,
        "calib_keplerian_patches": calib_keplerian_patches,
        "calib_h4rg_2d_patches": calib_h4rg_2d_patches,
        "calib_g6_patches": calib_g6_patches,
        "calib_comb_patches": calib_comb_patches,
    }


def _unpack_order_patches(patches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for p in patches:
        np_d = dict(p)
        np_d["flux"] = _arr_from_nullable(p["flux"])
        if p.get("flux_a") is not None:
            np_d["flux_a"] = _arr_from_nullable(p["flux_a"])
        if p.get("flux_b") is not None:
            np_d["flux_b"] = _arr_from_nullable(p["flux_b"])
        out.append(np_d)
    return out


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
    cfg = get_inst_config("SPIROU")
    prov_by_dp = {r["dp_id"]: r for r in bundle["provenance_rows"]}

    by_star_rows: dict[str, list[dict[str, str]]] = {}
    for r in cohort_rows:
        by_star_rows.setdefault(r["canonical_target"], []).append(r)

    # 1. Recompute 2,124 NIST RV anchors + 29 star RV summaries
    rv_anchor_rows = []
    exp_rv_map: dict[str, tuple[float, int]] = {}
    for r in cohort_rows:
        dp = r["dp_id"]
        item = bundle["rv_anchor_bundle"][dp]
        prior_rv = float(item["prior_rv_kms"])
        exp_clean = []
        for anc in LOCKED_SPIROU_RV_ANCHORS:
            aid, lab = anc["anchor_id"], float(anc["lab_vac_A"])
            win = item["windows"][aid]
            fit = fit_single_rv_anchor(np.asarray(win["wave"], dtype=np.float64), _arr_from_nullable(win["flux"]), lab, prior_rv, cfg)
            if fit["status"] == "CLEAN_ABSORPTION":
                exp_clean.append(fit["best_rv_kms"])
            rv_anchor_rows.append({
                "instrument": "SPIROU",
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
        rvs = np.array([exp_rv_map[x["dp_id"]][0] for x in srows], dtype=np.float64)
        clean_cnts = [exp_rv_map[x["dp_id"]][1] for x in srows]
        pmeta = bundle["channel_p_searched_by_star"][st]
        star_rv_summary.append({
            "instrument": "SPIROU",
            "star": st,
            "common_name": srows[0]["common_name"],
            "role": srows[0]["role"],
            "subrole": srows[0]["subrole"],
            "panchromatic_bridge": srows[0]["panchromatic_bridge"] == "True",
            "radio_mm_id": srows[0]["radio_mm_id"],
            "dist_pc": float(srows[0]["dist_pc"]),
            "within_10pc": srows[0]["within_10pc"] == "True",
            "teff_k": float(srows[0]["teff_k"]),
            "mh_dex": float(srows[0]["mh_dex"]),
            "phot_g_mag": float(srows[0]["phot_g_mag"]),
            "j_mag": float(srows[0]["j_mag"]),
            "h_mag": float(srows[0]["h_mag"]),
            "ks_mag": float(srows[0]["ks_mag"]),
            "n_exoplanets": int(srows[0]["n_exoplanets"]),
            "n_epochs": len(srows),
            "median_clean_anchors": int(exact_median_1d(np.asarray(clean_cnts, dtype=np.float64))),
            "empirical_mean_bary_rv_kms": float(np.mean(rvs)),
            "epoch_rms_kms": float(np.std(rvs, ddof=1)) if len(rvs) > 1 else 0.0,
            "prior_rv_kms": float(srows[0]["prior_rv_kms"]),
            "empirical_minus_prior_kms": float(np.mean(rvs)) - float(srows[0]["prior_rv_kms"]),
            "knn_neighbors": ";".join(pmeta["knn_neighbors"]),
            "optical_depth_gamma": pmeta["median_optical_depth_gamma"],
            "post_match_mad": pmeta["post_match_mad"],
        })

    # 2. Prospective Control Calibration (2,592 Trials Total across Suites A-F)
    sig_v, margin, step_c = float(cfg["sigma_v_kms"]), int(cfg["scan_margin_bins"]), float(cfg["coadd_step_angstrom"])
    inj_rows = []
    for p in bundle["calib_transient_patches"]:
        wb = np.asarray(p["wave_win"], dtype=np.float64)
        ys = _arr_from_nullable(p["y_self_win"])
        yc = _arr_from_nullable(p["y_cross_win"])
        fn = _arr_from_nullable(p["f_norm_win"])
        wg2 = np.asarray(p["s1d_wave_win"], dtype=np.float64)
        rc2, oh2 = _arr_from_nullable(p["s1d_recon_win"]), _arr_from_nullable(p["s1d_oh_rel_win"])
        pr2, po2 = _arr_from_nullable(p["s1d_pre_win"]), _arr_from_nullable(p["s1d_post_win"])
        pr2_c = exact_median_1d(pr2[np.isfinite(pr2) & (pr2 > 0)]) if np.any(np.isfinite(pr2) & (pr2 > 0)) else 1.0
        po2_c = exact_median_1d(po2[np.isfinite(po2) & (po2 > 0)]) if np.any(np.isfinite(po2) & (po2 > 0)) else 1.0
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
            profg = np.exp(-0.5 * ((C_KMS * (wg2 - inj_b) / inj_b) / sig_v) ** 2)
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
                po2i = po2 + amp * po2_c * profg
                pr2i = pr2 + amp * pr2_c * profg * np.where(np.isfinite(rc2), rc2, 1.0)
                g2 = evaluate_gate_g2_spirou_atmosphere(fb, float(p["berv_kms"]), wg2, rc2, oh2, pr2i, po2i, ft.get("amp_mid", amp), cfg)
                i_ops = []
                for op in base_ops:
                    wo, fo_a = np.asarray(op["wave"]), op["flux"]
                    c80 = exact_quantile_1d(fo_a[np.isfinite(fo_a) & (fo_a > 0)], 0.80) if np.sum(fo_a > 0) > 10 else 1.0
                    g_n = np.exp(-0.5 * ((wo - inj_b) / snat) ** 2)
                    nop = {**op, "target_wave_a": float(fb), "flux": fo_a + amp * c80 * g_n}
                    if op.get("flux_a") is not None:
                        fa_a = op["flux_a"]
                        c80a = exact_quantile_1d(fa_a[np.isfinite(fa_a) & (fa_a > 0)], 0.80) if np.sum(fa_a > 0) > 10 else 1.0
                        nop["flux_a"] = fa_a + amp * c80a * g_n
                    if op.get("flux_b") is not None:
                        fb_a = op["flux_b"]
                        c80b = exact_quantile_1d(fb_a[np.isfinite(fb_a) & (fb_a > 0)], 0.80) if np.sum(fb_a > 0) > 10 else 1.0
                        nop["flux_b"] = fb_a + amp * c80b * g_n
                    i_ops.append(nop)
                g345 = evaluate_gates_g3_g4_g5_spirou(i_ops, fb / (1.0 + float(p["v_star_kms"]) / C_KMS), n_ridge, cfg)
                rec_ok = bool(g1_ok and g2["g2_pass"] and g345["g3_pass"] and g345["g4_pass"])
                inj_rows.append({"instrument": "SPIROU", "mode": "CHANNEL_T_TRANSIENT_1EPOCH", "star": p["star"], "dp_id": p["dp_id"], "band_id": p["band_id"], "injected_wave_a": inj_b, "phase_bins": ph, "sigma_mult": mult, "injected_amp_rel": amp, "fitted_snr_mid": ft.get("snr_mid", 0.0), "fitted_cosine": ft.get("cosine", 0.0), "fitted_fwhm_ratio": ft.get("fwhm_ratio"), "g1_pass": g1_ok, "g2_pass": g2["g2_pass"], "g3_pass": g345["g3_pass"], "g4_pass": g345["g4_pass"], "recovered": rec_ok})

    for p in bundle["calib_persistent_patches"]:
        wb = np.asarray(p["coadd_wave_win"], dtype=np.float64)
        ypb, csb = _arr_from_nullable(p["y_p_win"]), _arr_from_nullable(p["c_sub_win"])
        wg2 = np.asarray(p["s1d_wave_win"], dtype=np.float64)
        rc2, oh2 = _arr_from_nullable(p["s1d_recon_win"]), _arr_from_nullable(p["s1d_oh_rel_win"])
        pr2, po2 = _arr_from_nullable(p["s1d_pre_win"]), _arr_from_nullable(p["s1d_post_win"])
        pr2_c = exact_median_1d(pr2[np.isfinite(pr2) & (pr2 > 0)]) if np.any(np.isfinite(pr2) & (pr2 > 0)) else 1.0
        po2_c = exact_median_1d(po2[np.isfinite(po2) & (po2 > 0)]) if np.any(np.isfinite(po2) & (po2 > 0)) else 1.0
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
            profg = np.exp(-0.5 * ((C_KMS * (wg2 - inj_b0) / inj_b0) / sig_v) ** 2)
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
                po2i = po2 + amp * po2_c * profg
                pr2i = pr2 + amp * pr2_c * profg * np.where(np.isfinite(rc2), rc2, 1.0)
                g2 = evaluate_gate_g2_spirou_atmosphere(b0, float(p["berv_kms"]), wg2, rc2, oh2, pr2i, po2i, fp.get("amp_mid", amp), cfg)
                i_ops = []
                for op in base_ops:
                    wo, fo_a = np.asarray(op["wave"]), op["flux"]
                    c80 = exact_quantile_1d(fo_a[np.isfinite(fo_a) & (fo_a > 0)], 0.80) if np.sum(fo_a > 0) > 10 else 1.0
                    g_n = np.exp(-0.5 * ((wo - inj_b0) / snat) ** 2)
                    nop = {**op, "target_wave_a": float(b0), "flux": fo_a + amp * c80 * g_n}
                    if op.get("flux_a") is not None:
                        fa_a = op["flux_a"]
                        c80a = exact_quantile_1d(fa_a[np.isfinite(fa_a) & (fa_a > 0)], 0.80) if np.sum(fa_a > 0) > 10 else 1.0
                        nop["flux_a"] = fa_a + amp * c80a * g_n
                    if op.get("flux_b") is not None:
                        fb_a = op["flux_b"]
                        c80b = exact_quantile_1d(fb_a[np.isfinite(fb_a) & (fb_a > 0)], 0.80) if np.sum(fb_a > 0) > 10 else 1.0
                        nop["flux_b"] = fb_a + amp * c80b * g_n
                    i_ops.append(nop)
                g345 = evaluate_gates_g3_g4_g5_spirou(i_ops, fr, n_ridge, cfg)
                rec_ok = bool(g1_ok and g2["g2_pass"] and g345["g3_pass"] and g345["g4_pass"])
                inj_rows.append({"instrument": "SPIROU", "mode": "CHANNEL_P_PERSISTENT_5EPOCH", "star": p["star"], "dp_id": p["rep_dp_id"], "band_id": p["band_id"], "injected_wave_a": inj_r, "phase_bins": ph, "sigma_mult": mult, "injected_amp_rel": amp, "fitted_snr_mid": fp.get("snr_mid", 0.0), "fitted_cosine": fp.get("cosine", 0.0), "fitted_fwhm_ratio": fp.get("fwhm_ratio"), "g1_pass": g1_ok, "g2_pass": g2["g2_pass"], "g3_pass": g345["g3_pass"], "g4_pass": g345["g4_pass"], "recovered": rec_ok})

    kep_rows = []
    for kp in bundle["calib_keplerian_patches"]:
        wpl = np.asarray(kp["planet_wave_win"], dtype=np.float64)
        smad = float(kp["single_in_exp_mad"])
        kc = len(wpl) // 2
        w0 = float(wpl[kc])
        tracks = kp["in_exp_tracks"]
        req_td = max(2, int(math.ceil(cfg["channel_tdiff_min_in_exp_fraction"] * len(tracks))))
        req_kp = max(2, int(math.ceil(cfg["channel_kplanet_min_in_exp_fraction"] * len(tracks))))
        wg2 = np.asarray(kp["s1d_wave_win"], dtype=np.float64)
        rc2, oh2 = _arr_from_nullable(kp["s1d_recon_win"]), _arr_from_nullable(kp["s1d_oh_rel_win"])
        pr2, po2 = _arr_from_nullable(kp["s1d_pre_win"]), _arr_from_nullable(kp["s1d_post_win"])
        pr2_c = exact_median_1d(pr2[np.isfinite(pr2) & (pr2 > 0)]) if np.any(np.isfinite(pr2) & (pr2 > 0)) else 1.0
        po2_c = exact_median_1d(po2[np.isfinite(po2) & (po2 > 0)]) if np.any(np.isfinite(po2) & (po2 > 0)) else 1.0
        n_ridge = sum(1 for v in kp["other_stars_fn_max_pm0p16"].values() if float(v) >= cfg["gate_g3_cross_star_ridge_fn_min"])
        base_ops = _unpack_order_patches(kp["order_patches"])
        for ph in KEPLERIAN_INJECTION_PHASES:
            inj_p = w0 + ph * step_c
            ptol = 0.75 * (inj_p / cfg["resolving_power"])
            profd = np.exp(-0.5 * ((C_KMS * (wpl - inj_p) / inj_p) / sig_v) ** 2)
            unsh_profs = [np.exp(-0.5 * ((C_KMS * (wpl - inj_p * (1.0 + float(trk["dv_orb_kms"]) / C_KMS)) / (inj_p * (1.0 + float(trk["dv_orb_kms"]) / C_KMS))) / sig_v) ** 2) for trk in tracks]
            ib_rep = inj_p * (1.0 + float(kp["rep_v_star_kms"]) / C_KMS) * (1.0 + float(kp["rep_dv_orb_kms"]) / C_KMS)
            profg = np.exp(-0.5 * ((C_KMS * (wg2 - ib_rep) / ib_rep) / sig_v) ** 2)
            snat = ib_rep / (cfg["resolving_power"] * FWHM_FACTOR)
            for me in KEPLERIAN_EXP_SIGMAS:
                amp = me * smad
                runl = [_arr_from_nullable(t["r_star_unshifted_win"]) + amp * unsh_profs[j] for j, t in enumerate(tracks)]
                uunl = [_arr_from_nullable(t["u_star_unshifted_win"]) + amp * unsh_profs[j] for j, t in enumerate(tracks)]
                r_a, u_a = np.vstack(runl), np.vstack(uunl)
                ytd = np.array([exact_median_1d(r_a[:, c][np.isfinite(r_a[:, c])]) for c in range(r_a.shape[1])], dtype=np.float64)
                utd = np.array([exact_median_1d(u_a[:, c][np.isfinite(u_a[:, c])]) for c in range(u_a.shape[1])], dtype=np.float64)
                ktpk = max(margin, min(len(wpl) - margin - 1, (kc - 35) + int(np.argmax(np.where(np.isfinite(ytd[kc - 35 : kc + 36]), ytd[kc - 35 : kc + 36], -1e9)))))
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
                po2i = po2 + amp * po2_c * profg
                pr2i = pr2 + amp * pr2_c * profg * np.where(np.isfinite(rc2), rc2, 1.0)
                g2kp = evaluate_gate_g2_spirou_atmosphere(brep, float(kp["rep_berv_kms"]), wg2, rc2, oh2, pr2i, po2i, fkp.get("amp_mid", amp), cfg)
                i_ops = []
                for op in base_ops:
                    wo, fo_a = np.asarray(op["wave"]), op["flux"]
                    c80 = exact_quantile_1d(fo_a[np.isfinite(fo_a) & (fo_a > 0)], 0.80) if np.sum(fo_a > 0) > 10 else 1.0
                    g_n = np.exp(-0.5 * ((wo - ib_rep) / snat) ** 2)
                    nop = {**op, "target_wave_a": float(brep), "flux": fo_a + amp * c80 * g_n}
                    if op.get("flux_a") is not None:
                        fa_a = op["flux_a"]
                        c80a = exact_quantile_1d(fa_a[np.isfinite(fa_a) & (fa_a > 0)], 0.80) if np.sum(fa_a > 0) > 10 else 1.0
                        nop["flux_a"] = fa_a + amp * c80a * g_n
                    if op.get("flux_b") is not None:
                        fb_a = op["flux_b"]
                        c80b = exact_quantile_1d(fb_a[np.isfinite(fb_a) & (fb_a > 0)], 0.80) if np.sum(fb_a > 0) > 10 else 1.0
                        nop["flux_b"] = fb_a + amp * c80b * g_n
                    i_ops.append(nop)
                g345kp = evaluate_gates_g3_g4_g5_spirou(i_ops, rrep, n_ridge, cfg)
                kprec = bool(kpg1 and g2kp["g2_pass"] and g345kp["g3_pass"] and g345kp["g4_pass"])
                kep_rows.append({"instrument": "SPIROU", "star": kp["star"], "rep_dp_id": kp["rep_dp_id"], "band_id": kp["band_id"], "dv_span_kms": kp["dv_span_kms"], "injected_planet_wave_a": inj_p, "phase_bins": ph, "exp_sigma_mult": me, "injected_amp_rel": amp, "tdiff_uncomp_snr_mid": ftd.get("snr_mid", 0.0), "tdiff_uncomp_recovered": td_rec, "kplanet_dedop_snr_mid": fkp.get("snr_mid", 0.0), "kplanet_dedop_cosine": fkp.get("cosine", 0.0), "kplanet_dedop_fwhm_ratio": fkp.get("fwhm_ratio"), "kplanet_g1_pass": kpg1, "kplanet_g2_pass": g2kp["g2_pass"], "kplanet_g3_pass": g345kp["g3_pass"], "kplanet_g4_pass": g345kp["g4_pass"], "kplanet_dedop_recovered": kprec})

    # Suite D: 216 H4RG Dual-Fiber G4 + 2D G5 Physics Trials (72 Patches x 3 Classes)
    h4rg_rows = []
    for rp in bundle["calib_h4rg_2d_patches"]:
        base_ops = _unpack_order_patches(rp["order_patches"])
        tgt, rw = float(rp["target_bary_a"]), float(rp["stellar_rest_wave_a"])
        n_ridge = sum(1 for v in rp["other_stars_fn_max_pm0p16"].values() if float(v) >= cfg["gate_g3_cross_star_ridge_fn_min"])
        sig_a = tgt / (cfg["resolving_power"] * FWHM_FACTOR)
        ol, oi, opl = [], [], []
        for op in base_ops:
            wo, fo_a = np.asarray(op["wave"], dtype=np.float64), op["flux"]
            c80 = exact_quantile_1d(fo_a[np.isfinite(fo_a) & (fo_a > 0)], 0.80) if np.sum(fo_a > 0) >= 10 else 1.0
            kt = int(np.argmin(np.abs(wo - tgt)))
            g_l = np.exp(-0.5 * ((wo - tgt) / sig_a) ** 2)
            g_p = np.exp(-0.5 * ((wo - tgt) / (3.2 * sig_a)) ** 2)
            pc = np.zeros_like(fo_a)
            pc[kt] = 0.70 * c80
            if kt > 0:
                pc[kt - 1] = 0.02 * 0.70 * c80
            if kt + 1 < len(pc):
                pc[kt + 1] = 0.02 * 0.70 * c80

            nop_l = {**op, "flux": fo_a + 0.25 * c80 * g_l}
            nop_i = {**op, "flux": fo_a + pc}
            nop_p = {**op, "flux": fo_a + 0.35 * c80 * g_p}
            if op.get("flux_a") is not None:
                c80a = exact_quantile_1d(op["flux_a"][np.isfinite(op["flux_a"]) & (op["flux_a"] > 0)], 0.80) if np.sum(op["flux_a"] > 0) >= 10 else 1.0
                nop_l["flux_a"] = op["flux_a"] + 0.25 * c80a * g_l
                nop_i["flux_a"] = op["flux_a"] + (0.70 * c80a / max(1e-9, 0.70 * c80)) * pc
                nop_p["flux_a"] = op["flux_a"] + 0.35 * c80a * g_p
            if op.get("flux_b") is not None:
                c80b = exact_quantile_1d(op["flux_b"][np.isfinite(op["flux_b"]) & (op["flux_b"] > 0)], 0.80) if np.sum(op["flux_b"] > 0) >= 10 else 1.0
                nop_l["flux_b"] = op["flux_b"] + 0.25 * c80b * g_l
                nop_i["flux_b"] = op["flux_b"] + (0.70 * c80b / max(1e-9, 0.70 * c80)) * pc
                nop_p["flux_b"] = op["flux_b"] + 0.35 * c80b * g_p
            ol.append(nop_l)
            oi.append(nop_i)
            opl.append(nop_p)

        for tcls, exp_g45, rs in (
            ("TRUE_DUALFIBER_LASER", True, evaluate_gates_g3_g4_g5_spirou(ol, rw, n_ridge, cfg)),
            ("H4RG_IPC_HOT_PIXEL", False, evaluate_gates_g3_g4_g5_spirou(oi, rw, n_ridge, cfg)),
            ("H4RG_PERSISTENCE_PLATEAU", False, evaluate_gates_g3_g4_g5_spirou(opl, rw, n_ridge, cfg)),
        ):
            g45 = bool(rs["g4_pass"] and rs["g5_pass"])
            h4rg_rows.append({
                "star": rp["star"], "dp_id": rp["dp_id"], "band_id": rp["band_id"],
                "primary_order": rs.get("primary_order"), "primary_native_px": rs.get("primary_native_px"),
                "trial_class": tcls, "expected_g45_pass": exp_g45,
                "g4_pass": rs["g4_pass"], "g5_pass": rs["g5_pass"], "g45_pass": g45,
                "fiber_ab_tested": rs.get("fiber_ab_tested"), "fiber_ab_amp_ratio": rs.get("fiber_ab_amp_ratio"),
                "cos_1d_11px": rs.get("cos_1d_11px"), "ipc_hotpx_ratio": rs.get("ipc_hotpx_ratio"),
                "far_wing_34_ratio": rs.get("far_wing_34_ratio"),
                "g4_reason": rs["g4_reason"], "g5_reason": rs["g5_reason"],
            })

    # Suite E: 240-Trial Head-to-Head G6_V36 Sparse vs G6_V35 Dense Coincidence Trials (20 Patches x 3 Sigmas x 4 Classes)
    g6_rows = []
    for gp in bundle["calib_g6_patches"]:
        tc, co, cpx = float(gp["cand_topo_vac_a"]), gp["cand_order"], gp["cand_px"]
        tvs, tbv = float(gp["target_vshift_kms"]), float(gp["target_berv_kms"])
        tdp, odp, obv = gp["dp_id"], gp["opp_dp_id"], float(gp["opp_berv_kms"])
        real_d, real_s = list(gp["local_dense_atlas"]), list(gp["local_sparse_atlas"])
        oth_stars = gp["synthetic_other_stars"]
        for sg in G6_CALIBRATION_SIGMAS:
            prom_inj = round(0.030 * (sg / 6.0), 4)
            fn_inj = round(1.0 + prom_inj, 5)
            # Class 1: True Barycentric Laser (uses pure real SPIRou dense & sparse atlases!)
            r1_d = evaluate_gate_g6_v35_dense(gp["star"], tc, co, cpx, tvs, real_d, cfg)
            r1_s = evaluate_gate_g6_v36_sparse(gp["star"], tdp, tbv, tc, co, cpx, tvs, real_s, cfg, "T")
            # Class 2: Unlisted Sky OH Emission Line (3 other stars at same topocentric wave)
            oh_recs = [{"star": s2, "dp_id": f"SYN_{s2}", "berv_kms": 0.0, "vshift_kms": vs2, "topo_vac_a": tc + 0.015 * (idx - 1), "order": (co + 1 if co is not None else None), "px": (cpx + 140 if cpx is not None else None), "prom_rel": prom_inj, "snr_local": sg, "f_norm_pk3": fn_inj, "fwhm_over_lsf": 1.0} for idx, (s2, vs2) in enumerate(oth_stars)]
            r2_d = evaluate_gate_g6_v35_dense(gp["star"], tc, co, cpx, tvs, real_d + oh_recs, cfg)
            r2_s = evaluate_gate_g6_v36_sparse(gp["star"], tdp, tbv, tc, co, cpx, tvs, real_s + oh_recs, cfg, "T")
            # Class 3: Stationary H4RG Warm Pixel (3 other stars at same native (order, px))
            px_recs = [{"star": s2, "dp_id": f"SYN_{s2}", "berv_kms": 0.0, "vshift_kms": vs2, "topo_vac_a": tc + 1.35 + 0.1 * idx, "order": co, "px": cpx, "prom_rel": prom_inj, "snr_local": sg, "f_norm_pk3": fn_inj, "fwhm_over_lsf": 0.85} for idx, (s2, vs2) in enumerate(oth_stars)]
            r3_d = evaluate_gate_g6_v35_dense(gp["star"], tc, co, cpx, tvs, real_d + px_recs, cfg)
            r3_s = evaluate_gate_g6_v36_sparse(gp["star"], tdp, tbv, tc, co, cpx, tvs, real_s + px_recs, cfg, "T")
            # Class 4: Intra-star Multi-Epoch BERV-Stationary Defect (same star opposite BERV epoch)
            intra_rec = [{"star": gp["star"], "dp_id": odp, "berv_kms": obv, "vshift_kms": tvs + (obv - tbv), "topo_vac_a": tc + 0.02, "order": co, "px": cpx, "prom_rel": prom_inj, "snr_local": sg, "f_norm_pk3": fn_inj, "fwhm_over_lsf": 1.0}]
            r4_d = evaluate_gate_g6_v35_dense(gp["star"], tc, co, cpx, tvs, real_d + intra_rec, cfg)
            r4_s = evaluate_gate_g6_v36_sparse(gp["star"], tdp, tbv, tc, co, cpx, tvs, real_s + intra_rec, cfg, "T")

            for tcls, exp_p, rd, rs in (
                ("TRUE_BARYCENTRIC_STELLAR_LASER", True, r1_d, r1_s),
                ("UNLISTED_STATIONARY_SKY_OH_LINE", False, r2_d, r2_s),
                ("STATIONARY_H4RG_WARM_PIXEL", False, r3_d, r3_s),
                ("INTRA_STAR_BERV_STATIONARY_GHOST", False, r4_d, r4_s),
            ):
                g6_rows.append({
                    "star": gp["star"], "dp_id": tdp, "band_id": gp["band_id"],
                    "sigma_inj": sg, "trial_class": tcls, "expected_g6_pass": exp_p,
                    "g6_v35_dense_pass": rd["g6_v35_pass"], "g6_v35_coincident_stars": rd["g6_v35_coincident_total_stars"],
                    "g6_v36_sparse_pass": rs["g6_pass"], "g6_v36_coincident_stars": rs["g6_coincident_total_stars"],
                    "g6_v36_same_star_hits": rs["g6_same_star_stationary_hits"],
                    "g6_v35_reason": rd["g6_v35_reason"], "g6_v36_reason": rs["g6_reason"],
                })

    # Suite F: 381-Trial V4 COMB Calibration (288 true combs + 48 single-line masquerades + 45 topo ro-vib pseudocombs)
    comb_cal_rows = []
    bgrid_full = np.round(np.arange(cfg["wave_min_angstrom"], cfg["wave_max_angstrom"] + 0.5 * step_c, step_c), 5)
    for idx_cp, cp in enumerate(bundle["calib_comb_patches"]):
        ww = np.asarray(cp["wave_win"], dtype=np.float64)
        yr = _arr_from_nullable(cp["y_rest_win"])
        sr = _arr_from_nullable(cp["sigma_rest_win"])
        fn = _arr_from_nullable(cp["fn_win"])
        rc = np.where(np.isfinite(_arr_from_nullable(cp["recon_win"])), _arr_from_nullable(cp["recon_win"]), 1.0)
        sk = np.asarray(cp["sky_mask_win"], dtype=bool)
        yt = _arr_from_nullable(cp["y_topo_win"])
        st_arr = _arr_from_nullable(cp["sigma_topo_win"])
        # Embed patch directly onto global bgrid so exact scan_frequency_comb_v4 executes identically!
        i0 = int(np.searchsorted(bgrid_full, float(ww[0]), side="left"))
        i1 = i0 + len(ww)
        #Temporarily localize cleanly on ww with patched window config!
        # Wait: scan_frequency_comb_v4 only uses ww[0]..ww[-1] inside win["lo_a"]..win["hi_a"]! If any bins outside ww are NaN, z_raw=-9 on outside!
        med_sr = exact_median_1d(sr[np.isfinite(sr) & (sr > 0)])
        nu_lo_c, nu_hi_c = float(cp["nu_lo_ghz"]), float(cp["nu_hi_ghz"])
        # Construct temporary 1D arrays aligned on bgrid_full
        yg = np.full(len(bgrid_full), np.nan, dtype=np.float64)
        sg = np.full(len(bgrid_full), np.nan, dtype=np.float64)
        fg = np.full(len(bgrid_full), 1.0, dtype=np.float64)
        rg = np.zeros(len(bgrid_full), dtype=np.float64)
        skg = np.ones(len(bgrid_full), dtype=bool)
        ytg = np.full(len(bgrid_full), np.nan, dtype=np.float64)
        stg = np.full(len(bgrid_full), np.nan, dtype=np.float64)

        b_sl = slice(i0, min(len(bgrid_full), i1))
        ln = b_sl.stop - b_sl.start
        yg[b_sl], sg[b_sl], fg[b_sl], rg[b_sl], skg[b_sl] = yr[:ln], sr[:ln], np.where(np.isfinite(fn[:ln]), fn[:ln], 1.0), rc[:ln], sk[:ln]
        ytg[b_sl], stg[b_sl] = yt[:ln], st_arr[:ln]
        loc_cfg = {**cfg, "comb_search_bands": [cp["band"]]}

        for dnu in COMB_CALIBRATION_SPACINGS:
            dnu_s = float(dnu)
            # Pick valid starting nu0 where all 6 teeth fall on finite clean bins inside [nu_lo_c + 20, nu_hi_c - 5*dnu_s - 20]
            span_g = 5.0 * dnu_s
            best_nu0 = None
            best_cnt = -1
            for off in range(15, max(16, int(nu_hi_c - nu_lo_c - span_g - 15)), 5):
                n0_try = nu_lo_c + off
                t_waves = [C_ANGSTROM_GHZ / (n0_try + t * dnu_s) for t in range(6)]
                ks = [int(np.argmin(np.abs(ww - wt_a))) for wt_a in t_waves]
                clean_c = sum(1 for k_t in ks if 10 <= k_t < len(ww) - 10 and np.isfinite(yr[k_t]) and np.isfinite(sr[k_t]) and sr[k_t] > 0 and rc[k_t] >= 0.84 and not sk[k_t])
                if clean_c > best_cnt:
                    best_cnt, best_nu0 = clean_c, n0_try
                if clean_c == 6:
                    break
            assert best_nu0 is not None
            t_waves = [C_ANGSTROM_GHZ / (best_nu0 + t * dnu_s) for t in range(6)]
            med_st = exact_median_1d(st_arr[np.isfinite(st_arr) & (st_arr > 0)])
            t_sig_local = []
            t_topo_sig = []
            for wt_a in t_waves:
                kt = int(np.argmin(np.abs(ww - wt_a)))
                t_sig_local.append(float(sr[kt]) if np.isfinite(sr[kt]) and sr[kt] > 0 else med_sr)
                t_topo_sig.append(float(st_arr[kt]) if np.isfinite(st_arr[kt]) and st_arr[kt] > 0 else med_st)

            # Build tooth unit Gaussians in stellar rest frame + BERV-smeared topocentric response + stationary topo unit
            tooth_unit = np.zeros(len(ww), dtype=np.float64)
            topo_unit = np.zeros(len(ww), dtype=np.float64)
            topo_smear_unit = np.zeros(len(ww), dtype=np.float64)
            berv_sp = max(6.0, float(cp["berv_span_kms"]))
            sig_smear_v = max(sig_v, 0.35 * berv_sp)
            for wt_a, sloc, stloc in zip(t_waves, t_sig_local, t_topo_sig):
                prof_w = np.exp(-0.5 * ((C_KMS * (ww - wt_a) / wt_a) / sig_v) ** 2)
                tooth_unit += sloc * prof_w
                topo_unit += max(sloc, stloc) * prof_w
                topo_smear_unit += (sloc * (sig_v / sig_smear_v)) * np.exp(-0.5 * ((C_KMS * (ww - wt_a) / wt_a) / sig_smear_v) ** 2)

            sub_cfg = {**loc_cfg, "comb_spacings_ghz": [dnu_s]}
            # Class 1: True 6-tooth stellar comb (6 SNR levels -> 288 trials)
            for snr_t in COMB_CALIBRATION_SIGMAS:
                yg_i = yg.copy()
                fg_i = fg.copy()
                ytg_i = ytg.copy()
                yg_i[b_sl] = np.where(np.isfinite(yr[:ln]), yr[:ln] + snr_t * tooth_unit[:ln], np.nan)
                fg_i[b_sl] = np.where(np.isfinite(fn[:ln]), fn[:ln] + snr_t * tooth_unit[:ln], 1.0)
                ytg_i[b_sl] = np.where(np.isfinite(yt[:ln]), yt[:ln] + snr_t * topo_smear_unit[:ln], 0.0)
                hits_c, _ = scan_frequency_comb_v4(bgrid_full, yg_i, sg, fg_i, rg, skg, ytg_i, stg, float(cp["median_berv_kms"]), float(cp["v_star_kms"]), sub_cfg)
                matched = any(abs(h["nu0_ghz"] - best_nu0) <= 5.0 for h in hits_c)
                comb_cal_rows.append({"star": cp["star"], "band": cp["band"], "dnu_ghz": dnu_s, "trial_class": "TRUE_6TOOTH_STELLAR_COMB", "tooth_snr_inj": snr_t, "expected_comb_hit": True, "comb_hit": matched, "max_s_comb": round(max((h["s_comb"] for h in hits_c), default=0.0), 4)})

            # Class 2: Single Bright Line Masquerade (20 sigma on tooth 2 only -> 48 trials)
            one_unit = t_sig_local[2] * np.exp(-0.5 * ((C_KMS * (ww - t_waves[2]) / t_waves[2]) / sig_v) ** 2)
            yg_1 = yg.copy()
            fg_1 = fg.copy()
            yg_1[b_sl] = np.where(np.isfinite(yr[:ln]), yr[:ln] + 20.0 * one_unit[:ln], np.nan)
            fg_1[b_sl] = np.where(np.isfinite(fn[:ln]), fn[:ln] + 20.0 * one_unit[:ln], 1.0)
            hits_1, _ = scan_frequency_comb_v4(bgrid_full, yg_1, sg, fg_1, rg, skg, ytg, stg, float(cp["median_berv_kms"]), float(cp["v_star_kms"]), sub_cfg)
            comb_cal_rows.append({"star": cp["star"], "band": cp["band"], "dnu_ghz": dnu_s, "trial_class": "SINGLE_BRIGHT_LINE_MASQUERADE", "tooth_snr_inj": 20.0, "expected_comb_hit": False, "comb_hit": len(hits_1) > 0, "max_s_comb": round(max((h["s_comb"] for h in hits_1), default=0.0), 4)})

            # Class 3: Stationary Topocentric Ro-Vibrational Pseudocomb (first 15 patches -> 45 trials)
            if idx_cp < 15:
                yg_t = yg.copy()
                fg_t = fg.copy()
                ytg_t = ytg.copy()
                # Exact aligned in topocentric + residual leaked into stellar rest at median BERV -> anti-comb ratio = 1.0 > 0.75
                yg_t[b_sl] = np.where(np.isfinite(yr[:ln]), yr[:ln] + 6.0 * tooth_unit[:ln], np.nan)
                fg_t[b_sl] = np.where(np.isfinite(fn[:ln]), fn[:ln] + 6.0 * tooth_unit[:ln], 1.0)
                ytg_t[b_sl] = np.where(np.isfinite(yt[:ln]), yt[:ln] + 6.2 * topo_unit[:ln], 0.0)
                hits_t, _ = scan_frequency_comb_v4(bgrid_full, yg_t, sg, fg_t, rg, skg, ytg_t, stg, float(cp["median_berv_kms"]), float(cp["v_star_kms"]), sub_cfg)
                comb_cal_rows.append({"star": cp["star"], "band": cp["band"], "dnu_ghz": dnu_s, "trial_class": "STATIONARY_TOPO_ROVIB_PSEUDOCOMB", "tooth_snr_inj": 6.0, "expected_comb_hit": False, "comb_hit": len(hits_t) > 0, "max_s_comb": round(max((h["s_comb"] for h in hits_t), default=0.0), 4)})

    # Band completeness summary (9 calibration bands x T & P)
    calib_band_rows = []
    for mode, s_list in (("CHANNEL_T_TRANSIENT_1EPOCH", TRANSIENT_INJECTION_SIGMAS), ("CHANNEL_P_PERSISTENT_5EPOCH", PERSISTENT_INJECTION_SIGMAS)):
        for bnd in CALIB_9_BANDS:
            for sm in s_list:
                sub = [r for r in inj_rows if r["mode"] == mode and r["band_id"] == bnd["band_id"] and r["sigma_mult"] == sm]
                nt, nr = len(sub), sum(1 for r in sub if r["recovered"])
                calib_band_rows.append({"instrument": "SPIROU", "mode": mode, "band_id": bnd["band_id"], "center_vac_A": bnd["center_vac_A"], "sigma_mult": sm, "n_trials": nt, "n_recovered": nr, "completeness": nr / nt if nt > 0 else 0.0})

    # 3. Evaluate All Uninjected Single-Line Candidates Across Channels T, P, T_DIFF, K_PLANET + G1..G6 (Head-to-Head V35 Dense vs V36 Sparse)
    v36_ledger = []
    cand_idx = 0
    dense_atlas = bundle["dense_atlas"]
    sparse_atlas = bundle["sparse_atlas"]

    def _eval_cand(item: dict[str, Any], channel: str) -> None:
        nonlocal cand_idx
        cand_idx += 1
        cid = f"V36-{channel}-{cand_idx:04d}"
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

        g2 = evaluate_gate_g2_spirou_atmosphere(
            bary_a, float(item["berv_kms"]), np.asarray(item["s1d_wave_win"], dtype=np.float64),
            _arr_from_nullable(item["s1d_recon_win"]), _arr_from_nullable(item["s1d_oh_rel_win"]),
            _arr_from_nullable(item["s1d_pre_win"]), _arr_from_nullable(item["s1d_post_win"]), fit1.get("amp_mid", 0.0), cfg,
        )
        n_ridge = sum(1 for v in item["other_stars_fn_max_pm0p16"].values() if float(v) >= cfg["gate_g3_cross_star_ridge_fn_min"])
        if g2["g2_pass"] and item["order_patches"]:
            g345 = evaluate_gates_g3_g4_g5_spirou(_unpack_order_patches(item["order_patches"]), rest_a, n_ridge, cfg)
        else:
            g345 = {"g3_pass": False, "g3_reason": "NOT_EVALUATED", "g4_pass": False, "g4_reason": "NOT_EVALUATED", "g5_pass": False, "g5_reason": "NOT_EVALUATED"}

        g6d = evaluate_gate_g6_v35_dense(item["star"], g2["topo_vac_a"], g345.get("primary_order"), g345.get("primary_native_px"), float(item["vshift_kms"]), dense_atlas, cfg)
        g6s = evaluate_gate_g6_v36_sparse(item["star"], item["dp_id"], float(item["berv_kms"]), g2["topo_vac_a"], g345.get("primary_order"), g345.get("primary_native_px"), float(item["vshift_kms"]), sparse_atlas, cfg, channel)
        pre_g6 = bool(f1c["f1_supraphotospheric_pass"] and g2["g2_pass"] and g345["g3_pass"] and g345["g4_pass"] and g345["g5_pass"])
        qual_v36 = bool(pre_g6 and g6s["g6_pass"])

        if not f1c["f1_supraphotospheric_pass"]:
            disp = "G1_V36_SUBCONTINUUM_VETO"
        elif not g2["g2_pass"]:
            disp = g2["g2_reason"]
        elif not g345["g3_pass"]:
            disp = g345["g3_reason"]
        elif not g345["g4_pass"]:
            disp = g345["g4_reason"]
        elif not g345["g5_pass"]:
            disp = g345["g5_reason"]
        elif not g6s["g6_pass"]:
            disp = g6s["g6_reason"]
        else:
            disp = "QUALIFIED_V3_6_LASER_CANDIDATE"

        v36_ledger.append({
            "candidate_id": cid, "instrument": "SPIROU", "channel": channel, "role": item["role"],
            "star": item["star"], "dp_id": item["dp_id"], "fitted_wave_a": fc_a,
            "stellar_rest_wave_a": rest_a, "bary_wave_a": bary_a, "topo_wave_a": g2["topo_vac_a"],
            "snr_mid": fit1.get("snr_mid", 0.0), "snr_out": fit1.get("snr_out", 0.0),
            "cosine": fit1.get("cosine", 0.0), "fwhm_ratio": fit1.get("fwhm_ratio"),
            "target_fn_pk3": f1c["fn_pk3"], "atm_transm_center": g2["atm_transm_center"],
            "oh_rel_pk3": g2["oh_rel_pk3"], "pre_post_consistency": g2["pre_post_consistency"],
            "cross_star_ridge_count": n_ridge,
            "g1_pass": f1c["f1_supraphotospheric_pass"], "g2_pass": g2["g2_pass"],
            "g3_pass": g345["g3_pass"], "primary_order": g345.get("primary_order"),
            "primary_native_px": g345.get("primary_native_px"),
            "primary_native_fn_pk3": g345.get("primary_native_fn_pk3"),
            "primary_template_dip_frac": g345.get("primary_template_dip_frac"),
            "primary_eta_1px": g345.get("primary_eta_1px"),
            "g4_pass": g345["g4_pass"], "fiber_ab_tested": g345.get("fiber_ab_tested"),
            "fiber_ab_amp_ratio": g345.get("fiber_ab_amp_ratio"), "overlap_tested": g345.get("overlap_tested"),
            "g5_pass": g345["g5_pass"], "g5_cos11": g345.get("cos_1d_11px"),
            "g5_ipc_hotpx_ratio": g345.get("ipc_hotpx_ratio"), "g5_far_wing_ratio": g345.get("far_wing_34_ratio"),
            "pre_g6_qualified": pre_g6,
            "g6_v35_dense_pass": g6d["g6_v35_pass"], "g6_v35_stars": g6d["g6_v35_coincident_total_stars"],
            "g6_pass": g6s["g6_pass"], "g6_coincident_total_stars": g6s["g6_coincident_total_stars"],
            "g6_same_star_stationary_hits": g6s["g6_same_star_stationary_hits"],
            "g6_reason": g6s["g6_reason"], "qualified_v36_laser": qual_v36, "final_disposition": disp,
        })

    for ch_key, b_key in (("T", "channel_t_candidates_bundle"), ("P", "channel_p_candidates_bundle"), ("T_DIFF", "channel_tdiff_candidates_bundle"), ("K_PLANET", "channel_kplanet_candidates_bundle")):
        for item in bundle[b_key]:
            _eval_cand(item, ch_key)

    # Recompute Stage B V4 COMB candidates from bounded bundle windows
    raw_comb_re = []
    for cb in bundle["comb_real_candidates_bundle"]:
        ww = np.asarray(cb["wave_win"], dtype=np.float64)
        yr = _arr_from_nullable(cb["y_rest_win"])
        sr = _arr_from_nullable(cb["sigma_rest_win"])
        fn = np.where(np.isfinite(_arr_from_nullable(cb["fn_win"])), _arr_from_nullable(cb["fn_win"]), 1.0)
        rc = np.where(np.isfinite(_arr_from_nullable(cb["recon_win"])), _arr_from_nullable(cb["recon_win"]), 1.0)
        sk = np.asarray(cb["sky_mask_win"], dtype=bool)
        yt = _arr_from_nullable(cb["y_topo_win"])
        stg_w = _arr_from_nullable(cb["sigma_topo_win"])
        hits_re, _ = scan_frequency_comb_v4(
            ww, yr, sr, fn, rc, sk, yt, stg_w, float(cb["median_berv_kms"]), float(cb["v_star_kms"]),
            {**cfg, "comb_search_bands": [cb["band"]], "comb_spacings_ghz": [cb["dnu_ghz"]]},
        )
        seed_nu0 = cb.get("nu0_ghz_stage_a")
        if seed_nu0 is not None:
            matched_re = [hr for hr in hits_re if abs(float(hr["nu0_ghz"]) - float(seed_nu0)) <= 0.5 * float(cb["dnu_ghz"])]
            hits_re = [max(matched_re, key=lambda h: float(h["s_comb"]))] if matched_re else []
        for hr in hits_re:
            raw_comb_re.append((cb["star"], cb["role"], hr))

    raw_comb_re.sort(key=lambda x: -float(x[2]["s_comb"]))
    dedup_comb_re = []
    for st_c, role_c, hr in raw_comb_re:
        if any(
            st_p == st_c and hp["band"] == hr["band"] and float(hp["dnu_ghz"]) == float(hr["dnu_ghz"])
            and abs(float(hp["nu0_ghz"]) - float(hr["nu0_ghz"])) <= 0.5 * float(hr["dnu_ghz"])
            for st_p, _, hp in dedup_comb_re
        ):
            continue
        dedup_comb_re.append((st_c, role_c, hr))
    dedup_comb_re.sort(key=lambda x: (x[0], x[2]["band"], float(x[2]["dnu_ghz"]), -float(x[2]["s_comb"])))
    comb_cand_rows = []
    for st_c, role_c, hr in dedup_comb_re:
        comb_cand_rows.append({
            "comb_id": f"V4COMB-{len(comb_cand_rows)+1:04d}",
            "star": st_c, "role": role_c, "band": hr["band"], "dnu_ghz": hr["dnu_ghz"],
            "nu0_ghz": hr["nu0_ghz"], "wave0_vac_a": hr["wave0_vac_a"], "wave_end_vac_a": hr["wave_end_vac_a"],
            "s_comb": hr["s_comb"], "s_comb_topo": hr["s_comb_topo"], "topo_anti_ratio": hr["topo_anti_ratio"],
            "n_qualifying_teeth": hr["n_qualifying_teeth"], "max_tooth_frac": hr["max_tooth_frac"],
            "teeth_vac_a": ";".join(str(x) for x in hr["teeth_vac_a"]),
            "tooth_z_caps": ";".join(str(x) for x in hr["tooth_z_caps"]),
        })

    comb_star_rows = []
    for st in sorted(by_star_rows.keys()):
        cm = bundle["comb_real_summary_by_star"][st]
        s0 = by_star_rows[st][0]
        hits_st = [c for c in comb_cand_rows if c["star"] == st]
        comb_star_rows.append({
            "star": st, "common_name": s0["common_name"], "role": cm["role"], "dist_pc": float(s0["dist_pc"]),
            "n_epochs": cm["n_epochs"], "berv_span_kms": cm["berv_span_kms"],
            "searched_comb_configs": cm["searched_comb_configs"],
            "median_sigma_rest_yjh_k": cm["median_sigma_rest_yjh_k"],
            "comb_v4_candidates": len(hits_st),
            "max_comb_score": max((c["s_comb"] for c in hits_st), default=0.0),
            "verified_eti_comb": 0,
        })

    # 4. Per-exposure Benchmark Table (177 Exposures)
    bench_rows = []
    for idx_r, r in enumerate(cohort_rows, start=1):
        dp = r["dp_id"]
        ss = bundle["searched_summary_by_dp"][dp]
        cd = [c for c in v36_ledger if c["channel"] == "T" and c["dp_id"] == dp]
        bench_rows.append({
            "cohort_index": idx_r, "instrument": "SPIROU", "role": r["role"], "subrole": r["subrole"],
            "panchromatic_bridge": r["panchromatic_bridge"] == "True",
            "star": r["canonical_target"], "epoch_rank": int(r["epoch_rank"]), "phase_window": r["phase_window"],
            "dp_id": dp, "snr_obs": float(prov_by_dp[dp]["snr_obs"]),
            "v2_searched_bins": ss["v2_searched_bins"], "v2_screened_events": ss["v2_screened_events"],
            "v2_accepted_false_alarms": ss["v2_accepted_hits"], "v31_pre_f1_g1_hits": ss["v31_pre_f1_g1_hits"],
            "v36_searched_bins": ss["v36_channel_t_searched_bins"],
            "v36_g1_hits": len(cd),
            "v36_after_g2": sum(1 for c in cd if c["g2_pass"]),
            "v36_after_g3": sum(1 for c in cd if c["g2_pass"] and c["g3_pass"]),
            "v36_after_g4": sum(1 for c in cd if c["g2_pass"] and c["g3_pass"] and c["g4_pass"]),
            "v36_after_g5_pre_g6": sum(1 for c in cd if c["pre_g6_qualified"]),
            "v36_qualified_lasers": sum(1 for c in cd if c["qualified_v36_laser"]),
        })

    # 5. Orbital Campaign Summary Table (10 Campaigns)
    orbital_rows = []
    for ostar, om in sorted(bundle["orbital_campaign_meta_by_star"].items()):
        s0 = by_star_rows[ostar][0]
        best_td_kw, best_kp_kw = float("inf"), float("inf")
        td_mads, kp_mads = [], []
        for bnd in BENCHMARK_LASER_BANDS_V36:
            mtd, mkp = float(om["band_mads_tdiff"][bnd["band_id"]]), float(om["band_mads_kplanet"][bnd["band_id"]])
            td_mads.append(mtd)
            kp_mads.append(mkp)
            ltd = compute_spirou_laser_power_limits(float(bnd["center_vac_A"]), 8.0 * mtd, float(s0["j_mag"]), float(s0["h_mag"]), float(s0["ks_mag"]), float(s0["teff_k"]), float(s0["dist_pc"]), cfg)
            lkp = compute_spirou_laser_power_limits(float(bnd["center_vac_A"]), 8.0 * mkp, float(s0["j_mag"]), float(s0["h_mag"]), float(s0["ks_mag"]), float(s0["teff_k"]), float(s0["dist_pc"]), cfg)
            best_td_kw = min(best_td_kw, ltd["p_beam_10m_kw"])
            best_kp_kw = min(best_kp_kw, lkp["p_beam_10m_kw"])
        td_c = [c for c in v36_ledger if c["channel"] == "T_DIFF" and c["star"] == ostar]
        kp_c = [c for c in v36_ledger if c["channel"] == "K_PLANET" and c["star"] == ostar]
        orbital_rows.append({
            "instrument": "SPIROU", "role": om["role"], "subrole": om["subrole"], "window_mode": om["window_mode"],
            "star": ostar, "common_name": s0["common_name"], "planet_name": om["planet_name"],
            "dist_pc": float(s0["dist_pc"]), "orbper_days": om["orbper_days"], "kp_kms": om["kp_kms"],
            "orbital_dv_span_kms": om["orbital_dv_span_kms"], "n_in_window": om["n_in_window"], "n_out_of_window": om["n_out_of_window"],
            "median_tdiff_mad_rel": exact_median_1d(np.asarray(td_mads)), "median_kplanet_mad_rel": exact_median_1d(np.asarray(kp_mads)),
            "tdiff_v36_g1_hits": len(td_c), "tdiff_qualified_v36": sum(1 for c in td_c if c["qualified_v36_laser"]),
            "kplanet_v36_g1_hits": len(kp_c), "kplanet_qualified_v36": sum(1 for c in kp_c if c["qualified_v36_laser"]),
            "best_tdiff_8sigma_10m_kw": best_td_kw, "best_kplanet_8sigma_10m_kw": best_kp_kw,
        })

    # 6. Physical 8-Sigma 10m Laser Power Upper Limits (25 Science Stars x 12 Bands = 300 Cells, 0 NaNs)
    upper_limit_rows = []
    bn_map: dict[tuple[str, str], list[float]] = {}
    for bnr in bundle["band_noise_rows"]:
        bn_map.setdefault((bnr["star"], bnr["band_id"]), []).append(float(bnr["empirical_resid_mad_t"]))
    for st in sorted([s for s in by_star_rows if by_star_rows[s][0]["role"] == "SCIENCE"]):
        s0 = by_star_rows[st][0]
        for bnd in BENCHMARK_LASER_BANDS_V36:
            bid, bc = bnd["band_id"], float(bnd["center_vac_A"])
            med_mad = exact_median_1d(np.asarray(bn_map[(st, bid)], dtype=np.float64))
            amp_lim = 8.0 * med_mad
            lim = compute_spirou_laser_power_limits(bc, amp_lim, float(s0["j_mag"]), float(s0["h_mag"]), float(s0["ks_mag"]), float(s0["teff_k"]), float(s0["dist_pc"]), cfg)
            upper_limit_rows.append({
                "instrument": "SPIROU", "star": st, "common_name": s0["common_name"], "subrole": s0["subrole"],
                "panchromatic_bridge": s0["panchromatic_bridge"] == "True", "radio_mm_id": s0["radio_mm_id"],
                "within_10pc": s0["within_10pc"] == "True", "n_exoplanets": int(s0["n_exoplanets"]),
                "has_transiting_planet": s0["has_transiting_planet"] == "True", "dist_pc": float(s0["dist_pc"]),
                "teff_k": float(s0["teff_k"]), "j_mag": float(s0["j_mag"]), "h_mag": float(s0["h_mag"]),
                "ks_mag": float(s0["ks_mag"]), "band_id": bid, "wave_bary_vac_A": bc,
                "median_epoch_mad_rel": med_mad, "amp_rel_8sigma_lim": amp_lim, **lim,
            })

    ul_by_star: dict[str, list[dict[str, Any]]] = {}
    for u in upper_limit_rows:
        ul_by_star.setdefault(u["star"], []).append(u)

    # 7. Eight-Star Panchromatic Optical-to-K Bridge (4 South D081-D083 + 4 North D084 CARMENES + D085 SPIRou)
    bridge_8 = list(prior_snapshot["d083_southern_bridge_rows"])
    for dr in prior_snapshot["d084_northern_bridge_optical_rows"]:
        wa = float(dr["wave_bary_vac_A"])
        bridge_8.append({
            "phase_id": "D084", "spectral_regime": "OPTICAL_FARRED_0p52_1p06um", "instrument": dr["instrument"],
            "star": dr["star"], "common_name": dr["common_name"], "dist_pc": float(dr["dist_pc"]),
            "band_id": dr["band_id"], "wave_um": round(wa / 10000.0, 5), "wave_A": wa,
            "ew_lim_mA": float(dr["ew_lim_mA"]), "flux_lim_erg_cm2_s": float(dr["flux_lim_erg_cm2_s"]),
            "l_iso_mw": float(dr["l_iso_mw"]), "p_beam_10m_kw": float(dr["p_beam_10m_kw"]), "p_beam_10m_w": float(dr["p_beam_10m_w"]),
        })
    for u in upper_limit_rows:
        if u["panchromatic_bridge"]:
            wa = float(u["wave_bary_vac_A"])
            bridge_8.append({
                "phase_id": "D085", "spectral_regime": "YJHK_0p955_2p515um", "instrument": "SPIROU",
                "star": u["star"], "common_name": u["common_name"], "dist_pc": float(u["dist_pc"]),
                "band_id": u["band_id"], "wave_um": round(wa / 10000.0, 5), "wave_A": wa,
                "ew_lim_mA": float(u["ew_lim_mA"]), "flux_lim_erg_cm2_s": float(u["flux_lim_erg_cm2_s"]),
                "l_iso_mw": float(u["l_iso_mw"]), "p_beam_10m_kw": float(u["p_beam_10m_kw"]), "p_beam_10m_w": float(u["p_beam_10m_w"]),
            })
    bridge_8.sort(key=lambda r: (str(r["star"]), float(r["wave_A"]), str(r["phase_id"])))

    # 8. Unified 150-Star Panchromatic V3 Synthesis (D079-D085, 1,009 Exposures, 73 < 10 pc)
    def _f_none(v: Any) -> float | None:
        if v is None or v == "":
            return None
        fv = float(v)
        return fv if math.isfinite(fv) else None

    by_star_u150: dict[str, dict[str, Any]] = {}
    for pr in prior_snapshot["unified_125star_rows"]:
        st = pr["star"]
        by_star_u150[st] = {
            "phases": pr["phases"], "hemisphere": pr["hemisphere"], "spectral_regime": pr["spectral_regime"],
            "instruments": pr["instruments"], "star": st, "common_name": pr["common_name"],
            "role": pr["role"], "subrole": pr["subrole"], "dist_pc": float(pr["dist_pc"]),
            "within_10pc": str(pr["within_10pc"]) == "True", "teff_k": float(pr["teff_k"]),
            "phot_g_mag": float(pr["phot_g_mag"]), "j_mag": _f_none(pr.get("j_mag")),
            "h_mag": _f_none(pr.get("h_mag")), "ks_mag": _f_none(pr.get("ks_mag")),
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
        }

    for rvs in star_rv_summary:
        st = rvs["star"]
        s0 = by_star_rows[st][0]
        uls = ul_by_star.get(st, [])
        p_yjh = [float(x["p_beam_10m_kw"]) for x in uls if float(x["wave_bary_vac_A"]) < 18800.0]
        p_k = [float(x["p_beam_10m_kw"]) for x in uls if float(x["wave_bary_vac_A"]) >= 18800.0]
        by_b = {x["band_id"]: float(x["p_beam_10m_kw"]) for x in uls}
        q_v36 = sum(1 for c in v36_ledger if c["star"] == st and c["qualified_v36_laser"])
        p_sp_min = min([float(x["p_beam_10m_kw"]) for x in uls]) if uls else None

        if rvs["panchromatic_bridge"] and st in by_star_u150:
            row_e = by_star_u150[st]
            row_e["phases"] = "D084+D085"
            row_e["spectral_regime"] = "PANCHROMATIC_0p52_2p51um"
            row_e["instruments"] = "CARMENES_VIS+SPIROU"
            row_e["subrole"] = rvs["subrole"]
            row_e["j_mag"] = rvs["j_mag"]
            row_e["h_mag"] = rvs["h_mag"]
            row_e["ks_mag"] = rvs["ks_mag"]
            row_e["n_exposures_nir_yjh"] += rvs["n_epochs"]
            row_e["n_exposures_total"] += rvs["n_epochs"]
            prev_n = row_e["min_nir_yjh_10m_kw"]
            new_yjh = min(p_yjh) if p_yjh else None
            row_e["min_nir_yjh_10m_kw"] = min(prev_n, new_yjh) if (prev_n is not None and new_yjh is not None) else (new_yjh or prev_n)
            row_e["min_kband_10m_kw"] = min(p_k) if p_k else None
            row_e["p_1064nm_10m_kw"] = by_b.get("S3_NDYAG_10641")
            row_e["p_1550nm_10m_kw"] = by_b.get("S7_ER_CBAND_15500")
            row_e["p_2040nm_tm_10m_kw"] = by_b.get("S9_TM_FIBER_20400")
            row_e["p_2097nm_hoyag_10m_kw"] = by_b.get("S10_HOYAG_20970")
            prev_m = row_e["min_panchromatic_10m_kw"]
            row_e["min_panchromatic_10m_kw"] = min(prev_m, p_sp_min) if (prev_m is not None and p_sp_min is not None) else (prev_m or p_sp_min)
            row_e["automated_qualified_candidates"] += q_v36
        else:
            dec_v = float(s0["s_dec"])
            by_star_u150[st] = {
                "phases": "D085", "hemisphere": "SOUTHERN" if dec_v < 0.0 else "NORTHERN",
                "spectral_regime": "YJHK_0p955_2p515um", "instruments": "SPIROU",
                "star": st, "common_name": rvs["common_name"], "role": rvs["role"], "subrole": rvs["subrole"],
                "dist_pc": rvs["dist_pc"], "within_10pc": rvs["within_10pc"], "teff_k": rvs["teff_k"],
                "phot_g_mag": rvs["phot_g_mag"], "j_mag": rvs["j_mag"], "h_mag": rvs["h_mag"], "ks_mag": rvs["ks_mag"],
                "n_exoplanets": rvs["n_exoplanets"],
                "n_exposures_optical": 0, "n_exposures_nir_yjh": rvs["n_epochs"], "n_exposures_kband": 0,
                "n_exposures_total": rvs["n_epochs"],
                "min_optical_10m_kw": None, "min_nir_yjh_10m_kw": min(p_yjh) if p_yjh else None,
                "min_kband_10m_kw": min(p_k) if p_k else None,
                "p_1064nm_10m_kw": by_b.get("S3_NDYAG_10641"), "p_1550nm_10m_kw": by_b.get("S7_ER_CBAND_15500"),
                "p_2040nm_tm_10m_kw": by_b.get("S9_TM_FIBER_20400"), "p_2097nm_hoyag_10m_kw": by_b.get("S10_HOYAG_20970"),
                "min_panchromatic_10m_kw": p_sp_min,
                "automated_qualified_candidates": q_v36, "verified_eti_detections": 0,
            }

    unified_150 = sorted(by_star_u150.values(), key=lambda x: (float(x["dist_pc"]), x["star"]))
    if len(unified_150) != 150:
        raise RuntimeError(f"Expected 150 unique V3 stars, got {len(unified_150)}")
    solar_10pc_73 = [x for x in unified_150 if bool(x["within_10pc"])]

    # 9. Unified 160-System Multi-Messenger Synthesis (150 Echelle + 24 Radio/TESS - 14 Direct Overlaps = 160 Systems!)
    mm_by_v3: dict[str, list[dict[str, Any]]] = {}
    radio_only = []
    for ms in mm_snapshot["systems"]:
        cv3 = str(ms.get("canonical_v3_star") or "").strip()
        if cv3:
            mm_by_v3.setdefault(cv3, []).append(ms)
        else:
            radio_only.append(ms)

    mm_160 = []
    for sr in unified_150:
        st = sr["star"]
        exm = mm_by_v3.get(st, [])
        rads = [m for m in exm if "RADIO" in m["modality"]]
        lss = [m for m in exm if "LIGHTSAIL" in m["modality"] or "PHOTOMETRIC" in m["modality"]]
        mods = ["ECHELLE_SPECTROSCOPY"]
        if rads:
            mods.append("RADIO_1p4GHZ_PLANET_FRAME")
        if lss:
            mods.append("TESS_SPECULAR_LIGHTSAIL")
        mm_160.append({
            "system_id": st, "host_name": sr["common_name"], "hemisphere": sr["hemisphere"], "role": sr["role"],
            "dist_pc": sr["dist_pc"], "within_10pc": sr["within_10pc"], "n_exoplanets": sr["n_exoplanets"],
            "modalities_searched": "+".join(mods), "n_modalities": len(mods), "multimessenger_overlap": len(mods) >= 2,
            "echelle_phases": sr["phases"], "echelle_instruments": sr["instruments"],
            "echelle_exposures": sr["n_exposures_total"], "min_echelle_10m_kw": sr["min_panchromatic_10m_kw"],
            "radio_milestone": "+".join(m["milestone"] for m in rads) if rads else "",
            "radio_facility": "+".join(m["facility"] for m in rads) if rads else "",
            "radio_snr40_recovery": rads[0]["snr40_recovery_fraction"] if rads else None,
            "lightsail_milestone": "+".join(m["milestone"] for m in lss) if lss else "",
            "verified_eti_detections": 0,
        })
    for rs in radio_only:
        mm_160.append({
            "system_id": rs["mm_id"], "host_name": rs["host_name"],
            "hemisphere": "NORTHERN" if "Green Bank" in rs["facility"] else "SOUTHERN",
            "role": "SCIENCE", "dist_pc": None, "within_10pc": None, "n_exoplanets": 1,
            "modalities_searched": "RADIO_1p4GHZ_PLANET_FRAME", "n_modalities": 1, "multimessenger_overlap": False,
            "echelle_phases": "", "echelle_instruments": "", "echelle_exposures": 0, "min_echelle_10m_kw": None,
            "radio_milestone": rs["milestone"], "radio_facility": rs["facility"],
            "radio_snr40_recovery": rs["snr40_recovery_fraction"], "lightsail_milestone": "", "verified_eti_detections": int(rs["verified_eti"]),
        })

    # Write all CSV deliverables
    write_csv(res_dir / "EXPOSURE_PROVENANCE_177.csv", bundle["provenance_rows"])
    write_csv(res_dir / "STELLAR_RV_ANCHORS_2124.csv", rv_anchor_rows)
    write_csv(res_dir / "STAR_RV_SUMMARY_29.csv", star_rv_summary)
    write_csv(res_dir / "INJECTION_RECOVERY_1620.csv", inj_rows)
    write_csv(res_dir / "KEPLERIAN_TRACK_CALIBRATION_135.csv", kep_rows)
    write_csv(res_dir / "DETECTOR_H4RG_G4G5_CALIBRATION_216.csv", h4rg_rows)
    write_csv(res_dir / "G6_SPARSE_VS_DENSE_CALIBRATION_240.csv", g6_rows)
    write_csv(res_dir / "COMB_V4_CALIBRATION_381.csv", comb_cal_rows)
    write_csv(res_dir / "CALIBRATION_COMPLETENESS_BY_BAND.csv", calib_band_rows)
    write_csv(res_dir / "V3_6_CANDIDATE_LEDGER.csv", v36_ledger)
    write_csv(res_dir / "FOUR_GEN_BENCHMARK_177.csv", bench_rows)
    write_csv(res_dir / "ORBITAL_CAMPAIGN_RESULTS_10.csv", orbital_rows)
    write_csv(res_dir / "COMB_V4_STAR_RESULTS_29.csv", comb_star_rows)
    write_csv(res_dir / "COMB_V4_CANDIDATES.csv", comb_cand_rows)
    write_csv(res_dir / "STAR_UPPER_LIMITS_300.csv", upper_limit_rows)
    write_csv(res_dir / "PANCHROMATIC_OPTICAL_NIR_K_BRIDGE_8STARS.csv", bridge_8)
    write_csv(res_dir / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_73STARS.csv", solar_10pc_73)
    write_csv(res_dir / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_150STARS.csv", unified_150)
    write_csv(res_dir / "MULTIMESSENGER_ECHELLE_RADIO_TESS_160SYSTEMS.csv", mm_160)

    # Metrics for SUMMARY.json & FORENSIC_SPIROU_CASCADE_DIAGNOSIS.json
    t_8 = [r for r in inj_rows if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH" and r["sigma_mult"] >= 8.0]
    p_9 = [r for r in inj_rows if r["mode"] == "CHANNEL_P_PERSISTENT_5EPOCH" and r["sigma_mult"] >= 9.0]
    p_12 = [r for r in inj_rows if r["mode"] == "CHANNEL_P_PERSISTENT_5EPOCH" and r["sigma_mult"] >= 12.0]
    kep_6p5 = [r for r in kep_rows if r["exp_sigma_mult"] >= 6.5]
    h_l = [r for r in h4rg_rows if r["trial_class"] == "TRUE_DUALFIBER_LASER"]
    h_i = [r for r in h4rg_rows if r["trial_class"] == "H4RG_IPC_HOT_PIXEL"]
    h_p = [r for r in h4rg_rows if r["trial_class"] == "H4RG_PERSISTENCE_PLATEAU"]
    g6_t = [r for r in g6_rows if r["trial_class"] == "TRUE_BARYCENTRIC_STELLAR_LASER"]
    g6_oh = [r for r in g6_rows if r["trial_class"] == "UNLISTED_STATIONARY_SKY_OH_LINE"]
    g6_px = [r for r in g6_rows if r["trial_class"] == "STATIONARY_H4RG_WARM_PIXEL"]
    g6_in = [r for r in g6_rows if r["trial_class"] == "INTRA_STAR_BERV_STATIONARY_GHOST"]
    c_hi = [r for r in comb_cal_rows if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and float(r["tooth_snr_inj"]) >= 3.8]
    c_1l = [r for r in comb_cal_rows if r["trial_class"] == "SINGLE_BRIGHT_LINE_MASQUERADE"]
    c_ro = [r for r in comb_cal_rows if r["trial_class"] == "STATIONARY_TOPO_ROVIB_PSEUDOCOMB"]

    forensic_cands = [c for c in v36_ledger if c["pre_g6_qualified"] or c["qualified_v36_laser"]]
    v36_q_ctrl = sum(1 for c in v36_ledger if c["role"] == "CONTROL" and c["qualified_v36_laser"])
    v36_q_sci = sum(1 for c in v36_ledger if c["role"] == "SCIENCE" and c["qualified_v36_laser"])
    best_u = min(upper_limit_rows, key=lambda x: float(x["p_beam_10m_w"]))
    best_10pc = [float(x["min_panchromatic_10m_kw"]) for x in solar_10pc_73 if x["min_panchromatic_10m_kw"] is not None]
    n_ovlp = sum(1 for r in mm_160 if r["multimessenger_overlap"])
    n_cal_d085 = len(inj_rows) + len(kep_rows) + len(h4rg_rows) + len(g6_rows) + len(comb_cal_rows)

    summary = {
        "phase_id": "D085",
        "detector": "SPIROU_V3_6_AND_COMB_V4",
        "instrument": "SPIROU",
        "resolving_power": 70000.0,
        "wavelength_domain_vac_um": [0.955, 2.515],
        "cohort": {
            "total_stars": len(by_star_rows),
            "control_stars": sum(1 for s in by_star_rows if by_star_rows[s][0]["role"] == "CONTROL"),
            "science_stars": sum(1 for s in by_star_rows if by_star_rows[s][0]["role"] == "SCIENCE"),
            "brand_new_unique_stars": sum(1 for s in by_star_rows if by_star_rows[s][0]["panchromatic_bridge"] != "True"),
            "panchromatic_bridge_stars_north": sum(1 for s in by_star_rows if by_star_rows[s][0]["panchromatic_bridge"] == "True"),
            "within_10pc_stars_d085": sum(1 for s in by_star_rows if by_star_rows[s][0]["within_10pc"] == "True"),
            "total_exposures": len(cohort_rows),
            "total_integration_hours": round(sum(float(r["exptime_s"]) for r in bundle["provenance_rows"]) / 3600.0, 4),
            "orbital_campaigns": len(orbital_rows),
        },
        "searched_spectral_elements": {
            "channel_t_1d_bins": sum(int(r["v36_searched_bins"]) for r in bench_rows),
            "channel_p_coadd_bins": sum(int(v["searched_bins"]) for v in bundle["channel_p_searched_by_star"].values()),
            "channel_tdiff_bins": sum(int(v["tdiff_searched_bins"]) for v in bundle["orbital_campaign_meta_by_star"].values()),
            "channel_kplanet_bins": sum(int(v["kplanet_searched_bins"]) for v in bundle["orbital_campaign_meta_by_star"].values()),
            "comb_v4_searched_configs": sum(int(r["searched_comb_configs"]) for r in comb_star_rows),
        },
        "rv_anchoring": {
            "total_anchor_fits": len(rv_anchor_rows),
            "clean_absorption_fits": sum(1 for r in rv_anchor_rows if r["status"] == "CLEAN_ABSORPTION"),
            "median_abs_empirical_minus_prior_kms": round(exact_median_1d(np.array([abs(r["empirical_minus_prior_kms"]) for r in star_rv_summary])), 4),
            "max_pure_stdlib_berv_diff_kms": round(max(abs(float(r["berv_kms"]) - float(r["berv_analytical_kms"])) for r in bundle["provenance_rows"]), 4),
        },
        "g6_atlas_compression": {
            "dense_v35_atlas_peaks": len(dense_atlas),
            "sparse_v36_atlas_peaks": len(sparse_atlas),
            "atlas_sparsity_ratio": round(len(dense_atlas) / max(1, len(sparse_atlas)), 3),
        },
        "synthetic_calibration_2592_trials": {
            "total_trials": n_cal_d085,
            "channel_t_trials": sum(1 for r in inj_rows if "CHANNEL_T" in r["mode"]),
            "channel_p_trials": sum(1 for r in inj_rows if "CHANNEL_P" in r["mode"]),
            "keplerian_paired_trials": len(kep_rows),
            "h4rg_g4g5_trials": len(h4rg_rows),
            "g6_sparse_vs_dense_trials": len(g6_rows),
            "comb_v4_trials": len(comb_cal_rows),
            "channel_t_ge_8sigma": round(sum(1 for r in t_8 if r["recovered"]) / max(1, len(t_8)), 5),
            "channel_p_ge_9sigma": round(sum(1 for r in p_9 if r["recovered"]) / max(1, len(p_9)), 5),
            "channel_p_ge_12sigma": round(sum(1 for r in p_12 if r["recovered"]) / max(1, len(p_12)), 5),
            "keplerian_tdiff_ge_6p5sigma": round(sum(1 for r in kep_6p5 if r["tdiff_uncomp_recovered"]) / max(1, len(kep_6p5)), 5),
            "keplerian_kplanet_ge_6p5sigma": round(sum(1 for r in kep_6p5 if r["kplanet_dedop_recovered"]) / max(1, len(kep_6p5)), 5),
            "h4rg_true_dualfiber_laser_pass": round(sum(1 for r in h_l if r["g45_pass"]) / max(1, len(h_l)), 5),
            "h4rg_ipc_hotpx_rejection": round(sum(1 for r in h_i if not r["g5_pass"]) / max(1, len(h_i)), 5),
            "h4rg_plateau_rejection": round(sum(1 for r in h_p if not r["g5_pass"]) / max(1, len(h_p)), 5),
            "g6_v35_dense_true_laser_pass": round(sum(1 for r in g6_t if r["g6_v35_dense_pass"]) / max(1, len(g6_t)), 5),
            "g6_v36_sparse_true_laser_pass": round(sum(1 for r in g6_t if r["g6_v36_sparse_pass"]) / max(1, len(g6_t)), 5),
            "g6_v36_sky_oh_rejection": round(sum(1 for r in g6_oh if not r["g6_v36_sparse_pass"]) / max(1, len(g6_oh)), 5),
            "g6_v36_warm_pixel_rejection": round(sum(1 for r in g6_px if not r["g6_v36_sparse_pass"]) / max(1, len(g6_px)), 5),
            "g6_v35_intra_star_stationary_rejection": round(sum(1 for r in g6_in if not r["g6_v35_dense_pass"]) / max(1, len(g6_in)), 5),
            "g6_v36_intra_star_stationary_rejection": round(sum(1 for r in g6_in if not r["g6_v36_sparse_pass"]) / max(1, len(g6_in)), 5),
            "comb_v4_6tooth_ge_3p8sigma_recovery": round(sum(1 for r in c_hi if r["comb_hit"]) / max(1, len(c_hi)), 5),
            "comb_v4_single_line_fpr": round(sum(1 for r in c_1l if r["comb_hit"]) / max(1, len(c_1l)), 5),
            "comb_v4_topo_rovib_pseudocomb_fpr": round(sum(1 for r in c_ro if r["comb_hit"]) / max(1, len(c_ro)), 5),
        },
        "false_alarm_cascade": {
            "v2_legacy_false_alarms": sum(int(r["v2_accepted_false_alarms"]) for r in bench_rows),
            "v36_total_ledger_g1_candidates": len(v36_ledger),
            "v36_after_g2": sum(1 for c in v36_ledger if c["g2_pass"]),
            "v36_after_g3": sum(1 for c in v36_ledger if c["g2_pass"] and c["g3_pass"]),
            "v36_after_g4": sum(1 for c in v36_ledger if c["g2_pass"] and c["g3_pass"] and c["g4_pass"]),
            "v36_pre_g6_passed_g1_to_g5": sum(1 for c in v36_ledger if c["pre_g6_qualified"]),
            "v36_vetoed_by_g6_sparse": sum(1 for c in v36_ledger if c["pre_g6_qualified"] and not c["g6_pass"]),
            "v36_would_veto_under_v35_dense": sum(1 for c in v36_ledger if c["pre_g6_qualified"] and not c["g6_v35_dense_pass"]),
            "v36_orbital_candidates": sum(1 for c in v36_ledger if c["channel"] in ("T_DIFF", "K_PLANET") and c["qualified_v36_laser"]),
            "automated_qualified_control": v36_q_ctrl,
            "automated_qualified_science": v36_q_sci,
            "comb_v4_automated_candidates": len(comb_cand_rows),
            "verified_eti_detections": 0,
        },
        "upper_limits_300_cells": {
            "n_cells": len(upper_limit_rows),
            "best_overall_star": best_u["star"],
            "best_overall_common_name": best_u["common_name"],
            "best_overall_band": best_u["band_id"],
            "best_overall_10m_w": round(float(best_u["p_beam_10m_w"]), 3),
        },
        "unified_150star_panchromatic_v3_synthesis": {
            "phases": "D079-D085",
            "unique_stars_total": len(unified_150),
            "within_10pc_unique_stars": len(solar_10pc_73),
            "within_10pc_median_limit_kw": round(exact_median_1d(np.asarray(best_10pc, dtype=np.float64)), 4),
            "panchromatic_bridge_stars_total": 8,
            "total_exposures_d079_d085": int(prior_snapshot["prior_v3_total_exposures_count"]) + len(cohort_rows),
            "total_calibration_trials_d079_d085": int(prior_snapshot["prior_v3_calibration_trials_count"]) + n_cal_d085,
            "v2_false_alarms_eliminated_total": int(prior_snapshot["prior_v2_false_alarms_eliminated_total"]) + sum(int(r["v2_accepted_false_alarms"]) for r in bench_rows),
            "verified_eti_detections_total": 0,
        },
        "multimessenger_160system_synthesis": {
            "distinct_stellar_systems_total": len(mm_160),
            "direct_multimessenger_overlap_count": n_ovlp,
            "direct_multimessenger_overlap_stars": [r["system_id"] for r in mm_160 if r["multimessenger_overlap"]],
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
        "schema": "D085_FORENSIC_SPIROU_CASCADE_DIAGNOSIS",
        "pre_g6_count": len(forensic_cands),
        "vetoed_by_g6_sparse": [c for c in forensic_cands if not c["g6_pass"]],
        "post_g6_qualified": [c for c in forensic_cands if c["qualified_v36_laser"]],
        "comb_v4_candidates": comb_cand_rows,
    }
    (res_dir / "FORENSIC_SPIROU_CASCADE_DIAGNOSIS.json").write_text(json.dumps(forensic_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    cal_s = summary["synthetic_calibration_2592_trials"]
    print(
        f"[Stage B DONE] {n_cal_d085} trials (G6_V36 laser={cal_s['g6_v36_sparse_true_laser_pass']*100:.1f}% vs V35={cal_s['g6_v35_dense_true_laser_pass']*100:.1f}%, "
        f"COMB>=3.8s={cal_s['comb_v4_6tooth_ge_3p8sigma_recovery']*100:.1f}% / FPR_1L={cal_s['comb_v4_single_line_fpr']:.3f}), "
        f"V2={summary['false_alarm_cascade']['v2_legacy_false_alarms']} -> preG6={len(forensic_cands)} -> qual={v36_q_ctrl+v36_q_sci} + COMB={len(comb_cand_rows)}, "
        f"150 stars / {len(solar_10pc_73)} <10pc / {len(mm_160)} MM systems ({n_ovlp} overlap).",
        flush=True,
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--from-full-inputs", nargs="?", const=str(DEFAULT_INPUTS_DIR))
    group.add_argument("--from-bounded-inputs", action="store_true")
    args = parser.parse_args()

    cohort_rows = list(csv.DictReader((HERE / "FROZEN_COHORT_D085.csv").open("r", encoding="utf-8")))
    kin_catalog = json.loads((HERE / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))
    excl_verif = json.loads((HERE / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    prior_snapshot = json.loads((HERE / "PRIOR_V3_PHASES_SNAPSHOT.json").read_text(encoding="utf-8"))
    mm_snapshot = json.loads((HERE / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").read_text(encoding="utf-8"))
    bundle_path = HERE / "bounded_inputs" / "d085_bounded_bundle.json.gz"

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
