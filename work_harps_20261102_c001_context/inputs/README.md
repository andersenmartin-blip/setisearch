# Exact existing inputs for C001 / HD103991

`INPUT_INVENTORY.json` binds fourteen restored files to existing archived bytes: all six merged spectra from the original epoch cohort, two discovery ancillary TARs, their two full native-A FITS products, and four preserved native/raw cutout NPZ files. `restore_inputs.py` validates full archive and selected-member hashes, then inspects FITS and NPY headers only. No observational array values were interpreted, no network request was made, and no historical file was changed.

| Discovery record | Merged product | Original raw progenitor |
|---|---|---|
| V2E2-0001 | ADP.2023-02-23T01:01:36.783 | HARPS.2023-02-22T06:23:48.539 |
| V2E2-0016 | ADP.2023-03-01T01:01:30.551 | HARPS.2023-02-28T06:06:39.357 |

The corresponding ancillary products are `ADP.2023-02-23T01:01:36.784` and `ADP.2023-03-01T01:01:30.552`. Archive-product dates must not be mistaken for observation dates.

| Same-target merged product | Actual UTC observation | Recorded BERV (km/s) |
|---|---|---:|
| ADP.2023-02-23T01:01:36.783 | 2023-02-22T06:23:48.539 | 16.9196571680147 |
| ADP.2023-02-24T01:01:17.499 | 2023-02-23T07:09:34.479 | 16.4295552925342 |
| ADP.2023-02-27T01:01:03.513 | 2023-02-26T07:07:40.801 | 15.1973358631226 |
| ADP.2023-02-28T01:02:17.095 | 2023-02-27T08:32:54.036 | 14.6303297937470 |
| ADP.2023-03-01T01:01:30.551 | 2023-02-28T06:06:39.357 | 14.4701720470153 |
| ADP.2023-03-02T01:01:24.353 | 2023-03-01T09:10:00.121 | 13.7264285926878 |

All merged FITS tables explicitly retain barycentric air wavelengths in angstrom and uncalibrated ADU flux. Their original header says the ERR spectrum is unavailable and filled with NaN; this inventory does not inspect those values. Each native-A primary image is 72×4096. The order2/3 degree3 wavelength polynomials and degree4 trace polynomials are retained in the inventory. The historical extractor uses zero-based native pixel coordinates and interprets the native wavelength polynomials as topocentric air angstrom. Native-A `BUNIT` is absent, which remains explicit; it does not supply independent native flux-unit certification.

Both discoveries place order2 at native pixel2230 / raw row1865 and order3 at native pixel75 / raw row4020. Their unchanged raw columns are respectively 91.3190831436 / 106.8001652639 for V2E2-0001 and 91.3174045464 / 106.8198061818 for V2E2-0016. The original order3 local mapping gate failed for both discoveries; the later fixed five-window reference audit supported both covering orders. Both histories are retained separately, without refitting coordinates or equating geometric support with useful flux.

Each restored NPZ contains a 31×33 raw cutout and 41-sample native snippet. The raw cutouts occupy rows `[1850,1881)`, columns `[75,108)` for order2, and rows `[4005,4036)`, columns `[91,124)` for order3. The full native FITS is available for the separately frozen broader-profile method. Header-polynomial endpoints already show that order3 begins near3851.2702 angstrom: the proposed ±3-angstrom neighborhood near3852.19 cannot have complete left-side order3 coverage. Preserve missing coverage; do not extrapolate, shrink the window, or infer local flux from the header geometry. No new detector spatial fit is part of input restoration.

The three source archives are already preserved:

- `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip`: all six merged spectra; see [original checkpoint instructions](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md).
- `SETI_HARPS_EXTENSION02_RAW_INPUTS_PART2_2026-11-01.zip`: V2E2-0001 ancillary; see [original raw checkpoint instructions](../../work_harps_20261101/v2/extension02/raw_followup/checkpoints/RESTORE.md).
- `SETI_HARPS_RAW_BATCH02_INPUTS_PART1_2026-11-01.zip`: V2E2-0016 ancillary; see [saved batch02 inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/SAVED_INPUTS.md).

Their exact bytes and hashes are in the inventory. The four cutouts are restored from committed mapping-follow-up/batch02 evidence archives. Full original raw images remain in their existing source archives and were not restored for this broader-profile context.

From a separate repository copy, restore using one or more directories containing those exact archives:

```sh
python3 work_harps_20261102_c001_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

The tool refuses any differing existing destination. It writes deterministic inventory/receipt metadata and copies only the specified bytes; it does not execute the scientific analysis. Preserve published methods and completed outputs when reproducing. The large restored products are ignored by Git because their source archives are already preserved.
