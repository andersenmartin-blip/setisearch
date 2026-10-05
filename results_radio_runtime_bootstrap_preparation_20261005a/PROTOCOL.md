# One-shot package bootstrap — 5 October 2026

The next engineering operation acquires the three exact original-plan wheels, checks their static archive contents, and runs one offline pip installation into a fresh owned directory. It closes the package-availability gap observed by capture B. It does not import NumPy, h5py, HDF5 or hdf5plugin, inspect telescope data, run codec or receiver trials, or qualify a scientific runtime.

The immutable original plan remains `results_radio_runtime_materialization_preparation_20261004a/runtime-materialization.plan.json`, 24,739 bytes, SHA-256 `fe0a2463d75002b2b675d998f7ac4f201b1b67664e21baa22b2e241ed8c46c25`. Package versions, archive URLs, archive sizes, hashes and wheel tags come from that plan. Fresh official release metadata matched all three identities and the historical raw metadata hashes. No extra provider, package or version is selected.

## Separate identity and finite allocation

Bootstrap identity: `7e4a63f99adcb7a9725211960b368db972e92b16c60bdf1a3d5220e49df2d52b`.

The fresh empty root is `/workspace/scratch/d804553c0e89/radio-runtime-bootstrap-20261005a`, device 27, inode 1575380, mode 0700. The fixed new activation path is `config/radio_runtime_bootstrap_20261005a.activate.json`. Existing capture A, hosted CAS and capture B remain closed, spent and nonretryable. This operation has its own identity and allocation; it borrows no earlier or scientific reservation.

| Selected limit | Ceiling |
| --- | ---: |
| Parent wall interval | 300 seconds |
| Direct offline pip child | 260 seconds |
| Child termination/reaping allowance | 10 seconds |
| Root logical and allocated storage, including directories | 1,610,612,736 bytes |
| Direct child virtual address space | 1,073,741,824 bytes |
| Parent explicit/conservatively precharged reads | 3,221,225,472 bytes |
| Unobserved child read reserve, retained in full | 1,073,741,824 bytes |
| Joined charged read envelope | 4,294,967,296 bytes |
| Each raw child stream | 1,048,576 bytes |
| Process/root samples | 1,200 |
| Single file and child RLIMIT_FSIZE | 134,217,728 bytes |
| Root regular files / directories | 20,000 / 4,096 |
| Protected terminal evidence storage | 8,388,608 bytes |

Publishing the new activation permanently allocates 300 seconds and 1,536 MiB of engineering headroom. The previous selected engineering subtotal is 1,030 seconds and 56 MiB; the resulting subtotal is 1,330 seconds and 1,592 MiB. These allocations are spent even if the operation refuses after activation or fails. They are not measurements of actual use and do not alter the scientific budgets.

A refusal during source admission can precede the root's local `spent.json` entry. The published activation and caller's one-invocation/no-retry law still consume the allocation in that case; an empty root does not authorize another attempt. File and parent-directory fsync provide the local spent-entry durability once that entry is created.

The 765 runtime files total 53,792,770 bytes. The 479 pip source/data files total 5,690,699 bytes. Two source-custody passes therefore require 118,966,938 raw bytes before publication proof, selected bootstrap sources, ZIP verification, terminal artifact hashing, process reads or EOF probes. Admission accounts for these terms separately. Parent requests are precharged without refunds, including zero-byte EOF probes. This conservative accounting is distinct from bytes actually returned.

Repeated short network or pipe reads can exhaust that finite charge before the transfer completes. The limit guarantees refusal before a further unaffordable read; it does not guarantee successful acquisition or installation. Terminal custody receives a protected read reserve, and unobserved suffixes are identified as such on failure.

## Publication, activation and execution order

1. Publish preparation sources, all tests and failed development snapshots, static prerequisite manifest, all 479 lossless installer representations, exact original-plan lock, resource analysis, and the generated contract/freeze.
2. Read every changed preparation file at the immutable preparation commit, validate its full body, length, SHA-256, Git blob and mode, decode all six base64 installer resources, and independently review readiness. A large body may be reconstructed from its fully read-back lossless parts, with the decoded raw Git blob bound to the expected immutable tree; raw and representation hashes remain separate. Read the inherited original-plan body as well.
3. Publish only the fixed new activation marker as a direct child of that preparation commit. Read back the complete marker and both immutable commit/tree relationships. Create a detached full-source publication witness and externally pin its raw bytes, the contract and activation.
4. Invoke the pinned primary CPython once with `-I -B -S` and those six detached inputs. Before wheel/seed mutation, hold and authenticate the empty root, rehash selected source/runtime files and the marker, and exclusively write/fsync `spent.json`. No retry, resume, alternate URL or automatic rearm is permitted.
5. Retain the complete actual outcome, partial files on failure, raw child streams, process brackets, before/after selected pins, root inventory, installed-file hashes and supervisor report. Independently review the original retained bytes, publish them losslessly and update status. A separate final publication receipt records full immutable result readback.

The gate verifies externally supplied publication evidence; it does not claim to perform network authentication of that evidence itself. The caller performs and preserves that readback before invoking the gate.

## Acquisition and static archive inspection

The three original archives total 68,409,067 bytes. Each is obtained through one HTTPS GET at its exact `files.pythonhosted.org` URL, with no redirects, retries or range/resume. Received bytes are retained even when size, stream or hash checks fail. Names are fixed and new files are exclusive. A held wheelhouse descriptor and its root relationship are checked.

Static inspection uses bounded EOCD and central-directory parsing before ZIP member streaming. It rejects multidisk/ZIP64, encryption, unsupported compression, unsafe or aliasing names, duplicate files, file/directory collisions, special modes, mismatched local/central headers and overlapping member regions. It hashes every regular member and checks exact size, CRC and canonical RECORD coverage. The sole RECORD row may have blank hash/size; unsupported signature exceptions are refused. METADATA name/version and the expanded WHEEL tags must match the original plan. No member is imported or directly extracted by this checker.

Per-wheel central directories are bounded at 2 MiB and 8,192 entries. Total declared payload is bounded at 512 MiB, and each member at 128 MiB. The payload ceiling is not a storage admission guarantee. Before the child starts, an explicit conservative estimate includes three times the actual declared payload, exact archive bytes, seed bytes, proof/evidence, terminal reserve and rounded file/directory allocation. If this estimate cannot fit, the spent operation closes without starting pip.

## Pinned offline installer and outcome limits

The static prerequisite read copied pip 26.2.1 without importing it. All 479 raw source/data rows and the sole `pip-26.2.1.dist-info` directory have separate raw and stored representation pins. Ambient bytecode is excluded. The gate rehashes original selected sources and creates a fresh isolated installer seed. Six Windows launcher resources are retained as data; they are not executed.

The one child uses the pinned interpreter, `-I -B -S`, its fresh seed and verified standard-library paths. Pip receives `--isolated --disable-pip-version-check install --no-index --no-deps --no-cache-dir --require-hashes --only-binary=:all: --no-compile --progress-bar off`, with only the owned wheelhouse, exact lock and owned target. `PIP_CONFIG_FILE=/dev/null` and the owned temporary directory are fixed. Scientific packages are installed as bytes, not imported.

The supervisor authenticates its own direct child through held pidfd/proc descriptors, namespace/session/interpreter bindings and raw identity brackets, then waits and reaps it. Finite process/root samples and storage checks provide observations at their recorded times. They do not establish absence of escaped descendants, peaks between samples, aggregate/provider RSS or a complete implicit loader closure. The reused capture-B source is exact published bytes used only for descriptor/accounting primitives; its old run and marker are never invoked.

Pip's implicit and explicit file/ZIP reads are unobserved. The entire 1 GiB child reserve remains charged; no observed joined read total or full joined-I/O certificate is invented. Child RLIMIT_AS, sampled memory and wait4 peak are reported with their individual scope. Transient child storage between checks also remains outside a peak certificate.

The 8 MiB terminal evidence reserve protects space and is checked before terminal writes. It does not guarantee that arbitrary unexpected child output or long names can be serialized within that reserve or the remaining wall interval. In such a refusal, existing raw/partial objects remain for caller preservation; the caller must not invent a missing terminal report.

Successful static installed-file/version checks permit only `MATERIALIZED_PACKAGES_ONLY` with `PENDING_RUNTIME_QUALIFICATION`. HDF5 2.0.0, native dependency closure, filter behavior, complete scientific freeze, receiver trial law, hosted transport/CAS, reservations and all 11 scientific fields still require their original evidence. Installed metadata does not authenticate a loaded HDF5 version.

The target, cadence, schedule and holdouts remain as recorded. Consolidation remains 9 October 2026 without an automatic extension.
