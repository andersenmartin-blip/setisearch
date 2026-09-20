# LS8U: TESS_260647166 residual and duration-matched noise study

Both retained LS8T contexts, both products and both coordinate conventions are included. No new archive bytes or exposures were acquired. The positive TG015701_P0 remains **UNRESOLVED_WITHIN_FIXED_SCOPE**; the negative TG000101_N0 remains **SPATIALLY_STRUCTURED** under the original LS8T gate.

**Retrospective diagnostics only: energy ratios, covariance models and held-sideband comparisons are not calibrated significances, probabilities or completeness measurements.**

Independent audit **PASS**: 583,488 numerical comparisons and 625,868 exact checks; no disagreements. Eighteen pre-analysis tests pass (ten duration/cadence/boundary tests and eight inherited spatial tests). All 48 signed known-template controls, 80 signed compact controls and 128 additive checks pass.

## Fixed durations, covariance and residual comparison

TG015701_P0 sums one 49-second exposure; TG000101_N0 sums three 42-second exposures (126 seconds total exposure). The IID reference uses the exact OLS prediction weights, including the d²/n baseline-estimation term. A pooled lag-1/lag-2 correlation estimated from training-only pixel residuals, with a Bartlett taper, supplies the second model. All event/baseline covariance enters the same quadratic form for both durations. Adjacent time differences outside 0.5–1.5 times that context’s cadence split covariance blocks. This estimated separable model is descriptive: longer correlations, nonstationarity and template-estimation uncertainty are not calibrated. Both the correlated and IID references remain visible.

The positive context has 24 single-row control targets; the negative has eight nonoverlapping three-row targets. Each excludes two neighboring rows on each side from training, in addition to the original native event and its guards. Templates, variances and correlations are refitted without held values; the original geometric center and aperture stay fixed. These controls share training data and differ in leverage and position from the selected native event. Their counts are not p-values.

| Control | Product / center | Combined weighted explained | Residual/reference, correlated | Residual/reference, IID | Held blocks >= native | Correlated/IID variance | Top 10 residual pixels |
|---|---|---:|---:|---:|---:|---:|---:|
| TG000101_N0 | CAL / C0 | 61.2928% | 0.718617 | 0.908296 | 6/8 | 1.263949 | 31.2785% |
| TG000101_N0 | COR / C0 | 64.2487% | 0.723441 | 0.915097 | 6/8 | 1.264922 | 31.1154% |
| TG000101_N0 | CAL / C1 | 61.2925% | 0.699149 | 0.881258 | 6/8 | 1.260472 | 32.3723% |
| TG000101_N0 | COR / C1 | 64.3670% | 0.705153 | 0.889540 | 6/8 | 1.261485 | 32.0361% |
| TG015701_P0 | CAL / C0 | 28.5482% | 3.789134 | 3.956313 | 1/24 | 1.044121 | 6.4630% |
| TG015701_P0 | COR / C0 | 25.0652% | 3.797390 | 3.964987 | 1/24 | 1.044135 | 6.4683% |
| TG015701_P0 | CAL / C1 | 26.9637% | 3.758934 | 3.923558 | 1/24 | 1.043795 | 7.0329% |
| TG015701_P0 | COR / C1 | 23.5071% | 3.765108 | 3.930198 | 1/24 | 1.043847 | 7.0340% |

## Exact boundary accounting

Both apertures retain radius 25 and their original centers. The C0/C1 intersection cancels exactly in the difference. For each product, C1 minus C0 equals the sum over C1-only pixels minus the sum over C0-only pixels. The full signed pixel list and the analogous squared-energy identity are retained in diagnostics.json. This accounts for aperture sums; it does not uniquely assign a physical cause or explain every change in a fitted model, whose training profile/background also depend on the convention.

| Control | Product | C0-only pixels / sum ADU | C1-only pixels / sum ADU | C1 − C0 ADU |
|---|---|---:|---:|---:|
| TG000101_N0 | CAL | 70 / -4754.572785 | 70 / -2563.206745 | 2191.366039 |
| TG000101_N0 | COR | 70 / -7432.264786 | 70 / -4142.736670 | 3289.528116 |
| TG000101_N0 | DELTA | 70 / -2677.692002 | 70 / -1579.529925 | 1098.162077 |
| TG015701_P0 | CAL | 70 / 15230.293387 | 70 / 5133.487704 | -10096.805683 |
| TG015701_P0 | COR | 70 / 14395.160949 | 70 / 4322.079002 | -10073.081947 |
| TG015701_P0 | DELTA | 70 / -835.132438 | 70 / -811.408702 | 23.723736 |

## Paired correction and brightness protection

Residual CAL and DELTA use the same COR combined projector. Their energies and the signed cross term add to COR residual energy; they are not independent cause fractions.

| Control / center | CAL / COR residual energy | DELTA / COR | Twice cross / COR |
|---|---:|---:|---:|
| TG000101_N0 / C0 | 1.004212 | 0.031336 | -0.035548 |
| TG000101_N0 / C1 | 1.001990 | 0.034848 | -0.036838 |
| TG015701_P0 / C0 | 1.000190 | 0.000012 | -0.000201 |
| TG015701_P0 / C1 | 1.000338 | 0.000030 | -0.000368 |

Pure brightness additions are ±0.1% per exposure: summed coefficients are ±0.001 for the positive context and ±0.003 for the negative. Displacement additions are ±0.05 gradient units per exposure, a linearized template rather than nonlinear resampling. Five fixed compact positions receive both signs with total amplitude five modeled event-pixel SDs, interpreted as equal additions over the event duration. The table shows losses from hypothetical displacement plus constant subtraction. No subtraction, veto or new mask is adopted.

| Control | Product / center | Brightness weighted energy retained | Brightness signed flux retained |
|---|---|---:|---:|
| TG000101_N0 | CAL / C0 | 86.3034% | 92.1564% |
| TG000101_N0 | COR / C0 | 86.2270% | 92.1834% |
| TG000101_N0 | CAL / C1 | 86.9283% | 92.6722% |
| TG000101_N0 | COR / C1 | 86.8603% | 92.6944% |
| TG015701_P0 | CAL / C0 | 85.0761% | 86.9133% |
| TG015701_P0 | COR / C0 | 85.0659% | 86.9248% |
| TG015701_P0 | CAL / C1 | 85.4202% | 87.2123% |
| TG015701_P0 | COR / C1 | 85.4169% | 87.2125% |

## All COR residual maps and held-block controls

Each panel has its own symmetric scale and retains the unchanged aperture. Standardized pixels are divided by the modeled event SD, not Gaussian sigmas. Only the plotting viewport is cropped; no analysis pixels are removed.

![TG000101_N0 residuals](TG000101_N0_residuals.png)

![TG015701_P0 residuals](TG015701_P0_residuals.png)

## Stop and interpretation boundaries

A high ratio establishes a mismatch with these local sidebands under the stated model; a low ratio does not prove an ordinary-noise origin. Fixed ring/quadrant partitions and top-pixel concentrations describe the residual without selecting pixels to refit. The LS8T classifications and LS8S thresholds remain unchanged. No technical-origin interpretation, qualified candidate, detector or coverage is established.

This single bounded study is closed regardless of result. Rank-5 EC 12578-2107 is next for a separately frozen independent transfer from the unchanged target ledger, exact pair CH_PR100002_TG008901_V0300 and CH_PR100002_TG008902_V0300. Its science values remain unopened. Further TESS_260647166 tuning is not part of this study. Raw imagettes, reserved TESS/M43 material and the unsent calibration request remain unchanged.

[Protocol](../LS8U_RESIDUAL_NOISE_PROTOCOL.md) · [Full diagnostics](diagnostics.json) · [Signed injections](injection_controls.json) · [Audit](audit.json) · [Original LS8T report](../results_ls8t_images/REPORT.md)
