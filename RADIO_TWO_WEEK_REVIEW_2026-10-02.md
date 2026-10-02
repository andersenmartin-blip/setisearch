# Radio SETI midpoint review — 2 October 2026

**The new radio-search pilot has not started.** The [26 September–9 October
plan](RADIO_TWO_WEEK_PLAN_2026-09-26.md) called for one bounded, reproducible
search on an independent observing sequence, with paired ON/OFF evidence,
prospective controls and complete candidate accounting. Work so far has
established source metadata, a source-specific design and engineering
components. It has not produced new telescope-spectrum analysis, a qualified
scientific detector, a searched pilot ledger or new candidate follow-up.

This is the scheduled 2 October review. The period still closes on **9 October
2026**, without an automatic extension or return to LS. The current
[runtime-custody integration](RADIO_NATIVE_V2_RUNTIME_CUSTODY_INTEGRATION_2026-10-02_RESULT.md)
is verified preparation work; its final checks and publication are recorded
separately. No pending test count is treated here as
an achieved result.

## Progress against the scheduled work

| Planned work | Evidence available at this review | Assessment |
|---|---|---|
| 26–27 September: restart, novelty inventory and metadata-only source selection | Restart and source inventories are published. The [alternate metadata screen](RADIO_ALTERNATE_DATA_2026-09-27_RESULT.md) selected HD189733/HIP98505, cadence 85030, under the fixed ordering. HD1461's provenance hold is retained. | Metadata/preparation work completed; no new spectra inspected. |
| 28–29 September: executable method and integrated transfer/control gate | The primary reference remains `neighbor9`. Source geometry, receiver-coordinate, adapter and panel contracts are recorded; codec, transport and resource components have retained successes and failures. Full scientific/native and execution qualification remains open. | The advancement gate has not passed. Component and synthetic checks do not qualify an astronomical search. |
| 30 September–3 October: frozen pilot, followed conditionally by at most two other sequences | No pilot spectra, eligible astronomical triggers, physical-veto outcomes or candidate search ledger exist for the selected sequence. GJ724 remains untouched. | The planned pilot work is blocked as of 2 October. There is no supported analysis start date. |
| 4–7 October: fixed follow-up of every surviving cluster | No new pilot cluster is available for this phase. Existing candidate dispositions remain preserved. | Dependent on a qualified pilot; no new follow-up achieved. |
| 8–9 October: consolidate scientific findings, limitations and next action | The published engineering record retains failed and incomplete scopes with their resource and custody limitations. This review identifies the gap to the scientific objective. | Consolidate on 9 October even if the route remains blocked, with an explicit bounded failure report and exact next information requirement. |

HD189733 superseded the earlier HD1461 selection following the owner's
27 September direction to use other data without sending messages. This is
the documented target change in the plan, not an amplitude-based reselection.
The [geometry study](RADIO_HD189733_GEOMETRY_2026-09-27_RESULT.md) exposes the
larger source-specific window and its model limitations. Its conditional
arithmetic does not establish physical completeness or sensitivity.

## Engineering result and present boundary

The engineering work has made custody, byte accounting, runtime admission,
process supervision and retained failure evidence more explicit. Earlier
offline transport and tiny resource probes establish their stated component
properties only. They neither count as additional observing sequences nor
complete the eight-input resource, full transport or scientific gate.

On 2 October, the [single engineering-control invocation](RADIO_NATIVE_V2_ONE_CONTROL_2026-10-02_RESULT.md)
closed with **`CLOSED_FAILED_RUNTIME_CUSTODY_POLICY_MISMATCH`** before scope
creation. The frozen Git bytes matched, but the activation check required a
sole-link file while the freezer had admitted hardlinked Git runtime files.
The marker and invocation are permanently spent. Preserve this failed
evaluation; do not retry it or reuse its marker.

The [remediation protocol](RADIO_NATIVE_V2_RUNTIME_CUSTODY_REMEDIATION_2026-10-02_RESULT.md)
and [read-only proof component](RADIO_NATIVE_V2_RUNTIME_CUSTODY_COMPONENT_2026-10-02_RESULT.md)
separate activation-only Git alias closure from sole-link runtime used later.
The current authorized package integrates this policy into freeze construction,
receipt validation and pre-write checks, then prepares a fresh blocked
plan/freeze after verification. It does not create a new execution-qualified
preread or marker and does not invoke another control.

Earlier reports describing receipt integration concern the interfaces and
checks verified at that point. The current source-worker guard still calls
`require_execution_ready()` without its required receipt and deliberately
refuses. Those historical descriptions do not establish end-to-end execution
readiness.

## Blockers that remain

1. **Authenticated admission at the source worker:** the receipt must reach the
   source-worker guard through an independently pinned, verified path. The
   existing hard refusal remains in place; structural receipt validation alone
   cannot start the full source workload.
2. **One-invocation consumption and replay resistance:** scope-bound receipt
   checks and denial of the known spent identity do not yet prove persistent,
   irreversible spending of a future invocation. That boundary requires its
   own prospective implementation and negative verification.
3. **Fresh public execution evidence:** any future control would need a new
   plan/freeze, a distinct execution-qualified preread with immutable public
   readback and a later unique marker under the prescribed ancestry. The
   current integration creates no such preread or marker. Old evidence cannot
   authorize the new code snapshot.
4. **Complete execution and resource qualification:** activation custody
   integration does not establish the full eight-input measurement, original
   time/storage/RSS caps, actual caller/host transport joins or every final
   disposition under the complete workload. Incomplete joins stay incomplete;
   tiny probes cannot upgrade them.
5. **Scientific and telescope admission:** full native physical/recovery/RFI/null
   controls, the separately frozen 127/24 gate, source acquisition and trial
   admission remain required before opening the selected telescope spectra.
   Neither a software test pass nor an engineering control would substitute
   for these gates.

## Decision for the remaining period

Complete the bounded runtime-custody preparation package, retain its failures
and exact verification evidence, and publish the fresh blocked snapshot under
the standing publication authorization. Then assess the named blockers in
order before considering any separately authorized future execution. The
remaining calendar days do not supply execution authority or justify wider
budgets, additional sequences, reused evaluations or automatic retries.

If the scientific gate cannot be reached by 9 October, close this period with
the achieved metadata/design/engineering evidence, the absence of a new radio
search result, the concrete obstruction and a decision to pause the blocked
route or undertake one named bounded information/method study. Do not claim
the pilot objective completed and do not extend the plan by default.

| Preserved disposition | State at this review |
|---|---|
| Selected radio preparation | HD189733/HIP98505, cadence 85030 |
| Held original preparation | HD1461/71139 — HOLD; provenance requirement unresolved |
| Reserve | GJ724/HIP91608, cadence 73005 — untouched |
| Telescope spectra and original M43AF holdouts | Unopened; original 112 injection/control inputs and 128 native nulls reserved |
| 127/24 scientific proposal | NOT ACTIVATED |
| `native8` | Unreserved; no native/scientific case execution authorized |
| Closed M43 and engineering outcomes | Preserved; no retuning into a pass or reclassification as fresh evaluation |
| LS | Paused at LS8BD–LS8BE; LS8BF remains the saved restart |
| CHEOPS calibration request | UNSENT; no reply awaited |
| Period closure | 9 October 2026; no automatic extension or LS return |

This review reads the existing project record. It opens no telescope values or
holdouts, runs no scientific case, draws no RNG, creates no reservation and
sends no external message.
