# Exact archived inputs for C007 / HD106515A

The header-only restoration verifies **10 exact files**: all seven existing merged cohort spectra, one discovery ancillary TAR, one complete native-A FITS product and the event-specific native/raw NPZ panel for **V2E2-0026**. Complete archive and selected-member hashes were checked. No acquisition, new flux/pixel interpretation, historical edit or detector registration was performed.

| Record | Discovery product | Observation date | Native order |
|---|---|---|---:|
| V2E2-0026 | ADP.2022-01-06T01:08:04.689 | 2022-01-05 | 19 |

This singleton has one discovery reference. The other six target epochs are retained without selecting favorable dates. `native_products`, `native_order_coverage`, `unique_native_order_pairs` and `saved_native_raw_cutouts` each contain one discovery context. Its original barycentric-air center is 4312.700 Å; dividing by the discovery BERV factor gives the fixed topocentric-air center 4312.266489291718 Å. The planned ±3 Å context and original ±0.25 Å core use the same saved source products as earlier work.

**The original C007 core was already visible in C006's positive normalization flank.** C007 reuses the same seven exposures and some of the same spectral values. A separate C007 context is therefore neither untouched data nor independent validation, and adds no observing time. The next-item choice was fixed from original queue row 6 before the C006 result; this does not remove the shared-data dependence.

`INPUT_INVENTORY.json` binds all seven products, observation dates, BERV, exact raw progenitors and restored-file hashes. A fresh `all_order_header_scan` checks endpoints and positive wavelength derivatives for all **72 native orders**. Only order 19 covers the original C007 center. Its topocentric-air endpoints are 4285.09765984656–4333.250317231099 Å, enclosing both planned frame windows geometrically. No historical covering order is omitted. Coordinate bounds do not establish finite flux, usable normalization or error support.

The native header shape is 72×4096. Degree 3 wavelength and degree 4 trace coefficients for order 19 are retained directly from the header. Merged wavelengths are explicitly barycentric air angstrom with uncalibrated ADU flux; ERR is declared unavailable. Native polynomials retain the historical topocentric-air-angstrom convention. Native `BUNIT` is absent, so native extracted units remain unspecified. NPY headers show 31×33 raw cutouts, 21×25 baseline cutouts and 41-sample native snippets. No array values were inspected during restoration.

**V2E2-0026's original local and baseline mapping gates are false**, while global and later five-window diagnostics are true. These separate historical stages remain explicit; no later gate overwrites the original failures. Native/merged agreement or header coverage cannot retroactively validate the local raw mapping. The saved detector location is native pixel 2143, raw row 1952 and raw column 736.7246044105867. `historical_raw_review_records` preserves the exact selected primary, secondary, adopted and comparison records. The adopted label remains U.

The seven existing cohort epochs span BERV −29.2347518620376 to +30.3750612537025 km/s, or 59.6098131157401 km/s. Discovery BERV is +30.1380355615464 km/s. Archive publication identifiers and observation dates remain distinct; exact raw identifiers retain inherited millisecond differences from FITS observation times.

## Reproduce exact bytes

Exactly two existing archives are used:

- `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip`: all seven merged spectra; [restoration instructions](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md) and [original registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json).
- `SETI_HARPS_RAW_BATCH02_INPUTS_PART2_2026-11-01.zip`: the discovery ancillary product; [saved-input instructions](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/SAVED_INPUTS.md) and [original registry](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/LIBRARY_INPUTS.json).

The inventory records complete archive sizes, hashes and member identities. The event NPZ comes from unchanged committed batch02 evidence parts. Full raw detector products stay in the existing archives and are not restored for this broader-profile comparison.

In a separate reproduction copy:

```sh
python3 work_harps_20261102_c007_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

The helper verifies whole archives and exact members, preserves identical destinations, rejects differing files and writes deterministic inventory/receipt metadata without local cache paths. It inspects FITS/NPY headers only and does not execute the comparison. Preserve published method, release and completed outputs. Restored full products and temporary input-panel copies are excluded from Git; their exact source archives already exist.
