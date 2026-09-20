# LS8E metadata-only selection: GJ 876

Completed 20 September 2026 under the target/product rule frozen before any
new-target science value was opened.

The fixed SETIsearch host order was reused unchanged. **GJ 876**, rank 1, is
the first non-excluded host with at least two public CHEOPS visits satisfying
all predeclared metadata requirements:

- archive/product version V0300;
- pipeline 14.1.2;
- public corrected light curve available;
- positive finite exposure metadata with stacked exposure <=60 s;
- exact product inventory contains DEFAULT `SCI_COR_Lightcurve`,
  `SCI_CAL_SubArray` and `SCI_COR_SubArray`.

Seven GJ 876 visits satisfy those conditions. The frozen pair rule selects the
two chronologically earliest eligible visits:

| role | file key | OBSID | MJD start | exposure | NEXP | stacked exposure |
|---|---|---:|---:|---:|---:|---:|
| visit 1 | `CH_PR100018_TG032801_V0300` | 1201652 | 59077.4744239216 | 3.0 s | 14 | 42 s |
| visit 2 | `CH_PR100018_TG032802_V0300` | 1237379 | 59114.8053256116 | 3.0 s | 14 | 42 s |

Both exact product inventories contain the required DEFAULT L2 light curve and
paired CAL/COR subarrays. The selection also retains all rejected versions and
eligibility reasons. For example, V0200/PIPE 13.1.0 versions are ineligible,
and later V0300 products using PIPE 14.1.3 are excluded by the frozen version
rule rather than substituted into the selected pair.

## Selection boundary

This stage used only the public CHEOPS visit database and product-name
inventories.

- science product bytes read: **0**
- FITS table rows read: **0**
- light-curve values read: **0**
- image pixels read: **0**
- product download calls: **0**

The target therefore was not chosen because of any transient, score, light
curve or image morphology. The metadata query and product-presence ledger are
retained in this directory with SHA-256 checksums.

## Next action

Acquire only the FITS primary and DEFAULT `SCI_COR_Lightcurve` table headers
for these two exact file keys. Require bounded byte ranges, stable object
identity and zero table-data bytes. Use those headers to verify schema, cadence,
exposure keywords and exact table boundaries.

Only after that header preflight is published may the cadence-screen protocol
be frozen. If the schema is compatible, the intended continuation is the same
symmetric cadence-unit screen used in LS7X/LS8A/LS8B: durations 1/2/3 rows,
12+12 sidebands, two-row guards, unchanged eligibility/statistic and both
+8.5 and -8.5 endpoints. No light-curve value may be opened before that
protocol is frozen.

[Selection protocol](../../LS8E_TARGET_SELECTION_PROTOCOL.md)
[Machine selection](selection.json)
