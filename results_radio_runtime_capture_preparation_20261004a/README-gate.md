# Prospective metadata capture gate

`capture_gate.py` is a new engineering observer. It does not reopen a closed CAS
attempt, start telescope acquisition, run calibration or validation cases, open
HDF5 datasets, install packages, or issue a scientific certificate. Importing the
module dispatches nothing. A real invocation requires a separately frozen raw
supervisor contract, a complete immutable source readback supplied by the
caller, and a fresh marker-only activation. The caller's independently supplied
raw hashes are trust inputs; hashes in a collector result never become trust
anchors.

The observed scope remains distinct from the original source/science authority
snapshot. Every field in `authority` is false. A separately admitted engineering
capture sets `engineering_capture_authorized` and
`engineering_reservation_spent` true, and records the actual child dispatch
count. Spending remains permanent if a dependency is missing or the child
fails. There is no retry, resume, refund, automatic successor, or marker deletion
operation.

## Frozen inputs

The exact supervisor contract keys are declared in `CONTRACT_KEYS`. Its fixed
namespace accepts `metadata-capture-only` or the explicit, disjoint test domain
`synthetic-test-fixture`. The public scientific evidence domain is refused.
Paths are absolute and canonical. Source and runtime inventories are separately
sorted, have no duplicate paths, and bind exact file length, SHA256, and Unix
permission bits. The guard, collector, collector contract, and original plan
must be source pins. The resolved Python executable must be a runtime pin and
must also be the running parent's actual interpreter. The parent and child run
with `-I -B -S`.

The output directory is a fresh, empty directory with mode `0700`. Its device,
inode, and mode are external contract pins. The gate holds its directory file
descriptor, verifies held/named identity, and uses fixed member names for all
writes and accounting. A spent basename may not collide with an evidence
member. Regular source/runtime files are read through held, nonsymlink ancestor
directories; sole-link identity, named identity, permissions, and modification
state are checked around each read.

The exact detached proof keys are declared in `PROOF_KEYS`. The supplied proof
binds preparation commit/tree, activation commit/tree, sole preparation parent,
the sole changed activation path, capture identity, supervisor and collector
contract hashes, plan hash, and activation bytes. `publication_files` contains
the complete source inventory's full bytes encoded as strict base64, together
with original repository path and intrinsic Git blob ID. Every length, SHA256,
and Git blob is rechecked. The local marker must equal the externally pinned
immutable marker bytes.

The proof's claimed service provenance is supplied and externally pinned by the
caller. This local gate does not itself make authenticated network calls or
prove service provenance. The caller must verify actual commit parentage,
tree/delta metadata, and immutable full file contents before supplying the
proof's raw hash. Ordinary reference publication is not scientific atomic CAS
qualification. A proof manufactured from local result flags is insufficient.

The preparation contract contains no own publication commit/tree or activation
hash, avoiding circular hashes. The post-publication proof is copied exactly
into `admission-witness.json` with mode `0644`; it supplies detached bindings to
the child. All other evidence members are created exclusively with mode `0600`.

## Finite reservation and observations

The maximum engineering reservation is 60 seconds, 8 MiB of artifacts, a
512 MiB direct-child address-space limit, and 256 MiB of selected explicit
parent/child reads. The child interval is at most 50 seconds, with a separate
reap allowance of at most five seconds. Smaller prospective limits are allowed.
The child contract's pinned read allowance is reserved from the joined read
ceiling before admission. Known two-pass source/runtime reads plus terminal
headroom must fit the parent's remaining allowance before spending.

The spent file is exclusive, `O_NOFOLLOW`, and fsynced together with the held
directory before launch. The gate starts one child in a new process group with
closed inherited descriptors, no standard input, a narrow environment, and
fixed command arguments. It retains exact received stdout/stderr. A stream cap,
deadline, sampled descendant, sampled RSS excess, or read limit causes closure
and process-group termination. Reaping uses `wait4(..., WNOHANG)` under fixed
deadlines, including exceptional paths. There is no unbounded waiting fallback.

The result is accepted only when the child is reaped with exit code zero,
selected source/runtime pins remain equal, and stdout contains the expected
metadata observation schema with matching capture, contract, and plan hashes,
all authority flags false, and finite selected read accounting. Missing HDF5
packages can still yield a completed metadata observation whose scientific
admission status remains pending.

Procfs status/stat bytes are finite ephemeral observations, preserved with
sample times. They are not subjected to an impossible sealed-file lifetime
claim. Aggregate read cap failures propagate; process disappearance is recorded
or ignored as an unavailable sample. Namespace PID mappings are observed before
the child process group is counted. The final scope records exact members,
permission bits, logical lengths, and observed allocated storage.

The result explicitly distinguishes direct-child `wait4` peak RSS from sampled
process observations and the parent's process-lifetime `ru_maxrss` at a selected
call. None certifies a complete capture-scope or host peak. Selected explicit
read accounting excludes implicit Python/dynamic-loader/kernel reads. Procfs
samples do not establish absence between samples. A stream cap failure preserves
the exact received prefix and does not certify the unread suffix. The report is
an engineering observation, not a completed source, host, codec, or scientific
closure certificate.

## Validation and retained development evidence

`test_capture_gate.py` invokes only fresh, disjoint synthetic child scripts in
temporary directories. It never invokes `collector.py`, imports HDF5 packages,
reads telescope data, or uses a previous closed identity. The final retained
suite contains 24 passing checks, including full raw receipt preservation,
irreversible spend, source and marker drift, immutable fullcontent mismatch,
directory replacement, forbidden domain and schema fields, joined read
reservation, exact stderr on nonzero exit, empty-result rejection, deadline
termination/reaping, raw stream overflow, source modification, hardlink and
ancestor-symlink rejection, duplicate JSON keys, the running parent interpreter,
cross-contract identity, observed descendant termination, and a nonsuppressed
procfs read cap.

All development logs remain public. Two earlier source/test snapshots and their
logs are retained under `development-gate-failure-01/` and
`development-gate-failure-02/`. The first retained suite log is partial; the
second records a transient positive-fixture failure without its specific
supervisor diagnostic. Their cause is not retrospectively proved. A separate
bounded procfs reader now respects the ephemeral nature of those observations;
the final test includes an assertion diagnostic. Only
`final-gate-tests-04.log`, ending `Ran 24 tests` and `OK`, is the final passing
suite. These synthetic tests do not constitute an actual runtime observation or
authenticate remote publication.
