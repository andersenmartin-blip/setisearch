# C012 / HD112410 preservation and reproduction

The fixed C012 run completed at **2026-11-03T12:44:19.073203+00:00**, with status `COMPLETE_FIXED_GROUP_CONTEXT`. It preserves nine bounded source windows, eighteen profiles in two fixed frames and both exact historical raw panels: **29 NPZ files totaling 317,583 bytes**.

| Saved evidence | Files | Total bytes | Exact filenames and SHA256 bindings |
|---|---:|---:|---|
| Seven HD112410 merged and two native-order source windows before interpolation | 9 | 72,224 | [BOUNDED_INPUT_INDEX.json](../analysis/results/BOUNDED_INPUT_INDEX.json) |
| Fourteen merged and four native frame profiles | 18 | 232,224 | [PROFILE_METRICS.json](../analysis/results/PROFILE_METRICS.json) |
| Original V2E2-0087 orders 2 and 3 raw panels | 2 | 13,135 | [PRESERVED_RAW_CONTEXT.json](../analysis/results/PRESERVED_RAW_CONTEXT.json) |

All **39 numerical files** in [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json) were rehashed while finalizing this document. All 29 NPZ files also match their separate index bindings; both raw copies match the original input bytes and hashes exactly. These checks preserve byte integrity without adding measurements. Figures and reports created later are outside the numerical-ledger count.

| Binding file | SHA256 |
|---|---|
| `analysis/results/OUTPUT_HASHES.json` | `d28f98192a5e4483b9ee20f4c99223a87aaf3efb390dbca8b697133a45c64175` |
| `analysis/results/BOUNDED_INPUT_INDEX.json` | `978a1fba04f322f19be721576dce74248edd812e1553b248fdb22a60dd784891` |
| `analysis/results/PROFILE_METRICS.json` | `9f0c81fc22b8920e204534d9b99cced8eb7881262146ef6fd179dc63956f3192` |
| `analysis/results/PRESERVED_RAW_CONTEXT.json` | `c60b8fc14637be5f0d8318b5454ff03f470a588dcb9fea0323659ed83e8f6c4a` |

## Complete support and missing coverage

All **18 profile slots and 36 comparison slots** remain, including **four labelled identical-product self comparisons**. There are two raw-only normalization slots, both native order 2, and no blocked source profiles or structurally excluded orders. The fixed gates allow 34 raw Pearson and 32 normalized RMS values; missing outcomes retain their records and explicit reasons.

| Profile group | Frame rows | Finite raw grid values per row | Finite normalized grid values per row | Fixed-flank outcome |
|---|---:|---:|---:|---|
| Seven merged observations | 14 | 601/601 | 601/601 | Valid positive pooled references; low-reference flags false |
| Native order 2 | 2 | 378/601 | 0/601 | `RAW_ONLY`, `MISSING_RIGHT_FLANK_COVERAGE`; valid reference and low-reference flag unavailable |
| Native order 3 | 2 | 601/601 | 601/601 | Valid positive pooled reference; low-reference flags false |

Order 2 retains 51/51 common core samples and raw core Pearson values in both frames. Its 327/550 broad-pattern samples fail the fixed minimum of 440, so both broad raw Pearson values remain unavailable. All four order-2 normalized RMS slots remain unavailable. The missing positive flank is a coverage limit, not a measured nonpositive two-flank reference: each frame has 166 finite left-flank source samples and zero right-flank samples. Its available one-sided median, 89.04349136352539 in unspecified native units, remains descriptive and is never substituted for valid two-flank normalization. No flank is moved or borrowed from order 3; no extrapolation fills the 223 unsupported grid values.

## Signed source values and unavailable errors

Original signed samples remain intact. Each merged frame window contains 600 finite original samples except the June 22 observation's topocentric window, which contains 599. The May 28 observation has 3/600 nonpositive samples in each frame (0.5%), including 3/150 in its left flank (2%); its right flank has none. The other twelve merged frame rows have no nonpositive samples in their fixed windows or flanks. These are two frame views of seven observations, not fourteen independent exposures.

Each native order-2 frame window retains 2/423 nonpositive original samples (approximately 0.4728%), including 1/166 in its available left flank (approximately 0.6024%); the absent right flank has no fraction. Each native order-3 frame window has 546 finite original samples, with no nonpositive values, and finite flank counts of 134 left and 139 right. Original-sample counts differ from interpolated grid support and from saved bounded windows, which include interpolation brackets. The full per-frame metrics retain every count, sign, median and unavailable result.

Positive finite ERR support is absent in all eighteen profiles. Compact NPZs retain signed flux, original source indices and coordinates, frame-conversion information, available ERR samples, support and normalization status. Load arrays with `allow_pickle=False`. Positive references, false low-reference flags and complete support in some rows do not supply calibrated uncertainty, significance, sensitivity or physical-origin discrimination. Native BUNIT is absent; merged ADU and unspecified native extracted scales are not a calibrated physical flux ratio. Original full FITS remain necessary for extraction-provenance checks.

## Target, geometry and historical evidence

This is **V2E2-0087 / original queue row 24 / R013**, at exactly **3869.2675 Å**, with its original ±0.25 Å core and ±3 Å context. Its seven existing HD112410 observations run from April to August 2025 and span **21.30284860830273 km/s** in BERV. The sole reference was observed on **2025-04-29**, with BERV **3.40485846065643 km/s**, defining the freshly recomputed wavelength-specific topocentric anchor **3869.2235557371996 Å**. No recentering or C010 numeric-anchor transfer occurs.

C010 shares the same seven HD112410 observations but has a disjoint wavelength window. Numeric wavelength overlap with older HD106515A C002/C003/C004 windows shares no observations or source pixels. Original epoch/profile and raw evidence for 0087 already existed. This bounded context adds no observing time, blind validation or independent detection. Fixed reference-flank medians remain descriptive levels rather than established line-free continua.

The fresh scan of all **72 order headers** selects orders 2 and 3, with no excluded covering orders. Both cover the complete original core. Order 2 ends at 3869.9999605859994 Å topocentric / 3870.0439136667287 Å barycentric, leaving its entire positive normalization flank outside the order in both frames. Order 3 covers the full context and both flanks. Header coverage, finite flux and valid normalization remain separate conditions.

Historical order 2 global-grid and later five-window diagnostics are true, while its original local-usable and baseline-verified diagnostics remain **false**. Order 3 retains true diagnostics at every historical stage. Later support does not repair original raw-registration limits. All primary, secondary and root-adopted reviews remain **U**, describing broad enhancement shared by orders 2 and 3, noisier order 2, smoother order 3 and trace-associated raw structure. Both complete original panels, background/excess arrays, baseline arrays, mapping stages and review text remain preserved without a new fit, crop or subtraction. Neither profile correlation nor same-exposure extraction agreement changes the disposition.

## Public method and release

All **25 prospective files** were published at commit [`3815808d874c9cf927da83dc287631e18de3bdd4`](https://github.com/andersenmartin-blip/setisearch/commit/3815808d874c9cf927da83dc287631e18de3bdd4) and read back exactly before execution. The [publication receipt](../PROSPECTIVE_PUBLICATION_RECEIPT.json) records both public branches and **320,586 verified bytes**. Receipt SHA256: `a23064f055adbfa4b26322f1a50905e4e5828d054a0883ded8facc2196876b66`.

The unchanged [plan](../analysis/PLAN.json) has SHA256 `247b79d76ef2129f4cf369ec6dd5e188d25a827c7c2d6f627d560942cd087aee`. The [root release](../analysis/ROOT_RELEASE.json), issued at **2026-11-03T12:44:09.849804+00:00**, has SHA256 `492768bbe412cd37367e82a87cc6a1411202c72dfe88ade59d9fbaa229c1663b`. All **49 plan-bound source hashes**, all **24 files bound by the root freeze**, and all 25 exact public-method file identities were checked unchanged while finalizing this note. The [preflight freeze](../PREFLIGHT_FREEZE.json) and prospective reviews preserve the pre-array contract.

The runner validates release and source hashes, performs the fixed comparison once and rejects an existing results directory. Preserve that guard and all completed outputs. The [independent reconstruction](../independent_audit/NUMERICAL_AUDIT.json) passed **481 checks across 70,371 scalar values**, covering all profiles, comparisons, bounded windows, both exact raw copies and self pairs without importing production functions. Audit report SHA256: `b8191ba18b2393ff03dd81f058e5571826fd0d3b9fcbb2a441f112891dbaa742`. Computational reconstruction does not supply independent observations or a physical-origin conclusion.

## Recover exact archived inputs

The [input inventory](../inputs/INPUT_INVENTORY.json), SHA256 `236ba3e633ebb1c1af464f8cb6fd51fc57ea7ee9fdf2d7f0a641e1cdafd90f26`, binds **11 restored files**: seven target-specific merged FITS, one discovery ancillary TAR, one native-A FITS and two historical raw-context NPZs. Both complete existing archives were reused only after verification against their original sizes and hashes. No live telescope/archive query or duplicate archive package was needed.

| Existing archive | Restored here | Original instructions and receipts |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven HD112410 merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART1_2026-11-01.zip` | April 2025 discovery ancillary product | [Saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json) |

The two original 0087 raw-context NPZs are reconstructed from unchanged committed batch03 evidence parts and cross-checked against the original mapping hashes. The saved result copies retain the exact hashes `9652f936f9b6ec7c442a0ac98268c3465e0da9f3e26d284c90e71011e0998970` (order 2) and `2a4ed269477a0b3bb6ed304853448a582896117f73835f09a06766edc49d792e` (order 3). Full raw detector products remain in the existing saved archive and are not extracted for this profile arithmetic. The [input instructions](../inputs/README.md) retain every archive/member identity, header convention and historical mapping qualification.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c012_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

One cache may hold both named archives. The helper verifies whole archives and selected members, rejects differing destinations, reuses identical files and writes deterministic metadata. It inspects FITS/NPY headers without executing the scientific comparison or making a network request. Local cache paths do not enter the metadata. Full restored inputs and temporary panel copies are excluded from Git; compact result evidence is retained with the analysis.

## Preserve the completed record

Reproduce in a separate checkout with this phase's `analysis/results/` absent before its first run, following the [analysis instructions](../analysis/README.md). Preserve the published input identities, code, method, root release and completed outputs. Do not reset the authoritative one-shot guard. Reproduction timestamps may differ; compare scientific arrays and numerical records.

All original U dispositions, review votes, mapping stages, survey counts and prior analyses remain unchanged. Reproduction of this fixed context does not authorize favorable-reference selection, shifted windows, extra fitted parameters or an independent-detection claim.
