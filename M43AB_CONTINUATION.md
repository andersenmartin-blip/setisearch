# M43AB prepared, runtime verified, public freeze blocked

Prepared 8 September 2026 after M43AA. Read PROJECT_DIRECTION.md and
MILESTONE_43AB_ATTRIBUTION_PLAN.md. M43AB is NOT executed and has NO scientific
result. No new null rows, calibration, injected input or baseline endpoint was
scored. Production code and prior M43X/Z failed gates remain unchanged.

## Completed work

- Implemented three named attribution endpoints alongside the four unchanged
  M43Z references; see `src/seti_repeater/attribution_m43ab.py`.
- Fixed panel: 36 historical cases (19 signal-present, 17 controls), 112 fresh
  combinations (64 signal-present, 48 controls), separate baseline. Planned
  total: 149 base executions and 1,043 paired endpoints, all on one historical
  observing sequence. Fresh payload identities may repeat; runner counts them.
- Three focused synthetic tests pass. Initial boundary test expected the wrong
  exception type; corrected to the existing V0P6CoverageError. Original failure
  log is preserved. No production rule was changed to accommodate the test.
- Six original telescope source receipts and 96 original anchor arrays restored
  exactly. Final operational preflight verifies all 48 native gathers and the
  original baseline provenance; 63.328 seconds. It scores no new rule or case.
- Main README-only update is prepared at local commit e037420, based on public
  main 038ca44. Publish only after the scientific branch plan is publicly live.

## Publication blocker

The conversation contains ongoing owner authorization for this exact repository,
branch, scientific files and README updates. Nevertheless automatic approval
review rejected the initial non-force git push, stating that the destination was
unverified and continuation did not clearly authorize publication.

Read-only GitHub verification then confirmed repository ID 1335786585, owner
andersenmartin-blip, public visibility, authenticated admin/push access, and branch
head c3fec57b76b9751a39ff2d1e51895fba02dc4dbd. The retry of the same non-force push
was permitted to execute but failed because shell Git lacked credentials.
The installed GitHub app's create-tree call subsequently rejected the reviewed
payload as not explicitly authorized. No further upload route was attempted.

No public M43AB freeze is verified. Do not execute the new experiment until the
owner's concrete publication approval resolves this blocker and a public freeze
is actually verified. This pause comes from automatic approval review, not a
request to renew the owner's established routine publication preference.

## Exact runtime and restart

Scientific checkout: `/workspace/scratch/626cf374c6c7/setisearch`.
README worktree: `/workspace/scratch/626cf374c6c7/setisearch-main`.
Runtime: `/workspace/scratch/626cf374c6c7/m43ab_runtime/{sources,anchors,mirrors}`.
Use `python` (3.12.13), NumPy 2.3.5, `PYTHONPATH=src:scripts`, explicit bash.
Astropy, h5py, hdf5plugin and pytest are installed in the current user environment.

If runtime is lost, use `scripts/m43ab_restore_runtime.py` with `--runtime-root`
and a NEW `--output` directory to preserve old recovery receipts. Then run
`scripts/m43ab_runtime_preflight.py --runtime-root <runtime>`. Original hashes
must match; changed archive identities must stop restoration. Cloned checkouts
also need `python scripts/m43z_restore_ledger.py` before the frozen dependency
checks. There is no reason to rerun completed M43AA.

After approval: publish the locally committed plan/code/config/tests/restoration
receipts and continuation documents to m43-support-qualification, with a normal
fast-forward update. Verify the public tree matches the local files. A GitHub
API-created commit may have a different SHA but must have the identical tree;
fetch that commit locally and use its actual verified SHA as the execution freeze.
Write a sealed `results_m43ab_attribution/public_freeze.json` with `commit` set to
that verified SHA, `remote_verified: true`, and supporting verification evidence.
Use the existing `write_sealed` helper only AFTER actual verification.

Execute `PYTHONPATH=src:scripts python -u scripts/m43ab_attribution.py
--runtime-root ../m43ab_runtime --freeze <verified-public-SHA>` with its output
redirected to a new closed run log. The script resumes sealed per-input files;
do not change endpoints, thresholds or panel selection after scoring. Audit
sealed input records, complete per-policy decisions, replay equality, native
anchors, signal/control costs and component counterparts before writing findings.
The numerical runner has not yet been exercised end-to-end on the real panel.
Any implementation failure must be preserved and corrected transparently without
silent retuning or claiming a completed prospective experiment.

Report success or failure plainly. Do not replace M43Z's 224/128 denominators with
the selected historical panel, equate labels with independent observations, or
claim that an association proves the injected component's identity. Any later
new null inventory excludes all 1,792 prior rows. No delegation or unattended
execution promise.
