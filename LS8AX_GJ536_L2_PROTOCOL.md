# LS8AX — GJ 536 exact DEFAULT-L2 screen

23 September 2026. **SCIENCE SCOPE FROZEN BEFORE TABLE ACCESS**.

The rank-20 pair passed its own header preflight. Initial header/source freeze:
`b28022d5ac230ce70906e651ea9d2df71f96df63`; executed checkout-recovery freeze:
`2a7d3fad3bbcb9670880ec9b6339d0e3fc3a403c`. The first workflow timed out in Git
fetch before archive access. Its complete log and status remain preserved;
the recovery and unchanged archive reader succeed. See LS8AX_CHECKOUT_RECOVERY.md.
Header-result commit: `328c1d234217d1737edc69d7012641f46a6847c7`.

All 28 metadata-manifest entries match SHA256. The independently implemented
scalar FITS-card parser verifies both full 18-column schemas, identities,
receipts, row counts, byte boundaries and exposure tuples. Its source was
frozen before headers; its PASS result is verification_ls8ax/header_audit.json.
No science values or image pixels were read.

## Exact inputs and verified cadence

| Product key | Rows | Row bytes | First byte | Last byte inclusive | Table bytes | NEXP | Own EXPTIME = TEXPTIME, seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| CH_PR100011_TG023501_V0300 | 4133 | 138 | 20160 | 590513 | 570354 | 1 | 40.1699981689453 |
| CH_PR100018_TG007801_V0300 | 121 | 138 | 20160 | 36857 | 16698 | 1 | 40.2000007629395 |

Exactly **587,052 science-table bytes** are authorized. Both products have
PIPE_VER=14.1.2. Their own exposure values agree with the original ledger and
the separately frozen binary32 encodings. Preserve and use these full header
values as cadence; do not replace them with 60 seconds or rounded nominal values.
ETags, filenames, total sizes, schemas and header hashes are pinned in
config/ls8ax_l2_scope.json. These are the first two of five eligible visits;
CH_PR100018_TG021001_V0300, CH_PR100018_TG021002_V0300 and
CH_PR100018_TG021003_V0300 remain outside the pair. No other aperture, visit,
extension, padding, image or raw imagette is included.

Require public freeze HEAD, clean tracked tree, dependency pins and metadata
checksums before access. Read only exact ranges with If-Match, HTTP 206,
exact range/length/total, matching ETag and filename. Preserve each table and
receipt before processing. Identity, schema, exposure, range or unrecovered
transport failure stops without substitution or widening.

## Unchanged arithmetic and bounded execution

Thin adapters invoke unchanged hash-pinned LS8K acquisition, stable scorer,
eligibility, signed clustering and independent scalar auditor. Only identities,
paths, target and rank change in the science adapters. The report displays
durations from each visit's verified cadence. The tested URL-timeout helper
permits at most three original resolution calls per product, with 45-second
timeout and five-second spacing, retrying only TimeoutError including that
wrapped URLError reason. Keep every attempt; exact table requests are unretried.
All five inherited transport tests passed before actual header acquisition.

- Durations: one/two/three rows. Approximately 40.17/80.34/120.51 seconds in
  TG023501 and 40.20/80.40/120.60 seconds in TG007801. These are display
  approximations; calculations use the complete verified TEXPTIME values.
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

The workflow uses the prospectively documented sparse checkout to include all
root files and named code, metadata, verification and output directories. All
13 input pins are covered. Result preservation requires a successful checkout;
the final success gate still rejects any unsuccessful science execution.
This execution repair changes no archive request, data scope or arithmetic.

No previous edge point, image label, correction ratio, residual or hypothetical
subtraction becomes a cut. Scores are not Gaussian significances or false-alarm
probabilities. Windows overlap. No sensitivity, completeness, population limit,
candidate/detector or observing coverage is qualified by this screen.

## Complete outcomes and stopping

Retain any zero-eligible visit. If either sign crosses, freeze the complete
signed representative set for separate CAL/COR diagnostics, establish unique
exposure joins, then separately freeze image/smearing ranges before pixels.
This L2 stage permits zero image bytes. Preserve numerical failures and
diagnose retained inputs before new access or promotion.

If neither sign crosses, close the pair as a descriptive null within eligible
windows. Next is rank-21 **2MASS J11285624+1010395**, first pair
CH_PR100018_TG010801_V0300 / CH_PR100018_TG010802_V0300, under separate
header/table freezes. Do not tune or expand GJ 536 based on its outcome.

Publish every table, ledger, signed cluster list, receipt, audit, report,
figure, environment, log and checksum. EC14338-1445 remains closed within
63 eligible windows, with its excluded signed variation unassessed. Earlier
null scopes, unresolved labels and closed studies remain unchanged. GJ 581
retains all 14 labels and its closed bounded study. Reserved TESS/M43 panels
stay closed. Calibration NOT_READY; request UNSENT. Publication authorized;
delegation deferred.
