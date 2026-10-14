#!/usr/bin/env python3
"""Independent audit of raw injection, box statistics, and one combined top five.

The median501 implementation maintains sorted raw float32 windows with
bisect, independently of the producer's array-window median operations.
No producer module is imported. No numerical work may run before frozen GO
and a complete producer receipt.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left, insort_right
from collections import Counter, defaultdict
import csv
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import statistics
import time

for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[var] = "1"
import numpy as np

NORMAL_FIELDS = ("row_power_median", "row_residual_median", "row_residual_MAD_scale", "row_winsorized_residual_location")
DC = (178782208, 179830784, 180879360)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def raw_digest(raw):
    return hashlib.sha256(np.asarray(raw, dtype="<f4", order="C").tobytes(order="C")).hexdigest()


def csv_rows(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def nearest_even(value):
    q = value.numerator // value.denominator
    remainder = value - q
    return q if remainder < Fraction(1, 2) else q + 1 if remainder > Fraction(1, 2) else q + q % 2


def fraction(value):
    return Fraction(*map(int, value))


def exact_centers(family, host, drift_fraction, phase):
    d = Fraction(family["original_drift_hz_s"]) + Fraction(4 / 158) * drift_fraction
    base = Fraction(family["source_reference_channel"] + host)
    return [base + phase + d * Fraction(t) / Fraction(-2.7939677238464355)
            for t in family["times_from_primary_reference_s"]]


def smear_cdf(x, width):
    """Exact trapezoid-area CDF; independent of the producer's hinge formula."""
    if width == 0:
        return min(Fraction(1), max(Fraction(0), x + Fraction(1, 2)))
    outer = (width + 1) / 2
    inner = abs(width - 1) / 2
    if x <= -outer:
        return Fraction(0)
    if x >= outer:
        return Fraction(1)
    if x < -inner:
        return (x + outer) ** 2 / (2 * width)
    if x <= inner:
        return min(width, Fraction(1)) / (2 * max(width, Fraction(1))) + (x + inner) / max(width, Fraction(1))
    return 1 - (outer - x) ** 2 / (2 * width)


def smear_weights(center, width):
    support_lo = center - (width + 1) / 2
    support_hi = center + (width + 1) / 2
    first = (support_lo - Fraction(1, 2)).numerator // (support_lo - Fraction(1, 2)).denominator
    last = math.ceil(support_hi + Fraction(1, 2))
    result = []
    for ch in range(first, last + 1):
        mass = smear_cdf(Fraction(ch) + Fraction(1, 2) - center, width) - smear_cdf(Fraction(ch) - Fraction(1, 2) - center, width)
        if mass > 0:
            result.append((ch, mass))
    require(sum(w for _, w in result) == 1, "Exact smear mass not one")
    return result


class Audit:
    def __init__(self):
        self.checks = 0
        self.max_error = defaultdict(float)

    def eq(self, got, expected, label):
        require(got == expected, f"{label}: {got!r} != {expected!r}")
        self.checks += 1

    def close(self, got, expected, label, tolerance=1e-12):
        actual = np.asarray(got, dtype=np.float64); predicted = np.asarray(expected, dtype=np.float64)
        require(actual.shape == predicted.shape, f"{label}: shapes differ")
        error = float(np.max(np.abs(actual - predicted))) if actual.size else 0.0
        require(np.isfinite(actual).all() and np.isfinite(predicted).all() and error <= tolerance,
                f"{label}: maximum absolute error {error}")
        self.max_error[label] = max(self.max_error[label], error)
        self.checks += actual.size


def raw_medians501(row, centers):
    """Odd-window median using an independent sorted sliding list."""
    centers = sorted(set(map(int, centers)))
    require(centers and centers[0] >= 250 and centers[-1] + 250 < len(row), "Median501 support incomplete")
    lo = centers[0]; hi = centers[-1]
    sequence = row.tolist()
    window = sorted(sequence[lo - 250:lo + 251])
    needed = set(centers); result = {}
    for center in range(lo, hi + 1):
        if center in needed:
            result[center] = window[250]
        if center < hi:
            old = sequence[center - 250]
            index = bisect_left(window, old)
            require(index < 501 and window[index] == old, "Sliding median deletion missing")
            window.pop(index)
            insort_right(window, sequence[center + 251])
    return result


def normalize_row(row, extra_centers=()):
    core = row[4000:8096].astype(np.float64)
    level = float(statistics.median(core.tolist()))
    require(level > 0 and math.isfinite(level), "Non-positive power median")
    medians = raw_medians501(row, list(range(4000, 8096)) + list(extra_centers))
    medians_core = np.asarray([medians[i] for i in range(4000, 8096)], dtype=np.float64)
    residual = core / level - medians_core / level
    center = float(statistics.median(residual.tolist()))
    scale = 1.4826 * float(statistics.median(np.abs(residual - center).tolist()))
    require(scale > 0 and math.isfinite(scale), "Non-positive MAD scale")
    location = center + float(np.mean(np.clip(residual - center, -5 * scale, 5 * scale), dtype=np.float64))
    return np.asarray([level, center, scale, location], dtype=np.float64), medians


def terms_for_paths(raw, channel0, rows, channels, normals, medians):
    terms = np.empty(channels.shape, dtype=np.float64)
    for pi in range(len(rows)):
        for j in range(4):
            source = int(rows[pi, j]); local = int(channels[pi, j]) - channel0
            level, _, scale, location = normals[:, source]
            residual = float(raw[source, local]) / level - medians[source][local] / level
            terms[pi, j] = (residual - location) / scale
    return terms


def path_geometry(family, host):
    paths = [(w["window_index"], w["window_source_rows"], [ch + host for ch in p["channels"]])
             for w in family["windows"] for p in w["paths"]]
    require(len({(wi, tuple(bins)) for wi, _, bins in paths}) == len(paths), "Frozen family duplicate path")
    windows = np.asarray([wi for wi, _, _ in paths], dtype=np.int64)
    rows = np.asarray([r for _, r, _ in paths], dtype=np.int64)
    channels = np.asarray([bins for _, _, bins in paths], dtype=np.int64)
    blocked = np.isin(channels, DC).any(axis=1)
    return windows, rows, channels, blocked


def ranked_truth(scores, windows, rows, channels, blocked, active_rows, bins):
    truth_cells = dict(zip(active_rows, bins))
    overlaps = [sum(truth_cells.get(int(r)) == int(ch) for r, ch in zip(rr, cc)) for rr, cc in zip(rows, channels)]
    eligible = [i for i, masked in enumerate(blocked) if not masked]
    ranked = sorted(eligible, key=lambda i: (-float(scores[i]), int(rows[i, 0]), tuple(map(int, channels[i]))))
    truth = [i for i in ranked if overlaps[i] == 4]
    require(len(truth) == 1, "Central-four truth identity missing/non-unique")
    ti = truth[0]; value = float(scores[ti])
    rank_min = 1 + sum(float(scores[i]) > value for i in eligible)
    rank_max = sum(float(scores[i]) >= value for i in eligible)
    deterministic = ranked.index(ti) + 1
    return ranked, overlaps, ti, rank_min, rank_max, deterministic


def reference_flux_capture(rows, channels, row_kernels):
    weights = {int(kernel["source_row"]): dict(zip(map(int, kernel["absolute_channels"]), map(float, kernel["weights"])))
               for kernel in row_kernels}
    return np.asarray([math.fsum(weights.get(int(r), {}).get(int(ch), 0.0) for r, ch in zip(rr, cc)) / 4
                       for rr, cc in zip(rows, channels)], dtype=np.float64)


WIDTHS = (1, 3, 9, 33)


def template_geometry(family, host):
    windows, rows, channels, blocked = path_geometry(family, host)
    count = len(windows)
    return {"width": np.repeat(WIDTHS, count).astype(np.int64),
            "path_index": np.tile(np.arange(count, dtype=np.int64), len(WIDTHS)),
            "window_index": np.tile(windows, len(WIDTHS)), "source_rows": np.tile(rows, (len(WIDTHS), 1)),
            "native4": np.tile(channels, (len(WIDTHS), 1)),
            "dc_mask": np.asarray([any(center - width // 2 <= dc <= center + width // 2 for center in ch for dc in DC)
                                    for width in WIDTHS for ch in channels], dtype=bool)}


def requested_box_cells(templates, channel0):
    result = defaultdict(set)
    for w, rr, cc in zip(templates["width"], templates["source_rows"], templates["native4"]):
        for r, ch in zip(rr, cc):
            result[int(r)].update(range(int(ch) - channel0 - int(w) // 2, int(ch) - channel0 + int(w) // 2 + 1))
    return result


def standardized_cells(raw, normals, medians, needed):
    result = {}
    for r, locals_ in needed.items():
        level, _, scale, location = normals[:, r]
        result[r] = {local: (float(raw[r, local]) / level - medians[r][local] / level - location) / scale
                     for local in locals_}
    return result


def score_boxes(templates, channel0, cells):
    terms = np.empty((len(templates["width"]), 4), dtype=np.float64)
    for ti, (width, rows, centers) in enumerate(zip(templates["width"], templates["source_rows"], templates["native4"])):
        half = int(width) // 2
        for j, (r, ch) in enumerate(zip(rows, centers)):
            center = int(ch) - channel0
            values = np.asarray([cells[int(r)][k] for k in range(center - half, center + half + 1)], dtype=np.float64)
            terms[ti, j] = values.sum(dtype=np.float64)
    scores = terms.sum(axis=1, dtype=np.float64) / np.sqrt(4 * templates["width"])
    return terms, scores


def capture_diagnostics(templates, kernels):
    response = {int(k["source_row"]): dict(zip(map(int, k["absolute_channels"]), map(float, k["weights"]))) for k in kernels}
    capture = np.empty(len(templates["width"]), dtype=np.float64)
    full_support = np.empty(len(templates["width"]), dtype=bool)
    for ti, (width, rows, centers) in enumerate(zip(templates["width"], templates["source_rows"], templates["native4"])):
        boxes = {int(r): (int(ch) - int(width) // 2, int(ch) + int(width) // 2) for r, ch in zip(rows, centers)}
        values = []
        complete = True
        for r, weights in response.items():
            if r not in boxes:
                values.append(0.0); complete = False
                continue
            lo, hi = boxes[r]
            values.append(math.fsum(w for ch, w in weights.items() if lo <= ch <= hi))
            complete = complete and all(lo <= ch <= hi for ch, w in weights.items() if w > 0)
        capture[ti] = math.fsum(values) / 4
        full_support[ti] = complete
    return capture, full_support


def ordered_templates(templates, scores, width1_only=False):
    indices = [i for i, masked in enumerate(templates["dc_mask"]) if not masked
               and (not width1_only or int(templates["width"][i]) == 1)]
    return sorted(indices, key=lambda i: (-float(scores[i]), int(templates["width"][i]),
                  int(templates["source_rows"][i, 0]), tuple(map(int, templates["native4"][i]))))


def boolean(value):
    require(value in (True, False, "True", "False"), "Invalid CSV boolean")
    return value in (True, "True")


def min_med_max(values):
    values = sorted(values)
    return [values[0], statistics.median(values), values[-1]]


def kernels_for(geometry):
    return geometry["row_kernels"] if "row_kernels" in geometry else geometry["models"]["integration_smear"]["row_kernels"]


def check_new_metadata(manifest, families, audit):
    profile_keys = set(); physical_keys = set(); cells = set(); sweep_widths = []
    for g in manifest["geometries"]:
        host = int(g["host_offset_channels"]); family = families[g["profile_id"]]
        f, ph, start = (Fraction(-31, 100), Fraction(-7, 100), 4) if host == -384 else (Fraction(79, 100), Fraction(41, 100), 8)
        require(host in (-384, 384), "Undeclared matched raw host")
        audit.eq(fraction(g["drift_fraction"]), f, "New matched drift identity")
        audit.eq(fraction(g["phase_fraction"]), ph, "New matched phase identity")
        centers = exact_centers(family, host, f, ph); truth = [nearest_even(c) for c in centers]
        active = list(range(start, start + 4))
        audit.eq(g["truth16"], truth, "Matched exact canonical centers")
        audit.eq(g["true_active_source_rows"], active, "Matched true active rows")
        audit.eq(g["truth_active4"], [truth[r] for r in active], "Matched canonical central4")
        key = (g["profile_id"], host, tuple(active), tuple(g["truth_active4"]))
        physical = (g["context_scan_id"], tuple(active), tuple(g["truth_active4"]))
        require(key not in profile_keys and physical not in physical_keys, "Aliased matched placement")
        profile_keys.add(key); physical_keys.add(physical)
        d = Fraction(family["original_drift_hz_s"]) + Fraction(4 / 158) * f
        width = abs(d * Fraction(18.253611008) / Fraction(-2.7939677238464355))
        sweep_widths.append(float(width))
        kernels = kernels_for(g)
        audit.eq([k["source_row"] for k in kernels], active, "Matched kernel row order")
        for k in kernels:
            r = int(k["source_row"]); response = smear_weights(centers[r], width)
            audit.eq(k["absolute_channels"], [ch for ch, _ in response], "Matched independent response channels")
            audit.eq([fraction(w) for w in k["exact_weights"]], [w for _, w in response], "Matched independent exact response masses")
            weights = [float(w) for _, w in response]; total = math.fsum(weights)
            audit.close(k["weights"], [w / total for w in weights], "Matched normalized response weights", 0.0)
            cells.update((g["context_scan_id"], r, int(ch)) for ch in k["absolute_channels"])
        templates = template_geometry(family, host)
        capture, complete = capture_diagnostics(templates, kernels)
        coefficient = 2 * capture / np.sqrt(templates["width"])
        width_oracles = {}
        for w in WIDTHS:
            eligible = (~templates["dc_mask"]) & (templates["width"] == w)
            projection = g["per_width_projection"][str(w)]
            central = next(i for i in range(len(capture)) if int(templates["width"][i]) == w
                           and templates["source_rows"][i].tolist() == active
                           and templates["native4"][i].tolist() == g["truth_active4"])
            audit.eq(projection["allowed_unique_template_count"], int(eligible.sum()), "Per-width metadata family count")
            audit.eq(projection["full_coverage_hypothesis_count"], int(complete[eligible].sum()), "Per-width metadata full-support count")
            audit.eq(projection["oracle_full_positive_kernel_coverage"], bool(complete[eligible].any()), "Per-width metadata full-support oracle")
            audit.eq(projection["canonical_center_full_positive_kernel_coverage"], bool(complete[central]), "Canonical box full support")
            audit.close(projection["oracle_ideal_deposited_fraction"], capture[eligible].max(), "Per-width metadata ideal fraction oracle")
            audit.close(projection["canonical_center_ideal_deposited_fraction"], capture[central], "Canonical box ideal fraction")
            audit.close(projection["ideal_best_score_per_reference_A"], 2 * capture[eligible].max() / math.sqrt(w), "Per-width ideal box coefficient")
            audit.close(projection["template_ideal_standardized_score_coefficients"], coefficient[eligible], "Independent per-template ideal coefficients")
            width_oracles[w] = float(coefficient[eligible].max())
        model = g["models"]["integration_smear"]
        best = max(width_oracles.values()); optimal = [w for w in WIDTHS if width_oracles[w] == best]
        audit.close(model["combined_family_oracle_ideal_standardized_score_coefficient"], best, "Combined ideal score coefficient oracle")
        audit.eq(model["oracle_optimal_width"], min(optimal), "Oracle coefficient optimal width")
        audit.eq(model["oracle_tied_optimal_widths"], optimal, "Oracle coefficient tied optimal widths")
    audit.eq(len(profile_keys), 108, "Matched new placement count")
    return {"new_unique_profile_placements": len(profile_keys), "new_unique_physical_placements": len(physical_keys),
            "new_positive_response_cells": len(cells), "sweep_width_min_max": [min(sweep_widths), max(sweep_widths)]}, cells


def check_policy(record, templates, scores, capture, full, coefficient, g, audit, baseline_scores=None):
    policy = record["policy"]
    require(policy in ("combined", "width1_only"), "Undeclared selection policy")
    ranked = ordered_templates(templates, scores, policy == "width1_only"); top = ranked[:5]
    path_count = len(scores) // 4
    canonical = next(i for i in range(path_count) if templates["source_rows"][i].tolist() == g["true_active_source_rows"]
                     and templates["native4"][i].tolist() == g["truth_active4"])
    uplifts = np.zeros_like(scores) if baseline_scores is None else scores - baseline_scores
    audit.eq(int(record["retained_count"]), 5, "One retained list has five slots")
    audit.eq(int(record["eligible_template_count"]), len(ranked), "Policy scored eligible family")
    audit.eq(int(record["winner_template_id"]), top[0], "Winner template identity")
    audit.eq(int(record["winner_path_index"]), int(templates["path_index"][top[0]]), "Winner native path")
    audit.eq(int(record["winner_width"]), int(templates["width"][top[0]]), "Winner matched width")
    audit.close(float(record["winner_score"]), scores[top[0]], "Winner actual raw score")
    audit.eq(json.loads(record["retained_template_ids"]), top, "Actual single top-five identities")
    audit.eq(json.loads(record["retained_widths"]), templates["width"][top].tolist(), "Actual top-five widths")
    audit.close(json.loads(record["retained_scores"]), scores[top], "Actual top-five raw scores")
    audit.close(json.loads(record["retained_reference_weight_fractions"]), capture[top], "Actual top-five ideal deposited fractions")
    audit.eq(json.loads(record["retained_full_positive_kernel_cell_coverage"]), full[top].tolist(), "Actual top-five positive-cell coverage")
    audit.close(json.loads(record["retained_ideal_standardized_score_coefficients"]), coefficient[top], "Actual top-five ideal coefficients")
    best_fraction = float(capture[top].max()); best_coefficient = float(coefficient[top].max())
    oracle_fraction = float(capture[ranked].max()); oracle_coefficient = float(coefficient[ranked].max())
    floats = {"best_retained_reference_weight_fraction": best_fraction,
              "signal_only_oracle_reference_weight_fraction": oracle_fraction,
              "best_retained_ideal_standardized_score_coefficient": best_coefficient,
              "signal_only_oracle_ideal_standardized_score_coefficient": oracle_coefficient,
              "best_retained_coefficient_fraction_of_oracle": best_coefficient / oracle_coefficient,
              "ideal_standardized_score_coefficient_gap_to_oracle": oracle_coefficient - best_coefficient}
    for field, expected in floats.items(): audit.close(float(record[field]), expected, "Matched policy " + field)
    audit.close(json.loads(record["retained_actual_score_uplifts"]), uplifts[top], "Actual retained box score changes")
    audit.close(float(record["winner_actual_score_uplift"]), uplifts[top[0]], "Actual winner box score change")
    audit.close(float(record["best_retained_actual_score_uplift"]), uplifts[top].max(), "Largest retained actual score change")
    audit.close(json.loads(record["canonical_score_uplift_by_width"]), uplifts[[wi * path_count + canonical for wi in range(4)]], "Actual canonical box changes by width")
    covered = bool(full[top].any()); canonical_retained = any(i % path_count == canonical for i in top)
    audit.eq(boolean(record["any_retained_full_positive_kernel_cell_coverage"]), covered, "Top-five full support is geometric")
    audit.eq(int(record["retained_full_positive_kernel_cell_coverage_count"]), int(full[top].sum()), "Retained full-support count")
    audit.eq(boolean(record["signal_only_oracle_full_positive_kernel_cell_coverage"]), bool(full[ranked].any()), "Policy geometric full-support oracle")
    audit.eq(boolean(record["canonical_center_retained_any_width"]), canonical_retained, "Secondary canonical-center retention")
    canonical_ranks = []
    for wi, width in enumerate(WIDTHS):
        if policy == "width1_only" and wi:
            canonical_ranks.append(None); continue
        index = wi * path_count + canonical; value = scores[index]
        higher = sum(scores[i] > value for i in ranked); equal = sum(scores[i] == value for i in ranked)
        canonical_ranks.append({"width": width, "rank_min": 1 + higher, "rank_max": higher + equal,
                                "rank_tie_count": equal, "deterministic_rank": ranked.index(index) + 1})
    audit.eq(json.loads(record["canonical_center_rank_by_width"]), canonical_ranks, "Secondary canonical score ranks and exact ties")
    return top, {"full": covered, "canonical": canonical_retained, "fraction": best_fraction,
                 "oracle_fraction": oracle_fraction, "coefficient": best_coefficient,
                 "oracle_coefficient": oracle_coefficient, "coefficient_ratio": best_coefficient / oracle_coefficient,
                 "coefficient_gap": oracle_coefficient - best_coefficient, "actual_uplift": float(uplifts[top].max())}


def policy_summary(values):
    return {"lists": len(values), "retained_slots": 5 * len(values),
            "any_full_positive_kernel_cell_coverage_count": sum(v["full"] for v in values),
            "best_retained_reference_weight_fraction_min_median_max": min_med_max([v["fraction"] for v in values]),
            "oracle_reference_weight_fraction_min_median_max": min_med_max([v["oracle_fraction"] for v in values]),
            "canonical_center_retained_any_width_count": sum(v["canonical"] for v in values),
            "best_retained_ideal_standardized_score_coefficient_min_median_max": min_med_max([v["coefficient"] for v in values]),
            "oracle_ideal_standardized_score_coefficient_min_median_max": min_med_max([v["oracle_coefficient"] for v in values]),
            "best_retained_coefficient_fraction_of_oracle_min_median_max": min_med_max([v["coefficient_ratio"] for v in values]),
            "best_retained_actual_score_uplift_min_median_max": min_med_max([v["actual_uplift"] for v in values])}


def check_summary(got, expected, audit):
    for field, value in expected.items():
        if isinstance(value, list): audit.close(got[field], value, "Independent matched summary " + field)
        else: audit.eq(got[field], value, "Independent matched summary " + field)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("input_root", type=Path); ap.add_argument("stage_root", type=Path)
    ap.add_argument("--go-scope-sha256", required=True); args = ap.parse_args()
    cpu0 = time.process_time(); wall0 = time.monotonic()
    root = args.input_root.resolve(); stage = args.stage_root.resolve(); out = stage / "results"
    scope_path = stage / "SCOPE.json"; scope = read_json(scope_path); go = read_json(stage / "GO.json")
    require(digest(scope_path) == args.go_scope_sha256 == go["scope_sha256"], "Matched frozen scope differs")
    require(digest(Path(__file__).resolve()) == go["qa_sha256"], "Matched frozen QA differs")
    require(digest(stage / "producer.py") == go["producer_sha256"] == scope["producer_pin"]["sha256"], "Matched frozen producer differs")
    budget = scope["resource_envelope"]
    resource.setrlimit(resource.RLIMIT_CPU, (budget["QA_CPU_s_cap"], budget["QA_CPU_s_cap"]))
    resource.setrlimit(resource.RLIMIT_AS, (budget["memory_bytes_cap_each"], budget["memory_bytes_cap_each"]))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("Matched QA wall cap exceeded")))
    signal.alarm(budget["wall_s_cap_each"]); audit = Audit()
    for pin in scope["input_pins"]:
        p = root / pin["path"]; audit.eq(p.stat().st_size, pin["bytes"], "Matched source pinned length")
        audit.eq(digest(p), pin["sha256"], "Matched source pinned hash")
    for pin in scope["stage_input_pins"]:
        p = stage / pin["path"]; audit.eq(p.stat().st_size, pin["bytes"], "Matched stage pinned length")
        audit.eq(digest(p), pin["sha256"], "Matched stage pinned hash")
    manifest_path = stage / scope["geometry_manifest_pin"]["path"]
    audit.eq(digest(manifest_path), scope["geometry_manifest_pin"]["sha256"], "Matched manifest scope hash")
    audit.eq(digest(manifest_path), go["metadata_manifest_sha256"], "Matched manifest GO hash")
    manifest = read_json(manifest_path)
    matrix = read_json(root / "seti_work/seti_burst_full/context_results/CONTEXT_PROFILES.json")
    families = {p["profile_id"]: p for p in read_json(root / "rounding_followup/exact_geometry_results/GEOMETRY.json")["profiles"]}
    novelty, new_cells = check_new_metadata(manifest, families, audit)
    old_cells = set(); old_physical = set()
    for trial in read_json(root / "rounding_followup/results/INJECTIONS.json")["trials"]:
        for field in ("canonical_float_truth_absolute_centers", "canonical_rational_truth_absolute_centers"):
            active = trial["true_active_source_rows"]; bins = tuple(trial[field][r] for r in active)
            old_physical.add((trial["context_scan_id"], tuple(active), bins))
            old_cells.update((trial["context_scan_id"], int(r), int(ch)) for r, ch in zip(active, bins))
    for old in read_json(stage / "prior_placements/GEOMETRY_MANIFEST_TOP5.json")["geometries"]:
        old_physical.add((old["context_scan_id"], tuple(old["true_active_source_rows"]), tuple(old["truth_active4"])))
        old_cells.update((old["context_scan_id"], int(r), int(ch)) for r, ch in zip(old["true_active_source_rows"], old["truth_active4"]))
    for old in read_json(stage / "prior_placements/GEOMETRY_MANIFEST_RAW648.json")["geometries"]:
        old_physical.add((old["context_scan_id"], tuple(old["true_active_source_rows"]), tuple(old["truth_active4"])))
        for model in old["models"].values():
            for k in model["row_kernels"]: old_cells.update((old["context_scan_id"], int(k["source_row"]), int(ch)) for ch, w in zip(k["absolute_channels"], k["weights"]) if w > 0)
    audit.eq(len(old_physical), manifest["counts"]["prior_physical_placements"], "All prior physical placement census")
    audit.eq(len(old_cells), manifest["counts"]["prior_positive_injection_cells"], "All prior positive source-cell census")
    audit.eq(len(new_cells & old_cells), 0, "Fresh matched positive source-cell footprint")
    novelty["prior_positive_cell_overlap"] = len(new_cells & old_cells)
    receipt = read_json(out / "EXECUTION_RECEIPT.json")
    audit.eq(receipt["status"], "COMPLETE", "Matched producer complete before QA")
    audit.eq(receipt["scope_sha256"], digest(scope_path), "Matched producer scope receipt")
    audit.eq(receipt["producer_sha256"], go["producer_sha256"], "Matched producer code receipt")
    audit.eq(receipt["effective_input_root"], str(root), "Matched runtime raw source")
    for pin in receipt["outputs"]:
        p = out / pin["path"]; audit.eq(p.stat().st_size, pin["bytes"], "Matched output pinned length")
        audit.eq(digest(p), pin["sha256"], "Matched output pinned hash")
    def table_map(name, key):
        source = csv_rows(out / name) if name.endswith(".csv") else read_json(out / name)
        return {key(r): r for r in source}
    policies = table_map("POLICY_RESULTS.csv", lambda r: (r["case_id"], r["policy"]))
    baseline_policies = table_map("BASELINE_POLICY_RESULTS.csv", lambda r: (r["geometry_id"], r["policy"]))
    norm_rows = table_map("NORMALIZATION_DELTA.csv", lambda r: (r["case_id"], int(r["source_row"])))
    retained = table_map("RETAINED_HYPOTHESES.csv", lambda r: (r["case_id"], r["policy"], int(r["rank"])))
    cases = {r["case_id"]: r for r in read_json(out / "CASE_ARRAYS.json")["cases"]}
    baselines = {r["profile_id"]: r for r in read_json(out / "BASELINE_ARRAYS.json")["profiles"]}
    for actual, expected, label in ((len(policies), 432, "positive policy lists"), (len(baseline_policies), 216, "baseline policy lists"),
                                   (len(norm_rows), 864, "modified normalized rows"), (len(retained), 2160, "retained template rows"),
                                   (len(cases), 216, "raw case arrays"), (len(baselines), 54, "baseline arrays")):
        audit.eq(actual, expected, "Matched " + label)
    grouped = defaultdict(list)
    for g in manifest["geometries"]: grouped[g["profile_id"]].append(g)
    panels = defaultdict(list); baseline_stats = defaultdict(list); strata = defaultdict(list); width_counts = defaultdict(Counter)
    checked_scores = 0; checked_box_values = 0
    for pi, profile in enumerate(matrix["profiles"]):
        pid = profile["profile_id"]; family = families[pid]
        with np.load(root / "seti_work" / profile["raw_normalization_crop"]["path"], allow_pickle=False) as z:
            raw = z["raw_power"]; channel0 = int(z["source_channel0"])
            require(raw.shape == (16, 12096) and raw.dtype == np.dtype("<f4") and np.isfinite(raw).all() and (raw >= 0).all(), "Matched raw source shape/type/power")
            audit.eq(z["absolute_time_rows"].tolist(), list(range(16)), "Matched raw time rows")
            audit.eq(z["normalization_source_channels"].tolist(), list(range(channel0 + 4000, channel0 + 8096)), "Matched normalization core coordinates")
        source_hash = raw_digest(raw)
        saved = read_json(root / "seti_work" / profile["normalization"]["path"])
        saved_norm = np.asarray([saved[k] for k in NORMAL_FIELDS], dtype=np.float64)
        template_sets = {h: template_geometry(family, h) for h in (-384, 384)}
        needed = defaultdict(set)
        for t in template_sets.values():
            for r, positions in requested_box_cells(t, channel0).items(): needed[r].update(positions)
        normal = np.empty((4, 16), dtype=np.float64); medians = {}
        for r in range(16): normal[:, r], medians[r] = normalize_row(raw[r], needed[r])
        audit.close(normal[0], saved_norm[0], "Matched baseline saved power median", 0.0)
        audit.close(normal[1:], saved_norm[1:], "Matched baseline full4096 normalization")
        base_cells = standardized_cells(raw, normal, medians, needed)
        bm = baselines.pop(pid); audit.eq(bm["raw_source_power_bytes_sha256"], source_hash, "Matched whole original raw hash")
        cache = {}
        with np.load(out / bm["arrays"]["path"], allow_pickle=False) as z:
            audit.eq(z["widths"].tolist(), list(WIDTHS), "Frozen scored widths")
            audit.eq(z["offset_channels"].tolist(), [-384, 384], "Matched baseline offsets")
            for j, k in enumerate(NORMAL_FIELDS):
                audit.close(z[k], normal[j], "Matched operational baseline normalization")
                audit.close(z["saved_" + k], saved_norm[j], "Matched saved amplitude reference", 0.0)
            for oi, host in enumerate((-384, 384)):
                t = template_sets[host]; count = len(t["width"]) // 4
                g = next(g for g in grouped[pid] if g["host_offset_channels"] == host)
                terms, scores = score_boxes(t, channel0, base_cells)
                capture, full = capture_diagnostics(t, kernels_for(g)); coefficient = 2 * capture / np.sqrt(t["width"])
                audit.eq(z["absolute_centers"][oi].tolist(), t["native4"][:count].tolist(), "Baseline matched centers")
                audit.eq(z["path_source_rows"].tolist(), t["source_rows"][:count].tolist(), "Baseline matched rows")
                audit.eq(z["path_window_index"].tolist(), t["window_index"][:count].tolist(), "Baseline matched windows")
                audit.eq(z["path_dc_mask"][oi].reshape(-1).tolist(), t["dc_mask"].tolist(), "Baseline extended box DC masks")
                audit.close(z["row_box_sum_z"][oi].reshape(-1, 4), terms, "Baseline independent ascending box sums")
                audit.close(z["scores"][oi].reshape(-1), scores, "Baseline independent box scores")
                audit.close(z["reference_weight_capture_fraction"][oi].reshape(-1), capture, "Baseline ideal deposited fractions")
                audit.eq(z["full_positive_kernel_cell_coverage"][oi].reshape(-1).tolist(), full.tolist(), "Baseline full positive-cell geometry")
                audit.close(z["ideal_standardized_score_coefficient"][oi].reshape(-1), coefficient, "Baseline ideal coefficient")
                cache[host] = (terms, scores, capture, full, coefficient)
                checked_scores += len(scores); checked_box_values += int(sum(4 * int(w) for w in t["width"]))
        for g in grouped[pid]:
            gid = g["geometry_id"]; host = int(g["host_offset_channels"]); active = g["true_active_source_rows"]
            t = template_sets[host]; count = len(t["width"]) // 4
            _, base_scores, capture, full, coefficient = cache[host]
            for policy in ("combined", "width1_only"):
                br = baseline_policies.pop((gid, policy)); audit.eq(boolean(br["sham_target_only"]), True, "Matched baseline sham marker")
                _, stats = check_policy(br, t, base_scores, capture, full, coefficient, g, audit); baseline_stats[policy].append(stats)
            kernels = kernels_for(g); needed_case = requested_box_cells(t, channel0)
            central_class = "ALL_CENTRAL_IN_CORE" if g["central_bins_in_core"] == 4 else "ALL_CENTRAL_OUTSIDE_CORE" if g["central_bins_in_core"] == 0 else "MIXED_CENTRAL_CORE"
            for amp in (8, 32):
                cid = gid + "_integration_smear_A" + str(amp); cm = cases.pop(cid)
                modified = raw.copy(); injected = []
                for k in kernels:
                    r = int(k["source_row"]); local = np.asarray(k["absolute_channels"], dtype=np.int64) - channel0
                    weights = np.asarray(k["weights"], dtype=np.float64)
                    power = amp * float(saved_norm[0, r]) * float(saved_norm[2, r]) * weights
                    before = raw[r, local].astype(np.float64); modified[r, local] = (before + power).astype("<f4")
                    injected.append((r, k["absolute_channels"], power, modified[r, local].astype(np.float64) - before))
                unchanged = [r for r in range(16) if r not in active]
                require(np.array_equal(modified[unchanged], raw[unchanged]), "Matched other12 raw rows changed")
                modified_hash = raw_digest(modified)
                audit.eq(cm["raw_source_power_bytes_sha256"], source_hash, "Matched case original raw hash")
                audit.eq(cm["raw_modified_power_bytes_sha256"], modified_hash, "Matched whole216 raw byte hashes")
                for actual, expected in zip(cm["injected_cells"], injected):
                    r, absolute, power, deposited = expected
                    audit.eq(actual["source_row"], r, "Matched modified source row")
                    audit.eq(actual["absolute_channels"], absolute, "Matched modified absolute cells")
                    audit.close(actual["requested_power_increment"], power, "Matched requested raw increments", 0.0)
                    audit.close(actual["actual_float32_power_increment"], deposited, "Matched quantized raw increments", 0.0)
                case_normal = normal.copy(); case_medians = dict(medians)
                for r in active:
                    case_normal[:, r], case_medians[r] = normalize_row(modified[r], needed_case[r])
                    nr = norm_rows.pop((cid, r))
                    for j, k in enumerate(NORMAL_FIELDS):
                        audit.close(float(nr[k + "_before"]), normal[j, r], "Matched row norm before", 0.0)
                        audit.close(float(nr[k + "_after"]), case_normal[j, r], "Matched row norm after")
                        audit.close(float(nr[k + "_delta"]), case_normal[j, r] - normal[j, r], "Matched row norm delta")
                case_cells = standardized_cells(modified, case_normal, case_medians, needed_case)
                terms, scores = score_boxes(t, channel0, case_cells)
                with np.load(out / cm["arrays"]["path"], allow_pickle=False) as z:
                    audit.eq(z["widths"].tolist(), list(WIDTHS), "Case fixed widths")
                    audit.eq(z["absolute_centers"].tolist(), t["native4"][:count].tolist(), "Case matched centers")
                    audit.eq(z["path_source_rows"].tolist(), t["source_rows"][:count].tolist(), "Case matched rows")
                    audit.eq(z["path_window_index"].tolist(), t["window_index"][:count].tolist(), "Case matched windows")
                    audit.eq(z["path_dc_mask"].reshape(-1).tolist(), t["dc_mask"].tolist(), "Case extended box DC masks")
                    for j, k in enumerate(NORMAL_FIELDS):
                        audit.close(z[k], case_normal[j], "Matched all16 case normalization")
                        audit.close(z[k][unchanged], normal[j, unchanged], "Matched other12 exact baseline norms", 0.0)
                    audit.close(z["row_box_sum_z"].reshape(-1, 4), terms, "Case independent ascending box sums")
                    audit.close(z["scores"].reshape(-1), scores, "Case independent box scores")
                    audit.close(z["reference_weight_capture_fraction"].reshape(-1), capture, "Case ideal deposited fractions")
                    audit.eq(z["full_positive_kernel_cell_coverage"].reshape(-1).tolist(), full.tolist(), "Case full positive-cell geometry")
                    audit.close(z["ideal_standardized_score_coefficient"].reshape(-1), coefficient, "Case independent ideal coefficients")
                    audit.close(z["score_uplift"].reshape(-1), scores - base_scores, "Case independently computed score changes")
                checked_scores += len(scores); checked_box_values += int(sum(4 * int(w) for w in t["width"]))
                for policy in ("combined", "width1_only"):
                    record = policies.pop((cid, policy))
                    audit.eq(record["raw_modified_power_bytes_sha256"], modified_hash, "Policy full raw hash")
                    audit.eq(record["central_truth_core_class"], central_class, "Matched mixed/core/outside stratum")
                    top, stats = check_policy(record, t, scores, capture, full, coefficient, g, audit, base_scores)
                    panels[(amp, policy)].append(stats); strata[(amp, central_class, policy)].append(stats)
                    width_counts[(amp, policy)].update(int(t["width"][i]) for i in top)
                    for rank, index in enumerate(top, 1):
                        rr = retained.pop((cid, policy, rank))
                        for field, value in (("template_id", index), ("width", int(t["width"][index])),
                                             ("path_index", int(t["path_index"][index])), ("window_index", int(t["window_index"][index]))):
                            audit.eq(int(rr[field]), value, "Matched retained " + field)
                        audit.eq(json.loads(rr["source_rows"]), t["source_rows"][index].tolist(), "Matched retained source rows")
                        audit.eq(json.loads(rr["native4_centers"]), t["native4"][index].tolist(), "Matched retained centers")
                        audit.close(float(rr["score"]), scores[index], "Matched retained raw score")
                        audit.close(float(rr["reference_weight_capture_fraction"]), capture[index], "Matched retained deposited fraction")
                        audit.eq(boolean(rr["full_positive_kernel_cell_coverage"]), bool(full[index]), "Matched retained geometric support")
                        audit.close(float(rr["ideal_standardized_score_coefficient"]), coefficient[index], "Matched retained ideal coefficient")
                        audit.close(float(rr["actual_score_uplift"]), scores[index] - base_scores[index], "Matched retained actual score change")
        print(json.dumps({"QA_profiles_complete": pi + 1, "checks": audit.checks, "CPU_s": time.process_time() - cpu0}), flush=True)
    require(not policies and not baseline_policies and not norm_rows and not retained and not cases and not baselines, "Unaudited matched results remain")
    summary = read_json(out / "SUMMARY.json")
    for (amp, policy), values in panels.items(): check_summary(summary["amplitude_panels"][str(amp)][policy], policy_summary(values), audit)
    for policy, values in baseline_stats.items(): check_summary(summary["baseline_sham_target"][policy], policy_summary(values), audit)
    for (amp, label, policy), values in strata.items(): check_summary(summary["by_central_truth_core_class"][str(amp)][label][policy], policy_summary(values), audit)
    for (amp, policy), counts in width_counts.items(): audit.eq(summary["retained_width_counts_by_amplitude_policy"][str(amp)][policy], {str(w): n for w, n in counts.items()}, "Matched retained width distribution")
    workload = {"combined_per_list": 5, "width1_only_per_list": 5, "ratio": 1, "combined_positive_slots": 1080,
                "width1_positive_slots": 1080, "combined_baseline_slots": 540, "width1_baseline_slots": 540, "per_width_top5_used": False}
    audit.eq(summary["candidate_workload"], workload, "Same five slots, one combined list")
    for field, expected in (("qualified_SETI_detection", False), ("calibrated_FAP", False), ("physical_sensitivity_established", False),
                            ("original_A_B", "FAIL_CLOSED"), ("full6scan_chain_gate_pass", False), ("new_observation", False),
                            ("new_telescope_requests", 0), ("new_telescope_bytes", 0), ("raw_spectral_arrays_opened", 54)):
        audit.eq(summary[field], expected, "Matched conditional-control interpretation " + field)
    usage = {"CPU_s": time.process_time() - cpu0, "wall_s": time.monotonic() - wall0,
             "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    require(usage["CPU_s"] <= budget["QA_CPU_s_cap"] and usage["wall_s"] <= budget["wall_s_cap_each"]
            and usage["peak_RSS_bytes"] <= budget["memory_bytes_cap_each"], "Matched QA resource cap exceeded")
    result = {"schema": "SETI_MATCHED_WIDTH_INDEPENDENT_QA_V1", "status": "PASS_INDEPENDENT_RAW_MEDIAN501_BOX_SCORE_POLICY_COVERAGE_COEFFICIENT",
              "scope_sha256": digest(scope_path), "qa_sha256": digest(Path(__file__).resolve()), "producer_sha256": go["producer_sha256"],
              "profiles": 54, "raw_cases": 216, "checked_template_scores": checked_scores, "checked_box_cell_values": checked_box_values,
              "checks": audit.checks, "maximum_absolute_errors": dict(audit.max_error), "independent_novelty": novelty,
              "amplitude_panels": {str(a): {p: policy_summary(panels[(a, p)]) for p in ("combined", "width1_only")} for a in (8, 32)},
              "baseline_sham_target": {p: policy_summary(values) for p, values in baseline_stats.items()},
              "geometric_support_is_detection_recovery_gate": False, "new_observation": False,
              "qualified_SETI_detection": False, "calibrated_FAP": False, "physical_sensitivity_established": False,
              "full6scan_chain_gate_pass": False, "resource_usage": usage}
    with (out / "QA_RECEIPT.json").open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True, allow_nan=False); f.write("\n")
    signal.alarm(0); print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

