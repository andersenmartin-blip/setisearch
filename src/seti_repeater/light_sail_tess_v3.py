"""LS7C uncertainty-weighted spatial competition and strength-matched trials.

Scores and weighted residuals are engineering diagnostics, not calibrated
probabilities. Original LS7 and LS7B implementations remain unchanged.
"""
from itertools import product

import numpy as np

from .light_sail_tess import pulse_shape, score_windows
from .light_sail_tess_v2 import pointing_delta, shifted_profile


def empirical_profile(reference, aperture):
    result = np.zeros(aperture.shape)
    result[aperture] = np.maximum(reference[aperture], 0)
    if not np.all(np.isfinite(result)) or result.sum() <= 0:
        raise ValueError("invalid empirical aperture profile")
    return result / result.sum()


def weighted_fit(delta, variance, templates):
    """Fit each nonnegative template amplitude plus a free constant background.

    Weighted centering eliminates the background analytically. Returns the best
    template, amplitude/error, background, and residual sum of squares.
    """
    y, v, p = np.asarray(delta), np.asarray(variance), np.atleast_2d(templates)
    if not np.all(np.isfinite(y)) or not np.all(np.isfinite(v)) or np.any(v <= 0) or not np.all(np.isfinite(p)):
        raise ValueError("invalid weighted-fit inputs")
    w = 1 / v
    y_mean = np.dot(y, w) / w.sum()
    p_mean = p @ w / w.sum()
    centered = p - p_mean[:, None]
    norm = (centered**2) @ w
    cross = centered @ (w * (y-y_mean))
    amp = np.divide(np.maximum(cross, 0), norm, out=np.zeros_like(norm), where=norm > 1e-24)
    chi0 = float(np.dot(w, (y-y_mean)**2))
    # Evaluate residuals directly to avoid catastrophic subtraction at high SNR.
    chi = np.sum(w * ((y-y_mean)[None, :] - amp[:, None]*centered)**2, axis=1)
    best = int(np.argmin(chi))
    return {"template_index": best, "amplitude": float(amp[best]),
            "amplitude_noise_score": float(amp[best]*np.sqrt(norm[best])),
            "background": float(y_mean-amp[best]*p_mean[best]),
            "chi2": float(chi[best]), "background_only_chi2": chi0}


def spatial_model(native, errors, aperture, start, stop, cfg):
    """Freeze a local model on sidebands, excluding the event and its guard.

    First differences never cross the gap between the two sidebands. Use the
    larger of empirical MAD noise and archived FLUX_ERR per pixel. A diagonal
    covariance approximation includes a Gaussian median-reference variance.
    """
    pcfg = cfg["spatial"]
    side_a = np.arange(max(0, start-60), max(0, start-5))
    side_b = np.arange(min(len(native), stop+5), min(len(native), stop+60))
    side = np.r_[side_a, side_b]
    if len(side_a) < 20 or len(side_b) < 20:
        raise ValueError("insufficient two-sided pixel context")
    pixels = np.all(np.isfinite(native[side]), axis=0)
    pixels &= np.all(np.isfinite(errors[side]) & (errors[side] > 0), axis=0)
    if not np.all(pixels[aperture]) or np.count_nonzero(pixels & ~aperture) < 3:
        raise ValueError("invalid aperture errors or insufficient background pixels")
    reference = np.zeros(aperture.shape)
    reference[pixels] = np.median(native[side][:, pixels], axis=0)
    d = np.concatenate([np.diff(native[a][:, pixels], axis=0) for a in (side_a, side_b)])
    empirical = 1.482602218505602*np.median(np.abs(d-np.median(d, axis=0)), axis=0)/np.sqrt(2)
    supplied = np.median(errors[side][:, pixels], axis=0)
    sigma = np.maximum(empirical, supplied)
    variance = sigma**2 * (1/(stop-start) + np.pi/(2*len(side)))
    profile = empirical_profile(reference, aperture)
    star = np.stack([shifted_profile(profile, aperture, d)[pixels] for d in pcfg["fit_shifts_yx"]])
    # Uniform changes are represented by the common free-background model.
    nuisance, labels = [np.zeros(pixels.sum())], ["uniform"]
    for y, x in zip(*np.where(aperture)):
        t = np.zeros(aperture.shape); t[y, x] = 1
        nuisance.append(t[pixels]); labels.append(f"single_pixel_{y}_{x}")
    for dy, dx in pcfg["pointing_template_shifts_yx"]:
        t = pointing_delta(reference, [dy, dx])
        for polarity in (1, -1):
            nuisance.append(polarity*t[pixels]); labels.append(f"pointing_{dy}_{dx}_{polarity}")
    return {"pixels": pixels, "reference": reference, "variance": variance,
            "star": star, "nuisance": np.stack(nuisance), "nuisance_labels": labels,
            "side_samples": len(side), "empirical_dominant_pixels": int(np.count_nonzero(empirical > supplied))}


def spatial_diagnostic(cube, start, stop, model, cfg, sign=1):
    delta = sign*(np.mean(cube[start:stop][:, model["pixels"]], axis=0)-model["reference"][model["pixels"]])
    if not np.all(np.isfinite(delta)):
        return {"pass": False, "reason": "nonfinite_event_pixels"}
    star = weighted_fit(delta, model["variance"], model["star"])
    nuisance = weighted_fit(delta, model["variance"], model["nuisance"])
    dof = len(delta)-2
    reduced = star["chi2"]/dof
    margin = nuisance["chi2"]-star["chi2"]
    pcfg = cfg["spatial"]
    gates = {"source_amplitude": star["amplitude_noise_score"] >= pcfg["source_score_min"],
             "weighted_residual": reduced <= pcfg["reduced_chi2_max"],
             "nuisance_separation": margin >= pcfg["nuisance_delta_chi2_min"]}
    return {"pass": bool(all(gates.values())), "gates": gates, "star": star,
            "best_shift_yx": pcfg["fit_shifts_yx"][star["template_index"]],
            "best_nuisance": model["nuisance_labels"][nuisance["template_index"]],
            "nuisance_chi2": nuisance["chi2"], "nuisance_delta_chi2": margin,
            "reduced_chi2": reduced, "residual_dof": dof, "pixels": len(delta),
            "side_samples": model["side_samples"],
            "empirical_dominant_pixels": model["empirical_dominant_pixels"]}


def matched_window(flux, seconds, centers, sigma, cfg, sign=1):
    best = None
    for width, starts, scores in score_windows(flux, sigma, cfg["baseline_samples"], cfg["box_samples"], sign):
        mid = (seconds[starts]+seconds[starts+width-1])/2
        js = np.flatnonzero(np.min(np.abs(mid[:, None]-np.asarray(centers)[None, :]), axis=1) <= cfg["injections"]["match_tolerance_seconds"])
        if len(js):
            j = js[np.argmax(scores[js])]
            if best is None or scores[j] > best["score"]:
                best = {"start": int(starts[j]), "stop": int(starts[j]+width), "score": float(scores[j])}
    if best is None:
        raise ValueError("no fixed matching window")
    return best


def strength_amplitude(native_flux, pulse, seconds, centers, sigma, target, cfg, sign=1):
    """Predeclared bracket/bisection on temporal strength only; no pixel feedback."""
    scfg = cfg["strength_trials"]
    base = matched_window(native_flux, seconds, centers, sigma, cfg, sign)
    level = float(np.median(native_flux))
    if not np.isfinite(level) or level <= 0:
        raise ValueError("nonpositive aperture baseline")
    if base["score"] >= target:
        return {"amplitude_e_per_s": 0., "matched": False, "reason": "native_at_or_above_target", "score": base["score"]}
    lo, hi = 0., level*scfg["maximum_aperture_fraction"]
    def score(a):
        return matched_window(native_flux+sign*a*pulse, seconds, centers, sigma, cfg, sign)["score"]
    if score(hi) < target:
        return {"amplitude_e_per_s": hi, "matched": False, "reason": "amplitude_cap", "score": score(hi)}
    for _ in range(scfg["bisection_iterations"]):
        mid = (lo+hi)/2
        if score(mid) < target:
            lo = mid
        else:
            hi = mid
    actual = score(hi)
    return {"amplitude_e_per_s": hi, "matched": bool(abs(actual-target) <= scfg["score_tolerance"]), "reason": "bisection", "score": actual}


def trial_specs(cfg):
    """One anchor/phase's fixed cases; every case has a stable integer index."""
    specs = []
    for shape, amp in product(cfg["injections"]["shapes"], cfg["injections"]["amplitudes"]):
        specs.append({"group": "fixed", "kind": "stellar", "shape": shape, "amplitude_fraction": amp, "shift_yx": [0., 0.]})
    profiles = [("stellar", [0., 0.])] + [("off_profile", d) for d in cfg["strength_trials"]["signal_shifts_yx"]]
    nuisance = [("single_pixel", [0., 0.]), ("block_2x2", [0., 0.]), ("uniform", [0., 0.])]
    nuisance += [("pointing", d) for d in cfg["strength_trials"]["pointing_shifts_yx"]]
    for shape, target, (kind, displacement) in product(cfg["strength_trials"]["shapes"], cfg["strength_trials"]["scores"], profiles+nuisance):
        specs.append({"group": "matched", "kind": kind, "shape": shape, "target_score": target, "shift_yx": displacement})
    specs.append({"group": "null", "kind": "null", "shape": "box30", "amplitude_fraction": 0., "shift_yx": [0., 0.]})
    return [{"case_index": i, **s} for i, s in enumerate(specs)]


def nuisance_pattern(kind, reference, profile, aperture, displacement):
    p = np.zeros(aperture.shape)
    if kind == "single_pixel":
        p.flat[np.argmax(profile)] = 1
    elif kind == "block_2x2":
        choices = [(float(profile[y:y+2, x:x+2].sum()), y, x) for y in range(p.shape[0]-1) for x in range(p.shape[1]-1)]
        _, y, x = max(choices, key=lambda a: a[0])
        p[y:y+2, x:x+2] = 1
    elif kind == "uniform":
        p[:] = 1
    elif kind == "pointing":
        p = pointing_delta(reference, displacement)
    else:
        raise ValueError("unknown nuisance kind")
    norm = float(p[aperture].sum())
    if not np.isfinite(norm) or abs(norm) < 1e-10:
        raise ValueError("nuisance has zero or invalid aperture projection")
    return p/abs(norm), (1 if norm > 0 else -1), abs(norm)


def run_anchor(cube, errors, aperture, time, anchor, anchor_id, sigma, cfg):
    half = cfg["injections"]["context_half_samples"]
    native = cube[anchor-half:anchor+half+1]
    err = errors[anchor-half:anchor+half+1]
    seconds = (time[anchor-half:anchor+half+1]-time[anchor])*86400
    native_flux = native[:, aperture].sum(axis=1)
    reference = np.zeros(aperture.shape)
    valid = np.all(np.isfinite(native), axis=0)
    reference[valid] = np.median(native[:, valid], axis=0)
    profile = empirical_profile(reference, aperture)
    level = float(np.median(native_flux))
    rows, models, strength_cache = [], {}, {}
    for phase in cfg["injections"]["phases_seconds"]:
        for spec in trial_specs(cfg):
            kind = spec["kind"]
            pulse, centers = pulse_shape(seconds, phase, spec["shape"], cfg["cadence_seconds"])
            if kind in ("stellar", "off_profile", "null"):
                pattern, sign, norm = shifted_profile(profile, aperture, spec["shift_yx"]), 1, 1.
            else:
                pattern, sign, norm = nuisance_pattern(kind, reference, profile, aperture, spec["shift_yx"])
            tuning = None
            if spec["group"] == "matched":
                key = (phase, spec["shape"], spec["target_score"], sign)
                if key not in strength_cache:
                    strength_cache[key] = strength_amplitude(native_flux, pulse, seconds, centers, sigma, spec["target_score"], cfg, sign)
                tuning = strength_cache[key]
                amplitude = tuning["amplitude_e_per_s"]
            else:
                amplitude = level*spec["amplitude_fraction"]
            injected = native + (amplitude*pulse)[:, None, None]*pattern
            best = matched_window(injected[:, aperture].sum(axis=1), seconds, centers, sigma, cfg, sign)
            original = matched_window(native_flux, seconds, centers, sigma, cfg, sign)
            confounded = bool(original["score"] >= cfg["score_threshold"])
            key = (best["start"], best["stop"])
            if key not in models:
                models[key] = spatial_model(native, err, aperture, *key, cfg)
            spatial = spatial_diagnostic(injected, *key, models[key], cfg, sign)
            detected = best["score"] >= cfg["score_threshold"]
            accepted = bool(detected and spatial["pass"])
            strength_ok = None if tuning is None else bool(tuning["matched"] and abs(best["score"]-spec["target_score"]) <= cfg["strength_trials"]["score_tolerance"])
            rows.append({**spec, "trial_id": f"a{anchor_id:02d}_p{phase:g}_c{spec['case_index']:02d}",
                         "anchor": anchor_id, "native_index": int(anchor), "btjd": float(time[anchor]),
                         "phase_seconds": phase, "sign": sign, "sigma_e_per_s": sigma,
                         "actual_aperture_amplitude_fraction": float(sign*amplitude/level),
                         "pattern_multiplier": float(amplitude/norm), "tuning": tuning,
                         "strength_matched": strength_ok, "best": best, "native_best": original,
                         "screen_detected": bool(detected), "spatial_pass": spatial["pass"],
                         "accepted": accepted, "baseline_confounded": confounded,
                         "recovered": bool(accepted and not confounded), "spatial": spatial})
    return rows


def accounting(rows, cfg):
    """Explicit denominators; retain confounded and unmatched cases."""
    groups = []
    keys = sorted({(r["group"], r["kind"], r["shape"], r.get("amplitude_fraction", r.get("target_score", 0))) for r in rows})
    for group, kind, shape, level in keys:
        selected = [r for r in rows if (r["group"], r["kind"], r["shape"], r.get("amplitude_fraction", r.get("target_score", 0))) == (group, kind, shape, level)]
        groups.append({"group": group, "kind": kind, "shape": shape, "level": level, "trials": len(selected),
                       **{k: sum(bool(r[k]) for r in selected) for k in ("screen_detected", "accepted", "recovered", "baseline_confounded", "strength_matched")}})
    gates = {"complete_trial_count": len(rows) == cfg["qualification"]["expected_trials"],
             "unique_trial_ids": len({r["trial_id"] for r in rows}) == len(rows),
             "all_strengths_matched": all(r["strength_matched"] for r in rows if r["group"] == "matched")}
    q = cfg["qualification"]
    for level in cfg["strength_trials"]["scores"]:
        for kind in ("stellar", "off_profile", "single_pixel", "block_2x2", "uniform", "pointing"):
            subset = [r for r in rows if r["group"] == "matched" and r["target_score"] == level and r["kind"] == kind]
            signal = kind in ("stellar", "off_profile")
            fraction = sum(r["recovered" if signal else "accepted"] for r in subset)/len(subset) if subset else None
            threshold = q["primary_recovery_min" if kind == "stellar" else "off_profile_recovery_min"] if signal else q["nuisance_acceptance_max_per_kind_per_level"]
            gates[f"{kind}_{level:g}"] = fraction is not None and (fraction >= threshold if signal else fraction <= threshold)
    bright = [r for r in rows if r["group"] == "fixed" and r["amplitude_fraction"] == .1 and r["shape"] != "doublet30sep87"]
    gates["ten_percent_single_recovery"] = bool(bright and sum(r["recovered"] for r in bright)/len(bright) >= q["primary_recovery_min"])
    signals = [r for r in rows if r["kind"] in ("stellar", "off_profile")]
    gates["signal_confounding"] = bool(signals and sum(r["baseline_confounded"] for r in signals)/len(signals) <= q["confounded_fraction_max"])
    gates["null_acceptance"] = not any(r["accepted"] for r in rows if r["kind"] == "null")
    return {"total_trials": len(rows), "groups": groups}, gates
