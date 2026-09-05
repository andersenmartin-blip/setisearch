# LS4E v1: synthetic residual-pulse qualification

This stage follows LS4D and is limited to synthetic data. Historical LS1–LS4D
code, freezes and outcomes remain unchanged. It is a new conservative
diagnostic of repeated pulse structure, not a physical diffraction fit.

## Method fixed before the qualification grid

- Include channel centers inside the closed requested band. Validate ascending
  and descending axes, exact edges, clipped coverage and invalid intervals.
- Partition the candidate and both reference regions independently, with a
  2 s guard separating candidate and reference. Within each region remove a
  line joining the first/last-quarter medians in nonoverlapping 2 s tiles.
  Process each final partial tile with the same rule.
- Average residuals at requested 1, 3, 10, 30, 100 and 300 ms widths, rounded
  to integer samples. Normalize each scale by its own scan's outside-envelope
  median/MAD. Ignore incomplete averaging blocks; reject degenerate scales.
- Cluster blocks with score at least 8 when their centers are no more than
  0.6 s apart. Record event times, scores and contributing-block counts.
- Require three separated events matched one-to-one between at least two
  scales, within the larger effective width. Different scales are correlated;
  this is a consistency condition, not independent confirmations.
- Reject when any width contains a pulse in the ON-reference regions or in
  the analyzed OFF candidate/reference regions. The two 2 s guard intervals
  are excluded from both scans' diagnostics. This conservatively penalizes
  contaminated controls, including temporally shifted OFF pulse trains.
- No Gaussian significance, calibrated false-alarm probability or
  astrophysical origin is assigned by these scores.

## Prospective synthetic gate

`config/ls4e_residual_qualification.json` fixes the method, 24 seeds and ten
case families before the first grid run. Every series uses 120,000 samples
at 1 ms, a 30–70 s candidate interval and independent unit Gaussian noise.
Negative families are noise, a +1 plateau, a smooth Gaussian envelope, a
linear baseline, a single gain step, a single impulse, ON/OFF pulse trains,
and ON candidate pulses accompanied by reference-region pulses.

Positive families are periodic and irregular ON-only 12 ms pulses, amplitude
10 relative to unit noise, above a +0.25 plateau. These are engineering test
signals; they are not simulations of sail diffraction. We require zero
passes in each negative family and at least 22/24 recoveries separately for
each positive family. A further native-LS4C-geometry plateau uses the exact
LS4D counterexample seed, timing and sample count and must be rejected.
There is no retuning after the grid is inspected: failure stays a failure.

All unit tests and the frozen code/config manifest must verify as well as
the grid gate. Success only qualifies this synthetic test suite. It does not
estimate completeness or an end-to-end false-positive rate: the small noise
ensemble, fixed candidate window, selected amplitudes and limited artifact
families do not represent the full Stage-1-conditioned real background.
Directional ON-only RFI with the same repeated pulse pattern is intrinsically
indistinguishable by this time-series test. Quantization, saturation, missing
channels, cross-band correlations and native spectral extraction require
separate real-data diagnostics.

## Data boundary

No new radio spectral values are authorized by this qualification file. A
separate LS4F runtime plan must freeze exact files and checksums, old/new
band comparisons, candidate/control inventory, chunked resource limits and
retained diagnostics before re-reading data. That reanalysis remains
retrospective because LS4C's candidate was already seen. Independent data
remain required before candidate promotion. The physical motivation remains
[Guillochon & Loeb (2015)](https://arxiv.org/abs/1508.03043); LS4E's thresholds
and pulse-train examples are project engineering choices, not predictions
derived from that paper.
