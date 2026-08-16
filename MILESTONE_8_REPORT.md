# Milestone 8 — Frozen-detector frequency confirmation

## Outcome

Milestone 8 is the independent-frequency confirmation promised after the
post-run Milestone 7 recurrence correction. The final Milestone 7 detector was
frozen before extracting or inspecting two untouched 0.5 MHz planet-frame
intervals: 1405.25–1405.75 and 1423.25–1423.75 MHz.

No candidate was found. The strongest ON-source result was S/N 6.3347 at
1423.628288269 MHz, using a 9-channel filter, projected orbital scale 0.25,
phase offset 0.1 cycle, and epochs 2+3. The 256-scramble global null had median
6.4046 and 99th percentile 7.2519. The empirical global p-value was 0.6031.

The lower confirmation band peaked at S/N 6.1541 at 1405.472141266 MHz, also
with a 9-channel filter. Its per-window p-value was 0.7354; the upper-band
per-window p-value was 0.3502. Neither matched OFF-source hypothesis met the
S/N 3 floor in every claimed active epoch.

## Confirmation status

The configuration was frozen at 2026-08-15T18:34:04Z. Its SHA-256 is
`2e9df9f13f5cf2a3c438f1ffbd20784e76355e66e3fcb90e70f2ff19658a3d6d`.
The eight automated detector tests passed before data extraction.

This is a genuine frequency confirmation: neither planet-frame interval had
previously been searched or candidate-inspected. It is not a temporal
confirmation, because it uses the same three Proxima ON/OFF observing visits as
Milestones 5–7. The distinction is important and is recorded in the frozen
configuration.

The detector retained the final Milestone 7 rules without adjustment:

1. At least two active epochs, with every claimed epoch at S/N ≥ 3.
2. Recurrence S/N equal to `sqrt(N)` times the weakest active-epoch S/N.
3. A per-epoch mask for an isolated S/N ≥ 10 feature whose second-highest epoch
   is below 3, with a 9-channel guard that follows its epoch during shifts.
4. Normalized 1-, 3-, 5-, and 9-channel spectral filters.
5. The same peak floor, clustering tolerance, report limit, template
   multiplicity flag, and arithmetic-frequency-family settings.

The confirmation required no RFI excision: the frozen rule masked zero ON and
zero OFF cells in both bands. This is useful because the ordinary real maxima
and null distribution arise entirely from the recurrence statistic rather than
data-dependent masking. It does not, however, provide a contaminated real-data
test of mask transport; that remains covered by deterministic validation.

## Search scale and candidate audit

The complete search comprises approximately 88,081,056 nominal
frequency/orbit/activity/width trials:

- 2 bands and 262,146 total rest-frequency bins;
- 21 orbital templates;
- 4 allowed two-/three-epoch activity subsets;
- 4 normalized spectral widths.

Candidate reporting retained 75 hypothesis peaks above S/N 5.5. These collapsed
to 69 frequency clusters within 20 Hz, and all 69 were reported because neither
band reached the 50-cluster cap. Every cluster was below the global S/N 7.2519
threshold.

Eleven approximate arithmetic-frequency families were flagged in the lower
band and five in the upper band. They have no bearing on the conclusion because
all members are sub-threshold; the family detector is an RFI-review heuristic,
not a separately calibrated significance test.

## Extended completeness

The pre-registered injection experiment used real 1405.5 MHz planet-frame
background vectors, circularly shifted independently by epoch. Signals were
active in epochs 1 and 3 and used continuous fractional-channel frequencies,
time-averaged sinc-squared leakage, and exact members of the orbital bank.

Four truth templates span mean within-integration sweeps of 0.34, 1.87, 3.64,
and 5.02 channels. With 32 trials per level and the globally calibrated S/N
7.2519 threshold, recovery was:

| Ideal single-epoch S/N | Multichannel | One channel |
|---:|---:|---:|
| 8 | 4/32 (12.5%) | 4/32 (12.5%) |
| 12 | 25/32 (78.1%) | 9/32 (28.1%) |
| 16 | 32/32 (100%) | 17/32 (53.1%) |
| 20 | 32/32 (100%) | 21/32 (65.6%) |
| 24 | 32/32 (100%) | 28/32 (87.5%) |
| 32 | 32/32 (100%) | 32/32 (100%) |
| 40 | 32/32 (100%) | 32/32 (100%) |

For the fastest 5.02-channel-sweep template, multichannel recovery was 4/8 at
S/N 12 and 8/8 at S/N 16. The one-channel regression recovered 0/8 at both
levels. This directly confirms the sensitivity advantage that motivated the
spectral-width bank.

Piecewise-linear interpolation between the frozen grid levels estimates the
multichannel 50% and 90% recovery points at ideal single-epoch S/N 10.29 and
14.17. One-channel estimates are 15.5 and 25.6. Thus, on this experiment, the
estimated S/N required for 90% recovery is about 1.8 times larger without the
multichannel bank.

These values are coarse-grid point estimates, not confidence limits. At S/N 16,
32/32 multichannel trials were recovered, but the Wilson 95% lower bound is
89.3%, just below 90%.

## Validation and reproducibility

1. The frozen config checksum after the run exactly matches the pre-extraction
   checksum.
2. All 12 extracts match the SHA-256 values in `DATA_MANIFEST_M8.sha256`.
3. Every extract has the expected 314,575 channels, 3.814697 Hz resolution,
   16.777216 s sampling, and embedded public source URL.
4. The intermittent-tone and five-channel known-answer validations pass.
5. The recurrence spike-rejection and moving-mask tests pass.
6. Scramble output is deterministic for its frozen seed.
7. Eight automated tests pass under software version 0.4.0.

## Interpretation

Milestone 8 supports the corrected recurrence detector on untouched
frequencies. The real maximum is slightly below the median complete-search null,
and 154 of 256 control maxima equal or exceed it. The absence of masked cells
also shows that the null conclusion does not rely on excising confirmation-band
data after inspection.

This remains a constrained SETI null: it covers 1 MHz, three historical epochs,
the specified orbital bank, and signals present in at least two epochs. It says
nothing about broadband signals, other frequencies, different duty cycles, or
transmitters outside the modeled planet-frame paths.

## Recommended Milestone 9

Move from frequency independence to temporal independence. Freeze version 0.4.0
unchanged and apply it to separate Proxima observing dates, or to a new nearby
exoplanet target with multiple ON/OFF epochs and a defined orbital template.
That will test the recurrence statistic and RFI behavior under a genuinely new
observing environment before scaling to substantially wider bandwidth.
