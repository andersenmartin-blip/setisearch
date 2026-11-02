# C006 preservation and reproduction

The frozen C006 run completed at **2026-11-02T17:14:02.569765 UTC** with status `COMPLETE_FIXED_GROUP_CONTEXT`. It preserves nine bounded source windows, eighteen profiles in the two fixed frames and exact copies of all three historical raw panels: **30 NPZ files totaling 341,668 bytes**.

| Saved evidence | Files | Total bytes | Exact filenames and SHA256 bindings |
|---|---:|---:|---|
| Seven merged and two unique native source windows before interpolation | 9 | 75,943 | [BOUNDED_INPUT_INDEX.json](../analysis/results/BOUNDED_INPUT_INDEX.json) |
| Fourteen merged and four native frame profiles | 18 | 241,760 | [PROFILE_METRICS.json](../analysis/results/PROFILE_METRICS.json) |
| Separate historical panels for 0025, 0042 and 0043 | 3 | 23,965 | [PRESERVED_RAW_CONTEXT.json](../analysis/results/PRESERVED_RAW_CONTEXT.json) |

All **40 files** bound by the numerical [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json) were rehashed successfully while finalizing this document. All 30 NPZ files also match their separate index hashes; the three raw copies match the original input hashes exactly. These checks establish byte integrity, without new array interpretation or measurements. Later figures and reports lie outside this numerical-ledger count.

| Binding file | SHA256 |
|---|---|
| `analysis/results/OUTPUT_HASHES.json` | `7e044b1b3470c5248b755ced0be80a0be974f923293977a44972c5ebd4e393db` |
| `analysis/results/BOUNDED_INPUT_INDEX.json` | `d94756edf09b6e15d5dac9d395bb301adb2e936857e6b27b55729d8d08fddc58` |
| `analysis/results/PROFILE_METRICS.json` | `22d985e05d596187188a18587706404f20960628e01b2866390144897a016b19` |
| `analysis/results/PRESERVED_RAW_CONTEXT.json` | `2e7f4780473ffd47106f9a14efde7fea2e42673e5aaa9029cdf209e4817a6b4b` |

All eighteen profiles and 64 comparison slots are retained, including eight identical-product self comparisons. There are no raw-only normalization slots or blocked source profiles. The compact evidence preserves signed flux, source coordinates/indices, frame-conversion metadata, available ERR samples, coverage and normalization status. Read NPZ files with `allow_pickle=False`, retaining unavailable-error samples and all status information. The original full FITS remain necessary for extraction-provenance checks.

Three catalog records represent two unique discovery products. V2E2-0042 and V2E2-0043 share the 2022-12-31 exposure; preserving separate panels does not count overlapping raw pixels, repeated samples, or observing time as independent evidence. The seven merged epochs also reuse the original cohort. The next C007 group's proposed window overlaps this context, including a feature in C006's positive reference flank; preservation does not make those shared pixels independent.

## Method and release

All **25 prospective files** were published as commit [`e495c9fa6e59af1c3927a0b8a57767556eb30eff`](https://github.com/andersenmartin-blip/setisearch/commit/e495c9fa6e59af1c3927a0b8a57767556eb30eff) and read back byte-for-byte before the run. The [publication receipt](../PROSPECTIVE_PUBLICATION_RECEIPT.json) records both branch heads, individual file identities and 283,213 verified bytes. Its SHA256 is `e398ba3dc8957b932e116d2bc151018d358198ec61c5e964485ae223988d5c98`.

The unchanged [analysis plan](../analysis/PLAN.json) has SHA256 `fbb1334412e103c9991fac9681a71a5d0c6cf5f5acdab08dbf17825567fa0039`; the [root release](../analysis/ROOT_RELEASE.json) has SHA256 `497afcfdfc247f4da5cd53d531687d283156e63adbb48f363a1bb755a6e039f1`. The runner checks the fixed release/source bindings and rejects an existing output directory. The published [preflight freeze](../PREFLIGHT_FREEZE.json) and independent pre-array audits remain unchanged.

## Exact archived input restoration

This phase uses existing archived HD106515A inputs. No additional source upload or duplicate archive package is needed. The exact [input inventory](../inputs/INPUT_INVENTORY.json), SHA256 `8cfaa7ec00fe08600213ff385175c1a0cd113ca0352f140eaebbaa793086a0af`, binds 14 restored files: seven merged FITS, two ancillary TARs, two unique native-A FITS, and three saved native/raw NPZ panels.

All 72 native orders were checked from headers for each discovery product. Only order 19 covers the original C006 centers. Two unique product/order pairs retain all three original event identities and panels. V2E2-0042 and V2E2-0043 share a product; their panels and overlapping pixels do not represent independent exposures. V2E2-0025's original local/baseline mapping failures remain separately recorded from its later supported five-window gate. The two other events retain their full mapping history.

| Existing archive | Content restored here | Instructions and original receipts |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | All seven merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH02_INPUTS_PART2_2026-11-01.zip` | Both discovery ancillary TARs | [Saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/LIBRARY_INPUTS.json) |

Three raw-context NPZ files are restored from the unchanged committed batch02 evidence parts. Full raw detector products remain in those existing archives and are not necessary for this group's broader-profile arithmetic.

In a separate reproduction copy:

```sh
python3 work_harps_20261102_c006_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

The helper verifies complete archive/member hashes, rejects differing destinations, preserves identical files and generates deterministic metadata. Its inspection is header-only and does not execute the comparison. Local cache paths do not affect generated metadata. Restored full input products and the temporary input-panel copies are excluded from Git; the compact completed output evidence is preserved with the analysis.

## Preserve the completed record

Full reproduction belongs in a separate checkout with this phase's `analysis/results/` omitted before its first run. Keep the published inputs, method, code and root release unchanged, and follow the [analysis instructions](../analysis/README.md). Do not reset the authoritative one-shot guard or overwrite completed outputs. Timestamp-bearing receipts can differ in a reproduction; compare scientific arrays and numerical records.

No new observation or acquisition was added. All three U dispositions and earlier survey results remain unchanged. Reproduction checks this fixed contextual analysis; it does not create an independent detection or authorize new method variants.
