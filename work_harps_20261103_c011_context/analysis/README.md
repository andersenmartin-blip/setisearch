# Fixed C011 individual spectral context

This prospective method follows original queue row **25**, after C012 row 24: singleton **V2E2-0089 / C011 / R012** on **HD112410**, exact catalog center **3865.6775000000002 Å** barycentric air. Historical primary, secondary and adopted reviews remain **U/U/U**. Figure titles display 3865.6775 Å; the scientific constant retains the exact original float.

Use HD112410's own **seven existing April–August 2025 observations**, with the sole discovery reference **`ADP.2025-05-29T01:01:14.389`**, observed **2025-05-28**, BERV **−5.48386283255014 km/s**. C012 used the April discovery; neither that reference nor its numeric anchor is transferred. No new acquisition or observing time is added.

The original core is **[3865.4275000000002,3865.9275000000002] Å**, full ±3 Å context **[3862.6775000000002,3868.6775000000002] Å**. The core lies outside C012's bounded window, but their wider windows overlap over **[3866.2675,3868.6775000000002] Å**, width **2.4100000000003092 Å**, on the same seven merged products. Reused surrounding/reference pixels make this dependent post-detection context. Original C011 epoch/profile/raw evidence already exists; it is not blind, untouched or independent new observing evidence. C010 uses the same epochs but a disjoint wavelength window. Numeric wavelength overlap with other-target HD106515A windows shares no observing products or source pixels.

[PLAN.json](PLAN.json), [the fresh input inventory](../inputs/INPUT_INVENTORY.json) and [synthetic checks](SYNTHETIC_PREFLIGHT.json) bind the method before observed values are read.

## Fixed geometry and accounting

Set `cb=3865.6775000000002 Å`, `c=299792.458 km/s` and `ct=cb/(1-5.48386283255014/c)=3865.748213029564 Å`, recomputed from the May discovery. The `arange(-300,301)/100` grid has **601 centers** across ±3 Å: **51** in the original ±0.25 Å core and **550** surrounding centers. Barycentric profiles query `cb+x`; fixed topocentric profiles query barycentric wavelengths `(ct+x)*(1+BERV_epoch/c)`. Native topocentric-air wavelengths use the unchanged zero-based polynomial on pixels 0..4095 and are multiplied by `(1+BERV_epoch/c)` once.

The same own-target BERV span is **21.30284860830273 km/s**. This supplies coordinate separation rather than calibrated origin discrimination. A barycentrically coherent catalog center can approach or leave the fixed topocentric core; comparisons may then describe neighboring structure. No center, width, lag, RV, continuum, background, drift or alignment is fitted.

| Output family | Fixed accounting |
|---|---:|
| Seven merged epochs × two frames | 14 profiles |
| May discovery × orders 2 and 3 × two frames | 4 profiles |
| Seven epochs × one reference × two frames × two regions | 28 comparisons |
| Two native orders × same-exposure merged × two frames × two regions | 8 comparisons |
| Identical-product self rows included above | 4 |
| Historical raw cutout/excess pairs retained | 2 |
| Compact pre-interpolation source windows | 9 |

There are **18 profile slots and 36 comparison slots**. Every missing, insufficient, nonpositive, low or invalid outcome retains its slot and reason. Native and merged products share an exposure and extraction lineage, so their agreement is dependent evidence rather than another observation or a physical flux ratio.

## Fresh native scope and historical mapping

A fresh scan of all **72 native order headers** identifies **orders 2 and 3** alone covering the original center. Their topocentric endpoints are **[3827.04590550197,3870.000069396472] Å** and **[3851.2615075553,3894.490605015315] Å**, respectively. Both orders cover the full ±3 Å context, original core and both reference flanks in each frame: all **601 grid centers**, including 51 core and 550 surrounding centers. These fresh header endpoints and support are bound in the plan. Coordinate coverage is distinct from finite flux, reference validity, low-reference status and usable statistics. C012's order 2 missing-flank outcomes are not assumed at this different center and May native product.

For C011, **both original orders 2 and 3 retain true global-grid, original local usable, original baseline verified and later five-window support**. C012's original order 2 local/baseline failures do not apply. Each recorded C011 stage remains preserved; fresh wavelength support and native/merged agreement do not independently validate raw-detector registration or physical origin.

The historical reviews describe broad native structure and diffuse trace-associated enhancement in both orders, without a clear charge morphology or qualified narrow emission source. Exact review texts, saved pixels and qualifications remain preserved. No shape, correlation, structured flank or mapping flag changes **U/U/U**, identifies origin or qualifies a laser candidate.

## Signed reference rule and comparisons

Merged flux retains uncalibrated ADU units. Native BUNIT is absent, so native extracted units remain unspecified. Signed flux is never clipped or sign-flipped. Only source slices required by the union of both fixed-frame windows, plus interpolation brackets, are copied. Full merged coordinates locate those slices; native coordinates derive from recorded headers.

Sampling, normalization and comparison functions remain unchanged from C012. Per profile and frame, the reference is the pooled signed median of original source samples at **1.5 ≤ |offset| ≤ 3 Å**, requiring **at least 20 finite samples in each flank and a strictly positive pooled median**. Preserve geometric/native/finite counts, separate medians and nonpositive fractions, available versus valid references, ERR support and failure reasons. All fixed-flank structure remains; these medians are descriptive levels rather than established line-free continua.

The first-difference proxy is `1.4826 × MAD / sqrt(2)` from finite adjacent source samples in the same flank and without a large wavelength gap. The low-reference rule `reference ≤ 3 × proxy` applies only to valid normalization and is not formal SNR. Missing, insufficient or nonpositive references remain raw-only, with null low flags, no moved flank, smaller window or fitted replacement. A valid but low reference retains an explicit true flag.

Raw Pearson requires nonzero exact range and at least **41/51 core or 440/550 surrounding common finite grid values**. Normalized RMS uses the same gate with valid references. An adequately covered raw-only profile may retain raw Pearson. Linear interpolation masks brackets above 1.51 times the full-source median wavelength step and never extrapolates. Interpolated samples and self rows are dependent. ERR support and descriptive proxies do not establish calibrated significance, sensitivity, false alarms or a qualified survey null.

## Release, plots and preservation

All seven merged headers and the May discovery native header are checked before new flux access: exact identity/hash/metadata, numeric BERV, merged barycentric-air Angstrom/ADU and unique WAVE/FLUX/ERR single-exposure tables, native shape and polynomial coefficients. The runner has no network code, checks frozen sources/release hashes before and after execution, and refuses to overwrite a result directory.

Nine compact source NPZs retain exact indices, original-frame and barycentric wavelengths, signed flux, ERR (NaN where native errors are unavailable), BERV, hashes and full-source spacing. Both exact historical 0089 raw/native NPZs are copied byte for byte. Their saved cutout/excess maps are displayed unchanged, without new registration, subtraction, detector modeling, pixel statistics or origin assignment.

Four fixed figures retain all seven merged broad/core profiles, both native orders and both original raw/excess pairs. Markers denote catalog/discovery coordinates rather than fitted peaks. Keep raw-only reasons and any low-reference outcome visible. Merged scales match across frames per quantity/window; native raw scales match across frames per order. Every finite value remains with a 5% margin. Raw images use separate full extrema. No smoothing, clipping, favorable epoch choice or contrast variant is introduced.

After root publishes and reads back the exact method, execute once:

```bash
python work_harps_20261103_c011_context/analysis/compare_group.py
python work_harps_20261103_c011_context/analysis/plot_group.py
```

`ROOT_RELEASE.json` must use `HARPS_C011_GROUP_RELEASE_V1` and bind verified public readback, plan, runner and inventory hashes. All previous science outputs and dispositions remain immutable.
