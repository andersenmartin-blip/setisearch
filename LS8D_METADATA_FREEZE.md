# LS8D exact metadata and image-boundary freeze

All eight original representatives now have unique exposure joins to both
native products: **482 verified joins** for **241 L2 context rows**. The
independent struct auditor passes **2,213 exact checks** before any image
payload is opened. UTC strings, MJD and BJD agree exactly (maximum numeric
time difference **0 seconds**); paired CE counters/integrity also agree.

| Visit | Frames per native cube | X/Y window offsets | NEXP | Cadence (s) |
|---|---:|---|---:|---:|
| TG000302 | 1,171 | 180 / 728 | 20 | 44.2200012207031 |
| TG000303 | 1,189 | 180 / 728 | 20 | 44.2200012207031 |
| TG000304 | 1,194 | 180 / 728 | 20 | 44.2200012207031 |

All image planes are 200x200 big-endian float64 with unit BSCALE, zero BZERO,
DRP 14.1.2 and native BUNIT `ADU`. CAL/COR integration keywords match L2.
Smearing products are native 3-D arrays of shape (N,1,200), also float64 ADU;
one 200-value vector corresponds to each joined exposure.

The first metadata join attempt asserted a 2-D smearing layout and stopped.
The initial independent metadata audit omitted the CE_COUNTER column's
TSCAL=1 / TZERO=32768 unsigned convention and stopped. Both implementation
assumptions were corrected against the actual headers **before image access**.
The initial logs are preserved beside the final passing metadata audit.
No time tolerance, representative, image range or scientific gate changed.

The complete [machine manifest](config/ls8d_images.json) freezes file names,
object totals/ETags, offsets, all 482 plane joins and all 24 requested byte
ranges (CAL, COR and smearing for each context). The exact future transfer is
**154,240,000 image bytes + 385,600 smearing bytes = 154,625,600 bytes**.
No science image or smearing payload was acquired during metadata preflight.
Other extensions, including PIP_COR_Centroid and smearing-error arrays, were
skipped. Header/metadata receipts and raw ranges are retained in
`results_ls8d_metadata/`.

Publish this completed manifest, the [paired-image protocol](LS8D_PAIRED_IMAGE_PROTOCOL.md),
producer, independent auditor and seven passing synthetic tests together
before acquisition. Retain all historical results and the raw-imagette gate.
