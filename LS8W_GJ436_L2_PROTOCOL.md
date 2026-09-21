# LS8W — GJ 436 exact DEFAULT-L2 screen

21 September 2026. **SCIENCE SCOPE FROZEN BEFORE TABLE ACCESS**.

The rank-6 pair passed its public header-only preflight at
`d4e4d2fd07d11c28e95bab3b495d9cf0152d6d04`, following header freeze
`13b1883b82b8e4178336e8b60390ef8474923d53`. All 28 metadata-manifest entries
were retrieved and checksum verified. Independent scalar FITS-card checks
confirm both row counts, row widths and exposure tuples. Table values and
images remained unopened during that review.

## Exact inputs

| Product key | Rows | Row bytes | First byte | Last byte inclusive | Table bytes | NEXP | EXPTIME / TEXPTIME |
|---|---:|---:|---:|---:|---:|---:|---:|
| CH_PR100041_TG000302_V0300 | 340 | 138 | 20160 | 67079 | 46920 | 1 | 60 / 60 s |
| CH_PR100041_TG001301_V0300 | 300 | 138 | 20160 | 61559 | 41400 | 1 | 60 / 60 s |

Exactly **88,320 science-table bytes** are authorized. Product identities,
ETags, filenames, total file sizes, complete 18-column schema and source
header checksums are fixed in `config/ls8w_l2_scope.json`. PIPE_VER=14.1.2
for both visits. Their unchanged original/reconciled cohort position is
rank 6; no other aperture, visit, table extension, padding or image is included.

Require the public freeze HEAD, clean tracked tree, all dependency pins and
all metadata checksums before archive access. Read only these exact table
ranges, with If-Match, HTTP 206, exact range/length/total size, matching ETag
and filename. Preserve each original table and receipt before processing.
An identity, schema, exposure, range or unrecovered transport failure stops
without alternate products or scope expansion; preserve the first outcome.

## Unchanged arithmetic and bounded transport

The thin LS8W adapters invoke the same hash-pinned LS8K acquisition, stable
scorer, eligibility, signed clustering and independent scalar auditor. Only
paths and keys change, and the previously frozen timeout helper wraps URL
resolution. It permits at most three original URL requests per product,
45 seconds each, with five-second delays, only after TimeoutError (including
that precise wrapped URLError reason). Retain every attempt and outcome.
Do not retry the science-table request or weaken any gate. Both header URL
resolutions succeeded on their first attempt. All five transport tests pass.

- Event durations: one/two/three rows, **60/120/180 seconds** per visit.
- Sidebands: 12 rows on each side, with two-row guards on each side.
- Entire context: finite BJD, FLUX and FLUXERR; FLUXERR>0; STATUS=0;
  consecutive BJD steps within 0.5–1.5 times that visit's verified TEXPTIME.
  Do not bridge gaps. EVENT remains a reported value, not a new veto.
- Sideband-only, flux-centered linear baseline, original robust/formal noise
  and baseline-prediction leverage; symmetric endpoints **+8.5 and -8.5**.
- Cluster each sign separately by overlapping/adjacent event intervals;
  retain all members. Choose largest signed score, then shorter duration,
  then earlier start. Preserve every eligible window and representative.
- Before values, run the two existing stable-arithmetic known-answer tests.
  Independently decode the big-endian rows, enumerate eligible contexts,
  solve scalar normal equations and verify scores, clusters and counts.
  Keep exact discrete checks and relative 2e-8 / absolute 2e-10 tolerances.
- Plot both complete retained tables and every eligible signed score.
  Median normalization is only for display; scoring uses local baselines
  in electron units.

No earlier image label, residual rank, covariance model, alternative aperture
or hypothetical correction becomes a selection rule. Scores are not Gaussian
significances or calibrated false-alarm probabilities. Overlapping windows
are dependent. No short-glint sensitivity, completeness, population limit,
qualified candidate/detector or observing coverage is established here.

## Complete outcomes and continuation

A zero-eligible visit is retained as such. If either sign has clusters,
prepare one separately frozen CAL/COR diagnostic retaining **all** signed
representatives. Verify exact exposure joins first, then freeze exact image
and smearing intervals before values. This L2 scope permits zero image bytes.

If both signs are empty, close this pair as a descriptive null. The next
fixed cohort is rank-7 **PG 1245-042**, with chronological pair
CH_PR100002_TG008601_V0300 and CH_PR100002_TG008602_V0300. It requires its own
metadata/header and science freezes. Do not expand or retune GJ 436 after
seeing this result.

On numerical audit failure, preserve the result and diagnose retained tables
before further acquisition or promotion. Publish all tables, eligible/signed
results, receipts, audit, figure, report, transport records, logs, environment
and checksums. Closed EC 12578-2107 and other optical studies remain closed;
the earlier TESS_260647166 positive remains unresolved within its fixed scope.
Reserved TESS/M43 panels stay closed. Calibration remains NOT_READY and its
technical request unsent. Standing publication authorization continues;
delegation remains deferred.
