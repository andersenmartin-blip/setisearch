# Prospective GitHub rehearsal and attempt journal — 27 September 2026

**The bounded preparation contract and its local attempt journal are complete;
25 new tests pass. Live qualification and telescope access remain blocked.**
This completes the exact preparation item from science commit
`8e6400ee1bcfee530780a5fc96491847c05e57b1`. No live ledger namespace was created,
no remote grant was issued and no telescope value was opened.

## Concrete changes

The [prospective protocol](RADIO_REHEARSAL_CONTRACT_2026-09-27_PROTOCOL.md) now
names one separate namespace, immutable model/grant genesis templates, five
ordered phases and a finite **160-call / 32-MiB returned-text / 1,200-second**
proposed engineering envelope. These numbers are not active grants. The model
uses distinct resource/inventory identities and cannot confer source rights.
Neither the old exhausted demo nor the unactivated telescope namespace is
reused. The canonical preparation configuration identity is
`099202290f68ec85ba52dc9a8ab815bc05288ca5defedfe0d22a79741a1d5754`.

The new journal fsyncs the unique call/attempt identity, request digest and reply
allowance **before dispatch**. Short replies do not refund the reserved amount.
An existing contract/phase path cannot be reopened for sending calls. Replay
validates an independent head checkpoint, exact grant, chain, schema, order and
limits, and always returns zero dispatch rights. Budget and other veto reasons
are retained when the journal remains writable; broken evidence is not repaired.

## Verified new risks

| Boundary | Result in local qualification |
| --- | --- |
| Exit after intent, before simulated side effect | Pending intent; entire phase charged; no restart dispatch |
| Exit after simulated write, before reply | Same pending state; side effect retained; no resend |
| Intent fsync failure | Provider never called; uncertain journal bytes not adopted |
| Result-journal failure | Last confirmed intent retained; outcome unresolved; no retry |
| Lost reply, malformed reply or oversized/late result | Permanent stop; spent allowance retained |
| Call/reply allowance exhausted | Next call refused before dispatch; stop reason retained |
| Unicode reply | UTF-8 bytes counted, rather than characters |
| Clock regression | Further dispatch refused |
| Reopen with fresh attempt UUID | Existing phase still refused |
| Read-only recovery or duplicate mutation sequence | Write refused |
| Torn/corrupted/truncated journal or mismatched checkpoint/grant | Replay refused |
| Coherently rehashed but invalid event order/types | Replay refused |
| Live provider, source-path alias or false ready flag | Preparation boundary refuses it |

The final qualification includes **two actual child-process exits** and retains
33 journal/checkpoint/side-effect/corruption files. There are two retained local
development runs: the initial 24-test pass and the final 25-test pass after
adding explicit stop-reason retention and a malformed-reply case. Their logs,
source hashes and full evidence archives remain separate; they are **25 distinct
final tests, not 49 independent cases**. Both runs have two child exits (four
executions in total). No scientific setting or failed evaluation was tuned.

Python 3.12.14 was used, with socket creation disabled during qualification.
All twelve pinned inputs verify before and after the run. This package reuses
the old journal's storage primitive but does not rerun the closed acquisition,
Git backend, codec/native, orbital-reference or scientific-control studies.

## Newly explicit limitation

The callable connector declarations expose immutable Git reads and explicit
parent/base-tree/`force=false` arguments. They do not expose HTTP status,
caller-selected API version, internal retries, numeric pre-decode caps or
transport cancellation. The retained capability inventory records that actual
interface, without probing a live ledger endpoint.

Consequently a tool-call budget cannot be claimed as an HTTP request/wire-byte
budget. The journal can stop before dispatch or reject a late result; it cannot
interrupt an in-flight connector operation. A local fsynced journal also does
not prove survival of lost scratch or coordination across machines. These are
concrete remaining gaps, not passed gates. The previous backend still accepts
only its isolated service and expects an HTTP-shaped response; no live service
is disguised as that fixture. Ordinary publication of this report is not a
qualification of the live ledger backend.

The preparation deliberately leaves all activation flags false. Publication
read-back can later be recorded separately; this original preparation is never
rewritten to ready. Its local grants, proposed limits and stored templates issue
zero live rights.

## Precise continuation

This contract/journal preparation item is complete. Do not recreate it, rerun
the same fixtures as progress, initialize its live namespace or restart the
exhausted demo. The next useful engineering unit is **offline integration of a
typed connector boundary and irreversible phase ownership/recovery** under this
exact fixed envelope. It must:

1. Represent documented connector success, errors and uncertainty without
   fabricating HTTP status/version/retry guarantees; keep real adapters distinct
   from fixture providers and the production resource contract.
2. Account for the remote grant bootstrap, immutable confirmation, checkpoint
   retention, read-only recovery and closure within the existing 160-call/32-MiB/
   1,200-second budget, including ambiguous publication and loss of local state.
   No unmetered administration or fresh namespace may restore spent allowance.
3. Integrate the journal and previous one-append/unique-attempt/ancestry checks;
   qualify only the newly changed adapter/ownership/recovery risks. Publish and
   verify the resulting evidence and transport disposition before any live
   activation. If the provider cannot meet required bounds, retain the explicit
   limitation; do not silently relax the frozen source or transport requirements.

These are implementable engineering tasks; this report does not declare all
useful work exhausted or stop the two-week plan. A live attempt is not the next
automatic action. Further physical motion work still needs the named inputs in
the [motion report](RADIO_MOTION_CONTRACT_2026-09-27_RESULT.md), with no new bank
or scalar refresh inferred from this package.

HD1461/HIP1499 cadence 71139 remains selected under
`HOLD_POINTING_PROVENANCE_UNRESOLVED`. Pointing requires genuinely new same-scan
RAW/FIL header, observing log or file-specific conversion evidence for
AGBT16A_999_189 ON scans 0015/0017/0019. No new such evidence was found or claimed
in this engineering work; the closed catalog/code searches were not repeated.

Primary remains `neighbor9`. The original source preparation contract, closed
synthetic ledger, empty telescope genesis and five execution blockers are
unchanged. Telescope requests/reservations and new scientific evaluations are
zero. The fresh 24-case panel and original 112+128 M43AF holdouts remain untouched;
M43AI is failed/closed. M15 GJ581 and M33 HD3651 retain their unresolved status.
LS stays paused at LS8BD–LS8BE, LS8BF unopened, CHEOPS unsent. No external message,
paid service, booking, subagent or new automation was used. Plan closure remains
**9 October 2026**.

## Evidence

The preparation, both inactive genesis templates, capability inventory, runtime,
machine-readable result and both retained qualification attempts are under
`results_radio_rehearsal_contract_2026-09-27/`. The checksum manifest covers the
new code, protocol, report and evidence. Existing input pins are in the config.

```sh
PYTHONPATH=src:scripts python scripts/radio_rehearsal_contract_qualification.py
sha256sum -c RESULTS_MANIFEST_RADIO_REHEARSAL_CONTRACT_2026-09-27.sha256
```

The runner preserves any additional local replay in a new numbered evidence
directory. Such a replay is not new science, a new grant, or new plan progress.
