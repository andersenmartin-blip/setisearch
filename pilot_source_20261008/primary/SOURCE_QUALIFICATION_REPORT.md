# HD 189733 / HIP98505 source qualification — 8 October 2026

The primary source is **usable for bounded, prospectively gated acquisition**. Current public metadata verifies all six scans of GBT cadence 85030, their identities/pointings/time/frequency layout, and all 96 required compressed chunk byte ranges. Their exact future payload sum is **305,133,821 bytes**; all spent source metadata plus that payload totals **306,292,061 bytes**, below the 2 GiB cadence ceiling. Complete chunk decoding would produce 384 MiB, below the 4 GiB RAM ceiling, with chunkwise decoding available. A full scientific pipeline memory measurement remains pending.

**No spectral payload was fetched, no telescope values were decoded, and no pilot/search/control evaluation was performed.** The source contract does not open the scientific value gate. Fresh prospective validation and normal-codec integration must pass before any real pilot acquisition. The source is one ON/OFF observing cadence with three ON scans and three OFF scans, not three independent revisits. No alternate was selected.

## Source and complete cadence

The archive identifies HD 189733 as HIP98505; the historical NASA Exoplanet Archive identity/coordinate record is retained in `historical_official_metadata.json`. Original catalogue receipts and metadata history are retained. Current 8 October HEAD and byte-range responses match all six frozen URLs, full file sizes and ETags. Every response was exact URL without redirection. The original catalogue names the telescope GBT, and each current filterbank header has telescope_id 6 / source_name HIP98505 or HIP98505_OFF. Declared catalogue MD5s are provenance fields, **not hashes verified by downloading the full files**.

All observations are on 17 March 2016. Start times below come from current HDF5 headers. The epoch1_off and epoch2_off catalogue timestamps are about 1 second earlier than their HDF5 headers; the headers are authoritative for trajectory timing. The OFF pointings are about 2 degrees north of ON. The previously frozen ON identity/proximity checks were 0.23988, 0.19353 and 0.27564 arcsec, below the 60 arcsec metadata criterion; this is no independent measured-pointing audit or epoch-propagated astrometry.

| Scan | Role | Catalogue ID | Header UTC start | RA hours | Declination degrees | Full file bytes | Required stored bytes |
|---|---|---:|---|---:|---:|---:|---:|
| epoch1_on | ON | 85030 | 16:33:36 | 20.012139444444 | 22.709715555556 | 12,633,556,341 | 50,852,779 |
| epoch1_off | OFF | 85032 | 16:39:06 | 20.012138888889 | 24.709705833333 | 12,635,962,948 | 50,856,655 |
| epoch2_on | ON | 85034 | 16:44:36 | 20.012139166667 | 22.709732777778 | 12,632,416,909 | 50,857,795 |
| epoch2_off | OFF | 85036 | 16:50:06 | 20.012139166667 | 24.709720277778 | 12,632,543,923 | 50,855,119 |
| epoch3_on | ON | 85038 | 16:55:36 | 20.012139166667 | 22.709706388889 | 12,628,346,613 | 50,855,862 |
| epoch3_off | OFF | 85040 | 17:01:05 | 20.012140833333 | 24.709731666667 | 12,629,521,140 | 50,855,611 |

Exact public files:

- `epoch1_on`: [spliced_blc02030405_2bit_guppi_57464_59616_HIP98505_0003.gpuspec.0000.h5](https://bldata.berkeley.edu/pipeline/AGBT16A_999_97/holding/spliced_blc02030405_2bit_guppi_57464_59616_HIP98505_0003.gpuspec.0000.h5)
- `epoch1_off`: [spliced_blc02030405_2bit_guppi_57464_59946_HIP98505_OFF_0004.gpuspec.0000.h5](https://bldata.berkeley.edu/pipeline/AGBT16A_999_97/holding/spliced_blc02030405_2bit_guppi_57464_59946_HIP98505_OFF_0004.gpuspec.0000.h5)
- `epoch2_on`: [spliced_blc02030405_2bit_guppi_57464_60276_HIP98505_0005.gpuspec.0000.h5](https://bldata.berkeley.edu/pipeline/AGBT16A_999_97/holding/spliced_blc02030405_2bit_guppi_57464_60276_HIP98505_0005.gpuspec.0000.h5)
- `epoch2_off`: [spliced_blc02030405_2bit_guppi_57464_60606_HIP98505_OFF_0006.gpuspec.0000.h5](https://bldata.berkeley.edu/pipeline/AGBT16A_999_97/holding/spliced_blc02030405_2bit_guppi_57464_60606_HIP98505_OFF_0006.gpuspec.0000.h5)
- `epoch3_on`: [spliced_blc02030405_2bit_guppi_57464_60936_HIP98505_0007.gpuspec.0000.h5](https://bldata.berkeley.edu/pipeline/AGBT16A_999_97/holding/spliced_blc02030405_2bit_guppi_57464_60936_HIP98505_0007.gpuspec.0000.h5)
- `epoch3_off`: [spliced_blc02030405_2bit_guppi_57464_61265_HIP98505_OFF_0008.gpuspec.0000.h5](https://bldata.berkeley.edu/pipeline/AGBT16A_999_97/holding/spliced_blc02030405_2bit_guppi_57464_61265_HIP98505_OFF_0008.gpuspec.0000.h5)

Their full-file total is 75,792,347,874 bytes, so whole-file downloading is outside this plan. Each file declares `data` shape `[16,1,264503296]`, little-endian IEEE float32 (`<f4`), chunks `[1,1,1048576]`, and one bitshuffle/LZ4 filter 32008 with preserved options `[0,3,4,0,2]`. The dtype endian confirmation used only retained cached metadata, with zero network/value access. Each 16-row scan spans 287.779586048 seconds of integrations, sampled every 17.986224128 seconds.

The shared native channel grid is `f(j)=1876.46484375 − j×0.000002835503418452676 MHz`. Physical array order is **time,feed,frequency**, established by shape/nchans and normal filterbank metadata. `DIMENSION_LABELS` incorrectly declares frequency/feed/time; this discrepancy is preserved explicitly rather than used to transpose the data.

## Frozen band and exact read budget

The metadata-selected 4096-channel reference interval is `[159905792,159909888)`, with descending native channel centers 1423.0514239036174 to 1423.039812517119 MHz. The prospective expanded science halo is `[159903921,159911759)`. Both lie wholly inside physical frequency chunk 152, `[159383552,160432128)`. It is disjoint from the historical calibration 159 and validation 156 chunks. Each needed physical chunk origin is `(row,0,159383552)` for rows 0–15, across all six sources.

`source_manifest.json` retains every exact future byte range, stored byte count, filter mask and source pin. All 96 recorded filter masks are 0. Their compressed sum is 305,133,821 bytes, versus 402,653,184 decoded bytes. There is no inference from a small requested hyperslab to small compressed I/O: the budget includes the complete intersected chunks. A later acquisition must allow only those exact 96 pinned ranges, preserve ETag/full-size checks, and reuse downloaded bytes for controls/analysis without repeated source fetches.

The source-specific normal-reader proposal is to place exact filtered bytes into small local HDF5 datasets using `write_direct_chunk` with original chunk/filter/type properties, then read the narrow halos with supported bitshuffle decoding. This avoids another source B-tree enumeration and requires no native build. The proposal has not fetched payloads or decoded this source. Codec numeric integration and full pipeline resources remain gates, not results of this metadata qualification.

## Preserved failure and distinct metadata result

The first h5py 3.15.1 / HDF5 1.14.6 metadata attempt verified every source header/shape/type/chunk/filter, then reached its 64 GET per-file ceiling while `get_chunk_info_by_coord` walked many nodes. It remains `FAILED_CLOSED`, with its original code, freeze, 64 receipts per file, and binary metadata untouched. There was no quota reset or retry of that operation.

Offline raw-chunk B-tree parsing recovered 72/96 records. The separately frozen direct lookup used official HDF5 v1 B-tree rules and only exact metadata children, never a leaf payload pointer. Its public freeze is **a35b5436934b6709151c8ada3ba7da5b74919907**, verified by parent readback before the invocation. The exact script hash is `e868886941a807c5d95d14c1e7aad5597edfac389dcef98b5a522bb17f812d21`. The authorized command ran once with an external 350 second timeout:

```sh
timeout 350s python pilot_source_20261008/primary/direct_chunk_metadata.py
```

It completed all 96 metadata records with 30 new 3136-byte GETs, **94,080 received bytes**, 29.040222 seconds wall, 0.194760 CPU seconds and 21,102,592 bytes peak RSS. Receipts were written before requests; all 30 responses were 206 with exact range, size, URL and ETag. A 200 response would have been rejected before its body. Node signatures/type/size/order/bounds/depth and exact chunk coordinates were checked. The independent caps were 32 GETs / 256 KiB per file, 300 seconds per source, one attempt without retries. There was no new runtime route or third telescope-reference analysis.

| Source phase | Disposition | HTTP requests | Received source body bytes | Wall seconds |
|---|---|---:|---:|---:|
| HEAD + 64-byte superblock probe | PASS |12|384|12.102635|
| Original h5py metadata enumeration | FAILED_CLOSED |384|1,063,776|420.935662|
| Offline cached-node salvage |72/96 records|0|0|Not a source request interval|
| Separate direct metadata traversal |PASS, 96/96 records|30|94,080|29.040222|
| Total these source phases |Preserved complete ledger|426|1,158,240|Individual intervals above|

`SOURCE_BYTES_LEDGER.json` charges all phases, including the failure. The measured scopes exclude dependency download/install, 7 October reference work and earlier project activity; unknown historical totals are not replaced by this ledger. Cash spend is 0 kr.

## Prior use, limits and retained evidence

`PROJECT_STATUS.md` at science head b74e13df1c17baa4300657087ea06a5ee095e499 explicitly records no HD 189733/pilot value, fresh evaluation or historical holdout opened. The exact retrieved excerpt is `prior_use_status_excerpt.txt`; historical source qualification also states spectral-values false. The old calibration/validation/pilot geometry is metadata history, and old synthetic fixtures are not fresh telescope validation. Old holdouts, reserved panels, the HD 1461 hold and GJ 724 reserve were not accessed or activated. Historical closed failures stay closed.

The machine-readable contract is `source_manifest.json`; the full result with traversal-node hashes is `direct_metadata_ranges/current_direct_chunk_metadata.json`. Public-freeze receipt, exact header receipts, dtype confirmation, byte ledger, and both metadata evidence bundles are retained alongside this report. `cached_metadata_ranges.tar.gz` preserves the closed first walk and `direct_metadata_evidence.tar.gz` preserves the new selective phase. Both deterministic archives have per-member byte/hash manifests and contain no spectral payloads.

Official documentation: [HDF5 File Format Specification](https://support.hdfgroup.org/documentation/hdf5/latest/_f_m_t3.html), v1 B-trees and Data Layout Message; [h5py chunked-storage behavior](https://docs.h5py.org/en/stable/high/dataset.html#chunked-storage); [h5py 3.15.1 public binary wheels](https://pypi.org/project/h5py/3.15.1/). These primary sources were verified before selecting the binary format/dependency rules. The complete header/shape/filter and byte-range evidence, rather than any observed spectral signal, establishes this source qualification.
