#!/usr/bin/env python3
"""Run the public LS7C freeze on the one pinned, previously unopened sector."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import warnings

from astropy.io import fits
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import median_filter

from ls7_tess_pilot import ROOT, load_products, retrieve, save_json, sha256
from ls7b_tess_pilot import read_preflight, seal
from seti_repeater.light_sail_tess import geometry_diagnostic, screen
from seti_repeater.light_sail_tess_v3 import accounting, run_anchor, spatial_diagnostic, spatial_model


def annotate(events, cube, errors, ap, corrected_flux, time, quality, positions, segments, noise, cfg):
    sigmas = {r["segment"]: r["sigma_e_per_s"] for r in noise}
    for e in events:
        lo, hi = e["start"], e["stop"]
        seg_lo, seg_hi = segments[e["segment"]]
        # Bounded slice entirely inside one accepted run, with the full sidebands.
        a, b = max(seg_lo, lo-60), min(seg_hi, hi+60)
        model = spatial_model(cube[a:b], errors[a:b], ap, lo-a, hi-a, cfg)
        e["spatial"] = spatial_diagnostic(cube[a:b], lo-a, hi-a, model, cfg, e["sign"])
        e["btjd_mid"] = float(np.mean(time[lo:hi]))
        e["quality_words"] = sorted(set(int(x) for x in quality[lo:hi]))
        local = corrected_flux[a:b]
        baseline = median_filter(local, size=cfg["baseline_samples"], mode="nearest")
        e["corrected_score_same_window"] = float(e["sign"]*np.sum((local-baseline)[lo-a:hi-a])/(sigmas[e["segment"]]*np.sqrt(hi-lo)))
        side = np.r_[lo-60:lo-5, hi+5:hi+60]
        e["pointing_proxy_delta_xy_pixels"] = []
        for v in positions.T:
            delta = float(np.mean(v[lo:hi])-np.median(v[side])) if np.all(np.isfinite(v[np.r_[lo:hi, side]])) else None
            e["pointing_proxy_delta_xy_pixels"].append(delta)
        e["pair_separation_stellar_radii"] = {k: float(v) for k, v in geometry_diagnostic(e["btjd_mid"]+2457000, cfg["geometry"]).items()}


def figures(output, groups, events, cube, aperture, flux, corrected_flux, time, cfg):
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), layout="constrained")
    for kind in ("stellar", "off_profile"):
        levels = cfg["strength_trials"]["scores"]
        curves = []
        for level in levels:
            g = [r for r in groups if r["group"] == "matched" and r["kind"] == kind and r["level"] == level]
            curves.append(sum(r["recovered"] for r in g)/sum(r["trials"] for r in g))
        ax[0].plot(levels, curves, "o-", label=kind)
    for kind in ("single_pixel", "block_2x2", "uniform", "pointing"):
        rates = []
        for level in levels:
            g = [r for r in groups if r["group"] == "matched" and r["kind"] == kind and r["level"] == level]
            rates.append(sum(r["accepted"] for r in g)/sum(r["trials"] for r in g))
        ax[1].plot(levels, rates, "o-", label=kind)
    for a in ax:
        a.set(xlabel="Matched temporal screening score", ylim=(-.03, 1.03), xticks=levels)
        a.legend(fontsize=8)
    ax[0].set(ylabel="Digital signal recovery", title="Stellar aperture profiles")
    ax[1].set(ylabel="Control acceptance", title="Above-threshold nuisance challenges")
    ax[1].axhline(.05, color="black", linestyle="--", lw=.8)
    fig.suptitle("LS7C · L 98-59 sector 32 · 10 shared backgrounds, not sky completeness", fontsize=11)
    fig.savefig(output/"qualification.svg"); fig.savefig(output/"qualification.png", dpi=145)
    plt.close(fig)
    ordered = sorted((e for e in events if e["sign"] == 1), key=lambda e: (-e["score"], e["start"]))
    selected = [e for e in ordered if e["spatial"]["pass"]][:cfg["native_review"]["passing_events"]]
    selected += [e for e in ordered if not e["spatial"]["pass"]][:cfg["native_review"]["failing_events"]]
    save_json(output/"native_review_selection.json", selected)
    if not selected:
        return
    fig, axes = plt.subplots(len(selected), 2, figsize=(11, 2.5*len(selected)), squeeze=False, layout="constrained")
    for row, e in enumerate(selected):
        lo, hi = e["start"], e["stop"]
        a, b = lo-30, hi+30
        norm = np.median(corrected_flux[a:b])
        for y, label in ((flux, "restored"), (corrected_flux, "corrected")):
            axes[row, 0].plot((time[a:b]-e["btjd_mid"])*86400, 100*(y[a:b]/norm-1), ".-", lw=.7, ms=2, label=label)
        axes[row, 0].set(xlabel="Seconds from window midpoint", ylabel="Relative flux (%)", title=f"BTJD {e['btjd_mid']:.6f}; score {e['score']:.1f}; pixel pass {e['spatial']['pass']}")
        axes[row, 0].legend(fontsize=7)
        side = np.r_[lo-60:lo-5, hi+5:hi+60]
        delta = np.nanmean(cube[lo:hi], axis=0)-np.nanmedian(cube[side], axis=0)
        limit = float(np.nanmax(np.abs(delta))) or 1.
        im = axes[row, 1].imshow(delta, origin="lower", cmap="RdBu_r", vmin=-limit, vmax=limit)
        axes[row, 1].contour(aperture, levels=[.5], colors="black", linewidths=.6)
        axes[row, 1].set(xlabel="Stamp column", ylabel="Stamp row", title="Restored excess (electrons/s)")
        fig.colorbar(im, ax=axes[row, 1], shrink=.8)
    fig.savefig(output/"native_review.png", dpi=130)
    plt.close(fig)


def report(output, s):
    p, m, n = s["preflight"], s["metadata"], s["native"]
    lines = ["# LS7C: noise-aware TESS pixel qualification", "", "Run: "+s["run_utc"], "",
             "**Restricted digital qualification: "+("PASS" if s["qualification_pass"] else "FAIL")+".** No event is promoted as a light-sail candidate.", "",
             f"L 98-59, TIC {m['tic']}, sector {m['sector']}, nominal 600–1000 nm, 20-second sampling. Observed {m['date_obs_utc']} to {m['date_end_utc']} UTC.", "",
             f"{p['accepted_cadence_days']:.4f} accepted cadence-days; **{p['searchable_cadence_days']:.4f} searchable cadence-days**. Ten nonoverlapping 401-sample contexts span {p['anchor_span_days']:.3f} days. These are summed sample durations, not exact photon live time.", "",
             f"All **{s['digital_trials_completed']}** planned digital trials completed: 240 fixed-amplitude signals, 600 strength-matched signals, 600 strength-matched nuisances and 20 unchanged controls. Matched tests use observed screening scores 8.5, 12 and 20. Confounded and unmatched cases remain in their denominators.", "",
             "## Matched-strength trials", "", "| Kind | Score | Trials | Screen detections | Accepted | Recovered |", "|---|---:|---:|---:|---:|---:|"]
    for kind in ("stellar", "off_profile", "single_pixel", "block_2x2", "uniform", "pointing"):
        for level in (8.5, 12., 20.):
            gs = [g for g in s["recovery"]["groups"] if g["group"] == "matched" and g["kind"] == kind and g["level"] == level]
            counts = [sum(g[k] for g in gs) for k in ("trials", "screen_detected", "accepted", "recovered")]
            lines.append(f"| {kind} | {level:g} | "+" | ".join(map(str, counts))+" |")
    lines += ["", "Recovered means accepted without a pre-existing matched trigger. For nuisances the qualification endpoint is acceptance, irrespective of confounding.", "", "![Matched-strength qualification](qualification.svg)", "",
              "## Fixed-amplitude signals", "", "| Shape | Added aperture flux | Screen / trials | Recovered / trials |", "|---|---:|---:|---:|"]
    for g in s["recovery"]["groups"]:
        if g["group"] == "fixed":
            lines.append(f"| {g['shape']} | {100*g['level']:g}% | {g['screen_detected']}/{g['trials']} | {g['recovered']}/{g['trials']} |")
    lines += ["", "## Frozen requirements", "", "| Requirement | Pass |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in s["qualification_gates"].items()]
    lines += ["", "## Native data and geometry", "",
              f"Restored: {n['restored_positive']} positive and {n['restored_negative']} negative triggers; {n['restored_positive_spatial_pass']} positive and {n['restored_negative_spatial_pass']} negative spatial passes. Corrected: {n['corrected_positive']} positive and {n['corrected_negative']} negative triggers. All retained windows, same-window corrected scores, flags and spatial diagnostics are archived.", "",
              "[Predetermined native review selection](native_review_selection.json) and [excess images](native_review.png). Spatial consistency alone cannot establish artificial origin or reject stellar flares and all unresolved contaminants.", "",
              "The unchanged circular, edge-on, common-node approximation gives searched cadence coverage within one stellar radius in projected pair separation:", ""]
    for pair, g in s["geometry"].items():
        lines.append(f"- {pair}: {100*g['fraction_within_one_stellar_radius']:.3f}% ({g['cadence_days_within_one_stellar_radius']:.5f} cadence-days).")
    lines += ["", "Pair intervals overlap. Geometry is descriptive, omits inclination/node/ephemeris uncertainties, and does not select events or predict beam interception.", "",
              "## Scope and reproducibility", "",
              "This is a prospective evaluation on sector 32, selected using metadata after sectors 28/29 had closed. Scientific code and thresholds were published before the new arrays were retrieved. Original LS7/LS7B outputs remain unchanged. No result-dependent threshold adjustment is allowed.", "",
              "The spatial model uses diagonal pixel variances and empirical aperture profiles, with fitted constant background and a fixed displacement grid. Its residual scores are not calibrated probabilities. Digital injections are deterministic additions after mission processing/quality selection; they do not add photon shot noise or measure processing survival. Strength-matched nuisances include amplified scene-shift patterns, not a complete physical spacecraft model; some controls share templates with the rejection model. The 2×2 block is an additional spatial mismatch absent from that library.", "",
              "The ten backgrounds are shared by many trials. Passing would qualify only this finite challenge, not total transient completeness or an adopted SETI detector. TESS provides one optical band and cannot identify a laser spectrum; a 1.06-micron line lies outside its nominal band. The experiment complements LS1 radio work but supports no propulsion population limit.", "",
              "- [Prospective protocol](../LS7C_TESS_PROTOCOL.md)", "- [Input identities](source_manifest.json)", "- [Full summary](summary.json)", "- [All 1,460 trial records](trials.json)", "- [Native records](restored_events.json)", "- [Output checksums](SHA256SUMS)", "",
              "Code commit: `"+s["code_commit"]+"`; freeze SHA-256: `"+s["freeze_sha256"]+"`.", "",
              "Processing: [NASA cosmic-ray documentation](https://heasarc.gsfc.nasa.gov/docs/tess/TESS-CosmicRayPrimer.html), [MAST quality flags](https://outerspace.stsci.edu/spaces/TESS/pages/14563420/2.0%2B-%2BData%2BProduct%2BOverview)."]
    (output/"REPORT.md").write_text("\n".join(lines)+"\n")


def execute(args, cfg, s):
    paths, sources = {}, []
    for product in cfg["products"]:
        paths[product["kind"]], record = retrieve(product, args.cache)
        sources.append(record)
    save_json(args.output/"source_manifest.json", {"retrieved_utc": datetime.now(timezone.utc).isoformat(), "products": sources})
    preflight, segments, searchable, good, quality = read_preflight(paths, cfg)
    s["preflight"] = preflight
    save_json(args.output/"preflight.json", preflight)
    print("Eligibility:", json.dumps(preflight), flush=True)
    if not preflight["pass"]:
        raise ValueError("frozen eligibility failed before screening")
    cube, ap, time, cadence, old_good, flux, corrected_flux, meta = load_products(paths, cfg)
    with fits.open(paths["tp"], memmap=False) as tp, fits.open(paths["lc"], memmap=False) as lc:
        if tp[1].columns["FLUX_ERR"].unit != tp[1].columns["FLUX"].unit:
            raise ValueError("FLUX_ERR unit mismatch")
        errors = np.asarray(tp[1].data["FLUX_ERR"], dtype=float)
        positions = np.stack([tp[1].data["POS_CORR1"], tp[1].data["POS_CORR2"]], axis=1).astype(float)
        sap = np.asarray(lc[1].data["SAP_FLUX"], dtype=float)
        compare = good & np.isfinite(sap) & (sap != 0)
        difference = np.abs((corrected_flux[compare]-sap[compare])/sap[compare])
        if not len(difference) or np.median(difference) > 1e-4:
            raise ValueError("allowed-cadence SAP disagreement")
    if not np.all(np.isfinite(cube[good][:, ap])) or not np.all(np.isfinite(errors[good][:, ap]) & (errors[good][:, ap] > 0)):
        raise ValueError("nonfinite restored aperture or invalid archived errors")
    meta.update(legacy_strict_accepted_rows=meta["accepted_rows"], accepted_rows=int(good.sum()),
                accepted_cadence_days=preflight["accepted_cadence_days"],
                accepted_rows_with_aperture_correction=int(np.count_nonzero(good & (flux != corrected_flux))),
                allowed_cadence_sap_median_absolute_fraction=float(np.median(difference)), allowed_quality_bits=cfg["allowed_quality_bits"])
    s["metadata"] = meta; save_json(args.output/"metadata.json", meta)
    positive, noise, a = screen(flux, segments, cfg)
    negative, _, b = screen(flux, segments, cfg, sign=-1)
    cp, _, c = screen(corrected_flux, segments, cfg)
    cn, _, d = screen(corrected_flux, segments, cfg, sign=-1)
    native = sorted(positive+negative, key=lambda e: (e["start"], e["sign"]))
    annotate(native, cube, errors, ap, corrected_flux, time, quality, positions, segments, noise, cfg)
    for e in cp+cn:
        e["btjd_mid"] = float(np.mean(time[e["start"]:e["stop"]]))
    save_json(args.output/"restored_events.json", native)
    save_json(args.output/"corrected_events.json", sorted(cp+cn, key=lambda e: (e["start"], e["sign"])))
    save_json(args.output/"segments.json", noise)
    s["native"] = {"restored_positive": len(positive), "restored_negative": len(negative),
                   "restored_positive_spatial_pass": sum(e["spatial"]["pass"] for e in positive),
                   "restored_negative_spatial_pass": sum(e["spatial"]["pass"] for e in negative),
                   "corrected_positive": len(cp), "corrected_negative": len(cn), "event_cap_overflow": a or b or c or d}
    print("Native:", json.dumps(s["native"]), flush=True)
    rows = []
    half = cfg["injections"]["context_half_samples"]
    for anchor_id, anchor in enumerate(preflight["anchors"]):
        candidates = [n for n in noise if n["start"]+half <= anchor < n["stop"]-half]
        if len(candidates) != 1:
            raise ValueError("preflight anchor absent from a unique scored run")
        part = run_anchor(cube, errors, ap, time, anchor, anchor_id, candidates[0]["sigma_e_per_s"], cfg)
        rows.extend(part)
        save_json(args.output/"trials.json", rows)
        s["digital_trials_completed"] = len(rows)
        print(f"Completed anchor {anchor_id+1}/10; {len(rows)} trials", flush=True)
    recovery, gates = accounting(rows, cfg)
    gates.update(eligibility=preflight["pass"], no_event_overflow=not (a or b or c or d))
    s.update(recovery=recovery, qualification_gates=gates, qualification_pass=all(gates.values()), status="COMPLETED")
    s["geometry"] = {pair: {"fraction_within_one_stellar_radius": float(np.mean(distance <= 1)),
                           "cadence_days_within_one_stellar_radius": float(np.count_nonzero(distance <= 1)*20/86400)}
                     for pair, distance in geometry_diagnostic(time[searchable]+2457000, cfg["geometry"]).items()}
    figures(args.output, recovery["groups"], native, cube, ap, flux, corrected_flux, time, cfg)
    report(args.output, s)
    print("Qualification:", json.dumps({"pass": s["qualification_pass"], "gates": gates}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"results_ls7c_tess")
    parser.add_argument("--cache", type=Path, default=ROOT/"data_ls7c_tess")
    args = parser.parse_args()
    for line in (ROOT/"LS7C_FREEZE.sha256").read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        if sha256(ROOT/name) != expected:
            raise RuntimeError("freeze mismatch: "+name)
    if args.output.exists():
        raise RuntimeError("refusing to replace existing results")
    args.output.mkdir(parents=True); args.cache.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((ROOT/"config/ls7c_tess_l9859.json").read_text())
    s = {"schema": cfg["schema"], "run_utc": datetime.now(timezone.utc).isoformat(),
         "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
         "freeze_sha256": sha256(ROOT/"LS7C_FREEZE.sha256"), "digital_trials_completed": 0,
         "environment": {"python": platform.python_version(), **{p: importlib.metadata.version(p) for p in ("numpy", "scipy", "astropy", "matplotlib")}},
         "claim": "Finite digital engineering challenge; no candidate promotion or population limit"}
    error = None
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", RuntimeWarning)
        try:
            execute(args, cfg, s)
        except Exception as exc:
            error = exc
            s.update(status="NOT_QUALIFIED_INCOMPLETE", qualification_pass=False, error_type=type(exc).__name__, error=str(exc))
            (args.output/"REPORT.md").write_text("# LS7C: incomplete qualification\n\nThe frozen run stopped: "+str(exc)+".\n\nCompleted trials: "+str(s["digital_trials_completed"])+". Missing endpoints are not zero recovery. Preserve ledgers and inspect summary.json.\n")
    s["runtime_warnings"] = dict(Counter(str(w.message) for w in caught))
    save_json(args.output/"summary.json", s)
    seal(args.output)
    if error is not None:
        raise error


if __name__ == "__main__":
    main()
