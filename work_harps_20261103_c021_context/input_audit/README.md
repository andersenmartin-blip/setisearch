# C021 independent input audit

`INPUT_AUDIT.json` records **PASS: 1,458 checks, zero failures**, against GREEN baseline `b4728c70f901ae2b7e9eb4f344981a5db900e691` and prior state `73e2470696e3d55524d3d0ef0199f2b9c56801ebc3a6d344952f6038ce7518f3`. Five complete cached archives, all 22 restored files and 34 historical bindings are independently hashed. Original archive members, all five original raw panels and the separate 0130 wider archive retain exact custody. No network requests, observed-array/raw-image decoding, new registration or classification occur.

## Exact members and five references

C021 is the full original joint queue group on HD114783, R022, at rows 35/40/44/48/55. Original member floats and mapping gates remain event-specific:

| Event | Queue row | Catalog barycentric air center (Å) | Original local/baseline |
|---|---:|---:|---|
| V2E2-0116 | 35 | 4309.827499999999 | false / false |
| V2E2-0121 | 40 | 4309.827499999999 | true / true |
| V2E2-0126 | 44 | 4309.825 | false / false |
| V2E2-0130 | 48 | 4309.825 | false / false |
| V2E2-0139 | 55 | 4309.827499999999 | true / true |

The catalog-extrema midpoint is exactly 4309.82625 Å. First-queue discovery `ADP.2022-01-22T01:09:14.958`, observed January 21, 2022, BERV 29.658729150824 km/s, fixes common topocentric anchor 4309.39991731037 Å under center/(1+BERV/c). The common metric core and original member cores/markers remain separate; edges differ by up to 0.00125 Å, so the common core is not the full original-core union. No fitted peak or post-value expansion occurs.

The same seven HD114783 January 2022–July 2023 observations and BERV span 59.073251754930496 km/s are verified against original records and prior product custody. References are January 21, February 5 and May 5, 2022, plus January 16 and **July 1, 2023**. March 22 and May 15, 2023 remain non-reference epochs. Exact set differences verify that July replaces C019's May reference, despite equal reference counts.

Five references each have six other epochs: 30 directed nonself rows per frame/region represent 20 unordered pairs plus 10 reciprocal duplicates. These are metadata counts from seven reused observations, not independent samples or new numerical comparisons.

## Fresh header geometry

FITS headers are parsed directly and data blocks skipped by seeking. Covering orders are derived from all 72 polynomials in each of five native products before consulting stored lists. All **360 order geometries**, positive derivatives, original-event coverage and separate common barycentric/topocentric center coverage are independently checked. Only order 19 covers each event, giving five product/order and ten frame contexts.

| Every order-19 context, both frames | Coordinate support |
|---|---:|
| Fixed ±3 Å context, 0.01 Å grid | 601/601 |
| Common ±0.25 Å metric core | 51/51 |
| Negative reference flank [−3,−1.5] Å | 151/151 |
| Positive reference flank [1.5,3] Å | 151/151 |

All ten contexts have complete geometric support. Native domains, fixed-frame endpoints and offsets remain in the receipt. These counts establish coordinate support alone; finite samples, actual gaps, reference quality and usable normalization remain unassessed. Previous-group quality or missing-flank outcomes are not transferred.

## Original and later mapping/review stages

Original global-grid support and later five-window support are true for every member. The three failed original local/baseline stages in the member table remain false; later support does not rewrite them. Exact original source paths, baseline field bases, native pixels, raw row/column coordinates, orientations and trace/wavelength coefficients are checked separately from later support.

Batch03 stores explicit `baseline_mapping_verified`, with its five-window field in the same source mapping file. Older 0130 uses original `mapping_verified`; its later stage is in `raw_followup/mapping_followup/MAPPING_AUDIT.json`. No C019/0129 null/unassessed stage is transferred.

Four batch03 members retain exact original primary/secondary/adopted U/U/U records. **0130 differs:** original primary I, secondary M normalized I, adopted baseline I for insufficient local mapping; later separate reviews U/U and current adopted U. All current labels remain U with unconfirmed physical origin. Exact original, agreement, baseline, later and root-current records are compared separately to the inventory.

The original 0130 baseline order-19 NPZ is **3,532 bytes**, SHA `a7dd8a01661a3a51629a1939b159814059d02acd8b5ce32433538f4bf9e0272e`. It is restored exactly from original baseline evidence. The later wider container is **5,534 bytes**, SHA `1474320f43541da160cacb6c8cf7f1664b3df29ae38d95a5e689d51c03181d0b`, and is bound separately. It is not substituted for the original panel. Only original NPY shape/dtype headers are decoded. Unchanged coordinate metadata and prior reconstruction/pixel-preservation declarations are retained as recorded prior evidence, without a new pixel-equality reconstruction or physical-origin validation.

## Dependence and unchanged work

All sixteen earlier bounded-context plans retain exact membership, target and geometry. Old extension02 evidence, those plans and the entire tracked C019 phase remain unchanged. Seven merged products and five native products match prior C018 custody exactly.

C021 reuses the observations/native products at a bounded spectral window disjoint from C018/C019's blue windows. This disjointness does not establish independence of complete historical raw crops or observing evidence. The nearby HD114386 C016 window is disjoint by approximately 0.03875 Å. C006/C007 overlap numerically on HD106515A with different observing products and no shared source pixels.

Original C021 seven-epoch/two-frame evidence and completed 0130 wider mapping evidence already existed. No new observation, blind/untouched data or independent observing-time claim follows; completed mapping/normalization diagnostics are not replayed.

Merged flux is uncalibrated ADU. Native BUNIT is absent and retains instrumental labels, without asserted calibrated-unit equivalence. Air-wavelength convention remains inherited from the archived extractor, without a new solution. ERR is declared unavailable, so positive uncertainty support is not inferred.

## Reproduction and final bindings

From the repository root after exact restoration:

```bash
python work_harps_20261103_c021_context/input_audit/audit_inputs.py
```

Default cache directories are `../c010_archive_cache`, `../c016_archive_cache` and `../c018_archive_cache`; repeated `--archive-dir PATH` options accept other exact copies. Reproduction rewrites this receipt only. Its timestamp changes, so these hashes identify the reviewed run.

- `inputs/INPUT_INVENTORY.json`: `61c26f45548618c783ad71bd2f6eb79d82528740918d2de67e58a924ccc09fd0`
- `inputs/restore_inputs.py`: `00c96f8584c58506d7da4c9e67604a648eefb55b1e0a65272cbd6cf396f64470`
- `input_audit/audit_inputs.py`: `538dc22715b28df4670abada639324f73bd00256b74b47898f540b9e753a4710`
- `input_audit/INPUT_AUDIT.json`: `e7771d73416ee6f9aad864a1692cae04e4c3b52dfa728e87d541b72672c8324c`
