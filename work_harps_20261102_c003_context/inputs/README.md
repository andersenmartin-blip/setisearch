# Exact archived inputs for C003 / HD106515A

The header-only inventory restores 25 exact files: seven merged spectra, five discovery ancillary TARs, five full native-A FITS products, and **eight** existing native/raw NPZ panels. All complete source archives and selected members were hash-verified. No new network request, observational array interpretation, historical edit, or detector mapping was performed.

| Discovery record | Merged product | Historical covering orders |
|---|---|---|
| V2E2-0022 | ADP.2022-01-06T01:08:04.689 | 2, 3 |
| V2E2-0027 | ADP.2022-03-08T01:01:37.342 | 2, 3 |
| V2E2-0044 | ADP.2023-03-23T01:02:04.831 | 2, 3 |
| V2E2-0051 | ADP.2023-05-25T01:01:39.293 | 3 |
| V2E2-0053 | ADP.2023-07-05T01:02:00.053 | 3 |

`INPUT_INVENTORY.json` retains the exact seven epoch identities, actual observation dates, BERV, raw provenance, table representations, archive/member hashes, and all restored-file hashes. Its native products contain degree 3 wavelength and degree 4 trace polynomials for orders 2/3 from all five FITS headers, each with image shape 72×4096. `native_order_coverage` is the complete five-by-two metadata inventory; `covering_orders` defines the eight existing combinations. `excluded_native_orders` explicitly preserves the two `NOT_COVERING_LINE` cases. No order 2 panel exists for either excluded case.

Coverage uses each event's original topocentric feature center from the historical mapping, not the common plotting anchor. For V2E2-0051, order 2 ends at 3870.006051618989 angstrom while the feature center is 3870.0700818006676. For V2E2-0053, the endpoint is 3870.0057691951843 and the feature center is 3870.132402290935. Those order 2 combinations remain excluded from new profiles. In the first three discoveries, order 2 covers the line but ends less than 0.7 angstrom to its right; the separately frozen analysis must retain its incomplete broader-window coverage without extrapolation or window shrinkage.

All eight combinations retain the original global, local, baseline and later five-window mapping gates. The first three order 2 local/baseline gates were false and their later reference gates were true; all five order 3 combinations had local and later reference support. Geometric support does not certify useful flux, and no gate or coordinate is recomputed here.

The merged products explicitly use barycentric air wavelengths in angstrom and uncalibrated ADU flux. Their headers describe unavailable ERR spectra filled with NaN; those arrays are not inspected during restoration. Native wavelengths retain the unchanged historical topocentric-air-angstrom polynomial convention. Native `BUNIT` is absent in all five products, so no independent native flux-unit certification is asserted. Saved NPZ headers show 31×33 raw cutouts, 21×25 baseline cutouts, and 41-sample native snippets. Full native FITS permit the broader fixed windows after release.

The seven original cohort epochs span recorded BERV −29.2347518620376 to +30.3750612537025 km/s (59.6098131157401 km/s total). The earliest discovery has BERV +30.1380355615464 km/s. These are stored header metadata, not a measurement of frame-discrimination power.

## Reproduce the byte restoration

The three existing archives are:

- `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip`: all seven merged FITS; [checkpoint instructions](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md) and [receipt registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json).
- `SETI_HARPS_RAW_BATCH02_INPUTS_PART2_2026-11-01.zip`: the first two discovery ancillary TARs.
- `SETI_HARPS_RAW_BATCH02_INPUTS_PART3_2026-11-01.zip`: the last three discovery ancillary TARs. Both raw archives have [saved-input instructions](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/SAVED_INPUTS.md) and an [exact receipt registry](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/LIBRARY_INPUTS.json).

The inventory gives their exact bytes and SHA256 values. The eight NPZs are recovered from the committed batch02 evidence parts. Original full raw images remain preserved in the existing archives and are not restored for this profile-context phase.

From a separate copy of the repository, run:

```sh
python3 work_harps_20261102_c003_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

The helper requires all three exact archives, keeps identical destinations, refuses differing existing files, and regenerates deterministic inventory/receipt metadata without embedding local cache paths. It reads only FITS/NPY headers after byte restoration. The larger restored products are ignored by Git because their exact source archives are already preserved. Keep published plans, releases, and completed outputs intact when reproducing; this helper does not run the scientific analysis.
