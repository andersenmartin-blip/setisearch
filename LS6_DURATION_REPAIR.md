# LS6 technical duration repair — 2026-09-05

The initial published freeze is retained unchanged at
5aba35e7aaec5de881f71a05edabff8bed56bfed.

The first A1 attempt downloaded and indexed the selected 14,680,458-byte file,
then failed with `ValueError: time template exceeds scan duration` in the
unchanged LS1 detector. Contrary to the initial plan's description, the core
raises rather than silently skipping an oversized template. Some fitting
window scores were computed internally before the exception, but none were
returned, checkpointed, inspected, or used to choose parameters. No completed
scan result exists from this attempt. The raw file was deleted.

Freeze this technical amendment before restarting: use exactly 4,8,16,32-second
templates, dropping only the impossible 64-second template based on the already
known 56-sample header. All frequencies, scans, roles, thresholds, clipping,
widths, event caps and detector implementation remain unchanged. This is not
an independent held-out rerun; A1 values were accessed before the amendment.
The other three scan values were not accessed before the amendment.

The amended configuration is config/ls6_trappist1_x_subband_repaired.json.
Its original-freeze and prior-exposure fields are explicit. Preserve the initial
configuration, original runner and primary freeze record. The repaired runner
accepts only this named technical repair and verifies the initial configuration
hash before execution. No HTR values are opened.
