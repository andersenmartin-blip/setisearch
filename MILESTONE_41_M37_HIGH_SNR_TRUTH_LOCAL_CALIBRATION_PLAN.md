# Milestone 41 M37 higher-S/N truth-local calibration plan

Status: **PRE-EXECUTION FREEZE — POST-M40 V2; NO M41 INJECTION EXECUTED**.

## Purpose and adaptive boundary

Milestone 40 v2 completed all 6,144 coverage-repaired trials but did not
bracket a score-recovery transition. Its maximum finite truth-local score was
70.08597564697266 at ideal single-epoch S/N 40, below the unchanged
operational threshold 126.20158386230469. M41 is an explicitly post-M40,
separately labelled extension whose only purpose is to measure the same
conditional pointwise endpoint at higher injected strengths.

The M40 result is immutable. M41 adopts no M40 score receipt and does not
reinterpret the M40 zero-recovery levels. The public M40 maximum is used only
to place the new grid: simple proportional scaling puts a possible first
threshold contact near S/N 72, without asserting that recovery is linear.

## Frozen trial inventory

M41 reuses all 512 M40 v2 continuous truths byte-for-byte, including their
motion coefficients, widths, activity subsets, and coverage-repaired carrier
indices. No truth is selected, removed, or moved. Each truth is evaluated at
all 12 exact higher-S/N levels:

`48, 56, 64, 72, 80, 88, 96, 112, 128, 160, 192, 256`.

This gives exactly 6,144 new trials. Trial identities and randomized native
background shifts are newly derived from the sealed M40 v2 aggregate, the
M41 level, and the truth ordinal. No M40 background or score receipt is
reused. The M39-qualified adapter, six exact 1412.5 MHz source products,
native-domain injection, eight spectral widths, four activity subsets,
20 Hz truth-local tolerance, recomputed two-pass mask, and frozen threshold
remain unchanged.

## Execution and stopping rules

Before any injection, the implementation must publish a deterministic start
certificate that binds this plan, the complete trial inventory, source-code
ancestry, the M40 v2 aggregate and ledger, and zero executed M41 trials.
Execution is restartable through immutable canonical per-trial receipts and
may be partitioned only by trial ordinal modulo a fixed shard count.

Aggregation is forbidden unless exactly one valid receipt exists for every
one of the 6,144 trials. Missing, duplicate, extra, identity-mismatched,
coverage-invalid, non-finite-injection, or over-capacity state stops without
an estimate. Existing valid receipts may be reopened but never rewritten.

## Permitted result

M41 may report only the 12 pointwise conditional truth-local score-recovery
fractions, their Wilson 95% intervals, finite-score counts, maximum scores,
and the first tested level with any recovery plus the first tested levels—if
any—at or above recovery fractions 0.5 and 0.9. Interpolation between levels
is forbidden.

The result is not end-to-end detector completeness. It does not calibrate
physical-veto survival or the global false-positive field, does not transport
to an occurrence-rate constraint, and cannot support a technosignature
claim. Cases with no truth-local candidate cell or no finite unmasked score
remain valid no-recovery outcomes rather than missing trials.
