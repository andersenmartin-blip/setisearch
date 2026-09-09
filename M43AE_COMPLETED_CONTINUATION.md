# Continue from completed M43AE

M43AE execution, independent audit and lossless archive verification are
complete. Read `MILESTONE_43AE_JOINT_RESPONSE_RESULT.md` and
`results_m43ae_joint_response/ARCHIVE_README.md`. The public scientific freeze
is `d65644ac2f7e7fb84cd9913d80a16df2314c7400`, tree
`dc8f9d060df8818dcf3aabd0d9efb979e986bd16`. Its implementation and configuration
remain unchanged. The post-publication receipt is
`M43AE_PUBLICATION_COMPLETED.md`; it identifies the verified result and README
commits when present.

## Closed result

- 262 case evaluations, including one separate baseline; 3,406 paired policy
  endpoints, comprising 1,500 reused and 1,906 newly evaluated endpoints.
- 150 upstream audits reused. Only 112 additional inputs received new detector
  executions. Three separately declared upstream regression executions match
  all 19 prior-evidence fields exactly.
- All three new rules fail qualification on both panels. Historical recovery
  is 70/83 with 16, 17 and 16 leaking controls /66. Additional recovery is
  58/64 with one leaking control /48 under every new rule. The centered
  combination recovers the same signal cases with 10/66 and 0/48 leaks.
- The independent audit passes: 511 pinned files, 9,394 complete profiles,
  12,014 profile links, 55,707 new policy-member decisions and 10,774 direct
  native comparisons. No requested profile is incomplete. All 19 focused
  tests passed before the freeze.
- The 14-part XZ/base64 archive reconstructs all 264 original files byte for
  byte. XZ SHA256:
  `1ad2b2e36dfec8a085d935e12338f4fa8402d892cd0cf7ec9073259f31eee49d`.
- Result seal:
  `03095e2406baf20dea5db707437d08d4bd4b57176146913c31068eaf9866cd37`.
  Audit seal:
  `83c177c021ddc340ea7a76004bf100425729c8e19b59fd98c75416b82c87cb9d`.

There are 246 distinct native payloads on one reused observing sequence.
The additional panel has 104 distinct payloads and zero overlap with M43AB or
M43AD. No new nulls, independent sky coverage, physical false-alarm estimate,
production rule or astronomical candidate is claimed. The earlier panels and
all 1,792 prior null rows retain their original identities and denominators.

## Mechanisms to preserve in the next design

`ad_new038` is restored because the correlated OFF profile has center 3.255846;
the old 8.078562 window maximum occurs elsewhere. Every new rule preserves the
signals recovered by the centered and geometry-plus-original-OFF combinations.
The three historical losses versus neighbor9, `ad_ab_z260`, `ad_ab_z261` and
`ad_ab_z265`, remain inherited weak-epoch failures before new profile queries.

The added candidate-track hypothesis correctly finds correlated profiles for
`ad_ab_z158`, but all OFF centers remain below 5.5 (maximum 5.476272); 24 final
members survive. The additional `fresh048` control also survives as one width-33
member at score index 1808. Its candidate-track OFF centers are
3.534620/4.436933/4.743367 with correlations 0.800273/0.900754/0.989130.
Center-only amplitude is insufficient even when the shape mapping agrees.
Do not lower the floor post hoc to remove either example.

`ad_ab_fresh032` is already removed by the conjunction of geometry and remaining
support: the one above-floor remaining member is receiver-alias-vetoed, while
310 other geometry survivors fail remaining support. It receives no new OFF
profile query. Do not credit this inherited rejection to the new test.

The new additional width-17 gain `fresh017` is relative to original-OFF
combinations only. It was already recovered by the centered and aligned
comparisons. All new rules retain the same four signal-only/mixed pair losses
as neighbor9, with 31/32 signal-only and 27/32 mixed cases recovered.

## Next integrated task

Treat every M43AE input as historical. Develop one explicitly specified
response-level amplitude and confirmation study that addresses the observed
cost jointly: matched OFF profiles can be individually subthreshold, while
weak ON support may be supplied by unchanged background. Compare evidence
across profile samples and epochs only under a named, prospectively frozen
statistic, coordinate rule and calibration plan. Preserve full-profile
completeness and both track hypotheses; do not quietly reintroduce a displaced
maximum, fitted lag, truth subtraction or post-result threshold choice.

Retain the current 5.5 floor, separate remaining-epoch rule and all failed gates
until a different rule is explicitly defined and qualified. Specify signal
costs and control leaks together. Any new null inventory must exclude all
1,792 previous rows. Any new validation panel must disclose shared observing
data and native-payload overlap. No new statistic, null calibration or follow-on
endpoint has been evaluated by this checkpoint.

Reuse unchanged arithmetic and sealed original evidence. Do not rerun the
completed 262-case experiment or old exhaustive alias census merely to resume.
The original runtime was verified at
`/workspace/scratch/69269edb2f83/m43ad_runtime`; check availability and identities
before any future native work. Archive restoration and the independent audit
do not require rerunning the native experiment.

The initial publication-review block was resolved before execution by checking
the public ongoing authorization and source provenance. The later report-only
checksum-key collision was corrected with the invalid derivative and repair
receipt preserved. All scientific originals remain intact. Ongoing publication
to `andersenmartin-blip/setisearch` on `m43-support-qualification`, with README
updates on `main`, remains covered by `PROJECT_DIRECTION.md`. Delegation remains
deferred. No unattended execution is promised between active sessions.
