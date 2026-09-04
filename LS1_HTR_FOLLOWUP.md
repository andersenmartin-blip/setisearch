# LS1 high-time-resolution follow-up freeze

Stage 1 left two adjacent-OFF-surviving events, both in A1 and both touching a
scan boundary. This document freezes their candidate-conditioned follow-up
after the Stage 1 result but before reading any `.8.0001` spectral value.

Only A1 and its frozen adjacent-OFF scan B1 are opened. For each candidate the
HTR channels covering the exact Stage 1 band plus 0.5 MHz on either side are
averaged into a time series. The Stage 1 envelope is tested against the rest of
the scan with a two-second guard. Fixed pulse widths are 1, 3, 10, 30, 100,
300 and 1000 ms.

The HTR envelope is confirmed only when the ON screening score is at least 8,
exceeds the same relative-time score in B1, and the B1 score is below 6.
Diffraction-like structure additionally requires at least two subsecond scales
whose ON maximum is at least 8 and exceeds the B1 maximum by at least 2.

These are deterministic screening rules, not calibrated significances. A
positive outcome remains a candidate requiring independent observation; a
negative outcome rejects only these two Stage 1 events. Raw spectra may not be
published.
