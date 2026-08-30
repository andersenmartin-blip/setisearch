# Milestone 37 primary spectral run: capacity-invalid result

Status: **M37_INVALID_NO_CONCLUSION — SPECTRAL DATA ACCESSED; NO SIGNAL OR
NULL CLAIM**.

The authorized detector-v0.6 production execution reached complete extraction,
native-cache construction, five-window calibration and global-threshold
publication. It then stopped fail-closed during exhaustive ON retention because
the frozen 10,000-record capacity was exceeded in `m37_1418p5`. The protocol
forbids truncation and threshold adaptation, so OFF retention, physical
disposition, rank significance and scientific outcome assembly were not run.

## Production lineage

Run `m37-v0p6-primary-003` stopped before producing any native cache after an
endpoint one-ULP geometry mismatch exposed a missing bounded-roundoff allowance
in the production cache-build path. That run was permanently invalidated with
reason `production-cache-endpoint-ulp-validator-mismatch`. The same four-ULP
bound already required by the validated gather path was applied consistently,
and the complete 288-test suite passed with one expected skip.

Run `m37-v0p6-primary-004` then used a new source/factor bundle and a new
spectral authorization artifact. All six sparse remote mirrors were reopened
and every checkpoint segment SHA-256 was independently verified before the
normalized products and cache manifest were accepted.

| Production item | Result |
|---|---:|
| Authorized remote scans | 6 |
| Remote logical bytes | 5,106,402,756 |
| Normalized window/scan products | 30 |
| Native cache entries | 240 |
| Native cache payload bytes | 11,545,072,128 |
| Cache manifest file SHA-256 | `b85011823dc31e9ed0f7abc4c316f8b4a903cce80919aae676cf56289a80d11b` |
| Verified cache inventory SHA-256 | `3bc5e5c745043cb5d738b85a89c9f4e8b5917c842c48f32b83f8e8ee43774c97` |

## Complete calibration

Each of the five windows evaluated all 2,976 hypotheses and all 256 frozen
scrambles. The combined execution covered 11,125,255,200 observed score cells
and 2,848,065,331,200 null score cells. Controller completion telemetry was:

| Window | Observed maximum S/N | Null-maxima SHA-256 |
|---|---:|---|
| `m37_1400p5` | 2351.90673828125 | `c0b4e0f4af10965d2943ff82ec84cad42739f4e7f61d0a36b186efb5c5b2371e` |
| `m37_1406p5` | 34281.89453125 | `0e7aae4da61803acf69a1ee64d2a101881176b34aca7089d61a098aa12143b32` |
| `m37_1412p5` | 255.06434631347656 | `b5c9001036e9a5471b37d29d23926a0f7571bb932852f286065d46bfb4b94671` |
| `m37_1418p5` | 154.97610473632812 | `25f8933e798b04c30e0c0f68b970b5cd12753c2be8cd7cd8ea43ff008826ce63` |
| `m37_1425p0` | 38.835044860839844 | `a33a5614874d23ac541faaefc545e1fc2f1d785435bb5da40a9a043d1df2ff6a` |

The sealed global-null vector contains 256 maxima. It produced an operational
threshold of S/N `126.20158386230469` and inclusive rank-p
`0.01556420233463035`.

| Calibration identity | SHA-256 |
|---|---|
| Threshold certificate | `d65048bd962a247a3763eb58c9cad530d9f7db06586f52a01a34e03b4ba0ad71` |
| Global-null maxima | `9f1ced12ece55f149a0f3331a69f11450ef4235b0d23272c38f1b268441bd3d1` |
| Global-null file | `c15e1c4b8f83652574e9f2f5e55cef62686d75f67ddd8678d669bb4417804449` |

## Exhaustive-retention stop

Window-level work was parallelized without changing the retention algorithm or
artifact schema. Each process used the same sealed threshold, factor bundle,
cache manifest and exact hypothesis order. Existing immutable window artifacts
were reopened instead of recomputed. This completed four ON-window artifacts
while `m37_1418p5` failed before its first five-template progress interval.

| Window | ON retention status | Records |
|---|---|---:|
| `m37_1400p5` | complete partial-run artifact | 1,800 |
| `m37_1406p5` | complete partial-run artifact | 218 |
| `m37_1412p5` | complete partial-run artifact | 225 |
| `m37_1418p5` | capacity failure | at least 10,026 |
| `m37_1425p0` | complete partial-run artifact | 0 |

An independent deterministic replay located the first overflowing hypothesis.
After 156 complete hypotheses, 8,925 records had been counted. Template 4,
line index -2, width index 7 (129 channels), active epochs `[0, 1]`, contributed
1,101 additional records with maximum S/N `133.93687438964844`. The cumulative
lower bound therefore became 10,026 after 117,383,405 score cells, exceeding
the frozen capacity by at least 26 records.

The failure evidence is
`results_m37_v0p6_primary_004/retention-capacity-failure.json`:

- evidence SHA-256:
  `e7a21d172939a54933b762a6afa96670365d6e6eeb57a7a45a98777622265ded`;
- evidence-file SHA-256:
  `b6f9b1a61c18a5f79e5385f9dcfb81cac8d311859dfc8a28caab6e83fec4a5da`;
- final journal stage: `invalid`;
- final journal head:
  `d13d03a5d8430b5c48dd7c9de24158659ce810bfcc44ffbf13f7cac29f3b8e61`;
- reason code: `retention-capacity-overflow`.

The four completed window artifacts are diagnostic partial-run evidence only.
They cannot be joined, interpreted as candidates, or used to make a null claim
because the normative five-window ON inventory is incomplete.

## Interpretation and next boundary

This is a successful fail-closed execution of the preregistered rule, not a
technosignature result. The data contain more above-threshold score cells in at
least one window than the frozen publication/evidence capacity can represent.
The run does not establish whether any member would survive OFF, adjacent-OFF,
receiver-frame alias or rank-significance checks.

Run 004 is immutable and cannot be repaired by deleting records, increasing
its threshold or silently enlarging its capacity. Any continuation requires a
separately documented new protocol/run—explicitly acknowledging that the
capacity revision is post-contact—and must preserve this invalid result. The
machine-readable summary is
`results_m37_v0p6_primary_004/result.json`.
