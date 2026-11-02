# Preservation and reproduction

The completed V2E2-0235 diagnostic is preserved by its compact public outputs and the existing immutable batch03 source archive. No additional archive or upload is needed. All paths below are relative to this phase unless stated otherwise.

## Compact arithmetic record

Both NPZ files were rehashed against `analysis/results/OUTPUT_HASHES.json` when this document was prepared.

| File | Bytes | SHA256 |
|---|---:|---|
| `analysis/results/SELECTED_NATIVE_PIXELS.npz` | 19,208 | `ccbd63ed7bb47295abebaf0229c9d51808131c82ad7d4d1cee21dfc689c8e5b2` |
| `analysis/results/SPATIAL_ARRAYS.npz` | 187,167 | `43e3572ed46c5e44a57b374762d0033297be68beb3b432ec6cd2cc9ba1b11c5a` |

`SELECTED_NATIVE_PIXELS.npz` contains the exact 331×25 native raw-ADU samples, absolute/relative raw rows, stitched/chip2 columns, inherited trace centers, training rows, and control centers. Together with `analysis/PLAN.json`, those values suffice to independently reconstruct the fixed background, all three templates, the 27 target/control fits, and their descriptive statistics. `SPATIAL_ARRAYS.npz` also retains the raw/model/residual maps, exact offsets, and fit masks for comparison. Use `allow_pickle=False` when opening either archive. The scalar methods in `independent_audit/independent_math.py` provide an independent arithmetic implementation.

The saved pixels alone do not prove extraction from the original FITS. That provenance check uses the full restored raw source. The completed `independent_audit/NUMERICAL_AUDIT.json` records an independent direct-byte decode of the same 8,275 pixels and their exact agreement with the saved values. No additional overlap or science calculation was added for preservation.

## Exact full-source restoration

The existing source is [SETI_HARPS_RAW_BATCH03_INPUTS_PART8_2026-11-01.zip](https://chatgpt.com/library?file_id=libfile_31072572b7988191abdbff50a9d960c1&account_id=personal): 99,302,855 bytes, SHA256 `f950ce0c99069c87f792f084237e5971dfba6b9480231cfbc34af2d5b2aa6096`. Its original receipt is in repository path `work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json`.

Run the existing restoration tool from a separate restoration copy of the repository:

```sh
python3 work_harps_20261102_spatial_0235/inputs/restore_inputs.py \
  --input-archive /path/to/SETI_HARPS_RAW_BATCH03_INPUTS_PART8_2026-11-01.zip
```

It verifies the archive and selected raw/ancillary members, restores the two exact committed evidence members, extracts native A/B FITS, and decompresses the raw FITS. It reads FITS/NPY headers only. All seven file paths and expected hashes are in the published `inputs/INPUT_INVENTORY.json`; the full decompressed raw is 35,265,600 bytes with SHA256 `52fe1d9a69c102188d0e2b75490f9f933b3906e47b8fca3a2b89622c6851797f`.

The restoration tool also regenerates inventory metadata, including the local archive path. A different local archive path can therefore change the regenerated inventory's bytes. For guarded reproduction, copy only the seven verified restored byte files to their identical relative paths in a fresh reproduction checkout; retain that checkout's published inventory, source metadata, plan, scripts, and release unchanged. The published inventory SHA256 is `d3c9b750ac8221e12c841625efc7c53c6964ad0d44413afee0c92a5ba720a5c7`.

## One-shot reproduction

Before running the guarded analysis in that reproduction copy, restore its historical profile-cache prerequisites. `analysis/PLAN.json` also binds twelve May-quality result NPZ files and twenty-four BERV-follow-up result NPZ files in `source_hashes`; these are preserved through archives and are not all directly tracked files. Follow the [existing restoration instructions](../../CONTINUE_SETI.md) and [May-quality preservation instructions](../../work_harps_20261102_may_quality/README.md). The specific byte-only helpers, run from the repository root, are:

```sh
python3 work_harps_20261102_may_quality/preservation/restore_archive.py PROFILE_EVIDENCE_MANIFEST.json
python3 work_harps_20261102_berv_followup/prospective_comparison/restore_profile_evidence.py
```

The first restores all twelve May-quality result profiles; the second restores all twenty-four BERV result profiles and twenty discovery references. They verify archived member hashes and preserve differing existing files. Keep the published manifests, inventories, release, and other source metadata unchanged; restoration is not a rerun of either completed comparison.

Preserve the authoritative completed results. Use a separate checkout with `analysis/results/` omitted from that reproduction copy before its first run. The released `analysis/measure_spatial.py` checks the exact plan, inventory, historical sources, and full raw hash, then refuses an existing results directory. Run it and `analysis/plot_spatial.py` as documented in `analysis/README.md`; the existing release must remain intact. Do not reset its guard or rerun into the original output directory. Timestamp-bearing receipts can differ in a reproduction; compare scientific arrays and numerical records against the preserved outputs.

This preserves one completed descriptive spatial diagnostic, not a new observation or classifier. The original U label, historical extraction, and all previous phases remain unchanged.
