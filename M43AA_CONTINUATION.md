# Continue after locally completed M43AA

M43AA is complete, audited, and locally committed. Do not rerun its numerical
runner or treat its local freeze as a public prospective freeze. Read
PROJECT_DIRECTION.md, MILESTONE_43AA_NATIVE_RESPONSE_RESULT.md, and
results_m43aa_native_response/artifact_validation.json.

## Exact completed scope

Local execution freeze: 6edf2b28bfc1f53dc1d16bd3bdddcedee7f378f5.
32 executions / 128 endpoints INCLUDE the separate baseline: 28 historical Z
replays, three moderate-OFF component-only inputs, one uninjected baseline.
32 distinct native patch inventories on the existing single observing sequence.
754 stage probes, 266 complete 321-sample response neighborhoods, 12,768 native
scalar comparisons. All original 96 arrays and 48 gathers exact; historical
audits and all four policy decisions exact; Z calibration restored with no new
or recalculated shifts. Three focused unit tests and artifact audit pass.
Runtime 293.261 seconds. Two PNG figures have been visually checked.

The two new paired receiver-alias proofs show unchanged central width-1 ON/OFF
scores in 170/171 and 280/281, but altered local receiver peaks and a new alias
veto. Associated narrow mixed members are vetoed upstream; aggregation then
removes the broad remaining associated members. The weak 260/261/265 family is
a separate remaining-score failure even in signal-only input.

Residual controls 6/16/96 have 12/3/19 combined survivors. Their entire uninjected
supporting response vectors equal baseline. Case 96 uses three ACTUAL active
epochs. These are three native configurations representing seven original Z
labels; preserve the original denominator. A single global lower-bound cut on
the measured inter-epoch correlation cannot remove all residual controls while
retaining all selected signals (control 6 correlations 0.901–0.926 versus weak
signal 260 correlations 0.076–0.193).

Nearby ON/OFF response correlation contains descriptive separation information
in the selected comparison, but the three matched ON-OFF controls already have
zero reference survivors. Do not claim that any of the eight original leaking
ON-OFF controls has been repaired. No detector, threshold or science gate changed.

## Remaining publication task

The user already granted ongoing publication authorization on 7 September 2026,
as preserved in conversation context and the live public PROJECT_DIRECTION.md.
Automatic approval review nevertheless rejected the exact non-force GitHub push
twice, including after a live verification of destination and authorization.
It classified historical authorization as untrusted retrieved content and did
not accept 'continue SETI' as approval of this exact payload. No connector,
alternate host, indirect upload or other bypass was attempted.

The final response asks for concrete approval only because this automatic review
blocked publication. After approval, publish all locally committed M43AA plan,
code, tests, results, two plots, complete input ledgers and closed logs to
andersenmartin-blip/setisearch on m43-support-qualification. Then publish the
prepared README-only commit 4250c7ae6f7fb5c0299b9947da6849275125520b to main.
Do not include unrelated files or force-push. Check current remote heads first.
The README worktree is /workspace/scratch/c6cafebacdb1/setisearch-main, based on
main 324a3e7. The scientific worktree is
/workspace/scratch/0a0bcfbb77b6/setisearch-next. Check its git log for the final
M43AA result commit after the initial freeze 6edf2b2; publication-pending notes
and checksums are included there. README links become live after branch push.

## Next scientific task

Use the concrete attribution evidence to develop a candidate-centered receiver
signature comparison, jointly with centered ON/OFF response agreement. Include
both mixed signal-loss pairs, all eight original leaking ON-OFF cases, residual
background configurations, the weak unequal signal family, and genuine alias
controls in explicit signal/control costs. Do not adopt a simple global shape
correlation cut. Any new decision endpoint requires a separate public prospective
freeze and fresh evaluation inputs; prior X/Z failed gates remain. New null rows,
if required, exclude all 1,792 prior rows. Preserve M43T history, LS and owner
control. No delegation or unattended execution promise.

## Runtime if later needed

Use .venv/bin/python, PYTHONPATH=src:scripts, explicit bash/login=false.
Native source/anchor cache remains at
/workspace/scratch/0a0bcfbb77b6/m43z_runtime/{sources,anchors,trials}.
The complete M43Z source recovery and ledgers remain intact. The new response
ledgers are gzip JSON files in results_m43aa_native_response/inputs/ and are
covered with the new code/report/logs by RESULTS_MANIFEST_M43AA_NATIVE_RESPONSE.sha256.
