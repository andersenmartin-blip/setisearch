# M43Z result: joint OFF-window rejection and signal-retention cost

The frozen experiment completed all 352 inputs and 1,408 paired policy endpoints.
combined: 8 signal-case losses, 33 leaking controls removed; off_window: 3 signal-case losses, 8 leaking controls removed; remaining_aggregate: 5 signal-case losses, 25 leaking controls removed. All policies are additive cuts of the same reference executions.
All three alternatives fail the frozen acceptance gates.
No astronomical candidate or general adoption is claimed. The earlier M43X
signal losses remain unresolved; new combinations cannot erase exposed failures.

## Complete signal and control results

| Policy | Signal associations | Leaking controls | Interferer-only | Supported spike | ON-OFF | OFF-only |
|---|---:|---:|---:|---:|---:|---:|
| neighbor9 | 125/224 | 40/128 | 25/32 | 7/32 | 8/32 | 0/32 |
| off_window | 122/224 | 32/128 | 25/32 | 7/32 | 0/32 | 0/32 |
| remaining_aggregate | 120/224 | 15/128 | 7/32 | 0/32 | 8/32 | 0/32 |
| combined | 117/224 | 7/128 | 7/32 | 0/32 | 0/32 | 0/32 |

Signal association uses the exact injected activity subset and <=20 Hz maximum
center-track residual over every active ON integration. Counts are not independent
physical detections. Pure controls and signal-present inputs retain separate
denominators. Counts in the four control-type columns are leaking cases.

The following predeclared new-panel conditions fail:

- combined: no_signal_case_loss, zero_interferer_only_final_members.
- off_window: no_signal_case_loss, zero_interferer_only_final_members, zero_supported_spike_final_members.
- remaining_aggregate: no_signal_case_loss, zero_ON_OFF_final_members, zero_interferer_only_final_members.

The zero interferer-only-member condition explicitly tests background-supported
single-epoch interference, even when it does not associate with the absent truth.
No condition was weakened after evaluation. Complete gains/losses and Boolean
gates are retained in result.json.

Duplicate-aware control accounting: neighbor9: 40 leaking labels from 30 distinct native patch inventories; off_window: 32 leaking labels from 22 distinct native patch inventories; remaining_aggregate: 15 leaking labels from 11 distinct native patch inventories; combined: 7 leaking labels from 3 distinct native patch inventories. These groups share the
same fixed background; even different patch inventories are not independent
observing sequences.

## Matched signal costs

Every row contains 32 paired input labels, not 32 independent observations.
The last column counts additional policy losses among with-interference cases
that reference still associates. A denominator of zero is undefined, not a zero
false-veto rate. Paired losses/gains compare signal-only to with-interference
under the same policy and can include effects already present in reference.
Mixed-unequal adds ON interference; the other four families add OFF interference.

| Input family | Policy | Signal only | With interference | Paired losses | Paired gains | Added policy losses / reference recoverable |
|---|---|---:|---:|---:|---:|---:|
| distributed17-near-OFF | neighbor9 | 25/32 | 0/32 | 25 | 0 | 0/0 |
| distributed17-near-OFF | off_window | 25/32 | 0/32 | 25 | 0 | 0/0 |
| distributed17-near-OFF | remaining_aggregate | 25/32 | 0/32 | 25 | 0 | 0/0 |
| distributed17-near-OFF | combined | 25/32 | 0/32 | 25 | 0 | 0/0 |
| distributed17-far-OFF | neighbor9 | 25/32 | 25/32 | 0 | 0 | 0/25 |
| distributed17-far-OFF | off_window | 25/32 | 25/32 | 0 | 0 | 0/25 |
| distributed17-far-OFF | remaining_aggregate | 25/32 | 25/32 | 0 | 0 | 0/25 |
| distributed17-far-OFF | combined | 25/32 | 25/32 | 0 | 0 | 0/25 |
| combined-near-OFF | neighbor9 | 32/32 | 8/32 | 24 | 0 | 0/8 |
| combined-near-OFF | off_window | 32/32 | 8/32 | 24 | 0 | 0/8 |
| combined-near-OFF | remaining_aggregate | 31/32 | 7/32 | 24 | 0 | 1/8 |
| combined-near-OFF | combined | 31/32 | 7/32 | 24 | 0 | 1/8 |
| distributed17-moderate-OFF | neighbor9 | 25/32 | 9/32 | 16 | 0 | 0/9 |
| distributed17-moderate-OFF | off_window | 25/32 | 6/32 | 19 | 0 | 3/9 |
| distributed17-moderate-OFF | remaining_aggregate | 25/32 | 9/32 | 16 | 0 | 0/9 |
| distributed17-moderate-OFF | combined | 25/32 | 6/32 | 19 | 0 | 3/9 |
| mixed-unequal | neighbor9 | 32/32 | 26/32 | 6 | 0 | 0/26 |
| mixed-unequal | off_window | 32/32 | 26/32 | 6 | 0 | 0/26 |
| mixed-unequal | remaining_aggregate | 31/32 | 23/32 | 8 | 0 | 3/26 |
| mixed-unequal | combined | 31/32 | 23/32 | 8 | 0 | 3/26 |

All 128 signal/OFF pairs have exactly identical ON native patch payloads. The
near and far OFF offsets are 16 and 96 proxy bins with alternating sign and
strength 4S in the declared active epochs; the added moderate near-OFF family uses strength S. Distributed17 is a specified sum of
17 equal snapped carrier components q-8 through q+8, with total nominal strength S
per epoch. It reuses the existing ordered float32 overlay and filtering. It is
not a measured channelizer model or general broadband completeness statement.

[Breakdowns by strength and each activity subset](results_m43z_joint_controls/activity_breakdown.json) retain all conditional denominators.

[Exact signal-loss members and OFF maxima](results_m43z_joint_controls/signal_loss_evidence.json)
provide ON scores, OFF-window maxima and locations, base decisions and added-cut
reasons. [Interpretation data](results_m43z_joint_controls/interpretation.json)
include every surviving pure-control case. The full ledger preserves all retained
members and all four policy decisions, including rejected and unassociated ones.

## Failure interpretation and next work

The combination removes all eight leaking ON-OFF cases and all seven supported
spikes, but retains seven interferer-only labels representing three distinct
native patch inventories. It loses eight signal-associated cases versus reference.
Both constituent rules have measured costs; none passes every frozen gate.

The OFF extension loses cases 324/336/346: three distinct strength 24 distributed 17
inputs with moderate nearby OFF interference, all with two active epochs. It
retains only 6 of the 9 cases that reference still associates in this family.
The lost members have width 17 and OFF-window maxima 6.478244, 7.891757 or 7.186285,
above the fixed 5.5 floor. Their active ON scores pass the aggregate rule. The
nearby OFF component is separately injected and the ON patch payloads exactly
match the signal-only counterparts. This is a directly measured added signal
cost, not simply a reduction in unassociated hypotheses. The ratio 3/9 describes
this selected within-sequence family, not a general false-veto probability.

The original strong near-OFF distributed controls left no associated signal
under reference: 25/32 signal-only associations fall to 0/32 with strong nearby
OFF, while far OFF retains 25/32. They cannot by themselves estimate the added
cut's cost on reference-surviving distributed signals. The publicly added
moderate level supplies that missing comparison without changing any original
case or looking at prospective results before the amendment.

Aggregation loses cases 171/260/261/265/281. Cases 260/261/265 contain the same
unequal signal under three conditions: alone, with ON interference, and with
nearby OFF interference. Their lost associated member sets and ON scores match;
for example the narrowest member has active scores 4.684855 and 12.707705. Count
these as three gate losses, not three independent signal realizations. The
other mixed-input losses, 171 and 281, have surviving reference associations at
width 129; mixed-case association counts alone do not establish attribution to
the intended component. Case 281 is a three-epoch loss: one lost member has
remaining aggregate 5.344600 below 5.5. Thus the new cost is not exclusively a
two-epoch phenomenon. All five remain failures of the declared no-loss gate.

The residual controls also show two support mechanisms. Cases 6/46/126 share one
strength 96 single-epoch injection; 16/56/136 share its strength 192 counterpart.
Their uninjected supporting epochs already score about 5.501–5.712. Case 96 is a
third native configuration: 19 retained members use three actual active epochs,
although the absent reference-truth label lists only two. Two uninjected epochs
individually score 3.004–4.976, below 5.5, but their combined remaining statistic
passes 5.5 after the strong injected epoch is excluded. Always use actual member
activity, not the injected-truth label, when interpreting these decisions.

## Next useful work

Do not lower 5.5, widen the OFF window further, or adopt the combination on these
results. The observed opposing costs require more information than a single
score floor or a maximum anywhere in a response window.

Use one integrated retrospective comparison of native response shapes and stage
transitions: the three new OFF losses and their signal-only/strong/far counterparts;
the three aggregation-loss families and their matched components; and the three
remaining interference configurations, including case 96's pooled background.
Reuse the completed arithmetic/null evidence and frozen case ledger. Measure the
native ON/OFF footprints, peak centers and widths, and which upstream vetoes
remove associated narrow members in mixed cases before broad ones remain.

The goal is to determine whether a response-matching or per-epoch shape test has
information that separates desired signal from incidental background support.
Such a test is a proposal, not a repair already demonstrated here. Any changed
endpoint then needs its own public freeze, fresh signal/control comparisons and
explicit false-veto costs. Preserve X/Z losses and original denominators. New
calibration shifts must exclude all 1,792 prior rows. This does not add observing
coverage, independent physical false-alarm evidence or an astronomical candidate.


## Frozen scope and checks

New carriers 896/3200, all four active-epoch subsets, existing anchors 0/36,
strengths 24/48, eleven input families: 352 cases with 224 signal-present and 128 pure
controls. There are 340 distinct native patch
inventories. These are correlated interventions on the same observing sequence.
One separate uninjected baseline adds four endpoints to the 1,408 panel endpoints.
No source scope or observing coverage was added.

The original 320 cases are unchanged; a public pre-evaluation amendment appended 32 moderate near-OFF counterparts before any Z scoring. Two composition tests pass. The audit verifies 288 frozen files,
all 352 seals, 33,825 retained reference members and
135,300 policy member decisions, all associations/gates,
128 matched ON payload invariants and exact set intersections. All 96 original
arrays and 48 native gathers match. The unchanged W 4,440 OFF scalar anchors and
X 5,920 aggregate anchors are reused rather than rerun.

Training and heldout each use 128 new shift rows, excluding 1,536 earlier rows.
Training maximum 8.222109, heldout maximum
8.331632, fixed calibrated threshold 10.000000,
heldout exceedances 0/128. Future fresh rows
must exclude 1,792 total prior rows. These within-sequence pre-veto nulls do not
measure an independent physical FAP or OFF false-veto probability.
Numerical experiment runtime: 2288.352 seconds.

The ephemeral workspace had been cleared. Existing archive byte ranges were
redownloaded against original ETags, sizes and segment hashes, then all source
receipts and 96 arrays were reproduced. Recovery is not new telescope coverage.
The initial missing hdf5plugin dependency failure is preserved; installing the
required package restored the already qualified HDF5 runtime. Redundant HTTP
mirror caches were released only after source/anchor verification to stay within
local disk capacity. Source files and anchor arrays were retained. No experiment
rule was changed by operational restoration. Recovery logs are under restoration/.

Public scientific freeze:
[ac2337057670b40438bcbc3ff4c59ec2ed47626b](https://github.com/andersenmartin-blip/setisearch/commit/ac2337057670b40438bcbc3ff4c59ec2ed47626b).
The full gzip is published as three byte segments under ledger_parts/ because
the publishing connection has a 16 MiB request limit. Reconstruct the exact original
with `python scripts/m43z_restore_ledger.py` before audit or checksum verification.
No original record or seal changed.
Result seal: `94cfa4e5b288cb650ad0cc17b064dc0b7258f0362d23e6dcad52d43896c7a850`.
[Plan](MILESTONE_43Z_JOINT_CONTROLS_PLAN.md),
[result](results_m43z_joint_controls/result.json),
[complete ledger and reconstruction instructions](results_m43z_joint_controls/ledger_parts/README.md),
[audit](results_m43z_joint_controls/artifact_validation.json),
[run log](results_m43z_joint_controls/live_run.log),
[checksum manifest](RESULTS_MANIFEST_M43Z_JOINT_CONTROLS.sha256).
