# M43L — exhaustive wider integrated real-score anchors

## Endpoint

Evaluate EVERY integrated score for the fixed 1,701-template bank over all
747,793 support carriers, at widths 3,5,9,17,33,65,129, for both existing M43H
first-epoch ON/OFF telescope sources at 1412.5 MHz. This closes the wider-score
combinations left unenumerated by M43I/K. M43J retains the width-one endpoint.
No candidate ranking, detection threshold, recovery or real multi-epoch stack
is included. These are numerical anchors on one observing epoch pair/window.

Freeze protocol, configuration, code and tests publicly before evaluation.
Retain M43E's bank/factors, M43H receipts, unchanged M43I production cache/gather,
and the exact M43I/J/K results and dependencies. All recreated source/cache
identities must equal their prior counterparts.

## Factorized reference, without repeating native windows per score

For each source/width, independently rebuild all native filter values using
explicit integer-indexed normalized windows in 2,048-center chunks. Store this
reference in absolute native coordinates, with NaN guards at invalid centers.
It shares no array storage or filter calls with the production cache, whose
native index is offset by width//2. Require every independent native reference
row digest and combined valid-payload digest to equal M43K's published oracle
and cache digests before using that reference for any integrated comparison.

For integrated reference chunks, calculate nearest-even binary64 native
coordinates directly, sample the independently constructed absolute-coordinate
reference and accumulate rows in ascending float32 order, divided by float32
sqrt(16). Production remains the unmodified receipt-bound M43I adapter.
Compare every integrated cell exactly, with no tolerance. This is a factorized
oracle, not repeated materialization of each native window for each score.
Unit tests require factorization to match the earlier direct-window oracle at
all seven widths and multiple chunk sizes, including repeated native mappings.
The factorization saves repeated work while preserving the frozen arithmetic.

The reference uses a separate filter/access path but shares factors, formulas
and NumPy with production. This is numerical cross-validation, not independent
scientific replication. Digest equality uses the existing local integrity trust
model; it is not protection against a malicious runtime or archive server.

## Inventory and checkpoints

Process contiguous template batches of 32 with the last five-template batch
(indices 1696–1700). Each batch spans the ENTIRE support lattice. Gather and
integrated reference chunks are 4096 carriers. Keep every proxy carrier,
including repeated native-channel mappings and the 64 guards at either end.
There are 54 batches per source/width, 14 source/width jobs, 756 batches,
23,814 complete integrated vectors and 17,807,942,502 compared score cells.
Counts include M43I overlap and correlated mappings, not independent trials.

Retain the M43I full vectors for template indices 911 and 1678 from exhaustive
batches, in the published order; their combined digest must match M43I for each
source/width. A source/width checkpoint is atomically updated after each passing
batch, with complete=false. Only the exact 54-batch ordered inventory and M43I
vector agreement permit complete=true. Its final seal is referenced by the
aggregate result, which is written only after all 14 jobs pass.

Checkpoints contain batch ranges, counts and output hashes, not full matrices.
Final source/width files retain every batch record. This runner recomputes on
restart; it does not trust arbitrary self-sealed files to skip comparisons.

## Parallel runtime and failure policy

Seven ordinary numerical worker processes handle one width each, with two
sources sequentially per process. This is computational multiprocessing, with
no delegated research or AI agents. The observed environment before freezing
provides an eight-CPU quota and 20 GiB cgroup memory. BLAS threads are fixed to
one per process. The config fixes seven workers; no unattended execution is
promised between active sessions.

Each worker holds one source, production cache, independent reference and one
32-template full-support score output. The unchanged adapter models 434,394,176
bytes for its gather, below its 512 MiB cap. That cap excludes oracle/caller
arrays, process RSS and OS caches. The independent absolute reference adds
about 72.5 MB plus temporary construction storage per worker. There is no claim
of a 512 MiB limit on the combined seven-process job or measured total RSS.
Reference coordinate arrays are carrier-chunked. No complete bank-by-carrier
score matrix is retained. Observed wall time is descriptive, not calibrated
production throughput or cost.

A failed job signals the other workers, which stop at the next batch boundary;
no aggregate success is written. Preserve any partial/failure evidence and
publish an amendment before changing arithmetic or the endpoint. The required
M43-family tests cover direct/factorized equivalence, absolute guards, complete
batch assembly, ancestor-vector order, and rejected mismatches/inventories.

## Interpretation and next work

If all checks pass, M43J plus M43L cover the complete bank/carrier integrated
score domain at all eight widths for these two sources. This does not extend
the source epoch/window coverage, qualify a real multi-epoch stack, or establish
false-alarm/recovery behavior. The next gate adds the remaining real epochs and
qualifies the stack/detection endpoint before newly frozen calibration.
