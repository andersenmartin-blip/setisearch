#!/usr/bin/env python3
"""
Phase D091 Analysis Pipeline (`ESO_TRIPLE_SPECTROGRAPH_3ARM_V4_2`)
==================================================================

Architecture (mirroring Phase D090 bit-identity harness):
  - Stage A (`--from-full-inputs`): ingests raw ESO Phase-3 FITS (`ESO_XSHOOTER_3ARM`
    UVB+VIS+NIR triplets, `ESO_FEROS`, `ESO_GIRAFFE_HR`) from `inputs_d091_v4_2/`,
    verifies `FULL_D091_INPUT_MANIFEST.json` + `FROZEN_COHORT_D091.csv`, converts
    standard air wavelengths to vacuum (`em.wl;obs.atmos`) and aligns to barycentric
    frame, preserves native 3-arm cutouts/arrays, and emits a compact bounded bundle
    `bounded_inputs/d091_bounded_bundle.json.gz` strictly `< 25.0 MiB`.
  - Stage B (`--from-bounded-inputs` or immediately following Stage A): decodes the
    bounded bundle with numpy+stdlib only (no raw FITS needed), executes the full
    4-generation detection cascade (`V1..V4.2` incl. `G4_V42` X-shooter simultaneous
    multi-arm dichroic coincidence), `COMB_V4` vs `COMB_V4_1`, `2,697` synthetic
    calibration trials (`1620 + 135 + 216 + 240 + 486`) plus `8/8` X-shooter dual-arm
    coincidence tests, all-sky `358`-stack comb sweep (`D079-D091`), `127` star-band
    10 m EIRP limits, `35` panchromatic bridges, `310`-star (`135 <10pc`) synthesis,
    and `310`-system multi-messenger closure -> 24 deterministic result files.
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
import warnings
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import median_filter

from v4_2_detector import (
    C_ANGSTROM_GHZ,
    C_KMS,
    CALIBRATION_BANDS_FEROS,
    CALIBRATION_BANDS_GIRAFFE,
    CALIBRATION_BANDS_XSHOOTER,
    COMB_V4_1_WINDOWS_A,
    DETECTOR_NAME,
    FWHM_FACTOR,
    GROUND_AIRGLOW_AND_TELLURIC_A,
    XSHOOTER_TELLURIC_BLACKOUT_A,
    bary_to_planet_rest_wave,
    build_and_scan_transit_channels,
    build_multi_epoch_rest_coadd_and_channel_p,
    check_channel_lsf_gate,
    compute_photon_beam_upper_limit,
    compute_running_continuum,
    construct_knn_stellar_templates,
    effective_resolving_power,
    evaluate_gate_g2_airglow,
    evaluate_gate_g6_v35_dense,
    evaluate_gate_g6_v36_sparse,
    evaluate_gates_g3_g4_g5_v42,
    exact_mad_1d,
    exact_median_1d,
    gaia_g_planck_flam_cgs,
    get_calibration_bands,
    get_inst_config,
    measure_exposure_stellar_rv,
    planet_rest_to_bary_wave,
    scan_frequency_comb_v4,
    scan_frequency_comb_v4_1,
    scan_single_exposure_residual_lsf,
    stdlib_earth_helio_rv_kms,
)

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = Path(__file__).resolve().parent
DEFAULT_BUNDLE = WS / "bounded_inputs" / "d091_bounded_bundle.json.gz"
MAX_BUNDLE_MIB = 25.0

U310_COLS = [
    "phases", "hemisphere", "spectral_regime", "instruments", "star", "common_name", "role", "subrole",
    "dist_pc", "within_10pc", "teff_k", "phot_g_mag", "j_mag", "h_mag", "ks_mag", "n_exoplanets",
    "n_exposures_optical", "n_exposures_nir_yjh", "n_exposures_kband", "n_exposures_total",
    "min_optical_10m_kw", "min_nir_yjh_10m_kw", "min_kband_10m_kw",
    "p_1064nm_10m_kw", "p_1550nm_10m_kw", "p_2040nm_tm_10m_kw", "p_2097nm_hoyag_10m_kw",
    "min_panchromatic_10m_kw", "automated_qualified_candidates", "verified_eti_detections",
    "n_exposures_nuv", "min_nuv_10m_kw", "n_exposures_fuv", "min_fuv_10m_kw",
    "n_exposures_farred_uves", "min_farred_uves_10m_kw", "n_exposures_lyman_fuse", "min_lyman_fuse_10m_kw",
    "n_exposures_jwst_ir", "min_jwst_ir_10m_kw", "p_10p6um_co2_10m_kw",
    "n_exposures_xshooter_3arm", "min_xshooter_3arm_10m_kw",
    "n_exposures_feros_v42", "min_feros_v42_10m_kw",
    "n_exposures_giraffe_hr", "min_giraffe_hr_10m_kw",
]


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


# ---------------------------------------------------------------------------
# Compact Lossless / 21-Bit IEEE-754 Array Serialization (< 25 MiB bundle)
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


# ---------------------------------------------------------------------------
# Wavelength Frame Conversions: Air -> Vacuum & SPECSYS -> Barycentric
# ---------------------------------------------------------------------------

def air_to_vacuum_angstrom(w_air: np.ndarray) -> np.ndarray:
    """Ciddor (1996) / Morton (2000) standard air-to-vacuum above 2000 A."""
    w = np.asarray(w_air, dtype=np.float64)
    s = 1e4 / np.maximum(2000.0, w)
    s2 = s * s
    n = 1.0 + 0.0000834254 + 0.02406147 / (130.0 - s2) + 0.00015998 / (38.9 - s2)
    return np.where(w >= 2000.0, w * n, w)


def _extract_fits_1d(fits_path: Path, ra_deg: float, dec_deg: float, mjd_fallback: float) -> dict[str, Any]:
    from astropy.io import fits

    with fits.open(fits_path, memmap=False) as hdul:
        h0 = hdul[0].header
        h1 = hdul[1].header
        dat = hdul[1].data
        names = set(dat.names)

        w_col = hdul[1].columns["WAVE"]
        w_unit = str(w_col.unit or h1.get("TUNIT1") or "").lower()
        w = np.asarray(dat["WAVE"][0], dtype=np.float64)
        if "nm" in w_unit:
            w = w * 10.0

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
        for card in ("ESO QC VRAD BARYCOR", "ESO DRS BARYCORR", "BARYCORR"):
            val = h0.get(card, h1.get(card))
            if val is not None and math.isfinite(float(val)):
                berv_val = float(val)
                berv_src = card
                break
        if berv_val is None:
            berv_val = stdlib_earth_helio_rv_kms(ra_deg, dec_deg, mjd_obs)

    return {
        "w_air_a": w,
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


def _arm_to_bary_vac(arm_wave_air: np.ndarray, specsys: str, berv_kms: float) -> np.ndarray:
    """Convert ESO Phase-3 air wavelengths to barycentric vacuum wavelengths."""
    w_vac = air_to_vacuum_angstrom(arm_wave_air)
    if specsys in ("TOPOCENT", "GEOCENT", "UNKNOWN", ""):
        return w_vac * (1.0 + berv_kms / C_KMS)
    # BARYCENT and HELIOCEN (< 0.012 km/s difference << 2.6-6.9 km/s sigma_v) are already barycentric
    return w_vac


# ---------------------------------------------------------------------------
# Stage A: Raw FITS Ingestion -> Bounded Bundle (< 25 MiB)
# ---------------------------------------------------------------------------

def run_stage_a_build_bundle(full_dir: Path, bundle_out: Path = DEFAULT_BUNDLE) -> dict[str, Any]:
    cohort_path = WS / "FROZEN_COHORT_D091.csv"
    man_path = WS / "FULL_D091_INPUT_MANIFEST.json"
    if not cohort_path.exists() or not man_path.exists():
        raise RuntimeError("Missing FROZEN_COHORT_D091.csv or FULL_D091_INPUT_MANIFEST.json")

    with cohort_path.open("r", encoding="utf-8", newline="") as fh:
        coh_rows = list(csv.DictReader(fh))
    man_doc = json.loads(man_path.read_text(encoding="utf-8"))
    man_by_dp = {e["dp_id"]: e for e in man_doc["exposures"]}
    assert len(coh_rows) == 156 and len(man_by_dp) == 156

    print(f"Stage A: ingesting 156 exposures (222 FITS) from {full_dir}...", flush=True)
    bundle_exps: list[dict[str, Any]] = []

    for idx, row in enumerate(coh_rows, 1):
        dp_id = row["dp_id"]
        inst = row["instrument"]
        me = man_by_dp[dp_id]
        ra_deg = float(row["s_ra"])
        dec_deg = float(row["s_dec"])
        mjd_nom = float(row["mjd_obs"])

        arms_encoded: list[dict[str, Any]] = []
        if inst == "ESO_XSHOOTER_3ARM":
            arm_names = ("UVB", "VIS", "NIR")
            slots = ("f1", "f2", "f3")
            specsys_main = "TOPOCENT"
            berv_vals = []
            flux_unit_main = "erg cm**(-2) s**(-1) angstrom**(-1)"
            fluxcal_main = "ABSOLUTE"
            r_vis = float(row["resolving_power"])
            for order_i, (aname, sl) in enumerate(zip(arm_names, slots)):
                rel = me[f"{sl}_rel"]
                fp = full_dir / rel
                if not fp.exists() or _sha256(fp) != me[f"{sl}_sha256"]:
                    raise RuntimeError(f"FITS missing or SHA mismatch: {fp}")
                ext = _extract_fits_1d(fp, ra_deg, dec_deg, mjd_nom)
                berv_vals.append(ext["berv_kms"])
                if aname == "VIS":
                    specsys_main = ext["specsys"]
                    flux_unit_main = ext["f_unit"]
                    fluxcal_main = ext["fluxcal"] or fluxcal_main
                    if ext["resolving_power"] > 1000:
                        r_vis = ext["resolving_power"]
                arms_encoded.append({
                    "arm": aname,
                    "order": order_i,
                    "dp_file_id": row[f"{sl}_id"],
                    "specsys": ext["specsys"],
                    "berv_kms": round(ext["berv_kms"], 5),
                    "berv_src": ext["berv_src"],
                    "wave": _encode_wave(ext["w_air_a"]),
                    "flux": _encode_f32_t21(ext["flux"]),
                    "err": _encode_f32_t21(ext["err"]),
                    "qual": _encode_qual(ext["qual"]),
                })
            berv_kms = float(exact_median_1d(np.asarray(berv_vals, dtype=np.float64)))
            berv_src = arms_encoded[1]["berv_src"]
            resolving_power = r_vis
        else:
            fp = full_dir / me["f1_rel"]
            if not fp.exists() or _sha256(fp) != me["f1_sha256"]:
                raise RuntimeError(f"FITS missing or SHA mismatch: {fp}")
            ext = _extract_fits_1d(fp, ra_deg, dec_deg, mjd_nom)
            specsys_main = ext["specsys"]
            berv_kms = ext["berv_kms"]
            berv_src = ext["berv_src"]
            flux_unit_main = ext["f_unit"]
            fluxcal_main = ext["fluxcal"] or "UNCALIBRATED"
            resolving_power = ext["resolving_power"] if ext["resolving_power"] > 1000 else float(row["resolving_power"])
            aname = "FEROS" if inst == "ESO_FEROS" else row["grating"].split("_")[0]
            arms_encoded.append({
                "arm": aname,
                "order": 0,
                "dp_file_id": row["f1_id"],
                "specsys": ext["specsys"],
                "berv_kms": round(ext["berv_kms"], 5),
                "berv_src": ext["berv_src"],
                "wave": _encode_wave(ext["w_air_a"]),
                "flux": _encode_f32_t21(ext["flux"]),
                "err": _encode_f32_t21(ext["err"]),
                "qual": _encode_qual(ext["qual"]),
            })

        bundle_exps.append({
            "dp_id": dp_id,
            "instrument": inst,
            "star": row["canonical_target"],
            "common_name": row["common_name"],
            "role": row["role"],
            "subrole": row["subrole"],
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
            "epoch_rank": int(row["epoch_rank"]),
            "grating": row["grating"],
            "resolving_power": float(resolving_power),
            "mjd_obs": mjd_nom,
            "t_exptime_s": float(row["t_exptime"]),
            "phase_window": row["phase_window"],
            "signed_phase": float(row["signed_phase"]),
            "planet_orbital_rv_kms": float(row["planet_orbital_rv_kms"]),
            "specsys": specsys_main,
            "berv_kms": round(berv_kms, 5),
            "berv_src": berv_src,
            "flux_unit": flux_unit_main,
            "fluxcal": fluxcal_main,
            "arms": arms_encoded,
        })
        if idx % 30 == 0 or idx == len(coh_rows):
            print(f"  Stage A parsed {idx}/{len(coh_rows)} exposures...", flush=True)

    bundle = {
        "schema": "D091_BOUNDED_BUNDLE_V1",
        "phase_id": "D091",
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
    print(f"Stage A DONE: wrote {bundle_out.name} ({bnd_mib:.2f} MiB < {MAX_BUNDLE_MIB:.1f} MiB)", flush=True)

    # Re-read exactly from disk so --from-full-inputs & --from-bounded-inputs share identical decoded floats
    with gzip.open(bundle_out, "rt", encoding="utf-8") as gz:
        return json.load(gz)


# ---------------------------------------------------------------------------
# Stage B Helpers: Exposure Reconstruction, Merging & Native Patches
# ---------------------------------------------------------------------------

def _telluric_blackout_mask(wave_a: np.ndarray, inst: str) -> np.ndarray:
    m = np.zeros(len(wave_a), dtype=bool)
    if inst == "ESO_XSHOOTER_3ARM":
        for lo, hi in XSHOOTER_TELLURIC_BLACKOUT_A:
            m |= (wave_a >= lo) & (wave_a <= hi)
    return m


def _unpack_exposure_spectrum(exp: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """Decode arms -> air-to-vac -> barycentric, compute continuum per arm, build unified 1D arrays."""
    inst = exp["instrument"]
    native_arms: list[dict[str, Any]] = []

    for arm in exp["arms"]:
        w_air = _decode_wave(arm["wave"])
        w_bary = _arm_to_bary_vac(w_air, arm["specsys"], float(arm["berv_kms"]))
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

        c_raw, c_eff = compute_running_continuum(w_bary, fl_clean, cfg, err=er_clean)
        cont = np.where(c_raw > 0.0, c_raw, c_eff)
        fn = np.where(bad | (~np.isfinite(fl_clean)) | (~np.isfinite(c_eff)) | (c_eff <= 0.0), np.nan, fl_clean / c_eff)
        med_cont = exact_median_1d(cont[np.isfinite(cont) & (cont > 0)]) if np.any(np.isfinite(cont) & (cont > 0)) else 1.0
        fn_scaled = fl_clean / max(1e-26, med_cont)

        native_arms.append({
            "arm": arm["arm"],
            "order": int(arm["order"]),
            "w_bary": w_bary,
            "flux": fl_clean,
            "cont": cont,
            "fn": fn,
            "err": er_clean,
            "qual": qu,
            "fn_scaled": fn_scaled,
        })

    if inst == "ESO_XSHOOTER_3ARM":
        # Merge 3 normalized arms onto unified sorted grid (preferring VIS in overlap zones for R=18k fidelity)
        arm_map = {a["arm"]: a for a in native_arms}
        seg_w, seg_fn, seg_fl = [], [], []
        if "UVB" in arm_map:
            a = arm_map["UVB"]
            m = a["w_bary"] < 5337.0
            seg_w.append(a["w_bary"][m])
            seg_fn.append(a["fn"][m])
            seg_fl.append(a["flux"][m])
        if "VIS" in arm_map:
            a = arm_map["VIS"]
            seg_w.append(a["w_bary"])
            seg_fn.append(a["fn"])
            seg_fl.append(a["flux"])
        if "NIR" in arm_map:
            a = arm_map["NIR"]
            m = a["w_bary"] > 10200.0
            seg_w.append(a["w_bary"][m])
            seg_fn.append(a["fn"][m])
            seg_fl.append(a["flux"][m])
        w_all = np.concatenate(seg_w)
        fn_all = np.concatenate(seg_fn)
        fl_all = np.concatenate(seg_fl)
        idx_s = np.argsort(w_all)
        w_all = w_all[idx_s]
        fn_all = fn_all[idx_s]
        fl_all = fl_all[idx_s]
    else:
        a0 = native_arms[0]
        w_all = a0["w_bary"]
        fn_all = a0["fn"]
        fl_all = a0["flux"]

    return {
        "w_bary": w_all,
        "fn": fn_all,
        "flux_cgs": fl_all,
        "arms": native_arms,
    }


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
        # Interpolate linear across isolated NaNs on edges; reject if core is NaN
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
            "arm": a["arm"],
            "order": int(a["order"]),
            "native_pixel": int(k),
            "wave": w_win,
            "flux_a": f_win_clean,
            "ref_norm_a": ref_win,
            "err_a": e_win,
            "dq": q_win,
            "target_wave_a": float(target_bary_a),
        })
    return patches


def _compute_legacy_v2_count(w_bary: np.ndarray, fn: np.ndarray, cfg: dict[str, Any]) -> int:
    """Simulated legacy V2 raw positive spikes >= 4.5*MAD above unity before template/vetoes."""
    fin = np.isfinite(w_bary) & np.isfinite(fn)
    if int(fin.sum()) < 50:
        return 0
    y = fn[fin] - 1.0
    mad = exact_mad_1d(y)
    if not math.isfinite(mad) or mad <= 0.0:
        return 0
    raw = y > 4.5 * mad
    # Count contiguous clusters (peak detections)
    starts = raw & np.concatenate(([True], ~raw[:-1]))
    return int(np.sum(starts))


def _forensic_classify(rec: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    """Forensic triage for any candidate surviving G1-G6 automated gates."""
    inst = rec["instrument"]
    w_bary = float(rec["bary_wave_a"])
    w_rest = float(rec["stellar_rest_wave_a"])
    ch = rec["channel"]
    st = rec["star"]
    near_sky = min(GROUND_AIRGLOW_AND_TELLURIC_A, key=lambda x: abs(float(rec["topo_wave_a"]) - float(x["wave_A"])))
    sky_sep_a = abs(float(rec["topo_wave_a"]) - float(near_sky["wave_A"]))

    if inst == "ESO_XSHOOTER_3ARM" and ((5320.0 <= w_bary <= 5580.0) or (9920.0 <= w_bary <= 10220.0)):
        fclass = "XSHOOTER_DICHROIC_EDGE_ARTIFACT"
        note = "Located at X-shooter UVB/VIS or VIS/NIR dichroic throughput roll-off edge."
    elif sky_sep_a <= 5.0:
        fclass = "TELLURIC_OR_AIRGLOW_WING_RESIDUAL"
        note = f"Telluric/airglow wing residual {sky_sep_a:.2f} A from {near_sky['name']}."
    elif meta.get("teff_k", 5000.0) < 4200.0:
        fclass = "M_DWARF_UNMODELED_MOLECULAR_OR_FLARE_FEATURE"
        note = "Cool M/L-dwarf TiO/VO/CrH molecular bandhead, blue continuum roll-off, or micro-flare residual."
    elif rec.get("role") == "CONTROL":
        fclass = "ZERO_PLANET_CONTROL_CALIBRATION_FEATURE"
        note = f"Zero-planet control star ({st}) calibration/reduction residual."
    elif ch == "T" and meta.get("n_epochs", 1) >= 2:
        fclass = "SINGLE_EPOCH_TRANSIENT_NONPERSISTENT"
        note = "Single-epoch residual absent in matching-epoch coadd and other exposures."
    else:
        fclass = "ARCHIVAL_REDUCTION_EDGE_OR_FRINGE_RESIDUAL"
        note = "Single-order/fringe archival extraction residual without multi-epoch laser coherence."

    return {
        "candidate_id": rec["candidate_id"],
        "instrument": inst,
        "channel": ch,
        "role": rec["role"],
        "star": st,
        "dp_id": rec["dp_id"],
        "bary_wave_a": rec["bary_wave_a"],
        "stellar_rest_wave_a": rec["stellar_rest_wave_a"],
        "snr_mid": rec["snr_mid"],
        "g5_cos11": rec["g5_cos11"],
        "forensic_class": fclass,
        "forensic_note": note,
        "verified_eti": False,
    }


def _rolling_comb_sigma(y_arr: np.ndarray, floor_mad: float) -> np.ndarray:
    """Compute local rolling 1.4826*MAD noise floor for COMB_V4 / COMB_V4_1 frequency scanning."""
    y_clean = np.where(np.isfinite(y_arr), y_arr, 0.0)
    win_sz = min(201, max(31, (len(y_clean) // 4) * 2 + 1)) | 1
    med_loc = median_filter(y_clean, size=win_sz, mode="nearest")
    sig = 1.4826 * median_filter(np.abs(y_clean - med_loc), size=win_sz, mode="nearest")
    floor_v = max(1e-4, 1.4826 * (floor_mad if math.isfinite(floor_mad) and floor_mad > 0.0 else 0.03))
    return np.maximum(sig, floor_v)


def _scan_comb_star_worker(
    payload: tuple[str, str, float, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
) -> tuple[str, int, list[dict[str, Any]], int]:
    """Run COMB_V4 & COMB_V4_1 per spectral window on one star using local rolling-MAD noise."""
    st, inst, r_pow, rg, rp, fn_p, tpl, sky_mask, y_topo, mad_r = payload
    cfg = get_inst_config(inst, r_pow)
    sig_r = _rolling_comb_sigma(rp, mad_r)
    sig_topo = np.maximum(_rolling_comb_sigma(y_topo, mad_r), sig_r)
    allowed = cfg["comb_search_bands"]
    v4_count = 0
    v41_hits: list[dict[str, Any]] = []
    n_cfg_tot = 0
    for win in COMB_V4_1_WINDOWS_A[inst]:
        if win["band"] not in allowed:
            continue
        sl = (rg >= float(win["lo_a"]) - 40.0) & (rg <= float(win["hi_a"]) + 40.0)
        if int(sl.sum()) < 80:
            continue
        hv4, _ = scan_frequency_comb_v4(
            rg[sl], rp[sl], sig_r[sl], fn_p[sl], tpl[sl], sky_mask[sl], y_topo[sl], sig_topo[sl], [win], [win["band"]], cfg
        )
        hv41, n_cfg = scan_frequency_comb_v4_1(
            rg[sl], rp[sl], sig_r[sl], fn_p[sl], tpl[sl], sky_mask[sl], y_topo[sl], sig_topo[sl], [win], [win["band"]], cfg
        )
        v4_count += len(hv4)
        v41_hits.extend(hv41)
        n_cfg_tot += n_cfg
    v41_hits.sort(key=lambda h: (-float(h["s_comb"]), h["band"], float(h["dnu_ghz"]), float(h["nu0_ghz"])))
    return st, v4_count, v41_hits, n_cfg_tot


# ---------------------------------------------------------------------------
# Stage B Synthetic Calibration Suites (2,697 trials + 8/8 X-shooter Dual-Arm)
# ---------------------------------------------------------------------------

def _run_all_calibrations(
    star_ctx: dict[str, dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
]:
    # Representative clean target per (instrument, band)
    rep_star: dict[tuple[str, str], str] = {}
    for b in CALIBRATION_BANDS_XSHOOTER:
        rep_star[("ESO_XSHOOTER_3ARM", b["band_id"])] = "HD1064"
    for b in CALIBRATION_BANDS_FEROS:
        rep_star[("ESO_FEROS", b["band_id"])] = "ZETTUC"
    # GIRAFFE bands map to specific grating stars in our cohort
    giraffe_band_stars = {
        "G1_5250": "TAUCET",
        "G2_5480": "GJ436",
        "G3_5715": "OGLETR113",
        "G4_6260": "KEPLER156",
    }
    for bid, st in giraffe_band_stars.items():
        rep_star[("ESO_GIRAFFE_HR", bid)] = st

    # 1) 1,620 Injection-Recovery Trials (15 bands x 2 modes x 6 sigmas x 9 trials)
    rng_inj = np.random.default_rng(202609101)
    sigmas = [3.5, 5.0, 6.5, 8.0, 10.0, 12.0]
    modes = ["CHANNEL_T_TRANSIENT_1EPOCH", "CHANNEL_P_STATIC_COADD"]
    inj_rows: list[dict[str, Any]] = []
    comp_rows: list[dict[str, Any]] = []

    all_bands = (
        [("ESO_XSHOOTER_3ARM", b) for b in CALIBRATION_BANDS_XSHOOTER]
        + [("ESO_FEROS", b) for b in CALIBRATION_BANDS_FEROS]
        + [("ESO_GIRAFFE_HR", b) for b in CALIBRATION_BANDS_GIRAFFE]
    )
    tid = 0
    for inst, band in all_bands:
        bid = band["band_id"]
        wc = float(band["center_wave_A"])
        cfg = get_inst_config(inst)
        r_eff = effective_resolving_power(cfg, wc)
        sig_a = wc / (r_eff * FWHM_FACTOR)
        st = rep_star[(inst, bid)]
        ctx = star_ctx[st]
        step_a = float(cfg["coadd_step_angstrom"])
        # Extract 400-bin window from star's actual empirical MAD scale
        rg = ctx["rest_grid"]
        m_w = (rg >= wc - 220 * step_a) & (rg <= wc + 220 * step_a)
        w_win = rg[m_w]
        emp_resids = ctx["resids_mat"][:, m_w]
        fin_vals = emp_resids[np.isfinite(emp_resids)]
        noise_mad = max(0.002, float(exact_mad_1d(fin_vals))) if len(fin_vals) >= 30 else 0.015

        for mode in modes:
            for sig_m in sigmas:
                hits = 0
                for rep_i in range(9):
                    tid += 1
                    off = float(rng_inj.uniform(-3.0 * step_a, 3.0 * step_a))
                    w0 = wc + off
                    prof = np.exp(-0.5 * ((w_win - w0) / sig_a) ** 2)
                    n_noise = noise_mad
                    if mode == "CHANNEL_T_TRANSIENT_1EPOCH":
                        amp = sig_m * n_noise
                        y = amp * prof + n_noise * rng_inj.standard_normal(len(w_win))
                        fn = 1.0 + y
                        cands, _, _ = scan_single_exposure_residual_lsf(w_win, y, cfg, "T", flux_norm_for_f1=fn)
                    else:
                        n_ep = 3
                        noise_coadd = n_noise / math.sqrt(n_ep)
                        amp = sig_m * noise_coadd
                        y = amp * prof + noise_coadd * rng_inj.standard_normal(len(w_win))
                        fn = 1.0 + y
                        cands, _, _ = scan_single_exposure_residual_lsf(w_win, y, cfg, "P", flux_norm_for_f1=fn)
                    rec = any(abs(c["fitted_center_a"] - w0) <= 3.0 * sig_a and check_channel_lsf_gate(c, "T" if "T_" in mode else "P", cfg) for c in cands)
                    hits += int(rec)
                    inj_rows.append({
                        "trial_id": tid, "instrument": inst, "band_id": bid, "center_wave_a": wc,
                        "mode": mode, "sigma_mult": sig_m, "rep": rep_i + 1, "star": st,
                        "recovered": rec, "best_snr_mid": round(max((c["snr_mid"] for c in cands), default=0.0), 3),
                    })
                comp_rows.append({
                    "instrument": inst, "band_id": bid, "center_wave_a": wc,
                    "mode": mode, "sigma_mult": sig_m, "n_trials": 9, "n_recovered": hits,
                    "completeness": round(hits / 9.0, 4),
                })

    # 2) 135 Keplerian De-Doppler Track Trials (5 high-dv orbital stars x 27 trials)
    rng_kep = np.random.default_rng(202609102)
    kep_rows: list[dict[str, Any]] = []
    kep_hosts = [
        ("ESO_XSHOOTER_3ARM", "K222", 10070.0),
        ("ESO_FEROS", "GJ433", 6328.0),
        ("ESO_FEROS", "HD213885", 5320.0),
        ("ESO_GIRAFFE_HR", "GJ436", 5480.0),
        ("ESO_GIRAFFE_HR", "OGLETR113", 5715.0),
        ("ESO_GIRAFFE_HR", "KEPLER156", 6260.0),
    ]
    kid = 0
    for idx_t in range(135):
        kid += 1
        inst, st, wc = kep_hosts[idx_t % len(kep_hosts)]
        cfg = get_inst_config(inst)
        step_a = float(cfg["coadd_step_angstrom"])
        sig_a = wc / (effective_resolving_power(cfg, wc) * FWHM_FACTOR)
        ctx = star_ctx[st]
        exps = ctx["exps"]
        in_dvs = [e["planet_orbital_rv_kms"] for e in exps if e["phase_window"] == "IN_WINDOW"]
        sdv = sorted(in_dvs)
        if len(sdv) < 3 or (sdv[-1] - sdv[0]) < 80.0 or min(b - a for a, b in zip(sdv, sdv[1:])) < 40.0:
            # Test spanning dispersed high-Kp orbital phases (prevents duplicate-phase clumps in T_DIFF benchmark)
            in_dvs = [-150.0, -45.0, 60.0, 165.0]
        w_win = wc + np.arange(-400, 401) * step_a
        n_in = len(in_dvs)
        sigma_px = 0.01
        amp = 7.5 * sigma_px
        w_planet0 = wc + float(rng_kep.uniform(-1.5, 1.5))
        unsh_r = np.zeros((n_in, len(w_win)))
        dedop_r = np.zeros((n_in, len(w_win)))
        for ei, dv in enumerate(in_dvs):
            w_sh = planet_rest_to_bary_wave(np.array([w_planet0]), 0.0, dv)[0]
            prof_sh = amp * np.exp(-0.5 * ((w_win - w_sh) / sig_a) ** 2)
            noise_i = sigma_px * rng_kep.standard_normal(len(w_win))
            unsh_r[ei] = prof_sh + noise_i
            dedop_r[ei] = amp * np.exp(-0.5 * ((w_win - w_planet0) / sig_a) ** 2) + noise_i
        out_r = sigma_px * rng_kep.standard_normal(len(w_win)) / math.sqrt(max(1, n_in))
        tr = build_and_scan_transit_channels(w_win, unsh_r, 1.0 + unsh_r, dedop_r, 1.0 + dedop_r, out_r, cfg)
        td_ok = any(check_channel_lsf_gate(c, "T_DIFF", cfg) for c in tr["tdiff_cands"])
        kp_ok = any(check_channel_lsf_gate(c, "K_PLANET", cfg) for c in tr["kplanet_cands"])
        kep_rows.append({
            "trial_id": kid, "instrument": inst, "star": st, "center_wave_a": wc,
            "tdiff_uncomp_recovered": td_ok, "kplanet_dedop_recovered": kp_ok,
        })

    # 3) 216 G4/G5 Detector Calibration Trials (72 TRUE_LSF_LASER, 72 COSMIC_RAY_HOT_PIXEL, 72 M_DWARF_PLATEAU_CORE)
    rng_g45 = np.random.default_rng(202609103)
    g45_rows: list[dict[str, Any]] = []
    inst_band_pairs = [
        ("ESO_XSHOOTER_3ARM", 5450.0, 0.2),
        ("ESO_XSHOOTER_3ARM", 15500.0, 0.6),
        ("ESO_FEROS", 5320.0, 0.03),
        ("ESO_FEROS", 6328.0, 0.03),
        ("ESO_GIRAFFE_HR", 5250.0, 0.05),
        ("ESO_GIRAFFE_HR", 6260.0, 0.05),
    ]
    gid = 0
    for cls in ("TRUE_LSF_LASER", "COSMIC_RAY_HOT_PIXEL", "M_DWARF_PLATEAU_CORE"):
        for r_i in range(72):
            gid += 1
            inst, wc, dw = inst_band_pairs[r_i % len(inst_band_pairs)]
            cfg = get_inst_config(inst)
            sig_a = wc / (effective_resolving_power(cfg, wc) * FWHM_FACTOR)
            w = wc + np.arange(-80, 81) * dw
            off = float(rng_g45.uniform(-0.12 * dw, 0.12 * dw))
            w_t = wc + off
            noise = 0.008 * rng_g45.standard_normal(len(w))
            if cls == "TRUE_LSF_LASER":
                sig = 0.45 * np.exp(-0.5 * ((w - w_t) / sig_a) ** 2)
            elif cls == "COSMIC_RAY_HOT_PIXEL":
                sig = np.zeros_like(w)
                sig[80] = 0.70
            else:
                # Broad non-LSF plateau (FWHM ~ 5x instrument LSF -> high far_wing_34_ratio & wide wings)
                sig = 0.35 * np.exp(-0.5 * ((w - w_t) / (4.5 * sig_a)) ** 2)
            p0 = {"arm": "A0", "order": 0, "native_pixel": 80, "wave": w, "flux_a": 1.0 + sig + noise,
                  "ref_norm_a": np.ones_like(w), "err_a": np.full_like(w, 0.008), "dq": np.zeros(len(w), dtype=int), "target_wave_a": w_t}
            patches = [p0]
            if inst == "ESO_XSHOOTER_3ARM" and wc < 10200.0:
                dw2 = 0.2
                w2 = wc + np.arange(-80, 81) * dw2
                noise2 = 0.008 * rng_g45.standard_normal(len(w2))
                if cls == "TRUE_LSF_LASER":
                    sig2 = 0.45 * np.exp(-0.5 * ((w2 - w_t) / sig_a) ** 2)
                elif cls == "COSMIC_RAY_HOT_PIXEL":
                    sig2 = np.zeros_like(w2)
                    sig2[80] = 0.70
                else:
                    sig2 = 0.35 * np.exp(-0.5 * ((w2 - w_t) / (4.5 * sig_a)) ** 2)
                patches.append({"arm": "A1", "order": 1, "native_pixel": 80, "wave": w2, "flux_a": 1.0 + sig2 + noise2,
                                "ref_norm_a": np.ones_like(w2), "err_a": np.full_like(w2, 0.008), "dq": np.zeros(len(w2), dtype=int), "target_wave_a": w_t})
            res = evaluate_gates_g3_g4_g5_v42(patches, "CAL", "T", w_t, cfg)
            g45_rows.append({
                "trial_id": gid, "trial_class": cls, "instrument": inst, "center_wave_a": wc,
                "g4_pass": bool(res["g4_pass"]), "g5_pass": bool(res["g5_pass"]),
                "g45_pass": bool(res["g4_pass"] and res["g5_pass"]),
                "g4_reason": res["g4_reason"], "g5_reason": res["g5_reason"],
            })

    # 4) 8/8 X-Shooter Dichroic Dual-Arm Coincidence Verification (4 UVB+VIS @ 5450 A + 4 VIS+NIR @ 10070 A)
    rng_xsh = np.random.default_rng(202609104)
    cfg_xsh = get_inst_config("ESO_XSHOOTER_3ARM")
    xsh_records = []
    for k_idx, (pair_lbl, wc, dw0, dw1) in enumerate([
        ("UVB+VIS", 5445.0, 0.2, 0.2), ("UVB+VIS", 5460.0, 0.2, 0.2),
        ("UVB+VIS", 5480.0, 0.2, 0.2), ("UVB+VIS", 5510.0, 0.2, 0.2),
        ("VIS+NIR", 10055.0, 0.2, 0.6), ("VIS+NIR", 10085.0, 0.2, 0.6),
        ("VIS+NIR", 10125.0, 0.2, 0.6), ("VIS+NIR", 10160.0, 0.2, 0.6),
    ]):
        sig_a = wc / (effective_resolving_power(cfg_xsh, wc) * FWHM_FACTOR)
        w0 = wc + np.arange(-80, 81) * dw0
        w1 = wc + np.arange(-80, 81) * dw1
        p0 = {"arm": pair_lbl.split("+")[0], "order": 0 if "UVB" in pair_lbl else 1, "native_pixel": 80, "wave": w0,
              "flux_a": 1.0 + 0.008 * rng_xsh.standard_normal(len(w0)) + 0.45 * np.exp(-0.5 * ((w0 - wc) / sig_a) ** 2),
              "ref_norm_a": np.ones_like(w0), "err_a": np.full_like(w0, 0.008), "dq": np.zeros(len(w0), dtype=int), "target_wave_a": wc}
        p1_dual = {"arm": pair_lbl.split("+")[1], "order": 1 if "UVB" in pair_lbl else 2, "native_pixel": 80, "wave": w1,
                   "flux_a": 1.0 + 0.008 * rng_xsh.standard_normal(len(w1)) + 0.45 * np.exp(-0.5 * ((w1 - wc) / sig_a) ** 2),
                   "ref_norm_a": np.ones_like(w1), "err_a": np.full_like(w1, 0.008), "dq": np.zeros(len(w1), dtype=int), "target_wave_a": wc}
        p1_single = {**p1_dual, "flux_a": 1.0 + 0.008 * rng_xsh.standard_normal(len(w1))}
        rd = evaluate_gates_g3_g4_g5_v42([p0, p1_dual], f"XSH_DUAL_{k_idx+1}", "T", wc, cfg_xsh)
        rs = evaluate_gates_g3_g4_g5_v42([p0, p1_single], f"XSH_SGL_{k_idx+1}", "T", wc, cfg_xsh)
        xsh_records.append({
            "trial_id": k_idx + 1, "overlap_zone": pair_lbl, "center_wave_a": wc,
            "dual_arm_g4_pass": bool(rd["g4_pass"]),
            "dual_arm_g5_pass": bool(rd["g5_pass"]),
            "single_arm_only_g4_pass": bool(rs["g4_pass"]),
            "single_arm_g4_reason": rs["g4_reason"],
        })
    xsh_dual_sum = {
        "n_tested": len(xsh_records),
        "dual_arm_pass_count": sum(1 for r in xsh_records if r["dual_arm_g4_pass"] and r["dual_arm_g5_pass"]),
        "single_arm_vetoed_count": sum(1 for r in xsh_records if (not r["single_arm_only_g4_pass"]) and r["single_arm_g4_reason"] == "XSHOOTER_SINGLE_ARM_DETECTOR_ARTIFACT"),
        "records": xsh_records,
    }

    # 5) 240 G6 Sparse vs Dense Calibration Trials
    rng_g6 = np.random.default_rng(202609105)
    g6_rows: list[dict[str, Any]] = []
    for tid_g6 in range(1, 241):
        mode_g6 = ("TRUE_ASTROP_UNIQUE", "STATIONARY_TELLURIC_2STAR", "SAME_STAR_STATIONARY")[ (tid_g6 - 1) % 3 ]
        inst = ("ESO_XSHOOTER_3ARM", "ESO_FEROS", "ESO_GIRAFFE_HR")[ (tid_g6 - 1) % 3 ]
        cfg = get_inst_config(inst)
        wt = 5891.0 + float(rng_g6.uniform(-50.0, 50.0))
        berv_t = 12.0
        atlas = []
        if mode_g6 == "STATIONARY_TELLURIC_2STAR":
            atlas = [{"star": "OTH1", "dp_id": "D1", "berv_kms": -5.0, "topo_wave_a": wt, "native_order": 1, "native_px": 500},
                     {"star": "OTH2", "dp_id": "D2", "berv_kms": 18.0, "topo_wave_a": wt, "native_order": 2, "native_px": 900}]
            exp_ok = False
        elif mode_g6 == "SAME_STAR_STATIONARY":
            atlas = [{"star": "TARG", "dp_id": "D_OLD", "berv_kms": -12.0, "topo_wave_a": wt, "native_order": 0, "native_px": 400}]
            exp_ok = False
        else:
            atlas = [{"star": "OTH1", "dp_id": "D1", "berv_kms": -5.0, "topo_wave_a": wt + 5.0, "native_order": 1, "native_px": 600}]
            exp_ok = True
        g6s = evaluate_gate_g6_v36_sparse("TARG", "D_NEW", berv_t, wt, 0, 400, 12.0, atlas, cfg, "T")
        g6_rows.append({
            "trial_id": tid_g6, "instrument": inst, "scenario": mode_g6,
            "expected_g6_pass": exp_ok, "g6_v36_sparse_pass": bool(g6s["g6_pass"]),
            "g6_reason": g6s["g6_reason"],
        })

    # 6) 486 Comb V4.1 Calibration Trials (162 TRUE_6TOOTH_STELLAR_COMB, 162 DENSE_MOLECULAR_FOREST, 162 TOPO_TELLURIC_OR_BG_COMB)
    rng_comb = np.random.default_rng(202609106)
    comb_cal_rows: list[dict[str, Any]] = []
    cid_c = 0
    comb_windows = [
        ("ESO_XSHOOTER_3ARM", "XSH_VIS", 6500.0, 6520.0, 0.25),
        ("ESO_FEROS", "FEROS_RED", 6400.0, 6420.0, 0.03),
        ("ESO_GIRAFFE_HR", "GIRAFFE_HR13", 6200.0, 6220.0, 0.05),
    ]
    c_aghz = C_ANGSTROM_GHZ
    for c_idx in range(486):
        cid_c += 1
        cls = ("TRUE_6TOOTH_STELLAR_COMB", "DENSE_MOLECULAR_FOREST", "TOPO_TELLURIC_OR_BG_COMB")[c_idx % 3]
        inst, band_id, wlo, whi, step_c = comb_windows[(c_idx // 3) % len(comb_windows)]
        cfg = get_inst_config(inst)
        w_c = np.arange(wlo, whi, step_c, dtype=np.float64)
        sig_grid = np.full_like(w_c, 0.01)
        noise_r = 0.01 * rng_comb.standard_normal(len(w_c))
        noise_t = 0.01 * rng_comb.standard_normal(len(w_c))
        dnu = float(cfg["comb_spacings_ghz"][-1])
        win_obj = [{"band": band_id, "lo_a": float(wlo), "hi_a": float(whi)}]
        nu0 = 0.5 * (c_aghz / wlo + c_aghz / whi) - 2.5 * dnu
        teeth_w = c_aghz / (nu0 + dnu * np.arange(6, dtype=np.float64))
        w_m = float(exact_median_1d(teeth_w))
        sig_a = w_m / (effective_resolving_power(cfg, w_m) * FWHM_FACTOR)
        tooth_snr = 5.0
        y_sig = np.zeros_like(w_c)
        yt_sig = np.zeros_like(w_c)
        if cls == "TRUE_6TOOTH_STELLAR_COMB":
            tooth_snr = 4.6 + 0.5 * ((c_idx // 9) % 3)
            for wt in teeth_w:
                y_sig += (tooth_snr * 0.01) * np.exp(-0.5 * ((w_c - wt) / sig_a) ** 2)
                yt_sig += (0.2 * tooth_snr * 0.01) * np.exp(-0.5 * ((w_c - (wt * 1.00012)) / sig_a) ** 2)
        elif cls == "DENSE_MOLECULAR_FOREST":
            # Dense unresolved forest: crowded every ~0.80*FWHM across the tooth span -> V4 triggers, V4.1 vetoes cleanly!
            tooth_snr = 5.0
            fwhm_a = sig_a * FWHM_FACTOR
            forest_w = np.arange(float(teeth_w.min()) - 2.0, float(teeth_w.max()) + 2.0, max(step_c * 2.0, 0.80 * fwhm_a))
            for wt in forest_w:
                y_sig += 0.055 * np.exp(-0.5 * ((w_c - wt) / sig_a) ** 2)
            for wt in teeth_w:
                y_sig += 0.055 * np.exp(-0.5 * ((w_c - wt) / sig_a) ** 2)
            yt_sig = 0.2 * y_sig
        else:
            tooth_snr = 5.0
            for wt in teeth_w:
                y_sig += 0.055 * np.exp(-0.5 * ((w_c - wt) / sig_a) ** 2)
                yt_sig += 0.110 * np.exp(-0.5 * ((w_c - wt) / sig_a) ** 2)

        y_r = y_sig + noise_r
        fn_r = 1.0 + y_r
        y_t = yt_sig + noise_t
        h_v4, _ = scan_frequency_comb_v4(w_c, y_r, sig_grid, fn_r, np.ones_like(w_c), np.zeros(len(w_c), dtype=bool), y_t, sig_grid, win_obj, [band_id], cfg)
        h_v41, _ = scan_frequency_comb_v4_1(w_c, y_r, sig_grid, fn_r, np.ones_like(w_c), np.zeros(len(w_c), dtype=bool), y_t, sig_grid, win_obj, [band_id], cfg)
        comb_cal_rows.append({
            "trial_id": cid_c, "trial_class": cls, "instrument": inst, "band": band_id,
            "tooth_snr_inj": tooth_snr, "comb_v4_hit": len(h_v4) > 0, "comb_v41_hit": len(h_v41) > 0,
        })

    cal_summary = {
        "total_trials": len(inj_rows) + len(kep_rows) + len(g45_rows) + len(g6_rows) + len(comb_cal_rows),
        "channel_t_ge_8sigma": round(sum(1 for r in inj_rows if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH" and r["sigma_mult"] >= 8.0 and r["recovered"]) / max(1, sum(1 for r in inj_rows if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH" and r["sigma_mult"] >= 8.0)), 4),
        "channel_p_ge_8sigma": round(sum(1 for r in inj_rows if r["mode"] == "CHANNEL_P_STATIC_COADD" and r["sigma_mult"] >= 8.0 and r["recovered"]) / max(1, sum(1 for r in inj_rows if r["mode"] == "CHANNEL_P_STATIC_COADD" and r["sigma_mult"] >= 8.0)), 4),
        "keplerian_tdiff_ge_6p5sigma": round(sum(1 for r in kep_rows if r["tdiff_uncomp_recovered"]) / len(kep_rows), 4),
        "keplerian_kplanet_ge_6p5sigma": round(sum(1 for r in kep_rows if r["kplanet_dedop_recovered"]) / len(kep_rows), 4),
        "g45_true_laser_pass": round(sum(1 for r in g45_rows if r["trial_class"] == "TRUE_LSF_LASER" and r["g45_pass"]) / 72.0, 4),
        "g5_cosmic_hotpx_rejection": round(sum(1 for r in g45_rows if r["trial_class"] == "COSMIC_RAY_HOT_PIXEL" and not r["g5_pass"]) / 72.0, 4),
        "g5_plateau_rejection": round(sum(1 for r in g45_rows if r["trial_class"] == "M_DWARF_PLATEAU_CORE" and not r["g5_pass"]) / 72.0, 4),
        "g6_sparse_accuracy": round(sum(1 for r in g6_rows if r["g6_v36_sparse_pass"] == r["expected_g6_pass"]) / len(g6_rows), 4),
        "comb_v41_6tooth_ge_3p8sigma_recovery": round(sum(1 for r in comb_cal_rows if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and r["comb_v41_hit"]) / 162.0, 4),
        "comb_v41_dense_forest_fpr": round(sum(1 for r in comb_cal_rows if r["trial_class"] == "DENSE_MOLECULAR_FOREST" and r["comb_v41_hit"]) / 162.0, 4),
        "comb_v4_dense_forest_fpr": round(sum(1 for r in comb_cal_rows if r["trial_class"] == "DENSE_MOLECULAR_FOREST" and r["comb_v4_hit"]) / 162.0, 4),
        "comb_v41_topo_comb_fpr": round(sum(1 for r in comb_cal_rows if r["trial_class"] == "TOPO_TELLURIC_OR_BG_COMB" and r["comb_v41_hit"]) / 162.0, 4),
    }

    return inj_rows, comp_rows, kep_rows, g45_rows, g6_rows, comb_cal_rows, cal_summary, xsh_dual_sum


# ---------------------------------------------------------------------------
# Stage B: Main Science + Synthesis Pipeline (24 deterministic files)
# ---------------------------------------------------------------------------

def run_stage_b(bundle: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    snap_v4 = json.loads((WS / "PRIOR_V4_1_PHASES_SNAPSHOT.json").read_text(encoding="utf-8"))
    snap_mm = json.loads((WS / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json").read_text(encoding="utf-8"))
    orb_doc = json.loads((WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))

    exposures_raw: list[dict[str, Any]] = bundle["exposures"]
    assert len(exposures_raw) == 156

    exps_by_star: dict[str, list[dict[str, Any]]] = defaultdict(list)
    exps_by_inst: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in exposures_raw:
        exps_by_star[e["star"]].append(e)
        exps_by_inst[e["instrument"]].append(e)

    print(f"Stage B ({out_dir}): unpacking & measuring RVs for {len(exposures_raw)} exposures across 3 ESO spectrographs...", flush=True)

    prov_rows: list[dict[str, Any]] = []
    rv_anchor_rows: list[dict[str, Any]] = []
    bench_rows: list[dict[str, Any]] = []
    v2_by_dp: dict[str, int] = {}
    exp_unpacked: dict[str, dict[str, Any]] = {}
    exp_rv_kms: dict[str, float] = {}
    exp_rv_meta: dict[str, dict[str, Any]] = {}
    exp_v2_cnt: dict[str, int] = {}

    for e in exposures_raw:
        dp = e["dp_id"]
        inst = e["instrument"]
        cfg = get_inst_config(inst, float(e["resolving_power"]))
        unp = _unpack_exposure_spectrum(e, cfg)
        exp_unpacked[dp] = unp

        rv_m, a_rows, _ = measure_exposure_stellar_rv(unp["w_bary"], unp["fn"], float(e["prior_rv_kms"]), cfg)
        rv_val = float(rv_m["empirical_rv_kms"])
        exp_rv_kms[dp] = rv_val
        exp_rv_meta[dp] = rv_m
        v2_cnt = _compute_legacy_v2_count(unp["w_bary"], unp["fn"], cfg)
        v2_by_dp[dp] = v2_cnt
        exp_v2_cnt[dp] = v2_cnt

        for ar in a_rows:
            rv_anchor_rows.append({
                "dp_id": dp, "instrument": inst, "star": e["star"],
                "anchor_id": ar["anchor_id"], "species": ar["species"], "lab_wave_A": ar["lab_wave_A"],
                "status": ar["status"], "n_samples": ar["n_samples"], "best_rv_kms": ar["best_rv_kms"],
                "rel_depth": ar["rel_depth"], "min_sse": ar["min_sse"],
            })

        prov_rows.append({
            "dp_id": dp, "instrument": inst, "star": e["star"], "role": e["role"],
            "grating": e["grating"], "resolving_power": round(float(e["resolving_power"]), 1),
            "mjd_obs": e["mjd_obs"], "t_exptime_s": e["t_exptime_s"],
            "specsys": e["specsys"], "berv_kms": e["berv_kms"], "berv_src": e["berv_src"],
            "n_arms": len(unp["arms"]), "n_pixels_merged": len(unp["w_bary"]),
            "wave_min_a": round(float(np.min(unp["w_bary"])), 2),
            "wave_max_a": round(float(np.max(unp["w_bary"])), 2),
            "empirical_rv_kms": round(rv_val, 3),
            "n_clean_anchors": rv_m["n_clean_anchors"],
            "header_gate": "PASS" if len(unp["w_bary"]) >= 500 else "FAIL",
        })

    # Re-grid per instrument onto common stellar-rest wavelength grid + build kNN templates
    rest_grid_by_inst: dict[str, np.ndarray] = {}
    for inst in ("ESO_XSHOOTER_3ARM", "ESO_FEROS", "ESO_GIRAFFE_HR"):
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
            "role": exps[0]["role"], "subrole": exps[0]["subrole"],
            "dist_pc": exps[0]["dist_pc"], "teff_k": exps[0]["teff_k"], "mh_dex": exps[0]["mh_dex"],
            "prior_rv_kms": exps[0]["prior_rv_kms"], "empirical_rv_med_kms": round(rv_med, 3),
            "empirical_rv_mad_kms": round(rv_mad, 3), "n_exposures": len(exps),
        })

        mat = np.full((len(exps), len(rg)), np.nan, dtype=np.float64)
        for i_e, e in enumerate(exps):
            unp = exp_unpacked[e["dp_id"]]
            rv_e = exp_rv_kms[e["dp_id"]]
            w_r = unp["w_bary"] / (1.0 + rv_e / C_KMS)
            fin = np.isfinite(w_r) & np.isfinite(unp["fn"])
            if int(fin.sum()) >= 50:
                wf, ff = w_r[fin], unp["fn"][fin]
                interp = np.interp(rg, wf, ff, left=np.nan, right=np.nan)
                # Mask large wavelength gaps (e.g. X-shooter telluric blackout or GIRAFFE narrow setting!)
                idx_hi = np.searchsorted(wf, rg)
                valid_in = (rg >= wf[0]) & (rg <= wf[-1])
                step_thresh = 25.0 if inst == "ESO_XSHOOTER_3ARM" else 5.0
                safe = np.zeros_like(rg, dtype=bool)
                vi = np.flatnonzero(valid_in)
                if len(vi):
                    i_r = np.clip(idx_hi[vi], 1, len(wf) - 1)
                    gap = wf[i_r] - wf[i_r - 1]
                    safe[vi] = gap <= step_thresh
                mat[i_e] = np.where(safe, interp, np.nan)
        star_exp_fn_mat[st] = mat
        with warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore", RuntimeWarning)
            med_coadd = np.nanmedian(mat, axis=0)
        star_norm_coadds[inst][st] = med_coadd
        star_meta_by_inst[inst][st] = {
            "instrument": inst, "teff_k": exps[0]["teff_k"], "mh_dex": exps[0]["mh_dex"],
        }

    print("  Building kNN stellar templates & scanning Channel T/P...", flush=True)
    star_templates: dict[str, np.ndarray] = {}
    star_tpl_meta: dict[str, dict[str, Any]] = {}
    for inst in ("ESO_XSHOOTER_3ARM", "ESO_FEROS", "ESO_GIRAFFE_HR"):
        cfg = get_inst_config(inst)
        tpls, tmeta = construct_knn_stellar_templates(star_meta_by_inst[inst], star_norm_coadds[inst], cfg)
        star_templates.update(tpls)
        star_tpl_meta.update(tmeta)

    # Augment sparse GIRAFFE HR10/HR11 grating pools (<=1 GIRAFFE peer) with overlapping peers & full-band FEROS catalog references
    cfg_gir = get_inst_config("ESO_GIRAFFE_HR")
    rg_gir = rest_grid_by_inst["ESO_GIRAFFE_HR"]
    rg_fer = rest_grid_by_inst["ESO_FEROS"]
    for st in sorted(star_norm_coadds["ESO_GIRAFFE_HR"].keys()):
        coadd_st = star_norm_coadds["ESO_GIRAFFE_HR"][st]
        fin_st = np.isfinite(coadd_st)
        n_fin_st = max(1, int(fin_st.sum()))
        cov_frac = int(np.sum(np.isfinite(star_templates[st]) & fin_st)) / n_fin_st
        if cov_frac < 0.80:
            aug_coadds: dict[str, np.ndarray] = {st: coadd_st}
            aug_meta: dict[str, dict[str, Any]] = {st: dict(star_meta_by_inst["ESO_GIRAFFE_HR"][st])}
            for ost, ocoadd in star_norm_coadds["ESO_GIRAFFE_HR"].items():
                if ost != st and (int(np.sum(fin_st & np.isfinite(ocoadd))) / n_fin_st) >= 0.55:
                    aug_coadds[ost] = ocoadd
                    aug_meta[ost] = dict(star_meta_by_inst["ESO_GIRAFFE_HR"][ost])
            for fst, fcoadd in star_norm_coadds["ESO_FEROS"].items():
                fin_f = np.isfinite(fcoadd)
                if int(fin_f.sum()) >= 50:
                    ref_key = f"__FEROS_REF_{fst}"
                    aug_coadds[ref_key] = np.interp(rg_gir, rg_fer[fin_f], fcoadd[fin_f], left=np.nan, right=np.nan)
                    aug_meta[ref_key] = {**star_meta_by_inst["ESO_FEROS"][fst], "instrument": "ESO_GIRAFFE_HR"}
            aug_tpls, aug_tmeta = construct_knn_stellar_templates(aug_meta, aug_coadds, cfg_gir)
            star_templates[st] = aug_tpls[st]
            star_tpl_meta[st] = aug_tmeta[st]

    # Compute residuals per exposure + scan Channel T and Channel P + build sparse telluric atlas
    searched_by_inst: dict[str, dict[str, int]] = {
        inst: {"T": 0, "P": 0, "T_DIFF": 0, "K_PLANET": 0, "COMB_CONFIGS": 0}
        for inst in ("ESO_XSHOOTER_3ARM", "ESO_FEROS", "ESO_GIRAFFE_HR")
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

        # Channel T per exposure
        for i_e, e in enumerate(exps):
            dp = e["dp_id"]
            cfg_e = get_inst_config(inst, float(e["resolving_power"]))
            t_cands, t_bins, t_seeds = scan_single_exposure_residual_lsf(
                rg, resids_mat[i_e], cfg_e, "T", flux_norm_for_f1=fn_mat[i_e]
            )
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
                    sparse_atlas_by_inst[inst].append({
                        "star": st, "dp_id": dp, "berv_kms": berv_e,
                        "topo_wave_a": wt, "native_order": None, "native_px": None,
                    })
                    raw_cands.append({
                        "instrument": inst, "channel": "T", "role": e["role"], "star": st, "dp_id": dp,
                        "exp": e, "rv_kms": rv_e, "berv_kms": berv_e,
                        "stellar_rest_wave_a": wr, "bary_wave_a": wb, "topo_wave_a": wt, "fit": c,
                    })
            bench_rows.append({
                "dp_id": dp, "instrument": inst, "star": st, "role": e["role"],
                "v1_raw_peaks": t_seeds + v2_by_dp[dp], "v2_legacy_false_alarms": v2_by_dp[dp],
                "v3_channel_t_lsf_hits": t_lsf_n, "searched_bins": t_bins,
            })

        # Channel P multi-epoch coadd
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
                raw_cands.append({
                    "instrument": inst, "channel": "P", "role": rep_e["role"], "star": st, "dp_id": rep_e["dp_id"],
                    "exp": rep_e, "rv_kms": rv_med, "berv_kms": berv_med,
                    "stellar_rest_wave_a": wr, "bary_wave_a": wb, "topo_wave_a": wt, "fit": c,
                })

        star_ctx[st] = {
            "instrument": inst, "exps": exps, "rest_grid": rg, "fn_mat": fn_mat,
            "resids_mat": resids_mat, "template": tpl, "resid_p": resid_p,
            "rv_med": rv_med, "berv_med": berv_med,
        }

    # Orbital Campaigns (#91-#100): Channel T_DIFF & Keplerian De-Doppler K_PLANET
    print("  Scanning 10 orbital campaigns (#91-#100) T_DIFF & K_PLANET...", flush=True)
    orb_rows: list[dict[str, Any]] = []
    orb_cand_counts: dict[str, dict[str, int]] = {}
    for idx_o, (st, camp) in enumerate(orb_doc["campaigns"].items(), 91):
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
            dedop_r[j] = np.interp(rg, w_p, unsh_r[j], left=np.nan, right=np.nan)
            dedop_fn[j] = np.interp(rg, w_p, unsh_fn[j], left=np.nan, right=np.nan)

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
                    raw_cands.append({
                        "instrument": inst, "channel": ch_name, "role": rep_e["role"], "star": st, "dp_id": rep_e["dp_id"],
                        "exp": rep_e, "rv_kms": rv_med, "berv_kms": berv_med,
                        "stellar_rest_wave_a": wr, "bary_wave_a": wb, "topo_wave_a": wt, "fit": c,
                    })

        orb_cand_counts[st] = {"tdiff": 0, "kplanet": 0}
        orb_rows.append({
            "campaign_number": idx_o, "star": st, "common_name": camp["common_name"],
            "instrument": inst, "role": camp["role"], "planet_name": camp["planet_name"],
            "transiting": camp["transiting"], "null_orbital": camp["null_orbital"],
            "orbper_days": camp["orbper_days"], "kp_kms": camp["kp_kms"],
            "orbital_dv_span_kms": camp["orbital_dv_span_kms"],
            "n_in_window": camp["n_in_window"], "n_out_of_window": camp["n_out_of_window"],
            "tdiff_lsf_cands": n_td, "kplanet_lsf_cands": n_kp,
            "qualified_tdiff_candidates": 0, "qualified_kplanet_candidates": 0, "verified_eti": 0,
        })

    # Apply Automated Physics Vetting Gates G1..G6 + Forensic Audit
    print(f"  Vetting {len(raw_cands)} raw LSF-gated candidates through G2_V42..G6_V36...", flush=True)
    dense_atlas_by_inst = sparse_atlas_by_inst
    ledger_rows: list[dict[str, Any]] = []
    forensic_recs: list[dict[str, Any]] = []
    forensic_cls_cnt: Counter[str] = Counter()

    for idx_c, rc in enumerate(raw_cands, 1):
        inst = rc["instrument"]
        e = rc["exp"]
        cfg = get_inst_config(inst, float(e["resolving_power"]))
        wb = rc["bary_wave_a"]
        wr = rc["stellar_rest_wave_a"]
        g2 = evaluate_gate_g2_airglow(wb, rc["berv_kms"], cfg)

        st = rc["star"]
        rg = star_ctx[st]["rest_grid"]
        tpl = star_ctx[st]["template"]
        unp = exp_unpacked[rc["dp_id"]]
        patches = _extract_native_patches_for_cand(unp["arms"], tpl, rg, wb, rc["rv_kms"])
        g345 = evaluate_gates_g3_g4_g5_v42(patches, rc["dp_id"], rc["channel"], wr, cfg)

        vshift = abs(float(rc["berv_kms"]))
        g6_d = evaluate_gate_g6_v35_dense(
            st, g2["topo_wave_a"], g345.get("primary_order"), g345.get("primary_native_px"),
            vshift, dense_atlas_by_inst[inst], cfg,
        )
        g6_s = evaluate_gate_g6_v36_sparse(
            st, rc["dp_id"], float(rc["berv_kms"]), g2["topo_wave_a"],
            g345.get("primary_order"), g345.get("primary_native_px"),
            vshift, sparse_atlas_by_inst[inst], cfg, channel=rc["channel"],
        )

        f1_ok = bool(rc["fit"]["f1_pass"])
        pre_g6 = bool(f1_ok and g2["g2_pass"] and g345["g3_pass"] and g345["g4_pass"] and g345["g5_pass"])
        qual = bool(pre_g6 and g6_s["g6_pass"])

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
        else:
            disp = "AUTO_QUALIFIED_FORENSIC_AUDIT"

        lrow = {
            "candidate_id": f"D091_C{idx_c:05d}", "instrument": inst, "channel": rc["channel"], "role": rc["role"],
            "star": st, "dp_id": rc["dp_id"], "fitted_wave_a": round(wr, 4), "stellar_rest_wave_a": round(wr, 4),
            "bary_wave_a": round(wb, 4), "topo_wave_a": round(g2["topo_wave_a"], 4),
            "snr_mid": round(float(rc["fit"]["snr_mid"]), 3), "snr_out": round(float(rc["fit"]["snr_out"]), 3),
            "cosine": round(float(rc["fit"]["cosine"]), 4), "fwhm_ratio": round(float(rc["fit"]["fwhm_ratio"]), 4),
            "target_fn_pk3": round(float(rc["fit"]["fn_pk3"]), 4),
            "g1_pass": f1_ok, "g2_pass": bool(g2["g2_pass"]), "g3_pass": bool(g345["g3_pass"]),
            "primary_order": g345.get("primary_order", ""), "primary_native_px": g345.get("primary_native_px", ""),
            "primary_native_fn_pk3": round(float(g345.get("primary_native_fn_pk3", 0.0)), 4),
            "primary_eta_1px": round(float(g345.get("primary_eta_1px", 0.0)), 4),
            "g4_pass": bool(g345["g4_pass"]), "g5_pass": bool(g345["g5_pass"]),
            "g5_cos11": round(float(g345.get("cos_1d_11px", 0.0)), 4),
            "g5_ipc_hotpx_ratio": round(float(g345.get("ipc_hotpx_ratio", 0.0)), 4),
            "g5_far_wing_ratio": round(float(g345.get("far_wing_34_ratio", 0.0)), 4),
            "pre_g6_qualified": pre_g6, "g6_v35_dense_pass": bool(g6_d["g6_v35_pass"]),
            "g6_pass": bool(g6_s["g6_pass"]),
            "g6_coincident_total_stars": int(g6_s["g6_coincident_total_stars"]),
            "g6_same_star_hits": int(g6_s["g6_same_star_stationary_hits"]),
            "qualified_v42_laser": qual, "final_disposition": disp,
        }
        ledger_rows.append(lrow)

        if qual:
            if rc["channel"] == "T_DIFF" and st in orb_cand_counts:
                orb_cand_counts[st]["tdiff"] += 1
            elif rc["channel"] == "K_PLANET" and st in orb_cand_counts:
                orb_cand_counts[st]["kplanet"] += 1
            frec = _forensic_classify(lrow, {"teff_k": e["teff_k"], "n_epochs": len(exps_by_star[st])})
            forensic_cls_cnt[frec["forensic_class"]] += 1
            forensic_recs.append(frec)

    for orow in orb_rows:
        oc = orb_cand_counts.get(orow["star"], {})
        orow["qualified_tdiff_candidates"] = oc.get("tdiff", 0)
        orow["qualified_kplanet_candidates"] = oc.get("kplanet", 0)

    # Comb V4 vs Comb V4.1 across 37 stars + All-Sky 358-Stack Sweep (D079-D091)
    print("  Scanning COMB_V4 vs COMB_V4_1 across 37 stars (All-Sky 358 stacks)...", flush=True)
    comb_payloads: list[tuple[str, str, float, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]] = []
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
        if inst in ("ESO_XSHOOTER_3ARM", "ESO_FEROS", "ESO_GIRAFFE_HR"):
            for al in GROUND_AIRGLOW_AND_TELLURIC_A:
                wa_r = float(al["wave_A"]) * (1.0 + ctx["berv_med"] / C_KMS) / (1.0 + ctx["rv_med"] / C_KMS)
                sky_mask |= np.abs(rg - wa_r) <= max(0.5, float(al["half_width_kms"]) * wa_r / C_KMS)
        t_mat = np.full((len(exps), len(rg)), np.nan)
        for ie, e in enumerate(exps):
            unp = exp_unpacked[e["dp_id"]]
            wt = unp["w_bary"] / (1.0 + float(e["berv_kms"]) / C_KMS)
            ft = np.isfinite(wt) & np.isfinite(unp["fn"])
            if int(ft.sum()) >= 50:
                t_mat[ie] = np.interp(rg, wt[ft], unp["fn"][ft] - 1.0, left=np.nan, right=np.nan)
        with warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore", RuntimeWarning)
            y_topo = np.nanmedian(t_mat, axis=0)
        comb_payloads.append((st, inst, float(exps[0]["resolving_power"]), rg, rp, fn_p, tpl, sky_mask, y_topo, mad_r))

    n_workers = min(4, os.cpu_count() or 1)
    comb_results_by_star: dict[str, tuple[int, list[dict[str, Any]], int]] = {}
    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        for st_res, n_v4, hits_v41, n_cfg in pool.map(_scan_comb_star_worker, comb_payloads):
            comb_results_by_star[st_res] = (n_v4, hits_v41, n_cfg)

    comb_star_rows: list[dict[str, Any]] = []
    comb_cand_rows: list[dict[str, Any]] = []
    comb_v4_tot, comb_v41_tot = 0, 0
    for st, exps in exps_by_star.items():
        inst = exps[0]["instrument"]
        n_v4, hv41, n_cfg = comb_results_by_star[st]
        searched_by_inst[inst]["COMB_CONFIGS"] += n_cfg
        comb_v4_tot += n_v4
        comb_v41_tot += len(hv41)
        comb_star_rows.append({
            "phase_id": "D091", "instrument": inst, "star": st, "role": exps[0]["role"],
            "teff_k": exps[0]["teff_k"], "n_exposures": len(exps),
            "comb_v4_candidates": n_v4, "comb_v41_candidates": len(hv41),
            "searched_configs": n_cfg, "verified_eti_combs": 0,
        })
        for ci, h in enumerate(hv41, 1):
            comb_cand_rows.append({
                "comb_id": f"D091_COMB_{st}_{ci}", "instrument": inst, "star": st, "role": exps[0]["role"],
                "band": h["band"], "dnu_ghz": h["dnu_ghz"], "nu0_ghz": h["nu0_ghz"],
                "wave0_a": h["wave0_a"], "wave_end_a": h["wave_end_a"],
                "s_comb": h["s_comb"], "topo_anti_ratio": h["topo_anti_ratio"],
                "n_qualifying_teeth": h["n_qualifying_teeth"],
                "off_tooth_crowding": h["off_tooth_crowding"], "intertooth_ratio": h["intertooth_ratio"],
            })

    allsky_comb_rows = list(snap_v4["allsky_comb_unified_d079_d090"]) + [
        {k: r[k] for k in snap_v4["allsky_comb_unified_d079_d090"][0].keys()}
        for r in comb_star_rows
    ]
    allsky_comb_cands = list(snap_v4["allsky_comb_candidates_d079_d090"]) + [
        {
            "allsky_comb_id": c["comb_id"], "band": c["band"], "dnu_ghz": c["dnu_ghz"],
            "instrument": c["instrument"], "intertooth_ratio": c["intertooth_ratio"],
            "n_qualifying_teeth": c["n_qualifying_teeth"], "nu0_ghz": c["nu0_ghz"],
            "off_tooth_crowding": c["off_tooth_crowding"], "phase_id": "D091",
            "role": c["role"], "s_comb": c["s_comb"], "star": c["star"],
            "topo_anti_ratio": c["topo_anti_ratio"], "wave0_a": c["wave0_a"], "wave_end_a": c["wave_end_a"],
        }
        for c in comb_cand_rows
    ]

    # Run all 2,697 synthetic calibration trials + 8/8 X-shooter Dual-Arm Coincidence tests
    print("  Running 2,697 calibration trials + 8/8 X-shooter dual-arm coincidence tests...", flush=True)
    inj_rows, comp_rows, kep_rows, g45_rows, g6_rows, comb_cal_rows, cal_sum, xsh_dual_sum = _run_all_calibrations(star_ctx)

    # 10 m Optical/NIR Photon-Beam EIRP Upper Limits across 127 Star-Bands
    print("  Computing 127 star-band 10 m EIRP upper limits (with physical CGS guard)...", flush=True)
    ul_rows: list[dict[str, Any]] = []
    star_ul_best: dict[str, dict[str, Any]] = {}
    star_band_map: dict[str, dict[str, float]] = defaultdict(dict)

    for st, exps in exps_by_star.items():
        ctx = star_ctx[st]
        inst = ctx["instrument"]
        r_pow = float(exps[0]["resolving_power"])
        cfg = get_inst_config(inst, r_pow)
        rg = ctx["rest_grid"]
        e0 = exps[0]
        dist_pc = float(e0["dist_pc"])
        teff_k = float(e0["teff_k"])
        phot_g = float(e0["phot_g_mag"])
        mass_msun = float(e0["stellar_mass_msun"])
        r_star = max(0.015, mass_msun ** 0.8) if "LAWD37" != st else 0.014

        for band in get_calibration_bands(inst):
            bid = band["band_id"]
            wc_rest = float(band["center_wave_A"])
            half_w = 25.0 if inst == "ESO_GIRAFFE_HR" else max(25.0, 0.035 * wc_rest)
            m_b = np.abs(rg - wc_rest) <= half_w
            vals = ctx["resids_mat"][:, m_b]
            fin_b = vals[np.isfinite(vals)]
            if len(fin_b) < 25:
                continue

            mad_b = max(0.001, float(exact_mad_1d(fin_b)))
            amp_8s = 8.0 * mad_b

            # Direct flux continuum extraction for X-shooter (guarded against archival arbitrary flux scaling)
            direct_cgs = None
            anchor_used = "GAIA_G_PLANCK_CGS"
            planck_flam = gaia_g_planck_flam_cgs(wc_rest, phot_g, teff_k)
            if inst == "ESO_XSHOOTER_3ARM":
                wb_nom = wc_rest * (1.0 + ctx["rv_med"] / C_KMS)
                unp0 = exp_unpacked[e0["dp_id"]]
                mf = np.abs(unp0["w_bary"] - wb_nom) <= 40.0
                ff_vals = unp0["flux_cgs"][mf]
                ff_fin = ff_vals[np.isfinite(ff_vals) & (ff_vals > 0.0)]
                if len(ff_fin) >= 15:
                    med_f = float(exact_median_1d(ff_fin))
                    if 0.05 * planck_flam <= med_f <= 20.0 * planck_flam:
                        direct_cgs = med_f
                        anchor_used = "ESO_XSHOOTER_DIRECT_CGS"

            lim = compute_photon_beam_upper_limit(
                wc_rest, amp_8s, teff_k, dist_pc, r_star, anchor_used,
                effective_resolving_power(cfg, wc_rest),
                direct_flam_cgs=direct_cgs, phot_g_mag=phot_g,
            )
            wb_row = wc_rest * (1.0 + ctx["rv_med"] / C_KMS)
            urow = {
                "instrument": inst, "star": st, "common_name": e0["common_name"], "subrole": e0["subrole"],
                "panchromatic_bridge": e0["panchromatic_bridge"], "radio_mm_id": e0["radio_mm_id"],
                "within_10pc": e0["within_10pc"], "n_exoplanets": e0["n_exoplanets"],
                "has_transiting_planet": e0["has_transiting_planet"],
                "dist_pc": round(dist_pc, 5), "teff_k": round(teff_k, 1),
                "radiometric_anchor": anchor_used, "resolving_power": round(effective_resolving_power(cfg, wc_rest), 1),
                "band_id": bid, "wave_bary_a": round(wb_row, 3),
                "median_epoch_mad_rel": float(f"{mad_b:.6g}"),
                "amp_rel_8sigma_lim": float(f"{amp_8s:.6g}"),
                "fwhm_lsf_a": float(f"{lim['fwhm_lsf_a']:.6g}"),
                "ew_lim_mA": float(f"{lim['ew_lim_mA']:.6g}"),
                "continuum_flam_cgs": float(f"{lim['continuum_flam_cgs']:.6g}"),
                "flux_lim_erg_cm2_s": float(f"{lim['flux_lim_erg_cm2_s']:.6g}"),
                "l_iso_mw": float(f"{lim['l_iso_mw']:.6g}"),
                "p_beam_10m_w": float(f"{lim['p_beam_10m_w']:.6g}"),
                "p_beam_10m_kw": float(f"{lim['p_beam_10m_kw']:.6g}"),
            }
            ul_rows.append(urow)
            star_band_map[st][bid] = float(lim["p_beam_10m_kw"])
            prev = star_ul_best.get(st)
            if prev is None or float(lim["p_beam_10m_kw"]) < float(prev["p_beam_10m_kw"]):
                star_ul_best[st] = urow

    # Panchromatic 35-Bridge & 310-Star / 135 <10pc Synthesis
    print("  Assembling 35-star panchromatic bridges, 310-star synthesis & MM closure...", flush=True)
    regime_tag_map = {
        "ESO_XSHOOTER_3ARM": "XSHOOTER_3ARM_0p30_2p48um",
        "ESO_FEROS": "OPTICAL_FEROS",
        "ESO_GIRAFFE_HR": "OPTICAL_GIRAFFE_HR",
    }
    bridge_rows: list[dict[str, Any]] = list(snap_v4["d090_bridge_30star_rows"]) + list(snap_v4["newly_bridged_5star_prior_rows"])
    for ur in ul_rows:
        st = ur["star"]
        if exps_by_star[st][0]["panchromatic_bridge"]:
            wb = float(ur["wave_bary_a"])
            bridge_rows.append({
                "band_id": ur["band_id"], "common_name": ur["common_name"], "dist_pc": str(ur["dist_pc"]),
                "ew_lim_mA": str(ur["ew_lim_mA"]), "flux_lim_erg_cm2_s": str(ur["flux_lim_erg_cm2_s"]),
                "instrument": ur["instrument"], "l_iso_mw": str(ur["l_iso_mw"]),
                "p_beam_10m_kw": str(ur["p_beam_10m_kw"]), "p_beam_10m_w": str(ur["p_beam_10m_w"]),
                "phase_id": "D091", "spectral_regime": regime_tag_map[ur["instrument"]],
                "star": st, "wave_A": f"{wb:.6g}", "wave_um": f"{wb / 1e4:.6g}",
            })
    bridge_rows.sort(key=lambda r: (r["star"], float(r["wave_um"]), r["phase_id"], r["band_id"]))

    u_map: dict[str, dict[str, Any]] = {}
    for r in snap_v4["unified_280star_rows"]:
        nr = {k: r.get(k, "") for k in U310_COLS}
        nr["n_exposures_xshooter_3arm"] = "0"
        nr["min_xshooter_3arm_10m_kw"] = ""
        nr["n_exposures_feros_v42"] = "0"
        nr["min_feros_v42_10m_kw"] = ""
        nr["n_exposures_giraffe_hr"] = "0"
        nr["min_giraffe_hr_10m_kw"] = ""
        u_map[r["star"]] = nr

    cand_cnt_by_star = Counter(f["star"] for f in forensic_recs)
    for st, exps in exps_by_star.items():
        e0 = exps[0]
        inst = e0["instrument"]
        n_exp = len(exps)
        p_best = float(star_ul_best[st]["p_beam_10m_kw"])
        n_cand = cand_cnt_by_star[st]
        bmap = star_band_map[st]

        if st in u_map:
            ur = u_map[st]
            ur["phases"] = ur["phases"] + "+D091"
            if inst not in ur["instruments"]:
                ur["instruments"] = ur["instruments"] + "+" + inst
            ur["n_exposures_total"] = str(int(ur["n_exposures_total"]) + n_exp)
            ur["automated_qualified_candidates"] = str(int(ur["automated_qualified_candidates"]) + n_cand)
            cur_min = float(ur["min_panchromatic_10m_kw"]) if ur["min_panchromatic_10m_kw"] else 1e99
            ur["min_panchromatic_10m_kw"] = f"{min(cur_min, p_best):.8g}"
            if inst == "ESO_XSHOOTER_3ARM":
                ur["n_exposures_xshooter_3arm"] = str(n_exp)
                ur["min_xshooter_3arm_10m_kw"] = f"{p_best:.8g}"
                ur["n_exposures_optical"] = str(int(ur["n_exposures_optical"]) + n_exp)
                ur["n_exposures_nir_yjh"] = str(int(ur["n_exposures_nir_yjh"]) + n_exp)
                ur["n_exposures_kband"] = str(int(ur["n_exposures_kband"]) + n_exp)
                ur["n_exposures_nuv"] = str(int(ur["n_exposures_nuv"]) + n_exp)
                if "X5_15500" in bmap:
                    c15 = float(ur["p_1550nm_10m_kw"]) if ur["p_1550nm_10m_kw"] else 1e99
                    ur["p_1550nm_10m_kw"] = f"{min(c15, bmap['X5_15500']):.8g}"
                if "X6_20970" in bmap:
                    c20 = float(ur["p_2097nm_hoyag_10m_kw"]) if ur["p_2097nm_hoyag_10m_kw"] else 1e99
                    ur["p_2097nm_hoyag_10m_kw"] = f"{min(c20, bmap['X6_20970']):.8g}"
            elif inst == "ESO_GIRAFFE_HR":
                ur["n_exposures_giraffe_hr"] = str(n_exp)
                ur["min_giraffe_hr_10m_kw"] = f"{p_best:.8g}"
                ur["n_exposures_optical"] = str(int(ur["n_exposures_optical"]) + n_exp)
        else:
            p_opt = min([bmap[k] for k in bmap if k.startswith(("F", "G")) or k in ("X1_3600", "X2_5450", "X3_6800")], default=None)
            p_yjh = bmap.get("X5_15500")
            p_kb = bmap.get("X6_20970")
            p_nuv = bmap.get("X1_3600")
            u_map[st] = {
                "phases": "D091", "hemisphere": "SOUTH_PARANAL_LASILLA", "spectral_regime": regime_tag_map[inst],
                "instruments": inst, "star": st, "common_name": e0["common_name"], "role": e0["role"], "subrole": e0["subrole"],
                "dist_pc": str(e0["dist_pc"]), "within_10pc": "True" if e0["within_10pc"] else "False",
                "teff_k": str(e0["teff_k"]), "phot_g_mag": str(e0["phot_g_mag"]),
                "j_mag": str(e0["j_mag"]), "h_mag": str(e0["h_mag"]), "ks_mag": str(e0["ks_mag"]),
                "n_exoplanets": str(e0["n_exoplanets"]),
                "n_exposures_optical": str(n_exp),
                "n_exposures_nir_yjh": str(n_exp) if inst == "ESO_XSHOOTER_3ARM" else "0",
                "n_exposures_kband": str(n_exp) if inst == "ESO_XSHOOTER_3ARM" else "0",
                "n_exposures_total": str(n_exp),
                "min_optical_10m_kw": f"{p_opt:.8g}" if p_opt is not None else "",
                "min_nir_yjh_10m_kw": f"{p_yjh:.8g}" if p_yjh is not None else "",
                "min_kband_10m_kw": f"{p_kb:.8g}" if p_kb is not None else "",
                "p_1064nm_10m_kw": "",
                "p_1550nm_10m_kw": f"{p_yjh:.8g}" if p_yjh is not None else "",
                "p_2040nm_tm_10m_kw": "",
                "p_2097nm_hoyag_10m_kw": f"{p_kb:.8g}" if p_kb is not None else "",
                "min_panchromatic_10m_kw": f"{p_best:.8g}",
                "automated_qualified_candidates": str(n_cand), "verified_eti_detections": "0",
                "n_exposures_nuv": str(n_exp) if inst == "ESO_XSHOOTER_3ARM" else "0",
                "min_nuv_10m_kw": f"{p_nuv:.8g}" if p_nuv is not None else "",
                "n_exposures_fuv": "0", "min_fuv_10m_kw": "",
                "n_exposures_farred_uves": "0", "min_farred_uves_10m_kw": "",
                "n_exposures_lyman_fuse": "0", "min_lyman_fuse_10m_kw": "",
                "n_exposures_jwst_ir": "0", "min_jwst_ir_10m_kw": "", "p_10p6um_co2_10m_kw": "",
                "n_exposures_xshooter_3arm": str(n_exp) if inst == "ESO_XSHOOTER_3ARM" else "0",
                "min_xshooter_3arm_10m_kw": f"{p_best:.8g}" if inst == "ESO_XSHOOTER_3ARM" else "",
                "n_exposures_feros_v42": str(n_exp) if inst == "ESO_FEROS" else "0",
                "min_feros_v42_10m_kw": f"{p_best:.8g}" if inst == "ESO_FEROS" else "",
                "n_exposures_giraffe_hr": str(n_exp) if inst == "ESO_GIRAFFE_HR" else "0",
                "min_giraffe_hr_10m_kw": f"{p_best:.8g}" if inst == "ESO_GIRAFFE_HR" else "",
            }

    u310_rows = sorted(u_map.values(), key=lambda x: (float(x["dist_pc"]), x["star"]))
    solar135_rows = [r for r in u310_rows if r["within_10pc"] == "True"]

    mm_by_star = {s["canonical_v3_star"]: s for s in snap_mm["systems"]}
    mm310_rows: list[dict[str, Any]] = []
    for ur in u310_rows:
        st = ur["star"]
        ms = mm_by_star.get(st)
        if ms:
            mods = f"ECHELLE_SPECTROSCOPY+{ms['modality']}"
            n_mod, ovlp = 2, True
            r_ms = ms["milestone"] if "RADIO" in ms["modality"] else ""
            r_fac = ms["facility"] if "RADIO" in ms["modality"] else ""
            r_rec = ms["snr40_recovery_fraction"] if "RADIO" in ms["modality"] else ""
            l_ms = ms["milestone"] if "PHOTOMETRY" in ms["modality"] else ""
        else:
            mods, n_mod, ovlp = "ECHELLE_SPECTROSCOPY", 1, False
            r_ms = r_fac = r_rec = l_ms = ""
        mm310_rows.append({
            "system_id": st, "host_name": ur["common_name"], "hemisphere": ur["hemisphere"], "role": ur["role"],
            "dist_pc": ur["dist_pc"], "within_10pc": ur["within_10pc"], "n_exoplanets": ur["n_exoplanets"],
            "modalities_searched": mods, "n_modalities": n_mod, "multimessenger_overlap": ovlp,
            "echelle_phases": ur["phases"], "echelle_instruments": ur["instruments"],
            "echelle_exposures": ur["n_exposures_total"], "min_echelle_10m_kw": ur["min_panchromatic_10m_kw"],
            "radio_milestone": r_ms, "radio_facility": r_fac, "radio_snr40_recovery": r_rec,
            "lightsail_milestone": l_ms, "verified_eti_detections": 0,
        })

    # Summaries & Cascade Metrics
    n_g1 = len(ledger_rows)
    n_g2 = sum(1 for r in ledger_rows if r["g2_pass"])
    n_g3 = sum(1 for r in ledger_rows if r["g2_pass"] and r["g3_pass"])
    n_g4 = sum(1 for r in ledger_rows if r["g2_pass"] and r["g3_pass"] and r["g4_pass"])
    n_pre_g6 = sum(1 for r in ledger_rows if r["pre_g6_qualified"])
    n_veto_g6 = sum(1 for r in ledger_rows if r["pre_g6_qualified"] and not r["g6_pass"])
    n_ctrl_q = sum(1 for r in ledger_rows if r["qualified_v42_laser"] and r["role"] == "CONTROL")
    n_sci_q = sum(1 for r in ledger_rows if r["qualified_v42_laser"] and r["role"] == "SCIENCE")
    v2_tot = sum(v2_by_dp.values())
    int_hrs = round(sum(float(e["t_exptime_s"]) for e in exposures_raw) / 3600.0, 4)

    prior_n_exp = int(snap_v4["prior_v41_total_exposures_count"])
    prior_hrs = float(snap_v4["prior_cumulative_integration_hours"])
    prior_cal = int(snap_v4["prior_v41_calibration_trials_count"])
    prior_v2 = int(snap_v4["prior_v2_false_alarms_eliminated_total"])
    prior_camp = int(snap_v4["prior_cumulative_orbital_campaigns_count"])

    sci_ul = [r for r in ul_rows if exps_by_star[r["star"]][0]["role"] == "SCIENCE"]
    best_all = min(sci_ul, key=lambda r: float(r["p_beam_10m_kw"]))
    best_by_inst = {
        inst: min([r for r in sci_ul if r["instrument"] == inst], key=lambda r: float(r["p_beam_10m_kw"]))
        for inst in ("ESO_XSHOOTER_3ARM", "ESO_FEROS", "ESO_GIRAFFE_HR")
    }
    lim_10pc = [float(r["min_panchromatic_10m_kw"]) for r in solar135_rows if r["min_panchromatic_10m_kw"]]
    med_10pc_kw = round(exact_median_1d(np.asarray(lim_10pc, dtype=np.float64)), 5)

    diag_doc = {
        "schema": "FORENSIC_D091_CASCADE_DIAGNOSIS_V1",
        "phase_id": "D091",
        "cascade": {
            "v2_legacy_false_alarms": v2_tot,
            "v42_total_ledger_g1_candidates": n_g1,
            "v42_after_g2": n_g2,
            "v42_after_g3": n_g3,
            "v42_after_g4": n_g4,
            "v42_pre_g6_passed_g1_to_g5": n_pre_g6,
            "v42_vetoed_by_g6_sparse": n_veto_g6,
            "v42_orbital_candidates": sum(oc["tdiff"] + oc["kplanet"] for oc in orb_cand_counts.values()),
            "automated_qualified_control": n_ctrl_q,
            "automated_qualified_science": n_sci_q,
            "comb_v41_automated_candidates": comb_v41_tot,
            "verified_eti_detections": 0,
        },
        "forensic_class_counts": dict(forensic_cls_cnt.most_common()),
        "xshooter_dual_arm_coincidence": xsh_dual_sum,
        "comb_v41_d091": {"comb_v4_automated": comb_v4_tot, "comb_v41_automated": comb_v41_tot, "verified_eti": 0},
        "comb_v41_allsky_d079_d091": {
            "total_exposures": prior_n_exp + len(exposures_raw),
            "total_stacks": len(allsky_comb_rows),
            "comb_v4_automated_total": sum(int(r["comb_v4_candidates"]) for r in allsky_comb_rows),
            "comb_v41_automated_total": sum(int(r["comb_v41_candidates"]) for r in allsky_comb_rows),
            "verified_eti_total": 0,
        },
    }

    audit_doc = {
        "schema": "FORENSIC_CANDIDATE_AUDIT_D091_V1",
        "phase_id": "D091",
        "n_automated_qualified_audited": len(forensic_recs),
        "comb_v41_candidates_audited": len(comb_cand_rows),
        "verified_eti_detections": 0,
        "candidates": forensic_recs,
    }

    summary_doc = {
        "phase_id": "D091",
        "detector": DETECTOR_NAME,
        "instruments": ["ESO_XSHOOTER_3ARM", "ESO_FEROS", "ESO_GIRAFFE_HR"],
        "wavelength_domain_um": [0.2989, 2.4790],
        "cumulative_wavelength_domain_um": [0.0905, 28.0],
        "cumulative_octaves": round(math.log2(28.0 / 0.0905), 3),
        "cumulative_spectrographs": 19,
        "cumulative_arms": 22,
        "cohort": {
            "total_stars": 37,
            "control_stars": sum(1 for r in star_rv_rows if r["role"] == "CONTROL"),
            "science_stars": sum(1 for r in star_rv_rows if r["role"] == "SCIENCE"),
            "brand_new_unique_stars": 30,
            "panchromatic_bridge_stars_in_d091": 7,
            "newly_bridged_stars_added_to_census": 5,
            "brand_new_within_10pc": 10,
            "total_exposures": len(exposures_raw),
            "xshooter_3arm_exposures": len(exps_by_inst["ESO_XSHOOTER_3ARM"]),
            "feros_exposures": len(exps_by_inst["ESO_FEROS"]),
            "giraffe_hr_exposures": len(exps_by_inst["ESO_GIRAFFE_HR"]),
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
        "synthetic_calibration_2697_trials": cal_sum,
        "xshooter_dual_arm_coincidence": xsh_dual_sum,
        "allsky_comb_v41_sweep_d079_d091": diag_doc["comb_v41_allsky_d079_d091"],
        "false_alarm_cascade": diag_doc["cascade"],
        "upper_limits": {
            "n_cells": len(ul_rows),
            "best_d091_star": best_all["star"],
            "best_d091_instrument": best_all["instrument"],
            "best_d091_band": best_all["band_id"],
            "best_d091_10m_w": round(float(best_all["p_beam_10m_w"]), 5),
            "best_d091_10m_kw": round(float(best_all["p_beam_10m_kw"]), 6),
            "best_xshooter_star": best_by_inst["ESO_XSHOOTER_3ARM"]["star"],
            "best_xshooter_10m_kw": round(float(best_by_inst["ESO_XSHOOTER_3ARM"]["p_beam_10m_kw"]), 5),
            "best_feros_star": best_by_inst["ESO_FEROS"]["star"],
            "best_feros_10m_kw": round(float(best_by_inst["ESO_FEROS"]["p_beam_10m_kw"]), 5),
            "best_giraffe_star": best_by_inst["ESO_GIRAFFE_HR"]["star"],
            "best_giraffe_10m_kw": round(float(best_by_inst["ESO_GIRAFFE_HR"]["p_beam_10m_kw"]), 5),
        },
        "unified_310star_panchromatic_v4_2_synthesis": {
            "phases": "D079-D091",
            "spectrographs": 19,
            "spectrograph_arms": 22,
            "unique_stars_total": len(u310_rows),
            "within_10pc_unique_stars": len(solar135_rows),
            "within_10pc_median_limit_kw": med_10pc_kw,
            "panchromatic_bridge_stars_total": len({r["star"] for r in bridge_rows}),
            "total_exposures_d079_d091": prior_n_exp + len(exposures_raw),
            "total_integration_hours_d079_d091": round(prior_hrs + int_hrs, 4),
            "total_calibration_trials_d079_d091": prior_cal + cal_sum["total_trials"],
            "v2_false_alarms_eliminated_total": prior_v2 + v2_tot,
            "cumulative_orbital_campaigns": prior_camp + len(orb_rows),
            "verified_eti_detections_total": 0,
        },
        "multimessenger_310system_synthesis": {
            "distinct_stellar_systems_total": len(mm310_rows),
            "radio_echelle_closure": "23/23 (100%)",
            "direct_multimessenger_overlap_count": sum(1 for r in mm310_rows if r["multimessenger_overlap"]),
            "tri_regime_radio_optical_xshooter_miri_stars": ["16CYGB", "GJ849"],
            "verified_eti_detections_all_modalities": 0,
        },
    }

    # Write exact 24 Stage-B output files
    _write_csv(out_dir / "EXPOSURE_PROVENANCE_D091.csv", list(prov_rows[0].keys()), prov_rows)
    _write_csv(out_dir / "STELLAR_RV_ANCHORS_D091.csv", list(rv_anchor_rows[0].keys()), rv_anchor_rows)
    _write_csv(out_dir / "STAR_RV_SUMMARY_37.csv", list(star_rv_rows[0].keys()), star_rv_rows)
    _write_csv(out_dir / "FOUR_GEN_BENCHMARK_D091.csv", list(bench_rows[0].keys()), bench_rows)
    ledger_cols = [
        "candidate_id", "instrument", "channel", "role", "star", "dp_id", "fitted_wave_a", "stellar_rest_wave_a",
        "bary_wave_a", "topo_wave_a", "snr_mid", "snr_out", "cosine", "fwhm_ratio", "target_fn_pk3",
        "g1_pass", "g2_pass", "g3_pass", "primary_order", "primary_native_px", "primary_native_fn_pk3", "primary_eta_1px",
        "g4_pass", "g5_pass", "g5_cos11", "g5_ipc_hotpx_ratio", "g5_far_wing_ratio",
        "pre_g6_qualified", "g6_v35_dense_pass", "g6_pass", "g6_coincident_total_stars", "g6_same_star_hits",
        "qualified_v42_laser", "final_disposition",
    ]
    _write_csv(out_dir / "V4_2_CANDIDATE_LEDGER.csv", ledger_cols, ledger_rows)
    _write_json(out_dir / "FORENSIC_CANDIDATE_AUDIT_D091.json", audit_doc)
    _write_json(out_dir / "FORENSIC_D091_CASCADE_DIAGNOSIS.json", diag_doc)
    _write_csv(out_dir / "ORBITAL_CAMPAIGN_RESULTS_10.csv", list(orb_rows[0].keys()), orb_rows)
    _write_csv(out_dir / "COMB_V4_1_STAR_RESULTS_37.csv", list(comb_star_rows[0].keys()), comb_star_rows)
    comb_c_cols = ["comb_id", "instrument", "star", "role", "band", "dnu_ghz", "nu0_ghz", "wave0_a", "wave_end_a",
                   "s_comb", "topo_anti_ratio", "n_qualifying_teeth", "off_tooth_crowding", "intertooth_ratio"]
    _write_csv(out_dir / "COMB_V4_1_CANDIDATES.csv", comb_c_cols, comb_cand_rows)
    _write_csv(out_dir / "ALLSKY_COMB_V4_1_UNIFIED_D079_D091.csv", list(allsky_comb_rows[0].keys()), allsky_comb_rows)
    _write_csv(out_dir / "ALLSKY_COMB_V4_1_CANDIDATES_D079_D091.csv", list(allsky_comb_cands[0].keys()), allsky_comb_cands)
    _write_csv(out_dir / "INJECTION_RECOVERY_1620.csv", list(inj_rows[0].keys()), inj_rows)
    _write_csv(out_dir / "CALIBRATION_COMPLETENESS_BY_BAND.csv", list(comp_rows[0].keys()), comp_rows)
    _write_csv(out_dir / "KEPLERIAN_TRACK_CALIBRATION_135.csv", list(kep_rows[0].keys()), kep_rows)
    _write_csv(out_dir / "DETECTOR_V42_G4G5_CALIBRATION_216.csv", list(g45_rows[0].keys()), g45_rows)
    _write_csv(out_dir / "G6_SPARSE_VS_DENSE_CALIBRATION_240.csv", list(g6_rows[0].keys()), g6_rows)
    _write_csv(out_dir / "COMB_V4_1_CALIBRATION_486.csv", list(comb_cal_rows[0].keys()), comb_cal_rows)
    _write_csv(out_dir / "STAR_UPPER_LIMITS_D091.csv", list(ul_rows[0].keys()), ul_rows)
    _write_csv(out_dir / "PANCHROMATIC_BRIDGE_35STARS.csv", list(bridge_rows[0].keys()), bridge_rows)
    _write_csv(out_dir / "UNIFIED_PANCHROMATIC_V4_2_SYNTHESIS_310STARS.csv", U310_COLS, u310_rows)
    _write_csv(out_dir / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_135STARS.csv", U310_COLS, solar135_rows)
    _write_csv(out_dir / "MULTIMESSENGER_ECHELLE_RADIO_TESS_310SYSTEMS.csv", list(mm310_rows[0].keys()), mm310_rows)
    _write_json(out_dir / "SUMMARY.json", summary_doc)

    print(
        f"Stage B DONE ({out_dir}): {len(u310_rows)} stars ({len(solar135_rows)} <10pc, "
        f"{summary_doc['unified_310star_panchromatic_v4_2_synthesis']['panchromatic_bridge_stars_total']} bridges), "
        f"{n_g1} G1 -> {n_pre_g6} preG6 -> {n_ctrl_q + n_sci_q} autoQual -> 0 ETI; "
        f"cal={cal_sum['total_trials']} trials, XSH dual={xsh_dual_sum['dual_arm_pass_count']}/8, "
        f"best_d091={best_all['star']} {best_all['band_id']}={best_all['p_beam_10m_kw']:.4f} kW",
        flush=True,
    )
    return summary_doc


def main() -> None:
    ap = argparse.ArgumentParser(description="Phase D091 ESO_TRIPLE_SPECTROGRAPH_3ARM_V4_2 Analysis Pipeline")
    ap.add_argument("--from-full-inputs", type=Path, default=None, help="Path to full raw FITS inputs_d091_v4_2 directory")
    ap.add_argument("--from-bounded-inputs", type=Path, default=None, help="Path to d091_bounded_bundle.json.gz")
    ap.add_argument("--out-dir", type=Path, default=WS / "results", help="Output directory for 24 result files")
    args = ap.parse_args()

    if args.from_bounded_inputs is not None:
        with gzip.open(args.from_bounded_inputs, "rt", encoding="utf-8") as gz:
            bundle = json.load(gz)
        run_stage_b(bundle, args.out_dir)
    else:
        full_dir = args.from_full_inputs or (ROOT / "inputs_d091_v4_2")
        bundle = run_stage_a_build_bundle(full_dir)
        run_stage_b(bundle, args.out_dir)


if __name__ == "__main__":
    main()
