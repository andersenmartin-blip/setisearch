# Exact archived inputs for C012 / HD112410

Header-only restoration verifies **11 exact files**: all seven existing HD112410 merged cohort spectra, one discovery ancillary TAR, one complete native-A FITS product and both original event-specific native/raw NPZ panels. Complete source-archive and selected-member hashes were checked. No live telescope/archive acquisition, new flux or detector-pixel interpretation, historical edit or new registration was performed.

| Record | Discovery product | Observation date | Covering native orders |
|---|---|---|---|
| V2E2-0087 | ADP.2025-04-30T01:01:50.866 | 2025-04-29T03:06:38.398 | 2, 3 |

Original queue row 24 fixes the singleton C012 / R013 and its one April 2025 discovery reference. The barycentric-air catalog center is **3869.2675 Å**, discovery BERV **3.40485846065643 km/s**, and independently computed fixed topocentric-air anchor **3869.2235557371996 Å**, using `3869.2675 / (1 + 3.40485846065643 / 299792.458)`. The numeric C010 anchor is not transferred. The original core is ±0.25 Å and the proposed wider context ±3 Å in each fixed frame.

The same seven existing HD112410 observations run from 2025-04-29 to 2025-08-07 and span BERV −17.8979901476463 to +3.40485846065643 km/s, a range of **21.30284860830273 km/s**. Original 0087 epoch/profile and raw evidence already existed. The proposed barycentric window [3866.2675, 3872.2675] Å and core [3869.0175, 3869.5175] Å are separate from C010's window on this target. Their numeric wavelengths overlap older HD106515A blue windows, but those are different observing products and pixels. Reused observations and old evidence do not make this blind, untouched or independent new data and add no observing time or archive-wide completeness.

[INPUT_INVENTORY.json](INPUT_INVENTORY.json) binds product identities, dates, BERV, raw progenitors, exact archive members and restored hashes. The fresh scan of **all 72 native order headers** records endpoints and positive wavelength derivatives across the complete native product. Only orders 2 and 3 cover the original center; both cover the entire original core and are retained with their two historical raw panels. No covering order is excluded.

| Order | Lower topocentric-air endpoint (Å) | Upper endpoint (Å) | Upper fixed-frame offset B/T (Å) | Full ±3 Å context |
|---:|---:|---:|---|---|
| 2 | 3827.04557082137 | 3869.9999605859994 | +0.7764136667287858 / +0.776404848799757 | No |
| 3 | 3851.2610722297 | 3894.4910032774533 | +25.2677345123916 / +25.26744754025367 | Yes |

The order 2 core and negative [−3, −1.5] Å reference flank are geometrically covered in both frames, but its entire positive [+1.5, +3] Å flank is absent. At most 378 of the fixed 601 grid centers and 327 of the 550 surrounding centers have coordinate support. Thus the unchanged two-flank rule must retain missing-right-flank normalization, and the 440-sample surrounding Pearson gate cannot be reached for order 2. Finite nonconstant core support remains a runtime check. This is a fresh geometry result for this product and wavelength; it is not a measured nonpositive two-sided reference or an inherited earlier-group outcome. Order 3 covers the complete context, core and both reference flanks in both frames. All endpoint and mask checks are retained under `native_products[].orders[].fixed_frame_header_geometry`.

Coordinate coverage does not establish finite flux, positive references, valid normalization, calibrated uncertainties or physical origin. The separately frozen analysis must retain each missing, nonpositive, low-reference or mapping-limited result explicitly.

Native header shape is 72×4096. Degree 3 wavelength and degree 4 trace coefficients are retained for both orders, with ascending coefficients evaluated at zero-based pixels 0–4095. Merged wavelengths are barycentric air angstrom and uncalibrated ADU; ERR is declared unavailable. The historical native convention remains topocentric air angstrom. Native BUNIT is absent, so its extracted units remain unspecified. NPY headers preserve the saved panel and native-snippet shapes without reading array values. Publication identifiers and observation timestamps remain distinct.

## Historical mapping and review limits

| Historical order | Global grid usable | Original local usable | Original baseline verified | Later five-window support |
|---:|---|---|---|---|
| 2 | true | false | false | true |
| 3 | true | true | true | true |

`mapping_records` retains each stage, native-pixel and raw-row/column coordinate. Later reference-window support does not retroactively repair order 2's original local/baseline limits. Header coverage is distinct from registration reliability; no new mapping test is performed.

`historical_raw_review_records` preserves the exact primary, secondary, root-adopted and comparison records. All three review stages retain **U**. Historical evidence describes broad enhancement across the overlapping orders, noisier order 2 and smoother order 3, with trace-associated raw structure. Restoration does not replace those votes, establish a charge-deposit or spectral origin, or qualify a laser candidate. Both original raw-panel hashes are checked directly against the unchanged historical mapping table as well as the evidence manifest.

## Restore exact bytes

Two existing archives supply the inputs:

- `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip`: all seven merged spectra; [restoration instructions](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md) and [source registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json).
- `SETI_HARPS_RAW_BATCH03_INPUTS_PART1_2026-11-01.zip`: the April discovery ancillary product; [saved-input instructions](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/SAVED_INPUTS.md) and [source registry](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json).

The inventory records complete archive sizes/hashes and exact selected members. The two event NPZs are reconstructed from unchanged committed batch03 evidence parts. Full raw detector products remain in the existing archive and are not restored for this profile context.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c012_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

One cache may hold both archives. The helper verifies complete archive and member hashes, reuses identical destinations, rejects differing bytes and writes deterministic metadata without local cache paths. Its FITS/NPY inspection is header-only and it executes no comparison or network request. Preserve published methods and completed outputs; reproduce separately. Full restored products and temporary raw-panel copies are excluded from Git.
