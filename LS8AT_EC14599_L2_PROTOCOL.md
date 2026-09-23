# LS8AT — EC 14599-2047 exact DEFAULT-L2 screen

23 September 2026. **SCIENCE SCOPE FROZEN BEFORE TABLE ACCESS**.

The rank-16 pair passed public header-only preflight following header freeze
`eb7fc7d955b90a136ebf0b70f52c9781e285b583`. The exact header-result commit is
pinned in config/ls8at_l2_scope.json. All 28 metadata-manifest entries match
their SHA256 hashes. The independent 80-byte FITS-card parser in
scripts/ls8at_header_audit.py verifies both complete 18-column schemas,
source identities and every receipt, row count, byte boundary and exposure
tuple. Its public result is verification_ls8at/header_audit.json.
No science values or pixels were read in that audit.

## Exact inputs

| Product key | Rows | Row bytes | First byte | Last byte inclusive | Table bytes | NEXP | EXPTIME / TEXPTIME |
|---|---:|---:|---:|---:|---:|---:|---:|
| CH_PR100002_TG010301_V0300 | 90 | 138 | 20160 | 32579 | 12420 | 1 | 60 / 60 s |
| CH_PR100002_TG010302_V0300 | 80 | 138 | 20160 | 31199 | 11040 | 1 | 60 / 60 s |

Exactly **23,460 science-table bytes** are authorized. ETags, filenames,
total sizes, schemas and header hashes are fixed in config/ls8at_l2_scope.json.
PIPE_VER=14.1.2 in both. These are the first two of three eligible visits;
TG010303 remains outside this pair. No other aperture, visit, extension,
padding, image or raw imagette is included.

Require public freeze HEAD, clean tracked tree, dependency pins and metadata
checksums before access. Read only the exact ranges with If-Match, HTTP 206,
exact range/length/total, matching ETag and filename. Preserve each table and
receipt before processing. Identity, schema, exposure, range or unrecovered
transport failures stop without substitution or widening.

## Unchanged arithmetic and transport

Thin adapters invoke unchanged hash-pinned LS8K acquisition, stable scorer,
eligibility, clustering and independent scalar auditor. Only keys, paths,
cohort names and rank change. The tested URL-timeout helper permits at most
three original resolution requests per product, each with 45-second timeout,
five-second spacing, retrying only TimeoutError including that wrapped
URLError reason. All attempts are retained; table requests remain unretried.
All five transport tests passed before the header requests.

- Durations: one/two/three rows, **60/120/180 seconds** per visit.
- Context: 12-row sidebands and two-row guards on each side.
- Eligibility: finite BJD, FLUX and FLUXERR, FLUXERR>0, STATUS=0 throughout;
  adjacent BJD steps within 0.5–1.5 times verified cadence; no gap bridging.
  EVENT remains metadata, with no new veto.
- Sideband-only flux-centered linear baseline, unchanged robust/formal noise
  and prediction leverage; symmetric endpoints **+8.5 and -8.5**.
- Separate signed clusters of overlapping/adjacent event intervals. Keep
  all members; representative is strongest signed score, then shorter,
  then earlier. Retain every eligible window and signed representative.
- Both stable-arithmetic known-answer tests pass before values. Independently
  decode big-endian rows, enumerate contexts, solve scalar equations and check
  signed counts/clusters. Exact discrete comparisons and unchanged numerical
  tolerances, relative 2e-8 and absolute 2e-10.
- Plot complete retained tables and every eligible score. Visit-median
  normalization is for display; scoring remains in electron units.

No previous image label, correction ratio, weighted residual or hypothetical
subtraction becomes a screening cut. Scores are not Gaussian significances
or false-alarm probabilities. Windows overlap. No sensitivity, completeness,
population limit, candidate/detector or observing coverage is qualified here.

## Complete outcomes and stopping

Retain any zero-eligible visit. If either sign crosses, freeze the complete
signed representative set for separate CAL/COR diagnostics, establish unique
exposure joins, then separately freeze exact image/smearing ranges before
values. This stage permits zero image bytes. Preserve numerical failures and
diagnose retained inputs before new access or promotion.

If neither sign crosses, close the pair as a descriptive null. Next is
rank-17 **LS IV +09 2**, pair CH_PR100002_TG009301_V0300 and
CH_PR100002_TG009302_V0300, under separate header/table freezes. Do not tune
or expand EC 14599-2047 from its outcome.

Publish all tables, ledgers, signed clusters, receipts, audits, report, figure,
environment, logs and checksums. GJ 581 keeps all 14 original labels and its
closed bounded study. Earlier unresolved labels and closed studies remain
unchanged; reserved TESS/M43 panels stay closed. Calibration is NOT_READY,
request UNSENT. Standing publication authorization applies; delegation deferred.
