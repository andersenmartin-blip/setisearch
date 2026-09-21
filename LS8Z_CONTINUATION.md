# LS8Y–LS8Z — PG 1245-042 result and exact continuation

21 September 2026. The rank-7 pair's unchanged screen and complete signed
image follow-up are **complete and closed**. Its sole negative representative is
**CORRECTION_LINKED** under the original descriptive gate. No qualified SETI
candidate, detector or observing coverage is added.

## Complete light-curve result

Both visits have verified NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline
14.1.2. The unchanged screen keeps 60/120/180-second events, 12-row sidebands,
two-row guards, original eligibility and symmetric +/-8.5 endpoints.

| Visit | Rows | Eligible overlapping windows | Minimum score | Maximum score | Positive / negative clusters |
|---|---:|---:|---:|---:|---:|
| CH_PR100002_TG008601_V0300 | 85 | 135 | -18.490172 | +3.255699 | 0 / 1 |
| CH_PR100002_TG008602_V0300 | 79 | 93 | -1.689957 | +1.688104 | 0 / 0 |
| Total | 164 | 228 | — | — | 0 / 1 |

Four negative crossings form one cluster. The original representative
**TG008601_N0** is zero-based row 31, one 60-second exposure, score
**-18.490171716816285**, approximately 7.00% below its local fitted L2
baseline. No positive crossing occurs in either visit. Scores are not
Gaussian sigma and overlapping windows are not independent trials. This
screen does not establish sensitivity, completeness or population limits.

Exactly **22,632 science-table bytes** were read. The full cluster membership
and all eligible windows remain preserved; no below-threshold control was
substituted for the fixed representative.

## Image diagnostic and interpretation

The complete signed representative set was frozen before new image metadata.
All 29 original L2 context rows 17:46 have unique CAL/COR exposure matches,
with <=1 ms time differences and agreeing UTC/exposure counters/integrity.
A second public freeze fixed exactly **18,560,000 image bytes plus 46,400
smearing bytes**. No image was acquired for the second visit.

Both original coordinate conventions and the common finite mask are retained.
DELTA=COR-CAL. Image sums below use native ADU, separate from L2 electron units.

| Quantity | C0 | C1 |
|---|---:|---:|
| CAL event residual, aperture sum [ADU] | +19,510.106 | +20,048.337 |
| COR event residual, aperture sum [ADU] | -28,325.362 | -27,924.061 |
| DELTA event residual, aperture sum [ADU] | -47,835.468 | -47,972.398 |
| DELTA / COR | +1.688786 | +1.717959 |
| Column-projected DELTA / COR | +1.607004 | +1.629805 |
| COR brightness explained energy | 12.49992% | 12.27948% |
| COR displacement explained energy | 47.31536% | 47.34618% |

Both conventions have complete apertures and negative COR sums agreeing with
the L2 sign. DELTA/COR is **+1.688786 / +1.717959**; the column-projected
ratios are **+1.607004 / +1.629805**. The direct and column-projected ratios
exceed the predeclared 0.5 threshold in both conventions. The correction gate is evaluated first,
giving **CORRECTION_LINKED** without changing any rule.

The CAL aperture event residual is positive in both conventions, while COR
is negative. The negative delivered correction is larger than the remaining
COR deficit and reverses the aperture residual's sign. This establishes a
material dependence on delivered processing. The responsible physical or
processing component remains unidentified, and source variability is not
excluded. The fixed smearing regression is rank deficient in both conventions
and remains unavailable; no smearing-specific cause is assigned.

Displacement explains about 47.3% of COR residual energy and brightness
about 12.3–12.5%; neither describes all remaining structure. The completed
correction gate is a descriptive stopping rule, not a calibrated false-alarm
or artificial-origin test. Keep this pair closed under that rule.

## Verification and publication

The five existing URL-timeout tests and two inherited stable L2 tests pass.
The L2 audit passes **2,736 numerical/discrete comparisons**. Metadata-only
image checks pass **58 unique joins and 269 exact checks** before pixels.
All nine inherited image tests pass before payload. The independent image
audit passes **94,537 numerical comparisons and 160,581
exact checks**, with no disagreements or changed tolerances. Both figures
were visually inspected.

All 28 L2 metadata files, 22 L2 result files and 57 image metadata files were
locally SHA256/Git-identity verified. Of 22
image-result manifest entries, 20
were also locally verified. The two larger compressed CAL/COR inputs were verified, decompressed and
independently decoded by the successful workflow audit. The connector
exposed their Git identities but returned no binary content for an additional
local copy. Their public files, raw/compressed hashes and exact range receipts
are preserved. This is a local retrieval limitation, not missing science data
or a failed audit.

The original nine-test pre-pixel gate, independent long-double temporal
equations and scalar spatial normal equations are unchanged. Relative
tolerance remains 2e-8; native/dimensionless absolute tolerances remain
1e-6/1e-8. No scientific rerun or result-dependent retuning is needed.

The eight scientific commits add **155 files**, with no earlier file
changed or removed. Exactly 153 match locally calculated Git blob
identities; the publication record explains any separately workflow-verified
compressed inputs. Code, inputs, receipts, maps, audits, reports, environment,
logs and checksums are public. [Immutable sequence and verification](PUBLICATION_2026-09-21_LS8Y_LS8Z.md).

## Exact next action

Keep the PG 1245-042 pair closed, including its five later eligible visits.
Do not change thresholds, apertures or image scope to obtain a physical
explanation. Prepare **LS8AA**, the next independent metadata-first transfer
to **rank-8 WASP-43** in the unchanged reconciled LS8J chronology:

| Chronological visit | Exact product key | Existing ledger |
|---|---|---|
| First | CH_PR100016_TG007801_V0300 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |
| Second | CH_PR100016_TG007802_V0300 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |

These are the cohort's only two eligible visits in the original census.
The exposures are still ledger values requiring header verification. Freeze
the exact pair and header-only budget, verify identities, schema, row counts
and exposure tuples, then separately freeze exact DEFAULT-L2 table ranges
before science values. Transfer the unchanged signed screen and independent
audit. Any triggered image follow-up must retain every signed representative,
establish unique metadata joins and freeze exact payload ranges first.
WASP-43 science values remain unopened at this checkpoint. No LS8Z image
ratio or label becomes a new L2 screening cut.

GJ 436 remains closed under CORRECTION_LINKED. The earlier TESS_260647166
positive remains UNRESOLVED_WITHIN_FIXED_SCOPE and its bounded study closed.
This negative-event diagnostic neither resolves nor discounts that separate
event. Prior closed optical studies and the M33 HD 3651 radio case are
unchanged. Reserved TESS/M43 panels remain closed. Calibration is NOT_READY
and its technical request unsent. Standing research/publication authorization
continues; delegation remains deferred.

[L2 report and figure](results_ls8y_l2_screen/REPORT.md) ·
[Image report and figure](results_ls8z_images/REPORT.md) ·
[Frozen image method](LS8Z_PAIRED_IMAGE_PROTOCOL.md) ·
[Current project status](PROJECT_STATUS.md).
