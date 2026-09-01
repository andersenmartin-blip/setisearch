# Milestone 38 M37 completeness feasibility result

Status: **FEASIBILITY PROTOCOL FROZEN — FULL REPLAY GATE CLOSED; NO
CALIBRATION RESULT AND NO QUANTITATIVE SENSITIVITY CLAIM**.

M38 reproduced the exact M37 Run 006 outcome boundary from four hash-pinned
inputs. The source run remains `outcome_complete`, reports
`closed_no_unresolved_scientific_candidates`, contains zero unresolved
candidates, and has no measured completeness result.

## Preserved full-replay gate

The provisional v0.6 design allocates 512 truths at each of 12 exact S/N
levels, for 6,144 trials. One exhaustive 1412.5 MHz window replay evaluates
2,225,051,040 score cells; the full design therefore requires exactly
13,670,713,589,760 score-cell evaluations.

The production status remains
`mandatory-full-replay-benchmark-not-yet-passed`. M38 permits neither
truncation nor an unreported trial reduction. The three synthetic sparse
reference receipts remain known-answer evidence only; their production
equivalence flag is false.

## Selected next path

M38 freezes a retrospective truth-local score-recovery calibration for the
existing `m37_1412p5` background and retains the complete 512-by-12 trial
inventory. Its eventual endpoint is a truth-local score at or above the frozen
M37 threshold after native-domain injection and recomputation of the two-pass
mask.

This is intentionally narrower than end-to-end detector completeness. It does
not calibrate physical-veto survival or the global false-positive field. Any
later numerical output can be described only as conditional score-recovery
sensitivity and must retain the randomized-background and downstream-survival
conditions. M38 itself executes zero injection trials, reads no new spectral
values, and makes no sensitivity, occurrence-rate, or technosignature claim.

## Verification

The deterministic result is
`results_m38_m37_completeness_feasibility/feasibility.json`.

| Item | Value |
|---|---|
| Certificate SHA-256 | `8fa94f07c63ec425294457095bd16d1dc21ec35dc2889cc31a679f383b687d35` |
| Input-inventory SHA-256 | `25315e111c3476338da603a030a19e89d9eb48b39bee0dbc86868ffdd7afeee7` |
| Frozen truth inventory | `0c96a4f1b0d09be3e40048a85cf0fbbd48b3ad1352c7224bfef25523cae42f60` |
| Frozen trial inventory | `c15e656295d3c40f179a2df58e0eff2b6d9129b2550311c3a7c5825579f3176a` |
| Full suite | 311 tests, 0 failures, 1 expected benchmark skip |

The M38-specific tests reject changed input hashes, silent trial reduction,
promotion of synthetic receipts to production evidence, and any premature
quantitative or end-to-end claim. The existing completeness and sparse
reference tests also passed unchanged.

## Next boundary

The next stage is a restartable production truth-local adapter followed by
predeclared real-M37 anchor trials against an exhaustive operational replay of
the complete 1412.5 MHz window. Calibration execution remains blocked until
the source/factor artifacts are rehydrated and hash-verified, the adapter and
output schema are frozen, and the anchor comparisons pass.
