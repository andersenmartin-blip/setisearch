#!/usr/bin/env python3
"""Independent scalar audit of LS7D's saved accounting (no FITS reread)."""
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]


def read(p):
    return json.loads(p.read_text())


def close(a, b, scale=1.):
    assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10*max(scale, 1.)), (a, b)


def main():
    out = ROOT/"results_ls7d_noise"
    s, windows, links = [read(out/p) for p in ("summary.json", "windows.json", "trial_links.json")]
    by = {r["window_id"]: r for r in windows}
    originals = [r for r in read(ROOT/"results_ls7c_tess/trials.json") if r["group"] == "matched" and r["kind"] == "stellar"]
    original_by = {r["trial_id"]: r for r in originals}
    assert len(originals) == len(links) == len({r["trial_id"] for r in links}) == 120
    assert {r["trial_id"] for r in links} == set(original_by)
    expected = {(r["anchor"], r["native_index"], r["best"]["start"], r["best"]["stop"]) for r in originals}
    assert len(expected) == len(windows) == len(by) == s["unique_windows"] == 34
    assert len({r["anchor"] for r in links}) == s["anchors"] == 10
    for link in links:
        old, w = original_by[link["trial_id"]], by[link["window_id"]]
        assert old["anchor"] == w["anchor"] == link["anchor"]
        assert old["native_index"] == w["native_index"]
        assert w["absolute_event_start"] == old["native_index"]-200+old["best"]["start"]
        assert w["absolute_event_stop"] == old["native_index"]-200+old["best"]["stop"]
        assert link["original_spatial_pass"] == old["spatial_pass"]
        close(link["original_noise_ratio"], w["quadrature_to_run_sigma_ratio"])
    assert sum(r["original_spatial_pass"] for r in links) == s["original_spatial_passes"] == 42
    covariance_checks = 0
    for w in windows:
        assert w["full_stamp_covariance_rank_upper_bound"] == 107 < w["valid_stamp_pixels"] == 121
        ap = {tuple(p) for p in w["aperture_pixel_yx"]}
        mask = [tuple(p) in ap for p in w["valid_pixel_yx"]]
        supplied, empirical = w["pixel_supplied_sigma"], w["pixel_empirical_sigma"]
        q_emp = math.sqrt(sum(e*e for e, use in zip(empirical, mask) if use))
        q_max = math.sqrt(sum(max(e, f)**2 for e, f, use in zip(empirical, supplied, mask) if use))
        q_sup = math.sqrt(sum(e*e for e, use in zip(supplied, mask) if use))
        for a, b in ((q_emp, w["quadrature_empirical_sigma"]), (q_max, w["quadrature_ls7c_sigma"]), (q_sup, w["quadrature_supplied_sigma"])):
            close(a, b)
        factors = w["multiplicative_factors"]
        close(math.prod(factors.values()), q_max/w["run_aperture_mad_sigma"])
        for stream in ("restored", "corrected"):
            r = w[stream]; c = r["covariance"]
            assert len(c) == len(ap) == 18 and all(len(row) == 18 for row in c)
            diagonal = sum(c[i][i] for i in range(18))
            total = math.fsum(x for row in c for x in row)
            for i in range(18):
                for j in range(18):
                    close(c[i][j], c[j][i], diagonal)
            close(diagonal, r["diagonal_variance"])
            close(total, r["scalar_variance"], diagonal)
            close(total-diagonal, r["cross_variance"], diagonal)
            close(total/diagonal, r["covariance_sum_to_diagonal_variance_ratio"])
            close(math.sqrt(diagonal/r["scalar_variance"]), r["diagonal_to_projected_sigma_ratio"])
            covariance_checks += 1
        for row, width in zip(w["block_scales"], (1, 2, 3, 5)):
            assert row["width_samples"] == width
            assert row["blocks_per_side"] == [55//width]*2
            assert row["unused_tail_samples_per_side"] == [55 % width]*2
            assert row["difference_vectors"] == 2*(55//width-1)
    for name, sample in (("trial_weighted", [by[r["window_id"]] for r in links]), ("unique_windows", windows)):
        summary = s["summaries"][name]
        for key in ("quadrature_to_run_sigma_ratio", "quadrature_ls7c_sigma", "quadrature_empirical_sigma", "quadrature_supplied_sigma"):
            values = [r[key] for r in sample]
            for k, f in (("min", min), ("median", statistics.median), ("max", max)):
                close(summary[key][k], f(values))
        for key in summary["factors"]:
            values = [r["multiplicative_factors"][key] for r in sample]
            for k, f in (("min", min), ("median", statistics.median), ("max", max)):
                close(summary["factors"][key][k], f(values))
    checked = 0
    for folder, name in ((ROOT, "LS7D_FREEZE.sha256"), (ROOT/"results_ls7c_tess", "SHA256SUMS"), (ROOT/"results_ls7c_tess", "REVIEW_SHA256SUMS")):
        for line in (folder/name).read_text().splitlines():
            expected_hash, path = line.split(maxsplit=1)
            assert hashlib.sha256((folder/path).read_bytes()).hexdigest() == expected_hash, path
            checked += 1
    audit = {"passed": True, "trial_links_checked": len(links), "unique_windows_checked": len(windows),
             "covariance_matrices_checked": covariance_checks, "hash_checks": checked,
             "original_spatial_decisions_preserved": 120,
             "scope": "Scalar ledger consistency, exact original membership and frozen input preservation; not detector qualification"}
    (out/"AUDIT.json").write_text(json.dumps(audit, indent=2)+"\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
