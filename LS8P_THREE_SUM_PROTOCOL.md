# LS8P: frozen retained GJ 1132 three-sum study

Status: **prospectively specified before any new native-derived LS8P calculation**.
The Git commit introducing this protocol, config, implementation, independent
auditor, tests and workflow is the freeze identity. The workflow records its
exact `GITHUB_SHA` and refuses dirty tracked input. Publication follows the
standing project authorization. No contact with people is made.

## Question, scope and stop

This is the single integrated study specified by LS8O_CONTINUATION.md at
`b9108033d537136043209b4ec00a461fbed098d8`: assess local variability of the
five negative controls' three-exposure sums, fixed-model residuals, and the
exact aperture-boundary contribution to coordinate sensitivity.

Source result is LS8O commit `51cc3cee0b803ad2d41b6564758b6b91df693a2a`.
All five contexts are mandatory: TG000401_N0 and TG000403_N0/N1/N2/N3.
Only their previously retained CAL/COR 31 x 200 x 200 image arrays, matching
L2 tables, original image maps and metadata are used. Existing SMEAR files
remain manifest-verified; no new smearing model is fitted. Config and input
SHA-256 pins, original image manifest and gzip raw receipts are checked.
No new archive pixels, rows, visits or products may be acquired. Repo
checkout of already published inputs is not new scientific acquisition.

Original LS8N/LS8O thresholds, representatives, masks, radii and labels are
immutable. In particular, all five remain UNRESOLVED_WITHIN_FIXED_SCOPE;
the near-80% case is not rounded up and no convention is preferred. Zero
positive LS8N crossings remain zero. This retrospective study establishes
no candidate, classifier, detector qualification or observing coverage.
Stop after all five cases, regardless of their results. No extra radius,
pixel removal, template, correlation length or control window is tried.

## Three-row temporal operator

Each context is local rows 0..30. Native targets are 14,15,16; baseline rows
are 0..11 and 19..30. Rows 12,13,17,18 are guards. Times are retained BJD
differences in seconds. Common finite pixels are exactly those finite in
both CAL and COR on the original 24 baseline plus 3 native rows, and must
match the original LS8O common mask.

For each pixel, fit an unweighted intercept and slope to training rows
only, centering pixel values by their training median for numerical stability.
With n training rows, d=3 targets, centered training times u, and
q=sum(target time minus mean training time), the full length-31 temporal
weight vector is +1 on target rows, -d/n-q*u/sum(u^2) on training rows, and
zero elsewhere. The event map is the sum of the three target prediction
residuals. It must match the original LS8O sum within the frozen tolerance.

For IID temporal noise the propagation factor is
`h0 = w.T w = d + d^2/n + q^2/sum(u^2)`, not three copies of a single-row
prediction factor. Baseline estimation is common to all three exposures.

## Fixed descriptive covariance model

The old masks and profiles are retained in definition: sideband mean minus
median in 30<r<=40, centered finite differences in x/y, radius 25 aperture,
and both original centers C0/C1 (C1 is C0 minus one in both axes). Centers
always use the original 24-row centroid mean and the frozen detector offsets.
There must be no additional missing aperture or gradient pixels.

Estimate temporal correlation separately for each product, convention and
native/held case from its training-only residual matrix S in the unchanged
aperture. Initial per-pixel variance is SSE/(n-2). Standardize S by the
square root of a fixed 50:50 mixture of each pixel's variance and the
aperture median variance. A nonpositive median stops the case; there is
no event-based floor or mask change.

Form lag-1 and lag-2 sums of standardized residual products using pairs
whose original local row indices differ by 1 or 2. A cadence step outside
30..90 seconds splits a segment; correlations never cross such a gap.
Divide both lag sums by the same total standardized squared residual,
then multiply lag 1 by 2/3 and lag 2 by 1/3. Missing training positions
are zero-padded. This is a biased autocorrelation estimate with a Bartlett
lag-2 taper. Its block Toeplitz correlation matrix R has diagonal 1,
the two estimated off-diagonals, and zeros elsewhere. It is positive
semidefinite by construction; numerically nonpositive eigenvalues stop
the case without an alternative estimator or clipping rule.

Let M be the OLS residual projector on training rows. Use
`b = trace(M R_train)` as the variance normalization, and `h = w.T R w`
for the complete event-minus-predicted-baseline operator. Thus event,
baseline and their cross-covariances are all included. Per-pixel variance
is `SSE/b`; the fitted pixel variance is
`h * (0.5*SSE/b + 0.5*median(SSE/b))`. Report n-2, b, h0, h, the two lag
coefficients and pair counts, cadence segments, all weights and the
variance factor `(h/b)/(h0/(n-2))`. Save actual-case R matrices.

This is one pooled temporal correlation model, not pixel-dependent time
covariance or a complete temporal spectrum. The estimated lag values are
affected by detrending. Longer correlations, nonstationarity, short
training sets, and uncertainty in the fitted profile, R and weights are
not calibrated. With pooled R, changing IID to correlated propagation
rescales all pixel variances equally within a case; it changes the noise
normalization, not the spatial fit coefficients. Report IID results beside
the correlated results rather than choosing whichever looks preferable.

## Spatial and paired residual accounting

Retain the pinned LS8M weighted spatial algebra and its independent
normal-equation auditor: brightness+constant, x/y gradients+constant,
and brightness+x/y gradients+constant. Scaled SVD uses relative rank
tolerance 1e-12. No regularization or fallback after rank failure.

Report coefficients, descriptive baseline-propagated coefficient SDs,
weighted/unweighted explained energies and remaining energies, and the
ratio to propagated training residual energy after the same spatial
projector. Spatial covariance in aperture sums is kept by summing pixels
in each residual row before squaring, and is compared with a diagonal
pixel estimate. Use covariance normalization h/b throughout; none of
these SDs are calibrated confidence intervals.

For the combined residual, retain the fixed rings 0..8, 8..16, 16..25
and four quadrants, signed flux and energy by cell, and descriptive top-1
and top-10 pixel energy concentrations. Ordering pixels is reporting only;
no ordered pixel is masked or removed. For paired CAL/COR/DELTA, use the
same COR combined projector and report
`E_COR = E_CAL + E_DELTA + 2<CAL,DELTA>` in raw and weighted units.
Keep the signed cross term; these are not additive physical-cause fractions.

## Eight fixed held-out three-row controls

Target blocks are [0,1,2], [3,4,5], [6,7,8], [9,10,11], [19,20,21],
[22,23,24], [25,26,27], [28,29,30]. For each, training uses the original
24 baseline rows after excluding the target and all rows within two
local indices of it. Native event and original guards never enter
training. Refit temporal baseline, profile, variance, R and spatial model
using training only. Keep the original centers and common masks.

Publish all eight, and the count whose combined weighted residual/reference
ratio is at least the native value. No p-value is inferred: targets are
not selected in the same way as the native events, leverage differs,
profiles vary, and their overlapping training sets are dependent.
There are 5 x 2 products x 2 conventions = 20 native cases and 160 held
cases; three spatial fits and both temporal reference models are reported.

## Exact coordinate-boundary identity

Use the two original radius-25 masks, their intersection, and C0-only/
C1-only pixels. For each CAL/COR/DELTA native map, retain signed flux and
squared energy in all regions, the two full aperture sums, and the exact
identity `sum(C1)-sum(C0)=sum(C1-only)-sum(C0-only)`. Save every boundary
pixel coordinate and signed map value. No preferred mask, third aperture,
intersection-only fit, event-driven cut or new pixel selection is introduced.
Boundary accounting explains aperture differences, not automatically
changes in fitted models with different background/profile definitions.

## Signed signal protection and synthetic gates

Both signs are mandatory despite the all-negative native sample. Add equal
per-exposure pure brightness (+/-0.001 times the training profile), x-gradient
and y-gradient (+/-0.05 per exposure) pulses for three exposures. Summed
known coefficients are +/-0.003 and +/-0.15. These are first-order template
controls, not a nonlinear star-position injection model.

Use five compact locations chosen geometrically: center, and +/-10 along
x or y; nearest aperture pixel breaks ties in row-major order. Each signed
three-row sum has amplitude 5 times that pixel's modeled event SD, divided
equally over the three targets. Retain all 320 signed controls: 120 exact
template cases and 200 compact cases. Recover pure combined coefficients
and their incremental values when added to the native map; expected and
linearity errors must be <=1e-9. Report retained energy and signed flux
under hypothetical displacement+constant subtraction. Do not adopt it.

Before native access, run nine new tests of summed signed brightness,
displacement and compact responses, guard exclusion, analytic IID factor,
PSD/cadence-aware covariance propagation, target and held-block leakage,
independent reconstruction, boundary identity, signal-loss accounting and
zero-variance failure. Also run the eight existing LS8M spatial-algebra
tests. The new nine tests have passed locally on synthetic arrays; no new
native-derived LS8P values were inspected in constructing this protocol.

## Independent audit, figures and failure preservation

The auditor imports no producer or producer numerical module. It decodes
retained binary tables/images with struct, solves temporal normal equations
in long double, forms lag sums and covariance quadratic forms independently,
uses the pinned independent scalar-fsum weighted normal-equation spatial
auditor, and accounts for coordinate boundaries using pixel-coordinate sets.
It checks every reported actual, held, injection and boundary diagnostic,
per-context duplicate, saved actual array, original map and common mask.

Numerical tolerances remain relative 2e-8, absolute 1e-6 for native-valued
quantities/arrays and 1e-8 for dimensionless summary quantities. Integer,
boolean, membership, count, label and key checks are exact. Mismatches stop
publication of a successful report; preserve the failed result and audit
instead of changing tolerances or omitting cases. No pre-existing file is
overwritten. The workflow preserves logs, environment, freeze identity and
SHA-256 manifest for either complete or failed execution.

One fixed six-panel COR figure per context shows C0/C1 combined residuals,
modeled pixel-SD residuals, and all eight held comparisons. Each image
panel uses its own symmetric full residual range and labels units; axes
show the unchanged aperture without analysis clipping. Inspect all five
figures before the interpretive project-status update.

After the bounded study, rank-3 HD 136352 remains next for a separately
frozen independent transfer of the already selected chronological pair.
Its native science values, all reserved material and raw imagettes remain
closed here. The raw-imagette calibration request is still unsent.
