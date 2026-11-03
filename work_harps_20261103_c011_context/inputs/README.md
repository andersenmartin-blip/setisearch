# Exact archived inputs for C011 / HD112410

Header-only restoration verifies **11 exact files**: all seven existing HD112410 merged cohort spectra, one May discovery ancillary TAR, one complete native-A FITS product and both original event-specific native/raw NPZ panels. Complete source-archive and selected-member hashes were checked. No live telescope/archive acquisition, new flux or detector-pixel interpretation, historical edit or new registration was performed.

| Record | Discovery product | Observation date | Covering native orders |
|---|---|---|---|
| V2E2-0089 | ADP.2025-05-29T01:01:14.389 | 2025-05-28T05:06:00.591 | 2, 3 |

Original queue row 25 fixes the singleton C011 / R012 after C012 at row 24; numeric group order does not replace queue order. C011 uses its own May 2025 discovery reference. Its barycentric-air catalog center is **3865.6775000000002 Å**, discovery BERV **−5.48386283255014 km/s**, and independently computed fixed topocentric-air anchor **3865.748213029564 Å**, using `3865.6775000000002 / (1 - 5.48386283255014 / 299792.458)`. The April reference and numeric C010/C012 anchors are not transferred. The original core is ±0.25 Å and the proposed wider context ±3 Å in each fixed frame.

The same seven existing HD112410 observations run from 2025-04-29 to 2025-08-07 and span BERV −17.8979901476463 to +3.40485846065643 km/s, a range of **21.30284860830273 km/s**. Original 0089 epoch/profile and raw evidence already existed. The proposed barycentric window is [3862.6775000000002, 3868.6775000000002] Å and the original core [3865.4275000000002, 3865.9275000000002] Å.

C011 and C012 reuse the same seven merged products. Their broad barycentric windows overlap on [3866.2675, 3868.6775000000002] Å, a width of **2.4100000000003092 Å**, so surrounding and reference pixels can be shared. The original C011 core is entirely below the C012 window. The two phases use different discovery native/raw products: May 28 for C011 and April 29 for C012. C010's same-target window is disjoint. Numeric overlap with older HD106515A windows uses different observing products and source pixels. These dependencies and existing evidence make this post-detection context; it is not blind, untouched or independent new data and adds no observing time or archive-wide completeness.

[INPUT_INVENTORY.json](INPUT_INVENTORY.json) binds product identities, dates, BERV, raw progenitors, exact archive members and restored hashes. The fresh scan of **all 72 native order headers** records endpoints and positive wavelength derivatives across the complete May native product. Only orders 2 and 3 cover the original center. Both cover the entire original core, full proposed context and both fixed reference flanks in both frames, and are retained with their two historical raw panels. No covering order is excluded.

| Order | Lower topocentric-air endpoint (Å) | Upper endpoint (Å) | Upper fixed-frame offset B/T (Å) | Full ±3 Å context and both flanks |
|---:|---:|---:|---|---|
| 2 | 3827.04590550197 | 3870.000069396472 | +4.25177859111227 / +4.251856366908214 | Yes, both frames |
| 3 | 3851.2615075553 | 3894.490605015315 | +28.74186622424213 / +28.742391985751055 | Yes, both frames |

Both native orders have coordinate support for all 601 grid centers, all 51 core centers and all 550 surrounding centers. This is a fresh geometry result for the May product at C011's own wavelength. C012's partial order-2 coverage is not inherited. Coordinate coverage does not establish finite flux, positive references, valid normalization, calibrated uncertainties or physical origin. Each runtime missing, nonpositive, low-reference or blocked result must remain explicit under the separately frozen analysis.

Native header shape is 72×4096. Degree 3 wavelength and degree 4 trace coefficients are retained for both orders, with ascending coefficients evaluated at zero-based pixels 0–4095. Merged wavelengths are barycentric air angstrom and uncalibrated ADU; ERR is declared unavailable. The historical native convention remains topocentric air angstrom. Native BUNIT is absent, so its extracted units remain unspecified. NPY headers preserve the saved panel and native-snippet shapes without reading array values. Publication identifiers and observation timestamps remain distinct.

## Historical mapping and review limits

| Historical order | Global grid usable | Original local usable | Original baseline verified | Later five-window support |
|---:|---|---|---|---|
| 2 | true | true | true | true |
| 3 | true | true | true | true |

`mapping_records` retains each distinct stage and original native-pixel/raw-row/raw-column coordinate. Both orders' all-true stages are verified from 0089's own original records; C012's order-2 local/baseline failures are not transferred. Header coverage is distinct from registration reliability, and supported historical mapping does not prove physical origin. No new mapping test is performed.

`historical_raw_review_records` preserves the exact primary, secondary, root-adopted and comparison records. All three review stages retain **U**. Historical evidence describes broad native structure and diffuse central enhancement in both orders, with broad low-continuum, trace-confined raw enhancement. Restoration does not replace those votes, establish a charge-deposit or spectral origin, or qualify a laser candidate. Both complete raw panels, baseline/background/excess arrays and native snippets remain intact. Original raw-panel hashes are checked directly against the unchanged historical mapping table and the evidence manifest.

## Restore exact bytes

Two existing archives supply the inputs:

- `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip`: all seven merged spectra; [restoration instructions](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md) and [source registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json).
- `SETI_HARPS_RAW_BATCH03_INPUTS_PART1_2026-11-01.zip`: the May discovery ancillary product; [saved-input instructions](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/SAVED_INPUTS.md) and [source registry](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json).

The inventory records complete archive sizes/hashes and exact selected members. Both complete archives were reused from an existing local cache only after exact whole-file verification. The two event NPZs are reconstructed from unchanged committed batch03 evidence parts. Full raw detector products remain in the existing archive and are not restored for this profile context.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c011_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

One cache may hold both archives. The helper verifies complete archive and member hashes, reuses identical destinations, rejects differing bytes and writes deterministic metadata without local cache paths. Its FITS/NPY inspection is header-only and it executes no comparison or network request. Preserve published methods and completed outputs; reproduce separately. Full restored products and temporary raw-panel copies are excluded from Git.
