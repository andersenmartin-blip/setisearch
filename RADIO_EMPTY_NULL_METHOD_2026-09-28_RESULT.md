# Empty outcomes and null-reference validity — method result, 28 September 2026

**The method study is complete. Empty outcomes can be retained in an exact
inclusive rank. This does not qualify the previous guarded-shift null design
or reopen its failed attempt.** A separate, unactivated
[whole-cadence proposal](RADIO_WHOLE_CADENCE_NULL_2026-09-28_PROTOCOL_PROPOSAL.md)
now specifies 127 fresh reference cadences and 24 fresh evaluation identities.
No new random/native control, evaluation or telescope spectrum was generated.

Continuation checkpoint: `e5841013b40b069eceb5fb7d5d64fd31a01b8764`.
The owner's 28 September continuation permits this bounded method/preparation
work. Its [scope](RADIO_EMPTY_NULL_METHOD_2026-09-28_SCOPE.md) was written before
the one exact audit; it allocates zero new scientific attempts. The old
3-calibration/one-evaluation allocation and single diagnosis remain closed.

## Statistic and rank, including the empty atom

Let one complete cadence produce all eligible ON hypothesis scores under the
fixed mask, bank, activity rule and stack. Define its statistic as their maximum
if any exist, and the distinct symbol EMPTY otherwise. Order EMPTY below every
finite real score. It is a legitimate statistic outcome, not an absent draw,
a zero-valued score or a reason to shorten the reference table. Numerical NaN,
positive/negative infinity and incomplete computation remain errors.

`src/seti_repeater/empty_null_radio.py` implements this tagged representation,
strict JSON round trips, higher quantiles and exact `Fraction` ranks. It cannot
produce a detector certificate or telescope admission. It does not import a
data reader, random generator or legacy calibration adapter.

For an observed statistic T0 and B references T1,...,TB, use

`p = (1 + count(Tb >= T0, b=1,...,B)) / (B+1)`.

All B observations stay in the denominator, including EMPTY. An EMPTY
observation has p=1. A tie counts against rejection; no randomized tie breaking
is used. The operational screen also requires a finite score at least
`max(10, highest reference statistic)`. If all references are EMPTY, that
additional floor is still 10. This is arithmetic, not by itself a valid p-value.

**Our proof of the bound:** assume the B+1 whole-cadence statistics are jointly
exchangeable under the stated null. Write N=B+1 and, for each position i,
`r_i = count(j: Tj >= Ti)`. For any integer k, at most k positions have
`r_i <= k`; inclusive ties can only decrease that number. Conditional on the
unordered multiset, the observed position is uniform by exchangeability.
Consequently `Pr(p <= alpha) <= floor(alpha*N)/N <= alpha`, also for multisets
containing EMPTY. The independent-draw model proposed here is one sufficient
way to obtain exchangeability. Equal marginal distributions alone are not.

The cadence maximum bounds every eligible member score. Ranking a member
against the same reference maxima therefore cannot give a smaller rank than
ranking its cadence maximum. Thus the probability of *any* member passing the
rank rule is bounded under that whole-cadence null. The fixed floor and
subsequent physical vetoes only remove members. This argument requires the
entire prospectively fixed hypothesis family; it is not a collection of
uncorrected individual-template tests.

The bound is marginal over random reference and observed cadences. It is not
a guarantee conditional on a particular realized reference bank, a measured
tail estimate, or a telescope/RFI error bound. Reusing a reference bank across
evaluations couples their decisions; this does not establish a project-wide
or period-wide 1% error guarantee. With deterministic pseudorandom software,
the exact theorem concerns the ideal stated sampling model; distinct seeds
alone do not prove independence or exact random sampling.

## Exact evidence and its extent

The one audit enumerated every multiset of lengths 2 through 8 over
`{EMPTY, -2, 0, 1, 3}`, every possible observed position and every integer rank
cutoff. All arithmetic was exact. Retained evidence is in
`results_radio_empty_null_method_2026-09-28/exact01/`.

| Check | Result |
|---|---:|
| Complete finite histograms | 1,281 |
| Distinguished-position ranks | 8,575 |
| Rank-bound inequalities | 9,856 |
| Violations | 0 |
| New rank/identity interface tests | 17 passed |
| New complete-family/reference boundary tests | 18 passed |
| Exact-audit runtime / peak process RSS | 0.099124315 s / 13,500,416 bytes |

The finite enumeration supports the implementation; the proof above supplies
the general result. It does not establish the null model of the old detector.
Tests cover the EMPTY atom, ties, floor, sample size, strict serialization,
duplicate proposed identities and the absence of admission authority.

| Reference size B | Smallest possible inclusive rank | Can reach 0.01? |
|---|---|---|
| 3 | 1/4 | No |
| 99 | 1/100 | Yes, without a reference tie/exceedance |
| 127 | 1/128 | Yes, without a reference tie/exceedance |

These are fixed mathematical examples, not newly exposed controls. Three
old realizations do not become 381 independent observations by using 127
conditional shifts on each. Neither those shifts nor the closed three maxima
are reused as the new proposed reference set.

## Connected implementation: complete maximum versus missing computation

The separately scoped
[reference engineering step](RADIO_WHOLE_CADENCE_REFERENCE_2026-09-28_SCOPE.md)
is also complete. `src/seti_repeater/whole_cadence_reference_radio.py` reduces
a complete score inventory to a typed maximum and binds exactly 127 ordered
receipts. It preserves every EMPTY outcome. It rejects missing or extra
vectors, changed score/case/context identities, nonfinite inputs, incomplete
hypothesis counts, duplicate/reordered units and changed external bindings.

One concrete boundary required attention: the legacy stack helper maps
nonfinite results to its ineligible sentinel. The new adapter independently
checks the eligibility mask and rejects a nonfinite score in an eligible
cell, so float32 overflow cannot masquerade as EMPTY. No old kernel changes
or old score reads were needed. All 18 new deterministic fixture tests passed
on their first run; together with the first suite there are **35 distinct new
tests**. Fixtures used a two-template toy grid, fixed score arrays and their
own namespace, never the proposed controls or Gaussian/native realizations.

The reference bundle remains engineering evidence without a detector
certificate. Its hashes bind records but do not prove a noise distribution,
authenticate arbitrary external claims or establish exchangeability. The
NativeRun wrapper's successful path has not been qualified; tests exercise
its rejection of an unsupported input. Future source records must bind both
the fresh case and the noise law. The old renderer does not supply that
additional law field. Full native/runtime and downstream integration remain
named requirements, not implied by these 18 tests.

## Why simply accepting empty old shifts is insufficient

The old guarded-shift sampling universe, with identity included, has 290
elements inside `Z_81 x Z_81`, whose full size is 6,561. The published offsets
32..48 fail group closure and inverses: `(32,32)+(32,32)=(64,64)` and the inverse
`(49,49)` are outside that universe. The old draw is uniform over 289 guarded
pairs, not over the full ambient group. No applicable alternative validity
proof was published for that restriction.

This is a missing sufficient justification, **not a measurement of the actual
detector's false-alarm rate**. A randomly sampled subset need not itself be a
group under a valid random-permutation construction. The issue is the sampling
law and null invariance, not merely lack of closure of 127 sampled rows.

Two fixed examples isolate distinct assumptions without reading old scores:

* For a uniform origin in Z5, statistic `(4,3,2,1,0)` and the next cyclic shift
  as the sole reference, four of five ranks equal 1/2. Rejection at nominal
  1/2 occurs with probability 4/5. Marginal invariance of a chosen transform
  does not suffice for the rank rule. This is an abstract counterexample, not
  the receiver pipeline.
* Let `Yi=(Xi+Xi+1+Xi+2)/sqrt(3)` for 81 carriers and independent unit-variance
  raw values. Neighbor covariance is 2/3, whereas endpoint covariance is zero.
  Rolling the finite score axis takes a neighboring pair across that seam,
  so raw iid noise alone does not imply cyclic invariance of filtered scores.
  This example omits robust normalization, other templates/widths and masks.
  It does not assert a covariance or error rate for the full detector.

The earlier failure remains exactly its published finite-support-prerequisite
failure. Describing EMPTY as a legitimate ordered outcome corrects the broader
mathematical interpretation; it does not retroactively change that protocol,
issue its missing certificate, or turn its result into a pass.

## Concrete next method and budget boundary

The new proposal uses 127 independently generated whole synthetic cadences,
each reduced once to the complete maximum or EMPTY. It uses no score shifts.
It preserves neighbor9, all 81 rate labels, eight widths, active-epoch rule,
floor 10, inclusive rank ceiling 0.01 and the unchanged 24 recovery/RFI/null
recipes, with new namespaces and seeds. A metadata collision audit inspected
273 published JSON configurations and two additional identity metadata files;
all 151 proposed namespaces, seeds and case identities are distinct from that
inventory. This checks identifiers, not statistical independence.

The proposal carries its exact frequency windows, source/score-map pins,
noise law, gates and cumulative counters. Its status is
**PROPOSED_NOT_ACTIVATED**. It requires the reference bundle's native/runtime
qualification and a distinct downstream certificate adapter, verified executable freeze and a fresh
allocation before any of its values. The current study charges **zero** new
calibration/evaluation/remedy/pilot attempts. Reopening the old runner is not
an implementation of this proposal.

Do not repeat this exact audit or the closed score diagnosis as new progress.
The next useful engineering work is the explicitly named downstream
certificate integration and NativeRun/source-codec handoff. It
must not fabricate legacy scramble receipts. A new scientific execution also
needs the proposal's explicit fresh budget decision; no existing allocation
has spare capacity. Source codec/runtime handoff and integrated telescope
acquisition/trial admission remain separate prerequisites after any synthetic
pass. No plan extension, target switch or external contact is authorized here.

All old invariant pins remain unchanged. HD1461's hold, untouched GJ724,
M43AI's failure, original 112+128 M43AF holdouts, unresolved M15/M33, paused
LS8BD–LS8BE, untouched LS8BF and unsent CHEOPS persist. Consolidate on 9 October.

## Primary references and attribution

1. Phipson, B. & Smyth, G. K. (2010), *Permutation P-values Should Never Be
   Zero*, doi:[10.2202/1544-6115.1585](https://doi.org/10.2202/1544-6115.1585).
   [Author preprint, corrected 9 February 2011](https://gksmyth.github.io/pubs/PermPValuesPreprint.pdf),
   section 4. It motivates the observed-plus-reference rank correction for
   Monte Carlo tests with independent null simulations. Our EMPTY/tie proof
   above is supplied here rather than assumed from a continuity argument.
2. Hemerik, J. & Goeman, J. (2018), *Exact testing with random permutations*,
   TEST 27, 811–825, doi:[10.1007/s11749-017-0571-1](https://doi.org/10.1007/s11749-017-0571-1).
   [Published open text](https://pmc.ncbi.nlm.nih.gov/articles/PMC6405018/),
   [author preprint](https://arxiv.org/abs/1411.7565).
   Its conditions distinguish an invariant transformation group and valid
   random sampling from arbitrary restricted transformation choices. We use
   these as sufficient conditions to audit, not a necessity theorem.

Primary-source retrieval: 28 September 2026. A later PMC open encountered a
verification wall; it was not bypassed. All finite examples, enumeration and
the present receiver-design implications are our own analysis. Literature
lookups are not telescope requests; their wire byte totals are unavailable.
