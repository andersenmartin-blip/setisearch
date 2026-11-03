# Exact archived inputs for C015 / HD114386

Header-only restoration verifies **10 exact files**: all seven existing HD114386 merged cohort spectra, one May 2022 discovery ancillary TAR, one complete native-A FITS product and the original event-specific native/raw NPZ panel. Complete source-archive and selected-member hashes were checked. No live telescope/archive acquisition, new flux or detector-pixel interpretation, historical edit or new registration was performed.

| Record | Queue row / group | Discovery product | Observation timestamp | Covering native order |
|---|---|---|---|---:|
| V2E2-0095 | 28 / C015 / R016 | ADP.2022-05-17T01:02:16.724 | 2022-05-16T02:17:40.312 | 3 |

Original queue row 28 fixes this singleton after the complete four-member C016 group. C015 retains its own sole May 2022 discovery reference. Its exact barycentric-air catalog center is **3869.915 Å**, discovery BERV **−10.767337430651 km/s**, and independently computed fixed topocentric-air anchor **3870.0539967497375 Å**, using `3869.915 / (1 - 10.767337430651 / 299792.458)`. No C016 midpoint, March anchor, four-reference joint design or order-19 scope is transferred. The original core is [3869.665, 3870.165] Å and the proposed ±3 Å barycentric context [3866.915, 3872.915] Å.

The same seven existing HD114386 observations run from 2022-01-06 to 2023-08-27, with BERV −24.8175760325439 to +26.7544256646121 km/s and span **51.572001697156 km/s**. The May reference and full native product were also used by C016 at a different order and wavelength. C015's window is disjoint from C016's [4300.7875, 4306.7875] Å context and the completed [blue normalization windows](../../work_harps_20261101/v2/extension02/normalization_context_20261102/README.md). The completed 0092/C013 and 0104/C014 normalization routes remain skipped rather than replayed.

Numerical wavelength overlaps with earlier HD106515A C002/C003/C004 and HD112410 C011/C012 windows share no observing products or source pixels because those are other targets. Original 0095 epoch/profile and raw evidence already existed, and the same HD114386 cohort has prior normalization evidence at other blue wavelengths. Reusing these observations does not make C015 blind, untouched or independent new data and adds no observing time or archive-wide completeness.

## Fresh native scope

[INPUT_INVENTORY.json](INPUT_INVENTORY.json) binds exact product identities, dates, BERV, raw progenitors, archive members and hashes. The fresh scan of **all 72 May native order headers** records endpoints and positive wavelength derivatives across pixels 0–4095. **Only order 3 covers the original catalog center**. It covers the entire original core, proposed context and both fixed reference flanks in both frames, and is retained with its one original raw panel. No covering order is excluded.

| Selected order | Topocentric-air endpoints (Å) | Barycentric-air endpoints (Å) | Full ±3 Å context and both flanks |
|---:|---|---|---|
| 3 | 3851.27166904696 to 3894.4973838317906 | 3851.1333468827725 to 3894.3575091740545 | Yes, both frames |

Order 3 has coordinate support for all **601** grid centers, **51** core centers and **550** surrounding centers in each fixed frame. The adjacent order 2 ends at 3870.006986547364 Å topocentric, below C015's 3870.0539967497375 Å original center; it is not a covering order and is not an excluded covering-context slot. All 72 scan records remain explicit. The complete selected-order coefficients, endpoints, masks and fixed-frame geometry are retained under `native_products[].orders[].fixed_frame_header_geometry`.

This is a fresh geometry result for C015's wavelength in the May product. Coordinate coverage does not establish finite flux, positive references, valid normalization, calibrated uncertainties or physical origin. The separately frozen analysis must retain each runtime missing, nonpositive, low-reference or blocked outcome explicitly. No previous target's or C016's quality outcome is transferred.

The native header shape is 72×4096. Degree 3 wavelength and degree 4 trace coefficients are retained for order 3, with ascending coefficients evaluated at zero-based pixels 0–4095. Merged wavelengths are barycentric air angstrom and uncalibrated ADU; ERR is declared unavailable. The historical native convention remains topocentric air angstrom. Native BUNIT is absent, so extracted units remain unspecified. NPY headers preserve saved panel and native-snippet shapes without reading array values. Publication identifiers and observation timestamps remain distinct.

## Historical mapping and review limits

| Original event / order | Global grid usable | Original local usable | Original baseline verified | Later five-window support |
|---|---|---|---|---|
| 0095 / 3 | true | true | true | true |

`mapping_records` retains each original stage, native pixel 1619, raw row 2476 and raw column 126.71408818235776. These all-true stages come from 0095's own order-3 evidence. Other targets' mapping limits and another blue normalization raw-window registration discrepancy are not transferred here. Header coverage and supported historical mapping do not establish physical origin; no new mapping test is performed.

`historical_raw_review_records` preserves the exact primary, secondary, root-adopted and comparison records. All review stages retain **U/U/U**. Historical evidence describes a broad native feature spanning many dispersion samples and smooth diffuse trace-associated raw enhancement, without a distinct charge track. Restoration does not replace those votes, establish a charge-deposit or spectral origin, or qualify a laser candidate. The complete original raw panel, background/excess arrays, baseline arrays and native snippets remain intact. Its hash is checked directly against the original mapping table and the evidence manifest.

## Restore exact bytes

Two existing archives supply the inputs:

| Archive | Selected contents | Original instructions and receipts |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | All seven HD114386 merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART2_2026-11-01.zip` | May 2022 discovery ancillary product | [Saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json) |

Both complete archives were reused from existing caches only after exact whole-file verification. The inventory records complete archive sizes/hashes and exact selected members. No new file transfer, duplicate archive package or live telescope query was needed. The 0095 raw-context NPZ is reconstructed from unchanged committed batch03 evidence parts; its exact SHA256 is `2940f494ab65835f39b2a06aa879d47b7fc46c01bc4fc14eaa42921e98b53bba`. Full raw detector products remain in the existing archive and are not restored for this profile context.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c015_context/inputs/restore_inputs.py \
  --archive-dir /path/to/merged/archive/cache \
  --archive-dir /path/to/native/archive/cache
```

One cache may hold both archives. The helper verifies complete archive and member hashes, reuses identical destinations, rejects differing bytes and writes deterministic metadata without local cache paths. Its FITS/NPY inspection is header-only and it executes no comparison or network request. Preserve published methods and completed outputs; reproduce separately. Full restored products and the temporary raw-panel copy are excluded from Git.
