# SETIsearch — current project status

Updated 10 September 2026. This is the maintained operational entry point.
Earlier reports and continuation files preserve their historical states.

## Latest closed comparison: M43AH completed

[The M43AH epoch-support study](MILESTONE_43AH_EPOCH_SUPPORT_RESULT.md) compared
two fixed observable rule families on the 241 public closed M43AF training
records. Neither meets the joint training requirements; no rule is adopted.

| Conditional family | Fewest required signal losses with zero non-signal leaks | Fewest leaking controls while recovering all 57 |
|---|---:|---:|
| Original coordinates, exact M43AG family | 1 of 57 | 8 of 48 |
| M43AH raw second-epoch ON support | 3 of 57 | 4 of 48 |
| M43AH second-epoch ON-minus-OFF support | 6 of 57 | 12 of 48 |

M43AH exhausts 1,743 and 1,758 ON-cut equivalence classes, respectively.
A separate scalar path verifies 3,497 member features through 14,744 original
profile-center references. The fixed M43AG auditor verifies both complete
sweeps and their extrema/certificates; every zero-leak optimum has complete
case-level recovery and per-reference loss accounting. All 16 new tests pass.

The protocol, code, tests and source preflight were
[published and verified before extraction](https://github.com/andersenmartin-blip/setisearch/commit/3e6a0b60f65d9599ddc78d0aa9ec2e976d5b323f).
All 244 original training-archive files and the unchanged M43AG dependencies
were hash checked. This is retrospective development, not fresh validation.

## M43AI fixed model selected; prospective native test next

[The fixed combined model](MILESTONE_43AI_TRAINING_SELECTION.md) recovers all
57 required training signals with zero control/baseline/null surviving members.
It recovers 57 of all 64 signals. This was selected under the published
[M43AI protocol](MILESTONE_43AI_COMBINED_RULE_PROTOCOL.md); it is known-case
training evidence, not independent validation or an adopted detector.

The exact conditional rule is second-epoch ON >=6.158954620361328 OR
second-epoch ON-minus-OFF >=4.034601211547852. Both selected OFF-profile ceilings
are unbounded. The OFF-center penalty still enters the second feature.
Model seal: `be8e8523410156a162b2bd0c0629b5d4cb2fe6d872ef41be2953b95f9c24f5de`.

Next, verify the public model and evaluate the frozen 112 new injection/control
inputs (64 signals, 48 controls), then report them separately from the 128 new
native nulls. Execution order is nulls first, injections second. The 2,048
prior/reserved shift rows are excluded and the original held-out panels remain
unopened. No new validation input has been evaluated at this model publication.

All six native sources, 96 original arrays, 48 gathers, calibration binding,
zero-translation score bits and 432 direct samples have been restored exactly.
Twenty-two new tests pass. Do not repeat closed M43AF/M43AG/M43AH work or the
historical acquisitions. General adoption needs independent observing data.

## Scientific and publication state

| Item | Current state |
|---|---|
| M43AI | Fixed combined model meets training requirements; native evaluation pending |
| M43AH | Completed with full feature/family ledgers, audits, source identities and output hashes |
| M43AG | Completed exact original-boundary obstruction; [result](MILESTONE_43AG_BOUNDARY_OBSTRUCTION_RESULT.md) |
| M43AF training | Published: 241 records, failed joint qualification; [result](MILESTONE_43AF_TRAINING_RESULT.md) |
| M43AF complete no-model study | Saved and audited: 502 records; complete historical archive still awaits publication |
| Adopted new detector / new M43AF–M43AH astronomical candidate | None |
| Earlier M33 HD 3651 case | Still unresolved; [investigation](MILESTONE_33_CANDIDATE_INVESTIGATION.md) |
| LS research | Preserved for later work; [LS6A](LS6A_SCAN_END_RESULT.md) |

M43AF's 502 records include 261 already completed historical acquisitions and
the 241 training/baseline/null records. Its 940 scientific pins and earlier
endpoints remain unchanged. M43AH performs new downstream feature/rule
calculations, with no full upstream native-pipeline rerun, new telescope data
or additional observing sequence. Control-case counts are not independent
noise realizations; empty native-null/baseline retained sets supply no
conditional tail observations or physical false-alarm probability.

Current science is on m43-support-qualification; main remains a concise overview
with earlier pipeline code. [PROJECT_DIRECTION.md](PROJECT_DIRECTION.md) retains
the owner's long-term direction and ongoing publication authorization.

## Separate pending M43AF complete release

The intact saved package is `setisearch_M43AF_complete_release.zip`, SHA256
`82e649f8aa0faffe88d4020cda4eb5fce4cbdcda1a84015cd48774a94f673999`.
Its 69 parts restore 508 original files, including all 502 records.
Archive SHA256:
`b66e2a2dbe41d3dda4a63254c4528185e761aae7fdcf4745ef8e3764ca6c9443`.

Earlier automatic review rejected this complete-archive upload; that issue
remains unresolved. M43AG and M43AH use only already public training evidence
and did not upload or depend on that blocked historical archive. The prior
20-blob transfer ledger is a resume aid, not proof of a published full release.

When that review restriction is resolved, recheck current refs and missing
payloads, preserve all newer work, and verify the complete destination tree.
Keep the original ZIP and scientific manifests unchanged. If publishing their
exact historical payload at a dedicated release commit, retain/reapply current
operational documentation separately. Do not overwrite this status or the
short README with the old package versions. Compare each manifest against its
exact release commit and verify complete membership and byte identities.

[Restoration notes](M43AF_CURRENT_CONTINUATION.md) distinguish the public training
archive from the pending complete archive. Exact restoration uses recorded
Python 3.12.14 / zlib 1.3.2 and frozen dependencies.

The prospective M43AI run may start only after the model publication is
verified. Unattended work between sessions is not assumed. Main CI alone does not establish coverage of
the later science branch; use the study's own tests and recorded audits.
