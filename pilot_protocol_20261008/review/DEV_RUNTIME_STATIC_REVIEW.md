# Independent correction-1 DEV runtime review — 8 October 2026

**Static PASS for the two prospective DEV_RUNTIME jobs only.** The reviewer
read/AST-parsed code and checked hashes, recipes, identities, metadata and
arithmetic. No arrays, RNG, native imports, rendering or search were invoked.

The reviewed `run_dev_runtime.py` SHA256 is
`56c655e283dc7ac13e4f210df7e3862c68c6f97e75f47fb883dc5affb7c860d9`.
The coordinator and all exact preparation hashes are retained in the paired
`DEV_RUNTIME_STATIC_REVIEW.json`.

All eleven fixed scientific/bank/closed-A bindings match current files. The
two new full-SHA256 seeds and DEV_RUNTIME identities are disjoint from original
DEV, A and B. Their physical recipes equal A128/129 except identity, panel and
seed. A remains precisely its original FAIL_CLOSED, with both timeout failures,
and is recomputed before native imports or RNG. Neither A nor B is replayed.

The correction changes operational allocation only. The original detector,
generator, helper, contract, thresholds, complete 4096-carrier/5415-drift family,
OFF comparisons and recovery definitions stay unchanged. Canonical exclusive
claims and output paths refuse repeated identities. Completion requires the
original full output set and successful guarded flush/hash/resource checks;
the final COMMITTED marker is the sole success authority. Failure removes or
invalidates that marker and preserves the failed claim. CPU/wall watchdogs
remain armed through finalization; a 4 GiB address-space guard and one-thread
native-library environment apply before native imports.

Two independent 1800-CPU-second partitions reserve 3600 seconds, fitting
24,292.071999981 seconds after closed A and the root's separate 1200-second
unmeasured-preparation planning reservation. Their remaining planning-adjusted
capacity is 20,692.071999981 seconds before actual refunds. Each still has the
unchanged 1800-second wall and 4 GiB memory caps. Whole reaped child and
coordinator costs must be charged on close; missing/failed receipts are not
zero-cost proof.

The approved plan allows one development correction followed by wholly fresh
validation. These two jobs prove only the operational correction. B must
remain untouched until both actual proofs are complete and a separate B scope
is frozen. Rolling reservations must protect active jobs without double
spending and stop new admissions if a full next partition cannot fit. Neither
this preparation nor its success guarantees B completion or pilot admission.
