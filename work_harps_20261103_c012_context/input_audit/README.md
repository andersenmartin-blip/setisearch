# C012 independent input audit

`INPUT_AUDIT.json` records **PASS: 346 checks, zero failures**, against baseline `e5f14130818450391896a09bcdd181a7d8327c87`. The audit rehashes the exact final inventory and restore helper, both cached archives, all 11 restored files, 14 historical sources, archived members and prior evidence parts. No archive acquisition, flux decoding, detector-pixel decoding, raw-image decoding or new classification occurred.

## Exact scope and coordinate custody

C012 is the original queue row 24 / R013 singleton `V2E2-0087`, HD112410, barycentric air center 3869.2675 Å. The fixed April 29 discovery is `ADP.2025-04-30T01:01:50.866`, BERV 3.40485846065643 km/s. Its exact topocentric anchor is 3869.2235557371996 Å, recomputed from this wavelength and discovery BERV. The same seven April–August 2025 target-specific epochs and BERV span 21.30284860830273 km/s are retained.

FITS header blocks are parsed directly and data blocks are skipped by seeking. All 72 degree-three order wavelength polynomials are freshly checked for increasing wavelength and original-event coverage. Only orders 2 and 3 cover the historical event. The audit independently checks coefficients, endpoints, trace geometry and the original raw-coordinate records. Saved NPZ members are opaque-hashed; only NPY dtype/shape headers are decoded.

| Order | Frame | Geometric grid support | Core support | Negative flank | Positive flank |
|---|---|---:|---:|---:|---:|
| 2 | Barycentric | 378/601 | 51/51 | 151/151 | 0/151 |
| 2 | Topocentric | 378/601 | 51/51 | 151/151 | 0/151 |
| 3 | Barycentric | 601/601 | 51/51 | 151/151 | 151/151 |
| 3 | Topocentric | 601/601 | 51/51 | 151/151 | 151/151 |

The grid is ±3 Å in 0.01 Å steps, the core ±0.25 Å, and reference flanks [−3,−1.5] and [1.5,3] Å. Order 2 ends at offsets +0.776413667 Å barycentric / +0.776404849 Å topocentric; the whole positive reference flank is outside its geometric domain. These header counts establish geometry alone. Finite samples, gaps and usable normalization remain unassessed. One discovery product supplies two orders and two saved raw panels: four order/frame contexts reuse the same exposure.

## Historical stages and dependency custody

| Order | Original global | Original local | Original baseline | Later five-window |
|---|---|---|---|---|
| 2 | true | false | false | true |
| 3 | true | true | true | true |

All original mapping stages are preserved distinctly. No registration, coordinate refit or mapping upgrade was performed. The exact primary, secondary, comparison and adopted records match the final inventory. Their U/U/U agreement retains broad structure shared by orders 2/3 and unconfirmed physical origin; the input audit performs no adjudication.

All ten completed bounded-window plans are checked against original target membership and remain unchanged. C012 is disjoint in wavelength from same-target C010 while reusing all seven observations. Its numerical overlap with C002/C003/C004 is on HD106515A with disjoint observing products; it shares none of their pixels or flux values. Original C012 epoch/native/raw evidence already existed. No blind, untouched-data, new-observation or independent-observation claim follows.

Merged flux is uncalibrated ADU; native BUNIT is absent and its flux label remains instrumental. Air-wavelength convention is inherited from the archived extractor; no new wavelength solution is asserted. ERR is declared unavailable, so no positive uncertainty support is inferred.

## Reproduction and bindings

Run from the repository root after restoring the exact inputs:

```bash
python work_harps_20261103_c012_context/input_audit/audit_inputs.py
```

The existing `../c010_archive_cache` is the default cache; `--archive-dir PATH` may supply another directory containing the same exact hashes. Reproduction rewrites only this audit receipt; it performs no network requests or science-array reads.

- `inputs/INPUT_INVENTORY.json`: `236ba3e633ebb1c1af464f8cb6fd51fc57ea7ee9fdf2d7f0a641e1cdafd90f26`
- `inputs/restore_inputs.py`: `dadfea319c88ad2797af5beea1fdffe776163a27056ade1c5833f982297c35d9`
- `input_audit/audit_inputs.py`: `917a7f14c18c727777be56ef8252b245fc84d2daebf2988651fed39766f4c173`
- `input_audit/INPUT_AUDIT.json`: `c01acd1d2eb935ebd6707a01c7caa4ad378cd6f7089efa902f94b635b8df119f`

The receipt binds the audit code and exact historical/handoff sources. Its timestamp changes on reproduction, so the committed receipt hash above identifies this reviewed run.
