# LS2D preregistration: HD 260655 light-sail leakage screen

## Frozen question

LS2D asks whether the public 2016-09-14 GBT L-band ABACAD cadence `--64524`
contains a short, broadband, time-local excess matching the LS1 screening
morphology motivated by Guillochon & Loeb (2015).

HD 260655 is approximately 10.01 pc away and has two transiting planets. LS2,
LS2B and LS2C selected the target and cadence using catalogue, cadence-listing
and HDF5-header metadata only. No spectral dataset value has been read in this
branch before this preregistration.

## Geometry caveat

The nominal circular/common-node projected b--c separation at the first ON
midpoint is 32.5777 stellar radii. Perturbing both published orbital periods and
transit epochs across all -1, 0 and +1 sigma input combinations gives a
31.9474--33.1723 stellar-radius envelope. This is about 5.21 times the LS1
selected separation and is not described as a close conjunction.

The cadence remains useful as the best fully HTR-capable opportunity in the
frozen LS2 inventory and as an independent-system replication of the LS1
method. A null result will not be interpreted as strongly
conjunction-conditioned evidence.

## Frozen data and detector

The six exact `.gpuspec.0002.h5` products are searched over 1100--1900 MHz.
Headers already verified a 1.073741824 s sampling interval, approximately
2.861 kHz channels and an A-B-A-C-A-D source sequence.

LS2D copies the LS1 detector without adjustment:

- native channels are robustly centered/scaled, clipped to `[-6, 12]`, and
  averaged into fixed 1024-channel base bins;
- spectral widths are 1, 4, 16, 32 and 64 base bins;
- temporal widths are 4, 8, 16, 32 and 64 seconds;
- ON events require score at least 8.0;
- adjacent OFF events veto at score at least 6.0 with at least 50% frequency
  overlap; and
- 2048 clustered events per scan is a hard retention cap whose overflow
  invalidates the screen.

Scores remain robust screening statistics, not Gaussian significances. The
unchanged LS1 synthetic injection must be recovered before archive execution.

## Conditional HTR boundary

All six 0.349525 ms HTR products are catalogued and header-qualified but remain
closed to spectral access. They may be read only if Stage 1 has at least one
surviving ON event and no retention truncation. A candidate-conditioned HTR
template bank and exact bands must be committed separately before that access.

## Interpretation

- A Stage 1 survivor is a follow-up candidate, not a detection.
- A Stage 1 null applies only to this cadence, L-band and frozen detector.
- The weak projected geometry and suboptimal observing frequency prevent a
  general light-sail exclusion.
- No calibrated false-alarm, sensitivity or occurrence-rate claim is
  authorized.
- Any detection claim would require independent observations plus
  instrumental/RFI review.
- Raw radio spectra may not be committed; only hashes and derived summaries
  may be published.
