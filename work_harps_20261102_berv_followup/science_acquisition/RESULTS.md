# Fixed spectrum acquisition completed

Both preregistered HD122640 FITS products were downloaded successfully on their first attempt. Exactly 10,529,280 bytes were saved across two files. No redirects, substitute products, repeated attempts or broad spectral searches were used. Acquisition did not interpret spectral arrays.

| Observation UTC | Product | Bytes | SHA256 |
|---|---|---:|---|
| 2017-05-22 05:20:05.415 | ADP.2017-05-23T01:01:52.459 | 5,264,640 | `73400a092367c4c0991e94d48263b3c60b7004559b67fc8e032fd2851497cdf8` |
| 2018-01-20 08:50:34.271 | ADP.2018-01-21T01:01:37.761 | 5,264,640 | `ab009a8e47db0d472eb3b4ce1a6a1ee63804526d694435f6410a6aa986a02eb1` |

[The complete manifest](ACQUISITION_MANIFEST.json) binds every request receipt and product hash. The prior [public release](PUBLICATION_RECEIPT.json) identifies the frozen method and selected identities. Payload header compatibility and new-array interpretation belong to the separate comparison stage.

## Exact input preservation

The two original FITS files are preserved in four ordered [archive parts](INPUT_ARCHIVE.json). Combined ZIP: 3,578,014 bytes; SHA256 `7c515f430ec46b0e74aa4f43a71e90abbb9ceb75ec00eb4ff2db7d4f2bb6db43`. All parts, both complete member hashes and the uncompressed byte total passed verification. No spectral arrays were interpreted to create or verify the archive.

From this directory run `python3 restore_inputs.py` to verify and restore `products/`. It refuses to overwrite a differing existing file. Run `python3 restore_inputs.py --verify-only` to verify the complete archive and both members without restoring. Original direct download URLs remain recorded, but future live downloads may have different patched metadata. These parts preserve the exact bytes used in this continuation.

The original 300-exposure survey, 70.874650833-hour coverage, 669 V2 records and all dispositions remain unchanged. These two archival follow-up spectra supply targeted context, not two new survey-search exposures.
