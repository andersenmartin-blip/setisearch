# LS4C: LHS 1140 X-band HTR preregistration

Status: **FROZEN AFTER LS4B AND BEFORE HTR SPECTRAL ACCESS**.

LS4B produced seven medium-resolution events that survived the frozen adjacent-OFF veto. All seven are in `A1`, use the 64 s template, occupy one 2.93 MHz base bin and overlap in time near 91-159 s, while spanning 8.680-10.244 GHz. This common-time pattern is suspicious contextual evidence, but it is not a retroactive veto and is not evidence of a technosignature.

LS4C tests the exact seven-event inventory against the high-time-resolution `A1` product and its adjacent `B1` control. Because no survivor occurs in `A2` or `A3`, the other four HTR scans are excluded. This reduces the frozen HTR payload from 56.61 GB to 18.87 GB.

## Frozen method

- Verify the LS4B result file, result identity and exact ordered survivor inventory.
- Verify both 8-bit SIGPROC headers, source names, epochs, dimensions and file sizes.
- Download, hash, process and delete one 9.435 GB HTR file at a time.
- In one row-chunked pass per source, collapse each candidate interval plus 0.5 MHz padding into seven time series.
- Reuse the LS1 HTR pulse widths, robust envelope scores, ON/OFF thresholds, pulse margin and required subsecond-scale count without retuning.
- Publish only source digests, derived metrics and dispositions; never raw spectra or collapsed time series.

Even a candidate passing LS4C requires an independent observation. Scores are uncalibrated screening statistics, and neither LS4B nor LS4C alone can establish artificial origin.

The normative freeze is `config/ls4c_lhs1140_x_htr_followup.json`; `LS4C_FREEZE.sha256` binds the executable code and tests.
