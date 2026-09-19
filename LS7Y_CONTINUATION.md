# Continue after LS7Y

LS7Y completed an independently audited, bounded L1 CAL/COR image follow-up of
the two prospectively selected LS7X DEFAULT-aperture clusters for CHEOPS
`CH_PR300024_TG000301_V0300`.

## Closed branch: cluster 0

LS7X cluster 0 (rows 66–68, score 10.2765767) is
**CORRECTION_LINKED** under the frozen LS7Y descriptive rule. In both retained
coordinate conventions, the CAL→COR event-excess change has magnitude greater
than half the final COR event excess. The DELTA event map is also strongly
column-coherent (0.8141). Do not widen cluster 0 into neighboring rows,
apertures, visits or raw imagettes merely to rescue it.

This label is an instrumental-processing statement, not a claim about the
physical origin of every photon in those frames.

## Active branch: cluster 1 only

LS7X cluster 1 (rows 185–187, score 9.1185320) remains positive in the CAL and
COR target apertures. Its CAL→COR change is substantial but below the fixed
50% correction-dominance gate in both coordinate conventions. About 78% of the
absolute COR event-excess-map L1 norm lies inside r<=25. LS7Y therefore labels
it **IMAGE_LOCALIZED_NOT_CORRECTION_DOMINATED**.

That label is deliberately limited. It does not establish that the excursion is
stellar, astrophysical, artificial, isolated from pointing/PSF effects, or
independent of every DRP correction.

## Immediate continuation

Before opening any additional image pixels, use only the bytes already
published by LS7X and LS7Y to characterize cluster 1:

1. fixed radial concentration and event-excess centroid diagnostics;
2. row/column coherence of the COR event map;
3. a fixed decomposition against the sideband mean target profile and its
   first spatial derivatives, to distinguish brightness-like from
   small-displacement-like morphology;
4. fixed event-minus-sideband diagnostics for the already retained L2
   auxiliary columns (DARK, BACKGROUND, contamination, SMEARING_LC, roll,
   location and centroid coordinates).

This next stage is LS7Z and must be fully frozen before evaluation. It opens no
new archive bytes. It may report morphology/component evidence but may not
promote a candidate to astrophysical/artificial status.

If LS7Z shows that cluster 1 is dominated by a pointing/spatially structured
component, close the branch without widening. If it remains compact and
brightness-profile-like, any further physical interpretation or new-data
follow-up must be separately frozen. The unresolved raw-imagette `gcoadd`
calibration remains a separate route and must not be inferred from LS7Z.
