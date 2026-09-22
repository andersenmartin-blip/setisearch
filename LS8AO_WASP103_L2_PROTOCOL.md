# LS8AO — WASP-103 exact DEFAULT-L2 screen

22 September 2026. **SCIENCE SCOPE FROZEN BEFORE TABLE ACCESS**.

The rank-14 pair passed its public header-only preflight at
`3ac15f4973461879f47449a3a0925548ae99df00`, following header freeze
`094430641b3ea57dbc376aa18214156d9e9259ae`. All 28 metadata-manifest entries
were retrieved and checksum verified. Independent scalar FITS-card checks
confirm both row counts, row widths and exposure tuples. Table values and
images remained unopened during review.

## Exact inputs

| Product key | Rows | Row bytes | First byte | Last byte inclusive | Table bytes | NEXP | EXPTIME / TEXPTIME |
|---|---:|---:|---:|---:|---:|---:|---:|
| CH_PR100013_TG000101_V0300 | 269 | 138 | 20160 | 57281 | 37122 | 1 | 60 / 60 s |
| CH_PR100013_TG000102_V0300 | 296 | 138 | 20160 | 61007 | 40848 | 1 | 60 / 60 s |

Exactly **77,970 science-table bytes** are authorized.
Source ETags, filenames, total sizes, complete 18-column schema and header
hashes are fixed in config/ls8ao_l2_scope.json. PIPE_VER=14.1.2 in both.
The original/reconciled rank-14 chronology is unchanged. No other aperture,
visit, extension, padding, image or raw imagette is included. These are the first two of 11 eligible WASP-103 visits in the original cohort;
the remaining nine remain outside this transfer.

Require public freeze HEAD, clean tracked tree, dependency pins and metadata
checksums before archive access. Read only the exact ranges with If-Match,
HTTP 206, exact range/length/total, matching ETag and filename. Preserve each
original table and receipt before processing. Identity, schema, exposure,
range or unrecovered transport failure stops without substitution or widening.

## Unchanged arithmetic and transport

Thin adapters invoke the unchanged hash-pinned LS8K acquisition, stable
scorer, eligibility, clustering and independent scalar auditor. Only keys,
paths and cohort text change. Reuse the tested URL-timeout helper: at most
three original resolution requests per product, each with a 45-second timeout,
five-second spacing, retry only TimeoutError including that wrapped URLError
reason. Retain every attempt; exact science-table requests remain unretried.
All five existing transport tests pass before headers.

- Durations: one/two/three rows, **60/120/180 seconds** per visit.
- Context: 12-row sidebands and two-row guards on each side.
- Eligibility: finite BJD, FLUX and FLUXERR, FLUXERR>0, STATUS=0 throughout;
  adjacent BJD steps within 0.5–1.5 times the verified cadence. No gap bridging.
  EVENT is retained as metadata, not used as a new veto.
- Sideband-only flux-centered linear baseline, original robust/formal noise
  and prediction leverage; symmetric endpoints **+8.5 and -8.5**.
- Separate signed clusters of overlapping/adjacent event intervals. Keep
  all members; representative is strongest signed score, then shorter,
  then earlier. Retain every eligible window and signed representative.
- Before values, run both existing stable-arithmetic known-answer tests.
  Independent big-endian decoding, eligible-context enumeration, scalar
  equations and count/cluster checks. Exact discrete checks and unchanged
  relative 2e-8 / absolute 2e-10 numerical tolerances.
- Plot complete retained tables and every eligible score. Visit-median
  normalization is for display; scoring remains in electron units.

No prior image label, correction ratio, weighted residual or hypothetical
subtraction becomes a screening cut. Scores are not Gaussian significances
or false-alarm probabilities. Overlapping windows are dependent. No sensitivity,
completeness, population limit, candidate/detector or observing coverage is
qualified by this screen.

## Complete outcomes and stopping

Retain any zero-eligible visit. If either sign crosses, freeze the complete
signed representative set for a separate CAL/COR diagnostic, establish unique
exposure joins, then separately freeze exact image and smearing ranges before
values. This L2 stage permits zero image bytes. Numerical audit failures are
preserved and diagnosed on retained inputs before new access or promotion.

If neither sign crosses, close this WASP-103 pair as a descriptive null. The
next predetermined cohort is rank-15 **GJ 581**, chronological pair
CH_PR100011_TG023701_V0300 and CH_PR100018_TG008301_V0300, requiring separate
header/table freezes. Do not tune or expand the closed WASP-103 pair.

Publish all tables, ledgers, signed clusters, receipts, audits, reports,
figure, environment, logs and checksums. Earlier TESS_260647166's positive
remains unresolved; HD 106315 retains its three unresolved labels and closed
bounded study. Other prior bounded studies remain closed. Reserved TESS/M43
panels stay closed. Calibration is NOT_READY and its request unsent. Standing
publication authorization applies; delegation remains deferred.
