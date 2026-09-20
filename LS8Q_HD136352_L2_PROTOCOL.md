# LS8Q — frozen two-visit HD 136352 DEFAULT-L2 screen

Status: **EXACT SCIENCE SCOPE FROZEN BEFORE TABLE VALUES**.

Pair/header freeze: `ec67f47f2e7782d0aed8b7e6be27c9327fa0b43a`.
Public header result: `3cb7624f5044bcdb45293df880f939e4a13352b0`,
**PASS_COMPATIBLE** after 40,320 header bytes and **zero science-table bytes**.
Both products have PIPE 14.1.2, the compatible 18-field/138-byte schema,
NEXP=26, EXPTIME=1.70000004768372 s and TEXPTIME=44.2000007629395 s.

| Exact file key | Rows | Zero-based table start | Table bytes | Inclusive final byte |
|---|---:|---:|---:|---:|
| CH_PR100041_TG000901_V0300 | 558 | 20160 | 77004 | 97163 |
| CH_PR100041_TG000101_V0300 | 567 | 20160 | 78246 | 98405 |

Acquire exactly these two DEFAULT table intervals, **155,250 bytes** total.
Their frozen total sizes, ETags, Content-Disposition identities, complete
headers and schema are in `config/ls8q_l2_scope.json`. Verify the pinned
metadata summary, full header manifest and immutable acquisition/scoring/
audit source files before values. Require HTTP 206, exact Content-Range and
Content-Length, matching ETag and filename. Never substitute or expand a
range after an identity, transport or schema failure; preserve the outcome.

## Unchanged numerical method

Thin LS8Q path/key adapters call the exact pinned LS8K acquisition, score,
eligibility and signed-clustering functions and the exact independently
implemented LS8K scalar auditor. No numerical source is changed.

- Durations: one/two/three stacked rows, approximately 44.2/88.4/132.6 s
  integrated exposure. Individual 1.7-second exposures are not resolved by
  these DEFAULT-L2 rows; do not claim that temporal resolution.
- Sidebands: 12 rows each side; guards: two rows each side.
- Entire context: finite BJD/FLUX/FLUXERR, FLUXERR>0 and STATUS=0; adjacent
  BJD steps between 0.5 and 1.5 times the verified TEXPTIME. Do not bridge gaps.
- Sideband-only, flux-centered linear baseline, original robust/formal
  noise and prediction leverage, endpoints **+8.5 and -8.5**. EVENT flags
  remain reported metadata, not an additional veto.
- Cluster the two signs separately by overlapping/adjacent event intervals;
  choose largest signed score, shorter duration, then earlier start. Keep
  every eligible window, cluster member and representative in both visits.
- Run the existing two stable-arithmetic known-answer tests before values.
  Independently decode the 138-byte rows, enumerate all eligible contexts,
  solve scalar normal equations and compare every score/cluster/summary.
  Keep exact discrete rules and **relative 2e-8 / absolute 2e-10** tolerance.
- Plot both complete retained tables and all eligible signed scores.
  Visit-median normalization is for display only; actual scoring uses the
  original local baseline in electrons.

Neither LS8M nor LS8P weighted residuals, covariance models, aperture changes
or hypothetical displacement subtraction are detection rules in this screen.
The score is not a calibrated Gaussian significance or false-alarm probability;
overlapping windows are not independent trials. No completeness, short-glint
sensitivity, population limit, qualified candidate/detector or additional
qualified observing coverage follows from this descriptive screen.

## Complete outcomes and stop

A zero-eligible visit remains a valid outcome. If either sign forms a cluster,
retain **all** representatives for one separately frozen CAL/COR diagnostic.
Establish unique exposure metadata joins, then freeze exact image/smearing
ranges before accessing their values. This L2 scope authorizes zero images.

If neither endpoint is crossed, close the HD 136352 pair as a descriptive null
without adding visits or changing thresholds. The next target is rank 4,
TESS_260647166, in the unchanged reconciled LS8J ledger. Its existing pair is
CH_PR300046_TG000101_V0300 followed by CH_PR100031_TG015701_V0300; it requires
its own header and exact science-byte freeze before any data acquisition.

On any audit failure, preserve the original run and diagnose retained tables
before further acquisition. Publish raw ranges, receipts, complete eligible
and signed results, audit, report, figure, logs, environment and checksums.
Closed GJ 1132 and WASP-189 studies, alternate apertures, raw imagettes,
reserved TESS sectors and M43 held-out panels remain unchanged. The separate
raw-imagette calibration request remains unsent; publication is already
authorized under the ongoing project scope.
