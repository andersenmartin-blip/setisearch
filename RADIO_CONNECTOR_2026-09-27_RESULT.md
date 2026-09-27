# Typed connector integration and bootstrap limit — 27 September 2026

**Twenty new offline integration tests pass. The live rehearsal remains
blocked by a concrete missing admission primitive, in addition to the known
transport limitations.** This completes the bounded offline connector/ownership
investigation requested at `ef0827036b16952808a09a65bad910b3e29577e9`; it does not
complete live bootstrap or authorize telescope access.

## Working integration

The new typed adapter distinguishes Git objects, returned object IDs and a
reference-update acknowledgement. It never invents HTTP status, API version or
internal retry counts. One actual read-only envelope for this project's prior
public commit was retained and decoded. Text-only/ambiguous/error envelopes and
conflicting nested GET content are refused.

The separate rehearsal model now reaches the frozen one-append, sibling-file,
blob and ancestry checks through the durable attempt journal. All operations
within a phase share its allowance; restarting the backend's internal operation
counter cannot reset it. A minimal tool acknowledgement is independently checked
against immutable Git content and current-head ancestry. A false success reply
without a landed commit fails confirmation.

A further concrete protection reads back the **exact unique-attempt commit
message** after connector conversion. If the provider drops that field, the
candidate is refused before a reference update. The previous backend and
preparation are unchanged; the new constructor explicitly binds an engineering
model and accepts local connector fixtures only.

With an explicitly supplied independent admission fixture, two competing owners
produce one owner and one refusal. A serialized grant cannot reopen ownership.
A lost reply after a model append remains spent and unconfirmed. A fresh client,
using a separate read-only recovery phase and no old client journal, observes
the two existing model reservations without resending the mutation. All of this
is conditional on the independent fixture authority already existing.

## Phase-veto gap found and corrected before closing this work

The first published version (`c8b8317cb8750d80f2fc531bbea2c606d58e652b`)
passed 19 tests. Final review then identified an untested composition gap: after
a byte-valid but semantically rejected tool envelope, the store stopped but the
journal and independent owner could remain active. A new regression reproduced
this: a fresh store reused that phase and made **five additional calls**, taking
the case from one call to six.

The corrected `_stop` propagates every semantic/Git-validation veto to the phase
journal and revokes the owner channel while retaining its full uncertain charge.
The same regression now stays at **one call**, and both rebinding a fresh store
and using the old owner are refused. The failure and its code snapshot remain in
`qualification_02`; `qualification_03` contains the final 20-test pass. The initial
19-test pass is retained in `qualification_01`. These are 20 distinct final cases,
not 59 independent results. No scientific evaluation was changed or rerun.

## Why live startup is still blocked

The fixed rehearsal contract counts initialization and requires durable admission
before its calls. If the first GitHub call is itself needed to create the first
durable admission record, that requirement is circular. This can be resolved by
an independent pre-existing admission authority; it cannot be resolved merely
by adding another local checkpoint file or retry loop.

The new negative baseline makes the failure visible using actual local Git
reads: permit a first branch GET before the grant, then discard client state.
The next client sees the same branch and no grant, so it can repeat that GET.
The retained traces reach **13 calls against the 12-call initialization cap**
and **161 calls against the 160-call total**, with no durable grant recorded.
These are two bounded restart-policy traces, not real process crashes or live
GitHub traffic. They demonstrate the named unsafe policy; they do not rule out
an independently metered runtime.

The positive authority is a separate transactional SQLite **fixture**. Its setup,
granting and server-side recovery are assumptions supplied to the local tests.
They are not a GitHub implementation and cannot become unmetered administrative
calls in a live run. The full five-phase charging model exhausts exactly the
existing 160-call / 32-MiB / 1,200-second proposal, but no live initialization,
remote grant or closure is qualified by that arithmetic.

The [protocol](RADIO_CONNECTOR_2026-09-27_PROTOCOL.md) records the dependency
argument, accounting boundary and explicit transport disposition. Live startup
requires a durable exclusive admission mechanism available **before the first
rehearsal call**, with its own provisioning accounted for. No such available
mechanism was established in this task. The current connector also supplies no
observable HTTP status/version, retry bound, numeric pre-decode cap or transport
cancellation. These missing guarantees remain false; the old preparation is
not rewritten or silently relaxed.

## Evidence and exact scope

| Retained item | Count / result |
| --- | --- |
| Distinct tests in final qualification | 20 passed |
| Isolated bare Git repositories in final run, no remotes | 16 |
| Simulated connector calls in final run | 371 |
| Of these, deliberately unsafe bootstrap baseline calls | 174 |
| Confirmed protected model appends | 3 |
| Archived Git objects verified in final run | 196 |
| Full local attempt journals in final run | 14 |
| Frozen input file pins checked | 14 |
| Actual ordinary project-commit metadata reads | 1 |
| Live ledger requests / live grants / telescope requests | 0 / 0 / 0 |

The one observed public project-commit tool result is 3,827 bytes under the
runner's canonical JSON encoding. That measures an application envelope, not
HTTP wire bytes. Ordinary publication/read-back is separate from the future
rehearsal and is not called a live ledger test.

The full connector/service exchanges, authority snapshots, journals, receipts,
vetoes, negative traces, orphan Git objects, exact source snapshot and runtime
are retained under `results_radio_connector_2026-09-27/`. Python 3.12.14 was
used with socket creation disabled during the fixture suite. All 196 archived
objects from the final run verify against their Git object hashes. These are engineering counts,
not independent sky trials or detector-recovery measurements.

```sh
PYTHONPATH=src:scripts python scripts/radio_connector_qualification.py
sha256sum -c RESULTS_MANIFEST_RADIO_CONNECTOR_2026-09-27.sha256
```

The new boundary tests reuse frozen algorithm components but do not rerun the
old backend/journal suites, science controls, native pipeline or source searches.
Do not replay them unchanged and count that as new progress.

## Precise continuation

This offline connector/journal/admission investigation is closed. **Do not
initialize the planned live namespace or add another self-funding GitHub grant
loop.** Reopen live engineering only for a concrete independent admission
capability with documented provisioning/accounting and the missing transport
guarantees, or an explicitly published prospective alternative that does not
silently alter the frozen contract. The fixture authority is not that capability.
Keep the planned limits and all ledger identities unchanged; no automatic retry,
refund, fresh namespace or unmetered administrative path.

The next available independent plan item is the motion report's explicitly
allowed **prospective phase-agnostic domain/convention contract**. Work only on
declaring conditional parameter support, relative-axis/emitter conventions,
source/observer time and frequency definitions, and the evidence needed for an
error budget. Use the retained limit/source metadata; do not repeat its closed
catalogue/paper lookup, adopt a central e=0.172, manufacture a joint-confidence
domain from marginal errors, create a new bank, or execute detector controls.
Keep unqualified physical terms explicit. Such a document would not resolve
pointing, qualify bank coverage, change the primary or open spectra.

Pointing can advance only with genuinely new same-scan original RAW/FIL header,
observing log or file-specific conversion evidence for AGBT16A_999_189 ON scans
0015/0017/0019. None was obtained in this engineering unit. HD1461/HIP1499 cadence
71139 remains selected under `HOLD_POINTING_PROVENANCE_UNRESOLVED`.

Primary remains `neighbor9`; all five execution blockers, original preparation,
closed/exhausted synthetic ledger and empty telescope genesis are unchanged.
The fresh 24-case panel, original 112+128 M43AF holdouts and LS8BF remain untouched.
M43AI remains failed/closed; M15 GJ581 and M33 HD3651 unresolved. LS remains paused
at LS8BD–LS8BE and CHEOPS unsent. No messages, paid service, booking, subagent or
new automation was used. Consolidation remains **9 October 2026**, with no
extension of the two-week plan.
