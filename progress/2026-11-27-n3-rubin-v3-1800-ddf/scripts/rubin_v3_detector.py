#!/usr/bin/env python3
"""
Locked Rubin Observatory (LSST) V3 Cross-Stream SETI Detector & Calibrator (1,800 Stars).
Implements:
  - Strict 64-bit string IDs (parse_int=str) & separate /sources vs /fp evaluation
  - V2-compatible LONO +-180d & causal -180d baselines + pixel flag / timeWithdrawn hygiene
  - V3 Upgrade Gate 1: Astrometric stability (centroid offset <= 0.40") & reliability >= 0.50
  - V3 Upgrade Gate 2: Cross-stream /sources <-> /fp co-confirmation (|dt| <= 0.05d, same band,
      Dim fp_ratio <= 0.80, Flash fp_ratio >= 1.40) -> suppresses unconfirmed DIA subtraction artifacts
  - Automated Lomb-Scargle periodicity & blue M-dwarf flare characterization
  - 4,800-trial/stream synthetic injection-recovery (2,400 Dim + 2,400 Flash) across 400 stars
  - Exact analytical Bayesian f95 for N3 standalone AND Combined Rubin V2+V3 (2,100 zero-overlap stars)
"""
from __future__ import annotations

import collections
import csv
import datetime
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from astropy.timeseries import LombScargle
import numpy as np
from scipy.stats import beta as scipy_beta

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace" / "work_n3_20261127_rubin_v3_1800ddf"
INP = ROOT / "inputs_n3_20261127"
RES = WS / "results"
RV2_SUMMARY_PATH = ROOT / "analysis_workspace" / "work_rubin_v2_20261126_r1_ddf_and_r2_catalog" / "results" / "R1_R2_DETECTOR_SUMMARY.json"

# Locked physical & statistical thresholds
RATIO_DIM_MAX = 10.0 ** (-0.4 * 0.30)      # 0.7585775750291837
Z_DIM_MIN = 5.0
RATIO_FLASH_MIN = 10.0 ** (0.4 * 0.50)     # 1.5848931924611136
Z_FLASH_MIN = 6.0
BASELINE_WINDOW_DAYS = 180.0
MIN_BASE_VISITS = 5
MIN_BASE_DATES = 3
MIN_BASE_SNR = 10.0
MAD_SCALE = 1.4826

# V3 Cross-Stream & Astrometric Gates
V3_MAX_CENTROID_OFFSET_ARCSEC = 0.40
V3_MIN_RELIABILITY = 0.50
V3_CROSS_MATCH_DT_DAYS = 0.05
V3_FP_DIM_CONFIRM_RATIO = 0.80
V3_FP_FLASH_CONFIRM_RATIO = 1.40

CRITICAL_FALSE_FLAGS = (
    "r:pixelFlags_saturated",
    "r:pixelFlags_saturatedCenter",
    "r:pixelFlags_cr",
    "r:pixelFlags_crCenter",
    "r:pixelFlags_bad",
    "r:pixelFlags_edge",
    "r:pixelFlags_offimage",
    "r:pixelFlags_nodata",
    "r:pixelFlags_interpolatedCenter",
    "r:isDipole",
    "r:forced_PsfFlux_flag",
    "r:forced_PsfFlux_flag_edge",
    "r:forced_PsfFlux_flag_noGoodPixels",
)


def parse_bool_strict(val: Any) -> bool | None:
    if isinstance(val, bool):
        return val
    if val is None:
        return None
    s = str(val).strip().lower()
    if s in ("false", "0", "0.0", "f", "no"):
        return False
    if s in ("true", "1", "1.0", "t", "yes"):
        return True
    return None


def safe_float(val: Any) -> float | None:
    if val is None or val == "" or str(val).strip().lower() in ("nan", "null", "none", "inf", "-inf"):
        return None
    try:
        x = float(val)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def angsep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    cos_a = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_a)))) * 3600.0


def check_source_quality(row: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    fval = safe_float(row.get("r:scienceFlux"))
    ferr = safe_float(row.get("r:scienceFluxErr"))
    mjd = safe_float(row.get("r:midpointMjdTai"))
    band = str(row.get("r:band") or "").strip()
    if mjd is None or not band:
        reasons.append("MISSING_MJD_OR_BAND")
    if fval is None or ferr is None or ferr <= 0.0:
        reasons.append("NONFINITE_FLUX")
    sat = parse_bool_strict(row.get("r:pixelFlags_saturated"))
    sat_c = parse_bool_strict(row.get("r:pixelFlags_saturatedCenter"))
    cr = parse_bool_strict(row.get("r:pixelFlags_cr"))
    cr_c = parse_bool_strict(row.get("r:pixelFlags_crCenter"))
    dip = parse_bool_strict(row.get("r:isDipole"))
    edge_bad = any(parse_bool_strict(row.get(k)) is True for k in CRITICAL_FALSE_FLAGS[4:9])
    forced_bad = any(parse_bool_strict(row.get(k)) is True for k in CRITICAL_FALSE_FLAGS[10:13])
    missing_core = any(parse_bool_strict(row.get(k)) is None for k in CRITICAL_FALSE_FLAGS[:10])
    if sat is True or sat_c is True:
        reasons.append("SATURATED")
    if cr is True or cr_c is True:
        reasons.append("COSMIC_RAY")
    if dip is True:
        reasons.append("DIPOLE")
    if edge_bad:
        reasons.append("EDGE_OR_BAD")
    if forced_bad:
        reasons.append("FORCED_FLAG_FAIL")
    if missing_core:
        reasons.append("MISSING_PIXEL_FLAG")
    return (len(reasons) == 0), reasons


def check_fp_quality(row: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    fval = safe_float(row.get("r:scienceFlux"))
    ferr = safe_float(row.get("r:scienceFluxErr"))
    mjd = safe_float(row.get("r:midpointMjdTai"))
    band = str(row.get("r:band") or "").strip()
    if mjd is None or not band:
        reasons.append("MISSING_MJD_OR_BAND")
    if fval is None or ferr is None or ferr <= 0.0:
        reasons.append("NONFINITE_FLUX")
    return (len(reasons) == 0), reasons


def robust_baseline_stats(fluxes: np.ndarray, errs: np.ndarray) -> tuple[float, float]:
    f0 = float(np.median(fluxes))
    mad = float(np.median(np.abs(fluxes - f0)))
    med_err = float(np.median(errs))
    sigma_rob = max(MAD_SCALE * mad, med_err)
    return f0, sigma_rob


def evaluate_object_band(
    obs: list[dict[str, Any]],
    mode: str = "lono",
    flux_override: np.ndarray | None = None,
) -> list[dict[str, Any]]:
    n = len(obs)
    if n == 0:
        return []
    mjds = np.array([o["mjd"] for o in obs], dtype=float)
    days = np.array([int(math.floor(m)) for m in mjds], dtype=np.int64)
    fluxes = np.array([o["flux"] for o in obs], dtype=float) if flux_override is None else flux_override
    errs = np.array([o["err"] for o in obs], dtype=float)

    scored = []
    for i in range(n):
        mi, di, fi, ei = float(mjds[i]), int(days[i]), float(fluxes[i]), float(errs[i])
        if mode == "lono":
            mask = (days != di) & (np.abs(mjds - mi) <= BASELINE_WINDOW_DAYS)
        elif mode == "causal":
            mask = (days < di) & ((mi - mjds) <= BASELINE_WINDOW_DAYS) & (mjds < mi)
        else:
            raise ValueError(mode)

        base_f, base_e, base_d, base_m = fluxes[mask], errs[mask], days[mask], mjds[mask]
        n_base = int(len(base_f))
        n_base_dates = int(len(set(base_d.tolist())))
        evaluable = False
        reason = "OK"
        f0 = sigma_rob = ratio = z_dim = z_flash = mag_delta = nearest_gap = float("nan")
        trig_dim = trig_flash = False

        if n_base < MIN_BASE_VISITS or n_base_dates < MIN_BASE_DATES:
            reason = "INSUFFICIENT_BASELINE_VISITS_OR_DATES"
        else:
            f0, sigma_rob = robust_baseline_stats(base_f, base_e)
            if f0 <= 0.0 or sigma_rob <= 0.0:
                reason = "NONPOSITIVE_BASELINE"
            elif (f0 / sigma_rob) < MIN_BASE_SNR:
                reason = "LOW_BASELINE_SNR"
            else:
                evaluable = True
                ratio = fi / f0
                denom = math.hypot(sigma_rob, ei)
                z_dim = (f0 - fi) / denom
                z_flash = (fi - f0) / denom
                if ratio > 0.0:
                    mag_delta = -2.5 * math.log10(ratio)
                trig_dim = (ratio <= RATIO_DIM_MAX) and (z_dim >= Z_DIM_MIN)
                trig_flash = (ratio >= RATIO_FLASH_MIN) and (z_flash >= Z_FLASH_MIN)
                nearest_gap = float(np.min(np.abs(base_m - mi)))

        scored.append({
            "obs_id": obs[i]["obs_id"],
            "mjd": mi,
            "utc_day": di,
            "band": obs[i]["band"],
            "flux": fi,
            "flux_err": ei,
            "snr": obs[i].get("snr"),
            "reliability": obs[i].get("reliability"),
            "centroid_offset_arcsec": obs[i].get("centroid_offset_arcsec"),
            "evaluable": evaluable,
            "reason": reason,
            "n_base_visits": n_base,
            "n_base_dates": n_base_dates,
            "baseline_f0": f0,
            "baseline_sigma_rob": sigma_rob,
            "flux_ratio": ratio,
            "mag_delta": mag_delta,
            "z_dim": z_dim,
            "z_flash": z_flash,
            "trig_dim": trig_dim,
            "trig_flash": trig_flash,
            "nearest_gap_days": nearest_gap,
        })
    return scored


def load_batches(prefix: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fp in sorted(INP.glob(f"**/{prefix}*.json")):
        if fp.name.endswith(".receipt.json"):
            continue
        d = json.loads(fp.read_text(encoding="utf-8"), parse_int=str)
        if isinstance(d, list):
            rows.extend(d)
    return rows


def dedup_rows(rows: list[dict[str, Any]], id_key: str, stream: str) -> list[dict[str, Any]]:
    seen: dict[tuple[str, str, str], dict[str, Any]] = {}
    for r in rows:
        oid = str(r.get("r:diaObjectId") or "")
        sid = str(r.get(id_key) or "")
        k = (oid, sid if sid else f"{r.get('r:midpointMjdTai')}:{r.get('r:band')}", stream)
        if k not in seen:
            seen[k] = r
    return list(seen.values())


def lomb_scargle_check(obs: list[dict[str, Any]]) -> dict[str, Any]:
    if len(obs) < 12:
        return {"ls_tested": False, "best_period_d": None, "ls_power": None, "ls_fap": None, "periodic_flag": False}
    t = np.array([o["mjd"] for o in obs], dtype=float)
    y = np.array([o["flux"] for o in obs], dtype=float)
    dy = np.array([o["err"] for o in obs], dtype=float)
    tspan = float(np.max(t) - np.min(t))
    if tspan < 1.0:
        return {"ls_tested": False, "best_period_d": None, "ls_power": None, "ls_fap": None, "periodic_flag": False}
    ls = LombScargle(t, y, dy)
    freq, power = ls.autopower(minimum_frequency=1.0 / max(tspan, 10.0), maximum_frequency=10.0, samples_per_peak=5)
    if len(power) == 0:
        return {"ls_tested": False, "best_period_d": None, "ls_power": None, "ls_fap": None, "periodic_flag": False}
    idx = int(np.argmax(power))
    max_p = float(power[idx])
    best_period = 1.0 / float(freq[idx]) if float(freq[idx]) > 0 else float("nan")
    try:
        fap = float(ls.false_alarm_probability(max_p))
    except Exception:
        fap = 1.0
    is_day_alias = abs(best_period - 1.0) < 0.03 or abs(best_period - 0.5) < 0.015
    periodic = (fap < 1e-3) and (max_p > 0.35) and not is_day_alias
    return {"ls_tested": True, "best_period_d": round(best_period, 6), "ls_power": round(max_p, 5), "ls_fap": float(fap), "periodic_flag": periodic}


def bayesian_limits(n_eval: int, n_eff: float, k_det: int = 0) -> dict[str, Any]:
    if n_eff <= 0.0:
        return {"n_eval": n_eval, "n_eff": 0.0, "uniform_f95_pct": 100.0, "jeffreys_f95_pct": 100.0, "clopper_pearson_f95_pct": 100.0}
    u95 = float(scipy_beta.ppf(0.95, k_det + 1.0, n_eff + 1.0)) * 100.0
    j95 = float(scipy_beta.ppf(0.95, k_det + 0.5, n_eff + 0.5)) * 100.0
    cp95 = (1.0 - (0.05 ** (1.0 / max(1.0, n_eff)))) * 100.0 if k_det == 0 else float(scipy_beta.ppf(0.95, k_det + 1.0, max(1.0, n_eff - k_det))) * 100.0
    return {
        "n_eval": int(n_eval),
        "n_eff": round(float(n_eff), 3),
        "uniform_f95_pct": round(u95, 4),
        "jeffreys_f95_pct": round(j95, 4),
        "clopper_pearson_f95_pct": round(cp95, 4),
    }


def analyze_stream(
    cohort_rows: list[dict[str, Any]],
    raw_rows: list[dict[str, Any]],
    stream_name: str,
    id_key: str,
) -> dict[str, Any]:
    cohort_ids = {r["diaObjectId"]: r for r in cohort_rows}
    deduped = dedup_rows(raw_rows, id_key=id_key, stream=stream_name)
    by_obj_raw: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    withdrawn_nonnull = 0
    for r in deduped:
        oid = str(r.get("r:diaObjectId") or "")
        if oid in cohort_ids:
            if r.get("r:timeWithdrawnMjdTai") not in (None, "", "null"):
                withdrawn_nonnull += 1
            by_obj_raw[oid].append(r)

    reason_counts: collections.Counter[str] = collections.Counter()
    clean_by_obj_band: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    clean_coords_by_obj: dict[str, tuple[list[float], list[float]]] = collections.defaultdict(lambda: ([], []))
    clean_rows_total = 0
    excluded_rows_total = 0

    for oid, rows in by_obj_raw.items():
        for r in rows:
            ok, reasons = check_source_quality(r) if stream_name == "sources" else check_fp_quality(r)
            if not ok:
                excluded_rows_total += 1
                for rs in reasons:
                    reason_counts[rs] += 1
                continue
            clean_rows_total += 1
            ra_v = safe_float(r.get("r:ra"))
            dec_v = safe_float(r.get("r:dec"))
            if ra_v is not None and dec_v is not None:
                clean_coords_by_obj[oid][0].append(ra_v)
                clean_coords_by_obj[oid][1].append(dec_v)
            clean_by_obj_band[(oid, str(r["r:band"]).strip())].append({
                "obs_id": str(r.get(id_key) or ""),
                "mjd": float(r["r:midpointMjdTai"]),
                "band": str(r["r:band"]).strip(),
                "flux": float(r["r:scienceFlux"]),
                "err": float(r["r:scienceFluxErr"]),
                "snr": safe_float(r.get("r:snr")),
                "reliability": safe_float(r.get("r:reliability")),
                "ra": ra_v,
                "dec": dec_v,
                "centroid_offset_arcsec": None,
            })

    # Compute per-object median clean coordinates and per-epoch centroid offset (/sources)
    med_coords = {}
    for oid, (ras, decs) in clean_coords_by_obj.items():
        if ras:
            med_coords[oid] = (float(np.median(ras)), float(np.median(decs)))
    for (oid, _), obs in clean_by_obj_band.items():
        if oid in med_coords:
            rm, dm = med_coords[oid]
            for o in obs:
                if o["ra"] is not None and o["dec"] is not None:
                    o["centroid_offset_arcsec"] = round(angsep_arcsec(o["ra"], o["dec"], rm, dm), 4)

    eval_objs_lono: set[str] = set()
    eval_objs_causal: set[str] = set()
    eval_rows_lono = eval_rows_causal = 0
    evaluable_series_lono: dict[tuple[str, str], list[dict[str, Any]]] = {}
    scored_lookup_by_obj_band: dict[tuple[str, str], list[dict[str, Any]]] = {}
    triggers_dim: list[dict[str, Any]] = []
    triggers_flash: list[dict[str, Any]] = []
    ls_by_obj_band: dict[tuple[str, str], dict[str, Any]] = {}

    obj_summary: dict[str, dict[str, Any]] = {}
    for c in cohort_rows:
        oid = c["diaObjectId"]
        obj_summary[oid] = {
            "diaObjectId": oid,
            "gaia_source_id": c["gaia_source_id"],
            "field": c["field"],
            "phot_g_mean_mag": c["phot_g_mean_mag"],
            "bp_rp": c["bp_rp"],
            "phot_variable_flag": c["phot_variable_flag"],
            "raw_rows": len(by_obj_raw.get(oid, ())),
            "clean_rows": 0,
            "eval_rows_lono": 0,
            "eval_rows_causal": 0,
            "eval_bands": [],
            "n_trig_dim": 0,
            "n_trig_flash": 0,
            "max_z_dim": 0.0,
            "max_z_flash": 0.0,
            "min_ratio": float("nan"),
            "max_ratio": float("nan"),
        }

    for (oid, band), obs in sorted(clean_by_obj_band.items()):
        obs.sort(key=lambda x: x["mjd"])
        obj_summary[oid]["clean_rows"] += len(obs)
        sc_lono = evaluate_object_band(obs, mode="lono")
        sc_caus = evaluate_object_band(obs, mode="causal")
        scored_lookup_by_obj_band[(oid, band)] = sc_lono
        ev_l = [r for r in sc_lono if r["evaluable"]]
        ev_c = [r for r in sc_caus if r["evaluable"]]
        if ev_l:
            eval_objs_lono.add(oid)
            eval_rows_lono += len(ev_l)
            evaluable_series_lono[(oid, band)] = obs
            obj_summary[oid]["eval_rows_lono"] += len(ev_l)
            obj_summary[oid]["eval_bands"].append(band)
        if ev_c:
            eval_objs_causal.add(oid)
            eval_rows_causal += len(ev_c)
            obj_summary[oid]["eval_rows_causal"] += len(ev_c)

        any_trig = any(r["trig_dim"] or r["trig_flash"] for r in ev_l)
        if any_trig:
            ls_by_obj_band[(oid, band)] = lomb_scargle_check(obs)

        for r in ev_l:
            os = obj_summary[oid]
            rt = r["flux_ratio"]
            os["min_ratio"] = rt if math.isnan(os["min_ratio"]) else min(os["min_ratio"], rt)
            os["max_ratio"] = rt if math.isnan(os["max_ratio"]) else max(os["max_ratio"], rt)
            os["max_z_dim"] = max(os["max_z_dim"], r["z_dim"])
            os["max_z_flash"] = max(os["max_z_flash"], r["z_flash"])
            if r["trig_dim"] or r["trig_flash"]:
                base_rec = {
                    "diaObjectId": oid,
                    "gaia_source_id": cohort_ids[oid]["gaia_source_id"],
                    "field": cohort_ids[oid]["field"],
                    "bp_rp": cohort_ids[oid]["bp_rp"],
                    "phot_g_mean_mag": cohort_ids[oid]["phot_g_mean_mag"],
                    "phot_variable_flag": cohort_ids[oid]["phot_variable_flag"],
                    "stream": stream_name,
                    "obs_id": r["obs_id"],
                    "band": band,
                    "mjd": r["mjd"],
                    "flux": r["flux"],
                    "flux_err": r["flux_err"],
                    "baseline_f0": r["baseline_f0"],
                    "baseline_sigma_rob": r["baseline_sigma_rob"],
                    "n_base_visits": r["n_base_visits"],
                    "flux_ratio": round(r["flux_ratio"], 5),
                    "mag_delta": round(r["mag_delta"], 4) if math.isfinite(r["mag_delta"]) else None,
                    "z_dim": round(r["z_dim"], 3),
                    "z_flash": round(r["z_flash"], 3),
                    "reliability": r["reliability"],
                    "centroid_offset_arcsec": r["centroid_offset_arcsec"],
                    "ls_periodic": ls_by_obj_band.get((oid, band), {}).get("periodic_flag", False),
                    "ls_period_d": ls_by_obj_band.get((oid, band), {}).get("best_period_d"),
                }
                if r["trig_dim"]:
                    os["n_trig_dim"] += 1
                    triggers_dim.append({**base_rec, "channel": "DIM"})
                if r["trig_flash"]:
                    os["n_trig_flash"] += 1
                    triggers_flash.append({**base_rec, "channel": "FLASH"})

    return {
        "stream": stream_name,
        "selected_objects": len(cohort_rows),
        "objects_with_raw_data": len(by_obj_raw),
        "raw_rows_deduped": len(deduped),
        "cohort_raw_rows": sum(len(v) for v in by_obj_raw.values()),
        "clean_rows": clean_rows_total,
        "excluded_rows": excluded_rows_total,
        "exclusion_reasons": dict(reason_counts),
        "timeWithdrawnMjdTai_nonnull": withdrawn_nonnull,
        "evaluable_objects_lono": len(eval_objs_lono),
        "evaluable_rows_lono": eval_rows_lono,
        "evaluable_objects_causal": len(eval_objs_causal),
        "evaluable_rows_causal": eval_rows_causal,
        "minimum50_met_lono": len(eval_objs_lono) >= 50,
        "trigger_rows_dim": len(triggers_dim),
        "trigger_objects_dim": len({t["diaObjectId"] for t in triggers_dim}),
        "trigger_rows_flash": len(triggers_flash),
        "trigger_objects_flash": len({t["diaObjectId"] for t in triggers_flash}),
        "evaluable_series_lono": evaluable_series_lono,
        "scored_lookup_by_obj_band": scored_lookup_by_obj_band,
        "triggers_dim": sorted(triggers_dim, key=lambda x: -x["z_dim"]),
        "triggers_flash": sorted(triggers_flash, key=lambda x: -x["z_flash"]),
        "obj_summary": list(obj_summary.values()),
    }


def apply_v3_cross_stream_gates(res_src: dict[str, Any], res_fp: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Upgrade from V2 -> V3:
      1) Astrometric stability <= 0.40" & reliability >= 0.50 on /sources triggers
      2) Cross-stream co-confirmation between /sources and /fp (|dt| <= 0.05 d, same band,
         fp_ratio <= 0.80 for Dim or fp_ratio >= 1.40 for Flash)
    """
    fp_lookup = res_fp["scored_lookup_by_obj_band"]
    src_lookup = res_src["scored_lookup_by_obj_band"]

    veto_counts = {
        "raw_sources_triggers": len(res_src["triggers_dim"]) + len(res_src["triggers_flash"]),
        "raw_sources_dim": len(res_src["triggers_dim"]),
        "raw_sources_flash": len(res_src["triggers_flash"]),
        "veto_astrom_or_rel_src": 0,
        "veto_unconfirmed_in_fp": 0,
        "veto_no_fp_epoch_within_dt": 0,
        "v3_coconfirmed_epochs": 0,
        "v3_coconfirmed_dim_epochs": 0,
        "v3_coconfirmed_flash_epochs": 0,
        "raw_fp_triggers": len(res_fp["triggers_dim"]) + len(res_fp["triggers_flash"]),
        "fp_single_epoch_unmatched_src": 0,
        "fp_matched_src_epochs": 0,
    }

    coconfirmed_events: list[dict[str, Any]] = []
    seen_event_keys: set[tuple[str, str, float, str]] = set()
    centroid_offsets_all: list[float] = []

    for trig in res_src["triggers_dim"] + res_src["triggers_flash"]:
        c_off = trig.get("centroid_offset_arcsec")
        rel = trig.get("reliability")
        if c_off is not None:
            centroid_offsets_all.append(float(c_off))
        ast_ok = (c_off is not None and c_off <= V3_MAX_CENTROID_OFFSET_ARCSEC)
        rel_ok = (rel is not None and rel >= V3_MIN_RELIABILITY)
        if not (ast_ok and rel_ok):
            veto_counts["veto_astrom_or_rel_src"] += 1
            continue

        fp_obs = fp_lookup.get((trig["diaObjectId"], trig["band"]), [])
        best_fp = None
        best_dt = 999.0
        for fpo in fp_obs:
            if not fpo["evaluable"]:
                continue
            dt = abs(fpo["mjd"] - trig["mjd"])
            if dt <= V3_CROSS_MATCH_DT_DAYS and dt < best_dt:
                best_dt = dt
                best_fp = fpo

        if best_fp is None:
            veto_counts["veto_no_fp_epoch_within_dt"] += 1
            continue

        fp_ratio = best_fp["flux_ratio"]
        confirmed = (
            (trig["channel"] == "DIM" and fp_ratio <= V3_FP_DIM_CONFIRM_RATIO)
            or (trig["channel"] == "FLASH" and fp_ratio >= V3_FP_FLASH_CONFIRM_RATIO)
        )
        if not confirmed:
            veto_counts["veto_unconfirmed_in_fp"] += 1
            continue

        veto_counts["v3_coconfirmed_epochs"] += 1
        if trig["channel"] == "DIM":
            veto_counts["v3_coconfirmed_dim_epochs"] += 1
        else:
            veto_counts["v3_coconfirmed_flash_epochs"] += 1
        ekey = (trig["diaObjectId"], trig["band"], round(trig["mjd"], 4), trig["channel"])
        if ekey not in seen_event_keys:
            seen_event_keys.add(ekey)
            coconfirmed_events.append({
                **trig,
                "fp_obs_id": best_fp["obs_id"],
                "fp_match_dt_days": round(best_dt, 5),
                "fp_flux_ratio": round(fp_ratio, 5),
                "fp_z_dim": round(best_fp["z_dim"], 3),
                "fp_z_flash": round(best_fp["z_flash"], 3),
                "fp_trig_dim": bool(best_fp["trig_dim"]),
                "fp_trig_flash": bool(best_fp["trig_flash"]),
            })

    # Audit primary /fp triggers to measure how many have clean co-occurring /sources alerts
    for fpt in res_fp["triggers_dim"] + res_fp["triggers_flash"]:
        sobs = src_lookup.get((fpt["diaObjectId"], fpt["band"]), [])
        matched_src = any(abs(s["mjd"] - fpt["mjd"]) <= V3_CROSS_MATCH_DT_DAYS for s in sobs if s["evaluable"])
        if matched_src:
            veto_counts["fp_matched_src_epochs"] += 1
        else:
            veto_counts["fp_single_epoch_unmatched_src"] += 1

    # Collapse to unique candidate objects with aggregate stats
    by_obj: dict[str, dict[str, Any]] = {}
    for ev in coconfirmed_events:
        oid = ev["diaObjectId"]
        cur = by_obj.get(oid)
        sev = ev["z_dim"] if ev["channel"] == "DIM" else ev["z_flash"]
        if cur is None or sev > cur["max_severity_z"]:
            by_obj[oid] = {
                "diaObjectId": oid,
                "gaia_source_id": ev["gaia_source_id"],
                "field": ev["field"],
                "phot_g_mean_mag": ev["phot_g_mean_mag"],
                "bp_rp": ev["bp_rp"],
                "phot_variable_flag": ev["phot_variable_flag"],
                "primary_channel": ev["channel"],
                "primary_band": ev["band"],
                "peak_obs_id": ev["obs_id"],
                "peak_mjd": ev["mjd"],
                "flux_ratio": ev["flux_ratio"],
                "fp_flux_ratio": ev["fp_flux_ratio"],
                "mag_delta": ev["mag_delta"],
                "z_dim": ev["z_dim"],
                "z_flash": ev["z_flash"],
                "max_severity_z": sev,
                "reliability": ev["reliability"],
                "centroid_offset_arcsec": ev["centroid_offset_arcsec"],
                "ls_periodic": ev["ls_periodic"],
                "ls_period_d": ev["ls_period_d"],
                "n_coconfirmed_epochs": 1,
                "channels_seen": ev["channel"],
            }
        else:
            cur["n_coconfirmed_epochs"] += 1
            if ev["channel"] not in cur["channels_seen"]:
                cur["channels_seen"] = cur["channels_seen"] + "+" + ev["channel"]

    cand_rows = sorted(by_obj.values(), key=lambda x: -x["max_severity_z"])
    veto_counts["v3_coconfirmed_unique_objects"] = len(cand_rows)
    veto_counts["v3_coconfirmed_dim_objects"] = sum(1 for c in cand_rows if "DIM" in c["channels_seen"])
    veto_counts["v3_coconfirmed_flash_objects"] = sum(1 for c in cand_rows if "FLASH" in c["channels_seen"])
    veto_counts["centroid_offset_arcsec_median"] = round(float(np.median(centroid_offsets_all)), 4) if centroid_offsets_all else None
    return cand_rows, veto_counts


def run_injection_calibration_4800(
    evaluable_series: dict[tuple[str, str], list[dict[str, Any]]],
    seed: int = 20261127,
) -> dict[str, Any]:
    """
    4,800 seeded trials per stream (2,400 Dim + 2,400 Flash):
      400 real LONO-evaluable object-band series x 6 amplitudes per channel.
    """
    rng = np.random.default_rng(seed)
    all_keys = sorted(evaluable_series.keys())
    if not all_keys:
        return {"n_trials_total": 0}
    sample_idx = rng.choice(len(all_keys), size=min(400, len(all_keys)), replace=(len(all_keys) < 400))
    sampled_keys = [all_keys[int(i)] for i in sample_idx]
    # Ensure exact 400 stars x 6 amps = 2,400 trials per channel even if len(all_keys)<400
    while len(sampled_keys) < 400:
        sampled_keys.append(all_keys[int(rng.integers(0, len(all_keys)))])

    dim_amps = (0.35, 0.50, 0.75, 1.00, 1.50, 2.00)
    flash_amps = (0.55, 0.75, 1.00, 1.50, 2.00, 3.00)

    def run_channel(kind: str, amps: tuple[float, ...]) -> dict[str, Any]:
        grid = {f"{a:.2f}": {"trials": 0, "recovered": 0} for a in amps}
        tot_tr = tot_rec = 0
        for k in sampled_keys:
            obs = evaluable_series[k]
            mjds = np.array([o["mjd"] for o in obs], dtype=float)
            fluxes = np.array([o["flux"] for o in obs], dtype=float)
            f_med = float(np.median(fluxes))
            if f_med <= 0.0:
                continue
            for a in amps:
                idx = int(rng.integers(0, len(mjds)))
                inj = fluxes.copy()
                if kind == "dim":
                    inj[idx] = inj[idx] * (10.0 ** (-0.4 * a))
                else:
                    inj[idx] = inj[idx] + ((10.0 ** (0.4 * a)) - 1.0) * f_med
                sc = evaluate_object_band(obs, mode="lono", flux_override=inj)
                r = sc[idx]
                hit = bool(r["evaluable"] and (r["trig_dim"] if kind == "dim" else r["trig_flash"]))
                ck = f"{a:.2f}"
                grid[ck]["trials"] += 1
                tot_tr += 1
                if hit:
                    grid[ck]["recovered"] += 1
                    tot_rec += 1
        for v in grid.values():
            v["completeness"] = round(v["recovered"] / max(1, v["trials"]), 4)
        # Strong-regime completeness (>=0.50m Dim, >=0.75m Flash) and overall completeness
        strong_keys = ("0.50", "0.75", "1.00", "1.50", "2.00") if kind == "dim" else ("0.75", "1.00", "1.50", "2.00", "3.00")
        st_tr = sum(grid[sk]["trials"] for sk in strong_keys)
        st_rec = sum(grid[sk]["recovered"] for sk in strong_keys)
        return {
            "n_trials": tot_tr,
            "recovered": tot_rec,
            "completeness_all": round(tot_rec / max(1, tot_tr), 4),
            "completeness_strong": round(st_rec / max(1, st_tr), 4),
            "grid": grid,
        }

    dim_res = run_channel("dim", dim_amps)
    flash_res = run_channel("flash", flash_amps)
    return {
        "n_trials_total": dim_res["n_trials"] + flash_res["n_trials"],
        "dim_conditional": dim_res,
        "flash_conditional": flash_res,
    }


def _write_csv(path: Path, cols: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def main() -> int:
    cohort = list(csv.DictReader((RES / "N3_COHORT_1800_FROZEN.csv").open(encoding="utf-8")))
    ml_path = RES / "METHOD_LOCK.json"
    if ml_path.exists():
        ml = json.loads(ml_path.read_text(encoding="utf-8"))
        for rel, exp in ml.get("sha256", {}).items():
            actual = hashlib.sha256((WS / rel).read_bytes()).hexdigest()
            assert actual == exp, f"METHOD_LOCK mismatch on {rel}"

    raw_src = load_batches("n3_sources_")
    raw_fp = load_batches("n3_fp_")

    res_src = analyze_stream(cohort, raw_src, "sources", "r:diaSourceId")
    res_fp = analyze_stream(cohort, raw_fp, "fp", "r:diaForcedSourceId")

    coconfirmed, veto_stats = apply_v3_cross_stream_gates(res_src, res_fp)

    inj_src = run_injection_calibration_4800(res_src["evaluable_series_lono"], seed=20261127)
    inj_fp = run_injection_calibration_4800(res_fp["evaluable_series_lono"], seed=20261128)

    # Empirical astrometric/reliability pass fraction among clean evaluable /sources detections
    ev_src_all = [r for sc in res_src["scored_lookup_by_obj_band"].values() for r in sc if r["evaluable"]]
    v3_gate1_eff = sum(
        1 for r in ev_src_all
        if (r.get("centroid_offset_arcsec") is not None and r["centroid_offset_arcsec"] <= V3_MAX_CENTROID_OFFSET_ARCSEC)
        and (r.get("reliability") is not None and r["reliability"] >= V3_MIN_RELIABILITY)
    ) / max(1, len(ev_src_all))
    # Joint cross-stream completeness = C_src * C_fp * v3_gate1_eff
    c_src_dim = inj_src["dim_conditional"]["completeness_all"]
    c_src_fl = inj_src["flash_conditional"]["completeness_all"]
    c_fp_dim = inj_fp["dim_conditional"]["completeness_all"]
    c_fp_fl = inj_fp["flash_conditional"]["completeness_all"]

    n3_bounds = {
        "sources_dim": bayesian_limits(res_src["evaluable_objects_lono"], res_src["evaluable_objects_lono"] * c_src_dim),
        "sources_flash": bayesian_limits(res_src["evaluable_objects_lono"], res_src["evaluable_objects_lono"] * c_src_fl),
        "v3_coconfirmed_dim": bayesian_limits(res_src["evaluable_objects_lono"], res_src["evaluable_objects_lono"] * c_src_dim * c_fp_dim * v3_gate1_eff),
        "v3_coconfirmed_flash": bayesian_limits(res_src["evaluable_objects_lono"], res_src["evaluable_objects_lono"] * c_src_fl * c_fp_fl * v3_gate1_eff),
        "fp_dim": bayesian_limits(res_fp["evaluable_objects_lono"], res_fp["evaluable_objects_lono"] * c_fp_dim),
        "fp_flash": bayesian_limits(res_fp["evaluable_objects_lono"], res_fp["evaluable_objects_lono"] * c_fp_fl),
    }

    # Combine with R1 (300 zero-overlap DDF stars) -> 2,100 total stars
    rv2 = json.loads(RV2_SUMMARY_PATH.read_text(encoding="utf-8"))
    r1_lim = rv2["bayesian_limits"]
    combined_2100 = {
        "combined_stars_total": 300 + len(cohort),
        "sources_dim": bayesian_limits(
            r1_lim["sources_dim_conditional"]["n_eval"] + res_src["evaluable_objects_lono"],
            r1_lim["sources_dim_conditional"]["n_eff"] + n3_bounds["sources_dim"]["n_eff"],
        ),
        "sources_flash": bayesian_limits(
            r1_lim["sources_flash_conditional"]["n_eval"] + res_src["evaluable_objects_lono"],
            r1_lim["sources_flash_conditional"]["n_eff"] + n3_bounds["sources_flash"]["n_eff"],
        ),
        "fp_dim": bayesian_limits(
            r1_lim["fp_dim_conditional"]["n_eval"] + res_fp["evaluable_objects_lono"],
            r1_lim["fp_dim_conditional"]["n_eff"] + n3_bounds["fp_dim"]["n_eff"],
        ),
        "fp_flash": bayesian_limits(
            r1_lim["fp_flash_conditional"]["n_eval"] + res_fp["evaluable_objects_lono"],
            r1_lim["fp_flash_conditional"]["n_eff"] + n3_bounds["fp_flash"]["n_eff"],
        ),
    }

    # Write compact outputs
    obj_cols = [
        "diaObjectId", "gaia_source_id", "field", "phot_g_mean_mag", "bp_rp", "phot_variable_flag",
        "raw_rows", "clean_rows", "eval_rows_lono", "eval_rows_causal", "eval_bands",
        "n_trig_dim", "n_trig_flash", "max_z_dim", "max_z_flash", "min_ratio", "max_ratio",
    ]
    for tag, rdict in [("N3_SOURCES", res_src), ("N3_FP", res_fp)]:
        rows_out = []
        for x in rdict["obj_summary"]:
            xc = dict(x)
            xc["eval_bands"] = "+".join(sorted(set(xc["eval_bands"])))
            rows_out.append(xc)
        _write_csv(RES / f"{tag}_OBJECT_SUMMARY.csv", obj_cols, rows_out)

    cand_cols = list(coconfirmed[0].keys()) if coconfirmed else [
        "diaObjectId", "gaia_source_id", "field", "phot_g_mean_mag", "bp_rp", "phot_variable_flag",
        "primary_channel", "primary_band", "peak_obs_id", "peak_mjd", "flux_ratio", "fp_flux_ratio",
        "mag_delta", "z_dim", "z_flash", "max_severity_z", "reliability", "centroid_offset_arcsec",
        "ls_periodic", "ls_period_d", "n_coconfirmed_epochs", "channels_seen",
    ]
    _write_csv(RES / "N3_V3_COCONFIRMED_CANDIDATES.csv", cand_cols, coconfirmed)
    veto_stats["v3_gate1_empirical_efficiency"] = round(v3_gate1_eff, 4)
    (RES / "N3_V3_VETO_STATISTICS.json").write_text(json.dumps(veto_stats, indent=2) + "\n", encoding="utf-8")

    drop_keys = ("evaluable_series_lono", "scored_lookup_by_obj_band", "obj_summary", "triggers_dim", "triggers_flash")
    summary = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "detector_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "n3_sources": {k: v for k, v in res_src.items() if k not in drop_keys},
        "n3_fp": {k: v for k, v in res_fp.items() if k not in drop_keys},
        "v3_veto_funnel": veto_stats,
        "injection_sources": inj_src,
        "injection_fp": inj_fp,
        "bayesian_limits_n3": n3_bounds,
        "bayesian_limits_combined_v2_v3_2100stars": combined_2100,
        "verified_eti": 0,
    }
    (RES / "N3_DETECTOR_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
