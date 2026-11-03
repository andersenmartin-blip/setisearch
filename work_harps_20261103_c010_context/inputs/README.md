# Exact archived inputs for C010 / HD112410

Header-only restoration verifies **10 exact files**: the seven existing HD112410 merged cohort spectra, one discovery ancillary TAR, one complete native-A FITS product and the original event-specific native/raw NPZ panel. The two complete source archives and every selected member were hash-checked. Existing archive bytes were recovered after workspace maintenance; no live telescope/archive acquisition, new flux or detector-pixel interpretation, historical edit or new registration was performed.

| Record | Discovery product | Observation date | Covering native order |
|---|---|---|---:|
| V2E2-0086 | ADP.2025-04-30T01:01:50.866 | 2025-04-29T03:06:38.398 | 1 |

The single reference is fixed by original queue row 23, group C010 / R011. The catalog input remains exactly **3823.0649999999996 Å** in barycentric air wavelengths (human-readable 3823.065 Å). The April 2025 discovery BERV is **3.40485846065643 km/s**, giving the independently calculated fixed topocentric-air anchor **3823.0215804708346 Å** via `3823.0649999999996 / (1 + 3.40485846065643 / 299792.458)`. No numeric anchor or exposure from the previous HD106515A contexts is transferred.

**The target and cohort change to HD112410.** Its seven existing observations run from 2025-04-29 through 2025-08-07, with BERV spanning −17.8979901476463 to +3.40485846065643 km/s, a range of 21.30284860830273 km/s. Original epoch/profile and raw evidence for 0086 already existed. A distinct target and wavelength window do not make these blind or untouched data, add observing time or establish independent observing evidence. The proposed barycentric ±3 Å window is [3820.0649999999996, 3826.0649999999996] Å; the original ±0.25 Å core is [3822.8149999999996, 3823.3149999999996] Å. These ranges are disjoint from completed C001–C009 bounded contexts.

[INPUT_INVENTORY.json](INPUT_INVENTORY.json) binds all product identities, dates, BERV values, raw progenitors, archive members and exact restored-file hashes. A fresh scan of **all 72 native order headers** records wavelength endpoints and positive derivatives across every order. Only order 1 covers the original center, and it covers the whole original core. It and its original raw panel are retained; no covering order is excluded.

| Frame | Lower order-1 endpoint (Å) | Upper endpoint (Å) | Endpoint offsets from fixed center (Å) |
|---|---:|---:|---|
| Topocentric air | 3803.1337172151 | 3845.8145628369703 | [−19.887863255734374, +22.792982366135675] |
| Barycentric air | 3803.176910870139 | 3845.8582412348187 | [−19.88808912986042, +22.793241234819106] |

The full ±3 Å context, ±0.25 Å core and both fixed [−3, −1.5] / [+1.5, +3] Å reference intervals are geometrically covered in both frames. The inventory retains those checks under `native_products[].orders[].fixed_frame_header_geometry`. Coordinate coverage does not establish finite flux, positive references, valid normalization, calibrated uncertainties or physical origin. Those outcomes remain for the separately frozen diagnostic.

Native header shape is 72×4096. Degree 3 wavelength and degree 4 trace coefficients for order 1 are copied from the header, with ascending coefficients evaluated at zero-based native pixels 0–4095. Merged wavelengths are barycentric air angstrom and merged flux is uncalibrated ADU; ERR is declared unavailable. The historical native convention remains topocentric air angstrom. Native BUNIT is absent, so its extracted units remain unspecified. NPY headers retain panel shapes and native-snippet identities without reading their array values. Publication identifiers remain distinct from observation timestamps.

## Historical mapping and review limits

| Historical order | Global grid usable | Original local usable | Original baseline verified | Later five-window support |
|---:|---|---|---|---|
| 1 | true | false | false | true |

The exact stages, native pixel and raw coordinates are retained in `mapping_records`. Later reference-window support does not repair the earlier local/baseline limitations. Header geometry is a separate check and no new mapping test is performed here.

`historical_raw_review_records` preserves the exact primary, secondary, root-adopted and comparison records. All three review stages retain **U**. The original evidence describes a broad native bump and diffuse trace-confined raw enhancement over several dispersion pixels, without an unambiguous compact charge deposit. The broad spectral structure remains unresolved. Restoration does not replace these records, assign physical origin or qualify a laser candidate.

## Restore exact bytes

Two existing archives provide the inputs:

- `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` supplies all seven merged spectra; [restoration instructions](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md) and [source registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json).
- `SETI_HARPS_RAW_BATCH03_INPUTS_PART1_2026-11-01.zip` supplies the April 2025 ancillary product; [saved-input instructions](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/SAVED_INPUTS.md) and [source registry](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json).

The inventory retains the complete archive sizes and hashes and exact selected members. The original 0086 NPZ is reconstructed from unchanged committed batch03 evidence parts. Full raw detector products remain archived and are not extracted for this profile context.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c010_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

One cache may contain both named archives. The helper verifies complete archives and members, reuses identical files, refuses differing destinations and writes deterministic inventory/receipt metadata without local cache paths. Its FITS/NPY inspection is header-only and it performs no comparison or network request. Preserve published methods and completed outputs; reproduce in a separate checkout. Restored full products and temporary input-panel copies are excluded from Git.
