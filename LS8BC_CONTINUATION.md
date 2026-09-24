# LS8BC — GJ 422 audited pair and exact continuation

24 September 2026. The predetermined rank-22 pair is **complete and closed**.
The unchanged screen finds **no positive or negative threshold crossings**
in **75 eligible overlapping windows** from 97 retained rows. No image or
residual study is triggered. No qualified SETI candidate or detector is added.

## Measured result and limited scope

| Exact visit | Retained rows | STATUS=0 finite | Eligible windows, 1 / 2 / 3 rows | Positive / negative crossings | Score range |
|---|---:|---:|---:|---:|---:|
| CH_PR100018_TG012201_V0300 | 48 | 47 | 11 / 10 / 9 | 0 / 0 | +0.269636 to +3.206120 |
| CH_PR100018_TG012202_V0300 | 49 | 48 | 16 / 15 / 14 | 0 / 0 | +0.341989 to +5.502935 |

Both own headers independently verify NEXP=1, EXPTIME=TEXPTIME=60 seconds
and pipeline 14.1.2. Each uses its verified cadence. The fixed durations are
one/two/three rows (60/120/180 seconds), with 12-row sidebands, two guards per
side and endpoints +/-8.5. Eligibility requires finite BJD/FLUX/FLUXERR,
positive error, STATUS=0 throughout and adjacent BJD steps within 0.5–1.5
own cadence. Gaps are not bridged; EVENT remains metadata. Baselines use
sidebands only. Visit medians enter display normalization, never the scorer.

The scores are not Gaussian significances or false-alarm probabilities, and
the windows are not independent trials. The null concerns only these eligible
contexts under the fixed short-event screen. The plotted broader variation
is retained; this result does not establish that GJ 422 is constant.

The [full report and figure](results_ls8bc_l2_screen/REPORT.md) retain all 97
rows and every eligible score. Scope bookkeeping from the retained tables
and ledgers is in [eligible_scope.json](verification_ls8bc/eligible_scope.json).
Indices below are zero-based:

- First visit: eligible event rows are 14–24 inclusive. Its maximum, row 17,
  is 1.006822091 times the STATUS=0 visit median and belongs to six eligible
  windows. Its minimum, row 39, is **0.779087205 times that median**, or
  **22.091280% below it**, but has STATUS=1 and no eligible event window.
  There is also a cadence gap after row 39. This large dip remains preserved
  and unassessed by the screen; no cause is assigned.
- Second visit: eligible event rows are 19–34 inclusive. Row 4 has STATUS=1
  and a following cadence gap. The maximum, row 22, is 1.006671520 times its
  STATUS=0 visit median and belongs to six eligible windows. Its minimum,
  row 10, has STATUS=0 but no eligible context and is 0.979240998 times the
  median. It also remains outside the tested event scope.

These ratios describe the display and are not fitted event excesses. The
event-row unions are bookkeeping, not qualified observing coverage. No
unassessed point is substituted into the signed follow-up list. Both original
cluster lists are empty, so no CAL/COR images or additional visits are opened.

## Verification and publication

Both workflows succeed at their original public freezes. All five transport
tests and both stable-arithmetic tests pass before the corresponding archive
reads. The separately frozen scalar FITS-card auditor verifies both complete
18-column/138-byte-row schemas, identities, exposure tuples, receipts and
table boundaries. The independent L2 scalar audit passes **900 comparisons
with zero disagreements**, retaining relative 2e-8 / absolute 2e-10 tolerances.
Both signed cluster sets and per-duration eligibility counts are verified.

All **64 added scientific files** match their public Git blob identities
locally. All **50 manifest entries** and **24 input pins** pass SHA256.
The complete figure was visually inspected. Both header requests and both
L2 URL resolutions succeed on their first attempt; no scientific failure or
result-dependent rerun occurred. Archive acquisition totals are **40,320
header bytes**, **13,386 science-table bytes**, and **zero image bytes**.
Retained-data release verification adds zero archive bytes or scientific fits.

[Publication record](PUBLICATION_2026-09-24_LS8BC.md),
[reproducible release verifier](scripts/ls8bc_release_verify.py), and
[machine-readable verification](verification_ls8bc/release_verification.json).

## Exact next action

**Prepare LS8BD for rank-23 GJ 494**, next in the original reconciled order.
Select only the chronological first two of its four eligible visits:

| Visit | Exact key | Ledger start MJD | Ledger tuple, subject to own header verification |
|---|---|---:|---|
| 1 | CH_PR100018_TG007401_V0300 | 58972.950558862 | NEXP=1; EXPTIME=TEXPTIME=42 s; pipeline 14.1.2 |
| 2 | CH_PR100018_TG007402_V0300 | 58982.7820436582 | NEXP=1; EXPTIME=TEXPTIME=42 s; pipeline 14.1.2 |

Freeze exact pair, bounded header reader and independent auditor before
archive access. Independently verify each identity, full schema, row count,
exposure tuple and receipt. Separately freeze exact DEFAULT-L2 identities and
table ranges before values. Transfer the unchanged signed screen and scalar
audit with each own verified cadence; **do not inherit 60 seconds**. Every
selected signed representative receives the fixed follow-up. GJ 494's science
values remain unopened, and TG007403/TG007404 remain outside the selected pair.

The original 1,000-row census, 452 eligible visits and 107-cohort order remain
unchanged. The historical LS8J discarded-full-response limitation stays
documented alongside the preserved later reconciliation. Earlier labels,
unassessed points, closed studies and reserved TESS/M43 panels are unchanged.
No sensitivity, completeness, population limit or qualified observing coverage
is claimed. Calibration NOT_READY; technical request UNSENT. Standing
research/publication authorization applies; delegation is deferred.
