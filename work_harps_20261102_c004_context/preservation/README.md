# C004 preservation and reproduction

The fixed C004 run completed at **2026-11-02T18:34:34.883651+00:00**, with status `COMPLETE_FIXED_GROUP_CONTEXT`. It retains ten bounded source windows, twenty profiles in two fixed frames and three exact historical raw panels: **33 NPZ files totaling 381,864 bytes**.

| Saved evidence | Files | Total bytes | Exact filenames and SHA256 bindings |
|---|---:|---:|---|
| Seven merged and three native source windows before interpolation | 10 | 88,345 | [BOUNDED_INPUT_INDEX.json](../analysis/results/BOUNDED_INPUT_INDEX.json) |
| Fourteen merged and six native frame profiles | 20 | 272,621 | [PROFILE_METRICS.json](../analysis/results/PROFILE_METRICS.json) |
| Original V2E2-0028 / 0045 / 0052 order-3 raw panels | 3 | 20,898 | [PRESERVED_RAW_CONTEXT.json](../analysis/results/PRESERVED_RAW_CONTEXT.json) |

All **43 files** bound by [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json) were rehashed successfully while finalizing this document. All 33 NPZ files match their separate index hashes, and all three raw copies match the original input hashes exactly. These are byte-integrity checks, without new array interpretation or measurements. Later figures and reports are outside this numerical-ledger count.

| Binding file | SHA256 |
|---|---|
| `analysis/results/OUTPUT_HASHES.json` | `71f4d5cb11ec585ff2bd8984c7405b521432cdb7ef84f7b7d2ce898d4592b19b` |
| `analysis/results/BOUNDED_INPUT_INDEX.json` | `3b0e71085fe7668fddfa0bd321b6a46b8f1ea7ce44836efab87f8f1ab62ee227` |
| `analysis/results/PROFILE_METRICS.json` | `94b0080c0746e0c8ae6c31ceb4176b6b3daa86007380abe36da0a6bd7e1005b6` |
| `analysis/results/PRESERVED_RAW_CONTEXT.json` | `0c90e32d1e2a1c674fa64b6682dcdd714d290659038ce3a106c7781fed3aa67c` |

All twenty profiles and **96 comparison slots** remain, including **twelve identical-product self comparisons**. No source profiles are blocked or raw-only. All three distinct discovery references remain fixed and fully represented. Compact arrays preserve signed flux, original source indices and coordinates, fixed-frame conversion information, available ERR samples, support and normalization status. Load NPZs with `allow_pickle=False` and retain unavailable-error values and status information. Original full FITS remain necessary for extraction-provenance checks.

The C004 original core was already visible within the completed C003 positive reference flank. Conversely, C003's core structure lies inside the C004 negative reference flank. Both contexts therefore contain known neighboring structure in their fixed reference medians. The same seven observations are reused, so this context and any reproduction are neither blind validation nor independent observing time or detections. All three U labels remain unchanged. Historical global, local, baseline and later five-window mapping gates are true for all three records; these stages are preserved as earlier diagnostics, not promoted into new physical-origin validation.

## Method and release

All **25 prospective files** were published at commit [`7c3e46e41fc98073c844259ab91350b8363bc63a`](https://github.com/andersenmartin-blip/setisearch/commit/7c3e46e41fc98073c844259ab91350b8363bc63a) and read back exactly before execution. The [publication receipt](../PROSPECTIVE_PUBLICATION_RECEIPT.json) binds both public branch heads, file identities and **320,736 verified bytes**. Receipt SHA256: `4b80a8bf080a6b987332b2c661a95df1b0a95dac275f23e3ca83f06a1179425e`.

The unchanged [plan](../analysis/PLAN.json) has SHA256 `044cabc2adafd835cb4882afb506488752c6f0d91743ca564cc076a0031b1670`; the [root release](../analysis/ROOT_RELEASE.json) has SHA256 `6dba29aef505739cfd2e1f5e224aae0e415d7b24bd933810b08feefcfcc55fce`. All **46 plan-bound source hashes** remain exact. The comparison uses the first C004 discovery on 2022-03-07, BERV 10.77158288517 km/s, with fixed topocentric anchor 3872.1058747209718 Å. It does not inherit the January anchor of earlier groups. The runner checks release/source bindings and rejects an existing output directory. The [preflight freeze](../PREFLIGHT_FREEZE.json) and pre-array audit records remain unchanged.

## Exact archived input restoration

The [input inventory](../inputs/INPUT_INVENTORY.json), SHA256 `1be83dc6e3be2ca639de5a90f16bcff28081e591243c5d2f46160ecc2222607e`, binds **16 restored files**: seven merged FITS, three ancillary TARs, three native-A FITS and three historical raw-context NPZs. No extra acquisition or duplicate source-archive package is required.

Fresh header checks of all **216 native orders** identify only order 3 as covering each original C004 center. Those coordinate bounds and same-exposure extraction agreement do not establish usable flux, calibrated uncertainties or physical origin. The [input instructions](../inputs/README.md) retain all archive/member hashes, historical mapping stages, units, original review records and exact discovery identities.

| Existing archive | Restored here | Original instructions and receipts |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH02_INPUTS_PART2_2026-11-01.zip` | Discovery ancillary products | [Saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH02_INPUTS_PART3_2026-11-01.zip` | Remaining discovery ancillary products | Same saved-input instructions and registry |

The three raw-context NPZs are restored from unchanged committed batch02 evidence parts. Full raw detector products remain in those existing archives and are not required for the broader-profile arithmetic.

In a separate reproduction checkout:

```sh
python3 work_harps_20261102_c004_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

Each cache directory may hold multiple named archives. The helper verifies complete archives and member hashes, rejects differing destinations, retains identical files and writes deterministic metadata. It inspects FITS/NPY headers without executing the comparison. Local cache paths do not enter the metadata. Full restored inputs and temporary input-panel copies are excluded from Git; compact evidence is preserved with the completed analysis.

## Preserve the completed record

Reproduce only in a separate checkout with this phase's `analysis/results/` absent before its first run. Preserve the published inputs, method, code and root release, following the [analysis instructions](../analysis/README.md). Do not reset the authoritative one-shot guard or overwrite completed outputs. Reproduction timestamps can differ; compare scientific arrays and numerical records.

All original U dispositions, survey counts and prior analyses remain unchanged. Reproduction of this fixed context does not authorize favorable reference selection, shifted windows, extra fitted parameters or an independent-detection claim.
