# V2 checkpoint event batching passes

30 September 2026. **PASS for the deterministic local parent/journal
component.** No native execution or case reservation occurred.

The v2 writer now registers each checkpoint's new content-addressed parts in
bounded batches of at most 128 files. The append-only event retains every
individual filename, byte length and SHA256; artifact bytes, case/file caps,
journal allocation and closure reserves are unchanged. Checkpoints larger than
one batch split only their journal registration, not their file identities.

**125 tests pass** across the changed event store/v2 parent suites and the
nearest physical, v2-codec and remote-archive regressions. Five new tests cover:

- 64 files committed by one canonically ordered event with all individual
  receipts and exact history restoration;
- a torn eight-file batch leaving only explicit unregistered bytes, no event
  and no resumable lease;
- refusal of closure, outside-group and over-budget batch members before write;
- a normal v2 checkpoint registering all new parts in one event; and
- a checkpoint crossing 128 new files registering two events while preserving
  every exact file and reconstructing the original snapshot.

The pre-existing lost-acknowledgement test was tightened for the new atomic
event: when the journal head move lands but its response is lost, read-only
recovery sees the complete batch and both writer and lease remain stopped. Old
single-artifact events and historical documents are unchanged.

This removes one concrete cumulative-journal obstruction for the next native
qualification, but it is not sufficient admission. The hard physical algorithm
can make about 51 checkpoints at its 10,000-record ceiling (admission; bounded
matched/adjacent/alias/decision/cluster stages; receiver/identity; terminal
snapshot). The next public freeze must therefore set a compatible explicit
checkpoint limit (not silently rely on the hard 128), per-case dynamic file cap
and cumulative event/file/byte budget for all fresh cases. It must also integrate
the already qualified receiver batching and terminal archive batching into
publication during execution.

**Exact continuation:** construct and test that fresh native v2 parent/runner
without drawing RNG: fixed new namespace/identities, eight-case manifest,
18-MiB cases, 8-MiB cumulative journal, explicit checkpoint/file/event ceilings,
full stage timers, bounded failure/RSS evidence and a batched remote publication
broker. Publish and independently read back its complete executable/runtime
freeze before any reservation or RNG entry. Do not reuse or rerun the closed
29 September identities.

127/24 remains NOT ACTIVATED. HD189733/85030 remains selected; HD1461/71139
remains on pointing-provenance HOLD and GJ724/73005 remains reserve. Spectra and
old holdouts remain unopened, LS paused, CHEOPS UNSENT. No external messages or
plan extension; consolidate 9 October.
