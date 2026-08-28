# Milestone 37 detector-v0.6 physical resource-envelope checkpoint

Status: **NON-FROZEN SYNTHETIC CHECKPOINT — AGGREGATE PHYSICAL-EVIDENCE
RESOURCE ENVELOPE PASSED — PRODUCTION GATE BLOCKED — NO SPECTRAL ACCESS**.

This checkpoint integrates the width-streaming receiver-frame and single-
adjacent-OFF stages in one strict sequential executor. It was implemented and
tested without opening, requesting or inspecting an HD 156668 / HIP 84607
telescope spectral payload. It is not a detector release, preregistration,
search, completeness result, null result or signal claim.

## Closed bounded gates

- Width-stream resource receipts now carry the exact source, cache-plan,
  cache-manifest, cache-payload, path and payload-byte receipt for every
  opened width-by-scan cache. Schema version 2 revalidates those identities,
  exact ordering, canonical paths, uniqueness and byte totals.
- The physical-evidence executor runs receiver-frame measurement first,
  seals it only after all ON handles close, and only then opens the paired OFF
  stream. Both streams become permanently sealed before the aggregate receipt
  exists.
- The aggregate receipt requires one run ID, window, cache-run manifest,
  cache inventory, factor bundle, ON-retention certificate, ON-record
  inventory, factor contract, width inventory and mapped-byte cap.
- Receiver and adjacent evidence cache identities must exactly equal the
  caches recorded by their respective streams. The receipt binds the complete
  receiver result and adjacent evidence identities, both evidence-certificate
  identities and both stream-certificate identities.
- Because the stages are serialized, the aggregate mapped-byte peak is the
  maximum of their measured peaks rather than their sum. The generic executor
  records this ownership; the M37 validator additionally freezes all eight
  widths, six scan labels, the M37 factor identities and the 536,870,912-byte
  cap.
- Independently rehashed run mixing, cache-receipt mutation, wrong root
  identity and expansion of the synthetic receipt into an M37 claim all fail
  closed.

## Synthetic known answers

The end-to-end fixture publishes six real read-only native-cache files, opens
them through the run manifest and memory-mapped arenas, builds both evidence
products, closes every handle and seals the aggregate receipt.

| Artifact | SHA-256 |
|---|---|
| Physical resource envelope | `f64d93cdb027d09ca6486bd533b48990b11c16451fc5c8b2b57c89bd4e898191` |
| Complete execution result | `6d323d2142bfc195514ccd8955331d8e30f2175f37fa8b26324baf89b9e919e7` |
| Receiver cache identity inventory | `80db329e7330d6aa57cb099f279f635bae145d96374a2343f6b3a8fc2e94ac81` |
| Adjacent-OFF cache identity inventory | `ce89d8ff81e8329bc28c8154c189614e7725645eb658b733da1e72d50c7ec266` |
| Offline wheel | `235060e1e81a813a95f9b673d0644a8339f829d0c930a501022f444bf3f4b183` |

The fixture opens two one-width batches and six cache handles in total. Its
measured aggregate peak is 81,600 mapped bytes and three simultaneous
handles. This small number is a synthetic contract test, not a projection of
the M37 production working set.

## Verification

| Check | Result |
|---|---|
| Targeted cache-stream, receiver, adjacent and aggregate suite | 27 passed, 0 skipped, 0 failed |
| Full repository suite | 263 run, 262 passed, 1 expected benchmark skip, 0 failed |
| Offline wheel build and isolated import | Passed |
| Receiver closes before adjacent opens | Enforced by the executor and receipt |
| Evidence cache receipts equal stream cache receipts | Exact match |
| Rehashed cross-run or cache mutation | Rejected |
| Synthetic-to-M37 claim expansion | Rejected |
| HD 156668 spectral files contacted | No |
| Spectral dataset values read | No |

## Claim boundary and remaining blockers

This closes the aggregate resource envelope only for the two physical-
evidence streaming stages, using a bounded synthetic run. It does not prove
production receipt ancestry, the complete primary-search or completeness
working-set envelope, or the full restartable production lifecycle. No M37
cache exists because authorized extraction has not occurred.

The phase-3 sparse reference and this real-cache streaming fixture exercise
complementary contracts: phase 3 covers all final physical-disposition
branches, while this checkpoint proves actual cache ownership and sequential
closure for receiver and adjacent evidence. They are not yet one production
receipt chain. Completeness feasibility, production runner persistence and
the final pinned runtime remain blocked.

The machine-readable checkpoint is
`results_m37_v0p6_resource_envelope/progress.json`.
