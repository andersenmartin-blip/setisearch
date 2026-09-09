# M43AF preparation: response amplitude and remaining-epoch ON support

**Prepared locally; not publicly frozen or evaluated. No detector rule changes.**

M43AE is scientifically complete. Its full result publication must be resolved
before new scientific evaluation. This document and the measurement module are
a concrete preparation for the next integrated study, not an executed experiment
or a calibration certificate. A native acquisition adapter, independent audit,
explicit new calibration inventory and final executable freeze remain required.

## The two costs must be investigated together

M43AE locates correlated OFF profiles whose individual centers are below 5.5.
It also retains the inherited weak-epoch signal losses. Full-profile amplitude
may recover useful OFF evidence, but a stronger veto without an account of ON
confirmation costs would not qualify an improved detector.

There is an additional selection problem in reusing the M43AE archive. It
queried profiles only after the existing remaining-epoch requirement passed.
For example, the stored `ad_ab_z260` record contains no queried profiles.
Unqueried M43AE links contain neutral `complete=True` placeholders. Those are
not measured weak-epoch responses and must never count as available profiles.
This is a source-schema inspection, not an evaluation of the new statistic.

The new request inventory retains geometry and rank eligibility but explicitly
collects profiles **before** the remaining-epoch cut. It includes every active
epoch, both existing track mappings, and every retained filter width. Keep
counts before and after the old cut, including missing, incomplete and constant
profiles. A failure to obtain required profiles blocks interpretation; do not
average only the available epochs.

## Fixed measurement definitions

Use the existing member carrier, width and integration factors. Both OFF
coordinate hypotheses remain unchanged: `receiver_mean` uses the M43AE fixed
mapping/interpolation, and `candidate_track` uses the same candidate carrier and
template in each scan. Each vector spans exactly 2w+1 samples, centered on the
unchanged member. No displaced maximum, peak search, fitted lag, truth subtraction
or relabeling may determine these measurements.

For two complete vectors a and b, let ca=a-mean(a), cb=b-mean(b). Define the signed
zero-lag projection

    P(a,b) = dot(ca / norm(ca), cb).

A constant template makes P undefined. A constant response to a nonconstant
template gives P=0 and undefined correlation. Keep negative projections.
Record both norms and the ordinary centered correlation as diagnostics.
Mean centering within the queried profile is not subtraction of an uninjected
truth/background realization.

1. **OFF response amplitude:** in each active epoch, project the mapped OFF
   vector onto that epoch's ON shape. For each mapping separately, record the
   arithmetic mean of these epoch projections. Preserve every constituent
   value, coordinate and original center amplitude; do not choose the best
   epoch or best mapping after inspecting the result.
2. **ON confirmation:** select the strongest active ON center, with the earliest
   active epoch resolving an exact tie, as in M43X. Its centered unit vector is
   the template. Project each other active ON vector onto it at the unchanged
   candidate coordinates and record their arithmetic mean. The strongest epoch
   never contributes to the tested confirmation amplitude itself. Save the
   old remaining sum/sqrt(k), its unchanged 5.5 cut and its original outcome.

ON coordinates do not depend on the OFF hypothesis. Use the direct
candidate-track copy and require the receiver-mean ON copy to agree wherever
available. All ON profile centers must exactly equal the retained epoch score.

These values are **uncalibrated descriptors in score units**. They are not SNRs,
independent-sample averages, Gaussian significances or false-alarm probabilities.
Profiles overlap, filters correlate their samples, and epochs reuse one observing
sequence. Width changes the projection norm. The data-dependent ON template and
strongest-epoch selection must be included in calibration. Neither division by
sqrt(sample count) nor existing single-bin thresholds resolve these issues.

## Evidence acquisition and historical accounting

Treat all 262 M43AE inputs as historical, including its formerly fresh panel.
Retain the one separate baseline, the original historical 83-signal/66-control
group and the additional 64-signal/48-control group; do not combine denominators
silently. There are 246 distinct native payloads, with shared observing data.
Report payload duplicates explicitly and do not count member rows as events.

Rehydrate original geometry decisions and unchanged policy endpoints. Reuse
existing complete profiles only at the exact matching query identity. Rebuild
the necessary native overlays for newly requested pre-confirmation profiles;
do not rerun the 262-case detector or exhaustive alias census. Require source
identities, all 96 anchor arrays, 48 native gathers, calibration binding and
each native overlay identity to match the original evidence. Query bounds and
direct native comparison rules must be frozen with the acquisition adapter.

Record both descriptors for all eligible members, attach truth/policy labels
only in reporting, and publish all gains/losses of any eventual named endpoint.
The arithmetic module accepts no truth label and makes no detection decisions.
Report eligibility, requested/reused/new queries, unavailable/incomplete/constant
profiles, and correlations separately for both mappings, width and activity.
Case-level summaries must retain which members produced them; selecting a
case maximum is a multiple-comparison operation, not additional evidence.

## Required calibration and validation before a decision rule

Do not choose a threshold from the M43AE counterexamples. Before computing new
calibration or validation measurements, publish a second, executable freeze
containing all of the following:

- An explicit inventory of null shifts excluding all 1,792 prior rows by exact
  identity, plus disclosed dependencies between new rows on the same observing
  data. Training and held-out inventories must be disjoint and fixed in advance.
- A fixed pipeline that reproduces geometry/rank selection, pre-confirmation
  queries, widths, active-epoch subsets, template selection, both OFF mappings
  and any case-level search/maximization in every null evaluation. Calibrating
  only already-selected signal/control profiles is insufficient.
- A named deterministic training rule for the joint OFF/ON decision boundary
  and its complete handling of missing or undefined measurements. Lock the
  trained boundary before opening held-out results. A two-coordinate boundary
  cannot be inferred from independent one-coordinate calibrations.
- An explicitly listed additional native-injection/control panel with signal-only
  and mixed pairs, broad profiles, unequal epochs and shared-background cases.
  Require zero native-payload overlap with all earlier panels, disclose within-
  panel duplicates, and retain the one-sequence limitation. A genuinely new
  observing sequence is still needed for transfer beyond this dataset.
- Joint gates: signal costs versus neighbor9 and the centered combination,
  control-member leaks and false associations, complete evidence, baseline
  behavior and held-out calibration behavior. Preserve all previously failed
  gates. Passing a conditional shift test alone does not establish a physical
  false-alarm rate or certify an astronomical candidate.

No null rows, independent observations or new native endpoints are generated by
this preparation. No numerical calibration size, decision boundary, or validation
panel is implicitly selected here. Those remain explicit unresolved parts of
the executable protocol; the current module is not a ready production detector.

## Preparation checks and continuation

`src/seti_repeater/response_m43af.py` implements the two measurements and the
pre-confirmation query inventory. Focused synthetic tests check analytic scale,
offset invariance, signed/constant responses, tied epoch selection, missing
evidence, immutable input handling, query deduplication and corruption detection.
They use constructed vectors only, never M43AE values to tune a statistic.

    PYTHONPATH=src:scripts python -m pytest -q tests/test_m43af_response.py

Complete M43AE publication first. Then implement the native acquisition adapter
and an independent scalar arithmetic/profile-coordinate audit; specify the
calibration inventory and prospective validation panel above. Verify the whole
executable freeze publicly before measuring this study. Preserve original M43AE
code, results, archive bytes and all older milestones throughout.
