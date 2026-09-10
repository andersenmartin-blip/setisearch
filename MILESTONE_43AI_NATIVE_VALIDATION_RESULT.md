# M43AI — prospective native result

The fixed combined rule failed the predeclared same-sequence native challenge. It recovered 53/64 signal cases and lost 0/53 signals required by the reference union. 1/48 controls and 0/128 native null cases had surviving members.

All 240 planned inputs are complete and audited. No threshold was changed after evaluation began. The detector is not adopted; no astronomical candidate or physical false-alarm probability is claimed.

## Complete accounting

| Panel | Cases | Signal recovery | Cases with non-signal survivors | Eligible members | Surviving members |
|---|---:|---:|---:|---:|---:|
| Injection/control panel | 112 (64 signals, 48 controls) | 53/64 | 1/48 | 5029 | 785 |
| Native null panel | 128 | Not applicable | 0/128 | 0 | 0 |

The required union is determined from the two references on these new inputs; its denominator is not the old 57 training cases.

All missed signals: `ai_validation002`, `ai_validation003`, `ai_validation009`, `ai_validation010`, `ai_validation022`, `ai_validation023`, `ai_validation024`, `ai_validation057`, `ai_validation093`, `ai_validation094`, `ai_validation101`.

Required signal losses: None.

Leaking controls: `ai_validation048`.

False control associations: None.

Signal cases with additional unassociated surviving members: `ai_validation015`, `ai_validation042`, `ai_validation043`, `ai_validation044`, `ai_validation045`, `ai_validation049`, `ai_validation050`, `ai_validation051`, `ai_validation052`, `ai_validation098`, `ai_validation099`, `ai_validation100`, `ai_validation105`, `ai_validation106`, `ai_validation107`, `ai_validation108`.

## Reference comparisons

| Reference | Recovered signals | Losses under combined rule | Gains under combined rule | Leaking reference controls |
|---|---:|---:|---:|---:|
| centered_receiver_off_match_aggregate | 53/64 | 0 | 0 | 4/48 |
| neighbor9 | 53/64 | 0 | 0 | 11/48 |

centered_receiver_off_match_aggregate losses: None.

centered_receiver_off_match_aggregate gains: None.

centered_receiver_off_match_aggregate control leaks removed: `ai_validation004`, `ai_validation018`, `ai_validation032`, `ai_validation046`.

centered_receiver_off_match_aggregate control leaks introduced: `ai_validation048`.

neighbor9 losses: None.

neighbor9 gains: None.

neighbor9 control leaks removed: `ai_validation004`, `ai_validation018`, `ai_validation032`, `ai_validation046`, `ai_validation060`, `ai_validation074`, `ai_validation081`, `ai_validation088`, `ai_validation095`, `ai_validation102`.

neighbor9 control leaks introduced: None.

## Predeclared gates

| Gate | Result |
|---|---|
| complete_native_evidence | Pass |
| fixed_public_model_before_evaluation | Pass |
| no_reference_signal_loss | Pass |
| zero_control_members | Fail |
| zero_false_control_associations | Pass |
| zero_native_null_members | Pass |
| zero_prior_native_payload_overlap | Pass |

## Surviving control members

| Case | Member | Raw second-epoch ON | Second-epoch excess | Accepting branch |
|---|---|---:|---:|---|
| ai_validation048 | `0c0b53cd894ee6fb83ec84526788bc0a78b0e8f93a260ff9d8da4fd3a1208b64` | 6.398906707763672 | 0.7406374111239558 | second_epoch_on |

## Signal and control strata

| Case type | Signal cases | Recovered | Required losses | Control cases | Leaking controls |
|---|---:|---:|---:|---:|---:|
| ON-OFF | 0 | 0 | 0 | 16 | 1 |
| combined-unequal | 16 | 16 | 0 | 0 | 0 |
| distributed17 | 16 | 12 | 0 | 0 | 0 |
| distributed17-moderate-OFF | 16 | 11 | 0 | 0 | 0 |
| interferer-only | 0 | 0 | 0 | 16 | 0 |
| mixed-unequal | 16 | 14 | 0 | 0 | 0 |
| supported-spike | 0 | 0 | 0 | 16 | 0 |

## Fixed method, provenance and checks

Protocol freeze: `cd69d0d7509fe09da7c8dcc201e797865776b4f9`. Exact public model: `e066f5016b2f4f7fed560b5ffc1e419a6b7138f3`. Both were fetched and verified before their respective selection/evaluation stages.

Model seal: `be8e8523410156a162b2bd0c0629b5d4cb2fe6d872ef41be2953b95f9c24f5de`. The unchanged member rule is R >=6.158954620361328 OR E >=4.034601211547852, conditional on original geometry/rank eligibility and complete profiles. R is second-largest active-epoch ON support; E is second-largest per-epoch ON-minus-nonnegative-OFF support. Both selected OFF-profile ceilings are unbounded.

All injection carriers moved by +211 channels and component strengths were multiplied by 15/16. The 128 null rows were fixed before scoring and excluded 2,048 prior/reserved shifts. The original held-out panels remain unopened.

The final audit verified 240 sealed records, 5029 eligible members, 21360 original profile-center references and 60764 recorded direct native checks. It independently rebuilt case decisions and headline gates and checked original reference endpoints. All 22 prepublication unit tests passed. Frozen public file hashes were rechecked after runtime recovery.

There are 232 distinct native payloads among 240 labelled cases; 8 within-panel duplicate payloads are disclosed in final_audit.json. These are not 240 independent noise realizations.

The runtime connection failed after 100 completed null records. On recovery, no worker remained. The unchanged runner verified and reused those records and evaluated only the missing inputs. Earlier saved records remain byte-identical.

This is one observing sequence and a deliberately nearby signal challenge. Empty native-null retained sets provide no conditional profile-tail measurements. General adoption requires independent observing data. The selected model fails this endpoint and must not be retuned on these outcomes.

## Files and continuation

Complete original records, endpoint tables, inventory hashes, summary, reference-control accounting and final audit accompany this report. The saved ZIP manifest binds every original file; ZIP extraction was compared byte-for-byte. Post-execution audit command:

```bash
PYTHONPATH=src:scripts python scripts/m43ai_result_audit.py
```

The owner explicitly approved the prepared M43AI result package and main README update after the earlier automatic-review rejection. The complete original records are distributed in a lossless archive, with every original size and SHA256 retained in its manifest. [Restoration instructions](results_m43ai_native_archive/README.md). Earlier scientific files, M33 HD 3651, the LS track and the separately pending M43AF complete archive are preserved.
