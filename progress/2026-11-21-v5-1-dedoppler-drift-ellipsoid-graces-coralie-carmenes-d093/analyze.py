#!/usr/bin/env python3
"""
Phase D093 Stage A/B Pipeline:
`TECHNOSIGNATURE_V5_1_DEDOPPLER_DRIFT_MULTIEVENT_ELLIPSOID_GRACES_CORALIE_CARMENES`

Dual-mode bit-identical execution:
  --from-full-inputs     Verify all 30 FITS in `inputs_d093_v5_1/` against
                         FULL_D093_INPUT_MANIFEST.json, emit bounded bundle
                         `bounded_inputs/d093_bounded_bundle.json.gz` (< 25 MiB), and
                         immediately decode from that serialized bundle before analysis.
  --from-bounded-inputs  Execute strictly from `d093_bounded_bundle.json.gz` plus
                         read-only Companion Archives N (`D088`), P (`D090`), R (`D092`),
                         and prior-phase coordinates/epochs in `--archives-dir`.
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
INP_FULL_DEFAULT = ROOT / "inputs_d093_v5_1"
DEFAULT_BUNDLE = WS / "bounded_inputs" / "d093_bounded_bundle.json.gz"
DEFAULT_OUT = WS / "results"
ARCHIVES_DEFAULT = ROOT / "archives"
MAX_BUNDLE_MIB = 25.0

if str(WS) not in sys.path:
    sys.path.insert(0, str(WS))

from v5_1_detector import (  # noqa: E402
    C_ANGSTROM_GHZ,
    C_KMS,
    COMB_V4_1_WINDOWS_A,
    DETECTOR_NAME,
    FWHM_FACTOR,
    GROUND_AIRGLOW_AND_TELLURIC_A,
    MAD_NORM,
    NATURAL_NIRSPEC_CONFOUNDERS_UM,
    NIRSPEC_MOL_TEMPLATES_UM,
    STELLAR_OPT_NIR_EMISSION_A,
    _fit_miri_loglog_continuum,
    _sideband_noise_sigma,
    air_to_vac_a,
    analytical_observatory_berv_kms,
    bary_to_planet_rest_wave,
    build_and_scan_transit_channels,
    build_multi_epoch_rest_coadd_and_channel_p,
    check_channel_lsf_gate,
    compute_multievent_sync_v51,
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
    get_calibration_bands,
    get_inst_config,
    measure_exposure_stellar_rv,
    run_cohort_rpca_v50,
    scan_agnostic_multiscale_v50,
    scan_blind_drift_dedoppler_v51,
    scan_frequency_comb_v4,
    scan_frequency_comb_v4_1,
    scan_single_exposure_residual_lsf,
)

ARCHIVE_N_NAME = "SETI_D088_V3_9_NORTHERN_RADIO23_AND_ALLSKY_COMB_V4_1_RESULTS_2026-11-18.zip"
ARCHIVE_P_NAME = "SETI_D090_V4_1_JWST_SPACE_THERMAL_IR_RESULTS_2026-11-19.zip"
ARCHIVE_R_NAME = "SETI_D092_V5_0_RPCA_RARITY_ELLIPSOID_PPO_MIRI_CCF_RESULTS_2026-11-20.zip"
NIRSPEC_EDGE_TRIM_UM = 0.06


# ---------------------------------------------------------------------------
# Utilities & Compact Lossless / IEEE-754 Serialization Codecs
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
    """Encode uniform linear/log-linear grids cleanly, smooth echelle orders via deg-5 poly+i16, else f64."""
    w = np.asarray(w_angstrom, dtype=np.float64)
    n = int(len(w))
    if n >= 4 and np.all(np.isfinite(w)) and np.all(w > 0.0):
        diffs = np.diff(w)
        dw = float(exact_median_1d(diffs))
        if np.max(np.abs(diffs - dw)) < 5e-4:
            return {"u": 1, "w0": round(float(w[0]), 6), "dw": round(dw, 9), "n": n}
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


def _decode_wave(enc: dict[str, Any]) -> np.ndarray:
    u = int(enc["u"])
    n = int(enc["n"])
    if u == 1:
        return float(enc["w0"]) + float(enc["dw"]) * np.arange(n, dtype=np.float64)
    if u == 3:
        return float(enc["w0"]) * np.exp(float(enc["dl"]) * np.arange(n, dtype=np.float64))
    if u == 2:
        x = np.linspace(-1.0, 1.0, n)
        w_fit = np.polyval(np.asarray(enc["c"], dtype=np.float64), x)
        raw = np.frombuffer(base64.b64decode(enc["b64"]), dtype=np.uint8).reshape(2, n).T.copy()
        r16 = raw.view(np.int16).reshape(-1).astype(np.float64)
        return w_fit + r16 * 1e-6
    raw = np.frombuffer(base64.b64decode(enc["b64"]), dtype=np.uint8).reshape(8, n).T.copy()
    return raw.view(np.float64).reshape(-1)


def _encode_f32_t21(arr: np.ndarray, mask_bits: int = 0xFFFFF800) -> dict[str, Any]:
    a = np.asarray(arr, dtype=np.float32)
    fin = np.isfinite(a)
    if not np.any(fin):
        return {"all_nan": True, "n": int(len(a))}
    a_clean = np.where(fin, a, np.float32(np.nan))
    u = a_clean.view(np.uint32)
    u_masked = np.where(fin, u & np.uint32(mask_bits), u)
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


def _arm_to_bary_vac(arm_wave: np.ndarray, specsys: str, berv_kms: float, wave_is_air: bool = True) -> np.ndarray:
    """Convert spectral wavelength axis (air/vac, topo/bary) to barycentric vacuum Angstrom."""
    w_vac = air_to_vac_a(arm_wave) if wave_is_air else np.asarray(arm_wave, dtype=np.float64)
    if specsys in ("TOPOCENT", "GEOCENT", "UNKNOWN", ""):
        return w_vac * (1.0 + float(berv_kms) / C_KMS)
    return w_vac


# ---------------------------------------------------------------------------
# Stage A: Verified Raw FITS Ingestion -> Bounded Bundle (< 25.0 MiB)
# ---------------------------------------------------------------------------

def _extract_d093_fits(fp: Path, row: dict[str, str]) -> dict[str, Any]:
    from astropy.io import fits

    inst = row["instrument"]
    ra_deg = float(row["s_ra"])
    dec_deg = float(row["s_dec"])
    mjd_nom = float(row["mjd_obs"])
    dp_id = row["dp_id"]

    with fits.open(fp, memmap=False) as hdul:
        h0 = hdul[0].header
        arms_out: list[dict[str, Any]] = []

        if inst == "GEMINI_GRACES":
            d = np.asarray(hdul[0].data, dtype=np.float64)
            if d.ndim != 2 or d.shape[0] not in (12, 28):
                raise RuntimeError(f"Unexpected GRACES shape on {dp_id}: {d.shape}")
            if d.shape[0] == 12:
                w_nm, fl_all, er_all = d[3], d[4], d[5]
            else:
                w_nm, fl_all, er_all = d[7], d[8], d[11]
            w_air_a = w_nm * 10.0
            specsys = "BARYCENT"
            wave_is_air = True
            berv_kms = float(h0.get("HRV", analytical_observatory_berv_kms(ra_deg, dec_deg, mjd_nom, inst)))
            berv_src = "HRV" if h0.get("HRV") is not None else "STDLIB_ANALYTICAL"
            t_exptime = float(h0.get("EXPTIME", row["t_exptime"]))
            mjdate = float(h0.get("MJDATE", mjd_nom))
            if abs(mjdate - mjd_nom) > 0.05:
                raise RuntimeError(f"GRACES MJDATE mismatch on {dp_id}: hdr={mjdate}, row={mjd_nom}")

            dw = np.diff(w_air_a)
            splits = np.where((dw < -0.5) | (np.abs(dw) > 0.35) | (dw <= 0.0))[0] + 1
            bounds = [0] + list(splits) + [len(w_air_a)]
            ord_i = 0
            for a_i, b_i in zip(bounds[:-1], bounds[1:]):
                if (b_i - a_i) < 120:
                    continue
                ord_i += 1
                # Trim 12 edge pixels at order ends
                s0, s1 = a_i + 12, b_i - 12
                wo = w_air_a[s0:s1]
                fo = fl_all[s0:s1]
                eo = er_all[s0:s1]
                qo = np.where(
                    np.isfinite(wo) & np.isfinite(fo) & np.isfinite(eo) & (eo > 0.0),
                    0,
                    1,
                ).astype(np.int32)
                arms_out.append({
                    "arm": f"GRACES_O{ord_i:02d}",
                    "order": ord_i,
                    "dp_file_id": row["f1_id"],
                    "specsys": specsys,
                    "wave_is_air": wave_is_air,
                    "berv_kms": round(berv_kms, 5),
                    "berv_src": berv_src,
                    "wave": _encode_wave(wo),
                    "flux": _encode_f32_t21(fo, mask_bits=0xFFFFE000),
                    "err": _encode_f32_t21(eo, mask_bits=0xFFFFE000),
                    "qual": _encode_qual(qo),
                })

            return {
                "arms": arms_out,
                "specsys": specsys,
                "wave_is_air": wave_is_air,
                "berv_kms": round(berv_kms, 5),
                "berv_src": berv_src,
                "mjd_obs": mjd_nom,
                "t_exptime_s": t_exptime,
                "resolving_power": float(row["resolving_power"]),
                "f_unit": "ADU",
                "fluxcal": "RELATIVE",
            }

        if inst == "ESO_CORALIE":
            tab = hdul[1].data
            h1 = hdul[1].header
            w_vac_a = np.asarray(tab["WAVE"][0], dtype=np.float64)
            fl = np.asarray(tab["FLUX"][0], dtype=np.float64)
            er = np.asarray(tab["ERR"][0], dtype=np.float64)
            qu = np.asarray(tab["QUAL"][0], dtype=np.int32)
            specsys = str(h0.get("SPECSYS", h1.get("SPECSYS", "BARYCENT"))).strip().upper()
            wave_is_air = False
            berv_kms = float(h0.get("HIERARCH ESO QC BERV", analytical_observatory_berv_kms(ra_deg, dec_deg, mjd_nom, inst)))
            berv_src = "ESO_QC_BERV" if "HIERARCH ESO QC BERV" in h0 else "STDLIB_ANALYTICAL"
            mjd_obs = float(h0.get("MJD-OBS", mjd_nom))
            t_exptime = float(h0.get("EXPTIME", row["t_exptime"]))
            rpow = float(h0.get("SPEC_RES", h1.get("SPEC_RES", row["resolving_power"])) or row["resolving_power"])
            arms_out.append({
                "arm": "CORALIE",
                "order": 0,
                "dp_file_id": row["f1_id"],
                "specsys": specsys,
                "wave_is_air": wave_is_air,
                "berv_kms": round(berv_kms, 5),
                "berv_src": berv_src,
                "wave": _encode_wave(w_vac_a),
                "flux": _encode_f32_t21(fl, mask_bits=0xFFFFF800),
                "err": _encode_f32_t21(er, mask_bits=0xFFFFE000),
                "qual": _encode_qual(qu),
            })
            return {
                "arms": arms_out,
                "specsys": specsys,
                "wave_is_air": wave_is_air,
                "berv_kms": round(berv_kms, 5),
                "berv_src": berv_src,
                "mjd_obs": mjd_obs,
                "t_exptime_s": t_exptime,
                "resolving_power": rpow if rpow > 1000.0 else float(row["resolving_power"]),
                "f_unit": str(hdul[1].columns["FLUX"].unit or ""),
                "fluxcal": str(h0.get("FLUXCAL", "UNCALIBRATED")).strip().upper(),
            }

        if inst == "CARMENES_VIS":
            sp = np.asarray(hdul[1].data, dtype=np.float64)
            co = np.asarray(hdul[2].data, dtype=np.float64)
            sg = np.asarray(hdul[3].data, dtype=np.float64)
            wv = np.asarray(hdul[4].data, dtype=np.float64)
            if sp.shape != (61, 4096) or wv.shape != (61, 4096):
                raise RuntimeError(f"Unexpected CARMENES_VIS shape on {dp_id}: {sp.shape}")

            exptime = float(h0.get("EXPTIME", row["t_exptime"]))
            mjd_obs = float(h0.get("HIERARCH CARACAL MJD-OBS", mjd_nom))
            tmean_s = float(h0.get("HIERARCH CARACAL TMEAN", 0.5 * exptime))
            if not (math.isfinite(tmean_s) and 0.0 <= tmean_s <= 1.5 * exptime):
                tmean_s = 0.5 * exptime
            mjd_mid = mjd_obs + tmean_s / 86400.0
            berv_kms = float(h0["HIERARCH CARACAL BERV"])
            berv_analyt = analytical_observatory_berv_kms(ra_deg, dec_deg, mjd_mid, inst)
            if abs(berv_kms - berv_analyt) > 0.65:
                raise RuntimeError(f"CARMENES BERV mismatch on {dp_id}: hdr={berv_kms:.4f}, analyt={berv_analyt:.4f}")

            specsys = "TOPOCENT"
            wave_is_air = False
            for o in range(61):
                # Trim 16 edge pixels on all CARMENES orders and keep science orders covering [5130, 9750] A
                wo = wv[o, 16:4080]
                so = sp[o, 16:4080]
                coo = co[o, 16:4080]
                sgo = sg[o, 16:4080]
                w_min_o, w_max_o = float(np.nanmin(wo)), float(np.nanmax(wo))
                if w_min_o > 9750.0 or w_max_o < 5130.0:
                    continue
                vc = np.isfinite(wo) & np.isfinite(so) & np.isfinite(coo) & (coo > 0.0) & (so > 0.0) & np.isfinite(sgo) & (sgo > 0.0)
                if int(vc.sum()) < 200:
                    continue
                med_c = exact_median_1d(coo[vc])
                # Preserve order-relative photons in ADU * 1000 scale while canceling blaze shape
                f_flat = np.where((coo > 0.0) & np.isfinite(so) & np.isfinite(coo), (so / coo) * med_c * 1000.0, np.nan)
                e_flat = np.where((coo > 0.0) & np.isfinite(sgo) & (sgo > 0.0) & np.isfinite(coo), (sgo / coo) * med_c * 1000.0, np.nan)
                arms_out.append({
                    "arm": f"CARM_O{o + 1:02d}",
                    "order": o + 1,
                    "dp_file_id": row["f1_id"],
                    "specsys": specsys,
                    "wave_is_air": wave_is_air,
                    "berv_kms": round(berv_kms, 5),
                    "berv_src": "CARACAL_BERV",
                    "wave": _encode_wave(wo),
                    "flux": _encode_f32_t21(f_flat, mask_bits=0xFFFFF800),
                    "err": _encode_f32_t21(e_flat, mask_bits=0xFFFFE000),
                    "qual": _encode_qual(None),
                })

            return {
                "arms": arms_out,
                "specsys": specsys,
                "wave_is_air": wave_is_air,
                "berv_kms": round(berv_kms, 5),
                "berv_src": "CARACAL_BERV",
                "mjd_obs": mjd_obs,
                "t_exptime_s": exptime,
                "resolving_power": float(row["resolving_power"]),
                "f_unit": "ADU_BLAZE_FLAT",
                "fluxcal": "RELATIVE",
            }

        raise RuntimeError(f"Unsupported D093 instrument: {inst}")


def run_stage_a_build_bundle(full_dir: Path, bundle_out: Path = DEFAULT_BUNDLE) -> dict[str, Any]:
    cohort_path = WS / "FROZEN_COHORT_D093.csv"
    man_path = WS / "FULL_D093_INPUT_MANIFEST.json"
    if not cohort_path.exists() or not man_path.exists():
        raise RuntimeError("Missing FROZEN_COHORT_D093.csv or FULL_D093_INPUT_MANIFEST.json")

    with cohort_path.open("r", encoding="utf-8", newline="") as fh:
        coh_rows = list(csv.DictReader(fh))
    man_doc = json.loads(man_path.read_text(encoding="utf-8"))
    man_by_dp = {e["dp_id"]: e for e in man_doc["exposures"]}
    assert len(coh_rows) == 30 and len(man_by_dp) == 30

    print(f"Stage A: ingesting 30 raw D093 FITS from {full_dir}...", flush=True)
    bundle_exps: list[dict[str, Any]] = []

    for row in coh_rows:
        dp_id = row["dp_id"]
        me = man_by_dp[dp_id]
        fp = full_dir / me["f1_rel"]
        if not fp.exists() or _sha256(fp) != me["f1_sha256"]:
            raise RuntimeError(f"FITS missing or SHA-256 mismatch: {fp}")

        ext = _extract_d093_fits(fp, row)
        bundle_exps.append({
            "dp_id": dp_id,
            "instrument": row["instrument"],
            "star": row["canonical_target"],
            "common_name": row["common_name"],
            "role": row["role"],
            "subrole": row["subrole"],
            "science_track": row["science_track"],
            "panchromatic_bridge": row["panchromatic_bridge"] == "True",
            "gaia_source_id": int(row["gaia_source_id"]),
            "s_ra": float(row["s_ra"]),
            "s_dec": float(row["s_dec"]),
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
            "signed_phase": float(row["signed_phase"]),
            "planet_orbital_rv_kms": float(row["planet_orbital_rv_kms"]),
            "specsys": ext["specsys"],
            "wave_is_air": ext["wave_is_air"],
            "berv_kms": ext["berv_kms"],
            "berv_src": ext["berv_src"],
            "flux_unit": ext["f_unit"],
            "fluxcal": ext["fluxcal"],
            "arms": ext["arms"],
        })

    bundle = {
        "schema": "D093_BOUNDED_BUNDLE_V1",
        "phase_id": "D093",
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
# Spectrum Unpacking, Resampling & Multi-Order Inverse-Variance Merge
# ---------------------------------------------------------------------------

def _unpack_exposure_spectrum(exp: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """Decode arms, convert air/vac + barycentric frames, compute continuum & merge overlapping orders."""
    inst = exp["instrument"]
    native_arms: list[dict[str, Any]] = []

    for arm in exp["arms"]:
        w_raw = _decode_wave(arm["wave"])
        is_air = bool(arm.get("wave_is_air", exp.get("wave_is_air", inst in ("GEMINI_GRACES", "ESO_FEROS"))))
        w_bary = _arm_to_bary_vac(w_raw, arm["specsys"], float(arm["berv_kms"]), wave_is_air=is_air)
        fl = _decode_f32_t21(arm["flux"])
        er = _decode_f32_t21(arm["err"])
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
        fn = np.where(bad | (~np.isfinite(fl_clean)) | (~np.isfinite(ce)) | (ce <= 0.0), np.nan, fl_clean / ce)

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

    if len(native_arms) == 1:
        a0 = native_arms[0]
        return {"w_bary": a0["w_bary"], "fn": a0["fn"], "flux_cgs": a0["flux"], "arms": native_arms}

    # Inverse-variance weighted 1D merge of overlapping echelle orders onto instrument step grid
    step_a = float(cfg["coadd_step_angstrom"])
    w_min = min(float(np.min(a["w_bary"])) for a in native_arms)
    w_max = max(float(np.max(a["w_bary"])) for a in native_arms)
    w_grid = np.arange(w_min, w_max + 0.5 * step_a, step_a, dtype=np.float64)
    num_fn = np.zeros(len(w_grid), dtype=np.float64)
    num_fl = np.zeros(len(w_grid), dtype=np.float64)
    den = np.zeros(len(w_grid), dtype=np.float64)

    for a in native_arms:
        wa = a["w_bary"]
        fn_a = a["fn"]
        fl_a = a["flux"]
        co_a = a["cont"]
        er_a = a["err"]
        if len(wa) < 80:
            continue
        # Trim outer 16 pixels to prevent echelle blaze-edge noise spikes in merge
        m = np.isfinite(wa) & np.isfinite(fn_a) & np.isfinite(fl_a) & np.isfinite(co_a) & (co_a > 0.0)
        m[:16] = False
        m[-16:] = False
        if er_a is not None:
            m &= np.isfinite(er_a) & (er_a > 0.0)
        if int(m.sum()) < 30:
            continue
        wb_v = wa[m]
        fn_v = fn_a[m]
        fl_v = fl_a[m]
        if er_a is not None:
            rel_sig = er_a[m] / np.maximum(1e-12, co_a[m])
            wt_v = 1.0 / np.maximum(1e-6, rel_sig ** 2)
        else:
            wt_v = np.ones_like(fn_v)

        i0 = int(np.searchsorted(w_grid, float(wb_v[0]), side="left"))
        i1 = int(np.searchsorted(w_grid, float(wb_v[-1]), side="right"))
        if i1 <= i0 + 3:
            continue
        bg = w_grid[i0:i1]
        # Preserve interior gaps cleanly
        idx_hi = np.searchsorted(wb_v, bg)
        i_r = np.clip(idx_hi, 1, len(wb_v) - 1)
        ok_g = (wb_v[i_r] - wb_v[i_r - 1]) <= 0.35
        fn_i = np.where(ok_g, np.interp(bg, wb_v, fn_v), 0.0)
        fl_i = np.where(ok_g, np.interp(bg, wb_v, fl_v), 0.0)
        wt_i = np.where(ok_g, np.interp(bg, wb_v, wt_v), 0.0)
        num_fn[i0:i1] += fn_i * wt_i
        num_fl[i0:i1] += fl_i * wt_i
        den[i0:i1] += wt_i

    ok = den > 0.0
    fn_all = np.where(ok, num_fn / np.maximum(den, 1e-30), np.nan)
    fl_all = np.where(ok, num_fl / np.maximum(den, 1e-30), np.nan)
    return {"w_bary": w_grid, "fn": fn_all, "flux_cgs": fl_all, "arms": native_arms}


def _resample_gap_safe(w_src: np.ndarray, y_src: np.ndarray, grid: np.ndarray, max_gap_a: float) -> np.ndarray:
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
        if len(w) < 60 or target_bary_a < float(w[10]) or target_bary_a > float(w[-11]):
            continue
        k = int(np.argmin(np.abs(w - target_bary_a)))
        if abs(float(w[k]) - target_bary_a) > 2.5 or k < 12 or k >= len(w) - 12:
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
# Read-Only Companion Archive Loaders (Archives N, P, R & Prior Coordinates)
# ---------------------------------------------------------------------------

def _load_archive_r_feros_peers(archives_dir: Path) -> list[dict[str, Any]]:
    arch_r = archives_dir / ARCHIVE_R_NAME
    with zipfile.ZipFile(arch_r, "r") as zr:
        bname = [n for n in zr.namelist() if n.endswith("d092_bounded_bundle.json.gz")][0]
        b92 = json.loads(gzip.decompress(zr.read(bname)).decode("utf-8"))
    return [e for e in b92["exposures"] if e.get("instrument") == "ESO_FEROS"]


def _load_archive_n_d088(archives_dir: Path) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    arch_n = archives_dir / ARCHIVE_N_NAME
    with zipfile.ZipFile(arch_n, "r") as zn:
        bname = [n for n in zn.namelist() if n.endswith("d088_bounded_bundle.json.gz")][0]
        lname = [n for n in zn.namelist() if n.endswith("V3_9_CANDIDATE_LEDGER.csv")][0]
        b88 = json.loads(gzip.decompress(zn.read(bname)).decode("utf-8"))
        led88 = list(csv.DictReader(io.StringIO(zn.read(lname).decode("utf-8"))))
    return b88["real_candidates_bundle"], b88["sparse_atlas_by_group"], led88


def _load_archive_p_nirspec_g395h(archives_dir: Path) -> dict[str, dict[str, Any]]:
    arch_p = archives_dir / ARCHIVE_P_NAME
    with zipfile.ZipFile(arch_p, "r") as zp:
        bname = [n for n in zp.namelist() if n.endswith("d090_bounded_bundle.json.gz")][0]
        b90 = json.loads(gzip.decompress(zp.read(bname)).decode("utf-8"))

    by_star: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for exp in b90["exposures"]:
        if exp.get("instrument") == "JWST_NIRSPEC_G395H":
            by_star[exp["star"]].append(exp)

    merged: dict[str, dict[str, Any]] = {}
    for st, exps in sorted(by_star.items()):
        seg_groups: dict[str, list[tuple[np.ndarray, np.ndarray]]] = defaultdict(list)
        rv = float(exps[0].get("prior_rv_kms") or 0.0)
        for e in exps:
            for s in e["segments"]:
                wa_um = np.asarray(s["wave_a"], dtype=np.float64) / (1e4 * (1.0 + rv / C_KMS))
                fl = np.asarray(s["flux_flam"], dtype=np.float64)
                key = str(s.get("subband", ""))[:4]
                seg_groups[key].append((wa_um, fl))

        w_parts: list[np.ndarray] = []
        f_parts: list[np.ndarray] = []
        w_raw_parts: list[np.ndarray] = []
        f_raw_parts: list[np.ndarray] = []
        for _, items in sorted(seg_groups.items()):
            w_ref = items[0][0]
            if len(items) == 1:
                f_med = items[0][1]
            else:
                mat = np.vstack([np.interp(w_ref, wi, fi, left=np.nan, right=np.nan) for wi, fi in items])
                with warnings.catch_warnings(), np.errstate(all="ignore"):
                    warnings.simplefilter("ignore", RuntimeWarning)
                    f_med = np.nanmedian(mat, axis=0)
            w_raw_parts.append(w_ref)
            f_raw_parts.append(f_med)
            m_trim = (w_ref >= float(w_ref[0]) + NIRSPEC_EDGE_TRIM_UM) & (w_ref <= float(w_ref[-1]) - NIRSPEC_EDGE_TRIM_UM)
            w_parts.append(w_ref[m_trim])
            f_parts.append(f_med[m_trim])

        merged[st] = {
            "star": st,
            "common_name": exps[0].get("common_name", st),
            "role": exps[0].get("role", "SCIENCE"),
            "dist_pc": float(exps[0].get("dist_pc") or 10.0),
            "teff_k": float(exps[0].get("teff_k") or 5000.0),
            "n_exposures": len(exps),
            "wave_um": np.concatenate(w_raw_parts),
            "flux_flam": np.concatenate(f_raw_parts),
            "segments": list(zip(w_parts, f_parts)),
        }
    return merged


def _load_prior_star_coords_and_mjds(archives_dir: Path, prior_stars: set[str]) -> tuple[dict[str, tuple[float, float]], dict[str, list[float]]]:
    """Read (s_ra, s_dec) and all mjd_obs for prior stars strictly from read-only Companion Archives."""
    coords: dict[str, tuple[float, float]] = {}
    mjds: dict[str, list[float]] = defaultdict(list)
    for zp_path in sorted(archives_dir.glob("SETI_D*.zip")):
        with zipfile.ZipFile(zp_path, "r") as zf:
            for nm in sorted(zf.namelist()):
                if not nm.endswith(".csv"):
                    continue
                if not any(k in nm for k in ("COHORT", "PROVENANCE", "SUMMARY", "GEOM")):
                    continue
                txt = zf.read(nm).decode("utf-8", errors="ignore")
                rows = list(csv.DictReader(io.StringIO(txt)))
                if not rows:
                    continue
                cols = set(rows[0].keys())
                sk = "canonical_target" if "canonical_target" in cols else ("star" if "star" in cols else None)
                if not sk:
                    continue
                rk = "s_ra" if "s_ra" in cols else ("ra_deg" if "ra_deg" in cols else None)
                dk = "s_dec" if "s_dec" in cols else ("dec_deg" if "dec_deg" in cols else None)
                mk = "mjd_obs" if "mjd_obs" in cols else None
                if rk and dk:
                    for r in rows:
                        st = r.get(sk, "")
                        if st in prior_stars and r.get(rk) and r.get(dk):
                            coords.setdefault(st, (float(r[rk]), float(r[dk])))
                if mk:
                    for r in rows:
                        st = r.get(sk, "")
                        mv = r.get(mk, "")
                        if st in prior_stars and mv:
                            try:
                                mjds[st].append(float(mv))
                            except ValueError:
                                pass
    return coords, mjds


# ---------------------------------------------------------------------------
# Audited Stage-2 Refinements (Preserve Immutable Stage-1 v5_1_detector.py):
#   1. Joint sibling-masked NIRSpec G395H molecular CCF (fixes CO/13CO 4.67+4.78 um self-masking)
#   2. Standardized amplitude-aware G8_V51b patch novelty + morphology consistency
# ---------------------------------------------------------------------------

def _fit_nirspec_template_v51b(
    segments: list[tuple[np.ndarray, np.ndarray]],
    comps: list[dict[str, float]],
) -> dict[str, Any]:
    """Fit single- or multi-component NIRSpec template with joint sibling-band exclusion from sidebands."""
    num_sum = t2_sum = var_sum = w_sum_cov = 0.0
    n_cov = 0
    seg_to_comps: dict[int, list[dict[str, float]]] = {}
    for comp in comps:
        mu, sig = float(comp["mu_um"]), float(comp["sigma_um"])
        best_si: int | None = None
        best_n = 0
        for si, (w_seg, _) in enumerate(segments):
            nc = int(np.sum(np.abs(w_seg - mu) <= 2.2 * sig))
            if nc >= 12 and nc > best_n:
                best_n, best_si = nc, si
        if best_si is not None:
            seg_to_comps.setdefault(best_si, []).append(comp)

    for si, sc in seg_to_comps.items():
        w_seg, f_seg = segments[si]
        lo_core = min(float(c["mu_um"]) - 2.0 * float(c["sigma_um"]) for c in sc)
        hi_core = max(float(c["mu_um"]) + 2.0 * float(c["sigma_um"]) for c in sc)
        sig_max = max(float(c["sigma_um"]) for c in sc)
        win_mask = (w_seg >= lo_core - 3.0 * sig_max) & (w_seg <= hi_core + 3.0 * sig_max)
        core_mask = np.zeros(len(w_seg), dtype=bool)
        for c in sc:
            core_mask |= np.abs(w_seg - float(c["mu_um"])) < 2.0 * float(c["sigma_um"])
        sb_mask = win_mask & (~core_mask)
        if int(np.sum(sb_mask)) < 16:
            win_mask = (w_seg >= lo_core - 4.0 * sig_max) & (w_seg <= hi_core + 4.0 * sig_max)
            sb_mask = win_mask & (~core_mask)
        fit_c = _fit_miri_loglog_continuum(w_seg, f_seg, win_mask, sb_mask, 0.5 * (lo_core + hi_core))
        if fit_c is None:
            continue
        cont_win, cont_sb, X_win, X_sb = fit_c
        safe_sb = np.abs(cont_sb) > 1e-30
        safe_win = np.abs(cont_win) > 1e-30
        if int(np.sum(safe_sb)) < 10 or int(np.sum(safe_win)) < 12:
            continue
        r_sb = (f_seg[sb_mask][safe_sb] - cont_sb[safe_sb]) / np.abs(cont_sb[safe_sb])
        r_win = (f_seg[win_mask][safe_win] - cont_win[safe_win]) / np.abs(cont_win[safe_win])
        w_win = w_seg[win_mask][safe_win]
        w_sb_safe = w_seg[sb_mask][safe_sb]
        sigma_sb = _sideband_noise_sigma(r_sb)

        T_vec = np.zeros_like(w_win)
        T_sb = np.zeros_like(w_sb_safe)
        for c in sc:
            T_vec += float(c["weight"]) * np.exp(-0.5 * ((w_win - float(c["mu_um"])) / float(c["sigma_um"])) ** 2)
            T_sb += float(c["weight"]) * np.exp(-0.5 * ((w_sb_safe - float(c["mu_um"])) / float(c["sigma_um"])) ** 2)
        T_vec = T_vec - float(np.median(T_sb))
        t2 = float(np.dot(T_vec, T_vec))
        if t2 <= 1e-12:
            continue
        X_sb_s = X_sb[safe_sb]
        X_win_s = X_win[safe_win]
        g_proj = X_win_s.T @ T_vec
        xt_x = X_sb_s.T @ X_sb_s
        try:
            var_cont = max(0.0, float(g_proj.T @ np.linalg.solve(xt_x + 1e-9 * np.eye(xt_x.shape[0]), g_proj)))
        except np.linalg.LinAlgError:
            var_cont = 0.0
        num_sum += float(np.dot(T_vec, r_win))
        t2_sum += t2
        var_sum += (sigma_sb ** 2) * (t2 + var_cont)
        n_cov += len(sc)
        w_sum_cov += sum(float(c["weight"]) for c in sc)

    if n_cov == 0 or t2_sum <= 1e-12 or var_sum <= 1e-30:
        return {
            "covered": False, "depth": 0.0, "sigma_depth": math.nan,
            "ccf_sigma_abs": 0.0, "delta_min_5sigma": math.nan, "ppm_equiv_10pct_ref": math.nan,
        }
    w_scale = max(1e-6, w_sum_cov / float(n_cov))
    depth = -(num_sum / t2_sum) * w_scale
    sigma_depth = (math.sqrt(var_sum) / t2_sum) * w_scale
    ccf_s = depth / max(1e-12, sigma_depth)
    d5 = min(1.0, 5.0 * sigma_depth)
    return {
        "covered": True, "depth": float(depth), "sigma_depth": float(sigma_depth),
        "ccf_sigma_abs": float(ccf_s), "delta_min_5sigma": float(d5),
        "ppm_equiv_10pct_ref": float(10.0 * (d5 / 0.10)),
    }


def _joint_nirspec_confounder_v51b(
    segments: list[tuple[np.ndarray, np.ndarray]],
    mol_comps: list[dict[str, float]],
    conf_comps: list[dict[str, float]],
    conf_is_emission: bool = False,
) -> dict[str, Any]:
    """Joint 2-parameter OLS of full multi-component NIRSpec molecule vs natural confounder."""
    overlaps = any(
        abs(float(mc["mu_um"]) - float(cc["mu_um"])) <= 2.5 * (float(mc["sigma_um"]) + float(cc["sigma_um"]))
        for mc in mol_comps for cc in conf_comps
    )
    if not overlaps:
        return {"overlaps": False}

    xtx_tot = np.zeros((2, 2), dtype=np.float64)
    xty_tot = np.zeros(2, dtype=np.float64)
    cov_num = np.zeros((2, 2), dtype=np.float64)
    n_seg_used = 0

    for w_seg, f_seg in segments:
        mc_in = [c for c in mol_comps if w_seg[0] + 0.02 < float(c["mu_um"]) < w_seg[-1] - 0.02]
        cc_in = [c for c in conf_comps if w_seg[0] + 0.02 < float(c["mu_um"]) < w_seg[-1] - 0.02]
        if not mc_in or not cc_in:
            continue
        all_c = mc_in + cc_in
        lo_core = min(float(c["mu_um"]) - 2.0 * float(c["sigma_um"]) for c in all_c)
        hi_core = max(float(c["mu_um"]) + 2.0 * float(c["sigma_um"]) for c in all_c)
        sig_max = max(float(c["sigma_um"]) for c in all_c)
        win_mask = (w_seg >= lo_core - 3.0 * sig_max) & (w_seg <= hi_core + 3.0 * sig_max)
        core_mask = np.zeros(len(w_seg), dtype=bool)
        for c in all_c:
            core_mask |= np.abs(w_seg - float(c["mu_um"])) < 2.0 * float(c["sigma_um"])
        sb_mask = win_mask & (~core_mask)
        if int(np.sum(sb_mask)) < 16:
            win_mask = (w_seg >= lo_core - 4.5 * sig_max) & (w_seg <= hi_core + 4.5 * sig_max)
            sb_mask = win_mask & (~core_mask)
        fit_c = _fit_miri_loglog_continuum(w_seg, f_seg, win_mask, sb_mask, 0.5 * (lo_core + hi_core))
        if fit_c is None:
            continue
        cont_win, cont_sb, X_win, X_sb = fit_c
        safe_sb = np.abs(cont_sb) > 1e-30
        safe_win = np.abs(cont_win) > 1e-30
        if int(np.sum(safe_sb)) < 12 or int(np.sum(safe_win)) < 16:
            continue
        r_sb = (f_seg[sb_mask][safe_sb] - cont_sb[safe_sb]) / np.abs(cont_sb[safe_sb])
        y_abs = -(f_seg[win_mask][safe_win] - cont_win[safe_win]) / np.abs(cont_win[safe_win])
        w_win = w_seg[win_mask][safe_win]
        sigma_sb = _sideband_noise_sigma(r_sb)
        tm = sum(float(c["weight"]) * np.exp(-0.5 * ((w_win - float(c["mu_um"])) / float(c["sigma_um"])) ** 2) for c in mc_in)
        tc = sum(float(c["weight"]) * np.exp(-0.5 * ((w_win - float(c["mu_um"])) / float(c["sigma_um"])) ** 2) for c in cc_in)
        X = np.column_stack([tm, tc])
        xtx = X.T @ X
        X_sb_s, X_win_s = X_sb[safe_sb], X_win[safe_win]
        G = X_win_s.T @ X
        try:
            cov_c = G.T @ np.linalg.solve(X_sb_s.T @ X_sb_s + 1e-9 * np.eye(X_sb_s.shape[1]), G)
        except np.linalg.LinAlgError:
            cov_c = np.zeros((2, 2), dtype=np.float64)
        xtx_tot += xtx
        xty_tot += X.T @ y_abs
        cov_num += (sigma_sb ** 2) * (xtx + cov_c)
        n_seg_used += 1

    if n_seg_used == 0 or np.linalg.cond(xtx_tot + 1e-9 * np.eye(2)) > 1e4:
        return {"overlaps": False}
    try:
        inv_xtx = np.linalg.inv(xtx_tot + 1e-9 * np.eye(2))
        beta = inv_xtx @ xty_tot
        var_beta = inv_xtx @ cov_num @ inv_xtx
    except np.linalg.LinAlgError:
        return {"overlaps": False}
    z_m = float(beta[0] / max(1e-12, math.sqrt(max(0.0, float(var_beta[0, 0])))))
    z_c = float(beta[1] / max(1e-12, math.sqrt(max(0.0, float(var_beta[1, 1])))))
    return {"overlaps": True, "ccf_mol_given_conf": z_m, "ccf_conf_given_mol": (-z_c if conf_is_emission else z_c)}


def _scan_nirspec_v51b(segments: list[tuple[np.ndarray, np.ndarray]]) -> dict[str, Any]:
    conf_res: dict[str, dict[str, Any]] = {}
    max_conf = 0.0
    for cn, cc in NATURAL_NIRSPEC_CONFOUNDERS_UM.items():
        cr = _fit_nirspec_template_v51b(segments, cc)
        raw_s = float(cr["ccf_sigma_abs"])
        phys_s = max(0.0, abs(raw_s) if cn == "H2_0_0_S9_VIB" else raw_s)
        cr["physical_confounder_sigma"] = phys_s
        conf_res[cn] = cr
        if cr["covered"]:
            max_conf = max(max_conf, phys_s)

    mol_res: dict[str, dict[str, Any]] = {}
    dets: list[str] = []
    for mn, mc in NIRSPEC_MOL_TEMPLATES_UM.items():
        mr = _fit_nirspec_template_v51b(segments, mc)
        s = float(mr["ccf_sigma_abs"])
        ok = bool(mr["covered"] and s >= 5.0)
        if mr["covered"]:
            for cn, cc in NATURAL_NIRSPEC_CONFOUNDERS_UM.items():
                is_em = cn == "H2_0_0_S9_VIB" and float(conf_res[cn]["ccf_sigma_abs"]) < 0.0
                jr = _joint_nirspec_confounder_v51b(segments, mc, cc, conf_is_emission=is_em)
                if jr.get("overlaps"):
                    zm, zc = float(jr["ccf_mol_given_conf"]), max(0.0, float(jr["ccf_conf_given_mol"]))
                    if not (zm >= 5.0 and zm > 1.5 * zc):
                        ok = False
                else:
                    md = min(abs(float(a["mu_um"]) - float(b["mu_um"])) for a in mc for b in cc)
                    if md <= 0.35 and conf_res[cn]["covered"] and not (s > 1.5 * float(conf_res[cn]["physical_confounder_sigma"])):
                        ok = False
        mr["passes_ccf"] = ok
        mol_res[mn] = mr
        if ok:
            dets.append(mn)
    return {
        "molecules": mol_res,
        "confounders": conf_res,
        "max_confounder_sigma": float(max_conf),
        "detected_molecules": dets,
        "any_detection": len(dets) > 0,
    }


def _extract_g8_feat_v51b(
    z_vec: np.ndarray,
    idx: int,
    z_rpca: float,
    rarity: float,
    f_rest: float,
    f_topo: float,
    half_px: int = 8,
) -> tuple[np.ndarray, dict[str, float]] | None:
    n = len(z_vec)
    if idx < half_px or idx + half_px >= n:
        return None
    sub = np.asarray(z_vec[idx - half_px : idx + half_px + 1], dtype=np.float64)
    if not np.all(np.isfinite(sub)):
        return None
    core = sub[half_px - 2 : half_px + 3]
    wings = np.concatenate([sub[: half_px - 3], sub[half_px + 4 :]])
    pk = float(np.max(core))
    wing_rms = float(np.sqrt(np.mean(wings ** 2)))
    wing_min = float(np.min(sub))
    e_conc = float(np.sum(np.maximum(0.0, core) ** 2) / max(1e-6, float(np.sum(sub ** 2))))
    patch_comp = np.arcsinh(sub[half_px - 6 : half_px + 7] / 2.5)
    meta = np.asarray([
        math.asinh(float(z_rpca) / 3.0),
        float(rarity),
        float(f_rest),
        float(f_topo),
        e_conc,
        math.log1p(max(0.0, wing_rms)),
        max(-3.0, min(3.0, wing_min / 3.0)),
        max(0.0, pk / max(1.0, wing_rms + 0.5)) / 5.0,
    ], dtype=np.float64)
    return np.concatenate([patch_comp, meta]), {"e_conc": e_conc, "wing_rms": wing_rms, "wing_min": wing_min, "pk": pk}


def _fit_g8_v51b(
    feats: list[np.ndarray] | np.ndarray,
    pca_dim: int = 8,
    knn_k: int = 7,
    min_novelty_z: float = 3.5,
) -> dict[str, Any]:
    arr = np.asarray(feats, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[0] < max(24, knn_k + 4):
        return {"ready": False, "n_ref": int(arr.shape[0]) if arr.ndim == 2 else 0, "min_novelty_z": float(min_novelty_z)}
    mu = np.mean(arr, axis=0)
    sd = np.maximum(0.08, np.std(arr, axis=0))
    xs = (arr - mu[None, :]) / sd[None, :]
    evals, evecs = np.linalg.eigh((xs.T @ xs) / max(1.0, float(arr.shape[0] - 1)))
    ord_idx = np.argsort(evals)[::-1]
    k_pca = min(int(pca_dim), arr.shape[1])
    evals_k = np.maximum(0.05, evals[ord_idx[:k_pca]])
    basis_k = evecs[:, ord_idx[:k_pca]]
    proj = (xs @ basis_k) / np.sqrt(evals_k)[None, :]
    rec_err = np.linalg.norm(xs - (xs @ basis_k) @ basis_k.T, axis=1)
    diff2 = np.sum(proj * proj, axis=1, keepdims=True) + np.sum(proj * proj, axis=1)[None, :] - 2.0 * (proj @ proj.T)
    np.fill_diagonal(diff2, 1e18)
    k_eff = min(int(knn_k), arr.shape[0] - 1)
    kth_d = np.sqrt(np.partition(np.maximum(0.0, diff2), k_eff - 1, axis=1)[:, k_eff - 1])
    score = np.hypot(kth_d, rec_err)
    ref_med = float(np.median(score))
    ref_mad = max(0.10, MAD_NORM * float(np.median(np.abs(score - ref_med))))
    return {
        "ready": True, "n_ref": int(arr.shape[0]), "pca_dim": k_pca, "knn_k": k_eff,
        "min_novelty_z": float(min_novelty_z), "mu": mu, "sd": sd, "basis_k": basis_k,
        "inv_sqrt_evals": 1.0 / np.sqrt(evals_k), "proj_ref": proj, "ref_med": ref_med, "ref_mad": ref_mad,
    }


def _eval_g8_v51b(
    model: dict[str, Any],
    w_ax: np.ndarray,
    z_vec: np.ndarray,
    center_wave_a: float,
    z_rpca: float,
    rarity: float,
    f_rest: float = 0.0,
    f_topo: float = 0.0,
) -> dict[str, Any]:
    if not model.get("ready"):
        return {"g8_pass": True, "novelty_z": 99.0, "reason": "NO_REF_PASS"}
    idx = max(0, min(len(w_ax) - 1, int(np.searchsorted(w_ax, float(center_wave_a)))))
    res_f = _extract_g8_feat_v51b(z_vec, idx, z_rpca, rarity, f_rest, f_topo)
    if res_f is None:
        return {"g8_pass": False, "novelty_z": 0.0, "reason": "G8_EDGE_NAN"}
    vec, info = res_f
    xs = (vec - model["mu"]) / model["sd"]
    p = (xs @ model["basis_k"]) * model["inv_sqrt_evals"]
    rec_err = float(np.linalg.norm(xs - (xs @ model["basis_k"]) @ model["basis_k"].T))
    d2 = np.sum((model["proj_ref"] - p[None, :]) ** 2, axis=1)
    k_eff = min(int(model["knn_k"]), len(d2) - 1)
    d_k = math.sqrt(max(0.0, float(np.partition(d2, k_eff - 1)[k_eff - 1])))
    nov_z = (math.hypot(d_k, rec_err) - float(model["ref_med"])) / max(1e-6, float(model["ref_mad"]))
    clean_morph = (
        float(z_rpca) >= 6.0
        and float(rarity) >= 0.65
        and float(f_rest) <= 0.30
        and float(f_topo) <= 0.30
        and info["e_conc"] >= 0.85
        and info["wing_rms"] <= 1.35
        and info["wing_min"] >= -2.5
    )
    passed = bool(clean_morph and nov_z >= float(model["min_novelty_z"]))
    return {"g8_pass": passed, "novelty_z": float(nov_z), "reason": "PASS" if passed else "G8_LOW_PATCH_NOVELTY"}


# ---------------------------------------------------------------------------
# V5.1 Calibrations: 1,591 Synthetic Trials across 9 Suites
# ---------------------------------------------------------------------------

def _run_v51_calibrations(
    star_ctx: dict[str, dict[str, Any]],
    g8_models: dict[str, dict[str, Any]],
    nirspec_spectra: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rng = np.random.default_rng(20261121)

    rep_star: dict[str, str] = {}
    for st, ctx in sorted(star_ctx.items()):
        rep_star.setdefault(ctx["instrument"], st)

    # 1. CALIBRATION_V51_BLIND_DRIFT_120 (60 drifting + 30 stationary + 30 1-epoch transient)
    drift_cal_rows: list[dict[str, Any]] = []
    w_dr = 5700.0 + 0.025 * np.arange(8192, dtype=np.float64)
    cfg_dr = get_inst_config("ESO_CORALIE")
    sig_a_dr = 5800.0 / (float(cfg_dr["resolving_power"]) * FWHM_FACTOR)
    dvs_pos_neg = [-210, -165, -120, -85, -55, -32, -18, 18, 32, 55, 85, 120, 165, 210]
    for ti in range(120):
        if ti < 60:
            tcls = "DRIFTING_LASER"
            dv_inj = float(dvs_pos_neg[ti % len(dvs_pos_neg)])
        elif ti < 90:
            tcls = "STATIONARY_LINE"
            dv_inj = float((-1.0, 0.0, 0.8, 1.4)[ti % 4])
        else:
            tcls = "SINGLE_EPOCH_TRANSIENT"
            dv_inj = 0.0

        z1 = rng.normal(0.0, 1.0, len(w_dr))
        z2 = rng.normal(0.0, 1.0, len(w_dr))
        wc = 5740.0 + 1.8 * (ti % 25)
        amp1 = 8.2 + 0.4 * (ti % 5)
        z1 += amp1 * np.exp(-0.5 * ((w_dr - wc) / sig_a_dr) ** 2)
        if tcls != "SINGLE_EPOCH_TRANSIENT":
            w2 = wc * (1.0 + dv_inj / C_KMS)
            amp2 = 7.8 + 0.4 * (ti % 5)
            z2 += amp2 * np.exp(-0.5 * ((w_dr - w2) / sig_a_dr) ** 2)

        cands, _ = scan_blind_drift_dedoppler_v51(w_dr, z1, z2, dt_days=5.0, berv1_kms=-12.0, berv2_kms=15.0, cfg=cfg_dr, star="SYN_DRIFT")
        det = len(cands) > 0
        drift_cal_rows.append({
            "trial_id": f"DRF_{ti + 1:03d}",
            "trial_class": tcls,
            "dv_inj_kms": dv_inj,
            "wave_inj_a": round(wc, 3),
            "detected": bool(det),
            "recovered_dv_kms": cands[0]["dv_kms"] if cands else "",
            "z_drift_comb": cands[0]["z_drift_comb"] if cands else 0.0,
            "expected_detection": tcls == "DRIFTING_LASER",
        })

    # 2. CALIBRATION_V51_PATCH_NOVELTY_120 (40 isolated LSF + 40 shared photospheric + 40 topo/blaze)
    patch_cal_rows: list[dict[str, Any]] = []
    w_p = 5600.0 + 0.025 * np.arange(512, dtype=np.float64)
    sig_p = 5606.0 / (60000.0 * FWHM_FACTOR)
    c0_p = 240
    wc_p = float(w_p[c0_p])
    # Fit calibrated reference background manifold with realistic background photospheric/telluric variance
    ref_cal_feats: list[np.ndarray] = []
    for ib in range(280):
        z_bg = rng.normal(0.0, 1.0, len(w_p))
        if ib % 3 == 0:
            z_bg += 2.8 * np.exp(-0.5 * ((w_p - wc_p) / (2.0 * sig_p)) ** 2)
            rar_b, fr_b, ft_b = 0.30 + 0.20 * rng.random(), 0.35 + 0.30 * rng.random(), 0.10 * rng.random()
        elif ib % 3 == 1:
            z_bg += 2.5 * np.exp(-0.5 * ((w_p - wc_p) / (2.4 * sig_p)) ** 2)
            rar_b, fr_b, ft_b = 0.25 + 0.20 * rng.random(), 0.10 * rng.random(), 0.40 + 0.30 * rng.random()
        else:
            rar_b, fr_b, ft_b = 0.50 + 0.30 * rng.random(), 0.15 * rng.random(), 0.15 * rng.random()
        res_f = _extract_g8_feat_v51b(z_bg, c0_p, float(z_bg[c0_p]), rar_b, fr_b, ft_b, half_px=8)
        if res_f is not None:
            ref_cal_feats.append(res_f[0])
    g8_cal_model = _fit_g8_v51b(ref_cal_feats, pca_dim=8, knn_k=7, min_novelty_z=3.5)

    for ti in range(120):
        if ti < 40:
            tcls = "ISOLATED_LSF_LASER"
            zc = rng.normal(0.0, 0.9, len(w_p))
            z_pk = 9.5 + 0.25 * (ti % 8)
            zc += z_pk * np.exp(-0.5 * ((w_p - wc_p) / sig_p) ** 2)
            rar, fr, ft = 0.95, 0.0, 0.0
            z_val = float(zc[c0_p])
        elif ti < 80:
            tcls = "SHARED_PHOTOSPHERIC_PATCH"
            zc = rng.normal(0.0, 1.0, len(w_p))
            zc += 6.5 * np.exp(-0.5 * ((w_p - wc_p) / (2.1 * sig_p)) ** 2)
            rar, fr, ft = 0.38, 0.48, 0.10
            z_val = float(zc[c0_p])
        else:
            tcls = "TOPO_BLAZE_ARTIFACT"
            zc = rng.normal(0.0, 1.0, len(w_p))
            zc += 6.0 * np.exp(-0.5 * ((w_p - wc_p) / (2.5 * sig_p)) ** 2)
            rar, fr, ft = 0.28, 0.05, 0.62
            z_val = float(zc[c0_p])

        out_g8 = _eval_g8_v51b(g8_cal_model, w_p, zc, wc_p, z_val, rar, fr, ft)
        patch_cal_rows.append({
            "trial_id": f"G8P_{ti + 1:03d}", "trial_class": tcls,
            "novelty_z": round(float(out_g8["novelty_z"]), 3),
            "g8_pass": bool(out_g8["g8_pass"]), "expected_pass": tcls == "ISOLATED_LSF_LASER",
        })

    # 3. CALIBRATION_V51_RPCA_RARITY_180 (60 ISOLATED + 60 SHARED_PHOTOSPHERIC_LEAK + 60 TOPO_SKY_REPEAT)
    rpca_cal_rows: list[dict[str, Any]] = []
    block_n = 2048
    n_syn_stars = 16
    w_blk = 5500.0 + 0.03 * np.arange(block_n)
    teffs_cal = np.linspace(3200.0, 5800.0, n_syn_stars)
    basis_a = -0.22 * np.sin(w_blk / 6.8) ** 4
    basis_b = -0.16 * np.cos(w_blk / 10.5) ** 6
    sig_a_inj = 5530.0 / (60000.0 * FWHM_FACTOR)
    bervs_cal = np.linspace(-24.0, 24.0, n_syn_stars)
    sig_v_cal = C_KMS / (60000.0 * FWHM_FACTOR)

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
                "trial_id": f"RPCA_{len(rpca_cal_rows) + 1:03d}", "trial_class": cls,
                "wave_rest_a": round(wc, 3), "z_rpca": round(zv, 3),
                "f_rest": round(rar["f_rest"], 4), "f_topo": round(rar["f_topo"], 4),
                "rarity_score": round(rar["rarity_score"], 4), "g7_pass": bool(g7["g7_pass"]),
                "expected_pass": cls == "ISOLATED_LASER",
            })

    # 4. CALIBRATION_V51_AGNOSTIC_MULTISCALE_120 (4 scales x 2 kernels x 2 polarities)
    ag_cal_rows: list[dict[str, Any]] = []
    w_ag = 5600.0 + 0.025 * np.arange(4096)
    cfg_ag = get_inst_config("ESO_CORALIE")
    lsf_sig_a = 5660.0 / (float(cfg_ag["resolving_power"]) * FWHM_FACTOR)
    bervs_ag = np.linspace(-20.0, 20.0, 8)
    for idx_t in range(120):
        sc = (2.0, 4.0, 8.0, 14.0)[idx_t % 4]
        kern = "gaussian" if (idx_t // 4) % 2 == 0 else "boxcar_drift"
        pol = 1.0 if (idx_t // 8) % 2 == 0 else -1.0
        z_noise = rng.normal(0.0, 1.0, (8, len(w_ag)))
        res_s = 0.005 * z_noise[0]
        wc = 5640.0 + 1.1 * (idx_t % 15)
        sig_f = sc * lsf_sig_a
        if kern == "gaussian":
            norm_k = math.sqrt(max(1.0, math.sqrt(math.pi) * sig_f / 0.025))
            amp = 12.5 * 0.005 / norm_k
            prof = pol * amp * np.exp(-0.5 * ((w_ag - wc) / sig_f) ** 2)
        else:
            half_box = 0.5 * FWHM_FACTOR * sig_f
            n_in = max(1, int(round(2.0 * half_box / 0.025)))
            amp = 12.5 * 0.005 / math.sqrt(float(n_in))
            prof = np.where(np.abs(w_ag - wc) <= half_box, pol * amp, 0.0)
        res_s = res_s + prof
        z_noise[0] = res_s / 0.005
        survs, _ = scan_agnostic_multiscale_v50(w_ag, res_s, 0, z_noise, bervs_ag, cfg_ag)
        rec = any(abs(float(s["wave_rest_a"]) - wc) <= max(0.8, 2.0 * sc * lsf_sig_a) and s["polarity"] == ("+" if pol > 0 else "-") for s in survs)
        best_s = max([s for s in survs if abs(float(s["wave_rest_a"]) - wc) <= max(0.8, 2.0 * sc * lsf_sig_a)], key=lambda d: abs(d["z_multi"]), default=None)
        ag_cal_rows.append({
            "trial_id": f"AGN_{idx_t + 1:03d}", "scale_lsf": sc, "kernel": kern,
            "polarity": "+" if pol > 0 else "-", "inj_wave_a": round(wc, 3),
            "recovered": bool(rec), "z_multi": round(float(best_s["z_multi"]), 2) if best_s else 0.0,
            "rarity_score": round(float(best_s["rarity_score"]), 4) if best_s else 0.0,
        })

    # 5. CALIBRATION_V51_NIRSPEC_MOL_CCF_160 (80 injected molecules + 80 confounders on Archive P G395H trimmed segments)
    nir_cal_rows: list[dict[str, Any]] = []
    ref_n_star = "P330E" if "P330E" in nirspec_spectra else sorted(nirspec_spectra.keys())[0]
    p_segs_cal = nirspec_spectra[ref_n_star]["segments"]
    mols_n = list(NIRSPEC_MOL_TEMPLATES_UM.keys())
    confs_n = list(NATURAL_NIRSPEC_CONFOUNDERS_UM.keys())

    for ti in range(80):
        mol = mols_n[ti % 4]
        depth_inj = 0.025 + 0.01 * ((ti // 4) % 4)
        segs_s: list[tuple[np.ndarray, np.ndarray]] = []
        for ws_seg, _ in p_segs_cal:
            sed_seg = 1e-16 * (np.maximum(1.0, ws_seg) / 4.0) ** (-2.8)
            fac = np.ones_like(ws_seg)
            for comp in NIRSPEC_MOL_TEMPLATES_UM[mol]:
                fac -= depth_inj * comp["weight"] * np.exp(-0.5 * ((ws_seg - comp["mu_um"]) / comp["sigma_um"]) ** 2)
            segs_s.append((ws_seg, sed_seg * (fac + rng.normal(0.0, 0.004, len(ws_seg)))))
        out_n = _scan_nirspec_v51b(segs_s)
        m_info = out_n["molecules"].get(mol, {})
        nir_cal_rows.append({
            "trial_id": f"NIR_{len(nir_cal_rows) + 1:03d}", "trial_class": f"INJ_{mol}",
            "target_gas": mol, "depth_inj": depth_inj,
            "ccf_sigma": round(float(m_info.get("ccf_sigma_abs", 0.0)), 2),
            "passes_ccf": bool(m_info.get("passes_ccf", False)),
            "any_mol_detected": bool(out_n["any_detection"]), "expected_detection": True,
        })

    for ti in range(80):
        cname = confs_n[ti % 4]
        sign = -1.0
        amp_c = 0.05 + 0.015 * ((ti // 4) % 3)
        segs_s = []
        for ws_seg, _ in p_segs_cal:
            sed_seg = 1e-16 * (np.maximum(1.0, ws_seg) / 4.0) ** (-2.8)
            fac = np.ones_like(ws_seg)
            for comp in NATURAL_NIRSPEC_CONFOUNDERS_UM[cname]:
                fac += sign * amp_c * comp["weight"] * np.exp(-0.5 * ((ws_seg - comp["mu_um"]) / comp["sigma_um"]) ** 2)
            segs_s.append((ws_seg, sed_seg * (fac + rng.normal(0.0, 0.004, len(ws_seg)))))
        out_n = _scan_nirspec_v51b(segs_s)
        c_info = out_n["confounders"].get(cname, {})
        nir_cal_rows.append({
            "trial_id": f"NIR_{len(nir_cal_rows) + 1:03d}", "trial_class": f"CONFOUNDER_{cname}",
            "target_gas": cname, "depth_inj": amp_c,
            "ccf_sigma": round(float(c_info.get("physical_confounder_sigma", 0.0)), 2),
            "passes_ccf": bool(out_n["any_detection"]),
            "any_mol_detected": bool(out_n["any_detection"]), "expected_detection": False,
        })

    # 6. INJECTION_RECOVERY_540 & CALIBRATION_COMPLETENESS_BY_BAND (3 inst x 3 bands x 5 SNRs x 2 modes x 6 = 540)
    inj_bands = {
        "GEMINI_GRACES": [("R2_5320", 5320.5), ("R3_6328", 6328.2), ("R4_8521", 8521.1)],
        "ESO_CORALIE": [("L2_5320", 5320.5), ("L3_5800", 5800.0), ("L4_6328", 6328.2)],
        "CARMENES_VIS": [("M2_6328", 6328.2), ("M3_8082", 8082.0), ("M4_8800", 8800.0)],
    }
    snr_grid = (4.0, 6.0, 8.0, 12.0, 20.0)
    inj_rows: list[dict[str, Any]] = []
    comp_rows: list[dict[str, Any]] = []
    for inst in ("GEMINI_GRACES", "ESO_CORALIE", "CARMENES_VIS"):
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
                            cands, _, _ = scan_single_exposure_residual_lsf(wg, y, cfg, "T", flux_norm_for_f1=1.0 + y)
                            ok = any(check_channel_lsf_gate(c, "T", cfg) and abs(c["fitted_center_a"] - wc0) <= tol_a for c in cands)
                        else:
                            y0 = rng.normal(0.0, mad_noise * math.sqrt(2.0), len(wg)) + amp * prof
                            y1 = rng.normal(0.0, mad_noise * math.sqrt(2.0), len(wg)) + amp * prof
                            ymat = np.vstack([y0, y1])
                            _, _, pcands, _, _ = build_multi_epoch_rest_coadd_and_channel_p(wg, 1.0 + ymat, ymat, np.ones_like(wg), cfg)
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

    # 7. KEPLERIAN_TRACK_CALIBRATION_81 (3 inst x 3 Kp x 3 SNRs x 3 = 81)
    kep_rows: list[dict[str, Any]] = []
    for inst, w0 in (("GEMINI_GRACES", 6328.0), ("ESO_CORALIE", 5320.0), ("CARMENES_VIS", 8082.0)):
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

    # 8. DETECTOR_V51_G4G5_CALIBRATION_108 (3 inst x 3 classes x 12 = 108)
    g45_rows: list[dict[str, Any]] = []
    for inst, wc in (("GEMINI_GRACES", 6328.0), ("ESO_CORALIE", 5320.0), ("CARMENES_VIS", 8082.0)):
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

    # 9. COMB_V4_1_CALIBRATION_162 (3 inst x 3 classes x 18 = 162)
    comb_cal_rows: list[dict[str, Any]] = []
    comb_band_map = {
        "GEMINI_GRACES": ("GRACES_RED", 6150.0, 6175.0),
        "ESO_CORALIE": ("CORALIE_RED", 6000.0, 6025.0),
        "CARMENES_VIS": ("CARM_RED", 6320.0, 6340.0),
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
                h4, _ = scan_frequency_comb_v4(wg, y_r, sig_c, 1.0 + y_r, np.ones_like(wg), sky_m, y_t, sig_c, win_obj, [bname], cfg)
                h41, _ = scan_frequency_comb_v4_1(wg, y_r, sig_c, 1.0 + y_r, np.ones_like(wg), sky_m, y_t, sig_c, win_obj, [bname], cfg)
                comb_cal_rows.append({
                    "trial_id": f"CCAL_{len(comb_cal_rows) + 1:03d}", "instrument": inst, "trial_class": cls,
                    "tooth_snr_inj": snr_t, "comb_v4_hit": len(h4) > 0, "comb_v41_hit": len(h41) > 0,
                })

    tot_trials = (
        len(drift_cal_rows) + len(patch_cal_rows) + len(rpca_cal_rows) + len(ag_cal_rows)
        + len(nir_cal_rows) + len(inj_rows) + len(kep_rows) + len(g45_rows) + len(comb_cal_rows)
    )
    dr_rec = [r["detected"] for r in drift_cal_rows if r["trial_class"] == "DRIFTING_LASER"]
    dr_st = [not r["detected"] for r in drift_cal_rows if r["trial_class"] == "STATIONARY_LINE"]
    dr_tr = [not r["detected"] for r in drift_cal_rows if r["trial_class"] == "SINGLE_EPOCH_TRANSIENT"]
    p_iso = [r["g8_pass"] for r in patch_cal_rows if r["trial_class"] == "ISOLATED_LSF_LASER"]
    p_shr = [not r["g8_pass"] for r in patch_cal_rows if r["trial_class"] == "SHARED_PHOTOSPHERIC_PATCH"]
    p_top = [not r["g8_pass"] for r in patch_cal_rows if r["trial_class"] == "TOPO_BLAZE_ARTIFACT"]
    rp_iso = [r["g7_pass"] for r in rpca_cal_rows if r["trial_class"] == "ISOLATED_LASER"]
    rp_leak = [not r["g7_pass"] for r in rpca_cal_rows if r["trial_class"] == "SHARED_PHOTOSPHERIC_LEAK"]
    rp_topo = [not r["g7_pass"] for r in rpca_cal_rows if r["trial_class"] == "TOPO_SKY_REPEAT"]
    ag_ok = [r["recovered"] for r in ag_cal_rows]
    n_rec = [r["passes_ccf"] for r in nir_cal_rows if r["expected_detection"]]
    n_veto = [not r["any_mol_detected"] for r in nir_cal_rows if not r["expected_detection"]]
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
        "blind_drift_recovery": f"{sum(dr_rec)}/{len(dr_rec)} ({sum(dr_rec)/len(dr_rec):.4f})",
        "blind_drift_stationary_veto": f"{sum(dr_st)}/{len(dr_st)} ({sum(dr_st)/len(dr_st):.4f})",
        "blind_drift_transient_veto": f"{sum(dr_tr)}/{len(dr_tr)} ({sum(dr_tr)/len(dr_tr):.4f})",
        "g8_patch_isolated_laser_pass": f"{sum(p_iso)}/{len(p_iso)} ({sum(p_iso)/len(p_iso):.4f})",
        "g8_patch_shared_suppression": f"{sum(p_shr)}/{len(p_shr)} ({sum(p_shr)/len(p_shr):.4f})",
        "g8_patch_topo_suppression": f"{sum(p_top)}/{len(p_top)} ({sum(p_top)/len(p_top):.4f})",
        "rpca_isolated_laser_recovery": f"{sum(rp_iso)}/{len(rp_iso)} ({sum(rp_iso)/len(rp_iso):.4f})",
        "rpca_shared_leak_suppression": f"{sum(rp_leak)}/{len(rp_leak)} ({sum(rp_leak)/len(rp_leak):.4f})",
        "rpca_topo_repeat_suppression": f"{sum(rp_topo)}/{len(rp_topo)} ({sum(rp_topo)/len(rp_topo):.4f})",
        "agnostic_multiscale_recovery": f"{sum(ag_ok)}/{len(ag_ok)} ({sum(ag_ok)/len(ag_ok):.4f})",
        "nirspec_mol_ccf_recovery": f"{sum(n_rec)}/{len(n_rec)} ({sum(n_rec)/len(n_rec):.4f})",
        "nirspec_confounder_veto": f"{sum(n_veto)}/{len(n_veto)} ({sum(n_veto)/len(n_veto):.4f})",
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
        "drift_cal_rows": drift_cal_rows,
        "patch_cal_rows": patch_cal_rows,
        "rpca_cal_rows": rpca_cal_rows,
        "ag_cal_rows": ag_cal_rows,
        "nir_cal_rows": nir_cal_rows,
        "inj_rows": inj_rows,
        "comp_rows": comp_rows,
        "kep_rows": kep_rows,
        "g45_rows": g45_rows,
        "comb_cal_rows": comb_cal_rows,
        "summary": cal_sum,
    }


# ---------------------------------------------------------------------------
# Stage B: Full Scientific Analysis, V5.1 Engines & 350-Star Synthesis
# ---------------------------------------------------------------------------

def run_stage_b(bundle: dict[str, Any], out_dir: Path, archives_dir: Path = ARCHIVES_DEFAULT) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    snap_v50 = json.loads((WS / "PRIOR_V5_0_PHASES_SNAPSHOT.json").read_text(encoding="utf-8"))
    orb_doc = json.loads((WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))

    exposures_raw: list[dict[str, Any]] = bundle["exposures"]
    assert len(exposures_raw) == 30

    exps_by_star: dict[str, list[dict[str, Any]]] = defaultdict(list)
    exps_by_inst: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in exposures_raw:
        exps_by_star[e["star"]].append(e)
        exps_by_inst[e["instrument"]].append(e)

    print(f"Stage B ({out_dir}): unpacking & measuring RVs for 30 D093 exposures...", flush=True)
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

    # Re-grid per instrument onto uniform rest-frame grid + build kNN stellar templates
    rest_grid_by_inst: dict[str, np.ndarray] = {}
    for inst in ("GEMINI_GRACES", "ESO_CORALIE", "CARMENES_VIS"):
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

    print("  Building kNN stellar templates across GRACES/CORALIE/CARMENES_VIS...", flush=True)
    star_templates: dict[str, np.ndarray] = {}
    for inst in ("GEMINI_GRACES", "ESO_CORALIE", "CARMENES_VIS"):
        cfg = get_inst_config(inst)
        tpls, _ = construct_knn_stellar_templates(star_meta_by_inst[inst], star_norm_coadds[inst], cfg)
        star_templates.update(tpls)

    searched_by_inst: dict[str, dict[str, int]] = {
        inst: {"T": 0, "P": 0, "T_DIFF": 0, "K_PLANET": 0, "COMB_CONFIGS": 0, "DRIFT_EVALS": 0}
        for inst in ("GEMINI_GRACES", "ESO_CORALIE", "CARMENES_VIS")
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

    # Orbital Campaigns (#110-#117)
    print("  Scanning 8 orbital campaigns (#110-#117)...", flush=True)
    orb_rows: list[dict[str, Any]] = []
    orb_cand_counts: dict[str, dict[str, int]] = {}
    for st, camp in sorted(orb_doc["campaigns"].items(), key=lambda kv: kv[1]["campaign_index"]):
        ctx = star_ctx[st]
        inst = ctx["instrument"]
        cfg = get_inst_config(inst, float(ctx["exps"][0]["resolving_power"]))
        rg = ctx["rest_grid"]
        exps = ctx["exps"]
        in_i = [i for i, e in enumerate(exps) if e["phase_window"] == "IN_WINDOW"]
        out_i = [i for i, e in enumerate(exps) if e["phase_window"] == "OUT_OF_WINDOW"]
        if not in_i:
            in_i = [0]
        if not out_i:
            out_i = [i for i in range(len(exps)) if i not in in_i] or [len(exps) - 1]
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

        orb_cand_counts[st] = {}
        orb_rows.append({
            "campaign_number": camp["campaign_index"], "star": st, "common_name": camp["common_name"],
            "instrument": inst, "role": camp["role"], "planet_name": camp["planet_name"],
            "n_planets_in_system": camp["n_planets_in_system"], "min_ppo_align_score": camp["min_ppo_align_score"],
            "orbper_days": camp["orb_per_days"], "kp_kms": camp["kp_kms"],
            "orbital_dv_span_kms": camp["orbital_dv_span_kms"],
            "n_in_window": len(in_i), "n_out_of_window": len(out_i),
            "tdiff_lsf_cands": n_td, "kplanet_lsf_cands": n_kp,
            "qualified_v50_tdiff": 0, "qualified_v50_kplanet": 0,
            "qualified_v51_tdiff": 0, "qualified_v51_kplanet": 0, "verified_eti": 0,
        })

    # Clean-Room Archive R ESO_FEROS 10-Star Optical Manifold Peers for Augmented RPCA
    print("  Loading Archive R ESO_FEROS (10 stars / 20 exps) for optical RPCA manifold augmentation...", flush=True)
    feros_raw = _load_archive_r_feros_peers(archives_dir)
    feros_by_st: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fe in feros_raw:
        feros_by_st[fe["star"]].append(fe)
    feros_unpacked: dict[str, dict[str, Any]] = {}
    feros_meta: dict[str, dict[str, Any]] = {}
    cfg_fer = get_inst_config("ESO_FEROS")
    for fst, fexps in sorted(feros_by_st.items()):
        rvs_f, bervs_f, f_unps = [], [], []
        for fe in fexps:
            unp_f = _unpack_exposure_spectrum(fe, cfg_fer)
            rm_f, _, _ = measure_exposure_stellar_rv(unp_f["w_bary"], unp_f["fn"], float(fe["prior_rv_kms"]), cfg_fer)
            rvs_f.append(float(rm_f["empirical_rv_kms"]))
            bervs_f.append(float(fe["berv_kms"]))
            f_unps.append((float(rm_f["empirical_rv_kms"]), unp_f))
        feros_unpacked[fst] = {"exps": f_unps}
        feros_meta[fst] = {
            "teff_k": float(fexps[0]["teff_k"]),
            "v_obs_to_rest": float(exact_median_1d(np.asarray(bervs_f))) - float(exact_median_1d(np.asarray(rvs_f))),
        }

    # Build Joint RPCA+LOSO Manifolds (GRACES 14-star, CORALIE 15-star, CARMENES_VIS 16-star)
    print("  Running V5.1 Masked Inexact-ALM RPCA + LOSO across augmented optical manifolds...", flush=True)
    rpca_by_inst: dict[str, dict[str, Any]] = {}
    for inst in ("GEMINI_GRACES", "ESO_CORALIE", "CARMENES_VIS"):
        rg = rest_grid_by_inst[inst]
        coadds, teffs_m, vsh_m = {}, {}, {}
        for st in sorted(star_norm_coadds[inst].keys()):
            coadds[f"D093_{st}"] = star_norm_coadds[inst][st]
            teffs_m[f"D093_{st}"] = float(star_ctx[st]["exps"][0]["teff_k"])
            vsh_m[f"D093_{st}"] = star_ctx[st]["berv_med"] - star_ctx[st]["rv_med"]
        for fst, fobj in sorted(feros_unpacked.items()):
            mat_f = np.full((len(fobj["exps"]), len(rg)), np.nan, dtype=np.float64)
            for ie, (rv_f, unp_f) in enumerate(fobj["exps"]):
                mat_f[ie] = _resample_gap_safe(unp_f["w_bary"] / (1.0 + rv_f / C_KMS), unp_f["fn"], rg, max_gap_a=2.5)
            with warnings.catch_warnings(), np.errstate(all="ignore"):
                warnings.simplefilter("ignore", RuntimeWarning)
                coadds[f"REF92_{fst}"] = np.nanmedian(mat_f, axis=0)
            teffs_m[f"REF92_{fst}"] = feros_meta[fst]["teff_k"]
            vsh_m[f"REF92_{fst}"] = feros_meta[fst]["v_obs_to_rest"]

        keys = sorted(coadds.keys())
        mat = np.vstack([coadds[k] for k in keys])
        teffs_arr = np.asarray([teffs_m[k] for k in keys], dtype=np.float64)
        vsh_arr = np.asarray([vsh_m[k] for k in keys], dtype=np.float64)
        rp_out = run_cohort_rpca_v50(rg, mat, teffs=teffs_arr, block_len=2048, overlap=128, loso_rank=6)
        rp_out["stars"] = keys
        rp_out["star_to_idx"] = {k: i for i, k in enumerate(keys)}
        rp_out["v_shifts"] = vsh_arr
        rpca_by_inst[inst] = rp_out
        print(f"    RPCA [{inst}]: shape={mat.shape}, rank=6 done.", flush=True)

    # Fit Gate G8_V51b Standardized Non-Linear PCA-Whitened k-NN Patch Novelty Models per Instrument Cohort
    print("  Fitting Gate G8_V51b standardized k=7-NN patch novelty manifolds...", flush=True)
    g8_models: dict[str, dict[str, Any]] = {}
    for inst in ("GEMINI_GRACES", "ESO_CORALIE", "CARMENES_VIS"):
        rp_b = rpca_by_inst[inst]
        w_ax = rp_b["wave_rest"]
        feats: list[np.ndarray] = []
        d93_keys = [k for k in rp_b["stars"] if k.startswith("D093_")]
        for rk in d93_keys:
            si = rp_b["star_to_idx"][rk]
            zv = rp_b["z_rpca"][si]
            fin_idx = np.flatnonzero(np.isfinite(zv) & (np.arange(len(zv)) >= 25) & (np.arange(len(zv)) < len(zv) - 25))
            if len(fin_idx) == 0:
                continue
            stride = max(1, len(fin_idx) // 65)
            for idx_p in fin_idx[::stride][:65]:
                sub_z = zv[idx_p - 8 : idx_p + 9]
                if not np.all(np.isfinite(sub_z)):
                    continue
                sig_v = float(get_inst_config(inst)["sigma_v_kms"])
                rar_bg = compute_spectral_rarity_score(w_ax, rp_b["z_rpca"], rp_b["v_shifts"], si, float(w_ax[idx_p]), sig_v, polarity=1.0)
                res_f = _extract_g8_feat_v51b(
                    zv, int(idx_p), float(zv[idx_p]),
                    rar_bg["rarity_score"], rar_bg["f_rest"], rar_bg["f_topo"], half_px=8
                )
                if res_f is not None:
                    feats.append(res_f[0])
        g8_models[inst] = _fit_g8_v51b(feats, pca_dim=8, knn_k=7, min_novelty_z=3.5)
        print(f"    G8_V51b [{inst}]: n_ref={g8_models[inst]['n_ref']} ready={g8_models[inst]['ready']}", flush=True)

    def _eval_g7_g8(inst_k: str, row_key: str, wr_a: float, sigma_v: float) -> dict[str, Any]:
        rp_b = rpca_by_inst[inst_k]
        w_ax = rp_b["wave_rest"]
        si = rp_b["star_to_idx"][row_key]
        k = int(np.argmin(np.abs(w_ax - wr_a)))
        lo, hi = max(0, k - 2), min(len(w_ax), k + 3)
        zw = rp_b["z_rpca"][si, lo:hi]
        fin = np.isfinite(zw)
        z_pk = float(np.max(zw[fin])) if np.any(fin) else math.nan
        if not math.isfinite(z_pk):
            return {"g7_pass": False, "g8_pass": False, "z_rpca": math.nan, "rarity_score": 0.0, "f_rest": 1.0, "f_topo": 0.0, "novelty_z": 0.0, "reason": "G7_UNCOVERED"}
        rar = compute_spectral_rarity_score(w_ax, rp_b["z_rpca"], rp_b["v_shifts"], si, wr_a, sigma_v, polarity=1.0)
        g7 = evaluate_gate_g7_v50(z_pk, rar["rarity_score"])
        g8 = _eval_g8_v51b(g8_models[inst_k], w_ax, rp_b["z_rpca"][si], wr_a, z_pk, rar["rarity_score"], rar["f_rest"], rar["f_topo"])
        return {
            **g7,
            "f_rest": rar["f_rest"], "f_topo": rar["f_topo"],
            "g8_pass": bool(g8["g8_pass"]), "novelty_z": float(g8["novelty_z"]), "g8_reason": g8["reason"],
        }

    # Gate Vetting G2..G6 + G7_V50 + G8_V51 on D093 raw candidates
    print(f"  Vetting {len(raw_cands)} D093 candidates through G2..G6 + G7_V50 + G8_V51...", flush=True)
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

        g78 = _eval_g7_g8(inst, f"D093_{st}", wr, float(cfg["sigma_v_kms"]))
        qual_v50 = bool(qual_v42 and g78["g7_pass"])
        qual_v51 = bool(qual_v50 and g78["g8_pass"])

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
        elif not g78["g7_pass"]:
            disp = f"VETO_G7_{g78['reason']}"
        elif not g78["g8_pass"]:
            disp = f"VETO_G8_{g78['g8_reason']}"
        else:
            disp = "AUTO_QUALIFIED_V5_1"

        lrow = {
            "candidate_id": f"D093_C{idx_c:05d}", "instrument": inst, "channel": rc["channel"], "role": rc["role"],
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
            "z_rpca": round(float(g78["z_rpca"]), 3) if math.isfinite(float(g78["z_rpca"])) else "",
            "rarity_score": round(float(g78["rarity_score"]), 4),
            "f_rest": round(float(g78["f_rest"]), 4), "f_topo": round(float(g78["f_topo"]), 4),
            "g7_pass": bool(g78["g7_pass"]), "qualified_v50_laser": qual_v50,
            "novelty_z": round(float(g78["novelty_z"]), 4), "g8_pass": bool(g78["g8_pass"]),
            "qualified_v51_laser": qual_v51, "final_disposition": disp,
        }
        ledger_rows.append(lrow)

        if st in orb_cand_counts:
            if rc["channel"] == "T_DIFF":
                if qual_v50: orb_cand_counts[st]["tdiff_v50"] = orb_cand_counts[st].get("tdiff_v50", 0) + 1
                if qual_v51: orb_cand_counts[st]["tdiff_v51"] = orb_cand_counts[st].get("tdiff_v51", 0) + 1
            elif rc["channel"] == "K_PLANET":
                if qual_v50: orb_cand_counts[st]["kplanet_v50"] = orb_cand_counts[st].get("kplanet_v50", 0) + 1
                if qual_v51: orb_cand_counts[st]["kplanet_v51"] = orb_cand_counts[st].get("kplanet_v51", 0) + 1

        if qual_v51:
            near_sky = min(GROUND_AIRGLOW_AND_TELLURIC_A, key=lambda x: abs(float(lrow["topo_wave_a"]) - float(x["wave_A"])))
            near_ch = min(STELLAR_OPT_NIR_EMISSION_A, key=lambda x: abs(wr - float(x["wave_A"])))
            sky_d = abs(float(lrow["topo_wave_a"]) - float(near_sky["wave_A"]))
            ch_d = abs(wr - float(near_ch["wave_A"]))
            if sky_d <= 5.0 or wr >= 6850.0:
                fcls = "TELLURIC_OR_O2_H2O_BAND"
            elif ch_d <= 5.0:
                fcls = "CHROMOSPHERIC_LINE_CORE_OR_WING"
            elif float(e["teff_k"]) < 4000.0:
                fcls = "M_DWARF_MOLECULAR_OR_FLARE_RESIDUAL"
            elif rc["channel"] == "T":
                fcls = "SINGLE_EPOCH_ARCHIVAL_RESIDUAL"
            else:
                fcls = "PHOTOSPHERIC_ORDER_MERGE_RESIDUAL"
            forensic_cls_cnt[fcls] += 1
            forensic_recs.append({**lrow, "forensic_class": fcls, "sky_sep_a": round(sky_d, 2), "chromo_sep_a": round(ch_d, 2), "verified_eti": False})

    for orow in orb_rows:
        oc = orb_cand_counts.get(orow["star"], {})
        orow["qualified_v50_tdiff"] = oc.get("tdiff_v50", 0)
        orow["qualified_v50_kplanet"] = oc.get("kplanet_v50", 0)
        orow["qualified_v51_tdiff"] = oc.get("tdiff_v51", 0)
        orow["qualified_v51_kplanet"] = oc.get("kplanet_v51", 0)

    # Engine 6 (V5.1): Blind Linear Drift-Rate (v_0, v_dot) Search across 15 Multi-Epoch Stars
    print("  Running V5.1 Blind Linear Drift-Rate (DRIFT_V51) scan across 15 multi-epoch stars...", flush=True)
    drift_rows: list[dict[str, Any]] = []
    drift_evals_tot = 0
    for st in sorted(star_ctx.keys()):
        ctx = star_ctx[st]
        inst = ctx["instrument"]
        exps = ctx["exps"]
        if len(exps) < 2:
            continue
        e1, e2 = exps[0], exps[-1]
        dt_d = abs(float(e2["mjd_obs"]) - float(e1["mjd_obs"]))
        cfg = get_inst_config(inst, float(e1["resolving_power"]))
        rg = ctx["rest_grid"]
        rp_b = rpca_by_inst[inst]
        si = rp_b["star_to_idx"][f"D093_{st}"]
        mad1 = max(0.002, exact_mad_1d(ctx["resids_mat"][0][np.isfinite(ctx["resids_mat"][0])]))
        mad2 = max(0.002, exact_mad_1d(ctx["resids_mat"][-1][np.isfinite(ctx["resids_mat"][-1])]))
        z1 = ctx["resids_mat"][0] / mad1
        z2 = ctx["resids_mat"][-1] / mad2
        c_dr, stat_dr = scan_blind_drift_dedoppler_v51(
            rg, z1, z2, dt_d, float(e1["berv_kms"]), float(e2["berv_kms"]),
            cfg, star=st, star_idx=si, z_rpca_mat=rp_b["z_rpca"], bervs_cohort=rp_b["v_shifts"],
        )
        searched_by_inst[inst]["DRIFT_EVALS"] += int(stat_dr["n_evals"])
        drift_evals_tot += int(stat_dr["n_evals"])
        for dc in c_dr:
            wr1 = float(dc["wave1_rest_a"])
            g8_d = _eval_g8_v51b(g8_models[inst], rg, np.where(np.isfinite(z1), z1, 0.0), wr1, float(dc["z1"]), float(dc["rarity1"]), 0.0, 0.0)
            near_sky = min(GROUND_AIRGLOW_AND_TELLURIC_A, key=lambda x: abs(wr1 - float(x["wave_A"])))
            near_ch = min(STELLAR_OPT_NIR_EMISSION_A, key=lambda x: abs(wr1 - float(x["wave_A"])))
            drift_rows.append({
                "drift_id": f"D093_DRF_{len(drift_rows) + 1:04d}",
                "instrument": inst, "role": e1["role"], "teff_k": e1["teff_k"],
                **dc,
                "novelty_z": round(float(g8_d["novelty_z"]), 3),
                "g8_pass": bool(g8_d["g8_pass"]),
                "nearest_sky_sep_a": round(abs(wr1 - float(near_sky["wave_A"])), 2),
                "nearest_chromo_sep_a": round(abs(wr1 - float(near_ch["wave_A"])), 2),
            })

    # Dual-Polarity Agnostic Multi-Scale Matched Filter across all 15 D093 stars
    print("  Running V5.1 Agnostic Multi-Scale Matched Filter across 15 D093 stars...", flush=True)
    ag_survivor_rows: list[dict[str, Any]] = []
    ag_evals_tot = 0
    for st in sorted(star_ctx.keys()):
        ctx = star_ctx[st]
        inst = ctx["instrument"]
        cfg = get_inst_config(inst, float(ctx["exps"][0]["resolving_power"]))
        rp_b = rpca_by_inst[inst]
        si = rp_b["star_to_idx"][f"D093_{st}"]
        survs, nev = scan_agnostic_multiscale_v50(rp_b["wave_rest"], rp_b["S_loso"][si], si, rp_b["z_rpca"], rp_b["v_shifts"], cfg)
        ag_evals_tot += nev
        for pk in survs:
            near_sky = min(GROUND_AIRGLOW_AND_TELLURIC_A, key=lambda x: abs(float(pk["wave_rest_a"]) - float(x["wave_A"])))
            near_ch = min(STELLAR_OPT_NIR_EMISSION_A, key=lambda x: abs(float(pk["wave_rest_a"]) - float(x["wave_A"])))
            ag_survivor_rows.append({
                "survivor_id": f"D093_AGN_{len(ag_survivor_rows) + 1:04d}",
                "star": st, "instrument": inst, "role": ctx["exps"][0]["role"], "science_track": ctx["exps"][0]["science_track"],
                "teff_k": ctx["exps"][0]["teff_k"],
                "wave_rest_a": round(float(pk["wave_rest_a"]), 3), "z_multi": round(float(pk["z_multi"]), 3),
                "polarity": pk["polarity"], "scale_lsf": pk["scale_lsf"], "kernel": pk["kernel"],
                "fwhm_a": round(float(pk["fwhm_a"]), 3), "rarity_score": round(float(pk["rarity_score"]), 4),
                "f_rest": round(float(pk["f_rest"]), 4), "f_topo": round(float(pk["f_topo"]), 4),
                "nearest_sky_name": near_sky["name"], "nearest_sky_sep_a": round(abs(float(pk["wave_rest_a"]) - float(near_sky["wave_A"])), 2),
                "nearest_chromo_name": near_ch["name"], "nearest_chromo_sep_a": round(abs(float(pk["wave_rest_a"]) - float(near_ch["wave_A"])), 2),
            })

    # Retroactive Northern D088 (Archive N) V5.1 Regression across all 4,727 G1-passing records (20 V3.9 qualified)
    print("  Running Retroactive Northern D088 (4,727 G1 / 20 V3.9) V5.1 regression from Archive N...", flush=True)
    rcb88, sparse88, led88 = _load_archive_n_d088(archives_dir)
    by_grp_rest88: dict[str, list[tuple[str, float]]] = defaultdict(list)
    by_grp_topo88: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for br in rcb88:
        g = br["atlas_group"]
        wr8 = float(br["seed_wave_a"]) / (1.0 + float(br["v_star_kms"]) / C_KMS)
        wt8 = float(br["seed_wave_a"]) / (1.0 + float(br["berv_kms"]) / C_KMS)
        by_grp_rest88[g].append((br["star"], wr8))
        by_grp_topo88[g].append((br["star"], wt8))
    for g, items in sparse88.items():
        for it in items:
            by_grp_topo88[g].append((it["star"], float(it["topo_wave_a"])))
    grp_r_arr = {g: (np.array([x[1] for x in v]), np.array([x[0] for x in v])) for g, v in by_grp_rest88.items()}
    grp_t_arr = {g: (np.array([x[1] for x in v]), np.array([x[0] for x in v])) for g, v in by_grp_topo88.items()}

    bg88: dict[str, list[np.ndarray]] = {g: [] for g in grp_r_arr}
    for br in rcb88:
        g = br["atlas_group"]
        if len(bg88[g]) >= 400:
            continue
        wv = np.asarray(br["wave_win"], dtype=np.float64)
        yv = np.asarray(br["y_primary_win"], dtype=np.float64)
        nw = len(yv)
        if nw < 101:
            continue
        hw = nw // 3
        mad = max(0.002, exact_mad_1d(np.concatenate([yv[:hw], yv[-hw:]])))
        zv = yv / mad
        for ci in (20, 40, nw - 41, nw - 21):
            res_f88 = _extract_g8_feat_v51b(zv, ci, float(zv[ci]), 0.45, 0.25, 0.15, half_px=8)
            if res_f88 is not None:
                bg88[g].append(res_f88[0])
    g8_88 = {g: _fit_g8_v51b(feats, pca_dim=8, knn_k=7, min_novelty_z=3.5) for g, feats in bg88.items()}

    retro88_rows: list[dict[str, Any]] = []
    for lr, br in zip(led88, rcb88):
        g = br["atlas_group"]
        wv = np.asarray(br["wave_win"], dtype=np.float64)
        yv = np.asarray(br["y_primary_win"], dtype=np.float64)
        nw = len(yv)
        hw = max(20, nw // 3)
        mad = max(0.002, exact_mad_1d(np.concatenate([yv[:hw], yv[-hw:]])))
        zv = yv / mad
        c = nw // 2
        z_pk = float(np.max(zv[c - 3 : c + 4]))
        wr8 = float(br["seed_wave_a"]) / (1.0 + float(br["v_star_kms"]) / C_KMS)
        wt8 = float(br["seed_wave_a"]) / (1.0 + float(br["berv_kms"]) / C_KMS)
        tol_a = max(0.12, wr8 * (4.0 * C_KMS / (float(br["resolving_power"]) * FWHM_FACTOR) / C_KMS))
        arr_r, arr_sr = grp_r_arr[g]
        arr_t, arr_st = grp_t_arr[g]
        f_rest = len(set(arr_sr[(np.abs(arr_r - wr8) <= tol_a) & (arr_sr != br["star"])])) / max(1, len(set(arr_sr)) - 1)
        f_topo = len(set(arr_st[(np.abs(arr_t - wt8) <= tol_a * 1.5) & (arr_st != br["star"])])) / max(1, len(set(arr_st)) - 1)
        rarity = max(0.0, 1.0 - max(f_rest, f_topo))
        g7 = evaluate_gate_g7_v50(z_pk, rarity)
        g8 = _eval_g8_v51b(g8_88[g], wv, zv, float(br["seed_wave_a"]), z_pk, rarity, f_rest, f_topo)
        v39 = lr["qualified_v39_laser"] == "True"
        v50_p = bool(v39 and g7["g7_pass"])
        v51_p = bool(v50_p and g8["g8_pass"])
        retro88_rows.append({
            "candidate_id": lr["candidate_id"], "instrument": g, "channel": lr["channel"],
            "role": lr["role"], "star": lr["star"], "stellar_rest_wave_a": lr["stellar_rest_wave_a"],
            "qualified_v39_laser": v39,
            "z_rpca": round(z_pk, 3), "f_rest": round(f_rest, 4), "f_topo": round(f_topo, 4),
            "rarity_score": round(rarity, 4), "g7_pass": bool(g7["g7_pass"]),
            "novelty_z": round(float(g8["novelty_z"]), 3), "g8_pass": bool(g8["g8_pass"]),
            "qualified_v50_retro": v50_p, "qualified_v51_retro": v51_p,
        })

    # Engine 9 (V5.1): Retroactive D090 JWST NIRSpec G395H (2.86-5.18 um) Molecular CCF (11 targets x 4 = 44 cells)
    print("  Running V5.1 JWST NIRSpec G395H Molecular & Isotopologue CCF across 11 Archive P targets...", flush=True)
    nir_spectra = _load_archive_p_nirspec_g395h(archives_dir)
    nir_rows: list[dict[str, Any]] = []
    for st_n, ns in sorted(nir_spectra.items()):
        nscan = _scan_nirspec_v51b(ns["segments"])
        max_conf = float(nscan["max_confounder_sigma"])
        for mol in NIRSPEC_MOL_TEMPLATES_UM:
            mres = nscan["molecules"][mol]
            ccf_s = float(mres["ccf_sigma_abs"])
            passes = bool(mres["passes_ccf"])
            nir_rows.append({
                "star": st_n, "common_name": ns["common_name"], "role": ns["role"],
                "dist_pc": ns["dist_pc"], "teff_k": ns["teff_k"], "n_exposures": ns["n_exposures"],
                "molecule": mol, "covered": bool(mres["covered"]),
                "depth": round(float(mres["depth"]), 5), "ccf_sigma_abs": round(ccf_s, 3),
                "max_confounder_sigma": round(max_conf, 3),
                "delta_min_5sigma": round(float(mres["delta_min_5sigma"]), 5) if math.isfinite(float(mres["delta_min_5sigma"])) else "",
                "ppm_equiv_10pct_ref": round(float(mres["ppm_equiv_10pct_ref"]), 4) if math.isfinite(float(mres["ppm_equiv_10pct_ref"])) else "",
                "passes_ccf": passes,
            })

    # Geometric Synchronization Tracks Summary (15 D093 stars)
    geom_rows: list[dict[str, Any]] = []
    camp_map = orb_doc["campaigns"]
    v50_cnt_by_star = Counter(l["star"] for l in ledger_rows if l["qualified_v50_laser"])
    v51_cnt_by_star = Counter(l["star"] for l in ledger_rows if l["qualified_v51_laser"])
    drift_cnt_by_star = Counter(d["star"] for d in drift_rows)
    ag_cnt_by_star = Counter(a["star"] for a in ag_survivor_rows)

    for st in sorted(exps_by_star.keys()):
        exps = exps_by_star[st]
        e0 = exps[0]
        cm = camp_map.get(st)
        best_sync = min(
            [compute_multievent_sync_v51(float(e0["s_ra"]), float(e0["s_dec"]), float(e0["dist_pc"]), float(x["mjd_obs"])) for x in exps],
            key=lambda s: s["min_abs_ellipsoid_dt_days"],
        )
        sn87_min = min(abs(float(x["sn1987a_dt_days"])) for x in exps)
        gw17_min = min(abs(float(x["gw170817_dt_days"])) for x in exps)
        sn23_min = min(abs(float(x["sn2023ixf_dt_days"])) for x in exps)
        geom_rows.append({
            "star": st, "common_name": e0["common_name"], "instrument": e0["instrument"],
            "role": e0["role"], "science_track": e0["science_track"], "dist_pc": e0["dist_pc"],
            "within_10pc": e0["within_10pc"], "ecliptic_lat_deg": e0["ecliptic_lat_deg"],
            "etz_qualified": abs(float(e0["ecliptic_lat_deg"])) <= 0.264,
            "nearest_event": best_sync["nearest_event"],
            "min_abs_ellipsoid_dt_days": round(best_sync["min_abs_ellipsoid_dt_days"], 3),
            "min_abs_sn1987a_dt_days": round(sn87_min, 3),
            "min_abs_gw170817_dt_days": round(gw17_min, 3),
            "min_abs_sn2023ixf_dt_days": round(sn23_min, 3),
            "ellipsoid_qualified": min(sn87_min, gw17_min, sn23_min) <= 180.0,
            "min_ppo_align_score": cm["min_ppo_align_score"] if cm else round(min(float(x["ppo_align_score"]) for x in exps), 5),
            "orbital_dv_span_kms": cm["orbital_dv_span_kms"] if cm else 0.0,
            "v50_qualified": v50_cnt_by_star[st], "v51_qualified": v51_cnt_by_star[st],
            "drift_v51_candidates": drift_cnt_by_star[st], "agnostic_survivors": ag_cnt_by_star[st],
        })

    # COMB_V4 vs COMB_V4_1 across 15 D093 stars + Unified 401-Stack All-Sky Catalog
    print("  Scanning COMB_V4 vs COMB_V4_1 across 15 D093 stars (All-Sky 401 stacks)...", flush=True)
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
    for st in sorted(exps_by_star.keys()):
        exps = exps_by_star[st]
        inst = exps[0]["instrument"]
        n_v4, hv41, n_cfg = comb_results_by_star[st]
        searched_by_inst[inst]["COMB_CONFIGS"] += n_cfg
        comb_v4_tot += n_v4
        comb_v41_tot += len(hv41)
        comb_star_rows.append({"phase_id": "D093", "instrument": inst, "star": st, "role": exps[0]["role"], "teff_k": exps[0]["teff_k"], "n_exposures": len(exps), "comb_v4_candidates": n_v4, "comb_v41_candidates": len(hv41), "searched_configs": n_cfg, "verified_eti_combs": 0})
        for ci, h in enumerate(hv41, 1):
            comb_cand_rows.append({"comb_id": f"D093_COMB_{st}_{ci}", "instrument": inst, "star": st, "role": exps[0]["role"], "band": h["band"], "dnu_ghz": h["dnu_ghz"], "nu0_ghz": h["nu0_ghz"], "wave0_a": h["wave0_a"], "wave_end_a": h["wave_end_a"], "s_comb": h["s_comb"], "topo_anti_ratio": h["topo_anti_ratio"], "n_qualifying_teeth": h["n_qualifying_teeth"], "off_tooth_crowding": h["off_tooth_crowding"], "intertooth_ratio": h["intertooth_ratio"]})

    allsky_comb_rows = list(snap_v50["allsky_comb_unified_d079_d092"]) + [
        {k: r[k] for k in snap_v50["allsky_comb_unified_d079_d092"][0].keys()} for r in comb_star_rows
    ]
    allsky_comb_cands = list(snap_v50["allsky_comb_candidates_d079_d092"]) + [
        {"allsky_comb_id": c["comb_id"], "band": c["band"], "dnu_ghz": c["dnu_ghz"], "instrument": c["instrument"], "intertooth_ratio": c["intertooth_ratio"], "n_qualifying_teeth": c["n_qualifying_teeth"], "nu0_ghz": c["nu0_ghz"], "off_tooth_crowding": c["off_tooth_crowding"], "phase_id": "D093", "role": c["role"], "s_comb": c["s_comb"], "star": c["star"], "topo_anti_ratio": c["topo_anti_ratio"], "wave0_a": c["wave0_a"], "wave_end_a": c["wave_end_a"]}
        for c in comb_cand_rows
    ]

    # Run all 1,591 synthetic V5.1 calibrations across 9 suites
    print("  Running 1,591 synthetic V5.1 calibrations across 9 suites...", flush=True)
    cal = _run_v51_calibrations(star_ctx, g8_models, nir_spectra)
    cal_sum = cal["summary"]

    # 10 m Optical EIRP Upper Limits across all 15 D093 stars (60 cells)
    print("  Computing 60 star-band 10 m EIRP upper limits (Gaia-G Planck CGS)...", flush=True)
    ul_rows: list[dict[str, Any]] = []
    star_ul_best: dict[str, dict[str, Any]] = {}
    star_band_map: dict[str, dict[str, float]] = defaultdict(dict)
    for st in sorted(exps_by_star.keys()):
        exps = exps_by_star[st]
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

    # Unified 350-Star Synthesis, 153 <10 pc, 37 Bridges (631 cells), and Multi-Event 350-Star Ellipsoid Catalog
    print("  Assembling 350-star unified V5.1 synthesis & multi-event ellipsoid catalog...", flush=True)
    bridge_rows: list[dict[str, Any]] = list(snap_v50["d092_bridge_37star_rows"])
    u335_base = snap_v50["unified_335star_rows"]
    U350_COLS = list(u335_base[0].keys()) + [
        "n_exposures_graces", "min_graces_10m_kw",
        "n_exposures_coralie", "min_coralie_10m_kw",
        "n_exposures_carmenes_v51", "min_carmenes_v51_10m_kw",
    ]
    u_map: dict[str, dict[str, Any]] = {}
    for r in u335_base:
        nr = {k: r.get(k, "") for k in U350_COLS}
        for c in ("n_exposures_graces", "n_exposures_coralie", "n_exposures_carmenes_v51"):
            nr[c] = "0"
        for c in ("min_graces_10m_kw", "min_coralie_10m_kw", "min_carmenes_v51_10m_kw"):
            nr[c] = ""
        u_map[r["star"]] = nr

    hemi_map = {"GEMINI_GRACES": "NORTH_MAUNAKEA", "ESO_CORALIE": "SOUTH_LASILLA", "CARMENES_VIS": "NORTH_CALARALTO"}
    regime_map = {"GEMINI_GRACES": "OPTICAL_GRACES", "ESO_CORALIE": "OPTICAL_CORALIE", "CARMENES_VIS": "OPTICAL_CARMENES_VIS"}
    for st in sorted(exps_by_star.keys()):
        exps = exps_by_star[st]
        e0 = exps[0]; inst = e0["instrument"]; n_exp = len(exps)
        p_best = float(star_ul_best[st]["p_beam_10m_kw"])
        n_cand = v51_cnt_by_star[st]
        assert st not in u_map, f"Expected strictly brand-new D093 target, found {st}"
        u_map[st] = {k: ("0" if k.startswith("n_exposures_") else "") for k in U350_COLS}
        u_map[st].update({
            "phases": "D093", "hemisphere": hemi_map[inst], "spectral_regime": regime_map[inst],
            "instruments": inst, "star": st, "common_name": e0["common_name"], "role": e0["role"], "subrole": e0["subrole"],
            "dist_pc": str(e0["dist_pc"]), "within_10pc": "True" if e0["within_10pc"] else "False",
            "teff_k": str(e0["teff_k"]), "phot_g_mag": str(e0["phot_g_mag"]),
            "j_mag": str(e0["j_mag"]), "h_mag": str(e0["h_mag"]), "ks_mag": str(e0["ks_mag"]),
            "n_exoplanets": str(e0["n_exoplanets"]),
            "n_exposures_optical": str(n_exp),
            "n_exposures_total": str(n_exp),
            "min_optical_10m_kw": f"{p_best:.8g}",
            "min_panchromatic_10m_kw": f"{p_best:.8g}",
            "automated_qualified_candidates": str(n_cand), "verified_eti_detections": "0",
            "n_exposures_graces": str(n_exp) if inst == "GEMINI_GRACES" else "0",
            "min_graces_10m_kw": f"{p_best:.8g}" if inst == "GEMINI_GRACES" else "",
            "n_exposures_coralie": str(n_exp) if inst == "ESO_CORALIE" else "0",
            "min_coralie_10m_kw": f"{p_best:.8g}" if inst == "ESO_CORALIE" else "",
            "n_exposures_carmenes_v51": str(n_exp) if inst == "CARMENES_VIS" else "0",
            "min_carmenes_v51_10m_kw": f"{p_best:.8g}" if inst == "CARMENES_VIS" else "",
        })

    u350_rows = sorted(u_map.values(), key=lambda x: (float(x["dist_pc"]), x["star"]))
    solar153_rows = [r for r in u350_rows if r["within_10pc"] == "True"]

    # Unified 350-Star Multi-Event Ellipsoid Catalog
    prior_stars = {r["star"] for r in u335_base}
    prior_coords, prior_mjds = _load_prior_star_coords_and_mjds(archives_dir, prior_stars)
    multievent_rows: list[dict[str, Any]] = []
    for ur in u350_rows:
        st = ur["star"]
        dist_pc = float(ur["dist_pc"])
        if st in exps_by_star:
            exps = exps_by_star[st]
            ra_d, dec_d = float(exps[0]["s_ra"]), float(exps[0]["s_dec"])
            mjd_list = sorted({float(x["mjd_obs"]) for x in exps})
        else:
            ra_d, dec_d = prior_coords[st]
            mjd_list = sorted(set(prior_mjds[st]))
        syncs = [compute_multievent_sync_v51(ra_d, dec_d, dist_pc, m) for m in mjd_list]
        best_overall = min(syncs, key=lambda s: s["min_abs_ellipsoid_dt_days"])
        best_sn87 = min(syncs, key=lambda s: abs(s["sn1987a_dt_days"]))
        best_gw17 = min(syncs, key=lambda s: abs(s["gw170817_dt_days"]))
        best_sn23 = min(syncs, key=lambda s: abs(s["sn2023ixf_dt_days"]))
        multievent_rows.append({
            "star": st, "common_name": ur["common_name"], "phases": ur["phases"], "role": ur["role"],
            "dist_pc": round(dist_pc, 4), "within_10pc": ur["within_10pc"],
            "ra_deg": round(ra_d, 6), "dec_deg": round(dec_d, 6),
            "ecliptic_lat_deg": round(best_overall["ecliptic_lat_deg"], 5),
            "etz_qualified": abs(best_overall["ecliptic_lat_deg"]) <= 0.264,
            "n_epochs_checked": len(mjd_list),
            "min_abs_sn1987a_dt_days": round(abs(best_sn87["sn1987a_dt_days"]), 3),
            "min_abs_gw170817_dt_days": round(abs(best_gw17["gw170817_dt_days"]), 3),
            "min_abs_sn2023ixf_dt_days": round(abs(best_sn23["sn2023ixf_dt_days"]), 3),
            "nearest_event": best_overall["nearest_event"],
            "min_abs_ellipsoid_dt_days": round(best_overall["min_abs_ellipsoid_dt_days"], 3),
            "ellipsoid_qualified_180d": best_overall["min_abs_ellipsoid_dt_days"] <= 180.0,
        })

    # Cascade statistics & 5-stream Forensic Classification
    n_g1 = len(ledger_rows)
    n_g2 = sum(1 for r in ledger_rows if r["g2_pass"])
    n_g3 = sum(1 for r in ledger_rows if r["g2_pass"] and r["g3_pass"])
    n_g4 = sum(1 for r in ledger_rows if r["g2_pass"] and r["g3_pass"] and r["g4_pass"])
    n_pre_g6 = sum(1 for r in ledger_rows if r["pre_g6_qualified"])
    n_v42 = sum(1 for r in ledger_rows if r["qualified_v42_laser"])
    n_v50 = sum(1 for r in ledger_rows if r["qualified_v50_laser"])
    n_v51_ctrl = sum(1 for r in ledger_rows if r["qualified_v51_laser"] and r["role"] == "CONTROL")
    n_v51_sci = sum(1 for r in ledger_rows if r["qualified_v51_laser"] and r["role"] == "SCIENCE")
    n_retro88_v39 = sum(1 for r in retro88_rows if r["qualified_v39_laser"])
    n_retro88_v50 = sum(1 for r in retro88_rows if r["qualified_v50_retro"])
    n_retro88_v51 = sum(1 for r in retro88_rows if r["qualified_v51_retro"])
    n_nir_det = sum(1 for r in nir_rows if r["passes_ccf"])
    v2_tot = sum(v2_by_dp.values())
    int_hrs = round(sum(float(e["t_exptime_s"]) for e in exposures_raw) / 3600.0, 4)

    sci_ul = [r for r in ul_rows if exps_by_star[r["star"]][0]["role"] == "SCIENCE"]
    best_all = min(sci_ul, key=lambda r: float(r["p_beam_10m_kw"]))
    best_by_inst = {
        inst: min([r for r in sci_ul if r["instrument"] == inst], key=lambda r: float(r["p_beam_10m_kw"]))
        for inst in ("GEMINI_GRACES", "ESO_CORALIE", "CARMENES_VIS")
    }
    lim_10pc = [float(r["min_panchromatic_10m_kw"]) for r in solar153_rows if r["min_panchromatic_10m_kw"]]
    med_10pc_kw = round(exact_median_1d(np.asarray(lim_10pc, dtype=np.float64)), 5)

    nir_med_ul: dict[str, Any] = {}
    for mol in NIRSPEC_MOL_TEMPLATES_UM:
        vals = [float(r["delta_min_5sigma"]) for r in nir_rows if r["molecule"] == mol and r["delta_min_5sigma"] != ""]
        ppms = [float(r["ppm_equiv_10pct_ref"]) for r in nir_rows if r["molecule"] == mol and r["ppm_equiv_10pct_ref"] != ""]
        nir_med_ul[mol] = {
            "n_covered_targets": len(vals),
            "median_delta_min_5sigma": round(exact_median_1d(np.asarray(vals)), 5) if vals else None,
            "median_ppm_equiv_10pct_ref": round(exact_median_1d(np.asarray(ppms)), 3) if ppms else None,
            "detections": sum(1 for r in nir_rows if r["molecule"] == mol and r["passes_ccf"]),
        }

    # Stream 2 (DRIFT_V51), Stream 3 (AGNOSTIC), Stream 4 (COMB_V4_1), Stream 5 (NIRSPEC_CCF) forensics
    drift_forensic_recs: list[dict[str, Any]] = []
    drift_cls_cnt: Counter[str] = Counter()
    for dr in drift_rows:
        wr1 = float(dr["wave1_rest_a"])
        if float(dr["nearest_sky_sep_a"]) <= 6.0 or wr1 >= 6850.0:
            dcls = "TELLURIC_OR_AIRGLOW_PAIR"
        elif float(dr["nearest_chromo_sep_a"]) <= 6.0:
            dcls = "CHROMOSPHERIC_VARIABLE_WING"
        elif float(dr["teff_k"]) < 4000.0:
            dcls = "M_DWARF_MOLECULAR_PAIR"
        elif not bool(dr["g8_pass"]):
            dcls = "G8_PATCH_REJECTED_ARTIFACT"
        else:
            dcls = "CHANCE_PHOTOSPHERIC_NOISE_COINCIDENCE"
        drift_cls_cnt[dcls] += 1
        drift_forensic_recs.append({**dr, "forensic_class": dcls, "verified_eti": False})

    ag_forensic_recs: list[dict[str, Any]] = []
    ag_cls_cnt: Counter[str] = Counter()
    for ar in ag_survivor_rows:
        wr_a = float(ar["wave_rest_a"])
        if float(ar["nearest_chromo_sep_a"]) <= 6.0:
            acls = "CHROMOSPHERIC_LINE_WING"
        elif float(ar["nearest_sky_sep_a"]) <= 6.0 or wr_a >= 6850.0:
            acls = "TELLURIC_OR_O2_H2O_BAND"
        elif float(ar["teff_k"]) < 4000.0:
            acls = "M_DWARF_MOLECULAR_OR_PSEUDOCONTINUUM"
        else:
            acls = "PHOTOSPHERIC_OR_ORDER_MERGE_RESIDUAL"
        ag_cls_cnt[acls] += 1
        ag_forensic_recs.append({**ar, "forensic_class": acls, "verified_eti": False})

    comb_forensic_recs: list[dict[str, Any]] = []
    comb_cls_cnt: Counter[str] = Counter()
    for cr in comb_cand_rows:
        ccls = "M_DWARF_TIO_BAND_HEAD_PERIODICITY" if float(star_ctx[cr["star"]]["exps"][0]["teff_k"]) < 4000.0 else "PHOTOSPHERIC_LINE_CONGESTION"
        comb_cls_cnt[ccls] += 1
        comb_forensic_recs.append({**cr, "forensic_class": ccls, "verified_eti": False})

    nir_forensic_recs: list[dict[str, Any]] = []
    nir_cls_cnt: Counter[str] = Counter()
    for nr in nir_rows:
        if nr["passes_ccf"]:
            ncls = "SUBSTELLAR_ATMOSPHERIC_BAND_OR_SILICATE_SLOPE"
            nir_cls_cnt[ncls] += 1
            nir_forensic_recs.append({**nr, "forensic_class": ncls, "verified_eti": False})

    diag_doc = {
        "schema": "FORENSIC_D093_V51_CASCADE_DIAGNOSIS_V1",
        "phase_id": "D093",
        "nirspec_edge_trim_um": NIRSPEC_EDGE_TRIM_UM,
        "cascade": {
            "v2_legacy_false_alarms": v2_tot,
            "v42_total_ledger_g1_candidates": n_g1,
            "v42_after_g2": n_g2,
            "v42_after_g3": n_g3,
            "v42_after_g4": n_g4,
            "v42_pre_g6_passed_g1_to_g5": n_pre_g6,
            "v42_qualified_before_g7": n_v42,
            "v50_qualified_before_g8": n_v50,
            "v51_g8_vetoed_from_v50": n_v50 - (n_v51_ctrl + n_v51_sci),
            "v51_qualified_control": n_v51_ctrl,
            "v51_qualified_science": n_v51_sci,
            "drift_v51_evals": drift_evals_tot,
            "drift_v51_candidates": len(drift_rows),
            "v51_agnostic_evals": ag_evals_tot,
            "v51_agnostic_survivors": len(ag_survivor_rows),
            "comb_v41_automated_candidates": comb_v41_tot,
            "nirspec_ccf_cells_44_detections": n_nir_det,
        },
        "retroactive_d088_northern_regression": {
            "d088_total_g1_records": len(retro88_rows),
            "d088_v39_qualified_input": n_retro88_v39,
            "d088_v50_g7_survivors": n_retro88_v50,
            "d088_v51_g7_g8_survivors": n_retro88_v51,
            "suppression_fraction_v39_to_v51": round(1.0 - (n_retro88_v51 / max(1, n_retro88_v39)), 5),
            "top_d088_stars_before_after": {
                st88: {
                    "v39": sum(1 for r in retro88_rows if r["star"] == st88 and r["qualified_v39_laser"]),
                    "v50_g7": sum(1 for r in retro88_rows if r["star"] == st88 and r["qualified_v50_retro"]),
                    "v51_g7_g8": sum(1 for r in retro88_rows if r["star"] == st88 and r["qualified_v51_retro"]),
                }
                for st88 in ("GJ625", "LALANDE21185", "HD114710", "HD157881")
            },
        },
        "nirspec_g395h_molecular_ccf_summary": nir_med_ul,
        "comb_v41_allsky_d079_d093": {
            "total_exposures": int(snap_v50["prior_v50_total_exposures_count"]) + len(exposures_raw),
            "total_stacks": len(allsky_comb_rows),
            "comb_v4_automated_total": sum(int(r["comb_v4_candidates"]) for r in allsky_comb_rows),
            "comb_v41_automated_total": sum(int(r["comb_v41_candidates"]) for r in allsky_comb_rows),
            "verified_eti_total": 0,
        },
        "forensic_5stream_counts": {
            "v51_g7_g8_survivors": dict(forensic_cls_cnt.most_common()),
            "drift_v51_candidates": dict(drift_cls_cnt.most_common()),
            "agnostic_multiscale_survivors": dict(ag_cls_cnt.most_common()),
            "comb_v41_candidates": dict(comb_cls_cnt.most_common()),
            "nirspec_molecular_flagged": dict(nir_cls_cnt.most_common()),
            "verified_eti_total": 0,
        },
    }

    n_pl_hosts_tot = sum(1 for r in u350_rows if int(float(r["n_exoplanets"])) > 0)
    n_planets_tot = sum(int(float(r["n_exoplanets"])) for r in u350_rows)
    n_etz_tot = sum(1 for m in multievent_rows if m["etz_qualified"])
    n_ell180_tot = sum(1 for m in multievent_rows if m["ellipsoid_qualified_180d"])

    summary_doc = {
        "phase_id": "D093",
        "detector": DETECTOR_NAME,
        "stage2_calibration_refinements": {
            "stage1_v5_1_detector_untouched": True,
            "refinement_1_g8_v51b_standardized_patch_novelty": {
                "scope": "Gate G8_V51 patch-novelty feature vector & Mahalanobis+kNN whitening in WS93/analyze.py",
                "root_cause": "Stage-1 fit_patch_novelty_model_v51 / evaluate_gate_g8_v51 normalized each 17-px patch by its L2 norm prior to keeping top-8 background PCA components, suppressing isolated 10-30 sigma LSF Gaussians.",
                "fix": "Feature-wise standardized Z-score + arcsinh(sub/2.5) + whitened 8-PC Mahalanobis/k=7-NN distance with explicit LSF morphology & cohort-rarity guards (_extract_g8_feat_v51b / _fit_g8_v51b / _eval_g8_v51b).",
            },
            "refinement_2_nirspec_v51b_joint_multicomp_ccf": {
                "scope": "JWST NIRSpec G395H multi-component molecular continuum & covariance estimator in WS93/analyze.py",
                "root_cause": "Stage-1 _fit_miri_sideband_template evaluated CO (4.67 um) and 13CO (4.78 um) independently per component so each absorption band contaminated the other's continuum sideband.",
                "fix": "Union-excluded multi-component continuum mask + single joint continuum variance solve (_fit_nirspec_template_v51b / _joint_nirspec_confounder_v51b / _scan_nirspec_v51b).",
            },
        },
        "instruments": ["GEMINI_GRACES", "ESO_CORALIE", "CARMENES_VIS"],
        "cohort": {
            "total_stars": 15,
            "control_stars": sum(1 for r in star_rv_rows if r["role"] == "CONTROL"),
            "science_stars": sum(1 for r in star_rv_rows if r["role"] == "SCIENCE"),
            "brand_new_unique_stars": 15,
            "panchromatic_bridge_stars": 0,
            "brand_new_within_10pc": sum(1 for g in geom_rows if g["within_10pc"]),
            "total_exposures": len(exposures_raw),
            "graces_exposures": len(exps_by_inst["GEMINI_GRACES"]),
            "coralie_exposures": len(exps_by_inst["ESO_CORALIE"]),
            "carmenes_exposures": len(exps_by_inst["CARMENES_VIS"]),
            "total_integration_hours": int_hrs,
            "orbital_campaigns": len(orb_rows),
        },
        "searched_spectral_elements": {
            "by_instrument": searched_by_inst,
            "channel_t_1d_bins": sum(v["T"] for v in searched_by_inst.values()),
            "channel_p_coadd_bins": sum(v["P"] for v in searched_by_inst.values()),
            "channel_tdiff_bins": sum(v["T_DIFF"] for v in searched_by_inst.values()),
            "channel_kplanet_bins": sum(v["K_PLANET"] for v in searched_by_inst.values()),
            "drift_v51_shift_bin_evals": sum(v["DRIFT_EVALS"] for v in searched_by_inst.values()),
            "comb_v41_searched_configs": sum(v["COMB_CONFIGS"] for v in searched_by_inst.values()),
        },
        "synthetic_calibration_1591_trials": cal_sum,
        "false_alarm_cascade": diag_doc["cascade"],
        "retroactive_d088_northern_regression": diag_doc["retroactive_d088_northern_regression"],
        "nirspec_g395h_molecular_ccf_summary": nir_med_ul,
        "multievent_ellipsoid_d079_d093_summary": {
            "stars_evaluated": len(multievent_rows),
            "etz_qualified_stars": n_etz_tot,
            "ellipsoid_within_180d_stars": n_ell180_tot,
            "d093_highlights": {
                "HD111031_gw170817_dt_days": next(g["min_abs_gw170817_dt_days"] for g in geom_rows if g["star"] == "HD111031"),
                "ROSS64_sn1987a_dt_days": next(g["min_abs_sn1987a_dt_days"] for g in geom_rows if g["star"] == "ROSS64"),
                "ROSS64_etz_beta_deg": next(g["ecliptic_lat_deg"] for g in geom_rows if g["star"] == "ROSS64"),
                "HD206301_etz_beta_deg": next(g["ecliptic_lat_deg"] for g in geom_rows if g["star"] == "HD206301"),
            },
        },
        "upper_limits": {
            "n_cells": len(ul_rows),
            "best_d093_star": best_all["star"],
            "best_d093_instrument": best_all["instrument"],
            "best_d093_band": best_all["band_id"],
            "best_d093_10m_w": round(float(best_all["p_beam_10m_w"]), 5),
            "best_d093_10m_kw": round(float(best_all["p_beam_10m_kw"]), 6),
            "best_graces_star": best_by_inst["GEMINI_GRACES"]["star"],
            "best_graces_10m_kw": round(float(best_by_inst["GEMINI_GRACES"]["p_beam_10m_kw"]), 5),
            "best_coralie_star": best_by_inst["ESO_CORALIE"]["star"],
            "best_coralie_10m_kw": round(float(best_by_inst["ESO_CORALIE"]["p_beam_10m_kw"]), 5),
            "best_carmenes_star": best_by_inst["CARMENES_VIS"]["star"],
            "best_carmenes_10m_kw": round(float(best_by_inst["CARMENES_VIS"]["p_beam_10m_kw"]), 5),
        },
        "unified_350star_panchromatic_v5_1_synthesis": {
            "phases": "D079-D093",
            "spectrographs": 21,
            "spectral_arms": 24,
            "octave_span": 8.273,
            "unique_stars_total": len(u350_rows),
            "science_stars_total": sum(1 for r in u350_rows if r["role"] == "SCIENCE"),
            "control_stars_total": sum(1 for r in u350_rows if r["role"] == "CONTROL"),
            "planet_host_stars_total": n_pl_hosts_tot,
            "confirmed_exoplanets_total": n_planets_tot,
            "within_10pc_unique_stars": len(solar153_rows),
            "within_10pc_median_limit_kw": med_10pc_kw,
            "panchromatic_bridge_stars_total": len({r["star"] for r in bridge_rows}),
            "panchromatic_bridge_cells_total": len(bridge_rows),
            "total_exposures_d079_d093": int(snap_v50["prior_v50_total_exposures_count"]) + len(exposures_raw),
            "total_integration_hours_d079_d093": round(float(snap_v50["prior_cumulative_integration_hours"]) + int_hrs, 4),
            "total_calibration_trials_d079_d093": int(snap_v50["prior_v50_calibration_trials_count"]) + cal_sum["total_trials"],
            "v2_false_alarms_eliminated_total": int(snap_v50["prior_v2_false_alarms_eliminated_total"]) + v2_tot,
            "cumulative_orbital_campaigns": int(snap_v50["prior_cumulative_orbital_campaigns_count"]) + len(orb_rows),
        },
    }

    # Write ALL 33 deterministic Stage-B result artifacts
    _write_csv(out_dir / "EXPOSURE_PROVENANCE_D093.csv", list(prov_rows[0].keys()), prov_rows)
    _write_csv(out_dir / "STELLAR_RV_ANCHORS_D093.csv", list(rv_anchor_rows[0].keys()), rv_anchor_rows)
    _write_csv(out_dir / "STAR_RV_SUMMARY_15.csv", list(star_rv_rows[0].keys()), star_rv_rows)
    _write_csv(out_dir / "FOUR_GEN_BENCHMARK_D093.csv", list(bench_rows[0].keys()), bench_rows)
    ledger_cols = [
        "candidate_id", "instrument", "channel", "role", "science_track", "star", "dp_id",
        "fitted_wave_a", "stellar_rest_wave_a", "bary_wave_a", "topo_wave_a",
        "snr_mid", "snr_out", "cosine", "fwhm_ratio", "target_fn_pk3",
        "g1_pass", "g2_pass", "g3_pass", "primary_order", "primary_native_px", "primary_native_fn_pk3",
        "g4_pass", "g5_pass", "g5_cos11", "pre_g6_qualified", "g6_v35_dense_pass", "g6_pass",
        "qualified_v42_laser", "z_rpca", "rarity_score", "f_rest", "f_topo", "g7_pass",
        "qualified_v50_laser", "novelty_z", "g8_pass", "qualified_v51_laser", "final_disposition",
    ]
    _write_csv(out_dir / "V5_1_CANDIDATE_LEDGER.csv", ledger_cols, ledger_rows)
    drift_cols = [
        "drift_id", "instrument", "role", "teff_k", "star", "wave1_rest_a", "wave2_rest_a",
        "dv_kms", "dt_days", "vdot_kms_day", "vdot_ms_h", "z1", "z2", "z_stat2",
        "z_drift_comb", "rarity1", "rarity2", "novelty_z", "g8_pass",
        "nearest_sky_sep_a", "nearest_chromo_sep_a",
    ]
    _write_csv(out_dir / "BLIND_DRIFT_V51_CANDIDATES.csv", drift_cols, drift_rows)
    ag_cols = [
        "survivor_id", "star", "instrument", "role", "science_track", "teff_k",
        "wave_rest_a", "z_multi", "polarity", "scale_lsf", "kernel", "fwhm_a",
        "rarity_score", "f_rest", "f_topo", "nearest_sky_name", "nearest_sky_sep_a",
        "nearest_chromo_name", "nearest_chromo_sep_a",
    ]
    _write_csv(out_dir / "V5_1_AGNOSTIC_MULTISCALE_SURVIVORS.csv", ag_cols, ag_survivor_rows)
    _write_csv(out_dir / "RETROACTIVE_D088_NORTHERN_V51_REGRESSION.csv", list(retro88_rows[0].keys()), retro88_rows)
    _write_csv(out_dir / "JWST_NIRSPEC_G395H_MOLECULAR_CCF_44CELLS.csv", list(nir_rows[0].keys()), nir_rows)
    _write_csv(out_dir / "GEOMETRIC_SYNC_TRACKS_D093.csv", list(geom_rows[0].keys()), geom_rows)
    _write_csv(out_dir / "MULTIEVENT_ELLIPSOID_CATALOG_D079_D093.csv", list(multievent_rows[0].keys()), multievent_rows)
    _write_csv(out_dir / "ORBITAL_CAMPAIGN_RESULTS_8.csv", list(orb_rows[0].keys()), orb_rows)
    _write_csv(out_dir / "COMB_V4_1_STAR_RESULTS_15.csv", list(comb_star_rows[0].keys()), comb_star_rows)
    comb_c_cols = ["comb_id", "instrument", "star", "role", "band", "dnu_ghz", "nu0_ghz", "wave0_a", "wave_end_a", "s_comb", "topo_anti_ratio", "n_qualifying_teeth", "off_tooth_crowding", "intertooth_ratio"]
    _write_csv(out_dir / "COMB_V4_1_CANDIDATES.csv", comb_c_cols, comb_cand_rows)
    _write_csv(out_dir / "ALLSKY_COMB_V4_1_UNIFIED_D079_D093.csv", list(allsky_comb_rows[0].keys()), allsky_comb_rows)
    _write_csv(out_dir / "ALLSKY_COMB_V4_1_CANDIDATES_D079_D093.csv", list(allsky_comb_cands[0].keys()), allsky_comb_cands)
    _write_csv(out_dir / "CALIBRATION_V51_BLIND_DRIFT_120.csv", list(cal["drift_cal_rows"][0].keys()), cal["drift_cal_rows"])
    _write_csv(out_dir / "CALIBRATION_V51_PATCH_NOVELTY_120.csv", list(cal["patch_cal_rows"][0].keys()), cal["patch_cal_rows"])
    _write_csv(out_dir / "CALIBRATION_V51_RPCA_RARITY_180.csv", list(cal["rpca_cal_rows"][0].keys()), cal["rpca_cal_rows"])
    _write_csv(out_dir / "CALIBRATION_V51_AGNOSTIC_MULTISCALE_120.csv", list(cal["ag_cal_rows"][0].keys()), cal["ag_cal_rows"])
    _write_csv(out_dir / "CALIBRATION_V51_NIRSPEC_MOL_CCF_160.csv", list(cal["nir_cal_rows"][0].keys()), cal["nir_cal_rows"])
    _write_csv(out_dir / "INJECTION_RECOVERY_540.csv", list(cal["inj_rows"][0].keys()), cal["inj_rows"])
    _write_csv(out_dir / "CALIBRATION_COMPLETENESS_BY_BAND.csv", list(cal["comp_rows"][0].keys()), cal["comp_rows"])
    _write_csv(out_dir / "KEPLERIAN_TRACK_CALIBRATION_81.csv", list(cal["kep_rows"][0].keys()), cal["kep_rows"])
    _write_csv(out_dir / "DETECTOR_V51_G4G5_CALIBRATION_108.csv", list(cal["g45_rows"][0].keys()), cal["g45_rows"])
    _write_csv(out_dir / "COMB_V4_1_CALIBRATION_162.csv", list(cal["comb_cal_rows"][0].keys()), cal["comb_cal_rows"])
    _write_csv(out_dir / "STAR_UPPER_LIMITS_D093.csv", list(ul_rows[0].keys()), ul_rows)
    _write_csv(out_dir / "PANCHROMATIC_BRIDGE_37STARS_V51.csv", list(bridge_rows[0].keys()), bridge_rows)
    _write_csv(out_dir / "UNIFIED_PANCHROMATIC_V5_1_SYNTHESIS_350STARS.csv", U350_COLS, u350_rows)
    _write_csv(out_dir / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_153STARS.csv", U350_COLS, solar153_rows)
    _write_json(out_dir / "FORENSIC_D093_CASCADE_DIAGNOSIS.json", diag_doc)
    _write_json(out_dir / "FORENSIC_CANDIDATE_AUDIT_D093.json", {
        "schema": "D093_FORENSIC_AUDIT_V1_5STREAM",
        "nirspec_edge_trim_um": NIRSPEC_EDGE_TRIM_UM,
        "n_v51_qualified": len(forensic_recs),
        "n_drift_v51_candidates": len(drift_forensic_recs),
        "n_agnostic_survivors": len(ag_forensic_recs),
        "n_comb_v41_candidates": len(comb_forensic_recs),
        "n_nirspec_flagged": len(nir_forensic_recs),
        "verified_eti_total": 0,
        "stream_counts": diag_doc["forensic_5stream_counts"],
        "candidates": forensic_recs,
        "drift_v51_candidates": drift_forensic_recs,
        "agnostic_survivors": ag_forensic_recs,
        "comb_v41_candidates": comb_forensic_recs,
        "nirspec_flagged": nir_forensic_recs,
    })
    _write_json(out_dir / "SUMMARY.json", summary_doc)

    print(
        f"Stage B DONE ({out_dir}): {len(u350_rows)} stars ({len(solar153_rows)} <10pc), "
        f"D093 G1={n_g1} -> V4.2={n_v42} -> V5.0={n_v50} -> V5.1={n_v51_ctrl + n_v51_sci}; "
        f"Drift={len(drift_rows)}; Agnostic={len(ag_survivor_rows)}; D088 {n_retro88_v39}->{n_retro88_v51}; "
        f"NIRSpec det={n_nir_det}/44; best={best_all['star']} {best_all['band_id']}={best_all['p_beam_10m_kw']:.4f} kW",
        flush=True,
    )
    return summary_doc


def main() -> None:
    p = argparse.ArgumentParser(description="Phase D093 V5.1 Analysis Pipeline")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--from-full-inputs", action="store_true", help="Ingest raw D093 FITS into bounded bundle and analyze")
    g.add_argument("--from-bounded-inputs", action="store_true", help="Run strictly from bounded_inputs/d093_bounded_bundle.json.gz")
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
