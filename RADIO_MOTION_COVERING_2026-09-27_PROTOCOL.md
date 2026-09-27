# Conditional continuous-parameter covering calculus — 27 September 2026

Continue from science `bd7b801c0329e2f49c843124014b3c39d88b8d32` and its
published [retarded-time setting](RADIO_TIME_TRANSFER_2026-09-27_PROTOCOL.md).
The [configuration](config/radio_motion_covering_20260927.json) freezes one
equal-allocation construction and two scalar derivative-oracle points before
calculation. It is published with this engineering result, not presented as
an earlier public scientific preregistration. No grid or template is generated.

## Conditional chart and derivatives

Use six coordinates `(P,a,lambda,e,M0,omega)`, where P is in seconds and a in
metres during derivation, `A=a*lambda`, `0<=lambda<=1`, `0<=a<=a_max`. P and e
have the previously declared support. Both angles are circles. This rectangular
chart stays within `0<=A<=a<=a_max`, including degenerate zero/face-on/circular
cases. It does not create additional source-membership or probability claims.

Set `d=1-e_max`, `k=sqrt(1-e_max²)`, `n=2*pi/P_min`, and use the published
whole-domain speed V, acceleration Q, `B=V/c`, `U=T/(1-B)`. Write
`w=(n*a_max/c)²`. All following entries are upper bounds on absolute derivatives
at fixed source time |tau|<=U, not derivatives of a worst-case scalar bound.

Kepler's equation implies `|E_M|<=1/d`, `|E_e|<=1/d`, and
`|E_P|<=n*U/(P_min*d)`. The line-of-sight position numerator has derivatives
`|h_E|<=1`, `|h_e|<=1/k`, `|h_omega|<=1+e_max`. For the velocity numerator
`g/(1-e*cos E)`, its E derivative is bounded by `1/d²`; its explicit e
derivative by `e_max/(k*d)+1/d²`. Full squared speed divided by c² is
`(2*pi*a/(P*c))²*(1+e*cos E)/(1-e*cos E)`. Differentiating gives:

| Coordinate | Z: position derivative bound | W: LOS velocity derivative bound | X: derivative bound for speed²/c² |
| --- | --- | --- | --- |
| P | a_max*n*U/(P_min*d) | V/P_min+n²*a_max*U/(P_min*d³) | 2B²/P_min+2w*e_max*n*U/(P_min*d³) |
| a | 1+e_max | V/a_max | 2B²/a_max |
| lambda | a_max*(1+e_max) | V | 0 |
| e | a_max*(1/k+1/d) | n*a_max*(e_max/(k*d)+1/d²+1/d³) | 2w/d³ |
| M0 | a_max/d | n*a_max/d³ | 2w*e_max/d³ |
| omega | a_max*(1+e_max) | V | 0 |

These bounds enclose each conditional orbit and all directions; the e derivative
includes the implicit E change. The code then converts P derivatives to per day
and a derivatives to per AU. Circle distances use the shortest arc, including
the seam. The old legacy phase sign is not reused as M0.

## Implicit emission time and normalized proper frequency

At fixed reception s, differentiate `s=tau+[z(tau)-z(0)]/c`:

```text
|d tau/d theta| <= 2*Z_theta/[c*(1-B)] = H_theta
W_retarded = W_theta + Q*H_theta
X_retarded = X_theta + (2*V*Q/c²)*H_theta.
```

The second z term is the parameter-dependent reference position. Dropping it
or the implicit source-time derivative would invalidate the bound. For
`R=(c+v0)/(c+v_tau)` and `G=sqrt[(1-x_tau)/(1-x0)]`,

```text
|R_theta| <= W_theta/(c-V) + (c+V)*W_retarded/(c-V)²
|G_theta| <= (X_retarded+X_theta)/[2*(1-B²)^(3/2)]
|d(f0*R*G)/dtheta|
 <= f0*[|R_theta|/sqrt(1-B²) + (1+B)/(1-B)*|G_theta|] = L_theta.
```

The multivariate mean-value bound is `sum L_theta*distance_theta`, with circle
arc distances for the angles. A coordinate-by-coordinate path stays inside the
declared rectangle. It also applies throughout the observation interval; it is
not merely agreement at selected samples. This is a conditional centre-track
statement, with the same stationary-receiver/proper-oscillator assumptions as
the preceding study. Unknown physical and instrument terms are still excluded.

## One sufficient construction; no minimum-size claim

Take epsilon=1.417751709226338 Hz (half a native channel) solely as a reporting
tolerance, not a new detector gate. Allocate epsilon/6 to each coordinate.
For interval width W or circle circumference 2*pi and coefficient L, choose
`N=max(1,ceil(W*L/(2*(epsilon/6))))`. Interval cell midpoints have covering
radius W/(2N); equally spaced circular nodes have radius pi/N. Their Cartesian
product is a sufficient mathematical construction under the stated bounds.
Count it using integers without producing nodes or spectra. Report all six
counts, radii and bounded contributions, and the product.

The stored binary64 derivative constants and integer-ceiling calculation are
numerical engineering, not directed-rounding interval certification. A small
outward count-rounding step does not certify the constants. Report hypothetical
float64 factor storage as `N_product*96*3*8` bytes for the previous 96-row,
three-time-sample layout. This is a materialized-storage estimate for this
construction only, not source-download expenditure, measured runtime, or a
requirement imposed on all possible algorithms.

Global derivative bounds ignore cancellations from reference normalization,
parameter degeneracies, free-carrier optimization and local curvature. Thus a
huge count would show that **this loose Cartesian construction is unsuitable**,
not that all physical banks or searches are impossible. Do not search for a
better allocation/grid in this study, instantiate the product, expand the old
33-template bank or tune controls. Broad-filter recovery is a separate question.

## Independent checks and preservation

A standalone forward-derivative oracle differentiates scalar Cartesian
position/velocity equations through Newton Kepler iterations and a fixed-point
arrival-time inverse. It does not import or differentiate the bound formulas.
Two fixed interior points provide all six frequency and time derivatives.
Compare these with the global bounds and an independently bracketed inverse;
finite differences check the implicit derivatives. These scalar checks catch
implementation/units/sign errors but do not replace the analytic derivation.

Other new tests cover reference normalization, circular phase/orientation
degeneracy, periodic seams, cell geometry, integer products, zero derivatives,
nonfinite/incomplete declarations and the difference between hypothetical
storage, source spend and recovery evidence. At most 32 new tests and two
retained derivative points are allowed. All attempted runs, source snapshots,
logs and runtime are retained; test sockets are disabled. No old phase audit,
control panel, bank witness or telescope data are evaluated. The original
preparation, ledgers, blockers and candidate/LS dispositions are immutable.
The plan remains limited to 26 September–9 October 2026.
