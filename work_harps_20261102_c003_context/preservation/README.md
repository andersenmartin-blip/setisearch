# Preservation and reproduction

This phase reuses existing archived HD106515A inputs. The original source archives remain unchanged; no additional source archive, duplicate package, or upload is needed. Paths below are relative to this phase unless stated otherwise.

## Verified compact evidence

The authorized run completed at 2026-11-02T14:54:08.482665 UTC with status `COMPLETE_FIXED_GROUP_CONTEXT`. It preserved fifteen bounded pre-interpolation input windows (seven merged spectra and eight historically covering discovery orders), thirty frame-profile NPZ files, and exact copies of all eight existing native/raw-panel NPZ files: **53 NPZ files totaling 568,599 bytes**.

| Saved file set | Files | Total bytes | Exact filenames and individual hashes |
|---|---:|---:|---|
| `analysis/results/bounded_inputs/merged_*.npz` and `native_*.npz` | 15 | 138,083 | [BOUNDED_INPUT_INDEX.json](../analysis/results/BOUNDED_INPUT_INDEX.json) |
| `analysis/results/profiles/*.npz` | 30 | 377,583 | [PROFILE_METRICS.json](../analysis/results/PROFILE_METRICS.json) |
| `analysis/results/bounded_inputs/V2E2-*.npz` | 8 | 52,933 | [PRESERVED_RAW_CONTEXT.json](../analysis/results/PRESERVED_RAW_CONTEXT.json) |

All **63 files** listed in the numerical-run [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json) were rehashed successfully when this document was finalized. Each of the 53 indexed NPZs also matched its index hash; all eight raw copies matched the recorded original input hashes. These checks process bytes without interpreting arrays or calculating new scientific measurements. Figures and later report documents are outside this numerical-ledger claim.

| Binding file | SHA256 |
|---|---|
| `analysis/results/OUTPUT_HASHES.json` | `03a8581d24ea3d866f7cdb8e53b5b30fbc4e2da428228f277d6fa92bd0305878` |
| `analysis/results/BOUNDED_INPUT_INDEX.json` | `81a1b08ab85b2f9418504d430638adf7be2724851da1236484d0644b2182da49` |
| `analysis/results/PROFILE_METRICS.json` | `bef88cc3c6aeda068c0c8e87cd4c3a5b533c177bbe731f5b62379247d29fb42b` |
| `analysis/results/PRESERVED_RAW_CONTEXT.json` | `695f905094714142535f39251749e86a8c76fdd913e8acf3ddc5bb52b9f3f665` |

All thirty profile slots and 172 comparison slots remain recorded, including twenty identical-product self comparisons. Six selected order2 frame profiles retain raw-only normalization; no source-profile slot was blocked. These preserved outcomes do not authorize changing the windows or repeating the completed phase.

The compact input windows retain source indices, original-frame and barycentric wavelengths, signed source flux, and available ERR samples. Their index binds recorded BERV, original full-source hashes, median wavelength spacing, and selected bounds. Together with the fixed plan, the saved windows support independent arithmetic. The full FITS products remain necessary to verify extraction provenance. Use `allow_pickle=False` for NPZ files, preserving missing coverage, signed values, unavailable errors, explicit blocked slots, and raw-only normalization outcomes.

The eight copied raw panels are historical context. No order2 panel exists for V2E2-0051 or V2E2-0053, and no panel or profile is fabricated for those structural exclusions. Reproduction does not refit detector mapping, backgrounds, or extraction.

## Exact full-source restoration

`inputs/INPUT_INVENTORY.json` binds all 25 restored files: seven merged FITS, five ancillary TARs, five full native-A FITS, and eight exact saved NPZs. Its SHA256 is `05548c32e4d8a20c16fe0e8549c83365b6dd74bcb38814faafde49a3717d77ca`. All five native products retain a complete two-order metadata inventory, distinguishing eight historical covering combinations from two `NOT_COVERING_LINE` entries.

| Exact existing archive | Content used here | Original instructions / receipts |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven merged spectra | [Checkpoint instructions](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [receipt registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH02_INPUTS_PART2_2026-11-01.zip` | First two discovery ancillary TARs | [Saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/SAVED_INPUTS.md), [receipt registry](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH02_INPUTS_PART3_2026-11-01.zip` | Last three discovery ancillary TARs | Same batch02 instructions and registry |

The inventory supplies exact archive sizes, hashes, and member identities. The eight saved cutouts come from the committed batch02 evidence parts. Full original raw images remain preserved in the existing archives; they are not required for this broader-profile arithmetic.

From a separate reproduction copy of the repository, run:

```sh
python3 work_harps_20261102_c003_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

The helper verifies complete archive and member hashes, restores the specified bytes, and regenerates deterministic inventory/receipt metadata. It does not embed local archive paths in that metadata. Identical existing destinations are retained; differing files cause failure. The helper reads FITS and NPY headers only and does not run the scientific analysis.

## Preserve the one-shot record

Keep the published plan, source metadata, release, and completed outputs unchanged. Full reproduction belongs in a separate checkout with this phase's `analysis/results/` omitted before the first run. After exact restoration, follow [the analysis instructions](../analysis/README.md) to run `analysis/compare_group.py` and `analysis/plot_group.py`. The runner verifies its source hashes and release and refuses an existing results directory. Do not reset that guard or replace authoritative outputs. Compare scientific arrays and numerical records; timestamp-bearing receipts can differ in a reproduction.

All five U labels and previous survey, epoch, mapping, and extraction results remain unchanged. Reproduction checks one fixed group-context analysis, not a new observation, classifier, or independent detection.
