# Whole-cadence source and downstream handoff — 28 September 2026

**Two engineering interfaces are now qualified within the stated scope.**
The retained codec fixture reaches the receiver-native complete-family maximum;
a separate whole-cadence threshold/retention/rank interface handles EMPTY
without impersonating the failed legacy scramble calibration. **41 new unit
tests and three native negative checks pass.** No scientific allocation or
new telescope/source request was consumed.

Scope: [prospective engineering boundary](RADIO_WHOLE_CADENCE_HANDOFF_2026-09-28_SCOPE.md).
Parent: `fa65fd3837c1fd61850302a93708f71fffcdc8da`.

## Retained codec → source receipts → native scores

The legacy-declaration HDF5 member was restored from the published archive,
with its original SHA256 verified. Version identities and all 30 published
codec binary hashes were checked before decoding. The original fixture
failure and corrected reconciliation remain unchanged; neither closed script
was restarted and no new HDF5 fixture was generated.

Only the validation-window rows were passed through the new interface. Their
decoded and normalized hashes match the retained reconciliation receipts.
One normalized immutable payload is assigned to six explicit synthetic scan
slots, each with its own context/scan/case/law/source identity. The receipt
states that the payload is shared: **not six independent observations, not
Gaussian draws, and not archive telescope provenance**. The adapter rejects
incorrect law labels, member/window/runtime bindings and incomplete row
inventories before the first row is read.

The connected run produced and preserved:

- 6 source identities and 48 native-cache receipts;
- 1,296 score vectors / 384,912 score cells, restored from NPZ with identical
  vector identities during postflight;
- all 2,592 ON hypotheses, covering 209,952 ON score cells;
- 15,456 eligible cells and finite maximum 52.15322494506836.

That maximum is the response to the **deterministic arithmetic texture**. It
is not a sky signal, a calibration reference or a measured false alarm.
Active time: 4.004705396 s; peak RSS: 78,127,104 bytes; modelled arrays:
53,366,656 bytes. Wrong case/law and a changed final OFF-vector identity are
rejected. The full native scores, scope records, source/cache ancestry and
maximum receipt are retained in
[`native01`](results_radio_whole_cadence_handoff_2026-09-28/native01).

## Separate threshold, complete retention and rank

`whole_cadence_downstream_radio.py` accepts only the distinct typed
whole-cadence threshold. It recomputes the reference bundle from 127 ordered
complete-family receipts, retains EMPTY outcomes, binds the family/law/domain,
and rejects reference/observation case overlap. It never constructs a legacy
ThresholdCertificate, scramble table or legacy retention certificate.

The numerical rules stay fixed: neighbor9, eight widths, four activity
subsets, minimum active S/N 3, sum stack, floor 10, higher quantile 1 and
inclusive rank ceiling 1/100. Every threshold-crossing ON and OFF member is
retained, including ties and members that fail the rank cut. The ON-null rank
is applied only to ON members; OFF members remain physical-control evidence.
Mask hashes, hypothesis counts, maximum consistency, record hashes and input
identities accompany the full report. EMPTY observations have rank 1.

The existing calibration→validation score-map proof can now be consumed as a
pinned input. Both actual receiver contexts must validate, including their
grids; a claimed context hash with an unrelated grid fails. No old numerical
map study was repeated. Operator equality still does not establish a telescope
noise law or qualify absolute-frequency physical veto transfer.

A scalar fixture oracle verifies all 192 members per kind over both templates,
every width/subset and three carrier positions. Six durable interface scenarios
preserve **385 complete triggers, two partial triggers and two capacity-crossing
triggers**, including a retained tie with p=2/128 that fails the 1/100 cut.
Record-count and record-byte cap failures and eligible OFF overflow return
incomplete evidence and never a success receipt. These are expected negative
checks, not hidden execution errors. All fixture vectors, reference receipts,
thresholds, masks, triggers and failure reports are published in
[`downstream01`](results_radio_whole_cadence_handoff_2026-09-28/downstream01).

The 127 engineering receipt identities in these fixed score fixtures are not
127 independent null draws and consume none of the proposed 127-null budget.
Their law explicitly states that distinction. The 134 serialized engineering
case identities do not collide with any identity in the inactive scientific
proposal. Interface fixture execution took less than one second. Retained new
evidence at postflight is 2,831,874 bytes, below the 128 MiB scope ceiling.
Per-kind byte accounting refers to the canonical retained-member stream;
shared metadata and the complete persisted artifact have a separate total
bound. An integrated scientific runtime must enforce its full stage budget.

## Preserved state and precise continuation

The 15 historical invariant pins, HD189733 preparation and 127/24 proposal are
unchanged. Development6, failed calibration3, one closed evaluation allocation
with zero evaluation values/runs, and the one retained-score diagnosis stay
closed. Old24 evaluation identities remain unusable/unopened. The old synthetic
acquisition ledger remains exhausted; the telescope genesis is inactive.
Neighbor9, M43AI failed/closed, original112+128M43AF holdouts, M15/M33 unresolved,
HD1461 pointing hold, untouched GJ724 reserve, LS8BD–BE pause/LS8BF untouched and
unsent CHEOPS are preserved. No external messages or plan extension; consolidate
on 9 October.

**Completed:** codec-to-receiver deterministic source/law receipt handoff,
native-success maximum reduction, distinct whole-cadence threshold and full
ON/OFF retention/rank interfaces. Do not replay these fixtures or the prior
closed codec/calibration/development executions as new progress.

**Next:** integrate the distinct retention receipts with matched-OFF,
single-adjacent-OFF, receiver-alias and clustering stages, preserving every
physical veto and fixed numerical rule. The legacy physical validators cannot
consume the new receipts by relabelling them. Also bind the proposed Gaussian
renderer to its exact law, case and source identities; the deterministic codec
handoff does not qualify that renderer. Then freeze and verify one executable
prospective synthetic protocol with all recovery/RFI/null gates, current code
and runtime pins, crash-safe result retention and cumulative resource/trial
accounting. The 127/24 proposal remains **PROPOSED_NOT_ACTIVATED** until a
separately authorized fresh allocation and published/readback freeze exist.
No original preparation contract may be rewritten to ready. A synthetic pass
still requires separate integrated acquisition/trial admission before opening
any telescope spectrum.

Evidence index: [postflight](results_radio_whole_cadence_handoff_2026-09-28/postflight.json),
[30 downstream tests](results_radio_whole_cadence_handoff_2026-09-28/downstream_tests_initial.log),
[11 source tests](results_radio_whole_cadence_handoff_2026-09-28/source_tests_initial.log).
No unexpected test or execution failure occurred in this scope. A grid-binding
check was strengthened during pre-exposure implementation review, before the
first test or native execution.
