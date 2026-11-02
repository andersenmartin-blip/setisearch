# C002 / HD106515A: individual context complete, V2E2-0033 remains unresolved

The fixed context at **3868.6025 Å** is complete across seven existing cohort epochs: **18 profiles and 36 comparisons**, retaining the single May 2022 discovery reference and fresh native-order coverage. **V2E2-0033 remains U.** No physical-origin assignment, qualified laser candidate or calibrated null follows.

The six nonself merged-epoch comparisons per frame retain the complete ranges below. Reused spectra and self-pairs are not independent detections.

| Region | Median r, barycentric | Median r, topocentric | Range r, barycentric | Range r, topocentric |
|---|---:|---:|---:|---:|
| core | 0.966483 | -0.047896 | 0.938800–0.980641 | -0.173859–0.559801 |
| broad_pattern | 0.982187 | 0.006332 | 0.957488–0.986064 | -0.196845–0.282579 |

16 of 18 profiles have full 601-point raw coverage; 16 have usable positive normalization, 2 are raw-only and 0 are blocked. Low-reference flags are 0 true, 16 false and 2 null; unavailable normalization does not count as a false flag. All 34 evaluable Pearson and 32 normalized RMS values are retained, including 4 labelled identical-product self-comparisons. Positive finite ERR support is absent in 18 profiles.

Both order 2 profiles retain 417 of 601 grid points and lack the right reference flank. Their raw core comparisons remain evaluable; their broad raw correlations and all normalized comparisons stay unavailable under the fixed support rules. The one available flank was not substituted for the missing reference.

The method was public in `264a6d5cfd8b0b40780df1f28b65986f50659b2e` and all 25 method/input files were read back before execution. The fixed anchor is **0033, observed on 2022-05-07, with BERV −18.8907517532076 km/s**. The original ±0.25 Å core, ±3 Å context and fixed reference flanks were retained without fitted shifts, widths, stellar velocity or continuum. A fixed topocentric core may sample neighboring structure after a coherent feature leaves its window; frame correlations are not a calibrated origin test.

The original C002 core was already visible in the completed C003 surrounding window, outside its core and normalization flanks. It lies outside the C004 window, while the wider C002 context overlaps C004 by 2.3575 Å. Shared spectral pixels and the same seven observing products preclude a blind or independent validation claim. Structured flank medians are reference levels, not a proven line-free continuum or calibrated physical flux. Positive scalar normalization leaves Pearson unchanged while changing plotted heights and normalized RMS; unavailable or nonpositive references remain explicit in the outputs.

The historical raw panels, native-input identities and each mapping stage are preserved in [the inventory](inputs/INPUT_INVENTORY.json) and [closure](GROUP_CLOSURE.json). Native orders 2, 3 were freshly selected by header coverage. The historical adopted description of order 3 concerns its smoother, trace-centered central feature; order 2 is noisy. The full order 3 panel also contains a separate bright patch toward the lower right, already recorded as off-event context in the historical secondary review. That remote patch remains visible and is not assigned to the catalog event or given a new physical origin.

These inherited observations are distinct from new mapping validation. Same-exposure native/merged agreement is not independent confirmation or an origin classification. Native units are unspecified, merged ADU are uncalibrated, and unavailable ERR support and descriptive noise proxies do not provide formal significance.

| Historical order | Global grid usable | Local usable | Baseline verified | Later five-window support |
|---|---|---|---|---|
| 2 | true | false | false | true |
| 3 | true | true | true | true |

The later reference-window support does not overwrite the earlier local/baseline diagnostics or turn them into an origin classification.

[Full report and figures](analysis/RESULTS_REPORT.md) · [Scientific interpretation](scientific_review/RESULT_INTERPRETATION.md) · [All comparisons](analysis/results/COMPARISONS.csv) · [Profile quality](analysis/results/PROFILE_METRICS.csv)

[Independent reconstruction](independent_audit/NUMERICAL_AUDIT.json) passes **456 checks and 71,071 scalar comparisons**. [Input audit](input_audit/INPUT_AUDIT.json) verifies 11 exact restored inputs and fresh order-header coverage. No new archive query or observing time was added. [Preservation](preservation/README.md) retains 29 NPZs totaling 320,652 bytes: 9 source windows, 18 profiles and 2 exact raw-panel copies. Preserve published results and reproduce in a separate directory.

The next original-queue item is [C008 / V2E2-0047 at 5182.005 Å](NEXT_ACTION.json), row 17 / R009. It has one discovery reference from 2023-03-22. Its wavelength is separate from the completed blue contexts, but its original epoch/raw results and the same observations already exist. [Detailed handoff](scientific_review/NEXT_STEP.md) preserves those dependencies. Group-number order does not determine the queue.

[Current checkpoint](CONTINUATION_STATE.json) · [Project continuation](../CONTINUE_SETI.md). Original coverage remains 300 exposures, 20 stars and 70.874650833 hours, with 403 A / 46 O / 185 U / 35 M. Rubin remains stopped at limited feasibility with the minimum 50 evaluable objects unmet.
