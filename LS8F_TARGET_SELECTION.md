# LS8F — GJ 514 selection freeze

Status: **FROZEN BEFORE GJ 514 SCIENCE VALUES**.

LS8E closed the exact two-visit GJ 876 pair with zero +/-8.5 crossings. The
next target is not chosen from that null result's detailed values; it follows
the target order that was frozen before LS8E science access.

The existing metadata-only LS8E ledger is reused without a new archive query.
In that ledger:

- rank 1 GJ 876 is now completed;
- rank 2 HD 219134 has no exact match under the predeclared aliases;
- rank 3 **GJ 514** has nine eligible public V0300 / PIPE 14.1.2 visits.

The frozen pair rule again selects the two chronologically earliest eligible
visits:

| role | file key | OBSID | MJD start | exposure | NEXP | stacked |
|---|---|---:|---:|---:|---:|---:|
| visit 1 | `CH_PR100018_TG007501_V0300` | 1106324 | 58985.1549744834 | 22 s | 2 | 44 s |
| visit 2 | `CH_PR100018_TG007502_V0300` | 1110092 | 58988.9100675873 | 22 s | 2 | 44 s |

The frozen product inventories for both visits contain DEFAULT
`SCI_COR_Lightcurve`, `SCI_CAL_SubArray` and `SCI_COR_SubArray`.

No GJ 514 science-product byte, light-curve value or image pixel has been read
to make this choice. The immutable source ledger is
`results_ls8e_selection/selection.json`, blob
`05dca92185a6f279f0090b76e89f16614fe42ef9`.

## Next boundary

Perform header-only preflight on those two exact DEFAULT light curves. Do not
read table data. If the schemas are compatible with the established screen,
freeze the same prospective stable 1/2/3-row symmetric +/-8.5 rule before
opening either table range.

Do not substitute later GJ 514 visits if either selected product fails the
preflight.

[Previous result](results_ls8e_l2_screen/REPORT.md)
