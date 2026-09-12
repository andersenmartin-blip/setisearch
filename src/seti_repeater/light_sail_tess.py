"""LS7 fixed TESS screening and digital qualification; no SETI significance test."""
from itertools import combinations

import numpy as np
from scipy.ndimage import median_filter


def restore_cosmic_rays(flux, cadence, records, column, row):
    """Add back ground-removed e-/s by detector coordinates and cadence ID.

    Inputs have already been validated as the same flux unit. Duplicate records
    accumulate. Cadences absent from this product are counted, not reindexed.
    An in-product record outside the stamp is a structural error.
    """
    if len(np.unique(cadence)) != len(cadence):
        raise ValueError("duplicate cadence IDs")
    index = {int(c): i for i, c in enumerate(cadence)}
    ii = np.array([index.get(int(c), -1) for c in records["CADENCENO"]])
    keep = ii >= 0
    xx = np.asarray(records["RAWX"], dtype=int)[keep] - column
    yy = np.asarray(records["RAWY"], dtype=int)[keep] - row
    values = np.asarray(records["COSMIC_RAY"], dtype=float)[keep]
    if np.any((xx < 0) | (xx >= flux.shape[2]) | (yy < 0) | (yy >= flux.shape[1])):
        raise ValueError("cosmic-ray coordinate outside target stamp")
    if not np.all(np.isfinite(values)):
        raise ValueError("nonfinite cosmic-ray corrections")
    restored = np.array(flux, dtype=float, copy=True)
    np.add.at(restored, (ii[keep], yy, xx), values)
    return restored, {"records": len(ii), "applied_records": int(keep.sum()),
                      "absent_cadence_records": int((~keep).sum()),
                      "cadences_with_records": len(np.unique(ii[keep]))}


def good_segments(time, cadence, good, cadence_seconds):
    """Half-open runs; never bridge a quality exclusion, ID gap or time gap."""
    good = np.asarray(good, dtype=bool) & np.isfinite(time)
    ids = np.flatnonzero(good)
    if not len(ids):
        return []
    cuts = np.flatnonzero((np.diff(ids) != 1) | (np.diff(cadence[ids]) != 1)
                         | (np.diff(time[ids]) <= 0)
                         | (np.diff(time[ids]) * 86400 > 1.5 * cadence_seconds)) + 1
    return [(int(g[0]), int(g[-1] + 1)) for g in np.split(ids, cuts)]


def robust_sigma(values):
    d = np.diff(values)
    sigma = 1.482602218505602 * np.median(np.abs(d - np.median(d))) / np.sqrt(2)
    if not np.isfinite(sigma) or sigma <= 0:
        raise ValueError("nonpositive first-difference noise estimate")
    return float(sigma)


def score_windows(flux, sigma, baseline_samples, widths, sign=1):
    """Scores are robust screening statistics, not Gaussian significances."""
    baseline = median_filter(flux, size=baseline_samples, mode="nearest")
    residual = (flux - baseline) * sign
    guard = baseline_samples // 2
    for width in widths:
        if len(flux) < 2 * guard + width:
            continue
        scores = np.convolve(residual, np.ones(width), mode="valid") / (sigma * np.sqrt(width))
        starts = np.arange(guard, len(flux) - guard - width + 1)
        yield width, starts, scores[starts]


def screen(flux, segments, cfg, sign=1):
    """Return all retained non-overlapping triggers and fixed segment noise."""
    windows, noise = [], []
    for seg_id, (lo, hi) in enumerate(segments):
        if hi - lo < cfg["baseline_samples"] + max(cfg["box_samples"]):
            continue
        sigma = robust_sigma(flux[lo:hi])
        noise.append({"segment": seg_id, "start": lo, "stop": hi, "sigma_e_per_s": sigma})
        for width, starts, scores in score_windows(flux[lo:hi], sigma, cfg["baseline_samples"], cfg["box_samples"], sign):
            for j in np.flatnonzero(scores >= cfg["score_threshold"]):
                windows.append({"start": int(lo + starts[j]), "stop": int(lo + starts[j] + width),
                                "score": float(scores[j]), "sign": sign, "segment": seg_id})
    retained, used = [], np.zeros(len(flux), dtype=bool)
    for event in sorted(windows, key=lambda e: (-e["score"], e["start"], e["stop"])):
        lo, hi = event["start"], event["stop"]
        if np.any(used[lo:hi]):
            continue
        retained.append(event)
        used[max(0, lo - 2):min(len(flux), hi + 2)] = True
    overflow = len(retained) > cfg["event_cap_per_sign"]
    return retained[:cfg["event_cap_per_sign"]], noise, overflow


def pixel_diagnostic(cube, aperture, start, stop, thresholds, sign=1):
    """Compare local excess to an empirical stellar image; not flare rejection."""
    side = np.r_[max(0, start - 60):max(0, start - 5), min(len(cube), stop + 5):min(len(cube), stop + 60)]
    if len(side) < 20:
        return {"pass": False, "reason": "insufficient_sideband"}
    reference = np.nanmedian(cube[side], axis=0)
    excess = sign * (np.nanmean(cube[start:stop], axis=0) - reference)
    if not np.all(np.isfinite(reference[aperture])) or not np.all(np.isfinite(excess[aperture])):
        return {"pass": False, "reason": "nonfinite_aperture"}
    profile = np.maximum(reference[aperture], 0)
    delta = excess[aperture]
    positive = np.maximum(delta, 0)
    if profile.sum() <= 0 or positive.sum() <= 0 or delta.sum() <= 0:
        return {"pass": False, "reason": "nonpositive_excess_or_profile"}
    profile = profile / profile.sum()
    yy, xx = np.where(aperture)
    centroid = np.array([np.dot(positive, xx), np.dot(positive, yy)]) / positive.sum()
    expected = np.array([np.dot(profile, xx), np.dot(profile, yy)])
    cosine = float(np.dot(delta, profile) / (np.linalg.norm(delta) * np.linalg.norm(profile)))
    outside = excess[~aperture & np.isfinite(excess)]
    if len(outside) < 3:
        return {"pass": False, "reason": "insufficient_background_pixels"}
    background_ratio = float(abs(np.median(outside)) / np.mean(delta))
    shift = float(np.linalg.norm(centroid - expected))
    peak_fraction = float(positive.max() / positive.sum())
    passed = (cosine >= thresholds["cosine_min"] and shift <= thresholds["centroid_max_pixels"]
              and peak_fraction <= profile.max() + thresholds["peak_fraction_margin"]
              and background_ratio <= thresholds["background_ratio_max"])
    return {"pass": bool(passed), "cosine": cosine, "centroid_shift_pixels": shift,
            "peak_fraction": peak_fraction, "profile_peak_fraction": float(profile.max()),
            "background_ratio": background_ratio, "mean_excess_e_per_s": float(delta.sum())}


def integrated_pulse(time_seconds, center, duration, exposure_seconds=20.0):
    """Fraction of each contiguous exposure intersecting a unit top-hat pulse."""
    lo = np.maximum(time_seconds - exposure_seconds / 2, center - duration / 2)
    hi = np.minimum(time_seconds + exposure_seconds / 2, center + duration / 2)
    return np.maximum(hi - lo, 0) / exposure_seconds


def pulse_shape(time_seconds, center, shape, exposure_seconds):
    if shape == "doublet30sep87":
        centers, duration = [center - 43.5, center + 43.5], 30
    else:
        centers, duration = [center], int(shape.removeprefix("box"))
    return sum(integrated_pulse(time_seconds, c, duration, exposure_seconds) for c in centers), centers


def geometry_diagnostic(bjd, geometry):
    """1D circular common-node separation in stellar radii; no beam prediction."""
    coordinates = {p["name"]: p["a_au"] * np.sin(2 * np.pi * (np.asarray(bjd) - p["t0_bjd_tdb"]) / p["period_days"])
                   for p in geometry["planets"]}
    radius = geometry["stellar_radius_solar"] * 0.00465047
    return {a + "-" + b: np.abs(coordinates[a] - coordinates[b]) / radius
            for a, b in combinations(coordinates, 2)}


def qualify_injections(cube, aperture, time, noise, cfg):
    """Deterministic post-processing injections at flux-blind cadence anchors."""
    icfg = cfg["injections"]
    half = icfg["context_half_samples"]
    eligible = []
    sigmas = {}
    for seg in noise:
        for idx in range(seg["start"] + half, seg["stop"] - half):
            eligible.append(idx)
            sigmas[idx] = seg["sigma_e_per_s"]
    if len(eligible) < icfg["anchors"]:
        raise ValueError("not enough unbroken data for fixed injection anchors")
    anchors = np.array(eligible)[np.linspace(0, len(eligible) - 1, icfg["anchors"]).astype(int)]
    rows = []
    for anchor_id, anchor in enumerate(anchors):
        local = cube[anchor - half:anchor + half + 1]
        seconds = (time[anchor - half:anchor + half + 1] - time[anchor]) * 86400
        native = local[:, aperture].sum(axis=1)
        profile = np.zeros(aperture.shape)
        profile[aperture] = np.maximum(np.median(local[:, aperture], axis=0), 0)
        if profile.sum() <= 0:
            raise ValueError("nonpositive empirical profile")
        profile /= profile.sum()
        flux_level = float(np.median(native))
        sigma = sigmas[int(anchor)]
        native_windows = list(score_windows(native, sigma, cfg["baseline_samples"], cfg["box_samples"]))
        cases = [("stellar", shape, amp) for shape in icfg["shapes"] for amp in icfg["amplitudes"]]
        cases += [("single_pixel", "box30", 0.01), ("uniform", "box30", 0.01), ("null", "box30", 0.0)]
        for phase in icfg["phases_seconds"]:
            for kind, shape, amp in cases:
                pulse, centers = pulse_shape(seconds, phase, shape, cfg["cadence_seconds"])
                spatial = profile.copy()
                if kind == "single_pixel":
                    spatial[:] = 0
                    spatial.flat[np.argmax(profile)] = 1
                elif kind == "uniform":
                    spatial[:] = 1 / aperture.sum()
                injected = local + (amp * flux_level * pulse)[:, None, None] * spatial
                injected_flux = injected[:, aperture].sum(axis=1)
                best = None
                confounded = False
                for (width, starts, scores), (_, _, base_scores) in zip(
                    score_windows(injected_flux, sigma, cfg["baseline_samples"], cfg["box_samples"]), native_windows
                ):
                    mid = (seconds[starts] + seconds[starts + width - 1]) / 2
                    match = np.min(np.abs(mid[:, None] - np.asarray(centers)[None, :]), axis=1) <= icfg["match_tolerance_seconds"]
                    if not np.any(match):
                        continue
                    confounded |= bool(np.any(base_scores[match] >= cfg["score_threshold"]))
                    js = np.flatnonzero(match)
                    j = js[np.argmax(scores[js])]
                    if best is None or scores[j] > best["score"]:
                        best = {"start": int(starts[j]), "stop": int(starts[j] + width), "score": float(scores[j]),
                                "native_score_same_window": float(base_scores[j])}
                if best is None:
                    raise ValueError("no eligible injection match window")
                morphology = pixel_diagnostic(injected, aperture, best["start"], best["stop"], cfg["morphology"])
                detected = best["score"] >= cfg["score_threshold"]
                rows.append({"anchor": anchor_id, "native_index": int(anchor), "btjd": float(time[anchor]),
                             "kind": kind, "shape": shape, "amplitude_fraction": amp, "phase_seconds": phase,
                             "screen_detected": bool(detected), "morphology_pass": morphology["pass"],
                             "accepted": bool(detected and morphology["pass"]),
                             "baseline_confounded": confounded, "recovered": bool(detected and morphology["pass"] and not confounded),
                             "best": best, "morphology": morphology})
    return rows
