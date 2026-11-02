# Fixed C003 joint profile context

This prospective analysis keeps V2E2-0022, 0027, 0044, 0051 and 0053 together as one C003/R003 group around 3869.75125 Å. It includes all seven HD106515A spectra in the original extension02 epoch cohort, all five discovery references and all eight historically covering native-order/raw-panel contexts. This is not archive-wide completeness. All five U labels and every historical epoch, extraction and mapping output remain unchanged.

[PLAN.json](PLAN.json) fixes the method before new broad-array interpretation. The [input inventory](../inputs/INPUT_INVENTORY.json) binds exact saved products and header evidence. The [input audit](../input_audit/INPUT_AUDIT.json) independently checks those bytes and representations. [SYNTHETIC_PREFLIGHT.json](SYNTHETIC_PREFLIGHT.json) records a compact check without observational arrays.

## Common frames and complete references

The center is the midpoint of the catalog extrema 3869.745 and 3869.7575 Å. The union of all five original ±0.25 Å cores is ±0.25625 Å around that midpoint. The unchanged `arange(-300,301)/100` grid gives 601 centers over ±3 Å: 51 core centers from −0.25 to +0.25 Å and 550 surrounding-pattern centers.

The barycentric center is `cb=3869.75125`. The fixed topocentric anchor is `ct=cb/(1+30.1380355615464/c)`, from the first discovery, V2E2-0022, with `c=299792.458 km/s`. Every reference and native profile shares that anchor. Barycentric panels query `cb+x`; topocentric panels query barycentric wavelengths `(ct+x)*(1+BERV_epoch/c)`. Native header polynomials use the unchanged zero-based pixel0..4095 and inherited topocentric-air convention; multiply by `(1+BERV_epoch/c)` once to obtain barycentric wavelengths. Equivalently the native queries are `(cb+x)/(1+BERV_epoch/c)` and `ct+x` respectively.

The seven-epoch BERV span is 59.6098131157 km/s, about 22.866 nominal resolution elements. At large BERV differences, a later discovery feature can fall outside the fixed first-anchor topocentric core. That core then describes the anchor coordinate window and potentially neighboring structure, not the later event’s recentered feature. All five references remain; there is no shift, lag, width, center, stellar-RV or drift fit and no aggregate frame-origin classifier.

| Output family | Fixed accounting |
|---|---:|
| Seven merged epochs × two frames | 14 profiles |
| Eight covering discovery/order pairs × two frames | 16 profiles |
| Seven merged epochs × five references × two frames × two regions | 140 comparisons |
| Eight native/order pairs × same-exposure merged × two frames × two regions | 32 comparisons |
| Identical-product merged self-comparisons, included above | 20 |
| Preserved raw cutouts and historical raw-excess maps | 8 panel pairs |
| Structural exclusions, never measured | 2 discovery/order pairs |

Self-pairs and shared-exposure dependencies are flagged. Thirty profiles and 172 comparisons retain invalid slots and reasons. The fixed pair lists in PLAN independently define selection; observed output keys never choose the sample.

## Native-order scope and signed profiles

| Discovery | Measured historical covering orders | Structural exclusion |
|---|---|---|
| V2E2-0022 | 2, 3 | none |
| V2E2-0027 | 2, 3 | none |
| V2E2-0044 | 2, 3 | none |
| V2E2-0051 | 3 | order 2: original feature center 3870.0700818 Å exceeds endpoint 3870.0060516 Å |
| V2E2-0053 | 3 | order 2: original feature center 3870.1324023 Å exceeds endpoint 3870.0057692 Å |

The excluded pairs are `NOT_COVERING_LINE`, not mapping failures. Their metadata and full header endpoint/center evidence remain in `NATIVE_ORDER_SCOPE.json`; no flux is read from them and no nonexistent raw panel is synthesized. The first-anchor topocentric coordinate lying inside those orders does not make the original feature line-covering.

Signed source flux is always retained. Merged FLUX has header-confirmed ADU; all five native e2ds files lack BUNIT and are labeled **native extracted flux, unit unspecified**. No native/merged or cross-order physical flux ratio is inferred.

The numerical profile and comparison functions are unchanged from C001. Each profile/frame uses the pooled signed median of native samples at 1.5 ≤ |frame offset| ≤ 3 Å, requiring at least20 finite samples separately in each flank and a strictly positive pooled reference. Left/right sample counts, medians, nonpositive fractions and missing-coverage reasons remain explicit. There is no fitted background or continuum, and the flanks are not asserted to be quiet. Invalid normalization leaves a signed raw-only profile; no sign flip, shifted flank, shrink or extrapolation makes it valid.

Header geometry establishes that the three selected order2 contexts lack their positive normalization flank in both frames. This is a missing-right-coverage condition, not evidence of nonpositive continuum. All five selected order3 contexts have full fixed-window coordinate support; their actual flux/reference quality remains unknown until release.

The descriptive first-difference MAD ×1.4826/√2 proxy uses adjacent finite samples with both endpoints in the same flank and no large wavelength gap. The low-reference flag (reference≤3×proxy) is reported only for valid references; this is not formal SNR. Positive finite ERR coverage and signed nonpositive fractions are retained.

Interpolation is linear without extrapolation. Brackets above1.51 times the full-source median barycentric wavelength spacing are masked. Unshifted raw Pearson requires nonzero exact range and at least80% common finite support: **41/51 core or440/550 surrounding points**. Normalized RMS needs the same coverage and valid positive reference scaling on both sides. A raw-only order may retain a core correlation without supplying normalized or broad support; same-exposure comparisons are not independent confirmations.

## Bounded inputs, guards and figures

All seven merged and five native product headers are checked before any flux access. The script verifies recorded identity/metadata, numeric BERV, merged wavelength/flux representations and unique required table columns, and native shape/polynomial coefficients. Every frozen source and the public release are checked again after execution. Existing output directories are never overwritten; there is no network or acquisition code.

Fifteen compact pre-interpolation windows preserve source indices, original-frame and barycentric wavelengths, signed flux, ERR (NaN for unavailable native errors), source hashes, recorded BERV and full-source spacing. Only the union required by both fixed frame windows and bracketing points is copied or analyzed. The full merged wavelength vector only locates those slices. Eight archived raw/native NPZs are copied exactly; their historical raw cutout and raw-excess maps remain context with separate panel scales, not a new mapping or subtraction.

The frozen plotter produces six figures: all seven merged broad/core profiles, all eight native-order contexts in two fixed four-row pages, and all eight preserved raw-panel pairs in two fixed four-row pages. Signed values, invalid-reference annotations and all finite points remain. Merged frame scales match; native raw scales match between frames for each order. No smoothing or favorable epoch selection is introduced. The topocentric core’s fixed-anchor meaning appears on the merged plots.

After exact public method publication and readback, root may execute once:

```bash
python work_harps_20261102_c003_context/analysis/compare_group.py
python work_harps_20261102_c003_context/analysis/plot_group.py
```

`ROOT_RELEASE.json` requires schema `HARPS_C003_GROUP_RELEASE_V1`, verified publication commit/readback, plan/script hashes and exact inventory path/hash. The larger BERV span does not itself calibrate frame discrimination, line identity, origin, uncertainty, false-alarm rate or survey completeness. This is one fixed post-detection context comparison; no original pipeline is replayed or U label changed.
