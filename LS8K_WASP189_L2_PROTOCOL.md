# LS8K — frozen two-visit WASP-189 DEFAULT-L2 screen

Status: **FROZEN BEFORE WASP-189 TABLE VALUES**.

The original chronological LS8J census and separately dated full-inventory
reconciliation select the same two visits. The reconciliation PASS is public
at `f50fae88ba4f52b2d288a13feaaef2e8a069be29`. Header-only preflight is
public at `7925fa43f207f94cec26ffdf628afa4aae3491af`, with a compatible
18-field / 138-byte schema and zero table-data bytes acquired.

| Exact file key | Rows | Table start (zero-based byte) | Table bytes | Inclusive final byte |
|---|---:|---:|---:|---:|
| CH_PR100041_TG000201_V0300 | 771 | 20160 | 106398 | 126557 |
| CH_PR100041_TG000202_V0300 | 833 | 20160 | 114954 | 135113 |

Both visits have NEXP=7, EXPTIME=4.80000019073486 s and
TEXPTIME=33.6000022888184 s. Acquire exactly these two table ranges, totaling
**221,352 bytes**, using the saved ETags and Content-Disposition identities.
Verify the entire header-preflight checksum manifest before science access.

## Unchanged screen and audit

Reuse `seti_repeater.cheops_l2_stable.stable_score_window`, byte-identical to
Git blob `69bed9f3c0d5455313109ef0cd0d2ceb460fe875`.

- Durations: 1, 2 and 3 rows (approximately 33.6, 67.2 and 100.8 seconds).
- Sidebands: 12 rows on each side, separated by two-row guards.
- Require finite BJD/FLUX/FLUXERR, positive FLUXERR and STATUS=0 across the
  complete context; adjacent time steps must be 0.5–1.5 times TEXPTIME.
- Use the unchanged sideband-only local linear fit with flux centering,
  robust/formal noise scale and prediction-leverage term.
- Retain both endpoints, +8.5 and -8.5. These scores are not calibrated
  Gaussian significances. Do not apply an event-flag veto.
- Cluster each sign separately by overlapping or adjacent event intervals.
  Choose representatives by largest signed score, then shortest duration,
  then earliest start. Retain all members and all eligible window values.
- Independently decode raw 138-byte big-endian rows, solve scalar normal
  equations, and verify eligibility, scores, both cluster sets and summaries.
  Preserve tolerances relative 2e-8 and absolute 2e-10. Keep any audit failure.

The LS8I screen/audit wrappers are reused with target and output paths changed;
the new acquisition adds exact byte-count and saved-header checksum checks.
The existing stable-arithmetic known-answer tests run before target values.
The report displays both complete retained tables and all eligible scores;
visit-median normalization is for plotting only and never enters the screen.

## Stopping rules

A zero-eligible visit is a valid fixed result. If either signed endpoint is
crossed, preserve every positive and negative representative and prepare one
separately frozen CAL/COR metadata-and-image follow-up for all of them. Do not
open any image merely because this screen finishes. If neither endpoint is
crossed, close this pair without adding later WASP-189 visits; next consider
rank 2 of the unchanged LS8J ledger under its own exact-pair/header freeze.

On audit failure, preserve original outputs and diagnose only already retained
data before any further acquisition. No alternate aperture, image, raw
imagette, additional WASP-189 visit, unused TESS sector or M43 held-out panel
is in scope. No detector qualification, SETI candidate, false-alarm probability,
completeness or new qualified observing coverage follows from this screen.
