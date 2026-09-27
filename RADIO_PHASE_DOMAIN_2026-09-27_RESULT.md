# Conditional motion domain and conventions — 27 September 2026

**Sixteen new tests pass. A prospective mathematical support set and explicit
axis, phase, time and frequency conventions are now declared. The physical
model and all telescope access remain BLOCKED.**

The [protocol](RADIO_PHASE_DOMAIN_2026-09-27_PROTOCOL.md) and
[executable declaration](config/radio_phase_domain_20260927.json) are the
authorized continuation from science commit
`3c242a7288970aa2440c3c499fd3fadc08d96bf6`. The canonical declaration identity is
`ae64c06de60511d3c42551277aeb3a2bfe5280f082b89d3e24be555b3d385eff`.

P is conditionally restricted to [5.77107,5.77197] days, relative a to
[0.0612,0.0656] AU, and e to [0,0.172], with every phase and mathematical planet
orientation. P/a endpoints are a deliberate illustrative rectangle using the
retained quoted widths. **There is no joint probability or assertion that the
real source lies in this box.** The old e=0.172 remains an upper credible limit,
not a central eccentricity. No catalogue or paper query was repeated.

For a planet-COM emitter and any nonnegative planet/star mass ratio, the identity
`a_p=a_rel/(1+q)` gives the enclosing set `0<=A<=a_p<=0.0656 AU`. This declares
a useful conditional projection domain without inventing a mass measurement.
It excludes unmodelled surface/satellite/spacecraft and additional-companion
motion. Circular phase/orientation degeneracy and the old negative phase sign
are explicit. A face-on orbit can have zero radial motion and nonzero total
speed, which matters to relativistic modelling.

The source-time origin is the emission event corresponding to the first ON
reception midpoint. Constant travel delay can be absorbed into free phase;
variable orbital delay cannot. The old UTC reception clock is not silently
converted into emission time. The reference carrier is a received frequency,
with observer transformation and full physical clock mapping still unresolved.
The audit binds these meanings as well as the scalar endpoints and cannot
return source or bank authorization. Nine complete physical terms remain null.

The 16 tests cover false confidence/limit interpretations, invalid or missing
conventions, COM/projection geometry, phase and orientation signs, circular
degeneracy, radial/total speed separation and activation refusal. The sole
qualification run retains its exact code/configuration snapshot, log and
runtime; three scalar axis examples are retained. These are engineering
checks, not scientific trials. No new template, bank, control, spectrum,
old witness or phase sweep was computed. Network sockets were disabled during
qualification. All nine pinned prior inputs match before and after.

```sh
PYTHONPATH=src:scripts python scripts/radio_phase_domain_qualification.py
sha256sum -c RESULTS_MANIFEST_RADIO_PHASE_DOMAIN_2026-09-27.sha256
```

Reproduction appends a new qualification directory; unchanged reproduction
does not count as new progress. The original preparation, exhausted synthetic
ledger, empty telescope genesis and all five execution blockers stay unchanged.
There are zero new metadata/source requests, telescope reservations, scientific
trials or evaluation exposures. Primary is neighbor9. M43AI remains failed/
closed, original 112+128 M43AF holdouts untouched, M15 GJ581 and M33 HD3651
unresolved. LS is paused at LS8BD–LS8BE, LS8BF unopened, CHEOPS unsent.

## Exact continuation

Continue immediately with **conditional source-time/Doppler error and continuous
parameter sensitivity bounds** on this declared domain. Derive the varying
light-travel map, distinguish emitted proper from coordinate frequency, and
retain omitted terms as unknown. Test equations against independent scalar
oracles and analytic cases. Do not generate templates, change widths, adopt
the box as real-source support, or execute the fresh 24-case panel. Numerical
evaluation of a proven conditional inequality is not an interval certificate
or recovery result. Keep the original total physical error blocked.

The independent connector/admission frontier is closed until a concrete live
capability or explicit prospective alternative exists. Pointing still needs
genuinely new same-scan RAW/FIL, log or file-specific conversion evidence for
AGBT16A_999_189 ON 0015/0017/0019. No such evidence was obtained here. HD1461/
HIP1499 cadence 71139 remains on the 34.23-arcminute pointing hold. No external
message, automation, booking, paid service or delegated work was used. The
two-week plan is not expanded and closes on 9 October 2026.
