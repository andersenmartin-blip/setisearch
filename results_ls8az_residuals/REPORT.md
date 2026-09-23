# LS8AZ: GJ 536 residual and duration-matched noise study

Both unresolved LS8AY positive contexts, both products and both conventions are included. The other seven representatives retain their closed image labels without additional native fitting. No new archive bytes or exposures were acquired. TG023501_P1 and TG023501_P6 remain **UNRESOLVED_WITHIN_FIXED_SCOPE** under the original LS8AY gate.

**Retrospective diagnostics only: energy ratios, covariance models and held-sideband comparisons are not calibrated significances, probabilities or completeness measurements.**

Independent audit **PASS**: 610,586 numerical comparisons and 640,224 exact checks; no disagreements. Eighteen pre-analysis tests pass (ten duration/cadence/boundary tests and eight inherited spatial tests). All 48 signed known-template controls, 80 signed compact controls and 128 additive checks pass.

## Fixed durations, covariance and residual comparison

TG023501_P1 and TG023501_P6 are each one 40.1699981689453-second exposure. The IID reference uses the exact OLS prediction weights, including the d²/n baseline-estimation term. A pooled lag-1/lag-2 correlation estimated from training-only pixel residuals, with a Bartlett taper, supplies the second model. All event/baseline covariance enters the same quadratic form for the native and held rows. Adjacent time differences outside 0.5–1.5 times that context’s cadence split covariance blocks. This estimated separable model is descriptive: longer correlations, nonstationarity and template-estimation uncertainty are not calibrated. Both the correlated and IID references remain visible.

Each positive context has 24 single-row control targets. Each excludes two neighboring rows on each side from training, in addition to the original native event and its guards. Templates, variances and correlations are refitted without held values; the original geometric center and aperture stay fixed. These controls share training data and differ in leverage and position from the selected native event. Their counts are not p-values.

| Control | Product / center | Combined weighted explained | Residual/reference, correlated | Residual/reference, IID | Held blocks >= native | Correlated/IID variance | Top 10 residual pixels |
|---|---|---:|---:|---:|---:|---:|---:|
| TG023501_P1 | CAL / C0 | 24.9428% | 0.256696 | 0.269745 | 23/24 | 1.050837 | 10.7107% |
| TG023501_P1 | COR / C0 | 24.1421% | 0.257893 | 0.271008 | 23/24 | 1.050858 | 10.6978% |
| TG023501_P1 | CAL / C1 | 24.5980% | 0.262940 | 0.276316 | 23/24 | 1.050868 | 10.6063% |
| TG023501_P1 | COR / C1 | 23.7633% | 0.263414 | 0.276812 | 23/24 | 1.050864 | 10.6044% |
| TG023501_P6 | CAL / C0 | 56.9584% | 3935.177956 | 4017.485725 | 0/24 | 1.020916 | 4.8321% |
| TG023501_P6 | COR / C0 | 54.8082% | 3841.994548 | 3922.327190 | 0/24 | 1.020909 | 5.0371% |
| TG023501_P6 | CAL / C1 | 56.8665% | 4020.960233 | 4104.782880 | 0/24 | 1.020846 | 4.7344% |
| TG023501_P6 | COR / C1 | 54.7359% | 3951.598570 | 4034.086818 | 0/24 | 1.020875 | 4.9557% |

## Exact boundary accounting

Both apertures retain radius 25 and their original centers. The C0/C1 intersection cancels exactly in the difference. For each product, C1 minus C0 equals the sum over C1-only pixels minus the sum over C0-only pixels. The full signed pixel list and the analogous squared-energy identity are retained in diagnostics.json. This accounts for aperture sums; it does not uniquely assign a physical cause or explain every change in a fitted model, whose training profile/background also depend on the convention.

| Control | Product | C0-only pixels / sum ADU | C1-only pixels / sum ADU | C1 − C0 ADU |
|---|---|---:|---:|---:|
| TG023501_P1 | CAL | 71 / -122.042528 | 71 / 617.810108 | 739.852635 |
| TG023501_P1 | COR | 71 / -189.717241 | 71 / 513.604367 | 703.321609 |
| TG023501_P1 | DELTA | 71 / -67.674713 | 71 / -104.205740 | -36.531027 |
| TG023501_P6 | CAL | 71 / 344075.651881 | 71 / 410593.936782 | 66518.284900 |
| TG023501_P6 | COR | 71 / 335526.324732 | 71 / 402109.197582 | 66582.872850 |
| TG023501_P6 | DELTA | 71 / -8549.327150 | 71 / -8484.739200 | 64.587950 |

## Paired correction and brightness protection

Residual CAL and DELTA use the same COR combined projector. Their energies and the signed cross term add to COR residual energy; they are not independent cause fractions.

| Control / center | CAL / COR residual energy | DELTA / COR | Twice cross / COR |
|---|---:|---:|---:|
| TG023501_P1 / C0 | 1.001211 | 0.000737 | -0.001948 |
| TG023501_P1 / C1 | 1.000091 | 0.000366 | -0.000457 |
| TG023501_P6 / C0 | 1.024391 | 0.114235 | -0.138626 |
| TG023501_P6 / C1 | 1.023431 | 0.112237 | -0.135668 |

Pure brightness additions are ±0.1% per exposure: summed coefficients are ±0.001 for each one-row context. Displacement additions are ±0.05 gradient units per exposure, a linearized template rather than nonlinear resampling. Five fixed compact positions receive both signs with total amplitude five modeled event-pixel SDs, interpreted as equal additions over the event duration. The table shows losses from hypothetical displacement plus constant subtraction. No subtraction, veto or new mask is adopted.

| Control | Product / center | Brightness weighted energy retained | Brightness signed flux retained |
|---|---|---:|---:|
| TG023501_P1 | CAL / C0 | 83.3323% | 88.8504% |
| TG023501_P1 | COR / C0 | 83.2857% | 88.8727% |
| TG023501_P1 | CAL / C1 | 83.5827% | 89.0307% |
| TG023501_P1 | COR / C1 | 83.5799% | 89.0331% |
| TG023501_P6 | CAL / C0 | 83.4506% | 88.5336% |
| TG023501_P6 | COR / C0 | 83.4325% | 88.5233% |
| TG023501_P6 | CAL / C1 | 83.7763% | 88.6843% |
| TG023501_P6 | COR / C1 | 83.7582% | 88.6957% |

## All COR residual maps and held-block controls

Each panel has its own symmetric scale and retains the unchanged aperture. Standardized pixels are divided by the modeled event SD, not Gaussian sigmas. Only the plotting viewport is cropped; no analysis pixels are removed.

![TG023501_P1 residuals](TG023501_P1_residuals.png)

![TG023501_P6 residuals](TG023501_P6_residuals.png)

## Stop and interpretation boundaries

A high ratio establishes a mismatch with these local sidebands under the stated model; a low ratio does not prove an ordinary-noise origin. Fixed ring/quadrant partitions and top-pixel concentrations describe the residual without selecting pixels to refit. The LS8AY classifications and LS8AX thresholds remain unchanged. No technical-origin interpretation, qualified candidate, detector or coverage is established.

This single bounded study is closed regardless of result. Rank-21 2MASS J11285624+1010395 is next for a separately frozen independent transfer from the unchanged target ledger, exact pair CH_PR100018_TG010801_V0300 and CH_PR100018_TG010802_V0300. Its science values remain unopened. Further GJ 536 tuning is not part of this study. Raw imagettes, reserved TESS/M43 material and the unsent calibration request remain unchanged.

[Protocol](../LS8AZ_RESIDUAL_NOISE_PROTOCOL.md) · [Full diagnostics](diagnostics.json) · [Signed injections](injection_controls.json) · [Audit](audit.json) · [Original LS8AY report](../results_ls8ay_images/REPORT.md)
