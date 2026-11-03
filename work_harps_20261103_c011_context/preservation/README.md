# C011 / HD112410 preservation and reproduction

The fixed C011 run completed at **2026-11-03T13:12:26.297038+00:00**, with status `COMPLETE_FIXED_GROUP_CONTEXT`. It preserves nine bounded source windows, eighteen profiles in two fixed frames and both exact historical raw panels: **29 NPZ files totaling 336,009 bytes**.

| Saved evidence | Files | Total bytes | Exact filenames and SHA256 bindings |
|---|---:|---:|---|
| Seven HD112410 merged and two native-order source windows before interpolation | 9 | 75,925 | [BOUNDED_INPUT_INDEX.json](../analysis/results/BOUNDED_INPUT_INDEX.json) |
| Fourteen merged and four native frame profiles | 18 | 247,111 | [PROFILE_METRICS.json](../analysis/results/PROFILE_METRICS.json) |
| Original V2E2-0089 orders 2 and 3 raw panels | 2 | 12,973 | [PRESERVED_RAW_CONTEXT.json](../analysis/results/PRESERVED_RAW_CONTEXT.json) |

All **39 numerical files** in [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json) were rehashed while finalizing this document. All 29 NPZ files also match their separate index bindings; both raw copies match the original input bytes and hashes exactly. These checks preserve byte integrity without adding measurements. Figures and reports created later are outside the numerical-ledger count.

| Binding file | SHA256 |
|---|---|
| `analysis/results/OUTPUT_HASHES.json` | `b0911c6470e1ebe1103b8555925546207e2b96bb13bc395db5b92234f7fd4b7e` |
| `analysis/results/BOUNDED_INPUT_INDEX.json` | `dd0bc9d67b4ccf8d1bcadff7b9e8d7d6db334a2add80f110918994350fcb0106` |
| `analysis/results/PROFILE_METRICS.json` | `0b525cd9bc6c86ec1a0d1235a3694820d97ef30f9d7217e77abec6d87dd145ab` |
| `analysis/results/PRESERVED_RAW_CONTEXT.json` | `97a2c6f081c3c1ff0d152e0e36be1d4cc9d7d78ec12d1f37e2c6cf87c6d6b00c` |

## Complete support and retained low-reference flags

All **18 profile slots and 36 comparison slots** remain, including **four labelled identical-product self comparisons**. Every profile has 601/601 finite raw and normalized grid values and a valid positive fixed-flank reference. All 36 raw Pearson and 36 normalized RMS values pass the fixed evaluability gates. No source is raw-only, blocked or structurally excluded. Both native order-2 frame rows retain **true low-reference flags**; every other row's flag is false. The flagged rows remain in the complete arrays and comparisons.

| Profile group | Frame rows | Finite source samples in each fixed window | Finite left / right flank samples | Low-reference flag |
|---|---:|---|---|---|
| Seven merged observations | 14 | 600 except May 30 topocentric, 599 | 150 / 150 except May 30 topocentric, 149 / 150 | false |
| Native order 2 | 2 | 655 | 160 / 168 | **true** |
| Native order 3 | 2 | 534 | 132 / 136 | false |

Native order 2 has a positive pooled reference of **43.3865966796875** in unspecified native units in each frame, while order 3 has **109.76749420166016**. The fixed low-reference test compares a valid reference with three times its descriptive first-difference noise proxy; a true flag does not make a valid reference raw-only, remove samples or supply formal significance. Reference-flank medians remain descriptive levels rather than established line-free continua. Positive references and full coordinate support do not establish uniformly positive source samples or calibrated uncertainty.

## Signed source values and unavailable errors

Original signed samples remain intact. The May 28 merged observation retains **3/600 nonpositive samples** in each frame (0.5%); all its flank samples are positive. The other twelve merged frame rows have no nonpositive source samples in their fixed windows or flanks. These are two frame views of seven observations, not fourteen independent exposures.

Each native order-2 frame window retains **29/655 nonpositive original samples** (approximately 4.4275%), including **13/168 in the right flank** (approximately 7.7381%) and none among 160 left-flank samples. Each native order-3 frame window retains **3/534 nonpositive original samples** (approximately 0.5618%), with none in either flank. Original-sample counts differ from the 601-point interpolated grid and from saved bounded windows, which include interpolation brackets. The complete metrics preserve each per-frame count, sign, median, reference and quality flag; no clipping or sign change is applied.

Positive finite ERR support is absent in all eighteen profiles. Compact NPZs retain signed flux, original source indices and coordinates, frame-conversion information, available ERR samples, support and normalization status. Load arrays with `allow_pickle=False`. Neither the positive references, full support nor descriptive noise proxies supply formal uncertainty, significance, sensitivity or physical-origin discrimination. Native BUNIT is absent; merged ADU and unspecified native extracted scales are not a calibrated physical flux ratio. Original full FITS remain necessary for extraction-provenance checks.

## Target, dependence and historical evidence

This is **V2E2-0089 / original queue row 25 / R012**, at exactly **3865.6775000000002 Å**, with its original ±0.25 Å core and ±3 Å context. C011 follows completed C012 at queue row 24; numeric group order does not replace queue order. Its seven existing HD112410 observations run from April to August 2025 and span **21.30284860830273 km/s** in BERV. The sole reference was observed on **2025-05-28**, with BERV **−5.48386283255014 km/s**, defining the independently recomputed wavelength-specific topocentric anchor **3865.748213029564 Å**. No April reference or C010/C012 numeric anchor is transferred and no recentering occurs.

C011 and C012 reuse the same seven merged observing products. Their broad barycentric windows overlap on **[3866.2675, 3868.6775000000002] Å**, a width of **2.4100000000003092 Å**, so surrounding/reference pixels can be shared. The original C011 core [3865.4275000000002, 3865.9275000000002] Å lies entirely below C012's window. Their native/raw discovery products are different epochs: May 28 for C011 and April 29 for C012. C010's same-target window is disjoint. Numeric wavelength overlap with older HD106515A windows shares no observing products or source pixels. Original C011 epoch/profile and raw evidence already existed. This is dependent post-detection context; it adds no observing time, blind validation, independent detection or archive-wide completeness.

The fresh scan of all **72 order headers** selects orders 2 and 3, with no excluded covering orders. Both May native orders cover the complete original core, full context and both fixed flanks in both frames. Order 2 ends at 3870.000069396472 Å topocentric / 3869.9292785911125 Å barycentric, respectively more than 4.25 Å above the fixed centers. C012's partial order-2 coverage does not apply to this product and wavelength. Header geometry, finite flux and normalization quality remain separate conditions.

Both orders retain **true** global-grid, original local-usable, original baseline-verified and later five-window mapping diagnostics, verified from 0089's own historical records. C012's original order-2 local/baseline failures are not transferred. Supported mapping does not prove physical origin. All primary, secondary and root-adopted reviews remain **U**, describing broad native structure and diffuse central enhancement across both orders, with broad low-continuum, trace-confined raw enhancement. Both complete original panels, background/excess arrays, baseline arrays, native snippets, mapping stages and review text remain intact without a new fit, crop or subtraction. Neither profile correlation nor same-exposure extraction agreement changes the disposition or qualifies a laser candidate.

## Public method and release

All **25 prospective files** were published at commit [`dad9f542b6f7bb830f1020d373634012483e7b15`](https://github.com/andersenmartin-blip/setisearch/commit/dad9f542b6f7bb830f1020d373634012483e7b15) and read back exactly before execution. The [publication receipt](../PROSPECTIVE_PUBLICATION_RECEIPT.json) records both public branches and **339,201 verified bytes**. Receipt SHA256: `26e751119446bd57a3f6a320455836062db4f96df1ba788f43932b0cb347eb64`.

The unchanged [plan](../analysis/PLAN.json) has SHA256 `95aafe1f5985cdb57a112f787bfd3f999ff1cccf310905e85c25eb97fb4691a0`. The [root release](../analysis/ROOT_RELEASE.json), issued at **2026-11-03T13:12:16.062951+00:00**, has SHA256 `8aecc1e5cabf564c80a89771fc05bdd9bab53c3d15a886716b1f6515b9369d01`. All **50 plan-bound source hashes**, all **24 files bound by the root freeze**, and all 25 exact public-method file identities were checked unchanged while finalizing this note. The [preflight freeze](../PREFLIGHT_FREEZE.json) and prospective reviews preserve the pre-array contract.

The runner validates release and source hashes, performs the fixed comparison once and rejects an existing results directory. Preserve that guard and all completed outputs. The [independent reconstruction](../independent_audit/NUMERICAL_AUDIT.json) passed **481 checks across 71,203 scalar values**, covering all profiles, comparisons, bounded windows, both exact raw copies and self pairs without importing production functions. Audit report SHA256: `564a1e1c29810641c533bfbc3afb78793d44dda7bba4f7bb55a2bbdeebae14ab`. Computational reconstruction does not supply independent observations or a physical-origin conclusion.

## Recover exact archived inputs

The [input inventory](../inputs/INPUT_INVENTORY.json), SHA256 `287e3d994e1f94418f5ad07b373a3664da51987438a00773890df5f799968ba3`, binds **11 restored files**: seven target-specific merged FITS, one May discovery ancillary TAR, one native-A FITS and two historical raw-context NPZs. Both complete existing archives were reused only after verification against their original sizes and hashes. No live telescope/archive query or duplicate archive package was needed.

| Existing archive | Restored here | Original instructions and receipts |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven HD112410 merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART1_2026-11-01.zip` | May 2025 discovery ancillary product | [Saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json) |

Both original 0089 raw-context NPZs are reconstructed from unchanged committed batch03 evidence parts and cross-checked against the original mapping hashes. The saved result copies retain exact hashes `be55109e91d184ac18643e0598ec1e6bf6b53575c7b2c9c931ed0c32df4b7c79` (order 2) and `6dafe128d0cf145cbbd0ebdb936599eefbfe22422e98a939db9ec4451630b049` (order 3). Full raw detector products remain in the existing saved archive and are not extracted for this profile arithmetic. The [input instructions](../inputs/README.md) retain every archive/member identity, header convention and historical mapping qualification.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c011_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

One cache may hold both named archives. The helper verifies whole archives and selected members, rejects differing destinations, reuses identical files and writes deterministic metadata. It inspects FITS/NPY headers without executing the scientific comparison or making a network request. Local cache paths do not enter the metadata. Full restored inputs and temporary panel copies are excluded from Git; compact result evidence is retained with the analysis.

## Preserve the completed record

Reproduce in a separate checkout with this phase's `analysis/results/` absent before its first run, following the [analysis instructions](../analysis/README.md). Preserve the published input identities, code, method, root release and completed outputs. Do not reset the authoritative one-shot guard. Reproduction timestamps may differ; compare scientific arrays and numerical records.

All original U dispositions, review votes, mapping stages, survey counts and prior analyses remain unchanged. Reproduction of this fixed context does not authorize favorable-reference selection, shifted windows, extra fitted parameters or an independent-detection claim.
