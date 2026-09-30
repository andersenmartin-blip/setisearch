# v2 event parent passes; live archive timeout is retained

30 September 2026. **Local parent/event integration PASS; live terminal archive
scope CLOSED FAILED on its prospectively fixed time limit.** A separate read-only
Git recovery confirms every published byte. It does not reverse that failure or
grant restart/scientific admission.

The parent and physical source dispositions intentionally remain FAILED: this
work retains an already incomplete historical report and deterministic software
receiver bytes. It creates no new random values, native scores, receiver
measurements or telescope reads. Repeated software pairs are a serialization
stress load, not independent members or queries.

## Changes and prospective freezes

The new `physical_case_v2_radio` adapter binds v2 to an exclusively consumed
engineering `EventDirectoryStore` parent. Matching case/plan identities, exact
original base-byte inventory, exact closure policy and the tighter parent file
cap are checked before physical writing. Inventory exceptions now poison v2
irreversibly; removing a rejected symlink cannot restore the writer.
Old v1 code and closed results are unchanged.

`event_archive_remote_radio` publishes a terminal engineering snapshot, rather
than a remote execution lease. Original files larger than 256 KiB use ordered
transport pieces; their full original lengths, SHA256 and Git blob identities
are retained. One exact fast-forward commit exposes the archive and manifest.
The protocol rejects namespace reuse, changed parent/tree/bytes, resource excess
and ambiguous acknowledgements. Unknown responses retain reserved charges.

The [contract](RADIO_V2_PARENT_2026-09-30_CONTRACT.md), code and local
[freeze](results_radio_v2_parent_2026-09-30/freeze.json) were published at
`cd37ba829707ab589ca8acfcf0bc0dca34a73bf7`. All 16 new/changed public files were
independently byte-checked before consumption; see
[freeze_readback.json](results_radio_v2_parent_2026-09-30/freeze_readback.json).
The runtime freeze additionally pins every project Python source file.

The concrete [remote freeze](results_radio_v2_parent_2026-09-30/remote_freeze.json)
was published on `main` at `2a6e0c3679cb552dbd00ae02e8bef4caa08502e8`, independently
read back before the publisher opened. This kept the frozen science-branch parent
unchanged. The same exact freeze is retained here. The one remote namespace was
executed once; it is permanently closed after the timeout.

## Local result

| Measurement | Observed |
|---|---:|
| Exact snapshot restoration | 3 / 3 |
| Large snapshots, each | 42,366,912 logical bytes |
| Original journal versions restored | 41 / 41 |
| Complete registered case plus journal | 4,882,416 stored bytes |
| Local worker region | 8.374304 seconds |
| Parent active time through failed closure | 5,328 milliseconds |
| Peak local worker RSS | 214,921,216 bytes |
| Frozen complete case allocation | 18,874,368 bytes |
| Frozen cumulative journal allocation | 8,388,608 bytes |
| Final relevant preflight tests | 146 passed |

The case allocation includes all seven original base artifacts, physical parts,
all checkpoints, physical failure footer, group seal and outer outcome. Both
outer closure reservations and the internal physical footer were protected.
The explicit active-time check prevents expected FAILED closure from hiding
a time overrun. Complete event/pointer history retains every original revision.

The first administrative preflight log records a missing `scripts` import path
in the test invocation. The corrected invocation and subsequent final code
checks pass. All four original logs remain retained; that harness failure is
not hidden or relabelled. The final 146-test count includes 19 new parent and
17 new remote-protocol tests plus existing relevant regressions.

## Live archive result: FAILED on time

The archive was atomically exposed at
`9f2b30ab7323af261b6bd028d37c8d4b5e1d1d77`; update acknowledgement 150 confirmed
the non-forced fast-forward. Exact candidate parent/tree and tree delta had been
checked before that update. The complete archive contains **130 stored files,
4,961,274 bytes**, representing **122 original files** and the manifest/HEAD.
Its [manifest](results_radio_v2_parent_2026-09-30/live01/manifest.json) binds the
physical, base, seal/outcome and all journal/event/pointer bytes.

The worker stopped during immutable readback call 274: the received response
arrived after the fixed **900-second** publisher limit. Actual publisher time
was **901.230029 seconds**; whole worker time was **902.516828 seconds**. There
were 124 file GETs: 123 completed byte checks, then one response accounted on
arrival before the time guard stopped its subsequent byte validation. Six file
GETs and the final branch check were never dispatched. No retry, alternate
namespace or additional publisher was opened.

| Closed live-scope counter | Observed / frozen limit |
|---|---:|
| Git tool calls | 274 / 512 |
| Normalized request JSON | 6,679,426 / 16,777,216 bytes |
| Received/charged normalized response JSON | 6,843,566 / 25,165,824 bytes |
| Unknown response bytes/calls | 0 / 0 |
| Complete tool wrapper frames | 7,816,592 / 67,108,864 bytes |
| Local broker handoff commands | 392 / 3,000 |
| Broker elapsed region | 887.507 / 900 seconds |
| Publisher elapsed region | **901.230029 / 900 seconds — FAILED** |

The broker started after the publisher, so its shorter clock cannot replace
the governing publisher measurement. Normalized replies and complete tool
frames are separate explicitly charged byte domains. Requests, replies, full
tool frames, original errors, counters and both clocks are retained. This
engineering snapshot's latency is not an 80-second native/scientific result.

## Read-only recovery

After closure, an independent Git fetch retrieved the immutable candidate.
`scripts/radio_v2_parent_readonly_audit.py` used one `git cat-file --batch`
operation to verify **all 130 stored files**, including each original length,
SHA256 and Git object identity. It restored all **122 original files**, all
**three exact snapshot streams** and all **41 original journal versions**.
Audit region: **3.604578 seconds**, peak RSS **120,225,792 bytes**.

This recovery makes no Git mutation, writer, lease, allocation, random values,
receiver measurement or telescope read. It is successful byte verification of
a failed live publication scope. The original 900-second failure stays FAILED.

## Complete retained evidence

- [Local result](results_radio_v2_parent_2026-09-30/integration01/result.json)
- [Stopped live result](results_radio_v2_parent_2026-09-30/remote01/result.json)
- [Transport accounting](results_radio_v2_parent_2026-09-30/remote01/transport_receipts.json)
- [Broker accounting](results_radio_v2_parent_2026-09-30/remote01/broker_result.json)
- [Read-only recovery](results_radio_v2_parent_2026-09-30/readonly_recovery01.json)
- [Full original administrative/log/transport archive](results_radio_v2_parent_2026-09-30/admin_archive/manifest.json)

The administrative archive preserves every original request, reply and complete
tool frame, plus freezes, readback receipts, test/run/audit logs and results.
Its manifest pins each original file and each ASCII transport part; decoding
base64, decompressing XZ and reading the tar restores the exact bytes. The
complete original case/journal content is already retained by the live archive
and is not duplicated in that administrative bundle. Administrative package
publication is outside the closed live scope and cannot repair its timing.

## Exact continuation and preserved state

**Next:** qualify bounded batched content publication and grouped independent
immutable readback for this complete archive, with a new prospective scope and
namespace, exact original bytes and unchanged scientific budgets. The measured
serial MCP/RPC path is the present transport obstruction. Do not retry this
closed scope or raise its 900-second cap. Then freeze fresh complete native
physical/resource qualification, with receiver batching, full stage timings,
complete failure evidence and explicit publication during execution. The
terminal archive alone does not supply that runtime integration.

Actual 127/24 validation and a separate telescope acquisition/trial protocol
remain required. **127/24 stays NOT ACTIVATED; the radio pilot has not started.**
HD189733/85030 remains selected, HD1461 HOLD, GJ724 reserve; spectra and old
holdouts stay unopened, LS paused, CHEOPS UNSENT. Every historical failure,
spent identity, counter, threshold and resource limit is retained. No external
messages or scheduled-task changes. Review around 2 October and consolidate
9 October without extension.
