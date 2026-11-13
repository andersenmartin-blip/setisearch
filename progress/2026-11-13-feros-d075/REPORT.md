# FEROS progress through D075 — 2026-11-13

Current completed analysis: **D075**, the individual-order follow-up to D074. Target: HD43629/TIC34077285; existing observations on 2019-11-04, 07, 08, 10 and 14. **0 qualified lasers; the three previously investigated physical origins remain unresolved.**

## What changed

The five-epoch FEROS investigation has progressed beyond the older D001 default-branch pointer. D067–D071 acquired and compared existing public archive products and established an explicit common sample-index bridge. D072 inventoried 2,565 stored FITS headers and 860 pipeline archive member names; no supplied stellar-RV/CCF fields or corresponding member names were found in that bounded material. D073 retained missing timescale/stellar-velocity information as missing and distinguished the already-applied observer correction from stellar RV. D074 computed all 540 fixed merged-profile registration curves: 216,540 grid fits, with the candidate cores excluded. Its largest red/blue difference at 0061 was 0.80 km/s.

D075 now compares **all 150 covering individual-order profiles** against those merged results: 10 epoch pairs, 5 site/HDU groups, 3 extraction modes, flat/nonflat variants and 3 fixed sideband masks. All **900 curves / 360,900 grid evaluations** were supported, with positive fitted scale at every minimum and no grid-boundary minima. Every target mask matches D074's common SDP sample indices and wavelength values exactly.

| Site | FITS HDU index | Curves | BOTH-mask shift range, km/s | Max. absolute order–merged, km/s | Max. red–blue, km/s | Max. triangle residual, km/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| D002-0061 | 29 | 180 | -0.30 to +0.60 | 0.85 | 0.85 | 1.00 |
| D002-0061 | 30 | 180 | -0.55 to +0.60 | 1.45 | 1.35 | 1.70 |
| D002-0063 | 17 | 180 | -0.40 to +0.60 | 0.00 | 0.20 | 0.15 |
| D002-0071 | 24 | 180 | -0.35 to +0.45 | 0.25 | 0.20 | 0.15 |
| D002-0071 | 25 | 180 | -0.25 to +0.45 | 0.40 | 0.45 | 0.20 |

The maxima in the last three columns include all three masks. At 0061, order versus merged minima can differ by **1.45 km/s**, red versus blue by **1.35 km/s**, and a three-epoch loop can fail closure by **1.70 km/s**. These are sensitivities of a local pattern-matching diagnostic. They do not identify the physical cause, calibrate wavelength accuracy, or establish a common physical stellar velocity. HDU indices identify product extensions, not established physical echelle-order numbers. Exact grid-minimum agreement at 0063/HDU17 is not an independent calibration test.

## Method and claim boundary

The D075 method, both numerical implementations, all 240 source-profile hashes, D074 masks/minima and previous state tables were locked before D075 array access. Earlier spectra and D074 merged results were already known: this is a prospectively fixed follow-up on known data, not a blind detection test.

Use the exact D074 target masks: 1–4 Angstrom from each fixed candidate center; exclude the central ±1 Angstrom. Map the merged mask to the order through the unchanged common SDP indices; retain any unsupported slot. Fit every earlier/later epoch pair on BOTH, BLUE and RED masks, without choosing a winning order/mode. Normalize each source by its own positive D071 baseline. Temporarily evaluate the earlier reference at target wavelength divided by sqrt((1+v/c)/(1-v/c)), interpolate linearly, and fit a free scale plus constant and linear background by unweighted least squares. Use all 401 grid nodes from −10 to +10 km/s, c=299792.458 km/s, and require full reference support. Preserve the complete SSE and coefficient curves.

**0.05 km/s is a grid step, not validated physical precision.** SSE is a descriptive residual score, not a noise likelihood, confidence interval or FAP. Merged and order products reuse photons. Source arrays and original candidate statistics were not changed. No absolute stellar RV, calibrated rest frame, persistence exclusion, covariance, laser response or physical-cause assignment is claimed.

## Validation and preservation

The alternate calculation uses explicit interpolation brackets, exp(atanh(v/c)), QR instead of least squares, and scalar SSE summation. It reproduced all **360,900 grid values and all 900 minima**, checked all 900 masks, 2,910 pair differences and 900 three-epoch closures. Largest absolute SSE discrepancy: **1.16e-10**. This is an internal alternate implementation by the same assistant, not external peer review.

All **102,833 previous state-table cells** and the same 37+141 row order were preserved exactly; eight appended columns bring the total to **104,257**. Existing 0061-rho failure, blue-COMB gap and secondary 6-March status are unchanged. No original candidate statistic was shifted or reclassified. No new archive requests, telescope observations, FITS science arrays or raw CCD arrays were used in D075.

See [METHOD.json](METHOD.json), [SUMMARY.json](SUMMARY.json), [NUMERICAL_AUDIT.json](NUMERICAL_AUDIT.json), [STATE_PRESERVATION_AUDIT.json](STATE_PRESERVATION_AUDIT.json) and the public ESO identifiers in [SOURCES.json](SOURCES.json).

## Publication scope and reproducibility

This contribution publishes a bounded text summary, method parameters, audit receipts and public source identifiers. The complete profile extraction chain, numerical arrays and binary evidence are retained in the project checkpoints and are **not included in this contribution**. These text files alone do not provide a self-contained reproduction of the complete extraction chain. No telescope payloads, evidence archives or private storage identifiers are added here. The separate historical 663-file D002/D003 delivery is still pending and is not represented as published by this update. Prior published milestone files remain intact.

## Next gate

D076 is proposed, not frozen or executed: a bounded calibrated-reference feasibility study should establish explicit calibration provenance and accuracy limits before broader template work or any physical registration claim. D074/D075 minima must not be applied to candidate statistics as a common stellar velocity. Old 141 raw-work queue remains closed; the older 90/Rubin track remains stopped. No background science job is running.
