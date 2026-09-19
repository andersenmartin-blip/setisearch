# LS7Z — frozen morphology and L2-component study for CHEOPS cluster 1

Frozen 19 September 2026 before computing any LS7Z result. This stage uses only
already published LS7X/LS7Y bytes and opens **zero new archive science bytes**.

## Fixed parent

Only LS7X/LS7Y cluster 1 is in scope:

- visit: `CH_PR300024_TG000301_V0300`
- event rows: 185–187
- fixed context: rows 171–201
- fixed sidebands: rows 171–182 and 190–201
- fixed guards: rows 183–184 and 188–189
- parent LS7X score: 9.118532025193854
- parent LS7Y label: `IMAGE_LOCALIZED_NOT_CORRECTION_DOMINATED`

Cluster 0 is closed for this continuation because LS7Y classified it
`CORRECTION_LINKED`.

## Allowed inputs

Use only:

- `results_ls7x_l2_pilot/lightcurve_table.bin`
- `results_ls7x_l2_metadata/lightcurve_header.bin`
- the retained cluster-1 CAL/COR frame ranges in
  `results_ls7y_l1_followup/`
- `cluster_1_event_excess_maps.npz` only as a comparison copy; the evaluator
  must independently rebuild the COR event-excess map from the retained frames.

Do not request the archive, open other apertures, inspect raw imagettes, add
frames, or use another visit.

Carry both LS7Y coordinate conventions unchanged:

- C0 = (CENTROID_X-715, CENTROID_Y-181)
- C1 = C0-(1,1)

No convention may be selected from the outcome.

## A. Fixed L2 component diagnostics

For each already retained continuous L2 column below, compute the event sum
minus the same unweighted sideband-only straight-line prediction used by LS7X:

- FLUX
- FLUXERR
- DARK
- BACKGROUND
- CONTA_LC
- CONTA_LC_ERR
- SMEARING_LC
- SMEARING_LC_ERR
- ROLL_ANGLE
- LOCATION_X
- LOCATION_Y
- CENTROID_X
- CENTROID_Y

For each column report event sum, predicted event sum, event excess, sideband
median, sideband residual MAD scale, and
`event_excess / (MAD*sqrt(3))` when the MAD scale is finite and nonzero.
These normalized values are diagnostics, not new screening scores and have no
accept/reject threshold.

## B. Fixed radial morphology

Independently rebuild the COR three-frame event-excess map from the 24 fixed
sideband frames. A pixel is eligible only if finite in all 27 used frames.

For C0 and C1 separately, report at fixed radii
**3, 5, 8, 12, 18, 25 and 35 pixels**:

- signed event-excess sum;
- positive-part sum;
- negative-part magnitude;
- absolute L1 sum;
- fraction of the full common-eligible positive-part sum inside the radius;
- fraction of the full common-eligible absolute L1 sum inside the radius;
- eligible and total geometric pixel counts.

Do not adjust radii after evaluation.

## C. Fixed target-centered shape diagnostics

Within r<=25 and eligible pixels:

1. Use the positive part of the COR event-excess map as weights. If positive
   weight is nonzero, compute its centroid offset from the event-mean target
   coordinate and its 2x2 second central moment. Report major/minor RMS and
   axis ratio. Do the same with absolute event-excess weights.
2. Compute row-constant and column-constant orthogonal projections of the COR
   event-excess map on the eligible r<=35 pixels. Report their squared-L2
   energy fractions relative to the map on the same domain.
3. Report the signed and absolute sums in annuli 0–5, 5–12, 12–25 and 25–35.

No clipping, smoothing or morphology threshold is allowed.

## D. Fixed profile/pointing decomposition

For each coordinate convention independently:

1. Construct the sideband mean COR image from the 24 fixed sideband frames.
2. Estimate one scalar background as the median of eligible sideband-mean
   pixels in the fixed annulus 30<r<=40.
3. Define the fixed brightness template `P = sideband_mean - background`.
4. Define fixed central-difference derivative templates on P:
   `Dx=(P[y,x+1]-P[y,x-1])/2`,
   `Dy=(P[y+1,x]-P[y-1,x])/2`.
   Pixels needing unavailable neighbors are excluded.
5. On eligible r<=25 pixels, fit by ordinary least squares:
   - brightness model: [P, constant]
   - shift model: [Dx, Dy, constant]
   - combined model: [P, Dx, Dy, constant]
6. For each model report rank, condition number, residual RMS, squared-L2
   explained fraction `1 - SSE/SST0` where SST0=sum(E^2) about zero, and
   fitted coefficients. Also report cosine similarity between E and P, Dx, Dy
   individually on the same fixed pixel set.

These fits are descriptive. No minimum explained fraction is declared, and no
model is selected as a physical truth.

## Interpretation boundary

LS7Z may state which predeclared template family accounts for more of the
cluster-1 event-map energy and whether the event excess is centrally
concentrated. It may not use post-hoc thresholds to label the event
astrophysical, artificial, instrumental or a candidate detection.

A subsequent stage is justified only if its question is separately frozen from
the LS7Z numerical outcome. No additional image bytes are opened by LS7Z.

## Independent audit

A separate script must parse the saved L2 binary table and cluster-1 CAL/COR
frames independently, rebuild all eligible masks, temporal fits, event maps,
radial metrics and template fits, and reproduce every published continuous
quantity within fixed numerical tolerance. Publication requires a passing
audit and a SHA256 manifest.
