#!/usr/bin/env python3
"""
Locked Rubin Observatory (LSST) V2 Dual-Channel SETI Detector & Calibrator.
Implements:
  - Strict 64-bit string ID handling and separate sources vs forced-photometry (fp) streams
  - Flag hygiene + explicit timeWithdrawnMjdTai / FORCED_PIXEL_FLAGS_UNAVAILABLE tracking
  - Per-band LONO +/-180d (primary) and causal -180d (comparison) baselines
  - Channel A: Boyajian-like dimming (>= 0.30 mag, ratio <= 0.7585775750, Z_dim >= 5.0)
  - Channel B: Optical flash / laser-pulse (>= 0.50 mag, ratio >= 1.5848931925, Z_flash >= 6.0)
  - Lomb-Scargle periodicity & blue-flare triage on every triggered object
  - Synthetic injection-recovery calibration (>= 1,200 trials/channel) & analytical Bayesian f95
  - Spor R2 (538 Southern SETI catalog stars) host vs companion/saturation analysis
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from astropy.timeseries import LombScargle
from scipy.stats import beta as scipy_beta

WS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/analysis_workspace/work_rubin_v2_20261126_r1_ddf_and_r2_catalog")
INPUTS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/inputs_rubin_v2_20261126")
RESULTS = WS / "results"

RATIO_DIM_MAX = 10.0 ** (-0.4 * 0.30)      # 0.7585775750291837
Z_DIM_MIN = 5.0
RATIO_FLASH_MIN = 10.0 ** (0.4 * 0.50)     # 1.5848931924611136
Z_FLASH_MIN = 6.0
BASELINE_WINDOW_DAYS = 180.0
MIN_BASE_VISITS = 5
MIN_BASE_DATES = 3
MIN_BASE_SNR = 10.0
MAD_SCALE = 1.4826

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
    cos_a = max(-1.0, min(1.0, cos_a))
    return math.degrees(math.acos(cos_a)) * 3600.0


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
    edge_bad = any(
        parse_bool_strict(row.get(k)) is True
        for k in (
            "r:pixelFlags_bad",
            "r:pixelFlags_edge",
            "r:pixelFlags_offimage",
            "r:pixelFlags_nodata",
            "r:pixelFlags_interpolatedCenter",
        )
    )
    forced_bad = any(
        parse_bool_strict(row.get(k)) is True
        for k in (
            "r:forced_PsfFlux_flag",
            "r:forced_PsfFlux_flag_edge",
            "r:forced_PsfFlux_flag_noGoodPixels",
        )
    )
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
    """
    Evaluate clean observations of a single (diaObjectId, band, stream).
    obs must contain mjd, flux, err, obs_id, withdrawn.
    mode: 'lono' (0 < |dt| <= 180, day_j != day_i) or 'causal' (-180 <= dt < 0, day_j < day_i).
    """
    n = len(obs)
    if n == 0:
        return []
    mjds = np.array([o["mjd"] for o in obs], dtype=float)
    days = np.array([int(math.floor(m)) for m in mjds], dtype=np.int64)
    fluxes = np.array([o["flux"] for o in obs], dtype=float) if flux_override is None else flux_override
    errs = np.array([o["err"] for o in obs], dtype=float)

    scored = []
    for i in range(n):
        mi = mjds[i]
        di = days[i]
        fi = float(fluxes[i])
        ei = float(errs[i])

        if mode == "lono":
            mask = (days != di) & (np.abs(mjds - mi) <= BASELINE_WINDOW_DAYS)
        elif mode == "causal":
            mask = (days < di) & ((mi - mjds) <= BASELINE_WINDOW_DAYS) & (mjds < mi)
        else:
            raise ValueError(f"Unknown mode {mode}")

        base_f = fluxes[mask]
        base_e = errs[mask]
        base_d = days[mask]
        base_m = mjds[mask]

        n_base = int(len(base_f))
        n_base_dates = int(len(set(base_d.tolist())))
        evaluable = False
        reason = "OK"
        f0 = float("nan")
        sigma_rob = float("nan")
        ratio = float("nan")
        z_dim = float("nan")
        z_flash = float("nan")
        mag_delta = float("nan")
        trig_dim = False
        trig_flash = False
        nearest_gap = float("nan")

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
                denom = math.sqrt(sigma_rob * sigma_rob + ei * ei)
                z_dim = (f0 - fi) / denom
                z_flash = (fi - f0) / denom
                if ratio > 0.0:
                    mag_delta = -2.5 * math.log10(ratio)
                trig_dim = (ratio <= RATIO_DIM_MAX) and (z_dim >= Z_DIM_MIN)
                trig_flash = (ratio >= RATIO_FLASH_MIN) and (z_flash >= Z_FLASH_MIN)
                nearest_gap = float(np.min(np.abs(base_m - mi)))

        scored.append({
            "obs_id": obs[i]["obs_id"],
            "mjd": float(mi),
            "utc_day": int(di),
            "band": obs[i]["band"],
            "flux": fi,
            "flux_err": ei,
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
    files = sorted(INPUTS.glob(f"**/{prefix}*.json"))
    for fp in files:
        if fp.name.endswith(".receipt.json"):
            continue
        data = json.loads(fp.read_text(encoding="utf-8"), parse_int=str)
        if isinstance(data, list):
            rows.extend(data)
    return rows


def dedup_rows(rows: list[dict[str, Any]], id_key: str, stream: str) -> list[dict[str, Any]]:
    seen: dict[tuple[str, str, str], dict[str, Any]] = {}
    for r in rows:
        oid = str(r.get("r:diaObjectId") or "")
        sid = str(r.get(id_key) or "")
        mjd = str(r.get("r:midpointMjdTai") or "")
        band = str(r.get("r:band") or "")
        k = (oid, sid if sid else f"{mjd}:{band}", stream)
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
    best_freq = float(freq[idx])
    best_period = 1.0 / best_freq if best_freq > 0 else float("nan")
    try:
        fap = float(ls.false_alarm_probability(max_p))
    except Exception:
        fap = 1.0
    # Ignore 1-day solar alias windows (0.97-1.03 d, 0.49-0.51 d) unless ultra-strong non-alias
    is_day_alias = abs(best_period - 1.0) < 0.03 or abs(best_period - 0.5) < 0.015
    periodic = (fap < 1e-3) and (max_p > 0.35) and not is_day_alias
    return {
        "ls_tested": True,
        "best_period_d": round(best_period, 6),
        "ls_power": round(max_p, 5),
        "ls_fap": float(fap),
        "is_day_alias": is_day_alias,
        "periodic_flag": periodic,
    }


def bayesian_limits(n_eval: int, n_eff: float, k_det: int = 0) -> dict[str, Any]:
    if n_eff <= 0:
        return {"n_eval": n_eval, "n_eff": 0.0, "uniform_f95_pct": 100.0, "jeffreys_f95_pct": 100.0, "clopper_pearson_f95_pct": 100.0}
    u95 = float(scipy_beta.ppf(0.95, k_det + 1.0, n_eff + 1.0)) * 100.0
    j95 = float(scipy_beta.ppf(0.95, k_det + 0.5, n_eff + 0.5)) * 100.0
    cp95 = (1.0 - (0.05) ** (1.0 / max(1.0, n_eff))) * 100.0 if k_det == 0 else float(scipy_beta.ppf(0.95, k_det + 1.0, max(1.0, n_eff - k_det))) * 100.0
    return {
        "n_eval": int(n_eval),
        "n_eff": round(float(n_eff), 3),
        "uniform_f95_pct": round(u95, 4),
        "jeffreys_f95_pct": round(j95, 4),
        "clopper_pearson_f95_pct": round(cp95, 4),
    }


def run_injection_calibration(
    evaluable_series: dict[tuple[str, str], list[dict[str, Any]]],
    seed: int = 20261126,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    keys = sorted(evaluable_series.keys())
    if not keys:
        return {"n_trials_per_channel": 0, "dimming": {}, "flash": {}}

    dim_depths = (0.30, 0.60, 1.00)
    dim_durs = (1.0 / 24.0, 1.0, 7.0)  # days
    flash_amps = (0.50, 1.00, 2.00)
    flash_durs = (30.0 / 86400.0, 1.0 / 24.0)

    def trial_set(kind: str, mode_center: str, n_trials: int = 1200) -> dict[str, Any]:
        grid = (
            [(d, w) for d in dim_depths for w in dim_durs]
            if kind == "dim"
            else [(a, w) for a in flash_amps for w in flash_durs]
        )
        per_cell = {f"{p:.2f}mag_{w*24:.3f}h": {"trials": 0, "recovered": 0} for p, w in grid}
        total_rec = 0
        for t_idx in range(n_trials):
            k = keys[int(rng.integers(0, len(keys)))]
            obs = evaluable_series[k]
            mjds = np.array([o["mjd"] for o in obs], dtype=float)
            fluxes = np.array([o["flux"] for o in obs], dtype=float)
            f_med = float(np.median(fluxes))
            if f_med <= 0:
                continue
            amp_mag, dur_d = grid[t_idx % len(grid)]
            if mode_center == "epoch":
                t0 = float(mjds[int(rng.integers(0, len(mjds)))])
            else:
                t0 = float(rng.uniform(float(np.min(mjds)), float(np.max(mjds))))
            half_w = 0.5 * dur_d
            in_event = np.abs(mjds - t0) <= half_w
            inj = fluxes.copy()
            if kind == "dim":
                factor = 10.0 ** (-0.4 * amp_mag)
                inj[in_event] = inj[in_event] * factor
            else:
                # Pulse adds excess signal (10^(0.4*amp) - 1)*F_med cleanly above baseline
                excess = (10.0 ** (0.4 * amp_mag) - 1.0) * f_med
                inj[in_event] = inj[in_event] + excess

            scored = evaluate_object_band(obs, mode="lono", flux_override=inj)
            hit = False
            for r in scored:
                if not r["evaluable"]:
                    continue
                if abs(r["mjd"] - t0) <= half_w:
                    if kind == "dim" and r["trig_dim"]:
                        hit = True
                        break
                    if kind == "flash" and r["trig_flash"]:
                        hit = True
                        break
            ckey = f"{amp_mag:.2f}mag_{dur_d*24:.3f}h"
            per_cell[ckey]["trials"] += 1
            if hit:
                per_cell[ckey]["recovered"] += 1
                total_rec += 1
        for c in per_cell.values():
            c["completeness"] = round(c["recovered"] / max(1, c["trials"]), 4)
        return {
            "n_trials": n_trials,
            "recovered": total_rec,
            "completeness": round(total_rec / n_trials, 4),
            "grid": per_cell,
        }

    return {
        "n_trials_per_regime": 1200,
        "dim_conditional": trial_set("dim", "epoch", 1200),
        "dim_duty_cycle": trial_set("dim", "span", 1200),
        "flash_conditional": trial_set("flash", "epoch", 1200),
        "flash_duty_cycle": trial_set("flash", "span", 1200),
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
            clean_by_obj_band[(oid, str(r["r:band"]).strip())].append({
                "obs_id": str(r.get(id_key) or ""),
                "mjd": float(r["r:midpointMjdTai"]),
                "band": str(r["r:band"]).strip(),
                "flux": float(r["r:scienceFlux"]),
                "err": float(r["r:scienceFluxErr"]),
                "snr": safe_float(r.get("r:snr")),
                "reliability": safe_float(r.get("r:reliability")),
            })

    # Score both LONO +/-180d and causal -180d
    eval_objs_lono: set[str] = set()
    eval_objs_causal: set[str] = set()
    eval_rows_lono = 0
    eval_rows_causal = 0
    evaluable_series_lono: dict[tuple[str, str], list[dict[str, Any]]] = {}
    all_scored_lono: list[dict[str, Any]] = []
    triggers_dim: list[dict[str, Any]] = []
    triggers_flash: list[dict[str, Any]] = []
    obj_summary: dict[str, dict[str, Any]] = {}

    for oid in cohort_ids:
        obj_summary[oid] = {
            "diaObjectId": oid,
            "gaia_source_id": cohort_ids[oid].get("gaia_source_id", ""),
            "field": cohort_ids[oid].get("field", ""),
            "phot_g_mean_mag": cohort_ids[oid].get("phot_g_mean_mag", ""),
            "bp_rp": cohort_ids[oid].get("bp_rp", ""),
            "phot_variable_flag": cohort_ids[oid].get("phot_variable_flag", ""),
            "raw_rows": len(by_obj_raw.get(oid, [])),
            "clean_rows": 0,
            "eval_rows_lono": 0,
            "eval_rows_causal": 0,
            "eval_bands": [],
            "n_trig_dim": 0,
            "n_trig_flash": 0,
            "max_z_dim": None,
            "max_z_flash": None,
            "min_ratio": None,
            "max_ratio": None,
        }

    for (oid, band), obs in sorted(clean_by_obj_band.items()):
        obs.sort(key=lambda x: x["mjd"])
        obj_summary[oid]["clean_rows"] += len(obs)
        scored_l = evaluate_object_band(obs, mode="lono")
        scored_c = evaluate_object_band(obs, mode="causal")
        eval_c = [s for s in scored_c if s["evaluable"]]
        eval_rows_causal += len(eval_c)
        if eval_c:
            eval_objs_causal.add(oid)
            obj_summary[oid]["eval_rows_causal"] += len(eval_c)

        eval_l = [s for s in scored_l if s["evaluable"]]
        if eval_l:
            eval_objs_lono.add(oid)
            eval_rows_lono += len(eval_l)
            obj_summary[oid]["eval_rows_lono"] += len(eval_l)
            obj_summary[oid]["eval_bands"].append(band)
            evaluable_series_lono[(oid, band)] = obs

        for s in eval_l:
            s_rec = {"diaObjectId": oid, **s}
            all_scored_lono.append(s_rec)
            mz_d = obj_summary[oid]["max_z_dim"]
            obj_summary[oid]["max_z_dim"] = s["z_dim"] if mz_d is None else max(mz_d, s["z_dim"])
            mz_f = obj_summary[oid]["max_z_flash"]
            obj_summary[oid]["max_z_flash"] = s["z_flash"] if mz_f is None else max(mz_f, s["z_flash"])
            mr = obj_summary[oid]["min_ratio"]
            obj_summary[oid]["min_ratio"] = s["flux_ratio"] if mr is None else min(mr, s["flux_ratio"])
            xr = obj_summary[oid]["max_ratio"]
            obj_summary[oid]["max_ratio"] = s["flux_ratio"] if xr is None else max(xr, s["flux_ratio"])
            if s["trig_dim"]:
                triggers_dim.append(s_rec)
                obj_summary[oid]["n_trig_dim"] += 1
            if s["trig_flash"]:
                triggers_flash.append(s_rec)
                obj_summary[oid]["n_trig_flash"] += 1

    # Automated Lomb-Scargle triage on all triggered objects
    triggered_oids = sorted({t["diaObjectId"] for t in triggers_dim + triggers_flash})
    triage_by_obj: dict[str, dict[str, Any]] = {}
    for oid in triggered_oids:
        # Pick best-sampled band for Lomb-Scargle
        cand_bands = [(len(v), b, v) for (o, b), v in clean_by_obj_band.items() if o == oid]
        cand_bands.sort(reverse=True)
        ls_info = lomb_scargle_check(cand_bands[0][2]) if cand_bands else {}
        best_band = cand_bands[0][1] if cand_bands else ""

        # Check blue-flare dominance and persistence across all triggered epochs for this object
        o_dim = [t for t in triggers_dim if t["diaObjectId"] == oid]
        o_fl = [t for t in triggers_flash if t["diaObjectId"] == oid]
        fl_bands = collections.Counter(t["band"] for t in o_fl)
        dim_bands = collections.Counter(t["band"] for t in o_dim)
        g_var = str(cohort_ids[oid].get("phot_variable_flag") or "").upper()
        try:
            bp_rp = float(cohort_ids[oid].get("bp_rp") or "nan")
        except ValueError:
            bp_rp = float("nan")
        g_mag = cohort_ids[oid].get("phot_g_mean_mag", "")

        # Provisional automated astrophysical triage (before FITS cutout + SIMBAD)
        if g_var == "VARIABLE" or ls_info.get("periodic_flag"):
            auto_class = "ASTROPHYSICAL_VARIABLE_PERIODIC"
        elif o_fl and not o_dim and (not math.isnan(bp_rp) and bp_rp > 1.5) and (fl_bands.get("u", 0) + fl_bands.get("g", 0) + fl_bands.get("r", 0) >= 1) and len(o_fl) <= 3:
            auto_class = "ASTROPHYSICAL_FLARE_MDWARF_CANDIDATE"
        elif len(o_dim) >= 2 and len(dim_bands) >= 2:
            auto_class = "MULTI_BAND_DIMMING_HIGH_PRIORITY"
        elif len(o_dim) >= 1 and len(o_fl) >= 1:
            auto_class = "IRREGULAR_DIPPING_OR_VARIABLE_CANDIDATE"
        elif len(o_dim) == 1:
            auto_class = "SINGLE_EPOCH_DIMMING_VETTING"
        else:
            auto_class = "SINGLE_OR_MULTI_FLASH_VETTING"

        triage_by_obj[oid] = {
            "diaObjectId": oid,
            "gaia_source_id": cohort_ids[oid].get("gaia_source_id", ""),
            "field": cohort_ids[oid].get("field", ""),
            "ra_deg": cohort_ids[oid].get("ra_deg", ""),
            "dec_deg": cohort_ids[oid].get("dec_deg", ""),
            "phot_g_mean_mag": g_mag,
            "bp_rp": cohort_ids[oid].get("bp_rp", ""),
            "phot_variable_flag": g_var,
            "n_trig_dim": len(o_dim),
            "n_trig_flash": len(o_fl),
            "dim_bands": dict(dim_bands),
            "flash_bands": dict(fl_bands),
            "max_z_dim": round(max([t["z_dim"] for t in o_dim], default=0.0), 3),
            "max_z_flash": round(max([t["z_flash"] for t in o_fl], default=0.0), 3),
            "min_ratio_dim": round(min([t["flux_ratio"] for t in o_dim], default=1.0), 5),
            "max_ratio_flash": round(max([t["flux_ratio"] for t in o_fl], default=1.0), 3),
            "ls_best_band": best_band,
            **ls_info,
            "provisional_class": auto_class,
        }

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
        "forced_pixel_flags_available": (stream_name == "sources"),
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
        "all_scored_lono": all_scored_lono,
        "triggers_dim": sorted(triggers_dim, key=lambda x: -x["z_dim"]),
        "triggers_flash": sorted(triggers_flash, key=lambda x: -x["z_flash"]),
        "triage_by_obj": triage_by_obj,
        "obj_summary": list(obj_summary.values()),
    }


def main() -> int:
    r1_cohort = list(csv.DictReader((RESULTS / "R1_COHORT_FROZEN.csv").open(encoding="utf-8")))
    r1_ctrl = list(csv.DictReader((RESULTS / "R1_CONTROLS_FROZEN.csv").open(encoding="utf-8")))
    r2_cohort = list(csv.DictReader((RESULTS / "R2_SOUTHERN_538STARS_FROZEN.csv").open(encoding="utf-8")))

    # Verify METHOD_LOCK / IMPLEMENTATION_LOCK if present
    ml_path = RESULTS / "METHOD_LOCK.json"
    if ml_path.exists():
        ml = json.loads(ml_path.read_text(encoding="utf-8"))
        for rel, exp in ml.get("sha256", {}).items():
            actual = hashlib.sha256((WS / rel).read_bytes()).hexdigest()
            assert actual == exp, f"METHOD_LOCK mismatch on {rel}: {actual} != {exp}"

    raw_src = load_batches("r1_sources_")
    raw_fp = load_batches("r1_fp_")

    res_src = analyze_stream(r1_cohort, raw_src, "sources", "r:diaSourceId")
    res_fp = analyze_stream(r1_cohort, raw_fp, "fp", "r:diaForcedSourceId")

    ctrl_src = analyze_stream(r1_ctrl, raw_src, "sources", "r:diaSourceId")
    ctrl_fp = analyze_stream(r1_ctrl, raw_fp, "fp", "r:diaForcedSourceId")

    # Injection-recovery calibration on empirical evaluable sources & fp separately
    inj_src = run_injection_calibration(res_src["evaluable_series_lono"], seed=20261126)
    inj_fp = run_injection_calibration(res_fp["evaluable_series_lono"], seed=20261127)

    # Compute conservative occurrence-rate limits for zero-ETI after vetting
    # Note: we report both conditional-epoch N_eff and full survey-span duty-cycle N_eff!
    limits = {
        "sources_dim_conditional": bayesian_limits(
            res_src["evaluable_objects_lono"],
            res_src["evaluable_objects_lono"] * inj_src["dim_conditional"].get("completeness", 0.0),
        ),
        "sources_dim_duty_cycle": bayesian_limits(
            res_src["evaluable_objects_lono"],
            res_src["evaluable_objects_lono"] * inj_src["dim_duty_cycle"].get("completeness", 0.0),
        ),
        "sources_flash_conditional": bayesian_limits(
            res_src["evaluable_objects_lono"],
            res_src["evaluable_objects_lono"] * inj_src["flash_conditional"].get("completeness", 0.0),
        ),
        "sources_flash_duty_cycle": bayesian_limits(
            res_src["evaluable_objects_lono"],
            res_src["evaluable_objects_lono"] * inj_src["flash_duty_cycle"].get("completeness", 0.0),
        ),
        "fp_dim_conditional": bayesian_limits(
            res_fp["evaluable_objects_lono"],
            res_fp["evaluable_objects_lono"] * inj_fp["dim_conditional"].get("completeness", 0.0),
        ),
        "fp_flash_conditional": bayesian_limits(
            res_fp["evaluable_objects_lono"],
            res_fp["evaluable_objects_lono"] * inj_fp["flash_conditional"].get("completeness", 0.0),
        ),
    }

    # Spor R2 catalog cross-match evaluation
    r2_matches_path = INPUTS / "r2_catalog" / "r2_conesearch_matches.json"
    r2_matches = json.loads(r2_matches_path.read_text(encoding="utf-8"), parse_int=str)
    r2_raw_src = load_batches("r2_sources_")
    r2_raw_fp = load_batches("r2_fp_")
    r2_by_oid_src = collections.defaultdict(list)
    r2_by_oid_fp = collections.defaultdict(list)
    for row in dedup_rows(r2_raw_src, "r:diaSourceId", "sources"):
        r2_by_oid_src[str(row.get("r:diaObjectId") or "")].append(row)
    for row in dedup_rows(r2_raw_fp, "r:diaForcedSourceId", "fp"):
        r2_by_oid_fp[str(row.get("r:diaObjectId") or "")].append(row)

    r2_object_rows = []
    r2_pseudo_cohort = []
    for m in r2_matches.get("matches", []):
        oid = str(m["diaObjectId"])
        sep = float(m["separation_arcsec"])
        s_rows = r2_by_oid_src.get(oid, [])
        f_rows = r2_by_oid_fp.get(oid, [])
        sat_cnt = sum(1 for x in s_rows if parse_bool_strict(x.get("r:pixelFlags_saturated")) is True or parse_bool_strict(x.get("r:pixelFlags_saturatedCenter")) is True)
        clean_cnt = sum(1 for x in s_rows if check_source_quality(x)[0])
        assoc_class = "DIRECT_HOST_STAR_LE_2ARCSEC" if sep <= 2.0 else "NEARBY_COMPANION_OR_FIELD_2_10ARCSEC"
        if sat_cnt > 0 and sat_cnt >= clean_cnt:
            sat_note = "SATURATED_DOMINANT"
        elif sat_cnt > 0:
            sat_note = "PARTIAL_SATURATION"
        else:
            sat_note = "NO_SATURATION_FLAG"
        r2_object_rows.append({
            "star": m["star"],
            "common_name": m["common_name"],
            "dist_pc": m["dist_pc"],
            "star_ra_deg": m["star_ra_deg"],
            "star_dec_deg": m["star_dec_deg"],
            "diaObjectId": oid,
            "obj_ra_deg": m["obj_ra_deg"],
            "obj_dec_deg": m["obj_dec_deg"],
            "separation_arcsec": round(sep, 4),
            "association_class": assoc_class,
            "raw_source_rows": len(s_rows),
            "clean_source_rows": clean_cnt,
            "saturated_source_rows": sat_cnt,
            "saturation_status": sat_note,
            "raw_fp_rows": len(f_rows),
        })
        r2_pseudo_cohort.append({
            "diaObjectId": oid,
            "gaia_source_id": m["star"],
            "field": m["star"],
            "ra_deg": m["obj_ra_deg"],
            "dec_deg": m["obj_dec_deg"],
            "phot_g_mean_mag": "",
            "bp_rp": "",
            "phot_variable_flag": "",
        })

    r2_res_src = analyze_stream(r2_pseudo_cohort, r2_raw_src, "sources", "r:diaSourceId") if r2_pseudo_cohort else {}
    r2_res_fp = analyze_stream(r2_pseudo_cohort, r2_raw_fp, "fp", "r:diaForcedSourceId") if r2_pseudo_cohort else {}

    # Save tabular outputs (lightweight without embedding giant series dict)
    for tag, res in [("R1_SOURCES", res_src), ("R1_FP", res_fp)]:
        with (RESULTS / f"{tag}_OBJECT_SUMMARY.csv").open("w", newline="", encoding="utf-8") as fh:
            fn = [
                "diaObjectId", "gaia_source_id", "field", "phot_g_mean_mag", "bp_rp", "phot_variable_flag",
                "raw_rows", "clean_rows", "eval_rows_lono", "eval_rows_causal", "eval_bands",
                "n_trig_dim", "n_trig_flash", "max_z_dim", "max_z_flash", "min_ratio", "max_ratio",
            ]
            w = csv.DictWriter(fh, fieldnames=fn)
            w.writeheader()
            for r in res["obj_summary"]:
                rc = dict(r)
                rc["eval_bands"] = "+".join(sorted(set(rc["eval_bands"])))
                w.writerow(rc)

        with (RESULTS / f"{tag}_TRIGGERS_DIM.json").open("w", encoding="utf-8") as fh:
            json.dump(res["triggers_dim"], fh, indent=2)
        with (RESULTS / f"{tag}_TRIGGERS_FLASH.json").open("w", encoding="utf-8") as fh:
            json.dump(res["triggers_flash"], fh, indent=2)
        with (RESULTS / f"{tag}_TRIAGE.json").open("w", encoding="utf-8") as fh:
            json.dump(list(res["triage_by_obj"].values()), fh, indent=2)

    with (RESULTS / "R2_CATALOG_MATCHES.csv").open("w", newline="", encoding="utf-8") as fh:
        fn = [
            "star", "common_name", "dist_pc", "star_ra_deg", "star_dec_deg", "diaObjectId",
            "obj_ra_deg", "obj_dec_deg", "separation_arcsec", "association_class",
            "raw_source_rows", "clean_source_rows", "saturated_source_rows", "saturation_status", "raw_fp_rows",
        ]
        w = csv.DictWriter(fh, fieldnames=fn)
        w.writeheader()
        for r in r2_object_rows:
            w.writerow(r)

    summary = {
        "r1_sources": {k: v for k, v in res_src.items() if k not in ("evaluable_series_lono", "all_scored_lono", "obj_summary", "triggers_dim", "triggers_flash", "triage_by_obj")},
        "r1_fp": {k: v for k, v in res_fp.items() if k not in ("evaluable_series_lono", "all_scored_lono", "obj_summary", "triggers_dim", "triggers_flash", "triage_by_obj")},
        "r1_controls_sources": {k: v for k, v in ctrl_src.items() if k not in ("evaluable_series_lono", "all_scored_lono", "obj_summary", "triggers_dim", "triggers_flash", "triage_by_obj")},
        "r1_controls_fp": {k: v for k, v in ctrl_fp.items() if k not in ("evaluable_series_lono", "all_scored_lono", "obj_summary", "triggers_dim", "triggers_flash", "triage_by_obj")},
        "injection_sources": inj_src,
        "injection_fp": inj_fp,
        "bayesian_limits": limits,
        "r2_catalog": {
            "stars_queried": r2_matches.get("stars_queried", len(r2_cohort)),
            "stars_matched_within_10arcsec": len({r["star"] for r in r2_object_rows}),
            "matched_dia_objects": len(r2_object_rows),
            "direct_host_le_2arcsec": sum(1 for r in r2_object_rows if r["association_class"] == "DIRECT_HOST_STAR_LE_2ARCSEC"),
            "companion_2_10arcsec": sum(1 for r in r2_object_rows if r["association_class"] != "DIRECT_HOST_STAR_LE_2ARCSEC"),
            "sources_stream": {k: v for k, v in r2_res_src.items() if k not in ("evaluable_series_lono", "all_scored_lono", "obj_summary", "triggers_dim", "triggers_flash", "triage_by_obj")} if r2_res_src else {},
            "fp_stream": {k: v for k, v in r2_res_fp.items() if k not in ("evaluable_series_lono", "all_scored_lono", "obj_summary", "triggers_dim", "triggers_flash", "triage_by_obj")} if r2_res_fp else {},
        },
        "verified_eti": 0,
    }
    (RESULTS / "R1_R2_DETECTOR_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (RESULTS / "R2_SOURCES_TRIGGERS_DIM.json").write_text(json.dumps(r2_res_src.get("triggers_dim", []), indent=2) + "\n", encoding="utf-8")
    (RESULTS / "R2_SOURCES_TRIGGERS_FLASH.json").write_text(json.dumps(r2_res_src.get("triggers_flash", []), indent=2) + "\n", encoding="utf-8")
    (RESULTS / "R2_FP_TRIGGERS_DIM.json").write_text(json.dumps(r2_res_fp.get("triggers_dim", []), indent=2) + "\n", encoding="utf-8")
    (RESULTS / "R2_FP_TRIGGERS_FLASH.json").write_text(json.dumps(r2_res_fp.get("triggers_flash", []), indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
