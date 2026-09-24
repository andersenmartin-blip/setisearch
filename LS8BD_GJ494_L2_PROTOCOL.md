# LS8BD — GJ 494 exact DEFAULT-L2 screen

24 September 2026. **SCIENCE SCOPE FROZEN BEFORE TABLE ACCESS**.

The predetermined rank-23 pair passed its own header preflight. Header freeze:
`c536c25eea1cc0609fd3158ffb5c80e71392da4c`; successful header-result commit:
`c258bb317464ebeae6b96dc2729ff8aa3df1942e`.
All 28 metadata-manifest entries match SHA256. The independent scalar
FITS-card parser verifies both complete 18-column schemas, identities,
receipts, row counts, byte boundaries and exposure tuples. Its source was
frozen before headers; its PASS result is verification_ls8bd/header_audit.json.
No science values or image pixels were read.

## Exact inputs and verified cadence

| Product key | Rows | Row bytes | First byte | Last byte inclusive | Table bytes | NEXP | Own EXPTIME = TEXPTIME, seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| CH_PR100018_TG007401_V0300 | 83 | 138 | 20160 | 31613 | 11454 | 1 | 42 |
| CH_PR100018_TG007402_V0300 | 65 | 138 | 20160 | 29129 | 8970 | 1 | 42 |

Exactly **20,424 science-table bytes** are authorized. Both products have
PIPE_VER=14.1.2 and independently verified NEXP=1, EXPTIME=TEXPTIME=42 seconds,
agreeing with their original ledger values and frozen binary32 encoding.
Use each own verified TEXPTIME as cadence. ETags, filenames, total sizes,
complete schemas and header hashes are pinned in config/ls8bd_l2_scope.json.
These are the chronological first two of four eligible visits in the ledger.
TG007403 and TG007404 remain outside the selected pair.
No other aperture, visit, extension, padding, image or raw imagette is included.

Require public freeze HEAD, clean tracked checkout, all 14 input pins and
metadata checksums before access. Read only exact ranges with If-Match,
HTTP 206, exact range/length/total and matching ETag/filename. Preserve each
table and receipt before processing. Identity, schema, exposure, range or
unrecovered transport failure stops without substitution or widening.

## Unchanged arithmetic and bounded execution

Thin adapters invoke unchanged hash-pinned LS8K acquisition, stable scorer,
eligibility, signed clustering and independent scalar auditor. Only paths,
identities, target, rank and next-cohort text differ from LS8BC. The report
uses each visit's verified cadence for displayed durations. The unchanged
URL resolver permits at most three identical resolution calls per product,
45-second timeout and five-second spacing, retrying only TimeoutError
including that exact wrapped URLError reason. Retain every attempt; exact
table-range requests are not retried. All five existing transport tests
passed before header acquisition.

- Durations: one/two/three rows, independently verified 42/84/126 seconds.
- Context: 12-row sidebands and two-row guards on each side.
- Eligibility: finite BJD, FLUX and FLUXERR, FLUXERR>0, STATUS=0 throughout;
  adjacent BJD steps within 0.5–1.5 own cadences, without bridging gaps.
  EVENT remains metadata and adds no veto.
- Sideband-only flux-centered linear baseline, unchanged robust/formal noise
  and prediction leverage; symmetric endpoints **+8.5 and -8.5**.
- Separate signed clusters of overlapping/adjacent event intervals; keep all
  members. Representative: strongest signed score, then shorter, then earlier.
  Retain every eligible window and every signed representative.
- Both existing stable-arithmetic tests pass before values. Independent
  big-endian row decoding, context enumeration, scalar normal equations and
  checks of signed clusters/counts. Exact discrete comparisons and unchanged
  relative 2e-8 / absolute 2e-10 numerical tolerances.
- Plot complete retained tables and every eligible score. Visit-median
  normalization is display only; scoring stays in electron units.

The already verified sparse-checkout pattern includes all root files and
required code, metadata, verification and output directories. It covers every
pin. Preservation requires successful checkout; an unsuccessful scientific
execution cannot pass the final success gate. No previous edge point, image
label, residual or hypothetical subtraction becomes a cut.

Scores are not Gaussian significances or false-alarm probabilities. Windows
overlap. No sensitivity, completeness, population limit, qualified candidate,
detector or observing coverage follows from this screen.

## Complete outcomes and stopping

Retain any zero-eligible visit. If either sign crosses, freeze the complete
signed representative set for paired CAL/COR diagnostics, independently
establish unique exposure joins, then separately freeze exact image/smearing
ranges before pixels. This L2 stage permits zero image bytes. Preserve any
numerical failure and diagnose retained inputs before new access or promotion.

If neither sign crosses, close the pair as a descriptive null within eligible
windows and prepare **LS8BE, rank-24 2MASS J11474440+0048164**, exact pair
CH_PR100018_TG007101_V0300 / CH_PR100018_TG007102_V0300, under separate header
and table freezes. These are both eligible visits for that target; its science
values remain unopened. Do not tune or widen the GJ 494 pair, including its
two later visits, based on these outcomes. A visit with zero eligible windows
supplies no tested null.

Publish every table, ledger, signed cluster list, receipt, audit, report,
figure, environment, log and checksum. GJ 536 retains all nine image labels,
including two unresolved events, and its closed single bounded study.
Earlier null scopes, unassessed points, unresolved labels and closed studies
remain unchanged. Reserved TESS/M43 panels stay closed. Calibration NOT_READY;
request UNSENT. Publication authorized; delegation deferred.
