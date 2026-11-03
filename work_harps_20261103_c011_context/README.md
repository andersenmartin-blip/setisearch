# C011 / HD112410: individual context complete, V2E2-0089 remains unresolved

All six other epochs agree better with the fixed May discovery profile in barycentric coordinates than in the fixed topocentric frame, in both the original core and surrounding window. V2E2-0089 remains U. Both native orders have complete coverage and valid positive normalization. Order 2's two low-reference flags are true and its noisy signed variation remains explicit. These descriptive results do not identify a spectral line or physical origin, qualify a laser candidate, estimate significance or calibrate a null result.

The fixed context at **3865.6775 Å** (exact scientific input `3865.6775000000002`) is complete across seven existing **HD112410** cohort epochs: **18 profiles and 36 comparisons**. The only discovery reference was observed on 2025-05-28, BERV **-5.48386283255014 km/s**. The target-specific BERV span is **21.30284860830273 km/s**. The HD112410 cohort is reused from C010/C012; the C011 anchor is recomputed at this wavelength and its own May discovery reference. **V2E2-0089 remains U.** No qualified laser candidate or calibrated null follows.

| Region | Median r, barycentric | Median r, topocentric | Range r, barycentric | Range r, topocentric |
|---|---:|---:|---:|---:|
| core | 0.963708 | -0.313622 | 0.949081 to 0.973576 | -0.711186 to 0.953127 |
| broad_pattern | 0.964388 | 0.164278 | 0.961697 to 0.969492 | -0.017720 to 0.954910 |

The weakest barycentric core correlation is retained on **2025-06-27** (r=0.949081); the largest barycentric core normalized RMS is retained on **2025-06-27** (0.162986). Profile morphology and scaled amplitude vary across the epochs. The complete ranges and all rows remain in the report; these are descriptive differences, not calibrated physical amplitudes or significance.

18 of 18 profiles have full 601-point raw coverage; 18 have usable positive normalization, 0 are raw-only and 0 are blocked. Low-reference flags are 2 true, 16 false and 0 null. Flagged rows: native order 2 barycentric, native order 2 topocentric. Their usable positive normalizations are retained with the flags. All 36 evaluable Pearson and 36 normalized RMS values are retained, including 4 labelled identical-product self-comparisons; 0 Pearson slots and 0 RMS slots remain explicitly unevaluable under the fixed rules. Positive finite ERR support is absent in 18 profiles. 6 of 18 profile rows retain nonpositive signed original samples; valid positive pooled references do not imply positive individual samples. merged: 0–3 nonpositive samples among 599–600 finite original source samples per window; native: 3–29 nonpositive samples among 534–655 finite original source samples per window. Frame rows reuse their source observations. All signs remain unchanged; no clipping was introduced.

| Retained low-reference source | Order | Frame | Positive pooled reference | First-difference proxy |
|---|---:|---|---:|---:|
| ADP.2025-05-29T01:01:14.389 | 2 | barycentric | 43.386597 | 17.929966 |
| ADP.2025-05-29T01:01:14.389 | 2 | topocentric | 43.386597 | 17.929966 |

These low-reference flags are retained without excluding their usable positive normalizations. Their scaled amplitudes remain descriptive; the noise proxy does not supply formal uncertainty or significance.

All partial, missing-reference, low-reference and signed-flux outcomes are retained in [the complete profile quality](analysis/results/PROFILE_METRICS.csv) and [closure](GROUP_CLOSURE.json). They are not repaired by shrinking windows, borrowing another order or substituting a one-sided reference.

The method was public in `dad9f542b6f7bb830f1020d373634012483e7b15` and all **25 method/input files** were read back before execution. The exact original ±0.25 Å core, ±3 Å context and fixed 1.5–3 Å reference flanks were retained without fitted shifts, widths, stellar velocity or continuum. The wavelength-specific topocentric anchor is **3865.748213029564 Å**. All seven metadata-predicted centers remain inside the fixed May-reference ±0.25 Å topocentric core: the April and August offsets are −0.114616520 Å and +0.160086601 Å. These are predicted centers, not fitted peaks or full finite-feature coverage; fixed windows can still include neighboring structure. Frame statistics remain descriptive, not calibrated origin tests.

C011 reuses the same seven original HD112410 April–August 2025 observations as C010/C012, with its own May 28 discovery reference and wavelength-specific anchor. Its broader window overlaps C012 on the same observing products by 2.4100000000003092 Å, while the original C011 core lies outside the C012 window. Shared surrounding/reference pixels remain dependent evidence. Original C011 epoch/profile and raw evidence already existed; these are reused observations, not blind or independent new data or added observing time.

Primary, secondary and root-adopted reviews all retain U for broad native structure and diffuse trace-associated enhancement in orders 2 and 3. Both orders retain true at every original global/local/baseline and later five-window mapping stage. Those supported diagnostics do not establish a clear charge morphology, qualified narrow source or physical origin. Full historical raw panels and review text remain unchanged; no new origin assignment follows.

| Historical order | Global grid usable | Local usable | Baseline verified | Later five-window support |
|---|---|---|---|---|
| 2 | true | true | true | true |
| 3 | true | true | true | true |

Native units are unspecified, merged ADU are uncalibrated, and shared extraction lineage is not independent observing confirmation. The fixed flank medians are descriptive reference levels rather than established line-free continua. Missing positive ERR support and first-difference proxies do not provide formal significance, sensitivity or false-alarm probabilities.

[Full report and figures](analysis/RESULTS_REPORT.md) · [Scientific interpretation](scientific_review/RESULT_INTERPRETATION.md) · [All comparisons](analysis/results/COMPARISONS.csv)

[Independent reconstruction](independent_audit/NUMERICAL_AUDIT.json) passes **481 checks and 71,203 scalar comparisons**. [Input audit](input_audit/INPUT_AUDIT.json) verifies exact saved inputs and fresh header coverage. [Preservation](preservation/README.md) retains **29 NPZ files totaling 336,009 bytes**: 9 source windows, 18 profiles and 2 exact historical raw-panel copies. Preserve completed outputs and reproduce in a separate directory.

The next original-queue item is [C016 / V2E2-0094, V2E2-0096, V2E2-0098, V2E2-0110 on HD114386 with member centers 4303.785–4303.79 Å](NEXT_ACTION.json), row 27 / R017. The exact scientific member centers are `[4303.785, 4303.785, 4303.785, 4303.79]` Å. Its target-specific epochs, discovery metadata and each historical mapping limitation are preserved in [the detailed handoff](scientific_review/NEXT_STEP.md). Group-number order does not determine the queue. Selection: Original ACTION_QUEUE first unfinished diagnostic route after completed C001–C010/C012 and currently planned C011, excluding exactly the already-completed NORMALIZATION_CONTEXT routes for 0092/C013 row 26 and 0104/C014 row 31. Thus row 27 C016 is first, and all its original members at rows 27/29/30/32 stay together. Unresolved U is not evidence that a completed diagnostic should be rerun. Selection fixed before C011 values. New target HD114386 with its own seven existing January 2022–August 2023 epochs and four distinct discovery products. Retain every fixed reference, not a favorable subset. Do not transfer HD112410 products, May 2025 reference, numeric anchor or BERV span. Original C016 epoch/profile/raw evidence already existed; no added observation. Target changes to HD114386; proposed group window is disjoint from completed C001–C012 bounded group windows. The same HD114386 observations were used in original epoch/raw evidence and completed blue normalization contexts; no blind, untouched, independent-data or new observing-time claim. Fresh header inventory at this wavelength and preserved original order-19 mapping are required. Proposed common group center: `4303.7875` Å. Midpoint of minimum/maximum original catalog centers, following the existing joint-group convention; exact individual centers and all four discovery markers remain explicit. Not a fitted peak.

[Current checkpoint](CONTINUATION_STATE.json) · [Project continuation](../CONTINUE_SETI.md). Original coverage remains 300 exposures, 20 stars and 70.874650833 hours, with 403 A / 46 O / 185 U / 35 M. Rubin remains stopped at limited feasibility with minimum 50 unmet.
