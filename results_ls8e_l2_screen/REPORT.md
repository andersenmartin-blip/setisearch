# LS8E: audited two-visit GJ 876 DEFAULT-L2 screen

Completed 20 September 2026. GJ 876 and the exact two-visit pair were selected
from metadata before any new-target light-curve value was opened. A subsequent
header-only preflight established a compatible 18-field DEFAULT-L2 schema and
the table byte ranges before this evaluation was frozen.

The prospective screen used the same LS7X/LS8A/LS8B cadence-unit rule:
1/2/3-row events, 12+12 sidebands, two-row guards, unchanged eligibility and
symmetric +/-8.5 endpoints. The numerical implementation was the already
verified flux-centered OLS form, frozen before GJ 876 table access.

## Audited result

| Visit | rows | cadence | eligible windows | positive >=+8.5 | negative <=-8.5 | max score | min score |
|---|---:|---:|---:|---:|---:|---:|---:|
| `CH_PR100018_TG032801_V0300` | 115 | 42 s | 243 | 0 | 0 | 5.243715 | -5.127294 |
| `CH_PR100018_TG032802_V0300` | 112 | 42 s | 186 | 0 | 0 | 4.547101 | -2.193953 |
| **total** | **227** | — | **429** | **0** | **0** | — | — |

Exactly **31,326 science-table bytes** were acquired: the two previously
declared first-table ranges only. No other aperture, image, raw imagette or
visit was opened.

No positive or negative signed threshold window exists, so there are zero
signed clusters and no image-follow-up branch.

## Independent verification

The auditor decodes the retained bytes with a fixed big-endian 138-byte row
struct and recomputes the flux-centered scalar normal equations without
importing the producer scorer. It independently re-enumerates eligibility,
signed thresholds, clusters, event/context indices, event bitmasks, per-duration
counts, extrema and row unions.

- audit status: **PASS**
- numerical/discrete comparisons: **5,148**
- numeric disagreements: **0**
- largest score difference: **1.42e-14**
- largest excess difference: **3.64e-11 electrons**
- image bytes: **0**

[Machine summary](summary.json) · [independent audit](audit.json) ·
[checksums](SHA256SUMS).

## Interpretation

This is a clean null result for the exact prospectively selected two-visit
GJ 876 transfer. It does not establish a population upper limit, detector
qualification or Gaussian false-alarm probability. The 429 windows overlap
strongly and are not 429 independent trials.

Because neither sign crosses the fixed endpoint, there is no result-driven
reason to open CAL/COR images for these visits. Do not lower the threshold,
change durations, inspect another aperture or add another GJ 876 visit to seek
a crossing.

The next survey step should advance mechanically through the already frozen
host order rather than widen GJ 876 after seeing this null result. HD 219134
had no match under the frozen aliases in the metadata selection; **GJ 514** is
the next host in that order with multiple eligible public CHEOPS visits. Its
next stage must again be frozen before science values are opened.

[Screen protocol](../../LS8E_GJ876_L2_PROTOCOL.md) ·
[selection result](../results_ls8e_selection/REPORT.md).
