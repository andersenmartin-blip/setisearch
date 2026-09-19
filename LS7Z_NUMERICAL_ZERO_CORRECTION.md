# LS7Z numerical-zero correction for normalized L2 diagnostics

The first LS7Z execution completed the frozen evaluator but publication stopped
in the independent audit. The first mismatch was `CONTA_LC_ERR`:
the sideband series is constant to numerical precision. NumPy least squares
left a residual-MAD of about 1.6e-22 while the independent scalar normal
equations produced exact zero. Dividing the correspondingly tiny event-excess
roundoff by that tiny MAD produced a finite but physically meaningless
normalized value.

Before rerunning, the existing protocol phrase “when the MAD scale is finite
and nonzero” is given this fixed floating-point interpretation:

`MAD` is treated as numerically zero for the **normalized_event_excess field
only** when

`MAD <= 64 * eps_float64 * max(abs(sideband values), abs(predicted event values), tiny)`.

In that case `normalized_event_excess = null`. The raw sideband MAD, event
sum, predicted event sum and event excess remain reported exactly as computed.

The same rule is applied by evaluator and independent audit. It is a generic
machine-precision rule fixed from the input scale, not from the LS7Z morphology
outcome. It changes no image map, radial metric, template, fit domain, candidate
context, scientific threshold or interpretation boundary.
