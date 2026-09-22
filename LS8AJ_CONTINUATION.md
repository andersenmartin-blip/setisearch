# LS8AI–LS8AJ — EC13080-1508 result and exact continuation

22 September 2026. The rank-11 pair's unchanged screen and complete signed
image follow-up are **complete and closed**. Its sole negative representative is
**CORRECTION_LINKED** under the original descriptive gate. No qualified SETI
candidate, detector or observing coverage is added.

## Complete light-curve result

Both visits have verified NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline
14.1.2. The unchanged screen keeps 60/120/180-second events, 12-row sidebands,
two-row guards, original eligibility and symmetric +/-8.5 endpoints.

| Visit | Rows | Eligible overlapping windows | Minimum score | Maximum score | Positive / negative clusters |
|---|---:|---:|---:|---:|---:|
| CH_PR100002_TG005201_V0300 | 93 | 192 | -13.170392 | +3.659851 | 0 / 1 |
| CH_PR100002_TG005202_V0300 | 86 | 96 | -7.294181 | +3.747225 | 0 / 0 |
| Total | 179 | 288 | — | — | 0 / 1 |

Four negative crossings form one cluster. The representative **TG005201_N0**
is zero-based row 65, one 60-second exposure, original score
**-13.17039181262956**, approximately 3.97253% below the local fitted L2 baseline.
No positive crossing occurs in either visit. Scores are not Gaussian sigma;
overlapping windows are not independent trials. This screen does not establish
sensitivity, completeness or population limits.

Exactly **24,702 science-table bytes** were read. All eligible windows and
the complete signed cluster sets are preserved. No below-threshold event
is substituted or added to the image follow-up.

## Image diagnostic and interpretation

The complete signed representative set was frozen before image metadata.
All 29 original L2 context rows 51:80 have unique CAL/COR exposure matches,
with <=1 ms time differences and agreeing UTC/exposure counters/integrity.
A separate public freeze fixed exactly **18,560,000 image bytes plus 46,400
smearing bytes**. No image was acquired for the zero-crossing second visit.

Both original coordinate conventions and the common finite mask are retained.
DELTA=COR-CAL. Image sums use native ADU, separate from L2 electron units.

| Quantity | C0 | C1 |
|---|---:|---:|
| CAL event residual, aperture sum [ADU] | -63,227.768 | -63,096.835 |
| COR event residual, aperture sum [ADU] | -14,434.939 | -14,296.235 |
| DELTA event residual, aperture sum [ADU] | +48,792.829 | +48,800.600 |
| DELTA / COR | -3.380189 | -3.413528 |
| Column-projected DELTA / COR | -3.015552 | -3.059442 |
| COR brightness explained energy | 2.95393% | 2.89890% |
| COR displacement explained energy | 70.23305% | 70.32761% |

Both conventions have complete 1,958-pixel apertures and negative COR sums
agreeing with L2. DELTA/COR is **-3.380189 / -3.413528**; the corresponding
column-projected ratios are **-3.015552 / -3.059442**. In both conventions
the absolute ratios exceed the original 0.5 threshold. The correction gate
is evaluated first, giving **CORRECTION_LINKED** with no changed rule.

CAL and COR aperture residuals are both negative. The delivered correction
adds approximately 48,793 / 48,801 ADU, reducing CAL deficits of about
63,228 / 63,097 ADU to COR deficits of about 14,435 / 14,296 ADU.
The correction has the opposite sign to the remaining event and exceeds
its magnitude by more than a factor of three in both conventions. Neither
aperture or coordinate convention is selected or adjusted after the result.

This establishes material dependence on delivered processing. It does not
identify the responsible correction component, explain the entire remaining
light-curve deficit, or exclude source variability. The fixed smearing
regression is rank deficient in both conventions and remains unavailable;
no smearing-specific cause is assigned.

Displacement explains 70.23% / 70.33% of COR residual energy, compared with
2.95% / 2.90% for brightness. This does not reach the separate 80% spatial
gate. The correction label is a descriptive stopping rule, not a calibrated
false-alarm or artificial-origin test. Keep this pair closed under that rule;
no additional retained-data study is required by the frozen decision sequence.

## Verification and publication

The five existing URL-timeout tests and two inherited stable L2 tests pass.
The independent L2 audit passes **3,456 numerical/discrete comparisons**.
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
[Immutable sequence and verification](PUBLICATION_2026-09-22_LS8AI_LS8AJ.md).

## Exact next action

Keep the EC13080-1508 pair closed. Its third eligible visit,
CH_PR100002_TG005203_V0300, remains outside this transfer. Do not expand image
scope, alter thresholds or apertures, or reopen earlier events to force a
physical explanation. Prepare **LS8AK**, the next independent metadata-first
transfer to **rank-12 PG 1343-102** in the unchanged reconciled LS8J chronology:

| Chronological visit | Exact product key | Start MJD in ledger | Existing exposure tuple |
|---|---|---:|---|
| First | CH_PR100002_TG008701_V0300 | 58966.2226830580 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |
| Second | CH_PR100002_TG008702_V0300 | 58969.6386530057 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |

These are the first two of four eligible visits. TG008703 and TG008704
remain outside this transfer. Ledger exposures still require separate header
verification. Freeze the exact pair and header-only budget; verify source
identities, schema, row counts and exposure tuples. Then separately freeze
exact DEFAULT-L2 table ranges before science values, and transfer the unchanged
signed screen and independent audit.

Any triggered image follow-up must preserve every signed representative,
verify unique metadata joins and freeze exact payload ranges before pixels.
PG 1343-102 science values remain unopened at this checkpoint. No LS8AJ image
ratio or label becomes a new L2 screening cut. The original 1,000-row census,
452 eligible visits and 107-cohort chronology remain fixed.

The earlier TESS_260647166 positive remains UNRESOLVED_WITHIN_FIXED_SCOPE
and its bounded study closed. PG1303-114’s negative and PG 1207-033’s positive also retain their unresolved
labels and closed bounded studies. WASP-43, GJ 436 and PG 1245-042 remain
closed under CORRECTION_LINKED. Other closed optical studies and M33 HD 3651 are unchanged.
Reserved TESS/M43 panels remain closed. Calibration is NOT_READY and its
technical request unsent. Standing research/publication authorization
continues; delegation remains deferred.

[L2 report and figure](results_ls8ai_l2_screen/REPORT.md) ·
[Image report and figure](results_ls8aj_images/REPORT.md) ·
[Frozen image method](LS8AJ_PAIRED_IMAGE_PROTOCOL.md) ·
[Current project status](PROJECT_STATUS.md).
