# LS8I: audited two-visit GJ 649 DEFAULT-L2 screen is null

Completed 20 September 2026. The two exact GJ 649 visits were selected
mechanically from the host order fixed before LS8E science access. Header-only
preflight established the same 18-field DEFAULT-L2 schema before any
science-table values were opened. The visits retain their different native
cadences.

## Audited result

| Visit | rows | cadence | eligible windows | positive >=+8.5 | negative <=-8.5 | max score | min score |
|---|---:|---:|---:|---:|---:|---:|---:|
| `CH_PR100018_TG018601_V0300` | 127 | 22.650 s | 294 | 0 | 0 | 2.337192 | -3.285708 |
| `CH_PR100018_TG031201_V0300` | 75 | 42 s | 87 | 0 | 0 | 4.587742 | -3.081413 |
| **total** | **202** | — | **381** | **0** | **0** | — | — |

Exactly **27,876 science-table bytes** were acquired from the two frozen
first-table ranges. No other aperture, image, raw imagette or visit was opened.

The unchanged flux-centered cadence-unit rule, 1/2/3-row durations, sidebands,
guards, eligibility and symmetric +/-8.5 endpoints were fixed before table
access. Each visit used its own header-frozen TEXPTIME.

## Independent verification

The independent audit directly decoded the retained 138-byte big-endian rows
and rebuilt the centered scalar normal equations, eligibility, scores, signed
clusters and visit summaries.

- audit status: **PASS**
- numerical/discrete comparisons: **4,572**
- disagreements: **0**
- largest score discrepancy: **8.88e-16**
- image bytes: **0**
- raw imagettes: **0**

## Interpretation and survey boundary

This is a clean null result for the exact prospectively selected GJ 649 pair.
It does not establish a population upper limit, detector qualification or a
Gaussian false-alarm probability.

The metadata host order frozen before LS8E is now exhausted under its unchanged
requirement of at least two eligible V0300 / PIPE 14.1.2 visits per host.
No later host in that retained ledger qualifies for another two-visit stage.

Do not lower the two-visit requirement, relax the metadata eligibility rules,
or reuse an already closed host to extend this sequence. The next independent
search must begin with a new metadata-only target/dataset selection whose
population, ranking and eligibility rules are frozen before new science values
are inspected.

[Protocol](../../LS8I_GJ649_L2_PROTOCOL.md)
[Selection freeze](../../LS8I_SELECTION_FREEZE.md)
[Independent audit](audit.json)
