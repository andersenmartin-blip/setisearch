# M mapping/kernel boundary — 6 October 2026

Disposition before the administrative snapshot:
**SOURCE_PLUS_ONE_ADMINISTRATIVE_SELF_SNAPSHOT_NO_TARGET_AUTHORITY**.

Authority parent is `33f543de37ad6e66fac46d35d892024aa7b1776c`. Continue K/L,
without replay, package installation, archive retry, old-ledger reset or target
execution. K's 902 original copied files and 136 unrecovered members are unchanged.
L remains source-only; its kernel-object veto and all native/codec/science gates
are not relaxed. The original preparation contract remains not ready.

M closes a bounded source-level attribution gap. `mapping.py` parses complete
bounded raw Linux maps, ELF64 little-endian x86-64 program headers and auxv. For
each executable PT_LOAD, it requires complete page coverage with exact held-fd
device/inode and file-offset geometry. Writable/shared/anonymous/deleted
executable mappings, gaps, unsupported relocation, overflows, malformed headers,
ambiguous program tables and changed auxv attribution refuse. Literal pathname
equality never substitutes for inode/offset evidence. Raw pathname bytes remain
hex encoded; ambiguous proc spelling is not decoded into filesystem authority.
Only read-only private executable file pages are within this restricted scope.
The held-file ELF prefix is limited to 64 KiB and explicitly not a full-file pin.
Nonexecutable mappings, anonymous BSS and the full native graph are unqualified.

For this administrative process only, exactly one `[vdso]` map must agree with
AT_SYSINFO_EHDR and AT_PAGESZ. Its inode/device/offset must be zero and permissions
r-xp; its full region is at most 64 KiB. Two exact self-memory reads must agree,
with supported ET_DYN/PT_LOAD geometry. The bytes are recorded in hex and pinned.
This does not authenticate the kernel image, a different process, historical
kernel identity, callable symbols or continuous mapped contents. Other kernel
maps (vvar/vvar_vclock/vsyscall) are recorded but never read or admitted. A vDSO
snapshot is not general kernel-object support for L or the target.

`capture_self.py` accepts no PID argument or foreign-process selector. It opens
only its own held `/proc/PID` directory. It binds local PID, proc start-time ticks
and PID-namespace metadata before/after; reads maps/auxv through EOF within caps;
opens the kernel's own exe link for the actual administrative executable; and
preads only the auxv/maps-derived vDSO region of its own mem descriptor. The exe
and PID namespace links are explicit kernel-link exceptions, not general symlink
admission. The copied K target is never opened for execution. Complete raw maps,
auxv, executable prefix, both kernel byte snapshots and failure remnants remain
retained. Selection uses fixed structural metadata, without RNG or scientific
case identities. An access refusal is a closed failed administrative scope, not
permission to retry or change the rules to pass.

Before one actual snapshot, publish source/freeze and independently fetch every
full new body at its immutable commit. Verify bytes/Git blobs. Pass that freeze's
SHA256 to the driver, which rechecks exact source bodies before creating an
exclusive new private output root. Use isolated `python3 -I -S -B`. No target
native package, audit module, telescope spectrum, HDF5 file or holdout is opened.

Distinct administrative envelope: **20 s wall / 10 CPU s / 256 MiB AS / 64 fds /
1 MiB retained artifacts / 4 MiB explicit reads**. Rlimits and external timeout
(2-s kill grace) are active. Per-read/write/wall checks add bounds. Final private
logical/allocated footprint and evidence-preservation reads are reported
separately. Reads are source/freeze, proc metadata, one executable prefix and
two <=64-KiB kernel snapshots. There is no executable outer native freeze,
scientific/native allocation, authenticated descendant monitor or terminal-IO
qualification. No crash resume or second administrative capture is authorized.

64 new source/driver tests pass: 47 invented ELF/maps/auxv/kernel fixtures and
17 source-integrity, EOF, short-read, access-failure, exclusive-output and budget
controls. They never call the actual self snapshot or execute an ELF fixture.
Fixture inputs/logs are retained and explicitly non-native/no scientific identity.

Primary interfaces, checked 6 October 2026:
[maps](https://man7.org/linux/man-pages/man5/proc_pid_maps.5.html),
[auxv](https://man7.org/linux/man-pages/man5/proc_pid_auxv.5.html),
[vDSO](https://man7.org/linux/man-pages/man7/vdso.7.html),
[ELF program loading](https://gabi.xinuos.com/elf/07-pheader.html).
These document interfaces; they do not certify this observer.

Next after the administrative scope: preserve its exact result and limitations,
then join prospective L descriptor events to independently authenticated
same-process mapping/start-time/namespace and kernel witnesses under an explicit
provenance-preserving J/I/H interface. Continuous startup-to-terminal observation,
mapped-byte/constructor/symbol custody, collector own dependencies and terminal
IO remain unqualified. Authentic K remaining bytes and a complete new current
runtime contract are still required before a separately frozen/read-back and
one-shot native qualification activation. Do not infer interval coverage from
two matching snapshots, replay closed controls or tune scientific evaluations.

Historical selected spend remains 2,920 s / 5,512 MiB plus five separate guard
controls; exhausted ledgers remain exhausted. H codec600s/540CPU/448MiB/4GiB+1GiB
remains unallocated. HD189733/HIP98505 cadence85030/neighbor9, HD1461 HOLD,
GJ724 reserve, unopened spectra/original112+128, native8 unreserved,127+24 inactive,
M43AI closed,M15/M33 unresolved,LS paused LS8BD–LS8BE/BF untouched,CHEOPS UNSENT.
No person messages, new targets or plan extension; consolidate 9 October 2026.
