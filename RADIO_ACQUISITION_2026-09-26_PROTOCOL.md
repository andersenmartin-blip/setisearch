# Radio acquisition continuity — engineering protocol

**Synthetic HTTP only. No telescope access is authorized.** This work continues
the completed native search/control integration. The HD 1461 pointing hold and
all scientific prerequisites remain unchanged.

## Reservation rule

Reserve a complete session's request, payload-byte and time allowances in a
durable revisioned ledger before constructing its network budget. The ledger
binds the source-contract hash, source-inventory hash, cumulative limits and
append-only reservation ancestry. Publishing must compare both the expected
revision and ledger digest. A fresh read must confirm the exact append before
the process can enter the existing transport.

A reservation is irrevocable, even if publication acknowledgment is lost,
the local journal cannot be created, or the process exits without using all its
allowance. A new process always needs a new reservation. There is no permission
to resume an old lease. Completed cached bytes/rows may remain reusable under
the unchanged content-verification rules, but their presence does not refund
the session quota. This deliberately conservative policy prevents workspace
loss from restoring potentially consumed resources.

Within a session, append and fsync a hash-chained request reservation before
the HTTP call. Accepted GET bodies are recorded separately. A failed request
keeps its reserved bytes, including the one-byte response-length probe. HEAD
reserves a request and zero payload bytes. The log binds the scan, URL, window
and extraction scope. Failed requests' exact byte intervals are not supplied
by the unchanged transport's Budget interface; this log does not invent them.
Successful range evidence remains in the existing verified mirror checkpoints.

Time is a per-session monotonic boundary check; the complete allowance remains
charged cumulatively after a crash. It is not a hard process-kill deadline.
Payload-byte quotas exclude headers, TLS and publication-service traffic.
Local request counts describe reservations made before HTTP, which may exceed
actual attempts if a failure occurs before sending. Unknown crashed usage is
bounded by its fully charged lease, never reported as measured zero.

Journals cannot be silently reset, truncated or repaired. Read-only replay
requires an independently retained final hash and reservation. A hash chain
alone cannot detect rollback if its trusted head is also replaced. The durable
publication store, current revision and append-only compare-and-swap are the
authority; local files do not substitute for them.

## Predeclared publication-backed demonstration

The exact illustrative limits and expected outcomes are in
`config/radio_acquisition_engineering_20260926.json`. Publish its genesis ledger
and this protocol before running the demonstration. This is a test namespace;
its six-request/200-byte/60-second total is not a future telescope quota.

1. Start one worker process. Through the authorized GitHub connector, append
   and verify its full 3-request/100-byte/30-second reservation. Enter the actual
   radio transport with simulated HEAD and four-byte GET replies. Terminate
   with `os._exit(73)` without a session-end event.
2. Start a separate process from the current published ledger. It must debit a
   second complete session, then execute the same two simulated HTTP calls and
   close its journal normally. The cumulative charged allowance is exhausted.
3. Start a third process. It must stop before publication of another lease or
   any source HTTP call. No automatic refund or larger quota is allowed.

`radio_acquisition_worker.py` exchanges only read/publish JSON messages with
`radio_acquisition_controller.js`, run in Work Mode code mode. The controller
reads the actual branch HEAD and ledger at that immutable commit, creates one
child commit and uses a non-forced ref update. Its permitted path is restricted
to the synthetic ledger. No credential is passed to the worker. The subsequent
fresh read is part of the activation gate. The final publication retains both
actual journals, publication revisions and all three process outcomes.

The independent local test panel additionally covers durable-store restoration
after deleting a work directory; uncertain acknowledgment; stale/false
publication; changed source/checkpoint identity; corrupt, rolled-back and torn
journals; request/byte/time exhaustion; failed fsync; and unchanged HD 1461 gates.
The local test store is explicitly marked `local-fixture` and cannot authorize
the telescope entry point. Existing detector/codec tests are not rerun as new
scientific results.

## Live-data boundary

`start_source_session` checks the existing scientific gates before consulting
the publication store. A future source contract must pin the new code/policy,
runtime, cumulative and session budgets and exact GitHub reservation location.
Its ledger must bind that same contract and six-source inventory. The checked
contract remains preparation-only, so no live acquisition session is opened.

The fixture controller is deliberately restricted to its demonstration ledger.
A source-specific controller location and prospective protocol still need to be
frozen and reviewed before telescope use. This engineering proof supplies
neither pointing provenance, a motion model, a new source calibration nor
scientific validation. M43AF reserved inputs, closed M43AI and paused LS remain
untouched. Continue from the exact source-provenance requirement in project status.
