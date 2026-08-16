# Milestone 10 — five-band Proxima small survey

## Outcome

The frozen `seti-repeater` v0.4.0 detector was applied to five fresh,
pre-registered 1 MHz planet-frame bands using three public Parkes Proxima
observations from 30 April, 2 May, and 3 May 2021. The source filterbanks and
searched frequency intervals had not been used by Milestones 6–9.

**Result: no candidate.** The strongest ON maximum is S/N 9.3115 at
1424.937812000 MHz, below the empirical 99th-percentile operational threshold
of S/N 12.6079. Of 256 complete-search scrambles, 126 produced a maximum at
least this large, giving a finite-sample global p-value of 0.4942. The observed
maximum is therefore typical of the calibrated look-elsewhere background.

## Data and preregistration

The archive selection rule, six source URLs, five frequency bands, detector
source digest, random seeds, thresholds, masks, and completeness design were
frozen before any selected spectral payload was extracted. The study uses a
later ON/OFF pair on 30 April than Milestone 9, followed by the earliest
complete pairs on the two previously unused dates.

| Epoch | ON start UTC | OFF start UTC | ON / OFF integrations |
|---:|---|---|---:|
| 1 | 2021-04-30 12:52:27 | 2021-04-30 13:24:07 | 120 / 20 |
| 2 | 2021-05-02 12:04:35 | 2021-05-02 12:36:05 | 120 / 20 |
| 3 | 2021-05-03 12:09:44 | 2021-05-03 12:41:16 | 120 / 20 |

All integrations are 15 s at 2 Hz channel spacing. Each of the 30 extracted
tiles contains 850,001 channels across a 1.7 MHz interval: ON arrays have shape
120 × 850,001 and OFF arrays 20 × 850,001. Every array is finite, its frequency
axis is monotonic and exactly bounded, and every SHA-256 in
`DATA_MANIFEST_M10.sha256` passes. The six source filterbanks total about
107.5 GB; byte-range extraction retained about 6.8 GiB across the five guarded
bands.

The November 2020 and January 2021 observations described by the campaign were
not returned by either the general archive query or the paper-specific public
API on the preregistration date. This is an archive-availability statement, not
a claim that those data do not exist. Milestone 10 consequently remains within
the April–May 2021 campaign and does not claim an independent long-baseline
confirmation.

The public-data context is documented by the
[Berkeley SETI BLC1 page](https://seti.berkeley.edu/blc1/), the
[Breakthrough Listen Open Data Archive](https://breakthroughinitiatives.org/opendatasearch),
and the follow-up report,
[“No Redetections of blc1 in 39 hr of Reobservation of Proxima Centauri”](https://doi.org/10.3847/2515-5172/ac33b2).

## Frozen search result

The searched grid contains five disjoint 1 MHz planet-frame bands, 500,001
frequency bins per band, 21 orbital templates, four two-or-more-epoch activity
subsets, and four spectral widths. This is approximately 840,001,680 nominal
frequency/orbit/activity/width trials.

| Planet-frame band (MHz) | Best S/N | Width | Best frequency (MHz) | Window p | OFF global S/N |
|---|---:|---:|---:|---:|---:|
| 1400.0–1401.0 | 9.0755 | 9 ch | 1400.048482001 | 0.4280 | 6.9125 |
| 1406.0–1407.0 | 8.0659 | 9 ch | 1406.963081999 | 0.8521 | 6.4457 |
| 1412.0–1413.0 | 8.3645 | 9 ch | 1412.660504000 | 0.5292 | 6.3093 |
| 1418.0–1419.0 | 8.2842 | 9 ch | 1418.221840001 | 0.6342 | 6.3392 |
| 1424.5–1425.5 | 9.3115 | 9 ch | 1424.937812000 | 0.1790 | 6.5375 |

The global null median is S/N 9.2781 and its empirical 99th percentile is S/N
12.6079. The strongest feature uses projected orbital scale 0.25, phase offset
0.0, and epochs 1 + 2. Its filtered epoch values are 6.584, 9.219, and 2.572;
the third epoch is inactive under the frozen S/N 3 floor. The matched OFF
hypothesis fails the recurrence floor. Its use of the widest predeclared
9-channel filter is a triage flag but is not needed for rejection.

Candidate reduction retained 3,914 hypothesis peaks above S/N 5.5 and merged
them into 3,235 frequency clusters. The strongest 50 clusters per band were
reported, for 250 total; all are below the global threshold. No candidate
crossed the threshold, so no post-hoc full-band fractional-drift family analysis
was triggered.

The moving isolated-epoch mask removed 32,708 ON and 8,737 OFF
template/epoch/frequency cells across the five bands, fractions of 2.08 × 10⁻⁴
and 5.55 × 10⁻⁵. The 1400.0–1401.0 MHz band contributes most of the ON masked
cells and has the same empirical 99th-percentile value as the global null. This
documents a heavy low-band null tail; it does not by itself establish the
physical cause. The mask was moved with every shifted epoch in all null and
completeness realizations.

## Real-noise completeness

The preregistered experiment injected fractional-channel,
acceleration-smeared signals into independently shifted real 1412.0–1413.0 MHz
noise. Signals were active in epochs 1 and 3 and drawn equally from four exact
orbital templates. There are 32 trials at each of seven ideal single-epoch S/N
levels.

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 0/32 (0.0%) | 0/32 (0.0%) |
| 12 | 1/32 (3.1%) | 1/32 (3.1%) |
| 16 | 7/32 (21.9%) | 5/32 (15.6%) |
| 20 | 15/32 (46.9%) | 8/32 (25.0%) |
| 24 | 24/32 (75.0%) | 8/32 (25.0%) |
| 32 | 32/32 (100%) | 8/32 (25.0%) |
| 40 | 32/32 (100%) | 9/32 (28.1%) |

Piecewise-linear point estimates place multichannel 50% and 90% recovery near
ideal single-epoch S/N 20.44 and 28.8. These are coarse-grid estimates rather
than confidence bounds. The one-channel-only search reaches neither 50% nor
90% by S/N 40, demonstrating the importance of the multichannel bank for these
2 Hz, 15 s spectra. Even 32/32 recovery has a Wilson 95% lower bound of 89.3%.

## Reproducibility audit

- The frozen config SHA-256 is
  `47b244a596d88ed06edd2dd232edc556c6e92c456f6af99afbf92849d17623ee`.
- The v0.4.0 detector source digest remains
  `80201e8c2061122dedf5b166c648c7c31c9f223873c231fc9403030ed1f9641e`.
- All eight automated tests and both internal known-answer recoveries passed.
- All 30 data checksums and structural checks passed.
- All five JSON products are strict JSON; failed matched-OFF recurrences are
  encoded as `null`, not non-finite values.
- Independent calculation found 126 null exceedances and reproduced p =
  0.4941634241 and the empirical higher-order q99 = 12.6078538895 from the 256
  stored global maxima.
- All 224 injection trial records are present.
- A complete second run produced byte-identical search JSON, completeness JSON,
  null archive, CSV, and plots. Both plots also passed visual inspection.

## Interpretation and next milestone

This null result constrains the searched signal class in five fresh bands and
three selected epochs. It is not evidence that no transmitter exists. A signal
must be present in at least two epochs, fall within the frozen orbital and width
banks, and be strong enough for the measured completeness. The OFF scans are
only 5 minutes versus 30 minutes ON and therefore provide a weaker veto.

The next scientifically useful milestone should prioritize genuinely
independent observing times rather than add more bandwidth from this same
three-day campaign. The preferred path is to locate or obtain access to the
public November 2020/January 2021 follow-up filterbanks; if they remain
unavailable, select a different public exoplanet target with preregisterable
multi-epoch ON/OFF data and retain the frozen detector for a new-target test.
