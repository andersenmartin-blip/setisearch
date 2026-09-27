# Bounded motion provenance, accuracy and coverage contract — 27 September 2026

## Scope and freeze

Continue from science commit `0af377cbb7b385b86c5951e6feeb6bcdbdf12be9`.
This is an offline metadata/model continuation under
`HOLD_POINTING_PROVENANCE_UNRESOLVED`, not an integrated permission to acquire
spectra. The original source contract, execution envelope, telescope genesis,
exhausted synthetic ledger and 33-template direct banks are immutable inputs.
Primary remains `neighbor9`.

The [study configuration](config/radio_motion_contract_study_20260927.json)
records the bounded retrieval and the single coverage witness. Its coordinates
were fixed locally before the witness calculation: projected scale 0.25,
mean-anomaly phase 9/32 cycles, comparison carrier 1,500,000,000 Hz. The free
carrier convention was clarified to multiplicative `q * F_template` before
calculation. The four reporting restrictions were made explicit after the
initial calculation; they are the same witness, not four independent trials.
This protocol is published with the results, **not claimed to be an earlier
public preregistration**. No telescope/control evaluation is authorized by it.

Only three new direct metadata artifact requests were budgeted, with no automatic
retries: NASA `ps` solution rows, `pscomppars` value/error/limit/reference fields,
and the Díaz primary paper. Total direct-response ceiling 8,912,896 bytes;
per-request timeout 40 seconds. Retain URL, response headers, byte length and
SHA256. Search/discovery service response bytes are not instrumented and must
not be presented as included in this byte account. Reproduction is offline and
must not repeat these requests. Full copyrighted paper and page images stay out
of the repository; retain only hashes, source links and factual transcription.

This orbital-reference retrieval is distinct from the already closed pointing
catalogue/public-code investigations. It cannot resolve pointing. No sky
coordinate is corrected, and no alternate target is selected.

## Parameter provenance and uncertainty

For every consumed parameter preserve value, both errors, limit flag and source.
Missing flags are not zero. Nonzero limit flags cannot be used as point estimates.
Reference identifiers are compared, not just scalar values. An inferred match
by value/error/limit tuple is labelled as an inference and restricted to the
four retained solution rows.

Two distinct contracts are possible in principle:

1. A coherent epoch-anchored solution needs a common orbital solution, explicit
   epoch/time scale, angular conventions and uncertainties.
2. An explicitly phase-agnostic domain can omit an absolute periastron epoch,
   but needs a declared parameter domain and a coverage/recovery proof over it.

The historical bank uses free phase and does **not** consume the archived
periastron epoch. Do not misdiagnose the unused epoch as an arithmetic input.
Its consumed P/a/e/omega still require provenance; the new central-solution
audit refuses the actual mixed inputs under either phase policy.

`BJD` alone does not supply a TDB/TT/UTC clock convention. A stellar-reflex omega
must not silently be interpreted as a planet omega or shifted by 180 degrees.
The existing negative line-of-sight velocity convention is preserved as a
working convention. A relative semimajor axis also needs explicit conversion
to the transmitter's orbit and the required mass assumptions. No conversion
is adopted here. Marginal errors/quantiles do not define a joint posterior or
guaranteed bounded support. In particular an eccentricity 99% upper credible
limit is neither a central estimate nor a 99% joint P/a/e/omega domain.

The new audit is supplementary and offline. Even a complete declaration returns
`physical_model_qualified=false`; it cannot grant readiness to the old pipeline.
Unresolved full accuracy terms remain null, never zero or an optimistic partial
sum. A bound is summable only if qualified for exactly the same declared scope.

## Conditional two-body interpolation bound

For an idealized Keplerian orbit with fixed central P and a, e in [0,e_max],
all phases and line-of-sight projection magnitude at most one, define

```text
n = 2*pi/P,  mu = n^2*a^3,  r_min = a*(1-e_max)
V_max = n*a*sqrt((1+e_max)/(1-e_max))
A_max = mu/r_min^2
J_max = 2*mu*V_max/r_min^3
```

The jerk formula follows by differentiating acceleration:
`j = -mu/r^3 * (I - 3*rhat*rhat^T) * v`. The matrix has operator norm two.
These are all-phase norm bounds for this conditional Newtonian model, not
sampled maxima from a new phase scan. The standard linear-interpolation
remainder for scalar velocity on an interval of duration dt is at most
`J_max*dt^2/8`.

For first-carrier-normalized first-order emitter factor
`(c-s*v(t))/(c-s*v(0))`, with `0<=s<=1`, the frequency interpolation error is
at most `f*J_max*dt^2 / (8*(c-V_max))` when `V_max<c`. This statement holds the
observer multiplier fixed. It excludes observer curvature, relativistic
emitter/systemic terms, clock transformation, channel response, uncertain
P/a/e and detector recovery. It is deliberately not entered as a bound on
the complete exposure-and-instrument term.

## One continuous-domain center-track witness

Reuse stored `catalogue_fixed` factors and observer multipliers byte-for-byte.
Calculate only the fixed witness at the 96 retained integration midpoints using
the unchanged historical P/a/e/omega working scenario. Normalize at the first
ON midpoint exactly as the stored bank does. Do not regenerate any bank, scan
2048 phases, evaluate spectrum values, inject power or add a template.

For a selected set of ON midpoints let `y_i = f * F_witness(t_i)` and let
`G_i = F_template(t_i)>0`. Allow each template an unconstrained positive
physical carrier q. Its optimal maximum discrepancy is

```text
E = min_q max_i |y_i - q*G_i|
  = max_(i,k) |y_i*G_k - y_k*G_i|/(G_i+G_k).
```

Proof: an error E is feasible exactly when all intervals
`[(y_i-E)/G_i, (y_i+E)/G_i]` intersect. Pairwise lower/upper comparisons give
the expression above. Positive y and G admit a positive optimum. Recover q
from the common intersection and independently check residuals. Long-double
arithmetic limits cancellation; an independent 60-digit Decimal feasibility
bisection tests the formula at radio frequencies. This is floating-point
numerical evidence, not a directed-rounding interval certificate.

Report the minimum E over all unchanged 33 templates for all three ON epochs
and each of the three two-ON restrictions. Preserve every template's E, q and
active row pair, plus the witness factors and best residual vectors. The
unconstrained q relaxation is at least as favorable as the real bounded/discrete
carrier grid. Therefore a residual above a tolerance is a conservative
counterexample to center-track coverage at that tolerance. Restricting to
midpoints also favors coverage relative to requiring all observation times.

Half a native channel is an illustrative **reporting tolerance**, not a newly
adopted detector gate. A center-track mismatch does not imply failure of a broad
filter, a recovery fraction, RFI rejection, or an astrophysical detection claim.
The 129-channel width is not replaced or tuned in response to this witness.
No signal amplitude, noise realization or threshold is evaluated.

## Validation, accounting and publication

Test only the new risks: lost limit flags, mixed/missing references, implicit
time/omega/axis conventions, optional versus required epoch, minimax correctness
and carrier relaxation, conditional interpolation units/scaling, and refusal
to turn missing or differently scoped errors into a total bound. Existing
closed arithmetic/control tests are not a new milestone.

Pin all prior evidence and this continuation's implementation hashes. Retain
direct acquisition receipts separately from the telescope resource namespace.
One distinct motion witness and 132 distinct template/scope comparisons are
engineering calculations, not 132 independent scientific trials. Reproduction
and implementation checks do not create fresh scientific cases. No telescope
reservation, source request, trigger, veto, holdout or fresh 24-case evaluation
is consumed. No old ledger is rewritten or reset.

Publish this protocol, code, evidence and result on `m43-support-qualification`
with a fast-forward update. Publish a concise correction/status link on `main`.
Keep the old reports reproducible; place the corrected interpretation in the
current status/direction/plan. The execution envelope remains blocked with its
original five gates. The two-week plan is not extended beyond 9 October.
