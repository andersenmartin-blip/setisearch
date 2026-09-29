# Bounded physical evidence — closed storage qualification

The local checkpoint store passes its two fixed byte-only fixtures. All 22
serialization views of the previously failed native report restore exactly;
their cumulative charged case size is **17,391,433 bytes**, below 24 MiB
(25,165,824 bytes). The historical physical status remains FAILED. This storage
result neither reruns nor changes the closed native-chain experiment.

## Exact work and results

The [scope](RADIO_PHYSICAL_EVIDENCE_2026-09-29_SCOPE.md) fixes the original
14,979,354-byte report from public commit
`43fa09b11c0586c47538d2a8ebfc6060e3d5248e`, SHA256
`6a205b43d53f0a582d73d6d88c1501a0d4d8cd992a974dc8ff6328d300296dfd`.
Its retained rows define 22 deterministic serialization views. Intermediate
views are constructed storage fixtures, not historically captured time points.
Every view's hash and length, code version and reservation were fixed before
creating the exclusive stores. Seven original case artifacts totaling 2,004,352
bytes are independently pinned and charged to each fixture's case model.

| Measurement | 24-MiB representation fixture | 16-MiB capacity fixture |
|---|---:|---:|
| Verified committed views | 22 / 22 | 1 / 1 |
| Stored checkpoint/part/config/footer bytes | 15,387,081 | 8,958,817 |
| Charged bytes including existing artifacts | 17,391,433 | 10,963,169 |
| Terminal footer bytes | 644 | 838 |
| Original fixture elapsed seconds | 32.522140 | 1.747618 |
| Outcome | Exact restoration PASS | Expected refusal PASS |

The representation accounts for 260,277,157 logical snapshot bytes by sharing
identical immutable parts. No compression discount enters either case budget.
The smaller fixture rejects the full report before writing additional files,
retains its prior checkpoint and records the refused state's exact hash/length
as uncommitted. That full report remains in the unchanged original public archive.
Neither fixture has orphan files. Both stores are closed and cannot resume.

The complete original qualification took **38.419505 s**, peaked at
**247,115,776 RSS bytes**, and created 24,362,765 evidence bytes before its summary.
It made one batched local Git input read. There were **zero new random values,
native scores or physical decisions**, and the old input bytes remained unchanged.

## Implementation and verification

`physical_evidence_radio.py` stores SHA256-addressed immutable parts and linked
checkpoint records. Lists use 128-row groups; raw parts are at most 1 MiB.
All unique parts and metadata count cumulatively. A 64-KiB terminal reserve is
withheld within the same case cap. Capacity stops are irreversible; uncertain
writes poison the writer. Read-only recovery exposes a verified committed prefix
and explicitly counts any orphan tail. It grants no restart or scientific lease.

The physical helper can opt into checkpoints at admission, completed stages,
each 1024 appended rows, receiver return before receipt verification and final
closure. It retains a small failure reference and records timing/RSS when durable
closure is possible. Successful numerical report bytes are unchanged.

**63 tests pass:** 23 new storage/integration tests, 34 existing physical fixtures
and six native-receipt bridge tests. They cover capacity, corruption, stale pins,
lost acknowledgements, torn writes, timeout/cancellation, terminal failure and
exact report-byte preservation. The initial test run exposed a local variable
name collision; that failure log is retained alongside the corrected passing run.

After the large fixtures closed, the decoder was optimized to validate each
immutable logical value once and assemble its canonical bytes. Exact copies of
the seven code/scope/test files used by the original qualification are preserved
under `qualified_sources/` with their hash manifest. The published current decoder
was separately checked by all 63 tests and a **read-only audit of the same closed
stores**, with writer/RNG/native entry points blocked. All 22 + 1 snapshots match
the independent prewritten size/hash schedule, and every closed fixture file
remains unchanged. Immutable cache/inventory views also reject mutation.

The optimized reader inspected and restored the 22-view store in **2.101765 s**;
the whole read-only audit took **2.387792 s** and peaked at **146,915,328 RSS bytes**.
The earlier readback took 20.019321 s but also reconstructed comparison JSON
views; these different workloads are descriptive observations, not a controlled
benchmark or qualification of the scientific 40/80-second budgets.

## Evidence and continuation

[`results_radio_physical_evidence_2026-09-29/`](results_radio_physical_evidence_2026-09-29/)
contains the fixed input schedule, both results, reservations/checkpoints/footers,
all test/stdout logs, the original qualified sources, the decoder audit and a
lossless full archive. `archive_manifest.json` inventories every original file and
transport part by length/hash. `scripts/radio_physical_evidence_archive.py` verifies
and optionally restores that archive without running either qualification.
The publication audit records immutable remote readback and complete transport
accounting separately from local fixture timings.

This qualifies local storage/restoration for the observed partial-report workload.
It does **not** establish that full receiver/alias evidence fits, that a complete
native physical run passes, or that remote scientific timing/capacity is adequate.
An abrupt kill can lose work since the last checkpoint; in-progress receiver
queries and retention failures before helper entry are not individually covered.

**Next:** bind the store and all dynamically generated artifacts into the outer
worker's prospective case allocation and strict publication inventory. Preserve
only bounded failure references outside that allocation, then measure complete
archive publication/readback. Any later native physical qualification requires a
separate fixed freeze and fresh identities. Do not reopen or rerun the closed
eight-case experiment, reuse its unentered identities or raise its failed caps.

The prior receipt mismatch and 8-MiB failure-reserve failure remain recorded;
all eight old identities remain spent. **127/24 stays NOT ACTIVATED.** Telescope
spectra and old holdouts remain unopened; all source selections, holds, counters,
LS pause and CHEOPS UNSENT are unchanged. No messages or delegation. Consolidate
on 9 October without extending the plan.
