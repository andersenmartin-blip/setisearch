# Milestone 39 M37 truth-local qualification checkpoint

Status: **STARTED — FACTOR ANCESTRY VERIFIED; SOURCE/CACHE REHYDRATION AND
REAL-ANCHOR EQUIVALENCE PENDING**.

## Completed in this checkpoint

M39 now has a hash-frozen, resource-bounded truth-local planner and score
adapter. The focused known-answer tests show that its interval planner matches
the older materialized reference, including tolerance boundaries, and that its
local mask/score path is bit-identical to a dense synthetic replay. Changed
source ancestry fails closed.

The checkpoint reopened the compact M37 Run 006 factor bundle against its
independent file, manifest, table, basis, label, analysis-contract, and
source-metadata identities. The 93-by-48 ON factor matrix has SHA-256
`6e53ac8fb786e6598f8798aa829d51ffa55edda005c27262d6a1d8d6c9ab001b`.

Three real-M37 anchors are frozen. Factor-only planning yields respectively
0, 2, and 11 truth-local carrier cells. The zero-cell first anchor is retained
as an explicit structural boundary case; it must reproduce an exhaustive
zero-result exactly rather than being silently dropped.

## Gate status

| Gate | Status |
|---|---|
| Compact factor ancestry | Passed |
| Adapter source and checkpoint schema freeze | Passed |
| Six source products and 48 cache sidecars present | Pending (0 / 6, 0 / 48) |
| Restartable real-anchor runner | Pending |
| Exhaustive real-M37 anchor equivalence | Pending (0 / 3 executed) |
| 6,144 calibration trials authorized | No |

No spectral value was read by this checkpoint, no injection was executed, and
no completeness, sensitivity, physical-veto survival, global false-positive,
occurrence-rate, or technosignature claim is made.

## Reproducible certificate

The deterministic record is
`results_m39_m37_truth_local_qualification/qualification.json`.

| Item | SHA-256 |
|---|---|
| Qualification certificate | `1f9aaed8ee1d63dd4db1910b9a9fb93fb1e8a4526e125d7ec78cb52f7d1155d1` |
| Configuration | `965bfe00d0a5d586ca3173e436e23fab3490831d601eb8db3222fe625b9ed48d` |
| Input inventory | `c18004044fe1b16b0cef7064433dae19dac5a9930ecb218fe639d9b9111d9d35` |
| Anchor-plan inventory | `531933a5f325d205d8997d2263daa11c2a427b9f5d114ce9b3a3406d261da107` |

The complete local regression suite passed 322 tests with zero failures and
one expected exact-grid benchmark skip.

The next stage is an explicitly authorized, restartable rehydration of only
the frozen 1412.5 MHz products and caches, followed by the three predeclared
exhaustive anchor comparisons. The calibration ledger remains closed until
all of those comparisons pass.
