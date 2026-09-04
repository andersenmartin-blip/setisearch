# LS3C — preregistered HD 63433 light-sail leakage screen

LS3B selected the public Green Bank Telescope L-band cadence `--87575` for HD 63433. Its nominal d–b projected separation is 2.821 stellar radii, with a 2.605–3.036 range under the frozen period/epoch input-corner diagnostic. This is about 45% of LS1’s selected separation and is the best frozen LS archive geometry tested so far.

LS3C will read the six medium-resolution dynamic spectra only after this document, configuration, code, tests and checksums are committed. The target, cadence, 1100–1900 MHz science band, detector bank, score thresholds, adjacent-OFF veto and 2,048-event-per-scan retention cap are fixed in advance.

## Detector and decision rule

The broadband detector and every numerical parameter are inherited unchanged from LS1. It searches time-local excess power over 4–64 seconds and multiple broad frequency scales. Scores are robust matched-filter screening statistics, not calibrated Gaussian significances.

An ON event must score at least 8.0 and must not overlap a score-6.0-or-higher event in its frozen adjacent OFF scans by 50% or more in frequency. Any retention truncation invalidates the screen. HTR values remain closed unless at least one event survives and no scan is truncated; an HTR template bank would then require a new prospective freeze.

## Interpretation boundary

The conjunction geometry assumes circular, edge-on, common-node orbits and treats archive MJD as BJD for ranking. Unknown nodes and ephemeris/model uncertainty mean 2.821 stellar radii is not proof of a physical conjunction.

The observing band is far below the tens-of-GHz illustrative optimum in Guillochon & Loeb (2015). A null result closes only this cadence, band and frozen morphology. A survivor is a follow-up candidate, not a technosignature detection. No calibrated sensitivity or occurrence-rate claim is authorized.
