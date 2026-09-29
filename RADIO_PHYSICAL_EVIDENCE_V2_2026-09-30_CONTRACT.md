# Prospective v2 physical evidence contract — 30 September 2026

This is a new engineering representation, `radio-physical-evidence-checkpoints-v2-zlib`.
The old v1 module, its 24-MiB logical restriction and all closed results remain
unchanged. This contract addresses the capacity obstruction established in
[the receiver evidence review](RADIO_RECEIVER_CAPACITY_2026-09-29_DECISION.md).
It does not authorize a native experiment or scientific admission.

## Representation and limits

The actual cumulative case allocation is **18,874,368 stored bytes (18 MiB)**,
including the seven pinned existing base artifacts. A 65,536-byte failure footer
is reserved before accepting any checkpoint. Top-level fields and groups of
128 list rows are represented by lossless zlib level-6/base64 chunks, each covering
at most 1,048,576 original bytes. Encoded chunks have content-addressed SHA256
names; unchanged chunks are stored once. Original field and whole-snapshot
lengths and SHA256 hashes remain independently verifiable.

The reader reconstructs canonical whole-snapshot JSON as a stream. Each
individual field or row group is limited to **25,165,824 logical bytes (24 MiB)**;
whole snapshots have a separately declared **128,000,000-byte logical bound**,
matching the existing physical stage's canonical-byte bound. The v1 bound is
not edited or applied retroactively. Whole-snapshot materialization over 24 MiB
is explicitly refused; callers must use `iter_snapshot`. Values are still
materialized individually, and the writer still materializes a bounded full
canonical snapshot to compute its original digest. This is not a fully streamed
writer or a promise of arbitrary-input RSS safety.

Strict decompression rejects expansion overflow, missing EOF, truncated or
concatenated streams, trailing data, changed hashes and noncanonical JSON.
Checkpoint gaps, wrong case/reservation pins, symlinks and lost acknowledgements
stop the writer. Recovery is read-only; exclusive directories cannot be resumed.
Capacity failure is final, with only failed closure allowed. Completed closure
requires a saved final `complete: true` snapshot.

## One fixed byte-only qualification

[freeze.json](results_radio_physical_v2_2026-09-30/freeze.json) pins the code,
source hashes, fresh identity, recipe and limits before this one directory is
created. The freeze must be publicly committed and independently read back
before execution. The allocation is `radio-physical-v2-byte-20260930a`, with
180 seconds for the whole worker, 512 MiB peak RSS, three checkpoints and the
18-MiB stored-case cap. A failure closes this scope; no retry or smaller
replacement is authorized within it.

The source is the **original 14,979,354-byte incomplete physical report**, plus
the already published deterministic width-1 and width-129 receiver software
outputs (1,024 signature/receipt pairs each). Exact original files, including
their newlines, are retained as UTF-8 string fields. The first snapshot contains
one ordered copy of the 2,048 pairs. The next two contain twenty copies, a
serialization stress load exceeding the known 29,821,434-byte report floor.
Every copy and value remains in the reconstructed JSON; repetition is not
an additional member, query, measurement or independent realization. The
seven original base artifacts are charged at **2,004,352 bytes**, verified
against their immutable archive and retained there without duplication.

The final wrapper and footer remain **FAILED/incomplete**, preserving the
source's physical disposition. A byte-qualification PASS means only that all
three constructed snapshots and the original source files restore exactly
inside this fixed storage/resource allocation. It cannot stand in for the
missing complete native report or extrapolate compression to future draws.

Reproduction uses `PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python
scripts/radio_physical_evidence_v2_qualification.py --freeze` in a fresh result
directory, followed by the same script with `--receipt` pointing to the verified
public freeze receipt. The historical source commit and all transport pins are
checked before writer creation. Existing result directories cannot be rerun.

## Admission boundary and next integration

The physical fixture observer accepts exactly the original writer or this new
writer. Deterministic tests compare the whole result with and without the new
observer. **Parent-lease creation is explicitly rejected** in v2: neither the
event store, remote runtime publisher nor scientific allocation adapter is
qualified by this change. No numerical method, threshold, receiver query,
historical reservation or scientific budget changes.

After exact large-load restoration, the next substantive task is to bind v2
to the existing event/parent and bounded remote protocol, then freeze one fresh
complete native physical/resource qualification with receiver batching and all
failure duties. Actual 127/24 validation and a separate telescope protocol are
still required. 127/24 remains NOT ACTIVATED; spectra and old holdouts remain
unopened. All holds, spent identities and failures remain; no messages or
delegation. Review around 2 October, consolidate 9 October without extension.
