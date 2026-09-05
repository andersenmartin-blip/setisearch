# LS4N: reference-only OFF diagnostic counterfactual

LS4M located the measured lower-band HTR rejection in the OFF reference
regions. LS4N asks what additional *diagnostic* recovery would result if
inside-window OFF pulses retained their veto while reference-only OFF pulses
were separately labelled. The operational policy, Stage-1 rejections, ON
reference veto and all existing sky dispositions remain unchanged.

## Measured-data counterfactual

Use only hash-pinned LS4L v2 and LS4M derived ledgers. Reproduce all 256
selected-fragment and 48 fixed-window OFF counts/vetoes before joining.
Classify each selected fragment's control as quiet, reference-only,
inside-only or inside-and-reference, across the unchanged six-width bank.

The original HTR pass requires cross-scale ON support, no ON-reference
pulse, and no OFF pulse anywhere in the inside/reference regions. The
counterfactual diagnostic requires the same support and ON-reference veto,
and no OFF *inside* pulse. Truth recovery additionally requires at least
three of the same injected pulses at two supporting scales, exactly as LS4L.
No pulses are newly detected, merged, reselected or associated in this study.

Retain all 144 configurations and 256 fragment evaluations, including empty
selections and the 64 zero-HTR-level fragment comparisons. Report full-grid
and selected-positive denominators separately. Compare a passing fragment
with its own zero-level result. Original Stage-1 rejection evidence stays
attached, so original joint passes and promoted sky candidates remain zero.

This retrospective comparison conditions on prior digital medium selection.
Zero-level results are not a complete-pipeline false-alarm sample. The A1/B1
backgrounds are reused and medium/HTR amplitude units remain independent.

## Frozen synthetic controls

Eight fixed seeds, white and AR(1) rho 0.8 noise, three ON widths (3/12/100 ms)
and amplitudes (4/8/16 noise-standard-deviation units) yield 144 labelled rows
per family. Every vector is 120 s at 1 ms sampling, with a 30–70 s ON envelope
and the same six jittered pulse times and height-4 plateau convention as LS4K.
No smooth OFF bump is added: only the location of discrete control pulses is
varied here. Control pulses are 12 ms wide and height 16.

Seven numerical families are: train with quiet OFF; train with an OFF pulse
at 50.25 s inside; train with an OFF reference pulse at 15.25 s; train with an
OFF reference pulse at 105.25 s; train with an ON reference pulse at 15.25 s;
plateau-only ON with an early OFF reference pulse; and a single ON pulse at
50.25 s with an early OFF reference pulse.

Two additional causal labels are exact waveform/truth copies of the early
and late OFF-reference train cases, representing possible ON-only pulsed
interference. Total labelled rows: 1,296. Deduplicate numerical evaluations
by waveform and truth identities and report distinct counts. Verify every
clone's inputs and decisions are identical. Repeated null labels, clones and
matched backgrounds are not independent statistical trials.

Apply unchanged LS4E residual processing, widths, thresholds and truth
association before comparing policies. Preserve both pulse-admission and
truth-recovery totals. These collapsed synthetic vectors do not simulate a
medium search, calibrated instrument transfer, physical flux sensitivity or
an observed RFI population. No synthetic Stage-1 endpoint is claimed.

## Evidence and execution

Test the complete Boolean policy table, no-promotion invariant, exact control
placement, signal/clone byte identity, ON-reference and inside-OFF vetoes,
same-fragment zero comparisons and tampered joins before freezing. Publish
the plan, config, implementation, tests and input/dependency hashes before
the full numerical evaluation. Write the measured ledger first and checkpoint
the synthetic ledger after every seed. Preserve any partial run and abort;
the runner refuses an existing output directory. No new radio spectrum or
reserved A3/C1/D1 observation is opened.

Report all outcomes, including any unexpected admissions. Additional recovery
does not authorize a veto change. The explicit interference clones test an
identifiability limitation, not the prevalence of interference. No false-alarm
probability, completeness, independent confirmation or technosignature follows
from this diagnostic experiment.
