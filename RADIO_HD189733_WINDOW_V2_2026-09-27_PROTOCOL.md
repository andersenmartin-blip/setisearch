# HD189733: new window identity version after the geometry study

The retained metadata study found a concrete transfer incompatibility: the
old cross-window contract fixes 16,384 channels and four normalization blocks,
whereas the declared HD189733 nominal-model guard selects 65,536 channels
and sixteen blocks. The old API correctly refuses this geometry. It stays
unchanged; changing its constants would relabel previously frozen identities.

Implement a separate, metadata-only v2 builder for this selected source and
the three exact windows in the retained geometry study. Bind externally
supplied SHA-256 values for the preparation contract and design bytes. Recheck
every source URL/size/ETag, header-derived frequency endpoint, interval/chunk
mapping, 16 time rows per source, all normalization blocks and disjointness.
Recomputing an embedded hash must not conceal a stale ETag, changed source,
wrong coordinates, shifted frequency or broken normalization partition.

Freeze only identities. This component has no extraction, calibration,
scoring, threshold-transfer or admission operation. Mark its result as blocked
until the physical motion bank, source codec/runtime evidence, fresh control
design, numeric transfer and recovery/RFI/null evaluation are completed under
one integrated prospective protocol and cumulative resource/trial ledger.
The geometric model bound is not that physical qualification.

Exercise only these new metadata-binding risks. Do not rerun old pipelines,
control panels or closed acquisition tests. No new synthetic spectral values
are required by the v2 tests. Do not alter either HD1461's v1 identity contract
or the selected source's preparation-only contract. Primary stays neighbor9;
the reserved M43AF inputs, all closed outcomes and unsent messages persist.
