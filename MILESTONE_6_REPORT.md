# Milestone 6 — Smearing-aware matched filters and completeness

## Outcome

The pipeline now searches normalized 1-, 3-, 5-, and 9-channel spectral widths,
calibrates the enlarged trials factor empirically, and measures detection
completeness with realistic signals injected into real noise. No real-data
candidate was found.

The strongest multichannel result was S/N 6.7248 at 1401.244979858 MHz using a
9-channel filter, projected orbital scale 0.75, phase offset 0.1 cycle, and
epochs 2+3. Its matched-hypothesis OFF-source S/N was 0.3163. Across all four
windows its empirical global p-value was 0.3463. The 99th-percentile global-null
maximum was S/N 7.4830, which therefore became the operational threshold.

## Validation chain

1. The original intermittent drifting-tone known-answer test still recovers the
   correct frequency, orbital path, and activity subset.
2. A five-channel deterministic signal is strongest in the five-channel
   unit-noise filter.
3. An actual model signal sweeping 4.91 channels per integration is strongest in
   the five-channel filter.
4. Five automated tests pass.
5. All four one-channel maxima exactly reproduce Milestone 5.
6. The complete multichannel trials factor is recalibrated with 256 null
   scrambles rather than treated as four independent searches analytically.

## Completeness experiment

Signals have a continuous rest frequency, so their fractional channel phase is
not quantized. Within each integration the instantaneous tone is sampled at 32
subtimes, converted to a sinc-squared power response, and averaged while the
frequency sweeps according to the celestial plus orbital acceleration model.

The background is the real w1421 planet-frame spectrum. Each epoch is shifted
independently to randomize alignment while preserving its marginal noise and RFI.
Four exact search-bank templates span mean smearing of 0.34, 1.89, 3.68, and
5.08 channels per integration. The signal is present in epochs 1 and 3.

At ideal unsmeared single-epoch S/N 12, the multichannel recovery is 28/32
(87.5%; Wilson 95% interval 71.9–95.0%), versus 15/32 (46.9%; 30.9–63.6%) for
one channel. At S/N 16 it is 31/32 (96.9%) versus 17/32 (53.1%). At S/N 20 the
multichannel bank reaches 32/32; the one-channel statistic reaches only 22/32.

The clearest high-acceleration result is the 5.08-channel-sweep template: at
S/N 20, multichannel recovery is 8/8 while one-channel recovery is 0/8.

## Interpretation

The raw multichannel maxima are higher than in Milestone 5 because wider filters
and extra trials create more opportunities for noise peaks. The scramble
distribution rises as well, and the strongest real maximum remains ordinary
under that distribution. This is why the result is still a clean null despite
the larger raw S/N values.

The completeness experiment verifies that the new filter bank solves the main
sensitivity failure identified in Milestone 5. It does not yet cover orbital
parameter mismatch, every intermittent duty cycle, or the full radio band.

## Recommended next milestone

Scale the validated search to a substantially larger pre-registered bandwidth,
while adding candidate clustering and explicit RFI-family vetoes so that wider
filters and neighboring templates do not produce redundant candidate lists.

