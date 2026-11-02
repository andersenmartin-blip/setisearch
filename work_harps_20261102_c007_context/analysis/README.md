# Fixed C007 individual profile context

This prospective method follows the original queue's singleton V2E2-0026 / C007 / R008 on HD106515A at 4312.700 Å. All seven original-cohort merged epochs are retained against the one fixed discovery product, observed on 2022-01-05. The record remains U. This adds a bounded interpretation of existing evidence, not a new exposure, archive-wide sample or independent detection.

The core is already visible in completed C006: its original ±0.25 Å interval, 4312.450–4312.950 Å, falls entirely inside C006's positive normalization flank. C007 was selected by queue metadata before C006's calculation, but its subsequent flux interpretation is neither blind nor independent. The wider ±3 Å windows also overlap, and every epoch product is reused. [PLAN.json](PLAN.json) fixes this separate context before additional window values; [input inventory](../inputs/INPUT_INVENTORY.json) and [synthetic checks](SYNTHETIC_PREFLIGHT.json) bind its inputs and arithmetic.

## Geometry and complete accounting

Set `cb = 4312.700 Å`, `c = 299792.458 km/s` and `ct = cb/(1 + 30.1380355615464/c)` using the fixed discovery BERV. The common `arange(-300,301)/100` grid has 601 centers across ±3 Å. The original ±0.25 Å core contains **51 centers**, with **550 surrounding centers**. Barycentric profiles query `cb+x`; topocentric profiles query barycentric wavelengths `(ct+x)*(1+BERV_epoch/c)`. Native topocentric-air wavelengths use the unchanged zero-based polynomial on pixels 0..4095 and are multiplied by `(1+BERV_epoch/c)` once.

The six other existing epochs span the same total BERV range, 59.6098131157401 km/s, as the earlier target contexts. The fixed topocentric window does not track each later feature and can sample neighboring structure when a coherent feature leaves its core. No shift, recentering, fitted width, lag, stellar velocity, background or drift is optimized.

| Output family | Fixed accounting |
|---|---:|
| Seven merged epochs × two frames | 14 profiles |
| One discovery product × order 19 × two frames | 2 profiles |
| Seven epochs × one reference × two frames × two regions | 28 comparisons |
| One native order × same-exposure merged × two frames × two regions | 4 comparisons |
| Identical-product self-comparisons, included above | 4 |
| Preserved event raw cutout/excess pair | 1 |
| Compact source windows before interpolation | 8 |

There are **16 profile slots and 32 comparison slots**. Missing or invalid outcomes retain their slots and reasons. The same-exposure native/merged relationship and shared earlier-window pixels do not provide independent confirmation.

## Coverage, mapping and normalization

Fresh header geometry inventories every native order at this original feature center. Historical evidence identifies order 19. Coverage, polynomial metadata and original mapping stages are kept distinct. For 0026, **local_mapping_usable=false and baseline_mapping_verified=false** remain alongside true global and later five-window diagnostics. Shape agreement or a coordinate coverage check cannot retroactively promote that local raw-detector mapping. The original primary, secondary and adopted reviews remain intact.

Merged FLUX is uncalibrated ADU; native BUNIT is absent, so native extracted units remain unspecified. Signed flux is preserved. Only the source samples needed by the union of the two fixed-frame windows, plus bracketing samples, are copied. Full merged wavelength coordinates locate those slices; native coordinates derive from headers.

Profile sampling, normalization and comparison functions are unchanged from C006. Per profile/frame, the reference is the pooled signed median of native samples at 1.5 ≤ |offset| ≤ 3 Å, requiring at least 20 finite samples in each flank and a strictly positive median. Side counts, medians, nonpositive fractions, ERR support, missing-coverage reasons and available-versus-valid references are explicit. These flanks contain spectral structure and are not a fitted line-free continuum. The C006 center lies at −2.245 Å inside C007's negative flank; its neighboring catalog cores overlap that reference area. Those pre-known features are retained without masks or alternate flanks.

The descriptive first-difference proxy is 1.4826 × MAD / √2 using finite adjacent native samples in the same fixed flank without a large wavelength gap. A reference ≤ 3 × proxy flag is not formal SNR. Invalid normalization remains raw-only; there is no sign flip, moved flank, shrinkage or extrapolation.

Linear interpolation masks brackets above 1.51 times the full-source median wavelength step. Raw Pearson requires a nonzero exact range and at least 80% common finite support: **41/51 core or 440/550 surrounding centers**. Normalized RMS requires that support and valid references on both profiles. Adequately supported raw Pearson remains available for a raw-only profile. Every frame and epoch is retained, regardless of the outcome.

## Release and preservation

All seven merged headers and the native discovery header are checked before new flux access: exact identity/source hashes, recorded metadata, numeric BERV, merged barycentric-air Angstrom and ADU representation, unique WAVE/FLUX/ERR table columns, native shape and polynomial coefficients. Source and release hashes are rechecked after execution. The runner has no network code and refuses to overwrite an existing output directory.

Eight compact source NPZs retain exact source indices, original-frame and barycentric wavelengths, signed flux, ERR (NaN for unavailable native errors), hashes, BERV and full-source spacing. The one event-specific raw/native NPZ is copied exactly. Its existing cutout and raw-excess map are displayed without new registration, subtraction or detector statistics.

The fixed plotter produces four figures: all-epoch merged broad/core context, one native order context and one historical raw cutout/excess pair. The event marker denotes the catalog/discovery coordinate, not a fitted peak. Merged scales match across frames per quantity/window, and native raw scales match across frames. Every finite plotted value is retained with a 5% scale margin; raw image panels use their separate full extrema. No smoothing, clipping or favorable epoch selection is used.

After root publishes and verifies the complete method, execute once:

```bash
python work_harps_20261102_c007_context/analysis/compare_group.py
python work_harps_20261102_c007_context/analysis/plot_group.py
```

`ROOT_RELEASE.json` uses schema `HARPS_C007_GROUP_RELEASE_V1` and binds the exact public readback, plan/script and inventory hashes. This descriptive context does not identify origin, measure a physical linewidth, calibrate false alarms or establish a qualified null. Earlier pipelines, labels and completed analyses remain unchanged.
