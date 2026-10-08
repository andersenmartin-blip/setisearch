# Separate selective metadata traversal — prospective scope, 8 October 2026

The first h5py `get_chunk_info_by_coord` attempt remains `FAILED_CLOSED`: its 64-request per-file ceiling stopped enumeration after all six current headers were verified. It received 1,063,776 body bytes in 384 GETs. The preceding HEAD/superblock probe received 384 bytes in 12 requests. **The source ledger before this separate phase is therefore 1,064,160 received body bytes and 396 requests.** No spectral payload or value was read.

Offline parsing recovered 72 of the 96 required physical chunk records, without network access. The new algorithm performs targeted root-to-leaf traversal of the existing raw-chunk v1 B-tree, using verified retained nodes. It does not call h5py, H5D, a dataset slicing API, or a codec. It never follows a leaf child pointer as a read address: that pointer identifies a future spectral payload range and is recorded only.

The frozen selection is sixteen time rows × six scans × frequency chunk 152, physical origin `(row, 0, 159383552)`. The HDF5 superblocks use version 0, 8-byte offsets/lengths and base address 0. The chunked version-3 layout at absolute byte 1240 identifies B-tree root 7432, rank-plus-dtype dimensions `(1, 1, 1048576, 4)`. All six retained layout and superblock bytes were verified offline. A raw-chunk B-tree node is 3136 bytes; its 24-byte header, 40-byte `<II4Q` keys and 8-byte child addresses follow the official format. Keys give stored byte count, filter mask, three chunk coordinates and a zero datatype coordinate. The chunk-tree interval rule is lower-inclusive, upper-exclusive. Nodes above level 0 point to metadata; level-0 children point to payloads.

The exact missing addresses are in `direct_offline_validation.json`. Each source needs the cached-key-selected row-12 leaf and one level-1 node for rows 13–15; the latter supplies their three exact leaf addresses. Expected new work is five 3136-byte metadata GETs per file: **30 GETs, 94,080 bytes total**. The address discovery rule is frozen, rather than guessing unobserved child addresses.

Hard independent phase ceilings are 32 new GETs and 262,144 received body bytes per file, 300 seconds per source, 30 seconds per HTTP request, one attempt and no retries. Six sources may run in parallel. The invocation must use an external 350-second command timeout. Before each new GET, a reservation receipt is written. Every response must be exact URL, status 206, expected ETag, exact Content-Range including full pinned file size, and Content-Length 3136. Status 200 or mismatched headers is rejected before reading the response body. Node type, size, bounds, ordered keys, depth decrease and exact leaf chunk coordinates are verified. A fresh output directory is mandatory; an existing output directory prevents replay.

The configuration pins all retained byte-range files, their original request receipts, superblocks, exact six URLs, full file sizes and ETags. The implementation records every reused/new traversal node hash, exact stored payload offset/size/mask and complete prospective payload sum. The source contract cannot be declared qualified unless all 96 exact ranges are obtained. It cannot authorize scientific values or search execution: the fresh prospective validation and its gates remain separate.

One command after the parent verifies the public freeze:

```sh
timeout 350s python pilot_source_20261008/primary/direct_chunk_metadata.py
```

The existing first-attempt files are read-only inputs and remain preserved. A separate `direct_metadata_ranges` directory receives this phase's receipts and result. The final ledger must add the new actual body/request counts to the previous 1,064,160 bytes and 396 requests, even if this phase fails.

Official format attribution: [HDF5 File Format Specification — v1 B-trees](https://support.hdfgroup.org/documentation/hdf5/latest/_f_m_t3.html), section III.A.1, and [Data Layout Message](https://support.hdfgroup.org/documentation/hdf5/latest/_f_m_t3.html), section IV.A.2.i, verified 8 October 2026. The official [h5py chunked-storage documentation](https://docs.h5py.org/en/stable/high/dataset.html#chunked-storage) explains why a narrow hyperslab still requires its entire intersected compressed chunks; our budget uses stored chunk sizes, not requested array dimensions.
