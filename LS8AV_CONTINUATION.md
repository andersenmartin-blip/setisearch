# LS8AV — GJ 9404 result and exact continuation

23 September 2026. The predetermined rank-18 pair is **COMPLETE_AUDITED**
and closed as a descriptive null within its eligible windows.

The two visits supplied **145 retained rows and 150 eligible overlapping
windows**, with **zero positive or negative threshold crossings or clusters**.
The unchanged one/two/three-row screen uses 60/120/180-second integrations,
12-row sidebands, two-row guards and +/-8.5 endpoints. Scores are not Gaussian
significances; overlapping windows are not independent trials.

| Visit | Rows | Finite STATUS=0 rows | Eligible 1/2/3-row windows | Positive / negative crossings | Maximum / minimum score |
|---|---:|---:|---:|---:|---:|
| CH_PR100018_TG007301_V0300 | 59 | 59 | 31 / 30 / 29 | 0 / 0 | +1.283802 / -3.268263 |
| CH_PR100018_TG007302_V0300 | 86 | 84 | 22 / 20 / 18 | 0 / 0 | +1.971044 / -2.391310 |

## Exact scope of the null

The first visit has no flagged rows or cadence gaps. Its eligible event-row
union is **14–44**, with 31 distinct rows. The second has flagged rows
**37 and 44**, gaps after **36 and 43**, and eligible event-row unions
**14–22 and 59–71**, with 22 distinct rows. All indices are zero-based;
gaps are adjacent BJD steps outside the unchanged 0.5–1.5-cadence bounds.
These are bookkeeping sets, not qualified observing-coverage claims.

The complete figure retains all finite points, including those excluded by
the original context/status rule. The displayed extrema are:

| Visit | Display extremum | Row | Flux relative to visit median | STATUS | Eligible event windows containing row |
|---|---|---:|---:|---:|---:|
| TG007301 | maximum | 12 | +0.774915% | 0 | 0 |
| TG007301 | minimum | 58 | -0.251547% | 0 | 0 |
| TG007302 | maximum | 45 | +0.666562% | 0 | 0 |
| TG007302 | minimum | 44 | -33.149963% | 1 | 0 |

First-visit row 12 lacks sufficient left context, and row 58 is the last
row. Second-visit row 45 follows a gap and flagged row 44; row 44 itself
fails STATUS=0. In particular, the large displayed dip is retained as an
original flagged point, not counted as a tested negative event. The values
above are display ratios, not fitted local event excesses or significance
estimates. Physical causes are unassigned; no image classifications are given.

This review uses only retained tables and the full saved window ledger.
It changes no eligibility rule, duration, threshold, mask or follow-up
selection. The null applies to **150 eligible windows**, not every retained
variation. No image acquisition or residual study is triggered; TG007303
remains outside the closed pair.

## Verification and publication

Both own-header checks confirm NEXP=1, EXPTIME=TEXPTIME=60 seconds,
PIPE_VER=14.1.2, 18 columns and 138-byte rows. The separate scalar FITS-card
audit verifies complete schemas, source identities, receipts, exposure tuples
and byte boundaries; its reader was frozen before headers. Both workflows
succeed. All five inherited transport tests and both stable L2 tests pass.
The independent scalar science audit passes **1,800 numerical/discrete
comparisons**, with zero disagreements at unchanged relative 2e-8 /
absolute 2e-10 tolerances. The original scientific arithmetic is unchanged.

Exactly **40,320 header bytes**, followed by **20,010 L2 science-table bytes**,
were acquired under separate public freezes. All four URL resolutions succeed
on their first attempt. Zero image bytes, alternate apertures, raw imagettes
or other visits were acquired. All **64 files** in the four-commit scientific
sequence match their public Git identities locally; all **28 header and 22
science manifest entries** match SHA256. The full figure was visually inspected.
No qualified candidate, detector, sensitivity, completeness, population limit
or observing-coverage claim is added.

## Exact next action

Prepare **LS8AW for rank-19 EC14338-1445**, the two eligible visits in its
original unchanged cohort:

| Chronological visit | Exact key | Ledger start MJD | Ledger tuple, requiring own-header checks |
|---|---|---:|---|
| 1 | CH_PR100002_TG006601_V0300 | 58968.3712946721 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |
| 2 | CH_PR100002_TG006602_V0300 | 58976.4199261389 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |

Freeze the exact pair and bounded header reader before new headers. Verify
each identity, full schema, row count and exposure tuple independently,
then separately freeze DEFAULT-L2 source identities and byte ranges before
values. Transfer the unchanged signed one/two/three-row scorer and scalar
audit using verified cadence. EC14338-1445 science values remain unopened.
The original 1,000-row census, 452 eligible visits and 107-cohort order stay fixed.

No GJ 9404 outcome becomes a new cut. Earlier nulls keep their stated eligible
scope; earlier unassessed points, unresolved labels and closed bounded studies
remain unchanged. GJ 581 retains all 14 original labels, including two unresolved
events. Other closed targets and reserved TESS/M43 panels stay closed.
Calibration NOT_READY; technical request UNSENT. Standing research/publication
authorization continues; delegation is deferred.

[L2 report and figure](results_ls8av_l2_screen/REPORT.md) ·
[Independent science audit](results_ls8av_l2_screen/audit.json) ·
[Publication record](PUBLICATION_2026-09-23_LS8AV.md) ·
[Retained scope and release verification](verification_ls8av/release_verification.json).
