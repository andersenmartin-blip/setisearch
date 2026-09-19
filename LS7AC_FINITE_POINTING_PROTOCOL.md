# LS7AC — frozen finite-displacement pointing prediction for CHEOPS cluster 1

Frozen 19 September 2026 before computing any LS7AC numerical result. This
stage opens **zero new archive bytes** and uses only already published LS7X,
LS7Z and LS7AB material.

## Question

Does replacing LS7AB's first-order gradient approximation with a fixed
finite-displacement image translation materially improve the independently
predicted cluster-1 event map?

This tests approximation order. It is not a source-classification test.

## Fixed inputs

- LS7X L2 table already published in `results_ls7x_l2_pilot/`;
- LS7Z COR event-excess map, eligibility mask and sideband mean image;
- LS7Z C0 and C1 target centres;
- LS7AB first-order metrics for direct comparison.

No new aperture, archive frame, visit, raw imagette or science byte may be
opened.

## Independent per-frame displacements

For CENTROID_X and CENTROID_Y separately, fit the same unweighted straight
line to the 24 fixed sideband rows 171–182 and 190–201.

For each event row 185, 186 and 187 define

`delta_i = observed_centroid_i - sideband_prediction_i`.

The three displacements are used individually. Their vector sum must reproduce
the audited LS7AA summed L2 centroid event excess within numerical tolerance.

No displacement component is fitted to image pixels.

## Fixed profile and interpolation

For C0 and C1 separately:

1. take the already published LS7Z sideband-mean COR image;
2. subtract the same fixed 30<r<=40 median scalar background used by LS7Z;
3. call the resulting fixed profile `P`;
4. for event displacement `(dx,dy)`, evaluate
   `P_shifted(x,y) = P(x-dx, y-dy)` using ordinary bilinear interpolation;
5. no extrapolation, smoothing, spline, Fourier shift, PSF refit or amplitude
   rescaling is allowed;
6. the finite predicted summed event map is
   `sum_i [P_shifted_i - P]`.

Bilinear source coordinates must have all four finite neighbouring profile
pixels. A target pixel is eligible only if it is eligible in LS7Z and valid
for all three event-frame translations.

## Fixed comparison domain

The primary comparison uses the intersection of:

- r<=25 under the current C0/C1 convention;
- finite LS7Z event excess;
- finite unshifted profile;
- valid bilinear support for every event displacement.

LS7AB is recomputed on that **same reduced domain** for an apples-to-apples
first-order comparison.

## Fixed diagnostics

For both the finite predictor and the recomputed first-order predictor report:

- squared-L2 explained fraction `1-SSE/SST0`;
- cosine similarity with E;
- RMS prediction and RMS residual;
- prediction-energy/event-energy ratio;
- residual absolute-L1/event absolute-L1 ratio.

Report the finite-minus-first-order change in explained fraction and residual
RMS. No improvement threshold is declared.

For the finite predictor additionally report the diagnostic optimal scalar
`alpha=dot(E,pred)/dot(pred,pred)` and its scaled explained fraction, without
applying that scale to the primary residual.

## Fixed radial ledger

At r<=5, r<=12 and the full common r<=25 domain, report the finite predictor's
residual absolute-L1/event absolute-L1 ratio.

## Interpretation boundary

LS7AC may state whether finite sub-pixel translation accounts for more, less or
similar event-map energy than the frozen first-order approximation. It may not
label the event astrophysical, artificial, instrumental, a detection or a false
positive.

If a further stage is warranted, its question must be separately frozen before
its own evaluation. The LS7AC output itself may not be used to tune an
interpolator, scale, centroid, radius or mask.

## Independent audit

A separate script must independently decode the L2 table, solve the sideband
centroid regressions, implement scalar bilinear interpolation, rebuild the
finite and first-order predictions, and reproduce every published metric.
Publication requires a passing audit and SHA256 manifest.
