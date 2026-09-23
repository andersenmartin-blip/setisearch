# LS8AW — EC14338-1445 result and exact continuation

23 September 2026. The predetermined rank-19 pair is **COMPLETE_AUDITED**
and closed as a descriptive null within **63 eligible windows**. The second
visit has only three eligible windows and large retained positive/negative
values outside eligible event contexts. This is not a null for all its variation.

The two visits supplied **159 retained rows**, with **zero positive or negative
threshold crossings or clusters** in the unchanged screen. One/two/three-row
durations are 60/120/180 seconds, with 12-row sidebands, two-row guards and
+/-8.5 endpoints. Scores are not Gaussian significances; overlapping windows
are not independent trials.

| Visit | Rows | Finite STATUS=0 rows | Eligible 1/2/3-row windows | Positive / negative crossings | Maximum / minimum score |
|---|---:|---:|---:|---:|---:|
| CH_PR100002_TG006601_V0300 | 79 | 78 | 22 / 20 / 18 | 0 / 0 | +3.694572 / -3.158844 |
| CH_PR100002_TG006602_V0300 | 80 | 78 | 2 / 1 / 0 | 0 / 0 | -1.048635 / -1.694216 |

## Exact scope and retained unassessed variation

The first visit has flagged row **48**, a cadence gap after **47**, and eligible
event-row unions **14–33 and 63–64** (22 distinct rows). The second has flagged
rows **30 and 54**, a gap after **29**, and eligible event rows **14–15** only.
It has no eligible three-row window. All indices are zero-based; gaps are
adjacent BJD steps outside the unchanged 0.5–1.5-cadence bounds. These are
bookkeeping sets, not qualified observing-coverage claims.

The complete figure retains all finite points. Its extrema are:

| Visit | Display extremum | Row | Flux / visit median | STATUS | Eligible event windows containing row |
|---|---|---:|---:|---:|---:|
| TG006601 | maximum | 41 | 1.012875227 | 0 | 0 |
| TG006601 | minimum | 28 | 0.990921676 | 0 | 6 |
| TG006602 | maximum | 23 | 265.563670273 | 0 | 0 |
| TG006602 | minimum | 55 | -184.068365878 | 0 | 0 |

First-visit row 41 has a required right context containing the gap/flag at
47/48. Its minimum at row 28 is included in six eligible windows, all below
the signed endpoints. Second-visit row 23 has a required right context
containing the gap/flag at 29/30. Row 55 has required left context containing
flagged row 54. STATUS=0 at an event row alone does not make its context eligible.

The second-visit extrema are large signed values in the retained DEFAULT
table, not tested positive/negative detections. Ratios above use the finite
STATUS=0 visit median only for display; they are not fitted event excesses,
significances or physical flux interpretations. Their causes remain
unassigned and no image classification is given. The plot retains the full
range without clipping these points.

This review uses only retained tables and the complete saved window ledger.
It changes no eligibility rule, mask, duration, threshold or follow-up
selection. The null applies to **63 eligible windows**, not every retained
variation. With no signed crossing, the fixed rule triggers no image
acquisition or residual study. Both original cohort visits are now closed.

## Verification and publication

Both own-header checks confirm NEXP=1, EXPTIME=TEXPTIME=60 seconds,
PIPE_VER=14.1.2, 18 columns and 138-byte rows. The separate scalar FITS-card
audit verifies full schemas, identities, receipts, exposure tuples and byte
boundaries; its source was frozen before headers. Both workflows succeed.
All five inherited transport tests and both stable L2 tests pass. The
independent scalar science audit passes **756 numerical/discrete comparisons**,
with zero disagreements at unchanged relative 2e-8 / absolute 2e-10
tolerances. Scientific arithmetic remains unchanged and hash-pinned.

Exactly **40,320 header bytes**, followed by **21,942 L2 science-table bytes**,
were acquired under separate public freezes. All four URL resolutions succeed
on their first attempt. Zero image bytes, alternate apertures, raw imagettes
or other visits were acquired. All **64 files** in the four-commit scientific
sequence match their public Git identities locally; all **28 header and 22
science manifest entries** match SHA256. The full figure was visually inspected.
No qualified candidate, detector, sensitivity, completeness, population limit
or observing-coverage claim is added.

## Exact next action

Prepare **LS8AX for rank-20 GJ 536**, the first two of five eligible visits in
its original unchanged cohort:

| Chronological visit | Exact key | Ledger start MJD | Ledger EXPTIME / TEXPTIME, seconds |
|---|---|---:|---:|
| 1 | CH_PR100011_TG023501_V0300 | 58959.0929003754 | 40.1699981689453 / 40.1699981689453 |
| 2 | CH_PR100018_TG007801_V0300 | 58976.4945254206 | 40.2000007629395 / 40.2000007629395 |

Both ledger tuples have NEXP=1 and pipeline 14.1.2. These ledger durations
are approximately 40.17 and 40.20 seconds; require independent comparisons
with each product's own headers. Do not inherit a 60-second cadence from
EC14338-1445. Transfer one/two/three-row durations using each verified cadence.
The other visits CH_PR100018_TG021001_V0300, CH_PR100018_TG021002_V0300 and
CH_PR100018_TG021003_V0300 remain outside the selected pair.

Freeze the exact pair and bounded header reader before new headers. Verify
each identity, full schema, row count and exposure tuple independently,
then separately freeze DEFAULT-L2 source identities and byte ranges before
values. Transfer the unchanged signed scorer and independent scalar audit.
GJ 536 science values remain unopened. The original 1,000-row census, 452
eligible visits and 107-cohort order stay fixed.

No EC14338-1445 outcome becomes a new cut. Earlier null scopes, unassessed
points, unresolved labels and closed bounded studies remain unchanged.
GJ 9404's third visit stays outside its closed pair. GJ 581 retains all 14
original labels, including two unresolved events. Other closed targets and
reserved TESS/M43 panels stay closed. Calibration NOT_READY; technical request
UNSENT. Standing research/publication authorization continues; delegation deferred.

[L2 report and figure](results_ls8aw_l2_screen/REPORT.md) ·
[Independent science audit](results_ls8aw_l2_screen/audit.json) ·
[Publication record](PUBLICATION_2026-09-23_LS8AW.md) ·
[Retained scope and release verification](verification_ls8aw/release_verification.json).
