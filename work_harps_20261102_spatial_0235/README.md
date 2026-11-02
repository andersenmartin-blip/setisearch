# V2E2-0235: completed spatial follow-up, unresolved

The 5548.09 Å discovery excursion in HD122640 has a larger, more concentrated mismatch to a fixed empirical spatial profile than all eight coordinate-selected controls. Most mismatch is inside the prescribed ±3-pixel trace band. This result persists across the three original spatial templates and the two separately frozen background sensitivities. **The event remains U; physical origin is unresolved.**

Exactly 8,275 native pixels from the already preserved discovery exposure were used: 232 disjoint training rows, one eleven-row target and eight eleven-row controls. No new archive product, detector footprint or telescope observation was added. The original 27 template/window outcomes and final 18 background-sensitivity outcomes are all retained, with no blocked windows. Reusing these pixels does not supply independent detections.

## Fixed results

| Model | Target residual L1 (ADU) | Target outside ±3 pixels | Largest pixel / target L1 |
|---|---:|---:|---:|
| pooled | 8,633.12 | 15.70% | 6.52% |
| negative_raw_flank | 8,445.26 | 15.55% | 6.62% |
| positive_raw_flank | 8,902.73 | 15.99% | 6.39% |
| negative_side | 8,817.70 | 16.24% | 6.43% |
| positive_side | 8,922.85 | 19.21% | 6.29% |

For the original pooled template, controls have residual L1 of 2,249.83–4,024.91 ADU, off-trace shares of 29.09–38.81%, and largest-pixel shares of 2.08–2.72%. The target is brighter, so the absolute residual ordering alone is not a calibrated noise test. The fixed on/off-band areas differ; per-pixel means and all eight controls are reported in the underlying tables.

With negative-side background, controls span 2,068.05–4,107.54 ADU and 29.38–35.18% off trace; with positive-side background, they span 3,178.77–4,889.81 ADU and 34.64–56.08%. The target retains higher total residual and pixel concentration, and a lower off-trace share, in each variant. No preferred estimator is selected. Background choice changes numerical values; it does not remove the near-trace discrepancy or identify its cause.

[Original complete results and readable figures](analysis/RESULTS_REPORT.md) · [Both background variants and all comparisons](background_sensitivity/results/WINDOW_METRICS.csv) · [Scientific reading](scientific_review/RESULT_INTERPRETATION.md) · [Final sensitivity interpretation](scientific_review/BACKGROUND_RESULT_REVIEW.md) · [Machine-readable case closure](CASE_CLOSURE.json)

## What remains unresolved

The result is model mismatch, not a photon fraction, significance, or demonstrated isolated off-trace charge deposit. A free template amplitude can absorb aligned contamination. Profile variation, interpolation, background errors and photon/charge mixtures remain possible. The nearby FP calibration fiber could affect the outer background, but these data do not identify that contribution. Three-pixel side medians are sensitivity checks, not calibrated noise estimates.

The [earlier May-quality comparison](../work_harps_20261102_may_quality/README.md) did not reproduce the sharp central excursion at comparable amplitude. That temporal context and the present spatial mismatch do not warrant an origin assignment. The original raw adjudication, extraction and all previous results are unchanged.

## Verification and preservation

The original exact method was published and read back before the bounded raw calculation in commit `8193e79cefabc32ec4a08230b2f77468905a5eee`; its complete results were published in `328d7646c50d1f0572858ad697da34a25ab31cfb`. The final two-background method was separately published and read back before execution in `2cb8e31a3764c25a01af7a95c1ee4126ed264d2a`. Both variants were declared before their outcomes and both are retained.

[Original independent reconstruction](independent_audit/NUMERICAL_AUDIT.json) passed 13,779 checks and 86,442 scalar comparisons, including byte-exact decoding of all 8,275 saved raw pixels. [Sensitivity reconstruction](background_sensitivity/independent_audit/NUMERICAL_AUDIT.json) passed 506 checks and 57,522 comparisons. Maximum model/residual differences are 2.28e-10 ADU and 6.82e-13 ADU respectively. These are independent calculations and machine reviews, not human peer review or independent telescope observations.

[Preservation and reproduction](preservation/README.md) records the public compact pixel/model archives and original complete raw-input provenance. The main plotting script and original images remain unchanged; additional readable figures correct only overlapping axis labels and retain all data/scales. Preserve completed outputs; reproduce in a separate copy.

## Continue from the fixed queue

This bounded 0235 investigation is closed with U retained. Do not add further background, template, aperture, registration or May-reference variants in this continuation. [The next handoff](NEXT_ACTION.json) identifies the first existing joint-context group, C001: **V2E2-0001 and V2E2-0016, HD103991, approximately 3852 Å**, in original catalog order. Prepare one joint native-order/broader-profile context analysis after verifying saved inputs; do not replay the completed mapping or epoch pipelines. [Detailed evidence requirements](scientific_review/NEXT_STEP.md) preserve native order-3 quality limits and the absence of a measured linewidth.

[Current full SETI state](CONTINUATION_STATE.json) · [Project continuation](../CONTINUE_SETI.md). The main survey remains 300 exposures, 20 targets and 70.874650833 hours; all 669 classifications and Rubin's limited-feasibility status are unchanged. No qualified laser candidate or calibrated null result is established.
