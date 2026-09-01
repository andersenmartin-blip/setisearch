# Milestone 38 M37 completeness feasibility plan

Status: **RETROSPECTIVE FEASIBILITY FREEZE — NO CALIBRATION RESULT, NO NEW
SPECTRAL ACCESS, AND NO QUANTITATIVE SENSITIVITY CLAIM**.

## Purpose and timing

Milestone 37 Run 006 is closed with zero unresolved scientific candidates, but
its published boundary explicitly leaves measured detector completeness open.
The existing v0.6 candidate completeness design was never promoted from its
prospective/provisional status. It requires 6,144 exact trials and
13,670,713,589,760 score-cell evaluations before its production wrapper can
open.

M38 is designed after the M37 outcome is known. It is therefore a
retrospective calibration plan, not a blind preregistration and not a change to
the frozen M37 detector, threshold, candidate outcome, or Run 004/006 history.
This milestone reads only already-published compact metadata and source code.

## Feasibility decision

The full exhaustive replay gate remains closed. M38 does not reinterpret the
synthetic phase-1, phase-2, or phase-3 known-answer receipts as production
evidence, and it does not make the computation appear feasible by deleting
trials, narrowing the S/N grid, or truncating global records.

The selected next path is a **retrospective truth-local score-recovery
calibration** in the frozen `m37_1412p5` background window. It preserves the
existing 512 physical truths at all 12 exact ideal-S/N levels. Recovery is
limited to the predeclared truth-local endpoint after native-domain injection
and recomputation of the two-pass mask.

That endpoint can support only a conditional score-recovery sensitivity
statement. It does not calibrate survival through physical vetoes, replay the
global false-positive field, establish end-to-end detector completeness, or
by itself justify an occurrence-rate bound. Any later quantitative report must
state both the randomized-background condition and the assumption that a true
score recovery is not lost downstream.

## Mandatory gates before calibration

1. Rehydrate and hash-verify the M37 1412.5 MHz native source products, factor
   bundle, threshold certificate, and exact cache ancestry.
2. Implement a restartable production truth-local adapter with explicit memory,
   mapped-byte, record-byte, and crash/restart receipts.
3. Compare real M37 anchor trials against an exhaustive operational replay of
   the complete 1412.5 MHz window. A mismatch stops the program; anchor success
   does not convert the synthetic references into a global equivalence proof.
4. Freeze the adapter, result schema, and anchor inventory before executing the
   6,144-trial ledger.
5. Account for every frozen trial exactly once. No result is published after a
   missing, duplicate, capped, or truncated trial.
6. Report pointwise score recovery only, with no interpolation, no physical-veto
   survival claim, and no unconditional sensitivity or population statement.

## Stopping rule and output

This feasibility milestone stops after writing a certificate that binds the
M37 outcome, the provisional trial inventory, the unchanged full-replay gate,
the three synthetic reference identities, the selected conditional endpoint,
and the six execution gates. It executes zero injections and reads zero new
spectral values.

The deterministic implementation is
`scripts/m38_m37_completeness_feasibility.py`; its frozen inputs are declared in
`config/m38_m37_completeness_feasibility.json`. The result directory contains
`feasibility.json`, an input manifest, and a result manifest.
