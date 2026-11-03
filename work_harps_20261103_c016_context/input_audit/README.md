# C016 independent input audit

`INPUT_AUDIT.json` records **PASS: 1,157 checks, zero failures**, against baseline `48bf48e93e7eb772993ba3b166f8035f309debff` and prior state `2039a86cf1a62151757a656a17f05b767fce0ea510eae1b9c4245a4666a284e8`. The audit checks all 19 exact restored files, three complete archives, 14 historical bindings, original archive members and preserved evidence parts. It performs no network requests, science-array decoding, raw-image decoding, new mapping or classification.

## New target, fixed group and exact members

C016 is the complete original queue group at rows 27/29/30/32, R017, on **HD114386**. Its own seven existing January 2022–August 2023 epochs and BERV span 51.572001697156 km/s are checked against original epoch input records and the C011 handoff. No HD112410 products, reference identity, numeric anchor or quality are transferred.

| Event | Queue row | Exact barycentric air center (Å) | Discovery product |
|---|---:|---:|---|
| V2E2-0094 | 27 | 4303.785 | ADP.2022-03-08T01:01:37.348 |
| V2E2-0096 | 29 | 4303.785 | ADP.2022-05-17T01:02:16.724 |
| V2E2-0098 | 30 | 4303.785 | ADP.2023-01-03T01:08:17.803 |
| V2E2-0110 | 32 | 4303.79 | ADP.2023-08-29T01:02:07.487 |

The common fixed center 4303.7875 Å is the midpoint of minimum/maximum catalog centers. The first original-queue discovery, March 7, 2022, fixes the common topocentric anchor: BERV 19.1606928163471 km/s and 4303.512448784194 Å under center/(1+BERV/c). All four distinct discovery references and their individual original centers remain explicit. The common ±0.25 Å core differs from each original member-centered core by 0.0025 Å at each corresponding edge; the receipt records these geometries separately. No center is fitted and no physical linewidth is inferred.

## Fresh coordinate coverage and historical custody

The audit parses FITS header blocks directly and seeks past data blocks. For each of four native products it derives candidate covering orders from all 72 header polynomials before consulting stored lists. It independently verifies 288 order geometries, their positive wavelength derivatives, original-event coverage and separate common barycentric/topocentric center coverage. Only order 19 covers each original event.

| Original native context | Order | Context support in each frame | Common-core support | Negative flank | Positive flank |
|---|---:|---:|---:|---:|---:|
| V2E2-0094 | 19 | 601/601 | 51/51 | 151/151 | 151/151 |
| V2E2-0096 | 19 | 601/601 | 51/51 | 151/151 | 151/151 |
| V2E2-0098 | 19 | 601/601 | 51/51 | 151/151 | 151/151 |
| V2E2-0110 | 19 | 601/601 | 51/51 | 151/151 | 151/151 |

The common fixed context is ±3 Å in 0.01 Å steps; its core is ±0.25 Å and reference flanks [−3,−1.5] and [1.5,3] Å. Both frames of each product have complete geometric coverage. Native topocentric domains, fixed-frame endpoints and offsets are retained in the receipt. This is coordinate support only: finite samples, actual gaps, reference quality and usable normalization remain unassessed. Four discovery exposures supply four orders/four preserved raw panels, giving eight order/frame contexts; the two frames reuse each exposure.

Every original order-19 context retains true global-grid, local, baseline and later five-window mapping support. Exact prior native pixel, raw row/column, coefficients and orientation are checked without registration or coordinate refits. The four saved NPZ files are opaque-hashed against original evidence; only NPY shape/dtype headers are decoded. Exact historical primary, secondary, comparison and adopted records are retained, all U/U/U with unconfirmed physical origin. Broad structure, neighboring shoulders and diffuse trace-associated excess do not establish a new origin.

## Existing evidence and immutable results

All twelve earlier bounded-context plans have separate observing products and disjoint wavelength windows; their exact target membership and geometry are verified. The old extension02 evidence, those plans and the entire tracked C011 phase remain unchanged.

Original C016 two-frame/seven-epoch records already existed for all four members. The same seven HD114386 observations also supported the completed blue normalization contexts for 0092/C013 and 0104/C014. Original event-epoch identities, focused product hashes, 28 archived profiles, eight focused profiles and 12 native/raw contexts are checked through preserved metadata. These completed routes remain complete; the audit does not replay them. Their unresolved origins and the separate later 0092 raw-window discrepancy do not alter the four historically supported C016 panels. This dependent post-detection context supplies no new observation, blind/untouched data or independent observing evidence.

Merged flux is uncalibrated ADU. Native BUNIT is absent and retains an instrumental label, without an asserted calibrated-unit equivalence. Air-wavelength convention is inherited from the archived extractor; no new wavelength solution is asserted. ERR is declared unavailable, so positive uncertainty support is not inferred.

## Reproduction and final bindings

From the repository root after exact input restoration:

```bash
python work_harps_20261103_c016_context/input_audit/audit_inputs.py
```

Default caches are `../c010_archive_cache` for science inputs and `../c016_archive_cache` for original raw-input parts 2/3. Repeated `--archive-dir PATH` options accept other exact copies. Reproduction rewrites this audit receipt only; its timestamp changes, so these hashes identify the reviewed run.

- `inputs/INPUT_INVENTORY.json`: `ef8b5ebe21e6ab03f037691c6582a3b70187a77908274c46e08e89e430f99cce`
- `inputs/restore_inputs.py`: `36451bef2b6557dfd81f765f36eeca7878dd525607b9d656ccca2b5fff5fd018`
- `input_audit/audit_inputs.py`: `c62ebe61b89add771da8a14e5b68677217ee58381f6ea7ab6bb281bd21d059f4`
- `input_audit/INPUT_AUDIT.json`: `a47994d7fb608bda6c67a3015acd82e2a30710cff748e43b78762a874602cb8a`
