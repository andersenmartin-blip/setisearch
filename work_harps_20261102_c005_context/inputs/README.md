# Exact archived inputs for C005 / HD106515A

The header-only inventory restores 27 exact files: all seven existing merged cohort spectra, five discovery ancillary TARs, five complete native-A FITS products, and ten preserved native/raw NPZ panels. Entire source archives and selected-member bytes were hash-verified. No new acquisition, observed flux/pixel interpretation, historical edit, or detector mapping was performed.

| Discovery record | Merged product | Historical covering orders |
|---|---|---|
| V2E2-0023 | ADP.2022-01-06T01:08:04.689 | 3, 4 |
| V2E2-0029 | ADP.2022-03-08T01:01:37.342 | 3, 4 |
| V2E2-0035 | ADP.2022-05-08T01:01:37.876 | 3, 4 |
| V2E2-0046 | ADP.2023-03-23T01:02:04.831 | 3, 4 |
| V2E2-0054 | ADP.2023-07-05T01:02:00.053 | 3, 4 |

`INPUT_INVENTORY.json` records all seven cohort products, actual observation dates, BERV, exact raw progenitors, source hashes, and restored-file hashes. The five-by-two `native_order_coverage` inventory confirms ten `COVERING_LINE` combinations and no exclusions. Coverage retains each event's original topocentric feature center, independent of any common plotting anchor. Full native images have shape 72×4096; degree 3 wavelength and degree 4 trace coefficients for orders 3/4 are retained directly from their headers. Their endpoints provide coordinate support for the intended broader context, but do not establish usable flux or valid normalization before the released analysis.

All ten original global, local, baseline and later five-window mapping gates are true and remain separately recorded. `historical_raw_review_records` preserves the selected original primary, secondary, adopted and comparison records. In particular, the V2E2-0023 order 4 off-trace pixel remains described as distinct from the candidate, and the V2E2-0054 order 4 panel remains described as noisier. These are preserved [batch02 review records](../../work_harps_20261101/v2/extension02/raw_followup_batch02/ADOPTED_DISPOSITIONS.csv), not a new panel inspection or origin assignment. All five dispositions remain U.

Merged FITS headers explicitly retain barycentric air wavelengths in angstrom and uncalibrated ADU flux; ERR is described as unavailable and filled with NaN. Native wavelength polynomials retain the unchanged topocentric-air-angstrom convention. Native `BUNIT` is absent in all five products, so their extracted flux units remain unspecified. NPY headers confirm 31×33 raw cutouts, 21×25 baseline cutouts, and 41-sample native snippets. Values in those arrays were not interpreted during restoration.

The same seven cohort headers span BERV −29.2347518620376 to +30.3750612537025 km/s, a 59.6098131157401 km/s range. The first discovery has BERV +30.1380355615464 km/s. Archive publication identifiers and actual observation dates are kept distinct, including the inherited millisecond differences between some raw filenames and header times.

## Reproduce exact bytes

The three existing archives are:

- `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip`: seven merged spectra; [checkpoint instructions](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md) and [receipt registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json).
- `SETI_HARPS_RAW_BATCH02_INPUTS_PART2_2026-11-01.zip`: ancillary products for the January, March and May 2022 discoveries.
- `SETI_HARPS_RAW_BATCH02_INPUTS_PART3_2026-11-01.zip`: ancillary products for the March and July 2023 discoveries. Both raw archives have [saved-input instructions](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/SAVED_INPUTS.md) and an [exact receipt registry](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/LIBRARY_INPUTS.json).

Their complete sizes, hashes and selected-member identities are in the inventory. The ten NPZs come from committed batch02 evidence parts. Original full raw images remain preserved in the existing archives and are not needed for this broader-profile input restoration.

From a separate reproduction copy of the repository:

```sh
python3 work_harps_20261102_c005_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

The helper validates archives and member hashes, preserves identical destinations, rejects differing files, and regenerates deterministic inventory/receipt metadata without local cache paths. It reads FITS/NPY headers only and does not execute the science analysis. Large restored products are ignored by Git because their exact source archives are already preserved. Retain the published plans, releases, source metadata and completed outputs when reproducing.
