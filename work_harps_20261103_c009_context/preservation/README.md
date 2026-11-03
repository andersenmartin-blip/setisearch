# C009 preservation and reproduction

The fixed C009 run completed at **2026-11-03T00:23:31.735455+00:00**, with status `COMPLETE_FIXED_GROUP_CONTEXT`. It retains eight bounded source windows, sixteen profiles in two fixed frames and the exact historical order-70 raw panel: **25 NPZ files totaling 276,753 bytes**.

| Saved evidence | Files | Total bytes | Exact filenames and SHA256 bindings |
|---|---:|---:|---|
| Seven merged and one native-order source window before interpolation | 8 | 59,844 | [BOUNDED_INPUT_INDEX.json](../analysis/results/BOUNDED_INPUT_INDEX.json) |
| Fourteen merged and two native frame profiles | 16 | 207,693 | [PROFILE_METRICS.json](../analysis/results/PROFILE_METRICS.json) |
| Original V2E2-0050 order-70 raw panel | 1 | 9,216 | [PRESERVED_RAW_CONTEXT.json](../analysis/results/PRESERVED_RAW_CONTEXT.json) |

All **35 files** bound by [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json) were rehashed successfully while finalizing this document. All 25 NPZ files match their separate index hashes, and the raw copy matches the original input hash exactly. These are byte-integrity checks without additional measurements. Later figures and reports are outside this numerical-ledger count.

| Binding file | SHA256 |
|---|---|
| `analysis/results/OUTPUT_HASHES.json` | `e5d70d3eee64a8cad5da96da257504af050462e5535269d6079ff857ae4b0bbb` |
| `analysis/results/BOUNDED_INPUT_INDEX.json` | `3a77207bff18629e76e5051ef9a285dcb11d9e635e62ade0ca3fbb299adefcef` |
| `analysis/results/PROFILE_METRICS.json` | `fd0090e11f7505006b08814c5a65fa5d4e5afdce95f3314daa28dbf09ce5ab1f` |
| `analysis/results/PRESERVED_RAW_CONTEXT.json` | `d96229ab234a8a1d17cd34cd81613a91362b4c2c216ca97a92ce66cf4d1b9aa1` |

All sixteen profiles and **32 comparison slots** remain, including **four identical-product self comparisons**. All sixteen profiles retain 601 finite raw and normalized grid values with valid positive fixed-flank references and false low-reference flags; there are no raw-only or blocked source slots. All source-window nonpositive fractions are zero. Positive finite ERR support is absent in every profile. Valid scaling and positive samples do not provide a calibrated uncertainty, significance or physical-origin test.

Compact arrays preserve signed flux, original source indices and coordinates, fixed-frame conversion information, available ERR samples, support and normalization status. Load NPZs with `allow_pickle=False` and retain unavailable-error values and status information. Original full FITS remain necessary for extraction-provenance checks. Native extracted units remain unspecified because `BUNIT` is absent; merged ADU and native scales are not a calibrated physical flux ratio.

C009's fixed [6799.02, 6805.02] Å window is disjoint from the completed C001–C008 bounded contexts. Nevertheless, the original epoch/profile and raw evidence already exist and all seven observing products are reused. Reproduction therefore adds neither blind validation nor independent observing time or detections. Fixed reference medians remain descriptive levels, not established line-free continua. The adopted U label remains unchanged. Primary A and secondary A provisional votes for the compact slanted concentration remain distinct from root adoption; the secondary review retained broader residual structure and could not exclude a spectral contribution. The unresolved possible artifact/spectral blend is preserved without assigning an origin or promoting a laser candidate.

The sole native covering order is 70, freshly determined from all 72 order headers. Its full context, core and both reference intervals are covered in both frames. Historical global, original local, original baseline and later five-window mapping gates are all true and retained distinctly. These are preserved historical diagnostics; no new detector registration or origin validation was performed.

## Method and release

All **25 prospective files** were published at commit [`d1405bf95678d8225c18dc869d0de4b45c2fec76`](https://github.com/andersenmartin-blip/setisearch/commit/d1405bf95678d8225c18dc869d0de4b45c2fec76) and read back exactly before execution. The [publication receipt](../PROSPECTIVE_PUBLICATION_RECEIPT.json) binds both public branch heads, file identities and **276,874 verified bytes**. Receipt SHA256: `b5057dbb81e450c13e3c0c8778770b6ef7fc1f76cede01714d51d9ad93cf23bd`.

The unchanged [plan](../analysis/PLAN.json) has SHA256 `b66a3428c61fd703d17526ce0642246f8262aa612f6cc1b68167dab2e92e0b66`; the [root release](../analysis/ROOT_RELEASE.json), issued at **2026-11-03T00:23:21.023422+00:00**, has SHA256 `4653b5a32add56e3651ef20004d6ff8deb3b1c4266daac9a99cd22251c740914`. All **46 plan-bound source hashes** remain exact. The comparison uses the sole C009 discovery observed on **2023-03-22**, BERV **3.26509772194068 km/s**, with fixed topocentric anchor **6801.945918689643 Å**. Earlier January, March 2022 and May 2022 anchors are not transferred, and the numeric C008 anchor wavelength is not reused. The runner checks release/source bindings and rejects an existing output directory. The [preflight freeze](../PREFLIGHT_FREEZE.json) and pre-array audit records remain unchanged.

The [independent numerical reconstruction](../independent_audit/NUMERICAL_AUDIT.json) passed **428 checks across 63,354 scalar values**, including all profiles, comparisons, source windows, the raw copy and self-pairs, without importing production functions. It verifies arithmetic and lineage, not a physical-origin conclusion or independent observing evidence.

## Exact archived input restoration

The [input inventory](../inputs/INPUT_INVENTORY.json), SHA256 `961a3b767b16441bac13c260b5ff44254282788caea34f69ceb8f1ffd3ddd9e3`, binds **10 restored files**: seven merged FITS, one ancillary TAR, one native-A FITS and one historical raw-context NPZ. No extra acquisition or duplicate source-archive package is required. The [input instructions](../inputs/README.md) retain archive/member hashes, fresh 72-order header coverage, original review records, units and exact discovery identities.

| Existing archive | Restored here | Original instructions and receipts |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH02_INPUTS_PART3_2026-11-01.zip` | March 2023 discovery ancillary product | [Saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/LIBRARY_INPUTS.json) |

The historical raw-context NPZ is restored from unchanged committed batch02 evidence parts. Full raw detector products remain in the existing archive and are not required for the broader-profile arithmetic.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c009_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

One cache may hold both named archives. The helper verifies complete archives and member hashes, rejects differing destinations, retains identical files and writes deterministic metadata. It inspects FITS/NPY headers without executing the comparison. Local cache paths do not enter the metadata. Full restored inputs and temporary input-panel copies are excluded from Git; compact evidence is preserved with the completed analysis.

## Preserve the completed record

Reproduce only in a separate checkout with this phase's `analysis/results/` absent before its first run. Preserve the published inputs, method, code and root release, following the [analysis instructions](../analysis/README.md). Do not reset the authoritative one-shot guard or overwrite completed outputs. Reproduction timestamps can differ; compare scientific arrays and numerical records.

All adopted U dispositions, the original primary and secondary review votes, survey counts and prior analyses remain unchanged. Reproduction of this fixed context does not authorize favorable reference selection, shifted windows, extra fitted parameters or an independent-detection claim.
