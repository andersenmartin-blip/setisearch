# Continue M43AD

The public M43AC package is verified at
`450b7e9f0233b9715f482157b9bd864929769a6e`; its historical publication-pending
notes are superseded by that observed remote commit.

M43AD plan/code/configuration and focused tests are prepared. No M43AD endpoint
has yet been evaluated. Read `MILESTONE_43AD_GEOMETRY_PLAN.md` and
`PROJECT_DIRECTION.md`. The owner has ongoing publication authorization for
scientific work on `m43-support-qualification` and README updates on `main`.

Eight tests pass (five new geometry/integration tests plus three unchanged
M43AB tests). All six sources and 96 original anchor arrays have been restored;
the new operational preflight also verifies all 48 native gathers exactly.
No new calibration, injection or detector rule was scored by that preflight.
The configuration pins Python 3.12.14 / NumPy 2.3.5 and installed dependencies.
Historical replay must remain exact despite the Python patch-version change.

After publishing and verifying the complete preparation tree, write a sealed
`results_m43ad_geometry/public_freeze.json` containing the observed public
`commit` and `remote_verified: true`. Fetch that commit into the local checkout.
Do not make a verification receipt based only on a local commit or an intended
upload. Then run the frozen evaluator and audit:

```bash
PYTHONPATH=src:scripts python -u scripts/m43ad_geometry.py --runtime-root ../m43ad_runtime --freeze <verified-public-commit>
PYTHONPATH=src:scripts python scripts/m43ad_audit.py
```

The evaluator saves every completed input independently and resumes only its
exact configuration/freeze. Preserve failures and completed results. The audit
adds an exhaustive alias-pair oracle and reconstructs every new correlation.
Report all new gates and explicit costs, including weak-epoch support failures.

Current checkout: `/workspace/scratch/69269edb2f83/setisearch`.
Current runtime: `/workspace/scratch/69269edb2f83/m43ad_runtime`.
If runtime is lost, restore with `scripts/m43ab_restore_runtime.py` and a NEW
receipt output directory. A fresh clone must first restore the old published
ledgers with `python scripts/m43z_restore_ledger.py` and
`python scripts/m43ab_archive.py restore`. Neither regenerates old experiments.
The new restoration receipts are in `results_m43ad_geometry/restoration/`.

No new sky coverage, physical false-alarm probability or astronomical candidate
is claimed. LS is preserved. No delegation or unattended-execution promise.
