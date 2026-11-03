# Exact archived inputs for C021 / HD114783

Header-only restoration verifies **22 exact files**: all seven existing HD114783 merged spectra, five discovery ancillary TARs, five complete native-A FITS products and five original native/raw NPZ panels. Five complete cached archives and every selected member were verified. No new download, live telescope/archive acquisition, observed flux or detector-pixel interpretation, historical edit, new registration or completed-diagnostic replay was performed.

## Seven observations and five exact references

Original queue row 35 fixes the complete five-member C021 / R022 group. Retain all five discovery references together at rows 35/40/44/48/55. The March 22 and May 15 2023 products remain observing epochs without becoming C021 references. **July 1 is a C021 reference**, replacing C019's May 15 reference in the reference set; equal reference counts do not make the identities interchangeable.

| Record | Queue row | Discovery product | Exact catalog center (Å) | Original ±0.25 Å core (Å) |
|---|---:|---|---:|---|
| 0116 | 35 | ADP.2022-01-22T01:09:14.958 | 4309.827499999999 | 4309.577499999999 to 4310.077499999999 |
| 0121 | 40 | ADP.2022-02-06T01:07:28.382 | 4309.827499999999 | 4309.577499999999 to 4310.077499999999 |
| 0126 | 44 | ADP.2022-05-06T01:04:00.123 | 4309.825 | 4309.575 to 4310.075 |
| 0130 | 48 | ADP.2023-01-17T01:07:48.581 | 4309.825 | 4309.575 to 4310.075 |
| 0139 | 55 | ADP.2023-07-02T01:01:43.311 | 4309.827499999999 | 4309.577499999999 to 4310.077499999999 |

The exact catalog-extrema midpoint evaluates to **4309.82625 Å**, not a fitted peak. Its common metric core is [4309.57625, 4310.07625] Å and ±3 Å context [4306.82625, 4312.82625] Å. The fixed ±0.25 Å metric core differs from original edges by up to 0.00125 Å and does not contain their complete union. Preserve the original exact floats, intervals and discovery markers separately without post-value expansion.

First queue member 0116 was observed on **2022-01-21T06:51:10.597**, BERV **29.658729150824 km/s**. It fixes the independently recomputed common topocentric anchor **4309.39991731037 Å** using `4309.82625 / (1 + 29.658729150824 / 299792.458)`. Every original event-specific topocentric center is separately checked using its own exact catalog center and discovery BERV. Other references do not redefine the common coordinate anchor.

The same seven HD114783 observations run from January 2022 through July 2023, with BERV −29.0643174950811 to +30.0089342598494 km/s and span **59.073251754930496 km/s**. Five references each compare six other epochs: **30 directed nonself rows per frame/region represent 20 unordered observation pairs plus 10 reciprocal duplicates**, sharing seven observations. Preserve exact reference/source identities and per-reference summaries; these rows and pairs are not independent detections.

C021 reuses C018/C019 observations and some identical complete native products at a disjoint newly bounded spectral window. Historical raw containers remain separately preserved; bounded-window disjointness does not establish independent observations or independence of every complete saved crop. Numeric overlaps with C006/C007 use HD106515A and share no products or source pixels. The nearby other-target HD114386 C016 window is disjoint by approximately 0.03875 Å. Original C021 epoch/profile/raw evidence and the completed wider 0130 mapping diagnosis already exist. This is dependent post-detection context, not blind, untouched or independent new data; it adds no observing time or archive-wide completeness. Completed mapping and normalization routes are not replayed.

## Fresh headers in every discovery product

[INPUT_INVENTORY.json](INPUT_INVENTORY.json) binds exact product identities, dates, BERV, raw progenitors, archive members and hashes. Each native product has a fresh scan of **all 72 order headers**, totaling **360 flat records keyed by product/order**. Every polynomial has a positive wavelength derivative over pixels 0–4095. Every discovery independently selects **order 19 only**, agreeing with its own original covering-order record. All five covering pairs remain; none is excluded.

| Event | Native order | Topocentric-air endpoints (Å) |
|---|---:|---|
| 0116 | 19 | 4285.09715793688 to 4333.250210121655 |
| 0121 | 19 | 4285.0970492084 to 4333.250216838259 |
| 0126 | 19 | 4285.09737976191 to 4333.250218570714 |
| 0130 | 19 | 4285.09576714302 to 4333.2484424843005 |
| 0139 | 19 | 4285.09459649946 to 4333.248619024135 |

**Every selected product covers the full common context, core and both fixed reference flanks in both frames.** All ten native frame rows have coordinate support for 601 grid centers, 51 core centers and 550 surrounding centers. Exact per-product barycentric/topocentric endpoints, coefficients, event centers and fixed-frame geometry remain in the inventory. Coordinate coverage does not establish finite flux, positive references, normalization quality, calibrated uncertainty or physical origin; each runtime missing, nonpositive, low-reference or blocked outcome must remain explicit in the separately frozen analysis. No C019 quality outcome or C018 order-2 coverage limit is transferred.

Each native header shape is 72×4096, with degree 3 wavelength and degree 4 trace polynomials evaluated at zero-based pixels 0–4095. Merged wavelengths are barycentric air angstrom and uncalibrated ADU; ERR is declared unavailable. The historical native convention remains topocentric air angstrom. Native BUNIT is absent in all five products, so extracted units remain unspecified. NPY headers preserve original panel/native-snippet shapes without reading array values. Publication IDs and observation timestamps remain distinct.

## Source-specific mapping stages

| Original event / order | Global grid usable | Original local usable | Original baseline verified | Later five-window support |
|---|---|---|---|---|
| 0116 / 19 | true | **false** | **false** | true |
| 0121 / 19 | true | true | true | true |
| 0126 / 19 | true | **false** | **false** | true |
| 0130 / 19 | true | **false** | **false** | true |
| 0139 / 19 | true | true | true | true |

`mapping_records` retains each original native-pixel/raw-row/raw-column coordinate, exact source path and baseline-field basis. Batch03 explicitly uses `baseline_mapping_verified`; original 0130 raw_followup uses `mapping_verified`. The later 0130 support comes from its separate completed mapping-followup order record at exactly the original native/raw coordinates. Later reference support does not rewrite the three original failed local/baseline stages. No null/unassessed C019/0129 field is transferred to this assessed 0130 context. Header geometry, normalization quality and supported mapping remain separate from physical origin.

## Distinct original and later review histories

Four batch03 members, 0116/0121/0126/0139, retain original primary/secondary/adopted **U/U/U**. Their broad native profiles and diffuse trace-associated raw enhancements remain unresolved, including the separately recorded original mapping limits for 0116 and 0126.

**0130 has a separate history and original evidence source.** Its original raw_followup primary code is **I**, secondary **M**, explicitly normalized to **I**, with adopted baseline **I / INSUFFICIENT_LOCAL_RAW_MAPPING**. A later completed wider five-window diagnosis and separate visual reviews at unchanged coordinates retain **U/U/current U**. Preserve every original and later stage; the later support neither repairs the original failed gate retroactively nor establishes a specific origin. Every current C021 event remains U.

`historical_raw_review_records` separates `batch03_original` (four exact original review sets), `separate_raw_followup_0130` (exact original/later records, verification, archive identity and recorded preservation declarations), `current_adopted` (five current source rows) and `per_event_history` (five staged summaries). The older declarations of unchanged coordinates/preserved original pixels remain historical records; restoration does not decode arrays to re-prove them or replay the completed mapping diagnosis. Do not transfer 0129's original-U/null-later history to 0130 or flatten C021 into blanket original U reviews.

## Five original raw containers

Four original batch03 NPZs retain their raw/background/excess, baseline and native arrays. The original **0130 order-19 baseline NPZ** retains five arrays: raw cutout, background, excess, native wavelength and native flux. It remains exactly **3,532 bytes**, SHA256 **`a7dd8a01661a3a51629a1939b159814059d02acd8b5ce32433538f4bf9e0272e`**.

This original is not replaced by its distinct later wider container, **5,534 bytes**, SHA256 `1474320f43541da160cacb6c8cf7f1664b3df29ae38d95a5e689d51c03181d0b`. Original baseline ZIP/member and historical preserved-input hashes are verified; the later wider evidence archive and recorded sample-preservation declarations remain separately bound. No panel is newly fitted, cropped or subtracted. Neither supported mapping nor morphology qualifies a laser or assigns a physical origin.

## Restore exact bytes

Five complete cached archives supply the inputs:

| Archive | Selected contents | Original registries |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven HD114783 merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART3_2026-11-01.zip` | 0116 ancillary product | [Batch03 saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART4_2026-11-01.zip` | 0121/0126 ancillary products | Same batch03 instructions and registry |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART5_2026-11-01.zip` | 0139 ancillary product | Same batch03 instructions and registry |
| `SETI_HARPS_EXTENSION02_RAW_INPUTS_PART1_2026-11-01.zip` | Separate original 0130 ancillary product | [Original raw restore](../../work_harps_20261101/v2/extension02/raw_followup/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |

The inventory binds complete archive sizes/hashes and exact selected members. No new transfer, duplicate archive upload or live telescope query was needed. Four batch03 panels are reconstructed from unchanged committed evidence parts; the original 0130 panel comes from unchanged `RAW_BASELINE_EVIDENCE.zip` and its manifest, cross-checked against the preserved-input ledger. Full detector products remain in existing archives and are not extracted for profile arithmetic.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c021_context/inputs/restore_inputs.py \
  --archive-dir /path/to/merged/archive/cache \
  --archive-dir /path/to/batch03/archive/cache \
  --archive-dir /path/to/original/raw/archive/cache
```

One cache may hold all five archives. The helper verifies whole archives and selected members, rejects differing destinations, reuses identical bytes and writes deterministic metadata without local cache paths. Its FITS/NPY inspection is header-only; it executes no scientific comparison, completed diagnostic or network request. Preserve published methods and completed outputs; reproduce separately. Full restored FITS/TAR and temporary panel copies are excluded from Git.
