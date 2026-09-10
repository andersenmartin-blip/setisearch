# SETIsearch — current project status

Updated 10 September 2026. This is the operational entry point for continuing
the project. Earlier milestone reports and continuation files record historical
states; their old “next step” instructions are not the current work queue.

## Verified state

| Item | State | Evidence |
|---|---|---|
| M43AF training | Published; 241 records; zero feasible boundaries among 1,156 frozen grid points | [Training result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_43AF_TRAINING_RESULT.md), [publication commit](https://github.com/andersenmartin-blip/setisearch/commit/bdab6b0af39d6bc6c81ce9d5f07ef24c103ca833) |
| M43AF complete no-model study | Completed in the saved release package: 502 records and a passing independent whole-study audit | `setisearch_M43AF_complete_release.zip`; complete publication still pending |
| Complete M43AF archive on the science branch | Not published at the verified baseline below | The branch has the training archive, but no complete-stage archive |
| Validation | 112 injection inputs and 128 held-out native nulls remain unopened | Failed training decision and unchanged executable protocol |
| New detector / new M43AF astronomical candidate | None | Failed qualification; one observing sequence |
| M43AG | A local retrospective diagnostic draft is prepared, with 13 preparation tests passed; no execution or publication is established by this cleanup | Uses only the already public 241-record training archive |
| Earlier M33 follow-up | Still unresolved; no independent HD 3651 cadence available | [M33 investigation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_33_CANDIDATE_INVESTIGATION.md) |
| LS research branch | Preserved for later work; the narrowband milestone track remains the current priority | [Project direction](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PROJECT_DIRECTION.md), [LS6A result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS6A_SCAN_END_RESULT.md) |

The 502 complete-stage records include the 241 training/baseline records and
261 historical diagnostic acquisitions. They are not 502 new independent
observations. Those historical acquisitions have already been completed in the
saved package and must not be restarted because an old continuation says they
are “remaining”.

The failed result concerns the frozen two-coordinate grid. It does not prove
that all possible detectors fail. M43AG's prepared diagnostic asks whether
finer boundaries within the same fixed rule family could change the training
trade-off. It is retrospective and provides no independent validation.

## Publication baseline and saved evidence

These are the branch heads checked before the documentation cleanup, not
the final documentation commit identifiers:

- Science: `4a0a180ea1037113fce6b24ea5524eeeca905520`.
- Main: `60bad761f4aa6eebeeef367f7a4123b80fd33e44`.
- Scientific freeze: `75b271b4b92819783692375687586d6df4f40c57`.
- Complete release ZIP SHA256:
  `82e649f8aa0faffe88d4020cda4eb5fce4cbdcda1a84015cd48774a94f673999`.

The saved ZIP contains the complete-stage evidence: 69 archive parts restoring
508 original files, including all 502 records. Its manifests and payload
hashes were checked during cleanup. No closed scientific evaluation was rerun.

A separate local transfer ledger lists 20 uploaded blobs. Uploaded blobs alone
are not a published result: a verified commit must contain the complete payload
and be reachable from the intended branch. Earlier publication notes saying
“no blobs uploaded” describe an older attempt.

The complete-package upload encountered automatic approval-review rejections.
That unresolved publication issue is separate from the already published
training decision and from the successful scientific computations. Existing
owner publication authorization remains recorded in PROJECT_DIRECTION.md.

## Continue from here

1. Read this status and the latest saved publication receipt. Inspect current
   remote branch heads and compare their trees with the complete release
   manifest before writing; preserve any newer work.
2. Resume only missing publication work when the existing upload restriction
   is resolved. Keep the original release ZIP and scientific manifests intact.
   Verify complete archive membership and byte identities before declaring
   the complete-stage release public.
3. Apply historical payloads at a dedicated release commit, then retain or
   reapply the current operational documentation separately. The release ZIP's
   README and continuation are historical publication payloads: blindly applying
   them over this cleanup would lose the current navigation and status.
   Compare a release manifest against its exact release commit.
4. Use the existing M43AG draft for the next bounded diagnostic after checking
   whether it has since been published or executed. Its inputs are the public
   training archive; it does not require native source recovery or the unpublished
   complete historical archive. Preserve its named scope and verification plan.
5. A changed feature, acceptance rule or detector needs a new prospective
   protocol and fresh evaluation inputs. General adoption also requires an
   independent observing sequence.

Do not rerun M43AF training or historical acquisitions, reopen its validation
panels, or repeat native-source downloads merely to resume publication. Old
“M11 install and reproduce” commands reproduce M11; they are not an M43AF
restart procedure.

For an explicit restoration of saved evidence, use the archive-recorded
Python 3.12.14 / zlib 1.3.2 and the frozen dependencies.
[The M43AF continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/M43AF_CURRENT_CONTINUATION.md)
distinguishes training restoration from the pending complete-stage publication.

## Verification limits

The latest five GitHub Test suite runs checked during cleanup succeeded on
`main`; the latest was
[run 34465105942](https://github.com/andersenmartin-blip/setisearch/actions/runs/34465105942).
The CI workflow is triggered for main pushes and pull requests. Its green badge
does not establish that the later science-branch code or an unpublished release
has been tested by that run. The saved focused tests and independent science
audits are separate evidence.

No running SETI worker was observed in the inspected runtime. A previous
“continue” message does not create unattended computation between sessions.
The original scientific code, protocols, seals and results remain unchanged
by this documentation cleanup.
