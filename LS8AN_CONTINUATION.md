# LS8AL–LS8AN — HD 106315 results and exact continuation

22 September 2026. The rank-13 pair's screen, complete signed image follow-up
and one bounded retained-data study are **complete and closed**. All three
positive image labels remain **UNRESOLVED_WITHIN_FIXED_SCOPE**. Closure ends
the prescribed study; it does not establish the physical origin of the events.

## Complete L2 result

Both exact visits independently verify NEXP=1, EXPTIME=TEXPTIME=41 seconds
and pipeline 14.1.2. The unchanged LS8K method uses 41/82/123-second events,
12-row sidebands, two-row guards, original finite/status/cadence eligibility
and symmetric +/-8.5 endpoints. EVENT remains metadata. All retained rows,
eligible windows and complete signed cluster sets are public.

| Exact visit | Rows | STATUS=0 finite rows | Eligible windows | Positive / negative crossings | Positive / negative clusters |
|---|---:|---:|---:|---:|---:|
| CH_PR100041_TG000801_V0300 | 872 | 867 | 2,079 | 7 / 0 | 2 / 0 |
| CH_PR100041_TG001401_V0300 | 1,510 | 1,478 | 2,619 | 6 / 0 | 1 / 0 |

| Representative | Visit | Zero-based event row | Duration | L2 score | Excess / local L2 baseline |
|---|---|---:|---|---:|---:|
| TG000801_P0 | CH_PR100041_TG000801_V0300 | 223 | 1 row / 41 s | +44.503884094991555 | +1.020259% |
| TG000801_P1 | CH_PR100041_TG000801_V0300 | 363 | 1 row / 41 s | +9.691535552281110 | +0.244514% |
| TG001401_P0 | CH_PR100041_TG001401_V0300 | 178 | 1 row / 41 s | +28.143188663326402 | +0.646338% |

Exactly 328,716 science-table bytes were acquired after a separate public
header result and exact-range freeze. Threshold counts concern eligible
windows, not every visible change in every retained row. The displayed visit
median is not the local screening baseline. Overlapping windows are dependent;
scores are not Gaussian sigma, probabilities or a calibrated sensitivity.

## Complete image diagnostic

The original contexts are native rows 209:238, 349:378 and 164:193. All 87
context rows have unique CAL and COR exposure joins: 174 joins and 803 exact
metadata checks before pixels, with <=1 ms MJD/BJD differences and agreeing
UTC text, exposure counters and integrity. Native indices are verified rather
than assumed. A separate freeze fixes every source identity and payload range.

Both CAL/COR products, both coordinate conventions, the original finite mask,
radius-25 apertures and background annuli are retained. Image units are native
ADU, separate from L2 electrons. Every aperture is complete and every COR sum
matches the positive L2 sign. The correction gate is tested before the spatial
gate; neither reaches its original threshold for any representative.

| Representative | DELTA/COR C0 / C1 | COR brightness explained C0 / C1 | COR displacement explained C0 / C1 |
|---|---:|---:|---:|
| TG000801_P0 | -0.166952 / -0.153053 | 3.018% / 2.986% | 77.578% / 77.583% |
| TG000801_P1 | -0.051078 / -0.050873 | 5.083% / 5.070% | 60.385% / 60.387% |
| TG001401_P0 | +0.355280 / +0.365547 | 3.204% / 3.200% | 37.650% / 37.599% |

Column-projected correction ratios also remain below 0.5 in magnitude. The
smearing regressions remain rank deficient and unavailable. The first two
figures show signed structure over the stellar profile in CAL and COR.
The third figure's full-frame color scale is dominated by a feature outside
the source aperture; its aperture COR sums remain positive. These visual
descriptions do not identify causes or replace the frozen displacement gate.
No gate, aperture, center, mask or image selection changes after inspection.

## Bounded retained-data result

LS8AN transfers the unchanged duration-aware residual/noise method to all
three existing contexts, using **zero new archive/source bytes**. All 12
native product/convention cases, 288 held cases and 192 signed controls are
retained. The model includes training-only lag-1/lag-2 covariance, the original
variance shrinkage and exact event/baseline propagation. IID references,
fixed spatial partitions, signed C0/C1 boundary accounting and paired
CAL/DELTA/COR energy identities remain available in the full report.

| Representative | COR residual/reference C0 / C1 | Held controls >= native C0 / C1 | Injected COR brightness flux lost under hypothetical subtraction C0 / C1 |
|---|---:|---:|---:|
| TG000801_P0 | 20.138851 / 19.920447 | 0/24 / 0/24 | 7.41% / 7.01% |
| TG000801_P1 | 0.732455 / 0.741480 | 16/24 / 15/24 | 7.47% / 7.11% |
| TG001401_P0 | 0.832824 / 0.840364 | 15/24 / 15/24 | 13.12% / 12.92% |

TG000801_P0 retains a large mismatch with its local residual/noise model;
none of its 24 held COR controls is as large in either convention. The other
two events do not stand out in this comparison, with 15–16 of 24 held COR
controls at least as large. These dependent counts are not probabilities and
do not establish a noise, astrophysical or artificial origin. All physical
causes remain unassigned. Hypothetical displacement-plus-constant subtraction
loses 7.01–13.12% of injected COR brightness flux across the three contexts
and is not adopted.

Each native result is compared with all 24 single-row sideband targets for
that product and convention. Held targets and their two neighboring rows on
each side are excluded from training; native event/guards never enter it.
These controls share data, have different leverage and are not independent
trials or p-values. The estimated covariance does not calibrate tails,
nonstationarity, longer correlations or template-estimation uncertainty.

All 72 signed known-template, 120 compact and 192 additive checks pass.
The quoted brightness losses describe a hypothetical displacement-plus-constant
subtraction. No subtraction, correction or veto is adopted. The single bounded
study closes regardless of residual size, with all LS8AM labels preserved.

## Verification and publication

All five workflows complete successfully at their public freeze commits.
The 5 transport, 2 stable L2, 9 image and 18 residual tests pass before the
respective acquisitions/native calculations. Audits pass 56,376 L2 comparisons,
803 image-metadata checks, 283,611 numerical / 481,739 exact image checks, and
916,452 numerical / 960,362 exact residual
checks, with zero disagreements. The largest residual-audit error uses
0.000876752721524 of its allowed tolerance.
Original tolerances and independent mathematical functions remain unchanged.
The L2 figure, three image figures and three residual figures were visually
inspected. No scientific rerun or archive retry was needed.

The ten scientific commits add 253 files,
changing or removing no earlier scientific file. Exactly
247 match locally recomputed Git identities.
The publication record identifies any additional local-copy limitations and
the successful workflow verification of the complete retained inputs and outputs.
All code, inputs, receipts, maps, audits, reports, environment, logs and checksums
are public. No qualified SETI candidate, detector, sensitivity or observing
coverage is added.

## Exact next action

Keep the HD 106315 pair and its bounded study closed. Prepare **LS8AO**, the
next independent metadata-first transfer to **rank-14 WASP-103** in the
unchanged reconciled LS8J chronology:

| Chronological visit | Exact product key | Start MJD in ledger | Ledger exposure tuple |
|---|---|---:|---|
| First | CH_PR100013_TG000101_V0300 | 58957.9564832128 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |
| Second | CH_PR100013_TG000102_V0300 | 58971.8300946827 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |

These are the first two of 11 eligible visits; the other nine remain outside
the transfer. Science values remain unopened. Freeze exact keys and a bounded
header preflight; verify identities, schema, row counts and each exposure tuple.
Then separately freeze exact DEFAULT-L2 ranges before values. Transfer the
unchanged scorer and independent audit with the visit's own verified cadence
(60/120/180 seconds if confirmed). Any triggered image follow-up must retain
all signed representatives, verify unique joins and freeze exact payload ranges
before pixels. No HD 106315 diagnostic becomes a new screening cut.

The original 1,000-row census, 452 eligible visits and 107-cohort ordering
remain fixed. The HD 106315 pair's three positive labels stay unresolved and
its bounded study is closed. TESS_260647166's positive, PG1303-114's negative
and PG 1207-033's positive retain their unresolved labels and closed bounded
studies. EC13080-1508, WASP-43, GJ 436 and PG 1245-042 remain closed under
CORRECTION_LINKED; PG 1343-102 remains a closed descriptive null. Other closed
optical studies and M33 HD 3651 are unchanged. Reserved TESS/M43 panels stay
closed. Calibration is NOT_READY and its technical request remains unsent.
Standing research/publication authorization continues; delegation is deferred.

[Scientific interpretation and exact continuation](LS8AN_CONTINUATION.md),
[L2 report and figure](results_ls8al_l2_screen/REPORT.md),
[image report and all three figures](results_ls8am_images/REPORT.md),
[residual report and all three figures](results_ls8an_residuals/REPORT.md),
[publication identities and verification](PUBLICATION_2026-09-22_LS8AL_LS8AN.md).
