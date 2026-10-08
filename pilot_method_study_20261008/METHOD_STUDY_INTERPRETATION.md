# Scientific interpretation of the completed 64-cell method study

All 64 prespecified synthetic cells completed with valid outcome metadata. The fixed method recovered every active ON in 52/64 cells and at least one active ON in 59/64. All results are synthetic; telescope power remains unopened. The study is exploratory, was designed after B’s observed losses, and cannot qualify a sky pilot or reverse A/B’s failed decisions.

| Declared ideal level | ALL active ONs recovered | ANY active ON recovered |
|---|---:|---:|
|10|6/16|12/16|
|12|14/16|15/16|
|16|16/16|16/16|
|24|16/16|16/16|

The 12 cells lacking ALL recovery contain 13 missed active scans. Every miss has zero ON threshold carriers and a retained global ON maximum below 10. Eleven missed scans occur at declared level 10 and two at level 12. Across 128 active scans, 115 have localized survivors and 13 miss at the ON threshold. No active-scan recovery is lost through localization or OFF matching. All 7051 retained raw ON threshold carriers survive OFF in these signal-only cells; these are correlated responses across nearby carrier templates, not 7051 independent candidate objects.

At level 12, `method_signal:027` is third ON only, drift −1.25 Hz/s, intrinsic width 3, interior placement 3070.75; its ON maximum is 9.630510667. `method_signal:030` is active in all three ONs, drift +4 Hz/s, intrinsic width 3, interior 1024.25; the first ON maximum 9.956024861 misses while the second and third recover. This repeats the observed stage of B’s operating:019/021/045 failures: the loss occurs before OFF, with a declared ideal level 12 that does not guarantee a measured detector response above 10. Success in every observed cell at levels 16 and 24 describes these 32 cells only; it does not establish a universal boundary.

| Descriptive group | ALL recovery | ANY recovery |
|---|---:|---:|
|Drift −4 Hz/s|14/16|16/16|
|Drift −1.25 Hz/s|12/16|14/16|
|Drift +1.25 Hz/s|12/16|14/16|
|Drift +4 Hz/s|14/16|15/16|
|Intrinsic width 1|27/32|30/32|
|Intrinsic width 3|25/32|29/32|
|Third ON only `[4]`|27/32|27/32|
|All three ONs `[0,2,4]`|25/32|32/32|
|Native offset 0.25|14/16|15/16|
|Native offset 4094.75|14/16|15/16|
|Native offset 1024.25|12/16|15/16|
|Native offset 3070.75|12/16|14/16|

The two edge blocks have 14/16 ALL recoveries each, while the two interior blocks have 12/16 each; this grid provides no observed edge deficit. The ±1.25 drift groups and intrinsic width 3 have fewer ALL recoveries than their counterparts, but the counts do not establish effects or significance. Each factor cell has one seed and one placement. The balanced placement assignment removes marginal width/activity confounding while leaving placement deterministic and unreplicated within a cell.

Activity changes the recovery question. At declared level 10, third ON only cells recover 4/8; all-three cells recover ALL 2/8 and ANY 8/8. At level 12, third ON only cells recover 7/8; all-three cells recover ALL 7/8 and ANY 8/8. At levels 16 and 24, both activity patterns recover 8/8 ALL and ANY. ALL across three scans imposes three requirements; ANY gives three chances. These independent-noise, differently blocked activity contrasts cannot establish a causal benefit from repeated visits. Per-ON recovery is 28/32 first ON, 31/32 second ON and 56/64 third ON; third ON is active in every cell, while the others are active in half. Those unequal populations and the small unreplicated design prevent a causal last-visit-bias claim.

Completed B supplies the complementary filter evidence. All 142 cases have complete integrity outcomes, but B fails its fixed science gates: operating ALL 45/48 and ANY 46/48 include third ON only 6/8 against required 7, and intrinsic width 3 recovers 21/24 against required 22. All 24 matched-RFI cases first detect localized signal in all three ONs and reject the true localized RFI, yet two cadences leak 14 nonlocalized first ON carriers. Their width 33, off-truth drift geometry is consistent with bright smeared-RFI aliases; this is a geometric inference documented in the motivating-evidence report, not a new counterfactual experiment. The zero-ANY-survivor interference gate fails.

B’s 32 fresh noise cadences are empty. This finite synthetic family does not calibrate sky false-alarm probabilities. All 12 single-row transient diagnostics survive, so a large summed track statistic alone does not establish persistence. For nearby-OFF contamination, 11/12 signals are initially localized and none remain after OFF; all 11 initially detected signals are rejected, while the twelfth was already missed before OFF. The conservative filter therefore has a measured sensitivity cost around nearby interference. The new signal-only grid adds no independent interference or null qualification.

The nominal ideal level is the original noiseless unfiltered box projection under Gamma16 with raw sigma 0.25. It is neither measured detector SNR nor flux. There is one realization per heterogeneous cell; scan outcomes within a cell are not additional independent cell replicates. Present discrete outcomes and valid denominators, without a fitted efficiency curve, confidence-calibrated recovery boundary, sky sensitivity claim or false-alarm claim. New identities make the draws disjoint; selecting this study after B makes its interpretation exploratory.

Proposals for a future authorized plan, with no implementation in this study:

1. Compare a tightly bounded set of fresh development methods that account for integration smearing and measure sensitivity after preprocessing. Freeze the comparison and its resource budget before draws; preserve the current threshold misses as historical evidence.
2. Represent and inspect ON candidate families or fitted tracks before OFF propagation, retain every raw hit, and evaluate path uncertainty against both bright smeared-RFI alias leakage and nearby-OFF false rejection on new controls. No wider tolerance or lower threshold is justified by these counts alone.
3. Add explicit time-occupancy and morphology evidence with separate persistent-track and transient labels, preserving one-ON and burst events for inspection.
4. Freeze a new claim and disjoint qualification with repeated seeds near levels 10/12/16, physically crossed placements and prespecified drift/width/activity/mask subgroups, matched interference and nulls. Keep ALL and ANY separate, and require complete output/resource integrity before a telescope pilot.

The method resource receipt reports all children reaped, 5387.471679 child CPU seconds plus 19.750352 controller CPU seconds, and passage of the local 6000-second allocation. Root’s whole-period resource reconciliation and the independent retained-output audit are separate. This interpretation changes no frozen inputs, protocols, workers, claims, thresholds or budgets. There is no second correction and no sky admission.
