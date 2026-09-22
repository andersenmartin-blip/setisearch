# LS8AE: PG1303-114 residual and duration-matched noise study

The retained LS8AD negative context, both products and both coordinate conventions are included. No new archive bytes or exposures were acquired. TG006402_N0 remains **UNRESOLVED_WITHIN_FIXED_SCOPE** under the original LS8AD gate.

**Retrospective diagnostics only: energy ratios, covariance models and held-sideband comparisons are not calibrated significances, probabilities or completeness measurements.**

Independent audit **PASS**: 305,356 numerical comparisons and 320,126 exact checks; no disagreements. Eighteen pre-analysis tests pass (ten duration/cadence/boundary tests and eight inherited spatial tests). All 24 signed known-template controls, 40 signed compact controls and 64 additive checks pass.

## Fixed durations, covariance and residual comparison

TG006402_N0 is one 60-second exposure. The IID reference uses the exact OLS prediction weights, including the d²/n baseline-estimation term. A pooled lag-1/lag-2 correlation estimated from training-only pixel residuals, with a Bartlett taper, supplies the second model. All event/baseline covariance enters the same quadratic form for the native and held rows. Adjacent time differences outside 0.5–1.5 times that context’s cadence split covariance blocks. This estimated separable model is descriptive: longer correlations, nonstationarity and template-estimation uncertainty are not calibrated. Both the correlated and IID references remain visible.

The negative context has 24 single-row control targets. Each excludes two neighboring rows on each side from training, in addition to the original native event and its guards. Templates, variances and correlations are refitted without held values; the original geometric center and aperture stay fixed. These controls share training data and differ in leverage and position from the selected native event. Their counts are not p-values.

| Control | Product / center | Combined weighted explained | Residual/reference, correlated | Residual/reference, IID | Held blocks >= native | Correlated/IID variance | Top 10 residual pixels |
|---|---|---:|---:|---:|---:|---:|---:|
| TG006402_N0 | CAL / C0 | 19.7263% | 0.849377 | 0.880726 | 20/24 | 1.036908 | 5.4253% |
| TG006402_N0 | COR / C0 | 22.7036% | 0.878666 | 0.903129 | 20/24 | 1.027841 | 5.2802% |
| TG006402_N0 | CAL / C1 | 18.8987% | 0.847932 | 0.879110 | 20/24 | 1.036769 | 5.3813% |
| TG006402_N0 | COR / C1 | 21.6960% | 0.876726 | 0.901111 | 19/24 | 1.027814 | 5.2382% |

## Exact boundary accounting

Both apertures retain radius 25 and their original centers. The C0/C1 intersection cancels exactly in the difference. For each product, C1 minus C0 equals the sum over C1-only pixels minus the sum over C0-only pixels. The full signed pixel list and the analogous squared-energy identity are retained in diagnostics.json. This accounts for aperture sums; it does not uniquely assign a physical cause or explain every change in a fitted model, whose training profile/background also depend on the convention.

| Control | Product | C0-only pixels / sum ADU | C1-only pixels / sum ADU | C1 − C0 ADU |
|---|---|---:|---:|---:|
| TG006402_N0 | CAL | 71 / -448.470018 | 71 / -188.384204 | 260.085814 |
| TG006402_N0 | COR | 71 / -589.468368 | 71 / -327.004974 | 262.463394 |
| TG006402_N0 | DELTA | 71 / -140.998351 | 71 / -138.620770 | 2.377580 |

## Paired correction and brightness protection

Residual CAL and DELTA use the same COR combined projector. Their energies and the signed cross term add to COR residual energy; they are not independent cause fractions.

| Control / center | CAL / COR residual energy | DELTA / COR | Twice cross / COR |
|---|---:|---:|---:|
| TG006402_N0 / C0 | 1.050746 | 0.072401 | -0.123147 |
| TG006402_N0 / C1 | 1.050377 | 0.071818 | -0.122196 |

Pure brightness additions are ±0.1% per exposure: summed coefficients are ±0.001 for this one-row context. Displacement additions are ±0.05 gradient units per exposure, a linearized template rather than nonlinear resampling. Five fixed compact positions receive both signs with total amplitude five modeled event-pixel SDs, interpreted as equal additions over the event duration. The table shows losses from hypothetical displacement plus constant subtraction. No subtraction, veto or new mask is adopted.

| Control | Product / center | Brightness weighted energy retained | Brightness signed flux retained |
|---|---|---:|---:|
| TG006402_N0 | CAL / C0 | 78.2611% | 59.4997% |
| TG006402_N0 | COR / C0 | 79.5864% | 61.7662% |
| TG006402_N0 | CAL / C1 | 78.3673% | 59.5723% |
| TG006402_N0 | COR / C1 | 79.6774% | 61.8293% |

## All COR residual maps and held-block controls

Each panel has its own symmetric scale and retains the unchanged aperture. Standardized pixels are divided by the modeled event SD, not Gaussian sigmas. Only the plotting viewport is cropped; no analysis pixels are removed.

![TG006402_N0 residuals](TG006402_N0_residuals.png)

## Stop and interpretation boundaries

A high ratio establishes a mismatch with these local sidebands under the stated model; a low ratio does not prove an ordinary-noise origin. Fixed ring/quadrant partitions and top-pixel concentrations describe the residual without selecting pixels to refit. The LS8AD classifications and LS8AC thresholds remain unchanged. No technical-origin interpretation, qualified candidate, detector or coverage is established.

This single bounded study is closed regardless of result. Rank-10 PG 1207-033 is next for a separately frozen independent transfer from the unchanged target ledger, exact pair CH_PR100002_TG000901_V0300 and CH_PR100002_TG000902_V0300. Its science values remain unopened. Further PG1303-114 tuning is not part of this study. Raw imagettes, reserved TESS/M43 material and the unsent calibration request remain unchanged.

[Protocol](../LS8AE_RESIDUAL_NOISE_PROTOCOL.md) · [Full diagnostics](diagnostics.json) · [Signed injections](injection_controls.json) · [Audit](audit.json) · [Original LS8AD report](../results_ls8ad_images/REPORT.md)
