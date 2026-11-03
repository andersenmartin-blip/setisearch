# C022 independent input audit

`INPUT_AUDIT.json` records **PASS: 962 checks, zero failures**, against baseline `b586350441ce4bf3f21020a83d688e0281bfaca3` and prior state `039ebd60993c8c82fdb54fe48013c3acc8e021ec46d478d138f4d5ddb3f373c1`. The receipt binds the final root baseline receipt, four complete cached archives, all 16 restored files and 34 historical source bindings. Original archive members, all three original raw panels and the separate 0131 wider archive retain exact custody. No network requests, observed-array/raw-image decoding, new registration or classification occur.

## Exact members and reference identities

C022 is the full original joint queue group on HD114783, R023:

| Event | Queue row | Exact catalog barycentric air center (Å) |
|---|---:|---:|
| V2E2-0117 | 36 | 4312.245 |
| V2E2-0127 | 45 | 4312.245 |
| V2E2-0131 | 49 | 4312.237499999999 |

The catalog-extrema midpoint is **4312.241249999999 Å**. First-queue discovery `ADP.2022-01-22T01:09:14.958`, observed January 21, 2022, BERV 29.658729150824 km/s, fixes common topocentric anchor **4311.814678415948 Å** under center/(1+BERV/c). The common metric core and exact original member cores/markers remain separate. Their edges differ by approximately 0.00375 Å, so the common core is not the full original-core union. No fitted peak, recentering or post-value expansion occurs.

The same seven HD114783 January 2022–July 2023 observations and BERV span 59.073251754930496 km/s are checked against original inputs, the handoff and C021 source custody. References are January 21 and May 5, 2022, and January 16, 2023. February 5, 2022, and March 22, May 15 and July 1, 2023 remain non-reference epochs. Each reference compares with six other epochs: 18 directed nonself records per frame/region represent 15 unordered observation pairs plus three reciprocal duplicates over seven reused observations. These metadata counts do not add independent observations.

## Fresh headers and coordinate support

FITS headers are parsed directly and data blocks skipped by seeking. Covering orders are derived from all 72 polynomials in each of three discovery products before consulting stored lists. All **216 order geometries**, positive derivatives, original-event coverage and separate common barycentric/topocentric center coverage are independently checked. Only order 19 covers each original event, giving three product/order and six frame contexts.

| Every order-19 context, both frames | Coordinate support |
|---|---:|
| Fixed ±3 Å context, 0.01 Å grid | 601/601 |
| Common ±0.25 Å metric core | 51/51 |
| Negative reference flank [−3,−1.5] Å | 151/151 |
| Positive reference flank [1.5,3] Å | 151/151 |

All six contexts have complete geometric support. Native domains, fixed-frame endpoints and offsets are retained in the receipt. These counts establish coordinate support only. Finite samples, actual gaps, reference quality and usable normalization remain unassessed.

## Direct C021 exposure and reference-flank dependence

All seven merged products and the three native products match C021 source bytes exactly. Its frozen plan and completed closure are bound. The audit verifies its fixed common core, signed 1.5–3 Å reference rule and retention of structured samples without masks.

The barycentric windows share **[4309.241249999999, 4312.82625] Å**, width **3.585000000000946 Å**, on the same source observations/native lineage. The geometry is checked independently in both fixed frames. In barycentric coordinates:

| Common core already exposed | Containing fixed reference flank |
|---|---|
| C022 [4311.991249999999, 4312.491249999999] Å | C021 positive [4311.32625, 4312.82625] Å |
| C021 [4309.57625, 4310.07625] Å | C022 negative [4309.241249999999, 4310.741249999999] Å |

The cores are distinct, but each is wholly contained in the other's fixed reference flank. C022's common core was already exposed by completed C021. The receipt also records the corresponding topocentric overlap and mutual containment. Fixed structured flanks retain all samples without candidate masks or a line-free assumption. This is direct reused spectral evidence, not an untouched or independent test. The audit establishes provenance and coordinate exposure without decoding spectral arrays or asserting equality/independence of complete saved raw crops.

Earlier same-target C018/C019 blue windows are disjoint. C006/C007 numerical overlaps are on HD106515A, with different observing products and no shared source pixels. All seventeen earlier bounded plans retain original membership, target and geometry; old extension02 evidence and the entire tracked C021 phase remain unchanged.

## Mapping stages and 0131 custody

| All three original order-19 contexts | Recorded stage |
|---|---|
| Original global-grid support | true |
| Original local support | false |
| Original baseline verification | false |
| Later five-window support | true |

Exact original source paths, field bases, native pixels, raw row/column coordinates, orientations and trace/wavelength coefficients are checked separately from later support. Batch03 explicitly stores `baseline_mapping_verified`; older 0131 uses original `mapping_verified`, with later support in the separate mapping-followup audit. Later support does not rewrite failed original stages.

Two batch03 members retain exact original primary/secondary/adopted U/U/U. **0131 retains original primary I, secondary M normalized I and adopted baseline I**, followed by completed unchanged-coordinate wider diagnosis and later U/U/current U. All three current labels remain U with unconfirmed physical origin. Exact original, agreement, baseline, later and root-current records are compared separately to the inventory.

The original 0131 baseline NPZ is **3,602 bytes**, SHA `ddba2ac8fc401e59cf646ff6c70ebb598da650d45f1c3decea5b34176f6069bb`. It remains separate from the later **5,497-byte** wider container, SHA `a1d0e34caa677b4d235d23fa30cac276d705ad27dfdd1a5d6645e5f574a464f1`. Original panels are opaque-hashed and only their NPY shape/dtype headers decoded. Unchanged coordinate metadata and prior reconstruction/pixel-preservation declarations are retained as prior evidence, without a new pixel-equality reconstruction or replayed diagnosis.

Original C022 epoch/raw evidence and completed 0131 mapping evidence already existed. No new observing time, blind/untouched data, independent evidence or archive-completeness claim follows.

Merged flux is uncalibrated ADU. Native BUNIT is absent and retains instrumental labels without asserted calibrated-unit equivalence. Air-wavelength convention remains inherited from the archived extractor, without a new solution. ERR is declared unavailable, so positive uncertainty support is not inferred.

## Reproduction and final bindings

From the repository root after exact restoration:

```bash
python work_harps_20261103_c022_context/input_audit/audit_inputs.py
```

Default caches are `../c010_archive_cache`, `../c016_archive_cache` and `../c018_archive_cache`; repeated `--archive-dir PATH` options accept other exact copies. Reproduction rewrites this receipt only. Its timestamp changes, so these hashes identify the reviewed run.

- `inputs/INPUT_INVENTORY.json`: `046b3a3b58cee917f912e86f98f0a6ed8cfd2b2efe319052e650b4e31de0774c`
- `inputs/restore_inputs.py`: `92acf3120262f40af7a43b57882c0ca01b8d5c1f8a3a28c8cdeb8dd75926700b`
- `input_audit/audit_inputs.py`: `22e712a68e0c06b7f1435d0b88779de8db9a3deb021b985430d93b0d2995ead5`
- `input_audit/INPUT_AUDIT.json`: `ae5288d3e3e72dbc88b7e15218a6bfb04c98956a22c6f6ff60a42aa084552ba2`
