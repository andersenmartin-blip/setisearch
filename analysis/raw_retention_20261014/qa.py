#!/usr/bin/env python3
"""Independent audit of raw-power injection and refitted local retention.

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


def metadata_check(manifest, families, audit):
    seen = set(); physical = set(); classes = defaultdict(Counter); sweep_widths = []
    for g in manifest["geometries"]:
        pid = g["profile_id"]; family = families[pid]; host = int(g["host_offset_channels"])
        require(host in (-640, 640), "Undeclared raw host")
        f, ph, start = (Fraction(-67, 100), Fraction(-19, 100), 0) if host == -640 else (Fraction(23, 100), Fraction(33, 100), 12)
        audit.eq(fraction(g["drift_fraction"]), f, "Frozen new drift identity")
        audit.eq(fraction(g["phase_fraction"]), ph, "Frozen new phase identity")
        centers = exact_centers(family, host, f, ph)
        audit.eq([fraction(c) for c in g["continuous_centers_fraction"]], centers, "Exact continuous midpoint centers")
        truth = [nearest_even(c) for c in centers]
        active = list(range(start, start + 4))
        audit.eq(g["truth16"], truth, "Exact central truth16")
        audit.eq(g["true_active_source_rows"], active, "Exact active rows")
        audit.eq(g["truth_active4"], [truth[r] for r in active], "Exact central active4")
        core_lo, core_hi = g["normalization_core_interval_half_open"]
        audit.eq(g["central_bins_in_core"], sum(core_lo <= truth[r] < core_hi for r in active), "Central bins in fixed normalization core")
        key = (pid, host, tuple(active), tuple(g["truth_active4"]))
        require(key not in seen, "Duplicate raw placement")
        seen.add(key)
        physical_key = (g["context_scan_id"], tuple(active), tuple(g["truth_active4"]))
        require(physical_key not in physical, "Cross-profile physical raw placement duplicate")
        physical.add(physical_key)
        d = Fraction(family["original_drift_hz_s"]) + Fraction(4 / 158) * f
        width = abs(d * Fraction(18.253611008) / Fraction(-2.7939677238464355))
        audit.eq(fraction(g["integration_sweep_channels_fraction"]), width, "Exact drift exposure width")
        sweep_widths.append(float(width))
        for model in ("delta", "fixed3", "integration_smear"):
            kernels = g["models"][model]["row_kernels"]
            audit.eq([k["source_row"] for k in kernels], active, "Kernel active row order")
            for kernel in kernels:
                row = int(kernel["source_row"])
                if model == "delta":
                    response = [(truth[row], Fraction(1))]
                elif model == "fixed3":
                    response = [(truth[row] - 1, Fraction(1, 4)), (truth[row], Fraction(1, 2)), (truth[row] + 1, Fraction(1, 4))]
                else:
                    response = smear_weights(centers[row], width)
                audit.eq(kernel["absolute_channels"], [ch for ch, _ in response], "Analytic response channels")
                audit.eq([fraction(w) for w in kernel["exact_weights"]], [w for _, w in response], "Analytic exact response weights")
                converted = [float(w) for _, w in response]
                total = math.fsum(converted)
                normalized = [w / total for w in converted]
                audit.close(kernel["weights"], normalized, "Normalized response weights", 0.0)
                audit.close(kernel["prenormal_sum"], total, "Float weight pre-normal mass", 0.0)
                audit.eq(kernel["negative_clipped_count"], 0, "No negative analytic response masses")
                require(all(w > 0 for w in normalized) and abs(math.fsum(normalized) - 1) <= 1e-15, "Kernel normalization invalid")
                core_lo, core_hi = g["normalization_core_interval_half_open"]
                channels = kernel["absolute_channels"]
                classification = "CORE_OVERLAP" if any(core_lo <= ch < core_hi for ch in channels) else "HALO_ONLY" if any(core_lo - 250 <= ch < core_hi + 250 for ch in channels) else "OUTSIDE_NORMALIZATION_SUPPORT"
                audit.eq(kernel["normalization_support_class"], classification, "Independent core/halo/outside kernel class")
                classes[model][classification] += 1
            windows, rows, channels, blocked = path_geometry(family, host)
            ideal = reference_flux_capture(rows, channels, kernels)
            ti = next(i for i, (rr, cc) in enumerate(zip(rows, channels)) if list(rr) == active and list(cc) == g["truth_active4"])
            audit.close(g["models"][model]["central4_ideal_deposited_fraction"], ideal[ti], "Metadata ideal central path fraction")
            audit.close(g["models"][model]["frozen_family_oracle_ideal_deposited_fraction"], ideal[~blocked].max(), "Metadata ideal family oracle fraction")
    audit.eq(len(seen), 108, "Raw distinct geometry count")
    audit.eq({model: dict(counts) for model, counts in classes.items()}, manifest["counts"]["kernel_row_normalization_support_classes"], "Full core/halo/outside row census")
    return {"unique_profile_placements": len(seen), "unique_physical_placements": len(physical),
            "integration_sweep_width_min_max": [min(sweep_widths), max(sweep_widths)],
            "kernel_row_normalization_support_classes": {model: dict(counts) for model, counts in classes.items()},
            "fresh_observing_background": False}


def boolean(value):
    require(value in (True, False, "True", "False"), "Invalid CSV boolean")
    return value in (True, "True")


def check_rank(record, scores, windows, rows, channels, blocked, g, audit):
    ranked, overlaps, ti, rank_min, rank_max, deterministic = ranked_truth(
        scores, windows, rows, channels, blocked, g["true_active_source_rows"], g["truth_active4"])
    winner = ranked[0]; partial = next(i for i in ranked if overlaps[i] < 4)
    integers = {"truth_path_index": ti, "truth_path_count": 1, "truth_rank_min": rank_min,
                "truth_rank_max": rank_max, "truth_rank_tie_count": rank_max - rank_min + 1,
                "truth_deterministic_rank": deterministic, "winner_path_index": winner,
                "winner_window_index": int(windows[winner]), "winner_matching_central_truth_cells": overlaps[winner],
                "best_partial_path_index": partial, "retained_count_top1": 1, "retained_count_top5": 5,
                "eligible_unique_hypotheses": len(ranked)}
    for field, value in integers.items():
        audit.eq(int(record[field]), value, "Operational raw rank " + field)
    floats = {"truth_score": scores[ti], "winner_score": scores[winner],
              "winner_minus_truth_score": scores[winner] - scores[ti], "best_partial_score": scores[partial],
              "truth_minus_best_partial_score": scores[ti] - scores[partial]}
    for field, value in floats.items():
        audit.close(float(record[field]), value, "Raw rank score " + field)
    audit.eq(boolean(record["truth_retained_top1"]), deterministic <= 1, "Deterministic k1 central identity")
    audit.eq(boolean(record["truth_retained_top5"]), deterministic <= 5, "Deterministic k5 central identity")
    audit.eq(json.loads(record["retained_top5_indices"]), ranked[:5], "Actual top5 raw identities")
    audit.eq(json.loads(record["retained_top5_central_truth_matches"]), [overlaps[i] for i in ranked[:5]], "Top5 central overlaps")
    audit.close(json.loads(record["retained_top5_scores"]), scores[ranked[:5]], "Actual top5 raw scores")
    return ranked, overlaps, ti, deterministic


def min_med_max(values):
    values = sorted(values)
    return [values[0], statistics.median(values), values[-1]]


def check_common(record, g, audit):
    for field in ("geometry_id", "profile_id", "origin_scan_id", "context_scan_id"):
        audit.eq(record[field], g[field], "Raw trial identity " + field)
    for field in ("origin_rank", "host_offset_channels", "true_window_index", "central_bins_in_core"):
        audit.eq(int(record[field]), int(g[field]), "Raw trial identity " + field)
    for field in ("true_active_source_rows", "truth_active4"):
        audit.eq(json.loads(record[field]), g[field], "Raw trial identity " + field)
    label = "ALL_CENTRAL_IN_CORE" if g["central_bins_in_core"] == 4 else "ALL_CENTRAL_OUTSIDE_CORE" if g["central_bins_in_core"] == 0 else "MIXED"
    audit.eq(record["central_truth_core_class"], label, "Canonical central core stratum")
    return label


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_root", type=Path); ap.add_argument("stage_root", type=Path)
    ap.add_argument("--go-scope-sha256", required=True)
    ap.add_argument("--prior-placement-manifest", type=Path)
    args = ap.parse_args()
    cpu0 = time.process_time(); wall0 = time.monotonic()
    root = args.input_root.resolve(); stage = args.stage_root.resolve(); out = stage / "results"
    scope_path = stage / "SCOPE.json"; scope = read_json(scope_path); go = read_json(stage / "GO.json")
    require(digest(scope_path) == args.go_scope_sha256 == go["scope_sha256"], "Frozen scope GO differs")
    require(digest(Path(__file__).resolve()) == go["qa_sha256"], "Frozen QA GO differs")
    require(digest(stage / "producer.py") == go["producer_sha256"] == scope["producer_pin"]["sha256"], "Frozen producer GO differs")
    budget = scope["resource_envelope"]
    resource.setrlimit(resource.RLIMIT_CPU, (budget["QA_CPU_s_cap"], budget["QA_CPU_s_cap"]))
    resource.setrlimit(resource.RLIMIT_AS, (budget["memory_bytes_cap_each"], budget["memory_bytes_cap_each"]))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("Raw QA wall cap exceeded")))
    signal.alarm(budget["wall_s_cap_each"])
    audit = Audit()
    for pin in scope["input_pins"]:
        path = root / pin["path"]
        audit.eq(path.stat().st_size, pin["bytes"], "Source pinned length")
        audit.eq(digest(path), pin["sha256"], "Source pinned hash")
    manifest_path = stage / scope["geometry_manifest_pin"]["path"]
    audit.eq(digest(manifest_path), scope["geometry_manifest_pin"]["sha256"], "Manifest scope pin")
    audit.eq(digest(manifest_path), go["metadata_manifest_sha256"], "Manifest GO pin")
    original_generator = stage / scope["original_generator_pin"]["path"]
    audit.eq(digest(original_generator), scope["original_generator_pin"]["sha256"], "Historical idealized generator provenance")
    manifest = read_json(manifest_path)
    matrix = read_json(root / "seti_work/seti_burst_full/context_results/CONTEXT_PROFILES.json")
    families = {p["profile_id"]: p for p in read_json(root / "rounding_followup/exact_geometry_results/GEOMETRY.json")["profiles"]}
    novelty = metadata_check(manifest, families, audit)
    receipt = read_json(out / "EXECUTION_RECEIPT.json")
    audit.eq(receipt["status"], "COMPLETE", "Producer complete before QA")
    audit.eq(receipt["scope_sha256"], digest(scope_path), "Producer scope receipt")
    audit.eq(receipt["producer_sha256"], go["producer_sha256"], "Producer code receipt")
    audit.eq(receipt["effective_input_root"], str(root), "Producer effective raw source")
    for pin in receipt["outputs"]:
        path = out / pin["path"]
        audit.eq(path.stat().st_size, pin["bytes"], "Result pinned length")
        audit.eq(digest(path), pin["sha256"], "Result pinned hash")
    case_records = {r["case_id"]: r for r in csv_rows(out / "TRIAL_RANKS.csv")}
    baseline_records = {r["geometry_id"]: r for r in csv_rows(out / "BASELINE_RANKS.csv")}
    norm_records = {(r["case_id"], int(r["source_row"])): r for r in csv_rows(out / "NORMALIZATION_DELTA.csv")}
    retained_records = {(r["case_id"], int(r["rank"])): r for r in csv_rows(out / "RETAINED_HYPOTHESES.csv")}
    case_meta = {r["case_id"]: r for r in read_json(out / "CASE_ARRAYS.json")["cases"]}
    baseline_meta = {r["profile_id"]: r for r in read_json(out / "BASELINE_ARRAYS.json")["profiles"]}
    audit.eq(len(case_records), 648, "Raw case count")
    audit.eq(len(baseline_records), 108, "Unique baseline count")
    audit.eq(len(norm_records), 2592, "Refitted row count")
    audit.eq(len(retained_records), 3240, "Retained workload count")
    audit.eq(len(case_meta), 648, "Case array metadata count")
    audit.eq(len(baseline_meta), 54, "Baseline array metadata count")
    grouped = defaultdict(list)
    for g in manifest["geometries"]: grouped[g["profile_id"]].append(g)
    panels = defaultdict(lambda: {"cases": 0, "top1": 0, "top5": 0, "additional": 0, "ranks": Counter(),
                                  "uplifts": [], "refit_deltas": [], "frozen_errors": [],
                                  "flux_central": [], "flux_oracle": [], "flux_rank1": [], "flux_top5": [],
                                  "strata": defaultdict(lambda: {"cases": 0, "top1": 0, "top5": 0, "uplifts": [], "refit_deltas": []})})
    base_capture = Counter(); norm_core_cells = Counter(); raw_cells = set()
    old_cells = set()
    old_trial_path = root / "rounding_followup/results/INJECTIONS.json"
    audit.eq(digest(old_trial_path), "aeffd0a53ef0b2b4aab69e2829af9ef76dac1cf5223062fe2e12c32d42bf5a16", "Authenticated old512 placement bank")
    old_trials = read_json(old_trial_path)["trials"]
    for trial in old_trials:
        for field in ("canonical_float_truth_absolute_centers", "canonical_rational_truth_absolute_centers"):
            old_cells.update((trial["context_scan_id"], int(r), int(trial[field][r])) for r in trial["true_active_source_rows"])
    previous_manifest = args.prior_placement_manifest or stage / scope["prior_placement_manifest_pin"]["path"]
    require(previous_manifest.is_file(), "Prior placement manifest required for source-cell novelty")
    audit.eq(digest(previous_manifest), "106b0bffba727c95cd6fa9bb1c7217ec1e23ed8b0476716184192fa0c1c73297", "Frozen prior placement manifest")
    audit.eq(digest(previous_manifest), scope["prior_placement_manifest_pin"]["sha256"], "Scope prior placement manifest pin")
    for g in read_json(previous_manifest)["geometries"]:
        old_cells.update((g["context_scan_id"], int(r), int(ch)) for r, ch in zip(g["true_active_source_rows"], g["truth_active4"]))
    checked_path_scores = 0; checked_raw_arrays = 0
    for pi, profile in enumerate(matrix["profiles"]):
        pid = profile["profile_id"]; family = families[pid]
        source_path = root / "seti_work" / profile["raw_normalization_crop"]["path"]
        with np.load(source_path, allow_pickle=False) as z:
            raw = z["raw_power"]; channel0 = int(z["source_channel0"])
            require(raw.shape == (16, 12096) and raw.dtype == np.dtype("<f4") and np.isfinite(raw).all() and (raw >= 0).all(), "Raw source contract differs")
            audit.eq(z["absolute_time_rows"].tolist(), list(range(16)), "Raw source row coordinates")
            audit.eq(z["normalization_source_channels"].tolist(), list(range(channel0 + 4000, channel0 + 8096)), "Raw normalization coordinates")
        raw_hash = raw_digest(raw); checked_raw_arrays += 1
        saved = read_json(root / "seti_work" / profile["normalization"]["path"])
        saved_normal = np.asarray([saved[k] for k in NORMAL_FIELDS], dtype=np.float64)
        audit.eq(saved["normalization_unmasked_counts"], [4096] * 16, "Fixed full-core normalization counts")
        geometry = {host: path_geometry(family, host) for host in (-640, 640)}
        requested = defaultdict(set)
        for _, rows, channels, _ in geometry.values():
            for rr, cc in zip(rows, channels):
                for r, ch in zip(rr, cc): requested[int(r)].add(int(ch) - channel0)
        recomputed = np.empty((4, 16), dtype=np.float64); medians = {}
        for r in range(16): recomputed[:, r], medians[r] = normalize_row(raw[r], requested[r])
        audit.close(recomputed[0], saved_normal[0], "Baseline original power median", 0.0)
        audit.close(recomputed[1:], saved_normal[1:], "Baseline full-core normalization")
        normal = recomputed.copy()
        bm = baseline_meta.pop(pid)
        audit.eq(bm["raw_source_power_bytes_sha256"], raw_hash, "Whole original raw array hash")
        with np.load(out / bm["arrays"]["path"], allow_pickle=False) as z:
            audit.eq(z["offset_channels"].tolist(), [-640, 640], "Baseline offset ordering")
            for j, k in enumerate(NORMAL_FIELDS):
                audit.close(z[k], normal[j], "Baseline independently refitted operational normalization")
                audit.close(z["saved_" + k], saved_normal[j], "Baseline saved amplitude-reference normalization", 0.0)
            baselines = {}
            for oi, host in enumerate((-640, 640)):
                windows, rows, channels, blocked = geometry[host]
                audit.eq(z["absolute_channels"][oi].tolist(), channels.tolist(), "Baseline native geometry")
                audit.eq(z["path_source_rows"].tolist(), rows.tolist(), "Baseline path rows")
                audit.eq(z["path_window_index"].tolist(), windows.tolist(), "Baseline path windows")
                audit.eq(z["path_dc_mask"][oi].tolist(), blocked.tolist(), "Baseline DC mask")
                terms = terms_for_paths(raw, channel0, rows, channels, normal, medians)
                scores = terms.sum(axis=1, dtype=np.float64) / 2
                audit.close(z["residual_row_terms"][oi], terms, "Baseline raw median501 row terms")
                audit.close(z["scores"][oi], scores, "Baseline raw path scores")
                checked_path_scores += len(scores)
                baselines[host] = (terms, scores)
        for g in grouped[pid]:
            gid = g["geometry_id"]; host = int(g["host_offset_channels"]); active = g["true_active_source_rows"]
            windows, rows, channels, blocked = geometry[host]; base_terms, base_scores = baselines[host]
            br = baseline_records.pop(gid)
            central_core_label = check_common(br, g, audit)
            _, _, ti, base_rank = check_rank(br, base_scores, windows, rows, channels, blocked, g, audit)
            audit.eq(boolean(br["sham_target_only"]), True, "Baseline sham interpretation")
            base_capture["k1"] += base_rank <= 1; base_capture["k5"] += base_rank <= 5
            for model in ("delta", "fixed3", "integration_smear"):
                kernels = g["models"][model]["row_kernels"]
                support_classes = Counter(k["normalization_support_class"] for k in kernels)
                support_label = next(iter(support_classes)) if len(support_classes) == 1 else "MIXED"
                ideal = reference_flux_capture(rows, channels, kernels)
                oracle = float(ideal[~blocked].max())
                for kernel in kernels:
                    r = int(kernel["source_row"])
                    for ch in kernel["absolute_channels"]:
                        raw_cells.add((g["context_scan_id"], r, int(ch)))
                        norm_core_cells["inside" if 4000 <= int(ch) - channel0 < 8096 else "outside"] += 1
                for amp in (2, 8):
                    cid = gid + "_" + model + "_A" + str(amp)
                    record = case_records.pop(cid); cm = case_meta.pop(cid)
                    check_common(record, g, audit)
                    audit.eq(record["kernel_normalization_support_stratum"], support_label, "Raw kernel support stratum")
                    for field, label in (("kernel_core_overlap_rows", "CORE_OVERLAP"), ("kernel_halo_only_rows", "HALO_ONLY"),
                                         ("kernel_outside_normalization_support_rows", "OUTSIDE_NORMALIZATION_SUPPORT")):
                        audit.eq(int(record[field]), support_classes[label], "Kernel normalization support row counts")
                    modified = raw.copy(); injected = []
                    for kernel in kernels:
                        r = int(kernel["source_row"]); absolute = kernel["absolute_channels"]
                        local = np.asarray(absolute, dtype=np.int64) - channel0
                        require(local.min() >= 0 and local.max() < 12096, "Raw injection kernel support unavailable")
                        weights = np.asarray(kernel["weights"], dtype=np.float64)
                        power = amp * float(saved_normal[0, r]) * float(saved_normal[2, r]) * weights
                        before = raw[r, local].astype(np.float64)
                        modified[r, local] = (before + power).astype("<f4")
                        injected.append((r, absolute, power, modified[r, local].astype(np.float64) - before))
                    unchanged = [r for r in range(16) if r not in active]
                    require(np.array_equal(modified[unchanged], raw[unchanged]), "Other12 raw rows changed")
                    modified_hash = raw_digest(modified)
                    audit.eq(record["raw_modified_power_bytes_sha256"], modified_hash, "Case whole raw float32 byte hash")
                    audit.eq(cm["raw_modified_power_bytes_sha256"], modified_hash, "Case metadata raw byte hash")
                    audit.eq(cm["raw_source_power_bytes_sha256"], raw_hash, "Case original raw byte hash")
                    audit.eq(len(cm["injected_cells"]), 4, "Four injected raw rows")
                    for actual, expected in zip(cm["injected_cells"], injected):
                        r, absolute, power, deposited = expected
                        audit.eq(actual["source_row"], r, "Injected source row")
                        audit.eq(actual["absolute_channels"], absolute, "Injected absolute channels")
                        audit.close(actual["requested_power_increment"], power, "Requested raw power increments", 0.0)
                        audit.close(actual["actual_float32_power_increment"], deposited, "Quantized float32 raw power increments", 0.0)
                    case_normal = normal.copy(); case_medians = dict(medians)
                    for r in active:
                        extras = channels[rows == r] - channel0
                        case_normal[:, r], case_medians[r] = normalize_row(modified[r], extras)
                        nr = norm_records.pop((cid, r))
                        kernel = next(k for k in kernels if k["source_row"] == r)
                        audit.eq(nr["normalization_support_class"], kernel["normalization_support_class"], "Refitted row core/halo/outside class")
                        lo, hi = g["normalization_core_interval_half_open"]
                        core_fraction = math.fsum(w for ch, w in zip(kernel["absolute_channels"], kernel["weights"]) if lo <= ch < hi)
                        halo_fraction = math.fsum(w for ch, w in zip(kernel["absolute_channels"], kernel["weights"]) if lo - 250 <= ch < hi + 250)
                        audit.close(float(nr["reference_fraction_power_in_core"]), core_fraction, "Refitted row ideal mass in core")
                        audit.close(float(nr["reference_fraction_power_in_core_halo"]), halo_fraction, "Refitted row ideal mass in filter halo")
                        for j, k in enumerate(NORMAL_FIELDS):
                            audit.close(float(nr[k + "_before"]), normal[j, r], "Changed row normalization before", 0.0)
                            audit.close(float(nr[k + "_after"]), case_normal[j, r], "Changed row normalization after")
                            audit.close(float(nr[k + "_delta"]), case_normal[j, r] - normal[j, r], "Changed row normalization delta")
                    require(np.array_equal(case_normal[:, unchanged], normal[:, unchanged]), "Other12 saved normalization rows changed")
                    terms = terms_for_paths(modified, channel0, rows, channels, case_normal, case_medians)
                    scores = terms.sum(axis=1, dtype=np.float64) / 2
                    frozen_terms = terms_for_paths(modified, channel0, rows[ti:ti + 1], channels[ti:ti + 1], normal, case_medians)[0]
                    baseline_truth = base_terms[ti]; refit_truth = terms[ti]
                    central_weights = [next((w for ch, w in zip(k["absolute_channels"], k["weights"]) if ch == g["truth_active4"][j]), 0.0) for j, k in enumerate(kernels)]
                    requested_response = amp * np.asarray(central_weights, dtype=np.float64)
                    frozen_response = frozen_terms - baseline_truth; refit_response = refit_truth - baseline_truth
                    refit_delta = refit_truth - frozen_terms
                    with np.load(out / cm["arrays"]["path"], allow_pickle=False) as z:
                        audit.eq(z["absolute_channels"].tolist(), channels.tolist(), "Case native path geometry")
                        audit.eq(z["path_source_rows"].tolist(), rows.tolist(), "Case source path rows")
                        audit.eq(z["path_window_index"].tolist(), windows.tolist(), "Case path windows")
                        audit.eq(z["path_dc_mask"].tolist(), blocked.tolist(), "Case native DC mask")
                        for j, k in enumerate(NORMAL_FIELDS):
                            audit.close(z[k], case_normal[j], "Case all16 normalization fields")
                            audit.close(z[k][unchanged], normal[j, unchanged], "Case other12 baseline normalization rows", 0.0)
                        audit.close(z["residual_row_terms"], terms, "Case raw median501 refitted row terms")
                        audit.close(z["scores"], scores, "Case allpath scores")
                        for field, expected in (("baseline_truth_row_terms", baseline_truth), ("frozen_normal_truth_row_terms", frozen_terms),
                                                ("refit_truth_row_terms", refit_truth), ("requested_central_response", requested_response),
                                                ("reference_weight_capture_fraction", ideal)):
                            audit.close(z[field], expected, "Case " + field)
                    checked_path_scores += len(scores)
                    ranked, overlaps, case_ti, rank = check_rank(record, scores, windows, rows, channels, blocked, g, audit)
                    audit.eq(case_ti, ti, "Fixed canonical central identity")
                    floats = {"baseline_truth_score": base_scores[ti], "truth_score_uplift": scores[ti] - base_scores[ti],
                              "truth_score_frozen_normalization": frozen_terms.sum() / 2,
                              "truth_score_refit_minus_frozen": refit_delta.sum() / 2,
                              "central_response_frozen_minus_requested_max_abs": np.abs(frozen_response - requested_response).max(),
                              "central_response_refit_minus_frozen_max_abs": np.abs(refit_delta).max(),
                              "reference_total_power_fraction_central_path": ideal[ti], "reference_total_power_fraction_oracle": oracle,
                              "reference_total_power_fraction_rank1": ideal[ranked[0]],
                              "reference_total_power_fraction_best_top5": ideal[ranked[:5]].max()}
                    for field, expected in floats.items(): audit.close(float(record[field]), expected, "Case diagnostic " + field)
                    for field, expected in (("requested_central_standardized_response", requested_response),
                                            ("actual_frozen_central_standardized_response", frozen_response),
                                            ("actual_refit_central_standardized_response", refit_response)):
                        audit.close(json.loads(record[field]), expected, "Case response " + field)
                    audit.eq(int(record["baseline_truth_deterministic_rank"]), base_rank, "Paired baseline rank")
                    audit.eq(boolean(record["baseline_truth_retained_top1"]), base_rank <= 1, "Paired baseline k1")
                    audit.eq(boolean(record["baseline_truth_retained_top5"]), base_rank <= 5, "Paired baseline k5")
                    for retained_rank, index in enumerate(ranked[:5], 1):
                        rr = retained_records.pop((cid, retained_rank))
                        audit.eq(int(rr["path_index"]), index, "Retained raw hypothesis index")
                        audit.eq(int(rr["window_index"]), int(windows[index]), "Retained raw window")
                        audit.eq(json.loads(rr["source_rows"]), rows[index].tolist(), "Retained raw rows")
                        audit.eq(json.loads(rr["native4"]), channels[index].tolist(), "Retained raw native bins")
                        audit.close(float(rr["score"]), scores[index], "Retained raw score")
                        audit.eq(int(rr["matched_central_truth_cells"]), overlaps[index], "Retained central overlap")
                        audit.eq(boolean(rr["complete_central_truth"]), overlaps[index] == 4, "Retained central identity")
                    p = panels[(model, amp)]
                    p["cases"] += 1; p["top1"] += rank <= 1; p["top5"] += rank <= 5; p["additional"] += 1 < rank <= 5
                    p["ranks"][rank] += 1; p["uplifts"].append(float(scores[ti] - base_scores[ti]))
                    p["refit_deltas"].append(float(refit_delta.sum() / 2)); p["frozen_errors"].append(float(np.abs(frozen_response - requested_response).max()))
                    p["flux_central"].append(float(ideal[ti])); p["flux_oracle"].append(oracle)
                    p["flux_rank1"].append(float(ideal[ranked[0]])); p["flux_top5"].append(float(ideal[ranked[:5]].max()))
                    for name, label in (("by_central_truth_core_class", central_core_label), ("by_kernel_normalization_support_stratum", support_label)):
                        sp = p["strata"][(name, label)]
                        sp["cases"] += 1; sp["top1"] += rank <= 1; sp["top5"] += rank <= 5
                        sp["uplifts"].append(float(scores[ti] - base_scores[ti])); sp["refit_deltas"].append(float(refit_delta.sum() / 2))
        print(json.dumps({"QA_profiles_complete": pi + 1, "CPU_s": time.process_time() - cpu0, "checks": audit.checks}), flush=True)
    require(not case_records and not baseline_records and not norm_records and not retained_records and not case_meta and not baseline_meta, "Unaudited result records remain")
    overlap = len(raw_cells & old_cells)
    audit.eq(overlap, 0, "Kernel source cells novel against both prior injection banks")
    novelty["prior_kernel_source_cell_overlap"] = overlap
    novelty["distinct_new_kernel_source_cells"] = len(raw_cells)
    novelty["declared_kernel_cells_inside_outside_normalization_core"] = dict(norm_core_cells)
    summary = read_json(out / "SUMMARY.json")
    for (model, amp), p in panels.items():
        s = summary["models"][model][str(amp)]
        for field, expected in (("cases", p["cases"]), ("top1_complete_central_truth", p["top1"]),
                                ("top5_complete_central_truth", p["top5"]), ("additional_top5_complete_central_truth", p["additional"]),
                                ("top5_missing_central_truth", p["cases"] - p["top5"])):
            audit.eq(s[field], expected, "Model raw retention aggregate")
        audit.eq(s["deterministic_truth_rank_counts"], {str(k): v for k, v in p["ranks"].items()}, "Model raw rank histogram")
        audit.close(s["truth_score_uplift_min_median_max"], min_med_max(p["uplifts"]), "Raw uplift summary")
        audit.close(s["refit_minus_frozen_truth_score_min_median_max"], min_med_max(p["refit_deltas"]), "Normalization refit summary")
        audit.close(s["central_frozen_minus_requested_max_abs"], max(p["frozen_errors"]), "Frozen central response summary")
        for field, values in (("reference_total_power_fraction_oracle_min_median_max", p["flux_oracle"]),
                              ("reference_total_power_fraction_rank1_min_median_max", p["flux_rank1"]),
                              ("reference_total_power_fraction_best_top5_min_median_max", p["flux_top5"])):
            audit.close(s[field], min_med_max(values), "Ideal flux capture summary")
        for (name, label), sp in p["strata"].items():
            sub = s[name][label]
            for field, expected in (("cases", sp["cases"]), ("top1_complete_central_truth", sp["top1"]), ("top5_complete_central_truth", sp["top5"])):
                audit.eq(sub[field], expected, "Conditional core/halo/outside subgroup counts")
            audit.close(sub["truth_score_uplift_min_median_max"], min_med_max(sp["uplifts"]), "Subgroup raw uplift summary")
            audit.close(sub["refit_minus_frozen_truth_score_min_median_max"], min_med_max(sp["refit_deltas"]), "Subgroup normalization refit summary")
    audit.eq(summary["A0_baseline_sham_target"]["top1_count"], base_capture["k1"], "Unique sham k1 count")
    audit.eq(summary["A0_baseline_sham_target"]["top5_count"], base_capture["k5"], "Unique sham k5 count")
    for field, expected in (("positive_case_top1_slots", 648), ("positive_case_top5_slots", 3240),
                            ("baseline_unique_top1_slots", 108), ("baseline_unique_top5_slots", 540), ("ratio", 5)):
        audit.eq(summary["candidate_workload"][field], expected, "Frozen k5 workload " + field)
    for field, expected in (("qualified_SETI_detection", False), ("calibrated_FAP", False), ("physical_sensitivity_established", False),
                            ("original_A_B", "FAIL_CLOSED"), ("full6scan_chain_gate_pass", False), ("new_observation", False),
                            ("new_telescope_requests", 0), ("new_telescope_bytes", 0), ("raw_spectral_arrays_opened", 54)):
        audit.eq(summary[field], expected, "Raw control interpretation " + field)
    usage = {"CPU_s": time.process_time() - cpu0, "wall_s": time.monotonic() - wall0,
             "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    require(usage["CPU_s"] <= budget["QA_CPU_s_cap"] and usage["wall_s"] <= budget["wall_s_cap_each"]
            and usage["peak_RSS_bytes"] <= budget["memory_bytes_cap_each"], "Raw QA budget exceeded")
    result = {"schema": "SETI_RAW_RETENTION_INDEPENDENT_QA_V1", "status": "PASS_INDEPENDENT_RAW_HASH_RESPONSE_NORMALIZATION_MEDIAN501_SCORE_RANK",
              "scope_sha256": digest(scope_path), "qa_sha256": digest(Path(__file__).resolve()), "producer_sha256": go["producer_sha256"],
              "profiles": checked_raw_arrays, "raw_cases": 648, "checked_path_scores": checked_path_scores,
              "checks": audit.checks, "maximum_absolute_errors": dict(audit.max_error), "independent_novelty": novelty,
              "canonical_central_path_retention": {model: {str(amp): {"cases": panels[(model, amp)]["cases"],
                  "k1": panels[(model, amp)]["top1"], "k5": panels[(model, amp)]["top5"]} for amp in (2, 8)} for model in ("delta", "fixed3", "integration_smear")},
              "unique_A0_sham_retention": dict(base_capture), "resource_usage": usage,
              "qualified_SETI_detection": False, "calibrated_FAP": False, "physical_sensitivity_established": False,
              "full6scan_chain_gate_pass": False, "new_observation": False}
    with (out / "QA_RECEIPT.json").open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True, allow_nan=False); f.write("\n")
    signal.alarm(0)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
