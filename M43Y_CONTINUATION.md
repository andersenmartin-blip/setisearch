# Continue after completed M43Y

Read PROJECT_DIRECTION.md and MILESTONE_43Y_RESPONSE_DIAGNOSTIC_RESULT.md.
M43Y completed 13 base executions / 39 paired endpoints: six X controls, one
baseline and six ON-only/OFF-only counterparts. Historical and calibration
replays are exact. There are 11 distinct native patch inventories including
baseline; cases 13/45/109 share one. There are 18 frozen probes per input,
11,232 direct native comparisons, 285 pins, all 96 arrays and 48 gathers exact,
three tests and 12 response invariants. Runtime: 157.652 seconds.
Result seal: 3b74e94cc0d00bc9aa2c65604ff7bf0ba91c5ac7c7b1ec0e55527b6a2ad454f0.
Public scientific freeze: 84036781fa798ea54de1dffe53c162ab2cb5fdf0.
No experiment amendment or numerical rerun. Preserve the blank-line reader
failure log; it only affected unpinned result extraction and is corrected.

Seven ON-OFF surviving members: case 47 has five width129/template2/q1290–1294
members with active epochs [0,2]; cases 79/111 have the same width65/template0/
q1249 hypothesis with active epochs [1,2]. Exact active OFF maxima are below
5.5; neighborhood maxima are 6.634779 or 7.187113. In case 47, the OFF epoch2
injection lands within 8/7/7/6/5 of 16 row windows versus all 16 ON windows:
a partial native response. In cases 79/111, all 16 windows include the injection,
but the broad 40/sqrt(65) response plus differing backgrounds leaves the active
OFF maximum at 5.293052. Case 111's inactive epoch0 OFF score of 6.334426 is
correctly excluded. Nearest retained OFF track distances exceed 20 Hz:
161.233–172.575 (47), 53.878 (79), 39.699 (111). Alias evaluation found no match.

The other 27 labeled members are nine repeats under cases 13/45/109. A strong
single-epoch ON injection combines with unchanged epoch2 background scoring
5.530963–5.896018. Both two-epoch confirmation rules pass. OFF neighborhood
maxima stay below 3.874, with no retained OFF member. No absent-truth association.
The measured OFF extension does not repair this mechanism. No physical origin
of background structure or independent noise probability was established.

Next integrated M43Z: consider reusing the existing M43W OFF window with the X
aggregate, comparing reference, OFF window alone, aggregate alone and combined.
Its arithmetic matches the Y geometry; reuse unchanged implementation evidence.
Publicly freeze a meaningful fresh panel addressing unequal/two-epoch sensitivity,
strong single-epoch interference, ON-OFF response, and ON-only signals with
unrelated OFF structure to measure false-veto cost. Do not adopt a detector or
lower 5.5 on these exposed data. Preserve X's three two-epoch losses and failed
gates. New null rows must exclude 1,536 prior R/T/U/W/X rows; Y used none.

The user explicitly approves ongoing publication of code, plans, results and
logs to andersenmartin-blip/setisearch on m43-support-qualification, plus README
updates on main. No routine approval stops; collaboration/delegation deferred.
No unattended run. Preserve both M43T histories and LS. Progress is validated
methods and coverage, not milestone count. No candidate or general adoption.

Repository: /workspace/scratch/15c947a9ca66/setisearch-next
Python: .venv/bin/python with PYTHONPATH=src:scripts
Sources and anchors: /workspace/scratch/15c947a9ca66/m43t_runtime/{sources,anchors}
Y scratch checkpoints: /workspace/scratch/0a0bcfbb77b6/m43y_runtime/trials
Public ledger: results_m43y_response_diagnostic/case_audits.jsonl.gz
Use public ledgers if scratch checkpoints are pruned; verify before reuse.
