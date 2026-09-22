# LS8AN: HD 106315 residual and duration-matched noise study

All three retained LS8AM positive contexts, both products and both coordinate conventions are included. No new archive bytes or exposures were acquired. TG000801_P0, TG000801_P1 and TG001401_P0 remain **UNRESOLVED_WITHIN_FIXED_SCOPE** under the original LS8AM gate.

**Retrospective diagnostics only: energy ratios, covariance models and held-sideband comparisons are not calibrated significances, probabilities or completeness measurements.**

Independent audit **PASS**: 916,452 numerical comparisons and 960,362 exact checks; no disagreements. Eighteen pre-analysis tests pass (ten duration/cadence/boundary tests and eight inherited spatial tests). All 72 signed known-template controls, 120 signed compact controls and 192 additive checks pass.

## Fixed durations, covariance and residual comparison

TG000801_P0, TG000801_P1 and TG001401_P0 are each one 41-second exposure. The IID reference uses the exact OLS prediction weights, including the d²/n baseline-estimation term. A pooled lag-1/lag-2 correlation estimated from training-only pixel residuals, with a Bartlett taper, supplies the second model. All event/baseline covariance enters the same quadratic form for the native and held rows. Adjacent time differences outside 0.5–1.5 times that context’s cadence split covariance blocks. This estimated separable model is descriptive: longer correlations, nonstationarity and template-estimation uncertainty are not calibrated. Both the correlated and IID references remain visible.

Each positive context has 24 single-row control targets. Each excludes two neighboring rows on each side from training, in addition to the original native event and its guards. Templates, variances and correlations are refitted without held values; the original geometric center and aperture stay fixed. These controls share training data and differ in leverage and position from the selected native event. Their counts are not p-values.

| Control | Product / center | Combined weighted explained | Residual/reference, correlated | Residual/reference, IID | Held blocks >= native | Correlated/IID variance | Top 10 residual pixels |
|---|---|---:|---:|---:|---:|---:|---:|
| TG000801_P0 | CAL / C0 | 42.4016% | 33.573516 | 34.117666 | 0/24 | 1.016208 | 43.4832% |
| TG000801_P0 | COR / C0 | 52.0935% | 20.138851 | 20.467972 | 0/24 | 1.016343 | 6.9752% |
| TG000801_P0 | CAL / C1 | 43.1533% | 31.671128 | 32.183506 | 0/24 | 1.016178 | 42.8158% |
| TG000801_P0 | COR / C1 | 51.9587% | 19.920447 | 20.246230 | 0/24 | 1.016354 | 7.4827% |
| TG000801_P1 | CAL / C0 | 41.7635% | 0.691696 | 0.722840 | 16/24 | 1.045025 | 7.0286% |
| TG000801_P1 | COR / C0 | 41.0812% | 0.732455 | 0.765488 | 16/24 | 1.045099 | 6.7860% |
| TG000801_P1 | CAL / C1 | 42.1080% | 0.695904 | 0.727437 | 16/24 | 1.045313 | 7.0615% |
| TG000801_P1 | COR / C1 | 41.3908% | 0.741480 | 0.775075 | 15/24 | 1.045307 | 6.7698% |
| TG001401_P0 | CAL / C0 | 11.4694% | 0.763379 | 0.782478 | 18/24 | 1.025018 | 8.7308% |
| TG001401_P0 | COR / C0 | 24.0394% | 0.832824 | 0.850206 | 15/24 | 1.020871 | 8.5445% |
| TG001401_P0 | CAL / C1 | 10.1728% | 0.774771 | 0.794095 | 17/24 | 1.024941 | 8.8058% |
| TG001401_P0 | COR / C1 | 22.0439% | 0.840364 | 0.857895 | 15/24 | 1.020862 | 8.7577% |

## Exact boundary accounting

Both apertures retain radius 25 and their original centers. The C0/C1 intersection cancels exactly in the difference. For each product, C1 minus C0 equals the sum over C1-only pixels minus the sum over C0-only pixels. The full signed pixel list and the analogous squared-energy identity are retained in diagnostics.json. This accounts for aperture sums; it does not uniquely assign a physical cause or explain every change in a fitted model, whose training profile/background also depend on the convention.

| Control | Product | C0-only pixels / sum ADU | C1-only pixels / sum ADU | C1 − C0 ADU |
|---|---|---:|---:|---:|
| TG000801_P0 | CAL | 71 / 19651.570092 | 71 / 4472.849708 | -15178.720384 |
| TG000801_P0 | COR | 71 / 13731.755527 | 71 / 3627.272410 | -10104.483117 |
| TG000801_P0 | DELTA | 71 / -5919.814565 | 71 / -845.577298 | 5074.237267 |
| TG000801_P1 | CAL | 71 / 1950.884573 | 71 / 2196.033734 | 245.149161 |
| TG000801_P1 | COR | 71 / 1851.323756 | 71 / 2095.024002 | 243.700246 |
| TG000801_P1 | DELTA | 71 / -99.560818 | 71 / -101.009733 | -1.448915 |
| TG001401_P0 | CAL | 70 / 3655.787211 | 70 / 70.510016 | -3585.277195 |
| TG001401_P0 | COR | 70 / 5300.021610 | 70 / 1759.117204 | -3540.904406 |
| TG001401_P0 | DELTA | 70 / 1644.234399 | 70 / 1688.607188 | 44.372789 |

## Paired correction and brightness protection

Residual CAL and DELTA use the same COR combined projector. Their energies and the signed cross term add to COR residual energy; they are not independent cause fractions.

| Control / center | CAL / COR residual energy | DELTA / COR | Twice cross / COR |
|---|---:|---:|---:|
| TG000801_P0 / C0 | 1.680077 | 0.613508 | -1.293585 |
| TG000801_P0 / C1 | 1.631027 | 0.526816 | -1.157843 |
| TG000801_P1 / C0 | 1.013367 | 0.023027 | -0.036395 |
| TG000801_P1 / C1 | 1.013963 | 0.023695 | -0.037657 |
| TG001401_P0 / C0 | 1.015073 | 0.008517 | -0.023590 |
| TG001401_P0 / C1 | 1.014945 | 0.008782 | -0.023727 |

Pure brightness additions are ±0.1% per exposure: summed coefficients are ±0.001 for each one-row context. Displacement additions are ±0.05 gradient units per exposure, a linearized template rather than nonlinear resampling. Five fixed compact positions receive both signs with total amplitude five modeled event-pixel SDs, interpreted as equal additions over the event duration. The table shows losses from hypothetical displacement plus constant subtraction. No subtraction, veto or new mask is adopted.

| Control | Product / center | Brightness weighted energy retained | Brightness signed flux retained |
|---|---|---:|---:|
| TG000801_P0 | CAL / C0 | 83.1454% | 92.5717% |
| TG000801_P0 | COR / C0 | 83.0835% | 92.5932% |
| TG000801_P0 | CAL / C1 | 84.0838% | 92.9252% |
| TG000801_P0 | COR / C1 | 83.8733% | 92.9917% |
| TG000801_P1 | CAL / C0 | 83.6564% | 92.3495% |
| TG000801_P1 | COR / C0 | 83.0516% | 92.5313% |
| TG000801_P1 | CAL / C1 | 84.4876% | 92.6761% |
| TG000801_P1 | COR / C1 | 83.8279% | 92.8915% |
| TG001401_P0 | CAL / C0 | 84.1860% | 85.9013% |
| TG001401_P0 | COR / C0 | 84.1791% | 86.8818% |
| TG001401_P0 | CAL / C1 | 84.4492% | 86.2615% |
| TG001401_P0 | COR / C1 | 84.4315% | 87.0784% |

## All COR residual maps and held-block controls

Each panel has its own symmetric scale and retains the unchanged aperture. Standardized pixels are divided by the modeled event SD, not Gaussian sigmas. Only the plotting viewport is cropped; no analysis pixels are removed.

![TG000801_P0 residuals](TG000801_P0_residuals.png)

![TG000801_P1 residuals](TG000801_P1_residuals.png)

![TG001401_P0 residuals](TG001401_P0_residuals.png)

## Stop and interpretation boundaries

A high ratio establishes a mismatch with these local sidebands under the stated model; a low ratio does not prove an ordinary-noise origin. Fixed ring/quadrant partitions and top-pixel concentrations describe the residual without selecting pixels to refit. The LS8AM classifications and LS8AL thresholds remain unchanged. No technical-origin interpretation, qualified candidate, detector or coverage is established.

This single bounded study is closed regardless of result. Rank-14 WASP-103 is next for a separately frozen independent transfer from the unchanged target ledger, exact pair CH_PR100013_TG000101_V0300 and CH_PR100013_TG000102_V0300. Its science values remain unopened. Further HD 106315 tuning is not part of this study. Raw imagettes, reserved TESS/M43 material and the unsent calibration request remain unchanged.

[Protocol](../LS8AN_RESIDUAL_NOISE_PROTOCOL.md) · [Full diagnostics](diagnostics.json) · [Signed injections](injection_controls.json) · [Audit](audit.json) · [Original LS8AM report](../results_ls8am_images/REPORT.md)
