# Fixed C004 joint profile context

This prospective context follows the original queue's C004 / R004 group on HD106515A: V2E2-0028, 0045 and 0052, all with catalog center 3872.245 Å. Keep all seven original-cohort merged epochs and all three distinct discovery references. No extra reference is chosen from the resulting correlations. All three records remain U; this is a bounded diagnostic of existing evidence, not a new observation or independent detection.

The original ±0.25 Å C004 core [3871.995, 3872.495] Å was already visible inside C003's positive reference flank [3871.25125, 3872.75125] Å. The wider windows and observation products are shared. Selection by queue preceded C007's results, but C004 values had been seen in C003; this interpretation is neither blind nor independent of that earlier context. The dependence is reciprocal: the full C003 original core union [3869.495, 3870.0075] Å lies inside C004's negative reference flank [3869.245, 3870.745] Å. Keep that known structure, without masks or alternative reference intervals.

[PLAN.json](PLAN.json), the [input inventory](../inputs/INPUT_INVENTORY.json) and [synthetic checks](SYNTHETIC_PREFLIGHT.json) bind this method before additional window interpretation.

## Geometry and complete accounting

Set `cb = 3872.245 Å`, `c = 299792.458 km/s` and `ct = cb/(1 + 10.77158288517/c)`. The anchor is **V2E2-0028, observed 2022-03-07**, the first C004 discovery product ADP.2022-03-08T01:01:37.342. The January 2022 BERV used in earlier groups must not be inherited. All three discovery products use this one fixed topocentric anchor.

The common `arange(-300,301)/100` grid has 601 centers across ±3 Å. The identical original catalog cores give **51 core centers** at |x| ≤ 0.25 Å and **550 surrounding centers**. Barycentric profiles query `cb+x`; topocentric profiles query barycentric wavelengths `(ct+x)*(1+BERV_epoch/c)`. Native topocentric-air coordinates use the unchanged zero-based order polynomial and one multiplication by `(1+BERV_epoch/c)`.

The seven-epoch BERV span remains 59.6098131157401 km/s. A fixed topocentric core can sample neighboring structure when an expected coherent feature moves beyond it. No fitted shift, linewidth, lag, stellar velocity, background or drift is used.

| Output family | Fixed accounting |
|---|---:|
| Seven merged epochs × two frames | 14 profiles |
| Three discovery products × order 3 × two frames | 6 profiles |
| Seven epochs × three references × two frames × two regions | 84 comparisons |
| Three native contexts × same-exposure merged × two frames × two regions | 12 comparisons |
| Identical-product self-comparisons, included above | 12 |
| Preserved event raw cutout/excess pairs | 3 |
| Compact source windows before interpolation | 10 |

There are **20 profile slots and 96 comparison slots**. Invalid or missing outcomes retain their slots and reasons. Reversed reference pairs, shared epochs and same-exposure native/merged comparisons do not create independent detections.

## Coverage, normalization and original mapping

Fresh header scans of all 216 native orders identify only order 3 at each original C004 center. All three historical global, local, baseline and later five-window mapping flags are true, and their distinct stages remain preserved. These are historical diagnostics, not a new physical-origin validation. Do not inherit C003's excluded or partially covered order 2 contexts at this different center. Any observed finite-support or normalization failure stays explicit.

Merged FLUX is uncalibrated ADU; native BUNIT is absent, so native extracted units remain unspecified. Preserve signed flux. Save only source samples needed by the union of the two fixed-frame windows plus brackets. Full merged wavelength coordinates locate slices; native coordinates derive from headers.

The profile and comparison functions are unchanged from C007. Each profile/frame uses the pooled signed median at 1.5 ≤ |offset| ≤ 3 Å, with at least 20 finite native samples separately in both flanks and a positive pooled median. Side counts, medians, nonpositive fractions, ERR support and available-versus-valid reference levels remain explicit. These structured flanks are not fitted line-free continua. Invalid references remain raw-only, without sign flips, changed flanks or extrapolation.

The descriptive noise proxy is 1.4826 × first-difference MAD / √2 within each same fixed flank, excluding large gaps. The reference ≤ 3 × proxy flag is not formal SNR. Linear interpolation masks brackets larger than 1.51 times the full-source median step. Raw Pearson requires nonzero exact range and at least 80% common support: **41/51 core or 440/550 surrounding centers**. Normalized RMS additionally needs valid references. Every epoch, frame and fixed discovery reference is reported.

## Release and preservation

Verify all seven merged and three native headers before new flux access: exact hashes and identities, recorded metadata, numeric BERV, merged barycentric-air Angstrom/ADU representation and unique WAVE/FLUX/ERR columns, native shape and polynomial coefficients. Recheck source and release hashes after execution. The runner has no network code and refuses to overwrite an existing results directory.

Ten compact source NPZs preserve indices, original-frame and barycentric wavelengths, signed flux, ERR (NaN for unavailable native errors), source hashes, BERV and full-source spacing. Copy all three exact event-specific raw/native NPZs. Display their original cutouts and excess maps without new registration, subtraction or detector-pixel statistics.

The plotter produces four figures: all-epoch merged broad/core contexts, all three native order contexts and all three historical raw cutout/excess pairs. The barycentric catalog markers coincide; their topocentric discovery coordinates differ because their BERV values differ. Markers are catalog coordinates, not fitted peaks. Matching frame scales retain every finite value with a 5% margin, and raw images use separate full extrema. No smoothing, clipping or favorable epoch selection.

After root publishes and verifies the complete method, execute once:

```bash
python work_harps_20261102_c004_context/analysis/compare_group.py
python work_harps_20261102_c004_context/analysis/plot_group.py
```

`ROOT_RELEASE.json` uses schema `HARPS_C004_GROUP_RELEASE_V1` and binds the public readback, plan/script and inventory hashes. This diagnostic does not establish line origin, physical linewidth, false-alarm calibration, sensitivity or a qualified null. Earlier pipelines, outputs and labels remain unchanged.
