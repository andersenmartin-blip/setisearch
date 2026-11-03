# Exact archived inputs for C018 / HD114783

Header-only restoration verifies **35 exact files**: HD114783's own seven existing merged spectra, seven discovery ancillary TARs, seven complete native-A FITS products and all fourteen original native/raw NPZ panels. Five complete source archives and every selected member were verified. No live telescope/archive acquisition, new flux or detector-pixel interpretation, historical edit, new registration or completed-diagnostic replay was performed.

## Seven fixed references and exact catalog information

Original queue row 33 fixes the complete seven-member C018 / R019 joint group. Every discovery product remains a reference; the common coordinate anchor does not select a favorable comparison reference.

| Record | Queue row | Discovery product | Exact catalog center (Å) | Original ±0.25 Å core (Å) |
|---|---:|---|---:|---|
| 0114 | 33 | ADP.2022-01-22T01:09:14.958 | 3869.3349999999996 | 3869.0849999999996 to 3869.5849999999996 |
| 0119 | 38 | ADP.2022-02-06T01:07:28.382 | 3869.3325 | 3869.0825 to 3869.5825 |
| 0124 | 42 | ADP.2022-05-06T01:04:00.123 | 3869.3325 | 3869.0825 to 3869.5825 |
| 0128 | 46 | ADP.2023-01-17T01:07:48.581 | 3869.335 | 3869.085 to 3869.585 |
| 0133 | 50 | ADP.2023-03-23T01:02:04.833 | 3869.3349999999996 | 3869.0849999999996 to 3869.5849999999996 |
| 0134 | 51 | ADP.2023-05-16T01:01:18.574 | 3869.3325 | 3869.0825 to 3869.5825 |
| 0138 | 54 | ADP.2023-07-02T01:01:43.311 | 3869.335 | 3869.085 to 3869.585 |

The common center **3869.33375 Å** is the midpoint of the exact minimum/maximum catalog centers, not a fitted peak. Its fixed common core is [3869.08375, 3869.58375] Å and ±3 Å context [3866.33375, 3872.33375] Å. The metric core differs from individual originals by up to 0.00125 Å at one edge. Preserve the exact original intervals and markers separately; do not expand or recenter after values.

The first queue member, 0114, was observed on **2022-01-21T06:51:10.597**, BERV **29.658729150824 km/s**. It fixes the independently recomputed common topocentric anchor **3868.9509913064876 Å** through `3869.33375 / (1 + 29.658729150824 / 299792.458)`. Each historical event center is separately checked against its own exact catalog center and discovery BERV; the other six references do not redefine the common anchor.

The target changes to **HD114783**, with its own seven observations from January 2022 through July 2023. BERV ranges from −29.0643174950811 to +30.0089342598494 km/s, a span of **59.073251754930496 km/s**. Do not transfer HD114386 products, the May singleton reference, numeric anchors, BERV span or quality outcomes. With seven references, 42 directed nonself comparisons per frame/region represent 21 unordered observation pairs and 21 reciprocal duplicates, using only seven observations. Original epoch/profile/raw evidence and the completed wider 0128 mapping diagnosis already exist. This is dependent post-detection context, not blind, untouched or independent new data; it adds no observing time or archive-wide completeness.

C018's numeric wavelength overlaps C015 and older HD112410/HD106515A blue contexts, but those other targets use different observing products and source pixels. Completed normalization routes for 0092/C013 and 0104/C014 are on HD114386 and remain skipped, not transferred or replayed.

## Fresh headers in every discovery product

[INPUT_INVENTORY.json](INPUT_INVENTORY.json) binds exact product identities, timestamps, BERV, raw progenitors, archive members and hashes. Each native product has a fresh scan of **all 72 order headers**, totaling **504 flat records keyed by product/order**. Every polynomial has a positive wavelength derivative over pixels 0–4095. Every discovery independently selects **orders 2 and 3**, agreeing with its own historical covering-order records. All fourteen covering pairs remain; none is excluded.

Every selected order covers the complete common core in both frames. Every order 3 covers the complete ±3 Å context and both reference flanks. **Every order 2 lacks the entire positive [+1.5, +3] Å reference flank in both common frames**, while its core and negative [−3, −1.5] Å flank are geometrically covered. The coordinate-only support counts are:

| Event | Order-2 raw grid support B/T, of 601 | Order-2 common core support B/T, of 51 | Order-2 surrounding support B/T, of 550 |
|---|---|---|---|
| 0114 | 406 / 406 | 51 / 51 | 355 / 355 |
| 0119 | 402 / 406 | 51 / 51 | 351 / 355 |
| 0124 | 351 / 406 | 51 / 51 | 300 / 355 |
| 0128 | 406 / 406 | 51 / 51 | 355 / 355 |
| 0133 | 379 / 406 | 51 / 51 | 328 / 355 |
| 0134 | 346 / 406 | 51 / 51 | 295 / 355 |
| 0138 | 330 / 406 | 51 / 51 | 279 / 355 |

Order-2 upper common-frame offsets range from approximately +0.2971 to +1.0597 Å barycentric and +1.0549 to +1.0563 Å topocentric, below the +1.5 Å right-flank start. The fixed two-flank rule must preserve missing-right-flank normalization, without borrowing order 3 or moving/shrinking a flank. Order-2 surrounding support cannot meet the fixed Pearson minimum of 440. Finite nonconstant core support remains a runtime check. Missing geometric coverage is distinct from a measured nonpositive two-flank reference. Order 3 has coordinate support for all 601 grid, 51 core and 550 surrounding centers in both frames.

Exact per-product endpoints, polynomial coefficients, original event centers and common-frame geometry remain in the inventory. Header coverage does not establish finite flux, reference quality, valid normalization, calibrated uncertainty or physical origin. Every runtime missing, nonpositive, low-reference or blocked outcome must remain explicit in the separately frozen analysis.

Each native header shape is 72×4096, with degree 3 wavelength and degree 4 trace polynomials evaluated at zero-based pixels 0–4095. Merged wavelengths are barycentric air angstrom and uncalibrated ADU; ERR is declared unavailable. The historical native convention remains topocentric air angstrom. Native BUNIT is absent in all seven products, so extracted units remain unspecified. NPY headers preserve original panel/native-snippet shapes without reading array values. Publication IDs and observation timestamps remain distinct.

## Original mapping stages and distinct review histories

For **each of all seven events**, original order-2 global-grid support is true, original local-usable and baseline-verified flags are **false**, and later five-window support is true. Original order 3 is true at all these stages. `mapping_records` keeps all fourteen original native-pixel/raw-row/raw-column coordinates, exact source paths, stage fields and baseline-field basis. Batch03 uses `baseline_mapping_verified`; original 0128 raw_followup uses `mapping_verified`. Later support does not retroactively repair the failed original order-2 stage. No new registration or mapping diagnostic is executed.

Six members, 0114/0119/0124/0133/0134/0138, come from `raw_followup_batch03` and retain their original primary/secondary/adopted **U/U/U** records. Their broad overlapping-order features and diffuse trace-associated raw structure remain unresolved. The remote bright pixel described in the historical 0134 order-2 review does not classify its central diffuse feature.

**0128 has a different history and evidence source.** Its original `raw_followup` primary code is **I**, secondary code **M**, explicitly normalized to **I**, with adopted baseline **I / INSUFFICIENT_LOCAL_RAW_MAPPING**. The later completed five-window follow-up at unchanged coordinates reports both orders supported and separate visual reviews **U/U**, followed by current adopted **U**. Preserve every stage and source separately. This history does not establish physical origin or authorize replay of the completed mapping diagnosis.

`historical_raw_review_records` separates `batch03_original` (six exact original review sets), `separate_raw_followup_0128` (exact original and later records), `current_adopted` (seven current source rows) and `per_event_history` (seven staged summaries). The later 0128 verification and declarations of unchanged coordinates/preserved original pixels are retained as historical records; restoration does not decode arrays to re-prove them.

All **fourteen original panel containers** are restored. The twelve batch03 panels retain their original raw/background/excess, baseline and native arrays. The two 0128 baseline NPZs contain their original five arrays: raw cutout, background, excess, native wavelength and native flux. They are **2,993 bytes / SHA256 `611ae2dc067904173f901bf03208b6191a3df2adacbcb78179cce75c4a5576ee`** and **3,158 bytes / SHA256 `99477055051b5e031ccd24afafa3371506c0178621d808d8f5325e23fc3d4be6`**. They are not replaced by the distinct larger later follow-up containers. The original baseline archive/member hashes and preserved-input ledger are verified; the later wider archive is separately hashed as historical custody. Supported mapping, morphology and current U labels do not qualify a laser or assign an origin.

## Restore exact bytes

Five existing archives supply the inputs:

| Archive | Selected contents | Original registries |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven HD114783 merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART3_2026-11-01.zip` | 0114 ancillary product | [Saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART4_2026-11-01.zip` | 0119/0124/0133/0134 ancillary products | Same batch03 instructions and registry |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART5_2026-11-01.zip` | 0138 ancillary product | Same batch03 instructions and registry |
| `SETI_HARPS_EXTENSION02_RAW_INPUTS_PART1_2026-11-01.zip` | Separate original 0128 ancillary product | [Original raw restore](../../work_harps_20261101/v2/extension02/raw_followup/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |

Two archives were already cached; three missing complete archives were recovered from their previously saved source identities and verified exactly. No duplicate archive upload or live telescope query was needed. The inventory binds complete archive sizes/hashes and selected members. Twelve batch03 panels are reconstructed from unchanged committed evidence parts; the two 0128 panels come from the unchanged `RAW_BASELINE_EVIDENCE.zip` and its original manifest. Full raw detector products remain in existing saved archives and are not extracted for profile arithmetic.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c018_context/inputs/restore_inputs.py \
  --archive-dir /path/to/merged/archive/cache \
  --archive-dir /path/to/batch03/archive/cache \
  --archive-dir /path/to/remaining/archive/cache
```

One cache may hold all five archives. The helper verifies whole archives and selected members, rejects differing destinations, reuses identical bytes and writes deterministic metadata without local cache paths. Its FITS/NPY inspection is header-only; it executes no comparison, completed diagnostic or network request. Preserve published methods and completed outputs; reproduce separately. Full restored FITS/TAR and temporary panel copies are excluded from Git.
