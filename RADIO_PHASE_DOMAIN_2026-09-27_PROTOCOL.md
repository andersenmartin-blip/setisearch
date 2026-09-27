# Prospective conditional motion support and conventions — 27 September 2026

This is the next independent item after science commit
`3c242a7288970aa2440c3c499fd3fadc08d96bf6`. It declares a mathematical domain for
subsequent analytic engineering, using only retained orbital facts. It does not
adopt a source orbit, create search templates, replace the old preparation, or
authorize data access. It is published with its declaration/geometry tests,
before the follow-on time-transfer and covering-bound study. There is no claim
of a preregistered scientific evaluation.

## Conditional support, not a confidence region

The [versioned declaration](config/radio_phase_domain_20260927.json) uses:

| Quantity | Conditional support | Interpretation |
| --- | --- | --- |
| Period P | [5.77107, 5.77197] days | A deliberate rectangle endpoint, one quoted marginal width around retained Díaz P |
| Relative semimajor axis | [0.0612, 0.0656] AU | Same deliberate choice for retained Díaz a |
| Eccentricity | [0, 0.172] | Conditional restriction; 0.172 remains a quoted 99% upper credible limit |
| Reference mean anomaly | Entire circle | No absolute periastron epoch needed |
| Mathematical planet orientation angle | Entire circle | No reinterpretation of the mixed catalogue omega |
| Mass ratio q=M_planet/M_star | All q>=0, M_star>0 | No mass or probability inferred |
| Projection sin(i) | [0,1] | All line-of-sight inclinations |

The P/a rectangle is **not** guaranteed source support and has no joint
probability. Marginal errors do not yield a joint confidence box. The
eccentricity quantile does not imply a 99% probability for this combined domain.
Actual-source membership and period-clock transfer remain unresolved. One day
is defined as 86400 conditional coordinate seconds for these calculations;
this is not evidence for the catalogue's clock scale.

For a transmitter at the planet centre of mass in an isolated two-body model,
`a_p=a_rel/(1+q)` and `A=a_p*sin(i)`. Consequently the closed relaxation
`0<=A<=a_p<=0.0656 AU` contains the projections of every finite nonnegative q
in the declared relative-axis domain. Zero a_p is a conservative closure,
not an asserted finite-mass orbit. This is why a mass measurement is unnecessary
for this *conditional enclosing set*. It does not establish the transmitter's
location. Surface rotation, moons, spacecraft, other companions, secular
changes and non-Keplerian motion are outside the model and need their own terms.

## Geometry and signs

Let z be displacement away from the receiver, tau the conditional source
coordinate time, and M(tau)=M0+2*pi*tau/P. With E-e*sin(E)=M, define

```text
z = -A[(cos E-e) sin omega + sqrt(1-e²) sin E cos omega]
v_z = (2*pi/P) A [sin E sin omega - sqrt(1-e²) cos E cos omega]/(1-e cos E).
```

These are our mathematical angle and sign conventions. The full omega circle
contains opposite orientations; no catalogue angle is converted by 180 degrees.
The old routine uses `M=2*pi*(t/P-legacy_phase_cycles)`, so equivalence requires
`M0=-2*pi*legacy_phase_cycles`. One deterministic equation check verifies this
sign mapping. It does not regenerate the stored bank or previous witness.
For e=0, M0 and omega are degenerate through their sum, so they are not two
independent physical observables. At A=0 the radial track is constant while
three-dimensional orbital speed can remain nonzero. Radial speed must not be
substituted for total speed in a transverse relativistic term.

## Time and frequency meanings

Tau=0 is the emission event corresponding to the first ON reception midpoint.
This removes an arbitrary constant light-travel delay through the free phase;
it does not remove the varying orbital light-travel delay. The retained UTC
reception offsets are not silently treated as emission offsets or relabelled
TDB. The follow-on study must derive the conditional varying-delay map and its
effect on a carrier-normalized track. Full observer/time-scale and systemic
transforms remain null until supported.

The reference carrier means received frequency at the reference event after
all declared factors, not emitted proper frequency. A future combined track may
use separately defined emitter and positive observer ratios only with a
qualified common frame/time/frequency convention. The old optical-correction
multiplier is not thereby certified as a complete covariant transformation.
No source, barycentric or receiver frequency window is changed here.

## Verification and boundaries

The executable audit binds numeric support *and its semantics*, rejects missing
conventions, probability claims, zeroed unknown terms, impossible projections,
nonfinite numbers and nonpositive arrival-time derivatives. Even a valid
declaration has `physical_model_qualified=false`. Nine complete physical terms
remain explicitly null. No partial bound is substituted into the old seven-term
accuracy contract or the original five-gate execution envelope.

Tests address new risks: source-membership confusion, the quantile/point
distinction, mass/projection geometry, phase-sign and circular degeneracy,
three-dimensional versus radial speed and invalid/missing declarations.
Only scalar deterministic geometry is used, without templates, noise,
injections, nulls or telescope samples. Qualification disables socket creation,
retains each run's log and exact source/configuration snapshot, and verifies
all pinned old inputs before and after. At most 32 distinct new tests and 12
retained axis examples are allowed; failed attempts stay visible.

The closed synthetic ledger, empty telescope genesis and source preparation
remain immutable. The 24-case panel is unopened; neighbor9, M43AI and the
112+128 M43AF holdouts retain their dispositions. M15 GJ581 and M33 HD3651 stay
unresolved. LS remains paused at LS8BD–LS8BE, LS8BF unopened, CHEOPS unsent.
No external lookup, new automation, message, booking or paid service is used.
The plan ends 9 October; this conditional declaration does not expand it.
