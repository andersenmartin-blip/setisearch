# LS8N — frozen two-visit GJ 1132 DEFAULT-L2 screen

Status: **FROZEN BEFORE GJ 1132 TABLE VALUES**.

The rank-2 pair/header freeze is
`4311c777d4b9fda1a89b91d674ccca8caa813fdb`. Its public header-only result is
`d66d357aed60e1470a5c2ee9f1c8dd3f5a13bccc`, status PASS_COMPATIBLE, with
40,320 total header bytes and **zero science-table bytes** acquired.
Both products match the pinned 18-field / 138-byte scalar-decoder schema,
PIPE 14.1.2, NEXP=1 and EXPTIME=TEXPTIME=60 s.

| Exact file key | Rows | Table start (zero-based byte) | Table bytes | Inclusive final byte |
|---|---:|---:|---:|---:|
| CH_PR100041_TG000401_V0300 | 301 | 20160 | 41538 | 61697 |
| CH_PR100041_TG000403_V0300 | 314 | 20160 | 43332 | 63491 |

Acquire exactly these two DEFAULT table ranges, **84,870 bytes** in total,
using their frozen total sizes, ETags and Content-Disposition identities in
`config/ls8n_l2_scope.json`. Verify the pinned metadata summary and entire
header checksum manifest before acquisition. Require HTTP 206 and exact
Content-Range, Content-Length, ETag and filename. No substitution or widening
is allowed if an identity/transport/schema gate fails; preserve the outcome.

## Unchanged screen and independent audit

Call the existing LS8K acquisition/scoring/clustering functions and existing
independent LS8K scalar auditor through thin LS8N path/key adapters. Their
source-file hashes and the stable numerical module are pinned in the scope
configuration. No numerical implementation is changed for this transfer.

- Durations: 1/2/3 rows, corresponding to 60/120/180 seconds of integration.
- Sidebands: 12 rows each side; guards: 2 rows each side.
- Require finite BJD/FLUX/FLUXERR, FLUXERR>0 and STATUS=0 over the entire
  context, and adjacent time steps between 0.5 and 1.5 times TEXPTIME.
- Use the existing sideband-only, flux-centered local linear fit, robust/formal
  noise scale and prediction-leverage factor. Keep endpoints **+8.5 and -8.5**.
  Retain EVENT flags for reporting; they are not a new veto.
- Cluster each sign separately by overlapping/adjacent event intervals;
  choose representatives by largest signed score, shorter duration, then
  earlier row. Save every eligible window, cluster member and representative.
- Run the existing two stable-arithmetic known-answer tests before table
  access. Independently decode big-endian 138-byte rows, enumerate all
  eligible windows and solve scalar normal equations. Preserve numerical
  tolerances **relative 2e-8, absolute 2e-10**, and exact cluster/summary rules.
- Display both complete retained tables and all eligible signed scores.
  Visit-median normalization is for plotting only. Gaps are not interpolated.

The first two selected visits and all outcomes stay in the result. Neither
LS8M residual weighting nor compactness is used for selection, veto or scoring.
Scores are not Gaussian significances, and overlapping windows are not
independent trials. This screen establishes no sensitivity/completeness,
population limit, qualified detector/candidate or qualified observing coverage.

## Stopping rule

A zero-eligible visit is a valid fixed result. If either endpoint is crossed,
retain every signed representative and prepare one separately frozen CAL/COR
metadata-and-image follow-up, with unique exposure joins and exact byte scope
before image access. No image acquisition is authorized by this L2 freeze.

If neither endpoint is crossed, close the pair as a descriptive null without
altering thresholds or adding visits. The next independent cohort is rank 3,
HD 136352, in the unchanged reconciled LS8J ledger; its pair requires a new
prospective metadata-first freeze. This is not an automatic new acquisition.

On an audit failure preserve the original result and diagnose only retained
tables before further acquisition. Publish success, failure and null outcomes
with raw ranges, complete diagnostics, independent audit, logs, environment
and checksum manifest. Leave the closed WASP-189 branch, alternate apertures,
raw imagettes, reserved TESS sectors and M43 held-out panels unchanged. The
external raw-imagette calibration request remains unsent.
