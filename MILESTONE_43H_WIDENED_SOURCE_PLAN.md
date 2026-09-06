# M43H: widened source receipts, restart and live integration gate

Freeze this protocol, code, fixtures and configuration publicly before the
full-size source-chain evaluation. This continues M43G's numerical qualification;
M43H must establish raw-data ancestry before new-bank scores can be meaningful.

## Scope and known environment limitation

Select epoch1_on and epoch1_off at m37_1412p5, with all 16 integrations and the
exact M43F wider interval [163032021, 164164291). No selection depends on spectra.
Keep every M43E bank/factor and prior-result identity unchanged.

The current executor has neither h5py nor hdf5plugin. An attempted pip installation
was cancelled by the environment's network approval before a decision was returned.
No alternative download route is authorized by this fact. Consequently this
milestone can qualify source-row persistence and bounded HTTP behavior through
explicit local fixtures, but cannot presently qualify HDF5 decoding or attest
live telescope products. The config's HDF5 integration gate remains false.
Installing dependencies alone does not make that unexecuted gate pass.

This is an engineering validation limit, not a request for a new owner permission.
Existing authorization covers analysis, downloads and publication. Finish all useful
local work and publish the blocked live stage plainly; do not relabel fixture arrays
as telescope spectra or use synthetic source identities for physical data.

## Separate source boundary

`source_m43h.extract_remote` owns the prospective production path. It verifies the
hash-pinned implementation/config, original scan definitions and M43F/M43G ancestry,
checks the selected dimensions and normalization scope, then requires dependencies
and HDF5 integration qualification before any remote HEAD or payload request.
A later qualified invocation must match exact URL/size/ETag, header, chunk geometry,
and the precise `data[row, 0, start:stop]` hyperslab before source rows are accepted.
It never accepts caller-normalized arrays. No old source/cache class is modified.

Preserve each native descending float32 row and derive normalization internally:
reverse once to ascending physical frequency, partition median/MAD in 4096-channel
blocks from the **new extraction zero**, including the terminal block. Check finite
values, dtype, shape and layout before coercion. This is the same arithmetic M43G
qualified, with newly named physical-source receipts rather than synthetic products.

Store each native and normalized row as an atomic .npy file, flush/fsync and publish
its sealed receipt last. Bind scope, integration index, native/ascending/normalized
payload hashes and .npy file hashes. An interrupted, unreceipted row is not complete.
Restart rechecks existing receipts, file bytes, dtype/shape and normalization before
reusing a row. A complete source receipt requires every row in exact order.
Rehydration requires an independently retained complete receipt SHA and expected
source kind. A local fixture cannot satisfy the default telescope-kind requirement.

Live source receipts also retain a range-plan hash and complete transport checkpoint.
A mirror may grow to include another window; preserve the original completed source
identity if its rows, scope, range plan and original checkpoint segments survive.
Checksums and in-process factory ownership establish reproducible integrity, not a
cryptographic guarantee against a malicious server, runtime or caller forging both
payload and its supposed independently trusted receipt.

## Bounded transfer and resource scope

The new transport retains the legacy identity-bound sparse mirror/checkpoint logic,
with serial requests capped at 8 MiB and file-object reads capped at 32 MiB. It checks
HTTP status, exact Content-Range, ETag and encoding before reading at most requested
length + 1 bytes. Reject oversized/truncated bodies and unbounded HDF5 reads. Restore
only checkpoints whose individual segments respect the new size cap; hash-check them.
Use a separate M43H mirror namespace. Timeout is 30 seconds; a failed request leaves
completed segments available for an explicit restart, without an unbounded retry loop.

Require rank-3 chunks with leading shape (1,1), at most 16 MiB decoded per chunk, and
an 8 MiB HDF5 chunk-cache setting. The conservative declared buffer allowance is
32 bytes/native channel plus 92 MiB for transport, HDF5 reads/cache/chunk and scratch,
with a 256 MiB cap. This is allocation modelling, not measured RSS or proof about all
HDF5/compression-library/internal or OS memory. Do not assert full transport memory
qualification while the HDF5 integration is unexecuted.

## Predeclared fixture evaluation

Use the real selected metadata/dimensions and exact wider intervals in an explicitly
local dataset facade. It supplies deterministic float32 values from
`((channel*1103515245 + (row+1)*12345) % 104729) / float32(1024)`.
This facade exercises hyperslab requests and source-row logic but does **not** decode
an HDF5 file, contact a remote host, or test archive compression.

For both selected scan/windows:
1. Interrupt after exactly five completed rows; require no complete source receipt.
2. Resume the remaining eleven rows, without rereading the first five from the facade.
3. Verify all sixteen normalized rows against independent full-sort median/MAD code.
4. Rehydrate from the retained receipt, then repeat a completed restart with zero new
   dataset reads and an identical complete receipt.
5. Publish only fixture receipts, hashes and results; intermediate arrays remain
   reproducible working inputs, not user-facing telescope products.

Development fixtures additionally test wrong headers, intervals, chunk bounds, dtype,
shape, nonfinite data, changed scope/rows/files, row ordering, independently trusted
receipt checks, wrong source kind, HTTP rejection before body reads, bounded response
reads, sparse-mirror corruption and zero-request restart. These may run before freeze.

Finally invoke the guarded live entry for the two frozen anchors. Record exact missing
packages/integration status. Failures must be reported as blocked before remote contact,
with zero attested telescope products. No scores, injections or new calibration occur.

## Next gate

Enable an environment with the HDF5 dependencies through its approved installation
mechanism, then execute actual HDF5/codec integration fixtures through the same bounded
file interface, including header/hyperslab faults and restart. Publish that qualification
and a frozen amendment before enabling the live gate. Then fetch the two chosen real
anchors, independently verify raw/normalization ancestry, and connect a separately
attested cache path for the fixed bank before exhaustive real-data score anchors and
renewed null calibration. Do not interpret this milestone as a detection result.
