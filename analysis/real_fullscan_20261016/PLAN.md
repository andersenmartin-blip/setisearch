# Proposed descriptive full six-scan search on one retained 2017 band

**Assessment: scientifically defensible and within the standing analysis instruction, as a separately identified descriptive search.** This does not admit, reopen, complete or overwrite either failed/retired 205-case bank or either old nine-band exposed phase. It requires a new fixed scope, its own once-only claims, a successful complete transport integration, and a complete independent numerical check. No permission request is introduced by this assessment.

## Identity and fixed choice

New study: `SETI_REAL_FULLSCAN_DESCRIPTIVE_20261016_B00`. New case: `SETI_REAL_FULLSCAN_DESCRIPTIVE_20261016_B00`. The former `SETI_SIXSCAN_BURST_20261014:real_sham:native170_q131` identifier appears only in source provenance; it is not an executed case identifier, alias, resumed claim or endpoint in the new study.

The band is **index 0 of the original canonical sorted `(native_chunk_index, core_q)` inventory**, namely **native170 / q131**. All nine original groups are retained in `SOURCE_SELECTION.json`. This is different from the first selected-track profile, which was native171 / q055. The source interval is `[178790496,178802592)`; the 4,096-carrier reference core is `[178794496,178798592)`. The prior top-nine feature in this band was epoch2 ON rank2. The first-band choice does not use the newly measured smearing result.

All six scans are from **28 April 2017**, one HIP98505/HD189733 observing visit with acquisition roles preserved in chronological ON, OFF, ON, OFF, ON, OFF order. They are not six independent observing visits. Source headers, scan directions, actual timestamps, 18.253611008 s row integration time and signed −2.7939677238464355 Hz channel spacing remain unchanged.

## What this adds, and the claims it cannot support

The proposed documented execution searches all 4,096 reference carriers, all seven four-row windows, widths 1/3/9/33, and the 5,723-point global cadence grid over ±4 Hz/s. The finest cadence-reference grid and wide boxes can expose features missed by the earlier coarse width1 search and local profiles. Full maps and the complete OFF inventories make it possible to inspect what generated any high score and whether a compatible OFF feature exists in the declared discrete family.

It remains a re-search of already exposed, postselected real data. The original unrecovered run might have attempted the same family; its outcome is unknown, so this cannot be called a never-previously-attempted geometry or independent confirmation. No new telescope coverage or observation is added. Engineering integration shows that complete outputs can survive transport; it does not establish detector recovery probability, RFI robustness or telescope false-alarm calibration.

**`rank_status = NOT_APPLIED_NO_CALIBRATION`.** Do not run a reference panel, assign Gamma16 ranks to the telescope data, supply a p-value, set missing ranks to 1, calculate a recovery denominator or declare sensitivity. The fixed numerical ON≥10 and OFF≥8 cuts are empirical descriptive cuts only. An empty retained ON list means zero retained hypotheses reached that fixed cut in this completed declared search; it is not a general null result. A surviving OFF comparison does not establish sky or artificial origin.

The global ON output is **all retained combined top-five hypotheses per carrier whose score is ≥10**, at most 3 × 4096 × 5 = 61,440 records. It is **not** an exhaustive inventory of every scored ON hypothesis above 10. By contrast, every unique OFF native-four-row identity with score≥8 and all donor aliases must be retained from the exhaustive OFF traversal. The OFF top five cannot prove absence of a match.

## Metadata-only source reader specification

Before numerical imports and raw array decoding: create the new claim once; hash the new frozen scope and all source/transport/QA files; authenticate the existing source archive and the exact context/selection metadata. The archive and source-selection pins are in `SOURCE_SELECTION.json`. Bind the pending engineering integration PASS receipt by hash in the final scope; do not execute until it exists. Final source pins must be reread after parent implementation is complete, rather than assuming mutable development files are frozen.

Use a **new reader**, rather than calling the old worker main, `authenticate_exposed_prerequisites`, `read_exposed_arrays`, a generator, an old bank coordinator or an old GO. The former requirement that the old 205-case integrity gate close remains in its original scope and is never set true by this study. The new wrapper may call unchanged pinned numerical functions as libraries under its own descriptive admission.

For each of the six source members below, authenticate the complete NPZ and normalization JSON bytes before decoding the NPZ. Require a regular float32 raw_power array with shape `(16,12096)`, finite nonnegative values, the exact declared source_channel0, time rows0..15 and normalization_source_channels equal to the 4,096 selected core channels. Require original header equality across all bands for each scan and agreement with the source context metadata and pinned coordinate contract. Do not shift, pad, crop, replace, inject into, normalize in place or regenerate the retained raw array. Keep complete array byte hashes in the new payload.

Read the pinned old coordinate contract as a metadata template, then use a new in-memory geometry record with this selected band's source/core intervals. Preserve the six original headers and actual timing arrays. Never edit the old contract or scope. `worker.scan_inputs`, `detector.search_cadence`, `worker.verify_result_inventory` and `worker.json_and_array_store` may be imported unchanged after source authentication. No recovery function is needed: the real-data record has no injected truth. Require `synthetic_injection=false`, `postselected=true`, `fresh_background=false`, `new_observation=false`, and use the new case ID throughout.

Normalization is the unchanged old detector preprocessing over this selected core (running median501, per-row robust center/scale and winsorized location); no parameters are refitted after inspecting an output. The independently pinned source-normalization files are retained as provenance, and the numerical QA recomputes preprocessing from raw values. No result-dependent tuning, threshold change or added recurrence condition is permitted.

### Exact existing raw input pins

Every path below is relative to `SETI_NATIVE_SPOR_2026-10-14/` inside the existing source archive. The six corresponding normalization pins and complete header metadata are in `SOURCE_SELECTION.json` and the authenticated source context JSON.

| Scan | Raw member | Bytes | SHA-256 |
|---|---|---:|---|
| epoch1_on | `seti_work/seti_burst_full/context_results/epoch1_on_native170_q131_raw12096.npz` | 808140 | `e98a0cee33a4c0b249ba363e623354176c7e6fc745dc151b41ec717a7e5f55d3` |
| epoch1_off | `seti_work/seti_burst_full/context_results/epoch1_off_native170_q131_raw12096.npz` | 808140 | `b61d699b8113ee68cbfaf62d28135fb3b46eaa7fc2d5bf981cceaf8c61103879` |
| epoch2_on | `seti_work/seti_burst_full/context_results/epoch2_on_native170_q131_raw12096.npz` | 808140 | `d1d7470ff2a083abb30932ac6f9febc8631eb14e8b50c35ad10ba86c2a7395c9` |
| epoch2_off | `seti_work/seti_burst_full/context_results/epoch2_off_native170_q131_raw12096.npz` | 808140 | `abf5aba13a5ef886737d7a00c0e6d7d4f7b1d1e851769d0863d027c5b4a2b211` |
| epoch3_on | `seti_work/seti_burst_full/context_results/epoch3_on_native170_q131_raw12096.npz` | 808140 | `666eac7fd0c8cdf49265c8d21626d7132f4c914052be8644f014c5206a082e33` |
| epoch3_off | `seti_work/seti_burst_full/context_results/epoch3_off_native170_q131_raw12096.npz` | 808140 | `90a3bbbd0358c031df79421254cbd09eb2f594b18a0732e82712f54ec8cf061f` |

## Fixed execution, numerical QA and resources

The final parent runner must use an exclusive new ledger with **1,300 CPU-seconds**: reserve **600** for the one producer, **600** for the one independent verifier, and **100** for preparation, summary and delivery. Run the numerical phases sequentially, each with **1 GiB address space**, **1,800 s wall limit**, a complete parent `wait4` receipt, single-thread numerical-library settings, and no retry. Reservation acceptance must use complete whole-child CPU≤600 after reap; a valid payload followed by over-limit closure is a failed phase. Do not refund or reuse either old bank's debits or reservations.

Use a **2 GiB total new output bound**, including payload, claim, partials, stdout/stderr, manifests and receipts. Per-phase slot reservations are producer800MiB, QA64MiB, logs1MiB per phase and metadata1MiB; the producer physical payload writer itself is capped at768MiB. Reserve writer capacity before execution and enforce physical writer quotas without assuming a compression ratio. The producer payload is written once and reused by QA, not duplicated. Parent must derive the full-array/record worst-case bound before admission and reserve the remaining output allowance for logs and reports. If actual complete OFF inventories exceed the unchanged 2,000,000-row cap per OFF scan or a writer quota fails, retain a failed partial execution and stop; do not lower the threshold, truncate an inventory, or turn a partial into a negative OFF match.

The independent verifier authenticates both source raw NPZ bytes and the complete payload descriptor census; recomputes the complete geometry, native rounding aliases, original row preprocessing, all widths/windows/carriers, each retained map, every OFF≥8 identity and all relevant witnesses using pinned independent QA functions. It imports neither producer arithmetic nor detector code. It checks every ON retained threshold record and OFF comparison against independently reconstructed maps/inventories. It may call the unchanged `verify_recovery` empty-activity branch only to authenticate explicit non-applicability, with no injected recovery trial, denominator or measured recovery result. It validates the descriptive flags, new ID, no-calibration rank state and preserved source acquisition roles.

The summary reports measured CPU/wall/RSS, source/output pins, per-scan maxima and inventory counts; raw retained≥10 counts; matched/surviving descriptive counts; actual searched geometry; and complete/incomplete status. No old summary integrity gate is reused or manufactured. A timeout, quota failure, missing phase or QA failure is explicitly incomplete, not a measured zero. A full QA PASS establishes numerical agreement within its frozen tolerances, not telescope significance.

## Preserved restrictions

Cost stays **0 DKK**. No new telescope requests or payload downloads, paid compute, observing bookings, external messages or source discovery are needed. Original A/B remains FAIL_CLOSED; protected2016 and unavailable2019 routes remain closed. Both old bank outcomes and old nine-band statuses are unchanged. The formal checkpoint remains20 October2026. All newly retained outputs are saved before reporting progress.

**Current status: source/reader implementation being prepared; no raw values decoded or detector run.** This planning step read metadata, source code and scope documents; it did not open/decode any real raw spectral array or run a detector. The final executable scope/code and successful integration receipt must be frozen and checked before this proposed once-only numerical execution.

The required source ZIP is **48,468,705 bytes**, SHA-256 `52b948958c89069a7afb563cf377ee33e4f1324e014428d597b4b3e3a20f6eb3`, now restored at `sources_recovered_20261016/SETI_NATIVE_SPOR_2026-10-14.zip`. A preparation-only metadata snapshot initially hashed a truncated29,396,480-byte local copy as `a902bab...` without first checking it against the authoritative archivepin. That copy fails ZIP validation, has not been admitted or decoded for this search, and is preserved unchanged. `SOURCE_SELECTION.json` records this rejected preparation observation separately; the corrected expected pin matches the earlier frozen smearing scope, its independent QA and the original coordinate contract.

The final producer and reader are `producer.py` and `reader.py` in this source directory. The real-data payload contains `worker_json`, `worker_arrays`, `legacy_descriptors`, `truth`, `admission`, `case`, `inputs` and a copied coordinate `contract`. Only the two source/core coordinate intervals differ from the pinned legacy contract. Its remaining study/calibration fields are metadata template provenance, and grant no admission. A legacy `calibrationglobal_ON_max` field is retained solely as an explicitly uncalibrated alias of the actual global ON maximum. `recovery` contains only the original worker ABI's explicit `recovery_applicable=false`, an empty activity list and a reason; it is not measured recovery. No rank, calibration or detector recovery function is applied.
