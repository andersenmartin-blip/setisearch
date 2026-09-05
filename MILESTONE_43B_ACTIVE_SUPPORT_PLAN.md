# M43B: active-epoch 20 Hz geometric association

Freeze this plan, code and configuration publicly before evaluating the 512
truths. The baseline metadata factor table has already been reconstructed and
matches the historical hashes. No new 512-truth support comparison was read.
This is a prospective specification for a retrospective engineering comparison.

## Named association contract

`m43b-active-epoch-20hz-geometric-association-v1` requires ONE fixed bank template
and ONE fixed carrier-grid cell to be within inclusive 20 Hz of the injected
truth at EVERY integration in each truth-active ON epoch. All integrations
within active epochs are retained. Activity is one of [0,1], [0,2], [1,2],
or [0,1,2]. Inactive epochs impose no association distance constraint.

The 93-template bank, carrier grid, positive binary64 factors and exact distance
expression are unchanged. Spectral width does not change the 20 Hz tolerance.
All 512 original M40 v2/M41 truths remain, including unsupported truths. This
contract is for labelled injection association, not an unlabelled sky search.
No claim is made that dropping epochs is a bug fix or increases detection.

## Fixed evaluation and gates

1. Reconstruct the factor basis and table from frozen metadata; require exact
   historical basis, labels and full-table hashes. No spectra are needed.
2. Validate all 6,144 M41 records through the M42 loader; obtain all 512 truths
   through the unchanged M41 truth validator. Require truth-by-truth agreement.
3. Recompute all-epoch candidate cells and complete plan inventory identities
   for every truth. Require exact agreement with M41, including the 32-fold
   width/activity score-cell expansion. Any mismatch stops the comparison.
4. Compute the active-only candidate set for every truth. Require the old
   set to be a subset of it for each template. Require exact plan identity for
   all-epoch-active truths. Publish totals, activity and width subgroups, and
   the complete per-truth counts and identities. No outcome-based exclusions.
5. Check synthetic multi-integration fixtures against exhaustive distances,
   test epoch-order and invalid-activity handling, and verify no carrier or
   template may change between integrations.

Execution is checkpointed per truth; checkpoints pin the config, inputs, code,
truth and plan identities. Freeze a suggested future anchor list by selecting
the lowest truth ordinal in each (legacy/newly supported/unsupported, activity,
width 1 or 129) cell; omit empty cells transparently. This list is selected
after the geometric comparison and before any new spectral evaluation.

## Claim boundary and next gate

This stage measures geometric association coverage only. It runs no score
adapter, masks, injections, sensitivity calculation or new real-data replay.
The original M41 recovery curve and its denominator are unchanged. A future
score endpoint must explicitly tie the evaluated activity hypothesis to the
truth-active subset; calling the old unrestricted evaluator is not sufficient.
Two-pass masking must continue to use all ON epochs and the full width bank,
including inactive epochs, with full dependency closure. Neither filtering
width nor native injection width is silently used to relax association here.

Before calibration, implement that separately frozen scorer, compare it with
exhaustive real-data anchors, and quantify false associations using labelled
controls. More geometric support alone does not establish higher recovery or
better sensitivity. Full M43 qualification remains open until these gates pass.
