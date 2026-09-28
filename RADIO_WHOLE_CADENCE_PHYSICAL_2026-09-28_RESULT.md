# Whole-cadence physical stages, renderer binding and gates — 28 September 2026

**Three connected engineering interfaces are complete within their scopes.**
The new retention receipts now feed matched-OFF, adjacent-OFF, receiver aliases
and complete clustering; the proposed renderer's case/law/call schedule is bound;
and a distinct post-decision interface applies the fixed recovery/RFI/null gates.
**66 distinct new unit tests pass**, plus a schedule check that rejects a bad
final-scan plan before creating any stream. No Gaussian experiment or telescope
spectrum was opened, and no fresh scientific allocation was consumed.

Parent checkpoint: `9261abcd80086ec9f863ae6ae3b80eaa29e20383`.
Scopes: [physical/renderer](RADIO_WHOLE_CADENCE_PHYSICAL_2026-09-28_SCOPE.md),
[post-decision gates](RADIO_WHOLE_CADENCE_GATES_2026-09-28_SCOPE.md).

## Physical decision chain

`whole_cadence_physical_radio.py` computes its own upstream retention through
the distinct whole-cadence interface. It never passes a relabelled receipt to
the old scramble/retention validators. It reuses the pure signature, literal
alias and ON-track partition arithmetic, and implements the same indexed OFF
and alias comparisons with complete deterministic-fixture comparisons against
literal all-pairs oracles.

All fixed rules are preserved: maximum track distance <=20Hz over all 48
midpoints; exact same-hypothesis OFF first; then local OFF, unmasked adjacent
OFF at S/N>=5.5 in any active epoch; then stationary receiver aliases across
separate ON-track components, with peaks at S/N>=5.5, within +/-100Hz locally
and <=20Hz apart in at least two shared epochs. Width, template, activity and
carrier matching retain their original meaning. Receiver midpoints must also
agree with the bound factors, not merely with a self-consistent signature.

The full 20Hz transitive component partition is retained. Components may span
more than 20 Hz; grouping is not an extra veto. Later evidence is evaluated even
when an earlier veto already applies, with the original precedence preserved.
All members remain available, including physical/rank failures.

**34 physical tests** cover literal boundary/next-float behavior, masked
adjacent-OFF evidence, active epochs, same-component exclusion, transitivity,
complete witness ranking, missing signatures and every bounded stage. Three
additional handoff tests and the final snapshot test are included in that 34,
not counted twice. Callback mutations cannot silently change a successful
report; the original upstream receipt is detached and retained on failure.

Eleven durable scenarios preserve **14 triggers in eight complete runs**, plus
**six upstream triggers across three intentionally incomplete capacity cases**.
The complete examples contain two same-hypothesis vetoes, one local-OFF veto,
one adjacent-OFF veto, three receiver-alias vetoes and four diagnostic survivors.
These are fixed synthetic score/signature fixtures, **not measured interference
rates, signal recovery or sky candidates**. Scores, factor matrices, signatures,
all witnesses/decisions, partitions and expected failures are retained under
[`physical01`](results_radio_whole_cadence_physical_2026-09-28/physical01).
Execution: 0.855178248 s; peak RSS 29,073,408 bytes.

## Renderer plan and source/law binding

`whole_cadence_render_radio.py` validates the immutable proposal, every case's
recipe/seed/source/context/law and all six stream schedules. **14 tests pass**.
All **151 proposed case plans** bind without calling an RNG. The metadata-only
plan index is retained. A changed case or recipe cannot self-activate a trial.

Two explicitly non-Gaussian mock cadences exercise the row/injection/
normalization boundary: one without injection and one with the first
prospectively selected width129 ON-signal recipe. Each has six streams and
96 rows. All generator arguments/order and source scopes are recorded; the
injected example affects exactly 48 ON rows and conserves the specified power
before float32 rounding (maximum mass error 1.11e-16).

The mock's actual case and law identities differ from the intended proposed
Gaussian identities. Its deterministic arithmetic texture ignores the seed;
no PRNG output or scientific calibration/reference is claimed. The real
Gaussian entry remains explicitly disabled pending durable fresh allocation
and a published/readback executable freeze.

All **12 normalized sources / 12,582,912 values** are saved losslessly. Postflight
reconstructs the existing deterministic raw rows, checks all original row
hashes and restores the same 12 complete source identities. This is a durable
rehydration check, not an additional mock experiment. Full raw/normalized
source hashes and geometry are retained in
[`source_rehydration.json`](results_radio_whole_cadence_physical_2026-09-28/source_rehydration.json).
Mock execution: 1.236237189 s; peak RSS 77,541,376 bytes. No detector scores or recovery
outcomes were computed on these mock cadences.

## Fixed post-decision gates

`whole_cadence_evaluation_radio.py` binds the truth recipe to the exact case and
context, then evaluates association only after decisions. Every active epoch
must be among injected ON epochs, and every active midpoint must be within two
native channel spacings of the injected track. Complete member/component counts,
broad-width 65/129 leakage and mixed-component accounting are retained.

**18 tests** and eight saved handcrafted decision examples qualify the counting
interface. Signal examples without an associated final member fail; any final
RFI/null member fails the zero-control gate, even when associated. Missing or
duplicated members, changed case/recipe/context, broken retention receipts and
hidden cluster finals are rejected. The examples are clearly marked handcrafted
and do not constitute detector or scientific gate measurements.

## Preservation and exact continuation

[Postflight](results_radio_whole_cadence_physical_2026-09-28/postflight.json)
verifies the old 15 invariant pins plus HD189733 preparation and the inactive
127/24 proposal. No prior development/calibration/evaluation/diagnosis attempt,
old 24 unopened evaluations or exhausted acquisition ledger was reopened. All
old failures, holdouts and dispositions persist: HD1461 pointing hold, GJ724
reserve, M43AI failed/closed, original 112+128 M43AF, M15/M33 unresolved, LS8BD–BE
paused/LS8BF untouched and CHEOPS unsent. No external messages, source requests
or plan extension; consolidation remains 9 October.

No unexpected test or fixture failure occurred. Negative capacity fixtures stay
incomplete. Two focused implementation hardenings preserve callback/source
integrity, and stream schedules are checked before the first mock read; the
qualification phases and code hashes are recorded in
[`qualified_code_pins.json`](results_radio_whole_cadence_physical_2026-09-28/qualified_code_pins.json).
Saved evidence is 1,253,364 bytes at postflight, below the 128 MiB scope ceiling.

**Completed:** deterministic physical integration, metadata/mock renderer
binding, source rehydration and fixed post-decision gate interface. Do not
rerun these unchanged fixtures, old codec/calibration/development executions
or the prior diagnosis as new progress.

**Next:** implement a distinct durable scientific case-consumption journal and
connect the real Gaussian renderer to it; qualify the full native physical and
gate chain, source/runtime/law bindings and cumulative crash/restart behavior.
Use the [integrated execution outline](RADIO_WHOLE_CADENCE_INTEGRATION_2026-09-28_DRAFT.md)
for concrete order, fixed gates and budgets. It is a **draft, not an executable
freeze or allocation**. The proposal remains PROPOSED_NOT_ACTIVATED. No actual
127/24 values before fresh authorization/allocation and a published/readback
executable freeze. Original preparation contracts remain unchanged/not-ready;
a synthetic pass still cannot authorize telescope spectra without separate
integrated source/acquisition/trial admission.
