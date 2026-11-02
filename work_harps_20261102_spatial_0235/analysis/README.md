# Fixed spatial-support diagnostic for V2E2-0235

This is a separate, post-hoc diagnostic of the existing discovery exposure. It quantifies disagreement with a local empirical spatial template; it does not classify a cosmic ray, identify physical origin, alter the historical extraction, or change U. Both closed temporal-comparison phases remain unchanged.

The exact input identity is discovery `ADP.2023-02-23T01:01:36.791`, raw `HARPS.2023-02-22T07:40:53.531`, ancillary `ADP.2023-02-23T01:01:36.792`, zero-based native order 50 / pixel 956. The inherited detector location is raw row 3139, stitched column 2323.7701943175816. The preserved row/argument flips make the order-50 trace polynomial argument equal to zero-based raw row. No coordinate is refitted.

[PLAN.json](PLAN.json) fixes the method and all source hashes before reading target/control values. [Input inventory](../inputs/INPUT_INVENTORY.json), [trace metadata](../inputs/TRACE_METADATA.json) and the [neighbor geometry audit](../input_audit/NEIGHBOR_GEOMETRY_AUDIT.json) establish byte provenance and orientation without inspecting those values.

## Pixels and held-out controls

Raw dispersion runs along rows; cross-dispersion runs along columns. The original mosaic is `hstack([HDU1[:,50:2098], HDU2[:,50:2098]])`. All selected pixels are on HDU2, with physical column `stitched_column − 2048 + 50`.

| Partition | Fixed relative raw rows | Count |
|---|---|---:|
| Target | −5 through +5 | 11 |
| Original flank union | [−280,−80) and [81,281) | 400 |
| Held-out controls | Eight windows of center ±5 | 88 |
| Training | Flanks excluding every control center ±10 | 232 |
| Unused control buffers | Remaining excluded flank rows | 80 |

Control centers are −255, −205, −155, −105, +106, +156, +206 and +256. Every background pixel follows its row's partition, so target/control pixels never enter training. Native-relative flank [−280,−80) maps to raw absolute [3220,3420), while native-relative [81,281) maps to [2859,3059). Their labels reverse under the row flip; their sorted raw-offset union is the same.

Each observed row contributes 25 native columns around its rounded inherited trace center. All **331 × 25 = 8,275 observed pixels**, their raw/chip/stitch coordinates, trace centers and partition indices are saved before template fitting in `results/SELECTED_NATIVE_PIXELS.npz`. The buffer rows are not interpreted. Target/control values remain native, with no interpolation or clipping.

## Fixed template and model

For each row, the background is the median of native pixels at true trace distance 9–12 pixels. The separate negative- and positive-outer medians and outer MAD × 1.4826 are recorded as descriptive context; they are not alternate fits or formal noise uncertainties. Pixel counts depend on the actual fractional trace position and are retained.

Training rows alone are interpolated onto integer true-offset coordinates −8 through +8 after background subtraction. Each is divided by its signed net grid sum if positive; invalid/nonpositive rows retain explicit dispositions. The pointwise median is divided by its positive signed sum, preserving every negative template value. There is no clipping or positivity projection.

All three declared templates are reported: pooled training (minimum 200 of 232 rows), negative-raw-flank training (minimum 100 of 116), and positive-raw-flank training (minimum 100 of 116). The two flank-only templates are fixed sensitivity comparisons, with no selection of a preferred result.

For each target/control row, the fixed template is evaluated at the exact fractional offsets of the observed native pixels with |offset| ≤ 8, then normalized by its signed sampled sum. One signed ordinary least-squares amplitude is fitted:

`A = dot(T, raw − background) / dot(T, T)`

`model = background + A × T`

The background stays fixed; no intercept, slope, center, width, extraction or outlier rejection is fitted. Inadequate training or invalid windows produce explicit blocked records. All 27 template/window slots are retained, and the selected raw-pixel archive survives a support failure.

## Descriptive outputs

The primary statistic is residual off-trace L1 fraction: the sum of absolute residuals at 3 < |offset| ≤ 8 divided by the sum at |offset| ≤ 8, with an explicit zero-denominator flag. On/off-band pixel counts and mean absolute residual per pixel expose their unequal areas. Signed residual sum, negative residual sum, maximum-pixel L1 concentration and L1 centroids are also retained. Positive residual total/centroids are separately named quantities; they are not photon fractions or charge probabilities.

All eight coordinate-selected controls are reported individually, including amplitude, background and outer-noise-proxy context. Counts of controls at least as large as the target are uncalibrated local comparisons, not p-values, detection significance or a classifier. Shared exposure and order structure make the windows dependent.

Figures retain raw/model/residual maps for the target under every template, pooled maps for the target and all controls, and all three templates' control metrics. Observed image pixels use nearest-pixel display. Each raw/model pair shares its native minimum/maximum scale; all residual maps share one symmetric scale across windows and templates. No visual smoothing or favorable template selection is used.

## Release and execution

`ROOT_RELEASE.json` must use schema `HARPS_SPATIAL_0235_RELEASE_V1` and bind the verified public publication commit/readback, exact plan/script hashes and exact input-inventory path/hash. Every frozen source and the raw bytes are checked before any array access and again after analysis. Existing results are never overwritten. There is no network code.

Root may execute only after public release:

```bash
python work_harps_20261102_spatial_0235/analysis/measure_spatial.py
python work_harps_20261102_spatial_0235/analysis/plot_spatial.py
```

The pooled and both flank-only outcomes will be reported together, including unfavorable or blocked results. Source files, plans and historical outputs remain unchanged.

The nearest fiber-B order-49 FP calibration trace is approximately +16.354 pixels from the science trace. No neighboring trace center lies within ±12, but the positive background band is only 4.35–7.35 pixels from that FP center; unknown wings may contaminate background or template. A two-sided median does not demonstrate absence of contamination. Fiber B is not a sky reference. Other limitations include fractional-phase interpolation in training, profile variation/curvature, extraction and response differences, and unavailable gain/read-noise/Poisson/bias/flat uncertainty modeling. The result can describe residual spatial support, not physical origin.
