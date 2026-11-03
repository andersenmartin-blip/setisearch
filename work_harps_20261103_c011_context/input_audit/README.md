# C011 independent input audit

`INPUT_AUDIT.json` records **PASS: 351 checks, zero failures**, against baseline `9abccb3c723026a15c822f938d2dd0080854022f`. The audit rehashes the final inventory/helper, both complete cached archives, all 11 restored files, 14 historical sources, archive members and original evidence parts. It performs no acquisition, science-array decoding, raw-image decoding or classification.

## Exact scope and coordinate custody

C011 is original queue row 25 / R012, singleton `V2E2-0089` on HD112410, exact barycentric air center 3865.6775000000002 Å. Its discovery `ADP.2025-05-29T01:01:14.389` was observed May 28, 2025, with BERV −5.48386283255014 km/s. The recomputed fixed topocentric anchor is 3865.748213029564 Å. This May discovery reference differs from the April C012 reference. The same seven April–August 2025 HD112410 epochs and BERV span 21.30284860830273 km/s are preserved.

FITS header blocks are parsed directly and data blocks skipped by seeking. All 72 degree-three order wavelength polynomials are freshly checked for positive derivative and original-event coverage. Orders 2 and 3 alone cover the event; each order retains its own wavelength coefficients, trace coefficients and original raw mapping coordinates. Saved NPZ members are opaque-hashed and only NPY dtype/shape headers are decoded.

| Order | Frame | Context support | Core support | Negative flank | Positive flank |
|---|---|---:|---:|---:|---:|
| 2 | Barycentric | 601/601 | 51/51 | 151/151 | 151/151 |
| 2 | Topocentric | 601/601 | 51/51 | 151/151 | 151/151 |
| 3 | Barycentric | 601/601 | 51/51 | 151/151 | 151/151 |
| 3 | Topocentric | 601/601 | 51/51 | 151/151 | 151/151 |

The fixed grid is ±3 Å in 0.01 Å steps, with original core ±0.25 Å and reference flanks [−3,−1.5] and [1.5,3] Å. Both orders geometrically cover the full context in both frames. The receipt includes native topocentric endpoints, fixed-frame endpoints and offsets. These are coordinate-support counts only; finite samples, actual gaps, reference quality and usable normalization are not assessed or inferred. A single discovery product supplies two orders and two saved raw panels, giving four order/frame contexts from the same exposure.

## Historical stages and dependence

| Order | Original global | Original local | Original baseline | Later five-window |
|---|---|---|---|---|
| 2 | true | true | true | true |
| 3 | true | true | true | true |

The exact original mapping stages are retained; C012's order-2 failures do not apply to this May exposure. No mapping, registration or coordinate refit is performed. Exact primary, secondary, comparison and adopted records match the inventory. All retain U/U/U and unconfirmed origin for broad native structure and diffuse trace-associated enhancement. The audit makes no new classification.

Eleven prior frozen plans are checked against original target membership and remain unchanged; the entire tracked C012 phase is also unchanged. C011 and C012 share the same seven observing products. Their broad barycentric windows overlap [3866.2675, 3868.6775000000002] Å, width 2.4100000000003092 Å, while the original C011 core [3865.4275000000002, 3865.9275000000002] Å lies outside C012's window. The broad surrounding/reference flux is reused and provides dependent post-detection context. C010 is disjoint in wavelength. Numerical overlaps with HD106515A C002/C003 use distinct products. Original C011 epoch/native/raw evidence already existed; no blind, untouched, independent-data or new-observation claim follows.

Merged flux is uncalibrated ADU. Native BUNIT is absent, so its label remains instrumental; the audit asserts no calibrated-unit equivalence. The air-wavelength convention remains inherited from the archived extractor, without a new wavelength solution. ERR is declared unavailable, providing no positive uncertainty support.

## Reproduction and bindings

From the repository root after exact restoration:

```bash
python work_harps_20261103_c011_context/input_audit/audit_inputs.py
```

The default archive cache is `../c010_archive_cache`; `--archive-dir PATH` accepts another location with the exact same archived bytes. Reproduction rewrites this receipt and uses no network requests or science-array values. The receipt binds its code, the inventory/helper and exact historical/handoff sources. Its timestamp changes on reproduction; the hashes below identify this reviewed run.

- `inputs/INPUT_INVENTORY.json`: `287e3d994e1f94418f5ad07b373a3664da51987438a00773890df5f799968ba3`
- `inputs/restore_inputs.py`: `a871ca7cfe2a4ee8c9209beaec8bf6010ffc7811761696991d4ff875a7b53a29`
- `input_audit/audit_inputs.py`: `9fc57fdcb4f24558d88b542f19a1afcc0df61c868e68a08ad890a3bb9a7ebd51`
- `input_audit/INPUT_AUDIT.json`: `cba0b2dce914639087663c60054145dd7b239aa08031725672a2513bd27774e5`
