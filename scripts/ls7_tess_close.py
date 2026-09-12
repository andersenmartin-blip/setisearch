#!/usr/bin/env python3
"""Close the unchanged LS7 run after its injection-anchor eligibility failure.

This reporting/quality-metadata diagnostic does not alter or rerun the frozen
search. Alternative flag policies are feasibility comparisons, not evaluations.
"""
from collections import Counter
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform

from astropy.io import fits
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from ls7_tess_pilot import ROOT, save_json, sha256, verify_freeze
from seti_repeater.light_sail_tess import geometry_diagnostic, good_segments


def main():
    verify_freeze()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results_ls7_tess")
    parser.add_argument("--cache", type=Path, default=ROOT / "data_ls7_tess")
    args = parser.parse_args()
    output = args.output
    if (output / "summary.json").exists():
        raise RuntimeError("refusing to replace a completed summary")
    cfg = json.loads((ROOT / "config/ls7_tess_l9859.json").read_text())
    manifest = json.loads((output / "source_manifest.json").read_text())
    metadata = json.loads((output / "metadata.json").read_text())
    noise = json.loads((output / "segments.json").read_text())
    events = json.loads((output / "native_events.json").read_text())
    for product in manifest["products"]:
        path = args.cache / product["name"]
        if sha256(path) != product["sha256"]:
            raise RuntimeError("input hash changed")
    tp_path = args.cache / next(p["name"] for p in manifest["products"] if p["kind"] == "tp")
    lc_path = args.cache / next(p["name"] for p in manifest["products"] if p["kind"] == "lc")
    with fits.open(tp_path, memmap=False) as tp, fits.open(lc_path, memmap=False) as lc:
        time = np.asarray(tp[1].data["TIME"], dtype=float)
        cadence = np.asarray(tp[1].data["CADENCENO"], dtype=int)
        qtp = np.asarray(tp[1].data["QUALITY"], dtype=int)
        qlc = np.asarray(lc[1].data["QUALITY"], dtype=int)
        quality = qtp | qlc
        aperture = (tp["APERTURE"].data & 2) != 0
        finite = np.isfinite(time) & np.all(np.isfinite(tp[1].data["FLUX"][:, aperture]), axis=1)
        # Inspect correction locations/IDs, not their measured amplitudes.
        cr = tp["TARGET COSMIC RAY"].data
        x = np.asarray(cr["RAWX"], dtype=int) - int(tp[1].header["1CRV5P"])
        y = np.asarray(cr["RAWY"], dtype=int) - int(tp[1].header["2CRV5P"])
        cr_cadences = np.unique(cr["CADENCENO"][aperture[y, x]])
        corrected_aperture_cadence = np.isin(cadence, cr_cadences)
        policies = []
        for label, allowed in [("frozen_quality_zero", 0), ("diagnostic_allow_aperture_CR", 64),
                               ("diagnostic_allow_collateral_CR", 1024), ("diagnostic_allow_both_CR", 64 | 1024)]:
            good = ((quality & ~allowed) == 0) & finite
            runs = good_segments(time, cadence, good, cfg["cadence_seconds"])
            lengths = np.array([hi - lo for lo, hi in runs])
            searchable = np.zeros(len(time), dtype=bool)
            for lo, hi in runs:
                if hi - lo >= cfg["baseline_samples"] + max(cfg["box_samples"]):
                    searchable[lo + 60:hi - 60] = True
            policies.append({"policy": label, "allowed_bits": allowed, "evaluated_search": allowed == 0,
                             "accepted_rows": int(good.sum()), "accepted_cadence_days": float(good.sum()*20/86400),
                             "runs": len(runs), "longest_run_rows": int(lengths.max()),
                             "median_run_rows": float(np.median(lengths)),
                             "screenable_runs": int(np.count_nonzero(lengths >= 126)),
                             "searchable_rows": int(searchable.sum()), "searchable_cadence_days": float(searchable.sum()*20/86400),
                             "eligible_injection_anchor_indices": int(np.maximum(lengths - 400, 0).sum()),
                             "accepted_aperture_CR_cadences": int(np.count_nonzero(good & corrected_aperture_cadence))})
            if allowed == 0:
                frozen_searchable = searchable
                frozen_lengths = lengths
        geometry = {pair: {"searched_fraction_within_one_stellar_radius": float(np.mean(d <= 1)),
                          "searched_cadence_days_within_one_stellar_radius": float(np.count_nonzero(d <= 1)*20/86400)}
                    for pair, d in geometry_diagnostic(time[frozen_searchable]+metadata["bjd_reference"], cfg["geometry"]).items()}
    original = policies[0]
    if original["accepted_rows"] != metadata["accepted_rows"] or original["eligible_injection_anchor_indices"] != 0:
        raise RuntimeError("closure assumptions do not match frozen run")
    if original["searchable_rows"] != sum(r["stop"]-r["start"]-120 for r in noise):
        raise RuntimeError("original segment ledger mismatch")
    if (output / "injection_trials.json").exists():
        raise RuntimeError("unexpected injection ledger for an anchor-aborted run")
    save_json(output / "quality_feasibility.json", {"scope": "retrospective_quality_and_time_metadata_only_no_alternative_flux_search",
                                                    "policies": policies, "tp_lc_quality_disagreements": int(np.count_nonzero(qtp != qlc)),
                                                    "frozen_run_length_histogram": {str(k): int(v) for k,v in sorted(Counter(frozen_lengths.tolist()).items())}})
    summary = {"schema": "ls7-tess-pilot-closure-v1", "closed_utc": datetime.now(timezone.utc).isoformat(),
               "frozen_code_commit": "ef940930572e13d871eb8bfa5f756778bca16993", "freeze_sha256": sha256(ROOT / "LS7_FREEZE.sha256"),
               "closure_script_sha256": sha256(Path(__file__)), "python": platform.python_version(),
               "status": "NOT_QUALIFIED_INSUFFICIENT_CONTIGUOUS_ANCHORS", "qualification_pass": False,
               "original_error": "ValueError: not enough unbroken data for fixed injection anchors",
               "original_exit_code": 1, "original_outputs_preserved": ["metadata.json", "source_manifest.json", "segments.json", "native_events.json"],
               "metadata": metadata, "frozen_coverage": original, "native_trigger_count": len(events),
               "digital_trials_planned": 300, "digital_trials_completed": 0,
               "recovery_fraction": None, "nuisance_acceptance_fraction": None,
               "geometry": geometry,
               "claim": "No sensitivity measurement, qualified detector, LS candidate or astrophysical null result",
               "next_step": "Freeze a correction-aware flag policy and independently evaluate an unopened sector; do not relabel the present failure as a success."}
    save_json(output / "summary.json", summary)
    fig, ax = plt.subplots(figsize=(8, 4.4), layout="constrained")
    labels = ["QUALITY = 0\nFrozen pilot", "Allow bit 64\nMetadata only", "Allow bit 1024\nMetadata only", "Allow 64 + 1024\nMetadata only"]
    bars = ax.bar(labels, [p["searchable_cadence_days"] for p in policies], color=["#a85332", "#5c748d", "#5c748d", "#5c748d"])
    for bar, p in zip(bars, policies):
        ax.annotate(f"{p['searchable_cadence_days']:.2f} d", (bar.get_x()+bar.get_width()/2, bar.get_height()), xytext=(0, 5), textcoords="offset points", ha="center")
    ax.set(ylabel="Cadence-days after run and edge requirements", title="L 98-59 · TESS sector 28: effect of flag exclusions")
    ax.set_ylim(0, max(p["searchable_cadence_days"] for p in policies)*1.18)
    ax.grid(axis="y", alpha=.2)
    fig.savefig(output / "quality_feasibility.svg")
    fig.savefig(output / "quality_feasibility.png", dpi=150)
    plt.close(fig)
    print(json.dumps({"frozen": original, "diagnostic_policies": policies[1:], "geometry": geometry}, indent=2))


if __name__ == "__main__":
    main()
