#!/usr/bin/env python3
"""Independent audit of the frozen LS7Z cluster-1 morphology study."""
import json
import math
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
L2 = ROOT / "results_ls7x_l2_pilot"
L1 = ROOT / "results_ls7y_l1_followup"
OUT = ROOT / "results_ls7z_morphology"

ROW = struct.Struct(">26sddddii7d4f")
assert ROW.size == 138

FIRST = 171
STOP = 202
EVENT_G = np.arange(185, 188)
SIDE_G = np.r_[np.arange(171, 183), np.arange(190, 202)]
EVENT = EVENT_G - FIRST
SIDE = SIDE_G - FIRST
XOFF = 715.0
YOFF = 181.0
RADII = [3.0, 5.0, 8.0, 12.0, 18.0, 25.0, 35.0]
ANNULI = [(0.0, 5.0), (5.0, 12.0), (12.0, 25.0), (25.0, 35.0)]
L2_INDEX = {
    "FLUX": 3, "FLUXERR": 4, "DARK": 7, "BACKGROUND": 8,
    "CONTA_LC": 9, "CONTA_LC_ERR": 10, "SMEARING_LC": 11,
    "SMEARING_LC_ERR": 12, "ROLL_ANGLE": 13,
    "LOCATION_X": 14, "LOCATION_Y": 15, "CENTROID_X": 16, "CENTROID_Y": 17,
}
RTOL = 5e-8
ATOL = 2e-6


def parse_table(raw):
    rows = list(ROW.iter_unpack(raw))
    assert len(rows) == 432
    out = {"BJD_TIME": np.array([r[2] for r in rows], dtype=float)}
    for name, idx in L2_INDEX.items():
        out[name] = np.array([r[idx] for r in rows], dtype=float)
    return out


def mask(cx, cy, radius):
    yy, xx = np.mgrid[0:200, 0:200]
    return (xx - cx) ** 2 + (yy - cy) ** 2 <= radius ** 2


def line_fit(times, values, side, event):
    values = np.asarray(values, float)
    if not np.isfinite(values[np.r_[side, event]]).all():
        return {"available": False}
    t0 = float(np.mean(times[event]))
    xs = (times[side] - t0) * 86400.0
    xe = (times[event] - t0) * 86400.0
    y = values[side]
    n = float(len(xs))
    sx = float(np.sum(xs)); sxx = float(np.dot(xs, xs))
    sy = float(np.sum(y)); sxy = float(np.dot(xs, y))
    det = n * sxx - sx * sx
    assert det != 0.0
    b0 = (sy * sxx - sx * sxy) / det
    b1 = (n * sxy - sx * sy) / det
    pred = b0 + b1 * xe
    residual = y - (b0 + b1 * xs)
    med = float(np.median(residual))
    mad = float(1.4826 * np.median(np.abs(residual - med)))
    excess = float(np.sum(values[event] - pred))
    scale = max(
        float(np.max(np.abs(values[side]))),
        float(np.max(np.abs(pred))),
        float(np.finfo(float).tiny),
    )
    zero_floor = float(64.0 * np.finfo(float).eps * scale)
    mad_is_zero = bool(mad <= zero_floor)
    return {
        "available": True,
        "event_sum": float(np.sum(values[event])),
        "predicted_event_sum": float(np.sum(pred)),
        "event_excess": excess,
        "side_median": float(np.median(y)),
        "side_residual_sigma_mad": mad,
        "normalization_zero_floor": zero_floor,
        "normalization_mad_treated_as_zero": mad_is_zero,
        "normalized_event_excess": (
            float(excess / (mad * math.sqrt(3.0)))
            if (not mad_is_zero and mad > 0 and np.isfinite(mad)) else None
        ),
        "baseline_coefficients": [float(b0), float(b1)],
    }


def pixel_map(times, cube):
    used = np.r_[SIDE, EVENT]
    ok = np.isfinite(cube[used]).all(axis=0)
    out = np.full((200, 200), np.nan)
    if not ok.any():
        return out, ok
    t0 = float(np.mean(times[EVENT]))
    xs = (times[SIDE] - t0) * 86400.0
    xe = (times[EVENT] - t0) * 86400.0
    y = cube[SIDE][:, ok]
    n = float(len(xs)); sx = float(np.sum(xs)); sxx = float(np.dot(xs, xs))
    det = n * sxx - sx * sx
    sy = np.sum(y, axis=0)
    sxy = xs @ y
    b0 = (sy * sxx - sx * sxy) / det
    b1 = (n * sxy - sx * sy) / det
    pred_sum = len(EVENT) * b0 + float(np.sum(xe)) * b1
    obs_sum = np.sum(cube[EVENT][:, ok], axis=0)
    out[ok] = obs_sum - pred_sum
    return out, ok


def weighted_shape(E, use, cx, cy, absolute=False):
    if absolute:
        w = np.where(use, np.abs(E), 0.0)
    else:
        w = np.where(use, np.maximum(E, 0.0), 0.0)
    total = float(np.sum(w))
    if total <= 0:
        return {"available": False, "weight_sum": total}
    yy, xx = np.mgrid[0:200, 0:200]
    mx = float(np.sum(w * xx) / total)
    my = float(np.sum(w * yy) / total)
    dx = xx - mx; dy = yy - my
    cxx = float(np.sum(w * dx * dx) / total)
    cyy = float(np.sum(w * dy * dy) / total)
    cxy = float(np.sum(w * dx * dy) / total)
    trace = cxx + cyy
    disc = math.sqrt(max((cxx - cyy) ** 2 + 4.0 * cxy * cxy, 0.0))
    minor2 = max((trace - disc) / 2.0, 0.0)
    major2 = max((trace + disc) / 2.0, 0.0)
    minor = math.sqrt(minor2); major = math.sqrt(major2)
    return {
        "available": True,
        "weight_sum": total,
        "centroid_xy": [mx, my],
        "offset_from_target_pixels": float(math.hypot(mx - cx, my - cy)),
        "second_moment": [[cxx, cxy], [cxy, cyy]],
        "major_rms_pixels": float(major),
        "minor_rms_pixels": float(minor),
        "axis_ratio_major_over_minor": (float(major / minor) if minor > 0 else None),
    }


def projection(E, use):
    e = np.where(use, E, 0.0)
    energy = float(np.sum(e * e))
    if energy <= 0:
        return {"available": False, "energy": energy,
                "row_constant_energy_fraction": None,
                "column_constant_energy_fraction": None}
    row_energy = 0.0
    for y in range(200):
        m = use[y]
        if m.any():
            mean = float(np.mean(E[y, m]))
            row_energy += int(m.sum()) * mean * mean
    col_energy = 0.0
    for x in range(200):
        m = use[:, x]
        if m.any():
            mean = float(np.mean(E[m, x]))
            col_energy += int(m.sum()) * mean * mean
    return {
        "available": True,
        "energy": energy,
        "row_constant_energy_fraction": float(row_energy / energy),
        "column_constant_energy_fraction": float(col_energy / energy),
    }


def radial(E, ok, cx, cy):
    pos_total = float(np.sum(np.maximum(E[ok], 0.0)))
    l1_total = float(np.sum(np.abs(E[ok])))
    rows = {}
    for radius in RADII:
        geom = mask(cx, cy, radius)
        use = geom & ok
        vals = E[use]
        pos = float(np.sum(np.maximum(vals, 0.0))) if len(vals) else 0.0
        neg = float(np.sum(np.maximum(-vals, 0.0))) if len(vals) else 0.0
        l1 = pos + neg
        rows[str(int(radius))] = {
            "signed_sum": float(np.sum(vals)) if len(vals) else 0.0,
            "positive_sum": pos,
            "negative_magnitude": neg,
            "absolute_l1_sum": l1,
            "positive_fraction_of_full": (float(pos / pos_total) if pos_total > 0 else None),
            "absolute_l1_fraction_of_full": (float(l1 / l1_total) if l1_total > 0 else None),
            "eligible_pixels": int(use.sum()),
            "geometric_pixels": int(geom.sum()),
        }
    return {
        "full_common_eligible_positive_sum": pos_total,
        "full_common_eligible_absolute_l1_sum": l1_total,
        "radii": rows,
    }


def annuli(E, ok, cx, cy):
    yy, xx = np.mgrid[0:200, 0:200]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    out = {}
    for lo, hi in ANNULI:
        geom = (d <= hi) if lo == 0 else ((d > lo) & (d <= hi))
        use = geom & ok
        vals = E[use]
        out[f"{int(lo)}_{int(hi)}"] = {
            "signed_sum": float(np.sum(vals)) if len(vals) else 0.0,
            "absolute_l1_sum": float(np.sum(np.abs(vals))) if len(vals) else 0.0,
            "positive_sum": float(np.sum(np.maximum(vals, 0.0))) if len(vals) else 0.0,
            "eligible_pixels": int(use.sum()),
            "geometric_pixels": int(geom.sum()),
        }
    return out


def svd_fit(y, columns, names):
    X = np.column_stack(columns)
    U, s, vt = np.linalg.svd(X, full_matrices=False)
    tol = float(s[0] * max(X.shape) * np.finfo(float).eps) if len(s) else 0.0
    keep = s > tol
    rank = int(np.sum(keep))
    coeff = np.zeros(X.shape[1])
    if rank:
        coeff = vt[keep].T @ ((U[:, keep].T @ y) / s[keep])
    pred = X @ coeff
    residual = y - pred
    sse = float(np.sum(residual * residual))
    sst0 = float(np.sum(y * y))
    return {
        "names": names,
        "coefficients": [float(x) for x in coeff],
        "rank": rank,
        "condition_number": (float(s[0] / s[-1]) if len(s) and s[-1] > 0 else None),
        "pixels": int(len(y)),
        "residual_rms": float(math.sqrt(sse / len(y))),
        "squared_l2_explained_fraction": (float(1.0 - sse / sst0) if sst0 > 0 else None),
    }


def cos(a, b):
    den = float(math.sqrt(float(np.dot(a, a))) * math.sqrt(float(np.dot(b, b))))
    return float(np.dot(a, b) / den) if den > 0 else None


def decomposition(E, ok, side_mean, cx, cy):
    yy, xx = np.mgrid[0:200, 0:200]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    bgmask = (d > 30.0) & (d <= 40.0) & ok & np.isfinite(side_mean)
    if not bgmask.any():
        return {"available": False, "reason": "empty_background_annulus"}
    bg = float(np.median(side_mean[bgmask]))
    P = np.full((200, 200), np.nan)
    P[ok] = side_mean[ok] - bg

    dx = np.full_like(P, np.nan)
    dy = np.full_like(P, np.nan)
    for y in range(200):
        for x in range(1, 199):
            if np.isfinite(P[y, x-1]) and np.isfinite(P[y, x+1]):
                dx[y, x] = (P[y, x+1] - P[y, x-1]) / 2.0
    for y in range(1, 199):
        for x in range(200):
            if np.isfinite(P[y-1, x]) and np.isfinite(P[y+1, x]):
                dy[y, x] = (P[y+1, x] - P[y-1, x]) / 2.0

    fit_geom = d <= 25.0
    fit = fit_geom & ok & np.isfinite(E) & np.isfinite(P) & np.isfinite(dx) & np.isfinite(dy)
    n = int(fit.sum())
    if n < 10:
        return {"available": False, "reason": "insufficient_common_fit_pixels", "pixels": n}
    e = E[fit]; p = P[fit]; vx = dx[fit]; vy = dy[fit]; ones = np.ones(n)
    return {
        "available": True,
        "background_annulus_median": bg,
        "fit_pixels": n,
        "fit_geometric_pixels": int(fit_geom.sum()),
        "fit_pixel_fraction": float(n / fit_geom.sum()),
        "cosine_similarity": {"P": cos(e, p), "Dx": cos(e, vx), "Dy": cos(e, vy)},
        "models": {
            "brightness": svd_fit(e, [p, ones], ["P", "constant"]),
            "shift": svd_fit(e, [vx, vy, ones], ["Dx", "Dy", "constant"]),
            "combined": svd_fit(e, [p, vx, vy, ones], ["P", "Dx", "Dy", "constant"]),
        },
    }


def compare(expected, saved, label, diffs):
    count = 0
    if expected is None:
        assert saved is None, (label, expected, saved)
    elif isinstance(expected, bool):
        assert saved is expected, (label, expected, saved)
    elif isinstance(expected, dict):
        assert isinstance(saved, dict), label
        for key, value in expected.items():
            assert key in saved, (label, key)
            count += compare(value, saved[key], f"{label}.{key}", diffs)
    elif isinstance(expected, list):
        assert len(expected) == len(saved), label
        for i, value in enumerate(expected):
            count += compare(value, saved[i], f"{label}[{i}]", diffs)
    elif isinstance(expected, (int, float)):
        a = float(expected); b = float(saved)
        delta = abs(a - b)
        diffs[label] = max(diffs.get(label, 0.0), delta)
        assert math.isclose(a, b, rel_tol=RTOL, abs_tol=ATOL), (label, a, b)
        count += 1
    else:
        assert expected == saved, (label, expected, saved)
    return count


def main():
    saved = json.loads((OUT / "summary.json").read_text())
    assert saved["stage"] == "LS7Z_CLUSTER1_MORPHOLOGY"
    assert saved["status"] == "COMPLETE_UNAUDITED"
    assert saved["new_archive_science_bytes"] == 0
    assert saved["other_apertures_opened"] is False
    assert saved["raw_imagettes_opened"] is False
    assert saved["other_visits_opened"] is False

    table = parse_table((L2 / "lightcurve_table.bin").read_bytes())
    times_all = table["BJD_TIME"]
    component = {name: line_fit(times_all, table[name], SIDE_G, EVENT_G) for name in L2_INDEX}

    raw = (L1 / "SCI_COR_SubArray_cluster1_rows_171_201.bin").read_bytes()
    assert len(raw) == 31 * 200 * 200 * 8
    cube = np.frombuffer(raw, dtype=">f8").reshape(31, 200, 200).astype(float)
    times = times_all[FIRST:STOP]
    E, ok = pixel_map(times, cube)

    side_ok = np.isfinite(cube[SIDE]).all(axis=0)
    side_mean = np.full((200, 200), np.nan)
    side_mean[side_ok] = np.mean(cube[SIDE][:, side_ok], axis=0)

    with np.load(OUT / "cluster1_morphology_arrays.npz") as arr:
        saved_e = np.asarray(arr["cor_event_excess"], float)
        saved_ok = np.asarray(arr["eligible"], bool)
        saved_mean = np.asarray(arr["sideband_mean_cor"], float)
    assert np.array_equal(ok, saved_ok)
    assert np.array_equal(np.isnan(E), np.isnan(saved_e))
    assert np.array_equal(np.isnan(side_mean), np.isnan(saved_mean))
    finite_e = np.isfinite(E)
    finite_m = np.isfinite(side_mean)
    assert np.allclose(E[finite_e], saved_e[finite_e], rtol=RTOL, atol=ATOL)
    assert np.allclose(side_mean[finite_m], saved_mean[finite_m], rtol=RTOL, atol=ATOL)

    prior = np.load(L1 / "cluster_1_event_excess_maps.npz")
    prior_e = np.asarray(prior["cor"], float)
    prior_ok = np.asarray(prior["cor_eligible"], bool)
    assert np.array_equal(ok, prior_ok)
    prior_diff = float(np.max(np.abs(E[ok] - prior_e[ok]))) if ok.any() else 0.0

    # LS7Z explicitly promotes decoded float32 centroid values to float64 before averaging.
    cx0 = float(np.mean(table["CENTROID_X"][EVENT_G].astype(float))) - XOFF
    cy0 = float(np.mean(table["CENTROID_Y"][EVENT_G].astype(float))) - YOFF

    conventions = {}
    for label, shift in (("C0", 0.0), ("C1", -1.0)):
        cx = cx0 + shift; cy = cy0 + shift
        r25 = mask(cx, cy, 25.0) & ok
        r35 = mask(cx, cy, 35.0) & ok
        conventions[label] = {
            "target_center_xy": [cx, cy],
            "radial": radial(E, ok, cx, cy),
            "annuli": annuli(E, ok, cx, cy),
            "shape_positive_r25": weighted_shape(E, r25, cx, cy, False),
            "shape_absolute_r25": weighted_shape(E, r25, cx, cy, True),
            "coherence_r35": projection(E, r35),
            "template_decomposition": decomposition(E, ok, side_mean, cx, cy),
        }

    rebuilt = {
        "l2_components": component,
        "conventions": conventions,
        "cor_event_map_eligible_pixels": int(ok.sum()),
        "cor_event_map_eligible_fraction": float(ok.mean()),
        "ls7y_cor_map_max_abs_reproduction_difference": prior_diff,
    }
    target = {
        "l2_components": saved["l2_components"],
        "conventions": saved["conventions"],
        "cor_event_map_eligible_pixels": saved["cor_event_map_eligible_pixels"],
        "cor_event_map_eligible_fraction": saved["cor_event_map_eligible_fraction"],
        "ls7y_cor_map_max_abs_reproduction_difference": saved["ls7y_cor_map_max_abs_reproduction_difference"],
    }
    diffs = {}
    scalar_count = compare(rebuilt, target, "LS7Z", diffs)
    array_count = int(ok.sum()) + int(side_ok.sum()) + 40000

    result = {
        "status": "PASS",
        "scalar_numeric_comparisons": scalar_count,
        "array_or_mask_comparisons": array_count,
        "total_numeric_or_discrete_comparisons": scalar_count + array_count,
        "maximum_absolute_differences": diffs,
        "tolerance": {"relative": RTOL, "absolute": ATOL},
        "method": (
            "independent fixed-struct L2 parsing, scalar temporal normal equations, "
            "direct big-endian COR-frame parsing, scalar pixel regressions, explicit "
            "radial/shape moments, row/column projections, and SVD template fits"
        ),
        "new_archive_science_bytes": 0,
    }
    (OUT / "audit.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")

    saved["status"] = "COMPLETE_AUDITED"
    saved["audit_status"] = "PASS"
    saved["audit_comparisons"] = result["total_numeric_or_discrete_comparisons"]
    (OUT / "summary.json").write_text(json.dumps(saved, indent=2, allow_nan=False) + "\n")

    report = (OUT / "REPORT.md").read_text().replace(
        "Independent publication requires the LS7Z audit.",
        f"Independent audit: **PASS** ({result['total_numeric_or_discrete_comparisons']:,} numeric/discrete comparisons)."
    )
    (OUT / "REPORT.md").write_text(report)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
