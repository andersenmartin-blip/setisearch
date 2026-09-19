# LS7AB — frozen independently predicted pointing subtraction for CHEOPS cluster 1

Frozen 19 September 2026 before computing any LS7AB numerical result. This
stage opens **zero new archive bytes**. It uses only the audited LS7Z event-map
products and the independently audited LS7AA/L2 centroid excursion.

## Question

How much of the cluster-1 COR event-excess map is explained, to first order, by
the **independently measured L2 centroid displacement**, without fitting the
pointing amplitude to the event map?

This is a consistency/residual study, not a source-classification test.

## Fixed parent evidence

- parent cluster: LS7X/LS7Y cluster 1 only;
- event rows: 185–187;
- context rows: 171–201;
- sidebands and guards unchanged from LS7Z;
- LS7Z COR event map and sideband mean are reused from
  `results_ls7z_morphology/cluster1_morphology_arrays.npz`;
- the L2 summed centroid event-excess vector is the audited LS7AA value,
  independently derived from CENTROID_X/Y over the same three rows.

No new aperture, visit, raw imagette, archive frame or image context may be
opened.

## Fixed sign convention

For each C0/C1 coordinate convention, reconstruct the same LS7Z sideband
template `P` and central differences `Dx=dP/dx`, `Dy=dP/dy`.

For summed L2 displacement
`D_L2=(delta_x, delta_y)`, the externally predicted first-order event map is

`E_point = -delta_x*Dx - delta_y*Dy`.

The coefficients are taken directly from L2. They are not fitted or rescaled
before the primary comparison.

## Fixed comparison domain

Use exactly the LS7Z common template-fit domain:

- r<=25 under the current C0/C1 convention;
- finite event excess E;
- finite P, Dx and Dy.

The primary domain may not be enlarged or clipped after evaluation.

## Primary fixed diagnostics

For C0 and C1 separately report on the common domain:

1. squared-L2 explained fraction by the unit-amplitude external prediction:
   `1 - sum((E-E_point)^2)/sum(E^2)`;
2. RMS of E, E_point and residual;
3. cosine similarity between E and E_point;
4. `sum(E_point^2)/sum(E^2)`;
5. signed sum and absolute-L1 sum of E, E_point and residual;
6. residual cosine similarity with P, Dx and Dy.

No pass/fail threshold is declared.

## Fixed amplitude-consistency diagnostic

Report, but do not apply to the primary residual, the least-squares scalar

`alpha = dot(E,E_point)/dot(E_point,E_point)`

and the explained fraction obtained by `alpha*E_point`. This is a diagnostic
of the LS7AA magnitude mismatch, not a retuned correction or a new detector.

## Fixed radial residual ledger

At radii 5, 12 and 25 pixels report residual signed sum, residual absolute-L1,
and the ratio of residual absolute-L1 to the original event-map absolute-L1 on
the same domain. Radii are fixed before evaluation.

## Interpretation boundary

LS7AB may state whether the independently measured centroid motion predicts the
spatial pattern strongly or weakly in these descriptive metrics and quantify
the remaining map. It may not label the event astrophysical, artificial,
instrumental, a detection, or a false positive.

A further stage is justified only by a separately frozen question. Any
remaining residual must be preserved; no outcome-driven threshold, scale,
centroid, radius or mask adjustment is allowed.

## Independent audit

A separate script must:

- decode the saved L2 table independently and recompute CENTROID_X/Y event
  excess from the fixed sidebands;
- read the saved LS7Z event map and sideband mean;
- reconstruct P, Dx, Dy and the common domains independently;
- recompute every LS7AB metric.

Publication requires a passing audit and SHA256 manifest.
