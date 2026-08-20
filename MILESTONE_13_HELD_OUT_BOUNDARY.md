# Milestone 13 held-out boundary

Status: detector boundary fixed before target selection and spectral inspection.

Milestone 13 is the first independent application of detector v0.5.0. Its target-specific preregistration must be committed before extracting or inspecting any selected spectral payload.

## Selection boundary

The target/cadence must:

- be a public multi-epoch narrowband observation not previously searched or visually inspected by this project;
- provide at least three ON scans interleaved with matched OFF scans;
- use a telescope, observing session, or target payload independent of the M11 LHS 1140 development data; and
- cover the five established 1 MHz test intervals, unless an archive-coverage constraint is documented before payload inspection.

Catalogue metadata and filterbank headers may be inspected to establish identity, cadence, duration, resolution, and coverage. Spectral payload values in the intended search bands may not be inspected before the target-specific configuration is committed.

## Frozen detector boundary

Milestone 13 must use seti-repeater 0.5.0 with the exact `candidate_veto_v0p5` block published in `MILESTONE_12_DETECTOR_V0P5.md`. The v0.4 search bank, recurrence statistic, RFI mask, spectral widths, empirical scramble calibration, and candidate-reporting rules remain unchanged unless a difference is forced by documented data geometry before payload inspection.

Arithmetic-family candidates that do not receive a specific v0.5 veto remain manual-review cases; they are never silently promoted. Any detector or threshold change after spectral inspection ends the held-out test and requires a separately labelled development milestone.

## Claim boundary

A retained Milestone 13 candidate is a follow-up trigger, not a technosignature claim. It requires an independently observed cadence before any stronger interpretation. A null result applies only to the preregistered bands, activity subsets, motion bank, and measured completeness.
