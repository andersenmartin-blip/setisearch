# C018 independent input audit

`INPUT_AUDIT.json` records **PASS: 2,095 checks, zero failures**, against GREEN baseline `70fcd37632223f4b761fb4d9555a044d792a8d15` and prior state `7aff6a985c1aa7d4212d591a68e268eac6cb70008ce83e14cfc37bb41f2b8652`. Five complete archives, all 35 restored files and 34 historical source bindings are independently hashed. Original archive members, all fourteen original raw panels and the separate 0128 original/later evidence archives retain exact custody. No network requests, observed-array decoding, raw-image decoding, new registration or classification occur.

## Seven exact members and references

C018 is the full original joint queue group on **HD114783**, R019, with its own seven January 2022–July 2023 observations and BERV span 59.073251754930496 km/s. All seven observations are distinct discovery references; exact IDs and timestamps are retained without normalizing away millisecond differences from other targets.

| Event | Queue row | Exact catalog barycentric air center (Å) |
|---|---:|---:|
| V2E2-0114 | 33 | 3869.3349999999996 |
| V2E2-0119 | 38 | 3869.3325 |
| V2E2-0124 | 42 | 3869.3325 |
| V2E2-0128 | 46 | 3869.335 |
| V2E2-0133 | 50 | 3869.3349999999996 |
| V2E2-0134 | 51 | 3869.3325 |
| V2E2-0138 | 54 | 3869.335 |

The catalog-extrema midpoint is exactly 3869.33375 Å. The first original-queue discovery, `ADP.2022-01-22T01:09:14.958`, was observed January 21, 2022, with BERV 29.658729150824 km/s and fixes the common topocentric anchor 3868.9509913064876 Å under center/(1+BERV/c). This common coordinate anchor does not select a preferred reference. The common metric core and seven original member cores/markers remain separate; their edges differ by up to 0.00125 Å without post-value expansion or a fitted linewidth.

Seven references have six other epochs each: 42 directed nonself pairs per frame/region correspond to 21 unordered observation pairs plus 21 reciprocal duplicates. These are metadata counts from seven reused observations, not independent samples or new correlations.

## Fresh headers and coordinate support

FITS header blocks are parsed directly and data blocks skipped by seeking. Candidate covering orders are derived from all 72 header polynomials in each of seven products before consulting stored lists. The audit checks all **504 order geometries**, positive wavelength derivatives, original-event coverage, and separate common barycentric/topocentric center coverage. Only orders 2 and 3 cover each original event, giving fourteen unique product/order contexts and twenty-eight frame contexts.

| Event | Order-2 barycentric context support / 601 | Order-2 topocentric context support / 601 |
|---|---:|---:|
| 0114 | 406 | 406 |
| 0119 | 402 | 406 |
| 0124 | 351 | 406 |
| 0128 | 406 | 406 |
| 0133 | 379 | 406 |
| 0134 | 346 | 406 |
| 0138 | 330 | 406 |

The fixed common grid is ±3 Å in 0.01 Å steps, with metric core ±0.25 Å and reference flanks [−3,−1.5] and [1.5,3] Å. Every order-2 context covers all 51 core and 151 negative-flank coordinates, but **zero positive-flank coordinates in both frames**. Every order-3 context geometrically covers all 601 context, 51 core and 151 coordinates in each flank. Native domains, fixed-frame endpoints and offsets are retained in the receipt.

These are coordinate-support counts only. Finite samples, actual gaps, reference quality and usable normalization remain unassessed; geometry does not establish them. Both frames and overlapping orders reuse their source exposure.

## Fourteen mapping histories and distinct 0128 review stages

| Original order, every member | Global | Original local | Original baseline | Later five-window |
|---|---|---|---|---|
| 2 | true | false | false | true |
| 3 | true | true | true | true |

All fourteen original coordinates, trace/wavelength coefficients and orientations are checked against their exact source records. For six members the source is `raw_followup_batch03/NATIVE_MAPPING.json`, with explicit `baseline_mapping_verified`. For 0128 the original source is `raw_followup/NATIVE_MAPPING.json`, whose `mapping_verified` is the baseline field; later support comes from `raw_followup/mapping_followup/MAPPING_AUDIT.json`. Source paths and field bases are independently asserted. Later support does not rewrite an original false gate.

Six batch03 members preserve exact original primary/secondary/adopted U/U/U records. **0128 remains different:** original primary I, original secondary M normalized to I, and adopted baseline I for insufficient local mapping. Its later separate reviews are U/U and its current adopted code is U. All seven current labels remain U with unconfirmed physical origin. Exact original, agreement, baseline, later and root-current records are compared separately to the final inventory.

0128's original baseline NPZ panels are restored exactly: order 2 is 2,993 bytes (`611ae2dc067904173f901bf03208b6191a3df2adacbcb78179cce75c4a5576ee`); order 3 is 3,158 bytes (`99477055051b5e031ccd24afafa3371506c0178621d808d8f5325e23fc3d4be6`). Only their NPY headers are decoded. The later wider containers have different bytes and are bound separately; they are not substituted for original panels. Exact unchanged coordinate metadata and the prior reconstruction/pixel-preservation declarations are retained. This audit performs no new pixel-equality reconstruction and does not reinterpret the prior verification's acquisition-history or physical-origin limitations.

## Existing-data dependence and immutability

All fourteen earlier bounded-context plans retain exact original target membership and geometry. Old extension02 evidence, those plans and the entire tracked C015 phase remain unchanged. Numerical overlaps with C002/C003/C004, C011/C012 and C015 are on other targets, with disjoint exact observing products and no shared source pixels.

Original C018 seven-epoch/two-frame records already existed for every member, as did the completed 0128 wider mapping diagnosis. They remain dependent post-detection evidence. No blind, untouched, independent observing data or new observing-time claim follows; prior mapping/normalization diagnostics are not replayed.

Merged flux is uncalibrated ADU. Native BUNIT is absent, retaining instrumental labels without asserted calibrated-unit equivalence. Air-wavelength convention remains inherited from the archived extractor, without a new wavelength solution. ERR is declared unavailable, so positive uncertainty support is not inferred.

## Reproduction and bindings

From the repository root after exact restoration:

```bash
python work_harps_20261103_c018_context/input_audit/audit_inputs.py
```

Default caches are `../c010_archive_cache`, `../c016_archive_cache` and `../c018_archive_cache`. Repeated `--archive-dir PATH` options accept other exact copies. Reproduction rewrites this audit receipt only; its timestamp changes, so these hashes identify the reviewed run.

- `inputs/INPUT_INVENTORY.json`: `dea91e8d3288079c5d0fbfb1df5922ba1156375515a6714a426edba1afed8fa5`
- `inputs/restore_inputs.py`: `47dbcbe51acd3c01cd8d4775ab648795386e5a1ef86243839f024c2397bef32a`
- `input_audit/audit_inputs.py`: `cdd1b2d794104df1ca980201d9c056daed8580652141ea1d2c4d8a7121a101b2`
- `input_audit/INPUT_AUDIT.json`: `a07123c0cda26e03fe502630e157fbd0bcf67464ac4caef3349bdd593efa6579`
