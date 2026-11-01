# Raw batch03 saved inputs

**Eight saved packages preserve all 64 canonical ESO products: 32 RAW files and 32 ancillary TAR files from 32 complete exposure pairs.** The packages add no observing time. All eight save receipts succeeded and their local Library identity metadata was applied.

The exact archive lengths, SHA-256 values, product/member hashes and Library/file identities are recorded in [LIBRARY_INPUTS.json](LIBRARY_INPUTS.json). The original packaging manifest is [INPUT_ARCHIVES.json](INPUT_ARCHIVES.json).

- [SETI_HARPS_RAW_BATCH03_INPUTS_PART1_2026-11-01.zip](https://chatgpt.com/library?file_id=libfile_6ac765bba6288191836d02da5fc89ce8&account_id=personal) — 99,022,819 bytes; 4 exposure pairs.
- [SETI_HARPS_RAW_BATCH03_INPUTS_PART2_2026-11-01.zip](https://chatgpt.com/library?file_id=libfile_767674a55080819192d15d8ef0afd865&account_id=personal) — 96,845,730 bytes; 4 exposure pairs.
- [SETI_HARPS_RAW_BATCH03_INPUTS_PART3_2026-11-01.zip](https://chatgpt.com/library?file_id=libfile_004f09ffe59081919e6772284be35ab9&account_id=personal) — 97,097,418 bytes; 4 exposure pairs.
- [SETI_HARPS_RAW_BATCH03_INPUTS_PART4_2026-11-01.zip](https://chatgpt.com/library?file_id=libfile_1580a5695e5c8191b6334dcc68bed002&account_id=personal) — 99,764,162 bytes; 4 exposure pairs.
- [SETI_HARPS_RAW_BATCH03_INPUTS_PART5_2026-11-01.zip](https://chatgpt.com/library?file_id=libfile_3207042a5154819181c61b46704fcf7e&account_id=personal) — 97,007,130 bytes; 4 exposure pairs.
- [SETI_HARPS_RAW_BATCH03_INPUTS_PART6_2026-11-01.zip](https://chatgpt.com/library?file_id=libfile_0bff369426c08191b55f9a92fae09946&account_id=personal) — 95,450,562 bytes; 4 exposure pairs.
- [SETI_HARPS_RAW_BATCH03_INPUTS_PART7_2026-11-01.zip](https://chatgpt.com/library?file_id=libfile_8b3a8356363481918f8af859e300ada8&account_id=personal) — 95,292,740 bytes; 4 exposure pairs.
- [SETI_HARPS_RAW_BATCH03_INPUTS_PART8_2026-11-01.zip](https://chatgpt.com/library?file_id=libfile_31072572b7988191abdbff50a9d960c1&account_id=personal) — 99,302,855 bytes; 4 exposure pairs.

## Restore without changing current results

1. Download all eight packages and verify each archive size and SHA-256 against `LIBRARY_INPUTS.json`.
2. Extract into a separate staging directory. Archive members beginning `v2/extension02/` are relative to `work_harps_20261101/`; do not add another project-root prefix.
3. Verify all 64 canonical product hashes and lengths against the checkpoint product entries and `products/MANIFEST.json`. Copy only verified payloads and matching receipts into the expected `raw_followup_batch03/products/` paths.
4. Preserve the current GitHub plans, status tables, adopted decisions and publication receipts. Metadata copies inside these input archives record the acquisition checkpoint and must not replace later results.

Residual `.part` files are excluded from the packages and are never valid analysis inputs. The 100 source 1D spectra remain in the earlier extension02 input packages. Derived cutouts/reference grids are restored independently from this batch’s GitHub evidence archive; see [the batch README](../README.md).

Total saved archive bytes: **779,783,416**. No selected exposure pair was omitted or replaced.
