# Inert hosted scientific callback preparation

This bundle connects the six exact `ScientificGitStore` callback shapes to an
injected synthetic Git service. It performs no live network, credential access,
workflow creation, allocation, activation, telescope access or scientific case.
The default constructor refuses; `public-scientific-evidence` refuses before any
injected callback. The only accepted domain is explicitly
`synthetic-test-fixture`. No qualification certificate producer exists.

The code directory is
`results_radio_hosted_scientific_callback_preparation_20261004a`. Its simulated
owned Git prefix is separately fixed to
`results_radio_scientific_callback_preparation_20261004a`.

## Exact callback boundary

| Operation | Required result |
| --- | --- |
| `read_ref` | repository, branch, commit |
| `read_commit` | sha, original raw data bytes |
| `read_tree` | sha, truncated=false, complete immediate entries |
| `create_candidate` | commit, tree |
| `read_immutable_file` | repository, commit, root tree, path, regular mode, blob, byte count, raw data |
| `atomic_ref_compare_and_swap` | repository, branch, expected revision, commit, atomic=true, accepted=true |

HTTP receives `{method,path,body}` and returns `{status,data}`. A separate raw Git
reader receives `{repository,commit}` and returns `{sha,data}`. Existing signed
headers, timestamps and timezone bytes come from that reader and must reproduce
the requested intrinsic Git commit hash. REST metadata is never used to guess
the original parent bytes.

The journal callback receives bounded records before dispatch and after replies.
Its exact acknowledgement seals the record digest. The caller must provide an
explicit synthetic, secret-free, durable-journal contract. The in-memory journal
fixture verifies ordering and digests; it does not qualify actual durability,
transport authentication, process lifetime or physical storage.

Candidate creation preserves every sibling through complete nonrecursive trees
along the declared path. A namespace absent from the parent can be created; a
nested path can be added. Updating an existing ordinary blob requires its exact
independently supplied previous blob pin. Executable/symlink ancestors or leaves,
unrelated changes, wrong raw objects and unpinned updates refuse. New commits
have one exact parent, fixed UTC metadata and an explicit final message newline.
Original candidate bytes are read independently before CAS.

The mutation is the fixed GraphQL `updateRefs` query with an exact `beforeOid`,
the precreated candidate as `afterOid` and `force:false`. Only the exact success
acknowledgement is accepted. Every error, absent/ambiguous acknowledgement,
over-limit operation, mutation of recursive input/configuration state or nested
reentrant invocation permanently stops the instance. No error becomes
`accepted:false`, a conflict certificate, a refund, a retry or a different parent.

Limits are 100 HTTP requests, 2 MiB per HTTP reply and 8 MiB conservatively charged
HTTP descriptor/reply bytes. That HTTP byte counter excludes the independent
raw Git reader. A separate 8 MiB retained tagged journal budget includes HTTP and
raw Git evidence; 400 external callbacks include HTTP, raw readers and journal
calls. There are at most 100 store operations. Smaller explicit limits are
allowed. These are bounded injected-interface accounting; no actual full wire,
RSS or host supervision is qualified. Return shapes and reply sizes are checked
before hashing/copying untrusted replies. Raw Git replies additionally have a
64 KiB ceiling.

## Retained actual observations and scientific law

The archived positive acknowledgement and generic GitHub internal-error response
from hosted control `20261004a` are byte-pinned parser fixtures only. The old
control remains `CLOSED_FAILED`; its attempted stale-head test remains unknown.
The timestamp and diagnostic ID in the generic error identify a service failure,
not an authenticated expected-head rejection.

The unchanged scientific store requires a separately authenticated eight-field
atomic-CAS qualification at `scientific_store.py:219–227` and exact success at
`:420–428`; it stops on all failure at `:439–445`. It does not require a named
conflict error in its certificate schema. The additional named-error/null-result
criterion belonged to the closed hosted-control protocol, whose result cannot be
promoted. This bundle issues no actual qualified law or actual scientific receipt.

The unchanged hosted/native certificate still requires completed calibration and
evaluation profiles with native/host/caller receipts, time, evidence, RSS, SDK,
connector, Git process and raw-byte counters (`scientific_admission.py:261–276`).
The complete source/runtime/ELF/plugin freeze and all source/session/allocation
gates remain pending. An engineering Git CAS component cannot replace them.

## Validation and unchanged dependencies

`test_callback.py` verifies four dependency snapshots by independent byte count,
SHA256 and intrinsic Git blob ID before importing them. Their origin is
`results_radio_scientific_execution_prospective_20261003a` at original scientific
publication commit `3abe758efbe2c5bf3220f6843d5d5711aac8596b`. The snapshots are
copied read-only and remain unmodified.

The focused suite exercises full unchanged `ScientificGitStore.publish`, which
returns `SIMULATION_ONLY`, and permanent closure of both callback and store on
the actual archived generic error. It also checks original signed-header parent
bytes, nested genesis and pinned update, undeclared deltas, bad blob/raw commit,
scope and mode failures, acknowledgement extras, request/input/metadata drift,
type-exact booleans, reentrancy and resource ceilings.

`failure01` preserves the six genuine failing development checks and their exact
source before correction. Development logs retain the progression. No live
probe, successor control or scientific source modification was performed.
