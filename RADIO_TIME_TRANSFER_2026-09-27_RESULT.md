# Conditional emission-time and Doppler error — 27 September 2026

**Fifteen new tests pass. Variable light-travel delay and two normalized Doppler
corrections are now separately bounded over the declared conditional domain.
The full physical error remains unknown; spectra remain BLOCKED.**

This is the connected continuation after the published
[phase-domain declaration](RADIO_PHASE_DOMAIN_2026-09-27_RESULT.md), science
`82df2e2a928a1d26849c15420c486289bf9ab8ce`. The
[protocol](RADIO_TIME_TRANSFER_2026-09-27_PROTOCOL.md) gives the derivations,
assumptions, fixed cases and numerical limitations. No old bank or control was
rerun, and no new template was created.

## Conditional whole-domain bounds

Use a stationary distant receiver, fixed line of sight, system barycentre at
rest, isolated Keplerian planet-COM emitter and flat spacetime, with observer
ratio one. These are conditional mathematical assumptions, not a qualified
model of the actual telescope/source. P/a/e support has no joint probability
or established real-source membership. At 1500 MHz, using the numeric maximum
absolute retained exposure edge 1960.786474 seconds:

| Conditional quantity | Upper bound |
| --- | ---: |
| COM speed | 147125.405437 m/s |
| Acceleration | 2.272940910 m/s² |
| Jerk | 0.000082308792 m/s³ |
| Source-time absolute extent | 1961.749217 s |
| Varying orbital light-travel delay | 0.962743 s |
| First-order frequency error from using reception instead of emission time | 10.954242 Hz |
| Normalized reciprocal versus first-order Doppler difference | 21.919242 Hz |
| Normalized transverse/proper-time term | 10.959621 Hz |
| Sum for this conditional emitter comparison only | 43.833105 Hz |

The inequalities cover every phase/orientation and the declared parameter
domain; they are analytic enclosing bounds, not phase-sampled maxima. The
numerical evaluations use binary64 and are not interval-certified. The sum
bounds one conditional model comparison. It **does not** bound observer,
systemic, gravitational, clock-scale, other-emitter-motion or instrument terms,
and is not entered into the blocked total physical accuracy contract.
A large upper bound does not establish a source error or detector loss.

The arrival map is `s=tau+[z(tau)-z(0)]/c`. Its derivative lies between
0.9995092425 and 1.0004907575, giving a unique conditional emission time. Free
phase absorbs a constant travel delay but not the varying orbital term. A
constant emitted proper frequency differs from a constant coordinate frequency.
After normalization, the transverse term vanishes for a circular orbit but
can survive with zero radial motion in a face-on eccentric orbit.

## Four frozen scalar equation examples

The four endpoints were fixed before computation at P_min, a_max, reference
mean anomaly pi/4 and the same positive endpoint T. They are equation examples,
not a bank comparison, optimized witness, independent observing sample or
detector-recovery test. Every signed contribution is retained:

| Endpoint case | Wrong clock (Hz) | Reciprocal (Hz) | Transverse (Hz) | Combined (Hz) |
| --- | ---: | ---: | ---: | ---: |
| e=.172, edge-on, omega=0 | -4.507981 | -8.985309 | +1.206382 | -12.286907 |
| e=0, edge-on, omega=0 | -3.189796 | -6.305407 | 0 | -9.495203 |
| e=.172, face-on | 0 | 0 | +1.206071 | +1.206071 |
| e=.172, half projection, omega=pi/3 | +0.737714 | +1.495632 | +1.205952 | +3.439298 |

All lie within the corresponding analytic bounds. Their signs and partial
cancellations are not assumed for other phases or missing physical terms.
The 15 new tests include independent eccentric-anomaly bisection and retarded
fixed-point inversion, a 60-digit Decimal algebra check, inverse-map derivative,
negative/reference offsets, circular/face-on limits, full integration-edge
extent, inconsistent speed rejection and refusal of physical authorization.

One qualification attempt is retained with exact code/configuration snapshot,
test log and runtime. Recomputing the same four endpoints during checking and
reporting does not create additional cases. Socket creation was disabled.
All twelve pinned old inputs still match; no metadata lookup, source request,
telescope reservation, scientific trial or evaluation exposure was made.

```sh
PYTHONPATH=src:scripts python scripts/radio_time_transfer_qualification.py
sha256sum -c RESULTS_MANIFEST_RADIO_TIME_TRANSFER_2026-09-27.sha256
```

The original preparation, exhausted synthetic ledger, empty telescope genesis
and all five execution blockers are unchanged. Primary remains neighbor9;
the fresh 24-case panel and original 112+128 M43AF holdouts remain unopened.
M43AI stays failed/closed, M15 GJ581 and M33 HD3651 unresolved, LS paused at
LS8BD–LS8BE, LS8BF unopened and CHEOPS unsent.

## Exact continuation

Continue directly with **analytic continuous-parameter sensitivity and covering
cost** for this conditional retarded proper-frequency model. Use bounded
derivatives and periodic-angle distances, explicitly include the implicit
emission-time derivative, and calculate a sufficient grid-size estimate without
generating a single template. Distinguish a loose sufficient construction from
a necessary lower bound or actual detector/runtime measurement. No bank, width,
confidence claim or evaluated control may be adopted or tuned from the result.

Full physical motion still needs the named missing terms and actual-source
support. The live connector frontier is closed at independent admission and
transport requirements. Pointing still requires genuinely new same-scan RAW/FIL
headers, log or file-specific conversion evidence for AGBT16A_999_189 ON scans
0015/0017/0019; none was obtained here. HD1461/HIP1499 cadence 71139 remains on
the 34.23-arcminute hold. There were no external messages, bookings, paid
services, delegated work or new automations. The plan closes on 9 October 2026.
