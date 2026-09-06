# M43H: two widened telescope sources verified

**Both frozen ON/OFF telescope anchors pass the widened-source gate.**

M43H adds a separately named widened-source factory, row receipts and bounded HTTP range transport. It preserves exact native hyperslabs, normalizes from the new ascending extraction origin, and verifies row bytes and normalization before restart or rehydration. The old M37 source contract and M43G synthetic adapter remain unchanged.

## Results by stage

| Stage | Exact scope | Result |
|---|---|---|
| Development tests | 55 M43-family tests, including 11 source/transport tests | Passed |
| Full-size local dataset facade | 2 sources, each 16 x 1,132,270 float32 values | Passed |
| Interrupted source extraction | Stop after 5 rows, resume only the remaining 11 per source | Passed |
| Fixture normalization | 32 full rows against independent sorted median/MAD | Exact |
| Completed fixture restart | 16 reused rows per source; zero new dataset reads | Identical receipts |
| Actual local HDF5 integration | gzip and Bitshuffle/LZ4; 3 rows each through bounded sparse interface | Passed |
| HDF5 restart and fault checks | Interrupt after row 1, resume, reject changed header, completed restart without new HTTP requests | Passed |
| Live telescope sources | epoch1_on and epoch1_off at 1412.5 MHz | 2/2 attested; 32/32 rows verified |

All stages keep their own provenance. The full-size dataset facade has the real metadata/dimensions but locally generated values and does not decode HDF5. The codec fixtures decode real local HDF5 files with simulated HTTP responses. Neither fixture category counts as telescope data. No broader repository test run is claimed.

## Live anchor outcomes

| Scan | Source gate | HEAD attempted/completed | Range attempted/completed | Accepted range bytes |
|---|---|---:|---:|---:|
| epoch1_on | telescope-source-attested | 1/1 | 96/96 | 457,178,431 |
| epoch1_off | telescope-source-attested | 1/1 | 96/96 | 457,176,430 |

The fixed archive interval is [163032021, 164164291), start-inclusive and stop-exclusive. The prospective factory owns live URL/size/ETag, header, chunk-geometry and exact `data[row, 0, start:stop]` checks. A successful source binds the qualified runtime, observed dataset filters, range plan and hashed transport checkpoint to native and normalized row receipts. Every completed live source is also compared against the independent sorted normalization reference and rehydrated in the result audit. Accepted HTTP byte counts include prefetched compressed/metadata regions; they are not the number of decoded science-array bytes.

## Integrity, normalization and resource scope

Each native descending row and its internally derived normalized ascending row is written atomically as .npy, flushed and fsynced. Its receipt is published last. Restart checks file and payload hashes, dtype, shape, row order and normalization before reuse. No incomplete row inventory is a complete source. Rehydration requires an independently retained source-receipt SHA and the expected source kind; local fixtures cannot satisfy telescope-kind rehydration. Checksums do not provide a cryptographic guarantee against a malicious server or runtime.

Normalization uses the M43G-qualified float32 median/MAD arithmetic in 4096-channel blocks from the new extraction zero, including the terminal block. No old normalized-source or threshold receipt is reused. A verified mirror may grow for another window without changing an earlier complete source identity when its original segments and exact row inventory survive.

The declared buffer model is 126.55 MiB per selected source, under a 256 MiB cap. HTTP requests are at most 8 MiB; file-object reads at most 32 MiB; configured HDF5 chunk cache 8 MiB; accepted decoded chunks at most 16 MiB. HTTP identity/range checks precede a body read bounded to requested length plus one byte. This is static buffer accounting and exercised integration behavior, not a measured full-process RSS ceiling or a bound on all HDF5/compression/OS internals.

## Environment change and public freezes

The installation tool initially reported that network approval was cancelled. Both required packages subsequently became available. The first full-size fixture run correctly left live access blocked because HDF5 integration had not yet been qualified; that historical result and configuration remain published. The local HDF5/codec checks were then completed, and their receipt and the live amendment were public before the telescope attempts. The earlier dependency limitation is historical, not a current missing-package claim.

Qualified runtime: NumPy 2.3.5, h5py 3.16.0, HDF5 2.0.0, hdf5plugin 7.1.0. Initial fixture freeze: `4db1a35bce82117de47689c83713ad4b2d208c2e`. Live amendment freeze: `bbc686467ff925390006b49d88fb569eff2fbd76`. Both were fetched and verified before their respective evaluations.

## Next gate and scientific limits

The two selected sources are ready for the next separately qualified physical cache/score path. Next compare selected full-grid real-data score anchors with direct native-window calculations for the fixed bank, preserving ON/OFF controls and repeated-channel correlations. Renew null/threshold calibration before interpreting new-bank detections.

No spectral filter, signal-track score, injection recovery rate, candidate ranking or new threshold is produced by M43H. Source verification is a prerequisite to those calculations. All earlier scientific results retain their original scope and denominators.

## Reproduction and audit

Live result identity: `be4a08ee35c1b1a9257538c31c580ceb5fada308932daa47592844ab8e81e56e`. Fixture identity: `dcb823c1e8a1a906d86f5e86c86a6daadcc6d2e471f61ba4f2541d1233f7dd44`. HDF5 integration identity: `60bfdc726d6dcffcf318b5d9aaf7aca85d278595177160e7056389409e114e27`. The manifest pins the plans, implementation, tests and derived receipts. Intermediate row arrays are reproducible working inputs and are not published as user-facing datasets.

The audit rechecks frozen inputs, exact stage inventories and transport counters, regenerates every full-size fixture raw row, and rehydrates all completed source receipts. Published range plans use the inherited transport encoding so their file SHA matches the source receipt. The audit does not repeat remote downloads or claim independent telescope observations. To reproduce the historical facade stage, use its original public freeze; the current configuration advances to live sources.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python -m unittest discover -s tests -p 'test_m43*.py' -q
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43h_hdf5_integration.py
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43h_live_sources.py --work-root /absolute/working-directory
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43h_result_report.py --work-root /absolute/working-directory
```
