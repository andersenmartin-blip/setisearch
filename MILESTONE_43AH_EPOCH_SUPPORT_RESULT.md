# M43AH — epoch-support development result

**Neither new rule meets the joint training requirements.** Raw second-epoch
support trades more missed required signals for fewer leaking controls;
subtracting the OFF-center penalty worsens both headline costs.

The fixed [plan](MILESTONE_43AH_EPOCH_SUPPORT_PLAN.md), code, 16-test log and
source preflight were published and independently fetched at
[3e6a0b6](https://github.com/andersenmartin-blip/setisearch/commit/3e6a0b60f65d9599ddc78d0aa9ec2e976d5b323f)
before extracting the new features. This is retrospective development using
only the 241 already public M43AF training/baseline/null records.

## Fixed-family results

| Conditional rule family | Minimum losses among 57 required signals with zero non-signal leaks | Minimum leaking control cases when all 57 are recovered |
|---|---:|---:|
| Original M43AF 1,156-point grid, historical | 4 | 8 of 48 |
| Original coordinates, full M43AG boundary family | 1 | 8 of 48 |
| M43AH second-epoch ON support | **3** | **4 of 48** |
| M43AH second-epoch ON-minus-OFF support | **6** | **12 of 48** |

Each M43AH family retains the original OFF-profile coordinate y and replaces
only the ON coordinate z. Its member rule is z >= a and y < b.

For `second_epoch_on`, z is the second-largest original ON center score
within the member's active epoch subset. For `second_epoch_excess`, first
subtract max(0, receiver-mean OFF center, candidate-track OFF center) separately
in each active epoch, then take the second-largest value. With three active
epochs this is the middle value, explicitly testing support in at least two.

All acceptance-equivalent real boundaries were exhausted: 1,743 ON-cut
classes for raw support and 1,758 for excess support. The failed result is
therefore not explained by a coarse threshold grid within these fixed families.
It does not rule out a combination or a different response representation.

## Signal losses are explicit

At every zero-leak optimum the recovered case sets are constant for each
family. There are 50 such ON-cut states for raw support and 117 for excess
support.

| Zero-leak accounting | Raw second-epoch support | Second-epoch excess |
|---|---:|---:|
| Recovered among all 64 signal cases | 54 | 51 |
| Recovered among the fixed 57 required cases | 54 | 51 |
| Lost versus neighbor9, which recovers 57 | 3 | 6 |
| Lost versus the centered reference, which recovers 54 | 0 | 6 |
| Gained versus the centered reference | 0 | 3 |

The raw-support rule loses required cases training057, training071 and
training085. It reproduces the centered reference's recovered signal set at
its zero-leak optima. Training057 and training071 have no associated member
that can avoid every dominating control in this new coordinate family.
Training085 is also lost at every global minimum-loss zero-leak state, without
being individually impossible in isolation.

The excess rule loses required cases training017, training031, training059,
training073, training087 and training101. Each is individually blocked by
dominating control members. It regains training057, training071 and training085
relative to the centered reference, but sacrifices the six cases above.

Seven additional signal cases are outside the fixed 57-case required set and
are missed by both families at these optima. The full ledgers retain all 64
case identities and the exact per-reference gains and losses; those seven
cases have not disappeared from the accounting.

Control counts refer to labelled cases, not independent noise realizations.
There are 48 injected control cases plus 128 native nulls and one baseline.
The latter have no eligible members and provide no conditional profile-tail
observations. All data derive from one observing sequence.

## Verification and preserved evidence

All 244 files from the public training archive were hash checked. The new code
pins the previously published M43AG sweep/auditor and reference summary, and
checks every source record's file hash, content seal, source/configuration
identity, phase, name and native payload identity against the immutable M43AF
training decision.

The 3,497 eligible members retain their old selection and original OFF
coordinate. A separate scalar implementation checks their new features directly
against original stored ON vectors and OFF interpolation samples. It verifies
14,744 member-profile center references, including repeated references.
It computes the order statistic by pair minima rather than the primary sorting
operation. All fixed-tolerance 1e-11 interpolation/feature checks pass; acceptance
comparisons and boundary ties remain exact on the primary binary64 coordinates.

The separate exact-sweep auditor performs 6,095,271 scalar member visits for
raw support and 6,147,726 for excess support. It verifies all cut states,
headline extrema, optimum indices, fixed denominators, inventories and
deterministic dominance certificates (178 and 68 member witnesses,
respectively). Direct case reduction at every zero-leak optimum verifies the
all-signal and per-reference accounting. Eighteen existing M43AG algorithm
tests remain bound to the unchanged dependency; the 16 new M43AH tests pass,
including 100 seeded scalar-oracle fixtures and intentional evidence corruption.

After the run, every output hash and all 241 source record hashes were checked.
All reported extrema and optimum indices were recomputed from the saved ledgers
without rerunning feature extraction or the native detector.

- [Summary](results_m43ah_epoch_support/summary.json)
- [Both feature definitions for every member](results_m43ah_epoch_support/features.json)
- [Raw-support full sweep, certificates and case accounting](results_m43ah_epoch_support/second_epoch_on.json)
- [Excess-support full sweep, certificates and case accounting](results_m43ah_epoch_support/second_epoch_excess.json)
- [Feature audit](results_m43ah_epoch_support/feature_audit.json)
- [Input identities](results_m43ah_epoch_support/input_manifest.json)
- [Output hashes](results_m43ah_epoch_support/manifest.json)
- [Verified pre-execution public freeze](results_m43ah_preparation/public_freeze.json)

## Interpretation and next study

Neither standalone rule is adopted. Raw support improves the all-required
control-leak count from eight to four but loses three required signals in its
zero-leak optimum, versus M43AG's one. Excess subtraction does not yield an
overall improvement.

The two families lose different required cases. Their disjoint loss lists
suggest an explicitly defined OR-combination as a follow-up hypothesis.
Such a combination was not one of M43AH's frozen endpoints. Any selection,
threshold choice and evaluation of that combined rule must be recorded in a
new protocol, with these cases treated as known development evidence and fresh
evaluation inputs reserved for testing. This is a design inference from the
published loss accounting, not an independently validated detector.

The next study should combine candidate definition, selection rules, complete
signal-loss accounting and a prospective native-input evaluation plan, rather
than silently adding a post-hoc third M43AH method. Preserve the old M43AF
held-out panels until an explicit new scope addresses their status. General
adoption additionally requires an independent observing sequence.

M43AH performed new downstream feature/rule-family calculations, with zero full
upstream native-pipeline executions, zero native acquisitions and zero new
observing sequences. No physical false-alarm probability, astronomical candidate
or general completeness estimate is claimed. Both old validation panels remain
unopened. The separate M43AF complete-archive publication remains pending.

Continue from [PROJECT_STATUS.md](PROJECT_STATUS.md).
