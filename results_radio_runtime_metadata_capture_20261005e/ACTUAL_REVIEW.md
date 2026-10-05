Independent read-only review of `radio-runtime-metadata-capture-20261005e`, 5 October 2026.

The single E operation completed **OBSERVED_METADATA_ONLY_PENDING_RUNTIME_QUALIFICATION**. Its caller reports success, and its collector completed **COLLECTED_IDENTITY_INPUTS_ONLY**. Independent verification found no material mismatch in retained receipts, selected input integrity, artifact bytes or metadata. This is successful bounded engineering observation, not scientific admission or a complete runtime/native custody certificate.

The review read frozen source, manifests, receipts, raw streams, metadata and selected file bytes. It did not run tests, replay the scope, execute the collector, launch the installed interpreter, perform package imports or make native observation calls. No frozen preparation or actual E file was changed. This report is written separately under preservation.

There was exactly one outer dispatch and one guarded leaf dispatch. Both exited 0 and were reaped. The exact phase-1 guard and phase-2 exec-seal records are retained; the leaf reports no failure and the caller reports no watchdog kill. The leaf CPU/wall observations are **1.118381 / 1.1218861450033728 seconds**. Terminal outer wait4 CPU is **2.432254 seconds**, and full parent lifetime is **2.4368178980002995 seconds**. The 180-second whole-operation reservation, 150-second active cutoff, 90-second leaf wall bound, 80-second leaf CPU ceiling and 512 MiB parent/leaf address-space ceilings were respected by retained observations/enforcement. No installation occurred in E.

`native-metadata.json` is **2,868,865 bytes**, SHA-256 **`53f52557608cb3014ffe2d025c0f3019d80cf8419af0eefd578513fa7fce09aa`**. Its independently checked bytes agree with the gate and stdout hashes. Stdout is 327 bytes with SHA-256 `f38dbe789bb59edb4214877649e468759e450ee09d62a0558494203ff53b9d6c`; stderr is the 154-byte phase-2 marker with SHA-256 `38bdc7dfc8ca28970cda9ea864fb26a1d4c9dd69a7898eef5c242ffb50302c8f`. Both match the direct-leaf custody receipt. All eight files in the gate's preterminal artifact inventory independently match retained hashes, sizes and modes.

Independent current verification matched all **44 source pins and 1,460 selected runtime pins**, totaling **1,504 pins**, including their full hashes, sizes, modes and frozen identity/link observations. All **1,038 installed venv files and 110 directories** also match hashes, identities, modes, link counts, path bindings and exact membership. There are no extra/missing paths, links or special files. The historical before/after tree observations agree with these checks; the retained C venv remains unchanged. These are selected integrity checks, not continuous ancestor namespace custody.

| Explicit parent read component | Bytes |
| --- | ---: |
| Root explicit reads | 830,970,074 |
| Supervisor held-file pin reads | 30,928,843 |
| Supervisor proc metadata reads | 2,313 |
| Retained leaf stream reads | 481 |
| Total explicit parent reads | **861,901,711** |
| Fully charged opaque child reserve | 536,870,912 |
| Conservative joined charge | **1,398,772,623** |
| Frozen joined reservation | **2,147,483,648 (2 GiB)** |

Every explicit partition is within its frozen ceiling and the arithmetic reconciles exactly. The collector's separate explicit-read charge reconstructs to **293,420,411 bytes**, below its 512 MiB ceiling. That child observation is covered by the opaque child reservation; it is not added again to the joined charge. The full **2 GiB reservation remains spent, with no refund**. Child proc IO was unavailable in this PID view and is recorded as unavailable, never zero. Neither explicit reader accounting nor the opaque reserve measures complete loader/provider/native IO.

Gate self highwater before terminal serialization is **224,116,736 bytes**. The terminal outer wait4 highwater observation is **227,119,104 bytes**, including waited-child accounting. Direct-leaf wait4 highwater is **227,119,104 bytes**. The earlier gate conservative sum is therefore **451,235,840 bytes**, while the terminal caller sum is **454,238,208 bytes**. Both reconcile. They are distinct kernel observations and conservative sums, not measured simultaneous process-tree RSS peaks; the difference does not prove growth of the parent's own RSS.

| Stored-output snapshot | Files | Directories | Logical bytes | Allocated bytes |
| --- | ---: | ---: | ---: | ---: |
| Gate inventory before result.json | 8 | 4 | 3,465,560 | 3,485,696 |
| Caller inventory before caller-receipt.json | 9 | 4 | 3,479,458 | 3,502,080 |
| Current retained E root | 10 | 4 | 3,480,652 | 3,506,176 |

Directory storage is included. Adding result.json and caller-receipt.json reconciles these totals; no additional allocation delta was found. They are far below the 64 MiB output envelope with its terminal reserve. Caller raw outer streams are outside this root and explicitly excluded by its receipt; preservation is separate administrative work. These are final snapshots, not transient storage peaks. The reused C input tree separately occupies **300,103,358 logical / 302,645,248 allocated bytes** including directories.

The captured versions are NumPy **2.3.5**, h5py **3.16.0**, and hdf5plugin distribution/module **7.1.0**. HDF5 runtime and built version are both **2.0.0**. Observed module files/package roots and the plugin directory all belong to the retained C venv. The process reports isolated cp312 Python 3.12.14 with bytecode writing disabled and the expected venv/base prefixes and site path.

| Distribution | Complete raw RECORD rows | Presence-filtered projection | Script relocation witnesses | Declared native ELF files |
| --- | ---: | ---: | ---: | ---: |
| NumPy | 904 | 902 | 2 | 22 |
| h5py | 106 | 106 | 0 | 29 |
| hdf5plugin | 26 | 26 | 0 | 12 |

Decoded raw RECORD hashes match their frozen whole-body inputs. The two NumPy scripts have exact frozen relocation witnesses. Files and raw RECORD source objects compare equal before/after for all three distributions. The presence-filtered projection is explicitly separate from complete raw inventory.

All **12** declared plugin filters were absent before plugin import. After import all report available with `get_filter_info=3`, encode enabled and decode enabled, including required bitshuffle **32008**. This establishes registration/capability metadata in that process. It does not establish successful dataset decoding, encoder behavior or codec qualification.

The three map snapshots contain **56 / 336 / 402 mapping records** and **9 / 46 / 58 named ELF file identities**, respectively. Decoded raw-map hashes match their retained witnesses. Across distribution declarations and sampled maps, all **75 distinct named ELF paths** have byte-size/SHA agreement with the combined frozen source, runtime and installed-tree pins, including the E exec-seal helper. There are no unseen paths or conflicting hashes in that selected comparison. The 63 declared native ELF files and sampled maps identify named bytes; they do not prove complete load history, executed-memory identity, loader edge closure or continuous native custody.

All seven collector `NO_AUTHORITY` fields are false. Gate/caller runtime qualification and scientific authority remain false, and full native IO/full scientific closure are explicitly unqualified. The frozen collector opens no HDF5 dataset or spectrum and runs no scientific trial/source session. Its permitted package imports and implicit plugin registration are engineering metadata work.

E's one-shot reservation adds **180 seconds and 64 MiB of output capacity** to the selected reservation ledger. The coordinator reports a selected subtotal of **2,770 seconds / 5,304 MiB**; this is reservation accounting, not measured full-history usage. The spent marker is retained and no automatic successor is activated. C and D remain closed. **All eleven scientific admission fields remain pending**: this review grants no scientific execution, spectral access, source-session, transport, CAS, runtime or native custody qualification and issues no certificate.
