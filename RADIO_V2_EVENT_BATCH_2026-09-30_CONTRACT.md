# Prospective v2 checkpoint event batching — 30 September 2026

This is a deterministic engineering component qualification. It creates no
native array, random value, receiver measurement, score or telescope read and
does not reserve a fresh case. Existing ledgers, physical outcomes and archive
namespaces remain immutable and closed.

The v2 physical writer may create many content-addressed parts for one logical
checkpoint. Under this contract, an engineering `EventDirectoryStore` registers
at most 128 new dynamic physical files in one append-only `artifact_batch`
event. Every member retains its individual plain filename, byte length and
SHA256. The event list is unique and sorted. Fixed/base artifacts, group seals
and reserved closure files cannot be batched.

If a checkpoint needs more than 128 new files, the writer emits consecutive
bounded events; the checkpoint record remains in the last applicable batch.
The exact case inventory, byte allocation, dynamic file cap, v2 checkpoint cap,
8-MiB cumulative journal allocation and all closure reservations remain
unchanged. Batching reduces event/pointer overhead; it never discounts stored
artifact bytes or permits more evidence files.

All files in a batch are durably created before the one journal event. A crash
before the event leaves explicit unregistered case-directory orphans and stops
the process-local lease. A lost acknowledgement after the atomic journal head
move may leave the entire batch committed; both writer and lease still stop and
recovery is read-only. No partial committed batch, retry, reconstruction of a
lease, overwrite, deletion or refund is allowed.

Qualification must cover canonical event order, individual receipts, batches
crossing the 128-file boundary, changed/torn bytes, lost acknowledgement,
journal capacity, reserved closure space, v1/v2 separation and exact read-only
recovery. Existing scalar-artifact events and all historical evidence retain
their original interpretation.

Passing this component does not prove that a complete fresh eight-case native
scope fits 18 MiB per case, 8 MiB of cumulative journal storage, its time/RSS
caps or remote publication budget. A later public freeze must specify exact
fresh identities, no more than the physical algorithm's bounded checkpoint
inventory, per-case dynamic file caps, cumulative event/file/byte ceilings,
receiver batching, full stage timings, complete failure evidence and batched
remote publication during execution. 127/24 and telescope admission remain
off.
