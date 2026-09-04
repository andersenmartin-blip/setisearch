# LS1 preregistration: light-sail leakage search

## Frozen scientific question

LS1 asks whether an already public Green Bank Telescope L-band observation of
HD 219134 contains a short, broadband, time-local excess consistent with the
*morphology* proposed by Guillochon & Loeb (2015) for leakage from a microwave
beam driving an interplanetary light sail. The motivating paper predicts Jy
transients lasting tens of seconds and recommends nearby multi-transiting
systems near projected planetary conjunction.

This is a new experimental track. It does not modify detector v0.5/v0.6 or the
M33--M42 chain, and it does not treat HD 219134 as a known source. The GBT band
searched here (1.1--1.9 GHz) is far below the paper's illustrative optimum near
tens of GHz, so a null result cannot exclude that fiducial propulsion system.

Primary reference: [Guillochon & Loeb 2015](https://doi.org/10.1088/2041-8205/811/2/L20).
Earlier power-beaming searches are acknowledged; LS1 does **not** claim to be
the first search for power-beaming leakage. In particular,
[Harp et al. (2016)](https://arxiv.org/abs/1511.01606) searched KIC 8462852 at
1--10 GHz for narrow and moderate-band emission, and
[Benford & Benford (2016)](https://arxiv.org/abs/1602.05485) interpreted those
limits in a wider power-beaming context. The narrower novelty statement, if
supported by a final literature review, is a dedicated archival search
conditioned on projected conjunction for the specific Guillochon--Loeb
light-sail morphology.

## Prospective boundary

The machine-readable configuration, target ranking rule, signal templates,
thresholds, adjacent-OFF veto and event-retention cap are committed before LS1
reads any spectral dataset value from the selected `gpuspec.0002.h5` or
`gpuspec.8.0001.h5` files. M16 previously inspected the separate fine-resolution
`.0000` products for a narrowband experiment; LS1 neither reuses those values
nor tunes itself from their result.

Only hashes, validation records and derived event summaries may be published.
Raw or sliced telescope spectra remain untracked.

## Target and cadence ranking

HD 219134 is 6.53127 pc away and has two transiting inner planets, b and c.
Five public GBT L-band ABACAD cadences qualify. They are ranked without spectral
access using circular, edge-on orbits, a shared sky-plane nodal line and the
absolute difference between the planets' signed projected coordinates at the
midpoint of the first ON scan. The ephemeris is frozen from the NASA Exoplanet
Archive composite table on 2026-09-04.

This geometry is intentionally modest: unknown mutual node, eccentricity and
propagated ephemeris uncertainty mean the score is an archive-prioritization
metric, not proof that the planets were physically aligned. The fixed ranking
selects cadence `--63424` from 2016-08-22. The ranking must reproduce from
`results_m16_header_screen_corrected/header_screen.json` before spectral access.

## Stage 1: medium-resolution envelope screen

All six scans in the selected A-B-A-C-A-D cadence are read from the public
`.0002` products. Header geometry must identify the frozen source, start within
two seconds of the archive record, time resolution 0.5--2 s and spectral
resolution 1--5 kHz. The searched band is fixed at 1100--1900 MHz.

Each native frequency channel is robustly centered and scaled over time, clipped
to `[-6, 12]`, and averaged into fixed 1024-channel base bins. Spectral boxcars
span 1, 4, 16, 32 and 64 base bins; temporal boxcars span 4, 8, 16, 32 and 64 s.
The statistic is normalized again over time for each spectral boxcar. It is a
robust screening score, not a Gaussian sigma or calibrated false-alarm
probability.

An ON event is retained at score >= 8.0. It is vetoed if an adjacent OFF scan
has score >= 6.0 with at least 50% frequency overlap. At most 2048 clustered
events are retained per scan; reaching the cap with omitted events invalidates
the screen rather than silently truncating it.

## Stage 2: high-time-resolution follow-up

The `.8.0001` products remain closed unless Stage 1 has at least one surviving
ON event and no retention truncation. A separate, committed template bank must
then be frozen before those values are read. Its purpose is to test for the
subsecond diffraction structure predicted inside a surviving broadband
envelope, not to rescue or retune the Stage 1 threshold.

## Interpretation

- A surviving Stage 1 event is a follow-up candidate, not a detection.
- No calibrated false-alarm, sensitivity, occurrence-rate or technosignature
  claim is authorized by LS1 as currently frozen.
- Any detection claim would require independent observations, instrumental/RFI
  review and a separately documented statistical calibration.
- A null result applies only to this cadence, band, template bank and
  sensitivity; it cannot exclude light sails generally.
