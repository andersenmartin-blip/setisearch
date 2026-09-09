# M43AE: joint OFF amplitude, profile and track attribution

Prepared after the verified public M43AD result at `657e0a425ebc340604fc8bf6fd3efb53f39c2eed`.
This development comparison must be publicly frozen, with its implementation,
tests and dependency hashes, before any new endpoint evaluation. It changes no
production policy. The M43AD results and failed acceptance gates remain intact.

## Joint rule and explicit alternatives

M43AD could combine an above-floor OFF maximum at one coordinate with a
correlated profile at another. Its `new038` signal-loss counterexample makes
that conjunction inadequate for attributing a common response. M43AE ties
the amplitude requirement to the center of the actual compared profile.

Keep the M43AD geometry-selected receiver signatures and all upstream
retention, masking, alias, score and rank decisions. Keep the unchanged M43X
remaining-epoch aggregation rule and its 5.5 floor as a separate requirement.
For each rank-eligible, physically surviving member passing that requirement,
query both hypotheses in every active epoch:

1. **Equal mean receiver frequency (`receiver_mean`).** Use the exact M43AD
   geometry-fixed mapping and interpolation of the OFF profile. This aligns
   mean receiver frequency; it does not equate every integration's track or
   provide a complete model of arbitrary stationary interference. Preserve
   both track spans and the original mapping coordinates.
2. **Same candidate track (`candidate_track`).** Use the same template and
   carrier index in ON and OFF. Each scan retains its own integration factors;
   the common source-frame carrier defines the moving-track alternative.
   Sample the OFF scores directly at integer proxy coordinates, without an
   artificial interpolation or a fitted shift. This is one specified moving
   track hypothesis, not a fit over arbitrary interference trajectories.

In each case, the ON interval extends one full filter width on each side of
the candidate. Its center is the member's unchanged ON score. The OFF amplitude
is exactly the center of the OFF vector used for the shape comparison,
including the same interpolation weights under the receiver-mean hypothesis.
A hypothesis rejects the member if, in any active epoch, both center scores
are at least **5.5** and their mean-subtracted profile correlation is at least
**0.8**. The bounds are inclusive. Constant profiles have undefined correlation
and cannot trigger the shape veto. The previous OFF-window maximum is recorded
for diagnosis only; it cannot supply the required amplitude elsewhere.

No fitted lag, truth label, known-injection subtraction, altered score floor
or changed threshold is used. Correlation and co-location are development
evidence, not proof of a signal's physical origin. Complete requested profiles
are required; do not crop, extrapolate or silently skip missing support.

Three paired new policies all include geometry receiver selection and the
unchanged remaining-epoch rule:

- `joint_receiver_off_aggregate`: receiver-mean hypothesis only.
- `joint_track_off_aggregate`: candidate-track hypothesis only.
- `joint_dual_off_aggregate`: reject when either hypothesis rejects.

Missing evidence disqualifies a member for policies requiring that hypothesis
and fails that policy's evidence-completeness gate. It does not disqualify the
other single-hypothesis policy. Prior vetoes retain precedence. Persist unique
profiles once with explicit query IDs and link every member/epoch decision to
its exact profile. Both hypotheses are queried even when the old OFF maximum
is below 5.5; the old maximum must not preselect these new comparisons.

## Fixed panel and reuse

The historical panel contains all 149 non-baseline M43AD inputs: **83
signal-present and 66 control inputs**. Rename their labels with `ad_` and
retain explicit source-file and record hashes. Rehydrate their original
geometry decisions; reuse all ten old policy endpoints without rerunning the
completed detector. Reconstruct only the native overlays needed for the new
profile evidence and require their payload identities to match M43AD exactly.

The additional panel translates the 112 M43AD additional component
specifications from score indices 1280/2816 to **1792/2304**, preserving nominal
strength **28**, every relative offset, component amplitude, profile, component
order, activity subset and both template anchors. It has **64 signal-present
and 48 control inputs**, with the same seven case types and 32 matched
signal-only/mixed pairs. None of its component specifications may equal an
M43AB or M43AD specification. Count resulting native payload identities and
require zero overlap with both earlier inventories for fresh qualification.
Repeated payloads within a panel remain reported as such.

One unchanged baseline is separate. In total there are **262 case evaluations
and 3,406 paired policy endpoints**. Of these, 1,500 old endpoints are reused;
1,906 are newly evaluated (786 new-policy endpoints and 1,120 old-policy
comparisons on the additional inputs). There are 112 new-input detector
executions, not 262 new astronomical observations.

The fresh-input adapter introduces an implementation boundary. After the
public freeze, replay only three named M43AD anchors—`baseline`, `ab_z138`,
and `new038`—through that adapter and require exact equality of all old-policy
decisions, signatures, confirmation evidence and direct checks. These three
regression executions are reported separately. They are not new cases and
do not rerun the historical census. No new rule is evaluated during operational
preflight. All six source identities, 96 old anchor arrays, 48 native gathers
and the old calibration binding must match before execution.

## Acceptance and audit

For each panel and new policy require: no lost `neighbor9` signal-associated
inputs; zero final control members; zero false control associations; strict
control-leak reduction relative to `neighbor9`; zero baseline survivors;
complete required evidence; preservation of every signal recovered by the
centered combination; and preservation of every signal recovered by geometry
plus the original OFF rule. Fresh qualification additionally requires zero
native-payload overlap with the prior inventories.

Report exact gained/lost signal names and added/removed leaking controls
against `neighbor9`, the centered combination, and both M43AD combinations.
Report all 32 signal-only/mixed pairs across all 13 policies. Do not select a
preferred policy after inspecting results or relax a failed gate. Even a
passing development comparison would require further independent qualification.

For the first complete query per epoch, filter width and hypothesis in each
input, compare ON center/shoulders and the OFF interpolation brackets with
direct native-window arithmetic. Deduplicate identical direct coordinates
while checking score equality. Preserve every complete sampled profile,
coordinate, bracket, weight and amplitude. An independent audit reconstructs
the two coordinate mappings, every correlation and center score, every
member-level veto, all truth associations and panel counts from sealed evidence.

The existing M43Z calibration is restored, with no new null rows. All 1,792
previous null rows must be excluded from any future new null inventory. All
inputs reuse one existing observing sequence; intervention counts do not
measure independent sky coverage or a physical false-alarm probability.
Weak unequal-epoch support remains a separate open problem. No astronomical
candidate, general detector adoption or new observation is claimed here.

Owner authorization in `PROJECT_DIRECTION.md` covers ongoing code, plans,
results and logs on `m43-support-qualification`, with README updates on main.
No delegation. Sealed resumable records must match this exact public freeze;
preserve failures and completed original evidence if execution is interrupted.
