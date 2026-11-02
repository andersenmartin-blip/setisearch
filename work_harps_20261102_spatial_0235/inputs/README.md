# Exact archived inputs for the V2E2-0235 spatial diagnostic

The discovery inputs were restored from existing, hash-verified archives. This inventory reads FITS and NPY headers only; it does not interpret raw pixels, native flux, previous reference profiles, or other science-array values. No ESO or other network request was made. The previous products, mapping, classifications, and evidence remain unchanged.

The identities are discovery `ADP.2023-02-23T01:01:36.791`, raw `HARPS.2023-02-22T07:40:53.531`, and ancillary `ADP.2023-02-23T01:01:36.792`, all from the original raw-follow-up batch03. The actual observation is 2023-02-22T07:40:53.531 UTC; the ADP identifiers carry the later publication date.

`INPUT_INVENTORY.json` records the exact paths, sizes, SHA256 hashes, original archive membership, and historical source hashes. `RESTORE_RECEIPT.json` reports seven verified files: two original archived products, two exact committed evidence members, the native A and B FITS members extracted from the ancillary TAR, and the decompressed raw FITS. Byte restoration and hashing necessarily process the stored bytes; no numerical array interpretation occurs.

The saved native NPZ contains a raw cutout of shape 31×33, covering zero-based raw rows `[3124,3155)` and columns `[2308,2341)`. It does not cover the planned flank rows. The full raw FITS has two image HDUs, each 4096×2148. The inherited mosaic is `hstack([HDU1[:,50:2098], HDU2[:,50:2098]])`, giving 4096×4096 without a transpose or rotation. It therefore supplies the requested raw row span `[2859,3420)` and flank union `[2859,3059) ∪ [3220,3420)`.

`TRACE_METADATA.json` preserves the existing order50/native-pixel956 registration at raw row3139 and column2323.7701943175816, with `row_flip=true`, `argument_flip=true`, and `column_flip=false`. Those conventions make the trace-polynomial argument equal to the raw row. The file includes every primary-header degree4 trace polynomial: 72 fiber-A orders and 71 fiber-B orders, with their exact native-member paths and hashes. A and B integer order indices are not interchangeable. These header-derived polynomials describe geometric centers; their separation does not itself establish the absence of trace wings or contamination. The new spatial analysis must use its separately frozen protocol before reading pixel values.

The original input archive is `SETI_HARPS_RAW_BATCH03_INPUTS_PART8_2026-11-01.zip`, 99,302,855 bytes, SHA256 `f950ce0c99069c87f792f084237e5971dfba6b9480231cfbc34af2d5b2aa6096`. Its persistent receipt is recorded in `work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json`. The exact evidence ZIP is reconstructed and checked from committed batch03 `EVIDENCE_PARTS.json` and `EVIDENCE_ARCHIVE.json`; only this event's native NPZ and discovery reference JSON are copied. The reference JSON is restored as opaque bytes, not interpreted here.

To reproduce the inventory from the existing archive, run from the repository root:

```sh
python3 work_harps_20261102_spatial_0235/inputs/restore_inputs.py \
  --input-archive /path/to/SETI_HARPS_RAW_BATCH03_INPUTS_PART8_2026-11-01.zip
```

The tool validates the complete archive and each selected member before use. Existing restored byte files must already be identical; it never replaces differing files. Restored FITS/TAR products are ignored by Git because their exact persistent source archive is already preserved. The inventory, trace metadata, receipt, and restoration code provide the reproducible input contract.
