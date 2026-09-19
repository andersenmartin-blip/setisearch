# LS8B numerical review: preserve the frozen failure and test an arithmetic repair

The first frozen audit stopped at a near-zero excess comparison. A complete
review at the unchanged 2e-8 relative / 2e-10 absolute tolerance finds exactly
two mismatches among 31,668 numerical field comparisons: two event sums, not
scores, in TG000303 row 699/duration 2 and TG000304 row 522/duration 3.
The differences are 2.384185791e-7 and 8.940696716e-7 electrons on per-row
fluxes near 3.9e8 electrons. Preserve the first failure log, frozen source,
every original ledger value, and the **FAIL** status of the frozen audit.

The audit's `--complete-review` option was added after that failure solely to
finish the accounting. It retains the exact tolerances and records FAIL when
any mismatch remains. It changes no producer calculation or scientific gate.

A separate 60-decimal reference solves the same OLS equations for all 7,917
eligible windows, starting from exact Decimal conversions of the binary64
inputs and the same time coordinates. The largest score difference from the
frozen producer is 4.5711e-11. No signed threshold decision changes. One
producer event sum still violates the original relative comparison against
this more accurate reference; the frozen failure is not waived.

## Closed-data numerical repair, specified before its evaluation

The separate `cheops_l2_stable.py` implementation subtracts the median raw
sideband flux before the OLS fit and sums event excesses in those centered
coordinates. Translation of an intercept-containing linear model is an
algebraic identity; it reduces cancellation in finite arithmetic. The raw
flux is still used in the original noise floor. Durations, context eligibility,
sidebands, guards, baseline model, noise estimator, thresholds and clustering
are unchanged. `cheops_l2.py` remains byte-identical to its public freeze.

Two new known-answer tests cover large backgrounds with tiny positive,
negative and zero pulses and preservation of the raw-flux noise floor. They
must pass before evaluating the repair on the retained LS8B table bytes.

Compare every eligible/ineligible window, all four numerical quantities against
the independently saved 60-decimal reference at the original tolerances, and
both signed threshold decisions against the frozen original. Publish every
mismatch. No new archive bytes may be acquired. This is a retrospective
implementation repair on closed data, never a second held-out evaluation.
Its result cannot replace the original audit failure or qualify a detector.
