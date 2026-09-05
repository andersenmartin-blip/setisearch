# M43C: cause of the remaining geometric coverage gap

**Completed: 330 of 345 unsupported truths require better track-shape coverage under the fixed 20 Hz rule.**

All 512 M43B active-epoch plan inventories and candidate counts reproduce exactly. The 167 supported truths remain supported. The 345 unsupported truths split as follows:

| Cause | Truths | Fraction of 345 unsupported |
|---|---:|---:|
| No fixed template fits the active track, even with a freely chosen carrier | 330 | 95.65% |
| A continuous solution exists only outside the current carrier range | 9 | 2.61% |
| A continuous solution in range falls between tested carrier cells | 6 | 1.74% |
| Unresolved numerical boundary | 0 | 0.00% |

The diagnosis uses every active integration, one common template and one carrier throughout. Truths with a possible in-range continuous solution take precedence over outside-range solutions. Any ambiguous template would make an unsupported truth unresolved; no truth received that label.

## Activity breakdown

| Active ON epochs (zero-based) | Supported | Track shape | Outside range | Between cells | Unresolved |
|---|---:|---:|---:|---:|---:|
| [0, 1] | 55 | 67 | 3 | 3 | 0 |
| [0, 2] | 32 | 94 | 2 | 0 | 0 |
| [1, 2] | 48 | 73 | 4 | 3 | 0 |
| [0, 1, 2] | 32 | 96 | 0 | 0 | 0 |

Each activity group retains all 128 assigned truths. This is not an equal-truth causal comparison across activity groups.

## Best continuous fit

The best residual minimizes the largest absolute track discrepancy over active integrations, allowing a continuous carrier for each of the 93 existing templates. The minimum across those templates is summarized below. It measures geometric mismatch in Hz, not S/N or detection significance.

| Truth inventory | Minimum | 25th percentile | Median | 75th percentile | Maximum |
|---|---:|---:|---:|---:|---:|
| all | 0.778 | 15.300 | 26.612 | 40.378 | 73.660 |
| unsupported | 5.349 | 26.549 | 34.851 | 45.639 | 73.660 |

The unsupported inventory includes 15 truths with a continuous fit below 20 Hz, explaining why its minimum is below the association tolerance. The other 330 fail because the existing track shapes do not fit, not because the carrier sampling is too coarse.

## Decision

A finer carrier grid within the existing range could geometrically address at most the six between-cell cases: support would be bounded by 173/512 (33.7890625%) under this unchanged bank and rule. Even unrestricted continuous carriers could address only 182/512 (35.546875%). These are geometric bounds derived from this inventory, not proposed detector changes or calibrated recoveries.

The next useful experiment is a separately frozen bank-coverage study at the same 20 Hz tolerance and active-epoch association. Define a family of denser track templates from the existing physical coefficient domain before evaluation, preserve the original bank as baseline, and measure computational cost and held-out geometric coverage. Do not simply add each known injection truth as a template and call that general coverage.

Any chosen bank requires renewed source/cache coverage checks, score/false-association validation and exhaustive real-data anchors. Changing the number of templates also changes the search trials and can invalidate a transferred threshold calibration. M43B’s prospective anchor suggestions remain unexecuted; their suitability must be rechecked for the selected bank. M41 recovery fractions and all historical results are unchanged.

## Verification and limitations

Fourteen M43/M43B/M43C tests passed, including six new cause-classification and minimax checks. The synthetic minimax result is independently checked against a densely sampled objective. This turn does not claim a new full-repository test run. No production detector module changed.

The historical factor basis and table were reconstructed exactly. New active-epoch plans match every M43B inventory digest and cell count. Numerical diagnostics use longdouble with 63 mantissa bits and a predeclared 0.001 Hz ambiguity guard; this guard never changes the 20 Hz acceptance rule. Pairwise minimax bounds and directly evaluated residuals agree within that guard. The continuous calculation is a numerical diagnosis, not a formal real-arithmetic proof.

Public freeze `b8a9cad2f9f70a8392bcc1fdb9e8ca25d6d554b6`, tree `225a2efcf231c5e8b9b98c37327bac74789aa611`, was verified before execution. This is a retrospective metadata diagnosis; no new spectra, masks, injected data or scores were read or evaluated. No sensitivity, occurrence-rate or technosignature claim follows.

Result identity: `6f26717ee0f86271fa9e73a9d187a227721acc3b3fb24397f9c08640bff7b7ed`.

diagnostic.json retains all 512 sealed per-truth checkpoints, cause counts over all 93 templates, the best continuous fit and a hash of the complete template diagnostic inventory. The inventory can be regenerated from frozen metadata and code. truth_summary.csv provides a compact review table. Local restart copies are excluded from Git because the combined diagnostic already retains their complete contents.

```bash
PYTHONPATH=src:scripts python scripts/m43c_coverage_cause.py
PYTHONPATH=src:scripts python scripts/m43c_result_report.py
PYTHONPATH=src:scripts python -m unittest discover -s tests -p 'test_m43*.py' -v
```
