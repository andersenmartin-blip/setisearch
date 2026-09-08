# Continue M43Z from the public checkpoint

Read PROJECT_DIRECTION.md, MILESTONE_43Z_JOINT_CONTROLS_PLAN.md and
MILESTONE_43Z_PLAN_AMENDMENT.md. The experiment is in progress; do not claim
final gates or substitute partial denominators for the complete panel.

Execution freeze: ac2337057670b40438bcbc3ff4c59ec2ed47626b.
Initial freeze: cdf2c8ca7154643b92c87742d207310a7fee304c.
Before any Z calibration or trial, analytical review added 32 moderate near-OFF
counterparts while preserving every original 320 case and all shift rows. This
separates added-cut costs from reference rejection by stronger OFF responses.
352 inputs, 224 signal-present, 128 pure controls, 1,408 paired endpoints, plus one
separate baseline/four endpoints. Policies: neighbor9, OFF window, remaining
aggregate and their intersection. All thresholds/rules/gates fixed publicly.

The public checkpoint contains the first 64 sealed cases and 256 endpoints under
results_m43z_joint_controls/checkpoints/inputs064.jsonl.gz and its summary/log.
Resume from these exact case records; decompress JSONL, skip blank separators,
verify seals/config/freeze/case identities and save caseNNN.json to the runtime
trial directory. Do not repeat completed numerical cases merely to resume.
The frozen runner validates saved cases and completes the remaining ones.

Calibration complete: training maximum 8.222108840942383, threshold 10;
heldout maximum 8.331631660461426, exceedances 0/128. Each set has 128 fresh rows
excluding 1,536 prior R/T/U/W/X rows. Future new rows must exclude 1,792 including Z.
No independent physical FAP, observing sequence, astronomical candidate or
general adoption claim. X's three two-epoch signal losses remain unresolved.

All six historical source receipts and 96 anchor arrays were restored exactly.
All 48 native gathers pass before calibration. Restoration logs preserve an
initial missing hdf5plugin dependency failure; installation restored the qualified
runtime. Redundant sparse HTTP caches were removed only after source/anchor
verification; source and anchor files remain. No new source scope was added.
The completed restoration summary records actual archive transport, distinct
from the numerical experiment's zero new telescope/source requests.

New workspace: /workspace/scratch/0a0bcfbb77b6/setisearch-next
Python: .venv/bin/python, PYTHONPATH=src:scripts
Runtime: /workspace/scratch/0a0bcfbb77b6/m43z_runtime/{sources,anchors,trials}
The environment supports explicit shell="bash", login=false.
Original workspace /workspace/scratch/15c947a9ca66 was cleared. Repo was cloned
from GitHub; restore again if necessary using published receipts/hashes.

The main frozen runner is scripts/m43z_joint_controls.py. It needs --freeze-commit,
--anchor-root, --source-root and --checkpoint-root. On completion run
scripts/m43z_audit_report.py then scripts/m43z_complete_report.py. Review the
complete result, matched false-veto costs, activity breakdown and exact loss
members before writing a final interpretation and publishing the full ledger.
Preserve both intermediate checkpoints and original M43T histories/LS.

Ongoing publication authorization remains valid for code, plans, results and
logs on andersenmartin-blip/setisearch m43-support-qualification and README
updates on main. No routine permission stop; no delegation or unattended promise.
