# Closed F namespace-aware process IO result

6 October 2026. **OBSERVED_KERNEL_IO_ONLY_PENDING_INTEGRATION**. Exactly one harmless deterministic control was dispatched and closed successfully. This establishes the stated direct-child identity/counter observation in the current environment; it issues no complete runtime/native, codec, hosted-profile, CAS or scientific certificate.

## Concrete improvement

The previous supervisor correctly refused a proc directory whose PID differed from the local wait namespace. F binds the actual owner and waited child across the visible outer and local PID namespaces, retaining proc root/owner/child directory handles, namespace inode, UID, parent and starttime. WNOWAIT leaves the terminal child observable for its last IO snapshot before the sole owner's exact wait4.

The unchanged guard/seal/bootstrap bytes were reused; the interpreter wrapper already accepted -I -B -S. The new F fork also fixes an inherited cleanup issue: a repeated selector/drain error cannot bypass the independent bounded terminal/reap path. C/D/E and earlier scopes remain closed and are not retried or edited.

## Exact observed control

| Evidence | Observation |
|---|---|
| Owner PID | outer49902 / local5 |
| Waited child PID | outer49903 / local6 |
| Namespace | device4 / inode4026532277 |
| Child starttime | 7362824 ticks |
| Resolution | bounded proc scan:17 candidates /16 rejected |
| Live and terminal snapshots |14 live +1 terminal; same held child identity |
| Terminal state | Z before/after; exact WNOWAIT child6 before wait4 |
| Guarded child and gate | one each; exit0; reaped; no watchdog kill |
| Payload |131072 fixed ASCII bytes ×8 hash-checked passes |
| Known workload |1048576 explicit logical read bytes |
| Child self rchar change |1048676 bytes, including100-byte prior self IO read |
| Terminal kernel rchar |2322467 bytes;100 above child self-after |
| Complete leaf lifetime |0.295569383 seconds |
| Complete gate lifetime |0.729374843 seconds |

The direct children path returned ENOENT with zero received bytes. The finite fallback retained every failed candidate/error/read event and resolved one exact child. All115007 received proc metadata bytes,559 operations,17 candidates and30 error/rejection events are accounted. Zero received bytes on the failed path do not replace missing IO counters. A separately inferred child-only proc-read subset remains unknown.

| Kernel counter | Terminal value |
|---|---:|
| rchar |2322467 |
| wchar |3128 |
| syscr |169 |
| syscw |4 |
| read_bytes |0 |
| write_bytes |8192 |
| cancelled_write_bytes |0 |

These are the actual seven fields in retained raw terminal IO. Logical rchar covers the frozen workload and the child's complete self-after counter. Storage-layer read_bytes=0 is a present page-cache-compatible kernel observation; it does not mean that no reads occurred. These counters do not identify every loader operation or attribute each read to a file.

## Admission, tests and independent verification

Preparation commit **6abaa3ff6ebb10af17bf99625316ce3cc44afd2b**, treefe062fd638186955c9952f06ccdfe9223faae839. All **37 complete bodies /1436687 UTF8 bytes** matched immutable readback, including independently calculated Git blob hashes. Freeze538703 bytes, SHA256 **fd4a4e77d504425abab17a6cb82cc306a16b629491c3480fa5736e9c6d9dac77**.

Marker-only activation **e18b3ee123d00bcb7eb51abef4aae0466a18581e**, tree2a8f9a95cfec34fce1793c0c2cdcaf1515ba13c3, has the preparation as its sole parent and the exact marker as its only changed path. Marker full body and Git blob were read back; SHA2566e5f59e25979d3c356e50a436f249e1476a58ba93ff27b19c42ae2a4d625c616. Both ordinary branch publications used explicit expected-head leases and non-forced updates. This demonstrates these administrative writes; it does not qualify the original scientific CAS law or its stale-head/atomicity prerequisites.

Before freezing, **43 distinct offline fixtures** passed:19 proc,5 fake supervisor,12 independent gate/launcher and7 admission cases. The copied-layout19+5 rerun also passed. Initial fixture adjustment and numeric derivative defects were fixed prospectively and retained. No real control or scientific native import occurred in those tests.

Independent actual closure passes **37/37 checks** with complete receipts. All **1494 selected files (34 source +1460 runtime)** match current full SHA256/bytes/modes and declared runtime identities/link counts. Every raw closed-root file and eight preterminal inventory entries match. A preliminary administrative reviewer assertion omitted directory logical/allocated contributions; the corrected review includes all four4096-byte directories. The initial failed review is retained separately and is not a failure of the F operation. [Complete closure review](results_radio_proc_io_control_20261006f/closed/ACTUAL_CLOSURE_REVIEW.md) and [independent IO review](results_radio_proc_io_control_20261006f/closed/ACTUAL_IO_REVIEW.md) state the exact evidence and limitations.

## Resource arithmetic and closed storage

| Charged evidence | Bytes |
|---|---:|
| Gate explicit reads |222507582 |
| Supervisor held pins |30928843 |
| Proc metadata, all candidates/owner/child |115007 |
| Retained streams |331 |
| Explicit parent total |253551763 |
| Opaque child reserve, fully spent |16777216 |
| Conservative joined charge |270328979 |
| Frozen joined reservation |553648128 |

Frozen limits:30s whole gate (20 active +10 finalization),10s child wall/5s CPU/2s cleanup,256MiB parent AS/128MiB child AS,16MiB artifact with1MiB terminal reserve,1MiB output file,64KiB each leaf stream,2000 files/128 directories,0.02s sampling. Explicit parent reservations448+32+16+16=512MiB; opaque child16MiB yields528MiB joined. The administrative launcher/preservation/review remain outside the gate envelope and are labeled separately.

Full parent wait4 high-water81879040 B plus direct-child78229504 B yields conservative lifetime RSS160108544 B. This is not a simultaneous tree peak. Final root **10 files /4 directories**, **925997 logical /954368 allocated B**. Final stored bytes are not a transient storage-peak claim.

The verified saved bundle **SETI_proceskontrol_2026-10-06F_afsluttet.zip** has **579550 B /56 regular entries**, SHA256 **7d768e8397ada5bad119f8b24819652e72177b0fb1d0fadaaad312f9a5c3b054**. Every full archived body was reopened and checked. Its manifest references1458 unchanged base-runtime bodies in the complete saved C archive (189808619 B, SHA256434e5a5d64e9361b591d527608290a0f7443e6b7b0b7543c9d6e9dbad1111b7a); the new F source/payload/guard copies and complete actual evidence are retained here. Restoration does not recreate historical inode custody and supplies no replay permission.

## Explicit wording and scientific limits

The unused freeze metadata field **all_native_imports_forbidden:true** is overbroad literally. Operative protocol and enforced checks prohibit installed NumPy/h5py/hdf5plugin, datasets, installed Python, science, network and installation. Base Python and pinned native stdlib/guard/seal components were used. No zero-C-extension/native-code claim is supported. The field is never read by admission or control validation; frozen bytes are preserved, and independent reviews record this wording limitation. The namespace/counter result is unaffected.

The [original scientific-gate audit](results_radio_proc_io_control_20261006f/AUTHORITATIVE_GATE_AUDIT.md) distinguishes the historical permanently blocked metadata constructor's eleven diagnostic labels from maintained typed production gates. The original requirements include independently complete five-role/native graph/runtime publication, source-shaped22-law/12×16 codec evidence, genuine joined hosted profiles, authentic actual CAS, fresh source/pilot/session/allocation and complete127/24 outcomes. They do not add a prescribed full syscall trace or continuous-namespace mechanism. F supplies one component observation only.

A new **NO_DISPATCHED** codec16 draft retains original calibration epoch1_on metadata/window/chunk159 and all sixteen row indices, maintained normalizer source selections and controlled deterministic construction. It consumes no scientific case or spectrum and reserves no live resources. Independent normalizer extraction and artifact/read envelopes still need a new reviewed executable freeze/outer admission before any actual codec call. One eventual partial handoff cannot claim all twelve handoffs, all22 laws or a scientific certificate.

F's **30s/16MiB artifact** and **528MiB read reservation** are permanently spent, without refund. The selected live engineering reservation subtotal becomes **2800s/5320MiB artifact**, separate from five independent30s/512MiB-process-AS guard controls. There is no automatic successor or plan extension.

HD189733/HIP98505 cadence85030/neighbor9 remains selected; HD1461 HOLD, GJ724 reserve, spectra/112+128 holdouts unopened, native8 unreserved,127/24 NOT ACTIVATED, LS paused, BF untouched, CHEOPS UNSENT. Consolidate **9 October2026**.
