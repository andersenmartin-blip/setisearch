# C001 / HD103991: joint context complete, both records unresolved

The two records around 3852 Å were analyzed together across all six original-cohort HD103991 epochs and both native covering orders in their discovery exposures. The broader surrounding pattern is generally more consistent in barycentric coordinates. The core behaves differently and depends on which discovery is used as the reference. **Both V2E2-0001 and V2E2-0016 remain U; no origin or laser qualification follows.**

The fixed method was published in `c7e53d0180887618817923cfb1bec4b5b300ad53`, with exact readback of all 26 files before this new context calculation. It uses a joint 3852.3925 Å barycentric center, a single first-discovery topocentric anchor, ±3 Å context, and the fixed union core ±0.265 Å. No wavelength shift, linewidth, stellar velocity or fitted continuum was optimized. The original epoch pipeline was not rerun.

## Result

All 20 profile slots and 64 comparison slots are retained. Sixteen profiles have usable fixed-flank normalization. The four order-3 profiles remain raw-only because their entire negative reference flank is outside detector coverage. Four broader native-to-merged Pearson comparisons are therefore ineligible; all eight order-3 normalized-RMS comparisons are ineligible. This is explicit missing support, not a substituted window. The remaining 60 Pearson and 56 normalized-RMS values include eight self-comparison records and shared data; they are not independent detections.

Median raw Pearson over the five other epochs, reported separately for each fixed discovery reference:

| Discovery reference | Region | Barycentric | Topocentric |
|---|---|---:|---:|
| 22 February 2023 | core | 0.504765 | 0.795469 |
| 22 February 2023 | broad_pattern | 0.932862 | 0.863740 |
| 28 February 2023 | core | 0.839913 | 0.837973 |
| 28 February 2023 | broad_pattern | 0.934338 | 0.910320 |

The discovery-to-discovery pair illustrates the contrast: core r = 0.491621 / 0.795469 (barycentric/topocentric), while the broader pattern gives 0.936738 / 0.844334. Core correlations do not show a uniform frame preference under both references. The available BERV span is only 3.193229 km/s, about 1.225 nominal resolution elements. These correlations are descriptive, not a calibrated frame-discrimination test or origin assignment.

Native order 2 closely follows the same-exposure merged extraction: core r = 0.989192–0.992350 and broader-pattern r = 0.984655–0.986099. Those reductions share an observation and are not independent confirmations. Order 3 has core r = 0.181486–0.224722, incomplete broader coverage and many nonpositive flux samples. It cannot supply independent line corroboration. Its native flux unit is unspecified; merged flux is uncalibrated ADU. No physical flux ratio between reductions is claimed.

[Complete measurements and figures](analysis/RESULTS_REPORT.md) · [Scientific interpretation](scientific_review/RESULT_INTERPRETATION.md) · [All 64 comparisons](analysis/results/COMPARISONS.csv) · [All 20 profile/quality records](analysis/results/PROFILE_METRICS.csv) · [Machine-readable closure](GROUP_CLOSURE.json)

## Verification and preservation

[Independent numerical reconstruction](independent_audit/NUMERICAL_AUDIT.json) passes 504 checks and 76,086 scalar comparisons. It independently decoded all ten compact source windows from exact FITS inputs, reconstructed all profiles and comparisons, and verified all four unchanged raw-context panels. Source flux/error/index values match exactly; the largest comparison difference is 4.27e-13. This is independent arithmetic and machine review, not human peer review or independent observing time.

[Input audit](input_audit/INPUT_AUDIT.json) verifies the original three source archives and all fourteen restored files without new acquisition. [Preservation instructions](preservation/README.md) describe exact restoration and public compact arrays. No new archive request, full-spectrum survey exposure or telescope observation was added. The previous 0235 investigation, original mapping dispositions, normalization follow-ups and 4,370-profile epoch analysis remain unchanged.

No positive finite ERR samples are available in the selected windows. Flank medians are reference levels within structured spectra, not established quiet continuum; interpolation and shared inputs create dependence. The two records are overlapping descriptions of one context group, not two independent signals. Neither a measured intrinsic linewidth nor a calibrated false-alarm rate, sensitivity or null result is supplied.

## Next fixed group

Continue with [the exact C003 handoff](NEXT_ACTION.json): five HD106515A records around 3869.75 Å, selected because the first remaining original queue row is V2E2-0022. Numerical group names do not define queue order. Preserve all five members and their existing covering-order evidence; prepare a separate bounded group comparison before wider arrays are interpreted. [Detailed next step](scientific_review/NEXT_STEP.md).

[Current SETI checkpoint](CONTINUATION_STATE.json) · [Project continuation](../CONTINUE_SETI.md). The original survey remains 300 exposures, 20 stars and 70.874650833 hours; classifications remain 403 A / 46 O / 185 U / 35 M. Rubin remains a completed limited-feasibility study with minimum 50 evaluable objects unmet. No qualified laser candidate or calibrated null result is established.
