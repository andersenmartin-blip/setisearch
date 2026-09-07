# Resume M43X: qualified protocol, publication blocked

M43W remains the latest completed public trial. M43X's complete code, plan,
configuration, audit and four focused tests are committed locally at `ba2abaa2cce5a84b1fcbdc9353eaeb23560a8911`.
All 273 pinned dependencies verify, all 96 original arrays and 48 native
gathers are exact, and all 5,920 new scalar aggregate comparisons passed.
The preflight artifact recorded the literal ref HEAD; preflight_validation.json
binds that ref to the exact local protocol commit. This is not a public freeze.
No new null row or prospective M43X case has been evaluated.

The planned panel has 256 declared native input cases, 160 signal-present and
96 pure controls, with 768 paired endpoints from 256 base executions. Some
control cases can duplicate numerical inputs across activity labels; the audit
reports duplicate native patch inventories. These are not independent
observations. Read MILESTONE_43X_CONFIRMATION_PLAN.md for exact rules and gates.

## Actual publication block

GitHub create_tree was rejected twice by automatic approval review. The first
rejection said continuation did not explicitly authorize uploading local code,
configuration and research metadata to GitHub. The second rejected the same
unchanged eight-file upload after the previous user authorization and public
PROJECT_DIRECTION.md were checked, saying retrieved authorization was not
user-authored approval in this transcript. Nothing was uploaded by either call.
Do not bypass that block using another transport. Request current user approval
for publication of SETI code, plans, results and logs to
andersenmartin-blip/setisearch on m43-support-qualification, plus README on main.
The prior ongoing approval remains in PROJECT_DIRECTION.md; it was not enough
for this automatic reviewer. No scientific rule has been weakened to work around it.

## Continue after approval

1. Verify remote qualification head, currently 55e833638ec238de56e0530440827df9738f0f7e.
2. Publish the M43X protocol files and preflight evidence to that branch using
   the authorized GitHub connector. Preserve all earlier results and branches.
3. Reconstruct the returned public commit locally and verify its tree exactly.
   Use its full SHA for --freeze-commit, never the literal HEAD.
4. Run the full M43X trial, then scripts/m43x_audit_report.py. Preserve failures
   and all sealed checkpoints; do not change thresholds or gates after scoring.
5. Publish complete results, manifest, logs and a clear main README update.

Runtime repository: /workspace/scratch/15c947a9ca66/setisearch-next
Python: .venv/bin/python with PYTHONPATH=src:scripts
Source root: /workspace/scratch/15c947a9ca66/m43t_runtime/sources
Anchor root: /workspace/scratch/15c947a9ca66/m43t_runtime/anchors
New checkpoint root: /workspace/scratch/0a0bcfbb77b6/m43x_runtime/trials
Command: scripts/m43x_confirmation.py --freeze-commit FULL_PUBLIC_SHA
 --source-root SOURCE_ROOT --anchor-root ANCHOR_ROOT --checkpoint-root CHECKPOINT_ROOT
Use --preflight-only solely for baseline qualification, already passed here.
Do not rerun earlier milestones. No computation continues unattended.
