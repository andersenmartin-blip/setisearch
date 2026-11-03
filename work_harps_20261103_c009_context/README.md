# C009 / HD106515A: individual context complete, V2E2-0050 remains unresolved

**The central shape differs from the discovery while the surrounding pattern recurs.** The original C009 core differs from the March 2023 discovery in all six other epochs: barycentric raw Pearson is negative throughout, spanning -0.535854–-0.137821. The surrounding spectrum favors barycentric correlation and normalized RMS in all six comparisons, with r spanning 0.926466–0.959194. The core and surroundings therefore have different descriptive behavior. Higher fixed-topocentric core correlations and mixed core RMS outcomes may involve neighboring structure; they do not assign physical origin. V2E2-0050 remains U.

The fixed context at **6802.02 Å** is complete across seven existing cohort epochs: **16 profiles and 32 comparisons**, retaining the single March 2023 discovery reference and fresh native-order coverage. **V2E2-0050 remains U.** No physical-origin assignment, qualified laser candidate or calibrated null follows.

The six nonself merged-epoch comparisons per frame retain the complete ranges below. Reused spectra and self-pairs are not independent detections.

| Region | Median r, barycentric | Median r, topocentric | Range r, barycentric | Range r, topocentric |
|---|---:|---:|---:|---:|
| core | -0.359007 | 0.031288 | -0.535854–-0.137821 | -0.273291–0.368757 |
| broad_pattern | 0.941731 | -0.107914 | 0.926466–0.959194 | -0.184742–0.214778 |

16 of 16 profiles have full 601-point raw coverage; 16 have usable positive normalization, 0 are raw-only and 0 are blocked. Low-reference flags are 0 true, 16 false and 0 null; unavailable normalization does not count as a false flag. All 32 evaluable Pearson and 32 normalized RMS values are retained, including 4 labelled identical-product self-comparisons. Positive finite ERR support is absent in 16 profiles.

No partial or unscaled profile outcomes occur under the fixed support rules.

The method was public in `d1405bf95678d8225c18dc869d0de4b45c2fec76` and all 25 method/input files were read back before execution. The fixed anchor is **0050, observed on 2023-03-22, with BERV 3.26509772194068 km/s**. The original ±0.25 Å core, ±3 Å context and fixed reference flanks were retained without fitted shifts, widths, stellar velocity or continuum. A fixed topocentric core may sample neighboring structure after a coherent feature leaves its window; frame correlations are not a calibrated origin test.

The C009 wavelength window is disjoint from the completed C001–C008 bounded contexts. It nevertheless reuses all seven HD106515A observing products and already has original epoch and raw-detector evidence. This adds no observing time and is not blind, untouched or independent validation. Structured flank medians are reference levels, not a proven line-free continuum or calibrated physical flux. Positive scalar normalization leaves Pearson unchanged while changing plotted heights and normalized RMS; unavailable or nonpositive references remain explicit in the outputs.

The exact historical raw panel, native-input identities and each mapping stage are preserved in [the inventory](inputs/INPUT_INVENTORY.json) and [closure](GROUP_CLOSURE.json). Native order 70 was freshly selected by header coverage. Primary and secondary reviewers provisionally voted A for the compact slanted concentration, while root adopted U because a possible artifact/spectral blend remained unresolved. The broader residual structure and possible spectral contribution remain explicit. All original review text and the adopted U remain preserved.

These inherited observations are distinct from new mapping validation. Same-exposure native/merged agreement is not independent confirmation or an origin classification. Native units are unspecified, merged ADU are uncalibrated, and unavailable ERR support and descriptive noise proxies do not provide formal significance.

| Historical order | Global grid usable | Local usable | Baseline verified | Later five-window support |
|---|---|---|---|---|
| 70 | true | true | true | true |

The later reference-window support does not overwrite the earlier local/baseline diagnostics or turn them into an origin classification.

[Full report and figures](analysis/RESULTS_REPORT.md) · [Scientific interpretation](scientific_review/RESULT_INTERPRETATION.md) · [All comparisons](analysis/results/COMPARISONS.csv) · [Profile quality](analysis/results/PROFILE_METRICS.csv)

[Independent reconstruction](independent_audit/NUMERICAL_AUDIT.json) passes **428 checks and 63,354 scalar comparisons**. [Input audit](input_audit/INPUT_AUDIT.json) verifies 10 exact restored inputs and fresh order-header coverage. No new archive query or observing time was added. [Preservation](preservation/README.md) retains 25 NPZs totaling 276,753 bytes: 8 source windows, 16 profiles and 1 exact raw-panel copy. Preserve published results and reproduce in a separate directory.

The next original-queue item is [C010 / V2E2-0086 on HD112410 at 3823.065 Å](NEXT_ACTION.json), row 23 / R011. It has its own seven target epochs and one discovery reference observed on 2025-04-29. Preserve the historical order 1 local/baseline limitations and all U reviews. Original epoch/raw results already exist, even though this is a different target/cohort. [Detailed handoff](scientific_review/NEXT_STEP.md) preserves those dependencies. Group-number order does not determine the queue.

[Current checkpoint](CONTINUATION_STATE.json) · [Project continuation](../CONTINUE_SETI.md). Original coverage remains 300 exposures, 20 stars and 70.874650833 hours, with 403 A / 46 O / 185 U / 35 M. Rubin remains stopped at limited feasibility with the minimum 50 evaluable objects unmet.
