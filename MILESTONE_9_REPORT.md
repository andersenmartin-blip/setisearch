# Milestone 9 — independent-epoch Proxima confirmation

## Outcome

The frozen seti-repeater v0.4.0 detector was applied to three public Parkes
Proxima observations from 29 April, 30 April, and 1 May 2021, nearly two years
after the 2019 data used in Milestones 7 and 8. The search directly retested the
1405.25–1405.75 MHz planet-frame interval from Milestone 8 at 2 Hz resolution.

**Result: no candidate.** The strongest ON maximum is S/N 8.1271 at
1405.516462000 MHz, below the empirical 99th-percentile operational threshold
of S/N 9.0548. Its complete-search empirical p-value is 0.4708, and the null
median is S/N 8.1083. It is therefore typical of the calibrated look-elsewhere
background, despite appearing in all three ON epochs.

## Data and preregistration

The scan rule, URLs, frequency interval, detector source digest, random seeds,
and control limitation were frozen before any selected spectral payload was
extracted. For each date, the earliest complete 30-minute 2 Hz Proxima scan was
paired with its immediately following complete 5-minute 1421−490 blank-sky
scan.

| Epoch | ON start UTC | OFF start UTC | ON / OFF integrations |
|---:|---|---|---:|
| 1 | 2021-04-29 12:38:59 | 2021-04-29 13:14:04 | 120 / 20 |
| 2 | 2021-04-30 12:14:25 | 2021-04-30 12:45:54 | 120 / 20 |
| 3 | 2021-05-01 12:05:21 | 2021-05-01 12:36:47 | 120 / 20 |

All integrations are 15 s, all extracted arrays are finite, and every slice
contains 600,001 channels spanning 1404.9–1406.1 MHz. The source filterbanks
total about 108 GB; byte-range extraction retrieved only the selected windows.
The six reproducible extracts are covered by `DATA_MANIFEST_M9.sha256`.

The public-data and campaign context are documented by the
[Berkeley SETI BLC1 page](https://seti.berkeley.edu/blc1/), the
[Breakthrough Listen Open Data Archive](https://breakthroughinitiatives.org/opendatasearch),
and the follow-up report,
[“No Redetections of blc1 in 39 hr of Reobservation of Proxima Centauri”](https://doi.org/10.3847/2515-5172/ac33b2).

## Frozen search result

The searched grid contains 250,001 planet-frame frequency bins, 21 orbital
templates, four two-or-more-epoch activity subsets, and four spectral widths,
for approximately 84,000,336 nominal trials.

| Quantity | Result |
|---|---:|
| Strongest ON S/N | 8.127098559 |
| Rest frequency | 1405.516461999958 MHz |
| Spectral width | 9 channels (about 18 Hz) |
| Orbital template | projected scale 0.75, phase offset 0.0 |
| Active epochs | 1 + 2 + 3 |
| Per-epoch filtered S/N | 4.818, 4.985, 4.692 |
| OFF at matched hypothesis | fails recurrence floor |
| OFF global maximum | 6.709757239 |
| Scrambled-null median | 8.108335495 |
| Scrambled-null 99th percentile | 9.054776192 |
| Empirical global p-value | 0.470817121 |

The candidate-reduction stage retained 726 hypothesis peaks above S/N 5.5,
merged them into 581 frequency clusters, and reported the strongest 50. Every
reported cluster is below threshold. The strongest feature also uses the widest
predeclared filter and participates in arithmetic-spacing triage families, but
neither flag is needed for rejection: its calibrated score alone is insufficient.

The moving isolated-epoch interference mask removed 45 ON cells, all in epoch
1, and 44 OFF cells. The ON masked fraction is 2.86 × 10⁻⁶. The mask was moved
with each shifted epoch in every null and completeness realization.

## Temporal cross-check

As an explicitly post-hoc diagnostic, each campaign's strongest sub-threshold
feature was evaluated at the same rest frequency, orbital template, and
9-channel width in the other campaign. This diagnostic was not used to set the
threshold or change the candidate assessment.

- The 2019 maximum at 1405.472141266 MHz produced 2021 ON epoch values 2.187,
  2.268, and 3.228; no two epochs pass the S/N 3 floor.
- The 2021 maximum at 1405.516462000 MHz produced 2019 ON epoch values −0.010,
  2.214, and 0.550; again, no two epochs pass.

Thus neither campaign's strongest fluctuation recurs in the other campaign
under its own orbital hypothesis.

## Real-noise completeness

The preregistered experiment injected fractional-channel, acceleration-smeared
signals into independently shifted real 2021 noise. At 2 Hz resolution and 15 s
integrations, the tested orbital templates sweep roughly 0.56–5.91 channels per
integration on average, making the multichannel bank important.

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 3/32 (9.4%) | 3/32 (9.4%) |
| 12 | 11/32 (34.4%) | 6/32 (18.8%) |
| 16 | 27/32 (84.4%) | 8/32 (25.0%) |
| 20 | 32/32 (100%) | 8/32 (25.0%) |
| 24 | 32/32 (100%) | 9/32 (28.1%) |
| 32 | 32/32 (100%) | 16/32 (50.0%) |
| 40 | 32/32 (100%) | 23/32 (71.9%) |

Piecewise-linear point estimates place multichannel 50% and 90% recovery near
ideal single-epoch S/N 13.25 and 17.44. The one-channel experiment reaches 50%
at S/N 32 and does not reach 90% by S/N 40. These are coarse-grid point
estimates, not confidence limits.

## Reproducibility audit

- The frozen config hash is
  `35cc5deb4546b64f660a9905c60e891636dea0fc76787b789f35e1d5ea684d0f`.
- The v0.4.0 detector source digest remained
  `80201e8c2061122dedf5b166c648c7c31c9f223873c231fc9403030ed1f9641e`.
- All eight automated detector tests and both known-answer recoveries passed.
- The six data checksums passed.
- All JSON products are strict JSON; non-finite matched-OFF results are encoded
  as `null`.
- An independent recalculation reproduced p = 0.4708171206 and q99 =
  9.0547761917 from the 256 stored null maxima.
- A complete second search produced byte-identical search JSON, 256 null
  maxima, 224 injection records, CSV, and plots.

## Interpretation and next milestone

This is a temporally independent null for one 0.5 MHz band, not a full-receiver
survey and not evidence that no transmitter exists. It constrains signals that
were present in at least two of the three selected 2021 epochs and represented
by the frozen orbital and width banks. The OFF scans are one-sixth as long as
the ON scans and therefore provide a weaker veto.

A useful Milestone 10 would retain the frozen detector while expanding temporal
coverage to the November 2020 and January 2021 follow-up campaigns and testing
multiple preregistered bands. That would add long time baselines and independent
orbital phases rather than merely increasing bandwidth within one three-day run.
