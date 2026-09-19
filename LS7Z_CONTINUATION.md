# Continue after LS7Z

LS7Z completed the frozen morphology/component characterization of the only
remaining LS7X/LS7Y branch, cluster 1, using **zero new archive science bytes**.
The independent audit passes 103,218 numeric/discrete comparisons.

## Result: close the LS7X candidate branch

The retained cluster-1 COR event-excess map is not brightness-profile-like
under the fixed decomposition. In both coordinate conventions:

- brightness-only template explains about **0.11%** of squared event-map energy;
- the fixed first-derivative displacement template explains about **92.51%**;
- the combined brightness+displacement fit explains about **92.62%**;
- cosine similarity with Dx is about **0.9503**, versus about **0.0296** with
  the brightness profile P;
- the positive-excess centroid is displaced by about **5.17–5.53 pixels** from
  the target center.

This fulfills the predeclared LS7Y continuation branch in which a
pointing/spatially structured result closes the excursion without widening.
The result is descriptive morphology evidence: it does **not** prove the
physical cause, identify a particular spacecraft motion term, or classify the
excursion as astrophysical/artificial.

Cluster 0 was already closed as **CORRECTION_LINKED** by LS7Y. Therefore the
two prospectively selected LS7X L2 screens are now both closed as candidate
branches. Do not inspect another aperture, neighboring rows, raw imagettes or
another visit to rescue either event.

## What remains scientifically open

The separate raw-imagette calibration program remains useful as a method
development track, not as follow-up of an LS7X candidate. Its remaining
dependency is the exact onboard `gcoadd` pixel arithmetic and the verified
gain/reference-file contract. The pair grouping, raw storage width,
`ROUNDING=0` and `NLIN_COR=false` constraints are already documented.

Future short-transient work should begin with a separately prospective input
or method question, not with threshold/aperture changes to this closed visit.
The mission-delivered L2 pilot is evidence that the pipeline can produce
high-scoring local excursions whose image morphology needs instrumental
follow-up; it is not detector qualification or observing-rate evidence.

[LS7Z protocol](LS7Z_MORPHOLOGY_PROTOCOL.md)
[LS7Z result](results_ls7z_morphology/REPORT.md)
[LS7Z audit](results_ls7z_morphology/audit.json)
