# M43AE result: joint response attribution is insufficient

**Completed after the public freeze. All three new policies fail qualification on both panels.**

Requiring the OFF amplitude to come from the exact compared profile restores the M43AD width-17 signal counterexample. The added candidate-track hypothesis finds correlated control profiles, but their centers can remain below the unchanged 5.5 floor. The experiment therefore resolves a specific attribution error without qualifying an improved combined detector. No policy is adopted.

The new policies recover **70/83 historical signals** with **16, 17 and 16 leaking control inputs out of 66**, respectively. All three recover **58/64 additional signals** with **1/48 leaking controls**. The centered combination recovers the same signals with fewer leaking control inputs: **10/66 and 0/48**. These are conditional injection/control results on one reused observing sequence.

## Protocol, denominators and reuse

The [public freeze](https://github.com/andersenmartin-blip/setisearch/commit/d65644ac2f7e7fb84cd9913d80a16df2314c7400) fixed the [complete protocol](MILESTONE_43AE_JOINT_RESPONSE_PLAN.md), implementation, independent audit, 19 passing focused tests and 511 dependency hashes before any new endpoint evaluation. Both the public ref and exact Git tree were verified.

| Work item | Count | Meaning |
|---|---:|---|
| Historical signal/control inputs | 149 | All M43AD non-baseline inputs: 83 signals and 66 controls |
| Additional signal/control inputs | 112 | 64 signals and 48 controls at predeclared score indices 1792/2304, nominal strength 28 |
| Separate baseline | 1 | Zero final members under all 13 policies |
| Case evaluations | 262 | Historical evidence reused where arithmetic is unchanged |
| Paired policy endpoints including baseline | 3,406 | 1,500 reused and 1,906 newly evaluated |
| New-input detector executions | 112 | Ten prior policies plus the three new policies |
| Upstream regression executions | 3 | baseline, ab_z138 and new038 reproduce all 19 returned prior-evidence fields exactly |
| Distinct native payload identities | 246 | 142 historical/baseline and 104 additional; not independent observations |

The 1,906 newly evaluated endpoints comprise 786 new-policy evaluations on all 262 cases and 1,120 prior-policy comparisons on the 112 additional inputs. The result ledger has 3,393 non-baseline endpoint rows; baseline counts are separate. All 104 additional payload identities are absent from both the M43AB and M43AD inventories. Eight additional cases repeat a native payload within the same panel; all repeats are listed in [report_summary.json](results_m43ae_joint_response/report_summary.json). The historical /83 and /66 denominators combine the entire M43AD panel. Earlier /19 and /18 results remain unchanged.

Both hypotheses use the unchanged geometry receiver decisions and independent remaining-epoch requirement. `receiver_mean` maps the OFF vector to equal predicted mean receiver frequencies; it is not exact equality of full integration tracks. `candidate_track` uses the same template and carrier in both scan kinds, with each scan's own factors and no interpolation or fitted lag. A veto requires ON center >=5.5, OFF center >=5.5 and mean-subtracted correlation >=0.8 at the same compared profile. The original window maximum is diagnostic only. The dual rule rejects if either hypothesis rejects. No truth label, fitted shift, background subtraction, threshold adjustment or production change enters these rules.

## Complete paired comparison

A leaking control contains any final diagnostic member. A false control association additionally meets the unchanged truth-association endpoint. Zero false associations therefore does not establish zero control leakage.

| Policy | Historical signals /83 | Historical leaks /66 | Historical false associations /66 | Additional signals /64 | Additional leaks /48 | Additional false associations /48 |
|---|---:|---:|---:|---:|---:|---:|
| neighbor9 reference | 73 | 29 | 1 | 58 | 13 | 0 |
| Original OFF window | 68 | 18 | 1 | 57 | 12 | 0 |
| Remaining-epoch aggregation | 68 | 17 | 0 | 58 | 1 | 0 |
| Original OFF + aggregation | 63 | 6 | 0 | 57 | 0 | 0 |
| Centered receiver | 73 | 29 | 1 | 58 | 13 | 0 |
| Centered receiver + ON/OFF agreement | 73 | 20 | 1 | 58 | 12 | 0 |
| Centered combination | 70 | 10 | 0 | 58 | 0 | 0 |
| Geometry receiver | 73 | 29 | 1 | 58 | 13 | 0 |
| Geometry + original OFF + aggregation | 65 | 6 | 0 | 57 | 0 | 0 |
| Geometry + aligned OFF + aggregation | 69 | 14 | 0 | 58 | 1 | 0 |
| Joint receiver mean + aggregation | 70 | 16 | 0 | 58 | 1 | 0 |
| Joint candidate track + aggregation | 70 | 17 | 0 | 58 | 1 | 0 |
| Joint dual hypothesis + aggregation | 70 | 16 | 0 | 58 | 1 | 0 |

The dual rule has the same case-level outcomes as receiver mean alone on both panels. Relative to remaining-epoch aggregation, receiver mean/dual remove only the historical `ad_ab_z138` control input; the candidate-track combination removes no additional control input on either panel. Member counts and profile-veto details remain available even when the case-level endpoint is unchanged.

## Acceptance gates

| Panel | New policy | Failed predeclared requirements | Qualification |
|---|---|---|---|
| historical | Joint receiver mean + aggregation | `no_signal_loss`, `zero_control_members` | FAIL |
| historical | Joint candidate track + aggregation | `no_signal_loss`, `zero_control_members` | FAIL |
| historical | Joint dual hypothesis + aggregation | `no_signal_loss`, `zero_control_members` | FAIL |
| fresh | Joint receiver mean + aggregation | `zero_control_members` | FAIL |
| fresh | Joint candidate track + aggregation | `zero_control_members` | FAIL |
| fresh | Joint dual hypothesis + aggregation | `zero_control_members` | FAIL |

All other applicable gates pass: no false control associations, strict leak reduction versus neighbor9, zero baseline members, complete requested evidence, preservation of centered-combination and geometry-plus-original-OFF signals, and additional-payload novelty. Historical signal losses versus neighbor9 are exactly `ad_ab_z260`, `ad_ab_z261` and `ad_ab_z265` for all three new policies. The unchanged remaining-epoch rule rejects their surviving geometry members before any new profile query; these are not new profile-induced losses. No qualifying gate is relaxed because the other requirements pass.

## Mechanism evidence and signal costs

**The displaced maximum no longer rejects the historical width-17 signal.** In `ad_new038`, the correlated receiver-mean profile has correlation 0.955689 and OFF center 3.255846. The old OFF-window maximum is 8.078562 at another coordinate. M43AD combined that maximum with the aligned shape; M43AE requires amplitude at the compared center and retains the signal. All three policies gain this one historical signal relative to geometry plus aligned OFF, while receiver mean/dual add two leaking controls (`ad_ab_z038`, `ad_ab_z078`); candidate track also adds `ad_ab_z138`.

**The candidate-track mapping finds the moving control shape, but not an above-floor center.** `ad_ab_z158` retains 24 final members under all three new policies. Its 72 candidate-track profiles have correlations 0.894285–0.985247, but OFF centers only 4.572423–5.476272. None reaches 5.5. Receiver-mean OFF centers are still lower. Thus the moving-track alternative is queried correctly; the amplitude criterion remains insufficient for this control. The threshold is not lowered after seeing this example.

**The sole additional leaking control has the same limitation.** `fresh048` is an ON/OFF control at nominal score index 1792. One width-33 member centered at score index 1808 survives. Its candidate-track OFF centers are 3.534620, 4.436933 and 4.743367, with correlations 0.800273, 0.900754 and 0.989130. All centers remain below 5.5. The original OFF-window rule finds a maximum of 5.543846 elsewhere and rejects it. This control is not truth-associated under the frozen <=20 Hz endpoint, which explains the simultaneous zero false-association count.

**The additional signal gain is conditional on the comparison.** All three new rules retain `fresh017`, a width-17 distributed signal with unrelated nearby OFF power. It is lost by geometry plus the original OFF rule, but is already recovered by both the centered combination and geometry plus aligned OFF. The receiver-mean OFF center in epoch 0 is 6.655884, but its correlation is only 0.529233; amplitude alone does not establish a shared response.

**Inherited rejection must not be credited to the new OFF test.** For `ad_ab_fresh032`, 310 rank-eligible members pass geometry but fail the remaining-epoch requirement. The only rank-eligible member passing that requirement (5.501475) already has a receiver-alias veto under geometry. No new response profile is requested for this input. Its removal from the centered comparison is inherited geometry/aggregation evidence, not a newly demonstrated OFF-profile success.

The [mechanism diagnostic views](results_m43ae_joint_response/mechanism_diagnostics.json) retain all queried members of nine historical anchors and the two outcome-selected additional examples above. They aggregate unqueried failures and give bounded upstream-veto examples; every original member remains in the complete archive. These views are retrospective explanations and do not modify the frozen experiment.

### Matched signal-only/mixed pairs

All 32 additional pairs are evaluated under all 13 policies (416 comparisons). For each new policy, 31/32 signal-only cases and 27/32 mixed cases are recovered. The four paired losses are already present under neighbor9: `fresh000`→`fresh001`, `fresh056`→`fresh057`, `fresh100`→`fresh101`, and `fresh107`→`fresh108`. No additional paired loss is introduced by the new policies. The original-OFF combinations additionally lose `fresh016`→`fresh017`.

| Policy | Signal-only recovered /32 | Mixed recovered /32 | Paired losses |
|---|---:|---:|---:|
| neighbor9 reference | 31 | 27 | 4 |
| Original OFF window | 31 | 26 | 5 |
| Remaining-epoch aggregation | 31 | 27 | 4 |
| Original OFF + aggregation | 31 | 26 | 5 |
| Centered receiver | 31 | 27 | 4 |
| Centered receiver + ON/OFF agreement | 31 | 27 | 4 |
| Centered combination | 31 | 27 | 4 |
| Geometry receiver | 31 | 27 | 4 |
| Geometry + original OFF + aggregation | 31 | 26 | 5 |
| Geometry + aligned OFF + aggregation | 31 | 27 | 4 |
| Joint receiver mean + aggregation | 31 | 27 | 4 |
| Joint candidate track + aggregation | 31 | 27 | 4 |
| Joint dual hypothesis + aggregation | 31 | 27 | 4 |

## Verification and preserved evidence

The independent audit passes for all 262 inputs and all 511 pinned files. It reconstructs **9,394 complete profiles**, **12,014 member/profile links** and **55,707 new policy-member decisions** over **18,569 retained members**. It reconstructs 1,903 new non-baseline truth associations and verifies 1,490 reused endpoint rows exactly against their sealed M43AD sources, whose completed audit remains pinned. There are **zero incomplete profile requests**. The direct-check inventory contains **10,774 exact native comparisons**: 6,080 historical and 4,694 additional. These direct checks sample the first complete query per epoch/width/hypothesis, with identical coordinates deduplicated; they are not an exhaustive reread of every sampled profile value. All requested profile arithmetic is independently reconstructed from the persisted samples. The three upstream replay anchors also reproduce their prior direct checks exactly.

The 96 source arrays, 48 native gathers and unchanged calibration binding match. The focused suite has **19 passing tests** (14 new-rule/adapter/oracle cases plus five M43AD regressions). The existing exhaustive alias census was not repeated; its unchanged dependencies and the three explicit upstream replays bound that reuse. Execution completed in 980.376 seconds without an abort or scientific amendment. The public freeze remains unchanged.

The [lossless archive](results_m43ae_joint_response/ARCHIVE_README.md) stores **264 original files** in **14 base64 XZ parts** (5,472,132 compressed bytes). Every file was reconstructed byte for byte with Python 3.12.14 / zlib 1.3.2. The XZ archive SHA256 is `1ad2b2e36dfec8a085d935e12338f4fa8402d892cd0cf7ec9073259f31eee49d`. The complete result, all 262 sealed inputs, paired costs, original execution/audit logs, preparation receipts and dependency identities are retained. [Archive instructions](results_m43ae_joint_response/ARCHIVE_README.md) restore the existing M43Z/M43AB/M43AD dependencies without rerunning them.

Automatic review initially blocked the new configuration publication. Verification of the public ongoing authorization, exact destination and public-data derivation resolved that block before execution. The accepted retry and public-freeze verification are recorded in [publication_review.json](results_m43ae_joint_response/publication_review.json). Postprocessing reduced duplicate diagnostic views to bounded examples while preserving every original archived input. The report reader then detected a reserved checksum-key collision in the derived summary: its parent-result identity used the summary's own seal field. The invalid summary is preserved, and the parent identity now uses `source_result_sha256` with a separately verified summary seal. [Postprocessing repair](results_m43ae_joint_response/postprocessing_repair.json) records the exact metadata-only correction. All scientific inputs, the completed result, audit and archived bytes remain unchanged.

## Continuation and claim boundary

M43AE is closed as a negative qualification result. The same-response amplitude requirement is more explicit, but the tested center-only threshold loses control sensitivity. Neither the dual hypothesis nor the candidate-track alternative qualifies for adoption. The old centered rule is a reference comparison, not newly certified for general use by this result.

The next design question is whether response-level amplitude evidence across the profile and epochs can distinguish the matched subthreshold OFF controls while preserving broad and unequal-epoch signals. Any such rule needs its own prospective specification, signal-cost gates and independent calibration/validation; these examples must be historical. Keep the current 5.5 floor and the separate weak-epoch problem intact until a new rule is explicitly frozen and qualified. Do not replace same-response attribution with a displaced maximum or tune a cutoff to the known controls.

There are **zero new null rows**, **zero new observing sequences**, no physical false-alarm probability estimate and no astronomical candidate claim. All **1,792 prior null rows** remain excluded from any future new null inventory. These interventions reuse one observing sequence; their counts do not measure independent sky coverage. Continue from [M43AE_COMPLETED_CONTINUATION.md](M43AE_COMPLETED_CONTINUATION.md).

## Exact named endpoint changes

The following lists compare each new rule to all four frozen references. Empty lists are shown as None. They include every gain/loss and added/removed leaking control input; the corresponding endpoint rows and counts are in [report_summary.json](results_m43ae_joint_response/report_summary.json).

### historical: `joint_receiver_off_aggregate`

| Reference | Signal gains | Signal losses | Added leaking controls | Removed leaking controls |
|---|---|---|---|---|
| Centered combination | None | None | `ad_ab_z038`, `ad_ab_z078`, `ad_ab_z148`, `ad_ab_z158`, `ad_ab_z198`, `ad_ab_z278`, `ad_ab_z318`, `ad_new076`, `ad_new104` | `ad_ab_z138`, `ad_ab_fresh032`, `ad_new032` |
| Geometry + aligned OFF + aggregation | `ad_new038` | None | `ad_ab_z038`, `ad_ab_z078` | None |
| Geometry + original OFF + aggregation | `ad_ab_z324`, `ad_ab_z336`, `ad_ab_z346`, `ad_new003`, `ad_new038` | None | `ad_ab_z038`, `ad_ab_z078`, `ad_ab_z148`, `ad_ab_z158`, `ad_ab_z198`, `ad_ab_z278`, `ad_ab_z318`, `ad_new076`, `ad_new090`, `ad_new104` | None |
| neighbor9 reference | None | `ad_ab_z260`, `ad_ab_z261`, `ad_ab_z265` | None | `ad_ab_z138`, `ad_ab_z176`, `ad_ab_z266`, `ad_ab_fresh032`, `ad_new005`, `ad_new032`, `ad_new047`, `ad_new060`, `ad_new067`, `ad_new074`, `ad_new088`, `ad_new102`, `ad_new109` |

### historical: `joint_track_off_aggregate`

| Reference | Signal gains | Signal losses | Added leaking controls | Removed leaking controls |
|---|---|---|---|---|
| Centered combination | None | None | `ad_ab_z038`, `ad_ab_z078`, `ad_ab_z148`, `ad_ab_z158`, `ad_ab_z198`, `ad_ab_z278`, `ad_ab_z318`, `ad_new076`, `ad_new104` | `ad_ab_fresh032`, `ad_new032` |
| Geometry + aligned OFF + aggregation | `ad_new038` | None | `ad_ab_z038`, `ad_ab_z078`, `ad_ab_z138` | None |
| Geometry + original OFF + aggregation | `ad_ab_z324`, `ad_ab_z336`, `ad_ab_z346`, `ad_new003`, `ad_new038` | None | `ad_ab_z038`, `ad_ab_z078`, `ad_ab_z138`, `ad_ab_z148`, `ad_ab_z158`, `ad_ab_z198`, `ad_ab_z278`, `ad_ab_z318`, `ad_new076`, `ad_new090`, `ad_new104` | None |
| neighbor9 reference | None | `ad_ab_z260`, `ad_ab_z261`, `ad_ab_z265` | None | `ad_ab_z176`, `ad_ab_z266`, `ad_ab_fresh032`, `ad_new005`, `ad_new032`, `ad_new047`, `ad_new060`, `ad_new067`, `ad_new074`, `ad_new088`, `ad_new102`, `ad_new109` |

### historical: `joint_dual_off_aggregate`

| Reference | Signal gains | Signal losses | Added leaking controls | Removed leaking controls |
|---|---|---|---|---|
| Centered combination | None | None | `ad_ab_z038`, `ad_ab_z078`, `ad_ab_z148`, `ad_ab_z158`, `ad_ab_z198`, `ad_ab_z278`, `ad_ab_z318`, `ad_new076`, `ad_new104` | `ad_ab_z138`, `ad_ab_fresh032`, `ad_new032` |
| Geometry + aligned OFF + aggregation | `ad_new038` | None | `ad_ab_z038`, `ad_ab_z078` | None |
| Geometry + original OFF + aggregation | `ad_ab_z324`, `ad_ab_z336`, `ad_ab_z346`, `ad_new003`, `ad_new038` | None | `ad_ab_z038`, `ad_ab_z078`, `ad_ab_z148`, `ad_ab_z158`, `ad_ab_z198`, `ad_ab_z278`, `ad_ab_z318`, `ad_new076`, `ad_new090`, `ad_new104` | None |
| neighbor9 reference | None | `ad_ab_z260`, `ad_ab_z261`, `ad_ab_z265` | None | `ad_ab_z138`, `ad_ab_z176`, `ad_ab_z266`, `ad_ab_fresh032`, `ad_new005`, `ad_new032`, `ad_new047`, `ad_new060`, `ad_new067`, `ad_new074`, `ad_new088`, `ad_new102`, `ad_new109` |

### fresh: `joint_receiver_off_aggregate`

| Reference | Signal gains | Signal losses | Added leaking controls | Removed leaking controls |
|---|---|---|---|---|
| Centered combination | None | None | `fresh048` | None |
| Geometry + aligned OFF + aggregation | None | None | None | None |
| Geometry + original OFF + aggregation | `fresh017` | None | `fresh048` | None |
| neighbor9 reference | None | None | None | `fresh004`, `fresh018`, `fresh032`, `fresh046`, `fresh060`, `fresh067`, `fresh074`, `fresh081`, `fresh095`, `fresh102`, `fresh109`, `fresh110` |

### fresh: `joint_track_off_aggregate`

| Reference | Signal gains | Signal losses | Added leaking controls | Removed leaking controls |
|---|---|---|---|---|
| Centered combination | None | None | `fresh048` | None |
| Geometry + aligned OFF + aggregation | None | None | None | None |
| Geometry + original OFF + aggregation | `fresh017` | None | `fresh048` | None |
| neighbor9 reference | None | None | None | `fresh004`, `fresh018`, `fresh032`, `fresh046`, `fresh060`, `fresh067`, `fresh074`, `fresh081`, `fresh095`, `fresh102`, `fresh109`, `fresh110` |

### fresh: `joint_dual_off_aggregate`

| Reference | Signal gains | Signal losses | Added leaking controls | Removed leaking controls |
|---|---|---|---|---|
| Centered combination | None | None | `fresh048` | None |
| Geometry + aligned OFF + aggregation | None | None | None | None |
| Geometry + original OFF + aggregation | `fresh017` | None | `fresh048` | None |
| neighbor9 reference | None | None | None | `fresh004`, `fresh018`, `fresh032`, `fresh046`, `fresh060`, `fresh067`, `fresh074`, `fresh081`, `fresh095`, `fresh102`, `fresh109`, `fresh110` |
