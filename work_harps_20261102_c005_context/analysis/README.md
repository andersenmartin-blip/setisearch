# Fixed C005 joint profile context

This prospective analysis keeps V2E2-0023, 0029, 0035, 0046 and 0054 together as C005/R005 around 3882.0375 Å. It includes all seven HD106515A spectra in the original extension02 cohort, all five discovery references and the ten historically covering native-order/raw contexts. All five U labels and previous extraction, mapping and epoch outputs remain unchanged. These are the same seven exposures used in C003 at a different wavelength; the groups are not independent exposure samples.

[PLAN.json](PLAN.json) fixes the method before new broad-window interpretation. The [input inventory](../inputs/INPUT_INVENTORY.json) and [independent input audit](../input_audit/INPUT_AUDIT.json) bind exact archived bytes and header geometry. [SYNTHETIC_PREFLIGHT.json](SYNTHETIC_PREFLIGHT.json) records a compact check without observational arrays.

## Common coordinates and complete accounting

The center is the midpoint of catalog extrema 3882.035 and 3882.040 Å. The union of all five original ±0.25 Å cores is ±0.2525 Å around that midpoint. The unchanged `arange(-300,301)/100` grid has 601 centers across ±3 Å: 51 core centers from −0.25 through +0.25 Å, and 550 surrounding-pattern centers.

Set `cb=3882.0375` and `ct=cb/(1+30.1380355615464/c)`, with the first discovery’s recorded BERV and `c=299792.458 km/s`. Barycentric profiles query `cb+x`; topocentric profiles query barycentric wavelengths `(ct+x)*(1+BERV_epoch/c)`. Every reference and native order shares this single anchor. Native wavelengths follow the unchanged zero-based pixel 0..4095 header polynomial and inherited topocentric-air convention, multiplied by `(1+BERV_epoch/c)` once. Equivalently, native wavelength queries are `(cb+x)/(1+BERV_epoch/c)` or `ct+x`.

At the recorded 59.6098131157 km/s BERV span, later feature centers can leave the fixed first-anchor topocentric core. Those core comparisons then describe the anchor coordinate window, potentially neighboring structure, not each event’s recentered feature. All five references remain; there is no fitted shift, lag, center, width, stellar velocity or instrumental drift, and no aggregate frame-origin classifier.

| Output family | Fixed accounting |
|---|---:|
| Seven merged epochs × two frames | 14 profiles |
| Five discovery exposures × orders 3/4 × two frames | 20 profiles |
| Seven merged epochs × five references × two frames × two regions | 140 comparisons |
| Ten native/order pairs × same-exposure merged × two frames × two regions | 40 comparisons |
| Identical-product self-comparisons, included above | 20 |
| Preserved raw cutouts and historical raw-excess maps | 10 panel pairs |
| Structural native-order exclusions | 0 |

The complete total is 34 profiles and 180 comparisons. Self-pairs and shared-exposure relationships are flagged; invalid selected slots retain explicit reasons. The five references are defined by C005 membership, including the May 2022 discovery V2E2-0035; they are not inherited blindly from C003 or selected from correlation outcomes.

## Native scope, signed flux and support

Saved mapping and fresh header evidence establish orders 3 and 4 as covering the original event-specific topocentric feature center for each of the five discoveries. All ten pairs and their endpoint/center evidence are explicit in PLAN and `NATIVE_ORDER_SCOPE.json`. No new mapping or additional order is selected. Historical primary, secondary and adopted review records remain distinct inputs, including the separate off-trace pixel noted in 0023/order 4 and the noisier 0054/order 4 context.

Signed source flux is always retained. Merged FLUX is header-confirmed ADU; all five native e2ds files lack BUNIT and are labeled **native extracted flux, unit unspecified**. Native/merged or cross-order scale ratios are not physical flux measurements or independent observations.

The numerical profile, frame and comparison functions are unchanged from C003. Each profile/frame uses the pooled signed median of native samples at 1.5 ≤ |frame offset| ≤ 3 Å, requiring at least 20 finite samples in each flank and a strictly positive pooled reference. Left/right counts, medians, nonpositive fractions and missing-coverage reasons remain explicit. An available median is distinct from a valid reference. There is no fitted background or continuum, and flanks are not assumed quiet. Invalid normalization retains raw-only values; no sign flip, moved flank, shrink or extrapolation makes it valid. Coordinate coverage does not establish flux/reference quality before release.

The descriptive first-difference MAD × 1.4826 / √2 proxy uses adjacent finite samples with both endpoints in the same flank and no large wavelength gap. The reference ≤ 3 × proxy flag is reported only for a valid reference; it is not formal SNR. Positive finite ERR coverage and signed nonpositive fractions are retained.

Interpolation is linear without extrapolation. Brackets above 1.51 times the full-source median barycentric wavelength spacing are masked. Raw zero-shift Pearson requires nonzero exact range and at least 80% common finite samples: **41/51 core or 440/550 surroundings**. Normalized RMS requires the same support and valid positive references on both profiles. Raw-only profiles can retain adequately covered raw comparisons while normalized results are blocked. No favorable frame or reference is chosen.

## Bounded evidence and release

Before any flux access, all seven merged and five native headers are checked for recorded identity/metadata, numeric BERV, merged wavelength/flux representation and unique required table columns, and native shape/polynomial degree/coefficients. Every frozen source and release hash is checked again after execution. Existing output directories are never overwritten; the analysis contains no network or acquisition code.

Seventeen compact pre-interpolation windows preserve source indices, original-frame and barycentric wavelengths, signed flux, ERR (NaN for unavailable native errors), full-input hashes, BERV and full-source spacing metadata. Only the union required by both fixed-frame windows plus bracketing samples is copied or analyzed. Full merged wavelength coordinates locate the slices. The ten archived raw/native NPZs are copied exactly and their historical raw cutout/excess maps displayed without a new registration, subtraction or detector statistic.

The frozen plotter produces eight figures: merged broad/core plots and three fixed pages each for native and raw contexts (4 + 4 + 2 rows in input order). All profiles, invalid-reference annotations and signed finite values remain. Merged frame scales match; native raw frame scales match per order; raw panels have separate full-value scales. No smoothing, clipping or favorable epoch selection occurs. The topocentric core’s fixed-anchor meaning is stated on the merged figures.

After public method publication and exact readback, root may execute once:

```bash
python work_harps_20261102_c005_context/analysis/compare_group.py
python work_harps_20261102_c005_context/analysis/plot_group.py
```

`ROOT_RELEASE.json` uses schema `HARPS_C005_GROUP_RELEASE_V1` and binds verified publication/readback, plan/script hashes and exact inventory path/hash. The BERV span, shape correlations and noise proxy do not calibrate significance, physical origin, line width, false-alarm probability or completeness. The original pipelines are not replayed, and the seven-epoch cohort is not an archive-wide sample.
