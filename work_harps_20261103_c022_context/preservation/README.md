# C022 / HD114783 preservation and reproduction

The fixed C022 run completed at **2026-11-03T21:16:53.995508+00:00**, with status `COMPLETE_FIXED_GROUP_CONTEXT`. It preserves ten bounded source windows, twenty profiles in two fixed frames and all three exact original raw panels: **33 NPZ files totaling 384,410 bytes**.

| Saved evidence | Files | Total bytes | Exact filenames and SHA256 bindings |
|---|---:|---:|---|
| Seven HD114783 merged and three native-order source windows before interpolation | 10 | 86,921 | [BOUNDED_INPUT_INDEX.json](../analysis/results/BOUNDED_INPUT_INDEX.json) |
| Fourteen merged and six native frame profiles | 20 | 277,658 | [PROFILE_METRICS.json](../analysis/results/PROFILE_METRICS.json) |
| Original order-19 raw panels for all three discoveries | 3 | 19,831 | [PRESERVED_RAW_CONTEXT.json](../analysis/results/PRESERVED_RAW_CONTEXT.json) |

All **43 numerical files** in [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json) were rehashed while finalizing this document. All 33 NPZ files also match their separate index bindings; all three raw copies match their original input bytes and hashes exactly. These checks preserve byte integrity without adding measurements. Figures and reports created later are outside the numerical-ledger count. No runner, plotter or completed diagnostic was rerun for this note.

| Binding file | SHA256 |
|---|---|
| `analysis/results/OUTPUT_HASHES.json` | `3241c6be3bb3fd51a7c6bc99da96d4b47c91ee2ae236380edd2921450eff372b` |
| `analysis/results/BOUNDED_INPUT_INDEX.json` | `01bab9922e024dbcbc40ab4e5a3780246924b75efa72dd37e4860ab3b93f93b3` |
| `analysis/results/PROFILE_METRICS.json` | `a70418c855c056680aa6cb4c93a93facdc20778de9c77071682b68fee3bfcdf4` |
| `analysis/results/PRESERVED_RAW_CONTEXT.json` | `73b121c3cb9721eb70e448a8253e829ae21a28088e59104bea51e9da7c630f3e` |

## Complete support, signed samples and quality

All **20 profile slots and 96 comparison slots** remain, including **12 labelled identical-product self comparisons**. Every profile has 601/601 finite raw and normalized grid values, a valid positive two-flank reference and a false low-reference flag. All 96 raw Pearson and 96 normalized RMS values pass the fixed evaluability gates. No source is raw-only, blocked or structurally excluded; no grid sample is masked for an interpolation gap or outside native coverage.

All finite original samples inside every fixed window and reference flank are positive: window/left-flank/right-flank nonpositive fractions are zero in all twenty profiles. Each merged frame window contains 600 finite originals, with 150 finite originals in each flank. The six native frame rows retain their own source counts:

| Event / order | Finite window originals B/T | Finite left-flank originals B/T | Finite right-flank originals B/T |
|---|---|---|---|
| 0117 / 19 | 512 / 512 | 126 / 126 | 130 / 130 |
| 0127 / 19 | 515 / 512 | 127 / 126 | 131 / 130 |
| 0131 / 19 | 512 / 513 | 126 / 126 | 130 / 131 |

These are two frame views of three discovery products; fourteen merged frame rows are two views of seven observations. Original-sample counts differ from the 601-point interpolated grid and from saved bounded windows, which include interpolation brackets. The complete metrics retain signed source values, finite counts, medians, reference levels, noise proxies and flags without clipping, sign changes, shifted flanks or favorable-reference selection. Positivity describes the fixed sampled windows and does not characterize the full original spectra outside them.

Positive finite ERR support is absent in all twenty profiles. Compact NPZs retain signed flux, original source indices and coordinates, frame-conversion information, available ERR samples, support and normalization status. Load arrays with `allow_pickle=False`. Positive samples/references, false low-reference flags and complete support do not establish calibrated uncertainty, formal significance, sensitivity, a physical origin or a qualified survey null. Fixed-flank medians remain descriptive levels rather than established line-free continua. Structured flank evidence, including the C021 core below, remains in the references without masks. Native BUNIT is absent; merged ADU and unspecified native extracted scales are not a calibrated physical flux ratio. Full original FITS remain necessary for extraction-provenance checks.

## Seven observations and three exact references

C022 / R023 keeps **0117/0127/0131** together at original queue rows **36/45/49**. Exact catalog centers are **4312.245 Å** for 0117/0127 and **4312.237499999999 Å** for 0131. Their exact-extrema midpoint evaluates to **4312.241249999999 Å**, not a fitted peak. The common metric core is [4311.991249999999, 4312.491249999999] Å and context [4309.241249999999, 4315.241249999999] Å. Exact individual ±0.25 Å cores and discovery markers remain separate in the [input instructions](../inputs/README.md). Fixed common edges differ from original member edges by up to 0.00375 Å and do not contain their complete union; no core expansion or recentering occurs after values.

First queue discovery 0117 was observed on **2022-01-21T06:51:10.597**, under publication ID `ADP.2022-01-22T01:09:14.958`, BERV **29.658729150824 km/s**. It fixes one independently recomputed common topocentric anchor **4311.814678415948 Å**. Every original event-specific topocentric catalog center remains separately checked using its own exact member center and discovery BERV. Other references do not redefine the common coordinate anchor.

The same seven **HD114783** January 2022–July 2023 observations span **59.073251754930496 km/s** in BERV. C022's three references are January 21 and May 5 2022 and January 16 2023. February 5 2022 and March 22, May 15 and July 1 2023 remain observed non-reference epochs.

The 84 merged comparison slots are seven epochs × three fixed references × two frames × two regions. Per frame/region, three rows are identical-product self comparisons; **18 directed nonself rows represent 15 unordered observation pairs plus three reciprocal duplicates**, sharing seven observations. The other 12 slots are same-exposure native-to-merged comparisons from three order contexts, not additional observations or independent confirmation. Twenty profiles and 96 slots still use only seven observing products. Preserve source/reference identities and per-reference summaries rather than treating rows or pairs as independent detections.

## Direct C021 shared-pixel and reciprocal-flank exposure

C022 directly reuses C021 observing products, native lineage and bounded spectral source pixels. Their barycentric windows overlap on **[4309.241249999999, 4312.82625] Å**, width **3.585000000000946 Å**. The common cores are disjoint, but each lies wholly inside the other's fixed reference context:

| Exposed common core | Interval (Å) | Containing fixed reference flank |
|---|---|---|
| C022 | 4311.991249999999 to 4312.491249999999 | C021 positive flank: 4311.32625 to 4312.82625 |
| C021 | 4309.57625 to 4310.07625 | C022 negative flank: 4309.241249999999 to 4310.741249999999 |

The entire C022 common core was already exposed in C021's surrounding/positive reference context. C021's common core is retained in C022's negative reference flank. These dependencies and selection were fixed in the C021 prospective handoff before C021 values. All structured flank samples stay in the fixed reference calculation without an assumed line-free continuum. C022's additional context beyond the overlap adds no observing time or untouched-core evidence.

The independent audit also verifies shared original **source-index ranges for all ten C022 source windows** using metadata and original file identities. Seven merged shared counts range from **360 to 445** source samples; the three native shared counts are **306 / 358 / 306** for January 2022 / May 2022 / January 2023. These counts describe overlaps of the **saved union of both fixed-frame source windows plus interpolation brackets**. They are distinct from the pure 3.585000000000946 Å barycentric interval and from the 601-point interpolated grids. No old C021 arrays were opened or old pipeline rerun to establish this metadata proof; the complete records remain in the [numerical audit](../independent_audit/NUMERICAL_AUDIT.json).

Original C022 epoch/profile/raw evidence and the completed wider 0131 mapping diagnosis also already existed. Complete historical raw crops remain separately preserved, without an inferred equality or independence of all their contents. Earlier same-target C018/C019 blue windows are disjoint from C022. Numeric overlaps with C006/C007 use HD106515A and share no source products or pixels. This is dependent post-detection context, adding no observing time, blind validation, independent detection or archive-wide completeness. Completed mapping and normalization diagnostics are not replayed.

## Original failed stages and distinct 0131 history

Fresh scans of **all 72 order headers in each of three discovery products**, 216 records in total, select **order 19 only**, retaining all three covering pairs. Every selected product covers the full common context, core and both fixed reference flanks in both frames. Exact source-specific coefficients, endpoints, event centers and raw coordinates remain in the [input inventory](../inputs/INPUT_INVENTORY.json). Header geometry, observed finite support, normalization quality and raw registration remain separate conditions.

| Original event / order | Global support | Original local usable | Original baseline verified | Later five-window support |
|---|---|---|---|---|
| 0117 / 19 | true | **false** | **false** | true |
| 0127 / 19 | true | **false** | **false** | true |
| 0131 / 19 | true | **false** | **false** | true |

Batch03 explicitly stores `baseline_mapping_verified`; original 0131 raw_followup uses `mapping_verified`. Later 0131 support comes from its completed wider mapping-followup record at the original native pixel/raw row/raw column and event center. Later support does not rewrite any of the three original failed local/baseline stages. No earlier mixed mapping matrix or absent-later assessment is transferred to C022, and no new registration or completed diagnostic is run.

Two batch03 events, 0117/0127, retain exact original primary/secondary/adopted **U/U/U** reviews. Separate raw_followup event **0131** retains original primary **I**, secondary **M**, explicitly normalized to **I**, and adopted baseline **I / INSUFFICIENT_LOCAL_RAW_MAPPING**. Its completed wider diagnosis and separate later visual reviews at unchanged coordinates retain **U/U/current U**. Exact original/later records, verification, archive identity and historical coordinate/sample-preservation declarations remain distinct in the inventory. Those old declarations are not re-proved by a new array-equality test or mapping replay here. Every current C022 event remains U. Broad native and diffuse trace-associated raw structure remains unresolved; supported registration, profile correlation or same-exposure extraction agreement does not assign an origin or qualify a laser candidate.

All three preserved raw NPZs are **original containers**:

| Original panel | Bytes | SHA256 |
|---|---:|---|
| 0117 / 19 | 8,110 | `bdf4c1bf1775cd726b01a397e6b312a99c2bae41423258eb17e341c0e364aaa1` |
| 0127 / 19 | 8,119 | `810d2409f222af838ff3744f36ca883ffa7aaba5ab76886e8c92e43e1fb4ece6` |
| 0131 / 19 | 3,602 | `ddba2ac8fc401e59cf646ff6c70ebb598da650d45f1c3decea5b34176f6069bb` |

The two batch03 containers retain stored raw, background/excess, baseline and native arrays. Original 0131 retains five arrays: raw cutout, background, excess, native wavelength and native flux. It is not replaced by its distinct later wider container, **5,497 bytes**, SHA256 `a1d0e34caa677b4d235d23fa30cac276d705ad27dfdd1a5d6645e5f574a464f1`. Original baseline ZIP/member and historical preserved-input hashes agree; the later wider archive and declarations remain separately bound. All three result copies match their restored original bytes exactly. No panel is newly fitted, cropped or subtracted. Computational preservation adds no independent morphology evidence or physical-origin proof.

## Future C017/C018 overlap has a different relationship

The [prospective next-group metadata](../scientific_review/NEXT_GROUP_METADATA.json) selects **C017 / singleton 0118** at original queue row 37, with its own February 5 2022 discovery reference and exact center **3868.175 Å** over the same seven observations. Its proposed ±3 Å window [3865.175, 3871.175] Å overlaps completed C018 on **[3866.33375, 3871.175] Å**, width **4.8412500000004 Å**, sharing bounded source pixels. C017's proposed common core [3867.925, 3868.425] Å and C018's common core [3869.08375, 3869.58375] Å are disjoint and lie inside each other's broad surrounding contexts.

**Neither of those two cores intersects the other's fixed 1.5–3 Å reference flanks.** This is surrounding-context exposure, unlike C021/C022's reciprocal core-in-reference-flank relationship. The future C017 core was already exposed in C018, so its separate future freeze would not create an untouched or independent test. Complete historical raw crops remain separately preserved without an equality/independence claim.

C017 is a prospective **one-reference singleton**, with six other epochs and no reciprocal reference-pair duplication; C022's three-reference 18/15/3 accounting and January anchor are not transferred. Its own source geometry, signed-reference outcomes and quality would require a separate freeze and release. This section records metadata and prior exposure, not a C017 execution or result. C019/C021/C022 bounded windows are disjoint from the proposed blue C017 context while observations remain shared. Next-metadata SHA256: `43dbade5b7435f1e31301f4e4bafdb19150ac2fd2d0a3711213b41e1cc274903`.

## Public method and release

All **25 prospective files** were published at commit [`d1ad1e0e8aa6e29c20236929ffb78cbdb0e4667c`](https://github.com/andersenmartin-blip/setisearch/commit/d1ad1e0e8aa6e29c20236929ffb78cbdb0e4667c) and read back exactly before execution. The [publication receipt](../PROSPECTIVE_PUBLICATION_RECEIPT.json) records both public branches and **582,581 verified bytes**. Receipt SHA256: `032e4987b0e8242161c6b052d5e218d67db3b1406d43208ba80d2e694ffdb4db`.

The unchanged [plan](../analysis/PLAN.json) has SHA256 `766f9234da359c3a949eb899e7c7b23191cc3aa72a81b5b2554c9b642675980f`. The [root release](../analysis/ROOT_RELEASE.json), issued at **2026-11-03T21:16:44.267054+00:00**, has SHA256 `7cf50bd1f07b72ac5f51afbd25ff4e9f040cd5f093e0933dbd5bc2e8b472eb7b`. All **88 plan-bound source hashes**, all **24 files bound by the root freeze**, and all 25 exact public-method file identities were checked unchanged while finalizing this note. The [preflight freeze](../PREFLIGHT_FREEZE.json) and prospective reviews preserve the pre-array contract.

The runner validates release and source hashes, performs the fixed comparison once and rejects an existing results directory. Preserve that guard and all completed outputs. The [independent reconstruction](../independent_audit/NUMERICAL_AUDIT.json) passed **698 checks across 79,403 scalar values**, covering every profile, comparison, bounded window, all three exact original raw copies, self pairs, staged history and metadata-only C021 source-index overlap without importing production functions. Audit report SHA256: `51d6b9501e66da3c83ba22a30d477ddaaf6e5035b60fb8b8d484d6a212e9644b`. Computational reconstruction does not supply independent observations or a physical-origin conclusion.

## Recover exact archived inputs

The [input inventory](../inputs/INPUT_INVENTORY.json), SHA256 `046b3a3b58cee917f912e86f98f0a6ed8cfd2b2efe319052e650b4e31de0774c`, binds **16 restored files**: seven target-specific merged FITS, three discovery ancillary TARs, three native-A FITS and three original raw-context NPZs. All four complete cached archives were verified against original sizes and hashes. No new file transfer, live telescope/archive query, duplicate archive upload or full-package duplication was needed.

| Existing archive | Restored contents | Original registries |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven HD114783 merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART3_2026-11-01.zip` | 0117 ancillary product | [Batch03 saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART4_2026-11-01.zip` | 0127 ancillary product | Same batch03 instructions and registry |
| `SETI_HARPS_EXTENSION02_RAW_INPUTS_PART1_2026-11-01.zip` | Separate original 0131 ancillary product | [Original raw restore](../../work_harps_20261101/v2/extension02/raw_followup/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |

Two batch03 panels are reconstructed from unchanged committed evidence parts; original 0131 comes from unchanged `RAW_BASELINE_EVIDENCE.zip` and its manifest, cross-checked against the historical preserved-input ledger. Full detector products remain in existing saved archives and are not extracted for profile arithmetic. The [input instructions](../inputs/README.md) retain every archive/member identity, header convention, exact original core and historical qualification.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c022_context/inputs/restore_inputs.py \
  --archive-dir /path/to/merged/archive/cache \
  --archive-dir /path/to/batch03/archive/cache \
  --archive-dir /path/to/original/raw/archive/cache
```

One cache may hold all four archives. The helper verifies whole archives and selected members, rejects differing destinations, reuses identical bytes and writes deterministic metadata. It inspects FITS/NPY headers without executing the scientific comparison, completed diagnostic or network request. Local cache paths do not enter the metadata. Full restored FITS/TAR and temporary panel copies are excluded from Git; compact result evidence is retained with the analysis.

## Preserve the completed record

Reproduce in a separate checkout with this phase's `analysis/results/` absent before its first run, following the [analysis instructions](../analysis/README.md). Preserve published input identities, code, method, root release and completed outputs. Do not reset the authoritative one-shot guard. Reproduction timestamps may differ; compare scientific arrays and numerical records.

All original review votes, failed and supported mapping stages, baseline and current dispositions, survey counts and prior analyses remain unchanged. Reproduction of this fixed context does not authorize favorable-reference selection, shifted windows, extra fitted parameters, completed-diagnostic replay or an independent-detection claim. Preserve the direct C021 reciprocal-flank dependence and the different prospective C017/C018 surrounding-only exposure explicitly.
