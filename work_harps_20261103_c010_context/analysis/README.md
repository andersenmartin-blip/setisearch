# Fixed C010 individual spectral context

This prospective method follows original queue row 23: singleton **V2E2-0086 / C010 / R011** on **HD112410**. The exact catalog center is **3823.0649999999996 Å** in barycentric air wavelengths. Figure titles may display 3823.065 Å for readability; the scientific constant and saved plan retain the exact original float. The adopted record remains U.

The target and cohort change from the completed HD106515A contexts. Retain **HD112410's own seven existing observations from April–August 2025** against the one fixed discovery product `ADP.2025-04-30T01:01:50.866`, observed on **2025-04-29**. No earlier target's seven products, reference, BERV span or numeric anchor is transferred. Original epoch/profile and raw evidence for 0086 already exist, so this is post-detection descriptive context rather than blind or independent new observing evidence. No new acquisition or observing time is added.

The exact original core is [3822.8149999999996,3823.3149999999996] Å and the full context [3820.0649999999996,3826.0649999999996] Å. They are disjoint from completed C001–C009 bounded windows. [PLAN.json](PLAN.json), [the inventory](../inputs/INPUT_INVENTORY.json) and [synthetic checks](SYNTHETIC_PREFLIGHT.json) bind this method before new observed values are interpreted.

## Fixed geometry and accounting

Set `cb=3823.0649999999996 Å`, `c=299792.458 km/s` and `ct=cb/(1+3.40485846065643/c)=3823.0215804708346 Å`, using the **April 2025 HD112410 discovery BERV**. The `arange(-300,301)/100` grid has **601 centers** across ±3 Å: **51** in the original ±0.25 Å core and **550** in the surrounding pattern. Barycentric profiles query `cb+x`; fixed topocentric profiles query barycentric wavelengths `(ct+x)*(1+BERV_epoch/c)`. Native topocentric-air wavelengths use the unchanged zero-based polynomial on pixels 0..4095 and are multiplied by `(1+BERV_epoch/c)` once.

The own-target BERV span is **21.30284860830273 km/s**. This provides coordinate separation, not calibrated physical-origin discrimination. The topocentric window is fixed and can sample neighboring structure if an epoch's coherent catalog center leaves its original core. No center, width, lag, stellar velocity, continuum, background, drift or frame alignment is fitted.

| Output family | Fixed accounting |
|---|---:|
| Seven own-target merged epochs × two frames | 14 profiles |
| One discovery product × order 1 × two frames | 2 profiles |
| Seven epochs × one reference × two frames × two regions | 28 comparisons |
| Native order × same-exposure merged × two frames × two regions | 4 comparisons |
| Identical-product self rows included above | 4 |
| Preserved historical raw cutout/excess pair | 1 |
| Compact pre-interpolation source windows | 8 |

There are **16 profile slots and 32 comparison slots**. Every missing or invalid result retains its slot and reason. Native and merged products share an exposure and extraction lineage, so agreement between them is dependent evidence rather than another observation or a physical flux ratio.

## Fresh native scope and historical mapping limits

A fresh scan of all **72 native order headers** identifies **order 1 alone** covering the original center. Its topocentric endpoints are [3803.1337172151,3845.8145628369703] Å. The full ±3 Å context, original core and both fixed reference flanks are geometrically covered in both frames. This geometry does not establish finite flux, positive reference medians, false low-reference flags or usable statistics; those remain runtime checks.

**Preserve each historical registration stage.** Order 1 has global-grid support **true**, original local usable **false**, original baseline verified **false** and later five-window reference support **true**. Later supported reference geometry does not retroactively repair the original local/baseline limits. Fresh wavelength coverage or native/merged similarity does not validate raw-detector registration.

The historical primary, secondary and adopted reviews all retain **U**. They describe a broad native bump and diffuse trace-confined enhancement without an unambiguous compact charge deposit. All exact review texts, pixels and qualifications remain preserved. No shape correlation, broad structure or mapping flag silently promotes the record, identifies physical origin or qualifies a laser candidate.

## Signed reference rule and comparisons

Merged flux retains uncalibrated ADU units. Native BUNIT is absent, so native extracted units remain unspecified. Signed flux is never clipped or sign-flipped. Only source samples required by the union of the two fixed-frame windows plus bracketing samples are copied; full merged coordinates locate those slices and native coordinates derive from recorded headers.

Sampling, normalization and comparison functions are unchanged from C009. The header-validation function changes only its explicit target check to HD112410; the scope constants and validation/main identifiers change to the new cohort. Per profile and frame, the reference is the pooled signed median of original native samples at **1.5 ≤ |offset| ≤ 3 Å**, requiring **at least 20 finite samples separately in each flank and a strictly positive pooled median**. Coverage, native/finite counts, separate medians and nonpositive fractions, available versus valid references, ERR support and failure reasons remain explicit. Complete fixed flanks retain all spectral structure; they are descriptive levels rather than established line-free continua.

The first-difference proxy is `1.4826 × MAD / sqrt(2)` from finite adjacent source samples in the same fixed flank without a large wavelength gap. The low-reference rule `reference ≤ 3 × proxy` applies only to valid normalization and is not formal SNR. Invalid normalization remains raw-only. Missing or nonpositive references never cause moved flanks, a smaller window or a fitted replacement.

Raw Pearson requires nonzero exact range and at least **41/51 core or 440/550 surrounding common finite grid values**. Normalized RMS uses the same support gate with valid references. Adequately covered raw Pearson remains evaluable for a raw-only profile. Linear interpolation masks brackets above 1.51 times the full-source median wavelength step and never extrapolates. Neither these interpolated samples nor self rows are independent evidence. ERR availability and descriptive proxies do not establish calibrated significance, sensitivity, false-alarm rate or a qualified null.

## Release, plots and preservation

All seven target-specific merged headers and the April 2025 native header are checked before new flux access: exact identity/hash/metadata, numeric BERV, merged barycentric-air Angstrom/ADU representation and unique WAVE/FLUX/ERR single-exposure tables, native shape and polynomial coefficients. The runner has no network code, checks all frozen sources and release hashes before and after execution, and refuses to overwrite a prior result directory.

Eight compact source NPZs retain exact original indices, original-frame and barycentric wavelengths, signed flux, ERR (NaN where native errors are unavailable), BERV, source hashes and full-source spacing. The historical 0086 raw/native NPZ is copied byte for byte. Its saved cutout and excess map are displayed unchanged without new registration, subtraction, detector modeling, pixel statistics or origin assignment.

Four fixed figures retain all seven merged broad/core profiles, the native context and the original raw/excess pair. The marker denotes the catalog/discovery coordinate rather than a fitted peak. Keep any raw-only reasons, partial coverage and low-reference outcome visible. Merged scales match across frames per quantity/window; native raw scales match across frames per order. Every finite value is retained with a 5% margin. Raw images use separate full extrema; no smoothing, clipping, favorable epoch selection or contrast variant is introduced.

After root publishes and reads back the exact method, execute once:

```bash
python work_harps_20261103_c010_context/analysis/compare_group.py
python work_harps_20261103_c010_context/analysis/plot_group.py
```

`ROOT_RELEASE.json` must use `HARPS_C010_GROUP_RELEASE_V1` and bind verified public readback plus plan, runner and inventory hashes. This bounded context does not measure a physical linewidth, establish a line identity or physical origin, calibrate false alarms, estimate sensitivity or produce a qualified survey null. Previous science outputs and dispositions remain immutable.
