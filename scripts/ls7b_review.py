#!/usr/bin/env python3
"""Audit sealed LS7B ledgers and attribute losses; never rescore or refit data."""
from collections import Counter
import json
from pathlib import Path

from ls7_tess_pilot import ROOT, save_json, sha256


def main():
    out = ROOT/"results_ls7b_tess"
    for line in (out/"SHA256SUMS").read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        assert sha256(out/name) == expected, name
    for manifest in ("LS7_FREEZE.sha256", "LS7B_FREEZE.sha256"):
        for line in (ROOT/manifest).read_text().splitlines():
            expected, name = line.split(maxsplit=1)
            assert sha256(ROOT/name) == expected, name
    s = json.loads((out/"summary.json").read_text())
    cfg = json.loads((ROOT/"config/ls7b_tess_l9859.json").read_text())
    base = json.loads((out/"baseline_trials.json").read_text())
    extra = json.loads((out/"extended_trials.json").read_text())
    events = json.loads((out/"restored_events.json").read_text())
    anchors = s["preflight"]["anchors"]
    assert len(base) == 300 and len(extra) == 120
    assert len({(r["anchor"],r["kind"],r["shape"],r["amplitude_fraction"],r["phase_seconds"]) for r in base}) == 300
    assert len({(r["anchor"],r["kind"],tuple(r["displacement_yx_pixels"]),r["phase_seconds"]) for r in extra}) == 120
    assert all(anchors[r["anchor"]] == r["native_index"] for r in base+extra)
    assert all(b-a > 400 for a,b in zip(anchors,anchors[1:]))
    for r in base+extra:
        assert r["screen_detected"] == (r["best"]["score"] >= cfg["score_threshold"])
        assert r["accepted"] == (r["screen_detected"] and r["morphology_pass"])
        assert r["recovered"] == (r["accepted"] and not r["baseline_confounded"])
    bright = [r for r in base if r["kind"]=="stellar" and r["amplitude_fraction"]==.01 and r["shape"]!="doublet30sep87"]
    screened = [r for r in bright if r["screen_detected"]]
    cuts = {
        "cosine":lambda m:m.get("cosine",-1) >= cfg["morphology"]["cosine_min"],
        "centroid":lambda m:m.get("centroid_shift_pixels",float("inf")) <= cfg["morphology"]["centroid_max_pixels"],
        "concentration":lambda m:m.get("peak_fraction",float("inf")) <= m.get("profile_peak_fraction",0)+cfg["morphology"]["peak_fraction_margin"],
        "background":lambda m:m.get("background_ratio",float("inf")) <= cfg["morphology"]["background_ratio_max"],
    }
    for r in base+extra:
        assert r["morphology_pass"] == all(cut(r["morphology"]) for cut in cuts.values())
    group_audit = []
    for group in s["recovery"]["groups"]:
        selected = [r for r in base if r["kind"]=="stellar" and r["shape"]==group["shape"] and r["amplitude_fraction"]==group["amplitude_fraction"]]
        assert len(selected) == group["trials"]
        assert sum(r["recovered"] for r in selected) == group["recovered"]
        assert sum(r["screen_detected"] for r in selected) == group["screen_detected"]
        group_audit.append(group)
    assert sum(r["recovered"] for r in bright) == s["recovery"]["bright_single_recovered"] == 5
    assert len(events) == s["native"]["restored_positive"] == 343
    assert all(r["sign"]==1 and r["score"]>=8 and not r["morphology"]["pass"] for r in events)
    assert all(any(q&64 for q in r["quality_words"]) for r in events)
    assert all(r["corrected_score_same_window"]<8 for r in events)
    assert not json.loads((out/"corrected_events.json").read_text())
    ordered = sorted(events, key=lambda e:e["start"])
    assert all(a["stop"]+2 <= b["start"] for a,b in zip(ordered,ordered[1:]))
    off = [r for r in extra if r["kind"]=="off_profile"]
    null = [r for r in base if r["kind"]=="null"]
    stellar = [r for r in base if r["kind"]=="stellar"]
    assert len(off)==80 and len(null)==20 and len(stellar)==240
    limits = cfg["qualification"]
    expected_gates = {
        "bright_single_recovery":sum(r["recovered"] for r in bright)/60 >= limits["bright_single_pulse_recovery_min"],
        "off_profile_recovery":sum(r["recovered"] for r in off)/80 >= limits["off_profile_recovery_min"],
        "null_acceptance":sum(r["accepted"] for r in null) <= limits["null_accepted_max"],
        "baseline_confounding":sum(r["baseline_confounded"] for r in stellar)/240 <= limits["confounded_fraction_max"],
        "no_event_overflow":not s["native"]["event_cap_overflow"],
        "eligibility":all(s["preflight"]["gates"].values()),
    }
    for kind, count in (("single_pixel",20),("uniform",20),("pointing",40)):
        rows = [r for r in base+extra if r["kind"]==kind]
        assert len(rows)==count
        accepted = sum(r["accepted"] for r in rows)
        assert {"trials":count,"accepted":accepted} == s["recovery"]["nuisance_by_kind"][kind]
        expected_gates[kind+"_acceptance"] = accepted/count <= limits["nuisance_acceptance_max_per_kind"]
    assert expected_gates == s["qualification_gates"]
    assert s["qualification_pass"] == all(expected_gates.values())
    attribution = {
        "scope":"Retrospective accounting of frozen ledgers; no new scoring or tuning",
        "bright_single_trials":len(bright), "below_screen_threshold":len(bright)-len(screened),
        "screened":len(screened), "screened_but_pixel_rejected":sum(not r["morphology_pass"] for r in screened),
        "recovered":sum(r["recovered"] for r in bright),
        "overlapping_cut_failures_among_screened":{name:sum(not test(r["morphology"]) for r in screened) for name,test in cuts.items()},
        "screen_detections_by_kind":{kind:sum(r["screen_detected"] for r in base+extra if r["kind"]==kind) for kind in ("stellar","off_profile","single_pixel","uniform","pointing","null")},
        "native_events":len(events), "native_with_aperture_cosmic_flag":sum(any(q&64 for q in r["quality_words"]) for r in events),
        "native_below_threshold_in_corrected_same_window":sum(r["corrected_score_same_window"]<8 for r in events),
        "native_corrected_same_window_score_range":[min(r["corrected_score_same_window"] for r in events),max(r["corrected_score_same_window"] for r in events)],
        "native_cosine_range":[min(r["morphology"]["cosine"] for r in events),max(r["morphology"]["cosine"] for r in events)],
        "caution":"No instrumental control reached the screening threshold; zero acceptance does not validate above-threshold nuisance rejection.",
    }
    save_json(out/"review_accounting.json", attribution)
    save_json(out/"AUDIT.json", {"status":"PASS_FOR_INTEGRITY_AND_ACCOUNTING_NOT_DETECTOR_QUALIFICATION",
                               "original_output_manifest_sha256":sha256(out/"SHA256SUMS"),
                               "review_script_sha256":sha256(Path(__file__)),
                               "checked_trial_records":len(base)+len(extra), "checked_native_records":len(events),
                               "original_freezes_unchanged":True, "all_trial_and_gate_identities_checked":True,
                               "implemented_unit_tests_passed":15, "detector_qualification_pass":s["qualification_pass"]})
    print(json.dumps(attribution,indent=2))


if __name__ == "__main__":
    main()
