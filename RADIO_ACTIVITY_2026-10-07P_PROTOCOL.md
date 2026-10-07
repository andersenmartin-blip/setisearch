# P: prospective loader ACTIVITY/cookie/startup source scope

Date: 7 October 2026. Authority parent:
`4ab90a06aad2e3c026628bbaca215c23be1e5d2b`. Disposition before implementation:
**SOURCE_ACTIVITY_MODEL_ONLY_NO_NATIVE_ACTIVATION**.

O is complete and is not replayed. This is a distinct source-only continuation
for the explicitly unsupported `la_activity` and cookie/startup semantics. The
protocol and exact five-file context manifest must be published and every full
body read back before P source/tests are created. No M capture, K transfer,
native audit module, target runtime, HDF5/codec handoff, telescope spectrum or
scientific identity is opened. Existing failures, vetoes and budgets are retained.

## API fact and concrete defect

Linux `rtld-audit(7)` specifies that `la_activity` reports link-map activity;
its cookie identifies the object at the head of the link map. ADD begins adding,
DELETE begins removing, and CONSISTENT means the map is consistent again. The
object cookie passed to `la_objopen` is a separately mutable per-object identifier.

N currently emits `(uint64_t)*cookie` as the ACTIVITY generation after replacing
per-object cookies with its own generation values. Source review cannot assume
that this value is always a registered generation, especially during bootstrap
before the head object's `la_objopen`. P must never transmit or interpret a raw
link-map pointer as an object generation.

## Exact new C-source rule

Create a new successor copy; N's original remains unchanged. Each accepted
`la_objopen` stores the **address of its cookie slot** alongside the assigned
generation. `la_activity` compares the callback's cookie-slot address against
those registered slots. It emits:

- generation 0 only while no object generation has yet been registered;
- the matched head generation after registration;
- VETO and process exit for an unknown, ambiguous, null or non-head cookie slot.

Once the unique empty-name main object is registered, later activity must bind
to that main generation. The raw pointer address/value is neither serialized nor
logged. Slot equality is source logic only: without a live callback it does not
authenticate glibc, prove namespace identity, or establish mapped-file custody.

P retains N wire version 2 and the exact 28-byte ACK barrier. Every non-veto
ACTIVITY event still waits for an acknowledgment before callback return. Existing
N bounds and vetoes are not relaxed. Symbol auditing, extra namespaces, relative/
kernel objects, generic constructor coverage and the executable outer remain
unsupported. No C object/shared library may be built or loaded in P.

## Structural activity grammar

Implement a separate pure reducer over exact decoded wire-v2 source records.
It never mutates O/J receipts and never converts an ACTIVITY record into a J
event. It retains each raw record hash/identity and tracks:

1. one handshake;
2. bootstrap `ADD(head=0)` only before the first object registration;
3. one open activity batch at a time: ADD permits object opens only; DELETE
   permits closes only;
4. CONSISTENT must close the current batch, use generation 0 only if the batch
   began in bootstrap and no head exists yet, otherwise bind the registered main;
5. preinit occurs only after a closed initial ADD batch, with the unique live
   main generation, and transitions startup to running;
6. runtime ADD/DELETE and their CONSISTENT marker bind the same main head;
7. EOF/terminal is not supplied by ACTIVITY and remains outside P.

Mixed operations, nested batches, empty runtime batches, activity after poison,
unknown/double close, generation reuse, non-monotonic sequence/time, wrong PID,
unbound post-bootstrap head, main replacement and preinit during an open batch
refuse. Refused raw records, state and incomplete batch remain retained. A
bootstrap ADD may contain the initial object registrations; it must not be
treated as authenticated loader startup.

The reducer's successful fixture receipt may describe complete **structural
activity batches only**. It must set collector authentication, continuous loader/
file coverage, native/runtime qualification, codec/science authority and terminal
qualification false. Public release/dispatch always refuse. P sends no positive
production ACK. Tests may construct already-defined fixture ACK bytes solely to
check identity; this is not a production observer.

## Prospective controls and bounds

Test new risks only: deterministic C derivation and original-N pin, C syntax,
cookie-slot match/bootstrap/unknown/ambiguous/head rules in a pure source model,
initial ADD/open/CONSISTENT/preinit, runtime ADD and DELETE batches, interleaved
or empty batches, missing CONSISTENT, head changes, boolean identities, ordering,
raw-pointer nonserialization, poisoned-state closure, and inability to upgrade a
structural receipt to dispatch. Preserve every input, veto and failed first
implementation cohort; do not rerun unchanged O/N/J suites as new progress.

One source-engineering cohort is bounded at **60 s external wall / 30 CPU s /
256 MiB AS / 96 fds / 16 MiB retained evidence**. A single strict syntax-only C
check may use `-std=c11 -Wall -Wextra -Werror -pedantic -fsyntax-only`; compiler
and headers are administrative, not a native runtime ledger. No C module output,
LD_AUDIT launch, package import or target process is permitted. Record wall/RSS,
logical/allocated evidence and explicit context/source reads separately.

This administrative envelope is not H allocation and does not reset any ledger.
Historical selected spend stays **2,920 s / 5,512 MiB**, plus five separate guard
controls. H's future 600-wall/540-CPU/448-MiB/4-GiB+1-GiB proposal stays unallocated.

## Continuation boundary

Even a passing P source model does not resolve M's actual `ns/pid` EACCES, K's
136 missing authentic members, mapped-inode/content/kernel provenance, collector
origin/own dependencies, constructor and symbol coverage, descendant custody,
terminal IO or a complete current runtime. Do not retry/bypass M or unchanged K
transfers. Before native activation, separately publish and fully read back an
integrated executable outer, authenticated observer and cumulative one-shot
scope. Before spectra, all scientific source/session/recovery/RFI/null gates and
the existing precise frequency/motion/width/identity contract must be satisfied.
The original preparation-contract remains not ready.

HD189733/HIP98505 cadence85030 and neighbor9 remain selected. HD1461 HOLD and
GJ724 reserve remain; no new sequence. Spectra/original112+128 untouched; native8
unreserved;127+24 inactive;M43AI closed;M15/M33 unresolved;LS paused at
LS8BD–LS8BE with LS8BF untouched;CHEOPS UNSENT. No external messages, subagents,
paid service, booking, force-push, evidence deletion or plan extension.
Consolidate **9 October 2026**.

Primary interface reference checked 7 October 2026:
[rtld-audit(7)](https://man7.org/linux/man-pages/man7/rtld-audit.7.html).
It documents the API; it does not certify P or any present runtime.
