# C004 / HD106515A: joint context complete, all three records remain unresolved

The fixed context at **3872.245 Å** is complete across seven existing cohort epochs: **20 profiles and 96 comparisons**, retaining all three distinct discovery references. **V2E2-0028, 0045 and 0052 remain U.** No physical-origin assignment, qualified laser candidate or calibrated null follows.

Across all nonself comparisons, barycentric core correlations span 0.925276–0.990102; surrounding-pattern correlations span 0.967167–0.995102. Each reference remains separate below; reused spectra, reversed discovery pairs and self-pairs are not independent detections.

| Reference observation (UTC) | Region | Median r, barycentric | Median r, topocentric | Range r, barycentric | Range r, topocentric |
|---|---|---:|---:|---:|---:|
| 2022-03-07 | core | 0.978594 | -0.133278 | 0.962416–0.990102 | -0.261019–0.297301 |
| 2022-03-07 | broad_pattern | 0.989257 | 0.258103 | 0.974341–0.995102 | 0.102038–0.357637 |
| 2023-03-22 | core | 0.981993 | 0.094163 | 0.945522–0.990102 | -0.128058–0.748067 |
| 2023-03-22 | broad_pattern | 0.991086 | 0.099469 | 0.974156–0.995102 | 0.013010–0.244989 |
| 2023-05-24 | core | 0.979644 | 0.057321 | 0.925276–0.988447 | -0.086757–0.748067 |
| 2023-05-24 | broad_pattern | 0.990213 | 0.103207 | 0.967167–0.993093 | 0.013010–0.459677 |

20 of 20 profiles have full 601-point raw coverage; 20 have usable positive normalization, 0 are raw-only and 0 are blocked. There are 0 low-reference flags under the fixed rule. All 96 evaluable Pearson and 96 normalized RMS values are retained, including 12 labelled identical-product self-comparisons. Positive finite ERR support is absent in 20 profiles.

The method was public in `7c3e46e41fc98073c844259ab91350b8363bc63a` and all 25 method/input files were read back before execution. The first-discovery anchor uses **0028, observed on 2022-03-07, with BERV 10.77158288517 km/s**. It is not the January anchor used in earlier groups. The original ±0.25 Å core, ±3 Å context and fixed reference flanks were retained without fitted shifts, widths, stellar velocity or continuum. A fixed topocentric core may sample neighboring structure after the coherent feature leaves its window; frame correlations are not a calibrated origin test.

C004's entire original core was already visible in C003's positive normalization flank. The phases share observations and spectral pixels, and the wider C004 context contains previously seen neighboring structure. This is not blind or independent validation. Structured flank medians are reference levels, not a proven line-free continuum or calibrated physical flux; positive scalar normalization leaves Pearson unchanged while changing plotted heights and normalized RMS.

The exact historical raw panels and native-input identities are preserved. All three original order-3 global, local, baseline and later five-window mapping diagnostics are true. These inherited flags are distinct from a new mapping validation; same-exposure native/merged agreement is not independent confirmation or an origin classification. Native units are unspecified, merged ADU are uncalibrated, and unavailable ERR support and descriptive noise proxies do not provide formal significance.

[Full report and figures](analysis/RESULTS_REPORT.md) · [Scientific interpretation](scientific_review/RESULT_INTERPRETATION.md) · [All comparisons](analysis/results/COMPARISONS.csv) · [Profile quality](analysis/results/PROFILE_METRICS.csv) · [Closure](GROUP_CLOSURE.json)

[Independent reconstruction](independent_audit/NUMERICAL_AUDIT.json) passes **559 checks and 79,803 scalar comparisons**. [Input audit](input_audit/INPUT_AUDIT.json) verifies 16 exact restored inputs and fresh order-header coverage. No new archive query or observing time was added. [Preservation](preservation/README.md) retains 33 NPZs totaling 381,864 bytes: 10 source windows, 20 profiles and 3 exact raw-panel copies. Preserve published results and reproduce in a separate directory.

The next original-queue item is [C002 / V2E2-0033 at 3868.6025 Å](NEXT_ACTION.json), starting at row 10. It has one discovery reference from 2022-05-07. Its core was already visible in C003; its proposed wider context overlaps C004. [Detailed handoff](scientific_review/NEXT_STEP.md) preserves those dependencies. Group-number order does not determine the queue.

[Current checkpoint](CONTINUATION_STATE.json) · [Project continuation](../CONTINUE_SETI.md). Original coverage remains 300 exposures, 20 stars and 70.874650833 hours, with 403 A / 46 O / 185 U / 35 M. Rubin remains stopped at limited feasibility with the minimum 50 evaluable objects unmet.
