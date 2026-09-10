# M43AI — fixed combined model selected; native test not yet opened

The predeclared combination meets the closed training requirements: **57/57
required signals recovered, zero surviving members in the 48 controls, one
baseline and 128 native nulls.** It recovers 57 of all 64 signal cases. The
seven others remain explicit failures. This known-case coverage was expected
from M43AH's disjoint loss lists and is not independent validation.

The [protocol and executable preparation](MILESTONE_43AI_COMBINED_RULE_PROTOCOL.md)
were published and independently fetched at
[`cd69d0d`](https://github.com/andersenmartin-blip/setisearch/commit/cd69d0d7509fe09da7c8dcc201e797865776b4f9)
before the model was selected. No proposed native validation input has yet been
evaluated. The trained model must itself be published and verified before that
gate can open.

## Exact selected rule

| Feature | Inclusive lower bound | Strict OFF-profile upper bound | M43AH source state |
|---|---:|---|---:|
| Second-epoch ON support R | 6.158954620361328 | Unbounded | 171 |
| Second-epoch ON-minus-OFF support E | 4.034601211547852 | Unbounded | 316 |

These are the first zero-leak minimum-loss states in each frozen descending-ON
ledger. Because both OFF-profile ceilings are unbounded, the selected rule
simplifies to R >= 6.158954620361328 OR E >= 4.034601211547852, conditional on
the unchanged geometry/rank eligibility and complete measurements. E still
includes the fixed per-epoch OFF-center penalty. No detector decisions use
injection truth or the signal/control label.

The model seal is
`be8e8523410156a162b2bd0c0629b5d4cb2fe6d872ef41be2953b95f9c24f5de`.
The configuration SHA256 is
`9994511c34320560c0a1f580a85ffa0a33f32d0bfc3094e41abf2d4876fdbc4f`.

## Complete training accounting

- 241 original input records and 3,497 eligible members checked.
- 57/64 signal cases recovered; no losses against neighbor9 (57) or the
  centered reference (54). Gains over the latter: training057/071/085.
- Missing signals: training001/015/029/037/038/052/078, all outside the fixed
  57-case requirement and still included in the all-signal denominator.
- Zero control, baseline or native-null leaks and zero false control associations.
- 759 surviving member rows; these are correlated representations, not 759
  independent signals. Fifteen signal cases have additional unassociated
  survivors, listed in the full ledger; these are not astronomical candidates.
- An independent scalar reduction checks every member/case outcome. The union
  of the two published single-family recovery sets independently agrees.

The native nulls and baseline in this training archive have no eligible members.
They do not establish a physical false-alarm probability. All evidence is from
one observing sequence. No new detector is adopted.

## Next: fixed prospective native challenge

The frozen configuration specifies 112 new injection/control cases (64 signals,
48 controls), plus 128 new native translations disjoint from 2,048 prior or
reserved rows. Carrier locations shift by 211 channels and all strengths are
scaled by 15/16. No old held-out native inputs are opened. The new panel must
preserve both references' signal recovery, reject every control/null member and
pass all source, identity, completeness and independent arithmetic checks.

The six saved native sources, 96 original arrays, 48 gathers, calibration
binding and 432 direct native calculations were restored and verified.
The preparation's numeric measurements and hashes match already public
M43AF/M43P evidence; [the provenance comparison](results_m43ai_preparation/public_value_provenance.json)
records that verification. All 22 new unit tests pass.

- [Exact model](results_m43ai_combined_rule/model.json)
- [Every training endpoint and member decision](results_m43ai_combined_rule/training_endpoints.json)
- [Training summary](results_m43ai_combined_rule/training_summary.json)
- [Training hashes](results_m43ai_combined_rule/training_manifest.json)

Continue from [PROJECT_STATUS.md](PROJECT_STATUS.md). General adoption still
requires an independent observing sequence. The historical M43AF archive,
M33 HD 3651 follow-up and LS track remain separate continuation items.
