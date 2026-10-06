# N: source-only callback acknowledgment scope and future constraints

Date: 6 October 2026. Authority context: K/L checkpoint
`33f543de37ad6e66fac46d35d892024aa7b1776c`; M administrative source prerequisite
`35430dcf9018614a12239604b703a35379de24c4`. This is a distinct source engineering
scope after M's single refused administrative measurement. M is closed and its
rules, source freeze and failure are not modified. No further M operation is
authorized by N. No native target, audit-module build/load, compiler output
module, scientific identity, spectrum, allocation or activation is authorized.
This engineering record, source and controls are published together after the
controls; no prepublication test registration is claimed. A future native scope
still requires its own prospective published/read-back contract before use.

## Concrete race and scope

L queues an event and returns from the callback. A later consumer can encounter
an object after it has already been unloaded. N changes a **new** copy of the
restricted C source to wait for an exact acknowledgment after each successfully
sent non-veto event, before returning from that callback. This is a source-level
mechanism, not evidence that the C callback ran or that a live mapping was held.
The original L source remains unchanged. N does not weaken L's kernel-object,
namespace, path, phase, file, identity, object-count or symbol restrictions.

`build_successor.py` first verifies L's original 6,816-byte SHA256
`d4ab251c65caeeb28eb84706c89ce4c959da2f8c5235920061069abeee135551` and requires
one occurrence of every maintained replacement. It writes exclusive new outputs.
It must not overwrite an existing C file. The final source and evidence are
hashed in `SOURCE_FREEZE.json`; no changes are made to an observed failed scope.

## Wire boundary

N uses event wire **version 2**, retaining the 100-byte little-endian event
header and bounded name/path fields. It refuses L's version 1; J/L consumers
cannot silently interpret N as an old collector stream. The packet framing
check is not the complete object/namespace/content validator.

The acknowledgment is exactly 28 bytes, little-endian:

| Offset | Width | Meaning |
| --- | --- | --- |
| 0 | 4 | Magic `RACK` |
| 4 | 2 | Version, exactly 2 |
| 6 | 2 | Exact event kind |
| 8 | 4 | Exact event sequence |
| 12 | 4 | Exact emitting PID |
| 16 | 8 | Exact object generation |
| 24 | 4 | Decision: 0 veto; 1 fixture approval |

The event sequence must be below 4,096, kind 1 through 6, PID nonzero, generation
at most 256. Python fixture constructors reject booleans and non-integer
identities. A matching byte packet does **not** authenticate an observer.
`release()` and `dispatch()` always refuse, including after fixture success.
The only public production direction implemented is a negative acknowledgment.

The C source waits with nonblocking `recvmsg` and a monotonic deadline of two
seconds per callback, using `poll` with millisecond rounding. This is a scheduling
deadline, not a proven hard real-time maximum. EINTR/EAGAIN may retry within that
same deadline. Short, oversized, truncated, unknown-flag, wrong-event, wrong-PID,
wrong-generation, wrong-version and peer-close conditions exit 125; a matching
negative decision exits 126. Ordinary MSG_EOR is permitted. ACK ancillary data
is unsupported and produces a truncation/refusal with zero C control capacity.
VETO packets are retained and do not wait. The existing callback lock is held
until acknowledgment; recursion/concurrency remains refused.

The Python source fixture uses a real local AF_UNIX/SOCK_SEQPACKET pair and
bounded waits at most two seconds. It closes any received SCM_RIGHTS descriptors
on both success and failure, refuses ancillary/truncation/unknown receive flags,
allows normal MSG_EOR/MSG_CMSG_CLOEXEC, and cannot resume a closed/failed barrier.
Its raw acknowledgments and failure states are retained. No synthetic packet is
relabeled as an actual callback observation.

## Source validation and future resource boundary

Validate the documented ABI with an independent literal byte packet, manufactured
process/event/generation mismatches, veto, deadline, peer-close, length/version,
descriptor custody, normal boundary flag and unknown flag controls. Use a
fabricated producer thread over the real socket to check that the next
fabricated event cannot be emitted before the matching acknowledgment. This
does not execute the C module, prove loader scheduling or authenticate a peer.
Preserve every fixture and test log, including earlier runs before additional
flag controls. Do not repeat unchanged controls as new progress.

One distinct syntax-only administrative C check is permitted: `-std=c11 -Wall
-Wextra -Werror -pedantic -fsyntax-only`. Its inherited administrative bounds are
20 seconds external wall, 18 seconds child timeout, 15 CPU seconds, 256 MiB
address space, 64 descriptors and 1 MiB per output file. No object/shared library
may be built or loaded. Compiler/header reads are opaque administrative reads,
not qualified runtime accounting. Source tests use manufactured frames and no
scientific identities. Runtime and storage observations from these controls must
not be charged as native/scientific budget or used to reset a closed ledger.

For a future executable outer, callback waits must fit the **existing whole-run
cap**, including the observer's work. Two seconds multiplied by an event cap is
not an authorized extension. H's 600-wall/540-CPU/448-MiB/4-GiB+1-GiB proposal
stays unallocated. Historical selected spend stays 2,920 seconds / 5,512 MiB,
with the five separately retained guard controls. No old acquisition ledger,
failed evaluation or preparation-contract status changes.

## Explicit unresolved boundary

An ACK cannot establish which file inode the loader mapped, full file contents,
kernel pseudo-object coverage, the collector's origin or own dependencies,
constructor ordering, process namespace identity, descendant custody or terminal
IO. Callback blocking alone does not stop other threads or direct munmap/mprotect
and does not prove continuous content identity. Real C callbacks, errno/syscall
behavior and C negative/truncation exits have only syntax evidence here. L's
activity-cookie behavior and unsupported generic startup remain unqualified.
This C source is not a general runnable Linux audit collector.

M's actual `ns/pid` read was denied before maps/auxv/executable/vDSO reads.
Obtaining authorized same-process namespace metadata and an independent,
authenticated mapping/process observer is a concrete missing runtime capability;
this scope must not bypass that access requirement. K's 136 unrecovered original
members are a separate missing input. Neither packet matching nor a partial
recovered directory can substitute for them.

Next useful source work, if undertaken, must prospectively specify an explicit
version-2 J/I/H interface with retained refusal evidence and closed dispatch.
It cannot turn a self-reported trace or source freeze into coverage/authentication.
Before any actual native activation, independently qualify original-byte current
storage/runtime, kernel/mapping/startup/terminal coverage and observer identity;
publish and fully read back a distinct integrated executable outer freeze with
fresh cumulative budgets and exactly one bounded activation. All science gates
remain closed; no telescope spectra or original holdouts are opened by N.
Consolidate the current two-week plan on 9 October without extending it.

Interface references, consulted 6 October 2026: Linux man-pages
[poll(2)](https://man7.org/linux/man-pages/man2/poll.2.html),
[recvmsg(2)](https://man7.org/linux/man-pages/man2/recvmsg.2.html), and the
previously pinned L rtld-audit/UNIX transport references. These describe APIs;
they do not certify this implementation or present execution access.
