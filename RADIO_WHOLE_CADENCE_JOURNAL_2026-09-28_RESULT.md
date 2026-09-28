# Whole-cadence case consumption and durable native archives

28 September 2026. Parent checkpoint:
`4360136e3e083f1567a9dc449c09b1a85b788acd`.
[Prospective scope](RADIO_WHOLE_CADENCE_JOURNAL_2026-09-28_SCOPE.md).
[Complete postflight](results_radio_whole_cadence_journal_2026-09-28/postflight.json).

**51 distinct new tests pass**, together with six explicit crash boundaries.
Two retained mock cadences now have their first complete native score archives,
restored in a separate process with unchanged identities and values. No proposed
Gaussian value, scientific allocation, source request or telescope value was used.

## What is now implemented and verified

`whole_cadence_journal_radio.py` is a separate write-ahead consumption state
machine. It binds ordered case, plan, source, context, law, execution and allocation
identities. It reserves time and evidence quota before returning a process-local
lease, with no refund. CAS publication and exact readback precede permission.
A stale checkpoint, duplicate/skipped case, changed quota, uncertain publication
or incomplete prior case stops execution. No API recreates a consumed lease.
A failed/incomplete case is not a statistical EMPTY and cannot be redrawn.

The implementation preserves immutable revision history in its **local engineering
store**. A scientific adapter must additionally check the remotely published
freeze/allocation, current code/runtime, externally published artifact bytes and
all prior completed evidence. Both per-artifact byte readback and a final external
byte check precede scientific completion. These adapter requirements are tested
with explicit in-memory doubles; **no actual remote scientific adapter is supplied
or qualified here**. Local hashes and scratch are not claimed as publication.

The six [durable crash scenarios](results_radio_whole_cadence_journal_2026-09-28/crash01/result.json)
include five actual child-process exits: before consumption, after consumption,
during an artifact write, after artifact registration and after the final commit
but before its response. Completed data can be read; consumed incomplete data
cannot be executed again or permit a next case. The lost-final-response case
retains its completed evidence. All stores, immutable revisions, process logs
and partial bytes are preserved losslessly in
[the crash archive](results_radio_whole_cadence_journal_2026-09-28/crash01/crash_stores.tar.gz).

`render_gaussian` now has an implementation behind a one-use scientific lease.
It checks the complete six-stream schedule, publication/runtime binding and
case identity before durably registering renderer start, then uses the frozen
PCG64/SeedSequence row order and shared injection/normalization arithmetic.
The tests stop **before constructing a proposed PRNG**. They verify write-ahead
ordering, duplicate rejection, changed plans/runtime and the exclusion of
engineering leases. The successful real-Gaussian path is **not yet qualified**;
this code does not activate the proposal or supply an executable freeze.

## Durable source/score handoff

The [new native handoff](results_radio_whole_cadence_journal_2026-09-28/native01/result.json)
uses only the two normalized mock archives already published in the parent
checkpoint. Original source identities, raw-hash provenance and normalized bytes
are preserved. Their scores had not previously been computed. Each complete
store was computed once, with no renderer, RNG, codec or telescope call:

| Preserved and independently restored | Count |
| --- | ---: |
| Native source identities | 12 |
| Native cache receipts | 96 |
| Normalized source values | 12,582,912 |
| Complete score vectors | 2,592 |
| Score values | 769,824 |

The original un-injected deterministic texture has maximum 7.166114330291748
with 104 eligible cells; the retained width-129 injected mock has maximum
297.71307373046875 with 6,393 eligible cells. These are archive consistency
checks on deterministic mocks, **not a calibration, recovery measurement or
candidate result**. No physical decision/rank/gate was computed from them here.

A separate process reconstituted both `NativeRun`/`ScoreStore` objects and their
complete maxima while RNG, cache construction and score construction were
explicitly disabled. Complete archives include normalized arrays, raw/normalized
source hashes, scopes, all vectors, every vector identity, cache ancestry and
maximum receipts. Raw arrays were not regenerated; raw hashes retain their original
published provenance. This differs from proving a new raw-data normalization.

`whole_cadence_archive_radio.py` also rejects missing/extra/duplicate NPZ members,
wrong layout, pickle/object arrays, nonfinite values, truncated ZIPs and forged
huge NPY shapes **before allocating their declared arrays**. The header guard was
added after the first native run; all four original source/score archives were
checked under the final guard without recomputing any scores.

The native run plus independent restore took 9.0016 s with peak process RSS
84,271,104 bytes and modeled arrays 53,366,656 bytes per cadence. The journal
conservatively retains both full 500,000 ms / 60 MiB engineering reservations:
1,000,000 ms and 120 MiB charged, without refunds, under its 1,200,000 ms /
128 MiB ceiling. Logical case evidence, ledger quota and local immutable revision
history are separately visible. All engineering evidence on disk occupied
4,242,592 bytes at postflight; the complete directory stayed below 128 MiB.

## Qualification boundaries and exact next work

The evidence has four phases: 30 new journal tests; 11 archive plus 5 pre-RNG
guard tests; 3 external artifact guards; and 2 immutable-quota guards. Fourteen
existing renderer tests were rerun because their shared implementation changed,
and two existing success-path tests exercised final guard additions. These
**16 repeated checks are not counted as new tests**. No unexpected test failure
occurred. Initial native code pins and final qualified pins are both retained,
so later guards are not represented as present during earlier fixtures.

These journal/crash/archive fixtures are now **CLOSED**. Do not replay them, the
old codec fixtures, old calibration/development attempt or retained-score diagnosis
as new progress. The next useful work is:

1. Implement and qualify a real external scientific publication adapter: independent
   freeze/allocation readback, exact CAS, transitive current-code/runtime validation,
   durable artifact publication/readback, and restored completed evidence. The
   abstract adapter API and its test doubles are not enough for admission.
2. Bind a resource-feasible scientific archive policy. This engineering archive
   saves all normalized source arrays. Their uncompressed size is 25,165,824 bytes
   per cadence, or **3,800,039,424 bytes across 151**, before scores/reports. It
   therefore cannot be reserved as uncompressed evidence within 1 GiB, and mock
   compression is not evidence of a Gaussian compression ratio. The proposal
   requires complete scores and row/source receipts, not retention of every source
   value after decisions. Specify and test a compact score/receipt archive and
   phase-by-phase reservations without increasing the cap or pretending it can
   reconstruct omitted native arrays.
3. Qualify the actual Gaussian successful path and the full native physical/gate
   chain under a prospective engineering scope, disjoint from reserved scientific
   cases. Preserve exact law/context/source bindings, triggers and all vetoes.
4. Only then publish/read back the integrated executable freeze and charge a
   separately authorized fresh 127/24 allocation before any proposed values.
   The original proposal remains immutable **PROPOSED_NOT_ACTIVATED**.

Cumulative scientific counters are unchanged: development 6 closed; calibration
3 failed/closed; evaluation values/runs 0, one allocation closed; old 24 evaluation
identities unopened/unusable; diagnosis 1 closed; remedies/pilots/new source
requests 0. All 17 historical invariant pins match. Original preparations stay
not-ready, the old acquisition ledger stays exhausted, and telescope admission
still needs a distinct integrated source/acquisition/trial protocol.

HD1461's pointing hold, untouched GJ724 reserve, closed M43AI, original M43AF
holdouts, unresolved M15/M33, paused LS and unsent CHEOPS remain unchanged.
No external messages or plan extension; consolidate on 9 October.
