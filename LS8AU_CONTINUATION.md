# LS8AU — LS IV +09 2 result and exact continuation

23 September 2026. The predetermined rank-17 pair is **COMPLETE_AUDITED**
and closed as a descriptive null within its eligible windows.

The two visits supplied **212 retained rows and 123 eligible overlapping
windows**, with **zero positive or negative threshold crossings or clusters**.
The unchanged one/two/three-row screen uses 60/120/180-second integrations,
12-row sidebands, two-row guards and +/-8.5 endpoints. Scores are not Gaussian
significances; overlapping windows are not independent trials.

| Visit | Rows | Finite STATUS=0 rows | Eligible 1/2/3-row windows | Positive / negative crossings | Maximum / minimum score |
|---|---:|---:|---:|---:|---:|
| CH_PR100002_TG009301_V0300 | 98 | 94 | 9 / 7 / 5 | 0 / 0 | -0.321999 / -2.883077 |
| CH_PR100002_TG009302_V0300 | 114 | 110 | 36 / 34 / 32 | 0 / 0 | +4.428672 / -2.853957 |

## Exact scope of the null

The complete retained figure shows broad changes and gaps. The fixed rule
requires finite, positive-error, STATUS=0 rows and uninterrupted cadence
through the entire event/guard/sideband context. Four flagged rows per visit
and cadence gaps sharply restrict the eligible portions.

| Visit | Flagged rows | Cadence gap after row | Union of rows used as eligible events |
|---|---|---|---|
| TG009301 | 14, 50, 66, 97 | 14, 50, 66 | 29–35 and 81–82 (9 rows) |
| TG009302 | 33, 93, 112, 113 | 32, 92, 111 | 14–18 and 48–78 (36 rows) |

All indices are zero-based. A gap here is an adjacent BJD step outside the
pre-existing 0.5–1.5-cadence bounds. These row unions are bookkeeping for
the existing screen, not new qualified observing-coverage claims.

The highest displayed first-visit point is row 43, **9.674890% above its
visit median**; the highest second-visit point is row 86, **12.248097% above
its visit median**. Both have STATUS=0, but **neither appears in any eligible
event window**. Their required right contexts encounter the existing flagged
rows/gaps near rows 50 and 93. These percentages describe display normalization,
not excesses relative to fitted local event baselines. Their physical causes
remain unassigned; no event significance or image classification is attached.

The coverage review uses only retained tables and the full saved window
ledger. It changes no eligibility rule, mask, duration, threshold or follow-up
selection. The null applies to 123 eligible windows, not every visible
variation. No image acquisition or residual study is triggered.

## Verification and publication

Both own-header checks confirm NEXP=1, EXPTIME=TEXPTIME=60 seconds,
PIPE_VER=14.1.2, 18 columns and 138-byte rows. The separate scalar FITS-card
audit verifies every schema, source identity, receipt and row/byte boundary;
its reader was frozen before header access. Both workflows succeed. All
five inherited transport tests and both stable L2 arithmetic tests pass.
The independent scalar science audit passes **1,476 numerical/discrete
comparisons**, with zero disagreements at the unchanged relative 2e-8 /
absolute 2e-10 tolerances. The original arithmetic is unchanged.

Exactly **40,320 header bytes**, followed by **29,256 L2 science-table bytes**,
were acquired under separate public freezes. All four URL resolutions succeed
on their first attempt. Zero image bytes, alternate apertures, raw imagettes
or other visits were acquired. All 64 files in the four-commit scientific
sequence match their public Git identities locally; all 28 header and 22
science manifest entries match SHA256. The complete figure was visually
inspected. No qualified candidate, detector, sensitivity, completeness,
population limit or observing-coverage claim is added.

## Exact next action

Prepare **LS8AV for rank-18 GJ 9404**, using the first two of three eligible
visits in the original unchanged cohort:

| Chronological visit | Exact key | Ledger start MJD | Ledger tuple, requiring own-header checks |
|---|---|---:|---|
| 1 | CH_PR100018_TG007301_V0300 | 58973.0244933752 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |
| 2 | CH_PR100018_TG007302_V0300 | 58975.773334289 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |

Freeze the exact pair and bounded header reader before new headers. Verify
each identity, full schema, row count and exposure tuple independently,
then separately freeze DEFAULT-L2 source identities and byte ranges before
values. Transfer the unchanged signed one/two/three-row scorer and scalar
audit using verified cadence. GJ 9404 science values remain unopened;
TG007303 stays outside this prospective pair. The original 1,000-row census,
452 eligible visits and 107-cohort order remain fixed.

No LS IV +09 2 outcome becomes a new cut. EC 14599-2047 remains closed within
its eligible windows, with its late point unassessed by that screen. GJ 581
retains all 14 original labels, including two unresolved events, and its
closed bounded study. All other earlier labels, closed studies and reserved
TESS/M43 panels are unchanged. Calibration NOT_READY; technical request UNSENT.
Standing research/publication authorization continues; delegation is deferred.

[L2 report and figure](results_ls8au_l2_screen/REPORT.md) ·
[Independent science audit](results_ls8au_l2_screen/audit.json) ·
[Publication record](PUBLICATION_2026-09-23_LS8AU.md) ·
[Retained scope and release verification](verification_ls8au/release_verification.json).
