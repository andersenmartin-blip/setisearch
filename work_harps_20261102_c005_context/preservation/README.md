# Preservation and reproduction

This phase uses existing archived HD106515A inputs. The original source archives remain unchanged. No new source upload or duplicate archive package is needed. Paths below are relative to this phase unless stated otherwise.

## Verified compact evidence

The authorized run completed at 2026-11-02T16:33:38.843996 UTC with status `COMPLETE_FIXED_GROUP_CONTEXT`. It preserved seventeen bounded pre-interpolation windows, thirty-four frame-profile NPZ files, and exact copies of all ten existing native/raw panels: **61 NPZ files totaling 707,244 bytes**.

| Saved file set | Files | Total bytes | Exact filenames and individual hashes |
|---|---:|---:|---|
| `analysis/results/bounded_inputs/merged_*.npz` and `native_*.npz` | 17 | 171,762 | [BOUNDED_INPUT_INDEX.json](../analysis/results/BOUNDED_INPUT_INDEX.json) |
| `analysis/results/profiles/*.npz` | 34 | 468,469 | [PROFILE_METRICS.json](../analysis/results/PROFILE_METRICS.json) |
| `analysis/results/bounded_inputs/V2E2-*.npz` | 10 | 67,013 | [PRESERVED_RAW_CONTEXT.json](../analysis/results/PRESERVED_RAW_CONTEXT.json) |

All **71 files** in the numerical-run [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json) were rehashed successfully when this document was finalized. All 61 NPZs also matched their index hashes, and all ten raw copies matched the recorded original input hashes. These are byte-integrity checks, without array interpretation or new measurements. Figures and later reports are outside this numerical-ledger claim.

| Binding file | SHA256 |
|---|---|
| `analysis/results/OUTPUT_HASHES.json` | `ca67c2843bd1fabdd65dbbfcefaa64499e621b024a68a55d7bbd79e508827160` |
| `analysis/results/BOUNDED_INPUT_INDEX.json` | `d598071df6a3b8fff265575d427f754b56c2d62463e27a54fa5dcf10d8e24fb2` |
| `analysis/results/PROFILE_METRICS.json` | `2f77272574692c10d8e1910f9cd56891f92d1acfcdea9c5b9663e24fd97f90d7` |
| `analysis/results/PRESERVED_RAW_CONTEXT.json` | `54df2748b7df1a50c2d869c16bc5ae0f64b6fa2251cb55cbb02b99ae521bdb69` |

All thirty-four profiles and 180 comparison slots are preserved, including twenty identical-product self comparisons. There were no raw-only normalization slots or blocked source profiles. These completed outcomes do not authorize changing the method or repeating the phase.

The compact evidence preserves signed original flux, source coordinates and indices, frame conversion metadata, available ERR samples, coverage and normalization status. Those windows and the fixed plan support independent arithmetic; the original full FITS remain necessary for extraction-provenance checks. Use `allow_pickle=False` when reading NPZ evidence. Preserve signed values, unavailable-error samples and recorded status information. Original raw panels retain their historical caveats without a new detector fit or classification.

## Exact input restoration

`inputs/INPUT_INVENTORY.json` binds all 27 restored files: seven merged FITS, five ancillary TARs, five full native-A FITS, and ten saved NPZs. Its SHA256 is `13154b2d280c5b9df876730184e1d86a935d3a30ea342648f89eb453e0248919`. All ten historical order 3/4 combinations are represented; there are no structurally excluded orders in this group.

| Existing archive | Content used here | Original instructions / receipts |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | All seven merged spectra | [Checkpoint instructions](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [receipt registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH02_INPUTS_PART2_2026-11-01.zip` | First three discovery ancillary TARs | [Saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/SAVED_INPUTS.md), [receipt registry](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH02_INPUTS_PART3_2026-11-01.zip` | Last two discovery ancillary TARs | Same batch02 instructions and registry |

The inventory records exact archive sizes, hashes and member identities. Ten saved cutouts are restored from committed batch02 evidence parts. Full original raw images stay preserved in the existing archives and are not required for broader-profile arithmetic.

In a separate reproduction copy, run from the repository root:

```sh
python3 work_harps_20261102_c005_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

The helper checks whole archives and exact member hashes, writes deterministic inventory/receipt metadata, and refuses differing destinations. It preserves identical files and performs header-only inspection; it does not run the comparison. Local cache paths do not alter the generated metadata.

## Preserve the completed record

Full reproduction belongs in a separate checkout with this phase's `analysis/results/` omitted before its first run. Keep the published input metadata, plan, code and root release unchanged. Follow the phase's analysis instructions after exact restoration; the one-shot runner verifies source and release hashes and refuses existing output directories. Do not reset its guard or overwrite the authoritative run. Timestamp-bearing receipts can differ during reproduction; compare scientific arrays and numerical records.

All five U labels and historical survey, epoch, mapping and extraction results remain unchanged. Reproduction is a check of one fixed context analysis, not a new observation or independent detection.
