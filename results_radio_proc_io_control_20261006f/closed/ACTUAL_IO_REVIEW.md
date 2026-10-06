# Independent F actual I/O review

The single completed `radio-proc-io-control-20261006f` attempt supports `OBSERVED_KERNEL_IO_ONLY_PENDING_INTEGRATION`. This review read retained JSON and raw witnesses only, using base Python `-I -B -S`. It did not rerun F, launch the installed interpreter, import scientific packages, or modify frozen files. A second agent independently crosschecked the same selected JSON and agreed.

## Observed counters

The 131,072-byte payload was read eight times, with all eight reported pass hashes matching frozen SHA-256 `a95fd76b0505da19ff986507e75e8137c15a2912787e2a9d1fe6b7475823f4d8`. The known explicit workload is 1,048,576 bytes.

| Counter | Child self before | Child self after | Parent terminal snapshot |
| --- | ---: | ---: | ---: |
| rchar | 1,273,691 | 2,322,367 | 2,322,467 |
| wchar | 495 | 495 | 3,128 |
| syscr | 135 | 168 | 169 |
| syscw | 2 | 2 | 4 |
| read_bytes | 0 | 0 | 0 |
| write_bytes | 0 | 0 | 8,192 |
| cancelled_write_bytes | 0 | 0 | 0 |

Self `rchar` increased by 1,048,676 bytes, covering the known workload plus 100 bytes. Terminal `rchar` exceeds self-after by another 100 bytes. The terminal raw I/O body is 104 UTF-8 bytes with SHA-256 `4de0cd82116f5b7954c09ab9f3258f7acc3431e013eb87de62ab6fd726d031a9`; observer event 544 records that exact length and hash. Parsing its complete seven fields reproduces `terminal_proc.io`, the snapshot and `result.control.terminal_kernel_io`. Both self raw bodies independently match their stored lengths, hashes and values. All 14 retained live snapshots also have complete matching raw counters and the same child binding.

`read_bytes=0` is an actual field in complete kernel data, not a missing observation replaced by zero. Cached reads are consistent with this result; it does not mean the child read no data, and the review does not establish the cause of zero block-read charge. These are aggregate counters, not per-file or complete loader I/O attribution.

## Same child and terminal ordering

The leaf, waitid, terminal snapshot and exact wait4 all identify local child PID 6. The resolved outer PID is 49,903, outer PPid 49,902, and child starttime 7,362,824. Owner `NSpid=[49902,5]` and child `NSpid=[49903,6]` agree with the respective local PIDs. Both share PID namespace identity `(4,4026532277)`. The held child proc directory is `(30,296950)`, owner directory `(30,299932)`, and proc root `(30,1)`; owner starttime is 7,362,799. Terminal raw status/stat before and after bind the same PID, PPid and starttime and both record state `Z`. All four UID fields are zero.

The children-file route returned ENOENT, so the authenticated bounded proc scan examined 17 candidates and rejected 16. Its receipt records 559 operations, 30 candidate/lookup errors and 115,007 received bytes within the frozen bounds. Summing retained read-event charges independently reproduces 115,007. Those errors were retained and did not become zero counters.

Terminal observation records `available=true`, `terminal_observed=true`, `wnowait_requested=true`, waitid PID 6/code 1/status 0, and `wait4_called_here=false`. Its raw counter sample was taken in zombie state before reaping, at monotonic 73628.540620980. The supervisor subsequently records exact child wait4 PID 6/exit 0 before ending at 73628.540930766. This is consistent with the independently reviewed frozen WNOWAIT-then-wait4 flow. It authenticates the retained live and terminal samples; continuous namespace, loader and per-file custody is not established.

## Attempt, resources and authority

Custody records one guarded dispatch, phase-two exec sealing, no failures, exit 0 and reaping. Gate `children[0]` equals the separately retained custody JSON and its control-result SHA binds the actual leaf output. The caller records one gate dispatch, exit 0, reaping and success. Full parent lifetime is 0.7293748430092819 seconds; leaf lifetime is 0.29556938300083857 seconds. Exact wait4 high-water values are 78,229,504 bytes for the leaf and 81,879,040 for the gate, giving conservative sum 160,108,544 bytes. This is not simultaneous tree RSS. Administrative launcher overhead remains explicitly outside the gate envelope.

Explicit parent charges are 253,551,763 bytes: root 222,507,582 + supervisor pins 30,928,843 + proc 115,007 + streams 331. With opaque child reservation 16,777,216, the conservative joined charge is 270,328,979 within the 553,648,128-byte reservation. The reservation remains fully spent; it is not complete measured native I/O. All eight retained gate inventory files match their listed lengths and hashes. Storage inventories report selected stored bytes, not transient peaks. The entire 1,460-file runtime pin basis was not rehashed by this independent result review.

The actual leaf reports `-I -B -S` isolation flags true, scientific-package imports false and installed-interpreter launch false. All seven authority fields are false. Gate, custody and caller retain runtime/scientific authority false; gate retains full native I/O custody and full scientific closure false, with zero network requests, installations and HDF5 dataset reads.

Frozen `all_native_imports_forbidden=true` is overly broad, unused metadata wording. It is not an operative admission/protocol condition and cannot certify literal absence of native code. This scope uses base Python and its pinned stdlib/runtime binaries; the bootstrap imports `ctypes` and `hashlib` and loads pinned `exec_seal.so`, alongside native guard code. The intended prohibition covers installed NumPy/h5py/hdf5plugin and scientific native runtime. No zero-C-extension or zero-native-code claim is supported. Frozen bytes remain unchanged; this wording limitation does not invalidate the same-child counter observation.

This success closes the harmless selected counter control only. Integration into later runtime operations, complete native I/O custody, runtime qualification and original scientific production gates remain pending. No spectrum, source session, RNG, trial or scientific execution is admitted; no automatic successor or retry is authorized.

## Reviewed primary files

Paths below are relative to `/workspace/scratch/da6462abff17/radio-proc-io-control-20261006f`.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| control-result.json | 2456 | `cdc1713c5454bf24ba0d328e5dcd2540c4e177245da6eaafaaaa7f5a2f8aac0c` |
| processes/control.custody.json | 154654 | `f8bc4caf6c2093104470149d7232d2ce532f04a201ab964f386c519575333210` |
| result.json | 181293 | `2dfe5e2adcef607b4f6ac057c5a8f085e61e64c9a9c6860fa243ca4d8a7ee373` |
| caller-receipt.json | 1163 | `90e7b6758c469c46f733429afcffc930f505ce0ca99e0b01ac6df50daf2e0a0a` |
