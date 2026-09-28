# Whole-cadence synthetic reference — concrete proposal, not activated

**Status: PROPOSED_NOT_ACTIVATED. No new attempt is charged or executable.**
This is a separately named method following the closed HD189733 panel and its
completed diagnosis. It is not a remedy of that attempt. The
[method result](RADIO_EMPTY_NULL_METHOD_2026-09-28_RESULT.md) proves the rank
bound under its stated exchangeability assumption and identifies the missing
justification for treating the old guarded score shifts as that reference law.

Machine specification:
`config/radio_whole_cadence_null_proposal_20260928.json`.
Proposed identity record and collision audit:
`results_radio_empty_null_method_2026-09-28/proposal01/`.
These are proposals with immutable identities, not a consumption ledger.

## Target, exact geometry and fixed receiver scope

Keep HD189733/HIP98505 cadence 85030, source preparation
`config/radio_hd189733_source_preparation_20260927.json` and all six published
AGBT16A_999_97 scan identities. The preparation remains not-ready. This
proposal generates synthetic arrays on their geometry; it opens no telescope
payload. It claims a received linear-track scope, not planetary completeness
or a barycentric transformation.

| Role | Archive channel interval, half-open | Inclusive native channel-center endpoints, Hz | Inclusive scored-carrier endpoints, Hz |
|---|---|---|---|
| Calibration references | [167215104, 167280640) | 1402140020.024552–1402325844.7410803 | 1402232817.5449278–1402233044.3852012 |
| Evaluation | [164069376, 164134912) | 1411059742.5220742–1411245567.2386024 | 1411152540.04245–1411152766.8827233 |

Each extraction has 65,536 native channels. There are only 81 scored carriers,
spaced by 2.835503418452676 Hz, with 99 support carriers. The larger extraction
is not an all-frequency search. The old 288 native chunk identities remain
disjoint across calibration, validation and inactive pilot roles. No new real
frequency window, pilot allocation or source receipt is inferred from these
synthetic identities.

Primary remains neighbor9. Keep the 81 received rate labels -4 to +4 Hz/s in
0.1 steps, with `q*(1+r*t/C)` at the exact midpoint clock and the role's fixed
reference center C. Widths are 1,3,5,9,17,33,65,129 native channels. Use the four
two-or-three-epoch subsets, minimum active-epoch S/N 3 and sum stack. Each
cadence has 2,592 template/width/activity hypotheses and 209,952 ON scored
cells before eligibility. The complete score map is the statistic's domain.

The previously proved relative score-address equality permits only synthetic
calibration-to-validation operator translation under the identical relative
raw-array law. The proposal pins that proof and both distinct contexts. Keep
source receipts as source receipts and produce an explicit translation receipt;
do not claim a new destination measurement. It establishes neither actual
frequency-dependent noise equivalence nor transfer of absolute-frequency
vetoes. Those vetoes operate on each evaluation's own arrays.

## Null law, identities and one fixed reference set

Use exactly 127 new noise-only synthetic cadences, in proposed index order.
For each of six scans use NumPy 2.3.5
`Generator(PCG64(SeedSequence([case_seed, scan_index])))`. Read 16 rows in
ascending integration order. Each row is 65,536 ascending-frequency draws from
Gaussian digital power of mean 100 and standard deviation 1, cast float32,
then passed through the existing block normalization and filter/gather code.
There is no comb, injection or score rotation in these references.

Each whole cadence supplies **one** maximum over its complete eligible ON
family, or tagged EMPTY if that set is empty. Store both EMPTY and finite
outcomes. Any missing source/row/vector/hypothesis, corrupted pin, NaN, positive
infinity, numerical representation failure or exhausted capacity stops the
attempt. None is represented as EMPTY. An all-EMPTY *complete* reference bank
is mathematically permissible; it is not a measured zero tail probability.

The 127 reference namespaces and 24 evaluation namespaces are distinct under
`radio-hd189733-whole-cadence-null-20260928-v1`. The full 64-bit seeds and case
identities are published in the config; seeds are the first eight big-endian
bytes of SHA256(namespace + `/seed-v1`). No new values have been generated.
The six old development cases stay closed, the three old calibrations stay
failed/closed, and the 24 old unopened evaluations remain archived and unusable
by this attempt. The new identifiers do not turn old data into fresh data.

In the ideal model, distinct whole-cadence draws with the same score operator
are iid, hence exchangeable. The exact rank theorem is conditional on that
model. Seed uniqueness does not prove independence of deterministic streams;
the finite-precision pseudorandom implementation and nonphysical noise law
are explicit limitations. No telescope or RFI distribution is qualified.

## Threshold, rank and fixed evaluation panel

Reference size is fixed at B=127; no sequential stopping, replacement sample,
reference selection or sample-count tuning. This preserves 1/128 rank
resolution with *independent whole-cadence units* instead of conditional shift
rows. Three independent reference units would only permit a minimum rank 1/4.

The operational score threshold is `max(10, higher quantile at 1 of all 127
ordered maxima)`. For a finite member score s, its inclusive rank is
`(1 + count(reference maximum >= s))/128`. Require rank <=0.01 in addition
to score >=threshold and all unchanged physical vetoes. At B=127, this means
zero reference ties/exceedances; an EMPTY observed cadence never passes.
Do not publish a rank of zero or discard EMPTY reference units.

The 24 new recipes copy the old **unopened** panel's specified designs without
changing amplitudes, widths, drift labels or gates: ten ON-only signals, ten
matched ON/OFF controls, two single-adjacent-OFF controls and two noise nulls.
Signal widths 1/5/33/65/129 and digital powers 100/500 are unchanged. Full
finite-exposure rectangle convolution uses the exact header midpoints and
durations; designated scans are active for all 16 integrations. Matched OFF
uses the same received track at OFF times; adjacent controls use ON epochs
0 and 2 with OFF epoch 0. The existing recipe rate cycle is retained exactly.
Truth enters post-decision association only.

Keep full retention, matched-OFF tolerance 20 Hz, adjacent-OFF floor 5.5,
receiver neighborhood +/-100 Hz, local peak floor 5.5, at least two shared
active epochs and ON-track alias tolerance 20 Hz. Recovery requires at least
one associated final member and component in **each** ON-only case. All other
controls require zero final members/components, including the separate
unassociated-leakage checks for widths 65 and 129. Association and mixed
component accounting remain exactly the old gate specification copied into
the new config. Retain every trigger, veto, unassociated survivor and failure.

A scientific gate failure does not change the remaining recipes: finish the
fixed cases unless an integrity/resource error stops execution. No remedies,
tuning, alternative primary, fresh follow-on evaluation, target switch or
pilot is implied by a pass or failure. This new proposal includes no second
diagnosis allocation; the plan's original one is already spent.

## Prospective consumption and cumulative limits

| Quantity | Prior HD189733 actual/closed | New proposal ceiling | Cumulative if activated and fully run |
|---|---:|---:|---:|
| Native development cases | 6 | 0 | 6 |
| Calibration cadences | 3 | 127 | 130 |
| Evaluation values generated | 0 | 24 fresh | 24 |
| Evaluation runs executed | 0 | 1 | 1 |
| Evaluation attempt allocations charged | 1 closed | 1 new | 2 |
| Evaluation identities archived/reserved | 24 old unopened | 24 new | 48 distinct |
| Retained-score diagnosis allocations | 1 closed | 0 | 1 |
| Remedies / pilots / new source requests | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |

The proposal's resource ceilings are 7,200 active execution seconds, 512 MiB
process RSS, 256 MiB modeled arrays, 1 GiB retained evidence, 10,000 retained
records per scan kind/case, 128,000,000 canonical bytes per evidence stage and
the existing five-million comparison/visit caps. Cadences are processed
sequentially. These are proposed caps, not a benchmark or a promise that the
whole attempt will fit; reaching one closes the attempt with all partial
evidence retained. They do not authorize paid computation.

The prior 80 target-metadata requests, 55,841 body bytes and 557.320353 active
seconds remain spent. Other historical source/engineering costs and the
closed synthetic acquisition ledger remain preserved separately; none is
reset or presented as zero. The empty telescope-ledger genesis stays inactive.
Calendar end date, at-most-three-sequence limit and 9 October consolidation
are unchanged. This is a requested new experiment allocation, not an automatic
enlargement of the old 3/24/one-attempt/zero-remedy budget.

Only a later, separately authorized executable freeze may charge the 127
calibration slots and one new evaluation allocation durably. That freeze must
be published/read back before any proposed value is generated. Each case must
be charged before generation and its complete score archive/receipts persisted
before downstream decisions. Missing scratch or results never authorizes
replay of a charged identity. Preserve lost/incomplete cases as such and close
the attempt on integrity failure. Do not add an automatic retry budget.

## Implementation/admission work still required

The tagged rank arithmetic, proposal identity contract, complete-family
maximum reducer and ordered reference bundle are implemented and tested with
35 distinct deterministic tests. A complete execution runner is **not**
implemented by this document. The reference bundle's native-success path and
a distinct downstream certificate interface still require qualification with
externally pinned full-family/context/source/row provenance. The new native
wrapper requires the case and noise-law identity in every source scope; the
old renderer does not yet supply that law field. The reference bundle itself
does not validate the translation proof's semantics or authorize a detector.
The legacy calibration accumulators and threshold certificates encode
conditional scrambles and finite-only maxima. Do not forge a scramble table,
fill that slot with independent draws, monkeypatch validators or relabel an
old certificate. Retention, OFF, alias and final-rank stages must accept the
new method through a separately reviewed, explicit interface.

Before spending the proposed budget, qualify that interface using bounded
deterministic fixtures for empty/finite/tied outcomes, omitted/duplicate
cadences, altered context or noise law, incomplete hypothesis/source ancestry,
capacity failures and durable consumption. Do not use proposed reference or
evaluation values to debug the implementation. Pin and publish the complete
code/config/runtime/test/budget freeze and independently verify it.

Even a later synthetic pass cannot open telescope spectra. Source-specific
codec/runtime evidence and an integrated prospective acquisition/trial
protocol still have to satisfy the active source's separate admission gate.
HD1461's hold, untouched GJ724 reserve, closed M43AI, original M43AF holdouts,
M15/M33 dispositions, paused LS and unsent CHEOPS remain intact. No external
messages, observational booking, paid services or automatic plan extension.
