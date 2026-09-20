#!/usr/bin/env python3
"""Independent struct/scalar audit of the frozen LS8I GJ 649 L2 screen."""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "results_ls8i_l2_metadata"
OUT = ROOT / "results_ls8i_l2_screen"
KEYS = [
    "CH_PR100018_TG018601_V0300",
    "CH_PR100018_TG031201_V0300",
]
SIDE = 12
GUARD = 2
DURATIONS = (1, 2, 3)
SCREEN = 8.5
ROW = struct.Struct(">26sddddii7d4f")
assert ROW.size == 138


def load(path: Path):
    return json.loads(path.read_text())


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse(raw: bytes) -> dict[str, np.ndarray]:
    rows = list(ROW.iter_unpack(raw))
    return {
        "bjd": np.array([r[2] for r in rows], float),
        "flux": np.array([r[3] for r in rows], float),
        "err": np.array([r[4] for r in rows], float),
        "status": np.array([r[5] for r in rows], np.int64),
        "event": np.array([r[6] for r in rows], np.int64),
    }


def scalar_score(d: dict[str, np.ndarray], start: int, duration: int, cadence: float):
    lo = start - GUARD - SIDE
    hi = start + duration + GUARD + SIDE
    if lo < 0 or hi > len(d["flux"]):
        return None
    context = np.arange(lo, hi)
    if not (
        np.isfinite(d["bjd"][context]).all()
        and np.isfinite(d["flux"][context]).all()
        and np.isfinite(d["err"][context]).all()
        and (d["err"][context] > 0).all()
        and (d["status"][context] == 0).all()
    ):
        return None
    gaps = np.diff(d["bjd"][context]) * 86400.0
    if not ((gaps >= 0.5 * cadence) & (gaps <= 1.5 * cadence)).all():
        return None

    side = np.r_[
        np.arange(start - GUARD - SIDE, start - GUARD),
        np.arange(start + duration + GUARD, start + duration + GUARD + SIDE),
    ]
    ev = np.arange(start, start + duration)
    t0 = math.fsum(float(d["bjd"][i]) for i in ev) / duration
    xs = [(float(d["bjd"][i]) - t0) * 86400.0 for i in side]
    xe = [(float(d["bjd"][i]) - t0) * 86400.0 for i in ev]

    side_flux = [float(d["flux"][i]) for i in side]
    side_err = [float(d["err"][i]) for i in side]
    offset = float(np.median(np.asarray(side_flux)))
    ys = [y - offset for y in side_flux]

    nn = len(xs)
    sx = math.fsum(xs)
    sxx = math.fsum(x * x for x in xs)
    sy = math.fsum(ys)
    sxy = math.fsum(x * y for x, y in zip(xs, ys))
    det = nn * sxx - sx * sx
    assert det > 0
    b0 = (sy * sxx - sx * sxy) / det
    b1 = (nn * sxy - sx * sy) / det

    residual = np.asarray([y - (b0 + b1 * x) for x, y in zip(xs, ys)], float)
    med = float(np.median(residual))
    robust = 1.4826 * float(np.median(np.abs(residual - med)))
    formal = float(np.median(np.asarray(side_err)))
    floor = 1e-12 * abs(float(np.median(np.asarray(side_flux))))
    sigma = max(robust, formal, floor, 1e-12)

    excess = math.fsum(
        (float(d["flux"][i]) - offset) - (b0 + b1 * x)
        for i, x in zip(ev, xe)
    )
    x0 = float(duration)
    x1 = math.fsum(xe)
    i00 = sxx / det
    i01 = -sx / det
    i11 = nn / det
    leverage = x0 * x0 * i00 + 2.0 * x0 * x1 * i01 + x1 * x1 * i11
    denom = sigma * math.sqrt(duration + leverage)
    baseline = duration * offset + math.fsum(b0 + b1 * x for x in xe)
    return {
        "start": start,
        "duration": duration,
        "event_indices": ev.tolist(),
        "context_start": lo,
        "context_stop": hi,
        "bjd_mid": t0,
        "sigma_electrons": sigma,
        "baseline_event_sum_electrons": baseline,
        "excess_electrons": excess,
        "denominator_electrons": denom,
        "leverage": leverage,
        "score": excess / denom,
        "event_or": int(np.bitwise_or.reduce(d["event"][ev])),
        "context_event_or": int(np.bitwise_or.reduce(d["event"][context])),
    }


def groups(rows: list[dict], sign: int) -> list[dict]:
    selected = sorted(
        (r for r in rows if sign * r["score"] >= SCREEN),
        key=lambda r: (r["start"], r["start"] + r["duration"]),
    )
    result = []
    for row in selected:
        end = row["start"] + row["duration"] - 1
        if not result or row["start"] > result[-1]["max_end"] + 1:
            result.append({"min_start": row["start"], "max_end": end, "members": [row]})
        else:
            result[-1]["max_end"] = max(result[-1]["max_end"], end)
            result[-1]["members"].append(row)
    for group in result:
        group["representative"] = min(
            group["members"],
            key=lambda r: (-sign * r["score"], r["duration"], r["start"]),
        )
    return result


def main() -> None:
    suite = load(OUT / "summary.json")
    meta_all = load(META / "summary.json")
    assert suite["status"] == "COMPLETE_UNAUDITED"
    assert suite["selected_keys"] == KEYS
    assert meta_all["status"] == "PASS_COMPATIBLE"
    assert suite["screen_threshold"] == SCREEN
    assert suite["image_bytes_acquired"] == 0
    assert suite["other_apertures_opened"] is False
    meta_by_key = {x["file_key"]: x for x in meta_all["products"]}

    disagreements = []
    visit_audits = []
    for key, published_summary in zip(KEYS, suite["visits"]):
        meta = meta_by_key[key]
        folder = OUT / key
        raw = (folder / "lightcurve_table.bin").read_bytes()
        source = load(folder / "source.json")
        assert len(raw) == meta["table_bytes_declared"] == meta["rows"] * ROW.size
        assert sha(raw) == source["sha256"]
        assert source["start"] == meta["table_data_start"]
        assert source["count"] == meta["table_bytes_declared"]
        assert source["status"] == 206
        assert source["etag"] == meta["etag"]
        assert source["content_disposition"] == meta["content_disposition"]
        assert source["content_range"] == (
            f"bytes {meta['table_data_start']}-"
            f"{meta['table_data_start'] + meta['table_bytes_declared'] - 1}/"
            f"{meta['total_file_bytes']}"
        )

        data = parse(raw)
        cadence = float(meta["keywords"]["TEXPTIME"])
        rebuilt = []
        attempted = 0
        for duration in DURATIONS:
            for start in range(len(data["flux"]) - duration + 1):
                attempted += 1
                row = scalar_score(data, start, duration, cadence)
                if row is not None:
                    rebuilt.append(row)
        rebuilt.sort(key=lambda r: (r["duration"], r["start"]))
        saved = [
            json.loads(line)
            for line in gzip.decompress((folder / "ledger.jsonl.gz").read_bytes()).splitlines()
        ]
        assert [(r["start"], r["duration"]) for r in rebuilt] == [
            (r["start"], r["duration"]) for r in saved
        ]

        maxdiff = {
            "score": 0.0,
            "excess_electrons": 0.0,
            "sigma_electrons": 0.0,
            "denominator_electrons": 0.0,
            "baseline_event_sum_electrons": 0.0,
            "leverage": 0.0,
        }
        comparisons = 0
        numeric_fields = list(maxdiff)
        for a, b in zip(rebuilt, saved):
            for field in numeric_fields:
                diff = abs(a[field] - b[field])
                maxdiff[field] = max(maxdiff[field], diff)
                if not math.isclose(a[field], b[field], rel_tol=2e-8, abs_tol=2e-10):
                    disagreements.append({
                        "file_key": key,
                        "start": a["start"],
                        "duration": a["duration"],
                        "field": field,
                        "scalar": a[field],
                        "producer": b[field],
                        "difference": a[field] - b[field],
                    })
                comparisons += 1
            for field in (
                "event_indices", "context_start", "context_stop",
                "event_or", "context_event_or",
            ):
                assert a[field] == b[field]
                comparisons += 1
            assert math.isclose(a["bjd_mid"], b["bjd_mid"], rel_tol=0.0, abs_tol=5e-10)
            comparisons += 1

        published_clusters = load(folder / "clusters.json")
        for sign, label in ((1, "positive"), (-1, "negative")):
            rebuilt_groups = groups(rebuilt, sign)
            saved_groups = published_clusters[label]
            assert len(rebuilt_groups) == len(saved_groups)
            for index, (a, b) in enumerate(zip(rebuilt_groups, saved_groups)):
                assert b["cluster_id"] == index
                assert (a["min_start"], a["max_end"]) == (b["min_start"], b["max_end"])
                assert [(x["start"], x["duration"]) for x in a["members"]] == [
                    (x["start"], x["duration"]) for x in b["members"]
                ]
                assert (
                    a["representative"]["start"],
                    a["representative"]["duration"],
                ) == (
                    b["representative"]["start"],
                    b["representative"]["duration"],
                )
                assert math.isclose(
                    a["representative"]["score"],
                    b["representative"]["score"],
                    rel_tol=2e-8,
                    abs_tol=2e-10,
                )

        assert published_summary == load(folder / "summary.json")
        assert published_summary["rows"] == len(data["flux"])
        assert published_summary["eligible_windows"] == len(rebuilt)
        assert published_summary["positive_windows"] == sum(r["score"] >= SCREEN for r in rebuilt)
        assert published_summary["negative_windows"] == sum(r["score"] <= -SCREEN for r in rebuilt)
        assert published_summary["positive_clusters"] == len(groups(rebuilt, +1))
        assert published_summary["negative_clusters"] == len(groups(rebuilt, -1))
        union = {i for r in rebuilt for i in r["event_indices"]}
        assert published_summary["unique_event_rows"] == len(union)
        assert published_summary["eligible_event_row_union_seconds"] == len(union) * cadence
        if rebuilt:
            assert math.isclose(
                published_summary["maximum_score"],
                max(r["score"] for r in rebuilt),
                rel_tol=2e-8, abs_tol=2e-10,
            )
            assert math.isclose(
                published_summary["minimum_score"],
                min(r["score"] for r in rebuilt),
                rel_tol=2e-8, abs_tol=2e-10,
            )
        else:
            assert published_summary["maximum_score"] is None
            assert published_summary["minimum_score"] is None
        for d in published_summary["duration_results"]:
            selected = [r for r in rebuilt if r["duration"] == d["duration_rows"]]
            assert d["eligible_windows"] == len(selected)
            assert d["positive_windows"] == sum(r["score"] >= SCREEN for r in selected)
            assert d["negative_windows"] == sum(r["score"] <= -SCREEN for r in selected)

        failures = [x for x in disagreements if x["file_key"] == key]
        visit_audits.append({
            "file_key": key,
            "status": "FAIL" if failures else "PASS",
            "raw_rows": len(data["flux"]),
            "enumerated_windows": attempted,
            "eligible_windows": len(rebuilt),
            "numeric_and_discrete_comparisons": comparisons,
            "numeric_disagreements": len(failures),
            "maximum_absolute_differences": maxdiff,
            "signed_clusters_counts_and_summaries_verified": True,
        })

    result = {
        "status": "FAIL" if disagreements else "PASS",
        "method": "independent big-endian struct decoder and flux-centered scalar normal equations",
        "frozen_tolerances": {"relative": 2e-8, "absolute": 2e-10},
        "numeric_disagreements": disagreements,
        "visits": visit_audits,
        "numeric_and_discrete_comparisons": sum(
            v["numeric_and_discrete_comparisons"] for v in visit_audits
        ),
    }
    save = lambda p, x: p.write_text(json.dumps(x, indent=2, allow_nan=False) + "\n")
    save(OUT / "audit.json", result)
    suite["status"] = "COMPLETE_AUDITED" if result["status"] == "PASS" else "COMPLETE_AUDIT_FAILED"
    save(OUT / "summary.json", suite)

    files = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (OUT / "SHA256SUMS").write_text("".join(
        f"{sha(p.read_bytes())}  {p.relative_to(OUT)}\n" for p in files
    ))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
