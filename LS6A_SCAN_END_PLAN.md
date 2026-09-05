# LS6A: retrospective scan-end diagnostic

The completed LS6 pilot has 47 retained ON windows at two scan endings.
This follow-up is selected after seeing those results. It is not an independent
confirmation or a new prespectral search. Freeze this plan, implementation,
and configuration publicly before rereading the four previously exposed files.

## Fixed scope and measurements

- Reuse exactly A1/B1/A2/B2 in the repaired LS6 configuration. Verify their
  full-file SHA-256 values against the original screen; validate headers.
- Replay the unchanged LS6 screen and require exact equality of every scan
  record, including all scores and windows. Stop on disagreement.
- Use all 64 original 1024-channel bins in ascending frequency. Preserve
  the LS1 native robust normalization, clipping and valid-channel rules.
- Export the 56-by-64 normalized coarse spectrum, per-time frequency
  median, and per-bin time-mean-centered traces. Quantify the fraction of
  centered squared energy removed by subtracting the across-bin median
  trace (unit loading, no fitted gains). This can be negative and is a
  descriptive measure, not variance explained by a physical model.
- Independently summarize un-clipped native power: divide each finite,
  positive-median channel by its own full-scan temporal median, then take
  the frequency median for each time sample. This dimensionless quantity
  is not flux calibration. Report excluded-channel and nonfinite counts.
- For BOTH final 7 and final 15 samples in ALL four scans, report per-bin
  mean(tail)-mean(pre-tail), its median and fraction of positive bins.
  These windows come from the earlier LS6 result, not a new blind search.
- On the frequency-median normalized trace, fit intercept-plus-linear-time
  and intercept-plus-fixed-final-window-step (7 and 15 samples). Report
  descriptive R-squared and signed slope/step amplitude; do not optimize
  breakpoints, assign p-values or select a new acceptance threshold.
- Plot every full-length trace and coarse spectrum, with identical axes
  within comparable panels. Include OFF scans regardless of outcome.

## Interpretation and limits

Shared frequency behavior and smooth changes would support a baseline/common
mode concern. They cannot by themselves establish an instrumental cause:
a truly broadband sky signal can also be common mode. A step or pulse may
be clipped by the scan ending. No independent epoch, tracking telemetry,
other subband, or HTR product is opened in this diagnostic. Positive-only
screening can miss negative-going OFF changes, so zero OFF events alone
does not establish a stable control. Preserve all 47 primary survivors;
this diagnostic does not supply a new veto or promote a sky candidate.

## Reproduction

Run `PYTHONPATH=src:scripts python scripts/ls6a_scan_end.py` after the
public freeze has been verified. Each scan is checkpointed and raw data
are deleted after use. The configuration pins source artifacts and code.
Synthetic tests cover shared drift, localized changes, and decreasing power.
Reports and figures are generated separately from the sealed checkpoints.
