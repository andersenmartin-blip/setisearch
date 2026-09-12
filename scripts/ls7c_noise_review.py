#!/usr/bin/env python3
"""Retrospective residual attribution at already-recorded LS7C signal windows.

No new search, template selection, threshold or acceptance decision. Reconstruct
only the 120 nominal strength-matched trials and verify original fit residuals.
"""
import json
from pathlib import Path

from astropy.io import fits
import numpy as np

from ls7_tess_pilot import ROOT, load_products, sha256, save_json
from seti_repeater.light_sail_tess import pulse_shape
from seti_repeater.light_sail_tess_v3 import empirical_profile, spatial_model


def main():
    out = ROOT/"results_ls7c_tess"
    cfg = json.loads((ROOT/"config/ls7c_tess_l9859.json").read_text())
    sources = json.loads((out/"source_manifest.json").read_text())["products"]
    paths = {p["kind"]: ROOT/"data_ls7c_tess"/p["name"] for p in sources}
    for p in sources:
        assert sha256(paths[p["kind"]]) == p["sha256"]
    cube, ap, time, _, _, _, _, _ = load_products(paths, cfg)
    with fits.open(paths["tp"], memmap=False) as tp:
        err = np.asarray(tp[1].data["FLUX_ERR"], dtype=float)
        corrected = np.asarray(tp[1].data["FLUX"], dtype=float)
    trials = json.loads((out/"trials.json").read_text())
    rows = []
    for r in trials:
        if r["group"] != "matched" or r["kind"] != "stellar":
            continue
        a, h = r["native_index"], cfg["injections"]["context_half_samples"]
        native, errors = cube[a-h:a+h+1], err[a-h:a+h+1]
        seconds = (time[a-h:a+h+1]-time[a])*86400
        reference = np.zeros(ap.shape)
        valid = np.all(np.isfinite(native), axis=0)
        reference[valid] = np.median(native[:, valid], axis=0)
        profile = empirical_profile(reference, ap)
        pulse, _ = pulse_shape(seconds, r["phase_seconds"], r["shape"], 20.)
        injected = native + (r["tuning"]["amplitude_e_per_s"]*pulse)[:, None, None]*profile
        start, stop = r["best"]["start"], r["best"]["stop"]
        model = spatial_model(native, errors, ap, start, stop, cfg)
        pixels = model["pixels"]
        delta = np.mean(injected[start:stop][:, pixels], axis=0)-model["reference"][pixels]
        fit = r["spatial"]["star"]
        residual = delta-fit["amplitude"]*model["star"][fit["template_index"]]-fit["background"]
        contribution = residual**2/model["variance"]
        assert np.isclose(contribution.sum(), fit["chi2"], rtol=1e-10, atol=1e-7)
        outside = ~ap[pixels]
        index_lo, index_hi = a-h+start, a-h+stop
        restoration = np.mean(cube[index_lo:index_hi]-corrected[index_lo:index_hi], axis=0)[pixels]
        correction_pixels = np.abs(restoration) > 1e-9
        factor = 1/(stop-start)+np.pi/(2*model["side_samples"])
        quadrature_sigma = np.sqrt(model["variance"][~outside].sum()/factor)
        # Attributes original residuals to pixels with recorded ground restoration;
        # does not declare that removing them would yield a valid source fit.
        rows.append({"trial_id": r["trial_id"], "anchor": r["anchor"], "target_score": r["target_score"], "shape": r["shape"],
                     "spatial_pass": r["spatial_pass"], "reduced_chi2": r["spatial"]["reduced_chi2"],
                     "aperture_quadrature_to_run_sigma_ratio": float(quadrature_sigma/r["sigma_e_per_s"]),
                     "residual_fraction_outside_aperture": float(contribution[outside].sum()/contribution.sum()),
                     "residual_fraction_on_restored_pixels": float(contribution[correction_pixels].sum()/contribution.sum()),
                     "window_restored_pixels": int(correction_pixels.sum()),
                     "window_restored_pixels_outside_aperture": int(np.count_nonzero(correction_pixels & outside))})
    assert len(rows) == 120
    failed = [r for r in rows if r["reduced_chi2"] > cfg["spatial"]["reduced_chi2_max"]]
    result = {"scope": "Retrospective attribution on closed sector 32 at 120 recorded nominal trial windows; all original weighted residual sums reproduced, no altered decisions",
              "quadrature_to_run_sigma_ratio_min_median_max": [float(f([r["aperture_quadrature_to_run_sigma_ratio"] for r in rows])) for f in (np.min, np.median, np.max)],
              "residual_gate_failures": len(failed),
              "residual_failures_with_restored_pixels": sum(r["window_restored_pixels"] > 0 for r in failed),
              "residual_failure_fraction_on_restored_pixels_min_median_max": [float(f([r["residual_fraction_on_restored_pixels"] for r in failed])) for f in (np.min, np.median, np.max)] if failed else None,
              "rows": rows}
    save_json(out/"NOISE_REVIEW.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
