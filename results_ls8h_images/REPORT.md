# LS8H: GJ 849 L2 excursion is spatially structured in paired CAL/COR images

Completed 20 September 2026 under the image diagnostic frozen before payload
access. LS8G had selected one positive DEFAULT-L2 cluster in
`CH_PR100018_TG032401_V0300`; its fixed representative is row 75, duration
one 42-second row, with L2 screen score 23.4700798115.

The LS8H metadata preflight uniquely joined all 29 fixed context rows to both
native CAL and COR exposures before any image payload was opened. The frozen
diagnostic then acquired exactly **18,560,000 paired image bytes** plus
**46,400 smearing-row bytes**.

## Audited result

The event is **SPATIALLY_STRUCTURED** under the predeclared classification
order. It does not meet the CORRECTION_LINKED gate.

| Quantity | C0 | C1 |
|---|---:|---:|
| COR aperture event sum | 98,475.821 ADU | 97,101.022 ADU |
| CAL aperture event sum | 94,993.738 ADU | 93,919.955 ADU |
| DELTA/COR | 0.03536 | 0.03276 |
| column DELTA/COR | 0.03636 | 0.03598 |
| COR brightness model explained | 0.912% | 0.914% |
| COR displacement model explained | 87.801% | 87.800% |

Both fixed coordinate conventions have complete r<=25 apertures and the COR
event sign matches the positive L2 excursion. However, CAL→COR changes account
for only about 3–4% of the aperture event, far below the frozen 0.5
CORRECTION_LINKED threshold. The displacement template explains about 87.8%
of the COR event-map energy in both conventions while the brightness template
explains below 1%, satisfying the separately frozen SPATIALLY_STRUCTURED rule.

This is a morphological diagnostic result. It does **not** establish a unique
pointing, attitude, detector or astrophysical cause, and the L2 screen score is
not a Gaussian significance or a SETI-candidate probability.

The direct DELTA-versus-smearing-row regression is rank-deficient under the
frozen design and is retained as unavailable rather than repaired after the
result. The CAL→COR DELTA map itself is weakly column-structured
(`delta_column_energy_fraction = 0.0111`).

## Independent verification

Seven synthetic paired-image tests passed before image acquisition. The
independent auditor then redecoded the retained image ranges and metadata,
rebuilt event maps with long-double temporal normal equations and independently
recomputed the spatial fits and classification.

- numerical comparisons: **94,537**
- exact checks: **160,581**
- disagreements: **0**
- maximum CAL map difference: **1.82e-12 ADU**
- maximum COR map difference: **3.64e-12 ADU**
- maximum DELTA difference: **4.09e-12 ADU**
- audit status: **PASS**

No raw imagette, alternate aperture, second GJ 849 visit or additional image
row was opened.

## Decision

Close the fixed GJ 849 cluster as **SPATIALLY_STRUCTURED** under LS8H. Do not
retune its aperture, temporal context, spatial models or thresholds to seek a
different label. Continue the independent survey mechanically through the host
order already frozen before LS8E science access.

[Protocol](../../LS8H_PAIRED_IMAGE_PROTOCOL.md)
[Input scope](../../LS8H_INPUT_SCOPE.md)
[Machine diagnostics](diagnostics.json)
[Independent audit](audit.json)
