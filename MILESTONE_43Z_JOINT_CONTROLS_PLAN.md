# M43Z: prospective joint OFF-response and confirmation cost comparison

Publish this plan, executable code and explicit configuration before evaluating
any new input or calibration shift. M43Y supplies exposed development evidence;
its 34 outcomes are not new confirmation observations. Historical W/X/Y results,
including X's three two-epoch losses, remain unchanged. A passing new-panel gate
would not erase those failures or authorize general detector adoption.

## Inputs and endpoints

352 native input cases, 224 signal-present and 128 pure controls. Four post-cut
endpoints share each one base detector execution (1,408 paired endpoints), plus
one separate uninjected baseline with four endpoints. Cross new carrier centers
896/3200, every two-/three-epoch subset, existing anchor templates 0/36, and nominal
strength 24/48. These are new combinations within one existing observing sequence,
not independent observations or new telescope coverage. Count and publish actual
native patch identity groups; input labels do not establish distinct waveforms.

The original 320 inputs retain their indices. Each of 32 stratum/strength combinations initially contains ten input types:
1. Combined fractional/off-template signal with unequal active strengths.
2. The same signal plus strong single-epoch ON interference.
3. Distributed signal made of 17 equal snapped point components at q-8 through q+8.
4. The same distributed signal plus nearby OFF interference.
5. The same distributed signal plus distant OFF interference.
6. The same unequal combined signal plus nearby OFF interference.
7. Strong single-epoch interferer alone, with the intended central truth absent.
8. Supported spike with weaker displaced support in the other active epochs.
9. Equal ON-OFF control on the exact central template.
10. Nearby OFF component alone, with no injected ON signal.

A pre-evaluation amendment appends 32 distributed17 inputs with moderate nearby
OFF strength S, preserving all original inputs. These match type4 geometry and
type3 ON payload. Report this eleventh family separately from strong near-OFF.
See MILESTONE_43Z_PLAN_AMENDMENT.md for the analytical motivation and first freeze.

Unequal ratios are rotated [1,1/2] or [1,3/4,1/2]. Nearby/distant OFF point
components lie at +/-16 or +/-96 proxy bins and have total epoch strength 4S in
all declared active epochs. Sign alternates by stratum. Single-epoch ON interference
has strength 4S at +/-12 bins; supported-spike weak components have strength S/8 at
+/-6 bins. The configuration fixes every component, order, position and epoch.
Distributed17 has total nominal strength S in each active epoch, divided by17;
it reuses the existing ordered point overlay, not a new filter/profile algorithm.
Association is to its central exact truth, with exact activity and <=20 Hz maximum
center-track error over every active ON integration. Association alone does not
establish physical or causal identification of the intended component.

The four policies are the unchanged neighbor9 reference, the M43W OFF window
alone, the M43X remaining aggregate alone, and their intersection. OFF window:
reject if any actual active epoch's same-template/same-width OFF score anywhere
in the inclusive q +/- floor(width/2) full-support neighborhood reaches 5.5.
Aggregate: exclude the first strongest actual active ON epoch in canonical order;
float64 sum the rest divided by sqrt(remaining count), require>=5.5. The combined
policy applies both. Preserve existing retention, support>=3, isolation masks,
20 Hz OFF-track matching, paired OFF, receiver aliases and rank. Apply added cuts
after the existing decisions; do not recompute upstream masks/aliases under a cut.
Prior vetoes and rank failures remain failures. Every alternative final set must
be a subset of reference, and combined must equal the intersection of both cuts.

## Calibration, restoration and checks

Use 128 fresh training and 128 disjoint heldout circular-shift rows, seed 430026,
excluding all 1,536 earlier R/T/U/W/X rows. Zero first-epoch shift; every nonzero
shift and mutual circular separation >=128. The fixed new window identity is
m43z-shared-pre-veto-joint-controls. Shared conservative pre-veto maxima retain
support>=3. Threshold is max(10, training maximum), quantile1 and rank ceiling0.01.
Do not adjust thresholds or use heldout outcomes to modify the rules.
This does not measure independent physical FAP or an OFF false-veto probability.

Lost scratch data may be restored from exact historical source receipts and
segment/array hashes. Save new recovery logs under Z and preserve old logs and
results. Archive redownloads add no source scope. Independently verify all 96
original arrays and 48 native gathers before calibration. Reuse W’s 4,440 OFF
scalar anchors and X’s 5,920 aggregate anchors for unchanged arithmetic; do not
repeat their entire census. Two new focused tests cover composition/intersection,
prior-veto and rank preservation, input immutability and source-bound ON evidence.
The separate final artifact audit checks every seal, pinned file, calibration
inventory, retained-member decision, association, intersection and matched native
ON payload. Preserve implementation failures and publish an amendment before
changing scientific semantics.

## Predeclared comparisons and decision

For each alternative versus reference, require all of: no loss of any associated
signal-present case; no increase in leaking control cases; strict reduction in
leaking control cases; zero final members in ON-OFF, supported-spike, OFF-only
and interferer-only controls; zero absent-truth associations in interferer-only;
and zero shared heldout pre-veto exceedances. The zero interferer-only-member
gate explicitly retains Y's background-supported failure mechanism as a condition.
Publish every failing condition; do not weaken gates after scoring.

Separately report each matched signal-only/with-interference pair, including
reference's own losses and gains. For the 128 signal/OFF pairs, verify identical
ON native patch payloads. Report added policy losses among with-OFF inputs that
reference still associates, distinguishing these from losses already caused by
reference or ON interference. Stratify distributed versus unequal signals,
near versus far OFF, strength and activity. Publish exact lost-member ON scores,
OFF-window maxima/locations and rule decisions. Do not pool these signal-present
false-veto costs into the pure-control denominator or count pairs as independent.

Completion requires the full 352 inputs, 1,408 endpoints, audit, loss evidence,
matched comparisons, logs and checksum manifest. Publish checkpoints for recovery
if interrupted. No astronomical candidate, general adoption, independent observing
sequence or unattended continuation is promised. The next decision must address
measured interference rejection and sensitivity cost together.
