# Radio continuation — durable acquisition accounting

**Ten local tests pass, and the actual GitHub-backed crash/restart demonstration
passes.** A fresh process cannot restore an earlier process's acquisition quota.
The HD 1461 source remains blocked; no telescope request or spectral read occurs.

This completes the acquisition-continuity step after the
[native search/control integration](RADIO_PIPELINE_2026-09-26_RESULT.md).
The [engineering protocol](RADIO_ACQUISITION_2026-09-26_PROTOCOL.md), code and
genesis test ledger were published before the demonstration at commit
`3fde45184835c53aa26b1184f3e2ab92c308c20c`.

## Implemented behavior

`acquisition_radio.py` adds a publication-backed reservation ledger and a
transport-compatible session budget. Before a process can make source requests,
the publication service must durably append its complete request, payload-byte
and time allowance, then return that exact ledger on a fresh read. The ledger
binds the source contract, inventory, cumulative limits and reservation ancestry.
An expected-revision/content check and a non-forced Git update prevent a stale
writer from replacing newer accounting.

Each session also writes an exclusive, fsynced, hash-chained local journal before
every request. Successful GET bodies are recorded separately. Failed requests
retain their reservation; crashes, uncertain acknowledgments and unused quotas
are never automatically refunded. New processes need new reservations. Old
session journals can be inspected, but cannot reactivate an old permission to
make requests.

The existing source reader, transport validation, range checkpoints, native
normalization and detector algorithms are unchanged. The new source entry point
checks the existing scientific gates before consulting the publication store.
It requires new code, policy, runtime, cumulative-limit and publication-location
pins in any future live contract. The actual HD 1461 preparation contract stops
before store access or acquisition.

## Actual publication-backed result

The worker used the real radio transport with **simulated** source HTTP replies.
GitHub publication and verification were real, using the connected authorized
application. Three separate worker processes were started; this was not three
calls within one persistent Budget object.

| Process | Actual behavior | Local source requests | Accepted fixture bytes | Cumulative quota charged |
|---|---|---:|---:|---|
| 1 | Reservation verified; explicit process termination with exit 73; no session-end event | 2 simulated | 4 | 3 requests, 100 bytes, 30 s |
| 2 | New reservation verified; normal completion | 2 simulated | 4 | 6 requests, 200 bytes, 60 s |
| 3 | Refused because cumulative reservation allowance was exhausted | 0 | 0 | Unchanged |

The first reservation was committed at
`56979fb0f90d57f6c15f6dd429ad86369a87be70`; the second at
`6a5a687eeae9ea02bc7c4b9bccedac0c759590cf`.
Both were read back before the worker reached its simulated HTTP boundary.
An additional attempt to publish from the first writer's old revision was
rejected; the two-reservation ledger remained intact.

The charged 6-request/200-byte/60-second allowance is deliberately conservative.
Measured use in this demonstration was four simulated requests and eight
accepted bytes, with ten bytes reserved locally including response-length
probes. The unused portion is still charged. These are illustrative test
allowances, not HD 1461 resource limits or measured telescope traffic.

## Local failure checks and evidence

The ten tests additionally cover deletion of a worker directory while retaining
the separate durable store; reconstruction from that store; uncertain publication
acknowledgment; stale or false publication replies; invalid source/ledger identity;
request, byte and time exhaustion; failed fsync; duplicate/invalid body acceptance;
corrupt, rolled-back or torn journals; and the actual HD 1461 gate.
Final review added an extraction-boundary recheck of the cumulative/session
limits, policy and code pin, so a caller cannot supply a generically created
session with different total limits. Its negative test stops before extraction.
This guard was added after the recorded demonstration; the original demonstrated
implementation remains pinned by its freeze commit. The reservation/transport
path exercised by that demonstration is unchanged. All ten current tests pass
under Python 3.12.14 on Linux.

The retained result directory contains the actual test log and test evidence,
original genesis, final published ledger, both process journals, complete
controller/worker exchanges, process exit outcomes, code hashes and an offline
audit. The audit verifies publication order, exact reservation ancestry, both
journal hashes, the exhaustion refusal and continued source blocking. All
publication revisions remain inspectable in Git history.

```bash
PYTHONPATH=src:scripts python scripts/radio_acquisition_qualification.py
sha256sum -c RESULTS_MANIFEST_RADIO_ACQUISITION_2026-09-26.sha256
```

Reproduction runs local tests and audits the retained publication evidence; it
does not issue new GitHub reservations or telescope requests. Fresh test runs
generate different session identifiers, timestamps and duration logs, so their
new evidence hashes need not match this retained run. The closed, exhausted
demonstration ledger must not be reset to make another run fit.

## Scope and next work

The publication-store adapter is a trust boundary. Its reads must address the
current remote revision and its writes must enforce compare-and-swap. A local
hash chain cannot by itself detect an attacker or operator replacing both a
journal and its trusted head. The fixture controller is restricted to its exact
test ledger; a live location still needs to be pinned in a new source contract.

Request/payload reservations are bounded before sending. Time is checked at
operation boundaries and is not a hard process-kill limit; a native library
may overrun a deadline before control returns. Byte quotas exclude headers,
TLS and GitHub traffic. Failed requests' exact byte intervals are unavailable
at the unchanged Budget handoff; their scan/window and reserved size remain
recorded. The implementation does not manufacture missing evidence.

**Scientific readiness is unchanged: HOLD_POINTING_PROVENANCE_UNRESOLVED.**
The next authorized preparation is a source-specific metadata/motion-context
audit and prospective protocol. Keep raw-header and catalogue coordinates
separately identified while their discrepancy is unresolved. Do not silently
choose a corrected pointing, inherit toy calibration settings, substitute a
target or open spectra. A new same-scan original header/log or documented
file-specific conversion remains the exact missing scientific observable.

The eight native-integration tests and seven earlier source/codec tests remain
separate completed evidence. No detector qualification, physical false-alarm
rate, new astronomical candidate or sensitivity claim is added here. M43AF's
112+128 reserved inputs, closed M43AI results, earlier radio dispositions and
the paused LS branch remain preserved. The existing daily continuation remains
the scheduled route through 9 October; no duplicate task was created.
