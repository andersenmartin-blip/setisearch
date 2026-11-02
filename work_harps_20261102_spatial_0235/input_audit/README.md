# Spatial0235 input audit

The exact restored inputs pass independent identity and provenance checks. The 26-check historical metadata audit and 44-check restored-byte/header audit cover science DP `ADP.2023-02-23T01:01:36.791`, raw `HARPS.2023-02-22T07:40:53.531`, and ancillary `ADP.2023-02-23T01:01:36.792`. The cached PART8 archive, both original products, the original native cutout/reference grid, decompressed raw bytes and extracted native A/B bytes match their provenance. Historical batch03 source hashes remain unchanged.

All indices below are zero-based, and intervals are half-open. Native order50/pixel956 maps to raw row3139 and stitched column2323.7701943175816. The raw mosaic concatenates `HDU1[:,50:2098]` and `HDU2[:,50:2098]` without transpose or rotation. The center is on chip2 at physical column325.7701943175816. The fixed row and trace-argument reversals use `4095-native_pixel`; the column is not reversed.

| Region | Native dispersion pixels | Raw detector rows |
|---|---|---|
| Native saved snippet | [936,977) | [3119,3160) if mapped |
| First old local control | [676,876) | [3220,3420) |
| Second old local control | [1037,1237) | [2859,3059) |
| Existing raw cutout | [941,972) if mapped | [3124,3155) |

The original 31×33 raw cutout spans stitched columns[2308,2341), corresponding to chip2 columns[310,343). It cannot provide the flanking controls; the exact restored full raw image supplies their geometric coverage. The saved two controls each contain200 samples. Global and all five order50 mapping windows were supported in the historical metadata. No mapping orientation or trace is refitted here.

Header-only neighbor geometry checks all142 other A/B traces over561 raw rows[2859,3420). No predicted neighbor center enters ±12 pixels of A50. The nearest is B49 at +16.34097…+16.36971 pixels; A has72 orders and B71, so order numbers must not be equated between fibers. Fiber B is simultaneous FP calibration, not independent sky. Its unmeasured wings could affect the positive9–12 pixel background zone even without center overlap. This is a geometric prediction from saved calibration headers, not empirical validation of B registration or contaminating flux.

Only opaque bytes, FITS headers and NPY headers were examined; no raw/native pixel values were decoded and no network requests were made. `INPUT_METADATA_AUDIT.json` records the earlier metadata-only checkpoint; `RESTORED_INPUT_AUDIT.json` resolves its pending restored-byte verification. The initial inventory draft expected six files while the separately requested B-header restoration added a seventh; that scope-accounting draft is preserved as `DRAFT_BEFORE_SEVENTH_B_HEADER_INPUT.json`. The final audit verifies all seven, including B’s exact TAR-member hash.

The later extraction plan must bind these exact inputs and preserve the native-to-raw interval reversal. This audit does not assess candidate morphology, local flux, origin or statistical significance.
