# Conditional continuous coverage: a loose Cartesian construction — 27 September 2026

**Thirteen new tests pass. Six-parameter derivative envelopes now include the
implicit emission-time change. Their simple Cartesian covering construction is
far too large to instantiate. No bank was generated or adopted.**

This continues the [time-transfer result](RADIO_TIME_TRANSFER_2026-09-27_RESULT.md)
from science `bd7b801c0329e2f49c843124014b3c39d88b8d32`.
The [protocol](RADIO_MOTION_COVERING_2026-09-27_PROTOCOL.md) derives every bound
and distinguishes a sufficient construction from a necessary lower bound.

## Conditional derivative and covering result

The six-coordinate chart uses period, emitter-COM axis, projection ratio,
eccentricity, reference mean anomaly and mathematical planet orientation. The
projected axis is `a_p*projection`, so the whole rectangle respects the declared
axis relaxation. Both angles use shortest circular distance. Bounds apply to
the same retarded proper-frequency model, at 1500 MHz and through the numeric
exposure extent 1960.786474 s. Observer ratio remains one; physical-source
membership and full physical error remain unresolved.

| Coordinate | Global frequency derivative bound | Nodes in this sufficient construction |
| --- | ---: | ---: |
| Period (day) | 264840.035523 Hz/day | 505 |
| Emitter axis (AU) | 22489586.644161 Hz/AU | 3121810 |
| Projection ratio | 1474593.645222 Hz | 3120280 |
| Eccentricity | 4252648.437114 Hz | 1547780 |
| Mean anomaly (rad) | 2183158.012066 Hz/rad | 29025929 |
| Orientation (rad) | 1474593.645222 Hz/rad | 19605292 |

Six equal allocations of the illustrative half-channel tolerance give a summed
center-error bound of **1.417455574 Hz**, below 1.417751709 Hz. The resulting
Cartesian product has exactly **4332714645447545251954472549587360000** nodes
(about 4.333e36). Materializing float64 factors for 96 rows and three sample
times per row would take about **9.983e39 bytes**. No such allocation, template
generation or source-byte debit took place.

This huge number is **not a minimum required bank size or an impossibility
proof**. It is the size of one deliberately loose sufficient construction.
Global independent derivative envelopes discard reference-normalization
cancellation, local parameter correlations, zero/face-on/circular degeneracy,
free-carrier optimization and alternative track representations. The count is
not measured runtime, source-download expenditure, detector recovery or an
interval-certified implementation. The old 33-template bank is unchanged.

## Checks and retained evidence

The derivative proof explicitly includes
`d tau/dtheta = -[z_theta(tau)-z_theta(0)]/[c+v_z(tau)]`.
A separate scalar forward-derivative oracle differentiates Cartesian motion
through convergent Kepler and arrival-time iterations, rather than differentiating
the bound formulas. Two fixed interior points supply twelve frequency partials
and twelve implicit-time partials. All are inside their analytical envelopes.
Independent bracketed inversion and finite differences check the time terms.

The 13 tests additionally cover unit/frequency scaling, reference normalization,
circular phase/orientation degeneracy, angle seams, cell geometry, exact integer
products, zero derivatives, invalid inputs and the distinction between a
counted construction and a real bank or resource expenditure. One qualification
run retains exact code/configuration snapshots and logs. Test sockets were
disabled. All seventeen pinned input files still match. Repeated calculations
of the two oracle points do not become independent cases or scientific trials.

```sh
PYTHONPATH=src:scripts python scripts/radio_motion_covering_qualification.py
sha256sum -c RESULTS_MANIFEST_RADIO_MOTION_COVERING_2026-09-27.sha256
```

Across this connected continuation, domain declaration (16 tests), conditional
time transfer (15), and covering calculus (13) provide **44 distinct new tests**.
They do not rerun the old acquisition/native pipeline or failed science panels.
There are zero new metadata/source requests, telescope reservations, spectral
reads, generated templates, scientific trials or evaluation exposures.

All five original execution blockers remain. The source preparation, exhausted
synthetic ledger and empty telescope genesis are immutable. Primary is neighbor9.
The 24-case freeze and original 112+128 M43AF holdouts remain unopened. M43AI
is failed/closed; M15 GJ581 and M33 HD3651 unresolved. LS stays paused at
LS8BD–LS8BE, LS8BF unopened and CHEOPS unsent.

## Exact continuation

Do not instantiate or optimize this Cartesian grid. The next bounded connected
item is **analytic temporal compression**: derive uniform remainder bounds for
low-order polynomial representation of the same conditional retarded emitter
track, using derivative majorants. Evaluate only a prospectively bounded set of
orders and analytic checks; do not construct templates or run detectors. This
asks whether a different representation can avoid the demonstrated loose-grid
cost. It is not a physical-bank adoption, new width rule or control remedy.

After that, record what the combined conditional work can and cannot contribute
to the immutable execution envelope and fresh panel. A future physical bank
still needs real-source support, complete time/frequency/observer/systemic and
instrument terms, finite runtime evidence and prospectively bound recovery/RFI/
null evaluation within existing budgets. The pending 24 cases cannot be treated
as tested coverage of this new six-dimensional domain.

The live connector still needs independent admission and transport evidence.
Pointing still needs genuinely new same-scan RAW/FIL headers, observing log or
file-specific conversion for AGBT16A_999_189 ON 0015/0017/0019; the known
operator-log route is already recorded as requiring NRAO sign-on and was not
retried. HD1461/HIP1499 cadence 71139 remains on the 34.23-arcminute hold. No
message, booking, paid service, delegation or new automation occurred. The plan
is not expanded and closes on 9 October 2026.
