# M43M: complete the three-pair widened source inventory

M43L qualified all eight widths for the first ON/OFF pair at 1412.5 MHz.
Before qualifying the real multi-epoch combination, obtain the remaining
four widened source products: epoch2_on, epoch2_off, epoch3_on, epoch3_off.
These are repeated scans in the existing single observing sequence, not
independent observing dates. There is no new target or frequency selection.

Freeze this plan, runner, tests and configuration publicly before spectral
range requests. The metadata-only HEAD check on 2026-09-06 returned the
expected size and ETag for all four files (four HEADs; zero range requests).
The source selection and remote identities come from the unchanged M37
metadata; widened channel bounds come from the unchanged M43F preflight.

Use the unchanged, hash-pinned M43H live source factory, HDF5 runtime,
transport, hyperslab extraction, float32 normalization and source contract.
M43M extends the inventory, not M43H's historical two-anchor result. Four
ordinary subprocesses may run concurrently, one per source; no agent work.
Each source has at most two attempts, with checkpoint reuse only after
the inherited integrity checks. Retry only timeouts, connection errors,
HTTP 408/429/5xx, or URL errors whose reason is a timeout/connection error.
Do not retry source identity, normalization, integrity, permission or disk
errors. Preserve every failed attempt, partial row count and transfer counters.

Accept each source only after all 16 native and normalized rows pass the
retained receipt gate and independently sorted median/MAD reference,
including dtype equality. Then repeat the completed extraction: require
the same receipt identity, 16 resumed rows, and zero new range attempts or
bytes. HEAD revalidation on restart is allowed. Publish exact legacy-encoded
range-plan bytes, source receipt and per-source checkpoint as they finish.

The endpoint requires four new sources/64 rows. Combined with the unchanged
two M43H sources/32 rows, this gives six source products/96 rows across
three ON/OFF pairs at one window. No score calculation, candidate decision,
recovery estimate, threshold calibration or multi-epoch combination occurs
in M43M. The next endpoint must separately qualify that combination.
