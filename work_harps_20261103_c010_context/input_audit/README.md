# C010 independent input audit

[audit_inputs.py](audit_inputs.py) produced [INPUT_AUDIT.json](INPUT_AUDIT.json): **PASS, 303 checks, zero failures**. This checkpoint verifies identity, custody, the target-specific cohort, historical decisions and header geometry. No new spectral flux or detector pixel values were decoded or interpreted.

The original C010 singleton is **V2E2-0086 on HD112410**, exact catalog barycentric-air center **3823.0649999999996 Å**, original queue row 23 / R011 on route INDIVIDUAL_PROFILE_CONTEXT. Its discovery is `ADP.2025-04-30T01:01:50.866`, observed on **2025-04-29**. The April 2025 discovery BERV **3.40485846065643 km/s** independently gives fixed topocentric-air anchor **3823.0215804708346 Å** through `lambda_bary / (1 + BERV / 299792.458)`. The exact scientific center is retained; the displayed rounded wavelength does not replace it.

## Exact target-specific inputs

The audit verifies **ten restored inputs** against their historical bytes: all seven HD112410 merged spectra, one discovery ancillary TAR, one native A product and one saved raw NPZ panel. Two whole input archives have matching sizes and SHA-256 hashes: `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` and `SETI_HARPS_RAW_BATCH03_INPUTS_PART1_2026-11-01.zip`. The checks cover selected archive-member hashes, 14 inventory-bound historical sources, the assembled batch03 evidence ZIP, native TAR identity, original raw coordinates, NPZ identity and exact review records. The immutable baseline is `ca7befc1e02fb2ca22ff170214e691e4145d7665`.

The seven merged products independently match both the original target-filtered epoch input checks and every identity/date/MJD/BERV in the C009 metadata handoff. They run from April to August 2025 and have their own BERV span **21.30284860830273 km/s**. No HD106515A product set, reference date, numeric anchor or BERV span is transferred. The original observation timestamps and raw identifiers retain their zero or one millisecond offsets; publication identifiers remain distinct from observation dates.

## Fresh header-only coverage

A fresh scan of **all 72 native order wavelength polynomials** confirms that only **order 1** covers the original event. No covering order is structurally excluded. Its topocentric-air endpoints are **[3803.1337172151, 3845.8145628369703] Å**, derived independently from the header polynomial. Every order's positive wavelength derivative and event-coverage membership agree with the fresh inventory.

| Native order | Frame | ±3 Å grid / 601 | Core / 51 | Negative flank / 151 | Positive flank / 151 |
|---|---|---:|---:|---:|---:|
| 1 | Barycentric | 601 | 51 | 151 | 151 |
| 1 | Topocentric | 601 | 51 | 151 | 151 |

These counts describe geometric support for the fixed 0.01 Å grid, original ±0.25 Å core and 1.5–3 Å reference intervals. Finite flux, actual source gaps and usable numerical normalization remain unassessed. Header coverage does not establish positive reference levels or calibrated uncertainties.

## Historical mapping limits and U / U / U custody

| Historical stage | Preserved result |
|---|---|
| Global grid usable | true |
| Original local mapping usable | false |
| Original baseline verified | false |
| Later five-window reference supported | true |

The later supported reference window does not repair the original local/baseline registration limitations. Original native-pixel, raw-row and raw-column identities and the unchanged orientation are verified; no new registration or wavelength solution is performed. The broader native profile cannot retroactively validate an earlier raw-detector mapping.

**Primary U, secondary U and root-adopted U remain exact.** The primary described a broad native bump and diffuse trace-confined enhancement. The secondary retained a broad trace-confined feature across several dispersion pixels and the original baseline limitation. Root provisionally adopted their agreement. The audit verifies the full original records, current U, original queue route and unconfirmed-origin field. It performs no new classification or physical-origin assessment.

## Dependence and limits

The new bounded wavelength window [3820.0649999999996, 3826.0649999999996] Å is disjoint from the exact nine completed C001–C009 windows. Those nine method plans remain unchanged and hash-bound alongside the C009 handoff, original queue and current disposition. The target and cohort differ from the preceding HD106515A contexts, but original epoch/profile and raw evidence for 0086 and these seven HD112410 observations already existed. Distinct target or wavelength coverage does not establish untouched data, blind analysis, new observing time or independent new observations.

Order 1 and its saved panel belong to one discovery exposure. The two coordinate frames are two contexts of that same exposure. Native `BUNIT` is absent, so extracted units remain unspecified and no calibrated ADU equivalence to merged flux is asserted. Merged ERR columns are declared unavailable; no positive uncertainty support is inferred.

FITS data areas are skipped by byte offsets. NPZ arrays are inspected only through NPY shape/type headers. Whole archives and selected members are hashed as opaque bytes for custody checks. No full raw detector product is restored, no spectral flux or image array is decoded, no network request is made by the audit and no historical file is edited.

Frozen bindings:

- Input inventory SHA-256: `2eb4667377305f5d668c9a39ee3892b4ac62b1a38c77606924ac112083504329`.
- Restore helper SHA-256: `31aa25cd1052252370c36953a684fc7dccb0f09ff4cb70ba91ea1f35c334a201`.
- Audit helper SHA-256: `cb4fb8beedf8340b8daefe3844083e6a7d4960cb37c4bf9bfef717672ff278f6`.
- PASS receipt SHA-256: `d1d47d946332e02b72bfbe722f811937baadc6261af0f85b575fb526b4031d93`.

From the repository root, reproduce in a separate checkout with:

```sh
python work_harps_20261103_c010_context/input_audit/audit_inputs.py \
  --archive-dir /path/to/archive/cache
```

`--archive-dir` can be repeated; each exact archive filename must resolve once within the provided directories. The default cache is `c010_archive_cache` beside the repository. Rerunning creates a new timestamped receipt; preserve this checkpoint's exact bytes after the public method freeze.
