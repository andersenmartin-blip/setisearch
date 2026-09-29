# v2 restores a 42.37-MB byte load within the 18-MiB stored-case cap

30 September 2026. **PASS for exact byte retention and streamed restoration.**
The new, explicitly versioned format restores all three frozen snapshots,
including two of **42,366,912 logical bytes**, with their original lengths and
SHA256 hashes. Total charged case storage is **4,824,307 bytes**, including
the seven existing base artifacts. The stored-case allocation remains
**18,874,368 bytes (18 MiB)**. **46 tests pass: 12 new and 34 existing.**

This resolves the old whole-report materialization obstruction for the new
format and this measured load. It does **not** complete the missing native
physical report, establish compression of a fresh draw, qualify the remote
scientific runtime or admit a telescope pilot. The historical physical source
and the new wrapper/footer remain **FAILED/incomplete**. The storage PASS has
a separate meaning and changes none of those dispositions.

## Prospective scope and evidence

The [v2 contract](RADIO_PHYSICAL_EVIDENCE_V2_2026-09-30_CONTRACT.md), code, tests
and [freeze](results_radio_physical_v2_2026-09-30/freeze.json) were publicly
committed at `b20da8aea44cd21775cc7716b2ea8a2522cf38e8`. Every one of the nine
published files was independently verified before exclusive writer creation;
see [the readback receipt](results_radio_physical_v2_2026-09-30/freeze_readback.json).
The fresh namespace is `radio-physical-v2-byte-20260930a`. It was executed once,
then closed. No smaller replacement or retry was used.

The original incomplete report is retained as its exact UTF-8 string, including
whitespace: **14,979,354 bytes**, SHA256
`6a205b43d53f0a582d73d6d88c1501a0d4d8cd992a974dc8ff6328d300296dfd`.
The two original deterministic receiver software output files are also retained
as exact UTF-8 strings, including their final newlines. Both source files and
the historical native archive are read from the immutable `f6a91931...`
checkpoint, with transport, compressed archive and original-file pins checked.

The wrapper additionally contains the unchanged 2,048 software signature/receipt
pairs, once in the first view and twenty times in each large view. This yields
40,960 pair entries per large snapshot. **These repetitions are a byte stress
load, not independent members, receiver queries or scientific realizations.**
No receipt identity is regenerated and no old native case is rerun. The source
files and every repeated entry remain recoverable; there is no rounding,
omission, truncation or merging away of individual entries.

## Measured result

| Measurement | Result |
|---|---:|
| First snapshot logical bytes | 18,602,244 |
| Second and third snapshot logical bytes, each | 42,366,912 |
| Original snapshots restored exactly | 3 / 3 |
| Stored v2 reservation, parts, checkpoints and footer | 2,819,955 bytes |
| Seven pinned existing base artifacts | 2,004,352 bytes |
| **Total charged case bytes** | **4,824,307** |
| Fixed stored-case cap | 18,874,368 bytes |
| Stored bytes remaining | 14,050,061 bytes |
| Largest yielded restoration chunk | 1,048,576 bytes |
| Measured byte-worker active region | 8.390755 seconds |
| Snapshot write regions | 0.411193 / 1.397197 / 1.362872 seconds |
| Peak process RSS | 194,318,336 bytes |
| Fixed RSS ceiling | 536,870,912 bytes |
| Stored case files | 29 |
| Orphan files | 0 |
| New random values / receiver measurements / telescope reads | 0 / 0 / 0 |

The active timer starts on entry to the byte worker and includes pinned source
verification, encoding/writing, inspection, streamed restoration and exact source
file checks. Python startup/imports, prospective publication/readback, final
result-file emission and result publication are outside that measured region.
The 180-second alarm bounds the run function; this is not an independently
measured full-process or integrated native/publication timing result. Peak RSS
is the process high-water mark, including imports. No 40/80-second scientific
qualification is claimed.

The v2 reader separately bounds one decoded value/group at **24 MiB** and
whole logical snapshots at **128,000,000 bytes**. The latter is the declared
new representation limit matching the existing physical-stage canonical-byte
bound. The old v1 module and its old 24-MiB whole-report bound are unchanged,
verified against the parent code. Large aggregate `snapshot()` reads are
refused; the successful large views were restored with `iter_snapshot()`.
Stored chunks are zlib-compressed/base64 encoded and shared by content hash.
The measured compression and sharing ratio is specific to these original
bytes and intentional repetitions; it is not a capacity prediction for 151
future cases or unknown final alias/decision evidence.

## Tests, logs and complete stored bytes

The new tests cover exact bytes at 0/1/128/129-row boundaries, shared parts,
a snapshot over the old reader limit, individual-value overflow, incompressible
stored-capacity refusal with a preserved footer, decompression overflow,
truncation and concatenated streams, missing parts/noncanonical JSON,
wrong case/stale pins/symlinks, lost acknowledgement/read-only recovery,
incomplete completion and refusal of unqualified parent integration.
Deterministic physical fixtures produce byte-identical results with and without
the new observer and preserve an interrupted receiver stage as FAILED.

The final [46-test log](results_radio_physical_v2_2026-09-30/tests02.log),
[initial test log](results_radio_physical_v2_2026-09-30/tests01.log),
[execution log](results_radio_physical_v2_2026-09-30/run01.log),
[machine-readable result](results_radio_physical_v2_2026-09-30/result.json),
[29-file inventory](results_radio_physical_v2_2026-09-30/case_inventory.json)
and [all original stored case bytes](results_radio_physical_v2_2026-09-30/case1)
are included. Common code/tests, freeze, administrative logs and publication
receipts are package evidence, outside the charged case; the seven previously
stored base files remain in their pinned public archive and are fully charged.
Before freeze, a source-format check detected the software files' original
final newlines; the loader was corrected to verify and retain them. This was
preparation, before any writer or allocation was consumed.

## Continuation and preserved state

**Next:** integrate this version with the existing event/parent and bounded
remote publication protocol. `Writer.create_for_lease` explicitly refuses
that unqualified path today. Then freeze one fresh complete native physical/
resource qualification, using receiver batching, all physical stages and
complete failure evidence. These two remaining gates should be assessed
together; further isolated storage demonstrations do not establish native
readiness. No new native attempt is started by this result.

Actual 127/24 validation and a separately frozen telescope acquisition/trial
protocol remain necessary. **127/24 stays NOT ACTIVATED.** HD189733/85030 stays
selected, HD1461 stays on HOLD, GJ724 remains reserve; telescope spectra and old
holdouts remain unopened. LS is paused, CHEOPS is UNSENT. All closed failures,
spent identities, thresholds, budgets and counters remain unchanged. No
messages, delegation or scheduled task changes. Review around 2 October and
consolidate 9 October without extension.
