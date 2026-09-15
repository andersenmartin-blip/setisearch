# LS7V reduction-log reconciliation

[Findings](../LS7V_CALIBRATION_RECONCILIATION.md) explain why the saved CAL
electronics differ from the LS7U measurements and which corrections actually
ran. This is a source-contract reconciliation, not a native detector trial.

| File | Content |
|---|---|
| pipeline.log.gz | Complete original 60,868-byte log, losslessly compressed; only calibration lines 75–96 are analyzed |
| provenance.json | Original LS7R HTTP identity, original/compressed SHA-256, scope and seven reused input identities |
| selected_calibration_lines.json | The 22 analyzed lines with original line numbers |
| summary.json, verification.log | Extracted source facts, header checks, exact default-value comparison and limitations |
| reproduction.json | Actual clean offline reproduction result |
| calibration_contract.json | Updated requirements; the skipped spatial bias frame is distinguished from the applied dark map |

The log came from the already retained local clean-reproduction cache and
matches the identity saved in `results_ls7r_metadata/calibration_log_extract.json`.
No new network request or image/margin read is made. Source photometry and
other unselected log messages are not analyzed or used to choose this model.

From the repository root, with Python 3.12 and Astropy installed:

```bash
python3 scripts/ls7v_reconcile_log.py
python3 scripts/ls7v_verify.py
```

The first command verifies all saved input identities and writes the summary
and selected lines. The second runs the reconciliation in a new temporary
directory and compares both outputs byte-for-byte with the retained files.
This run used Python 3.12.14 and Astropy 8.0.1. NumPy is an Astropy dependency;
the reconciliation does not recalculate LS7U's margin statistics.

The [scope](../LS7V_SCOPE.md) was written after initial calibration-log
inspection, before the reconciliation program. It is explicitly forensic,
not a prospective detector preregistration. Earlier experiment results stay
unchanged. No source detector, new candidate or observing coverage follows.
