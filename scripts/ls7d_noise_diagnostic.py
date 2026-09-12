#!/usr/bin/env python3
"""Diagnose the closed LS7C noise mismatch without rescoring any event."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess

from astropy.io import fits
import numpy as np

from ls7_tess_pilot import ROOT, load_products, sha256, save_json
from seti_repeater.light_sail_tess_v3 import spatial_model
from seti_repeater.tess_noise_diagnostic import decompose_noise


def verify_manifest(base, manifest):
    count = 0
    for line in manifest.read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        if sha256(base/name) != expected:
            raise RuntimeError("source identity mismatch: "+name)
        count += 1
    return count


def distribution(values):
    v = [x for x in values if x is not None]
    return {"count": len(v), "missing": len(values)-len(v),
            "min": float(np.min(v)) if v else None,
            "median": float(np.median(v)) if v else None,
            "max": float(np.max(v)) if v else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT/"results_ls7d_noise")
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("refusing to overwrite completed results")
    own_count = verify_manifest(ROOT, ROOT/"LS7D_FREEZE.sha256")
    design = json.loads((ROOT/"config/ls7d_noise.json").read_text())
    for name, expected in design["input_sha256"].items():
        if sha256(ROOT/name) != expected:
            raise RuntimeError("pinned input changed: "+name)
    old_counts = {name: verify_manifest(ROOT, ROOT/name) for name in
                  ("LS7_FREEZE.sha256", "LS7B_FREEZE.sha256", "LS7C_FREEZE.sha256")}
    old = ROOT/"results_ls7c_tess"
    old_counts["LS7C_outputs"] = verify_manifest(old, old/"SHA256SUMS")
    old_counts["LS7C_review"] = verify_manifest(old, old/"REVIEW_SHA256SUMS")
    cfg = json.loads((ROOT/"config/ls7c_tess_l9859.json").read_text())
    sources = json.loads((old/"source_manifest.json").read_text())["products"]
    paths = {p["kind"]: args.cache/p["name"] for p in sources}
    for p in sources:
        if sha256(paths[p["kind"]]) != p["sha256"]:
            raise RuntimeError("FITS hash mismatch: "+p["name"])
    cube, aperture, time, cadence, _, _, _, _ = load_products(paths, cfg)
    with fits.open(paths["tp"], memmap=False) as tp, fits.open(paths["lc"], memmap=False) as lc:
        errors = np.asarray(tp[1].data["FLUX_ERR"], dtype=float)
        corrected = np.asarray(tp[1].data["FLUX"], dtype=float)
        sap_errors = np.asarray(lc[1].data["SAP_FLUX_ERR"], dtype=float)
        units = {"FLUX": tp[1].columns["FLUX"].unit,
                 "FLUX_ERR": tp[1].columns["FLUX_ERR"].unit,
                 "SAP_FLUX_ERR": lc[1].columns["SAP_FLUX_ERR"].unit}
    if len(set(units.values())) != 1:
        raise RuntimeError("noise column units differ")
    rows = json.loads((old/"trials.json").read_text())
    selected = [r for r in rows if r["group"] == "matched" and r["kind"] == "stellar"]
    if len(selected) != design["expected_trial_rows"] or len({r["anchor"] for r in selected}) != 10:
        raise RuntimeError("unexpected trial selection")
    previous = {r["trial_id"]: r for r in json.loads((old/"NOISE_REVIEW.json").read_text())["rows"]}
    windows, links = {}, []
    for r in selected:
        a, h = r["native_index"], cfg["injections"]["context_half_samples"]
        start, stop = r["best"]["start"], r["best"]["stop"]
        key = f"a{r['anchor']:02d}_s{start}_e{stop}"
        if key not in windows:
            native = cube[a-h:a+h+1]
            err = errors[a-h:a+h+1]
            cor = corrected[a-h:a+h+1]
            model = spatial_model(native, err, aperture, start, stop, cfg)
            pixels = model["pixels"]
            ap = aperture[pixels]
            parts = [np.arange(max(0, start-60), max(0, start-5)),
                     np.arange(min(len(native), stop+5), min(len(native), stop+60))]
            for side in parts:
                if not np.all(np.diff(cadence[a-h+side]) == 1):
                    raise RuntimeError("sideband crosses a cadence gap")
            d = decompose_noise([native[s][:, pixels] for s in parts],
                                [cor[s][:, pixels] for s in parts],
                                [err[s][:, pixels] for s in parts], ap, r["sigma_e_per_s"])
            factor = 1/(stop-start)+np.pi/(2*model["side_samples"])
            original_sigma = float(np.sqrt(model["variance"][ap].sum()/factor))
            if not np.isclose(d["quadrature_ls7c_sigma"], original_sigma, rtol=1e-12):
                raise RuntimeError("original LS7C variance not reproduced")
            ss = sap_errors[a-h+np.concatenate(parts)]
            if not np.all(np.isfinite(ss) & (ss > 0)):
                raise RuntimeError("invalid archived SAP errors")
            per_cadence_pixel_error = np.sqrt(np.sum(err[np.concatenate(parts)][:, aperture]**2, axis=1))
            d.update({"window_id": key, "anchor": r["anchor"], "native_index": a,
                      "absolute_event_start": a-h+start, "absolute_event_stop": a-h+stop,
                      "sideband_ranges_absolute": [[int(a-h+s[0]), int(a-h+s[-1]+1)] for s in parts],
                      "aperture_pixel_yx": np.argwhere(aperture).tolist(),
                      "valid_pixel_yx": np.argwhere(pixels).tolist(),
                      "archived_sap_error_median": float(np.median(ss)),
                      "pixel_error_quadrature_to_sap_error": distribution((per_cadence_pixel_error/ss).tolist()),
                      "restored_nonzero_sideband_pixel_samples": int(np.count_nonzero(native[np.concatenate(parts)][:, pixels] != cor[np.concatenate(parts)][:, pixels])),
                      "original_variance_absolute_error": abs(d["quadrature_ls7c_sigma"]-original_sigma)})
            windows[key] = d
        d = windows[key]
        original = previous[r["trial_id"]]["aperture_quadrature_to_run_sigma_ratio"]
        if not np.isclose(d["quadrature_to_run_sigma_ratio"], original, rtol=1e-12):
            raise RuntimeError("previous noise-review ratio changed")
        links.append({"trial_id": r["trial_id"], "window_id": key, "anchor": r["anchor"],
                      "target_score": r["target_score"], "shape": r["shape"],
                      "original_noise_ratio": original, "original_noise_ratio_error": abs(original-d["quadrature_to_run_sigma_ratio"]),
                      "original_spatial_pass": r["spatial_pass"]})
    unique = list(windows.values())
    keys = ("quadrature_to_run_sigma_ratio", "quadrature_ls7c_sigma", "quadrature_empirical_sigma", "quadrature_supplied_sigma")
    summaries = {}
    for name, sample in (("trial_weighted", [windows[r["window_id"]] for r in links]), ("unique_windows", unique)):
        summaries[name] = {k: distribution([w[k] for w in sample]) for k in keys}
        summaries[name]["factors"] = {k: distribution([w["multiplicative_factors"][k] for w in sample])
                                      for k in unique[0]["multiplicative_factors"]}
        summaries[name]["covariance"] = {s: {k: distribution([w[s][k] for w in sample]) for k in
                                               ("covariance_sum_to_diagonal_variance_ratio", "diagonal_to_projected_sigma_ratio")}
                                           for s in ("restored", "corrected")}
    anchors = [{"anchor": a, "unique_windows": sum(w["anchor"] == a for w in unique),
                "factors": {k: distribution([w["multiplicative_factors"][k] for w in unique if w["anchor"] == a])
                            for k in unique[0]["multiplicative_factors"]}}
               for a in sorted({w["anchor"] for w in unique})]
    result = {"scope": "Closed sector 32 noise accounting; no new detection decisions, injections, coverage or detector adoption",
              "created_utc": datetime.now(timezone.utc).isoformat(), "units": units,
              "diagnostic_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "freeze_sha256": sha256(ROOT/"LS7D_FREEZE.sha256"),
              "trial_rows": len(links), "unique_windows": len(unique), "anchors": len(anchors),
              "original_spatial_passes": sum(r["original_spatial_pass"] for r in links),
              "input_manifest_checks": old_counts, "diagnostic_freeze_files_checked": own_count,
              "summaries": summaries, "anchor_summaries": anchors,
              "supplied_dominates_every_aperture_pixel_windows": sum(w["supplied_dominant_aperture_pixels"] == int(aperture.sum()) for w in unique),
              "all_trial_links_reproduce_original_noise_ratios": True,
              "max_covariance_identity_error": max(w[s]["identity_absolute_error"] for w in unique for s in ("restored", "corrected")),
              "max_factorization_error": max(w["factorization_absolute_error"] or 0 for w in unique),
              "full_stamp_rank_deficient_windows": sum(w["full_stamp_covariance_rank_upper_bound"] < w["valid_stamp_pixels"] for w in unique),
              "environment": {"python": platform.python_version(), **{k: importlib.metadata.version(k) for k in ("numpy", "scipy", "astropy", "matplotlib")}}}
    # Verify original outputs again after array access and analysis.
    verify_manifest(old, old/"SHA256SUMS")
    verify_manifest(old, old/"REVIEW_SHA256SUMS")
    args.output.mkdir(parents=True)
    save_json(args.output/"summary.json", result)
    save_json(args.output/"windows.json", unique)
    save_json(args.output/"trial_links.json", links)
    save_json(args.output/"source_manifest.json", {"products": sources, "input_sha256": design["input_sha256"]})
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
