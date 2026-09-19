# LS8C: fixed retrospective diagnosis of eight LS8B representatives

Prepared 19 September 2026. Publish this protocol, configuration, producer,
independent audit and synthetic tests before calculating auxiliary diagnostics.
The LS8B data are already closed. This freeze controls diagnostic flexibility;
it does not make these data an independent test.

## Inputs and scope

Use only the four already retained DEFAULT-L2 binary tables with the exact
SHA-256 identities in `config/ls8c_auxiliary.json`. Select exactly the seven
positive representatives and one negative representative already recorded in
LS8B, in their original order. The fourth visit has no selected representative;
verify its identity without selecting a new window. Preserve all original
screening outcomes and the original LS8B audit FAIL.

For each event starting at zero-based row s and lasting d rows, the context
is [s-14,s+d+14), event rows are [s,s+d), and sidebands are [s-14,s-2) and
[s+d+2,s+d+14). Both two-row guards are excluded from every fit. All 24 side
rows have equal weight. No data acquisition, image opening, alternative
aperture, threshold change, representative replacement or new cluster search.

## Column semantics

The saved tables declare SCI_COR_Lightcurve version 13.1. The matching public
[CHEOPS common software schema, pinned commit 1e45b3b](https://github.com/davefutyan/common_sw/blob/1e45b3be84edd18a60e9a0ea8ef65444dfa2a254/fits_data_model/resources/SCI_COR_Lightcurve.fsd)
has Git blob `e0f42d2ee4898cd2e19ffc8ae40b00734445eff0`. It defines:

| Columns | Native unit / meaning |
|---|---|
| FLUX, DARK, BACKGROUND, SMEARING_LC | electrons |
| CONTA_LC | contaminating flux / target flux |
| CONTA_LC_ERR, SMEARING_LC_ERR | ratio, exactly as declared by this schema |
| ROLL_ANGLE | mean roll angle, degrees |
| LOCATION_X/Y | intended target position, CCD SOC pixels |
| CENTROID_X/Y | calculated target position, CCD SOC pixels |

Retain the unusual SMEARING_LC_ERR unit as declared; do not assume it is an
electron uncertainty. The column schema alone does not establish whether an
electron quantity is per pixel or per aperture, nor the exact DRP correction
operator. Do not add auxiliary columns to FLUX, multiply contamination by
FLUX to invent a correction, or interpret their residuals as recovered raw
flux. Position estimators can respond to source brightness and other image
structure; a centroid association does not establish an independent cause.

## Frozen diagnostics

For every field in the table above, and OFFSET_X/Y = CENTROID_X/Y minus
LOCATION_X/Y, use exactly the same linear time trend fitted on the sidebands.
Times are seconds relative to the first event BJD. Center each series on the
median sideband value before fitting to avoid cancellation at large offsets.
ROLL_ANGLE is unwrapped in time order across the full context, retaining the
first value and placing each subsequent angular difference in [-180,180).

Save all context values, fitted baseline and residuals, event mean, mean
predicted baseline, event residual sum and mean, sideband residual RMS,
1.4826 times the median absolute deviation from the median side residual, and
fitted slope. Define a roundoff floor as 64*binary64_epsilon times
max(1,maximum absolute context value). The descriptive MAD displacement is
event mean residual / side MAD, only if MAD exceeds that floor; otherwise it
is explicitly unavailable. This is not a z-score, probability or new cut.
Any nonfinite required context value makes that entire field unavailable;
do not drop or impute rows. A rank-deficient time fit is also unavailable.

For DARK, BACKGROUND, CONTA_LC, SMEARING_LC, ROLL_ANGLE and OFFSET_X/Y only,
also report a separate single-field coupling to FLUX. Fit beta = sum(a*f) /
sum(a*a) on their **sideband trend residuals only**. Record side correlation,
beta times the auxiliary event mean residual, the remaining FLUX mean
residual, and predicted fraction of the observed FLUX mean residual. Do not
combine predictors, choose a preferred predictor, fit on event values, or use
these fits to change any screening label. A coupling is unavailable when
either side RMS is at/below its roundoff floor. A fraction is unavailable if
the absolute event FLUX residual is at/below its floor. Fractions may be
negative or exceed one: they are extrapolations, not explained-variance or
causal fractions. Multiple testing and model uncertainty are not calibrated.

Finally report the Euclidean norm of the two OFFSET event mean residuals in
pixels. This is the norm of the mean displacement vector, not the average
distance of individual rows. Report all eight representatives and every
predeclared field, including zero-scatter and missing outcomes.

## Audit, presentation and stopping

Independently decode the raw 138-byte rows with `struct`, then calculate a
60-decimal scalar reference using normal equations. Independently verify
all representative identities, context indices, units, availability states,
all time samples and all scalar/vector diagnostic outputs. Compare the eight
FLUX residual sums with the existing LS8B 60-decimal ledger.

For native-unit values require absolute difference <= 1e-9*abs(reference)
+ 512*binary64_epsilon*max(1, maximum absolute native context value,
abs(reference)). For slopes the native context scale is the conservative
absolute budget. For coupling beta use scale 1; for predicted/remaining flux
use the native FLUX context scale. For correlations, fractions and MAD
displacements require difference <= 1e-7 + 1e-8*abs(reference). These are
arithmetic agreement tolerances, not scientific thresholds. They are fixed
before auxiliary calculation and do not replace the historical LS8B gate.
Preserve failures and resolve any concrete implementation error explicitly.

Synthetic known-answer tests cover a large baseline with tiny signed pulses,
trend removal, event/guard exclusion from coupling, circular wrap and its
half-turn tie, unavailable/constant fields, and common intended/measured
motion cancellation. Retain output, audit, CSV, checksums and offline command
instructions. Produce native-unit event/context plots and a complete compact
summary table. Use no significance ranking or automatic instrumental veto.

Stop after this closed-data diagnosis and its independently checked report.
All eight retain the status L2_ONLY_UNRESOLVED; this stage does not classify
them as astrophysical, artificial or uniquely instrumental. If spatial image
information is justified, describe a separate bounded CAL/COR follow-up and
freeze its exact file, byte and row scope before image access. No follow-up
download is part of LS8C. The separate raw-imagette gate remains NOT_READY;
the technical request stays unsent, and unused TESS/M43 panels stay closed.
