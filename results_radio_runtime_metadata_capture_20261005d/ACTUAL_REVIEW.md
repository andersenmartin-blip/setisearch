Independent read-only review of `radio-runtime-metadata-capture-20261005d`, 5 October 2026.

The single D operation is **FAILED_CLOSED**. It preserved a guarded, reaped failure and did not complete native package metadata capture. This review read retained receipts, frozen source, raw stderr, input manifests and file bytes. It did not execute a collector, launch the installed interpreter, import NumPy/h5py/hdf5plugin, run tests, or alter frozen D preparation or its output root.

The caller receipt records exactly one parent dispatch, exit 1, reaping, a full parent lifetime of 2.3599231699990924 seconds and no watchdog kill. The direct-leaf custody receipt records exactly one leaf dispatch, exit 2, reaping, and 0.23295731999678537 seconds. Both the exact phase-1 guard record and phase-2 exec-seal marker are retained. The only leaf failure is `nonzero_leaf_exit`; raw stderr identifies the collector refusal as `frozen target RECORD relocation row was unused`. Stdout is empty, and no `native-metadata.json` exists.

The failure cause is supported by the actual pinned stdlib and collector source, rather than by an inferred package incompatibility. Python 3.12 `importlib.metadata.Distribution.files` parses RECORD and then applies `skip_missing_files`, filtering each row with `path.locate().exists()`. `PathDistribution.locate_file` joins the RECORD path to the dist-info directory's parent. NumPy's byte-preserved RECORD declares `../../bin/f2py` and `../../bin/numpy-config`; their resulting `venv/lib/bin` locations are absent. The corresponding pinned 224-byte scripts exist in `venv/lib/python3.12/site-packages/bin`. The stdlib property therefore removes both declared rows before D's exact relocation handler can see them. The handler's required-use check then refuses the empty used-row set.

This refusal occurs in `distributions_before`, before the frozen collector calls `importer("numpy")`, `importer("h5py")` or `importer("hdf5plugin")`. The retained error and deterministic frozen flow support failure before those package imports and before HDF5 filter observation/registration. Interpreter startup and the guard/seal bootstrap did execute native code; this finding does not claim otherwise. The collector did read and hash native ELF bytes as metadata before refusing. No spectrum, HDF5 dataset, scientific trial or source session was opened by this collector flow.

The actual collector SHA-256 is `495cdc20a217ea197c5c122510002f3841d782456c655f7a9293069197d1768e`; the pinned stdlib metadata source SHA-256 is `1a26dfee8cb302b729501e944626f77e2cbcc4675038f3d18c2d8534751b3e8b`. Both independently match D's freeze. Retained stderr is 560 bytes, SHA-256 `64e74c5a074c65de039110743878d07deed0140b305a123ffce510f4fd6a47ee`.

Independent file verification found no mismatch across all **40 source pins, 1,460 selected runtime pins and 1,038 installed venv files**. Their full hashes, sizes and modes match. The installed tree contains exactly **1,038 regular files and 110 directories**; directory modes match, with no extra/missing paths, links or special files. These files include the three regenerated RECORD files and generated scripts. Both historical before/after tree observations agree with the current independent verification. All seven files in the gate's preterminal artifact inventory also match their retained hashes.

| Read accounting item | Bytes |
| --- | ---: |
| Root explicit reads | 822,941,840 |
| Supervisor held-file pin reads | 30,928,843 |
| Supervisor proc metadata reads | 2,313 |
| Retained leaf stream reads | 560 |
| Total explicit parent reads | **853,873,556** |
| Fully charged opaque child reserve | 536,870,912 |
| Conservative joined charge | **1,390,744,468** |
| Frozen joined reservation | **2,147,483,648** |

The arithmetic reconciles exactly and every explicit partition is within its frozen bound. The full **2 GiB reservation remains spent, with no refund**, even though the observed explicit reads plus opaque charge are smaller. Proc child IO is unavailable in this PID view and is explicitly recorded as unavailable; it is not substituted with zero. The 512 MiB opaque reserve is accounting, not a complete measurement or certification of loader/native IO.

The caller's parent wait4 high-water value is 215,408,640 bytes, and the direct leaf's wait4 value is 212,918,272 bytes. Their sum, **428,326,912 bytes**, matches the retained conservative bound. It is not a measured simultaneous process-tree RSS peak.

| Storage observation | Files | Directories | Logical bytes | Allocated bytes |
| --- | ---: | ---: | ---: | ---: |
| Gate inventory before result.json | 7 | 4 | 591,330 | 606,208 |
| Caller inventory before caller-receipt.json | 8 | 4 | 604,369 | 622,592 |
| Current retained D root | 9 | 4 | 605,523 | 626,688 |

These totals include directory storage. The caller's raw outer streams are outside that root and are explicitly excluded by its receipt; preservation is separate administrative work. Logical and allocated figures are snapshots, not transient storage peaks or immutable identity fields. The reused C venv separately occupies 300,103,358 logical / 302,645,248 allocated bytes including directories; it is an input, not newly written D storage.

D's 180-second wall reservation, 90-second leaf bound, 512 MiB parent/leaf address-space ceilings and 64 MiB output envelope were not exceeded by the retained observations. No installation occurred. Source/runtime/tree matches establish selected pre/post integrity, not continuous ancestor namespace or native loader custody.

D must remain closed. A raw RECORD inventory repair may be prepared separately, but does not retroactively repair, repeat or activate D. This review grants **no runtime, loader, native custody, CAS, transport, source-session or scientific qualification; no certificate; no spectral access; and no scientific execution permission**. All eleven scientific admission fields remain pending.
