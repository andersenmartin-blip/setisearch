# Local transport qualification, 30 September 2026

The unchanged Python Publisher and Worker completed two fresh transport
fixtures at the full 26 MiB source ceiling. The first publication and its
sibling both restored every original byte, checked the complete Git tree
delta, and confirmed the final parent and branch head. Each used 52 shared
operations against the unchanged 64-operation allocation. These are offline
transport fixtures; no telescope spectra, case RNG or native reservations were
used, and scientific execution remains closed.

## Concrete implementation

The pinned local Node controller authenticates immutable Git metadata, computes
the candidate tree independently, fetches the candidate commit before the
nonforced ref update, and retains the grouped Git readback locally. Python
receives a sealed file projection rather than a 49 MiB tool response. Large
outgoing arguments are a view into the sole sealed Worker request. Supporting
read envelopes retain every observed field and are reconstructed against that
file and the independently observed full-envelope SHA256. Both the outgoing
request receipt and supporting receipt batch now stream through source-only
Python helpers. No second large request file or all-fragment string array is
needed.

The offline component's structural bound is 56 operations per case and 448 over
eight cases, using 960 KiB extraction fragments. The configured live04 network
path adds one mandatory capability process: 57 and 456 respectively. Extra actual courier polls
are counted separately; this bound does not qualify an actual eight-case run.
The old 64/512-operation,
48/64-MiB per-case request/response, 30-second Worker and 600-second case
limits remain unchanged. Local Git process wrappers are labelled explicitly
and are conservatively counted; they are not represented as tool envelopes.
The new accounting schema is consequently distinct from the old Runner schema.

## Measurements and retained negative evidence

The final full-size fixture used deterministic SHA256-counter bytes and
completed two publications in 62.101 seconds. Node peak self RSS was
281,448,448 bytes and Publisher Python peak self RSS 422,404,096 bytes, each
below 512 MiB. The independently sampled simultaneous family peak was
715,882,496 bytes, including Node, Publisher and a claim helper. This aggregate
is still unqualified; the historical 512 MiB limit applies to process self RSS,
so the aggregate measurement is not a claim that that limit was exceeded.

The entire isolated fixture occupied 647,909,835 logical and 653,045,760
allocated bytes, including its Git object database, source copies, receipts,
projections and logs. Git database storage is reported separately in the
inventory and has no inferred free allocation. These measurements cover two
fixtures and do not qualify eight cases or actual network Git timing.

The earlier periodic full-size fixture and its larger RSS are retained. A
small fixture closed on the Store's duplicate-or-uncharged-file refusal;
the unexpected filename was not observed and its cause remains unknown.
A later small fixture passed, but its initial Node-only sampler is explicitly
invalid as aggregate evidence. No closed scope was resumed.

Actual tool probes returned 1 MiB of deterministic high-entropy ASCII intact
and uploaded 8,650,752 bytes through one raw-TTY stdin call in 2.743 seconds.
The latter upload's sealed payload SHA256 was independently read back. Its
service subsequently closed on the idle command deadline; that terminal
failure and reservations are retained. These boundary probes do not qualify
the complete courier. A separate local 64 MiB stdio fixture passed in 0.597
seconds; it is not an actual tool throughput measurement.

The established metadata-only Python suites passed 299 tests; the new fixture
tests are retained separately. Three additional launcher regression tests bring
the scoped Python total to 305. Final JavaScript suites passed 97 tests.
An additional broad historical discovery ran 1,036 tests and failed with 108
errors and two old acquisition-pin assertion failures. Missing historical
artifacts and h5py are recorded in that log; this release does not claim that
all repository tests pass. No raw telescope data was fetched to fill those gaps.

## Prospective freeze and next control

The fresh live04 prospective runtime freeze pins 903 code, 16 input and 1,366 runtime
files. Its SHA256 is
`cede229b78f79aee8b460694e262701808e671a4632347566294c6786ae4c6c0`.
Its inputs include the network selection policy and public TLS certificate.
The preceding live01/live02/live03 freezes are retained separately.
Fresh local source preflight passed for all five Node modules and 184 Python
source imports; the largest launcher argument was 70,308 bytes. The fresh
startup cache remained empty and all 903 code and 16 input pins were reverified. The earlier
source-drift refusal is also preserved. Every execution, reservation, RNG,
restart and transport-integration authority flag remains false.

The live01 actual control closed before any connector dispatch: the controller
emitted its first head request, but the manual handoff exhausted the unchanged
30-second Worker deadline. Its full startup/poll responses, Store markers and
unknown reservations are retained. Its namespace and private Store cannot be reused.

The live02 actual control also closed before any connector dispatch. The
controller polled a Store that did not exist: Publisher consumes an existing
Store and never creates it. No Store or durable STOPPED marker existed in this
scope, so no durable shutdown is claimed. Both complete SDK responses and the
private start plan are retained. The controller now awaits exclusive,
source-qualified durable Store creation before starting Publisher or polling;
existing paths are rejected before helper dispatch. Regression tests cover
the wait barrier and a real Node/Python empty-Store poll and reuse refusal.
The client also preserves a valid failure reason when stderr accompanies it.

Live03 reached three actual connector calls and created tree
`10932aec46cd9462d8f67798a92b1d3acb5c67a8` and candidate commit
`9041ff761b18000832eb976a3c6834bcc56c216e`. The candidate fetch then failed
with `Could not resolve host: github.com`: the isolated child environment
omitted the execution environment's proxy. No ref update was dispatched.
Its 17 SDK calls, all 172 local scope files, complete failure receipt and
durable STOPPED marker are retained. Seven durable SDK receipts match the
caller byte for byte. Idle polls and the last delivery remain only in the
caller trace; the host retains a distinct unknown acknowledgement reservation.

Separate diagnostics proved credential-free loopback HTTPS proxy routing with
TLS verification and a pinned public CA. The proxy port changes per tool
invocation, so the launcher validates only the current HTTPS_PROXY against a
public policy and binds its exact value into the process receipt. Arbitrary
environment variables are not inherited. Local metadata Git retains its
isolated environment. The frozen Git 2.51.1 probe retrieved exactly three
requested archive blobs (88,514 bytes), one commit and 843 trees. No historical
blob payload was read. The first system-Git probe is retained separately.

Live04 requires an incoming protocol-v2 filtering capability transcript during
prepare_transport, before its first connector. Both candidate and post-update
fetches use blob:none/depth=1 plus only the exact frozen archive blob IDs;
unsupported filtering closes the scope. Capability preflight has its own
unchanged 30-second Worker operation. Its additional local process is counted:
60 actual SDK calls plus four conservative Git processes fit the existing 64
allocation. This is a trusted-endpoint capability check, not a hostile-server
or complete eight-case qualification.

Git's filtered URL fetch would otherwise register a promisor remote by changing
local configuration. A separate frozen-Git probe proved that pre-registering
the exact public URL and blob:none filter keeps both config and config.worktree
byte-identical through capability, fetch and inventory. That data preparation
was completed before the controller snapshot; strict metadata checks remain.

The separate live04 prospective plan permits one 64 KiB deterministic archive
under a fresh namespace, after immutable public code/freeze readback. A single
awaited portable client automates startup, source extraction, connector calls
and deliveries, with extra polls counted before dispatch. Its cap covers the
nested SDK calls and four conservative local Git processes; the surrounding
functions.exec/wait orchestration and courier V8 RSS remain unqualified.
It grants no native-case authority. Its result will be retained separately;
live04 has not run in this prospective publication. The controller reports its last supporting
acknowledgement as unconfirmed and does not claim durable late-envelope custody
after Store shutdown.

Before native execution, the complete actual shared transcript, a versioned
Runner accounting contract, eight-case runtime/storage qualification, and
independent public execution-freeze and irrevocable reservation verification
must be established. The scientific 127/24 protocol is not activated. The
radio plan still ends on 9 October; there is no extension or external contact.

Evidence: `results_radio_native_v2_local_transport_2026-09-30/`.
