# C007 preservation and reproduction

The frozen C007 run completed at **2026-11-02T17:56:14.717346+00:00** with status `COMPLETE_FIXED_GROUP_CONTEXT`. It preserves eight bounded source windows, sixteen profiles in the two fixed frames and one exact historical raw panel: **25 NPZ files totaling 285,753 bytes**.

| Saved evidence | Files | Total bytes | Exact filenames and SHA256 bindings |
|---|---:|---:|---|
| Seven merged and one native source window before interpolation | 8 | 65,887 | [BOUNDED_INPUT_INDEX.json](../analysis/results/BOUNDED_INPUT_INDEX.json) |
| Fourteen merged and two native frame profiles | 16 | 211,811 | [PROFILE_METRICS.json](../analysis/results/PROFILE_METRICS.json) |
| Original V2E2-0026 / order 19 raw panel | 1 | 8,055 | [PRESERVED_RAW_CONTEXT.json](../analysis/results/PRESERVED_RAW_CONTEXT.json) |

All **35 files** bound by [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json) were rehashed successfully while finalizing this document. All 25 NPZs match their separate index hashes; the raw copy matches the original input hash exactly. These are byte-integrity checks, without new array interpretation or measurements. Later figures and reports lie outside this numerical-ledger count.

| Binding file | SHA256 |
|---|---|
| `analysis/results/OUTPUT_HASHES.json` | `b651d712f402bd3d38630e1a841a6960a0623b586f33981b0ed3d81ded566cee` |
| `analysis/results/BOUNDED_INPUT_INDEX.json` | `862fb07e11d2553b761589a4be38f8605add972b8cfa34cc9646e8088bc3adda` |
| `analysis/results/PROFILE_METRICS.json` | `d991339fdc806d6f04d9e0b4e82a0a2acd6747898a4b28384595068ecfa87a0a` |
| `analysis/results/PRESERVED_RAW_CONTEXT.json` | `3bda05635ebf078cc477ecc8387b0754cf27c41baff561d1c2be624f998c9ed0` |

All sixteen profiles and 32 comparison slots are retained, including four identical-product self comparisons. There are no blocked source profiles or raw-only normalization slots. The compact evidence preserves signed flux, source indices and coordinates, frame conversion metadata, available ERR samples, support and normalization status. Read NPZs with `allow_pickle=False`; preserve unavailable-error samples and all status information. Original full FITS remain necessary for extraction-provenance checks.

The seven epochs reuse existing observations. C007's original ±0.25 Å core lies inside the already viewed C006 positive normalization flank. Conversely, C006's selected centers lie within C007's negative reference flank. Fixed queue selection before C006 results does not make this overlapping flux blind or independent validation. Reproduction adds no observing time, independent detection or new physical-origin assignment. V2E2-0026 remains U, with original local/baseline mapping failures retained alongside later global/five-window support.

## Method and release

All **25 prospective files** were published at commit [`57b5af70c88a3a4ee5fe8f9224ac805a7c3c438a`](https://github.com/andersenmartin-blip/setisearch/commit/57b5af70c88a3a4ee5fe8f9224ac805a7c3c438a) and read back exactly before the run. The [publication receipt](../PROSPECTIVE_PUBLICATION_RECEIPT.json) binds both branch heads, file identities and 235,182 verified bytes. Receipt SHA256: `722f782797dd9c88a18f5a6efd87a01704727fcd3b726a476aa77faf13767a16`.

The unchanged [analysis plan](../analysis/PLAN.json) has SHA256 `6047736562d39b0ec3700af24136eeb30faad74f1edbf3070a863b5c0b6bbcbb`; the [root release](../analysis/ROOT_RELEASE.json) has SHA256 `ec7a6c547533e3e257135f7bceba01c45f11b6299a5c49187c727ff71e97c9af`. All 39 plan-bound source hashes remain exact. The runner checks the release/source bindings and rejects an existing output directory. The [preflight freeze](../PREFLIGHT_FREEZE.json) and pre-array audits remain unchanged.

## Exact archived input restoration

The [input inventory](../inputs/INPUT_INVENTORY.json), SHA256 `b986603788b89f6cedef36ca9167feef9c46a87287ace28009bc2655e2dea7cd`, binds **10 restored files**: seven merged FITS, one discovery ancillary TAR, one native-A FITS and one historical raw-context NPZ. No additional acquisition or duplicate source archive package is required.

Fresh header checks of all 72 native orders identify only order 19 as covering the original C007 center. Header coverage and same-exposure native/merged agreement do not retrospectively validate V2E2-0026's original local and baseline raw mapping. Those flags remain false alongside true global and later five-window diagnostics. [Input instructions](../inputs/README.md) retain full archive, member, unit and historical review details.

| Existing archive | Restored here | Original instructions and receipts |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH02_INPUTS_PART2_2026-11-01.zip` | One discovery ancillary TAR | [Saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/LIBRARY_INPUTS.json) |

The raw-context NPZ is restored from unchanged committed batch02 evidence parts. Full raw detector products remain in the existing archive and are not required for this broader-profile arithmetic.

In a separate reproduction checkout:

```sh
python3 work_harps_20261102_c007_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

The helper checks complete archives and member hashes, rejects differing destinations, preserves identical files and writes deterministic metadata. Its inspection is header-only and does not execute the comparison. Local cache paths do not affect the metadata. Full restored inputs and temporary input-panel copies are excluded from Git; completed compact evidence is preserved with the analysis.

## Preserve the completed record

Full reproduction belongs in a separate checkout with this phase's `analysis/results/` absent before its first run. Preserve the published inputs, method, code and root release unchanged and follow the [analysis instructions](../analysis/README.md). Do not reset the authoritative one-shot guard or overwrite completed outputs. Reproduction timestamps can differ; compare scientific arrays and numerical records.

The original U disposition, survey counts and prior analyses remain unchanged. This is a reproduction of one fixed contextual comparison, not authorization to choose new reference windows, fit extra parameters or infer an independent detection.
