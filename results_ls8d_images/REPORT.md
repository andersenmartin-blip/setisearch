# LS8D: all eight fixed excursions are coupled to CAL→COR correction

Completed 20 September 2026 under the protocol frozen before image access at
`804c741dca3889a3e53f4f7165c78713238b25fb`. The exact three-visit metadata
preflight supplied 482 unique CAL/COR joins for the original 241 L2 context
rows. The frozen run then retrieved exactly **154,240,000 paired image bytes**
plus **385,600 smearing-row bytes** and no other science-image range.

All **eight** original LS8B/LS8C representatives — seven positive excursions
and the single negative control — satisfy the predeclared **CORRECTION_LINKED**
rule in both fixed coordinate conventions. This is evidence that the delivered
CAL→COR processing is strongly coupled to every retained excursion. It is
**not** identification of a unique correction component or physical cause,
not a classification as artificial/astrophysical, and not detector
qualification.

[Correction-gate overview](correction_gate_overview.png)
([vector PDF](correction_gate_overview.pdf)).

## Complete fixed-context outcome

Event sums are on the common finite native CAL/COR mask inside r<=25 and retain
the files' native ADU label. C0/C1 are the two coordinate conventions frozen
before image access. `DELTA = COR - CAL`.

| Representative | sign | COR C0 (10³ ADU) | COR C1 (10³ ADU) | DELTA/COR C0 | DELTA/COR C1 | DELTA column-energy fraction | COR displacement explained C0/C1 |
|---|---|---:|---:|---:|---:|---:|---:|
| TG000302_P0 | positive | 238.315 | 230.536 | -2.141 | -2.213 | 94.56% | 65.08% / 65.08% |
| TG000302_P1 | positive | 285.879 | 248.840 | -2.082 | -2.431 | 81.94% | 67.35% / 67.35% |
| TG000302_P2 | positive | 233.460 | 223.829 | -2.203 | -2.297 | 91.51% | 74.42% / 74.42% |
| TG000302_N0 | negative | -219.808 | -226.165 | 0.884 | 0.857 | 0.49% | 21.64% / 21.64% |
| TG000303_P0 | positive | 470.136 | 440.697 | -1.331 | -1.424 | 74.77% | 68.49% / 68.49% |
| TG000303_P1 | positive | 298.112 | 283.350 | -1.862 | -1.914 | 63.55% | 56.63% / 56.63% |
| TG000304_P0 | positive | 292.691 | 321.135 | -1.664 | -1.539 | 76.89% | 59.31% / 59.31% |
| TG000304_P1 | positive | 184.654 | 176.023 | -1.757 | -1.866 | 35.66% | 35.79% / 35.79% |

For the seven positive representatives, CAL→COR has a **negative** aperture
event contribution in every case while the COR event remains positive. Across
the two fixed coordinate conventions, **|DELTA/COR| ranges
1.331–2.431**, comfortably beyond the frozen
0.5 coupling gate. Thus the corrected product retains a positive excursion,
but its amplitude is substantially altered by the correction chain.

The negative control is coupled as well: its CAL aperture event is only mildly
negative, while COR is much more negative; **|DELTA/COR| is
0.857–0.884**. The same descriptive stopping
rule therefore closes both signs rather than selectively explaining only the
positive events.

## Spatial structure and the earlier smearing association

The CAL→COR change is strongly column-structured for many, but not all, positive
events: the DELTA column-constant projection accounts for
**35.66%–94.56%** of DELTA map
energy across the seven positives. The negative control is very different at
**0.49%**. Consequently LS8D
does not establish one common column-smearing mechanism for all eight events.

The delivered COR event maps themselves have small column-constant energy
fractions (all below 3%). The sideband brightness template explains at most
**2.29%** of COR event-map energy in the positive events,
whereas the displacement template explains **35.79%–
74.42%**. The negative control displacement fit explains
about **21.64%–21.64%**. None reaches the
separately frozen 80% spatial-structure threshold; the correction gate already
terminates classification first.

The direct DELTA-versus-smearing-row regression is rank-deficient in all eight
contexts under the frozen design. It is therefore retained as unavailable,
rather than repaired or replaced after seeing the images. This preserves the
LS8C result: the L2 smearing association motivated this image study, but LS8D
does not turn it into a calibrated event correction.

## Independent verification

Seven synthetic tests passed before image access. The independent auditor then
redecoded the retained byte ranges, rechecked metadata joins and receipts,
rebuilt event maps with long-double temporal normal equations, independently
recomputed masks, projections, spatial fits and closure labels, and compared
the saved maps.

- numerical comparisons: **756,296**
- exact checks: **1,284,709**
- audit disagreements: **0**
- maximum CAL/COR map discrepancy: **5.821e-11 ADU**
- maximum DELTA discrepancy: **1.164e-10 ADU**
- audit status: **PASS**

The original LS8B numerical audit remains **FAIL** exactly as published; the
separate stable-arithmetic repair is unchanged. LS8D is a retrospective
image diagnosis of already selected representatives, not a new held-out
false-alarm experiment. Raw imagettes were not opened.

[Machine summary](summary.json) · [independent audit](audit.json) ·
[complete diagnostics](diagnostics.json) · [independent reference](independent_reference.json) ·
[checksums](SHA256SUMS).

## Fixed event-map figures

Each figure shows CAL, COR and DELTA on one common signed scale for that
representative. Solid/dashed circles are the fixed C0/C1 r=25 apertures.
The figures are presentation products generated after the audited decisions;
they are not inputs to any classification.

- **TG000302_P0:** [PNG](TG000302_P0_CAL_COR_DELTA.png) · [vector PDF](TG000302_P0_CAL_COR_DELTA.pdf)
- **TG000302_P1:** [PNG](TG000302_P1_CAL_COR_DELTA.png) · [vector PDF](TG000302_P1_CAL_COR_DELTA.pdf)
- **TG000302_P2:** [PNG](TG000302_P2_CAL_COR_DELTA.png) · [vector PDF](TG000302_P2_CAL_COR_DELTA.pdf)
- **TG000302_N0:** [PNG](TG000302_N0_CAL_COR_DELTA.png) · [vector PDF](TG000302_N0_CAL_COR_DELTA.pdf)
- **TG000303_P0:** [PNG](TG000303_P0_CAL_COR_DELTA.png) · [vector PDF](TG000303_P0_CAL_COR_DELTA.pdf)
- **TG000303_P1:** [PNG](TG000303_P1_CAL_COR_DELTA.png) · [vector PDF](TG000303_P1_CAL_COR_DELTA.pdf)
- **TG000304_P0:** [PNG](TG000304_P0_CAL_COR_DELTA.png) · [vector PDF](TG000304_P0_CAL_COR_DELTA.pdf)
- **TG000304_P1:** [PNG](TG000304_P1_CAL_COR_DELTA.png) · [vector PDF](TG000304_P1_CAL_COR_DELTA.pdf)

## Decision and continuation

**Close all eight LS8B/LS8C representative branches as CORRECTION_LINKED under
the frozen LS8D descriptive rule.** This label means the event amplitude is
materially coupled to CAL→COR processing. It does not establish which DRP
component caused the coupling, nor that the underlying source variability is
instrumental.

Do not widen these branches to more rows, alternative apertures or additional
55 Cnc visits. The separate raw-imagette route remains **NOT_READY** pending
its exact gcoadd/gain/reference contract and the technical request remains
unsent. A future independent optical search should start from a new
prospectively frozen dataset/product choice rather than tune the completed
LS8D events.

[Protocol](../LS8D_PAIRED_IMAGE_PROTOCOL.md) ·
[metadata freeze](../LS8D_METADATA_FREEZE.md).
