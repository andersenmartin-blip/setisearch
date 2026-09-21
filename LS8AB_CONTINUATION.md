# LS8AA–LS8AB — WASP-43 result and exact continuation

21 September 2026. The rank-8 pair's unchanged screen and complete signed
image follow-up are **complete and closed**. Its sole positive representative is
**CORRECTION_LINKED** under the original descriptive gate. No qualified SETI
candidate, detector or observing coverage is added.

## Complete light-curve result

Both visits have verified NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline
14.1.2. The unchanged screen keeps 60/120/180-second events, 12-row sidebands,
two-row guards, original eligibility and symmetric +/-8.5 endpoints.

| Visit | Rows | Eligible overlapping windows | Minimum score | Maximum score | Positive / negative clusters |
|---|---:|---:|---:|---:|---:|
| CH_PR100016_TG007801_V0300 | 137 | 174 | -3.370208 | +9.486350 | 1 / 0 |
| CH_PR100016_TG007802_V0300 | 134 | 120 | -2.828537 | +2.311104 | 0 / 0 |
| Total | 271 | 294 | — | — | 1 / 0 |

One positive crossing forms one cluster. The representative **TG007801_P0**
is zero-based row 62, one 60-second exposure, original score
**+9.486349813911296**, approximately 0.78% above the local fitted L2 baseline.
No negative crossing occurs in either visit. Scores are not Gaussian sigma;
overlapping windows are not independent trials. This screen does not establish
sensitivity, completeness or population limits.

Exactly **37,398 science-table bytes** were read. All eligible windows and
the complete signed cluster sets are preserved. No below-threshold event
is substituted or added to the image follow-up.

## Image diagnostic and interpretation

The complete signed representative set was frozen before image metadata.
All 29 original L2 context rows 48:77 have unique CAL/COR exposure matches,
with <=1 ms time differences and agreeing UTC/exposure counters/integrity.
A separate public freeze fixed exactly **18,560,000 image bytes plus 46,400
smearing bytes**. No image was acquired for the zero-crossing second visit.

Both original coordinate conventions and the common finite mask are retained.
DELTA=COR-CAL. Image sums use native ADU, separate from L2 electron units.

| Quantity | C0 | C1 |
|---|---:|---:|
| CAL event residual, aperture sum [ADU] | +25,757.286 | +58,965.302 |
| COR event residual, aperture sum [ADU] | +15,031.572 | +15,529.109 |
| DELTA event residual, aperture sum [ADU] | -10,725.713 | -43,436.193 |
| DELTA / COR | -0.713546 | -2.797082 |
| Column-projected DELTA / COR | -0.854294 | -0.855279 |
| COR brightness explained energy | 0.17463% | 0.17917% |
| COR displacement explained energy | 42.30816% | 42.31091% |

Both conventions have complete 1,963-pixel apertures and positive COR sums
agreeing with L2. DELTA/COR is **-0.713546 / -2.797082**; the corresponding
column-projected ratios are **-0.854294 / -0.855279**. In both conventions
the absolute ratios exceed the original 0.5 threshold. The correction gate
is evaluated first, giving **CORRECTION_LINKED** with no changed rule.

CAL and COR aperture residuals are both positive. The delivered correction
reduces the positive CAL residual by about 10,726 ADU in C0 and 43,436 ADU
in C1, leaving about 15,032 / 15,529 ADU in COR. The substantial difference
between the aperture ratios records sensitivity to the original one-pixel
coordinate convention; neither convention is selected or adjusted after
seeing the event. Both independently satisfy the same fixed closure gate.

This establishes material dependence on delivered processing, not that the
whole remaining event has been physically explained or removed. The
responsible processing component remains unidentified; source variability
is not excluded. The smearing regression is rank deficient in both
conventions and stays unavailable, so no smearing-specific cause is assigned.

The displacement model explains about 42.31% of COR residual energy, versus
0.175–0.179% for brightness. That is below the separate 80% spatial gate;
no spatial closure is claimed. The correction label is a descriptive stopping
rule, not a calibrated false-alarm or artificial-origin test. Keep this pair
closed under the original rule.

## Verification and publication

The five existing URL-timeout tests and two inherited stable L2 tests pass.
The independent L2 audit passes **3,528 numerical/discrete comparisons**.
Image metadata passes **58 unique joins and 269 exact checks** before pixels.
All nine inherited image tests pass before payload. The independent image
audit passes **94,537 numerical comparisons and 160,581
exact checks**, zero disagreements. Both figures were visually inspected.

All 28 L2 metadata files, 22 L2 result files and 57 image metadata files were
locally SHA256/Git-identity verified. Of 22 image-result
manifest entries, 20 were also locally
verified. The two larger compressed CAL/COR inputs were verified, decompressed and
independently decoded by the successful workflow audit. The connector
exposed their Git identities but returned no binary content for an additional
local copy. Their public files, raw/compressed hashes and exact range receipts
are preserved. This is a local retrieval limitation, not missing science data
or a failed audit.

The original pre-pixel test gate, independent long-double temporal equations
and scalar spatial normal equations are unchanged. Image tolerances remain
relative 2e-8, native absolute 1e-6 and dimensionless absolute 1e-8; L2
tolerances remain relative 2e-8 / absolute 2e-10. No scientific retuning occurs.

The eight scientific commits add **155 files**, with
no earlier file changed or removed. Exactly 153 match
locally calculated Git blob identities. The publication record identifies
the separately workflow-verified inputs. Code, inputs, receipts, maps,
audits, reports, environment, logs and checksums are public.
[Immutable sequence and verification](PUBLICATION_2026-09-21_LS8AA_LS8AB.md).

## Exact next action

Keep the WASP-43 pair closed. These were its only two eligible visits in
the original census. Do not expand its image scope, change thresholds or
apertures, or reopen earlier events to obtain a physical explanation.
Prepare **LS8AC**, the next independent metadata-first transfer to
**rank-9 PG1303-114** in the unchanged reconciled LS8J chronology:

| Chronological visit | Exact product key | Start MJD in ledger | Existing exposure tuple |
|---|---|---:|---|
| First | CH_PR100002_TG006401_V0300 | 58957.8692102292 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |
| Second | CH_PR100002_TG006402_V0300 | 58966.6775431798 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |

These are the first two of the cohort's five eligible visits. The other
three remain outside this transfer. Ledger exposure values still require
header verification. Freeze the exact pair and header-only budget; verify
source identities, schema, row counts and exposure tuples. Then separately
freeze exact DEFAULT-L2 table ranges before reading science values, and
transfer the unchanged signed screen and independent audit.

Any triggered image follow-up must preserve every signed representative,
verify unique metadata joins and freeze exact payload ranges before pixels.
PG1303-114 science values remain unopened at this checkpoint. No LS8AB image
ratio or label becomes a new L2 screening cut. The original 1,000-row census,
452 eligible visits and 107-cohort chronology remain fixed.

The earlier TESS_260647166 positive remains UNRESOLVED_WITHIN_FIXED_SCOPE
and its bounded study closed. GJ 436 and PG 1245-042 remain closed under
CORRECTION_LINKED. Other closed optical studies and M33 HD 3651 are unchanged.
Reserved TESS/M43 panels remain closed. Calibration is NOT_READY and its
technical request unsent. Standing research/publication authorization
continues; delegation remains deferred.

[L2 report and figure](results_ls8aa_l2_screen/REPORT.md) ·
[Image report and figure](results_ls8ab_images/REPORT.md) ·
[Frozen image method](LS8AB_PAIRED_IMAGE_PROTOCOL.md) ·
[Current project status](PROJECT_STATUS.md).
