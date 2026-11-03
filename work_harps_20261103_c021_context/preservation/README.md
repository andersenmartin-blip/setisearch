# C021 / HD114783 preservation and reproduction

The fixed C021 run completed at **2026-11-03T19:27:53.520429+00:00**, with status `COMPLETE_FIXED_GROUP_CONTEXT`. It preserves twelve bounded source windows, twenty-four profiles in two fixed frames and all five exact original raw panels: **41 NPZ files totaling 476,728 bytes**.

| Saved evidence | Files | Total bytes | Exact filenames and SHA256 bindings |
|---|---:|---:|---|
| Seven HD114783 merged and five native-order source windows before interpolation | 12 | 107,883 | [BOUNDED_INPUT_INDEX.json](../analysis/results/BOUNDED_INPUT_INDEX.json) |
| Fourteen merged and ten native frame profiles | 24 | 332,805 | [PROFILE_METRICS.json](../analysis/results/PROFILE_METRICS.json) |
| Original order-19 raw panels for all five discoveries | 5 | 36,040 | [PRESERVED_RAW_CONTEXT.json](../analysis/results/PRESERVED_RAW_CONTEXT.json) |

All **51 numerical files** in [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json) were rehashed while finalizing this document. All 41 NPZ files also match their separate index bindings; all five raw copies match their original input bytes and hashes exactly. These checks preserve byte integrity without adding measurements. Figures and reports created later are outside the numerical-ledger count.

| Binding file | SHA256 |
|---|---|
| `analysis/results/OUTPUT_HASHES.json` | `d5b90db69fb0877f7c0dfe9eed11bcb3ab502903eae06e98a29aa3552ab00483` |
| `analysis/results/BOUNDED_INPUT_INDEX.json` | `0d786ec950397f5dfd4747df797bbb9f088d70d9db778142833fb6dc1be53f2b` |
| `analysis/results/PROFILE_METRICS.json` | `cfa1e10196d7026e6a0d36ef8b8acebc379ca56b2a5e935328961b06d0a0a91d` |
| `analysis/results/PRESERVED_RAW_CONTEXT.json` | `365d77f6fd1b7e0cff89a638bd1bfaaa2aa1258c00230ab381d6de45da7322c1` |

## Complete support, signed samples and quality

All **24 profile slots and 160 comparison slots** remain, including **20 labelled identical-product self comparisons**. Every profile has 601/601 finite raw and normalized grid values, a valid positive two-flank reference and a false low-reference flag. All 160 raw Pearson and 160 normalized RMS values pass the fixed evaluability gates. No source is raw-only, blocked or structurally excluded; no grid sample is masked for an interpolation gap or outside native coverage.

All finite original samples inside the fixed windows and reference flanks are positive: window/left-flank/right-flank nonpositive fractions are zero in every profile. Every merged frame window contains 600 finite original samples, with 150 finite originals in each flank. The ten native order-19 frame rows retain their own source counts:

| Event / order | Finite window originals B/T | Finite left-flank originals B/T | Finite right-flank originals B/T |
|---|---|---|---|
| 0116 / 19 | 505 / 505 | 124 / 124 | 128 / 128 |
| 0121 / 19 | 504 / 505 | 124 / 124 | 128 / 128 |
| 0126 / 19 | 506 / 505 | 125 / 124 | 128 / 128 |
| 0130 / 19 | 504 / 505 | 124 / 125 | 128 / 128 |
| 0139 / 19 | 507 / 505 | 125 / 125 | 128 / 128 |

These rows are two frame views of five discovery products; fourteen merged frame rows are two views of seven observing products. Original-sample counts differ from the 601-point interpolated grid and from saved bounded source windows, which include interpolation brackets. The complete metrics retain signed source values, finite counts, medians, references, noise proxies and flags without clipping, sign changes, shifted flanks or favorable-reference selection. Positivity describes these fixed sampled windows and does not characterize the full original spectra outside them.

Positive finite ERR support is absent in all twenty-four profiles. Compact NPZs retain signed flux, original source indices and coordinates, frame-conversion information, available ERR samples, support and normalization status. Load arrays with `allow_pickle=False`. Positive samples/references, false low-reference flags and complete support do not establish calibrated uncertainty, formal significance, sensitivity, a physical origin or a qualified survey null. Fixed-flank medians remain descriptive reference levels rather than established line-free continua; structured flank evidence is retained, including the prospective C022 overlap below. Native BUNIT is absent; merged ADU and unspecified native extracted scales are not a calibrated physical flux ratio. Full original FITS remain necessary for extraction-provenance checks.

## Seven observations and the exact five-reference set

C021 / R022 keeps **0116/0121/0126/0130/0139** together at original queue rows **35/40/44/48/55**. Exact catalog centers are **4309.827499999999 Å** for 0116/0121/0139 and **4309.825 Å** for 0126/0130. Their exact-extrema midpoint is **4309.82625 Å**, not a fitted peak. The fixed common core is [4309.57625, 4310.07625] Å and context [4306.82625, 4312.82625] Å. Exact original ±0.25 Å cores and discovery markers remain separate in the [input instructions](../inputs/README.md); common edges differ by up to 0.00125 Å and do not contain the complete original-core union. No core expansion or recentering occurs after values.

First queue member 0116 was observed on **2022-01-21T06:51:10.597**, under publication ID `ADP.2022-01-22T01:09:14.958`, BERV **29.658729150824 km/s**. It fixes one independently recomputed common topocentric anchor **4309.39991731037 Å**. Other references do not redefine that anchor; original event-specific topocentric catalog centers remain distinct metadata checked against each product's own BERV.

The same seven **HD114783** January 2022–July 2023 observations span **59.073251754930496 km/s** in BERV. C021 references are January 21, February 5 and May 5 2022, January 16 and **July 1 2023**. March 22 and **May 15 2023** remain non-reference epochs. C019's May reference is not transferred in place of C021's July reference, despite the same reference counts.

The 140 merged comparison slots are seven epochs × five fixed references × two frames × two regions. Per frame/region, five rows are identical-product self comparisons; **30 directed nonself rows represent 20 unordered observation pairs plus 10 reciprocal duplicates**, sharing seven observations. The other 20 slots are same-exposure native-to-merged comparisons from five order contexts, not additional observations or independent confirmation. Twenty-four profiles and 160 slots still use only seven observing products.

C021 reuses C018/C019 observations and some identical complete native products at a newly bounded window disjoint from their blue windows. Historical raw containers remain separately preserved; bounded-window disjointness does not establish independent observations or independence of all saved crops. Numeric overlaps with C006/C007 use HD106515A and share no products or pixels. The nearby HD114386 C016 window is disjoint by approximately 0.03875 Å. Original C021 epoch/profile/raw evidence and the completed wider 0130 mapping diagnosis already existed. This is dependent post-detection context, adding no observing time, blind validation, independent detection or archive-wide completeness. Completed mapping and normalization routes are not replayed.

## Prospective C022 directly reuses C021 spectral evidence

The [prospective next-group metadata](../scientific_review/NEXT_GROUP_METADATA.json), fixed and published before C021 values, identifies C022 on the same seven observing products and native lineage. Its proposed window [4309.241249999999, 4315.241249999999] Å overlaps C021 on **[4309.241249999999, 4312.82625] Å**, width **3.585000000000946 Å**, sharing bounded spectral source pixels.

The common cores are disjoint, but each is exposed in the other's reference context under the frozen barycentric geometry:

| Core already defined | Interval (Å) | Containing fixed reference flank |
|---|---|---|
| Prospective C022 common core | 4311.991249999999 to 4312.491249999999 | C021 positive flank: 4311.32625 to 4312.82625 |
| C021 common core | 4309.57625 to 4310.07625 | Prospective C022 negative flank: 4309.241249999999 to 4310.741249999999 |

Thus the full proposed C022 common core has already been sampled in C021's broad surrounding/positive reference context, and C021's core will lie in the proposed C022 negative reference flank. All structured samples remain in the fixed references without masks or an assumed line-free continuum. A future separately frozen C022 calculation would reuse observed spectral evidence; it would not be an untouched or independent test. This section records prospective metadata and exposure dependence, not a C022 execution or result. Complete original raw crops remain separately preserved without inferred equality or independence of their full contents. Next-metadata SHA256: `3b6e1784c1b82fcad35646132ade01e505e623995d36cd4b3ffe55dbdeeb14fb`.

## Fresh geometry and the mixed original mapping matrix

Fresh scans of **all 72 order headers in each of five discovery products**, 360 records in total, select **order 19 only** for every discovery, retaining all five covering pairs. Every selected product covers the full common context, core and both fixed reference flanks in both frames. Exact source-specific coefficients, endpoints, event centers and raw coordinates remain in the [input inventory](../inputs/INPUT_INVENTORY.json). Header geometry, observed finite support, normalization quality and raw registration remain separate conditions.

| Original event / order | Global support | Original local usable | Original baseline verified | Later five-window support |
|---|---|---|---|---|
| 0116 / 19 | true | **false** | **false** | true |
| 0121 / 19 | true | true | true | true |
| 0126 / 19 | true | **false** | **false** | true |
| 0130 / 19 | true | **false** | **false** | true |
| 0139 / 19 | true | true | true | true |

Batch03 explicitly stores `baseline_mapping_verified`; original 0130 raw_followup uses `mapping_verified`. Later 0130 reference support comes from its completed wider mapping-followup order record at the original native pixel/raw row/raw column and event center. Later support does not rewrite the failed original local/baseline stages for 0116/0126/0130. C019/0129's absent/null later fields do not apply to this assessed 0130 context. No completed mapping diagnostic or registration is rerun.

## Preserve original and later 0130 history separately

Four batch03 events, 0116/0121/0126/0139, retain exact original primary/secondary/adopted **U/U/U** reviews for broad native profiles and diffuse trace-associated raw enhancements, including the original mapping limitations recorded separately for 0116/0126.

Separate raw_followup event **0130** retains original primary **I**, secondary **M**, explicitly normalized to **I**, and adopted baseline **I / INSUFFICIENT_LOCAL_RAW_MAPPING**. Its completed wider five-window diagnosis and separate later visual reviews at unchanged coordinates retain **U/U/current U**. The inventory preserves exact original records, later records, verification, archive identity and historical coordinate/sample-preservation declarations as distinct stages. Those older declarations are not re-proved by a new array-equality test or mapping replay here. Every current C021 event remains U. Supported registration, profile correlation and same-exposure extraction agreement do not assign an origin or qualify a laser candidate.

All five saved raw NPZs are **original containers**. Four original batch03 containers retain stored raw, background/excess, baseline and native arrays. The original 0130 baseline NPZ retains five arrays: raw cutout, background, excess, native wavelength and native flux. Its saved result copy remains exactly **3,532 bytes**, SHA256 **`a7dd8a01661a3a51629a1939b159814059d02acd8b5ce32433538f4bf9e0272e`**.

This original is not replaced by its distinct later wider container, **5,534 bytes**, SHA256 `1474320f43541da160cacb6c8cf7f1664b3df29ae38d95a5e689d51c03181d0b`. Original baseline ZIP/member and historical preserved-input hashes agree; the later wider archive and its preservation declarations remain separately bound. All five current raw copies match their restored original bytes exactly. No raw panel is newly fitted, cropped or subtracted. Computational preservation does not add independent raw morphology evidence or supply physical-origin proof.

## Public method and release

All **25 prospective files** were published at commit [`d19abc6b1e4b23e4b6c5e4286ecf74ae5edc2a32`](https://github.com/andersenmartin-blip/setisearch/commit/d19abc6b1e4b23e4b6c5e4286ecf74ae5edc2a32) and read back exactly before execution. The [publication receipt](../PROSPECTIVE_PUBLICATION_RECEIPT.json) records both public branches and **693,186 verified bytes**. Receipt SHA256: `74e702745f6c62fd71807fbadbe1c580a4016c8b3c708828db5a9df2e2c328dc`.

The unchanged [plan](../analysis/PLAN.json) has SHA256 `9bcd1af103d6f3ee007da0e98cab5af8b2235508d68b9de98b258dc1e9630cdf`. The [root release](../analysis/ROOT_RELEASE.json), issued at **2026-11-03T19:27:34.968355+00:00**, has SHA256 `85561cdf2b90e59b5ffd1229d94d388912380839868dc4feda7c6312e8379aa8`. All **92 plan-bound source hashes**, all **24 files bound by the root freeze**, and all 25 exact public-method file identities were checked unchanged while finalizing this note. The [preflight freeze](../PREFLIGHT_FREEZE.json) and prospective reviews preserve the pre-array contract.

The runner validates release and source hashes, performs the fixed comparison once and rejects an existing results directory. Preserve that guard and all completed outputs. The [independent reconstruction](../independent_audit/NUMERICAL_AUDIT.json) passed **834 checks across 94,802 scalar values**, covering every profile, comparison, bounded window, all five exact original raw copies, self pairs and retained source-specific staged history without importing production functions. Audit report SHA256: `c5e391dc0144493aeb1f7cfa3bd191d238c2026848b3b10a9db7f489cfaef59a`. Computational reconstruction does not supply independent observations or a physical-origin conclusion.

## Recover exact archived inputs

The [input inventory](../inputs/INPUT_INVENTORY.json), SHA256 `61c26f45548618c783ad71bd2f6eb79d82528740918d2de67e58a924ccc09fd0`, binds **22 restored files**: seven target-specific merged FITS, five discovery ancillary TARs, five native-A FITS and five original raw-context NPZs. All five complete cached source archives were verified against original sizes and hashes. No new file transfer, live telescope/archive query, duplicate archive upload or full-package duplication was needed.

| Existing archive | Restored contents | Original registries |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven HD114783 merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART3_2026-11-01.zip` | 0116 ancillary product | [Batch03 saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART4_2026-11-01.zip` | 0121/0126 ancillary products | Same batch03 instructions and registry |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART5_2026-11-01.zip` | 0139 ancillary product | Same batch03 instructions and registry |
| `SETI_HARPS_EXTENSION02_RAW_INPUTS_PART1_2026-11-01.zip` | Separate original 0130 ancillary product | [Original raw restore](../../work_harps_20261101/v2/extension02/raw_followup/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |

Four batch03 panels are reconstructed from unchanged committed evidence parts; the original 0130 panel comes from unchanged `RAW_BASELINE_EVIDENCE.zip` and its manifest, cross-checked against the historical preserved-input ledger. Full detector products remain in existing saved archives and are not extracted for profile arithmetic. The [input instructions](../inputs/README.md) retain every archive/member identity, header convention, exact individual core and historical qualification.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c021_context/inputs/restore_inputs.py \
  --archive-dir /path/to/merged/archive/cache \
  --archive-dir /path/to/batch03/archive/cache \
  --archive-dir /path/to/original/raw/archive/cache
```

One cache may hold all five archives. The helper verifies whole archives and selected members, rejects differing destinations, reuses identical bytes and writes deterministic metadata. It inspects FITS/NPY headers without executing the scientific comparison, completed diagnostic or network request. Local cache paths do not enter the metadata. Full restored FITS/TAR and temporary panel copies are excluded from Git; compact result evidence is retained with the analysis.

## Preserve the completed record

Reproduce in a separate checkout with this phase's `analysis/results/` absent before its first run, following the [analysis instructions](../analysis/README.md). Preserve published input identities, code, method, root release and completed outputs. Do not reset the authoritative one-shot guard. Reproduction timestamps may differ; compare scientific arrays and numerical records.

All original review votes, failed and supported mapping stages, baseline and current dispositions, survey counts and prior analyses remain unchanged. Reproduction of this fixed context does not authorize favorable-reference selection, shifted windows, extra fitted parameters, completed-diagnostic replay or an independent-detection claim. The prospective C022 shared-pixel and reciprocal-flank dependence must remain explicit in any subsequent separately frozen work.
