# Exact archived inputs for C019 / HD114783

Header-only restoration verifies **27 exact files**: all seven existing HD114783 merged spectra, five discovery ancillary TARs, five complete native-A FITS products and ten original native/raw NPZ panels. Four complete cached archives and every selected member were verified. No new download, live telescope/archive acquisition, observed flux or detector-pixel interpretation, historical edit, new registration or completed-diagnostic replay was performed.

## Seven observations and five fixed references

Original queue row 34 fixes the complete five-member C019 / R020 joint group. All five discovery products remain comparison references. The March 22 and July 1 2023 observing epochs stay in the seven-product cohort without becoming C019 discovery references.

| Record | Queue row | Discovery product | Exact catalog center (Å) | Original ±0.25 Å core (Å) |
|---|---:|---|---:|---|
| 0115 | 34 | ADP.2022-01-22T01:09:14.958 | 3881.6125 | 3881.3625 to 3881.8625 |
| 0120 | 39 | ADP.2022-02-06T01:07:28.382 | 3881.615 | 3881.365 to 3881.865 |
| 0125 | 43 | ADP.2022-05-06T01:04:00.123 | 3881.6150000000002 | 3881.3650000000002 to 3881.8650000000002 |
| 0129 | 47 | ADP.2023-01-17T01:07:48.581 | 3881.615 | 3881.365 to 3881.865 |
| 0135 | 52 | ADP.2023-05-16T01:01:18.574 | 3881.6125 | 3881.3625 to 3881.8625 |

The midpoint of exact catalog extrema 3881.6125 and 3881.6150000000002 evaluates to **3881.6137500000004 Å**. Preserve that float; it is not a fitted peak. The common metric core is [3881.3637500000004, 3881.8637500000004] Å and ±3 Å context [3878.6137500000004, 3884.6137500000004] Å. The common ±0.25 Å core differs from each original at an edge by up to 0.00125 Å and does not contain the entire union of original cores. Keep exact individual intervals and markers separately without post-value expansion.

First queue member 0115 was observed on **2022-01-21T06:51:10.597**, BERV **29.658729150824 km/s**. It fixes the independently recomputed common topocentric anchor **3881.2297765555622 Å** using `3881.6137500000004 / (1 + 29.658729150824 / 299792.458)`. Other references do not redefine the anchor. Each historical event-specific topocentric center is separately verified using its own exact catalog center and discovery BERV.

The same seven HD114783 observations run from January 2022 through July 2023, with BERV −29.0643174950811 to +30.0089342598494 km/s and span **59.073251754930496 km/s**. Five references each compare with six other epochs: **30 directed nonself rows per frame/region represent 20 distinct unordered observation pairs plus 10 reciprocal duplicates**, using seven observations. Keep every source/reference identity and per-reference summary; these rows and pairs are not independent detections.

C019 reuses C018's seven observations and some identical complete native products. The new bounded ±3 Å spectral windows are disjoint, while complete original historical raw containers are preserved separately. Bounded-window disjointness does not establish independence of observations or all historical raw crops. C005's numeric wavelength overlap is on HD106515A and shares no observing products or source pixels. Original C019 epoch/profile/raw evidence already existed: this is dependent post-detection context, not blind, untouched or independent new data, and adds no observing time or archive-wide completeness. Completed mapping and normalization routes are not replayed.

## Fresh headers in each discovery product

[INPUT_INVENTORY.json](INPUT_INVENTORY.json) binds exact product identities, dates, BERV, raw progenitors, archive members and hashes. Each native product has a fresh scan of **all 72 order headers**, totaling **360 flat records keyed by product/order**. Every polynomial has a positive wavelength derivative over pixels 0–4095. Every discovery independently selects **orders 3 and 4**, agreeing with its own original covering-order records. All ten covering pairs remain; none is excluded.

| Event | Order-3 topocentric-air endpoints (Å) | Order-4 topocentric-air endpoints (Å) |
|---|---|---|
| 0115 | 3851.27138904318 to 3894.4977661376442 | 3875.7960726738 to 3919.2999685104774 |
| 0120 | 3851.27134612781 to 3894.4979569967977 | 3875.79586655284 to 3919.2999300164397 |
| 0125 | 3851.27189225561 to 3894.4976229097265 | 3875.79613571741 to 3919.2998597992373 |
| 0129 | 3851.27016967241 to 3894.4972296844776 | 3875.79516939862 to 3919.2983912736076 |
| 0135 | 3851.27014455048 to 3894.496672594678 | 3875.79471585105 to 3919.2984382778413 |

**Every selected order covers the full common context, core and both fixed reference flanks in both frames.** All twenty native frame rows have coordinate support for 601 grid centers, 51 core centers and 550 surrounding centers. Full per-product endpoints, coefficients, original event centers and fixed-frame geometry remain in the inventory. C018's order-2 missing-flank geometry and raw-only outcomes are not transferred. Coordinate coverage is distinct from finite flux, positive references, normalization quality, calibrated uncertainty or physical origin; each runtime missing, nonpositive, low-reference or blocked outcome must remain explicit in the separately frozen analysis.

Each native header shape is 72×4096, with degree 3 wavelength and degree 4 trace polynomials evaluated at zero-based pixels 0–4095. Merged wavelengths are barycentric air angstrom and uncalibrated ADU; ERR is declared unavailable. The historical native convention remains topocentric air angstrom. Native BUNIT is absent in all five products, so extracted units remain unspecified. NPY headers preserve panel and native-snippet shapes without reading array values. Publication IDs and observation timestamps remain distinct.

## Original mapping support and unassessed later fields

All ten original order-3/4 contexts retain **true** global-grid, original local-usable and original baseline-verified fields. The eight batch03 rows for 0115/0120/0125/0135 also explicitly retain **true** later five-window support. For original raw_followup event **0129**, the later-five-window field is **absent**, and neither its order records nor its event occur in the selected later mapping-followup records. Its canonical later-support fields therefore remain **null/unassessed**, with field presence false; do not replace absence with supported or unsupported status.

`mapping_records` retains all original native-pixel/raw-row/raw-column coordinates, exact mapping-source paths and baseline-field basis. Batch03 uses `baseline_mapping_verified`; original 0129 uses `mapping_verified`. The inventory explicitly records `UNASSESSED_FIELD_ABSENT_NOT_SELECTED_FOR_FOLLOWUP` for 0129. Supported original mapping, later field presence and fresh geometry remain separate facts; no new registration or mapping diagnostic is executed.

All five original primary/secondary/adopted review sets remain **U/U/U**, including 0129's original secondary U normalized to U and adopted baseline U. All five current labels remain U. The distinct C018/0128 I/M-normalized-I/baseline-I history and failed order-2 stages do not belong to C019/0129. Historical descriptions retain broad matching profiles and diffuse science-trace-associated enhancement without an established origin. The remote off-trace pixel noted for 0135 order 3 does not classify its central diffuse feature.

`historical_raw_review_records` separates `batch03_original` (four exact original sets), `separate_raw_followup_0129` (original U records, current U, empty later-selection records and null/unassessed later support), `current_adopted` (five current source rows) and `per_event_history` (five exact staged summaries). No later review or preservation declaration from another event is applied to 0129.

## Ten original panel containers

All ten restored panels are the original event-specific containers. Eight batch03 NPZs retain their original raw/background/excess, baseline and native arrays. The two original 0129 baseline NPZs retain five arrays each: raw cutout, background, excess, native wavelength and native flux. Their exact identities are:

| Original 0129 panel | Bytes | SHA256 |
|---|---:|---|
| Order 3 | 3,253 | `7cd1c059bcf483750405adbabfcad53453afcaa4fccf58ef638d9dabb1cad061` |
| Order 4 | 3,059 | `128c8ba54611e7ac1309e8dd5dcd96b5b69b0ff728bb19cf0e7dbdff446ccfa4` |

The unchanged original `RAW_BASELINE_EVIDENCE.zip` and member manifest are verified. No later container is substituted and no unperformed later diagnostic is claimed for 0129. Supported mapping or morphology does not qualify a laser or assign a physical origin.

## Restore exact bytes

Four existing cached archives supply the inputs:

| Archive | Selected contents | Original registries |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven HD114783 merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART3_2026-11-01.zip` | 0115 ancillary product | [Batch03 saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART4_2026-11-01.zip` | 0120/0125/0135 ancillary products | Same batch03 instructions and registry |
| `SETI_HARPS_EXTENSION02_RAW_INPUTS_PART1_2026-11-01.zip` | Separate original 0129 ancillary product | [Original raw restore](../../work_harps_20261101/v2/extension02/raw_followup/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |

Complete archive sizes/hashes and exact selected members are bound in the inventory. No new file transfer, duplicate archive upload or live telescope query was needed. Eight batch03 panels are reconstructed from unchanged committed evidence parts; the two 0129 panels come from the unchanged original baseline archive. Full raw detector products remain in existing saved archives and are not extracted for profile arithmetic.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c019_context/inputs/restore_inputs.py \
  --archive-dir /path/to/merged/archive/cache \
  --archive-dir /path/to/batch03/archive/cache \
  --archive-dir /path/to/original/raw/archive/cache
```

One cache may hold all four archives. The helper verifies whole archives and selected members, rejects differing destinations, reuses identical bytes and writes deterministic metadata without local cache paths. Its FITS/NPY inspection is header-only; it executes no scientific comparison, completed diagnostic or network request. Preserve published methods and completed outputs; reproduce separately. Full restored FITS/TAR and temporary panel copies are excluded from Git.
