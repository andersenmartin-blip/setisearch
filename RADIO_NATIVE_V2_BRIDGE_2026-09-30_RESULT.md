# Native-v2 concrete bridge: storage passes; full-size IPC stays closed

30 September 2026. The concrete host-to-worker bridge now handles immutable
requests, a single irreversible host claim, bounded replies and independently
charged durable receipts, runner state and Git projections. **257 Python tests
and 34 JavaScript tests pass.** This is component evidence. No native engineering
case or telescope spectrum was opened, and the production 127/24 protocol remains
NOT ACTIVATED.

## Actual tool boundary and storage correction

A small read-only probe used the actual GitHub connector to fetch an immutable
public commit and the actual execution tool to store and read back its complete
untouched 3,982-byte receipt. Probe01 initially passed receipt readback, but an
independent storage audit found an additional uncharged 3,982-byte `part` copy.
Its initial report, every observed file and the final
**CLOSED_FAILED_STORAGE_AUDIT** classification are retained. Its scope stays
closed. The cause of the unexpected copy was not established.

The corrected store retains one authoritative file throughout its lifetime.
Final markers and file/directory fsync seal that same file; finalization uses no
link, rename, unlink or deletion credit. Unexpected extra files are rejected.
Fresh probe02 passes both exact receipt readback and independent storage audit:
six single-file payloads total 12,300 bytes, exactly matching charged buckets.
All 16,507 file bytes are covered by payload and reserved metadata accounting.
Both probes' raw evidence is retained, including the final supporting reply.
That final reply is known in the caller but its durability is explicitly
unconfirmed. Supporting requests have byte/hash links; this does not assert
complete durable custody of every supporting request envelope.

Real subprocess tests additionally connect the Python worker queue to the
JavaScript adapter, preserve the original Python broker reply and verify raw Git
spool bytes before projection. Expiry, duplicate claims, malformed replies,
storage exhaustion and lost acknowledgements stop without retry.

## Full-size measurements and decisive budget failure

The maximum-size measurements use deterministic alphabet/base64 fixtures,
offline Git and real fsync storage. Connector responses and network fetches are
mocked. The host baseline and Python storage measurement are separate scopes;
their peaks do not establish simultaneous integrated capacity.

| Measured component | Size | Result |
| --- | ---: | --- |
| Actual broker capacity shape | 36,875,057 bytes / 28 files | Local host/storage/readback pass; Node peak RSS 408,920,064 bytes |
| Normalized broker readback | 49,171,168 bytes | Fits the 50,331,648-byte reservation |
| Python storage, original reply receipt and exact 2-MiB state | 186,494,235 stored bytes | Pass; Python peak RSS 268,365,824 bytes |
| Current tool IPC, strict lower bound for one maximum-size case | 3,015 calls / 3,002 custody items | Fails existing 64 calls per case, 512 total calls and 2,048-item limits before dispatch |

The last bound excludes reserve/seal/status/claim and several custody operations,
so adding them cannot repair the failure. No full-size supporting tool call was
dispatched. The bridge's separate prospective support counters do not enlarge
the old runner/broker allocations or qualify execution. The generic 36-MiB host
ceiling also exceeds its 48-MiB normalized reply reservation; this is distinct
from the smaller actual broker capacity shape, whose reservation passes.

Initial PID-namespace sampling mistakes and the pre-storage-fix measurement are
retained separately. Corrected kernel RSS and sampled process totals are labelled
precisely. Brief Git children were not independently RSS-qualified. Easily
compressed fixtures do not establish worst-case Git database disk use.

## Source loading, freeze and continuation

An isolated `-I -S -B` preflight executes the parent's hash-verified bootstrap
buffer, directly compiles pinned Python sources, disables site hooks and uses a
fresh private startup cache prefix. Against the final prospective freeze,
runner and bridge imports pass with 2,256 code/runtime files checked, 253
file-origin modules and 72 builtin/frozen entries. Startup sources and native
extensions have separately stated local identity checks. This assumes a trusted
parent launcher and stable local filesystem; it is not an adversarial native
loader race proof or an execution authority.

The new prospective freeze pins **890 code, 14 input and 1,366 runtime files**.
SHA256: `999b743a915cf3ca0d1645d5b270c48c2e7d1a66ea64bf62939228466dea064c`.
All execution, reservation, RNG, restart and transport qualification flags remain
false. Full evidence is in `results_radio_native_v2_bridge_2026-09-30/`.

**Exact continuation:** replace per-chunk tool IPC with a prospectively bounded
transport that fits the existing allocations, then measure the actual integrated
host/worker/storage path. Propagate the worker deadline inside the broker before
dispatch and close the declared runtime/custody and trusted verifier boundaries.
Only after a new execution-qualified public freeze and its exact readback may a
separate irrevocable reservation authorize the eight fresh cases. Current and
historical prospective freezes cannot grant those permissions.

HD189733/85030 remains selected; HD1461/71139 stays on pointing-provenance HOLD;
GJ724/73005 remains reserve. Spectra and old holdouts stay unopened, LS is paused,
CHEOPS is UNSENT, no external messages were sent, and consolidation remains
9 October without extending the plan. There are no new scientific results.
