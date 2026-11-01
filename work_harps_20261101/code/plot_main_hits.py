#!/usr/bin/env python3
"""Plot all ten preserved production hits and initialize unreviewed dispositions.

Uses measured calibrated-spectrum FLUX in uncalibrated ADU; no synthetic signal,
raw-image retrieval, origin classification, or detector-parameter change.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter, MaxNLocator
import numpy as np

from harps_detector import analyze_arrays, read_spectrum


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--production", type=Path, default=Path("production"))
    args = parser.parse_args()
    root = args.project_root.resolve()
    production = args.production if args.production.is_absolute() else root / args.production
    hit_path = production / "PRELIMINARY_HITS.csv"
    dispositions_path = production / "HIT_DISPOSITIONS.csv"
    # Regeneration must never overwrite later human or scientific dispositions.
    if dispositions_path.exists():
        prior = list(csv.DictReader(dispositions_path.open()))
        if any(row.get("review_status") != "UNREVIEWED" for row in prior):
            raise ValueError("Existing dispositions contain reviewed records; preserve them")
    hits = list(csv.DictReader(hit_path.open()))
    if len(hits) != 10 or any(hit["status"] != "PRELIMINARY_EMISSION_HIT" for hit in hits):
        raise ValueError("This fixed figure requires the ten preserved preliminary hits")
    config_path = root / "code/DETECTOR_CONFIG.json"
    config = json.loads(config_path.read_text())
    run_inputs = json.loads((production / "RUN_INPUTS.json").read_text())
    if config != run_inputs["config"]:
        raise ValueError("Detector configuration changed after production")
    detector_path = root / "code/harps_detector.py"
    if digest(detector_path) != run_inputs["input_hashes"]["detector"]["sha256"]:
        raise ValueError("Detector code changed after production")
    manifest = {entry["dp_id"]: entry for entry in json.loads((root / "acquisition/DOWNLOAD_MANIFEST.json").read_text())}
    cached = {}
    dispositions = []
    provenance = []
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    figure, axes = plt.subplots(5, 2, figsize=(14, 20))
    figure.subplots_adjust(top=0.87, bottom=0.075, left=0.085, right=0.98, hspace=0.58, wspace=0.23)
    figure.suptitle("10 foreløbige emissionshits — oprindelse endnu ikke vurderet", fontsize=19, y=0.975, fontweight="bold")
    figure.text(0.5, 0.947, "HARPS · målt flux i ukalibreret ADU · barycentriske luftbølgelængder (AIR)", ha="center", fontsize=11)
    for index, (axis, hit) in enumerate(zip(axes.flat, hits), 1):
        dp_id = hit["dp_id"]
        token = dp_id.replace(":", "_")
        result_path = production / "spectra" / (token + ".json")
        saved = json.loads(result_path.read_text())
        if dp_id not in cached:
            fits_path = root / "data/main" / (token + ".fits")
            wave, flux, metadata = read_spectrum(fits_path)
            if metadata["sha256"] != hit["input_sha256"] or metadata["sha256"] != saved["input"]["sha256"]:
                raise ValueError("FITS hash differs from production: " + dp_id)
            if metadata["SPECSYS"] != "BARYCENT" or "obs.atmos" not in metadata["wavelength_ucd"]:
                raise ValueError("Unexpected wavelength frame or medium: " + dp_id)
            recomputed, arrays = analyze_arrays(wave, flux, config)
            if recomputed["all_threshold_runs"] != saved["all_threshold_runs"]:
                raise ValueError("Recomputed event tuples differ from preserved production: " + dp_id)
            cached[dp_id] = arrays, metadata
            provenance.append({"dp_id": dp_id, "fits_path": str(fits_path.relative_to(root)),
                               "fits_sha256": metadata["sha256"], "saved_result_sha256": digest(result_path),
                               "recomputed_all_threshold_runs_exactly_match": True})
        arrays, metadata = cached[dp_id]
        start, end, peak = (int(hit[key]) for key in ("start_index", "end_index_exclusive", "peak_index"))
        event = next(event for event in saved["all_threshold_runs"]
                     if event["start_index"] == start and event["end_index_exclusive"] == end)
        if event["status"] != "PRELIMINARY_EMISSION_HIT" or event["peak_index"] != peak:
            raise ValueError("Selected hit does not match preserved event")
        wave = arrays["wave"]
        center = wave[peak]
        shown = (wave >= center - 0.4) & (wave <= center + 0.4)
        x = wave[shown] / 10.0
        axis.plot(x, arrays["flux"][shown], color="#163e57", lw=1.15, marker="o", ms=2.0, label="Målt flux")
        axis.plot(x, arrays["continuum"][shown], color="#158070", lw=1.8, label="Lokal median (101 punkter)")
        threshold = arrays["continuum"] + config["threshold_local_std"] * arrays["local_std"]
        axis.plot(x, threshold[shown], color="#c37421", lw=1.5, ls="--", label="Median + 3,5 × lokal std")
        half_step = saved["nominal_step_angstrom"] / 2
        axis.axvspan((wave[start]-half_step)/10, (wave[end-1]+half_step)/10,
                     color="#b95e78", alpha=0.20, label="Registreret run (4 punkter)")
        axis.set_xlim((center-0.4)/10, (center+0.4)/10)
        axis.set_title(f"H{index:02d} · {hit['canonical_target']} · {center/10:.3f} nm\n"
                       f"DATE-OBS: {metadata['DATE-OBS']}", loc="left", fontsize=11, pad=10)
        axis.set_xlabel("Barycentrisk luftbølgelængde (nm)", fontsize=9)
        axis.set_ylabel("Flux (ADU)", fontsize=9)
        axis.xaxis.set_major_formatter(FormatStrFormatter("%.3f"))
        axis.xaxis.set_major_locator(MaxNLocator(nbins=5))
        axis.yaxis.set_major_locator(MaxNLocator(nbins=5))
        axis.tick_params(labelsize=9)
        axis.grid(alpha=0.16, lw=0.6)
        dispositions.append({
            "hit_id": f"H{index:02d}", "canonical_target": hit["canonical_target"], "dp_id": dp_id,
            "input_sha256": metadata["sha256"], "date_obs_utc": metadata["DATE-OBS"],
            "mjd_obs": metadata["MJD-OBS"], "exptime_seconds": metadata["EXPTIME"],
            "raw_progenitor_ids": json.dumps(manifest[dp_id]["raw_progenitor_ids"]),
            "berv_km_s": metadata["berv_km_s"], "wavelength_frame": "BARYCENT", "wavelength_medium": "AIR",
            "wave_peak_angstrom": event["wave_peak_angstrom"], "wave_peak_nm": event["wave_peak_angstrom"]/10,
            "start_index": start, "end_index_exclusive": end, "peak_index": peak,
            "run_pixels": event["run_pixels"], "peak_local_contrast": event["peak_local_contrast"],
            "observed_fwhm_angstrom": event["observed_fwhm_angstrom"],
            "detector_status": event["status"], "review_status": "UNREVIEWED", "origin": "", "review_notes": "",
        })
    handles, labels = axes.flat[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.932), ncol=4,
                  frameon=False, fontsize=10, handlelength=2.6, columnspacing=1.5)
    figure.text(0.5, 0.026,
                 "Hvert panel viser ±0,4 Å omkring det målte maksimum. Lokal kontrast er ikke en kalibreret signifikans.\n"
                 "Alle 10 hits er UNREVIEWED; figuren angiver ingen oprindelse.",
                 ha="center", fontsize=10, color="#394c59")
    png_path = production / "PRELIMINARY_HITS.png"
    figure.savefig(png_path, dpi=160, facecolor="white")
    plt.close(figure)
    with dispositions_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(dispositions[0]))
        writer.writeheader()
        writer.writerows(dispositions)
    receipt = {
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "code_sha256": digest(Path(__file__)), "detector_sha256": digest(detector_path),
        "configuration_sha256": digest(config_path), "preliminary_hits_csv_sha256": digest(hit_path),
        "versions": {"python": sys.version, **{name: importlib.metadata.version(name) for name in ("numpy", "scipy", "astropy", "matplotlib")}},
        "panels": len(hits), "layout": "5 rows by 2 columns", "half_window_angstrom": 0.4,
        "input_spectra": provenance, "all_dispositions": "UNREVIEWED",
        "origin_classification_performed": False, "raw_data_downloaded": False,
        "outputs": {png_path.name: digest(png_path), dispositions_path.name: digest(dispositions_path)},
    }
    (production / "PLOT_MAIN_HITS_RECEIPT.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"panels": len(hits), "plotted_spectra": len(cached), "figure": str(png_path),
                      "dispositions": str(dispositions_path), "status": "ALL_UNREVIEWED"}))


if __name__ == "__main__":
    main()
