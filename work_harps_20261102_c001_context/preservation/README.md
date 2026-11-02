# Preservation and reproduction

This phase uses existing archived HD103991 inputs. The original source archives remain unchanged; no additional source archive, duplicate package, or upload is needed. Paths below are relative to this phase unless stated otherwise.

## Compact arithmetic evidence

The authorized run completed at 2026-11-02T14:06:17.554752 UTC with status `COMPLETE_FIXED_GROUP_CONTEXT`. It preserved ten bounded pre-interpolation input windows (six merged spectra and four discovery native orders), twenty frame-profile NPZ files, and exact copies of all four existing native/raw-panel NPZ files. The bounded input windows retain source indices, original-frame and barycentric wavelengths, signed source flux, and available ERR samples. The accompanying index binds recorded BERV, source hashes, full-source median wavelength spacing, and the selected bounds. These compact inputs and the fixed plan suffice for independent arithmetic; the full FITS products are needed to verify their extraction provenance.

Use `allow_pickle=False` for NPZ files. Preserve missing coverage, signed flux, NaN errors, explicit blocked slots, and raw-only normalization outcomes. Saved raw panels are historical context; reproducing the phase does not fit new detector mapping, backgrounds, or spatial templates.

| Saved file set | Files | Total bytes | Exact filenames and individual hashes |
|---|---:|---:|---|
| `analysis/results/bounded_inputs/merged_*.npz` and `native_*.npz` | 10 | 82,441 | [BOUNDED_INPUT_INDEX.json](../analysis/results/BOUNDED_INPUT_INDEX.json) |
| `analysis/results/profiles/*.npz` | 20 | 251,178 | [PROFILE_METRICS.json](../analysis/results/PROFILE_METRICS.json) |
| `analysis/results/bounded_inputs/V2E2-*.npz` | 4 | 21,557 | [PRESERVED_RAW_CONTEXT.json](../analysis/results/PRESERVED_RAW_CONTEXT.json) |

All 43 files listed in [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json) were rehashed successfully when this document was finalized. The three indexes also independently matched every listed NPZ hash; preserved raw copies matched their original input hashes. This was a byte-integrity check, without array interpretation or new measurements.

| Binding file | SHA256 |
|---|---|
| `analysis/results/OUTPUT_HASHES.json` | `35969a2c7a6db7231d7c6eb55a7ecec12fcae2bb4008c327d51a1bd1166cfada` |
| `analysis/results/BOUNDED_INPUT_INDEX.json` | `a3cb7a1b63ebb5d7fb6ffaeca42644073d876a89161d502732261ac4029b40d8` |
| `analysis/results/PROFILE_METRICS.json` | `a84b3371847fe00a3a00f9a4e7114502eba6a8242b11cc476964c472d2069c23` |
| `analysis/results/PRESERVED_RAW_CONTEXT.json` | `b9b5800ee68a0bbb7e137c5e31893c61c267a766615dc46a1c375b388784577d` |

All twenty profile slots and sixty-four comparison slots remain recorded. Four native-order3 frame slots retain raw-only normalization; no source-profile slot was blocked. These statuses are preserved results, not reasons to change the fixed windows or repeat the phase.

## Full-source restoration

`inputs/INPUT_INVENTORY.json` supplies the exact archive, member, and fourteen restored-file hashes. Existing archive receipts and restoration instructions are retained at these repository paths:

| Exact source archive | Existing instructions / receipt |
|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | [Extension02 checkpoint](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md) and [receipt registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_EXTENSION02_RAW_INPUTS_PART2_2026-11-01.zip` | [Original raw checkpoint](../../work_harps_20261101/v2/extension02/raw_followup/checkpoints/RESTORE.md) |
| `SETI_HARPS_RAW_BATCH02_INPUTS_PART1_2026-11-01.zip` | [Saved batch02 inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/SAVED_INPUTS.md) and [receipt registry](../../work_harps_20261101/v2/extension02/raw_followup_batch02/checkpoints/LIBRARY_INPUTS.json) |

In a separate reproduction copy of the repository, run:

```sh
python3 work_harps_20261102_c001_context/inputs/restore_inputs.py \
  --archive-dir /path/to/first/archive/cache \
  --archive-dir /path/to/second/archive/cache
```

This byte-only helper validates each whole archive and selected member, restores all six merged FITS, both ancillary TARs, both full native-A FITS, and four exact saved cutouts, and regenerates deterministic inventory/receipt metadata. Local archive paths are not embedded in the generated metadata. Existing identical files are retained; differing destinations cause a failure. Full original raw images remain preserved in the archives and are not required for this phase's broader-profile arithmetic.

## Preserve the one-shot record

Keep the published plan, source metadata, release, and completed outputs unchanged. Full reproduction belongs in a separate checkout with this phase's `analysis/results/` omitted before the first run. After exact restoration, use `analysis/compare_group.py` followed by `analysis/plot_group.py` as documented in [the analysis instructions](../analysis/README.md). The runner verifies its source hashes and release and refuses an existing results directory. Do not reset that guard or replace the authoritative outputs. Compare scientific arrays and numerical records; timestamp-bearing receipts can differ in a reproduction.

Both U labels and all previous survey, epoch, mapping, and extraction results remain unchanged. Reproduction checks one fixed contextual analysis, not a new observation, classifier, or independent detection.
