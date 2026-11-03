# C016 / HD114386 preservation and reproduction

The fixed C016 run completed at **2026-11-03T14:18:14.637881+00:00**, with status `COMPLETE_FIXED_GROUP_CONTEXT`. It preserves eleven bounded source windows, twenty-two profiles in two fixed frames and all four exact historical raw panels: **37 NPZ files totaling 432,482 bytes**.

| Saved evidence | Files | Total bytes | Exact filenames and SHA256 bindings |
|---|---:|---:|---|
| Seven HD114386 merged and four native-order source windows before interpolation | 11 | 96,080 | [BOUNDED_INPUT_INDEX.json](../analysis/results/BOUNDED_INPUT_INDEX.json) |
| Fourteen merged and eight native frame profiles | 22 | 305,218 | [PROFILE_METRICS.json](../analysis/results/PROFILE_METRICS.json) |
| Original 0094/0096/0098/0110 order-19 raw panels | 4 | 31,184 | [PRESERVED_RAW_CONTEXT.json](../analysis/results/PRESERVED_RAW_CONTEXT.json) |

All **47 numerical files** in [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json) were rehashed while finalizing this document. All 37 NPZ files also match their separate index bindings; all four raw copies match the original input bytes and hashes exactly. These checks preserve byte integrity without adding measurements. Figures and reports created later are outside the numerical-ledger count.

| Binding file | SHA256 |
|---|---|
| `analysis/results/OUTPUT_HASHES.json` | `ebc83d56a37b575a85386b94b3202bd79da99b1068ea3725ffba7c5d700b3d0e` |
| `analysis/results/BOUNDED_INPUT_INDEX.json` | `717f82677e5a3fc7294b129f0f410cc2f78db3dd8092b8d3b914f7ce261286fd` |
| `analysis/results/PROFILE_METRICS.json` | `5fe96ad5c03b60f597e4a22741029ce376157c4347c8b7a57ec7cd27833be96e` |
| `analysis/results/PRESERVED_RAW_CONTEXT.json` | `af228ed3fa7a1a2ed62cffdc410e3aa6ebac9fbaffcb780f01c42cf34cfe8259` |

## Complete support, signed samples and quality

All **22 profile slots and 128 comparison slots** remain, including **16 labelled identical-product self comparisons**. Every profile has 601/601 finite raw and normalized grid values, a valid positive fixed-flank reference and a false low-reference flag. All 128 raw Pearson and 128 normalized RMS values pass the fixed evaluability gates. No source is raw-only, blocked or structurally excluded; no grid value is masked for an interpolation gap or outside native coverage.

The finite original samples inside every fixed window and reference flank are positive: all window/left-flank/right-flank nonpositive fractions are zero. Every merged frame window has 600 finite original samples, with 150 finite originals in each flank. The eight native frame rows retain their own original-sample counts:

| Discovery event / order | Finite window samples B/T | Finite left / right flank samples, barycentric | Finite left / right flank samples, topocentric |
|---|---|---|---|
| 0094 / 19 | 486 / 486 | 120 / 124 | 120 / 124 |
| 0096 / 19 | 487 / 486 | 120 / 123 | 120 / 124 |
| 0098 / 19 | 485 / 486 | 120 / 123 | 120 / 123 |
| 0110 / 19 | 488 / 486 | 121 / 124 | 120 / 123 |

These are two frame views of four discovery products; fourteen merged frame rows are two views of seven observations. Original-sample counts differ from the 601-point interpolated grid and from the saved bounded source windows, which include interpolation brackets. The complete metrics retain the signed source values, finite counts, medians, references, noise proxies and quality flags. No clipping, sign change, favorable-reference selection or window adjustment is applied.

Positive finite ERR support is absent in all twenty-two profiles. Compact NPZs retain signed flux, original source indices and coordinates, frame-conversion information, available ERR samples, support and normalization status. Load arrays with `allow_pickle=False`. Positive source samples and references, false low-reference flags and complete support do not establish calibrated uncertainty, formal significance, sensitivity, a physical origin or a qualified survey null. Fixed-flank medians remain descriptive reference levels rather than established line-free continua. Native BUNIT is absent; merged ADU and unspecified native extracted scales are not a calibrated physical flux ratio. Full original FITS remain necessary for extraction-provenance checks.

## Seven observations, four fixed references

C016 / R017 keeps **V2E2-0094, 0096, 0098 and 0110** together at original queue rows **27, 29, 30 and 32**. Each of the four distinct discovery products remains a fixed reference; none is selected by its resulting comparison values. The original member centers are **4303.785 Å** for the first three and **4303.79 Å** for 0110. The common center **4303.7875 Å** is the midpoint of those extremes, not a fitted peak. Its fixed ±3 Å context is [4300.7875, 4306.7875] Å and common ±0.25 Å core [4303.5375, 4304.0375] Å. Exact individual centers and their original cores remain distinct catalog information.

The first original queue member, 0094, fixes one common topocentric group anchor **4303.512448784194 Å**, using its own March discovery BERV **19.1606928163471 km/s**. It was observed on **2022-03-07**, under publication ID `ADP.2022-03-08T01:01:37.348`. Other references do not redefine the anchor. Original event-specific topocentric catalog centers remain separate metadata, checked using each product's own BERV; neither those event markers nor the other references recenter the common comparison.

The target is **HD114386**, with its own seven existing observations from January 2022 through August 2023 and BERV span **51.572001697156 km/s**. No HD112410 products, numeric anchor, May 2025 reference, BERV span or quality outcome is transferred. The 112 merged comparison slots are seven observations × four fixed references × two frames × two regions. Within each frame/region, four of the 28 rows are identical-product self comparisons and 24 are nonself rows, **four references × six other observations**. Reciprocal and shared-reference comparisons reuse observations and pixels. The remaining 16 comparisons are same-exposure native-to-merged rows from four discovery products, not additional observations or independent confirmation. Computational slot counts therefore do not increase the seven-observation evidence base.

Original C016 epoch/profile and raw evidence already existed. A completed [blue normalization context](../../work_harps_20261101/v2/extension02/normalization_context_20261102/README.md) also used these same HD114386 observations at different blue wavelengths. It completed the 0092/C013 and 0104/C014 normalization routes; those diagnostics are skipped rather than replayed. That work does not complete C016's distinct joint-profile route or supply independent observing evidence. The C016 bounded window is disjoint from completed C001–C012 group windows. This is dependent post-detection context, adding no observing time, blind validation, independent detection or archive-wide completeness.

## Native geometry and historical evidence

Fresh scans of **all 72 order headers in each of four native products**, 288 rows in total, select **order 19 only** for each discovery. All four products cover the full common context, core and both fixed normalization flanks in both frames. Header geometry, finite flux and normalization quality remain distinct conditions. Product-specific coefficients, exact endpoints, original member topocentric centers and raw coordinates remain in the [input inventory](../inputs/INPUT_INVENTORY.json).

Every own original order-19 context retains **true** global-grid, original local-usable, original baseline-verified and later five-window mapping diagnostics. The later 0092 raw-window registration discrepancy in another blue normalization context is local to that evidence and is not transferred here. Supported mapping does not prove physical origin. Every primary, secondary and root-adopted review remains **U/U/U**, describing broad rounded native features, nearby shoulders or secondary structure and weak diffuse trace-associated raw enhancement. All four complete original panels, background/excess arrays, baseline arrays, native snippets, mapping stages and review text remain intact without a new fit, crop or subtraction. Neither profile correlation nor same-exposure extraction agreement changes any disposition or qualifies a laser candidate.

## Public method and release

All **25 prospective files** were published at commit [`d4283a5d145d747081058783f31826c8e4531837`](https://github.com/andersenmartin-blip/setisearch/commit/d4283a5d145d747081058783f31826c8e4531837) and read back exactly before execution. The [publication receipt](../PROSPECTIVE_PUBLICATION_RECEIPT.json) records both public branches and **533,738 verified bytes**. Receipt SHA256: `0264ad41ed4a1e85faed233f2f2afb5b6d93a680c11a5d68500ce8f05a83dd8a`.

The unchanged [plan](../analysis/PLAN.json) has SHA256 `1df97d5a7b8d147b22a5003812c7da4e6321d4e00c6484cb2c332732d8036f55`. The [root release](../analysis/ROOT_RELEASE.json), issued at **2026-11-03T14:17:48.238794+00:00**, has SHA256 `57f9d43229a0ca9194404ab8d7c81ac404459c9c7fb55bf7d333c7f087939171`. All **64 plan-bound source hashes**, all **24 files bound by the root freeze**, and all 25 exact public-method file identities were checked unchanged while finalizing this note. The [preflight freeze](../PREFLIGHT_FREEZE.json) and prospective reviews preserve the pre-array contract.

The runner validates release and source hashes, performs the fixed comparison once and rejects an existing results directory. Preserve that guard and all completed outputs. The [independent reconstruction](../independent_audit/NUMERICAL_AUDIT.json) passed **700 checks across 86,525 scalar values**, covering every profile, comparison, bounded window, all four exact raw copies and self pairs without importing production functions. Audit report SHA256: `9cc71d85a7b436267209f49af9a60123d1a08df8a4b3647b528e94fe28bc0489`. Computational reconstruction does not supply independent observations or a physical-origin conclusion.

## Recover exact archived inputs

The [input inventory](../inputs/INPUT_INVENTORY.json), SHA256 `ef8b5ebe21e6ab03f037691c6582a3b70187a77908274c46e08e89e430f99cce`, binds **19 restored files**: seven target-specific merged FITS, four discovery ancillary TARs, four native-A FITS and four historical raw-context NPZs. All three complete existing archives were verified against their original sizes and hashes. The merged archive was reused from an exact cache; both required raw-input archives were recovered from previously saved source files. No live telescope/archive query or duplicate archive package was needed.

| Existing archive | Restored here | Original instructions and receipts |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven HD114386 merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART2_2026-11-01.zip` | March and May 2022 discovery ancillary products | [Saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART3_2026-11-01.zip` | January and August 2023 discovery ancillary products | Same saved-input instructions and registry |

The four original raw-context NPZs are reconstructed from unchanged committed batch03 evidence parts and cross-checked against the original mapping hashes. Saved result copies retain the following exact identities:

| Original event / order | Bytes | SHA256 |
|---|---:|---|
| 0094 / 19 | 7,942 | `78a9d1784e5776213d82d6040d6f7f324fe9923da684b370acd207a88cbcb8e7` |
| 0096 / 19 | 7,909 | `966d401018a0e21e2e37b982ba0d5880a6256205527bd560875732ede7c222df` |
| 0098 / 19 | 7,819 | `aa2377a8c18a7a3af9aa492a448c5a344b2f3412225cde032662aae7d71d3dc5` |
| 0110 / 19 | 7,514 | `045d1b374812e41b63c084ee89619a8dcf6cd0cf1bdb287ad04b3cb0c1fba766` |

Full raw detector products remain in the existing saved archives and are not extracted for this profile arithmetic. The [input instructions](../inputs/README.md) retain every archive/member identity, header convention and historical mapping qualification.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c016_context/inputs/restore_inputs.py \
  --archive-dir /path/to/merged/archive/cache \
  --archive-dir /path/to/native/archive/cache
```

One cache may hold all three archives. The helper verifies whole archives and selected members, rejects differing destinations, reuses identical files and writes deterministic metadata. It inspects FITS/NPY headers without executing the scientific comparison or making a network request. Local cache paths do not enter the metadata. Full restored inputs and temporary panel copies are excluded from Git; compact result evidence is retained with the analysis.

## Preserve the completed record

Reproduce in a separate checkout with this phase's `analysis/results/` absent before its first run, following the [analysis instructions](../analysis/README.md). Preserve the published input identities, code, method, root release and completed outputs. Do not reset the authoritative one-shot guard. Reproduction timestamps may differ; compare scientific arrays and numerical records.

All original U dispositions, review votes, mapping stages, survey counts and prior analyses remain unchanged. Reproduction of this fixed context does not authorize favorable-reference selection, shifted windows, extra fitted parameters or an independent-detection claim.
