# Continue from the M43AF preparation

M43AE is scientifically complete; its archive and all 314 release-manifest
entries were verified again on 9 September 2026 without rerunning the experiment.
Its result seal remains
`03095e2406baf20dea5db707437d08d4bd4b57176146913c31068eaf9866cd37`.
The complete scientific release is local commit
`ff0b1a0805e1b2f6b5b337eedda510d2de940598`, tree
`4997e4adb06f152a7145a3105af70416f5adbcef`.

**Publication is complete.** The full scientific result is public at
`c875ff8548111b558cef0dec67a941b81454e97c`, M43AF preparation at
`2b7350adb8e20197fa927f75a8ba046f292319c2`, and the README update on main at
`3adb241f8f24c1b3e5468893aad00966b09b8264`. Their public refs, file identities
and complete Git trees were verified. All 14 M43AE archive parts are included.
Read `M43AE_PUBLICATION_COMPLETED.md`; it supersedes the earlier upload-block
status. No further publication approval is pending for these snapshots.

The local scientific release commits above remain provenance references. Public
GitHub commits have the same exact trees, with their own publication history.
Future sessions should first read the current public refs and this receipt.

## Work completed after M43AE

`MILESTONE_43AF_RESPONSE_STUDY_PLAN.md` specifies a signed complete-profile OFF
measurement and an ON confirmation measurement using the strongest epoch's
shape only as a template for the other active epochs. Neither is calibrated
or used to change a detector decision. The measurement code and query inventory
are in `src/seti_repeater/response_m43af.py`.

The key acquisition change is to request complete profiles after geometry/rank
eligibility but before the old remaining-epoch cut. M43AE's unqueried neutral
placeholders are not measured profiles. Its stored weak-loss example
`ad_ab_z260` has no queried profile, so reusing only its saved queried profiles
would not investigate the weak-epoch problem.

All 28 focused tests pass: 14 new constructed-vector/query checks and the
existing 14 M43AE/M43X regression cases. The receipt and exact tested file hashes
are in `results_m43af_preparation/`. No new scientific profile measurement,
native endpoint, null row, calibration threshold or observing sequence has been
evaluated. The new code is preparation, not a publicly frozen executable study.

## Remaining integrated work

After M43AE publication, implement native acquisition of the additional
pre-confirmation profiles with exact original overlay identities and a separate
scalar/coordinate audit. Then specify explicit calibration and held-out
inventories excluding all 1,792 earlier null rows, the joint training rule and
the additional native validation panel. The plan lists the required selection
and correlation accounting. Publish and verify the whole executable scientific
freeze before evaluating it. Do not tune cuts on M43AE examples.

Reuse completed detector arithmetic and the sealed evidence. Do not rerun the
262-case M43AE experiment merely to resume. The earlier native runtime was at
`/workspace/scratch/69269edb2f83/m43ad_runtime`; verify its availability and
identities before any future native acquisition. All old failed gates and
original denominators remain in force. No delegation or unattended execution.
