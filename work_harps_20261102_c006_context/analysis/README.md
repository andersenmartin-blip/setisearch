# Fixed C006 joint profile context

This prospective analysis keeps all three HD106515A records V2E2-0025, 0042 and 0043 together around 4310.455 Å. The group includes both R006 and R007 neighborhoods and all seven original-cohort merged epochs. There are **two unique discovery products**, because 0042 and 0043 share the 2022-12-31 exposure. They remain separate catalog records and raw-panel histories, but they are never treated as separate product references or independent observing time. All three labels remain U.

[PLAN.json](PLAN.json) fixes the method before new broad-window interpretation. The [input inventory](../inputs/INPUT_INVENTORY.json) binds exact archived bytes, historical mapping reviews and fresh header geometry. [SYNTHETIC_PREFLIGHT.json](SYNTHETIC_PREFLIGHT.json) checks method behavior without observational arrays. Previous groups used the same seven exposure products at other wavelengths; this is additional wavelength context, not additional exposure coverage or an archive-wide sample.

## Coordinates and complete accounting

The catalog centers 4310.585, 4310.305 and 4310.605 Å give midpoint 4310.455 Å and a connected union of their original ±0.25 Å cores, from 4310.055 to 4310.855 Å. The common `arange(-300,301)/100` grid has 601 centers across ±3 Å: **81 core centers from −0.40 through +0.40 Å and 520 surrounding centers**. Joint-window correlation is not an independent measurement of each neighboring feature.

Set `cb=4310.455` and `ct=cb/(1+30.1380355615464/c)`, using the first discovery's BERV and `c=299792.458 km/s`. Barycentric profiles query `cb+x`; topocentric profiles query barycentric wavelengths `(ct+x)*(1+BERV_epoch/c)`. All references and native orders share that anchor. Native wavelengths use the unchanged zero-based pixel 0..4095 header polynomial and inherited topocentric-air convention, multiplied by `(1+BERV_epoch/c)` once.

The two discovery products have near-matched BERV, 30.1380355615464 and 30.3750612537025 km/s. The other five existing epochs provide the wider 59.6098131157401 km/s span. Later features can leave the fixed topocentric core, which can then sample neighboring structure. No recentering, fitted shift, width, lag, stellar velocity or instrumental drift is used. Displays retain all three event coordinates, both R006/R007 labels and all raw panels.

| Output family | Fixed accounting |
|---|---:|
| Seven merged epochs × two frames | 14 profiles |
| Two unique discovery products × order 19 × two frames | 4 profiles |
| Seven epochs × two unique references × two frames × two regions | 56 comparisons |
| Two native/order pairs × same-exposure merged × two frames × two regions | 8 comparisons |
| Identical-product self-comparisons, included above | 8 |
| Event-specific stored raw cutout/excess pairs | 3 |
| Compact source windows before interpolation | 9 |

The total is 18 profiles and 64 comparison slots. Product references, native inputs and shared profiles are deduplicated; 0042/0043's overlapping saved raw pixels remain historical context rather than independent confirmations. Missing or invalid outcomes retain explicit slots and reasons.

## Native coverage, mapping and signed flux

Fresh header coverage is checked at this wavelength. Historical mapping identifies order 19 for all three records; the two unique discovery/order combinations are the numerical native scope. Header coverage and all historical event-specific mapping statuses are retained separately. In particular, 0025 has **local_mapping_usable=false and baseline_mapping_verified=false** in the saved mapping, while its global/five-window diagnostics pass. A fresh coordinate check or favorable shape agreement cannot retroactively promote that local mapping. The separate off-trace feature recorded for 0042 is also preserved.

Signed source flux is retained. Merged FLUX is header-confirmed ADU; native e2ds BUNIT is unspecified. Scale ratios between extraction products are not physical flux measurements or independent observations. Only the bounded union needed by the two frame windows, plus bracketing samples, is copied. Full merged wavelength coordinates locate the slices; native coordinates derive from headers.

Numerical sampling, profile normalization and comparison functions are unchanged from C005; only group geometry, unique identities and accounting change. Each profile/frame uses the pooled signed median of native samples at 1.5 ≤ |frame offset| ≤ 3 Å, requiring at least 20 finite samples in each flank and a strictly positive pooled reference. Counts, side medians, nonpositive fractions, ERR support and missing-coverage reasons are explicit. The available median is distinct from a valid reference. Flanks can contain spectral structure; no background or quiet continuum is fitted. The catalog center of the next C007 record, 4312.700 Å, lies at +2.245 Å inside this positive flank. That known neighboring structure stays in the fixed reference window; it is not masked or treated as quiet continuum. C007 will overlap this broad context and cannot be counted as independent exposure or pixel evidence.

The first-difference MAD × 1.4826 / √2 proxy uses adjacent finite native samples with both endpoints inside the same flank and no large wavelength gap. A reference ≤ 3 × proxy flag is descriptive, not formal SNR. Invalid normalization keeps signed raw-only arrays; no sign flip, moved flank, extrapolation or shrink makes it valid.

Linear interpolation masks brackets above 1.51 times the full-source median wavelength step and never extrapolates. Raw unshifted Pearson requires nonzero exact range and at least 80% common finite support: **65/81 core or 416/520 surroundings**. Normalized RMS requires that support and valid positive references on both profiles. Raw-only profiles can retain adequately covered raw Pearson. No frame or reference is selected by the outcome.

## Frozen release and plots

All seven merged and two native headers are verified before flux access: identity and recorded metadata, numeric BERV, merged barycentric-air wavelength/ADU flux representation and unique table columns, native shape and polynomial coefficients. Frozen source and release hashes are rechecked after execution. Existing output directories are never overwritten. The runner contains no network or acquisition code.

Nine compact source NPZs retain original indices, original-frame and barycentric wavelength, signed flux, ERR (NaN where native errors are unavailable), source hashes, BERV and full-source spacing metadata. Three raw/native NPZs are copied exactly from the saved event panels. Their raw cutout and stored raw-excess maps are displayed without new mapping, subtraction or detector statistics.

The frozen plotter makes four figures: merged broad/core comparisons, both unique native contexts and all three preserved raw panels. Merged frame scales match for each quantity/window; native raw scales match across frames for each order. Every finite plotted value has a 5% scale margin, except raw image panels which use separate full extrema. No smoothing, clipping or favorable epoch selection is allowed. All record markers show catalog/discovery coordinates, not fitted feature positions.

After root publishes the complete method and verifies exact readback, execute once:

```bash
python work_harps_20261102_c006_context/analysis/compare_group.py
python work_harps_20261102_c006_context/analysis/plot_group.py
```

`ROOT_RELEASE.json` uses `HARPS_C006_GROUP_RELEASE_V1` and binds public readback, plan/script hashes and inventory path/hash. These descriptive correlations do not identify a physical origin, calibrate false alarms, measure physical line widths or yield a qualified null result. Previous pipelines, dispositions and completed group analyses remain unchanged.
