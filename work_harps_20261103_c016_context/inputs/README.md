# Exact archived inputs for C016 / HD114386

Header-only restoration verifies **19 exact files**: all seven existing HD114386 merged cohort spectra, four discovery ancillary TARs, four complete native-A FITS products and four original event-specific native/raw NPZ panels. Complete source-archive and selected-member hashes were checked. No live telescope/archive acquisition, new flux or detector-pixel interpretation, historical edit or new registration was performed.

| Record | Queue row | Discovery product | Observation timestamp | Exact catalog center (Å) |
|---|---:|---|---|---:|
| V2E2-0094 | 27 | ADP.2022-03-08T01:01:37.348 | 2022-03-07T06:25:44.466 | 4303.785 |
| V2E2-0096 | 29 | ADP.2022-05-17T01:02:16.724 | 2022-05-16T02:17:40.312 | 4303.785 |
| V2E2-0098 | 30 | ADP.2023-01-03T01:08:17.803 | 2023-01-02T07:03:31.892 | 4303.785 |
| V2E2-0110 | 32 | ADP.2023-08-29T01:02:07.487 | 2023-08-27T23:33:30.418 | 4303.79 |

Original queue row 27 fixes the complete four-member C016 / R017 joint group; all four distinct discovery products remain fixed comparison references. The group center **4303.7875 Å** is the midpoint of minimum and maximum original catalog centers, not a fitted peak. The first queue member, 0094, fixes the sole common topocentric group anchor: **4303.512448784194 Å**, independently calculated as `4303.7875 / (1 + 19.1606928163471 / 299792.458)` using its March discovery BERV. Other references do not redefine that anchor, and individual catalog centers remain explicit.

The target changes to **HD114386**, with its own seven existing observations from 2022-01-06 to 2023-08-27. BERV ranges from −24.8175760325439 to +26.7544256646121 km/s, a span of **51.572001697156 km/s**. No HD112410 product, May 2025 reference, numeric anchor, BERV span, coverage limit or quality outcome is transferred.

The common barycentric context is [4300.7875, 4306.7875] Å and core [4303.5375, 4304.0375] Å. The original member centers and ±0.25 Å cores remain distinct catalog information. The context is disjoint from completed C001–C012 bounded group windows, but original C016 epoch/profile and raw evidence already existed. A completed [blue normalization context](../../work_harps_20261101/v2/extension02/normalization_context_20261102/README.md) also used these same HD114386 observations at different blue wavelengths. It completed the 0092/C013 and 0104/C014 normalization routes, which are skipped rather than replayed. That earlier work does not complete C016's distinct joint-profile route or provide independent data. This new bounded context adds no observing time, blind validation or archive-wide completeness.

## Fresh native scope in every discovery product

[INPUT_INVENTORY.json](INPUT_INVENTORY.json) binds exact product identities, dates, BERV, raw progenitors, archive members and hashes. Each of the four restored native products has its own fresh scan of **all 72 order headers**, totaling **288 flat `all_order_header_scan` records**, keyed by product and order. Every wavelength polynomial has a positive derivative over pixels 0–4095. Each product independently selects **order 19 only**, matching its own historical covering-order record. All four native contexts and raw panels remain; no covering order is excluded.

| Record | Order | Lower / upper topocentric-air endpoint (Å) | Lower / upper barycentric-air endpoint (Å) |
|---|---:|---|---|
| 0094 | 19 | 4285.09779604887 / 4333.250171281799 | 4285.371670325447 / 4333.527123130362 |
| 0096 | 19 | 4285.09770339571 / 4333.2503414105095 | 4284.943799947959 / 4333.094708513976 |
| 0098 | 19 | 4285.09523100635 / 4333.24856587709 | 4285.469210202527 / 4333.626747627586 |
| 0110 | 19 | 4285.09569701922 / 4333.248198278159 | 4284.778043466938 / 4332.926975187608 |

Every product covers the full common ±3 Å context, common core and both [−3, −1.5] / [+1.5, +3] Å reference flanks in both fixed frames. All **601** grid centers, **51** core centers and **550** surrounding centers have coordinate support in each of the eight native frame rows. The complete per-product coefficients, endpoints, flags and fixed-frame geometry remain in the inventory. Coordinate support is distinct from finite flux, a positive reference, normalization quality, calibrated uncertainties or physical origin; each runtime missing, nonpositive, low-reference or blocked outcome must remain explicit under the separately frozen analysis.

The original event-specific topocentric catalog centers are not the common fixed group anchor:

| Record | Original event topocentric-air center (Å) | Its discovery BERV (km/s) |
|---|---:|---:|
| 0094 | 4303.509948943966 | +19.1606928163471 |
| 0096 | 4303.939580172063 | −10.767337430651 |
| 0098 | 4303.4094224434075 | +26.1642125597642 |
| 0110 | 4304.109063010477 | −22.2235735125819 |

Each original center is checked against that member's own exact catalog center and own discovery BERV. The common group anchor remains fixed by the first queue member; no per-reference recentering occurs. Product-specific historical centers, native pixels and raw coordinates remain attached to their own events.

Each native header shape is 72×4096. Degree 3 wavelength and degree 4 trace coefficients are retained for order 19 in every product, with ascending coefficients evaluated at zero-based pixels 0–4095. Merged wavelengths are barycentric air angstrom and uncalibrated ADU; ERR is declared unavailable. The historical native convention remains topocentric air angstrom. Native BUNIT is absent, so extracted units remain unspecified. NPY headers preserve saved panel and native-snippet shapes without reading array values. Publication identifiers and observation timestamps remain distinct.

## Historical mapping and review limits

| Original event / order | Global grid usable | Original local usable | Original baseline verified | Later five-window support |
|---|---|---|---|---|
| 0094 / 19 | true | true | true | true |
| 0096 / 19 | true | true | true | true |
| 0098 / 19 | true | true | true | true |
| 0110 / 19 | true | true | true | true |

`mapping_records` preserves all four events' distinct native-pixel/raw-row/raw-column coordinates and each mapping stage. These flags come from the four own original order-19 contexts. The later 0092 raw-window registration discrepancy in another blue normalization context is local to that evidence and is not transferred here. Supported historical mapping and fresh coordinate geometry do not establish physical origin. No new mapping test is performed.

`historical_raw_review_records` retains the exact primary, secondary, root-adopted and comparison records for all four members. Every review stage remains **U**. Historical evidence describes broad rounded native features, nearby shoulders or secondary structure and weak diffuse trace-associated raw enhancement, without an established compact charge morphology or spectral origin. Restoration does not replace these votes or qualify a laser candidate. All four complete raw panels, background/excess arrays, baseline arrays and native snippets remain intact. Panel hashes are verified directly against the original mapping table and the evidence manifest.

## Restore exact bytes

Three existing archives supply the inputs:

| Archive | Selected contents | Original instructions and receipts |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | All seven HD114386 merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART2_2026-11-01.zip` | March and May 2022 discovery ancillary products | [Saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART3_2026-11-01.zip` | January and August 2023 discovery ancillary products | Same saved-input instructions and registry |

The inventory records complete archive sizes/hashes and exact selected members. The merged archive was reused from an existing cache; both required raw-input archives were recovered from the previously saved source files and verified exactly. No duplicate archive package or live telescope query was needed. The four event NPZs are reconstructed from unchanged committed batch03 evidence parts. Full raw detector products remain in the existing archives and are not restored for this profile context.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c016_context/inputs/restore_inputs.py \
  --archive-dir /path/to/merged/archive/cache \
  --archive-dir /path/to/native/archive/cache
```

One cache may hold all three archives. The helper verifies complete archive and member hashes, reuses identical destinations, rejects differing bytes and writes deterministic metadata without local cache paths. Its FITS/NPY inspection is header-only and it executes no comparison or network request. Preserve published methods and completed outputs; reproduce separately. Full restored products and temporary raw-panel copies are excluded from Git.
