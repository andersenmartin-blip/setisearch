# Continue from the M43AF preparation

M43AE is scientifically complete; its archive and all 314 release-manifest
entries were verified again on 9 September 2026 without rerunning the experiment.
Its result seal remains
`03095e2406baf20dea5db707437d08d4bd4b57176146913c31068eaf9866cd37`.
The complete scientific release is local commit
`ff0b1a0805e1b2f6b5b337eedda510d2de940598`, tree
`4997e4adb06f152a7145a3105af70416f5adbcef`.

**Publication remains incomplete.** At the last verified check the public
scientific branch was `d65644ac2f7e7fb84cd9913d80a16df2314c7400`, and main was
`758377712cf60f51bbeea3a5385eaa9b665006e3`. No ref was changed in this session.
An accepted Git blob is not a published result. See the outer continuation
package's operational receipt for the blocked upload and accepted blob inventory;
do not infer that an archive is complete from one accepted part.

The ready README-only commit remains
`55cc942fd6ccbc28bdff7f6ece5ef8649fd4bac2`, tree
`6e89ce8e86a60812c105658b9d20d24305783370`. Publish the full M43AE scientific
release before the README, then record the verified public identities. Publish
the new preparation as a separate scientific commit. Compare current refs first
and preserve any intervening work. Do not publish stale private upload-review
handoffs as scientific results.

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
