# LS8F: audited two-visit GJ 514 DEFAULT-L2 screen

Completed 20 September 2026. The two exact GJ 514 visits were selected
mechanically from the already frozen LS8E metadata ledger before science-table
access. Header-only preflight established a compatible DEFAULT-L2 schema with
zero table-data bytes before this screen was frozen.

## Audited result

| Visit | rows | cadence | eligible windows | positive >=+8.5 | negative <=-8.5 | max score | min score |
|---|---:|---:|---:|---:|---:|---:|---:|
| `CH_PR100018_TG007501_V0300` | 90 | 44 s | 150 | 0 | 0 | 5.819043 | -2.311805 |
| `CH_PR100018_TG007502_V0300` | 62 | 44 s | 0 | 0 | 0 | unavailable | unavailable |
| **total** | **152** | — | **150** | **0** | **0** | — | — |

Exactly **20,976 science-table bytes** were acquired from the two previously
declared first-table ranges. No other aperture, image, raw imagette or visit
was opened.

The second visit has zero eligible windows under the frozen context rule. This
is retained as a valid outcome rather than repaired by changing sidebands,
guards, durations or status/gap criteria after inspection.

## Independent verification

The audit directly decodes the retained 138-byte big-endian rows and recomputes
the flux-centered scalar normal equations, eligibility, signed endpoints,
cluster construction and visit summaries without importing the producer scorer.

- audit status: **PASS**
- numerical/discrete comparisons: **1,800**
- numeric disagreements: **0**
- maximum score difference: **1.33e-15**
- image bytes: **0**
- raw imagettes: **0**

## Interpretation

This is a clean null result for the exact prospectively selected GJ 514 pair:
there are no positive or negative threshold crossings in the eligible windows.
It does not establish detector qualification, a population upper limit or a
Gaussian false-alarm probability. The 150 eligible windows overlap and are not
independent trials.

Do not lower the threshold, change aperture/durations/context rules, or add a
later GJ 514 visit because the selected pair was null or because the second
visit contributed no eligible windows.

The next survey step advances mechanically through the already frozen host
order. **GJ 849** is rank 4 and has six eligible V0300 / PIPE 14.1.2 visits in
the saved metadata ledger. A new milestone must again freeze the exact visit
pair before opening science-table values.

[Screen protocol](../../LS8F_GJ514_L2_PROTOCOL.md)
[Selection freeze](../../LS8F_SELECTION_FREEZE.md)
