# M43AF: executable joint response study

**Prospective protocol. No new M43AF scientific measurement may precede public
verification of this complete code/configuration freeze.**

This completes and amends the development draft at 068541a. The raw signed
projection definitions, pre-confirmation query inventory, two-coordinate rule,
112 training inputs and 112 initially unopened validation inputs are unchanged.
All historical M43AE measurements and failed gates remain historical. The study
has one original observing sequence; it does not adopt a production detector
or estimate a physical false-alarm probability.

## Resolved native null operator

The draft did not specify a consistent native resampling operator. Its proposed
256 integer tuples are retained verbatim, as are the 128/128 split and exact
exclusion of all 1,792 earlier tuples. Their **new meaning is native translation,
not circular rotation of integrated proxy scores**. Old and new null laws are
different; their numerical results and denominators must not be pooled.

For each epoch e, both ON and OFF scans and every integration row use

    D_e(row, k) = B_e(row, k + s_e),  0 <= k < N - s_e.

B is the original receipt-verified normalized float32 native source. Native
spacing and assigned frequency zero remain fixed; s is an integer native-channel
translation. The input is explicitly derived after the original fixed
normalization. There is no new normalization, circular wrap, interpolation,
injection, partial window or extrapolation. Paired ON/OFF translations preserve
their shared native offset. Epoch 1 has s=0.

The cropped suffix of each existing filtered native cache is exactly the cache
of D wherever a complete window exists: both sum the same float32 samples in
the same order. The new source/cache objects have distinct types, provenance,
identities and source-family labels. They never claim original telescope
attestations for changed data. The original receipts are read-only.

Recompute all 37 templates, eight widths and six epoch/kind score matrices from
these native cache views, preserving nearest-even mapping and ascending float32
integration. Run the unchanged detector retention, neighbor9 masks, original
rank binding, ON/OFF matching, stationary receiver and geometry attribution on
that same derived source. Acquire both complete response mappings before the old
remaining-epoch cut. Both ON/OFF response coordinates and any centered/local
receiver witness therefore refer to the same derived native realization.

Coverage is checked before use across the full stored proxy support, all
templates and a margin of maximum native filter half-width plus the entire
100 Hz receiver query and four extra channels. Incomplete coverage or capacity
overflow is an explicit failed prerequisite, never a truncated valid null.
The existing 10 retention floor and M43Z reference calibration binding are
unchanged. These new native trials do not overwrite that old certificate.

For each native null, 432 predeclared gather probes cover both scan kinds,
three epochs, all eight widths, templates 0/18/36 and support indices first,
middle and last. Compare exact float32 bits with direct complete native windows.
The independent release audit reads the ORIGINAL unshifted source at k+s,
instead of reading the derived view. Original cache/filter arithmetic and
coordinates are thus checked through two different paths.

An empty retained/query set is a valid empty outcome of this fully specified
native pipeline. It provides no conditional profile-tail observations. Report
that absence explicitly; do not infer a Gaussian significance, profile SNR or
physical false-alarm rate. A proxy-score pre-veto bound alone still does not
substitute for these native pipeline trials. All 128 training native trials
run before fitting; held-out native trials remain unopened until a model is
publicly sealed. The shifts remain dependent within one observing sequence.

## Joint training and immutable decision

For each geometry/rank-eligible member of width w, the rule uses
x=remaining-epoch ON projection mean / sqrt(2w+1), and
y=max(receiver-mean OFF projection mean, candidate-track OFF projection mean)
/ sqrt(2w+1). Accept iff x>=a and y<b. The scale convention does not make samples
independent or replace calibration. Negative values are retained.

The 33 higher quantiles per coordinate and deterministic tie ordering remain
as in the draft. Grid values come ONLY from the 112 new training injection/control
cases. The separate baseline and all 128 native training nulls are additional
joint feasibility constraints; they do not provide quantile-grid values.
Every feasible boundary must recover the union of neighbor9 and centered
combination training signals, with zero surviving control/baseline/null members
and complete, defined required evidence. Nonzero reference recovery is mandatory.
Maximize recovered signal cases, then select the lowest ON bound, then highest
OFF bound. Keep the full grid, all case outcomes and surviving member IDs.

The independent boundary auditor computes higher quantiles with numpy and
array-based member acceptance, checks the entire grid and case reduction, and
selects the optimum independently. Missing/undefined evidence or no feasible
boundary is an explicit failed training outcome. There is no fallback floor,
post-hoc optimization, or tuning against the historical M43AE counterexamples.

Require no exact recorded native-overlay identity overlap with previous
inventories. The configuration pins earlier U/V/W/X/Y/Z ledgers and available
AA/AB/AD/AE records as well as prior identity inventories. Report within-panel
duplicates; component specifications and native payloads are different counts.
Validation must also have no overlap with training. A novelty failure rejects
qualification without rewriting the mathematical fit or its ledger.

Publish and verify model_decision.json, binding the full training-grid seal,
case-record identities, exact chosen boundary or failure, and the freeze commit,
before any historical response measurement or validation. If no model is
feasible, leave both held-out native nulls and the validation injection panel
unopened. Still measure the historical response profiles as a closed diagnostic,
without producing a learned endpoint or counting rejection as successful recovery.

## Historical acquisition and evaluation

Reuse all 262 sealed M43AE inputs: one baseline, 149 original historical cases
(83 signals/66 controls) and 112 formerly additional cases (64/48). Rehydrate
the exact geometry/member decisions and 13 old endpoints; do not rerun their
detectors or exhaustive alias census. Rebuild only the necessary native overlays,
requiring the original native identity. Reuse matching complete profiles and
obtain missing pre-confirmation profiles. Neutral unqueried links are not data.

For every acquired case, the independent scalar/coordinate oracle checks query
selection, old remaining scores, strongest-epoch tie selection, both mappings,
complete spans, signs, norms, correlations and projection means. Relative and
absolute scalar tolerance is 1e-11; retained centers, coordinate mappings and
native float32 comparisons remain exact. Direct native profile checks cover
the center and both shoulders plus both OFF interpolation brackets, for the
first complete case/epoch/width/mapping. Deduplicate repeated native requests
within each case. Preserve all inputs and record each case immediately.

If the model is feasible, apply its frozen boundary to historical and validation
panels separately. Report exact signal losses versus neighbor9, centered
combination, geometry plus original OFF/aggregation, and geometry plus aligned
OFF/aggregation; zero control members/false associations; strict control-leak
reduction versus neighbor9; baseline and native-null outcomes; complete evidence;
and native-payload novelty. Every condition must pass jointly for a development
qualification. General adoption remains false: independent observing-sequence
validation is outside this study.

If training fails, report its precise cause and the measured historical weak
members/profile coordinates, retaining all original 5.5 failures. A descriptive
projection is not a restored detection. The validation panel stays unopened.

## Execution and recovery

1. Restore the original six native sources, all 96 arrays and 48 native gathers.
   Process-isolated sequential recovery changes resource scheduling only.
2. Run the complete focused tests and metadata check. The zero-translation
   preflight must reproduce every original score bit and all 432 direct probes.
   Zero replay is an existing-input arithmetic check, not a new null observation.
3. Publish and independently verify this protocol, all executable files,
   configuration, test log and native preflight before scientific evaluation.
4. Run training, audit its full grid, then publish/verify the immutable model
   decision. Only then run historical diagnostics and, if feasible, validation.
5. Independently audit all record seals, frozen inventories, source reuse,
   native probes, scalar measurements, labels, association membership, model
   grid, case outcomes, novelty and joint gates. Publish results and the full
   lossless ledger with a verified restoration manifest.

The complete no-model branch has 502 recorded evaluations: 262 reused
historical/baseline inputs with new response measurements, 112 new injection
inputs and 128 new native nulls. A feasible model opens another 112 injection
inputs and 128 native nulls, for 742 records. Null trials are always counted
separately from signal/control injection cases. No observation is independent
merely because its translation or injected payload differs.

A runtime interruption resumes only from matching sealed records. A scientific
coverage/capacity failure is recorded and blocks completion; its limits cannot
be changed after inspecting outcomes within this freeze.
