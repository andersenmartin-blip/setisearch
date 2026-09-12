#!/usr/bin/env python3
"""Run the frozen, one-sector LS7 pilot; raw FITS are never committed."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import urllib.parse
import urllib.request
import warnings

from astropy.io import fits
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from seti_repeater.light_sail_tess import (
    geometry_diagnostic, good_segments, pixel_diagnostic, qualify_injections,
    restore_cosmic_rays, screen,
)

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def verify_freeze():
    for line in (ROOT / "LS7_FREEZE.sha256").read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        if sha256(ROOT / name) != expected:
            raise RuntimeError("freeze mismatch: " + name)


def retrieve(product, cache):
    path = cache / product["name"]
    url = "https://mast.stsci.edu/api/v0.1/Download/file?" + urllib.parse.urlencode({"uri": "mast:TESS/product/" + product["name"]})
    if not path.exists():
        temp = path.with_suffix(".download")
        print("Downloading", product["name"], flush=True)
        size = 0
        with urllib.request.urlopen(url, timeout=120) as response, temp.open("wb") as dest:
            if response.status != 200:
                raise RuntimeError("expected a complete HTTP 200 product")
            for block in iter(lambda: response.read(1024 * 1024), b""):
                size += len(block)
                if size > product["bytes"]:
                    raise RuntimeError("archive product exceeds frozen byte count")
                dest.write(block)
        if size != product["bytes"]:
            raise RuntimeError("archive product is incomplete or changed")
        temp.rename(path)
    if path.stat().st_size != product["bytes"]:
        raise RuntimeError("cached product byte count mismatch")
    return path, {**product, "url": url, "sha256": sha256(path)}


def load_products(paths, cfg):
    with fits.open(paths["tp"], memmap=False) as tp, fits.open(paths["lc"], memmap=False) as lc:
        tp.verify("exception")
        lc.verify("exception")
        for hdus in (tp, lc):
            if hdus[0].header["TICID"] != cfg["tic"] or hdus[0].header["SECTOR"] != cfg["sector"]:
                raise ValueError("wrong target or sector")
            if hdus[1].header["TIMESYS"] != "TDB" or not np.isclose(hdus[1].header["TIMEDEL"] * 86400, cfg["cadence_seconds"], rtol=1e-6):
                raise ValueError("wrong time system or sampling")
        table, lt = tp[1].data, lc[1].data
        cadence = np.asarray(table["CADENCENO"], dtype=int)
        if not np.array_equal(cadence, lt["CADENCENO"]):
            raise ValueError("LC/TPF cadence IDs do not match")
        time = np.asarray(table["TIME"], dtype=float)
        if not np.allclose(time, lt["TIME"], atol=1e-7, rtol=0, equal_nan=True):
            raise ValueError("LC/TPF times do not match")
        reference = tp[1].header["BJDREFI"] + tp[1].header.get("BJDREFF", 0)
        lc_reference = lc[1].header["BJDREFI"] + lc[1].header.get("BJDREFF", 0)
        if reference != 2457000 or lc_reference != reference:
            raise ValueError("unexpected BTJD reference")
        cr = tp["TARGET COSMIC RAY"]
        flux_unit = tp[1].columns["FLUX"].unit
        if flux_unit != cr.columns["COSMIC_RAY"].unit or flux_unit not in ("e-/s", "electron/s", "electrons/s"):
            raise ValueError("unverified cosmic-ray/flux units: " + str((flux_unit, cr.columns["COSMIC_RAY"].unit)))
        aperture = (tp["APERTURE"].data & 2) != 0
        if not np.any(aperture):
            raise ValueError("empty optimal aperture")
        corrected = np.asarray(table["FLUX"], dtype=float)
        restored, cr_info = restore_cosmic_rays(corrected, cadence, cr.data, int(tp[1].header["1CRV5P"]), int(tp[1].header["2CRV5P"]))
        quality = np.asarray(table["QUALITY"], dtype=np.int64) | np.asarray(lt["QUALITY"], dtype=np.int64)
        good = (quality == cfg["quality_value"]) & np.isfinite(time) & np.all(np.isfinite(restored[:, aperture]), axis=1)
        native_flux = restored[:, aperture].sum(axis=1)
        corrected_flux = corrected[:, aperture].sum(axis=1)
        sap = np.asarray(lt["SAP_FLUX"], dtype=float)
        comparable = good & np.isfinite(sap)
        if not np.any(comparable):
            raise ValueError("no comparable SAP data")
        relative_difference = (corrected_flux[comparable] - sap[comparable]) / sap[comparable]
        # Structural cross-check, not a fitted calibration; tolerates FITS rounding.
        if np.median(np.abs(relative_difference)) > 1e-4:
            raise ValueError("aperture sum disagrees with SPOC SAP")
        metadata = {"tic": cfg["tic"], "sector": cfg["sector"], "date_obs_utc": tp[1].header.get("DATE-OBS", tp[0].header.get("DATE-OBS")),
                    "date_end_utc": tp[1].header.get("DATE-END", tp[0].header.get("DATE-END")), "bjd_reference": reference,
                    "tstart_btjd": float(tp[1].header["TSTART"]), "tstop_btjd": float(tp[1].header["TSTOP"]),
                    "cadence_seconds": cfg["cadence_seconds"], "flux_unit": flux_unit,
                    "stamp_shape": list(aperture.shape), "aperture_pixels": int(aperture.sum()),
                    "rows": len(time), "quality_zero_rows": int(np.count_nonzero(quality == 0)),
                    "quality_histogram": {str(k): int(v) for k, v in sorted(Counter(quality.tolist()).items())},
                    "accepted_rows": int(good.sum()), "accepted_cadence_days": float(good.sum() * cfg["cadence_seconds"] / 86400),
                    "cosmic_ray_restoration": cr_info,
                    "accepted_rows_with_aperture_correction": int(np.count_nonzero(good & (native_flux != corrected_flux))),
                    "sap_comparison_median_absolute_fraction": float(np.median(np.abs(relative_difference)))}
    return restored, aperture, time, cadence, good, native_flux, corrected_flux, metadata


def trial_summary(trials, cfg):
    stellar = [r for r in trials if r["kind"] == "stellar"]
    bright = [r for r in stellar if r["amplitude_fraction"] == .01 and r["shape"] != "doublet30sep87"]
    nuisance = [r for r in trials if r["kind"] in ("single_pixel", "uniform")]
    null = [r for r in trials if r["kind"] == "null"]
    groups = []
    for shape in cfg["injections"]["shapes"]:
        for amp in cfg["injections"]["amplitudes"]:
            selected = [r for r in stellar if r["shape"] == shape and r["amplitude_fraction"] == amp]
            groups.append({"shape": shape, "amplitude_fraction": amp, "trials": len(selected),
                           "screen_detected": sum(r["screen_detected"] for r in selected),
                           "recovered": sum(r["recovered"] for r in selected),
                           "confounded": sum(r["baseline_confounded"] for r in selected)})
    return {"total_trials": len(trials), "stellar_trials": len(stellar), "groups": groups,
            "bright_single_trials": len(bright), "bright_single_recovered": sum(r["recovered"] for r in bright),
            "bright_single_recovery_fraction": sum(r["recovered"] for r in bright) / len(bright),
            "nuisance_trials": len(nuisance), "nuisance_accepted": sum(r["accepted"] for r in nuisance),
            "nuisance_acceptance_fraction": sum(r["accepted"] for r in nuisance) / len(nuisance),
            "nuisance_by_kind": {kind: {"trials": sum(r["kind"] == kind for r in nuisance), "accepted": sum(r["accepted"] and r["kind"] == kind for r in nuisance)} for kind in ("single_pixel", "uniform")},
            "null_trials": len(null), "null_screen_detections": sum(r["screen_detected"] for r in null),
            "stellar_confounded": sum(r["baseline_confounded"] for r in stellar),
            "stellar_confounded_fraction": sum(r["baseline_confounded"] for r in stellar) / len(stellar)}


def write_report(output, summary):
    meta, recovery = summary["metadata"], summary["recovery"]
    text = ["# LS7: L 98-59 TESS pilot result", "", "Run: " + summary["run_utc"], "",
            "**Engineering qualification: " + ("PASS" if summary["qualification_pass"] else "FAIL") + ".** No event is promoted as a light-sail candidate.", "",
            f"TIC {meta['tic']}, sector {meta['sector']}; {meta['date_obs_utc']} to {meta['date_end_utc']} UTC; 20-second SPOC target pixels, nominal 600–1000 nm.", "",
            f"Accepted {meta['accepted_rows']:,} / {meta['rows']:,} rows ({meta['accepted_cadence_days']:.4f} cadence-days). After run-length and edge guards, {summary['searchable_rows']:,} cadence centers ({summary['searchable_cadence_days']:.4f} cadence-days) remain. These are cadence-coverage denominators, not wall-clock span or exact photon live time.", "",
            f"Restored {meta['cosmic_ray_restoration']['applied_records']:,} archived ground cosmic-ray corrections; {meta['accepted_rows_with_aperture_correction']:,} accepted aperture sums changed. Median absolute difference between corrected aperture sum and SAP: {meta['sap_comparison_median_absolute_fraction']:.3g} of SAP.", "",
            "## Digital qualification", "",
            f"Bright single pulses: **{recovery['bright_single_recovered']}/{recovery['bright_single_trials']}** recovered at 1% added aperture flux (required >=90%). Nuisance acceptance: **{recovery['nuisance_accepted']}/{recovery['nuisance_trials']}** (required <=5%). Baseline-confounded stellar trials: {recovery['stellar_confounded']}/{recovery['stellar_trials']} (required <=20%).", "",
            "| Injected shape | Added flux | Recovered / trials | Screen detections | Confounded |",
            "|---|---:|---:|---:|---:|"]
    for g in recovery["groups"]:
        text.append(f"| {g['shape']} | {100*g['amplitude_fraction']:g}% | {g['recovered']}/{g['trials']} | {g['screen_detected']} | {g['confounded']} |")
    text += ["", "These are 240 digital stellar-profile injections, 40 nuisance controls and 20 unchanged controls at 10 time/quality-selected anchors. Trials share backgrounds and are not 300 independent sky observations. Injections occur after mission processing and quality masking, using the measured aperture profile and continuous 20-second bins. They do not establish total astrophysical completeness, laser sensitivity or a population limit.", "",
             "## Native screening and geometry", "",
             f"Retained positive triggers: {summary['positive_events']}; negative triggers: {summary['negative_events']}. Positive triggers passing the provisional pixel screen: {summary['positive_morphology_pass']}. Event-cap overflow: {summary['event_cap_overflow']}. Scores are screening statistics, not discovery significance. Native stellar flares and unresolved contamination require separate validation even if pixel morphology passes.", "",
             "The frozen circular, edge-on, common-node approximation gives the following fraction of searched cadence centers within one stellar radius in projected pair separation:", ""]
    for pair, g in summary["geometry"].items():
        text.append(f"- {pair}: {100*g['fraction_within_one_stellar_radius']:.3f}% ({g['cadence_days_within_one_stellar_radius']:.5f} cadence-days).")
    text += ["", "This is descriptive geometry without inclination, nodal or ephemeris uncertainty; it is not a prediction of a beam reaching Earth. No geometry window was used to select or promote a trigger.", "",
             "## Scope and next decision", "",
             "This red-optical, 30–100-second qualification complements LS1's radio search with a different target, band and instrumental system. TESS has one broad photometric band; a narrow 1.06-micron beam lies outside its nominal band. No null result about extraterrestrial propulsion follows from this engineering experiment.", "",
             "Keep all other TESS sectors unopened until the present qualification and native contaminants have been reviewed. Any revised method requires a separate freeze and evaluation on an unopened sector. No threshold was adjusted after opening these data.", "",
             "## Reproduction and provenance", "",
             "- [Frozen protocol](../LS7_TESS_L9859_PROTOCOL.md)",
             "- [Summary and gates](summary.json)", "- [All digital trials](injection_trials.json)",
             "- [Native event ledger](native_events.json)", "- [Source manifest](source_manifest.json)",
             "- [Figure](qualification.svg)", "- [Output checksums](SHA256SUMS)", "",
             "Code commit at execution: `" + summary["code_commit"] + "`. Freeze SHA-256: `" + summary["freeze_sha256"] + "`.", "",
             "Processing references: [NASA TESS products](https://heasarc.gsfc.nasa.gov/docs/tess/data-products.html), [NASA cosmic-ray primer](https://heasarc.gsfc.nasa.gov/docs/tess/TESS-CosmicRayPrimer.html). The exact MAST URLs and input hashes are in the source manifest."]
    (output / "REPORT.md").write_text("\n".join(text) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results_ls7_tess")
    parser.add_argument("--cache", type=Path, default=ROOT / "data_ls7_tess")
    args = parser.parse_args()
    verify_freeze()
    if args.output.exists():
        raise RuntimeError("refusing to overwrite existing results; use another --output")
    cfg = json.loads((ROOT / "config/ls7_tess_l9859.json").read_text())
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True)
    run_utc = datetime.now(timezone.utc).isoformat()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    paths, manifest = {}, []
    for product in cfg["products"]:
        paths[product["kind"]], record = retrieve(product, args.cache)
        manifest.append(record)
    save_json(args.output / "source_manifest.json", {"retrieved_utc": datetime.now(timezone.utc).isoformat(), "products": manifest})
    print("Reading validated products", flush=True)
    cube, aperture, time, cadence, good, flux, corrected, metadata = load_products(paths, cfg)
    save_json(args.output / "metadata.json", metadata)
    segments = good_segments(time, cadence, good, cfg["cadence_seconds"])
    positive, noise, over_pos = screen(flux, segments, cfg)
    negative, _, over_neg = screen(flux, segments, cfg, sign=-1)
    searchable = np.zeros(len(time), dtype=bool)
    for n in noise:
        searchable[n["start"] + cfg["baseline_samples"] // 2:n["stop"] - cfg["baseline_samples"] // 2] = True
    if not np.any(searchable):
        raise ValueError("no searchable cadence centers")
    events = positive + negative
    for event in events:
        lo, hi = event["start"], event["stop"]
        event["btjd_mid"] = float(np.mean(time[lo:hi]))
        event["bjd_tdb_mid"] = event["btjd_mid"] + metadata["bjd_reference"]
        # Restrict sidebands to the same unbroken run.
        seg_lo, seg_hi = segments[event["segment"]]
        event["morphology"] = pixel_diagnostic(cube[seg_lo:seg_hi], aperture, lo - seg_lo, hi - seg_lo, cfg["morphology"], event["sign"])
        event["restored_minus_corrected_mean_e_per_s"] = float(np.mean(flux[lo:hi] - corrected[lo:hi]))
        event["pair_separation_stellar_radii"] = {k: float(v) for k, v in geometry_diagnostic(event["bjd_tdb_mid"], cfg["geometry"]).items()}
    save_json(args.output / "native_events.json", sorted(events, key=lambda e: e["start"]))
    save_json(args.output / "segments.json", noise)
    print("Digital injections and nuisance controls", flush=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", RuntimeWarning)
        trials = qualify_injections(cube, aperture, time, noise, cfg)
    save_json(args.output / "injection_trials.json", trials)
    recovery = trial_summary(trials, cfg)
    gates = {"bright_single_recovery": recovery["bright_single_recovery_fraction"] >= cfg["qualification"]["bright_single_pulse_recovery_min"],
             "nuisance_acceptance": recovery["nuisance_acceptance_fraction"] <= cfg["qualification"]["nuisance_acceptance_max"],
             "confounded_fraction": recovery["stellar_confounded_fraction"] <= cfg["qualification"]["confounded_fraction_max"],
             "no_event_cap_overflow": not (over_pos or over_neg)}
    geometry = {pair: {"fraction_within_one_stellar_radius": float(np.mean(distance <= 1)),
                       "cadence_days_within_one_stellar_radius": float(np.count_nonzero(distance <= 1) * cfg["cadence_seconds"] / 86400)}
                for pair, distance in geometry_diagnostic(time[searchable] + metadata["bjd_reference"], cfg["geometry"]).items()}
    summary = {"schema": cfg["schema"], "run_utc": run_utc, "code_commit": commit,
               "freeze_sha256": sha256(ROOT / "LS7_FREEZE.sha256"), "metadata": metadata,
               "environment": {"python": platform.python_version(), **{p: importlib.metadata.version(p) for p in ("numpy", "scipy", "astropy", "matplotlib")}},
               "searchable_rows": int(searchable.sum()), "searchable_cadence_days": float(searchable.sum() * cfg["cadence_seconds"] / 86400),
               "positive_events": len(positive), "negative_events": len(negative),
               "positive_morphology_pass": sum(e["morphology"]["pass"] for e in positive),
               "event_cap_overflow": over_pos or over_neg, "recovery": recovery, "geometry": geometry,
               "qualification_gates": gates, "qualification_pass": all(gates.values()),
               "injection_runtime_warnings": dict(Counter(str(w.message) for w in caught)),
               "claim": "engineering_qualification_only_no_LS_candidate_promotion"}
    save_json(args.output / "summary.json", summary)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")
    for shape in cfg["injections"]["shapes"]:
        group = [g for g in recovery["groups"] if g["shape"] == shape]
        axes[0].plot([100*g["amplitude_fraction"] for g in group], [g["recovered"]/g["trials"] for g in group], "o-", label=shape)
    axes[0].set(xlabel="Added aperture flux (%)", ylabel="Digital recovery fraction", ylim=(-.03, 1.05), xscale="log", title="L 98-59 · TESS sector 28")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=.2)
    kinds = ["single_pixel", "uniform"]
    axes[1].bar(["Single pixel", "Uniform stamp"], [recovery["nuisance_by_kind"][k]["accepted"] / recovery["nuisance_by_kind"][k]["trials"] for k in kinds], color=["#ab5b37", "#536b87"])
    axes[1].axhline(.05, linestyle="--", color="black", label="Gate: <=5% overall")
    axes[1].set(ylabel="Nuisance acceptance fraction", ylim=(0, 1.05), title="20 trials per nuisance type")
    axes[1].legend(fontsize=8)
    fig.suptitle("Post-processing injections; not total astrophysical completeness", fontsize=11)
    fig.savefig(args.output / "qualification.svg")
    fig.savefig(args.output / "qualification.png", dpi=150)
    plt.close(fig)
    write_report(args.output, summary)
    output_files = sorted(p for p in args.output.iterdir() if p.is_file())
    (args.output / "SHA256SUMS").write_text("".join(sha256(p) + "  " + p.name + "\n" for p in output_files))
    print(json.dumps({"qualification_pass": summary["qualification_pass"], "gates": gates,
                      "bright_recovered": recovery["bright_single_recovered"], "bright_total": recovery["bright_single_trials"],
                      "nuisance_accepted": recovery["nuisance_accepted"], "positive_events": len(positive),
                      "positive_morphology_pass": summary["positive_morphology_pass"], "output": str(args.output)}, indent=2), flush=True)


if __name__ == "__main__":
    main()
