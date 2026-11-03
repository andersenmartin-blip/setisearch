# Fixed C009 individual spectral context

This prospective method follows original queue row 18: singleton **V2E2-0050 / C009 / R010** on HD106515A at **6802.02 Å**. All seven original-cohort merged epochs are retained against the fixed discovery product observed on **2023-03-22**. The record remains U. This is bounded descriptive context, not a new exposure, archive-wide sample or independent detection.

The original core [6801.77, 6802.27] Å and full window [6799.02, 6805.02] Å are disjoint from completed C001–C008 bounded windows. However, original epoch/profile and raw evidence already exist for this record, and the same seven observations are reused. A distinct wavelength region does not make this blind, untouched or independent evidence. [PLAN.json](PLAN.json), [the input inventory](../inputs/INPUT_INVENTORY.json) and [synthetic checks](SYNTHETIC_PREFLIGHT.json) bind the method before new observed array access.

## Geometry and accounting

Set `cb = 6802.02 Å`, `c = 299792.458 km/s` and `ct = cb/(1 + 3.26509772194068/c) = 6801.945918689643 Å`, using the **March 2023 discovery BERV**. No earlier May, March 2022 or January anchor is inherited. The `arange(-300,301)/100` grid has 601 centers across ±3 Å, including **51 original core centers** and **550 surrounding centers**. Barycentric profiles query `cb+x`; topocentric profiles query barycentric wavelengths `(ct+x)*(1+BERV_epoch/c)`. Native topocentric-air wavelengths use the unchanged zero-based polynomial on pixels 0..4095 and are multiplied by `(1+BERV_epoch/c)` once.

The seven epochs span 59.6098131157401 km/s in BERV. This is coordinate separation, not a calibrated origin test. The fixed topocentric window does not track other features and can sample neighboring structure when their coherent centers leave the core. No shift, recentering, fitted width, lag, stellar velocity, continuum, background or drift is optimized.

| Output family | Fixed accounting |
|---|---:|
| Seven merged epochs × two frames | 14 profiles |
| One discovery product × order 70 × two frames | 2 profiles |
| Seven epochs × one reference × two frames × two regions | 28 comparisons |
| Native order × same-exposure merged × two frames × two regions | 4 comparisons |
| Identical-product self-comparisons, included above | 4 |
| Preserved raw cutout/excess pair | 1 |
| Compact source windows before interpolation | 8 |

There are **16 profile slots and 32 comparison slots**. Missing or invalid outcomes retain their slots and reasons. Same-exposure native/merged agreement is not independent confirmation or a physical flux ratio.

## Fresh native scope and signed reference levels

The fresh scan of all **72 native order headers** identifies **order 70 alone** as covering the original feature center. Its topocentric endpoints are [6759.84721690394, 6836.063260095031] Å. Both complete ±3 Å windows, their cores and both reference flanks fit inside those endpoints in their respective frames. This geometry does not establish finite flux, positive reference levels, false low-reference flags or usable statistics.

All historical global, local, baseline and later five-window mapping diagnostics are true for this order. These stages and all primary, secondary and adopted reviews remain distinct and unchanged. They are preserved historical evidence, not a new registration or physical-origin validation.

**The current adopted classification is U.** Historical primary and secondary reviews provisionally voted A after describing a compact slanted concentration in order 70. The secondary also retained broader residual structure and could not exclude an underlying spectral contribution. Root adopted U because a possible artifact/spectral blend remained unresolved. The complete compact and broader raw structures, both earlier votes and the root adoption are preserved; future shape comparisons do not silently replace that adoption or qualify a laser candidate.

Merged FLUX is uncalibrated ADU. Native BUNIT is absent, so native values retain unspecified extracted units. Signed flux is preserved. Only available source samples needed by the union of both fixed-frame windows, plus bracketing samples, are copied. Full merged wavelength coordinates locate those slices; native coordinates derive from headers.

Sampling, normalization and comparison functions are unchanged from validated C008. Per profile/frame, the reference is the pooled signed median of native samples at **1.5 ≤ |offset| ≤ 3 Å**, requiring at least 20 finite samples in each flank and a strictly positive pooled median. Side coverage, finite counts, medians, nonpositive fractions, ERR support, available versus valid reference and failure reasons stay explicit. The complete fixed flanks are retained; any neighboring structure remains in the reference. These are descriptive levels, not established line-free continua.

The first-difference proxy is 1.4826 × MAD / √2 using finite adjacent source samples in the same fixed flank without a large wavelength gap. The reference ≤ 3 × proxy flag is not formal SNR and is evaluated only for a valid reference. Invalid normalization stays raw-only; no sign flip, moved flank, shrunken window or alternate background is permitted.

Raw Pearson requires a nonzero exact range and at least 80% common finite support: **41/51 core or 440/550 surrounding centers**. Normalized RMS requires the same support gate with valid references. Adequately covered raw Pearson remains available for a raw-only profile. Linear interpolation masks brackets above 1.51 times the full-source median wavelength step and never extrapolates. All outcomes remain in the output.

## Release and preservation

All seven merged headers and the discovery native header are checked before new flux access: exact identities/hashes, metadata, numeric BERV, merged barycentric-air Angstrom and ADU representation, unique WAVE/FLUX/ERR single-exposure tables, native shape and polynomial coefficients. The runner has no network code, rechecks frozen sources and release hashes after execution, and refuses to overwrite existing results.

Eight compact source NPZs preserve exact source indices, original-frame and barycentric wavelengths, signed flux, ERR (NaN where native errors are unavailable), source hashes, BERV and full-source spacing. The historical 0050 raw/native NPZ is copied exactly. Its original cutout and raw-excess map are displayed without new registration, subtraction, detector modeling or pixel statistics.

Four fixed figures retain all-epoch merged broad/core context, the native order and the preserved raw cutout/excess pair. The marker denotes the catalog/discovery coordinate, not a fitted peak. Any raw-only reasons remain explicit. Merged scales match across frames per quantity/window; native raw scales match across frames. All finite plotted values are retained with a 5% scale margin. Raw images use separate full extrema. No smoothing, clipping or favorable epoch selection is used.

After root publishes and verifies the exact method, execute once:

```bash
python work_harps_20261103_c009_context/analysis/compare_group.py
python work_harps_20261103_c009_context/analysis/plot_group.py
```

`ROOT_RELEASE.json` uses schema `HARPS_C009_GROUP_RELEASE_V1` and binds verified public readback, plan/script and inventory hashes. This descriptive context does not identify physical origin, measure a linewidth, calibrate false alarms, establish sensitivity or produce a qualified null. Previous pipelines, labels and completed contexts remain unchanged.
