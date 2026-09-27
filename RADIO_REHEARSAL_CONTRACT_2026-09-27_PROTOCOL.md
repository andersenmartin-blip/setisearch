# Prospective GitHub rehearsal contract — 27 September 2026

## Preparation scope

Continue from science commit `8e6400ee1bcfee530780a5fc96491847c05e57b1`.
This is the bounded contract and local journal preparation requested there.
Publish and verify this entire package before considering a live qualification.
It creates **no live namespace, remote grant, telescope reservation or source
permission**. It does not qualify a live adapter or change any science gate.
The original source preparation contract and exhausted demonstration ledger
are immutable inputs. The end of this plan remains **9 October 2026**.

`config/radio_rehearsal_contract_20260927.json` pins twelve inputs, including
the last v2 backend, validator/controller, original source contract, empty
telescope genesis, previous evidence and the connector declarations observed
in this session. `prepared_contract.json` binds the canonical configuration
SHA256 and two inactive, domain-separated genesis templates. These are stored
under the preparation results directory, not the planned live directory.

The planned live model path is exactly
`andersenmartin-blip/setisearch`, branch `m43-support-qualification`,
`results_radio_github_v2_live_rehearsal_2026-09-27_01/model_ledger.json`.
Its namespace is `radio-github-v2-rehearsal-20260927-01`. It cannot alias either
`results_radio_hd1461_live_v2/resource_ledger.json` or the closed demo ledger.
No fallback or automatically incremented namespace is permitted.

The model genesis uses the v2 ledger *shape*, with two new domain-separated
resource/inventory hashes. Its calibration/validation/pilot names and numeric
v2 allowance fields are dummy payload semantics for testing that algorithm.
They identify **no source objects and confer zero telescope allowance**.
The original production `ResourceContract` and fixture-only backend cannot
silently be rebound to this model. A future typed adapter/model binding must
be explicitly implemented and qualified; never spoof its fixture marker.

The separate grant genesis describes the actual prospective engineering budget.
It is empty and inactive. A future live grant must irrevocably debit the entire
named phase before calls in that phase, with fresh UUID4 identity, exact parent,
contract/model identities and immutable read-back. It must survive loss of local
scratch. The local fixture grants in this package are expressly not such grants.

## Finite proposed budget

| Phase | Caller-visible tool invocations | Reserved response UTF-8 bytes | Active wall seconds |
| --- | ---: | ---: | ---: |
| Initialization | 12 | 4,194,304 | 120 |
| Normal append | 44 | 8,388,608 | 300 |
| Deliberately lost-reply append | 44 | 8,388,608 | 300 |
| Read-only recovery | 40 | 8,388,608 | 300 |
| Closure | 20 | 4,194,304 | 180 |
| **Total** | **160** | **33,554,432 (32 MiB)** | **1,200** |

Every call, including failed/ambiguous ones, counts. Reserve its maximum reply
allowance before dispatch; do not refund the unused part after a short reply.
At most 2 MiB is reserved per response, 256 KiB per encoded request and 8 MiB
per local journal. One ordered tree/commit/ref mutation sequence per mutating
phase; `force=false` must be explicit. Reads may occur between the operations.
The recovery phase permits reads only. No automatic retries, refunds, rebases,
second mutation attempt or extra phase is authorized.

These are **caller-visible tool-call/returned-text bounds**, not counts of HTTP
requests, wire-byte bounds, a process-memory limit, or transport cancellation.
The current local implementation measures deadlines before and after a call;
it cannot interrupt a blocked connector call. Late/oversized responses cause a
permanent stop and remain recorded. Granting these numbers now would therefore
be premature. Ordinary code/report publication is outside this future rehearsal
budget and must not be presented as live ledger qualification.

## Observed connector capabilities and unresolved transport terms

The retained `connector_capabilities.json` contains the callable declarations
inspected on 27 September 2026; no live ledger endpoint was probed. GET access to
immutable Git resources and explicit parent/base-tree/`force=false` write
arguments are available. The tools do **not expose** raw HTTP status, caller-set
API version, internal retry policy, pre-decode byte cap, or caller-controlled
transport cancellation/deadline. Their documentation mentions oversized-response
rejection without a numeric limit. Do not invent HTTP 200/201 facts from a
successful tool result, count tool calls as wire requests, or describe observed
tool output as a pre-decode limit.

The previous backend expects `(HTTP status, JSON)` from an isolated provider.
It is not directly compatible with these connector envelopes. A future adapter
must preserve its semantic object/parent/ancestry checks while explicitly typing
success, errors and uncertainty from documented connector results. The previous
HTTP-version/pre-decode obligations are not erased by this new contract. Either
obtain the missing transport controls or prospectively document a separately
bounded connector-only qualification and leave HTTP qualification unclaimed.
No such live activation/disposition is made by this preparation.

## Journal and crash rules

The new `FixtureAttemptJournal` reuses only the existing fsynced hash-chain
storage primitive, with a new replay grammar and Git-call budget semantics.
It requires a declared local fixture provider; it has no connector/credential
path. The fixture declaration is a trusted-code boundary, not a sandbox.

For each call: validate operation and allowance; append and fsync an intent
containing unique call ID, phase attempt UUID4, request and its digest, reserved
reply bytes and monotonic elapsed time; only then invoke the provider. Append
the returned UTF-8 size/hash and acceptance or exception type. Provider failure,
journal error, non-finite/regressed clock, exhausted cap or malformed response
permanently stops that session. Pre-dispatch veto reasons are also journaled
when the journal remains writable; a broken/full journal is never repaired.
Full phase allowance remains spent regardless
of how many calls returned. The phase attempt ID is intended to bind a future
commit message; the fixture journal alone does not verify Git commit contents.

Each local contract/phase directory is exclusive and cannot be reopened, even
with a different attempt UUID. Replay requires a separately retained journal
head and the exact grant; it validates chain, schema, order, limits and outcomes.
It returns **zero dispatch rights**. A pending intent cannot distinguish a crash
before the external side effect from a crash after it. Only the separately
budgeted read-only recovery phase may later inspect remote objects; it may never
reissue the ambiguous operation. Missing checkpoint, torn tail, coherent-prefix
truncation, corruption and incompatible grant all block replay; never repair or
truncate the evidence. A journal fsync failure may leave bytes visible without
a confirmed checkpoint and must remain uncertain.

Local files/fsync establish process-crash behavior only. They do not survive
loss of scratch by guarantee and do not coordinate multiple machines or copies
of a fixture root. Before a live run, remote whole-phase charging/ownership and
checkpoint retention must close that gap, including **bootstrap, confirmation,
recovery and closure calls themselves within the fixed total**. No unmetered
administrative side channel or self-granting recursion is permitted. If this
cannot be implemented within the budget, stop and retain the blocked contract;
do not silently enlarge its caps.

## Future sequence and activation gates

Preparation is immutable and remains `PROSPECTIVE_PREPARATION_ONLY`. A distinct
activation record would need all seven named evidence items: publication
read-back; absence of the separate namespace at a pinned head; qualified remote
whole-phase grants; typed adapter qualification; explicit transport disposition;
durable journal integration; and read-only recovery qualification. Changing
booleans in the preparation file cannot create a permit.

After all gates, a future live sequence would initialize the exact model,
confirm one normal append, attempt one different append with intentionally lost
client reply, inspect its outcome read-only after restart, and publish closure
with every call, trigger and uncertainty retained. Confirmation must preserve
the previous backend's exact blob/sole-parent/sibling and bounded ancestry
checks plus unique attempt identity. Model/calibration/validation are engineering
payload labels only. Neither a pass nor a closure could authorize telescope data.
No live attempt may start after 9 October or automatically roll into a new plan.

## New offline qualification

Test only this changed boundary: domain and cap separation, false-ready refusal,
live-provider refusal, pre-dispatch intent, UTF-8 accounting, no refund, call and
deadline limits, mutation ordering, journal failures, strict replay and actual
child-process exit before/after a simulated side effect. Preserve every attempt,
including failures, as logs and full journal/side-effect/checkpoint bytes. Socket
creation is disabled during these tests. They do not rerun the previous 31 Git
backend tests, old native/codec pipeline, failed scientific panel or source
searches. Publish checksums and exact continuation together with results.
