# LS8F — frozen GJ 514 visit selection

Status: **FROZEN BEFORE GJ 514 SCIENCE-TABLE ACCESS**.

LS8E completed the prospectively selected two-visit GJ 876 screen with no
positive or negative threshold crossings. Its continuation requires mechanical
advance through the target order already frozen before LS8E science access.

The saved LS8E metadata ledger identifies **GJ 514** as the next qualifying
host (rank 3; rank 2 HD 219134 had no exact alias match). Nine GJ 514 visits
satisfy the LS8E V0300 / PIPE 14.1.2 / public DEFAULT-L2 / CAL+COR product
requirements.

Apply the unchanged pair-selection rule: choose the two chronologically
earliest eligible visits, without reading prospective light-curve values.

Selected pair:

1. `CH_PR100018_TG007501_V0300`
   - OBSID 1106324
   - MJD start 58985.1549744834
   - EXPTIME 22 s
   - NEXP 2
   - stacked exposure 44 s
2. `CH_PR100018_TG007502_V0300`
   - OBSID 1110092
   - MJD start 58988.9100675873
   - EXPTIME 22 s
   - NEXP 2
   - stacked exposure 44 s

Both were already recorded in `results_ls8e_selection/selection.json` as
eligible V0300 / PIPE 14.1.2 products with DEFAULT `SCI_COR_Lightcurve`,
`SCI_CAL_SubArray` and `SCI_COR_SubArray`.

## Boundary

This freeze uses only the already saved metadata ledger. No GJ 514 light-curve
value, FITS table row or image pixel is inspected by this selection step.

Next acquire only the primary and first DEFAULT `SCI_COR_Lightcurve` BINTABLE
headers for the two exact file keys. Require zero table-data bytes. If and only
if both schemas are compatible with the unchanged cadence-unit screen, freeze
that screen before acquiring their table ranges.

Do not substitute a later GJ 514 visit if either selected object fails.
Do not alter aperture, durations, sidebands, guards or signed endpoints based
on header contents.
