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


def mad_scale(a):
    a = np.asarray(a, float)
    med = float(np.median(a))
    return 1.4826 * float(np.median(np.abs(a - med)))


def linear_prediction(times, values, side, event):
    t0 = float(np.mean(times[event]))
    xs = (times[side] - t0) * 86400.0
    xe = (times[event] - t0) * 86400.0
    y = np.asarray(values, float)[side]

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
    ev = np.asarray(values, float)[event]
    return {
        "event_sum": float(np.sum(ev)),
        "baseline_event_sum": float(np.sum(pred)),
        "event_excess": float(np.sum(ev - pred)),
        "side_median": float(np.median(y)),
        "side_sigma_mad": mad_scale(residual),
    }


def pixel_excess(times, cube, side, event):
    t0 = float(np.mean(times[event]))
    xs = (times[side] - t0) * 86400.0
    xe = (times[event] - t0) * 86400.0
    y = cube[side].reshape(len(side), -1)

    n = float(len(xs))
    sx = float(np.sum(xs))
    sxx = float(np.dot(xs, xs))
    sy = np.sum(y, axis=0)
    sxy = xs @ y
    det = n * sxx - sx * sx
    b0 = (sy * sxx - sx * sxy) / det
    b1 = (n * sxy - sx * sy) / det

    pred_sum = len(event) * b0 + float(np.sum(xe)) * b1
    event_sum = np.sum(cube[event].reshape(len(event), -1), axis=0)
    return (event_sum - pred_sum).reshape(200, 200)


def delta_smear_fit(delta, smear, cx, cy):
    outside = ~mask_for(cx, cy, EXCLUDE_RADIUS)
    yy = delta[outside]
    xx = np.repeat(smear[None, :], 200, axis=0)[outside]
    good = np.isfinite(xx) & np.isfinite(yy)
    x = xx[good]
    y = yy[good]

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
        "alpha": float(alpha),
        "beta": float(beta),
        "residual_rms": float(math.sqrt(float(np.mean(residual * residual)))),
        "pixels": int(good.sum()),
    }


def close(a, b, label, diffs):
    aa = float(a)
    bb = float(b)
    diff = abs(aa - bb)
    diffs[label] = max(diffs.get(label, 0.0), diff)
    assert math.isclose(aa, bb, rel_tol=RTOL, abs_tol=ATOL), (label, aa, bb)
    return 1


def compare_dict_numeric(expected, saved, prefix, diffs):
    comparisons = 0
    for key, value in expected.items():
        assert key in saved, (prefix, key)
        got = saved[key]
        label = f"{prefix}.{key}"
        if isinstance(value, dict):
            comparisons += compare_dict_numeric(value, got, label, diffs)
        elif isinstance(value, list):
            assert len(value) == len(got), label
            for i, x in enumerate(value):
                if isinstance(x, (int, float)) and not isinstance(x, bool):
                    comparisons += close(x, got[i], f"{label}[{i}]", diffs)
                else:
                    assert x == got[i], (label, i, x, got[i])
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            comparisons += close(value, got, label, diffs)
        else:
            assert value == got, (label, value, got)
    return comparisons


def main():
    acquisition = json.loads((OUT / "acquisition.json").read_text())
    assert acquisition["subarray_science_bytes"] == 39680000
    assert acquisition["smearing_data_bytes"] == 99200
    assert acquisition["smearing_header_bytes"] == 5760
    assert acquisition["contexts"] == CONTEXTS
    assert len(acquisition["receipts"]) == 7

    # Independently validate the selected range payload sizes from the saved bytes.
    for rec in acquisition["receipts"]:
        p = OUT / rec["file"]
        assert p.is_file() and p.stat().st_size == rec["count"], rec["file"]

    # Smearing header: minimal independent FITS-card check, no astropy.
    sh = (OUT / "SCI_COR_SmearingRow_header.bin").read_bytes()
    assert len(sh) == 5760 and len(sh) % 2880 == 0
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

    saved_summary = json.loads((OUT / "summary.json").read_text())
    assert saved_summary["stage"] == "LS7Y_CHEOPS_L1_IMAGE_FOLLOWUP"
    assert saved_summary["status"] == "COMPLETE_UNAUDITED"
    assert saved_summary["other_l2_apertures_opened"] is False
    assert saved_summary["raw_imagettes_opened"] is False
    assert saved_summary["other_subarray_rows_opened"] is False
    saved_clusters = {x["cluster"]: x for x in saved_summary["clusters"]}

    saved_frames = [
        json.loads(line) for line in
        gzip.decompress((OUT / "frame_metrics.jsonl.gz").read_bytes()).decode().splitlines()
    ]
    assert len(saved_frames) == 62
    saved_frame_lookup = {(x["cluster"], x["row"]): x for x in saved_frames}

    diffs = {}
    comparisons = 0
    rebuilt_labels = []
    map_comparisons = 0

    for ctx in CONTEXTS:
        cid = ctx["cluster"]
        n = ctx["stop"] - ctx["start"]
        first = ctx["start"]
        event_global = np.arange(ctx["event_start"], ctx["event_stop"])
        left = np.arange(ctx["event_start"] - 14, ctx["event_start"] - 2)
        right = np.arange(ctx["event_stop"] + 2, ctx["event_stop"] + 14)
        side_global = np.r_[left, right]
        side = side_global - first
        event = event_global - first

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
        assert np.isfinite(cal).all() and np.isfinite(cor).all() and np.isfinite(smear).all()

        delta = cor - cal
        times = l2["bjd"][first:ctx["stop"]]
        sums = {"C0": {"CAL": [], "COR": [], "DELTA": [], "SMEAR": []},
                "C1": {"CAL": [], "COR": [], "DELTA": [], "SMEAR": []}}
        fits = []

        for li, gi in enumerate(range(first, ctx["stop"])):
            cx0 = l2["cx"][gi] - XOFF
            cy0 = l2["cy"][gi] - YOFF
            fit = delta_smear_fit(delta[li], smear[li], cx0, cy0)
            fits.append(fit)
            rebuilt = {
                "cluster": cid,
                "row": gi,
                "delta_median": float(np.median(delta[li])),
                "delta_sigma_mad": mad_scale(delta[li]),
                "smear_fit": {**fit, "row": gi},
            }
            for name, shift in (("C0", 0.0), ("C1", -1.0)):
                m = mask_for(cx0 + shift, cy0 + shift, AP_RADIUS)
                w = np.sum(m, axis=0)
                vals = {
                    "CAL": float(np.sum(cal[li][m])),
                    "COR": float(np.sum(cor[li][m])),
                    "DELTA": float(np.sum(delta[li][m])),
                    "SMEAR": float(np.dot(smear[li], w)),
                }
                rebuilt[name] = vals
                for key, value in vals.items():
                    sums[name][key].append(value)
            comparisons += compare_dict_numeric(
                rebuilt, saved_frame_lookup[(cid, gi)], f"frame[{cid},{gi}]", diffs
            )

        cal_map = pixel_excess(times, cal, side, event)
        cor_map = pixel_excess(times, cor, side, event)
        delta_map = cor_map - cal_map
        col = np.repeat(np.mean(delta_map, axis=0)[None, :], 200, axis=0)

        npz = np.load(OUT / f"cluster_{cid}_event_excess_maps.npz")
        for name, rebuilt in (("cal", cal_map), ("cor", cor_map), ("delta", delta_map),
                              ("delta_column_component", col)):
            saved = np.asarray(npz[name], float)
            assert saved.shape == (200, 200)
            md = float(np.max(np.abs(saved - rebuilt)))
            diffs[f"maps.cluster{cid}.{name}"] = md
            assert np.allclose(saved, rebuilt, rtol=RTOL, atol=ATOL), (cid, name, md)
            map_comparisons += saved.size

        mean_cx0 = float(np.mean(l2["cx"][event_global])) - XOFF
        mean_cy0 = float(np.mean(l2["cy"][event_global])) - YOFF
        conventions = {}
        correction_gate = []
        localized_gate = []

        for name, shift in (("C0", 0.0), ("C1", -1.0)):
            m25 = mask_for(mean_cx0 + shift, mean_cy0 + shift, AP_RADIUS)
            m35 = mask_for(mean_cx0 + shift, mean_cy0 + shift, EXCLUDE_RADIUS)
            temporal = {k: linear_prediction(times, np.asarray(v, float), side, event)
                        for k, v in sums[name].items()}
            cor_abs = float(np.sum(np.abs(cor_map)))
            concentration = float(np.sum(np.abs(cor_map[m25])) / cor_abs) if cor_abs else None
            col_ap = float(np.sum(col[m25]))
            conventions[name] = {
                "center_event_mean": [mean_cx0 + shift, mean_cy0 + shift],
                "aperture_pixels": int(m25.sum()),
                "temporal": temporal,
                "maps": {
                    "cal_r25_sum": float(np.sum(cal_map[m25])),
                    "cor_r25_sum": float(np.sum(cor_map[m25])),
                    "delta_r25_sum": float(np.sum(delta_map[m25])),
                    "cal_r35_sum": float(np.sum(cal_map[m35])),
                    "cor_r35_sum": float(np.sum(cor_map[m35])),
                    "delta_r35_sum": float(np.sum(delta_map[m35])),
                    "cal_full_sum": float(np.sum(cal_map)),
                    "cor_full_sum": float(np.sum(cor_map)),
                    "delta_full_sum": float(np.sum(delta_map)),
                    "cor_l1_concentration_r25": concentration,
                    "delta_column_component_r25_sum": col_ap,
                },
            }
            cor_ex = temporal["COR"]["event_excess"]
            delta_ex = temporal["DELTA"]["event_excess"]
            correction_gate.append(
                abs(delta_ex) >= 0.5 * abs(cor_ex) or abs(col_ap) >= 0.5 * abs(cor_ex)
            )
            localized_gate.append(
                cor_ex > 0 and concentration is not None and concentration >= 0.5
            )

        if all(correction_gate):
            label = "CORRECTION_LINKED"
        elif not any(correction_gate) and all(localized_gate):
            label = "IMAGE_LOCALIZED_NOT_CORRECTION_DOMINATED"
        else:
            label = "AMBIGUOUS_IMAGE_FOLLOWUP"
        rebuilt_labels.append(label)

        denom = float(np.sum(delta_map * delta_map))
        coherence = float(np.sum(col * col) / denom) if denom else None
        rebuilt_cluster = {
            "cluster": cid,
            "event_rows": [int(x) for x in event_global],
            "context_rows": [first, ctx["stop"] - 1],
            "ls7x_score": float(candidates[cid]["score"]),
            "conventions": conventions,
            "delta_event_map_column_coherence_fraction": coherence,
            "smear_fit_event": [fits[x]["beta"] for x in event],
            "smear_fit_side_median_beta": float(np.median([fits[x]["beta"] for x in side])),
            "classification": label,
        }
        comparisons += compare_dict_numeric(
            rebuilt_cluster, saved_clusters[cid], f"cluster[{cid}]", diffs
        )

    result = {
        "status": "PASS",
        "clusters": len(CONTEXTS),
        "saved_frame_metric_rows": len(saved_frames),
        "summary_numeric_comparisons": comparisons,
        "event_map_numeric_comparisons": map_comparisons,
        "total_numeric_comparisons": comparisons + map_comparisons,
        "maximum_absolute_differences": diffs,
        "classifications": rebuilt_labels,
        "method": (
            "independent big-endian struct parsing, scalar two-parameter normal "
            "equations, direct radius masks, and independently rebuilt pixel event maps"
        ),
        "tolerance": {"relative": RTOL, "absolute": ATOL},
    }
    (OUT / "audit.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")

    saved_summary["status"] = "COMPLETE_AUDITED"
    saved_summary["audit_status"] = "PASS"
    saved_summary["audit_numeric_comparisons"] = result["total_numeric_comparisons"]
    (OUT / "summary.json").write_text(json.dumps(saved_summary, indent=2, allow_nan=False) + "\n")

    report = (OUT / "REPORT.md").read_text()
    report = report.replace(
        "Independent publication requires the LS7Y audit.",
        f"Independent audit: **PASS** ({result['total_numeric_comparisons']:,} numerical comparisons)."
    )
    (OUT / "REPORT.md").write_text(report)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
