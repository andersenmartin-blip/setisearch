# C010 / HD112410: individual context complete, V2E2-0086 remains unresolved

All six other HD112410 epochs align better with the fixed discovery profile in barycentric coordinates than in the fixed topocentric frame, in both the original core and surrounding window. V2E2-0086 remains U. The central broad structure and its surrounding pattern are present with substantial shape, amplitude and reference-level differences. The comparison describes these saved spectra; it does not identify a line or physical origin, qualify a laser candidate, establish significance or calibrate a null result.

The fixed context at **3823.065 Å** (exact scientific input `3823.0649999999996`) is complete across seven existing **HD112410** cohort epochs: **16 profiles and 32 comparisons**. The only discovery reference was observed on 2025-04-29, BERV **3.40485846065643 km/s**. The target-specific BERV span is **21.30284860830273 km/s**. No HD106515A observing product or numeric anchor is transferred. **V2E2-0086 remains U.** No qualified laser candidate or calibrated null follows.

| Region | Median r, barycentric | Median r, topocentric | Range r, barycentric | Range r, topocentric |
|---|---:|---:|---:|---:|
| core | 0.750154 | 0.027023 | 0.596420 to 0.869229 | -0.130725 to 0.323374 |
| broad_pattern | 0.899448 | 0.455775 | 0.836596 to 0.962802 | 0.446920 to 0.583838 |

The weakest barycentric core correlation is retained on **2025-06-27** (r=0.596420); the largest barycentric core normalized RMS is retained on **2025-05-28** (1.600996). Profile morphology and scaled amplitude vary across the epochs. The complete ranges and all rows remain in the report; these are descriptive differences, not calibrated physical amplitudes or significance.

16 of 16 profiles have full 601-point raw coverage; 16 have usable positive normalization, 0 are raw-only and 0 are blocked. Low-reference flags are 0 true, 16 false and 0 null. All 32 evaluable Pearson and 32 normalized RMS values are retained, including 4 labelled identical-product self-comparisons. Positive finite ERR support is absent in 16 profiles. 16 of 16 profile rows retain nonpositive signed original samples; valid positive pooled references do not imply positive individual samples. merged: 2–21 nonpositive samples among 600 finite original source samples per window; native: 3 nonpositive samples among 562 finite original source samples per window. Frame rows reuse their source observations. All signs remain unchanged; no clipping was introduced.

All partial, missing-reference, low-reference and signed-flux outcomes are retained in [the complete profile quality](analysis/results/PROFILE_METRICS.csv) and [closure](GROUP_CLOSURE.json). They are not repaired by shrinking windows, borrowing another order or substituting a one-sided reference.

The method was public in `acb3a382b43ca0b9d3d13f3e30317383f591fb10` and all **25 method/input files** were read back before execution. The exact original ±0.25 Å core, ±3 Å context and fixed 1.5–3 Å reference flanks were retained without fitted shifts, widths, stellar velocity or continuum. The wavelength-specific topocentric anchor is **3823.0215804708346 Å**. A fixed topocentric core can sample neighboring structure after the expected catalog feature leaves the window; frame statistics are descriptive, not calibrated origin tests.

C010 changes target from HD106515A to HD112410 and uses the seven original HD112410 April–August 2025 observations. Its exact window is separate from completed bounded contexts, while its original epoch/profile and raw evidence already existed. These are reused observations, not blind or independent new data or observing time.

Primary, secondary and root-adopted reviews all retain U for broad native structure and diffuse trace-confined enhancement. Original order 1 local/baseline mapping failures remain explicit alongside supported global and later five-window diagnostics. Full historical raw panels and review text remain unchanged; no new origin assignment follows.

| Historical order | Global grid usable | Local usable | Baseline verified | Later five-window support |
|---|---|---|---|---|
| 1 | true | false | false | true |

Native units are unspecified, merged ADU are uncalibrated, and shared extraction lineage is not independent observing confirmation. The fixed flank medians are descriptive reference levels rather than established line-free continua. Missing positive ERR support and first-difference proxies do not provide formal significance, sensitivity or false-alarm probabilities.

[Full report and figures](analysis/RESULTS_REPORT.md) · [Scientific interpretation](scientific_review/RESULT_INTERPRETATION.md) · [All comparisons](analysis/results/COMPARISONS.csv)

[Independent reconstruction](independent_audit/NUMERICAL_AUDIT.json) passes **432 checks and 63,469 scalar comparisons**. [Input audit](input_audit/INPUT_AUDIT.json) verifies exact saved inputs and fresh header coverage. [Preservation](preservation/README.md) retains **25 NPZ files totaling 292,148 bytes**: 8 source windows, 16 profiles and 1 exact historical raw-panel copy. Preserve completed outputs and reproduce in a separate directory.

The next original-queue item is [C012 / V2E2-0087 on HD112410 at 3869.2675 Å](NEXT_ACTION.json), row 24 / R013. Its target-specific epochs, discovery metadata and each historical mapping limitation are preserved in [the detailed handoff](scientific_review/NEXT_STEP.md). Group-number order does not determine the queue. Same April 2025 discovery and same seven HD112410 epochs as C010; no added observation. Recompute the anchor at the C012 wavelength rather than copying C010 or HD106515A. Original C012 epoch/raw evidence already existed.

[Current checkpoint](CONTINUATION_STATE.json) · [Project continuation](../CONTINUE_SETI.md). Original coverage remains 300 exposures, 20 stars and 70.874650833 hours, with 403 A / 46 O / 185 U / 35 M. Rubin remains stopped at limited feasibility with minimum 50 unmet.
