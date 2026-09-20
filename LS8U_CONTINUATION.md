# LS8U — scientific interpretation and exact continuation

20 September 2026. The single retained-data residual/noise study of
TESS_260647166 is **complete and closed**. The positive TG015701_P0 remains
**UNRESOLVED_WITHIN_FIXED_SCOPE**; the negative TG000101_N0 remains
**SPATIALLY_STRUCTURED** under the original LS8T gate. LS8U characterizes the
remaining structure and local variability; it does not identify a unique
physical cause, qualify a SETI candidate or adopt a detector.

## What the bounded study establishes

Both original contexts, products and coordinate conventions were included.
The positive sums one 49-second exposure, the negative three 42-second
exposures. All 38,400,000 CAL/COR bytes were already retained; **zero new
archive science bytes** were acquired. Original masks, centers, temporal
guards, L2 scores, search thresholds and image-classification gates remain
unchanged. Every aperture contains its original 1,957 pixels.

The table gives the COR combined-model weighted residual energy divided by
its sideband-derived reference energy. Both temporal-noise descriptions are
retained; the correlated model includes exact duration and baseline-estimate
propagation. These quantities are descriptive, not Gaussian significances.

| Event / center | Correlated residual/reference | IID residual/reference | Correlated/IID variance | Held targets >= native | Top 10 weighted residual pixels |
|---|---:|---:|---:|---:|---:|
| Negative TG000101_N0 / C0 | 0.723441 | 0.915097 | 1.264922 | 6/8 | 31.1154% |
| Negative TG000101_N0 / C1 | 0.705153 | 0.889540 | 1.261485 | 6/8 | 32.0361% |
| Positive TG015701_P0 / C0 | 3.797390 | 3.964987 | 1.044135 | 1/24 | 6.4683% |
| Positive TG015701_P0 / C1 | 3.765108 | 3.930198 | 1.043847 | 1/24 | 7.0340% |

**The positive retains a substantial model mismatch.** Its residual/reference
energy is about 3.77–3.80, and the correlated model changes the estimated
variance by only about 4.4%. The standardized residual maps show spatially
extended structure, especially in the outer aperture. The fixed 16–25-pixel
ring accounts for **72.95% / 73.45%** of weighted residual energy. The largest
weighted residual pixel accounts for only **0.7451% / 0.8145%**, at native
coordinate `(77,107)` in both conventions. The unweighted top-ten shares are
about 25.7–25.8%, illustrating why raw and noise-weighted structure must be
reported separately. No ranked pixel or ring is removed or used to refit.

One single-row held target, local row **10**, exceeds the positive's residual
ratio in both COR conventions: **3.896439 / 3.886711**. The same 1/24 count
holds in CAL. This is a local comparison using dependent training sets and
different temporal leverage, not a false-alarm estimate. It neither turns the
event into a candidate nor proves that the whole selected excursion is ordinary
noise. Its original +45.460348286 L2 score remains a screening statistic.

**The negative's residual is modest in aggregate relative to this local
reference.** Accounting for temporal correlation raises its modeled COR
variance by about 26.1–26.5%, and six of eight duration-matched held targets
have at least as much residual/reference energy. Its standardized map still
contains localized residual structure: the largest weighted pixel at
`(114,90)` contributes about **19.86% / 21.21%**. A ratio below one is not a
proof of a complete physical explanation or absence of local defects. The
original displacement label is preserved, without reinterpretation as a cause.

The new weighted fits are a different descriptive calculation from LS8T's
unweighted classification gates. In particular, the positive's original COR
displacement explained energies, **75.76422% / 75.77892%**, still miss the fixed
80% requirement in both conventions. No LS8U measure replaces that requirement.

## Paired products and protection against signal loss

Projecting CAL, COR and DELTA with the same COR combined projector retains
the full energy identity and its signed cross term. For the positive,
weighted CAL/COR residual-energy ratios are **1.000190 / 1.000338**; DELTA/COR
is only **0.000011558 / 0.000030126**, offset by negative cross terms. Thus
the measured residual is already nearly the same in CAL under this projector.
This does not identify an upstream physical cause or assign independent
causal fractions. For the negative, DELTA/COR residual-energy ratios are
**0.031336 / 0.034848**, again with negative cross terms retained.

Both radius-25 apertures have 70 exclusive boundary pixels per convention.
Their signed sums exactly account for each C1−C0 aperture-sum difference.
For the positive COR map that difference is **−10,073.081947 ADU**; for DELTA
it is **+23.723736 ADU**. Complete pixel lists and raw/weighted energy accounts
are retained. No coordinate convention is selected from its outcome.

All **128 signed controls** pass the fixed coefficient-recovery and additive
linearity checks: 48 known-template and 80 compact cases. Hypothetical
displacement-plus-constant subtraction loses **12.79–13.09%** of injected
brightness flux in the positive context and **7.31–7.84%** in the negative,
across CAL/COR and C0/C1. No subtraction, new correction or veto is adopted.
The injections are linear template controls, not a complete physical response
calibration or a demonstration of detector completeness.

## Verification and publication

The protocol, configuration, producer, independent auditor, tests, report and
workflow were frozen publicly at **`4de69b42f8e0982a1964a4378c87c9ba9e6cf745`**
before any new native-derived LS8U calculation. All **18 prospective tests**
pass. The first execution and independent reconstruction both succeed, with
**583,488 numerical comparisons and 625,868 exact checks**, zero disagreements
and unchanged tolerances. Maximum discrepancy is only 0.00010684 of the
applicable numerical tolerance. All eight native product/convention cases,
128 held cases and 128 signed controls are retained.

The complete result is **`6cff907b742f862094131cb6ea4f5499821cba24`**. Workflow
[35531218961](https://github.com/andersenmartin-blip/setisearch/actions/runs/35531218961)
concludes success, with scientific status **COMPLETE_AUDITED_DESCRIPTIVE_ONLY**.
All 22 manifest-listed result files were downloaded from that immutable commit
and checksum verified. Both six-panel figures were visually inspected before
this interpretation; labels, maps, scales and all held controls are legible.
No rerun, tolerance relaxation, source extension or post-result mask adjustment
was used to obtain closure.

## Exact next action

Close this bounded TESS_260647166 study as prospectively specified, preserving
its unresolved positive. Do not extend the pair, tune the templates, suppress
the outer ring, change thresholds or treat the dependent control rank as a
new selection rule. A future reopening would need an independently justified,
separately specified research question and appropriate validation.

Next prepare **LS8V**, a metadata-first independent transfer of the unchanged
DEFAULT-L2 screen to **rank-5 EC 12578-2107** from the unchanged reconciled LS8J
chronology:

| Chronological visit | Exact product key | Existing ledger |
|---|---|---|
| First | CH_PR100002_TG008901_V0300 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |
| Second | CH_PR100002_TG008902_V0300 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |

These are existing ledger values, not newly verified FITS headers. Freeze the
exact pair and header-only byte budget first; verify product identity, schema,
row counts and exposure semantics independently for both visits. Only then
freeze exact DEFAULT-L2 table ranges and the original stable screen before
opening science values. Retain both signs, every eligible window and all
independent audit outcomes. Any image follow-up requires its own metadata joins
and exact payload freeze. Do not transfer LS8U residual ratios or pixel ranks
as screening cuts. Rank-5 science values remain unopened at this checkpoint.

The original LS8J first-1,000 chronology, its complete reconciliation and
cohort order remain unchanged. Closed HD 136352, GJ 1132 and WASP-189 studies
stay closed. Raw imagettes and reserved TESS/M43 evaluation data stay closed;
the calibration gate remains NOT_READY and the technical request remains
unsent. Standing publication authorization continues; delegation stays deferred.

[Frozen protocol](LS8U_RESIDUAL_NOISE_PROTOCOL.md) ·
[Complete report and both figures](results_ls8u_residuals/REPORT.md) ·
[Full diagnostics](results_ls8u_residuals/diagnostics.json) ·
[Audit](results_ls8u_residuals/audit.json) ·
[Publication identities](PUBLICATION_2026-09-20_LS8U.md) ·
[Current status](PROJECT_STATUS.md).
