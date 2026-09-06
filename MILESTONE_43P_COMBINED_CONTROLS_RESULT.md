# M43P — combined component controls pass

The missing sparse M43I score adapter now handles repeated native-channel
mappings, arbitrary score-index order and duplicate requests. Its direct
paired-OFF rule retains the inclusive 5.5 floor, active epochs only, exact
q/template/width, and no mask or frequency neighborhood. The unchanged M37
adapter still rejects noninjective mappings; no old attestation is bypassed.

This run combines source/score transfer, full-support mask construction,
masked sums, scramble wiring and paired-OFF decisions. All declared numerical
comparisons pass. **158 tests pass**, including six new boundary/adversarial
tests and inherited retention, OFF-track association, adjacent-OFF, alias,
rank-significance and sparse physical-disposition fixtures.

| Check | Evaluated scope | Result |
| --- | --- | --- |
| Independent sparse native-window reference | 734,832 cells; all 1,701 templates, six sources, eight widths, nine queries/source | Exact |
| Full-support ancestor replay | 1,328,080,368 per-epoch cells; templates 0–31 and 1696–1700 | Prior M43J/L/N batch hashes reproduce |
| Width-OR masks and clipped dilation | 166,010,046 Boolean cells | Exact |
| Masked sum and active>=3 outputs | 1,770,470,720 cells; both ON and OFF | Exact |
| Four scramble maxima per template/kind | 7,081,882,880 underlying stack cells; 296 maxima | Exact maxima and inventory counts |
| Paired-OFF active-subset decision | 381,024 Boolean decisions | Exact scalar-rule agreement |

The sparse queries are fixed from geometry, including six literal repeated-
channel witnesses, before reading scores. Duplicated requests count as
repeated numerical checks, not independent trials. The seven common queries
provide paired-OFF comparisons; the two source-specific collision queries
are not mixed across epochs. All 48 source/width inputs reproduce independently
retained source and cache identities.

## What is now checked

For each of 37 fixed template anchors and both scan kinds, every support
carrier is included at all eight widths. The first pass combines isolated-
epoch flags across widths. A separate reference uses explicit other-epoch
comparisons and prefix interval counts, independent of production sorting and
offset-OR dilation. Masks are built over all 747,793 support carriers, then
cropped to 747,665 score carriers. This preserves edge neighborhoods.

Every masked score is compared directly for the four inherited subsets.
Scramble validation checks the correct rotation direction, wrap domain and
the movement of each mask with its own epoch scores. Independent modular
indexing/reference sums produce the same maxima as `update_calibration`.
The scramble endpoint compares **maxima**, not every individual scrambled
score; the table states the underlying evaluated cell count accordingly.
The four rows are deterministic wiring controls, not a null ensemble used
for statistical inference. Each accumulator has an explicitly separate
one-template diagnostic identity; no full-bank calibration is certified.

## Execution and reproducibility

Public protocol/code freeze: `bd064e301c247206e12dc2e723cab023e8f9e80e`.
Configuration: `c78ea34f1df9eadd2534945cf1f027ac9e4a314d211c3d06995c07844fc1bb16`.
Sealed result: `d46cdb1a95c1a011d34df9162cb437e810b74a6bad010e86e4489270eb21a753`.
The configuration pins 176 files. NumPy 2.3.5.
Runtime: **158.766 seconds** wall time for the combined
real-data run. Seven ordinary source workers and two logic workers, with
cooperative stop boundaries. **Zero new telescope requests/downloads.**
All 16 kind/width source checkpoints and both 37-template logic checkpoints
are complete. Checkpoints and the full run log are retained in the result
directory. Large disposable anchor arrays stay outside git; their full
payload hashes are retained and reproduce earlier public batch identities.
Reproduction recomputes them from the six verified source directories.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/m43p_combined_controls.py --freeze-commit bd064e301c247206e12dc2e723cab023e8f9e80e --work-root /path/to/new-empty-work-directory --source-root /path/to/m43h_work/live
PYTHONPATH=src:scripts .venv/bin/python scripts/m43p_result_report.py
sha256sum -c RESULTS_MANIFEST_M43P_COMBINED_CONTROLS.sha256
```

## Scientific boundary and next work

These are numerical/component results in one window, using repeated scans
in one observing sequence. The 37 full-support anchors are a fixed sample
of the 1,701-template bank; they do not qualify all template-specific masks.
Passing the inherited synthetic event/physical-veto tests does not establish
the final M43 pipeline. The new paired-OFF adapter has not yet been connected
to a bank-bound final retention/evidence entry point. No new threshold,
false-alarm rate, native injection/recovery curve, candidate or scientific
nondetection is claimed. Synthetic injected scores in unit tests are logic
fixtures, not a measured sensitivity experiment.

Next: integrate the already qualified source, mask, stack and sparse-OFF
components into one explicit M43 detector contract, preserving track
association and provenance. Then freeze a combined null and native-injection
calibration. Reuse M43J/L/N/O/P evidence where it applies; avoid another
unmotivated census of unchanged arithmetic. All older results and denominators
remain intact.
