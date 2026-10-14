#!/usr/bin/env python3
"""Independent bounded audit of frozen retained-native-path controls.

No producer module is imported. Every injected score is rebuilt by matching
four active (source row, native channel) cells to each saved eligible path.
The saved four-row terms authenticate base score arithmetic. Exact ranks use
the authenticated saved base sums, so the audit does not change floating
rounding or the producer's declared deterministic tie rule.
"""
from __future__ import annotations

import argparse
import csv
from fractions import Fraction
import hashlib
import json
import math
import os
import resource
import signal
import time
from collections import Counter, defaultdict
from pathlib import Path

for thread_var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[thread_var] = "1"
import numpy as np


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


def load_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def as_bool(value):
    require(value in (True, False, "True", "False", "true", "false", "1", "0"),
            f"Invalid bool {value!r}")
    return value in (True, "True", "true", "1")


def nearest_even(value):
    lower = value.numerator // value.denominator
    residue = value - lower
    if residue < Fraction(1, 2):
        return lower
    if residue > Fraction(1, 2):
        return lower + 1
    return lower + (lower % 2)


def canonical_centers(profile, host, drift_fraction, phase):
    base = Fraction(profile["source_reference_channel"] + int(host))
    drift = Fraction(profile["original_drift_hz_s"]) + Fraction(4 / 158) * drift_fraction
    df = Fraction(-2.7939677238464355)
    return [nearest_even(base + phase + drift * Fraction(t) / df)
            for t in profile["times_from_primary_reference_s"]]


class Auditor:
    def __init__(self):
        self.checks = 0
        self.max_score_error = 0.0

    def eq(self, got, expected, context):
        require(got == expected, f"{context}: {got!r} != {expected!r}")
        self.checks += 1

    def close(self, got, expected, context, tolerance=1e-12):
        got = float(got); expected = float(expected)
        error = abs(got - expected)
        require(math.isfinite(got) and math.isfinite(expected) and error <= tolerance,
                f"{context}: {got!r} != {expected!r} (error {error})")
        self.max_score_error = max(self.max_score_error, error)
        self.checks += 1


def rebuild_paths(npz_path, offsets, family, audit):
    """Authenticate all base arrays, return ordinary-Python eligible paths."""
    with np.load(npz_path, allow_pickle=False) as z:
        source_rows = z["path_source_rows"].tolist()
        window_index = z["path_window_index"].tolist()
        hosts = z["offset_channels"].tolist()
        results = {}
        for host in offsets:
            require(host in hosts, f"Host absent: {host}")
            oi = hosts.index(host)
            absolute = z["absolute_channels"][oi].tolist()
            blocked = z["path_dc_mask"][oi].tolist()
            row_blocked = z["row_dc_mask"][oi].tolist()
            terms = z["residual_row_terms"][oi].tolist()
            scores = z["scores"][oi].tolist()
            records = []
            unique = set()
            expected = [(w["window_index"], tuple(w["window_source_rows"]),
                         tuple(ch + host for ch in p["channels"]))
                        for w in family["windows"] for p in w["paths"]]
            audit.eq(len(source_rows), len(expected), "Frozen geometry path count")
            for i, (rows, wi, bins, masked, masks, values, saved) in enumerate(zip(
                    source_rows, window_index, absolute, blocked, row_blocked, terms, scores)):
                audit.eq((wi, tuple(rows), tuple(bins)), expected[i], "Saved path geometry identity")
                audit.eq(rows, list(range(2 * wi, 2 * wi + 4)), "Window source rows")
                audit.eq(masks, [ch in (178782208, 179830784, 180879360) for ch in bins],
                         "Native frozen DC contacts")
                audit.eq(masked, any(masks), "Saved path DC mask")
                audit.close(saved, math.fsum(values) / 2, "Saved base score versus four row terms")
                identity = (2 * wi, tuple(bins))
                require(identity not in unique, "Duplicate native-bin hypothesis")
                unique.add(identity)
                if not masked:
                    records.append({"index": i, "window_index": wi, "window_start": 2 * wi,
                                    "rows": tuple(rows), "bins": tuple(bins), "base": saved})
            require(records, "No eligible native-bin hypotheses")
            results[host] = records
        return results


def score_trial(records, active_rows, active_bins, amplitude):
    truth_cells = dict(zip(active_rows, active_bins))
    scored = []
    for p in records:
        hits = sum(truth_cells.get(r) == ch for r, ch in zip(p["rows"], p["bins"]))
        score = p["base"] + float(amplitude) * hits / 2.0
        scored.append({**p, "overlap": hits, "score": score})
    scored.sort(key=lambda p: (-p["score"], p["window_start"], p["bins"]))
    truth = [p for p in scored if p["overlap"] == 4]
    require(truth, "No eligible complete truth path")
    best = truth[0]
    higher = sum(p["score"] > best["score"] for p in scored)
    equal = sum(p["score"] == best["score"] for p in scored)
    deterministic_rank = next(i + 1 for i, p in enumerate(scored) if p["overlap"] == 4)
    partial = next(p for p in scored if p["overlap"] < 4)
    return scored, truth, best, higher + 1, higher + equal, equal, deterministic_rank, partial


def check_metadata(source_root, manifest, audit):
    """Rebuild exact draws, alias grouping and the two novelty definitions."""
    for pin in manifest["input_pins"]:
        p = source_root / pin["path"]
        audit.eq(p.stat().st_size, pin["bytes"], "Metadata pinned length")
        audit.eq(digest(p), pin["sha256"], "Metadata pinned hash")
    family = read_json(source_root / "rounding_followup/exact_geometry_results/GEOMETRY.json")
    profiles = {p["profile_id"]: p for p in family["profiles"]}
    old = read_json(source_root / "rounding_followup/results/INJECTIONS.json")["trials"]
    old_relative = set()
    old_absolute = set()
    old_physical = set()
    for t in old:
        pid = t["profile_id"]
        rows = tuple(t["true_active_source_rows"])
        for field in ("canonical_float_truth_absolute_centers", "canonical_rational_truth_absolute_centers"):
            bins = tuple(t[field][r] for r in rows)
            old_absolute.add((pid, rows, bins))
            old_relative.add((pid, rows, tuple(ch - 512 for ch in bins)))
            old_physical.add((t["context_scan_id"], rows, bins))
    expected = defaultdict(list)
    fractions = [Fraction(-83, 100), Fraction(47, 100)]
    phases = [Fraction(-41, 100), Fraction(13, 100)]
    all_draws = 0
    for pid in sorted(profiles):
        p = profiles[pid]
        for host in (-768, 768):
            for wi in range(7):
                rows = tuple(range(2 * wi, 2 * wi + 4))
                for fraction in fractions:
                    for phase in phases:
                        bins16 = canonical_centers(p, host, fraction, phase)
                        bins4 = tuple(bins16[r] for r in rows)
                        key = (pid, host, rows, bins4)
                        expected[key].append((fraction, phase, bins16))
                        all_draws += 1
    audit.eq(all_draws, manifest["counts"]["nominal_geometry_draws"], "Draw census")
    audit.eq(len(expected), manifest["counts"]["unique_geometry_placements"], "Deduplicated census")
    seen = set()
    old_native4 = 0
    absolute_collisions = 0
    new_physical = Counter()
    for g in manifest["geometries"]:
        pid = g["profile_id"]; host = int(g["host_offset_channels"])
        rows = tuple(g["true_active_source_rows"]); bins = tuple(g["truth_active4"])
        key = (pid, host, rows, bins)
        require(key in expected and key not in seen, "Unexpected/duplicate geometry placement")
        seen.add(key)
        audit.eq(rows, tuple(range(2 * int(g["true_window_index"]), 2 * int(g["true_window_index"]) + 4)),
                 "Truth active source rows")
        audit.eq(tuple(g["native4"]), tuple(ch - host for ch in bins), "Native4 host translation")
        canonical_aliases = {(f, ph, tuple(b16)) for f, ph, b16 in expected[key]}
        supplied_aliases = set()
        for draw in g["draws"]:
            f = Fraction(*map(int, draw["drift_fraction"]))
            ph = Fraction(*map(int, draw["phase_fraction"]))
            bins16 = canonical_centers(profiles[pid], host, f, ph)
            audit.eq(bins16, draw["canonical_truth16"], "Exact draw truth16")
            audit.eq(Fraction(*map(int, draw["delta_drift_fraction"])), Fraction(4 / 158) * f,
                     "Exact drift increment")
            supplied_aliases.add((f, ph, tuple(bins16)))
        audit.eq(supplied_aliases, canonical_aliases, "Geometry alias map")
        audit.eq(len(g["draws"]), len(expected[key]), "Alias count")
        audit.eq(g["alias_draw_count"], len(expected[key]), "Declared alias count")
        audit.eq(g["truth16"], g["draws"][0]["canonical_truth16"], "Representative truth16")
        relative_old = (pid, rows, tuple(ch - host for ch in bins)) in old_relative
        absolute_old = (pid, rows, bins) in old_absolute
        audit.eq(g["native4_seen_in_prior_same_profile_window"], relative_old, "Relative old native4 collision")
        audit.eq(g["canonical_placement_seen_in_prior"], absolute_old, "Absolute old placement collision")
        old_native4 += relative_old
        absolute_collisions += absolute_old
        new_physical[(g["context_scan_id"], rows, bins)] += 1
    audit.eq(seen, set(expected), "Complete unique geometry manifest")
    audit.eq(old_native4, manifest["counts"]["prior_same_window_native4_collisions"], "Old native4 census")
    audit.eq(absolute_collisions, manifest["counts"]["prior_absolute_placement_collisions"], "Old placement census")
    audit.eq(Counter(str(len(v)) for v in expected.values()), Counter(manifest["counts"]["alias_draw_count_histogram"]),
             "Alias histogram")
    return profiles, {g["geometry_id"]: g for g in manifest["geometries"]}, {
        "nominal_geometry_draws": all_draws,
        "unique_geometry_placements": len(expected),
        "duplicate_alias_draws": all_draws - len(expected),
        "relative_native4_old": old_native4,
        "relative_native4_unseen": len(expected) - old_native4,
        "prior_absolute_placement_collisions": absolute_collisions,
        "physical_unique_geometries": len(new_physical),
        "physical_profile_aliases": len(expected) - len(new_physical),
        "prior_unique_physical_geometries": len(old_physical),
        "physical_new_overlap_prior": len(set(new_physical) & old_physical),
        "physical_identity_multiplicity": dict(Counter(str(v) for v in new_physical.values())),
        "context_scans": len({key[0] for key in new_physical}),
        "independent_fresh_visits": 0,
        "fresh_observing_background": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_root", type=Path)
    ap.add_argument("stage_root", type=Path)
    ap.add_argument("--go-scope-sha256", required=True)
    args = ap.parse_args()
    started_cpu = time.process_time(); started_wall = time.monotonic()
    stage = args.stage_root.resolve(); source_root = args.input_root.resolve()
    scope_path = stage / "SCOPE.json"; go_path = stage / "GO.json"
    require(go_path.is_file(), "Root GO absent")
    scope = read_json(scope_path); go = read_json(go_path)
    require(digest(scope_path) == args.go_scope_sha256 == go["scope_sha256"], "Scope GO hash differs")
    require(digest(Path(__file__).resolve()) == go["qa_sha256"], "Frozen QA code differs")
    require(digest(stage / "producer.py") == go["producer_sha256"] == scope["producer_pin"]["sha256"],
            "Frozen producer code differs")
    audit = Auditor()
    budget = scope["resource_envelope"]
    resource.setrlimit(resource.RLIMIT_CPU, (budget["QA_CPU_s_cap"], budget["QA_CPU_s_cap"]))
    resource.setrlimit(resource.RLIMIT_AS, (budget["memory_bytes_cap_each"], budget["memory_bytes_cap_each"]))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("QA wall budget exceeded")))
    signal.alarm(budget["wall_s_cap_each"])
    for pin in scope["input_pins"]:
        path = source_root / pin["path"]
        audit.eq(path.stat().st_size, pin["bytes"], "Frozen source length")
        audit.eq(digest(path), pin["sha256"], "Frozen source hash")
    manifest_path = stage / scope["geometry_manifest_pin"]["path"]
    audit.eq(digest(manifest_path), go["metadata_manifest_sha256"], "GO manifest hash")
    audit.eq(digest(manifest_path), scope["geometry_manifest_pin"]["sha256"], "Scope manifest hash")
    manifest = read_json(manifest_path)
    families, geometries, novelty = check_metadata(source_root, manifest, audit)
    annex_path = stage / scope["physical_novelty_pin"]["path"]
    audit.eq(digest(annex_path), scope["physical_novelty_pin"]["sha256"], "Physical novelty annex hash")
    annex = read_json(annex_path)
    for key in ("physical_unique_geometries", "physical_profile_aliases", "prior_unique_physical_geometries",
                "physical_new_overlap_prior", "physical_identity_multiplicity", "context_scans", "independent_fresh_visits"):
        audit.eq(annex["counts"][key], novelty[key], "Cross-profile physical novelty " + key)
    audit.eq(annex["scores_evaluated"], False, "Physical novelty metadata only")
    audit.eq(annex["spectral_arrays_opened"], False, "Physical novelty no arrays")
    out = stage / "results"
    producer_receipt = read_json(out / "EXECUTION_RECEIPT.json")
    audit.eq(producer_receipt["status"], "COMPLETE", "Producer complete before QA")
    audit.eq(producer_receipt["scope_sha256"], digest(scope_path), "Producer scope hash")
    audit.eq(producer_receipt["producer_sha256"], go["producer_sha256"], "Producer receipt code hash")
    audit.eq(producer_receipt["geometry_manifest_sha256"], digest(manifest_path), "Producer manifest hash")
    audit.eq(producer_receipt["effective_input_root"], str(source_root), "Producer runtime source root")
    for field, expected in (("raw_spectral_arrays_opened", False), ("new_telescope_requests", 0),
                            ("new_telescope_bytes", 0), ("opened_saved_profile_arrays", 54)):
        audit.eq(producer_receipt[field], expected, "Producer execution boundaries " + field)
    for pin in producer_receipt["outputs"]:
        path = out / pin["path"]
        audit.eq(path.stat().st_size, pin["bytes"], "Producer output length")
        audit.eq(digest(path), pin["sha256"], "Producer output hash")
    summary = read_json(out / "SUMMARY.json")
    rows = load_csv(out / "TRIAL_RANKS.csv")
    candidates = load_csv(out / "RETAINED_HYPOTHESES.csv")
    observed = load_csv(out / "OBSERVED_TOP5.csv")
    pairs = load_csv(out / "CANDIDATE_OVERLAP.csv")
    nulls = load_csv(out / "NULL_BURDEN.csv")
    expected_trial_count = len(geometries) * 3
    audit.eq(len(rows), expected_trial_count, "Unique placement-amplitude trial count")
    audit.eq(expected_trial_count, scope["actual_numeric_trial_count"], "Frozen numeric count")
    audit.eq(len(candidates), 5 * expected_trial_count, "Retained table workload")
    audit.eq(len(observed), 270, "Observed candidate table count")
    audit.eq(len(pairs), 540, "Observed pair table count")
    audit.eq(len(nulls), 108, "Unique null-host table count")
    row_map = {}; candidate_map = {}; observed_map = {}; pair_map = {}; null_map = {}
    for row in rows:
        key = (row["geometry_id"], int(row["amplitude"]))
        require(key not in row_map, "Duplicate placement-amplitude row")
        row_map[key] = row
    for row in candidates:
        key = (row["geometry_id"], int(row["amplitude"]), int(row["rank"]))
        require(key not in candidate_map, "Duplicate retained row")
        candidate_map[key] = row
    for row in observed:
        key = (row["profile_id"], int(row["rank"]))
        require(key not in observed_map, "Duplicate observed row")
        observed_map[key] = row
    for row in pairs:
        key = (row["profile_id"], int(row["rank_a"]), int(row["rank_b"]))
        require(key not in pair_map, "Duplicate overlap pair")
        pair_map[key] = row
    for row in nulls:
        key = (row["profile_id"], int(row["host_offset_channels"]))
        require(key not in null_map, "Duplicate unique null profile-host")
        null_map[key] = row
    grouped = defaultdict(list)
    for g in geometries.values():
        grouped[g["profile_id"]].append(g)
    panels = {amp: {"count": 0, "top1": 0, "top5": 0, "additional": 0,
                    "rank_counts": Counter(), "winner_overlaps": Counter(),
                    "breakdown": defaultdict(Counter)} for amp in (0, 2, 8)}
    shared_cells = Counter(); score_recomputed_count = 0
    null_top1_scores = []; null_cut_scores = []
    for pid in sorted(families):
        paths = rebuild_paths(source_root / "rounding_followup/results/profiles" / f"{pid}_paths.npz",
                              (0, -768, 768), families[pid], audit)
        score_recomputed_count += sum(len(v) for v in paths.values())
        base0 = sorted(paths[0], key=lambda p: (-p["base"], p["window_start"], p["bins"]))
        for rank, path in enumerate(base0[:5], 1):
            row = observed_map.pop((pid, rank))
            for field, expected in (("host_offset_channels", 0), ("path_index", path["index"]),
                                    ("window_index", path["window_index"]),
                                    ("eligible_unique_hypotheses", len(base0))):
                audit.eq(int(row[field]), expected, "Observed " + field)
            audit.eq(json.loads(row["source_rows"]), list(path["rows"]), "Observed source rows")
            audit.eq(json.loads(row["native4"]), list(path["bins"]), "Observed native bins")
            audit.close(row["score"], path["base"], "Observed score")
            audit.eq(as_bool(row["new_detection"]), False, "Observed descriptive only")
        for left in range(5):
            for right in range(left + 1, 5):
                row = pair_map.pop((pid, left + 1, right + 1))
                p = base0[left]; q = base0[right]
                common = len(set(zip(p["rows"], p["bins"])) & set(zip(q["rows"], q["bins"])))
                shared_cells[common] += 1
                audit.eq(int(row["shared_active_cells"]), common, "Observed shared cells")
                audit.eq(int(row["shared_source_rows"]), len(set(p["rows"]) & set(q["rows"])), "Observed shared rows")
                audit.eq(as_bool(row["same_window"]), p["window_index"] == q["window_index"], "Observed common window")
                audit.close(row["score_gap"], p["base"] - q["base"], "Observed pair score gap")
        for host in (-768, 768):
            base = sorted(paths[host], key=lambda p: (-p["base"], p["window_start"], p["bins"]))
            row = null_map.pop((pid, host))
            for field, expected in (("eligible_unique_hypotheses", len(base)), ("retained_k1_count", 1),
                                    ("retained_k5_count", 5), ("additional_candidates", 4)):
                audit.eq(int(row[field]), expected, "Unique null " + field)
            audit.eq(json.loads(row["top5_indices"]), [p["index"] for p in base[:5]], "Unique null retained identities")
            for got, path in zip(json.loads(row["top5_scores"]), base[:5]):
                audit.close(got, path["base"], "Unique null score")
            audit.close(row["top1_score"], base[0]["base"], "Null top1 score")
            audit.close(row["top5_cut_score"], base[4]["base"], "Null cut score")
            audit.eq(as_bool(row["independent_null_trials"]), False, "Null correlated backgrounds")
            audit.eq(row["p_value"], "NOT_CALIBRATED", "Null calibration limitation")
            null_top1_scores.append(base[0]["base"]); null_cut_scores.append(base[4]["base"])
        for g in grouped[pid]:
            gid = g["geometry_id"]; host = int(g["host_offset_channels"])
            for amp in (0, 2, 8):
                row = row_map.pop((gid, amp))
                audit.eq(row["profile_id"], pid, "Trial profile")
                for field in ("origin_scan_id", "context_scan_id"):
                    audit.eq(row[field], g[field], "Trial " + field)
                audit.eq(int(row["origin_rank"]), int(g["origin_rank"]), "Trial origin rank")
                for field, expected in (("host_offset_channels", host), ("true_window_index", g["true_window_index"]),
                                        ("alias_draw_count", g["alias_draw_count"])):
                    audit.eq(int(row[field]), expected, "Trial " + field)
                for field, expected in (("true_active_source_rows", g["true_active_source_rows"]),
                                        ("truth_absolute_centers", g["truth16"]),
                                        ("truth_native4", g["truth_active4"]), ("relative_native4", g["native4"])):
                    audit.eq(json.loads(row[field]), expected, "Trial " + field)
                audit.eq(as_bool(row["native4_seen_in_prior_same_profile_window"]), g["native4_seen_in_prior_same_profile_window"], "Trial relative novelty")
                ranked, truth, best, rank_min, rank_max, tied, deterministic, partial = score_trial(
                    paths[host], g["true_active_source_rows"], g["truth_active4"], amp)
                winner = ranked[0]; top5 = ranked[:5]
                ints = {"truth_best_path_index": best["index"], "truth_path_count": len(truth),
                        "truth_rank_min": rank_min, "truth_rank_max": rank_max, "truth_rank_tie_count": tied,
                        "truth_deterministic_rank": deterministic, "winner_path_index": winner["index"],
                        "winner_window_index": winner["window_index"], "winner_overlap_count": winner["overlap"],
                        "best_partial_path_index": partial["index"], "best_partial_window_index": partial["window_index"],
                        "best_partial_overlap_count": partial["overlap"], "retained_count_top1": 1,
                        "retained_count_top5": 5, "full_truth_retained_count_top1": int(winner["overlap"] == 4),
                        "full_truth_retained_count_top5": sum(p["overlap"] == 4 for p in top5),
                        "eligible_unique_hypotheses": len(ranked)}
                for field, expected in ints.items():
                    audit.eq(int(row[field]), expected, "Trial " + field)
                floats = {"truth_score": best["score"], "winner_score": winner["score"],
                          "winner_minus_truth_score": winner["score"] - best["score"],
                          "best_partial_score": partial["score"],
                          "truth_minus_best_partial_score": best["score"] - partial["score"]}
                for field, expected in floats.items():
                    audit.close(row[field], expected, "Trial " + field)
                top1_capture = deterministic <= 1; top5_capture = deterministic <= 5
                audit.eq(as_bool(row["truth_retained_top1"]), top1_capture, "Actual deterministic k1 capture")
                audit.eq(as_bool(row["truth_retained_top5"]), top5_capture, "Actual deterministic k5 capture")
                audit.eq(as_bool(row["sham_target_only"]), amp == 0, "A0 sham interpretation")
                audit.eq(json.loads(row["retained_top5_indices"]), [p["index"] for p in top5], "Actual top5 identities")
                audit.eq(json.loads(row["retained_top5_overlaps"]), [p["overlap"] for p in top5], "Top5 cell overlaps")
                for rank, p in enumerate(top5, 1):
                    c = candidate_map.pop((gid, amp, rank))
                    audit.eq(c["profile_id"], pid, "Retained profile")
                    for field, expected in (("host_offset_channels", host), ("path_index", p["index"]),
                                            ("window_index", p["window_index"]), ("matched_active_cells", p["overlap"])):
                        audit.eq(int(c[field]), expected, "Retained " + field)
                    audit.eq(json.loads(c["source_rows"]), list(p["rows"]), "Retained rows")
                    audit.eq(json.loads(c["native4"]), list(p["bins"]), "Retained bins")
                    audit.close(c["score"], p["score"], "Retained injected score")
                    audit.eq(as_bool(c["complete_truth"]), p["overlap"] == 4, "Retained complete truth")
                panel = panels[amp]
                panel["count"] += 1; panel["top1"] += top1_capture; panel["top5"] += top5_capture
                panel["additional"] += top5_capture and not top1_capture
                panel["rank_counts"][deterministic] += 1; panel["winner_overlaps"][winner["overlap"]] += 1
                novelty_label = "seen_relative_path_new_absolute_placement" if g["native4_seen_in_prior_same_profile_window"] else "unseen_relative_path"
                for subgroup in (("by_host", str(host)), ("by_relative_native4_novelty", novelty_label)):
                    counts = panel["breakdown"][subgroup]
                    counts["trials"] += 1; counts["top1_count"] += top1_capture; counts["top5_count"] += top5_capture
        print(json.dumps({"QA_profiles_completed": len(families) - len(grouped) + 1, "checks": audit.checks}), flush=True)
        grouped.pop(pid)
    require(not row_map and not candidate_map and not observed_map and not pair_map and not null_map,
            "Unverified producer rows remain")
    for amp, panel in panels.items():
        s = summary["amplitude_panels"][str(amp)]
        for field, expected in (("trials", panel["count"]), ("top1_complete_truth_count", panel["top1"]),
                                ("top5_complete_truth_count", panel["top5"]),
                                ("additional_top5_complete_truth_count", panel["additional"]),
                                ("top5_missing_truth_count", panel["count"] - panel["top5"]),
                                ("hypothesis_slots_top1", panel["count"]), ("hypothesis_slots_top5", panel["count"] * 5)):
            audit.eq(s[field], expected, "Aggregate " + field)
        audit.eq(s["truth_deterministic_rank_counts"], {str(k): v for k, v in panel["rank_counts"].items()}, "Aggregate actual ranks")
        audit.eq(s["winner_overlap_counts"], {str(k): v for k, v in panel["winner_overlaps"].items()}, "Aggregate overlaps")
        audit.eq(s["label"], "SHAM_TARGET_RANK_DIAGNOSTIC" if amp == 0 else "CONDITIONAL_COMPLETE_TRUTH_CAPTURE", "Panel interpretation")
        audit.close(s["top1_complete_truth_fraction"], panel["top1"] / panel["count"], "Overall k1 fraction", 1e-15)
        audit.close(s["top5_complete_truth_fraction"], panel["top5"] / panel["count"], "Overall k5 fraction", 1e-15)
        for (name, label), counts in panel["breakdown"].items():
            subgroup = s[name][label]
            for field in ("trials", "top1_count", "top5_count"):
                audit.eq(subgroup[field], counts[field], "Subgroup " + name + " " + field)
            audit.close(subgroup["top1_fraction"], counts["top1_count"] / counts["trials"], "Subgroup k1 fraction", 1e-15)
            audit.close(subgroup["top5_fraction"], counts["top5_count"] / counts["trials"], "Subgroup k5 fraction", 1e-15)
    audit.eq(summary["numeric_trial_count"], expected_trial_count, "Summary trial count")
    audit.eq(summary["geometry_count"], len(geometries), "Summary geometry count")
    audit.eq(summary["source_score_recomputed_count"], score_recomputed_count, "Source row-term score census")
    audit.eq(summary["physical_novelty_counts"], annex["counts"], "Summary physical novelty census")
    audit.eq(summary["optional_raw_source_function_status"], "UNEXECUTED_UNTESTED_NOT_USED_FOR_RESULTS", "Optional raw helper excluded")
    burden = summary["null_burden_unique_profile_host_lists"]
    for field, expected in (("lists", 108), ("top1_candidates", 108), ("top5_candidates", 540),
                            ("additional_candidates", 432), ("workload_ratio", 5),
                            ("independent_null_trials", False), ("false_alarm_calibrated", False)):
        audit.eq(burden[field], expected, "Unique null workload " + field)
    for field, values in (("top1_score_min_median_max", null_top1_scores), ("top5_cut_score_min_median_max", null_cut_scores)):
        ordered_values = sorted(values)
        expected = [ordered_values[0], (ordered_values[53] + ordered_values[54]) / 2, ordered_values[-1]]
        for got, wanted in zip(burden[field], expected):
            audit.close(got, wanted, "Independent null min/median/max")
    obs = summary["observed_offset0_lists"]
    for field, expected in (("profiles", 54), ("top1_candidates", 54), ("top5_candidates", 270),
                            ("pairwise_comparisons", 540), ("new_detection", False)):
        audit.eq(obs[field], expected, "Observed workload " + field)
    audit.eq(obs["shared_cell_count_distribution"], {str(k): v for k, v in shared_cells.items()}, "Observed shared-cell histogram")
    for field, expected in (("qualified_SETI_detection", False), ("pilot_gate_pass", False),
                            ("original_A_B", "FAIL_CLOSED"), ("full6scan_chain_gates_tested", False),
                            ("calibrated_FAP", False), ("new_observation", False), ("new_telescope_requests", 0)):
        audit.eq(summary[field], expected, "Preserved interpretation " + field)
    usage = {"CPU_s": time.process_time() - started_cpu, "wall_s": time.monotonic() - started_wall,
             "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    require(usage["CPU_s"] <= budget["QA_CPU_s_cap"] and usage["wall_s"] <= budget["wall_s_cap_each"]
            and usage["peak_RSS_bytes"] <= budget["memory_bytes_cap_each"], "QA resource cap exceeded")
    result = {"schema": "SETI_FROZEN_RETENTION_INDEPENDENT_QA_V1",
              "status": "PASS_INDEPENDENT_GEOMETRY_OVERLAP_RANK_RETENTION_RECOMPUTATION",
              "scope_sha256": digest(scope_path), "qa_sha256": digest(Path(__file__).resolve()),
              "producer_sha256": go["producer_sha256"], "manifest_sha256": digest(manifest_path),
              "numeric_trial_count": expected_trial_count, "checks": audit.checks,
              "max_absolute_score_error": audit.max_score_error,
              "profiles": len(families), "source_base_scores_checked": score_recomputed_count,
              "independently_checked_novelty": novelty,
              "conditional_capture": {str(a): {"trials": p["count"], "k1": p["top1"], "k5": p["top5"],
                                                "additional": p["additional"]} for a, p in panels.items()},
              "unique_null_workload": {"lists": 108, "k1_slots": 108, "k5_slots": 540, "factor": 5},
              "observed_local_refinement": {"profiles": 54, "candidates": 270, "pairs": 540,
                                             "shared_active_cell_counts": dict(shared_cells)},
              "raw_spectral_arrays_opened": False, "new_telescope_requests": 0,
              "qualified_SETI_detection": False, "pilot_gate_pass": False,
              "calibrated_FAP": False, "physical_sensitivity_established": False,
              "fresh_background_validation": False, "resource_usage": usage}
    receipt_path = out / "QA_RECEIPT.json"
    require(not receipt_path.exists(), "QA receipt already exists; no overwrite/repeated run")
    with receipt_path.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True, allow_nan=False); f.write("\n")
    signal.alarm(0)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
