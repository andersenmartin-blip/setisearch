# M43B active-epoch geometric association result

**Geometry comparison complete: 167/512 supported, versus the unchanged 98/512 baseline. Score and real-data qualification remain pending.**

The publicly frozen active-epoch rule adds 69 supported truths and loses none. All 512 original truths remain in the denominator. The 345 unsupported truths still prevent a 50% recovery endpoint under this fixed bank and 20 Hz association rule, even before masking or threshold losses. This is geometry, not measured signal recovery or sensitivity.

| Association | Supported truths | Fraction of all 512 |
|---|---:|---:|
| Original all-epoch 20 Hz | 98 | 19.140625% |
| Active-epoch 20 Hz | 167 | 32.617188% |

## Activity comparison

| Truth-active ON epochs (zero-based) | Truths | Original support | Active-only support | Added |
|---|---:|---:|---:|---:|
| [0, 1] | 128 | 22 | 55 | 33 |
| [0, 2] | 128 | 25 | 32 | 7 |
| [1, 2] | 128 | 19 | 48 | 29 |
| [0, 1, 2] | 128 | 32 | 32 | 0 |

All-epoch-active truths retain exact complete plan identities. The change only removes distance constraints from epochs in which the labelled injected truth is absent. A single fixed template and carrier must still match every integration of every active epoch. Width does not relax the 20 Hz criterion; different widths have different assigned truths, so subgroup differences are not isolated causal width effects.

## Width inventory

| Injected width (channels) | Truths | Original support | Active-only support |
|---|---:|---:|---:|
| 1 | 64 | 14 | 23 |
| 3 | 64 | 18 | 25 |
| 5 | 64 | 8 | 20 |
| 9 | 64 | 16 | 23 |
| 17 | 64 | 13 | 25 |
| 33 | 64 | 9 | 14 |
| 65 | 64 | 10 | 17 |
| 129 | 64 | 10 | 20 |

## Verification

The metadata-derived factor basis and 93-template table reproduce their historical SHA-256 identities exactly. All 6,144 M41 records were validated. For every one of the 512 truths, the original complete plan-inventory digest and candidate-score-cell count reproduce M41 exactly. The geometric count is expanded by 8 widths × 4 score activity hypotheses in the original score-cell tally. Every original candidate set is contained in the corresponding new set.

All eight M43/M43B tests passed. Four new tests cover every canonical activity subset with a multi-integration exhaustive Boolean oracle, retention of every active integration, invalid/reordered activity, and invalid inactive-epoch input. No production detector code changed. This turn does not claim a newly completed full repository test run.

Public freeze `ec23df9a02563b12a2c2a1396d705ba3c290dc74`, tree `63b84738c1cf8572ba79ad4167df57056fac1d4b`, was ref-verified before the 512-truth comparison. All inputs, code and per-truth checkpoint identities are retained.

Result identity: `893c066ccfadbd7cc1cac25832cc671aaa3d34714e501bd0bcff078253f2288e`.

## Decision and next stage

Active-epoch association removes a genuine restriction of the old definition, but is a renamed endpoint rather than an implementation repair. It is useful progress without establishing an increase in detection probability. The remaining geometric ceiling is 167/512 = 32.6171875%; another S/N-only extension still cannot reach 50%.

Before a new calibration campaign, audit the remaining bank/track geometry on active epochs. That audit should distinguish no common carrier interval from an interval falling between carrier cells or outside the grid. It can determine whether bank coverage or a separately justified width-dependent association needs work. Keep the present 20 Hz results intact; do not tune an acceptance threshold to the observed support count.

The deterministic future-anchor inventory selects 21 nonempty cells from 24 possible (category, activity, width 1/129) combinations by the lowest original truth ordinal. Empty combinations are explicit nulls. Selection uses this geometric result and precedes any new spectral read. The inventory is a proposed validation set, not evidence that anchors have been replayed.

A future scorer must tie its evaluated activity hypothesis to the labelled truth-active subset, while preserving full all-epoch/all-width two-pass mask dependencies. It requires a separate freeze and exhaustive real-data comparisons. Old M39 anchors cannot certify the changed endpoint. No new spectral samples, masks, injected spectra, scores, calibrated sensitivities or technosignatures are reported here.

## Restart

geometry.json contains the full set of 512 sealed per-truth checkpoints, so the result can be verified without telescope data. The runner regenerates the metadata comparison when local checkpoints are absent. truth_summary.csv offers a compact inspectable inventory. The report generator verifies config, code, checkpoint hashes and totals before emitting the summary.

```bash
PYTHONPATH=src:scripts python scripts/m43b_active_support.py
PYTHONPATH=src:scripts python scripts/m43b_result_report.py
PYTHONPATH=src:scripts python -m unittest discover -s tests -p 'test_m43*.py' -v
```
