# Bounded physical evidence checkpoints — prospective byte-only qualification

Namespace: `physical-evidence-qualification-20260929c`. This is an engineering
storage study using already public bytes, not a new signal/control run. No RNG,
native cache, scores, detector, physical decision, old experiment or telescope
array may be regenerated. It neither consumes nor releases any scientific case.
The previous native-chain execution and 8-MiB failure-reserve failures remain
unchanged; all eight of its identities remain spent, including the unentered three.

## Exact input and fixed work

Use only the archived partial report from public result commit
`43fa09b11c0586c47538d2a8ebfc6060e3d5248e`, at original archive member
`live01/partial_physical_or_retention.json`: 14,979,354 bytes, SHA256
`6a205b43d53f0a582d73d6d88c1501a0d4d8cd992a974dc8ff6328d300296dfd`.
Verify it against that commit's archive manifest. Also verify the seven already
stored case4 artifact byte strings against the same immutable manifest. Their
2,004,352 bytes count in the case total, although they are not copied into the
new representation. The old case identity in a snapshot is source provenance,
not permission to execute or reserve that case again.

Build a fixed serialization schedule from the report: one snapshot with empty
matched-OFF and adjacent-OFF lists; ten monotonically increasing matched-OFF
prefixes at 1024-row intervals and the final 9792-row prefix; ten equivalent
adjacent-OFF prefixes; finally the EXACT original failed report. These 22 views
are deterministic storage fixtures constructed from retained rows. Intermediate
views are **not claimed to be historically captured states or timing evidence**.
Record every expected canonical snapshot size/hash and exact code/scope/input
pins before creating the first storage writer.

Run exactly two large byte fixtures in separate exclusive directories:

1. `representation01`: a 24-MiB case reservation, including the seven old artifact
   byte strings, every unique part, all 22 checkpoint records, reservation and
   terminal footer. Recover every view exactly. The stored terminal physical
   status stays FAILED because the source report is failed.
2. `capacity01`: a deliberately smaller 16-MiB case reservation. Commit the first
   view, then attempt the full failed report. Expect a refusal before additional
   files are written, a small failed footer, and recovery of only the prior
   committed view. The rejected full snapshot must be named by hash/length and
   explicitly marked uncommitted; it cannot be truncated into success. It remains
   publicly available in the unchanged original archive.

Fixed small unit fixtures separately test correct completion, wrong bindings,
changed/corrupt/missing bytes, stale anchors, lost acknowledgements, torn parts
and commit records, timeout/cancellation, footer failure and irreversible stops.
They use deterministic arrays/signatures and no new Gaussian values. Tests must
also compare the complete physical report bytes with and without the observer.

## Representation, accounting and failure semantics

Each immutable checkpoint names its predecessor, reservation, stage, exact
logical snapshot SHA256/length and field parts. Immutable parts are SHA256-named;
top-level lists are grouped by 128 rows, other fields by 1-MiB byte parts. Identical
parts are shared. Every checkpoint and every unique part is charged in full;
no compression discount is used for the case budget. All 22 original views are
restorable without retaining 22 duplicate large JSON documents. Virtual decoded
bytes are reported separately from physically stored bytes.

64 KiB of the SAME case reservation is withheld before normal checkpoint writes
for a terminal footer. The footer records failure/stage, elapsed time, final
process peak RSS and the exact last checkpoint. Large physical evidence belongs
in prospective case storage, never an unregistered post-failure top-level dump.
This is the rule for the new mechanism; it does not retrospectively reassign
bytes in the old failed scope.

The local writer is non-resumable: exclusive directory creation, exact unchanged
inventory before writes, durable exclusive part writes, then a checkpoint commit
record. Any uncertain write poisons the writer. Readers may expose a verified
committed prefix and explicitly counted orphans after a crash; they have no
write, lease, restart or scientific authority. A capacity refusal is irreversible
and leaves the reserved failure footer available. A failed/uncertain checkpoint
cannot authorize a complete result. If the latest in-memory state cannot fit,
report that it was NOT archived; do not silently treat it as empty or complete.

The physical helper may opt into this observer. It checkpoints admission,
completed stages and every 1024 appended stage rows, and preserves a failure
snapshot on caught interruption when space/storage permit. Between checkpoints,
in-memory work can still be lost on process kill. There is no claim that receiver
queries currently in progress are individually durable, nor that upstream
retention-generation failures are covered by a helper entered only after retention.
Successful numerical report bytes and all physical thresholds/caps stay unchanged.

Limits per store: at most 24 MiB charged case bytes, 24 MiB per decoded snapshot,
128 checkpoints, 8192 files, 1 MiB per raw part, 128 rows per list group. Each
large fixture has 180 seconds; whole qualification 480 seconds including setup
and audit; 512 MiB peak RSS; 96 MiB of uncompressed new qualification evidence.
The case4 external 2,004,352 bytes are charged to EACH fixture's model separately,
not refunded or counted as a second scientific observation. No budget is raised
in response to the measurements. Oversize writes stop; all completed files remain.

Publication allowance for this package: 48 GitHub tool calls, 48 top-level local
Git invocations, 64 MiB each request/response JSON, 1800 seconds cumulative active
tool latency. Development/tests and byte-fixture time are separately reported.
Use batched local Git object reads and exact tree prediction. Lossless public
transport may compress the parts/checkpoints, but decoded case-byte accounting
still uses the uncompressed stored parts. Preserve input schedule, code pins,
initial test failures, final tests, stdout, both outcomes and a full archive
inventory. Verify every decoded public file against its original.

## What a pass means

PASS qualifies local durable storage/restoration and explicit byte reservation
on this observed partial-report workload. It does NOT qualify a full successful
native physical run, scientific 40/80-second timing, the 151-case ledger, new
127-reference calibration, cross-process/remote scientific publication, or a
dynamic artifact inventory in the existing strict scientific lease.

The future outer worker must bind this store, its existing-artifact pins and its
entire archive into one prospective case allocation; it must write only a small
failure reference outside it. Remote publication and complete final receiver/
alias evidence need their own measured integration. Keep 127/24 NOT ACTIVATED,
all telescope/holdout values unopened, prior dispositions/counters unchanged,
no messages or delegation, and consolidation on 9 October without extension.
