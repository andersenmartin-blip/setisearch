# N: callback acknowledgment barrier source; no live observer or dispatch

Date: 6 October 2026. Disposition **SOURCE_COMPONENT_NO_NATIVE_ACTIVATION**.
N follows [M's closed namespace-access refusal](RADIO_MAPPING_KERNEL_2026-10-06M_RESULT.md)
and the immutable K/L checkpoint `33f543de37ad6e66fac46d35d892024aa7b1776c`.
Neither original failed scope nor historical preparation-contract is rewritten.

## Concrete change

L queues an event and returns, permitting unload before the consumer checks the
mapping. N creates a separate pinned successor source with **event wire version
2** and an exact 28-byte event/PID/generation acknowledgment. Each successful
non-veto event send is followed by a bounded wait before callback return. Missing,
malformed, truncated, mismatched or negative acknowledgments fail closed. The
original L source is unchanged; its unsupported objects/namespace/symbol/phase
limits remain. There is no silent old-wire compatibility layer.

[New C source](results_radio_callback_barrier_source_20261006n/audit_collector.c)
is 8,917 B, SHA256
`659ff8b2f3cbc325731a6c39361c224cc3d23cc8bef23789b54d4b21b3fdcf85`.
[The exact delta](results_radio_callback_barrier_source_20261006n/source-delta.patch)
and [original L pin](results_radio_callback_barrier_source_20261006n/L_BASE_SOURCE_PIN.json)
are retained. The [Python channel component](results_radio_callback_barrier_source_20261006n/acknowledgment.py)
retains raw acknowledgments/vetoes, closes received descriptors and refuses any
attempt to resume a failed or completed wait. `release()` and `dispatch()`
**always refuse**, even after a matching fixture acknowledgment. A positive
production observer is absent.

## Verification and resource evidence

**33 final source controls pass**, including an independent literal ACK ABI,
wrong process/sequence/generation/version/kind, rejection, deadline, peer close,
trailing/truncated packets, SCM_RIGHTS cleanup, normal record-boundary flags,
unknown flags, closed-state refusal and public positive-release refusal. The
producer-thread test checks that a next fabricated socket event cannot advance
before acknowledgment. It does not execute a real native callback. Both the
initial 31-control record and final 33-control record are preserved; these are
33 distinct controls, not 64 new independent trials.

A single strict C **syntax-only** check passes (`-std=c11 -Wall -Wextra -Werror
-pedantic -fsyntax-only`): **0.022723867999957292 s / 10,112 KiB child peak RSS**.
No object/shared library was built, module loaded, callback observed, native
target executed or codec budget reserved. Administrative compiler/header reads
are opaque and cannot qualify runtime read accounting. See
[syntax receipt](results_radio_callback_barrier_source_20261006n/syntax-1.json),
[final controls](results_radio_callback_barrier_source_20261006n/ACK_FIXTURES-2.json),
[final test log](results_radio_callback_barrier_source_20261006n/tests-final.stderr.log),
[source review](results_radio_callback_barrier_source_20261006n/SOURCE_REVIEW.json)
and [freeze](results_radio_callback_barrier_source_20261006n/SOURCE_FREEZE.json).

## What remains unresolved

ACK bytes do not authenticate the peer or collector, attribute the mapped inode,
pin full contents, qualify the audit module's own dependencies, kernel pseudo
objects, constructor order, process/descendant custody or terminal IO. Blocking
one callback does not stop other threads/direct munmap/mprotect or prove continuous
mapped contents. Real callback behavior and C error exits remain unobserved;
syntax checking and manufactured Python packets cannot substitute for them.
Unsupported generic startup and L activity-cookie semantics remain unqualified.

The per-callback deadline is two seconds with poll's millisecond rounding; it
does not extend H's future whole-run cap. Future observer waits and work must fit
that cap. H's 600-wall/540-CPU/448-MiB/4-GiB+1-GiB remains unallocated and
historical selected spend stays **2,920 s / 5,512 MiB** plus separate guard controls.
M remains closed with real `ns/pid` EACCES and zero downstream metadata/memory
reads. K still lacks 136 original members. No access bypass or retry is authorized
by this source result.

Exact continuation: source-only version-2 J/I/H integration, if useful, requires
its own prospective interface scope retaining all refusals and closed dispatch.
For native work obtain the missing authentic original bytes and permitted
namespace/observer capability, then qualify the complete current-runtime and
mapping/kernel/startup/terminal boundary. Separately publish/read back the
integrated executable outer with cumulative budgets before one bounded native
qualification. Do not replay unchanged controls or convert source receipts to
runtime/scientific readiness. The integrated scientific protocol and telescope
opening gates remain unsatisfied.

HD189733/neighbor9 remains selected; HD1461 HOLD/GJ724 reserve remain, no new
sequence selected. Spectra/112+128 untouched; native8 unreserved;127+24 inactive;
M43AI closed;M15/M33 unresolved;LS paused/BF untouched;CHEOPS UNSENT. No external
messages and no plan extension. Consolidate **9 October 2026**.
