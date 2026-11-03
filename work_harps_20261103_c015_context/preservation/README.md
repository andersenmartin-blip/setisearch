# C015 / HD114386 preservation and reproduction

The fixed C015 run completed at **2026-11-03T14:54:01.893783+00:00**, with status `COMPLETE_FIXED_GROUP_CONTEXT`. It preserves eight bounded source windows, sixteen profiles in two fixed frames and the exact original raw panel: **25 NPZ files totaling 288,991 bytes**.

| Saved evidence | Files | Total bytes | Exact filenames and SHA256 bindings |
|---|---:|---:|---|
| Seven HD114386 merged and one native-order source window before interpolation | 8 | 64,659 | [BOUNDED_INPUT_INDEX.json](../analysis/results/BOUNDED_INPUT_INDEX.json) |
| Fourteen merged and two native frame profiles | 16 | 217,479 | [PROFILE_METRICS.json](../analysis/results/PROFILE_METRICS.json) |
| Original V2E2-0095 order-3 raw panel | 1 | 6,853 | [PRESERVED_RAW_CONTEXT.json](../analysis/results/PRESERVED_RAW_CONTEXT.json) |

All **35 numerical files** in [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json) were rehashed while finalizing this document. All 25 NPZ files also match their separate index bindings; the raw copy matches the original input bytes and hash exactly. These checks preserve byte integrity without adding measurements. Figures and reports created later are outside the numerical-ledger count.

| Binding file | SHA256 |
|---|---|
| `analysis/results/OUTPUT_HASHES.json` | `612a2600752381d35c8895cd8176d39c72c19795bf18ce65fe720472e97eebab` |
| `analysis/results/BOUNDED_INPUT_INDEX.json` | `b2b8ad9a9d7a5ec6880bc07228c98b1006576ec8c6ba12a4c8522767cea6e746` |
| `analysis/results/PROFILE_METRICS.json` | `f4209678f16eccb1914fa4d593800699ca296b06f812289e533e682f9073ed4d` |
| `analysis/results/PRESERVED_RAW_CONTEXT.json` | `e0d587e00b24bb8fcc689569b2166455275e26f8edd8a6e46f555472e1b5b7b7` |

## Complete support, signed samples and quality

All **16 profile slots and 32 comparison slots** remain, including **four labelled identical-product self comparisons**. Every profile has 601/601 finite raw and normalized grid values, a valid positive fixed-flank reference and a false low-reference flag. All 32 raw Pearson and 32 normalized RMS values pass the fixed evaluability gates. No source is raw-only, blocked or structurally excluded; no grid value is masked for an interpolation gap or outside native coverage.

Each merged frame window contains 600 finite original samples, with 150 finite originals in each flank. The **2023-01-02 merged observation** retains **1/600 nonpositive window samples** (approximately 0.1667%) in each frame, including **1/150 in its right flank** (approximately 0.6667%); its left flank has none. The other twelve merged frame rows have no nonpositive source samples in their fixed windows or flanks. These fourteen rows are two frame views of seven observations, not fourteen independent exposures.

Each native order-3 frame window contains **550 finite original samples**, with **135 left-flank and 140 right-flank samples**. All those fixed-window and flank samples are positive. Its pooled reference is **200.03173828125** in unspecified native units in each frame; both low-reference flags are false. Positive references do not make the January merged source sample positive: every original sign and count remains intact without clipping or sign change. Original-sample counts differ from the 601-point interpolated grid and from the saved bounded windows, which include interpolation brackets. Complete per-frame metrics retain all counts, medians, reference values, noise proxies and quality flags.

Positive finite ERR support is absent in all sixteen profiles. Compact NPZs retain signed flux, original source indices and coordinates, frame-conversion information, available ERR samples, support and normalization status. Load arrays with `allow_pickle=False`. Positive references, false low-reference flags and complete support do not establish calibrated uncertainty, formal significance, sensitivity, a physical origin or a qualified survey null. Fixed-flank medians remain descriptive reference levels rather than established line-free continua. Native BUNIT is absent; merged ADU and unspecified native extracted scales are not a calibrated physical flux ratio. Full original FITS remain necessary for extraction-provenance checks.

## One May reference and seven reused observations

This is **V2E2-0095 / original queue row 28 / C015 / R016**, at exactly **3869.915 Å**, with the original ±0.25 Å core [3869.665, 3870.165] Å and fixed ±3 Å context [3866.915, 3872.915] Å. It follows the completed four-member C016 joint route; numeric group order does not replace original queue membership. The sole reference was observed on **2022-05-16T02:17:40.312**, under publication ID `ADP.2022-05-17T01:02:16.724`, with BERV **−10.767337430651 km/s**. Its independently recomputed wavelength-specific topocentric anchor is **3870.0539967497375 Å**. No reference selection, recentering, C016 midpoint, March anchor, four-reference joint design or order-19 scope is transferred.

The same seven existing **HD114386** observations run from January 2022 through August 2023 and span **51.572001697156 km/s** in BERV. The 28 merged comparison slots are seven observations × one fixed May reference × two frames × two regions, including four identical-product self rows. The other four slots are same-exposure native-to-merged comparisons from the May product, not additional observations or independent confirmation. Slot counts do not increase the seven-observation evidence base.

The May product was already one of C016's four discovery references. C015's bounded window is disjoint from C016's [4300.7875, 4306.7875] Å context and the completed [0092/0104 blue normalization windows](../../work_harps_20261101/v2/extension02/normalization_context_20261102/README.md). Those completed normalization routes remain skipped rather than replayed. Original C015 epoch/profile and raw evidence already existed. Numerical wavelength overlaps with earlier HD106515A C002/C003/C004 and HD112410 C011/C012 contexts share no observing products or source pixels because those are different targets. Reusing the HD114386 observations makes this dependent post-detection context; it adds no observing time, blind validation, independent detection or archive-wide completeness.

## Native geometry and historical evidence

The fresh scan of **all 72 May native order headers** selects **order 3 only**, covering the full original core, fixed context and both reference flanks in both frames. Its topocentric endpoints are 3851.27166904696 to 3894.4973838317906 Å; barycentric endpoints are 3851.1333468827725 to 3894.3575091740545 Å. Adjacent order 2 ends at 3870.006986547364 Å topocentric, below the original center; it is not a covering order or an excluded covering-context slot. Header geometry, finite flux and normalization quality remain distinct conditions. Exact per-order coefficients, all 72 scan records and original raw coordinates remain in the [input inventory](../inputs/INPUT_INVENTORY.json).

The own original order-3 context retains **true** global-grid, original local-usable, original baseline-verified and later five-window mapping diagnostics. Other targets' mapping limits and another blue normalization raw-window registration discrepancy are not transferred here. Supported historical mapping does not prove physical origin. Primary, secondary and root-adopted reviews remain **U/U/U**, describing a broad native feature spanning many dispersion samples and smooth diffuse trace-associated raw enhancement without a distinct charge track. The complete original raw panel, background/excess arrays, baseline arrays, native snippets, mapping stages and review text remain intact without a new fit, crop or subtraction. Neither profile correlation nor same-exposure extraction agreement changes the disposition or qualifies a laser candidate.

## Public method and release

All **25 prospective files** were published at commit [`622447cb88946e3e2f0020dc7dc59c99c081b11b`](https://github.com/andersenmartin-blip/setisearch/commit/622447cb88946e3e2f0020dc7dc59c99c081b11b) and read back exactly before execution. The [publication receipt](../PROSPECTIVE_PUBLICATION_RECEIPT.json) records both public branches and **360,818 verified bytes**. Receipt SHA256: `1616d2455b7bbd5cdcb353fc77bb55f98134b2a65f6b4479012e7af683e0f3b4`.

The unchanged [plan](../analysis/PLAN.json) has SHA256 `8f1bab6cd274e703d96d4a707b6ef189fb0ca1c13e5d977ed8d65bd6916fc3a4`. The [root release](../analysis/ROOT_RELEASE.json), issued at **2026-11-03T14:53:48.612867+00:00**, has SHA256 `bdb44f15409073fec3fc7091fe027b58b575b74a2d3fc45990885a99a25eed66`. All **56 plan-bound source hashes**, all **24 files bound by the root freeze**, and all 25 exact public-method file identities were checked unchanged while finalizing this note. The [preflight freeze](../PREFLIGHT_FREEZE.json) and prospective reviews preserve the pre-array contract.

The runner validates release and source hashes, performs the fixed comparison once and rejects an existing results directory. Preserve that guard and all completed outputs. The [independent reconstruction](../independent_audit/NUMERICAL_AUDIT.json) passed **455 checks across 63,724 scalar values**, covering every profile, comparison, bounded window, the exact raw copy and self pairs without importing production functions. Audit report SHA256: `606a81c9ffd50563861f24eb1e3ec6680acdf2649a03b59e4005fd64d7c35cca`. Computational reconstruction does not supply independent observations or a physical-origin conclusion.

## Recover exact archived inputs

The [input inventory](../inputs/INPUT_INVENTORY.json), SHA256 `ef6ca3750128fd47fc96f5b7eca83877fb2d96cb7d5780008f3467d3c5376987`, binds **10 restored files**: seven target-specific merged FITS, one May discovery ancillary TAR, one native-A FITS and one historical raw-context NPZ. Both complete existing archives were reused from exact caches only after verification against their original sizes and hashes. No new file transfer, live telescope/archive query or duplicate archive package was needed.

| Existing archive | Restored here | Original instructions and receipts |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven HD114386 merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART2_2026-11-01.zip` | May 2022 discovery ancillary product | [Saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json) |

The original 0095 order-3 raw-context NPZ is reconstructed from unchanged committed batch03 evidence parts and cross-checked against the original mapping hash. Its saved result copy retains exactly **6,853 bytes**, SHA256 `2940f494ab65835f39b2a06aa879d47b7fc46c01bc4fc14eaa42921e98b53bba`. Full raw detector products remain in the existing saved archive and are not extracted for this profile arithmetic. The [input instructions](../inputs/README.md) retain every archive/member identity, header convention and historical mapping qualification.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c015_context/inputs/restore_inputs.py \
  --archive-dir /path/to/merged/archive/cache \
  --archive-dir /path/to/native/archive/cache
```

One cache may hold both archives. The helper verifies whole archives and selected members, rejects differing destinations, reuses identical files and writes deterministic metadata. It inspects FITS/NPY headers without executing the scientific comparison or making a network request. Local cache paths do not enter the metadata. Full restored inputs and the temporary panel copy are excluded from Git; compact result evidence is retained with the analysis.

## Preserve the completed record

Reproduce in a separate checkout with this phase's `analysis/results/` absent before its first run, following the [analysis instructions](../analysis/README.md). Preserve the published input identities, code, method, root release and completed outputs. Do not reset the authoritative one-shot guard. Reproduction timestamps may differ; compare scientific arrays and numerical records.

All original U dispositions, review votes, mapping stages, survey counts and prior analyses remain unchanged. Reproduction of this fixed context does not authorize favorable-reference selection, shifted windows, extra fitted parameters or an independent-detection claim.
