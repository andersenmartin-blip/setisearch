# L restricted descriptor collector source — 6 October 2026

Disposition: **RESTRICTED_COLLECTOR_SOURCE_NO_NATIVE_OBSERVATION**.

Continue J and the actual K partial recovery; both original authorities and
closed results remain unchanged. This source component implements Linux/x86-64
glibc audit callbacks and a stdlib receiver of actual SCM_RIGHTS descriptors.
It supplies no native launcher, binary, activation, executable outer freeze or
runtime/scientific allocation. J's manufactured event chain is not authenticated
by this new component and is not silently reinterpreted as live observations.

`audit_collector.c` implements la_version, la_objopen, la_preinit, la_objclose
and la_activity. A fixed future inherited SOCK_SEQPACKET endpoint is fd198.
One process, version2, base namespace only, 256 unreused generations, 4,096
events and names shorter than 1,024 UTF8 bytes are supported. Child-side held
descriptors are not released at unload; SCM_RIGHTS duplicates let a future parent
retain them beyond unload/EOF/exit. Reentrant/concurrent callback entry, changed
PID, full channel, unsupported object/namespace/path, bad cookie, identity drift
or cap conditions terminate with nonzero exit. A queued veto is sent when
possible; outer EOF/reaping must detect all other termination/loss conditions.
The fixed channel and held descriptors require a future explicit descriptor
envelope and authenticated launch; none is allocated here.

Wire format is explicitly little endian, not C struct padding: 100-byte header
`<4sHHIIQQQQQQIIQQQHH`, then exact loader-name/resolved-path bytes. Fields are
magic RLA1, wire version1, kind, sequence, local PID, generation, namespace,
load base, device, inode, file bytes, mode, flags, mtime_ns, ctime_ns,
monotonic_ns, loader-name length and resolved-path length. Kinds1..6 are handshake,
open, preinit, close, veto and activity. Only an open carries exactly one fd.
Version2 is a handshake flag. Non-open object/file fields are zero. No in-band
hash or self-reported PID authenticates event origin.

`receiver.py` retains every received raw frame and refusal, validates packet and
ancillary boundaries, closes all refused descriptors, checks monotonic sequence
and process identity, and hashes a held regular fd with pread against exact
prospective file pins. It retains accepted descriptors through close and EOF;
one terminal receipt also requires an exact separately supplied successful wait.
No offset is consumed. Bad startup, wrong wait, modified files, truncation,
duplicate generations, fd count/identity/hash errors and post-failure resumption
refuse. The bounded frame stream is 8 MiB and explicit fd reads 1 GiB. The
current implementation is synchronous and has no hard outer lifetime bound or
durable live-event journal; those must be supplied by a future qualified outer.

Crucial gaps: a callback newly opens a pathname; its fd is not the loader's
original mapping fd. Therefore matching fd bytes do **not** prove which inode
the loader mapped. The namespace/process start-time witness, callback origin,
kernel mapping/IO correlation, intermediate content immutability, collector's
own audit-namespace dependencies, symbol activity, constructor ordering and
process/descendant/terminal-IO coverage remain unqualified. Activity-cookie
ordering is also unobserved; unknown cookies are refused. Kernel pseudo-objects
including linux-vdso.so.1 and extra namespaces are explicitly unsupported and
vetoed. Consequently this restricted source cannot claim generic real glibc
startup support or full native coverage. No native load has tested these gaps.

Validation here is administrative only: isolated stdlib tests use fabricated
frames over real local sockets and ordinary temporary bytes. They never execute
an ELF fixture or callback module. All per-test fabricated frames, refusals and
generation metadata are retained in TRANSPORT_FIXTURES-1.json and marked as
non-native / no scientific identity. C syntax validation uses `-fsyntax-only`;
no object/shared library is produced or loaded. Each of two compiler checks had
20-s external wall, 18-s child timeout, 15 CPU s, 256 MiB AS, 64 fds and 1 MiB
per output file. Compiler/header reads are opaque administrative reads and are
not a certified runtime read ledger. Retain the failed compiler source/logs.

Primary API references, checked 6 October 2026:
[Linux man-pages rtld-audit](https://man7.org/linux/man-pages/man7/rtld-audit.7.html),
[UNIX SCM_RIGHTS](https://man7.org/linux/man-pages/man7/unix.7.html),
[recvmsg boundary flags](https://man7.org/linux/man-pages/man3/recvmsg.3p.html).
These establish interfaces, not correctness/qualification of this source.

Next: obtain K's authentic remaining inputs under a new complete current-storage
contract; independently review/complete L's actual kernel pseudo-object and
mapping/startup/terminal/descriptor boundary plus the provenance-preserving J/I/H
interface. Only a separately published executable outer freeze, independent
full public preread and one-shot activation can allocate a bounded native
qualification control. No native experiment is proposed as already ready.
Do not replay G/K/J or reset old ledgers. All science/source/motion/fresh identity,
recovery/RFI/null and codec gates remain pending. Primary neighbor9 and all target,
holdout, M43AI, M15/M33, LS/CHEOPS dispositions remain unchanged. Consolidate
9 October; no plan extension, new targets or external messages.
