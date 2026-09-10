# SETIsearch — current project status

Updated 10 September 2026. This is the maintained operational entry point.
Earlier reports and continuation files preserve their historical states.

## Current result: M43AH completed

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

## Next integrated study

The raw-support rule loses required cases training057/071/085. The excess rule
loses training017/031/059/073/087/101. Their disjoint loss lists motivate an
explicit OR-combination as a new development hypothesis.

Specify that combined rule, deterministic training/threshold selection,
reference comparisons, signal-loss accounting and fresh native-input evaluation
together in a new protocol. The known cases remain development evidence.
Do not silently append a third method to M43AH, select a model after the fact
under its old freeze, or count known-case coverage as independent validation.

The two standalone families are now closed evidence. Do not rerun M43AH,
M43AG or the already completed M43AF acquisitions merely to continue. The next
combined-rule protocol has not yet been frozen or evaluated. Any fresh native
evaluation needs explicit input provenance and the applicable source recovery;
reading these results or preparing the design does not.

The original 112 held-out injection inputs and 128 held-out native nulls remain
unopened. A future protocol must explicitly address their status rather than
quietly treating them as fresh inputs. General detector adoption additionally
requires an independent observing sequence.

## Scientific and publication state

| Item | Current state |
|---|---|
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

No SETI worker remains active after the completed M43AH run. Unattended work
between sessions is not assumed. Main CI alone does not establish coverage of
the later science branch; use the study's own tests and recorded audits.
