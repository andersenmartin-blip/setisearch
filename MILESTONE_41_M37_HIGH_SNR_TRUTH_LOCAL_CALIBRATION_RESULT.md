# Milestone 41 M37 higher-S/N truth-local calibration result

Status: **COMPLETE — 6,144 / 6,144 HIGH-S/N TRIALS; FIRST POINTWISE
RECOVERY AT S/N 72; NO 50% RECOVERY TRANSITION**.

## Result

Milestone 41 completed the separately frozen post-M40 higher-S/N extension.
All 512 coverage-repaired M40 v2 truths were evaluated, without selection or
relocation, at all 12 exact ideal single-epoch S/N levels. Every trial used a
new M41 trial identity and independently derived randomized background. The
aggregate validated exactly 6,144 unique canonical receipts with no missing
or extra record and adopted no M40 score receipt.

The first tested level with any recovery at the unchanged operational
truth-local score threshold of 126.20158386230469 was S/N 72, with 2 of 512
truths recovered. Recovery remained sparse throughout the extension: the
largest observed pointwise recovery fraction was 46 of 512, or 8.984375%, at
S/N 192 and S/N 256. The frozen levels therefore do not bracket either a 50%
or a 90% pointwise recovery transition, and no interpolation was performed.

| Ideal single-epoch S/N | Trials | Finite best scores | Maximum best score | Recovered | Recovery fraction | Wilson 95% interval |
|---:|---:|---:|---:|---:|---:|---:|
| 48 | 512 | 52 | 84.91242980957031 | 0 | 0 | [0, 0.0074469757] |
| 56 | 512 | 48 | 98.45069885253906 | 0 | 0 | [0, 0.0074469757] |
| 64 | 512 | 51 | 113.10334014892578 | 0 | 0 | [0, 0.0074469757] |
| 72 | 512 | 49 | 128.57357788085938 | 2 | 0.00390625 | [0.0010718891, 0.0141294071] |
| 80 | 512 | 48 | 141.8671112060547 | 7 | 0.013671875 | [0.0066380970, 0.0279490005] |
| 88 | 512 | 46 | 155.03990173339844 | 11 | 0.021484375 | [0.0120380750, 0.0380576635] |
| 96 | 512 | 44 | 168.3516387939453 | 27 | 0.052734375 | [0.0364923058, 0.0756379967] |
| 112 | 512 | 50 | 193.7136688232422 | 37 | 0.072265625 | [0.0528807028, 0.0980212022] |
| 128 | 512 | 45 | 220.50503540039062 | 40 | 0.078125 | [0.0578955038, 0.1046378820] |
| 160 | 512 | 44 | 277.7625427246094 | 43 | 0.083984375 | [0.0629473705, 0.1112174960] |
| 192 | 512 | 49 | 334.6981201171875 | 46 | 0.08984375 | [0.0680328868, 0.1177634605] |
| 256 | 512 | 49 | 441.6459045410156 | 46 | 0.08984375 | [0.0680328868, 0.1177634605] |

The finite-score count records trials for which the truth-local adapter
returned a finite best score after the frozen two-pass mask. A missing finite
score is a valid no-recovery outcome, not a missing trial. Each level had 98
truths with at least one truth-local candidate-score cell before the adapter's
final finite-best-score selection.

## Execution and lineage checks

| Check | Result |
|---|---|
| Trial inventory | Passed (6,144 / 6,144) |
| Per-level inventory | Passed (512 at each of 12 levels) |
| Reused M40 v2 truth inventory | Passed (512 / 512; no selection or relocation) |
| New M41 trial and background identities | Passed |
| Canonical record identities | Passed |
| Missing or extra receipts | None |
| M40 score receipts adopted | 0 |
| Frozen threshold changed after injection | No |
| M39-qualified adapter and source ancestry | Preserved |

The operational restart checkpoints are execution-continuity artifacts, not
partial calibration curves. Only the complete 6,144-record aggregate supports
the result above.

The complete local regression suite ran 358 tests with no failures and two
expected skips: the rehydrated-execution-root coverage witness and the exact
M37 kernel benchmark.

## Reproducible certificate

The compact result is published in
`results_m41_m37_high_snr_truth_local_calibration/`. The deterministic gzip
ledger contains the 6,144 canonical trial records in frozen plan order. For
transport through the publication interface, its unchanged 3,318,065 bytes
are stored as seven parts described by `trial-ledger.parts.json`; concatenating
those parts in listed order reconstructs `trial-ledger.jsonl.gz` exactly.

| Item | SHA-256 |
|---|---|
| Aggregate identity | `b95220e51b02636a45d0a9e322bdc879fa47bad79f03d0577eb2566382b6f8c9` |
| Aggregate file | `2564733b8c93b935e090861028fe6a6b622f70e9e7066bde81e4c083c95ca43d` |
| Trial ledger | `429789c591f44cb1ea87a5b340bf79a72905b44af3aa71bef964b3d002cc50fb` |
| Ledger transport manifest | `a6c4989d76a3ee5de16ff82332720e1bc9d8c4f55be3fe3ae9e7badb4e89917b` |
| Trial-record inventory | `b2ddeb5a4c1e5b06a52be946fafa0bb370946d804fb1301e1fbe491b1f40801d` |
| M41 start identity | `f2b9198cf25df9503e2f53ed99ab3098ddbb8e7af0689206d143cfd97276facd` |
| M41 start file | `8b131b170a6e45f441aebcb833a20f7652d6b6a2c72fffbbd1dd2ff7795fed5c` |

## Claim boundary and next decision

This is a complete pointwise conditional truth-local score-recovery result
for the frozen randomized M37 background model. It is not end-to-end detector
completeness. No physical-veto survival, global false-positive-field replay,
sensitivity transport, occurrence-rate constraint, or technosignature claim
follows from M41.

The sparse plateau at the two highest tested levels is evidence that simply
extending S/N again is not yet justified. A separate prospective diagnostic
should first determine which frozen truth/support or mask classes can produce
a finite score and why most do not. That interpretation is a next-step
hypothesis, not an additional M41 result; M41 itself remains pointwise-only
and does not permit interpolation.
