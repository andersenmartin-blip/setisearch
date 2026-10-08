# Independent VAL_A wrapper review — 8 October 2026

**PASS for static preparation; execution admission is separate.** No validation
values, RNG, generator or detector were invoked. The wrapper was read and
AST-parsed; all eight embedded original scientific/shared file hashes and both
new preparation-manifest hashes were independently matched to current files.

The reviewed wrapper is `pilot_engine_20261008/run_validation.py`, SHA256
`de3bd90d787a05449a51f232eb01a52355449737cfe9363d97048dfa4ab6e313`.
It preserves the pre-DEV detector, generator, preprocessing, thresholds,
geometry, output helpers, case banks and summarizer. It requires a new public
VAL_A admission, exact hash-bound complete DEV outcomes and summary, and a
reviewed same-science readiness statement before generation. Recomputing the
DEV summary catches missing, duplicate and failed DEV outcomes.

The complete 142/24/142 VAL_A/DEV/VAL_B identity and seed banks are checked for
correct panels and pairwise disjointness. Only one explicitly admitted VAL_A
case can run. Before generation, an exclusive persistent claim is created;
all jobs must use the same designated claim directory. A failed or completed
claim cannot authorize a repeat or switch to VAL_B. New output directories
are required.

The runner saves all six full maximum maps, every threshold ON carrier and
its complete OFF comparisons, truth and synthetic array hashes, localized
pre-OFF/final recovery in every active ON, partial failures and resources.
Full scientific code uses all 4096 ON carriers and all 5415 drift values.
The exclusive allocation is at most 250 CPU seconds per invocation. Measured
resource violations explicitly set integrity false and return failure.
The root coordinator remains responsible for the aggregate cap and exclusive
allocations across concurrent jobs.

One completed case does not evaluate the panel gate. A full fresh VAL_A panel
has 142 cases: 14 strong, 48 operating, 24 matched RFI, 32 noise, 12 single-row
transient and 12 near-OFF diagnostic cases. The same frozen joint gates require:

- All 142 distinct cases present with valid integrity and no failure.
- Strong localized all-active recovery in 14/14 cases.
- Operating all-active recovery in at least 44/48; at least 7/8 per activity
  subgroup, 10/12 per drift subgroup and 22/24 per intrinsic-width subgroup.
- Primary localized pre-OFF recovery in all 24 matched-RFI cases, with zero
  matched-RFI cadences retaining any survivor.
- At most one of 32 noise cadences retaining any survivor.

The static operating bank has exactly six activity groups of eight, four
drift groups of twelve and two width groups of twenty-four. The diagnostic
families remain required complete outputs, outside the operating denominator.
These gates qualify the declared synthetic laws and exploratory method only;
they do not calibrate sky false alarms or admit pilot values by themselves.
