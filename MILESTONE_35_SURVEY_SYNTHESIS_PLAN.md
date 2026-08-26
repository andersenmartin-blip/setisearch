# Milestone 35: retrospective 1412 MHz survey synthesis

## Purpose and status

Milestone 35 combines the frozen detector-v0.5 held-out searches from Milestones
14 through 33 into a target-level sensitivity analysis. This is a retrospective
analysis, not a blind preregistration: the search results and candidate outcomes
were known while this protocol was designed. The protocol will nevertheless be
committed before the final scripted execution so that the inputs, cohort,
statistic, and stopping rule cannot change during that execution.

No spectral arrays are read in this synthesis. The only numerical inputs are the
already-published `search_summary.json` and `completeness.json` records, plus the
published M16 investigation and independent-cadence records used to preserve its
candidate-positive status.

## Frequency-matched scope

Every target's injection experiment used its `mXX_1412p5` background, whose
frozen rest-frequency search interval is 1412.0--1413.0 MHz. The primary outcome
is therefore restricted to that same interval. A five-window occurrence bound
is not supported because the other four windows have no matching injection
calibration and substantially different RFI environments.

This frequency match does not make completeness a worst-case lower bound at
every fixed frequency in the interval. The generator places truth frequencies
at the rest-grid centre plus a uniform offset in +/-0.010 MHz and a half-channel
sub-bin jitter. For every injection and S/N level, each epoch's real 1412 MHz
noise-vector/mask pair is shifted together; the shifts are independent across
epochs, trials, and S/N levels. Thus recovery is an average over that frozen
randomized background relationship, not a calibrated fixed-frequency efficiency
curve.

The benchmark amplitudes are the seven exact ideal single-epoch S/N levels
8, 12, 16, 20, 24, 32, and 40. There is no interpolation and no claim about
signals with S/N greater than a benchmark. Each target-level completeness value
is the observed `multi_channel_recovered / trials` fraction from 32 injections,
equally divided across truth-template indices 0, 8, 14, and 20 and active in
zero-based epochs 0 and 2. One-channel recovery is never substituted.

## Frozen cohorts and candidate accounting

The primary cohort is the complete administrative sequence M14--M33: 20 unique
held-out target systems analysed with detector v0.5.0. Within 1412.0--1413.0 MHz
it contains 267 fully retained clusters, 49 above the target-specific threshold,
and 48 with a frozen physical OFF-source or receiver-frame veto. M16's
1412.485745176673 MHz cluster is the only remaining candidate-positive system.
It is counted as one possible true detection even though an independent cadence
did not redetect it: that later observation is neither a physical veto of the
primary event nor a calibrated two-cadence completeness experiment.

The secondary complete-retention check is M23--M33: 11 naturally contiguous
systems, 192 fully retained 1412 MHz clusters, two above threshold, both with
M27 local-OFF vetoes, and zero candidate-positive systems. This is a secondary
check, not a replacement for the full administrative cohort.

The outcome-selected M17--M32 clean-null subset is explicitly rejected as a
primary analysis. M14, M15, M16, and M33 must not be removed merely because they
contain candidates elsewhere in the survey.

## Nominal plug-in calculation

At an exact benchmark S/N, let `c_i` be target `i`'s observed multichannel
recovery fraction. The model gives every system in the selected cohort the same
independent Bernoulli occurrence probability `f(S)` for the injected signal
class. This is a common model probability, not the observed finite-cohort
fraction. The count of recovered true signals is Poisson-binomial with target
probabilities `f * c_i`. If `K` candidate-positive systems are used as an upper
bound on the number of true detections, the nominal upper limit solves

`P_f(T <= K) = 0.05`.

The inversion uses the exact inclusive Poisson-binomial lower tail, not a Poisson
approximation. If the tail at `f = 1` remains above 0.05, the result is the
trivial upper limit 1 and is labelled “no non-trivial bound.” Because `c_i` is
estimated from only 32 injections, this plug-in result is nominal and is not
presented as a finite-calibration 95% confidence bound.

## Pointwise finite-injection construction

For a conservative pointwise 95% construction, the total error probability is
split into 0.025 for injection calibration and 0.025 for the survey tail. At one
S/N level, the calibration share is divided across the `N` targets by
Bonferroni, `alpha_i = 0.025 / N`.

For target `i`, with `k_i` recoveries in `n_i = 32` independent injections, the
one-sided lower confidence bound for the average of possibly non-identical
Bernoulli success probabilities is

- 0 when `k_i = 0`;
- `alpha_i / n_i` when `k_i = 1`;
- the solution `p` of `P(Binomial(n_i, p) >= k_i) = alpha_i` when `k_i >= 2`.

This is the Mattner--Tasto/Buehler construction for an inhomogeneous Bernoulli
chain, not an unjustified pooled-binomial interval. The primary reference is
[Mattner and Tasto, *Confidence intervals for average success probabilities*](https://arxiv.org/abs/1403.0229),
Theorem 1.2.

Let the resulting simultaneous target lower bounds be `L_i`. The reported
finite-injection upper bound solves

`P_f(sum_i Bernoulli(f * L_i) <= K) = 0.025`.

On the event that every `L_i <= c_i`, this is conservative; Bonferroni and the
survey-tail allocation give total pointwise error at most 0.05. It is not a
simultaneous confidence band over the seven S/N levels, nor are the primary and
secondary results a joint simultaneous confidence statement.

## Mandatory interpretation conditions

The injection endpoint is local recovery above the operational score threshold
at the injected truth template. It does not execute candidate peak retention,
clustering, report capping, OFF-source vetoes, receiver-frame vetoes, or manual
adjudication. The numerical occurrence bounds are therefore conditional on this
assumption:

> A true injected-class signal recovered above the operational score threshold
> would not be lost during clustering, report retention, physical vetoing, or
> adjudication.

Without that assumption, the documented lower bound on end-to-end detection
efficiency is zero and the only unconditional occurrence upper bound is the
trivial value 1. The outputs must call the calculation a **conditional
score-recovery sensitivity bound**, never an unconditional technosignature or
transmitter occurrence limit.

A second condition is equally mandatory:

> A true signal's local background and RFI relationship follows the frozen
> randomized injection distribution.

The observed average recovery is not a lower bound at every fixed frequency in
1412.0--1413.0 MHz. Without this background-distribution condition, a
worst-case fixed-frequency efficiency can again be zero and the corresponding
unconditional upper bound is 1.

## Further limits

- The inference is pointwise at each exact ideal-S/N benchmark.
- The efficiency averages the frozen truth-frequency and independently shifted
  empirical-background generator; it is not a guarantee at every frequency in
  the outcome window.
- Ideal S/N is not a common flux or EIRP threshold across targets.
- The injected signal model is active in scans 1 and 3 and averages four frozen
  track templates; arbitrary duty cycles or morphologies are not covered.
- M31--M33 use a wider boxcar bank than M14--M30. Target-specific completeness
  absorbs this for the injected model, but raw trial and cluster counts are not
  directly exchangeable.
- Target occurrences and injection trials are modelled as independent.
- The archive/rank-selected cohort is not a random exoplanet population sample.
- There is no claim about civilizations, all receivers, all frequencies, or the
  broader Galaxy.

## Fail-closed validation and outputs

The synthesis script must stop unless all declared input SHA-256 hashes match;
all 20 summaries report detector 0.5.0; the embedded completeness records match
their standalone records; the 1412 MHz lists are fully retained; the frozen
cluster/candidate totals reproduce; and all injection counts, templates, S/N
levels, and recovery booleans reconcile exactly.

The scripted outputs are:

- `analysis_summary.json`, including all assumptions and both cohorts;
- `occurrence_bounds.csv`, one row per cohort and exact S/N level;
- `target_accounting.csv`, the target-level audit trail;
- `score_recovery_bounds.png`, a single primary-cohort comparison chart;
- `run_metadata.json` and `INPUT_MANIFEST.sha256`;
- `RESULTS_MANIFEST.sha256` covering every other result file.

Execution stops after both frozen cohorts and all seven exact S/N levels are
reported. No subset or threshold may be added or removed in response to the
calculated upper limits.
