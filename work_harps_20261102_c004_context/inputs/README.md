# Exact archived inputs for C004 / HD106515A

Header-only restoration verifies **16 exact files**: all seven existing merged cohort spectra, three discovery ancillary TARs, three complete native-A FITS products and three event-specific native/raw NPZ panels. Complete source-archive and selected-member hashes were checked. No acquisition, new flux or detector-pixel interpretation, historical edit or new registration was performed.

| Record | Discovery product | Observation date | Native order |
|---|---|---|---:|
| V2E2-0028 | ADP.2022-03-08T01:01:37.342 | 2022-03-07 | 3 |
| V2E2-0045 | ADP.2023-03-23T01:02:04.831 | 2023-03-22 | 3 |
| V2E2-0052 | ADP.2023-05-25T01:01:39.293 | 2023-05-24 | 3 |

All three discovery products are distinct. Their references remain separate within the same seven original target epochs; no favorable date or duplicate product is selected. `native_products`, `native_order_coverage`, `unique_native_order_pairs` and `saved_native_raw_cutouts` each retain three contexts. All three original barycentric-air catalog centers are **3872.245 Å**. The first discovery is March 2022, with BERV **10.77158288517 km/s**, giving first-discovery topocentric-air center **3872.1058747209718 Å**. This is a different anchor from the January discovery used in earlier groups. The proposed ±3 Å context and ±0.25 Å original core use the existing saved source products.

**The complete C004 original core was already visible inside C003's positive normalization flank.** All seven observations are reused; the overlapping wavelength values are not blind or independent validation and add no observing time. Selection by original queue row 8 before C007 results does not erase the earlier C003 exposure to those flux values. C004 is separate from the C007 wavelength window, but shares its observing cohort.

`INPUT_INVENTORY.json` binds all products, observation dates, BERV, exact raw progenitors and restored-file hashes. Fresh `all_order_header_scan` records endpoints and positive wavelength derivatives for all **216 native orders**, 72 per unique product. Only order 3 covers each original event center. All planned ±3 Å frame windows lie geometrically inside that order's endpoints; header bounds do not establish finite flux, usable normalization or available error values. No covering order is omitted, and no C003 order-2 result is transferred to this wavelength.

| Discovery record | Order 3 lower topocentric-air endpoint (Å) | Upper endpoint (Å) |
|---|---:|---:|
| V2E2-0028 | 3851.27147613778 | 3894.49761983731 |
| V2E2-0045 | 3851.27028788661 | 3894.49636669776 |
| V2E2-0052 | 3851.27020323082 | 3894.49611578159 |

Native header shape is 72×4096. Degree 3 wavelength and degree 4 trace coefficients for order 3 are retained directly from each header. Merged wavelengths are explicitly barycentric air angstrom with uncalibrated ADU flux; ERR is declared unavailable. Native polynomials retain the historical topocentric-air-angstrom convention. Native `BUNIT` is absent, so native extracted units remain unspecified. NPY headers preserve the raw and baseline cutout shapes and native-snippet identities without reading array values.

All three historical **global, local, baseline and later five-window mapping gates are true**. The separate stages and exact native-pixel/raw-row/raw-column positions are preserved in `mapping_records`; no new mapping test or physical-origin inference is performed. These historical gates should not be replaced by C007's different local/baseline failures. `historical_raw_review_records` retains the exact selected primary, secondary, adopted and comparison records. All three adopted labels remain U.

The seven existing epochs span BERV −29.2347518620376 to +30.3750612537025 km/s, a range of 59.6098131157401 km/s. Publication identifiers and observation dates remain distinct; exact raw identifiers retain inherited millisecond differences from FITS observation times.

## Reproduce exact bytes

Exactly three existing archives are used:

- `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip`: all seven merged spectra; [restoration instructions](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md) and [original registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json).
- `SETI_HARPS_RAW_BATCH02_INPUTS_PART2_2026-11-01.zip` and `SETI_HARPS_RAW_BATCH02_INPUTS_PART3_2026-11-01.zip`: discovery ancillary products; [saved-input instructions](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/SAVED_INPUTS.md) and [original registry](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/LIBRARY_INPUTS.json).

The inventory records complete archive sizes, hashes and member identities. Event NPZs are reconstructed from unchanged committed batch02 evidence parts. Full raw detector products remain in the existing archives and are not restored for this broader-profile comparison.

In a separate reproduction checkout:

```sh
python3 work_harps_20261102_c004_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

Each cache directory can contain more than one of the three named archives. The helper verifies whole archives and exact members, preserves identical destinations, rejects differing files and writes deterministic inventory/receipt metadata without local cache paths. Its FITS/NPY inspection is header-only and does not execute the comparison. Preserve the published method and completed outputs. Full restored inputs and temporary input-panel copies are excluded from Git; their exact source archives already exist.
