# C008 / HD106515A: individual context complete, V2E2-0047 remains unresolved

The fixed context at **5182.005 Å** is complete across seven existing cohort epochs: **16 profiles and 32 comparisons**, retaining the single March 2023 discovery reference and fresh native-order coverage. **V2E2-0047 remains U.** No physical-origin assignment, qualified laser candidate or calibrated null follows.

The six nonself merged-epoch comparisons per frame retain the complete ranges below. Reused spectra and self-pairs are not independent detections.

| Region | Median r, barycentric | Median r, topocentric | Range r, barycentric | Range r, topocentric |
|---|---:|---:|---:|---:|
| core | 0.956320 | 0.588209 | 0.844156–0.978778 | 0.336330–0.692322 |
| broad_pattern | 0.999357 | 0.833054 | 0.992765–0.999513 | 0.806281–0.905966 |

16 of 16 profiles have full 601-point raw coverage; 16 have usable positive normalization, 0 are raw-only and 0 are blocked. Low-reference flags are 0 true, 16 false and 0 null; unavailable normalization does not count as a false flag. All 32 evaluable Pearson and 32 normalized RMS values are retained, including 4 labelled identical-product self-comparisons. Positive finite ERR support is absent in 16 profiles.

No partial or unscaled profile outcomes occur under the fixed support rules.

The method was public in `d194c32c3679cebb485f901ceccd1ac4786d66f6` and all 25 method/input files were read back before execution. The fixed anchor is **0047, observed on 2023-03-22, with BERV 3.26509772194068 km/s**. The original ±0.25 Å core, ±3 Å context and fixed reference flanks were retained without fitted shifts, widths, stellar velocity or continuum. A fixed topocentric core may sample neighboring structure after a coherent feature leaves its window; frame correlations are not a calibrated origin test.

The C008 wavelength window is disjoint from the completed C001–C007 bounded contexts. It nevertheless reuses all seven HD106515A observing products and already has original epoch and raw-detector evidence. This adds no observing time and is not blind, untouched or independent validation. Structured flank medians are reference levels, not a proven line-free continuum or calibrated physical flux. Positive scalar normalization leaves Pearson unchanged while changing plotted heights and normalized RMS; unavailable or nonpositive references remain explicit in the outputs.

The exact historical raw panel, native-input identities and each mapping stage are preserved in [the inventory](inputs/INPUT_INVENTORY.json) and [closure](GROUP_CLOSURE.json). Native order 43 was freshly selected by header coverage. Historical evidence describes a broad asymmetric shoulder or bump and extended trace residual, without a decisive compact charge deposit. All primary, secondary and adopted review text remains preserved.

These inherited observations are distinct from new mapping validation. Same-exposure native/merged agreement is not independent confirmation or an origin classification. Native units are unspecified, merged ADU are uncalibrated, and unavailable ERR support and descriptive noise proxies do not provide formal significance.

| Historical order | Global grid usable | Local usable | Baseline verified | Later five-window support |
|---|---|---|---|---|
| 43 | true | true | true | true |

The later reference-window support does not overwrite the earlier local/baseline diagnostics or turn them into an origin classification.

[Full report and figures](analysis/RESULTS_REPORT.md) · [Scientific interpretation](scientific_review/RESULT_INTERPRETATION.md) · [All comparisons](analysis/results/COMPARISONS.csv) · [Profile quality](analysis/results/PROFILE_METRICS.csv)

[Independent reconstruction](independent_audit/NUMERICAL_AUDIT.json) passes **424 checks and 63,374 scalar comparisons**. [Input audit](input_audit/INPUT_AUDIT.json) verifies 10 exact restored inputs and fresh order-header coverage. No new archive query or observing time was added. [Preservation](preservation/README.md) retains 25 NPZs totaling 282,389 bytes: 8 source windows, 16 profiles and 1 exact raw-panel copies. Preserve published results and reproduce in a separate directory.

The next original-queue item is [C009 / V2E2-0050 at 6802.02 Å](NEXT_ACTION.json), row 18 / R010. It has one discovery reference from 2023-03-22. Preserve the historical compact-cluster review and the adopted unresolved possible blend. Its wavelength is separate from completed bounded contexts, but its original epoch/raw results and the same observations already exist. [Detailed handoff](scientific_review/NEXT_STEP.md) preserves those dependencies. Group-number order does not determine the queue.

[Current checkpoint](CONTINUATION_STATE.json) · [Project continuation](../CONTINUE_SETI.md). Original coverage remains 300 exposures, 20 stars and 70.874650833 hours, with 403 A / 46 O / 185 U / 35 M. Rubin remains stopped at limited feasibility with the minimum 50 evaluable objects unmet.
