# LS8AX–LS8AZ — GJ 536 result and exact continuation

23 September 2026. The predetermined pair and its single bounded residual
study are **complete and closed**, preserving all nine original image labels.

The rank-20 GJ 536 pair supplied **4,254 rows and 10,215 eligible overlapping
windows**. There are 38 positive crossings in eight clusters and five negative
crossings in one cluster. Every signed representative completed image follow-up:
**three CORRECTION_LINKED, four SPATIALLY_STRUCTURED and two
UNRESOLVED_WITHIN_FIXED_SCOPE**. These descriptive labels assign neither
unique physical causes nor artificial origin. The original +/-8.5 scores are
not Gaussian significances; overlapping windows are not independent trials.

The complete unresolved set, TG023501_P1/P6, then received one separately
frozen retained-data study: eight native product/convention cases, 192 held
cases and 128 signed controls, with **zero new archive bytes**. In COR, P1's
residual/reference ratios are **0.257893 / 0.263414** (C0/C1), with **23/24**
local controls at least as large in each convention. P6's ratios are
**3841.994548 / 3951.598570**, with **0/24** controls at least as large.
These dependent control counts are not false-alarm probabilities.

**The very large P6 peak coincides with a broad oblique bright band crossing
the full saved subarray and the source aperture in both CAL and COR.** The
residual maps retain broad signed structure, especially toward the aperture
boundary. A large residual here demonstrates a severe mismatch with the local
reference/model; it does not establish a clean point-source brightening or a
SETI signal. P1's much smaller residual does not prove ordinary noise either.
Both causes remain unassigned and both original unresolved labels remain.
No extra fit, mask, subtraction or image-classification rule is adopted.

All five data-reading/analysis workflows succeed. The preceding AX checkout
attempt timed out before any archive access; its failure is retained separately.
The 5 transport / 2 L2 / 11 image / 18 residual tests pass. Independent audits
pass **122,580 L2 comparisons**, **2,393 metadata checks**, **850,833 numerical
/ 1,445,201 exact image checks**, and **610,586 numerical / 640,224 exact
residual checks**, with zero disagreements at unchanged tolerances. All 309
new scientific files match their public Git identities locally, and all 12
figures have been visually inspected. No qualified candidate, detector,
sensitivity or observing-coverage claim is added.

## Complete L2 scope and eligibility

Both visits independently verify NEXP=1, EXPTIME=TEXPTIME and pipeline 14.1.2.
Their own exposure values differ; the scorer uses each verified cadence.
Keep one/two/three-row durations, 12-row sidebands, two-row guards, +/-8.5
endpoints, finite/positive-error/STATUS=0 context requirements and
0.5–1.5-cadence steps. Gaps are not bridged; EVENT remains metadata.

| Visit | Exposure seconds | Rows | STATUS=0 finite | Eligible windows | Positive / negative crossings | Positive / negative clusters |
|---|---:|---:|---:|---:|---:|---:|
| CH_PR100011_TG023501_V0300 | 40.1699981689453 | 4133 | 4101 | 10032 | 32 / 5 | 7 / 1 |
| CH_PR100018_TG007801_V0300 | 40.2000007629395 | 121 | 119 | 183 | 6 / 0 | 1 / 0 |

The first visit has 3,370 / 3,344 / 3,318 eligible one/two/three-row windows;
the second has 63 / 61 / 59. All 4,254 rows remain retained. There are 32
flagged rows and 21 cadence gaps in the first visit, versus flagged rows
39/40 and a gap after row 39 in the second. The complete eligible-row intervals
are retained in the release verification; their union is bookkeeping, not
qualified observing coverage. Indices are zero-based.

The first visit's display maximum, row 3408, is 1.695203988 times its
STATUS=0 visit median and occurs in six eligible event windows; it is P6 and
receives all prescribed follow-up. A separate retained point at row 1977 is
1.511025498 times that median but has STATUS=1 and belongs to no eligible
event window. Its cause remains unassigned; no image follow-up is silently
substituted for the original eligibility rule. The display minimum at row
1978 is also outside eligible event windows. The second visit's maximum,
row 17 (1.010879448 times its visit median), is tested as TG007801_P0;
its minimum at row 1 is outside complete left context. Display ratios are
not the local fitted excesses listed below.

## All original signed image representatives

All representatives have duration one row. The eight TG023501 representatives
use 40.1699981689453-second exposures; TG007801_P0 uses 40.2000007629395 seconds.
The original event row fixes its unaltered 29-row context [start-14,start+15).
All nine contexts are disjoint within their visits: 261 context rows and 522
unique CAL/COR joins, verified before pixels. Exposure integration does not
establish the duration of a possible shorter physical pulse.

| Representative | Start row | Original score | Excess / local baseline | Fixed label | DELTA/COR C0 / C1 |
|---|---:|---:|---:|---|---:|
| TG023501_P0 | 1816 | +18.968234 | +0.576269% | SPATIALLY_STRUCTURED | -0.321952 / -0.409874 |
| TG023501_P1 | 1849 | +9.877824 | +0.226988% | UNRESOLVED_WITHIN_FIXED_SCOPE | -0.060327 / -0.060201 |
| TG023501_P2 | 2573 | +13.572894 | +0.384290% | SPATIALLY_STRUCTURED | -0.095293 / -0.113964 |
| TG023501_P3 | 2770 | +31.864099 | +0.759873% | CORRECTION_LINKED | -0.976739 / -0.992979 |
| TG023501_P4 | 3082 | +20.039903 | +0.462369% | SPATIALLY_STRUCTURED | -0.470309 / -0.799208 |
| TG023501_P5 | 3323 | +15.723833 | +0.361474% | SPATIALLY_STRUCTURED | +0.056801 / +0.056574 |
| TG023501_P6 | 3408 | +2923.687795 | +69.592873% | UNRESOLVED_WITHIN_FIXED_SCOPE | -0.051018 / -0.050770 |
| TG023501_N0 | 802 | -14.861686 | -0.387849% | CORRECTION_LINKED | +1.269167 / +1.288950 |
| TG007801_P0 | 17 | +47.629872 | +1.104699% | CORRECTION_LINKED | -4.107454 / -3.806229 |

The unchanged gate order requires complete apertures and matching COR/L2
signs in both center conventions. CORRECTION_LINKED is tested first: absolute
DELTA/COR or column-DELTA/COR >=0.5 in both. Otherwise, displacement explained
energy >=0.8 with >=0.2 advantage over brightness in both gives
SPATIALLY_STRUCTURED. Remaining events stay unresolved. P4's C1 correction
ratio alone cannot satisfy the two-convention gate; it passes the spatial gate.
A correction label does not identify one correction component or exclude source
variability; a spatial label describes the fit without assigning a cause.

For P1, original COR displacement explained energy is 38.88464% / 38.87776%;
for P6, 70.41623% / 70.43642%. Their correction ratios also remain below the
original gate. Smearing fits are rank deficient and unavailable. P1 shows
weak mixed signed structure over the stellar profile; P6's broad band is
visible in both products, while DELTA is weaker on the common scale. Visual
inspection does not alter the labels or introduce selected pixels to refit.

## Single retained-data study and its limits

LS8AZ freezes the complete unresolved set P1/P6, independently checked against
the full nine-ID/label ledger. The seven other labels are closed and receive
no new native fitting. Contexts 1835:1864 and 3394:3423 include CAL/COR and
C0/C1, using 37,120,000 retained uncompressed image bytes and no new archive
bytes. Training-only temporal fits, templates, lag-1/lag-2 Bartlett covariance,
50/50 variance shrinkage, original apertures and guard exclusions are retained.
All 24 held sideband targets per context are refitted without their own values
or adjacent guards entering training.

The following combined-model COR energy ratios compare residuals with their
local reference. The full report also retains every CAL case.

| Representative | Center | Correlated residual/reference | IID residual/reference | Held >= native | Combined weighted explained | Top-10 weighted residual pixels | Injected brightness flux retained after hypothetical subtraction |
|---|---|---:|---:|---:|---:|---:|---:|
| TG023501_P1 | C0 | 0.257892521 | 0.271008291 | 23/24 | 24.14208% | 10.69784% | 88.87268% |
| TG023501_P1 | C1 | 0.263413889 | 0.276812070 | 23/24 | 23.76335% | 10.60445% | 89.03311% |
| TG023501_P6 | C0 | 3841.994547746 | 3922.327189804 | 0/24 | 54.80815% | 5.03712% | 88.52327% |
| TG023501_P6 | C1 | 3951.598569808 | 4034.086818375 | 0/24 | 54.73591% | 4.95574% | 88.69571% |

P1 has 23 larger or equal local controls in either convention. P6 lies above
all of its 24 controls, but this finite selected-context comparison supplies
no calibrated tail probability. Controls share training, differ in leverage
and follow event selection. Neither control rank establishes noise,
astrophysical or artificial origin; energy ratios are not Gaussian sigma.
The estimated covariance does not calibrate nonstationarity, longer lags or
template-estimation uncertainty.

P1's residual map has signed stellar-profile features, with top-10 pixels
holding 10.60–10.70% of weighted residual energy. P6 retains broad positive
and negative structure with top-10 concentration only 4.96–5.04%, and large
standardized features toward the aperture edge. Standardization uses modeled
event SD, not a calibrated Gaussian distribution. Exact signed C0/C1 boundary
lists and the CAL/DELTA cross-term identities are retained; their algebra
does not partition independent physical causes.

All 48 signed known-template controls, 80 signed compact controls and 128
additive checks pass. Hypothetical displacement-plus-constant subtraction
would lose **10.97–11.48% of injected COR brightness flux** and is not adopted.
This single bounded study ends here regardless of outcome. P1/P6 retain their
original unresolved labels; GJ 536 is not widened or tuned further.

## Exact next action

**Prepare LS8BA for rank-21 2MASS J11285624+1010395**, exact chronological
pair CH_PR100018_TG010801_V0300 / CH_PR100018_TG010802_V0300. These are both
eligible visits in the unchanged ledger. Freeze the pair and bounded header
reader, independently verify each identity, schema, row count and exposure
tuple, then separately freeze exact DEFAULT-L2 ranges before values.
Transfer the unchanged signed one/two/three-row screen and scalar audit using
each verified cadence. This target's science values remain unopened.

| Chronological visit | Exact key | Ledger start MJD | Ledger tuple, subject to own header checks |
|---|---|---:|---|
| 1 | CH_PR100018_TG010801_V0300 | 58973.0988567193 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |
| 2 | CH_PR100018_TG010802_V0300 | 58976.88448678 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |

The original 1,000-row census, 452 eligible visits and 107-cohort order remain
fixed and equal to their independent reconciliation. GJ 536's later visits
CH_PR100018_TG021001_V0300, TG021002_V0300 and TG021003_V0300 remain outside
its closed pair. Earlier unassessed points, unresolved labels and bounded
studies, including HD 106315 and GJ 581, remain unchanged. Closed WASP-103,
other closed targets and reserved TESS/M43 panels stay closed. Calibration
NOT_READY; technical request UNSENT. Standing research/publication
authorization continues; delegation is deferred.

[L2 report](results_ls8ax_l2_screen/REPORT.md) ·
[All signed image outcomes](results_ls8ay_images/REPORT.md) ·
[Bounded residual study](results_ls8az_residuals/REPORT.md) ·
[Publication and verification](PUBLICATION_2026-09-23_LS8AX_LS8AZ.md) ·
[Checkout failure and recovery](LS8AX_CHECKOUT_RECOVERY.md).
