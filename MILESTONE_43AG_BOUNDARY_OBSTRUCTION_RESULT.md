# M43AG — exact retrospective boundary obstruction result

**A finer boundary search reduces the control-free training loss from four
required signals to one, but cannot make the unchanged rule family qualify.**

The diagnostic was published and verified at
[119cac8](https://github.com/andersenmartin-blip/setisearch/commit/119cac883efefeb548a8a49386e3e026d33f6872)
before execution. It uses only the 241 closed M43AF training/baseline/null
records published at
[bdab6b0](https://github.com/andersenmartin-blip/setisearch/commit/bdab6b0af39d6bc6c81ce9d5f07ef24c103ca833).
No detector, native acquisition or validation panel was executed.

## Result

| Same requirement on the closed training records | M43AF frozen 1,156-point grid | M43AG all acceptance-equivalent real boundaries |
|---|---:|---:|
| Reject every control, baseline and null member: minimum required signal losses | 4 of 57 | **1 of 57** |
| Recover all 57 required signal cases: minimum leaking control cases | 8 of 48 | **8 of 48** |
| Jointly recover all 57 and reject every non-signal member | Impossible in that grid | **Impossible throughout the unchanged rule family** |

The family is `x >= a and y < b`, using exactly the recorded M43AF ON/OFF
coordinates, eligibility and truth-association rules. M43AG examines all
**2,514 ON-cut equivalence classes** of the 3,497 eligible members. At each cut,
it computes the exact OFF ceiling for zero leakage and the exact minimum
leakage compatible with recovery of every required case. Thus the continuum
is exhausted for these finite recorded coordinates without approximating it
by a denser numerical grid.

The original 1,156 grid points reproduce exactly. There are 16 ON-cut states
attaining the one-loss, zero-leak optimum and 267 attaining the eight-leak,
all-required optimum. They are diagnostic equivalence classes, not independent
trials. No boundary is selected or adopted.

The 57 required cases are the unchanged union recovered by the two M43AF
reference methods among 64 training signal injections. They are not the entire
signal population, and 56/57 is not an astronomical completeness estimate.
The 48 training control cases remain a separate denominator from the 128
native nulls and one baseline. All nulls and the baseline have zero eligible
members; they contribute no conditional profile-tail observations.
The eight leaking cases correspond to four distinct native payload identities,
not eight independent noise realizations.

## Why one loss is unavoidable

`training057` has 11 eligible associated members. Every one has a non-signal
member with at least as large an ON coordinate and at most as large an OFF
coordinate. Any boundary in this family accepting that signal member must
also accept the corresponding control member.

The deterministic certificates use one member of `training004` for seven
signal members and one member of `training032` for the remaining four.
Two examples are shown below; values here are rounded for display, while the
calculation and [complete certificates](results_m43ag_obstruction/dominance_certificates.json)
retain the original binary64 values.

| Signal member prefix in training057 | Signal ON | Signal OFF | Dominating control | Control ON | Control OFF |
|---|---:|---:|---|---:|---:|
| `1b5ccb82` | 0.167910 | 0.396290 | training004 | 0.675801 | 0.167803 |
| `82245008` | 0.364727 | -0.026663 | training032 | 0.404840 | -0.110020 |

For an inclusive ON lower cut and a strict OFF upper cut, both inequalities
force the control to pass whenever the signal passes. This covers all 11
associated members of training057, proving the lower bound of one lost case.
The full sweep also exhibits zero-leak states recovering the other 56 required
cases, so the bound is attained.

Across all required cases, 72 individual member-level dominance witnesses are
verified. Training057 is the only case for which all eligible associated
members are individually blocked. The eight-control lower bound for retaining
all 57 comes from the exhaustive joint calculation; it is not inferred merely
from those two illustrative witnesses.

## Independent checks and evidence

- All 244 files from the public training archive match their recorded hashes.
  The public model-decision and archive-manifest Git blob identities match.
- All 241 record file hashes, content seals, phase/name/native identities and
  source freeze/configuration bindings are checked against the immutable
  failed training decision.
- Eighteen synthetic tests pass, including 100 seeded small fixtures compared
  with independent complete Cartesian rectangle enumeration.
- The independent scalar auditor rescans every ON class and performs
  8,791,458 member visits. It checks the entire sweep, headline optima, optimal
  indices, fixed required-case denominator, inventories and certificates.
- All 72 dominance witnesses, deterministic witness choices and impossibility
  reasons are checked. Both the scalar audit and original-grid audit pass.

The review found and repaired audit gaps before the diagnostic freeze: corrupted
headline optima and required-case inventories now fail, certificate reasons and
ordering are checked, and impossible historical recovery is represented
explicitly. The original M43AF scientific code and results were unchanged.

[Machine-readable summary](results_m43ag_obstruction/summary.json) ·
[Complete ON-cut ledger](results_m43ag_obstruction/on_cut_sweep.json) ·
[Input identities](results_m43ag_obstruction/input_manifest.json) ·
[Output hashes](results_m43ag_obstruction/manifest.json) ·
[Verified public freeze](results_m43ag_preparation/public_freeze.json) ·
[Tests](results_m43ag_preparation/focused_tests.log)

## Interpretation and next scope

Grid coarseness explains three additional required-signal losses in the original
zero-leak grid optimum. It does not explain away the failed joint qualification.
Changing only grid density cannot meet both original requirements on these
closed training coordinates.

If those recovery and rejection requirements are retained, the next integrated
design must change the response representation or acceptance-rule family.
The known obstruction can be used as a development constraint. It cannot become
a fresh validation example, and a new protocol must be frozen before evaluating
fresh inputs. General detector adoption still requires an independent observing
sequence.

An initial design hypothesis is to retain observable compatible support across
epochs when a strong single-epoch interferer is present. The blocked training057
case contains an unequal two-epoch injected signal mixed with such interference;
the eight leaking control cases contain interference alone. Any new feature
must use observable data rather than injected truth labels. This diagnosis does
not establish that the proposed feature would succeed.

This is retrospective analysis of one observing sequence, including repeated
native payloads (104 distinct training payloads). It measures no physical
false-alarm probability or additional sky coverage and claims no astronomical
candidate. The 112 validation inputs and 128 held-out native nulls remain
unopened. M43AF's complete historical archive remains a separate pending
publication; it was not needed or uploaded for M43AG.

Continue from [PROJECT_STATUS.md](PROJECT_STATUS.md).
