# C015 independent input audit

`INPUT_AUDIT.json` records **PASS: 363 checks, zero failures**, against baseline `0bac7db413fbf2ae02546fa7219df5e647bd1a85` and prior state `438fcf32c51c4c8979da8d8043a8e06f5fda86cd639c04bed6af9b9ee448fd40`. The audit checks two complete archived inputs, all 10 exact restored files, 14 historical source bindings, original archive members and preserved evidence parts. It performs no network requests, science-array decoding, raw-image decoding, mapping fit or classification.

## Exact singleton and May reference

C015 is original queue row 28 / R016, singleton `V2E2-0095` on HD114386 at exactly 3869.915 Å barycentric air. Its own discovery `ADP.2022-05-17T01:02:16.724` was observed May 16, 2022, BERV −10.767337430651 km/s. The fixed topocentric anchor is independently recomputed as 3870.0539967497375 Å under center/(1+BERV/c).

The original core is [3869.665, 3870.165] Å and the fixed ±3 Å context [3866.915, 3872.915] Å. C015 retains one discovery reference and one catalog core. The same seven existing HD114386 January 2022–August 2023 observations and BERV span 51.572001697156 km/s are verified against original epoch inputs and handoff identities. No C016 joint midpoint, March anchor, four-reference design or order-19 scope is transferred.

## Fresh header scope and preserved mapping

FITS headers are parsed directly while data blocks are skipped by seeking. The audit derives candidate covering orders from all 72 polynomials before consulting stored lists, then independently checks all endpoints, positive derivatives and original-event coverage. **Only order 3 covers the original event.**

Order 2 ends at 3870.006986547364 Å topocentric, about 0.0470102023735 Å below the original center. This boundary evidence is recorded separately. Nearby partial context cannot create another original event-covering order or raw panel.

| Frame, order 3 | Context coordinate support | Core support | Negative flank | Positive flank |
|---|---:|---:|---:|---:|
| Barycentric | 601/601 | 51/51 | 151/151 | 151/151 |
| Topocentric | 601/601 | 51/51 | 151/151 | 151/151 |

The fixed grid is ±3 Å in 0.01 Å steps, with core ±0.25 Å and reference flanks [−3,−1.5] and [1.5,3] Å. Order 3 geometrically covers the full context in both frames. Its native domain, fixed-frame endpoints and offsets are retained in the receipt. These counts establish coordinate support only; finite samples, actual gaps, reference quality and usable normalization remain unassessed. One native product and one original raw panel supply two frame contexts from the same exposure.

The original order-3 global-grid, local, baseline and later five-window mapping stages are all true and remain distinct. Native pixel 1619, raw row 2476, raw column 126.71408818235776 and unchanged orientation/trace coefficients are checked against exact original custody. The one 6,853-byte NPZ panel is opaque-hashed against original evidence; only NPY shape/dtype headers are decoded. Exact primary, secondary, comparison and adopted records retain U/U/U and unconfirmed origin for a broad multi-sample native feature and diffuse trace-associated enhancement. No new registration or origin decision occurs.

## Previous evidence and wavelength dependence

All thirteen completed bounded-context plans retain exact original target membership and geometry. Old extension02 evidence, those plans and the entire tracked C016 phase remain unchanged.

C015 reuses all seven C016 observations; its own May product was one of C016's four references. Its wavelength context is disjoint from C016's [4300.7875, 4306.7875] Å window. Numerical overlaps with C002/C003/C004 on HD106515A and C011/C012 on HD112410 have different observing products and share no source pixels.

Original C015 seven-epoch/two-frame evidence already existed. The same HD114386 observations also supplied the completed 0092/0104 blue normalization study. The audit verifies original epoch identities, focused-product hashes, preserved 28-profile/eight-focus/12-native-context scope, and all eight merged and 12 native focused window centers. With the original fixed ±2 Å halfwidth, each completed normalization window is disjoint from the respective C015 fixed frame. The completed study is preserved and not replayed. This dependent post-detection context supplies no new observation, blind/untouched data or independent observing evidence.

Merged flux is uncalibrated ADU. Native BUNIT is absent and retains an instrumental label, without asserted calibrated-unit equivalence. The air-wavelength convention remains inherited from the archived extractor, without a new wavelength solution. ERR is declared unavailable, so positive uncertainty support is not inferred.

## Reproduction and final bindings

From the repository root after exact restoration:

```bash
python work_harps_20261103_c015_context/input_audit/audit_inputs.py
```

Default caches are `../c010_archive_cache` for science part 1 and `../c016_archive_cache` for original raw-input part 2. Repeated `--archive-dir PATH` accepts other exact copies. Reproduction rewrites this receipt only; its timestamp changes, so these hashes identify the reviewed run.

- `inputs/INPUT_INVENTORY.json`: `ef6ca3750128fd47fc96f5b7eca83877fb2d96cb7d5780008f3467d3c5376987`
- `inputs/restore_inputs.py`: `77fefeae6e1bf210ae3e8c212fd5df9224a1febce21bd72ba1e83cbdb23c585f`
- `input_audit/audit_inputs.py`: `6e17be3b208ba56c2fcbb5bc121ee4d5ab6b024b26e34ac762b4780181d86ff9`
- `input_audit/INPUT_AUDIT.json`: `53701eefefb67db0395235a3d33856f320a7e7ec4b38e5b1b3002583f9789a7f`
