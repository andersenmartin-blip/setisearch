# LS8AK — PG 1343-102 null result and exact continuation

22 September 2026. The rank-12 pair is **COMPLETE_AUDITED and closed**.
The unchanged signed screen has no threshold crossing in its eligible windows.

## Complete light-curve result

Both visits have separately verified NEXP=1, EXPTIME=TEXPTIME=60 seconds
and pipeline 14.1.2. All 176 table rows remain available; 173 have finite
required values, positive flux error and STATUS=0. Eligibility additionally
requires the complete event, sidebands, guards and cadence checks.

| Visit | Rows | STATUS=0 finite rows | Eligible windows | Minimum score | Maximum score | Positive / negative clusters |
|---|---:|---:|---:|---:|---:|---:|
| CH_PR100002_TG008701_V0300 | 86 | 84 | 99 | -3.408216 | +3.403111 | 0 / 0 |
| CH_PR100002_TG008702_V0300 | 90 | 89 | 132 | -3.990887 | +4.025282 | 0 / 0 |
| Total | 176 | 173 | 231 | — | — | 0 / 0 |

| Event duration | TG008701 eligible windows | TG008702 eligible windows | Positive / negative crossings across both visits |
|---|---:|---:|---:|
| 1 row / 60 seconds | 34 | 45 | 0 / 0 |
| 2 rows / 120 seconds | 33 | 44 | 0 / 0 |
| 3 rows / 180 seconds | 32 | 43 | 0 / 0 |

The frozen LS8K method is unchanged: flux-centered local-linear baseline,
12 sideband rows on each side, two-row guards, symmetric +/-8.5 endpoints,
finite BJD/flux/error, positive error and STATUS=0 throughout the required
context. Consecutive cadence must lie within 0.5–1.5 times the visit's
verified cadence. Gaps are not bridged. EVENT is not introduced as a veto.
The complete eligible score tables and both empty signed cluster sets are
preserved; no below-threshold substitute is selected for image analysis.

## Scope of the null and visual review

The retained-table figure shows a large early point in the second visit.
Independent scalar parsing of the retained bytes identifies zero-based
row 10: STATUS=0 and flux/visit median = 1.3445547616059867, approximately
34.46% above that median. Visit-median normalization is for display; it is
not the local baseline used by the screen.

Every one/two/three-row event interval containing row 10 lacks the required
left sideband and guard. The first eligible one-row event is row 14.
Row 10 remains in the data and figure and can contribute to later sidebands
under the original rule; it is not eligible as a tested event. Its physical
cause is unassigned. Flagged rows 17 and 80 in the first visit and row 73
in the second also remain visible. The null therefore describes the
**231 eligible windows**, not an absence of all large changes in all rows.
Neither the edge rule nor the signed threshold is changed after viewing.

The windows overlap and are not independent trials. Scores are not Gaussian
sigma or calibrated false-alarm probabilities. This result does not establish
completeness, sensitivity to glints, population limits or qualified observing
coverage. No image stage is triggered and no SETI candidate is claimed.

## Verification and publication

The header preflight acquired exactly 20,160 primary-plus-L2 header bytes per
product within its frozen 64-KiB-per-product limit, with no table or image
bytes. It verified both product identities and 18-column, 138-byte row schemas.
The separate science freeze authorized bytes 20,160–32,027 (11,868 bytes)
for TG008701 and 20,160–32,579 (12,420 bytes) for TG008702: exactly
**24,288 science-table bytes**. No other aperture, image or raw imagette was
opened. All four archive URL resolutions succeeded on their first attempt;
there was no table retry, source substitution or scientific rerun.

All five inherited URL/transport tests pass before the header acquisition;
the two inherited stable L2 tests pass before science values. The independent
big-endian scalar decoder, separate window enumeration and scalar normal
equations pass **2,772 numerical/discrete comparisons** (1,188 + 1,584),
with zero disagreements. Both complete signed cluster sets and summary
counts agree. Relative tolerance remains 2e-8 and absolute tolerance 2e-10;
the maximum score difference is 1.5543122344752192e-15. No tolerance changes.

Both workflows completed successfully. The four scientific commits add
**62 files**, changing or removing no earlier file. All 62 were locally
verified against published Git blob identities. Every one of the 28 metadata
and 22 L2 manifest entries also passes local SHA256 verification; both
manifests are included in the Git verification. The full light-curve/score
figure was visually inspected. Code, retained bytes, range receipts, audits,
reports, logs, environment records and checksums are public.

[Immutable sequence and verification](PUBLICATION_2026-09-22_LS8AK.md).

## Exact next action

Keep this PG 1343-102 pair closed; TG008703 and TG008704 remain outside it.
Prepare **LS8AL**, the next independent metadata-first transfer to
**rank-13 HD 106315** in the unchanged reconciled LS8J chronology:

| Chronological visit | Exact product key | Start MJD in ledger | Existing exposure tuple |
|---|---|---:|---|
| First | CH_PR100041_TG000801_V0300 | 58933.4583544308 | NEXP=1; EXPTIME=TEXPTIME=41 s; pipeline 14.1.2 |
| Second | CH_PR100041_TG001401_V0300 | 58970.6255582254 | NEXP=1; EXPTIME=TEXPTIME=41 s; pipeline 14.1.2 |

These are the cohort's two eligible visits in the original ledger. Their
science values remain unopened. Freeze the exact pair and header-only budget;
verify identities, schema, row counts and exposure tuples. Then separately
freeze exact DEFAULT-L2 byte ranges before reading values. Transfer the
unchanged one/two/three-row scorer and independent audit using each visit's
own verified cadence: **41/82/123 seconds if the headers confirm the ledger**.
Do not carry the PG 1343-102 60-second assertions into HD 106315.

Any threshold-triggered image follow-up must retain every signed representative,
verify unique metadata joins and separately freeze exact payload ranges before
pixels. No outcome in this closed pair becomes a new screening cut.

The original 1,000-row census, 452 eligible visits and 107-cohort ordering
remain fixed. TESS_260647166's positive, PG1303-114's negative and
PG 1207-033's positive retain their unresolved labels and closed bounded
studies. EC13080-1508, WASP-43, GJ 436 and PG 1245-042 remain closed under
CORRECTION_LINKED. Other closed optical studies and M33 HD 3651 are
unchanged. Reserved TESS/M43 panels remain closed. Calibration is NOT_READY
and its technical request remains unsent. Standing research/publication
authorization continues; delegation remains deferred.

[L2 report and figure](results_ls8ak_l2_screen/REPORT.md) ·
[Independent audit](results_ls8ak_l2_screen/audit.json) ·
[Header protocol](LS8AK_PG1343102_HEADER_PROTOCOL.md) ·
[L2 protocol](LS8AK_PG1343102_L2_PROTOCOL.md) ·
[Current project status](PROJECT_STATUS.md).
