# M43X: strongest-epoch-excluded aggregate confirmation

Completed **256 native inputs, 256 shared base detector executions and 768 paired policy endpoints**. One uninjected execution/three endpoints is separate. No candidate or general adoption is claimed.

**The aggregate rule improves on the hard per-epoch rule but fails qualification.**
It preserves 134/160 signal associations versus 132/160 for the hard rule and
137/160 for neighbor9. Both additions reduce leaking pure-control cases from
28/96 to 6/96, but all three ON-OFF leakage cases remain. Neither alternative
passes the unchanged no-signal-loss and zero-ON-OFF-leak requirements.

The new rule excludes the strongest declared active epoch and requires the normalized sum of the remaining epochs to be >=5.5. Both alternatives retain all original neighbor9 vetoes and the shared score threshold.

| Endpoint | Signal associations /160 | Leaking controls /96 | ON-OFF leaks /32 | Supported spikes /32 | False associations /32 | Development gate |
|---|---:|---:|---:|---:|---:|---|
| neighbor9 | 137 | 28 | 3 | 8 | 0 | reference |
| epoch_confirmation | 132 | 6 | 3 | 0 | 0 | False |
| remaining_aggregate | 134 | 6 | 3 | 0 | 0 | False |

## Strength and morphology

Each cell has 16 paired inputs. Signal rows count associations; interferer-only rows count absent-truth false associations; supported-spike and ON-OFF rows count cases with any final member.

| Strength / input | Neighbor9 | Epoch confirmation | Remaining aggregate |
|---|---:|---:|---:|
| 16 / nearest-unequal | 16/16 | 16/16 | 16/16 |
| 16 / combined-equal | 16/16 | 16/16 | 16/16 |
| 16 / combined-unequal | 9/16 | 7/16 | 8/16 |
| 16 / mixed-equal | 14/16 | 14/16 | 14/16 |
| 16 / mixed-unequal | 9/16 | 6/16 | 7/16 |
| 16 / interferer-only | 0/16 | 0/16 | 0/16 |
| 16 / supported-spike | 0/16 | 0/16 | 0/16 |
| 16 / ON-OFF | 0/16 | 0/16 | 0/16 |
| 40 / nearest-unequal | 16/16 | 16/16 | 16/16 |
| 40 / combined-equal | 16/16 | 16/16 | 16/16 |
| 40 / combined-unequal | 16/16 | 16/16 | 16/16 |
| 40 / mixed-equal | 11/16 | 11/16 | 11/16 |
| 40 / mixed-unequal | 14/16 | 14/16 | 14/16 |
| 40 / interferer-only | 0/16 | 0/16 | 0/16 |
| 40 / supported-spike | 8/16 | 0/16 | 0/16 |
| 40 / ON-OFF | 3/16 | 3/16 | 3/16 |

## Predeclared gates and losses

### epoch_confirmation

Signal losses: [2, 132, 180, 226, 228]. Signal gains: [].

- no_increased_leaking_control_count: **True**.
- no_signal_case_loss: **False**.
- strict_control_leak_reduction: **True**.
- zero_ON_OFF_final_members: **False**.
- zero_interferer_only_false_associations: **True**.
- zero_shared_heldout_pre_veto_exceedances: **True**.
- zero_supported_spike_final_members: **True**.

### remaining_aggregate

Signal losses: [2, 132, 180]. Signal gains: [].

- no_increased_leaking_control_count: **True**.
- no_signal_case_loss: **False**.
- strict_control_leak_reduction: **True**.
- zero_ON_OFF_final_members: **False**.
- zero_interferer_only_false_associations: **True**.
- zero_shared_heldout_pre_veto_exceedances: **True**.
- zero_supported_spike_final_members: **True**.

Every lost associated member and its exact epoch evidence is retained in [signal_loss_evidence.json](results_m43x_confirmation/signal_loss_evidence.json). The complete [activity breakdown](results_m43x_confirmation/activity_breakdown.json) and [matched component outcomes](results_m43x_confirmation/matched_components.json) preserve uneven-strength and causal-confusion diagnostics.

## Interpretation and scope

The two-epoch aggregate rule is mathematically identical to the hard minimum rule; all member-level two-epoch decisions verify that identity. With three epochs it pools the two weaker scores and may retain cases the hard floor rejects. Every hard-floor final set is a subset of the aggregate final set, itself a subset of neighbor9. This is not a new independent detection channel.

The 256 declared cases have 244 distinct native patch-payload inventories; duplicate control cases are listed in [input_identity_groups.json](results_m43x_confirmation/input_identity_groups.json). There are 16 strata at new carriers 1280/2816, four activity subsets and two anchor templates. Strengths 16/40 are nominal injection amplitudes, not output SNR. Unequal ratios are rotated [1,1/2] or [1,3/4,1/2]. The panel includes exact paired signal-only, interference-only and mixed inputs. Associations use exact activity and <=20 Hz center-track residual; an association does not demonstrate causal recovery. Cases are correlated digital interventions on one existing observing sequence, not independent observations.

No OFF rule changed; prior V OFF failures remain unresolved regardless of outcomes at new carriers. The exposed W73/74 examples are not counted in this prospective panel. No threshold is fitted after evaluation, no failed condition is weakened, and no general detector adoption follows.

## What the improvement and remaining failures mean

The gain is confined to the three-active-epoch signal cases. The new rule
preserves all 35 of the reference's associations in those 40 cases, compared
with 33 for the hard rule. For two-active-epoch signals both alternatives
retain 99/120, down from 102/120 for neighbor9. This split follows injection
truth activity; unrelated retained hypotheses can have other activity subsets.

The two restored cases, 226/228, are the same strength-16 unequal combined
signal at carrier 2816, anchor 0, without/with its matched interfering component.
They are two paired cases, not two independent successful signal realizations.
For example, their width-3 member at carrier 2816 has active scores
4.751085, 9.539946 and 7.864453. Excluding the largest leaves aggregate score
8.920533, above 5.5, although the weakest epoch fails the hard 5.5 floor.
All five previously lost associated members in each case pass the aggregate rule.

The aggregate rule still loses cases 2, 132 and 180, all with two active truth
epochs and unequal strength-16 signals. Cases 132/180 are mixed-input associations
that their matched signal-only inputs do not reproduce. Their loss remains a
predeclared gate failure; association alone does not prove causal signal recovery.
No criterion is relaxed to discount these cases after seeing their outcomes.

The six leaking pure-control cases under both additions are interferer-only
13/45/109 and ON-OFF 47/79/111. The first three share the same native patch
inventory; the denominator remains declared input cases, not independent
realizations. Their retained members use width 129. ON-OFF case 47 has five
width-129 members; cases 79/111 each have the same width-65 hypothesis. All these
surviving members use two active epochs. The observations of broad filters
justify examining width/response handling next, but this extraction did not
reconstruct their OFF scores and does not establish the exact OFF-veto cause.

The interferer-only survivors are not associated with the absent reference
truth, so zero false truth associations does not mean zero interference leakage.
Moreover the reference already has zero such associations in this panel;
this is not evidence of a comparative false-association repair here.
All three methods retain the same original physical and receiver/alias stages.
The inherited label `pending_receiver_alias_evaluation` can persist after no
rejecting alias is found; it does not mean that evaluation was skipped.

See [the full interpretation](results_m43x_confirmation/interpretation.json),
[matched component outcomes](results_m43x_confirmation/matched_components.json),
and [surviving control member evidence](results_m43x_confirmation/control_survivor_evidence.json).

## Audit correction and publication history

The prospective v1 audit failed its overly broad whole-case activity assertion;
[its actual failure log is preserved](results_m43x_confirmation/artifact_validation_v1.log).
The [public audit amendment](MILESTONE_43X_AUDIT_AMENDMENT.md) corrects the check
to each member's actual activity subset. The v2 audit passes, including all
273 original pins, every seal and association, all 73,227 policy decisions,
subset relations and the unmodified development gates. The original four
focused tests and one new audit regression test pass. No detector, threshold,
input or scientific decision was changed, and no trial was rerun under altered
rules. The initial prepublication approval block was resolved by the user's
explicit ongoing approval in this conversation; the historical pending note
and intermediate 96-case checkpoint remain available.

## Next useful work

M43Y should first reconstruct the surviving broad-filter control cases with
exact baseline and single-component counterparts, and inspect native ON/OFF
response across coordinate and width. Any replay of exposed cases is a
retrospective diagnostic, not independent validation. Preserve the M43X failure.
The two-epoch sensitivity cost also needs an explicit operating decision or
a separately named endpoint; an epoch-aggregation rule cannot change the
mathematical two-epoch identity. Do not lower 5.5 simply to recover these losses.

Before evaluating any new response-aware OFF rule, publish its complete
semantics and prospective controls, including its false-veto cost on distributed
and unequal signals. Exclude all 1,536 earlier R/T/U/W/X shift rows from future
fresh null inventories. No general adoption, new observing coverage, independent
physical false-alarm probability, or astronomical candidate follows from M43X.

## Calibration and verification

Training: 128 fresh shifts, maximum 8.553452; shared threshold 10.000000. Held-out: 128 distinct shifts, maximum 8.319118, 0/128 at or above threshold. All 256 new shift rows exclude 1,280 earlier rows. Shared conservative pre-veto evidence is not independent physical FAP or OFF false-veto calibration.

All 96 original arrays, 48 native gathers and 5,920 scalar aggregate anchors verify. Four focused tests pass. The audit verifies 273 pinned files, 256 sealed inputs, 768 endpoints, 24,409 retained reference records and 73,227 policy decisions, including all associations, gates, subset relations and exact component pairings. Runtime: 1619.4 seconds. New telescope requests: 0.

Public freeze: `0d4406c5a6a7106f49a71d809fc7c79731ccc238`. Result seal: `b46a117e5ebb9782d0a6afa4c802defb59e4be6b01ef6a3800f0c43aa14400aa`.

[Plan](MILESTONE_43X_CONFIRMATION_PLAN.md), [complete result](results_m43x_confirmation/result.json), [ledger](results_m43x_confirmation/case_audits.jsonl.gz), [validation](results_m43x_confirmation/artifact_validation.json), [run log](results_m43x_confirmation/live_run.log), [manifest](RESULTS_MANIFEST_M43X_CONFIRMATION.sha256).
