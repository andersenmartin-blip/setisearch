# Continue after M43AC retrospective diagnosis

M43AC is complete. Read MILESTONE_43AC_DUAL_EVIDENCE_RESULT.md. Do not rerun the
closed M43AB experiment or reinterpret its development inputs as independent
observations. Completed M43AB scientific/results publication was verified at
2612645426a348bcbf02917c110751e24671be57 and README main at
41548374c40eeac6db6d6fb94bbc5ff640fc8344. Older pending-publication notes describe
historical blocks, not outstanding M43AB work.

M43AC publication itself is blocked by automatic approval review running out
of context; see M43AC_PUBLICATION_PENDING.md for the exact rejection, commits,
verified destinations and restart requirements. No M43AC files or README update
have been confirmed published. Resolve publication before announcing it online.

M43AC reuses all 149 input ledgers and reconstructs only three selected native
response neighborhoods. No new detector endpoint was tested. 868 rank-eligible
alias rejections were all released by M43AB centered sampling; 861 original
best witnesses lose enough above-floor epochs, seven lose frequency agreement.
The sole fresh combined control has a fully background-supported second active
epoch (5.5014748573); broad ON/OFF control 138 has displaced increment edges and
correlations below 0.8 even after subtracting its known baseline.

The next task is a jointly specified width/track-aware attribution endpoint,
retaining both receiver measurements and explicit broad ON/OFF evidence, with
prospective additional inputs and the recovered signal families as cost checks.
Do not select new thresholds on the completed panel. Weak unequal-epoch support
remains unresolved and should not be hidden by a rule tailored to fresh032.
Any new null rows exclude all 1,792 previous rows. Preserve LS and owner
direction in PROJECT_DIRECTION.md. No delegation or unattended execution.

## Reproducibility

Use Python 3.12.13 / NumPy 2.3.5 and PYTHONPATH=src:scripts. After cloning the
scientific branch, restore the published original ledgers if absent:

```bash
python scripts/m43ab_archive.py restore
PYTHONPATH=src:scripts python -m pytest -q tests/test_m43ac_dual_evidence.py
PYTHONPATH=src:scripts python scripts/m43ac_audit.py
sha256sum -c RESULTS_MANIFEST_M43AC_DUAL_EVIDENCE.sha256
```

The audit uses stored vectors, not the large native runtime. Full reconstruction
requires original receipts, sources and anchors; restoration instructions and
code are in the M43AB preparation. Existing runtime location:
`/workspace/scratch/626cf374c6c7/m43ab_runtime/{sources,anchors,mirrors}`.

For a numerical replay, preserve the existing results directory by moving it
to a separate temporary location in a disposable checkout, then run:

```bash
PYTHONPATH=src:scripts python scripts/m43ac_dual_evidence.py
PYTHONPATH=src:scripts python scripts/m43ac_response_profiles.py --runtime-root ../m43ab_runtime
PYTHONPATH=src:scripts python scripts/m43ac_audit.py
PYTHONPATH=src:scripts python scripts/m43ac_plot_responses.py
```

Closed numerical scripts refuse to overwrite their completed summary files.
The figure renderer uses Matplotlib; preview PNGs are temporary, while the
repository contains the reproducible SVG figures. Audit and test logs are
preserved. Verify current remote heads before publishing; ongoing owner
authorization covers scientific code, plans, results, logs and README on main.
