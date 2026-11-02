# C007 / HD106515A: individual context complete, V2E2-0026 remains unresolved

The fixed C007 context at **4312.700 Å** is complete across seven existing cohort epochs: **16 profiles and 32 comparison slots** with one discovery reference. **V2E2-0026 remains U.** No physical-origin assignment, qualified laser candidate or calibrated null follows.

The nonself barycentric core correlations span 0.959862–0.969939; the surrounding-pattern correlations span 0.983174–0.987315. The single discovery reference is retained for every epoch; no favorable reference or shifted window was selected.

| Region | Median r, barycentric | Median r, topocentric | Range r, barycentric | Range r, topocentric |
|---|---:|---:|---:|---:|
| core | 0.965836 | -0.064383 | 0.959862–0.969939 | -0.459282–0.977230 |
| broad_pattern | 0.985081 | 0.124842 | 0.983174–0.987315 | -0.120875–0.990867 |

The 2022-12-31 observation is the retained near-BERV exception: core r is 0.977230 topocentric versus 0.959862 barycentric, and surrounding r is 0.990867 versus 0.983498. Its BERV differs from discovery by only about 0.237 km/s although the observations are nearly a year apart. There is no universal pairwise frame ranking. A barycentrically coherent center lies outside the fixed topocentric core in five epochs; those comparisons can describe neighboring structure.

16 of 16 profiles have full 601-point raw coverage; 16 have usable positive normalization, 0 are raw-only and 0 are blocked. There are 0 low-reference flags under the fixed rule. All 32 evaluable Pearson and 32 normalized RMS values remain. These totals include four labelled identical-product self-comparisons. Positive finite ERR support is absent in 16 profiles.

The exact method was public in `57b5af70c88a3a4ee5fe8f9224ac805a7c3c438a` and all 25 method/input files were read back before this execution. The ±0.25 Å core, ±3 Å context and fixed first-discovery topocentric anchor were retained, without fitting a shift, linewidth, stellar velocity or continuum. At different BERV values the fixed topocentric core can sample neighboring structure rather than the recentered feature.

The original C007 core was already visible in C006's positive reference flank. This separate context therefore overlaps already seen flux and reuses the same observations; it is neither blind nor independent confirmation. The dependence is reciprocal: the complete C006 original core union lies inside C007's negative reference flank. Both flank medians therefore contain known spectral structure; positive reference scaling is not a proven line-free continuum or calibrated physical flux.

The native order 19 context and one historical raw panel remain exact. **0026's original local and baseline mapping flags remain false**, alongside true global and later five-window diagnostics. Same-exposure native/merged agreement does not validate the local raw mapping. Native units are unspecified; merged ADU are uncalibrated. The descriptive noise proxy and unavailable ERR support do not provide formal significance.

[Full report and figures](analysis/RESULTS_REPORT.md) · [Scientific interpretation](scientific_review/RESULT_INTERPRETATION.md) · [All comparisons](analysis/results/COMPARISONS.csv) · [Profile quality](analysis/results/PROFILE_METRICS.csv) · [Closure](GROUP_CLOSURE.json)

[Independent reconstruction](independent_audit/NUMERICAL_AUDIT.json) passes **410 checks and 64,179 scalar comparisons**. [Input audit](input_audit/INPUT_AUDIT.json) verifies the ten exact restored inputs and fresh order-header coverage. No new archive query or observing time was added. [Preservation](preservation/README.md) retains 25 NPZs totaling 285,753 bytes: eight source windows, sixteen profiles and one raw-panel copy. Preserve published results and reproduce in a separate directory.

The next original-queue group is [C004 at 3872.245 Å](NEXT_ACTION.json), starting at row 8 and containing 0028/0045/0052 from three distinct discovery products. Its original core is already visible within C003's positive reference flank. [Detailed handoff](scientific_review/NEXT_STEP.md) preserves that dependency; group-number order does not determine the queue.

[Current checkpoint](CONTINUATION_STATE.json) · [Project continuation](../CONTINUE_SETI.md). Original coverage remains 300 exposures, 20 stars and 70.874650833 hours, with 403 A / 46 O / 185 U / 35 M. Rubin remains stopped at limited feasibility with the minimum 50 evaluable objects unmet.
