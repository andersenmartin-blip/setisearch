# GitHub v2 publication boundary: isolated qualification — 27 September 2026

**The injected GitHub v2 publication algorithm now passes 31 new tests. Live
qualification and telescope execution remain blocked.** This completes the
isolated-service backend item from science commit
`23d8ce008810123befe38afdee614744c7f82e98`. No live ledger namespace was created,
no telescope request was made and no published ledger was changed.

## What was implemented

`GitHubRoleStore` binds the frozen specification, resource/genesis identity,
repository/branch/path and caller-held branch plus ledger hashes. It reads
immutable commit/tree/blob objects, permits one ordered append, creates only
the pinned ledger entry, checks unchanged sibling files and the exact sole
parent, and makes one explicit `force=false` update. Confirmation reads the
committed payload and verifies current-head ancestry, including every
intervening ledger blob.

The backend is connected to the existing v2 `reserve_role` controller. In the
isolated service, calibration, validation and pilot each reserve their full
unchanged allowance; a fourth reservation is refused. The controller still
returns no network budget or spectral permission. No HTTP adapter, real
credentials or namespace initializer is supplied. Only declared isolated
providers are accepted by this version.

## New concurrency finding and protection

Fast-forward protection alone does not supply an expected-head CAS operation.
The new baseline demonstrates that two updates to one identical commit can
both succeed in the Git-backed service while the ledger contains one
reservation. That would be unsafe if two workers each treated the response
as their own separate source allowance.

Each protected publication now puts a fresh UUID4 attempt ID in its commit
message. Two writers with the same parent then create distinct divergent
commits, even if the proposed ledger payloads are identical. Both the identical
and distinct payload race tests produce **one confirmed winner and one stopped
writer**, with exactly one reservation. These are local service/Git results;
no claim of a live GitHub race experiment is made.

## Verified outcomes

| New boundary risk | Verified fixture result |
| --- | --- |
| Full controller path | Three ordered roles; unchanged cumulative cap exhausted; fourth refused |
| Two same-parent writers | One winner for both identical and distinct proposed payloads |
| Lost reply after reference update | Reservation remains on branch; no client receipt; no retry |
| Fresh client after lost reply | Reads the spent reservation and refuses the old checkpoint |
| Timeout before reference update | Branch unchanged; orphan commit retained; no automatic retry |
| Lost tree/commit creation reply | No branch update; created objects retained |
| Wrong parent, wrong ledger or unrelated file changes | Ref update refused before publication |
| Unrelated descendant after publication | Confirmed only after exact ledger and ancestry verification |
| Copied ledger on unrelated history | Not accepted as confirmation |
| Reset then restore in intervening history | Refused even when the final ledger bytes match |
| Later reservation or merge during confirmation | Conservative stop; existing reservations preserved |
| Missing ledger, malformed JSON/tree/blob, service failure or exceeded cap | Closed client; no initialization or retry |

The retained qualification has **31 tests, 53 isolated bare Git repositories,
638 simulated service calls, 23 simulated ref-update attempts and 8 protected
client confirmations**. Repositories with no attempted operation are included
in the 53 setup count. These are fixture counts, not independent scientific
trials or new observations. The unsafe baseline's two acknowledgements are
not included in protected confirmations.

All **579 archived Git objects** have been checked against their Git object
hashes after compression/retrieval from the evidence archive. The archive
retains unsuccessful attempts and orphan objects as well as successful ones.
An ambiguous outcome is not discarded or converted into an unspent allowance.

## Limits of the result

The [protocol](RADIO_GITHUB_V2_2026-09-27_PROTOCOL.md) maps the algorithm to the
[official GitHub ref](https://docs.github.com/en/rest/git/refs#update-a-reference),
[tree](https://docs.github.com/en/rest/git/trees#create-a-tree) and
[commit](https://docs.github.com/en/rest/git/commits) interfaces inspected on
27 September 2026. Real Git constructs object IDs and checks fast-forward
ancestry in the fixture. **There was no live API qualification**, authentication
exercise or real ledger write. Ordinary publication of this package is separate
from testing the v2 ledger backend.

The service is trusted to provide immutable Git-addressed objects. UUID4
collision resistance is assumed. The implementation deliberately rejects
merges, later ledger changes and ancestry deeper than 16 commits during
confirmation; it does not silently retry under branch contention. A privileged
external ref rollback is outside this proof.

Any error stops the current instance. Its event log is in memory until retained
by the qualification runner. A live caller would require its own durable
intent/checkpoint journal and explicit restart contract; these service tests do
not establish that missing live integration. Likewise the 8 MiB limit measures
canonical decoded response JSON, not pre-decode transport bytes or total process
memory. A future actual HTTP/connector adapter must separately bound those.

## Evidence, reproduction and unchanged scientific state

`results_radio_github_v2_2026-09-27/` contains a full test log, case index,
compressed service/client/Git-object evidence, runtime hashes and machine-readable
result. Python 3.12.14 and Git 2.51.1 were used. The new study config pins nine
unchanged prior files, checked before and after qualification. New implementation,
protocol, report and evidence are covered by the checksum manifest.

```sh
PYTHONPATH=src:scripts python scripts/radio_github_v2_qualification.py
sha256sum -c RESULTS_MANIFEST_RADIO_GITHUB_V2_2026-09-27.sha256
```

Reruns may produce different UUIDs, winning thread and commit IDs; the fixed
assertions concern publication/accounting behavior. Do not count unchanged
replays as additional progress. No old codec/native pipeline, failed scientific
panel, phase audit or orbital catalogue lookup was repeated.

Live ledger requests, telescope requests, telescope reservations and new
scientific evaluations are all **zero**. The old synthetic acquisition ledger
remains closed/exhausted with SHA256
`b77c59e4e1772b27ef7c170bb1c08d1f6c7483d1f12a6c5a0a0deedfca82fd83`.
The original preparation contract remains
`c434c6f0615dfec165512195dcae888d8aa4b33a29efdb5037895ba5530d8bcb`.
The prospective telescope genesis is empty, the remote-store specification is
unmodified, and the execution envelope retains its original five blockers.

## Precise continuation

The isolated-service v2 backend item is complete. Do not rerun these fixtures
as new progress or describe this implementation as live-qualified. The next
bounded engineering preparation is **one prospective live-rehearsal contract**:
identify an explicitly separate qualification namespace, its immutable genesis,
a finite GitHub-only operation budget, the required HTTP/connector response
bounds, a durable attempt journal, and crash/restart confirmation rules. Bind
this package's implementation and unique-attempt rule. Publish and verify that
contract before any namespace initialization or live ledger attempt. Preparing
it creates no namespace, reservation or permission to access telescope data;
do not silently substitute the old exhausted demo or the unactivated telescope
path. Do not implement an automatic retry/refund policy.

Physical qualification still needs the [motion contract's named inputs](RADIO_MOTION_CONTRACT_2026-09-27_RESULT.md),
not another scalar refresh or bank expansion. HD1461/HIP1499 cadence 71139 remains
selected under `HOLD_POINTING_PROVENANCE_UNRESOLVED`. Only a genuinely new
same-scan original RAW/FIL header, observing log or documented file-specific
conversion for AGBT16A_999_189 ON scans 0015/0017/0019 can advance that provenance
question. No such new evidence was available in this engineering task.

Primary remains `neighbor9`. The fresh 24-case panel remains unexecuted; M43AI
failed/closed; original 112+128 M43AF holdouts untouched. M15 GJ581 and M33 HD3651
remain unresolved with prior dispositions intact. LS stays paused at LS8BD–LS8BE,
LS8BF unopened and CHEOPS unsent. No external messages, paid services, booking,
subagents or new automation were used. Consolidation remains **9 October 2026**;
this work does not extend the two-week plan.
