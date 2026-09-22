# LS8AS: GJ 581 residual and duration-matched noise study

Both unresolved LS8AR positive contexts, both products and both conventions are included. The other 12 representatives retain their closed image labels without additional native fitting. No new archive bytes or exposures were acquired. TG023701_P3 and TG023701_P5 remain **UNRESOLVED_WITHIN_FIXED_SCOPE** under the original LS8AR gate.

**Retrospective diagnostics only: energy ratios, covariance models and held-sideband comparisons are not calibrated significances, probabilities or completeness measurements.**

Independent audit **PASS**: 610,448 numerical comparisons and 640,222 exact checks; no disagreements. Eighteen pre-analysis tests pass (ten duration/cadence/boundary tests and eight inherited spatial tests). All 48 signed known-template controls, 80 signed compact controls and 128 additive checks pass.

## Fixed durations, covariance and residual comparison

TG023701_P3 and TG023701_P5 are each one 60-second exposure. The IID reference uses the exact OLS prediction weights, including the d²/n baseline-estimation term. A pooled lag-1/lag-2 correlation estimated from training-only pixel residuals, with a Bartlett taper, supplies the second model. All event/baseline covariance enters the same quadratic form for the native and held rows. Adjacent time differences outside 0.5–1.5 times that context’s cadence split covariance blocks. This estimated separable model is descriptive: longer correlations, nonstationarity and template-estimation uncertainty are not calibrated. Both the correlated and IID references remain visible.

Each positive context has 24 single-row control targets. Each excludes two neighboring rows on each side from training, in addition to the original native event and its guards. Templates, variances and correlations are refitted without held values; the original geometric center and aperture stay fixed. These controls share training data and differ in leverage and position from the selected native event. Their counts are not p-values.

| Control | Product / center | Combined weighted explained | Residual/reference, correlated | Residual/reference, IID | Held blocks >= native | Correlated/IID variance | Top 10 residual pixels |
|---|---|---:|---:|---:|---:|---:|---:|
| TG023701_P3 | CAL / C0 | 60.6226% | 1.062146 | 1.066423 | 13/24 | 1.004026 | 6.6790% |
| TG023701_P3 | COR / C0 | 59.4309% | 1.179547 | 1.184342 | 9/24 | 1.004065 | 6.8297% |
| TG023701_P3 | CAL / C1 | 62.6115% | 1.048930 | 1.052996 | 13/24 | 1.003876 | 6.7245% |
| TG023701_P3 | COR / C1 | 61.4760% | 1.161620 | 1.166219 | 9/24 | 1.003959 | 6.8042% |
| TG023701_P5 | CAL / C0 | 9.4451% | 2.872995 | 2.953546 | 3/24 | 1.028037 | 9.5398% |
| TG023701_P5 | COR / C0 | 24.1886% | 3.192676 | 3.267799 | 1/24 | 1.023530 | 9.9063% |
| TG023701_P5 | CAL / C1 | 6.5015% | 2.784437 | 2.863137 | 3/24 | 1.028264 | 10.5895% |
| TG023701_P5 | COR / C1 | 20.3780% | 3.078003 | 3.150440 | 2/24 | 1.023534 | 10.9766% |

## Exact boundary accounting

Both apertures retain radius 25 and their original centers. The C0/C1 intersection cancels exactly in the difference. For each product, C1 minus C0 equals the sum over C1-only pixels minus the sum over C0-only pixels. The full signed pixel list and the analogous squared-energy identity are retained in diagnostics.json. This accounts for aperture sums; it does not uniquely assign a physical cause or explain every change in a fitted model, whose training profile/background also depend on the convention.

| Control | Product | C0-only pixels / sum ADU | C1-only pixels / sum ADU | C1 − C0 ADU |
|---|---|---:|---:|---:|
| TG023701_P3 | CAL | 71 / 7520.930686 | 71 / 10822.090559 | 3301.159872 |
| TG023701_P3 | COR | 71 / 7097.075074 | 71 / 10398.135070 | 3301.059997 |
| TG023701_P3 | DELTA | 71 / -423.855613 | 71 / -423.955489 | -0.099876 |
| TG023701_P5 | CAL | 71 / 9236.092776 | 71 / -1455.652258 | -10691.745034 |
| TG023701_P5 | COR | 71 / 11888.972253 | 71 / 1183.922594 | -10705.049660 |
| TG023701_P5 | DELTA | 71 / 2652.879478 | 71 / 2639.574852 | -13.304626 |

## Paired correction and brightness protection

Residual CAL and DELTA use the same COR combined projector. Their energies and the signed cross term add to COR residual energy; they are not independent cause fractions.

| Control / center | CAL / COR residual energy | DELTA / COR | Twice cross / COR |
|---|---:|---:|---:|
| TG023701_P3 / C0 | 1.043321 | 0.026451 | -0.069772 |
| TG023701_P3 / C1 | 1.046107 | 0.027288 | -0.073395 |
| TG023701_P5 / C0 | 1.002106 | 0.002066 | -0.004172 |
| TG023701_P5 / C1 | 1.002229 | 0.002197 | -0.004426 |

Pure brightness additions are ±0.1% per exposure: summed coefficients are ±0.001 for each one-row context. Displacement additions are ±0.05 gradient units per exposure, a linearized template rather than nonlinear resampling. Five fixed compact positions receive both signs with total amplitude five modeled event-pixel SDs, interpreted as equal additions over the event duration. The table shows losses from hypothetical displacement plus constant subtraction. No subtraction, veto or new mask is adopted.

| Control | Product / center | Brightness weighted energy retained | Brightness signed flux retained |
|---|---|---:|---:|
| TG023701_P3 | CAL / C0 | 83.7218% | 88.9576% |
| TG023701_P3 | COR / C0 | 83.2112% | 89.4045% |
| TG023701_P3 | CAL / C1 | 84.0218% | 89.1743% |
| TG023701_P3 | COR / C1 | 83.5443% | 89.5911% |
| TG023701_P5 | CAL / C0 | 84.1815% | 88.2323% |
| TG023701_P5 | COR / C0 | 83.9876% | 88.7927% |
| TG023701_P5 | CAL / C1 | 84.3201% | 88.4079% |
| TG023701_P5 | COR / C1 | 84.1667% | 88.9671% |

## All COR residual maps and held-block controls

Each panel has its own symmetric scale and retains the unchanged aperture. Standardized pixels are divided by the modeled event SD, not Gaussian sigmas. Only the plotting viewport is cropped; no analysis pixels are removed.

![TG023701_P3 residuals](TG023701_P3_residuals.png)

![TG023701_P5 residuals](TG023701_P5_residuals.png)

## Stop and interpretation boundaries

A high ratio establishes a mismatch with these local sidebands under the stated model; a low ratio does not prove an ordinary-noise origin. Fixed ring/quadrant partitions and top-pixel concentrations describe the residual without selecting pixels to refit. The LS8AR classifications and LS8AQ thresholds remain unchanged. No technical-origin interpretation, qualified candidate, detector or coverage is established.

This single bounded study is closed regardless of result. Rank-16 EC14599-2047 is next for a separately frozen independent transfer from the unchanged target ledger, exact pair CH_PR100002_TG010301_V0300 and CH_PR100002_TG010302_V0300. Its science values remain unopened. Further GJ 581 tuning is not part of this study. Raw imagettes, reserved TESS/M43 material and the unsent calibration request remain unchanged.

[Protocol](../LS8AS_RESIDUAL_NOISE_PROTOCOL.md) · [Full diagnostics](diagnostics.json) · [Signed injections](injection_controls.json) · [Audit](audit.json) · [Original LS8AR report](../results_ls8ar_images/REPORT.md)
