# LS8S — frozen TESS_260647166 two-visit DEFAULT-L2 screen

Status: **EXACT SCIENCE SCOPE FROZEN BEFORE TABLE VALUES**.
Pair/header freeze: `ff8ec675b51f1869f85dfdf76426f056d938eff7`.
Public header result: `282effbcd95efe7c2269f44dd66d53a67c92f469`,
**PASS_COMPATIBLE** after 40,320 header bytes and zero science-table bytes.
Both products have PIPE 14.1.2, NEXP=1 and the complete compatible
18-field/138-byte schema. EXPTIME and TEXPTIME agree within each product:
42 seconds in the first visit and 49 seconds in the second.

| Exact file key | Rows | Zero-based table start | Table bytes | Inclusive final byte |
|---|---:|---:|---:|---:|
| CH_PR300046_TG000101_V0300 | 983 | 20160 | 135654 | 155813 |
| CH_PR100031_TG015701_V0300 | 764 | 20160 | 105432 | 125591 |

Acquire exactly these two DEFAULT table intervals, **241,086 bytes** total.
`config/ls8s_l2_scope.json` records complete source identities, ETags, total
sizes, filenames, headers/schema and hash pins. Verify those pins, the full
header manifest, executing freeze HEAD and clean tracked tree before values.
Require HTTP 206, exact Content-Range and Content-Length, matching ETag and
filename. Preserve failures and acquired bytes without substituting or
expanding products after an identity, transport or schema failure.

## Unchanged screen and independent audit

Thin LS8S path/key adapters invoke the unchanged hash-pinned LS8K acquisition,
eligibility, stable scorer and signed clustering, and its independent scalar
auditor. Each uses the verified TEXPTIME of the current visit. No numerical
source, threshold, cluster or tolerance is changed.

- Durations: one/two/three rows, exactly 42/84/126 seconds of integrated
  exposure in the first visit and 49/98/147 seconds in the second.
- Sidebands: 12 rows on each side; guards: two rows each side.
- Entire context: finite BJD/FLUX/FLUXERR, FLUXERR>0 and STATUS=0; adjacent
  BJD steps within 0.5–1.5 of that visit's TEXPTIME. Do not bridge gaps.
  EVENT is reported, not an extra veto.
- Sideband-only flux-centered linear baseline, original robust/formal
  noise and prediction leverage, signed endpoints +8.5 and -8.5.
- Cluster signs separately by overlapping/adjacent event intervals. Keep
  every member; select the largest signed score, shorter duration, then
  earlier start. Retain every eligible window and signed representative.
- Run both existing stable-arithmetic known-answer tests before values.
  Independently decode the 138-byte rows, enumerate eligible contexts, solve
  scalar normal equations and verify scores, clusters and summary counts.
  Keep exact discrete rules and relative 2e-8 / absolute 2e-10 tolerances.
- Plot both complete retained tables and all eligible signed scores. Median
  normalization is for display; scoring uses local baselines in electrons.

No previous image label, residual weighting, covariance model, alternative
aperture or hypothetical displacement subtraction becomes a detection rule.
Scores are not Gaussian significances or calibrated false-alarm probabilities.
Overlapping windows are not independent trials. No completeness, short-glint
sensitivity, population limit, qualified candidate/detector or additional
qualified observing coverage follows from this descriptive screen.

## Complete outcomes and stop

A zero-eligible visit remains a valid outcome. Any cluster of either sign
requires one separately frozen CAL/COR diagnostic retaining **all** signed
representatives. Verify exposure metadata joins, then freeze exact image and
smearing ranges before values. This L2 scope authorizes zero image bytes.

If neither endpoint is crossed, close this pair as a descriptive null without
new visits or threshold changes. The next unchanged ledger cohort is rank 5,
EC 12578-2107, pair CH_PR100002_TG008901_V0300 and
CH_PR100002_TG008902_V0300; it requires separate header/science freezes.

On audit failure, preserve the original run and diagnose the saved tables
before any further acquisition or promotion. Publish ranges, receipts,
complete eligible/signed results, independent audit, figure, report, logs,
environment and checksums. TESS_260647166 here names CHEOPS products;
reserved TESS sectors and M43 panels remain closed. Closed HD 136352,
GJ 1132 and WASP-189 studies remain unchanged. The raw-imagette calibration
request remains unsent. Publication is already authorized.
