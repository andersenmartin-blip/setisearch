# Distinct inert proxy integration — 5 October 2026

Status: **SIMULATION_ONLY / PENDING_ACTUAL_NATIVE_CUSTODY**. This is a new code
preparation cohort. Original bootstrap A remains immutable **CLOSED_FAILED**;
there is no retry, activation, allocation, live connection/request, package
installation/import, native scientific execution, new live identity or holdout
opening. No accepted transcript qualifies a scientific result.

`proxy_opener.make_opener` authenticates the complete unchanged original plan
through `proxy_contract.prepare`, extracts all three official pinned wheel specs
and permits only their exact original URLs. It accepts only a canonical numeric
loopback HTTP proxy. All trust, connect, TLS, HTTP and deadline dependencies are
mandatory; the adapter has no socket, DNS, ambient environment or default SSL
context loader. `wheel_io.py` is an exact unchanged dependency. Its default direct
HTTPS loader is never selected: all integration tests explicitly inject this
opener and additionally test that the default path is blocked.

Trust bytes are read through the injected bounded reader with a precharged +1
probe and must match their exact pinned length/hash **before** any connection.
The descriptor and observed pin do not authenticate where those trust bytes
originated. Tests use clearly synthetic text, not an actual certificate.

CONNECT reads one byte per receive, refreshes the finite remaining timeout before
every send/receive, retains returned bytes before checking the post-operation
deadline and does not use `makefile` or read ahead into the tunnel. Original
16KiB/4096-byte/64-field bounds and conservative requested-byte precharges apply.
The distinct dependency copy fixes the prior parser's last-receive deadline gap
and requires the status-code trailing space. The predecessor source/report stays
historical. Preparation receipt wording now correctly states that it authenticates
the raw plan hash; the adapter separately parses and binds the official wheels.

TLS receives an immutable configuration requiring the exact
`files.pythonhosted.org` peer/SNI, hostname checking, CERT_REQUIRED, TLS1.2 minimum,
HTTP/1.1 ALPN and observed pinned trust bytes. Injected factories register
closable resources before fallible operations and register returned resources.
All registered sockets/responses are closed in reverse order on every visible
failure and on final response closure; cleanup failure prevents success. A spent
or reentrant call has its own refusal receipt and cannot overwrite the first
attempt's evidence or close an active first handle.

`native_bindings.build_native_bindings` supplies compact prospective stdlib-shaped
connect/TLS functions from explicitly supplied socket/SSL modules. Building the
functions performs no native operations. When invoked, they use only AF_INET
numeric loopback, `SSLContext(PROTOCOL_TLS_CLIENT)`, explicit pinned ASCII PEM
`cadata`, CERT_REQUIRED and hostname checking, deferred wrapping, registration
before the handshake, timeout refresh and exact HTTP/1.1 ALPN. Tests inject fake
modules exclusively. Invoking these functions with real modules would require
a distinct admitted scope; it has not happened here.

The pure injected `bounded_http_binding` performs bounded HTTP/1.1 header reads
without buffering and exposes raw prefixes and bounded body reads to unchanged
`acquire_wheel`. Existing status, sole Content-Length, encoding/redirect, exact
archive hash and held/named exclusive-file guards remain in that dependency.
Its exact +1 oversize body is written and retained before refusal. A deadline
crossing body receive that cannot be returned to the wheel writer is separately
retained in the failure receipt and counted once in actual received bytes.
Successful body counts remain owned by unchanged `wheel_io`, avoiding double count.

The new deterministic 1.0 pure Python test wheel and `synthetic-plan.json` are
explicitly separate fixtures. `make_simulation_opener` still authenticates the
original plan anchor and marks fixture use separately. They do not replace any
original package/version/URL/length/hash selection. `build_fixture.py` regenerates
the exact archive without importing or installing its inert payload.
`synthetic-wheel.whl.base64` preserves the binary fixture for UTF-8 publication;
`source-pins.json` binds its decoded length, SHA-256 and Git blob identity.

Validation: **40 tests** in `tests-04.log`, including changed original plan and URL
substitution, trust mismatch, finite deadlines, per-syscall timeout refresh,
fragmented receives, no CONNECT read-ahead, status/framing/oversize refusals,
partial factory failures, immutable TLS configuration, fake native handshake/ALPN
failures, raw prefixes, exact/short/hash-mismatched/+1 wheel bodies, static archive
preflight, failed-body actual accounting, repeated calls and cleanup exceptions.
Earlier 34-, 35- and 39-test passing logs are retained as development stages, not
additional final-test counts. Independent review found two initial bugs despite
the first passing stage: second-call evidence overwrite and failed body receive
accounting. Their source snapshot remains in `retained-failure-01`. A subsequent
custom-response handler issue is fixed by retaining the budget explicitly and
has a dedicated test. Independent review reproductions/snapshots are preserved
by the root publication cohort.

`simulation-receipts.json` retains one successful synthetic wheel receipt,
the corresponding unqualified transport receipt, a raw 407 CONNECT refusal and
a deadline-crossing raw body refusal. It records zero live operations explicitly.

Limits remain exact: injected Python bindings can violate their declared contract;
overreturned observed bytes are evidence/refusal, not proof of a lower-level cap.
No native socket ownership, TLS ciphertext/loader IO, kernel buffering, actual
peer certificate/hostname validation, trust provenance, wall-clock/peak-resource
custody, crash durability, current proxy reachability or runtime qualification is
certified. Frozen source/runtime/trust inputs, fresh root, complete resource
accounting and single-use live admission remain pending. This work changes no
scientific dispositions or reservations and cannot authorize an actual successor.
