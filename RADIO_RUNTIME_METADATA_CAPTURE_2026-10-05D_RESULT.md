# Runtime metadata capture D: closed before scientific imports

The distinct engineering scope `radio-runtime-metadata-capture-20261005d` is **FAILED_CLOSED**. Its sole guarded collector exited 2; the complete parent exited 1. Both were reaped, without a watchdog kill. No NumPy, h5py or hdf5plugin importer was reached, no native metadata output was produced, and no HDF5 dataset, spectrum, scientific trial or source session was opened. D is spent and cannot be retried.

## Exact failure and next eligible repair

The retained 560-byte stderr contains phase-2 admission followed by `Refusal: frozen target RECORD relocation row was unused`. Its SHA-256 is `64e74c5a074c65de039110743878d07deed0140b305a123ffce510f4fd6a47ee`.

Independent inspection of the pinned Python 3.12 `importlib.metadata` source explains the failure: `Distribution.files` filters out entries whose declared locations do not exist. NumPy's two original `../../bin/f2py` and `../../bin/numpy-config` RECORD rows refer to absent declared locations; the verified target installation stores their wrappers under `site-packages/bin`. D's exact relocation manifest handles those two rows, but the filtered enumeration removed both before the handler. The unchanged unused-row requirement therefore refused the observation. The frozen collector performs this distribution check before its scientific importers.

The preceding static/offline tests did not model that stdlib filtering behavior. Preserve that limitation and the original failed evidence. A **new, distinct capture-only E preparation** will enumerate the complete bounded raw RECORD bodies, retain every row and validate the same exact relocations. Its realistic preflight must include filtered `.files` behavior. This report neither activates E nor changes D's frozen sources, root, marker or limits.

## Publication and unchanged input custody

Preparation commit `24bddee788b06ffc756646f3d934beeba9ae9538`, tree `36836250f648dde293bb617fed3aae9bd7872a43`, precedes marker-only activation `130b60d0a7955be1d53ed6f9a3377a66631464a1`. All **43 complete preparation bodies / 1,838,704 UTF-8 bytes** matched immutable readback before activation. The marker's full body, sole parent, tree and sole changed path were checked before advancing the branch.

Freeze SHA-256: `83c50a46a150c91ebd2cb6109ac78b019a551dcdabe7bc662a4b7c0d74b4dd2b`. All **40 source plus 1,460 runtime pins** matched after closure. Independent checking also confirms all **1,038 installed file hashes, sizes and modes**, exact **110-directory** membership/modes and no links, special, extra or missing entries. The existing C installation remains unchanged: **299,652,798 regular-file bytes**, **300,103,358 logical / 302,645,248 allocated bytes** including directories. Allocated blocks describe observed storage, not immutable content identity.

The copied supervisor/guard/seal/phase-2 inputs remained unchanged. One leaf was admitted through both guard phases; sockets, new descendants and later executable starts were denied. Its parent-death SIGKILL and expected-parent race checks were active. These observations do not establish full native IO or continuous loader/namespace custody.

## Actual accounting and finite reservation

| Observation | Retained value |
|---|---:|
| Complete parent lifetime | 2.3599231699990924 s |
| Complete guarded leaf lifetime | 0.23295731999678537 s |
| Parent lifetime wait4 RSS | 215,408,640 bytes |
| Leaf lifetime wait4 RSS | 212,918,272 bytes |
| Conservative joined lifetime RSS bound | 428,326,912 bytes |
| Parent wait4 user / system CPU | 1.064583 / 1.291822 s |
| Leaf wait4 user / system CPU | 0.167304 / 0.064742 s |
| Root explicit reads | 822,941,840 bytes |
| Supervisor pin reads | 30,928,843 bytes |
| Proc metadata reads | 2,313 bytes |
| Retained stream reads | 560 bytes |
| Explicit parent total | 853,873,556 bytes |
| Fully charged opaque child reserve | 536,870,912 bytes |
| Conservative joined charge / reservation | 1,390,744,468 / 2,147,483,648 bytes |
| Closed root, including terminal/caller receipts | 9 files / 4 directories |
| Closed root logical / allocated footprint | 605,523 / 626,688 bytes |

RSS addition is a conservative bound, not a simultaneous tree peak. Child proc IO was unavailable in the local PID view; missing counters are retained as missing, never zero. Final footprints do not establish transient storage peaks. Preservation/review operations after closure are separate administrative work.

D reserved **180 parent seconds / 64 MiB artifact storage**, with a 150-second operation cutoff, one 90-second / 80-CPU-second leaf, parent and leaf 512-MiB AS ceilings, 8-MiB output/terminal caps and 2-GiB joined read reservation. The entire reservation is spent without reset or refund. Selected prior live-scope subtotal becomes **2,590 seconds / 5,240 MiB artifact reservations**; this is neither measured use nor a complete historical ledger. Five separate 30-second / 512-MiB-AS guard controls remain a separate category; process AS is not artifact storage.

## Complete closed evidence

The verified archive `SETI_metadata_capture_2026-10-05D_closed.zip` has **58 regular entries**, **445,287 bytes**, SHA-256 `e2d519ae58fb81becf65787b41a8f51d35e1c8653c7d7f648df37d0b929d29c7`. Every retained raw entry was verified by its complete hash. It preserves all D root evidence, frozen preparation sources/manifests, guard binaries, raw caller streams and preservation source. Preservation manifest SHA-256: `9806a925e1226b4d7d93c19293f2ebc9f91f0067bdf1180daaa6471c838c482c`.

The unchanged installed/base input bodies remain in the complete referenced C archive: **189,808,619 bytes**, SHA-256 `434e5a5d64e9361b591d527608290a0f7443e6b7b0b7543c9d6e9dbad1111b7a`. Content restoration does not recreate historical inode custody. Neither archive authorizes replay.

All **eleven scientific fields remain pending**, including actual HDF5/plugin runtime observations, full native IO/loader custody and original CAS/source/session admission. HD189733/HIP98505 cadence 85030 / neighbor 9 remains selected; HD1461 HOLD, GJ724 reserve, spectra and 112+128 holdouts unopened, native8 unreserved, 127/24 NOT ACTIVATED, LS paused and CHEOPS UNSENT. Consolidate **9 October 2026** without automatic extension. No scientific outcome or target decision changes.
