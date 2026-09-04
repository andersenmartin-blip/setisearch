# Milestone 42 M41 truth-local support and mask diagnostic result

Status: **COMPLETE — LEDGER-ONLY DIAGNOSTIC; 98 / 512 TRUTHS HAVE
GEOMETRIC SCORE SUPPORT; 50% RECOVERY IS STRUCTURALLY UNREACHABLE**.

## Result

M42 reassembled and hash-verified the complete M41 ledger, validated all 6,144
canonical records, and separated the frozen endpoint into three nested stages:
geometric candidate support, a finite score after the two-pass mask, and
threshold recovery.

Only 98 of 512 truths have one or more truth-local candidate-score cells. The
other 414 have none at every tested S/N level. Candidate-cell count,
mask-dependency-cell count, and plan identity are invariant across all 12 S/N
levels for every truth. Under the unchanged M41 adapter, the maximum possible
recovery is therefore 98/512 = 19.140625%, even before mask/finiteness and
threshold losses. A 50% recovery transition cannot be reached by increasing
injected S/N alone.

| Ideal S/N | Geometrically supported | Finite post-mask | Recovered | Recovery / all 512 | Recovery / supported | Recovery / finite |
|---:|---:|---:|---:|---:|---:|---:|
| 48 | 98 | 52 | 0 | 0 | 0 | 0 |
| 56 | 98 | 48 | 0 | 0 | 0 | 0 |
| 64 | 98 | 51 | 0 | 0 | 0 | 0 |
| 72 | 98 | 49 | 2 | 0.00390625 | 0.02040816 | 0.04081633 |
| 80 | 98 | 48 | 7 | 0.01367188 | 0.07142857 | 0.14583333 |
| 88 | 98 | 46 | 11 | 0.02148438 | 0.11224490 | 0.23913043 |
| 96 | 98 | 44 | 27 | 0.05273438 | 0.27551020 | 0.61363636 |
| 112 | 98 | 50 | 37 | 0.07226562 | 0.37755102 | 0.74000000 |
| 128 | 98 | 45 | 40 | 0.07812500 | 0.40816327 | 0.88888889 |
| 160 | 98 | 44 | 43 | 0.08398438 | 0.43877551 | 0.97727273 |
| 192 | 98 | 49 | 46 | 0.08984375 | 0.46938776 | 0.93877551 |
| 256 | 98 | 49 | 46 | 0.08984375 | 0.46938776 | 0.93877551 |

At the predeclared highest-level cross-section, S/N 256, exactly half of the
geometrically supported truths produce a finite score (49/98), and 46/49 of
those finite scores exceed the frozen threshold. The dominant loss in the
original 512-truth endpoint therefore occurs before threshold comparison:
414 truths lack a candidate cell, and another 49 supported truths have no
finite post-mask score in that randomized trial.

## Descriptive S/N 256 subgroups

The width table illustrates that geometric support and post-mask finiteness
are distinct. These are post-M41 descriptive counts, not separately calibrated
subgroup sensitivities.

| Injected width (channels) | Truths | Supported | Finite | Recovered |
|---:|---:|---:|---:|---:|
| 1 | 64 | 14 | 1 | 1 |
| 3 | 64 | 18 | 2 | 2 |
| 5 | 64 | 8 | 4 | 4 |
| 9 | 64 | 16 | 7 | 5 |
| 17 | 64 | 13 | 6 | 5 |
| 33 | 64 | 9 | 9 | 9 |
| 65 | 64 | 10 | 10 | 10 |
| 129 | 64 | 10 | 10 | 10 |

| Activity subset index | Truths | Supported | Finite | Recovered |
|---:|---:|---:|---:|---:|
| 0 | 128 | 22 | 12 | 9 |
| 1 | 128 | 25 | 9 | 9 |
| 2 | 128 | 19 | 6 | 6 |
| 3 | 128 | 32 | 22 | 22 |

The machine-readable result additionally reports the predeclared line, radial,
and phase strata, the complete candidate-cell-count distribution, and
hash-pinned supported and unsupported truth-ID inventories.

## Execution checks

| Check | Result |
|---|---|
| M41 aggregate identity and file hash | Passed |
| Seven-part ledger transport and reassembly hash | Passed |
| Canonical M41 record validation | Passed (6,144 / 6,144) |
| Per-truth 12-level inventory | Passed (512 / 512) |
| Structural support invariant across S/N | Passed |
| Nested `recovered <= finite <= supported` accounting | Passed |
| New spectral reads | 0 |
| New injections or adapter executions | 0 |
| Threshold or M41 record changes | 0 |
| Complete local test suite | Passed (364 tests; 2 expected skips) |

## Reproducible certificate

| Item | SHA-256 |
|---|---|
| M42 diagnostic identity | `270fa7c5abb25218894b563d38f3b8b8501e348ec4623fcbed43d6d79bbc9447` |
| M42 diagnostic file | `f6b4f02b4bd04af52374012c20da6f19a4efe81ce21d1041dafc66ce4a4762ac` |
| Supported truth-ID inventory | `2d03fa8e67e6048166123f3202e5509bdb2b45cad6bbece2ec126846a881ec5d` |
| Unsupported truth-ID inventory | `6c26c35fcf122ac1d8477811429e685ab70e781f4393325065c0c9e78ebc56d1` |
| Parent M41 aggregate | `b95220e51b02636a45d0a9e322bdc879fa47bad79f03d0577eb2566382b6f8c9` |
| Parent M41 ledger | `429789c591f44cb1ea87a5b340bf79a72905b44af3aa71bef964b3d002cc50fb` |

## Claim boundary and next decision

The 19.140625% ceiling applies only to the frozen M41 pointwise truth-local
endpoint. It is an engineering property of that adapter and its ±20 Hz
truth-to-bank candidate definition, not an astronomical completeness or
sensitivity bound. The 46/98 and 46/49 supported-only fractions may not replace
the original 46/512 denominator.

M42 therefore rejects another blind S/N extension. The next defensible step is
to freeze a prospective adapter-support repair or a clearly renamed endpoint
redesign, validate it against exhaustive real-data anchors, and only then
consider new injections. M42 does not authorize that change and makes no
interpolation, sensitivity-transport, occurrence-rate, or technosignature
claim.
