# M43AD: width/track attribution and receiver-aligned ON/OFF comparison

Completed 9 September 2026. The predeclared development experiment is closed.
Public scientific freeze: `f2467ee06deb1391af3643ebedcbddf276dc1ef2`.
The source, plan and tests were publicly verified before the first evaluation.

**All three new policies fail their predeclared gates on both panels.**
Geometry with the original OFF rule recovers two additional historical
signals without adding leaking controls, but does not improve the additional
panel. Receiver-aligned ON/OFF comparison recovers more signals while also
admitting more controls and rejecting one signal retained by the centered
combination. No policy is adopted.

## Complete comparison

**150 base executions and 1,500 paired policy endpoints**: 37 historical inputs
(19 signal-present, 18 controls), 112 prospectively specified combinations
(64 signal-present, 48 controls), and one separate unchanged baseline.
There are **142 distinct native payload inventories** overall.
The additional panel has 104 distinct payloads, with 0 payload identities shared with M43AB.
These are correlated interventions on one existing observing sequence, not
independent astronomical observations or a physical false-alarm calibration.

| Policy | Historical signals /19 | Historical leaking controls /18 | Additional signals /64 | Additional leaking controls /48 |
|---|---:|---:|---:|---:|
| `neighbor9` | 16 | 14 | 57 | 15 |
| `off_window` | 13 | 6 | 55 | 12 |
| `remaining_aggregate` | 11 | 11 | 57 | 6 |
| `combined` | 8 | 3 | 55 | 3 |
| `centered_receiver` | 16 | 14 | 57 | 15 |
| `centered_receiver_off_match` | 16 | 7 | 57 | 13 |
| `centered_receiver_off_match_aggregate` | 13 | 5 | 57 | 5 |
| `geometry_receiver` | 16 | 14 | 57 | 15 |
| `geometry_receiver_off_aggregate` | 10 | 3 | 55 | 3 |
| `geometry_receiver_aligned_off_aggregate` | 13 | 8 | 56 | 6 |

A recovered signal means at least one final member passes the unchanged
activity/track association criterion. It is not proof of the physical origin
of every retained member. A leaking control has any final rank-eligible member.
The added historical control is M43AB fresh032; earlier M43AB /17 control
denominators remain unchanged in their original report.

## What the comparison establishes

Against the original combined rule, geometry plus the original OFF rule
raises historical recovery from 8/19 to 10/19, with the same three leaking
controls. It restores `ab_z171` at widths 9/17 and `ab_z281` at widths
1/3/5/9. On the additional panel, both rules recover 55/64 signals and
leak the same three control inputs: `new004`, `new018`, `new046`.
Those three labels share one native payload; label counts are not three
independent interference realizations.

The aligned combination recovers 13/19 historical signals but leaks 8/18
controls, compared with 13/19 and 5/18 for the centered combination.
It removes `ab_z138` and `ab_fresh032`, but newly leaks `ab_z148`,
`ab_z158`, `ab_z198`, `ab_z278`, and `ab_z318` relative to that combination.
It still loses the weak unequal-epoch `ab_z260/261/265` family.

On the additional panel, the aligned combination recovers 56/64 signals
and leaks 6/48 controls. The centered combination recovers 57/64 and leaks
5/48. Alignment removes the `new032` control but adds `new076` and
`new104`, and loses the previously recovered width-17 signal in `new038`.
It preserves `new003`, which the original combined rule loses.
Among the 32 predeclared signal-only/mixed pairs, mixed-case recovery is
lost in seven pairs for the original and geometry/original-OFF combinations,
five for the centered combination, and six for the aligned combination.

## Mechanisms and limits

The post-run excerpts in `mechanism_examples.json` identify exact members
inside the original sealed inputs; they do not add an evaluated policy.
For the width-129 survivor in `ab_z138`, fixed receiver-coordinate shifts
of about 29–30 bins give correlations 0.739701, 0.810251 and 0.940601.
The latter two epochs trigger the predeclared ON/OFF veto.

That successful stationary-receiver example does not generalize to all
moving ON/OFF controls. The recorded `ab_z158` survivor has only one
qualifying OFF maximum (6.307977); its fixed shift is about -464.956 bins
and its correlation is 0.774079. It remains below the unchanged 0.8 floor,
whereas the original OFF-window rule rejects this control.

The additional `new038` signal exposes a second attribution problem.
Its surviving width-17 member passes geometry and remaining-epoch support.
In zero-based epoch 2 the original OFF maximum is 8.078562 and the aligned
correlation is 0.955689, so the frozen rule rejects the signal. However,
the compared OFF profile is displaced by -474.528 bins and its center is
only 3.255846. The rule combines a qualifying maximum in the original
window with shape agreement at a different coordinate; it does not require
them to identify the same response. This is evidence against treating
that conjunction as sufficient physical attribution. The stored evidence
does not by itself identify the physical cause of the aligned background.

These examples motivate the next integrated study: make the OFF amplitude,
shape and hypothesized track refer to one explicitly attributed response,
while retaining both stationary-receiver and moving-track alternatives.
Simply adding another veto would leave the signal-loss counterexample
unresolved. Specify the joint rule and its signal/control costs before new
evaluation; all M43AD cases are historical after this result. Continue to
treat weak-epoch/background support as a separate requirement. No new
threshold, combined hypothesis or calibration is validated here.

## Predeclared gates

`no_signal_loss` and strict control-leak reduction compare with the
original `neighbor9` reference, not with `combined`. Preservation of the
centered combination is a separate additional requirement. All ten policies
have zero baseline survivors. On the additional panel, geometry alone
retains one false control truth association; the two new combinations
have none but still leave control members.

| Panel and policy | Passed | Failed requirements |
|---|---|---|
| `fresh:geometry_receiver` | False | strict_control_leak_reduction, zero_control_members, zero_false_control_associations |
| `fresh:geometry_receiver_aligned_off_aggregate` | False | no_signal_loss, preserve_centered_combination_signals, zero_control_members |
| `fresh:geometry_receiver_off_aggregate` | False | no_signal_loss, preserve_centered_combination_signals, zero_control_members |
| `historical:geometry_receiver` | False | strict_control_leak_reduction, zero_control_members |
| `historical:geometry_receiver_aligned_off_aggregate` | False | no_signal_loss, zero_control_members |
| `historical:geometry_receiver_off_aggregate` | False | no_signal_loss, preserve_centered_combination_signals, zero_control_members |

Full gain/loss names, control additions/removals and preservation costs against
the M43AB centered combination are in `result.json` (lossless archive).
`case_summary.json` lists all cases and final associated widths.
`paired_signal_costs.json` preserves every additional signal-only/mixed pair.

## Reproducibility and audit

The audit verifies 348 frozen dependencies, 150 sealed inputs,
128,360 policy-member decisions and 1,611 direct native comparisons.
All 38 historical/baseline inputs replay all seven old policies exactly.
An exhaustive oracle checks 2,758,914 cross-identity alias pairs without bucket pruning.
All 205 queried complete aligned profiles reproduce from their stored coordinates,
interpolation brackets and values. Incomplete profile requests: 0.
Repeated member/epoch queries and arithmetic checks are not independent events.

All six original source receipts, 96 original arrays and 48 native gathers
match. Eight focused tests pass. Python 3.12.14 / NumPy 2.3.5 preserves exact
historical replay despite the Python patch change. No new null rows were
generated; the original M43Z calibration and thresholds were restored.
Recorded evaluation wall time: 1093.456 seconds.

```bash
python scripts/m43z_restore_ledger.py
python scripts/m43ab_archive.py restore
python scripts/m43ad_archive.py restore
PYTHONPATH=src:scripts python scripts/m43ad_audit.py
```

The archive restores original gzip bytes and verifies their SHA256 values.
Full native re-execution also needs the original source/anchor runtime.

## Claim boundary

No production rule is adopted. No additional observing coverage, independent
physical false-alarm probability or astronomical candidate is claimed.
Original M43X/Z/AB failed gates and denominators remain public. Weak
unequal-epoch support and background-supported confirmation remain distinct
questions; the 5.5 floor was not tuned to remove a particular control.
