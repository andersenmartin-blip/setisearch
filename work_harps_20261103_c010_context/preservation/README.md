# C010 / HD112410 preservation and reproduction

The fixed C010 run completed at **2026-11-03T08:58:03.639309+00:00**, with status `COMPLETE_FIXED_GROUP_CONTEXT`. It preserves eight bounded source windows, sixteen profiles in two fixed frames and the exact historical order-1 raw panel: **25 NPZ files totaling 292,148 bytes**.

| Saved evidence | Files | Total bytes | Exact filenames and SHA256 bindings |
|---|---:|---:|---|
| Seven HD112410 merged and one native-order source window before interpolation | 8 | 64,594 | [BOUNDED_INPUT_INDEX.json](../analysis/results/BOUNDED_INPUT_INDEX.json) |
| Fourteen merged and two native frame profiles | 16 | 220,548 | [PROFILE_METRICS.json](../analysis/results/PROFILE_METRICS.json) |
| Original V2E2-0086 order-1 raw panel | 1 | 7,006 | [PRESERVED_RAW_CONTEXT.json](../analysis/results/PRESERVED_RAW_CONTEXT.json) |

All **35 numerical files** in [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json) were rehashed while finalizing this document. All 25 NPZ files also match their separate index bindings, and the raw copy matches the original input bytes and hash exactly. These checks preserve byte integrity without adding measurements. Figures and reports created later are outside the numerical-ledger count.

| Binding file | SHA256 |
|---|---|
| `analysis/results/OUTPUT_HASHES.json` | `6e775f7454e5164c7045781bd9811348c615b7be90695c47b08271de7b47b035` |
| `analysis/results/BOUNDED_INPUT_INDEX.json` | `1f03cb2e2af84c3380fa37854bbc885c436b7663cea44766f0ea128393d35c33` |
| `analysis/results/PROFILE_METRICS.json` | `60d284da438a2aecc33b9ad54c9edde6411d6c161db88a6ac464b829c6f2ca46` |
| `analysis/results/PRESERVED_RAW_CONTEXT.json` | `5e05e28582383babb541a016594ad899500b86ae2ab0828311a238be805b78b2` |

## Signed values and complete support

All **16 profiles and 32 comparison slots** remain, including **four labelled identical-product self comparisons**. Every profile has 601 finite raw and normalized grid values, a valid positive fixed-flank reference and a false low-reference flag; no source is raw-only, blocked or structurally excluded. Positive finite ERR support is absent in every profile.

**A positive reference does not mean all source samples are positive.** Every profile retains nonpositive signed source values. Each merged frame window contains 600 finite original samples, with 2–21 nonpositive samples (0.3333%–3.5%) across the fourteen merged profile rows. Those rows are two frame views of seven observations. Both native frame windows contain 3 nonpositive samples among 562 finite originals (0.5338%). The native left flank contains 3/139 nonpositive samples and its right flank 0/143. The full merged flank counts and fractions, which can differ between frames, remain in the complete metrics. Original-sample counts are distinct from the 601-point interpolated grid support. All signs and unavailable errors are preserved without clipping or sign changes.

Compact NPZs retain the signed flux, original source indices and coordinates, fixed-frame conversion information, available ERR samples, support and normalization status. Load arrays with `allow_pickle=False`. Valid scaling, false low-reference flags and full support do not provide calibrated uncertainty, significance, sensitivity or a physical-origin test. Native BUNIT is absent, so native extracted units remain unspecified; merged ADU and native scales are not a calibrated physical flux ratio. Original full FITS are required for extraction-provenance checks.

## Target, geometry and historical evidence

**The target and cohort change to HD112410.** Its seven existing observations run from April to August 2025 and span 21.30284860830273 km/s in BERV. The original center remains exactly **3823.0649999999996 Å**, with the original ±0.25 Å core and ±3 Å context. This window is disjoint from completed C001–C009 bounded contexts, but original epoch/profile and raw evidence for 0086 already existed. Reusing these products adds no observing time, blind validation or independent detections. No HD106515A product or numeric anchor is transferred. Fixed reference-flank medians remain descriptive levels rather than established line-free continua.

The fresh scan of all 72 order headers selects order 1 alone, covering the complete context, core and both fixed flanks in both frames. Historical order 1 global-grid and later five-window mapping diagnostics are true, while the original local-usable and baseline-verified diagnostics remain **false**. Header geometry and later support do not repair those original raw-registration limits. All primary, secondary and root-adopted reviews remain **U** for broad diffuse trace-confined structure without an unambiguous compact charge deposit. The original panel, subtraction, review text and stages remain intact; no new registration, physical-origin assignment or classification is implied.

## Public method and release

All **25 prospective files** were published at commit [`acb3a382b43ca0b9d3d13f3e30317383f591fb10`](https://github.com/andersenmartin-blip/setisearch/commit/acb3a382b43ca0b9d3d13f3e30317383f591fb10) and read back exactly before execution. The [publication receipt](../PROSPECTIVE_PUBLICATION_RECEIPT.json) records both public branches and **290,904 verified bytes**. Receipt SHA256: `788d866b762f910efb549a208b917e9fc8172b368fb5eb86451773f4068d3c03`.

The unchanged [plan](../analysis/PLAN.json) has SHA256 `a17103d238df587dfdf45d61d3b6500971dc6e8066f0e6b738bde4720c5b04e9`. The [root release](../analysis/ROOT_RELEASE.json), issued at **2026-11-03T08:57:45.510815+00:00**, has SHA256 `8136b29e1c070e9e3e3a4a4eda031e4de5384c077ade935603e2e490a0c1a124`. All **47 plan-bound source hashes**, all **24 files bound by the root freeze**, and all 25 exact public-method file identities remain unchanged. The [preflight freeze](../PREFLIGHT_FREEZE.json) and prospective reviews preserve the pre-array contract.

The sole reference was observed on **2025-04-29**, with BERV **3.40485846065643 km/s**, defining the wavelength-specific topocentric anchor **3823.0215804708346 Å**. The runner validates release and source hashes, performs the fixed comparison once and rejects an existing results directory. Preserve that guard and all completed outputs.

The [independent reconstruction](../independent_audit/NUMERICAL_AUDIT.json) passed **432 checks across 63,469 scalar values**, covering all profiles, comparisons, bounded windows, the raw copy and self pairs without importing production functions. Computational reconstruction does not supply independent observations or a physical-origin conclusion.

## Recover exact archived inputs

The [input inventory](../inputs/INPUT_INVENTORY.json), SHA256 `2eb4667377305f5d668c9a39ee3892b4ac62b1a38c77606924ac112083504329`, binds **10 restored files**: seven target-specific merged FITS, one discovery ancillary TAR, one native-A FITS and one historical raw-context NPZ. Both whole archives were recovered from the preserved source files after transient workspace maintenance and verified against their original complete sizes and hashes. No live telescope/archive query or duplicate archive package was needed.

| Existing archive | Restored here | Original instructions and receipts |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven HD112410 merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART1_2026-11-01.zip` | April 2025 discovery ancillary product | [Saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json) |

The original 0086 raw-context NPZ is reconstructed from unchanged committed batch03 evidence parts. Full raw detector products remain in the existing saved archive and are not extracted for this profile arithmetic. The [input instructions](../inputs/README.md) retain every archive/member identity, header convention and historical mapping qualification.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c010_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

One cache may hold both named archives. The helper verifies whole archives and selected members, rejects differing destinations, reuses identical files and writes deterministic metadata. It inspects FITS/NPY headers without executing the scientific comparison or making a network request. Local cache paths do not enter the metadata. Full restored inputs and temporary panel copies are excluded from Git; compact result evidence is retained with the analysis.

## Preserve the completed record

Reproduce in a separate checkout with this phase's `analysis/results/` absent before its first run, following the [analysis instructions](../analysis/README.md). Preserve the published input identities, code, method, root release and completed outputs. Do not reset the authoritative one-shot guard. Reproduction timestamps may differ; compare scientific arrays and numerical records.

All original U dispositions, review votes, mapping stages, survey counts and prior analyses remain unchanged. Reproduction of this fixed context does not authorize favorable-reference selection, shifted windows, extra fitted parameters or an independent-detection claim.
