# C008 preservation and reproduction

The fixed C008 run completed at **2026-11-02T20:27:35.448903+00:00**, with status `COMPLETE_FIXED_GROUP_CONTEXT`. It retains eight bounded source windows, sixteen profiles in two fixed frames and the exact historical order-43 raw panel: **25 NPZ files totaling 282,389 bytes**.

| Saved evidence | Files | Total bytes | Exact filenames and SHA256 bindings |
|---|---:|---:|---|
| Seven merged and one native-order source window before interpolation | 8 | 61,886 | [BOUNDED_INPUT_INDEX.json](../analysis/results/BOUNDED_INPUT_INDEX.json) |
| Fourteen merged and two native frame profiles | 16 | 211,864 | [PROFILE_METRICS.json](../analysis/results/PROFILE_METRICS.json) |
| Original V2E2-0047 order-43 raw panel | 1 | 8,639 | [PRESERVED_RAW_CONTEXT.json](../analysis/results/PRESERVED_RAW_CONTEXT.json) |

All **35 files** bound by [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json) were rehashed successfully while finalizing this document. All 25 NPZ files match their separate index hashes, and the raw copy matches the original input hash exactly. These are byte-integrity checks without additional measurements. Later figures and reports are outside this numerical-ledger count.

| Binding file | SHA256 |
|---|---|
| `analysis/results/OUTPUT_HASHES.json` | `f7ddae1a488fb495bd577bcab6f617c12f66c39eaab2079e562694f1cea704ba` |
| `analysis/results/BOUNDED_INPUT_INDEX.json` | `741ebd65b2fd716e3261839283a5a55b1813a2664d4f3e8df15bb52dbc565468` |
| `analysis/results/PROFILE_METRICS.json` | `e4fe9912bff57912855e023b1a9f50d7a6ee243c803f2fb205762c3c556063e1` |
| `analysis/results/PRESERVED_RAW_CONTEXT.json` | `1ef17f398b438b186458cf5b699dc1fe5e991eb06e32e35d563d2e7c3d4e2b60` |

All sixteen profiles and **32 comparison slots** remain, including **four identical-product self comparisons**. All sixteen profiles retain 601 finite raw and normalized grid values with valid positive fixed-flank references and false low-reference flags; there are no raw-only or blocked source slots. All source-window nonpositive fractions are zero. Positive finite ERR support is absent in every profile. Valid scaling and positive samples do not provide a calibrated uncertainty, significance or physical-origin test.

Compact arrays preserve signed flux, original source indices and coordinates, fixed-frame conversion information, available ERR samples, support and normalization status. Load NPZs with `allow_pickle=False` and retain unavailable-error values and status information. Original full FITS remain necessary for extraction-provenance checks. Native extracted units remain unspecified because `BUNIT` is absent; merged ADU and native scales are not a calibrated physical flux ratio.

C008's fixed [5179.005, 5185.005] Å window is disjoint from the completed C001–C007 bounded contexts. Nevertheless, the original epoch/profile and raw evidence already exist and all seven observing products are reused. Reproduction therefore adds neither blind validation nor independent observing time or detections. Fixed reference medians remain descriptive levels, not established line-free continua. The U label remains unchanged.

The sole native covering order is 43, freshly determined from all 72 order headers. Its full context, core and both reference intervals are covered in both frames. Historical global, original local, original baseline and later five-window mapping gates are all true and retained distinctly. These are preserved historical diagnostics; no new detector registration or origin validation was performed.

## Method and release

All **25 prospective files** were published at commit [`d194c32c3679cebb485f901ceccd1ac4786d66f6`](https://github.com/andersenmartin-blip/setisearch/commit/d194c32c3679cebb485f901ceccd1ac4786d66f6) and read back exactly before execution. The [publication receipt](../PROSPECTIVE_PUBLICATION_RECEIPT.json) binds both public branch heads, file identities and **266,131 verified bytes**. Receipt SHA256: `4f6cdb31fd6784d62280a1c476719fe55266459b6ebe08f293dbcf3ac52f47fb`.

The unchanged [plan](../analysis/PLAN.json) has SHA256 `22824f0319684b6c27022023946f2806cdd00d4604dc74493f8b7f074e2bf31f`; the [root release](../analysis/ROOT_RELEASE.json), issued at **2026-11-02T20:27:08.984523+00:00**, has SHA256 `c01bb2e63f954205d3fef08600de65ca66d1600dd979aef6874d8c8457b43c5d`. All **45 plan-bound source hashes** remain exact. The comparison uses the sole C008 discovery observed on **2023-03-22**, BERV **3.26509772194068 km/s**, with fixed topocentric anchor **5181.9485623946 Å**. Earlier January, March 2022 and May 2022 anchors are not transferred. The runner checks release/source bindings and rejects an existing output directory. The [preflight freeze](../PREFLIGHT_FREEZE.json) and pre-array audit records remain unchanged.

The [independent numerical reconstruction](../independent_audit/NUMERICAL_AUDIT.json) passed **424 checks across 63,374 scalar values**, including all profiles, comparisons, source windows, the raw copy and self-pairs, without importing production functions. It verifies arithmetic and lineage, not a physical-origin conclusion or independent observing evidence.

## Exact archived input restoration

The [input inventory](../inputs/INPUT_INVENTORY.json), SHA256 `80cce49d1000211f735449d65efc27b447de85bdd9e5ba9fbbbfac924e21f890`, binds **10 restored files**: seven merged FITS, one ancillary TAR, one native-A FITS and one historical raw-context NPZ. No extra acquisition or duplicate source-archive package is required. The [input instructions](../inputs/README.md) retain archive/member hashes, fresh 72-order header coverage, original review records, units and exact discovery identities.

| Existing archive | Restored here | Original instructions and receipts |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH02_INPUTS_PART3_2026-11-01.zip` | March 2023 discovery ancillary product | [Saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/LIBRARY_INPUTS.json) |

The historical raw-context NPZ is restored from unchanged committed batch02 evidence parts. Full raw detector products remain in the existing archive and are not required for the broader-profile arithmetic.

In a separate reproduction checkout:

```sh
python3 work_harps_20261102_c008_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

One cache may hold both named archives. The helper verifies complete archives and member hashes, rejects differing destinations, retains identical files and writes deterministic metadata. It inspects FITS/NPY headers without executing the comparison. Local cache paths do not enter the metadata. Full restored inputs and temporary input-panel copies are excluded from Git; compact evidence is preserved with the completed analysis.

## Preserve the completed record

Reproduce only in a separate checkout with this phase's `analysis/results/` absent before its first run. Preserve the published inputs, method, code and root release, following the [analysis instructions](../analysis/README.md). Do not reset the authoritative one-shot guard or overwrite completed outputs. Reproduction timestamps can differ; compare scientific arrays and numerical records.

All original U dispositions, survey counts and prior analyses remain unchanged. Reproduction of this fixed context does not authorize favorable reference selection, shifted windows, extra fitted parameters or an independent-detection claim.
