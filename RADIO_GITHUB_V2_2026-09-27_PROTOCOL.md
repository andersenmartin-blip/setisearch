# Injected GitHub v2 ledger backend — qualification protocol, 27 September 2026

## Scope and authoritative inputs

Continue from `23d8ce008810123befe38afdee614744c7f82e98` and the newest status,
direction and two-week plan. Implement the already frozen publication-store
specification using an injected REST-shaped service and isolated fixtures.
This protocol documents that implementation and its qualification alongside the
results; it is not a preregistered scientific evaluation or a live activation.

The unchanged specification is
`results_radio_codec_publication_2026-09-27/publication_store_spec.json`, file
SHA256 `3e5c8ba7161fa7ff06be99903dc1e83191741bfc025357ac2cca8dedefc563b7`.
The new study config pins it, the resource contract configuration, original
execution envelope, source preparation contract, closed synthetic ledger,
empty telescope genesis and reused validator/controller implementations.
No old specification or evidence is rewritten to make qualification pass.

The backend has **no HTTP adapter, credentials, namespace initializer or network
budget constructor**. It accepts only an injected service declaring isolated
fixture mode. The provider is a trusted boundary; that declaration is not a
sandbox against malicious injected code. Qualification disables Python socket
creation and uses bare local Git repositories with no remotes. The pinned
production path appears only as a routing identity in the simulated service.
No directory, ledger, branch or reservation is created at that live location.

## GitHub semantics and additional obligations

Official documentation checked on 27 September 2026:

- [Git references](https://docs.github.com/en/rest/git/refs#update-a-reference):
  the update body names the target SHA and `force`; `force=false` requests a
  fast-forward update. It is not an expected-old-head compare-and-swap argument.
- [Git trees](https://docs.github.com/en/rest/git/trees#create-a-tree): use an
  explicit base tree to preserve unrelated entries; truncated inventories are
  insufficient for full verification.
- [Git commits](https://docs.github.com/en/rest/git/commits): explicitly bind the
  tree and a one-element parent list. A missing parent list would create a root.

The documentation advertises REST version `2026-03-10`. A future real transport
must explicitly bind the API version and authentication/error behavior; this
package does not claim that such a transport has been tested.

A deterministic commit can be acknowledged twice by a fast-forward-only store
when both callers ask for the identical commit. The isolated Git baseline
must demonstrate this, then verify that the protected path's fresh UUID4 in
each commit message makes competing attempts distinct. With the same sole
parent their commits diverge, so only one may win. UUID collision resistance
and trusted UUID generation are assumptions, not a global locking service.

## Publication algorithm

1. Verify the specification against the caller's independent file hash and
   bind repository, branch, path, resource, source inventory and genesis.
2. Read the branch SHA, then read its commit, non-recursive tree path and blob
   at immutable Git object identities. Do not read the file from a mutable ref.
   Missing files, symlinks, malformed/truncated/duplicate tree entries, wrong
   object IDs, changed namespaces and duplicate/non-finite JSON are failures.
3. Require both caller-held branch SHA and canonical ledger SHA256. Validate
   the existing v2 ledger plus exactly one ordered append with the entire old
   prefix and root preserved. Missing ledger never means initialize.
4. Create one tree entry at the pinned path from the pinned parent tree. Verify
   every sibling inventory along the path is unchanged and the new leaf is the
   exact expected Git blob. Re-read the candidate commit to verify its tree and
   sole parent. Re-read the branch before attempting one `force=false` update.
5. Acknowledge success only after the candidate's committed blob is read back
   and a bounded first-parent walk connects the current head to that candidate.
   Every intervening ledger blob must be byte-identical. Unrelated commits can
   pass; changed ledgers, later reservations, merges, copied ledgers on unrelated
   history, reset-then-restore sequences and overlong ancestry stop confirmation.
6. Preserve the receipt, all client events, service exchanges and Git objects.
   The existing `reserve_role` controller may consume this interface, but still
   returns `network_budget_issued=false` and `spectral_access_authorized=false`.

Git SHA-1 object IDs and the ledger's canonical JSON SHA256 have different roles
and are never interchanged. Blob bytes are checked against their Git ID before
JSON is trusted. GitHub/service object addressing is trusted; the client does
not independently rebuild signed commit objects or defend against a malicious
Git server. External privileged force-push/rollback is outside this proof.

## Failure semantics and bounded resources

There are no retries, implicit rebases, refunds or fallback providers. Any
operation error permanently closes that client instance. A reference update
may already have landed even when its reply was lost; no receipt or source
allowance is emitted on that path. A fresh client sees the durable reservation
and refuses the old checkpoint. It must not interpret a new process as retry
permission.

A timeout before the reference update can leave an orphan tree/commit without
changing the branch. Preserve that distinction: an orphan is not proof of a
committed reservation, while an uncertain outcome is not authorization to retry
or restore quota. This prototype's events are in memory during a call and are
retained by the qualification runner. A live caller would additionally need a
durable intent/checkpoint journal before mutation and an explicit restart policy.
The old acquisition demo's crash/restart tests are not rerun or claimed here.

Per public read/publish operation: at most 128 service calls, 8 MiB of canonical
returned JSON, 64 KiB ledger payload and 16 confirmation commits. All counts
include failed calls. Response bytes are measured after the injected service
returns decoded JSON; these are not HTTP wire-byte or transport-memory bounds.
A future HTTP adapter must enforce pre-decode limits and timeouts separately.
No telescope quota is used. The original 1.5 GiB / 1,500-request / 3,600-second
three-role telescope contract remains frozen and unactivated.

## Qualification and retained evidence

Use actual Git 2.51.1 object creation and ancestry checks in the service fixture,
independent of the client's ledger/tree checks. Qualify the changed boundary:
controller integration, same/different-payload writer races, stale checkpoints,
lost object/update responses, post-commit corruption, wrong parents/trees,
unrelated file mutation, strict parsing and bounded ancestry/resource errors.

The deliberately unsafe duplicate-ack baseline is separate from protected
client confirmations. Intentional reset/corruption cases affect only ephemeral
service fixtures. Preserve full exchanges, client traces, receipts and every
Git object (including orphans) in `service_evidence.json.gz`; retain an indexed
case summary and complete test log. Fixture counts are engineering cases, not
scientific trials, independent sky observations or telescope reservations.
Replay can change UUIDs, winning thread and Git commit IDs; test conclusions
and ledger/accounting properties must remain the same.

Publish code, protocol, report and evidence with a checksum manifest on
`m43-support-qualification`, using a fast-forward from the verified current
head. Update `main` README without merging unrelated branch contents. Source
selection, pointing hold, preparation contract and all five execution blockers
stay unchanged. No new spectrum, fresh control panel, LS8BF data, holdout,
external message, paid service, booking or delegation is authorized here.
