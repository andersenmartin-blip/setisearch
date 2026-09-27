# Conditional temporal compression with rational remainder bounds — 27 September 2026

Continue from science `5ef2667a1aa24bf79a8b2dc6373efea7204121ac`. The preceding
[cover-count study](RADIO_MOTION_COVERING_2026-09-27_RESULT.md) demonstrates the
cost of one loose parameter grid, not a minimum bank size. This bounded next
study asks whether the *same conditional emitter tracks* admit short temporal
polynomial representations with controlled remainders. It does not generate
a polynomial, template, coefficient grid, spectrum or control realization.

The [configuration](config/radio_temporal_majorant_20260927.json) fixes degrees
1–6, reference carrier 1500 MHz, absolute reception extent 1960.7864736412732 s
and the prior illustrative half-channel tolerance before calculation. No
additional degrees, parameter optimization or threshold selection is allowed
in this package. These engineering choices are published with their results,
not described as a prior public science preregistration.

## Model and coefficient conventions

Retain the declared conditional P/a/e support, every phase/orientation, an
isolated Keplerian planet-COM emitter, fixed line of sight, stationary distant
receiver and system barycentre, flat spacetime and observer ratio one. The
constant proper-time oscillator and retarded arrival map are exactly those
defined in the time-transfer protocol. Actual source support, observer motion,
clock-scale transfer, systemic/gravitational terms, other emitter motion and
instrument response remain unqualified. No probability is assigned to the box.

Interpret decimal support endpoints and the declared numerical reception
extent as exact rationals for this certificate. This is not a physical UTC
conversion or certification of an old binary64 implementation. Coefficients
are Taylor coefficients (derivative divided by factorial), never raw derivatives.
All bounds are uniform at any orbital phase and local reception time.

## Newtonian derivative majorant

For normalized position u=r/a_p, the limiting a_p=0 case is treated through
scaling rather than division by zero. Nonzero orbits obey
`u''=-n²*u/|u|³`, `|u|>=d=1-e_max`. Let R_j bound `|u^(j)|/j!`, and use the
maximum angular frequency n=2*pi/P_min. Seed the proven norm bounds:

```text
R0 = 1+e_max
R1 = n*sqrt[(1+e_max)/(1-e_max)]
R2 = n²/(2*d²)
R3 = n³*sqrt[(1+e_max)/(1-e_max)]/(3*d³).
```

For j>=4 set k=j-2. The coefficient of degree l>=1 of `|u|²` is bounded by
`Q_l=sum_(i=0..l) R_i*R_(l-i)` using the vector Cauchy inequality and triangle
inequality. Its constant term is at least d². Consequently coefficients of
`|u|^-3` are bounded by the nonnegative series

```text
G(h) = d^-3 * sum_m |binom(-3/2,m)| [sum_(l>=1) Q_l*h^l/d²]^m
R_j = n²/(j*(j-1)) * coefficient_k [R(h)*G(h)].
```

Only already bounded coefficients up to k are needed at each recurrence.
Compute position majorants through degree eight, enough for frequency
derivatives through degree seven. This is a finite local derivative recurrence,
not an assumption that an infinite majorant series converges over the cadence.

## Proper-frequency and retarded-time composition

Let `v_j=(j+1)*R_(j+1)*a_max/c`, with v0=B enclosing total speed/c. It bounds
both scalar radial-beta coefficients and vector velocity/c coefficients.
For x=|v|²/c², nonconstant coefficient bounds are the convolution of v_j with
itself. Write their zero-constant series as delta_beta and delta_x. Since
`1+beta0>=1-B`, `1-x0>=1-B²` and `sqrt(1-x0)<=1`, an absolute coefficient
majorant for unnormalized proper frequency is

```text
D(h) = [sum_m |binom(1/2,m)| (delta_x/(1-B²))^m]
       * [1/(1-B) * sum_m (delta_beta/(1-B))^m].
```

For a local reception displacement s, source displacement h is the inverse
of the arrival map. Bound the inverse coefficients by the positive recurrence

```text
H(s) = s/(1-B) + [sum_(j>=2) R_j*a_max/c * H(s)^j]/(1-B).
```

The local reference-displacement constant cancels; the linear derivative is
bounded below by 1-B. Higher coefficients depend only on earlier inverse
coefficients. Normalizing the emitter factor to the first reference event
costs at most `K=(1+B)/sqrt(1-B²)`. Thus

```text
C_m = f0*K * coefficient_m D(H(s))
|F^(m)(s)|/m! <= C_m for every declared orbit and reception time.
```

Taylor's finite-order remainder theorem then gives a degree-q representation
error at most `C_(q+1)*T^(q+1)` for |s|<=T, using the *actual* reference
derivatives of the conditional model. No such derivatives or polynomial tracks
are generated here. Bounds on every local derivative, not convergence of the
formal majorant at T, justify this remainder. A small remainder establishes
temporal representability only; it does not quantify coefficient-grid coverage,
search cost, channel response, width/recovery or any missing physical term.

## One-sided rational arithmetic

Use exact Python Fraction addition, multiplication, division and integer powers
for every coefficient and tolerance comparison. Obtain pi from Machin's identity
`pi=16*atan(1/5)-4*atan(1/239)`, with 48 and 16 alternating-series terms.
The first omitted term encloses each remainder. Round the resulting upper
bound upward to 40 decimal places. Integer square roots enclose each positive
root between adjacent rationals of denominator 10^40. Use upper roots in
numerators and lower roots in positive denominators. All majorant operations
are monotone in the substituted bounds; denominator replacements remain positive.

Retain exact numerator/denominator pairs for pi, beta, position, inverse time,
normalization, frequency coefficients and remainders. Human-readable remainder
decimals round upward. The certificate concerns this finite one-sided arithmetic
under the documented analytical inequalities. It is not a theorem-prover
verification, a physical-source certificate or a numerical certificate for the
old pipeline. Prior unqualified physical terms stay null.

## Verification, resources and integration boundary

At most 32 new tests check exact Machin tangent identity, alternating bounds,
integer-root enclosures, known binomial coefficients, independent Catalan inverse
coefficients, polynomial cross terms, circular derivative/factorial limits,
analytic first-three reception derivatives, zero-axis constancy, exact remainder
comparison, outward rendering and bounded-study/refusal semantics. All attempts
retain code/config snapshots, logs and runtime. Test sockets are disabled.
Repeated certificate evaluation is the same six-order calculation, not new
scientific cases. There is no grid allocation, detector run, source request,
fresh control execution or change to old evidence.

After the result, integrate the conditional conclusions with the existing
blocked envelope and fresh panel in a separate disposition record. Do not
rewrite the old source preparation, reset a ledger, claim the 24 fixed cases
cover a new motion family, or expand attempts/resources. Pointing and live
admission need their existing concrete missing evidence. Primary remains
neighbor9; earlier candidate, holdout and LS/CHEOPS dispositions persist.
The plan is unchanged through its 9 October 2026 end date.
