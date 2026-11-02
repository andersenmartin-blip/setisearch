# C005 / HD106515A: joint context complete, all five records unresolved

Five records around 3882.04 Å were compared across all seven existing cohort epochs, all five discovery references and ten covering native-order contexts. Core and surrounding structure show high barycentric agreement against every reference. **All five records remain U; no line identity, physical origin or qualified laser candidate is established.**

The fixed method and exact input identities were public in `b9e06d67e3a499dd93bf1b718820a18b0ddbe395`; all 33 files were read back before the new calculation. The center is 3882.0375 Å, the single first-discovery topocentric anchor is 3881.6472792969134 Å, the wider window is ±3 Å, and the union core is ±0.2525 Å. BERV spans 59.609813 km/s. No shift, width, stellar velocity or continuum model was optimized.

## Complete result

All **34 profiles and 180 comparison slots** are measured, with full 601-point coverage and valid positive-flank normalization. All 180 Pearson and 180 normalized RMS values are retained. Twenty self-comparison records and shared/reversed references are explicit; these are not independent detections.

Median raw Pearson over the six other epochs, with each discovery reference separate:

| Discovery observation (UTC) | Region | Barycentric | Topocentric |
|---|---|---:|---:|
| 2022-01-05 | core | 0.948681 | -0.062313 |
| 2022-01-05 | broad_pattern | 0.971425 | 0.167409 |
| 2022-03-07 | core | 0.987626 | -0.248398 |
| 2022-03-07 | broad_pattern | 0.983516 | 0.298419 |
| 2022-05-07 | core | 0.985985 | 0.154541 |
| 2022-05-07 | broad_pattern | 0.987088 | 0.360436 |
| 2023-03-22 | core | 0.989248 | -0.098214 |
| 2023-03-22 | broad_pattern | 0.985375 | 0.392800 |
| 2023-07-03 | core | 0.984982 | -0.214093 |
| 2023-07-03 | broad_pattern | 0.980731 | 0.123611 |

Nonself barycentric core r spans 0.912055–0.994226; surrounding-pattern r spans 0.947577–0.994515. The central structure recurs with its wider pattern. Some near-BERV pairs also agree strongly topocentrically; there is no universal pairwise frame ranking. Four of seven expected coherent feature centers fall outside the fixed topocentric core. Those comparisons sample the fixed anchor window rather than a recentered feature, and do not calibrate an origin test.

Native order 3 matches its same-exposure merged extraction with core r = 0.993281–0.997261 and wider r = 0.945941–0.968422. Order 4 has core r = 0.965275–0.991654 and wider r = 0.866191–0.905812. Shared extraction inputs prevent interpreting these as independent confirmations or physical flux ratios.

Two order 4 **topocentric** profiles have the fixed low-reference flag: V2E2-0035 (7 May 2022) has reference 40.55 versus noise proxy 16.20; V2E2-0054 (3 July 2023) has 32.03 versus 16.20. Their available-window nonpositive fractions are 2.99% and 4.98%. Both remain valid positive normalizations under the frozen rule; this is a quality limitation, not missing coverage or a reason to discard the result. Structured, frame-dependent flank references can change plotted heights and normalized RMS; positive scaling alone leaves Pearson unchanged. Native flux units are unspecified.

[Full report and all eight figures](analysis/RESULTS_REPORT.md) · [Scientific interpretation](scientific_review/RESULT_INTERPRETATION.md) · [All comparisons](analysis/results/COMPARISONS.csv) · [All profile/quality records](analysis/results/PROFILE_METRICS.csv) · [Machine-readable closure](GROUP_CLOSURE.json)

## Verification and preservation

[Independent reconstruction](independent_audit/NUMERICAL_AUDIT.json) passes **895 checks and 135,577 scalar comparisons**, covering all 17 pre-interpolation source windows, 34 profiles, 180 comparisons and ten unchanged raw panels. Original source flux, ERR and indices agree exactly. Maximum comparison discrepancy is 1.86e-13. This is independent arithmetic and machine review, not human peer review or new observing time.

[Input audit](input_audit/INPUT_AUDIT.json) passes 267 checks for 27 exact files restored from three existing archives. [Preservation instructions](preservation/README.md) bind all 71 numerical-ledger files and 61 NPZs totaling 707,244 bytes. Full input restoration needs no live archive query; reproduce in a separate copy and preserve published outputs.

All 34 profiles have zero positive finite ERR support. Merged flux is uncalibrated ADU; native flux units are unspecified. The descriptive noise proxy and positive references are not a formal error model. Original raw panels and distinct primary/secondary/adopted reviews remain exact, including separate off-trace pixels and noisy contexts. No new mapping, subtraction or charge/photon classification was performed. No intrinsic linewidth, false-alarm rate, sensitivity or qualified null follows.

## Next fixed group

[C006 is next](NEXT_ACTION.json), selected before these results by original queue row 5. It contains V2E2-0025/0042/0043 near 4310 Å across R006/R007, but only **two distinct discovery exposures**: 0042 and 0043 share a product. Retain all three wavelength records while deduplicating product references. [Detailed handoff](scientific_review/NEXT_STEP.md). Its seven cohort epochs overlap this phase in observing time; its wavelength region is distinct. No C006 arrays or new acquisition were executed here.

[Current SETI checkpoint](CONTINUATION_STATE.json) · [Project continuation](../CONTINUE_SETI.md). Original coverage remains 300 exposures, 20 stars and 70.874650833 hours; classifications remain 403 A / 46 O / 185 U / 35 M. Rubin remains a completed limited-feasibility study with minimum 50 evaluable objects unmet.
