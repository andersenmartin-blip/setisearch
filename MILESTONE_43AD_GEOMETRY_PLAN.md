# M43AD: width/track attribution and receiver-aligned ON/OFF evidence

Prepared 9 September 2026 after published M43AC commit
`450b7e9f0233b9715f482157b9bd864929769a6e`. This document specifies new development
endpoints before their numerical evaluation. The 37 historical cases are
regressions selected using known results; only the 112 additional combinations
are prospectively specified inputs. All use the same existing observing sequence.

## Motivation and fixed rules

M43AC showed why replacing every local receiver maximum with a centered sample
loses useful alias witnesses, and why broad ON/OFF response edges can be
displaced. It did not validate a new rule. M43AD tests both mechanisms together
while retaining the original and centered measurements and all earlier failures.

For each retained member and active epoch, calculate the minimum and maximum
predicted receiver frequencies over **all integrations** of its ON track. Pad
each end by `(width//2 + 0.5) * native_channel_spacing`. If the original local
peak falls inside this closed envelope, use its original frequency and score
for alias matching. Otherwise use the original M43AB centered measurement.
Selection uses geometry, never a comparison of scores or injected truth.
Store both source signatures, the envelope and the selection. Envelope overlap
does not prove common physical origin. The existing cross-identity matcher,
20 Hz agreement, two shared epochs, 5.5 score floor and 100 Hz peak search
remain unchanged. No upstream retention, masking or rank rule changes.

The ON/OFF comparison uses a separately named **stationary receiver** hypothesis.
For ON proxy frequency q, calculate its predicted mean receiver frequency using
the inherited sequential reduction of q times all ON integration factors. The
OFF proxy coordinate is that frequency divided by the corresponding mean OFF
factor. Linearly interpolate the stored OFF score profile at that fixed
coordinate. No lag is optimized on the scores. The ON comparison interval spans
one full filter width on either side of the candidate, including shoulders.
The correlation remains the mean-subtracted cosine with the existing 0.8 floor.
This transform aligns mean receiver coordinates, not the complete integration
tracks; record both track spans and treat imperfect agreement as a real limit.

The new ON/OFF veto requires BOTH (a) the original width-aware OFF neighborhood
maximum at least 5.5, and (b) aligned correlation at least 0.8 in any active
epoch. A constant vector has undefined correlation and cannot trigger this
veto. Earlier vetoes retain precedence. Additional profiles are needed only for
rank-eligible, physically surviving members that pass remaining-epoch support
and have a qualifying OFF maximum. If such a requested profile exceeds stored
support, record incomplete evidence, disqualify the member for this endpoint,
and fail the endpoint's development gate. Never silently crop or extrapolate.

Three new paired policies are:

1. `geometry_receiver`: geometry-based receiver selection alone.
2. `geometry_receiver_off_aggregate`: selection plus the original M43Z OFF
   neighborhood and remaining-epoch aggregation.
3. `geometry_receiver_aligned_off_aggregate`: selection plus the aligned
   ON/OFF comparison and the same remaining-epoch aggregation.

All seven M43AB reference policies are evaluated alongside them. The production
detector is unchanged. The 5.5 aggregation floor is not raised to remove the
known near-boundary `fresh032` control. Weak unequal-epoch support remains a
separate open problem, including the 260/261/265 losses.

## Panel fixed before execution

- Historical: all 36 original M43AB historical inputs, plus its `fresh032`
  control, now explicitly historical: **19 signal-present and 18 controls**.
  Exact prior audits, signatures and all seven policy decisions must replay.
- Additional: carriers **1280 and 2816**, nominal strength **28**, all four
  activity subsets, anchors **0 and 36**, and all seven M43AB case types:
  combined-unequal, mixed-unequal, distributed17, distributed17-moderate-OFF,
  interferer-only, supported-spike, and ON-OFF. This gives **64 signal-present
  and 48 control inputs**. Translate the original component frequencies and
  scale all component strengths proportionally; preserve profiles and order.
- One separate unchanged baseline. Total: **150 base executions and 1,500
  paired policy endpoints**. Count distinct native payload inventories as well
  as labels. These are correlated interventions, not independent observations.

The 112 additional component specifications must differ from all 148 old M43AB
specifications before execution. Equal resulting payloads must be counted and
reported honestly. The native noise and telescope sequence remain reused.

## Gates, checks and interpretation

For each panel and new policy, retain the prior gates: no loss of reference
`neighbor9` signal-associated inputs; zero surviving control members; zero false
control truth associations; strict reduction of leaking controls; and zero
baseline survivors. Also require preservation of every signal-associated input
recovered by the M43AB centered combination, and complete requested additional
evidence (including baseline). Report the exact gained/lost inputs and paired
signal-only/mixed costs. Passing these development gates would justify further
qualification, not general adoption or an astronomical claim.

Restore all six original source receipts, 96 original anchor arrays and 48
native gathers exactly. Reuse unchanged arithmetic evidence rather than rerun
the completed census. The new runtime is Python 3.12.14 / NumPy 2.3.5; the patch
version change from historical Python 3.12.13 must not excuse a failed byte
replay. Pin the actual dependency versions in the new configuration.

Known-answer tests cover narrow/broad attribution, full integration tracks,
envelope boundaries, geometry-fixed fractional alignment, constant profiles,
and explicit incomplete support. In each input, independently compare the
first queried epoch/width's ON center and shoulders and both OFF interpolation
brackets with direct native-window arithmetic. Retain full sampled profiles,
coordinates and weights for post-run reconstruction of every correlation.
Audit every input seal, decision, recovery association and historical replay.

Publicly commit the plan, implementation, tests and hash-pinned configuration
and verify the remote tree **before any M43AD endpoint evaluation**. Resume only
sealed inputs for that exact freeze; preserve failed logs and make any repair
explicit. Restore the existing M43Z calibration without generating new null
rows. Any future new null inventory must exclude all 1,792 previous rows.

No additional observing coverage, physical false-alarm calibration or candidate
is claimed. Original M43X/Z/AB denominators and failed gates remain intact.
Owner authorization in PROJECT_DIRECTION.md covers publication on
`m43-support-qualification` and README updates on `main`. No delegation.
