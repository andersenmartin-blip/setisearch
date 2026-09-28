# HD189733 filter profile and full-chunk fixture — prospective engineering scope

Continue from method checkpoint `1f9a1513498a0496b9c2e8857f76c89d13c9df65`.
The existing generic gzip/bitshuffle qualification is closed and reused as
evidence, not rerun. The new issues are the active source's exact filter
declaration and chunk geometry, plus enforcement before extraction.

The six retained definitions declare one optional HDF5 filter 32008 with
client data `[0,3,4,0,2]`, chunk shape `[1,1,1048576]`, float32 and full dataset
shape `[16,1,264503296]`. Use those retained definitions and exact calibration,
validation and pilot extraction coordinates. No remote product or new header
request is authorized. Keep the original preparation file unchanged.

1. Add a strict filter-pipeline guard to the source reader. Compare IDs, flags,
   order and every client-data integer before chunk discovery/prefetch and
   before row extraction. Display names are not codec semantics. A telescope
   definition missing a declaration fails before live identity lookup. Preserve
   the old local-fixture path where no declaration was supplied.
2. Verify the guard with focused negative fixtures for missing/extra/reordered
   filters, version/element-size/compressor/flag mismatch and early rejection.
3. Construct one local deterministic source-shaped HDF5 fixture, with only
   the 48 selected chunks (16 rows by three window positions) populated. Each
   chunk contains 1,048,576 float32 values given by the fixed arithmetic
   pattern in the generator, never noise or an injected signal. Verify all
   50,331,648 decoded cells bit-for-bit and all 3,145,728 extracted native cells.
   Verify descending-to-ascending normalization of those extracted rows.
4. Match the old source's filter client-data declaration using an isolated
   local-fixture creation process with the filter temporarily unregistered,
   optional declaration present, and direct compressed-chunk writes. Restore
   the actual bundled filter before decoding. The compressed bytes are from
   the current local encoder; do not describe them as archive-produced bytes
   or proof about the original encoder. If this construction cannot preserve
   the exact declaration, stop it with evidence, without changing scope.

Limits: one full-chunk fixture execution, 600 active seconds, 512 MiB RSS,
128 MiB local fixture/evidence bytes, zero source/network requests and zero
scientific control/attempt/diagnosis/remedy/pilot allocations. Tests concern
new code risks, not old unchanged pipelines. Keep compressed local evidence,
hashes, runtime binary identities, timings and every failure. No source receipt
or telescope admission may be inferred from local decoding. A later live
protocol must use a fresh code/runtime binding rather than rewriting the
original preparation contract or relabelling old fixture receipts.
