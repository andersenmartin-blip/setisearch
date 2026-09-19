# Continue after LS8A

LS8A completed the first held-out transfer of the unchanged LS7X DEFAULT-L2
screen on the chronologically earliest public 55 Cnc visit after the March 2020
pilot.

## Audited result

- visit: `CH_PR100006_TG000301_V0300`, OBSID 1300462
- cadence: 44.220001 s
- rows: 1,178
- finite STATUS=0 rows: 1,135
- eligible 1/2/3-row windows: 1,911
- positive clusters at score >= +8.5: **0**
- negative-control screens at score <= -8.5: **4**
- maximum positive score: 6.775700
- minimum score: -10.602420
- independent audit: **PASS**, 9,555 numeric/discrete comparisons.

The method, DEFAULT aperture, cadence-unit durations, sidebands, guards,
eligibility rules, threshold and clustering were frozen before the table bytes
were opened.

## Interpretation

This is a useful held-out transfer result but not detector qualification.
The absence of positive clusters does not establish a low false-positive rate.
The four negative threshold crossings show that the local screening statistic
has extreme held-out tails that are not represented by a simple calibrated
Gaussian-significance interpretation.

Do not change the +/-8.5 threshold, noise estimator, sideband length or duration
set in response. Do not inspect another aperture to remove the negative controls.

## Next action

Before any further positive-event image follow-up or detector claim, apply the
same frozen cadence-unit screen to a small prospectively selected suite of
additional unused 55 Cnc visits. Selection must be deterministic from the
already saved archive metadata and fixed before their L2 table values are read.

Use both positive and negative threshold counts as control outputs. The suite
is a transfer/tail-behavior study, not a candidate search, and overlapping
windows must not be counted as independent observations.

[Protocol](LS8A_HELDOUT_L2_PROTOCOL.md)
[Result](results_ls8a_l2_transfer/REPORT.md)
[Audit](results_ls8a_l2_transfer/audit.json)
