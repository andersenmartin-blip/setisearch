#!/usr/bin/env python3
"""Execute the frozen LS7B sector 29 qualification, including structured failures."""
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

from ls7_tess_pilot import ROOT, load_products, retrieve, save_json, sha256, trial_summary
from seti_repeater.light_sail_tess import geometry_diagnostic, pixel_diagnostic, qualify_injections, screen
from seti_repeater.light_sail_tess_v2 import eligibility, extended_trials, quality_mask


def seal(output):
    for svg in output.glob("*.svg"):
        svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")
    files = sorted(p for p in output.iterdir() if p.is_file() and p.name != "SHA256SUMS")
    (output/"SHA256SUMS").write_text("".join(sha256(p)+"  "+p.name+"\n" for p in files))


def read_preflight(paths, cfg):
    with fits.open(paths["tp"], memmap=False) as tp, fits.open(paths["lc"], memmap=False) as lc:
        for hdus in (tp, lc):
            if hdus[0].header["TICID"] != cfg["tic"] or hdus[0].header["SECTOR"] != cfg["sector"]:
                raise ValueError("wrong preflight target/sector")
        t = np.asarray(tp[1].data["TIME"], dtype=float)
        c = np.asarray(tp[1].data["CADENCENO"], dtype=int)
        if not np.array_equal(c, lc[1].data["CADENCENO"]) or not np.allclose(t, lc[1].data["TIME"], atol=1e-7, rtol=0, equal_nan=True):
            raise ValueError("LC/TPF timing mismatch at eligibility preflight")
        q = np.asarray(tp[1].data["QUALITY"], dtype=int) | np.asarray(lc[1].data["QUALITY"], dtype=int)
        aperture = (tp["APERTURE"].data & 2) != 0
        finite = np.isfinite(t) & np.all(np.isfinite(tp[1].data["FLUX"][:, aperture]), axis=1)
        good = quality_mask(q, finite, cfg["allowed_quality_bits"])
        result, segments, searchable = eligibility(t, c, good, cfg)
        result["allowed_quality_bits"] = cfg["allowed_quality_bits"]
        result["accepted_quality_words"] = {str(k): int(v) for k,v in sorted(Counter(q[good].tolist()).items())}
    return result, segments, searchable, good, q


def annotate_events(events, cube, corrected, flux, corrected_flux, time, quality, positions, aperture, segments, noise, cfg):
    sigma_by_segment = {n["segment"]: n["sigma_e_per_s"] for n in noise}
    for e in events:
        lo, hi = e["start"], e["stop"]
        seg_lo, seg_hi = segments[e["segment"]]
        e["btjd_mid"] = float(np.mean(time[lo:hi]))
        e["bjd_tdb_mid"] = e["btjd_mid"] + 2457000
        e["quality_words"] = sorted(set(int(x) for x in quality[lo:hi]))
        e["morphology"] = pixel_diagnostic(cube[seg_lo:seg_hi], aperture, lo-seg_lo, hi-seg_lo, cfg["morphology"], e["sign"])
        e["corrected_morphology"] = pixel_diagnostic(corrected[seg_lo:seg_hi], aperture, lo-seg_lo, hi-seg_lo, cfg["morphology"], e["sign"])
        local = corrected_flux[lo-60:hi+60]
        baseline = median_filter(local, size=cfg["baseline_samples"], mode="nearest")
        e["corrected_score_same_window"] = float(e["sign"]*(local-baseline)[60:60+hi-lo].sum()/(sigma_by_segment[e["segment"]]*np.sqrt(hi-lo)))
        e["mean_restored_contribution_e_per_s"] = float(np.mean(flux[lo:hi]-corrected_flux[lo:hi]))
        side = np.r_[lo-60:lo-5, hi+5:hi+60]
        reference_flux = float(np.median(flux[side]))
        excess = e["morphology"].get("mean_excess_e_per_s")
        e["mean_excess_fraction"] = float(excess/reference_flux) if excess is not None and reference_flux > 0 else None
        deltas = []
        for component in positions.T:
            a, b = component[lo:hi], component[side]
            deltas.append(float(np.mean(a)-np.median(b)) if np.all(np.isfinite(a)) and np.all(np.isfinite(b)) else None)
        e["pointing_proxy_delta_xy_pixels"] = deltas
        e["pair_separation_stellar_radii"] = {k: float(v) for k,v in geometry_diagnostic(e["bjd_tdb_mid"], cfg["geometry"]).items()}


def summarize(base, extra, cfg, overflow):
    result = trial_summary(base, cfg)
    shifted = [r for r in extra if r["kind"] == "off_profile"]
    nuisance = [r for r in base+extra if r["kind"] in ("single_pixel", "uniform", "pointing")]
    by_kind = {kind: {"trials": sum(r["kind"]==kind for r in nuisance), "accepted": sum(r["kind"]==kind and r["accepted"] for r in nuisance)} for kind in ("single_pixel", "uniform", "pointing")}
    null = [r for r in base if r["kind"] == "null"]
    result.update(total_trials=len(base)+len(extra), off_profile_trials=len(shifted), off_profile_recovered=sum(r["recovered"] for r in shifted),
                  off_profile_confounded=sum(r["baseline_confounded"] for r in shifted), nuisance_by_kind=by_kind,
                  nuisance_trials=len(nuisance), nuisance_accepted=sum(r["accepted"] for r in nuisance),
                  nuisance_acceptance_fraction=sum(r["accepted"] for r in nuisance)/len(nuisance),
                  null_accepted=sum(r["accepted"] for r in null))
    q = cfg["qualification"]
    gates = {"bright_single_recovery": result["bright_single_recovery_fraction"] >= q["bright_single_pulse_recovery_min"],
             "off_profile_recovery": result["off_profile_recovered"]/len(shifted) >= q["off_profile_recovery_min"],
             "null_acceptance": result["null_accepted"] <= q["null_accepted_max"],
             "baseline_confounding": result["stellar_confounded_fraction"] <= q["confounded_fraction_max"],
             "no_event_overflow": not overflow}
    for kind, group in by_kind.items():
        gates[kind+"_acceptance"] = group["accepted"]/group["trials"] <= q["nuisance_acceptance_max_per_kind"]
    return result, gates


def figures(output, summary, positive, cube, aperture, flux, corrected_flux, time, cfg):
    recovery = summary["recovery"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), layout="constrained")
    for shape in cfg["injections"]["shapes"]:
        rows = [r for r in recovery["groups"] if r["shape"]==shape]
        axes[0].plot([100*r["amplitude_fraction"] for r in rows], [r["recovered"]/r["trials"] for r in rows], "o-", label=shape)
    axes[0].plot([1.], [recovery["off_profile_recovered"]/recovery["off_profile_trials"]], "kx", markersize=10, label="shifted profile, 30 s")
    axes[0].set(xscale="log", xlabel="Added aperture flux (%)", ylabel="Digital recovery fraction", ylim=(-.03, 1.05), title="L 98-59 · sector 29")
    axes[0].legend(fontsize=8)
    groups = recovery["nuisance_by_kind"]
    axes[1].bar(list(groups), [g["accepted"]/g["trials"] for g in groups.values()], color="#657e97")
    axes[1].axhline(.05, color="black", linestyle="--")
    axes[1].set(ylim=(0, 1.05), ylabel="Control acceptance fraction", title="Separate 5% acceptance limits")
    fig.suptitle("420 post-processing trials on ten backgrounds; not total sky completeness", fontsize=11)
    fig.savefig(output/"qualification.svg")
    fig.savefig(output/"qualification.png", dpi=150)
    plt.close(fig)
    ordered = sorted(positive, key=lambda e: (-e["score"], e["start"]))
    selected = [e for e in ordered if e["morphology"]["pass"]][:cfg["native_review"]["passing_events"]]
    selected += [e for e in ordered if not e["morphology"]["pass"]][:cfg["native_review"]["failing_events"]]
    save_json(output/"native_review_selection.json", selected)
    if not selected:
        return
    fig, axes = plt.subplots(len(selected), 2, figsize=(11, 2.6*len(selected)), squeeze=False, layout="constrained")
    for row, e in enumerate(selected):
        lo, hi = e["start"], e["stop"]
        plot_lo, plot_hi = lo-cfg["native_review"]["plot_half_samples"], hi+cfg["native_review"]["plot_half_samples"]
        t = (time[plot_lo:plot_hi]-e["btjd_mid"])*86400
        norm = np.median(corrected_flux[plot_lo:plot_hi])
        axes[row, 0].plot(t, 100*(flux[plot_lo:plot_hi]/norm-1), ".-", label="restored", lw=.7, ms=2)
        axes[row, 0].plot(t, 100*(corrected_flux[plot_lo:plot_hi]/norm-1), ".-", label="corrected", lw=.7, ms=2)
        axes[row, 0].axvspan((time[lo]-e["btjd_mid"])*86400-10, (time[hi-1]-e["btjd_mid"])*86400+10, alpha=.12, color="black")
        axes[row, 0].set(xlabel="Seconds from window midpoint", ylabel="Relative flux (%)", title=f"BTJD {e['btjd_mid']:.6f}; score {e['score']:.1f}; pixel pass {e['morphology']['pass']}")
        axes[row, 0].legend(fontsize=7)
        side = np.r_[lo-60:lo-5, hi+5:hi+60]
        delta = np.nanmean(cube[lo:hi], axis=0)-np.nanmedian(cube[side], axis=0)
        limit = float(np.nanmax(np.abs(delta))) or 1.0
        im = axes[row, 1].imshow(delta, origin="lower", cmap="RdBu_r", vmin=-limit, vmax=limit)
        axes[row, 1].contour(aperture, levels=[.5], colors="black", linewidths=.6)
        axes[row, 1].set(title="Restored excess image (electrons/s)", xlabel="Stamp column", ylabel="Stamp row")
        fig.colorbar(im, ax=axes[row, 1], shrink=.8)
    fig.savefig(output/"native_review.png", dpi=130)
    plt.close(fig)


def write_report(output, s):
    m, r, p = s["metadata"], s["recovery"], s["preflight"]
    text = ["# LS7B: L 98-59 TESS sector 29 qualification", "", "Run: "+s["run_utc"], "",
            "**Restricted digital qualification: "+("PASS" if s["qualification_pass"] else "FAIL")+".** No event is promoted as a light-sail candidate.", "",
            f"Public TESS/SPOC 20-second products, TIC {m['tic']}, sector {m['sector']}: {m['date_obs_utc']} to {m['date_end_utc']} UTC. Nominal band 600–1000 nm.", "",
            f"Explicitly allowing only quality bits 64/1024 retains {p['accepted_cadence_days']:.4f} cadence-days; {p['searchable_cadence_days']:.4f} cadence-days remain after run and edge guards. Ten nonoverlapping 401-sample backgrounds span {p['anchor_span_days']:.3f} days. Coverage is summed cadence duration, not exact photon live time.", "",
            f"The frozen method executed **{r['total_trials']} digital trials**: 240 baseline signals, 80 displaced-profile signals, 80 instrumental controls and 20 unchanged controls. Bright single pulses recovered: **{r['bright_single_recovered']}/{r['bright_single_trials']}** at 1% added aperture flux. Displaced-profile recovery: **{r['off_profile_recovered']}/{r['off_profile_trials']}**. Instrumental controls accepted: **{r['nuisance_accepted']}/{r['nuisance_trials']}**; unchanged controls accepted: **{r['null_accepted']}/{r['null_trials']}**.", "",
            "| Baseline pulse | Added flux | Recovered / trials | Screen detections | Confounded |", "|---|---:|---:|---:|---:|"]
    for g in r["groups"]:
        text.append(f"| {g['shape']} | {100*g['amplitude_fraction']:g}% | {g['recovered']}/{g['trials']} | {g['screen_detected']} | {g['confounded']} |")
    text += ["", "## Frozen gates", "", "| Gate | Passed |", "|---|---|"]
    for name, passed in s["qualification_gates"].items():
        text.append(f"| {name} | {passed} |")
    text += ["", "Per-class instrumental controls:", ""]
    for kind, g in r["nuisance_by_kind"].items():
        text.append(f"- {kind}: {g['accepted']}/{g['trials']} accepted.")
    text += ["", "The baseline and extra trials share ten backgrounds. Noise, quality selection, and mission processing precede digital injection. Shifted profiles and two simple pointing motions are limited models. These results do not measure hardware/SPOC survival, complete transient sensitivity, all kinds of interference, or a physical population limit.", "",
             "![Digital qualification](qualification.svg)", "", "## Native screening", "",
             f"Restored screen: {s['native']['restored_positive']} positive and {s['native']['restored_negative']} negative events; {s['native']['restored_positive_pixel_pass']} positive events pass the provisional pixel screen. Corrected diagnostic screen: {s['native']['corrected_positive']} positive and {s['native']['corrected_negative']} negative events. Counts may differ because correction and robust noise both affect screening; same-window corrected scores are also recorded.", "",
             "All retained events are in the ledgers. The fixed visual review selects the strongest six positive pixel passes and four positive failures, when available. A pixel pass does not distinguish every stellar flare, unresolved source or instrumental fluctuation from an artificial transient. No retrospective veto changes a gate or event count.", "",
             "[Native review selection](native_review_selection.json) and [time/excess-image figure](native_review.png).", "",
             "## Geometry and LS1 comparison", "",
             "The unchanged circular, edge-on, common-node approximation gives these fractions of searched cadence centers within one stellar radius in projected pair separation:", ""]
    for pair, g in s["geometry"].items():
        text.append(f"- {pair}: {100*g['fraction_within_one_stellar_radius']:.3f}% ({g['cadence_days_within_one_stellar_radius']:.5f} cadence-days).")
    text += ["", "Geometry uses BJD_TDB and the existing LS3 ephemerides without inclination, nodal or ephemeris uncertainty. It did not select windows or promote an event and does not predict beam interception. This red-optical short-transient experiment complements LS1's radio work; it has separate sensitivity and exposure denominators. TESS supplies one broad band and cannot establish a narrow laser spectrum. A narrow 1.06-micron beam lies outside the nominal band.", "",
             "## Provenance and continuation", "",
             "The method was fixed and published before opening sector 29. Sector 28 remains closed development evidence with its original failure unchanged. No threshold, anchor, amplitude or quality mask was retuned after this evaluation. Later interpretation of native plots is explicitly retrospective and will be reported separately from the fixed ledgers.", "",
             "Code commit: `"+s["code_commit"]+"`. Freeze SHA-256: `"+s["freeze_sha256"]+"`.", "",
             "- [Frozen protocol](../LS7B_TESS_PROTOCOL.md)", "- [Full summary and environment](summary.json)",
             "- [Source identities](source_manifest.json)", "- [Eligibility preflight](preflight.json)",
             "- [Baseline trials](baseline_trials.json)", "- [Additional trials](extended_trials.json)",
             "- [Restored native ledger](restored_events.json)", "- [Corrected native ledger](corrected_events.json)",
             "- [Output checksums](SHA256SUMS)", "",
             "Processing references: [MAST flags](https://outerspace.stsci.edu/spaces/TESS/pages/14563420/2.0%2B-%2BData%2BProduct%2BOverview), [NASA TESS cosmic-ray processing](https://heasarc.gsfc.nasa.gov/docs/tess/TESS-CosmicRayPrimer.html)."]
    (output/"REPORT.md").write_text("\n".join(text)+"\n")


def execute(args, cfg, summary):
    paths, manifest = {}, []
    for product in cfg["products"]:
        paths[product["kind"]], record = retrieve(product, args.cache)
        manifest.append(record)
    save_json(args.output/"source_manifest.json", {"retrieved_utc": datetime.now(timezone.utc).isoformat(), "products": manifest})
    preflight, segments, searchable, good, quality = read_preflight(paths, cfg)
    summary["preflight"] = preflight
    save_json(args.output/"preflight.json", preflight)
    print("Eligibility:", json.dumps(preflight), flush=True)
    if not preflight["pass"]:
        raise ValueError("frozen data eligibility failed before screening")
    cube, ap, time, cadence, old_good, flux, corrected_flux, meta = load_products(paths, cfg)
    if not np.all(np.isfinite(cube[good][:, ap])):
        raise ValueError("restoration changed aperture finiteness")
    meta["legacy_strict_accepted_rows"] = meta["accepted_rows"]
    meta["accepted_rows"] = int(good.sum())
    meta["accepted_cadence_days"] = preflight["accepted_cadence_days"]
    meta["accepted_rows_with_aperture_correction"] = int(np.count_nonzero(good & (flux != corrected_flux)))
    meta["allowed_quality_bits"] = cfg["allowed_quality_bits"]
    with fits.open(paths["tp"], memmap=False) as tp, fits.open(paths["lc"], memmap=False) as lc:
        corrected = np.array(tp[1].data["FLUX"], dtype=float, copy=True)
        positions = np.stack([tp[1].data["POS_CORR1"], tp[1].data["POS_CORR2"]], axis=1).astype(float)
        sap = np.asarray(lc[1].data["SAP_FLUX"], dtype=float)
        compare = good & np.isfinite(sap) & (sap != 0)
        difference = np.abs((corrected_flux[compare]-sap[compare])/sap[compare])
        if not len(difference) or np.median(difference) > 1e-4:
            raise ValueError("new allowed cadences disagree with SAP aperture sum")
        meta["allowed_cadence_sap_median_absolute_fraction"] = float(np.median(difference))
    summary["metadata"] = meta
    save_json(args.output/"metadata.json", meta)
    positive, noise, a = screen(flux, segments, cfg)
    negative, _, b = screen(flux, segments, cfg, sign=-1)
    cp, _, c = screen(corrected_flux, segments, cfg)
    cn, _, d = screen(corrected_flux, segments, cfg, sign=-1)
    annotate_events(positive+negative, cube, corrected, flux, corrected_flux, time, quality, positions, ap, segments, noise, cfg)
    for e in cp+cn:
        e["btjd_mid"] = float(np.mean(time[e["start"]:e["stop"]]))
    save_json(args.output/"restored_events.json", sorted(positive+negative, key=lambda e:e["start"]))
    save_json(args.output/"corrected_events.json", sorted(cp+cn, key=lambda e:e["start"]))
    save_json(args.output/"segments.json", noise)
    summary["native"] = {"restored_positive":len(positive), "restored_negative":len(negative), "restored_positive_pixel_pass":sum(e["morphology"]["pass"] for e in positive), "corrected_positive":len(cp), "corrected_negative":len(cn), "event_cap_overflow":a or b or c or d}
    print("Native screening:", json.dumps(summary["native"]), flush=True)
    base = qualify_injections(cube, ap, time, noise, cfg)
    actual_anchors = sorted({r["native_index"] for r in base})
    if actual_anchors != preflight["anchors"]:
        raise ValueError("injection anchors changed after preflight")
    save_json(args.output/"baseline_trials.json", base)
    summary["digital_trials_completed"] = len(base)
    extra = extended_trials(cube, ap, time, noise, actual_anchors, cfg)
    save_json(args.output/"extended_trials.json", extra)
    summary["digital_trials_completed"] += len(extra)
    recovery, gates = summarize(base, extra, cfg, a or b or c or d)
    gates["eligibility"] = preflight["pass"]
    summary.update(recovery=recovery, qualification_gates=gates, qualification_pass=all(gates.values()), status="COMPLETED")
    summary["geometry"] = {pair:{"fraction_within_one_stellar_radius":float(np.mean(distance<=1)), "cadence_days_within_one_stellar_radius":float(np.count_nonzero(distance<=1)*20/86400)} for pair,distance in geometry_diagnostic(time[searchable]+2457000, cfg["geometry"]).items()}
    figures(args.output, summary, positive, cube, ap, flux, corrected_flux, time, cfg)
    write_report(args.output, summary)
    print("Qualification:", json.dumps({"pass":summary["qualification_pass"], "gates":gates, "bright_recovered":recovery["bright_single_recovered"], "shifted_recovered":recovery["off_profile_recovered"], "controls_accepted":recovery["nuisance_accepted"]}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"results_ls7b_tess")
    parser.add_argument("--cache", type=Path, default=ROOT/"data_ls7b_tess")
    args = parser.parse_args()
    for line in (ROOT/"LS7B_FREEZE.sha256").read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        if sha256(ROOT/name) != expected:
            raise RuntimeError("freeze mismatch: "+name)
    if args.output.exists():
        raise RuntimeError("refusing to replace existing results")
    args.output.mkdir(parents=True)
    args.cache.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((ROOT/"config/ls7b_tess_l9859.json").read_text())
    summary = {"schema":cfg["schema"], "run_utc":datetime.now(timezone.utc).isoformat(),
               "code_commit":subprocess.check_output(["git","rev-parse","HEAD"], cwd=ROOT, text=True).strip(),
               "freeze_sha256":sha256(ROOT/"LS7B_FREEZE.sha256"), "digital_trials_completed":0,
               "environment":{"python":platform.python_version(), **{p:importlib.metadata.version(p) for p in ("numpy","scipy","astropy","matplotlib")}},
               "claim":"Restricted engineering qualification; no LS candidate promotion or population limit"}
    error = None
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", RuntimeWarning)
        try:
            execute(args, cfg, summary)
        except Exception as exc:
            error = exc
            summary.update(status="NOT_QUALIFIED_INCOMPLETE", qualification_pass=False, error_type=type(exc).__name__, error=str(exc))
            (args.output/"REPORT.md").write_text("# LS7B: incomplete qualification\n\nThe frozen run stopped: "+str(exc)+".\n\nCompleted digital trials: "+str(summary["digital_trials_completed"])+". Missing endpoints are not zero recovery. See summary.json and the preserved ledgers.\n")
    summary["runtime_warnings"] = dict(Counter(str(w.message) for w in caught))
    save_json(args.output/"summary.json", summary)
    seal(args.output)
    if error is not None:
        raise error


if __name__ == "__main__":
    main()
