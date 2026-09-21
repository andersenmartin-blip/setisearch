# LS8Y — PG 1245-042 exact DEFAULT-L2 screen

21 September 2026. **SCIENCE SCOPE FROZEN BEFORE TABLE ACCESS**.

The rank-7 pair passed its public header-only preflight at
`7bea9c90c40fb36fa75f2826fbc2e6e51f70555c`, following header freeze
`32fb831f02cec5bea3f8d2c35d22f5eefaa73e92`. All 28 metadata-manifest entries
were retrieved and checksum verified. Independent scalar FITS-card checks
confirm both row counts, row widths and exposure tuples. Table values and
images remained unopened during that review.

## Exact inputs

| Product key | Rows | Row bytes | First byte | Last byte inclusive | Table bytes | NEXP | EXPTIME / TEXPTIME |
|---|---:|---:|---:|---:|---:|---:|---:|
| CH_PR100002_TG008601_V0300 | 85 | 138 | 20160 | 31889 | 11730 | 1 | 60 / 60 s |
| CH_PR100002_TG008602_V0300 | 79 | 138 | 20160 | 31061 | 10902 | 1 | 60 / 60 s |

Exactly **22,632 science-table bytes** are authorized.
Product identities, ETags, filenames, total sizes, complete 18-column schema
and source header hashes are fixed in config/ls8y_l2_scope.json. PIPE_VER is
14.1.2 in both. The original/reconciled cohort position remains rank 7.
No other aperture, visit, table extension, padding or image is included.

Require the public freeze HEAD, clean tracked tree, all dependency pins and
metadata checksums before access. Read only the exact ranges with If-Match,
HTTP 206, exact range/length/total size, matching ETag and filename. Preserve
original tables and receipts before processing. Stop on identity, schema,
exposure, range or unrecovered transport failure, preserving the first outcome.

## Unchanged arithmetic and transport

The thin adapters invoke the unchanged hash-pinned LS8K acquisition, stable
scorer, eligibility, signed clustering and independent scalar auditor. Only
paths and keys change. Reuse the previously frozen URL-timeout helper: at
most three original resolution calls per product, 45 seconds each, five-second
spacing, retry only TimeoutError including that exact wrapped URLError reason.
Preserve every attempt. The science-table requests themselves remain unretried.
All five transport tests passed before headers.

- Event durations: one/two/three rows, **60/120/180 seconds** per visit.
- Sidebands: 12 rows on each side, with two guards per side.
- Entire context: finite BJD, FLUX and FLUXERR; FLUXERR>0; STATUS=0;
  consecutive BJD steps within 0.5–1.5 times the verified visit cadence.
  Do not bridge gaps. EVENT is recorded, not a new veto.
- Sideband-only, flux-centered linear baseline, original robust/formal noise
  and baseline-prediction leverage; endpoints **+8.5 and -8.5**.
- Separate signed clusters of overlapping/adjacent event intervals. Keep
  every member; representative is strongest signed score, then shorter
  duration, then earlier start. Preserve every eligible window.
- Before values, run both existing stable-arithmetic known-answer tests.
  Independently decode big-endian rows, enumerate eligible contexts, solve
  scalar equations and check scores, counts and signed cluster sets.
  Exact discrete checks; relative 2e-8 / absolute 2e-10 numeric tolerances.
- Plot complete retained tables and every eligible signed score. Median
  normalization is for display only; scoring uses electron-valued baselines.

No prior image label, correction ratio, residual rank, covariance diagnostic
or hypothetical subtraction becomes a selection cut. Scores are not Gaussian
significances or false-alarm probabilities; windows overlap. No sensitivity,
completeness, population limit, qualified candidate/detector or observing
coverage is established by this screen.

## Complete outcomes and stopping

Retain visits with zero eligible windows. If either sign has clusters, freeze
one CAL/COR diagnostic containing **all signed representatives**, establish
unique exposure joins and then separately freeze exact image/smearing ranges.
This L2 scope authorizes zero image bytes. On numerical audit failure,
preserve and diagnose retained inputs before further access or promotion.

If neither sign crosses, close this PG 1245-042 pair as a descriptive null.
The next fixed cohort is rank-8 **WASP-43**, chronological pair
CH_PR100016_TG007801_V0300 and CH_PR100016_TG007802_V0300, requiring separate
header and table freezes. Do not extend to the five later PG 1245-042 visits
or tune the closed pair after its outcome.

Publish all original tables, eligible/signed results, receipts, audit, figure,
report, transport records, logs, environment and checksums. Prior closed
studies remain closed; the earlier TESS_260647166 positive remains unresolved.
Reserved TESS/M43 panels stay closed. Calibration is NOT_READY and its request
unsent. Standing publication authorization continues; delegation is deferred.
