# SETIsearch — current project status

Updated 12 September 2026. This is the maintained operational entry point.
Earlier reports and continuation files preserve their historical states.

## LS7D noise diagnosis completed locally: strong cross-pixel cancellation

All **120** LS7C nominal-trial noise ratios reproduce across **34 unique windows
in ten shared backgrounds**. Archived error floors alter the ratio by at most
0.0083%; local/run aperture MAD differs by a median factor 1.050. A separate
covariance calculation confirms strong cancellation: the corrected aperture
variance has a trial-weighted median of only **4.72%** of diagonal pixel variance.
The diagonal spatial approximation misses that structure. Eight analytical tests
and the scalar audit of 120 links and 68 covariance matrices pass.

This is closed-sector diagnosis, with no new injection, candidate, coverage,
threshold or adopted detector. A full 121-pixel empirical covariance is singular
with these sidebands (rank at most 107). The next combined development experiment
must handle covariance, unrelated residual pixels and compact/extended nuisance
patterns before another independent-sector evaluation.
[Result and figure](results_ls7d_noise/REPORT.md), [frozen diagnostic](LS7D_NOISE_PROTOCOL.md),
[continuation and historical LS7C name distinction](LS7D_CONTINUATION.md).

Publication: the LS7C sector 32 result and LS7D result are complete locally.
Automatic review rejected the new report upload because it required explicit
approval of the payload and public destination. No remote mutation succeeded.
The complete code/results package and main README edit are ready together.
[Exact release scope and restoration](LS7D_RELEASE_STATUS.md).

## LS7C TESS challenge completed: recovery and compact-control rejection fail

All **1,460 digital trials** completed on **18.7771 searchable cadence-days**
of L 98-59 sector 32, observed 20 November–16 December 2020. The noise-aware
pixel method was published before opening this sector. Thirty tests and the
complete ledger audit pass; the detector's joint qualification fails.

All 1,200 strength-matched trials reach their intended screening scores. Nominal
stellar recovery is 3/40, 12/40 and 27/40 at scores 8.5, 12 and 20; compact 2×2
controls leak in 0/40, 5/40 and 11/40 cases. Only 44/60 fixed 10% single pulses
recover. All 325 native excursions fail the spatial test; no LS candidate or
physical population limit is established. [Reviewed result](results_ls7c_tess/REVIEW.md).

A retrospective reconstruction of 120 recorded signal windows finds that
quadrature pixel noise exceeds run-level aperture noise by a median factor 4.66.
All 30 residual-cut failures have restored correction pixels contributing
70.9–94.8% of their weighted residual sums. These are diagnostics, not new vetoes.

LS7D has now measured the covariance/noise mismatch on the closed sector 32
backgrounds. Develop the revised spatial model on closed sectors 28/29/32,
including unrelated residual pixels and compact/extended nuisances. Do not
retune this result or open another sector merely because qualification failed.

## LS7B TESS qualification completed: weak-glint recovery failed

The correction-aware sector 29 evaluation completes all **420 digital trials**
on **19.6620 cadence-days** of screened L 98-59 data, observed 26 August–21 September
2020. Ten nonoverlapping backgrounds pass the frozen eligibility requirements.
The code and protocol were public before this sector was opened; 15 tests pass.

The detector recovers only **5/60** baseline single pulses at 1% extra aperture
flux: 35 are below threshold and another 20 fail pixel morphology. All 80 displaced
30-second profile trials are below threshold. The method remains unqualified.
No instrumental control reaches threshold either, so their 0/80 acceptance does
not demonstrate rejection of stronger nuisance events.

All 343 restored-stream native excursions fail the pixel screen and fall below
threshold in the corresponding corrected windows. The strongest four reviewed
images are consistent with cosmic-ray contamination. There is no promoted LS
candidate or astrophysical population limit.
[Reviewed result and concrete continuation](results_ls7b_tess/REVIEW.md).

LS7C subsequently tested a separately frozen noise-aware spatial method and
stronger controls on sector 32. Preserve these completed LS7B denominators and
failed gates. The earlier radio LS/M43 results are unchanged.

## Previous closed LS7 sector 28 pilot: no eligible injection anchors

The owner requested a return to optical light-sail work with TESS. The prospective
L 98-59 sector 28 pilot retrieved and checked the public 20-second light curve
and target pixels, dated 31 July–25 August 2020. Eight implementation tests pass.

The frozen quality mask fragments 20.306 accepted cadence-days into 3,779 runs.
Only 2.39 hours survive the screening guards, and no run supports the required
401-sample injection context. **Zero of the 300 planned digital trials ran.**
The method is not qualified; there is no sensitivity estimate or LS candidate.
[Full result and preserved failure](results_ls7_tess/REPORT.md).

A separate time/quality metadata comparison found 17.527 potentially searchable
cadence-days in sector 28 when correction flags 64 and 1024 are allowed. That
sector 28 alternative remains a metadata diagnostic. LS7B evaluated the explicit
flag policy on the previously unopened sector 29. LS7C subsequently opened sector 32 under its separate freeze.

## M43AI native evaluation completed

The fixed combined rule failed the predeclared same-sequence native challenge. It recovered 53/64 signal cases and lost 0/53 signals required by the reference union. 1/48 controls and 0/128 native null cases had surviving members.

[Complete result](MILESTONE_43AI_NATIVE_VALIDATION_RESULT.md). All 240 sealed records passed the final integrity and accounting audit. The exact protocol and model were public before scoring. No threshold was retuned. The original held-out panels remain unopened; the model is not adopted.

The complete result archive, audit and report accompany this science release.
The owner explicitly approved publication of the prepared M43AI package and
main README update after the earlier automatic-review rejection.
[Restore the 240 original records](results_m43ai_native_archive/README.md).

## Previous closed comparison: M43AH completed

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

## Scientific and publication state

| Item | Current state |
|---|---|
| M43AI | Complete native challenge failed; all 240 records, audit and report released |
| M43AH | Completed with full feature/family ledgers, audits, source identities and output hashes |
| M43AG | Completed exact original-boundary obstruction; [result](MILESTONE_43AG_BOUNDARY_OBSTRUCTION_RESULT.md) |
| M43AF training | Published: 241 records, failed joint qualification; [result](MILESTONE_43AF_TRAINING_RESULT.md) |
| M43AF complete no-model study | Saved and audited: 502 records; complete historical archive still awaits publication |
| Adopted new detector / new M43AF–M43AI astronomical candidate | None |
| Earlier M33 HD 3651 case | Still unresolved; [investigation](MILESTONE_33_CANDIDATE_INVESTIGATION.md) |
| LS research | [LS7D](results_ls7d_noise/REPORT.md): noise cancellation measured on closed data; [LS7C](results_ls7c_tess/REVIEW.md): 1,460 trials, qualification failed; combined covariance/residual development is next |

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

M43AI is complete. Do not rerun or retune this closed study. Any successor
requires a separately fixed protocol and new evaluation evidence. The original
held-out panels remain reserved. Main CI alone does not establish coverage of
the science branch; use the native study audit and original-byte archive checks.
