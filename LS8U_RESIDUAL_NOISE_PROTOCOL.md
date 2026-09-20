# LS8U — retained TESS_260647166 residual and duration-matched noise study

Status: **FROZEN_BEFORE_NEW_NATIVE_DERIVED_CALCULATION**. This protocol, the JSON
configuration, producer, independent auditor, report, tests and workflow must be
published together before execution. The recorded Actions `GITHUB_SHA` is the
freeze identity; the producer requires that exact clean tracked checkout.

## Question and complete fixed scope

This is the single bounded follow-up authorized by `LS8T_CONTINUATION.md` at
`7e76ab3a8d3b3e0870a7963bf921b22655e45d6f`. It asks how much image structure remains
after the fixed brightness/displacement fits, how it compares with local
duration-matched sidebands, and how hypothetical displacement subtraction would
attenuate injected signals. It is a retrospective descriptive study, not a new
search, classifier, significance calibration or technical-origin test.

All inputs were published before this protocol: LS8T image result
`3e0bd85cee4b191f4bbe82b499977976c1b1484a` and LS8S L2 result
`cc05ba9a55a98bcfe6e1c747820ec4dd3265617f`. Exact SHA-256 pins are in
`config/ls8u_residuals.json`; the complete pinned LS8T manifest is verified before
calculation. Decompression receipts also verify the original raw cube digests.

| Context | Native rows (zero based) | Local event | Native exposure | Retained context | Held targets | Original LS8T label |
|---|---|---|---|---|---|---|
| TG000101_N0 | 317–319 | 14–16 | 3 × 42 s, NEXP=1 | 303:334, 31 rows | Eight 3-row blocks | SPATIALLY_STRUCTURED |
| TG015701_P0 | 217 | 14 | 1 × 49 s, NEXP=1 | 203:232, 29 rows | Twenty-four 1-row blocks | UNRESOLVED_WITHIN_FIXED_SCOPE |

The first key is `CH_PR300046_TG000101_V0300`; the second is
`CH_PR100031_TG015701_V0300`. Both CAL and COR, both C0 and C1 coordinate
conventions, all original finite pixels and the original radius-25 apertures are
mandatory. The existing 38,400,000 uncompressed CAL/COR bytes are reused. New
source/archive bytes authorized: **zero**. No extra visit, raw imagette or
extension of either context is allowed. SMEAR products are manifest-verified but
their original rank-deficient fits are not changed or repaired.

## Temporal residual and exact duration propagation

For duration `d`, the original 24 training rows are `0:12` and
`(16+d):(28+d)`; the native target is `14:(14+d)`. The two rows immediately before
and after the native event remain excluded. Actual BJD times, converted to
seconds relative to local row 14, enter an intercept-plus-linear-time OLS fit
at each pixel. The event image is the **sum** of the `d` target residuals, never
their mean. Subtracting a training-only median before fitting is a numerical
centering operation and does not change the model.

For training size `n`, centered training times `u`, and
`q = sum(target times − mean training time)`, residual weights are 1 on the
target, `−d/n − q*u/sum(u²)` on training, and zero elsewhere. The exact IID
variance multiplier is `wᵀw = d + d²/n + q²/sum(u²)`. In particular, three rows
must not receive a single-row noise normalization.

The correlated reference uses the validated LS8P construction, with the nominal
cadence set prospectively to 42 or 49 seconds for the corresponding context:

1. Compute training OLS residuals and initial per-pixel variance `SSE/(n−2)`
   inside the unchanged aperture. Standardize each residual by the square root
   of the 50/50 mixture of its variance and the across-pixel median variance.
2. Estimate pooled lag-1 and lag-2 correlations from these standardized residuals
   only. Both numerators share the same total sum-of-squares denominator; apply
   Bartlett tapers 2/3 and 1/3. Missing training rows are implicit zeros in the
   biased autocorrelation. They are never compressed into new neighboring rows.
3. Break cadence segments at adjacent time differences outside `[0.5, 1.5]`
   times the nominal cadence. Lag pairs cannot cross such gaps. The full `R`
   has diagonal 1, these two tapered off-diagonals within segments, and zeros
   elsewhere. This is the zero-padded biased autocorrelation construction with
   a positive-semidefinite Bartlett window. Require positive eigenvalues in the
   numerical result, without adding a floor or regularizer.
4. For the OLS residual projector `M`, use `b = trace(M R_train)` and
   `h = wᵀ R w`. Re-estimate pixel variance as `SSE/b`; the event variance is
   `h` times its 50/50 median shrinkage. Require positive finite variance and
   propagation factors. Report `h`, `b`, the two correlations, lag-pair counts,
   segment count, all weights, and correlated/IID variance factor.

Keep the exact IID reference alongside the correlated model. The estimated
separable covariance is descriptive; it does not calibrate longer correlations,
nonstationarity, template-estimation uncertainty, selection effects or tail
probabilities. Pixel-standardized maps are in modeled event SD units, not
Gaussian detection sigmas. Aperture and coefficient noise retain the inherited
cross-pixel sideband covariance calculation, with the same `h/b` propagation.

## Fixed spatial fits, concentrations and paired accounting

The geometric centers and common-finite mask are the original LS8T definitions,
including the original 24-row centroid mean, source offsets and C0/C1 shift.
The annulus is `30 < r <= 40`. The background-subtracted mean training image and
its centered finite-difference x/y gradients form the templates. The fitted
models remain brightness+constant, gradients+constant, and all four columns.
Use the pinned LS8M weighted scaled-SVD implementation and its unchanged rank
tolerance; fit every original aperture pixel. A missing pixel, rank failure or
nonpositive variance stops and is retained as an outcome, not repaired by
masking, extra data or threshold adjustment.

Publish model coefficients and sideband noise, weighted and unweighted explained
energy, residual energy, expected residual energy, residual/reference ratios,
aperture flux and flux noise. Fit the event only to estimate its model
coefficients; profiles, variances and covariance estimates use training alone.
Verify the reconstructed native event maps against the original LS8T maps.

Describe the combined-model residual in the fixed rings 0–8, 8–16, 16–25 pixels
and four coordinate quadrants, with signed flux and raw/weighted energy in all
12 cells. Report top-1/top-10 pixel energy concentrations and the largest
residual's coordinate. These are reporting statistics only: no pixel selection,
new mask, refit, threshold, physical-cause label or decision gate follows them.

For paired CAL/COR, project CAL, COR and DELTA=COR−CAL with the **same COR
combined projector** and preserve the signed cross term:
`E_COR = E_CAL + E_DELTA + 2 <CAL_residual, DELTA_residual>`, raw and weighted.
The terms are an identity, not independent causal fractions. Also preserve the
exact C0/C1 aperture-boundary flux and squared-energy identities and full signed
boundary pixel lists for CAL, COR and DELTA. Coordinate serialization uses
Python integers prospectively, incorporating the known LS8P representation fix.

## Duration-matched held controls and signal loss

Tile each original 12-row sideband into nonoverlapping `d`-row targets. For each
held target, remove its rows and a two-row guard on both sides from the original
training set. The native event and native guards never enter training. Refit the
time trend, profile, gradients, pixel variances and correlations using the
remaining training values; keep the original center and common aperture fixed.
Run all 24 single-row controls for TG015701_P0 and all eight three-row controls
for TG000101_N0 in both products and conventions: **128 held cases** in total.
Report every case and the count with combined weighted residual/reference ratio
at least as large as the native event. Controls share training data, are few and
have different leverage and location; these counts are **not p-values**.

For each of eight native product/convention cases, run both signs of:

- Brightness at 0.001 per exposure: summed coefficients ±`d*0.001`.
- Each gradient at 0.05 per exposure: summed coefficients ±`d*0.05`.
- A compact addition at each of five fixed geometric offsets: `(0,0)`, `(10,0)`,
  `(0,10)`, `(−10,0)`, `(0,−10)`, nearest aperture pixel with row-major tie break.
  Total amplitude is five modeled event-pixel SDs, interpreted as equal
  per-exposure additions over the original duration.

Recover pure and additive coefficient increments and require maximum known
coefficient/linearity error <=1e−9. There are **128 signed controls**, including
48 known-template and 80 compact cases. Record weighted energy and signed flux
retained after a hypothetical gradients+constant subtraction. A nearly zero
signed injected flux has no flux fraction. No subtraction, correction or veto
is adopted, irrespective of apparent fit quality or loss.

## Independent audit, publication and stop

The auditor never imports the producer. It uses independent `struct` binary
decoding, long-double temporal normal equations, scalar lag sums and explicit
quadratic forms, the pinned independent LS8M spatial normal-equation code, and
coordinate-set boundary accounting. Reconstruct all native and held cases,
signed controls, saved arrays and summaries, and check preserved labels, native
maps and masks. Integer/Boolean/discrete results must agree exactly. Numerical
tolerances remain `rtol=2e−8`, native `atol=1e−6`, and dimensionless `atol=1e−8`.
Do not relax them after inspecting native outcomes.

Before native execution, require all **18 prospective tests**: eight inherited
spatial tests and ten new duration, cadence, leakage, known-answer, independent
reconstruction, serialization and legacy-compatibility tests. The workflow uses
Python 3.12.14, pinned `requirements_ls7g.txt` and one BLAS thread. Preserve
complete or failed results, logs, environment, freeze SHA and SHA-256 manifest.
Publish both contexts' six-panel COR residual/standardized/control figures and
inspect them before writing the final interpretation. Retain all CAL diagnostics
and arrays even though the overview figures show COR.

This **single bounded study closes regardless of result**. Both original LS8T
labels, LS8S search scores and thresholds remain unchanged. It adds no qualified
candidate, calibrated detector or qualified coverage. Do not automatically tune
TESS_260647166 further. The next independent transfer is rank-5 **EC 12578-2107**,
exact pair `CH_PR100002_TG008901_V0300`, `CH_PR100002_TG008902_V0300`, under its own
future metadata/L2 freeze; those science values remain unopened here. Closed
GJ 1132, HD 136352 and WASP-189 studies stay closed. Raw imagettes, reserved
TESS/M43 data, the NOT_READY calibration gate and unsent request stay unchanged.
