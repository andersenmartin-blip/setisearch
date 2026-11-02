# Exact archived inputs for C006 / HD106515A

The header-only restoration verifies 14 exact files: all seven existing merged cohort spectra, two unique discovery ancillary TARs, two complete native-A FITS products, and three event-specific native/raw NPZ panels. Entire source archives and selected member bytes were hash-verified. No new acquisition, flux/pixel interpretation, historical edit or detector registration was performed.

| Record | Discovery product | Observation date | Native order |
|---|---|---|---:|
| V2E2-0025 | ADP.2022-01-06T01:08:04.689 | 2022-01-05 | 19 |
| V2E2-0042 | ADP.2023-01-01T01:10:52.479 | 2022-12-31 | 19 |
| V2E2-0043 | ADP.2023-01-01T01:10:52.479 | 2022-12-31 | 19 |

The last two records share one exposure and native product. `native_products` therefore contains two unique products, each retaining a representative `event`, its full `discovery_for` list, and every event-specific original center. `native_order_coverage` and `saved_native_raw_cutouts` retain all three event contexts. `unique_native_order_pairs` has two entries. Product deduplication must not drop either event or its historical panel; overlapping panels do not supply independent observing time.

`INPUT_INVENTORY.json` binds all seven epoch products, observation dates, BERV, exact raw progenitors and restored-file hashes. Its fresh `all_order_header_scan` checks wavelength endpoints and positive wavelength derivatives for all 72 orders of both native products. Only order 19 covers the original event centers. There are two selected native product/order pairs and no omitted historical covering orders. Order 19 endpoints are 4285.09765984656–4333.250317231099 Å for the first discovery and 4285.09520889465–4333.248689049508 Å for the second. Those geometric bounds do not establish finite flux, valid normalization or error support.

The native images have header shape 72×4096. Degree 3 wavelength and degree 4 trace coefficients for order 19 are retained directly from their headers. Merged wavelengths are explicitly barycentric air angstrom, with uncalibrated ADU flux; ERR is declared unavailable and filled with NaN. Native polynomials inherit the unchanged topocentric-air-angstrom convention. Native `BUNIT` is absent in both products, so their extracted flux units remain unspecified. NPY headers confirm 31×33 raw cutouts, 21×25 baseline cutouts and 41-sample native snippets. Those array values were not inspected during restoration.

All global and later five-window mapping gates are true. **V2E2-0025's original local and baseline mapping gates are false**; this history remains explicit and is not overwritten by the later gate. V2E2-0042 and V2E2-0043 have true original local and baseline gates. No new registration is attempted. `historical_raw_review_records` preserves the selected primary, secondary, adopted and comparison records exactly, including the separate off-trace feature for 0042. These are preserved historical descriptions, not new raw-panel interpretation or origin assignments. All three labels remain U.

The same seven existing cohort epochs span BERV −29.2347518620376 to +30.3750612537025 km/s, or 59.6098131157401 km/s. The two discovery BERVs, +30.1380355615464 and +30.3750612537025 km/s, are nearly matched. Archive publication identifiers and observation dates remain distinct; exact raw identifiers retain inherited millisecond differences from FITS observation times.

## Reproduce exact bytes

Exactly two existing archives are used:

- `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip`: seven merged spectra; [checkpoint instructions](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md) and [receipt registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json).
- `SETI_HARPS_RAW_BATCH02_INPUTS_PART2_2026-11-01.zip`: both discovery ancillary products; [saved-input instructions](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/SAVED_INPUTS.md) and [receipt registry](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/LIBRARY_INPUTS.json).

The inventory records complete archive sizes, hashes and member identities. All three NPZs come from committed batch02 evidence parts. Full original raw images stay in the existing archives; broader-profile input restoration does not need to restore or interpret them.

In a separate reproduction copy of the repository, run:

```sh
python3 work_harps_20261102_c006_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

The helper checks whole archives and exact members, preserves identical destinations, rejects differing files, and writes deterministic inventory and receipt metadata without local cache paths. It reads FITS/NPY headers only and does not execute science analysis. Preserve published plans, release records and completed outputs. Large restored products are ignored by Git because their exact archives are already preserved.
