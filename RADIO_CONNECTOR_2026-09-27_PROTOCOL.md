# Typed connector and ownership integration — 27 September 2026

## Scope and unchanged contract

Continue from science commit `ef0827036b16952808a09a65bad910b3e29577e9`.
This protocol documents offline implementation and qualification alongside its
results. It is not a preregistered sky evaluation or permission to activate the
prospective live rehearsal. The original preparation contract, inactive model
and grant genesis, five phase limits, expiry, source contract, closed synthetic
ledger and empty telescope ledger remain unchanged.

The new config pins fourteen inputs, including the previous backend, local
journal, pure validators, preparation file and connector declarations. One
read-only call to the project's own immutable public Git commit supplies an
actual GET tool envelope. Its full response is retained, with a separate
ordinary-project-metadata accounting line; it is not a live ledger operation.
Write envelope forms are based on the callable interfaces and successful
ordinary publication responses already observed, then exercised with fixtures.

No source spectrum, original RAW/FIL payload, fresh scientific control, failed
evaluation or M43AF holdout is read. The previous 31-test backend and 25-test
journal studies are not rerun unchanged. Tests concern the newly composed
connector/journal/admission boundary and its newly exposed failure modes.

## Typed connector semantics

`ConnectorReply` distinguishes a returned Git object, an object identity and a
reference-update acknowledgement. `http_status`, `api_version` and
`internal_attempts` remain null. No REST status code is synthesized from a tool
success envelope. Require `isError` to be exactly false and a typed
`structuredContent` payload; text-only success, integer-as-boolean flags,
missing payloads, duplicate JSON keys and inconsistent duplicated GET content
are rejected. A tool error after a side effect remains uncertain, not proof
that nothing happened.

The mapping uses the explicitly pinned repository/branch/model path:

| Algorithm operation | Connector operation | Accepted semantic result |
| --- | --- | --- |
| Immutable object/ref GET | `github_fetch` with exact API URL | Strict JSON object inside returned text |
| Create tree | `github_create_tree` with explicit base tree and entries | Git object identity |
| Create commit | `github_create_commit` with one explicit parent | Git object identity |
| Fast-forward update | `github_update_ref`, explicit `force=false` | Acknowledgement only |

`ConnectorModelStore` has an explicit constructor for the separate engineering
model and accepts only the new local connector fixture through a journal. It
does not invoke the production `ResourceContract`, pretend a live connector is
the old REST fixture, or alter the original backend. The frozen pure Git
object/blob/path/sibling/ledger/ancestry methods are reused with the new binding.

The new publication method still permits exactly one append and verifies the
caller-held head/digest, unchanged sibling files, blob content and sole parent.
It binds the phase grant's UUID4 into the commit message and **reads back the
exact message**, so a connector dropping that uniqueness field cannot silently
collapse two attempts. A minimal `success=true` update reply is never expanded
into an invented ref/target response. Immutable candidate content and bounded
current-head ancestry must independently confirm the write. An acknowledgement
without a landed commit is insufficient.

Each connector call goes through the existing fsynced local attempt journal.
The fixture reserves 65,536 bytes for the entire canonical tool-result envelope
per call, including wrapper fields, and counts all calls across read/publish
operations within one phase. This is a fixed local qualification allowance,
not evidence that a real repository inventory fits it. The inherited algorithm's
per-operation counters never reset the enclosing phase allowance. Journal
`accepted` records byte/time acceptance; typed semantic acceptance is separate
and its vetoes are retained in the store evidence.

## Independent admission fixture and its explicit assumption

The fixture authority is a separate SQLite database with full synchronous
transactions. It exists **before** a test worker's first connector call. It
irrevocably charges an entire phase once, maintains unique phase ownership and
atomically debits each call before the simulated connector runs. The authority
and its phase state survive replacement of the client instance and local client
directory. Copying a serialized grant cannot restore an active owner channel.
A new authority instance still sees the spent phase. An abandoned owner can
only become uncertain, never unspent; a distinct read-only recovery phase may
inspect the model without reissuing a mutation.

This is a **supplied independent authority model**, not a remotely implemented
GitHub grant system. The local SQL setup, grant operations and server-side
abandon action are fixture assumptions. They may not be implemented as free
administrative GitHub calls or claimed as qualified live bootstrap/closure.
Positive tests prove the composition conditional on this primitive; they do
not establish that it exists in the current runtime. No live connector callable,
credential path, initializer or grant constructor is added.

The five whole-phase charges still sum to the fixed 160 tool calls / 32 MiB
returned-text allowance / 1,200 seconds. The full-charge fixture exhausts those
numbers without issuing source rights. Actual model append/recovery paths use
only their allotted phase budgets. The fixture's modeled charging does not
prove hard interruption of an in-flight call or pre-decode network limits.

## Bootstrap counterexample and transport disposition

The published rehearsal requires a durable full-phase charge before every call
in that phase, including initialization, confirmation, recovery and closure.
Under these explicit conditions:

1. No independently durable admission state initially exists.
2. The connector is the only means of creating that state.
3. Every connector call requires the prior durable admission.

there is no admissible first connector call. A journal in disposable client
scratch cannot supply the missing independently durable state after that scratch
is lost. This is a dependency argument under those assumptions, not a claim
that bounded distributed execution is impossible with an external coordinator.

To demonstrate the practical hole in weakening condition 3, a deliberately
unsafe baseline allows its first branch GET before recording a grant. Each
simulated restart discards client state immediately after that GET. Actual
local bare-Git reads leave the branch and grant state unchanged. **Thirteen**
such reads exceed the 12-call initialization allowance; **161** exceed the
entire 160-call envelope, still with zero durable grants. The full call/response
traces are retained. These are fixture restart-policy traces, not actual process
crashes or live traffic. The protected path refuses to run without its explicit
independent fixture admission primitive.

Disposition: **live bootstrap remains blocked**. Required new evidence is an
independently durable, exclusive admission mechanism present before the first
rehearsal call, with accounted provisioning, one-owner semantics, whole-phase
charging and loss-of-client-state behavior. Its provisioning and recovery must
fit an explicit approved accounting boundary; it cannot be hidden as ordinary
publication. An alternative would require an explicit prospective contract
change; none is made here and no existing ledger may be reset.

The connector still does not expose HTTP status/version, internal retries,
numeric pre-decode bounds or cancellation. The typed implementation qualifies
only the visible envelope semantics offline. HTTP transport, hard wall deadlines
and wire-byte bounds remain unqualified. No flag in the old preparation is
rewritten to ready, no new automatic attempt is issued and no namespace starts.

## Retention and publication

Disable Python socket creation during qualification. Preserve all connector and
underlying service exchanges, journals, model receipts, vetoes, owner snapshots,
negative traces, Git objects (including orphans), source snapshots and runtime
hashes. Verify every archived Git object after decompression. Distinguish ordinary
project metadata reads, simulated protected calls, deliberately unsafe baseline
calls, live ledger requests and source requests in the result.

Publish the package and checksum manifest on `m43-support-qualification`, and a
README overview on `main`, each from a verified parent with `force=false`. End
this engineering item with its explicit missing primitive, rather than another
automatic round of unchanged bootstrap/journal tests. Preserve the plan's
9 October closure, source selection and every earlier scientific disposition.
