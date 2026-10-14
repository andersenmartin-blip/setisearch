#!/usr/bin/env python3
"""Independent saved-array check of the weak truth-rank result table."""
import argparse
import csv
import hashlib
import json
import resource
import time
from pathlib import Path

import numpy as np


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_root", type=Path)
    ap.add_argument("result_root", type=Path)
    a = ap.parse_args()
    wall0 = time.perf_counter(); cpu0 = time.process_time()
    scope = json.loads((a.result_root / "SCOPE.json").read_text())
    source = json.loads((a.input_root / "INJECTIONS.json").read_text())
    trials = {(t["profile_id"], float(t["true_drift_fraction_of_half_original_step"]),
               float(t["true_phase_channels"]), int(t["true_window_index"])): t
              for t in source["trials"] if t["amplitude_per_active_standardized_single_bin"] == 2.0}
    with (a.result_root / "results" / "TRIAL_RANKS.csv").open(newline="", encoding="utf-8") as f:
        table = list(csv.DictReader(f))
    summary = json.loads((a.result_root / "results" / "SUMMARY.json").read_text())
    assert len(table) == 1512 == len(trials)
    arrays = {}
    checks = 0
    max_score_error = 0.0
    observed_full = 0
    for row in table:
        pid = row["profile_id"]
        key = (pid, float(row["true_drift_fraction"]), float(row["true_phase_channels"]),
               int(row["true_window_index"]))
        t = trials.pop(key)
        if pid not in arrays:
            arrays[pid] = dict(np.load(a.input_root / "profiles" / f"{pid}_paths.npz", allow_pickle=False))
        z = arrays[pid]
        oi = list(z["offset_channels"]).index(512)
        allowed_indices = [i for i, blocked in enumerate(z["path_dc_mask"][oi]) if not blocked]
        active_rows = set(t["true_active_source_rows"])
        truth = t["canonical_float_truth_absolute_centers"]
        records = []
        for i in allowed_indices:
            hits = sum(int(src) in active_rows and int(ch) == int(truth[int(src)])
                       for src, ch in zip(z["path_source_rows"][i], z["absolute_channels"][oi, i]))
            score = float(z["scores"][oi, i]) + float(hits)
            records.append((score, hits, i))
        records.sort(key=lambda x: (-x[0], x[2]))
        truth_records = [x for x in records if x[1] == 4]
        assert truth_records
        truth_score = truth_records[0][0]
        higher = sum(x[0] > truth_score for x in records)
        equal = sum(x[0] == truth_score for x in records)
        winner = records[0]
        numeric = {
            "truth_score": truth_score,
            "truth_rank_min": 1 + higher,
            "truth_rank_max": higher + equal,
            "winner_score": winner[0],
            "winner_overlap_count": winner[1],
            "winner_path_index": winner[2]
        }
        for name, value in numeric.items():
            got = float(row[name]) if isinstance(value, float) else int(row[name])
            if isinstance(value, float):
                max_score_error = max(max_score_error, abs(got - value))
                assert abs(got - value) <= 1e-12
            else:
                assert got == value
            checks += 1
        observed_full += winner[1] == 4
        for k in (1, 2, 3, 5, 10, 20, 50, 100):
            assert (row[f"truth_retained_top{k}"] == "True") == ((1 + higher) <= k)
            checks += 1
    assert not trials and observed_full == 1036
    assert summary["global_winner_full_truth"] == observed_full
    assert summary["global_winner_partial"] == 1512 - observed_full
    assert summary["old_full_to_exact_partial"] == sum(r["old_full_to_exact_partial"] == "True" for r in table)
    assert summary["old_partial_to_exact_full"] == sum(r["old_partial_to_exact_full"] == "True" for r in table)
    checks += 4
    for k in (1, 2, 3, 5, 10, 20, 50, 100):
        count = sum(int(r["truth_rank_min"]) <= k for r in table)
        assert summary["retention"][str(k)]["count"] == count
        assert abs(summary["retention"][str(k)]["fraction"] - count / 1512) <= 1e-15
        checks += 2
    assert summary["old_full_to_exact_partial_diagnostic"]["retained_top5"] == 43
    checks += 1
    usage = {
        "CPU_s": time.process_time() - cpu0,
        "wall_s": time.perf_counter() - wall0,
        "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    }
    assert usage["CPU_s"] <= scope["resource_envelope"]["QA_CPU_s_cap"]
    result = {
        "schema": "SETI_WEAK_TRUTH_RANK_QA_V1",
        "status": "PASS_INDEPENDENT_SAVED_ARRAY_RECOMPUTATION",
        "trials": 1512,
        "profiles": len(arrays),
        "checks": checks,
        "full_truth_winners": observed_full,
        "max_absolute_score_error": max_score_error,
        "table_sha256": digest(a.result_root / "results" / "TRIAL_RANKS.csv"),
        "summary_sha256": digest(a.result_root / "results" / "SUMMARY.json"),
        "resource_usage": usage,
        "qualified_SETI_detection": False
    }
    out = a.result_root / "results" / "QA_RECEIPT.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
