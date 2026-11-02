# Raw batch04 saved inputs

**Nine saved packages preserve all 72 acquired canonical ESO products: 36 RAW files and 36 ancillary TAR files from 36 complete exposure pairs.** The selected scope remains 37 exposures; the omitted pair is recorded below and was not replaced. The packages add no observing time. All nine save receipts succeeded and local Library identity metadata was applied.

Exact archive lengths, SHA-256 values, product/member hashes and Library/file identities are in [LIBRARY_INPUTS.json](LIBRARY_INPUTS.json). The original packaging manifest is [INPUT_ARCHIVES.json](INPUT_ARCHIVES.json).

- [SETI_HARPS_RAW_BATCH04_INPUTS_PART1_2026-11-02.zip](https://chatgpt.com/library?file_id=libfile_3a9b06d502d48191bec0ae6b9f1df0a5&account_id=personal) — 99,599,572 bytes; 4 exposure pairs.
- [SETI_HARPS_RAW_BATCH04_INPUTS_PART2_2026-11-02.zip](https://chatgpt.com/library?file_id=libfile_df127c8e938881918cb21eb3d78dbbaf&account_id=personal) — 102,330,682 bytes; 4 exposure pairs.
- [SETI_HARPS_RAW_BATCH04_INPUTS_PART3_2026-11-02.zip](https://chatgpt.com/library?file_id=libfile_1a1606cc15788191803b0640ee27ceee&account_id=personal) — 103,650,621 bytes; 4 exposure pairs.
- [SETI_HARPS_RAW_BATCH04_INPUTS_PART4_2026-11-02.zip](https://chatgpt.com/library?file_id=libfile_aad85a71452c8191b04adbc1208996a3&account_id=personal) — 102,154,939 bytes; 4 exposure pairs.
- [SETI_HARPS_RAW_BATCH04_INPUTS_PART5_2026-11-02.zip](https://chatgpt.com/library?file_id=libfile_eb37fe44d85881919caa486f6949f942&account_id=personal) — 108,960,615 bytes; 4 exposure pairs.
- [SETI_HARPS_RAW_BATCH04_INPUTS_PART6_2026-11-02.zip](https://chatgpt.com/library?file_id=libfile_afff4d625f6c8191b4e2b4f19991d643&account_id=personal) — 103,151,421 bytes; 4 exposure pairs.
- [SETI_HARPS_RAW_BATCH04_INPUTS_PART7_2026-11-02.zip](https://chatgpt.com/library?file_id=libfile_d0f01d227a448191ad5f2da97515ec3f&account_id=personal) — 83,883,553 bytes; 4 exposure pairs.
- [SETI_HARPS_RAW_BATCH04_INPUTS_PART8_2026-11-02.zip](https://chatgpt.com/library?file_id=libfile_9697b4de019c81919a0e83f618925903&account_id=personal) — 72,845,560 bytes; 4 exposure pairs.
- [SETI_HARPS_RAW_BATCH04_INPUTS_PART9_2026-11-02.zip](https://chatgpt.com/library?file_id=libfile_704d32c87a888191ad52ac376e8a6afa&account_id=personal) — 100,306,816 bytes; 4 exposure pairs.

## Preserved acquisition omission

Exposure **ADP.2023-07-07T01:08:58.252**, target **HD141937**, MAIN100 index **99**, was selected but not acquired. Its ancillary product **ADP.2023-07-07T01:08:58.253** failed both allowed metadata HEAD attempts with HTTP 503. The RAW counterpart **HARPS.2023-07-06T04:02:59.524** was consequently not downloaded either; the pair was omitted without replacement. Selected events **V2E2-0332 and V2E2-0333** remain without raw evidence in this checkpoint. The exact selection, original product identities and metadata failures are retained in each ZIP's metadata and in the manifests.

## Restore without changing current results

1. Download all nine packages and verify each archive size and SHA-256 against `LIBRARY_INPUTS.json`.
2. Extract into a separate staging directory. Archive members beginning `v2/extension02/` are relative to `work_harps_20261101/`; do not add another project-root prefix.
3. Verify all 72 canonical product hashes and lengths against the checkpoint product entries and `products/MANIFEST.json`. Copy only verified payloads and matching receipts into the expected `raw_followup_batch04/products/` paths.
4. Preserve current GitHub plans, status tables, adopted decisions and publication receipts. Metadata copies inside these archives record the acquisition checkpoint and must not replace later results.

All noncanonical payload files, including residual `.part` files and hidden transient copies, are excluded and are never valid analysis inputs. The 100 source 1D spectra remain in the earlier extension02 input packages. Derived cutouts/reference grids are restored independently from this batch's GitHub evidence archive; see [the batch README](../README.md).

Total saved archive bytes: **876,883,779**. One selected pair is omitted; no selected exposure or product was replaced.
