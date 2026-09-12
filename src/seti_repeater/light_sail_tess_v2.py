"""LS7B correction-aware eligibility and additional pixel-domain trials.

The original LS7 arithmetic remains frozen in light_sail_tess.py.
"""
import numpy as np
from scipy.ndimage import shift

from .light_sail_tess import good_segments, pixel_diagnostic, pulse_shape, score_windows


def quality_mask(quality, finite, allowed_bits):
    quality = np.asarray(quality, dtype=np.int64)
    return ((quality & ~int(allowed_bits)) == 0) & np.asarray(finite, dtype=bool)


def eligibility(time, cadence, good, cfg):
    """Inspect timing/flags before screening; never choose anchors using flux."""
    segments = good_segments(time, cadence, good, cfg["cadence_seconds"])
    searchable = np.zeros(len(time), dtype=bool)
    candidates = []
    half = cfg["injections"]["context_half_samples"]
    guard = cfg["baseline_samples"] // 2
    for lo, hi in segments:
        if hi - lo >= cfg["baseline_samples"] + max(cfg["box_samples"]):
            searchable[lo + guard:hi - guard] = True
        candidates.extend(range(lo + half, hi - half))
    count = cfg["injections"]["anchors"]
    enough = len(candidates) >= count
    anchors = np.array(candidates)[np.linspace(0, len(candidates) - 1, count).astype(int)] if enough else np.array([], dtype=int)
    nonoverlap = bool(enough and np.all(np.diff(anchors) > 2 * half))
    # Index disjointness plus chronological separation protects against pathological IDs.
    separated = bool(enough and np.all(np.diff(time[anchors]) * 86400 >= (2*half + 1) * cfg["cadence_seconds"] * 0.99))
    span = float(time[anchors[-1]] - time[anchors[0]]) if enough else 0.0
    days = float(searchable.sum() * cfg["cadence_seconds"] / 86400)
    gates = {"minimum_searchable_days": days >= cfg["qualification"]["searchable_days_min"],
             "enough_anchor_indices": enough, "nonoverlapping_contexts": nonoverlap,
             "time_separation": separated, "minimum_anchor_span": span >= cfg["qualification"]["anchor_span_days_min"]}
    return {"pass": all(gates.values()), "gates": gates, "accepted_rows": int(np.count_nonzero(good)),
            "accepted_cadence_days": float(np.count_nonzero(good)*cfg["cadence_seconds"]/86400),
            "runs": len(segments), "longest_run_rows": max((b-a for a,b in segments), default=0),
            "searchable_rows": int(searchable.sum()), "searchable_cadence_days": days,
            "eligible_anchor_indices": len(candidates), "anchors": anchors.tolist(),
            "anchor_btjd": time[anchors].tolist(), "anchor_span_days": span}, segments, searchable


def match_trial(native_flux, injected_flux, seconds, centers, sigma, cfg):
    """Same fixed best-window and confounding rule as the original LS7 trials."""
    best, confounded = None, False
    original = score_windows(native_flux, sigma, cfg["baseline_samples"], cfg["box_samples"])
    modified = score_windows(injected_flux, sigma, cfg["baseline_samples"], cfg["box_samples"])
    for (width, starts, scores), (_, _, base) in zip(modified, original):
        mid = (seconds[starts] + seconds[starts + width - 1]) / 2
        match = np.min(np.abs(mid[:, None] - np.asarray(centers)[None, :]), axis=1) <= cfg["injections"]["match_tolerance_seconds"]
        js = np.flatnonzero(match)
        if not len(js):
            continue
        confounded |= bool(np.any(base[js] >= cfg["score_threshold"]))
        j = js[np.argmax(scores[js])]
        if best is None or scores[j] > best["score"]:
            best = {"start": int(starts[j]), "stop": int(starts[j] + width), "score": float(scores[j]),
                    "native_score_same_window": float(base[j])}
    if best is None:
        raise ValueError("no fixed matching window")
    return best, confounded


def shifted_profile(profile, aperture, displacement):
    """Bilinear subpixel shift, clipped to aperture, normalized to unit aperture flux."""
    moved = shift(profile, displacement, order=1, mode="constant", cval=0., prefilter=False)
    moved[~aperture] = 0
    if not np.all(np.isfinite(moved)) or moved.sum() <= 0:
        raise ValueError("invalid shifted profile")
    return moved / moved.sum()


def pointing_delta(image, displacement):
    """Shift a local scene; preserve its total stamp flux before aperture selection."""
    image = np.nan_to_num(image, nan=0.0)
    moved = shift(image, displacement, order=1, mode="nearest", prefilter=False)
    if image.sum() <= 0 or moved.sum() <= 0:
        raise ValueError("invalid scene for pointing control")
    moved *= image.sum() / moved.sum()
    return moved - image


def extended_trials(cube, aperture, time, noise, anchors, cfg):
    rows = []
    half = cfg["injections"]["context_half_samples"]
    ecfg = cfg["extended_trials"]
    for anchor_id, anchor in enumerate(anchors):
        segments = [n for n in noise if n["start"] + half <= anchor < n["stop"] - half]
        if len(segments) != 1:
            raise ValueError("preflight anchor absent from scored segments")
        sigma = segments[0]["sigma_e_per_s"]
        local = cube[anchor-half:anchor+half+1]
        seconds = (time[anchor-half:anchor+half+1] - time[anchor])*86400
        native = local[:, aperture].sum(axis=1)
        reference = np.nanmedian(local, axis=0)
        profile = np.zeros(aperture.shape)
        profile[aperture] = np.maximum(reference[aperture], 0)
        profile /= profile.sum()
        cases = [("off_profile", d) for d in ecfg["profile_shifts_yx"]]
        cases += [("pointing", d) for d in ecfg["pointing_shifts_yx"]]
        for phase in cfg["injections"]["phases_seconds"]:
            pulse, centers = pulse_shape(seconds, phase, ecfg["shape"], cfg["cadence_seconds"])
            for kind, displacement in cases:
                if kind == "off_profile":
                    delta = ecfg["amplitude_fraction"]*np.median(native)*shifted_profile(profile, aperture, displacement)
                else:
                    delta = pointing_delta(reference, displacement)
                injected = local + pulse[:, None, None]*delta
                best, confounded = match_trial(native, injected[:, aperture].sum(axis=1), seconds, centers, sigma, cfg)
                morphology = pixel_diagnostic(injected, aperture, best["start"], best["stop"], cfg["morphology"])
                detected = best["score"] >= cfg["score_threshold"]
                accepted = bool(detected and morphology["pass"])
                rows.append({"anchor": anchor_id, "native_index": int(anchor), "btjd": float(time[anchor]),
                             "kind": kind, "displacement_yx_pixels": displacement, "phase_seconds": phase,
                             "shape": ecfg["shape"], "actual_aperture_amplitude_fraction": float(delta[aperture].sum()/np.median(native)),
                             "screen_detected": bool(detected), "morphology_pass": morphology["pass"],
                             "accepted": accepted, "baseline_confounded": confounded,
                             "recovered": bool(accepted and not confounded), "best": best, "morphology": morphology})
    return rows
