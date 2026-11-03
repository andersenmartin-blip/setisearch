# C019 independent input audit

`INPUT_AUDIT.json` records **PASS: 1,539 checks, zero failures**, against GREEN baseline `103b6c4f471d1e473315b7d86579047516e26f91` and prior state `47db3c1322addab03740e98d6fb21babefe31504ab9efe2d50af07a35d98fdf2`. Four complete cached archives, all 27 exact restored files and 27 historical source bindings are independently hashed. Original archive members and all ten original raw panels retain exact custody. No network requests, observed-array decoding, raw-image decoding, new registration or classification occur.

## Five references, seven observations

C019 is the full original joint queue group on HD114783, R020, at rows 34/39/43/47/52. Exact member centers remain distinct:

| Event | Queue row | Catalog barycentric air center (Å) |
|---|---:|---:|
| V2E2-0115 | 34 | 3881.6125 |
| V2E2-0120 | 39 | 3881.615 |
| V2E2-0125 | 43 | 3881.6150000000002 |
| V2E2-0129 | 47 | 3881.615 |
| V2E2-0135 | 52 | 3881.6125 |

The catalog-extrema midpoint evaluates to **3881.6137500000004 Å**. The first original-queue discovery `ADP.2022-01-22T01:09:14.958`, observed January 21, 2022, has BERV 29.658729150824 km/s and fixes common topocentric anchor 3881.2297765555622 Å under center/(1+BERV/c). All five discovery references are preserved. The common metric core and original member cores/markers remain separate; corresponding edges differ by up to 0.00125 Å and the common core does not cover their complete union. No fitted peak or post-value core expansion occurs.

The same seven January 2022–July 2023 observations and BERV span 59.073251754930496 km/s are checked against original epoch inputs, the handoff and C018 custody. The March 22 and July 1, 2023 products remain observing epochs without becoming discovery references. Five references each have six other epochs: 30 directed nonself rows per frame/region represent 20 unordered observation pairs plus 10 reciprocal duplicates. These are metadata counts from seven reused observations, not independent samples or new numerical comparisons.

## Fresh coordinate coverage

FITS headers are parsed directly and data blocks skipped by seeking. Covering orders are derived from all 72 polynomials in each of five discovery products before consulting historical lists. All **360 order geometries**, positive wavelength derivatives, original-event coverage and separate common barycentric/topocentric center coverage are independently checked. Only orders 3 and 4 cover each original event, giving ten product/order and twenty frame contexts.

| Order, every product and both frames | Context coordinate support | Common-core support | Negative flank | Positive flank |
|---|---:|---:|---:|---:|
| 3 | 601/601 | 51/51 | 151/151 | 151/151 |
| 4 | 601/601 | 51/51 | 151/151 | 151/151 |

The fixed common grid is ±3 Å in 0.01 Å steps, metric core ±0.25 Å, and reference flanks [−3,−1.5] and [1.5,3] Å. All twenty contexts have full geometric coverage; native domains, fixed-frame endpoints and offsets remain in the receipt. These counts establish coordinate support only. Finite samples, actual gaps, reference quality and usable normalization remain unassessed. No C018 missing-flank outcome is transferred.

## Mapping and original review custody

| Event source | Original global/local/baseline | Later five-window stage |
|---|---|---|
| Four batch03 members, both orders | true / true / true | Explicitly true |
| Older raw_followup 0129, both orders | true / true / true | null / unassessed |

All ten original pixel/trace coordinates, wavelength coefficients and orientations are checked against exact source records. Batch03 uses explicit `baseline_mapping_verified`; 0129 uses the original `mapping_verified` field. Source paths, field bases and field-presence/assessment metadata are independently asserted.

**0129 has no original later-five-window field and was not selected in the separate mapping follow-up.** Its absence is checked in selection, order, event and disposition records. Its two later values remain `null`, with `UNASSESSED_FIELD_ABSENT_NOT_SELECTED_FOR_FOLLOWUP`; no true or false value is invented. Its original true mapping support remains intact.

All five original primary/secondary/adopted histories and current root records retain U/U/U with unconfirmed physical origin. The older 0129 original primary U, secondary U normalized U, adopted baseline U and current U are checked separately. No C018/0128 I/M/I history or mapping failure is transferred.

The 0129 original baseline NPZ panels are restored exactly: order 3 is 3,253 bytes (`7cd1c059bcf483750405adbabfcad53453afcaa4fccf58ef638d9dabb1cad061`); order 4 is 3,059 bytes (`128c8ba54611e7ac1309e8dd5dcd96b5b69b0ff728bb19cf0e7dbdff446ccfa4`). Every original panel is opaque-hashed against its own evidence archive. Only NPY shape/dtype headers are decoded; no later wider container or repeated mapping diagnosis is substituted.

## Existing-data dependence and unchanged work

All fifteen earlier bounded-context plans retain original membership, target and geometry. Old extension02 evidence, those plans and the entire tracked C018 phase remain unchanged. C019's seven merged products and five native products match the reused C018 inputs exactly.

The newly bounded C019 and C018 spectral windows are disjoint, while observations and some complete native products are shared. This disjointness does not assert independence of full historical raw crops or observing evidence. C005 overlaps numerically on HD106515A, with different observing products and no shared source pixels.

Original C019 seven-epoch/two-frame evidence already existed for all five members. No observation, blind/untouched data or independent observing-time evidence is added, and completed diagnostics are not replayed.

Merged flux is uncalibrated ADU. Native BUNIT is absent and retains instrumental labels without asserted calibrated-unit equivalence. Air-wavelength convention remains inherited from the archived extractor, without a new solution. ERR is declared unavailable, so positive uncertainty support is not inferred.

## Reproduction and final bindings

From the repository root after exact restoration:

```bash
python work_harps_20261103_c019_context/input_audit/audit_inputs.py
```

Default cache directories are `../c010_archive_cache`, `../c016_archive_cache` and `../c018_archive_cache`; repeated `--archive-dir PATH` options accept other exact copies. Reproduction rewrites this receipt only. Its timestamp changes, so these hashes identify the reviewed run.

- `inputs/INPUT_INVENTORY.json`: `ceff0bd21ef4dac8a27003450ed3c64b912190c040981c2c03c665a6c160b9ab`
- `inputs/restore_inputs.py`: `269611623f40193eebf7d3406c59ad5c0bddb014d6ae9faed56a1a0f582ae831`
- `input_audit/audit_inputs.py`: `ee0590ef4e92d4aa94a213ee48f890f5e58f72b2da69c9607fa95b86121117e6`
- `input_audit/INPUT_AUDIT.json`: `90c229a40759d7791b48a3340ee1b3fc1387c5ad8f3ed86a91da071fb93d1859`
