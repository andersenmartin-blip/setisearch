# LS8V — completed EC 12578-2107 screen and exact continuation

21 September 2026. The rank-5 two-visit DEFAULT-L2 screen is **complete and
closed**, with **zero positive and zero negative threshold crossings**.
No CAL/COR image follow-up is triggered by the fixed rule. No qualified
SETI candidate, detector or observing coverage is claimed.

## Result and its limits

Both predetermined CHEOPS visits have NEXP=1 and EXPTIME=TEXPTIME=60 seconds.
The unchanged screen considered one-, two- and three-row events, corresponding
to 60, 120 and 180 seconds of integrated exposure. Every eligible window was
retained, with the original two-row guards, 12-row sidebands, status/cadence
requirements and symmetric +/-8.5 endpoints.

| Visit | Retained rows | Eligible windows | Minimum score | Maximum score | Positive / negative clusters |
|---|---:|---:|---:|---:|---:|
| CH_PR100002_TG008901_V0300 | 87 | 36 | -1.649202 | +1.405440 | 0 / 0 |
| CH_PR100002_TG008902_V0300 | 87 | 165 | -5.420897 | +4.891934 | 0 / 0 |
| Total | 174 | 201 | — | — | 0 / 0 |

The first visit contributes eligible event centers in only 13 distinct rows;
the second contributes 56. Their event-row unions total 69 minutes of nominal
integration. This is descriptive bookkeeping, **not qualified observing
coverage** or 201 independent trials. Baselines, guards, flagged samples and
gaps restrict which rows can participate. The score is not Gaussian sigma.
The null does not establish completeness, sensitivity to short glints or a
population limit, and does not imply that the target is intrinsically constant.

Exactly 24,012 science-table bytes were acquired. No other aperture, later
visit, CAL/COR image or raw imagette was opened. The original metadata-only
selection and all 107 reconciled cohort positions remain unchanged.

## First failure and successful bounded recovery

The header freeze `91dce63e208e126affe519077a9bf571263a8810` preceded all new
headers. The metadata result `1eb452464982af7bd23e67bca33d429000297a2a`
passed both products and the reference schema. All 26 manifest-listed
metadata files were retrieved and verified; separate scalar FITS-card checks
confirmed the row counts and 60-second exposure semantics.

The initial science freeze was `b2b185f8a592e8ae465fa396e96be746e76ecf4c`.
Its first execution stopped during TLS URL resolution before any table
request. That genuine failure remains at
`d6703a70572eb70c0e028808c8be9e20c73de63e` under
`results_ls8v_l2_screen/`; it is not relabeled as a success or a null result.

A public transport-only recovery was frozen at
`e3dfd9b6cc82134c770b89469f11e99b1a060f4f`. It preserved the failed output,
original exact byte ranges, source identities, numerical code and thresholds.
The bounded wrapper allowed at most three URL-resolution timeout attempts;
both products resolved on the first attempt in this recovery. The science
HTTP requests retained all original identity/range checks and no retry.

The complete result is `94c679a6b460d5911fedc847a656eed630b72d47` under
`results_ls8v_l2_recovered/`. Both existing known-answer tests pass. The
independent scalar audit passes **2,412 numerical/discrete comparisons**, with
zero disagreements and unchanged tolerances. Its largest absolute score
discrepancy is 6.66e-15. All **20 result files** match their immutable SHA256
manifest and Git identities. The four-panel figure was visually inspected:
both complete light curves, flagged samples, score series and thresholds are
legible. No scientific rerun or retuning was needed.

The complete six-commit study added 67 files relative to the LS8U checkpoint;
every added file was byte-verified against GitHub. No earlier file was changed
or removed by those study commits. The separate documentation closure records
these outcomes and updates the active continuation.

## Exact next action

Keep this EC 12578-2107 pair closed. Do not open its five later eligible visits
or alter thresholds because the fixed screen was empty. Prepare **LS8W**, a
separate metadata-first transfer to **rank-6 GJ 436** in the unchanged LS8J
chronology:

| Chronological visit | Exact product key | Existing ledger |
|---|---|---|
| First | CH_PR100041_TG000302_V0300 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |
| Second | CH_PR100041_TG001301_V0300 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |

These are the cohort's only two eligible visits in the original census.
The exposure entries remain **ledger values**, not newly checked FITS headers.
Freeze the exact pair and header-only budget, verify both product identities,
schemas, row counts and exposure tuples, then separately freeze the exact
DEFAULT-L2 ranges before values. Transfer the unchanged screen and independent
audit, retaining both signs and all outcomes. Any image follow-up needs its
own metadata joins and exact payload scope. GJ 436 science values remain
unopened at this checkpoint.

The earlier TESS_260647166 positive remains UNRESOLVED_WITHIN_FIXED_SCOPE;
its negative remains SPATIALLY_STRUCTURED. LS8V's empty result neither resolves
nor discounts that separate event. Closed HD 136352, GJ 1132 and WASP-189
studies and the M33 HD 3651 radio case are unchanged. Reserved TESS/M43 data
remain closed. The raw-imagette calibration gate remains NOT_READY and its
request unsent. Standing publication authorization continues; delegation is
deferred.

[Audited report and figure](results_ls8v_l2_recovered/REPORT.md) ·
[Original L2 protocol](LS8V_EC125782107_L2_PROTOCOL.md) ·
[Preserved failure and recovery](LS8V_TRANSPORT_RECOVERY.md) ·
[Publication identities](PUBLICATION_2026-09-21_LS8V.md) ·
[Current project status](PROJECT_STATUS.md).
