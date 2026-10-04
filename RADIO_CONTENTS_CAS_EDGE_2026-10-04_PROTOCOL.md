# Contents file-SHA versus branch-revision CAS — prospective edge probe

## Purpose, 4 October 2026

Continue from the closed v2 checkpoint `1057023c933655406932cd9ea1f6523659640d83`.
Do not repeat v2 or the earlier create-only-ref collision probe. This new scope
tests a different real service edge: whether Contents API's current-file blob
SHA check can stand in for the scientific store's exact expected **branch commit**.
It tests only tiny synthetic metadata in a new probe branch; no source/spectral,
native control, scientific trial or existing ledger is touched.

The [official Contents reference](https://docs.github.com/en/rest/repos/contents?apiVersion=2022-11-28#create-or-update-file-contents)
defines the update `sha` as the blob of the file being replaced and lists 409
conflict. The [official GraphQL commit reference](https://docs.github.com/en/graphql/reference/commits)
defines `expectedHeadOid` for `createCommitOnBranch`; that operation creates and
appends a commit. The current connector exposes Contents update and non-forced
ref update, not this GraphQL mutation. Documentation is a capability lead, not
live qualification. Neither endpoint is silently adopted as the unchanged
scientific store's pre-created exact-candidate CAS primitive.

## Exact single scope and budget

[scope.json](results_radio_contents_cas_probe_20261004a/scope.json) is **2,923
bytes**, SHA256 `a307b4cd7056297b1225b2694be93bc09aa5849a26dc5bfc75fddde6ae2334cf`.
It pins three selected code/test files and the unchanged original scientific
store. Its single identity is
`30f2bd0bae3de697866d7c6c983343a5753fe35809d4328da2f3dff342ebf062`.

| Protected item | Limit or identity |
|---|---|
| Repository | `andersenmartin-blip/setisearch` |
| New probe branch | `radio-contents-cas-probe-20261004a` |
| Initial branch commit | `1057023c933655406932cd9ea1f6523659640d83` |
| New synthetic file namespace | `synthetic_contents_cas_probe_20261004a/` |
| Original artifact directory | `/workspace/scratch/ef1503c23d23/contents-cas-probe-20261004a-artifacts`; device 27, inode 1319284 |
| Invocation allocation | One, irreversibly spent on admission; never retry/resume/rearm |
| Visible GitHub connector calls | At most 18, expected sequence of 17 |
| Mutation attempts | Exactly five if completed: one new branch, two new files, two distinct update probes |
| Admission deadline | 180,000 elapsed visible milliseconds; checked before and after each returned call |
| Serialized response ceiling | 2,097,152 JavaScript UTF-16 code units across returned tool results |
| Retained original evidence ceiling | 4 MiB, logical and allocated storage including directories |

The visible admission deadline cannot interrupt a hung connector or observe
hidden SDK retries. It is not complete process/hosted/native transport resource
qualification. Record that limit explicitly, never describe it as measured HTTP
wire bytes, total underlying requests, RSS or complete wait-chain lifetime.
All request/result envelopes and errors at the visible boundary are retained.

Freeze/publication and full immutable Git payload readback must precede live
admission. Independently check the original empty directory's device/inode,
scope raw SHA256/count and each selected source pin. Create a local exclusive
fsynced attempt-start record before any probe call. A missing/replaced original
directory after admission, ambiguous result or failed persistence closes the
identity; archived bytes never authorize continuation or replay. Do not delete
the public probe branch/files or reset a failed state.

## Frozen sequence and expected observations

1. Positively observe HTTP 404 for the exact new branch; otherwise close before
   mutation. Create it at the frozen base and verify its initial head.
2. Create the exact synthetic revision-0 ledger file, read its immutable commit
   **R0** (sole parent frozen base) and complete bytes/blob **B0**.
3. Create only a separate interference marker. Verify its commit **R1** has sole
   parent R0, the branch head is R1, and the ledger file remains B0 with exact bytes.
4. Submit revision 1 with the still-current file blob B0. Its body retains the
   caller's stale expected branch R0. The API request has no expected branch
   parameter. If accepted, verify commit **R2** has sole parent **R1**, not R0.
   This is a counterexample to substituting file-blob CAS for branch-revision CAS.
5. Submit the separately fixed negative revision-2 update with stale blob B0.
   Expect positively observed HTTP 409. Preserve the full error; do not retry.
6. Verify final head R2, exact revision-1 ledger and interference marker bytes,
   and the primary science branch still at the independently supplied protocol
   publication commit. Retain all 17 operations in order, no extra update.

The negative probe is a separately frozen test phase, not a retry of a failed
scientific evaluation. If any expected observation fails or cannot be positively
read back, the entire live probe is CLOSED_FAILED/ambiguous; do not tune/repeat it
to produce the expected counterexample. Unexpected outcomes remain evidence.

## Review, accounting and limits of inference

The independent Python transcript checker verifies raw external pins, operation
order/routes/counts, integer clocks, response accounting, immutable commit
parents, full file bytes and Git blob hashes, distinct branch/blob identities,
the conflict and final primary head. It never issues a scientific CAS law or
VerifiedFreeze. Nine focused development tests pass; the initial parser failure
(one error in nine tests) is retained. The final parser distinguishes a wrapper's
JSON text from an already decoded base64 Contents object. No old test suite was
rerun as progress.

Reserve 180 engineering seconds, 18 visible connector calls and 4 MiB retained
evidence without refund. The separate v2 reservation of 30 seconds/4 MiB remains
spent, so these two continuation reservations subtotal **210 seconds / 8 MiB**.
This is not a replacement for historical a/b/c/E/F accounting or an estimate of
hidden HTTP/runtime overhead. All historical ledgers, failures and original
scientific/source/native phase budgets remain unchanged and inactive.

The probe may establish one live file-blob conflict and a real branch-revision
counterexample. It cannot establish universal atomicity, absence of privileged
forced updates/deletion, global scientific CAS, hosted transport/native/RSS,
runtime closure, complete source lifetime or scientific readiness. Record all
those authority fields false even if the expected observations pass.

## Preserved scientific scope and exact continuation

Primary remains neighbor9; HD189733 cadence 85030 remains selected, HD1461
cadence 71139 remains pointing-provenance HOLD and GJ724 cadence 73005 stays
untouched reserve. All eleven authentic evidence fields remain pending. Spectra
and original 112+128 M43AF holdouts remain unopened; M43AI failed/closed,
M15/M33 unresolved, a/b/c/E/F permanently spent, F CLOSED_FAILED 0/8, d
uncreated, native8 unreserved, 127/24 NOT ACTIVATED, LS paused, CHEOPS unsent.
No person messages, paid services, booking or schedule changes.

After this single live transcript, preserve its actual disposition and decide
which genuinely supported provider operation could satisfy the unchanged
scientific store law. An available expected-head append API would still require
an authenticated callable bridge and prospective compatibility qualification;
its existence is not permission to alter the old admission contract. Consolidate
the active period on **9 October 2026**, without automatic extension or target change.
