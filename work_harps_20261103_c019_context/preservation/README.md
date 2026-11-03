# C019 / HD114783 preservation and reproduction

The fixed C019 run completed at **2026-11-03T18:55:09.358024+00:00**, with status `COMPLETE_FIXED_GROUP_CONTEXT`. It preserves seventeen bounded source windows, thirty-four profiles in two fixed frames and all ten exact original raw panels: **61 NPZ files totaling 700,579 bytes**.

| Saved evidence | Files | Total bytes | Exact filenames and SHA256 bindings |
|---|---:|---:|---|
| Seven HD114783 merged and ten native-order source windows before interpolation | 17 | 168,013 | [BOUNDED_INPUT_INDEX.json](../analysis/results/BOUNDED_INPUT_INDEX.json) |
| Fourteen merged and twenty native frame profiles | 34 | 472,365 | [PROFILE_METRICS.json](../analysis/results/PROFILE_METRICS.json) |
| Original orders 3/4 raw panels for all five discoveries | 10 | 60,201 | [PRESERVED_RAW_CONTEXT.json](../analysis/results/PRESERVED_RAW_CONTEXT.json) |

All **71 numerical files** in [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json) were rehashed while finalizing this document. All 61 NPZ files also match their separate index bindings; all ten raw copies match their original input bytes and hashes exactly. These checks preserve byte integrity without adding measurements. Figures and reports created later are outside the numerical-ledger count.

| Binding file | SHA256 |
|---|---|
| `analysis/results/OUTPUT_HASHES.json` | `e4c43d247db9bf5cd27ba4e6c7501de91ac8b57293b1f5d563e03f3d4be919ac` |
| `analysis/results/BOUNDED_INPUT_INDEX.json` | `8c443295e4419b70504b4e705798f4390093a505518c3a307459dea0eb7ffe13` |
| `analysis/results/PROFILE_METRICS.json` | `f9aac266dee7648db131f9c5b47b37c11420ad822958b27c387255b764e3dd83` |
| `analysis/results/PRESERVED_RAW_CONTEXT.json` | `4722a5b333df5648c9088f591813c148f4e412a9be58162e9d6678ecf1cdc2fc` |

## Complete support and retained signed samples

All **34 profile slots and 180 comparison slots** remain, including **20 labelled identical-product self comparisons**. Every profile has 601/601 finite raw and normalized grid values, a valid positive two-flank reference and a false low-reference flag. All 180 raw Pearson and 180 normalized RMS values pass the fixed evaluability gates. No source is raw-only, blocked or structurally excluded; no grid sample is masked for an interpolation gap or outside native coverage. C018's order-2 partial coverage and raw-only outcomes are not transferred.

Every merged frame window contains 600 finite original samples, with 150 finite originals in each flank. All merged fixed-window/flank originals are positive. All ten native order-3 frame rows also have positive finite originals throughout their fixed windows and flanks. They contain 599–603 finite window originals, 147–148 left-flank originals and 153–154 right-flank originals. Native order-4 frame rows contain 500–502 finite window originals, 123–124 left and 126–127 right flank originals.

Six order-4 frame rows retain nonpositive source samples, all inside their respective left flanks:

| Event / order | Frame | Nonpositive / finite window originals | Nonpositive / finite left-flank originals |
|---|---|---|---|
| 0115 / 4 | Barycentric | 1 / 500 | 1 / 123 |
| 0115 / 4 | Topocentric | 1 / 500 | 1 / 123 |
| 0125 / 4 | Topocentric | 10 / 500 | 10 / 123 |
| 0129 / 4 | Barycentric | 1 / 501 | 1 / 124 |
| 0129 / 4 | Topocentric | 1 / 500 | 1 / 123 |
| 0135 / 4 | Topocentric | 5 / 500 | 5 / 123 |

The other four order-4 frame rows have positive originals throughout their fixed windows and flanks. Every order-4 right flank has zero nonpositive samples. For 0125 topocentric, the retained fractions are 2% of window originals and approximately 8.13% of its left flank; 0135 topocentric retains 1% of window originals and approximately 4.07% of its left flank. These are frame views of four discovery products, not six independent exposures or necessarily six disjoint sets of source pixels. The two fixed frames can retain different source samples without moving either frame's windows or excluding unfavorable values.

Positive pooled references do not change those original signs. The complete metrics retain every per-frame count, signed value, flank median, reference, noise proxy and quality flag without clipping or sign changes. Original-sample counts differ from the 601-point interpolated grid and from saved bounded source windows, which include interpolation brackets.

Positive finite ERR support is absent in all thirty-four profiles. Compact NPZs retain signed flux, original source indices and coordinates, frame-conversion information, available ERR samples, support and normalization status. Load arrays with `allow_pickle=False`. Valid positive references, false low-reference flags and complete support do not establish calibrated uncertainty, formal significance, sensitivity, a physical origin or a qualified survey null. Fixed-flank medians remain descriptive levels rather than established line-free continua. Native BUNIT is absent; merged ADU and unspecified native extracted scales are not a calibrated physical flux ratio. Full original FITS remain necessary for extraction-provenance checks.

## Seven observations and five fixed references

C019 / R020 keeps **0115/0120/0125/0129/0135** together at original queue rows **34/39/43/47/52**. The exact catalog centers are **3881.6125 Å** for 0115/0135, **3881.615 Å** for 0120/0129 and **3881.6150000000002 Å** for 0125. The midpoint of exact extrema evaluates to **3881.6137500000004 Å**; preserve that float rather than rounding the method. This is a catalog-based coordinate, not a fitted peak.

The fixed common core is [3881.3637500000004, 3881.8637500000004] Å and context [3878.6137500000004, 3884.6137500000004] Å. Original individual ±0.25 Å cores and discovery markers remain distinct in the [input instructions](../inputs/README.md). Common metric edges differ from original edges by up to 0.00125 Å and do not contain the full union. No core expansion or recentering occurs after values.

First queue discovery 0115 was observed on **2022-01-21T06:51:10.597**, under publication ID `ADP.2022-01-22T01:09:14.958`, BERV **29.658729150824 km/s**. It fixes one independently recomputed common topocentric anchor **3881.2297765555622 Å**. Other references do not redefine that anchor; original event-specific topocentric centers remain separate metadata checked against each product's own BERV.

The same seven **HD114783** January 2022–July 2023 observations span **59.073251754930496 km/s** in BERV. All five distinct discovery references remain fixed. The March 22 and July 1 2023 observations stay in the cohort without becoming C019 references. The 140 merged comparison slots are seven epochs × five references × two frames × two regions. Per frame/region, five rows are identical-product self comparisons; **30 directed nonself rows represent 20 distinct unordered observation pairs plus 10 reciprocal duplicates**, sharing seven observations. The other 40 slots are same-exposure native-to-merged comparisons from ten order contexts, not additional observations or independent confirmation. Thirty-four profiles and 180 slots still use only seven observing products.

C019 reuses C018's observations and some identical complete native products. Their newly bounded ±3 Å spectral windows are disjoint, while complete original historical raw containers remain separately preserved. Bounded-window disjointness does not establish independent observations or independence of every historical raw crop. C005's numeric wavelength overlap is on HD106515A and shares no products or source pixels. Original C019 epoch/profile/raw evidence already existed; this is dependent post-detection context, adding no observing time, blind validation, independent detection or archive-wide completeness. Completed mapping and normalization routes are not replayed.

## Fresh geometry, original support and unassessed later fields

Fresh scans of **all 72 order headers in each of five discovery products**, 360 records in total, select **orders 3 and 4 for every discovery**, retaining all ten covering pairs. Every selected product covers the full common context, core and both fixed reference flanks in both frames. Exact per-product polynomial coefficients, endpoints, event centers and raw coordinates remain in the [input inventory](../inputs/INPUT_INVENTORY.json). Header geometry, observed finite support, normalization quality and raw registration remain separate conditions.

All ten original order-3/4 global-grid, original local-usable and original baseline-verified fields are **true**. Four batch03 events, 0115/0120/0125/0135, also explicitly retain true later five-window support for both orders. Older raw_followup event **0129 has no later-five-window field and was not selected for that later mapping follow-up**. Its canonical later support remains **null/unassessed**, with field presence false and no later selected-order/disposition records. Absence does not mean supported or unsupported. Source paths and field basis remain explicit: batch03 uses `baseline_mapping_verified`, while original 0129 uses `mapping_verified`.

All five exact original primary/secondary/adopted review sets remain **U/U/U**, including 0129's original secondary U normalized to U, adopted baseline U and current U. Every current C019 label remains U. The distinct C018/0128 I/M-normalized-I/baseline-I history and failed order-2 stages are not applied to C019/0129. No later review or preservation declaration from another event is borrowed for 0129, and no unperformed later diagnostic is claimed.

Historical evidence retains broad matching profiles and diffuse science-trace-associated raw enhancement without a specific physical-origin assignment. The remote off-trace pixel noted in 0135's order-3 review does not classify the central diffuse feature. Supported mapping, profile correlation and same-exposure extraction agreement do not change dispositions or qualify a laser candidate.

## Ten exact original raw containers

Eight original batch03 NPZs retain their stored raw, background/excess, baseline and native arrays. The two original 0129 baseline NPZs retain five arrays each: raw cutout, background, excess, native wavelength and native flux. They remain exactly:

| Original 0129 panel | Bytes | SHA256 |
|---|---:|---|
| Order 3 | 3,253 | `7cd1c059bcf483750405adbabfcad53453afcaa4fccf58ef638d9dabb1cad061` |
| Order 4 | 3,059 | `128c8ba54611e7ac1309e8dd5dcd96b5b69b0ff728bb19cf0e7dbdff446ccfa4` |

The unchanged original `RAW_BASELINE_EVIDENCE.zip` and its member manifest are verified, and each saved result copy is byte-identical to the restored original. No later container is substituted. No raw panel is fitted, cropped or subtracted anew. Exact raw-copy preservation and numerical reconstruction do not add independent morphology evidence or supply physical-origin proof.

## Public method and release

All **25 prospective files** were published at commit [`5c1c049f3c04906fd4fdd5480557b5007fc86dec`](https://github.com/andersenmartin-blip/setisearch/commit/5c1c049f3c04906fd4fdd5480557b5007fc86dec) and read back exactly before execution. The [publication receipt](../PROSPECTIVE_PUBLICATION_RECEIPT.json) records both public branches and **752,259 verified bytes**. Receipt SHA256: `d6cef6d37cc5ed262e975eb4b7a4020004576f99b86dbc165ece49b670aec510`.

The unchanged [plan](../analysis/PLAN.json) has SHA256 `e6e194dda59b341b5ab5fd9b4bf64e3b62c77820aedfa7532ac115c4a947fd99`. The [root release](../analysis/ROOT_RELEASE.json), issued at **2026-11-03T18:54:53.505083+00:00**, has SHA256 `fc0f0429aca28cd7e4e3c5cea45ef63ab90b4a3ce3fb5a9b4e33a121cfe644b6`. All **89 plan-bound source hashes**, all **24 files bound by the root freeze**, and all 25 exact public-method file identities were checked unchanged while finalizing this note. The [preflight freeze](../PREFLIGHT_FREEZE.json) and prospective reviews preserve the pre-array contract.

The runner validates release and source hashes, performs the fixed comparison once and rejects an existing results directory. Preserve that guard and all completed outputs. The [independent reconstruction](../independent_audit/NUMERICAL_AUDIT.json) passed **1,026 checks across 134,487 scalar values**, covering every profile, comparison, bounded window, all ten exact original raw copies, self pairs and source-specific mapping/review history without importing production functions. Audit report SHA256: `d534442a2f184766eade0fbb7051971efdac5535807dbbae9546a8e95ec414df`. Computational reconstruction does not supply independent observations or a physical-origin conclusion.

## Recover exact archived inputs

The [input inventory](../inputs/INPUT_INVENTORY.json), SHA256 `ceff0bd21ef4dac8a27003450ed3c64b912190c040981c2c03c665a6c160b9ab`, binds **27 restored files**: seven target-specific merged FITS, five discovery ancillary TARs, five native-A FITS and ten original raw-context NPZs. All four complete cached source archives were verified against original sizes and hashes. No new file transfer, live telescope/archive query, duplicate archive upload or full-package duplication was needed.

| Existing archive | Restored contents | Original registries |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven HD114783 merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART3_2026-11-01.zip` | 0115 ancillary product | [Batch03 saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART4_2026-11-01.zip` | 0120/0125/0135 ancillary products | Same batch03 instructions and registry |
| `SETI_HARPS_EXTENSION02_RAW_INPUTS_PART1_2026-11-01.zip` | Separate original 0129 ancillary product | [Original raw restore](../../work_harps_20261101/v2/extension02/raw_followup/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |

Eight batch03 panels are reconstructed from unchanged committed evidence parts; the two 0129 panels come from the unchanged original baseline archive. Full raw detector products remain in existing saved archives and are not extracted for profile arithmetic. The [input instructions](../inputs/README.md) retain every archive/member identity, header convention, exact individual core and historical qualification.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c019_context/inputs/restore_inputs.py \
  --archive-dir /path/to/merged/archive/cache \
  --archive-dir /path/to/batch03/archive/cache \
  --archive-dir /path/to/original/raw/archive/cache
```

One cache may hold all four archives. The helper verifies whole archives and selected members, rejects differing destinations, reuses identical bytes and writes deterministic metadata. It inspects FITS/NPY headers without executing the scientific comparison, completed diagnostic or network request. Local cache paths do not enter the metadata. Full restored FITS/TAR and temporary panel copies are excluded from Git; compact result evidence is retained with the analysis.

## Preserve the completed record

Reproduce in a separate checkout with this phase's `analysis/results/` absent before its first run, following the [analysis instructions](../analysis/README.md). Preserve published input identities, code, method, root release and completed outputs. Do not reset the authoritative one-shot guard. Reproduction timestamps may differ; compare scientific arrays and numerical records.

All original review votes, supported and unassessed mapping stages, baseline and current dispositions, survey counts and prior analyses remain unchanged. Reproduction of this fixed context does not authorize favorable-reference selection, shifted windows, extra fitted parameters, completed-diagnostic replay or an independent-detection claim.
