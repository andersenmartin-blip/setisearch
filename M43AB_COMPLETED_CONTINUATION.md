# Continue after completed M43AB

M43AB is scientifically complete and audited. This supersedes the pre-execution
status in M43AB_CONTINUATION.md; preserve that earlier document as history.
Do not rerun the numerical runner or retune this panel.

The owner explicitly approved preparation source 1ee2069 (including 1a116c6)
and README e037420 on 8 September 2026. They were published through GitHub with
byte-identical trees as af8ffd16d3126f389d2389c5ee9404218ad87eb1 and
c676ea419f72abd271575f4c2669fae7a5b29486. The scientific branch was fetched and
its tree verified before any new baseline or injection scoring. M43AB therefore
has a verified public prospective freeze; M43AA remains retrospective.

## Completed scope and result

149 executions and 1,043 paired endpoints INCLUDE one separate baseline.
36 historical cases: 19 signal-present, 17 pure controls. 112 fresh combinations:
64 signal-present, 48 pure controls. There are 141 distinct native patch payloads
including baseline, all on the same pre-existing observing sequence. Calibration
was restored unchanged; no new null rows or physical false-alarm measurement.

| Policy | Historical signals /19 | Historical controls /17 | Fresh signals /64 | Fresh controls /48 |
|---|---:|---:|---:|---:|
| neighbor9 | 16 | 13 | 52 | 15 |
| original combined | 8 | 3 | 52 | 0 |
| centered + ON/OFF agreement + aggregate | 13 | 4 | 52 | 1 |

All three new endpoints fail the predeclared development gates. No production
rule is adopted. Five historical losses are recovered by the new combination:
171 and 281 regain narrow members (32 at widths 1–65, and 13 at widths 1–9);
324/336/346 regain width-17 associations. The shared weak family 260/261/265 is
still lost to aggregation. These are tests with injected components, not sky
candidates. Original M43Z 224/128 denominators and M43X/Z failures remain intact.

The gain does not transfer as improved association counts on this fresh panel:
all seven policies recover 52/64. New combination leaves one member in fresh032
(interferer-only), whereas the old combination leaves no fresh control members.
Historical 96 releases 18 old alias-vetoed members; final combined survivors
increase 19 to 30. ON/OFF control 138 retains its width-129 member because its
correlations 0.658, -0.199, 0.471 fail the fixed 0.8 criterion despite OFF maxima
5.774, 7.328, 6.669. No parameters were adjusted after observing results.

Audit passes: 299 frozen dependency hashes, 149 sealed input records, 36 exact
historical replays plus baseline, 13,632 reference members /95,424 policy-member
decisions, 1,137 direct native centered-sample checks, 96 original arrays and
48 native gathers exact. Three synthetic tests pass. Numerical runtime 1091.089 s.
Read MILESTONE_43AB_ATTRIBUTION_RESULT.md and results_m43ab_attribution/summary.json.

## Evidence restoration and publication

The 149 original per-input gzip ledgers, full result.json and paired_signal_costs
are stored as 151 original files in a 7,218,932-byte lossless text/xz archive,
split into 14 checksummed parts. Assembled archive SHA256:
c08f76ab8120de4746173098c2f0d14ff1baa900bef9b19c219a573daa78c25a.
All original file bytes were reconstructed and verified before publication.
The archive records the required Python/zlib versions and fails on any mismatch.
After cloning, run `python scripts/m43ab_archive.py restore`, then check
RESULTS_MANIFEST_M43AB_ATTRIBUTION.sha256. Restore the historical M43Z ledger
with `python scripts/m43z_restore_ledger.py` before rerunning the artifact audit.

The completed scientific/result package and README result update are prepared
for publication after the approved preparation freeze. Check current remote
branch and main heads before any push; API-created commits can have a different
SHA while retaining exactly the local tree. Ongoing owner authorization applies
to SETI results/logs and README updates. If automatic review blocks publication,
preserve the exact review reason and ask for concrete approval only after all
unaffected work is complete; do not switch upload routes to evade a rejection.

Workspace: /workspace/scratch/626cf374c6c7/setisearch.
README worktree: /workspace/scratch/626cf374c6c7/setisearch-main.
Runtime: /workspace/scratch/626cf374c6c7/m43ab_runtime/{sources,anchors,mirrors}.
Python 3.12.13 /NumPy 2.3.5, PYTHONPATH=src:scripts. Source restoration code and
all original restoration logs remain available; do not overwrite closed logs.

## Next scientific task

Keep centered measurements and unrestricted peaks together as evidence. Develop
a width- and track-aware peak-attribution test, with explicit costs on both
recovered mixed families, alias control 96, ON/OFF control 138 and fresh032.
Investigate the broad ON/OFF response and fresh failure's stage evidence before
proposing another endpoint; do not select a new floor on this completed panel.
Weak unequal-epoch support remains a separate unresolved mechanism. Any changed
endpoint needs another public prospective freeze and additional input coverage.
Any new null rows exclude all 1,792 prior rows. Preserve LS, M43T histories and
owner direction. No delegation or unattended execution promise.
