# C002 preservation and reproduction

The fixed C002 run completed at **2026-11-02T19:00:12.407586+00:00**, with status `COMPLETE_FIXED_GROUP_CONTEXT`. It retains nine bounded source windows, eighteen profiles in two fixed frames and both exact historical raw panels: **29 NPZ files totaling 320,652 bytes**.

| Saved evidence | Files | Total bytes | Exact filenames and SHA256 bindings |
|---|---:|---:|---|
| Seven merged and two native-order source windows before interpolation | 9 | 74,375 | [BOUNDED_INPUT_INDEX.json](../analysis/results/BOUNDED_INPUT_INDEX.json) |
| Fourteen merged and four native frame profiles | 18 | 233,240 | [PROFILE_METRICS.json](../analysis/results/PROFILE_METRICS.json) |
| Original V2E2-0033 order-2 and order-3 raw panels | 2 | 13,037 | [PRESERVED_RAW_CONTEXT.json](../analysis/results/PRESERVED_RAW_CONTEXT.json) |

All **39 files** bound by [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json) were rehashed successfully while finalizing this document. All 29 NPZ files match their separate index hashes, and both raw copies match the original input hashes exactly. These are byte-integrity checks, without new array interpretation or measurements. Later figures and reports are outside this numerical-ledger count.

| Binding file | SHA256 |
|---|---|
| `analysis/results/OUTPUT_HASHES.json` | `e341d118bd5562a9f7f11c3256e876c67e4c00552e6ccbdd7ac406dca6566b37` |
| `analysis/results/BOUNDED_INPUT_INDEX.json` | `f32ff78b546d748c17d1124ddc22d530e621126041a5f63eefc7a1b588a4510c` |
| `analysis/results/PROFILE_METRICS.json` | `9c2727e6d17e6dcbaac343c4fd80ccbde6ca1e69d1e11b946f07259ba26291c2` |
| `analysis/results/PRESERVED_RAW_CONTEXT.json` | `814097970c6e1edbec52a3b00fa2f9bc2b341e571a5b56b646c801e29a20410e` |

All eighteen profiles and **36 comparison slots** remain, including **four identical-product self comparisons**. No source profiles are blocked. Both order-2 frame profiles remain **raw-only**, with `MISSING_RIGHT_FLANK_COVERAGE`: the entire positive [+1.5, +3] Å interval is outside that order in both frames. This is missing coverage, not a measured nonpositive two-flank reference. Preserve the unchanged support thresholds and any unavailable normalized comparisons; do not replace a missing reference with a one-sided value or drop these profiles.

Compact arrays preserve signed flux, original source indices and coordinates, fixed-frame conversion information, available ERR samples, support and normalization status. Load NPZs with `allow_pickle=False` and retain unavailable-error values and status information. Original full FITS remain necessary for extraction-provenance checks. Native extracted units remain unspecified because `BUNIT` is absent; merged ADU and native scales are not a calibrated physical flux ratio.

The C002 original core was already visible inside the completed C003 surrounding-spectrum window, between its negative reference flank and core. The wider C002 context overlaps C003 over 4.85125 Å and C004 over 2.3575 Å; its original core is outside C004's window. The same seven observations are reused, so this context and any reproduction are neither blind validation nor independent observing time or detections. Fixed reference medians remain descriptive levels, not established line-free continua. The U label remains unchanged.

Historical order-2 global and later five-window mapping gates are true, while its original local and baseline gates are false. Order 3 has all four stages true. Preserve these separate stages: coordinate support or same-exposure native/merged agreement cannot retroactively validate order-2 raw mapping or establish physical origin.

## Method and release

All **25 prospective files** were published at commit [`264a6d5cfd8b0b40780df1f28b65986f50659b2e`](https://github.com/andersenmartin-blip/setisearch/commit/264a6d5cfd8b0b40780df1f28b65986f50659b2e) and read back exactly before execution. The [publication receipt](../PROSPECTIVE_PUBLICATION_RECEIPT.json) binds both public branch heads, file identities and **279,199 verified bytes**. Receipt SHA256: `76c5396f36711022ffe8f72e99a1e4d76973600b10a23ed9e16c18d503763aed`.

The unchanged [plan](../analysis/PLAN.json) has SHA256 `3cfcc7ad2007357edb49c39320d33976d5348ea9a3f03b2d700f6bc4cb3e3efe`; the [root release](../analysis/ROOT_RELEASE.json), issued at **2026-11-02T18:59:58.692291+00:00**, has SHA256 `7a1a077bf7f6c7236869fde5d957a5aa448cd1b87460c6336602f819bb984691`. All **41 plan-bound source hashes** remain exact. The comparison uses the sole C002 discovery on 2022-05-07, BERV −18.8907517532076 km/s, with fixed topocentric anchor **3868.846286702511 Å**. It does not inherit either the January or March anchor. The runner checks release/source bindings and rejects an existing output directory. The [preflight freeze](../PREFLIGHT_FREEZE.json) and pre-array audit records remain unchanged.

## Exact archived input restoration

The [input inventory](../inputs/INPUT_INVENTORY.json), SHA256 `703b3dabc53c7133b8c3c9c4a581fad381c54fb4a0dca501b9c846dd976e8c23`, binds **11 restored files**: seven merged FITS, one ancillary TAR, one native-A FITS and two historical raw-context NPZs. No extra acquisition or duplicate source-archive package is required.

Fresh header checks of all **72 native orders** identify orders 2 and 3 as covering the C002 original center and core; both are retained. Order 2 ends at fixed offset +1.1609411974559407 Å barycentric or +1.161014356180658 Å topocentric, before the positive reference flank. Order 3 covers the complete ±3 Å context. These bounds are freshly established for May 2022, not transferred from C003 or C004. The [input instructions](../inputs/README.md) retain all archive/member hashes, original review records, units and exact discovery identities.

| Existing archive | Restored here | Original instructions and receipts |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH02_INPUTS_PART2_2026-11-01.zip` | May discovery ancillary product | [Saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/LIBRARY_INPUTS.json) |

Both raw-context NPZs are restored from unchanged committed batch02 evidence parts. Full raw detector products remain in the existing archive and are not required for the broader-profile arithmetic.

In a separate reproduction checkout:

```sh
python3 work_harps_20261102_c002_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

One cache may hold both named archives. The helper verifies complete archives and member hashes, rejects differing destinations, retains identical files and writes deterministic metadata. It inspects FITS/NPY headers without executing the comparison. Local cache paths do not enter the metadata. Full restored inputs and temporary input-panel copies are excluded from Git; compact evidence is preserved with the completed analysis.

## Preserve the completed record

Reproduce only in a separate checkout with this phase's `analysis/results/` absent before its first run. Preserve the published inputs, method, code and root release, following the [analysis instructions](../analysis/README.md). Do not reset the authoritative one-shot guard or overwrite completed outputs. Reproduction timestamps can differ; compare scientific arrays and numerical records.

All original U dispositions, survey counts and prior analyses remain unchanged. Reproduction of this fixed context does not authorize favorable reference selection, shifted windows, extra fitted parameters or an independent-detection claim.
