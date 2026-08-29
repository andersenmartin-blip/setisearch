# Milestone 37 detector-v0.6 disposition/journal checkpoint

Status: **NON-FROZEN SYNTHETIC CHECKPOINT — COMPLETE DISPOSITION JOIN AND
JOURNAL BINDING PASSED — COMPLETENESS FEASIBILITY BLOCKED — NO SPECTRAL
ACCESS**.

This checkpoint joins the complete receiver, adjacent-OFF, retained-OFF and
receiver-alias products and makes the joined result restartable. It also adds
the exact run-inventory contract consumed by the M37 physical-disposition
journal transition. It is not a detector release, preregistration, search,
completeness result, null result or signal claim.

## Closed bounded gates

- `physical_disposition_v0p6` validates the complete physical-evidence
  execution result, retained-OFF result and receiver-alias result against
  independently supplied receipt identities. It requires one shared window,
  ON-retention record inventory, receiver product, adjacent evidence and final
  disposition count. Upstream evidence is retained byte-for-byte.
- The complete joined result can be published as canonical, no-replace,
  read-only JSON and reopened only against independent file, run, window,
  cache-manifest, factor-bundle and ON-retention roots.
- `physical_disposition_manifest_v0p6` orders the complete child artifacts by
  window, reopens every child and aggregates final disposition and resource
  accounting. A missing, duplicated or reordered window fails closed.
- The M37 wrappers require the exact five M37 windows and reapply the M37
  resource and receiver-alias contracts. The bounded one-window synthetic
  fixture cannot expand into an M37 claim.
- `advance_m37_physical_disposition_from_manifest(...)` reopens the exact M37
  run manifest before appending `physical_disposition_complete`. The journal
  event binds the manifest file, manifest identity, child inventory,
  ON-retention inventory, cache/factor ancestry, five-window count and measured
  resource totals.
- The journal metadata gate requires five windows, no more than 50,000 final
  records, the exact 536,870,912-byte mapped-memory cap and a peak no larger
  than that cap.

## Verification

| Check | Result |
|---|---|
| Disposition/resource/journal targeted suite | 26 passed, 0 skipped, 0 failed |
| Complete repository suite in candidate dependency stack | 279 run, 278 passed, 1 expected benchmark skip, 0 failed |
| Exact-grid 256-scramble benchmark | Passed; 0.727581 s, 13.33× recorded-baseline speedup |
| Exact-grid output SHA-256 | `ec7baa1b7e7f5089dac5cf321c7f5294806057aaf1a2a68f7b56dcb99a8321d4` |
| Exact-grid peak RSS | 99,647,488 bytes |
| Offline wheel build | Passed; SHA-256 `59fc8d15a754b41e948859f8d94f670bb0a6afe6c6881261e06ebe14356b9531` |
| Candidate numerical/extractor stack | NumPy 2.5.2, Astropy 8.0.1, h5py 3.16.0, hdf5plugin 6.0.0, fsspec 2026.7.0, Matplotlib 3.11.1 |
| Python patch level | 3.12.13 available; prospective 3.12.14 pin not reproduced |
| HD 156668 spectral files contacted | No |
| Spectral dataset values read | No |

## Six-point closure status

1. **Complete evidence to final RFI disposition:** closed for the bounded
   synthetic execution contract; the positive M37 gate remains data-dependent.
2. **All five windows as one run:** the exact ordered run-manifest contract is
   implemented and negative-gated; no five-window production children exist
   before execution.
3. **Restartable journal:** closed at the physical-disposition transition.
4. **Completeness and resource gates:** resource accounting is closed at this
   transition. Completeness is still blocked by the deliberately frozen
   `mandatory-full-replay-benchmark-not-yet-passed` status: there is no
   concrete `CompletenessOperationalPipeline`, no 6,144-trial production
   replay and no production sparse/local receipt chain.
5. **Final Astropy environment:** the full suite and exact-grid benchmark pass
   in the pinned library stack, but Python 3.12.14 is not available in this
   host and therefore the exact final runtime is not claimed.
6. **Six HD 156668 HDF5 files:** not contacted. Crossing the spectral boundary
   while point 4 remains blocked would violate the project's fail-closed
   preregistration gate even though user authorization has been received.

The machine-readable companion is
`results_m37_v0p6_disposition_journal/progress.json`.
