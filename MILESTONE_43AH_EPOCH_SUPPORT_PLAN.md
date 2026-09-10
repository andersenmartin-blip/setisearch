# M43AH — integrated epoch-support development plan

This is a fixed retrospective development study on already public, closed
training evidence. Publish and verify this plan, code, tests and source
preflight before extracting the two new features across the training panel.
The study cannot establish independent validation or detector adoption.

## Motivation and source boundary

M43AG proved that the original two-coordinate rectangle cannot preserve all
57 required training signals while rejecting every control/baseline/null member.
The exact control-free optimum loses training057, whose associated members are
dominated by controls in the original ON/OFF coordinates.

The design uses that public diagnosis and a schema inspection of training057.
That case contains unequal two-epoch signal plus a strong single-epoch
interferer. Its weak-epoch profile can have a negative signed projection onto
the strongest-epoch profile even while its center score is positive. This
motivates testing observable second-epoch support without fitting a profile
template to injected truth. These design inputs are explicitly retrospective.

Use only the 241 records at public M43AF training commit
`bdab6b0af39d6bc6c81ce9d5f07ef24c103ca833`: 112 injection inputs (64 signals,
48 controls), 128 native nulls and one baseline. The immutable failed model
decision seal is
`e1ef8cfc261a4b155695cc61d3cbda875ca35ff9aef7c8b0cff20b03c48bf7a3`.
Verify each source file hash, content seal, name, phase, native identity and
source freeze/configuration binding. The public M43AG summary and exact
sweep/auditor implementation are pinned by SHA256 in the new script.

Do not read the 112 held-out injection inputs or 128 held-out native nulls.
The unpublished M43AF historical archive and raw telescope data are not inputs.
Earlier scientific files, endpoints, rejections and denominators remain intact.

## Frozen observable feature definitions

Keep the same geometry/rank-eligible member inventory and retained carrier,
width, motion template, epoch subset and both OFF mappings. Let E be that
member's canonical active subset of two or three epochs. At its unchanged
carrier/width, define:

- O_e: the original retained ON center score in epoch e.
- F_e,r and F_e,t: the original interpolated OFF center scores for receiver-mean
  and candidate-track mappings, respectively.
- P_e = max(0, F_e,r, F_e,t).
- D_e = O_e - P_e.

There are exactly two proposed ON-support coordinates:

1. `second_epoch_on`: second-largest O_e over e in E.
2. `second_epoch_excess`: second-largest D_e over e in E.

OFF subtraction occurs separately in each epoch before ranking. Negative ON
or excess values are retained. Negative OFF fluctuations give no positive
bonus. Both mappings are used, with no fitted lag, alternate carrier, best-bin
search, amplitude normalization or truth-derived feature.

For two active epochs this statistic is the smaller value. For three it is the
middle value: the new endpoint deliberately tests support in at least two
active epochs rather than requiring all three. It does not rewrite the original
activity/confirmation definition. All active profiles must nevertheless exist
and be complete. An inactive epoch cannot fill missing active evidence.

For both families, keep the old M43AF OFF coordinate y bit for bit:
the maximum of the two mean signed OFF-profile projections divided by the
original width scale. The new conditional member rule is z >= a and y < b,
where z is one of the two definitions above. Scores are observable development
coordinates, not calibrated sigma values or independent samples.

The feature function accepts observable member/measurement fields only.
Injected labels and truth associations enter case-level recovery accounting
and training requirements, never feature construction or member acceptance.

## Full-family comparison and signal-loss accounting

For each family independently, exhaust every acceptance-equivalent real
boundary using the pinned M43AG exact sweep. Do not use a quantile grid, tune
the feature definition after seeing outcomes, select a preferred family, or
open another dataset within this study.

The fixed required set remains the same 57 training signal cases recovered by
the union of neighbor9 and centered_receiver_off_match_aggregate. For every
ON-cut state, derive the exact OFF ceiling needed to reject all non-signal
members and the minimum case leakage compatible with recovering all 57.

Report for both families:

- The minimum required-signal losses when every control/baseline/null member
  is rejected, with the complete ON-cut ledger and all optimum indices.
- The minimum leaking non-signal cases when all 57 required cases are recovered;
  serialize impossibility explicitly when no eligible association exists.
- All member dominance certificates and individually impossible required cases.
- At every zero-leak optimum, exact recovered/lost case identities among all
  64 signal cases, and gains/losses against each original reference separately.
- The old M43AG costs (1/57 losses or 8/48 control leaks) as published reference
  values, without rerunning that closed diagnostic.

Joint training feasibility means zero required losses and zero non-signal
leaks on these same closed cases. It is only a development finding, even if
either family meets it. No model/boundary is selected, no previous failure is
overturned, and no qualification on fresh inputs is claimed.

## Independent arithmetic and source checks

Primary extraction reads retained ON center values and sealed M43AF OFF
measurement rows. A separate scalar path reconstructs ON centers from the
original stored profile vectors and OFF centers from their left/right samples
and interpolation weights. It verifies profile identities, full spans, both
copies of the ON vector, the per-epoch arithmetic and each second-order
statistic. The oracle uses maximum pair minima rather than sorting.

All new coordinates used for boundary comparisons are the primary stored-
measurement calculations, with ordinary binary64 arithmetic and exact
inclusive ON/strict OFF comparisons. The independent interpolation/feature
check uses fixed relative and absolute tolerance 1e-11; this tolerance never
changes acceptance, threshold equality or the exact sweep partition.

The pinned M43AG scalar auditor independently rescans every cut, fixed
required-case denominator, optimum, optimum index, inventory, dominance
witness, deterministic witness choice and impossibility reason. A further
direct case reduction at every zero-leak optimum checks the reported
all-signal and per-reference gains/losses.

Before real feature extraction, test two/three active epochs, ties and signed
values, inactive-epoch exclusion, strong single-epoch outliers, both OFF
mappings, negative-OFF clipping, subtraction before ranking, truth-field
independence, missing/inconsistent measurements, raw profile/interpolation
tampering, altered source identities and case-recovery accounting. One hundred
seeded synthetic fixtures cover every canonical activity subset with the
separate scalar oracle. Reuse the already tested unchanged M43AG algorithm.

Missing evidence, source mismatch or an arithmetic/audit failure blocks
completion; do not drop affected members or silently substitute a partial
profile. Check all destinations before writing and preserve differing
previously completed outputs.

## Outputs and next boundary

Publish the feature ledger, both complete family sweeps/certificates/case
accountings, immutable input identities, audit counts, summary, output hashes
and readable result. Record the verified public plan commit before execution.

```bash
PYTHONPATH=scripts python -m unittest discover -s tests -p 'test_m43ah_epoch_support.py' -v
python scripts/m43ah_epoch_support.py
```

These commands run from the science checkout after exact restoration of the
already public M43AF training archive. A relocated input checkout may be
specified with --root and a separate output directory with --output. The
public M43AG reference and pinned script remain beside the new study code.
The original archive-recorded Python/zlib versions apply to byte-identical
restoration; feature analysis itself uses the Python standard library.

The study adds two downstream development-rule evaluations and new derived
member features, with zero full native-pipeline detector executions, zero
native acquisitions and zero additional observing sequences. Empty baseline
or native-null retained sets do not supply conditional tail observations.
No physical false-alarm rate, astronomical candidate or general completeness
estimate follows from this training analysis.

Any later selection and prospective evaluation requires a new explicit
protocol and fresh evaluation inputs; the old held-out panels stay unopened.
General adoption also requires an independent observing sequence. Continue
from PROJECT_STATUS.md after publishing the result.
