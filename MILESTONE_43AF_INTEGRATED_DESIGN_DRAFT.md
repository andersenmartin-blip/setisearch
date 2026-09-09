# M43AF integrated study: prospective design draft

**9 September 2026. This is a development checkpoint, not the executable
scientific freeze. New Python checks and native execution have not run.**

M43AE publication is complete. This document adds concrete acquisition code,
an independent scalar check, a deterministic candidate learning rule and
explicit new input inventories to the published M43AF measurement proposal.
The original proposal's qualification requirements remain in force. No M43AF
scientific descriptors, new null scores or native endpoints have been evaluated.

## Joint question and unchanged reference

Can full ON/OFF response amplitudes separate controls while preserving the
signal recoveries of both neighbor9 and the centered combination? A new OFF
veto cannot qualify by hiding the inherited weak-epoch losses.

Keep the existing catalogue, 4,097 score bins, eight widths, four activity
subsets, score arithmetic, neighbor9 masks, geometry decisions and rank
eligibility. Keep the original 10 retention floor and M43Z calibration binding.
The M43X remaining-epoch statistic and its 5.5 floor remain unchanged references.
The proposed named endpoint replaces that final confirmation test only in its
own explicitly labeled comparison. It does not modify any historical endpoint.

All 262 M43AE inputs are historical: one separate baseline; the 83-signal /
66-control group; and the formerly additional 64-signal / 48-control group.
Preserve these denominators, native-payload duplicates and every failed gate.
Do not rerun their detector executions or the exhaustive alias census.

## Acquisition and independent checks

The new acquisition module requests both fixed M43AE mappings at every active
epoch after geometry/rank eligibility, before the old remaining-epoch cut.
It validates every retained ON center against the current score store. It
compares reused real profiles against the exact current overlay measurement;
a neutral unqueried link cannot pass as a profile. Full, incomplete and
undefined evidence have separate counts.

The caller must first reproduce all six source identities, 96 arrays, 48 native
gathers, the original calibration binding and each native overlay payload.
Acquisition does not issue these certificates itself. Rehydrate historical
geometry/member evidence and old endpoints from the sealed M43AE archive.
For new inputs only, use the unchanged M43AE upstream adapter and ten M43AD
reference policies.

For each case and first complete (epoch, width, mapping), check the ON center
and both shoulders plus both interpolation brackets for the corresponding
three OFF samples against direct native float32 arithmetic. Deduplicate repeated
native coordinates within each case, recording their exact identities and bits.
Keep full profile coordinates and values for every requested query.

The independent scalar oracle uses Python scalar operations and math.fsum, not
the numpy projection routine. It checks strongest-epoch tie selection, complete
epoch coverage, signed projections, constituent norms, correlations and means.
Scalar comparisons allow relative and absolute tolerance 1e-11; original centers
and coordinate/interpolation evidence remain exact. The existing independent
M43AE coordinate oracle checks both unchanged mappings. This is a numerical
tolerance, not an uncertainty estimate.

The final release auditor still needs to bind these checks to all input seals,
native receipts, query counts, independent boundary selection and exact case
inventories. The new scalar script alone is not that final release auditor.

## Explicit additional panels

The JSON draft contains the full components and labels of every additional
input, derived by translation of the 112 M43AD additional descriptors. Nominal
strength remains 28 and all other component, width, shape, epoch, unequal-support
and matched-pair definitions remain unchanged.

| Panel | Carrier mapping | Signal cases | Control cases |
|---|---|---:|---:|
| Training | 1280 to 1024; 2816 to 3072 | 64 | 48 |
| Validation, initially unopened | 1280 to 1152; 2816 to 2944 | 64 | 48 |

Metadata comparison finds 112 distinct component specifications in each panel,
no specification overlap between the panels and none with the loaded earlier
panel specifications. Component-specification identity is not native-payload
identity: labels, truth metadata and active-subset bookkeeping can differ while
the actual float32 patches match. Earlier comparable panels had eight such
native duplicates. No distinct-native count is claimed for these new panels
until their payloads are constructed and checked.

Require zero native-payload overlap with all prior inventories and across
training/validation. Report all within-panel duplicates. Every input reuses
the same observing sequence; translated frequencies do not add independent
observations or new sky coverage. These panels cannot establish transfer to a
new observing sequence.

## Proposed deterministic joint learning rule

Raw descriptors stay exactly as defined in response_m43af.py. For each eligible
member of width w, define two coordinates:

- x = mean remaining-epoch ON projection / sqrt(2w+1).
- y = max(mean receiver-mean OFF projection, mean candidate-track OFF
  projection) / sqrt(2w+1).

The maximum across both mappings is fixed prospectively. The length factor is
a deterministic scale convention only. It does not make correlated samples
independent, convert values to SNR/sigma, or replace empirical calibration.
Keep the unscaled projections and both constituent OFF coordinates.

The proposed endpoint m43af_joint_profile accepts a member iff x >= a and y < b.
Missing, incomplete or undefined evidence rejects that member and fails the
complete-evidence gate for the study. Do not substitute partial means or zero.
The geometry/rank query inventory precedes this rule and stays unchanged.

Only the 112 new training cases select a and b. Construct each coordinate grid
from 33 fixed higher order-statistic quantiles i/32: index ceil(i*(n-1)/32),
i=0,...,32, with sorted duplicate values removed. Add an explicitly unbounded
lower x value and unbounded upper y value, represented by JSON null. A null bound
is not a missing measurement. Baseline measurements constrain feasibility but
do not supply grid values.

A feasible pair must:

1. Recover every signal case recovered by either neighbor9 or the centered
   combination (the union of the two reference recovery sets).
2. Leave zero members in every training control and the separate baseline.
3. Have complete, defined evidence throughout the required inventory.

Require nonzero reference recovery, so rejecting everything cannot qualify.
Among feasible boundaries maximize recovered signal cases, then choose the
lowest ON lower bound, then the highest OFF upper bound. Report the entire grid,
case outcomes and responsible member IDs; member counts are not event counts.

If no boundary is feasible, publish the failed training result and no model.
Do not weaken a constraint or use a historical counterexample to select another
cut. Leave the native validation panel unopened. Historical profile measurements
may still be completed as explicitly diagnostic work; no learned endpoint exists
in that branch.

If a boundary is feasible, publish and verify the sealed training/model receipt
before opening held-out null scores or native validation. Lock the boundary.
Evaluate historical groups and validation separately and publish exact gains,
losses, leaking controls and false associations against all retained references.
A later change requires a new prospective study, not retuning this validation.

## Explicit new null inventory and unresolved calibration requirement

The draft enumerates all 1,792 distinct previous shift rows from M43R/T/U/W/X/Z
and 256 newly proposed rows, split 128 training / 128 held out. Exact row overlap
is zero. The grid has 4,097 bins; each row is (0,a,b), with 128 <= a,b < 3969 and
circular distance between a and b at least 128.

Generation is specified in full: xorshift32 seed 430032, shifts (13,17,5),
unsigned 32-bit arithmetic; reject words at or above floor(2^32/3841)*3841,
then take 128 + word modulo 3841. Reject old rows, duplicate rows and rows that
fail the distance requirement. This generator is explicitly new; it does not
claim to replay an earlier numpy RNG stream. Its rows were generated from
metadata only, without inspecting spectral/null scores.

These rows reuse one observing sequence and are dependent. Excluding exact
identities does not make them independent null observations.

**The full selected-null pipeline is still unresolved and blocks the executable
freeze.** It must reproduce retention, masks, physical geometry/rank selection,
both OFF mappings, widths/activity subsets, strongest-epoch template selection,
profile acquisition and final case/member reduction consistently under the
resampling. A shifted ON score array passed to an unshifted native receiver is
not a valid implementation. Selected injection/control profiles alone do not
calibrate the null behavior of the joint rule.

A limited pre-veto bound may be implemented and reported separately: if a new
row's global pre-veto maximum is strictly below the unchanged 10 retention
floor, its ON retained set is empty, so subsequent selection has no members.
A row at or above 10 remains unresolved until the consistent native resampling
pipeline is implemented. Such a bound does not measure the conditional
distribution of the new response descriptors, fit their boundary, or supply a
physical false-alarm probability. It does not satisfy or replace the full
calibration requirement in the original M43AF plan. No bound was evaluated here.

## Execution order and gates

1. Recover the runtime and verify new recovery receipts. Preserve closed old
   evidence; never infer recovery completion from a started shell session.
2. Run the original 28 focused checks and the new acquisition/boundary tests.
   Verify the design metadata locally and finish the independent release
   auditor and consistent selected-null adapter.
3. Publish the complete executable code/configuration/protocol with exact
   input/file hashes and verify the public ref and tree before any M43AF
   scientific measurement. This draft publication is not that authorization
   gate or scientific freeze.
4. Evaluate training and seal/publish its decision. Open held-out validation
   only if the prospective training criteria and calibration prerequisite pass.
5. Audit and publish the full resulting evidence, preserving failure branches
   and all earlier failed gates.

Joint validation requires no losses versus neighbor9, the centered combination
and the historical geometry references; zero surviving control members and
false control associations; strict control-leak reduction against neighbor9;
zero baseline members; complete evidence; disjoint new native payloads; and
the predeclared full calibration checks. Publish every failed condition.
Independent observing-sequence validation remains necessary for general
adoption. No astronomical candidate or physical false-alarm rate follows from
this development pilot.

## Current operational status

The environment disconnected during native source restoration and subsequently
returned environment_offline (409 Conflict). Fresh commands cannot run. GitHub
remained accessible, so this checkpoint's source files and metadata were
prepared and inspected there. Metadata-only inventory checks ran in a separate
JavaScript evaluator. The new Python source and tests have not executed; no
native-recovery completion, new scientific measurement or model is certified.

Run when the runtime is available:

    PYTHONPATH=src:scripts python scripts/m43af_verify_design.py
    PYTHONPATH=src:scripts python -m pytest -q tests/test_m43af_response.py tests/test_m43ae_attribution.py tests/test_m43x_confirmation.py tests/test_m43af_acquisition.py tests/test_m43af_boundary.py

Finish the unresolved full null adapter and final release auditor before
producing the executable freeze.
