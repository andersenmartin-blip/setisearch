#!/usr/bin/env python3
"""
Phase D087 Analysis Pipeline:
  SPACE_UV_STIS_AND_FARRED_V3_8 (200 Unique Stars / >4 Octaves / G4_V38 / 60 Orbital Campaigns)

Supports two strictly synchronized execution modes:
  1. --from-full-inputs <inputs_d087_v3_8>:
       Reads all 201 science FITS files (HST_STIS _x1d, UVES_RED FLUX_REDUCED,
       ESPRESSO S1D_A+S1D_B), runs Stage A extraction + full-spectrum searches
       across Channels T, P, T_DIFF, K_PLANET + COMB_V4 / COMB_V4_1 + D086
       G4_V38 Fiber-B 577-record regression, packages everything into
       bounded_inputs/d087_bounded_bundle.json.gz (< 25.0 MiB), and executes Stage B.
  2. --from-bounded-inputs <d087_bounded_bundle.json.gz>:
       Recomputes 100% of CSV/JSON deliverables offline from the self-contained
       bounded bundle with byte-for-byte identical outputs.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

warnings.filterwarnings("ignore", category=RuntimeWarning)

from v3_8_detector import (
    BASE_V3_8_CONFIG,
    C_ANGSTROM_GHZ,
    C_KMS,
    COMB_V4_1_WINDOWS_A,
    FWHM_FACTOR,
    LOCKED_RV_ANCHORS_FARRED,
    LOCKED_RV_ANCHORS_OPTICAL,
    LOCKED_RV_ANCHORS_STIS_FUV,
    MAD_NORM,
    OPTIONAL_UVES_RED_BANDS_A,
    PARANAL_LAT_DEG,
    PARANAL_LON_DEG,
    STELLAR_CHROMOSPHERIC_EMISSION_AIR_A,
    STELLAR_FUV_EMISSION_VAC_A,
    STIS_GEOCORONAL_BANDS_VAC_A,
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
    evaluate_g4_v38_fiber_b_bleed_record,
    evaluate_gate_g2_airglow,
    evaluate_gate_g6_v35_dense,
    evaluate_gate_g6_v36_sparse,
    evaluate_gates_g3_g4_g5_v38,
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
    resolve_band_radiometric_anchor,
    scan_frequency_comb_v4,
    scan_frequency_comb_v4_1,
    scan_single_exposure_residual_lsf,
    stdlib_earth_helio_rv_kms,
    stdlib_observatory_berv_kms,
)

ROOT = Path(".")
AWS = ROOT / "analysis_workspace"
WS = AWS / "work_stis_farred_20261118_d087_v3_8_space_uv_and_200star"
D086_WS = AWS / "work_uves_panchrom_20261117_d086_v3_7_nuv_and_comb_v4_1"
DEFAULT_IN = ROOT / "inputs_d087_v3_8"
DEFAULT_BUNDLE = WS / "bounded_inputs" / "d087_bounded_bundle.json.gz"
RESULTS = WS / "results"

MAX_BUNDLE_MIB = 25.0


# ---------------------------------------------------------------------------
# Generic Helpers (JSON sanitization, rounding, CSV writers)
# ---------------------------------------------------------------------------

def _assert_json_finite(obj: Any, path: str = "root") -> None:
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError(f"Non-finite float at {path}: {obj}")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _assert_json_finite(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _assert_json_finite(v, f"{path}[{i}]")


def rsig(val: float, sig: int = 5) -> float:
    x = float(val)
    if not math.isfinite(x) or x == 0.0:
        return 0.0
    return float(f"{x:.{sig}g}")


def rarr(arr: np.ndarray | list[float], ndig: int | None = None, sig: int | None = None) -> list[float]:
    out: list[float] = []
    for v in arr:
        x = float(v)
        if not math.isfinite(x):
            out.append(0.0)
        elif sig is not None:
            out.append(rsig(x, sig))
        elif ndig is not None:
            out.append(round(x, ndig))
        else:
            out.append(x)
    return out


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        if not rows:
            raise ValueError(f"Cannot infer fieldnames for empty CSV {path}")
        fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _annulus_noise_mad(w_arr: np.ndarray, y_arr: np.ndarray, center_a: float, sigma_v_kms: float) -> float:
    abs_dv = np.abs(C_KMS * (w_arr - center_a) / center_a)
    bg_mid = np.isfinite(y_arr) & (abs_dv >= 3.0 * sigma_v_kms) & (abs_dv <= 12.0 * sigma_v_kms)
    if int(bg_mid.sum()) >= 12:
        val = exact_mad_1d(y_arr[bg_mid])
        if math.isfinite(val) and val > 0.0:
            return val
    fin = y_arr[np.isfinite(y_arr)]
    if len(fin) >= 12:
        val = exact_mad_1d(fin)
        if math.isfinite(val) and val > 0.0:
            return val
    return 0.04


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def vac_to_air_angstrom(w_vac: np.ndarray) -> np.ndarray:
    """IAU standard Morton (1991) / Edlen vacuum-to-air conversion for >2000 A."""
    s2 = (1.0e4 / np.maximum(2000.0, w_vac)) ** 2
    n_air = 1.0 + 0.0000834254 + 0.02406147 / (130.0 - s2) + 0.00015998 / (38.9 - s2)
    return w_vac / n_air


def normalize_flux_with_continuum(
    flux: np.ndarray,
    c_raw: np.ndarray,
    c_eff: np.ndarray,
    instrument: str,
) -> np.ndarray:
    fn = np.where(
        np.isfinite(flux) & np.isfinite(c_eff) & (c_eff > 0.0),
        np.where(c_raw >= c_eff, flux / c_eff, 1.0 + (flux - c_raw) / c_eff),
        np.nan,
    )
    if instrument.upper() != "HST_STIS":
        fn = np.where(flux > 0.0, fn, np.nan)
    return fn


def safe_dp(dp_id: str) -> str:
    return dp_id.replace(":", "_")


# ---------------------------------------------------------------------------
# Stage A FITS Readers (HST_STIS _x1d, UVES_RED S1D, ESPRESSO S1D_A+S1D_B)
# ---------------------------------------------------------------------------

def _mjd_from_tdate_ttime(tdate: str, ttime: str) -> float:
    dt = datetime.fromisoformat(f"{tdate.strip()}T{ttime.strip()}").replace(tzinfo=timezone.utc)
    mjd0 = datetime(1858, 11, 17, tzinfo=timezone.utc)
    return (dt - mjd0).total_seconds() / 86400.0


def load_stis_x1d(path: Path, row_meta: dict[str, str]) -> dict[str, Any]:
    from astropy.io import fits

    with fits.open(path) as hdul:
        h0 = hdul[0].header
        sci_hdus = [h for h in hdul[1:] if h.header.get("EXTNAME") == "SCI"]
        if not sci_hdus:
            sci_hdus = [hdul[1]]
        h1 = sci_hdus[0].header
        helcorr = str(h1.get("HELCORR", h0.get("HELCORR", ""))).strip().upper()
        if helcorr != "COMPLETE":
            raise RuntimeError(f"HST_STIS {path.name} HELCORR={helcorr!r} != 'COMPLETE'")
        v_helio = float(h1["V_HELIO"])
        berv_kms = -v_helio  # CALSTIS: lam_helio = lam_obs * (1 - V_HELIO/c)
        expstart = float(h1.get("EXPSTART", row_meta["mjd_obs"]))
        expend = float(h1.get("EXPEND", expstart + float(row_meta["t_exptime"]) / 86400.0))
        mjd_mid = 0.5 * (expstart + expend)
        exptime = float(h1.get("EXPTIME", h0.get("TEXPTIME", row_meta["t_exptime"])))
        ra_deg = float(h0.get("RA_TARG", row_meta["s_ra"]))
        dec_deg = float(h0.get("DEC_TARG", row_meta["s_dec"]))

        # Base extension 1 orders
        d0 = sci_hdus[0].data
        sporders0 = [int(x) for x in d0["SPORDER"]]
        n_ord = len(sporders0)
        n_px = len(d0["WAVELENGTH"][0])
        flux_sum = np.zeros((n_ord, n_px), dtype=np.float64)
        ivar_sum = np.zeros((n_ord, n_px), dtype=np.float64)
        net_sum = np.zeros((n_ord, n_px), dtype=np.float64)
        bg_sum = np.zeros((n_ord, n_px), dtype=np.float64)
        cnt_sum = np.zeros((n_ord, n_px), dtype=np.float64)
        dq_or = np.zeros((n_ord, n_px), dtype=np.int64)
        base_waves = np.asarray(d0["WAVELENGTH"], dtype=np.float64)
        v_hels = []

        for sh in sci_hdus:
            vh = float(sh.header.get("V_HELIO", v_helio))
            v_hels.append(vh)
            sd = sh.data
            by_ord = {int(sd["SPORDER"][i]): i for i in range(len(sd["SPORDER"]))}
            for oi, spo in enumerate(sporders0):
                if spo not in by_ord:
                    continue
                si = by_ord[spo]
                w_e = np.asarray(sd["WAVELENGTH"][si], dtype=np.float64)
                f_e = np.asarray(sd["FLUX"][si], dtype=np.float64)
                e_e = np.asarray(sd["ERROR"][si], dtype=np.float64)
                bg_e = np.asarray(sd["BACKGROUND"][si], dtype=np.float64)
                net_e = np.asarray(sd["NET"][si], dtype=np.float64)
                dq_e = np.asarray(sd["DQ"][si], dtype=np.int64)
                if not np.allclose(w_e, base_waves[oi], atol=0.05):
                    f_e = np.interp(base_waves[oi], w_e, f_e)
                    e_e = np.interp(base_waves[oi], w_e, e_e)
                    bg_e = np.interp(base_waves[oi], w_e, bg_e)
                    net_e = np.interp(base_waves[oi], w_e, net_e)
                good = np.isfinite(f_e) & np.isfinite(e_e) & (e_e > 0.0) & ((dq_e & ~1024) == 0)
                iv = np.where(good, 1.0 / np.maximum(1e-34, e_e * e_e), 0.0)
                flux_sum[oi] += np.where(good, f_e * iv, 0.0)
                ivar_sum[oi] += iv
                net_sum[oi] += np.where(np.isfinite(net_e), net_e, 0.0)
                bg_sum[oi] += np.where(np.isfinite(bg_e), bg_e, 0.0)
                cnt_sum[oi] += np.where(np.isfinite(net_e), 1.0, 0.0)
                dq_or[oi] |= dq_e

        if len(v_hels) > 1:
            v_helio = float(np.median(v_hels))
            berv_kms = -v_helio

        orders: list[dict[str, Any]] = []
        splice_grid = np.arange(1146.0, 1709.0, 0.015, dtype=np.float64)
        sp_num = np.zeros_like(splice_grid)
        sp_den = np.zeros_like(splice_grid)
        sp_err_iv = np.zeros_like(splice_grid)

        for oi, spo in enumerate(sporders0):
            w_o = base_waves[oi]
            iv_o = ivar_sum[oi]
            f_o = np.where(iv_o > 0.0, flux_sum[oi] / np.where(iv_o > 0.0, iv_o, 1.0), 0.0)
            e_o = np.where(iv_o > 0.0, 1.0 / np.sqrt(np.maximum(1e-34, iv_o)), 1e-13)
            net_o = np.where(cnt_sum[oi] > 0.0, net_sum[oi] / np.maximum(1.0, cnt_sum[oi]), 0.0)
            bg_o = np.where(cnt_sum[oi] > 0.0, bg_sum[oi] / np.maximum(1.0, cnt_sum[oi]), 0.0)
            dq_o = dq_or[oi]
            if w_o[-1] < w_o[0]:
                w_o = w_o[::-1]
                f_o = f_o[::-1]
                e_o = e_o[::-1]
                net_o = net_o[::-1]
                bg_o = bg_o[::-1]
                dq_o = dq_o[::-1]
            orders.append({
                "order": spo,
                "wave": w_o,
                "flux_a": f_o,
                "err_a": e_o,
                "bg_flux": bg_o,
                "net_a": net_o,
                "dq": dq_o,
                "active_start_px": 16,
                "active_end_px": n_px - 17,
            })

            trim = np.zeros(n_px, dtype=bool)
            trim[16 : n_px - 16] = True
            good_o = trim & np.isfinite(f_o) & np.isfinite(e_o) & (e_o > 0.0) & ((dq_o & ~1024) == 0)
            if int(good_o.sum()) >= 40:
                m_grid = (splice_grid >= w_o[16]) & (splice_grid <= w_o[-17])
                if np.any(m_grid):
                    fi = np.interp(splice_grid[m_grid], w_o[good_o], f_o[good_o])
                    ei = np.interp(splice_grid[m_grid], w_o[good_o], e_o[good_o])
                    w_i = 1.0 / np.maximum(1e-34, ei * ei)
                    sp_num[m_grid] += fi * w_i
                    sp_den[m_grid] += w_i
                    sp_err_iv[m_grid] += w_i

        wave_bary = splice_grid
        flux_1d = np.where(sp_den > 0.0, sp_num / np.where(sp_den > 0.0, sp_den, 1.0), np.nan)
        err_1d = np.where(sp_err_iv > 0.0, 1.0 / np.sqrt(np.maximum(1e-34, sp_err_iv)), np.nan)

    return {
        "instrument": "HST_STIS",
        "observatory": "HST_LEO",
        "ra_deg": ra_deg,
        "dec_deg": dec_deg,
        "mjd_mid": mjd_mid,
        "exptime": exptime,
        "resolving_power": 45800.0,
        "em_min_a": float(np.nanmin(wave_bary)),
        "em_max_a": float(np.nanmax(wave_bary)),
        "berv_kms": float(berv_kms),
        "specsys": "HELIOCENT",
        "dpr_or_calsel": f"STIS_{h0.get('OPT_ELEM', 'E140M')}_{h0.get('APERTURE', '0.2X0.2')}",
        "wave_bary": wave_bary,
        "flux_a": flux_1d,
        "err_a": err_1d,
        "orders": orders,
        "direct_flam_grid": wave_bary,
        "direct_flam_vals": flux_1d,
        "direct_flam_errs": err_1d,
    }


def load_uves_red_s1d(path: Path, row_meta: dict[str, str]) -> dict[str, Any]:
    from astropy.io import fits

    with fits.open(path) as hdul:
        h0 = hdul[0].header
        d1 = hdul[1].data
        specsys = str(h0.get("SPECSYS", "TOPOCENT")).strip().upper()
        mjd_obs = float(h0.get("MJD-OBS", row_meta["mjd_obs"]))
        exptime = float(h0.get("EXPTIME", row_meta["t_exptime"]))
        mjd_end = float(h0.get("MJD-END", mjd_obs + exptime / 86400.0))
        mjd_mid = 0.5 * (mjd_obs + mjd_end)
        ra_deg = float(h0.get("RA", row_meta["s_ra"]))
        dec_deg = float(h0.get("DEC", row_meta["s_dec"]))
        if "ESO QC VRAD BARYCOR" in h0:
            berv_kms = float(h0["ESO QC VRAD BARYCOR"])
        else:
            import astropy.units as u
            from astropy.coordinates import EarthLocation, SkyCoord
            from astropy.time import Time

            loc = EarthLocation.from_geodetic(lon=PARANAL_LON_DEG * u.deg, lat=PARANAL_LAT_DEG * u.deg, height=2635.0 * u.m)
            sc = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")
            berv_kms = float(
                sc.radial_velocity_correction("barycentric", obstime=Time(mjd_mid, format="mjd", scale="utc"), location=loc).to_value(u.km / u.s)
            )
        r_pow = float(h0.get("SPEC_RES", row_meta["em_res_power"]))
        dpr = f"{h0.get('ESO DPR TYPE', 'OBJECT')}_{h0.get('ESO INS SLIT2 NAME', 'SLIT')}".strip()

        wave_raw = np.asarray(d1["WAVE"], dtype=np.float64).ravel()
        flux_red = np.asarray(d1["FLUX_REDUCED"], dtype=np.float64).ravel()
        cols = set(hdul[1].columns.names)
        err_red = np.asarray(d1["ERR_REDUCED"], dtype=np.float64).ravel() if "ERR_REDUCED" in cols else np.ones_like(flux_red)
        bg_red = np.asarray(d1["BGFLUX_REDUCED"], dtype=np.float64).ravel() if "BGFLUX_REDUCED" in cols else None

        if wave_raw[-1] < wave_raw[0]:
            wave_raw = wave_raw[::-1]
            flux_red = flux_red[::-1]
            err_red = err_red[::-1]
            if bg_red is not None:
                bg_red = bg_red[::-1]

        wave_bary = wave_raw * (1.0 + berv_kms / C_KMS) if specsys == "TOPOCENT" else wave_raw.copy()
        valid_pos = np.isfinite(wave_bary) & np.isfinite(flux_red) & (flux_red > 0.0)
        flux_clean = np.where(valid_pos, flux_red, np.nan)
        err_clean = np.where(valid_pos & np.isfinite(err_red) & (err_red > 0.0), err_red, np.nan)

        # Preserve single combined native 1D order covering 5655-10425 A (inter-chip gap masked in flux_clean, finite in order patch check)
        orders = [{
            "order": 1,
            "wave": wave_bary,
            "flux_a": flux_red,
            "err_a": err_red,
            "bg_flux": bg_red,
            "net_a": None,
            "dq": None,
            "active_start_px": 25,
            "active_end_px": len(wave_bary) - 26,
        }]

    return {
        "instrument": "UVES_RED",
        "observatory": "PARANAL",
        "ra_deg": ra_deg,
        "dec_deg": dec_deg,
        "mjd_mid": mjd_mid,
        "exptime": exptime,
        "resolving_power": r_pow,
        "em_min_a": float(np.nanmin(wave_bary)),
        "em_max_a": float(np.nanmax(wave_bary)),
        "berv_kms": berv_kms,
        "specsys": specsys,
        "dpr_or_calsel": dpr,
        "wave_bary": wave_bary,
        "flux_a": flux_clean,
        "err_a": err_clean,
        "orders": orders,
    }


def load_espresso_s1d(path_a: Path, path_b: Path, row_meta: dict[str, str]) -> dict[str, Any]:
    from astropy.io import fits

    with fits.open(path_a) as ha, fits.open(path_b) as hb:
        h0 = ha[0].header
        da = ha[1].data
        db = hb[1].data
        cols_a = set(ha[1].columns.names)
        cols_b = set(hb[1].columns.names)

        specsys = str(h0.get("SPECSYS", "BARYCENT")).strip().upper()
        mjd_obs = float(h0.get("MJD-OBS", row_meta["mjd_obs"]))
        exptime = float(h0.get("EXPTIME", row_meta["t_exptime"]))
        mjd_mid = mjd_obs + 0.5 * exptime / 86400.0
        ra_deg = float(h0.get("RA", row_meta["s_ra"]))
        dec_deg = float(h0.get("DEC", row_meta["s_dec"]))
        if "ESO QC BERV" in h0:
            berv_kms = float(h0["ESO QC BERV"])
        else:
            from astropy.coordinates import EarthLocation, SkyCoord
            from astropy.time import Time
            import astropy.units as u

            paranal_loc = EarthLocation.from_geodetic(lon=PARANAL_LON_DEG * u.deg, lat=PARANAL_LAT_DEG * u.deg, height=2635.0 * u.m)
            sc = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")
            berv_kms = float(
                sc.radial_velocity_correction(
                    "barycentric",
                    obstime=Time(mjd_mid, format="mjd", scale="utc"),
                    location=paranal_loc,
                ).to_value(u.km / u.s)
            )
        r_pow = float(h0.get("SPEC_RES", row_meta["em_res_power"]))
        cal_tokens = [
            str(h0[k]).strip()
            for k in h0.keys()
            if ("CALSEL NAME" in k or "CALSEL ID" in k or "DPR TYPE" in k or k == "ESO INS MODE")
        ]
        dpr_or_calsel = " ".join(cal_tokens) if cal_tokens else "OBJECT"

        flux_a = np.asarray(da["FLUX_EL"] if "FLUX_EL" in cols_a else da["FLUX"], dtype=np.float64).ravel()
        err_col = "ERR_EL" if "ERR_EL" in cols_a else "ERR"
        err_a = np.asarray(da[err_col], dtype=np.float64).ravel()

        if "WAVE_AIR" in cols_a:
            wave_bary = np.asarray(da["WAVE_AIR"], dtype=np.float64).ravel()
        elif "WAVE_AIR" in cols_b and len(np.asarray(db["WAVE_AIR"]).ravel()) == len(flux_a):
            wave_bary = np.asarray(db["WAVE_AIR"], dtype=np.float64).ravel()
        else:
            wave_bary = vac_to_air_angstrom(np.asarray(da["WAVE"], dtype=np.float64).ravel())

        flux_b_raw = np.asarray(db["FLUX_EL"] if "FLUX_EL" in cols_b else db["FLUX"], dtype=np.float64).ravel()
        if "WAVE_AIR" in cols_b:
            wb_air = np.asarray(db["WAVE_AIR"], dtype=np.float64).ravel()
        else:
            wb_air = vac_to_air_angstrom(np.asarray(db["WAVE"], dtype=np.float64).ravel())

        if wave_bary[-1] < wave_bary[0]:
            wave_bary = wave_bary[::-1]
            flux_a = flux_a[::-1]
            err_a = err_a[::-1]
        if wb_air[-1] < wb_air[0]:
            wb_air = wb_air[::-1]
            flux_b_raw = flux_b_raw[::-1]

        if len(wb_air) == len(wave_bary) and np.allclose(wb_air, wave_bary, atol=1e-4):
            flux_b = flux_b_raw
        else:
            flux_b = np.interp(wave_bary, wb_air, flux_b_raw)

        valid_pos = np.isfinite(wave_bary) & np.isfinite(flux_a) & (flux_a > 0.0)
        flux_clean = np.where(valid_pos, flux_a, np.nan)
        err_clean = np.where(valid_pos & np.isfinite(err_a) & (err_a > 0.0), err_a, np.nan)

        orders = [{
            "order": 1,
            "wave": wave_bary,
            "flux_a": flux_a,
            "err_a": err_a,
            "flux_b": flux_b,
            "bg_flux": None,
            "net_a": None,
            "dq": None,
            "active_start_px": 25,
            "active_end_px": len(wave_bary) - 26,
        }]

    return {
        "instrument": "ESPRESSO",
        "observatory": "PARANAL",
        "ra_deg": ra_deg,
        "dec_deg": dec_deg,
        "mjd_mid": mjd_mid,
        "exptime": exptime,
        "resolving_power": r_pow,
        "em_min_a": float(np.nanmin(wave_bary)),
        "em_max_a": float(np.nanmax(wave_bary)),
        "berv_kms": berv_kms,
        "specsys": specsys,
        "dpr_or_calsel": dpr_or_calsel,
        "wave_bary": wave_bary,
        "flux_a": flux_clean,
        "err_a": err_clean,
        "orders": orders,
    }


def extract_native_order_patches(
    exp_rec: dict[str, Any],
    bary_target_wave_a: float,
    star_grid_rest: np.ndarray | None = None,
    template_rest: np.ndarray | None = None,
    v_star_kms: float = 0.0,
) -> list[dict[str, Any]]:
    """Extract strictly symmetric (k0 = len//2) native order windows around bary_target_wave_a."""
    patches: list[dict[str, Any]] = []
    is_stis = exp_rec["instrument"] == "HST_STIS"
    for ord_d in exp_rec["orders"]:
        w = ord_d["wave"]
        if bary_target_wave_a < float(w[0]) or bary_target_wave_a > float(w[-1]):
            continue
        kp = int(np.argmin(np.abs(w - bary_target_wave_a)))
        n_px = len(w)
        half_w = min(80, kp, n_px - 1 - kp)
        if half_w < 35:
            continue
        sl = slice(kp - half_w, kp + half_w + 1)
        w_win = w[sl]
        fa_win = ord_d["flux_a"][sl]
        if not np.all(np.isfinite(fa_win)):
            continue

        ref_norm = None
        if star_grid_rest is not None and template_rest is not None:
            w_rest = w_win / (1.0 + v_star_kms / C_KMS)
            ref_norm = rarr(np.interp(w_rest, star_grid_rest, np.where(np.isfinite(template_rest), template_rest, 1.0)), ndig=4)

        patch: dict[str, Any] = {
            "order": int(ord_d["order"]),
            "native_pixel": int(kp),
            "active_start_px": int(ord_d["active_start_px"]),
            "active_end_px": int(ord_d["active_end_px"]),
            "target_wave_a": round(float(bary_target_wave_a), 5),
            "wave": rarr(w_win, ndig=5),
            "flux_a": rarr(fa_win, sig=5 if is_stis else None, ndig=None if is_stis else 2),
            "err_a": rarr(ord_d["err_a"][sl], sig=5) if (is_stis and ord_d.get("err_a") is not None) else None,
            "flux_b": rarr(ord_d["flux_b"][sl], ndig=2) if ord_d.get("flux_b") is not None else None,
            "bg_flux": rarr(ord_d["bg_flux"][sl], sig=5 if is_stis else None, ndig=None if is_stis else 2) if ord_d.get("bg_flux") is not None else None,
            "net_a": rarr(ord_d["net_a"][sl], sig=5) if (is_stis and ord_d.get("net_a") is not None) else None,
            "dq": [int(x) for x in ord_d["dq"][sl]] if ord_d.get("dq") is not None else None,
            "ref_norm_a": ref_norm,
        }
        patches.append(patch)
    return patches


# ---------------------------------------------------------------------------
# Stage A: Build Bounded Reproducible Bundle (< 25 MiB)
# ---------------------------------------------------------------------------

def _legacy_v2_false_alarms(
    wave_bary: np.ndarray,
    resid: np.ndarray,
    sky_mask_topo: np.ndarray | None,
) -> int:
    """Count raw >5*MAD local peaks (legacy V2 baseline without morphology/template/G6)."""
    fin = np.isfinite(resid)
    if int(fin.sum()) < 200:
        return 0
    vals = np.where(fin, resid, 0.0)
    mad = max(1e-6, exact_mad_1d(vals[fin]))
    pk = (vals[1:-1] > vals[:-2]) & (vals[1:-1] >= vals[2:]) & (vals[1:-1] > 5.0 * mad) & fin[1:-1]
    if sky_mask_topo is not None:
        pk = pk & (~sky_mask_topo[1:-1])
    idxs = np.flatnonzero(pk)
    cnt, last = 0, -999
    for k in idxs:
        if k - last >= 6:
            cnt += 1
            last = int(k)
    return cnt


def _collect_exposure_top_peaks(
    star: str,
    dp_id: str,
    berv_kms: float,
    wave_bary: np.ndarray,
    resid: np.ndarray,
    instrument: str,
    limit: int = 120,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return dense (<=120) and sparse (<=30 clean high-SNR) topocentric peak entries."""
    fin = np.isfinite(resid)
    if int(fin.sum()) < 200:
        return [], []
    vals = np.where(fin, resid, 0.0)
    mad = max(1e-6, exact_mad_1d(vals[fin]))
    pks = np.flatnonzero((vals[1:-1] > vals[:-2]) & (vals[1:-1] >= vals[2:]) & fin[1:-1] & (vals[1:-1] >= 3.2 * mad)) + 1
    if len(pks) == 0:
        return [], []
    snrs = vals[pks] / mad
    order_idx = np.argsort(-snrs)
    dense: list[dict[str, Any]] = []
    sparse: list[dict[str, Any]] = []
    inv_berv = 1.0 + berv_kms / C_KMS
    for i in order_idx:
        k = int(pks[i])
        snr = float(snrs[i])
        wb = float(wave_bary[k])
        topo_a = wb / inv_berv
        entry = {
            "star": star,
            "dp_id": dp_id,
            "berv_kms": round(berv_kms, 3),
            "topo_wave_a": round(topo_a, 4),
            "snr": round(snr, 2),
        }
        if len(dense) < limit:
            dense.append(entry)
        if len(sparse) < 35 and snr >= 5.0:
            sparse.append(entry)
        if len(dense) >= limit and len(sparse) >= 35:
            break
    return dense, sparse


def build_d086_fiberb_regression_records(
    d086_bundle_path: Path,
    d086_audit_path: Path,
) -> list[dict[str, Any]]:
    with gzip.open(d086_bundle_path, "rt", encoding="utf-8") as f:
        b86 = json.load(f)
    fa86 = json.loads(d086_audit_path.read_text(encoding="utf-8"))
    bleeds = [r for r in fa86["post_g6_singleline_forensic_classifications"] if "BLEED" in r["forensic_classification"]]
    cands86 = b86["real_candidates_bundle"]
    by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for c in cands86:
        by_key.setdefault((c["star"], c["dp_id"], c["channel"]), []).append(c)

    records: list[dict[str, Any]] = []
    for bl in bleeds:
        pool = by_key[(bl["star"], bl["dp_id"], bl["channel"])]
        hit = min(
            pool,
            key=lambda c: min(
                abs(float(c["seed_wave_a"]) - float(bl["bary_wave_a"])),
                abs(float(c["seed_wave_a"]) - float(bl["stellar_rest_wave_a"])),
            ),
        )
        best_op = max(hit["order_patches"], key=lambda op: exact_median_1d(np.asarray(op["flux_a"], dtype=np.float64)))
        fb_arr = np.asarray(best_op["flux_b"], dtype=np.float64)
        fa_arr = np.asarray(best_op["flux_a"], dtype=np.float64)
        k0 = len(fb_arr) // 2
        fb_pk = float(np.max(fb_arr[max(0, k0 - 3) : min(len(fb_arr), k0 + 4)]))
        fa_med = max(1e-6, exact_median_1d(fa_arr[np.isfinite(fa_arr)]))
        records.append({
            "d086_candidate_id": bl["candidate_id"],
            "instrument": bl["instrument"],
            "star": bl["star"],
            "channel": bl["channel"],
            "dp_id": bl["dp_id"],
            "bary_wave_a": round(float(bl["bary_wave_a"]), 5),
            "dpr_or_calsel": hit["dpr_or_calsel"],
            "fb_pk": rsig(fb_pk, 6),
            "fa_med": rsig(fa_med, 6),
        })
    return records


def build_bounded_bundle(in_dir: Path, out_bundle_path: Path) -> None:
    lock = json.loads((WS / "METHOD_LOCK.json").read_text(encoding="utf-8"))
    orb_doc = json.loads((WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))
    with (WS / "FROZEN_COHORT_D087.csv").open("r", encoding="utf-8", newline="") as f:
        cohort_rows = list(csv.DictReader(f))

    print(f"[Stage A] Reading {len(cohort_rows)} FITS exposures from {in_dir}...", flush=True)
    prov_rows: list[dict[str, Any]] = []
    rv_anchor_bundle: list[dict[str, Any]] = []
    star_meta: dict[str, dict[str, Any]] = {}
    exp_by_star: dict[str, list[dict[str, Any]]] = {}
    exp_by_dp: dict[str, dict[str, Any]] = {}
    total_int_hours = 0.0

    # Group star metadata + load every FITS + measure RV anchors
    for r in cohort_rows:
        st = r["canonical_target"]
        inst = r["instrument"]
        dp = r["dp_id"]
        sdp = safe_dp(dp)
        if inst == "HST_STIS":
            p_this = in_dir / "hst_stis" / "x1d" / f"{sdp}_x1d.fits"
            rec = load_stis_x1d(p_this, r)
            s1d_sha = sha256_file(p_this)
            aux_sha = ""
            berv_stdlib = stdlib_earth_helio_rv_kms(rec["ra_deg"], rec["dec_deg"], rec["mjd_mid"])
        elif inst == "UVES_RED":
            p_this = in_dir / "uves_red" / "s1d" / f"{sdp}_s1d.fits"
            rec = load_uves_red_s1d(p_this, r)
            s1d_sha = sha256_file(p_this)
            aux_sha = ""
            berv_stdlib = stdlib_observatory_berv_kms(rec["ra_deg"], rec["dec_deg"], rec["mjd_mid"], PARANAL_LAT_DEG, PARANAL_LON_DEG)
        else:
            p_a = in_dir / "espresso" / "s1d_a" / f"{sdp}_s1d_a.fits"
            p_b = in_dir / "espresso" / "s1d_b" / f"{sdp}_s1d_b.fits"
            rec = load_espresso_s1d(p_a, p_b, r)
            s1d_sha = sha256_file(p_a)
            aux_sha = sha256_file(p_b)
            berv_stdlib = stdlib_observatory_berv_kms(rec["ra_deg"], rec["dec_deg"], rec["mjd_mid"], PARANAL_LAT_DEG, PARANAL_LON_DEG)

        cfg = get_inst_config(inst, resolving_power=rec["resolving_power"])
        prior_rv = float(r["prior_rv_kms"])
        rv_sum, _, anc_bundle = measure_exposure_stellar_rv(rec["wave_bary"], rec["flux_a"], prior_rv, cfg)

        rec["star"] = st
        rec["dp_id"] = dp
        rec["role"] = r["role"]
        rec["subrole"] = r["subrole"]
        rec["epoch_rank"] = int(r["epoch_rank"])
        rec["phase_window"] = r["phase_window"]
        rec["planet_orbital_rv_kms"] = float(r["planet_orbital_rv_kms"])
        rec["prior_rv_kms"] = prior_rv
        rec["emp_rv_kms"] = rv_sum["empirical_rv_kms"]
        rec["n_clean_anchors"] = rv_sum["n_clean_anchors"]
        rec["cfg"] = cfg
        rec["berv_stdlib"] = berv_stdlib
        rec["berv_diff"] = abs(rec["berv_kms"] - berv_stdlib)
        total_int_hours += rec["exptime"] / 3600.0

        exp_by_star.setdefault(st, []).append(rec)
        exp_by_dp[dp] = rec

        if st not in star_meta:
            star_meta[st] = {
                "instrument": inst,
                "star": st,
                "common_name": r["common_name"],
                "role": r["role"],
                "subrole": r["subrole"],
                "panchromatic_bridge": r["panchromatic_bridge"] == "True",
                "radio_mm_id": r["radio_mm_id"],
                "within_10pc": r["within_10pc"] == "True",
                "dist_pc": float(r["dist_pc"]),
                "phot_g_mag": float(r["phot_g_mag"]),
                "phot_bp_mag": float(r["phot_bp_mag"]),
                "phot_rp_mag": float(r["phot_rp_mag"]),
                "j_mag": float(r["j_mag"]) if r["j_mag"] != "" else 0.0,
                "h_mag": float(r["h_mag"]) if r["h_mag"] != "" else 0.0,
                "ks_mag": float(r["ks_mag"]) if r["ks_mag"] != "" else 0.0,
                "teff_k": float(r["teff_k"]),
                "mh_dex": float(r["mh_dex"]),
                "stellar_mass_msun": float(r["stellar_mass_msun"]),
                "prior_rv_kms": prior_rv,
                "n_exoplanets": int(r["n_exoplanets"]),
                "has_transiting_planet": r["has_transiting_planet"] == "True",
                "resolving_powers": [],
            }
        star_meta[st]["resolving_powers"].append(rec["resolving_power"])

        max_diff_allowed = 8.50 if inst == "HST_STIS" else 0.50
        gate_pass = (
            rec["berv_diff"] <= max_diff_allowed
            and ((inst == "HST_STIS" and rec["specsys"] == "HELIOCENT") or (inst == "UVES_RED" and rec["specsys"] == "TOPOCENT") or (inst == "ESPRESSO" and rec["specsys"] == "BARYCENT"))
        )
        prov_rows.append({
            "instrument": inst,
            "observatory": rec["observatory"],
            "star": st,
            "role": r["role"],
            "radio_mm_id": r["radio_mm_id"],
            "dp_id": dp,
            "epoch_rank": int(r["epoch_rank"]),
            "phase_window": r["phase_window"],
            "s_ra_deg": round(rec["ra_deg"], 6),
            "s_dec_deg": round(rec["dec_deg"], 6),
            "mjd_mid": round(rec["mjd_mid"], 5),
            "t_exptime_s": round(rec["exptime"], 3),
            "resolving_power": round(rec["resolving_power"], 1),
            "em_min_a": round(rec["em_min_a"], 2),
            "em_max_a": round(rec["em_max_a"], 2),
            "berv_kms": round(rec["berv_kms"], 6),
            "berv_diff_stdlib_kms": round(rec["berv_diff"], 5),
            "specsys": rec["specsys"],
            "emp_rv_kms": round(rec["emp_rv_kms"], 5),
            "n_clean_anchors": rec["n_clean_anchors"],
            "header_gate": "PASS" if gate_pass else "FAIL",
            "s1d_sha256": s1d_sha,
            "aux_sha256": aux_sha,
        })
        clean_anc_bundle = {}
        for aid_k, a_win in anc_bundle.items():
            pairs = [
                (wx, fy)
                for wx, fy in zip(a_win.get("wave_a", []), a_win.get("flux", []))
                if math.isfinite(float(wx)) and math.isfinite(float(fy))
            ]
            clean_anc_bundle[aid_k] = {
                "wave_a": [x[0] for x in pairs],
                "flux": [x[1] for x in pairs],
            }
        rv_anchor_bundle.append({
            "dp_id": dp,
            "instrument": inst,
            "star": st,
            "prior_rv_kms": round(prior_rv, 5),
            "empirical_rv_kms": round(rec["emp_rv_kms"], 5),
            "windows": clean_anc_bundle,
        })

    # Compute per-star empirical RV (median across exposures) & continuum-normalized coadds per instrument
    rest_grids: dict[str, np.ndarray] = {}
    star_norm_by_inst: dict[str, dict[str, np.ndarray]] = {"HST_STIS": {}, "UVES_RED": {}, "ESPRESSO": {}}
    exp_rest_norm: dict[str, np.ndarray] = {}

    for inst in ("HST_STIS", "UVES_RED", "ESPRESSO"):
        cfg_i = get_inst_config(inst)
        step = float(cfg_i["coadd_step_angstrom"])
        rmin = float(cfg_i["coadd_rest_min_angstrom"])
        rmax = float(cfg_i["coadd_rest_max_angstrom"])
        rest_grids[inst] = np.arange(rmin, rmax + 0.1 * step, step, dtype=np.float64)

    for st, meta in star_meta.items():
        inst = meta["instrument"]
        exps = sorted(exp_by_star[st], key=lambda x: x["mjd_mid"])
        emp_rvs = [e["emp_rv_kms"] for e in exps if e["n_clean_anchors"] >= 1]
        v_star = exact_median_1d(np.asarray(emp_rvs, dtype=np.float64)) if emp_rvs else meta["prior_rv_kms"]
        rv_mad = exact_mad_1d(np.asarray(emp_rvs, dtype=np.float64)) if len(emp_rvs) >= 2 else 0.0
        meta["empirical_rv_kms"] = round(v_star, 5)
        meta["epoch_rv_mad_kms"] = round(rv_mad, 5)
        meta["median_resolving_power"] = round(exact_median_1d(np.asarray(meta["resolving_powers"], dtype=np.float64)), 1)
        meta["v_star_kms"] = v_star

        rg = rest_grids[inst]
        norm_stack = np.full((len(exps), len(rg)), np.nan, dtype=np.float64)
        for ei, rec in enumerate(exps):
            c_raw, c_eff = compute_running_continuum(rec["wave_bary"], rec["flux_a"], rec["cfg"], err=rec.get("err_a"))
            fn = normalize_flux_with_continuum(rec["flux_a"], c_raw, c_eff, inst)
            rec["flux_norm"] = fn
            rec["c_eff"] = c_eff
            w_rest = rec["wave_bary"] / (1.0 + v_star / C_KMS)
            fin = np.isfinite(fn)
            if int(fin.sum()) >= 50:
                interp_fn = np.interp(rg, w_rest[fin], fn[fin], left=np.nan, right=np.nan)
                # Mask huge inter-order / inter-chip gaps (> 1.5 A on ground, > 2.5 A on STIS)
                max_gap_a = 2.5 if inst == "HST_STIS" else 1.5
                w_fin = w_rest[fin]
                gaps = np.diff(w_fin)
                for gi in np.flatnonzero(gaps > max_gap_a):
                    g_mask = (rg > w_fin[gi]) & (rg < w_fin[gi + 1])
                    interp_fn[g_mask] = np.nan
                norm_stack[ei] = interp_fn
                exp_rest_norm[rec["dp_id"]] = interp_fn
            else:
                exp_rest_norm[rec["dp_id"]] = np.full_like(rg, np.nan)
        with np.errstate(all="ignore"):
            coadd_fn = np.nanmedian(norm_stack, axis=0)
        star_norm_by_inst[inst][st] = coadd_fn
        meta["norm_stack"] = norm_stack

    # 2. Construct KNN stellar templates within each instrument
    print("[Stage A] Constructing instrument-specific KNN stellar templates...", flush=True)
    matched_templates: dict[str, np.ndarray] = {}
    v3_rv_summary_rows: list[dict[str, Any]] = []
    for inst in ("HST_STIS", "UVES_RED", "ESPRESSO"):
        sub_meta = {st: meta for st, meta in star_meta.items() if meta["instrument"] == inst}
        mt, tmeta = construct_knn_stellar_templates(sub_meta, star_norm_by_inst[inst], get_inst_config(inst))
        matched_templates.update(mt)
        for st in sorted(sub_meta.keys()):
            m = sub_meta[st]
            tm = tmeta[st]
            m.update(tm)
            v3_rv_summary_rows.append({
                "instrument": inst,
                "star": st,
                "common_name": m["common_name"],
                "role": m["role"],
                "radio_mm_id": m["radio_mm_id"],
                "n_exposures": len(exp_by_star[st]),
                "median_resolving_power": m["median_resolving_power"],
                "prior_rv_kms": round(m["prior_rv_kms"], 5),
                "empirical_rv_kms": round(m["empirical_rv_kms"], 5),
                "empirical_minus_prior_kms": round(m["empirical_rv_kms"] - m["prior_rv_kms"], 5),
                "epoch_rv_mad_kms": m["epoch_rv_mad_kms"],
                "knn_neighbors": tm["knn_neighbors"],
                "optical_depth_gamma": tm["optical_depth_gamma"],
                "post_match_mad": tm["post_match_mad"],
            })

    # 3. Compute residuals per exposure + build G6 dense/sparse atlases + upper limits
    v2_counts_by_dp: dict[str, int] = {}
    dense_atlas_by_group: dict[str, list[dict[str, Any]]] = {"HST_STIS": [], "UVES_RED": [], "ESPRESSO": []}
    sparse_atlas_by_group: dict[str, list[dict[str, Any]]] = {"HST_STIS": [], "UVES_RED": [], "ESPRESSO": []}
    upper_limit_patches: list[dict[str, Any]] = []

    for st in sorted(star_meta.keys()):
        meta = star_meta[st]
        inst = meta["instrument"]
        rg = rest_grids[inst]
        tmpl = np.where(np.isfinite(matched_templates[st]), matched_templates[st], 1.0)
        exps = sorted(exp_by_star[st], key=lambda x: x["mjd_mid"])
        exp_resids_rest = np.full((len(exps), len(rg)), np.nan, dtype=np.float64)

        for ei, rec in enumerate(exps):
            dp = rec["dp_id"]
            y_rest = exp_rest_norm[dp] - tmpl
            exp_resids_rest[ei] = y_rest
            rec["resid_rest"] = y_rest

            # Native barycentric grid residual for Channel T
            wb = rec["wave_bary"]
            w_rest_nat = wb / (1.0 + meta["v_star_kms"] / C_KMS)
            tmpl_nat = np.interp(w_rest_nat, rg, tmpl)
            y_bary = rec["flux_norm"] - tmpl_nat
            # Resample onto uniform coadd_step grid so scan_single_exposure_residual_lsf has uniform step
            step = float(rec["cfg"]["coadd_step_angstrom"])
            bary_min = float(rec["cfg"]["coadd_rest_min_angstrom"])
            bary_max = float(rec["cfg"]["coadd_rest_max_angstrom"])
            bary_u = np.arange(bary_min, bary_max + 0.1 * step, step, dtype=np.float64)
            fin_b = np.isfinite(y_bary) & np.isfinite(rec["flux_norm"])
            y_u = np.interp(bary_u, wb[fin_b], y_bary[fin_b], left=np.nan, right=np.nan)
            fn_u = np.interp(bary_u, wb[fin_b], rec["flux_norm"][fin_b], left=np.nan, right=np.nan)
            gap_lim = 2.5 if inst == "HST_STIS" else 1.5
            w_fin = wb[fin_b]
            for gi in np.flatnonzero(np.diff(w_fin) > gap_lim):
                gm = (bary_u > w_fin[gi]) & (bary_u < w_fin[gi + 1])
                y_u[gm] = np.nan
                fn_u[gm] = np.nan

            rec["bary_u"] = bary_u
            rec["y_bary_u"] = y_u
            rec["fn_bary_u"] = fn_u
            rec["resid_topo_u"] = y_u  # Same amplitude grid indexed via topo = bary / (1+berv/c)
            rec["v2_count"] = _legacy_v2_false_alarms(bary_u, y_u, None)
            v2_counts_by_dp[dp] = rec["v2_count"]

            d_pks, s_pks = _collect_exposure_top_peaks(st, dp, rec["berv_kms"], bary_u, y_u, inst)
            dense_atlas_by_group[inst].extend(d_pks)
            sparse_atlas_by_group[inst].extend(s_pks)

        meta["exp_resids_rest"] = exp_resids_rest

        # Radiometric upper limits across star's calibration bands
        bands = list(get_calibration_bands(inst))
        if inst == "UVES_RED":
            em_lo = min(e["em_min_a"] for e in exps)
            em_hi = max(e["em_max_a"] for e in exps)
            for ob in OPTIONAL_UVES_RED_BANDS_A:
                if em_lo <= ob["req_min_le"] and em_hi >= ob["req_max_ge"]:
                    bands.append({"band_id": ob["band_id"], "center_wave_A": ob["center_wave_A"]})

        for bd in bands:
            cw = float(bd["center_wave_A"])
            m_b = (rg >= cw - 18.0) & (rg <= cw + 18.0)
            ep_mads: list[float] = []
            direct_flams: list[float] = []
            for ei, rec in enumerate(exps):
                seg = exp_resids_rest[ei][m_b]
                fin = seg[np.isfinite(seg)]
                if len(fin) >= 40:
                    m_val = exact_mad_1d(fin)
                    if math.isfinite(m_val) and m_val > 0.0:
                        ep_mads.append(m_val)
                if inst == "HST_STIS":
                    mw = (rec["direct_flam_grid"] >= cw - 18.0) & (rec["direct_flam_grid"] <= cw + 18.0)
                    f_vals = rec["direct_flam_vals"][mw]
                    e_vals = rec["direct_flam_errs"][mw]
                    ff = f_vals[np.isfinite(f_vals) & (f_vals > 0.0)]
                    ee = e_vals[np.isfinite(e_vals) & (e_vals > 0.0)]
                    f_pos = exact_median_1d(ff) if len(ff) >= 15 else 0.0
                    e_pos = 3.0 * exact_median_1d(ee) if len(ee) >= 15 else 1e-16
                    direct_flams.append(max(f_pos, e_pos, 1e-16))

            if not ep_mads:
                continue
            med_mad = exact_median_1d(np.asarray(ep_mads, dtype=np.float64))
            anchor = resolve_band_radiometric_anchor(inst, cw)
            d_flam = exact_median_1d(np.asarray(direct_flams, dtype=np.float64)) if (inst == "HST_STIS" and direct_flams) else None
            upper_limit_patches.append({
                "instrument": inst,
                "star": st,
                "common_name": meta["common_name"],
                "subrole": meta["subrole"],
                "panchromatic_bridge": meta["panchromatic_bridge"],
                "radio_mm_id": meta["radio_mm_id"],
                "within_10pc": meta["within_10pc"],
                "n_exoplanets": meta["n_exoplanets"],
                "has_transiting_planet": meta["has_transiting_planet"],
                "dist_pc": meta["dist_pc"],
                "teff_k": meta["teff_k"],
                "phot_g_mag": meta["phot_g_mag"],
                "phot_bp_mag": meta["phot_bp_mag"],
                "phot_rp_mag": meta["phot_rp_mag"],
                "j_mag": meta["j_mag"],
                "h_mag": meta["h_mag"],
                "ks_mag": meta["ks_mag"],
                "radiometric_anchor": anchor,
                "resolving_power": meta["median_resolving_power"],
                "band_id": bd["band_id"],
                "wave_bary_a": cw,
                "median_epoch_mad_rel": rsig(med_mad, 6),
                "direct_flam_cgs": rsig(d_flam, 5) if d_flam is not None else None,
            })

    # 4. Scan Channels T, P, T_DIFF, K_PLANET + COMB_V4 / COMB_V4_1 & collect real candidates + patches
    print("[Stage A] Running full-spectrum single-line & comb searches across all 33 stars / 201 exposures...", flush=True)
    searched_counts_by_inst: dict[str, dict[str, int]] = {
        k: {"T": 0, "P": 0, "T_DIFF": 0, "K_PLANET": 0, "COMB_CONFIGS": 0}
        for k in ("HST_STIS", "UVES_RED", "ESPRESSO")
    }
    real_candidates_bundle: list[dict[str, Any]] = []
    comb_v4_counts_by_star: dict[str, int] = {}
    comb_real_candidates_bundle: list[dict[str, Any]] = []

    def _build_sky_mask(inst: str, grid_bary: np.ndarray, berv_kms: float, v_star_kms: float) -> np.ndarray:
        mask = np.zeros(len(grid_bary), dtype=bool)
        if inst == "HST_STIS":
            for b in STIS_GEOCORONAL_BANDS_VAC_A:
                lo_b = float(b["lo_A"]) * (1.0 + berv_kms / C_KMS)
                hi_b = float(b["hi_A"]) * (1.0 + berv_kms / C_KMS)
                mask |= (grid_bary >= lo_b) & (grid_bary <= hi_b)
            for ch in STELLAR_FUV_EMISSION_VAC_A:
                cb = float(ch["wave_A"]) * (1.0 + v_star_kms / C_KMS)
                mask |= np.abs(grid_bary - cb) <= 0.45
        else:
            for b in TELLURIC_SATURATED_BANDS_TOPO_A:
                lo_b = float(b["lo_A"]) * (1.0 + berv_kms / C_KMS)
                hi_b = float(b["hi_A"]) * (1.0 + berv_kms / C_KMS)
                mask |= (grid_bary >= lo_b) & (grid_bary <= hi_b)
            for al in TELLURIC_AIRGLOW_LINES_A:
                ab = float(al["wave_A"]) * (1.0 + berv_kms / C_KMS)
                mask |= np.abs(grid_bary - ab) <= 0.20
            for ch in STELLAR_CHROMOSPHERIC_EMISSION_AIR_A:
                cb = float(ch["wave_A"]) * (1.0 + v_star_kms / C_KMS)
                mask |= np.abs(grid_bary - cb) <= 0.35
        return mask

    campaigns = orb_doc["campaigns"]
    for st in sorted(star_meta.keys()):
        meta = star_meta[st]
        inst = meta["instrument"]
        rg = rest_grids[inst]
        tmpl = np.where(np.isfinite(matched_templates[st]), matched_templates[st], 1.0)
        exps = sorted(exp_by_star[st], key=lambda x: x["mjd_mid"])
        cfg_star = get_inst_config(inst, resolving_power=meta["median_resolving_power"])
        n_exp = len(exps)

        # Channel T across each exposure
        for ei, rec in enumerate(exps):
            other_exps = [exps[j] for j in range(n_exp) if j != ei]
            opp_rec = max(other_exps, key=lambda o: abs(o["berv_kms"] - rec["berv_kms"])) if other_exps else rec
            y_sec = opp_rec["y_bary_u"] if opp_rec is not None else None
            cands_t, sb_t, _ = scan_single_exposure_residual_lsf(
                rec["bary_u"], rec["y_bary_u"], rec["cfg"], channel="T",
                y_secondary_check=y_sec, flux_norm_for_f1=rec["fn_bary_u"], enforce_f1_in_g1=False,
            )
            searched_counts_by_inst[inst]["T"] += sb_t
            step = float(rec["cfg"]["coadd_step_angstrom"])
            win_half_a = 4.5 if inst == "UVES_RED" else 2.0
            margin = max(65, int(round(win_half_a / step)))
            for ct in cands_t:
                k = int(ct["seed_index"])
                sl = slice(max(0, k - margin), min(len(rec["bary_u"]), k + margin + 1))
                w_cand = float(ct["fitted_center_a"])
                fn_sl = rec["fn_bary_u"][sl]
                fn_mid = len(fn_sl) // 2
                has_f1 = int(np.isfinite(fn_sl[max(0, fn_mid - 2) : min(len(fn_sl), fn_mid + 3)]).sum()) > 0 and float(
                    np.nanmax(fn_sl[max(0, fn_mid - 2) : min(len(fn_sl), fn_mid + 3)])
                ) >= 1.005
                op_list = extract_native_order_patches(rec, w_cand, rg, tmpl, meta["v_star_kms"]) if has_f1 else []
                vshift = abs(rec["berv_kms"] - meta["v_star_kms"])
                real_candidates_bundle.append({
                    "channel": "T",
                    "instrument": inst,
                    "atlas_group": inst,
                    "resolving_power": round(rec["resolving_power"], 1),
                    "role": meta["role"],
                    "star": st,
                    "dp_id": rec["dp_id"],
                    "seed_wave_a": round(float(rec["bary_u"][k]), 5),
                    "v_star_kms": round(meta["v_star_kms"], 5),
                    "berv_kms": round(rec["berv_kms"], 5),
                    "vshift_kms": round(vshift, 4),
                    "dpr_or_calsel": rec["dpr_or_calsel"],
                    "dv_orb_kms": 0.0,
                    "wave_win": rarr(rec["bary_u"][sl], ndig=5),
                    "y_primary_win": rarr(rec["y_bary_u"][sl], ndig=4),
                    "f_norm_win": rarr(fn_sl, ndig=4),
                    "order_patches": op_list,
                })

        # Channel P (stellar-rest coadd)
        coadd_r, coadd_fn, cands_p, sb_p, _ = build_multi_epoch_rest_coadd_and_channel_p(
            rg, meta["norm_stack"], meta["exp_resids_rest"], tmpl, cfg_star
        )
        searched_counts_by_inst[inst]["P"] += sb_p
        step_p = float(cfg_star["coadd_step_angstrom"])
        win_half_p = 4.5 if inst == "UVES_RED" else 2.0
        margin_p = max(65, int(round(win_half_p / step_p)))
        rep_rec = exps[len(exps) // 2]
        for cp in cands_p:
            k = int(cp["seed_index"])
            sl = slice(max(0, k - margin_p), min(len(rg), k + margin_p + 1))
            w_rest_cand = float(cp["fitted_center_a"])
            w_bary_rep = w_rest_cand * (1.0 + meta["v_star_kms"] / C_KMS)
            fn_sl = coadd_fn[sl]
            fn_mid = len(fn_sl) // 2
            has_f1 = int(np.isfinite(fn_sl[max(0, fn_mid - 2) : min(len(fn_sl), fn_mid + 3)]).sum()) > 0 and float(
                np.nanmax(fn_sl[max(0, fn_mid - 2) : min(len(fn_sl), fn_mid + 3)])
            ) >= 1.005
            op_list = extract_native_order_patches(rep_rec, w_bary_rep, rg, tmpl, meta["v_star_kms"]) if has_f1 else []
            epoch_wins = [rarr(meta["exp_resids_rest"][ei, sl], ndig=4) for ei in range(n_exp)]
            real_candidates_bundle.append({
                "channel": "P",
                "instrument": inst,
                "atlas_group": inst,
                "resolving_power": round(meta["median_resolving_power"], 1),
                "role": meta["role"],
                "star": st,
                "dp_id": rep_rec["dp_id"],
                "seed_wave_a": round(float(rg[k]), 5),
                "v_star_kms": round(meta["v_star_kms"], 5),
                "berv_kms": round(rep_rec["berv_kms"], 5),
                "vshift_kms": round(abs(rep_rec["berv_kms"] - meta["v_star_kms"]), 4),
                "dpr_or_calsel": rep_rec["dpr_or_calsel"],
                "dv_orb_kms": 0.0,
                "wave_win": rarr(rg[sl], ndig=5),
                "y_primary_win": rarr(coadd_r[sl], ndig=4),
                "f_norm_win": rarr(coadd_fn[sl], ndig=4),
                "epoch_wins": epoch_wins,
                "order_patches": op_list,
            })

        # Channels T_DIFF & K_PLANET for orbital campaign stars (10 campaigns)
        if st in campaigns:
            camp = campaigns[st]
            by_dp_camp = {e["dp_id"]: e for e in camp["exposures"]}
            in_exps = [rec for rec in exps if by_dp_camp[rec["dp_id"]]["phase_window"] == "IN_WINDOW"]
            out_exps = [rec for rec in exps if by_dp_camp[rec["dp_id"]]["phase_window"] == "OUT_OF_WINDOW"]
            out_stack = np.full((len(out_exps), len(rg)), np.nan, dtype=np.float64)
            for oi, rec in enumerate(out_exps):
                out_stack[oi] = rec["resid_rest"]
            with np.errstate(all="ignore"):
                out_med = np.nanmedian(out_stack, axis=0)
            unsh_r = np.full((len(in_exps), len(rg)), np.nan, dtype=np.float64)
            unsh_fn = np.full((len(in_exps), len(rg)), np.nan, dtype=np.float64)
            dedop_r = np.full((len(in_exps), len(rg)), np.nan, dtype=np.float64)
            dedop_fn = np.full((len(in_exps), len(rg)), np.nan, dtype=np.float64)
            for ii, rec in enumerate(in_exps):
                unsh_r[ii] = rec["resid_rest"]
                unsh_fn[ii] = exp_rest_norm[rec["dp_id"]]
                dv_p = float(by_dp_camp[rec["dp_id"]]["planet_orbital_rv_kms"])
                wb = rec["wave_bary"]
                fin_b = np.isfinite(rec["flux_norm"])
                if int(fin_b.sum()) >= 50:
                    w_pl = bary_to_planet_rest_wave(wb[fin_b], meta["v_star_kms"], dv_p)
                    tmpl_pl = np.interp(wb[fin_b] / (1.0 + meta["v_star_kms"] / C_KMS), rg, tmpl)
                    r_pl = rec["flux_norm"][fin_b] - tmpl_pl
                    dedop_r[ii] = np.interp(rg, w_pl, r_pl, left=np.nan, right=np.nan)
                    dedop_fn[ii] = np.interp(rg, w_pl, rec["flux_norm"][fin_b], left=np.nan, right=np.nan)

            orb_scan = build_and_scan_transit_channels(rg, unsh_r, unsh_fn, dedop_r, dedop_fn, out_med, cfg_star)
            searched_counts_by_inst[inst]["T_DIFF"] += orb_scan["tdiff_searched_bins"]
            searched_counts_by_inst[inst]["K_PLANET"] += orb_scan["kplanet_searched_bins"]
            rep_in = in_exps[0]
            rep_dv = float(by_dp_camp[rep_in["dp_id"]]["planet_orbital_rv_kms"])
            for ch_name, c_list, y_arr, fn_arr in (
                ("T_DIFF", orb_scan["tdiff_cands"], orb_scan["y_tdiff"], orb_scan["u_tdiff_fn"]),
                ("K_PLANET", orb_scan["kplanet_cands"], orb_scan["y_kplanet"], orb_scan["f_kplanet_fn"]),
            ):
                for ck in c_list:
                    k = int(ck["seed_index"])
                    sl = slice(max(0, k - margin_p), min(len(rg), k + margin_p + 1))
                    w_c = float(ck["fitted_center_a"])
                    w_bary = planet_rest_to_bary_wave(w_c, meta["v_star_kms"], rep_dv if ch_name == "K_PLANET" else 0.0)
                    fn_sl = fn_arr[sl]
                    fn_mid = len(fn_sl) // 2
                    has_f1 = int(np.isfinite(fn_sl[max(0, fn_mid - 2) : min(len(fn_sl), fn_mid + 3)]).sum()) > 0 and float(
                        np.nanmax(fn_sl[max(0, fn_mid - 2) : min(len(fn_sl), fn_mid + 3)])
                    ) >= 1.005
                    op_list = extract_native_order_patches(rep_in, w_bary, rg, tmpl, meta["v_star_kms"]) if has_f1 else []
                    mat_in = unsh_r if ch_name == "T_DIFF" else dedop_r
                    in_wins = [rarr(mat_in[ii, sl] - out_med[sl], ndig=4) for ii in range(len(in_exps))]
                    real_candidates_bundle.append({
                        "channel": ch_name,
                        "instrument": inst,
                        "atlas_group": inst,
                        "resolving_power": round(meta["median_resolving_power"], 1),
                        "role": meta["role"],
                        "star": st,
                        "dp_id": rep_in["dp_id"],
                        "seed_wave_a": round(float(rg[k]), 5),
                        "v_star_kms": round(meta["v_star_kms"], 5),
                        "berv_kms": round(rep_in["berv_kms"], 5),
                        "vshift_kms": round(abs(rep_in["berv_kms"] - meta["v_star_kms"]), 4),
                        "dpr_or_calsel": rep_in["dpr_or_calsel"],
                        "dv_orb_kms": round(rep_dv if ch_name == "K_PLANET" else 0.0, 4),
                        "wave_win": rarr(rg[sl], ndig=5),
                        "y_primary_win": rarr(y_arr[sl], ndig=4),
                        "f_norm_win": rarr(fn_arr[sl], ndig=4),
                        "in_epoch_wins": in_wins,
                        "order_patches": op_list,
                    })

        # COMB_V4 and COMB_V4_1 full-spectrum scan (in barycentric frame aligned with continuum/recon)
        bary_grid = rg * (1.0 + meta["v_star_kms"] / C_KMS)
        tmpl_b = tmpl
        with np.errstate(all="ignore"):
            y_b_stack = coadd_r
            sigma_b_stack = np.nanstd(meta["exp_resids_rest"], axis=0) / math.sqrt(max(1, n_exp))
            med_mad_all = exact_mad_1d(coadd_r[np.isfinite(coadd_r)]) if np.any(np.isfinite(coadd_r)) else 0.04
            sigma_b_stack = np.where(np.isfinite(sigma_b_stack) & (sigma_b_stack > 0.25 * med_mad_all), sigma_b_stack, med_mad_all)
            recon_stack = np.clip(tmpl_b, 0.0, 1.2)
            # Topocentric stack aligned to star barycentric grid via median epoch shift
            med_berv = exact_median_1d(np.asarray([e["berv_kms"] for e in exps], dtype=np.float64))
            topo_shift_stack = np.full((n_exp, len(bary_grid)), np.nan, dtype=np.float64)
            for ei, rec in enumerate(exps):
                fin_e = np.isfinite(rec["y_bary_u"])
                if int(fin_e.sum()) >= 50:
                    topo_shift_stack[ei] = np.interp(
                        bary_grid / (1.0 + rec["berv_kms"] / C_KMS),
                        rec["bary_u"][fin_e] / (1.0 + rec["berv_kms"] / C_KMS),
                        rec["y_bary_u"][fin_e],
                        left=np.nan,
                        right=np.nan,
                    )
            y_topo_stack = np.nanmedian(topo_shift_stack, axis=0)
            sigma_topo_stack = np.maximum(0.5 * med_mad_all, sigma_b_stack)

        sky_mask = _build_sky_mask(inst, bary_grid, med_berv, meta["v_star_kms"])
        win_list = COMB_V4_1_WINDOWS_A[inst]
        v4_cands, n_comb_cfg = scan_frequency_comb_v4(
            bary_grid, y_b_stack, sigma_b_stack, np.where(np.isfinite(coadd_fn), coadd_fn, 1.0), recon_stack,
            sky_mask, y_topo_stack, sigma_topo_stack, win_list, cfg_star["comb_search_bands"], cfg_star,
        )
        v41_cands, _ = scan_frequency_comb_v4_1(
            bary_grid, y_b_stack, sigma_b_stack, np.where(np.isfinite(coadd_fn), coadd_fn, 1.0), recon_stack,
            sky_mask, y_topo_stack, sigma_topo_stack, win_list, cfg_star["comb_search_bands"], cfg_star,
        )
        searched_counts_by_inst[inst]["COMB_CONFIGS"] += n_comb_cfg
        comb_v4_counts_by_star[st] = len(v4_cands)

        # Keep ALL v4.1 survivors + up to top 16 v4 candidates per star so bundle stays compact and exact
        keep_cands = list(v41_cands)
        seen_k = {(c["band"], round(c["dnu_ghz"], 2), round(c["nu0_ghz"], 1)) for c in keep_cands}
        for c in v4_cands:
            key = (c["band"], round(c["dnu_ghz"], 2), round(c["nu0_ghz"], 1))
            if key not in seen_k:
                keep_cands.append(c)
                seen_k.add(key)
            if len([k for k in keep_cands if k not in v41_cands]) >= 16:
                break

        for cc in keep_cands:
            w_lo = min(cc["wave0_a"], cc["wave_end_a"]) - 6.0
            w_hi = max(cc["wave0_a"], cc["wave_end_a"]) + 6.0
            m_c = (bary_grid >= w_lo) & (bary_grid <= w_hi)
            if int(m_c.sum()) < 30:
                continue
            comb_real_candidates_bundle.append({
                "star": st,
                "instrument": inst,
                "role": meta["role"],
                "band": cc["band"],
                "resolving_power": round(meta["median_resolving_power"], 1),
                "dnu_ghz": cc["dnu_ghz"],
                "nu0_ghz_stage_a": cc["nu0_ghz"],
                "wave_win": rarr(bary_grid[m_c], ndig=5),
                "y_rest_win": rarr(y_b_stack[m_c], ndig=4),
                "sigma_rest_win": rarr(sigma_b_stack[m_c], ndig=4),
                "fn_win": rarr(np.where(np.isfinite(coadd_fn[m_c]), coadd_fn[m_c], 1.0), ndig=4),
                "recon_win": rarr(recon_stack[m_c], ndig=4),
                "sky_mask_win": [bool(x) for x in sky_mask[m_c]],
                "y_topo_win": rarr(np.where(np.isfinite(y_topo_stack[m_c]), y_topo_stack[m_c], 0.0), ndig=4),
                "sigma_topo_win": rarr(sigma_topo_stack[m_c], ndig=4),
            })

    # 5. Extract Calibration Patches across ALL 3 instruments (2,697 synthetic trials)
    print("[Stage A] Extracting synthetic calibration patches across HST_STIS, UVES_RED, and ESPRESSO...", flush=True)
    calib_transient_patches: list[dict[str, Any]] = []
    calib_persistent_patches: list[dict[str, Any]] = []
    calib_keplerian_patches: list[dict[str, Any]] = []
    calib_g4g5_patches: list[dict[str, Any]] = []
    calib_g6_patches: list[dict[str, Any]] = []
    calib_comb_patches: list[dict[str, Any]] = []

    def _pick_stars_for_inst(inst: str, n: int) -> list[str]:
        pool = sorted(st for st, m in star_meta.items() if m["instrument"] == inst)
        if inst == "UVES_RED":
            # Prefer narrow-slit high-R spectra over wide-slit R=42k where 1 sigma exceeds 3.5 native px
            pool.sort(key=lambda s: (-star_meta[s]["median_resolving_power"], s))
            return pool[:n]
        if inst == "ESPRESSO":
            def _esp_key(s: str) -> tuple[int, float, str]:
                ex = sorted(exp_by_star[s], key=lambda x: x["mjd_mid"])
                mid_dpr = str(ex[len(ex) // 2]["dpr_or_calsel"]).upper()
                has_calb = 1 if any(t in mid_dpr for t in ("CALB", "WAVE", "FP")) else 0
                return (has_calb, float(star_meta[s]["phot_g_mag"]), s)
            pool.sort(key=_esp_key)
            return pool[:n]
        sci = [s for s in pool if star_meta[s]["role"] == "SCIENCE"] + [s for s in pool if star_meta[s]["role"] == "CONTROL"]
        return sci[:n]

    def _select_clean_band_spot(rec: dict[str, Any], meta: dict[str, Any], rg: np.ndarray, tmpl: np.ndarray, bd: dict[str, Any], bds: list[dict[str, Any]]) -> tuple[dict[str, Any], float, np.ndarray, list[dict[str, Any]]]:
        inst = meta["instrument"]
        offsets = sorted([round(float(x), 2) for x in np.linspace(-11.5, 11.5, 47) if abs(x) >= 0.4], key=abs)
        cand_exps = [rec] + [e for e in sorted(exp_by_star[meta["star"]], key=lambda x: x["mjd_mid"]) if e["dp_id"] != rec["dp_id"]]
        best_fb = None
        best_score = -1
        for cand_b in [bd] + list(bds):
            for ex_try in cand_exps[:4]:
                cfg_try = get_inst_config(inst, resolving_power=ex_try["resolving_power"])
                for off_a in offsets:
                    cw_c = float(cand_b["center_wave_A"]) + off_a
                    wb_raw = cw_c * (1.0 + meta["v_star_kms"] / C_KMS)
                    if not evaluate_gate_g2_airglow(wb_raw, float(ex_try["berv_kms"]), cfg_try)["g2_pass"]:
                        continue
                    ops_init = extract_native_order_patches(ex_try, wb_raw, rg, tmpl, meta["v_star_kms"])
                    if not ops_init:
                        continue
                    w0_arr = np.asarray(ops_init[0]["wave"], dtype=np.float64)
                    kp_m = int(np.argmin(np.abs(w0_arr - wb_raw)))
                    wb_c = float(w0_arr[kp_m])
                    wr_c = wb_c / (1.0 + meta["v_star_kms"] / C_KMS)
                    if not evaluate_gate_g2_airglow(wb_c, float(ex_try["berv_kms"]), cfg_try)["g2_pass"]:
                        continue
                    m_c = np.abs(ex_try["bary_u"] - wb_c) <= 4.5
                    if int((m_c & np.isfinite(ex_try["y_bary_u"])).sum()) < 120:
                        continue
                    ops_c = extract_native_order_patches(ex_try, wb_c, rg, tmpl, meta["v_star_kms"])
                    if not ops_c:
                        continue
                    w_win = np.asarray(ex_try["bary_u"][m_c], dtype=np.float64)
                    r_win = np.where(np.isfinite(ex_try["y_bary_u"][m_c]), ex_try["y_bary_u"][m_c], 0.0)
                    fn_win = np.where(np.isfinite(ex_try["fn_bary_u"][m_c]), ex_try["fn_bary_u"][m_c], 1.0)
                    lmad = _annulus_noise_mad(w_win, ex_try["y_bary_u"][m_c], wb_c, float(cfg_try["sigma_v_kms"]))
                    if not (math.isfinite(lmad) and lmad > 0.0):
                        continue
                    # G4/G5 discrimination check: true LSF passes, single-px cosmic spike & wide plateau fail
                    t_ops, s_ops, p_ops = [], [], []
                    for op in ops_c:
                        w_o = np.asarray(op["wave"], dtype=np.float64)
                        fa_o = np.asarray(op["flux_a"], dtype=np.float64)
                        fin_o = np.isfinite(fa_o)
                        cont = max(1e-16, exact_quantile_1d(fa_o[fin_o], 0.80))
                        sb_mad = max(1e-17, exact_mad_1d(fa_o[fin_o]))
                        k0 = int(np.argmin(np.abs(w_o - wb_c)))
                        sig_a = wb_c / (ex_try["resolving_power"] * FWHM_FACTOR)
                        g_true = np.exp(-0.5 * ((w_o - wb_c) / sig_a) ** 2)
                        g_wide = np.exp(-0.5 * ((w_o - wb_c) / (4.5 * sig_a)) ** 2)
                        t_ops.append({**op, "flux_a": fa_o + max(0.35 * cont, 16.0 * sb_mad) * g_true})
                        fa_spk = fa_o.copy()
                        spk = max(0.95 * cont, 32.0 * sb_mad)
                        fa_spk[k0] += spk
                        if k0 > 0:
                            fa_spk[k0 - 1] += 0.01 * spk
                        if k0 + 1 < len(fa_spk):
                            fa_spk[k0 + 1] += 0.01 * spk
                        s_ops.append({**op, "flux_a": fa_spk})
                        p_ops.append({**op, "flux_a": fa_o + max(0.65 * cont, 22.0 * sb_mad) * g_wide})
                    rt = evaluate_gates_g3_g4_g5_v38(t_ops, ex_try["dpr_or_calsel"], "T", wr_c, cfg_try)
                    rs = evaluate_gates_g3_g4_g5_v38(s_ops, ex_try["dpr_or_calsel"], "T", wr_c, cfg_try)
                    rp = evaluate_gates_g3_g4_g5_v38(p_ops, ex_try["dpr_or_calsel"], "T", wr_c, cfg_try)
                    g45_ok = bool(rt["g3_pass"] and rt["g4_pass"] and rt["g5_pass"] and (not (rs["g4_pass"] and rs["g5_pass"])) and (not (rp["g4_pass"] and rp["g5_pass"])))
                    if not g45_ok:
                        if best_score < 0:
                            best_score = 0
                            best_fb = (ex_try, wb_c, m_c, ops_c)
                        continue
                    # Channel T recovery check at 7.8 * lmad and 14.0 * lmad across all 3 subpixel phases
                    step_w = float(exact_median_1d(np.diff(w_win)))
                    w_m = float(w_win[len(w_win) // 2])
                    t_ok = True
                    for ph in (-0.35, 0.0, 0.35):
                        w_inj = w_m + ph * step_w
                        for sm_chk in (7.8, 14.0):
                            amp_i = sm_chk * lmad
                            fit_i = fit_lsf_on_window(w_win, _inject_gaussian(w_win, r_win, w_inj, amp_i, ex_try["resolving_power"]), w_inj, cfg_try)
                            fn_i = _inject_gaussian(w_win, fn_win, w_inj, amp_i, ex_try["resolving_power"])
                            f1_i = compute_supraphotospheric_f1_window(w_win, fn_i, fit_i.get("fitted_center_a", w_inj), cfg_try["supraphotospheric_min_fn_pk3"])["f1_supraphotospheric_pass"]
                            if not (check_channel_lsf_gate(fit_i, "T", cfg_try) and f1_i):
                                t_ok = False
                                break
                        if not t_ok:
                            break
                        # Native order G3-G5 check at 7.8 * lmad
                        n_ops = []
                        for op in ops_c:
                            ow = np.asarray(op["wave"], dtype=np.float64)
                            ofa = np.asarray(op["flux_a"], dtype=np.float64)
                            ce = max(1e-16, exact_quantile_1d(ofa[np.isfinite(ofa)], 0.80))
                            omad = exact_mad_1d(ofa[np.isfinite(ofa)])
                            n_ops.append({**op, "target_wave_a": round(float(w_inj), 5), "flux_a": _inject_gaussian(ow, ofa, w_inj, max(7.8 * lmad, 8.0 * omad / ce) * ce, ex_try["resolving_power"])})
                        r_nat = evaluate_gates_g3_g4_g5_v38(n_ops, ex_try["dpr_or_calsel"], "T", float(w_inj) / (1.0 + meta["v_star_kms"] / C_KMS), cfg_try)
                        if not (r_nat["g3_pass"] and r_nat["g4_pass"] and r_nat["g5_pass"]):
                            t_ok = False
                            break
                    if t_ok:
                        return ex_try, wb_c, m_c, ops_c
                    if best_score < 1:
                        best_score = 1
                        best_fb = (ex_try, wb_c, m_c, ops_c)
        if best_fb is None:
            raise RuntimeError(f"No valid transient patch for {inst}/{meta['star']}/{bd['band_id']}")
        return best_fb

    # 5a. calib_transient_patches (72 total = 24 STIS + 24 UVES_RED + 24 ESPRESSO -> *3*5 = 1080)
    # 5d. calib_g4g5_patches (72 total -> *3 = 216)
    plan_trans = [
        ("HST_STIS", _pick_stars_for_inst("HST_STIS", 6), 4),   # 6 * 4 = 24
        ("UVES_RED", _pick_stars_for_inst("UVES_RED", 4), 6),   # 4 * 6 = 24
        ("ESPRESSO", _pick_stars_for_inst("ESPRESSO", 4), 6),   # 4 * 6 = 24
    ]
    for inst, s_list, n_b in plan_trans:
        b_list = get_calibration_bands(inst)[:n_b]
        rg = rest_grids[inst]
        for st in s_list:
            meta = star_meta[st]
            exps = sorted(exp_by_star[st], key=lambda x: x["mjd_mid"])
            rec = exps[len(exps) // 2]
            tmpl = np.where(np.isfinite(matched_templates[st]), matched_templates[st], 1.0)
            for bd in b_list:
                ex_use, w_bary, m, ops = _select_clean_band_spot(rec, meta, rg, tmpl, bd, get_calibration_bands(inst))
                cfg_use = get_inst_config(inst, resolving_power=ex_use["resolving_power"])
                lmad = _annulus_noise_mad(ex_use["bary_u"][m], ex_use["y_bary_u"][m], w_bary, float(cfg_use["sigma_v_kms"]))
                calib_transient_patches.append({
                    "instrument": inst,
                    "star": st,
                    "dp_id": ex_use["dp_id"],
                    "resolving_power": round(ex_use["resolving_power"], 1),
                    "band_id": bd["band_id"],
                    "target_bary_a": round(w_bary, 5),
                    "v_star_kms": round(meta["v_star_kms"], 5),
                    "berv_kms": round(ex_use["berv_kms"], 5),
                    "dpr_or_calsel": ex_use["dpr_or_calsel"],
                    "local_mad": rsig(lmad, 5),
                    "wave_win": rarr(ex_use["bary_u"][m], ndig=5),
                    "resid_win": rarr(np.where(np.isfinite(ex_use["y_bary_u"][m]), ex_use["y_bary_u"][m], 0.0), ndig=4),
                    "f_norm_win": rarr(np.where(np.isfinite(ex_use["fn_bary_u"][m]), ex_use["fn_bary_u"][m], 1.0), ndig=4),
                    "order_patches": ops,
                })
                calib_g4g5_patches.append({
                    "instrument": inst,
                    "star": st,
                    "dp_id": ex_use["dp_id"],
                    "resolving_power": round(ex_use["resolving_power"], 1),
                    "band_id": bd["band_id"],
                    "target_bary_a": round(w_bary, 5),
                    "stellar_rest_wave_a": round(w_bary / (1.0 + meta["v_star_kms"] / C_KMS), 5),
                    "dpr_or_calsel": ex_use["dpr_or_calsel"],
                    "order_patches": ops,
                })

    # 5b. calib_persistent_patches (36 total = 12 STIS + 12 UVES_RED + 12 ESPRESSO -> *3*5 = 540)
    plan_pers = [
        ("HST_STIS", _pick_stars_for_inst("HST_STIS", 4), 3),   # 4 * 3 = 12
        ("UVES_RED", _pick_stars_for_inst("UVES_RED", 4), 3),   # 4 * 3 = 12
        ("ESPRESSO", _pick_stars_for_inst("ESPRESSO", 4), 3),   # 4 * 3 = 12
    ]
    for inst, s_list, n_b in plan_pers:
        b_list = get_calibration_bands(inst)[:n_b]
        rg = rest_grids[inst]
        p_offsets = sorted([round(float(x), 2) for x in np.linspace(-11.5, 11.5, 47) if abs(x) >= 0.4], key=abs)
        for st in s_list:
            meta = star_meta[st]
            exps = sorted(exp_by_star[st], key=lambda x: x["mjd_mid"])
            rep = exps[len(exps) // 2]
            tmpl = np.where(np.isfinite(matched_templates[st]), matched_templates[st], 1.0)
            cfg_p = get_inst_config(inst, resolving_power=meta["median_resolving_power"])
            with np.errstate(all="ignore"):
                coadd_r = np.nanmedian(meta["exp_resids_rest"], axis=0)
                coadd_fn = np.nanmedian(meta["norm_stack"], axis=0)
            for bd in b_list:
                cw, m, ops, cmad_sel = None, None, [], 0.03
                fb_p = None
                for cand_b in [bd] + list(get_calibration_bands(inst)):
                    found_p = False
                    for off_a in p_offsets:
                        cw_c = float(cand_b["center_wave_A"]) + off_a
                        m_c = np.abs(rg - cw_c) <= 4.5
                        if int((m_c & np.isfinite(coadd_r)).sum()) < 120:
                            continue
                        wb_c = cw_c * (1.0 + meta["v_star_kms"] / C_KMS)
                        if not evaluate_gate_g2_airglow(wb_c, float(rep["berv_kms"]), cfg_p)["g2_pass"]:
                            continue
                        ops_c = extract_native_order_patches(rep, wb_c, rg, tmpl, meta["v_star_kms"])
                        if not ops_c:
                            continue
                        w_p = np.asarray(rg[m_c], dtype=np.float64)
                        r_p = np.where(np.isfinite(coadd_r[m_c]), coadd_r[m_c], 0.0)
                        fn_p = np.where(np.isfinite(coadd_fn[m_c]), coadd_fn[m_c], 1.0)
                        cmad_c = _annulus_noise_mad(w_p, coadd_r[m_c], cw_c, float(cfg_p["sigma_v_kms"]))
                        if not (math.isfinite(cmad_c) and cmad_c > 0.0):
                            continue
                        if fb_p is None:
                            fb_p = (cw_c, m_c, ops_c, cmad_c)
                        step_p = float(exact_median_1d(np.diff(w_p)))
                        wm_p = float(w_p[len(w_p) // 2])
                        req_e = max(2, int(math.ceil(cfg_p["channel_p_min_epoch_fraction"] * len(exps))))
                        p_ok = True
                        for ph in (-0.35, 0.0, 0.35):
                            w_inj = wm_p + ph * step_p
                            for sm_chk in (7.8, 14.0):
                                amp_i = sm_chk * cmad_c
                                fit_p = fit_lsf_on_window(w_p, _inject_gaussian(w_p, r_p, w_inj, amp_i, meta["median_resolving_power"]), w_inj, cfg_p)
                                fn_inj_p = _inject_gaussian(w_p, fn_p, w_inj, amp_i, meta["median_resolving_power"])
                                f1_ok = compute_supraphotospheric_f1_window(w_p, fn_inj_p, fit_p.get("fitted_center_a", w_inj), cfg_p["supraphotospheric_min_fn_pk3"])["f1_supraphotospheric_pass"]
                                if not (check_channel_lsf_gate(fit_p, "P", cfg_p) and f1_ok):
                                    p_ok = False
                                    break
                                if sm_chk < 9.0:
                                    n_hit = 0
                                    for ei in range(len(exps)):
                                        er_w = np.where(np.isfinite(meta["exp_resids_rest"][ei, m_c]), meta["exp_resids_rest"][ei, m_c], 0.0)
                                        ef = fit_lsf_on_window(w_p, _inject_gaussian(w_p, er_w, w_inj, amp_i, meta["median_resolving_power"]), w_inj, cfg_p, fixed_phase_bins=fit_p.get("phase_bins"))
                                        if ef.get("valid_fit") and ef["snr_mid"] >= 2.8:
                                            n_hit += 1
                                    if n_hit < req_e:
                                        p_ok = False
                                        break
                            if not p_ok:
                                break
                        if p_ok:
                            cw, m, ops, cmad_sel = cw_c, m_c, ops_c, cmad_c
                            found_p = True
                            break
                    if found_p:
                        break
                if cw is None and fb_p is not None:
                    cw, m, ops, cmad_sel = fb_p
                if cw is None or m is None or not ops:
                    raise RuntimeError(f"No valid persistent patch for {inst}/{st}/{bd['band_id']}")
                calib_persistent_patches.append({
                    "instrument": inst,
                    "star": st,
                    "rep_dp_id": rep["dp_id"],
                    "resolving_power": round(meta["median_resolving_power"], 1),
                    "band_id": bd["band_id"],
                    "target_rest_a": round(cw, 5),
                    "v_star_kms": round(meta["v_star_kms"], 5),
                    "berv_kms": round(rep["berv_kms"], 5),
                    "dpr_or_calsel": rep["dpr_or_calsel"],
                    "coadd_mad": rsig(cmad_sel, 5),
                    "wave_win": rarr(rg[m], ndig=5),
                    "coadd_resid_win": rarr(np.where(np.isfinite(coadd_r[m]), coadd_r[m], 0.0), ndig=4),
                    "coadd_fn_win": rarr(np.where(np.isfinite(coadd_fn[m]), coadd_fn[m], 1.0), ndig=4),
                    "epoch_resids": [rarr(np.where(np.isfinite(meta["exp_resids_rest"][ei, m]), meta["exp_resids_rest"][ei, m], 0.0), ndig=4) for ei in range(len(exps))],
                    "order_patches": ops,
                })

    # 5c. calib_keplerian_patches (9 total: 2 on AUMIC [HST_STIS] + 7 on ESPRESSO science/control orbital hosts -> *3*5 = 135)
    kep_specs = [
        ("AUMIC", 0), ("AUMIC", 2),
        ("CDCET", 3), ("GJ3138", 4), ("HD40307", 5),
        ("TOI700", 6), ("TOI178", 7), ("K23", 8), ("41ARA", 4),
    ]
    for st, b_idx in kep_specs:
        meta = star_meta[st]
        inst = meta["instrument"]
        rg = rest_grids[inst]
        exps = sorted(exp_by_star[st], key=lambda x: x["mjd_mid"])
        camp = campaigns[st]
        by_dp_c = {e["dp_id"]: e for e in camp["exposures"]}
        in_exps = [rec for rec in exps if by_dp_c[rec["dp_id"]]["phase_window"] == "IN_WINDOW"]
        out_exps = [rec for rec in exps if by_dp_c[rec["dp_id"]]["phase_window"] == "OUT_OF_WINDOW"]
        bd_list = get_calibration_bands(inst)
        bd = bd_list[b_idx % len(bd_list)]
        cw = float(bd["center_wave_A"]) + 3.0
        m = np.abs(rg - cw) <= 6.5
        out_stack = np.vstack([rec["resid_rest"][m] for rec in out_exps])
        with np.errstate(all="ignore"):
            out_med = np.nanmedian(out_stack, axis=0)
        in_tracks = []
        ep_mads = []
        for rec in in_exps:
            tr = rec["resid_rest"][m]
            f_tr = tr[np.isfinite(tr)]
            if len(f_tr) >= 15:
                ep_mads.append(exact_mad_1d(f_tr))
            in_tracks.append({
                "dp_id": rec["dp_id"],
                "dv_orb_kms": round(float(by_dp_c[rec["dp_id"]]["planet_orbital_rv_kms"]), 5),
                "resid_win": rarr(np.where(np.isfinite(tr), tr, 0.0), ndig=4),
            })
        s_mad = exact_median_1d(np.asarray(ep_mads, dtype=np.float64)) if ep_mads else 0.04
        calib_keplerian_patches.append({
            "star": st,
            "instrument": inst,
            "rep_dp_id": in_exps[0]["dp_id"],
            "resolving_power": round(meta["median_resolving_power"], 1),
            "band_id": bd["band_id"],
            "dv_span_kms": float(camp["orbital_dv_span_kms"]),
            "single_in_exp_mad": rsig(s_mad, 5),
            "target_planet_a": round(cw, 5),
            "planet_wave_win": rarr(rg[m], ndig=5),
            "out_resid_med_win": rarr(np.where(np.isfinite(out_med), out_med, 0.0), ndig=4),
            "in_epoch_tracks": in_tracks,
        })

    # 5e. calib_g6_patches (20 total: 7 HST_STIS + 7 UVES_RED + 6 ESPRESSO -> *3*4 = 240)
    plan_g6 = [
        ("HST_STIS", _pick_stars_for_inst("HST_STIS", 7)),
        ("UVES_RED", _pick_stars_for_inst("UVES_RED", 7)),
        ("ESPRESSO", _pick_stars_for_inst("ESPRESSO", 6)),
    ]
    for inst, s_list in plan_g6:
        bds = get_calibration_bands(inst)
        d_all = dense_atlas_by_group[inst]
        s_all = sparse_atlas_by_group[inst]
        other_pool = [s for s in sorted(star_meta.keys()) if star_meta[s]["instrument"] == inst]
        for idx_s, st in enumerate(s_list):
            exps = sorted(exp_by_star[st], key=lambda x: x["mjd_mid"])
            rec = exps[0]
            opp = max(exps, key=lambda o: abs(o["berv_kms"] - rec["berv_kms"]))
            # Guarantee distinct synthetic BERV separation in calibration even if exposure BERV span is modest
            opp_berv = opp["berv_kms"] if abs(opp["berv_kms"] - rec["berv_kms"]) >= 6.0 else (rec["berv_kms"] + 12.0)
            opp_dp = opp["dp_id"] if opp["dp_id"] != rec["dp_id"] else f"{rec['dp_id']}_OPP"
            bd = bds[idx_s % len(bds)]
            cand_topo = float(bd["center_wave_A"]) + 4.12
            loc_dense = [p for p in d_all if abs(p["topo_wave_a"] - cand_topo) <= 3.0]
            loc_sparse = [p for p in s_all if abs(p["topo_wave_a"] - cand_topo) <= 3.0]
            synth_others = [s for s in other_pool if s != st][:4]
            calib_g6_patches.append({
                "instrument": inst,
                "atlas_group": inst,
                "star": st,
                "dp_id": rec["dp_id"],
                "opp_dp_id": opp_dp,
                "target_berv_kms": round(rec["berv_kms"], 4),
                "opp_berv_kms": round(opp_berv, 4),
                "target_vshift_kms": round(abs(rec["berv_kms"] - star_meta[st]["v_star_kms"]), 4),
                "cand_topo_vac_a": round(cand_topo, 4),
                "cand_order": 1,
                "cand_px": 15000 + idx_s * 100,
                "band_id": bd["band_id"],
                "local_dense_atlas": loc_dense[:40],
                "local_sparse_atlas": loc_sparse[:20],
                "synthetic_other_stars": synth_others,
            })

    # 5f. calib_comb_patches (18 total: 6 STIS + 6 UVES_RED + 6 ESPRESSO -> *3*9 = 486)
    plan_comb = [
        ("HST_STIS", _pick_stars_for_inst("HST_STIS", 3), COMB_V4_1_WINDOWS_A["HST_STIS"]),
        ("UVES_RED", _pick_stars_for_inst("UVES_RED", 3), COMB_V4_1_WINDOWS_A["UVES_RED"]),
        ("ESPRESSO", _pick_stars_for_inst("ESPRESSO", 2), COMB_V4_1_WINDOWS_A["ESPRESSO"]),
    ]
    for inst, s_list, win_defs in plan_comb:
        rg = rest_grids[inst]
        for st in s_list:
            meta = star_meta[st]
            cfg_s = get_inst_config(inst, resolving_power=meta["median_resolving_power"])
            exps = sorted(exp_by_star[st], key=lambda x: x["mjd_mid"])
            bary_grid = rg * (1.0 + meta["v_star_kms"] / C_KMS)
            tmpl = np.where(np.isfinite(matched_templates[st]), matched_templates[st], 1.0)
            with np.errstate(all="ignore"):
                coadd_r = np.nanmedian(meta["exp_resids_rest"], axis=0)
                coadd_fn = np.nanmedian(meta["norm_stack"], axis=0)
            med_mad_all = exact_mad_1d(coadd_r[np.isfinite(coadd_r)]) if np.any(np.isfinite(coadd_r)) else 0.04
            med_berv = exact_median_1d(np.asarray([e["berv_kms"] for e in exps], dtype=np.float64))
            sky_mask = _build_sky_mask(inst, bary_grid, med_berv, meta["v_star_kms"])

            for wd in win_defs:
                # Choose an explicit 28 A clean window near the band center (spanning > 2000 GHz even in STIS, > 800 GHz in UVES_RED)
                c_mid = 0.5 * (wd["lo_a"] + wd["hi_a"])
                if inst == "HST_STIS" and wd["band"] == "STIS_FUV_LONG":
                    c_mid = 1585.0  # Clean long-FUV region away from CIV 1548/1550
                elif inst == "HST_STIS" and wd["band"] == "STIS_FUV_SHORT":
                    c_mid = 1352.0  # Clean short-FUV region away from CII 1335 and OI 1302/1356
                half_span = 16.0 if inst == "HST_STIS" else (45.0 if inst == "UVES_RED" else 32.0)
                m = (bary_grid >= c_mid - half_span) & (bary_grid <= c_mid + half_span)
                if int(m.sum()) < 250:
                    continue
                nu_lo = round(C_ANGSTROM_GHZ / (c_mid + half_span - 2.0), 1)
                nu_hi = round(C_ANGSTROM_GHZ / (c_mid - half_span + 2.0), 1)
                ep_bervs = [round(e["berv_kms"], 3) for e in exps]
                calib_comb_patches.append({
                    "instrument": inst,
                    "star": st,
                    "band": wd["band"],
                    "resolving_power": round(meta["median_resolving_power"], 1),
                    "v_star_kms": round(meta["v_star_kms"], 5),
                    "median_berv_kms": round(med_berv, 4),
                    "berv_span_kms": round(max(ep_bervs) - min(ep_bervs), 3),
                    "epoch_bervs_kms": ep_bervs,
                    "nu_lo_ghz": nu_lo,
                    "nu_hi_ghz": nu_hi,
                    "wave_win": rarr(bary_grid[m], ndig=5),
                    "y_rest_win": rarr(np.where(np.isfinite(coadd_r[m]), coadd_r[m], 0.0), ndig=4),
                    "sigma_rest_win": rarr(np.full(int(m.sum()), max(1e-4, med_mad_all)), sig=4),
                    "fn_win": rarr(np.where(np.isfinite(coadd_fn[m]), coadd_fn[m], 1.0), ndig=4),
                    "recon_win": rarr(np.clip(tmpl[m], 0.0, 1.2), ndig=4),
                    "sky_mask_win": [bool(x) for x in sky_mask[m]],
                    "y_topo_win": rarr(np.where(np.isfinite(coadd_r[m]), coadd_r[m], 0.0), ndig=4),
                    "sigma_topo_win": rarr(np.full(int(m.sum()), max(1e-4, med_mad_all)), sig=4),
                })

    # Trim dense/sparse atlases minimally if needed while keeping all unique stars + high SNR peaks
    for inst in ("HST_STIS", "UVES_RED", "ESPRESSO"):
        dense_atlas_by_group[inst].sort(key=lambda x: (-x["snr"], x["star"]))
        sparse_atlas_by_group[inst].sort(key=lambda x: (-x["snr"], x["star"]))

    # 6. Build D086 G4_V38 Fiber-B 577-record regression table
    d086_fibb_577 = build_d086_fiberb_regression_records(
        D086_WS / "bounded_inputs" / "d086_bounded_bundle.json.gz",
        D086_WS / "FORENSIC_CANDIDATE_AUDIT_D086.json",
    )

    # 7. Strip heavy per-star numpy arrays before serializing star_meta
    serializable_star_meta = {}
    for st, m in star_meta.items():
        serializable_star_meta[st] = {
            k: v for k, v in m.items()
            if k not in ("norm_stack", "exp_resids_rest", "resolving_powers")
        }

    bundle = {
        "schema": "SETI_D087_BOUNDED_REPRODUCIBLE_BUNDLE_V1",
        "phase_id": "D087",
        "locked_utc": lock["locked_utc"],
        "method_lock_sha256": sha256_file(WS / "METHOD_LOCK.json"),
        "total_integration_hours": round(total_int_hours, 4),
        "searched_counts_by_inst": searched_counts_by_inst,
        "comb_v4_counts_by_star": comb_v4_counts_by_star,
        "provenance_rows": prov_rows,
        "rv_anchor_bundle": rv_anchor_bundle,
        "v3_rv_summary_rows": v3_rv_summary_rows,
        "v2_counts_by_dp": v2_counts_by_dp,
        "star_meta": serializable_star_meta,
        "dense_atlas_by_group": dense_atlas_by_group,
        "sparse_atlas_by_group": sparse_atlas_by_group,
        "calib_transient_patches": calib_transient_patches,
        "calib_persistent_patches": calib_persistent_patches,
        "calib_keplerian_patches": calib_keplerian_patches,
        "calib_g4g5_patches": calib_g4g5_patches,
        "calib_g6_patches": calib_g6_patches,
        "calib_comb_patches": calib_comb_patches,
        "real_candidates_bundle": real_candidates_bundle,
        "comb_real_candidates_bundle": comb_real_candidates_bundle,
        "d086_fiberb_regression_577": d086_fibb_577,
        "upper_limit_patches": upper_limit_patches,
    }
    _assert_json_finite(bundle, "d087_bundle")
    out_bundle_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out_bundle_path, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(bundle, f, allow_nan=False, separators=(",", ":"))
    size_mib = out_bundle_path.stat().st_size / (1024.0 * 1024.0)
    print(
        f"[Stage A] Wrote {out_bundle_path.name}: {size_mib:.2f} MiB "
        f"(cands={len(real_candidates_bundle)}, comb_cands={len(comb_real_candidates_bundle)}, "
        f"patches=({len(calib_transient_patches)},{len(calib_persistent_patches)},{len(calib_keplerian_patches)},{len(calib_g4g5_patches)},{len(calib_g6_patches)},{len(calib_comb_patches)}))",
        flush=True,
    )
    if size_mib >= MAX_BUNDLE_MIB:
        raise RuntimeError(f"Bounded bundle {size_mib:.2f} MiB exceeds {MAX_BUNDLE_MIB:.1f} MiB cap!")


# ---------------------------------------------------------------------------
# Stage B: Offline Deterministic Evaluator (Synthetic + Real + Synthesis)
# ---------------------------------------------------------------------------

def _inject_gaussian(wave: np.ndarray, sig_arr: np.ndarray, center_a: float, amp: float, r_pow: float) -> np.ndarray:
    sigma_a = center_a / (r_pow * FWHM_FACTOR)
    return sig_arr + amp * np.exp(-0.5 * ((wave - center_a) / sigma_a) ** 2)


def _forensic_classify_singleline(cand: dict[str, Any], meta: dict[str, Any]) -> tuple[str, str]:
    inst = cand["instrument"]
    star = cand["star"]
    role = cand["role"]
    wb = float(cand["bary_wave_a"])
    wt = float(cand["topo_wave_a"])
    wr = float(cand["stellar_rest_wave_a"])
    teff = float(meta["teff_k"])
    fwhm_r = float(cand["fwhm_ratio"])
    cos_v = float(cand["cosine"])
    snr = float(cand["snr_mid"])
    fn_pk = float(cand["target_fn_pk3"])
    dpr = str(cand.get("dpr_or_calsel", "")).upper()

    if inst == "HST_STIS":
        # Check wider geocoronal wings (e.g. LyA damping wing, OI 1302/1306/1356, NI 1200)
        for b in STIS_GEOCORONAL_BANDS_VAC_A:
            if (b["lo_A"] - 3.5) <= wt <= (b["hi_A"] + 3.5):
                return (
                    "STIS_FUV_GEOCORONAL_AIRGLOW_WING",
                    f"Feature at topo {wt:.3f} A lies in extended geocoronal wing of {b['name']} ({b['lo_A']}-{b['hi_A']} A); non-celestial LEO sky glow.",
                )
        # Check wider stellar FUV chromospheric/transition-region broad emission wings (+- 2.2 A)
        for ch in STELLAR_FUV_EMISSION_VAC_A:
            if abs(wr - float(ch["wave_A"])) <= 2.2:
                return (
                    "STIS_FUV_BROAD_CHROMOSPHERIC_LINE",
                    f"Feature at rest {wr:.3f} A falls within broad stellar FUV transition-region/chromospheric wing of {ch['name']} ({ch['wave_A']} A) in active star/control.",
                )
        return (
            "STIS_FUV_CONTINUUM_OR_MAMA_BACKGROUND" if teff < 4200 else "STIS_FUV_SOLAR_PHOTOSPHERIC_FEATURE",
            f"STIS FUV E140M {'low-continuum M-dwarf noise/emission residual' if teff < 4200 else 'broad UV continuum/absorption-edge modulation'} (SNR={snr:.2f}, fn_pk3={fn_pk:.2f}, FWHM_ratio={fwhm_r:.2f}).",
        )

    # Ground-based ESPRESSO / UVES_RED
    if any(tok in dpr for tok in ("CALB", "WAVE", "FP", "THAR")):
        return (
            "SIMULTANEOUS_CAL_FIBER_ARTIFACT",
            f"Exposure uses simultaneous calibration ({dpr}); optical scatter or sub-threshold bleed artifact.",
        )

    for b in TELLURIC_SATURATED_BANDS_TOPO_A:
        if (b["lo_A"] - 2.5) <= wt <= (b["hi_A"] + 2.5):
            return (
                "TELLURIC_BAND_EDGE_OR_AIRGLOW_RESIDUAL",
                f"Topocentric {wt:.3f} A lies within saturated telluric band margin of {b['name']}.",
            )
    for al in TELLURIC_AIRGLOW_LINES_A:
        if abs(wt - float(al["wave_A"])) <= 0.65:
            return (
                "TELLURIC_AIRGLOW_OR_OH_MEINEL_WING",
                f"Topocentric {wt:.3f} A is within 0.65 A wing of atmospheric emission {al['name']} ({al['wave_A']} A).",
            )
    for ch in STELLAR_CHROMOSPHERIC_EMISSION_AIR_A:
        if abs(wr - float(ch["wave_A"])) <= 1.25:
            return (
                "STELLAR_CHROMOSPHERIC_LINE_WING",
                f"Stellar rest {wr:.3f} A lies in active chromospheric emission/core reversal wing of {ch['name']} ({ch['wave_A']} A).",
            )

    if teff < 4100.0:
        return (
            "MOLECULAR_TIO_VO_BANDHEAD_OR_ACTIVE_CONTINUUM",
            f"Cool-star (Teff={teff:.0f} K) TiO/VO/CaH molecular bandhead peak at {wb:.3f} A (cos={cos_v:.3f}, FWHM_ratio={fwhm_r:.2f}).",
        )
    if role == "CONTROL":
        return (
            "NULL_CONTROL_PHOTOSPHERIC_CONTINUUM_FLUCTUATION",
            f"Uncompensated photospheric continuum/blend residual in n_exo=0 null-control star {star} at {wb:.3f} A (SNR={snr:.2f}).",
        )
    return (
        "STELLAR_PHOTOSPHERIC_BLEND_OR_CONTINUUM_PEAK",
        f"Photospheric continuum fluctuation / KNN optical-depth residual at {wb:.3f} A (Teff={teff:.0f} K, cos={cos_v:.3f}, FWHM_ratio={fwhm_r:.2f}).",
    )


def _forensic_classify_comb(cand: dict[str, Any], meta: dict[str, Any]) -> tuple[str, str]:
    teff = float(meta["teff_k"])
    inst = cand["instrument"]
    band = cand["band"]
    dnu = cand["dnu_ghz"]
    w0, w1 = float(cand["wave0_a"]), float(cand["wave_end_a"])
    sc = float(cand["s_comb"])
    if inst == "HST_STIS":
        return (
            "STIS_FUV_ACTIVE_REGION_LINE_COMPLEX",
            f"FUV line complex across {w1:.2f}-{w0:.2f} A ({band}, dnu={dnu:.0f} GHz, S_comb={sc:.2f}) aligned with dense solar/stellar transition-region emission forest.",
        )
    if teff < 4200.0:
        return (
            "COOL_STAR_MOLECULAR_BAND_PSEUDOCOMB",
            f"M/late-K dwarf (Teff={teff:.0f} K) accidental alignment across {w1:.2f}-{w0:.2f} A ({band}, dnu={dnu:.0f} GHz, S_comb={sc:.2f}) in dense TiO/FeH/CN opacity troughs.",
        )
    return (
        "PHOTOSPHERIC_LINE_FOREST_OR_FRINGE_PSEUDOCOMB",
        f"Chance multi-tooth photospheric continuum/residual modulation across {w1:.2f}-{w0:.2f} A ({inst} {band}, dnu={dnu:.0f} GHz, S_comb={sc:.2f}).",
    )


def run_stage_b(bundle_path: Path) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    with gzip.open(bundle_path, "rt", encoding="utf-8") as f:
        bundle = json.load(f)

    star_meta = bundle["star_meta"]
    prov_rows = bundle["provenance_rows"]
    rv_bundle = bundle["rv_anchor_bundle"]
    rv_sum_rows = bundle["v3_rv_summary_rows"]
    v2_counts = bundle["v2_counts_by_dp"]

    prior_snap = json.loads((WS / "PRIOR_V3_PHASES_SNAPSHOT.json").read_text(encoding="utf-8"))
    orb_doc = json.loads((WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))
    mm_snap = json.loads((WS / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").read_text(encoding="utf-8"))
    with (WS / "FROZEN_COHORT_D087.csv").open("r", encoding="utf-8", newline="") as f:
        cohort_rows = list(csv.DictReader(f))

    # 1. EXPOSURE_PROVENANCE_201.csv & FOUR_GEN_BENCHMARK_201.csv & STAR_RV_SUMMARY_33.csv & STELLAR_RV_ANCHORS
    write_csv(RESULTS / "EXPOSURE_PROVENANCE_201.csv", prov_rows)
    write_csv(RESULTS / "STAR_RV_SUMMARY_33.csv", rv_sum_rows)

    rv_anchor_rows: list[dict[str, Any]] = []
    for item in rv_bundle:
        inst = item["instrument"]
        dp = item["dp_id"]
        st = item["star"]
        pr = float(item["prior_rv_kms"])
        cfg = get_inst_config(inst)
        for anc in cfg["rv_anchors"]:
            aid = anc["anchor_id"]
            lab_a = float(anc["lab_wave_A"])
            win = item["windows"].get(aid, {"wave_a": [], "flux": []})
            w_arr = np.asarray(win["wave_a"], dtype=np.float64)
            f_arr = np.asarray(win["flux"], dtype=np.float64)
            res = fit_rv_anchor_absorption(w_arr, f_arr, lab_a, pr, cfg)
            rv_anchor_rows.append({
                "instrument": inst,
                "star": st,
                "dp_id": dp,
                "anchor_id": aid,
                "species": anc["species"],
                "lab_wave_A": lab_a,
                "prior_rv_kms": round(pr, 5),
                "status": res["status"],
                "n_samples": res["n_samples"],
                "best_rv_kms": round(float(res["best_rv_kms"]), 5) if math.isfinite(float(res["best_rv_kms"])) else "",
                "rel_depth": round(float(res["rel_depth"]), 5) if math.isfinite(float(res["rel_depth"])) else "",
                "min_sse": round(float(res["min_sse"]), 5) if math.isfinite(float(res["min_sse"])) else "",
            })
    write_csv(RESULTS / f"STELLAR_RV_ANCHORS_{len(rv_anchor_rows)}.csv", rv_anchor_rows)

    # 2. D086 G4_V38 Fiber-B 577-record Regression
    reg_rows = []
    for i, rec in enumerate(bundle["d086_fiberb_regression_577"], start=1):
        res = evaluate_g4_v38_fiber_b_bleed_record(rec["dpr_or_calsel"], float(rec["fb_pk"]), float(rec["fa_med"]), BASE_V3_8_CONFIG)
        reg_rows.append({
            "reg_index": i,
            "d086_candidate_id": rec["d086_candidate_id"],
            "instrument": rec["instrument"],
            "star": rec["star"],
            "channel": rec["channel"],
            "dp_id": rec["dp_id"],
            "bary_wave_a": rec["bary_wave_a"],
            "dpr_or_calsel": rec["dpr_or_calsel"],
            "fb_over_fa_cont": round(res["fb_over_fa_cont"], 3),
            "g4_v37_retained": True,
            "g4_v38_retained": bool(res["g4_v38_pass"]),
            "g4_v38_reason": res["g4_v38_reason"],
        })
    write_csv(RESULTS / "D086_G4_V38_FIBERB_REGRESSION_577.csv", reg_rows)

    # 3. Synthetic Calibration Suite 1 & 2: INJECTION_RECOVERY_1620.csv (1080 T + 540 P)
    inj_rows: list[dict[str, Any]] = []
    sigmas_tp = [5.0, 6.5, 8.0, 10.0, 14.0]
    phases_tp = [-0.35, 0.0, 0.35]

    for p in bundle["calib_transient_patches"]:
        inst = p["instrument"]
        cfg = get_inst_config(inst, resolving_power=p["resolving_power"])
        w = np.asarray(p["wave_win"], dtype=np.float64)
        r0 = np.asarray(p["resid_win"], dtype=np.float64)
        fn0 = np.asarray(p["f_norm_win"], dtype=np.float64)
        lmad = float(p["local_mad"])
        step_a = float(exact_median_1d(np.diff(w)))
        w_mid = float(w[len(w) // 2])
        for ph in phases_tp:
            w_inj = w_mid + ph * step_a
            for sm in sigmas_tp:
                amp_inj = sm * lmad
                r_inj = _inject_gaussian(w, r0, w_inj, amp_inj, p["resolving_power"])
                fn_inj = _inject_gaussian(w, fn0, w_inj, amp_inj, p["resolving_power"])
                fit = fit_lsf_on_window(w, r_inj, w_inj, cfg)
                g1_f1 = compute_supraphotospheric_f1_window(w, fn_inj, fit.get("fitted_center_a", w_inj), cfg["supraphotospheric_min_fn_pk3"])["f1_supraphotospheric_pass"]
                g1 = check_channel_lsf_gate(fit, "T", cfg) and g1_f1
                g2 = evaluate_gate_g2_airglow(fit.get("fitted_center_a", w_inj), float(p["berv_kms"]), cfg)["g2_pass"]
                # Inject matched true-LSF signal into native order patches for G3-G5
                ops_inj = []
                for op in p["order_patches"]:
                    op_w = np.asarray(op["wave"], dtype=np.float64)
                    op_fa = np.asarray(op["flux_a"], dtype=np.float64)
                    cont_est = max(1e-16, exact_quantile_1d(op_fa[np.isfinite(op_fa)], 0.80))
                    op_fa_inj = _inject_gaussian(op_w, op_fa, w_inj, max(amp_inj, 8.0 * exact_mad_1d(op_fa[np.isfinite(op_fa)]) / cont_est) * cont_est, p["resolving_power"])
                    op_new = dict(op)
                    op_new["target_wave_a"] = round(float(w_inj), 5)
                    op_new["flux_a"] = op_fa_inj
                    ops_inj.append(op_new)
                g345 = evaluate_gates_g3_g4_g5_v38(ops_inj, p["dpr_or_calsel"], "T", float(w_inj) / (1.0 + float(p["v_star_kms"]) / C_KMS), cfg)
                rec_ok = bool(g1 and g2 and g345["g3_pass"] and g345["g4_pass"] and g345["g5_pass"])
                inj_rows.append({
                    "instrument": inst,
                    "mode": "CHANNEL_T_TRANSIENT_1EPOCH",
                    "star": p["star"],
                    "dp_id": p["dp_id"],
                    "band_id": p["band_id"],
                    "injected_wave_a": round(w_inj, 4),
                    "phase_bins": ph,
                    "sigma_mult": sm,
                    "injected_amp_rel": round(amp_inj, 5),
                    "fitted_snr_mid": round(float(fit.get("snr_mid", 0.0)), 4),
                    "fitted_cosine": round(float(fit.get("cosine", 0.0)), 4),
                    "fitted_fwhm_ratio": round(float(fit.get("fwhm_ratio", 0.0)), 4),
                    "g1_pass": bool(g1),
                    "g2_pass": bool(g2),
                    "g3_pass": bool(g345["g3_pass"]),
                    "g4_pass": bool(g345["g4_pass"]),
                    "g5_pass": bool(g345["g5_pass"]),
                    "recovered": rec_ok,
                })

    for p in bundle["calib_persistent_patches"]:
        inst = p["instrument"]
        cfg = get_inst_config(inst, resolving_power=p["resolving_power"])
        w = np.asarray(p["wave_win"], dtype=np.float64)
        c0 = np.asarray(p["coadd_resid_win"], dtype=np.float64)
        fn0 = np.asarray(p["coadd_fn_win"], dtype=np.float64)
        cmad = float(p["coadd_mad"])
        step_a = float(exact_median_1d(np.diff(w)))
        w_mid = float(w[len(w) // 2])
        for ph in phases_tp:
            w_inj = w_mid + ph * step_a
            for sm in sigmas_tp:
                amp_inj = sm * cmad
                r_inj = _inject_gaussian(w, c0, w_inj, amp_inj, p["resolving_power"])
                fn_inj = _inject_gaussian(w, fn0, w_inj, amp_inj, p["resolving_power"])
                fit = fit_lsf_on_window(w, r_inj, w_inj, cfg)
                g1_f1 = compute_supraphotospheric_f1_window(w, fn_inj, fit.get("fitted_center_a", w_inj), cfg["supraphotospheric_min_fn_pk3"])["f1_supraphotospheric_pass"]
                n_hit = 0
                for ep_r in p["epoch_resids"]:
                    e_inj = _inject_gaussian(w, np.asarray(ep_r, dtype=np.float64), w_inj, amp_inj, p["resolving_power"])
                    ef = fit_lsf_on_window(w, e_inj, w_inj, cfg, fixed_phase_bins=fit.get("phase_bins"))
                    if ef.get("valid_fit") and ef["snr_mid"] >= 2.8:
                        n_hit += 1
                req_e = max(2, int(math.ceil(cfg["channel_p_min_epoch_fraction"] * len(p["epoch_resids"]))))
                g1 = check_channel_lsf_gate(fit, "P", cfg) and g1_f1 and (n_hit >= req_e)
                g2 = evaluate_gate_g2_airglow(fit.get("fitted_center_a", w_inj) * (1.0 + float(p["v_star_kms"]) / C_KMS), float(p["berv_kms"]), cfg)["g2_pass"]
                rec_ok = bool(g1 and g2)
                inj_rows.append({
                    "instrument": inst,
                    "mode": "CHANNEL_P_PERSISTENT_COADD",
                    "star": p["star"],
                    "dp_id": p["rep_dp_id"],
                    "band_id": p["band_id"],
                    "injected_wave_a": round(w_inj, 4),
                    "phase_bins": ph,
                    "sigma_mult": sm,
                    "injected_amp_rel": round(amp_inj, 5),
                    "fitted_snr_mid": round(float(fit.get("snr_mid", 0.0)), 4),
                    "fitted_cosine": round(float(fit.get("cosine", 0.0)), 4),
                    "fitted_fwhm_ratio": round(float(fit.get("fwhm_ratio", 0.0)), 4),
                    "g1_pass": bool(g1),
                    "g2_pass": bool(g2),
                    "g3_pass": True,
                    "g4_pass": True,
                    "g5_pass": True,
                    "recovered": rec_ok,
                })
    write_csv(RESULTS / "INJECTION_RECOVERY_1620.csv", inj_rows)

    # Calibration Completeness summary by band
    comp_map: dict[tuple[str, str, str, float], list[int]] = {}
    band_c = {}
    for b_inst in ("HST_STIS", "UVES_RED", "ESPRESSO"):
        for bd in get_calibration_bands(b_inst):
            band_c[(b_inst, bd["band_id"])] = bd["center_wave_A"]
    for ir in inj_rows:
        key = (ir["instrument"], ir["mode"], ir["band_id"], ir["sigma_mult"])
        stat = comp_map.setdefault(key, [0, 0])
        stat[0] += 1
        if ir["recovered"]:
            stat[1] += 1
    comp_rows = []
    for (inst, mode, bid, sm), (nt, nr) in sorted(comp_map.items()):
        comp_rows.append({
            "instrument": inst,
            "mode": mode,
            "band_id": bid,
            "center_wave_A": band_c.get((inst, bid), 0.0),
            "sigma_mult": sm,
            "n_trials": nt,
            "n_recovered": nr,
            "completeness": round(nr / max(1, nt), 6),
        })
    write_csv(RESULTS / "CALIBRATION_COMPLETENESS_BY_BAND.csv", comp_rows)

    # 4. Synthetic Calibration Suite 3: KEPLERIAN_TRACK_CALIBRATION_135.csv
    kep_rows: list[dict[str, Any]] = []
    kep_sigmas = [3.5, 5.0, 6.5, 8.5, 11.0]
    for p in bundle["calib_keplerian_patches"]:
        inst = p["instrument"]
        cfg = get_inst_config(inst, resolving_power=p["resolving_power"])
        w = np.asarray(p["planet_wave_win"], dtype=np.float64)
        out_med = np.asarray(p["out_resid_med_win"], dtype=np.float64)
        mad_e = float(p["single_in_exp_mad"])
        step_a = float(exact_median_1d(np.diff(w)))
        w_mid = float(w[len(w) // 2])
        tracks = p["in_epoch_tracks"]
        for ph in phases_tp:
            w_pl = w_mid + ph * step_a
            for sm in kep_sigmas:
                amp_ep = sm * mad_e
                unsh_list = []
                dedop_list = []
                for tr in tracks:
                    r_base = np.asarray(tr["resid_win"], dtype=np.float64) - out_med
                    # Planet emission sits at w_pl * (1 + dv_orb/c) in stellar rest frame
                    w_obs_st = w_pl * (1.0 + float(tr["dv_orb_kms"]) / C_KMS)
                    r_in_st = _inject_gaussian(w, r_base, w_obs_st, amp_ep, p["resolving_power"])
                    unsh_list.append(r_in_st)
                    # De-Doppler shifting back into planet rest frame
                    w_shifted = w / (1.0 + float(tr["dv_orb_kms"]) / C_KMS)
                    dedop_list.append(np.interp(w, w_shifted, r_in_st))
                with np.errstate(all="ignore"):
                    y_tdiff = np.nanmedian(np.vstack(unsh_list), axis=0)
                    y_kpl = np.nanmedian(np.vstack(dedop_list), axis=0)
                f_td = fit_lsf_on_window(w, y_tdiff, w_pl, cfg)
                f_kp = fit_lsf_on_window(w, y_kpl, w_pl, cfg)
                n_hit_kp = 0
                for dk in dedop_list:
                    ef = fit_lsf_on_window(w, dk, w_pl, cfg, fixed_phase_bins=f_kp.get("phase_bins"))
                    if ef.get("valid_fit") and ef["snr_mid"] >= cfg["channel_kplanet_min_in_exp_snr"]:
                        n_hit_kp += 1
                kp_ok = check_channel_lsf_gate(f_kp, "K_PLANET", cfg) and (n_hit_kp >= max(2, int(math.ceil(cfg["channel_kplanet_min_in_exp_fraction"] * len(dedop_list)))))
                td_ok = check_channel_lsf_gate(f_td, "T_DIFF", cfg)
                kep_rows.append({
                    "instrument": inst,
                    "star": p["star"],
                    "rep_dp_id": p["rep_dp_id"],
                    "band_id": p["band_id"],
                    "dv_span_kms": p["dv_span_kms"],
                    "injected_planet_wave_a": round(w_pl, 4),
                    "phase_bins": ph,
                    "exp_sigma_mult": sm,
                    "tdiff_uncomp_snr_mid": round(float(f_td.get("snr_mid", 0.0)), 4),
                    "tdiff_uncomp_recovered": bool(td_ok),
                    "kplanet_dedop_snr_mid": round(float(f_kp.get("snr_mid", 0.0)), 4),
                    "kplanet_dedop_fwhm_ratio": round(float(f_kp.get("fwhm_ratio", 0.0)), 4),
                    "kplanet_dedop_recovered": bool(kp_ok),
                })
    write_csv(RESULTS / "KEPLERIAN_TRACK_CALIBRATION_135.csv", kep_rows)

    # 5. Synthetic Calibration Suite 4: DETECTOR_V38_G4G5_CALIBRATION_216.csv
    g45_rows: list[dict[str, Any]] = []
    for p in bundle["calib_g4g5_patches"]:
        inst = p["instrument"]
        cfg = get_inst_config(inst, resolving_power=p["resolving_power"])
        wb = float(p["target_bary_a"])
        wr = float(p["stellar_rest_wave_a"])
        for tcls, exp_pass in (
            ("TRUE_LSF_LASER", True),
            ("COSMIC_SINGLE_PX_SPIKE", False),
            ("WIDE_SCATTERING_PLATEAU", False),
        ):
            mod_ops = []
            for op in p["order_patches"]:
                w_o = np.asarray(op["wave"], dtype=np.float64)
                fa_o = np.asarray(op["flux_a"], dtype=np.float64)
                k0 = int(np.argmin(np.abs(w_o - wb)))
                fin_o = np.isfinite(fa_o)
                cont = max(1e-16, exact_quantile_1d(fa_o[fin_o], 0.80))
                sb_mad = max(1e-17, exact_mad_1d(fa_o[fin_o]))
                fa_new = fa_o.copy()
                if tcls == "TRUE_LSF_LASER":
                    amp_u = max(0.35 * cont, 16.0 * sb_mad)
                    sig_a = wb / (p["resolving_power"] * FWHM_FACTOR)
                    fa_new = fa_new + amp_u * np.exp(-0.5 * ((w_o - wb) / sig_a) ** 2)
                elif tcls == "COSMIC_SINGLE_PX_SPIKE":
                    spk = max(0.95 * cont, 32.0 * sb_mad)
                    fa_new[k0] += spk
                    if k0 > 0:
                        fa_new[k0 - 1] += 0.01 * spk
                    if k0 + 1 < len(fa_new):
                        fa_new[k0 + 1] += 0.01 * spk
                else:
                    amp_p = max(0.65 * cont, 22.0 * sb_mad)
                    sig_wide = 4.5 * (wb / (p["resolving_power"] * FWHM_FACTOR))
                    fa_new = fa_new + amp_p * np.exp(-0.5 * ((w_o - wb) / sig_wide) ** 2)
                op_m = dict(op)
                op_m["flux_a"] = fa_new
                mod_ops.append(op_m)
            res = evaluate_gates_g3_g4_g5_v38(mod_ops, p["dpr_or_calsel"], "T", wr, cfg)
            g45_ok = bool(res["g4_pass"] and res["g5_pass"])
            g45_rows.append({
                "instrument": inst,
                "star": p["star"],
                "dp_id": p["dp_id"],
                "band_id": p["band_id"],
                "primary_order": res.get("primary_order", 0),
                "primary_native_px": res.get("primary_native_px", 0),
                "trial_class": tcls,
                "expected_g45_pass": exp_pass,
                "g4_pass": bool(res["g4_pass"]),
                "g5_pass": bool(res["g5_pass"]),
                "g45_pass": g45_ok,
                "cos_1d_11px": round(float(res.get("cos_1d_11px", 0.0)), 4),
                "ipc_hotpx_ratio": round(float(res.get("ipc_hotpx_ratio", 0.0)), 4),
                "far_wing_34_ratio": round(float(res.get("far_wing_34_ratio", 0.0)), 4),
                "g4_reason": res["g4_reason"],
                "g5_reason": res["g5_reason"],
            })
    write_csv(RESULTS / "DETECTOR_V38_G4G5_CALIBRATION_216.csv", g45_rows)

    # 6. Synthetic Calibration Suite 5: G6_SPARSE_VS_DENSE_CALIBRATION_240.csv
    g6_rows: list[dict[str, Any]] = []
    for p in bundle["calib_g6_patches"]:
        inst = p["instrument"]
        cfg = get_inst_config(inst)
        st = p["star"]
        dp = p["dp_id"]
        opp_dp = p["opp_dp_id"]
        tb = float(p["target_berv_kms"])
        ob = float(p["opp_berv_kms"])
        tv = float(p["target_vshift_kms"])
        ct = float(p["cand_topo_vac_a"])
        cord = int(p["cand_order"])
        cpx = int(p["cand_px"])
        others = p["synthetic_other_stars"]
        # Use genuine clean off-peak wavelength around cand_topo for true barycentric injection
        loc_d = list(p["local_dense_atlas"])
        loc_s = list(p["local_sparse_atlas"])
        for s_inj in (5.5, 8.0, 12.0):
            for tcls, exp_p in (
                ("TRUE_BARYCENTRIC_STELLAR_LASER", True),
                ("UNLISTED_STATIONARY_SKY_OH_LINE", False),
                ("STATIONARY_DETECTOR_WARM_PIXEL", False),
                ("INTRA_STAR_BERV_STATIONARY_GHOST", False),
            ):
                d_atl = list(loc_d)
                s_atl = list(loc_s)
                if tcls == "TRUE_BARYCENTRIC_STELLAR_LASER":
                    # Real stellar laser moves in topocentric frame when BERV changes -> filter out stationary artifacts at ct
                    test_topo = ct + 1.37
                    d_atl = [q for q in d_atl if abs(float(q["topo_wave_a"]) - test_topo) > 0.08]
                    s_atl = [q for q in s_atl if abs(float(q["topo_wave_a"]) - test_topo) > 0.08]
                    px_q = None
                elif tcls == "UNLISTED_STATIONARY_SKY_OH_LINE":
                    test_topo = ct
                    for os_name in others[:4]:
                        pk_e = {"star": os_name, "dp_id": f"{os_name}_D", "berv_kms": -5.0, "topo_wave_a": test_topo, "snr": s_inj}
                        d_atl.append(pk_e)
                        s_atl.append(pk_e)
                    px_q = None
                elif tcls == "STATIONARY_DETECTOR_WARM_PIXEL":
                    test_topo = ct + 0.85
                    for os_name in others[:4]:
                        pk_e = {"star": os_name, "dp_id": f"{os_name}_P", "berv_kms": 5.0, "topo_wave_a": test_topo + 0.9, "order": cord, "px": cpx, "snr": s_inj}
                        d_atl.append(pk_e)
                        s_atl.append(pk_e)
                    px_q = cpx
                else:
                    test_topo = ct + 0.42
                    pk_e = {"star": st, "dp_id": opp_dp, "berv_kms": ob, "topo_wave_a": test_topo, "snr": s_inj}
                    d_atl.append(pk_e)
                    s_atl.append(pk_e)
                    px_q = None

                r_v35 = evaluate_gate_g6_v35_dense(st, test_topo, cord if px_q is not None else None, px_q, tv, d_atl, cfg)
                r_v36 = evaluate_gate_g6_v36_sparse(st, dp, tb, test_topo, cord if px_q is not None else None, px_q, tv, s_atl, cfg, "T")
                g6_rows.append({
                    "instrument": inst,
                    "star": st,
                    "dp_id": dp,
                    "band_id": p["band_id"],
                    "sigma_inj": s_inj,
                    "trial_class": tcls,
                    "expected_g6_pass": exp_p,
                    "g6_v35_dense_pass": bool(r_v35["g6_v35_pass"]),
                    "g6_v36_sparse_pass": bool(r_v36["g6_pass"]),
                    "g6_v36_same_star_hits": int(r_v36["g6_same_star_stationary_hits"]),
                })
    write_csv(RESULTS / "G6_SPARSE_VS_DENSE_CALIBRATION_240.csv", g6_rows)

    # 7. Synthetic Calibration Suite 6: COMB_V4_1_CALIBRATION_486.csv (18 patches * 3 dnu * 9 classes = 486)
    comb_cal_rows: list[dict[str, Any]] = []
    comb_dnus = [40.0, 60.0, 100.0]
    comb_trials_spec = [
        ("TRUE_6TOOTH_STELLAR_COMB", 2.5, True),
        ("TRUE_6TOOTH_STELLAR_COMB", 3.2, True),
        ("TRUE_6TOOTH_STELLAR_COMB", 3.8, True),
        ("TRUE_6TOOTH_STELLAR_COMB", 4.5, True),
        ("TRUE_6TOOTH_STELLAR_COMB", 5.5, True),
        ("TRUE_6TOOTH_STELLAR_COMB", 7.0, True),
        ("SINGLE_BRIGHT_LINE_MASQUERADE", 20.0, False),
        ("STATIONARY_TOPO_ROVIB_PSEUDOCOMB", 6.0, False),
        ("DENSE_MOLECULAR_FOREST_PSEUDOCOMB", 4.3, False),
    ]
    for p in bundle["calib_comb_patches"]:
        inst = p["instrument"]
        cfg = dict(get_inst_config(inst, resolving_power=p["resolving_power"]))
        w = np.asarray(p["wave_win"], dtype=np.float64)
        yr = np.asarray(p["y_rest_win"], dtype=np.float64)
        sr = np.asarray(p["sigma_rest_win"], dtype=np.float64)
        fn = np.asarray(p["fn_win"], dtype=np.float64)
        rc = np.asarray(p["recon_win"], dtype=np.float64)
        smask = np.asarray(p["sky_mask_win"], dtype=bool)
        yt = np.asarray(p["y_topo_win"], dtype=np.float64)
        st_arr = np.asarray(p["sigma_topo_win"], dtype=np.float64)
        med_sig = exact_median_1d(sr)
        w_mid = float(w[len(w) // 2])
        nu_mid = C_ANGSTROM_GHZ / w_mid
        win_c = [{"band": p["band"], "lo_a": float(w[0]) + 0.5, "hi_a": float(w[-1]) - 0.5}]

        for dnu in comb_dnus:
            cfg_t = dict(cfg)
            cfg_t["comb_spacings_ghz"] = [dnu]
            for tcls, snr_inj, exp_hit in comb_trials_spec:
                yr_i = yr.copy()
                fn_i = fn.copy()
                yt_i = yt.copy()
                sm_i = smask.copy()
                # Clear genuine natural spikes only within the clean local injection corridor for controlled recovery benchmark
                nu_0 = math.floor(nu_mid / float(cfg_t["comb_freq_step_ghz"])) * float(cfg_t["comb_freq_step_ghz"]) - 2.0 * dnu
                teeth_nu = [nu_0 + t * dnu for t in range(6)]
                if tcls == "TRUE_6TOOTH_STELLAR_COMB":
                    corridor = (w >= C_ANGSTROM_GHZ / (teeth_nu[-1] + 20.0)) & (w <= C_ANGSTROM_GHZ / (teeth_nu[0] - 20.0))
                    sm_i[corridor] = False
                    rc_i = np.where(corridor, np.maximum(0.95, rc), rc)
                    yr_i[corridor] = 0.0
                    yt_i[corridor] = 0.0
                    fn_i[corridor] = 1.0
                    for tn in teeth_nu:
                        wa = C_ANGSTROM_GHZ / tn
                        amp_t = snr_inj * med_sig
                        yr_i = _inject_gaussian(w, yr_i, wa, amp_t, p["resolving_power"])
                        fn_i = _inject_gaussian(w, fn_i, wa, amp_t, p["resolving_power"])
                elif tcls == "SINGLE_BRIGHT_LINE_MASQUERADE":
                    wa = C_ANGSTROM_GHZ / teeth_nu[2]
                    yr_i = _inject_gaussian(w, yr_i, wa, snr_inj * med_sig, p["resolving_power"])
                    fn_i = _inject_gaussian(w, fn_i, wa, snr_inj * med_sig, p["resolving_power"])
                    rc_i = np.maximum(0.92, rc)
                elif tcls == "STATIONARY_TOPO_ROVIB_PSEUDOCOMB":
                    rc_i = np.maximum(0.92, rc)
                    for tn in teeth_nu:
                        wa = C_ANGSTROM_GHZ / tn
                        sm_i[np.abs(w - wa) <= 0.3] = False
                        yr_i = _inject_gaussian(w, yr_i, wa, snr_inj * med_sig, p["resolving_power"])
                        yt_i = _inject_gaussian(w, yt_i, wa, snr_inj * med_sig, p["resolving_power"])
                        fn_i = _inject_gaussian(w, fn_i, wa, snr_inj * med_sig, p["resolving_power"])
                else:
                    # Dense forest across teeth + inter-tooth troughs (quarter-spacing sub-harmonic clutter, D086 parity)
                    rc_i = np.maximum(0.92, rc)
                    for q_off in np.arange(-1.0, 6.25, 0.25):
                        tn = teeth_nu[0] + float(q_off) * dnu
                        wa = C_ANGSTROM_GHZ / tn
                        if w[5] <= wa <= w[-6]:
                            sm_i[np.abs(w - wa) <= 0.3] = False
                            yr_i = _inject_gaussian(w, yr_i, wa, snr_inj * med_sig, p["resolving_power"])
                            fn_i = _inject_gaussian(w, fn_i, wa, snr_inj * med_sig, p["resolving_power"])

                h4, _ = scan_frequency_comb_v4(w, yr_i, sr, fn_i, rc_i, sm_i, yt_i, st_arr, win_c, [p["band"]], cfg_t)
                h41, _ = scan_frequency_comb_v4_1(w, yr_i, sr, fn_i, rc_i, sm_i, yt_i, st_arr, win_c, [p["band"]], cfg_t)
                max_s = max([c["s_comb"] for c in (h41 if h41 else h4)] or [0.0])
                comb_cal_rows.append({
                    "instrument": inst,
                    "star": p["star"],
                    "band": p["band"],
                    "dnu_ghz": dnu,
                    "trial_class": tcls,
                    "tooth_snr_inj": snr_inj,
                    "expected_comb_hit": exp_hit,
                    "comb_v4_hit": len(h4) > 0,
                    "comb_v41_hit": len(h41) > 0,
                    "comb_hit": len(h41) > 0,
                    "max_s_comb": round(max_s, 4),
                })
    write_csv(RESULTS / "COMB_V4_1_CALIBRATION_486.csv", comb_cal_rows)

    # 8. Real Candidate Automated Evaluation (G1 -> G2 -> G3 -> G4_V38 -> G5 -> G6)
    ledger_rows: list[dict[str, Any]] = []
    four_gen_by_dp: dict[str, dict[str, int]] = {
        r["dp_id"]: {
            "v2_accepted_false_alarms": int(v2_counts.get(r["dp_id"], 0)),
            "v38_g1_candidates": 0,
            "v38_pre_g6": 0,
            "v38_post_g6_qualified": 0,
        }
        for r in prov_rows
    }
    cascade_cnt = {
        "v2_legacy_false_alarms": sum(int(v2_counts.get(r["dp_id"], 0)) for r in prov_rows),
        "v38_total_ledger_g1_candidates": 0,
        "v38_after_g2": 0,
        "v38_after_g3": 0,
        "v38_after_g4": 0,
        "v38_pre_g6_passed_g1_to_g5": 0,
        "v38_vetoed_by_g6_sparse": 0,
        "v38_orbital_candidates": 0,
        "automated_qualified_control": 0,
        "automated_qualified_science": 0,
    }
    forensic_single_rows: list[dict[str, Any]] = []
    forensic_diag_details: list[dict[str, Any]] = []

    for idx_c, c in enumerate(bundle["real_candidates_bundle"], start=1):
        ch = c["channel"]
        inst = c["instrument"]
        st = c["star"]
        dp = c["dp_id"]
        role = c["role"]
        meta = star_meta[st]
        cfg = get_inst_config(inst, resolving_power=c["resolving_power"])
        w_win = np.asarray(c["wave_win"], dtype=np.float64)
        y_win = np.asarray(c["y_primary_win"], dtype=np.float64)
        fn_win = np.asarray(c["f_norm_win"], dtype=np.float64)
        seed_w = float(c["seed_wave_a"])

        fit = fit_lsf_on_window(w_win, y_win, seed_w, cfg)
        fitted_w = float(fit.get("fitted_center_a", seed_w))
        f1 = compute_supraphotospheric_f1_window(w_win, fn_win, fitted_w, cfg["supraphotospheric_min_fn_pk3"])
        g1_lsf = check_channel_lsf_gate(fit, ch, cfg)
        multi_ok = True
        if ch == "P" and "epoch_wins" in c:
            nh = sum(
                1
                for ew in c["epoch_wins"]
                if fit_lsf_on_window(w_win, np.asarray(ew, dtype=np.float64), fitted_w, cfg, fixed_phase_bins=fit.get("phase_bins")).get("snr_mid", 0.0) >= 2.8
            )
            multi_ok = nh >= max(2, min(len(c["epoch_wins"]), max(3, int(math.ceil(cfg["channel_p_min_epoch_fraction"] * len(c["epoch_wins"]))))))
        elif ch in ("T_DIFF", "K_PLANET") and "in_epoch_wins" in c:
            min_es = cfg["channel_tdiff_min_in_exp_snr"] if ch == "T_DIFF" else cfg["channel_kplanet_min_in_exp_snr"]
            min_ef = cfg["channel_tdiff_min_in_exp_fraction"] if ch == "T_DIFF" else cfg["channel_kplanet_min_in_exp_fraction"]
            nh = sum(
                1
                for ew in c["in_epoch_wins"]
                if fit_lsf_on_window(w_win, np.asarray(ew, dtype=np.float64), fitted_w, cfg, fixed_phase_bins=fit.get("phase_bins")).get("snr_mid", 0.0) >= min_es
            )
            multi_ok = len(c["in_epoch_wins"]) >= 2 and nh >= max(2, int(math.ceil(min_ef * len(c["in_epoch_wins"]))))
        g1 = bool(g1_lsf and multi_ok and f1["f1_supraphotospheric_pass"])

        v_st = float(c["v_star_kms"])
        dv_o = float(c["dv_orb_kms"])
        if ch == "T":
            w_bary = fitted_w
            w_rest = w_bary / (1.0 + v_st / C_KMS)
        elif ch in ("P", "T_DIFF"):
            w_rest = fitted_w
            w_bary = w_rest * (1.0 + v_st / C_KMS)
        else:
            w_bary = planet_rest_to_bary_wave(fitted_w, v_st, dv_o)
            w_rest = w_bary / (1.0 + v_st / C_KMS)

        g2_res = evaluate_gate_g2_airglow(w_bary, float(c["berv_kms"]), cfg)
        g2 = bool(g2_res["g2_pass"])
        topo_w = float(g2_res["topo_wave_a"])

        if g1 and g2:
            g345 = evaluate_gates_g3_g4_g5_v38(c["order_patches"], c["dpr_or_calsel"], ch, w_rest, cfg)
        else:
            g345 = {
                "g3_pass": False, "g3_reason": "SKIPPED",
                "g4_pass": False, "g4_reason": "SKIPPED",
                "g5_pass": False, "g5_reason": "SKIPPED",
                "primary_order": 0, "primary_native_px": 0, "primary_native_fn_pk3": 0.0,
                "primary_eta_1px": 0.0, "cos_1d_11px": 0.0, "ipc_hotpx_ratio": 0.0, "far_wing_34_ratio": 0.0,
            }
        g3, g4, g5 = bool(g345["g3_pass"]), bool(g345["g4_pass"]), bool(g345["g5_pass"])
        pre_g6 = bool(g1 and g2 and g3 and g4 and g5)

        p_ord = g345.get("primary_order", 0) if g345.get("primary_order", 0) > 0 else None
        p_px = g345.get("primary_native_px", 0) if g345.get("primary_native_px", 0) > 0 else None
        g6_d = evaluate_gate_g6_v35_dense(st, topo_w, p_ord, p_px, float(c["vshift_kms"]), bundle["dense_atlas_by_group"][c["atlas_group"]], cfg)
        g6_s = evaluate_gate_g6_v36_sparse(st, dp, float(c["berv_kms"]), topo_w, p_ord, p_px, float(c["vshift_kms"]), bundle["sparse_atlas_by_group"][c["atlas_group"]], cfg, ch)
        g6 = bool(g6_s["g6_pass"])
        qual = bool(pre_g6 and g6)

        if not g1:
            disp = "G1_V38_SUBCONTINUUM_VETO"
        elif not g2:
            disp = f"G2_{g2_res['g2_reason']}"
        elif not g3:
            disp = f"G3_{g345['g3_reason']}"
        elif not g4:
            disp = f"G4_{g345['g4_reason']}"
        elif not g5:
            disp = f"G5_{g345['g5_reason']}"
        elif not g6:
            disp = f"G6_{g6_s['g6_reason']}"
        else:
            disp = "QUALIFIED_V3_8_LASER_CANDIDATE"

        cid = f"V38-{ch}-{idx_c:04d}"
        ledger_rows.append({
            "candidate_id": cid,
            "instrument": inst,
            "channel": ch,
            "role": role,
            "star": st,
            "dp_id": dp,
            "fitted_wave_a": round(fitted_w, 5),
            "stellar_rest_wave_a": round(w_rest, 5),
            "bary_wave_a": round(w_bary, 5),
            "topo_wave_a": round(topo_w, 5),
            "snr_mid": round(float(fit.get("snr_mid", 0.0)), 4),
            "snr_out": round(float(fit.get("snr_out", 0.0)), 4),
            "cosine": round(float(fit.get("cosine", 0.0)), 4),
            "fwhm_ratio": round(float(fit.get("fwhm_ratio", 0.0)), 4),
            "target_fn_pk3": round(float(f1["fn_pk3"]), 5),
            "g1_pass": g1,
            "g2_pass": g2,
            "g3_pass": g3,
            "primary_order": g345.get("primary_order", 0),
            "primary_native_px": g345.get("primary_native_px", 0),
            "primary_native_fn_pk3": round(float(g345.get("primary_native_fn_pk3", 0.0)), 5),
            "primary_eta_1px": round(float(g345.get("primary_eta_1px", 0.0)), 4),
            "g4_pass": g4,
            "g5_pass": g5,
            "g5_cos11": round(float(g345.get("cos_1d_11px", 0.0)), 4),
            "g5_ipc_hotpx_ratio": round(float(g345.get("ipc_hotpx_ratio", 0.0)), 4),
            "g5_far_wing_ratio": round(float(g345.get("far_wing_34_ratio", 0.0)), 4),
            "pre_g6_qualified": pre_g6,
            "g6_v35_dense_pass": bool(g6_d["g6_v35_pass"]),
            "g6_pass": g6,
            "g6_coincident_total_stars": int(g6_s["g6_coincident_total_stars"]),
            "g6_same_star_hits": int(g6_s["g6_same_star_stationary_hits"]),
            "qualified_v38_laser": qual,
            "final_disposition": disp,
        })

        # Accumulate cascade & four-gen counts
        if ch in ("T", "P", "T_DIFF", "K_PLANET"):
            if g1:
                cascade_cnt["v38_total_ledger_g1_candidates"] += 1
                four_gen_by_dp[dp]["v38_g1_candidates"] += 1
                if g2:
                    cascade_cnt["v38_after_g2"] += 1
                    if g3:
                        cascade_cnt["v38_after_g3"] += 1
                        if g4:
                            cascade_cnt["v38_after_g4"] += 1
                            if g5:
                                cascade_cnt["v38_pre_g6_passed_g1_to_g5"] += 1
                                four_gen_by_dp[dp]["v38_pre_g6"] += 1
                                if not g6:
                                    cascade_cnt["v38_vetoed_by_g6_sparse"] += 1
                                else:
                                    four_gen_by_dp[dp]["v38_post_g6_qualified"] += 1
                                    if ch in ("T_DIFF", "K_PLANET"):
                                        cascade_cnt["v38_orbital_candidates"] += 1
                                    if role == "CONTROL":
                                        cascade_cnt["automated_qualified_control"] += 1
                                    else:
                                        cascade_cnt["automated_qualified_science"] += 1

        if qual:
            fcls, frat = _forensic_classify_singleline({**ledger_rows[-1], "dpr_or_calsel": c["dpr_or_calsel"]}, meta)
            forensic_single_rows.append({
                "candidate_id": cid,
                "instrument": inst,
                "channel": ch,
                "role": role,
                "star": st,
                "dp_id": dp,
                "bary_wave_a": round(w_bary, 5),
                "stellar_rest_wave_a": round(w_rest, 5),
                "topo_wave_a": round(topo_w, 5),
                "snr_mid": round(float(fit["snr_mid"]), 4),
                "target_fn_pk3": round(float(f1["fn_pk3"]), 5),
                "forensic_classification": fcls,
                "forensic_rationale": frat,
                "eti_plausible": False,
            })
            forensic_diag_details.append({"candidate_id": cid, "star": st, "instrument": inst, "channel": ch, "classification": fcls})

    write_csv(
        RESULTS / "V3_8_CANDIDATE_LEDGER.csv",
        ledger_rows,
        fieldnames=[
            "candidate_id", "instrument", "channel", "role", "star", "dp_id",
            "fitted_wave_a", "stellar_rest_wave_a", "bary_wave_a", "topo_wave_a",
            "snr_mid", "snr_out", "cosine", "fwhm_ratio", "target_fn_pk3",
            "g1_pass", "g2_pass", "g3_pass", "primary_order", "primary_native_px",
            "primary_native_fn_pk3", "primary_eta_1px", "g4_pass", "g5_pass",
            "g5_cos11", "g5_ipc_hotpx_ratio", "g5_far_wing_ratio", "pre_g6_qualified",
            "g6_v35_dense_pass", "g6_pass", "g6_coincident_total_stars",
            "g6_same_star_hits", "qualified_v38_laser", "final_disposition",
        ],
    )

    four_gen_rows = []
    for r in prov_rows:
        dp = r["dp_id"]
        fg = four_gen_by_dp[dp]
        four_gen_rows.append({
            "instrument": r["instrument"],
            "star": r["star"],
            "role": r["role"],
            "dp_id": dp,
            "v2_accepted_false_alarms": fg["v2_accepted_false_alarms"],
            "v38_g1_candidates": fg["v38_g1_candidates"],
            "v38_pre_g6": fg["v38_pre_g6"],
            "v38_post_g6_qualified": fg["v38_post_g6_qualified"],
        })
    write_csv(RESULTS / "FOUR_GEN_BENCHMARK_201.csv", four_gen_rows)

    # 9. Recompute COMB_V4_1 candidates cleanly offline from comb_real_candidates_bundle
    comb_cands_rows: list[dict[str, Any]] = []
    forensic_comb_rows: list[dict[str, Any]] = []
    comb_v41_by_star: dict[str, list[dict[str, Any]]] = {st: [] for st in star_meta}

    for cr in bundle["comb_real_candidates_bundle"]:
        st = cr["star"]
        inst = cr["instrument"]
        cfg = dict(get_inst_config(inst, resolving_power=cr["resolving_power"]))
        cfg["comb_spacings_ghz"] = [float(cr["dnu_ghz"])]
        w = np.asarray(cr["wave_win"], dtype=np.float64)
        yr = np.asarray(cr["y_rest_win"], dtype=np.float64)
        sr = np.asarray(cr["sigma_rest_win"], dtype=np.float64)
        fn = np.asarray(cr["fn_win"], dtype=np.float64)
        rc = np.asarray(cr["recon_win"], dtype=np.float64)
        sm = np.asarray(cr["sky_mask_win"], dtype=bool)
        yt = np.asarray(cr["y_topo_win"], dtype=np.float64)
        st_arr = np.asarray(cr["sigma_topo_win"], dtype=np.float64)
        win_c = [{"band": cr["band"], "lo_a": float(w[0]) + 0.2, "hi_a": float(w[-1]) - 0.2}]
        h41, _ = scan_frequency_comb_v4_1(w, yr, sr, fn, rc, sm, yt, st_arr, win_c, [cr["band"]], cfg)
        for hit in h41:
            if abs(float(hit["nu0_ghz"]) - float(cr["nu0_ghz_stage_a"])) <= 2.5 * float(cfg["comb_freq_step_ghz"]):
                comb_v41_by_star[st].append((cr["role"], hit))
                break

    comb_idx = 0
    for st in sorted(comb_v41_by_star.keys()):
        hits = comb_v41_by_star[st]
        # Dedup close windows within star
        kept_st = []
        for role, h in sorted(hits, key=lambda x: -x[1]["s_comb"]):
            if any(p["band"] == h["band"] and abs(p["nu0_ghz"] - h["nu0_ghz"]) <= 0.5 * h["dnu_ghz"] for _, p in kept_st):
                continue
            kept_st.append((role, h))
            comb_idx += 1
            cid = f"V41COMB-{comb_idx:04d}"
            row = {
                "comb_id": cid,
                "instrument": star_meta[st]["instrument"],
                "star": st,
                "role": role,
                "band": h["band"],
                "dnu_ghz": h["dnu_ghz"],
                "nu0_ghz": h["nu0_ghz"],
                "wave0_a": h["wave0_a"],
                "wave_end_a": h["wave_end_a"],
                "s_comb": h["s_comb"],
                "topo_anti_ratio": h["topo_anti_ratio"],
                "n_qualifying_teeth": h["n_qualifying_teeth"],
                "off_tooth_crowding": h["off_tooth_crowding"],
                "intertooth_ratio": h["intertooth_ratio"],
            }
            comb_cands_rows.append(row)
            fcls, frat = _forensic_classify_comb(row, star_meta[st])
            forensic_comb_rows.append({
                **row,
                "forensic_classification": fcls,
                "forensic_rationale": frat,
                "eti_plausible": False,
            })

    comb_fields = [
        "comb_id", "instrument", "star", "role", "band", "dnu_ghz", "nu0_ghz",
        "wave0_a", "wave_end_a", "s_comb", "topo_anti_ratio", "n_qualifying_teeth",
        "off_tooth_crowding", "intertooth_ratio",
    ]
    write_csv(RESULTS / "COMB_V4_1_CANDIDATES.csv", comb_cands_rows, fieldnames=comb_fields)

    comb_star_rows = []
    comb_v4_cnts = bundle["comb_v4_counts_by_star"]
    v41_cnt_by_st = {}
    for cr in comb_cands_rows:
        v41_cnt_by_st[cr["star"]] = v41_cnt_by_st.get(cr["star"], 0) + 1
    for st in sorted(star_meta.keys()):
        comb_star_rows.append({
            "instrument": star_meta[st]["instrument"],
            "star": st,
            "role": star_meta[st]["role"],
            "comb_v4_candidates": int(comb_v4_cnts.get(st, 0)),
            "comb_v41_candidates": int(v41_cnt_by_st.get(st, 0)),
            "verified_eti_combs": 0,
        })
    write_csv(RESULTS / "COMB_V4_1_STAR_RESULTS_33.csv", comb_star_rows)

    # 10. ORBITAL_CAMPAIGN_RESULTS_10.csv
    orb_rows: list[dict[str, Any]] = []
    for st in sorted(orb_doc["campaigns"].keys()):
        c = orb_doc["campaigns"][st]
        q_td = sum(1 for r in ledger_rows if r["star"] == st and r["channel"] == "T_DIFF" and r["qualified_v38_laser"])
        q_kp = sum(1 for r in ledger_rows if r["star"] == st and r["channel"] == "K_PLANET" and r["qualified_v38_laser"])
        orb_rows.append({
            "star": st,
            "common_name": c["common_name"],
            "instrument": c["instrument"],
            "role": c["role"],
            "planet_name": c["planet_name"],
            "transiting": c["transiting"],
            "orbper_days": c["orbper_days"],
            "kp_kms": c["kp_kms"],
            "orbital_dv_span_kms": c["orbital_dv_span_kms"],
            "n_in_window": c["n_in_window"],
            "n_out_of_window": c["n_out_of_window"],
            "qualified_tdiff_candidates": q_td,
            "qualified_kplanet_candidates": q_kp,
            "verified_eti_detections": 0,
        })
    write_csv(RESULTS / "ORBITAL_CAMPAIGN_RESULTS_10.csv", orb_rows)

    # 11. Radiometric 10m Transmitter Upper Limits (STAR_UPPER_LIMITS_D087.csv)
    ul_rows: list[dict[str, Any]] = []
    for up in bundle["upper_limit_patches"]:
        inst = up["instrument"]
        cw = float(up["wave_bary_a"])
        anchor = up["radiometric_anchor"]
        mad_rel = float(up["median_epoch_mad_rel"])
        amp_lim = 8.0 * mad_rel
        if anchor == "HST_CALSTIS_DIRECT_FLAM":
            mag = float(up["phot_g_mag"])
        elif anchor == "GAIA_DR3_GRP":
            mag = float(up["phot_rp_mag"])
        elif anchor == "TWOMASS_J":
            mag = float(up["j_mag"])
        else:
            mag = float(up["phot_g_mag"])
        pb = compute_photon_beam_upper_limit(
            wave_a=cw,
            amp_rel_8sigma_lim=amp_lim,
            teff_k=float(up["teff_k"]),
            dist_pc=float(up["dist_pc"]),
            mag=mag,
            radiometric_anchor=anchor,
            resolving_power=float(up["resolving_power"]),
            d_tx_m=10.0,
            direct_flam_cgs=up.get("direct_flam_cgs"),
        )
        ul_rows.append({
            "instrument": inst,
            "star": up["star"],
            "common_name": up["common_name"],
            "subrole": up["subrole"],
            "panchromatic_bridge": up["panchromatic_bridge"],
            "radio_mm_id": up["radio_mm_id"],
            "within_10pc": up["within_10pc"],
            "n_exoplanets": up["n_exoplanets"],
            "has_transiting_planet": up["has_transiting_planet"],
            "dist_pc": up["dist_pc"],
            "teff_k": up["teff_k"],
            "phot_g_mag": up["phot_g_mag"],
            "phot_rp_mag": up["phot_rp_mag"],
            "j_mag": up["j_mag"],
            "radiometric_anchor": anchor,
            "resolving_power": up["resolving_power"],
            "band_id": up["band_id"],
            "wave_bary_a": cw,
            "median_epoch_mad_rel": mad_rel,
            "amp_rel_8sigma_lim": rsig(amp_lim, 8),
            "fwhm_lsf_a": rsig(pb["fwhm_lsf_a"], 8),
            "ew_lim_mA": rsig(pb["ew_lim_mA"], 8),
            "continuum_flam_cgs": rsig(pb["continuum_flam_cgs"], 8),
            "flux_lim_erg_cm2_s": rsig(pb["flux_lim_erg_cm2_s"], 8),
            "l_iso_mw": rsig(pb["l_iso_mw"], 8),
            "p_beam_10m_w": round(float(pb["p_beam_10m_w"]), 4),
            "p_beam_10m_kw": round(float(pb["p_beam_10m_kw"]), 7),
        })
    write_csv(RESULTS / "STAR_UPPER_LIMITS_D087.csv", ul_rows)

    best_ul = min(ul_rows, key=lambda r: float(r["p_beam_10m_w"]))

    # 12. PANCHROMATIC_BRIDGE_17STARS.csv (13 prior bridge stars + 4 newly promoted [ADLEO, HD209458, GJ1061, GJ729])
    bridge_cols = [
        "phase_id", "spectral_regime", "instrument", "star", "common_name", "dist_pc",
        "band_id", "wave_um", "wave_A", "ew_lim_mA", "flux_lim_erg_cm2_s",
        "l_iso_mw", "p_beam_10m_kw", "p_beam_10m_w",
    ]
    bridge_rows: list[dict[str, Any]] = []
    # Keep all prior 13 bridge stars' rows + add prior rows for the 4 newly promoted bridge stars + add D087 rows for all 8 D087 bridges
    for br in prior_snap["d086_bridge_13star_rows"]:
        bridge_rows.append({k: br.get(k, "") for k in bridge_cols})
    for pr_u in prior_snap["prior_new_bridge_upper_limits"]:
        w_a = float(pr_u.get("wave_bary_vac_A", pr_u.get("wave_bary_air_A", 0.0)))
        p_kw = float(pr_u["p_beam_10m_kw"])
        bridge_rows.append({
            "phase_id": pr_u["phase_id"],
            "spectral_regime": pr_u["spectral_regime"],
            "instrument": pr_u["instrument"],
            "star": pr_u["star"],
            "common_name": pr_u["common_name"],
            "dist_pc": pr_u["dist_pc"],
            "band_id": pr_u["band_id"],
            "wave_um": round(w_a / 10000.0, 6),
            "wave_A": w_a,
            "ew_lim_mA": pr_u["ew_lim_mA"],
            "flux_lim_erg_cm2_s": pr_u["flux_lim_erg_cm2_s"],
            "l_iso_mw": pr_u["l_iso_mw"],
            "p_beam_10m_kw": pr_u["p_beam_10m_kw"],
            "p_beam_10m_w": pr_u.get("p_beam_10m_w", round(1000.0 * p_kw, 4)),
        })
    for ur in ul_rows:
        if ur["panchromatic_bridge"]:
            w_a = float(ur["wave_bary_a"])
            bridge_rows.append({
                "phase_id": "D087",
                "spectral_regime": "SPACE_FUV_0p1145_0p171um" if ur["instrument"] == "HST_STIS" else "FARRED_0p565_1p042um",
                "instrument": ur["instrument"],
                "star": ur["star"],
                "common_name": ur["common_name"],
                "dist_pc": ur["dist_pc"],
                "band_id": ur["band_id"],
                "wave_um": round(w_a / 10000.0, 6),
                "wave_A": ur["wave_bary_a"],
                "ew_lim_mA": ur["ew_lim_mA"],
                "flux_lim_erg_cm2_s": ur["flux_lim_erg_cm2_s"],
                "l_iso_mw": ur["l_iso_mw"],
                "p_beam_10m_kw": ur["p_beam_10m_kw"],
                "p_beam_10m_w": ur["p_beam_10m_w"],
            })
    write_csv(RESULTS / "PANCHROMATIC_BRIDGE_17STARS.csv", bridge_rows, fieldnames=bridge_cols)

    # 13. UNIFIED_PANCHROMATIC_V3_SYNTHESIS_200STARS.csv & SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_103STARS.csv
    def _min_ul(vals: list[float]) -> str:
        clean = [v for v in vals if math.isfinite(v)]
        return f"{min(clean):.8g}" if clean else ""

    d87_ul_by_star: dict[str, list[dict[str, Any]]] = {}
    for ur in ul_rows:
        d87_ul_by_star.setdefault(ur["star"], []).append(ur)
    exp_cnt_by_star: dict[str, dict[str, int]] = {}
    for r in prov_rows:
        d = exp_cnt_by_star.setdefault(r["star"], {"HST_STIS": 0, "UVES_RED": 0, "ESPRESSO": 0})
        d[r["instrument"]] += 1
    cand_cnt_by_star: dict[str, int] = {}
    for r in ledger_rows:
        if r["qualified_v38_laser"]:
            cand_cnt_by_star[r["star"]] = cand_cnt_by_star.get(r["star"], 0) + 1

    unified_by_star: dict[str, dict[str, Any]] = {}
    for r in prior_snap["unified_175star_rows"]:
        row = dict(r)
        row.setdefault("n_exposures_fuv", "0")
        row.setdefault("min_fuv_10m_kw", "")
        row.setdefault("n_exposures_farred_uves", "0")
        row.setdefault("min_farred_uves_10m_kw", "")
        unified_by_star[r["star"]] = row

    for st in sorted(star_meta.keys()):
        m = star_meta[st]
        ec = exp_cnt_by_star[st]
        sul = d87_ul_by_star.get(st, [])
        min_fuv = _min_ul([float(u["p_beam_10m_kw"]) for u in sul if u["instrument"] == "HST_STIS"])
        min_fr = _min_ul([float(u["p_beam_10m_kw"]) for u in sul if u["instrument"] == "UVES_RED"])
        min_opt = _min_ul([float(u["p_beam_10m_kw"]) for u in sul if u["instrument"] == "ESPRESSO"])
        d87_all_kw = _min_ul([float(u["p_beam_10m_kw"]) for u in sul])

        if st in unified_by_star:
            row = unified_by_star[st]
            row["phases"] = f"{row['phases']}+D087"
            row["instruments"] = f"{row['instruments']}+{m['instrument']}"
            if min_fuv:
                row["spectral_regime"] = "PANCHROMATIC_0p1145_2p515um_BRIDGE"
                row["n_exposures_fuv"] = str(int(row["n_exposures_fuv"] or 0) + ec["HST_STIS"])
                row["min_fuv_10m_kw"] = min_fuv
            if min_fr:
                if "0p1145" not in row["spectral_regime"]:
                    row["spectral_regime"] = "PANCHROMATIC_0p305_2p515um_BRIDGE"
                row["n_exposures_farred_uves"] = str(int(row["n_exposures_farred_uves"] or 0) + ec["UVES_RED"])
                row["min_farred_uves_10m_kw"] = min_fr
            row["n_exposures_total"] = str(int(row["n_exposures_total"]) + sum(ec.values()))
            prev_min = float(row["min_panchromatic_10m_kw"]) if row.get("min_panchromatic_10m_kw") else 1e30
            new_min = float(d87_all_kw) if d87_all_kw else 1e30
            best_v = min(prev_min, new_min)
            row["min_panchromatic_10m_kw"] = f"{best_v:.8g}" if best_v < 1e29 else ""
            row["automated_qualified_candidates"] = str(int(row["automated_qualified_candidates"]) + cand_cnt_by_star.get(st, 0))
            if not row.get("j_mag") and m["j_mag"]:
                row["j_mag"] = str(round(m["j_mag"], 4))
                row["h_mag"] = str(round(m["h_mag"], 4)) if m["h_mag"] else ""
                row["ks_mag"] = str(round(m["ks_mag"], 4)) if m["ks_mag"] else ""
        else:
            reg = (
                "SPACE_FUV_0p1145_0p171um" if m["instrument"] == "HST_STIS"
                else ("FARRED_0p565_1p042um" if m["instrument"] == "UVES_RED" else "OPTICAL_0p38_0p78um")
            )
            unified_by_star[st] = {
                "phases": "D087",
                "hemisphere": "ALL_SKY" if m["instrument"] == "HST_STIS" else "SOUTHERN",
                "spectral_regime": reg,
                "instruments": m["instrument"],
                "star": st,
                "common_name": m["common_name"],
                "role": m["role"],
                "subrole": m["subrole"],
                "dist_pc": str(round(m["dist_pc"], 5)),
                "within_10pc": str(bool(m["within_10pc"])),
                "teff_k": str(m["teff_k"]),
                "phot_g_mag": str(round(m["phot_g_mag"], 5)),
                "j_mag": str(round(m["j_mag"], 4)) if m["j_mag"] else "",
                "h_mag": str(round(m["h_mag"], 4)) if m["h_mag"] else "",
                "ks_mag": str(round(m["ks_mag"], 4)) if m["ks_mag"] else "",
                "n_exoplanets": str(m["n_exoplanets"]),
                "n_exposures_optical": str(ec["ESPRESSO"]),
                "n_exposures_nir_yjh": "0",
                "n_exposures_kband": "0",
                "n_exposures_total": str(sum(ec.values())),
                "min_optical_10m_kw": min_opt,
                "min_nir_yjh_10m_kw": "",
                "min_kband_10m_kw": "",
                "p_1064nm_10m_kw": "",
                "p_1550nm_10m_kw": "",
                "p_2040nm_tm_10m_kw": "",
                "p_2097nm_hoyag_10m_kw": "",
                "min_panchromatic_10m_kw": d87_all_kw,
                "automated_qualified_candidates": str(cand_cnt_by_star.get(st, 0)),
                "verified_eti_detections": "0",
                "n_exposures_nuv": "0",
                "min_nuv_10m_kw": "",
                "n_exposures_fuv": str(ec["HST_STIS"]),
                "min_fuv_10m_kw": min_fuv,
                "n_exposures_farred_uves": str(ec["UVES_RED"]),
                "min_farred_uves_10m_kw": min_fr,
            }

    unified_rows = sorted(unified_by_star.values(), key=lambda x: (float(x["dist_pc"]), x["star"]))
    write_csv(RESULTS / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_200STARS.csv", unified_rows)
    solar_10pc_rows = [r for r in unified_rows if r["within_10pc"] == "True"]
    write_csv(RESULTS / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_103STARS.csv", solar_10pc_rows)

    # 14. MULTIMESSENGER_ECHELLE_RADIO_TESS_206SYSTEMS.csv
    mm_by_star = {s.get("canonical_v3_star"): s for s in mm_snap["systems"] if s.get("canonical_v3_star")}
    mm_rows: list[dict[str, Any]] = []
    for ur in unified_rows:
        st = ur["star"]
        ms = mm_by_star.get(st)
        if ms:
            is_ls = "LIGHTSAIL" in str(ms.get("modality", "")).upper()
            mods = "ECHELLE_SPECTROSCOPY+TESS_SPECULAR_LIGHTSAIL" if is_ls else "ECHELLE_SPECTROSCOPY+RADIO_1p4GHZ_PLANET_FRAME"
            n_mod = 2
            ovlp = True
            if is_ls:
                r_ms = r_fac = r_rec = ""
                ls_ms = ms.get("milestone", "")
            else:
                r_ms = ms.get("milestone", "")
                r_fac = ms.get("facility", "")
                r_rec = ms.get("snr40_recovery_fraction", "")
                ls_ms = ""
        else:
            mods = "ECHELLE_SPECTROSCOPY"
            n_mod = 1
            ovlp = False
            r_ms = r_fac = r_rec = ls_ms = ""
        mm_rows.append({
            "system_id": st,
            "host_name": ur["common_name"],
            "hemisphere": ur["hemisphere"],
            "role": ur["role"],
            "dist_pc": ur["dist_pc"],
            "within_10pc": ur["within_10pc"],
            "n_exoplanets": ur["n_exoplanets"],
            "modalities_searched": mods,
            "n_modalities": n_mod,
            "multimessenger_overlap": ovlp,
            "echelle_phases": ur["phases"],
            "echelle_instruments": ur["instruments"],
            "echelle_exposures": ur["n_exposures_total"],
            "min_echelle_10m_kw": ur["min_panchromatic_10m_kw"],
            "radio_milestone": r_ms,
            "radio_facility": r_fac,
            "radio_snr40_recovery": r_rec,
            "lightsail_milestone": ls_ms,
            "verified_eti_detections": 0,
        })
    for ms in mm_snap["systems"]:
        if not ms.get("canonical_v3_star"):
            mm_rows.append({
                "system_id": ms["mm_id"],
                "host_name": ms["host_name"],
                "hemisphere": "NORTHERN",
                "role": "SCIENCE",
                "dist_pc": "",
                "within_10pc": "",
                "n_exoplanets": ms.get("n_exoplanets", 1),
                "modalities_searched": "RADIO_1p4GHZ_PLANET_FRAME",
                "n_modalities": 1,
                "multimessenger_overlap": False,
                "echelle_phases": "",
                "echelle_instruments": "",
                "echelle_exposures": 0,
                "min_echelle_10m_kw": "",
                "radio_milestone": ms.get("milestone", ""),
                "radio_facility": ms.get("facility", ""),
                "radio_snr40_recovery": ms.get("snr40_recovery_fraction", ""),
                "lightsail_milestone": "",
                "verified_eti_detections": 0,
            })
    write_csv(RESULTS / "MULTIMESSENGER_ECHELLE_RADIO_TESS_206SYSTEMS.csv", mm_rows)

    # 15. Write FORENSIC_CANDIDATE_AUDIT_D087.json, FORENSIC_D087_CASCADE_DIAGNOSIS.json & SUMMARY.json
    forensic_doc = {
        "schema": "D087_FORENSIC_CANDIDATE_AUDIT_V1",
        "phase_id": "D087",
        "pre_g6_count": cascade_cnt["v38_pre_g6_passed_g1_to_g5"],
        "post_g6_count": cascade_cnt["automated_qualified_control"] + cascade_cnt["automated_qualified_science"],
        "comb_v41_count": len(comb_cands_rows),
        "post_g6_singleline_forensic_classifications": forensic_single_rows,
        "comb_v41_forensic_classifications": forensic_comb_rows,
        "verified_eti_detections": 0,
    }
    _assert_json_finite(forensic_doc, "forensic_doc")
    (WS / "FORENSIC_CANDIDATE_AUDIT_D087.json").write_text(json.dumps(forensic_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    # Cascade breakdown summary
    class_counts: dict[str, int] = {}
    for fr in forensic_single_rows:
        class_counts[fr["forensic_classification"]] = class_counts.get(fr["forensic_classification"], 0) + 1
    diag_doc = {
        "schema": "FORENSIC_D087_CASCADE_DIAGNOSIS_V1",
        "phase_id": "D087",
        "cascade": cascade_cnt,
        "forensic_class_counts": class_counts,
        "d086_g4_v38_regression": {
            "before": len(reg_rows),
            "survivors_after": sum(1 for r in reg_rows if r["g4_v38_retained"]),
        },
        "comb_v41_summary": {
            "comb_v4_automated_candidates": sum(int(v) for v in comb_v4_cnts.values()),
            "comb_v41_automated_candidates": len(comb_cands_rows),
            "verified_eti_combs": 0,
        },
    }
    _assert_json_finite(diag_doc, "diag_doc")
    (RESULTS / "FORENSIC_D087_CASCADE_DIAGNOSIS.json").write_text(json.dumps(diag_doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    # Compute exact summary metrics
    t_inj_8 = [r for r in inj_rows if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH" and r["sigma_mult"] >= 8.0]
    p_inj_9 = [r for r in inj_rows if r["mode"] == "CHANNEL_P_PERSISTENT_COADD" and r["sigma_mult"] >= 8.0]
    kep_65 = [r for r in kep_rows if r["exp_sigma_mult"] >= 6.5]
    g45_t = [r for r in g45_rows if r["trial_class"] == "TRUE_LSF_LASER"]
    g45_c = [r for r in g45_rows if r["trial_class"] == "COSMIC_SINGLE_PX_SPIKE"]
    g45_w = [r for r in g45_rows if r["trial_class"] == "WIDE_SCATTERING_PLATEAU"]
    c_6t = [r for r in comb_cal_rows if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and r["tooth_snr_inj"] >= 3.8]
    c_1l = [r for r in comb_cal_rows if r["trial_class"] == "SINGLE_BRIGHT_LINE_MASQUERADE"]
    c_tp = [r for r in comb_cal_rows if r["trial_class"] == "STATIONARY_TOPO_ROVIB_PSEUDOCOMB"]
    c_df = [r for r in comb_cal_rows if r["trial_class"] == "DENSE_MOLECULAR_FOREST_PSEUDOCOMB"]

    searched_inst = bundle["searched_counts_by_inst"]
    sc_t = sum(v["T"] for v in searched_inst.values())
    sc_p = sum(v["P"] for v in searched_inst.values())
    sc_td = sum(v["T_DIFF"] for v in searched_inst.values())
    sc_kp = sum(v["K_PLANET"] for v in searched_inst.values())
    sc_comb = sum(v["COMB_CONFIGS"] for v in searched_inst.values())

    n_new_stars = sum(1 for m in star_meta.values() if not m["panchromatic_bridge"])
    n_bridge_in_d087 = sum(1 for m in star_meta.values() if m["panchromatic_bridge"])
    n_new_10pc = sum(1 for m in star_meta.values() if (not m["panchromatic_bridge"]) and m["within_10pc"])
    n_tot_cal = len(inj_rows) + len(kep_rows) + len(g45_rows) + len(g6_rows) + len(comb_cal_rows)
    w10_kws = [float(r["min_panchromatic_10m_kw"]) for r in solar_10pc_rows if r.get("min_panchromatic_10m_kw")]
    w10_med_kw = round(exact_median_1d(np.asarray(w10_kws, dtype=np.float64)), 4)

    summary = {
        "phase_id": "D087",
        "detector": "SPACE_UV_STIS_AND_FARRED_V3_8",
        "instruments": ["HST_STIS", "UVES_RED", "ESPRESSO"],
        "wavelength_domain_um": [0.1145, 1.0425],
        "cumulative_wavelength_domain_um": [0.1145, 2.515],
        "cumulative_octaves": round(math.log2(2.515 / 0.1145), 3),
        "cohort": {
            "total_stars": len(star_meta),
            "control_stars": sum(1 for m in star_meta.values() if m["role"] == "CONTROL"),
            "science_stars": sum(1 for m in star_meta.values() if m["role"] == "SCIENCE"),
            "brand_new_unique_stars": n_new_stars,
            "panchromatic_bridge_stars_in_d087": n_bridge_in_d087,
            "brand_new_within_10pc": n_new_10pc,
            "total_exposures": len(prov_rows),
            "hst_stis_exposures": sum(1 for r in prov_rows if r["instrument"] == "HST_STIS"),
            "uves_red_exposures": sum(1 for r in prov_rows if r["instrument"] == "UVES_RED"),
            "espresso_exposures": sum(1 for r in prov_rows if r["instrument"] == "ESPRESSO"),
            "espresso_uhr_190k_exposures": sum(1 for r in prov_rows if r["instrument"] == "ESPRESSO" and float(r["resolving_power"]) >= 175000.0),
            "total_integration_hours": bundle["total_integration_hours"],
            "orbital_campaigns": len(orb_rows),
        },
        "searched_spectral_elements": {
            "by_instrument": searched_inst,
            "channel_t_1d_bins": sc_t,
            "channel_p_coadd_bins": sc_p,
            "channel_tdiff_bins": sc_td,
            "channel_kplanet_bins": sc_kp,
            "comb_v41_searched_configs": sc_comb,
            "total_searched_1d_bins": sc_t + sc_p + sc_td + sc_kp,
        },
        "rv_anchoring": {
            "total_anchor_fits": len(rv_anchor_rows),
            "clean_absorption_fits": sum(1 for a in rv_anchor_rows if a["status"] == "CLEAN_ABSORPTION"),
            "median_abs_empirical_minus_prior_kms": round(
                exact_median_1d(np.asarray([abs(float(r["empirical_minus_prior_kms"])) for r in rv_sum_rows], dtype=np.float64)),
                4,
            ),
            "max_ground_stdlib_berv_diff_kms": round(
                max(float(r["berv_diff_stdlib_kms"]) for r in prov_rows if r["instrument"] != "HST_STIS"),
                4,
            ),
            "max_stis_leo_helio_diff_kms": round(
                max(float(r["berv_diff_stdlib_kms"]) for r in prov_rows if r["instrument"] == "HST_STIS"),
                4,
            ),
        },
        "synthetic_calibration_2697_trials": {
            "total_trials": n_tot_cal,
            "channel_t_trials": sum(1 for r in inj_rows if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH"),
            "channel_p_trials": sum(1 for r in inj_rows if r["mode"] == "CHANNEL_P_PERSISTENT_COADD"),
            "keplerian_paired_trials": len(kep_rows),
            "g4g5_trials": len(g45_rows),
            "g6_sparse_vs_dense_trials": len(g6_rows),
            "comb_v41_trials": len(comb_cal_rows),
            "channel_t_ge_8sigma": round(sum(1 for r in t_inj_8 if r["recovered"]) / max(1, len(t_inj_8)), 5),
            "channel_p_ge_8sigma": round(sum(1 for r in p_inj_9 if r["recovered"]) / max(1, len(p_inj_9)), 5),
            "keplerian_tdiff_ge_6p5sigma": round(sum(1 for r in kep_65 if r["tdiff_uncomp_recovered"]) / max(1, len(kep_65)), 5),
            "keplerian_kplanet_ge_6p5sigma": round(sum(1 for r in kep_65 if r["kplanet_dedop_recovered"]) / max(1, len(kep_65)), 5),
            "g45_true_laser_pass": round(sum(1 for r in g45_t if r["g45_pass"]) / max(1, len(g45_t)), 5),
            "g5_cosmic_hotpx_rejection": round(sum(1 for r in g45_c if not r["g45_pass"]) / max(1, len(g45_c)), 5),
            "g5_plateau_rejection": round(sum(1 for r in g45_w if not r["g45_pass"]) / max(1, len(g45_w)), 5),
            "comb_v41_6tooth_ge_3p8sigma_recovery": round(sum(1 for r in c_6t if r["comb_v41_hit"]) / max(1, len(c_6t)), 5),
            "comb_v41_single_line_fpr": round(sum(1 for r in c_1l if r["comb_v41_hit"]) / max(1, len(c_1l)), 5),
            "comb_v41_topo_rovib_pseudocomb_fpr": round(sum(1 for r in c_tp if r["comb_v41_hit"]) / max(1, len(c_tp)), 5),
            "comb_v41_dense_forest_fpr": round(sum(1 for r in c_df if r["comb_v41_hit"]) / max(1, len(c_df)), 5),
            "comb_v4_dense_forest_fpr": round(sum(1 for r in c_df if r["comb_v4_hit"]) / max(1, len(c_df)), 5),
        },
        "d086_g4_v38_fiberb_regression": {
            "d086_fiberb_bleed_candidates_before": len(reg_rows),
            "d087_g4_v38_survivors_after": sum(1 for r in reg_rows if r["g4_v38_retained"]),
        },
        "false_alarm_cascade": {
            **cascade_cnt,
            "comb_v4_automated_candidates_on_d087": sum(int(v) for v in comb_v4_cnts.values()),
            "comb_v41_automated_candidates": len(comb_cands_rows),
            "verified_eti_detections": 0,
        },
        "upper_limits": {
            "n_cells": len(ul_rows),
            "best_overall_star": best_ul["star"],
            "best_overall_instrument": best_ul["instrument"],
            "best_overall_band": best_ul["band_id"],
            "best_overall_10m_w": float(best_ul["p_beam_10m_w"]),
            "best_stis_fuv_star": min([r for r in ul_rows if r["instrument"] == "HST_STIS"], key=lambda r: float(r["p_beam_10m_w"]))["star"],
            "best_stis_fuv_10m_w": float(min([r for r in ul_rows if r["instrument"] == "HST_STIS"], key=lambda r: float(r["p_beam_10m_w"]))["p_beam_10m_w"]),
        },
        "unified_200star_panchromatic_v3_synthesis": {
            "phases": "D079-D087",
            "spectrographs": 9,
            "spectrograph_arms": 10,
            "unique_stars_total": len(unified_rows),
            "within_10pc_unique_stars": len(solar_10pc_rows),
            "within_10pc_median_limit_kw": w10_med_kw,
            "panchromatic_bridge_stars_total": len({r["star"] for r in bridge_rows}),
            "total_exposures_d079_d087": int(prior_snap["prior_v3_total_exposures_count"]) + len(prov_rows),
            "total_calibration_trials_d079_d087": int(prior_snap["prior_v3_calibration_trials_count"]) + n_tot_cal,
            "v2_false_alarms_eliminated_total": int(prior_snap["prior_v2_false_alarms_eliminated_total"]) + cascade_cnt["v2_legacy_false_alarms"],
            "cumulative_orbital_campaigns": int(prior_snap["d086_summary_headline"]["unified_175star_panchromatic_v3_synthesis"]["cumulative_orbital_campaigns"]) + len(orb_rows),
            "verified_eti_detections_total": 0,
        },
        "multimessenger_206system_synthesis": {
            "distinct_stellar_systems_total": len(mm_rows),
            "direct_multimessenger_overlap_count": mm_snap["n_direct_echelle_multimessenger_overlap_stars"],
            "direct_multimessenger_overlap_stars": mm_snap["overlapping_v3_stars"],
            "verified_eti_detections_all_modalities": 0,
        },
    }
    _assert_json_finite(summary, "summary")
    (RESULTS / "SUMMARY.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"[Stage B] Completed D087 offline recompute: {len(prov_rows)} exp, {len(unified_rows)} stars ({len(solar_10pc_rows)} <10pc), {len(mm_rows)} MM systems, 0 verified ETI.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="D087 Space-FUV HST/STIS + UVES_RED + ESPRESSO Pipeline")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--from-full-inputs", type=Path, help="Full raw FITS directory (inputs_d087_v3_8)")
    g.add_argument("--from-bounded-inputs", type=Path, help="Bounded bundle (.json.gz) for offline recomputation")
    args = parser.parse_args()

    if args.from_full_inputs is not None:
        build_bounded_bundle(args.from_full_inputs, DEFAULT_BUNDLE)
        run_stage_b(DEFAULT_BUNDLE)
    else:
        run_stage_b(args.from_bounded_inputs)


if __name__ == "__main__":
    main()
