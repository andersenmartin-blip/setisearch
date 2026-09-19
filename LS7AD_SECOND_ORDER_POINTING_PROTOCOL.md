# LS7AD — frozen second-order pointing expansion for CHEOPS cluster 1

Frozen 19 September 2026 before computing any LS7AD numerical result. This
stage opens **zero new archive bytes** and uses only already published LS7X,
LS7Z and LS7AC material.

## Question

Does the fixed second-order Taylor expansion of the sideband image profile,
driven only by the three independently measured L2 centroid displacements,
explain the cluster-1 event map better than the first-order pointing predictor?

This is an approximation-order diagnostic. It is not a source-classification
test.

## Fixed inputs and displacements

Reuse the exact LS7AC event rows, sideband rows, centroid regressions and three
per-event displacement vectors. Their sum must reproduce the audited LS7AA
centroid event-excess vector.

No displacement component or scale is fitted to image pixels.

## Fixed derivatives

For each C0/C1 convention, use the LS7Z sideband-mean COR profile after the
same fixed scalar background subtraction. On pixels with all required finite
neighbors compute unit-grid central differences:

- `Px = (P[x+1]-P[x-1])/2`
- `Py = (P[y+1]-P[y-1])/2`
- `Pxx = P[x+1]-2P[x]+P[x-1]`
- `Pyy = P[y+1]-2P[y]+P[y-1]`
- `Pxy = (P[y+1,x+1]-P[y+1,x-1]-P[y-1,x+1]+P[y-1,x-1])/4`

No smoothing, PSF fitting or derivative rescaling is allowed.

## Fixed predictions

For each event displacement `(dx_i,dy_i)`:

First order:
`E1_i = -dx_i*Px - dy_i*Py`

Second order:
`E2_i = E1_i + 0.5*dx_i^2*Pxx + dx_i*dy_i*Pxy + 0.5*dy_i^2*Pyy`

Sum each over the three event frames to obtain `E1` and `E2`.

## Fixed comparison domain

Use the intersection of:

- r<=25 under the current C0/C1 convention;
- finite LS7Z event excess E;
- finite P and every first/second derivative listed above.

Both E1 and E2 are evaluated on this identical domain.

## Fixed diagnostics

For E1 and E2 separately report:

- squared-L2 explained fraction;
- cosine similarity with E;
- prediction RMS and residual RMS;
- prediction-energy/event-energy ratio;
- residual absolute-L1/event absolute-L1 ratio.

Report second-order minus first-order change in explained fraction and residual
RMS.

For each prediction also report, without applying it to the primary residual,
the diagnostic optimal scalar
`alpha=dot(E,pred)/dot(pred,pred)` and its scaled explained fraction.

## Fixed radial ledger

At r<=5, r<=12 and r<=25 report the second-order residual
absolute-L1/event absolute-L1 ratio.

## Interpretation boundary

LS7AD may state whether the fixed second-order terms improve or degrade the
independently driven pointing prediction. It may not label the event
astrophysical, artificial, instrumental, a detection or a false positive.

No derivative rule, radius, mask, displacement, scale or threshold may be
changed after evaluation. A further stage needs its own frozen question.

## Independent audit

A separate script must independently decode the L2 centroid series, solve the
sideband regressions, rebuild every central derivative with explicit scalar
indexing, construct E1/E2 and reproduce all published metrics. Publication
requires a passing audit and SHA256 manifest.
