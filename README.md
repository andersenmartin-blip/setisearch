# SETIsearch

A transparent, reproducible search for intermittent narrowband signals across
multiple observing epochs. Exoplanet motion supplies a frequency-drift
hypothesis; it does not establish where an observed signal originated.

**The active programme has returned to ordinary narrowband radio SETI.**
The [26 September–9 October work plan](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/RADIO_TWO_WEEK_PLAN_2026-09-26.md)
targets a bounded search on independent ON/OFF observations, with fixed
controls and complete candidate follow-up.

The **light-sail (LS) research branch is paused** at LS8BD–LS8BE. Its optical
results and 16 unresolved events are preserved; LS8BF remains its saved
restart. Neither a radio trigger nor an optical brightening establishes
artificial origin.

**Start here: [current status and continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PROJECT_STATUS.md).**

The [12 September publication record](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-12.md)
links the complete LS7C/LS7D release and the preserved historical archives.

## Where the project stands

## 26 September: new two-week radio plan; LS paused

The owner has moved the active work from LS back to ordinary radio SETI.
The [new plan runs 26 September–9 October](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/RADIO_TWO_WEEK_PLAN_2026-09-26.md):

- 26–27 September: restore the radio restart point and select one independent
  ON/OFF sequence from a bounded metadata-only shortlist.
- 28–29 September: freeze the primary method and integrated transfer/control
  protocol, then evaluate its fixed gate.
- 30 September–3 October: run a bounded radio pilot if the gate passes.
- 4–7 October: complete the fixed candidate and independent-cadence follow-up.
- 8–9 October: publish the period report and next scientific decision.

M43AI remains a failed qualification: **53/64** injected signals recovered,
**zero losses among 53 reference-union cases**, **1/48** controls leaking,
and **0/128** native nulls with retained members. No model is adopted.
The original M43AF held-out panels remain reserved. The old HD 3651
case and every earlier candidate disposition are preserved.

**Immediate next action is the radio metadata/restart package**, before new
spectral values are opened. No new radio experiment has been evaluated by
issuing this plan. LS8BF is now a saved LS restart, not the active task.
The [LS period review](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/TWO_WEEK_REVIEW_2026-09-26.md)
and full unresolved register remain available. CHEOPS calibration stays
NOT_READY and its technical request UNSENT. Earlier dated next-action
statements below are historical.

## 26 September: two-week review and complete unresolved register

The original 14–27 September plan completed its negative-result branch and
first report early, on **13 September**. LS7I's joint TESS model fails the
requirements; unused-sector qualification remains closed. The new
[period review](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/TWO_WEEK_REVIEW_2026-09-26.md)
consolidates that decision and the separately specified CHEOPS follow-on
through **LS8BD–LS8BE, 24 September**.

The first **23 of 107 fixed cohorts** account for **46 selected visits,
18,865 retained rows and 34,271 eligible overlapping windows**. All **49
signed representatives** completed image follow-up: **24 correction-linked,
nine spatially structured and 16 unresolved**. The unresolved set comprises
**ten positive and six negative events across eight targets**. Each bounded
study is closed; the physical causes remain unassigned. None is a qualified
SETI candidate. These are descriptive counts, not independent-trial counts,
calibrated sensitivity or qualified observing coverage. One selected visit
has no eligible windows and provides no tested null.

[Full cohort table and unresolved register](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_two_week_review_2026-09-26/TABLES.md)
and [reproduction script](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/scripts/review_20260926.py)
verify 80 existing source records, selected-pair identities, count partitions
and complete signed follow-up. This review reads no new archive science
values and reruns no closed fit.

**Next scientific package: LS8BF, rank-24 2MASS J11474440+0048164**,
CH_PR100018_TG007101_V0300 / CH_PR100018_TG007102_V0300, using the existing
[LS8BE continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8BE_CONTINUATION.md).
Own-header verification and separate exact source-range freezes precede new
values. Calibration remains **NOT_READY**; the technical request is **UNSENT**.
Earlier dated next actions below are historical.

## 24 September LS8BD–LS8BE: GJ 494 pair and image follow-up closed

The predetermined rank-23 first pair supplies **148 retained rows and 165
eligible overlapping windows**. Two positive crossings form **one positive
cluster**; no negative window crosses. Its sole representative completes
image follow-up as **CORRECTION_LINKED** under the unchanged two-convention
gate. The unresolved set is empty, so no residual study is triggered.
No qualified SETI candidate, detector, sensitivity or observing coverage is added.

Both visits verify NEXP=1, EXPTIME=TEXPTIME=42 seconds and pipeline 14.1.2.
The fixed one/two/three-row screen retains +/-8.5 endpoints. First-visit row
53 has original score **+17.588819** and local excess **+0.433469%** in one
42-second integration. Scores are not Gaussian significances, and its two
overlapping crossing windows are not independent detections.

Image DELTA/COR ratios are **-3.496853 / -3.694644** (C0/C1), with complete
apertures and positive COR/L2 sign agreement. The correction gate passes
first. Displacement fits also exceed the later spatial thresholds, without
relabeling; smearing fits are rank deficient. The signed aperture sums show
material coupling to delivered processing. This does not identify a unique
physical cause or artificial origin, or exclude underlying source variability.

The original 29-row context contains 58 unique CAL/COR exposure joins.
Second-visit row 13 is **0.366957% above its STATUS=0 visit median** but lacks
an eligible context and remains unassessed. It is not substituted into
follow-up. GJ 494's two later visits stay outside the selected pair.

All four workflows succeed. The 5 transport / 2 L2 / 11 image tests pass;
independent audits pass **1,980 L2 comparisons**, **269 metadata checks** and
**94,537 numerical / 160,581 exact image checks**, with zero disagreements.
All **157 scientific files** are public; 155 match public Git identities
locally. Two large CAL/COR payloads could not be retrieved locally and are
verified by the published independent image audit. Of 129 manifest entries,
127 pass locally and two pass that CI audit. All 68 input-pin checks pass,
and both figures were visually inspected.

**Immediate next action: prepare LS8BF for rank-24 2MASS J11474440+0048164**,
CH_PR100018_TG007101_V0300 / CH_PR100018_TG007102_V0300, both eligible visits.
Freeze bounded headers, verify own identities/schema/exposures, then freeze
exact L2 ranges before values. Use each own verified cadence (ledger 60
seconds); do not inherit 42 seconds. These science values remain unopened.

[Scientific interpretation and exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8BE_CONTINUATION.md),
[L2 report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8bd_l2_screen/REPORT.md),
[complete image report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8be_images/REPORT.md),
[publication and verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-24_LS8BD_LS8BE.md).

Earlier dated next actions below are historical. Active continuation:
LS8BE_CONTINUATION.md; next stage: LS8BF. Prior labels, unassessed points,
closed studies, original census/cohort order and reserved TESS/M43 panels
remain unchanged. Calibration NOT_READY; request UNSENT. Publication
continues under standing authorization; delegation is deferred.

## 24 September LS8BC: GJ 422 audited pair closed

The predetermined rank-22 pair supplied **97 retained rows and 75 eligible
overlapping windows**, with **zero positive or negative threshold crossings
or clusters**. The first visit contributes 30 windows and the second 45.
Both own headers verify NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline
14.1.2. The unchanged one/two/three-row screen retains +/-8.5 endpoints;
its scores are not Gaussian significances. Maximum scores are +3.206120
and +5.502935. No image/residual study is triggered and no qualified SETI
candidate, detector, sensitivity or observing-coverage claim is added.

The null applies only to eligible contexts. The full figure retains the
first visit's large dip at zero-based row 39: **22.091280% below its STATUS=0
visit median**, but **STATUS=1** and no eligible event window. It remains
unassessed, without an assigned cause. Broader displayed variation does not
change the fixed selection. Edge points, flagged contexts and gaps are not
silently counted as tested nulls.

Both workflows succeed at their original freezes. All **five transport and
two stable-arithmetic tests** pass, and the independent audit passes **900
numerical/discrete comparisons with zero disagreements**. All **64 new
scientific file identities**, **50 manifest entries** and **24 input pins**
are verified locally. The complete figure is visually inspected. Exactly
**13,386 L2 science-table bytes** and zero image bytes were acquired.

**Immediate next action: prepare LS8BD for rank-23 GJ 494**, exact first pair
CH_PR100018_TG007401_V0300 / CH_PR100018_TG007402_V0300. Freeze bounded headers,
audit own identities/schema/exposures and then freeze exact L2 ranges before
values. The ledger gives **42 seconds**, NEXP=1 and pipeline 14.1.2; use each
verified cadence and do not inherit 60 seconds. These science values remain
unopened; its two later visits stay outside the pair.

[Scientific interpretation and exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8BC_CONTINUATION.md),
[L2 report and full figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8bc_l2_screen/REPORT.md),
[publication and verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-24_LS8BC.md).

Earlier dated next actions below are historical. Active continuation:
LS8BC_CONTINUATION.md; next stage: LS8BD. Prior labels, unassessed points,
closed studies, original census/cohort order and reserved TESS/M43 panels
remain unchanged. Calibration NOT_READY; request UNSENT. Standing
research/publication authorization continues; delegation is deferred.

## 23 September LS8BA–LS8BB: 2MASS J11285624+1010395 pair closed

The predetermined rank-21 pair supplied **97 retained rows and 90 eligible
overlapping windows**. Six positive crossings form one cluster and three
negative crossings form one cluster. Both signed representatives completed
image follow-up and are **CORRECTION_LINKED** under the unchanged two-convention
gate. No event is unresolved, so no residual study is triggered. The pair is
closed without a qualified candidate, detector, sensitivity or coverage claim.

Both visits independently verify NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline
14.1.2. The first visit has 59 rows and 90 eligible windows; the second has
38 rows and **zero eligible windows, providing no tested null**. The original
one/two/three-row rule and +/-8.5 endpoints remain fixed. Scores are not Gaussian
significances and overlapping windows are not independent trials.

The representatives are adjacent first-visit rows 25 (score **+65.277456**,
local excess **+8.778835%**) and 24 (**-35.043142**, **-4.788958%**). They occur
in each other's original guards and share 28 context rows. Their 58 row
occurrences cover 30 distinct exposures; 116 CAL/COR join occurrences cover
60 distinct product exposures. They are not independent replication. Every
shared CAL/COR/smearing row is verified byte-identical.

DELTA/COR ratios are **-1.485049 / -1.534163** for P0 and
**+9.886640 / +9.536732** for N0 (C0/C1). Both pass the correction gate first.
Displacement fits also exceed the later spatial gate, without changing the
fixed classification. Smearing fits are rank deficient. The maps show broad
processing differences and signed source structure; no unique physical cause
or artificial origin is established, and source variability is not excluded.

The first visit's last point, row 58, is **8.758721% above its STATUS=0 visit
median**, but lacks an eligible complete context and remains unassessed. All
97 points and every eligible window remain preserved. The second visit's gaps
and flagged rows prevent any complete test context. Display variation is not
qualified observing coverage.

All four data-reading/analysis workflows and the retained verification workflow
succeed. The 5 transport / 2 L2 / 11 image tests pass. Independent audits pass
**1,080 L2 comparisons**, **534 metadata checks**, and **189,074 numerical /
321,158 exact image checks**, with zero disagreements. All 175 added
scientific/verification files are public; 171 match public Git identities
locally. Four large compressed CAL/COR files are verified by the independent
image and retained CI audits but were not downloaded locally. Of 143 manifest
entries, 139 are recomputed locally and four pass those published CI checks.
All six payload receipts and all three exact overlap checks pass; all four
figures have been visually reviewed. The optional artifact uploaded, but its
local download returned HTTP 403 and no local ZIP verification is claimed.

**Immediate next action: prepare LS8BC for rank-22 GJ 422**, exact pair
CH_PR100018_TG012201_V0300 / CH_PR100018_TG012202_V0300. These are both eligible
visits in the fixed ledger. NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline
14.1.2 remain subject to their own header checks. Freeze bounded headers,
independently verify identity/schema/exposure, then separately freeze exact
L2 ranges before values. Transfer the unchanged screen and audit. GJ 422
science values remain unopened.

[Scientific interpretation and exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8BB_CONTINUATION.md),
[L2 report](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8ba_l2_screen/REPORT.md),
[complete signed-image report](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8bb_images/REPORT.md),
[readable unchanged-map overview](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/verification_ls8bb_retained/paired_image_review.png),
[publication and verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-23_LS8BA_LS8BB.md).

Earlier dated next actions are historical. Active continuation:
LS8BB_CONTINUATION.md; next stage: LS8BC. The original census and 107-cohort
order, prior labels, unassessed points, closed studies and reserved TESS/M43
panels stay unchanged. GJ 536's P1/P6 keep their unresolved labels and its one
bounded study stays closed. Calibration NOT_READY; technical request UNSENT.
Standing research/publication authorization continues; delegation is deferred.

**LS8AX–LS8AZ GJ 536: complete pair and bounded study, 23 September 2026.**

The predetermined rank-20 pair supplied **4,254 retained rows and 10,215
eligible overlapping windows**. Its 38 positive and five negative crossings
form eight positive clusters and one negative cluster. All nine signed
representatives completed image follow-up: **three CORRECTION_LINKED, four
SPATIALLY_STRUCTURED and two UNRESOLVED_WITHIN_FIXED_SCOPE (P1/P6)**.
Labels describe processing and fits without assigning unique physical causes.
Both visits verify NEXP=1 and pipeline 14.1.2; their own exposure/cadence values
are **40.1699981689453 and 40.2000007629395 seconds**. The unchanged signed
one/two/three-row rule and +/-8.5 endpoints remain fixed. Scores are not
Gaussian significances and windows are not independent trials.

The complete unresolved set received one separately frozen retained-data
study: eight native product/convention cases, 192 held cases and 128 signed
controls, **zero new archive bytes**. P1's COR residual/reference ratios are
**0.257893 / 0.263414**, with **23/24** local controls at least as large in
both center conventions. P6's ratios are **3841.994548 / 3951.598570**, with
**0/24** at least as large. These dependent counts are not p-values.

**P6's very large peak coincides with a broad oblique bright band crossing
the saved subarray and aperture in CAL and COR; broad signed structure remains
after fitting.** This is a severe mismatch with the local model/reference,
not evidence establishing a clean point-source brightening or a SETI signal.
P1's low residual does not prove ordinary noise. Both original unresolved
labels remain. Hypothetical subtraction loses 10.97–11.48% of injected COR
brightness flux and is not adopted. The pair and this single bounded study
are closed without additional GJ 536 tuning or a qualified candidate/detector.

The largest retained point, row 3408, is P6 and received every prescribed
follow-up. A separate first-visit point at row 1977 is approximately 51.10%
above its STATUS=0 visit median but has STATUS=1 and no eligible event window;
it remains retained and unassessed. All rows and eligible intervals are
documented. Display variation is not qualified observing coverage.

All five data-reading/analysis workflows succeed; the initial AX checkout
attempt timed out before archive access and is preserved with its prospective
recovery. The 5 transport / 2 L2 / 11 image / 18 residual tests pass.
Independent audits pass **122,580 L2 comparisons**, **2,393 metadata checks**,
**850,833 numerical / 1,445,201 exact image checks** and **610,586 numerical /
640,224 exact residual checks**, with zero disagreements. All **309 new
scientific files** match public Git identities locally, all 272 manifest
entries pass SHA256, and all 12 figures have been visually inspected.

**Immediate next action: prepare LS8BA for rank-21 2MASS J11285624+1010395**,
CH_PR100018_TG010801_V0300 / CH_PR100018_TG010802_V0300. These are both eligible
visits in the fixed ledger; NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline
14.1.2 remain subject to their own header verification. Freeze bounded headers,
audit identity/schema/exposure, then separately freeze exact L2 ranges before
values. Transfer the unchanged screen and audit. Its science values remain
unopened. GJ 536's three later eligible visits remain outside the closed pair.

[Scientific interpretation and exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8AZ_CONTINUATION.md),
[L2 report](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8ax_l2_screen/REPORT.md),
[complete signed-image report](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8ay_images/REPORT.md),
[bounded residual study](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8az_residuals/REPORT.md),
[publication and verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-23_LS8AX_LS8AZ.md).

Earlier dated next actions are historical. Active continuation:
LS8AZ_CONTINUATION.md; next stage: LS8BA. The original census and 107-cohort
order, prior labels, unassessed points, closed studies and reserved TESS/M43
panels remain unchanged. Calibration NOT_READY; technical request UNSENT.
Standing research/publication authorization continues; delegation is deferred.

**LS8AW EC14338-1445: audited null within 63 eligible windows, 23 September 2026.**

The predetermined rank-19 pair supplied **159 retained rows and 63 eligible
overlapping windows**, with **zero positive or negative threshold crossings
or clusters**. The first visit contributes 60 windows; the second only three
(two one-row, one two-row and no three-row windows). Both verify NEXP=1,
EXPTIME=TEXPTIME=60 seconds and pipeline 14.1.2. The unchanged +/-8.5
scores are not Gaussian significances.

The null applies only to eligible windows. The full figure retains the second
visit's large signed values: maximum row 23 is **265.563670273 times its visit
median**, and minimum row 55 is **-184.068365878 times that median**. Both have
STATUS=0 but are outside eligible event contexts because the required
neighboring rows encounter flags/gaps. Only event rows 14–15 are eligible in
that visit. Indices are zero-based. These display ratios are not fitted event
excesses, significance estimates or physical classifications. Causes remain
unassigned; no eligibility or follow-up rule changes.

Both workflows and all **five transport and two stable L2 tests** pass.
The independent audit passes **756 numerical/discrete comparisons** with
zero disagreements. Scalar header verification, all 50 manifest entries and
all 64 scientific file identities pass; the complete figure was visually
inspected. Exactly **21,942 L2 science bytes** and zero image bytes were
acquired. The pair is complete and closed within its eligible scope.
No image/residual study is triggered; no qualified candidate or detector is added.

**Immediate next action: prepare LS8AX for rank-20 GJ 536**,
CH_PR100011_TG023501_V0300 and CH_PR100018_TG007801_V0300, the first two of
five eligible visits. Freeze the pair and bounded header reader, independently
verify both own identities, schemas, rows and exposures, then separately
freeze exact DEFAULT-L2 ranges before values. Ledger exposures are approximately
**40.17 and 40.20 seconds**, with NEXP=1 and pipeline 14.1.2. Use each verified
cadence; do not inherit 60 seconds. Transfer the unchanged signed screen and
scalar audit. These science values remain unopened; the three later eligible
GJ 536 visits stay outside the selected pair. Earlier labels, unassessed points,
closed studies and reserved TESS/M43 panels are unchanged.

[Scientific interpretation and exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8AW_CONTINUATION.md),
[L2 report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8aw_l2_screen/REPORT.md),
[publication identities and verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-23_LS8AW.md).

Earlier dated next actions below are historical. Active continuation:
LS8AW above; next stage: LS8AX.

**LS8AV GJ 9404: audited null within eligible windows, 23 September 2026.**

The predetermined rank-18 pair supplied **145 retained rows and 150 eligible
overlapping windows**, with **zero positive or negative threshold crossings
or clusters**. The first visit contributes 90 windows and the second 60.
Both verify NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline 14.1.2.
The unchanged +/-8.5 scores are not Gaussian significances.

The null applies to eligible windows. The complete figure retains the
second visit's large dip at zero-based row 44, **33.149963% below its visit
median**, with **STATUS=1**. It fails the original eligibility rule.
Edge points and contexts crossing flagged rows/gaps are also outside the
event search. These display values are not fitted event excesses or
significance estimates. No cause or image classification is assigned,
and no eligibility or follow-up rule is changed.

Both workflows, all **five transport and two stable L2 tests** pass.
The independent audit passes **1,800 numerical/discrete comparisons** with
zero disagreements. Scalar header verification, all 50 manifest entries and
all 64 scientific file identities pass; the complete figure was visually
inspected. Exactly **20,010 L2 science bytes** and zero image bytes were
acquired. The pair is complete and closed as a descriptive null.
No image/residual study is triggered; no qualified candidate or detector is added.

**Immediate next action: prepare LS8AW for rank-19 EC14338-1445**,
CH_PR100002_TG006601_V0300 and CH_PR100002_TG006602_V0300. Freeze the exact
pair and bounded header reader, independently verify each identity, full
schema, rows and exposure tuple, then separately freeze DEFAULT-L2 ranges
before values. Their ledger tuple is NEXP=1, EXPTIME=TEXPTIME=60 s, pipeline
14.1.2. Transfer the unchanged signed screen and scalar audit. These science
values remain unopened; GJ 9404 TG007303 stays outside its closed pair.
Earlier labels, unassessed points, closed studies and reserved panels are unchanged.

[Scientific interpretation and exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8AV_CONTINUATION.md),
[L2 report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8av_l2_screen/REPORT.md),
[publication identities and verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-23_LS8AV.md).

Earlier dated next actions below are historical. Active continuation:
LS8AV above; next stage: LS8AW.

**LS8AU LS IV +09 2: audited null within eligible windows, 23 September 2026.**

The predetermined rank-17 pair supplied **212 retained rows and 123 eligible
overlapping windows**, with **zero positive or negative threshold crossings
or clusters**. The first visit contributes 21 windows and the second 102.
Both verify NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline 14.1.2.
The unchanged +/-8.5 scores are not Gaussian significances.

Four flagged rows per visit and cadence gaps restrict the eligible portions.
The displayed maxima, first-visit row 43 and second-visit row 86, are
**9.674890% and 12.248097% above their visit medians**. Neither lies in an
eligible event window: its required right context encounters flags/gaps.
These are display ratios, not fitted event excesses or significance estimates.
Causes remain unassigned; the null applies to eligible windows, not every
visible variation. No eligibility or follow-up rule is changed.

Both workflows, all **five transport and two stable L2 tests** pass.
The independent audit passes **1,476 numerical/discrete comparisons** with
zero disagreements. Scalar header verification, all 50 manifest entries and
all 64 scientific file identities pass; the figure was visually inspected.
Exactly **29,256 L2 science bytes** and zero image bytes were acquired.
The pair is complete and closed as a descriptive null. No image/residual
follow-up is triggered; no qualified candidate or detector is added.

**Immediate next action: prepare LS8AV for rank-18 GJ 9404**,
CH_PR100018_TG007301_V0300 and CH_PR100018_TG007302_V0300, the first two of
three eligible visits. Freeze exact pair/headers, independently verify each
identity, schema, rows and exposure tuple, then separately freeze DEFAULT-L2
ranges before values. Their ledger tuple is NEXP=1, EXPTIME=TEXPTIME=60 s,
pipeline 14.1.2. Transfer the unchanged signed screen and scalar audit.
These science values remain unopened; TG007303 stays outside the pair.
Earlier labels, closed studies and reserved TESS/M43 panels are unchanged.

[Scientific interpretation and exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8AU_CONTINUATION.md),
[L2 report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8au_l2_screen/REPORT.md),
[publication identities and verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-23_LS8AU.md).

Earlier dated next actions below are historical. Active continuation:
LS8AU above; next stage: LS8AV.

**LS8AT EC 14599-2047: audited null within eligible windows, 23 September 2026.**

The predetermined rank-16 pair supplied **170 retained rows and 225 eligible
overlapping windows**, with **zero positive or negative threshold crossings
or clusters**. The first visit contributes 180 windows and the second 45.
Both verify NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline 14.1.2.
The unchanged +/-8.5 scores are not Gaussian significances.

The full figure retains a large STATUS=0 point at **zero-based row 86 of
TG010301, 115.605933% above the visit median**. With only three following
rows, it lacks the required right context and belongs to no eligible event
window. Its cause is unassigned; it has no image classification. The null
applies to the eligible windows, not every visible variation. No edge rule
or follow-up selection is changed.

Both workflows, all **five transport and two stable L2 tests** pass.
The independent audit passes **2,700 numerical/discrete comparisons** with
zero disagreements. Separate scalar header verification, all 50 manifest
entries and all 64 scientific file identities pass; the figure was visually
inspected. Acquisition is exactly **23,460 L2 science bytes**, with zero
image bytes. The pair is complete and closed as a descriptive null.
No image/residual study is triggered and no qualified candidate or detector
is added.

**Immediate next action: prepare LS8AU for rank-17 LS IV +09 2**,
CH_PR100002_TG009301_V0300 and CH_PR100002_TG009302_V0300. Freeze the exact
pair and bounded headers; independently verify identities, schemas, rows
and exposures, then separately freeze DEFAULT-L2 byte ranges before values.
Transfer the unchanged signed screen and independent scalar audit. Their
ledger tuple is NEXP=1, EXPTIME=TEXPTIME=60 s, pipeline 14.1.2.
These science values remain unopened. EC 14599-2047 TG010303 stays outside
its pair; all earlier closed studies and unresolved labels are unchanged.

[Scientific interpretation and exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8AT_CONTINUATION.md),
[L2 report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8at_l2_screen/REPORT.md),
[publication identities and verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-23_LS8AT.md).

Earlier dated next actions below are historical. Active continuation:
LS8AT above; next stage: LS8AU.

**LS8AQ–LS8AS GJ 581: complete signed follow-up and bounded study closed, 22 September 2026.**

The predetermined rank-15 GJ 581 pair supplied **3,623 rows and 7,869
eligible overlapping windows**. The first visit has 30 positive crossings
in nine clusters and 16 negative crossings in five clusters; the second has
zero signed crossings in its 84 eligible windows. The original +/-8.5 scores
are not Gaussian significances, and the windows are not independent trials.

All 14 representatives completed paired-image follow-up: **nine
CORRECTION_LINKED** (four positive, all five negative), **three
SPATIALLY_STRUCTURED** (P2/P6/P8) and **two UNRESOLVED_WITHIN_FIXED_SCOPE**
(P3/P5). The complete positive IDs are prefixed TG023701_. The two-exposure
negative N1 is included and CORRECTION_LINKED; all other representatives
are one 60-second exposure. These labels describe processing or image fits,
without assigning unique physical causes or artificial origin.

The separately frozen retained-data study includes both unresolved events,
eight native product/convention cases, 192 held cases and 128 signed controls,
with **zero new archive bytes**. Its COR residual/reference ratios are
**1.179547 / 1.161620 for P3** and **3.192676 / 3.078003 for P5** (C0/C1).
For P3, **9/24 controls** are at least as large in both conventions. For P5,
the counts are **1/24 and 2/24**. P3 has several comparable or larger local
controls; P5 is larger than most, with some comparable or larger controls.
These dependent counts are not p-values or calibrated false-alarm rates.
Both causes remain unknown and both original unresolved labels are retained.
Hypothetical displacement-plus-constant subtraction loses **10.41–11.21%**
of injected COR brightness flux and is not adopted.

All five workflows and the **5 transport / 2 L2 / 11 image / 18 residual
tests** pass. Independent audits pass 94,428 L2 comparisons, 3,723 metadata
checks, 1,323,518 numerical / 2,248,091 exact image checks and 610,448
numerical / 640,222 exact residual checks, with zero disagreements at
unchanged tolerances. All 17 figures were visually inspected. The pair and
its single bounded study are complete and closed, preserving all 14 labels.
No new cut, subtraction, qualified candidate, detector, sensitivity or
observing-coverage claim is added.

**Immediate next action: prepare LS8AT for rank-16 EC14599-2047**,
the first two of three eligible visits: CH_PR100002_TG010301_V0300 and
CH_PR100002_TG010302_V0300. Their ledger tuple is NEXP=1,
EXPTIME=TEXPTIME=60 seconds and pipeline 14.1.2. Freeze the exact pair and
bounded header reader, independently verify each identity/schema/row count/
exposure, then separately freeze DEFAULT-L2 byte ranges before values.
Transfer the unchanged signed one/two/three-row scorer and independent audit
using the verified cadence. EC14599-2047 science values remain unopened;
TG010303 and the five later eligible GJ 581 visits remain outside their pairs.
No GJ 581 outcome becomes a new screening cut.

[Scientific interpretation and exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8AS_CONTINUATION.md),
[L2 report](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8aq_l2_screen/REPORT.md),
[complete signed-image report](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8ar_images/REPORT.md),
[bounded residual study](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8as_residuals/REPORT.md),
[publication identities and verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-22_LS8AQ_LS8AS.md).

Earlier dated sections retain their historical next actions. Active continuation:
LS8AS above; next stage: LS8AT.

**LS8AO–LS8AP WASP-103: complete search and correction-linked follow-up, 22 September 2026.**

The predetermined rank-14 CHEOPS pair supplied **565 rows and 804 eligible
overlapping windows**. The first visit has no signed threshold crossing; the
second has three positive crossings in one cluster and no negative crossing.
The sole representative, **TG000102_P0**, is row 274 of
CH_PR100013_TG000102_V0300: one 60-second exposure, L2 score **+13.672258**,
and **+1.301371%** above its local L2 baseline. Scores are not Gaussian sigma.

The complete paired-image follow-up classifies the event **CORRECTION_LINKED**.
Both coordinate conventions have complete apertures and positive COR sums
matching L2. The CAL event-residual aperture sum is approximately -91,100 ADU,
while COR is +18,550 ADU; DELTA=COR-CAL is about +109,650 ADU.
DELTA/COR is **5.906078 / 5.915583**, and the column-projected ratios are
**6.087909 / 6.093572**, above the pre-existing 0.5 correction gate in both
conventions. These are event-residual sums, not negative total stellar flux.
The label establishes substantial coupling to delivered processing; it does
not identify one physical correction component or exclude source variability.

All four workflows and the **5 transport / 2 L2 / 9 image tests** pass.
Independent audits pass **9,648 L2 comparisons**, **269 image-metadata checks**
and **94,537 numerical / 160,581 exact image checks**, with zero disagreements
at unchanged tolerances. Both figures were visually inspected. Acquisition is
exactly **77,970 L2 bytes, 18,560,000 image bytes and 46,400 smearing bytes**.
The WASP-103 pair is complete and closed under its fixed descriptive label;
no residual study is triggered. No qualified SETI candidate, detector,
sensitivity or observing-coverage claim is added.

**Immediate next action: prepare LS8AQ for rank-15 GJ 581**, beginning
with a separate exact-pair/header freeze for CH_PR100011_TG023701_V0300 and
CH_PR100018_TG008301_V0300. They are the first two of seven eligible visits.
Their ledger tuples are NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline
14.1.2; verify each product's own identity, schema, rows and exposures before
separately freezing exact DEFAULT-L2 byte ranges. Transfer the unchanged
one/two/three-row signed screen and independent audit using the verified cadence.
GJ 581 science values remain unopened. The nine later eligible WASP-103 visits
stay outside the closed pair; no event in it becomes a new screening cut.

[Scientific interpretation and exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8AP_CONTINUATION.md),
[L2 report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8ao_l2_screen/REPORT.md),
[paired-image report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8ap_images/REPORT.md),
[publication identities and verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-22_LS8AO_LS8AP.md).

Earlier dated sections below preserve their historical next actions. The
active continuation is LS8AP above; the next stage is LS8AQ.

**LS8AL–LS8AN HD 106315: complete search and bounded follow-up, 22 September 2026.**

The rank-13 CHEOPS pair supplied **2,382 rows and 4,698 eligible overlapping
windows**, with 13 positive crossings in three clusters and no negative
crossing. All three representatives are one 41-second exposure, with L2
scores **+44.503884, +9.691536 and +28.143189**, approximately 1.02026%,
0.24451% and 0.64634% above their respective local L2 baselines.
Scores are not Gaussian significances.

The complete image follow-up leaves all three
**UNRESOLVED_WITHIN_FIXED_SCOPE**. DELTA/COR magnitudes remain below the
original correction gate, and COR displacement explained energy is about
77.58%, 60.39% and 37.60–37.65%, below the original 80% gate in both
coordinate conventions. Physical causes remain unassigned.

The separately frozen retained-data study includes **12 native cases,
288 held cases and 192 signed controls**, using zero new archive bytes.
Its COR residual/reference ratios and local counts are:

- TG000801_P0: 20.138851/19.920447, with 0/24 and 0/24 held controls at least as large.
- TG000801_P1: 0.732455/0.741480, with 16/24 and 15/24 held controls at least as large.
- TG001401_P0: 0.832824/0.840364, with 15/24 and 15/24 held controls at least as large.

TG000801_P0 retains a large mismatch with its local residual/noise model;
none of its 24 held COR controls is as large in either convention. The other
two events do not stand out in this comparison, with 15–16 of 24 held COR
controls at least as large. These dependent counts are not probabilities and
do not establish a noise, astrophysical or artificial origin. All physical
causes remain unassigned. Hypothetical displacement-plus-constant subtraction
loses 7.01–13.12% of injected COR brightness flux across the three contexts
and is not adopted.

All five workflows and the 5 transport / 2 L2 / 9 image / 18 residual tests
pass. Independent audits pass **56,376** L2 comparisons, **803** image-metadata
checks, **283,611 numerical / 481,739 exact** image checks, and
**916,452 numerical / 960,362 exact**
residual checks, with zero disagreements. All seven figures were visually
inspected. Acquisition is exactly **328,716 L2 bytes, 55,680,000 image bytes
and 139,200 smearing bytes**. The bounded HD 106315 study is complete and
closed; all original labels remain unchanged, with no new correction,
screening cut, qualified candidate, detector or observing-coverage claim.

**Immediate next action: prepare LS8AO for rank-14 WASP-103**, beginning
with a separate exact-pair/header freeze for CH_PR100013_TG000101_V0300 and
CH_PR100013_TG000102_V0300. Verify their own NEXP=1, EXPTIME=TEXPTIME=60-second
ledger tuples and pipeline 14.1.2 before freezing exact DEFAULT-L2 ranges.
Transfer the unchanged signed one/two/three-row screen using each visit's
verified cadence. These science values remain unopened. The remaining nine
eligible WASP-103 visits stay outside the prospective pair.

[Scientific interpretation and exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8AN_CONTINUATION.md),
[L2 report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8al_l2_screen/REPORT.md),
[image report and all three figures](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8am_images/REPORT.md),
[residual report and all three figures](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8an_residuals/REPORT.md),
[publication identities and verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-22_LS8AL_LS8AN.md).

Earlier dated sections below preserve their historical next actions. The
active continuation is LS8AN above; the next stage is LS8AO.

**LS8AK PG 1343-102: audited null and closed pair, 22 September 2026.**

The predetermined rank-12 CHEOPS pair supplied **176 rows and 231 eligible
overlapping windows**, with **zero positive or negative threshold crossings
and zero clusters of either sign**. Both visits have verified NEXP=1 and
EXPTIME=TEXPTIME=60 seconds, pipeline 14.1.2. The unchanged screen uses
60/120/180-second events, 12-row sidebands, two-row guards and endpoints
+/-8.5. The pair is **COMPLETE_AUDITED and closed as a descriptive null**.

The null applies to the eligible windows. The second visit contains an early
STATUS=0 point at zero-based row 10, about 34.46% above the visit median.
It lacks the required left context for every tested event duration; it remains
in the retained table and figure. Its cause is unassigned. No edge rule is
changed and no image follow-up is triggered by this null result.

The five inherited transport tests and two stable L2 tests pass. The independent
audit passes **2,772 numerical/discrete comparisons**, with zero disagreements
at the unchanged tolerances. The figure was visually inspected. Exactly
**24,288 L2 science bytes** and no image bytes were acquired. All **62 new
scientific files** were locally verified against their published Git identities;
the four scientific commits change or remove no earlier file. Scores are not
Gaussian significances; no sensitivity, candidate, detector or qualified
observing-coverage claim is added.

**Immediate next action: prepare LS8AL for rank-13 HD 106315**, beginning
with a separate exact-pair/header freeze for CH_PR100041_TG000801_V0300 and
CH_PR100041_TG001401_V0300. Their ledger exposures are NEXP=1 and
EXPTIME=TEXPTIME=41 seconds, pipeline 14.1.2, and still require their own
header verification. Then freeze exact DEFAULT-L2 ranges and transfer the
unchanged one/two/three-row screen using each visit's verified cadence
(41/82/123 seconds if confirmed). Those science values remain unopened.
The two later eligible PG 1343-102 visits stay outside the closed pair.

[Scientific interpretation and exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8AK_CONTINUATION.md),
[L2 report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8ak_l2_screen/REPORT.md),
[publication identities and verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-22_LS8AK.md).

Earlier dated sections below preserve their historical next actions. The
active continuation is LS8AK above; the next stage is LS8AL.

**LS8AI–LS8AJ EC13080-1508 screen and image follow-up complete and closed, 22 September 2026.**

The predetermined rank-11 CHEOPS pair supplied **179 rows and 288 eligible
overlapping windows**, with four negative crossings in one cluster and no positive
crossing. TG005201_N0 is a 60-second exposure at zero-based row 65, score
**-13.17039181262956**, approximately 3.97253% below its local L2 baseline.
Both visits have verified NEXP=1 and 60-second exposures. Scores are not
Gaussian significances.

The fixed image diagnostic classifies the negative event as
**CORRECTION_LINKED**. DELTA/COR is **-3.380189 / -3.413528** in the two
coordinate conventions, with complete apertures and negative COR signs
matching L2. The delivered correction substantially reduces a larger CAL
deficit while leaving a negative COR residual. The label describes material
coupling to processing; the responsible component and physical cause remain
unassigned. No new correction or screening cut is adopted.

The L2 audit passes **3,456 comparisons**. Before pixels, image metadata
passes **58 unique joins and 269 exact checks**. All nine inherited image
tests pass; the independent image audit passes **94,537 numerical
comparisons and 160,581 exact checks**, zero disagreements. Both figures
were visually inspected. Exactly 24,702 L2 bytes, 18,560,000 image bytes and
46,400 smearing bytes were acquired. The publication record gives the exact
workflow and local verification scope. No qualified SETI candidate, detector
or observing coverage is added.

**Immediate next action: prepare LS8AK for rank-12 PG 1343-102**, starting
with a separate exact-pair/header freeze for CH_PR100002_TG008701_V0300 and
CH_PR100002_TG008702_V0300. Verify the NEXP=1/60-second ledger exposures,
then freeze exact DEFAULT-L2 ranges and transfer the unchanged signed screen.
Those science values remain unopened; the cohort's two later eligible visits
stay outside scope. The EC13080-1508 pair is closed, with its third visit
TG005203 outside the completed transfer.


The earlier TESS_260647166 positive remains unresolved within its fixed scope.
[Scientific interpretation and continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8AJ_CONTINUATION.md),
[L2 report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8ai_l2_screen/REPORT.md),
[image report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8aj_images/REPORT.md),
[publication identities and verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-22_LS8AI_LS8AJ.md).

Earlier dated sections below retain their historical next steps. The active
continuation is LS8AJ above.

**22 September LS8AF–LS8AH: PG 1207-033 screen and bounded follow-up complete and closed.**

The rank-10 CHEOPS pair supplied **153 rows and 165 eligible overlapping
windows**, with six positive crossings in one cluster and no negative crossing.
TG000901_P0 is one 60-second exposure at zero-based row 60, score
**+141.1054591837304**, approximately 43.12658% above its local L2 baseline.
Both visits have verified NEXP=1 and 60-second exposures. Scores are not
Gaussian significances.

The fixed image diagnostic leaves the positive
**UNRESOLVED_WITHIN_FIXED_SCOPE**. DELTA/COR is 0.218211/0.314435 and COR
displacement explained energy 11.40%/16.23%, below the original gates in
both conventions. The figure shows an extended stripe crossing the upper
aperture edge. Its physical cause remains unassigned; the specific original
displacement-fit gate is not replaced by a visual morphology label.

The separately frozen retained-data study finds COR residual/reference energy
**278.663206/124.118239**, with **0/24 held controls as large** in each
convention. The fixed outer ring contains **98.39%/97.84%** of weighted
residual energy. These results describe a large, edge-dominated mismatch
with the local sideband model, not a calibrated probability or SETI detection.
Exact boundary accounting gives COR C1 minus C0 **-46,369.987482 ADU**.
Hypothetical displacement subtraction loses **42.99–43.53%** of injected
COR brightness flux and is not adopted. All four native cases, 96 held cases
and 64 signed controls are retained. The bounded study is closed and its
original unresolved label preserved, with no new cut, qualified candidate,
detector or coverage claim.

All five workflows and the 5 transport / 2 L2 / 9 image / 18 residual tests
pass. Independent audits pass 1,980 L2 comparisons, 269 image-metadata checks,
94,537 numerical / 160,581 exact image checks and 305,224 numerical /
320,118 exact residual checks. All three figures were visually inspected.
Exact acquisition was 21,114 L2 bytes and 18,560,000 image plus 46,400
smearing bytes; the residual study used no new archive bytes.

**Immediate next action: prepare LS8AI for rank-11 EC13080-1508**, starting
with a separate exact-pair/header freeze for CH_PR100002_TG005201_V0300 and
CH_PR100002_TG005202_V0300. Verify the NEXP=1/60-second ledger exposures,
then freeze exact DEFAULT-L2 ranges and transfer the unchanged signed screen.
Those science values remain unopened. The third eligible visit,
CH_PR100002_TG005203_V0300, stays outside this two-visit transfer.

[Scientific interpretation and exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8AH_CONTINUATION.md),
[L2 report](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8af_l2_screen/REPORT.md),
[image report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8ag_images/REPORT.md),
[residual report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8ah_residuals/REPORT.md),
[publication identities and verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-22_LS8AF_LS8AH.md).

All earlier dated next actions are historical. The active continuation is
LS8AH above. The prior TESS_260647166 positive and PG1303-114 negative retain
their unresolved labels and closed bounded studies. Other closed studies
and reserved TESS/M43 panels remain closed. Calibration is NOT_READY and
its request unsent. Standing publication authorization continues;
delegation remains deferred.

**22 September LS8AC–LS8AE: PG1303-114 screen and bounded follow-up complete and closed.**

The rank-9 CHEOPS pair supplied **165 rows and 222 eligible overlapping
windows**, with **zero positive crossings** and two negative crossings in
one cluster. TG006402_N0 is one 60-second exposure at zero-based row 21,
score **-10.531570808271077**, approximately 3.00335% below its local L2
baseline. Both visits have verified NEXP=1 and 60-second exposures.
Scores are not Gaussian significances.

The complete signed image follow-up leaves the negative
**UNRESOLVED_WITHIN_FIXED_SCOPE**. DELTA/COR is 0.304773/0.312012 and COR
displacement explained energy is 58.94%/58.68%, below the original gates in
both conventions. The subsequent separately frozen retained-data study finds
COR residual/reference energy **0.878666/0.876726**, with **20/24 and 19/24**
held single-row controls at least as large. The residual is not exceptional
in this fixed local comparison; these dependent counts are not p-values and
do not identify its cause. The original label remains unchanged.

Hypothetical displacement subtraction loses **38.17–38.23%** of injected
COR brightness flux and is not adopted. All four native cases, 96 held cases
and 64 signed controls are retained. The bounded study is closed without
a new correction, cut, qualified SETI candidate, detector or coverage claim.

All five workflows and the 5 transport / 2 L2 / 9 image / 18 residual tests
pass. The independent audits pass 2,664 L2 comparisons, 269 image-metadata
checks, 94,537 numerical / 160,581 exact image checks, then 305,356 numerical /
320,126 exact residual checks. All three figures were visually inspected.
Exactly 22,770 L2 bytes and 18,560,000 image plus 46,400 smearing bytes were
acquired; the residual study used no new archive bytes.

**Immediate next action: prepare LS8AF for rank-10 PG 1207-033**, starting
with a separate exact-pair/header freeze for CH_PR100002_TG000901_V0300 and
CH_PR100002_TG000902_V0300. Verify the NEXP=1/60-second ledger exposures,
then freeze exact DEFAULT-L2 ranges and transfer the unchanged signed screen.
Those science values remain unopened. PG1303-114's three later eligible
visits remain outside scope.

[Scientific interpretation and exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8AE_CONTINUATION.md),
[L2 report](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8ac_l2_screen/REPORT.md),
[image report](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8ad_images/REPORT.md),
[residual report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8ae_residuals/REPORT.md),
[publication identities and verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-22_LS8AC_LS8AE.md).

All earlier dated next actions below are historical. The active continuation
is LS8AE above. The prior TESS_260647166 positive remains unresolved and its
bounded study closed. Other closed studies and reserved TESS/M43 data remain
closed. Calibration is NOT_READY and its request unsent. Standing publication
authorization continues; delegation remains deferred.

**LS8AA–LS8AB WASP-43 screen and image follow-up complete and closed, 21 September 2026.**

The predetermined rank-8 CHEOPS pair supplied **271 rows and 294 eligible
overlapping windows**, with one positive crossing/cluster and no negative
crossing. TG007801_P0 is a 60-second exposure at zero-based row 62, score
**+9.486349813911296**, approximately 0.78% above its local L2 baseline.
Both visits have verified NEXP=1 and 60-second exposures. Scores are not
Gaussian significances.

The fixed image diagnostic classifies the positive event as
**CORRECTION_LINKED**. DELTA/COR is **-0.713546 / -2.797082** in the two
coordinate conventions, with complete apertures and positive COR signs
matching L2. The delivered correction reduces the positive aperture residual;
the amount is sensitive to the coordinate convention, while both satisfy the
original closure gate. The label describes material coupling to processing;
the responsible component and physical cause remain unassigned.

The L2 audit passes **3,528 comparisons**. Before pixels, image metadata
passes **58 unique joins and 269 exact checks**. All nine inherited image
tests pass; the independent image audit passes **94,537 numerical
comparisons and 160,581 exact checks**, zero disagreements. Both figures
were visually inspected. Exactly 37,398 L2 bytes, 18,560,000 image bytes and
46,400 smearing bytes were acquired. The publication record gives the exact
workflow and local verification scope. No qualified SETI candidate, detector
or observing coverage is added.

**Immediate next action: prepare LS8AC for rank-9 PG1303-114**, starting
with a separate exact-pair/header freeze for CH_PR100002_TG006401_V0300 and
CH_PR100002_TG006402_V0300. Verify the NEXP=1/60-second ledger exposures,
then freeze exact DEFAULT-L2 ranges and transfer the unchanged signed screen.
Those science values remain unopened; the cohort's three later eligible
visits stay outside scope. The WASP-43 pair is closed.


The earlier TESS_260647166 positive remains unresolved within its fixed scope.
[Scientific interpretation and continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8AB_CONTINUATION.md),
[L2 report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8aa_l2_screen/REPORT.md),
[image report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8ab_images/REPORT.md),
[publication identities and verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-21_LS8AA_LS8AB.md).

Earlier dated sections below retain their historical next steps. The active
continuation is LS8AB above.

**LS8Y–LS8Z PG 1245-042 screen and image follow-up complete and closed, 21 September 2026.**
The predetermined rank-7 pair supplied **164 rows and 228 eligible overlapping
windows**, with one negative cluster and no positive crossing. Its representative
is one 60-second exposure, original score -18.490171716816285, not Gaussian sigma.

The fixed image diagnostic classifies the negative event as
**CORRECTION_LINKED**. DELTA/COR is **+1.688786 / +1.717959** in the two
coordinate conventions, with complete apertures and negative COR signs
matching L2. The delivered correction reverses a positive CAL aperture
residual into a negative COR residual. The label describes material coupling
to processing; the responsible component and physical cause remain unassigned.

Both scientific audits pass: **2,736 L2 comparisons**, then **94,537
image numerical comparisons and 160,581 exact checks**, with no
disagreements. All nine inherited image tests pass before pixels. Both report
figures were visually inspected. Data, receipts, logs and checksums are public;
the publication record gives the exact workflow and local verification scope.
No qualified SETI candidate, detector or observing coverage is added.

**Immediate next action: prepare LS8AA for rank-8 WASP-43**, beginning
with a separate exact-pair/header freeze for CH_PR100016_TG007801_V0300 and
CH_PR100016_TG007802_V0300. Verify their NEXP=1/60-second ledger exposures,
then freeze exact DEFAULT-L2 ranges and transfer the unchanged signed screen.
Those science values remain unopened. The PG 1245-042 pair is closed.

The earlier TESS_260647166 positive remains unresolved within its fixed scope.
[Scientific interpretation and continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8Z_CONTINUATION.md),
[L2 report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8y_l2_screen/REPORT.md),
[image report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8z_images/REPORT.md),
[publication identities and verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-21_LS8Y_LS8Z.md).

Earlier dated sections below retain their historical next steps. The active
continuation is LS8Z above.

**LS8W–LS8X GJ 436 screen and image follow-up completed and closed, 21 September 2026.**
The unchanged rank-6 pair supplied **640 rows and 936 eligible overlapping
windows**, with one positive 60-second event and no negative threshold
crossing. Its original L2 score is +9.634235209975396, not Gaussian sigma.

The separately frozen image diagnostic classifies the event as
**CORRECTION_LINKED**. DELTA/COR is **-2.089268 / -2.001642** in the two
coordinate conventions, passing the original correction gate. The negative
DELTA reduces a larger positive CAL residual; the label does not establish
one physical cause or artificial origin. No qualified SETI candidate,
detector or observing coverage is added.

Both scientific audits pass: **11,232 L2 comparisons**, then **94,537 image
numerical comparisons and 160,581 exact checks**, with no disagreements.
All nine inherited image tests pass before pixels. Both report figures were
visually inspected. All data, receipts, logs and checksums are public;
the publication record states the exact workflow and local verification scope.

**Current next action: LS8Y, rank-7 PG 1245-042.** Separately freeze header
checks for CH_PR100002_TG008601_V0300 and CH_PR100002_TG008602_V0300, verify
their NEXP=1/60-second ledger exposures, then freeze exact DEFAULT-L2 ranges
and transfer the unchanged signed screen. Those science values remain unopened.
The earlier TESS_260647166 positive remains unresolved within its fixed scope.
[Scientific interpretation and continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8X_CONTINUATION.md),
[L2 report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8w_l2_screen/REPORT.md),
[image report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8x_images/REPORT.md),
[publication identities and verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-21_LS8W_LS8X.md).

Earlier dated sections below preserve their historical next steps. The active
continuation is LS8X above.

**LS8V EC 12578-2107 screen completed and closed, 21 September 2026.**
The unchanged rank-5 pair supplied **174 rows and 201 eligible overlapping
windows**, with **no positive or negative threshold crossing**. Both visits
have verified 60-second integrations; tested event durations are 60/120/180
seconds. No image follow-up is triggered and no qualified SETI candidate,
detector or observing coverage is claimed.

Both known-answer tests and **2,412 independent numerical/discrete comparisons**
pass without disagreement. All 20 result files and 26 metadata files were
checksum verified, and the figure was visually inspected. A pre-table TLS
failure is preserved; its separately frozen transport-only recovery succeeded
with unchanged data scope, arithmetic and thresholds. Exactly 24,012 science
bytes were acquired. Scores are not Gaussian significances; the empty screen
does not establish completeness or short-glint sensitivity.

**Current next action: LS8W, rank-6 GJ 436.** Separately freeze metadata/header
checks for CH_PR100041_TG000302_V0300 and CH_PR100041_TG001301_V0300, verify
their ledger NEXP=1/60-second exposures, then freeze exact DEFAULT-L2 ranges
and transfer the unchanged screen. Its science values remain unopened.
The earlier TESS_260647166 positive remains unresolved within its fixed scope.
[Scientific interpretation and continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8V_CONTINUATION.md),
[audited report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8v_l2_recovered/REPORT.md),
[preserved failure and recovery](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8V_TRANSPORT_RECOVERY.md),
[publication identities](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-21_LS8V.md).

Earlier dated next steps below are historical; the active queue is the LS8V
continuation above.

**LS8U TESS_260647166 residual/noise study completed and closed,
20 September 2026.** The positive remains **UNRESOLVED_WITHIN_FIXED_SCOPE**;
the negative remains **SPATIALLY_STRUCTURED**. There is no qualified SETI
candidate or new detector or observing-coverage qualification.

The positive's COR residual/reference energy is **3.77–3.80**, with **1/24**
duration-matched local controls at least as large in both conventions. Its
weighted residual is spread across many pixels: the top ten account for
**6.47–7.03%**. The negative's ratio is **0.705–0.723**, with **6/8** controls
at least as large. These are dependent, model-based descriptions, not
calibrated significances or identified physical causes. The original scores,
labels, masks and thresholds remain unchanged.

A hypothetical displacement correction would lose **12.79–13.09%** of an
injected brightness pulse's flux in the positive context, so no correction
or veto is adopted. All **18 tests**, **583,488 numerical comparisons and
625,868 exact checks** pass. Both contexts, **128 held cases and 128 signed
controls** are retained. No new archive bytes were acquired; all 22 result
files were checksum verified and both residual figures visually inspected.

**Current next action:** separately freeze the metadata/header check for
**rank-5 EC 12578-2107**, then its exact DEFAULT-L2 intervals and unchanged
screen. Its selected pair remains CH_PR100002_TG008901_V0300 and
CH_PR100002_TG008902_V0300; both ledger exposures are 60 seconds. Science
values remain unopened. The bounded TESS_260647166 study is closed.
[Scientific interpretation and exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8U_CONTINUATION.md),
[report and both figures](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8u_residuals/REPORT.md),
[frozen method](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8U_RESIDUAL_NOISE_PROTOCOL.md),
[publication identities](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-20_LS8U.md).

Earlier checkpoints below retain historical next steps; the active work
queue is the LS8U continuation above.

**LS8S–LS8T TESS_260647166 screen and both image follow-ups completed,
20 September 2026.** This CHEOPS target's selected pair supplied **1,747
rows and 2,004 eligible overlapping windows**, retaining **one positive
and one negative cluster**. Six overlapping positive crossings describe
one event, not six detections.

The negative is **SPATIALLY_STRUCTURED**: the displacement model explains
**92.96%** of its COR event-map energy in both coordinate conventions.
The positive remains **UNRESOLVED_WITHIN_FIXED_SCOPE**: displacement explains
**75.76–75.78%**, below the original 80% requirement, and pure brightness
explains about **2.7%**. Neither correction gate passes. Its L2 score
**+45.46035 is not a Gaussian significance**; no qualified SETI candidate,
new detector or observing coverage is claimed.

All data joins and apertures are complete. Both L2 tests, **24,048 L2 checks**,
nine image tests and **189,074 numerical plus 321,180 exact image checks**
pass without disagreements. Both image figures and the L2 figure were
checksum verified and visually inspected. The original signs and labels
remain unchanged.

**Current next action:** separately freeze one bounded residual/noise study
using the two saved contexts, with duration-matched controls and signed
signal-protection tests. The positive spans one 49-second exposure; the
negative spans three 42-second exposures and needs an explicit temporal
noise treatment. No new pixels or visits are required. Rank-5 EC 12578-2107
remains a later independent transfer.
[Scientific interpretation and continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8T_CONTINUATION.md),
[image report and both figures](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8t_images/REPORT.md),
[L2 report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8s_l2_screen/REPORT.md),
[publication identities](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-20_LS8S_LS8T.md).

Earlier checkpoints below retain historical next steps; the active work
queue is the LS8T continuation above.

**LS8Q–LS8R HD 136352 screen and image follow-up completed and closed,
20 September 2026.** The unchanged rank-3 pair supplied **1,125 rows and
1,923 eligible overlapping windows**, with **no positive threshold crossing**.
Thirteen negative crossings formed three clusters; all received the
prospectively frozen CAL/COR image diagnostic.

**All three are CORRECTION_LINKED in both coordinate conventions.** Direct
signed DELTA/COR aperture-sum ratios are **0.55856–0.81381**, above the
unchanged 0.5 gate. This identifies coupling to delivered processing; it
does not identify a unique physical cause or exclude source variability.
There is no qualified SETI candidate, new detector or coverage qualification.

Both L2 tests, all **23,076 L2 comparisons**, nine image tests and **283,611
numerical plus 481,748 exact image checks** pass without disagreements.
All three image figures and the L2 figure were checksum verified and
visually inspected. Each L2 row stacks 26 exposures into approximately
44.2 seconds; the individual 1.7-second exposures are not resolved.

**Current next action:** separately freeze the metadata/header preflight
for **rank-4 TESS_260647166's CHEOPS pair**, then its exact DEFAULT-L2 ranges
and unchanged screen. Its ledger integrations are 42 and 49 seconds; each
visit needs its own exposure verification. The HD 136352 pair is closed.
[Scientific interpretation and continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8R_CONTINUATION.md),
[image report and three figures](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8r_images/REPORT.md),
[L2 report and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8q_l2_screen/REPORT.md),
[publication identities](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-20_LS8Q_LS8R.md).

Earlier checkpoints below retain historical next steps; the active work
queue is the LS8R continuation above.

**LS8P GJ 1132 retained-data study completed and closed, 20 September 2026.**
All five original negative controls remain unresolved, and LS8N still has
**no positive threshold crossing in 699 eligible windows**.

The fixed three-exposure covariance model raises estimated COR variance by
about **37–67%** relative to IID propagation. Residual/reference energy ratios
are **1.43–2.02**, with **6/8 or 8/8** held blocks at least as large. These
dependent comparisons are descriptive, not detection probabilities.
Exact accounting of the two existing apertures' boundary pixels explains
the coordinate-sensitive correction-budget sign change. No unique physical
cause is assigned and no mask or historical threshold is changed.

Hypothetical displacement subtraction loses **24–38% of injected brightness
flux** and is not adopted. All **160 held cases and 320 signed controls** are
retained. Seventeen pre-analysis tests, one serialization regression and
**1,400,704 numerical comparisons plus 1,529,059 exact checks** pass.
The initial audit-output serialization failure is preserved; a separately
frozen representation-only repair completed the same audit without rerunning
the producer or changing scientific arithmetic.

**Current next action:** separately freeze the **rank-3 HD 136352**
metadata/header check and independent transfer of the unchanged DEFAULT-L2
screen to its already selected chronological pair. No qualified candidate,
detector or new observing coverage is claimed.
[Scientific interpretation and continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8P_CONTINUATION.md),
[verified report and five figures](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8p_verified/REPORT.md),
[preserved failure and repair](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8P_AUDIT_RECOVERY.md),
[publication identities](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-20_LS8P.md).

Earlier checkpoints below retain historical next steps; the active work
queue is the LS8P continuation above.

**LS8N–LS8O GJ 1132 screen and all image controls completed, 20 September 2026.**
The unchanged rank-2 pair supplied **615 L2 rows and 699 eligible overlapping
windows**. There were **no positive threshold crossings**; 12 negative
crossings formed **five control clusters**.

All five received a separately frozen CAL/COR image follow-up. They remain
**UNRESOLVED_WITHIN_FIXED_SCOPE** with complete image coverage and matching
signs. One displacement fit explains **79.74861% / 83.79823%** in the two
coordinate conventions, missing the requirement of at least 80% in both.
Another control's correction ratio changes sign between conventions.
These are model limitations, with no qualified SETI candidate or new detector
or coverage qualification.

The L2 audit passes **8,388 comparisons**. Nine image tests and **472,685
numerical comparisons plus 802,983 exact checks** pass with zero disagreements.
Every signed outcome, source range, image context and audit is retained.

**Current next action:** freeze one bounded study using the five saved
contexts to examine variability of three-exposure sums, residual structure
and the boundary difference between the existing coordinate conventions.
The original gates and labels remain fixed. Rank-3 HD 136352 stays next for
a later, separately frozen independent transfer.
[Scientific interpretation and exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8O_CONTINUATION.md),
[image report and maps](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8o_images/REPORT.md),
[L2 screen and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8n_l2_screen/REPORT.md),
[publication identities](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-20_LS8N_LS8O.md).

Earlier checkpoints below retain their historical next steps; the active
work queue is the LS8O continuation above.

**LS8M bounded WASP-189 residual/noise study completed, 20 September 2026.**
The smaller positive's residual is concentrated in a few pixels and is
comparable in weighted energy to local sideband variability: its
residual/reference ratio is **1.101–1.106**, and **7–8 of 24** held-sideband
controls are at least as large. Ten pixels account for **48.4–48.5%** of
weighted residual energy.

This does not prove that the entire selected excursion is ordinary noise or
identify its physical cause. Its original **UNRESOLVED_WITHIN_FIXED_SCOPE**
label remains; the other two events retain their previous labels. There is
**no qualified SETI candidate** and no new detector or coverage qualification.

Eight pre-analysis tests and the independent audit pass: **790,128 numerical
comparisons and 911,228 exact checks**, with zero disagreements. All 288
held-sideband cases and 192 signed injection cases are retained. No new native
source bytes were acquired. A tested displacement subtraction would lose
about 8% of an injected brightness pulse's flux, so no new correction or veto
is adopted.

**Current next action:** close this bounded WASP-189 follow-up and separately
freeze a metadata-first transfer to **rank-2 GJ 1132**, preserving the unchanged
DEFAULT-L2 screen and both signs.
[Scientific conclusion and exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8M_CONTINUATION.md),
[full report and residual maps](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8m_residuals/REPORT.md),
[publication identities](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-20_LS8M.md).

Earlier checkpoints below retain their historical next steps; the current
work queue is the LS8M continuation above.

**LS8K–LS8L WASP-189 screening and image follow-up completed, 20 September 2026.**
The new chronology-selected pair supplied **1,604 L2 rows and 2,603 eligible
windows**, retaining two positive clusters and one negative control. The
separately frozen CAL/COR image study followed all three representatives:

- The stronger positive is **SPATIALLY_STRUCTURED**: displacement explains
  **88.331%** of the event-map energy.
- The negative control is **CORRECTION_LINKED**, with absolute DELTA/COR
  **0.92196–0.94371**.
- The smaller positive remains **UNRESOLVED_WITHIN_FIXED_SCOPE**: neither
  closure gate passes, while the pure-brightness template explains only about
  **5.66%** of its event-map energy.

There is **no qualified SETI candidate**. The labels do not uniquely establish
physical cause, and the L2 scores are not Gaussian significances. Seven image
tests, **283,611 numerical comparisons and 481,739 exact checks** pass with
zero disagreements. The L2 audit separately passes all 31,236 comparisons.

The LS8J metadata reconciliation also retained all 452 complete fresh product
inventories and verified unchanged 107-cohort order. It preserves the original
run's missing full-response limitation explicitly.

**Current next action:** a separately frozen residual/noise diagnostic on the
three already retained image contexts, with both signs and signal-protection
controls. No new native data is opened by that continuation.
[Result and three image maps](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8l_images/REPORT.md),
[L2 screen and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8k_l2_screen/REPORT.md),
[exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8L_CONTINUATION.md).

Earlier checkpoints and their historical next steps follow below.

**LS8E–LS8I independent CHEOPS host sequence completed, 20 September 2026.**
The prospectively frozen post-55-Cnc sequence evaluated GJ 876, GJ 514,
GJ 849 and GJ 649 with the unchanged DEFAULT-L2 cadence screen. GJ 876,
GJ 514 and GJ 649 are clean two-visit null results. The frozen host ledger is
now exhausted under its unchanged requirement of at least two eligible visits.

GJ 849 produced one audited positive L2 cluster, representative score
**23.470080** at one 42-second row. Its separately frozen paired CAL/COR image
diagnostic acquired **18,560,000 image bytes + 46,400 smearing bytes** and
classified the event as **SPATIALLY_STRUCTURED**, not correction-linked:
|DELTA/COR| is only **0.03536 / 0.03276**, while the fixed displacement model
explains **87.801% / 87.800%** of COR event-map energy in C0/C1. The image audit
passes 94,537 numerical and 160,581 exact checks with zero disagreements.
This is a morphological label, not a unique physical-cause determination or a
SETI candidate.

The final GJ 649 screen contains **381 eligible windows with zero signed
threshold crossings** and passes 4,572 independent comparisons.
[LS8H image result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8h_images/REPORT.md),
[LS8I survey closure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8i_l2_screen/REPORT.md).

**Next:** begin a new metadata-only independent population/dataset selection.
Freeze its population, target-name authority, product requirements, visit
multiplicity and deterministic ranking before opening new science values.
[Exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8I_CONTINUATION.md).

**LS8D: all eight retained CHEOPS excursions are correction-linked, 20 September 2026.**
The paired CAL/COR study was frozen before image access, after 482 unique
exposure joins were verified. It then acquired exactly **154,240,000 image
bytes** plus **385,600 smearing-row bytes** for the eight fixed LS8B/LS8C
representatives.

All seven positive excursions and the single negative control satisfy the same
predeclared **CORRECTION_LINKED** rule in both coordinate conventions. For the
positive events, absolute CAL→COR DELTA/COR is **1.331–2.431**; for the negative
control it is **0.857–0.884**. This establishes material coupling to the
delivered correction chain, not a unique physical cause and not artificial or
astrophysical origin.

Seven synthetic tests passed before image access. The independent audit passes
**756,296 numerical comparisons and 1,284,709 exact checks** with zero
disagreements. The original LS8B audit FAIL remains preserved, no raw imagette
was opened and no detector is qualified.
[Full report and CAL/COR/DELTA maps](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8d_images/REPORT.md).

**Next:** close these eight 55 Cnc branches without widening. Select the next
independent optical dataset/product under a new metadata-only freeze before
reading new light-curve values or image pixels.
[Exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8D_CONTINUATION.md).

**LS8C: all seven positive CHEOPS excursions share a smearing/roll pattern, 19 September 2026.**
The frozen diagnosis of all eight LS8B representatives uses only saved L2
tables. Every positive representative coincides with a large smearing-column
residual (**205,662–293,495 electrons**) at mean roll angles of **16.39–20.42
degrees**. The negative control does not share this pattern. All 112 field
diagnoses and 56 separate sideband-only couplings are retained.

The shared pattern motivates image/correction follow-up. Sideband smearing
fits predict between **−0.42 and 31.78 times** the observed positive brightness
residuals, so they cannot supply a reliable event correction or establish a
unique cause. All eight remain **L2_ONLY_UNRESOLVED**. No SETI candidate,
detector qualification or qualified observing coverage is added.

Six synthetic tests pass, followed by an independent audit with **11,635
numerical comparisons and 1,009 exact checks**. The original LS8B audit FAIL
remains preserved. No new archive science bytes or image pixels were opened.
[Complete report and context plots](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8c_auxiliary/REPORT.md).

**Next:** prepare one bounded CAL/COR image-and-correction study of all eight
fixed representatives. Establish exact product metadata and exposure joins,
then freeze byte/row/pixel scope and stopping rules before image access.
[Exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8C_CONTINUATION.md).

**LS8B: four held-out CHEOPS visits evaluated.**
The unchanged DEFAULT-aperture screen covers **4,754 rows and 7,917 eligible
windows**. It finds **seven positive clusters and one negative control cluster**;
per-visit positive/negative counts are 3/1, 2/0, 2/0 and 0/0. These are L2
excursions, not SETI candidates or calibrated Gaussian significances.

The frozen audit fails two tiny near-zero excess comparisons. A 60-decimal
reference verifies every screening decision, and a separately frozen
flux-centered implementation passes **31,668** numerical comparisons at the
original tolerances, with zero changed decisions. The original audit failure
and original values remain preserved; this is an arithmetic repair on closed
data, not detector qualification.
[Result and four-visit figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8b_l2_suite/REPORT.md),
[numerical review](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8B_NUMERICAL_REVIEW.md).

The preceding LS8A held-out visit had zero positive clusters and four negative
threshold windows. Both fixed transfer results remain separate and unchanged.
[LS8A result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8a_l2_transfer/REPORT.md).

**LS7Z closes both prospectively screened CHEOPS L2 excursions.**
The LS7X DEFAULT-aperture pilot produced two threshold crossings. LS7Y linked
the first to the CAL→COR correction. For the second, LS7Z used only already
published bytes and found that a fixed displacement-template model explains
about **92.5%** of the event-map squared energy, versus about **0.11%** for a
brightness-profile model. The independent LS7Z audit passes 103,218
comparisons. Following the predeclared stopping rule, both branches are now
closed without widening to other apertures, rows, visits or raw imagettes.
[LS7Z result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7z_morphology/REPORT.md).

The integrated work in the [14–27 September plan](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/TWO_WEEK_PLAN_2026-09-14.md)
is now complete, including the negative-result decision branch. The calendar
dates were work estimates; execution proceeded during active sessions.

**Separate raw-imagette track: resolve the remaining physical input contract.**
The official University of Vienna CHEOPS-IASW repository and ESA documentation
now narrow the onboard stacking question: ordinary window `coadd` is described
as pixel-by-pixel coaddition, while the exact `gcoadd` definition is delegated
to CHEOPS-UVIE-INST-TN-001 issue 2.0. A second bounded public-source pass did
not recover that technical note, a flight-relevant `gcoadd` implementation,
or the required native reference-validity rules. The public-source route is
therefore **incomplete**, and the raw-imagette calibration study remains blocked.
[LS7W follow-up](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7W_PUBLIC_SOURCE_FOLLOWUP.md).

Matching-version public CHEOPS schemas now also fix the required flat/dark/
bad-map/LUT product structures and units, while the pinned public PIPE code
provides an independent comparison for Teff interpolation, detector slicing
and validity-start selection. PIPE's calibration order differs from the
official DRP architecture, so it is **not** adopted as a DRP 14.0.1 proxy.

The invariant parts of the next 30/60/100-second positive-pulse experiment
are predeclared before target access in both a
[human-readable preparation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7W_NATIVE_STUDY_PREPARATION.md)
and a
[machine-readable manifest](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7W_NATIVE_STUDY_PREPARATION.json).
Its state is **PREPARED_NOT_FROZEN — TARGET PIXELS CLOSED**.

A complete
[technical request](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/CHEOPS_CALIBRATION_REQUEST.md)
and [exact-version manifest](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/CHEOPS_REQUIRED_INPUTS.json)
are prepared and narrowed to the remaining operator/reference questions. The
message is **unsent**; no reply is pending. LS7V is the earlier calibration-log
checkpoint; the newer L2 transfer results above do not resolve the raw-image gate.

**LS7V CHEOPS calibration-log reconciliation completed, 15 September 2026.**
The actual reduction log explains the difference investigated in LS7U:
**563.43 ADU/frame bias and 7.13 ADU/frame noise are chosen defaults**, whose
binary32 representations exactly match the saved CAL/COR values. The log also
shows that the spatial bias-frame correction was skipped. Its reference is
not needed to reproduce an unapplied correction.

Source identities, native-header comparisons and fresh offline reproduction
pass. The applied dark map, exact gain/coaddition/offline operator and remaining
spatial inputs still need resolution before the combined native image study.
**Input remains NOT_READY; no source trial or new observing coverage is added.**
[Findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7V_CALIBRATION_RECONCILIATION.md),
[evidence](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification/results_ls7v_reduction_log),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7V_CONTINUATION.md).

**Earlier LS7U CHEOPS electronic-reference measurements completed, 15 September 2026.**
The fixed virtual prescan now directly measures **562.089864 ADU/readout bias**
and **7.118046 ADU/readout effective noise**. Its bias differs from CAL beyond
the descriptive sampling interval. A separately specified exploratory check
executes PIPE's original estimator on its actual blank-reference input and
gives **562.071429 / 7.024590 ADU/readout**. CAL's noise is **1.500584% higher**,
so this alternative input does not reproduce the calibration numbers.

All **1,036,800 electronic values**, independent scalar checks and clean offline
reproduction pass. The retained arrays contain electronic reference values;
target-image bytes remain zero. The gain/coaddition and exact spatial-reference
contract still needs completion before a prospective native image study.
**Input remains NOT_READY; no candidate or qualified coverage is added.**
[Findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7U_ELECTRONICS_FINDINGS.md),
[evidence](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification/results_ls7u_prescan),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7U_CONTINUATION.md).

**Earlier LS7T CHEOPS native-HK contract audit completed, 15 September 2026.**
The actual 1,140-row instrument table reveals that the pinned PIPE gain reader
uses a separate voltage field in its temperature term. Running the unchanged
function gives about **−0.57027%** in scale relative to the centered-temperature
diagnostic. The earlier 8.129% comparison used a different conditional input.
Onboard nonlinearity is disabled, so its missing conversion coefficients are
not by themselves a calibration obstacle.

The primary sources disagree on the gain-temperature sign; gcoadd, offline
calibration and exact references still need resolving. Byte/scalar checks and
clean offline reproduction pass. **Native input remains NOT_READY:** no image
search, candidate or additional qualified coverage is added.
[Findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7T_CALIBRATION_CONTRACT.md),
[evidence](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification/results_ls7t_contract),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7T_CONTINUATION.md).

**Earlier LS7S CHEOPS calibration-input audit completed, 15 September 2026.**
The original gain reference is verified and **14/15 exact calibration versions**
are located. The saved 6,048 exposure rows have missing onboard gain/bias
values; physical calibration and coaddition assumptions still need resolving.
A conditional temperature-offset comparison exposes an absolute-scale
ambiguity, with no calibration adopted. The numerical audit passes.

The remaining reference download was blocked in this session. **Native input
is NOT_READY:** no image search, new candidate or qualified coverage is added.
Next finish the physical calibration contract and one combined protected
pulse/control/native study on the same visit.
[Findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7S_CALIBRATION_FINDINGS.md),
[evidence](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification/results_ls7s_calibration),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7S_CONTINUATION.md).

**LS7R CHEOPS input and temporal assessment completed, 14 September 2026.**
The selected public 55 Cnc visit provides **3,024 raw imagettes**, **432
matching subarrays** and metadata for **6,048 individual exposures**. Bounded
byte-range access works; only headers and metadata were acquired.

The small images combine two 2.2-second exposures and arrive about every
**4.449 seconds**. A timestamp-only 30-second pulse retains full peak in these
images versus **48–96%** in the larger stacked images on the sampled onset
grid. Four long observation gaps remain explicit. This is a temporal response
calculation, not noisy recovery or a detection.

LS7S subsequently audited the named inputs; the combined native pixel
calibration, signal-protection and nuisance-control study remains pending. No image pixels
were inspected, no detector was qualified and no search coverage was added.
[Findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7R_CHEOPS_INPUT.md),
[evidence](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification/results_ls7r_metadata),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7R_CONTINUATION.md).

**LS7Q HiPERCAM metadata assessment completed, 14 September 2026.**
A bounded inspection saves 100 catalogue rows, six run/calibration headers and
the observatory QC log. A public XO-2b run contains 11,152 stored frames with
header-derived repeat intervals of **0.652–13.040 seconds**, depending on the
channel. Its timing arithmetic agrees with the official instrument reader.

The native pilot is **not ready**: raw-file access is unresolved and the
identified bias/flat set requires a documented match to the science readout
and filters. No science pixels were opened, no new candidate was assessed and
no observing coverage was added. Next establish the actual input package, with
CHEOPS retained as a secondary metadata option.
[Read the findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7Q_OPTICAL_METADATA.md),
[saved evidence](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification/results_ls7q_metadata),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7Q_CONTINUATION.md).

**LS7P reconstruction and publication completed.** The explicit
reconstruction is now public as **83/83 release files** on
`m43-support-qualification`, including retained raw extracts, NPZ outputs,
audit records, provenance inventories, report and reproduction code. The
independent audit passes **1,496,872 numerical comparisons**, and
**48,114/48,120** centroid rows meet the fixed binary32 reconstruction bound.
This is reproducible replacement evidence, not recovery of the earlier missing
original run. It does not qualify the reference-star motion input or add new
observing coverage.
[Result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7p_response/REPORT.md),
[verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7p_reconstruction/README.md),
[release inventory](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/release_inventory.json).

**LS7O reference availability completed, 14 September 2026: the input contract fails.**
Twelve simultaneous 20-second products from seven reference stars provide
**48,120 selected rows**, acquired in **4,812,000 bytes**. All cadence and
spacecraft-time joins agree exactly, centroids and positive quoted errors are
finite, and the reference pixel masks are disjoint from the science target.

The fixed requirement for six QUALITY=0 references throughout every sideband
blocks **all 420 windows**. Event-only availability is **72/210 and 101/210**,
but complete-sideband availability is zero in both sectors. Consequently,
**zero new corrections and zero pulse transfers were measured**. The 840 model
slots and 12,600 pulse slots are blocked ledger entries, not measured failures.

The independent input audit passes **384,960 exact raw-field comparisons**;
916 numerical comparisons preserve the static baseline. A separate raw-byte
audit confirms every quality count and all 420 window attributions.
LS7J and LS7N remain separate measured response failures.

Next establish pixel-level quality, cosmic-ray handling and centroid response
for these fixed references before any bounded pixel acquisition and new
comparison. Matching pixel products are identified; their time-series contents
remain unread. No flags are waived, stars removed or unused sectors opened.
[Findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7O_FINDINGS.md),
[audited result](https://github.com/andersenmartin-blip/setisearch/blob/c03a07e174af1c49376f5a8e26a8983cd73bcbd0/results_ls7o_response/REPORT.md),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7O_CONTINUATION.md).

**LS7N calibrated native response completed, 14 September 2026: the joint test failed.**
The fixed cadence-level PRF plus protected-plane model evaluated the same
**420 native windows** under both declared column origins (**840 paired model
rows**). Combined residual energy rises **12.14–12.36% in sector 29** and
**12.37–12.49% in sector 32**. Only **0/10 and 2/10** background aggregates
improve, against six required. All predictions are available.

All **12,600 downstream pulse-response cases pass**: maximum nominal
distortion is **0.015354%**, and maximum calibration-entry stress distortion is
**0.226796%**. The independent audit passes **108,604 numerical comparisons**.
Correction size exceeds its alignment benefit in both sectors; the same failure
holds at both column origins. No detector or candidate is adopted.

This closes the exact cadence response without gain/sign/lag/profile retuning.
LS7O subsequently established simultaneous reference products, but its fixed
all-six/all-sideband quality rule blocks every window. The pixel/quality
measurement contract remains the next need, as described above. Unused TESS
and M43 panels remain closed.
[Findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7N_FINDINGS.md),
[audited result](https://github.com/andersenmartin-blip/setisearch/blob/3354f09bf34af32a3fbf6ed68af77076f9f3d604/results_ls7n_response/REPORT.md),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7N_CONTINUATION.md).

**LS7M calibrated PRF and exposure operator completed, 14 September 2026.**
Ten known-answer tests, all **4,050 phase reconstructions** and **144 fixed
calibration cases** pass. An independent original-MATLAB/SciPy/Simpson audit
finds at most **1.39e-16** absolute flux discrepancy. Every original PRF image
and uncertainty array matches its mission FITS export exactly.

Both declared column origins are retained; they change modeled pixel responses
by up to **0.7946%** over this panel. Finite stamp coverage is explicit, and a
synthetic 30 ms pulse has **10–15 ms** of live exposure across the declared
readout placements. This stage verified numerical response arithmetic.
LS7N subsequently fixed and evaluated the cadence-level native comparison
reported above. Instantaneous quaternion mapping, exact timing and upstream
target dependence remain limitations. No detector is adopted or unused panel
opened.
[Findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7M_FINDINGS.md),
[audited result](https://github.com/andersenmartin-blip/setisearch/blob/81406913ff12cc7ce91c9c9caf3d25aa758f568f/results_ls7m_response/REPORT.md),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7M_CONTINUATION.md).

**LS7L engineering and PRF phase inputs completed, 14 September 2026.**
All **81,200 camera-4 orientation rows** and **30,594 thermal rows** are
restored on the same twenty closed contexts. Every one of the **8,020** saved
cadence bins has exactly ten orientation samples. The independent raw-byte
audit passes.

The fifty mission PRFs yield **4,050 phase images** with at most **0.405205%**
footprint flux deficit. Engineering calendar checks support the TDB numeric
time scale. Thermal gaps reach seven minutes. LS7M subsequently completed the
relative-coordinate and exposure arithmetic above. Absolute detector origin,
exact mission timing and upstream target dependence remain physical-model
limits. No detector is adopted or unused sector opened.
[Findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7L_FINDINGS.md),
[audited inputs](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7l_inputs/REPORT.md),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7L_CONTINUATION.md).

**LS7K instrument-response inputs completed, 14 September 2026.**
All **50 original mission PRFs**, with their uncertainty images, and **8,020
timing rows** from the same twenty closed contexts are restored and audited.
Every reused motion value agrees with the original extraction. Four matching
engineering products were listed at this checkpoint; LS7L has now completed
their bounded extraction above.

LS7K established a mission-calibrated pixel-response family. LS7L completed the
engineering and phase-normalization inputs; LS7M subsequently verified the
numerical PRF/exposure family above. The physical observable-to-pixel mapping,
exact fast-cadence motion uncertainty and target exclusion remain unestablished. No detector is adopted or unused sector opened.
[Findings and response contract](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7K_INPUT_FINDINGS.md),
[audited input packet](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7k_inputs/REPORT.md),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7K_CONTINUATION.md).

**LS7J auxiliary-information study completed, 14 September 2026: the fixed correction failed.**
All **420 native windows and 9,480 digital response rows** are complete and
independently audited on the same twenty closed-sector contexts. The combined
motion/outside-aperture correction increases residual energy by **45.74% and
34.51%**, with no improved background aggregate. All pulse-protection
requirements pass, including broadened full-stamp profiles with at most
**0.365% distortion**. All required motion values are available.

The component comparison and exact energy accounting identify the fixed motion
response as the limitation: its squared size exceeds its limited alignment
with the measured fluctuation. The plane alone improves only five of ten
backgrounds per sector. No detector is adopted or unused sector opened.

LS7K subsequently completed the requested calibration/provenance input
assessment, reported above. It establishes an available mission PRF family
while retaining explicit coordinate, estimator-timing and target-dependence
questions. No gain, sign, lag or profile retry is appended to LS7J.
[Result and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7j_auxiliary/REPORT.md),
[limitation analysis](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7J_LIMITATIONS.md),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7J_CONTINUATION.md).

**LS7I protected background model completed, 13 September 2026: the joint test failed.**
The one fixed model and static comparison cover **7,080 digital cases**:
6,720 preserved historical cases plus a separately labeled 360-case sector-32
shape supplement. All **420** fixed native-prediction windows and the independent
audit are complete. Six of twelve signal cells and two of sixty control cells
fail; neither sector improves the aggregate native prediction requirement.
Weak nominal recovery is only **18/40** in sector 29 and **7/40** in sector 32,
against 36/40 required. All pulse-protection checks pass, but the new statistic
rejects too many weak signals. No detector is adopted or unused sector opened.

Every additional signal loss is published. The limitation analysis identifies
source-score losses and much broader conditional error calibration on sector
32. The proposed auxiliary-information direction was subsequently tested in
the separately frozen LS7J study reported above. LS7I's original negative
result remains unchanged; no cut, bank or ridge retry was appended.
[Result and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7i_background/REPORT.md),
[limitation analysis](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7I_LIMITATIONS.md),
[consolidated plan result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/TWO_WEEK_REPORT_2026-09-14.md).

The prerequisite input restoration also passed: both closed-sector packages
reproduce all **6,720 historical recipes** and **300 old training vectors**
exactly across twenty backgrounds, including independent sector-32 raw-FITS
checks. [Input report](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7i_inputs/REPORT.md).

**LS7H TESS morphology diagnosis completed, 13 September 2026.**
All 3,540 saved LS7G trials and the independent numerical audit are complete.
For all 24 accepted controls in the four failed cells, removing the known
native background reverses the spatial comparison; this uses injection truth
and cannot serve as a native-event veto. Adding 245 shape templates reduces
those acceptances **24 → 9**, but loses **10** recovered stellar trial rows.
Two control cells still fail, while all six signal-recovery cells pass.
LS7I subsequently tested one protected background model on both closed
sectors, with the result reported above. No detector or candidate is adopted.
[Read the result and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7h_morphology/REPORT.md).

**LS7G fixed TESS transfer completed, 13 September 2026.**
All 3,540 trials on already closed sector 29 completed and pass the independent
numerical audit. The fixed development rule recovers **37/40, 40/40 and 40/40**
nominal pulses and meets all displaced-signal recovery requirements. The joint
test still fails: four control cells accept too many weak or medium-strength
artifacts, especially crosses and triangles. No detector is adopted or candidate
promoted. [Read the result and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7g_transfer/REPORT.md).

**LS7F TESS separation study completed, 13 September 2026.**
Using all 3,180 saved LS7E trials, the expanded nuisance model rejects all 960
matched control cases at the old margin but also loses more stellar tests.
An exhaustive comparison finds jointly passing development settings only at
**negative margins**, where a nuisance fit may be better than the stellar fit.
These settings are not adopted or independently validated. All six tests and
the independent numerical audit pass. LS7G subsequently completed the fixed
transfer on already closed sector 29; its outcome is recorded above. [Read the result and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7f_separation/REPORT.md).

**LS7E TESS model comparison completed, 12 September 2026.**
Across 3,180 paired development trials on closed sector 32, the combined model
raises nominal recovery from 3/40, 12/40, 27/40 to **18/40, 37/40, 40/40** and
rejects all 120 original compact pixel controls. Weak-signal recovery and
broader-contamination rejection still fail; no detector is adopted or candidate
promoted. The independent numerical audit passes. [Read the result and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7e_joint/REPORT.md).

**LS7D TESS noise diagnosis completed, 12 September 2026.**
The diagonal pixel model misses strong cancellation between pixel fluctuations.
All 120 original trial-noise ratios reproduce across 34 windows in ten shared
backgrounds; eight analytical tests and the covariance audit pass. This is
method development with no new candidate or adopted detector. LS7E subsequently
combined covariance, residual handling and broader nuisance controls on the
closed data. [Read the result and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7d_noise/REPORT.md).

**LS7C TESS qualification completed, 12 September 2026: the joint test failed.**
The noise-aware pixel method completed 1,460 digital trials over 18.78 searchable
cadence-days of L 98-59 sector 32. All planned matched-strength tests reach the
screening threshold, but stellar recovery is insufficient and 16/120 compact
pixel controls are accepted. All 325 native excursions fail spatial screening;
no LS candidate is promoted. LS7D and LS7E subsequently examined covariance
and residual contamination on these closed data.
[Read the reviewed result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7c_tess/REVIEW.md).

**M43AI native evaluation is complete:** The fixed combined rule failed the predeclared same-sequence native challenge. It recovered 53/64 signal cases and lost 0/53 signals required by the reference union. 1/48 controls and 0/128 native null cases had surviving members.
The model remains unadopted; all inputs use one observing sequence.
[Read the complete result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_43AI_NATIVE_VALIDATION_RESULT.md).

M43AF's frozen joint response rule failed qualification: none of the 1,156
tested boundaries met all requirements. The complete **502-record study and
its lossless archive are now public**: 69 parts restore 508 original files,
verified byte for byte. The original M43AF held-out panels remain unopened.
[Read the complete study](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_43AF_RESPONSE_STUDY_RESULT.md).

There is no new M43AF astronomical candidate or adopted detector. The earlier
**M33 HD 3651 follow-up at 1424.934238382 MHz remains unresolved**, pending an
independent observing cadence. It is not a detection or technosignature claim.

| Read or do | Entry point |
|---|---|
| Continue the active work | [Current project status](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PROJECT_STATUS.md) |
| Inspect current TESS work | [LS7O availability findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7O_FINDINGS.md), [LS7O audited report](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7o_response/REPORT.md), [LS7N native findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7N_FINDINGS.md), [LS7N audited result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7n_response/REPORT.md), [LS7M PRF/exposure findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7M_FINDINGS.md), [LS7M audited benchmark](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7m_response/REPORT.md), [LS7L engineering/phase findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7L_FINDINGS.md), [LS7L audited inputs](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7l_inputs/REPORT.md), [LS7K input findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7K_INPUT_FINDINGS.md), [LS7K audited inputs](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7k_inputs/REPORT.md), [LS7J auxiliary result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7j_auxiliary/REPORT.md), [LS7J limitations](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7J_LIMITATIONS.md), [LS7I joint background result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7i_background/REPORT.md), [LS7I limitations](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7I_LIMITATIONS.md), [LS7H morphology diagnosis](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7h_morphology/REPORT.md), [LS7G sector-29 transfer](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7g_transfer/REPORT.md), [LS7F separation study](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7f_separation/REPORT.md), [LS7E combined development](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7e_joint/REPORT.md), [LS7D noise diagnosis](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7d_noise/REPORT.md), [LS7C reviewed result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7c_tess/REVIEW.md), [frozen protocol](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7C_TESS_PROTOCOL.md), and [previous LS7B result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7b_tess/REVIEW.md) |
| Inspect the latest native evaluation | [M43AI result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_43AI_NATIVE_VALIDATION_RESULT.md) |
| Inspect the separate historical TESS development | [LS7C sector 29 archive: 1,300 retrospective trials](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/archives/ls7c_sector29_development/README.md) |
| Understand the failed training rule | [M43AF training result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_43AF_TRAINING_RESULT.md) |
| Inspect the frozen scientific method | [M43AF executable protocol](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_43AF_EXECUTABLE_PROTOCOL.md) |
| Restore existing M43AF evidence | [M43AF continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/M43AF_CURRENT_CONTINUATION.md) |
| Follow the earlier open case | [M33 candidate investigation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_33_CANDIDATE_INVESTIGATION.md) |
| Understand the long-term plan | [Project direction](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PROJECT_DIRECTION.md) |
| Revisit earlier radio LS work | [LS6 result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS6_TRAPPIST1_RESULT.md) and [LS6A result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS6A_SCAN_END_RESULT.md) |
| Read the full milestone history | [Archived README before cleanup](https://github.com/andersenmartin-blip/setisearch/blob/60bad761f4aa6eebeeef367f7a4123b80fd33e44/README.md) |

## Working with the repository

Current scientific development is on
[`m43-support-qualification`](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification).
The main branch provides this overview and earlier pipeline code.
Use the current status to select the correct branch and evidence archive.

Closed evaluations are restored from their sealed records. For exact M43AF
archive restoration, use the recorded Python 3.12.14 / zlib 1.3.2 and frozen
dependencies. Historical reproduction commands apply to their named milestones;
they are not commands to restart the current work.

The archive link preserves the previous full README and all its milestone
summaries. Its “current” labels and “next step” instructions describe their
historical dates. The current work queue is maintained in PROJECT_STATUS.md.
