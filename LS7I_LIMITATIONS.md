# LS7I limitation analysis and completed plan decision

This is a **retrospective reading of the sealed, audited result**, not another detector experiment. No additional data, fit, threshold, bank, training choice or observing sector is evaluated here. It completes the negative-result branch of the two-week plan.

The one fixed model fails six of twelve signal cells and two of sixty instrumental cells. Its native prediction does not improve the aggregate common-metric residual energy on either sector. The correct decision is to close this ridge-prediction route and preserve the unused-data boundary.

## The signal is protected, but the resulting decision is insufficient

All 7,080 injected additions are exactly zero in the predictor/reference bands. The prediction, local scale and reference are invariant to the injected pulse and parent-local stress. This rules out direct fitting-away of the pulse through those features. It does not guarantee that the new uncertainty-weighted source score remains large enough to accept the pulse.

The additional stellar losses are concentrated in the source-amplitude/noise requirement. The table uses the audited first-failure path: another gate can also fail, so this is an accounting attribution, not a unique causal decomposition.

| Sector | Reference | Lost stellar rows | First failure: source score | First failure: nuisance margin | Base / stress rows |
|---|---|---:|---:|---:|---:|
| 29 | ls7g_broad_minus1 | 174 | 174 | 0 | 113 / 61 |
| 29 | ls7h_augmented_minus1 | 165 | 165 | 0 | 106 / 59 |
| 29 | static | 32 | 32 | 0 | 21 / 11 |
| 32 | ls7f_broad_minus1 | 365 | 331 | 34 | 216 / 149 |
| 32 | static | 261 | 246 | 15 | 154 / 107 |

A row can appear against multiple references. In particular, these row/reference totals cannot be summed into a count of independent missed observations. Every individual loss remains listed in [SIGNAL_LOSSES.md](results_ls7i_background/SIGNAL_LOSSES.md).

## Error calibration changes substantially across sectors

The primary and static ablation use separate, nested held-background error covariances. The following trace ratio is computed from those already published covariance matrices, across all thirty anchor/width folds per sector.

| Sector | Minimum covariance trace ratio | Median | Maximum | Native residual-energy ratio |
|---|---:|---:|---:|---:|
| 29 | 0.980910 | 1.062948 | 1.159923 | 1.008294 |
| 32 | 1.023596 | 6.232691 | 18.390124 | 1.001058 |

Sector 32’s conditional calibration covariance is much broader in this summary than the static covariance, while the native prediction provides essentially no aggregate improvement. Thus both the prediction and its generalization error matter to the poor weak-signal result. A covariance trace includes all pixel directions, including components projected out during fitting; it does not by itself measure uncertainty along the stellar template or explain every lost row. No alternative covariance, stronger ridge penalty or changed score threshold is tried here.

The native energy ratios are **1.008294** and **1.001058**: about 0.83% and 0.11% above static on the fixed windows. These are descriptive differences on reused contexts, without an independent significance claim. They fail the predeclared non-increase requirement, even though neither sector has a background exceeding the separate twofold stability ceiling.

## Concrete next direction

The next research question should be whether **additional observable instrumental information** predicts the confusing spatial component better than target-aperture sidebands alone. Existing 11×11 cutouts already contain pixels outside the target aperture, so their availability can be assessed on the same closed data. Archived image-motion or centroid indicators are another possible input; their availability and source identity must be checked before they are used.

A useful bounded follow-on would first establish what those observables measure and whether they respond to a stellar pulse. A mission centroid must not be assumed independent of the target signal. Use pulse-protection checks and entire-background exclusions before any detector comparison. Keep any future model and evaluation separately specified, including the signal cost of instrumental corrections. This is a proposed next direction, not an assertion that such information will solve the problem.

Do not open an unused sector, relax the current cuts or extend the current template bank as a repair. The current method remains unqualified, while the project retains a reproducible negative result and a more specific information requirement.

## Reproduce this bookkeeping

```sh
python scripts/ls7i_limitations.py
```

The script first verifies the sealed output hashes, checks its counts against the audited summary, and writes [LS7I_LIMITATIONS.json](LS7I_LIMITATIONS.json) with exact per-fold ratios and provenance. It never rewrites the sealed result directory.

- [Complete joint result and figure](results_ls7i_background/REPORT.md)
- [Independent numerical audit](results_ls7i_background/AUDIT.json)
- [Two-week result](TWO_WEEK_REPORT_2026-09-14.md)
- [Current continuation](LS7I_CONTINUATION.md)
