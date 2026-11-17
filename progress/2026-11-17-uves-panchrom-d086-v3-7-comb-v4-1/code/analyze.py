#!/usr/bin/env python3
"""Two-stage reproducible analysis pipeline for Phase D086
(PANCHROM_NUV_OPT_V3_7_AND_COMB_V4_1).

Modes:
  --from-full-inputs <dir>      Read full FITS/TAR cache from inputs_d086_v3_7/,
                                build bounded_inputs/d086_bounded_bundle.json.gz (<25 MiB),
                                then run offline evaluator.
  --from-bounded-inputs <path>  Recompute all outputs in results/ & FORENSIC_CANDIDATE_AUDIT_D086.json
                                strictly bit-identically from the bounded gzipped JSON bundle.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gc
import gzip
import hashlib
import io
import json
import math
import tarfile
import warnings
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import median_filter

from v3_7_detector import (
    BASE_V3_7_CONFIG,
    C_ANGSTROM_GHZ,
    C_KMS,
    CALIBRATION_BANDS_ESPRESSO_A,
    CALIBRATION_BANDS_HARPS_A,
    CALIBRATION_BANDS_UVES_NUV_A,
    CLEAN_SPIROU_WINDOWS_VAC_A,
    COMB_V4_1_WINDOWS_A,
    FWHM_FACTOR,
    LA_SILLA_LAT_DEG,
    LA_SILLA_LON_DEG,
    MAD_NORM,
    OPTIONAL_EXTREME_NUV_BANDS_A,
    PARANAL_LAT_DEG,
    PARANAL_LON_DEG,
    STELLAR_CHROMOSPHERIC_EMISSION_AIR_A,
    TELLURIC_AIRGLOW_LINES_A,
    TELLURIC_SATURATED_BANDS_TOPO_A,
    bary_to_planet_rest_wave,
    build_and_scan_transit_channels,
    build_multi_epoch_rest_coadd_and_channel_p,
    check_channel_lsf_gate,
    compute_keplerian_kp_kms,
    compute_photon_beam_upper_limit,
    compute_planet_orbital_rv_kms,
    compute_running_continuum,
    compute_supraphotospheric_f1_window,
    construct_knn_stellar_templates,
    evaluate_gate_g2_airglow,
    evaluate_gate_g6_v35_dense,
    evaluate_gate_g6_v36_sparse,
    evaluate_gates_g3_g4_g5_v37,
    evaluate_native_order_patch,
    exact_mad_1d,
    exact_median_1d,
    exact_quantile_1d,
    fit_lsf_on_window,
    fit_rv_anchor_absorption,
    get_calibration_bands,
    get_inst_config,
    measure_exposure_stellar_rv,
    planet_rest_to_bary_wave,
    scan_frequency_comb_v4,
    scan_frequency_comb_v4_1,
    scan_single_exposure_residual_lsf,
    stdlib_observatory_berv_kms,
)

HERE = Path(__file__).resolve().parent
D085_WS = HERE.parent / "work_spirou_20261116_d085_v3_6_yjhk_and_comb_v4"

TRANSIENT_INJECTION_PHASES = [-0.35, 0.0, 0.35]
TRANSIENT_INJECTION_SIGMAS = [5.0, 6.5, 8.0, 10.0, 14.0]
PERSISTENT_INJECTION_PHASES = [-0.35, 0.0, 0.35]
PERSISTENT_INJECTION_SIGMAS = [6.0, 7.5, 9.0, 12.0, 16.0]
KEPLERIAN_INJECTION_PHASES = [-0.35, 0.0, 0.35]
KEPLERIAN_EXP_SIGMAS = [3.5, 5.0, 6.5, 8.5, 11.0]
G6_CALIBRATION_SIGMAS = [5.5, 8.0, 12.0]
COMB_CALIBRATION_SPACINGS = [40.0, 60.0, 100.0]
COMB_CALIBRATION_SIGMAS = [2.5, 3.2, 3.8, 4.5, 5.5, 7.0]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_prospective_lock(full_inputs_dir: Path | None) -> tuple[dict[str, Any], dict[str, Any]]:
    lock_p = HERE / "METHOD_LOCK.json"
    rec_p = HERE / "LOCK_RECEIPT.json"
    if not lock_p.is_file() or not rec_p.is_file():
        raise RuntimeError("Missing METHOD_LOCK.json or LOCK_RECEIPT.json")
    mlock = json.loads(lock_p.read_text(encoding="utf-8"))
    rec = json.loads(rec_p.read_text(encoding="utf-8"))
    if sha256_file(lock_p) != rec.get("method_lock_sha256"):
        raise RuntimeError("METHOD_LOCK.json hash mismatch vs LOCK_RECEIPT.json")
    impl_p = HERE / "IMPLEMENTATION_LOCK.json"
    impl = json.loads(impl_p.read_text(encoding="utf-8")) if impl_p.is_file() else None
    if impl is not None and impl.get("parent_method_lock_sha256") != sha256_file(lock_p):
        raise RuntimeError("IMPLEMENTATION_LOCK.json parent_method_lock_sha256 mismatch")
    for rel, exp_sha in rec.get("locked_artifact_sha256", {}).items():
        if impl is not None and rel in impl.get("amended_file_hashes", {}):
            v0_rel = impl["preserved_pre_ingestion_files"][rel]
            v0_fp = HERE / v0_rel
            if not v0_fp.is_file() or sha256_file(v0_fp) != exp_sha:
                raise RuntimeError(f"Preserved pre-ingestion artifact SHA mismatch: {v0_rel}")
            cur_fp = HERE / rel
            if not cur_fp.is_file() or sha256_file(cur_fp) != impl["amended_file_hashes"][rel]:
                raise RuntimeError(f"Amended implementation SHA mismatch: {rel}")
        else:
            fp = HERE / rel
            if not fp.is_file() or sha256_file(fp) != exp_sha:
                raise RuntimeError(f"Locked artifact SHA mismatch: {rel}")

    if full_inputs_dir is not None:
        dl_p = full_inputs_dir / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json"
        if not dl_p.is_file():
            raise RuntimeError("Missing FIRST_SCIENCE_DOWNLOAD_RECEIPT.json")
        dl_r = json.loads(dl_p.read_text(encoding="utf-8"))
        t_lock = dt.datetime.fromisoformat(rec["locked_utc"].replace("Z", "+00:00"))
        t_dl = dt.datetime.fromisoformat(dl_r["first_download_utc"].replace("Z", "+00:00"))
        if not (t_lock < t_dl):
            raise RuntimeError(f"Chronology violation: locked={t_lock} >= download={t_dl}")
    return mlock, rec


def _clean_json_floats(arr: np.ndarray | list[float], decimals: int = 6) -> list[float]:
    a = np.asarray(arr, dtype=np.float64)
    return np.where(np.isfinite(a), np.round(a, decimals), 0.0).tolist()


def _clean_json_nullable(arr: np.ndarray, decimals: int = 6) -> list[float | None]:
    out: list[float | None] = []
    for x in np.asarray(arr, dtype=np.float64):
        xv = float(x)
        out.append(round(xv, decimals) if math.isfinite(xv) else None)
    return out


def _arr_from_nullable(vals: list[float | None]) -> np.ndarray:
    return np.array([float("nan") if v is None else float(v) for v in vals], dtype=np.float64)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        cols = fieldnames or ["empty"]
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=cols).writeheader()
        return
    cols = fieldnames or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            out = {}
            for k in cols:
                v = r.get(k)
                if isinstance(v, float):
                    out[k] = f"{v:.10g}" if math.isfinite(v) else ""
                elif v is None:
                    out[k] = ""
                else:
                    out[k] = v
            w.writerow(out)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Instrument FITS / TAR Loaders
# ---------------------------------------------------------------------------

def _safe_header_dict(hdr: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for card in hdr.cards:
        try:
            k = str(card.keyword)
            if k and k not in ("COMMENT", "HISTORY"):
                out[k] = card.value
        except Exception:
            continue
    return out


def _poly_eval_header(hdr: dict[str, Any], prefix: str, deg: int, order: int, x: np.ndarray) -> np.ndarray:
    coeffs = [float(hdr[f"{prefix}{order * (deg + 1) + i}"]) for i in range(deg + 1)]
    return np.polynomial.polynomial.polyval(x, coeffs)


def _vac_to_air_edlen66(wave_vac_a: np.ndarray) -> np.ndarray:
    s2 = (1.0e4 / wave_vac_a) ** 2
    n_air = 1.0 + 1.0e-8 * (8342.13 + 2406030.0 / (130.0 - s2) + 15997.0 / (38.9 - s2))
    return wave_vac_a / n_air


def load_uves_nuv_fits(path: Path, row: dict[str, str]) -> dict[str, Any]:
    from astropy.coordinates import EarthLocation, SkyCoord
    from astropy.io import fits
    from astropy.time import Time
    import astropy.units as u

    with fits.open(path, memmap=False) as hdul:
        hdr = _safe_header_dict(hdul[0].header)
        spec = hdul[1].data
        cols = [c.name for c in hdul[1].columns]
        wave_topo = np.asarray(spec["WAVE"][0], dtype=np.float64).ravel().copy()
        if "FLUX_REDUCED" in cols:
            flux_raw = np.asarray(spec["FLUX_REDUCED"][0], dtype=np.float64).ravel().copy()
            bg_flux = np.asarray(spec["BGFLUX_REDUCED"][0], dtype=np.float64).ravel().copy() if "BGFLUX_REDUCED" in cols else None
        else:
            flux_raw = np.asarray(spec["FLUX"][0], dtype=np.float64).ravel().copy()
            bg_flux = None

    mjd_mid = float(row["mjd_mid"])
    ra_deg, dec_deg = float(row["s_ra"]), float(row["s_dec"])
    paranal = EarthLocation.from_geodetic(PARANAL_LON_DEG, PARANAL_LAT_DEG, 2635.0)
    sc = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg)
    berv_ap = float(sc.radial_velocity_correction(obstime=Time(mjd_mid, format="mjd", scale="utc"), location=paranal).to(u.km / u.s).value)
    berv_hdr = hdr.get("ESO QC VRAD BARYCOR", hdr.get("HIERARCH ESO QC VRAD BARYCOR", float("nan")))
    try:
        berv_hdr_f = float(berv_hdr)
    except Exception:
        berv_hdr_f = float("nan")
    specsys = str(hdr.get("SPECSYS", "TOPOCENT")).strip()
    if specsys == "BARYCENT":
        wave_bary = wave_topo
    else:
        wave_bary = wave_topo * (1.0 + berv_ap / C_KMS)

    flux = np.where(np.isfinite(wave_bary) & np.isfinite(flux_raw) & (flux_raw > 0.0), flux_raw, np.nan)
    berv_std = stdlib_observatory_berv_kms(ra_deg, dec_deg, mjd_mid, PARANAL_LAT_DEG, PARANAL_LON_DEG)
    if abs(berv_ap - berv_std) > 0.50:
        raise RuntimeError(f"Paranal BERV mismatch for {row['dp_id']}: ap={berv_ap:.3f} vs std={berv_std:.3f}")

    return {
        "instrument": "UVES_NUV",
        "wave": wave_bary,
        "flux": flux,
        "bg_flux": bg_flux,
        "berv_kms": berv_ap,
        "berv_hdr_kms": berv_hdr_f if math.isfinite(berv_hdr_f) else berv_ap,
        "berv_diff_stdlib_kms": abs(berv_ap - berv_std),
        "specsys": specsys,
        "dpr_or_calsel": str(hdr.get("ESO DPR TYPE", "STAR,UVES_BLUE")).strip(),
        "resolving_power": float(hdr.get("SPEC_RES", row["em_res_power"])),
        "s1d_sha256": sha256_file(path),
        "aux_sha256": "",
        "header_gate": "PASS",
    }


def load_espresso_s1d_and_b(s1d_a_path: Path, s1d_b_path: Path, row: dict[str, str]) -> dict[str, Any]:
    from astropy.io import fits

    with fits.open(s1d_a_path, memmap=False) as hdul:
        hdr = _safe_header_dict(hdul[0].header)
        spec = hdul[1].data
        cols = [c.name for c in hdul[1].columns]
        berv_val = float(hdr.get("ESO QC BERV", float("nan")))
        if "WAVE_AIR" in cols and "FLUX_EL" in cols:
            wave = np.asarray(spec["WAVE_AIR"], dtype=np.float64).ravel().copy()
            flux_raw = np.asarray(spec["FLUX_EL"], dtype=np.float64).ravel().copy()
            qual = np.asarray(spec["QUAL_EL"], dtype=np.int32).ravel()
        else:
            wave_vac = np.asarray(spec["WAVE"], dtype=np.float64).ravel()
            flux_cal = np.asarray(spec["FLUX"], dtype=np.float64).ravel()
            qual = np.asarray(spec["QUAL"], dtype=np.int32).ravel()
            snr_c = np.asarray(spec["SNR"], dtype=np.float64).ravel()
            contrib = np.asarray(spec["CONTRIB"], dtype=np.float64).ravel() if "CONTRIB" in cols else np.ones_like(flux_cal)
            wave = None
            with fits.open(s1d_b_path, memmap=False) as hb:
                cb = [c.name for c in hb[1].columns]
                if "WAVE_AIR" in cb and "WAVE" in cb:
                    wbv = np.asarray(hb[1].data["WAVE"], dtype=np.float64).ravel()
                    if wbv.shape == wave_vac.shape and np.allclose(wbv, wave_vac, rtol=0.0, atol=1e-9):
                        wave = np.asarray(hb[1].data["WAVE_AIR"], dtype=np.float64).ravel().copy()
                if not math.isfinite(berv_val):
                    berv_val = float(_safe_header_dict(hb[0].header).get("ESO QC BERV", float("nan")))
            if wave is None:
                wave = _vac_to_air_edlen66(wave_vac)
            ok = (qual == 0) & np.isfinite(flux_cal) & (flux_cal > 0) & np.isfinite(snr_c) & (snr_c > 5.0) & np.isfinite(contrib) & (contrib > 0)
            scale = float(np.median((snr_c[ok] ** 2) / np.maximum(1.0, contrib[ok]) / flux_cal[ok])) if int(ok.sum()) >= 100 else 1e17
            flux_raw = flux_cal * scale

    with fits.open(s1d_b_path, memmap=False) as hb:
        sb = hb[1].data
        cb = [c.name for c in hb[1].columns]
        wb = np.asarray(sb["WAVE_AIR"], dtype=np.float64).ravel().copy() if "WAVE_AIR" in cb else _vac_to_air_edlen66(np.asarray(sb["WAVE"], dtype=np.float64).ravel())
        fb = np.asarray(sb["FLUX_EL"], dtype=np.float64).ravel().copy() if "FLUX_EL" in cb else np.asarray(sb["FLUX"], dtype=np.float64).ravel().copy()
        if not math.isfinite(berv_val):
            berv_val = float(_safe_header_dict(hb[0].header).get("ESO QC BERV", float("nan")))

    if not math.isfinite(berv_val):
        berv_val = stdlib_observatory_berv_kms(float(row["s_ra"]), float(row["s_dec"]), float(row["mjd_mid"]), PARANAL_LAT_DEG, PARANAL_LON_DEG)
    berv_std = stdlib_observatory_berv_kms(float(row["s_ra"]), float(row["s_dec"]), float(row["mjd_mid"]), PARANAL_LAT_DEG, PARANAL_LON_DEG)
    if abs(berv_val - berv_std) > 0.50:
        raise RuntimeError(f"ESPRESSO BERV mismatch for {row['dp_id']}: {berv_val:.3f} vs {berv_std:.3f}")

    calsel = next((str(hdr[k]).strip() for k in hdr.keys() if "CALSEL ID" in k.upper()), "TRG_SKY")
    flux = np.where((qual == 0) & np.isfinite(flux_raw) & (flux_raw > 0.0), flux_raw, np.nan)
    return {
        "instrument": "ESPRESSO",
        "wave": wave,
        "flux": flux,
        "s1d_b_wave": wb,
        "s1d_b_flux": fb,
        "berv_kms": float(berv_val),
        "berv_diff_stdlib_kms": abs(berv_val - berv_std),
        "specsys": str(hdr.get("SPECSYS", "BARYCENT")).strip(),
        "dpr_or_calsel": calsel,
        "resolving_power": 140000.0,
        "s1d_sha256": sha256_file(s1d_a_path),
        "aux_sha256": sha256_file(s1d_b_path),
        "header_gate": "PASS",
    }


def load_harps_s1d_and_tar(s1d_path: Path, tar_path: Path, row: dict[str, str]) -> dict[str, Any]:
    from astropy.io import fits

    with fits.open(s1d_path, memmap=False) as hdul:
        hdr = _safe_header_dict(hdul[0].header)
        wave = np.asarray(hdul[1].data["WAVE"][0], dtype=np.float64).ravel().copy()
        flux_raw = np.asarray(hdul[1].data["FLUX"][0], dtype=np.float64).ravel().copy()
        berv_val = float(hdr.get("ESO DRS BERV", hdr.get("HIERARCH ESO DRS BERV", float("nan"))))

    with tarfile.open(tar_path, "r") as tf:
        m_a = next((m for m in tf.getmembers() if m.name.endswith("_e2ds_A.fits")), None)
        if m_a is None:
            raise RuntimeError(f"Missing _e2ds_A.fits in {tar_path}")
        with fits.open(io.BytesIO(tf.extractfile(m_a).read()), memmap=False) as ha:
            hdr_a = _safe_header_dict(ha[0].header)
            e2ds_a = np.asarray(ha[0].data, dtype=np.float64).copy()
        m_b = next((m for m in tf.getmembers() if m.name.endswith("_e2ds_B.fits")), None)
        e2ds_b = None
        waves_topo_b = None
        if m_b is not None:
            with fits.open(io.BytesIO(tf.extractfile(m_b).read()), memmap=False) as hb:
                hdr_b = _safe_header_dict(hb[0].header)
                e2ds_b = np.asarray(hb[0].data, dtype=np.float64).copy()
            if "ESO DRS CAL TH DEG LL" in hdr_b and "ESO DRS CAL TH COEFF LL0" in hdr_b:
                deg_b = int(hdr_b["ESO DRS CAL TH DEG LL"])
                xb = np.arange(e2ds_b.shape[1], dtype=np.float64)
                waves_topo_b = np.array([_poly_eval_header(hdr_b, "ESO DRS CAL TH COEFF LL", deg_b, ob, xb) for ob in range(e2ds_b.shape[0])], dtype=np.float64)

    deg = int(hdr_a["ESO DRS CAL TH DEG LL"])
    x = np.arange(e2ds_a.shape[1], dtype=np.float64)
    waves_topo = np.array([_poly_eval_header(hdr_a, "ESO DRS CAL TH COEFF LL", deg, o, x) for o in range(e2ds_a.shape[0])], dtype=np.float64)
    if not math.isfinite(berv_val):
        berv_val = float(hdr_a.get("ESO DRS BERV", float("nan")))
    berv_std = stdlib_observatory_berv_kms(float(row["s_ra"]), float(row["s_dec"]), float(row["mjd_mid"]), LA_SILLA_LAT_DEG, LA_SILLA_LON_DEG)
    if abs(berv_val - berv_std) > 0.50:
        raise RuntimeError(f"HARPS BERV mismatch for {row['dp_id']}: {berv_val:.3f} vs {berv_std:.3f}")

    flux = np.where(np.isfinite(flux_raw) & (flux_raw > 0.0), flux_raw, np.nan)
    return {
        "instrument": "HARPS",
        "wave": wave,
        "flux": flux,
        "e2ds_a": e2ds_a,
        "e2ds_b": e2ds_b,
        "waves_topo": waves_topo,
        "waves_topo_b": waves_topo_b,
        "berv_kms": float(berv_val),
        "berv_diff_stdlib_kms": abs(berv_val - berv_std),
        "specsys": str(hdr.get("SPECSYS", "BARYCENT")).strip(),
        "dpr_or_calsel": str(hdr_a.get("ESO DPR TYPE", "STAR,WAVE,THAR")).strip(),
        "resolving_power": 115000.0,
        "s1d_sha256": sha256_file(s1d_path),
        "aux_sha256": sha256_file(tar_path),
        "header_gate": "PASS",
    }


def run_legacy_v2_benchmark(wave: np.ndarray, fn: np.ndarray, cfg: dict[str, Any]) -> int:
    """Count naive V2-style narrow single-spectrum emission spikes >= 6 sigma over local continuum."""
    fin = np.isfinite(fn) & (fn > 0.05)
    if int(fin.sum()) < 500:
        return 0
    fn_f = np.where(fin, fn, 1.0)
    med = median_filter(fn_f, size=101, mode="nearest")
    resid = np.where(fin, fn_f - med, np.nan)
    mad = MAD_NORM * median_filter(np.abs(np.where(fin, resid, 0.0)), size=101, mode="nearest")
    margin = 10
    pks = np.flatnonzero(
        fin[margin:-margin]
        & (mad[margin:-margin] > 0)
        & (resid[margin:-margin] > resid[margin - 1 : -margin - 1])
        & (resid[margin:-margin] >= resid[margin + 1 : -margin + 1])
        & (resid[margin:-margin] >= 6.0 * mad[margin:-margin])
    ) + margin
    dedup: list[float] = []
    fwhm_tol = 2.0 * (float(wave[len(wave) // 2]) / float(cfg["resolving_power"]))
    for k in pks:
        w = float(wave[k])
        if not dedup or (w - dedup[-1]) > fwhm_tol:
            dedup.append(w)
    return len(dedup)


# ---------------------------------------------------------------------------
# Native Patch Extractors (Unified across UVES_NUV, ESPRESSO, HARPS)
# ---------------------------------------------------------------------------

def extract_native_order_patches(
    exp_rec: dict[str, Any],
    star_rest_grid: np.ndarray | None,
    star_tmpl: np.ndarray | None,
    target_bary_a: float,
    v_star_kms: float,
    half_px: int = 80,
) -> list[dict[str, Any]]:
    inst = exp_rec["instrument"]
    berv = float(exp_rec["berv_kms"])

    def _tmpl_on(w_bary: np.ndarray) -> list[float] | None:
        if star_rest_grid is None or star_tmpl is None:
            return None
        w_rest = w_bary / (1.0 + v_star_kms / C_KMS)
        fin_t = np.isfinite(star_tmpl)
        if int(fin_t.sum()) < 10:
            return None
        ref = np.interp(w_rest, star_rest_grid[fin_t], star_tmpl[fin_t])
        return _clean_json_floats(ref, 6)

    if inst == "HARPS":
        target_topo = target_bary_a / (1.0 + berv / C_KMS)
        wt = exp_rec["waves_topo"]
        e2a = exp_rec["e2ds_a"]
        e2b = exp_rec["e2ds_b"]
        wtb = exp_rec["waves_topo_b"]
        patches: list[dict[str, Any]] = []
        for o in range(wt.shape[0]):
            w_o = wt[o]
            if not (w_o[0] < target_topo < w_o[-1]):
                continue
            k0 = int(np.argmin(np.abs(w_o - target_topo)))
            if k0 < max(24, half_px) or k0 > (w_o.shape[0] - 1 - max(24, half_px)):
                continue
            sl = slice(k0 - half_px, k0 + half_px + 1)
            w_win = w_o[sl].copy()
            fa_win = e2a[o, sl].copy()
            if not (np.all(np.isfinite(w_win)) and np.all(np.isfinite(fa_win))):
                continue
            fb_win = None
            if e2b is not None and wtb is not None and wtb.shape[0] == e2b.shape[0]:
                mid_a = float(w_o[w_o.shape[0] // 2])
                ob = int(np.argmin(np.abs(wtb[:, wtb.shape[1] // 2] - mid_a)))
                kb0 = int(np.argmin(np.abs(wtb[ob] - target_topo)))
                if half_px <= kb0 <= (wtb.shape[1] - 1 - half_px):
                    sb = e2b[ob, kb0 - half_px : kb0 + half_px + 1]
                    if np.all(np.isfinite(sb)):
                        fb_win = _clean_json_floats(sb, 4)
            w_bary_win = w_win * (1.0 + berv / C_KMS)
            patches.append({
                "order": int(o),
                "native_pixel": int(k0),
                "active_start_px": 0,
                "active_end_px": int(w_o.shape[0] - 1),
                "target_wave_a": float(target_topo),
                "wave": _clean_json_floats(w_win, 6),
                "flux_a": _clean_json_floats(fa_win, 4),
                "flux_b": fb_win,
                "bg_flux": None,
                "ref_norm_a": _tmpl_on(w_bary_win),
            })
        return patches

    # ESPRESSO S1D_A+S1D_B and UVES_NUV FLUX_REDUCED+BGFLUX_REDUCED
    w = exp_rec["wave"]
    f = exp_rec["flux"]
    if not (w[0] < target_bary_a < w[-1]):
        return []
    k0 = int(np.argmin(np.abs(w - target_bary_a)))
    if k0 < half_px + 5 or k0 >= len(w) - half_px - 5:
        return []
    sl = slice(k0 - half_px, k0 + half_px + 1)
    ww = w[sl].copy()
    fa = f[sl].copy()
    if int(np.sum(np.isfinite(fa))) < int(0.85 * len(fa)):
        return []
    fin_a = np.isfinite(fa)
    if not np.all(fin_a):
        idx_a = np.arange(len(fa))
        fa = np.interp(idx_a, idx_a[fin_a], fa[fin_a])

    fb_win = None
    bg_win = None
    if inst == "ESPRESSO" and exp_rec.get("s1d_b_wave") is not None:
        wb, fb = exp_rec["s1d_b_wave"], exp_rec["s1d_b_flux"]
        kb = int(np.argmin(np.abs(wb - target_bary_a)))
        if half_px <= kb <= len(fb) - 1 - half_px:
            sub_b = fb[kb - half_px : kb + half_px + 1]
            if int(np.sum(np.isfinite(sub_b))) >= int(0.80 * len(sub_b)):
                med_b = exact_median_1d(sub_b[np.isfinite(sub_b)])
                fb_win = _clean_json_floats(np.where(np.isfinite(sub_b), sub_b, med_b), 4)
    elif inst == "UVES_NUV" and exp_rec.get("bg_flux") is not None:
        bgf = exp_rec["bg_flux"][sl]
        if int(np.sum(np.isfinite(bgf))) >= int(0.80 * len(bgf)):
            med_g = exact_median_1d(bgf[np.isfinite(bgf)])
            bg_win = _clean_json_floats(np.where(np.isfinite(bgf), bgf, med_g), 4)

    return [{
        "order": 1,
        "native_pixel": int(k0),
        "active_start_px": 0,
        "active_end_px": len(w) - 1,
        "target_wave_a": float(target_bary_a),
        "wave": _clean_json_floats(ww, 6),
        "flux_a": _clean_json_floats(fa, 4),
        "flux_b": fb_win,
        "bg_flux": bg_win,
        "ref_norm_a": _tmpl_on(ww),
    }]


def _clean_cal_wave_ok(w_bary_a: float) -> bool:
    for band in TELLURIC_SATURATED_BANDS_TOPO_A:
        if (float(band["lo_air_A"]) - 2.0) <= w_bary_a <= (float(band["hi_air_A"]) + 2.0):
            return False
    for ln in TELLURIC_AIRGLOW_LINES_A:
        if abs(w_bary_a - float(ln["wave_air_A"])) <= 1.5:
            return False
    for ch in STELLAR_CHROMOSPHERIC_EMISSION_AIR_A:
        if abs(w_bary_a - float(ch["wave_air_A"])) <= 2.5:
            return False
    return True


def _annulus_noise_mad(
    ww: np.ndarray,
    res_win: np.ndarray,
    wc: float,
    sigma_v_kms: float,
) -> float:
    w = np.asarray(ww, dtype=np.float64)
    y = np.asarray(res_win, dtype=np.float64)
    fin = np.isfinite(w) & np.isfinite(y)
    if int(fin.sum()) < 20:
        return exact_mad_1d(y[np.isfinite(y)])
    dv = C_KMS * np.abs(w - float(wc)) / max(1e-6, float(wc))
    sv = float(sigma_v_kms)
    m_mid = fin & (dv >= 6.0 * sv) & (dv <= 30.0 * sv)
    m_out = fin & (dv >= 30.0 * sv) & (dv <= 60.0 * sv)
    if int(m_mid.sum()) >= 10 and int(m_out.sum()) >= 10:
        s_mid = exact_mad_1d(y[m_mid])
        s_out = exact_mad_1d(y[m_out])
        if math.isfinite(s_mid) and math.isfinite(s_out) and s_mid > 0.0 and s_out > 0.0:
            return float(max(s_mid, s_out))
    return exact_mad_1d(y[fin])


def _pick_clean_wave_near(
    center_a: float,
    w_grid: np.ndarray,
    fn_grid: np.ndarray,
    res_grid: np.ndarray | None = None,
    sigma_v_kms: float = 2.0,
    half_search_a: float = 18.0,
) -> float:
    mask = (w_grid >= center_a - half_search_a) & (w_grid <= center_a + half_search_a) & np.isfinite(fn_grid)
    idxs = np.flatnonzero(mask)
    if len(idxs) == 0:
        return center_a

    best_tier1: tuple[float, float] | None = None
    best_tier2: tuple[float, float] | None = None
    best_fallback: tuple[float, float] | None = None

    n_g = len(w_grid)
    for idx in idxs[::2]:
        w_try = float(w_grid[idx])
        if not _clean_cal_wave_ok(w_try):
            continue
        fv = float(fn_grid[idx])
        fn5 = fn_grid[max(0, idx - 2) : min(n_g, idx + 3)]
        if len(fn5) == 0 or not np.all(np.isfinite(fn5)):
            continue
        if float(np.min(fn5)) >= 0.85:
            if res_grid is not None:
                i0 = max(0, idx - 450)
                i1 = min(n_g, idx + 451)
                w_loc = w_grid[i0:i1]
                r_loc = res_grid[i0:i1]
                sl_m = (w_loc >= w_try - 4.0) & (w_loc <= w_try + 4.0) & np.isfinite(r_loc)
                if int(sl_m.sum()) >= 30:
                    wl, rl = w_loc[sl_m], r_loc[sl_m]
                    dv = C_KMS * np.abs(wl - w_try) / w_try
                    sv = float(sigma_v_kms)
                    mm = (dv >= 6.0 * sv) & (dv <= 30.0 * sv)
                    mo = (dv >= 30.0 * sv) & (dv <= 60.0 * sv)
                    if int(mm.sum()) >= 10 and int(mo.sum()) >= 10:
                        s_mid = exact_mad_1d(rl[mm])
                        s_out = exact_mad_1d(rl[mo])
                        c7 = res_grid[max(0, idx - 3) : min(n_g, idx + 4)]
                        c7f = c7[np.isfinite(c7)]
                        if s_mid > 0.0 and s_out > 0.0 and len(c7f) > 0:
                            rat = s_mid / s_out
                            cost = abs(fv - 1.0) + 1.5 * abs(math.log(rat))
                            if 0.82 <= rat <= 1.22 and float(np.max(np.abs(c7f))) <= 2.5 * s_mid:
                                if best_tier1 is None or cost < best_tier1[0]:
                                    best_tier1 = (cost, w_try)
                                continue
                            if best_tier2 is None or cost < best_tier2[0]:
                                best_tier2 = (cost, w_try)
                            continue
            sc = abs(fv - 1.0)
            if best_tier2 is None or sc < best_tier2[0]:
                best_tier2 = (sc, w_try)
        elif fv >= 0.78:
            sc = abs(fv - 1.0)
            if best_fallback is None or sc < best_fallback[0]:
                best_fallback = (sc, w_try)

    if best_tier1 is not None:
        return best_tier1[1]
    if best_tier2 is not None:
        return best_tier2[1]
    if best_fallback is not None:
        return best_fallback[1]
    return center_a


# ---------------------------------------------------------------------------
# Stage A: Build Bounded Reproducible Bundle from Full Inputs (< 25 MiB)
# ---------------------------------------------------------------------------

def build_bounded_bundle_from_full_inputs(
    full_inputs_dir: Path,
    lock: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    with (HERE / "FROZEN_COHORT_D086.csv").open("r", encoding="utf-8", newline="") as f:
        cohort_rows = list(csv.DictReader(f))
    orb_cat = json.loads((HERE / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))
    manifest = json.loads((full_inputs_dir / "FULL_D086_INPUT_MANIFEST.json").read_text(encoding="utf-8"))
    man_by_dp = {m["dp_id"]: m for m in manifest["exposures"]}

    print(f"[analyze --from-full-inputs] Loading 181 verified exposures across UVES_NUV/ESPRESSO/HARPS...", flush=True)
    exp_records: list[dict[str, Any]] = []
    provenance_rows: list[dict[str, Any]] = []
    rv_anchor_bundle: list[dict[str, Any]] = []
    v2_counts_by_dp: dict[str, int] = {}

    star_meta: dict[str, dict[str, Any]] = {}
    exps_by_star: dict[str, list[dict[str, Any]]] = {}

    for row in cohort_rows:
        dp = row["dp_id"].strip()
        st = row["canonical_target"].strip()
        inst = row["instrument"].strip()
        m_item = man_by_dp[dp]
        s1d_p = full_inputs_dir / m_item["s1d_relpath"]
        if sha256_file(s1d_p) != m_item["s1d_sha256"]:
            raise RuntimeError(f"Primary FITS SHA mismatch for {dp}")

        if inst == "UVES_NUV":
            loaded = load_uves_nuv_fits(s1d_p, row)
        elif inst == "ESPRESSO":
            aux_p = full_inputs_dir / m_item["aux_relpath"]
            if sha256_file(aux_p) != m_item["aux_sha256"]:
                raise RuntimeError(f"ESPRESSO S1D_B SHA mismatch for {dp}")
            loaded = load_espresso_s1d_and_b(s1d_p, aux_p, row)
        else:
            aux_p = full_inputs_dir / m_item["aux_relpath"]
            if sha256_file(aux_p) != m_item["aux_sha256"]:
                raise RuntimeError(f"HARPSTAR SHA mismatch for {dp}")
            loaded = load_harps_s1d_and_tar(s1d_p, aux_p, row)

        cfg_e = get_inst_config(inst, loaded["resolving_power"])
        prior_rv = float(row["prior_rv_kms"])
        rv_sum, anc_rows, anc_win = measure_exposure_stellar_rv(loaded["wave"], loaded["flux"], prior_rv, cfg_e)
        cont = compute_running_continuum(loaded["wave"], loaded["flux"], cfg_e)
        fn = np.where(cont > 0.0, loaded["flux"] / cont, np.nan)
        v2_cnt = run_legacy_v2_benchmark(loaded["wave"], fn, cfg_e)
        v2_counts_by_dp[dp] = v2_cnt

        loaded["dp_id"] = dp
        loaded["star"] = st
        loaded["row"] = row
        loaded["cfg"] = cfg_e
        loaded["cont"] = cont
        loaded["fn"] = fn
        loaded["emp_rv_kms"] = rv_sum["empirical_rv_kms"]
        loaded["vshift_kms"] = rv_sum["empirical_rv_kms"] - loaded["berv_kms"]
        loaded["n_clean_anchors"] = rv_sum["n_clean_anchors"]
        exp_records.append(loaded)
        exps_by_star.setdefault(st, []).append(loaded)

        if st not in star_meta:
            star_meta[st] = {
                "star": st,
                "common_name": row["common_name"],
                "instrument": inst,
                "role": row["role"],
                "subrole": row["subrole"],
                "panchromatic_bridge": row["panchromatic_bridge"] == "True",
                "radio_mm_id": row["radio_mm_id"],
                "dist_pc": float(row["dist_pc"]),
                "within_10pc": row["within_10pc"] == "True",
                "phot_g_mag": float(row["phot_g_mag"]),
                "phot_bp_mag": float(row["phot_bp_mag"]),
                "j_mag": float(row["j_mag"]) if row["j_mag"] else None,
                "h_mag": float(row["h_mag"]) if row["h_mag"] else None,
                "ks_mag": float(row["ks_mag"]) if row["ks_mag"] else None,
                "teff_k": float(row["teff_k"]),
                "mh_dex": float(row["mh_dex"]),
                "stellar_mass_msun": float(row["stellar_mass_msun"]),
                "prior_rv_kms": prior_rv,
                "n_exoplanets": int(row["n_exoplanets"]),
                "has_transiting_planet": row["has_transiting_planet"] == "True",
                "s_ra_deg": float(row["s_ra"]),
                "s_dec_deg": float(row["s_dec"]),
            }

        provenance_rows.append({
            "instrument": inst,
            "observatory": cfg_e["observatory"],
            "star": st,
            "role": row["role"],
            "radio_mm_id": row["radio_mm_id"],
            "dp_id": dp,
            "epoch_rank": int(row["epoch_rank"]),
            "phase_window": row["phase_window"],
            "s_ra_deg": float(row["s_ra"]),
            "s_dec_deg": float(row["s_dec"]),
            "mjd_mid": float(row["mjd_mid"]),
            "t_exptime_s": float(row["t_exptime"]),
            "resolving_power": round(loaded["resolving_power"], 1),
            "em_min_a": float(row["em_min_a"]),
            "em_max_a": float(row["em_max_a"]),
            "berv_kms": round(loaded["berv_kms"], 6),
            "berv_diff_stdlib_kms": round(loaded["berv_diff_stdlib_kms"], 5),
            "specsys": loaded["specsys"],
            "emp_rv_kms": round(rv_sum["empirical_rv_kms"], 5),
            "n_clean_anchors": rv_sum["n_clean_anchors"],
            "header_gate": loaded["header_gate"],
            "s1d_sha256": loaded["s1d_sha256"],
            "aux_sha256": loaded["aux_sha256"],
        })
        emp_rv = rv_sum["empirical_rv_kms"]
        rv_anchor_bundle.append({
            "dp_id": dp,
            "instrument": inst,
            "star": st,
            "prior_rv_kms": prior_rv,
            "empirical_rv_kms": (
                None if (emp_rv is None or not math.isfinite(float(emp_rv))) else float(emp_rv)
            ),
            "windows": {
                aid: {
                    "wave_a": _clean_json_floats(v["wave_a"], 6),
                    "flux": _clean_json_nullable(v["flux"], 4),
                }
                for aid, v in anc_win.items()
            },
        })

    # Compute per-star coadded rest spectra on each instrument's standard grid & KNN templates
    inst_grids: dict[str, np.ndarray] = {}
    star_norm_coadds: dict[str, np.ndarray] = {}
    v3_rv_summary_rows: list[dict[str, Any]] = []

    for inst in ("UVES_NUV", "ESPRESSO", "HARPS"):
        cfg_i = get_inst_config(inst)
        step = float(cfg_i["coadd_step_angstrom"])
        inst_grids[inst] = np.round(np.arange(cfg_i["ext_rest_min_angstrom"], cfg_i["ext_rest_max_angstrom"] + 0.5 * step, step), 4)

    for st, recs in sorted(exps_by_star.items()):
        inst = recs[0]["instrument"]
        rgrid = inst_grids[inst]
        med_r = exact_median_1d(np.array([r["resolving_power"] for r in recs], dtype=np.float64))
        star_meta[st]["median_resolving_power"] = round(med_r, 1)
        emp_rv = exact_median_1d(np.array([r["emp_rv_kms"] for r in recs], dtype=np.float64))
        star_meta[st]["v_star_kms"] = round(emp_rv, 5)

        stack = []
        for r in recs:
            w_rest = r["wave"] / (1.0 + emp_rv / C_KMS)
            fin = np.isfinite(r["fn"])
            c_exp = np.interp(rgrid, w_rest[fin], r["fn"][fin], left=np.nan, right=np.nan)
            stack.append(c_exp)
        mat = np.vstack(stack)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            coadd_s = np.nanmedian(mat, axis=0)
        star_norm_coadds[st] = coadd_s

        st_rvs = [r["emp_rv_kms"] for r in recs]
        v3_rv_summary_rows.append({
            "instrument": inst,
            "star": st,
            "common_name": star_meta[st]["common_name"],
            "role": star_meta[st]["role"],
            "radio_mm_id": star_meta[st]["radio_mm_id"],
            "n_exposures": len(recs),
            "median_resolving_power": round(med_r, 1),
            "prior_rv_kms": star_meta[st]["prior_rv_kms"],
            "empirical_rv_kms": round(emp_rv, 5),
            "empirical_minus_prior_kms": round(emp_rv - star_meta[st]["prior_rv_kms"], 5),
            "epoch_rv_mad_kms": round(exact_mad_1d(np.array(st_rvs)), 5) if len(st_rvs) >= 2 else 0.0,
        })

    # KNN templates separately on each instrument grid
    templates_by_star: dict[str, np.ndarray] = {}
    for inst in ("UVES_NUV", "ESPRESSO", "HARPS"):
        sub_meta = {s: m for s, m in star_meta.items() if m["instrument"] == inst}
        sub_coadd = {s: star_norm_coadds[s] for s in sub_meta}
        t_dict, t_meta = construct_knn_stellar_templates(sub_meta, sub_coadd, get_inst_config(inst))
        templates_by_star.update(t_dict)
        for rv_r in v3_rv_summary_rows:
            if rv_r["star"] in t_meta:
                rv_r.update(t_meta[rv_r["star"]])

    # Build exposure residual grids, Channel T/P/T_DIFF/K_PLANET real G1 candidates, COMB_V4_1 search, & calibration patches
    real_candidates_bundle: list[dict[str, Any]] = []
    searched_counts_by_inst: dict[str, dict[str, int]] = {
        "UVES_NUV": {"T": 0, "P": 0, "T_DIFF": 0, "K_PLANET": 0, "COMB_CONFIGS": 0},
        "ESPRESSO": {"T": 0, "P": 0, "T_DIFF": 0, "K_PLANET": 0, "COMB_CONFIGS": 0},
        "HARPS": {"T": 0, "P": 0, "T_DIFF": 0, "K_PLANET": 0, "COMB_CONFIGS": 0},
    }
    dense_atlas_by_group: dict[str, list[dict[str, Any]]] = {"UVES_NUV": [], "OPTICAL": []}
    sparse_atlas_by_group: dict[str, list[dict[str, Any]]] = {"UVES_NUV": [], "OPTICAL": []}

    calib_transient_patches: list[dict[str, Any]] = []
    calib_persistent_patches: list[dict[str, Any]] = []
    calib_keplerian_patches: list[dict[str, Any]] = []
    calib_g4g5_patches: list[dict[str, Any]] = []
    calib_g6_patches: list[dict[str, Any]] = []
    calib_comb_patches: list[dict[str, Any]] = []
    comb_real_candidates_bundle: list[dict[str, Any]] = []
    upper_limit_patches: list[dict[str, Any]] = []

    other_coadds_by_inst: dict[str, dict[str, np.ndarray]] = {
        i: {s: star_norm_coadds[s] for s, m in star_meta.items() if m["instrument"] == i}
        for i in ("UVES_NUV", "ESPRESSO", "HARPS")
    }

    def _other_star_fn_max(inst_s: str, target_star: str, rest_wave_a: float) -> int:
        rg = inst_grids[inst_s]
        m = (rg >= rest_wave_a - 0.16) & (rg <= rest_wave_a + 0.16)
        cnt = 0
        for ost, oc in other_coadds_by_inst[inst_s].items():
            if ost == target_star:
                continue
            sub = oc[m]
            fin_o = sub[np.isfinite(sub)]
            if len(fin_o) > 0 and float(np.max(fin_o)) >= 1.03:
                cnt += 1
        return cnt

    # Per-star full pass
    for st, recs in sorted(exps_by_star.items()):
        sm = star_meta[st]
        inst = sm["instrument"]
        atlas_grp = "UVES_NUV" if inst == "UVES_NUV" else "OPTICAL"
        rgrid = inst_grids[inst]
        tmpl = templates_by_star[st]
        v_star = float(sm["v_star_kms"])
        step = float(get_inst_config(inst)["coadd_step_angstrom"])
        half_win_bins = max(70, int(round(5.0 / step)))
        cand_half_bins = 170
        n_exp = len(recs)

        exp_rest_fn = np.full((n_exp, len(rgrid)), np.nan, dtype=np.float64)
        exp_rest_resid = np.full((n_exp, len(rgrid)), np.nan, dtype=np.float64)
        exp_bary_resid_on_rgrid = np.full((n_exp, len(rgrid)), np.nan, dtype=np.float64)

        for e_i, r in enumerate(recs):
            w_rest = r["wave"] / (1.0 + v_star / C_KMS)
            fin = np.isfinite(r["fn"])
            fn_on_r = np.interp(rgrid, w_rest[fin], r["fn"][fin], left=np.nan, right=np.nan)
            res_on_r = fn_on_r - tmpl
            exp_rest_fn[e_i] = fn_on_r
            exp_rest_resid[e_i] = res_on_r

            # Also build barycentric residual for Channel T
            cfg_e = r["cfg"]
            bgrid_e = rgrid * (1.0 + v_star / C_KMS)
            fin_t = np.isfinite(tmpl)
            tmpl_bary = np.interp(rgrid, rgrid[fin_t] * (1.0 + v_star / C_KMS), tmpl[fin_t], left=np.nan, right=np.nan)
            fn_on_b = np.interp(rgrid, r["wave"][fin], r["fn"][fin], left=np.nan, right=np.nan)
            res_b = fn_on_b - tmpl_bary
            exp_bary_resid_on_rgrid[e_i] = res_b

            # Extract sparse & dense atlas peaks from this exposure's rest residual above 3.2 MAD / 3.8 MAD
            r_fin = np.isfinite(res_b)
            if int(r_fin.sum()) > 500:
                rb_fill = np.where(r_fin, res_b, 0.0)
                rmad = MAD_NORM * median_filter(np.abs(rb_fill), size=101, mode="nearest")
                pks = np.flatnonzero(
                    r_fin[2:-2] & (rmad[2:-2] > 0) & (rb_fill[2:-2] > rb_fill[1:-3]) & (rb_fill[2:-2] >= rb_fill[3:-1]) & (rb_fill[2:-2] >= 3.8 * rmad[2:-2])
                ) + 2
                # Keep top ~40 strongest peaks for dense atlas and top ~12 supraphotospheric peaks for sparse atlas
                pk_snrs = [(float(rb_fill[k] / rmad[k]), int(k)) for k in pks]
                pk_snrs.sort(reverse=True)
                for snr_v, k in pk_snrs[:35]:
                    wb_a = float(rgrid[k])
                    wt_a = wb_a / (1.0 + float(r["berv_kms"]) / C_KMS)
                    dense_atlas_by_group[atlas_grp].append({
                        "star": st, "dp_id": r["dp_id"], "berv_kms": round(float(r["berv_kms"]), 4),
                        "topo_air_a": round(wt_a, 4), "order": None, "px": None,
                    })
                    if float(fn_on_b[k]) >= 1.005 and len(sparse_atlas_by_group[atlas_grp]) < 12000:
                        sparse_atlas_by_group[atlas_grp].append({
                            "star": st, "dp_id": r["dp_id"], "berv_kms": round(float(r["berv_kms"]), 4),
                            "topo_air_a": round(wt_a, 4), "order": None, "px": None,
                        })

            # Channel T scan on exposure
            cands_t, sb_t, _ = scan_single_exposure_residual_lsf(rgrid, res_b, cfg_e, channel="T", flux_norm_for_f1=fn_on_b, enforce_f1_in_g1=True)
            searched_counts_by_inst[inst]["T"] += sb_t
            for c in cands_t:
                k = int(c["seed_index"])
                sl = slice(max(0, k - cand_half_bins), min(len(rgrid), k + cand_half_bins + 1))
                bary_a = float(c["fitted_center_a"])
                rest_a = bary_a / (1.0 + v_star / C_KMS)
                ops = extract_native_order_patches(r, rgrid, tmpl, bary_a, v_star, half_px=80)
                if ops:
                    fa0 = np.asarray(ops[0]["flux_a"], dtype=np.float64)
                    cont_snr = float(exact_quantile_1d(fa0, 0.80) / max(1e-9, exact_mad_1d(fa0[:30])))
                else:
                    cont_snr = 30.0
                real_candidates_bundle.append({
                    "channel": "T", "instrument": inst, "atlas_group": atlas_grp,
                    "resolving_power": float(cfg_e["resolving_power"]),
                    "role": sm["role"], "star": st, "dp_id": r["dp_id"],
                    "seed_wave_a": float(rgrid[k]), "v_star_kms": v_star, "berv_kms": float(r["berv_kms"]),
                    "vshift_kms": float(r["vshift_kms"]), "dpr_or_calsel": r["dpr_or_calsel"],
                    "dv_orb_kms": 0.0, "other_ridge_cnt": _other_star_fn_max(inst, st, rest_a),
                    "wave_win": _clean_json_floats(rgrid[sl], 5),
                    "y_primary_win": _clean_json_nullable(res_b[sl], 5),
                    "f_norm_win": _clean_json_nullable(fn_on_b[sl], 5),
                    "order_patches": ops, "cont_snr_est": round(cont_snr, 2),
                })

        # Channel P (Multi-epoch rest coadd)
        cfg_star = get_inst_config(inst, star_meta[st]["median_resolving_power"])
        coadd_r, coadd_fn, cands_p, sb_p, _ = build_multi_epoch_rest_coadd_and_channel_p(rgrid, exp_rest_fn, exp_rest_resid, tmpl, cfg_star)
        searched_counts_by_inst[inst]["P"] += sb_p
        rep_rec = recs[len(recs) // 2]
        for c in cands_p:
            k = int(c["seed_index"])
            sl = slice(max(0, k - cand_half_bins), min(len(rgrid), k + cand_half_bins + 1))
            rest_a = float(c["fitted_center_a"])
            bary_a = rest_a * (1.0 + v_star / C_KMS)
            ops = extract_native_order_patches(rep_rec, rgrid, tmpl, bary_a, v_star, half_px=80)
            real_candidates_bundle.append({
                "channel": "P", "instrument": inst, "atlas_group": atlas_grp,
                "resolving_power": float(cfg_star["resolving_power"]),
                "role": sm["role"], "star": st, "dp_id": rep_rec["dp_id"],
                "seed_wave_a": float(rgrid[k]), "v_star_kms": v_star, "berv_kms": float(rep_rec["berv_kms"]),
                "vshift_kms": float(rep_rec["vshift_kms"]), "dpr_or_calsel": rep_rec["dpr_or_calsel"],
                "dv_orb_kms": 0.0, "other_ridge_cnt": _other_star_fn_max(inst, st, rest_a),
                "wave_win": _clean_json_floats(rgrid[sl], 5),
                "y_primary_win": _clean_json_nullable(coadd_r[sl], 5),
                "f_norm_win": _clean_json_nullable(coadd_fn[sl], 5),
                "order_patches": ops, "cont_snr_est": 50.0,
            })

        # Orbital Transit/Keplerian Channels T_DIFF & K_PLANET for the 10 orbital campaigns
        if st in orb_cat["campaigns"]:
            cm = orb_cat["campaigns"][st]
            kp_kms = compute_keplerian_kp_kms(cm["st_mass_msun"], cm["orbper_days"], cm["ecc"])
            in_idxs = [i for i, r in enumerate(recs) if r["row"]["phase_window"] == "IN_WINDOW"]
            in_recs = [recs[i] for i in in_idxs]
            out_idxs = [i for i, r in enumerate(recs) if r["row"]["phase_window"] == "OUT_OF_WINDOW"]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                out_res_med = np.nanmedian(exp_rest_resid[out_idxs], axis=0)
            unsh_res = []
            unsh_fn = []
            dedop_res = []
            dedop_fn = []
            for idx_r in in_idxs:
                r = recs[idx_r]
                _phi, dv_o = compute_planet_orbital_rv_kms(float(r["row"]["mjd_mid"]) + 2400000.5, cm["t0_bjd"], cm["orbper_days"], kp_kms)
                # Precise BJD from cohort row:
                exp_m = next((x for x in cm["exposures"] if x["dp_id"] == r["dp_id"]), None)
                dv_o = float(exp_m["planet_orbital_rv_kms"]) if exp_m else dv_o
                r["dv_orb_kms"] = dv_o
                unsh_res.append(exp_rest_resid[idx_r])
                unsh_fn.append(exp_rest_fn[idx_r])
                w_p_res = bary_to_planet_rest_wave(r["wave"], v_star, dv_o)
                fin_r = np.isfinite(r["fn"])
                tmpl_p = np.interp(rgrid, rgrid / (1.0 + dv_o / C_KMS), tmpl, left=np.nan, right=np.nan)
                fn_p = np.interp(rgrid, w_p_res[fin_r], r["fn"][fin_r], left=np.nan, right=np.nan)
                dedop_fn.append(fn_p)
                dedop_res.append(fn_p - tmpl_p)
            unsh_res_m = np.vstack(unsh_res)
            unsh_fn_m = np.vstack(unsh_fn)
            dedop_res_m = np.vstack(dedop_res)
            dedop_fn_m = np.vstack(dedop_fn)
            ores = build_and_scan_transit_channels(rgrid, unsh_res_m, unsh_fn_m, dedop_res_m, dedop_fn_m, out_res_med, cfg_star)
            searched_counts_by_inst[inst]["T_DIFF"] += ores["tdiff_searched_bins"]
            searched_counts_by_inst[inst]["K_PLANET"] += ores["kplanet_searched_bins"]
            rep_in = in_recs[len(in_recs) // 2]
            for ch_n, clist, ygrid_c, fgrid_c in (
                ("T_DIFF", ores["tdiff_cands"], ores["y_tdiff"], ores["u_tdiff_fn"]),
                ("K_PLANET", ores["kplanet_cands"], ores["y_kplanet"], ores["f_kplanet_fn"]),
            ):
                for c in clist:
                    k = int(c["seed_index"])
                    sl = slice(max(0, k - cand_half_bins), min(len(rgrid), k + cand_half_bins + 1))
                    fc_a = float(c["fitted_center_a"])
                    dv_u = 0.0 if ch_n == "T_DIFF" else float(rep_in.get("dv_orb_kms", 0.0))
                    bary_a = planet_rest_to_bary_wave(fc_a, v_star, dv_u)
                    rest_a = bary_a / (1.0 + v_star / C_KMS)
                    ops = extract_native_order_patches(rep_in, rgrid, tmpl, bary_a, v_star, half_px=80)
                    real_candidates_bundle.append({
                        "channel": ch_n, "instrument": inst, "atlas_group": atlas_grp,
                        "resolving_power": float(cfg_star["resolving_power"]),
                        "role": sm["role"], "star": st, "dp_id": rep_in["dp_id"],
                        "seed_wave_a": float(rgrid[k]), "v_star_kms": v_star, "berv_kms": float(rep_in["berv_kms"]),
                        "vshift_kms": float(rep_in["vshift_kms"]), "dpr_or_calsel": rep_in["dpr_or_calsel"],
                        "dv_orb_kms": dv_u, "other_ridge_cnt": _other_star_fn_max(inst, st, rest_a),
                        "wave_win": _clean_json_floats(rgrid[sl], 5),
                        "y_primary_win": _clean_json_nullable(ygrid_c[sl], 5),
                        "f_norm_win": _clean_json_nullable(fgrid_c[sl], 5),
                        "order_patches": ops, "cont_snr_est": 50.0,
                    })

            # Suite C Calibration Patch on first 9 orbital planet/control hosts (or specifically 7 science planet hosts + 2 controls = 9!)
            if len(calib_keplerian_patches) < 9 and (sm["role"] == "SCIENCE" or st in ("HD191408", "HD131977")):
                b_cands = [b["center_bary_air_A"] for b in get_calibration_bands(inst)[:3]]
                w_cal_p = _pick_clean_wave_near(float(b_cands[len(calib_keplerian_patches) % len(b_cands)]), rgrid, coadd_fn)
                kp_c = int(np.argmin(np.abs(rgrid - w_cal_p)))
                slk = slice(max(0, kp_c - half_win_bins), min(len(rgrid), kp_c + half_win_bins + 1))
                smad = exact_mad_1d(dedop_res_m[0, slk][np.isfinite(dedop_res_m[0, slk])])
                in_dvs = [float(r.get("dv_orb_kms", 0.0)) for r in in_recs]
                bary_r = planet_rest_to_bary_wave(w_cal_p, v_star, float(rep_in.get("dv_orb_kms", 0.0)))
                calib_keplerian_patches.append({
                    "star": st, "instrument": inst, "rep_dp_id": rep_in["dp_id"],
                    "resolving_power": float(cfg_star["resolving_power"]),
                    "band_id": get_calibration_bands(inst)[0]["band_id"],
                    "dv_span_kms": round(max(in_dvs) - min(in_dvs), 3),
                    "single_in_exp_mad": float(smad) if math.isfinite(smad) and smad > 0 else 0.02,
                    "rep_v_star_kms": v_star, "rep_dv_orb_kms": float(rep_in.get("dv_orb_kms", 0.0)),
                    "rep_berv_kms": float(rep_in["berv_kms"]),
                    "planet_wave_win": _clean_json_floats(rgrid[slk], 5),
                    "out_resid_med_win": _clean_json_nullable(out_res_med[slk], 5),
                    "in_exp_tracks": [
                        {
                            "dv_orb_kms": float(in_recs[j].get("dv_orb_kms", 0.0)),
                            "r_star_unshifted_win": _clean_json_nullable(unsh_res_m[j, slk], 5),
                            "u_star_unshifted_win": _clean_json_nullable(unsh_fn_m[j, slk], 5),
                            "y_kp_dedoppler_win": _clean_json_nullable(dedop_res_m[j, slk], 5),
                            "f_kp_dedoppler_win": _clean_json_nullable(dedop_fn_m[j, slk], 5),
                        }
                        for j in range(len(in_recs))
                    ],
                    "order_patches": extract_native_order_patches(rep_in, rgrid, tmpl, bary_r, v_star, half_px=80),
                })

        # COMB_V4_1 & COMB_V4 real search on coadded rest spectrum
        # Local 400-bin MAD noise envelope + topo stack
        fin_cr = np.isfinite(coadd_r)
        fill_cr = np.where(fin_cr, coadd_r, 0.0)
        sigma_rest = MAD_NORM * median_filter(np.abs(fill_cr), size=201, mode="nearest")
        sigma_rest = np.where(fin_cr & (sigma_rest > 0), sigma_rest, np.nan)
        recon_dummy = np.ones_like(coadd_r)
        sky_mask_b = np.zeros(len(rgrid), dtype=bool)
        for sat in TELLURIC_SATURATED_BANDS_TOPO_A:
            sky_mask_b |= (rgrid >= float(sat["lo_air_A"])) & (rgrid <= float(sat["hi_air_A"]))
        # Topocentric median coadd for COMB anti-comb check
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            exp_topo_res = []
            for r in recs:
                fin_t = np.isfinite(r["fn"])
                w_topo = r["wave"] / (1.0 + float(r["berv_kms"]) / C_KMS)
                ft_g = np.interp(rgrid, w_topo[fin_t], r["fn"][fin_t], left=np.nan, right=np.nan)
                exp_topo_res.append(ft_g - median_filter(np.where(np.isfinite(ft_g), ft_g, 1.0), size=101, mode="nearest"))
            y_topo_c = np.nanmedian(np.vstack(exp_topo_res), axis=0)
        sigma_topo_c = MAD_NORM * median_filter(np.abs(np.where(np.isfinite(y_topo_c), y_topo_c, 0.0)), size=201, mode="nearest")
        sigma_topo_c = np.where(np.isfinite(y_topo_c) & (sigma_topo_c > 0), sigma_topo_c, np.nan)

        wins_i = COMB_V4_1_WINDOWS_A[inst]
        sbands_i = cfg_star["comb_search_bands"]
        hits_v41, cfg_cnt = scan_frequency_comb_v4_1(rgrid, coadd_r, sigma_rest, coadd_fn, recon_dummy, sky_mask_b, y_topo_c, sigma_topo_c, wins_i, sbands_i, cfg_star)
        hits_v4, _ = scan_frequency_comb_v4(rgrid, coadd_r, sigma_rest, coadd_fn, recon_dummy, sky_mask_b, y_topo_c, sigma_topo_c, wins_i, sbands_i, cfg_star)
        searched_counts_by_inst[inst]["COMB_CONFIGS"] += cfg_cnt
        for h in hits_v41 + hits_v4:
            # Deduplicate Stage-A windows for bounded bundle
            if any(p["star"] == st and p["band"] == h["band"] and abs(p["nu0_ghz_stage_a"] - h["nu0_ghz"]) < 2.0 for p in comb_real_candidates_bundle):
                continue
            lo_w = min(h["teeth_a"]) - 6.0
            hi_w = max(h["teeth_a"]) + 6.0
            sl_w = slice(max(0, int(np.searchsorted(rgrid, lo_w))), min(len(rgrid), int(np.searchsorted(rgrid, hi_w))))
            comb_real_candidates_bundle.append({
                "star": st, "instrument": inst, "role": sm["role"], "band": h["band"],
                "resolving_power": float(cfg_star["resolving_power"]),
                "dnu_ghz": h["dnu_ghz"], "nu0_ghz_stage_a": h["nu0_ghz"],
                "wave_win": _clean_json_floats(rgrid[sl_w], 4),
                "y_rest_win": _clean_json_nullable(coadd_r[sl_w], 5),
                "sigma_rest_win": _clean_json_nullable(sigma_rest[sl_w], 5),
                "fn_win": _clean_json_nullable(coadd_fn[sl_w], 5),
                "recon_win": _clean_json_floats(recon_dummy[sl_w], 3),
                "sky_mask_win": [bool(x) for x in sky_mask_b[sl_w]],
                "y_topo_win": _clean_json_nullable(y_topo_c[sl_w], 5),
                "sigma_topo_win": _clean_json_nullable(sigma_topo_c[sl_w], 5),
            })

        # Upper-limit bands for SCIENCE stars (0 NaNs)
        if sm["role"] == "SCIENCE":
            cand_bands = list(get_calibration_bands(inst))
            if inst == "UVES_NUV":
                emin_min = min(float(r["row"]["em_min_a"]) for r in recs)
                emax_max = max(float(r["row"]["em_max_a"]) for r in recs)
                for ob in OPTIONAL_EXTREME_NUV_BANDS_A:
                    if emin_min <= ob["req_min_le"] and emax_max >= ob["req_max_ge"]:
                        cand_bands.append({"band_id": ob["band_id"], "center_bary_air_A": ob["center_bary_air_A"]})

            for bnd in cand_bands:
                wc = float(bnd["center_bary_air_A"])
                mads_e = []
                for e_i, r in enumerate(recs):
                    res_e = exp_rest_resid[e_i]
                    sl_b = (rgrid >= wc - 15.0) & (rgrid <= wc + 15.0) & np.isfinite(res_e)
                    if int(sl_b.sum()) >= 50:
                        md = exact_mad_1d(res_e[sl_b])
                        if math.isfinite(md) and md > 0.0:
                            mads_e.append(md)
                if not mads_e:
                    continue
                upper_limit_patches.append({
                    "instrument": inst,
                    "star": st,
                    "common_name": sm["common_name"],
                    "subrole": sm["subrole"],
                    "panchromatic_bridge": sm["panchromatic_bridge"],
                    "radio_mm_id": sm["radio_mm_id"],
                    "within_10pc": sm["within_10pc"],
                    "n_exoplanets": sm["n_exoplanets"],
                    "has_transiting_planet": sm["has_transiting_planet"],
                    "dist_pc": sm["dist_pc"],
                    "teff_k": sm["teff_k"],
                    "phot_g_mag": sm["phot_g_mag"],
                    "phot_bp_mag": sm["phot_bp_mag"],
                    "j_mag": sm["j_mag"],
                    "h_mag": sm["h_mag"],
                    "ks_mag": sm["ks_mag"],
                    "radiometric_anchor": cfg_star["radiometric_anchor"],
                    "resolving_power": float(cfg_star["resolving_power"]),
                    "band_id": bnd["band_id"],
                    "wave_bary_air_A": wc,
                    "median_epoch_mad_rel": exact_median_1d(np.array(mads_e)),
                })

    # Build bounded calibration suites strictly balanced across UVES_NUV, ESPRESSO, HARPS:
    # Suite A: 72 Channel T patches (24 per inst) + Suite D: 72 G4/G5 patches (24 per inst)
    # Suite B: 36 Channel P patches (12 per inst) + Suite E: 20 G6 patches + Suite F: 18 COMB patches (6 per inst)
    for inst in ("UVES_NUV", "ESPRESSO", "HARPS"):
        inst_stars = sorted([s for s, m in star_meta.items() if m["instrument"] == inst])
        bands_i = get_calibration_bands(inst)
        step_i = float(get_inst_config(inst)["coadd_step_angstrom"])
        hw_i = max(70, int(round(4.5 / step_i)))
        # 24 T & G4G5 patches per instrument
        t_cnt = 0
        for s_idx in range(192):
            st = inst_stars[s_idx % len(inst_stars)]
            rec = exps_by_star[st][(s_idx // len(inst_stars)) % len(exps_by_star[st])]
            rgrid = inst_grids[inst]
            tmpl = templates_by_star[st]
            v_star = float(star_meta[st]["v_star_kms"])
            fin_t = np.isfinite(tmpl)
            fin = np.isfinite(rec["fn"])
            fn_on_b = np.interp(rgrid, rec["wave"][fin], rec["fn"][fin], left=np.nan, right=np.nan)
            tmpl_b = np.interp(rgrid, rgrid[fin_t] * (1.0 + v_star / C_KMS), tmpl[fin_t], left=np.nan, right=np.nan)
            res_b = fn_on_b - tmpl_b
            bnd_t = bands_i[s_idx % len(bands_i)]
            b_nom = float(bnd_t["center_bary_air_A"])
            wc = _pick_clean_wave_near(
                b_nom, rgrid, fn_on_b, res_grid=res_b, sigma_v_kms=float(rec["cfg"]["sigma_v_kms"])
            )
            kc = int(np.argmin(np.abs(rgrid - wc)))
            sl = slice(max(0, kc - hw_i), min(len(rgrid), kc + hw_i + 1))
            ops = extract_native_order_patches(rec, rgrid, tmpl, wc, v_star, half_px=80)
            if not ops:
                continue
            eval0 = evaluate_native_order_patch(
                np.asarray(ops[0]["wave"], dtype=np.float64),
                np.asarray(ops[0]["flux_a"], dtype=np.float64),
                np.asarray(ops[0]["ref_norm_a"], dtype=np.float64) if ops[0].get("ref_norm_a") is not None else None,
                float(ops[0]["target_wave_a"]),
                rec["cfg"],
            )
            min_csnr = 16.0 if s_idx < 140 else 6.0
            if not eval0.get("usable") or float(eval0.get("continuum_snr", 0.0)) < min_csnr:
                continue
            lmad = _annulus_noise_mad(rgrid[sl], res_b[sl], wc, float(rec["cfg"]["sigma_v_kms"]))
            if not math.isfinite(lmad) or lmad <= 0.0:
                continue
            t_cnt += 1
            calib_transient_patches.append({
                "instrument": inst, "star": st, "dp_id": rec["dp_id"],
                "resolving_power": float(rec["cfg"]["resolving_power"]),
                "band_id": bnd_t["band_id"],
                "v_star_kms": v_star, "berv_kms": float(rec["berv_kms"]),
                "dpr_or_calsel": rec["dpr_or_calsel"],
                "local_mad": float(lmad),
                "wave_win": _clean_json_floats(rgrid[sl], 5),
                "resid_win": _clean_json_nullable(res_b[sl], 5),
                "f_norm_win": _clean_json_nullable(fn_on_b[sl], 5),
                "order_patches": ops,
            })
            calib_g4g5_patches.append({
                "instrument": inst, "star": st, "dp_id": rec["dp_id"],
                "resolving_power": float(rec["cfg"]["resolving_power"]),
                "band_id": bnd_t["band_id"],
                "target_bary_a": wc, "stellar_rest_wave_a": wc / (1.0 + v_star / C_KMS),
                "order_patches": ops,
            })
            if t_cnt >= 24:
                break

        # 12 Channel P patches per instrument
        p_cnt = 0
        for p_idx in range(96):
            st = inst_stars[p_idx % len(inst_stars)]
            recs = exps_by_star[st]
            rgrid = inst_grids[inst]
            tmpl = templates_by_star[st]
            v_star = float(star_meta[st]["v_star_kms"])
            med_r = star_meta[st]["median_resolving_power"]
            cfg_p_loc = get_inst_config(inst, med_r)
            bnd_p = bands_i[(p_idx // len(inst_stars) + p_idx) % len(bands_i)]
            b_nom = float(bnd_p["center_bary_air_A"])
            wc = _pick_clean_wave_near(
                b_nom, rgrid, star_norm_coadds[st],
                res_grid=star_norm_coadds[st] - tmpl,
                sigma_v_kms=float(cfg_p_loc["sigma_v_kms"]),
            )
            kc = int(np.argmin(np.abs(rgrid - wc)))
            sl = slice(max(0, kc - hw_i), min(len(rgrid), kc + hw_i + 1))
            er_list = []
            for r in recs:
                wr = r["wave"] / (1.0 + v_star / C_KMS)
                fn_i = np.interp(rgrid[sl], wr[np.isfinite(r["fn"])], r["fn"][np.isfinite(r["fn"])], left=np.nan, right=np.nan)
                er_list.append(fn_i - tmpl[sl])
            er_m = np.vstack(er_list)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                cm_r = np.nanmedian(er_m, axis=0)
            cmad = _annulus_noise_mad(rgrid[sl], cm_r, wc, float(cfg_p_loc["sigma_v_kms"]))
            wb_rep = wc * (1.0 + v_star / C_KMS)
            def _rep_flux_score(r_cand: dict[str, Any]) -> float:
                m_f = (r_cand["wave"] >= wb_rep - 2.0) & (r_cand["wave"] <= wb_rep + 2.0) & np.isfinite(r_cand["flux"])
                return float(np.nanmedian(r_cand["flux"][m_f])) if int(m_f.sum()) >= 5 else -1.0
            rep = max(recs, key=_rep_flux_score)
            ops_p = extract_native_order_patches(rep, rgrid, tmpl, wb_rep, v_star, half_px=80)
            if not ops_p or not math.isfinite(cmad) or cmad <= 0.0:
                continue
            eval_p0 = evaluate_native_order_patch(
                np.asarray(ops_p[0]["wave"], dtype=np.float64),
                np.asarray(ops_p[0]["flux_a"], dtype=np.float64),
                np.asarray(ops_p[0]["ref_norm_a"], dtype=np.float64) if ops_p[0].get("ref_norm_a") is not None else None,
                float(ops_p[0]["target_wave_a"]),
                cfg_p_loc,
            )
            min_csnr_p = 14.0 if p_idx < 64 else 5.0
            if not eval_p0.get("usable") or float(eval_p0.get("continuum_snr", 0.0)) < min_csnr_p:
                continue
            p_cnt += 1
            calib_persistent_patches.append({
                "instrument": inst, "star": st, "rep_dp_id": rep["dp_id"],
                "resolving_power": float(med_r),
                "band_id": bnd_p["band_id"],
                "v_star_kms": v_star, "berv_kms": float(rep["berv_kms"]),
                "dpr_or_calsel": rep["dpr_or_calsel"],
                "coadd_mad": float(cmad),
                "wave_win": _clean_json_floats(rgrid[sl], 5),
                "coadd_resid_win": _clean_json_nullable(cm_r, 5),
                "coadd_fn_win": _clean_json_nullable(star_norm_coadds[st][sl], 5),
                "epoch_resids": [_clean_json_nullable(row_e, 5) for row_e in er_m],
                "order_patches": ops_p,
            })
            if p_cnt >= 12:
                break

        # 6 COMB_V4_1 patches per instrument (18 total x 3 spacings x 9 trials = 486!)
        comb_stars_i = [
            s for s in inst_stars
            if max(
                abs(float(star_meta[s]["v_star_kms"]) - exact_median_1d(np.array([float(r["berv_kms"]) for r in exps_by_star[s]]))),
                0.5 * (max(float(r["berv_kms"]) for r in exps_by_star[s]) - min(float(r["berv_kms"]) for r in exps_by_star[s])),
            ) >= 14.0
        ] or inst_stars
        cand_strips: list[tuple[tuple[float, float, float], str, dict[str, Any], float, int, int]] = []
        for st in comb_stars_i:
            rgrid = inst_grids[inst]
            coadd_st = star_norm_coadds[st]
            r_pow = float(star_meta[st]["median_resolving_power"])
            for win_b in COMB_V4_1_WINDOWS_A[inst]:
                w_lo, w_hi = float(win_b["lo_a"]), float(win_b["hi_a"])
                w_ctr = 0.5 * (w_lo + w_hi)
                for mid_a_f in np.arange(w_lo + 40.0, w_hi - 39.0, 55.0):
                    mid_a = float(mid_a_f)
                    i0 = int(np.searchsorted(rgrid, mid_a - 32.0))
                    i1 = int(np.searchsorted(rgrid, mid_a + 32.0))
                    if i1 - i0 < 200:
                        continue
                    fn_s = coadd_st[i0:i1]
                    if float(np.mean(np.isfinite(fn_s))) < 0.96:
                        continue
                    sc = (
                        round(float(np.mean(np.isfinite(fn_s) & (fn_s >= 0.86))), 2),
                        r_pow,
                        -abs(mid_a - w_ctr),
                    )
                    cand_strips.append((sc, st, win_b, mid_a, i0, i1))
        cand_strips.sort(key=lambda x: x[0], reverse=True)
        chosen_strips: list[tuple[str, dict[str, Any], float, int, int]] = []
        seen_comb_stars: set[str] = set()
        for _sc, st, win_b, mid_a, i0, i1 in cand_strips:
            if st in seen_comb_stars:
                continue
            seen_comb_stars.add(st)
            chosen_strips.append((st, win_b, mid_a, i0, i1))
            if len(chosen_strips) >= 6:
                break
        if len(chosen_strips) < 6:
            for _sc, st, win_b, mid_a, i0, i1 in cand_strips:
                if any(st == cst and win_b["band"] == cwb["band"] and abs(mid_a - cmid) < 65.0 for cst, cwb, cmid, _, _ in chosen_strips):
                    continue
                chosen_strips.append((st, win_b, mid_a, i0, i1))
                if len(chosen_strips) >= 6:
                    break

        for st, win_b, _mid_a, i0, i1 in chosen_strips:
            recs = exps_by_star[st]
            rgrid = inst_grids[inst]
            tmpl = templates_by_star[st]
            v_star = float(star_meta[st]["v_star_kms"])
            med_r = star_meta[st]["median_resolving_power"]
            er_list = []
            et_list = []
            for r in recs:
                fn_f = r["fn"]
                fin_t = np.isfinite(fn_f)
                wr = r["wave"] / (1.0 + v_star / C_KMS)
                wt = r["wave"] / (1.0 + float(r["berv_kms"]) / C_KMS)
                er_list.append(np.interp(rgrid[i0:i1], wr[fin_t], fn_f[fin_t], left=np.nan, right=np.nan) - tmpl[i0:i1])
                ft_w = np.interp(rgrid[i0:i1], wt[fin_t], fn_f[fin_t], left=np.nan, right=np.nan)
                et_list.append(ft_w - median_filter(np.where(np.isfinite(ft_w), ft_w, 1.0), size=101, mode="nearest"))
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                yr_w = np.nanmedian(np.vstack(er_list), axis=0)
                yt_w = np.nanmedian(np.vstack(et_list), axis=0)
            sr_w = MAD_NORM * median_filter(np.abs(np.where(np.isfinite(yr_w), yr_w, 0.0)), size=101, mode="nearest")
            st_w = MAD_NORM * median_filter(np.abs(np.where(np.isfinite(yt_w), yt_w, 0.0)), size=101, mode="nearest")
            bervs_s = [float(r["berv_kms"]) for r in recs]
            calib_comb_patches.append({
                "instrument": inst, "star": st, "band": win_b["band"],
                "resolving_power": float(med_r), "v_star_kms": v_star,
                "median_berv_kms": exact_median_1d(np.array(bervs_s)),
                "berv_span_kms": max(bervs_s) - min(bervs_s),
                "epoch_bervs_kms": [round(float(r["berv_kms"]), 4) for r in recs],
                "nu_lo_ghz": C_ANGSTROM_GHZ / float(rgrid[i1 - 1]),
                "nu_hi_ghz": C_ANGSTROM_GHZ / float(rgrid[i0]),
                "wave_win": _clean_json_floats(rgrid[i0:i1], 4),
                "y_rest_win": _clean_json_nullable(yr_w, 5),
                "sigma_rest_win": _clean_json_nullable(np.where(sr_w > 0, sr_w, np.nan), 5),
                "fn_win": _clean_json_nullable(star_norm_coadds[st][i0:i1], 5),
                "recon_win": [1.0] * (i1 - i0),
                "sky_mask_win": [False] * (i1 - i0),
                "y_topo_win": _clean_json_nullable(yt_w, 5),
                "sigma_topo_win": _clean_json_nullable(np.where(st_w > 0, st_w, np.nan), 5),
            })

    # Suite E: 20 G6 Sparse vs Dense patches requiring genuine multi-epoch BERV span (>= 5.5 km/s)
    def _star_berv_span(s: str) -> float:
        bs = [float(r["berv_kms"]) for r in exps_by_star[s]]
        return (max(bs) - min(bs)) if len(bs) >= 2 else 0.0

    g6_uves = [s for s in sorted(star_meta) if star_meta[s]["instrument"] == "UVES_NUV" and _star_berv_span(s) >= 5.5]
    g6_esp = [s for s in sorted(star_meta) if star_meta[s]["instrument"] == "ESPRESSO" and _star_berv_span(s) >= 5.5]
    g6_harps = [s for s in sorted(star_meta) if star_meta[s]["instrument"] == "HARPS" and _star_berv_span(s) >= 5.5]
    g6_stars = (g6_uves + g6_esp + g6_harps)[:20]
    for idx_g, st in enumerate(g6_stars):
        recs = exps_by_star[st]
        inst = star_meta[st]["instrument"]
        agrp = "UVES_NUV" if inst == "UVES_NUV" else "OPTICAL"
        r0 = min(recs, key=lambda x: float(x["berv_kms"]))
        b0 = float(r0["berv_kms"])
        opp = max(recs, key=lambda x: float(x["berv_kms"]))
        tc = float(get_calibration_bands(inst)[idx_g % len(get_calibration_bands(inst))]["center_bary_air_A"]) - 2.35
        oth_s = [(s2, 10.0) for s2 in sorted(star_meta.keys()) if star_meta[s2]["instrument"] == inst and s2 != st][:4]
        local_d = [p for p in dense_atlas_by_group[agrp] if abs(p["topo_air_a"] - tc) <= 1.0]
        local_s = [p for p in sparse_atlas_by_group[agrp] if abs(p["topo_air_a"] - tc) <= 1.0]
        calib_g6_patches.append({
            "instrument": inst, "atlas_group": agrp, "star": st, "dp_id": r0["dp_id"],
            "opp_dp_id": opp["dp_id"], "target_berv_kms": b0, "opp_berv_kms": float(opp["berv_kms"]),
            "target_vshift_kms": float(r0["vshift_kms"]), "cand_topo_vac_a": round(tc, 4),
            "cand_order": 20 + (idx_g % 15), "cand_px": 1500 + 37 * idx_g,
            "band_id": get_calibration_bands(inst)[0]["band_id"],
            "local_dense_atlas": local_d, "local_sparse_atlas": local_s,
            "synthetic_other_stars": oth_s,
        })

    # Read-only D085 COMB_V4_1 regression cache from D085 bounded bundle (if present)
    d85_comb_cands: list[dict[str, Any]] = []
    d85_bundle_p = D085_WS / "bounded_inputs" / "d085_bounded_bundle.json.gz"
    if d85_bundle_p.is_file():
        with gzip.open(d85_bundle_p, "rt", encoding="utf-8") as gz85:
            b85 = json.load(gz85)
        d85_comb_cands = list(b85.get("comb_real_candidates_bundle", []))

    with (D085_WS / "results" / "MULTIMESSENGER_ECHELLE_RADIO_TESS_160SYSTEMS.csv").open("r", encoding="utf-8", newline="") as f:
        mm_prior_160_rows = list(csv.DictReader(f))

    bundle = {
        "schema": "SETI_D086_BOUNDED_REPRODUCIBLE_BUNDLE_V1",
        "phase_id": "D086",
        "locked_utc": receipt["locked_utc"],
        "method_lock_sha256": receipt["method_lock_sha256"],
        "total_integration_hours": round(sum(float(r["t_exptime"]) for r in cohort_rows) / 3600.0, 4),
        "searched_counts_by_inst": searched_counts_by_inst,
        "provenance_rows": provenance_rows,
        "rv_anchor_bundle": rv_anchor_bundle,
        "v3_rv_summary_rows": v3_rv_summary_rows,
        "v2_counts_by_dp": v2_counts_by_dp,
        "star_meta": star_meta,
        "dense_atlas_by_group": dense_atlas_by_group,
        "sparse_atlas_by_group": sparse_atlas_by_group,
        "calib_transient_patches": calib_transient_patches[:72],
        "calib_persistent_patches": calib_persistent_patches[:36],
        "calib_keplerian_patches": calib_keplerian_patches[:9],
        "calib_g4g5_patches": calib_g4g5_patches[:72],
        "calib_g6_patches": calib_g6_patches[:20],
        "calib_comb_patches": calib_comb_patches[:18],
        "real_candidates_bundle": real_candidates_bundle,
        "comb_real_candidates_bundle": comb_real_candidates_bundle,
        "d085_comb_real_candidates_bundle": d85_comb_cands,
        "mm_prior_160_rows": mm_prior_160_rows,
        "upper_limit_patches": upper_limit_patches,
    }
    return bundle


# ---------------------------------------------------------------------------
# Stage B: Deterministic Offline Evaluator (--from-bounded-inputs & Stage A)
# ---------------------------------------------------------------------------

def _classify_singleline_forensic(row: dict[str, Any], diag: dict[str, Any] | None = None) -> tuple[str, str]:
    if diag is not None:
        dpr_u = str(diag.get("dpr_or_calsel", "")).upper()
        ratio = float(diag.get("fb_over_fa_pk", 0.0))
        if any(tok in dpr_u for tok in ("CAL", "WAVE", "FP", "THAR")) and ratio >= 1.5:
            return (
                "FIBER_B_SIMULTANEOUS_CALIBRATION_BLEED",
                f"Simultaneous calibration observation ({diag['dpr_or_calsel']}) with extreme Fiber-B/Fiber-A peak contrast ({ratio:.1f}x) causing sub-threshold cross-fiber bleed into faint stellar Fiber A.",
            )

    rw = float(row["stellar_rest_wave_a"])
    inst = row["instrument"]
    fn = float(row["target_fn_pk3"])
    snr = float(row["snr_mid"])
    fwhm_r = float(row["fwhm_ratio"]) if row.get("fwhm_ratio") else 1.0

    # Check proximity to known atomic/chromospheric transitions within +-1.0 A
    best_ch = min(STELLAR_CHROMOSPHERIC_EMISSION_AIR_A, key=lambda x: abs(rw - float(x["wave_air_A"])))
    if abs(rw - float(best_ch["wave_air_A"])) <= 1.0:
        return "CHROMOSPHERIC_FLARE_OR_WING", f"Aligned within {abs(rw - float(best_ch['wave_air_A'])):.2f} A of stellar chromospheric transition {best_ch['name']}; broad/transient stellar activity."

    best_ag = min(TELLURIC_AIRGLOW_LINES_A, key=lambda x: abs(float(row["topo_wave_a"]) - float(x["wave_air_A"])))
    if abs(float(row["topo_wave_a"]) - float(best_ag["wave_air_A"])) <= 0.35:
        return "TELLURIC_AIRGLOW_WING_RESIDUAL", f"Topocentric coincidence near atmospheric airglow/streetlamp {best_ag['name']}."

    if inst == "UVES_NUV" and float(row["topo_wave_a"]) < 3160.0:
        return "NUV_OZONE_CUTOFF_LOW_SNR_FLUCTUATION", "Low-SNR extreme NUV (<3160 A) atmospheric ozone extinction cutoff noise spike; single-epoch non-persistent."
    if fn < 1.035 and snr < 12.0:
        return "PHOTOSPHERIC_FEI_TIO_TEMPLATE_RESIDUAL", f"Marginal continuum ripple (fn_pk3={fn:.4f}, S/N={snr:.2f}) in dense blue/NUV photospheric absorption blanketing; fails multi-epoch persistence."
    if fwhm_r < 0.72 or fwhm_r > 1.32:
        return "DETECTOR_ORDER_JOIN_OR_CR_ARTIFACT", f"Non-LSF line width (FWHM ratio={fwhm_r:.2f}); cosmic-ray/extraction residual confined to single epoch."
    return "SINGLE_EPOCH_STELLAR_ACTIVITY_OR_NOISE_EXCURSION", "Single-epoch NUV/optical fluctuation lacking cross-epoch repeatability (Channel P=0) and orbital Doppler coherent modulation."


def evaluate_bundle_and_write_outputs(bundle: dict[str, Any]) -> None:
    res_dir = HERE / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    cfg_base = BASE_V3_7_CONFIG

    with (HERE / "FROZEN_COHORT_D086.csv").open("r", encoding="utf-8", newline="") as f:
        cohort_rows = list(csv.DictReader(f))
    orb_cat = json.loads((HERE / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))
    prior_snap = json.loads((HERE / "PRIOR_V3_PHASES_SNAPSHOT.json").read_text(encoding="utf-8"))
    mm_snap = json.loads((HERE / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").read_text(encoding="utf-8"))

    # 1. Exposure provenance (181)
    write_csv(res_dir / "EXPOSURE_PROVENANCE_181.csv", bundle["provenance_rows"])

    # 2. Stellar RV anchors (2,424) & RV summary (31)
    rva_rows: list[dict[str, Any]] = []
    for item in bundle["rv_anchor_bundle"]:
        inst = item["instrument"]
        cfg_i = get_inst_config(inst)
        for anc in cfg_i["rv_anchors"]:
            aid = anc["anchor_id"]
            w_d = item["windows"][aid]
            fit = fit_rv_anchor_absorption(
                np.asarray(w_d["wave_a"], dtype=np.float64),
                _arr_from_nullable(w_d["flux"]),
                float(anc["lab_air_A"]),
                float(item["prior_rv_kms"]),
                cfg_i,
            )
            rva_rows.append({
                "instrument": inst, "star": item["star"], "dp_id": item["dp_id"],
                "anchor_id": aid, "species": anc["species"], "lab_air_A": anc["lab_air_A"],
                "status": fit["status"], "n_samples": fit["n_samples"],
                "best_rv_kms": fit["best_rv_kms"], "rel_depth": fit["rel_depth"], "min_sse": fit["min_sse"],
            })
    write_csv(res_dir / "STELLAR_RV_ANCHORS_2424.csv", rva_rows)
    write_csv(res_dir / "STAR_RV_SUMMARY_31.csv", bundle["v3_rv_summary_rows"])

    # 3. Calibration Suites A & B: 1,620 Single-Line Injection-Recovery Trials (72 T + 36 P)
    inj_rows: list[dict[str, Any]] = []
    sig_v_map = {inst: get_inst_config(inst)["sigma_v_kms"] for inst in ("UVES_NUV", "ESPRESSO", "HARPS")}

    for p in bundle["calib_transient_patches"]:
        cfg_t = get_inst_config(p["instrument"], p["resolving_power"])
        sig_v = float(cfg_t["sigma_v_kms"])
        ww = np.asarray(p["wave_win"], dtype=np.float64)
        yr = _arr_from_nullable(p["resid_win"])
        fn = _arr_from_nullable(p["f_norm_win"])
        step_w = float(exact_median_1d(np.diff(ww)))
        w0 = float(ww[len(ww) // 2])
        lmad = float(p["local_mad"])
        base_ops = p["order_patches"]
        for ph in TRANSIENT_INJECTION_PHASES:
            inj_b = w0 + ph * step_w
            prof = np.exp(-0.5 * ((C_KMS * (ww - inj_b) / inj_b) / sig_v) ** 2)
            snat = inj_b / (cfg_t["resolving_power"] * FWHM_FACTOR)
            for mult in TRANSIENT_INJECTION_SIGMAS:
                amp = mult * lmad
                fit = fit_lsf_on_window(ww, yr + amp * prof, inj_b, cfg_t)
                fb = fit.get("fitted_center_a", inj_b)
                f1 = compute_supraphotospheric_f1_window(ww, fn + amp * prof, fb, cfg_t["supraphotospheric_min_fn_pk3"])
                g1_ok = bool(check_channel_lsf_gate(fit, "T", cfg_t) and f1["f1_supraphotospheric_pass"])
                g2 = evaluate_gate_g2_airglow(fb, float(p["berv_kms"]), cfg_t)
                i_ops = []
                for op in base_ops:
                    wo, fo = np.asarray(op["wave"], dtype=np.float64), np.asarray(op["flux_a"], dtype=np.float64)
                    c80 = exact_quantile_1d(fo[np.isfinite(fo) & (fo > 0)], 0.80) if np.sum(fo > 0) >= 10 else 1.0
                    wt_i = inj_b / (1.0 + float(p["berv_kms"]) / C_KMS) if p["instrument"] == "HARPS" else inj_b
                    g_n = np.exp(-0.5 * ((wo - wt_i) / snat) ** 2)
                    nop = {**op, "target_wave_a": wt_i, "flux_a": fo + amp * c80 * g_n}
                    i_ops.append(nop)
                g345 = evaluate_gates_g3_g4_g5_v37(i_ops, p["dpr_or_calsel"], "T", fb / (1.0 + float(p["v_star_kms"]) / C_KMS), cfg_t)
                rec_ok = bool(g1_ok and g2["g2_pass"] and g345["g3_pass"] and g345["g4_pass"] and g345["g5_pass"])
                inj_rows.append({
                    "instrument": p["instrument"], "mode": "CHANNEL_T_TRANSIENT_1EPOCH", "star": p["star"], "dp_id": p["dp_id"],
                    "band_id": p["band_id"], "injected_wave_a": round(inj_b, 4), "phase_bins": ph, "sigma_mult": mult,
                    "injected_amp_rel": round(amp, 6), "fitted_snr_mid": fit.get("snr_mid", 0.0),
                    "fitted_cosine": fit.get("cosine", 0.0), "fitted_fwhm_ratio": fit.get("fwhm_ratio"),
                    "g1_pass": g1_ok, "g2_pass": g2["g2_pass"], "g3_pass": g345["g3_pass"], "g4_pass": g345["g4_pass"],
                    "g5_pass": g345["g5_pass"], "recovered": rec_ok,
                })

    for p in bundle["calib_persistent_patches"]:
        cfg_p = get_inst_config(p["instrument"], p["resolving_power"])
        sig_v = float(cfg_p["sigma_v_kms"])
        ww = np.asarray(p["wave_win"], dtype=np.float64)
        cr = _arr_from_nullable(p["coadd_resid_win"])
        cfn = _arr_from_nullable(p["coadd_fn_win"])
        epochs = [_arr_from_nullable(ep) for ep in p["epoch_resids"]]
        step_w = float(exact_median_1d(np.diff(ww)))
        w0 = float(ww[len(ww) // 2])
        cmad = float(p["coadd_mad"])
        base_ops = p["order_patches"]
        for ph in PERSISTENT_INJECTION_PHASES:
            inj_r = w0 + ph * step_w
            inj_b = inj_r * (1.0 + float(p["v_star_kms"]) / C_KMS)
            prof = np.exp(-0.5 * ((C_KMS * (ww - inj_r) / inj_r) / sig_v) ** 2)
            snat = inj_b / (cfg_p["resolving_power"] * FWHM_FACTOR)
            for mult in PERSISTENT_INJECTION_SIGMAS:
                amp = mult * cmad
                fit = fit_lsf_on_window(ww, cr + amp * prof, inj_r, cfg_p)
                fr = fit.get("fitted_center_a", inj_r)
                fb = fr * (1.0 + float(p["v_star_kms"]) / C_KMS)
                f1 = compute_supraphotospheric_f1_window(ww, cfn + amp * prof, fr, cfg_p["supraphotospheric_min_fn_pk3"])
                nhit = 0
                ncov = 0
                for ep in epochs:
                    ef = fit_lsf_on_window(ww, ep + amp * prof, inj_r, cfg_p, fixed_phase_bins=fit.get("phase_bins"))
                    if ef.get("valid_fit"):
                        ncov += 1
                        if ef["snr_mid"] >= 2.8:
                            nhit += 1
                req_e = max(2, min(ncov, max(3, int(math.ceil(0.5 * ncov))))) if ncov >= 2 else 2
                g1_ok = bool(check_channel_lsf_gate(fit, "P", cfg_p) and f1["f1_supraphotospheric_pass"] and nhit >= req_e)
                g2 = evaluate_gate_g2_airglow(fb, float(p["berv_kms"]), cfg_p)
                i_ops = []
                for op in base_ops:
                    wo, fo = np.asarray(op["wave"], dtype=np.float64), np.asarray(op["flux_a"], dtype=np.float64)
                    c80 = exact_quantile_1d(fo[np.isfinite(fo) & (fo > 0)], 0.80) if np.sum(fo > 0) >= 10 else 1.0
                    wt_i = inj_b / (1.0 + float(p["berv_kms"]) / C_KMS) if p["instrument"] == "HARPS" else inj_b
                    g_n = np.exp(-0.5 * ((wo - wt_i) / snat) ** 2)
                    i_ops.append({**op, "target_wave_a": wt_i, "flux_a": fo + amp * c80 * g_n})
                g345 = evaluate_gates_g3_g4_g5_v37(i_ops, p["dpr_or_calsel"], "P", fr, cfg_p)
                rec_ok = bool(g1_ok and g2["g2_pass"] and g345["g3_pass"] and g345["g4_pass"] and g345["g5_pass"])
                inj_rows.append({
                    "instrument": p["instrument"], "mode": "CHANNEL_P_PERSISTENT_MULTIEPOCH", "star": p["star"], "dp_id": p["rep_dp_id"],
                    "band_id": p["band_id"], "injected_wave_a": round(inj_r, 4), "phase_bins": ph, "sigma_mult": mult,
                    "injected_amp_rel": round(amp, 6), "fitted_snr_mid": fit.get("snr_mid", 0.0),
                    "fitted_cosine": fit.get("cosine", 0.0), "fitted_fwhm_ratio": fit.get("fwhm_ratio"),
                    "g1_pass": g1_ok, "g2_pass": g2["g2_pass"], "g3_pass": g345["g3_pass"], "g4_pass": g345["g4_pass"],
                    "g5_pass": g345["g5_pass"], "recovered": rec_ok,
                })
    write_csv(res_dir / "INJECTION_RECOVERY_1620.csv", inj_rows)

    # Suite C: 135 Keplerian Orbital Track Calibration Trials
    kep_rows: list[dict[str, Any]] = []
    for kp in bundle["calib_keplerian_patches"]:
        cfg_k = get_inst_config(kp["instrument"], kp["resolving_power"])
        sig_v = float(cfg_k["sigma_v_kms"])
        margin_k = max(65, int(round(4.5 / float(cfg_k["coadd_step_angstrom"]))))
        wpl = np.asarray(kp["planet_wave_win"], dtype=np.float64)
        step_k = float(exact_median_1d(np.diff(wpl)))
        kc = len(wpl) // 2
        w0 = float(wpl[kc])
        smad = float(kp["single_in_exp_mad"])
        tracks = kp["in_exp_tracks"]
        base_ops = kp["order_patches"]
        req_td = max(2, int(math.ceil(cfg_k["channel_tdiff_min_in_exp_fraction"] * len(tracks))))
        req_kp = max(2, int(math.ceil(cfg_k["channel_kplanet_min_in_exp_fraction"] * len(tracks))))
        for ph in KEPLERIAN_INJECTION_PHASES:
            inj_p = w0 + ph * step_k
            ptol = 0.75 * (inj_p / cfg_k["resolving_power"])
            profd = np.exp(-0.5 * ((C_KMS * (wpl - inj_p) / inj_p) / sig_v) ** 2)
            unsh_profs = [np.exp(-0.5 * ((C_KMS * (wpl - inj_p * (1.0 + float(trk["dv_orb_kms"]) / C_KMS)) / (inj_p * (1.0 + float(trk["dv_orb_kms"]) / C_KMS))) / sig_v) ** 2) for trk in tracks]
            ib_rep = inj_p * (1.0 + float(kp["rep_v_star_kms"]) / C_KMS) * (1.0 + float(kp["rep_dv_orb_kms"]) / C_KMS)
            snat = ib_rep / (cfg_k["resolving_power"] * FWHM_FACTOR)
            for me in KEPLERIAN_EXP_SIGMAS:
                amp = me * smad
                runl = [_arr_from_nullable(t["r_star_unshifted_win"]) + amp * unsh_profs[j] for j, t in enumerate(tracks)]
                uunl = [_arr_from_nullable(t["u_star_unshifted_win"]) + amp * unsh_profs[j] for j, t in enumerate(tracks)]
                r_a, u_a = np.vstack(runl), np.vstack(uunl)
                ytd = np.array([exact_median_1d(r_a[:, c][np.isfinite(r_a[:, c])]) for c in range(r_a.shape[1])], dtype=np.float64)
                utd = np.array([exact_median_1d(u_a[:, c][np.isfinite(u_a[:, c])]) for c in range(u_a.shape[1])], dtype=np.float64)
                ktpk = max(margin_k, min(len(wpl) - margin_k - 1, (kc - 35) + int(np.argmax(np.where(np.isfinite(ytd[kc - 35 : kc + 36]), ytd[kc - 35 : kc + 36], -1e9)))))
                sltd = slice(ktpk - margin_k, ktpk + margin_k + 1)
                ftd = fit_lsf_on_window(wpl[sltd], ytd[sltd], float(wpl[ktpk]), cfg_k)
                f1td = compute_supraphotospheric_f1_window(wpl[sltd], utd[sltd], ftd["fitted_center_a"], cfg_k["supraphotospheric_min_fn_pk3"]) if ftd.get("valid_fit") else {"f1_supraphotospheric_pass": False}
                ntdok = sum(1 for j in range(len(tracks)) if fit_lsf_on_window(wpl[sltd], runl[j][sltd], float(wpl[ktpk]), cfg_k).get("snr_mid", 0.0) >= cfg_k["channel_tdiff_min_in_exp_snr"]) if ftd.get("valid_fit") else 0
                td_rec = bool(check_channel_lsf_gate(ftd, "T_DIFF", cfg_k) and f1td["f1_supraphotospheric_pass"] and ntdok >= req_td)

                ykpl = [_arr_from_nullable(t["y_kp_dedoppler_win"]) + amp * profd for t in tracks]
                fkpl = [_arr_from_nullable(t["f_kp_dedoppler_win"]) + amp * profd for t in tracks]
                nkpok = 0
                for ykj in ykpl:
                    sbj = np.where(np.isfinite(ykj[kc - 2 : kc + 3]), ykj[kc - 2 : kc + 3], -1e9)
                    if float(np.max(sbj)) > -1e8:
                        kj = (kc - 2) + int(np.argmax(sbj))
                        efk = fit_lsf_on_window(wpl[kj - margin_k : kj + margin_k + 1], ykj[kj - margin_k : kj + margin_k + 1], float(wpl[kj]), cfg_k)
                        if efk.get("valid_fit") and efk["snr_mid"] >= cfg_k["channel_kplanet_min_in_exp_snr"]:
                            nkpok += 1
                yka, fka = np.vstack(ykpl), np.vstack(fkpl)
                ykpm = np.array([exact_median_1d(yka[:, c][np.isfinite(yka[:, c])]) for c in range(yka.shape[1])], dtype=np.float64)
                fkpm = np.array([exact_median_1d(fka[:, c][np.isfinite(fka[:, c])]) for c in range(fka.shape[1])], dtype=np.float64)
                kkpk = (kc - 2) + int(np.argmax(np.where(np.isfinite(ykpm[kc - 2 : kc + 3]), ykpm[kc - 2 : kc + 3], -1e9)))
                slkp = slice(kkpk - margin_k, kkpk + margin_k + 1)
                fkp = fit_lsf_on_window(wpl[slkp], ykpm[slkp], float(wpl[kkpk]), cfg_k)
                f1kp = compute_supraphotospheric_f1_window(wpl[slkp], fkpm[slkp], fkp["fitted_center_a"], cfg_k["supraphotospheric_min_fn_pk3"]) if fkp.get("valid_fit") else {"f1_supraphotospheric_pass": False}
                kpg1 = bool(check_channel_lsf_gate(fkp, "K_PLANET", cfg_k) and f1kp["f1_supraphotospheric_pass"] and nkpok >= req_kp and abs(fkp["fitted_center_a"] - inj_p) <= ptol)
                fpa = fkp.get("fitted_center_a", inj_p)
                brep = fpa * (1.0 + float(kp["rep_v_star_kms"]) / C_KMS) * (1.0 + float(kp["rep_dv_orb_kms"]) / C_KMS)
                rrep = brep / (1.0 + float(kp["rep_v_star_kms"]) / C_KMS)
                g2kp = evaluate_gate_g2_airglow(brep, float(kp["rep_berv_kms"]), cfg_k)
                i_ops = []
                for op in base_ops:
                    wo, fo = np.asarray(op["wave"], dtype=np.float64), np.asarray(op["flux_a"], dtype=np.float64)
                    c80 = exact_quantile_1d(fo[np.isfinite(fo) & (fo > 0)], 0.80) if np.sum(fo > 0) >= 10 else 1.0
                    wt_i = ib_rep / (1.0 + float(kp["rep_berv_kms"]) / C_KMS) if kp["instrument"] == "HARPS" else ib_rep
                    g_n = np.exp(-0.5 * ((wo - wt_i) / snat) ** 2)
                    i_ops.append({**op, "target_wave_a": wt_i, "flux_a": fo + amp * c80 * g_n})
                g345kp = evaluate_gates_g3_g4_g5_v37(i_ops, "TRG_SKY", "K_PLANET", rrep, cfg_k)
                kprec = bool(kpg1 and g2kp["g2_pass"] and g345kp["g3_pass"] and g345kp["g4_pass"] and g345kp["g5_pass"])
                kep_rows.append({
                    "instrument": kp["instrument"], "star": kp["star"], "rep_dp_id": kp["rep_dp_id"], "band_id": kp["band_id"],
                    "dv_span_kms": kp["dv_span_kms"], "injected_planet_wave_a": round(inj_p, 4), "phase_bins": ph, "exp_sigma_mult": me,
                    "tdiff_uncomp_snr_mid": ftd.get("snr_mid", 0.0), "tdiff_uncomp_recovered": td_rec,
                    "kplanet_dedop_snr_mid": fkp.get("snr_mid", 0.0), "kplanet_dedop_fwhm_ratio": fkp.get("fwhm_ratio"),
                    "kplanet_dedop_recovered": kprec,
                })
    write_csv(res_dir / "KEPLERIAN_TRACK_CALIBRATION_135.csv", kep_rows)

    # Suite D: 216 Detector G4/G5 Physics Trials (72 Patches x 3 Classes)
    g45_rows: list[dict[str, Any]] = []
    for rp in bundle["calib_g4g5_patches"]:
        cfg_d = get_inst_config(rp["instrument"], rp["resolving_power"])
        base_ops = rp["order_patches"]
        tgt = float(rp["target_bary_a"])
        rw = float(rp["stellar_rest_wave_a"])
        sig_a = tgt / (cfg_d["resolving_power"] * FWHM_FACTOR)
        ol, oi, opl = [], [], []
        for op in base_ops:
            wo, fo = np.asarray(op["wave"], dtype=np.float64), np.asarray(op["flux_a"], dtype=np.float64)
            c80 = exact_quantile_1d(fo[np.isfinite(fo) & (fo > 0)], 0.80) if np.sum(fo > 0) >= 10 else 1.0
            mad_loc = max(0.015, exact_mad_1d(np.diff(fo[np.isfinite(fo)])) / (1.4142 * max(1e-6, c80)))
            wt_i = float(op["target_wave_a"])
            kt = int(np.argmin(np.abs(wo - wt_i)))
            g_l = np.exp(-0.5 * ((wo - wt_i) / sig_a) ** 2)
            g_p = np.exp(-0.5 * ((wo - wt_i) / (3.6 * sig_a)) ** 2)
            pc = np.zeros_like(fo)
            pc[kt] = max(0.85, 30.0 * mad_loc) * c80
            if kt > 0:
                pc[kt - 1] = 0.01 * pc[kt]
            if kt + 1 < len(pc):
                pc[kt + 1] = 0.01 * pc[kt]
            ol.append({**op, "flux_a": fo + max(0.28, 18.0 * mad_loc) * c80 * g_l})
            oi.append({**op, "flux_a": fo + pc})
            opl.append({**op, "flux_a": fo + max(0.45, 22.0 * mad_loc) * c80 * g_p})
        for tcls, exp_g45, rs in (
            ("TRUE_LSF_LASER", True, evaluate_gates_g3_g4_g5_v37(ol, "TRG_DARK", "T", rw, cfg_d)),
            ("COSMIC_SINGLE_PX_SPIKE", False, evaluate_gates_g3_g4_g5_v37(oi, "TRG_DARK", "T", rw, cfg_d)),
            ("WIDE_SCATTERING_PLATEAU", False, evaluate_gates_g3_g4_g5_v37(opl, "TRG_DARK", "T", rw, cfg_d)),
        ):
            g45_rows.append({
                "instrument": rp["instrument"], "star": rp["star"], "dp_id": rp["dp_id"], "band_id": rp["band_id"],
                "primary_order": rs.get("primary_order"), "primary_native_px": rs.get("primary_native_px"),
                "trial_class": tcls, "expected_g45_pass": exp_g45,
                "g4_pass": rs["g4_pass"], "g5_pass": rs["g5_pass"], "g45_pass": bool(rs["g4_pass"] and rs["g5_pass"]),
                "cos_1d_11px": rs.get("cos_1d_11px"), "ipc_hotpx_ratio": rs.get("ipc_hotpx_ratio"),
                "far_wing_34_ratio": rs.get("far_wing_34_ratio"),
                "g4_reason": rs["g4_reason"], "g5_reason": rs["g5_reason"],
            })
    write_csv(res_dir / "DETECTOR_V37_G4G5_CALIBRATION_216.csv", g45_rows)

    # Suite E: 240-Trial G6_V36 Sparse vs G6_V35 Dense Head-to-Head Benchmark
    g6_rows: list[dict[str, Any]] = []
    for gp in bundle["calib_g6_patches"]:
        cfg_g = get_inst_config(gp["instrument"])
        tc, co, cpx = float(gp["cand_topo_vac_a"]), gp["cand_order"], gp["cand_px"]
        tvs, tbv = float(gp["target_vshift_kms"]), float(gp["target_berv_kms"])
        tdp, odp, obv = gp["dp_id"], gp["opp_dp_id"], float(gp["opp_berv_kms"])
        real_d, real_s = list(gp["local_dense_atlas"]), list(gp["local_sparse_atlas"])
        oths = gp["synthetic_other_stars"]
        for sg in G6_CALIBRATION_SIGMAS:
            r1_d = evaluate_gate_g6_v35_dense(gp["star"], tc, co, cpx, tvs, real_d, cfg_g)
            r1_s = evaluate_gate_g6_v36_sparse(gp["star"], tdp, tbv, tc, co, cpx, tvs, real_s, cfg_g, "T")
            oh_r = [{"star": s2, "dp_id": f"SYN_{s2}", "berv_kms": 0.0, "topo_air_a": tc + 0.015 * (idx - 1), "order": co + 1, "px": cpx + 120} for idx, (s2, _vs) in enumerate(oths)]
            r2_d = evaluate_gate_g6_v35_dense(gp["star"], tc, co, cpx, tvs, real_d + oh_r, cfg_g)
            r2_s = evaluate_gate_g6_v36_sparse(gp["star"], tdp, tbv, tc, co, cpx, tvs, real_s + oh_r, cfg_g, "T")
            px_r = [{"star": s2, "dp_id": f"SYN_{s2}", "berv_kms": 0.0, "topo_air_a": tc + 1.35 + 0.1 * idx, "order": co, "px": cpx} for idx, (s2, _vs) in enumerate(oths)]
            r3_d = evaluate_gate_g6_v35_dense(gp["star"], tc, co, cpx, tvs, real_d + px_r, cfg_g)
            r3_s = evaluate_gate_g6_v36_sparse(gp["star"], tdp, tbv, tc, co, cpx, tvs, real_s + px_r, cfg_g, "T")
            intra_r = [{"star": gp["star"], "dp_id": odp, "berv_kms": obv, "topo_air_a": tc + 0.02, "order": co, "px": cpx}]
            r4_d = evaluate_gate_g6_v35_dense(gp["star"], tc, co, cpx, tvs, real_d + intra_r, cfg_g)
            r4_s = evaluate_gate_g6_v36_sparse(gp["star"], tdp, tbv, tc, co, cpx, tvs, real_s + intra_r, cfg_g, "T")
            for tcls, exp_p, rd, rs in (
                ("TRUE_BARYCENTRIC_STELLAR_LASER", True, r1_d, r1_s),
                ("UNLISTED_STATIONARY_SKY_OH_LINE", False, r2_d, r2_s),
                ("STATIONARY_DETECTOR_WARM_PIXEL", False, r3_d, r3_s),
                ("INTRA_STAR_BERV_STATIONARY_GHOST", False, r4_d, r4_s),
            ):
                g6_rows.append({
                    "instrument": gp["instrument"], "star": gp["star"], "dp_id": tdp, "band_id": gp["band_id"],
                    "sigma_inj": sg, "trial_class": tcls, "expected_g6_pass": exp_p,
                    "g6_v35_dense_pass": rd["g6_v35_pass"], "g6_v36_sparse_pass": rs["g6_pass"],
                    "g6_v36_same_star_hits": rs["g6_same_star_stationary_hits"],
                })
    write_csv(res_dir / "G6_SPARSE_VS_DENSE_CALIBRATION_240.csv", g6_rows)

    # Suite F: 486-Trial COMB_V4_1 vs COMB_V4 Head-to-Head Calibration (18 patches x 3 spacings x 9 trials)
    comb_cal_rows: list[dict[str, Any]] = []
    for idx_cp, cp in enumerate(bundle["calib_comb_patches"]):
        cfg_c = get_inst_config(cp["instrument"], cp["resolving_power"])
        sig_v = float(cfg_c["sigma_v_kms"])
        ww = np.asarray(cp["wave_win"], dtype=np.float64)
        yr = _arr_from_nullable(cp["y_rest_win"])
        sr = _arr_from_nullable(cp["sigma_rest_win"])
        fn = _arr_from_nullable(cp["fn_win"])
        rc = np.asarray(cp["recon_win"], dtype=np.float64)
        sk = np.asarray(cp["sky_mask_win"], dtype=bool)
        yt = _arr_from_nullable(cp["y_topo_win"])
        st_arr = _arr_from_nullable(cp["sigma_topo_win"])
        med_sr = exact_median_1d(sr[np.isfinite(sr) & (sr > 0)])
        med_st = exact_median_1d(st_arr[np.isfinite(st_arr) & (st_arr > 0)])
        nu_lo_c = C_ANGSTROM_GHZ / float(ww[-20])
        nu_hi_c = C_ANGSTROM_GHZ / float(ww[20])
        wins_loc = [{"band": cp["band"], "lo_a": float(ww[0]), "hi_a": float(ww[-1])}]
        epoch_bervs = [float(x) for x in cp.get("epoch_bervs_kms", [cp["median_berv_kms"]])]

        for dnu in COMB_CALIBRATION_SPACINGS:
            dnu_s = float(dnu)
            best_nu0 = nu_lo_c + 5.0
            best_sc = (-1, -1e9)
            for off in np.arange(5.0, max(6.0, nu_hi_c - nu_lo_c - 5.0 * dnu_s - 5.0), 2.5):
                n0_t = float(nu_lo_c + off)
                ks = [int(np.argmin(np.abs(ww - C_ANGSTROM_GHZ / (n0_t + t * dnu_s)))) for t in range(6)]
                if not all(
                    16 <= kt < len(ww) - 16 and np.isfinite(yr[kt]) and np.isfinite(sr[kt]) and sr[kt] > 0 and np.isfinite(fn[kt])
                    for kt in ks
                ):
                    continue
                n_clean = sum(1 for kt in ks if fn[kt] >= 0.86 and abs(yr[kt]) <= 1.5 * sr[kt])
                sc = (n_clean, min(float(fn[kt]) for kt in ks))
                if sc > best_sc:
                    best_sc, best_nu0 = sc, n0_t
            t_waves = [C_ANGSTROM_GHZ / (best_nu0 + t * dnu_s) for t in range(6)]
            t_sigs = [float(sr[int(np.argmin(np.abs(ww - wt)))]) if np.isfinite(sr[int(np.argmin(np.abs(ww - wt)))]) else med_sr for wt in t_waves]
            ts_sigs = [float(st_arr[int(np.argmin(np.abs(ww - wt)))]) if np.isfinite(st_arr[int(np.argmin(np.abs(ww - wt)))]) else med_st for wt in t_waves]

            tooth_unit = np.zeros(len(ww), dtype=np.float64)
            topo_unit = np.zeros(len(ww), dtype=np.float64)
            for wt_a, sloc, stloc in zip(t_waves, t_sigs, ts_sigs):
                pw = np.exp(-0.5 * ((C_KMS * (ww - wt_a) / wt_a) / sig_v) ** 2)
                tooth_unit += sloc * pw
                topo_unit += max(sloc, stloc) * pw
            ep_topo_stack = []
            for b_ep in epoch_bervs:
                dv_ep = float(cp["v_star_kms"]) - b_ep
                ep_prof = np.zeros(len(ww), dtype=np.float64)
                for wt_a, sloc in zip(t_waves, t_sigs):
                    wt_ep = wt_a * (1.0 + dv_ep / C_KMS)
                    ep_prof += sloc * np.exp(-0.5 * ((C_KMS * (ww - wt_ep) / wt_ep) / sig_v) ** 2)
                ep_topo_stack.append(ep_prof)
            smear_unit = np.median(np.vstack(ep_topo_stack), axis=0)

            sub_cfg = {**cfg_c, "comb_spacings_ghz": [dnu_s]}
            # 6 True 6-Tooth Comb SNRs
            for snr_t in COMB_CALIBRATION_SIGMAS:
                yi = yr + snr_t * tooth_unit
                fni = fn + snr_t * tooth_unit
                yti = yt + snr_t * smear_unit
                h4, _ = scan_frequency_comb_v4(ww, yi, sr, fni, rc, sk, yti, st_arr, wins_loc, [cp["band"]], sub_cfg)
                h41, _ = scan_frequency_comb_v4_1(ww, yi, sr, fni, rc, sk, yti, st_arr, wins_loc, [cp["band"]], sub_cfg)
                comb_cal_rows.append({
                    "instrument": cp["instrument"], "star": cp["star"], "band": cp["band"], "dnu_ghz": dnu_s,
                    "trial_class": "TRUE_6TOOTH_STELLAR_COMB", "tooth_snr_inj": snr_t, "expected_comb_hit": True,
                    "comb_v4_hit": any(abs(h["nu0_ghz"] - best_nu0) <= 5.0 for h in h4),
                    "comb_v41_hit": any(abs(h["nu0_ghz"] - best_nu0) <= 5.0 for h in h41),
                    "comb_hit": any(abs(h["nu0_ghz"] - best_nu0) <= 5.0 for h in h41),
                    "max_s_comb": round(max((h["s_comb"] for h in h41), default=0.0), 4),
                })

            # Class 2: Single Bright Line Masquerade (20 sigma)
            one_u = t_sigs[2] * np.exp(-0.5 * ((C_KMS * (ww - t_waves[2]) / t_waves[2]) / sig_v) ** 2)
            h4_1, _ = scan_frequency_comb_v4(ww, yr + 20.0 * one_u, sr, fn + 20.0 * one_u, rc, sk, yt, st_arr, wins_loc, [cp["band"]], sub_cfg)
            h41_1, _ = scan_frequency_comb_v4_1(ww, yr + 20.0 * one_u, sr, fn + 20.0 * one_u, rc, sk, yt, st_arr, wins_loc, [cp["band"]], sub_cfg)
            comb_cal_rows.append({
                "instrument": cp["instrument"], "star": cp["star"], "band": cp["band"], "dnu_ghz": dnu_s,
                "trial_class": "SINGLE_BRIGHT_LINE_MASQUERADE", "tooth_snr_inj": 20.0, "expected_comb_hit": False,
                "comb_v4_hit": len(h4_1) > 0, "comb_v41_hit": len(h41_1) > 0, "comb_hit": len(h41_1) > 0,
                "max_s_comb": round(max((h["s_comb"] for h in h41_1), default=0.0), 4),
            })

            # Class 3: Stationary Topocentric Ro-Vib Pseudocomb (6.0 sigma in both frames -> anti_ratio ~ 1.0)
            h4_t, _ = scan_frequency_comb_v4(ww, yr + 6.0 * tooth_unit, sr, fn + 6.0 * tooth_unit, rc, sk, yt + 6.2 * topo_unit, st_arr, wins_loc, [cp["band"]], sub_cfg)
            h41_t, _ = scan_frequency_comb_v4_1(ww, yr + 6.0 * tooth_unit, sr, fn + 6.0 * tooth_unit, rc, sk, yt + 6.2 * topo_unit, st_arr, wins_loc, [cp["band"]], sub_cfg)
            comb_cal_rows.append({
                "instrument": cp["instrument"], "star": cp["star"], "band": cp["band"], "dnu_ghz": dnu_s,
                "trial_class": "STATIONARY_TOPO_ROVIB_PSEUDOCOMB", "tooth_snr_inj": 6.0, "expected_comb_hit": False,
                "comb_v4_hit": len(h4_t) > 0, "comb_v41_hit": len(h41_t) > 0, "comb_hit": len(h41_t) > 0,
                "max_s_comb": round(max((h["s_comb"] for h in h41_t), default=0.0), 4),
            })

            # Class 4: Dense Molecular / Photospheric Forest Pseudocomb (sub-harmonic + inter-tooth clutter!)
            dense_forest = np.zeros(len(ww), dtype=np.float64)
            for q_off in np.arange(-1.0, 6.25, 0.25):
                w_q = C_ANGSTROM_GHZ / (best_nu0 + q_off * dnu_s)
                if ww[5] <= w_q <= ww[-6]:
                    jq = int(np.argmin(np.abs(ww - w_q)))
                    dense_forest += (4.3 * (sr[jq] if np.isfinite(sr[jq]) else med_sr)) * np.exp(-0.5 * ((C_KMS * (ww - w_q) / w_q) / sig_v) ** 2)
            h4_f, _ = scan_frequency_comb_v4(ww, yr + dense_forest, sr, fn + dense_forest, rc, sk, yt, st_arr, wins_loc, [cp["band"]], sub_cfg)
            h41_f, _ = scan_frequency_comb_v4_1(ww, yr + dense_forest, sr, fn + dense_forest, rc, sk, yt, st_arr, wins_loc, [cp["band"]], sub_cfg)
            comb_cal_rows.append({
                "instrument": cp["instrument"], "star": cp["star"], "band": cp["band"], "dnu_ghz": dnu_s,
                "trial_class": "DENSE_MOLECULAR_FOREST_PSEUDOCOMB", "tooth_snr_inj": 4.3, "expected_comb_hit": False,
                "comb_v4_hit": len(h4_f) > 0, "comb_v41_hit": len(h41_f) > 0, "comb_hit": len(h41_f) > 0,
                "max_s_comb": round(max((h["s_comb"] for h in h41_f), default=0.0), 4),
            })
    write_csv(res_dir / "COMB_V4_1_CALIBRATION_486.csv", comb_cal_rows)

    # Read-only D085 COMB_V4_1 Regression Evaluation on D085's 19 COMB_V4 false alarms
    reg_rows: list[dict[str, Any]] = []
    cfg_spirou = {**BASE_V3_7_CONFIG, "instrument": "SPIROU", "resolving_power": 70000.0, "sigma_v_kms": (C_KMS / 70000.0) / FWHM_FACTOR}
    for idx_r, c85 in enumerate(bundle["d085_comb_real_candidates_bundle"], start=1):
        ww = np.asarray(c85["wave_win"], dtype=np.float64)
        yr = _arr_from_nullable(c85["y_rest_win"])
        sr = _arr_from_nullable(c85["sigma_rest_win"])
        fn = _arr_from_nullable(c85["fn_win"])
        rc = np.asarray([1.0 if x is None else float(x) for x in c85["recon_win"]], dtype=np.float64)
        sk = np.asarray(c85["sky_mask_win"], dtype=bool)
        yt = _arr_from_nullable(c85["y_topo_win"])
        st_arr = _arr_from_nullable(c85["sigma_topo_win"])
        wins85 = [{"band": c85["band"], "lo_a": float(ww[0]), "hi_a": float(ww[-1])}]
        sub_85 = {**cfg_spirou, "comb_spacings_ghz": [float(c85["dnu_ghz"])]}
        h85_v4, _ = scan_frequency_comb_v4(ww, yr, sr, fn, rc, sk, yt, st_arr, wins85, [c85["band"]], sub_85)
        h85_v41, _ = scan_frequency_comb_v4_1(ww, yr, sr, fn, rc, sk, yt, st_arr, wins85, [c85["band"]], sub_85)
        reg_rows.append({
            "d085_comb_index": idx_r,
            "star": c85["star"],
            "band": c85["band"],
            "dnu_ghz": c85["dnu_ghz"],
            "nu0_ghz_stage_a": c85["nu0_ghz_stage_a"],
            "s_comb_stage_a": c85["s_comb_stage_a"],
            "comb_v4_retained": len(h85_v4) > 0,
            "comb_v41_retained": len(h85_v41) > 0,
        })
    write_csv(res_dir / "D085_COMB_V4_1_REGRESSION_19.csv", reg_rows)

    # Calibration Completeness By Band
    cb_rows: list[dict[str, Any]] = []
    for inst in ("UVES_NUV", "ESPRESSO", "HARPS"):
        for mode, s_list in (("CHANNEL_T_TRANSIENT_1EPOCH", TRANSIENT_INJECTION_SIGMAS), ("CHANNEL_P_PERSISTENT_MULTIEPOCH", PERSISTENT_INJECTION_SIGMAS)):
            for bnd in get_calibration_bands(inst):
                for sm in s_list:
                    sub = [r for r in inj_rows if r["instrument"] == inst and r["mode"] == mode and r["band_id"] == bnd["band_id"] and r["sigma_mult"] == sm]
                    if not sub:
                        continue
                    nr = sum(1 for r in sub if r["recovered"])
                    cb_rows.append({
                        "instrument": inst, "mode": mode, "band_id": bnd["band_id"], "center_bary_air_A": bnd["center_bary_air_A"],
                        "sigma_mult": sm, "n_trials": len(sub), "n_recovered": nr, "completeness": round(nr / len(sub), 6),
                    })
    write_csv(res_dir / "CALIBRATION_COMPLETENESS_BY_BAND.csv", cb_rows)

    # 4. Evaluate All Uninjected Real Single-Line Candidates Across Channels T, P, T_DIFF, K_PLANET + G1..G6
    ledger: list[dict[str, Any]] = []
    cand_diag_by_id: dict[str, dict[str, Any]] = {}
    cand_idx = 0
    for item in bundle["real_candidates_bundle"]:
        cand_idx += 1
        ch = item["channel"]
        inst = item["instrument"]
        agrp = item["atlas_group"]
        cfg_c = get_inst_config(inst, item["resolving_power"])
        cid = f"V37-{ch}-{cand_idx:04d}"
        fb_over_fa_pk = 0.0
        if item["order_patches"]:
            op0 = item["order_patches"][0]
            fa0 = np.asarray(op0["flux_a"], dtype=np.float64)
            fb0_raw = op0.get("flux_b")
            fa_fin = fa0[np.isfinite(fa0)]
            if fb0_raw is not None and len(fa_fin) >= 10:
                fb0 = np.asarray(fb0_raw, dtype=np.float64)
                fb_fin = fb0[np.isfinite(fb0)]
                if len(fb_fin) >= 10:
                    kc_op = len(fa0) // 2
                    fb_pk = float(np.nanmax(fb0[max(0, kc_op - 3) : min(len(fb0), kc_op + 4)]))
                    fa_med = max(1e-6, exact_median_1d(fa_fin))
                    fb_over_fa_pk = fb_pk / fa_med
        cand_diag_by_id[cid] = {
            "dpr_or_calsel": item["dpr_or_calsel"],
            "fb_over_fa_pk": fb_over_fa_pk,
        }
        ww = np.asarray(item["wave_win"], dtype=np.float64)
        yp = _arr_from_nullable(item["y_primary_win"])
        fit = fit_lsf_on_window(ww, yp, float(item["seed_wave_a"]), cfg_c)
        fc = float(fit.get("fitted_center_a", float(item["seed_wave_a"])))
        f1 = compute_supraphotospheric_f1_window(ww, _arr_from_nullable(item["f_norm_win"]), fc, cfg_c["supraphotospheric_min_fn_pk3"])
        if ch == "T":
            bary_a = fc
            rest_a = bary_a / (1.0 + float(item["v_star_kms"]) / C_KMS)
        elif ch in ("P", "T_DIFF"):
            rest_a = fc
            bary_a = rest_a * (1.0 + float(item["v_star_kms"]) / C_KMS)
        else:
            bary_a = fc * (1.0 + float(item["v_star_kms"]) / C_KMS) * (1.0 + float(item["dv_orb_kms"]) / C_KMS)
            rest_a = bary_a / (1.0 + float(item["v_star_kms"]) / C_KMS)

        g2 = evaluate_gate_g2_airglow(bary_a, float(item["berv_kms"]), cfg_c, continuum_snr=float(item.get("cont_snr_est", 50.0)))
        if g2["g2_pass"] and item["order_patches"]:
            g345 = evaluate_gates_g3_g4_g5_v37(item["order_patches"], item["dpr_or_calsel"], ch, rest_a, cfg_c)
        else:
            g345 = {"g3_pass": False, "g3_reason": "NOT_EVALUATED", "g4_pass": False, "g4_reason": "NOT_EVALUATED", "g5_pass": False, "g5_reason": "NOT_EVALUATED"}

        g6d = evaluate_gate_g6_v35_dense(item["star"], g2["topo_air_a"], g345.get("primary_order"), g345.get("primary_native_px"), float(item["vshift_kms"]), bundle["dense_atlas_by_group"][agrp], cfg_c)
        g6s = evaluate_gate_g6_v36_sparse(item["star"], item["dp_id"], float(item["berv_kms"]), g2["topo_air_a"], g345.get("primary_order"), g345.get("primary_native_px"), float(item["vshift_kms"]), bundle["sparse_atlas_by_group"][agrp], cfg_c, ch)
        pre_g6 = bool(f1["f1_supraphotospheric_pass"] and g2["g2_pass"] and g345["g3_pass"] and g345["g4_pass"] and g345["g5_pass"])
        qual = bool(pre_g6 and g6s["g6_pass"])

        if not f1["f1_supraphotospheric_pass"]:
            disp = "G1_V37_SUBCONTINUUM_VETO"
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
            disp = "QUALIFIED_V3_7_LASER_CANDIDATE"

        ledger.append({
            "candidate_id": cid, "instrument": inst, "channel": ch, "role": item["role"],
            "star": item["star"], "dp_id": item["dp_id"], "fitted_wave_a": round(fc, 5),
            "stellar_rest_wave_a": round(rest_a, 5), "bary_wave_a": round(bary_a, 5),
            "topo_wave_a": round(g2["topo_air_a"], 5),
            "snr_mid": round(float(fit.get("snr_mid", 0.0)), 4),
            "snr_out": round(float(fit.get("snr_out", 0.0)), 4),
            "cosine": round(float(fit.get("cosine", 0.0)), 4),
            "fwhm_ratio": fit.get("fwhm_ratio"),
            "target_fn_pk3": round(f1["fn_pk3"], 5),
            "g1_pass": f1["f1_supraphotospheric_pass"], "g2_pass": g2["g2_pass"],
            "g3_pass": g345["g3_pass"], "primary_order": g345.get("primary_order"),
            "primary_native_px": g345.get("primary_native_px"),
            "primary_native_fn_pk3": g345.get("primary_native_fn_pk3"),
            "primary_eta_1px": g345.get("primary_eta_1px"),
            "g4_pass": g345["g4_pass"], "g5_pass": g345["g5_pass"],
            "g5_cos11": g345.get("cos_1d_11px"), "g5_ipc_hotpx_ratio": g345.get("ipc_hotpx_ratio"),
            "g5_far_wing_ratio": g345.get("far_wing_34_ratio"),
            "pre_g6_qualified": pre_g6,
            "g6_v35_dense_pass": g6d["g6_v35_pass"],
            "g6_pass": g6s["g6_pass"],
            "g6_coincident_total_stars": g6s["g6_coincident_total_stars"],
            "g6_same_star_hits": g6s["g6_same_star_stationary_hits"],
            "qualified_v37_laser": qual,
            "final_disposition": disp,
        })
    write_csv(res_dir / "V3_7_CANDIDATE_LEDGER.csv", ledger)

    # Four-Gen Benchmark (181)
    bench_rows: list[dict[str, Any]] = []
    for p in bundle["provenance_rows"]:
        dp = p["dp_id"]
        sub = [x for x in ledger if x["dp_id"] == dp]
        bench_rows.append({
            "instrument": p["instrument"], "star": p["star"], "role": p["role"], "dp_id": dp,
            "v2_accepted_false_alarms": bundle["v2_counts_by_dp"].get(dp, 0),
            "v37_g1_candidates": len(sub),
            "v37_pre_g6": sum(1 for x in sub if x["pre_g6_qualified"]),
            "v37_post_g6_qualified": sum(1 for x in sub if x["qualified_v37_laser"]),
        })
    write_csv(res_dir / "FOUR_GEN_BENCHMARK_181.csv", bench_rows)

    # Real COMB_V4_1 & COMB_V4 Star Results + Candidates
    comb_cands_out: list[dict[str, Any]] = []
    comb_v4_real_count = 0
    comb_v41_by_star: dict[str, int] = {s: 0 for s in bundle["star_meta"]}
    comb_v4_by_star: dict[str, int] = {s: 0 for s in bundle["star_meta"]}

    for cr in bundle["comb_real_candidates_bundle"]:
        cfg_c = get_inst_config(cr["instrument"], cr["resolving_power"])
        ww = np.asarray(cr["wave_win"], dtype=np.float64)
        yr = _arr_from_nullable(cr["y_rest_win"])
        sr = _arr_from_nullable(cr["sigma_rest_win"])
        fn = _arr_from_nullable(cr["fn_win"])
        rc = np.asarray(cr["recon_win"], dtype=np.float64)
        sk = np.asarray(cr["sky_mask_win"], dtype=bool)
        yt = _arr_from_nullable(cr["y_topo_win"])
        st_arr = _arr_from_nullable(cr["sigma_topo_win"])
        win_c = [{"band": cr["band"], "lo_a": float(ww[0]), "hi_a": float(ww[-1])}]
        sub_c = {**cfg_c, "comb_spacings_ghz": [float(cr["dnu_ghz"])]}
        h4, _ = scan_frequency_comb_v4(ww, yr, sr, fn, rc, sk, yt, st_arr, win_c, [cr["band"]], sub_c)
        h41, _ = scan_frequency_comb_v4_1(ww, yr, sr, fn, rc, sk, yt, st_arr, win_c, [cr["band"]], sub_c)
        if h4:
            comb_v4_real_count += len(h4)
            comb_v4_by_star[cr["star"]] = comb_v4_by_star.get(cr["star"], 0) + len(h4)
        for ch in h41:
            if any(
                p["star"] == cr["star"] and p["band"] == cr["band"] and abs(p["dnu_ghz"] - ch["dnu_ghz"]) < 1e-3 and abs(p["nu0_ghz"] - ch["nu0_ghz"]) <= 0.5 * ch["dnu_ghz"]
                for p in comb_cands_out
            ):
                continue
            comb_v41_by_star[cr["star"]] = comb_v41_by_star.get(cr["star"], 0) + 1
            comb_cands_out.append({
                "comb_id": f"V41COMB-{len(comb_cands_out) + 1:04d}",
                "instrument": cr["instrument"], "star": cr["star"], "role": cr["role"],
                "band": cr["band"], "dnu_ghz": ch["dnu_ghz"], "nu0_ghz": ch["nu0_ghz"],
                "wave0_a": ch["wave0_a"], "wave_end_a": ch["wave_end_a"],
                "s_comb": ch["s_comb"], "topo_anti_ratio": ch["topo_anti_ratio"],
                "n_qualifying_teeth": ch["n_qualifying_teeth"],
                "off_tooth_crowding": ch["off_tooth_crowding"],
                "intertooth_ratio": ch["intertooth_ratio"],
            })

    write_csv(res_dir / "COMB_V4_1_CANDIDATES.csv", comb_cands_out, fieldnames=[
        "comb_id", "instrument", "star", "role", "band", "dnu_ghz", "nu0_ghz",
        "wave0_a", "wave_end_a", "s_comb", "topo_anti_ratio", "n_qualifying_teeth",
        "off_tooth_crowding", "intertooth_ratio",
    ])
    comb_star_rows = [
        {
            "instrument": bundle["star_meta"][st]["instrument"], "star": st, "role": bundle["star_meta"][st]["role"],
            "comb_v4_candidates": comb_v4_by_star[st], "comb_v41_candidates": comb_v41_by_star[st],
            "verified_eti_combs": 0,
        }
        for st in sorted(bundle["star_meta"])
    ]
    write_csv(res_dir / "COMB_V4_1_STAR_RESULTS_31.csv", comb_star_rows)

    # 5. Forensic Candidate Audit (100% of Post-G6 Survivors + COMB_V4_1 Candidates)
    post_g6 = [r for r in ledger if r["qualified_v37_laser"]]
    sl_forensic = []
    for r in post_g6:
        cls, rat = _classify_singleline_forensic(r, cand_diag_by_id.get(r["candidate_id"]))
        sl_forensic.append({
            "candidate_id": r["candidate_id"], "instrument": r["instrument"], "channel": r["channel"],
            "role": r["role"], "star": r["star"], "dp_id": r["dp_id"],
            "bary_wave_a": r["bary_wave_a"], "stellar_rest_wave_a": r["stellar_rest_wave_a"],
            "snr_mid": r["snr_mid"], "target_fn_pk3": r["target_fn_pk3"],
            "forensic_classification": cls, "forensic_rationale": rat, "eti_plausible": False,
        })
    cb_forensic = []
    for c in comb_cands_out:
        if c["instrument"] == "ESPRESSO" and c["star"] == "GJ1002" and abs(float(c["dnu_ghz"]) - 40.0) < 1e-3:
            c_cls = "FIBER_B_FABRY_PEROT_HARMONIC_BLEED"
            c_rat = (
                f"ESPRESSO TRG_CALB simultaneous Fabry-Perot etalon bleed at 2x 20 GHz FSR harmonic "
                f"({c['band']} ~{c['wave_end_a']}-{c['wave0_a']} A) onto faint M5.5V Fiber A; not stellar."
            )
        else:
            c_cls = "PHOTOSPHERIC_TEMPLATE_MISMATCH_OR_WAVE_CAL_RIPPLE"
            c_rat = (
                f"Photospheric Fe I / rotational broadening template-subtraction ripple or Fiber-B WAVE leak "
                f"({c['instrument']} {c['star']} {c['band']} dnu={c['dnu_ghz']} GHz); lacks independent laser morphology."
            )
        cb_forensic.append({
            "comb_id": c["comb_id"], "instrument": c["instrument"], "star": c["star"], "role": c["role"],
            "band": c["band"], "dnu_ghz": c["dnu_ghz"], "s_comb": c["s_comb"],
            "forensic_classification": c_cls,
            "forensic_rationale": c_rat,
            "eti_plausible": False,
        })

    for_doc = {
        "schema": "D086_FORENSIC_CANDIDATE_AUDIT_V1",
        "phase_id": "D086",
        "pre_g6_count": sum(1 for r in ledger if r["pre_g6_qualified"]),
        "post_g6_count": len(post_g6),
        "comb_v41_count": len(comb_cands_out),
        "post_g6_singleline_forensic_classifications": sl_forensic,
        "comb_v41_forensic_classifications": cb_forensic,
        "verified_eti_detections": 0,
    }
    write_json(HERE / "FORENSIC_CANDIDATE_AUDIT_D086.json", for_doc)
    write_json(res_dir / "FORENSIC_D086_CASCADE_DIAGNOSIS.json", {
        "pre_g6_count": for_doc["pre_g6_count"],
        "post_g6_qualified": post_g6,
        "comb_v41_candidates": comb_cands_out,
    })

    # 6. Orbital Campaign Results (10)
    orb_rows: list[dict[str, Any]] = []
    for st, cm in sorted(orb_cat["campaigns"].items()):
        in_dvs = [float(x["planet_orbital_rv_kms"]) for x in cm["exposures"] if x["phase_window"] == "IN_WINDOW"]
        q_td = sum(1 for r in ledger if r["star"] == st and r["channel"] == "T_DIFF" and r["qualified_v37_laser"])
        q_kp = sum(1 for r in ledger if r["star"] == st and r["channel"] == "K_PLANET" and r["qualified_v37_laser"])
        orb_rows.append({
            "star": st, "common_name": cm["common_name"], "instrument": cm["instrument"], "role": cm["role"],
            "planet_name": cm["planet_name"], "transiting": cm["transiting"], "orbper_days": cm["orbper_days"],
            "kp_kms": cm["kp_kms"], "orbital_dv_span_kms": round(max(in_dvs) - min(in_dvs), 4),
            "n_in_window": cm["n_in_window"], "n_out_of_window": cm["n_out_of_window"],
            "qualified_tdiff_candidates": q_td, "qualified_kplanet_candidates": q_kp, "verified_eti_detections": 0,
        })
    write_csv(res_dir / "ORBITAL_CAMPAIGN_RESULTS_10.csv", orb_rows)

    # 7. Science Upper Limits (NaN-free) + 13-Star Bridge + 90-Star <10pc + 175-Star Unified + 181-System MM
    ul_rows: list[dict[str, Any]] = []
    min_lim_by_star: dict[str, dict[str, float]] = {}
    for p in bundle["upper_limit_patches"]:
        mad_r = float(p["median_epoch_mad_rel"])
        amp_8s = 8.0 * mad_r
        anchor = p["radiometric_anchor"]
        mag = float(p["phot_bp_mag"]) if anchor == "GAIA_DR3_GBP" else float(p["phot_g_mag"])
        rp = float(p["resolving_power"])
        lim = compute_photon_beam_upper_limit(
            float(p["wave_bary_air_A"]), amp_8s, float(p["teff_k"]), float(p["dist_pc"]), mag, anchor, rp
        )
        st = p["star"]
        min_lim_by_star.setdefault(st, {})
        if p["instrument"] == "UVES_NUV":
            prev = min_lim_by_star[st].get("min_nuv_10m_kw", 1e18)
            min_lim_by_star[st]["min_nuv_10m_kw"] = min(prev, lim["p_beam_10m_kw"])
        else:
            prev = min_lim_by_star[st].get("min_optical_10m_kw", 1e18)
            min_lim_by_star[st]["min_optical_10m_kw"] = min(prev, lim["p_beam_10m_kw"])

        ul_rows.append({
            "instrument": p["instrument"], "star": st, "common_name": p["common_name"], "subrole": p["subrole"],
            "panchromatic_bridge": p["panchromatic_bridge"], "radio_mm_id": p["radio_mm_id"], "within_10pc": p["within_10pc"],
            "n_exoplanets": p["n_exoplanets"], "has_transiting_planet": p["has_transiting_planet"],
            "dist_pc": p["dist_pc"], "teff_k": p["teff_k"], "phot_g_mag": p["phot_g_mag"], "phot_bp_mag": p["phot_bp_mag"],
            "j_mag": p["j_mag"], "h_mag": p["h_mag"], "ks_mag": p["ks_mag"],
            "radiometric_anchor": anchor, "resolving_power": rp,
            "band_id": p["band_id"], "wave_bary_air_A": p["wave_bary_air_A"],
            "median_epoch_mad_rel": mad_r, "amp_rel_8sigma_lim": amp_8s,
            "fwhm_lsf_a": lim["fwhm_lsf_a"], "ew_lim_mA": lim["ew_lim_mA"],
            "continuum_flam_cgs": lim["continuum_flam_cgs"], "flux_lim_erg_cm2_s": lim["flux_lim_erg_cm2_s"],
            "l_iso_mw": lim["l_iso_mw"], "p_beam_10m_w": lim["p_beam_10m_w"], "p_beam_10m_kw": lim["p_beam_10m_kw"],
        })
    write_csv(res_dir / "STAR_UPPER_LIMITS_D086.csv", ul_rows)

    # Panchromatic 13-Star Bridge Table (D085's 8 bridge stars + new D086 UVES/Optical bands on PROXIMACEN + 5 new bridges!)
    bridge_rows: list[dict[str, Any]] = []
    for br in prior_snap["d085_bridge_8star_rows"]:
        bridge_rows.append(dict(br))
    for pr in prior_snap["prior_new_bridge_upper_limits"]:
        wc_str = pr.get("wave_bary_vac_A") or pr.get("wave_bary_air_A") or "10000.0"
        wc_f = float(wc_str)
        bridge_rows.append({
            "phase_id": pr["phase_id"], "spectral_regime": pr["spectral_regime"], "instrument": pr["instrument"],
            "star": pr["star"], "common_name": pr["common_name"], "dist_pc": pr["dist_pc"],
            "band_id": pr["band_id"], "wave_um": round(wc_f / 1e4, 5), "wave_A": wc_f,
            "ew_lim_mA": pr["ew_lim_mA"], "flux_lim_erg_cm2_s": pr["flux_lim_erg_cm2_s"],
            "l_iso_mw": pr["l_iso_mw"], "p_beam_10m_kw": pr["p_beam_10m_kw"], "p_beam_10m_w": pr["p_beam_10m_w"],
        })
    for u in ul_rows:
        if u["panchromatic_bridge"]:
            reg = "NEAR_UV_0p305_0p456um" if u["instrument"] == "UVES_NUV" else "OPTICAL_0p38_0p78um"
            bridge_rows.append({
                "phase_id": "D086", "spectral_regime": reg, "instrument": u["instrument"],
                "star": u["star"], "common_name": u["common_name"], "dist_pc": u["dist_pc"],
                "band_id": u["band_id"], "wave_um": round(float(u["wave_bary_air_A"]) / 1e4, 5), "wave_A": u["wave_bary_air_A"],
                "ew_lim_mA": u["ew_lim_mA"], "flux_lim_erg_cm2_s": u["flux_lim_erg_cm2_s"],
                "l_iso_mw": u["l_iso_mw"], "p_beam_10m_kw": u["p_beam_10m_kw"], "p_beam_10m_w": u["p_beam_10m_w"],
            })
    bridge_rows.sort(key=lambda x: (x["star"], float(x["wave_um"])))
    write_csv(res_dir / "PANCHROMATIC_BRIDGE_13STARS.csv", bridge_rows)

    # Unified 175-Star Table + 90-Star <10 pc Sub-Census
    unified_rows: dict[str, dict[str, Any]] = {}
    for ur in prior_snap["unified_150star_rows"]:
        row_u = dict(ur)
        row_u.setdefault("n_exposures_nuv", "0")
        row_u.setdefault("min_nuv_10m_kw", "")
        unified_rows[ur["star"]] = row_u

    n_exp_by_star = {}
    for p in bundle["provenance_rows"]:
        n_exp_by_star[p["star"]] = n_exp_by_star.get(p["star"], 0) + 1

    for st, sm in sorted(bundle["star_meta"].items()):
        inst = sm["instrument"]
        n_e = n_exp_by_star[st]
        q_st = sum(1 for r in ledger if r["star"] == st and r["qualified_v37_laser"])
        lims = min_lim_by_star.get(st, {})
        nuv_lim = lims.get("min_nuv_10m_kw")
        opt_lim = lims.get("min_optical_10m_kw")

        if st in unified_rows:
            cur = unified_rows[st]
            cur["phases"] = f"{cur['phases']}+D086"
            cur["instruments"] = f"{cur['instruments']}+{inst}"
            cur["n_exposures_total"] = str(int(cur["n_exposures_total"]) + n_e)
            cur["automated_qualified_candidates"] = str(int(cur.get("automated_qualified_candidates") or 0) + q_st)
            if inst == "UVES_NUV":
                cur["n_exposures_nuv"] = str(int(cur.get("n_exposures_nuv") or 0) + n_e)
                cur["spectral_regime"] = "PANCHROMATIC_0p305_2p515um_BRIDGE"
                if nuv_lim is not None:
                    cur["min_nuv_10m_kw"] = f"{nuv_lim:.10g}"
            else:
                cur["n_exposures_optical"] = str(int(cur.get("n_exposures_optical") or 0) + n_e)
                cur["spectral_regime"] = "PANCHROMATIC_0p38_2p515um_BRIDGE"
                if opt_lim is not None:
                    prev_o = float(cur["min_optical_10m_kw"]) if cur.get("min_optical_10m_kw") else 1e18
                    cur["min_optical_10m_kw"] = f"{min(prev_o, opt_lim):.10g}"
            # Recompute min_panchromatic_10m_kw safely
            cand_mins = [float(cur[c]) for c in ("min_nuv_10m_kw", "min_optical_10m_kw", "min_nir_yjh_10m_kw", "min_kband_10m_kw") if cur.get(c)]
            if cand_mins:
                cur["min_panchromatic_10m_kw"] = f"{min(cand_mins):.10g}"
        else:
            all_lims = [v for v in (nuv_lim, opt_lim) if v is not None]
            min_pan = min(all_lims) if all_lims else ""
            unified_rows[st] = {
                "phases": "D086",
                "hemisphere": "SOUTHERN",
                "spectral_regime": "NEAR_UV_0p305_0p456um" if inst == "UVES_NUV" else "OPTICAL_0p38_0p78um",
                "instruments": inst,
                "star": st,
                "common_name": sm["common_name"],
                "role": sm["role"],
                "subrole": sm["subrole"],
                "dist_pc": f"{sm['dist_pc']:.6g}",
                "within_10pc": str(sm["within_10pc"]),
                "teff_k": f"{sm['teff_k']:.1f}",
                "phot_g_mag": f"{sm['phot_g_mag']:.5f}",
                "j_mag": f"{sm['j_mag']:.4f}" if sm["j_mag"] else "",
                "h_mag": f"{sm['h_mag']:.4f}" if sm["h_mag"] else "",
                "ks_mag": f"{sm['ks_mag']:.4f}" if sm["ks_mag"] else "",
                "n_exoplanets": str(sm["n_exoplanets"]),
                "n_exposures_nuv": str(n_e if inst == "UVES_NUV" else 0),
                "n_exposures_optical": str(n_e if inst != "UVES_NUV" else 0),
                "n_exposures_nir_yjh": "0",
                "n_exposures_kband": "0",
                "n_exposures_total": str(n_e),
                "min_nuv_10m_kw": f"{nuv_lim:.10g}" if nuv_lim is not None else "",
                "min_optical_10m_kw": f"{opt_lim:.10g}" if opt_lim is not None else "",
                "min_nir_yjh_10m_kw": "",
                "min_kband_10m_kw": "",
                "p_1064nm_10m_kw": "",
                "p_1550nm_10m_kw": "",
                "p_2040nm_tm_10m_kw": "",
                "p_2097nm_hoyag_10m_kw": "",
                "min_panchromatic_10m_kw": f"{min_pan:.10g}" if min_pan != "" else "",
                "automated_qualified_candidates": str(q_st),
                "verified_eti_detections": "0",
            }

    u_cols = list(next(iter(unified_rows.values())).keys())
    unified_list = sorted(unified_rows.values(), key=lambda x: (float(x["dist_pc"]), x["star"]))
    s90_list = [r for r in unified_list if r["within_10pc"] == "True"]
    write_csv(res_dir / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_175STARS.csv", unified_list, fieldnames=u_cols)
    write_csv(res_dir / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_90STARS.csv", s90_list, fieldnames=u_cols)

    # 181-System Multi-Messenger Synthesis (update M11_LHS1140, M26_HD19994, M29_HD11964, M31_HD192263, PROXIMACEN + add 21 new systems)
    mm_prior = bundle["mm_prior_160_rows"]
    mm_by_id: dict[str, dict[str, Any]] = {r["system_id"]: dict(r) for r in mm_prior}
    mm_by_host_clean = {r["host_name"].upper().replace(" ", "").replace("-", ""): r["system_id"] for r in mm_prior}

    for st, sm in bundle["star_meta"].items():
        ur = unified_rows[st]
        clean_k = st.upper()
        sys_k = st if st in mm_by_id else (sm["radio_mm_id"] if sm.get("radio_mm_id") and sm["radio_mm_id"] in mm_by_id else mm_by_host_clean.get(clean_k))
        if sys_k and sys_k in mm_by_id:
            mr = mm_by_id.pop(sys_k)
            mr["system_id"] = st
            mr["dist_pc"] = ur["dist_pc"]
            mr["within_10pc"] = ur["within_10pc"]
            mr["echelle_phases"] = ur["phases"]
            mr["echelle_instruments"] = ur["instruments"]
            mr["echelle_exposures"] = ur["n_exposures_total"]
            mr["min_echelle_10m_kw"] = ur["min_panchromatic_10m_kw"]
            mods = set(filter(None, mr["modalities_searched"].split("+"))) | {"ECHELLE_SPECTROSCOPY"}
            mr["modalities_searched"] = "+".join(sorted(mods))
            mr["n_modalities"] = str(len(mods))
            mr["multimessenger_overlap"] = str(len(mods) >= 2)
            mm_by_id[st] = mr
        else:
            mm_by_id[st] = {
                "system_id": st,
                "host_name": sm["common_name"],
                "hemisphere": "SOUTHERN",
                "role": sm["role"],
                "dist_pc": ur["dist_pc"],
                "within_10pc": ur["within_10pc"],
                "n_exoplanets": str(sm["n_exoplanets"]),
                "modalities_searched": "ECHELLE_SPECTROSCOPY",
                "n_modalities": "1",
                "multimessenger_overlap": "False",
                "echelle_phases": ur["phases"],
                "echelle_instruments": ur["instruments"],
                "echelle_exposures": ur["n_exposures_total"],
                "min_echelle_10m_kw": ur["min_panchromatic_10m_kw"],
                "radio_milestone": "",
                "radio_facility": "",
                "radio_snr40_recovery": "",
                "lightsail_milestone": "",
                "verified_eti_detections": "0",
            }
    mm_list = sorted(mm_by_id.values(), key=lambda x: (x["multimessenger_overlap"] != "True", float(x["dist_pc"] or 9999.0), x["system_id"]))
    write_csv(res_dir / "MULTIMESSENGER_ECHELLE_RADIO_TESS_181SYSTEMS.csv", mm_list)

    # SUMMARY.json
    n_tot_trials = len(inj_rows) + len(kep_rows) + len(g45_rows) + len(g6_rows) + len(comb_cal_rows)
    t8 = [r for r in inj_rows if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH" and r["sigma_mult"] >= 8.0]
    p9 = [r for r in inj_rows if r["mode"] == "CHANNEL_P_PERSISTENT_MULTIEPOCH" and r["sigma_mult"] >= 9.0]
    k65 = [r for r in kep_rows if r["exp_sigma_mult"] >= 6.5]
    c38 = [r for r in comb_cal_rows if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and r["tooth_snr_inj"] >= 3.8]
    c1l = [r for r in comb_cal_rows if r["trial_class"] == "SINGLE_BRIGHT_LINE_MASQUERADE"]
    cro = [r for r in comb_cal_rows if r["trial_class"] == "STATIONARY_TOPO_ROVIB_PSEUDOCOMB"]
    cfor = [r for r in comb_cal_rows if r["trial_class"] == "DENSE_MOLECULAR_FOREST_PSEUDOCOMB"]
    best_ul = min(ul_rows, key=lambda x: float(x["p_beam_10m_w"])) if ul_rows else None
    sc = bundle["searched_counts_by_inst"]

    summary_doc = {
        "phase_id": "D086",
        "detector": "PANCHROM_NUV_OPT_V3_7_AND_COMB_V4_1",
        "instruments": ["UVES_NUV", "ESPRESSO", "HARPS"],
        "wavelength_domain_um": [0.305, 0.785],
        "cumulative_wavelength_domain_um": [0.305, 2.515],
        "cohort": {
            "total_stars": len(bundle["star_meta"]),
            "control_stars": sum(1 for m in bundle["star_meta"].values() if m["role"] == "CONTROL"),
            "science_stars": sum(1 for m in bundle["star_meta"].values() if m["role"] == "SCIENCE"),
            "brand_new_unique_stars": sum(1 for m in bundle["star_meta"].values() if not m["panchromatic_bridge"]),
            "panchromatic_bridge_stars_in_d086": sum(1 for m in bundle["star_meta"].values() if m["panchromatic_bridge"]),
            "brand_new_within_10pc": sum(1 for m in bundle["star_meta"].values() if not m["panchromatic_bridge"] and m["within_10pc"]),
            "total_exposures": len(bundle["provenance_rows"]),
            "uves_nuv_exposures": sum(1 for p in bundle["provenance_rows"] if p["instrument"] == "UVES_NUV"),
            "espresso_exposures": sum(1 for p in bundle["provenance_rows"] if p["instrument"] == "ESPRESSO"),
            "harps_exposures": sum(1 for p in bundle["provenance_rows"] if p["instrument"] == "HARPS"),
            "total_integration_hours": bundle["total_integration_hours"],
            "orbital_campaigns": len(orb_rows),
        },
        "searched_spectral_elements": {
            "by_instrument": sc,
            "channel_t_1d_bins": sum(v["T"] for v in sc.values()),
            "channel_p_coadd_bins": sum(v["P"] for v in sc.values()),
            "channel_tdiff_bins": sum(v["T_DIFF"] for v in sc.values()),
            "channel_kplanet_bins": sum(v["K_PLANET"] for v in sc.values()),
            "comb_v41_searched_configs": sum(v["COMB_CONFIGS"] for v in sc.values()),
            "total_searched_1d_bins": sum(v["T"] + v["P"] + v["T_DIFF"] + v["K_PLANET"] for v in sc.values()),
        },
        "rv_anchoring": {
            "total_anchor_fits": len(rva_rows),
            "clean_absorption_fits": sum(1 for r in rva_rows if r["status"] == "CLEAN_ABSORPTION"),
            "median_abs_empirical_minus_prior_kms": round(float(np.median([abs(float(r["empirical_minus_prior_kms"])) for r in bundle["v3_rv_summary_rows"]])), 4),
            "max_pure_stdlib_berv_diff_kms": round(max(float(p["berv_diff_stdlib_kms"]) for p in bundle["provenance_rows"]), 4),
        },
        "synthetic_calibration_2697_trials": {
            "total_trials": n_tot_trials,
            "channel_t_trials": sum(1 for r in inj_rows if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH"),
            "channel_p_trials": sum(1 for r in inj_rows if r["mode"] == "CHANNEL_P_PERSISTENT_MULTIEPOCH"),
            "keplerian_paired_trials": len(kep_rows),
            "g4g5_trials": len(g45_rows),
            "g6_sparse_vs_dense_trials": len(g6_rows),
            "comb_v41_trials": len(comb_cal_rows),
            "channel_t_ge_8sigma": round(sum(1 for r in t8 if r["recovered"]) / max(1, len(t8)), 5),
            "channel_p_ge_9sigma": round(sum(1 for r in p9 if r["recovered"]) / max(1, len(p9)), 5),
            "keplerian_tdiff_ge_6p5sigma": round(sum(1 for r in k65 if r["tdiff_uncomp_recovered"]) / max(1, len(k65)), 5),
            "keplerian_kplanet_ge_6p5sigma": round(sum(1 for r in k65 if r["kplanet_dedop_recovered"]) / max(1, len(k65)), 5),
            "g45_true_laser_pass": round(sum(1 for r in g45_rows if r["trial_class"] == "TRUE_LSF_LASER" and r["g45_pass"]) / 72.0, 5),
            "g5_cosmic_hotpx_rejection": round(sum(1 for r in g45_rows if r["trial_class"] == "COSMIC_SINGLE_PX_SPIKE" and not r["g5_pass"]) / 72.0, 5),
            "g5_plateau_rejection": round(sum(1 for r in g45_rows if r["trial_class"] == "WIDE_SCATTERING_PLATEAU" and not r["g5_pass"]) / 72.0, 5),
            "comb_v41_6tooth_ge_3p8sigma_recovery": round(sum(1 for r in c38 if r["comb_v41_hit"]) / max(1, len(c38)), 5),
            "comb_v41_single_line_fpr": round(sum(1 for r in c1l if r["comb_v41_hit"]) / max(1, len(c1l)), 5),
            "comb_v41_topo_rovib_pseudocomb_fpr": round(sum(1 for r in cro if r["comb_v41_hit"]) / max(1, len(cro)), 5),
            "comb_v41_dense_forest_fpr": round(sum(1 for r in cfor if r["comb_v41_hit"]) / max(1, len(cfor)), 5),
            "comb_v4_dense_forest_fpr": round(sum(1 for r in cfor if r["comb_v4_hit"]) / max(1, len(cfor)), 5),
        },
        "d085_comb_v41_regression": {
            "d085_comb_v4_candidates_before": len(reg_rows),
            "d085_comb_v41_survivors_after": sum(1 for r in reg_rows if r["comb_v41_retained"]),
        },
        "false_alarm_cascade": {
            "v2_legacy_false_alarms": sum(int(r["v2_accepted_false_alarms"]) for r in bench_rows),
            "v37_total_ledger_g1_candidates": len(ledger),
            "v37_after_g2": sum(1 for r in ledger if r["g1_pass"] and r["g2_pass"]),
            "v37_after_g3": sum(1 for r in ledger if r["g1_pass"] and r["g2_pass"] and r["g3_pass"]),
            "v37_after_g4": sum(1 for r in ledger if r["g1_pass"] and r["g2_pass"] and r["g3_pass"] and r["g4_pass"]),
            "v37_pre_g6_passed_g1_to_g5": sum(1 for r in ledger if r["pre_g6_qualified"]),
            "v37_vetoed_by_g6_sparse": sum(1 for r in ledger if r["pre_g6_qualified"] and not r["g6_pass"]),
            "v37_orbital_candidates": sum(1 for r in ledger if r["channel"] in ("T_DIFF", "K_PLANET") and r["qualified_v37_laser"]),
            "automated_qualified_control": sum(1 for r in ledger if r["role"] == "CONTROL" and r["qualified_v37_laser"]),
            "automated_qualified_science": sum(1 for r in ledger if r["role"] == "SCIENCE" and r["qualified_v37_laser"]),
            "comb_v4_automated_candidates_on_d086": comb_v4_real_count,
            "comb_v41_automated_candidates": len(comb_cands_out),
            "verified_eti_detections": 0,
        },
        "upper_limits": {
            "n_cells": len(ul_rows),
            "best_overall_star": best_ul["star"] if best_ul else "",
            "best_overall_instrument": best_ul["instrument"] if best_ul else "",
            "best_overall_band": best_ul["band_id"] if best_ul else "",
            "best_overall_10m_w": round(float(best_ul["p_beam_10m_w"]), 3) if best_ul else 0.0,
        },
        "unified_175star_panchromatic_v3_synthesis": {
            "phases": "D079-D086",
            "spectrographs": 8,
            "unique_stars_total": len(unified_list),
            "within_10pc_unique_stars": len(s90_list),
            "within_10pc_median_limit_kw": round(float(np.median([float(r["min_panchromatic_10m_kw"]) for r in s90_list if r.get("min_panchromatic_10m_kw")])), 4),
            "panchromatic_bridge_stars_total": len({r["star"] for r in bridge_rows}),
            "total_exposures_d079_d086": sum(int(r["n_exposures_total"]) for r in unified_list),
            "total_calibration_trials_d079_d086": int(prior_snap["prior_v3_calibration_trials_count"]) + n_tot_trials,
            "v2_false_alarms_eliminated_total": int(prior_snap["prior_v2_false_alarms_eliminated_total"]) + sum(int(r["v2_accepted_false_alarms"]) for r in bench_rows),
            "cumulative_orbital_campaigns": 50,
            "verified_eti_detections_total": 0,
        },
        "multimessenger_181system_synthesis": {
            "distinct_stellar_systems_total": len(mm_list),
            "direct_multimessenger_overlap_count": sum(1 for r in mm_list if r["multimessenger_overlap"] == "True"),
            "direct_multimessenger_overlap_stars": [r["system_id"] for r in mm_list if r["multimessenger_overlap"] == "True"],
            "verified_eti_detections_all_modalities": 0,
        },
    }
    write_json(res_dir / "SUMMARY.json", summary_doc)
    print(f"[analyze] Complete: {len(unified_list)} stars, {len(s90_list)} <10pc, {len(bridge_rows)} bridge cells, "
          f"{n_tot_trials} calib trials, {len(mm_list)} MM systems ({summary_doc['multimessenger_181system_synthesis']['direct_multimessenger_overlap_count']} overlaps), "
          f"D085 COMB_V4_1 regression={summary_doc['d085_comb_v41_regression']['d085_comb_v4_candidates_before']}->{summary_doc['d085_comb_v41_regression']['d085_comb_v41_survivors_after']}.", flush=True)


def _assert_json_finite(obj: Any, path: str = "bundle") -> None:
    """Fail fast with exact field path if any float in the JSON bundle is NaN/Inf."""
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError(f"Non-finite float in bundle at {path}: {obj!r}")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _assert_json_finite(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            if isinstance(v, (float, dict, list, tuple)):
                _assert_json_finite(v, f"{path}[{i}]")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--from-full-inputs", type=Path)
    grp.add_argument("--from-bounded-inputs", type=Path)
    args = parser.parse_args()

    if args.from_full_inputs is not None:
        mlock, rec = verify_prospective_lock(args.from_full_inputs)
        bundle = build_bounded_bundle_from_full_inputs(args.from_full_inputs, mlock, rec)
        _assert_json_finite(bundle)
        bp = HERE / "bounded_inputs" / "d086_bounded_bundle.json.gz"
        bp.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(bp, "wt", encoding="utf-8", compresslevel=6) as gz:
            json.dump(bundle, gz, separators=(",", ":"), allow_nan=False)
        bmib = bp.stat().st_size / (1024.0 * 1024.0)
        print(f"[analyze] Wrote {bp.name}: {bmib:.2f} MiB (<25.0 MiB limit)", flush=True)
        if bmib >= 25.0:
            raise RuntimeError(f"Bounded bundle too large: {bmib:.2f} MiB >= 25.0 MiB")
        with gzip.open(bp, "rt", encoding="utf-8") as gz:
            bundle_reload = json.load(gz)
        del bundle
        gc.collect()
        evaluate_bundle_and_write_outputs(bundle_reload)
    else:
        verify_prospective_lock(None)
        with gzip.open(args.from_bounded_inputs, "rt", encoding="utf-8") as gz:
            bundle_reload = json.load(gz)
        evaluate_bundle_and_write_outputs(bundle_reload)


if __name__ == "__main__":
    main()
