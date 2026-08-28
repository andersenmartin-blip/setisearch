# Milestone 37 detector-v0.6 physical-reference phase-3 checkpoint

Status: **NON-FROZEN SYNTHETIC CHECKPOINT — ADJACENT-OFF AND RECEIVER-ALIAS
REFERENCE PASSED — PRODUCTION GATE BLOCKED — NO SPECTRAL ACCESS**.

This checkpoint extends the phase-2 retention/OFF/rank receipt through
complete synthetic single-adjacent-OFF evidence and receiver-frame alias
connected components. It was implemented and tested without opening,
requesting or inspecting an HD 156668 / HIP 84607 telescope spectral payload.
It is not a detector release, preregistration, search, completeness result,
null result or signal claim.

## Closed synthetic gates

- Dense-ancestry and sparse-ancestry inputs produce byte-identical adjacent-
  OFF evidence for all 160 retained ON records. The certificate covers all 24
  synthetic cache-oracle identities: eight widths by three paired OFF epochs.
- Among the 32 records that enter the adjacent stage without an earlier OFF
  veto, four take the inclusive `S/N >= 5.5` adjacent-OFF branch and 28 pass
  to receiver-alias evaluation.
- Receiver-alias output is byte-identical and independently reproduced from
  the phase-2 OFF annotations, complete adjacent evidence, exact receiver
  signatures and ON factor matrix.
- The identity partition contains five unique physical nodes, two connected
  components and five literal edges. At least one same-component node pair is
  farther apart than the inclusive 20-Hz edge tolerance, proving that the
  fixture exercises transitive connected-component closure.
- Receiver evidence contains 156 matched and four unmatched records. After
  frozen precedence is applied, all five final dispositions occur: 96 exact
  same-hypothesis OFF, 32 local-track OFF, four single-adjacent-OFF, 24
  receiver-frame alias and four still pending.
- The complete phase-3 receipt binds the pinned phase-2 receipt, ON retention
  product and OFF result. Claim expansion, adjacent mutation and alias
  mutation all fail closed.

## Known-answer identities

| Artifact | SHA-256 |
|---|---|
| Phase-2 ancestry receipt | `1d70d05ac7b7888cf8071bcbe894bd67bae24fba87636c6c17945b982cf0ca09` |
| Adjacent-OFF result | `5e14628984549016c459be03a9cbb00f5733c07bf31fe0c0a1db07aee6e6a0f7` |
| Receiver-signature product | `d41241af8c28ab818fef0f1ea63ca4242b2ea9413925f3144a0b40a0332c00bd` |
| Receiver-alias result | `369657f48115b8af63099ed8fc8accd18af540602be570cee78c94647a52b3bf` |
| Phase-3 receipt | `ef46ff54d69fdad918ca2d05d2c27896ae3ee53ecd0c2a20970003738d9a1f11` |

## Verification

| Check | Result |
|---|---|
| Targeted retention, replay, adjacent, alias, rank and core suite | 98 passed, 0 skipped, 0 failed |
| Full repository suite | 259 run, 258 passed, 1 expected benchmark skip, 0 failed |
| Offline wheel build and isolated phase-3 import | Passed; wheel SHA-256 `f06ca05aa02008c3ca1d0f6eb65de35721799525f7bf11f03c9b2ede47e29c73` |
| Dense/local adjacent result bytes | Identical |
| Dense/local receiver-alias result bytes | Identical |
| All width/paired-OFF cache-oracle identities present | 24 of 24 |
| Adjacent mutation | Rejected |
| Receiver-alias mutation | Rejected |
| Rehashed production-claim expansion | Rejected |
| HD 156668 spectral files contacted | No |
| Spectral dataset values read | No |

## Claim boundary and remaining blockers

This is a bounded synthetic reference, not a production replay. Its cache
entries are synthetic oracle identities; it does not assert that an M37 cache
was created or opened. The phase-2 dense-score oracle remains capped at
1,000,000 cells, so the M37 feasibility status remains
`mandatory-full-replay-benchmark-not-yet-passed` and the production wrapper
still hard-fails.

Adjacent-OFF and receiver-alias dependency coverage are now closed for the
synthetic reference. Production receipt ancestry, aggregate cache ownership
and the complete resource envelope remain mandatory. The streaming stages
must be integrated into the restartable runner, and the final runtime must be
pinned before a preregistration can be frozen.

The machine-readable checkpoint is
`results_m37_v0p6_physical_reference/progress.json`.
