# Conditional source-time and Doppler error study — 27 September 2026

Continue from science `82df2e2a928a1d26849c15420c486289bf9ab8ce`, whose
[phase-domain declaration](RADIO_PHASE_DOMAIN_2026-09-27_PROTOCOL.md) is now
public. Its numerical support, no-probability meaning and missing physical
terms are immutable inputs. This new study uses analytic inequalities and four
scalar endpoints only: no templates, detector scores, controls or spectra.
The [case configuration](config/radio_time_transfer_20260927.json) is locally
fixed before calculation and published with results, not falsely claimed as a
prior public scientific preregistration.

## Exact conditional setting

Work in flat spacetime with a stationary distant receiver, fixed line of sight,
source-system barycentre at rest and isolated Keplerian planet-COM motion. The
observer multiplier is one. Gravitational shifts/delays, systemic motion and
frame boosts, variable direction, other companions, transmitter motion relative
to the planet COM, real clock transformations and instrument response are not
included. This conditional setting is not the actual telescope/source geometry.

Let tau=0 be the source emission event for reference reception s=0. Positive z
points away from the receiver; v_z=dz/dtau. Remove only the constant path length:

```text
s = tau + [z(tau)-z(0)]/c
ds/dtau = 1+v_z/c.
```

For every declared orbit, speed<=V<c. With B=V/c, this map is strictly increasing,
`|tau|<=|s|/(1-B)`. Because an ellipse's diameter is at most 2a, and speed<=V,

```text
|tau-s| <= min(B*|s|/(1-B), 2*a_max/c).
```

This proves why a free reference phase removes constant light delay but cannot
remove the varying delay. We use the maximum absolute *retained exposure edge*
relative to the first midpoint, T=1960.7864736412732 seconds, as an illustrative
numeric extent |s|<=T. It includes both integration edges and inter-scan gaps.
The original offsets are UTC reception metadata. Equating their numeric extent
to this conditional inertial clock is **not** a qualified real clock conversion.

The scalar implementation inverts the monotone map by bracketing/bisection with
explicit residual checks. An independent fixed-point contraction using a
separate eccentric-anomaly bisection tests it. Floating-point brackets and
residuals are not directed-rounding interval certificates.

## Frequency and normalization

Define beta=v_z/c and x=|v|²/c²; beta²<=x<1. For an oscillator constant per source
coordinate second, received frequency is proportional to `1/(1+beta)` because
successive emission phases arrive at the derivative above. For a constant
source-*proper*-time oscillator, `d(proper time)/dtau=sqrt(1-x)`, so received
frequency is proportional to `sqrt(1-x)/(1+beta)`. Normalize at the reference:

```text
R(tau) = (1+beta0)/(1+beta(tau))                         coordinate oscillator
S(tau) = R(tau)*sqrt[(1-x(tau))/(1-x0)]                  proper oscillator
L(tau) = (1-beta(tau))/(1-beta0)                         first-order model.
```

The reference carrier f0=1500 MHz is *received frequency at s=0*. It absorbs
constant factors, not varying ones. These expressions apply only in the
conditional common frame above. Multiplying them by an unqualified optical
observer correction does not produce a verified astrophysical transformation.
Use full speed for x; a face-on eccentric orbit may have beta=0 but changing x.
For a circular orbit x is constant and the normalized transverse term cancels.

## All-phase, whole-domain inequalities

For `n=2*pi/P_min`, `a=a_max`, `e=e_max`, the relaxed COM support gives

```text
V = n*a*sqrt[(1+e)/(1-e)]
A = n²*a/(1-e)²
J = 2*n³*a*sqrt[(1+e)/(1-e)]/(1-e)³.
```

V/A/J are enclosing norm bounds over all declared P,a_p,e, phases and
orientations, not sampled maxima. Let U=T/(1-B), D=min(B*U,2a/c),
`delta_beta=min(2B,A*U/c)`. Then:

1. Using reception time in L instead of retarded source time costs at most
   `f0*A*D/[c*(1-B)]`.
2. Algebra gives `R-L=(beta²-beta0²)/[(1+beta)(1-beta0)]`, so its absolute
   frequency difference is at most
   `f0*min(B²,2B*delta_beta)/(1-B)²`.
3. Since `d|v|²/dtau=2*v·a`, and a Kepler ellipse has squared-speed range
   `4e*(n*a)²/(1-e²)`, take
   `delta_x=min(B²,2B*A*U/c,4e*(n*a/c)²/(1-e²))`.
   Rationalizing the square roots bounds the normalized transverse difference:
   `|S-R| <= delta_x/[2*(1-B)²]`.

The sum bounds `f0*|S(tau(s))-L(s)|` for this conditional emitter setting by the
triangle inequality. It is **not** a bound on total physical track error.
It neither bounds the unknown observer/clock/systemic/gravitational terms nor
proves real-source membership. A large upper bound does not establish that
every orbit, or the source, incurs that error. Do not subtract hypothetical
term cancellations or infer detector loss/recovery from center differences.
Numerical evaluations are ordinary binary64 with scalar independent checks,
not a certified finite-precision proof of an adopted physical bank.

## Frozen scalar checks and evidence

At the one endpoint s=T use four predeclared cases: e=.172 edge-on; e=0 edge-on;
e=.172 face-on; e=.172 half projection with omega=pi/3. All use P_min, a_max
and M0=pi/4. These deliberately fixed equation examples are not optimized or
compared to any bank. Retain every signed component and combined discrepancy.
Recomputations in tests and reporting remain the same four diagnostic examples,
not new scientific trials or independent samples.

At most 32 new unit tests and four retained endpoints are allowed. Socket
creation is disabled for tests. Independent checks include a 60-digit Decimal
algebra oracle, monotone/fixed-point time inversion, inverse derivative,
zero/reference and circular/face-on limits, declared-domain rejection and
correct edge extent. Every attempted run keeps its log and code/config snapshot.
Old physical accuracy terms, preparation/ledgers, closed failures, held-out
inputs and all five science blockers remain untouched. No external lookup or
source request occurs. The next connected step derives continuous-parameter
sensitivity bounds and a resource feasibility assessment without generating
or adopting a grid. The original two-week end date remains 9 October.
