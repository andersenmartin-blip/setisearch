# LS8AT — EC 14599-2047 result and exact continuation

23 September 2026. The predetermined rank-16 pair is **COMPLETE_AUDITED** and
closed as a descriptive null within its eligible windows.

The two visits supplied **170 retained rows and 225 eligible overlapping
windows**, with **zero positive or negative threshold crossings or clusters**.
The unchanged one/two/three-row screen uses 60/120/180-second integrations,
12-row sidebands, two-row guards and +/-8.5 endpoints. Scores are not Gaussian
significances and overlapping windows are not independent trials.

| Visit | Rows | Finite STATUS=0 rows | Eligible 1/2/3-row windows | Positive / negative crossings | Maximum / minimum score |
|---|---:|---:|---:|---:|---:|
| CH_PR100002_TG010301_V0300 | 90 | 90 | 61 / 60 / 59 | 0 / 0 | +6.072952 / -3.923636 |
| CH_PR100002_TG010302_V0300 | 80 | 78 | 16 / 15 / 14 | 0 / 0 | +3.717360 / -0.654723 |

## What the null does and does not cover

The complete retained figure shows a large STATUS=0 point at **zero-based
row 86 in TG010301**, with flux **2.1560593305 times the visit median**,
or **115.605933% above it**. This is a display normalization, not an event
excess relative to a fitted local baseline. Only three table rows follow it;
every tested duration requires at least two guard rows and twelve sideband
rows after its event. No eligible event window contains row 86. Its cause
is unassigned, and its significance is not calculated. It receives no image
classification and is not a qualified candidate.

First-visit event rows in eligible windows span 14–74. A late cadence gap
after row 88 also remains in the retained data. In the second visit, flagged
rows 44 and 64 and cadence gaps after rows 43, 44 and 63 restrict eligible
event rows to 14–29. The highest displayed second-visit point is row 19,
about 14.499% above its visit median; it lies in six eligible event windows,
and none of the visit's eligible scores crosses either endpoint.

These coverage observations use only retained tables and the complete saved
window ledger. They do not alter the screen or select a new follow-up. The
null applies to 225 eligible windows, not every visible variation in either
visit. No edge rule is changed; no image acquisition or residual study is
triggered. The third eligible EC 14599-2047 visit remains outside the pair.

## Verification and publication

Both own-header checks confirm NEXP=1, EXPTIME=TEXPTIME=60 seconds,
PIPE_VER=14.1.2, 18 columns and 138-byte rows. The separate scalar FITS-card
audit verifies every schema, source identity, receipt and row boundary.
Both workflows succeed; all five inherited transport tests and both stable
L2 arithmetic tests pass. The independent scalar science audit passes
**2,700 numerical/discrete comparisons**, with zero disagreements at the
unchanged relative 2e-8 / absolute 2e-10 tolerances.

Exactly **40,320 header bytes** and later **23,460 L2 science-table bytes**
were acquired under separate public freezes. All four URL resolutions
succeeded on their first attempt. Zero image bytes, alternate apertures,
raw imagettes or later visits were acquired. All 64 files in the four-commit
scientific sequence match their public Git identities locally; all 28 header
and 22 science manifest entries match their SHA256 hashes. The figure was
visually inspected. No candidate, detector, sensitivity, completeness,
population limit or qualified observing-coverage claim is added.

## Exact next action

Prepare **LS8AU for rank-17 LS IV +09 2**, using its first two eligible visits:

| Chronological visit | Exact key | Ledger start MJD | Ledger tuple, requiring own-header checks |
|---|---|---:|---|
| 1 | CH_PR100002_TG009301_V0300 | 58958.2321678431 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |
| 2 | CH_PR100002_TG009302_V0300 | 58974.0462928716 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |

Freeze the exact pair and bounded header reader before new headers. Verify
each identity, full schema, row count and exposure tuple independently,
then separately freeze DEFAULT-L2 source identities and byte ranges before
values. Transfer the unchanged signed one/two/three-row scorer and scalar
audit using verified cadence. Those science values remain unopened. The
original 1,000-row census, 452 eligible visits and 107-cohort order stay fixed.

No EC 14599-2047 outcome becomes a new screening cut. GJ 581 retains all
14 original labels, including its two unresolved events, and its closed
bounded study; its five later visits stay outside the pair. HD 106315 and
earlier unresolved cases retain their labels and closed studies. Other closed
targets and reserved TESS/M43 panels remain closed. Calibration is NOT_READY
and its technical request UNSENT. Standing research/publication authorization
continues; delegation is deferred.

[L2 report and figure](results_ls8at_l2_screen/REPORT.md) ·
[Independent science audit](results_ls8at_l2_screen/audit.json) ·
[Publication record](PUBLICATION_2026-09-23_LS8AT.md) ·
[Retained scope and release verification](verification_ls8at/release_verification.json).
