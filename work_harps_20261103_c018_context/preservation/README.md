# C018 / HD114783 preservation and reproduction

The fixed C018 run completed at **2026-11-03T17:55:28.368950+00:00**, with status `COMPLETE_FIXED_GROUP_CONTEXT`. It preserves twenty-one bounded source windows, forty-two profiles in two fixed frames and all fourteen exact original raw panels: **77 NPZ files totaling 780,814 bytes**.

| Saved evidence | Files | Total bytes | Exact filenames and SHA256 bindings |
|---|---:|---:|---|
| Seven HD114783 merged and fourteen native-order source windows before interpolation | 21 | 198,873 | [BOUNDED_INPUT_INDEX.json](../analysis/results/BOUNDED_INPUT_INDEX.json) |
| Fourteen merged and twenty-eight native frame profiles | 42 | 496,646 | [PROFILE_METRICS.json](../analysis/results/PROFILE_METRICS.json) |
| Original orders 2/3 raw panels for all seven events | 14 | 85,295 | [PRESERVED_RAW_CONTEXT.json](../analysis/results/PRESERVED_RAW_CONTEXT.json) |

All **87 numerical files** in [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json) were rehashed while finalizing this document. All 77 NPZ files also match their separate index bindings; all fourteen raw copies match their original input bytes and hashes exactly. These checks preserve byte integrity without adding measurements. Figures and reports created later are outside the numerical-ledger count.

| Binding file | SHA256 |
|---|---|
| `analysis/results/OUTPUT_HASHES.json` | `02d21a3bc3fc11752cc7b7a4f7f76578bb45b675f527d6c54178ad681f7b0c7c` |
| `analysis/results/BOUNDED_INPUT_INDEX.json` | `1cb3bbcdae89dcdbb8a4fc911abe82f48cc2ca197b03561b569ef9c2292debad` |
| `analysis/results/PROFILE_METRICS.json` | `c8935aa140528752bd100f860d460ec223f224d5102cd40abc9d729ba2965bb8` |
| `analysis/results/PRESERVED_RAW_CONTEXT.json` | `602fa1f41d8e8e145d6f4203f7ec01b8278e1e854518fa10789e54fc16d4ff83` |

## Complete slots and missing right flanks

All **42 profile slots and 252 comparison slots** remain, including **28 labelled identical-product self comparisons**. Fourteen order-2 frame profiles remain `RAW_ONLY` with reason `MISSING_RIGHT_FLANK_COVERAGE`; no source is blocked or structurally excluded. The other twenty-eight profiles have valid positive two-flank references, 601/601 finite raw and normalized grid values and false low-reference flags. Raw-only order-2 rows retain unavailable valid-reference and low-reference fields, zero finite normalized samples and their complete available signed raw values.

| Profile group | Frame rows | Finite raw grid support | Finite normalized grid support | Fixed-flank outcome |
|---|---:|---|---|---|
| Seven merged observations | 14 | 601/601 each | 601/601 each | Valid positive references; low-reference flags false |
| Native order 2 in seven discoveries | 14 | Per-product partial support below | 0/601 each | Entire positive flank absent; `RAW_ONLY` |
| Native order 3 in seven discoveries | 14 | 601/601 each | 601/601 each | Valid positive references; low-reference flags false |

Every order-2 core has 51/51 common finite raw samples, and all fourteen raw core Pearson values are evaluable. The fixed broad-pattern minimum is 440/550; none of the fourteen order-2 broad comparisons meets it. Their broad raw Pearson values remain unavailable with explicit insufficient-support reasons. All twenty-eight order-2 normalized RMS slots remain unavailable. Overall, **238 raw Pearson and 224 normalized RMS values** are evaluable; every unavailable slot stays in the records.

| Event | Order-2 raw grid samples B/T, of 601 | Common core B/T, of 51 | Common broad pattern B/T, of 550 |
|---|---|---|---|
| 0114 | 406 / 406 | 51 / 51 | 355 / 355 |
| 0119 | 402 / 406 | 51 / 51 | 351 / 355 |
| 0124 | 351 / 406 | 51 / 51 | 300 / 355 |
| 0128 | 406 / 406 | 51 / 51 | 355 / 355 |
| 0133 | 379 / 406 | 51 / 51 | 328 / 355 |
| 0134 | 346 / 406 | 51 / 51 | 295 / 355 |
| 0138 | 330 / 406 | 51 / 51 | 279 / 355 |

Every order-2 right flank has zero source samples in both common frames. Available left-flank medians are positive, ranging from 63.60298538208008 to 96.14652252197266 in unspecified native units, but are not substituted for valid two-flank references. This is missing geometric coverage, not a measured nonpositive two-flank reference. No window or flank is moved, shrunk, borrowed from order 3 or extrapolated. Positive left medians do not erase signed nonpositive source samples elsewhere in the windows.

## Signed samples and unavailable errors

All finite original samples inside the fourteen merged and fourteen order-3 fixed windows and reference flanks are positive. Each merged frame window has 600 finite original samples and 150 finite originals in each flank. The fourteen order-3 frame windows have 545–549 finite original samples, with 134–135 left and 138–140 right finite flank samples. These original-sample counts differ from the 601-point grid and from saved bounded source windows, which include interpolation brackets.

Order 2 retains the following signed source counts. An absent right flank has an unavailable nonpositive fraction, not a zero fraction.

| Event | Nonpositive / finite window originals, barycentric | Nonpositive / finite window originals, topocentric | Nonpositive / finite left-flank originals B/T |
|---|---|---|---|
| 0114 | 6 / 453 | 6 / 453 | 0 / 165 ; 0 / 165 |
| 0119 | 3 / 449 | 3 / 454 | 0 / 165 ; 0 / 166 |
| 0124 | 6 / 393 | 6 / 454 | 1 / 166 ; 1 / 166 |
| 0128 | 4 / 454 | 4 / 453 | 0 / 165 ; 0 / 165 |
| 0133 | 0 / 424 | 0 / 453 | 0 / 165 ; 0 / 165 |
| 0134 | 2 / 387 | 2 / 453 | 0 / 166 ; 0 / 165 |
| 0138 | 4 / 370 | 4 / 453 | 1 / 166 ; 0 / 165 |

The complete metrics preserve all per-frame signs, finite counts, medians, available values, valid-reference status, support and unavailable outcomes without clipping or sign changes. The two frames are views of the same products and may retain different native source samples; they are not independent exposures.

Positive finite ERR support is absent in all forty-two profiles. Compact NPZs retain signed flux, original source indices and coordinates, frame-conversion information, available ERR samples, support and normalization status. Load arrays with `allow_pickle=False`. Valid positive references, false low-reference flags in supported rows and full core support do not establish calibrated uncertainty, formal significance, sensitivity, a physical origin or a qualified survey null. Fixed-flank medians remain descriptive levels rather than established line-free continua. Native BUNIT is absent; merged ADU and unspecified native extracted scales are not a calibrated physical flux ratio. Full original FITS remain necessary for extraction-provenance checks.

## Seven observations and seven fixed references

C018 / R019 keeps **0114/0119/0124/0128/0133/0134/0138** together at original queue rows **33/38/42/46/50/51/54**. Every distinct discovery product remains a fixed reference. The exact member centers are 3869.3349999999996 Å for 0114/0133, 3869.3325 Å for 0119/0124/0134, and 3869.335 Å for 0128/0138. The common center **3869.33375 Å** is the midpoint of exact catalog extrema, not a fitted peak. Its fixed common core is [3869.08375, 3869.58375] Å and context [3866.33375, 3872.33375] Å. Exact original ±0.25 Å member intervals and discovery markers remain separately preserved in the [input instructions](../inputs/README.md); the common core differs at an edge by up to 0.00125 Å without post-value expansion.

First queue member 0114 was observed on **2022-01-21T06:51:10.597**, under publication ID `ADP.2022-01-22T01:09:14.958`, BERV **29.658729150824 km/s**. It fixes one common topocentric anchor **3868.9509913064876 Å**. Other references do not redefine that anchor. Original event-specific topocentric catalog centers remain distinct metadata computed with each discovery's own BERV; no per-reference recentering or favorable-reference selection occurs.

The target is **HD114783**, with its own seven January 2022–July 2023 observations and BERV span **59.073251754930496 km/s**. No HD114386 product, May singleton design, numeric anchor, BERV span or quality outcome is transferred. The 196 merged comparison slots are seven epochs × seven references × two frames × two regions. Per frame/region, seven rows are identical-product self comparisons; the other **42 directed nonself rows represent 21 unordered observation pairs plus 21 reciprocal duplicates**. Shared reference, reciprocal, frame and region comparisons reuse observations and pixels. The other 56 comparison slots are same-exposure native-to-merged rows from fourteen order contexts, not additional observations or independent confirmation. Forty-two profiles and 252 slots still use only seven observing products.

Original C018 epoch/profile/raw evidence and the completed wider 0128 mapping diagnosis already existed. Numeric wavelength overlap with C015 and older HD114386/HD112410/HD106515A contexts shares no observing products or source pixels because those are other targets. Completed 0092/C013 and 0104/C014 normalization routes remain skipped. This is dependent post-detection context, adding no observing time, blind validation, independent detection or archive-wide completeness.

## Mapping stages and 0128's distinct original history

Fresh scans of **all 72 order headers in each of seven native products**, 504 records in total, select **orders 2 and 3 for every discovery**, retaining all fourteen covering pairs. All cores and negative flanks are geometrically covered; every order-2 positive flank is absent in both common frames, while order 3 covers the full contexts and flanks. Exact source-specific coefficients, endpoints, event centers and raw coordinates remain in the [input inventory](../inputs/INPUT_INVENTORY.json). Header geometry, observed finite support, valid normalization and raw registration are separate conditions.

For every event, original order-2 global-grid support is true, while original local-usable and baseline-verified flags remain **false**. Later five-window support is true. Order 3 is true at every original stage. Batch03's baseline field is `baseline_mapping_verified`; original 0128 raw_followup uses `mapping_verified`. Later support does not rewrite an original failed local/baseline stage. No completed mapping diagnostic or registration is rerun.

Six batch03 events retain exact original primary/secondary/adopted **U/U/U** reviews for broad overlapping-order features and diffuse trace-associated raw structure. The historical remote bright pixel in 0134's order-2 panel does not classify the central diffuse feature.

**0128 is preserved separately.** Its original raw_followup primary code is **I**, secondary code **M**, explicitly normalized to **I**, with adopted baseline **I / INSUFFICIENT_LOCAL_RAW_MAPPING**. Its later completed five-window reference diagnosis at unchanged coordinates supports both orders; separate later visual reviews are **U/U**, with current adopted **U**. The inventory keeps exact original records, later records, coordinate metadata, historical verification and preservation declarations as separate stages. Every current C018 event remains U. Neither current support nor profile correlation establishes an origin or qualifies a laser candidate.

All fourteen preserved raw NPZs are **original containers**. Twelve batch03 containers retain their stored raw, baseline, background/excess and native arrays. The two original 0128 baseline containers retain five arrays each and remain exactly:

| Original panel | Bytes | SHA256 |
|---|---:|---|
| 0128 order 2 | 2,993 | `611ae2dc067904173f901bf03208b6191a3df2adacbcb78179cce75c4a5576ee` |
| 0128 order 3 | 3,158 | `99477055051b5e031ccd24afafa3371506c0178621d808d8f5325e23fc3d4be6` |

These originals are not replaced by the distinct larger later wider NPZ containers. The original `RAW_BASELINE_EVIDENCE.zip` is 604,677 bytes, SHA256 `4c906bcd33fdef20b4045e65df73d34e5871eeb333b905cf16316a7210866996`; original members and the historical preserved-input hash ledger agree. The later wider archive and its recorded unchanged-coordinate/original-pixel preservation declarations remain separately bound. This phase verifies exact original raw-copy bytes and retained metadata, without rerunning the completed diagnosis or claiming a new independent test of the older pixel-preservation declarations. No panel is fitted, cropped or subtracted anew.

## Public method and release

All **25 prospective files** were published at commit [`514cece459dc1feefafbd2a6faef3958f00ce325`](https://github.com/andersenmartin-blip/setisearch/commit/514cece459dc1feefafbd2a6faef3958f00ce325) and read back exactly before execution. The [publication receipt](../PROSPECTIVE_PUBLICATION_RECEIPT.json) records both public branches and **935,255 verified bytes**. Receipt SHA256: `01d4c5d37e9c7cd6d23572550599e4570d6aad1c0d8e37077b1a693c4d576252`.

The unchanged [plan](../analysis/PLAN.json) has SHA256 `06e746071ba547165c9f2a435581d6b7f1c7f51c9c0682fb7fbd6a0bea18a4b3`. The [root release](../analysis/ROOT_RELEASE.json), issued at **2026-11-03T17:55:13.026388+00:00**, has SHA256 `9a5a7ee8c32878d6e554918c183e64e1f8a63e904d69e37981a910684953e5b3`. All **103 plan-bound source hashes**, all **24 files bound by the root freeze**, and all 25 exact public-method file identities were checked unchanged while finalizing this note. The [preflight freeze](../PREFLIGHT_FREEZE.json) and prospective reviews preserve the pre-array contract.

The runner validates release and source hashes, performs the fixed comparison once and rejects an existing results directory. Preserve that guard and all completed outputs. The [independent reconstruction](../independent_audit/NUMERICAL_AUDIT.json) passed **1,268 checks across 161,625 scalar values**, covering every profile, comparison, bounded window, all fourteen exact original raw copies, self pairs and retained staged history without importing production functions. Audit report SHA256: `4b493e834f819a0d4e2fa651a1c40dd11624812f5f64c2245e28341d90da40f7`. Computational reconstruction does not supply independent observations or a physical-origin conclusion.

## Recover exact archived inputs

The [input inventory](../inputs/INPUT_INVENTORY.json), SHA256 `dea91e8d3288079c5d0fbfb1df5922ba1156375515a6714a426edba1afed8fa5`, binds **35 restored files**: seven target-specific merged FITS, seven discovery ancillary TARs, seven native-A FITS and fourteen original raw-context NPZs. All five complete existing source archives were verified against original sizes and hashes. Two were already cached; three missing archives were recovered from their previously saved identities. No live telescope/archive query, duplicate archive upload or full-package duplication was needed.

| Existing archive | Restored contents | Original registries |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven HD114783 merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART3_2026-11-01.zip` | 0114 ancillary product | [Batch03 saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART4_2026-11-01.zip` | 0119/0124/0133/0134 ancillary products | Same batch03 instructions and registry |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART5_2026-11-01.zip` | 0138 ancillary product | Same batch03 instructions and registry |
| `SETI_HARPS_EXTENSION02_RAW_INPUTS_PART1_2026-11-01.zip` | Separate original 0128 ancillary product | [Original raw restore](../../work_harps_20261101/v2/extension02/raw_followup/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |

Twelve batch03 panels are reconstructed from unchanged committed evidence parts; the two 0128 panels come from the unchanged original baseline archive. Full raw detector products remain in existing saved archives and are not extracted for profile arithmetic. The [input instructions](../inputs/README.md) retain every archive/member identity, header convention, exact individual core and historical qualification.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c018_context/inputs/restore_inputs.py \
  --archive-dir /path/to/merged/archive/cache \
  --archive-dir /path/to/batch03/archive/cache \
  --archive-dir /path/to/remaining/archive/cache
```

One cache may hold all five archives. The helper verifies whole archives and selected members, rejects differing destinations, reuses identical bytes and writes deterministic metadata. It inspects FITS/NPY headers without executing the scientific comparison, completed diagnostic or network request. Local cache paths do not enter the metadata. Full restored FITS/TAR and temporary panel copies are excluded from Git; compact result evidence is retained with the analysis.

## Preserve the completed record

Reproduce in a separate checkout with this phase's `analysis/results/` absent before its first run, following the [analysis instructions](../analysis/README.md). Preserve the published input identities, code, method, root release and completed outputs. Do not reset the authoritative one-shot guard. Reproduction timestamps may differ; compare scientific arrays and numerical records.

All original review votes, failed and supported mapping stages, baseline and current dispositions, survey counts and prior analyses remain unchanged. Reproduction of this fixed context does not authorize favorable-reference selection, shifted windows, extra fitted parameters, completed-diagnostic replay or an independent-detection claim.
