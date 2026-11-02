# Exact archived inputs for C002 / HD106515A

Header-only restoration verifies **11 exact files**: all seven existing merged cohort spectra, one discovery ancillary TAR, one complete native-A FITS product and both event-specific native/raw NPZ panels. Complete source-archive and selected-member hashes were checked. No acquisition, new flux or detector-pixel interpretation, historical edit or new registration was performed.

| Record | Discovery product | Observation date | Covering native orders |
|---|---|---|---|
| V2E2-0033 | ADP.2022-05-08T01:01:37.876 | 2022-05-07T05:12:25.401 | 2, 3 |

The one discovery reference is fixed by original queue row 10, group C002 / R002. Its barycentric-air catalog center is **3868.6025 Å**, and its BERV is **−18.8907517532076 km/s**. The independently calculated fixed topocentric-air anchor is **3868.846286702511 Å**, using `3868.6025 / (1 − 18.8907517532076 / 299792.458)`. This uses the May discovery metadata; neither the January nor March reference is transferred. The proposed context is ±3 Å and the original core is ±0.25 Å in each fixed coordinate frame.

**The complete C002 original core was already visible inside C003's surrounding-spectrum window**, at C003 offsets [−1.39875, −0.89875] Å, between its negative reference flank and core and outside both masks. C002's original core lies outside C004's window, but its proposed ±3 Å context overlaps C004 on [3869.245, 3871.6025] Å, a width of 2.3575 Å. All seven observations are reused. The shared pixels and observations are neither blind nor independent validation and add no observing time.

[INPUT_INVENTORY.json](INPUT_INVENTORY.json) binds every product, observation date, BERV, exact raw progenitor and restored-file hash. The fresh `all_order_header_scan` records endpoints and positive wavelength derivatives for all **72 native orders** of the May discovery product. Only orders 2 and 3 cover the original center, and both cover the full original core. Both are retained, with their two existing raw panels; none is excluded. Header geometry does not establish finite flux, usable normalization, calibrated uncertainties or physical origin.

| Native order | Lower topocentric-air endpoint (Å) | Upper endpoint (Å) | Upper offset from May anchor (Å) | Full ±3 Å context |
|---:|---:|---:|---:|---|
| 2 | 3827.05570799571 | 3870.0073010586916 | 1.161014356180658 | No |
| 3 | 3851.27210134526 | 3894.4973141740415 | 25.651027471530597 | Yes |

These bounds are freshly derived from this product's wavelength-polynomial header. In the barycentric frame, order 2 ends at offset **+1.1609411974559407 Å**. In both frames its entire positive reference interval [+1.5, +3] Å lies outside the order, while its full core and negative [−3, −1.5] Å interval are covered. Order 3 covers the complete context and both reference intervals in both frames. `native_products[].orders[].fixed_frame_header_geometry` records these coordinate checks explicitly. This geometric limitation is not inherited from C003; finite-sample and signed-normalization outcomes remain for the separately frozen diagnostic.

Native header shape is 72×4096. Degree 3 wavelength and degree 4 trace coefficients for both covering orders are retained directly from the header. Merged wavelengths are barycentric air angstrom with uncalibrated ADU flux; ERR is declared unavailable. Native polynomials retain the historical topocentric-air-angstrom convention. Native `BUNIT` is absent, so native extracted units remain unspecified. NPY headers preserve raw/baseline panel shapes and native-snippet identities without reading array values.

| Order | Historical global grid | Original local | Original baseline | Later five-window reference |
|---:|---|---|---|---|
| 2 | true | false | false | true |
| 3 | true | true | true | true |

The distinct historical stages and exact native-pixel/raw-row/raw-column positions are preserved in `mapping_records`. The later reference support does not erase order 2's earlier local/baseline failures. No new mapping test is performed. `historical_raw_review_records` retains the exact selected primary, secondary, adopted and comparison records; the adopted U label is unchanged.

The seven existing epochs span BERV −29.2347518620376 to +30.3750612537025 km/s, a range of 59.6098131157401 km/s. Publication identifiers and observation dates remain distinct; exact raw identifiers retain inherited millisecond differences from FITS observation times.

## Reproduce exact bytes

Exactly two existing archives are used:

- `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip`: all seven merged spectra; [restoration instructions](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md) and [original registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json).
- `SETI_HARPS_RAW_BATCH02_INPUTS_PART2_2026-11-01.zip`: May discovery ancillary product; [saved-input instructions](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/SAVED_INPUTS.md) and [original registry](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/LIBRARY_INPUTS.json).

The inventory records complete archive sizes, hashes and member identities. Both event NPZs are reconstructed from unchanged committed batch02 evidence parts. Full raw detector products remain in the existing archive and are not restored for this broader-profile comparison.

In a separate reproduction checkout:

```sh
python3 work_harps_20261102_c002_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

One cache can hold both named archives. The helper verifies whole archives and exact members, preserves identical destinations, rejects differing files and writes deterministic inventory/receipt metadata without local cache paths. Its FITS/NPY inspection is header-only and does not execute the comparison. Preserve the published method and any completed outputs. Full restored inputs and temporary input-panel copies are excluded from Git; their exact source archives already exist.
