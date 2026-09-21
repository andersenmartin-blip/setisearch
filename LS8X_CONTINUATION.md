# LS8W–LS8X — GJ 436 complete and exact continuation

21 September 2026. The predetermined rank-6 CHEOPS pair and its complete
signed image follow-up are **complete and closed**. The single positive
representative is **CORRECTION_LINKED** under the unchanged descriptive
gate. No qualified SETI candidate, detector or observing coverage is added.

## Light-curve result

Both selected visits have separately verified NEXP=1 and
EXPTIME=TEXPTIME=60 seconds, pipeline 14.1.2. The unchanged DEFAULT-L2
screen retains one-, two- and three-row events, 12-row sidebands on each
side, two-row guards, the original eligibility rules and symmetric +/-8.5
endpoints. It reads exactly **88,320 science-table bytes**.

| Visit | Rows | Eligible overlapping windows | Minimum score | Maximum score | Positive / negative clusters |
|---|---:|---:|---:|---:|---:|
| CH_PR100041_TG000302_V0300 | 340 | 558 | -3.267208 | +9.634235 | 1 / 0 |
| CH_PR100041_TG001301_V0300 | 300 | 378 | -3.569204 | +7.895926 | 0 / 0 |
| Total | 640 | 936 | — | — | 1 / 0 |

There is exactly one positive crossing, at zero-based row 33 of the first
visit: **TG000302_P0**, one 60-second exposure, original score
**+9.634235209975396**. Its excess is approximately 0.253% of the fitted
local L2 baseline. No negative crossing occurs in either visit. The score
is not Gaussian sigma; overlapping windows are not independent trials.
These descriptive counts do not establish sensitivity or completeness.

## Fixed image outcome and its limits

The complete signed representative set was frozen before image metadata.
Separate metadata checks established **58 unique CAL/COR exposure joins**
for the original context rows 19:48, before any pixels. A second public
freeze fixed the exact **18,560,000 paired-image bytes plus 46,400 smearing
bytes**. No image was acquired for the second visit.

The unchanged temporal maps and spatial models retain both original
coordinate conventions, complete 25-pixel-radius apertures and the common
finite mask. DELTA is COR minus CAL. All entries below refer to native image
ADU, separately from the L2 electron-valued measurement.

| Quantity | C0 | C1 |
|---|---:|---:|
| CAL event residual, aperture sum [ADU] | +122,940.669 | +124,682.991 |
| COR event residual, aperture sum [ADU] | +39,796.050 | +41,538.263 |
| DELTA event residual, aperture sum [ADU] | -83,144.619 | -83,144.728 |
| DELTA / COR | -2.089268 | -2.001642 |
| Column-projected DELTA / COR | -0.657541 | -0.639677 |
| COR brightness explained energy | 3.82004% | 3.78564% |
| COR displacement explained energy | 39.02952% | 39.02890% |

Both conventions preserve the positive COR sign and a complete aperture.
Both absolute DELTA/COR ratios exceed the predeclared 0.5 correction gate;
the column-projected ratios also pass. The correction gate is evaluated
first, so the fixed classification is **CORRECTION_LINKED**.

The negative DELTA means the delivered correction reduces a larger positive
CAL event residual. It does **not** show that processing created the original
positive event, identify one physical cause, or exclude source variability.
The separate smearing regression is rank deficient in both conventions and
remains unavailable; no smearing-specific cause is claimed. Neither the
brightness nor displacement fit accounts for all remaining COR structure.
The gate is a descriptive stopping rule, not an artificial-origin detector.
Keep this pair closed without widening its scope to force a causal account.

## Verification and publication

The five bounded URL-timeout tests and both inherited stable L2 tests pass.
The L2 audit passes **11,232 numerical/discrete comparisons**. All **nine
inherited image tests** pass before image access in the full workflow.
The metadata audit passes **269 exact checks**; the image audit independently
decodes retained bytes and passes **94,537 numerical comparisons and
160,581 exact checks**, with no disagreements and unchanged tolerances.
All URL resolutions and science-range requests succeed on their first
attempt. No scientific recovery or retuning is needed.

All 28 L2 metadata files, 22 L2 result files and 57 image metadata files
were locally checksum verified. Of 22 image-result manifest entries,
20 were also locally checksum verified. The two larger compressed CAL/COR
inputs were verified, decompressed and independently decoded by the successful
workflow audit; the connector could expose their Git identities but could
not return their binary contents for an additional local copy. Their raw
and compressed hashes, range receipts and public files are preserved.
This is a local retrieval limitation, not a missing science input or audit.
Both the L2 and CAL/COR/DELTA figures were visually inspected.

The complete eight-commit scientific sequence adds 157 files and changes
no earlier file. Of these, 155 match independently calculated local Git
blob identities; the two remaining identities are the compressed inputs
described above. Immutable commits, workflows, identities and verification
scope are recorded in [the publication record](PUBLICATION_2026-09-21_LS8W_LS8X.md).

## Exact next action

Prepare **LS8Y**, a separate metadata-first transfer to **rank-7 PG 1245-042**
from the unchanged reconciled LS8J chronology:

| Chronological visit | Exact key | Existing ledger |
|---|---|---|
| First | CH_PR100002_TG008601_V0300 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |
| Second | CH_PR100002_TG008602_V0300 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |

These are the first two of seven eligible visits in the original cohort.
The listed exposures remain ledger values requiring header verification.
Freeze the exact pair and header-only budget, verify identity, schema,
exposure tuple and row counts, then separately freeze exact DEFAULT-L2
table ranges before science access. Transfer the unchanged signed screen
and independent audit. Any triggered image follow-up needs its own complete
representative set, exposure joins and exact payload freeze. PG 1245-042's
science values remain unopened at this checkpoint.

Do not adopt LS8X correction ratios as a new L2 selection cut. The earlier
TESS_260647166 positive remains UNRESOLVED_WITHIN_FIXED_SCOPE and its bounded
study remains closed. Prior closed optical studies and the M33 HD 3651 radio
case are unchanged. Reserved TESS/M43 panels remain closed. The raw-imagette
calibration gate remains NOT_READY and its technical request unsent. Standing
research and publication authorization continues; delegation remains deferred.

[L2 report and figure](results_ls8w_l2_screen/REPORT.md) ·
[Image report and figure](results_ls8x_images/REPORT.md) ·
[Frozen image method](LS8X_PAIRED_IMAGE_PROTOCOL.md) ·
[Current project status](PROJECT_STATUS.md).
