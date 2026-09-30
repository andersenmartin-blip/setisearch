# Fresh native-v2 stage chain and durable transport receipts pass

30 September 2026. **PASS for the fresh stage bindings and durable transport
receipt component.** No case was reserved or executed.

`native_v2_chain_radio.py` supplies the previously missing namespace-specific
render, threshold, physical and evaluation functions. It reconstructs every
plan from the fresh v2 parent, writes a durable v2 start marker before the first
PRNG constructor, and refuses a second entry. Freeze or historical-identity
failure occurs before that marker and before RNG construction.

Four ordered fresh reference receipts produce a separately named
`UNCALIBRATED_ENGINEERING_ONLY` threshold with denominator 5, minimum possible
rank p=0.2 and the unchanged 1/100 gate explicitly unavailable. The physical
stage requires a distinct evaluation case, that exact threshold and a fresh
compressed evidence writer. It delegates to the complete native physical
arithmetic while retaining all eight v2 stage boundaries. Truth association is
performed only after immutable physical decisions and cannot issue a scientific
candidate.

The broker now also provides `DurableInvoker`. It canonicalizes and bounds the
request before calling transport, passes the untouched returned object to a
durable sink immediately after return, and only then parses and accounts for the
response. The sink's exact byte count and SHA256 must match. A bad request,
uncertain transport, failed receipt write or bad receipt permanently stops the
adapter; no second call is permitted. Existing function-style transports remain
compatible.

**246 tests pass** across five new chain tests, three new durable-invoker tests
and the adjacent v2 parent/broker, compressed evidence, physical parent,
event-store, terminal archive, journal, physical arithmetic, old native chain,
receiver batch/adapter and native receipt-bridge suites. The new tests prove
durable start ordering, pre-RNG collision/freeze stops, fresh reference order,
physical-writer binding, empty null/on gate behavior, raw receipt ordering,
preflight-before-call and permanent no-retry behavior. Python compilation also
passes.

This is not yet the complete executable runner. The remaining orchestrator must
bind one public freeze and reservation to the eight fixed cases, write compact
base evidence, create and close the v2 physical case for both reference and
evaluation roles, publish each terminal case plus cumulative journal through a
single `CumulativeBroker(DurableInvoker(...))`, and refuse the next case until
that publication/readback succeeds. Failure/interruption at every boundary must
close the allocation without retry.

**Exact continuation:** implement and deterministically test that orchestration,
including reference-only completed physical snapshots, terminal map extraction,
broker pin derivation and all stage/cumulative time/RSS/byte receipts. Then
generate a new complete runner+broker runtime freeze, publish it and independently
read back every pinned code/input/runtime identity. The historical prepare-only
freeze remains unchanged and non-executable. Only after the new freeze passes
may a separate immutable eight-case reservation be considered.

No reservation, lease, RNG, score, receiver computation, telescope/spectrum
read or scientific disposition occurred. 127/24 remains **NOT ACTIVATED**.
HD189733/85030 remains selected; HD1461/71139 remains on pointing-provenance
HOLD; GJ724/73005 remains reserve. Old holdouts are unopened, all failures and
spent identities persist, LS is paused and CHEOPS remains UNSENT.

