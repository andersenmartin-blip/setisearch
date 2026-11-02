# C003 / HD106515 A: joint context complete, all five records unresolved

Five overlapping records near 3869.75 Å were compared across all seven existing original-cohort epochs, all five discovery references and eight historically covering native-order contexts. Both core and surrounding spectral structure agree closely in barycentric coordinates. **All five records remain U; no line identity, physical origin or qualified laser candidate is established.**

The method and exact input identities were public in `d1046d8306ba34699f0eab9af57be145316eef76`, with all 31 files read back before the new computation. The fixed center is 3869.75125 Å, with the first discovery's single topocentric anchor3869.3622643053627 Å, a±3 Å context and the union core±0.25625 Å. The BERV span is 59.609813 km/s. No shift, width, stellar velocity or fitted continuum was optimized.

## Complete result

All 30 profiles and172 comparison slots are retained:24 usable normalizations and6 raw-only order2 profiles. Exactly166 raw Pearson and160normalized RMS values are evaluable; the other slots retain their reasons. Twenty self-comparison records and shared references are explicitly flagged, not counted as independent detections.

Median raw Pearson over the six other epochs, keeping each fixed discovery reference separate:

| Discovery observation (UTC) | Region | Barycentric | Topocentric |
|---|---|---:|---:|
| 2022-01-05 | core | 0.950983 | -0.044838 |
| 2022-01-05 | broad_pattern | 0.956488 | 0.132083 |
| 2022-03-07 | core | 0.984224 | 0.143348 |
| 2022-03-07 | broad_pattern | 0.981953 | 0.088721 |
| 2023-03-22 | core | 0.982358 | -0.188589 |
| 2023-03-22 | broad_pattern | 0.983450 | 0.200192 |
| 2023-05-24 | core | 0.981103 | -0.326308 |
| 2023-05-24 | broad_pattern | 0.979672 | 0.174217 |
| 2023-07-03 | core | 0.978759 | 0.076522 |
| 2023-07-03 | broad_pattern | 0.977921 | 0.233720 |

Every nonself barycentric core correlation is 0.940696–0.988011; broader-pattern correlations are0.928074–0.989934. The pattern persists in both regions. This is descriptive spectral agreement, not a calibrated origin classifier. There are near-BERV pairs with strong topocentric agreement too. With the fixed first-discovery anchor, the expected barycentric-coherent feature lies outside the topocentric core in four of seven epochs, including three discovery references. Those topocentric-core comparisons concern the fixed coordinate window, not a recentered feature.

Native order3 has full support for all five discovery contexts and closely matches each same-exposure merged extraction: core r=0.999388–0.999843, broad r=0.987953–0.993135. These are shared observations and reductions, not independent confirmations. Order2's three included contexts retain core r=0.867361–0.954447, but their positive normalization flank is outside coverage, so all six frame profiles remain raw-only and their broader correlations are ineligible. For the final two discoveries, order2 does not cover the original feature center at all; those two structural exclusions were recorded before array analysis. No missing panels or reference windows are substituted.

[Full report and all six figures](analysis/RESULTS_REPORT.md) · [Scientific interpretation](scientific_review/RESULT_INTERPRETATION.md) · [All 172 comparisons](analysis/results/COMPARISONS.csv) · [All 30 profile records](analysis/results/PROFILE_METRICS.csv) · [Machine-readable closure](GROUP_CLOSURE.json)

## Verification and preservation

[Independent numerical reconstruction](independent_audit/NUMERICAL_AUDIT.json) passes 807 checks and117,053 scalar comparisons, including all 15 pre-interpolation source windows,30 profiles,172 comparisons and8 unchanged raw panels. Original flux/error/index values match exactly; maximum comparison discrepancy is 6.60e-14. Independent arithmetic and AI review are not human peer review or additional observing time.

[Input audit](input_audit/INPUT_AUDIT.json) passes 248 checks for25 restored files from3 existing archives. [Preservation instructions](preservation/README.md) bind all 63 numerical-ledger files and53 NPZs totaling 568,599 bytes. Seven merged inputs, five ancillary/native pairs and eight original panels can be restored without a live archive query. Reproduction belongs in a separate copy; published outputs are preserved.

All 30 profiles have zero positive finite ERR support. Native flux units are unspecified; merged flux is uncalibrated ADU. Flanks contain spectral structure and are not asserted to be quiet continuum. All 14 merged and10order3 profiles have positive reference levels and no descriptive low-reference flag, which is not a formal uncertainty or sensitivity calibration. No origin, intrinsic linewidth, false-alarm rate or qualified null follows.

## Next fixed group

[C005/R005 is next](NEXT_ACTION.json), selected prospectively by the first remaining original queue row4: V2E2-0023/0029/0035/0046/0054 on HD106515 A near 3882.04 Å. It shares seven exposure products but a separate wavelength region outside this comparison. Its five discovery products differ from C003; the May2022 discovery native context must be inventoried. [Detailed handoff](scientific_review/NEXT_STEP.md). No C005 arrays or new acquisition were executed here.

[Current SETI state](CONTINUATION_STATE.json) · [Project continuation](../CONTINUE_SETI.md). The original survey remains300 exposures,20 stars and70.874650833 hours, with 403 A/46 O/185 U/35 M. Rubin remains a completed limited-feasibility study with minimum 50 evaluable objects unmet.
