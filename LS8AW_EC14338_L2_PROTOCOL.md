# LS8AW — EC14338-1445 exact DEFAULT-L2 screen

23 September 2026. **SCIENCE SCOPE FROZEN BEFORE TABLE ACCESS**.

The rank-19 pair passed public header-only preflight after header freeze
`a39fb989d906705f5583e16542a045f2da90b851`. The header-result commit is pinned
in config/ls8aw_l2_scope.json. All 28 metadata-manifest entries match SHA256.
The separately implemented scalar FITS-card parser verifies both complete
18-column schemas, source identities, receipts, row counts, byte boundaries
and exposure tuples. Its source was frozen before headers; its PASS result
is verification_ls8aw/header_audit.json. No values or pixels were read.

## Exact inputs

| Product key | Rows | Row bytes | First byte | Last byte inclusive | Table bytes | NEXP | EXPTIME / TEXPTIME |
|---|---:|---:|---:|---:|---:|---:|---:|
| CH_PR100002_TG006601_V0300 | 79 | 138 | 20160 | 31061 | 10902 | 1 | 60 / 60 s |
| CH_PR100002_TG006602_V0300 | 80 | 138 | 20160 | 31199 | 11040 | 1 | 60 / 60 s |

Exactly **21,942 science-table bytes** are authorized. ETags, filenames,
total sizes, schemas and header hashes are fixed in config/ls8aw_l2_scope.json.
Both have PIPE_VER=14.1.2. These are the two eligible visits in the original cohort.
No other aperture, visit, extension, padding, image or raw imagette is included.

Require public freeze HEAD, clean tracked tree, dependency pins and metadata
checksums before access. Read only exact ranges with If-Match, HTTP 206,
exact range/length/total, matching ETag and filename. Preserve each table and
receipt before processing. Identity, schema, exposure, range or unrecovered
transport failure stops without substitution or widening.

## Unchanged arithmetic and transport

Thin adapters invoke unchanged hash-pinned LS8K acquisition, stable scorer,
eligibility, clustering and independent scalar auditor. Only keys, paths,
target and rank change from LS8AV. The tested URL-timeout helper permits at
most three original resolution requests per product, each with 45-second
timeout and five-second spacing, retrying only TimeoutError including that
wrapped URLError reason. Preserve every attempt; table requests are unretried.
All five inherited transport tests passed before headers.

- Durations: one/two/three rows, **60/120/180 seconds** per visit.
- Context: 12-row sidebands and two-row guards on each side.
- Eligibility: finite BJD, FLUX and FLUXERR, FLUXERR>0, STATUS=0 throughout;
  adjacent BJD steps within 0.5–1.5 verified cadences; no gap bridging.
  EVENT remains metadata and supplies no new veto.
- Sideband-only flux-centered linear baseline, unchanged robust/formal noise
  and prediction leverage; symmetric endpoints **+8.5 and -8.5**.
- Separate signed clusters of overlapping/adjacent event intervals. Keep all
  members; representative is strongest signed score, then shorter, then earlier.
  Retain every eligible window and every signed representative.
- Both existing stable-arithmetic tests pass before values. Independently
  decode big-endian rows, enumerate contexts, solve scalar equations and check
  signed counts/clusters. Exact discrete comparisons and unchanged numerical
  tolerances, relative 2e-8 and absolute 2e-10.
- Plot complete retained tables and every eligible score. Visit-median
  normalization is only for display; scoring stays in electron units.

No earlier edge point, image label, correction ratio, residual or hypothetical
subtraction becomes a cut. Scores are not Gaussian significances or false-alarm
probabilities. Windows overlap. No sensitivity, completeness, population limit,
candidate/detector or observing coverage is qualified by this screen.

## Complete outcomes and stopping

Retain any zero-eligible visit. If either sign crosses, freeze the complete
signed representative set for separate CAL/COR diagnostics, establish unique
exposure joins, then separately freeze image/smearing ranges before values.
This L2 stage permits zero image bytes. Preserve numerical failures and
diagnose retained inputs before new access or promotion.

If neither sign crosses, close the pair as a descriptive null. Next is
rank-20 **GJ 536**, first pair CH_PR100011_TG023501_V0300 and
CH_PR100018_TG007801_V0300, under separate header/table freezes. Do not tune
or expand EC14338-1445 based on its outcome.

Publish every table, ledger, signed cluster list, receipt, audit, report,
figure, environment, log and checksum. GJ 9404 remains closed within its
150 eligible windows, with its third visit outside that pair. LS IV +09 2 remains closed within
its 123 eligible windows. EC 14599-2047 remains closed within
eligible windows, with its late point unassessed by that screen. GJ 581
retains all 14 labels and its closed bounded study. All earlier labels and
studies remain unchanged; reserved TESS/M43 panels stay closed. Calibration
NOT_READY, request UNSENT. Publication authorized; delegation deferred.
