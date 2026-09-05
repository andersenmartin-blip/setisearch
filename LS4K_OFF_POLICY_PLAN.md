# LS4K: counterexamples for OFF-gate deferral

LS4J traced every recovered strong fragment to the original Stage-1 OFF veto.
Before considering a new review path, compare that existing gate with an
additional diagnostic path which evaluates the unchanged LS4E pulse rule but
**retains the original Stage-1 veto and does not promote a sky candidate**.
This is a synthetic policy-level audit, not a new detector qualification or
a reason to weaken the operational veto.

## Two explicitly different input levels

Use stipulated retained-event records as inputs to the actual original
`apply_abacad_veto`: one ON event at score 12, 8500–8503 MHz and 30–70 s;
either no OFF event or one OFF event at score 10, 8496–8508 MHz and 32–96 s.
All ON/OFF thresholds and overlap settings remain those of LS4B. These scores
and events are assumed inputs; **no medium-resolution spectrum or search is
simulated**, and no physical transfer between products is established.

Separately construct collapsed HTR-like vectors, 120,000 samples at 1 ms,
with independent ON/OFF noise plus mean 100. Use white noise and AR(1) noise
at rho 0.8 with stationary unit innovation-derived variance, eight fixed
seeds, LS4G's six separated jittered pulse times, a 30–70 s ON plateau of
height 4, widths 3/12/100 ms and pulse heights 4/8/16 in noise-standard-deviation
units. Use the existing LS4G generator, rectangular sample-center injector
and LS4E evaluator without changing their settings.

The stipulated medium evidence and generated pulse vectors are paired
conditional inputs, not a physically consistent joint instrument simulation.
The goal is to expose policy consequences and counterexamples. A success
cannot certify an end-to-end instrument response or archived candidate.

## Eight frozen scenario families

1. `signal_clean`: six injected ON pulses; quiet OFF; no Stage-1 OFF event.
2. `signal_smooth_off`: same ON pulses; OFF Gaussian bump of height 8, center
   60 s and sigma 20 s; stipulated Stage-1 OFF event.
3. `signal_pulsed_off`: the second scenario plus one 12 ms, height-16 OFF
   pulse at 50.25 s; stipulated Stage-1 OFF event.
4. `signal_reference_pulse`: the second scenario plus one 12 ms, height-16
   ON-reference pulse at 15.25 s; stipulated Stage-1 OFF event.
5. `null_smooth_off`: ON plateau without injected pulses; smooth OFF and its
   stipulated event. Width/amplitude labels repeat the same null waveform.
6. `isolated_on_smooth_off`: one ON pulse at 50.25 s, with grid width/height;
   smooth OFF and its stipulated event.
7. `rfi_clone_clean`: numerically identical to the first scenario, but with
   the hypothetical causal label of local ON-only pulsed interference.
8. `rfi_clone_smooth_off`: numerically identical to the second scenario,
   with that same hypothetical interference label.

The final two are deliberate identifiability counterexamples, not empirical
RFI observations or additional independent trials. An identical input must
receive an identical decision, irrespective of its unobservable causal label.
They test what the rule cannot establish about origin, not how frequently
such interference occurs in real observations.

Cross all eight families with two backgrounds, three widths, three heights
and eight seeds: **1,152 labelled scenario rows**. Reuse matched noise between
families and grid points. Retain every row; report actual unique waveform
pairs and evaluator calls separately. Identical waveform-plus-truth inputs
may share one deterministic evaluation. Preserve input hashes, injected truth,
Stage-1 veto evidence, LS4E support and both pulse-control vetoes.

## Endpoints and checks

The current pass is `Stage1_OFF_survives AND LS4E_pass`. Diagnostic admission
is `LS4E_pass`, with the Stage-1 veto still attached. Also report truth-matched
pulse recovery for both. No diagnostic admission becomes an accepted sky
candidate. Compute all cells and all family totals; no post-result threshold
or scenario changes, and no inferred false-alarm probability or completeness.

Before execution, test the gate truth table, exact OFF boundaries, clone
identity, independent control locations, nonmutation of matched backgrounds
and the full grid. Freeze plan, code, tests, configuration and dependencies
and publish before the numerical scenario evaluation. Verify every clone's
input and output identity and the complete ledger at completion. A partial
run is incomplete and may not overwrite existing evidence.

## Decision boundary

If deferral admits injected trains behind smooth OFF while still vetoing
pulsed/reference controls, it may support a separately labelled review queue.
If an RFI clone is admitted too, that blocks interpreting admission as origin
classification or replacing the veto with automatic scientific acceptance.
Even zero admissions in other negative examples cannot remove this exact
identifiability limitation. A later measured-data diagnostic may inspect
vetoed events while retaining their original rejected status. A3/C1/D1 remain
unopened, and no telescope data are read by this audit.
