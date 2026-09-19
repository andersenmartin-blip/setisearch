#!/usr/bin/env python3
"""Evaluate the frozen LS7Z cluster-1 morphology study from published bytes only."""
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

import numpy as np
from astropy.io import fits

ROOT = Path(__file__).resolve().parents[1]
L2META = ROOT / "results_ls7x_l2_metadata"
L2 = ROOT / "results_ls7x_l2_pilot"
L1 = ROOT / "results_ls7y_l1_followup"
OUT = ROOT / "results_ls7z_morphology"

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
L2_COLUMNS = [
    "FLUX", "FLUXERR", "DARK", "BACKGROUND", "CONTA_LC", "CONTA_LC_ERR",
    "SMEARING_LC", "SMEARING_LC_ERR", "ROLL_ANGLE", "LOCATION_X", "LOCATION_Y",
    "CENTROID_X", "CENTROID_Y",
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def table_dtype(header):
    fields = []
    for i in range(1, header["TFIELDS"] + 1):
        count, code = re.fullmatch(r"(\d*)([ADEJI])", header[f"TFORM{i}"]).groups()
        n = int(count or "1")
        name = header[f"TTYPE{i}"]
        if code == "A":
            fields.append((name, f"S{n}"))
        else:
            typ = {"D": ">f8", "E": ">f4", "J": ">i4", "I": ">i2"}[code]
            fields.append((name, typ, (n,)) if n != 1 else (name, typ))
    dtype = np.dtype(fields)
    assert dtype.itemsize == header["NAXIS1"]
    return dtype


def mask(cx, cy, radius):
    yy, xx = np.mgrid[0:200, 0:200]
    return (xx - cx) ** 2 + (yy - cy) ** 2 <= radius ** 2


def temporal_diag(times, values):
    values = np.asarray(values, float)
    side = SIDE_G
    event = EVENT_G
    assert np.isfinite(times[np.r_[side, event]]).all()
    if not np.isfinite(values[np.r_[side, event]]).all():
        return {"available": False}
    t0 = float(np.mean(times[event]))
    xs = (times[side] - t0) * 86400.0
    xe = (times[event] - t0) * 86400.0
    X = np.column_stack([np.ones(len(xs)), xs])
    XE = np.column_stack([np.ones(len(xe)), xe])
    beta = np.linalg.lstsq(X, values[side], rcond=None)[0]
    residual = values[side] - X @ beta
    pred = XE @ beta
    medr = float(np.median(residual))
    mad = float(1.4826 * np.median(np.abs(residual - medr)))
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
        "side_median": float(np.median(values[side])),
        "side_residual_sigma_mad": mad,
        "normalization_zero_floor": zero_floor,
        "normalization_mad_treated_as_zero": mad_is_zero,
        "normalized_event_excess": (
            float(excess / (mad * math.sqrt(3.0)))
            if (not mad_is_zero and mad > 0 and np.isfinite(mad)) else None
        ),
        "baseline_coefficients": [float(beta[0]), float(beta[1])],
    }


def event_map(times, cube):
    used = np.r_[SIDE, EVENT]
    eligible = np.isfinite(cube[used]).all(axis=0)
    result = np.full((200, 200), np.nan, dtype=float)
    if not eligible.any():
        return result, eligible
    t0 = float(np.mean(times[EVENT]))
    xs = (times[SIDE] - t0) * 86400.0
    xe = (times[EVENT] - t0) * 86400.0
    X = np.column_stack([np.ones(len(xs)), xs])
    XE = np.column_stack([np.ones(len(xe)), xe])
    y = cube[SIDE][:, eligible]
    beta = np.linalg.solve(X.T @ X, X.T @ y)
    pred = np.sum(XE @ beta, axis=0)
    obs = np.sum(cube[EVENT][:, eligible], axis=0)
    result[eligible] = obs - pred
    return result, eligible


def weighted_shape(E, use, target_x, target_y, mode):
    values = np.asarray(E, float)
    if mode == "positive":
        weights = np.where(use, np.maximum(values, 0.0), 0.0)
    elif mode == "absolute":
        weights = np.where(use, np.abs(values), 0.0)
    else:
        raise ValueError(mode)
    total = float(np.sum(weights))
    if not total > 0:
        return {"available": False, "weight_sum": total}
    yy, xx = np.mgrid[0:200, 0:200]
    mx = float(np.sum(weights * xx) / total)
    my = float(np.sum(weights * yy) / total)
    dx = xx - mx
    dy = yy - my
    cxx = float(np.sum(weights * dx * dx) / total)
    cyy = float(np.sum(weights * dy * dy) / total)
    cxy = float(np.sum(weights * dx * dy) / total)
    eig = np.linalg.eigvalsh(np.array([[cxx, cxy], [cxy, cyy]], float))
    minor = float(math.sqrt(max(float(eig[0]), 0.0)))
    major = float(math.sqrt(max(float(eig[1]), 0.0)))
    return {
        "available": True,
        "weight_sum": total,
        "centroid_xy": [mx, my],
        "offset_from_target_pixels": float(math.hypot(mx - target_x, my - target_y)),
        "second_moment": [[cxx, cxy], [cxy, cyy]],
        "major_rms_pixels": major,
        "minor_rms_pixels": minor,
        "axis_ratio_major_over_minor": (float(major / minor) if minor > 0 else None),
    }


def projection_fractions(E, use):
    e = np.where(use, E, 0.0)
    energy = float(np.sum(e * e))
    if energy <= 0:
        return {
            "available": False,
            "energy": energy,
            "row_constant_energy_fraction": None,
            "column_constant_energy_fraction": None,
        }
    rowp = np.zeros_like(e)
    colp = np.zeros_like(e)
    for y in range(200):
        m = use[y]
        if m.any():
            rowp[y, m] = float(np.mean(E[y, m]))
    for x in range(200):
        m = use[:, x]
        if m.any():
            colp[m, x] = float(np.mean(E[m, x]))
    return {
        "available": True,
        "energy": energy,
        "row_constant_energy_fraction": float(np.sum(rowp * rowp) / energy),
        "column_constant_energy_fraction": float(np.sum(colp * colp) / energy),
    }


def cosine(a, b):
    den = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / den) if den > 0 else None


def fit_model(E, columns, names):
    X = np.column_stack(columns)
    y = np.asarray(E, float)
    beta, _, rank, s = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ beta
    resid = y - pred
    sse = float(np.sum(resid * resid))
    sst0 = float(np.sum(y * y))
    return {
        "names": names,
        "coefficients": [float(x) for x in beta],
        "rank": int(rank),
        "condition_number": (
            float(s[0] / s[-1]) if len(s) and s[-1] > 0 else None
        ),
        "pixels": int(len(y)),
        "residual_rms": float(math.sqrt(sse / len(y))),
        "squared_l2_explained_fraction": (float(1.0 - sse / sst0) if sst0 > 0 else None),
    }


def radial_metrics(E, eligible, cx, cy):
    pos_full = float(np.sum(np.maximum(E[eligible], 0.0)))
    l1_full = float(np.sum(np.abs(E[eligible])))
    out = {}
    for r in RADII:
        geom = mask(cx, cy, r)
        use = geom & eligible
        vals = E[use]
        pos = float(np.sum(np.maximum(vals, 0.0))) if len(vals) else 0.0
        neg = float(np.sum(np.maximum(-vals, 0.0))) if len(vals) else 0.0
        l1 = pos + neg
        out[str(int(r))] = {
            "signed_sum": float(np.sum(vals)) if len(vals) else 0.0,
            "positive_sum": pos,
            "negative_magnitude": neg,
            "absolute_l1_sum": l1,
            "positive_fraction_of_full": (float(pos / pos_full) if pos_full > 0 else None),
            "absolute_l1_fraction_of_full": (float(l1 / l1_full) if l1_full > 0 else None),
            "eligible_pixels": int(use.sum()),
            "geometric_pixels": int(geom.sum()),
        }
    return {
        "full_common_eligible_positive_sum": pos_full,
        "full_common_eligible_absolute_l1_sum": l1_full,
        "radii": out,
    }


def annular_metrics(E, eligible, cx, cy):
    yy, xx = np.mgrid[0:200, 0:200]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    out = {}
    for lo, hi in ANNULI:
        geom = (d > lo) & (d <= hi) if lo > 0 else (d <= hi)
        use = geom & eligible
        vals = E[use]
        key = f"{int(lo)}_{int(hi)}"
        out[key] = {
            "signed_sum": float(np.sum(vals)) if len(vals) else 0.0,
            "absolute_l1_sum": float(np.sum(np.abs(vals))) if len(vals) else 0.0,
            "positive_sum": float(np.sum(np.maximum(vals, 0.0))) if len(vals) else 0.0,
            "eligible_pixels": int(use.sum()),
            "geometric_pixels": int(geom.sum()),
        }
    return out


def template_decomposition(E, eligible, side_mean, cx, cy):
    yy, xx = np.mgrid[0:200, 0:200]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    ann = (dist > 30.0) & (dist <= 40.0) & eligible & np.isfinite(side_mean)
    if not ann.any():
        return {"available": False, "reason": "empty_background_annulus"}
    background = float(np.median(side_mean[ann]))
    P = np.full((200, 200), np.nan)
    P[eligible] = side_mean[eligible] - background
    Dx = np.full_like(P, np.nan)
    Dy = np.full_like(P, np.nan)
    valid_x = np.isfinite(P[:, :-2]) & np.isfinite(P[:, 2:])
    valid_y = np.isfinite(P[:-2, :]) & np.isfinite(P[2:, :])
    tmpx = (P[:, 2:] - P[:, :-2]) / 2.0
    tmpy = (P[2:, :] - P[:-2, :]) / 2.0
    Dx[:, 1:-1][valid_x] = tmpx[valid_x]
    Dy[1:-1, :][valid_y] = tmpy[valid_y]

    fit_geom = dist <= 25.0
    fit = fit_geom & eligible & np.isfinite(E) & np.isfinite(P) & np.isfinite(Dx) & np.isfinite(Dy)
    n = int(fit.sum())
    if n < 10:
        return {"available": False, "reason": "insufficient_common_fit_pixels", "pixels": n}

    e = E[fit]
    p = P[fit]
    dx = Dx[fit]
    dy = Dy[fit]
    ones = np.ones(n)
    return {
        "available": True,
        "background_annulus_median": background,
        "fit_pixels": n,
        "fit_geometric_pixels": int(fit_geom.sum()),
        "fit_pixel_fraction": float(n / fit_geom.sum()),
        "cosine_similarity": {
            "P": cosine(e, p),
            "Dx": cosine(e, dx),
            "Dy": cosine(e, dy),
        },
        "models": {
            "brightness": fit_model(e, [p, ones], ["P", "constant"]),
            "shift": fit_model(e, [dx, dy, ones], ["Dx", "Dy", "constant"]),
            "combined": fit_model(e, [p, dx, dy, ones], ["P", "Dx", "Dy", "constant"]),
        },
    }


def main():
    assert not OUT.exists(), "refuse completed LS7Z output overwrite"

    # Parent state/boundary checks.
    ysummary = json.loads((L1 / "summary.json").read_text())
    assert ysummary["status"] == "COMPLETE_AUDITED"
    cluster1 = next(x for x in ysummary["clusters"] if x["cluster"] == 1)
    assert cluster1["classification"] == "IMAGE_LOCALIZED_NOT_CORRECTION_DOMINATED"
    assert cluster1["event_rows"] == [185, 186, 187]
    assert cluster1["context_rows"] == [171, 201]

    h = fits.Header.fromstring((L2META / "lightcurve_header.bin").read_bytes().decode("ascii"), sep="")
    raw = (L2 / "lightcurve_table.bin").read_bytes()
    table = np.frombuffer(raw, dtype=table_dtype(h), count=h["NAXIS2"])
    assert len(table) == 432
    bjd = table["BJD_TIME"].astype(float)

    component = {name: temporal_diag(bjd, table[name].astype(float)) for name in L2_COLUMNS}

    n = STOP - FIRST
    cor_raw = (L1 / "SCI_COR_SubArray_cluster1_rows_171_201.bin").read_bytes()
    assert len(cor_raw) == n * 200 * 200 * 8
    cor = np.frombuffer(cor_raw, dtype=">f8").reshape(n, 200, 200).astype(float)
    times = bjd[FIRST:STOP]
    E, eligible = event_map(times, cor)

    # Reproduce the already-published LS7Y COR map before new morphology.
    with np.load(L1 / "cluster_1_event_excess_maps.npz") as prior:
        prior_cor = np.asarray(prior["cor"], float)
        prior_ok = np.asarray(prior["cor_eligible"], bool)
    assert np.array_equal(eligible, prior_ok)
    finite = eligible & np.isfinite(prior_cor)
    max_prior_diff = float(np.max(np.abs(E[finite] - prior_cor[finite]))) if finite.any() else 0.0
    assert np.allclose(E[finite], prior_cor[finite], rtol=1e-10, atol=2e-9)

    side_mean = np.full((200, 200), np.nan)
    side_ok = np.isfinite(cor[SIDE]).all(axis=0)
    side_mean[side_ok] = np.mean(cor[SIDE][:, side_ok], axis=0)

    # New LS7Z calculations deliberately convert stored float32 centroids to float64 first.
    mean_x0 = float(np.mean(table["CENTROID_X"][EVENT_G].astype(float))) - XOFF
    mean_y0 = float(np.mean(table["CENTROID_Y"][EVENT_G].astype(float))) - YOFF

    conventions = {}
    for label, shift in (("C0", 0.0), ("C1", -1.0)):
        cx = mean_x0 + shift
        cy = mean_y0 + shift
        r25 = mask(cx, cy, 25.0) & eligible
        r35 = mask(cx, cy, 35.0) & eligible
        conventions[label] = {
            "target_center_xy": [cx, cy],
            "radial": radial_metrics(E, eligible, cx, cy),
            "annuli": annular_metrics(E, eligible, cx, cy),
            "shape_positive_r25": weighted_shape(E, r25, cx, cy, "positive"),
            "shape_absolute_r25": weighted_shape(E, r25, cx, cy, "absolute"),
            "coherence_r35": projection_fractions(E, r35),
            "template_decomposition": template_decomposition(E, eligible, side_mean, cx, cy),
        }

    result = {
        "stage": "LS7Z_CLUSTER1_MORPHOLOGY",
        "status": "COMPLETE_UNAUDITED",
        "parent_cluster": 1,
        "parent_ls7x_score": float(cluster1["ls7x_score"]),
        "parent_ls7y_classification": cluster1["classification"],
        "event_rows": [185, 186, 187],
        "context_rows": [171, 201],
        "sideband_rows": [int(x) for x in SIDE_G],
        "guard_rows": [183, 184, 188, 189],
        "new_archive_science_bytes": 0,
        "other_apertures_opened": False,
        "raw_imagettes_opened": False,
        "other_visits_opened": False,
        "cor_event_map_eligible_pixels": int(eligible.sum()),
        "cor_event_map_eligible_fraction": float(eligible.mean()),
        "ls7y_cor_map_max_abs_reproduction_difference": max_prior_diff,
        "l2_components": component,
        "conventions": conventions,
        "interpretation": (
            "descriptive morphology/component study only; no astrophysical, artificial, "
            "instrumental-origin, detection, or false-alarm classification"
        ),
    }

    OUT.mkdir()
    save(OUT / "summary.json", result)
    np.savez_compressed(
        OUT / "cluster1_morphology_arrays.npz",
        cor_event_excess=E,
        eligible=eligible,
        sideband_mean_cor=side_mean,
    )

    lines = [
        "# LS7Z cluster-1 morphology and L2-component study",
        "",
        "Frozen before evaluation and computed entirely from already published LS7X/LS7Y bytes.",
        "No new archive science bytes were opened.",
        "",
        f"- Parent LS7X score: **{cluster1['ls7x_score']:.6f}**",
        f"- Parent LS7Y label: **{cluster1['classification']}**",
        f"- Common COR event-map eligible pixels: **{int(eligible.sum())}/40000**",
        "",
        "## Fixed morphology diagnostics",
        "",
        "| Convention | +L1 fraction r<=5 | +L1 fraction r<=12 | +L1 fraction r<=25 | positive centroid offset (px) | row coherence r<=35 | column coherence r<=35 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label in ("C0", "C1"):
        x = conventions[label]
        rad = x["radial"]["radii"]
        shp = x["shape_positive_r25"]
        coh = x["coherence_r35"]
        lines.append(
            f"| {label} | {rad['5']['positive_fraction_of_full']:.6g} | "
            f"{rad['12']['positive_fraction_of_full']:.6g} | "
            f"{rad['25']['positive_fraction_of_full']:.6g} | "
            f"{shp['offset_from_target_pixels']:.6g} | "
            f"{coh['row_constant_energy_fraction']:.6g} | "
            f"{coh['column_constant_energy_fraction']:.6g} |"
        )
    lines += [
        "",
        "## Fixed template decomposition",
        "",
        "| Convention | brightness explained | shift explained | combined explained | cos(E,P) | cos(E,Dx) | cos(E,Dy) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label in ("C0", "C1"):
        t = conventions[label]["template_decomposition"]
        lines.append(
            f"| {label} | {t['models']['brightness']['squared_l2_explained_fraction']:.6g} | "
            f"{t['models']['shift']['squared_l2_explained_fraction']:.6g} | "
            f"{t['models']['combined']['squared_l2_explained_fraction']:.6g} | "
            f"{t['cosine_similarity']['P']:.6g} | {t['cosine_similarity']['Dx']:.6g} | "
            f"{t['cosine_similarity']['Dy']:.6g} |"
        )
    lines += [
        "",
        "The template fits are descriptive and have no post-hoc physical classification threshold.",
        "Full L2 component diagnostics and numerical values are in summary.json.",
        "Independent publication requires the LS7Z audit.",
        "",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines))

    files = sorted(p for p in OUT.iterdir() if p.is_file() and p.name != "SHA256SUMS")
    (OUT / "SHA256SUMS").write_text(
        "".join(f"{sha(p.read_bytes())}  {p.name}\n" for p in files)
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
