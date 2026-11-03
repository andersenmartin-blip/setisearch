# Fixed C015 individual spectral context

This prospective method follows original queue **row 28**: **V2E2-0095 / C015 / R016** on **HD114386**, exact original catalog center **3869.915 Å** barycentric air. Primary, secondary and adopted reviews remain **U/U/U**. All four C016 joint members remain complete. Completed NORMALIZATION_CONTEXT routes C013/0092 and C014/0104 remain skipped; unresolved physical origin does not justify replaying completed diagnostics.

Use **HD114386's same seven existing January 2022–August 2023 observations**, with **one fixed reference**: `ADP.2022-05-17T01:02:16.724`, observed **2022-05-16**, BERV **−10.767337430651 km/s**. That product was one of C016's four discoveries, but C015 restores the singleton design with its own wavelength-specific anchor. C016's midpoint, common-core edge caveats, four reference families/markers and order-19 scope do not apply.

The original ±0.25 Å core is **[3869.665,3870.165] Å**, full ±3 Å context **[3866.915,3872.915] Å**. Both are disjoint from C016's order-19 wavelength context and the completed same-target 0092/0104 normalization windows. Numeric overlaps with C002/C003/C004 on HD106515A and C011/C012 on HD112410 share no observing products or source pixels. Original 0095 epoch/profile/raw evidence already exists, as do all seven observations. No blind, untouched, independent-data or new observing-time claim follows.

[PLAN.json](PLAN.json), [the fresh inventory](../inputs/INPUT_INVENTORY.json) and [synthetic checks](SYNTHETIC_PREFLIGHT.json) bind this method before observed values are read.

## Fixed geometry and accounting

Set `cb=3869.915 Å`, `c=299792.458 km/s` and **`ct=cb/(1-10.767337430651/c)=3870.0539967497375 Å`**, recomputed at this wavelength from the May discovery. The `arange(-300,301)/100` grid has **601 centers** across ±3 Å: **51** in the exact original ±0.25 Å core and **550** surrounding centers. Barycentric profiles query `cb+x`; fixed topocentric profiles query barycentric wavelengths `(ct+x)*(1+BERV_epoch/c)`. Native topocentric-air wavelengths use the unchanged zero-based polynomial on pixels 0..4095, multiplied by `(1+BERV_epoch/c)` once.

The own-target BERV span is **51.572001697156 km/s**. It supplies coordinate separation rather than calibrated origin discrimination. A coherent catalog center can leave the fixed topocentric core, allowing neighboring structure into a comparison. No center, width, lag, RV, continuum, background, drift or alignment is fitted.

| Output family | Fixed accounting |
|---|---:|
| Seven merged epochs × two frames | 14 profiles |
| One discovery/order 3 context × two frames | 2 profiles |
| Seven epochs × one reference × two frames × two regions | 28 comparisons |
| Native context × own same-exposure merged × two frames × two regions | 4 comparisons |
| Identical-product self rows included above | 4 |
| Exact historical raw cutout/excess pair retained | 1 |
| Compact pre-interpolation source windows | 8 |

There are **16 profile slots and 32 comparison slots**. Every missing, insufficient, nonpositive, low or invalid outcome retains its slot and reason. The six nonself epochs use the same unchanged May reference. Native and merged products share exposure and extraction lineage, so agreement is dependent evidence rather than another observation or a physical flux ratio.

## Fresh native scope and historical mapping

A fresh scan of **all 72 order headers** confirms **order 3 alone** covering 0095's original feature coordinate. Its topocentric endpoints are **[3851.27166904696,3894.4973838317906] Å**. Both frames have full context/core/flank geometry: **601 grid centers, 51 core and 550 surrounding centers**. Order 2 ends at 3870.006986547364 Å topocentric, below the original feature coordinate 3870.0539967497375 Å, and does not cover that center. The fresh scope confirms the historical order 3 context; C016 order 19 is not imported. Coordinate coverage does not establish finite flux, positive references, false low flags or usable comparisons. No C016 quality outcome is assumed.

Original C015/order 3 retains true **global-grid, original local usable, original baseline verified and later five-window support**. Each historical stage remains distinct from flux quality and physical origin. A separate other-wavelength registration discrepancy is not transferred to this context.

Historical reviews describe a broad multi-sample native feature and diffuse smooth trace-associated enhancement without a distinct charge track. Exact texts, saved pixels and qualifications remain preserved. No shape, correlation, structured flank or mapping flag changes **U/U/U**, identifies origin or qualifies a laser candidate.

## Signed reference rule and comparisons

Merged flux retains uncalibrated ADU units. Native BUNIT is absent in the fresh inventory, so native extracted units remain unspecified. Signed flux is never clipped or sign-flipped. Only source slices required by the union of both fixed-frame windows, plus interpolation brackets, are copied. Full merged coordinates locate those slices; native coordinates derive from recorded headers.

Sampling, normalization and comparison functions remain unchanged from C016 and the preceding singleton methods. Per profile/frame, the reference is the pooled signed median of original source samples at **1.5 ≤ |offset| ≤ 3 Å**, requiring **at least 20 finite samples in each flank and a strictly positive pooled median**. Preserve geometric/native/finite counts, separate medians and nonpositive fractions, available versus valid references, ERR support and failure reasons. All fixed-flank structure remains; these are descriptive levels rather than established line-free continua.

The first-difference proxy is `1.4826 × MAD / sqrt(2)` from finite adjacent source samples in the same flank without a large wavelength gap. The low-reference rule `reference ≤ 3 × proxy` applies only to valid normalization and is not formal SNR. Missing, insufficient or nonpositive references remain raw-only with null low flags; valid but low references retain true flags. No moved flank, smaller window or fitted replacement is introduced.

Raw Pearson requires nonzero exact range and at least **41/51 core or 440/550 surrounding common finite grid values**. Normalized RMS uses the same gate with valid references. An adequately covered raw-only profile may retain raw Pearson. Linear interpolation masks brackets above 1.51 times the full-source median wavelength step and never extrapolates. Interpolated samples and self rows remain dependent. ERR support and descriptive proxies do not establish calibrated significance, sensitivity, false alarms or a qualified survey null.

## Release, complete figures and preservation

All seven merged headers and the May discovery native header are checked before new flux access: exact identity/hash/metadata, numeric BERV, merged barycentric-air Angstrom/ADU and unique WAVE/FLUX/ERR single-exposure tables, native shape and polynomial coefficients. The runner has no network code, checks frozen sources/release hashes before and after execution and refuses to overwrite a result directory.

Eight compact source NPZs retain exact indices, original-frame and barycentric wavelengths, signed flux, ERR (NaN where native errors are unavailable), BERV, hashes and full-source spacing. The original 0095/order 3 raw/native NPZ is copied byte for byte. Saved cutout/excess maps are displayed unchanged, without new registration, subtraction, detector modeling, pixel statistics or origin assignment.

Four fixed figures retain all seven merged broad/core profiles, the native context and the original raw/excess pair. The exact 0095/R016 marker denotes the catalog/discovery coordinate rather than a fitted peak. Keep raw-only reasons and any low-reference outcome visible. Merged scales match across frames per quantity/window; native raw scales match across frames. Every finite value remains with a 5% margin. Raw images use separate full extrema. No smoothing, clipping, favorable epoch/reference choice or contrast variant is introduced.

After root publishes and reads back the exact method, execute once:

```bash
python work_harps_20261103_c015_context/analysis/compare_group.py
python work_harps_20261103_c015_context/analysis/plot_group.py
```

`ROOT_RELEASE.json` must use `HARPS_C015_GROUP_RELEASE_V1` and bind verified public readback plus plan, runner and inventory hashes. All prior science outputs and classifications remain immutable.
