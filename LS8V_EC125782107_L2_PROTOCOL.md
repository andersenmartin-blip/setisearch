# LS8V — EC 12578-2107 exact DEFAULT-L2 screen

21 September 2026. Status: **SCIENCE SCOPE FROZEN BEFORE TABLE ACCESS**.

The unchanged rank-5 pair passed its public metadata-only preflight at
`1eb452464982af7bd23e67bca33d429000297a2a`, following header freeze
`91dce63e208e126affe519077a9bf571263a8810`. Both exact headers and all
26 manifest-listed metadata files were retrieved and checksum checked.
Independent scalar FITS-card checks confirm both row counts and exposure
tuples. No science values or images were read in that review.

## Exact inputs and limits

| Product | Rows | Row bytes | First byte | Last byte inclusive | Table bytes | NEXP | EXPTIME / TEXPTIME |
|---|---:|---:|---:|---:|---:|---:|---:|
| CH_PR100002_TG008901_V0300 | 87 | 138 | 20160 | 32165 | 12006 | 1 | 60 / 60 s |
| CH_PR100002_TG008902_V0300 | 87 | 138 | 20160 | 32165 | 12006 | 1 | 60 / 60 s |

Total authorized science bytes: **24,012**. Both files have total size
34,560 bytes, PIPE_VER=14.1.2 and the original 18-column schema. Exact ETags,
filenames, schema, header hashes and acquisition identities are retained in
`config/ls8v_l2_scope.json`. The source census, reconciliation and rank-5
selection remain unchanged. No padding, other extension, alternate aperture,
later visit, image or raw imagette is included.

Before values, verify the public freeze HEAD, clean tracked tree, all input
pins and all metadata checksums. Use only the two frozen DEFAULT-L2 ranges,
requiring If-Match, HTTP 206, exact Content-Range/Content-Length, matching
ETag and filename. Preserve acquired bytes and receipts. An identity,
transport or schema failure stops without alternate inputs or scope expansion.

## Unchanged screen and independent audit

Thin LS8V path/key adapters invoke the unchanged hash-pinned LS8K acquisition,
stable scorer, eligibility, signed clustering and independent scalar auditor.
The numerical code, thresholds and audit tolerances are unchanged.

- Durations: one/two/three rows, **60/120/180 seconds** in each visit.
- Sidebands: 12 rows on each side; guards: two rows on each side.
- Whole context: finite BJD/FLUX/FLUXERR, positive FLUXERR and STATUS=0;
  consecutive BJD steps within 0.5–1.5 times that visit's verified TEXPTIME.
  Never bridge a gap. EVENT is reported and is not an extra veto.
- Sideband-only, flux-centered linear baseline; original robust/formal noise
  and baseline-prediction leverage; symmetric thresholds **+8.5 and -8.5**.
- Cluster signs separately by overlapping/adjacent event intervals. Keep all
  members; choose largest signed score, then shorter duration, then earlier
  start. Retain all eligible windows and every signed representative.
- Before values, run the two existing stable-arithmetic known-answer tests.
  Independently decode big-endian rows, enumerate eligible windows, solve
  scalar normal equations, and verify scores, clusters and summary counts.
  Tolerances remain relative 2e-8 / absolute 2e-10 with exact discrete checks.
- Display both retained light curves and all eligible signed scores.
  Visit-median normalization is only for display; scoring uses local
  sideband baselines in electron units.

No LS8U residual rank, ring, covariance ratio, image label, alternative
aperture or hypothetical subtraction becomes a new cut or veto. Scores are
not Gaussian significances or false-alarm probabilities; overlapping windows
are dependent. No completeness, short-glint sensitivity, population limit,
qualified candidate/detector or observing-coverage claim follows.

## Outcomes and next action

A zero-eligible visit remains a valid outcome. If either sign has clusters,
all representatives require one separately frozen CAL/COR diagnostic.
Establish exact exposure joins, then freeze image and smearing intervals
before their values. This L2 scope authorizes **zero image bytes**.

If neither endpoint is crossed, close this exact pair as a descriptive null
without new visits or retuning. The next fixed cohort is rank-6 **GJ 436**,
pair CH_PR100041_TG000302_V0300 and CH_PR100041_TG001301_V0300; its headers
and science ranges need separate freezes.

On audit failure, preserve the first outcome and diagnose retained tables
before further acquisition or promotion. Publish complete eligible/signed
results, receipts, audit, figure, report, logs, environment and checksums.
The closed TESS_260647166 positive remains unresolved; closed HD 136352,
GJ 1132 and WASP-189 studies are unchanged. Reserved TESS/M43 data remain
closed, calibration remains NOT_READY and its request unsent. Standing
research/publication authorization applies; delegation remains deferred.
