# C008: HD106515A individual spectral context

The shallow asymmetric shoulder near 5182.005 Å and the extensive surrounding spectrum recur in barycentric coordinates across the seven existing epochs. **V2E2-0047 remains U.** The feature sits on a structured, declining spectral level; neither the high surrounding correlation nor the scaled shoulder height establishes an isolated emission line, physical origin, qualified laser candidate or calibrated null.

The single released execution completed on **2026-11-02 at 20:27:35 UTC**: **16 profiles and 32 comparisons**, including four identical-product self rows, eight bounded source windows and one exact historical raw-panel copy. All profiles and comparisons are numerically evaluable; none is raw-only, blocked or structurally excluded. The fixed discovery reference is 2023-03-22. No new acquisition or observing time was added.

## All six other epochs against the fixed discovery

The original center is **5182.005 Å** in barycentric air wavelengths. The March 2023 discovery BERV **3.26509772194068 km/s** gives the single topocentric-air anchor **5181.9485623946 Å**. The unchanged ±3 Å window has 601 centers on a 0.01 Å grid: 51 in the original ±0.25 Å core and 550 in the surroundings. The common-support minima remain 41/440. No center, width, lag, stellar velocity, drift, continuum or background was fitted.

Values separated by `/` below are barycentric/topocentric. Each row is one other epoch against the sole reference. The four self rows remain in the complete output at r = 1 to floating-point precision and normalized RMS = 0; they add no independent recurrence evidence.

| Other observation (UTC) | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 2022-01-05 | 0.844156 / 0.575803 | 0.992765 / 0.806281 | 0.084750 / 0.509993 | 0.067710 / 0.426909 |
| 2022-03-07 | 0.978778 / 0.450025 | 0.999513 / 0.905966 | 0.020252 / 0.256964 | 0.019547 / 0.290001 |
| 2022-05-07 | 0.956636 / 0.336330 | 0.999482 / 0.865459 | 0.017856 / 0.157832 | 0.016782 / 0.275959 |
| 2022-12-31 | 0.944518 / 0.652531 | 0.998986 / 0.814653 | 0.023551 / 0.486166 | 0.026441 / 0.447996 |
| 2023-05-24 | 0.956003 / 0.600615 | 0.999390 / 0.837283 | 0.019036 / 0.170176 | 0.018108 / 0.309782 |
| 2023-07-03 | 0.958837 / 0.692322 | 0.999323 / 0.828825 | 0.017774 / 0.161130 | 0.019117 / 0.317305 |

Nonself barycentric core r spans **0.844156–0.978778**, median **0.956320**; surrounding r spans **0.992765–0.999513**, median **0.999357**. All six nonself pairs have higher barycentric r and lower barycentric normalized RMS in both regions, under this fixed calculation. **January 2022 is retained as the weakest comparison**: core/surrounding r **0.844156 / 0.992765**, with the largest barycentric RMS **0.084750 / 0.067710**. The other five epochs do not replace this full range.

- [All seven epochs: full signed and scaled context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: original core](results/figures/MERGED_CORE_CONTEXT.png)

The core figure shows a shallow, multi-sample asymmetric shoulder and a dip near +0.1 Å on an elevated level. January 2022 differs visibly around that shoulder and dip. The broader figure contains an extended decline, several negative-offset dips and a deep trough near **+2 Å**. The surrounding Pearson statistic includes all of that large-scale structure; its value near one is not a separate validation of an isolated core feature. The singleton marker is the catalog/discovery coordinate, not a fitted peak in each epoch. All seven curves, full titles, legends and matching frame scales are retained.

## Fixed topocentric window

These positions were calculated from metadata before new values were read, assuming a barycentrically coherent catalog center. They are coordinate predictions, not measured peak locations.

| Observation (UTC) | Role | Predicted offset from fixed anchor (Å) | Original ±0.25 Å core |
|---|---|---:|---|
| 2022-01-05 | Other epoch | -0.464455259 | Outside |
| 2022-03-07 | Other epoch | -0.129745834 | Inside |
| 2022-05-07 | Other epoch | +0.382990647 | Outside |
| 2022-12-31 | Other epoch | -0.468551495 | Outside |
| 2023-03-22 | Discovery | +0.000000000 | Inside |
| 2023-05-24 | Other epoch | +0.478364954 | Outside |
| 2023-07-03 | Other epoch | +0.561818581 | Outside |

Five predicted centers lie outside the fixed topocentric core. Only March 2022 and the March 2023 discovery lie inside. The other comparisons may describe neighboring structure in that window, and the window is never recentered. The full BERV span of 59.6098131157401 km/s is coordinate separation, not a calibrated physical-origin test. [Prospective coordinates and caveats](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

## Reference levels, signed values and uncertainty limits

All **16 profiles have 601 finite raw and normalized grid samples**, positive valid two-flank references and false low-reference flags. Every source-window and separate flank nonpositive fraction is zero; signed values were retained without clipping. All 16 profiles have **zero positive finite ERR samples**. Full support and positive references do not provide a calibrated uncertainty model.

The 14 merged reference levels span **2321.091–7666.803 ADU**; their first-difference proxies span **59.501–123.512 ADU**. The low-reference condition, reference ≤ 3 × proxy, is descriptive and is not formal SNR. Native BUNIT is absent, so native extracted units remain unspecified.

The discovery reference has the following values in both frames:

| Product and units | Left-flank median | Right-flank median | Pooled reference | First-difference proxy |
|---|---:|---:|---:|---:|
| Merged (ADU) | 12489.915527 | 4293.377930 | 6797.728760 | 112.299945 |
| Native order 43 (unspecified) | 17151.376953 | 6103.837646 | 9506.636719 | 218.302328 |

The two flanks sample visibly different structured levels. The deep trough near +2 Å lies **inside the positive [1.5, 3] Å reference flank**; all of that structure remains in the fixed pooled median without masks or alternate flanks. These reference levels are not established line-free continua. A scaled core value around 1.6 is therefore not an emission-line strength relative to a fitted continuum. Positive scalar normalization leaves Pearson unchanged; scaled heights and RMS depend on the selected fixed levels.

## Native order and preserved raw panel

Fresh header checks of all 72 orders identify **order 43 alone** as covering the original center. Both full windows and flanks are retained. Its same-exposure native/merged comparisons are:

| Native order | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 43 | 0.999404 / 0.999404 | 0.999582 / 0.999582 | 0.007621 / 0.007621 | 0.021340 / 0.021340 |

[Native order 43](results/figures/NATIVE_ORDERS_1.png) follows the merged shape closely after separate fixed scaling, with small visible differences preserved. Native and merged products share an extraction lineage; this is not independent observing confirmation or a physical flux ratio.

[The exact historical raw cutout and excess map](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retain their complete scales. **Two bright structures at the far right edge dominate those scales**, while the nominal central band and residual are faint. The historical descriptions of an extended, trace-centered central residual and continuum variation concern the enlarged central context; they do not describe every structure in the full panel. The edge structures are retained separately from the catalog feature and receive no new origin assignment. No new pixel statistic, registration, background subtraction or spatial model was applied.

The original global, local, baseline and later five-window mapping stages are all true for order 43 and remain distinct historical diagnostics. They do not establish a new mapping result or physical origin. All primary, secondary and adopted reviews, the U label and prior outputs are unchanged. The catalog fixed-template width is not a measured physical linewidth.

## Dependence and reconstruction

The C008 window [5179.005, 5185.005] Å is disjoint from the completed C001–C007 bounded wavelength windows. Nevertheless, original epoch/profile and raw evidence for 0047 already existed, and all seven observing products are reused. This is not blind, untouched or independent observing evidence and adds no observing time or archive-wide completeness. Missing ERR and descriptive morphology do not establish significance, false-alarm probability, sensitivity or a qualified survey null.

The [independent arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **424 checks across 63,374 scalar values**, covering all eight source windows, 16 profiles, 32 comparisons, one exact raw copy and four self rows without importing production functions. Source flux, ERR, indices and profile metrics agree exactly. Maximum wavelength difference is **9.095e-13 Å**, so wavelength arrays are not bitwise exact. Maximum raw interpolation difference is **7.822e-09 native units**, normalized-profile difference **8.229e-13** and comparison difference **1.436e-15**. This verifies arithmetic rather than physical origin.

The method was public and read back before execution in commit `d194c32c3679cebb485f901ceccd1ac4786d66f6`. [Plan](PLAN.json), [root release](ROOT_RELEASE.json), [summary](results/SUMMARY.json), [bounded inputs](results/BOUNDED_INPUT_INDEX.json), [all profile metrics](results/PROFILE_METRICS.csv), [all comparisons](results/COMPARISONS.csv) and [numerical hashes](results/OUTPUT_HASHES.json) bind the run.

All four figures were visually inspected and fully decoded, with sizes and hashes checked against [PLOT_INDEX.json](results/PLOT_INDEX.json). All **45 frozen method/input sources and 35 numerical output files** remain unchanged. [RESULTS_QA.json](RESULTS_QA.json) records delivery checks. The next original-queue item is C009 / V2E2-0050; its metadata handoff preserves the root-adopted U despite earlier reviewer A assessments. No C009 analysis was executed here.
