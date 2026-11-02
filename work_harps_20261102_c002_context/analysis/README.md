# Fixed C002 individual spectral context

This prospective method follows original queue row 10: singleton V2E2-0033 / C002 / R002 on HD106515A at **3868.6025 Å**. All seven original-cohort merged epochs are retained against the one fixed discovery product observed on **2022-05-07**. The record remains U. This adds bounded descriptive context of existing evidence, not a new exposure, archive-wide sample or independent detection.

The original ±0.25 Å core, [3868.3525, 3868.8525] Å, was already visible in completed C003's surrounding spectrum. It lies between that earlier core and negative reference flank, outside both masks. The C002 core lies outside C004's window, but the proposed full C002 window [3865.6025, 3871.6025] Å overlaps C003 over 4.85125 Å and C004 over 2.3575 Å. All seven epoch products are reused. Original queue selection before C004 values does not make this later interpretation blind, untouched or independent. [PLAN.json](PLAN.json), [the input inventory](../inputs/INPUT_INVENTORY.json) and [synthetic checks](SYNTHETIC_PREFLIGHT.json) bind the separate method before additional observed array access.

## Fixed geometry and complete accounting

Set `cb = 3868.6025 Å`, `c = 299792.458 km/s` and `ct = cb/(1 - 18.8907517532076/c) = 3868.846286702511 Å`, using the **May 2022 discovery BERV**. Do not inherit a March or January anchor. The `arange(-300,301)/100` grid has 601 centers across ±3 Å, including **51 original core centers** and **550 surrounding centers**. Barycentric profiles query `cb+x`; topocentric profiles query barycentric wavelengths `(ct+x)*(1+BERV_epoch/c)`. Native topocentric-air wavelengths use the unchanged polynomial on zero-based pixels 0..4095 and are multiplied by `(1+BERV_epoch/c)` once.

The same seven epochs span 59.6098131157401 km/s in BERV. That span is coordinate separation, not a calibrated origin test. The fixed topocentric window does not track each other feature and can sample neighboring structure when a barycentrically coherent center leaves the core. No shift, recentering, fitted width, lag, stellar velocity, continuum, background or drift is optimized.

| Output family | Fixed accounting |
|---|---:|
| Seven merged epochs × two frames | 14 profiles |
| One discovery product × two covering orders × two frames | 4 profiles |
| Seven epochs × one reference × two frames × two regions | 28 comparisons |
| Two native orders × same-exposure merged × two frames × two regions | 8 comparisons |
| Identical-product self-comparisons, included above | 4 |
| Preserved raw cutout/excess pairs, orders 2 and 3 | 2 |
| Compact source windows before interpolation | 9 |

There are **18 profile slots and 36 comparison slots**. Missing or invalid outcomes retain their slots and reasons. Both native orders share the discovery exposure; native/merged similarity is not independent confirmation.

## Fresh order scope, signed flux and historical mapping

The original raw evidence contains orders 2 and 3. A fresh header scan of all 72 orders checks their coverage against the original feature center. Both covering orders are retained; coverage of the center does not guarantee full window or flank coverage, finite flux, positive references or sufficient comparison support. Do not transfer order exclusions, reference signs or low-reference outcomes from earlier groups to this wavelength.

Fresh header geometry places order 2's positive endpoint at **+1.160941197 Å barycentric / +1.161014356 Å topocentric** relative to the corresponding fixed center. Its entire core is covered, but its **whole positive reference flank [1.5, 3] Å is absent in both frames**. At most 417 of 601 grid centers, including 366 of the 550 surrounding centers, can be supported geometrically. Under the unchanged gates, both order 2 profiles must remain raw-only, their normalized RMS unavailable and their surrounding raw Pearson below the 440-sample minimum. Their core raw Pearson remains conditional on finite support and nonzero variance. This is missing wavelength coverage, not evidence that a measured two-flank reference is nonpositive. Order 3 covers both full windows geometrically; its flux quality and reference validity remain to be measured after release.

For order 2, historical **`local_mapping_usable=false` and `baseline_mapping_verified=false`** remain alongside true global and later five-window diagnostics. Order 3's historical stages are true. These distinct diagnostic stages and all primary, secondary and adopted reviews remain intact. Coordinate coverage or native/merged similarity cannot retroactively validate order 2's local raw-detector mapping.

Merged FLUX is uncalibrated ADU. Native BUNIT is absent, so native values retain unspecified extracted units. Signed flux is preserved. Only available source samples needed by the union of the two fixed-frame windows, plus bracketing samples, are copied. Full merged wavelength coordinates locate those slices; native coordinates derive from headers.

Sampling, normalization and comparison functions are unchanged from validated C004. Per profile/frame, the reference is the pooled signed median of native samples at **1.5 ≤ |offset| ≤ 3 Å**, requiring at least 20 finite samples in each flank and a strictly positive pooled median. Side coverage, finite counts, medians, nonpositive fractions, ERR support, available versus valid reference and failure reasons remain explicit. Invalid normalization remains raw-only; there is no sign flip, moved flank, narrower window, extrapolation or added background model.

The descriptive first-difference proxy is 1.4826 × MAD / √2 using finite adjacent source samples in the same fixed flank without a large wavelength gap. The reference ≤ 3 × proxy flag is not formal SNR. Raw Pearson requires a nonzero exact range and at least 80% common finite support: **41/51 core or 440/550 surrounding centers**. Normalized RMS requires the same support gate and usable reference levels. Adequately supported raw Pearson remains available for a raw-only profile. Linear interpolation masks brackets above 1.51 times the full-source median wavelength step. All outcomes remain in the output.

C003's original core union [3869.495, 3870.0075] Å lies in C002's surrounding region between its core and positive flank, ending 0.095 Å before that flank. **It does not lie inside a C002 reference flank.** Portions of both C002 flanks were already visible in C003 context; all known neighboring structure remains. These fixed reference levels are not established line-free continua. Positive scalar division leaves Pearson unchanged, while scaled heights and normalized RMS depend on the reference levels.

## Release, outputs and preservation

All seven merged headers and the native discovery header are checked before new flux access: source identity and hashes, recorded metadata, numeric BERV, merged barycentric-air Angstrom and ADU representation, unique WAVE/FLUX/ERR columns, single-exposure tables, native shape and polynomial coefficients. The runner has no network code, rechecks every frozen source and release hash after execution, and refuses to overwrite a previous output directory.

Nine compact source NPZs retain exact source indices, original-frame and barycentric wavelengths, signed flux, ERR (NaN where native errors are unavailable), source hashes, BERV and full-source spacing. Both historical event/order raw NPZs are copied exactly. Their existing cutout and raw-excess maps are displayed without new registration, subtraction, detector modeling or pixel statistics.

The fixed plotter produces four figures: all-epoch merged broad/core context, both native order contexts and both historical raw cutout/excess pairs. The event marker denotes the catalog/discovery coordinate, not a fitted peak. Raw-only reasons and partial coverage stay explicit. Merged scales match across frames per quantity/window; native raw scales match across frames per order. All finite plotted values are retained with a 5% scale margin; raw images use separate full extrema. No smoothing, clipping or favorable epoch selection is used.

After root publishes and verifies the complete frozen method, execute once:

```bash
python work_harps_20261102_c002_context/analysis/compare_group.py
python work_harps_20261102_c002_context/analysis/plot_group.py
```

`ROOT_RELEASE.json` uses schema `HARPS_C002_GROUP_RELEASE_V1` and binds the verified public method, plan/script and inventory hashes. This context does not identify origin, measure a physical linewidth, calibrate false alarms, establish sensitivity or produce a qualified null. Earlier pipelines, labels and completed contexts remain unchanged.
