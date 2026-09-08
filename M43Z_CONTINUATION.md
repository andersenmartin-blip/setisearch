# Continue after completed M43Z

Read PROJECT_DIRECTION.md, MILESTONE_43Z_JOINT_CONTROLS_RESULT.md and
M43Z_FAILURE_INTERPRETATION.md. M43Z is complete and audited. Do not resume its
runner or substitute the intermediate 64/160-input checkpoints for final results.

## Frozen scope and complete result

Execution freeze: ac2337057670b40438bcbc3ff4c59ec2ed47626b.
Initial freeze: cdf2c8ca7154643b92c87742d207310a7fee304c.
Before any Z calibration or trial, the public amendment added 32 moderate near-OFF
counterparts, preserving every original 320 case and all shift rows.
352 inputs / 1,408 paired endpoints: 224 signal-present, 128 pure controls.
340 distinct native patch inventories on one observing sequence; these are not
independent observations. Separate uninjected baseline: one input/four endpoints.

| Policy | Signal-associated cases / 224 | Leaking controls / 128 |
|---|---:|---:|
| neighbor9 reference | 125 | 40 |
| OFF window | 122 | 32 |
| Remaining aggregate | 120 | 15 |
| Intersection | 117 | 7 |

All three alternatives fail their frozen acceptance gates. No general adoption,
astronomical candidate, new observing coverage or independent physical FAP claim.
Earlier M43X losses remain unresolved. OFF loses signal cases 324/336/346, or
3 of 9 reference-surviving moderate-OFF cases; the original strong near-OFF
family has no reference-surviving distributed signal and cannot measure that cost.
Aggregation loses 171/260/261/265/281. The 260/261/265 family shares the same
injected signal and lost members. Case 281 is a three-active-epoch loss.
The intersection removes all eight ON-OFF and seven supported-spike leaking
cases, but seven interferer-only labels from three native patch inventories remain.
Case 96 has 19 retained members with THREE actual active epochs: two uninjected,
individually sub-5.5 background scores pool above 5.5. Use actual member activity,
not the two-epoch absent reference-truth label, in support diagnostics.

## Durable evidence and checks

Complete result: results_m43z_joint_controls/result.json.
Full sealed ledger: results_m43z_joint_controls/case_audits.jsonl.gz.
Publication stores all original bytes in ledger_parts/; after cloning, run
python scripts/m43z_restore_ledger.py before checksum verification or auditing.
Result seal: 94cfa4e5b288cb650ad0cc17b064dc0b7258f0362d23e6dcad52d43896c7a850.
Ledger SHA256: 2d14724f9592673c62334501d6adb45a8c116d074403c9e6672aa4399920de7e.
Audit passed: 288 frozen files, 352 input seals, 33,825 reference members,
135,300 policy decisions, 128 paired ON-payload invariants, all associations,
gates and intersections. All 96 restored arrays and 48 native gathers match.
The unchanged W 4,440 scalar and X 5,920 aggregate anchors are reused.
Two new composition tests pass. Numerical runtime: 2288.352 seconds.

Training maximum 8.222108840942383, threshold 10; heldout maximum
8.331631660461426, exceedances 0/128. Each set uses 128 fresh rows excluding
1,536 prior R/T/U/W/X rows. Future new rows must exclude all 1,792 including Z.
Complete loss proofs, matched costs, actual control-member support and activity
breakdowns are in the result directory. RESULTS_MANIFEST_M43Z_JOINT_CONTROLS.sha256
covers final artifacts, code, plans, closed logs and preserved checkpoints.

## Next bounded scientific task

Perform the integrated retrospective native-response and stage-transition study
specified in M43Z_FAILURE_INTERPRETATION.md. Compare the three OFF-loss inputs
with their matched signal-only/strong/far counterparts; the three aggregation-loss
families with their components; and the three residual interference configurations.
Measure native ON/OFF footprints, centers/widths and upstream veto transitions.
Determine whether shape or response matching contains separation information.
Do not lower the 5.5 floor, widen the OFF window, silently retune endpoints or
claim that the proposed diagnostic already repairs these failures. Any changed
endpoint requires its own public freeze and explicit signal/control false-veto
comparisons. Preserve X/Z losses, original denominators and M43T histories/LS.

## Runtime recovery and publication authorization

Workspace: /workspace/scratch/0a0bcfbb77b6/setisearch-next
Python: .venv/bin/python, PYTHONPATH=src:scripts
Runtime: /workspace/scratch/0a0bcfbb77b6/m43z_runtime/{sources,anchors,trials}
Use explicit shell="bash", login=false. The previous workspace was cleared.
If necessary, restore from GitHub and original receipts/hashes using
scripts/m43z_restore_runtime.py. All six historical source receipts and 96 arrays
were restored exactly. Recovery logs preserve the initial missing hdf5plugin
failure and actual archive transport; this is not new source scope. Redundant
HTTP mirrors were removed only after source/anchor verification. Keep these logs.
The scientific computation and all final postprocessing have finished.

Ongoing user authorization covers publication of SETI code, plans, results and
logs to andersenmartin-blip/setisearch on m43-support-qualification, and README
updates on main. Do not request routine publication permission again. No
delegation or unattended-work promise. Preserve the 64- and 160-input checkpoints.
