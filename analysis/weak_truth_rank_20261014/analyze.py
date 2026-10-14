#!/usr/bin/env python3
"""Rank known complete weak-injection paths in preserved exact-family arrays."""
import argparse
import csv
import hashlib
import json
import os
import resource
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

KS = (1, 2, 3, 5, 10, 20, 50, 100)
AMP = 2.0
HOST_OFFSET = 512


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def quantiles(values):
    a = np.asarray(values, dtype=np.float64)
    if not len(a):
        return None
    return {k: float(v) for k, v in zip(
        ("min", "q25", "median", "q75", "max"),
        np.quantile(a, (0, .25, .5, .75, 1), method="linear"))}


def percentile_nearest(values, q):
    a = np.asarray(values, dtype=np.int64)
    return int(np.quantile(a, q, method="higher"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    inp = args.input_root
    out = args.output_root
    out.mkdir(parents=True, exist_ok=True)
    scope_path = Path(__file__).with_name("SCOPE.json")
    scope = json.loads(scope_path.read_text())
    injection_path = inp / "INJECTIONS.json"
    profiles_path = inp / "PROFILES.json"
    assert sha256(injection_path) == scope["authenticated_inputs"]["INJECTIONS.json"]
    assert sha256(profiles_path) == scope["authenticated_inputs"]["PROFILES.json"]
    injections = json.loads(injection_path.read_text())
    trials = [t for t in injections["trials"]
              if t["amplitude_per_active_standardized_single_bin"] == AMP]
    assert len(trials) == 1512
    grouped = defaultdict(list)
    for t in trials:
        grouped[t["profile_id"]].append(t)
    assert len(grouped) == 54 and all(len(v) == 28 for v in grouped.values())

    receipt = json.loads((inp / "EXECUTION_RECEIPT.json").read_text())
    expected_npz = {Path(x["path"]).name: x["sha256"] for x in receipt["outputs"]
                    if x["path"].startswith("profiles/")}
    assert len(expected_npz) == 54
    rows = []
    verified_npz = []
    for profile_id in sorted(grouped):
        npz_path = inp / "profiles" / f"{profile_id}_paths.npz"
        digest = sha256(npz_path)
        assert expected_npz[npz_path.name] == digest
        verified_npz.append({"path": npz_path.name, "sha256": digest})
        with np.load(npz_path, allow_pickle=False) as a:
            oi = int(np.flatnonzero(a["offset_channels"] == HOST_OFFSET)[0])
            base = a["scores"][oi].astype(np.float64)
            channels = a["absolute_channels"][oi]
            source_rows = a["path_source_rows"]
            eligible = ~a["path_dc_mask"][oi]
            window_indices = a["path_window_index"]
            assert base.shape == eligible.shape == window_indices.shape
            for t in grouped[profile_id]:
                truth = np.asarray(t["canonical_float_truth_absolute_centers"], dtype=np.int64)
                active = np.zeros(16, dtype=bool)
                active[np.asarray(t["true_active_source_rows"], dtype=np.int64)] = True
                matches = (channels == truth[source_rows]) & active[source_rows]
                counts = matches.sum(axis=1, dtype=np.int64)
                scores = base + AMP * counts / 2.0
                truth_mask = eligible & (counts == 4)
                truth_indices = np.flatnonzero(truth_mask)
                assert len(truth_indices) >= 1
                truth_scores = scores[truth_indices]
                truth_score = float(truth_scores.max())
                truth_index = int(truth_indices[int(np.argmax(truth_scores))])
                eligible_scores = scores[eligible]
                greater = int(np.count_nonzero(eligible_scores > truth_score))
                equal = int(np.count_nonzero(eligible_scores == truth_score))
                rank_min = 1 + greater
                rank_max = greater + equal
                masked = np.where(eligible, scores, -np.inf)
                winner_index = int(np.argmax(masked))
                winner_score = float(masked[winner_index])
                winner_overlap = int(counts[winner_index])
                assert abs(winner_score - float(t["exact_score"])) <= 1e-12
                assert winner_overlap == int(t["exact_winner_matching_active4_count"])
                partial_mask = eligible & (counts < 4)
                best_partial_index = int(np.argmax(np.where(partial_mask, scores, -np.inf)))
                best_partial_score = float(scores[best_partial_index])
                old_overlap = int(t["legacy_fine_winner_matching_active4_count"])
                rows.append({
                    "profile_id": profile_id,
                    "true_drift_fraction": t["true_drift_fraction_of_half_original_step"],
                    "true_phase_channels": t["true_phase_channels"],
                    "true_window_index": t["true_window_index"],
                    "truth_path_count": int(len(truth_indices)),
                    "truth_best_path_index": truth_index,
                    "truth_score": truth_score,
                    "truth_rank_min": rank_min,
                    "truth_rank_max": rank_max,
                    "truth_rank_tie_count": equal,
                    "winner_path_index": winner_index,
                    "winner_window_index": int(window_indices[winner_index]),
                    "winner_score": winner_score,
                    "winner_overlap_count": winner_overlap,
                    "winner_is_full_truth": winner_overlap == 4,
                    "winner_minus_truth_score": winner_score - truth_score,
                    "best_partial_path_index": best_partial_index,
                    "best_partial_window_index": int(window_indices[best_partial_index]),
                    "best_partial_overlap_count": int(counts[best_partial_index]),
                    "best_partial_score": best_partial_score,
                    "truth_minus_best_partial_score": truth_score - best_partial_score,
                    "legacy_winner_overlap_count": old_overlap,
                    "old_full_to_exact_partial": old_overlap == 4 and winner_overlap < 4,
                    "old_partial_to_exact_full": old_overlap < 4 and winner_overlap == 4,
                    **{f"truth_retained_top{k}": rank_min <= k for k in KS}
                })
    assert len(rows) == 1512

    fields = list(rows[0])
    csv_path = out / "TRIAL_RANKS.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)

    partial = [r for r in rows if not r["winner_is_full_truth"]]
    losses = [r for r in rows if r["old_full_to_exact_partial"]]
    gains = [r for r in rows if r["old_partial_to_exact_full"]]
    rank_counts = Counter(r["truth_rank_min"] for r in rows)
    overlap_counts = Counter(r["winner_overlap_count"] for r in rows)
    retention = {str(k): {"count": sum(r[f"truth_retained_top{k}"] for r in rows),
                          "fraction": sum(r[f"truth_retained_top{k}"] for r in rows) / len(rows)}
                 for k in KS}
    # The policy is deliberately simple and is marked development-only. Its
    # value is not used to rewrite any exposed outcome into a pass.
    development_policy = {
        "rule": "retain the five highest-scoring eligible unique (window, native four-bin path) hypotheses per profile/trial",
        "k": 5,
        "status": "DEVELOPMENT_ONLY_REQUIRES_FRESH_PROSPECTIVE_VALIDATION",
        "selected_after_exposed_rank_diagnostic": True,
        "qualifies_existing_results": False,
        "measured_exposed_weak_truth_retention": retention["5"]
    }
    summary = {
        "schema": "SETI_WEAK_TRUTH_RANK_RESULT_V1",
        "status": "COMPLETE_POSTDATA_WEAK_TRUTH_RANK_DIAGNOSTIC",
        "date": "2026-10-14",
        "weak_trials": len(rows),
        "complete_truth_path_attainable": sum(r["truth_path_count"] > 0 for r in rows),
        "complete_truth_path_multiplicity": {
            str(n): sum(r["truth_path_count"] == n for r in rows)
            for n in sorted(set(r["truth_path_count"] for r in rows))
        },
        "global_winner_overlap_counts": {str(k): overlap_counts[k] for k in sorted(overlap_counts)},
        "global_winner_full_truth": sum(r["winner_is_full_truth"] for r in rows),
        "global_winner_partial": len(partial),
        "old_full_to_exact_partial": len(losses),
        "old_partial_to_exact_full": len(gains),
        "truth_rank_counts": {str(k): rank_counts[k] for k in sorted(rank_counts)},
        "truth_rank_quantiles_all": {
            "min": min(r["truth_rank_min"] for r in rows),
            "q50_higher": percentile_nearest([r["truth_rank_min"] for r in rows], .5),
            "q90_higher": percentile_nearest([r["truth_rank_min"] for r in rows], .9),
            "q95_higher": percentile_nearest([r["truth_rank_min"] for r in rows], .95),
            "q99_higher": percentile_nearest([r["truth_rank_min"] for r in rows], .99),
            "max": max(r["truth_rank_min"] for r in rows)
        },
        "retention": retention,
        "retention_by_winner_overlap": {
            str(overlap): {
                "cases": sum(r["winner_overlap_count"] == overlap for r in rows),
                "top5_count": sum(r["winner_overlap_count"] == overlap and r["truth_rank_min"] <= 5 for r in rows)
            }
            for overlap in range(5)
        },
        "partial_winner_diagnostic": {
            "cases": len(partial),
            "winner_overlap_counts": {str(k): sum(r["winner_overlap_count"] == k for r in partial) for k in range(4)},
            "truth_rank_quantiles": {
                "min": min(r["truth_rank_min"] for r in partial),
                "q50_higher": percentile_nearest([r["truth_rank_min"] for r in partial], .5),
                "q90_higher": percentile_nearest([r["truth_rank_min"] for r in partial], .9),
                "q95_higher": percentile_nearest([r["truth_rank_min"] for r in partial], .95),
                "max": max(r["truth_rank_min"] for r in partial)
            },
            "winner_minus_truth_score_quantiles": quantiles([r["winner_minus_truth_score"] for r in partial])
        },
        "old_full_to_exact_partial_diagnostic": {
            "cases": len(losses),
            "truth_rank_counts": {str(k): sum(r["truth_rank_min"] == k for r in losses)
                                  for k in sorted(set(r["truth_rank_min"] for r in losses))},
            "truth_rank_max": max(r["truth_rank_min"] for r in losses),
            "retained_top5": sum(r["truth_rank_min"] <= 5 for r in losses),
            "winner_overlap_counts": {str(k): sum(r["winner_overlap_count"] == k for r in losses) for k in range(4)},
            "winner_minus_truth_score_quantiles": quantiles([r["winner_minus_truth_score"] for r in losses])
        },
        "development_candidate_retention_policy": development_policy,
        "qualified_SETI_detection": False,
        "calibrated_FAP": False,
        "physical_sensitivity_established": False,
        "new_observation": False,
        "new_telescope_requests": 0,
        "interpretation": [
            "Ranks are descriptive within an exposed, correlated exact-path family.",
            "Top-k retention does not turn a weak injected winner or telescope profile into a detection.",
            "The development policy must be frozen before and assessed on fresh identities."
        ]
    }
    summary_path = out / "SUMMARY.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    elapsed_cpu = time.process_time() - started_cpu
    elapsed_wall = time.perf_counter() - started_wall
    assert elapsed_cpu <= scope["resource_envelope"]["analysis_CPU_s_cap"]
    receipt_out = {
        "schema": "SETI_WEAK_TRUTH_RANK_EXECUTION_RECEIPT_V1",
        "status": "COMPLETE",
        "scope_sha256": sha256(scope_path),
        "input_INJECTIONS_sha256": sha256(injection_path),
        "input_PROFILES_sha256": sha256(profiles_path),
        "verified_profile_arrays": len(verified_npz),
        "verified_profile_arrays_manifest_sha256": hashlib.sha256(
            json.dumps(verified_npz, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "outputs": {
            "TRIAL_RANKS.csv": {"bytes": csv_path.stat().st_size, "sha256": sha256(csv_path)},
            "SUMMARY.json": {"bytes": summary_path.stat().st_size, "sha256": sha256(summary_path)}
        },
        "resource_usage": {
            "CPU_s": elapsed_cpu,
            "wall_s": elapsed_wall,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        },
        "new_telescope_requests": 0,
        "new_telescope_bytes": 0,
        "qualified_SETI_detection": False
    }
    (out / "EXECUTION_RECEIPT.json").write_text(json.dumps(receipt_out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
