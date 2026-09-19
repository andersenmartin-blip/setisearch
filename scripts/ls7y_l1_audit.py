#!/usr/bin/env python3
"""Independent audit of the frozen LS7Y bounded CHEOPS L1 image follow-up."""
import gzip
import json
import math
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results_ls7y_l1_followup"
PILOT = ROOT / "results_ls7x_l2_pilot"

ROW = struct.Struct(">26sddddii7d4f")
assert ROW.size == 138

CONTEXTS = [
    {"cluster": 0, "start": 52, "stop": 83, "event_start": 66, "event_stop": 69},
    {"cluster": 1, "start": 171, "stop": 202, "event_start": 185, "event_stop": 188},
]
XOFF = 715.0
YOFF = 181.0
AP_RADIUS = 25.0
EXCLUDE_RADIUS = 35.0
RTOL = 2e-8
ATOL = 2e-8


def parse_l2(raw):
    rows = list(ROW.iter_unpack(raw))
    return {
        "bjd": np.array([r[2] for r in rows], float),
        "cx": np.array([r[16] for r in rows], float),
        "cy": np.array([r[17] for r in rows], float),
    }


def mask_for(cx, cy, radius):
    yy, xx = np.mgrid[0:200, 0:200]
    return (xx - cx) ** 2 + (yy - cy) ** 2 <= radius ** 2


def finite_median(a):
    x = np.asarray(a, float)
    x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else None


def finite_mad(a):
    x = np.asarray(a, float)
    x = x[np.isfinite(x)]
    if not len(x):
        return None
    med = float(np.median(x))
    return 1.4826 * float(np.median(np.abs(x - med)))


def complete_sum(a, mask):
    x = np.asarray(a, float)[mask]
    if not len(x) or not np.isfinite(x).all():
        return None
    return float(np.sum(x))


def finite_sum_on(a, mask):
    use = mask & np.isfinite(a)
    return float(np.sum(np.asarray(a, float)[use])) if use.any() else None


def scalar_line(times, values, side, event):
    if len(values) != 31 or any(v is None for v in values):
        return {"available": False}
    allv = np.asarray(values, float)
    if not np.isfinite(allv).all():
        return {"available": False}

    t0 = float(np.mean(times[event]))
    xs = (times[side] - t0) * 86400.0
    xe = (times[event] - t0) * 86400.0
    y = allv[side]
    n = float(len(xs))
    sx = float(np.sum(xs))
    sxx = float(np.dot(xs, xs))
    sy = float(np.sum(y))
    sxy = float(np.dot(xs, y))
    det = n * sxx - sx * sx
    assert det != 0.0
    b0 = (sy * sxx - sx * sxy) / det
    b1 = (n * sxy - sx * sy) / det
    residual = y - (b0 + b1 * xs)
    pred = b0 + b1 * xe
    med = float(np.median(residual))
    return {
        "available": True,
        "event_sum": float(np.sum(allv[event])),
        "baseline_event_sum": float(np.sum(pred)),
        "event_excess": float(np.sum(allv[event] - pred)),
        "side_median": float(np.median(y)),
        "side_sigma_mad": 1.4826 * float(np.median(np.abs(residual - med))),
    }


def scalar_pixel_map(times, cube, side, event):
    used = np.r_[side, event]
    eligible = np.isfinite(cube[used]).all(axis=0)
    result = np.full((200, 200), np.nan, dtype=float)
    if not eligible.any():
        return result, eligible

    t0 = float(np.mean(times[event]))
    xs = (times[side] - t0) * 86400.0
    xe = (times[event] - t0) * 86400.0
    y = cube[side][:, eligible]

    n = float(len(xs))
    sx = float(np.sum(xs))
    sxx = float(np.dot(xs, xs))
    sy = np.sum(y, axis=0)
    sxy = xs @ y
    det = n * sxx - sx * sx
    b0 = (sy * sxx - sx * sxy) / det
    b1 = (n * sxy - sx * sy) / det
    pred_sum = len(event) * b0 + float(np.sum(xe)) * b1
    ev_sum = np.sum(cube[event][:, eligible], axis=0)
    result[eligible] = ev_sum - pred_sum
    return result, eligible


def scalar_smear_fit(delta, smear, cx, cy):
    outside = ~mask_for(cx, cy, EXCLUDE_RADIUS)
    predictor = np.repeat(smear[None, :], 200, axis=0)
    good = outside & np.isfinite(delta) & np.isfinite(predictor)
    count = int(good.sum())
    if count < 3:
        return {"available": False, "pixels": count}
    x = predictor[good]
    y = delta[good]
    n = float(len(x))
    sx = float(np.sum(x))
    sxx = float(np.dot(x, x))
    sy = float(np.sum(y))
    sxy = float(np.dot(x, y))
    det = n * sxx - sx * sx
    assert det != 0.0
    alpha = (sy * sxx - sx * sxy) / det
    beta = (n * sxy - sx * sy) / det
    residual = y - (alpha + beta * x)
    return {
        "available": True,
        "alpha": float(alpha),
        "beta": float(beta),
        "residual_rms": float(math.sqrt(float(np.mean(residual * residual)))),
        "pixels": count,
    }


def column_component(delta, common):
    out = np.full_like(delta, np.nan, dtype=float)
    for x in range(200):
        use = common[:, x]
        if use.any():
            out[use, x] = float(np.mean(delta[use, x]))
    return out


def compare_number(a, b, label, diffs):
    aa = float(a)
    bb = float(b)
    diff = abs(aa - bb)
    diffs[label] = max(diffs.get(label, 0.0), diff)
    assert math.isclose(aa, bb, rel_tol=RTOL, abs_tol=ATOL), (label, aa, bb)
    return 1


def compare_value(expected, saved, prefix, diffs):
    comparisons = 0
    if expected is None:
        assert saved is None, (prefix, expected, saved)
    elif isinstance(expected, dict):
        assert isinstance(saved, dict), prefix
        for key, value in expected.items():
            assert key in saved, (prefix, key)
            comparisons += compare_value(value, saved[key], f"{prefix}.{key}", diffs)
    elif isinstance(expected, list):
        assert isinstance(saved, list) and len(expected) == len(saved), prefix
        for i, value in enumerate(expected):
            comparisons += compare_value(value, saved[i], f"{prefix}[{i}]", diffs)
    elif isinstance(expected, bool):
        assert saved is expected, (prefix, expected, saved)
    elif isinstance(expected, (int, float)):
        comparisons += compare_number(expected, saved, prefix, diffs)
    else:
        assert expected == saved, (prefix, expected, saved)
    return comparisons


def compare_map(expected, saved, label, diffs):
    expected = np.asarray(expected)
    saved = np.asarray(saved)
    assert expected.shape == saved.shape, label
    if expected.dtype == bool:
        assert np.array_equal(expected, saved.astype(bool)), label
        return expected.size
    assert np.array_equal(np.isnan(expected), np.isnan(saved)), f"{label}.nanmask"
    finite = np.isfinite(expected)
    if finite.any():
        delta = np.abs(expected[finite] - saved[finite])
        md = float(np.max(delta))
        diffs[label] = md
        assert np.allclose(expected[finite], saved[finite], rtol=RTOL, atol=ATOL), (label, md)
        return int(finite.sum())
    return 0


def main():
    q = json.loads((OUT / "acquisition.json").read_text())
    assert q["subarray_science_bytes"] == 39680000
    assert q["smearing_data_bytes"] == 99200
    assert q["smearing_header_bytes"] == 5760
    assert q["contexts"] == CONTEXTS
    assert len(q["receipts"]) == 7
    for rec in q["receipts"]:
        p = OUT / rec["file"]
        assert p.is_file() and p.stat().st_size == rec["count"], rec["file"]

    sh = (OUT / "SCI_COR_SmearingRow_header.bin").read_bytes()
    assert len(sh) == 5760
    cards = [sh[i:i+80].decode("ascii") for i in range(0, len(sh), 80)]
    assert any(c.startswith("EXTNAME ") and "SCI_COR_SmearingRow" in c for c in cards)
    assert any(c.startswith("BITPIX  ") and "-64" in c for c in cards)
    assert any(c.startswith("NAXIS1  ") and "200" in c for c in cards)
    assert any(c.startswith("NAXIS2  ") and "432" in c for c in cards)

    l2 = parse_l2((PILOT / "lightcurve_table.bin").read_bytes())
    candidates = json.loads((PILOT / "candidates.json").read_text())["clusters"]
    assert [(x["cluster_id"], x["start"], x["duration"]) for x in candidates] == [
        (0, 66, 3), (1, 185, 3)
    ]

    summary = json.loads((OUT / "summary.json").read_text())
    assert summary["stage"] == "LS7Y_CHEOPS_L1_IMAGE_FOLLOWUP"
    assert summary["status"] == "COMPLETE_UNAUDITED"
    assert summary["finite_pixel_amendment"] == "LS7Y_FINITE_PIXEL_AMENDMENT.md"
    assert summary["other_l2_apertures_opened"] is False
    assert summary["raw_imagettes_opened"] is False
    assert summary["other_subarray_rows_opened"] is False
    saved_clusters = {x["cluster"]: x for x in summary["clusters"]}

    saved_frames = [
        json.loads(x) for x in
        gzip.decompress((OUT / "frame_metrics.jsonl.gz").read_bytes()).decode().splitlines()
    ]
    assert len(saved_frames) == 62
    saved_frame = {(x["cluster"], x["row"]): x for x in saved_frames}

    diffs = {}
    comparisons = 0
    map_comparisons = 0
    classifications = []

    for ctx in CONTEXTS:
        cid = ctx["cluster"]
        first = ctx["start"]
        n = ctx["stop"] - first
        event_global = np.arange(ctx["event_start"], ctx["event_stop"])
        side_global = np.r_[
            np.arange(ctx["event_start"] - 14, ctx["event_start"] - 2),
            np.arange(ctx["event_stop"] + 2, ctx["event_stop"] + 14),
        ]
        side = side_global - first
        event = event_global - first
        times = l2["bjd"][first:ctx["stop"]]

        cal = np.frombuffer(
            (OUT / f"SCI_CAL_SubArray_cluster{cid}_rows_{first}_{ctx['stop']-1}.bin").read_bytes(),
            dtype=">f8"
        ).reshape(n, 200, 200).astype(float)
        cor = np.frombuffer(
            (OUT / f"SCI_COR_SubArray_cluster{cid}_rows_{first}_{ctx['stop']-1}.bin").read_bytes(),
            dtype=">f8"
        ).reshape(n, 200, 200).astype(float)
        smear = np.frombuffer(
            (OUT / f"SCI_COR_SmearingRow_cluster{cid}_rows_{first}_{ctx['stop']-1}.bin").read_bytes(),
            dtype=">f8"
        ).reshape(n, 200).astype(float)
        delta = cor - cal

        sums = {
            "C0": {"CAL": [], "COR": [], "DELTA": [], "SMEAR": []},
            "C1": {"CAL": [], "COR": [], "DELTA": [], "SMEAR": []},
        }
        fits = []
        finite_counts = {
            "CAL": int(np.isfinite(cal).sum()),
            "COR": int(np.isfinite(cor).sum()),
            "DELTA": int(np.isfinite(delta).sum()),
            "SMEAR": int(np.isfinite(smear).sum()),
        }

        for li, gi in enumerate(range(first, ctx["stop"])):
            cx0 = l2["cx"][gi] - XOFF
            cy0 = l2["cy"][gi] - YOFF
            fit = scalar_smear_fit(delta[li], smear[li], cx0, cy0)
            fit["row"] = gi
            fits.append(fit)
            rebuilt = {
                "cluster": cid,
                "row": gi,
                "finite_pixels": {
                    "CAL": int(np.isfinite(cal[li]).sum()),
                    "COR": int(np.isfinite(cor[li]).sum()),
                    "DELTA": int(np.isfinite(delta[li]).sum()),
                    "SMEAR": int(np.isfinite(smear[li]).sum()),
                },
                "delta_median": finite_median(delta[li]),
                "delta_sigma_mad": finite_mad(delta[li]),
                "smear_fit": fit,
            }
            for name, shift in (("C0", 0.0), ("C1", -1.0)):
                m = mask_for(cx0 + shift, cy0 + shift, AP_RADIUS)
                weights = np.sum(m, axis=0)
                finite_smear = np.isfinite(smear[li][weights > 0]).all()
                vals = {
                    "CAL": complete_sum(cal[li], m),
                    "COR": complete_sum(cor[li], m),
                    "DELTA": complete_sum(delta[li], m),
                    "SMEAR": float(np.dot(smear[li], weights)) if finite_smear else None,
                }
                for key, value in vals.items():
                    sums[name][key].append(value)
                rebuilt[name] = {
                    **vals,
                    "aperture_pixels": int(m.sum()),
                    "complete_finite": {key: value is not None for key, value in vals.items()},
                }
            comparisons += compare_value(
                rebuilt, saved_frame[(cid, gi)], f"frame[{cid},{gi}]", diffs
            )

        cal_map, cal_ok = scalar_pixel_map(times, cal, side, event)
        cor_map, cor_ok = scalar_pixel_map(times, cor, side, event)
        common = cal_ok & cor_ok
        delta_map = np.full((200, 200), np.nan)
        delta_map[common] = cor_map[common] - cal_map[common]
        col = column_component(delta_map, common)

        with np.load(OUT / f"cluster_{cid}_event_excess_maps.npz") as saved:
            for name, rebuilt in (
                ("cal", cal_map), ("cor", cor_map), ("delta", delta_map),
                ("delta_column_component", col),
                ("cal_eligible", cal_ok), ("cor_eligible", cor_ok),
                ("common_eligible", common),
            ):
                map_comparisons += compare_map(
                    rebuilt, saved[name], f"maps.cluster{cid}.{name}", diffs
                )

        mean_cx0 = float(np.mean(l2["cx"][event_global])) - XOFF
        mean_cy0 = float(np.mean(l2["cy"][event_global])) - YOFF
        conventions = {}
        correction = []
        localized = []
        completeness = []

        for name, shift in (("C0", 0.0), ("C1", -1.0)):
            m25 = mask_for(mean_cx0 + shift, mean_cy0 + shift, AP_RADIUS)
            m35 = mask_for(mean_cx0 + shift, mean_cy0 + shift, EXCLUDE_RADIUS)
            temporal = {key: scalar_line(times, values, side, event)
                        for key, values in sums[name].items()}
            complete = bool(common[m25].all()) and all(
                temporal[key].get("available", False)
                for key in ("CAL", "COR", "DELTA", "SMEAR")
            )
            completeness.append(complete)

            denom = float(np.sum(np.abs(cor_map[common]))) if common.any() else 0.0
            m25c = m25 & common
            concentration = (
                float(np.sum(np.abs(cor_map[m25c])) / denom) if denom > 0 else None
            )
            col_ap = finite_sum_on(col, m25c)
            conventions[name] = {
                "center_event_mean": [mean_cx0 + shift, mean_cy0 + shift],
                "aperture_pixels": int(m25.sum()),
                "central_common_eligible_pixels": int(common[m25].sum()),
                "central_complete": complete,
                "temporal": temporal,
                "maps": {
                    "cal_r25_sum": finite_sum_on(cal_map, m25c),
                    "cor_r25_sum": finite_sum_on(cor_map, m25c),
                    "delta_r25_sum": finite_sum_on(delta_map, m25c),
                    "cal_r35_sum": finite_sum_on(cal_map, m35 & common),
                    "cor_r35_sum": finite_sum_on(cor_map, m35 & common),
                    "delta_r35_sum": finite_sum_on(delta_map, m35 & common),
                    "cal_full_sum": finite_sum_on(cal_map, common),
                    "cor_full_sum": finite_sum_on(cor_map, common),
                    "delta_full_sum": finite_sum_on(delta_map, common),
                    "cor_l1_concentration_r25": concentration,
                    "delta_column_component_r25_sum": col_ap,
                },
            }
            if complete:
                cor_ex = temporal["COR"]["event_excess"]
                delta_ex = temporal["DELTA"]["event_excess"]
                correction.append(
                    abs(delta_ex) >= 0.5 * abs(cor_ex)
                    or abs(col_ap) >= 0.5 * abs(cor_ex)
                )
                localized.append(
                    cor_ex > 0 and concentration is not None and concentration >= 0.5
                )
            else:
                correction.append(False)
                localized.append(False)

        if not all(completeness):
            classification = "AMBIGUOUS_IMAGE_FOLLOWUP"
        elif all(correction):
            classification = "CORRECTION_LINKED"
        elif not any(correction) and all(localized):
            classification = "IMAGE_LOCALIZED_NOT_CORRECTION_DOMINATED"
        else:
            classification = "AMBIGUOUS_IMAGE_FOLLOWUP"
        classifications.append(classification)

        energy = float(np.sum(delta_map[common] ** 2)) if common.any() else 0.0
        coherence = float(np.sum(col[common] ** 2) / energy) if energy > 0 else None
        event_betas = [
            fits[x].get("beta") if fits[x].get("available") else None for x in event
        ]
        side_betas = [fits[x]["beta"] for x in side if fits[x].get("available")]
        rebuilt_cluster = {
            "cluster": cid,
            "event_rows": [int(x) for x in event_global],
            "context_rows": [first, ctx["stop"] - 1],
            "ls7x_score": float(candidates[cid]["score"]),
            "context_finite_counts": finite_counts,
            "event_map_availability": {
                "cal_eligible_pixels": int(cal_ok.sum()),
                "cor_eligible_pixels": int(cor_ok.sum()),
                "common_eligible_pixels": int(common.sum()),
                "common_eligible_fraction": float(common.mean()),
            },
            "conventions": conventions,
            "delta_event_map_column_coherence_fraction": coherence,
            "smear_fit_event": event_betas,
            "smear_fit_side_median_beta": (
                float(np.median(side_betas)) if side_betas else None
            ),
            "classification": classification,
        }
        comparisons += compare_value(
            rebuilt_cluster, saved_clusters[cid], f"cluster[{cid}]", diffs
        )

    result = {
        "status": "PASS",
        "clusters": 2,
        "saved_frame_metric_rows": len(saved_frames),
        "summary_numeric_comparisons": comparisons,
        "event_map_numeric_comparisons": map_comparisons,
        "total_numeric_comparisons": comparisons + map_comparisons,
        "maximum_absolute_differences": diffs,
        "classifications": classifications,
        "method": (
            "independent big-endian struct parsing, scalar normal equations, "
            "explicit finite-pixel availability masks, direct radius masks, "
            "and independently rebuilt pixel event maps"
        ),
        "tolerance": {"relative": RTOL, "absolute": ATOL},
    }
    (OUT / "audit.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")

    summary["status"] = "COMPLETE_AUDITED"
    summary["audit_status"] = "PASS"
    summary["audit_numeric_comparisons"] = result["total_numeric_comparisons"]
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")

    report = (OUT / "REPORT.md").read_text()
    report = report.replace(
        "Independent publication requires the LS7Y audit.",
        f"Independent audit: **PASS** ({result['total_numeric_comparisons']:,} numerical comparisons)."
    )
    (OUT / "REPORT.md").write_text(report)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
