# Exact original inputs for the normalization diagnostic

Nine original inputs are listed with source archive identity, exact path, size and SHA-256 in [SOURCE_PRODUCTS.json](SOURCE_PRODUCTS.json). They are three merged science FITS files, three original raw FITS.Z files and three matching ancillary TAR files. No replacement observations are allowed.

They are contained in four already-saved input archives:

| Archive | Saved file |
|---|---|
| SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip | [Science spectra](https://chatgpt.com/library?file_id=libfile_0819807a43f881919930e00badffe670&account_id=personal) |
| SETI_HARPS_EXTENSION02_RAW_INPUTS_PART1_2026-11-01.zip | [Initial raw/ancillary inputs](https://chatgpt.com/library?file_id=libfile_a7ac21977ef48191ae7b303b49141fd4&account_id=personal) |
| SETI_HARPS_RAW_BATCH03_INPUTS_PART2_2026-11-01.zip | [Batch03 part2](https://chatgpt.com/library?file_id=libfile_767674a55080819192d15d8ef0afd865&account_id=personal) |
| SETI_HARPS_RAW_BATCH03_INPUTS_PART3_2026-11-01.zip | [Batch03 part3](https://chatgpt.com/library?file_id=libfile_004f09ffe59081919e6772284be35ab9&account_id=personal) |

[Archive restoration evidence](ARCHIVE_RESTORATION.json) records their verified byte lengths and SHA-256 values. Put the verified archives in a staging directory. In a separate reproduction copy, run:

```bash
python3 restore_sources.py --archives /absolute/path/to/verified-archives
python3 restore_evidence.py
```

The selector extracts only the exact nine frozen members, verifies hashes and lengths and retains identical copies; it refuses different existing data. It does not restore archive metadata over current records. Local working paths in receipts are historical context; source identities and hashes are authoritative. The newly packaged evidence stores 28 original selected profiles and 20 derived arrays; it does not duplicate the larger source products.
