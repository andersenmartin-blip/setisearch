# LS8M: one bounded residual and local-variability study

Frozen on 20 September 2026 **before calculating any new native-derived LS8M
quantity**. The trigger commit contains this protocol, configuration, both
implementations, synthetic tests, report generator and execution workflow.
The source is the already published LS8L image-result commit
`e86c3d15ca8ab6aed0e1a6a9cecaa95f0061efb0`; current direction is recorded at
`0c827bb15a68d4521396d60b4b8b36b12002ed24`.

## Question and scope

Which observable spatial residual and local variability prevent the existing
brightness/displacement model from describing the smaller WASP-189 positive
excursion, TG000201_P0? Retain TG000202_P0 and TG000202_N0 as signed comparison
cases. This is retrospective method development on three selected, closed
events. It is not an independent validation set or a new search.

Only the three retained 29-row CAL/COR contexts and their existing L2 rows,
metadata and receipts are inputs. Verify all LS8L hashes and the pinned L2
table/header hashes before calculation. Re-decode 55,680,000 retained CAL/COR
bytes. The already retained SMEAR files remain covered by the LS8L manifest;
no new smearing model is fitted. **New native source bytes: zero.** There is no
observatory network client in this analysis or audit.

Keep event local row 14, side rows 0–11 and 17–28, and guards 12–13 and 15–16.
Keep the exact LS8L common finite mask, C0/C1 centers, radius-25 aperture,
30 < radius <= 40 background annulus and finite centered-difference gradient
mask. Centers retain their original metadata definition even in sideband
controls. No pixels, weights, apertures or frames are selected from residuals.

## Fixed temporal and spatial calculations

For each product/convention use sideband ordinary least squares in native ADU,
with intercept and slope against BJD-relative seconds, and median-offset
arithmetic. Let S be its n-by-p matrix of side residuals (n=24), y the event
minus extrapolated sideband model, and df=n-2. The event prediction factor is

`h = 1 + 1/n + (t_event - mean(t_side))^2 / sum((t_side-mean)^2)`.

Use each pixel's `s2 = sum(S^2)/df` and **fixed 50% shrinkage** to the median
variance within that unchanged fit mask:

`v = h * (0.5*s2 + 0.5*median(s2))`.

The fixed shrinkage limits unstable weights from just 22 residual degrees of
freedom; it is not estimated by optimizing the event. No variance clipping,
weight sweep or alternative estimator follows. Nonpositive median variance,
incomplete aperture or rank deficiency stops the study with a retained failure.

Templates are unchanged in definition: side mean minus annular median (p),
centered native-pixel gradients gx/gy, and a constant. Fit brightness `[p,1]`,
displacement `[gx,gy,1]` and combined `[p,gx,gy,1]` by weighted least squares,
with column-normalized SVD and relative singular-value cutoff 1e-12. Retain
the original LS8L unweighted results beside the new weighted diagnostics.

For each model, let B map pixel values to fitted coefficients and R=I-XB.
Report coefficients, condition, raw and weighted explained energy, residual
energies, flux sums, and sideband coefficient/flux variability. Estimate the
sideband reference residual energies as `h*||S R^T||^2/df`, in raw and weighted
coordinates. Report observed/reference energy ratios without clipping.
Compute whole-aperture noise from the **sum of each side-residual image**;
compare it with the diagonal-only estimate. This preserves observed
cross-pixel covariance for the reported flux, without attempting to invert an
unidentifiable full pixel covariance matrix.

These reference energies describe local sideband variability, which may
contain structured instrumental changes. Extrapolation assumes comparable
event variability. They are not photon-noise-only estimates, chi-square
statistics, Gaussian significances or source probabilities.

## Residual location and paired correction accounting

Partition the combined-model residual into 12 fixed cells: radii <=8,
8<r<=16, 16<r<=25, each split into four native-coordinate quadrants. Q0 is
x>=cx,y>=cy; Q1 x<cx,y>=cy; Q2 x<cx,y<cy; Q3 x>=cx,y<cy. Report signed flux and
raw/weighted energy shares. Also report the largest one- and ten-pixel energy
shares and maximum pixel coordinate, with row-major tie breaking. These are
descriptive concentration measures, never pixel-removal criteria.

For CAL/COR correction accounting apply **the same COR combined-model
projector and weights** to CAL, COR and DELTA=COR-CAL. Retain the exact signed
identity `E_COR = E_CAL + E_DELTA + 2<CAL_residual,DELTA_residual>` in raw and
weighted coordinates. Report all three terms and normalized closure error;
do not add CAL and DELTA variances while discarding their cross term.

## Twenty-four sideband controls for every product/convention

Each of the 24 side rows is held out in turn as a pseudo-event. Rebuild the
temporal model, side mean templates and variance from the remaining 23 side
images (df=21); the native event and guards never enter this training. Retain
the original fixed geometry and common mask. Apply the held-row leverage
factor, including extrapolation at the sideband edges. Publish every model
and spatial summary for all **288 pseudo-event cases** (864 model fits).
For the combined weighted observed/reference energy ratio, report the count
of side controls at least as large as the native event, out of 24.

These overlapping controls share data, have different time leverage and
retain metadata geometry estimated earlier. Their ranks are **not**
false-alarm probabilities. L2 selection already used the native event.

## Fixed signed synthetic controls and signal-loss accounting

Before native analysis run the eight known-answer/leakage unit tests. On each
of the 12 native product/convention states, inject both signs of:

- brightness `0.001*p`;
- first-order displacement `0.05*gx` and `0.05*gy` (native pixel units);
- five compact single-pixel defects, each `5*sqrt(v_pixel)`, at the nearest
  existing fit pixel to center plus (0,0), (10,0), (0,10), (-10,0), (0,-10).
  Distance ties use row-major order.

This is **192 signed cases**, comprising 72 pure template cases with known
combined coefficients and 120 compact cases. Apply them both alone and
additively to the retained event vector; the temporal-map injection transfer
is separately tested against a known linear trend. Verify pure coefficient
recovery and additive linearity with maximum absolute coefficient error
1e-9, independently of native event classification. The synthetic gradients
are first-order templates, not a full physical jitter simulation.

For every injection report the weighted energy and signed flux remaining
after a hypothetical displacement-plus-constant subtraction. This explicitly
measures signal loss if that removal were contemplated. No subtraction,
veto or new classifier is adopted by LS8M, and compact controls are not used
to tune a cut. These tests do not qualify detection sensitivity.

## Audit, publication and stopping rule

Independently re-decode raw image/L2 bytes with struct, compute temporal
normal equations in long double and spatial normal equations with scalar
fsum cross-products. Rebuild all event summaries, every sideband case, all
injection outputs, sector/concentration summaries, paired energy accounting
and saved numerical arrays. The auditor imports no producer numerical code.
Use relative tolerance 2e-8; native absolute tolerance 1e-6 and dimensionless
or coefficient absolute tolerance 1e-8. Independently known-answer control
gates remain the tighter 1e-9 above. Compare masks, indices, copied historical
labels and branch decisions exactly. Publish complete or failed outcomes,
logs, environment, inputs' identities and an output checksum manifest.

Stop after this integrated study regardless of whether it explains the
limitation. Preserve LS8L's exact 80% displacement/20%-advantage and 50%
correction gates and all three historical classifications. Do not claim a
stellar or artificial event from a residual, weighted fit or small control
rank. There is no new candidate, detector, coverage qualification or automatic
new image acquisition. Any independent transfer to rank-2 GJ 1132 needs a
separate prospective freeze. The raw-imagette calibration gate, unsent
technical request, reserved TESS sectors and M43 held-out panels stay separate.
