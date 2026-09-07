# M43V: component interventions and actual failure-stage evidence

Completed **30 native inputs and 90 detector executions**: 30 exact historical
M43U endpoint replays and 60 new component endpoints. Three baseline replays are
separate. All original calibration summaries, maxima, thresholds and bindings
reproduce exactly. No detector or threshold changes; no new observations.

This is retrospective diagnosis of all eight M43U mixed cases and the two
leaking controls, not independent validation or a new pass/fail gate. Both
M43U development gates remain failed. No astronomical candidate is claimed.

The diagnostic identifies three limitations: the paired-OFF floor leaves three
wide-filter responses just below its rejection boundary; weak displaced power
can both suppress neighbor9's isolation mask and satisfy its active-epoch cut;
and one interferer-only input falsely matches the absent intended truth.

## Matched mixed-input interventions

The first component is the intended strength-32 combined-profile signal; the
second is the strength-128 nearby single-epoch component. Positions, profiles,
strengths and epoch membership are identical in both and component-only inputs.
Association uses the original exact activity subset and <=20 Hz center-track
rule. An association when only the interferer is injected is a false truth
association in this controlled test, never true-signal recovery.

| Policy | Both: truth associations / members | Signal only: associations / members | Interferer only: false associations / members | Both-only coordinates |
|---|---:|---:|---:|---:|
| legacy | 2/8 / 1759 | 3/8 / 389 | 0/8 / 496 | 1233 |
| neighbor2 | 7/8 / 2202 | 8/8 / 584 | 0/8 / 599 | 1410 |
| neighbor9 | 8/8 / 2710 | 8/8 / 584 | 1/8 / 792 | 1673 |

Counts of members are correlated template/carrier/width/activity representations,
not independent physical events. Both-only coordinates are present in the joint
input but absent from the union of the two component-only final sets. Their
presence establishes a conditional interaction in the implemented pipeline,
not which astronomical or instrumental process exists in real observations.
The complete per-case set differences and truth-association outcomes are in
[result.json](results_m43v_component_diagnostic/result.json).

In case 44, the signal alone is recovered by every policy. Adding the stronger
component removes its association under legacy and neighbor2, while neighbor9
retains it. Thus that paired difference is conditional on adding interference.

In case 35, neighbor9 associates one interferer-only member with the absent
intended truth: template 36, carrier 1574, width 129, activity [0,2], score
11.909003 and maximum center-track residual 19.491880 Hz. Its active-epoch
values are 13.691339 and 3.150533. No true signal was injected in this endpoint.
The broad response and marginal second-epoch support pass the declared
association and diagnostic cuts. This demonstrates that those cuts can be
confused; it does not justify retrospectively subtracting one from M43U's
8/8 association count or assigning every jointly associated member to the
interferer. See [the complete false-association record](results_m43v_component_diagnostic/false_truth_associations.json).

## Leaking-control interventions

Case 61: first is ON injection, second is the matching OFF injection; both use
strength 32 at carrier 3584, template 0, all epochs. Case 69: first is the
strength-32 epoch-0 spike at 3584, second is strength-4 power at 3590 in epochs
1 and 2, template 36. Counts below are final diagnostic member coordinates.

| Case / policy | Both | First only | Second only | Both-only coordinates |
|---|---:|---:|---:|---:|
| 61 / legacy | 3 | 155 | 0 | 0 |
| 61 / neighbor2 | 3 | 155 | 0 | 0 |
| 61 / neighbor9 | 3 | 155 | 0 | 0 |
| 69 / legacy | 0 | 0 | 0 | 0 |
| 69 / neighbor2 | 0 | 0 | 0 | 0 |
| 69 / neighbor9 | 1 | 0 | 0 | 1 |

The fixed historical probe coordinates were declared before M43V execution:
case 61 carriers 3610–3612, width 65, template 0, epochs [0,1,2]; case 69
carrier 3588, width 9, template 36, epochs [0,2]. Full probe traces include
scores, masks and contributing isolation seeds even when a probe is not retained.

| Case / policy / carrier / width | Paired OFF maximum | Retained OFF match | Qualified receiver epochs | Alias match |
|---|---:|---|---:|---|
| 61 / legacy / 3610 / 65 | 5.436803 | False | 3 | False |
| 61 / legacy / 3611 / 65 | 5.362956 | False | 3 | False |
| 61 / legacy / 3612 / 65 | 5.488204 | False | 3 | False |
| 61 / neighbor2 / 3610 / 65 | 5.436803 | False | 3 | False |
| 61 / neighbor2 / 3611 / 65 | 5.362956 | False | 3 | False |
| 61 / neighbor2 / 3612 / 65 | 5.488204 | False | 3 | False |
| 61 / neighbor9 / 3610 / 65 | 5.436803 | False | 3 | False |
| 61 / neighbor9 / 3611 / 65 | 5.362956 | False | 3 | False |
| 61 / neighbor9 / 3612 / 65 | 5.488204 | False | 3 | False |
| 69 / neighbor9 / 3588 / 9 | -0.787702 | False | 0 | False |

Paired-OFF rejection uses an inclusive 5.5 single-epoch floor at the exact
same template/carrier/width. Retained OFF-track matching uses 20 Hz tolerance.
Receiver-alias rejection requires qualifying signatures and a matching distinct
identity component in at least two active epochs. All actual measurements and
decisions, including component-only probes, are in
[failure_stage_trace.json](results_m43v_component_diagnostic/failure_stage_trace.json)
and the [complete ledger](results_m43v_component_diagnostic/case_audits.jsonl.gz).

Case 61 has no masking at the three probes. Adding the OFF component removes
152 of the 155 ON-only final coordinates, leaving three unchanged coordinates.
Their paired-OFF maxima are 5.436803, 5.362956 and 5.488204, all below 5.5.
No retained OFF track matches, and the executed receiver-alias search finds
no cross-component match despite three qualifying signature epochs. This is
a remaining boundary failure of the combined rules, not missing OFF input.

For case 69, the first component alone gives epoch scores 10.577853, 1.565340,
2.525096 at the fixed width-9 probe. Adding the weak second component changes
the latter two values to 2.898673 and 3.858429. Epochs [0,2] then satisfy the
minimum of 3 and yield stack score 10.207994. Of the 16 original isolation
seeds able to mask the probe, legacy retains 16, neighbor2 retains 11, and
neighbor9 retains none. The first component alone still leaves six neighbor9
seeds. This intervention therefore both removes exclusion and supplies the
second active epoch. Neither component alone has a final member. Receiver
peak scores 3.196169 and 1.854530 are below the 5.5 qualification floor, so
zero epochs qualify for alias matching. The ledger's seed traces reproduce
the actual mask bit for every probe and policy.

## Next experiment

The next useful milestone is a prospectively frozen comparison of rejection
evidence that accounts for filter width and the separate contributions from
active epochs. It must include ON/OFF paired signals, dominant single-epoch
power with displaced weak support, and interferer-only truth-confusion controls.
Keep true signals, both mixed components and their matched single-component
inputs in the same panel. Evaluate additional carrier/activity combinations
and a predeclared strength range with new calibration and held-out evidence.

Any proposed width-aware OFF or cross-epoch consistency rule must be defined
before evaluation. Preserve cases 35, 44, 61 and 69 as exposed development
examples, rather than treating successful repairs on them as independent
validation. Include false truth associations in the decision conditions;
recovery counts alone cannot establish that the intended component was found.
M43V supplies the diagnosis; it does not adopt a corrected detector.

## Clarification of the inherited disposition label

`pending_receiver_alias_evaluation` is a legacy output label that remains after
the alias routine has executed if no rejecting alias match is found. It does
not by itself mean that this routine was skipped. The alias certificate,
qualifying epoch count and actual match evidence establish what ran. Earlier
M43U prose cautiously associated the label with incomplete clearance; M43V
clarifies execution without changing any historical member or decision.
No-match under this limited rule is not proof of celestial origin.

## Validation and limits

Two focused coordinate/set-accounting tests pass. The unchanged detector's
earlier numerical tests are reused. This audit verifies 278
pinned files, 30 sealed input records, all 90 endpoints, 30 exact historical
pipeline audits, 13,123 member decisions and all reported set comparisons.
The run revalidates 96 original arrays and 48 native ON/OFF gather anchors.
Completed numerical runtime: 618.3 seconds. Source requests: 0.

The original freeze stopped on a baseline provenance mismatch before any
component input. The [public amendment](MILESTONE_43V_BASELINE_AMENDMENT.md)
restores the exact original baseline call; all scientific configuration values
remain unchanged. The original failure log is retained. Successful baseline and
historical audits still have to match M43U in full, not only in event counts.

No additional nulls, independent background realizations, carrier/activity
coverage, end-to-end completeness or physical false-alarm probabilities are
measured. Component interventions are conditional on this one observing sequence.
Any corrected rule requires a prospective freeze and additional evaluation
combinations; these already exposed cases remain development diagnostics.

- Public execution freeze: `30f2acbea05677b8a7cc4b9b54dbda5e155b5490`.
- Result seal: `40bea2aaaaf9aacd29e556ee4eb0e19b780aa5fa725ae07a9d9ce99d232609e2`.
- Compressed ledger SHA-256: `68568b4e251645f6e8380bb50a7f68036f31ea755098b5e142b979870248ef81`.
- [Frozen plan](MILESTONE_43V_COMPONENT_DIAGNOSTIC_PLAN.md).
- [Audit](results_m43v_component_diagnostic/artifact_validation.json),
  [run log](results_m43v_component_diagnostic/live_run.log), and
  [checksum manifest](RESULTS_MANIFEST_M43V_COMPONENT_DIAGNOSTIC.sha256).
