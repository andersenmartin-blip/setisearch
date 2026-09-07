# Continue after completed M43X

M43X is complete: 256 declared input cases / 256 base executions / 768 paired
endpoints, with 160 signal-present and 96 pure controls. There are 244 distinct
native patch inventories; do not claim 256 independent realizations.

Read MILESTONE_43X_CONFIRMATION_RESULT.md and PROJECT_DIRECTION.md first.
Neighbor9: 137/160 signal associations, 28/96 leaking controls.
Hard per-epoch confirmation: 132/160 signal associations, 6/96 leaking controls.
Strongest-epoch-excluded aggregate: 134/160 signal associations, 6/96 leaking controls.
Both alternatives fail no-signal-loss and zero-ON-OFF-leak gates. ON-OFF leaks
remain 3/32 under every policy. Both additions remove all supported spikes,
but there are three leaking interferer-only input cases without absent-truth
association. No detector is adopted and no astronomical candidate is promoted.

Restored cases 226/228 are the same three-epoch unequal signal with/without
interference; aggregate preserves 35/40 three-epoch signal associations versus
33/40 for the hard rule. Both additions retain 99/120 two-epoch associations,
versus reference 102/120. Aggregate losses are cases 2/132/180. All are uneven
strength-16 cases; 132/180 are mixed-only associations absent in signal-only.
Do not reinterpret gate failures as successes or claim two independent restorations.

Surviving pure controls: interferer-only 13/45/109 (identical native patch
inventory), and ON-OFF 47/79/111. Survivors use widths 65/129 and two actual
active epochs. Control evidence is an extraction of frozen outcomes, not a
reconstruction of paired OFF scores; it does not prove the exact OFF failure cause.

Public scientific freeze: 0d4406c5a6a7106f49a71d809fc7c79731ccc238.
Public 96-case checkpoint: 634cd9fc0471f23d14e0faa72af1ecb02e2c8808.
Public audit-only amendment: 791c6dc2ad7632b77e7debed62e2b81518df1a56.
V1 audit incorrectly checked whole-case policy equality based on injected truth
activity; a two-epoch injection can produce three-epoch retained hypotheses.
V2 checks each actual member and passes all seals, associations, gates, 273 pins
and 73,227 policy decisions. Preserve v1 and its failure log. No detector or
scientific rule was altered. Four focused tests plus one audit regression pass.

Training/heldout: 128/128 new shifts, maxima 8.553452/8.319118, common threshold
10, heldout 0/128. Future fresh rows must exclude 1,536 total prior R/T/U/W/X
rows. No independent physical FAP or OFF false-veto probability is inferred.
The runtime was 1,619.402 seconds; no new telescope requests were made.

Next M43Y: prospectively plan a combined response-aware control diagnostic,
then exactly reconstruct broad-filter controls and matched baseline/component
counterparts. Exposed cases are development evidence only. Inspect native
ON/OFF response across width/carrier before proposing a new OFF endpoint.
Preserve the two-epoch sensitivity failure; do not tune 5.5 to these losses.
Any scientific change needs a new public freeze and full signal/control gates.

The user explicitly renewed ongoing approval in THIS conversation for SETI
code, plans, results and logs to andersenmartin-blip/setisearch on
m43-support-qualification, and README updates on main. Continue without
routine approval stops. Collaboration remains deferred. No unattended run
continues between sessions. Earlier M43T branch histories and LS remain intact.

Runtime repository: /workspace/scratch/15c947a9ca66/setisearch-next
Python: .venv/bin/python (PYTHONPATH=src:scripts)
Native sources: /workspace/scratch/15c947a9ca66/m43t_runtime/sources
Anchors: /workspace/scratch/15c947a9ca66/m43t_runtime/anchors
Case checkpoints: /workspace/scratch/0a0bcfbb77b6/m43x_runtime/trials
Full case ledger and all results are under results_m43x_confirmation.
Verify retained data before reuse; public restoration scripts can recover lost
runtime inputs. Do not rerun completed M43X merely to resume the next milestone.
