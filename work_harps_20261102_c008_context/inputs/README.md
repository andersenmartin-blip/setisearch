# Exact archived inputs for C008 / HD106515A

Header-only restoration verifies **10 exact files**: all seven existing merged cohort spectra, one discovery ancillary TAR, one complete native-A FITS product and the existing event-specific native/raw NPZ panel. Complete source-archive and selected-member hashes were checked. No acquisition, new flux or detector-pixel interpretation, historical edit or new registration was performed.

| Record | Discovery product | Observation date | Covering native order |
|---|---|---|---:|
| V2E2-0047 | ADP.2023-03-23T01:02:04.831 | 2023-03-22T04:52:14.904 | 43 |

The single discovery reference is fixed by original queue row 17, group C008 / R009. Its barycentric-air catalog center is **5182.005 Å**, and its BERV is **3.26509772194068 km/s**. The independently calculated fixed topocentric-air anchor is **5181.9485623946 Å**, using `5182.005 / (1 + 3.26509772194068 / 299792.458)`. This uses the March 2023 discovery metadata; none of the earlier January, March 2022 or May 2022 anchors is transferred. The proposed context is ±3 Å and the original core is ±0.25 Å in each fixed coordinate frame.

The proposed barycentric window [5179.005, 5185.005] Å is disjoint in wavelength from the completed C001–C007 bounded contexts. This does not make the evidence untouched, blind or independent: C008 already has original epoch/profile and raw evidence, and all seven observing products are reused. The broader context adds no observing time or archive-wide completeness. The discovery product is also among those previously restored for C004, but this phase establishes its order scope afresh.

[INPUT_INVENTORY.json](INPUT_INVENTORY.json) binds every product, observation date, BERV, exact raw progenitor and restored-file hash. The fresh `all_order_header_scan` records endpoints and positive wavelength derivatives for all **72 native orders** of the March 2023 discovery product. Only order 43 covers the original center, and it covers the full original core. That order and its existing raw panel are retained; no covering order is excluded. Header geometry does not establish finite flux, usable normalization, calibrated uncertainties or physical origin.

| Frame | Lower order-43 endpoint (Å) | Upper endpoint (Å) | Endpoint offsets from fixed center (Å) |
|---|---:|---:|---|
| Topocentric air | 5156.37162001017 | 5214.417647930924 | [−25.576942384430367, +32.4690855363242] |
| Barycentric air | 5156.427779052136 | 5214.474439163423 | [−25.57722094786368, +32.469439163422976] |

These bounds are freshly derived from this product's wavelength-polynomial header. The full ±3 Å context, ±0.25 Å core and both [−3, −1.5] / [+1.5, +3] Å reference intervals are geometrically covered in both frames. `native_products[].orders[].fixed_frame_header_geometry` records those checks explicitly. The geometry and normalization outcomes of earlier groups are not transferred; finite-sample and signed-reference checks remain for the separately frozen diagnostic.

Native header shape is 72×4096. Degree 3 wavelength and degree 4 trace coefficients for order 43 are retained directly from the header. Merged wavelengths are barycentric air angstrom with uncalibrated ADU flux; ERR is declared unavailable. Native polynomials retain the historical topocentric-air-angstrom convention. Native `BUNIT` is absent, so native extracted units remain unspecified. NPY headers preserve raw/baseline panel shapes and native-snippet identities without reading array values.

All four historical **global, original local, original baseline and later five-window mapping gates are true**. The distinct historical stages and exact native-pixel/raw-row/raw-column positions are preserved in `mapping_records`; no new mapping test is performed. `historical_raw_review_records` retains the exact selected primary, secondary, adopted and comparison records. The adopted U label is unchanged. Historical mapping support is not physical-origin validation.

The seven existing epochs span BERV −29.2347518620376 to +30.3750612537025 km/s, a range of 59.6098131157401 km/s. Publication identifiers and observation dates remain distinct; exact raw identifiers retain inherited millisecond differences from FITS observation times.

## Reproduce exact bytes

Exactly two existing archives are used:

- `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip`: all seven merged spectra; [restoration instructions](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md) and [original registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json).
- `SETI_HARPS_RAW_BATCH02_INPUTS_PART3_2026-11-01.zip`: March 2023 discovery ancillary product; [saved-input instructions](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/SAVED_INPUTS.md) and [original registry](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/LIBRARY_INPUTS.json).

The inventory records complete archive sizes, hashes and member identities. The event NPZ is reconstructed from unchanged committed batch02 evidence parts. Full raw detector products remain in the existing archive and are not restored for this broader-profile comparison.

In a separate reproduction checkout:

```sh
python3 work_harps_20261102_c008_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

One cache can hold both named archives. The helper verifies whole archives and exact members, preserves identical destinations, rejects differing files and writes deterministic inventory/receipt metadata without local cache paths. Its FITS/NPY inspection is header-only and does not execute the comparison. Preserve the published method and any completed outputs. Full restored inputs and temporary input-panel copies are excluded from Git; their exact source archives already exist.
