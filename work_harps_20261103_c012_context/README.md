# C012 / HD112410: individual context complete, V2E2-0087 remains unresolved

All six other HD112410 epochs agree better with the fixed discovery profile in barycentric coordinates than in the fixed topocentric frame, in both the original core and surrounding window. V2E2-0087 remains U. The central broad structure and surrounding peaks recur with retained shape, amplitude and reference-level differences. This is a descriptive comparison of saved spectra, without a line identification, physical-origin assignment, qualified laser candidate, significance estimate or calibrated null.

The fixed context at **3869.2675 Å** (exact scientific input `3869.2675`) is complete across seven existing **HD112410** cohort epochs: **18 profiles and 36 comparisons**. The only discovery reference was observed on 2025-04-29, BERV **3.40485846065643 km/s**. The target-specific BERV span is **21.30284860830273 km/s**. The HD112410 cohort is reused from C010; the C012 anchor is recomputed at this wavelength. **V2E2-0087 remains U.** No qualified laser candidate or calibrated null follows.

| Region | Median r, barycentric | Median r, topocentric | Range r, barycentric | Range r, topocentric |
|---|---:|---:|---:|---:|
| core | 0.947228 | -0.358147 | 0.912614 to 0.963934 | -0.417189 to -0.156073 |
| broad_pattern | 0.970949 | -0.035499 | 0.952137 to 0.981032 | -0.105845 to 0.098558 |

The weakest barycentric core correlation is retained on **2025-05-28** (r=0.912614); the largest barycentric core normalized RMS is retained on **2025-05-28** (0.135848). Profile morphology and scaled amplitude vary across the epochs. The complete ranges and all rows remain in the report; these are descriptive differences, not calibrated physical amplitudes or significance.

16 of 18 profiles have full 601-point raw coverage; 16 have usable positive normalization, 2 are raw-only and 0 are blocked. Low-reference flags are 0 true, 16 false and 2 null. All 34 evaluable Pearson and 32 normalized RMS values are retained, including 4 labelled identical-product self-comparisons; 2 Pearson slots and 4 RMS slots remain explicitly unevaluable under the fixed rules. Positive finite ERR support is absent in 18 profiles. 4 of 18 profile rows retain nonpositive signed original samples; valid positive pooled references do not imply positive individual samples. merged: 0–3 nonpositive samples among 599–600 finite original source samples per window; native: 0–2 nonpositive samples among 423–546 finite original source samples per window. Frame rows reuse their source observations. All signs remain unchanged; no clipping was introduced.

| Partial source | Order | Frame | Raw finite / 601 | Normalized finite / 601 | Normalization | Retained reasons |
|---|---:|---|---:|---:|---|---|
| ADP.2025-04-30T01:01:50.866 | 2 | barycentric | 378 | 0 | RAW_ONLY | MISSING_RIGHT_FLANK_COVERAGE |
| ADP.2025-04-30T01:01:50.866 | 2 | topocentric | 378 | 0 | RAW_ONLY | MISSING_RIGHT_FLANK_COVERAGE |

All partial, missing-reference, low-reference and signed-flux outcomes are retained in [the complete profile quality](analysis/results/PROFILE_METRICS.csv) and [closure](GROUP_CLOSURE.json). They are not repaired by shrinking windows, borrowing another order or substituting a one-sided reference.

The method was public in `3815808d874c9cf927da83dc287631e18de3bdd4` and all **25 method/input files** were read back before execution. The exact original ±0.25 Å core, ±3 Å context and fixed 1.5–3 Å reference flanks were retained without fitted shifts, widths, stellar velocity or continuum. The wavelength-specific topocentric anchor is **3869.2235557371996 Å**. A fixed topocentric core can sample neighboring structure after the expected catalog feature leaves the window; frame statistics are descriptive, not calibrated origin tests.

C012 reuses the same seven original HD112410 April–August 2025 observations and April discovery reference as C010, with its own wavelength-specific anchor. Its exact window is separate from C010. Numeric wavelength overlap with earlier HD106515A contexts shares none of their pixels or observing products. Original C012 epoch/profile and raw evidence already existed; these are reused observations, not blind or independent new data or added observing time.

Primary, secondary and root-adopted reviews all retain U for broad enhancement in overlapping orders 2 and 3, noisier in order 2 and smoother in order 3, with trace-associated raw structure. Original order 2 local/baseline mapping failures remain explicit alongside supported global and later five-window diagnostics; order 3 is true at all four stages. Full historical raw panels and review text remain unchanged; no new origin assignment follows.

| Historical order | Global grid usable | Local usable | Baseline verified | Later five-window support |
|---|---|---|---|---|
| 2 | true | false | false | true |
| 3 | true | true | true | true |

Native units are unspecified, merged ADU are uncalibrated, and shared extraction lineage is not independent observing confirmation. The fixed flank medians are descriptive reference levels rather than established line-free continua. Missing positive ERR support and first-difference proxies do not provide formal significance, sensitivity or false-alarm probabilities.

[Full report and figures](analysis/RESULTS_REPORT.md) · [Scientific interpretation](scientific_review/RESULT_INTERPRETATION.md) · [All comparisons](analysis/results/COMPARISONS.csv)

[Independent reconstruction](independent_audit/NUMERICAL_AUDIT.json) passes **481 checks and 70,371 scalar comparisons**. [Input audit](input_audit/INPUT_AUDIT.json) verifies exact saved inputs and fresh header coverage. [Preservation](preservation/README.md) retains **29 NPZ files totaling 317,583 bytes**: 9 source windows, 18 profiles and 2 exact historical raw-panel copies. Preserve completed outputs and reproduce in a separate directory.

The next original-queue item is [C011 / V2E2-0089 on HD112410 at 3865.6775 Å](NEXT_ACTION.json), row 25 / R012. The exact scientific center is `3865.6775000000002` Å. Its target-specific epochs, discovery metadata and each historical mapping limitation are preserved in [the detailed handoff](scientific_review/NEXT_STEP.md). Group-number order does not determine the queue. Same seven HD112410 epochs as C010/C012, but own May 28 2025 discovery replaces the April 29 discovery reference. Recompute the new wavelength-specific anchor. Original C011 epoch/profile/raw evidence already existed; no added observation. Broader C011/C012 windows overlap on the same seven observing products, although the original C011 core lies below the C012 window. Same observations and possible reused surrounding/reference pixels make this dependent post-detection context, not blind or independent evidence. Reinventory header coverage and raw mapping at C011 before values.

[Current checkpoint](CONTINUATION_STATE.json) · [Project continuation](../CONTINUE_SETI.md). Original coverage remains 300 exposures, 20 stars and 70.874650833 hours, with 403 A / 46 O / 185 U / 35 M. Rubin remains stopped at limited feasibility with minimum 50 unmet.
