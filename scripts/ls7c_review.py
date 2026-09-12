#!/usr/bin/env python3
"""Audit sealed LS7C ledgers without changing scores, thresholds or trial sets."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def manifest(base, path):
    count = 0
    for line in path.read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        assert digest(base/name) == expected, name
        count += 1
    return count


def spatial(r, cfg):
    if "gates" not in r:
        assert r["pass"] is False
        return
    star = r["star"]
    pcfg = cfg["spatial"]
    expected = {"source_amplitude": star["amplitude_noise_score"] >= pcfg["source_score_min"],
                "weighted_residual": r["reduced_chi2"] <= pcfg["reduced_chi2_max"],
                "nuisance_separation": r["nuisance_delta_chi2"] >= pcfg["nuisance_delta_chi2_min"]}
    assert r["gates"] == expected
    assert r["pass"] == all(expected.values())
    assert r["residual_dof"] == r["pixels"]-2
    assert math.isclose(r["reduced_chi2"]*r["residual_dof"], star["chi2"], rel_tol=1e-10, abs_tol=1e-8)
    assert math.isclose(r["nuisance_chi2"]-star["chi2"], r["nuisance_delta_chi2"], rel_tol=1e-10, abs_tol=1e-8)
    assert math.isclose(star["background_only_chi2"]-star["chi2"], star["amplitude_noise_score"]**2, rel_tol=1e-8, abs_tol=1e-7)
    assert r["best_shift_yx"] == cfg["spatial"]["fit_shifts_yx"][star["template_index"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"results_ls7c_tess")
    args = parser.parse_args(); out = args.output
    originals = manifest(out, out/"SHA256SUMS")
    freezes = {p: manifest(ROOT, ROOT/p) for p in ("LS7_FREEZE.sha256", "LS7B_FREEZE.sha256", "LS7C_FREEZE.sha256")}
    s, cfg, rows, events = read(out/"summary.json"), read(ROOT/"config/ls7c_tess_l9859.json"), read(out/"trials.json"), read(out/"restored_events.json")
    assert s["status"] == "COMPLETED"
    assert s["freeze_sha256"] == digest(ROOT/"LS7C_FREEZE.sha256")
    assert len(rows) == s["digital_trials_completed"] == 1460
    # Independently enumerate the design membership, without importing its generator.
    cases = []
    for shape in ("box30", "box60", "box100", "doublet30sep87"):
        for amp in (.01, .03, .1):
            cases.append(("fixed", "stellar", shape, amp, (0., 0.)))
    shapes = [("stellar", (0., 0.))]+[("off_profile", p) for p in ((.2, .2), (.2, -.2), (-.2, .2), (-.2, -.2))]
    shapes += [(k, (0., 0.)) for k in ("single_pixel", "block_2x2", "uniform")]+[("pointing", p) for p in ((0., .2), (0., -.2))]
    for shape, level, (kind, shift) in itertools.product(("box30", "box100"), (8.5, 12., 20.), shapes):
        cases.append(("matched", kind, shape, level, shift))
    cases.append(("null", "null", "box30", 0., (0., 0.)))
    expected_ids = {f"a{a:02d}_p{p:g}_c{c:02d}" for a, p, c in itertools.product(range(10), (0., 10.), range(73))}
    assert len(rows) == len(expected_ids) and {r["trial_id"] for r in rows} == expected_ids
    for r in rows:
        assert (r["group"], r["kind"], r["shape"], r.get("target_score", r.get("amplitude_fraction")), tuple(r["shift_yx"])) == cases[r["case_index"]]
        assert r["native_index"] == s["preflight"]["anchors"][r["anchor"]]
        assert r["btjd"] == s["preflight"]["anchor_btjd"][r["anchor"]]
        assert r["sign"] in (-1, 1)
        assert r["screen_detected"] == (r["best"]["score"] >= 8)
        spatial(r["spatial"], cfg)
        assert r["spatial_pass"] == r["spatial"]["pass"]
        assert r["accepted"] == (r["screen_detected"] and r["spatial_pass"])
        assert r["baseline_confounded"] == (r["native_best"]["score"] >= 8)
        assert r["recovered"] == (r["accepted"] and not r["baseline_confounded"])
        if r["group"] == "matched":
            expected = r["tuning"]["matched"] and abs(r["best"]["score"]-r["target_score"]) <= .01
            assert r["strength_matched"] == expected
    for g in s["recovery"]["groups"]:
        subset = [r for r in rows if (r["group"], r["kind"], r["shape"], r.get("target_score", r.get("amplitude_fraction"))) == (g["group"], g["kind"], g["shape"], g["level"])]
        assert len(subset) == g["trials"]
        for k in ("screen_detected", "accepted", "recovered", "baseline_confounded", "strength_matched"):
            assert sum(bool(r[k]) for r in subset) == g[k]
    gates = {"complete_trial_count": True, "unique_trial_ids": True,
             "all_strengths_matched": all(r["strength_matched"] for r in rows if r["group"] == "matched")}
    for level, kind in itertools.product((8.5, 12., 20.), ("stellar", "off_profile", "single_pixel", "block_2x2", "uniform", "pointing")):
        subset = [r for r in rows if r["group"] == "matched" and r["kind"] == kind and r["target_score"] == level]
        assert len(subset) == {"stellar": 40, "off_profile": 160, "pointing": 80}.get(kind, 40)
        if kind in ("stellar", "off_profile"):
            gates[f"{kind}_{level:g}"] = sum(r["recovered"] for r in subset)/len(subset) >= (.9 if kind == "stellar" else .8)
        else:
            gates[f"{kind}_{level:g}"] = sum(r["accepted"] for r in subset)/len(subset) <= .05
    bright = [r for r in rows if r["group"] == "fixed" and r["amplitude_fraction"] == .1 and r["shape"] != "doublet30sep87"]
    signals = [r for r in rows if r["kind"] in ("stellar", "off_profile")]
    assert len(bright) == 60 and len(signals) == 840
    gates.update(ten_percent_single_recovery=sum(r["recovered"] for r in bright)/60 >= .9,
                 signal_confounding=sum(r["baseline_confounded"] for r in signals)/840 <= .2,
                 null_acceptance=not any(r["accepted"] for r in rows if r["kind"] == "null"),
                 eligibility=s["preflight"]["pass"], no_event_overflow=not s["native"]["event_cap_overflow"])
    assert gates == s["qualification_gates"] and all(gates.values()) == s["qualification_pass"]
    for r in events:
        assert r["score"] >= 8 and r["sign"] in (-1, 1)
        spatial(r["spatial"], cfg)
    assert len(events) == s["native"]["restored_positive"]+s["native"]["restored_negative"]
    corrected = read(out/"corrected_events.json")
    assert len(corrected) == s["native"]["corrected_positive"]+s["native"]["corrected_negative"]
    ordered = sorted((r for r in events if r["sign"] == 1), key=lambda r: (-r["score"], r["start"]))
    selected = [r for r in ordered if r["spatial"]["pass"]][:6]+[r for r in ordered if not r["spatial"]["pass"]][:4]
    assert read(out/"native_review_selection.json") == selected
    for sign, label in ((1, "positive"), (-1, "negative")):
        assert sum(r["sign"] == sign for r in events) == s["native"]["restored_"+label]
        assert sum(r["sign"] == sign and r["spatial"]["pass"] for r in events) == s["native"]["restored_"+label+"_spatial_pass"]
    loss = {}
    for family in ("fixed", "matched"):
        for kind in ("stellar", "off_profile", "single_pixel", "block_2x2", "uniform", "pointing"):
            subset = [r for r in rows if r["group"] == family and r["kind"] == kind]
            if not subset:
                continue
            loss[family+"_"+kind] = {"trials": len(subset), "screen_detected": sum(r["screen_detected"] for r in subset),
                                  "accepted": sum(r["accepted"] for r in subset), "recovered": sum(r["recovered"] for r in subset),
                                  "confounded": sum(r["baseline_confounded"] for r in subset),
                                  "above_threshold_failed_spatial_gates_overlapping": dict(Counter(k for r in subset if r["screen_detected"] for k, passed in r["spatial"].get("gates", {}).items() if not passed))}
    audit = {"audited_utc": datetime.now(timezone.utc).isoformat(), "audit_pass": True,
             "qualification_pass": s["qualification_pass"], "original_output_files_verified": originals,
             "scientific_manifests_verified": freezes, "trials_verified": len(rows), "native_records_verified": len(events),
             "failed_qualification_gates": [k for k, v in gates.items() if not v], "loss_accounting": loss,
             "native_corrected_same_window_score_range": [min(r["corrected_score_same_window"] for r in events), max(r["corrected_score_same_window"] for r in events)] if events else None,
             "native_windows_including_aperture_cr_flag": sum(any(q & 64 for q in r["quality_words"]) for r in events),
             "native_spatial_failure_counts_overlapping": dict(Counter(k for r in events for k, v in r["spatial"].get("gates", {}).items() if not v)),
             "scope": "Independent design membership and recorded arithmetic audit; no rescreening, refitting or probability calibration"}
    (out/"AUDIT.json").write_text(json.dumps(audit, indent=2, allow_nan=False)+"\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
