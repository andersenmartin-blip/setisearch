# M43AG: exact retrospective boundary obstruction audit

## Question and scope

M43AF found no feasible boundary among 1,156 frozen quantile-grid points.
This named diagnostic asks whether a finer grid alone could satisfy the same
training requirements, using the **unchanged** rule x >= a and y < b and the
unchanged, sealed geometry/rank-eligible member coordinates.

The only inputs are the 241 public closed training/baseline/null records at
`bdab6b0af39d6bc6c81ce9d5f07ef24c103ca833`. The decision seal is
`e1ef8cfc261a4b155695cc61d3cbda875ca35ff9aef7c8b0cff20b03c48bf7a3`.
All record file hashes, content seals, source freeze/configuration identities,
case names, phases and native payload identities must match that decision.

This is descriptive analysis of already measured training data. It does not
fit or adopt a new detector, change M43AF, rerun an acquisition, open validation,
or report an independent performance estimate. The 112 validation injection
inputs and 128 held-out native nulls remain unopened. A future changed detector
still requires its own public protocol and fresh evaluation inputs, and general
adoption requires an independent observing sequence.

The M43AF complete historical archive is not an input. M43AG can be reproduced
from the already public M43AF **training** archive even if the complete release
is not yet public.

## Fixed diagnostic endpoints

1. Minimum number of the same 57 required training signal cases lost when all
   control, baseline and null members are excluded, over every real-valued
   boundary in the unchanged two-coordinate rule family.
2. Minimum number of leaking non-signal cases when all 57 required cases are
   recovered, over that same family. Report impossibility explicitly if a
   required case has no eligible associated member.
3. Complete member-level dominance witnesses for each required case, naming
   controls that make a signal member inseparable under the monotone rule.
   Distinguish individual dominance from a joint conflict across several cases.
4. Independent reproduction of the recorded aggregate costs at all original
   1,156 grid points, preserving the original failed qualification.

## Exhaustive calculation without a numerical grid approximation

All finite member coordinates are fixed binary64 values, compared directly
without epsilon or rounding. Changing a only changes membership at a recorded
x. Enumerate each distinct eligible-member x as an inclusive lower cut, plus
one state above the maximum. The smallest recorded x also represents no ON
bound. Process equal x values together before evaluating a state.

At a fixed lower cut, let s_i be the smallest y among eligible, truth-associated
members of required signal case i with x >= a. Let c_j be the smallest y among
all eligible members of non-signal case j with x >= a. An empty set has minimum
+infinity for calculation only; it is serialized explicitly, never as a
nonfinite JSON number.

For zero leakage, the largest allowed upper cut is b = min_j c_j. Because the
OFF comparison is strict, exactly the required cases with s_i < min_j c_j can
be recovered. If there are no qualifying control members, there is no OFF bound.

To recover all required signals, every s_i must be finite and b must be strictly
greater than q = max_i s_i. The smallest possible leaking-case count therefore
equals the number of c_j <= q. A real b just above q, and no greater than the
next distinct control minimum when one exists, realizes that count. This
describes an interval; no deployable boundary is selected.

Taking the extrema across every ON-cut equivalence class is exhaustive for the
fixed finite coordinates. This makes no claim about other features, nonmonotone
classifiers, new noise realizations, or population generalization.

## Dominance certificates

If control member c has x_c >= x_s and y_c <= y_s, every rectangle accepting
signal member s also accepts c. Equal values retain the inclusive ON and strict
OFF semantics. Choose the first witness in case-name/member-ID order for
deterministic evidence. Check every associated eligible member; a missing
eligible association is reported separately. Multiple members from one control
still count as one leaking case. Repeated native payloads are not independent
examples.

## Verification and outputs

Before running on the sealed training coordinates, test ties, signed values,
empty inventories, multiple members, missing associations, joint conflicts,
source/certificate tampering, and 100 seeded synthetic fixtures against an
independent complete Cartesian enumeration of all small-fixture rectangles.

The real-data auditor independently rescans every case/member for every ON cut,
checks each recorded cost, both headline optima, all optimal-state indices,
the case/cut inventories, every dominance witness, its deterministic ordering
and each impossibility reason, and reproduces the original grid aggregates.
Synthetic tests must reject corrupted headlines and certificates before
execution on the closed training records. Publish the script, tests, input hash inventory,
complete ON-cut ledger, certificates, result summary and file hashes.

```bash
PYTHONPATH=scripts python -m unittest discover -s tests -p 'test_m43ag_boundary_obstruction.py'
python scripts/m43ag_boundary_obstruction.py
```

Python's standard library is sufficient after restoring the byte-identical
M43AF training records. Restoration of the existing gzip transport uses the
archive-recorded Python/zlib versions. No raw telescope source is needed for
this diagnostic. The script refuses changed source seals and differing existing
diagnostic outputs. It reports zero new detector executions and zero additional
observing sequences.
