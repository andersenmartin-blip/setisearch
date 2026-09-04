# LS4B: LHS 1140 X-band signal-search preregistration

Status: **FROZEN BEFORE SPECTRAL ACCESS**.

LS4A inspected only SIGPROC headers and selected the complete GBT X-band ABACAD cadence `--114966`. LS4B now freezes the spectral search before any value in those six medium-resolution filterbanks is read.

## Scientific role

The usable 7.9515-12.0765 GHz coverage is substantially closer to the tens-of-GHz optimum discussed by Guillochon and Loeb than the L-band LS1-LS3 searches. The frozen science interval is 8-12 GHz. The observation is not close to a projected LHS 1140 c-b conjunction: the approximate nominal separation is 90.065 stellar radii. LS4B is therefore a high-frequency complement, not an improved-geometry test.

## Frozen method

- Use the exact six-scan `A1-B1-A2-C1-A3-D1` cadence listed in the machine-readable configuration.
- Verify file size, source, epoch and every frozen SIGPROC geometry field before searching.
- Download, verify, screen and delete one 1.569 GB medium-resolution file at a time. Publish only digests and derived results.
- Decode the 32-bit SIGPROC time-frequency matrix and search only 8,000-12,000 MHz.
- Reuse the LS1 broadband detector, template durations, spectral widths, clipping, thresholds, retention cap and adjacent-OFF veto without retuning. Only the science interval and input decoder differ.
- Stop after the medium-resolution screen. HTR files total 56.61 GB and remain closed unless at least one event survives without retention truncation and a separate follow-up is prospectively frozen.

Scores are screening statistics, not calibrated significances. No detection, technosignature, occurrence-rate or general light-sail claim follows from this stage alone.

The normative freeze is `config/ls4b_lhs1140_x_light_sail.json`; `LS4B_FREEZE.sha256` binds the exact executable implementation and tests.
