# Milestone 5 — Reusable pipeline and four-window real-data search

## Outcome

The notebook analysis is now a tested command-line pipeline, and the three-epoch
Proxima Centauri search has been expanded from one to four pre-registered
frequency windows. No narrowband planet-frame candidate was found.

The strongest result was in the 1410 MHz window: S/N 5.7078 at
1410.230712891 MHz, using projected orbital scale 0.5, phase offset 0.1 cycle,
and epochs 1+2. Its per-window scramble p-value was 0.0934. The OFF-source S/N at
that exact frequency/template/subset hypothesis was 0.7602.

Globally, the observed maximum had empirical p = 0.3191 under 256
coherence-destroying scrambles. The global null's 99th percentile was S/N 6.4634,
and every ON maximum was below the pre-registered S/N 7.0 reference.

## Validation chain

1. A deterministic synthetic intermittent drifting tone was recovered at the
   correct frequency, track template, and active-epoch subset before real data
   were searched.
2. Automated tests cover the known-answer recovery, loss models, and deterministic
   scramble calibration; all pass.
3. All 24 real-data slices were checked against embedded SIGPROC metadata.
4. The refactored pipeline exactly reproduced the prior 1421 MHz notebook maximum:
   S/N 5.0566109713 at 1421.254673004 MHz.
5. ON significance, matched-hypothesis OFF power, global OFF maximum, template
   identity, activity subset, empirical p-value, and loss estimates are retained
   separately.

## Search scope

- Three Parkes Proxima ON scans from 2019-04-29 through 2019-05-01.
- Three adjacent 1421-490 OFF scans.
- Four 0.5 MHz extraction windows centered at 1401.25, 1410.25, 1421.25, and
  1426.25 MHz.
- A 40 kHz rest-frequency grid per window at 3.814697 Hz resolution.
- 21 projected orbital templates and four two-/three-epoch activity subsets.
- 3,522,960 nominal frequency/template/subset trials.

## Interpretation

This null result is narrow. It excludes no civilization and does not survey the
full receiver band. It says only that this pipeline found no qualifying narrowband
signal in these rest-frequency intervals, during these epochs, under this orbital
bank and at the sensitivity of these data.

The new leakage and acceleration-smearing diagnostics also show why the next
scientific milestone should be a proper multi-channel matched-filter bank with
smearing-aware injections before scaling to a much larger bandwidth.

