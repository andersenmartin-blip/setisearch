# Milestone 7 — Wideband candidate clustering and recurrence controls

## Outcome

The validated planet-frame search was expanded from four 40 kHz intervals to
two disjoint 1 MHz bands: 1403.0–1404.0 and 1416.0–1417.0 MHz. This is 2 MHz in
total, 12.5 times Milestone 6's searched rest-frame bandwidth. The pipeline now
also clusters redundant hypothesis peaks, records explicit candidate
dispositions, detects approximate arithmetic-frequency families for triage, and
tracks per-epoch interference masks through every control shift.

No candidate was found. The strongest ON-source result was S/N 7.1442 at
1403.083610535 MHz, using a 9-channel filter, projected orbital scale 0.75,
phase offset 0.0, and epochs 2+3. The 256-scramble global null had median 7.4046
and 99th percentile 11.3669. The empirical global p-value was 0.6576.

The second band peaked at S/N 6.6932 at 1416.521030426 MHz with a 5-channel
filter and a per-window p-value of 0.1595. Neither matched OFF-source hypothesis
met the S/N 3 recurrence floor in all claimed active epochs.

## Scale and candidate reduction

The complete search comprises approximately 176,161,440 nominal
frequency/orbit/activity/width trials:

- 2 bands and 524,290 total rest-frequency bins;
- 21 orbital templates;
- 4 allowed two-/three-epoch activity subsets;
- 4 normalized spectral widths: 1, 3, 5, and 9 channels.

Candidate reporting retained up to three non-adjacent peaks per hypothesis above
S/N 5.5. This produced 194 records, which collapsed to 173 frequency clusters
within 20 Hz. The strongest 50 clusters in each band were retained in the
report. All 100 were below the S/N 11.3669 operational threshold.

Arithmetic-frequency families are deliberately conservative triage metadata.
Twenty families were flagged among the retained 1403 MHz clusters and 15 among
the 1416 MHz clusters. With many possible spacings, these counts are not assigned
a standalone probability and are not evidence for or against extraterrestrial
origin. They matter only if a future above-threshold event requires RFI review.

## Disclosed diagnostic correction

The original Milestone 7 selection rule, frequency bands, filter widths,
candidate settings, seeds, and injection grid were frozen before inspecting the
new bands. The first calibrated run used the earlier summed stacked statistic.
It produced a maximum of S/N 70.9324 at 1403.018123627 MHz. Its active-epoch
values were dominated by one epoch (about S/N 98.7) rather than a recurrence,
and the 256-scramble null was similarly extreme: median 70.9061 and 99th
percentile 72.4718.

A simple S/N 3 active-epoch floor reduced the real maximum to 44.6359 but did
not remove the null's long tail. A subsequent diagnostic used `sqrt(N)` times
the weakest active-epoch S/N, which reduced the real maxima to ordinary values
but still allowed accidental alignments of strong, unrelated single-epoch
lines in some shifted controls.

The final detector therefore applies both:

1. S/N at least 3 in every epoch claimed as active, with `sqrt(N)` times the
   weakest active-epoch S/N as the recurrence statistic.
2. A per-epoch mask for a cell whose strongest epoch is at least S/N 10 while
   the second strongest is below 3, dilated by 9 frequency channels.

The mask is shifted with the corresponding epoch in null and completeness
realizations. This is essential: a fixed-frequency mask would leave shifted RFI
unmasked. In the ON data it removes 0.0403% of template/epoch/frequency cells in
the 1403 MHz band and 0.00105% in the 1416 MHz band.

These choices were made after inspecting Milestone 7 diagnostics. The complete
real search, 256-control null, candidate reduction, and completeness experiment
were rerun with the final detector. The result is scientifically useful as an
exploratory milestone and software validation, but it is not an independent
confirmatory test of those corrections. A future data selection must freeze
them in advance.

## Completeness

The injection experiment uses real 1403 MHz planet-frame background vectors,
independently circularly shifted by epoch. The corresponding per-epoch masks
move with those shifts. Injected signals have continuous fractional-channel
frequencies and time-averaged sinc-squared channel power while following exact
members of the orbital bank. They are active in epochs 1 and 3.

Four truth templates span mean within-integration sweeps of 0.34, 1.87, 3.64,
and 5.01 channels. With 16 trials per level and the globally calibrated S/N
11.3669 threshold, recovery was:

| Ideal single-epoch S/N | Multichannel | One channel |
|---:|---:|---:|
| 8 | 0/16 | 0/16 |
| 10 | 0/16 | 0/16 |
| 12 | 0/16 | 0/16 |
| 16 | 7/16 (43.8%) | 3/16 (18.8%) |

The multichannel bank retains an advantage over the one-channel regression, but
the frozen Milestone 7 injection grid stops too early to estimate a 90%
completeness point. The 7/16 Wilson 95% interval is 23.1–66.8%.

## Validation chain

1. The intermittent drifting-tone known-answer test recovers the correct
   frequency, orbital path, and activity subset.
2. A deterministic five-channel signal is strongest in the five-channel
   unit-noise filter.
3. A one-epoch S/N spike is rejected by the recurrence requirement.
4. A dedicated mask test verifies that only the dominant contaminated epoch is
   flagged and that the frequency guard is correctly dilated.
5. Scramble output is deterministic for a fixed seed.
6. Eight automated tests pass.
7. All six ON and six OFF public telescope slices were used in both bands.

## Recommended Milestone 8

Freeze the corrected recurrence statistic and moving per-epoch RFI mask before
selecting an independent confirmation set. Use either new Proxima observations
or newly pre-registered, untouched frequency bands. Extend injection levels
above S/N 16 with more trials per level so the 50% and 90% completeness points
can be estimated, while leaving the candidate and null logic unchanged.
