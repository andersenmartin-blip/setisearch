# LS8I — frozen GJ 649 visit selection

Status: **FROZEN BEFORE GJ 649 SCIENCE-TABLE ACCESS**.

LS8H closed the fixed GJ 849 excursion as SPATIALLY_STRUCTURED under the
predeclared paired-image diagnostic. The survey now advances mechanically
through the host order fixed before LS8E science access.

The retained metadata ledger identifies **GJ 649** as rank 5 with five eligible
V0300 / PIPE 14.1.2 visits. Apply the unchanged selection rule: choose the two
chronologically earliest eligible visits without reading prospective
light-curve values.

Selected pair:

1. `CH_PR100018_TG018601_V0300`
   - OBSID 1124851
   - MJD start 59000.9631833702
   - EXPTIME 22.6499996185303 s
   - NEXP 1
   - stacked exposure 22.6499996185303 s
2. `CH_PR100018_TG031201_V0300`
   - OBSID 1175009
   - MJD start 59041.9127731326
   - EXPTIME 3 s
   - NEXP 14
   - stacked exposure 42 s

Both were already recorded as eligible V0300 / PIPE 14.1.2 public DEFAULT-L2
visits with CAL and COR subarray products in
`results_ls8e_selection/selection.json`.

No GJ 649 light-curve value, FITS table row or image pixel is opened by this
selection step. The two visits intentionally have different cadences; each
future screen must use its own frozen TEXPTIME rather than force a common
cadence.

Next perform header-only DEFAULT-L2 preflight with zero table-data bytes.
Do not substitute later visits if either selected object fails.
