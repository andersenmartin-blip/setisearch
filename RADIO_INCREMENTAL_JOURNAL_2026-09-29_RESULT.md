# Incremental durable journal: two live engineering probes pass and close

29 September 2026. **Both fixed live probes pass and close; the complete scope
fails its literal publication/verification operation cap.** The independent audit
verifies all four actual Git branch advances, every changed file, all six original
journal revisions and the fixed artifact. Its 41 local Git calls alone exceed
the separately stated 32-operation overhead cap. This failure is retained and
not retroactively repaired. No scientific experiment or telescope observation
was run. Both namespaces are permanently closed.

The [prospective scope](RADIO_INCREMENTAL_JOURNAL_2026-09-29_SCOPE.md), code,
29 Python risk tests, four broker checks, runtime freeze and both untouched
genesis records were public at `e496fc3fc89223c7e8dcb83a576250f30484c366` before
the live worker began. Its tree exactly matches the prepared local tree.
The local preparation commit `d9b20bb7` is a provenance identity, not the public
freeze commit; the worker used the actual public commit above. All 849 pinned
code/input files and 1,132 runtime files matched before and after execution.

## Observed outcomes

| Fixed namespace | Actual outcome | Original versions verified | End-to-end time |
|---|---|---:|---:|
| complete01 | Consumption, fixed artifact and completion published; fresh reader verifies all bytes | 4 | 86.932355 s |
| lost01 | Consumption published; injected acknowledgement loss stops writer; fresh read-only client confirms incomplete consumed state | 2 | 39.545042 s |

The lost response was deliberately injected at the **application/session
boundary after a successful GitHub update response**. It was not a naturally
occurring outage and did not kill the remote service. The actual success reply
remains in the transcript. After the last update (request 76), all nine remaining
requests were read-only. No artifact or completion was created for lost01;
its consumption and 120,000-ms / 4,096-byte reservation remain spent. It cannot
resume. This expected incomplete state is a successful fault-containment test,
not a completed data-analysis case or an EMPTY scientific result.

The normal 217-byte witness and its receipt were committed atomically. Every
mutation preserved all unrelated Git entries; there was no overwrite, forced
update, conflict recovery or retry. Offline fault tests cover those additional
risks, but this live run did not deliberately introduce a concurrent writer.

## Exact archive accounting

The representation keeps genesis once, each event once, and the small pointer
for **every historical version**. The independent audit derives these counts
from immutable Git bytes, not the publisher's own accounting implementation.

| Namespace | Genesis | Event records | All pointer versions | Total journal | Full-snapshot comparison |
|---|---:|---:|---:|---:|---:|
| complete01 | 1,118 | 2,477 | 1,632 | 5,227 | 7,741 |
| lost01 | 1,114 | 1,090 | 816 | 3,020 | 2,970 |
| Total | 2,232 | 3,567 | 2,448 | **8,247** | **10,711** |

All numbers are canonical bytes. Add 217 artifact bytes for **8,464 actual
journal/artifact bytes** across both namespaces. The short incomplete history
is 50 bytes larger than its full-snapshot comparison; the representation is
not claimed to save space for every small history. These measurements do not
qualify the proposed 151-case 8-MiB ledger allowance or describe Git-pack size.
Every original snapshot digest and length reconstructs exactly; prior archived
histories and all their charges remain unchanged.

## Resources and timing limitation

The combined worker, including fresh readers, took **169.958322 s**. It used
**85 GitHub calls**, 19,821 canonical request JSON bytes and 2,679,360 canonical
response JSON bytes. Peak RSS was **73,068,544 bytes**. Both 120-second session
limits and the 600-second / 240-call / 4-MiB request / 16-MiB response / 512-MiB
live ceilings passed. These limits were not increased after execution.

Calls comprised 49 Git metadata reads, 24 immutable file reads, and four each
of tree creation, commit creation and fast-forward update. Measured tool time
totals 47.719 s; the broker took 169.347 s. The difference includes handoff,
local work and verification, not a controlled attribution of latency.

**Scientific 40/80-second per-case timing remains unqualified.** Even this
small normal archive took 86.932355 s, and it includes no Gaussian generation,
native scoring, physical vetoes or recovery/RFI/null evaluation. The old 127/24
proposal remains NOT ACTIVATED. An engineering pass cannot silently enlarge
its scientific ceilings or certify a full integrated run.

## Publication/verification overhead failure

The scope separately limited publication/verification overhead to **32 Git
operations/tool calls**. The independent downstream audit invoked local Git
**41 times**: 21 calls to check the four exact deltas, one ancestry-list call,
and 19 calls to reconstruct the two histories and their inventories. That is a
proven lower bound for the whole overhead phase; it excludes freeze publication,
other readback, and closure filing. The scope did not exempt local Git calls.
Therefore the **complete overhead cap failed**, even though both live probes,
their 85-request live budget and all byte/state checks passed.

The worker's original `CLOSED_ENGINEERING_PASS` status is preserved as its
live-only output. The separate `disposition.json` records the narrower final
conclusion and the overhead failure. No threshold or cap was increased, and no
closed probe was repeated to manufacture a passing whole-scope result. Future
integrated work should batch local immutable-object reads as well as remote
reads and explicitly count both kinds prospectively.

A separate administrative closure allowance permits only preserving this known
failure, its exact already-generated evidence and associated README update:
at most 16 further GitHub calls, 16 local Git process invocations and 180 seconds
active filing/verification time. It grants no experiment, namespace, RNG, retry,
science allocation or correction of the failed historical budget. Filing is
covered by the owner's explicit package/log publication approval.

## Evidence and publication

[Complete evidence](results_radio_incremental_journal_2026-09-29) includes the
original worker result, every transport receipt, broker timings, preflight,
independent Git/JSON audit, exact scope and code. The complete lossless
`transport_frames.tar.xz.b64` archive retains **175 files / 2,707,041 original
bytes** in **80,045 stored ASCII bytes**. All members were decoded and compared
byte for byte before publication. Its manifest gives every original SHA-256.
Four temporary response duplicates are retained and verified identical to their
delivered responses; they are included in the physical transcript byte count.

The independent downstream auditor is
`scripts/radio_incremental_journal_postflight.py`. It imports no publisher,
journal, reader or codec implementation. Decode the ASCII/XZ/TAR archive into
an empty directory, then pass that directory with `--rpc` and an output path
with `--output`. This rechecks retained evidence only; it does not restart a
closed live worker or generate experiment values.

The earlier automatic approval rejections are retained as historical records.
The owner explicitly approved the package and logs/results in this conversation.
The initial CLI push then lacked Git credentials; publication used the connected
GitHub tools and was read back independently with Git and the immutable file
reader. A sparse checkout temporarily omitted four already-pinned metadata/input
files after switching branches. They were restored from the unchanged public
freeze before the first live call; no input or prospective rule changed.

## Exact continuation

This incremental storage scope is closed with the overhead failure above.
Its functional evidence remains useful but is not a whole-scope budget pass.
**Do not replay complete01 or
lost01, reset their reservations, or reopen older transport/Gaussian scopes.**
Carry forward the measured successful bytes and the unresolved timing limit.

Prepare the separately bounded integrated Gaussian same-law reference/native
physical/recovery/RFI/null engineering stage with fresh identities. As part of
that integration, bind the already-qualified immutable batch reader to the
incremental journal and prospectively define atomic event/artifact bundles to
reduce the measured round trips. Consumption must still become durable before
work; a lost or conflicting publication must still stop with read-only recovery.
Count all original revision/checkpoint obligations, physical artifacts, framing,
failure evidence and cumulative phase resources before mutation. Do not infer
that small-case compression or these engineering time caps make 151 cases fit.

Production thresholds need their actual 127 same-law reference maxima; old
deterministic fixtures cannot be relabelled. Freeze the new engineering recipe,
exact runtime, motion/width and numerical-transfer inputs before any RNG. Keep
the reserved scientific 127/24 identities untouched and its proposal inactive.

Primary neighbor9, selected HD189733/85030, HD1461 pointing hold, untouched GJ724,
closed M43AI failure, original M43AF 112+128 unopened, M15/M33 unresolved, LS pause
at LS8BD–LS8BE, LS8BF untouched and CHEOPS UNSENT all persist. No telescope values,
source requests, external messages, new target sequence or plan extension.
Consolidate on 9 October.
