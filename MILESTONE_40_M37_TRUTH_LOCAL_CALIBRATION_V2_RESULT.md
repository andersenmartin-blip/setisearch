# Milestone 40 v2 conditional truth-local calibration result

Status: **COMPLETE — 6,144 / 6,144 COVERAGE-REPAIRED TRIALS; NO
RECOVERY TRANSITION IN THE FROZEN S/N GRID**.

## Result

Milestone 40 v2 completed the separately frozen corrective execution after
the immutable v1 native-coverage abort. All 512 repaired continuous truths
were evaluated at all 12 exact ideal single-epoch S/N levels. Every trial
remained inside the common native-safe carrier interval, and the aggregate
validated exactly 6,144 unique canonical receipts with no missing or extra
record.

No trial reached the frozen operational truth-local score threshold of
126.20158386230469. The maximum finite truth-local score increased from
10.841727256774902 at injected S/N 4 to 70.08597564697266 at injected S/N 40,
but the predeclared grid therefore did not bracket a recovery transition.

| Ideal single-epoch S/N | Trials | Finite best scores | Maximum best score | Recovered | Recovery fraction | Wilson 95% interval |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 512 | 68 | 10.841727256774902 | 0 | 0 | [0, 0.0074469757] |
| 5 | 512 | 76 | 11.017040252685547 | 0 | 0 | [0, 0.0074469757] |
| 6 | 512 | 85 | 12.620399475097656 | 0 | 0 | [0, 0.0074469757] |
| 7 | 512 | 92 | 15.040443420410156 | 0 | 0 | [0, 0.0074469757] |
| 8 | 512 | 92 | 16.015438079833984 | 0 | 0 | [0, 0.0074469757] |
| 10 | 512 | 90 | 19.19729232788086 | 0 | 0 | [0, 0.0074469757] |
| 12 | 512 | 82 | 23.26470184326172 | 0 | 0 | [0, 0.0074469757] |
| 16 | 512 | 69 | 29.36761474609375 | 0 | 0 | [0, 0.0074469757] |
| 20 | 512 | 59 | 36.77976608276367 | 0 | 0 | [0, 0.0074469757] |
| 24 | 512 | 56 | 43.92475891113281 | 0 | 0 | [0, 0.0074469757] |
| 32 | 512 | 51 | 56.2032585144043 | 0 | 0 | [0, 0.0074469757] |
| 40 | 512 | 49 | 70.08597564697266 | 0 | 0 | [0, 0.0074469757] |

The finite-score count records trials for which the truth-local adapter found
a finite candidate score after the frozen two-pass mask. A missing finite
score is a valid no-recovery outcome, not a missing trial.

## Execution and lineage checks

| Check | Result |
|---|---|
| Coverage-repaired trial inventory | Passed (6,144 / 6,144) |
| Per-level inventory | Passed (512 at each of 12 levels) |
| Common native-safe allocation | Passed |
| Canonical record identities | Passed |
| Missing or extra receipts | None |
| V1 score receipts adopted | 0 |
| Frozen threshold changed after injection | No |
| M39-qualified adapter and source ancestry | Preserved |

The 156 diagnostic v1 receipts remain outside this result. V2 changed only
the prospective carrier allocation described by the coverage-repair plan; it
did not change motions, widths, activity subsets, S/N levels, randomized
background construction, mask, threshold, adapter, or endpoint.

The complete local regression suite ran 349 tests with no failures and one
expected exact-grid benchmark skip.

## Reproducible certificate

The compact result is published in
`results_m40_m37_truth_local_calibration_v2/`. The deterministic gzip ledger
contains the 6,144 canonical trial records in plan order.

| Item | SHA-256 |
|---|---|
| Aggregate identity | `03e162aea769c2020df6509171217dbf32624e69b4a3ccad4ae159c85836f974` |
| Aggregate file | `c8db65c5bf4489a291b67a52ef716347e92e3a9a6ed59af166dbfd06f904a708` |
| Trial ledger | `127a3ed5babcdd36385fe1d8cce1a2339b1702511820848c7103aab5a45fd22c` |
| Trial-record inventory | `dc01e176eb6414436ba151f366d4cdea072fd1feb2d1145a811eab960032ce37` |
| V2 start identity | `a0c81a88563fa55c15d123cc3de087abe71a23a78252f2f042e652f24c7dee92` |
| V2 start file | `1d1c8627fb7fbb7fe0e1bc8a5ac2228de6778645561b2e87460b29dad3bfe69a` |

## Claim boundary and next decision

This is a complete pointwise conditional truth-local score-recovery result
for the frozen randomized M37 background model. It is not end-to-end detector
completeness. No interpolation, physical-veto survival, global false-positive
field, sensitivity transport, occurrence-rate constraint, or technosignature
claim follows from M40 v2.

Because the highest tested S/N remains below the operational score threshold,
M40 v2 does not estimate a 50% recovery point or any other transition. A
future extension would require a new, separately frozen protocol with a
higher S/N range; the completed M40 result must remain unchanged.
