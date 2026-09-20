# LS8G — frozen GJ 849 visit selection

Status: **FROZEN BEFORE GJ 849 SCIENCE-TABLE ACCESS**.

LS8F completed the exact two-visit GJ 514 screen with no signed threshold
crossings. The next host is selected mechanically from the target order frozen
before LS8E science access.

The saved metadata ledger identifies **GJ 849** as rank 4 with six eligible
V0300 / PIPE 14.1.2 visits. Apply the unchanged rule: select the two
chronologically earliest eligible visits without reading prospective
light-curve values.

Selected pair:

1. `CH_PR100018_TG032401_V0300`
   - OBSID 1200677
   - MJD start 59077.947629114
   - EXPTIME 3 s
   - NEXP 14
   - stacked exposure 42 s
2. `CH_PR100018_TG032402_V0300`
   - OBSID 1254803
   - MJD start 59125.096092011
   - EXPTIME 3 s
   - NEXP 14
   - stacked exposure 42 s

Both already have DEFAULT `SCI_COR_Lightcurve`, `SCI_CAL_SubArray` and
`SCI_COR_SubArray` in the retained metadata-only product ledger.

No GJ 849 light-curve value, FITS table row or image pixel is opened by this
selection step. Next perform header-only DEFAULT-L2 preflight with zero table
bytes. Do not substitute later visits if either selected object fails.
