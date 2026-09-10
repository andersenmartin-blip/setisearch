# SETIsearch — current project status

Updated 10 September 2026. This is the maintained operational entry point.
Earlier milestone reports and continuation files preserve historical states.

## Current activity: M43AH preparation

The [M43AH epoch-support development plan](MILESTONE_43AH_EPOCH_SUPPORT_PLAN.md),
code, 16 passing synthetic tests and source preflight are recorded with this
status before feature extraction. The two families use second-epoch ON support
with and without a per-epoch OFF penalty. This is a fixed retrospective
training study; no fresh validation is opened. Resume from its verified public
freeze and inspect saved outputs before executing anything.

## Last completed result: M43AG

The [M43AG result](MILESTONE_43AG_BOUNDARY_OBSTRUCTION_RESULT.md) exhausts the
unchanged M43AF rule `x >= a and y < b` on its already public training records.

| Fixed requirement | Original 1,156-point grid | All 2,514 ON-cut equivalence classes |
|---|---:|---:|
| Zero surviving control/baseline/null members: fewest required signal losses | 4 of 57 | **1 of 57** |
| Recover all 57 required signal cases: fewest leaking control cases | 8 of 48 | **8 of 48** |

Grid refinement alone cannot meet both requirements. All 11 associated members
of training057 are blocked by dominating control members. No new rule is
selected. These are retrospective case counts from one observing sequence;
the eight leaking cases represent four distinct native payloads.

The diagnostic protocol, code, 18 passing synthetic tests and source preflight
were [published and verified before execution](https://github.com/andersenmartin-blip/setisearch/commit/119cac883efefeb548a8a49386e3e026d33f6872).
All 244 training-archive files were hash checked. Independent checks cover
every ON-cut state, headline optimum, optimal-state index, all 72 dominance
witnesses and all 1,156 original grid points. The complete ledger, certificates,
input identities and hashes accompany the result. No M43AF acquisition was rerun.

## Scientific and publication state

| Item | Current state |
|---|---|
| M43AG | Completed, audited; result and full derived ledger accompany this status |
| M43AF training | Published: 241 records, failed joint qualification; [training result](MILESTONE_43AF_TRAINING_RESULT.md) |
| M43AF complete no-model study | Saved and audited: 502 records total; its complete historical archive still awaits publication |
| Validation | 112 injection inputs and 128 held-out native nulls remain unopened |
| Adopted new detector / new astronomical candidate from M43AF or M43AG | None |
| Earlier M33 HD 3651 case | Still unresolved; no independent cadence available; [investigation](MILESTONE_33_CANDIDATE_INVESTIGATION.md) |
| LS research | Preserved for later work; narrowband qualification remains current priority; [LS6A](LS6A_SCAN_END_RESULT.md) |

M43AF's 502 records include its 241 training/baseline records and 261 historical
diagnostic acquisitions already completed in the saved package. Do not repeat
them because an old checkpoint says they are remaining.

The original 940 scientific pins, M43AF failed qualification, earlier results
and their denominators are unchanged. The main branch remains an overview plus
earlier pipeline code; current scientific work is on m43-support-qualification.
[Project direction](PROJECT_DIRECTION.md) retains the owner's decisions.

## Next integrated design

Continue from M43AG's obstruction, not another refinement of the same threshold
grid. To retain the original recovery/rejection requirements, develop a changed
observable representation or rule family. A bounded initial hypothesis is
compatible support across epochs in the presence of strong single-epoch
interference, while preserving unequal and intermittent signals.

The known training cases are development evidence, not fresh validation.
Specify observables, controls, signal-loss accounting, and acceptance criteria
together in a new protocol before evaluating fresh inputs. Do not use injected
truth labels as detector inputs or open the old M43AF held-out panels merely
because the diagnostic is complete. General adoption also requires an
independent observing sequence.

The next design can start from the public training evidence and M43AG
certificates. Native telescope recovery or the unpublished full historical
archive is unnecessary merely to read these results or prepare that design.
M43AH now records this bounded development protocol. Its results are not yet
reported in this preparation checkpoint.

## Separate pending M43AF release

The intact saved package is `setisearch_M43AF_complete_release.zip`, SHA256
`82e649f8aa0faffe88d4020cda4eb5fce4cbdcda1a84015cd48774a94f673999`.
Its 69 parts restore 508 original files, including the complete 502 records.
The archive SHA256 is
`b66e2a2dbe41d3dda4a63254c4528185e761aae7fdcf4745ef8e3764ca6c9443`.

Earlier automatic review rejected complete-archive writes. That issue remains
unresolved. M43AG uses only already public training evidence and did not upload
or depend on that blocked complete archive. A local ledger of 20 prior uploaded
blobs is only a resume aid, not proof of a published complete release.

Before resuming that publication, recheck both remote refs and compare the
original release manifest with their trees. Preserve all newer work and
scientific pins. If applying the exact historical payload at a dedicated release
commit, retain or reapply the current short README and operational status in a
subsequent documentation commit. Do not overwrite today's status with the old
package's README or stale continuation. Compare each release manifest against
its exact release commit; verify complete payload membership and identities
before declaring publication complete.

[Archive restoration notes](M43AF_CURRENT_CONTINUATION.md) distinguish the
already public training archive from the pending complete-stage archive.
Exact restoration uses the recorded Python 3.12.14 / zlib 1.3.2 and frozen
dependencies. No closed computation needs to be restarted.

## Verification scope

M43AG has its own 18-test log and independent result audit. Main-branch CI
[passed for the cleanup](https://github.com/andersenmartin-blip/setisearch/actions/runs/34483758311);
that run alone does not test later science-branch code. No active SETI worker
is left running after this completed diagnostic, and unattended work between
sessions is not assumed.
