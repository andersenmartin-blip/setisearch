# LS8AK — PG 1343-102 exact DEFAULT-L2 screen

22 September 2026. **SCIENCE SCOPE FROZEN BEFORE TABLE ACCESS**.

The rank-12 pair passed its public header-only preflight at
`03dc2e9bf9d80d992f63de1f9757ddcb08bbc558`, following header freeze
`d4095e08d24154e59998435588af2cf79fab7a06`. All 28 metadata-manifest entries
were retrieved and checksum verified. Independent scalar FITS-card checks
confirm both row counts, row widths and exposure tuples. Table values and
images remained unopened during review.

## Exact inputs

| Product key | Rows | Row bytes | First byte | Last byte inclusive | Table bytes | NEXP | EXPTIME / TEXPTIME |
|---|---:|---:|---:|---:|---:|---:|---:|
| CH_PR100002_TG008701_V0300 | 86 | 138 | 20160 | 32027 | 11868 | 1 | 60 / 60 s |
| CH_PR100002_TG008702_V0300 | 90 | 138 | 20160 | 32579 | 12420 | 1 | 60 / 60 s |

Exactly **24,288 science-table bytes** are authorized.
Source ETags, filenames, total sizes, complete 18-column schema and header
hashes are fixed in config/ls8ak_l2_scope.json. PIPE_VER=14.1.2 in both.
The original/reconciled rank-12 chronology is unchanged. No other aperture,
visit, extension, padding, image or raw imagette is included. The later eligible visits
CH_PR100002_TG008703_V0300 and CH_PR100002_TG008704_V0300 remain outside this transfer.

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

If neither sign crosses, close this PG 1343-102 pair as a descriptive null. The
next predetermined cohort is rank-13 **HD 106315**, chronological pair
CH_PR100041_TG000801_V0300 and CH_PR100041_TG001401_V0300, requiring separate
header/table freezes. Do not tune or expand the closed PG 1343-102 pair.

Publish all tables, ledgers, signed clusters, receipts, audits, reports,
figure, environment, logs and checksums. Earlier TESS_260647166's positive
remains unresolved; prior bounded studies remain closed. Reserved TESS/M43
panels stay closed. Calibration is NOT_READY and its request unsent. Standing
publication authorization applies; delegation remains deferred.
