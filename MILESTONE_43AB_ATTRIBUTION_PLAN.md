# M43AB: candidate-centered receiver attribution and ON/OFF agreement

This is a bounded development experiment following M43AA. Freeze this plan,
implementation, configuration, tests and all input specifications publicly before
scoring any M43AB case. Historical inputs are retrospective; new injection
combinations are prospective within the SAME existing observing sequence. Neither
group is independent observing coverage or a physical false-alarm calibration.

## Fixed endpoints

Retain all four M43Z policies unchanged as paired references. Three named new
endpoints share exactly the same retention, adjacent-OFF checks, receiver alias
identity partition, 20 Hz identity tolerance, 5.5 receiver floor and rank evidence:

1. `centered_receiver`: replace each unrestricted +/-100 Hz receiver maximum by
   the stationary native filtered score at the nearest-even native channel to
   the candidate's predicted scan midpoint. There is no fitted displacement,
   truth-based selection, new search radius or local maximization. This changes
   receiver attribution semantics, not an established arithmetic bug.
2. `centered_receiver_off_match`: also apply the existing width-aware OFF-window
   rejection only when the same epoch's ON/OFF centered response correlation is
   at least 0.8. Responses use the same template and width, no relative shift,
   radius max(1, floor(width/2)) proxy bins, float64 mean subtraction and cosine.
   Constant vectors have undefined correlation and cannot trigger this new veto.
   OFF strength must still reach 5.5 in the original OFF window. The 0.8 floor
   is an explicitly unvalidated development hypothesis, not a measured optimum.
   Earlier exact-coordinate OFF and retained-track vetoes are never relaxed.
3. `centered_receiver_off_match_aggregate`: add unchanged M43X remaining-epoch
   aggregation at 5.5 to endpoint 2. No global inter-epoch correlation cut.

No parameter is adjusted after scoring. Passing a selected development panel
does not authorize adoption. Fresh broader validation would still be required.

## Inputs and accounting

Historical panel: all 28 M43AA historical inputs, plus all eight original M43Z
leaking ON-OFF inputs (38,78,138,148,158,198,278,318): 36 total. This includes
both 170/171 and 280/281 mixed signal-loss pairs, the weak 260/261/265 family,
all three moderate-OFF losses and their signal-only/near/far counterparts,
residual controls 6/16/96, and case 96, the only M43Z pure-control input with
rank-eligible receiver-alias-vetoed members. These are observed alias-control
members, not a claim that the entire control's physical origin is known.

Fresh panel: 112 new native injection combinations at carriers 1536 and 2560,
crossing all four activity subsets and local templates 0/36. At each of these
16 strata, use the corresponding M43Z strength-24 source specification scaled
uniformly to strength 32. Include combined-unequal, mixed-unequal, distributed17,
distributed17-moderate-OFF, interferer-only, supported-spike, and ON-OFF. Preserve
relative offsets, component order and epoch ratios. No scores inform selection.
These give 64 signal-present and 48 pure-control inputs. Distinct native payload
inventories are counted separately from labels; repeated interferer payloads do
not become independent trials. Add one separately counted uninjected baseline.

Total: 149 base executions including baseline, each with seven paired policy
endpoints. Restore M43Z calibration exactly; no new null rows or threshold fit.
Any later fresh null rows must exclude all 1,792 previously used rows.

## Checks, costs and acceptance

Before scoring, verify all 96 source arrays and 48 native gathers. Reuse unchanged
M43W/X arithmetic certificates. At every input independently reconstruct the
first queried centered receiver sample for each epoch/width from raw normalized
rows plus declared profiles, preserving float32 addition/filter order. Require
exact agreement. Synthetic checks cover displacement contamination, centered
stationary interference, patch replacement, ON/OFF agreement and boundaries.

All 36 historical reference audits and all four M43Z policy decisions must replay
exactly; baseline must also replay. Preserve complete per-member new decisions,
receiver signatures and alias witnesses. Report every paired signal gain/loss,
added/removed leaking control, false truth association, and historical alias-veto
member that is released by the new endpoint. Association alone is not component
attribution; include fresh interferer-only counterparts explicitly.

For each new policy, require separately in historical and fresh panels: no loss
of reference-recovered signal cases; zero final members in each ON-OFF,
interferer-only and supported-spike input; no false control truth associations;
strictly fewer leaking controls. Require zero baseline survivors. Failure of any
condition fails the development gate. Original M43Z denominators 224/128 and
M43X failed gates stay unchanged; this selected panel cannot replace them.

Publish failures as well as gains. Production detector remains unchanged.
Owner's ongoing publication authorization applies. No delegation.
