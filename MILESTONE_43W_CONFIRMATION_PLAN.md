# M43W: prospective additive OFF and active-epoch confirmation controls

M43V identified remaining OFF-threshold responses, displaced weak support that
unmasks an isolated spike, and an interferer-only false truth association.
This experiment fixes two additional rejection predicates before evaluating
new combinations. The original neighbor9 path remains the common reference.

## Fixed rules and computation sharing

Four named endpoints: `neighbor9`, `off_window`, `epoch_confirmation`, `combined`.
All use the unchanged M43U neighbor9 masks, scoring, retention, original OFF and
receiver/alias vetoes, and rank calculation. The two new predicates apply AFTER
those stages; no upstream members, alias witnesses or calibration masks are removed.

1. OFF-window rejection: for each retained ON member, gather the same template
   and filter width in each active paired OFF epoch. Reject if any score is
   >=5.5 within inclusive proxy-carrier offsets `[-width//2,+width//2]`. Use the
   original full-support vectors, including guards. Incomplete support fails
   closed; no clipping or wrapping. The radius is explicitly defined in proxy
   bins, not a claim of exact native frequency-response equivalence. Width one
   reduces to the existing same-coordinate OFF test.
2. Active confirmation: require EVERY declared active ON epoch at the retained
   coordinate and width to have score >=5.5. This adopts the already used
   single-epoch confirmation floor instead of the weaker >=3 support floor.
   It may sacrifice faint or variable signals; the trial measures that cost.

The original 5.5 floor is not tuned to the three exposed M43V OFF values.
`off_window` applies only rule1, `epoch_confirmation` only rule2, `combined`
both. Every final alternative set must be a subset of the reference. One base
detector execution supplies all four endpoint decisions for each input. These
are four paired policies, not four independent executions or data realizations.

## Source, anchor and calibration qualification

Retain the 37-template, 4,097-score-carrier central pilot, eight filter widths
and three ON/OFF pairs in one existing observing sequence. Reverify all 96
original arrays and all 48 native ON/OFF gather anchors. Before calibration,
compare every new OFF-window maximum against separate scalar loops at five
fixed score positions (0,1,2048,4095,4096), every template, width and epoch:
4,440 real-data comparisons, including both score-grid edges. Reuse unchanged
detector numerical evidence; run focused boundary and four-policy tests.

Freeze 128 new training and 128 separate held-out shift rows with seed430023,
excluding all 1,024 prior R/T/U rows; V reused U and adds no new rows. Use the
existing mask-estimation/crop/co-roll scheme and >=3 pre-veto global maxima.
Threshold is max(10,training maximum), sealed before held-out and injection
evaluation. All four endpoints share this conservative pre-veto certificate:
the new cuts only remove members, so no lowered threshold or claimed gain in
noise sensitivity is allowed. Held-out results remain correlated, pre-veto
within-sequence evidence; no independent physical FAP or calibrated OFF false
rejection probability follows. No new telescope requests are planned.

## New fixed panel

Two new injection centers, score indices768 and3328, fully crossed with all
four activity subsets and the same two anchor templates (local0 and36).
These 16 strata each use strengths12 and32, with SIX input types:

- nearest native-bin signal;
- combined-profile signal (inherited coefficient offset,+0.5 proxy bin,
  one-native-channel smear and finite sinc-squared profile);
- that combined signal plus a strength4S nearest-bin component12 bins away
  in the first active epoch;
- the exact same strength4S component alone, with the absent combined truth
  retained ONLY as a false-association reference;
- strengthS at the anchor in the first active epoch plus strengthS/8 power
  six bins away in the other active epochs;
- matching nearest-bin strengthS ON and OFF injections in all active epochs.

Total:192 distinct native inputs,192 base detector executions,768 paired
policy endpoints. Of the inputs,96 contain intended signals and96 are pure
controls.32 interferer-only inputs test false association with an absent truth;
32 ON-OFF inputs test the specific control failure. One uninjected baseline
execution/four endpoints is separate. Both components of each mixed input have
matched single-component inputs. Complete additions occur in declared float32
order before native filtering/gathering. Metadata geometry must satisfy the
unchanged <=20Hz center-track association before the public freeze; abort if
any preselected combination lacks support. No score-based substitutions.

## Predeclared development decision

For each alternative versus the reference require ALL:

- no paired loss of an associated final member in any of96 signal-present cases;
- no increase in the number of pure-control cases with any final member;
- zero final members in all32 ON-OFF cases;
- zero absent-truth associations in all32 interferer-only cases;
- zero held-out pre-veto maxima at or above the shared threshold.

Also report member counts, every gained/lost case, conditional signal-only versus
mixed outcomes and false associations. Subset monotonicity makes nonincrease
of control leakage automatic; it cannot establish qualification alone. A pass
only permits broader validation. A fail is retained, without threshold tuning,
post-hoc gate weakening or repeating this panel as independent confirmation.

This panel adds carrier/activity combinations and a two-level strength comparison,
not observations, full-bank completeness, arbitrary variability or independent
astronomical trials. Exposed M43V cases35/44/61/69 are not counted in the new
panel. Preserve all earlier milestones and both M43T branch histories.

Publish config, implementation, tests and this plan before scoring. Persist one
sealed checkpoint per full four-policy input. Restart only matching freeze,
config, input, common calibration binding and exact input identities. No partial
panel may support a final development verdict. Publish failures and all logs.
