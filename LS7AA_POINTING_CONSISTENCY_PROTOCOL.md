# LS7AA — frozen pointing-consistency check for CHEOPS cluster 1

Frozen 19 September 2026 before computing the LS7AA comparison. This stage
opens **zero new archive bytes** and uses only the independently audited LS7Z
summary plus the already published LS7X L2 table for an independent audit.

## Question

Is the displacement-like LS7Z event-map morphology quantitatively consistent,
to first order, with the independently measured L2 centroid excursion over the
same three event rows?

This is a consistency test, not a source-classification test.

## Fixed inputs

From audited LS7Z:

- cluster 1 only;
- the shift-only model coefficients on `Dx` and `Dy` under both C0 and C1;
- the combined-model `Dx` and `Dy` coefficients as a fixed sensitivity check;
- the already reported L2 `CENTROID_X` and `CENTROID_Y` event excesses.

No brightness coefficient, radial result or other candidate is used to choose
the comparison.

## Fixed first-order sign convention

LS7Z defines central-difference templates from the sideband mean image:

`Dx = dP/dx`, `Dy = dP/dy`.

For a small displacement `(delta_x, delta_y)`, an image sampled on the fixed
pixel grid obeys to first order

`P(x-delta_x, y-delta_y) - P(x,y) ≈ -delta_x*Dx - delta_y*Dy`.

The LS7Z event map is the **sum over three event frames** relative to the
sideband temporal prediction. Therefore, if displacement dominates, the
shift-only fit coefficients `(b_x,b_y)` correspond to the inferred summed
centroid displacement

`D_template = (-b_x, -b_y)`.

The independent L2 vector is

`D_L2 = (CENTROID_X event_excess, CENTROID_Y event_excess)`,

where those event excesses are likewise sums over the same three rows relative
to the same fixed temporal sideband prediction.

## Fixed metrics

For each C0/C1 convention and for both the shift-only and combined LS7Z fits,
report:

- `D_template`;
- `D_L2`;
- both vectors divided by 3 (mean per event frame);
- Euclidean norms;
- difference vector and difference norm;
- cosine similarity;
- angular separation in degrees when both norms are positive;
- norm ratio `|D_template|/|D_L2|`;
- relative vector residual `|D_template-D_L2|/|D_L2|`.

No agreement threshold is declared. LS7AA may describe the numerical
direction/magnitude consistency but may not convert it into an
astrophysical/artificial/instrumental probability.

## Independent audit

The audit must decode CENTROID_X/Y independently from the saved L2 binary table,
reconstruct the fixed sideband linear predictions for rows 185–187, verify the
LS7Z coefficients from the published audited summary, and independently
recompute every vector metric. Publication requires a passing audit.
