# M43AI — one combined rule and prospective native evaluation

Publish and verify this protocol, its executable code, tests, configuration and
native preflight before selecting the combined model. Publish the exact model
and closed-training accounting in a second commit before any new native
validation input is evaluated. The two publication receipts bind exact bytes.

## Question and retrospective design evidence

M43AH's zero-leak optima lose different required training signals: raw second-
epoch support loses training057/071/085, whereas ON-minus-OFF support loses
training017/031/059/073/087/101. Their disjoint loss lists suggest a union.
This hypothesis and its expected training coverage were conceived after seeing
M43AH. The known-case union is therefore development evidence, not a new
independent test or a revision of M43AH's failed standalone endpoints.

M43AI combines related selection, implementation checks and a prospective
native challenge in one study. It does not repeat M43AF/M43AG/M43AH or the
261 completed historical M43AF acquisitions. Earlier results and all original
scientific pins remain intact. The separate historical archive remains pending;
this study uses the public training records and saved native source caches.

## One deterministic member rule

Retain the original geometry/rank eligibility, carrier, width, template, active
epoch subset, both OFF mappings and M43AF OFF-profile coordinate y. Compute the
two unchanged M43AH features from complete original observables:

- R: the second-largest ON center in the member's two or three active epochs.
- E: the second-largest per-epoch value ON minus max(0, receiver-mean OFF center,
  candidate-track OFF center). Subtract before ranking.

For each of the two closed M43AH families, select the **first** zero-leak
minimum-required-loss state in its published sweep. The ledger enumerates ON
cuts in descending order, so this is the largest ON lower bound among that
family's optima. Keep the state's exact strict OFF ceiling. A null OFF ceiling
means positive infinity; an above-maximum empty ON state is not an eligible
model. There is no pairwise search, averaging of thresholds, margin objective,
new feature, threshold midpoint or adjustment after evaluation.

A member survives exactly when

    (R >= a_R and y < b_R) OR (E >= a_E and y < b_E).

Each rectangle must be satisfied by that same member. Do not combine one
member's ON value with another's OFF value. Missing, undefined or nonfinite
evidence blocks the study, including the second feature if the first passes.
The acceptance function receives no injection truth, signal/control label or
case association. Case-level recovery requires at least one surviving member
with the unchanged activity-subset and <=20 Hz association endpoint.

## Selection and publication gate

Use only the 241 public closed M43AF records and the pinned M43AH feature and
family ledgers at `cc52f3b2f5a0cc3dfbf3dd84f65c14f272e71098`. Their immutable
original decision seal remains
`e1ef8cfc261a4b155695cc61d3cbda875ca35ff9aef7c8b0cff20b03c48bf7a3`.
Verify every original input record, case identity and hash, and the five pinned
M43AH payload hashes. No feature extraction or original detector rerun is needed
for this selection.

Account for all 64 signal cases, not just the 57 required by the union of the
neighbor9 and centered_receiver_off_match_aggregate references. Report each
reference's gains/losses, any control/baseline/null surviving member, false
control associations and unassociated survivors in signal cases. A separate
scalar member reduction checks acceptance and recovery. The union of the two
published selected-state recovery sets must independently match the new
combined recovery ledger.

Training eligibility requires zero losses among the same 57 required signals
and zero non-signal surviving members. Otherwise publish the failed selection
and leave prospective inputs unopened. Even if eligible, the model is a
candidate for this evaluation and is not adopted as the project detector.

After selection, publish and fetch the exact model and training outputs.
The native runner rejects an ineligible model, a changed model seal, a changed
configuration/protocol identity or an absent/mismatched public model receipt.

## New native panel, fixed before scoring

The explicit configuration contains 112 new injection/control specifications:
64 signal cases and 48 control cases. Preserve the original training design's
eight strata and fourteen cases per stratum, including signal-only/mixed pairs,
distributed 17-point profiles, moderate unrelated OFF emission, both unequal
epoch orientations, supported spikes and ON/OFF controls. The four activity
subsets and two carrier regions remain explicit.

For every specification, add **211 channels** to every score_index, including
all component tracks and the reference truth. Multiply every component strength
and reported total strength by **15/16**. Thus carrier centers are 1235 and 3283,
nominal strength is 26.25 and the strong single-epoch interferer has strength 105.
All shapes, relative offsets, motion coefficients, activity subsets, amplitude
ratios and OFF signs remain as specified. This is a deliberately nearby,
slightly weaker challenge on the same observing sequence; it is not a broad
survey over untested parameter space or a new telescope observation.

Generate 128 unique native null rows deterministically from SHA256 of
`SETIsearch:M43AI:native-validation:v1:<counter>`, starting at zero. Read the first
two eight-byte blocks as big-endian unsigned integers. Set shifts to
[0, 128+(u1 mod 3840), 128+(u2 mod 3840)]. Keep the first 128 rows outside the
exclusion inventory with |s1-s2| >=128. Exclude all 1,792 earlier shift rows,
128 M43AF training rows and its 128 still-reserved held-out rows. Explicit rows
are stored in the configuration; random-library versions do not affect them.

Use the unchanged coherent post-normalization operator B_e(row,k+s_e), shared
by ON/OFF in each epoch, without wrap or interpolation. The null evaluates the
full upstream selection, geometry, widths, templates, active subsets,
pre-confirmation measurements and the fixed combined rule. Do not calibrate
only previously retained members. Empty null retained sets supply no conditional
profile tail measurements and no physical false-alarm probability.

The original 112 held-out injections and 128 held-out native nulls remain
reserved and unopened. Their published design metadata is used solely to
exclude reused specifications/shifts; none of their native inputs or outcomes
is created or inspected. Actual new overlay identities must not intersect the
original M43AF prior-payload inventory or its public training inventory.
Within-panel duplicate payloads are disclosed and are not independent noise
realizations. A duplicate may still have a distinct labelled case denominator.

## Native restoration, execution and audits

Restore the six saved native-source backups and match every original source
receipt to its independently published trust anchor. Regenerate the 96 M43P
arrays from those sources and require every original array digest. Preserve
the original cache identities, 48 native gathers, catalogue, factor basis,
geometry and M43Z calibration binding. The preflight checks all zero-translation
score bits and 432 direct native sample/filter calculations. This is restoration
of completed arithmetic, with no new scientific input evaluation.

The native runner reuses the unchanged M43AE upstream and M43AF acquisition and
scalar-audit functions. For each new input it checks native payload novelty
before the upstream detector call, verifies the resulting payload binding,
and collects complete profiles before the old remaining-epoch cut. It applies
the two frozen M43AH feature definitions, independently checks every feature
against original ON vectors and OFF interpolation, and audits the combined
member and case decisions separately. Null rows also retain 432 independent
native sample checks per row.

Use Python 3.12.14, NumPy 2.3.5, Astropy 8.0.1, h5py 3.16.0 and hdf5plugin 7.1.0.
The configuration pins the restored original native code and data dependencies
by file SHA256. It also records the older 940-file pin inventory's identity;
no old scientific file is modified by this study. Standard-library unit tests
cover the new rule, exact ties, truth independence, incomplete evidence,
member/case association, deterministic selection, design transformations,
publication guards and preservation of completed outputs.

Execute the 128 explicit native nulls, then all 112 new injection/control cases
in configuration order. All planned inputs are evaluated even after a scientific
gate failure; a provenance, missing-evidence, arithmetic or integrity failure
stops the run. Save an immutable sealed record after every completed case.
Resume only missing cases after verifying the same model, protocol,
configuration, specifications and completed record bytes. A completed study is
never silently rerun. Computational counts distinguish new executions from
original inputs, regenerated anchors, retained members and independent data.

The single unshifted baseline is already a closed training case and is accounted
for there. It is not rerun or counted as a new validation input.

## Prospective gates and claim limits

Report the 64 signals, 48 controls and 128 native null cases separately. The
required recovery set for the new signals is the union recovered by the two
unchanged reference endpoints on those same new inputs; its size is an output,
not assumed to equal the old 57. Publish all signal failures and per-reference
gains/losses, including signal cases missed by both references.

Passing this same-sequence prospective challenge requires all of:

- No signal loss against either reference.
- No surviving member in any control or native null case.
- No false control association.
- Complete evidence and every independent arithmetic/provenance check passing.
- No overlap with prior native payloads and the fixed public model before scoring.

Any control-leak reduction relative to the references is reported with exact
case identities, not used to excuse a failed zero-control requirement.
Within-signal unassociated survivors are reported separately, never labelled
astronomical detections. No post-test threshold selection is permitted.

Passing is limited to this specified same-sequence native challenge. General
adoption requires an independent observing sequence. No physical false-alarm
rate, astronomical candidate or population completeness is claimed. A failed
test closes this selected model's endpoint without retuning on its outcomes.

## Commands and deliverables

From the science checkout with its original public training archive restored:

```bash
PYTHONPATH=scripts python -m unittest discover -s tests -p 'test_m43ai_combined_rule.py' -v
PYTHONPATH=src:scripts python scripts/m43ai_native_validation.py --runtime-root /path/to/runtime --preflight
# After verified protocol publication:
PYTHONPATH=scripts python scripts/m43ai_combined_rule.py --training-root /path/to/training-checkout
# After verified model publication:
PYTHONPATH=src:scripts python scripts/m43ai_native_validation.py --runtime-root /path/to/runtime
```

Publish the protocol/configuration, tests and preflight; then the model and
training ledger; then all native input records, complete endpoints, inventory,
hashes, audit and readable result. Update PROJECT_STATUS.md and the short main
README with the actual stopping point. Preserve the M33 and LS continuation
tracks and the separately pending historical M43AF archive.
