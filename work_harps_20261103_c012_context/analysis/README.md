# Fixed C012 individual spectral context

This prospective method follows original queue row **24**: singleton **V2E2-0087 / C012 / R013** on **HD112410**, center **3869.2675 Å** in barycentric air wavelengths. Primary, secondary and adopted reviews remain **U/U/U**. Queue row 24 precedes C011 at row 25; the original order is retained.

Retain HD112410's own **seven existing April–August 2025 observations** against the one discovery product `ADP.2025-04-30T01:01:50.866`, observed on **2025-04-29**. The same exposures were used in C010, whose bounded wavelength window is disjoint. C012 numerically overlaps older HD106515A C002/C003/C004 windows, but those belong to different observations and share no source pixels. Original 0087 epoch/profile and raw evidence already exist. This is post-detection descriptive context, with reused exposures and no new acquisition or independent observing evidence.

The original core is **[3869.0175,3869.5175] Å**, full context **[3866.2675,3872.2675] Å**. [PLAN.json](PLAN.json), [the inventory](../inputs/INPUT_INVENTORY.json) and [synthetic checks](SYNTHETIC_PREFLIGHT.json) bind the method before observed values are interpreted.

## Fixed geometry and accounting

Set `cb=3869.2675 Å`, `c=299792.458 km/s` and `ct=cb/(1+3.40485846065643/c)=3869.2235557371996 Å`, recomputed for this wavelength from its April discovery BERV. C010's numeric anchor is not transferred. The `arange(-300,301)/100` grid has **601 centers** across ±3 Å: **51** in the original ±0.25 Å core and **550** surrounding centers. Barycentric profiles query `cb+x`; fixed topocentric profiles query barycentric wavelengths `(ct+x)*(1+BERV_epoch/c)`. Native topocentric-air wavelengths use the unchanged zero-based polynomial on pixels 0..4095, multiplied by `(1+BERV_epoch/c)` once.

The own-target BERV span is **21.30284860830273 km/s**. This supplies coordinate separation, not calibrated physical-origin discrimination. A coherent catalog feature may leave the fixed topocentric core at another epoch, allowing neighboring structure into that comparison. No center, width, lag, RV, continuum, background, drift or alignment is fitted.

| Output family | Fixed accounting |
|---|---:|
| Seven merged epochs × two frames | 14 profiles |
| Discovery × orders 2 and 3 × two frames | 4 profiles |
| Seven epochs × one reference × two frames × two regions | 28 comparisons |
| Two native orders × same-exposure merged × two frames × two regions | 8 comparisons |
| Identical-product self rows included above | 4 |
| Preserved historical raw cutout/excess pairs | 2 |
| Compact pre-interpolation source windows | 9 |

There are **18 profile slots and 36 comparison slots**. Every missing, low or invalid outcome retains its slot and reason. Native and merged products share an exposure and extraction lineage; their agreement is dependent evidence rather than another observation or a physical flux ratio.

## Fresh native scope and historical mapping limits

A fresh all-**72-order header scan** identifies **orders 2 and 3** covering the original center. Order 2 endpoints are **[3827.04557082137,3869.9999605859994] Å** topocentric. It covers the entire original core and negative reference flank, but ends near **+0.7764 Å** and misses the positive reference flank in both frames. It stays selected; normalization must retain explicit missing-flank RAW_ONLY outcomes. Its header geometry covers **378/601** grid centers: full 51-point core plus **327/550** surrounding centers, below the fixed broad support gate. This geometric accounting does not establish finite raw flux or evaluable correlation.

Order 3 endpoints are **[3851.2610722297,3894.4910032774533] Å** topocentric; its full context, core and both flanks are geometrically covered. Geometric support does not establish finite flux, positive reference medians, false low-reference flags or usable statistics; these remain runtime checks.

Preserve each historical registration stage. **Order 2:** global-grid true, original local usable false, original baseline verified false, later five-window support true. **Order 3:** all four stages true. Later supported reference geometry does not repair original order 2 local/baseline limitations. Fresh wavelength coverage and native/merged agreement do not validate raw-detector registration.

The historical reviews describe broad enhancement in both overlapping orders, noisier order 2, smoother order 3 and trace-associated raw structure. Exact texts, pixels and qualifications remain preserved. No shape, frame correlation, broad structure or mapping flag changes U/U/U, identifies origin or qualifies a laser candidate.

## Signed reference rule and comparisons

Merged flux retains uncalibrated ADU units. Native BUNIT is absent, so native extracted units remain unspecified. Signed flux is never clipped or sign-flipped. Only the union required by both fixed-frame windows plus interpolation brackets is copied; full merged coordinates locate those slices and native coordinates derive from recorded headers.

Sampling, normalization and comparison functions are unchanged from C010. Per profile/frame, the reference is the pooled signed median of original source samples at **1.5 ≤ |offset| ≤ 3 Å**, requiring **at least 20 finite samples in each flank and a strictly positive pooled median**. Keep coverage, native/finite counts, separate medians and nonpositive fractions, available versus valid references, ERR support and failure reasons explicit. All fixed-flank spectral structure remains; medians are descriptive reference levels rather than established line-free continua.

The first-difference proxy is `1.4826 × MAD / sqrt(2)` from finite adjacent source samples within the same flank and without a large wavelength gap. The low-reference rule `reference ≤ 3 × proxy` applies only to valid normalization and is not formal SNR. Missing, insufficient or nonpositive references remain raw-only, with no moved flank, smaller window or fitted replacement.

Raw Pearson requires nonzero exact range and at least **41/51 core or 440/550 surrounding common finite grid values**. Normalized RMS uses the same gate with valid references. A raw-only profile can retain an adequately supported raw Pearson. Linear interpolation masks brackets above 1.51 times the full-source median wavelength step and never extrapolates. Interpolated samples and self rows are dependent evidence. ERR support and descriptive proxies do not establish calibrated significance, sensitivity, false alarms or a qualified survey null.

## Release, plots and preservation

All seven merged headers and the discovery native header are checked before new flux access: exact identity/hash/metadata, numeric BERV, merged barycentric-air Angstrom/ADU and unique WAVE/FLUX/ERR single-exposure tables, native shape and polynomial coefficients. The runner has no network code, checks frozen sources and release hashes before and after execution, and refuses to overwrite a result directory.

Nine compact source NPZs retain exact indices, original-frame and barycentric wavelengths, signed flux, ERR (NaN where native errors are unavailable), BERV, source hashes and full-source spacing. Both historical 0087 raw/native NPZs are copied byte for byte. Saved cutout/excess maps are displayed unchanged, without new registration, subtraction, detector modeling, pixel statistics or origin assignment.

Four fixed figures retain all seven merged broad/core profiles, both native contexts and both original raw/excess pairs. Markers denote catalog/discovery coordinates rather than fitted peaks. Keep raw-only reasons and any low-reference outcome visible. Merged scales match across frames per quantity/window; native raw scales match across frames per order. Every finite value remains with a 5% margin. Raw images use separate full extrema. No smoothing, clipping, favorable epoch selection or contrast variant is introduced.

After root publishes and reads back the exact method, execute once:

```bash
python work_harps_20261103_c012_context/analysis/compare_group.py
python work_harps_20261103_c012_context/analysis/plot_group.py
```

`ROOT_RELEASE.json` must use `HARPS_C012_GROUP_RELEASE_V1` and bind verified public readback plus plan, runner and inventory hashes. Previous science outputs and dispositions remain immutable.
