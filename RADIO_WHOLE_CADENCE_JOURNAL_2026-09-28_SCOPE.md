# Whole-cadence consumption and restart integration — prospective engineering scope

28 September 2026; parent checkpoint `4360136e3e083f1567a9dc449c09b1a85b788acd`.
The physical/mock/gate fixtures in that commit are closed. This scope addresses
new write-ahead consumption, publication ambiguity, archive integrity and
renderer admission risks. It does not activate the 127/24 proposal.

## Fixed work and limits before execution

Implement a separate case-consumption ledger, not an extension or reset of the
exhausted acquisition ledger. Bind ordered case/plan/source/context/law and
execution identities. Require a compare-and-swap publication and exact readback
before returning any process-local permission. Reserve time/evidence quota before
work, without refunds, and reject duplicates, skipped cases, ambiguous publication,
changed runtime/code and interrupted cases. A consumed case cannot be redrawn;
an incomplete attempt cannot continue to the next case. Restoration is read-only.

Archive immutable bytes before recording completion; require the exact declared
artifact inventory and hashes. Missing bytes, a torn write or a crash during
finalization is incomplete, never a typed EMPTY. Completed artifacts may be
rehydrated without granting a new execution lease. The remote store and its
independent checkpoint/readback remain explicit trust boundaries; a local hash
alone is not proof of publication. Filesystem-backed stores are engineering-only.

Connect the Gaussian entry to a one-use scientific lease and the frozen draw
schedule. Exercise its rejection paths without calling the proposed generators.
Do not accept an engineering lease or a self-activating plan as scientific
authority. A future executable freeze must separately bind all code/runtime
dependencies and a newly authorized allocation; none is issued by this scope.

Qualify the new journal with tiny, disjoint deterministic cases (including real
subprocess termination before/after consumption and artifact/finalization writes).
Use two already published mock source archives for the new source/score durable
handoff: restore their original identities, compute their previously uncomputed
native scores once, archive complete vectors/ancestry, then rehydrate and verify
them in another process. No new mock draw or scientific recovery measurement.
Preserve any technical failure and do not silently rerun an experimental runner.

Engineering ceiling: 1,200 active seconds, 512 MiB RSS, 256 MiB modeled arrays,
128 MiB new retained evidence. At most two retained-source score computations;
no new Gaussian values, calibration/evaluation allocations, source requests or
telescope values. Test failures may be corrected with separately retained logs;
they are not permission to repeat scientific cases. Existing invariant pins,
preparation contracts and all prior dispositions remain untouched.

The full native physical/gate chain and a complete prospective scientific runner
may still require a subsequent bounded integration scope. A journal pass is not
an executable freeze, a scientific pass or telescope admission. Consolidation
remains 9 October; no external messages or plan extension.
