# Independent E metadata review

The preserved E metadata is internally consistent with the frozen three-package cohort and the expected engineering-only capture. This review parsed raw JSON, reconstructed all retained RECORD and mapping bodies, verified their whole hashes and row witnesses, and read the two 224-byte generated scripts. It imported no collector or scientific package, launched no installed Python, and performed no capture or installation. Frozen preparation and prior closed scopes were not changed.

- Metadata: `/workspace/scratch/da6462abff17/radio-runtime-metadata-capture-20261005e/native-metadata.json`.
- Complete metadata size: **2,868,865 bytes**.
- Complete metadata SHA-256: `53f52557608cb3014ffe2d025c0f3019d80cf8419af0eefd578513fa7fce09aa`.
- Collector status: `COLLECTED_IDENTITY_INPUTS_ONLY`.
- Root result status: `OBSERVED_METADATA_ONLY_PENDING_RUNTIME_QUALIFICATION`.

## Versions and origin

NumPy **2.3.5**, h5py **3.16.0**, hdf5plugin distribution/module **7.1.0**, HDF5 runtime **2.0.0**, runtime tuple **[2, 0, 0]**, and built-against tuple **[2, 0, 0]** match. Reported Python is **3.12.14**, isolated with bytecode writes disabled. All package files and package roots are exactly below the existing C venv site-packages; the plugin directory is its `hdf5plugin/plugins`. This is package origin evidence within the selected installation, not complete namespace or loader closure.

## Complete raw RECORD inventories

| Distribution | Raw rows | Raw bytes | Presence-filtered projection | Declared native ELF files | Declared native bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| numpy | 904 | 84,100 | 902 | 22 | 45,593,806 |
| h5py | 106 | 9,539 | 106 | 29 | 16,412,757 |
| hdf5plugin | 26 | 2,263 | 26 | 12 | 193,889,000 |

The independently decoded RECORD bodies match their pinned full SHA-256, byte count and exact owned dist-info paths. Every raw row has a matching unique inventory row, preserved original ordinal, hash and size. The projection follows raw CSV order and omits only the two declared NumPy script paths. Before/after file rows and full raw RECORD witnesses are exactly equal for all three distributions; every reported equality Boolean is true. Native inventory hashes also match their respective RECORD hash/size expectations. Ordinary nonnative RECORD hashes remain unverified expectations in this collector.

Both exact NumPy relocations were verified before and after: `../../bin/f2py` and `../../bin/numpy-config` are declared under the venv `lib/bin/` and actually installed under `lib/python3.12/site-packages/bin/`. Each actual script is **224 bytes**, mode **0755**, with the full script hash matching the frozen pin and the raw RECORD expectation. No generic relocation fallback appears.

| Script | Whole SHA-256 |
| --- | --- |
| f2py | `9282f9c09af119dab9fd49398513de73b9572b9572b50b86ddb13954dd65c264` |
| numpy-config | `fe54fc4a0c25865381e8d3e0dd80fadc6262f3fb784d01be14c799726c28a33a` |

## Native filter observations

Filter **32008 (`bshuf`)** was unavailable before importing hdf5plugin: availability false, info and encode/decode flags null. After import it was available with `get_filter_info = 3`, **encode enabled** and **decode enabled**. The required bitshuffle decode observation Boolean is true. All **12** declared filters follow the same before/after pattern. These are the explicit `filter_avail` / `get_filter_info` metadata calls; no dataset was opened or decoded. Importing hdf5plugin may itself execute native registration.

## Sampled mappings and named whole-file hash observations

| Snapshot | Mapping records | Named mapped files | Retained raw map bytes | Hash reuses |
| --- | ---: | ---: | ---: | ---: |
| maps_before_packages | 56 | 9 | 6,574 | 0 |
| maps_after_numpy_h5py | 336 | 46 | 67,976 | 43 |
| maps_after_plugin_and_inventory | 402 | 58 | 82,045 | 58 |

All three reconstructed maps bodies match their retained complete hashes and byte counts; parsed mapping rows and absolute-file membership match the JSON. No deleted mapped-file path is retained. All identified named mapped files are ELF in this observation. Across declared native inventories and three sampled maps there are **239 observations**, comprising **75 initial whole-file hash reads** and **164 identity-rechecked hash reuses**, covering **75 unique named ELF files** and **293,066,707 unique full-file bytes**. Every reused hash/identity/ELF record agrees with its original record; all recorded ELF headers identify 64-bit, little-endian, x86-64 files. Before native inventory has 63 files; after native inventory reuses all 63 hashes.

The observed native byte accounting is internally consistent: **293,066,707** named full-file bytes + **156,595** raw maps bytes + **191,804** raw RECORD bytes + **896** relocated-script bytes + **4,409** input-manifest bytes = **293,420,411 explicitly charged bytes**, below the **536,870,912-byte** reader cap. Loader/import implicit reads are explicitly excluded from that collector count. This review checks retained hash witnesses; it does not independently rescan all scientific ELF file bodies or measure every native read.

## Authority and remaining limits

All seven metadata authority fields are false: `scientific_execution_authorized`, `spectral_access_authorized`, `runtime_qualified`, `source_closure_qualified`, `native_custody_qualified`, `cas_qualified`, and `certificate_issued`. Root also keeps scientific authority, runtime qualification, complete native IO custody, and complete scientific closure false, with **0 installations**, **0 network requests**, and **0 HDF5 dataset reads** in E.

Sampled maps and selected before/after integrity do not prove continuous namespace/loader custody, complete load history, executed code/memory closure, provider custody, or complete native IO. Version and filter metadata are engineering observations. **All eleven scientific plan fields remain pending**; no spectrum access, source/CAS session, scientific trial, detector activation, or scientific certificate is admitted by this successful E capture.
