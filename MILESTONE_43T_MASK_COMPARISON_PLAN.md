# M43T prospective paired isolation-mask comparison

## Motivation and frozen alternatives

M43S's retrospective replay located all four strongest combined-profile misses
at the inherited isolation mask. This follow-up tests one specified alternative;
it does not alter M43S, M43R or the general production detector.

Two arms use identical score and native-injection inputs:

- `legacy`: the unchanged M37 mask, union over all eight filter widths, then
  dilation by nine proxy-carrier bins. A seed is >=10 in one epoch and <3 in
  every other epoch at that carrier.
- `neighbor9`: retain a legacy seed only when every other epoch is <3 throughout
  the clipped +/-9 carrier neighborhood **at that same width**. Union the
  remaining seeds across widths and dilate by nine bins as before. Equality at
  3 protects the seed; equality at 10 qualifies it. Never wrap mask edges. Use
  full support before cropping to the 4,097 score carriers. Nine bins is inherited
  from the existing mask dilation; no radius search is conducted.

`neighbor9` can preserve displaced multi-epoch signals, but unrelated nearby
power can also protect interference. It is an experimental alternative, not an
accepted production repair. No parameter changes follow from the new results.

## Fixed scientific and numerical scope

Reuse the exact M43R central grid (~11.6 kHz), the same 37 parent templates,
three ON/OFF pairs in one observing sequence, all eight widths and all four
activity subsets. Verify the retained 96 M43P arrays and original 24 native
cache/gather identities. Reuse all 16 M43S truths and their metadata-selected
near-template perturbations, unchanged. Carrier and anchor remain confounded;
the combined profile does not separate fractional placement, template offset
and intra-integration smearing. This is development on previously inspected
background and known injection truths, not an independent blind experiment.

Test strengths **0, 6, 8, 12, 32**. These cover the earlier ideal transition,
combined-profile emergence and documented strong-signal reversals. Strengths
2 and 4 are not repeated in this focused comparison. Each profile has eight
truths at every included strength. The total is 64 distinct nonzero injection
inputs, each executed through both arms: 128 injected detector executions.
Two unmodified-background executions supply 32 explicitly reused zero-level
endpoints. Report all 160 endpoints; do not count the reuses as independent
noise trials. Inject in native data before filtering/gathering, including the
native receiver-signature path. Normalization and profile packets are unchanged.

## Prospective calibration

Before new score evaluation, publish this plan, executable code, focused tests
and exact config/dependency hashes. Generate 256 unique [0,a,b] shift rows with
NumPy seed 430020 and the inherited circular separation and edge guard of 128
bins. Exclude every M43R training and held-out shift. Freeze the first 128 as
training and the other 128 as held-out; both arms use the same rows.

For each arm construct its mask on the uninjected full-support background.
Reuse the existing calibration operation: crop, then co-roll the score vectors
and their fixed masks. **Masks are not re-estimated after scrambling.** This
measures conditional, correlated within-sequence pre-veto score maxima. Neither
training nor held-out outcomes measure an independent physical false-alarm
probability or the false positives of a wholly regenerated telescope sequence.

For each arm independently set threshold=max(10, maximum of 128 training
maxima), with inclusive rank p <=0.01 required afterward. Seal both threshold
certificates before either held-out or signal evaluation. Bind policy, null
vector and threshold identity explicitly to prevent cross-arm handoff. Report
all training and held-out maxima and inclusive held-out threshold exceedances.
There are 256 unique new resamplings and 512 arm-specific maxima, not 512
independent noise realizations. No new telescope data are requested.

The association endpoint is unchanged from M43S: exact activity subset and a
member center track within 20 Hz at **every active integration**, followed by
the inherited physical vetoes and inclusive rank cut. ON/OFF retention,
paired-OFF floor 5.5, receiver aliases, active cut 3, and scoring stay unchanged.
Maximum retained records remains 10,000; exhausting a cap is an incomplete run,
never a truncated successful result. No candidate selection is authorized.

## Evidence, comparisons and decision rule

Save both baseline executions, masks' hashes, calibration bindings, every paired
trial's compact member decisions, unchanged native-overlay receipts, input
hashes, endpoints and logs. Check identical injected-input and overlay identities
between paired arms. Retain per-pair restart checkpoints and publish their entire
sealed contents as one deterministic lossless gzip JSONL ledger, with compressed
and uncompressed SHA-256 hashes. Preserve errors and completed checkpoints.

Report retention, physical-veto and final recovery separately; display all
paired gains and losses and any strength reversals. Compare new legacy outcomes
with M43S at the shared strengths without assuming identical new thresholds.
Present the four previously missed strength-32 truths explicitly.

The alternative merits broader validation only if it recovers all four of those
truths, causes no paired recovery loss at any tested nonzero endpoint, and adds
no held-out pre-veto threshold exceedances relative to legacy. Even meeting all
three conditions is not enough to adopt it for candidate claims: held-out nulls
are conditional and correlated, and the small known-truth population cannot
measure general completeness. A failure remains a useful negative result; do
not tune the radius, thresholds, truth set or result definitions to pass.

Next work should be chosen from the measured failure stage. If the alternative
passes this development gate, use separately frozen broader carrier/template
coverage, independently varied profile effects, interference controls, and
additional observing sequences before scientific deployment.
